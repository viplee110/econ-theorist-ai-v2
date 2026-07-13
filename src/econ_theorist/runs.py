"""Immutable operational route runs built from a pinned canonical snapshot."""

from __future__ import annotations

import json
import os
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from .codec import canonical_json_bytes, sha256_digest
from .context import compile_context, make_context_manifest, units_for_bytes
from .errors import IntegrityError, RuntimeStoreError
from .ids import new_id, utc_now
from .legacy_boundary import (
    snapshot_has_phase2_material,
    snapshot_has_phase3_material,
    snapshot_has_phase4_material,
)
from .authoring_validation import (
    AuthoringValidationError,
    validate_phase3_route_entry,
)
from .profile_craft_validation import (
    ProfileCraftValidationError,
    validate_phase4_route_entry,
)
from .models import (
    Actor,
    ContextManifest,
    PrivacyLabel,
    RouteRun,
    RouteSpecV2,
    RouteSpecV3,
    RouteSpecV4,
    Snapshot,
)
from .policy import (
    ISOLATION_POLICY,
    KERNEL_HASH,
    KERNEL_VERSION,
    VALIDATOR_VERSION,
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V3_HASH,
    V3_NATIVE_ROUTE_IDS,
    V4_NATIVE_ROUTE_IDS,
    decision_registry_version_for_route,
    instruction_bundle_bytes,
    registry_hash_for_route,
    selector_version_for_route,
)
from .route_registry import authorize_route, get_route, validate_privacy_clearance
from .theory_validation import TheoryValidationError, validate_phase2_route_entry
from .runtime.layout import StoreLayout, UnsafeStorePath, assert_safe_store_path
from .runtime.objects import HeadStore, fsync_directory


_FILE_ID_RE = re.compile(r"[a-z][a-z0-9._-]{0,127}")
_WINDOWS_RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))}
)
COMPILED_CONTEXT_FILENAME = "compiled-context.json"


class RunError(RuntimeStoreError):
    """An operational route-run record cannot be created or read safely."""


class RunBaseMismatch(RunError):
    """The supplied snapshot is not the project's current canonical head."""


class RouteEntryError(RunError):
    """The exact canonical base does not satisfy a v2 scientific entry contract."""


class ImmutableRunConflict(IntegrityError):
    """An immutable operational path already contains different bytes."""


def _safe_id(value: str, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or _FILE_ID_RE.fullmatch(value) is None
        or value.endswith((".", " "))
        or value.split(".", 1)[0] in _WINDOWS_RESERVED_NAMES
    ):
        raise RunError(f"unsafe {field}: {value!r}")
    return value


def safe_run_id(value: str) -> str:
    """Validate an identifier before it is used as a filesystem segment."""

    return _safe_id(value, field="route_run_id")


def run_directory(layout: StoreLayout, route_run_id: str) -> Path:
    """Return one run's operational directory without creating it."""

    path = layout.runs_dir / safe_run_id(route_run_id)
    try:
        return assert_safe_store_path(
            layout.runs_dir,
            path,
            expected="directory",
            allow_missing=True,
        )
    except UnsafeStorePath as exc:
        raise RunError(f"unsafe run directory: {path}") from exc


def run_path(layout: StoreLayout, route_run_id: str) -> Path:
    return run_directory(layout, route_run_id) / "run.json"


def context_path(layout: StoreLayout, route_run_id: str) -> Path:
    return run_directory(layout, route_run_id) / "context.json"


def compiled_context_path(layout: StoreLayout, route_run_id: str) -> Path:
    return run_directory(layout, route_run_id) / COMPILED_CONTEXT_FILENAME


def candidate_path(layout: StoreLayout, route_run_id: str) -> Path:
    """Return the fixed noncanonical staging candidate path."""

    directory = layout.staging_dir / safe_run_id(route_run_id)
    try:
        assert_safe_store_path(
            layout.staging_dir,
            directory,
            expected="directory",
            allow_missing=True,
        )
        return assert_safe_store_path(
            layout.staging_dir,
            directory / "candidate.json",
            expected="file",
            allow_missing=True,
        )
    except UnsafeStorePath as exc:
        raise RunError(f"unsafe staging run directory: {directory}") from exc


