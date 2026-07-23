from __future__ import annotations

import unittest

from econ_theorist.codex_bridge import _unique_maximal_focus_candidate
from econ_theorist.machine.models import NavigationCandidateKeyV1, NavigationCandidateV1
from econ_theorist.models import Actor, EntityVersionRef


class CodexBridgeFocusResolutionTests(unittest.TestCase):
    def _candidate(
        self,
        digest_character: str,
        focus_refs: tuple[EntityVersionRef, ...],
    ) -> NavigationCandidateV1:
        return NavigationCandidateV1(
            candidate_digest=digest_character * 64,
            key=NavigationCandidateKeyV1(
                base_head="a" * 64,
                route_id="tournament.implementations",
                route_version=2,
                purpose="research_discovery",
                actor=Actor(kind="agent", actor_id="scientific_agent"),
                compartments=("project_research",),
                privacy_clearance="public",
                focus_refs=focus_refs,
                context_budget=32000,
                context_hash="b" * 64,
                route_registry_hash="c" * 64,
                instruction_bundle_hash="d" * 64,
                context_selector_version="context_selector.v1",
                navigation_registry_hash="e" * 64,
                policy_hashes={"kernel": "f" * 64},
            ),
            explanation="Fixture candidate.",
        )

    def test_selects_only_one_strictly_complete_nested_focus(self) -> None:
        question = EntityVersionRef(entity_id="question.fixture", version=1)
        mechanism = EntityVersionRef(entity_id="mechanism.fixture", version=1)
        rival = EntityVersionRef(entity_id="rival.fixture", version=1)
        selected = _unique_maximal_focus_candidate(
            [
                self._candidate("1", (question, mechanism)).model_dump(mode="json"),
                self._candidate("2", (question, rival)).model_dump(mode="json"),
                self._candidate(
                    "3", (question, mechanism, rival)
                ).model_dump(mode="json"),
            ],
            requested_route_id="tournament.implementations",
        )

        self.assertIsNotNone(selected)
        self.assertEqual(selected["candidate_digest"], "3" * 64)

    def test_refuses_incomparable_or_wrong_route_candidates(self) -> None:
        question = EntityVersionRef(entity_id="question.fixture", version=1)
        mechanism = EntityVersionRef(entity_id="mechanism.fixture", version=1)
        rival = EntityVersionRef(entity_id="rival.fixture", version=1)
        self.assertIsNone(
            _unique_maximal_focus_candidate(
                [
                    self._candidate("1", (question, mechanism)).model_dump(
                        mode="json"
                    ),
                    self._candidate("2", (question, rival)).model_dump(mode="json"),
                ],
                requested_route_id="tournament.implementations",
            )
        )
        self.assertIsNone(
            _unique_maximal_focus_candidate(
                [self._candidate("1", (question, mechanism)).model_dump(mode="json")],
                requested_route_id="decompose.primitives",
            )
        )


if __name__ == "__main__":
    unittest.main()
