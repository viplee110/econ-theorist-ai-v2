"""Concurrency-safe open/resume service for the machine facade."""

from __future__ import annotations

from pathlib import Path

from ..codec import canonical_json_bytes, sha256_digest
from ..runs import begin_run
from ..runtime.layout import StoreLayout
from ..runtime.lock import ExclusiveFileLock
from ..runtime.replay import replay
from .lifecycle import derive_all_run_execution_views, incomplete_run_views
from .disposition import (
    assert_reframe_successor_allowed,
    valid_disposed_run_ids,
)
from .models import NavigationCandidateV1, OpenRunResultV1, RunInputBriefV1
from .navigation import enumerate_navigation_candidates
from .operational import (
    OperationalError,
    ProjectOperationalLayout,
    write_immutable_operational,
)
from .packets import bind_run_input_brief, compile_work_packet


class ActiveRunConflict(OperationalError):
    """Existing incomplete work prevents an unambiguous open/resume."""


def _deterministic_ids(
    project_id: str, operation_key: str, candidate_digest: str
) -> tuple[str, str]:
    seed = sha256_digest(
        canonical_json_bytes(
            {
                "project_id": project_id,
                "operation_key": operation_key,
                "navigation_candidate_digest": candidate_digest,
            }
        )
    )
    return f"run_op_{seed[:48]}", f"ctx_op_{seed[:48]}"


def _candidate_binding_path(
    operational: ProjectOperationalLayout, route_run_id: str
) -> Path:
    return operational.runs / route_run_id / "navigation-candidate.json"


def _read_candidate_binding(
    operational: ProjectOperationalLayout, route_run_id: str
) -> NavigationCandidateV1 | None:
    path = _candidate_binding_path(operational, route_run_id)
    if not path.is_file():
        return None
    try:
        data = path.read_bytes()
        candidate = NavigationCandidateV1.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise ActiveRunConflict(
            f"invalid navigation binding for incomplete run {route_run_id}"
        ) from exc
    if canonical_json_bytes(candidate) != data:
        raise ActiveRunConflict(
            f"noncanonical navigation binding for incomplete run {route_run_id}"
        )
    return candidate


def _persist_candidate_binding(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    candidate: NavigationCandidateV1,
) -> None:
    write_immutable_operational(
        operational.project_root,
        _candidate_binding_path(operational, route_run_id),
        canonical_json_bytes(candidate),
    )


def _find_incomplete_match(
    operational: ProjectOperationalLayout,
    views: tuple[object, ...],
    candidate: NavigationCandidateV1,
) -> tuple[str | None, tuple[str, ...]]:
    incomplete = incomplete_run_views(views)  # type: ignore[arg-type]
    matches: list[str] = []
    unbound: list[str] = []
    for view in incomplete:
        binding = _read_candidate_binding(operational, view.route_run_id)
        if binding is None:
            unbound.append(view.route_run_id)
        elif binding == candidate:
            matches.append(view.route_run_id)
    if len(matches) > 1:
        raise ActiveRunConflict(
            "multiple incomplete runs have the same full navigation candidate key"
        )
    all_incomplete = tuple(view.route_run_id for view in incomplete)
    if unbound:
        raise ActiveRunConflict(
            "legacy or damaged incomplete runs lack exact navigation bindings: "
            + ", ".join(sorted(unbound))
        )
    if matches and len(all_incomplete) != 1:
        raise ActiveRunConflict(
            "several incomplete runs exist; explicit repair/disposition is required"
        )
    if not matches and all_incomplete:
        raise ActiveRunConflict(
            "another incomplete run owns navigation: "
            + ", ".join(sorted(all_incomplete))
        )
    return (matches[0] if matches else None), all_incomplete


