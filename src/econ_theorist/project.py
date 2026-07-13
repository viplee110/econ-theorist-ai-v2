"""Project initialization and non-scientific local configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import __version__
from .codec import canonical_json_bytes, sha256_digest, transaction_bytes
from .ids import new_id, utc_now
from .models import (
    Actor,
    CreateEntityOp,
    EntityVersion,
    FacetPayloads,
    PrivacyLabel,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from .runtime import HeadStore, ObjectStore, StoreLayout, atomic_write_bytes
from .runtime.commit import commit_transaction
from .runtime.lock import ExclusiveFileLock
from .runtime.replay import replay, validate_candidate


class ProjectInitializationError(RuntimeError):
    """A local directory cannot be reconciled with one canonical Project."""


def _project_entity(snapshot: Snapshot) -> EntityVersion:
    versions = {
        (entity.entity_id, entity.version): entity
        for entity in snapshot.entity_versions
    }
    version = snapshot.current_entities.get(snapshot.project_id)
    if version is None:
        raise ProjectInitializationError(
            "canonical history has no current Project entity keyed by project_id"
        )
    entity = versions[(snapshot.project_id, version)]
    if entity.entity_type != "Project":
        raise ProjectInitializationError("project_id does not resolve to a Project entity")
    return entity


def _config(snapshot: Snapshot) -> dict[str, Any]:
    entity = _project_entity(snapshot)
    return {
        "config_schema": 1,
        "project_id": snapshot.project_id,
        "name": entity.title,
        "scope": "economic_theory_only",
        "engine_version": __version__,
    }


def write_project_config(layout: StoreLayout, snapshot: Snapshot) -> Path:
    """Rebuild the local config from canonical Project identity."""

    atomic_write_bytes(layout.project_file, canonical_json_bytes(_config(snapshot)))
    return layout.project_file


def read_project_config(layout: StoreLayout) -> dict[str, Any]:
    try:
        data = layout.project_file.read_bytes()
        value = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProjectInitializationError("project.json is missing or invalid") from exc
    if not isinstance(value, dict):
        raise ProjectInitializationError("project.json must be a JSON object")
    return value


def _genesis_transaction(
    *,
    name: str,
    actor_id: str,
    project_id: str,
    created_at: str,
    transaction_id: str,
    route_run_id: str,
    project_privacy: PrivacyLabel = "project_private",
) -> Transaction:
    actor = Actor(kind="human", actor_id=actor_id)
    entity = EntityVersion(
        entity_id=project_id,
        entity_type="Project",
        version=1,
        project_id=project_id,
        title=name.strip(),
        summary="A theory-only economic research project.",
        status=ScientificStatus(lifecycle="active"),
        facets=FacetPayloads(
            terminology_presentation={"project_name": name.strip()},
            authority={"scope": "economic_theory_only"},
        ),
        privacy=project_privacy,
        created_at=created_at,
    )
    return Transaction(
        transaction_id=transaction_id,
        origin="genesis",
        project_id=project_id,
        base_revision=None,
        route_run_id=route_run_id,
        actor=actor,
        intent="Initialize one theory-only project and canonical Project identity.",
        operations=(CreateEntityOp(entity=entity),),
        privacy=project_privacy,
        created_at=created_at,
        parent_transaction_hash=None,
    )


def _recover_exact_orphan_genesis(
    layout: StoreLayout, transaction: Transaction
) -> Snapshot | None:
    """Install a head only for the one exact retry-stable orphan genesis.

    A crash after immutable transaction installation but before head
    replacement is recoverable only when the store contains exactly the bytes
    this initialization operation had already validated.  Any additional
    history trace remains an explicit recovery case.
    """

    body = transaction_bytes(transaction)
    digest = sha256_digest(body)
    with ExclusiveFileLock(layout.commit_lock):
        current = HeadStore(layout).read()
        if current is not None:
            return replay(layout)
        target = ObjectStore(layout).path_for("transactions", digest)
        if not target.is_file():
            return None
        transaction_files = tuple(
            path
            for path in layout.transactions_root.rglob("*")
            if path.is_file()
        )
        forbidden_files = tuple(
            path
            for root in (
                layout.artifacts_root,
                layout.provenance_root,
                layout.runs_dir,
                layout.staging_dir,
                layout.quarantine_dir,
            )
            for path in root.rglob("*")
            if path.is_file()
        )
        if transaction_files != (target,) or forbidden_files:
            raise ProjectInitializationError(
                "headless store contains evidence beyond the exact orphan genesis"
            )
        if ObjectStore(layout).read_bytes("transactions", digest) != body:
            raise ProjectInitializationError(
                "orphan genesis bytes differ from the retry-stable transaction"
            )
        candidate = validate_candidate(None, transaction)
        if candidate.head != digest or candidate.chain != (digest,):
            raise ProjectInitializationError(
                "orphan genesis does not validate as a unique canonical root"
            )
        HeadStore(layout).replace(None, digest)
    snapshot = replay(layout)
    if snapshot.head != digest or snapshot.project_id != transaction.project_id:
        raise ProjectInitializationError(
            "recovered genesis replay differs from the expected transaction"
        )
    write_project_config(layout, snapshot)
    return snapshot


def init_project(
    project_root: str | Path,
    *,
    name: str,
    actor_id: str,
    project_id: str | None = None,
    created_at: str | None = None,
    transaction_id: str | None = None,
    route_run_id: str | None = None,
    project_privacy: PrivacyLabel = "project_private",
) -> Snapshot:
    """Idempotently create one human-owned theory project and genesis chain."""

    if not name or not name.strip():
        raise ProjectInitializationError("project name must be non-empty")
    layout = StoreLayout.at(project_root).ensure()
    if HeadStore(layout).read() is not None:
        snapshot = replay(layout)
        write_project_config(layout, snapshot)
        return snapshot

    identifier = project_id or new_id("prj")
    timestamp = created_at or utc_now()
    transaction = _genesis_transaction(
        name=name,
        actor_id=actor_id,
        project_id=identifier,
        created_at=timestamp,
        transaction_id=transaction_id or new_id("txn"),
        route_run_id=route_run_id or new_id("run_init"),
        project_privacy=project_privacy,
    )
    result = commit_transaction(layout, transaction)
    if result.status == "committed" and result.snapshot is not None:
        snapshot = result.snapshot
    else:
        # A concurrent initializer won. Never replace its head or rebase ours.
        snapshot = replay(layout)
    write_project_config(layout, snapshot)
    return snapshot


def initialize_virgin_project(
    project_root: str | Path,
    *,
    name: str,
    actor_id: str,
    project_id: str,
    created_at: str,
    transaction_id: str,
    route_run_id: str,
    project_privacy: PrivacyLabel = "project_private",
) -> Snapshot:
    """Initialize a probe-confirmed virgin root with retry-stable identifiers.

    Unlike the legacy convenience path, a concurrent existing winner is never
    used as permission to rewrite ``project.json``.  It is accepted only when
    its canonical identity and name exactly equal the requested genesis.
    """

    layout = StoreLayout.at(project_root).ensure()
    if HeadStore(layout).read() is not None:
        snapshot = replay(layout)
        entity = _project_entity(snapshot)
        if (
            snapshot.project_id != project_id
            or entity.title != name.strip()
            or entity.privacy != project_privacy
        ):
            raise ProjectInitializationError(
                "a concurrent genesis created a different project identity, name, or privacy"
            )
        return snapshot
    transaction = _genesis_transaction(
        name=name,
        actor_id=actor_id,
        project_id=project_id,
        created_at=created_at,
        transaction_id=transaction_id,
        route_run_id=route_run_id,
        project_privacy=project_privacy,
    )
    recovered = _recover_exact_orphan_genesis(layout, transaction)
    if recovered is not None:
        return recovered
    return init_project(
        project_root,
        name=name,
        actor_id=actor_id,
        project_id=project_id,
        created_at=created_at,
        transaction_id=transaction_id,
        route_run_id=route_run_id,
        project_privacy=project_privacy,
    )
