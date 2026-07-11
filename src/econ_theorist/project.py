"""Project initialization and non-scientific local configuration."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import __version__
from .codec import canonical_json_bytes
from .ids import new_id, utc_now
from .models import (
    Actor,
    CreateEntityOp,
    EntityVersion,
    FacetPayloads,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from .runtime import HeadStore, StoreLayout, atomic_write_bytes
from .runtime.commit import commit_transaction
from .runtime.replay import replay


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


def init_project(
    project_root: str | Path,
    *,
    name: str,
    actor_id: str,
    project_id: str | None = None,
    created_at: str | None = None,
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
    actor = Actor(kind="human", actor_id=actor_id)
    entity = EntityVersion(
        entity_id=identifier,
        entity_type="Project",
        version=1,
        project_id=identifier,
        title=name.strip(),
        summary="A theory-only economic research project.",
        status=ScientificStatus(lifecycle="active"),
        facets=FacetPayloads(
            terminology_presentation={"project_name": name.strip()},
            authority={"scope": "economic_theory_only"},
        ),
        created_at=timestamp,
    )
    transaction = Transaction(
        transaction_id=new_id("txn"),
        origin="genesis",
        project_id=identifier,
        base_revision=None,
        route_run_id=new_id("run_init"),
        actor=actor,
        intent="Initialize one theory-only project and canonical Project identity.",
        operations=(CreateEntityOp(entity=entity),),
        created_at=timestamp,
        parent_transaction_hash=None,
    )
    result = commit_transaction(layout, transaction)
    if result.status == "committed" and result.snapshot is not None:
        snapshot = result.snapshot
    else:
        # A concurrent initializer won. Never replace its head or rebase ours.
        snapshot = replay(layout)
    write_project_config(layout, snapshot)
    return snapshot
