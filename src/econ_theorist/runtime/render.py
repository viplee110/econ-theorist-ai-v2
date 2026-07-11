"""Deterministic, explicitly noncanonical projections of a typed snapshot."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..codec import canonical_json_bytes
from ..models import FACET_ORDER, Snapshot
from .layout import StoreLayout
from .lock import ExclusiveFileLock
from .objects import (
    HeadChanged,
    HeadStore,
    atomic_write_bytes,
    atomic_write_text,
)


GENERATED_MARKER = "GENERATED"
NONCANONICAL_MARKER = "NONCANONICAL"


@dataclass(frozen=True, slots=True)
class RenderResult:
    """One status projection built from the head observed under the lock."""

    source_head: str
    path: Path


def _one_line(value: str) -> str:
    """Keep untrusted labels from changing the generated Markdown structure."""

    return " ".join(value.split()).replace("|", "\\|").replace("`", "'")


def render_status(snapshot: Snapshot) -> str:
    """Render one compact status page from canonical replay output only."""

    entity_index = {
        (entity.entity_id, entity.version): entity
        for entity in snapshot.entity_versions
    }
    decision_index = {
        (decision.decision_id, decision.version): decision
        for decision in snapshot.decisions
    }
    artifact_index = {
        (artifact.artifact_id, artifact.version): artifact
        for artifact in snapshot.artifacts
    }

    lines = [
        f"<!-- {GENERATED_MARKER}; {NONCANONICAL_MARKER}; edits have no authority -->",
        "# Theory project status",
        "",
        f"- source_head: `{snapshot.head}`",
        f"- project_id: `{snapshot.project_id}`",
        f"- committed_transactions: {len(snapshot.chain)}",
        f"- current_entities: {len(snapshot.current_entities)}",
        f"- effective_decisions: {len(snapshot.effective_decisions)}",
        f"- registered_artifacts: {len(snapshot.current_artifacts)}",
        "",
        "This file is a rebuildable view. Only transactions reachable from "
        "`.econ-theorist/refs/main` are canonical.",
    ]

    if snapshot.current_entities:
        lines.extend(
            [
                "",
                "## Current entities",
                "",
                "| Entity | Version | Type | Title | Acceptance | Freshness |",
                "|---|---:|---|---|---|---|",
            ]
        )
        for entity_id, version in sorted(snapshot.current_entities.items()):
            entity = entity_index[(entity_id, version)]
            derived = snapshot.derived_status.get(entity_id)
            acceptance = (
                derived.human_acceptance if derived is not None else "agent_proposed"
            )
            if derived is None or not derived.freshness:
                freshness = "unreported"
            else:
                freshness = ", ".join(
                    f"{facet}={derived.freshness[facet]}"
                    for facet in FACET_ORDER
                    if facet in derived.freshness
                )
            lines.append(
                "| `{}` | {} | `{}` | {} | `{}` | {} |".format(
                    entity_id,
                    version,
                    entity.entity_type,
                    _one_line(entity.title),
                    acceptance,
                    _one_line(freshness),
                )
            )

    if snapshot.effective_decisions:
        lines.extend(
            [
                "",
                "## Effective decisions",
                "",
                "| Decision key | Decision | Version | Status | Selected option |",
                "|---|---|---:|---|---|",
            ]
        )
        for key, reference in sorted(snapshot.effective_decisions.items()):
            decision = decision_index[(reference.decision_id, reference.version)]
            selected = decision.selected_option or "—"
            lines.append(
                "| {} | `{}` | {} | `{}` | {} |".format(
                    _one_line(key),
                    reference.decision_id,
                    reference.version,
                    decision.status,
                    _one_line(selected),
                )
            )

    if snapshot.current_artifacts:
        lines.extend(
            [
                "",
                "## Registered artifacts",
                "",
                "| Artifact | Version | Logical name | SHA-256 | Human-owned |",
                "|---|---:|---|---|---|",
            ]
        )
        for artifact_id, version in sorted(snapshot.current_artifacts.items()):
            artifact = artifact_index[(artifact_id, version)]
            lines.append(
                "| `{}` | {} | {} | `{}` | {} |".format(
                    artifact_id,
                    version,
                    _one_line(artifact.logical_name),
                    artifact.content_hash,
                    "yes" if artifact.human_owned else "no",
                )
            )

    if snapshot.blockers:
        lines.extend(
            [
                "",
                "## Recorded blockers",
                "",
                "| Severity | Blocker | Summary |",
                "|---|---|---|",
            ]
        )
        for blocker in sorted(snapshot.blockers, key=lambda item: item.blocker_id):
            lines.append(
                f"| `{blocker.severity}` | `{blocker.blocker_id}` | "
                f"{_one_line(blocker.summary)} |"
            )

    return "\n".join(lines) + "\n"


def write_snapshot(layout: StoreLayout, snapshot: Snapshot) -> Path:
    """Atomically replace the rebuildable typed snapshot cache.

    The caller must hold the commit lock.  The head guard makes accidental use
    of an older snapshot fail before it can replace a newer projection.
    """

    layout.ensure()
    actual_head = HeadStore(layout).read()
    if actual_head != snapshot.head:
        raise HeadChanged(snapshot.head, actual_head)
    atomic_write_bytes(
        layout.latest_snapshot,
        canonical_json_bytes(snapshot),
        after_replace_fault="after_snapshot_write",
    )
    return layout.latest_snapshot


def write_status_view(layout: StoreLayout, snapshot: Snapshot) -> Path:
    """Atomically replace the generated Markdown status projection.

    The caller must hold the commit lock.  See :func:`render_current` for the
    safe public regeneration path.
    """

    layout.ensure()
    actual_head = HeadStore(layout).read()
    if actual_head != snapshot.head:
        raise HeadChanged(snapshot.head, actual_head)
    atomic_write_text(
        layout.status_view,
        render_status(snapshot),
        after_replace_fault="after_view_write",
    )
    return layout.status_view


def render_current(
    layout: StoreLayout,
    *,
    lock_timeout: float | None = None,
) -> RenderResult:
    """Replay and render one current view while serializing against commits."""

    layout.ensure()
    with ExclusiveFileLock(layout.commit_lock, timeout=lock_timeout):
        # Import lazily so the replay module can use rendering primitives
        # without creating an import cycle.
        from .replay import replay

        snapshot = replay(layout)
        path = write_status_view(layout, snapshot)
        return RenderResult(source_head=snapshot.head, path=path)