def _write_new(path: Path, data: bytes, *, immutable: bool) -> None:
    """Publish a new file without replacing a winner or existing user work."""

    try:
        assert_safe_store_path(
            path.parent, path, expected="file", allow_missing=True
        )
    except UnsafeStorePath as exc:
        raise RunError(f"operational file path is unsafe: {path}") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        fsync_directory(path.parent)
    except FileExistsError as exc:
        if immutable:
            try:
                existing = path.read_bytes()
            except OSError as read_exc:
                raise ImmutableRunConflict(
                    f"cannot verify occupied immutable run path: {path}"
                ) from read_exc
            if existing == data:
                return
            raise ImmutableRunConflict(
                f"immutable run path already contains different bytes: {path}"
            ) from exc
        raise RunError(f"staging candidate already exists: {path}") from exc
    except OSError as exc:
        raise RunError(f"cannot create operational file {path}: {exc}") from exc


def _read_immutable(path: Path) -> bytes:
    try:
        assert_safe_store_path(
            path.parent, path, expected="file", allow_missing=False
        )
    except (UnsafeStorePath, FileNotFoundError) as exc:
        raise RunError(f"immutable operational file is missing or unsafe: {path}") from exc
    try:
        return path.read_bytes()
    except FileNotFoundError as exc:
        raise RunError(f"operational run file does not exist: {path}") from exc
    except OSError as exc:
        raise RunError(f"cannot read operational run file {path}: {exc}") from exc


def _candidate_template(
    run: RouteRun,
    *,
    route_run_hash: str,
    context_manifest_hash: str,
) -> dict[str, Any]:
    return {
        "candidate_schema": "econ-theorist/noncanonical-candidate/v1",
        "markers": ("GENERATED", "NONCANONICAL"),
        "route_run_id": run.route_run_id,
        "base_revision": run.base_revision,
        "route_id": run.route_id,
        "context_hash": run.context_hash,
        "transaction_bindings": {
            "route_run_hash": route_run_hash,
            "context_manifest_hash": context_manifest_hash,
            "compiled_context_hash": run.context_hash,
        },
        "candidate_transaction": None,
        "candidate_artifacts": (),
        "rationale": "",
        "uncertainty": (),
        "unresolved_conflicts": (),
        "recommended_next_route": None,
    }


