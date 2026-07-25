"""Focused checks for the disabled discovery-distillation ResearchMove release."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib
import unittest

from pydantic import ValidationError

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import object_digest, sha256_digest
from econ_theorist.research_craft import (
    ResearchCorpusRelease,
    ResearchSourceCard,
    research_source_ref,
)
from econ_theorist.research_craft_policy import (
    RESEARCH_CORPUS_V1_HASH,
    RESEARCH_CORPUS_V2_HASH,
    ResearchCraftPolicyError,
    load_research_corpus,
)


V1_PATH = REPOSITORY_ROOT / "craft" / "research_corpus.v1.json"
V2_PATH = REPOSITORY_ROOT / "craft" / "research_corpus.v2.json"
V2_REPORT_PATH = (
    REPOSITORY_ROOT
    / "review_outputs"
    / "phase5b_research_move_discovery_distillation_source_audit_v2.md"
)
NEW_MOVE_ROUTES = {
    "research.move.market_operation_primitive": {
        "frame.question_and_benchmarks",
        "decompose.primitives",
    },
    "research.move.different_implementation_question": {
        "frame.question_and_benchmarks",
        "tournament.mechanisms",
    },
    "research.move.ground_up_constraint_rebuild": {
        "frame.question_and_benchmarks",
        "decompose.primitives",
    },
}


def _source_key(reference) -> tuple[str, int, str]:
    return reference.source_id, reference.version, reference.content_hash


class ResearchCraftDistillationDevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.v1 = load_research_corpus(
            V1_PATH.resolve(),
            expected_hash=RESEARCH_CORPUS_V1_HASH,
        )
        cls.v2 = load_research_corpus(
            V2_PATH.resolve(),
            expected_hash=RESEARCH_CORPUS_V2_HASH,
        )

    def test_v1_remains_exact_and_v2_is_exactly_bound(self) -> None:
        self.assertEqual(
            sha256_digest(V1_PATH.read_bytes()),
            RESEARCH_CORPUS_V1_HASH,
        )
        self.assertEqual(
            sha256_digest(V2_PATH.read_bytes()),
            RESEARCH_CORPUS_V2_HASH,
        )
        self.assertEqual(object_digest(self.v2), RESEARCH_CORPUS_V2_HASH)
        self.assertEqual(
            sha256_digest(V2_REPORT_PATH.read_bytes()),
            self.v2.source_audit_report_sha256,
        )
        self.assertEqual(self.v2.resource_version, 2)
        self.assertEqual(
            self.v2.release_id,
            "research.corpus.discovery_distillation.v2",
        )

    def test_release_hashes_and_files_cannot_be_crossed(self) -> None:
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "hash mismatch",
        ):
            load_research_corpus(
                V1_PATH.resolve(),
                expected_hash=RESEARCH_CORPUS_V2_HASH,
            )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "hash mismatch",
        ):
            load_research_corpus(
                V2_PATH.resolve(),
                expected_hash=RESEARCH_CORPUS_V1_HASH,
            )

    def test_v2_adds_exactly_four_sources_and_three_moves(self) -> None:
        v1_sources = {
            _source_key(research_source_ref(source)) for source in self.v1.source_cards
        }
        v2_sources = {
            _source_key(research_source_ref(source)) for source in self.v2.source_cards
        }
        self.assertEqual(len(self.v1.source_cards), 11)
        self.assertEqual(len(self.v2.source_cards), 15)
        self.assertTrue(v1_sources.issubset(v2_sources))

        v1_moves = {move.move_id for move in self.v1.moves}
        v2_moves = {move.move_id: move for move in self.v2.moves}
        self.assertEqual(len(v1_moves), 3)
        self.assertEqual(len(v2_moves), 6)
        self.assertEqual(set(v2_moves) - v1_moves, set(NEW_MOVE_ROUTES))
        for move_id, expected_routes in NEW_MOVE_ROUTES.items():
            with self.subTest(move=move_id):
                self.assertEqual(
                    set(v2_moves[move_id].compatible_route_ids),
                    expected_routes,
                )

    def test_interviews_are_explicit_and_cross_domain_evidence_is_bounded(self) -> None:
        source_by_id = {
            source.source_id: source for source in self.v2.source_cards
        }
        interview_ids = {
            "research.source.acemoglu_nobel_ideas_interview",
            "research.source.musk_henry_ford_first_principles",
        }
        for source_id in interview_ids:
            with self.subTest(source=source_id):
                source = source_by_id[source_id]
                self.assertEqual(source.source_type, "interview")
                self.assertEqual(source.claim_relation, "explicitly_stated")

        musk = source_by_id[
            "research.source.musk_henry_ford_first_principles"
        ]
        self.assertEqual(
            musk.research_mode,
            "general_problem_solving_methodology",
        )
        ground_up = next(
            move
            for move in self.v2.moves
            if move.move_id == "research.move.ground_up_constraint_rebuild"
        )
        bound_sources = {
            binding.source_ref.source_id for binding in ground_up.evidence_bindings
        }
        self.assertEqual(
            bound_sources,
            {
                "research.source.musk_henry_ford_first_principles",
                "research.source.varian_model_building",
                "research.source.roth_economist_engineer",
            },
        )

        invalid_interview = musk.model_dump(mode="python")
        invalid_interview["claim_relation"] = "inferred_reconstruction"
        with self.assertRaisesRegex(
            ValidationError,
            "explicitly stated method",
        ):
            ResearchSourceCard.model_validate(invalid_interview)

        one_economic_anchor = ground_up.model_copy(
            update={
                "evidence_bindings": (
                    ground_up.evidence_bindings[0],
                    ground_up.evidence_bindings[1],
                )
            }
        )
        poisoned = self.v2.model_copy(
            update={
                "moves": tuple(
                    one_economic_anchor
                    if move.move_id == ground_up.move_id
                    else move
                    for move in self.v2.moves
                )
            }
        )
        with self.assertRaisesRegex(
            ValidationError,
            "two independent economic positive anchors",
        ):
            ResearchCorpusRelease.model_validate(
                poisoned.model_dump(mode="python")
            )

    def test_every_source_is_audited_referenced_and_source_isolated(self) -> None:
        source_by_ref = {
            _source_key(research_source_ref(source)): source
            for source in self.v2.source_cards
        }
        audit_by_ref = {
            _source_key(audit.source_ref): audit
            for audit in self.v2.source_admission_audits
        }
        referenced = {
            _source_key(binding.source_ref)
            for move in self.v2.moves
            for binding in move.evidence_bindings
        }
        self.assertEqual(set(source_by_ref), set(audit_by_ref))
        self.assertEqual(set(source_by_ref), referenced)
        self.assertTrue(
            all(audit.included_in_development for audit in audit_by_ref.values())
        )

        author_tokens = {
            token.casefold()
            for source in self.v2.source_cards
            for author in source.authors
            for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", author)
            if len(token) >= 3
        }
        for move in self.v2.moves:
            projection = move.runtime_projection.casefold()
            projection_tokens = set(
                re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", projection)
            )
            self.assertFalse(author_tokens.intersection(projection_tokens))
            self.assertNotIn("http://", projection)
            self.assertNotIn("https://", projection)
            for source in self.v2.source_cards:
                self.assertNotIn(source.source_id.casefold(), projection)
                self.assertNotIn(source.source_locator.casefold(), projection)

    def test_v2_remains_default_closed_and_absent_from_live_surfaces(self) -> None:
        for field_name in (
            "evaluation_holdouts_included",
            "production_package_resource",
            "runtime_selector_present",
            "pilot_authorized",
            "automatic_selection_authorized",
            "canonical_write_authorized",
        ):
            self.assertIs(getattr(self.v2, field_name), False)
        for move in self.v2.moves:
            self.assertEqual(move.activation_status, "development_disabled")
            self.assertFalse(move.pilot_authorized)
            self.assertFalse(move.automatic_selection_authorized)
            self.assertFalse(move.canonical_write_authorized)
            self.assertFalse(move.route_disposition_authority)

        pyproject = tomllib.loads(
            (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        serialized_data_files = repr(
            pyproject["tool"]["setuptools"]["data-files"]
        ).casefold()
        self.assertNotIn("research_corpus.v2.json", serialized_data_files)

        forbidden = (
            "research_corpus.v2.json",
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
            for forbidden_value in forbidden:
                with self.subTest(path=path, forbidden=forbidden_value):
                    self.assertNotIn(forbidden_value.casefold(), text)


if __name__ == "__main__":
    unittest.main()
