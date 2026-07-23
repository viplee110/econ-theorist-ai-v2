"""Red tests for Phase 2 route-specific scientific closure.

The generic Phase 2 models deliberately validate shape.  These tests define
the additional cross-object floors required by the ``mechanism_explanation``
vertical slice.  The unmodified reference fixture must remain admissible;
each negative mutation should be rejected by ``validate_theory_projection``.

Until the route-specific closure helpers are implemented, the negative tests
are expected to fail because the current projection validator accepts the
mutations.  They are intentionally not decorated with ``expectedFailure``:
Phase 2 must not be accepted while any scientific floor below stays red.
"""

from __future__ import annotations

import hashlib
import unittest
from collections.abc import Callable

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    Decision,
    DecisionVersionRef,
    EffectiveDecisionRef,
    EntityVersion,
    EntityVersionRef,
    RecordDecisionOp,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from econ_theorist.theory import (
    AbsorptionAssessment,
    AssumptionMap,
    AssumptionRecord,
    BenchmarkRecord,
    BenchmarkSet,
    ClaimGraph,
    ClaimNode,
    ClosestTheoryDimension,
    ClosestTheoryMap,
    EconomicArgumentEdge,
    EconomicArgumentGraph,
    EconomicArgumentNode,
    EconomicToFormalEntry,
    ExampleCase,
    ExampleSuite,
    FormalModel,
    FormalObject,
    FormalToEconomicEntry,
    FormalizationMap,
    FrozenPrediction,
    GateDossier,
    GateRequirement,
    ImplementationPairComparison,
    ImplementationTournament,
    LiteratureAssertion,
    LiteratureEvidence,
    MechanismHypothesis,
    MechanismPairComparison,
    MechanismStep,
    MechanismTournament,
    PortfolioItem,
    PredictionReconciliation,
    PredictionRegister,
    PrimitiveEdge,
    PrimitiveGraph,
    PrimitiveNode,
    ProofObligation,
    ResearchQuestion,
    ResultPortfolio,
    TheoryPayload,
    ValidatedArgumentPackage,
    VerificationBundle,
    VerificationRecord,
    pack_theory_payload,
    parse_theory_entity,
)
from econ_theorist.theory_validation import (
    TheoryValidationError,
    _gate_dossier_is_fresh,
    _typed_reference_closure_is_current_and_fresh,
    validate_phase2_human_gate_transaction,
    validate_theory_projection,
)


PROJECT_ID = "project.phase2.scientific.closure"
HUMAN = Actor(kind="human", actor_id="human.closure.owner")
TOOL = Actor(kind="deterministic_tool", actor_id="tool.analytic.checker")
CREATED_AT = "2026-07-11T16:00:00Z"


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def _digest(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _artifact(artifact_id: str) -> ArtifactRegistration:
    return ArtifactRegistration(
        artifact_id=artifact_id,
        version=1,
        project_id=PROJECT_ID,
        logical_name=f"{artifact_id}.txt",
        media_type="text/plain",
        content_hash=_digest(artifact_id),
        byte_size=len(artifact_id.encode("utf-8")),
        created_at=CREATED_AT,
    )


def _aref(artifact: ArtifactRegistration) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact.artifact_id,
        version=artifact.version,
        content_hash=artifact.content_hash,
    )


def _entity(
    entity_id: str,
    payload: TheoryPayload,
    *,
    version: int = 1,
    supersedes: EntityVersionRef | None = None,
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=version,
        project_id=PROJECT_ID,
        title=entity_id,
        summary=f"Scientific-closure fixture for {type(payload).__name__}.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=pack_theory_payload(payload),
        created_at=CREATED_AT,
        supersedes=supersedes,
    )


