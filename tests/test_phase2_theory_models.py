"""Executable contracts for Phase 2 typed theory payloads."""

from __future__ import annotations

import unittest

from pydantic import ValidationError
from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src on sys.path

from econ_theorist.codec import canonical_json_bytes
from econ_theorist.models import (
    ArtifactDependencyRef,
    DecisionVersionRef,
    EntityVersionRef,
)
from econ_theorist.theory import (
    AbsorptionAssessment,
    AssumptionMap,
    AssumptionRecord,
    BlindCaseManifest,
    EconomicArgumentEdge,
    EconomicArgumentGraph,
    EconomicArgumentNode,
    FrozenPrediction,
    GateDossier,
    GateRequirement,
    MechanismPairComparison,
    MechanismTournament,
    PredictionReconciliation,
    PredictionRegister,
    ReducedRational,
    ResearchQuestion,
    THEORY_PAYLOAD_MODELS,
    THEORY_PAYLOAD_OWNER_FACETS,
    ValidatedArgumentPackage,
    pack_theory_payload,
    parse_theory_payload,
    theory_schema_id,
    validate_prediction_register_update,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def aref(artifact_id: str, digest: str = DIGEST_A) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id,
        version=1,
        content_hash=digest,
    )


def dref(decision_id: str) -> DecisionVersionRef:
    return DecisionVersionRef(decision_id=decision_id, version=1)


def question() -> ResearchQuestion:
    return ResearchQuestion(
        phenomenon="More precise information can reduce realized accuracy.",
        object_to_explain="The receiver's realized decision accuracy.",
        unresolved_delta="The benchmark conditions on processing and misses participation.",
        importance="It changes how information quality should be interpreted.",
        kill_condition="Stop if the benchmark already implies the reversal.",
        proposed_scope="Binary state and ex-ante indivisible processing.",
        candidate_archetypes=("mechanism_explanation",),
        prohibited_claims=("Coarse information is always better.",),
    )


def frozen_prediction() -> FrozenPrediction:
    return FrozenPrediction(
        prediction_id="prediction.reversal",
        hypothesis_ref=eref("mechanism.attention_margin"),
        predicted_result="Accuracy reverses only between the two processing thresholds.",
        proposed_economic_chain=(
            "precision raises gross value linearly",
            "processing cost rises quadratically",
            "high precision is not processed",
        ),
        expected_conditions=("0 < ell < h <= 1", "attention is indivisible"),
        expected_ablation_outcome="Constant processing cost removes the reversal.",
        expected_rival_difference="Conditional on processing, the rival predicts high precision wins.",
        surprise_or_falsifier="A reversal under continuous attention falsifies indivisibility.",
        frozen_at="2026-07-11T12:00:00Z",
    )


def register(*reconciliations: PredictionReconciliation) -> PredictionRegister:
    return PredictionRegister(
        question_ref=eref("question.precision"),
        mechanism_tournament_ref=eref("tournament.mechanisms"),
        original_predictions=(frozen_prediction(),),
        reconciliations=reconciliations,
    )


def reconciliation(
    reconciliation_id: str = "reconciliation.reversal",
) -> PredictionReconciliation:
    return PredictionReconciliation(
        reconciliation_id=reconciliation_id,
        prediction_id="prediction.reversal",
        outcome="confirmed",
        observed_result="The exact threshold interval matches the prediction.",
        mechanism_diagnosis="The extensive processing margin creates the reversal.",
        evidence_refs=(eref("examples.precision"), aref("proof.thresholds")),
        recorded_at="2026-07-11T13:00:00Z",
    )


class ReducedRationalTests(unittest.TestCase):
    def test_reduced_rational_accepts_canonical_sign_and_zero(self) -> None:
        self.assertEqual(
            ReducedRational(numerator=-3, denominator=5).model_dump(),
            {"numerator": -3, "denominator": 5},
        )
        self.assertEqual(ReducedRational(numerator=0, denominator=1).numerator, 0)

    def test_reduced_rational_rejects_noncanonical_encodings(self) -> None:
        for values in (
            {"numerator": 2, "denominator": 4},
            {"numerator": 0, "denominator": 2},
            {"numerator": 1, "denominator": 0},
            {"numerator": 1, "denominator": -2},
            {"numerator": 1.0, "denominator": 2},
            {"numerator": 1, "denominator": 2.0},
        ):
            with self.subTest(values=values), self.assertRaises(ValidationError):
                ReducedRational.model_validate(values)


