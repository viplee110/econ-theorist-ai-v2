"""Prepare a fresh registry-V8 paired shadow for semantic authoring V2.

This evaluator-side script freezes a new accident-liability case, proves one
private oracle through both the complete Transaction and semantic-V2 surfaces,
and emits two protocol-separated generator directories.  It never invokes a model,
completes the open audit run, writes the canonical candidate, or confirms a
human gate.

The earlier failure-refund preparer remains frozen as historical evidence.
This script reuses only its case-neutral filesystem and manifest helpers.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from scripts import prepare_framing_authoring_pair as legacy  # noqa: E402

from econ_theorist.candidate_contract import (  # noqa: E402
    compile_candidate_authoring_contract,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest  # noqa: E402
from econ_theorist.framing_quality import (  # noqa: E402
    ActiveMarginWitness,
    AggregateInvarianceAssessment,
    ArchetypeTension,
    BenchmarkFramingAssessment,
    CausalChainStep,
    ChoiceConsequenceBinding,
    DistinctiveMechanismAssessment,
    EconomicForce,
    EconomistMemo,
    FramingQualityBundle,
    IllustrativeMinimalExample,
    PublicStateCondition,
    SelectionAssurance,
)
from econ_theorist.framing_quality_authoring import (  # noqa: E402
    BenchmarkChannelIntentV1,
    FramingAuditSemanticDraftV2,
    MarginWitnessIntentV2,
    PublicStateConditionIntentV2,
    compile_framing_audit_semantic_authoring_contract_v2,
    compile_framing_audit_semantic_draft_v2,
)
from econ_theorist.machine.models import WorkPacketV1  # noqa: E402
from econ_theorist.machine.navigation import enumerate_navigation_candidates  # noqa: E402
from econ_theorist.machine.operational import ProjectOperationalLayout  # noqa: E402
from econ_theorist.machine.packets import read_work_packet  # noqa: E402
from econ_theorist.machine.run_service import open_or_resume_run  # noqa: E402
from econ_theorist.models import (  # noqa: E402
    Actor,
    EntityVersion,
    RelationVersion,
    Snapshot,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V8_HASH  # noqa: E402
from econ_theorist.project import init_project  # noqa: E402
from econ_theorist.runtime import StoreLayout  # noqa: E402
from econ_theorist.runtime.replay import replay, validate_candidate  # noqa: E402
from econ_theorist.theory import (  # noqa: E402
    BenchmarkRecord,
    BenchmarkSet,
    GateDossier,
    GateRequirement,
    PrimitiveEdge,
    PrimitiveGraph,
    PrimitiveNode,
    ResearchQuestion,
)


REVIEW_ROOT = REPOSITORY_ROOT / "review_outputs" / "phase5a2_v8_authoring_pair_v2"
HARNESS_SOURCE = REPOSITORY_ROOT / "scripts" / "run_framing_authoring_shadow.py"
PUBLISHER_SOURCE = REPOSITORY_ROOT / "scripts" / "publish_json_only_artifact.py"

PAIR_ID = "pair.accident.liability.authoring.v8.v2"
ARM_IDS = {
    "transaction": "arm.transaction.accident.liability",
    "semantic_v2": "arm.semantic.v2.accident.liability",
}
AGENT = Actor(kind="agent", actor_id="paired.shadow.v2.agent")
HUMAN_ID = "human.owner"
T0 = "2026-07-19T09:00:00Z"
T1 = "2026-07-19T09:01:00Z"
T2 = "2026-07-19T09:02:00Z"
T3 = "2026-07-19T09:03:00Z"


def _eref(entity: EntityVersion):
    return legacy._eref(entity)


def _theory_entity(
    snapshot: Snapshot,
    *,
    entity_id: str,
    payload: Any,
    title: str,
    summary: str,
    created_at: str,
) -> EntityVersion:
    return legacy._theory_entity(
        snapshot,
        entity_id=entity_id,
        payload=payload,
        title=title,
        summary=summary,
        created_at=created_at,
    )


def _commit_route(
    layout: StoreLayout,
    *,
    route_id: str,
    purpose: str,
    focus: tuple[str, ...],
    outputs: tuple[EntityVersion, ...],
    relations: tuple[RelationVersion, ...],
    evidence_refs: tuple[Any, ...],
    route_run_id: str,
    context_id: str,
    transaction_id: str,
    created_at: str,
) -> Snapshot:
    original_agent = legacy.AGENT
    try:
        legacy.AGENT = AGENT
        return legacy._commit_route(
            layout,
            route_id=route_id,
            purpose=purpose,
            focus=focus,
            outputs=outputs,
            relations=relations,
            evidence_refs=evidence_refs,
            route_run_id=route_run_id,
            context_id=context_id,
            transaction_id=transaction_id,
            created_at=created_at,
        )
    finally:
        legacy.AGENT = original_agent


def _build_prefix(
    layout: StoreLayout,
) -> tuple[Snapshot, tuple[EntityVersion, EntityVersion, EntityVersion, EntityVersion]]:
    snapshot = replay(layout)
    question = _theory_entity(
        snapshot,
        entity_id="question.accident.liability",
        payload=ResearchQuestion(
            phenomenon=(
                "An accident-contingent private liability payment can change the "
                "modeled accident probability even though it does not alter the "
                "maintenance technology."
            ),
            object_to_explain=(
                "Whether liability changes accident probability through the "
                "operator's active maintenance choice."
            ),
            unresolved_delta=(
                "With routine maintenance fixed, liability changes private payoff "
                "but not accident risk; with reoptimization, the chosen maintenance "
                "and accident probability both change."
            ),
            importance=(
                "The comparison separates a private payoff debit from the "
                "behavioral margin that can change a real outcome."
            ),
            kill_condition=(
                "The mechanism fails if the exact payoff ranking does not switch "
                "across liability rules or the selected actions imply the same risk."
            ),
            proposed_scope=(
                "One risk-neutral operator, two exhaustive maintenance actions, one "
                "period, and the stated private-payoff and accident technology only."
            ),
            candidate_archetypes=("mechanism_explanation",),
            prohibited_claims=(
                "Social welfare rises.",
                "Liability four is optimal legal policy.",
                "The example has empirical or external validity.",
                "The audit establishes literature novelty.",
            ),
        ),
        title="Accident-liability maintenance question",
        summary="When a private liability debit changes maintenance and accident risk.",
        created_at=T1,
    )
    benchmarks = _theory_entity(
        snapshot,
        entity_id="benchmarks.accident.liability",
        payload=BenchmarkSet(
            question_ref=_eref(question),
            benchmarks=(
                BenchmarkRecord(
                    benchmark_id="b_routine_fixed_accounting",
                    label="Routine action fixed accounting",
                    exact_primitives=(
                        "Routine maintenance is held fixed.",
                        "Routine return is three and its accident probability is one half.",
                        "Only accident-contingent liability changes from zero to four.",
                    ),
                    timing=(
                        "Liability rule set and observed",
                        "Maintenance action held fixed at routine",
                        "Accident draw and private payment",
                    ),
                    solution_concept="Exact expected-private-payoff accounting under a fixed action.",
                    prediction=(
                        "Routine payoff falls from three to one while accident "
                        "probability remains one half."
                    ),
                    unresolved_delta="The operator is not allowed to reoptimize maintenance.",
                    exact_values=(
                        legacy._rational("routine_payoff_no_liability", 3, 1),
                        legacy._rational("routine_payoff_high_liability", 1, 1),
                        legacy._rational("fixed_routine_accident_probability", 1, 2),
                    ),
                ),
                BenchmarkRecord(
                    benchmark_id="b_maintenance_reoptimization",
                    label="Maintenance reoptimization",
                    exact_primitives=(
                        "Routine yields three before liability and accident probability one half.",
                        "Preventive yields two before liability and accident probability zero.",
                        "The operator chooses exactly one action after observing liability.",
                        "Liability is zero or four and is paid only after an accident.",
                    ),
                    timing=(
                        "Liability rule observed",
                        "Operator chooses routine or preventive",
                        "Accident draw and private payment",
                    ),
                    solution_concept="Strict expected-private-payoff maximization over two exhaustive actions.",
                    prediction=(
                        "At liability zero the operator chooses routine and accident "
                        "probability is one half; at liability four the operator chooses "
                        "preventive and accident probability is zero."
                    ),
                    unresolved_delta=(
                        "The liability debit changes routine's expected payoff enough "
                        "to reverse the strict maintenance ranking."
                    ),
                    exact_values=(
                        legacy._rational("no_liability_selected_payoff", 3, 1),
                        legacy._rational("high_liability_selected_payoff", 2, 1),
                        legacy._rational("no_liability_accident_probability", 1, 2),
                        legacy._rational("high_liability_accident_probability", 0, 1),
                    ),
                ),
            ),
            exact_question_delta=(
                "Hold routine maintenance fixed in the accounting benchmark, then "
                "allow the maintenance choice to reoptimize under the same two rules."
            ),
        ),
        title="Accident-liability benchmarks",
        summary="Fixed routine accounting versus maintenance reoptimization.",
        created_at=T1,
    )
    frame_relations = (
        RelationVersion(
            relation_id="relation.liability.question.frames.benchmarks",
            relation_type="frames",
            version=1,
            project_id=snapshot.project_id,
            source=_eref(question),
            target=_eref(benchmarks),
            privacy="project_private",
            access_compartments=("project_research",),
            created_at=T1,
        ),
        RelationVersion(
            relation_id="relation.liability.question.benchmark.delta",
            relation_type="benchmark_delta",
            version=1,
            project_id=snapshot.project_id,
            source=_eref(question),
            target=_eref(benchmarks),
            privacy="project_private",
            access_compartments=("project_research",),
            created_at=T1,
        ),
    )
    snapshot = _commit_route(
        layout,
        route_id="frame.question_and_benchmarks",
        purpose="research_framing",
        focus=(),
        outputs=(question, benchmarks),
        relations=frame_relations,
        evidence_refs=(),
        route_run_id="run.pair.liability.frame",
        context_id="context.pair.liability.frame",
        transaction_id="transaction.pair.liability.frame",
        created_at=T1,
    )

    graph = _theory_entity(
        snapshot,
        entity_id="primitives.accident.liability",
        payload=PrimitiveGraph(
            question_ref=_eref(question),
            benchmark_set_ref=_eref(benchmarks),
            nodes=(
                PrimitiveNode(
                    node_id="operator_actor",
                    kind="actor",
                    label="Risk-neutral operator",
                    economic_meaning="The single operator maximizes expected private payoff.",
                    status="primitive",
                ),
                PrimitiveNode(
                    node_id="liability_rule",
                    kind="institution",
                    label="Accident liability rule",
                    economic_meaning="An accident triggers a private payment of zero or four.",
                    status="primitive",
                ),
                PrimitiveNode(
                    node_id="maintenance_action_set",
                    kind="constraint",
                    label="Binary maintenance action set",
                    economic_meaning="Exactly routine or preventive is feasible; there is no exit or mixing.",
                    status="primitive",
                ),
                PrimitiveNode(
                    node_id="maintenance_return_risk_schedule",
                    kind="constraint",
                    label="Maintenance return-risk schedule",
                    economic_meaning="Routine gives return three and risk one half; preventive gives return two and risk zero.",
                    status="primitive",
                ),
                PrimitiveNode(
                    node_id="maintenance_timing",
                    kind="timing",
                    label="Liability-before-maintenance timing",
                    economic_meaning="The rule is observed before one maintenance choice and the accident draw.",
                    status="primitive",
                ),
                PrimitiveNode(
                    node_id="maintenance_payoff_basis",
                    kind="preference_technology",
                    label="Expected private maintenance payoff basis",
                    economic_meaning="Risk neutrality, returns, accident risks, and liability determine both action payoffs.",
                    status="derived",
                ),
                PrimitiveNode(
                    node_id="maintenance_choice",
                    kind="choice",
                    label="Maintenance choice",
                    economic_meaning="The operator selects the strict expected-payoff maximizing action.",
                    status="derived",
                ),
                PrimitiveNode(
                    node_id="accident_probability",
                    kind="outcome",
                    label="Accident probability",
                    economic_meaning="Routine induces probability one half and preventive induces zero.",
                    status="derived",
                ),
            ),
            edges=(
                PrimitiveEdge(
                    edge_id="e_rule_payoff",
                    source_node_id="liability_rule",
                    target_node_id="maintenance_payoff_basis",
                    economic_meaning="Accident liability enters the expected payoff of the risky action.",
                ),
                PrimitiveEdge(
                    edge_id="e_schedule_payoff",
                    source_node_id="maintenance_return_risk_schedule",
                    target_node_id="maintenance_payoff_basis",
                    economic_meaning="The fixed return-risk schedule enters both action payoffs.",
                ),
                PrimitiveEdge(
                    edge_id="e_operator_payoff",
                    source_node_id="operator_actor",
                    target_node_id="maintenance_payoff_basis",
                    economic_meaning="The risk-neutral private objective defines the comparison.",
                ),
                PrimitiveEdge(
                    edge_id="e_payoff_choice",
                    source_node_id="maintenance_payoff_basis",
                    target_node_id="maintenance_choice",
                    economic_meaning="The strict expected-payoff ranking determines maintenance.",
                ),
                PrimitiveEdge(
                    edge_id="e_actionset_choice",
                    source_node_id="maintenance_action_set",
                    target_node_id="maintenance_choice",
                    economic_meaning="The binary feasible set exhausts the choice comparison.",
                ),
                PrimitiveEdge(
                    edge_id="e_timing_choice",
                    source_node_id="maintenance_timing",
                    target_node_id="maintenance_choice",
                    economic_meaning="The operator observes liability before choosing.",
                ),
                PrimitiveEdge(
                    edge_id="e_choice_accident",
                    source_node_id="maintenance_choice",
                    target_node_id="accident_probability",
                    economic_meaning="The selected maintenance mode determines accident risk.",
                ),
            ),
        ),
        title="Accident-liability primitive graph",
        summary="Liability, expected private payoff, maintenance choice, and risk.",
        created_at=T2,
    )
    dossier = _theory_entity(
        snapshot,
        entity_id="dossier.g1.accident.liability.source",
        payload=GateDossier(
            gate_kind="G1_question_benchmark",
            research_question_ref=_eref(question),
            ordered_object_refs=(_eref(question), _eref(benchmarks), _eref(graph)),
            requirements=(
                GateRequirement(
                    requirement_id="g1.liability.question",
                    description="The exact question, scope, and kill condition are explicit.",
                    evidence_refs=(_eref(question),),
                    recorded_condition="evidence_supplied",
                ),
                GateRequirement(
                    requirement_id="g1.liability.benchmarks",
                    description="Fixed-action mapping and maintenance reoptimization are separated and hand-solvable.",
                    evidence_refs=(_eref(benchmarks),),
                    recorded_condition="evidence_supplied",
                ),
                GateRequirement(
                    requirement_id="g1.liability.graph",
                    description="The primitive graph closes the unique payoff-choice-risk channel.",
                    evidence_refs=(_eref(graph),),
                    recorded_condition="evidence_supplied",
                ),
                GateRequirement(
                    requirement_id="g1.liability.scope",
                    description="Welfare, optimal law, empirical validity, and novelty remain outside scope.",
                    evidence_refs=(_eref(question),),
                    recorded_condition="risk_disclosed",
                ),
            ),
            proposed_action="approve",
            rationale="The exact question, benchmarks, graph, and boundaries are proposed for human review.",
            prepared_at=T2,
        ),
        title="Source G1 accident-liability dossier",
        summary="Proposal-only pre-audit question and benchmark package.",
        created_at=T2,
    )
    decompose_relations = (
        RelationVersion(
            relation_id="relation.liability.question.decomposes.graph",
            relation_type="decomposes",
            version=1,
            project_id=snapshot.project_id,
            source=_eref(question),
            target=_eref(graph),
            privacy="project_private",
            access_compartments=("project_research",),
            created_at=T2,
        ),
        RelationVersion(
            relation_id="relation.liability.dossier.governs.question",
            relation_type="governs",
            version=1,
            project_id=snapshot.project_id,
            source=_eref(dossier),
            target=_eref(question),
            privacy="project_private",
            access_compartments=("project_research",),
            created_at=T2,
        ),
    )
    snapshot = _commit_route(
        layout,
        route_id="decompose.primitives",
        purpose="research_discovery",
        focus=(question.entity_id, benchmarks.entity_id),
        outputs=(graph, dossier),
        relations=decompose_relations,
        evidence_refs=(_eref(question), _eref(benchmarks)),
        route_run_id="run.pair.liability.decompose",
        context_id="context.pair.liability.decompose",
        transaction_id="transaction.pair.liability.decompose",
        created_at=T2,
    )
    return snapshot, (question, benchmarks, graph, dossier)


def _oracle_bundle(
    core: tuple[EntityVersion, EntityVersion, EntityVersion, EntityVersion],
) -> FramingQualityBundle:
    question, benchmarks, graph, dossier = core
    high_liability_state = PublicStateCondition(
        node_id="liability_rule", relation="equals", value="high_liability_L4"
    )
    witness = ActiveMarginWitness(
        decision_node_id="maintenance_choice",
        payoff_node_ids=("maintenance_payoff_basis",),
        concrete_state="Liability equals four and all return, risk, action-set, timing, and objective primitives are fixed.",
        decision_maker="Risk-neutral operator",
        focal_action="Choose preventive maintenance",
        alternative_action="Choose routine maintenance",
        focal_payoff="2",
        alternative_payoff="3-(1/2)(4)=1",
        feasibility_basis="Routine and preventive are the two feasible and exhaustive actions.",
        best_response_inequality="2 > 1",
        activity_status="active",
        status_basis="Liability changes preventive minus routine payoff from -1 at L=0 to +1 at L=4.",
        kill_condition="The payoff ranking does not reverse or the two actions imply the same accident probability.",
        consequence_binding=ChoiceConsequenceBinding(
            consequence_node_id="accident_probability",
            transition_kind="decrease",
            causal_edge_ids=("e_choice_accident",),
            public_state_conditions=(high_liability_state,),
            focal_consequence="Preventive maintenance gives accident probability zero.",
            alternative_consequence="Routine maintenance gives accident probability one half.",
            feasibility_basis="The same binary action set maps each selected action to its fixed risk.",
        ),
    )
    fixed_primitives = (
        legacy._held(
            "fixed.operator.objective",
            "Risk-neutral private-payoff objective",
            "primitive",
            "operator_actor",
            "primitive",
        ),
        legacy._held(
            "fixed.action.set",
            "Routine or preventive action set",
            "primitive",
            "maintenance_action_set",
            "primitive",
        ),
        legacy._held(
            "fixed.return.risk.schedule",
            "Returns and action-contingent accident risks",
            "primitive",
            "maintenance_return_risk_schedule",
            "primitive",
        ),
        legacy._held(
            "fixed.timing",
            "Liability-before-maintenance timing",
            "primitive",
            "maintenance_timing",
            "primitive",
        ),
    )
    fixed_assessment = BenchmarkFramingAssessment(
        benchmark_id="b_routine_fixed_accounting",
        changed=(
            legacy._object(
                "liability.rule.fixed",
                "Accident liability rule",
                "primitive",
                "liability_rule",
            ),
        ),
        held_fixed=(
            *fixed_primitives,
            legacy._held(
                "fixed.maintenance.choice",
                "Maintenance fixed at routine",
                "choice",
                "maintenance_choice",
                "choice",
            ),
        ),
        reoptimizing=(),
        still_endogenous=(
            legacy._object(
                "maintenance.payoff.fixed",
                "Routine private-payoff ledger",
                "payoff_ledger",
                "maintenance_payoff_basis",
            ),
            legacy._object(
                "accident.risk.fixed",
                "Accident probability under fixed routine maintenance",
                "outcome",
                "accident_probability",
            ),
        ),
        targets=(
            legacy._object(
                "target.maintenance.payoff",
                "Routine private payoff",
                "payoff_ledger",
                "maintenance_payoff_basis",
            ),
        ),
        channel_kind="boundary_or_mapping",
        channel_path=("liability_rule", "maintenance_payoff_basis"),
        channel_summary="Liability lowers fixed-routine private payoff from three to one while accident probability remains one half.",
        aggregate_invariance=AggregateInvarianceAssessment(
            aggregate_object="Accident probability under fixed routine maintenance",
            pointwise_policy_fixed=True,
            weighting_distribution_status="not_applicable",
            claims_aggregate_fixed=True,
            basis="The maintenance action and its action-contingent accident risk are fixed.",
            implication_for_attribution="The private debit alone is not an active accident-risk response.",
        ),
        selection_assurance=SelectionAssurance(
            status="not_applicable",
            selection_rule="No equilibrium or optimizer selection is used in fixed-action accounting.",
            basis="The benchmark mechanically evaluates the declared routine action.",
            implication_for_attribution="The row supplies a payoff-mapping boundary only.",
        ),
        attribution_strength="clean",
        attribution_basis="The changed payoff ledger and frozen maintenance choice are explicit.",
        distinctive_mechanism=DistinctiveMechanismAssessment(
            claim_kind="not_claimed",
            mechanism_label="No active maintenance response is claimed in fixed-action accounting.",
            basis="The benchmark intentionally freezes maintenance at routine.",
        ),
    )
    active_assessment = BenchmarkFramingAssessment(
        benchmark_id="b_maintenance_reoptimization",
        changed=(
            legacy._object(
                "liability.rule.reoptimized",
                "Accident liability rule",
                "primitive",
                "liability_rule",
            ),
        ),
        held_fixed=fixed_primitives,
        reoptimizing=(
            legacy._object(
                "maintenance.choice.response",
                "Maintenance choice",
                "choice",
                "maintenance_choice",
            ),
        ),
        still_endogenous=(
            legacy._object(
                "maintenance.payoff.selected",
                "Selected private-payoff ledger",
                "payoff_ledger",
                "maintenance_payoff_basis",
            ),
            legacy._object(
                "accident.risk.reoptimized",
                "Induced accident probability",
                "outcome",
                "accident_probability",
            ),
        ),
        targets=(
            legacy._object(
                "target.accident.probability",
                "Accident probability",
                "outcome",
                "accident_probability",
            ),
        ),
        channel_kind="active_response",
        channel_path=(
            "liability_rule",
            "maintenance_payoff_basis",
            "maintenance_choice",
            "accident_probability",
        ),
        channel_summary="Liability reverses the strict payoff ranking, switches maintenance from routine to preventive, and lowers accident probability from one half to zero.",
        aggregate_invariance=AggregateInvarianceAssessment(
            aggregate_object="Accident probability",
            pointwise_policy_fixed=False,
            weighting_distribution_status="not_applicable",
            claims_aggregate_fixed=False,
            basis="The maintenance choice reoptimizes while action-contingent risks remain fixed.",
            implication_for_attribution="The accident change is caused by the active maintenance switch.",
        ),
        selection_assurance=SelectionAssurance(
            status="not_applicable",
            selection_rule="Strict single-agent maximization over two exhaustive actions.",
            basis="Both liability regimes have a unique strict payoff maximizer.",
            implication_for_attribution="No equilibrium selector or tie drives the maintenance change.",
        ),
        attribution_strength="clean",
        attribution_basis="Only liability changes; the fixed technology maps the strict choice switch to lower risk.",
        distinctive_mechanism=DistinctiveMechanismAssessment(
            claim_kind="choice_mediated",
            mechanism_label="Liability-induced preventive maintenance",
            contrast_benchmark_id="b_routine_fixed_accounting",
            distinctive_node_ids=("maintenance_choice",),
            distinctive_edge_ids=("e_choice_accident",),
            consequence_node_id="accident_probability",
            transition_kind="decrease",
            required_public_state_conditions=(high_liability_state,),
            basis="The active benchmark adds the exact maintenance choice and its risk consequence.",
        ),
    )
    return FramingQualityBundle(
        research_question_ref=_eref(question),
        benchmark_set_ref=_eref(benchmarks),
        primitive_graph_ref=_eref(graph),
        source_g1_dossier_ref=_eref(dossier),
        tension=ArchetypeTension(
            result_archetype="mechanism_explanation",
            tension_kind="causal_channel",
            conventional_prediction="An accident-contingent payment is only a private payoff debit.",
            economic_puzzle="The same debit changes real accident risk once maintenance can respond.",
            resolution_target="Separate fixed-action payoff accounting from the active maintenance margin.",
        ),
        forces=(
            EconomicForce(
                force_id="force.liability.maintenance",
                label="Liability-induced preventive maintenance",
                role="baseline_force",
                operative_margin="Maintenance choice",
                direction="lowers_target",
                economic_logic="Higher accident liability makes routine maintenance strictly less profitable than prevention.",
                active_when="The operator observes liability and can reoptimize maintenance.",
                source_node_id="liability_rule",
                margin_node_id="maintenance_choice",
                target_node_id="accident_probability",
            ),
        ),
        causal_chain=(
            CausalChainStep(
                step_number=1,
                force_ids=("force.liability.maintenance",),
                cause="Accident liability rises from zero to four.",
                endogenous_response="Routine expected payoff falls from three to one while preventive payoff stays two.",
                consequence="The payoff gap preventive minus routine changes from minus one to plus one.",
                source_node_id="liability_rule",
                target_node_id="maintenance_payoff_basis",
            ),
            CausalChainStep(
                step_number=2,
                force_ids=("force.liability.maintenance",),
                cause="Preventive maintenance becomes the unique strict payoff maximizer.",
                endogenous_response="The operator switches from routine to preventive maintenance.",
                consequence="The selected action moves to the zero-accident-risk technology.",
                source_node_id="maintenance_payoff_basis",
                target_node_id="maintenance_choice",
                active_margin_witness=witness,
            ),
            CausalChainStep(
                step_number=3,
                force_ids=("force.liability.maintenance",),
                cause="The operator selects preventive rather than routine maintenance.",
                endogenous_response="The fixed action-risk mapping applies to the newly selected action.",
                consequence="Accident probability falls from one half to zero.",
                source_node_id="maintenance_choice",
                target_node_id="accident_probability",
            ),
        ),
        minimal_example=IllustrativeMinimalExample(
            title="One operator choosing routine or preventive maintenance",
            setup="A risk-neutral operator observes accident liability before choosing one of two maintenance modes.",
            moving_primitive="Accident-contingent private liability payment",
            held_fixed=("Returns", "Action-contingent accident risks", "Action set", "Timing", "Risk neutrality"),
            endogenous_responses=("Maintenance choice",),
            predicted_pattern="Fixed routine accounting leaves risk at one half, while reoptimization switches maintenance and lowers risk to zero.",
            economic_intuition="A private debit changes a real outcome only through the choice whose payoff ranking it reverses.",
            limitation="The example does not model victims, welfare, legal implementation, heterogeneity, evidence, or novelty.",
            cannot_establish=("Social welfare", "Optimal liability", "Legal feasibility", "Empirical relevance", "Literature novelty"),
        ),
        economist_memo=EconomistMemo(
            headline="Liability changes accidents only when maintenance can move",
            opening_question="Can an accident-state payment change risk rather than only private accounting?",
            benchmark_message="With routine maintenance fixed, payoff falls from three to one but accident probability stays one half.",
            tension_message="Once maintenance can respond, that same debit reverses the strict action ranking.",
            mechanism_message="Liability four makes prevention pay two versus one for routine, switching the chosen technology.",
            result_preview="The maintenance switch lowers accident probability from one half to zero.",
            contribution_message="The comparison isolates a payoff mapping from its choice-mediated real consequence.",
            scope_condition="The result is limited to the stated one-period, two-action, risk-neutral private-payoff problem.",
            reader_takeaway="A liability debit changes risk only by changing the maintenance action selected under the fixed technology.",
        ),
        benchmark_assessments=(fixed_assessment, active_assessment),
        distinctive_mechanism_contribution_status="claimed",
        disclosed_gaps=(),
        proposed_action="ready_for_g1",
        action_rationale="The exact mapping boundary, active payoff witness, strict choice, risk consequence, and scope are explicit for proposed human G1 review.",
    )


def _semantic_draft(bundle: FramingQualityBundle) -> FramingAuditSemanticDraftV2:
    raw = bundle.model_dump(mode="json", exclude_none=False)
    for field_name in (
        "research_question_ref",
        "benchmark_set_ref",
        "primitive_graph_ref",
        "source_g1_dossier_ref",
    ):
        raw.pop(field_name)
    for force in raw["forces"]:
        force.pop("margin_node_id")
    intents: list[BenchmarkChannelIntentV1] = []
    for row in raw["benchmark_assessments"]:
        row.pop("channel_path")
        intents.append(
            BenchmarkChannelIntentV1(
                benchmark_id=row["benchmark_id"],
                changed_object_id=row["changed"][0]["object_id"],
                target_object_id=row["targets"][0]["object_id"],
            )
        )
    for step in raw["causal_chain"]:
        step.pop("active_margin_witness", None)
    margin_intent = MarginWitnessIntentV2(
        step_number=2,
        margin_position="target",
        consequence_step_number=3,
        concrete_state="Liability equals four and all return, risk, action-set, timing, and objective primitives are fixed.",
        decision_maker="Risk-neutral operator",
        focal_action="Choose preventive maintenance",
        alternative_action="Choose routine maintenance",
        focal_payoff="2",
        alternative_payoff="3-(1/2)(4)=1",
        feasibility_basis="Routine and preventive are the two feasible and exhaustive actions.",
        best_response_inequality="2 > 1",
        activity_status="active",
        status_basis="Liability changes preventive minus routine payoff from -1 at L=0 to +1 at L=4.",
        kill_condition="The payoff ranking does not reverse or the two actions imply the same accident probability.",
        transition_kind="decrease",
        focal_consequence="Preventive maintenance gives accident probability zero.",
        alternative_consequence="Routine maintenance gives accident probability one half.",
        consequence_feasibility_basis="The same binary action set maps each selected action to its fixed risk.",
        public_state_conditions=(
            PublicStateConditionIntentV2(
                benchmark_id="b_maintenance_reoptimization",
                object_id="liability.rule.reoptimized",
                relation="equals",
                value="high_liability_L4",
            ),
        ),
    )
    return FramingAuditSemanticDraftV2(
        bundle_payload=raw,
        channel_intents=tuple(intents),
        margin_intents=(margin_intent,),
        transaction_intent="Compile the held-out accident-liability economics framing audit.",
        outcome_rationale="The held-out semantic-V2 draft passed compiler preflight and unchanged V8 validation.",
        bundle_title="Accident-liability economics framing preflight",
        bundle_summary="Payoff mapping, maintenance response, and accident-risk consequence.",
        replacement_dossier_title="Replacement G1 accident-liability dossier",
        replacement_dossier_summary="The source G1 package strengthened by the held-out framing audit.",
    )


def _open_audit(
    layout: StoreLayout, snapshot: Snapshot
) -> tuple[WorkPacketV1, Any, Snapshot]:
    candidates, diagnostics = enumerate_navigation_candidates(
        layout,
        snapshot,
        actor=AGENT,
        compartments=("project_research",),
        privacy_clearance="project_private",
        budget_units=32_000,
        requested_route_ids=("audit.framing_economics",),
    )
    if len(candidates) != 1:
        raise RuntimeError(
            "held-out prefix did not expose one audit route: "
            + ", ".join(item.code for item in diagnostics)
        )
    operational = ProjectOperationalLayout.at(layout)
    opened = open_or_resume_run(
        layout,
        operation_key="pair-liability-audit-open-v2",
        reserved_at=T3,
        candidate=candidates[0],
        run_input_brief=None,
        operational=operational,
    )
    packet = read_work_packet(
        operational, opened.route_run_id, opened.work_packet_hash
    )
    contract = compile_candidate_authoring_contract(
        layout, packet, opened.work_packet_hash
    )
    return packet, contract, replay(layout)


def _runner_script(
    *,
    output_root: Path,
    arm_root: Path,
    surface: str,
    python_runtime: Path,
    runtime_manifest_sha256: str,
) -> bytes:
    case_path = output_root / "private_evaluator" / "HARNESS_CASE.json"
    runtime_root = output_root / "runtime"
    runtime_site = runtime_root / "site"
    runtime_manifest_path = runtime_root / "RUNTIME_MANIFEST.json"
    harness = runtime_root / HARNESS_SOURCE.name
    publisher = runtime_root / PUBLISHER_SOURCE.name
    return (
        "param(\r\n"
        "  [Parameter(Mandatory=$true)][ValidateSet(1,2,3)][int]$Attempt\r\n"
        ")\r\n"
        "$ErrorActionPreference = 'Stop'\r\n"
        f"$runtimeManifestPath = '{runtime_manifest_path}'\r\n"
        "$runtimeManifestHash = (Get-FileHash -LiteralPath $runtimeManifestPath -Algorithm SHA256).Hash.ToLowerInvariant()\r\n"
        f"if ($runtimeManifestHash -ne '{runtime_manifest_sha256}') {{ throw 'INVALID_SETUP: runtime manifest digest mismatch' }}\r\n"
        "$runtimeManifest = Get-Content -LiteralPath $runtimeManifestPath -Raw | ConvertFrom-Json\r\n"
        "$runtimeRoot = Split-Path -Parent $runtimeManifestPath\r\n"
        "foreach ($item in $runtimeManifest.files) {\r\n"
        "  $path = Join-Path $runtimeRoot $item.path\r\n"
        "  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw \"INVALID_SETUP: missing runtime file $($item.path)\" }\r\n"
        "  $size = (Get-Item -LiteralPath $path).Length\r\n"
        "  $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()\r\n"
        "  if ($size -ne $item.bytes -or $hash -ne $item.sha256) { throw \"INVALID_SETUP: runtime file mismatch $($item.path)\" }\r\n"
        "}\r\n"
        "$runtimeExpected = @($runtimeManifest.files | ForEach-Object { $_.path })\r\n"
        "$runtimeUnexpected = @(Get-ChildItem -LiteralPath $runtimeRoot -Recurse -File | ForEach-Object { $_.FullName.Substring($runtimeRoot.Length + 1).Replace('\\','/') } | Where-Object { $_ -ne 'RUNTIME_MANIFEST.json' -and $_ -notin $runtimeExpected })\r\n"
        "if ($runtimeUnexpected.Count -gt 0) { throw \"INVALID_SETUP: unlisted runtime file(s): $($runtimeUnexpected -join ',')\" }\r\n"
        f"$env:PYTHONPATH = '{runtime_site}'\r\n"
        "$env:PYTHONDONTWRITEBYTECODE = '1'\r\n"
        "$number = $Attempt.ToString('00')\r\n"
        f"$workRoot = Join-Path '{arm_root}' 'work'\r\n"
        "$workInfo = Get-Item -LiteralPath $workRoot\r\n"
        "if (($workInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'INVALID_SETUP: work directory cannot be a reparse point' }\r\n"
        f"$receipt = Join-Path '{arm_root}' \"work/attempt_$number.receipt.json\"\r\n"
        f"$projection = Join-Path '{arm_root}' \"work/attempt_$number.scientific_projection.json\"\r\n"
        "if (Test-Path -LiteralPath $receipt) { throw \"INVALID_SETUP: attempt already has an immutable receipt: $receipt\" }\r\n"
        "$priorReceipt = $null\r\n"
        "if ($Attempt -gt 1) {\r\n"
        "  $previous = ($Attempt - 1).ToString('00')\r\n"
        f"  $priorReceipt = Join-Path '{arm_root}' \"work/attempt_$previous.receipt.json\"\r\n"
        "  if (-not (Test-Path -LiteralPath $priorReceipt -PathType Leaf)) { throw \"INVALID_SETUP: missing prior receipt: $priorReceipt\" }\r\n"
        "}\r\n"
        "$source = Join-Path $workRoot \"attempt_$number.json\"\r\n"
        "$arguments = @(\r\n"
        f"  '{harness}', '--case', '{case_path}', '--surface', '{surface}',\r\n"
        f"  '--arm-id', '{ARM_IDS[surface]}', '--attempt', $Attempt, '--source', $source,\r\n"
        "  '--receipt', $receipt, '--projection', $projection\r\n"
        ")\r\n"
        "if ($Attempt -gt 1) {\r\n"
        "  $arguments += @('--prior-receipt', $priorReceipt)\r\n"
        "}\r\n"
        "$checkArguments = @($arguments + '--check-setup-only')\r\n"
        f"$null = & '{python_runtime}' @checkArguments\r\n"
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\r\n"
        "$scratch = Join-Path $workRoot \"attempt_$number.scratch.json\"\r\n"
        "if (-not (Test-Path -LiteralPath $scratch -PathType Leaf)) { throw \"missing exact attempt scratch source: $scratch\" }\r\n"
        "$scratchInfo = Get-Item -LiteralPath $scratch\r\n"
        "if (($scratchInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'INVALID_SETUP: attempt scratch source cannot be a reparse point' }\r\n"
        f"$null = & '{python_runtime}' '{publisher}' --source $scratch --target $source\r\n"
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }\r\n"
        "if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw \"publisher did not create exact attempt source: $source\" }\r\n"
        "$sourceInfo = Get-Item -LiteralPath $source\r\n"
        "if (($sourceInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'INVALID_SETUP: attempt source cannot be a reparse point' }\r\n"
        f"& '{python_runtime}' @arguments\r\n"
        "exit $LASTEXITCODE\r\n"
    ).encode("utf-8")


def _task_prompt(surface: str) -> bytes:
    common = """# TASK PROMPT

