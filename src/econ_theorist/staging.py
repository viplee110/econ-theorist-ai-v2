"""Preserve noncanonical run candidates and bind them to exact run context."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path

from .codec import canonical_json_bytes, sha256_digest, transaction_bytes
from .models import (
    RecordDecisionOp,
    RegisterArtifactOp,
    RouteRun,
    SupersedeDecisionOp,
    Transaction,
)
from .policy import AUTHORITY_RANK, route_spec
from .runs import (
    read_context,
    read_run,
    run_directory,
    safe_run_id,
    transaction_bindings,
)
from .runtime import StoreLayout, atomic_write_text, fsync_directory
from .runtime.commit import CommitResult, StagedArtifact, commit_transaction
from .runtime.layout import (
    UnsafeStorePath,
    assert_safe_store_path,
    path_entry_exists,
)


class StagingError(RuntimeError):
    """A candidate or proposed artifact cannot be staged without ambiguity."""


_DIGEST_RE = re.compile(r"[0-9a-f]{64}")


def _write_immutable(path: Path, data: bytes) -> None:
    try:
        assert_safe_store_path(
            path.parent, path, expected="file", allow_missing=True
        )
    except UnsafeStorePath as exc:
        raise StagingError(f"staged file path is unsafe: {path}") from exc
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        assert_safe_store_path(
            path.parent,
            path.parent,
            expected="directory",
            allow_missing=False,
        )
    except (OSError, UnsafeStorePath) as exc:
        raise StagingError(f"staged file directory is unsafe: {path.parent}") from exc

    if path_entry_exists(path):
        _verify_immutable_winner(path, data)
        return

    temp_path = _write_immutable_temp(path.parent, path.name, data)
    try:
        try:
            os.link(temp_path, path)
        except FileExistsError:
            _verify_immutable_winner(path, data)
            return
        except OSError as exc:
            if path_entry_exists(path):
                _verify_immutable_winner(path, data)
                return
            raise StagingError(
                f"cannot atomically publish staged file: {path}"
            ) from exc

        try:
            assert_safe_store_path(
                path.parent, path, expected="file", allow_missing=False
            )
            fsync_directory(path.parent)
        except (OSError, UnsafeStorePath) as exc:
            raise StagingError(f"cannot durably publish staged file: {path}") from exc
    finally:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass


def _write_immutable_temp(parent: Path, basename: str, data: bytes) -> Path:
    """Write and sync one ordinary same-directory publication candidate."""

    fd, raw_path = tempfile.mkstemp(prefix=f".{basename}.tmp-", dir=parent)
    temp_path = Path(raw_path)
    try:
        assert_safe_store_path(
            parent, temp_path, expected="file", allow_missing=False
        )
        with os.fdopen(fd, "wb", closefd=True) as stream:
            written = stream.write(data)
            if written != len(data):
                raise OSError("short write while staging immutable file")
            stream.flush()
            os.fsync(stream.fileno())
        return temp_path
    except BaseException:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _verify_immutable_winner(path: Path, data: bytes) -> None:
    try:
        assert_safe_store_path(
            path.parent, path, expected="file", allow_missing=False
        )
        existing = path.read_bytes()
    except (OSError, UnsafeStorePath) as exc:
        raise StagingError(f"cannot verify staged path: {path}") from exc
    if existing != data:
        raise StagingError(f"occupied staged path contains different bytes: {path}")


def _run_staging(layout: StoreLayout, route_run_id: str) -> Path:
    try:
        directory = layout.staging_dir / safe_run_id(route_run_id)
        return assert_safe_store_path(
            layout.staging_dir,
            directory,
            expected="directory",
            allow_missing=True,
        )
    except (UnsafeStorePath, RuntimeError) as exc:
        raise StagingError(f"unsafe staging run directory: {route_run_id!r}") from exc


def _assert_staging_target(layout: StoreLayout, path: Path) -> None:
    try:
        assert_safe_store_path(
            layout.staging_dir, path, expected="file", allow_missing=True
        )
    except UnsafeStorePath as exc:
        raise StagingError(
            f"staged target escapes or redirects the runtime staging root: {path}"
        ) from exc


def active_candidate_path(layout: StoreLayout, route_run_id: str) -> Path:
    return _run_staging(layout, route_run_id) / "active-candidate"


def candidate_object_path(
    layout: StoreLayout, route_run_id: str, digest: str
) -> Path:
    if not isinstance(digest, str) or _DIGEST_RE.fullmatch(digest) is None:
        raise StagingError(f"candidate digest is not canonical: {digest!r}")
    return _run_staging(layout, route_run_id) / "candidates" / f"{digest}.json"


def staged_artifact_path(
    layout: StoreLayout, route_run_id: str, content_hash: str
) -> Path:
    if not isinstance(content_hash, str) or _DIGEST_RE.fullmatch(content_hash) is None:
        raise StagingError(f"artifact digest is not canonical: {content_hash!r}")
    return _run_staging(layout, route_run_id) / "artifacts" / content_hash


def _load_transaction(path: str | Path) -> Transaction:
    try:
        data = Path(path).read_bytes()
        transaction = Transaction.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise StagingError(f"candidate transaction is unavailable or invalid: {path}") from exc
    if transaction_bytes(transaction) != data:
        # Human-authored pretty JSON is valid input, but the staged object is
        # always canonical. Rejecting it would add friction without integrity.
        data = transaction_bytes(transaction)
    return transaction


def _validate_route_ceiling(
    layout: StoreLayout, run: RouteRun, transaction: Transaction
) -> None:
    manifest = read_context(layout, run.route_run_id)
    from .policy import load_route_registry_by_hash

    route = route_spec(
        run.route_id,
        load_route_registry_by_hash(manifest.route_registry_hash),
    )
    if transaction.origin != "route_run":
        raise StagingError("scientific route candidates require origin=route_run")
    for operation in transaction.operations:
        if operation.op not in route.allowed_operations:
            raise StagingError(
                f"route {route.route_id} cannot propose operation {operation.op}"
            )
        if isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp)):
            decision = operation.decision
            if (
                decision.status != "proposed"
                and AUTHORITY_RANK[decision.required_authority]
                > AUTHORITY_RANK[route.authority_ceiling]
            ):
                raise StagingError(
                    f"route {route.route_id} ceiling {route.authority_ceiling} "
                    f"cannot exercise {decision.required_authority} Decision authority; "
                    "use the explicit human decide action"
                )


def _validate_provenance_binding(
    layout: StoreLayout, run: RouteRun, transaction: Transaction
) -> None:
    expected = transaction_bindings(layout, run.route_run_id)
    actual = {
        "route_run_hash": transaction.route_run_hash,
        "context_manifest_hash": transaction.context_manifest_hash,
        "compiled_context_hash": transaction.compiled_context_hash,
    }
    if actual != expected:
        raise StagingError(
            "candidate must bind the exact immutable route run, context "
            "manifest, and compiled context hashes"
        )


def stage_candidate(
    layout: StoreLayout,
    route_run_id: str,
    transaction_path: str | Path,
    *,
    artifacts: Mapping[str, str | Path] | None = None,
) -> str:
    """Stage one immutable candidate and its exact registered artifact bytes."""

    layout.ensure()
    run = read_run(layout, route_run_id)
    transaction = _load_transaction(transaction_path)
    if (
        transaction.route_run_id != run.route_run_id
        or transaction.project_id != run.project_id
        or transaction.base_revision != run.base_revision
        or transaction.actor != run.actor
    ):
        raise StagingError(
            "candidate must match the run ID, project, pinned head, and actor"
        )
    _validate_route_ceiling(layout, run, transaction)
    _validate_provenance_binding(layout, run, transaction)
    body = transaction_bytes(transaction)
    digest = sha256_digest(body)
    transaction_target = candidate_object_path(layout, route_run_id, digest)
    _assert_staging_target(layout, transaction_target)
    _write_immutable(transaction_target, body)

    sources = dict(artifacts or {})
    registrations = [
        operation.artifact
        for operation in transaction.operations
        if isinstance(operation, RegisterArtifactOp)
    ]
    expected_ids = {registration.artifact_id for registration in registrations}
    if set(sources) != expected_ids:
        raise StagingError(
            "artifact arguments must exactly match registrations; expected "
            + ", ".join(sorted(expected_ids))
        )
    for registration in registrations:
        source = Path(sources[registration.artifact_id])
        try:
            data = source.read_bytes()
        except OSError as exc:
            raise StagingError(f"cannot read proposed artifact: {source}") from exc
        if sha256_digest(data) != registration.content_hash:
            raise StagingError(
                f"proposed artifact {registration.artifact_id} does not match content_hash"
            )
        if len(data) != registration.byte_size:
            raise StagingError(
                f"proposed artifact {registration.artifact_id} does not match byte_size"
            )
        artifact_target = staged_artifact_path(
            layout, route_run_id, registration.content_hash
        )
        _assert_staging_target(layout, artifact_target)
        _write_immutable(artifact_target, data)

    active_target = active_candidate_path(layout, route_run_id)
    _assert_staging_target(layout, active_target)
    atomic_write_text(active_target, f"{digest}\n")
    return digest


def read_staged_transaction(
    layout: StoreLayout, route_run_id: str, digest: str | None = None
) -> Transaction:
    if digest is None:
        try:
            digest = active_candidate_path(layout, route_run_id).read_text(
                encoding="ascii"
            ).strip()
        except OSError as exc:
            raise StagingError("run has no active staged candidate") from exc
    path = candidate_object_path(layout, route_run_id, digest)
    _assert_staging_target(layout, path)
    try:
        data = path.read_bytes()
        transaction = Transaction.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise StagingError(f"invalid staged candidate {digest}") from exc
    if transaction_bytes(transaction) != data or sha256_digest(data) != digest:
        raise StagingError("staged candidate bytes or address were modified")
    return transaction


def commit_run(
    layout: StoreLayout,
    route_run_id: str,
    *,
    digest: str | None = None,
) -> CommitResult:
    """Commit one preserved candidate; never infer or rewrite its scientific scope."""

    run = read_run(layout, route_run_id)
    transaction = read_staged_transaction(layout, route_run_id, digest)
    if (
        transaction.route_run_id != run.route_run_id
        or transaction.base_revision != run.base_revision
        or transaction.actor != run.actor
    ):
        raise StagingError("staged candidate no longer matches its immutable run")
    _validate_route_ceiling(layout, run, transaction)
    _validate_provenance_binding(layout, run, transaction)
    staged: list[StagedArtifact] = []
    for operation in transaction.operations:
        if isinstance(operation, RegisterArtifactOp):
            artifact = operation.artifact
            staged.append(
                StagedArtifact(
                    artifact_id=artifact.artifact_id,
                    version=artifact.version,
                    path=staged_artifact_path(
                        layout, route_run_id, artifact.content_hash
                    ),
                )
            )
    result = commit_transaction(layout, transaction, staged)
    outcome = {
        "outcome_schema": "econ-theorist/run-outcome/v1",
        "route_run_id": route_run_id,
        "candidate_digest": result.transaction_digest,
        "status": result.status,
        "head_before": result.head_before,
        "head_after": result.head_after,
        "reconciliation_conflicts": [
            {
                "artifact_id": conflict.artifact_id,
                "version": conflict.version,
                "logical_path": conflict.logical_path,
                "expected_base_hash": conflict.expected_base_hash,
                "working_hash": conflict.working_hash,
                "proposed_hash": conflict.proposed_hash,
                "working_state": conflict.working_state,
            }
            for conflict in result.reconciliation_conflicts
        ],
    }
    path = (
        run_directory(layout, route_run_id)
        / "outcomes"
        / f"{result.transaction_digest}.json"
    )
    _write_immutable(path, canonical_json_bytes(outcome))
    return result
