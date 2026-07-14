"""Compact read-only project inspection for machine hosts."""

from __future__ import annotations

from collections.abc import Iterable

from .. import __version__
from ..models import Actor, Snapshot
from ..policy import ROUTE_REGISTRY_HASH
from ..profile_craft_policy import CRAFT_CORPUS_V1_HASH, PROFILE_CATALOG_V1_HASH
from ..runtime.layout import StoreLayout
from ..runtime.replay import replay
from .lifecycle import (
    derive_all_run_execution_views,
    incomplete_run_views,
    resumable_run_views,
)
from .models import ProjectInspectionV1, RunInputBriefV1
from .navigation import plan_next
from .operational import ProjectOperationalLayout
from .resources import NAVIGATION_REGISTRY_HASH
from .resume import ResumeDescriptorError, derive_resume_descriptor


def inspect_project(
    layout: StoreLayout,
    *,
    actor: Actor,
    compartments: Iterable[str],
    privacy_clearance: str,
    budget_units: int | None = None,
    requested_route_ids: Iterable[str] | None = None,
    run_input_brief: RunInputBriefV1 | None = None,
    complete_if_none: bool = False,
    snapshot: Snapshot | None = None,
) -> ProjectInspectionV1:
    """Replay once and return a bounded state/navigation projection."""

    current = snapshot or replay(layout)
    views = derive_all_run_execution_views(layout, current)
    incomplete = incomplete_run_views(views)
    resumable = resumable_run_views(views)
    operational = ProjectOperationalLayout.at(layout)
    resume_descriptors = []
    for view in resumable:
        try:
            resume_descriptors.append(
                derive_resume_descriptor(layout, operational, view)
            )
        except ResumeDescriptorError:
            # Canonical run evidence can be intact while a noncanonical
            # navigation/packet sidecar is missing or corrupt.  Such a run is
            # not recoverable by inference and must enter explicit repair.
            continue
    resumable_ids = {
        item.route_run_id for item in resume_descriptors
    }
    repair_ids = tuple(
        item.route_run_id
        for item in incomplete
        if item.route_run_id not in resumable_ids
    )
    navigation = plan_next(
        layout,
        current,
        actor=actor,
        compartments=compartments,
        privacy_clearance=privacy_clearance,
        budget_units=budget_units,
        requested_route_ids=requested_route_ids,
        run_input_brief=run_input_brief,
        active_run_ids=tuple(sorted(resumable_ids)),
        resume_descriptors=tuple(resume_descriptors),
        repair_run_ids=repair_ids,
        complete_if_none=complete_if_none,
    )
    current_decisions = {
        (item.decision_id, item.version): item for item in current.decisions
    }
    pending = tuple(
        sorted(
            f"{decision_id}@{version}"
            for decision_id, version in current.current_decisions.items()
            if current_decisions[(decision_id, version)].status
            in {"proposed", "provisional"}
        )
    )
    return ProjectInspectionV1(
        project_id=current.project_id,
        head=current.head,
        engine_version=__version__,
        route_registry_hash=ROUTE_REGISTRY_HASH,
        navigation_registry_hash=NAVIGATION_REGISTRY_HASH,
        profile_catalog_hash=PROFILE_CATALOG_V1_HASH,
        craft_corpus_hash=CRAFT_CORPUS_V1_HASH,
        run_views=views,
        pending_decision_refs=pending,
        blocker_ids=tuple(sorted(item.blocker_id for item in current.blockers)),
        navigation=navigation,
    )


__all__ = ["inspect_project"]