class RegistryAndEnvelopeTests(unittest.TestCase):
    def test_registry_covers_the_contract_and_assigns_one_owner_facet(self) -> None:
        required = {
            "ResearchQuestion",
            "BenchmarkSet",
            "PrimitiveGraph",
            "MechanismHypothesis",
            "MechanismTournament",
            "PredictionRegister",
            "ExampleSuite",
            "EconomicArgumentGraph",
            "ImplementationTournament",
            "FormalModel",
            "FormalizationMap",
            "AssumptionMap",
            "ClaimGraph",
            "ProofObligation",
            "VerificationRecord",
            "VerificationBundle",
            "LiteratureEvidence",
            "ClosestTheoryMap",
            "AbsorptionAssessment",
            "ResultPortfolio",
            "GateDossier",
            "ValidatedArgumentPackage",
            "PreResultBrief",
            "BlindCaseManifest",
            "TransformedVariantManifest",
            "VAPComparisonRecord",
        }
        self.assertEqual(set(THEORY_PAYLOAD_MODELS), required)
        self.assertEqual(set(THEORY_PAYLOAD_OWNER_FACETS), required)
        self.assertEqual(
            THEORY_PAYLOAD_OWNER_FACETS["ResearchQuestion"],
            "economic_interpretation",
        )
        self.assertEqual(THEORY_PAYLOAD_OWNER_FACETS["FormalModel"], "formal")
        self.assertEqual(
            THEORY_PAYLOAD_OWNER_FACETS["AbsorptionAssessment"],
            "literature_novelty",
        )
        self.assertEqual(THEORY_PAYLOAD_OWNER_FACETS["GateDossier"], "authority")

    def test_registered_models_have_no_float_schema_or_derived_predicate_fields(self) -> None:
        forbidden = {
            "question_is_investable",
            "mechanism_is_discriminated",
            "formal_implementation_is_admissible",
            "formal_claim_is_verified",
            "semantic_translation_is_entailed",
            "mechanism_interpretation_is_validated",
            "contribution_is_nonabsorbed",
            "argument_is_validated",
        }
        for name, model in THEORY_PAYLOAD_MODELS.items():
            with self.subTest(model=name):
                self.assertTrue(forbidden.isdisjoint(model.model_fields))
                schema_bytes = canonical_json_bytes(model.model_json_schema())
                self.assertNotIn(b'"type":"number"', schema_bytes)

    def test_round_trip_uses_only_the_primary_facet(self) -> None:
        original = question()
        facets = pack_theory_payload(original)
        self.assertEqual(facets.formal, {})
        self.assertEqual(facets.literature_novelty, {})
        self.assertEqual(facets.terminology_presentation, {})
        self.assertEqual(facets.authority, {})
        self.assertEqual(
            facets.economic_interpretation["schema"],
            theory_schema_id("ResearchQuestion"),
        )
        parsed = parse_theory_payload("ResearchQuestion", facets)
        self.assertEqual(parsed, original)
        self.assertEqual(canonical_json_bytes(pack_theory_payload(parsed)), canonical_json_bytes(facets))

    def test_wrong_schema_cross_facet_content_and_extra_payload_fail_closed(self) -> None:
        facets = pack_theory_payload(question()).model_dump(mode="python")
        wrong_schema = {key: dict(value) for key, value in facets.items()}
        wrong_schema["economic_interpretation"]["schema"] = "wrong"
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            parse_theory_payload("ResearchQuestion", wrong_schema)

        cross_facet = {key: dict(value) for key, value in facets.items()}
        cross_facet["formal"] = {"note": "hidden coupling"}
        with self.assertRaisesRegex(ValueError, "must be empty"):
            parse_theory_payload("ResearchQuestion", cross_facet)

        extra = {key: dict(value) for key, value in facets.items()}
        extra["economic_interpretation"]["payload"] = dict(
            extra["economic_interpretation"]["payload"]
        )
        extra["economic_interpretation"]["payload"]["argument_is_validated"] = True
        with self.assertRaises(ValidationError):
            parse_theory_payload("ResearchQuestion", extra)

    def test_unregistered_type_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered"):
            parse_theory_payload("UnknownTheoryObject", pack_theory_payload(question()))


class PredictionHistoryTests(unittest.TestCase):
    def test_frozen_predictions_stay_byte_identical_and_reconciliation_appends(self) -> None:
        before = register()
        after = register(reconciliation())
        validate_prediction_register_update(before, after)
        validate_prediction_register_update(after, after)

    def test_prediction_edit_and_reconciliation_rewrite_are_rejected(self) -> None:
        before = register(reconciliation())
        edited_prediction = frozen_prediction().model_copy(
            update={"predicted_result": "Post-hoc replacement."}
        )
        edited = PredictionRegister(
            question_ref=before.question_ref,
            mechanism_tournament_ref=before.mechanism_tournament_ref,
            original_predictions=(edited_prediction,),
            reconciliations=before.reconciliations,
        )
        with self.assertRaisesRegex(ValueError, "immutable"):
            validate_prediction_register_update(before, edited)

        rewritten = reconciliation("reconciliation.changed")
        changed_history = register(rewritten)
        with self.assertRaisesRegex(ValueError, "append-only"):
            validate_prediction_register_update(before, changed_history)

        with self.assertRaisesRegex(ValueError, "append-only|truncated"):
            validate_prediction_register_update(before, register())

    def test_unknown_prediction_reconciliation_is_rejected(self) -> None:
        bad = reconciliation().model_copy(update={"prediction_id": "prediction.ghost"})
        with self.assertRaisesRegex(ValidationError, "unknown frozen prediction"):
            register(bad)


