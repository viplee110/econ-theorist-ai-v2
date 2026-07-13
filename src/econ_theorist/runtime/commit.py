"""Atomic transaction commit orchestration for the Phase 1 local store.

The commit boundary is deliberately small: candidate bytes are prepared and
validated before the lock, while the lock protects the final head re-read,
immutable installation, and atomic head replacement.  Human-owned paths are
read only for reconciliation; this module never writes them.
"""

from __future__ import annotations

import hmac
import json
import secrets
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..codec import canonical_json_bytes, sha256_digest, transaction_bytes
from ..errors import RuntimeStoreError
from ..legacy_boundary import (
    snapshot_has_phase2_material,
    snapshot_has_phase3_material,
    snapshot_has_phase4_material,
    transaction_introduces_phase2_material,
    transaction_introduces_phase3_material,
    transaction_introduces_phase4_material,
)
from ..models import (
    ArtifactRegistration,
    ContextManifest,
    RegisterArtifactOp,
    Snapshot,
    Transaction,
)
from ..policy import (
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V3_HASH,
)
from .faults import inject_fault
from .layout import StoreLayout
from .lock import ExclusiveFileLock
from .objects import HeadStore, ObjectStore
from .render import write_snapshot, write_status_view


class CandidateError(RuntimeStoreError, ValueError):
    """A candidate cannot safely enter the commit protocol."""


class CandidateBaseError(CandidateError):
    """The candidate was not prepared against the current canonical head."""


class CandidateArtifactError(CandidateError):
    """Staged artifact bytes do not satisfy their canonical registration."""


class UnsafeHumanPath(CandidateError):
    """A human-owned logical path escapes the project working tree."""


class StoreNotVirginError(CandidateError):
    """A missing head cannot be treated as genesis because history traces exist."""


_PREPARED_SEAL_KEY = secrets.token_bytes(32)


@dataclass(frozen=True, slots=True)
class StagedArtifact:
    """One staged file identified by the registration it is intended to fill.

    Relative paths are interpreted below ``layout.staging_dir``.  A resolved
    staged path must remain below that directory, including through symlinks.
    """

    artifact_id: str
    version: int
    path: Path | str


@dataclass(frozen=True, slots=True)
class ReconciliationConflict:
    """Three-way hash evidence for a changed or missing human-owned file."""

    artifact_id: str
    version: int
    logical_path: str
    expected_base_hash: str
    working_hash: str | None
    proposed_hash: str
    working_state: Literal["changed", "missing", "unreadable"]


@dataclass(frozen=True, slots=True)
class PreparedArtifact:
    """Verified staged bytes captured before acquiring the commit lock."""

    registration: ArtifactRegistration
    staged_path: Path
    data: bytes


@dataclass(frozen=True, slots=True)
class PreparedProvenance:
    """One exact run/context object preserved by its transaction digest refs."""

    label: Literal["run", "manifest", "context"]
    digest: str
    data: bytes