def open_or_resume_run(
    layout: StoreLayout,
    *,
    operation_key: str,
    reserved_at: str,
    candidate: NavigationCandidateV1,
    run_input_brief: RunInputBriefV1 | None,
    operational: ProjectOperationalLayout | None = None,
    lock_timeout: float | None = None,
) -> OpenRunResultV1:
    """Resume one exact run or publish one new run under the fixed lock order.

    The caller must already hold the operation-key lock.  This function then
    takes navigation and canonical commit locks in that order, replays the head
    inside the innermost lock, re-authorizes the exact candidate, and only then
    publishes operational run bytes.
    """

    operational = operational or ProjectOperationalLayout.at(layout)
    operational.ensure()
    with ExclusiveFileLock(operational.navigation_lock, timeout=lock_timeout):
        # The commit lock is deliberately held through dry-run compilation and
        # publication.  It prevents commit-vs-open TOCTOU without teaching the
        # frozen canonical commit path about the navigation lock.
        with ExclusiveFileLock(layout.commit_lock, timeout=lock_timeout):
            snapshot = replay(layout)
            if snapshot.head != candidate.key.base_head:
                raise ActiveRunConflict(
                    "navigation candidate base is stale; inspect and plan again"
                )
            if run_input_brief is None and candidate.key.run_input_brief_hash is not None:
                raise ActiveRunConflict("candidate requires its exact run input brief")
            if run_input_brief is not None and (
                sha256_digest(canonical_json_bytes(run_input_brief))
                != candidate.key.run_input_brief_hash
            ):
                raise ActiveRunConflict("run input brief differs from candidate key")

            legal, _ = enumerate_navigation_candidates(
                layout,
                snapshot,
                actor=candidate.key.actor,
                compartments=candidate.key.compartments,
                privacy_clearance=candidate.key.privacy_clearance,
                budget_units=candidate.key.context_budget,
                requested_route_ids=(candidate.key.route_id,),
                run_input_brief=run_input_brief,
            )
            if candidate not in legal:
                raise ActiveRunConflict(
                    "exact navigation candidate no longer passes the current validator"
                )

            views = derive_all_run_execution_views(layout, snapshot)
            assert_reframe_successor_allowed(
                layout,
                operational,
                views,
                candidate,
                run_input_brief,
            )
            disposed_ids = valid_disposed_run_ids(
                layout, operational, views
            )
            active_views = tuple(
                view
                for view in views
                if view.route_run_id not in disposed_ids
            )
            matched_run_id, _ = _find_incomplete_match(
                operational, active_views, candidate
            )
            deterministic_run_id, context_id = _deterministic_ids(
                snapshot.project_id, operation_key, candidate.candidate_digest
            )
            if matched_run_id is None:
                route_run_id = deterministic_run_id
                status = "opened"
                _persist_candidate_binding(operational, route_run_id, candidate)
                if run_input_brief is not None:
                    bind_run_input_brief(
                        operational, route_run_id, candidate, run_input_brief
                    )
                begin_run(
                    layout,
                    snapshot,
                    route_id=candidate.key.route_id,
                    actor=candidate.key.actor,
                    purpose=candidate.key.purpose,
                    compartments=candidate.key.compartments,
                    privacy_clearance=candidate.key.privacy_clearance,
                    focus_entity_ids=tuple(
                        item.entity_id for item in candidate.key.focus_refs
                    ),
                    budget_units=candidate.key.context_budget,
                    route_run_id=route_run_id,
                    context_manifest_id=context_id,
                    created_at=reserved_at,
                    route_registry_hash=candidate.key.route_registry_hash,
                )
            else:
                route_run_id = matched_run_id
                status = "resumed"
                matched_view = next(
                    view
                    for view in active_views
                    if view.route_run_id == route_run_id
                )
                if matched_view.integrity == "invalid":
                    if route_run_id != deterministic_run_id:
                        raise ActiveRunConflict(
                            "a partial run from another operation cannot be recovered automatically"
                        )
                    # Exact-key retry completes an interrupted idempotent
                    # publication. Equal pre-existing bytes are accepted;
                    # edited or conflicting bytes fail inside begin_run.
                    begin_run(
                        layout,
                        snapshot,
                        route_id=candidate.key.route_id,
                        actor=candidate.key.actor,
                        purpose=candidate.key.purpose,
                        compartments=candidate.key.compartments,
                        privacy_clearance=candidate.key.privacy_clearance,
                        focus_entity_ids=tuple(
                            item.entity_id for item in candidate.key.focus_refs
                        ),
                        budget_units=candidate.key.context_budget,
                        route_run_id=route_run_id,
                        context_manifest_id=context_id,
                        created_at=reserved_at,
                        route_registry_hash=candidate.key.route_registry_hash,
                    )
                elif matched_view.base_freshness != "current":
                    raise ActiveRunConflict(
                        "the matching incomplete run is stale and requires disposition"
                    )
                if run_input_brief is not None:
                    bind_run_input_brief(
                        operational, route_run_id, candidate, run_input_brief
                    )

            packet_hash, _ = compile_work_packet(
                layout, operational, candidate, route_run_id
            )
            return OpenRunResultV1(
                status=status,
                route_run_id=route_run_id,
                navigation_candidate_digest=candidate.candidate_digest,
                work_packet_hash=packet_hash,
                candidate_logical_path=(
                    f".econ-theorist/staging/{route_run_id}/candidate.json"
                ),
            )


__all__ = ["ActiveRunConflict", "open_or_resume_run"]
