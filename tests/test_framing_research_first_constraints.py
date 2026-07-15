"""Focused scientific regressions for mechanism-spine and consequence binding."""

from __future__ import annotations

import unittest

from pydantic import ValidationError
from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_framing_quality_models import bundle as legacy_bundle

from econ_theorist.framing_quality import (
    ActiveMarginWitness,
    AggregateInvarianceAssessment,
    ArchetypeTension,
    BenchmarkFramingAssessment,
    CausalChainStep,
    ChoiceConsequenceBinding,
    DistinctiveMechanismAssessment,
    EconomicForce,
    FramingObjectRef,
    FramingQualityBundle,
    HeldFixedObjectRef,
    PublicStateCondition,
    SelectionAssurance,
    render_framing_quality_memo,
)
from econ_theorist.framing_quality_validation import (
    FramingQualityValidationError,
    validate_research_first_framing_science,
)
from econ_theorist.models import EntityVersionRef
from econ_theorist.theory import (
    BenchmarkRecord,
    BenchmarkSet,
    PrimitiveEdge,
    PrimitiveGraph,
    PrimitiveNode,
    ResearchQuestion,
)


def ref(entity_id: str) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=1)


def obj(
    object_id: str,
    label: str,
    semantic_level: str,
    node_id: str,
) -> FramingObjectRef:
    return FramingObjectRef(
        object_id=object_id,
        label=label,
        semantic_level=semantic_level,
        primitive_node_id=node_id,
    )


def fixed(
    object_id: str,
    label: str,
    node_id: str,
) -> HeldFixedObjectRef:
    return HeldFixedObjectRef(
        object_id=object_id,
        label=label,
        semantic_level="primitive",
        primitive_node_id=node_id,
        fixing_level="payoff_ledger",
    )


def state(node_id: str, relation: str) -> PublicStateCondition:
    return PublicStateCondition(node_id=node_id, relation=relation)


def witness(
    decision_node_id: str,
    payoff_node_id: str,
    *,
    edge_ids: tuple[str, ...],
    consequence_node_id: str,
    transition_kind: str,
    state_condition: PublicStateCondition,
) -> ActiveMarginWitness:
    return ActiveMarginWitness(
        decision_node_id=decision_node_id,
        payoff_node_ids=(payoff_node_id,),
        concrete_state="The exact public-state class recorded in the consequence binding.",
        decision_maker="The optimizing agent",
        focal_action="Take the action that realizes the stated transition",
        alternative_action="Take the best feasible action that avoids that transition",
        focal_payoff="u_f including the common continuation convention",
        alternative_payoff="u_a including the common continuation convention",
        feasibility_basis="Both actions are feasible at the same state and timing.",
        best_response_inequality="u_f >= u_a",
        activity_status="active",
        status_basis="A nonempty primitive region crosses the stated payoff threshold.",
        kill_condition="the complete deviation envelope strictly dominates u_f.",
        consequence_binding=ChoiceConsequenceBinding(
            consequence_node_id=consequence_node_id,
            transition_kind=transition_kind,
            causal_edge_ids=edge_ids,
            public_state_conditions=(state_condition,),
            focal_consequence="The focal action realizes the claimed consequence.",
            alternative_consequence="The alternative leaves that consequence unrealized.",
            feasibility_basis="The edge path and public state make both consequences feasible.",
        ),
    )


