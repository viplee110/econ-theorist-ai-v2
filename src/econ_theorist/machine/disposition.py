"""Narrow operational disposition for one untouched framing reframe run."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Literal, TypeAlias

from ..codec import canonical_json_bytes, sha256_digest
from ..framing_team import framing_team_is_active
from ..models import Digest, EntityVersionRef, StrictModel
from ..runs import read_run
from ..runtime.layout import (
    StoreLayout,
    UnsafeStorePath,
    assert_safe_store_path,
    path_entry_exists,
)
from ..runtime.lock import ExclusiveFileLock
from ..runtime.replay import replay
from .egress import read_bound_work_packet
from .lifecycle import derive_run_execution_view
from .models import (
    DeliveryEnvelopeV1,
    NavigationCandidateV1,
    NonEmpty,
    OperationKey,
    RunExecutionViewV1,
    RunInputBriefV1,
)
from .navigation import enumerate_navigation_candidates
from .operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
    write_immutable_operational,
)
from .packets import read_run_input_brief


class RunReframeDispositionV1(StrictModel):
    """Legacy hash-only record written by the first local recovery pilot."""

    disposition_schema: Literal[
        "econ-theorist/run-reframe-disposition/v1"
    ] = "econ-theorist/run-reframe-disposition/v1"
    status: Literal["disposed_for_reframe"] = "disposed_for_reframe"
    operation_key: OperationKey
    project_id: NonEmpty
    head: Digest
    route_run_id: NonEmpty
    route_run_hash: Digest
    navigation_candidate_digest: Digest
    work_packet_hash: Digest
    delivery_envelope_hash: Digest
    successor_route_id: Literal["repair.dependency"] = "repair.dependency"
    successor_run_input_brief_hash: Digest
    successor_navigation_candidate_digest: Digest
    repair_target_ref: EntityVersionRef
    direct_user_capture_hash: Digest
    disposed_at: NonEmpty


class RunReframeDispositionV2(StrictModel):
    """Recoverable disposition with the exact non-secret successor inputs."""

    disposition_schema: Literal[
        "econ-theorist/run-reframe-disposition/v2"
    ] = "econ-theorist/run-reframe-disposition/v2"
    status: Literal["disposed_for_reframe"] = "disposed_for_reframe"
    operation_key: OperationKey
    project_id: NonEmpty
    head: Digest
    route_run_id: NonEmpty
    route_run_hash: Digest
    navigation_candidate_digest: Digest
    work_packet_hash: Digest
    delivery_envelope_hash: Digest
    successor_route_id: Literal["repair.dependency"] = "repair.dependency"
    successor_run_input_brief_hash: Digest
    successor_navigation_candidate_digest: Digest
    successor_run_input_brief: RunInputBriefV1
    successor_navigation_candidate: NavigationCandidateV1
    repair_target_ref: EntityVersionRef
    direct_user_capture_hash: Digest
    disposed_at: NonEmpty


RunReframeDispositionValue: TypeAlias = (
    RunReframeDispositionV1 | RunReframeDispositionV2
)


class RunReframeDispositionResultV1(StrictModel):
    result_schema: Literal[
        "econ-theorist/run-reframe-disposition-result/v1"
    ] = "econ-theorist/run-reframe-disposition-result/v1"
    status: Literal["disposed_for_reframe"] = "disposed_for_reframe"
    route_run_id: NonEmpty
    disposition_hash: Digest
    successor_run_input_brief_hash: Digest
    successor_navigation_candidate_digest: Digest
    repair_target_ref: EntityVersionRef


def _run_root(
    operational: ProjectOperationalLayout, route_run_id: str
) -> Path:
    if not route_run_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
        for character in route_run_id
    ):
        raise OperationalError(f"unsafe operational run ID: {route_run_id!r}")
    return operational.runs / route_run_id


def _disposition_path(
    operational: ProjectOperationalLayout, route_run_id: str
) -> Path:
    return _run_root(operational, route_run_id) / "reframe-disposition.json"


def _candidate_binding_path(
    operational: ProjectOperationalLayout, route_run_id: str
) -> Path:
    return _run_root(operational, route_run_id) / "navigation-candidate.json"


def _bridge_result_path(
    operational: ProjectOperationalLayout, route_run_id: str
) -> Path:
    return _run_root(operational, route_run_id) / "reframe-bridge-result.json"


def _read_candidate_binding(
    operational: ProjectOperationalLayout, route_run_id: str
) -> NavigationCandidateV1:
    path = _candidate_binding_path(operational, route_run_id)
    try:
        assert_safe_store_path(
            operational.project_root, path, expected="file", allow_missing=False
        )
        data = path.read_bytes()
        candidate = NavigationCandidateV1.model_validate_json(data, strict=True)
    except (OSError, ValueError, UnsafeStorePath) as exc:
        raise OperationalError(
            f"invalid navigation binding for run {route_run_id}"
        ) from exc
    if (
        canonical_json_bytes(candidate) != data
        or candidate.candidate_digest
        != sha256_digest(canonical_json_bytes(candidate.key))
    ):
        raise OperationalError("navigation binding is not canonical and self-bound")
    return candidate


def read_run_reframe_disposition(
    operational: ProjectOperationalLayout, route_run_id: str
) -> RunReframeDispositionValue | None:
    path = _disposition_path(operational, route_run_id)
    if not path_entry_exists(path):
        return None
    try:
        assert_safe_store_path(
            operational.project_root, path, expected="file", allow_missing=False
        )
        data = path.read_bytes()
        raw = json.loads(data)
        if not isinstance(raw, dict):
            raise ValueError("disposition must be one JSON object")
        schema = raw.get("disposition_schema")
        if schema == "econ-theorist/run-reframe-disposition/v1":
            record: RunReframeDispositionValue = (
                RunReframeDispositionV1.model_validate_json(data, strict=True)
            )
        elif schema == "econ-theorist/run-reframe-disposition/v2":
            record = RunReframeDispositionV2.model_validate_json(
                data, strict=True
            )
        else:
            raise ValueError("unknown disposition schema")
    except (OSError, ValueError, UnsafeStorePath) as exc:
        raise OperationalError("run reframe disposition is invalid") from exc
    if (
        canonical_json_bytes(record) != data
        or record.route_run_id != route_run_id
    ):
        raise OperationalError("run reframe disposition binding is invalid")
    if isinstance(record, RunReframeDispositionV2):
        brief = record.successor_run_input_brief
        candidate = record.successor_navigation_candidate
        if (
            sha256_digest(canonical_json_bytes(brief))
            != record.successor_run_input_brief_hash
            or candidate.candidate_digest
            != record.successor_navigation_candidate_digest
            or candidate.candidate_digest
            != sha256_digest(canonical_json_bytes(candidate.key))
            or candidate.key.route_id != record.successor_route_id
            or candidate.key.base_head != record.head
            or candidate.key.run_input_brief_hash
            != record.successor_run_input_brief_hash
            or record.repair_target_ref not in candidate.key.focus_refs
            or brief.project_id != record.project_id
            or brief.base_head != record.head
        ):
            raise OperationalError(
                "recoverable reframe successor binding is invalid"
            )
    return record


def read_reframe_bridge_result_bytes(
    operational: ProjectOperationalLayout, route_run_id: str
) -> bytes | None:
    path = _bridge_result_path(operational, route_run_id)
    if not path_entry_exists(path):
        return None
    try:
        assert_safe_store_path(
            operational.project_root, path, expected="file", allow_missing=False
        )
        return path.read_bytes()
    except (OSError, UnsafeStorePath) as exc:
        raise OperationalError("reframe bridge result is unavailable") from exc


def write_reframe_bridge_result_bytes(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    data: bytes,
) -> bool:
    if not data:
        raise OperationalError("reframe bridge result cannot be empty")
    return write_immutable_operational(
        operational.project_root,
        _bridge_result_path(operational, route_run_id),
        data,
    )


def recoverable_reframe_successor(
    record: RunReframeDispositionValue,
) -> tuple[RunInputBriefV1, NavigationCandidateV1]:
    if not isinstance(record, RunReframeDispositionV2):
        raise OperationalError(
            "legacy reframe disposition lacks recoverable successor inputs"
        )
    return (
        record.successor_run_input_brief,
        record.successor_navigation_candidate,
    )


def _validate_delivery(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    delivery_envelope_hash: str,
) -> tuple[object, DeliveryEnvelopeV1]:
    packet = read_bound_work_packet(
        operational, route_run_id, work_packet_hash
    )
    store = ContentAddressedOperationalStore(
        operational.project_root, _run_root(operational, route_run_id)
    )
    try:
        envelope_bytes = store.read_bytes("envelopes", delivery_envelope_hash)
        envelope = DeliveryEnvelopeV1.model_validate_json(
            envelope_bytes, strict=True
        )
    except (OSError, ValueError, OperationalError) as exc:
        raise OperationalError("delivery envelope is unavailable or invalid") from exc
    if canonical_json_bytes(envelope) != envelope_bytes:
        raise OperationalError("delivery envelope is not canonical JSON")
    if (
        envelope.work_packet_hash != work_packet_hash
        or envelope.pre_delivery_status != "authorized_to_deliver"
        or packet.route_run_id != route_run_id
    ):
        raise OperationalError("delivery does not bind the exact reframe run")
    return packet, envelope


def _has_completion_evidence(
    operational: ProjectOperationalLayout, route_run_id: str
) -> bool:
    root = _run_root(operational, route_run_id)
    for name in (
        "completion-starts",
        "completion-operations",
        "host-receipts",
        "host-candidates",
        "host-artifacts",
    ):
        directory = root / name
        if not path_entry_exists(directory):
            continue
        try:
            assert_safe_store_path(
                operational.project_root,
                directory,
                expected="directory",
                allow_missing=False,
            )
            if any(entry.is_file() for entry in directory.rglob("*")):
                return True
        except (OSError, UnsafeStorePath) as exc:
            raise OperationalError(
                "cannot inspect prior completion evidence"
            ) from exc
    return False


def _validate_source_bindings(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    view: RunExecutionViewV1,
    record: RunReframeDispositionValue,
) -> None:
    if (
        view.route_run_id != record.route_run_id
        or view.integrity != "valid"
        or view.lifecycle != "opened"
        or view.base_head != record.head
    ):
        raise OperationalError("disposed run evidence no longer matches its record")
    run = read_run(layout, record.route_run_id)
    candidate = _read_candidate_binding(operational, record.route_run_id)
    packet, _ = _validate_delivery(
        operational,
        route_run_id=record.route_run_id,
        work_packet_hash=record.work_packet_hash,
        delivery_envelope_hash=record.delivery_envelope_hash,
    )
    if (
        run.project_id != record.project_id
        or run.base_revision != record.head
        or sha256_digest(canonical_json_bytes(run)) != record.route_run_hash
        or candidate.candidate_digest != record.navigation_candidate_digest
        or candidate.key.route_id != "frame.question_and_benchmarks"
        or candidate.key.route_version != 2
        or candidate.key.focus_refs
        or candidate.key.base_head != record.head
        or packet.project_id != record.project_id
        or packet.base_head != record.head
        or packet.route_run_hash != record.route_run_hash
        or packet.navigation_candidate_digest != candidate.candidate_digest
        or packet.route_id != candidate.key.route_id
        or packet.route_version != candidate.key.route_version
        or packet.route_registry_hash != candidate.key.route_registry_hash
        or packet.focus_refs != candidate.key.focus_refs
    ):
        raise OperationalError("disposed source bindings are inconsistent")


def _successor_matches(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    view: RunExecutionViewV1,
    record: RunReframeDispositionValue,
) -> bool:
    if (
        view.route_run_id == record.route_run_id
        or view.integrity != "valid"
        or view.base_head != record.head
    ):
        return False
    candidate = _read_candidate_binding(operational, view.route_run_id)
    if (
        candidate.candidate_digest
        != record.successor_navigation_candidate_digest
        or candidate.key.route_id != record.successor_route_id
        or candidate.key.base_head != record.head
        or record.repair_target_ref not in candidate.key.focus_refs
        or candidate.key.run_input_brief_hash
        != record.successor_run_input_brief_hash
    ):
        return False
    run = read_run(layout, view.route_run_id)
    brief = read_run_input_brief(operational, view.route_run_id, candidate)
    return bool(
        brief is not None
        and sha256_digest(canonical_json_bytes(brief))
        == record.successor_run_input_brief_hash
        and run.project_id == record.project_id
        and run.base_revision == record.head
        and run.route_id == record.successor_route_id
        and run.route_version == candidate.key.route_version
        and run.actor == candidate.key.actor
        and run.context_hash == candidate.key.context_hash
        and run.focus_entity_ids
        == tuple(item.entity_id for item in candidate.key.focus_refs)
    )


def dispose_run_for_reframe(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    *,
    operation_key: str,
    disposed_at: str,
    route_run_id: str,
    work_packet_hash: str,
    delivery_envelope_hash: str,
    successor_run_input_brief: RunInputBriefV1,
    successor_candidate: NavigationCandidateV1,
    repair_target_ref: EntityVersionRef,
    direct_user_capture_hash: str,
    lock_timeout: float | None = None,
) -> tuple[RunReframeDispositionResultV1, bool]:
    """Dispose exactly one untouched empty-focus framing run for one repair."""

    operational.ensure()
    brief_hash = sha256_digest(canonical_json_bytes(successor_run_input_brief))
    with ExclusiveFileLock(operational.navigation_lock, timeout=lock_timeout):
        with ExclusiveFileLock(layout.commit_lock, timeout=lock_timeout):
            snapshot = replay(layout)
            view = derive_run_execution_view(layout, snapshot, route_run_id)
            existing = read_run_reframe_disposition(
                operational, route_run_id
            )
            if existing is not None:
                _validate_source_bindings(
                    layout, operational, view, existing
                )
                if (
                    existing.operation_key != operation_key
                    or existing.project_id != successor_run_input_brief.project_id
                    or existing.head != successor_run_input_brief.base_head
                    or existing.work_packet_hash != work_packet_hash
                    or existing.delivery_envelope_hash != delivery_envelope_hash
                    or existing.successor_run_input_brief_hash != brief_hash
                    or existing.successor_navigation_candidate_digest
                    != successor_candidate.candidate_digest
                    or existing.repair_target_ref != repair_target_ref
                    or existing.direct_user_capture_hash
                    != direct_user_capture_hash
                ):
                    raise OperationalError(
                        "run already has a different reframe disposition"
                    )
                digest = sha256_digest(canonical_json_bytes(existing))
                return (
                    RunReframeDispositionResultV1(
                        route_run_id=route_run_id,
                        disposition_hash=digest,
                        successor_run_input_brief_hash=brief_hash,
                        successor_navigation_candidate_digest=(
                            successor_candidate.candidate_digest
                        ),
                        repair_target_ref=repair_target_ref,
                    ),
                    False,
                )

            if (
                successor_run_input_brief.project_id != snapshot.project_id
                or successor_run_input_brief.base_head != snapshot.head
            ):
                raise OperationalError(
                    "successor brief is bound to a different project/head"
                )
            if (
                view.integrity != "valid"
                or view.base_freshness != "current"
                or view.lifecycle != "opened"
            ):
                raise OperationalError(
                    "only an exact valid current opened run can be disposed for reframe"
                )
            source_candidate = _read_candidate_binding(
                operational, route_run_id
            )
            if (
                source_candidate.key.route_id
                != "frame.question_and_benchmarks"
                or source_candidate.key.route_version != 2
                or source_candidate.key.focus_refs
            ):
                raise OperationalError(
                    "only an empty-focus framing v2 run can be disposed for reframe"
                )
            source_packet, _ = _validate_delivery(
                operational,
                route_run_id=route_run_id,
                work_packet_hash=work_packet_hash,
                delivery_envelope_hash=delivery_envelope_hash,
            )
            run = read_run(layout, route_run_id)
            run_hash = sha256_digest(canonical_json_bytes(run))
            if (
                source_packet.project_id != snapshot.project_id
                or source_packet.base_head != snapshot.head
                or source_packet.route_run_hash != run_hash
                or source_packet.navigation_candidate_digest
                != source_candidate.candidate_digest
                or source_packet.route_id != source_candidate.key.route_id
                or source_packet.route_version
                != source_candidate.key.route_version
                or source_packet.route_registry_hash
                != source_candidate.key.route_registry_hash
                or source_packet.focus_refs != source_candidate.key.focus_refs
            ):
                raise OperationalError("reframe packet has inconsistent bindings")
            if _has_completion_evidence(operational, route_run_id):
                raise OperationalError(
                    "a run with completion evidence cannot use untouched-run disposition"
                )
            if framing_team_is_active(
                operational,
                route_run_id=route_run_id,
                work_packet_hash=work_packet_hash,
            ):
                raise OperationalError(
                    "an activated framing team cannot use untouched-run disposition"
                )
            target_version = snapshot.current_entities.get(
                repair_target_ref.entity_id
            )
            if target_version != repair_target_ref.version:
                raise OperationalError("repair target is not the exact current version")

            legal, _ = enumerate_navigation_candidates(
                layout,
                snapshot,
                actor=successor_candidate.key.actor,
                compartments=successor_candidate.key.compartments,
                privacy_clearance=successor_candidate.key.privacy_clearance,
                budget_units=successor_candidate.key.context_budget,
                requested_route_ids=("repair.dependency",),
                run_input_brief=successor_run_input_brief,
            )
            matching = tuple(
                candidate
                for candidate in legal
                if repair_target_ref in candidate.key.focus_refs
            )
            if matching != (successor_candidate,):
                raise OperationalError(
                    "reframe does not bind one exact legal dependency repair candidate"
                )

            record = RunReframeDispositionV2(
                operation_key=operation_key,
                project_id=snapshot.project_id,
                head=snapshot.head,
                route_run_id=route_run_id,
                route_run_hash=run_hash,
                navigation_candidate_digest=source_candidate.candidate_digest,
                work_packet_hash=work_packet_hash,
                delivery_envelope_hash=delivery_envelope_hash,
                successor_run_input_brief_hash=brief_hash,
                successor_navigation_candidate_digest=(
                    successor_candidate.candidate_digest
                ),
                successor_run_input_brief=successor_run_input_brief,
                successor_navigation_candidate=successor_candidate,
                repair_target_ref=repair_target_ref,
                direct_user_capture_hash=direct_user_capture_hash,
                disposed_at=disposed_at,
            )
            data = canonical_json_bytes(record)
            mutated = write_immutable_operational(
                operational.project_root,
                _disposition_path(operational, route_run_id),
                data,
            )
            digest = sha256_digest(data)
            return (
                RunReframeDispositionResultV1(
                    route_run_id=route_run_id,
                    disposition_hash=digest,
                    successor_run_input_brief_hash=brief_hash,
                    successor_navigation_candidate_digest=(
                        successor_candidate.candidate_digest
                    ),
                    repair_target_ref=repair_target_ref,
                ),
                mutated,
            )


def valid_disposed_run_ids(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    views: Iterable[RunExecutionViewV1],
) -> frozenset[str]:
    disposed: set[str] = set()
    for view in views:
        record = read_run_reframe_disposition(
            operational, view.route_run_id
        )
        if record is None:
            continue
        _validate_source_bindings(layout, operational, view, record)
        disposed.add(view.route_run_id)
    return frozenset(disposed)


def pending_reframe_dispositions(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    views: Iterable[RunExecutionViewV1],
) -> tuple[RunReframeDispositionValue, ...]:
    view_tuple = tuple(views)
    disposed_ids = valid_disposed_run_ids(layout, operational, view_tuple)
    records = tuple(
        read_run_reframe_disposition(operational, route_run_id)
        for route_run_id in sorted(disposed_ids)
    )
    pending: list[RunReframeDispositionValue] = []
    for record in records:
        assert record is not None
        if not any(
            _successor_matches(layout, operational, view, record)
            for view in view_tuple
        ):
            pending.append(record)
    return tuple(pending)


def assert_reframe_successor_allowed(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    views: Iterable[RunExecutionViewV1],
    candidate: NavigationCandidateV1,
    run_input_brief: RunInputBriefV1 | None,
) -> None:
    pending = pending_reframe_dispositions(
        layout, operational, views
    )
    if not pending:
        return
    if len(pending) != 1:
        raise OperationalError("multiple pending reframe dispositions require repair")
    record = pending[0]
    actual_brief_hash = (
        None
        if run_input_brief is None
        else sha256_digest(canonical_json_bytes(run_input_brief))
    )
    if (
        candidate.candidate_digest
        != record.successor_navigation_candidate_digest
        or candidate.key.route_id != record.successor_route_id
        or candidate.key.base_head != record.head
        or record.repair_target_ref not in candidate.key.focus_refs
        or candidate.key.run_input_brief_hash
        != record.successor_run_input_brief_hash
        or actual_brief_hash != record.successor_run_input_brief_hash
    ):
        raise OperationalError(
            "pending reframe disposition requires its exact repair candidate and brief"
        )


def assert_run_not_disposed(
    operational: ProjectOperationalLayout, route_run_id: str
) -> None:
    if read_run_reframe_disposition(operational, route_run_id) is not None:
        raise OperationalError("disposed run cannot be resumed, delivered, or completed")


__all__ = [
    "RunReframeDispositionResultV1",
    "RunReframeDispositionV1",
    "RunReframeDispositionV2",
    "RunReframeDispositionValue",
    "assert_reframe_successor_allowed",
    "assert_run_not_disposed",
    "dispose_run_for_reframe",
    "pending_reframe_dispositions",
    "read_reframe_bridge_result_bytes",
    "read_run_reframe_disposition",
    "recoverable_reframe_successor",
    "valid_disposed_run_ids",
    "write_reframe_bridge_result_bytes",
]
