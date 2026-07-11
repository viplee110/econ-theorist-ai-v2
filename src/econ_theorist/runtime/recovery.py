"""Fail-closed recovery for one canonical local ``main`` head."""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from ..codec import (
    canonical_json_bytes,
    is_sha256_digest,
    sha256_digest,
    transaction_bytes,
)
from ..errors import RuntimeStoreError
from ..models import Snapshot, Transaction
from .layout import (
    StoreLayout,
    UnsafeStorePath,
    assert_safe_store_path,
    path_entry_exists,
)
from .lock import ExclusiveFileLock
from .objects import HeadFormatError, HeadStore, ObjectStore
from .render import write_snapshot, write_status_view


class RecoveryError(RuntimeStoreError):
    """Recovery cannot identify and replay one valid canonical head."""


class AmbiguousHeadError(RecoveryError):
    """The Phase 1 refs directory contains more than its single main head."""


class CorruptHeadError(RecoveryError):
    """The sole main pointer is malformed or not replayable."""


@dataclass(frozen=True, slots=True)
class OrphanReport:
    """Deterministic inventory of bytes not reachable from the canonical head."""

    transaction_digests: tuple[str, ...] = ()
    artifact_digests: tuple[str, ...] = ()
    provenance_digests: tuple[str, ...] = ()
    unrecognized_object_paths: tuple[str, ...] = ()
    run_paths: tuple[str, ...] = ()
    staging_paths: tuple[str, ...] = ()
    projection_paths: tuple[str, ...] = ()
    quarantine_paths: tuple[str, ...] = ()
    temporary_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GenesisResumeCandidate:
    """A syntactically and semantically valid, but noncanonical, genesis."""

    transaction_digest: str
    transaction_id: str
    project_id: str
    created_at: str


@dataclass(frozen=True, slots=True)
class RecoveryReport:
    """Result of replaying canonical history and rebuilding projections."""

    head: str | None
    canonical_head_count: int
    snapshot: Snapshot | None
    snapshot_hash: str | None
    orphans: OrphanReport
    recovery_state: str = "canonical"
    genesis_resume_candidates: tuple[GenesisResumeCandidate, ...] = ()
    recommended_action: str | None = None


def _relative(layout: StoreLayout, path: Path) -> str:
    try:
        return path.relative_to(layout.store_root).as_posix()
    except ValueError:
        return path.as_posix()


def _regular_files(root: Path) -> tuple[Path, ...]:
    """List leaf entries without traversing symlinks or reparse directories."""

    if not path_entry_exists(root):
        return ()
    assert_safe_store_path(
        root,
        root,
        expected="directory",
        allow_missing=False,
    )
    leaves: list[Path] = []
    pending = [root]
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    while pending:
        directory = pending.pop()
        try:
            entries = tuple(os.scandir(directory))
        except OSError as exc:
            raise RecoveryError(f"cannot scan runtime directory {directory}: {exc}") from exc
        for entry in entries:
            path = Path(entry.path)
            try:
                metadata = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise RecoveryError(f"cannot inspect runtime entry {path}: {exc}") from exc
            is_reparse = stat.S_ISLNK(metadata.st_mode) or bool(
                getattr(metadata, "st_file_attributes", 0) & reparse_flag
            )
            if is_reparse:
                leaves.append(path)
            elif stat.S_ISDIR(metadata.st_mode):
                pending.append(path)
            else:
                leaves.append(path)
    return tuple(sorted(leaves, key=lambda path: path.as_posix()))


def _ordinary_file(root: Path, path: Path) -> bool:
    try:
        assert_safe_store_path(
            root,
            path,
            expected="file",
            allow_missing=False,
        )
    except (FileNotFoundError, UnsafeStorePath):
        return False
    return True


def _read_unique_head(layout: StoreLayout) -> tuple[str | None, tuple[str, ...]]:
    """Read only ``refs/main``; temp files are orphans, not alternative heads."""

    assert_safe_store_path(
        layout.store_root,
        layout.refs_dir,
        expected="directory",
        allow_missing=False,
    )
    temporary: list[str] = []
    unexpected: list[str] = []
    for path in sorted(layout.refs_dir.iterdir(), key=lambda item: item.name):
        if path.name == "main":
            continue
        if path.name.startswith(".main.tmp-"):
            temporary.append(_relative(layout, path))
        else:
            unexpected.append(_relative(layout, path))
    if unexpected:
        raise AmbiguousHeadError(
            "single-head Phase 1 store contains unexpected refs: "
            + ", ".join(unexpected)
        )
    try:
        return HeadStore(layout).read(), tuple(temporary)
    except (HeadFormatError, UnsafeStorePath) as exc:
        raise CorruptHeadError(str(exc)) from exc