Use the ordinary/medium model selected for this paired test. Work only in this
directory. Continue only if the launch message's exact-digest call to
`VERIFY_MANIFEST.ps1` returned `MANIFEST_OK`; otherwise stop and report
`INVALID_SETUP`.

Do not use an old conversation, network access, subagents, repository source,
tests or fixtures, earlier pilots, the parent directory, sibling arm,
evaluator key, or any file not listed by this arm's manifest. The frozen
harness may be executed only through `./RUN_ATTEMPT.ps1`; do not inspect it.
This is a noncanonical shadow: do not invoke the bridge, stage or commit a
candidate, finish a run, or confirm a human gate. Do not request human editing.

Read `CASE.md`, `COMMON_WORK_PACKET.json`,
`FRAMING_PAYLOAD_CONTRACT.json`, and this arm's `SURFACE.json`. Draft only the
surface-specific JSON in the mutable transport buffer
`work/attempt_01.scratch.json`, then run:

```powershell
./RUN_ATTEMPT.ps1 -Attempt 1
```

The runner publishes `work/attempt_01.json` only if the scratch bytes are
valid UTF-8 and encode one complete top-level JSON object. It may remove one
UTF-8 BOM but never trims, extracts, reserializes, balances braces, or repairs
the source. If publication fails, correct the same scratch buffer and rerun
the same attempt; no formal attempt artifact or receipt exists yet. Record
every rejected scratch publication, its SHA-256, byte count, and rejection
reason in the final report as an artifact-hygiene correction, not an engine
route repair.