@dataclass(frozen=True, slots=True)
class PreparedCandidate:
    """An in-process preflight token, not an independently trusted authority.

    ``_seal`` is process-local and excluded from ``__init__``.  Consequently a
    direct constructor or :func:`dataclasses.replace` cannot manufacture a new
    prepared token.  Commit still redoes every safety check under the lock; the
    seal only proves that these cached fields came from this process's
    preflight rather than being caller-assembled inputs.
    """

    store_root: Path
    transaction: Transaction
    transaction_bytes: bytes
    transaction_digest: str
    base_revision: str | None
    candidate_snapshot: Snapshot
    artifacts: tuple[PreparedArtifact, ...]
    provenance: tuple[PreparedProvenance, ...]
    reconciliation_conflicts: tuple[ReconciliationConflict, ...]
    _seal: bytes = field(default=b"", init=False, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class CommitResult:
    """Outcome of the serialized portion of the commit protocol."""

    status: Literal["committed", "stale_base"]
    transaction_digest: str
    head_before: str | None
    head_after: str | None
    snapshot: Snapshot | None
    reconciliation_conflicts: tuple[ReconciliationConflict, ...] = ()


def _prepared_seal_payload(prepared: PreparedCandidate) -> bytes:
    """Encode every cached field that could otherwise redirect a commit."""

    return canonical_json_bytes(
        {
            "store_root": str(prepared.store_root),
            "transaction_hash": sha256_digest(
                transaction_bytes(prepared.transaction)
            ),
            "transaction_bytes_hash": sha256_digest(
                prepared.transaction_bytes
            ),
            "transaction_digest": prepared.transaction_digest,
            "base_revision": prepared.base_revision,
            "candidate_snapshot_hash": sha256_digest(
                canonical_json_bytes(prepared.candidate_snapshot)
            ),
            "artifacts": tuple(
                {
                    "registration": artifact.registration,
                    "staged_path": str(artifact.staged_path),
                    "data_hash": sha256_digest(artifact.data),
                    "byte_size": len(artifact.data),
                }
                for artifact in prepared.artifacts
            ),
            "provenance": tuple(
                {
                    "label": item.label,
                    "digest": item.digest,
                    "data_hash": sha256_digest(item.data),
                    "byte_size": len(item.data),
                }
                for item in prepared.provenance
            ),
            "reconciliation_conflicts": tuple(
                {
                    "artifact_id": conflict.artifact_id,
                    "version": conflict.version,
                    "logical_path": conflict.logical_path,
                    "expected_base_hash": conflict.expected_base_hash,
                    "working_hash": conflict.working_hash,
                    "proposed_hash": conflict.proposed_hash,
                    "working_state": conflict.working_state,
                }
                for conflict in prepared.reconciliation_conflicts
            ),
        }
    )


def _seal_prepared(prepared: PreparedCandidate) -> PreparedCandidate:
    seal = hmac.digest(
        _PREPARED_SEAL_KEY,
        _prepared_seal_payload(prepared),
        "sha256",
    )
    object.__setattr__(prepared, "_seal", seal)
    return prepared


def _verify_prepared_seal(prepared: PreparedCandidate) -> None:
    if not isinstance(prepared, PreparedCandidate):
        raise CandidateError("commit_prepared requires a PreparedCandidate token")
    expected = hmac.digest(
        _PREPARED_SEAL_KEY,
        _prepared_seal_payload(prepared),
        "sha256",
    )
    if not prepared._seal or not hmac.compare_digest(prepared._seal, expected):
        raise CandidateError(
            "prepared candidate was not issued intact by this process's preflight"
        )


def _registered_artifacts(
    transaction: Transaction,
) -> dict[tuple[str, int], ArtifactRegistration]:
    registrations: dict[tuple[str, int], ArtifactRegistration] = {}
    for operation in transaction.operations:
        if not isinstance(operation, RegisterArtifactOp):
            continue
        registration = operation.artifact
        key = (registration.artifact_id, registration.version)
        if key in registrations:
            raise CandidateArtifactError(
                "a transaction cannot register the same artifact version twice: "
                f"{registration.artifact_id}@{registration.version}"
            )
        registrations[key] = registration
    return registrations


def _resolve_staged_path(layout: StoreLayout, value: Path | str) -> Path:
    staging_root = layout.staging_dir.resolve()
    path = Path(value)
    if not path.is_absolute():
        path = staging_root / path
    try:
        resolved = path.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise CandidateArtifactError(f"staged artifact is unavailable: {path}") from exc
    if not resolved.is_relative_to(staging_root):
        raise CandidateArtifactError(
            f"staged artifact escapes the staging directory: {resolved}"
        )
    if not resolved.is_file():
        raise CandidateArtifactError(f"staged artifact is not a file: {resolved}")
    return resolved


def _prepare_artifacts(
    layout: StoreLayout,
    transaction: Transaction,
    staged_artifacts: Iterable[StagedArtifact],
) -> tuple[PreparedArtifact, ...]:
    expected = _registered_artifacts(transaction)
    provided: dict[tuple[str, int], Path] = {}
    for staged in staged_artifacts:
        key = (staged.artifact_id, staged.version)
        if key in provided:
            raise CandidateArtifactError(
                f"duplicate staged artifact: {staged.artifact_id}@{staged.version}"
            )
        provided[key] = _resolve_staged_path(layout, staged.path)

    missing = sorted(set(expected) - set(provided))
    extra = sorted(set(provided) - set(expected))
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(
                "missing=" + ",".join(f"{item}@{version}" for item, version in missing)
            )
        if extra:
            details.append(
                "unregistered="
                + ",".join(f"{item}@{version}" for item, version in extra)
            )
        raise CandidateArtifactError(
            "staged artifact set mismatch: " + "; ".join(details)
        )

    prepared: list[PreparedArtifact] = []
    for key in sorted(expected):
        registration = expected[key]
        staged_path = provided[key]
        try:
            data = staged_path.read_bytes()
        except OSError as exc:
            raise CandidateArtifactError(
                f"cannot read staged artifact {staged_path}: {exc}"
            ) from exc
        actual_hash = sha256_digest(data)
        if actual_hash != registration.content_hash:
            raise CandidateArtifactError(
                f"artifact {registration.artifact_id}@{registration.version} "
                f"declares {registration.content_hash}, staged bytes hash to "
                f"{actual_hash}"
            )
        if len(data) != registration.byte_size:
            raise CandidateArtifactError(
                f"artifact {registration.artifact_id}@{registration.version} "
                f"declares {registration.byte_size} bytes, staged file has {len(data)}"
            )
        prepared.append(PreparedArtifact(registration, staged_path, data))
    return tuple(prepared)


def _human_working_path(layout: StoreLayout, logical_path: str) -> Path:
    relative = Path(logical_path)
    if relative.is_absolute() or relative.drive or ".." in relative.parts:
        raise UnsafeHumanPath(f"unsafe human-owned logical path: {logical_path!r}")
    project_root = layout.project_root.resolve()
    working_path = (project_root / relative).resolve(strict=False)
    if not working_path.is_relative_to(project_root):
        raise UnsafeHumanPath(f"human-owned path escapes project: {logical_path!r}")
    if working_path.is_relative_to(layout.store_root.resolve()):
        raise UnsafeHumanPath(
            f"human-owned path cannot target the runtime store: {logical_path!r}"
        )
    return working_path


def _working_hash(
    path: Path,
) -> tuple[str | None, Literal["present", "missing", "unreadable"]]:
    try:
        working_bytes = path.read_bytes()
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "unreadable"
    return sha256_digest(working_bytes), "present"


def _replacement_conflict(
    layout: StoreLayout,
    registration: ArtifactRegistration,
    expected_base_hash: str,
) -> ReconciliationConflict | None:
    assert registration.logical_path is not None
    working_path = _human_working_path(layout, registration.logical_path)
    working_hash, state = _working_hash(working_path)
    if state == "present" and working_hash == expected_base_hash:
        return None
    conflict_state: Literal["changed", "missing", "unreadable"] = (
        "changed" if state == "present" else state
    )
    return ReconciliationConflict(
        artifact_id=registration.artifact_id,
        version=registration.version,
        logical_path=registration.logical_path,
        expected_base_hash=expected_base_hash,
        working_hash=working_hash,
        proposed_hash=registration.content_hash,
        working_state=conflict_state,
    )


def _validate_human_artifacts(
    layout: StoreLayout,
    base_snapshot: Snapshot | None,
    artifacts: tuple[PreparedArtifact, ...],
) -> tuple[ReconciliationConflict, ...]:
    """Enforce baseline and replacement semantics without writing user files."""

    history = (
        {
            (artifact.artifact_id, artifact.version): artifact
            for artifact in base_snapshot.artifacts
        }
        if base_snapshot is not None
        else {}
    )
    conflicts: list[ReconciliationConflict] = []
    for prepared in artifacts:
        registration = prepared.registration
        if registration.version == 1:
            if not registration.human_owned:
                if (
                    registration.logical_path is not None
                    or registration.expected_base_hash is not None
                ):
                    raise CandidateArtifactError(
                        "non-human artifact baselines cannot bind a working path "
                        "or expected_base_hash"
                    )
                continue
            assert registration.logical_path is not None
            assert registration.expected_base_hash is not None
            conflict = _replacement_conflict(
                layout,
                registration,
                registration.expected_base_hash,
            )
            if conflict is not None:
                conflicts.append(conflict)
            continue

        assert registration.supersedes is not None
        previous = history.get(
            (
                registration.supersedes.artifact_id,
                registration.supersedes.version,
            )
        )
        if previous is None:
            raise CandidateArtifactError(
                "artifact replacement lacks its exact canonical predecessor"
            )
        if registration.human_owned != previous.human_owned:
            raise CandidateArtifactError(
                "artifact ownership cannot change across a version chain"
            )
        if registration.logical_path != previous.logical_path:
            raise CandidateArtifactError(
                "artifact logical_path cannot change across a version chain"
            )
        if not registration.human_owned:
            if (
                registration.logical_path is not None
                or registration.expected_base_hash is not None
            ):
                raise CandidateArtifactError(
                    "non-human artifact replacements cannot bind a working path "
                    "or expected_base_hash"
                )
            continue
        if registration.expected_base_hash != previous.content_hash:
            raise CandidateArtifactError(
                "human-owned replacement expected_base_hash must equal the "
                "exact predecessor content_hash"
            )
        conflict = _replacement_conflict(
            layout,
            registration,
            previous.content_hash,
        )
        if conflict is not None:
            conflicts.append(conflict)
    return tuple(conflicts)


def reconstruct_reconciliation_conflicts(
    layout: StoreLayout,
    snapshot: Snapshot,
) -> tuple[ReconciliationConflict, ...]:
    """Rebuild current human-file conflicts after a crash or process restart.

    H0 and H2 are canonical registration fields; H1 remains the untouched
    human working file.  This projection therefore needs no ephemeral commit
    result and never writes the working path.
    """

    versions = {
        (artifact.artifact_id, artifact.version): artifact
        for artifact in snapshot.artifacts
    }
    conflicts: list[ReconciliationConflict] = []
    for artifact_id, version in sorted(snapshot.current_artifacts.items()):
        registration = versions[(artifact_id, version)]
        if not registration.human_owned:
            continue
        if registration.version == 1:
            assert registration.expected_base_hash is not None
            expected = registration.expected_base_hash
        else:
            assert registration.supersedes is not None
            predecessor = versions[
                (
                    registration.supersedes.artifact_id,
                    registration.supersedes.version,
                )
            ]
            expected = predecessor.content_hash
            if registration.expected_base_hash != expected:
                raise CandidateArtifactError(
                    "canonical human artifact has an invalid predecessor baseline"
                )
        conflict = _replacement_conflict(layout, registration, expected)
        if conflict is not None:
            conflicts.append(conflict)
    return tuple(conflicts)


def _prepare_provenance(
    layout: StoreLayout, transaction: Transaction
) -> tuple[PreparedProvenance, ...]:
    if transaction.route_run_hash is None:
        return ()
    from ..runs import provenance_bytes, read_context, read_run

    try:
        data = provenance_bytes(layout, transaction.route_run_id)
        run = read_run(layout, transaction.route_run_id)
        manifest = read_context(layout, transaction.route_run_id)
    except RuntimeStoreError as exc:
        raise CandidateError(
            "candidate route/context provenance is missing or invalid"
        ) from exc
    if (
        run.route_run_id != transaction.route_run_id
        or run.project_id != transaction.project_id
        or run.base_revision != transaction.base_revision
        or run.route_id != transaction.route_id
        or run.actor != transaction.actor
        or run.context_hash != transaction.compiled_context_hash
        or manifest.context_manifest_id != run.context_manifest_id
        or manifest.source_head != transaction.base_revision
        or manifest.context_hash != transaction.compiled_context_hash
    ):
        raise CandidateError(
            "candidate transaction and live route/context provenance disagree"
        )
    from .replay import PrivacyFlowError, validate_route_context_output_flow

    try:
        context_payload = json.loads(data["context"].decode("utf-8"))
        validate_route_context_output_flow(transaction, context_payload)
    except (UnicodeDecodeError, json.JSONDecodeError, PrivacyFlowError) as exc:
        raise CandidateError(
            "candidate outputs violate their compiled-context privacy join"
        ) from exc
    expected = {
        "run": transaction.route_run_hash,
        "manifest": transaction.context_manifest_hash,
        "context": transaction.compiled_context_hash,
    }
    prepared: list[PreparedProvenance] = []
    for label in ("run", "manifest", "context"):
        digest = expected[label]
        assert digest is not None
        if sha256_digest(data[label]) != digest:
            raise CandidateError(
                f"candidate {label} provenance does not match its declared digest"
            )
        prepared.append(PreparedProvenance(label, digest, data[label]))
    return tuple(prepared)


def _bound_route_registry_hash(
    transaction: Transaction,
    provenance: tuple[PreparedProvenance, ...],
) -> str | None:
    """Extract the exact catalog identity already bound by the transaction."""

    if transaction.origin != "route_run":
        return None
    manifests = [item for item in provenance if item.label == "manifest"]
    if len(manifests) != 1:
        raise CandidateError("route candidate lacks one exact context manifest")
    item = manifests[0]
    if item.digest != transaction.context_manifest_hash:
        raise CandidateError("route candidate binds a different context manifest")
    try:
        manifest = ContextManifest.model_validate_json(item.data, strict=True)
    except ValueError as exc:
        raise CandidateError("route candidate manifest fails its strict schema") from exc
    if canonical_json_bytes(manifest) != item.data:
        raise CandidateError("route candidate manifest is not canonical JSON")
    return manifest.route_registry_hash


def _validate_live_registry_boundary(
    base_snapshot: Snapshot | None,
    transaction: Transaction,
    route_registry_hash: str | None,
) -> None:
    """Reject live policy downgrade without changing historical replay."""

    if route_registry_hash == ROUTE_REGISTRY_V1_HASH:
        if base_snapshot is not None and snapshot_has_phase2_material(base_snapshot):
            raise CandidateError(
                "frozen v1 routes are replay-only after Phase 2 material enters a project"
            )
        if transaction_introduces_phase2_material(
            transaction
        ) or transaction_introduces_phase3_material(
            transaction
        ) or transaction_introduces_phase4_material(transaction):
            raise CandidateError(
                "frozen v1 live writes cannot create or mutate packed Phase 2/3/4 "
                "entities or register blind candidate locks"
            )
        return
    if route_registry_hash == ROUTE_REGISTRY_V2_HASH:
        if base_snapshot is not None and snapshot_has_phase3_material(base_snapshot):
            raise CandidateError(
                "frozen v2 routes are replay-only after Phase 3 material enters a project"
            )
        if transaction_introduces_phase3_material(
            transaction
        ) or transaction_introduces_phase4_material(transaction):
            raise CandidateError(
                "frozen v2 live writes cannot create or mutate packed Phase 3/4 entities"
            )
        return
    if route_registry_hash == ROUTE_REGISTRY_V3_HASH:
        if base_snapshot is not None and snapshot_has_phase4_material(base_snapshot):
            raise CandidateError(
                "frozen v3 routes are replay-only after Phase 4 material enters a project"
            )
        if transaction_introduces_phase4_material(transaction):
            raise CandidateError(
                "frozen v3 live writes cannot create or mutate packed Phase 4 entities"
            )


def _revalidate_prepared_payloads(
    prepared: PreparedCandidate,
) -> None:
    body = transaction_bytes(prepared.transaction)
    digest = sha256_digest(body)
    if body != prepared.transaction_bytes or digest != prepared.transaction_digest:
        raise CandidateError(
            "prepared transaction object, canonical bytes, and digest disagree"
        )
    if (
        prepared.transaction.base_revision != prepared.base_revision
        or prepared.transaction.parent_transaction_hash != prepared.base_revision
    ):
        raise CandidateError("prepared transaction no longer binds its base revision")

    expected_artifacts = _registered_artifacts(prepared.transaction)
    actual_artifacts: dict[tuple[str, int], PreparedArtifact] = {}
    for artifact in prepared.artifacts:
        key = (
            artifact.registration.artifact_id,
            artifact.registration.version,
        )
        if key in actual_artifacts:
            raise CandidateArtifactError("prepared artifact appears more than once")
        actual_artifacts[key] = artifact
        if expected_artifacts.get(key) != artifact.registration:
            raise CandidateArtifactError(
                "prepared artifact registration differs from the transaction"
            )
        if (
            sha256_digest(artifact.data) != artifact.registration.content_hash
            or len(artifact.data) != artifact.registration.byte_size
        ):
            raise CandidateArtifactError(
                "prepared artifact bytes no longer match their registration"
            )
    if set(actual_artifacts) != set(expected_artifacts):
        raise CandidateArtifactError(
            "prepared artifact set differs from transaction registrations"
        )

    expected_provenance = {
        "run": prepared.transaction.route_run_hash,
        "manifest": prepared.transaction.context_manifest_hash,
        "context": prepared.transaction.compiled_context_hash,
    }
    actual_provenance: dict[str, PreparedProvenance] = {}
    for item in prepared.provenance:
        if item.label in actual_provenance:
            raise CandidateError("prepared provenance label appears more than once")
        actual_provenance[item.label] = item
        if expected_provenance.get(item.label) != item.digest:
            raise CandidateError(
                "prepared provenance digest differs from the transaction"
            )
        if sha256_digest(item.data) != item.digest:
            raise CandidateError("prepared provenance bytes fail their digest")
    required_labels = {
        label for label, digest in expected_provenance.items() if digest is not None
    }
    if set(actual_provenance) != required_labels:
        raise CandidateError(
            "prepared provenance set differs from transaction bindings"
        )


def _assert_virgin_store(layout: StoreLayout) -> None:
    evidence_paths = (
        layout.main_ref,
        layout.project_file,
        layout.latest_snapshot,
        layout.status_view,
    )
    if any(path.exists() for path in evidence_paths):
        raise StoreNotVirginError(
            "main is absent but project/snapshot/view evidence exists; "
            "refuse a second genesis and run recovery"
        )
    evidence_roots = (
        layout.transactions_root,
        layout.artifacts_root,
        layout.provenance_root,
        layout.runs_dir,
        layout.staging_dir,
        layout.quarantine_dir,
    )
    if any(
        path.is_file() or path.is_symlink()
        for root in evidence_roots
        if root.exists()
        for path in root.rglob("*")
    ):
        raise StoreNotVirginError(
            "main is absent but prior store objects or run traces exist; "
            "canonical history is ambiguous and genesis is forbidden"
        )


def _replay_api():
    # Lazy import keeps primitive modules usable while replay is bootstrapped and
    # avoids a commit/replay import cycle.
    from .replay import replay, validate_candidate

    return replay, validate_candidate


def preflight_candidate(
    layout: StoreLayout,
    transaction: Transaction,
    staged_artifacts: Iterable[StagedArtifact] = (),
) -> PreparedCandidate:
    """Capture artifact bytes and validate a candidate at one exact head.

    This function makes no canonical write.  It is intentionally separable
    from :func:`commit_prepared` so competing candidates may both validate at
    revision ``R`` and still receive an explicit ``stale_base`` result when
    only one can advance the head.
    """

    layout.ensure()
    body = transaction_bytes(transaction)
    digest = sha256_digest(body)
    head = HeadStore(layout).read()
    if transaction.base_revision != head or transaction.parent_transaction_hash != head:
        raise CandidateBaseError(
            f"candidate base {transaction.base_revision!r} does not match head {head!r}"
        )

    replay, validate_candidate = _replay_api()
    base_snapshot = None if head is None else replay(layout)
    if base_snapshot is not None and base_snapshot.head != head:
        raise CandidateBaseError(
            f"replay returned {base_snapshot.head}, expected pinned head {head}"
        )
    provenance = _prepare_provenance(layout, transaction)
    route_registry_hash = _bound_route_registry_hash(transaction, provenance)
    _validate_live_registry_boundary(
        base_snapshot, transaction, route_registry_hash
    )
    candidate_snapshot = validate_candidate(
        base_snapshot,
        transaction,
        route_registry_hash=route_registry_hash,
    )
    if candidate_snapshot.head != digest:
        raise CandidateError(
            "candidate validator returned a snapshot for a different transaction"
        )

    artifacts = _prepare_artifacts(layout, transaction, staged_artifacts)
    conflicts = _validate_human_artifacts(layout, base_snapshot, artifacts)
    inject_fault("after_staging")
    prepared = PreparedCandidate(
        store_root=layout.store_root.resolve(),
        transaction=transaction,
        transaction_bytes=body,
        transaction_digest=digest,
        base_revision=head,
        candidate_snapshot=candidate_snapshot,
        artifacts=artifacts,
        provenance=provenance,
        reconciliation_conflicts=conflicts,
    )
    return _seal_prepared(prepared)


def commit_prepared(
    layout: StoreLayout,
    prepared: PreparedCandidate,
    *,
    lock_timeout: float | None = None,
) -> CommitResult:
    """Install a prepared candidate and atomically advance ``refs/main``.

    Immutable objects can become unreachable orphans after a pre-head crash;
    they never become canonical state until the single head replacement.  A
    losing candidate installs nothing and is never automatically rebased.
    """

    layout.ensure()
    if not isinstance(prepared, PreparedCandidate):
        raise CandidateError("commit_prepared requires a PreparedCandidate token")

    objects = ObjectStore(layout)
    heads = HeadStore(layout)
    committed_snapshot: Snapshot | None = None
    conflicts: tuple[ReconciliationConflict, ...] = ()
    committed_digest: str | None = None
    committed_base: str | None = None
    with ExclusiveFileLock(layout.commit_lock, timeout=lock_timeout):
        _verify_prepared_seal(prepared)
        if prepared.store_root != layout.store_root.resolve():
            raise CandidateError(
                "prepared candidate belongs to a different project store"
            )
        _revalidate_prepared_payloads(prepared)

        # Detach the canonical transaction from the caller-owned object.  All
        # subsequent installs and the head update use these lock-local values,
        # never the PreparedCandidate's cached bytes or digest.
        canonical_body = transaction_bytes(prepared.transaction)
        transaction = Transaction.model_validate_json(
            canonical_body,
            strict=True,
        )
        canonical_body = transaction_bytes(transaction)
        digest = sha256_digest(canonical_body)
        base_revision = transaction.base_revision
        if transaction.parent_transaction_hash != base_revision:
            raise CandidateBaseError(
                "transaction parent no longer equals its base revision"
            )

        actual_head = heads.read()
        if actual_head != base_revision:
            return CommitResult(
                status="stale_base",
                transaction_digest=digest,
                head_before=actual_head,
                head_after=actual_head,
                snapshot=None,
                reconciliation_conflicts=prepared.reconciliation_conflicts,
            )

        if actual_head is None:
            _assert_virgin_store(layout)
        replay, validate_candidate = _replay_api()
        base_snapshot = None if actual_head is None else replay(layout)
        locked_provenance = _prepare_provenance(layout, transaction)
        route_registry_hash = _bound_route_registry_hash(
            transaction, locked_provenance
        )
        _validate_live_registry_boundary(
            base_snapshot, transaction, route_registry_hash
        )
        committed_snapshot = validate_candidate(
            base_snapshot,
            transaction,
            route_registry_hash=route_registry_hash,
        )
        if committed_snapshot.head != digest:
            raise CandidateError(
                "lock-time validation produced a different transaction digest"
            )
        if committed_snapshot != prepared.candidate_snapshot:
            raise CandidateError(
                "prepared candidate snapshot differs from lock-time validation"
            )
        # Prepared bytes are only a preflight cache.  Resolve and read every
        # staging/provenance source again while the canonical head is locked.
        staged_refs = tuple(
            StagedArtifact(
                artifact.registration.artifact_id,
                artifact.registration.version,
                artifact.staged_path,
            )
            for artifact in prepared.artifacts
        )
        locked_artifacts = _prepare_artifacts(
            layout,
            transaction,
            staged_refs,
        )
        if locked_artifacts != prepared.artifacts:
            raise CandidateArtifactError(
                "staged artifact bytes changed after candidate preflight"
            )
        if locked_provenance != prepared.provenance:
            raise CandidateError(
                "route/context provenance changed after candidate preflight"
            )
        conflicts = _validate_human_artifacts(
            layout,
            base_snapshot,
            locked_artifacts,
        )

        for artifact in locked_artifacts:
            objects.install_bytes(
                "artifacts",
                artifact.registration.content_hash,
                artifact.data,
            )
        for provenance in locked_provenance:
            objects.install_bytes("provenance", provenance.digest, provenance.data)

        # Apply exactly the invariant replay applies to reachable provenance.
        # It reads the just-installed content-addressed copies, not mutable run
        # workspace paths, and runs before the transaction can become reachable.
        from .replay import _validate_operational_provenance

        _validate_operational_provenance(layout, transaction, base_snapshot)
        inject_fault("after_artifact_installation")

        objects.install_bytes(
            "transactions",
            digest,
            canonical_body,
        )
        inject_fault("after_transaction_installation")
        heads.replace(base_revision, digest)
        committed_digest = digest
        committed_base = base_revision

    # Both files are disposable projections.  Reacquiring the commit lock keeps
    # an older committer from overwriting a newer head's cache after a race.  If
    # another transaction already won, its committer (or recover) owns refresh.
    with ExclusiveFileLock(layout.commit_lock, timeout=lock_timeout):
        assert committed_digest is not None
        if heads.read() == committed_digest:
            assert committed_snapshot is not None
            write_snapshot(layout, committed_snapshot)
            write_status_view(layout, committed_snapshot)
    return CommitResult(
        status="committed",
        transaction_digest=committed_digest,
        head_before=committed_base,
        head_after=committed_digest,
        snapshot=committed_snapshot,
        reconciliation_conflicts=conflicts,
    )


def commit_transaction(
    layout: StoreLayout,
    transaction: Transaction,
    staged_artifacts: Iterable[StagedArtifact] = (),
    *,
    lock_timeout: float | None = None,
) -> CommitResult:
    """Preflight and commit one transaction in a single convenience call."""

    prepared = preflight_candidate(layout, transaction, staged_artifacts)
    return commit_prepared(layout, prepared, lock_timeout=lock_timeout)
