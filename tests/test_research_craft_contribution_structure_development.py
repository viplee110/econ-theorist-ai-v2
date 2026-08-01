"""Focused checks for the disabled contribution-structure ResearchMove release."""

from __future__ import annotations

import tomllib
import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import object_digest, sha256_digest
from econ_theorist.research_craft import research_source_ref
from econ_theorist.research_craft_policy import (
    RESEARCH_CORPUS_V3_HASH,
    RESEARCH_CORPUS_V4_HASH,
    ResearchCraftPolicyError,
    load_research_corpus,
)


V3_PATH = REPOSITORY_ROOT / "craft" / "research_corpus.v3.json"
V4_PATH = REPOSITORY_ROOT / "craft" / "research_corpus.v4.json"
V4_REPORT_PATH = (
    REPOSITORY_ROOT
    / "review_outputs"
    / "phase5b_research_move_contribution_structure_source_audit_v4.md"
)
NEW_SOURCE_IDS = {
    "research.source.galperti_levkun_perego_data_records",
    "research.source.gabaix_sparse_bounded_rationality",
    "research.source.hartline_roughgarden_simple_optimal",
    "research.source.ashlagi_monachou_nikzad_waitlists",
}
NEW_MOVE_ROUTES = {
    "research.move.question_reframer": {
        "frame.question_and_benchmarks",
        "audit.assumptions_generality_and_absorption",
    },
    "research.move.near_optimal_structure_pivot": {
        "tournament.implementations",
        "audit.assumptions_generality_and_absorption",
    },
}


def _source_key(source) -> tuple[str, int, str]:
    ref = research_source_ref(source)
    return ref.source_id, ref.version, ref.content_hash


class ResearchCraftContributionStructureDevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v3 = load_research_corpus(
            V3_PATH.resolve(),
            expected_hash=RESEARCH_CORPUS_V3_HASH,
        )
        cls.v4 = load_research_corpus(
            V4_PATH.resolve(),
            expected_hash=RESEARCH_CORPUS_V4_HASH,
        )

    def test_v3_remains_exact_and_v4_is_exactly_bound(self) -> None:
        self.assertEqual(
            sha256_digest(V3_PATH.read_bytes()),
            RESEARCH_CORPUS_V3_HASH,
        )
        self.assertEqual(
            sha256_digest(V4_PATH.read_bytes()),
            RESEARCH_CORPUS_V4_HASH,
        )
        self.assertEqual(object_digest(self.v4), RESEARCH_CORPUS_V4_HASH)
        self.assertEqual(
            sha256_digest(V4_REPORT_PATH.read_bytes()),
            self.v4.source_audit_report_sha256,
        )
        self.assertEqual(self.v4.resource_version, 4)
        self.assertEqual(
            self.v4.release_id,
            "research.corpus.contribution_structure.v4",
        )

    def test_release_hashes_and_files_cannot_be_crossed(self) -> None:
        with self.assertRaisesRegex(ResearchCraftPolicyError, "hash mismatch"):
            load_research_corpus(
                V3_PATH.resolve(),
                expected_hash=RESEARCH_CORPUS_V4_HASH,
            )
        with self.assertRaisesRegex(ResearchCraftPolicyError, "hash mismatch"):
            load_research_corpus(
                V4_PATH.resolve(),
                expected_hash=RESEARCH_CORPUS_V3_HASH,
            )

    def test_v4_adds_exactly_four_sources_and_two_moves(self) -> None:
        v3_sources = {_source_key(source) for source in self.v3.source_cards}
        v4_sources = {_source_key(source) for source in self.v4.source_cards}
        self.assertEqual(len(self.v3.source_cards), 20)
        self.assertEqual(len(self.v4.source_cards), 24)
        self.assertEqual(
            self.v4.source_cards[: len(self.v3.source_cards)],
            self.v3.source_cards,
        )
        self.assertTrue(v3_sources.issubset(v4_sources))
        self.assertEqual(
            {source_id for source_id, _, _ in v4_sources - v3_sources},
            NEW_SOURCE_IDS,
        )

        v3_moves = {move.move_id for move in self.v3.moves}
        v4_moves = {move.move_id: move for move in self.v4.moves}
        self.assertEqual(len(v3_moves), 9)
        self.assertEqual(len(v4_moves), 11)
        self.assertEqual(
            self.v4.moves[: len(self.v3.moves)],
            self.v3.moves,
        )
        self.assertEqual(set(v4_moves) - v3_moves, set(NEW_MOVE_ROUTES))
        for move_id, expected_routes in NEW_MOVE_ROUTES.items():
            with self.subTest(move=move_id):
                self.assertEqual(
                    set(v4_moves[move_id].compatible_route_ids),
                    expected_routes,
                )

    def test_new_sources_are_inferred_independent_paper_evidence(self) -> None:
        sources = {source.source_id: source for source in self.v4.source_cards}
        for source_id in NEW_SOURCE_IDS:
            with self.subTest(source=source_id):
                source = sources[source_id]
                self.assertEqual(source.source_type, "published_paper")
                self.assertEqual(
                    source.claim_relation,
                    "inferred_reconstruction",
                )
                self.assertIn("published_outcome_selection", source.bias_flags)
                self.assertGreater(source.source_snapshot_bytes, 200_000)

        report = V4_REPORT_PATH.read_text(encoding="utf-8")
        self.assertGreaterEqual(report.count("paper-chain-derived"), 2)
        self.assertIn(
            "none is evidence that an author privately used the move",
            " ".join(report.split()).casefold(),
        )

    def test_new_moves_preserve_authority_and_scientific_boundaries(self) -> None:
        moves = {move.move_id: move for move in self.v4.moves}
        expected_sources = {
            "research.move.question_reframer": {
                "research.source.galperti_levkun_perego_data_records",
                "research.source.gabaix_sparse_bounded_rationality",
            },
            "research.move.near_optimal_structure_pivot": {
                "research.source.hartline_roughgarden_simple_optimal",
                "research.source.ashlagi_monachou_nikzad_waitlists",
            },
        }
        for move_id, source_ids in expected_sources.items():
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
                self.assertFalse(move.canonical_write_authorized)

        reframer = moves["research.move.question_reframer"]
        reframer_text = " ".join(reframer.operation_steps).casefold()
        self.assertIn("freeze", reframer_text)
        self.assertIn("first benchmark reasoning link", reframer_text)
        self.assertIn(
            "requires_human_approved_reframe",
            reframer.advisory_evidence_kinds,
        )

        near_optimal = moves["research.move.near_optimal_structure_pivot"]
        near_optimal_text = " ".join(near_optimal.operation_steps).casefold()
        self.assertIn("additive or multiplicative loss bound", near_optimal_text)
        self.assertIn("zero-loss implementation", near_optimal_text)
        self.assertIn("tight example", near_optimal_text)
        self.assertIn(
            "loss_metric_undefined",
            near_optimal.non_applicability_keys,
        )

    def test_v4_is_source_isolated_default_closed_and_not_packaged(self) -> None:
        source_refs = {_source_key(source) for source in self.v4.source_cards}
        audited_refs = {
            (
                audit.source_ref.source_id,
                audit.source_ref.version,
                audit.source_ref.content_hash,
            )
            for audit in self.v4.source_admission_audits
        }
        referenced_refs = {
            (
                binding.source_ref.source_id,
                binding.source_ref.version,
                binding.source_ref.content_hash,
            )
            for move in self.v4.moves
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
            self.assertIs(getattr(self.v4, field_name), False)
        for move in self.v4.moves:
            self.assertFalse(move.source_identities_visible_to_generator)
            self.assertFalse(move.source_phrase_material_included)
            self.assertFalse(move.pilot_authorized)
            self.assertFalse(move.automatic_selection_authorized)

        pyproject = tomllib.loads(
            (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        serialized_data_files = repr(
            pyproject["tool"]["setuptools"]["data-files"]
        ).casefold()
        self.assertNotIn("research_corpus.v4.json", serialized_data_files)

        forbidden = ("research_corpus.v4.json", *NEW_MOVE_ROUTES)
        explicit_pilot_context = (
            REPOSITORY_ROOT / "src" / "econ_theorist" / "context.py"
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
                if (
                    path == explicit_pilot_context
                    and value == "research_corpus.v4.json"
                ):
                    # The separately authorized, default-closed reframe selector
                    # may load this exact checkout-only source.  No machine
                    # resource, route, or ordinary selector may reference it.
                    self.assertEqual(text.count(value), 1)
                    continue
                with self.subTest(path=path, forbidden=value):
                    self.assertNotIn(value.casefold(), text)


if __name__ == "__main__":
    unittest.main()