class ScientificShapeTests(unittest.TestCase):
    def test_mechanism_tournament_requires_real_member_rival_or_exact_waiver(self) -> None:
        selected = eref("mechanism.attention")
        rival = eref("mechanism.direct_information")
        valid = MechanismTournament(
            question_ref=eref("question.precision"),
            hypothesis_refs=(selected, rival),
            comparisons=(
                MechanismPairComparison(
                    left_ref=selected,
                    right_ref=rival,
                    distinct_arrow_or_signature="Participation changes only under attention margin.",
                    decisive_test="Hold processing fixed and vary precision.",
                ),
            ),
            proposed_selected_ref=selected,
            serious_rival_refs=(rival,),
            selection_rationale="Only the attention margin predicts nonprocessing.",
        )
        self.assertEqual(valid.serious_rival_refs, (rival,))

        with self.assertRaisesRegex(ValidationError, "serious rival or exact waiver"):
            MechanismTournament(
                question_ref=eref("question.precision"),
                hypothesis_refs=(selected,),
                proposed_selected_ref=selected,
                selection_rationale="Convenient but unsupported.",
            )

        waived = MechanismTournament(
            question_ref=eref("question.precision"),
            hypothesis_refs=(selected,),
            proposed_selected_ref=selected,
            rivalry_waiver_ref=aref("waiver.rivalry"),
            selection_rationale="Foundational archetype uses an independence test.",
        )
        self.assertIsNotNone(waived.rivalry_waiver_ref)

    def test_argument_graph_rejects_dangling_economic_arrow(self) -> None:
        node = EconomicArgumentNode(
            node_id="node.wedge",
            kind="primitive",
            statement="Precision changes processing cost.",
        )
        edge = EconomicArgumentEdge(
            edge_id="edge.dangling",
            source_node_id=node.node_id,
            target_node_id="node.missing",
            economic_meaning="The cost response changes participation.",
            effect_kind="direct",
            load_bearing=True,
            primitive_or_assumption_refs=(eref("primitive.graph"),),
            supporting_case_ids=("case.mechanism_on",),
            conclusion_ids=("claim.reversal",),
        )
        with self.assertRaisesRegex(ValidationError, "endpoint"):
            EconomicArgumentGraph(
                selected_mechanism_ref=eref("mechanism.attention"),
                primitive_graph_ref=eref("primitive.graph"),
                prediction_register_ref=eref("predictions"),
                example_suite_ref=eref("examples"),
                nodes=(node,),
                edges=(edge,),
            )

    def test_result_necessity_requires_exact_evidence(self) -> None:
        record_values = {
            "assumption_id": "assumption.indivisible",
            "exact_content": "d is binary",
            "quantifiers": ("d in {0,1}",),
            "economic_interpretation": "Attention is indivisible.",
            "foundation": "primitive",
            "roles": ("mechanism",),
            "satisfying_case_ids": ("case.mechanism_on",),
            "scope_cost": "Excludes divisible effort.",
            "necessity_status": "result_necessary",
        }
        with self.assertRaisesRegex(ValidationError, "requires exact evidence"):
            AssumptionRecord(**record_values)

        record = AssumptionRecord(
            **record_values,
            necessity_evidence_refs=(eref("examples.continuous_attention"),),
        )
        amap = AssumptionMap(
            formal_model_ref=eref("formal.indivisible"),
            formalization_map_ref=eref("formalization.indivisible"),
            assumptions=(record,),
        )
        self.assertEqual(amap.assumptions[0].necessity_status, "result_necessary")

    def test_absorption_preserves_outcome_logic_without_certifying_formal_truth(self) -> None:
        absorbed = AbsorptionAssessment(
            closest_theory_map_ref=eref("closest.adoption_threshold"),
            central_claim_graph_ref=eref("claims.reversal"),
            central_claim_id="claim.reversal",
            outcome="absorbed",
            rationale="An exact adoption-threshold translation delivers the result.",
            standard_argument_refs=(aref("proof.standard_argument"),),
            recommended_route="mutate",
        )
        self.assertNotIn("formal_claim_is_verified", type(absorbed).model_fields)
        self.assertNotIn("argument_is_validated", type(absorbed).model_fields)

        with self.assertRaisesRegex(ValidationError, "cannot recommend proceeding"):
            absorbed.model_copy(update={"recommended_route": "proceed"}).__class__(
                **absorbed.model_copy(update={"recommended_route": "proceed"}).model_dump()
            )
        with self.assertRaisesRegex(ValidationError, "first mapping failure"):
            AbsorptionAssessment(
                closest_theory_map_ref=eref("closest.adoption_threshold"),
                central_claim_graph_ref=eref("claims.reversal"),
                central_claim_id="claim.reversal",
                outcome="nonabsorbed",
                rationale="Unsupported differentiation.",
                recommended_route="proceed",
            )