def begin_run(
    layout: StoreLayout,
    snapshot: Snapshot,
    *,
    route_id: str,
    actor: Actor,
    purpose: str,
    compartments: Iterable[str],
    privacy_clearance: str = "project_private",
    focus_entity_ids: Iterable[str] = (),
    budget_units: int = 4_000,
    route_run_id: str | None = None,
    context_manifest_id: str | None = None,
    created_at: str | None = None,
    route_registry_hash: str | None = None,
) -> RouteRun:
    """Compile and start an isolated route run at ``snapshot.head``.

    Compilation, authorization, head matching, and required-budget checks all
    finish before a ``running`` record is created.  Successful setup writes
    immutable ``runs/<run_id>/run.json`` and ``context.json`` records plus the
    compiled bytes, then creates the editable, noncanonical
    ``staging/<run_id>/candidate.json`` template.  It never writes ``refs/main``
    or any other canonical object.
    """

    if not isinstance(layout, StoreLayout):
        raise TypeError("layout must be a StoreLayout")
    if not isinstance(snapshot, Snapshot):
        raise TypeError("snapshot must be a Snapshot")
    if not isinstance(actor, Actor):
        raise TypeError("actor must be an Actor")
    if isinstance(compartments, str) or isinstance(focus_entity_ids, str):
        raise RunError("compartments and focus_entity_ids must be iterables")

    # A materialized Snapshot is only a cache hint.  The canonical transaction
    # chain is replayed and compared byte-for-byte before it can influence a
    # route context.
    from .runtime.replay import replay

    canonical_snapshot = replay(layout)
    if canonical_json_bytes(snapshot) != canonical_json_bytes(canonical_snapshot):
        raise RunBaseMismatch(
            "supplied snapshot is not the exact projection of the canonical chain"
        )
    snapshot = canonical_snapshot

    compartment_tuple = tuple(compartments)
    focus_tuple = tuple(focus_entity_ids)
    clearance: PrivacyLabel = validate_privacy_clearance(privacy_clearance)
    route = authorize_route(
        route_id,
        purpose=purpose,
        compartments=compartment_tuple,
        privacy_clearance=clearance,
        route_registry_hash=route_registry_hash,
    )
    if (
        registry_hash_for_route(route) == ROUTE_REGISTRY_V1_HASH
        and snapshot_has_phase2_material(snapshot)
    ):
        raise RouteEntryError(
            "frozen v1 routes are replay-only after Phase 2 material enters a project"
        )
    if (
        registry_hash_for_route(route) == ROUTE_REGISTRY_V2_HASH
        and snapshot_has_phase3_material(snapshot)
    ):
        raise RouteEntryError(
            "frozen v2 routes are replay-only after Phase 3 material enters a project"
        )
    if (
        registry_hash_for_route(route) == ROUTE_REGISTRY_V3_HASH
        and snapshot_has_phase4_material(snapshot)
    ):
        raise RouteEntryError(
            "frozen v3 routes are replay-only after Phase 4 material enters a project"
        )
    if isinstance(route, RouteSpecV4) and route.route_id in V4_NATIVE_ROUTE_IDS:
        try:
            validate_phase4_route_entry(snapshot, route, focus_tuple, actor=actor)
        except ProfileCraftValidationError as exc:
            raise RouteEntryError(
                f"Phase 4 route entry rejected {route.route_id}: {exc}"
            ) from exc
    elif isinstance(route, RouteSpecV3) and route.route_id in V3_NATIVE_ROUTE_IDS:
        try:
            validate_phase3_route_entry(snapshot, route, focus_tuple, actor=actor)
        except AuthoringValidationError as exc:
            raise RouteEntryError(
                f"Phase 3 route entry rejected {route.route_id}: {exc}"
            ) from exc
    elif isinstance(route, RouteSpecV2):
        try:
            validate_phase2_route_entry(
                snapshot, route, focus_tuple, actor=actor
            )
        except TheoryValidationError as exc:
            raise RouteEntryError(
                f"Phase 2 route entry rejected {route.route_id}: {exc}"
            ) from exc

    actual_head = HeadStore(layout).read()
    if actual_head != snapshot.head:
        raise RunBaseMismatch(
            f"snapshot head {snapshot.head!r} does not match canonical head "
            f"{actual_head!r}"
        )

    # Pure compilation happens before IDs, directories, staging, or a running
    # record.  Budget/access failure therefore cannot leave a running run.
    compiled = compile_context(
        snapshot,
        route=route,
        actor=actor,
        purpose=purpose,
        compartments=compartment_tuple,
        privacy_clearance=clearance,
        focus_entity_ids=focus_tuple,
        budget_units=budget_units,
        layout=layout,
    )

    run_id = route_run_id or new_id("run")
    manifest_id = context_manifest_id or new_id("ctx")
    timestamp = created_at or utc_now()
    manifest = make_context_manifest(
        compiled,
        context_manifest_id=manifest_id,
        snapshot=snapshot,
        route=route,
        actor=actor,
        purpose=purpose,
        compartments=compartment_tuple,
        privacy_clearance=clearance,
        focus_entity_ids=focus_tuple,
        budget_units=budget_units,
        created_at=timestamp,
    )
    run = RouteRun(
        route_run_id=run_id,
        project_id=snapshot.project_id,
        base_revision=snapshot.head,
        route_id=route.route_id,
        route_version=route.route_version,
        actor=actor,
        purpose=purpose,
        compartments=tuple(sorted(compartment_tuple)),
        privacy_clearance=clearance,
        focus_entity_ids=tuple(sorted(focus_tuple)),
        context_manifest_id=manifest.context_manifest_id,
        context_hash=manifest.context_hash,
        status="running",
        created_at=timestamp,
    )
    run_bytes = canonical_json_bytes(run)
    context_bytes = canonical_json_bytes(manifest)
    route_run_hash = sha256_digest(run_bytes)
    context_manifest_hash = sha256_digest(context_bytes)

    layout.ensure()
    # The running record is deliberately published last.  Any preceding fault
    # leaves inspectable noncanonical setup, never a run falsely marked running.
    _write_new(compiled_context_path(layout, run_id), compiled.encoded, immutable=True)
    _write_new(
        context_path(layout, run_id),
        context_bytes,
        immutable=True,
    )
    _write_new(
        candidate_path(layout, run_id),
        canonical_json_bytes(
            _candidate_template(
                run,
                route_run_hash=route_run_hash,
                context_manifest_hash=context_manifest_hash,
            )
        ),
        immutable=False,
    )
    _write_new(run_path(layout, run_id), run_bytes, immutable=True)
    return run


