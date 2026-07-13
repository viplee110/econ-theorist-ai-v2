"""Provider-egress planning, authorization, and delivery-start serialization."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timezone
from pathlib import Path

from ..codec import canonical_json_bytes, sha256_digest
from ..ids import utc_now
from ..runtime.layout import (
    StoreLayout,
    UnsafeStorePath,
    assert_safe_store_path,
    path_entry_exists,
)
from ..runtime.faults import inject_fault
from ..runtime.lock import ExclusiveFileLock
from ..runtime.replay import replay
from .models import (
    CapabilityReceiptV1,
    DeliveryEnvelopeV1,
    DiagnosticV1,
    EgressAuthorizationV1,
    EgressPlanV1,
    HostOperationReceiptV1,
    LedgerEventV1,
    PacketDeliveryResultV1,
    WorkPacketV1,
)
from .operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
    write_immutable_operational,
)
from .packets import WorkPacketBindingV1, read_work_packet
from .resources import HOST_MANIFEST_V1_HASH


class EgressError(OperationalError):
    """Provider delivery is unauthorized, unsafe, stale, or uncertain."""


def read_bound_work_packet(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    packet_hash: str,
) -> WorkPacketV1:
    """Read only the immutable WorkPacket selected for one active run.

    The caller-supplied content address is checked against the run binding
    before packet bytes are read.  This prevents an alternate packet installed
    in the same operational CAS from changing privacy or egress semantics.
    """

    if not route_run_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
        for character in route_run_id
    ):
        raise EgressError(f"unsafe operational run ID: {route_run_id!r}")
    binding_path = operational.runs / route_run_id / "packet-binding.json"
    try:
        safe_binding_path = assert_safe_store_path(
            operational.project_root,
            binding_path,
            expected="file",
            allow_missing=False,
        )
        binding_data = safe_binding_path.read_bytes()
        binding = WorkPacketBindingV1.model_validate_json(
            binding_data, strict=True
        )
    except (OSError, ValueError, OperationalError, UnsafeStorePath) as exc:
        raise EgressError("work packet binding is unavailable or invalid") from exc
    if (
        canonical_json_bytes(binding) != binding_data
        or binding.route_run_id != route_run_id
        or binding.work_packet_hash != packet_hash
    ):
        raise EgressError("work packet is not the exact active run binding")
    packet = read_work_packet(operational, route_run_id, packet_hash)
    if (
        packet.route_run_id != route_run_id
        or packet.navigation_candidate_digest
        != binding.navigation_candidate_digest
    ):
        raise EgressError("work packet differs from its immutable run binding")
    return packet


def _uncertain_prior_delivery(
    event: LedgerEventV1,
    *,
    packet_hash: str,
    message: str,
) -> PacketDeliveryResultV1:
    """Return a retry result bound to the envelope that durably started."""

    if event.payload_hash is None:
        raise EgressError("delivery_started event lacks its envelope hash")
    return PacketDeliveryResultV1(
        status="unknown_possible_egress",
        delivery_envelope_hash=event.payload_hash,
        work_packet_hash=packet_hash,
        diagnostics=(
            DiagnosticV1(
                code="unknown_possible_egress",
                severity="error",
                message=message,
            ),
        ),
    )


def _parse_time(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EgressError(f"invalid egress timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise EgressError("egress timestamps must include a timezone")
    return parsed.astimezone(timezone.utc)


_REQUIRED_PHASE5A_CAPABILITIES = frozenset(
    {
        "python_runtime",
        "structured_process_invocation",
        "single_agent_topology",
    }
)


def _validate_required_capabilities(capability: CapabilityReceiptV1) -> None:
    available = {
        item.capability_id for item in capability.capabilities if item.available
    }
    if not _REQUIRED_PHASE5A_CAPABILITIES.issubset(available):
        raise EgressError("host capability receipt lacks required Phase 5A controls")


def _packet_privacy_labels(packet: WorkPacketV1) -> frozenset[str]:
    labels = {packet.privacy_clearance}
    if packet.run_input is not None:
        labels.add(packet.run_input.privacy)
    return frozenset(labels)


def _is_public_provider_packet(packet: WorkPacketV1) -> bool:
    """Return whether packet bytes are wholly public and non-blind."""

    return (
        _packet_privacy_labels(packet) == {"public"}
        and not packet.hidden_compartments
    )


def _automatic_delivery_subject(plan: EgressPlanV1) -> str:
    """Name a no-authorization ledger without mislabelling provider egress."""

    digest = sha256_digest(canonical_json_bytes(plan))[:48]
    if plan.execution_class == "local":
        return "local_" + digest
    if (
        plan.execution_class == "provider_backed"
        and not plan.authorization_required
        and tuple(plan.privacy_labels) == ("public",)
        and not plan.hidden_compartments
    ):
        return "public_" + digest
    raise EgressError("provider delivery cannot bypass authorization")


def create_egress_plan(
    packet: WorkPacketV1,
    capability: CapabilityReceiptV1,
    *,
    host_product: str,
    host_version: str,
    adapter_id: str,
    provider: str,
    model: str,
    execution_class: str,
    retention: str = "unknown",
    training_use: str = "unknown",
    logging: str = "unknown",
    region: str = "unknown",
    human_review: str = "unknown",
    memory_scope: str = "project_scoped",
) -> EgressPlanV1:
    """Build a conservative plan from technically accessible host scope."""

    if execution_class not in {"local", "provider_backed"}:
        raise EgressError("execution_class must be local or provider_backed")
    if capability.agent_topology != "single":  # pragma: no cover - literal guard
        raise EgressError("Phase 5A delivery requires single-agent topology")
    _validate_required_capabilities(capability)
    if capability.execution_class != execution_class:
        raise EgressError("capability execution class differs from the egress plan")
    if (
        host_product != capability.host_product
        or host_version != capability.host_version
        or adapter_id != capability.adapter_id
    ):
        raise EgressError("host identity differs from the capability receipt")
    labels = _packet_privacy_labels(packet)
    if packet.hidden_compartments and (
        capability.model_tool_isolation != "verified"
        or not set(packet.hidden_compartments).issubset(
            capability.enforced_denied_compartments
        )
    ):
        raise EgressError(
            "blind work requires adapter-enforced denial of every hidden compartment"
        )
    public_provider_packet = (
        execution_class == "provider_backed"
        and _is_public_provider_packet(packet)
    )
    if execution_class == "provider_backed":
        if "local_only" in labels:
            raise EgressError("local_only packet content cannot enter a provider host")
        provider_boundaries = (
            capability.environment_redaction,
            capability.credential_store_isolation,
            capability.secret_file_denial,
            capability.shadow_workspace_isolation,
        )
        if not public_provider_packet and any(
            value != "verified" for value in provider_boundaries
        ):
            raise EgressError(
                "provider execution requires verified environment, credential, secret-file, and shadow-workspace isolation"
            )
        if memory_scope not in {"disabled", "project_scoped"}:
            raise EgressError(
                "provider execution requires disabled or exact project-scoped memory"
            )
        if "restricted" in labels and (
            capability.model_tool_isolation != "verified"
            or capability.trusted_human_channel != "verified"
        ):
            raise EgressError(
                "restricted provider delivery requires verified tool isolation and trusted channel"
            )
        if "restricted" in labels and any(
            value == "unknown"
            for value in (retention, training_use, logging, region, human_review)
        ):
            raise EgressError(
                "restricted provider delivery cannot use unknown provider handling"
            )
    if packet.hidden_compartments and memory_scope != "disabled":
        raise EgressError("blind work requires disabled host memory")
    packet_hash = sha256_digest(canonical_json_bytes(packet))
    return EgressPlanV1(
        project_id=packet.project_id,
        head=packet.base_head,
        work_packet_hash=packet_hash,
        host_product=host_product,
        host_version=host_version,
        adapter_id=adapter_id,
        adapter_version=capability.adapter_version,
        capability_receipt_hash=sha256_digest(canonical_json_bytes(capability)),
        provider=provider,
        model=model,
        execution_class=execution_class,  # type: ignore[arg-type]
        technically_accessible_roots=capability.technically_accessible_roots,
        data_classes=("work_packet", "compiled_context", "run_input_brief"),
        privacy_labels=tuple(sorted(labels)),
        compartments=packet.compartments,
        hidden_compartments=packet.hidden_compartments,
        enforced_denied_compartments=capability.enforced_denied_compartments,
        purpose=packet.purpose,
        retention=retention,
        training_use=training_use,
        logging=logging,
        region=region,
        human_review=human_review,
        memory_scope=memory_scope,
        technical_isolation=capability.model_tool_isolation,
        trusted_human_channel=capability.trusted_human_channel,
        environment_redaction=capability.environment_redaction,
        credential_store_isolation=capability.credential_store_isolation,
        secret_file_denial=capability.secret_file_denial,
        shadow_workspace_isolation=capability.shadow_workspace_isolation,
        authorization_required=(
            execution_class == "provider_backed" and not public_provider_packet
        ),
    )


def _authorization_payload(
    authorization: EgressAuthorizationV1,
) -> dict[str, object]:
    return authorization.model_dump(mode="json", exclude={"authenticator"})


def _authenticator(secret: bytes, payload: dict[str, object]) -> str:
    if len(secret) < 32:
        raise EgressError("trusted egress secret must contain at least 32 bytes")
    return hmac.new(secret, canonical_json_bytes(payload), hashlib.sha256).hexdigest()


class HmacTrustedEgressChannel:
    """Reference non-model-callable authorization channel."""

    def __init__(self, channel_id: str, secret: bytes) -> None:
        if not channel_id or len(secret) < 32:
            raise EgressError("trusted egress channel requires an ID and 32-byte secret")
        self.channel_id = channel_id
        self._secret = secret

    def issue(
        self,
        plan: EgressPlanV1,
        *,
        direct_user_gesture: bool,
        expires_at: str,
        reuse: str = "single_delivery",
        max_deliveries: int = 1,
        issued_at: str | None = None,
        nonce: str | None = None,
    ) -> EgressAuthorizationV1:
        if not direct_user_gesture:
            raise EgressError("a model assertion is not egress authorization")
        if reuse not in {"single_delivery", "bounded_reuse"}:
            raise EgressError("unknown egress reuse rule")
        if (reuse == "single_delivery" and max_deliveries != 1) or (
            reuse == "bounded_reuse" and max_deliveries <= 1
        ):
            raise EgressError("egress reuse requires an exact positive delivery bound")
        issued = issued_at or utc_now()
        if _parse_time(issued) >= _parse_time(expires_at):
            raise EgressError("egress authorization expiry must follow issuance")
        plan_hash = sha256_digest(canonical_json_bytes(plan))
        token = nonce or secrets.token_hex(24)
        authorization_id = "egress_" + sha256_digest(
            canonical_json_bytes(
                {
                    "egress_plan_hash": plan_hash,
                    "channel_id": self.channel_id,
                    "nonce": token,
                }
            )
        )[:48]
        unsigned: dict[str, object] = {
            "authorization_schema": "econ-theorist/egress-authorization/v1",
            "authorization_id": authorization_id,
            "egress_plan_hash": plan_hash,
            "project_id": plan.project_id,
            "head": plan.head,
            "work_packet_hash": plan.work_packet_hash,
            "provider": plan.provider,
            "purpose": plan.purpose,
            "allowed_data_classes": plan.data_classes,
            "issued_at": issued,
            "expires_at": expires_at,
            "reuse": reuse,
            "max_deliveries": max_deliveries,
            "issuer_channel_id": self.channel_id,
            "nonce": token,
        }
        return EgressAuthorizationV1(
            **unsigned,
            authenticator=_authenticator(self._secret, unsigned),
        )

    def verify(self, authorization: EgressAuthorizationV1) -> None:
        if authorization.issuer_channel_id != self.channel_id:
            raise EgressError("authorization names a different trusted channel")
        expected = _authenticator(
            self._secret, _authorization_payload(authorization)
        )
        if not hmac.compare_digest(expected, authorization.authenticator):
            raise EgressError("egress authorization authenticator is invalid")


def _subject_root(
    operational: ProjectOperationalLayout, subject_id: str
) -> Path:
    if not subject_id.startswith(("egress_", "local_", "public_")) or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789_"
        for character in subject_id
    ):
        raise EgressError("unsafe egress ledger subject ID")
    return operational.egress / subject_id


def _events(
    operational: ProjectOperationalLayout, subject_id: str
) -> tuple[tuple[str, LedgerEventV1], ...]:
    root = _subject_root(operational, subject_id) / "events"
    if not path_entry_exists(root):
        return ()
    assert_safe_store_path(
        operational.project_root,
        root,
        expected="directory",
        allow_missing=False,
    )
    result: list[tuple[str, LedgerEventV1]] = []
    previous: str | None = None
    for sequence, path in enumerate(sorted(root.glob("*.json")), start=1):
        try:
            assert_safe_store_path(
                operational.project_root,
                path,
                expected="file",
                allow_missing=False,
            )
            data = path.read_bytes()
            event = LedgerEventV1.model_validate_json(data, strict=True)
        except (OSError, ValueError) as exc:
            raise EgressError("egress ledger event is invalid") from exc
        digest = sha256_digest(data)
        if (
            canonical_json_bytes(event) != data
            or event.ledger_kind != "egress"
            or event.subject_id != subject_id
            or event.sequence != sequence
            or event.previous_event_hash != previous
            or path.name != f"{sequence:08d}-{digest}.json"
        ):
            raise EgressError("egress ledger chain is inconsistent")
        result.append((digest, event))
        previous = digest
    return tuple(result)


def _append_event(
    operational: ProjectOperationalLayout,
    subject_id: str,
    *,
    event: str,
    operation_key: str | None,
    request_digest: str | None,
    payload_hash: str | None,
    recorded_at: str,
) -> LedgerEventV1:
    existing = _events(operational, subject_id)
    record = LedgerEventV1(
        ledger_kind="egress",
        subject_id=subject_id,
        sequence=len(existing) + 1,
        event=event,
        operation_key=operation_key,
        request_digest=request_digest,
        payload_hash=payload_hash,
        previous_event_hash=existing[-1][0] if existing else None,
        recorded_at=recorded_at,
    )
    data = canonical_json_bytes(record)
    digest = sha256_digest(data)
    path = (
        _subject_root(operational, subject_id)
        / "events"
        / f"{record.sequence:08d}-{digest}.json"
    )
    write_immutable_operational(operational.project_root, path, data)
    return record


def record_egress_authorization_issued(
    operational: ProjectOperationalLayout,
    plan: EgressPlanV1,
    authorization: EgressAuthorizationV1,
    channel: HmacTrustedEgressChannel,
) -> str:
    operational.ensure()
    channel.verify(authorization)
    plan_hash = sha256_digest(canonical_json_bytes(plan))
    if (
        authorization.egress_plan_hash != plan_hash
        or authorization.project_id != plan.project_id
        or authorization.head != plan.head
        or authorization.work_packet_hash != plan.work_packet_hash
        or authorization.provider != plan.provider
        or authorization.purpose != plan.purpose
        or tuple(authorization.allowed_data_classes) != tuple(plan.data_classes)
    ):
        raise EgressError("authorization differs from the exact egress plan")
    root = _subject_root(operational, authorization.authorization_id)
    store = ContentAddressedOperationalStore(operational.project_root, root)
    plan_digest, _ = store.install("plans", plan)
    authorization_digest, _ = store.install("authorizations", authorization)
    with ExclusiveFileLock(operational.egress_lock):
        existing = _events(operational, authorization.authorization_id)
        if existing:
            if (
                existing[0][1].event != "issued"
                or existing[0][1].payload_hash != authorization_digest
            ):
                raise EgressError("authorization ID is already bound differently")
            return authorization_digest
        _append_event(
            operational,
            authorization.authorization_id,
            event="issued",
            operation_key=None,
            request_digest=plan_digest,
            payload_hash=authorization_digest,
            recorded_at=authorization.issued_at,
        )
    return authorization_digest


def revoke_egress_authorization(
    operational: ProjectOperationalLayout,
    authorization_id: str,
    *,
    trusted_channel: bool,
    recorded_at: str | None = None,
) -> None:
    if not trusted_channel:
        raise EgressError("egress revocation requires the trusted-human channel")
    timestamp = recorded_at or utc_now()
    operational.ensure()
    with ExclusiveFileLock(operational.egress_lock):
        existing = _events(operational, authorization_id)
        if not existing:
            raise EgressError("unknown egress authorization")
        if existing[-1][1].event in {"revoked", "expired"}:
            return
        _append_event(
            operational,
            authorization_id,
            event="revoked",
            operation_key=None,
            request_digest=None,
            payload_hash=None,
            recorded_at=timestamp,
        )


def _blocked_envelope(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    packet_hash: str,
    operation_key: str,
    capability: CapabilityReceiptV1,
    plan: EgressPlanV1,
    *,
    host_session_id: str,
    adapter_version: str,
    delivery_time: str,
    session_fresh: bool,
    cross_run_memory_disabled: bool,
    authorization_hash: str | None,
    diagnostic: str,
) -> PacketDeliveryResultV1:
    run_root = operational.runs / route_run_id
    store = ContentAddressedOperationalStore(operational.project_root, run_root)
    capability_hash, _ = store.install("capabilities", capability)
    plan_hash, _ = store.install("egress-plans", plan)
    envelope = DeliveryEnvelopeV1(
        work_packet_hash=packet_hash,
        operation_key=operation_key,
        host_product=capability.host_product,
        host_version=capability.host_version,
        adapter_id=capability.adapter_id,
        adapter_version=adapter_version,
        host_session_id=host_session_id,
        session_fresh=session_fresh,
        cross_run_memory_disabled=cross_run_memory_disabled,
        project_root=str(operational.project_root),
        candidate_root=str(
            operational.store_root / "staging" / route_run_id
        ),
        projection_id=None,
        projection_hash=None,
        host_manifest_hash=HOST_MANIFEST_V1_HASH,
        capability_receipt_hash=capability_hash,
        egress_plan_hash=plan_hash,
        egress_authorization_hash=authorization_hash,
        delivery_time=delivery_time,
        pre_delivery_status="blocked_before_delivery",
    )
    envelope_hash, _ = store.install("envelopes", envelope)
    return PacketDeliveryResultV1(
        status="blocked_before_delivery",
        delivery_envelope_hash=envelope_hash,
        work_packet_hash=packet_hash,
        diagnostics=(
            DiagnosticV1(
                code="delivery_blocked",
                severity="error",
                message=diagnostic,
            ),
        ),
    )


def deliver_work_packet(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    packet_hash: str,
    operation_key: str,
    request_digest: str,
    plan: EgressPlanV1,
    capability: CapabilityReceiptV1,
    host_session_id: str,
    adapter_version: str,
    delivery_time: str,
    session_fresh: bool = False,
    cross_run_memory_disabled: bool = False,
    authorization: EgressAuthorizationV1 | None = None,
    channel: HmacTrustedEgressChannel | None = None,
) -> PacketDeliveryResultV1:
    """Record delivery_started before returning any packet content."""

    operational.ensure()
    packet = read_bound_work_packet(operational, route_run_id, packet_hash)
    packet_labels = tuple(sorted(_packet_privacy_labels(packet)))
    public_provider_packet = (
        plan.execution_class == "provider_backed"
        and _is_public_provider_packet(packet)
    )
    _validate_required_capabilities(capability)
    if packet.hidden_compartments and (
        capability.model_tool_isolation != "verified"
        or not set(packet.hidden_compartments).issubset(
            capability.enforced_denied_compartments
        )
    ):
        raise EgressError(
            "delivery capability does not enforce the packet's hidden compartments"
        )
    if packet.hidden_compartments and (
        not session_fresh or not cross_run_memory_disabled
    ):
        raise EgressError(
            "blind work requires a fresh session with cross-run memory disabled"
        )
    plan_hash_value = sha256_digest(canonical_json_bytes(plan))
    if (
        authorization is not None
        and plan_hash_value != authorization.egress_plan_hash
    ):
        raise EgressError("egress plan hash binding is invalid")
    if (
        plan.project_id != packet.project_id
        or plan.head != packet.base_head
        or plan.work_packet_hash != packet_hash
        or plan.host_product != capability.host_product
        or plan.host_version != capability.host_version
        or plan.adapter_id != capability.adapter_id
        or plan.adapter_version != capability.adapter_version
        or adapter_version != capability.adapter_version
        or plan.execution_class != capability.execution_class
        or plan.privacy_labels != packet_labels
        or plan.compartments != packet.compartments
        or plan.hidden_compartments != packet.hidden_compartments
        or plan.enforced_denied_compartments
        != capability.enforced_denied_compartments
        or plan.technically_accessible_roots
        != capability.technically_accessible_roots
        or plan.capability_receipt_hash
        != sha256_digest(canonical_json_bytes(capability))
        or plan.technical_isolation != capability.model_tool_isolation
        or plan.trusted_human_channel != capability.trusted_human_channel
        or plan.environment_redaction != capability.environment_redaction
        or plan.credential_store_isolation
        != capability.credential_store_isolation
        or plan.secret_file_denial != capability.secret_file_denial
        or plan.shadow_workspace_isolation
        != capability.shadow_workspace_isolation
        or any(item.required and not item.available for item in capability.capabilities)
        or capability.agent_topology != "single"
        or plan.authorization_required
        != (plan.execution_class == "provider_backed" and not public_provider_packet)
    ):
        raise EgressError("egress plan/capability differs from the work packet")

    if plan.execution_class == "provider_backed" and not public_provider_packet:
        provider_boundaries = (
            capability.environment_redaction,
            capability.credential_store_isolation,
            capability.secret_file_denial,
            capability.shadow_workspace_isolation,
        )
        if any(value != "verified" for value in provider_boundaries):
            raise EgressError(
                "provider execution requires verified environment, credential, secret-file, and shadow-workspace isolation"
            )
        if "local_only" in packet_labels:
            raise EgressError("local_only packet content cannot enter a provider host")

    authorization_hash: str | None = None
    if plan.authorization_required:
        if authorization is None or channel is None:
            return _blocked_envelope(
                operational,
                route_run_id,
                packet_hash,
                operation_key,
                capability,
                plan,
                host_session_id=host_session_id,
                adapter_version=adapter_version,
                delivery_time=delivery_time,
                session_fresh=session_fresh,
                cross_run_memory_disabled=cross_run_memory_disabled,
                authorization_hash=None,
                diagnostic="provider delivery requires trusted egress authorization",
            )
        channel.verify(authorization)
        authorization_hash = sha256_digest(canonical_json_bytes(authorization))
        subject_id = authorization.authorization_id
    else:
        subject_id = _automatic_delivery_subject(plan)

    run_root = operational.runs / route_run_id
    store = ContentAddressedOperationalStore(operational.project_root, run_root)
    capability_hash, _ = store.install("capabilities", capability)
    plan_hash, _ = store.install("egress-plans", plan)
    envelope = DeliveryEnvelopeV1(
        work_packet_hash=packet_hash,
        operation_key=operation_key,
        host_product=capability.host_product,
        host_version=capability.host_version,
        adapter_id=capability.adapter_id,
        adapter_version=adapter_version,
        host_session_id=host_session_id,
        session_fresh=session_fresh,
        cross_run_memory_disabled=cross_run_memory_disabled,
        project_root=str(layout.project_root),
        candidate_root=str(layout.staging_dir / route_run_id),
        projection_id=None,
        projection_hash=None,
        host_manifest_hash=HOST_MANIFEST_V1_HASH,
        capability_receipt_hash=capability_hash,
        egress_plan_hash=plan_hash,
        egress_authorization_hash=authorization_hash,
        delivery_time=delivery_time,
        pre_delivery_status="authorized_to_deliver",
    )
    envelope_hash, _ = store.install("envelopes", envelope)

    with ExclusiveFileLock(operational.egress_lock):
        existing = _events(operational, subject_id)
        if plan.authorization_required:
            assert authorization is not None
            if not existing or existing[0][1].event != "issued":
                raise EgressError("authorization was not issued through the trusted ledger")
            if _parse_time(delivery_time) >= _parse_time(authorization.expires_at):
                if existing[-1][1].event not in {"expired", "revoked"}:
                    _append_event(
                        operational,
                        subject_id,
                        event="expired",
                        operation_key=None,
                        request_digest=None,
                        payload_hash=None,
                        recorded_at=delivery_time,
                    )
                return _blocked_envelope(
                    operational,
                    route_run_id,
                    packet_hash,
                    operation_key,
                    capability,
                    plan,
                    host_session_id=host_session_id,
                    adapter_version=adapter_version,
                    delivery_time=delivery_time,
                    session_fresh=session_fresh,
                    cross_run_memory_disabled=cross_run_memory_disabled,
                    authorization_hash=authorization_hash,
                    diagnostic="egress authorization is expired",
                )
            prior_starts = [
                item for _, item in existing if item.event == "delivery_started"
            ]
            same_operation = next(
                (
                    item
                    for item in reversed(prior_starts)
                    if item.operation_key == operation_key
                ),
                None,
            )
            if same_operation is not None:
                return _uncertain_prior_delivery(
                    same_operation,
                    packet_hash=packet_hash,
                    message=(
                        "a prior attempt may already have exposed packet bytes; "
                        "automatic retry is forbidden"
                    ),
                )
            if len(prior_starts) >= authorization.max_deliveries:
                raise EgressError("egress authorization delivery bound was exhausted")
            if authorization.reuse == "single_delivery" and prior_starts:
                raise EgressError("single-delivery authorization was already used")
            if existing[-1][1].event in {"revoked", "expired"}:
                raise EgressError("egress authorization is revoked or expired")
        else:
            prior_automatic_start = next(
                (
                    item
                    for _, item in reversed(existing)
                    if item.event == "delivery_started"
                    and item.operation_key == operation_key
                ),
                None,
            )
            if prior_automatic_start is not None:
                return _uncertain_prior_delivery(
                    prior_automatic_start,
                    packet_hash=packet_hash,
                    message=(
                        "a prior public provider delivery may already have occurred"
                        if plan.execution_class == "provider_backed"
                        else "a prior local delivery may already have occurred"
                    ),
                )
            if not existing:
                _append_event(
                    operational,
                    subject_id,
                    event=(
                        "public_plan_registered"
                        if plan.execution_class == "provider_backed"
                        else "local_plan_registered"
                    ),
                    operation_key=None,
                    request_digest=plan_hash,
                    payload_hash=packet_hash,
                    recorded_at=delivery_time,
                )

        if any(
            item.event == "terminal_stale"
            and item.operation_key == operation_key
            and item.request_digest == request_digest
            for _, item in existing
        ):
            return _blocked_envelope(
                operational,
                route_run_id,
                packet_hash,
                operation_key,
                capability,
                plan,
                host_session_id=host_session_id,
                adapter_version=adapter_version,
                delivery_time=delivery_time,
                session_fresh=session_fresh,
                cross_run_memory_disabled=cross_run_memory_disabled,
                authorization_hash=authorization_hash,
                diagnostic="work packet base became stale before delivery",
            )

        if not existing or existing[-1][1].event != "reserved" or (
            existing[-1][1].operation_key != operation_key
        ):
            _append_event(
                operational,
                subject_id,
                event="reserved",
                operation_key=operation_key,
                request_digest=request_digest,
                payload_hash=envelope_hash,
                recorded_at=delivery_time,
            )
        with ExclusiveFileLock(layout.commit_lock):
            current = replay(layout)
            if current.head != packet.base_head:
                _append_event(
                    operational,
                    subject_id,
                    event="terminal_stale",
                    operation_key=operation_key,
                    request_digest=request_digest,
                    payload_hash=current.head,
                    recorded_at=delivery_time,
                )
                return _blocked_envelope(
                    operational,
                    route_run_id,
                    packet_hash,
                    operation_key,
                    capability,
                    plan,
                    host_session_id=host_session_id,
                    adapter_version=adapter_version,
                    delivery_time=delivery_time,
                    session_fresh=session_fresh,
                    cross_run_memory_disabled=cross_run_memory_disabled,
                    authorization_hash=authorization_hash,
                    diagnostic="work packet base became stale before delivery",
                )
            _append_event(
                operational,
                subject_id,
                event="delivery_started",
                operation_key=operation_key,
                request_digest=request_digest,
                payload_hash=envelope_hash,
                recorded_at=delivery_time,
            )
            inject_fault("after_delivery_started")
            # Returning this object is the first point packet content leaves the
            # engine service boundary. The durable start event precedes it.
            return PacketDeliveryResultV1(
                status="delivery_started",
                delivery_envelope_hash=envelope_hash,
                work_packet_hash=packet_hash,
                work_packet=packet,
            )


def record_delivery_outcome(
    operational: ProjectOperationalLayout,
    authorization_id: str,
    receipt: HostOperationReceiptV1,
) -> None:
    operational.ensure()
    with ExclusiveFileLock(operational.egress_lock):
        existing = _events(operational, authorization_id)
        starts = [
            item
            for _, item in existing
            if item.event == "delivery_started"
            and item.operation_key == receipt.operation_key
        ]
        if len(starts) != 1:
            raise EgressError("host receipt has no unique delivery_started event")
        event = (
            "unknown_possible_egress"
            if receipt.completion_status == "unknown_possible_egress"
            else "delivery_finished"
        )
        receipt_hash = sha256_digest(canonical_json_bytes(receipt))
        prior = [
            item
            for _, item in existing
            if item.event in {"delivery_finished", "unknown_possible_egress"}
            and item.operation_key == receipt.operation_key
        ]
        if prior:
            if len(prior) != 1 or (
                prior[0].event != event or prior[0].payload_hash != receipt_hash
            ):
                raise EgressError("delivery outcome is already bound differently")
            return
        _append_event(
            operational,
            authorization_id,
            event=event,
            operation_key=receipt.operation_key,
            request_digest=None,
            payload_hash=receipt_hash,
            recorded_at=receipt.completed_at,
        )


def record_envelope_delivery_outcome(
    operational: ProjectOperationalLayout,
    plan: EgressPlanV1,
    envelope: DeliveryEnvelopeV1,
    receipt: HostOperationReceiptV1,
) -> None:
    """Resolve the exact ledger subject and idempotently attach its outcome."""

    if envelope.pre_delivery_status != "authorized_to_deliver":
        return
    if plan.authorization_required:
        authorization_hash = envelope.egress_authorization_hash
        if authorization_hash is None:
            raise EgressError("authorized provider envelope lacks authorization")
        assert_safe_store_path(
            operational.project_root,
            operational.egress,
            expected="directory",
            allow_missing=False,
        )
        subjects: list[str] = []
        for root in operational.egress.iterdir():
            if not root.name.startswith("egress_"):
                continue
            assert_safe_store_path(
                operational.project_root,
                root,
                expected="directory",
                allow_missing=False,
            )
            events = _events(operational, root.name)
            if (
                events
                and events[0][1].event == "issued"
                and events[0][1].payload_hash == authorization_hash
            ):
                subjects.append(root.name)
        if len(subjects) != 1:
            raise EgressError("delivery envelope has no unique authorization ledger")
        subject_id = subjects[0]
    else:
        subject_id = _automatic_delivery_subject(plan)
    record_delivery_outcome(operational, subject_id, receipt)


__all__ = [
    "EgressError",
    "HmacTrustedEgressChannel",
    "create_egress_plan",
    "deliver_work_packet",
    "record_delivery_outcome",
    "record_envelope_delivery_outcome",
    "record_egress_authorization_issued",
    "read_bound_work_packet",
    "revoke_egress_authorization",
]
