"""Focused semantic tests for the Phase 3 authoring validator."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.authoring import (
    ConsequentialSpan,
    ManuscriptLocation,
    ManuscriptUnit,
    TerminologyRealization,
)
from econ_theorist.authoring_validation import (
    AUTHORING_LEAKAGE_LINT_VERSION,
    AuthoringValidationError,
    lint_authoring_governance_leakage,
    validate_authoring_projection,
    validate_manuscript_spans_and_text,
    validate_phase3_route_entry,
    validate_phase3_route_transaction,
)
from econ_theorist import authoring_validation as authoring_validation_module
from econ_theorist.codec import sha256_digest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RouteOutcome,
    SemanticFacetRef,
    Snapshot,
    Transaction,
)
from econ_theorist.route_registry import get_route


DIGEST = "a" * 64
PROJECT = "project.phase3.validation.unit"
AGENT = Actor(kind="agent", actor_id="agent.phase3.unit")


def empty_snapshot() -> Snapshot:
    return Snapshot(project_id=PROJECT, head=DIGEST, chain=(DIGEST,))


class LegacyAndLintTests(unittest.TestCase):
    def test_legacy_projection_without_authoring_is_valid(self) -> None:
        report = validate_authoring_projection(empty_snapshot())
        self.assertEqual(report.parsed_entity_count, 0)
        self.assertEqual(report.assurance_pass_refs, ())
        self.assertEqual(report.authoring_ready_refs, ())

    def test_narrow_lint_preserves_ordinary_economic_vocabulary(self) -> None:
        prose = (
            "The claim follows from the model. The proof isolates the mechanism "
            "and explains the economically relevant scope."
        )
        self.assertEqual(lint_authoring_governance_leakage(prose), ())

    def test_narrow_lint_detects_exact_governance_tokens(self) -> None:
        prose = "Run design.reader_path after G5 and inspect context_manifest_hash."
        findings = lint_authoring_governance_leakage(prose)
        self.assertEqual(AUTHORING_LEAKAGE_LINT_VERSION, "AUTHORING-LEAKAGE-LINT-0.1")
        self.assertEqual(
            {item.rule_id for item in findings},
            {"exact_route_id", "internal_gate_label", "context_manifest_key"},
        )


class ManuscriptBytesTests(unittest.TestCase):
    def test_span_and_artifact_hashes_are_exact(self) -> None:
        text = "Higher search costs reduce entry."
        span = ConsequentialSpan(
            assertion_id="assertion.entry",
            role="economic_translation",
            claim_projection_id="projection.entry",
            claim_graph_ref=EntityVersionRef(entity_id="claims.entry", version=1),
            claim_id="claim.entry",
            source_fields=(
                SemanticFacetRef(
                    entity_id="claims.entry",
                    version=1,
                    facet="formal",
                    field_path="/payload/claims/0/formal_statement",
                    semantic_hash="b" * 64,
                ),
            ),
            scope="positive search costs",
            assumption_ids=("assumption.cost",),
            location=ManuscriptLocation(start_offset=0, end_offset=len(text)),
            text_hash=sha256_digest(text.encode("utf-8")),
            wording_strength="entailed_weaker",
            presentation="economic_interpretation",
        )
        artifact = ArtifactDependencyRef(
            artifact_id="artifact.manuscript",
            version=1,
            content_hash=sha256_digest(text.encode("utf-8")),
        )
        unit = ManuscriptUnit(
            unit_id="unit.entry",
            paper_ir_ref=EntityVersionRef(entity_id="paper.entry", version=1),
            reader_path_ref=EntityVersionRef(entity_id="reader.entry", version=1),
            result_contract_set_ref=EntityVersionRef(
                entity_id="contracts.entry", version=1
            ),
            section_contract_id="section.entry",
            manuscript_artifact_ref=artifact,
            source_state_revision="c" * 64,
            canonical_writer=AGENT,
            writer_role_packet_hash="d" * 64,
            writer_output_hash=artifact.content_hash,
            integration_generation=1,
            spans=(span,),
            terminology=(
                TerminologyRealization(
                    object_id="object.search_cost",
                    realized_name="search cost",
                    formal_symbol="c",
                    first_use_assertion_id="assertion.entry",
                ),
            ),
            composed_at="2026-07-12T00:00:00Z",
        )
        validate_manuscript_spans_and_text(unit, text)
        with self.assertRaisesRegex(AuthoringValidationError, "artifact hash"):
            validate_manuscript_spans_and_text(unit, text + " Changed.")
        with self.assertRaisesRegex(
            AuthoringValidationError, "undeclared consequential prose"
        ):
            validate_manuscript_spans_and_text(
                unit,
                text + " An undeclared stronger conclusion follows.",
                check_artifact_hash=False,
            )


class RouteFamilyTests(unittest.TestCase):
    def test_route_input_count_contract_rejects_foreign_visible_type(self) -> None:
        route = get_route("review.manuscript_unit")
        entities = tuple(
            EntityVersion.model_construct(entity_type=entity_type)
            for entity_type in (
                "CriticAssignment",
                "ManuscriptUnit",
                "PaperIR",
                "ResultContractSet",
                "ClaimGraph",
            )
        )
        with self.assertRaisesRegex(AuthoringValidationError, "foreign input types"):
            authoring_validation_module._require_counts(
                route, entities, output=False  # type: ignore[arg-type]
            )

    def test_assurance_entry_uses_assurance_validator_family(self) -> None:
        route = get_route("verify.independent_rederivation")
        with self.assertRaisesRegex(AuthoringValidationError, "requires at least"):
            validate_phase3_route_entry(
                empty_snapshot(), route, (), actor=AGENT  # type: ignore[arg-type]
            )

    def test_assurance_exit_uses_assurance_validator_family(self) -> None:
        route = get_route("verify.independent_rederivation")
        outcome = RouteOutcome(
            route_run_id="run.assurance.unit",
            route_id=route.route_id,
            outcome="failed",
            rationale="No inputs in this boundary test.",
        )
        transaction = Transaction(
            transaction_id="transaction.assurance.unit",
            origin="route_run",
            project_id=PROJECT,
            base_revision=DIGEST,
            route_run_id="run.assurance.unit",
            route_id=route.route_id,
            route_run_hash="b" * 64,
            context_manifest_hash="c" * 64,
            compiled_context_hash="d" * 64,
            actor=AGENT,
            intent="Exercise assurance validator routing.",
            operations=(RecordRouteOutcomeOp(outcome=outcome),),
            created_at="2026-07-12T00:00:00Z",
            parent_transaction_hash=DIGEST,
        )
        with self.assertRaisesRegex(AuthoringValidationError, "requires at least"):
            validate_phase3_route_transaction(
                empty_snapshot(), transaction, route  # type: ignore[arg-type]
            )


if __name__ == "__main__":
    unittest.main()