The receipt is the completion marker for an attempt. If terminal output is
lost after that receipt exists, do not rerun the attempt; read and report the
immutable receipt. If a projection was published but no receipt exists, rerun
the same scratch bytes so the harness can complete the interrupted publication.

If the immutable receipt rejects it, use only its complete diagnostics to
draft `work/attempt_02.scratch.json` and then at most
`work/attempt_03.scratch.json`. Every successfully published formal artifact
after a receipt rejection counts as one experimental repair. Stop at the first
`validator_pass: true` or after attempt 3. Never overwrite a published
`attempt_XX.json` artifact or receipt.

Write `report/agent_report.md` with the manifest result, requested/visible
model label, whether the actual backend/provider was independently observable,
every source and receipt digest, elapsed times, final status, and confirmation
that canonical writes and human gates were zero. Do not guess an unobservable
provider identity.

"""
    if surface == "transaction":
        specific = """## This arm: complete Transaction

Write one complete Transaction JSON matching `SURFACE.json` into the scratch
path named in the common instructions, including
all wrappers, bindings, output objects, relations, hashes, and route outcome.
Use explicit JSON null only where the frozen draft-hash contract permits the
harness to materialize it. Do not call, imitate, or reconstruct the semantic
compiler.
"""
    elif surface == "semantic_v2":
        specific = """## This arm: semantic V2 draft