class AuthorityAndBlindnessTests(unittest.TestCase):
    def test_gate_dossier_preserves_exact_order_and_rejects_duplicate_refs(self) -> None:
        first = eref("question.precision")
        second = eref("benchmarks.precision")
        dossier = GateDossier(
            gate_kind="G1_question_benchmark",
            research_question_ref=first,
            ordered_object_refs=(first, second),
            requirements=(
                GateRequirement(
                    requirement_id="requirement.delta",
                    description="State the exact unresolved benchmark delta.",
                    evidence_refs=(first, second),
                    recorded_condition="evidence_supplied",
                ),
            ),
            proposed_action="approve",
            rationale="The delta is explicit; human confirmation remains separate.",
            prepared_at="2026-07-11T14:00:00Z",
        )
        self.assertEqual(dossier.ordered_object_refs, (first, second))
        with self.assertRaisesRegex(ValidationError, "must be unique"):
            dossier.__class__(**{**dossier.model_dump(), "ordered_object_refs": (first, first)})
        with self.assertRaisesRegex(ValidationError, "research_question_ref"):
            dossier.__class__(
                **{
                    **dossier.model_dump(),
                    "research_question_ref": eref("question.other").model_dump(),
                }
            )

    def test_blind_case_requires_disjoint_generator_and_evaluator_compartments(self) -> None:
        valid = BlindCaseManifest(
            case_id="case.precision.transformed",
            layer="transformed",
            pre_result_brief_ref=eref("brief.precision"),
            gold_package_ref=eref("vap.gold"),
            source_paper_refs=(aref("source.paper"),),
            gold_semantic_refs=(eref("vap.gold"), aref("gold.signature", DIGEST_B)),
            hidden_probe_refs=(aref("probe.transfer"),),
            answer_key_ref=aref("answer.key"),
            generator_compartments=("blind_generator",),
            evaluator_compartments=("sealed_gold",),
            attempt_id="attempt.001",
        )
        self.assertEqual(valid.layer, "transformed")
        with self.assertRaisesRegex(ValidationError, "must be disjoint"):
            BlindCaseManifest(
                **{
                    **valid.model_dump(),
                    "evaluator_compartments": ("blind_generator",),
                }
            )

    def test_evaluation_only_package_cannot_claim_external_novelty(self) -> None:
        values = {
            "question_ref": eref("question.precision"),
            "benchmark_set_ref": eref("benchmarks.precision"),
            "primitive_graph_ref": eref("primitives.precision"),
            "selected_mechanism_ref": eref("mechanism.attention"),
            "serious_rejected_rival_refs": (eref("mechanism.direct"),),
            "prediction_register_ref": eref("predictions.precision"),
            "example_suite_ref": eref("examples.precision"),
            "economic_argument_graph_ref": eref("argument.precision"),
            "implementation_tournament_ref": eref("implementations.precision"),
            "formal_model_ref": eref("formal.precision"),
            "formalization_map_ref": eref("formalization.precision"),
            "assumption_map_ref": eref("assumptions.precision"),
            "claim_graph_ref": eref("claims.precision"),
            "verification_bundle_ref": eref("verification.precision"),
            "closest_theory_map_ref": eref("closest.precision"),
            "absorption_assessment_ref": eref("absorption.precision"),
            "result_portfolio_ref": eref("portfolio.precision"),
            "prior_gate_decision_refs": (
                dref("gate.g1"),
                dref("gate.g2"),
                dref("gate.g3"),
                dref("gate.g4"),
            ),
            "g5_dossier_ref": eref("dossier.g5"),
            "economic_nugget": "Precision can deter indivisible attention.",
            "qualified_novelty": "Evaluation fixture; no external novelty claimed.",
            "unresolved_risks": ("Public classic may be memorized.",),
            "prohibited_overclaims": ("Endogenous attention always reverses accuracy.",),
            "release_mode": "evaluation_only",
            "novelty_claim_mode": "none",
        }
        package = ValidatedArgumentPackage(**values)
        self.assertEqual(package.release_mode, "evaluation_only")
        self.assertNotIn("argument_is_validated", type(package).model_fields)
        with self.assertRaisesRegex(ValidationError, "cannot make an external novelty claim"):
            ValidatedArgumentPackage(**{**values, "novelty_claim_mode": "qualified"})


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
