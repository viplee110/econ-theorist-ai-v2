"""Focused reachability checks for the additive manuscript budget policy."""

from __future__ import annotations

import tempfile
import unittest
from unittest import mock

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase3_downgrade_attacks import manuscript_material
from tests.test_phase4_profile_craft_validation import registration, world

from econ_theorist import authoring as a
from econ_theorist.authoring import parse_authoring_entity
from econ_theorist.machine.navigation import plan_next
from econ_theorist.models import Snapshot
from econ_theorist.policy import SELECTOR_VERSION_MANUSCRIPT_QUALITY
from econ_theorist.runtime import StoreLayout


class ManuscriptQualityNavigationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.layout = StoreLayout.at(temporary.name).ensure()

    def _world_with_prior_artifact(
        self,
    ) -> tuple[Snapshot, a.ManuscriptUnit, bytes]:
        snapshot, entities = world()
        prior = parse_authoring_entity(entities["diagnosed.manuscript.unit"])
        assert isinstance(prior, a.ManuscriptUnit)
        prior_ref = prior.manuscript_artifact_ref
        _prior_text, prior_bytes, _fixture_ref, _fixture_unit = manuscript_material(
            writer_packet_hash="2" * 64
        )
        prior_registration = registration(prior_ref).model_copy(
            update={
                "byte_size": len(prior_bytes),
                "media_type": "text/plain; charset=utf-8",
            }
        )
        snapshot = snapshot.model_copy(
            update={
                "artifacts": (
                    *(
                        item
                        for item in snapshot.artifacts
                        if not (
                            item.artifact_id == prior_ref.artifact_id
                            and item.version == prior_ref.version
                        )
                    ),
                    prior_registration,
                ),
                "current_artifacts": {
                    **snapshot.current_artifacts,
                    prior_ref.artifact_id: prior_ref.version,
                },
            }
        )
        return snapshot, prior, prior_bytes

    def test_route_default_reaches_profiled_compose_but_explicit_low_cap_blocks(
        self,
    ) -> None:
        snapshot, prior, prior_bytes = self._world_with_prior_artifact()
        common = dict(
            actor=prior.canonical_writer,
            compartments=("project_research",),
            privacy_clearance="project_private",
            requested_route_ids=("compose.profiled_manuscript_unit",),
        )

        with mock.patch(
            "econ_theorist.runtime.objects.ObjectStore.read_bytes",
            return_value=prior_bytes,
        ):
            default = plan_next(self.layout, snapshot, **common)
            capped = plan_next(self.layout, snapshot, budget_units=4_000, **common)

        self.assertEqual(default.outcome, "unique_next", default)
        self.assertEqual(len(default.candidates), 1)
        candidate = default.candidates[0]
        self.assertEqual(candidate.key.route_id, "compose.profiled_manuscript_unit")
        self.assertEqual(
            tuple(item.entity_id for item in candidate.key.focus_refs),
            (
                "assurance.bundle",
                "craft.selection",
                "diagnosed.manuscript.unit",
                "diagnosis.reader.problem",
                "entity.paper",
                "entity.reader.path",
                "entity.result.contracts",
                "package.validated",
                "profile.stack",
                "profile.universal",
                "review.closure.diagnosed",
                "revision.brief.diagnosed",
            ),
        )
        self.assertEqual(candidate.key.context_budget, 32_000)
        self.assertEqual(
            candidate.key.context_selector_version,
            SELECTOR_VERSION_MANUSCRIPT_QUALITY,
        )

        self.assertEqual(capped.outcome, "repair_required", capped)
        self.assertEqual(capped.candidates, ())
        self.assertIn(
            "context_budget_insufficient",
            {item.code for item in capped.blockers},
        )


if __name__ == "__main__":
    unittest.main()