class ResearchFirstFramingConstraintTests(unittest.TestCase):
    def _question(self) -> ResearchQuestion:
        return ResearchQuestion(
            phenomenon="Certification cost changes a consumable public stock.",
            object_to_explain="Whether stock depletion changes buyer search.",
            unresolved_delta="The stock channel must differ from its flow contrast.",
            importance="The distinction changes certification and search policy.",
            kill_condition="Kill the channel when the exact stock spine is absent.",
            proposed_scope="Two sellers, one buyer, and a public stock state.",
            candidate_archetypes=("mechanism_explanation",),
            prohibited_claims=("The framing audit proves an equilibrium theorem.",),
        )

    def _benchmarks(self) -> BenchmarkSet:
        records = tuple(
            BenchmarkRecord(
                benchmark_id=benchmark_id,
                label=label,
                exact_primitives=("The named certificate transition is exact.",),
                timing=("Issue", "Trade", "Transition"),
                solution_concept="A unique stationary equilibrium in the test region.",
                prediction="Trace the exact path without imposing its sign.",
                unresolved_delta="Whether the stock transition is distinctive.",
            )
            for benchmark_id, label in (
                ("benchmark.stock", "Consumable stock"),
                ("benchmark.flow", "Flow certificate"),
            )
        )
        return BenchmarkSet(
            question_ref=ref("question.stock"),
            benchmarks=records,
            exact_question_delta="Compare the exact stock and flow mechanism spines.",
        )

    def _graph(self) -> PrimitiveGraph:
        node_specs = (
            ("node.cost", "perturbation", "Certification cost"),
            ("node.issue", "choice", "Seller issuance"),
            ("node.trade", "choice", "Buyer trade choice"),
            ("node.stock_transition", "institution", "Mechanical stock transition"),
            ("node.stock", "institution", "Public certificate stock"),
            ("node.pool", "interaction", "Uncertified pool"),
            ("node.outcome", "outcome", "Buyer search outcome"),
            ("node.seller_payoff", "preference_technology", "Seller payoff"),
            ("node.buyer_payoff", "preference_technology", "Buyer payoff"),
        )
        edges = (
            ("edge.cost.issue", "node.cost", "node.issue"),
            ("edge.issue.trade", "node.issue", "node.trade"),
            ("edge.trade.stock", "node.trade", "node.stock"),
            ("edge.stock.outcome", "node.stock", "node.outcome"),
            ("edge.issue.pool", "node.issue", "node.pool"),
            ("edge.pool.outcome", "node.pool", "node.outcome"),
            ("edge.issue.transition", "node.issue", "node.stock_transition"),
            ("edge.transition.stock", "node.stock_transition", "node.stock"),
            ("edge.seller.issue", "node.seller_payoff", "node.issue"),
            ("edge.buyer.trade", "node.buyer_payoff", "node.trade"),
        )
        return PrimitiveGraph(
            question_ref=ref("question.stock"),
            benchmark_set_ref=ref("benchmarks.stock"),
            nodes=tuple(
                PrimitiveNode(
                    node_id=node_id,
                    kind=kind,
                    label=label,
                    economic_meaning=f"Exact economic role of {label}.",
                    status="primitive" if kind != "outcome" else "derived",
                )
                for node_id, kind, label in node_specs
            ),
            edges=tuple(
                PrimitiveEdge(
                    edge_id=edge_id,
                    source_node_id=source,
                    target_node_id=target,
                    economic_meaning=f"{source} changes {target}.",
                )
                for edge_id, source, target in edges
            ),
        )

    def _assessment(
        self,
        benchmark_id: str,
        *,
        path: tuple[str, ...],
        reoptimizing_nodes: tuple[str, ...],
        distinctive: DistinctiveMechanismAssessment,
    ) -> BenchmarkFramingAssessment:
        suffix = benchmark_id.rsplit(".", 1)[-1]
        return BenchmarkFramingAssessment(
            benchmark_id=benchmark_id,
            changed=(obj(f"changed.{suffix}", "Certification cost", "primitive", "node.cost"),),
            held_fixed=(fixed(f"fixed.payoff.{suffix}", "Payoff ledger", "node.buyer_payoff"),),
            reoptimizing=tuple(
                obj(
                    f"choice.{suffix}.{index}",
                    f"Choice {node_id}",
                    "behavioral_response",
                    node_id,
                )
                for index, node_id in enumerate(reoptimizing_nodes)
            ),
            still_endogenous=(
                obj(
                    f"endogenous.{suffix}",
                    "Seller issuance",
                    "choice",
                    "node.issue",
                ),
            ),
            targets=(obj(f"target.{suffix}", "Search outcome", "outcome", "node.outcome"),),
            channel_kind="active_response",
            channel_path=path,
            channel_summary="The exact path is the asserted mechanism spine.",
            aggregate_invariance=AggregateInvarianceAssessment(
                aggregate_object="Buyer search outcome",
                pointwise_policy_fixed=True,
                weighting_distribution_status="fixed",
                claims_aggregate_fixed=True,
                basis="The test conditions on one fixed public-state distribution.",
                implication_for_attribution="State reweighting cannot mimic the spine.",
            ),
            selection_assurance=SelectionAssurance(
                status="unique_equilibrium",
                selection_rule="Use the unique equilibrium in the stated region.",
                basis="The test fixture assumes uniqueness only for spine validation.",
                implication_for_attribution="No selector jump drives the comparison.",
            ),
            attribution_strength="clean",
            attribution_basis="The focal and contrast paths are structurally explicit.",
            distinctive_mechanism=distinctive,
        )

    @staticmethod
    def _no_claim() -> DistinctiveMechanismAssessment:
        return DistinctiveMechanismAssessment(
            claim_kind="not_claimed",
            mechanism_label="No distinctive mechanism asserted in the contrast row",
            basis="This row supplies only the comparison boundary.",
        )

    def _choice_claim(self) -> DistinctiveMechanismAssessment:
        return DistinctiveMechanismAssessment(
            claim_kind="choice_mediated",
            mechanism_label="Buyer-controlled certificate depletion",
            contrast_benchmark_id="benchmark.flow",
            distinctive_node_ids=("node.trade", "node.stock"),
            distinctive_edge_ids=("edge.trade.stock",),
            consequence_node_id="node.stock",
            transition_kind="decrease",
            required_public_state_conditions=(state("node.stock", "positive"),),
            basis="The buyer action must reduce a positive public stock.",
        )

    def _mechanical_claim(self) -> DistinctiveMechanismAssessment:
        return DistinctiveMechanismAssessment(
            claim_kind="mechanical_transition",
            mechanism_label="Automatic certificate depletion",
            contrast_benchmark_id="benchmark.flow",
            distinctive_node_ids=("node.stock_transition", "node.stock"),
            distinctive_edge_ids=("edge.transition.stock",),
            consequence_node_id="node.stock",
            transition_kind="decrease",
            required_public_state_conditions=(state("node.stock", "positive"),),
            basis="An institutional transition reduces positive stock without a buyer choice.",
        )

    def _choice_bundle(
        self,
        *,
        stock_path: tuple[str, ...],
        buyer_state: PublicStateCondition,
    ) -> FramingQualityBundle:
        seller = witness(
            "node.issue",
            "node.seller_payoff",
            edge_ids=("edge.issue.trade",),
            consequence_node_id="node.trade",
            transition_kind="switch",
            state_condition=state("node.stock", "zero"),
        )
        buyer = witness(
            "node.trade",
            "node.buyer_payoff",
            edge_ids=("edge.trade.stock",),
            consequence_node_id="node.stock",
            transition_kind="decrease",
            state_condition=buyer_state,
        )
        stock = self._assessment(
            "benchmark.stock",
            path=stock_path,
            reoptimizing_nodes=("node.issue", "node.trade"),
            distinctive=self._choice_claim(),
        )
        flow = self._assessment(
            "benchmark.flow",
            path=("node.cost", "node.issue", "node.pool", "node.outcome"),
            reoptimizing_nodes=("node.issue",),
            distinctive=self._no_claim(),
        )
        base = legacy_bundle()
        return FramingQualityBundle.model_validate(
            {
                **base.model_dump(mode="python"),
                "research_question_ref": ref("question.stock"),
                "benchmark_set_ref": ref("benchmarks.stock"),
                "primitive_graph_ref": ref("primitives.stock"),
                "source_g1_dossier_ref": ref("dossier.stock"),
                "tension": ArchetypeTension(
                    result_archetype="mechanism_explanation",
                    tension_kind="causal_channel",
                    conventional_prediction="Cheaper certification raises the visible stock.",
                    economic_puzzle="Buyer-controlled depletion may change search.",
                    resolution_target="Trace the exact stock consequence of the buyer action.",
                ),
                "forces": (
                    EconomicForce(
                        force_id="force.issue",
                        label="Issuance response",
                        role="baseline_force",
                        operative_margin="Seller issuance",
                        direction="changes_composition",
                        economic_logic="Cost changes the seller issuance threshold.",
                        active_when="The seller payoff difference crosses zero.",
                        source_node_id="node.cost",
                        margin_node_id="node.issue",
                        target_node_id="node.outcome",
                    ),
                    EconomicForce(
                        force_id="force.depletion",
                        label="Buyer depletion response",
                        role="equilibrium_feedback",
                        operative_margin="Buyer trade choice",
                        direction="changes_composition",
                        economic_logic="The chosen seller determines the remaining stock.",
                        active_when="The buyer payoff envelope supports both actions.",
                        source_node_id="node.issue",
                        margin_node_id="node.trade",
                        target_node_id="node.outcome",
                    ),
                ),
                "causal_chain": (
                    CausalChainStep(
                        step_number=1,
                        force_ids=("force.issue",),
                        cause="Certification cost moves the issuance payoff gap.",
                        endogenous_response="The seller changes issuance.",
                        consequence="The buyer faces a different trade opportunity.",
                        source_node_id="node.cost",
                        target_node_id="node.issue",
                        active_margin_witness=seller,
                    ),
                    CausalChainStep(
                        step_number=2,
                        force_ids=("force.depletion",),
                        cause="Issuance changes the buyer's feasible trade set.",
                        endogenous_response="The buyer chooses whether to deplete stock.",
                        consequence="The public stock falls after the focal action.",
                        source_node_id="node.issue",
                        target_node_id="node.trade",
                        active_margin_witness=buyer,
                    ),
                    CausalChainStep(
                        step_number=3,
                        force_ids=("force.issue", "force.depletion"),
                        cause="The buyer action changes the public stock.",
                        endogenous_response="The stock transition changes search states.",
                        consequence="The buyer search outcome changes.",
                        source_node_id="node.trade",
                        target_node_id="node.outcome",
                        active_margin_witness=buyer,
                    ),
                ),
                "benchmark_assessments": (stock, flow),
                "distinctive_mechanism_contribution_status": "claimed",
                "disclosed_gaps": (),
                "proposed_action": "ready_for_g1",
                "action_rationale": "The exact distinctive choice spine is active and closed.",
            }
        )

    def _mechanical_bundle(self) -> FramingQualityBundle:
        seller = witness(
            "node.issue",
            "node.seller_payoff",
            edge_ids=("edge.issue.transition",),
            consequence_node_id="node.stock_transition",
            transition_kind="switch",
            state_condition=state("node.stock", "positive"),
        )
        stock = self._assessment(
            "benchmark.stock",
            path=(
                "node.cost",
                "node.issue",
                "node.stock_transition",
                "node.stock",
                "node.outcome",
            ),
            reoptimizing_nodes=("node.issue",),
            distinctive=self._mechanical_claim(),
        )
        flow = self._assessment(
            "benchmark.flow",
            path=("node.cost", "node.issue", "node.pool", "node.outcome"),
            reoptimizing_nodes=("node.issue",),
            distinctive=self._no_claim(),
        )
        force = EconomicForce(
            force_id="force.stock",
            label="Issuance-to-stock force",
            role="baseline_force",
            operative_margin="Seller issuance",
            direction="changes_composition",
            economic_logic="Issuance feeds an automatic stock transition.",
            active_when="The seller issuance payoff gap crosses zero.",
            source_node_id="node.cost",
            margin_node_id="node.issue",
            target_node_id="node.outcome",
        )
        base = legacy_bundle()
        return FramingQualityBundle.model_validate(
            {
                **base.model_dump(mode="python"),
                "research_question_ref": ref("question.stock"),
                "benchmark_set_ref": ref("benchmarks.stock"),
                "primitive_graph_ref": ref("primitives.stock"),
                "source_g1_dossier_ref": ref("dossier.stock"),
                "tension": ArchetypeTension(
                    result_archetype="mechanism_explanation",
                    tension_kind="causal_channel",
                    conventional_prediction="Cheaper certification raises issuance.",
                    economic_puzzle="Automatic depletion changes stock occupancy.",
                    resolution_target="Trace the mechanical stock transition explicitly.",
                ),
                "forces": (force,),
                "causal_chain": (
                    CausalChainStep(
                        step_number=1,
                        force_ids=("force.stock",),
                        cause="Cost moves the seller issuance payoff gap.",
                        endogenous_response="The seller changes issuance.",
                        consequence="Issued certificates enter the stock process.",
                        source_node_id="node.cost",
                        target_node_id="node.issue",
                        active_margin_witness=seller,
                    ),
                    CausalChainStep(
                        step_number=2,
                        force_ids=("force.stock",),
                        cause="Issuance activates the institutional stock law.",
                        endogenous_response="The automatic transition depletes positive stock.",
                        consequence="The public stock changes without a buyer choice.",
                        source_node_id="node.issue",
                        target_node_id="node.stock_transition",
                    ),
                    CausalChainStep(
                        step_number=3,
                        force_ids=("force.stock",),
                        cause="The stock law changes stock occupancy.",
                        endogenous_response="Search states are reweighted.",
                        consequence="The buyer search outcome changes.",
                        source_node_id="node.stock_transition",
                        target_node_id="node.outcome",
                    ),
                ),
                "benchmark_assessments": (stock, flow),
                "distinctive_mechanism_contribution_status": "claimed",
                "disclosed_gaps": (),
                "proposed_action": "ready_for_g1",
                "action_rationale": "The distinctive mechanism is honestly mechanical.",
            }
        )

    def _validate(self, payload: FramingQualityBundle) -> None:
        validate_research_first_framing_science(
            payload,
            research_question=self._question(),
            benchmark_set=self._benchmarks(),
            primitive_graph=self._graph(),
        )

    def test_archived_like_stock_and_flow_same_path_is_rejected(self) -> None:
        same_path = ("node.cost", "node.issue", "node.pool", "node.outcome")
        payload = self._choice_bundle(
            stock_path=same_path,
            buyer_state=state("node.stock", "positive"),
        )
        with self.assertRaisesRegex(
            FramingQualityValidationError, "distinctive_mechanism_same_spine"
        ):
            self._validate(payload)

    def test_no_certificate_state_cannot_witness_depletion(self) -> None:
        with self.assertRaisesRegex(
            ValidationError, "decreasing transition cannot start from a zero"
        ):
            witness(
                "node.trade",
                "node.buyer_payoff",
                edge_ids=("edge.trade.stock",),
                consequence_node_id="node.stock",
                transition_kind="decrease",
                state_condition=state("node.stock", "zero"),
            )

    def test_positive_stock_buyer_tradeoff_can_pass(self) -> None:
        payload = self._choice_bundle(
            stock_path=(
                "node.cost",
                "node.issue",
                "node.trade",
                "node.stock",
                "node.outcome",
            ),
            buyer_state=state("node.stock", "positive"),
        )
        self._validate(payload)

    def test_shared_mechanism_benchmarks_can_honestly_disclaim_distinctiveness(self) -> None:
        payload = self._choice_bundle(
            stock_path=(
                "node.cost",
                "node.issue",
                "node.trade",
                "node.stock",
                "node.outcome",
            ),
            buyer_state=state("node.stock", "positive"),
        )
        payload = payload.model_copy(
            update={
                "benchmark_assessments": tuple(
                    assessment.model_copy(
                        update={"distinctive_mechanism": self._no_claim()}
                    )
                    for assessment in payload.benchmark_assessments
                ),
                "distinctive_mechanism_contribution_status": "not_claimed",
            }
        )
        self._validate(payload)

    def test_v7_requires_explicit_paper_level_distinctiveness_status(self) -> None:
        payload = self._choice_bundle(
            stock_path=(
                "node.cost",
                "node.issue",
                "node.trade",
                "node.stock",
                "node.outcome",
            ),
            buyer_state=state("node.stock", "positive"),
        ).model_copy(update={"distinctive_mechanism_contribution_status": None})
        with self.assertRaisesRegex(
            FramingQualityValidationError,
            "distinctive_mechanism_contribution_missing",
        ):
            self._validate(payload)

    def test_choice_claim_requires_the_exact_public_state_class(self) -> None:
        payload = self._choice_bundle(
            stock_path=(
                "node.cost",
                "node.issue",
                "node.trade",
                "node.stock",
                "node.outcome",
            ),
            buyer_state=state("node.stock", "positive"),
        )
        updated_steps = []
        for step in payload.causal_chain:
            margin = step.active_margin_witness
            if margin is None or margin.decision_node_id != "node.trade":
                updated_steps.append(step)
                continue
            assert margin.consequence_binding is not None
            binding = margin.consequence_binding.model_copy(
                update={
                    "public_state_conditions": (
                        *margin.consequence_binding.public_state_conditions,
                        state("node.stock_transition", "positive"),
                    )
                }
            )
            updated_steps.append(
                step.model_copy(
                    update={
                        "active_margin_witness": margin.model_copy(
                            update={"consequence_binding": binding}
                        )
                    }
                )
            )
        payload = payload.model_copy(update={"causal_chain": tuple(updated_steps)})
        with self.assertRaisesRegex(
            FramingQualityValidationError,
            "choice_consequence_binding_mismatch",
        ):
            self._validate(payload)

    def test_typed_public_state_can_condition_the_mechanism_off_spine(self) -> None:
        off_spine_state = state("node.stock_transition", "positive")
        payload = self._choice_bundle(
            stock_path=(
                "node.cost",
                "node.issue",
                "node.trade",
                "node.stock",
                "node.outcome",
            ),
            buyer_state=off_spine_state,
        )
        focal, contrast = payload.benchmark_assessments
        assert focal.distinctive_mechanism is not None
        focal = focal.model_copy(
            update={
                "distinctive_mechanism": focal.distinctive_mechanism.model_copy(
                    update={
                        "required_public_state_conditions": (off_spine_state,)
                    }
                )
            }
        )
        payload = payload.model_copy(
            update={"benchmark_assessments": (focal, contrast)}
        )
        self._validate(payload)

    def test_mechanical_edge_cannot_end_at_an_undeclared_choice(self) -> None:
        payload = self._mechanical_bundle()
        claim = DistinctiveMechanismAssessment(
            claim_kind="mechanical_transition",
            mechanism_label="A falsely mechanical institution-to-choice edge",
            contrast_benchmark_id="benchmark.flow",
            distinctive_node_ids=("node.stock_transition",),
            distinctive_edge_ids=("edge.transition.trade",),
            consequence_node_id="node.trade",
            transition_kind="switch",
            required_public_state_conditions=(
                state("node.stock_transition", "positive"),
            ),
            basis="This declaration must not hide the target choice node.",
        )
        focal, contrast = payload.benchmark_assessments
        focal = focal.model_copy(
            update={
                "channel_path": (
                    "node.cost",
                    "node.issue",
                    "node.stock_transition",
                    "node.trade",
                    "node.stock",
                    "node.outcome",
                ),
                "distinctive_mechanism": claim,
            }
        )
        payload = payload.model_copy(
            update={
                "benchmark_assessments": (focal, contrast),
                "causal_chain": tuple(
                    step.model_copy(
                        update={
                            "active_margin_witness": witness(
                                "node.trade",
                                "node.buyer_payoff",
                                edge_ids=("edge.trade.stock",),
                                consequence_node_id="node.stock",
                                transition_kind="decrease",
                                state_condition=state("node.stock", "positive"),
                            )
                        }
                    )
                    if step.step_number == 3
                    else step
                    for step in payload.causal_chain
                ),
            }
        )
        graph = self._graph()
        graph = graph.model_copy(
            update={
                "edges": (
                    *graph.edges,
                    PrimitiveEdge(
                        edge_id="edge.transition.trade",
                        source_node_id="node.stock_transition",
                        target_node_id="node.trade",
                        economic_meaning="The institutional state exposes a trade choice.",
                    ),
                )
            }
        )
        with self.assertRaisesRegex(
            FramingQualityValidationError,
            "distinctive_mechanism_mechanical_choice",
        ):
            validate_research_first_framing_science(
                payload,
                research_question=self._question(),
                benchmark_set=self._benchmarks(),
                primitive_graph=graph,
            )

    def test_mechanical_claim_cannot_condition_on_a_choice_node(self) -> None:
        payload = self._mechanical_bundle()
        focal, contrast = payload.benchmark_assessments
        assert focal.distinctive_mechanism is not None
        focal = focal.model_copy(
            update={
                "distinctive_mechanism": focal.distinctive_mechanism.model_copy(
                    update={
                        "required_public_state_conditions": (
                            state("node.issue", "positive"),
                        )
                    }
                )
            }
        )
        payload = payload.model_copy(
            update={"benchmark_assessments": (focal, contrast)}
        )
        with self.assertRaisesRegex(
            FramingQualityValidationError,
            "distinctive_mechanism_state",
        ):
            self._validate(payload)

    def test_explicit_mechanical_depletion_spine_can_pass(self) -> None:
        self._validate(self._mechanical_bundle())

    def test_economist_memo_exposes_exact_mechanism_and_consequence_checks(self) -> None:
        payload = self._choice_bundle(
            stock_path=(
                "node.cost",
                "node.issue",
                "node.trade",
                "node.stock",
                "node.outcome",
            ),
            buyer_state=state("node.stock", "positive"),
        )
        markdown = render_framing_quality_memo(
            payload, self._benchmarks(), self._graph()
        )
        self.assertIn("## Mechanism distinction", markdown)
        self.assertIn("Buyer-controlled certificate depletion", markdown)
        self.assertIn("Buyer trade choice -> Public certificate stock", markdown)
        self.assertIn("Public certificate stock positive", markdown)
        self.assertIn("**Consequence check.**", markdown)
        self.assertNotIn("node.trade", markdown)
        self.assertNotIn("edge.trade.stock", markdown)


if __name__ == "__main__":
    unittest.main()
