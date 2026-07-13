"""Strict single-agent dispatcher for the Phase 5A.1 machine protocol.

The dispatcher is the sole public machine-facing semantic surface.  It keeps
transport parsing, idempotency, trusted-channel injection, and the frozen
Phase 1--4 engine APIs on separate sides of one narrow boundary.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError

from ..codec import canonical_json_bytes, sha256_digest
from ..compatibility import probe_project_root
from ..ids import utc_now
from ..models import Actor, Decision, PrivacyLabel, StrictModel
from ..runtime.layout import StoreLayout
from ..runtime.replay import replay
from .authority import (
    HmacTrustedHumanChannel,
    confirm_decision_with_receipt,
)
from .binding import (
    bind_or_initialize_project,
    capture_project_root_identity,
    validate_discovery_grant,
)
from .bootstrap import (
    build_install_plan,
    validate_bootstrap_descriptor,
    verify_engine_inventory,
)
from .completion import complete_candidate, record_host_finish
from .egress import (
    HmacTrustedEgressChannel,
    create_egress_plan,
    deliver_work_packet,
)
from .inspection import inspect_project
from .models import (
    BootstrapDescriptorV1,
    CapabilityReceiptV1,
    DeliveryEnvelopeV1,
    DiagnosticV1,
    DiscoveryGrantV1,
    EgressAuthorizationV1,
    EgressPlanV1,
    EngineReleaseManifestV1,
    HumanApprovalChallengeV1,
    HumanApprovalReceiptV1,
    MachineRequestV1,
    MachineResponseV1,
    NavigationCandidateV1,
    PacketDeliveryResultV1,
    RunInputBriefV1,
)
from .operational import (
    ContentAddressedOperationalStore,
    OperationJournal,
    OperationKeyConflict,
    PreProjectOperationalLayout,
    ProjectOperationalLayout,
)
from .packets import read_work_packet
from .resources import HOST_MANIFEST_V1_HASH
from .run_service import open_or_resume_run


class MachineDispatchError(RuntimeError):
    """A request cannot be executed through the public machine surface."""


class _NavigationParameters(StrictModel):
    compartments: tuple[str, ...] = ("project_research",)
    privacy_clearance: PrivacyLabel = "project_private"
    budget_units: int | None = Field(default=None, ge=1)
    requested_route_ids: tuple[str, ...] | None = None
    run_input_brief: RunInputBriefV1 | None = None
    complete_if_none: bool = False


class _BindParameters(StrictModel):
    initialize: bool = False
    project_name: str | None = None
    requested_project_id: str | None = None


class _OpenParameters(StrictModel):
    candidate: NavigationCandidateV1
    run_input_brief: RunInputBriefV1 | None = None


class _BootstrapPlanParameters(StrictModel):
    descriptor: BootstrapDescriptorV1
    environment_root: str
    absolute_launcher: str
    network_origins: tuple[str, ...]
    project_initialization_requested: bool = False
    project_root: str | None = None
    project_name: str | None = None


class _BootstrapVerifyParameters(StrictModel):
    pass


class _EgressPlanParameters(StrictModel):
    route_run_id: str
    work_packet_hash: str
    capability: CapabilityReceiptV1
    host_product: str
    host_version: str
    adapter_id: str
    provider: str
    model: str
    execution_class: Literal["local", "provider_backed"]
    retention: str = "unknown"
    training_use: str = "unknown"
    logging: str = "unknown"
    region: str = "unknown"
    human_review: str = "unknown"
    memory_scope: Literal[
        "disabled", "project_scoped", "cross_project", "unknown"
    ] = "project_scoped"


class _DeliverParameters(StrictModel):
    route_run_id: str
    work_packet_hash: str
    plan: EgressPlanV1
    capability: CapabilityReceiptV1 | None = None
    authorization: EgressAuthorizationV1 | None = None


class _DecisionConfirmParameters(StrictModel):
    decision: Decision
    challenge: HumanApprovalChallengeV1
    receipt: HumanApprovalReceiptV1


class _CompletionParameters(StrictModel):
    action: Literal["stage_only", "commit_staged", "stage_and_commit"]
    route_run_id: str
    work_packet_hash: str
    delivery_envelope_hash: str
    transaction_path: str | None = None
    artifacts: dict[str, str] = Field(default_factory=dict)
    expected_candidate_digest: str | None = None
    reasoning_class: Literal[
        "not_exposed", "summary_only", "provider_hidden", "unknown"
    ] = "not_exposed"
    tool_identities: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class _HostFinishParameters(StrictModel):
    route_run_id: str
    work_packet_hash: str
    delivery_envelope_hash: str
    expected_candidate_digest: str | None = None
    reasoning_class: Literal[
        "not_exposed", "summary_only", "provider_hidden", "unknown"
    ] = "not_exposed"
    tool_identities: tuple[str, ...] = ()
    completion_status: Literal[
        "failed_no_effect",
        "failed_terminal",
        "cancelled",
        "unknown_possible_effect",
        "unknown_possible_egress",
    ] | None = None
    warnings: tuple[str, ...] = ()


class _OperationInspectParameters(StrictModel):
    operation_key: str
    scope: Literal["project", "preproject"] = "project"


@dataclass(frozen=True, slots=True)
class TrustedBootstrapAttestation:
    """External descriptor evidence injected outside model-controlled JSON."""

    descriptor_hash: str
    trusted_source: str
    signature_verified: bool
    revoked: bool = False


@dataclass(frozen=True, slots=True)
class TrustedBootstrapVerification:
    """Install evidence and host observation supplied by a trusted adapter."""

    launcher_path: str | None
    descriptor: BootstrapDescriptorV1
    release_manifest: EngineReleaseManifestV1
    target_id: str
    capability: CapabilityReceiptV1


@dataclass(frozen=True, slots=True)
class TrustedHostCompletionObservation:
    """Bounded host exit evidence injected outside the model tool payload."""

    operation_key: str
    delivery_envelope_hash: str
    host_product: str
    host_version: str
    adapter_id: str
    adapter_version: str
    provider: str
    model: str
    reasoning_class: Literal[
        "not_exposed", "summary_only", "provider_hidden", "unknown"
    ]
    tool_identities: tuple[str, ...] = ()
    completion_status: Literal[
        "completed",
        "failed_no_effect",
        "failed_terminal",
        "cancelled",
        "unknown_possible_effect",
        "unknown_possible_egress",
    ] = "completed"
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TrustedHostDeliverySession:
    """Adapter-observed session identity and memory boundary for one delivery."""

    operation_key: str
    adapter_id: str
    host_session_id: str
    fresh_session: bool
    cross_run_memory_disabled: bool


_ALWAYS_MUTATING = frozenset(
    {
        "bootstrap.verify",
        "run.open_or_resume",
        "packet.deliver",
        "candidate.complete",
        "host.finish",
        "decision.confirm",
    }
)
_PHASE5A_AGENT = Actor(kind="agent", actor_id="scientific_agent")


def _read_local_delivery_identity(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    delivery_envelope_hash: str,
) -> tuple[DeliveryEnvelopeV1, EgressPlanV1] | None:
    """Read one exact local envelope/plan for trusted self-use fallback."""

    store = ContentAddressedOperationalStore(
        operational.project_root, operational.runs / route_run_id
    )
    try:
        envelope_bytes = store.read_bytes("envelopes", delivery_envelope_hash)
        envelope = DeliveryEnvelopeV1.model_validate_json(
            envelope_bytes, strict=True
        )
        if (
            canonical_json_bytes(envelope) != envelope_bytes
            or envelope.egress_plan_hash is None
            or envelope.pre_delivery_status != "authorized_to_deliver"
        ):
            return None
        plan_bytes = store.read_bytes("egress-plans", envelope.egress_plan_hash)
        plan = EgressPlanV1.model_validate_json(plan_bytes, strict=True)
        if (
            canonical_json_bytes(plan) != plan_bytes
            or plan.execution_class != "local"
            or plan.adapter_id != envelope.adapter_id
            or plan.adapter_version != envelope.adapter_version
            or plan.host_product != envelope.host_product
            or plan.host_version != envelope.host_version
        ):
            return None
    except (OSError, RuntimeError, ValueError):
        return None
    return envelope, plan


def _result(value: Any) -> dict[str, Any]:
    if isinstance(value, StrictModel):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise MachineDispatchError(
        f"machine result must be a strict model or mapping, got {type(value).__name__}"
    )


def _request_digest(request: MachineRequestV1) -> str:
    return sha256_digest(canonical_json_bytes(request))


def _parse_parameters(model: type[StrictModel], request: MachineRequestV1) -> Any:
    """Validate untyped envelope parameters using strict JSON semantics.

    Pydantic intentionally distinguishes Python lists from tuples in strict
    Python mode, while JSON has only arrays.  Re-validating the canonical JSON
    representation preserves strict scalar typing and accepts protocol arrays
    for tuple fields exactly as direct ``model_validate_json`` would.
    """

    return model.model_validate_json(
        canonical_json_bytes(request.parameters), strict=True
    )


def _response(
    request: MachineRequestV1,
    *,
    outcome: str,
    mutated: bool,
    value: Any = None,
    project_id: str | None = None,
    head: str | None = None,
    diagnostics: tuple[DiagnosticV1, ...] = (),
    operation_receipt_hash: str | None = None,
) -> MachineResponseV1:
    return MachineResponseV1(
        operation=request.operation,
        request_digest=_request_digest(request),
        outcome=outcome,  # type: ignore[arg-type]
        mutated=mutated,
        project_id=project_id,
        head=head,
        result={} if value is None else _result(value),
        diagnostics=diagnostics,
        operation_receipt_hash=operation_receipt_hash,
    )


def error_response(
    request: MachineRequestV1,
    exc: Exception,
    *,
    outcome: str = "error",
) -> MachineResponseV1:
    """Return a strict response without exposing tracebacks or hidden state."""

    code = type(exc).__name__
    if isinstance(exc, ValidationError):
        failures = tuple(
            f"{'.'.join(str(item) for item in error['loc']) or '<root>'}:"
            f"{error['type']}"
            for error in exc.errors(include_url=False, include_context=False)
        )
        message = "invalid operation parameters (" + "; ".join(failures) + ")"
    else:
        message = (str(exc) or code)[:2000]
    return _response(
        request,
        outcome=outcome,
        mutated=False,
        diagnostics=(
            DiagnosticV1(
                code=code,
                severity="error",
                message=message,
            ),
        ),
    )


def _require_root_and_grant(request: MachineRequestV1) -> tuple[Path, DiscoveryGrantV1]:
    if request.project_root is None or request.discovery_grant is None:
        raise MachineDispatchError(
            "project_root and discovery_grant are required for this operation"
        )
    root, _ = validate_discovery_grant(
        request.project_root, request.discovery_grant
    )
    return root, request.discovery_grant


def _existing_project(request: MachineRequestV1) -> tuple[StoreLayout, Any]:
    root, _ = _require_root_and_grant(request)
    identity_before = capture_project_root_identity(root)
    probe = probe_project_root(root)
    if probe.classification != "valid_existing":
        raise MachineDispatchError(
            f"selected root is not a compatible project: {probe.classification}"
        )
    layout = StoreLayout.at(root)
    snapshot = replay(layout)
    identity_after = capture_project_root_identity(root)
    if identity_after != identity_before:
        raise MachineDispatchError(
            "selected project root/store changed during validation"
        )
    if snapshot.project_id != probe.project_id or snapshot.head != probe.head:
        raise MachineDispatchError(
            "compatibility probe and canonical replay disagree"
        )
    return layout, snapshot


def _navigation_outcome(outcome: str) -> str:
    return {
        "unique_next": "ok",
        "resume_required": "ok",
        "human_decision_required": "human_decision_required",
        "ambiguous_next": "ambiguous_next",
        "repair_required": "repair_required",
        "complete_for_requested_scope": "ok",
        "navigation_unsupported": "unsupported_host",
        "unsupported_host": "unsupported_host",
    }[outcome]


@dataclass(slots=True)
class MachineDispatcher:
    """Dispatch requests with trusted channels injected outside model input."""

    human_channels: Mapping[str, HmacTrustedHumanChannel] | None = None
    egress_channels: Mapping[str, HmacTrustedEgressChannel] | None = None
    host_capabilities: Mapping[str, CapabilityReceiptV1] | None = None
    trusted_clock: Callable[[], str] | None = None
    bootstrap_attestations: Mapping[str, TrustedBootstrapAttestation] | None = None
    bootstrap_verification: TrustedBootstrapVerification | None = None
    completion_observations: Mapping[
        str, TrustedHostCompletionObservation
    ] | None = None
    delivery_sessions: Mapping[str, TrustedHostDeliverySession] | None = None
    preproject_operational_home: str | Path | None = None
    initialization_actor_id: str = "local_human"

    def __post_init__(self) -> None:
        if not self.initialization_actor_id:
            raise MachineDispatchError("initialization actor ID cannot be empty")

    def _human_channel(
        self, receipt: HumanApprovalReceiptV1
    ) -> HmacTrustedHumanChannel | None:
        return (self.human_channels or {}).get(receipt.issuer_channel_id)

    def _egress_channel(
        self, authorization: EgressAuthorizationV1 | None
    ) -> HmacTrustedEgressChannel | None:
        if authorization is None:
            return None
        return (self.egress_channels or {}).get(authorization.issuer_channel_id)

    def _host_capability(self, adapter_id: str) -> CapabilityReceiptV1 | None:
        capability = (self.host_capabilities or {}).get(adapter_id)
        if capability is None or capability.adapter_id != adapter_id:
            return None
        return capability

    def _trusted_now(self) -> str | None:
        if self.trusted_clock is None:
            return None
        value = self.trusted_clock()
        if not isinstance(value, str) or not value:
            raise MachineDispatchError("trusted host clock returned an invalid value")
        return value

    def _completion_observation(
        self,
        operation_key: str,
        delivery_envelope_hash: str,
    ) -> TrustedHostCompletionObservation | None:
        value = (self.completion_observations or {}).get(operation_key)
        if (
            value is None
            or value.operation_key != operation_key
            or value.delivery_envelope_hash != delivery_envelope_hash
        ):
            return None
        return value

    def _delivery_session(
        self, operation_key: str, adapter_id: str
    ) -> TrustedHostDeliverySession | None:
        value = (self.delivery_sessions or {}).get(operation_key)
        if (
            value is None
            or value.operation_key != operation_key
            or value.adapter_id != adapter_id
            or not value.host_session_id
        ):
            return None
        return value

    def _journal_for(
        self, request: MachineRequestV1
    ) -> OperationJournal:
        root, _ = _require_root_and_grant(request)
        if request.operation in {"bootstrap.verify", "project.bind_or_initialize"}:
            preproject = PreProjectOperationalLayout.for_project(
                root,
                operational_home=self.preproject_operational_home,
            )
            return OperationJournal.for_preproject(preproject)
        layout, _ = _existing_project(request)
        return OperationJournal.for_project(ProjectOperationalLayout.at(layout))

    def dispatch(self, request: MachineRequestV1) -> MachineResponseV1:
        """Execute one request; exact mutating retries return stored responses."""

        initialize = bool(request.parameters.get("initialize", False))
        mutating = request.operation in _ALWAYS_MUTATING or (
            request.operation == "project.bind_or_initialize" and initialize
        )
        if mutating and request.operation_key is None:
            return error_response(
                request,
                MachineDispatchError(
                    "operation_key is required for every state-changing operation"
                ),
            )
        if not mutating and request.operation_key is not None:
            return error_response(
                request,
                MachineDispatchError(
                    "operation_key is reserved for state-changing operations"
                ),
            )
        if not mutating:
            try:
                return self._execute(request, reserved_at=None)
            except Exception as exc:
                return error_response(request, exc)

        assert request.operation_key is not None
        try:
            journal = self._journal_for(request)
            with journal.locked(request.operation_key) as operation:
                state = operation.reserve(request)
                if state.response is not None:
                    if (
                        request.operation == "packet.deliver"
                        and state.response.result.get("status")
                        == "delivery_started"
                    ):
                        # An exact transport retry may mean the first response
                        # was lost after packet bytes crossed the boundary.
                        # Egress safety therefore overrides ordinary response
                        # replay: never expose those bytes a second time.
                        uncertain = PacketDeliveryResultV1(
                            status="unknown_possible_egress",
                            delivery_envelope_hash=state.response.result[
                                "delivery_envelope_hash"
                            ],
                            work_packet_hash=state.response.result[
                                "work_packet_hash"
                            ],
                            diagnostics=(
                                DiagnosticV1(
                                    code="unknown_possible_egress",
                                    severity="error",
                                    message=(
                                        "a prior exact operation returned packet bytes; "
                                        "automatic redelivery is forbidden"
                                    ),
                                ),
                            ),
                        )
                        return _response(
                            request,
                            outcome="conflict",
                            mutated=False,
                            value=uncertain,
                            project_id=state.response.project_id,
                            head=state.response.head,
                            diagnostics=uncertain.diagnostics,
                            operation_receipt_hash=(
                                uncertain.delivery_envelope_hash
                            ),
                        )
                    return state.response
                response = self._execute(
                    request, reserved_at=state.reservation.reserved_at
                )
                operation.complete(response)
                return response
        except OperationKeyConflict as exc:
            return error_response(request, exc, outcome="conflict")
        except Exception as exc:
            # Unexpected/transient failures intentionally leave a reservation
            # incomplete so the exact key can recover after the cause is fixed.
            return error_response(request, exc)

    def _execute(
        self, request: MachineRequestV1, *, reserved_at: str | None
    ) -> MachineResponseV1:
        operation = request.operation
        if operation == "bootstrap.plan":
            parameters = _parse_parameters(_BootstrapPlanParameters, request)
            descriptor_hash = sha256_digest(
                canonical_json_bytes(parameters.descriptor)
            )
            attestation = (self.bootstrap_attestations or {}).get(descriptor_hash)
            now = self._trusted_now()
            if (
                attestation is None
                or attestation.descriptor_hash != descriptor_hash
                or now is None
            ):
                return _response(
                    request,
                    outcome="unsupported_host",
                    mutated=False,
                    diagnostics=(
                        DiagnosticV1(
                            code="external_bootstrap_attestation_required",
                            severity="error",
                            message=(
                                "the official bootstrap must inject signature, "
                                "revocation, and trusted-clock evidence for the exact descriptor"
                            ),
                        ),
                    ),
                )
            valid, diagnostics = validate_bootstrap_descriptor(
                parameters.descriptor,
                trusted_source=attestation.trusted_source,
                signature_verified_by_external_bootstrap=attestation.signature_verified,
                revoked=attestation.revoked,
                now=now,
            )
            if not valid:
                return _response(
                    request,
                    outcome="blocked",
                    mutated=False,
                    diagnostics=diagnostics,
                )
            plan = build_install_plan(
                parameters.descriptor,
                environment_root=parameters.environment_root,
                absolute_launcher=parameters.absolute_launcher,
                network_origins=parameters.network_origins,
                project_initialization_requested=(
                    parameters.project_initialization_requested
                ),
                project_root=parameters.project_root,
                project_name=parameters.project_name,
            )
            return _response(request, outcome="ok", mutated=False, value=plan)

        if operation == "bootstrap.verify":
            _parse_parameters(_BootstrapVerifyParameters, request)
            evidence = self.bootstrap_verification
            if evidence is None:
                return _response(
                    request,
                    outcome="unsupported_host",
                    mutated=False,
                    diagnostics=(
                        DiagnosticV1(
                            code="external_bootstrap_verification_required",
                            severity="error",
                            message=(
                                "the installed engine cannot attest its own installer; "
                                "an official adapter must inject exact external evidence"
                            ),
                        ),
                    ),
                )
            release_manifest_hash = sha256_digest(
                canonical_json_bytes(evidence.release_manifest)
            )
            descriptor = evidence.descriptor
            if (
                release_manifest_hash != descriptor.engine_manifest_hash
                or evidence.release_manifest.publisher_id != descriptor.publisher_id
                or evidence.release_manifest.release_version
                != descriptor.release_version
                or evidence.release_manifest.dependency_lock_hash
                != descriptor.dependency_lock_hash
                or descriptor.host_manifest_hash != HOST_MANIFEST_V1_HASH
            ):
                raise MachineDispatchError(
                    "trusted bootstrap evidence is not bound to the exact descriptor"
                )
            targets = tuple(
                item
                for item in evidence.release_manifest.targets
                if item.target_id == evidence.target_id
            )
            if len(targets) != 1:
                raise MachineDispatchError(
                    "trusted bootstrap evidence does not select one release target"
                )
            manifest, verification = verify_engine_inventory(
                project_root=request.project_root,
                launcher_path=evidence.launcher_path,
                expected_manifest_hash=targets[0].engine_inventory_hash,
                external_bootstrap_verified=True,
                release_manifest_hash=release_manifest_hash,
            )
            return _response(
                request,
                outcome="ok" if verification.verified else "blocked",
                mutated=True,
                value={
                    "engine_manifest": manifest.model_dump(mode="json"),
                    "verification": verification.model_dump(mode="json"),
                    "capability_receipt": evidence.capability.model_dump(mode="json"),
                },
                diagnostics=verification.diagnostics,
            )

        if operation == "project.bind_or_initialize":
            parameters = _parse_parameters(_BindParameters, request)
            root, grant = _require_root_and_grant(request)
            binding = bind_or_initialize_project(
                root,
                discovery_grant=grant,
                initialize=parameters.initialize,
                project_name=parameters.project_name,
                actor_id=self.initialization_actor_id,
                requested_project_id=parameters.requested_project_id,
                operation_key=request.operation_key,
                reserved_at=reserved_at,
                operational_home=self.preproject_operational_home,
            )
            outcome = {
                "bound": "ok",
                "initialized": "ok",
                "project_initialization_required": "permission_required",
                "project_identity_conflict": "conflict",
                "root_scope_incomplete": "unsupported_host",
                "recovery_required": "repair_required",
                "corrupt": "repair_required",
                "incompatible": "unsupported_host",
            }[binding.status]
            return _response(
                request,
                outcome=outcome,
                mutated=binding.mutated,
                value=binding,
                project_id=binding.project_id,
                head=binding.head,
                diagnostics=binding.diagnostics,
            )

        if operation in {"project.inspect", "navigation.plan_next"}:
            parameters = _parse_parameters(_NavigationParameters, request)
            layout, snapshot = _existing_project(request)
            inspection = inspect_project(
                layout,
                actor=_PHASE5A_AGENT,
                compartments=parameters.compartments,
                privacy_clearance=parameters.privacy_clearance,
                budget_units=parameters.budget_units,
                requested_route_ids=parameters.requested_route_ids,
                run_input_brief=parameters.run_input_brief,
                complete_if_none=parameters.complete_if_none,
                snapshot=snapshot,
            )
            value = (
                inspection
                if operation == "project.inspect"
                else inspection.navigation
            )
            assert value is not None
            outcome = (
                "ok"
                if operation == "project.inspect"
                else _navigation_outcome(value.outcome)
            )
            return _response(
                request,
                outcome=outcome,
                mutated=False,
                value=value,
                project_id=snapshot.project_id,
                head=snapshot.head,
                diagnostics=(
                    () if operation == "project.inspect" else value.blockers
                ),
            )

        if operation == "run.open_or_resume":
            parameters = _parse_parameters(_OpenParameters, request)
            layout, snapshot = _existing_project(request)
            assert request.operation_key is not None and reserved_at is not None
            if parameters.candidate.key.actor != _PHASE5A_AGENT:
                raise MachineDispatchError(
                    "navigation candidate actor differs from the trusted Phase 5A agent"
                )
            if (
                parameters.run_input_brief is not None
                and parameters.run_input_brief.actor_role
                != _PHASE5A_AGENT.actor_id
            ):
                raise MachineDispatchError(
                    "run input brief role differs from the trusted Phase 5A agent"
                )
            opened = open_or_resume_run(
                layout,
                operation_key=request.operation_key,
                reserved_at=reserved_at,
                candidate=parameters.candidate,
                run_input_brief=parameters.run_input_brief,
                operational=ProjectOperationalLayout.at(layout),
            )
            return _response(
                request,
                outcome="ok",
                mutated=True,
                value=opened,
                project_id=snapshot.project_id,
                head=snapshot.head,
            )

        if operation == "egress.plan":
            parameters = _parse_parameters(_EgressPlanParameters, request)
            layout, snapshot = _existing_project(request)
            operational = ProjectOperationalLayout.at(layout)
            packet = read_work_packet(
                operational,
                parameters.route_run_id,
                parameters.work_packet_hash,
            )
            plan = create_egress_plan(
                packet,
                parameters.capability,
                host_product=parameters.host_product,
                host_version=parameters.host_version,
                adapter_id=parameters.adapter_id,
                provider=parameters.provider,
                model=parameters.model,
                execution_class=parameters.execution_class,
                retention=parameters.retention,
                training_use=parameters.training_use,
                logging=parameters.logging,
                region=parameters.region,
                human_review=parameters.human_review,
                memory_scope=parameters.memory_scope,
            )
            return _response(
                request,
                outcome="ok",
                mutated=False,
                value=plan,
                project_id=snapshot.project_id,
                head=snapshot.head,
            )

        if operation == "packet.deliver":
            parameters = _parse_parameters(_DeliverParameters, request)
            layout, snapshot = _existing_project(request)
            assert request.operation_key is not None
            injected_capability = self._host_capability(parameters.plan.adapter_id)
            capability = injected_capability or parameters.capability
            delivery_time = self._trusted_now()
            channel = self._egress_channel(parameters.authorization)
            session = self._delivery_session(
                request.operation_key, parameters.plan.adapter_id
            )
            packet = read_work_packet(
                ProjectOperationalLayout.at(layout),
                parameters.route_run_id,
                parameters.work_packet_hash,
            )
            local_fallback = (
                injected_capability is None
                and capability is not None
                and parameters.plan.execution_class == "local"
                and not packet.hidden_compartments
            )
            if local_fallback:
                delivery_time = delivery_time or utc_now()
                session = session or TrustedHostDeliverySession(
                    operation_key=request.operation_key,
                    adapter_id=parameters.plan.adapter_id,
                    host_session_id=(
                        "local_"
                        + sha256_digest(request.operation_key.encode("utf-8"))[:32]
                    ),
                    fresh_session=False,
                    cross_run_memory_disabled=False,
                )
            if capability is None or delivery_time is None or session is None:
                return _response(
                    request,
                    outcome="unsupported_host",
                    mutated=False,
                    project_id=snapshot.project_id,
                    head=snapshot.head,
                    diagnostics=(
                        DiagnosticV1(
                            code="trusted_host_boundary_required",
                            severity="error",
                            message=(
                                "packet bytes require either a local self-use capability "
                                "receipt or an adapter-injected capability, session, and clock; "
                                "sealed packets never use the local fallback"
                            ),
                        ),
                    ),
                )
            if parameters.plan.authorization_required and (
                parameters.authorization is None or channel is None
            ):
                return _response(
                    request,
                    outcome="unsupported_host",
                    mutated=False,
                    project_id=snapshot.project_id,
                    head=snapshot.head,
                    diagnostics=(
                        DiagnosticV1(
                            code="trusted_egress_channel_required",
                            severity="error",
                            message=(
                                "provider delivery requires an injected, non-model-callable "
                                "egress authorization channel"
                            ),
                        ),
                    ),
                )
            delivery = deliver_work_packet(
                layout,
                ProjectOperationalLayout.at(layout),
                route_run_id=parameters.route_run_id,
                packet_hash=parameters.work_packet_hash,
                operation_key=request.operation_key,
                request_digest=_request_digest(request),
                plan=parameters.plan,
                capability=capability,
                host_session_id=session.host_session_id,
                adapter_version=capability.adapter_version,
                delivery_time=delivery_time,
                session_fresh=session.fresh_session,
                cross_run_memory_disabled=session.cross_run_memory_disabled,
                authorization=(
                    parameters.authorization if channel is not None else None
                ),
                channel=channel,
            )
            outcome = {
                "delivery_started": "ok",
                "blocked_before_delivery": "blocked",
                "unknown_possible_egress": "conflict",
            }[delivery.status]
            return _response(
                request,
                outcome=outcome,
                mutated=True,
                value=delivery,
                project_id=snapshot.project_id,
                head=snapshot.head,
                diagnostics=delivery.diagnostics,
                operation_receipt_hash=delivery.delivery_envelope_hash,
            )

        if operation == "decision.confirm":
            parameters = _parse_parameters(_DecisionConfirmParameters, request)
            layout, snapshot = _existing_project(request)
            channel = self._human_channel(parameters.receipt)
            now = self._trusted_now()
            if channel is None or now is None:
                return _response(
                    request,
                    outcome="unsupported_host",
                    mutated=False,
                    project_id=snapshot.project_id,
                    head=snapshot.head,
                    diagnostics=(
                        DiagnosticV1(
                            code="trusted_human_channel_required",
                            severity="error",
                            message=(
                                "the official adapter must inject a verified, "
                                "non-model-callable human channel and trusted clock"
                            ),
                        ),
                    ),
                )
            assert request.operation_key is not None
            confirmation = confirm_decision_with_receipt(
                layout,
                ProjectOperationalLayout.at(layout),
                operation_key=request.operation_key,
                request_digest=_request_digest(request),
                decision=parameters.decision,
                challenge=parameters.challenge,
                receipt=parameters.receipt,
                channel=channel,
                now=now,
            )
            return _response(
                request,
                outcome=(
                    "conflict" if confirmation.status == "stale_base" else "ok"
                ),
                mutated=confirmation.status == "committed",
                value=confirmation,
                project_id=snapshot.project_id,
                head=confirmation.head_after,
            )

        if operation == "candidate.complete":
            parameters = _parse_parameters(_CompletionParameters, request)
            layout, snapshot = _existing_project(request)
            assert request.operation_key is not None
            operational = ProjectOperationalLayout.at(layout)
            observation = self._completion_observation(
                request.operation_key, parameters.delivery_envelope_hash
            )
            completed_at = self._trusted_now()
            if observation is None:
                local_identity = _read_local_delivery_identity(
                    operational,
                    parameters.route_run_id,
                    parameters.delivery_envelope_hash,
                )
                if local_identity is not None:
                    envelope, plan = local_identity
                    observation = TrustedHostCompletionObservation(
                        operation_key=request.operation_key,
                        delivery_envelope_hash=parameters.delivery_envelope_hash,
                        host_product=envelope.host_product,
                        host_version=envelope.host_version,
                        adapter_id=envelope.adapter_id,
                        adapter_version=envelope.adapter_version,
                        provider=plan.provider,
                        model=plan.model,
                        reasoning_class=parameters.reasoning_class,
                        tool_identities=parameters.tool_identities,
                        completion_status="completed",
                        warnings=parameters.warnings,
                    )
                    completed_at = completed_at or utc_now()
            if (
                observation is None
                or completed_at is None
                or observation.completion_status != "completed"
            ):
                return _response(
                    request,
                    outcome="unsupported_host",
                    mutated=False,
                    project_id=snapshot.project_id,
                    head=snapshot.head,
                    diagnostics=(
                        DiagnosticV1(
                            code="trusted_host_completion_required",
                            severity="error",
                            message=(
                                "candidate completion requires either an exact local "
                                "delivery envelope or an adapter-injected host exit observation"
                            ),
                        ),
                    ),
                )
            completion = complete_candidate(
                layout,
                operational,
                action=parameters.action,
                operation_key=request.operation_key,
                request_digest=_request_digest(request),
                route_run_id=parameters.route_run_id,
                work_packet_hash=parameters.work_packet_hash,
                delivery_envelope_hash=parameters.delivery_envelope_hash,
                host_product=observation.host_product,
                host_version=observation.host_version,
                adapter_id=observation.adapter_id,
                adapter_version=observation.adapter_version,
                provider=observation.provider,
                model=observation.model,
                reasoning_class=observation.reasoning_class,
                tool_identities=observation.tool_identities,
                completed_at=completed_at,
                transaction_path=parameters.transaction_path,
                artifacts=parameters.artifacts,
                expected_candidate_digest=parameters.expected_candidate_digest,
                warnings=observation.warnings,
            )
            return _response(
                request,
                outcome=(
                    "conflict"
                    if completion.status == "stale_base"
                    else "ok"
                ),
                mutated=True,
                value=completion,
                project_id=snapshot.project_id,
                head=completion.head_after,
                operation_receipt_hash=completion.host_receipt_hash,
            )

        if operation == "host.finish":
            parameters = _parse_parameters(_HostFinishParameters, request)
            layout, snapshot = _existing_project(request)
            assert request.operation_key is not None
            operational = ProjectOperationalLayout.at(layout)
            observation = self._completion_observation(
                request.operation_key, parameters.delivery_envelope_hash
            )
            completed_at = self._trusted_now()
            if observation is None:
                local_identity = _read_local_delivery_identity(
                    operational,
                    parameters.route_run_id,
                    parameters.delivery_envelope_hash,
                )
                if (
                    local_identity is not None
                    and parameters.completion_status is not None
                ):
                    envelope, plan = local_identity
                    observation = TrustedHostCompletionObservation(
                        operation_key=request.operation_key,
                        delivery_envelope_hash=parameters.delivery_envelope_hash,
                        host_product=envelope.host_product,
                        host_version=envelope.host_version,
                        adapter_id=envelope.adapter_id,
                        adapter_version=envelope.adapter_version,
                        provider=plan.provider,
                        model=plan.model,
                        reasoning_class=parameters.reasoning_class,
                        tool_identities=parameters.tool_identities,
                        completion_status=parameters.completion_status,
                        warnings=parameters.warnings,
                    )
                    completed_at = completed_at or utc_now()
            if (
                observation is None
                or completed_at is None
                or observation.completion_status == "completed"
            ):
                return _response(
                    request,
                    outcome="unsupported_host",
                    mutated=False,
                    project_id=snapshot.project_id,
                    head=snapshot.head,
                    diagnostics=(
                        DiagnosticV1(
                            code="trusted_host_completion_required",
                            severity="error",
                            message=(
                                "host.finish requires either a local terminal status bound "
                                "to an exact delivery envelope or an adapter-injected observation"
                            ),
                        ),
                    ),
                )
            completion = record_host_finish(
                layout,
                operational,
                operation_key=request.operation_key,
                request_digest=_request_digest(request),
                route_run_id=parameters.route_run_id,
                work_packet_hash=parameters.work_packet_hash,
                delivery_envelope_hash=parameters.delivery_envelope_hash,
                host_product=observation.host_product,
                host_version=observation.host_version,
                adapter_id=observation.adapter_id,
                adapter_version=observation.adapter_version,
                provider=observation.provider,
                model=observation.model,
                reasoning_class=observation.reasoning_class,
                tool_identities=observation.tool_identities,
                completion_status=observation.completion_status,
                completed_at=completed_at,
                warnings=observation.warnings,
                expected_candidate_digest=parameters.expected_candidate_digest,
            )
            return _response(
                request,
                outcome="blocked",
                mutated=True,
                value=completion,
                project_id=snapshot.project_id,
                head=completion.head_after,
                operation_receipt_hash=completion.host_receipt_hash,
            )

        if operation == "operation.inspect":
            parameters = _parse_parameters(_OperationInspectParameters, request)
            root, _ = _require_root_and_grant(request)
            if parameters.scope == "preproject":
                operational = PreProjectOperationalLayout.for_project(
                    root, operational_home=self.preproject_operational_home
                )
                journal = OperationJournal(
                    anchor=operational.anchor,
                    operations=operational.operations,
                    locks=operational.locks,
                )
            else:
                layout, snapshot = _existing_project(request)
                operational = ProjectOperationalLayout.at(layout)
                journal = OperationJournal(
                    anchor=operational.project_root,
                    operations=operational.operations,
                    locks=operational.locks,
                )
            state = journal.inspect(parameters.operation_key)
            response_value = (
                None if state is None else state.response
            )
            if (
                response_value is not None
                and response_value.operation == "packet.deliver"
                and response_value.result.get("work_packet") is not None
            ):
                response_payload: dict[str, Any] | None = {
                    **response_value.model_dump(mode="json"),
                    "outcome": "conflict",
                    "mutated": False,
                    "result": {
                        "delivery_result_schema": (
                            "econ-theorist/packet-delivery-result/v1"
                        ),
                        "status": "unknown_possible_egress",
                        "delivery_envelope_hash": response_value.result[
                            "delivery_envelope_hash"
                        ],
                        "work_packet_hash": response_value.result[
                            "work_packet_hash"
                        ],
                        "work_packet": None,
                        "diagnostics": [],
                    },
                }
            else:
                response_payload = (
                    None
                    if response_value is None
                    else response_value.model_dump(mode="json")
                )
            value = (
                {"status": "absent", "operation_key": parameters.operation_key}
                if state is None
                else {
                    "status": (
                        "completed" if state.response is not None else "reserved"
                    ),
                    "reservation": state.reservation.model_dump(mode="json"),
                    "response": response_payload,
                }
            )
            return _response(
                request,
                outcome="ok",
                mutated=False,
                value=value,
            )

        raise MachineDispatchError(f"unsupported machine operation: {operation}")


__all__ = [
    "MachineDispatchError",
    "MachineDispatcher",
    "TrustedBootstrapAttestation",
    "TrustedBootstrapVerification",
    "TrustedHostCompletionObservation",
    "TrustedHostDeliverySession",
    "error_response",
]
