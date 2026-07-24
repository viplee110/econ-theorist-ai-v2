"""Focused checks for the disabled first ResearchMove development corpus."""

from __future__ import annotations

import json
from pathlib import Path
import re
import tempfile
import tomllib
import unittest

from pydantic import ValidationError

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import canonical_json_bytes, object_digest, sha256_digest
from econ_theorist.profile_craft import (
    PROFILE_CRAFT_PAYLOAD_MODELS,
    ProfileCraftPayload,
)
from econ_theorist.profile_craft_policy import (
    CRAFT_CORPUS_V1_HASH,
    load_craft_corpus,
)
from econ_theorist.research_craft import (
    RESEARCH_CRAFT_RESOURCE_MODELS,
    ResearchCorpusRelease,
    ResearchSourceCard,
    SourceAdmissionAudit,
    research_source_ref,
)
from econ_theorist.research_craft_policy import (
    RESEARCH_CORPUS_V1_HASH,
    ResearchCraftPolicyError,
    _validate_research_corpus_policy,
    load_research_corpus,
)


CORPUS_PATH = REPOSITORY_ROOT / "craft" / "research_corpus.v1.json"
AUDIT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "review_outputs"
    / "phase5b_research_move_source_audit_v1.md"
)
EXPECTED_MOVE_ROUTES = {
    "research.move.computational_structure_probe": {
        "lab.micro_examples_and_ablations",
        "discover.claims_and_boundaries",
    },
    "research.move.representation_hunter": {
        "tournament.mechanisms",
        "tournament.implementations",
    },
    "research.move.analogical_structure_transfer": {
        "tournament.mechanisms",
        "audit.assumptions_generality_and_absorption",
    },
}
ROUTE_OUTCOMES = {"continue", "park", "kill", "new_brief_required"}


def _source_key(reference) -> tuple[str, int, str]:
    return reference.source_id, reference.version, reference.content_hash


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value, flags=re.UNICODE))


class ResearchCraftDevelopmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus_bytes = CORPUS_PATH.read_bytes()
        cls.corpus = load_research_corpus(
            CORPUS_PATH.resolve(),
            expected_hash=RESEARCH_CORPUS_V1_HASH,
        )

    def test_strict_resource_models_remain_internal(self) -> None:
        self.assertNotIn(
            "FunctionOnlyResearchMoveProjection",
            RESEARCH_CRAFT_RESOURCE_MODELS,
        )
        self.assertFalse(
            any(
                (
                    REPOSITORY_ROOT / "schemas" / "research_craft"
                ).rglob("*.schema.json")
            )
        )

        def inspect_objects(node: object) -> None:
            if isinstance(node, dict):
                if node.get("type") == "object" and "properties" in node:
                    self.assertFalse(node.get("additionalProperties", True))
                for value in node.values():
                    inspect_objects(value)
            elif isinstance(node, list):
                for value in node:
                    inspect_objects(value)

        for model_name, model in RESEARCH_CRAFT_RESOURCE_MODELS.items():
            with self.subTest(model=model_name):
                self.assertTrue(model.model_config.get("strict"))
                self.assertTrue(model.model_config.get("frozen"))
                self.assertEqual(model.model_config.get("extra"), "forbid")
                schema = model.model_json_schema(mode="validation")
                self.assertNotIn('"type": "number"', json.dumps(schema))
                inspect_objects(schema)

    def test_resource_bytes_and_hash_are_exact(self) -> None:
        self.assertEqual(
            sha256_digest(self.corpus_bytes),
            RESEARCH_CORPUS_V1_HASH,
        )
        self.assertEqual(object_digest(self.corpus), RESEARCH_CORPUS_V1_HASH)
        self.assertEqual(
            sha256_digest(AUDIT_REPORT_PATH.read_bytes()),
            self.corpus.source_audit_report_sha256,
        )

    def test_loader_requires_explicit_absolute_path_and_exact_inputs(self) -> None:
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "explicit absolute path",
        ):
            load_research_corpus(
                Path("craft/research_corpus.v1.json"),
                expected_hash=RESEARCH_CORPUS_V1_HASH,
            )
        with self.assertRaisesRegex(TypeError, "pathlib.Path"):
            load_research_corpus(  # type: ignore[arg-type]
                str(CORPUS_PATH.resolve()),
                expected_hash=RESEARCH_CORPUS_V1_HASH,
            )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "expected hash is invalid",
        ):
            load_research_corpus(
                CORPUS_PATH.resolve(),
                expected_hash="not-a-digest",
            )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "expected hash is invalid",
        ):
            load_research_corpus(
                CORPUS_PATH.resolve(),
                expected_hash=object(),  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "not the fixed development release",
        ):
            load_research_corpus(
                CORPUS_PATH.resolve(),
                expected_hash="0" * 64,
            )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "cannot load",
        ):
            load_research_corpus(
                (CORPUS_PATH.parent / "missing.research-corpus.json").resolve(),
                expected_hash=RESEARCH_CORPUS_V1_HASH,
            )

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            noncanonical = root / "noncanonical.json"
            noncanonical_bytes = self.corpus_bytes + b"\n"
            noncanonical.write_bytes(noncanonical_bytes)
            with self.assertRaisesRegex(
                ResearchCraftPolicyError,
                "not exact canonical JSON",
            ):
                load_research_corpus(
                    noncanonical.resolve(),
                    expected_hash=RESEARCH_CORPUS_V1_HASH,
                )

            unknown = json.loads(self.corpus_bytes.decode("utf-8"))
            unknown["unexpected_runtime_switch"] = True
            unknown_bytes = canonical_json_bytes(unknown)
            unknown_path = root / "unknown-field.json"
            unknown_path.write_bytes(unknown_bytes)
            with self.assertRaisesRegex(
                ResearchCraftPolicyError,
                "cannot load",
            ):
                load_research_corpus(
                    unknown_path.resolve(),
                    expected_hash=RESEARCH_CORPUS_V1_HASH,
                )

    def test_loader_binds_the_exact_checkout_source_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            corpus_path = root / "craft" / "research_corpus.v1.json"
            report_path = (
                root
                / "review_outputs"
                / "phase5b_research_move_source_audit_v1.md"
            )
            corpus_path.parent.mkdir(parents=True)
            report_path.parent.mkdir(parents=True)
            corpus_path.write_bytes(self.corpus_bytes)
            report_path.write_bytes(AUDIT_REPORT_PATH.read_bytes())

            loaded = load_research_corpus(
                corpus_path.resolve(),
                expected_hash=RESEARCH_CORPUS_V1_HASH,
            )
            self.assertEqual(loaded, self.corpus)

            report_path.write_bytes(AUDIT_REPORT_PATH.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                ResearchCraftPolicyError,
                "source-audit report hash mismatch",
            ):
                load_research_corpus(
                    corpus_path.resolve(),
                    expected_hash=RESEARCH_CORPUS_V1_HASH,
                )

    def test_source_audit_is_exactly_bound_to_every_admitted_source(self) -> None:
        source_by_ref = {
            _source_key(research_source_ref(source)): source
            for source in self.corpus.source_cards
        }
        audit_by_ref = {
            _source_key(audit.source_ref): audit
            for audit in self.corpus.source_admission_audits
        }
        self.assertEqual(len(source_by_ref), 11)
        self.assertEqual(set(source_by_ref), set(audit_by_ref))
        self.assertTrue(
            all(audit.included_in_development for audit in audit_by_ref.values())
        )
        self.assertTrue(
            all(audit.exclusion_reason is None for audit in audit_by_ref.values())
        )

        referenced = {
            _source_key(binding.source_ref)
            for move in self.corpus.moves
            for binding in move.evidence_bindings
        }
        self.assertEqual(referenced, set(source_by_ref))
        self.assertTrue(
            all(
                source.source_locator.startswith("https://")
                for source in source_by_ref.values()
            )
        )
        self.assertTrue(
            all(source.source_snapshot_bytes > 0 for source in source_by_ref.values())
        )
        self.assertEqual(
            self.corpus.source_audit_report_path,
            "review_outputs/phase5b_research_move_source_audit_v1.md",
        )

    def test_exact_three_moves_keep_the_approved_routes_and_variant(self) -> None:
        moves = {move.move_id: move for move in self.corpus.moves}
        self.assertEqual(set(moves), set(EXPECTED_MOVE_ROUTES))
        self.assertEqual(len(self.corpus.moves), 3)
        for move_id, expected_routes in EXPECTED_MOVE_ROUTES.items():
            with self.subTest(move=move_id):
                self.assertEqual(
                    set(moves[move_id].compatible_route_ids),
                    expected_routes,
                )
        self.assertIsNone(
            moves["research.move.computational_structure_probe"].variant_id
        )
        self.assertIsNone(
            moves["research.move.representation_hunter"].variant_id
        )
        self.assertEqual(
            moves["research.move.analogical_structure_transfer"].variant_id,
            "first_mapping_failure",
        )

    def test_sources_are_independent_and_published_work_is_inferred(self) -> None:
        source_by_ref = {
            _source_key(research_source_ref(source)): source
            for source in self.corpus.source_cards
        }
        for source in self.corpus.source_cards:
            with self.subTest(source=source.source_id):
                if source.source_type == "published_paper":
                    self.assertEqual(
                        source.claim_relation,
                        "inferred_reconstruction",
                    )
                    self.assertIn(
                        "published_outcome_selection",
                        source.bias_flags,
                    )
                else:
                    self.assertEqual(source.source_type, "method_essay")
                    self.assertEqual(
                        source.claim_relation,
                        "explicitly_stated",
                    )

        excluded_data = self.corpus.source_cards[0].model_dump(mode="python")
        excluded_data["curator_decision"] = "exclude"
        excluded = ResearchSourceCard.model_validate(excluded_data)
        exclusion = SourceAdmissionAudit(
            source_ref=research_source_ref(excluded),
            included_in_development=False,
            exclusion_reason="not_applicable",
        )
        self.assertFalse(exclusion.included_in_development)

        future_data = self.corpus.source_cards[0].model_dump(mode="python")
        future_data["publication_year"] = 2027
        future_data["recency_tier"] = "2022_2026"
        future_data["recency_weight_milli"] = 1000
        with self.assertRaisesRegex(ValidationError, "cannot be in the future"):
            ResearchSourceCard.model_validate(future_data)

        for move in self.corpus.moves:
            positive_sources = [
                source_by_ref[_source_key(binding.source_ref)]
                for binding in move.evidence_bindings
                if binding.use_role == "positive_anchor"
            ]
            families = {
                source.paper_family_id for source in positive_sources
            }
            clusters = {
                source.coauthor_cluster_id for source in positive_sources
            }
            inferred_groups = {
                (source.paper_family_id, source.coauthor_cluster_id)
                for source in positive_sources
                if source.source_type == "published_paper"
            }
            has_explicit_method = any(
                source.source_type == "method_essay"
                and source.claim_relation == "explicitly_stated"
                for source in positive_sources
            )
            with self.subTest(move=move.move_id):
                self.assertGreaterEqual(len(positive_sources), 2)
                self.assertGreaterEqual(len(families), 2)
                self.assertGreaterEqual(len(clusters), 2)
                self.assertTrue(
                    (has_explicit_method and bool(inferred_groups))
                    or len(inferred_groups) >= 2
                )

        analogical = next(
            move
            for move in self.corpus.moves
            if move.move_id == "research.move.analogical_structure_transfer"
        )
        self.assertTrue(
            any(
                binding.use_role == "skeptical_contrast"
                for binding in analogical.evidence_bindings
            )
        )

    def test_default_closed_authority_cannot_be_bypassed(self) -> None:
        for field_name in (
            "evaluation_holdouts_included",
            "production_package_resource",
            "runtime_selector_present",
            "pilot_authorized",
            "automatic_selection_authorized",
            "canonical_write_authorized",
        ):
            with self.subTest(field=field_name):
                self.assertIs(getattr(self.corpus, field_name), False)
        self.assertTrue(
            self.corpus.opt_in_pilot_requires_separate_human_authorization
        )
        self.assertTrue(
            self.corpus.default_activation_requires_held_out_replication
        )
        self.assertTrue(
            self.corpus.default_activation_requires_end_to_end_pilot
        )
        for move in self.corpus.moves:
            with self.subTest(move=move.move_id):
                self.assertEqual(move.activation_status, "development_disabled")
                self.assertFalse(move.pilot_authorized)
                self.assertFalse(move.automatic_selection_authorized)
                self.assertFalse(move.canonical_write_authorized)
                self.assertFalse(move.route_disposition_authority)
                self.assertFalse(move.source_identities_visible_to_generator)

        dumped = self.corpus.model_dump(mode="json")
        dumped["pilot_authorized"] = True
        with self.assertRaises(ValidationError):
            ResearchCorpusRelease.model_validate(dumped)

        poisoned = self.corpus.model_copy(update={"runtime_selector_present": True})
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "invalid disabled research-craft corpus",
        ):
            _validate_research_corpus_policy(poisoned)

    def test_function_only_projection_is_compact_and_identity_isolated(self) -> None:
        author_tokens = {
            token.casefold()
            for source in self.corpus.source_cards
            for author in source.authors
            for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", author)
            if len(token) >= 3
        }
        for move in self.corpus.moves:
            projection = move.runtime_projection
            self.assertGreaterEqual(_word_count(projection), 80)
            self.assertLessEqual(_word_count(projection), 120)

            rendered = projection.casefold()
            tokens = set(re.findall(r"[a-z_]+", projection.casefold()))
            self.assertFalse(ROUTE_OUTCOMES.intersection(tokens))
            self.assertNotIn("http://", rendered)
            self.assertNotIn("https://", rendered)
            self.assertNotIn("doi:", rendered)
            projection_tokens = {
                token.casefold()
                for token in re.findall(
                    r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+",
                    projection,
                )
            }
            self.assertFalse(author_tokens.intersection(projection_tokens))

            for source in self.corpus.source_cards:
                self.assertNotIn(source.source_id.casefold(), rendered)
                self.assertNotIn(source.source_locator.casefold(), rendered)
                self.assertNotIn(source.citation.casefold(), rendered)

    def test_no_retrieval_selection_or_projection_surface_exists(self) -> None:
        policy_source = (
            REPOSITORY_ROOT
            / "src"
            / "econ_theorist"
            / "research_craft_policy.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "inspect_applicable_research_moves",
            "select_research_move",
            "retrieve_research_move",
            "FunctionOnlyResearchMoveProjection",
            "ResearchMoveApplicabilityQuery",
        ):
            self.assertNotIn(forbidden, policy_source)

    def test_policy_revalidation_catches_model_copy_bypass(self) -> None:
        original = self.corpus.moves[0]
        route_poison = original.model_copy(
            update={
                "compatible_route_ids": (original.compatible_route_ids[0],),
            }
        )
        route_poisoned_corpus = self.corpus.model_copy(
            update={
                "moves": (
                    route_poison,
                    *self.corpus.moves[1:],
                )
            }
        )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "route compatibility changed",
        ):
            _validate_research_corpus_policy(route_poisoned_corpus)

        projection_poison = original.model_copy(
            update={"runtime_projection": "Too short to be an admissible projection."}
        )
        projection_poisoned_corpus = self.corpus.model_copy(
            update={
                "moves": (
                    projection_poison,
                    *self.corpus.moves[1:],
                )
            }
        )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "invalid disabled research-craft corpus",
        ):
            _validate_research_corpus_policy(projection_poisoned_corpus)

        release_poison = self.corpus.model_copy(
            update={"released_at": "2026-07-24T00:00:01Z"}
        )
        with self.assertRaisesRegex(
            ResearchCraftPolicyError,
            "exact fixed development release",
        ):
            _validate_research_corpus_policy(release_poison)

    def test_development_corpus_is_isolated_from_live_systems(self) -> None:
        pyproject = tomllib.loads(
            (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        )
        serialized_data_files = repr(
            pyproject["tool"]["setuptools"]["data-files"]
        ).casefold()
        self.assertNotIn("research_corpus.v1.json", serialized_data_files)
        self.assertNotIn("schemas/research_craft", serialized_data_files)

        for model_name, model in RESEARCH_CRAFT_RESOURCE_MODELS.items():
            with self.subTest(model=model_name):
                self.assertNotIn(model_name, PROFILE_CRAFT_PAYLOAD_MODELS)
                self.assertFalse(issubclass(model, ProfileCraftPayload))

        forbidden_references = (
            "research_corpus.v1.json",
            "research.move.computational_structure_probe",
            "research.move.representation_hunter",
            "research.move.analogical_structure_transfer",
            "econ_theorist.research_craft",
        )
        inspected_paths = [
            REPOSITORY_ROOT / "src" / "econ_theorist" / "context.py",
            REPOSITORY_ROOT / "src" / "econ_theorist" / "profile_craft.py",
            REPOSITORY_ROOT
            / "src"
            / "econ_theorist"
            / "profile_craft_policy.py",
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
            for forbidden in forbidden_references:
                with self.subTest(path=path, forbidden=forbidden):
                    self.assertNotIn(forbidden, text)

        self.assertEqual(
            CRAFT_CORPUS_V1_HASH,
            "468571238038771dfd84ccc27fc9efcb9b562bdf887a49592701e3c33b8f813b",
        )
        existing_corpus = load_craft_corpus()
        self.assertEqual(object_digest(existing_corpus), CRAFT_CORPUS_V1_HASH)
        self.assertEqual(
            sha256_digest(
                (REPOSITORY_ROOT / "craft" / "corpus.v1.json").read_bytes()
            ),
            CRAFT_CORPUS_V1_HASH,
        )


if __name__ == "__main__":
    unittest.main()