Write one `FramingAuditSemanticDraftV2` matching `SURFACE.json` into the scratch
path named in the common instructions.
`bundle_payload` contains all scientific FramingQualityBundle content but must
omit the four exact input refs, every assessment's `channel_path`, and every
`active_margin_witness` key, including null placeholders. It must also omit
every force's `margin_node_id` while retaining the scientifically intended
source and target endpoints. Provide exactly one `channel_intent` per benchmark, omitting waypoints when its
endpoints select one unique graph path, and provide the required scientific
`margin_intent`. If a force is not uniquely named by one margin intent, provide
one entry in `force_margin_locators`; do not ask the compiler to infer it.
The model still authors actions, payoffs, feasibility, inequality, activity,
consequences, and kill condition. Do not author Transaction wrappers, exact
graph bindings owned by the V2 compiler, EntityVersion wrappers, a replacement
GateDossier, relations, canonical IDs or hashes, or a route outcome. Put
intentional scope limits in `economist_memo.scope_condition`; use
`disclosed_gaps` only for a genuine unresolved defect.
"""
    else:
        raise ValueError(f"unknown paired surface: {surface}")
    return (common + specific).encode("utf-8")


def _launch_prompt(
    *, arm_root: Path, surface: str, arm_manifest_sha256: str
) -> bytes:
    return legacy._launch_prompt(
        arm_root=arm_root,
        surface=surface,
        arm_manifest_sha256=arm_manifest_sha256,
    )


def _verify_frozen_runtime_v2(
    *,
    python_runtime: Path,
    runtime_site: Path,
    harness: Path,
    expected_engine_version: str,
    expected_engine_semantics_hash: str,
) -> dict[str, str]:
    facts = legacy._verify_frozen_runtime(
        python_runtime=python_runtime,
        runtime_site=runtime_site,
        harness=harness,
        expected_engine_version=expected_engine_version,
        expected_engine_semantics_hash=expected_engine_semantics_hash,
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(runtime_site)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = subprocess.run(
        (
            str(python_runtime),
            "-c",
            (
                "from econ_theorist.framing_quality_authoring import "
                "FramingAuditSemanticDraftV2, "
                "compile_framing_audit_semantic_authoring_contract_v2, "
                "compile_framing_audit_semantic_draft_v2, "
                "preflight_framing_audit_semantic_draft_v2; "
                "print(FramingAuditSemanticDraftV2.model_fields['semantic_draft_schema'].default)"
            ),
        ),
        cwd=runtime_site.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    expected = "econ-theorist/framing-audit-semantic-draft/v2"
    if probe.returncode != 0 or probe.stdout.strip() != expected:
        raise RuntimeError(
            "the frozen wheel lacks the exact semantic-V2 authoring surface: "
            + (probe.stderr or probe.stdout).strip()[:1000]
        )
    return {**facts, "semantic_authoring_surface": expected}


def _runtime_self_test(
    *,
    python_runtime: Path,
    runtime_site: Path,
    harness: Path,
    harness_case: Path,
    oracle_draft: FramingAuditSemanticDraftV2,
    oracle_transaction: Transaction,
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(runtime_site)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    results: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="etai-pair-v2-runtime-self-test-") as raw:
        root = Path(raw)
        sources = {
            "transaction": canonical_json_bytes(oracle_transaction),
            "semantic_v2": canonical_json_bytes(oracle_draft),
        }
        for surface, source_data in sources.items():
            source = root / f"{surface}.json"
            receipt = root / f"{surface}.receipt.json"
            projection = root / f"{surface}.projection.json"
            source.write_bytes(source_data)
            completed = subprocess.run(
                (
                    str(python_runtime),
                    str(harness),
                    "--case",
                    str(harness_case),
                    "--surface",
                    surface,
                    "--arm-id",
                    ARM_IDS[surface],
                    "--attempt",
                    "1",
                    "--source",
                    str(source),
                    "--receipt",
                    str(receipt),
                    "--projection",
                    str(projection),
                ),
                cwd=runtime_site.parent,
                env=environment,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if completed.returncode != 0 or not receipt.is_file():
                raise RuntimeError(
                    f"frozen {surface} harness self-test failed: "
                    + (completed.stderr or completed.stdout).strip()[:1000]
                )
            receipt_data = receipt.read_bytes()
            receipt_value = json.loads(receipt_data)
            if (
                canonical_json_bytes(receipt_value) != receipt_data
                or receipt_value.get("validator_pass") is not True
                or receipt_value.get("canonical_writes") != 0
                or receipt_value.get("head_before") != receipt_value.get("head_after")
                or receipt_value.get("experimental_repairs_submitted") != 0
                or receipt_value.get("experimental_repair_required") is not False
                or receipt_value.get("engine_route_repair_equivalent") != 0
                or receipt_value.get("engine_route_repair_eligible_for_burden_comparison") is not False
                or not isinstance(receipt_value.get("source_canonical_json_bytes"), int)
                or not projection.is_file()
            ):
                raise RuntimeError(
                    f"frozen {surface} harness self-test receipt is invalid"
                )
            results[surface] = {
                "source_sha256": sha256_digest(source_data),
                "receipt_sha256": sha256_digest(receipt_data),
                "projection_sha256": sha256_digest(projection.read_bytes()),
                "validator_pass": True,
                "canonical_writes": 0,
            }
        projection_hashes = {
            item["projection_sha256"] for item in results.values()
        }
        if len(projection_hashes) != 1:
            raise RuntimeError(
                "the two oracle surfaces do not produce one scientific projection"
            )

        invalid_source = root / "transaction-base-mismatch.json"
        invalid_receipt = root / "transaction-base-mismatch.receipt.json"
        invalid_transaction = oracle_transaction.model_copy(
            update={"base_revision": "0" * 64}
        )
        invalid_source.write_bytes(canonical_json_bytes(invalid_transaction))
        rejected = subprocess.run(
            (
                str(python_runtime),
                str(harness),
                "--case",
                str(harness_case),
                "--surface",
                "transaction",
                "--arm-id",
                ARM_IDS["transaction"],
                "--attempt",
                "1",
                "--source",
                str(invalid_source),
                "--receipt",
                str(invalid_receipt),
            ),
            cwd=runtime_site.parent,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if rejected.returncode != 1 or not invalid_receipt.is_file():
            raise RuntimeError(
                "base-mismatch harness self-test did not return one arm rejection: "
                + (rejected.stderr or rejected.stdout).strip()[:1000]
            )
        invalid_value = json.loads(invalid_receipt.read_bytes())
        if (
            invalid_value.get("validator_pass") is not False
            or invalid_value.get("issue_taxonomy", {}).get("wrapper_or_binding") != 1
            or invalid_value.get("experimental_repair_required") is not True
            or invalid_value.get("canonical_writes") != 0
        ):
            raise RuntimeError(
                "base-mismatch harness self-test receipt has the wrong classification"
            )
        results["base_mismatch_rejection"] = {
            "receipt_sha256": sha256_digest(invalid_receipt.read_bytes()),
            "validator_pass": False,
            "taxonomy": "wrapper_or_binding",
            "canonical_writes": 0,
        }
    return results


def _prepare(args: argparse.Namespace) -> None:
    legacy._verify_repository_binding(
        args.engine_commit, allow_dirty_probe=args.allow_dirty_probe
    )
    output_root = args.output_root.resolve()
    if output_root.exists():
        raise RuntimeError("output root already exists; choose a fresh directory")
    if not args.wheel.is_file():
        raise RuntimeError("the exact engine wheel is missing")
    if not args.python_runtime.is_file():
        raise RuntimeError("the frozen Python runtime path is missing")

    wheel_bytes = args.wheel.read_bytes()
    wheel_name = args.wheel.name
    wheel_sha256 = sha256_digest(wheel_bytes)
    output_root.mkdir(parents=True)
    private = output_root / "private_evaluator"
    seed_workspace = tempfile.TemporaryDirectory(prefix="etai-pair-v2-seed-")
    seed_root = Path(seed_workspace.name) / "project"
    runtime = output_root / "runtime"
    transaction_root = output_root / "arm-transaction"
    semantic_root = output_root / "arm-semantic"
    for directory in (
        private,
        seed_root,
        runtime,
        transaction_root / "work",
        transaction_root / "report",
        semantic_root / "work",
        semantic_root / "report",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    init_project(
        seed_root,
        name="Accident liability and preventive maintenance",
        actor_id=HUMAN_ID,
        project_id="project.accident.liability.pair.v2",
        created_at=T0,
        transaction_id="transaction.pair.liability.genesis",
        route_run_id="run.pair.liability.genesis",
    )
    layout = StoreLayout.at(seed_root)
    prefix_snapshot, core = _build_prefix(layout)
    packet, contract, audit_snapshot = _open_audit(layout, prefix_snapshot)
    if audit_snapshot.head != prefix_snapshot.head:
        raise RuntimeError("opening the audit unexpectedly changed canonical head")

    oracle_draft = _semantic_draft(_oracle_bundle(core))
    oracle_transaction = compile_framing_audit_semantic_draft_v2(
        audit_snapshot, contract, oracle_draft
    )
    validate_candidate(
        audit_snapshot,
        oracle_transaction,
        route_registry_hash=ROUTE_REGISTRY_V8_HASH,
        enforce_live_current_policy=True,
    )
    if replay(layout).head != prefix_snapshot.head:
        raise RuntimeError("private oracle validation changed canonical head")

    packet_bytes = canonical_json_bytes(packet)
    contract_bytes = canonical_json_bytes(contract)
    snapshot_bytes = canonical_json_bytes(audit_snapshot)
    semantic_surface = compile_framing_audit_semantic_authoring_contract_v2(
        contract
    )
    common_payload = legacy._framing_payload_contract(contract)
    harness_case = {
        "case_schema": "econ-theorist/framing-authoring-shadow-case/v1",
        "pair_id": PAIR_ID,
        "arm_ids": ARM_IDS,
        "engine_commit": args.engine_commit,
        "wheel_sha256": wheel_sha256,
        "runtime_requirements": {
            "python": platform.python_version(),
            "dependencies": {
                "pydantic": importlib.metadata.version("pydantic"),
                "pydantic-core": importlib.metadata.version("pydantic-core"),
            },
        },
        "base_head": audit_snapshot.head,
        "route_registry_hash": ROUTE_REGISTRY_V8_HASH,
        "work_packet_sha256": sha256_digest(packet_bytes),
        "snapshot_sha256": sha256_digest(snapshot_bytes),
        "authoring_contract_sha256": sha256_digest(contract_bytes),
        "snapshot": audit_snapshot.model_dump(mode="json", exclude_none=False),
        "authoring_contract": contract.model_dump(mode="json", exclude_none=False),
    }
    legacy._write_new(
        private / "HARNESS_CASE.json", canonical_json_bytes(harness_case)
    )
    seed_workspace.cleanup()
    evaluation_key_bytes = (REVIEW_ROOT / "frozen_evaluation_key.md").read_bytes()
    evaluation_key_sha256 = sha256_digest(evaluation_key_bytes)
    legacy._copy_new(REVIEW_ROOT / "protocol.md", output_root / "PAIR_PROTOCOL.md")

    frozen_wheel = runtime / wheel_name
    legacy._write_new(frozen_wheel, wheel_bytes)
    legacy._copy_new(HARNESS_SOURCE, runtime / HARNESS_SOURCE.name)
    legacy._copy_new(PUBLISHER_SOURCE, runtime / PUBLISHER_SOURCE.name)
    installation = subprocess.run(
        (
            str(args.python_runtime.resolve()),
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--no-index",
            "--no-compile",
            "--target",
            str(runtime / "site"),
            str(frozen_wheel),
        ),
        cwd=runtime,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if installation.returncode != 0:
        raise RuntimeError(
            "the exact wheel could not be installed offline: "
            + installation.stderr.strip()[:1000]
        )
    omitted_console_launchers = legacy._normalize_target_install_record(
        runtime / "site"
    )
    checkout_python_sha256 = legacy._verify_installed_python_matches_checkout(
        runtime / "site"
    )
    installed_share = runtime / "site" / "share" / "econ-theorist"
    if not installed_share.is_dir():
        raise RuntimeError("the target-installed wheel lacks its share resources")
    runtime_facts = _verify_frozen_runtime_v2(
        python_runtime=args.python_runtime.resolve(),
        runtime_site=runtime / "site",
        harness=runtime / HARNESS_SOURCE.name,
        expected_engine_version=packet.engine_version,
        expected_engine_semantics_hash=packet.engine_semantics_hash,
    )
    runtime_self_test = _runtime_self_test(
        python_runtime=args.python_runtime.resolve(),
        runtime_site=runtime / "site",
        harness=runtime / HARNESS_SOURCE.name,
        harness_case=private / "HARNESS_CASE.json",
        oracle_draft=oracle_draft,
        oracle_transaction=oracle_transaction,
    )
    runtime_paths = tuple(
        path.relative_to(runtime)
        for path in runtime.rglob("*")
        if path.is_file() and path.name != "RUNTIME_MANIFEST.json"
    )
    runtime_manifest = {
        "manifest_schema": "econ-theorist/framing-authoring-runtime-manifest/v1",
        "pair_id": PAIR_ID,
        "engine_commit": args.engine_commit,
        "wheel_sha256": wheel_sha256,
        "wheel_binding": "frozen_copy_and_checkout_python_match_v1",
        "checkout_python_sha256": checkout_python_sha256,
        "omitted_console_launchers": list(omitted_console_launchers),
        "files": legacy._manifest_rows(runtime, runtime_paths),
    }
    runtime_manifest_bytes = canonical_json_bytes(runtime_manifest)
    legacy._write_new(runtime / "RUNTIME_MANIFEST.json", runtime_manifest_bytes)
    runtime_manifest_sha256 = sha256_digest(runtime_manifest_bytes)

    common_files = {
        "CASE.md": (REVIEW_ROOT / "case.md").read_bytes(),
        "COMMON_WORK_PACKET.json": packet_bytes,
        "FRAMING_PAYLOAD_CONTRACT.json": canonical_json_bytes(common_payload),
    }
    surfaces = {
        "transaction": contract_bytes,
        "semantic_v2": canonical_json_bytes(semantic_surface),
    }
    arm_roots = {
        "transaction": transaction_root,
        "semantic_v2": semantic_root,
    }
    arm_manifest_hashes: dict[str, str] = {}
    for surface, arm_root in arm_roots.items():
        for name, data in common_files.items():
            legacy._write_new(arm_root / name, data)
        legacy._write_new(arm_root / "SURFACE.json", surfaces[surface])
        legacy._write_new(arm_root / "TASK_PROMPT.md", _task_prompt(surface))
        legacy._write_new(
            arm_root / "VERIFY_MANIFEST.ps1", legacy._verification_script()
        )
        legacy._write_new(
            arm_root / "RUN_ATTEMPT.ps1",
            _runner_script(
                output_root=output_root,
                arm_root=arm_root,
                surface=surface,
                python_runtime=args.python_runtime.resolve(),
                runtime_manifest_sha256=runtime_manifest_sha256,
            ),
        )
        visible = (
            Path("CASE.md"),
            Path("COMMON_WORK_PACKET.json"),
            Path("FRAMING_PAYLOAD_CONTRACT.json"),
            Path("SURFACE.json"),
            Path("TASK_PROMPT.md"),
            Path("VERIFY_MANIFEST.ps1"),
            Path("RUN_ATTEMPT.ps1"),
        )
        manifest = {
            "manifest_schema": "econ-theorist/framing-authoring-arm-manifest/v1",
            "pair_id": PAIR_ID,
            "arm_id": ARM_IDS[surface],
            "surface": surface,
            "files": legacy._manifest_rows(arm_root, visible),
        }
        manifest_bytes = canonical_json_bytes(manifest)
        legacy._write_new(arm_root / "MANIFEST.json", manifest_bytes)
        arm_manifest_hashes[surface] = sha256_digest(manifest_bytes)

    order_seed = sha256_digest(
        canonical_json_bytes(
            {
                "pair_id": PAIR_ID,
                "route_registry_hash": ROUTE_REGISTRY_V8_HASH,
                "base_head": audit_snapshot.head,
                "work_packet_sha256": sha256_digest(packet_bytes),
                "authoring_contract_sha256": sha256_digest(contract_bytes),
                "snapshot_sha256": sha256_digest(snapshot_bytes),
                "wheel_sha256": wheel_sha256,
            }
        )
    )
    order = (
        ("arm-transaction", "arm-semantic")
        if int(order_seed[:2], 16) % 2 == 0
        else ("arm-semantic", "arm-transaction")
    )
    launch_root = output_root / "launch"
    launch_root.mkdir()
    launch_paths: dict[str, Path] = {}
    for surface, arm_root in arm_roots.items():
        launch_path = launch_root / f"{arm_root.name}.md"
        legacy._write_new(
            launch_path,
            _launch_prompt(
                arm_root=arm_root,
                surface=surface,
                arm_manifest_sha256=arm_manifest_hashes[surface],
            ),
        )
        launch_paths[arm_root.name] = launch_path

    operator_prompt = f"""# Operator handoff