class ClosureFixture:
    """A coherent, exact mechanism-explanation package for negative mutation."""

    def __init__(self) -> None:
        artifact_ids = (
            "artifact.example.benchmark",
            "artifact.example.mechanism",
            "artifact.example.ablation",
            "artifact.example.separator",
            "artifact.example.boundary",
            "artifact.formal.selected",
            "artifact.formal.contrast",
            "artifact.mapping",
            "artifact.proof.threshold",
            "artifact.proof.boundary",
            "artifact.literature",
            "artifact.rivalry.waiver",
        )
        self.artifacts = {item: _artifact(item) for item in artifact_ids}
        self.entities: dict[tuple[str, int], EntityVersion] = {}
        self.decisions: dict[tuple[str, int], Decision] = {}
        self._build()

    def artifact_ref(self, artifact_id: str) -> ArtifactDependencyRef:
        return _aref(self.artifacts[artifact_id])

    def add(self, entity: EntityVersion) -> None:
        self.entities[(entity.entity_id, entity.version)] = entity

    def payload(self, entity_id: str, version: int = 1) -> TheoryPayload:
        return parse_theory_entity(self.entities[(entity_id, version)])

    def replace_payload(
        self, entity_id: str, payload: TheoryPayload, *, version: int = 1
    ) -> None:
        previous = self.entities[(entity_id, version)]
        self.entities[(entity_id, version)] = previous.model_copy(
            update={"facets": pack_theory_payload(payload)}
        )

    def validate(self) -> None:
        validate_theory_projection(
            tuple(self.entities.values()),
            tuple(self.artifacts.values()),
            tuple(self.decisions.values()),
        )

    def _example(
        self,
        case_id: str,
        role: str,
        artifact_id: str,
        result: str,
    ) -> ExampleCase:
        return ExampleCase(
            case_id=case_id,
            roles=(role,),  # type: ignore[arg-type]
            setup=f"Exact setup for {role}.",
            primitive_to_choice_trace=("precision changes processing surplus",),
            interaction_to_outcome_trace=("processing determines realized accuracy",),
            result=result,
            method="hand_solved",
            solution_artifact_ref=self.artifact_ref(artifact_id),
            assumption_ids=("assumption.binary_attention",),
        )

    def _gate(
        self,
        kind: str,
        ordered_refs: tuple[EntityVersionRef, ...],
        prepared_at: str,
    ) -> EntityVersion:
        suffix = kind.split("_", 1)[0].lower()
        question_ref = eref("question.closure")
        return _entity(
            f"dossier.{suffix}.closure",
            GateDossier(
                gate_kind=kind,  # type: ignore[arg-type]
                research_question_ref=question_ref,
                ordered_object_refs=(question_ref, *ordered_refs),
                requirements=(
                    GateRequirement(
                        requirement_id=f"requirement.{suffix}.closure",
                        description=f"Exact evidence for {kind} is supplied.",
                        evidence_refs=(question_ref, *ordered_refs),
                        recorded_condition="evidence_supplied",
                    ),
                ),
                proposed_action="approve",
                rationale=f"The {kind} fixture is ready for human review.",
                prepared_at=prepared_at,
            ),
        )

    def _decision(
        self,
        kind: str,
        dossier: EntityVersion,
        decided_at: str,
    ) -> Decision:
        suffix = kind.split("_", 1)[0].lower()
        return Decision(
            decision_id=f"decision.{suffix}.closure",
            version=1,
            project_id=PROJECT_ID,
            decision_kind=kind,  # type: ignore[arg-type]
            subject_ref=dossier.entity_id,
            scope_ref="question.closure",
            question=f"Approve the exact {kind} dossier?",
            options=("approve", "deny"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve the exact fixture dossier.",
            rationale="Every required fixture object is present.",
            evidence_refs=(dossier.entity_id,),
            required_authority="L2",
            decider=HUMAN,
            decided_at=decided_at,
            status="confirmed",
        )

    def _build(self) -> None:
        qref = eref("question.closure")
        bref = eref("benchmarks.closure")
        pref = eref("primitives.closure")
        selected_ref = eref("mechanism.selected.closure")
        rival_ref = eref("mechanism.rival.closure")
        tournament_ref = eref("tournament.mechanisms.closure")
        predictions_v1_ref = eref("predictions.closure", 1)
        predictions_v2_ref = eref("predictions.closure", 2)
        examples_ref = eref("examples.closure")
        argument_ref = eref("argument.closure")
        selected_model_ref = eref("model.selected.closure")
        contrast_model_ref = eref("model.contrast.closure")
        implementation_ref = eref("tournament.implementations.closure")
        mapping_ref = eref("formalization.closure")
        assumptions_ref = eref("assumptions.closure")
        claims_ref = eref("claims.closure")
        threshold_obligation_ref = eref("obligation.threshold.closure")
        boundary_obligation_ref = eref("obligation.boundary.closure")
        threshold_record_ref = eref("verification.threshold.closure")
        boundary_record_ref = eref("verification.boundary.closure")
        verification_ref = eref("verification.bundle.closure")
        literature_ref = eref("literature.closure")
        closest_ref = eref("closest.closure")
        absorption_ref = eref("absorption.closure")
        portfolio_ref = eref("portfolio.closure")

        self.add(
            _entity(
                qref.entity_id,
                ResearchQuestion(
                    phenomenon="More precise information can reduce realized accuracy.",
                    object_to_explain="The reversal in the precision ranking.",
                    unresolved_delta="The benchmark fixes information processing.",
                    importance="Information quality changes whether information is used.",
                    kill_condition="The reversal survives fixed processing.",
                    proposed_scope="Binary states, actions, and indivisible attention.",
                    candidate_archetypes=("mechanism_explanation",),
                    prohibited_claims=("Accuracy is welfare without an objective.",),
                ),
            )
        )
        self.add(
            _entity(
                bref.entity_id,
                BenchmarkSet(
                    question_ref=qref,
                    benchmarks=(
                        BenchmarkRecord(
                            benchmark_id="benchmark.fixed.processing",
                            label="Fixed processing",
                            exact_primitives=("one receiver", "binary state"),
                            timing=("signal", "action"),
                            solution_concept="optimal binary action",
                            prediction="higher precision improves conditional accuracy",
                            unresolved_delta="processing participation is absent",
                        ),
                    ),
                    exact_question_delta="Endogenize indivisible processing.",
                ),
            )
        )
        self.add(
            _entity(
                pref.entity_id,
                PrimitiveGraph(
                    question_ref=qref,
                    benchmark_set_ref=bref,
                    nodes=(
                        PrimitiveNode(
                            node_id="primitive.precision",
                            kind="information",
                            label="Precision",
                            economic_meaning="Precision raises conditional accuracy.",
                            status="primitive",
                        ),
                        PrimitiveNode(
                            node_id="primitive.attention",
                            kind="choice",
                            label="Attention",
                            economic_meaning="The receiver chooses whether to process.",
                            status="primitive",
                        ),
                        PrimitiveNode(
                            node_id="primitive.accuracy",
                            kind="outcome",
                            label="Accuracy",
                            economic_meaning="The action matches the state.",
                            status="derived",
                        ),
                    ),
                    edges=(
                        PrimitiveEdge(
                            edge_id="primitive.edge.precision.attention",
                            source_node_id="primitive.precision",
                            target_node_id="primitive.attention",
                            economic_meaning="Precision changes processing surplus.",
                        ),
                        PrimitiveEdge(
                            edge_id="primitive.edge.attention.accuracy",
                            source_node_id="primitive.attention",
                            target_node_id="primitive.accuracy",
                            economic_meaning="Processing determines realized accuracy.",
                        ),
                    ),
                ),
            )
        )

        selected = MechanismHypothesis(
            question_ref=qref,
            primitive_graph_ref=pref,
            decision_margin_or_foundational_distinction="Whether to process.",
            initiating_wedge="Precision raises convex processing cost.",
            force_chain=(
                MechanismStep(
                    step_id="step.extensive.margin",
                    source="higher precision",
                    response_or_constraint="reduces processing surplus",
                    target="attention participation",
                    economic_meaning="A precise signal can be ignored.",
                    effect_kind="conflict",
                ),
            ),
            predicted_consequence="Only the coarse signal is processed in the reversal region.",
            boundary="The effect disappears with fixed or divisible attention.",
            expected_load_bearing_conditions=("indivisible attention",),
            distinguishing_signature="The reversal disappears under fixed processing.",
            killer_test="Force processing and recompute the ranking.",
        )
        rival = MechanismHypothesis(
            question_ref=qref,
            primitive_graph_ref=pref,
            decision_margin_or_foundational_distinction="Conditional informativeness.",
            initiating_wedge="Precision raises signal accuracy.",
            force_chain=(
                MechanismStep(
                    step_id="step.direct.information",
                    source="higher precision",
                    response_or_constraint="raises conditional accuracy",
                    target="realized accuracy",
                    economic_meaning="More information helps when it is processed.",
                    effect_kind="direct",
                ),
            ),
            predicted_consequence="Higher precision weakly improves accuracy.",
            boundary="Processing is fixed at one.",
            expected_load_bearing_conditions=("fixed processing",),
            distinguishing_signature="No coarse advantage under fixed processing.",
            killer_test="Observe a coarse advantage with processing fixed.",
        )
        self.add(_entity(selected_ref.entity_id, selected))
        self.add(_entity(rival_ref.entity_id, rival))
        self.add(
            _entity(
                tournament_ref.entity_id,
                MechanismTournament(
                    question_ref=qref,
                    hypothesis_refs=(selected_ref, rival_ref),
                    comparisons=(
                        MechanismPairComparison(
                            left_ref=selected_ref,
                            right_ref=rival_ref,
                            distinct_arrow_or_signature="Only the selected mechanism changes participation.",
                            decisive_test="Fix processing and compare rankings.",
                        ),
                    ),
                    proposed_selected_ref=selected_ref,
                    serious_rival_refs=(rival_ref,),
                    selection_rationale="The fixed-processing separator rejects the rival.",
                ),
            )
        )

        frozen = (
            FrozenPrediction(
                prediction_id="prediction.selected",
                hypothesis_ref=selected_ref,
                predicted_result="Coarse precision wins when only it is processed.",
                proposed_economic_chain=("precision changes participation",),
                expected_conditions=("indivisible attention",),
                expected_ablation_outcome="Fixed processing removes the reversal.",
                expected_rival_difference="The direct rival remains monotone.",
                surprise_or_falsifier="A strict reversal with fixed processing.",
                frozen_at="2026-07-11T16:05:00Z",
            ),
            FrozenPrediction(
                prediction_id="prediction.rival",
                hypothesis_ref=rival_ref,
                predicted_result="Higher precision wins conditional on processing.",
                proposed_economic_chain=("precision raises conditional accuracy",),
                expected_conditions=("processing occurs",),
                expected_ablation_outcome="The monotone ranking remains.",
                expected_rival_difference="Participation does not enter the chain.",
                surprise_or_falsifier="A coarse advantage with processing fixed.",
                frozen_at="2026-07-11T16:05:00Z",
            ),
        )
        predictions_v1 = PredictionRegister(
            question_ref=qref,
            mechanism_tournament_ref=tournament_ref,
            original_predictions=frozen,
        )
        self.add(_entity(predictions_v1_ref.entity_id, predictions_v1))

        cases = (
            self._example(
                "case.benchmark",
                "benchmark",
                "artifact.example.benchmark",
                "Both signals are processed and high precision wins.",
            ),
            self._example(
                "case.mechanism",
                "mechanism_on",
                "artifact.example.mechanism",
                "Only the coarse signal is processed.",
            ),
            self._example(
                "case.ablation",
                "ablation",
                "artifact.example.ablation",
                "Fixed processing removes the reversal.",
            ),
            self._example(
                "case.separator",
                "rival_separator",
                "artifact.example.separator",
                "The direct rival predicts the opposite ranking.",
            ),
            self._example(
                "case.boundary",
                "boundary",
                "artifact.example.boundary",
                "At the threshold the tie rule determines processing.",
            ),
        )
        self.add(
            _entity(
                examples_ref.entity_id,
                ExampleSuite(
                    selected_mechanism_ref=selected_ref,
                    frozen_prediction_register_ref=predictions_v1_ref,
                    cases=cases,
                ),
            )
        )
        reconciliations = (
            PredictionReconciliation(
                reconciliation_id="reconciliation.selected",
                prediction_id="prediction.selected",
                outcome="confirmed",
                observed_result="The mechanism-on and ablation cases match the prediction.",
                mechanism_diagnosis="The extensive margin is load bearing.",
                evidence_refs=(examples_ref,),
                recorded_at="2026-07-11T16:06:00Z",
            ),
            PredictionReconciliation(
                reconciliation_id="reconciliation.rival",
                prediction_id="prediction.rival",
                outcome="confirmed",
                observed_result="The fixed-processing separator is monotone.",
                mechanism_diagnosis="The direct force is present but cannot explain the reversal.",
                evidence_refs=(examples_ref,),
                recorded_at="2026-07-11T16:06:00Z",
            ),
        )
        predictions_v2 = predictions_v1.model_copy(
            update={"reconciliations": reconciliations}
        )
        self.add(
            _entity(
                predictions_v2_ref.entity_id,
                predictions_v2,
                version=2,
                supersedes=predictions_v1_ref,
            )
        )

        argument_nodes = (
            EconomicArgumentNode(
                node_id="argument.precision",
                kind="primitive",
                statement="Signal precision rises.",
            ),
            EconomicArgumentNode(
                node_id="argument.attention",
                kind="margin",
                statement="Processing participation falls.",
            ),
            EconomicArgumentNode(
                node_id="argument.accuracy",
                kind="outcome",
                statement="Realized accuracy can fall.",
            ),
        )
        argument_edges = (
            EconomicArgumentEdge(
                edge_id="arrow.precision.attention",
                source_node_id="argument.precision",
                target_node_id="argument.attention",
                economic_meaning="Convex processing cost changes participation.",
                effect_kind="direct",
                load_bearing=True,
                primitive_or_assumption_refs=(pref,),
                formal_witness_refs=(self.artifact_ref("artifact.mapping"),),
                supporting_case_ids=("case.mechanism", "case.ablation"),
                conclusion_ids=("claim.headline",),
            ),
            EconomicArgumentEdge(
                edge_id="arrow.attention.accuracy",
                source_node_id="argument.attention",
                target_node_id="argument.accuracy",
                economic_meaning="Ignored information cannot improve the action.",
                effect_kind="direct",
                load_bearing=True,
                primitive_or_assumption_refs=(pref,),
                formal_witness_refs=(self.artifact_ref("artifact.mapping"),),
                supporting_case_ids=("case.mechanism", "case.separator"),
                conclusion_ids=("claim.headline",),
            ),
        )
        self.add(
            _entity(
                argument_ref.entity_id,
                EconomicArgumentGraph(
                    selected_mechanism_ref=selected_ref,
                    primitive_graph_ref=pref,
                    prediction_register_ref=predictions_v2_ref,
                    example_suite_ref=examples_ref,
                    nodes=argument_nodes,
                    edges=argument_edges,
                ),
            )
        )

        selected_model = FormalModel(
            question_ref=qref,
            selected_mechanism_ref=selected_ref,
            primitive_graph_ref=pref,
            formal_objects=(
                FormalObject(
                    object_id="formal.precision",
                    symbol="x",
                    object_kind="parameter",
                    definition="Signal precision.",
                    central=True,
                ),
                FormalObject(
                    object_id="formal.attention",
                    symbol="d",
                    object_kind="choice",
                    definition="Binary processing choice.",
                    central=True,
                ),
                FormalObject(
                    object_id="formal.accuracy",
                    symbol="Y",
                    object_kind="outcome",
                    definition="Realized accuracy.",
                    central=True,
                ),
            ),
            timing=("precision is chosen", "processing is chosen", "signal arrives"),
            choice_or_strategy_spaces=("d in {0,1}",),
            information_and_beliefs=("binary state with prior one half",),
            feasibility=("0 < x <= 1",),
            solution_concept="Optimal pre-signal processing and action.",
            outcome_definitions=("Y is the probability of a correct action",),
            full_specification_ref=self.artifact_ref("artifact.formal.selected"),
        )
        contrast_model = FormalModel(
            question_ref=qref,
            selected_mechanism_ref=selected_ref,
            primitive_graph_ref=pref,
            formal_objects=(
                FormalObject(
                    object_id="contrast.precision",
                    symbol="x",
                    object_kind="parameter",
                    definition="Signal precision.",
                    central=True,
                ),
                FormalObject(
                    object_id="contrast.effort",
                    symbol="e",
                    object_kind="choice",
                    definition="Divisible attention effort.",
                    central=True,
                ),
            ),
            timing=("precision is chosen", "effort is chosen", "signal arrives"),
            choice_or_strategy_spaces=("e in [0,1]",),
            information_and_beliefs=("binary state with prior one half",),
            feasibility=("0 < x <= 1",),
            solution_concept="Optimal divisible attention.",
            outcome_definitions=("Accuracy uses the processed signal intensity",),
            full_specification_ref=self.artifact_ref("artifact.formal.contrast"),
        )
        self.add(_entity(selected_model_ref.entity_id, selected_model))
        self.add(_entity(contrast_model_ref.entity_id, contrast_model))
        self.add(
            _entity(
                implementation_ref.entity_id,
                ImplementationTournament(
                    selected_mechanism_ref=selected_ref,
                    economic_argument_graph_ref=argument_ref,
                    candidate_model_refs=(selected_model_ref, contrast_model_ref),
                    comparisons=(
                        ImplementationPairComparison(
                            left_model_ref=selected_model_ref,
                            right_model_ref=contrast_model_ref,
                            fidelity_difference="Only the binary model preserves indivisibility.",
                            minimality_difference="Both models are hand solvable.",
                            proof_risk_difference="The binary model has threshold cases.",
                            mapping_transparency_difference="The binary choice directly implements participation.",
                            theorem_leverage_difference="The contrast model identifies the boundary.",
                        ),
                    ),
                    proposed_selected_model_ref=selected_model_ref,
                    contrast_model_refs=(contrast_model_ref,),
                    selection_rationale="The selected model preserves the promoted extensive margin.",
                ),
            )
        )

        economic_to_formal = (
            EconomicToFormalEntry(
                economic_element_id="argument.precision",
                formal_object_ids=("formal.precision",),
                implementation_statement="Precision is parameter x.",
                witness_refs=(self.artifact_ref("artifact.mapping"),),
            ),
            EconomicToFormalEntry(
                economic_element_id="argument.attention",
                formal_object_ids=("formal.attention",),
                implementation_statement="Attention is binary choice d.",
                witness_refs=(self.artifact_ref("artifact.mapping"),),
            ),
            EconomicToFormalEntry(
                economic_element_id="argument.accuracy",
                formal_object_ids=("formal.accuracy",),
                implementation_statement="Accuracy is outcome Y.",
                witness_refs=(self.artifact_ref("artifact.mapping"),),
            ),
            EconomicToFormalEntry(
                economic_element_id="arrow.precision.attention",
                formal_object_ids=("formal.precision", "formal.attention"),
                implementation_statement="Processing surplus falls with precision.",
                witness_refs=(self.artifact_ref("artifact.mapping"),),
            ),
            EconomicToFormalEntry(
                economic_element_id="arrow.attention.accuracy",
                formal_object_ids=("formal.attention", "formal.accuracy"),
                implementation_statement="Only processed signals affect accuracy.",
                witness_refs=(self.artifact_ref("artifact.mapping"),),
            ),
        )
        formal_to_economic = (
            FormalToEconomicEntry(
                formal_object_id="formal.precision",
                economic_identity="Signal precision.",
                research_job="Initiates the conflict between quality and processing.",
                economic_element_ids=("argument.precision", "arrow.precision.attention"),
            ),
            FormalToEconomicEntry(
                formal_object_id="formal.attention",
                economic_identity="Extensive processing margin.",
                research_job="Carries the promoted economic force.",
                economic_element_ids=(
                    "argument.attention",
                    "arrow.precision.attention",
                    "arrow.attention.accuracy",
                ),
            ),
            FormalToEconomicEntry(
                formal_object_id="formal.accuracy",
                economic_identity="Realized decision quality.",
                research_job="Records the economic consequence.",
                economic_element_ids=("argument.accuracy", "arrow.attention.accuracy"),
            ),
        )
        self.add(
            _entity(
                mapping_ref.entity_id,
                FormalizationMap(
                    economic_argument_graph_ref=argument_ref,
                    formal_model_ref=selected_model_ref,
                    economic_to_formal=economic_to_formal,
                    formal_to_economic=formal_to_economic,
                ),
            )
        )

        self.add(
            _entity(
                assumptions_ref.entity_id,
                AssumptionMap(
                    formal_model_ref=selected_model_ref,
                    formalization_map_ref=mapping_ref,
                    assumptions=(
                        AssumptionRecord(
                            assumption_id="assumption.binary_attention",
                            exact_content="Processing is indivisible.",
                            quantifiers=("d belongs to {0,1}",),
                            economic_interpretation="The receiver enters or exits processing.",
                            foundation="primitive",
                            roles=("mechanism", "domain"),
                            dependent_claim_ids=("claim.headline",),
                            proof_obligation_ids=("po.threshold", "po.boundary"),
                            argument_edge_ids=("arrow.precision.attention",),
                            satisfying_case_ids=("case.mechanism", "case.boundary"),
                            violation_attempts=("replace d with divisible effort",),
                            scope_cost="The result does not cover divisible attention.",
                            necessity_status="result_necessary",
                            necessity_evidence_refs=(
                                self.artifact_ref("artifact.example.boundary"),
                            ),
                        ),
                    ),
                ),
            )
        )

        threshold_obligation = ProofObligation(
            claim_graph_ref=claims_ref,
            claim_id="claim.headline",
            obligation_id="po.threshold",
            statement="Derive the exact participation thresholds.",
            burden="necessity",
            quantifier_scope="All admissible coarse and fine precisions.",
            assumption_ids=("assumption.binary_attention",),
            admissible_methods=("analytic_proof",),
        )
        boundary_obligation = ProofObligation(
            claim_graph_ref=claims_ref,
            claim_id="claim.headline",
            obligation_id="po.boundary",
            statement="Verify both threshold endpoints and the tie rule.",
            burden="boundary",
            quantifier_scope="Both exact endpoints.",
            assumption_ids=("assumption.binary_attention",),
            admissible_methods=("analytic_proof",),
        )
        self.add(_entity(threshold_obligation_ref.entity_id, threshold_obligation))
        self.add(_entity(boundary_obligation_ref.entity_id, boundary_obligation))

        claim = ClaimNode(
            claim_id="claim.headline",
            archetype="mechanism_explanation",
            scientific_job="headline",
            formal_statement="Coarse precision yields higher accuracy exactly on the threshold interval.",
            domain="Binary states, actions, and indivisible attention.",
            quantifiers=("for all 0 < ell < h <= 1",),
            assumption_ids=("assumption.binary_attention",),
            semantic_translation="Precision can reduce realized accuracy by deterring processing.",
            dependency_refs=(argument_ref, mapping_ref),
            mechanism_ref=selected_ref,
            proof_obligation_refs=(threshold_obligation_ref, boundary_obligation_ref),
            verification_record_refs=(threshold_record_ref, boundary_record_ref),
            boundary_case_ids=("case.boundary",),
        )
        self.add(
            _entity(
                claims_ref.entity_id,
                ClaimGraph(
                    formal_model_ref=selected_model_ref,
                    formalization_map_ref=mapping_ref,
                    assumption_map_ref=assumptions_ref,
                    claims=(claim,),
                    contribution_spine=("claim.headline",),
                ),
            )
        )

        threshold_record = VerificationRecord(
            obligation_ref=threshold_obligation_ref,
            claim_graph_ref=claims_ref,
            formal_model_ref=selected_model_ref,
            assumption_map_ref=assumptions_ref,
            verifier=TOOL,
            method="analytic_proof",
            outcome="discharged",
            checked_refs=(
                threshold_obligation_ref,
                claims_ref,
                selected_model_ref,
                assumptions_ref,
            ),
            evidence_refs=(self.artifact_ref("artifact.proof.threshold"),),
            limitations="The proof is restricted to indivisible attention.",
            checked_at="2026-07-11T16:12:00Z",
        )
        boundary_record = VerificationRecord(
            obligation_ref=boundary_obligation_ref,
            claim_graph_ref=claims_ref,
            formal_model_ref=selected_model_ref,
            assumption_map_ref=assumptions_ref,
            verifier=TOOL,
            method="analytic_proof",
            outcome="discharged",
            checked_refs=(
                boundary_obligation_ref,
                claims_ref,
                selected_model_ref,
                assumptions_ref,
            ),
            evidence_refs=(self.artifact_ref("artifact.proof.boundary"),),
            limitations="The endpoint conclusion uses the declared tie rule.",
            checked_at="2026-07-11T16:12:01Z",
        )
        self.add(_entity(threshold_record_ref.entity_id, threshold_record))
        self.add(_entity(boundary_record_ref.entity_id, boundary_record))
        self.add(
            _entity(
                verification_ref.entity_id,
                VerificationBundle(
                    claim_graph_ref=claims_ref,
                    proof_obligation_refs=(
                        threshold_obligation_ref,
                        boundary_obligation_ref,
                    ),
                    verification_record_refs=(
                        threshold_record_ref,
                        boundary_record_ref,
                    ),
                    interpretation_evidence_refs=(argument_ref, examples_ref),
                    counterexample_evidence_refs=(
                        self.artifact_ref("artifact.example.boundary"),
                    ),
                ),
            )
        )

        self.add(
            _entity(
                literature_ref.entity_id,
                LiteratureEvidence(
                    question_ref=qref,
                    assertions=(
                        LiteratureAssertion(
                            assertion_id="literature.closest",
                            assertion="The comparator fixes information processing.",
                            source_locator="Comparator, proposition 1.",
                            access_status="full_text",
                            evidence_ref=self.artifact_ref("artifact.literature"),
                            verification_status="source_verified",
                        ),
                    ),
                ),
            )
        )
        dimensions = tuple(
            ClosestTheoryDimension(
                dimension=dimension,  # type: ignore[arg-type]
                project_side=f"Project {dimension}.",
                comparator_side=f"Comparator {dimension}.",
                translation=f"Exact translation for {dimension}.",
                mapping_status=(
                    "fails" if dimension == "primitives" else "exact"
                ),
                evidence_refs=(self.artifact_ref("artifact.literature"),),
            )
            for dimension in (
                "benchmark",
                "primitives",
                "timing",
                "solution_concept",
                "assumptions",
                "quantifiers",
                "formal_result",
                "economic_lesson",
            )
        )
        self.add(
            _entity(
                closest_ref.entity_id,
                ClosestTheoryMap(
                    claim_graph_ref=claims_ref,
                    literature_evidence_ref=literature_ref,
                    comparator_label="Fixed-processing comparator",
                    dimensions=dimensions,
                    classification="different_mechanism",
                    first_mapping_failure="The comparator has no processing choice.",
                ),
            )
        )
        self.add(
            _entity(
                absorption_ref.entity_id,
                AbsorptionAssessment(
                    closest_theory_map_ref=closest_ref,
                    central_claim_graph_ref=claims_ref,
                    central_claim_id="claim.headline",
                    outcome="nonabsorbed",
                    rationale="The processing primitive has no comparator counterpart.",
                    first_mapping_failure="The comparator has no processing choice.",
                    recommended_route="proceed",
                ),
            )
        )
        self.add(
            _entity(
                portfolio_ref.entity_id,
                ResultPortfolio(
                    claim_graph_ref=claims_ref,
                    headline_claim_id="claim.headline",
                    included_results=(
                        PortfolioItem(
                            claim_id="claim.headline",
                            scientific_job="Headline characterization and mechanism.",
                            marginal_value="It states the exact reversal region.",
                        ),
                    ),
                    excluded_results=(),
                    economic_nugget="Better information can deter information use.",
                    reader_belief_update="Conditional quality and realized use must be separated.",
                    economic_consequence="Information design changes participation.",
                ),
            )
        )

        dossier_specs = (
            (
                "G1_question_benchmark",
                (bref, pref),
                "2026-07-11T16:01:00Z",
                "2026-07-11T16:02:00Z",
            ),
            (
                "G2_mechanism",
                (
                    selected_ref,
                    rival_ref,
                    tournament_ref,
                    predictions_v2_ref,
                    examples_ref,
                    argument_ref,
                ),
                "2026-07-11T16:03:00Z",
                "2026-07-11T16:04:00Z",
            ),
            (
                "G3_formal_base",
                (implementation_ref, selected_model_ref, mapping_ref, assumptions_ref),
                "2026-07-11T16:05:00Z",
                "2026-07-11T16:06:00Z",
            ),
            (
                "G4_result_investment",
                (
                    claims_ref,
                    verification_ref,
                    closest_ref,
                    absorption_ref,
                    portfolio_ref,
                ),
                "2026-07-11T16:07:00Z",
                "2026-07-11T16:08:00Z",
            ),
        )
        prior_decision_refs: list[DecisionVersionRef] = []
        for kind, ordered, prepared_at, decided_at in dossier_specs:
            dossier = self._gate(kind, ordered, prepared_at)
            self.add(dossier)
            decision = self._decision(kind, dossier, decided_at)
            self.decisions[(decision.decision_id, decision.version)] = decision
            prior_decision_refs.append(
                DecisionVersionRef(
                    decision_id=decision.decision_id, version=decision.version
                )
            )

        g5 = self._gate(
            "G5_argument_validation",
            (
                claims_ref,
                verification_ref,
                absorption_ref,
                portfolio_ref,
                eref("vap.closure"),
            ),
            "2026-07-11T16:09:00Z",
        )
        self.add(g5)
        self.add(
            _entity(
                "vap.closure",
                ValidatedArgumentPackage(
                    question_ref=qref,
                    benchmark_set_ref=bref,
                    primitive_graph_ref=pref,
                    selected_mechanism_ref=selected_ref,
                    serious_rejected_rival_refs=(rival_ref,),
                    prediction_register_ref=predictions_v2_ref,
                    example_suite_ref=examples_ref,
                    economic_argument_graph_ref=argument_ref,
                    implementation_tournament_ref=implementation_ref,
                    formal_model_ref=selected_model_ref,
                    formalization_map_ref=mapping_ref,
                    assumption_map_ref=assumptions_ref,
                    claim_graph_ref=claims_ref,
                    verification_bundle_ref=verification_ref,
                    closest_theory_map_ref=closest_ref,
                    absorption_assessment_ref=absorption_ref,
                    result_portfolio_ref=portfolio_ref,
                    prior_gate_decision_refs=tuple(prior_decision_refs),
                    g5_dossier_ref=eref(g5.entity_id),
                    economic_nugget="Better information can deter information use.",
                    qualified_novelty="The processing-participation primitive breaks the closest mapping.",
                    unresolved_risks=("External novelty remains subject to G5.",),
                    prohibited_overclaims=("The result is robust to divisible attention.",),
                    release_mode="production_candidate",
                    novelty_claim_mode="qualified",
                ),
            )
        )


class ScientificClosureTests(unittest.TestCase):
    def assertClosureRejected(
        self,
        mutate: Callable[[ClosureFixture], None],
        pattern: str,
    ) -> None:
        fixture = ClosureFixture()
        mutate(fixture)
        with self.assertRaisesRegex(TheoryValidationError, pattern):
            fixture.validate()

    def test_reference_mechanism_explanation_package_is_structurally_admissible(
        self,
    ) -> None:
        ClosureFixture().validate()

    def test_example_suite_requires_all_mechanism_explanation_roles(self) -> None:
        def mutate(fixture: ClosureFixture) -> None:
            suite = fixture.payload("examples.closure")
            assert isinstance(suite, ExampleSuite)
            fixture.replace_payload(
                "examples.closure",
                suite.model_copy(update={"cases": suite.cases[:2]}),
            )

        self.assertClosureRejected(
            mutate,
            r"(?i)(functional role|ablation|rival.?separator|boundary)",
        )

    def test_mechanism_promotion_requires_rival_ablation_separator_and_reconciliation(
        self,
    ) -> None:
        def no_serious_rival(fixture: ClosureFixture) -> None:
            tournament = fixture.payload("tournament.mechanisms.closure")
            assert isinstance(tournament, MechanismTournament)
            fixture.replace_payload(
                "tournament.mechanisms.closure",
                tournament.model_copy(
                    update={
                        "serious_rival_refs": (),
                        "rivalry_waiver_ref": fixture.artifact_ref(
                            "artifact.rivalry.waiver"
                        ),
                    }
                ),
            )

        def without_role(role: str) -> Callable[[ClosureFixture], None]:
            def mutate(fixture: ClosureFixture) -> None:
                suite = fixture.payload("examples.closure")
                assert isinstance(suite, ExampleSuite)
                fixture.replace_payload(
                    "examples.closure",
                    suite.model_copy(
                        update={
                            "cases": tuple(
                                case for case in suite.cases if role not in case.roles
                            )
                        }
                    ),
                )

            return mutate

        def missing_reconciliation(fixture: ClosureFixture) -> None:
            register = fixture.payload("predictions.closure", 2)
            assert isinstance(register, PredictionRegister)
            fixture.replace_payload(
                "predictions.closure",
                register.model_copy(
                    update={"reconciliations": register.reconciliations[:1]}
                ),
                version=2,
            )

        cases = (
            ("serious rival", no_serious_rival),
            ("ablation", without_role("ablation")),
            ("separator", without_role("rival_separator")),
            ("reconciliation", missing_reconciliation),
        )
        for label, mutate in cases:
            with self.subTest(missing=label):
                self.assertClosureRejected(
                    mutate,
                    rf"(?i)({label}|mechanism promotion|prediction)",
                )

    def test_formalization_requires_arrow_and_formal_object_coverage(self) -> None:
        def missing_load_bearing_arrow(fixture: ClosureFixture) -> None:
            mapping = fixture.payload("formalization.closure")
            assert isinstance(mapping, FormalizationMap)
            fixture.replace_payload(
                "formalization.closure",
                mapping.model_copy(
                    update={
                        "economic_to_formal": tuple(
                            item
                            for item in mapping.economic_to_formal
                            if item.economic_element_id
                            != "arrow.precision.attention"
                        )
                    }
                ),
            )

        def unknown_formal_id(fixture: ClosureFixture) -> None:
            mapping = fixture.payload("formalization.closure")
            assert isinstance(mapping, FormalizationMap)
            entries = list(mapping.economic_to_formal)
            entries[0] = entries[0].model_copy(
                update={"formal_object_ids": ("formal.ghost",)}
            )
            fixture.replace_payload(
                "formalization.closure",
                mapping.model_copy(update={"economic_to_formal": tuple(entries)}),
            )

        def uninterpreted_central_formal_object(fixture: ClosureFixture) -> None:
            mapping = fixture.payload("formalization.closure")
            assert isinstance(mapping, FormalizationMap)
            fixture.replace_payload(
                "formalization.closure",
                mapping.model_copy(
                    update={
                        "formal_to_economic": tuple(
                            item
                            for item in mapping.formal_to_economic
                            if item.formal_object_id != "formal.accuracy"
                        )
                    }
                ),
            )

        cases = (
            ("arrow coverage", missing_load_bearing_arrow),
            ("formal object id", unknown_formal_id),
            ("reverse coverage", uninterpreted_central_formal_object),
        )
        for label, mutate in cases:
            with self.subTest(missing=label):
                self.assertClosureRejected(
                    mutate,
                    r"(?i)(formalization|load.?bearing|arrow|formal object|coverage)",
                )

    def test_claim_obligation_and_verification_must_close_exactly(self) -> None:
        def obligation_names_foreign_claim(fixture: ClosureFixture) -> None:
            obligation = fixture.payload("obligation.threshold.closure")
            assert isinstance(obligation, ProofObligation)
            fixture.replace_payload(
                "obligation.threshold.closure",
                obligation.model_copy(update={"claim_id": "claim.ghost"}),
            )

        def bundle_omits_required_record(fixture: ClosureFixture) -> None:
            bundle = fixture.payload("verification.bundle.closure")
            assert isinstance(bundle, VerificationBundle)
            fixture.replace_payload(
                "verification.bundle.closure",
                bundle.model_copy(
                    update={
                        "verification_record_refs": bundle.verification_record_refs[:1]
                    }
                ),
            )

        def retained_claim_has_falsified_obligation(
            fixture: ClosureFixture,
        ) -> None:
            record = fixture.payload("verification.boundary.closure")
            assert isinstance(record, VerificationRecord)
            fixture.replace_payload(
                "verification.boundary.closure",
                record.model_copy(update={"outcome": "falsified"}),
            )

        cases = (
            ("claim mismatch", obligation_names_foreign_claim),
            ("bundle completeness", bundle_omits_required_record),
            ("falsified retained claim", retained_claim_has_falsified_obligation),
        )
        for label, mutate in cases:
            with self.subTest(inconsistency=label):
                self.assertClosureRejected(
                    mutate,
                    r"(?i)(claim|obligation|verification|falsified|bundle)",
                )

    def test_result_portfolio_claims_must_belong_to_claim_graph(self) -> None:
        def mutate(fixture: ClosureFixture) -> None:
            portfolio = fixture.payload("portfolio.closure")
            assert isinstance(portfolio, ResultPortfolio)
            ghost = portfolio.included_results[0].model_copy(
                update={"claim_id": "claim.ghost"}
            )
            fixture.replace_payload(
                "portfolio.closure",
                portfolio.model_copy(
                    update={
                        "headline_claim_id": "claim.ghost",
                        "included_results": (ghost,),
                    }
                ),
            )

        self.assertClosureRejected(
            mutate,
            r"(?i)(portfolio|claim graph|unknown claim|membership)",
        )

    def test_production_vap_floors_are_noncompensatory(self) -> None:
        def missing_proof_floor(fixture: ClosureFixture) -> None:
            record = fixture.payload("verification.threshold.closure")
            assert isinstance(record, VerificationRecord)
            fixture.replace_payload(
                "verification.threshold.closure",
                record.model_copy(update={"outcome": "inconclusive"}),
            )

        def missing_boundary_floor(fixture: ClosureFixture) -> None:
            graph = fixture.payload("claims.closure")
            assert isinstance(graph, ClaimGraph)
            claim = graph.claims[0].model_copy(update={"boundary_case_ids": ()})
            fixture.replace_payload(
                "claims.closure",
                graph.model_copy(update={"claims": (claim,)}),
            )

        def missing_mapping_floor(fixture: ClosureFixture) -> None:
            mapping = fixture.payload("formalization.closure")
            assert isinstance(mapping, FormalizationMap)
            fixture.replace_payload(
                "formalization.closure",
                mapping.model_copy(
                    update={
                        "economic_to_formal": tuple(
                            item
                            for item in mapping.economic_to_formal
                            if item.economic_element_id
                            != "arrow.attention.accuracy"
                        )
                    }
                ),
            )

        def missing_absorption_translation_floor(
            fixture: ClosureFixture,
        ) -> None:
            closest = fixture.payload("closest.closure")
            assert isinstance(closest, ClosestTheoryMap)
            fixture.replace_payload(
                "closest.closure",
                closest.model_copy(update={"dimensions": closest.dimensions[:1]}),
            )

        cases = (
            ("proof", missing_proof_floor),
            ("boundary", missing_boundary_floor),
            ("mapping", missing_mapping_floor),
            ("absorption", missing_absorption_translation_floor),
        )
        for label, mutate in cases:
            with self.subTest(missing_floor=label):
                self.assertClosureRejected(
                    mutate,
                    rf"(?i)({label}|VAP|non.?compensatory|scientific floor)",
                )


class G3DossierFreshnessTests(unittest.TestCase):
    """Keep promoted-model audit history distinct from live G3 dependencies."""

    def _snapshot_and_approval(
        self,
        *,
        include_unrelated_stale_ref: bool = False,
        use_unrelated_necessity_evidence: bool = False,
        cycle_tournament_argument_to_assumptions: bool = False,
        supersede_tournament_argument: bool = False,
        supersede_promoted_model: bool = False,
        supersede_mapping: bool = False,
    ) -> tuple[Snapshot, EntityVersion, GateDossier, Transaction]:
        fixture = ClosureFixture()
        question_ref = eref("question.closure")
        tournament_ref = eref("tournament.implementations.closure")
        predecessor_ref = eref("model.selected.closure", 1)
        promoted_ref = eref("model.selected.closure", 2)
        mapping_ref = eref("formalization.promoted.closure")
        assumptions_ref = eref("assumptions.promoted.closure")
        argument_ref = eref(
            "argument.closure",
            2 if supersede_tournament_argument else 1,
        )

        predecessor = fixture.payload(predecessor_ref.entity_id)
        assert isinstance(predecessor, FormalModel)
        promoted_entity = _entity(
            promoted_ref.entity_id,
            predecessor,
            version=promoted_ref.version,
            supersedes=predecessor_ref,
        )

        prior_mapping = fixture.payload("formalization.closure")
        assert isinstance(prior_mapping, FormalizationMap)
        promoted_mapping = prior_mapping.model_copy(
            update={
                "economic_argument_graph_ref": argument_ref,
                "formal_model_ref": promoted_ref,
            }
        )
        mapping_entity = _entity(mapping_ref.entity_id, promoted_mapping)

        unrelated_v1 = eref("model.unrelated.closure", 1)
        unrelated_v2 = eref("model.unrelated.closure", 2)
        necessity_evidence_ref = (
            unrelated_v1
            if use_unrelated_necessity_evidence
            else predecessor_ref
        )
        prior_assumptions = fixture.payload("assumptions.closure")
        assert isinstance(prior_assumptions, AssumptionMap)
        promoted_records = tuple(
            item.model_copy(
                update={"necessity_evidence_refs": (necessity_evidence_ref,)}
            )
            if item.necessity_status == "result_necessary"
            else item
            for item in prior_assumptions.assumptions
        )
        promoted_assumptions = prior_assumptions.model_copy(
            update={
                "formal_model_ref": promoted_ref,
                "formalization_map_ref": mapping_ref,
                "assumptions": promoted_records,
            }
        )
        assumptions_entity = _entity(
            assumptions_ref.entity_id, promoted_assumptions
        )
        if cycle_tournament_argument_to_assumptions:
            argument = fixture.payload("argument.closure")
            assert isinstance(argument, EconomicArgumentGraph)
            first_edge, *other_edges = argument.edges
            fixture.replace_payload(
                "argument.closure",
                argument.model_copy(
                    update={
                        "edges": (
                            first_edge.model_copy(
                                update={
                                    "formal_witness_refs": (
                                        assumptions_ref,
                                    )
                                }
                            ),
                            *other_edges,
                        )
                    }
                ),
            )

        extra_refs: tuple[EntityVersionRef, ...] = ()
        extra_entities: list[EntityVersion] = []
        if supersede_tournament_argument:
            prior_argument = fixture.payload("argument.closure")
            assert isinstance(prior_argument, EconomicArgumentGraph)
            extra_entities.append(
                _entity(
                    argument_ref.entity_id,
                    prior_argument,
                    version=argument_ref.version,
                    supersedes=eref(argument_ref.entity_id),
                )
            )
        if include_unrelated_stale_ref or use_unrelated_necessity_evidence:
            if include_unrelated_stale_ref:
                extra_refs = (unrelated_v1,)
            extra_entities.extend(
                (
                    _entity(unrelated_v1.entity_id, predecessor),
                    _entity(
                        unrelated_v2.entity_id,
                        predecessor,
                        version=2,
                        supersedes=unrelated_v1,
                    ),
                )
            )
        if supersede_promoted_model:
            extra_entities.append(
                _entity(
                    promoted_ref.entity_id,
                    predecessor,
                    version=3,
                    supersedes=promoted_ref,
                )
            )
        if supersede_mapping:
            extra_entities.append(
                _entity(
                    mapping_ref.entity_id,
                    promoted_mapping,
                    version=2,
                    supersedes=mapping_ref,
                )
            )

        dossier_payload = GateDossier(
            gate_kind="G3_formal_base",
            research_question_ref=question_ref,
            ordered_object_refs=(
                question_ref,
                tournament_ref,
                predecessor_ref,
                promoted_ref,
                mapping_ref,
                assumptions_ref,
                *extra_refs,
            ),
            requirements=(
                GateRequirement(
                    requirement_id="requirement.g3.promoted.lineage",
                    description=(
                        "The current formal base is bound to its exact "
                        "tournament-selected audit predecessor."
                    ),
                    evidence_refs=(
                        tournament_ref,
                        predecessor_ref,
                        promoted_ref,
                        mapping_ref,
                        assumptions_ref,
                    ),
                    recorded_condition="evidence_supplied",
                ),
            ),
            proposed_action="approve",
            rationale=(
                "The promoted model is current; its tournament predecessor is "
                "retained only as exact audit and necessity evidence."
            ),
            prepared_at="2026-07-11T17:00:00Z",
        )
        dossier_entity = _entity(
            "dossier.g3.promoted.history.closure", dossier_payload
        )

        entities = (
            *fixture.entities.values(),
            promoted_entity,
            mapping_entity,
            assumptions_entity,
            dossier_entity,
            *extra_entities,
        )
        current_entities: dict[str, int] = {}
        for entity in entities:
            current_entities[entity.entity_id] = max(
                current_entities.get(entity.entity_id, 0), entity.version
            )
        prior_decisions = tuple(
            decision
            for decision in fixture.decisions.values()
            if decision.decision_kind
            in {"G1_question_benchmark", "G2_mechanism"}
        )
        head = _digest("g3 historical predecessor snapshot")
        snapshot = Snapshot(
            project_id=PROJECT_ID,
            head=head,
            chain=(head,),
            entity_versions=tuple(entities),
            decisions=prior_decisions,
            artifacts=tuple(fixture.artifacts.values()),
            current_entities=current_entities,
            current_decisions={
                decision.decision_id: decision.version
                for decision in prior_decisions
            },
            current_artifacts={
                artifact.artifact_id: artifact.version
                for artifact in fixture.artifacts.values()
            },
            effective_decisions={
                decision.decision_id: EffectiveDecisionRef(
                    decision_id=decision.decision_id,
                    version=decision.version,
                    effective_revision=_digest(
                        f"effective {decision.decision_id}"
                    ),
                )
                for decision in prior_decisions
            },
        )
        approval = Decision(
            decision_id="decision.g3.promoted.history.closure",
            version=1,
            project_id=PROJECT_ID,
            decision_kind="G3_formal_base",
            subject_ref=dossier_entity.entity_id,
            scope_ref=question_ref.entity_id,
            question="Approve the exact promoted formal base?",
            options=("approve", "deny"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve the exact current promoted base.",
            rationale="The mapping and assumptions bind the promoted model.",
            evidence_refs=(dossier_entity.entity_id,),
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-11T17:01:00Z",
            status="confirmed",
        )
        transaction = Transaction(
            transaction_id="transaction.g3.promoted.history.closure",
            origin="human_decision",
            project_id=PROJECT_ID,
            base_revision=head,
            route_run_id="human.g3.promoted.history.closure",
            actor=HUMAN,
            intent="Approve the exact promoted formal base.",
            operations=(RecordDecisionOp(decision=approval),),
            created_at="2026-07-11T17:01:00Z",
            parent_transaction_hash=head,
        )
        return snapshot, dossier_entity, dossier_payload, transaction

    def test_exact_tournament_predecessor_remains_g3_audit_evidence(
        self,
    ) -> None:
        snapshot, dossier_entity, dossier, approval = (
            self._snapshot_and_approval()
        )

        self.assertTrue(
            _gate_dossier_is_fresh(snapshot, dossier_entity, dossier)
        )
        self.assertTrue(
            _typed_reference_closure_is_current_and_fresh(
                snapshot, eref("assumptions.promoted.closure")
            )
        )
        validate_phase2_human_gate_transaction(snapshot, approval)

    def test_unrelated_stale_model_cannot_hide_in_g3_dossier(self) -> None:
        snapshot, dossier_entity, dossier, approval = (
            self._snapshot_and_approval(include_unrelated_stale_ref=True)
        )

        self.assertFalse(
            _gate_dossier_is_fresh(snapshot, dossier_entity, dossier)
        )
        with self.assertRaisesRegex(TheoryValidationError, "stale dossier"):
            validate_phase2_human_gate_transaction(snapshot, approval)

    def test_unrelated_stale_necessity_evidence_remains_invalid(self) -> None:
        snapshot, dossier_entity, dossier, approval = (
            self._snapshot_and_approval(
                use_unrelated_necessity_evidence=True
            )
        )

        self.assertFalse(
            _typed_reference_closure_is_current_and_fresh(
                snapshot, eref("assumptions.promoted.closure")
            )
        )
        self.assertFalse(
            _gate_dossier_is_fresh(snapshot, dossier_entity, dossier)
        )
        with self.assertRaisesRegex(TheoryValidationError, "stale dossier"):
            validate_phase2_human_gate_transaction(snapshot, approval)

    def test_stale_tournament_argument_cannot_qualify_history(self) -> None:
        snapshot, dossier_entity, dossier, approval = (
            self._snapshot_and_approval(
                supersede_tournament_argument=True
            )
        )

        self.assertFalse(
            _typed_reference_closure_is_current_and_fresh(
                snapshot, eref("assumptions.promoted.closure")
            )
        )
        self.assertFalse(
            _gate_dossier_is_fresh(snapshot, dossier_entity, dossier)
        )
        with self.assertRaisesRegex(TheoryValidationError, "stale dossier"):
            validate_phase2_human_gate_transaction(snapshot, approval)

    def test_tournament_argument_cycle_reuses_freshness_walk_state(
        self,
    ) -> None:
        snapshot, dossier_entity, dossier, approval = (
            self._snapshot_and_approval(
                cycle_tournament_argument_to_assumptions=True
            )
        )

        self.assertTrue(
            _typed_reference_closure_is_current_and_fresh(
                snapshot, eref("assumptions.promoted.closure")
            )
        )
        self.assertTrue(
            _gate_dossier_is_fresh(snapshot, dossier_entity, dossier)
        )
        validate_phase2_human_gate_transaction(snapshot, approval)

    def test_later_promoted_model_or_mapping_revision_revokes_g3_dossier(
        self,
    ) -> None:
        for label, options in (
            ("model", {"supersede_promoted_model": True}),
            ("mapping", {"supersede_mapping": True}),
        ):
            with self.subTest(revised=label):
                snapshot, dossier_entity, dossier, approval = (
                    self._snapshot_and_approval(**options)
                )
                self.assertFalse(
                    _gate_dossier_is_fresh(
                        snapshot, dossier_entity, dossier
                    )
                )
                with self.assertRaisesRegex(
                    TheoryValidationError, "stale dossier"
                ):
                    validate_phase2_human_gate_transaction(
                        snapshot, approval
                    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
