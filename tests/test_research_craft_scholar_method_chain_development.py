"""Focused checks for the disabled scholar-method-chain ResearchMove release."""

from __future__ import annotations

from pathlib import Path
import tomllib
import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import object_digest, sha256_digest
from econ_theorist.research_craft import research_source_ref
from econ_theorist.research_craft_policy import (
    RESEARCH_CORPUS_V2_HASH,
    RESEARCH_CORPUS_V3_HASH,
    ResearchCraftPolicyError,
    load_research_corpus,
)


V2_PATH = REPOSITORY_ROOT / "craft" / "research_corpus.v2.json"
V3_PATH = REPOSITORY_ROOT / "craft" / "research_corpus.v3.json"
V3_REPORT_PATH = (
    REPOSITORY_ROOT
    / "review_outputs"
    / "phase5b_research_move_scholar_method_chain_source_audit_v3.md"
)
NEW_SOURCE_IDS = {
    "research.source.acemoglu_robinson_persistence_power",
    "research.source.carroll_robust_linear_contracts",
    "research.source.bergemann_morris_robust_predictions",
    "research.source.myerson_optimal_auction_design",
    "research.source.maskin_nobel_biographical",
}
NEW_MOVE_ROUTES = {
    "research.move.institutional_feedback_deepener": {
        "decompose.primitives",
        "tournament.mechanisms",
    },
    "research.move.robustness_axis_switch": {
        "discover.claims_and_boundaries",
        "audit.assumptions_generality_and_absorption",
    },
    "research.move.incentive_implementation_stress_test": {
        "tournament.mechanisms",
        "tournament.implementations",
    },
}


def _source_key(source) -> tuple[str, int, str]:
    ref = research_source_ref(source)
    return ref.source_id, ref.version, ref.content_hash


class ResearchCraftScholarMethodChainDevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v2 = load_research_corpus(
            V2_PATH.resolve(),
            expected_hash=RESEARCH_CORPUS_V2_HASH,
        )
        cls.v3 = load_research_corpus(
            V3_PATH.resolve(),
            expected_hash=RESEARCH_CORPUS_V3_HASH,
        )

    def test_v2_remains_exact_and_v3_is_exactly_bound(self) -> None:
        self.assertEqual(
            sha256_digest(V2_PATH.read_bytes()),
            RESEARCH_CORPUS_V2_HASH,
        )
        self.assertEqual(
            sha256_digest(V3_PATH.read_bytes()),
            RESEARCH_CORPUS_V3_HASH,
        )
        self.assertEqual(object_digest(self.v3), RESEARCH_CORPUS_V3_HASH)
        self.assertEqual(
            sha256_digest(V3_REPORT_PATH.read_bytes()),
            self.v3.source_audit_report_sha256,
        )
        self.assertEqual(self.v3.resource_version, 3)
        self.assertEqual(
            self.v3.release_id,
            "research.corpus.scholar_method_chain.v3",
        )

    def test_release_hashes_and_files_cannot_be_crossed(self) -> None:
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "hash mismatch",
        ):
            load_research_corpus(
                V2_PATH.resolve(),
                expected_hash=RESEARCH_CORPUS_V3_HASH,
            )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "hash mismatch",
        ):
            load_research_corpus(
                V3_PATH.resolve(),
                expected_hash=RESEARCH_CORPUS_V2_HASH,
            )

    def test_v3_adds_exactly_five_sources_and_three_moves(self) -> None:
        v2_sources = {_source_key(source) for source in self.v2.source_cards}
        v3_sources = {_source_key(source) for source in self.v3.source_cards}
        self.assertEqual(len(self.v2.source_cards), 15)
        self.assertEqual(len(self.v3.source_cards), 20)
        self.assertEqual(
            self.v3.source_cards[: len(self.v2.source_cards)],
            self.v2.source_cards,
        )
        self.assertTrue(v2_sources.issubset(v3_sources))
        self.assertEqual(
            {source_id for source_id, _, _ in v3_sources - v2_sources},
            NEW_SOURCE_IDS,
        )

        v2_moves = {move.move_id for move in self.v2.moves}
        v3_moves = {move.move_id: move for move in self.v3.moves}
        self.assertEqual(len(v2_moves), 6)
        self.assertEqual(len(v3_moves), 9)
        self.assertEqual(
            self.v3.moves[: len(self.v2.moves)],
            self.v2.moves,
        )
        self.assertEqual(set(v3_moves) - v2_moves, set(NEW_MOVE_ROUTES))
        for move_id, expected_routes in NEW_MOVE_ROUTES.items():
            with self.subTest(move=move_id):
                self.assertEqual(
                    set(v3_moves[move_id].compatible_route_ids),
                    expected_routes,
                )

    def test_evidence_distinguishes_papers_from_explicit_method_history(self) -> None:
        source_by_id = {
            source.source_id: source for source in self.v3.source_cards
        }
        for source_id in NEW_SOURCE_IDS - {
            "research.source.maskin_nobel_biographical"
        }:
            with self.subTest(source=source_id):
                source = source_by_id[source_id]
                self.assertEqual(source.source_type, "published_paper")
                self.assertEqual(
                    source.claim_relation,
                    "inferred_reconstruction",
                )

        maskin = source_by_id["research.source.maskin_nobel_biographical"]
        self.assertEqual(maskin.source_type, "method_essay")
        self.assertEqual(maskin.claim_relation, "explicitly_stated")
        self.assertIn("retrospective_narration", maskin.bias_flags)
        self.assertIn("successful_case_selection", maskin.bias_flags)

        report = V3_REPORT_PATH.read_text(encoding="utf-8")
        normalized_report = " ".join(report.split())
        self.assertIn("paper-chain-derived", report)
        self.assertIn(
            "A successful paper is not by itself evidence of the author's "
            "private research process.",
            normalized_report,
        )

    def test_each_new_move_has_the_intended_independent_evidence(self) -> None:
        moves = {move.move_id: move for move in self.v3.moves}
        expected = {
            "research.move.institutional_feedback_deepener": {
                "research.source.acemoglu_robinson_persistence_power",
                "research.source.doval_skreta_limited_commitment",
            },
            "research.move.robustness_axis_switch": {
                "research.source.carroll_robust_linear_contracts",
                "research.source.bergemann_morris_robust_predictions",
            },
            "research.move.incentive_implementation_stress_test": {
                "research.source.myerson_optimal_auction_design",
                "research.source.maskin_nobel_biographical",
            },
        }
        for move_id, source_ids in expected.items():
            with self.subTest(move=move_id):
                move = moves[move_id]
                self.assertEqual(
                    {
                        binding.source_ref.source_id
                        for binding in move.evidence_bindings
                    },
                    source_ids,
                )
                self.assertEqual(move.activation_status, "development_disabled")
                self.assertFalse(move.route_disposition_authority)

        institutional_text = " ".join(
            moves[
                "research.move.institutional_feedback_deepener"
            ].operation_steps
        ).casefold()
        self.assertIn("reoptimization", institutional_text)
        self.assertIn("fixed-state benchmark", institutional_text)
        self.assertIn("full-commitment benchmark", institutional_text)

        robustness = moves["research.move.robustness_axis_switch"]
        self.assertIn(
            "robustness_operator",
            robustness.required_semantic_inputs,
        )
        robustness_text = " ".join(robustness.operation_steps).casefold()
        self.assertIn("worst-case guarantee", robustness_text)
        self.assertIn("across-structure outcome set", robustness_text)
        self.assertIn("never merge", robustness_text)

    def test_v3_is_source_isolated_audited_and_default_closed(self) -> None:
        source_refs = {
            _source_key(source) for source in self.v3.source_cards
        }
        audited_refs = {
            (
                audit.source_ref.source_id,
                audit.source_ref.version,
                audit.source_ref.content_hash,
            )
            for audit in self.v3.source_admission_audits
        }
        referenced_refs = {
            (
                binding.source_ref.source_id,
                binding.source_ref.version,
                binding.source_ref.content_hash,
            )
            for move in self.v3.moves
            for binding in move.evidence_bindings
        }
        self.assertEqual(source_refs, audited_refs)
        self.assertEqual(source_refs, referenced_refs)
        for field_name in (
            "evaluation_holdouts_included",
            "production_package_resource",
            "runtime_selector_present",
            "pilot_authorized",
            "automatic_selection_authorized",
            "canonical_write_authorized",
        ):
            self.assertIs(getattr(self.v3, field_name), False)
        for move in self.v3.moves:
            self.assertFalse(move.source_identities_visible_to_generator)
            self.assertFalse(move.source_phrase_material_included)
            self.assertFalse(move.pilot_authorized)
            self.assertFalse(move.automatic_selection_authorized)
            self.assertFalse(move.canonical_write_authorized)

    def test_v3_is_not_packaged_or_referenced_by_live_surfaces(self) -> None:
        pyproject = tomllib.loads(
            (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        serialized_data_files = repr(
            pyproject["tool"]["setuptools"]["data-files"]
        ).casefold()
        self.assertNotIn("research_corpus.v3.json", serialized_data_files)

        forbidden = (
            "research_corpus.v3.json",
            *NEW_MOVE_ROUTES,
        )
        inspected_paths = [
            REPOSITORY_ROOT / "src" / "econ_theorist" / "context.py",
            *(
                path
                for path in (
                    REPOSITORY_ROOT / "src" / "econ_theorist" / "machine"
                ).rglob("*.py")
            ),
            *(
                path
                for path in (REPOSITORY_ROOT / "routes").rglob("*")
                if path.is_file()
            ),
            *(
                path
                for path in (REPOSITORY_ROOT / "machine").rglob("*")
                if path.is_file()
            ),
        ]
        for path in inspected_paths:
            text = path.read_text(encoding="utf-8").casefold()
            for value in forbidden:
                with self.subTest(path=path, forbidden=value):
                    self.assertNotIn(value.casefold(), text)


if __name__ == "__main__":
    unittest.main()
