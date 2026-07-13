"""Validated candidate completion and minimal host-operation receipts.

The machine facade keeps the frozen staging and commit implementations as the
only scientific validation and canonical mutation boundaries.  This module
adds exact WorkPacket/delivery binding, one fixed lock order, and crash-stable
operational receipts around those APIs.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError

from ..codec import canonical_json_bytes, sha256_digest, transaction_bytes
from ..models import Digest, RegisterArtifactOp, StrictModel, Transaction
from ..runs import read_run
from ..runtime.commit import CandidateBaseError
from ..runtime.layout import (
    StoreLayout,
    UnsafeStorePath,
    assert_safe_store_path,
    path_entry_exists,
)
from ..runtime.lock import ExclusiveFileLock
from ..runtime.objects import ObjectStore
from ..runtime.replay import replay
from ..staging import (
    StagingError,
    commit_run,
    read_staged_transaction,
    stage_candidate,
)
from .egress import read_bound_work_packet
from .models import (
    CandidateCompletionResultV1,
    DeliveryEnvelopeV1,
    EgressPlanV1,
    HostOperationReceiptV1,
    OperationKey,
    WorkPacketV1,
)
from .operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
    write_immutable_operational,
)


CompletionAction = Literal["stage_only", "commit_staged", "stage_and_commit"]
HostTerminalStatus = Literal[
    "failed_no_effect",
    "failed_terminal",
    "cancelled",
    "unknown_possible_effect",
    "unknown_possible_egress",
]

_SAFE_RECEIPT_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:+/@-]{0,127}")
_OPERATION_KEY = re.compile(r"[A-Za-z][A-Za-z0-9._:-]{0,127}")
_DIGEST = re.compile(r"[0-9a-f]{64}")
_REASONING_CLASSES = {
    "not_exposed",
    "summary_only",
    "provider_hidden",
    "unknown",
}


class CompletionError(OperationalError):
    """A completion request is stale, unbound, unsafe, or internally corrupt."""


class CandidateTransactionValidationError(CompletionError):
    """Strict candidate model issues safe to return to the authoring agent."""

    def __init__(
        self,
        *,
        issue_count: int,
        issues: tuple[dict[str, Any], ...],
        truncated: bool,
    ) -> None:
        super().__init__("candidate Transaction failed strict model validation")
        self.issue_count = issue_count
        self.issues = issues
        self.truncated = truncated


class _CompletionOperationRecordV1(StrictModel):
    record_schema: Literal["econ-theorist/completion-operation-record/v1"] = (
        "econ-theorist/completion-operation-record/v1"
    )
    invocation: Literal["candidate.complete", "host.finish"]
    operation_key: OperationKey
    request_digest: Digest
    route_run_id: str = Field(min_length=1)
    receipt_hash: Digest
    receipt: HostOperationReceiptV1
    result: CandidateCompletionResultV1


class _CandidateCompletionStartV1(StrictModel):
    start_schema: Literal["econ-theorist/candidate-completion-start/v1"] = (
        "econ-theorist/candidate-completion-start/v1"
    )
    action: Literal["stage_only", "commit_staged", "stage_and_commit"]
    operation_key: OperationKey
    request_digest: Digest
    route_run_id: str = Field(min_length=1)
    work_packet_hash: Digest
    delivery_envelope_hash: Digest
    candidate_digest: Digest


def _run_root(
    operational: ProjectOperationalLayout, route_run_id: str
) -> Path:
    if not route_run_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
        for character in route_run_id
    ):
        raise CompletionError(f"unsafe operational run ID: {route_run_id!r}")
    return operational.runs / route_run_id


def _operation_record_path(
    operational: ProjectOperationalLayout, route_run_id: str, operation_key: str
) -> Path:
    key_hash = sha256_digest(operation_key.encode("utf-8"))
    return (
        _run_root(operational, route_run_id)
        / "completion-operations"
        / f"{key_hash}.json"
    )


def _completion_start_path(
    operational: ProjectOperationalLayout, route_run_id: str, operation_key: str
) -> Path:
    key_hash = sha256_digest(operation_key.encode("utf-8"))
    return (
        _run_root(operational, route_run_id)
        / "completion-starts"
        / f"{key_hash}.json"
    )


def _load_completion_start(
    operational: ProjectOperationalLayout,
    *,
    action: CompletionAction,
    operation_key: str,
    request_digest: str,
    route_run_id: str,
    work_packet_hash: str,
    delivery_envelope_hash: str,
) -> _CandidateCompletionStartV1 | None:
    path = _completion_start_path(operational, route_run_id, operation_key)
    if not path_entry_exists(path):
        return None
    try:
        assert_safe_store_path(
            operational.project_root,
            path,
            expected="file",
            allow_missing=False,
        )
        data = path.read_bytes()
        start = _CandidateCompletionStartV1.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise CompletionError("candidate completion start record is invalid") from exc
    if (
        canonical_json_bytes(start) != data
        or start.action != action
        or start.operation_key != operation_key
        or start.request_digest != request_digest
        or start.route_run_id != route_run_id
        or start.work_packet_hash != work_packet_hash
        or start.delivery_envelope_hash != delivery_envelope_hash
    ):
        raise CompletionError(
            "operation key is already bound to a different candidate completion"
        )
    return start


def _persist_completion_start(
    operational: ProjectOperationalLayout,
    *,
    action: CompletionAction,
    operation_key: str,
    request_digest: str,
    route_run_id: str,
    work_packet_hash: str,
    delivery_envelope_hash: str,
    candidate_digest: str,
) -> _CandidateCompletionStartV1:
    start = _CandidateCompletionStartV1(
        action=action,
        operation_key=operation_key,
        request_digest=request_digest,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        delivery_envelope_hash=delivery_envelope_hash,
        candidate_digest=candidate_digest,
    )
    write_immutable_operational(
        operational.project_root,
        _completion_start_path(operational, route_run_id, operation_key),
        canonical_json_bytes(start),
    )
    return start


def _receipt_store(
    operational: ProjectOperationalLayout, route_run_id: str
) -> ContentAddressedOperationalStore:
    return ContentAddressedOperationalStore(
        operational.project_root, _run_root(operational, route_run_id)
    )


def _install_receipt(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    receipt: HostOperationReceiptV1,
) -> str:
    digest, _ = _receipt_store(operational, route_run_id).install(
        "host-receipts", receipt
    )
    return digest


def _load_operation_record(
    operational: ProjectOperationalLayout,
    *,
    invocation: Literal["candidate.complete", "host.finish"],
    operation_key: str,
    request_digest: str,
    route_run_id: str,
) -> CandidateCompletionResultV1 | None:
    path = _operation_record_path(operational, route_run_id, operation_key)
    if not path_entry_exists(path):
        return None
    try:
        assert_safe_store_path(
            operational.project_root,
            path,
            expected="file",
            allow_missing=False,
        )
        data = path.read_bytes()
        record = _CompletionOperationRecordV1.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise CompletionError("completion operation record is invalid") from exc
    if canonical_json_bytes(record) != data:
        raise CompletionError("completion operation record is not canonical JSON")
    if (
        record.invocation != invocation
        or record.operation_key != operation_key
        or record.request_digest != request_digest
        or record.route_run_id != route_run_id
        or record.receipt.operation_key != operation_key
        or record.result.route_run_id != route_run_id
        or record.result.host_receipt_hash != record.receipt_hash
        or sha256_digest(canonical_json_bytes(record.receipt)) != record.receipt_hash
    ):
        raise CompletionError(
            "operation key is already bound to different completion bytes"
        )
    # The operation record is the single crash boundary.  If a process stopped
    # after publishing it but before installing the content-addressed copy,
    # exact retry repairs that copy without changing the recorded result.
    installed = _install_receipt(
        operational, route_run_id, record.receipt
    )
    if installed != record.receipt_hash:  # pragma: no cover - hash invariant
        raise CompletionError("host receipt address changed during recovery")
    return record.result


def _persist_operation_result(
    operational: ProjectOperationalLayout,
    *,
    invocation: Literal["candidate.complete", "host.finish"],
    operation_key: str,
    request_digest: str,
    route_run_id: str,
    receipt: HostOperationReceiptV1,
    result_without_hash: CandidateCompletionResultV1,
) -> CandidateCompletionResultV1:
    receipt_hash = sha256_digest(canonical_json_bytes(receipt))
    result = result_without_hash.model_copy(
        update={"host_receipt_hash": receipt_hash}
    )
    record = _CompletionOperationRecordV1(
        invocation=invocation,
        operation_key=operation_key,
        request_digest=request_digest,
        route_run_id=route_run_id,
        receipt_hash=receipt_hash,
        receipt=receipt,
        result=result,
    )
    # Publish the combined record first.  It contains all receipt bytes and can
    # repair a missing content-addressed receipt after a crash.
    write_immutable_operational(
        operational.project_root,
        _operation_record_path(operational, route_run_id, operation_key),
        canonical_json_bytes(record),
    )
    installed = _install_receipt(operational, route_run_id, receipt)
    if installed != receipt_hash:  # pragma: no cover - hash invariant
        raise CompletionError("host receipt address changed during publication")
    return result


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left)) == os.path.normcase(str(right))


def _validate_output_paths(
    layout: StoreLayout,
    packet: WorkPacketV1,
    transaction_path: str | Path,
    artifacts: Mapping[str, str | Path] | None,
    *,
    allow_missing: bool = False,
) -> tuple[Path, dict[str, Path]]:
    lexical_transaction = Path(transaction_path)
    if not lexical_transaction.is_absolute():
        lexical_transaction = layout.project_root / lexical_transaction
    expected_transaction = layout.project_root / packet.candidate_logical_path
    candidate_root = layout.staging_dir / packet.route_run_id
    try:
        safe_transaction = assert_safe_store_path(
            candidate_root,
            lexical_transaction,
            expected="file",
            allow_missing=allow_missing,
        )
    except (FileNotFoundError, UnsafeStorePath) as exc:
        raise CompletionError("candidate transaction path is unsafe") from exc
    if not _same_path(safe_transaction, expected_transaction.absolute()):
        raise CompletionError(
            "candidate transaction must use the exact WorkPacket logical path"
        )
    shadow_root = layout.project_root / packet.shadow_logical_root
    safe_artifacts: dict[str, Path] = {}
    for artifact_id, value in (artifacts or {}).items():
        if not artifact_id:
            raise CompletionError("artifact IDs must be non-empty")
        lexical = Path(value)
        if not lexical.is_absolute():
            lexical = layout.project_root / lexical
        safe: Path | None = None
        for root in (candidate_root, shadow_root):
            try:
                safe = assert_safe_store_path(
                    root,
                    lexical,
                    expected="file",
                    allow_missing=allow_missing,
                )
                break
            except (FileNotFoundError, UnsafeStorePath):
                continue
        if safe is None:
            raise CompletionError(
                "candidate artifacts must stay in the packet candidate/shadow roots"
            )
        safe_artifacts[artifact_id] = safe
    return safe_transaction, safe_artifacts


def _capture_host_outputs(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    transaction: Transaction,
    artifact_sources: Mapping[str, Path],
) -> tuple[Path, dict[str, Path]]:
    root = _run_root(operational, route_run_id)
    body = transaction_bytes(transaction)
    candidate_digest = sha256_digest(body)
    candidate_path = (
        root / "host-candidates" / "sha256" / f"{candidate_digest}.json"
    )
    write_immutable_operational(
        operational.project_root, candidate_path, body
    )
    registration_items = [
        operation.artifact
        for operation in transaction.operations
        if isinstance(operation, RegisterArtifactOp)
    ]
    registrations = {
        registration.artifact_id: registration
        for registration in registration_items
    }
    if len(registrations) != len(registration_items):
        raise CompletionError("candidate repeats one artifact ID ambiguously")
    if set(registrations) != set(artifact_sources):
        raise CompletionError(
            "artifact sources must exactly match candidate registrations"
        )
    captured: dict[str, Path] = {}
    for artifact_id in sorted(registrations):
        registration = registrations[artifact_id]
        try:
            data = artifact_sources[artifact_id].read_bytes()
        except OSError as exc:
            raise CompletionError(
                f"candidate artifact is unavailable: {artifact_id}"
            ) from exc
        if (
            sha256_digest(data) != registration.content_hash
            or len(data) != registration.byte_size
        ):
            raise CompletionError(
                f"candidate artifact differs from its registration: {artifact_id}"
            )
        target = root / "host-artifacts" / "sha256" / registration.content_hash
        write_immutable_operational(operational.project_root, target, data)
        captured[artifact_id] = target
    return candidate_path, captured


def _read_captured_host_outputs(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    candidate_digest: str,
) -> tuple[Transaction, Path, dict[str, Path]]:
    root = _run_root(operational, route_run_id)
    candidate_path = (
        root / "host-candidates" / "sha256" / f"{candidate_digest}.json"
    )
    try:
        data = candidate_path.read_bytes()
        transaction = Transaction.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise CompletionError(
            "started completion lacks its immutable captured candidate"
        ) from exc
    if (
        transaction_bytes(transaction) != data
        or sha256_digest(data) != candidate_digest
    ):
        raise CompletionError("captured candidate bytes or address were modified")
    captured: dict[str, Path] = {}
    for operation in transaction.operations:
        if not isinstance(operation, RegisterArtifactOp):
            continue
        registration = operation.artifact
        if registration.artifact_id in captured:
            raise CompletionError("captured candidate repeats one artifact ID")
        path = root / "host-artifacts" / "sha256" / registration.content_hash
        try:
            artifact_data = path.read_bytes()
        except OSError as exc:
            raise CompletionError(
                "started completion lacks one immutable captured artifact"
            ) from exc
        if (
            sha256_digest(artifact_data) != registration.content_hash
            or len(artifact_data) != registration.byte_size
        ):
            raise CompletionError("captured artifact bytes or address were modified")
        captured[registration.artifact_id] = path
    return transaction, candidate_path, captured


def _has_exact_staged_candidate(
    layout: StoreLayout, route_run_id: str, candidate_digest: str
) -> bool:
    try:
        transaction = read_staged_transaction(layout, route_run_id)
    except StagingError:
        return False
    return sha256_digest(transaction_bytes(transaction)) == candidate_digest


def _read_candidate_source(path: str | Path) -> tuple[str, Transaction]:
    try:
        data = Path(path).read_bytes()
    except OSError as exc:
        raise CompletionError(
            "candidate transaction is unavailable at the declared WorkPacket path"
        ) from exc
    try:
        transaction = Transaction.model_validate_json(data, strict=True)
    except ValidationError as exc:
        raw_issues = exc.errors(
            include_url=False,
            include_context=False,
            include_input=False,
        )
        issues: list[dict[str, Any]] = []
        for error in raw_issues[:20]:
            location: list[str | int] = []
            for item in error["loc"]:
                if isinstance(item, int):
                    location.append(item)
                else:
                    text = str(item)
                    location.append(text if len(text) <= 160 else text[:157] + "...")
            issue_type = str(error["type"])
            message = str(error["msg"])
            issues.append(
                {
                    "location": location,
                    "type": issue_type if len(issue_type) <= 160 else issue_type[:157] + "...",
                    "message": message if len(message) <= 500 else message[:497] + "...",
                }
            )
        raise CandidateTransactionValidationError(
            issue_count=len(raw_issues),
            issues=tuple(issues),
            truncated=len(raw_issues) > len(issues),
        ) from exc
    body = transaction_bytes(transaction)
    return sha256_digest(body), transaction


def candidate_source_digest(
    layout: StoreLayout,
    packet: WorkPacketV1,
    transaction_path: str | Path,
) -> str:
    """Return canonical Transaction identity for the exact packet output path."""

    safe_path, _ = _validate_output_paths(
        layout,
        packet,
        transaction_path,
        artifacts=None,
    )
    digest, _ = _read_candidate_source(safe_path)
    return digest


def _artifact_digests(transaction: Transaction) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                operation.artifact.content_hash
                for operation in transaction.operations
                if isinstance(operation, RegisterArtifactOp)
            }
        )
    )


def _reachable_run_transaction(
    layout: StoreLayout, route_run_id: str
) -> tuple[str, Transaction] | None:
    snapshot = replay(layout)
    objects = ObjectStore(layout)
    found: list[tuple[str, Transaction]] = []
    for digest in snapshot.chain:
        data = objects.read_bytes("transactions", digest)
        try:
            transaction = Transaction.model_validate_json(data, strict=True)
        except ValueError as exc:  # pragma: no cover - replay already validates
            raise CompletionError("reachable transaction is invalid") from exc
        if transaction_bytes(transaction) != data:
            raise CompletionError("reachable transaction is noncanonical")
        if (
            transaction.origin == "route_run"
            and transaction.route_run_id == route_run_id
        ):
            found.append((digest, transaction))
    if len(found) > 1:
        raise CompletionError("canonical history repeats one route run")
    return found[0] if found else None


def _read_delivery_binding(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    packet_hash: str,
    delivery_envelope_hash: str,
    host_product: str,
    host_version: str,
    adapter_id: str,
    adapter_version: str,
    provider: str,
    model: str,
    require_authorized: bool,
) -> tuple[WorkPacketV1, DeliveryEnvelopeV1, EgressPlanV1]:
    try:
        packet = read_bound_work_packet(
            operational, route_run_id, packet_hash
        )
    except (OSError, ValueError, OperationalError) as exc:
        raise CompletionError("work packet binding is unavailable or invalid") from exc
    store = _receipt_store(operational, route_run_id)
    try:
        envelope_data = store.read_bytes("envelopes", delivery_envelope_hash)
        envelope = DeliveryEnvelopeV1.model_validate_json(
            envelope_data, strict=True
        )
    except (OSError, ValueError, OperationalError) as exc:
        raise CompletionError("delivery envelope is unavailable or invalid") from exc
    if canonical_json_bytes(envelope) != envelope_data:
        raise CompletionError("delivery envelope is not canonical JSON")
    if envelope.egress_plan_hash is None:
        raise CompletionError("delivery envelope lacks an exact egress plan")
    try:
        plan_data = store.read_bytes("egress-plans", envelope.egress_plan_hash)
        plan = EgressPlanV1.model_validate_json(plan_data, strict=True)
    except (OSError, ValueError, OperationalError) as exc:
        raise CompletionError("delivery egress plan is unavailable or invalid") from exc
    if canonical_json_bytes(plan) != plan_data:
        raise CompletionError("delivery egress plan is not canonical JSON")

    expected_candidate_root = (layout.staging_dir / route_run_id).resolve(
        strict=False
    )
    try:
        envelope_project_root = Path(envelope.project_root).resolve(strict=True)
        envelope_candidate_root = Path(envelope.candidate_root).resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        raise CompletionError("delivery envelope paths are unavailable") from exc
    if (
        packet.route_run_id != route_run_id
        or packet_hash != sha256_digest(canonical_json_bytes(packet))
        or envelope.work_packet_hash != packet_hash
        or plan.work_packet_hash != packet_hash
        or plan.project_id != packet.project_id
        or plan.head != packet.base_head
        or not _same_path(envelope_project_root, layout.project_root.resolve())
        or not _same_path(envelope_candidate_root, expected_candidate_root)
        or envelope.host_product != host_product
        or envelope.host_version != host_version
        or envelope.adapter_id != adapter_id
        or envelope.adapter_version != adapter_version
        or plan.host_product != host_product
        or plan.host_version != host_version
        or plan.adapter_id != adapter_id
        or plan.provider != provider
        or plan.model != model
        or (require_authorized and envelope.pre_delivery_status != "authorized_to_deliver")
    ):
        raise CompletionError(
            "host metadata or delivery bytes differ from the exact WorkPacket binding"
        )
    if envelope.pre_delivery_status == "authorized_to_deliver":
        _verify_delivery_started(
            operational,
            plan=plan,
            envelope=envelope,
            envelope_hash=delivery_envelope_hash,
        )
    return packet, envelope, plan


def _verify_delivery_started(
    operational: ProjectOperationalLayout,
    *,
    plan: EgressPlanV1,
    envelope: DeliveryEnvelopeV1,
    envelope_hash: str,
) -> None:
    # Use the egress module's chain validator; this is a read-only internal
    # boundary and avoids maintaining two subtly different ledger parsers.
    from .egress import _automatic_delivery_subject, _events

    if plan.authorization_required:
        if envelope.egress_authorization_hash is None:
            raise CompletionError(
                "provider delivery lacks its authorization content hash"
            )
        matching_subjects: list[str] = []
        try:
            assert_safe_store_path(
                operational.project_root,
                operational.egress,
                expected="directory",
                allow_missing=False,
            )
            subject_roots = tuple(operational.egress.iterdir())
        except OSError as exc:
            raise CompletionError("egress ledger root is unavailable") from exc
        for subject_root in subject_roots:
            if not subject_root.name.startswith("egress_"):
                continue
            try:
                assert_safe_store_path(
                    operational.project_root,
                    subject_root,
                    expected="directory",
                    allow_missing=False,
                )
            except (FileNotFoundError, UnsafeStorePath) as exc:
                raise CompletionError("egress ledger subject is unsafe") from exc
            events = _events(operational, subject_root.name)
            if (
                events
                and events[0][1].event == "issued"
                and events[0][1].payload_hash
                == envelope.egress_authorization_hash
            ):
                matching_subjects.append(subject_root.name)
        if len(matching_subjects) != 1:
            raise CompletionError(
                "delivery authorization does not have one exact egress ledger"
            )
        subject_id = matching_subjects[0]
    else:
        subject_id = _automatic_delivery_subject(plan)
    events = _events(operational, subject_id)
    starts = [
        event
        for _, event in events
        if event.event == "delivery_started"
        and event.operation_key == envelope.operation_key
        and event.payload_hash == envelope_hash
    ]
    if len(starts) != 1:
        raise CompletionError(
            "delivery envelope has no unique durable delivery_started event"
        )


def _validate_receipt_metadata(
    *,
    reasoning_class: str,
    tool_identities: tuple[str, ...],
    warnings: tuple[str, ...],
) -> None:
    if reasoning_class not in _REASONING_CLASSES:
        raise CompletionError(
            "reasoning_class must describe exposure, not contain model reasoning"
        )
    for label, values in (("tool identity", tool_identities), ("warning", warnings)):
        if len(set(values)) != len(values):
            raise CompletionError(f"{label} values must be unique")
        if any(_SAFE_RECEIPT_TOKEN.fullmatch(value) is None for value in values):
            raise CompletionError(
                f"{label} values must be bounded opaque identifiers, not free text"
            )


def _validate_invocation_metadata(
    *,
    operation_key: str,
    request_digest: str,
    completed_at: str,
    reasoning_class: str,
    tool_identities: tuple[str, ...],
    warnings: tuple[str, ...],
    expected_candidate_digest: str | None,
) -> None:
    if _OPERATION_KEY.fullmatch(operation_key) is None:
        raise CompletionError("operation key is not canonical")
    if _DIGEST.fullmatch(request_digest) is None:
        raise CompletionError("request digest is not canonical")
    if expected_candidate_digest is not None and (
        _DIGEST.fullmatch(expected_candidate_digest) is None
    ):
        raise CompletionError("expected candidate digest is not canonical")
    try:
        parsed = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CompletionError("completed_at is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise CompletionError("completed_at must include a timezone")
    _validate_receipt_metadata(
        reasoning_class=reasoning_class,
        tool_identities=tool_identities,
        warnings=warnings,
    )


def _receipt(
    *,
    delivery_envelope_hash: str,
    work_packet_hash: str,
    operation_key: str,
    host_product: str,
    host_version: str,
    adapter_id: str,
    adapter_version: str,
    provider: str,
    model: str,
    reasoning_class: str,
    tool_identities: tuple[str, ...],
    candidate_digest: str | None,
    artifact_digests: tuple[str, ...],
    stage_outcome: str | None,
    commit_outcome: str | None,
    head_before: str,
    head_after: str,
    warnings: tuple[str, ...],
    completion_status: str,
    completed_at: str,
) -> HostOperationReceiptV1:
    _validate_receipt_metadata(
        reasoning_class=reasoning_class,
        tool_identities=tool_identities,
        warnings=warnings,
    )
    return HostOperationReceiptV1(
        delivery_envelope_hash=delivery_envelope_hash,
        work_packet_hash=work_packet_hash,
        operation_key=operation_key,
        host_product=host_product,
        host_version=host_version,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        provider=provider,
        model=model,
        reasoning_class=reasoning_class,
        tool_identities=tool_identities,
        candidate_digest=candidate_digest,
        artifact_digests=artifact_digests,
        stage_outcome=stage_outcome,
        commit_outcome=commit_outcome,
        head_before=head_before,
        head_after=head_after,
        warnings=warnings,
        completion_status=completion_status,  # type: ignore[arg-type]
        completed_at=completed_at,
    )


def _result(
    *,
    status: str,
    route_run_id: str,
    candidate_digest: str | None,
    transaction_digest: str | None,
    head_before: str,
    head_after: str,
) -> CandidateCompletionResultV1:
    # The receipt hash is replaced atomically with the operation record.
    return CandidateCompletionResultV1(
        status=status,  # type: ignore[arg-type]
        route_run_id=route_run_id,
        candidate_digest=candidate_digest,
        transaction_digest=transaction_digest,
        head_before=head_before,
        head_after=head_after,
        host_receipt_hash="0" * 64,
    )


def complete_candidate(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    *,
    action: CompletionAction,
    operation_key: str,
    request_digest: str,
    route_run_id: str,
    work_packet_hash: str,
    delivery_envelope_hash: str,
    host_product: str,
    host_version: str,
    adapter_id: str,
    adapter_version: str,
    provider: str,
    model: str,
    reasoning_class: str,
    tool_identities: tuple[str, ...],
    completed_at: str,
    transaction_path: str | Path | None = None,
    artifacts: Mapping[str, str | Path] | None = None,
    expected_candidate_digest: str | None = None,
    warnings: tuple[str, ...] = (),
    lock_timeout: float | None = None,
) -> CandidateCompletionResultV1:
    """Stage and/or commit one exact host output through the frozen APIs.

    The caller must already hold the operation-key journal lock.  This service
    then takes ``navigation`` before every canonical commit lock acquisition.
    """

    if action not in {"stage_only", "commit_staged", "stage_and_commit"}:
        raise CompletionError(f"unsupported completion action: {action!r}")
    _validate_invocation_metadata(
        operation_key=operation_key,
        request_digest=request_digest,
        completed_at=completed_at,
        reasoning_class=reasoning_class,
        tool_identities=tool_identities,
        warnings=warnings,
        expected_candidate_digest=expected_candidate_digest,
    )
    if (action in {"stage_only", "stage_and_commit"}) != (
        transaction_path is not None
    ):
        raise CompletionError(
            "stage actions require one transaction path; commit_staged forbids it"
        )
    if action == "commit_staged" and artifacts:
        raise CompletionError("commit_staged cannot replace already staged artifacts")
    operational.ensure()
    replayed = _load_operation_record(
        operational,
        invocation="candidate.complete",
        operation_key=operation_key,
        request_digest=request_digest,
        route_run_id=route_run_id,
    )
    if replayed is not None:
        return replayed

    with ExclusiveFileLock(operational.navigation_lock, timeout=lock_timeout):
        # Recheck after acquiring the domain lock in case another process
        # completed the same exact operation while this caller was waiting.
        replayed = _load_operation_record(
            operational,
            invocation="candidate.complete",
            operation_key=operation_key,
            request_digest=request_digest,
            route_run_id=route_run_id,
        )
        if replayed is not None:
            return replayed
        packet, _, _ = _read_delivery_binding(
            layout,
            operational,
            route_run_id=route_run_id,
            packet_hash=work_packet_hash,
            delivery_envelope_hash=delivery_envelope_hash,
            host_product=host_product,
            host_version=host_version,
            adapter_id=adapter_id,
            adapter_version=adapter_version,
            provider=provider,
            model=model,
            require_authorized=True,
        )
        run = read_run(layout, route_run_id)
        if (
            run.project_id != packet.project_id
            or run.base_revision != packet.base_head
            or run.route_run_id != packet.route_run_id
        ):
            raise CompletionError("immutable run differs from its WorkPacket")

        start = _load_completion_start(
            operational,
            action=action,
            operation_key=operation_key,
            request_digest=request_digest,
            route_run_id=route_run_id,
            work_packet_hash=work_packet_hash,
            delivery_envelope_hash=delivery_envelope_hash,
        )
        if start is not None and expected_candidate_digest is not None and (
            start.candidate_digest != expected_candidate_digest
        ):
            raise CompletionError(
                "started candidate differs from the host declaration"
            )
        if start is not None and action in {"stage_only", "stage_and_commit"}:
            (
                transaction,
                safe_candidate_path,
                safe_artifact_sources,
            ) = _read_captured_host_outputs(
                operational, route_run_id, start.candidate_digest
            )
            candidate_digest = start.candidate_digest
        elif action == "commit_staged":
            transaction = read_staged_transaction(
                layout,
                route_run_id,
                digest=(start.candidate_digest if start is not None else None),
            )
            candidate_digest = sha256_digest(transaction_bytes(transaction))
            safe_candidate_path: Path | None = None
            safe_artifact_sources: dict[str, Path] = {}
        else:
            assert transaction_path is not None
            try:
                safe_candidate_path, safe_artifact_sources = _validate_output_paths(
                    layout, packet, transaction_path, artifacts
                )
                candidate_digest, transaction = _read_candidate_source(
                    safe_candidate_path
                )
            except CompletionError:
                # A process can stop after publishing the immutable,
                # content-addressed host capture but before publishing the
                # operation-key start record.  On an exact retry, the request
                # digest already binds the declared candidate digest and
                # paths.  Revalidate those paths lexically without requiring
                # the disposable originals to remain, then recover from the
                # captured bytes.  An unsafe or changed path still fails.
                if expected_candidate_digest is None:
                    raise
                _validate_output_paths(
                    layout,
                    packet,
                    transaction_path,
                    artifacts,
                    allow_missing=True,
                )
                (
                    transaction,
                    safe_candidate_path,
                    safe_artifact_sources,
                ) = _read_captured_host_outputs(
                    operational, route_run_id, expected_candidate_digest
                )
                candidate_digest = expected_candidate_digest
        if start is not None and start.candidate_digest != candidate_digest:
            raise CompletionError(
                "started completion differs from the active candidate"
            )
        if expected_candidate_digest is not None and (
            candidate_digest != expected_candidate_digest
        ):
            raise CompletionError("candidate digest differs from the host declaration")
        if (
            transaction.route_run_id != route_run_id
            or transaction.project_id != packet.project_id
            or transaction.base_revision != packet.base_head
        ):
            raise CompletionError("candidate differs from the exact run/packet base")
        artifact_hashes = _artifact_digests(transaction)

        with ExclusiveFileLock(layout.commit_lock, timeout=lock_timeout):
            snapshot = replay(layout)
            committed = _reachable_run_transaction(layout, route_run_id)
            if committed is not None:
                committed_digest, _ = committed
                if committed_digest != candidate_digest:
                    raise CompletionError(
                        "route run is canonically bound to a different transaction"
                    )
                if start is None:
                    raise CompletionError(
                        "route run was committed before this operation started"
                    )
                receipt = _receipt(
                    delivery_envelope_hash=delivery_envelope_hash,
                    work_packet_hash=work_packet_hash,
                    operation_key=operation_key,
                    host_product=host_product,
                    host_version=host_version,
                    adapter_id=adapter_id,
                    adapter_version=adapter_version,
                    provider=provider,
                    model=model,
                    reasoning_class=reasoning_class,
                    tool_identities=tool_identities,
                    candidate_digest=candidate_digest,
                    artifact_digests=artifact_hashes,
                    stage_outcome="staged",
                    commit_outcome="committed",
                    head_before=packet.base_head,
                    head_after=committed_digest,
                    warnings=warnings,
                    completion_status="completed",
                    completed_at=completed_at,
                )
                result = _result(
                    status="committed",
                    route_run_id=route_run_id,
                    candidate_digest=candidate_digest,
                    transaction_digest=committed_digest,
                    head_before=packet.base_head,
                    head_after=committed_digest,
                )
                return _persist_operation_result(
                    operational,
                    invocation="candidate.complete",
                    operation_key=operation_key,
                    request_digest=request_digest,
                    route_run_id=route_run_id,
                    receipt=receipt,
                    result_without_hash=result,
                )

            if snapshot.head != packet.base_head:
                if (
                    action == "stage_only"
                    and start is not None
                    and _has_exact_staged_candidate(
                        layout, route_run_id, candidate_digest
                    )
                ):
                    receipt = _receipt(
                        delivery_envelope_hash=delivery_envelope_hash,
                        work_packet_hash=work_packet_hash,
                        operation_key=operation_key,
                        host_product=host_product,
                        host_version=host_version,
                        adapter_id=adapter_id,
                        adapter_version=adapter_version,
                        provider=provider,
                        model=model,
                        reasoning_class=reasoning_class,
                        tool_identities=tool_identities,
                        candidate_digest=candidate_digest,
                        artifact_digests=artifact_hashes,
                        stage_outcome="staged",
                        commit_outcome=None,
                        head_before=packet.base_head,
                        head_after=packet.base_head,
                        warnings=warnings,
                        completion_status="completed",
                        completed_at=completed_at,
                    )
                    result = _result(
                        status="staged",
                        route_run_id=route_run_id,
                        candidate_digest=candidate_digest,
                        transaction_digest=None,
                        head_before=packet.base_head,
                        head_after=packet.base_head,
                    )
                    return _persist_operation_result(
                        operational,
                        invocation="candidate.complete",
                        operation_key=operation_key,
                        request_digest=request_digest,
                        route_run_id=route_run_id,
                        receipt=receipt,
                        result_without_hash=result,
                    )
                receipt = _receipt(
                    delivery_envelope_hash=delivery_envelope_hash,
                    work_packet_hash=work_packet_hash,
                    operation_key=operation_key,
                    host_product=host_product,
                    host_version=host_version,
                    adapter_id=adapter_id,
                    adapter_version=adapter_version,
                    provider=provider,
                    model=model,
                    reasoning_class=reasoning_class,
                    tool_identities=tool_identities,
                    candidate_digest=candidate_digest,
                    artifact_digests=artifact_hashes,
                    stage_outcome=(
                        "staged"
                        if _has_exact_staged_candidate(
                            layout, route_run_id, candidate_digest
                        )
                        else None
                    ),
                    commit_outcome="stale_base",
                    head_before=packet.base_head,
                    head_after=snapshot.head,
                    warnings=warnings,
                    completion_status="failed_terminal",
                    completed_at=completed_at,
                )
                result = _result(
                    status="stale_base",
                    route_run_id=route_run_id,
                    candidate_digest=candidate_digest,
                    transaction_digest=candidate_digest,
                    head_before=packet.base_head,
                    head_after=snapshot.head,
                )
                return _persist_operation_result(
                    operational,
                    invocation="candidate.complete",
                    operation_key=operation_key,
                    request_digest=request_digest,
                    route_run_id=route_run_id,
                    receipt=receipt,
                    result_without_hash=result,
                )

            if start is None:
                if action in {"stage_only", "stage_and_commit"}:
                    assert safe_candidate_path is not None
                    (
                        captured_candidate,
                        captured_artifacts,
                    ) = _capture_host_outputs(
                        operational,
                        route_run_id,
                        transaction,
                        safe_artifact_sources,
                    )
                start = _persist_completion_start(
                    operational,
                    action=action,
                    operation_key=operation_key,
                    request_digest=request_digest,
                    route_run_id=route_run_id,
                    work_packet_hash=work_packet_hash,
                    delivery_envelope_hash=delivery_envelope_hash,
                    candidate_digest=candidate_digest,
                )
            elif action in {"stage_only", "stage_and_commit"}:
                assert safe_candidate_path is not None
                captured_candidate = safe_candidate_path
                captured_artifacts = safe_artifact_sources

            if action in {"stage_only", "stage_and_commit"}:
                staged_digest = stage_candidate(
                    layout,
                    route_run_id,
                    captured_candidate,
                    artifacts=captured_artifacts,
                )
                if staged_digest != candidate_digest:
                    raise CompletionError("staging changed the candidate digest")

        if action == "stage_only":
            receipt = _receipt(
                delivery_envelope_hash=delivery_envelope_hash,
                work_packet_hash=work_packet_hash,
                operation_key=operation_key,
                host_product=host_product,
                host_version=host_version,
                adapter_id=adapter_id,
                adapter_version=adapter_version,
                provider=provider,
                model=model,
                reasoning_class=reasoning_class,
                tool_identities=tool_identities,
                candidate_digest=candidate_digest,
                artifact_digests=artifact_hashes,
                stage_outcome="staged",
                commit_outcome=None,
                head_before=packet.base_head,
                head_after=packet.base_head,
                warnings=warnings,
                completion_status="completed",
                completed_at=completed_at,
            )
            result = _result(
                status="staged",
                route_run_id=route_run_id,
                candidate_digest=candidate_digest,
                transaction_digest=None,
                head_before=packet.base_head,
                head_after=packet.base_head,
            )
        else:
            try:
                committed_result = commit_run(
                    layout, route_run_id, digest=candidate_digest
                )
            except CandidateBaseError:
                # A legacy writer can advance the head without the navigation
                # lock.  Normalize that safe loss into the machine terminal
                # stale result; never rebase or silently retry.
                current = replay(layout)
                committed_result = None
            if committed_result is None or committed_result.status == "stale_base":
                current_head = (
                    current.head
                    if committed_result is None
                    else committed_result.head_after
                )
                assert current_head is not None
                receipt = _receipt(
                    delivery_envelope_hash=delivery_envelope_hash,
                    work_packet_hash=work_packet_hash,
                    operation_key=operation_key,
                    host_product=host_product,
                    host_version=host_version,
                    adapter_id=adapter_id,
                    adapter_version=adapter_version,
                    provider=provider,
                    model=model,
                    reasoning_class=reasoning_class,
                    tool_identities=tool_identities,
                    candidate_digest=candidate_digest,
                    artifact_digests=artifact_hashes,
                    stage_outcome="staged",
                    commit_outcome="stale_base",
                    head_before=packet.base_head,
                    head_after=current_head,
                    warnings=warnings,
                    completion_status="failed_terminal",
                    completed_at=completed_at,
                )
                result = _result(
                    status="stale_base",
                    route_run_id=route_run_id,
                    candidate_digest=candidate_digest,
                    transaction_digest=candidate_digest,
                    head_before=packet.base_head,
                    head_after=current_head,
                )
            else:
                assert committed_result.head_after is not None
                receipt = _receipt(
                    delivery_envelope_hash=delivery_envelope_hash,
                    work_packet_hash=work_packet_hash,
                    operation_key=operation_key,
                    host_product=host_product,
                    host_version=host_version,
                    adapter_id=adapter_id,
                    adapter_version=adapter_version,
                    provider=provider,
                    model=model,
                    reasoning_class=reasoning_class,
                    tool_identities=tool_identities,
                    candidate_digest=candidate_digest,
                    artifact_digests=artifact_hashes,
                    stage_outcome="staged",
                    commit_outcome="committed",
                    head_before=packet.base_head,
                    head_after=committed_result.head_after,
                    warnings=warnings,
                    completion_status="completed",
                    completed_at=completed_at,
                )
                result = _result(
                    status="committed",
                    route_run_id=route_run_id,
                    candidate_digest=candidate_digest,
                    transaction_digest=committed_result.transaction_digest,
                    head_before=packet.base_head,
                    head_after=committed_result.head_after,
                )
        return _persist_operation_result(
            operational,
            invocation="candidate.complete",
            operation_key=operation_key,
            request_digest=request_digest,
            route_run_id=route_run_id,
            receipt=receipt,
            result_without_hash=result,
        )


def record_host_finish(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    *,
    operation_key: str,
    request_digest: str,
    route_run_id: str,
    work_packet_hash: str,
    delivery_envelope_hash: str,
    host_product: str,
    host_version: str,
    adapter_id: str,
    adapter_version: str,
    provider: str,
    model: str,
    reasoning_class: str,
    tool_identities: tuple[str, ...],
    completion_status: HostTerminalStatus,
    completed_at: str,
    warnings: tuple[str, ...] = (),
    expected_candidate_digest: str | None = None,
    lock_timeout: float | None = None,
) -> CandidateCompletionResultV1:
    """Persist a bounded failure/cancel/uncertainty receipt without mutation."""

    if completion_status not in {
        "failed_no_effect",
        "failed_terminal",
        "cancelled",
        "unknown_possible_effect",
        "unknown_possible_egress",
    }:
        raise CompletionError("host.finish cannot claim successful completion")
    _validate_invocation_metadata(
        operation_key=operation_key,
        request_digest=request_digest,
        completed_at=completed_at,
        reasoning_class=reasoning_class,
        tool_identities=tool_identities,
        warnings=warnings,
        expected_candidate_digest=expected_candidate_digest,
    )
    operational.ensure()
    replayed = _load_operation_record(
        operational,
        invocation="host.finish",
        operation_key=operation_key,
        request_digest=request_digest,
        route_run_id=route_run_id,
    )
    if replayed is not None:
        return replayed
    with ExclusiveFileLock(operational.navigation_lock, timeout=lock_timeout):
        replayed = _load_operation_record(
            operational,
            invocation="host.finish",
            operation_key=operation_key,
            request_digest=request_digest,
            route_run_id=route_run_id,
        )
        if replayed is not None:
            return replayed
        packet, _, _ = _read_delivery_binding(
            layout,
            operational,
            route_run_id=route_run_id,
            packet_hash=work_packet_hash,
            delivery_envelope_hash=delivery_envelope_hash,
            host_product=host_product,
            host_version=host_version,
            adapter_id=adapter_id,
            adapter_version=adapter_version,
            provider=provider,
            model=model,
            require_authorized=(completion_status == "unknown_possible_egress"),
        )
        with ExclusiveFileLock(layout.commit_lock, timeout=lock_timeout):
            snapshot = replay(layout)
            committed = _reachable_run_transaction(layout, route_run_id)
            if committed is not None:
                raise CompletionError(
                    "host.finish cannot overwrite a canonically completed run"
                )
            try:
                staged = read_staged_transaction(layout, route_run_id)
            except StagingError:
                staged = None
            candidate_digest = (
                sha256_digest(transaction_bytes(staged))
                if staged is not None
                else None
            )
            if expected_candidate_digest is not None and (
                expected_candidate_digest != candidate_digest
            ):
                raise CompletionError(
                    "host finish candidate differs from the staged run state"
                )
            receipt = _receipt(
                delivery_envelope_hash=delivery_envelope_hash,
                work_packet_hash=work_packet_hash,
                operation_key=operation_key,
                host_product=host_product,
                host_version=host_version,
                adapter_id=adapter_id,
                adapter_version=adapter_version,
                provider=provider,
                model=model,
                reasoning_class=reasoning_class,
                tool_identities=tool_identities,
                candidate_digest=candidate_digest,
                artifact_digests=(
                    _artifact_digests(staged) if staged is not None else ()
                ),
                stage_outcome=("staged" if staged is not None else None),
                commit_outcome=None,
                head_before=packet.base_head,
                head_after=snapshot.head,
                warnings=warnings,
                completion_status=completion_status,
                completed_at=completed_at,
            )
            result = _result(
                status="recorded_failure",
                route_run_id=route_run_id,
                candidate_digest=candidate_digest,
                transaction_digest=None,
                head_before=packet.base_head,
                head_after=snapshot.head,
            )
            return _persist_operation_result(
                operational,
                invocation="host.finish",
                operation_key=operation_key,
                request_digest=request_digest,
                route_run_id=route_run_id,
                receipt=receipt,
                result_without_hash=result,
            )


__all__ = [
    "CompletionAction",
    "CompletionError",
    "CandidateTransactionValidationError",
    "HostTerminalStatus",
    "candidate_source_digest",
    "complete_candidate",
    "record_host_finish",
]