def read_run(layout: StoreLayout, route_run_id: str) -> RouteRun:
    """Read and strictly validate one immutable ``run.json``."""

    data = _read_immutable(run_path(layout, route_run_id))
    try:
        run = RouteRun.model_validate_json(data, strict=True)
    except ValueError as exc:
        raise RunError(f"invalid immutable run record: {route_run_id}") from exc
    if run.route_run_id != route_run_id:
        raise IntegrityError("run directory ID does not match run.json")
    if canonical_json_bytes(run) != data:
        raise IntegrityError("immutable run record is not canonical JSON")
    return run


def read_context(layout: StoreLayout, route_run_id: str) -> ContextManifest:
    """Read and strictly validate one immutable ``context.json`` manifest."""

    data = _read_immutable(context_path(layout, route_run_id))
    try:
        manifest = ContextManifest.model_validate_json(data, strict=True)
    except ValueError as exc:
        raise RunError(f"invalid immutable context manifest: {route_run_id}") from exc
    if canonical_json_bytes(manifest) != data:
        raise IntegrityError("immutable context manifest is not canonical JSON")
    run = read_run(layout, route_run_id)
    route = get_route(
        run.route_id, route_registry_hash=manifest.route_registry_hash
    )
    instruction_bundle_bytes(route)
    if (
        run.context_manifest_id != manifest.context_manifest_id
        or run.context_hash != manifest.context_hash
        or run.base_revision != manifest.source_head
        or run.project_id != manifest.project_id
        or run.route_id != manifest.route_id
        or run.route_version != manifest.route_version
        or run.actor != manifest.actor
        or run.purpose != manifest.purpose
        or run.compartments != manifest.compartments
        or run.privacy_clearance != manifest.privacy_clearance
        or run.focus_entity_ids != manifest.focus_entity_ids
    ):
        raise IntegrityError("run/context manifest binding does not match")
    if (
        manifest.decision_registry_version
        != decision_registry_version_for_route(route)
        or manifest.selector_version != selector_version_for_route(route)
        or manifest.kernel_version != KERNEL_VERSION
        or manifest.kernel_hash != KERNEL_HASH
        or manifest.validator_version != VALIDATOR_VERSION
        or manifest.instruction_bundle_id != route.instruction_bundle_id
        or manifest.instruction_bundle_hash != route.instruction_bundle_hash
        or manifest.isolation_policy != ISOLATION_POLICY
        or manifest.write_allowlist != route.allowed_operations
    ):
        raise IntegrityError("context manifest policy bindings do not match")
    return manifest


def read_compiled_context(
    layout: StoreLayout, route_run_id: str
) -> Mapping[str, Any]:
    """Read compiled context bytes and verify their manifest hash/canonical form."""

    data = _read_immutable(compiled_context_path(layout, route_run_id))
    manifest = read_context(layout, route_run_id)
    if sha256_digest(data) != manifest.context_hash:
        raise IntegrityError("compiled context bytes do not match context_hash")
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegrityError("compiled context is not valid UTF-8 JSON") from exc
    if canonical_json_bytes(payload) != data:
        raise IntegrityError("compiled context is not canonical JSON")
    if not isinstance(payload, dict):
        raise IntegrityError("compiled context must be a JSON object")
    if units_for_bytes(data) != manifest.used_units:
        raise IntegrityError("compiled context lexical usage does not match manifest")
    if payload.get("source_head") != manifest.source_head:
        raise IntegrityError("compiled context source head does not match manifest")
    return payload


