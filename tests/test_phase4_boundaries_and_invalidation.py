"""Phase 4 catalog boundaries and selective-invalidation regressions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase4_profile_craft_models import directive, layer
from tests.test_phase4_profile_craft_validation import world

from econ_theorist import profile_craft as pc
from econ_theorist.codec import canonical_json_bytes
from econ_theorist.models import (
    Actor,
    CreateEntityOp,
    DecisionVersionRef,
    EffectiveDecisionRef,
    EntityVersion,
    EntityVersionRef,
    FacetPayloads,
    RouteSpecV3,
    RouteSpecV4,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from econ_theorist.policy import (
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V3_HASH,
    ROUTE_REGISTRY_V4_HASH,
    instruction_bundle_bytes,
    load_route_registry_by_hash,
    registry_hash_for_route,
    route_spec,
)
from econ_theorist.runs import RouteEntryError, begin_run
from econ_theorist.profile_craft_validation import (
    ProfileCraftValidationError,
    validate_profile_craft_ready,
)
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import (
    CandidateError,
    _validate_live_registry_boundary,
)
from econ_theorist.runtime.freshness import derive_entity_statuses
from econ_theorist.runtime.replay import validate_candidate


PROJECT = "project.phase4.boundaries"
HEAD = "9" * 64
NOW = "2026-07-12T16:00:00Z"
AGENT = Actor(kind="agent", actor_id="agent.phase4.boundary")


def _generic_entity(
    entity_id: str,
    entity_type: str,
    *,
    project_id: str = PROJECT,
    formal: object | None = None,
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=entity_type,
        version=1,
        project_id=project_id,
        title=f"Boundary fixture {entity_id}",
        summary="A minimal immutable catalog-boundary fixture.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=FacetPayloads(formal={} if formal is None else formal),
        created_at=NOW,
    )


def _legacy_transaction(snapshot: Snapshot) -> Transaction:
    note = _generic_entity(
        "note.historical.v1",
        "HistoricalResearchNote",
        project_id=snapshot.project_id,
        formal={"statement": "The exact historical note remains replayable."},
    )
    return Transaction(
        transaction_id="transaction.historical.v1",
        origin="route_run",
        project_id=snapshot.project_id,
        base_revision=snapshot.head,
        route_run_id="run.historical.v1",
        route_id="frame.question_and_benchmarks",
        route_run_hash="1" * 64,
        context_manifest_hash="2" * 64,
        compiled_context_hash="3" * 64,
        actor=AGENT,
        intent="Replay one frozen-v1 generic research note transaction.",
        operations=(CreateEntityOp(entity=note),),
        created_at=NOW,
        parent_transaction_hash=snapshot.head,
    )


def _minimal_phase4_snapshot() -> Snapshot:
    project = _generic_entity(PROJECT, "Project")
    marker_payload = layer(
        "profile.boundary.marker",
        "audience",
        "economic_theorist",
        (directive("directive.boundary.marker"),),
    )
    marker = EntityVersion(
        entity_id="profile.boundary.marker",
        entity_type=type(marker_payload).__name__,
        version=1,
        project_id=PROJECT,
        title="Phase 4 boundary marker",
        summary="A valid packed Phase 4 payload used to exercise historical replay.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=pc.pack_profile_craft_payload(marker_payload),
        created_at=NOW,
    )
    entities = (project, marker)
    current_entities = {item.entity_id: item.version for item in entities}
    derived = derive_entity_statuses(
        entity_versions=entities,
        relation_versions=(),
        decisions=(),
        current_entities=current_entities,
        current_relations={},
        effective_decisions={},
    )
    return Snapshot(
        project_id=PROJECT,
        head=HEAD,
        chain=(HEAD,),
        transaction_ids=("transaction.synthetic.phase4",),
        entity_versions=entities,
        current_entities=current_entities,
        derived_status=derived,
    )


class Phase4CatalogBoundaryTests(unittest.TestCase):
    def test_phase4_history_freezes_v1_v2_v3_live_entry_and_commit(self) -> None:
        snapshot, _entities = world()
        transaction = _legacy_transaction(snapshot)

        for registry_hash, phase in (
            (ROUTE_REGISTRY_V1_HASH, "v1"),
            (ROUTE_REGISTRY_V2_HASH, "v2"),
            (ROUTE_REGISTRY_V3_HASH, "v3"),
        ):
            with self.subTest(commit_catalog=phase), self.assertRaisesRegex(
                CandidateError, "replay-only"
            ):
                _validate_live_registry_boundary(
                    snapshot, transaction, registry_hash
                )

        # The active catalog is not a downgrade even when it dispatches a copied
        # Phase 1-3 route. Its route-specific validator remains authoritative.
        _validate_live_registry_boundary(
            snapshot, transaction, ROUTE_REGISTRY_V4_HASH
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            layout = StoreLayout.at(root)
            with mock.patch(
                "econ_theorist.runtime.replay.replay", return_value=snapshot
            ):
                for registry_hash, phase in (
                    (ROUTE_REGISTRY_V1_HASH, "v1"),
                    (ROUTE_REGISTRY_V2_HASH, "v2"),
                    (ROUTE_REGISTRY_V3_HASH, "v3"),
                ):
                    with self.subTest(entry_catalog=phase), self.assertRaisesRegex(
                        RouteEntryError, "replay-only"
                    ):
                        begin_run(
                            layout,
                            snapshot,
                            route_id="frame.question_and_benchmarks",
                            actor=AGENT,
                            purpose="research_framing",
                            compartments=("project_research",),
                            focus_entity_ids=(snapshot.project_id,),
                            route_registry_hash=registry_hash,
                        )
            self.assertFalse((root / "runs").exists())

    def test_v4_copies_frozen_v3_route_bytes_but_binds_active_catalog(self) -> None:
        route_id = "close.manuscript_review"
        frozen_v3 = route_spec(
            route_id, load_route_registry_by_hash(ROUTE_REGISTRY_V3_HASH)
        )
        active_v4 = route_spec(
            route_id, load_route_registry_by_hash(ROUTE_REGISTRY_V4_HASH)
        )

        self.assertIsInstance(frozen_v3, RouteSpecV3)
        self.assertNotIsInstance(frozen_v3, RouteSpecV4)
        self.assertIsInstance(active_v4, RouteSpecV4)
        self.assertEqual(active_v4.route_version, 3)
        self.assertEqual(
            active_v4.model_dump(mode="json"), frozen_v3.model_dump(mode="json")
        )
        self.assertEqual(
            instruction_bundle_bytes(active_v4), instruction_bundle_bytes(frozen_v3)
        )
        self.assertEqual(registry_hash_for_route(frozen_v3), ROUTE_REGISTRY_V3_HASH)
        self.assertEqual(registry_hash_for_route(active_v4), ROUTE_REGISTRY_V4_HASH)

    def test_historical_v1_validator_replays_after_phase4_without_rewriting_bytes(self) -> None:
        snapshot = _minimal_phase4_snapshot()
        transaction = _legacy_transaction(snapshot)
        before = {
            (item.entity_id, item.version): canonical_json_bytes(item)
            for item in snapshot.entity_versions
        }

        # validate_candidate is the deterministic replay primitive. Live writes
        # pass through the separate boundary above before reaching this layer.
        replayed = validate_candidate(
            snapshot,
            transaction,
            route_registry_hash=ROUTE_REGISTRY_V1_HASH,
        )

        self.assertEqual(replayed.current_entities["note.historical.v1"], 1)
        for reference, exact_bytes in before.items():
            current = next(
                item
                for item in replayed.entity_versions
                if (item.entity_id, item.version) == reference
            )
            self.assertEqual(canonical_json_bytes(current), exact_bytes)


class Phase4SelectiveInvalidationTests(unittest.TestCase):
    def test_overlay_decision_change_invalidates_phase4_ready_only_without_rewrites(self) -> None:
        snapshot, entities = world()
        venue_v1 = next(
            item
            for item in snapshot.decisions
            if item.decision_kind == "venue_overlay"
        )
        venue_v2 = venue_v1.model_copy(
            update={
                "version": 2,
                "selected_option": "revise",
                "rationale": "The human owner changes the active venue overlay target.",
                "supersedes": DecisionVersionRef(
                    decision_id=venue_v1.decision_id,
                    version=venue_v1.version,
                ),
                "decided_at": "2026-07-12T16:01:00Z",
            }
        )
        project = _generic_entity(
            snapshot.project_id, "Project", project_id=snapshot.project_id
        )
        old_phase1_to_3 = (
            project,
            *(
                item
                for item in snapshot.entity_versions
                if item.entity_type not in pc.PROFILE_CRAFT_PAYLOAD_MODELS
            ),
        )
        old_bytes = {
            (item.entity_id, item.version): canonical_json_bytes(item)
            for item in old_phase1_to_3
        }
        all_entities = (project, *snapshot.entity_versions)
        current_entities = {
            item.entity_id: item.version for item in all_entities
        }
        current_decisions = dict(snapshot.current_decisions)
        current_decisions[venue_v2.decision_id] = venue_v2.version
        effective_decisions = dict(snapshot.effective_decisions)
        effective_decisions["venue_overlay"] = EffectiveDecisionRef(
            decision_id=venue_v2.decision_id,
            version=venue_v2.version,
            effective_revision=snapshot.head,
        )
        decisions = (*snapshot.decisions, venue_v2)
        statuses = derive_entity_statuses(
            entity_versions=all_entities,
            relation_versions=snapshot.relation_versions,
            decisions=decisions,
            current_entities=current_entities,
            current_relations=snapshot.current_relations,
            effective_decisions=effective_decisions,
        )
        changed = snapshot.model_copy(
            update={
                "entity_versions": all_entities,
                "decisions": decisions,
                "current_entities": current_entities,
                "current_decisions": current_decisions,
                "effective_decisions": effective_decisions,
                "derived_status": statuses,
            }
        )

        with mock.patch(
            "econ_theorist.profile_craft_validation.validate_authoring_ready"
        ):
            validate_profile_craft_ready(
                snapshot, EntityVersionRef(entity_id="profile.craft.closure", version=1)
            )
            with self.assertRaisesRegex(
                ProfileCraftValidationError, "current and effective"
            ):
                validate_profile_craft_ready(
                    changed,
                    EntityVersionRef(entity_id="profile.craft.closure", version=1),
                )

        for item in old_phase1_to_3:
            reference = (item.entity_id, item.version)
            self.assertEqual(canonical_json_bytes(item), old_bytes[reference])
            self.assertTrue(
                all(value == "fresh" for value in statuses[item.entity_id].freshness.values())
            )


if __name__ == "__main__":
    unittest.main()