Pair root: `{output_root}`

The exact `PRE_MANIFEST.json` SHA-256 is supplied externally by the current
development task; it is intentionally not repeated inside this package. Run:

```powershell
./VERIFY_PRE_MANIFEST.ps1 -ExpectedManifestSha256 <EXTERNAL_PRE_MANIFEST_SHA256>
```

Transaction arm manifest SHA-256: `{arm_manifest_hashes['transaction']}`

Semantic V2 arm manifest SHA-256: `{arm_manifest_hashes['semantic_v2']}`

Only after `PRE_MANIFEST_OK`, create two independent new Codex tasks using
`{output_root}` as the workspace root and the same ordinary/medium model. Open
both before reading either result. Run them in this frozen order:

1. Paste `{launch_paths[order[0]]}` into the first task.
2. Paste `{launch_paths[order[1]]}` into the second task.

Each task must remain inside its assigned arm and must not create, fork,
delegate, or execute the sibling arm. Do not let either task read the parent,
sibling arm, repository, or `private_evaluator`. Do not discuss the first
result before the second task has stopped. Neither arm uses the bridge or
canonical commit path.

After both reports exist, return their two report paths to the development
task. High intelligence is not needed for generation; reserve it for the later
blinded economics and cold-reader adjudication.
"""
    legacy._write_new(
        output_root / "OPERATOR_HANDOFF.md", operator_prompt.encode("utf-8")
    )
    legacy._write_new(
        output_root / "VERIFY_PRE_MANIFEST.ps1",
        legacy._pre_verification_script(),
    )
    frozen_files = [
        Path("PAIR_PROTOCOL.md"),
        Path("OPERATOR_HANDOFF.md"),
        Path("VERIFY_PRE_MANIFEST.ps1"),
        Path("launch/arm-transaction.md"),
        Path("launch/arm-semantic.md"),
        Path("private_evaluator/HARNESS_CASE.json"),
        Path(f"runtime/{wheel_name}"),
        Path("runtime/RUNTIME_MANIFEST.json"),
        Path(f"runtime/{HARNESS_SOURCE.name}"),
        Path(f"runtime/{PUBLISHER_SOURCE.name}"),
        Path("arm-transaction/MANIFEST.json"),
        Path("arm-semantic/MANIFEST.json"),
    ]
    pre_rows = legacy._manifest_rows(output_root, frozen_files)
    oracle_bytes = canonical_json_bytes(oracle_transaction)
    pre_manifest = {
        "manifest_schema": "econ-theorist/framing-authoring-pair-pre-manifest/v1",
        "pair_id": PAIR_ID,
        "semantic_surface": "econ-theorist/framing-audit-semantic-authoring-surface/v2",
        "engine_commit": args.engine_commit,
        "route_registry_hash": ROUTE_REGISTRY_V8_HASH,
        "base_head": audit_snapshot.head,
        "work_packet_sha256": sha256_digest(packet_bytes),
        "authoring_contract_sha256": sha256_digest(contract_bytes),
        "snapshot_sha256": sha256_digest(snapshot_bytes),
        "wheel_sha256": wheel_sha256,
        "wheel_binding": "frozen_copy_and_checkout_python_match_v1",
        "checkout_python_sha256": checkout_python_sha256,
        "omitted_console_launchers": list(omitted_console_launchers),
        "runtime_manifest_sha256": runtime_manifest_sha256,
        "arm_manifest_sha256": arm_manifest_hashes,
        "evaluation_key_source": (
            "review_outputs/phase5a2_v8_authoring_pair_v2/"
            "frozen_evaluation_key.md"
        ),
        "evaluation_key_sha256": evaluation_key_sha256,
        "oracle_compiled_transaction_sha256": sha256_digest(oracle_bytes),
        "oracle_v8_valid": True,
        "oracle_canonical_writes": 0,
        "runtime_self_test": runtime_self_test,
        "runtime_facts": runtime_facts,
        "order_seed_sha256": order_seed,
        "execution_order": list(order),
        "files": pre_rows,
    }
    pre_manifest_bytes = canonical_json_bytes(pre_manifest)
    legacy._write_new(output_root / "PRE_MANIFEST.json", pre_manifest_bytes)
    legacy._verify_repository_binding(
        args.engine_commit, allow_dirty_probe=args.allow_dirty_probe
    )
    print("PAIR_PRE_MANIFEST_SHA256 " + sha256_digest(pre_manifest_bytes))
    print(pre_manifest_bytes.decode("utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--engine-commit", required=True)
    parser.add_argument(
        "--allow-dirty-probe",
        action="store_true",
        help="developer-only: bypass the clean exact-commit preparation gate",
    )
    parser.add_argument(
        "--python-runtime", type=Path, default=Path(sys.executable)
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _prepare(args)
        return 0
    except (OSError, RuntimeError, ValueError) as exc:
        print(
            f"pair preparation failed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
