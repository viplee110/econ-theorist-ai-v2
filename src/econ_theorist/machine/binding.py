"""Authorized root binding and strict virgin-project initialization."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from ..codec import canonical_json_bytes, sha256_digest
from ..compatibility import CompatibilityProbeResult, probe_project_root
from ..project import ProjectInitializationError, initialize_virgin_project
from ..models import PrivacyLabel
from ..runtime.layout import (
    STORE_DIRECTORY,
    StoreLayout,
    UnsafeStorePath,
    assert_safe_store_path,
    path_entry_exists,
)
from ..runtime.lock import ExclusiveFileLock
from ..runtime.replay import replay
from .models import (
    CompatibilityProbeV1,
    DiagnosticV1,
    DiscoveryGrantV1,
    ProjectBindingV1,
)
from .operational import PreProjectOperationalLayout


class DiscoveryGrantError(RuntimeError):
    """The selected root cannot be proved unique inside the granted scope."""


def _absolute(value: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(Path(value).expanduser())))


def _is_reparse(path: Path) -> bool:
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & flag)


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def validate_discovery_grant(
    selected_root: str | Path, grant: DiscoveryGrantV1
) -> tuple[Path, Path]:
    """Validate exact selected/ancestor scope without scanning siblings."""

    selected = _absolute(selected_root)
    if not Path(grant.selected_root).is_absolute():
        raise DiscoveryGrantError("discovery grant selected_root must be absolute")
    if selected != _absolute(grant.selected_root):
        raise DiscoveryGrantError("request root differs from discovery grant")
    if grant.ancestor_check_boundary is None:
        raise DiscoveryGrantError(
            "ancestor_check_boundary is required to prove an unambiguous project root"
        )
    if not Path(grant.ancestor_check_boundary).is_absolute():
        raise DiscoveryGrantError("ancestor_check_boundary must be absolute")
    if not Path(grant.stable_workspace_root).is_absolute():
        raise DiscoveryGrantError("stable_workspace_root must be absolute")
    boundary = _absolute(grant.ancestor_check_boundary)
    workspace = _absolute(grant.stable_workspace_root)
    allowed = tuple(_absolute(item) for item in grant.allowed_discovery_roots)
    if any(not Path(item).is_absolute() for item in grant.allowed_discovery_roots):
        raise DiscoveryGrantError("all discovery roots must be absolute")
    if boundary != workspace:
        raise DiscoveryGrantError(
            "ancestor_check_boundary must equal the stable workspace root"
        )
    if not _within(selected, workspace):
        raise DiscoveryGrantError("selected root is outside the stable workspace root")
    covering = tuple(
        root
        for root in allowed
        if _within(workspace, root) and _within(selected, root)
    )
    if not covering:
        raise DiscoveryGrantError(
            "selected root and stable workspace are not jointly covered by a grant"
        )

    # The boundary cannot hide a reparse point in a parent component.  Walk
    # from the actual granted root through the selected path, including
    # dangling links, before any probe or mutation follows the pathname.
    try:
        for root in covering:
            assert_safe_store_path(
                root,
                selected,
                expected="directory",
                allow_missing=True,
            )
    except (FileNotFoundError, UnsafeStorePath) as exc:
        raise DiscoveryGrantError(str(exc)) from exc

    cursor = selected
    while True:
        if _is_reparse(cursor):
            raise DiscoveryGrantError(f"granted ancestor is a reparse point: {cursor}")
        if cursor != selected:
            store = cursor / STORE_DIRECTORY
            if path_entry_exists(store):
                raise DiscoveryGrantError(
                    f"selected root is nested inside another theory project: {cursor}"
                )
        if cursor == workspace:
            break
        parent = cursor.parent
        if parent == cursor:
            raise DiscoveryGrantError("ancestor boundary cannot be reached")
        cursor = parent
    return selected, workspace


def capture_project_root_identity(project_root: str | Path) -> tuple[int, int, int, int]:
    """Capture ordinary project/store directory identities for swap detection."""

    root = _absolute(project_root)
    store = root / STORE_DIRECTORY
    try:
        root_metadata = root.lstat()
        store_metadata = store.lstat()
    except FileNotFoundError as exc:
        raise DiscoveryGrantError(
            "project identity cannot be pinned because root/store is absent"
        ) from exc
    if (
        _is_reparse(root)
        or _is_reparse(store)
        or not stat.S_ISDIR(root_metadata.st_mode)
        or not stat.S_ISDIR(store_metadata.st_mode)
    ):
        raise DiscoveryGrantError("project root/store identity is not ordinary")
    return (
        int(root_metadata.st_dev),
        int(root_metadata.st_ino),
        int(store_metadata.st_dev),
        int(store_metadata.st_ino),
    )


def _capture_selected_directory_identity(project_root: Path) -> tuple[int, int]:
    try:
        metadata = project_root.lstat()
    except FileNotFoundError as exc:
        raise DiscoveryGrantError(
            "selected project directory must exist before binding"
        ) from exc
    if _is_reparse(project_root) or not stat.S_ISDIR(metadata.st_mode):
        raise DiscoveryGrantError("selected project root is not an ordinary directory")
    return int(metadata.st_dev), int(metadata.st_ino)


def _probe_model(probe: CompatibilityProbeResult) -> CompatibilityProbeV1:
    return CompatibilityProbeV1(
        classification=probe.classification,
        project_root=probe.project_root,
        store_root=probe.store_root,
        head=probe.head,
        project_id=probe.project_id,
        transaction_schema=probe.transaction_schema,
        chain_length=probe.chain_length,
        engine_version_hint=probe.engine_version_hint,
        compatible_engine_version=probe.compatible_engine_version,
        diagnostics=probe.diagnostics,
    )


def _blocked_binding(
    probe: CompatibilityProbeResult,
    *,
    status: str,
    diagnostic: DiagnosticV1 | None = None,
) -> ProjectBindingV1:
    return ProjectBindingV1(
        status=status,  # type: ignore[arg-type]
        project_root=probe.project_root,
        project_id=probe.project_id,
        head=probe.head,
        canonical_validation="not_run",
        probe=_probe_model(probe),
        mutated=False,
        diagnostics=() if diagnostic is None else (diagnostic,),
    )


def _deterministic_genesis_ids(
    project_root: Path,
    operation_key: str,
    project_name: str,
    project_privacy: PrivacyLabel = "project_private",
) -> tuple[str, str, str]:
    payload = {
        "project_root": str(project_root),
        "operation_key": operation_key,
        "project_name": project_name.strip(),
    }
    # Preserve every historical/default deterministic ID byte-for-byte.  An
    # explicit non-default privacy choice receives a distinct bound seed.
    if project_privacy != "project_private":
        payload["project_privacy"] = project_privacy
    seed = sha256_digest(canonical_json_bytes(payload))
    return (
        f"prj_{seed[:48]}",
        f"txn_init_{seed[:48]}",
        f"run_init_{seed[:48]}",
    )


def _canonical_project_name(snapshot: object) -> str:
    project_id = getattr(snapshot, "project_id")
    current_entities = getattr(snapshot, "current_entities")
    version = current_entities.get(project_id)
    matches = [
        entity
        for entity in getattr(snapshot, "entity_versions")
        if entity.entity_id == project_id and entity.version == version
    ]
    if len(matches) != 1 or matches[0].entity_type != "Project":
        raise ProjectInitializationError("canonical Project identity is malformed")
    return matches[0].title


def _canonical_project_privacy(snapshot: object) -> PrivacyLabel:
    project_id = getattr(snapshot, "project_id")
    current_entities = getattr(snapshot, "current_entities")
    version = current_entities.get(project_id)
    matches = [
        entity
        for entity in getattr(snapshot, "entity_versions")
        if entity.entity_id == project_id and entity.version == version
    ]
    if len(matches) != 1 or matches[0].entity_type != "Project":
        raise ProjectInitializationError("canonical Project identity is malformed")
    return matches[0].privacy


def bind_or_initialize_project(
    project_root: str | Path,
    *,
    discovery_grant: DiscoveryGrantV1,
    initialize: bool,
    project_name: str | None = None,
    project_privacy: PrivacyLabel = "project_private",
    actor_id: str = "local_human",
    requested_project_id: str | None = None,
    operation_key: str | None = None,
    reserved_at: str | None = None,
    operational_home: str | Path | None = None,
    lock_timeout: float | None = None,
) -> ProjectBindingV1:
    """Bind an existing compatible project or create exactly one genesis."""

    try:
        selected, _ = validate_discovery_grant(project_root, discovery_grant)
        selected_identity = _capture_selected_directory_identity(selected)
    except DiscoveryGrantError as exc:
        root = _absolute(project_root)
        probe = CompatibilityProbeResult(
            classification="absent",
            project_root=str(root),
            store_root=str(root / STORE_DIRECTORY),
            diagnostics=("root_scope_incomplete",),
        )
        return _blocked_binding(
            probe,
            status="root_scope_incomplete",
            diagnostic=DiagnosticV1(
                code="root_scope_incomplete",
                severity="error",
                message=str(exc),
            ),
        )

    probe = probe_project_root(selected, expected_project_id=requested_project_id)
    if probe.classification == "valid_existing":
        store_identity = capture_project_root_identity(selected)
        try:
            snapshot = replay(StoreLayout.at(selected))
        except (RuntimeError, ValueError, OSError) as exc:
            return ProjectBindingV1(
                status="corrupt",
                project_root=str(selected),
                project_id=probe.project_id,
                head=probe.head,
                canonical_validation="failed",
                probe=_probe_model(probe),
                mutated=False,
                diagnostics=(
                    DiagnosticV1(
                        code="canonical_validation_failed",
                        severity="error",
                        message=str(exc),
                    ),
                ),
            )
        if (
            snapshot.project_id != probe.project_id
            or snapshot.head != probe.head
            or capture_project_root_identity(selected) != store_identity
            or _capture_selected_directory_identity(selected) != selected_identity
        ):
            raise ProjectInitializationError(
                "read-only compatibility probe and canonical replay disagree"
            )
        name_conflict = (
            initialize
            and project_name is not None
            and _canonical_project_name(snapshot) != project_name.strip()
        )
        privacy_conflict = (
            initialize
            and project_name is not None
            and _canonical_project_privacy(snapshot) != project_privacy
        )
        if name_conflict or privacy_conflict:
            return _blocked_binding(
                probe,
                status="project_identity_conflict",
                diagnostic=DiagnosticV1(
                    code=(
                        "project_name_conflict"
                        if name_conflict
                        else "project_privacy_conflict"
                    ),
                    severity="error",
                    message=(
                        "the selected root already contains a differently named project"
                        if name_conflict
                        else "the selected root already contains a project with different privacy"
                    ),
                ),
            )
        return ProjectBindingV1(
            status="bound",
            project_root=str(selected),
            project_id=snapshot.project_id,
            head=snapshot.head,
            canonical_validation="valid",
            probe=_probe_model(probe),
            mutated=False,
        )

    if probe.classification in {"corrupt", "incompatible"}:
        return _blocked_binding(probe, status=probe.classification)
    if probe.classification == "recovery_required" and not initialize:
        return _blocked_binding(probe, status="recovery_required")
    if not initialize:
        return _blocked_binding(probe, status="project_initialization_required")
    if (
        project_name is None
        or not project_name.strip()
        or operation_key is None
        or reserved_at is None
    ):
        raise ProjectInitializationError(
            "initialization requires exact project name, operation key, and reservation time"
        )

    preproject = PreProjectOperationalLayout.for_project(
        selected, operational_home=operational_home
    ).ensure()
    with ExclusiveFileLock(preproject.initialization_lock, timeout=lock_timeout):
        # A different host/key may have initialized while this request waited.
        revalidated, _ = validate_discovery_grant(selected, discovery_grant)
        if (
            revalidated != selected
            or _capture_selected_directory_identity(selected) != selected_identity
        ):
            raise ProjectInitializationError(
                "selected project directory changed before initialization"
            )
        current = probe_project_root(selected, expected_project_id=requested_project_id)
        if current.classification == "valid_existing":
            store_identity = capture_project_root_identity(selected)
            snapshot = replay(StoreLayout.at(selected))
            if (
                capture_project_root_identity(selected) != store_identity
                or snapshot.project_id != current.project_id
                or snapshot.head != current.head
            ):
                raise ProjectInitializationError(
                    "concurrent project identity changed during replay"
                )
            name_conflict = _canonical_project_name(snapshot) != project_name.strip()
            privacy_conflict = (
                _canonical_project_privacy(snapshot) != project_privacy
            )
            if name_conflict or privacy_conflict:
                return _blocked_binding(
                    current,
                    status="project_identity_conflict",
                    diagnostic=DiagnosticV1(
                        code=(
                            "project_name_conflict"
                            if name_conflict
                            else "project_privacy_conflict"
                        ),
                        severity="error",
                        message=(
                            "a concurrent initializer created a differently named project"
                            if name_conflict
                            else "a concurrent initializer created a project with different privacy"
                        ),
                    ),
                )
            return ProjectBindingV1(
                status="bound",
                project_root=str(selected),
                project_id=snapshot.project_id,
                head=snapshot.head,
                canonical_validation="valid",
                probe=_probe_model(current),
                mutated=False,
            )
        if current.classification not in {
            "absent",
            "virgin",
            "recovery_required",
        }:
            return _blocked_binding(current, status=current.classification)

        project_id, transaction_id, route_run_id = _deterministic_genesis_ids(
            selected, operation_key, project_name, project_privacy
        )
        if requested_project_id is not None:
            project_id = requested_project_id
        try:
            snapshot = initialize_virgin_project(
                selected,
                name=project_name,
                actor_id=actor_id,
                project_id=project_id,
                created_at=reserved_at,
                transaction_id=transaction_id,
                route_run_id=route_run_id,
                project_privacy=project_privacy,
            )
        except ProjectInitializationError:
            if current.classification == "recovery_required":
                return _blocked_binding(current, status="recovery_required")
            raise
        post = probe_project_root(selected, expected_project_id=snapshot.project_id)
        if post.classification != "valid_existing" or post.head != snapshot.head:
            raise ProjectInitializationError(
                "post-initialization compatibility verification failed"
            )
        replayed = replay(StoreLayout.at(selected))
        if (
            replayed != snapshot
            or _capture_selected_directory_identity(selected) != selected_identity
        ):
            raise ProjectInitializationError(
                "post-initialization canonical replay differs from committed snapshot"
            )
        return ProjectBindingV1(
            status="initialized",
            project_root=str(selected),
            project_id=snapshot.project_id,
            head=snapshot.head,
            canonical_validation="valid",
            probe=_probe_model(post),
            mutated=True,
        )


__all__ = [
    "DiscoveryGrantError",
    "bind_or_initialize_project",
    "capture_project_root_identity",
    "validate_discovery_grant",
]
