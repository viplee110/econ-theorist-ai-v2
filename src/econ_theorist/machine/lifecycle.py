"""Derived, noncanonical execution views for immutable RouteRun v1 records."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..codec import canonical_json_bytes, sha256_digest, transaction_bytes
from ..models import Snapshot, Transaction
from ..runs import (
    candidate_path,
    read_compiled_context,
    read_context,
    read_run,
    transaction_bindings,
)
from ..runtime.layout import StoreLayout, UnsafeStorePath, assert_safe_store_path
from ..runtime.objects import ObjectStore
from ..staging import active_candidate_path, read_staged_transaction
from .models import DiagnosticV1, RunExecutionViewV1


def _reachable_transactions(
    layout: StoreLayout, snapshot: Snapshot
) -> dict[str, tuple[str, Transaction]]:
    result: dict[str, tuple[str, Transaction]] = {}
    objects = ObjectStore(layout)
    for digest in snapshot.chain:
        data = objects.read_bytes("transactions", digest)
        transaction = Transaction.model_validate_json(data, strict=True)
        if transaction_bytes(transaction) != data:
            raise ValueError("reachable transaction is not canonical JSON")
        if transaction.origin != "route_run":
            continue
        previous = result.get(transaction.route_run_id)
        if previous is not None and previous[0] != digest:
            raise ValueError(
                f"canonical history repeats route_run_id {transaction.route_run_id}"
            )
        result[transaction.route_run_id] = (digest, transaction)
    return result


def _candidate_payload(
    layout: StoreLayout, route_run_id: str
) -> tuple[dict[str, Any], bytes]:
    path = candidate_path(layout, route_run_id)
    data = path.read_bytes()
    value = json.loads(data.decode("utf-8"))
    if not isinstance(value, dict) or canonical_json_bytes(value) != data:
        raise ValueError("candidate workspace is not canonical JSON")
    return value, data


def _candidate_has_progress(value: dict[str, Any]) -> bool:
    if value.get("candidate_transaction") is not None:
        return True
    if value.get("candidate_artifacts") not in ([], (), None):
        return True
    if str(value.get("rationale", "")).strip():
        return True
    for field in ("uncertainty", "unresolved_conflicts"):
        if value.get(field) not in ([], (), None):
            return True
    return value.get("recommended_next_route") is not None


def _valid_outcomes(
    layout: StoreLayout, route_run_id: str
) -> tuple[dict[str, Any], ...]:
    directory = layout.runs_dir / route_run_id / "outcomes"
    if not directory.exists():
        return ()
    assert_safe_store_path(
        layout.runs_dir, directory, expected="directory", allow_missing=False
    )
    outcomes: list[dict[str, Any]] = []
    for path in sorted(directory.iterdir(), key=lambda item: item.name):
        assert_safe_store_path(
            layout.runs_dir, path, expected="file", allow_missing=False
        )
        data = path.read_bytes()
        value = json.loads(data.decode("utf-8"))
        if not isinstance(value, dict) or canonical_json_bytes(value) != data:
            raise ValueError("run outcome is not canonical JSON")
        if (
            value.get("outcome_schema") != "econ-theorist/run-outcome/v1"
            or value.get("route_run_id") != route_run_id
            or value.get("status") not in {"committed", "stale_base"}
            or value.get("candidate_digest") != path.stem
            or not isinstance(value.get("candidate_digest"), str)
            or len(value["candidate_digest"]) != 64
        ):
            raise ValueError("run outcome fields are invalid")
        outcomes.append(value)
    return tuple(outcomes)


def _canonical_commit_view(
    layout: StoreLayout,
    snapshot: Snapshot,
    route_run_id: str,
    committed: tuple[str, Transaction],
) -> RunExecutionViewV1:
    digest, transaction = committed
    hashes = (
        transaction.route_run_hash,
        transaction.context_manifest_hash,
        transaction.compiled_context_hash,
    )
    if not all(isinstance(value, str) for value in hashes):
        raise ValueError("reachable route transaction lacks provenance hashes")
    objects = ObjectStore(layout)
    for provenance_hash in hashes:
        assert isinstance(provenance_hash, str)
        objects.read_bytes("provenance", provenance_hash)
    return RunExecutionViewV1(
        route_run_id=route_run_id,
        integrity="valid",
        base_freshness="not_applicable",
        lifecycle="committed",
        base_head=transaction.base_revision,
        current_head=snapshot.head,
        candidate_digest=digest,
        committed_transaction_digest=digest,
    )


def derive_run_execution_view(
    layout: StoreLayout,
    snapshot: Snapshot,
    route_run_id: str,
    *,
    reachable: dict[str, tuple[str, Transaction]] | None = None,
) -> RunExecutionViewV1:
    """Derive one mutually exclusive execution lifecycle without mutation."""

    canonical = reachable if reachable is not None else _reachable_transactions(
        layout, snapshot
    )
    committed = canonical.get(route_run_id)
    if committed is not None:
        try:
            return _canonical_commit_view(
                layout, snapshot, route_run_id, committed
            )
        except (OSError, RuntimeError, ValueError) as exc:
            return RunExecutionViewV1(
                route_run_id=route_run_id,
                integrity="invalid",
                base_freshness="unknown",
                lifecycle="unknown",
                base_head=committed[1].base_revision,
                current_head=snapshot.head,
                diagnostics=(
                    DiagnosticV1(
                        code="committed_provenance_invalid",
                        severity="error",
                        message=str(exc),
                    ),
                ),
            )

    try:
        run = read_run(layout, route_run_id)
        manifest = read_context(layout, route_run_id)
        read_compiled_context(layout, route_run_id)
        bindings = transaction_bindings(layout, route_run_id)
        if manifest.source_head != run.base_revision:
            raise ValueError("run/context base binding differs")
        outcomes = _valid_outcomes(layout, route_run_id)
        if any(item["status"] == "committed" for item in outcomes):
            raise ValueError("unreachable outcome falsely claims committed")
        stale_outcomes = tuple(
            item for item in outcomes if item["status"] == "stale_base"
        )
        freshness = "current" if run.base_revision == snapshot.head else "stale"
        if stale_outcomes:
            if len(stale_outcomes) != 1:
                raise ValueError("multiple immutable stale outcomes conflict")
            return RunExecutionViewV1(
                route_run_id=route_run_id,
                integrity="valid",
                base_freshness=freshness,
                lifecycle="commit_conflict",
                base_head=run.base_revision,
                current_head=snapshot.head,
                candidate_digest=stale_outcomes[-1]["candidate_digest"],
            )

        active_path = active_candidate_path(layout, route_run_id)
        if active_path.exists():
            transaction = read_staged_transaction(layout, route_run_id)
            expected = bindings
            actual = {
                "route_run_hash": transaction.route_run_hash,
                "context_manifest_hash": transaction.context_manifest_hash,
                "compiled_context_hash": transaction.compiled_context_hash,
            }
            if (
                transaction.route_run_id != route_run_id
                or transaction.project_id != run.project_id
                or transaction.base_revision != run.base_revision
                or transaction.actor != run.actor
                or actual != expected
            ):
                raise ValueError("active staged candidate does not bind the exact run")
            digest = sha256_digest(transaction_bytes(transaction))
            return RunExecutionViewV1(
                route_run_id=route_run_id,
                integrity="valid",
                base_freshness=freshness,
                lifecycle="staged",
                base_head=run.base_revision,
                current_head=snapshot.head,
                candidate_digest=digest,
            )

        candidate, candidate_bytes = _candidate_payload(layout, route_run_id)
        expected_bindings = {
            "route_run_hash": bindings["route_run_hash"],
            "context_manifest_hash": bindings["context_manifest_hash"],
            "compiled_context_hash": bindings["compiled_context_hash"],
        }
        if candidate.get("transaction_schema") == 1:
            transaction = Transaction.model_validate_json(
                candidate_bytes, strict=True
            )
            actual_bindings = {
                "route_run_hash": transaction.route_run_hash,
                "context_manifest_hash": transaction.context_manifest_hash,
                "compiled_context_hash": transaction.compiled_context_hash,
            }
            if (
                transaction_bytes(transaction) != candidate_bytes
                or transaction.origin != "route_run"
                or transaction.route_run_id != route_run_id
                or transaction.project_id != run.project_id
                or transaction.base_revision != run.base_revision
                or transaction.route_id != run.route_id
                or transaction.actor != run.actor
                or actual_bindings != expected_bindings
            ):
                raise ValueError(
                    "completed candidate transaction does not bind the exact run"
                )
            return RunExecutionViewV1(
                route_run_id=route_run_id,
                integrity="valid",
                base_freshness=freshness,
                lifecycle="candidate_present",
                base_head=run.base_revision,
                current_head=snapshot.head,
                candidate_digest=sha256_digest(candidate_bytes),
            )
        if (
            candidate.get("candidate_schema")
            != "econ-theorist/noncanonical-candidate/v1"
            or candidate.get("route_run_id") != route_run_id
            or candidate.get("base_revision") != run.base_revision
            or candidate.get("route_id") != run.route_id
            or candidate.get("context_hash") != run.context_hash
            or candidate.get("transaction_bindings") != expected_bindings
        ):
            raise ValueError("candidate workspace does not bind the exact run")
        lifecycle = "candidate_present" if _candidate_has_progress(candidate) else "opened"
        return RunExecutionViewV1(
            route_run_id=route_run_id,
            integrity="valid",
            base_freshness=freshness,
            lifecycle=lifecycle,
            base_head=run.base_revision,
            current_head=snapshot.head,
        )
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError, UnsafeStorePath) as exc:
        return RunExecutionViewV1(
            route_run_id=route_run_id,
            integrity="invalid",
            base_freshness="unknown",
            lifecycle="unknown",
            base_head=None,
            current_head=snapshot.head,
            diagnostics=(
                DiagnosticV1(
                    code="run_operational_integrity_invalid",
                    severity="error",
                    message=str(exc),
                ),
            ),
        )


def derive_all_run_execution_views(
    layout: StoreLayout, snapshot: Snapshot
) -> tuple[RunExecutionViewV1, ...]:
    """Return views for every reachable or locally present route run."""

    reachable = _reachable_transactions(layout, snapshot)
    run_ids = set(reachable)
    for root in (layout.runs_dir, layout.staging_dir):
        if not root.exists():
            continue
        try:
            assert_safe_store_path(
                layout.store_root, root, expected="directory", allow_missing=False
            )
            for entry in root.iterdir():
                if entry.is_dir():
                    run_ids.add(entry.name)
        except (OSError, UnsafeStorePath):
            run_ids.add("run_operational_root_invalid")
    return tuple(
        derive_run_execution_view(
            layout, snapshot, route_run_id, reachable=reachable
        )
        for route_run_id in sorted(run_ids)
    )


def incomplete_run_views(
    views: tuple[RunExecutionViewV1, ...]
) -> tuple[RunExecutionViewV1, ...]:
    return tuple(
        view
        for view in views
        if view.lifecycle
        in {"opened", "candidate_present", "staged", "commit_conflict", "unknown"}
    )


def resumable_run_views(
    views: tuple[RunExecutionViewV1, ...]
) -> tuple[RunExecutionViewV1, ...]:
    """Return only incomplete views a host can actually resume safely."""

    return tuple(
        view
        for view in views
        if view.integrity == "valid"
        and view.base_freshness == "current"
        and view.lifecycle in {"opened", "candidate_present", "staged"}
    )


__all__ = [
    "derive_all_run_execution_views",
    "derive_run_execution_view",
    "incomplete_run_views",
    "resumable_run_views",
]