def _object_orphans(
    layout: StoreLayout,
    root: Path,
    reachable: set[str],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    digests: list[str] = []
    unrecognized: list[str] = []
    temporary: list[str] = []
    for path in _regular_files(root):
        relative = _relative(layout, path)
        name = path.name
        if not _ordinary_file(root, path):
            unrecognized.append(relative)
        elif name.startswith(".") and ".tmp-" in name:
            temporary.append(relative)
        elif is_sha256_digest(name):
            if name not in reachable:
                digests.append(name)
        else:
            unrecognized.append(relative)
    return tuple(sorted(digests)), tuple(sorted(unrecognized)), tuple(sorted(temporary))


def _collect_orphans(
    layout: StoreLayout,
    snapshot: Snapshot | None,
    ref_temporary: tuple[str, ...],
) -> OrphanReport:
    reachable_transactions = set(snapshot.chain) if snapshot is not None else set()
    reachable_artifacts = (
        {artifact.content_hash for artifact in snapshot.artifacts}
        if snapshot is not None
        else set()
    )
    reachable_provenance = (
        set(snapshot.provenance_hashes) if snapshot is not None else set()
    )
    transaction_digests, transaction_unknown, transaction_temp = _object_orphans(
        layout, layout.transactions_root, reachable_transactions
    )
    artifact_digests, artifact_unknown, artifact_temp = _object_orphans(
        layout, layout.artifacts_root, reachable_artifacts
    )
    provenance_digests, provenance_unknown, provenance_temp = _object_orphans(
        layout, layout.provenance_root, reachable_provenance
    )
    staging = tuple(
        _relative(layout, path) for path in _regular_files(layout.staging_dir)
    )
    runs = tuple(_relative(layout, path) for path in _regular_files(layout.runs_dir))
    quarantine = tuple(
        _relative(layout, path) for path in _regular_files(layout.quarantine_dir)
    )
    projection = tuple(
        _relative(layout, path)
        for directory in (layout.snapshots_dir, layout.views_dir)
        for path in _regular_files(directory)
        if not (path.name.startswith(".") and ".tmp-" in path.name)
    )
    projection_temp = tuple(
        _relative(layout, path)
        for directory in (layout.snapshots_dir, layout.views_dir)
        for path in _regular_files(directory)
        if path.name.startswith(".") and ".tmp-" in path.name
    )
    return OrphanReport(
        transaction_digests=transaction_digests,
        artifact_digests=artifact_digests,
        provenance_digests=provenance_digests,
        unrecognized_object_paths=tuple(
            sorted((*transaction_unknown, *artifact_unknown, *provenance_unknown))
        ),
        run_paths=tuple(sorted(runs)),
        staging_paths=tuple(sorted(staging)),
        projection_paths=(tuple(sorted(projection)) if snapshot is None else ()),
        quarantine_paths=tuple(sorted(quarantine)),
        temporary_paths=tuple(
            sorted(
                (
                    *ref_temporary,
                    *transaction_temp,
                    *artifact_temp,
                    *provenance_temp,
                    *projection_temp,
                )
            )
        ),
    )


def _verify_reachable_artifacts(layout: StoreLayout, snapshot: Snapshot) -> None:
    objects = ObjectStore(layout)
    checked: dict[str, int] = {}
    for registration in snapshot.artifacts:
        expected_size = checked.get(registration.content_hash)
        if expected_size is not None:
            if expected_size != registration.byte_size:
                raise RecoveryError(
                    "one content hash is registered with conflicting byte sizes: "
                    f"{registration.content_hash}"
                )
            continue
        data = objects.read_bytes("artifacts", registration.content_hash, verify=True)
        if len(data) != registration.byte_size:
            raise RecoveryError(
                f"artifact {registration.artifact_id}@{registration.version} has "
                f"{len(data)} bytes, registration requires {registration.byte_size}"
            )
        checked[registration.content_hash] = registration.byte_size


def _genesis_resume_candidates(
    layout: StoreLayout,
    transaction_digests: tuple[str, ...],
) -> tuple[GenesisResumeCandidate, ...]:
    """Identify valid pre-head genesis bytes without granting them authority."""

    from .replay import validate_candidate

    objects = ObjectStore(layout)
    candidates: list[GenesisResumeCandidate] = []
    for digest in transaction_digests:
        try:
            data = objects.read_bytes("transactions", digest, verify=True)
            transaction = Transaction.model_validate_json(data, strict=True)
            if transaction_bytes(transaction) != data:
                continue
            if transaction.origin != "genesis":
                continue
            snapshot = validate_candidate(None, transaction)
            if snapshot.head != digest:
                continue
        except Exception:
            # Every byte remains visible in the orphan inventory.  Candidate
            # classification is deliberately stricter and grants no authority.
            continue
        candidates.append(
            GenesisResumeCandidate(
                transaction_digest=digest,
                transaction_id=transaction.transaction_id,
                project_id=transaction.project_id,
                created_at=transaction.created_at,
            )
        )
    return tuple(sorted(candidates, key=lambda item: item.transaction_digest))


def _missing_head_diagnosis(
    layout: StoreLayout,
    orphans: OrphanReport,
) -> tuple[str, tuple[GenesisResumeCandidate, ...], str]:
    candidates = _genesis_resume_candidates(layout, orphans.transaction_digests)
    has_orphan_evidence = any(
        (
            orphans.transaction_digests,
            orphans.artifact_digests,
            orphans.provenance_digests,
            orphans.unrecognized_object_paths,
            orphans.run_paths,
            orphans.staging_paths,
            orphans.projection_paths,
            orphans.quarantine_paths,
            orphans.temporary_paths,
        )
    ) or path_entry_exists(layout.project_file)
    if len(candidates) == 1:
        return (
            "pre_head_genesis_candidate",
            candidates,
            "Do not edit refs/main or initialize a second genesis. Audit the "
            "reported candidate, then use a future explicit locked resume "
            "operation or quarantine the orphan evidence.",
        )
    if len(candidates) > 1:
        return (
            "ambiguous_pre_head_genesis",
            candidates,
            "No candidate was selected. Quarantine and audit every candidate "
            "before any explicit recovery decision.",
        )
    if has_orphan_evidence:
        return (
            "missing_head_with_orphans",
            (),
            "No resumable genesis was verified. Preserve and audit or quarantine "
            "the reported evidence before initialization.",
        )
    return (
        "virgin",
        (),
        "No canonical or orphan state was found; project initialization is safe.",
    )


def recover(
    layout: StoreLayout,
    *,
    lock_timeout: float | None = None,
) -> RecoveryReport:
    """Replay the unique head, verify artifacts, and rebuild disposable caches.

    A malformed, missing-target, or ambiguous head is never replaced with an
    orphan transaction.  With no canonical head, every immutable object is
    merely reported as orphaned and no snapshot is invented.
    """

    layout.ensure()
    with ExclusiveFileLock(layout.commit_lock, timeout=lock_timeout):
        head, ref_temporary = _read_unique_head(layout)
        if head is None:
            orphans = _collect_orphans(layout, None, ref_temporary)
            state, candidates, action = _missing_head_diagnosis(layout, orphans)
            return RecoveryReport(
                head=None,
                canonical_head_count=0,
                snapshot=None,
                snapshot_hash=None,
                orphans=orphans,
                recovery_state=state,
                genesis_resume_candidates=candidates,
                recommended_action=action,
            )

        try:
            from .replay import replay

            snapshot = replay(layout)
            if snapshot.head != head:
                raise CorruptHeadError(
                    f"replay returned {snapshot.head}, canonical head is {head}"
                )
            _verify_reachable_artifacts(layout, snapshot)
        except CorruptHeadError:
            raise
        except Exception as exc:
            # Recovery is the fail-closed boundary: a bad head or chain must not
            # be converted into a guessed replacement, and caches stay untouched.
            raise CorruptHeadError(
                f"canonical head {head} cannot be replayed and was left unchanged: {exc}"
            ) from exc

        orphans = _collect_orphans(layout, snapshot, ref_temporary)
        write_snapshot(layout, snapshot)
        write_status_view(layout, snapshot)
        return RecoveryReport(
            head=head,
            canonical_head_count=1,
            snapshot=snapshot,
            snapshot_hash=sha256_digest(canonical_json_bytes(snapshot)),
            orphans=orphans,
        )
