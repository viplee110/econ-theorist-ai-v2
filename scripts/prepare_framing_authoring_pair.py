"""Prepare the frozen held-out registry-V8 authoring shadow pair.

This evaluator-side script creates one deterministic canonical Phase-2 prefix,
opens (but never completes) one fresh framing audit, freezes its Snapshot,
WorkPacket and authoring contract, proves one private semantic oracle through
the unchanged V8 validator, and emits two isolated generator directories.
No model is invoked.
"""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import platform
import re
from typing import Any, Iterable

from econ_theorist.candidate_contract import (
    candidate_authoring_contract_hash,
    compile_candidate_authoring_contract,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.framing_quality import (
    ActiveMarginWitness,
    AggregateInvarianceAssessment,
    ArchetypeTension,
    BenchmarkFramingAssessment,
    CausalChainStep,
    ChoiceConsequenceBinding,
    DistinctiveMechanismAssessment,
    EconomicForce,
    EconomistMemo,
    FramingObjectRef,
    FramingQualityBundle,
    HeldFixedObjectRef,
    IllustrativeMinimalExample,
    PublicStateCondition,
    SelectionAssurance,
)
from econ_theorist.framing_quality_authoring import (
    BenchmarkChannelIntentV1,
    FramingAuditSemanticDraftV1,
    compile_framing_audit_semantic_authoring_contract,
    compile_framing_audit_semantic_draft,
)
from econ_theorist.machine.models import WorkPacketV1
from econ_theorist.machine.navigation import enumerate_navigation_candidates
from econ_theorist.machine.operational import ProjectOperationalLayout
from econ_theorist.machine.packets import read_work_packet
from econ_theorist.machine.run_service import open_or_resume_run
from econ_theorist.models import (
    Actor,
    CreateEntityOp,
    CreateRelationOp,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V8_HASH
from econ_theorist.project import init_project
from econ_theorist.runs import begin_run, transaction_bindings
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import commit_transaction
from econ_theorist.runtime.replay import replay, validate_candidate
from econ_theorist.theory import (
    BenchmarkRecord,
    BenchmarkSet,
    GateDossier,
    GateRequirement,
    PrimitiveEdge,
    PrimitiveGraph,
    PrimitiveNode,
    RationalAssignment,
    ReducedRational,
    ResearchQuestion,
    TheoryPayload,
    pack_theory_payload,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
REVIEW_ROOT = REPOSITORY_ROOT / "review_outputs" / "phase5a2_v8_authoring_pair"
HARNESS_SOURCE = REPOSITORY_ROOT / "scripts" / "run_framing_authoring_shadow.py"

PAIR_ID = "pair.refund.authoring.v8"
ARM_IDS = {"transaction": "arm.transaction", "semantic": "arm.semantic"}
AGENT = Actor(kind="agent", actor_id="paired.shadow.agent")
HUMAN_ID = "human.owner"
T0 = "2026-07-19T08:00:00Z"
T1 = "2026-07-19T08:01:00Z"
T2 = "2026-07-19T08:02:00Z"
T3 = "2026-07-19T08:03:00Z"


def _eref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def _write_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite frozen output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _copy_new(source: Path, target: Path) -> None:
    _write_new(target, source.read_bytes())


def _theory_entity(
    snapshot: Snapshot,
    *,
    entity_id: str,
    payload: TheoryPayload,
    title: str,
    summary: str,
    created_at: str,
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=1,
        project_id=snapshot.project_id,
        title=title,
        summary=summary,
        status=ScientificStatus(lifecycle="proposed"),
        facets=pack_theory_payload(payload),
        privacy="project_private",
        access_compartments=("project_research",),
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
    evidence_refs: tuple[EntityVersionRef, ...],
    route_run_id: str,
    context_id: str,
    transaction_id: str,
    created_at: str,
) -> Snapshot:
    before = replay(layout)
    run = begin_run(
        layout,
        before,
        route_id=route_id,
        actor=AGENT,
        purpose=purpose,
        compartments=("project_research",),
        privacy_clearance="project_private",
        focus_entity_ids=focus,
        budget_units=32_000,
        route_run_id=route_run_id,
        context_manifest_id=context_id,
        created_at=created_at,
        route_registry_hash=ROUTE_REGISTRY_V8_HASH,
    )
    relation_refs = tuple(
        RelationVersionRef(relation_id=item.relation_id, version=item.version)
        for item in relations
    )
    transaction = Transaction(
        **transaction_bindings(layout, route_run_id),
        transaction_id=transaction_id,
        origin="route_run",
        project_id=before.project_id,
        base_revision=run.base_revision,
        route_run_id=route_run_id,
        route_id=route_id,
        actor=AGENT,
        intent=f"Freeze the held-out {route_id} prefix without model generation.",
        operations=(
            *(CreateEntityOp(entity=item) for item in outputs),
            *(CreateRelationOp(relation=item) for item in relations),
            RecordRouteOutcomeOp(
                outcome=RouteOutcome(
                    route_run_id=route_run_id,
                    route_id=route_id,
                    outcome="completed_with_candidate",
                    rationale="Deterministic evaluator setup for a held-out shadow pair.",
                    candidate_refs=(
                        *(_eref(item) for item in outputs),
                        *relation_refs,
                    ),
                    privacy="project_private",
                    access_compartments=("project_research",),
                )
            ),
        ),
        evidence_refs=evidence_refs,
        privacy="project_private",
        access_compartments=("project_research",),
        created_at=created_at,
        parent_transaction_hash=run.base_revision,
    )
    result = commit_transaction(layout, transaction)
    if result.status != "committed":
        raise RuntimeError(f"held-out setup route did not commit: {route_id}")
    return replay(layout)


def _rational(symbol: str, numerator: int, denominator: int) -> RationalAssignment:
    return RationalAssignment(
        symbol=symbol,
        value=ReducedRational(numerator=numerator, denominator=denominator),
    )


def _build_prefix(
    layout: StoreLayout,
) -> tuple[Snapshot, tuple[EntityVersion, EntityVersion, EntityVersion, EntityVersion]]:
    snapshot = replay(layout)
    question = _theory_entity(
        snapshot,
        entity_id="question.failure.refund",
        payload=ResearchQuestion(
            phenomenon=(
                "A failure refund changes only failed-state payments yet can change "
                "whether a threshold project starts."
            ),
            object_to_explain=(
                "When the refund changes provision through the initiator's initial "
                "contribution choice."
            ),
            unresolved_delta=(
                "Fixed strategies leave provision at one third, while sequential "
                "reoptimization moves provision from zero to one third."
            ),
            importance=(
                "Payment rules can change participation and realized provision even "
                "when later conditional behavior is unchanged."
            ),
            kill_condition=(
                "The mechanism fails if the failed-state payment does not strictly "
                "change the initiator's best response or provision remains unchanged."
            ),
            proposed_scope=(
                "One two-person sequential threshold contribution game with fixed "
                "values, costs, type probabilities, timing, and information."
            ),
            candidate_archetypes=("mechanism_explanation",),
            prohibited_claims=(
                "Total welfare rises.",
                "Failure refunds are generally optimal.",
                "The result applies to simultaneous contribution games.",
                "The audit establishes empirical or literature novelty.",
            ),
        ),
        title="Failure-refund participation question",
        summary="Why a failed-state payment rule changes initial participation.",
        created_at=T1,
    )
    benchmarks = _theory_entity(
        snapshot,
        entity_id="benchmarks.failure.refund",
        payload=BenchmarkSet(
            question_ref=_eref(question),
            benchmarks=(
                BenchmarkRecord(
                    benchmark_id="b_fixed_strategy_accounting",
                    label="Fixed strategy accounting",
                    exact_primitives=(
                        "The initiator contribution is fixed at one.",
                        "The follower contributes if high and declines if low.",
                        "Only the failed-campaign refund rule changes.",
                    ),
                    timing=(
                        "Initiator contribution fixed",
                        "Follower observes type",
                        "Follower conditional action",
                        "Threshold provision and payments",
                    ),
                    solution_concept="Exact payoff accounting under fixed strategies.",
                    prediction=(
                        "Initiator payoff moves from -1/3 to +1/3, but provision "
                        "probability is 1/3 under both rules."
                    ),
                    unresolved_delta="The initiator is not allowed to reoptimize.",
                    exact_values=(
                        _rational("no_refund_initiator_payoff", -1, 3),
                        _rational("refund_initiator_payoff", 1, 3),
                        _rational("fixed_strategy_provision", 1, 3),
                    ),
                ),
                BenchmarkRecord(
                    benchmark_id="b_sequential_reoptimization",
                    label="Sequential reoptimization",
                    exact_primitives=(
                        "The initiator chooses whether to contribute one.",
                        "A high follower value is two with probability 1/3; low is zero.",
                        "Both contributions are required and successful contributions cost one.",
                        "A campaign closes before the follower moves if the initiator declines.",
                    ),
                    timing=(
                        "Refund rule fixed",
                        "Initiator contribution choice",
                        "Follower observes type and chooses",
                        "Threshold provision and payments",
                    ),
                    solution_concept="Unique strict subgame-perfect equilibrium by backward induction.",
                    prediction=(
                        "No refund gives no start and zero provision; failure refund "
                        "gives a start and provision probability 1/3."
                    ),
                    unresolved_delta=(
                        "The failed-state payoff now feeds the initiator's strict "
                        "participation comparison."
                    ),
                    exact_values=(
                        _rational("no_refund_provision", 0, 1),
                        _rational("refund_provision", 1, 3),
                    ),
                ),
            ),
            exact_question_delta=(
                "Hold the follower's type-contingent strategy fixed across rules but "
                "allow the initiator's initial contribution to reoptimize."
            ),
        ),
        title="Failure-refund benchmarks",
        summary="Fixed-strategy accounting versus sequential reoptimization.",
        created_at=T1,
    )
    frame_relations = (
        RelationVersion(
            relation_id="relation.refund.question.frames.benchmarks",
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
            relation_id="relation.refund.question.benchmark.delta",
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
        route_run_id="run.pair.refund.frame",
        context_id="context.pair.refund.frame",
        transaction_id="transaction.pair.refund.frame",
        created_at=T1,
    )

    graph = _theory_entity(
        snapshot,
        entity_id="primitives.failure.refund",
        payload=PrimitiveGraph(
            question_ref=_eref(question),
            benchmark_set_ref=_eref(benchmarks),
            nodes=(
                PrimitiveNode(node_id="initiator_actor", kind="actor", label="Initiator", economic_meaning="The first mover chooses whether to open the campaign.", status="primitive"),
                PrimitiveNode(node_id="follower_actor", kind="actor", label="Follower", economic_meaning="The second mover chooses after observing her value.", status="primitive"),
                PrimitiveNode(node_id="refund_rule", kind="institution", label="Failure refund rule", economic_meaning="Failed contributions are kept or returned.", status="primitive"),
                PrimitiveNode(node_id="success_threshold", kind="constraint", label="Two-contribution threshold", economic_meaning="Provision requires both agents to contribute.", status="primitive"),
                PrimitiveNode(node_id="contribution_cost", kind="constraint", label="Contribution cost", economic_meaning="A successful contribution costs one.", status="primitive"),
                PrimitiveNode(node_id="initiator_value", kind="preference_technology", label="Initiator value", economic_meaning="The initiator values provision at two.", status="primitive"),
                PrimitiveNode(node_id="follower_value_type", kind="information", label="Follower value type", economic_meaning="Value two occurs with probability one third and value zero otherwise.", status="primitive"),
                PrimitiveNode(node_id="campaign_timing", kind="timing", label="Sequential campaign timing", economic_meaning="The initiator moves first and a declined start closes the campaign.", status="primitive"),
                PrimitiveNode(node_id="initiator_failure_payoff", kind="outcome", label="Failed-state initiator payoff", economic_meaning="Failure yields minus one without refund and zero with refund.", status="derived"),
                PrimitiveNode(node_id="initiator_payoff_basis", kind="preference_technology", label="Initiator payoff comparison", economic_meaning="Provision value, contribution cost, and failed-state payment determine the initial contribution payoff.", status="derived"),
                PrimitiveNode(node_id="follower_payoff_basis", kind="preference_technology", label="Follower payoff comparison", economic_meaning="Follower value and contribution cost determine the type-contingent choice.", status="derived"),
                PrimitiveNode(node_id="initiator_pledge_choice", kind="choice", label="Initial contribution choice", economic_meaning="The initiator chooses whether to contribute one.", status="derived"),
                PrimitiveNode(node_id="follower_conditional_choice", kind="choice", label="Follower conditional contribution", economic_meaning="The follower contributes if high and declines if low.", status="derived"),
                PrimitiveNode(node_id="provision_probability", kind="outcome", label="Provision probability", economic_meaning="The probability that both contributions occur.", status="derived"),
            ),
            edges=(
                PrimitiveEdge(edge_id="e_refund_failure_payoff", source_node_id="refund_rule", target_node_id="initiator_failure_payoff", economic_meaning="Refund changes the failed-state net payment."),
                PrimitiveEdge(edge_id="e_failure_payoff_basis", source_node_id="initiator_failure_payoff", target_node_id="initiator_payoff_basis", economic_meaning="The failed branch enters expected participation payoff."),
                PrimitiveEdge(edge_id="e_initiator_value_basis", source_node_id="initiator_value", target_node_id="initiator_payoff_basis", economic_meaning="Provision value enters expected participation payoff."),
                PrimitiveEdge(edge_id="e_cost_initiator_basis", source_node_id="contribution_cost", target_node_id="initiator_payoff_basis", economic_meaning="Contribution cost enters initial participation payoff."),
                PrimitiveEdge(edge_id="e_payoff_initiation", source_node_id="initiator_payoff_basis", target_node_id="initiator_pledge_choice", economic_meaning="The strict payoff comparison determines campaign initiation."),
                PrimitiveEdge(edge_id="e_timing_initiation", source_node_id="campaign_timing", target_node_id="initiator_pledge_choice", economic_meaning="Sequential timing defines the initial decision."),
                PrimitiveEdge(edge_id="e_initiation_follower", source_node_id="initiator_pledge_choice", target_node_id="follower_conditional_choice", economic_meaning="Only an opened campaign reaches the follower decision."),
                PrimitiveEdge(edge_id="e_type_follower_basis", source_node_id="follower_value_type", target_node_id="follower_payoff_basis", economic_meaning="Follower type enters her payoff comparison."),
                PrimitiveEdge(edge_id="e_cost_follower_basis", source_node_id="contribution_cost", target_node_id="follower_payoff_basis", economic_meaning="Contribution cost enters the follower payoff comparison."),
                PrimitiveEdge(edge_id="e_follower_basis_choice", source_node_id="follower_payoff_basis", target_node_id="follower_conditional_choice", economic_meaning="The strict type-specific payoff comparison determines contribution."),
                PrimitiveEdge(edge_id="e_threshold_follower", source_node_id="success_threshold", target_node_id="follower_conditional_choice", economic_meaning="The threshold makes the follower pivotal after initiation."),
                PrimitiveEdge(edge_id="e_timing_follower", source_node_id="campaign_timing", target_node_id="follower_conditional_choice", economic_meaning="The follower acts only after observing type and initiation."),
                PrimitiveEdge(edge_id="e_follower_provision", source_node_id="follower_conditional_choice", target_node_id="provision_probability", economic_meaning="Conditional follower contribution completes the threshold."),
                PrimitiveEdge(edge_id="e_threshold_provision", source_node_id="success_threshold", target_node_id="provision_probability", economic_meaning="Both contributions are required for provision."),
            ),
        ),
        title="Failure-refund primitive graph",
        summary="Payment mapping, payoff comparisons, sequential choices, and provision.",
        created_at=T2,
    )
    dossier = _theory_entity(
        snapshot,
        entity_id="dossier.g1.failure.refund.source",
        payload=GateDossier(
            gate_kind="G1_question_benchmark",
            research_question_ref=_eref(question),
            ordered_object_refs=(_eref(question), _eref(benchmarks), _eref(graph)),
            requirements=(
                GateRequirement(requirement_id="g1.refund.question", description="The exact question, scope, and kill condition are explicit.", evidence_refs=(_eref(question),), recorded_condition="evidence_supplied"),
                GateRequirement(requirement_id="g1.refund.benchmarks", description="Fixed-strategy mapping and sequential reoptimization are separated and hand-solvable.", evidence_refs=(_eref(benchmarks),), recorded_condition="evidence_supplied"),
                GateRequirement(requirement_id="g1.refund.graph", description="The primitive graph closes both benchmark channels.", evidence_refs=(_eref(graph),), recorded_condition="evidence_supplied"),
                GateRequirement(requirement_id="g1.refund.scope", description="Welfare, general optimality, empirical validity, and novelty remain outside scope.", evidence_refs=(_eref(question),), recorded_condition="risk_disclosed"),
            ),
            proposed_action="approve",
            rationale="The deterministic prefix proposes a complete question and benchmark package for human G1 review; it does not confirm that review.",
            prepared_at=T2,
        ),
        title="Source G1 failure-refund dossier",
        summary="Proposed pre-G1 question, benchmarks, graph, and scope boundary.",
        created_at=T2,
    )
    decompose_relations = (
        RelationVersion(
            relation_id="relation.refund.question.decomposes.graph",
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
            relation_id="relation.refund.dossier.governs.question",
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
        route_run_id="run.pair.refund.decompose",
        context_id="context.pair.refund.decompose",
        transaction_id="transaction.pair.refund.decompose",
        created_at=T2,
    )
    return snapshot, (question, benchmarks, graph, dossier)


def _held(
    object_id: str,
    label: str,
    level: str,
    node_id: str,
    fixing: str,
) -> HeldFixedObjectRef:
    return HeldFixedObjectRef(
        object_id=object_id,
        label=label,
        semantic_level=level,
        primitive_node_id=node_id,
        fixing_level=fixing,
    )


def _object(
    object_id: str, label: str, level: str, node_id: str
) -> FramingObjectRef:
    return FramingObjectRef(
        object_id=object_id,
        label=label,
        semantic_level=level,
        primitive_node_id=node_id,
    )


def _oracle_bundle(
    core: tuple[EntityVersion, EntityVersion, EntityVersion, EntityVersion],
) -> FramingQualityBundle:
    question, benchmarks, graph, dossier = core
    refund_state = PublicStateCondition(
        node_id="refund_rule", relation="equals", value="failure_refund"
    )
    high_type_state = PublicStateCondition(
        node_id="follower_value_type", relation="equals", value="high_value_two"
    )
    initiator_witness = ActiveMarginWitness(
        decision_node_id="initiator_pledge_choice",
        payoff_node_ids=("initiator_payoff_basis",),
        concrete_state="Failure refund, high-type probability 1/3, and all other primitives fixed.",
        decision_maker="Initiator",
        focal_action="Contribute one and open the campaign",
        alternative_action="Decline and close the campaign",
        focal_payoff="(1/3)(2-1)+(2/3)0=1/3",
        alternative_payoff="0",
        feasibility_basis="Both initial actions are feasible before the follower moves.",
        best_response_inequality="1/3 > 0",
        activity_status="active",
        status_basis="The refund makes initiation a strict best response.",
        kill_condition="The refund fails to make expected initiation payoff strictly positive.",
        consequence_binding=ChoiceConsequenceBinding(
            consequence_node_id="provision_probability",
            transition_kind="increase",
            causal_edge_ids=("e_initiation_follower", "e_follower_provision"),
            public_state_conditions=(refund_state,),
            focal_consequence="An opened campaign is provided with probability 1/3.",
            alternative_consequence="A closed campaign has provision probability zero.",
            feasibility_basis="Initiation versus closure is compared before any follower action.",
        ),
    )
    follower_witness = ActiveMarginWitness(
        decision_node_id="follower_conditional_choice",
        payoff_node_ids=("follower_payoff_basis",),
        concrete_state="Opened campaign and follower value two.",
        decision_maker="High-value follower",
        focal_action="Contribute one",
        alternative_action="Decline",
        focal_payoff="2-1=1",
        alternative_payoff="0",
        feasibility_basis="Both follower actions are feasible after an opened campaign.",
        best_response_inequality="1 > 0",
        activity_status="active",
        status_basis="The high type contributes strictly; the low type declines strictly.",
        kill_condition="The type-contingent follower comparison is not strict as stated.",
        consequence_binding=ChoiceConsequenceBinding(
            consequence_node_id="provision_probability",
            transition_kind="increase",
            causal_edge_ids=("e_follower_provision",),
            public_state_conditions=(high_type_state,),
            focal_consequence="The second contribution completes the threshold.",
            alternative_consequence="Declining leaves the project unprovided.",
            feasibility_basis="The opened campaign gives the high type both actions.",
        ),
    )
    fixed_primitives = (
        _held("fixed.threshold", "Two-contribution threshold", "primitive", "success_threshold", "primitive"),
        _held("fixed.cost", "Contribution cost one", "primitive", "contribution_cost", "primitive"),
        _held("fixed.initiator.value", "Initiator value two", "primitive", "initiator_value", "primitive"),
        _held("fixed.follower.types", "Follower type values and probabilities", "primitive", "follower_value_type", "primitive"),
        _held("fixed.timing", "Sequential timing and close rule", "primitive", "campaign_timing", "primitive"),
    )
    fixed_assessment = BenchmarkFramingAssessment(
        benchmark_id="b_fixed_strategy_accounting",
        changed=(_object("refund.rule.fixed.strategy", "Failure refund rule", "primitive", "refund_rule"),),
        held_fixed=(
            *fixed_primitives,
            _held("fixed.initiator.choice", "Initial contribution fixed at one", "choice", "initiator_pledge_choice", "choice"),
            _held("fixed.follower.choice", "High contributes and low declines", "behavioral_response", "follower_conditional_choice", "realized_behavior"),
        ),
        reoptimizing=(),
        still_endogenous=(
            _object("mapped.failure.payoff", "Failed-state payoff entry", "payoff_ledger", "initiator_failure_payoff"),
            _object("fixed.strategy.provision", "Provision under fixed strategies", "outcome", "provision_probability"),
        ),
        targets=(_object("target.failure.payoff", "Initiator failed-state payoff", "payoff_ledger", "initiator_failure_payoff"),),
        channel_kind="boundary_or_mapping",
        channel_path=("refund_rule", "initiator_failure_payoff"),
        channel_summary="Refund changes the failed-state ledger while fixed behavior leaves provision at one third.",
        aggregate_invariance=AggregateInvarianceAssessment(
            aggregate_object="Provision probability under the fixed follower strategy",
            pointwise_policy_fixed=True,
            weighting_distribution_status="fixed",
            claims_aggregate_fixed=True,
            basis="The high-type probability and both strategies are fixed.",
            implication_for_attribution="The ledger mapping alone is not an active provision response.",
        ),
        selection_assurance=SelectionAssurance(
            status="not_applicable",
            selection_rule="No equilibrium selection is used in fixed-strategy accounting.",
            basis="The benchmark mechanically evaluates a declared strategy profile.",
            implication_for_attribution="The benchmark supplies a mapping boundary only.",
        ),
        attribution_strength="clean",
        attribution_basis="The changed ledger and held-fixed choices are explicitly separated.",
        distinctive_mechanism=DistinctiveMechanismAssessment(
            claim_kind="not_claimed",
            mechanism_label="No active response is claimed in fixed-strategy accounting.",
            basis="The benchmark intentionally freezes both choices.",
        ),
    )
    active_assessment = BenchmarkFramingAssessment(
        benchmark_id="b_sequential_reoptimization",
        changed=(_object("refund.rule.reoptimization", "Failure refund rule", "primitive", "refund_rule"),),
        held_fixed=fixed_primitives,
        reoptimizing=(_object("initiator.choice.response", "Initial contribution choice", "choice", "initiator_pledge_choice"),),
        still_endogenous=(
            _object("follower.conditional.response", "Follower type-contingent contribution", "behavioral_response", "follower_conditional_choice"),
            _object("equilibrium.provision", "Equilibrium provision probability", "outcome", "provision_probability"),
        ),
        targets=(_object("target.provision", "Provision probability", "outcome", "provision_probability"),),
        channel_kind="active_response",
        channel_path=(
            "refund_rule",
            "initiator_failure_payoff",
            "initiator_payoff_basis",
            "initiator_pledge_choice",
            "follower_conditional_choice",
            "provision_probability",
        ),
        channel_summary="Refund removes failed-state loss, flips initial participation, activates the unchanged follower strategy, and raises provision from zero to one third.",
        aggregate_invariance=AggregateInvarianceAssessment(
            aggregate_object="Provision probability",
            pointwise_policy_fixed=True,
            weighting_distribution_status="fixed",
            claims_aggregate_fixed=False,
            basis="Type probabilities and the follower's type-contingent strategy are fixed while initial participation changes.",
            implication_for_attribution="The provision change is not a reweighting of follower types.",
        ),
        selection_assurance=SelectionAssurance(
            status="unique_equilibrium",
            selection_rule="Backward induction with strict choices at every reached decision.",
            basis="High and low follower types and the initiator each have strict comparisons.",
            implication_for_attribution="No arbitrary off-path selector drives the provision change.",
        ),
        attribution_strength="clean",
        attribution_basis="Only the refund rule changes and the unique active response is initial participation.",
        distinctive_mechanism=DistinctiveMechanismAssessment(
            claim_kind="choice_mediated",
            mechanism_label="Refund-induced campaign initiation",
            contrast_benchmark_id="b_fixed_strategy_accounting",
            distinctive_node_ids=("initiator_pledge_choice",),
            distinctive_edge_ids=("e_initiation_follower", "e_follower_provision"),
            consequence_node_id="provision_probability",
            transition_kind="increase",
            required_public_state_conditions=(refund_state,),
            basis="The active benchmark adds the initiator choice and its exact path to provision.",
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
            conventional_prediction="A failed-state refund only changes accounting after failure.",
            economic_puzzle="The same follower behavior yields a higher provision probability once initiation can respond.",
            resolution_target="Separate the payoff mapping from the initiator's active participation response.",
        ),
        forces=(
            EconomicForce(
                force_id="force.refund.participation",
                label="Refund-induced initial participation",
                role="equilibrium_feedback",
                operative_margin="Initiator contribution",
                direction="raises_target",
                economic_logic="Removing failed-state loss makes campaign initiation strictly profitable.",
                active_when="The initiator can reoptimize before the follower moves.",
                source_node_id="refund_rule",
                margin_node_id="initiator_pledge_choice",
                target_node_id="provision_probability",
            ),
        ),
        causal_chain=(
            CausalChainStep(step_number=1, force_ids=("force.refund.participation",), cause="Failure contributions are returned rather than kept.", endogenous_response="The failed-state initiator payoff rises from minus one to zero.", consequence="Expected contribution payoff rises from minus one third to plus one third.", source_node_id="refund_rule", target_node_id="initiator_failure_payoff"),
            CausalChainStep(step_number=2, force_ids=("force.refund.participation",), cause="The initiator's expected contribution payoff becomes positive.", endogenous_response="The initiator switches from declining to contributing.", consequence="The campaign reaches the follower's type-contingent decision.", source_node_id="initiator_failure_payoff", target_node_id="initiator_pledge_choice", active_margin_witness=initiator_witness),
            CausalChainStep(step_number=3, force_ids=("force.refund.participation",), cause="An opened campaign reaches the follower.", endogenous_response="The high type contributes and the low type declines under the same conditional strategy.", consequence="Provision probability rises from zero to one third.", source_node_id="initiator_pledge_choice", target_node_id="provision_probability", active_margin_witness=follower_witness),
        ),
        minimal_example=IllustrativeMinimalExample(
            title="Two contributors and a two-contribution threshold",
            setup="An initiator moves before a privately informed follower; a failed initial contribution is kept or refunded.",
            moving_primitive="Failed-campaign refund rule",
            held_fixed=("Values", "Costs", "Type probabilities", "Threshold", "Timing", "Information"),
            endogenous_responses=("Initial contribution", "Follower type-contingent contribution"),
            predicted_pattern="The follower strategy is unchanged, but provision moves from zero to one third when initiation responds.",
            economic_intuition="A failed-state payment changes whether the later contribution opportunity exists.",
            limitation="The example makes no welfare, optimality, universality, empirical, or novelty claim.",
            cannot_establish=("General optimal refund design", "Total welfare", "Empirical relevance", "Literature novelty"),
        ),
        economist_memo=EconomistMemo(
            headline="A refund can create the campaign it seems only to insure",
            opening_question="Can a failed-state refund raise provision without changing the follower's strategy?",
            benchmark_message="With strategies fixed, the refund changes the initiator ledger but provision stays at one third.",
            tension_message="Once the initiator can opt out, that same ledger change determines whether the follower ever moves.",
            mechanism_message="The refund flips a strict initial participation comparison while high and low follower choices remain unchanged.",
            result_preview="Provision rises from zero to one third under the failure refund.",
            contribution_message="The comparison separates payoff mapping from choice-mediated implementation.",
            scope_condition="The result is limited to the stated sequential two-person threshold game.",
            reader_takeaway="Payment rules can change realized provision by opening or closing later decision nodes.",
        ),
        benchmark_assessments=(fixed_assessment, active_assessment),
        distinctive_mechanism_contribution_status="claimed",
        disclosed_gaps=(),
        proposed_action="ready_for_g1",
        action_rationale="Both exact benchmarks, active payoff witnesses, selection, and claim boundaries are explicit for proposed human G1 review.",
    )


def _semantic_draft(bundle: FramingQualityBundle) -> FramingAuditSemanticDraftV1:
    raw = bundle.model_dump(mode="json", exclude_none=False)
    for field_name in (
        "research_question_ref",
        "benchmark_set_ref",
        "primitive_graph_ref",
        "source_g1_dossier_ref",
    ):
        raw.pop(field_name)
    intents: list[BenchmarkChannelIntentV1] = []
    for row in raw["benchmark_assessments"]:
        path = tuple(row.pop("channel_path"))
        intents.append(
            BenchmarkChannelIntentV1(
                benchmark_id=row["benchmark_id"],
                changed_object_id=row["changed"][0]["object_id"],
                target_object_id=row["targets"][0]["object_id"],
                ordered_waypoint_node_ids=path[1:-1],
            )
        )
    return FramingAuditSemanticDraftV1(
        bundle_payload=raw,
        channel_intents=tuple(intents),
        transaction_intent="Compile the held-out failure-refund economics framing audit.",
        outcome_rationale="The held-out semantic draft passed compiler preflight and unchanged V8 validation.",
        bundle_title="Failure-refund economics framing preflight",
        bundle_summary="Payoff mapping, initial participation, conditional response, and provision.",
        replacement_dossier_title="Replacement G1 failure-refund dossier",
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
        operation_key="pair-refund-audit-open-v1",
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


def _manifest_rows(root: Path, relative_paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for relative in sorted(relative_paths, key=lambda item: item.as_posix()):
        path = root / relative
        data = path.read_bytes()
        rows.append(
            {
                "path": relative.as_posix(),
                "bytes": len(data),
                "sha256": sha256_digest(data),
            }
        )
    return rows


def _verification_script() -> bytes:
    return (
        "param(\r\n"
        "  [Parameter(Mandatory=$true)]\r\n"
        "  [ValidatePattern('^[0-9a-f]{64}$')]\r\n"
        "  [string]$ExpectedManifestSha256\r\n"
        ")\r\n"
        "$ErrorActionPreference = 'Stop'\r\n"
        "$root = Split-Path -Parent $MyInvocation.MyCommand.Path\r\n"
        "$manifestPath = Join-Path $root 'MANIFEST.json'\r\n"
        "$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()\r\n"
        "if ($manifestHash -ne $ExpectedManifestSha256) { throw 'INVALID_SETUP: arm manifest digest differs from the external launch anchor' }\r\n"
        "$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json\r\n"
        "foreach ($item in $manifest.files) {\r\n"
        "  $path = Join-Path $root $item.path\r\n"
        "  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw \"missing frozen file: $($item.path)\" }\r\n"
        "  $size = (Get-Item -LiteralPath $path).Length\r\n"
        "  $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()\r\n"
        "  if ($size -ne $item.bytes -or $hash -ne $item.sha256) { throw \"frozen file mismatch: $($item.path)\" }\r\n"
        "}\r\n"
        "$expected = @('MANIFEST.json') + @($manifest.files | ForEach-Object { $_.path })\r\n"
        "$unexpected = @(Get-ChildItem -LiteralPath $root -Recurse -File | ForEach-Object { $_.FullName.Substring($root.Length + 1).Replace('\\','/') } | Where-Object { $_ -notin $expected })\r\n"
        "if ($unexpected.Count -gt 0) { throw \"INVALID_SETUP: unlisted arm file(s): $($unexpected -join ',')\" }\r\n"
        "Write-Output \"MANIFEST_OK $($manifest.arm_id) $manifestHash $($manifest.files.Count) files\"\r\n"
    ).encode("utf-8")


def _pre_verification_script() -> bytes:
    return (
        "param(\r\n"
        "  [Parameter(Mandatory=$true)]\r\n"
        "  [ValidatePattern('^[0-9a-f]{64}$')]\r\n"
        "  [string]$ExpectedManifestSha256\r\n"
        ")\r\n"
        "$ErrorActionPreference = 'Stop'\r\n"
        "$root = Split-Path -Parent $MyInvocation.MyCommand.Path\r\n"
        "$manifestPath = Join-Path $root 'PRE_MANIFEST.json'\r\n"
        "$manifestHash = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash.ToLowerInvariant()\r\n"
        "if ($manifestHash -ne $ExpectedManifestSha256) { throw 'INVALID_SETUP: pair pre-manifest digest differs from the external development-task anchor' }\r\n"
        "$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json\r\n"
        "foreach ($item in $manifest.files) {\r\n"
        "  $path = Join-Path $root $item.path\r\n"
        "  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw \"missing frozen pair file: $($item.path)\" }\r\n"
        "  $size = (Get-Item -LiteralPath $path).Length\r\n"
        "  $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()\r\n"
        "  if ($size -ne $item.bytes -or $hash -ne $item.sha256) { throw \"frozen pair file mismatch: $($item.path)\" }\r\n"
        "}\r\n"
        "$expandedExpected = @('PRE_MANIFEST.json') + @($manifest.files | ForEach-Object { $_.path })\r\n"
        "foreach ($armName in @('arm-transaction','arm-semantic')) {\r\n"
        "  $armRoot = Join-Path $root $armName\r\n"
        "  $armManifest = Get-Content -LiteralPath (Join-Path $armRoot 'MANIFEST.json') -Raw | ConvertFrom-Json\r\n"
        "  foreach ($item in $armManifest.files) {\r\n"
        "    $path = Join-Path $armRoot $item.path\r\n"
        "    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw \"missing arm file: $armName/$($item.path)\" }\r\n"
        "    $size = (Get-Item -LiteralPath $path).Length\r\n"
        "    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()\r\n"
        "    if ($size -ne $item.bytes -or $hash -ne $item.sha256) { throw \"arm file mismatch: $armName/$($item.path)\" }\r\n"
        "    $expandedExpected += \"$armName/$($item.path)\"\r\n"
        "  }\r\n"
        "}\r\n"
        "$runtimeRoot = Join-Path $root 'runtime'\r\n"
        "$runtimeManifest = Get-Content -LiteralPath (Join-Path $runtimeRoot 'RUNTIME_MANIFEST.json') -Raw | ConvertFrom-Json\r\n"
        "foreach ($item in $runtimeManifest.files) {\r\n"
        "  $path = Join-Path $runtimeRoot $item.path\r\n"
        "  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw \"missing runtime file: $($item.path)\" }\r\n"
        "  $size = (Get-Item -LiteralPath $path).Length\r\n"
        "  $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()\r\n"
        "  if ($size -ne $item.bytes -or $hash -ne $item.sha256) { throw \"runtime file mismatch: $($item.path)\" }\r\n"
        "  $expandedExpected += \"runtime/$($item.path)\"\r\n"
        "}\r\n"
        "$actual = @(Get-ChildItem -LiteralPath $root -Recurse -File | ForEach-Object { $_.FullName.Substring($root.Length + 1).Replace('\\','/') })\r\n"
        "$unexpected = @($actual | Where-Object { $_ -notin $expandedExpected })\r\n"
        "if ($unexpected.Count -gt 0) { throw \"INVALID_SETUP: unlisted pair file(s): $($unexpected -join ',')\" }\r\n"
        "Write-Output \"PRE_MANIFEST_OK $manifestHash $($manifest.files.Count) files\"\r\n"
    ).encode("utf-8")


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
    harness = runtime_root / "run_framing_authoring_shadow.py"
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
        "$source = Join-Path $workRoot \"attempt_$number.json\"\r\n"
        "if (-not (Test-Path -LiteralPath $source -PathType Leaf)) { throw \"missing exact attempt source: $source\" }\r\n"
        "$sourceInfo = Get-Item -LiteralPath $source\r\n"
        "if (($sourceInfo.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'INVALID_SETUP: attempt source cannot be a reparse point' }\r\n"
        f"$receipt = Join-Path '{arm_root}' \"work/attempt_$number.receipt.json\"\r\n"
        f"$projection = Join-Path '{arm_root}' \"work/attempt_$number.scientific_projection.json\"\r\n"
        "$arguments = @(\r\n"
        f"  '{harness}', '--case', '{case_path}', '--surface', '{surface}',\r\n"
        f"  '--arm-id', '{ARM_IDS[surface]}', '--attempt', $Attempt, '--source', $source,\r\n"
        "  '--receipt', $receipt, '--projection', $projection\r\n"
        ")\r\n"
        "if ($Attempt -gt 1) {\r\n"
        "  $previous = ($Attempt - 1).ToString('00')\r\n"
        f"  $arguments += @('--prior-receipt', (Join-Path '{arm_root}' \"work/attempt_$previous.receipt.json\"))\r\n"
        "}\r\n"
        f"& '{python_runtime}' @arguments\r\n"
        "exit $LASTEXITCODE\r\n"
    ).encode("utf-8")


def _task_prompt(surface: str) -> bytes:
    common = """# TASK PROMPT

Use the ordinary/medium model selected for this paired test.  Work only in
this directory.  Continue only if the launch message's exact-digest call to
`VERIFY_MANIFEST.ps1` returned `MANIFEST_OK`; otherwise stop and report
`INVALID_SETUP`.

Do not use an old conversation, network access, subagents, repository source,
tests or fixtures, R2/R3 material, the parent directory, sibling arm, evaluator
key, or any file not listed by this arm's manifest.  The frozen harness script
may be executed only through `./RUN_ATTEMPT.ps1`; do not open or inspect it.
This is a noncanonical shadow: do not invoke the etai bridge, stage or commit
anything, finish a run, or confirm a human gate.  Do not request human editing.

Read `CASE.md`, `COMMON_WORK_PACKET.json`,
`FRAMING_PAYLOAD_CONTRACT.json`, and this arm's `SURFACE.json`.  Produce only
the surface-specific JSON in `work/attempt_01.json`, then run:

```powershell
./RUN_ATTEMPT.ps1 -Attempt 1
```

If the immutable receipt rejects it, copy the complete receipt diagnostics
without summary or added hints into your own reasoning, revise only from those
diagnostics, and run attempt 2 and then at most attempt 3 with the corresponding
filenames.  Every new artifact counts as an experimental repair.  Stop at the
first `validator_pass: true` or after attempt 3.  Never overwrite an artifact
or receipt.

Write `report/agent_report.md` with manifest result, requested/visible model
label, a statement that actual backend/provider was or was not independently
observable, each source and receipt digest, elapsed times, final status, and a
statement that canonical writes and human gates were zero.  Do not guess an
unobservable provider identity.

"""
    if surface == "transaction":
        specific = """## This arm: complete Transaction

Write one complete Transaction JSON exactly under `SURFACE.json`, including
all required wrappers, exact bindings, output objects, relations, hashes and
route outcome.  Use explicit JSON null only where the frozen draft-hash
contract permits the harness to materialize it.  Do not call, imitate, or
reconstruct the semantic compiler.
"""
    else:
        specific = """## This arm: semantic draft

Write one `FramingAuditSemanticDraftV1` exactly under `SURFACE.json`.
`bundle_payload` contains all scientific FramingQualityBundle content but must
omit the four exact input refs and every assessment's `channel_path`.  Provide
exactly one `channel_intent` per benchmark: its changed object ID, target
object ID, and only the ordered PrimitiveGraph waypoints needed to select the
directed path.  Do not author a Transaction, EntityVersion wrapper,
replacement GateDossier, relation, canonical ID/hash, or route outcome; those
are compiler-owned.
"""
    return (common + specific).encode("utf-8")


def _launch_prompt(
    *, arm_root: Path, surface: str, arm_manifest_sha256: str
) -> bytes:
    return f"""# Frozen paired-authoring task launch

This is the `{surface}` arm.  Open the new Codex task with this exact workspace
root so the frozen runner can read the pair runtime:

`{arm_root.parent}`

Then set the task's shell working directory to exactly:

`{arm_root}`

The externally supplied expected SHA-256 of this arm's `MANIFEST.json` is:

`{arm_manifest_sha256}`

Before opening any arm file, run exactly:

```powershell
./VERIFY_MANIFEST.ps1 -ExpectedManifestSha256 {arm_manifest_sha256}
```

If and only if it prints `MANIFEST_OK`, read `TASK_PROMPT.md` and follow it.
Otherwise stop with `INVALID_SETUP`.  Do not read the parent directory, the
sibling arm, the repository, or any old conversation.
""".encode("utf-8")


def _framing_payload_contract(contract: Any) -> dict[str, Any]:
    bundles = [
        item.model_dump(mode="json", exclude_none=False)
        for item in contract.payload_schemas
        if item.entity_type == "FramingQualityBundle"
    ]
    if len(bundles) != 1:
        raise RuntimeError("candidate contract lacks one FramingQualityBundle schema")
    return {
        "payload_contract_schema": "econ-theorist/framing-pair-payload-contract/v1",
        "candidate_authoring_contract_hash": candidate_authoring_contract_hash(
            contract
        ),
        "framing_quality_bundle": bundles[0],
        "model_invariants": [
            item.model_dump(mode="json", exclude_none=False)
            for item in contract.output_contract.model_invariants
        ],
    }


def _verify_repository_binding(engine_commit: str, *, allow_dirty_probe: bool) -> None:
    if allow_dirty_probe:
        return
    if re.fullmatch(r"[0-9a-f]{40}", engine_commit) is None:
        raise RuntimeError("engine commit must be one exact lowercase Git SHA")
    head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    status = subprocess.run(
        ("git", "status", "--porcelain", "--untracked-files=all"),
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if (
        head.returncode != 0
        or head.stdout.strip() != engine_commit
        or status.returncode != 0
        or status.stdout.strip()
    ):
        raise RuntimeError(
            "pair preparation requires the exact clean engine commit named by the manifest"
        )


def _verify_installed_python_matches_checkout(runtime_site: Path) -> str:
    source_root = REPOSITORY_ROOT / "src" / "econ_theorist"
    installed_root = runtime_site / "econ_theorist"
    source_files = {
        path.relative_to(source_root).as_posix(): path
        for path in source_root.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    installed_files = {
        path.relative_to(installed_root).as_posix(): path
        for path in installed_root.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    if not source_files or set(source_files) != set(installed_files):
        raise RuntimeError(
            "the wheel's installed Python module set differs from the exact checkout"
        )
    rows: list[dict[str, Any]] = []
    for relative in sorted(source_files):
        source_data = source_files[relative].read_bytes()
        installed_data = installed_files[relative].read_bytes()
        if source_data != installed_data:
            raise RuntimeError(
                "the wheel's installed Python bytes differ from the exact checkout: "
                + relative
            )
        rows.append(
            {
                "path": relative,
                "bytes": len(source_data),
                "sha256": sha256_digest(source_data),
            }
        )
    return sha256_digest(canonical_json_bytes(rows))


def _normalize_target_install_record(runtime_site: Path) -> tuple[str, ...]:
    distributions = tuple(runtime_site.glob("econ_theorist_ai-*.dist-info"))
    if len(distributions) != 1:
        raise RuntimeError("target runtime does not contain one engine distribution")
    record = distributions[0] / "RECORD"
    try:
        with record.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise RuntimeError("target-installed engine RECORD is unreadable") from exc
    normalized_rows: list[list[str]] = []
    omitted_launchers: list[str] = []
    for row in rows:
        if len(row) != 3:
            raise RuntimeError("target-installed engine RECORD row is malformed")
        logical = row[0]
        while logical.startswith("../"):
            logical = logical[3:]
        normalized_logical = logical.replace("\\", "/")
        if normalized_logical.casefold() in {
            "bin/etai",
            "bin/etai.exe",
            "scripts/etai.exe",
        }:
            launcher = runtime_site / Path(normalized_logical)
            if not launcher.is_file():
                raise RuntimeError(
                    "target-installed console launcher is absent before omission"
                )
            launcher.unlink()
            omitted_launchers.append(normalized_logical)
            continue
        if logical != row[0] and not (runtime_site / logical).is_file():
            raise RuntimeError(
                "target-installed wheel data file is absent after RECORD projection"
            )
        normalized_rows.append([logical, row[1], row[2]])
    try:
        with record.open("w", encoding="utf-8", newline="") as stream:
            csv.writer(stream, lineterminator="\n").writerows(normalized_rows)
    except OSError as exc:
        raise RuntimeError("target-installed engine RECORD cannot be projected") from exc
    for directory_name in ("bin", "Scripts"):
        directory = runtime_site / directory_name
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    return tuple(sorted(omitted_launchers))


def _verify_frozen_runtime(
    *,
    python_runtime: Path,
    runtime_site: Path,
    harness: Path,
    expected_engine_version: str,
    expected_engine_semantics_hash: str,
) -> dict[str, str]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(runtime_site)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    probe = subprocess.run(
        (
            str(python_runtime),
            "-c",
            (
                "import json; from pathlib import Path; import econ_theorist; "
                "from econ_theorist.framing_quality_authoring import "
                "compile_framing_audit_semantic_authoring_contract; "
                "from econ_theorist.machine.bootstrap import current_engine_semantics_hash; "
                "from econ_theorist.policy import ROUTE_REGISTRY_HASH, route_spec; "
                "assert route_spec('audit.framing_economics').route_version == 8; "
                "print(json.dumps({'module_path': str(Path(econ_theorist.__file__).resolve()), "
                "'engine_version': econ_theorist.__version__, "
                "'engine_semantics_hash': current_engine_semantics_hash(), "
                "'route_registry_hash': ROUTE_REGISTRY_HASH}, sort_keys=True))"
            ),
        ),
        cwd=runtime_site.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if probe.returncode != 0:
        raise RuntimeError(
            "the frozen wheel cannot import the semantic compiler: "
            + probe.stderr.strip()[:1000]
        )
    try:
        facts = json.loads(probe.stdout)
        imported = Path(facts["module_path"]).resolve()
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("the frozen runtime probe returned invalid facts") from exc
    try:
        imported.relative_to(runtime_site.resolve())
    except ValueError as exc:
        raise RuntimeError(
            "runtime probe imported econ_theorist outside the extracted wheel"
        ) from exc
    if (
        facts.get("engine_version") != expected_engine_version
        or facts.get("engine_semantics_hash") != expected_engine_semantics_hash
        or facts.get("route_registry_hash") != ROUTE_REGISTRY_V8_HASH
    ):
        raise RuntimeError(
            "the frozen wheel differs from the exact WorkPacket engine bindings"
        )
    harness_probe = subprocess.run(
        (str(python_runtime), str(harness), "--help"),
        cwd=runtime_site.parent,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if harness_probe.returncode != 0:
        raise RuntimeError(
            "the frozen shadow harness cannot start: "
            + harness_probe.stderr.strip()[:1000]
        )
    return {str(key): str(value) for key, value in facts.items()}


def _runtime_self_test(
    *,
    python_runtime: Path,
    runtime_site: Path,
    harness: Path,
    harness_case: Path,
    oracle_draft: FramingAuditSemanticDraftV1,
    oracle_transaction: Transaction,
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(runtime_site)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    results: dict[str, Any] = {}
    with tempfile.TemporaryDirectory(prefix="etai-pair-runtime-self-test-") as raw:
        root = Path(raw)
        sources = {
            "transaction": canonical_json_bytes(oracle_transaction),
            "semantic": canonical_json_bytes(oracle_draft),
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
                or receipt_value.get("head_before")
                != receipt_value.get("head_after")
                or receipt_value.get("experimental_repairs_submitted") != 0
                or receipt_value.get("experimental_repair_required") is not False
                or receipt_value.get("engine_route_repair_equivalent") != 0
                or receipt_value.get(
                    "engine_route_repair_eligible_for_burden_comparison"
                )
                is not False
                or not isinstance(
                    receipt_value.get("source_canonical_json_bytes"), int
                )
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
            or invalid_value.get("issue_taxonomy", {}).get("wrapper_or_binding")
            != 1
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
    _verify_repository_binding(
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
    seed_workspace = tempfile.TemporaryDirectory(prefix="etai-pair-seed-")
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
        name="Failure refunds and threshold provision",
        actor_id=HUMAN_ID,
        project_id="project.failure.refund.pair",
        created_at=T0,
        transaction_id="transaction.pair.refund.genesis",
        route_run_id="run.pair.refund.genesis",
    )
    layout = StoreLayout.at(seed_root)
    prefix_snapshot, core = _build_prefix(layout)
    packet, contract, audit_snapshot = _open_audit(layout, prefix_snapshot)
    if audit_snapshot.head != prefix_snapshot.head:
        raise RuntimeError("opening the audit unexpectedly changed canonical head")

    oracle_draft = _semantic_draft(_oracle_bundle(core))
    oracle_transaction = compile_framing_audit_semantic_draft(
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
    semantic_surface = compile_framing_audit_semantic_authoring_contract(contract)
    common_payload = _framing_payload_contract(contract)
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
    _write_new(private / "HARNESS_CASE.json", canonical_json_bytes(harness_case))
    seed_workspace.cleanup()
    _copy_new(REVIEW_ROOT / "frozen_evaluation_key.md", private / "FROZEN_EVALUATION_KEY.md")
    _copy_new(REVIEW_ROOT / "protocol.md", output_root / "PAIR_PROTOCOL.md")
    frozen_wheel = runtime / wheel_name
    _write_new(frozen_wheel, wheel_bytes)
    _copy_new(HARNESS_SOURCE, runtime / HARNESS_SOURCE.name)
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
    omitted_console_launchers = _normalize_target_install_record(runtime / "site")
    checkout_python_sha256 = _verify_installed_python_matches_checkout(
        runtime / "site"
    )
    installed_share = runtime / "site" / "share" / "econ-theorist"
    if not installed_share.is_dir():
        raise RuntimeError("the target-installed wheel lacks its share resources")
    runtime_facts = _verify_frozen_runtime(
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
        "files": _manifest_rows(runtime, runtime_paths),
    }
    runtime_manifest_bytes = canonical_json_bytes(runtime_manifest)
    _write_new(runtime / "RUNTIME_MANIFEST.json", runtime_manifest_bytes)
    runtime_manifest_sha256 = sha256_digest(runtime_manifest_bytes)

    common_files = {
        "CASE.md": (REVIEW_ROOT / "case.md").read_bytes(),
        "COMMON_WORK_PACKET.json": packet_bytes,
        "FRAMING_PAYLOAD_CONTRACT.json": canonical_json_bytes(common_payload),
    }
    surfaces = {
        "transaction": contract_bytes,
        "semantic": canonical_json_bytes(semantic_surface),
    }
    arm_roots = {"transaction": transaction_root, "semantic": semantic_root}
    arm_manifest_hashes: dict[str, str] = {}
    for surface, arm_root in arm_roots.items():
        for name, data in common_files.items():
            _write_new(arm_root / name, data)
        _write_new(arm_root / "SURFACE.json", surfaces[surface])
        _write_new(arm_root / "TASK_PROMPT.md", _task_prompt(surface))
        _write_new(arm_root / "VERIFY_MANIFEST.ps1", _verification_script())
        _write_new(
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
            "files": _manifest_rows(arm_root, visible),
        }
        manifest_bytes = canonical_json_bytes(manifest)
        _write_new(arm_root / "MANIFEST.json", manifest_bytes)
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
        _write_new(
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
development task; it is intentionally not repeated inside this package.  Run:

```powershell
./VERIFY_PRE_MANIFEST.ps1 -ExpectedManifestSha256 <EXTERNAL_PRE_MANIFEST_SHA256>
```

Transaction arm manifest SHA-256: `{arm_manifest_hashes['transaction']}`

Semantic arm manifest SHA-256: `{arm_manifest_hashes['semantic']}`

Only after `PRE_MANIFEST_OK`, create two new Codex tasks using `{output_root}`
as the workspace root and the same ordinary/medium model.  Open both before
reading either result.  Run them in this frozen order:

1. Paste `{launch_paths[order[0]]}` into a new task.
2. Paste `{launch_paths[order[1]]}` into a second new task.

Each launch prompt contains the exact arm root and external arm-manifest hash.
Do not let either task read the parent, sibling arm, repository, or
`private_evaluator`.  Do not comment on the first result until the second task
has also stopped.  Neither arm uses the bridge or canonical commit path.

After both reports exist, return their two report paths to the development
task.  High intelligence is not needed for generation; use it only for the
later blinded economics/reader adjudication.
"""
    _write_new(output_root / "OPERATOR_HANDOFF.md", operator_prompt.encode("utf-8"))
    _write_new(
        output_root / "VERIFY_PRE_MANIFEST.ps1", _pre_verification_script()
    )
    frozen_files = [
        Path("PAIR_PROTOCOL.md"),
        Path("OPERATOR_HANDOFF.md"),
        Path("VERIFY_PRE_MANIFEST.ps1"),
        Path("launch/arm-transaction.md"),
        Path("launch/arm-semantic.md"),
        Path("private_evaluator/HARNESS_CASE.json"),
        Path("private_evaluator/FROZEN_EVALUATION_KEY.md"),
        Path(f"runtime/{wheel_name}"),
        Path("runtime/RUNTIME_MANIFEST.json"),
        Path("runtime/run_framing_authoring_shadow.py"),
        Path("arm-transaction/MANIFEST.json"),
        Path("arm-semantic/MANIFEST.json"),
    ]
    pre_rows = _manifest_rows(output_root, frozen_files)
    oracle_bytes = canonical_json_bytes(oracle_transaction)
    pre_manifest = {
        "manifest_schema": "econ-theorist/framing-authoring-pair-pre-manifest/v1",
        "pair_id": PAIR_ID,
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
    _write_new(output_root / "PRE_MANIFEST.json", pre_manifest_bytes)
    _verify_repository_binding(
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
        print(f"pair preparation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