def provenance_bytes(layout: StoreLayout, route_run_id: str) -> dict[str, bytes]:
    """Return verified immutable bytes for later content-addressed preservation."""

    run = read_run(layout, route_run_id)
    manifest = read_context(layout, route_run_id)
    read_compiled_context(layout, route_run_id)

    # Before canonical commit, reproduce the exact context from the canonical
    # base.  This prevents a hand-crafted but internally self-consistent run
    # workspace from entering the immutable transaction chain.
    from .runtime.replay import replay

    snapshot = replay(layout)
    if snapshot.head != run.base_revision:
        raise IntegrityError("route run base is no longer the canonical head")
    route = authorize_route(
        run.route_id,
        purpose=run.purpose,
        compartments=run.compartments,
        privacy_clearance=run.privacy_clearance,
        route_registry_hash=manifest.route_registry_hash,
    )
    if isinstance(route, RouteSpecV4) and route.route_id in V4_NATIVE_ROUTE_IDS:
        try:
            validate_phase4_route_entry(
                snapshot, route, run.focus_entity_ids, actor=run.actor
            )
        except ProfileCraftValidationError as exc:
            raise RouteEntryError(
                f"Phase 4 route entry no longer recompiles: {exc}"
            ) from exc
    elif isinstance(route, RouteSpecV3) and route.route_id in V3_NATIVE_ROUTE_IDS:
        try:
            validate_phase3_route_entry(
                snapshot, route, run.focus_entity_ids, actor=run.actor
            )
        except AuthoringValidationError as exc:
            raise RouteEntryError(
                f"Phase 3 route entry no longer recompiles: {exc}"
            ) from exc
    elif isinstance(route, RouteSpecV2):
        try:
            validate_phase2_route_entry(
                snapshot, route, run.focus_entity_ids, actor=run.actor
            )
        except TheoryValidationError as exc:
            raise RouteEntryError(
                f"Phase 2 route entry no longer recompiles: {exc}"
            ) from exc
    compiled = compile_context(
        snapshot,
        route=route,
        actor=run.actor,
        purpose=run.purpose,
        compartments=run.compartments,
        privacy_clearance=run.privacy_clearance,
        focus_entity_ids=run.focus_entity_ids,
        budget_units=manifest.budget_units,
        layout=layout,
    )
    expected_manifest = make_context_manifest(
        compiled,
        context_manifest_id=manifest.context_manifest_id,
        snapshot=snapshot,
        route=route,
        actor=run.actor,
        purpose=run.purpose,
        compartments=run.compartments,
        privacy_clearance=run.privacy_clearance,
        focus_entity_ids=run.focus_entity_ids,
        budget_units=manifest.budget_units,
        created_at=manifest.created_at,
    )
    expected_run = run.model_copy(
        update={"context_hash": compiled.context_hash}
    )
    if canonical_json_bytes(expected_manifest) != canonical_json_bytes(manifest):
        raise IntegrityError("context manifest cannot be reproduced from canonical base")
    if canonical_json_bytes(expected_run) != canonical_json_bytes(run):
        raise IntegrityError("route run cannot be reproduced from canonical base")
    compiled_bytes = _read_immutable(compiled_context_path(layout, route_run_id))
    if compiled.encoded != compiled_bytes:
        raise IntegrityError("compiled context cannot be reproduced from canonical base")
    return {
        "run": _read_immutable(run_path(layout, route_run_id)),
        "manifest": _read_immutable(context_path(layout, route_run_id)),
        "context": _read_immutable(compiled_context_path(layout, route_run_id)),
    }


def transaction_bindings(layout: StoreLayout, route_run_id: str) -> dict[str, str]:
    """Return the exact operational hashes a committed transaction must bind."""

    data = provenance_bytes(layout, route_run_id)
    return {
        "route_run_hash": sha256_digest(data["run"]),
        "context_manifest_hash": sha256_digest(data["manifest"]),
        "compiled_context_hash": sha256_digest(data["context"]),
    }


__all__ = [
    "COMPILED_CONTEXT_FILENAME",
    "ImmutableRunConflict",
    "RunBaseMismatch",
    "RunError",
    "begin_run",
    "candidate_path",
    "compiled_context_path",
    "context_path",
    "read_compiled_context",
    "read_context",
    "read_run",
    "provenance_bytes",
    "transaction_bindings",
    "run_directory",
    "run_path",
    "safe_run_id",
]
