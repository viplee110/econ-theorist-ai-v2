"""Exact, leakage-aware acceptance tests for the Phase 2 gold case."""

from __future__ import annotations

import json
import unittest
from copy import deepcopy
from fractions import Fraction

from tests.helpers import REPOSITORY_ROOT

from econ_theorist.gold_cases import (
    GoldCaseError,
    continuous_attention,
    evaluate_binary_attention,
    load_attention_fixture,
    rational,
    reversal_predicted,
    validate_attention_fixture,
)


FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "phase2_attention_precision_gold.v1.json"
)


class AttentionPrecisionGoldCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.payload = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_complete_fixture_matches_the_independent_fraction_oracle(self) -> None:
        summary = load_attention_fixture(FIXTURE)
        self.assertEqual(summary["case_id"], "phase2.attention_precision.indivisible.v1")
        self.assertEqual(summary["absorption"], "absorbed")
        self.assertIs(summary["publication_eligible"], False)
        self.assertEqual(
            summary["case_ids"], ("E0", "E1", "E2", "E3", "E4", "E5", "E6")
        )

    def test_headline_reversal_region_and_both_tie_rules_are_exact(self) -> None:
        ell = Fraction(1, 2)
        h = Fraction(1)
        self.assertFalse(
            reversal_predicted(ell=ell, h=h, kappa=Fraction(1, 2), tie_rule="process")
        )
        self.assertTrue(
            reversal_predicted(ell=ell, h=h, kappa=Fraction(3, 4), tie_rule="process")
        )
        self.assertTrue(
            reversal_predicted(ell=ell, h=h, kappa=Fraction(1), tie_rule="process")
        )
        self.assertFalse(
            reversal_predicted(ell=ell, h=h, kappa=Fraction(5, 4), tie_rule="process")
        )
        self.assertTrue(
            reversal_predicted(
                ell=ell, h=h, kappa=Fraction(1, 2), tie_rule="do_not_process"
            )
        )
        self.assertFalse(
            reversal_predicted(
                ell=ell, h=h, kappa=Fraction(1), tie_rule="do_not_process"
            )
        )

    def test_constant_cost_ablation_removes_the_reversal(self) -> None:
        result = evaluate_binary_attention(
            ell=Fraction(1, 2),
            h=Fraction(1),
            kappa=Fraction(3, 4),
            constant_cost=Fraction(3, 16),
        )
        self.assertEqual(result["ordering"], "h_gt_ell")
        self.assertIs(result["d_ell"], True)
        self.assertIs(result["d_h"], True)

    def test_continuous_attention_never_creates_a_strict_coarse_advantage(self) -> None:
        for kappa in (
            Fraction(0),
            Fraction(1, 4),
            Fraction(1, 2),
            Fraction(3, 4),
            Fraction(1),
            Fraction(2),
        ):
            _, y_ell = continuous_attention(
                precision=Fraction(1, 3), kappa=kappa
            )
            _, y_h = continuous_attention(
                precision=Fraction(2, 3), kappa=kappa
            )
            self.assertGreaterEqual(y_h, y_ell)

    def test_declared_wrong_example_answer_is_rejected(self) -> None:
        payload = deepcopy(self.payload)
        payload["evaluator"]["gold_examples"][1]["expected"]["y_ell"] = {
            "numerator": 1,
            "denominator": 2,
        }
        with self.assertRaisesRegex(GoldCaseError, "y_ell"):
            validate_attention_fixture(payload)

    def test_wrong_endpoint_probe_is_rejected(self) -> None:
        payload = deepcopy(self.payload)
        payload["evaluator"]["hidden_probes"][0]["expected_ordering"] = "h_gt_ell"
        with self.assertRaisesRegex(GoldCaseError, "hidden boundary"):
            validate_attention_fixture(payload)

    def test_noncanonical_or_float_rationals_are_rejected(self) -> None:
        with self.assertRaisesRegex(GoldCaseError, "lowest terms"):
            rational({"numerator": 2, "denominator": 4})
        payload = deepcopy(self.payload)
        payload["evaluator"]["gold_examples"][0]["kappa"] = 0.0
        with self.assertRaisesRegex(GoldCaseError, "canonical JSON"):
            validate_attention_fixture(payload)

    def test_generator_compartment_cannot_receive_gold_or_inverse_maps(self) -> None:
        for leaked_key in ("headline_proposition", "gold_examples", "inverse_transform"):
            payload = deepcopy(self.payload)
            payload["generator"]["pre_result_brief"][leaked_key] = "leak"
            with self.subTest(leaked_key=leaked_key):
                with self.assertRaisesRegex(GoldCaseError, "pre_result_brief"):
                    validate_attention_fixture(payload)

    def test_absorption_mapping_cannot_be_renamed_away(self) -> None:
        payload = deepcopy(self.payload)
        payload["evaluator"]["absorption_decoy"]["translation"]["adopter"] = "reader"
        with self.assertRaisesRegex(GoldCaseError, "absorption translation"):
            validate_attention_fixture(payload)

    def test_formal_truth_is_not_destroyed_by_absorption_expectations(self) -> None:
        payload = deepcopy(self.payload)
        effects = payload["evaluator"]["absorption_decoy"]["expected_effects"]
        effects.remove("formal_validity_preserved")
        effects.append("formal_validity_failed")
        with self.assertRaisesRegex(GoldCaseError, "expected effects"):
            validate_attention_fixture(payload)


if __name__ == "__main__":
    unittest.main()
