from __future__ import annotations

from pathlib import Path
import unittest

from econ_theorist.machine.packets import _packet_forbidden_actions
from econ_theorist.route_registry import get_route


ROOT = Path(__file__).resolve().parents[1]


class LiteratureAcquisitionCheckpointTests(unittest.TestCase):
    def test_formal_output_bundle_adds_only_the_two_acquisition_guards(self) -> None:
        ordinary_route = get_route("frame.question_and_benchmarks")
        ordinary_outputs = tuple(
            item.entity_type for item in ordinary_route.required_output_entities
        )
        baseline = _packet_forbidden_actions(ordinary_outputs)
        audit_route = get_route("audit.assumptions_generality_and_absorption")
        audit_outputs = tuple(
            item.entity_type for item in audit_route.required_output_entities
        )
        guarded = _packet_forbidden_actions(audit_outputs)
        self.assertEqual(guarded[: len(baseline)], baseline)
        self.assertEqual(
            guarded[len(baseline) :],
            (
                "contribution_judgment_from_model_memory_or_uninspected_sources",
                "recommend_proceed_without_current_full_text_literature_acquisition",
            ),
        )
        incomplete = _packet_forbidden_actions(audit_outputs[:-1])
        self.assertEqual(incomplete, baseline)

    def test_all_three_host_adapters_receive_the_formal_acquisition_duty(self) -> None:
        paths = (
            ROOT / ".agents" / "skills" / "econ-theorist-v2" / "SKILL.md",
            ROOT / "CLAUDE.md",
            ROOT / ".cursor" / "rules" / "econ-theorist-v2.mdc",
        )
        for path in paths:
            with self.subTest(path=path):
                text = path.read_text(encoding="utf-8")
                for required in (
                    "LiteratureEvidence",
                    "ClosestTheoryMap",
                    "AbsorptionAssessment",
                    "privacy/egress permission",
                    "model memory",
                    "`proceed`",
                ):
                    self.assertIn(required, text)
                self.assertIn("full-text", text.replace("_", "-"))


if __name__ == "__main__":
    unittest.main()
