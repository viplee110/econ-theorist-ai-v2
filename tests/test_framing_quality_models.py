"""Executable contracts for the independent framing-quality preflight."""

from __future__ import annotations

import unittest

from pydantic import ValidationError
from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src on sys.path

from econ_theorist.codec import canonical_json_bytes
from econ_theorist.framing_quality import (
    FRAMING_QUALITY_JSON_SCHEMA_REGISTRY,
    FRAMING_QUALITY_PAYLOAD_MODELS,
    FRAMING_QUALITY_PAYLOAD_OWNER_FACETS,
    ActiveMarginWitness,
    AggregateInvarianceAssessment,
    ArchetypeTension,
    BenchmarkFramingAssessment,
    CausalChainStep,
    DisclosedFramingGap,
    EconomicForce,
    EconomistMemo,
    FramingObjectRef,
    FramingQualityBundle,
    FramingRepairTargetRef,
    HeldFixedObjectRef,
    IllustrativeMinimalExample,
    SelectionAssurance,
    framing_quality_schema_id,
    is_packed_framing_quality_entity,
    pack_framing_quality_payload,
    parse_framing_quality_payload,
    render_framing_quality_memo,
)
from econ_theorist.models import EntityVersion, EntityVersionRef, ScientificStatus
from econ_theorist.theory import BenchmarkRecord, BenchmarkSet


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def oref(
    object_id: str,
    label: str,
    semantic_level: str,
    primitive_node_id: str | None,
) -> FramingObjectRef:
    return FramingObjectRef(
        object_id=object_id,
        label=label,
        semantic_level=semantic_level,
        primitive_node_id=primitive_node_id,
    )


def href(
    object_id: str,
    label: str,
    semantic_level: str,
    primitive_node_id: str | None,
    fixing_level: str,
) -> HeldFixedObjectRef:
    return HeldFixedObjectRef(
        object_id=object_id,
        label=label,
        semantic_level=semantic_level,
        primitive_node_id=primitive_node_id,
        fixing_level=fixing_level,
    )


def margin_witness(
    decision_node_id: str,
    payoff_node_id: str,
    *,
    focal_action: str,
    alternative_action: str,
) -> ActiveMarginWitness:
    return ActiveMarginWitness(
        decision_node_id=decision_node_id,
        payoff_node_ids=(payoff_node_id,),
        concrete_state="The two actions are feasible at the same public state and beliefs",
        decision_maker="The optimizing agent",
        focal_action=focal_action,
        alternative_action=alternative_action,
        focal_payoff="u_f including the relevant continuation value",
        alternative_payoff="u_a including the same continuation convention",
        feasibility_basis="The timing and action set admit both actions before uncertainty resolves.",
        best_response_inequality="u_f >= u_a",
        activity_status="active",
        status_basis="The stated admissible region contains values with u_f >= u_a.",
        kill_condition="the exact payoff ledger implies u_f < u_a throughout the admissible region.",
    )


def benchmarks() -> BenchmarkSet:
    return BenchmarkSet(
        question_ref=eref("question.certificates"),
        benchmarks=(
            BenchmarkRecord(
                benchmark_id="benchmark.no_certificate",
                label="No certification",
                exact_primitives=("Sellers choose quality before buyers inspect.",),
                timing=("Quality", "Inspection", "Purchase"),
                solution_concept="Symmetric stationary equilibrium",
                prediction="Buyers inspect whenever the expected gain exceeds cost.",
                unresolved_delta="There is no public quality signal.",
            ),
            BenchmarkRecord(
                benchmark_id="benchmark.fixed_signal",
                label="Fixed public signal",
                exact_primitives=("A signal is assigned without seller response.",),
                timing=("Signal", "Inspection", "Purchase"),
                solution_concept="The same selected stationary equilibrium",
                prediction="The signal redirects inspection across sellers.",
                unresolved_delta="Seller quality remains frozen.",
            ),
        ),
        exact_question_delta=(
            "Allow sellers to reoptimize quality after certification becomes available."
        ),
    )


def assessment(
    benchmark_id: str,
    *,
    changed: str,
    reoptimizing: str,
) -> BenchmarkFramingAssessment:
    return BenchmarkFramingAssessment(
        benchmark_id=benchmark_id,
        changed=(
            oref(
                f"object.changed.{benchmark_id.rsplit('.', 1)[-1]}",
                changed,
                "primitive",
                "node.certificate",
            ),
        ),
        held_fixed=(
            href(
                "object.search_cost",
                "Buyer search cost and preferences",
                "primitive",
                "node.search_cost",
                "primitive",
            ),
        ),
        reoptimizing=(
            oref(
                f"object.reoptimizing.{benchmark_id.rsplit('.', 1)[-1]}",
                reoptimizing,
                "behavioral_response",
                "node.quality_choice",
            ),
        ),
        still_endogenous=(
            oref(
                f"object.endogenous.{benchmark_id.rsplit('.', 1)[-1]}",
                "Inspection and purchase choices",
                "choice",
                "node.inspection",
            ),
        ),
        targets=(
            oref(
                "object.match_quality",
                "Realized match quality",
                "aggregate",
                "node.match_quality",
            ),
        ),
        channel_kind="active_response",
        channel_path=(
            "node.certificate",
            "node.inspection",
            "node.quality_choice",
            "node.match_quality",
        ),
        channel_summary=(
            "Certification changes seller quality incentives and buyer inspection."
        ),
        aggregate_invariance=AggregateInvarianceAssessment(
            aggregate_object="The stationary distribution of buyer states",
            pointwise_policy_fixed=True,
            weighting_distribution_status="fixed",
            claims_aggregate_fixed=True,
            basis="The comparison conditions on the same stationary state weights.",
            implication_for_attribution="Composition cannot explain the target change.",
        ),
        selection_assurance=SelectionAssurance(
            status="unique_equilibrium",
            selection_rule="The equilibrium is unique in the stated parameter region.",
            basis="The best-response map is a contraction in that region.",
            implication_for_attribution="No selected-branch jump drives the comparison.",
        ),
        attribution_strength="clean",
        attribution_basis="Only the stated institutional margin differs.",
    )


def bundle() -> FramingQualityBundle:
    return FramingQualityBundle(
        research_question_ref=eref("question.certificates"),
        benchmark_set_ref=eref("benchmarks.certificates"),
        primitive_graph_ref=eref("primitives.certificates"),
        source_g1_dossier_ref=eref("dossier.g1.certificates"),
        tension=ArchetypeTension(
            result_archetype="mechanism_explanation",
            tension_kind="force_conflict",
            conventional_prediction="Better certification should improve matching.",
            countervailing_logic=(
                "Certification can weaken inspection and alter sellers' quality incentives."
            ),
            economic_puzzle=(
                "A more informative institution can reduce realized match quality."
            ),
            resolution_target=(
                "Identify when the incentive response outweighs direct information."
            ),
        ),
        forces=(
            EconomicForce(
                force_id="force.information",
                label="Direct information",
                role="baseline_force",
                operative_margin="Buyer targeting",
                direction="raises_target",
                economic_logic="A certificate directs buyers toward likely high quality.",
                active_when="Buyers condition inspection on the signal.",
                source_node_id="node.certificate",
                margin_node_id="node.inspection",
                target_node_id="node.match_quality",
            ),
            EconomicForce(
                force_id="force.incentives",
                label="Seller incentive response",
                role="countervailing_force",
                operative_margin="Seller quality investment",
                direction="lowers_target",
                economic_logic="Reduced inspection weakens the return to hidden quality.",
                active_when="Seller quality responds after certification is introduced.",
                source_node_id="node.certificate",
                margin_node_id="node.quality_choice",
                target_node_id="node.match_quality",
            ),
        ),
        causal_chain=(
            CausalChainStep(
                step_number=1,
                force_ids=("force.information",),
                cause="Certification redirects buyer attention.",
                endogenous_response="Buyers inspect certified sellers less intensively.",
                consequence="The private return to hidden quality changes.",
                source_node_id="node.certificate",
                target_node_id="node.inspection",
                active_margin_witness=margin_witness(
                    "node.inspection",
                    "node.buyer_payoff",
                    focal_action="Inspect",
                    alternative_action="Buy without inspection",
                ),
            ),
            CausalChainStep(
                step_number=2,
                force_ids=("force.incentives",),
                cause="The return to hidden quality falls.",
                endogenous_response="Sellers reduce quality investment.",
                consequence="The quality distribution deteriorates.",
                source_node_id="node.inspection",
                target_node_id="node.quality_choice",
                active_margin_witness=margin_witness(
                    "node.quality_choice",
                    "node.seller_payoff",
                    focal_action="Invest in hidden quality",
                    alternative_action="Do not invest",
                ),
            ),
            CausalChainStep(
                step_number=3,
                force_ids=("force.information", "force.incentives"),
                cause="Direct targeting and incentive deterioration act together.",
                endogenous_response="Buyers reallocate search across changed offers.",
                consequence="Match quality falls when the incentive force dominates.",
                source_node_id="node.quality_choice",
                target_node_id="node.match_quality",
                active_margin_witness=margin_witness(
                    "node.quality_choice",
                    "node.seller_payoff",
                    focal_action="Invest in hidden quality",
                    alternative_action="Do not invest",
                ),
            ),
        ),
        minimal_example=IllustrativeMinimalExample(
            title="Two sellers and one inspection opportunity",
            setup="One seller receives a certificate before the buyer chooses inspection.",
            moving_primitive="certificate precision",
            held_fixed=("inspection cost", "buyer preferences"),
            endogenous_responses=("seller quality", "buyer inspection"),
            predicted_pattern="Quality first rises and then falls with precision.",
            economic_intuition=(
                "The certificate helps targeting but eventually crowds out quality incentives."
            ),
            limitation="The example neither proves the general result nor establishes novelty.",
            cannot_establish=("the theorem", "robustness", "literature novelty"),
        ),
        economist_memo=EconomistMemo(
            headline="When quality certificates weaken quality",
            opening_question=(
                "Can a more informative certificate make buyers worse matched?"
            ),
            benchmark_message=(
                "Standard comparisons hold seller quality fixed and retain only targeting."
            ),
            tension_message=(
                "Targeting improves, but the incentive to supply hidden quality weakens."
            ),
            mechanism_message=(
                "The same signal changes inspection and therefore seller investment."
            ),
            result_preview=(
                "Match quality falls when the induced quality response dominates targeting."
            ),
            contribution_message=(
                "The comparison separates information from the supply response it induces."
            ),
            scope_condition="The claim applies where seller quality is responsive.",
            reader_takeaway=(
                "Information design must account for endogenous product quality."
            ),
        ),
        benchmark_assessments=(
            assessment(
                "benchmark.no_certificate",
                changed="Certification becomes available",
                reoptimizing="Sellers and buyers",
            ),
            assessment(
                "benchmark.fixed_signal",
                changed="Seller quality is allowed to respond",
                reoptimizing="Sellers",
            ),
        ),
        disclosed_gaps=(
            DisclosedFramingGap(
                gap_id="gap.global_robustness",
                category="scope",
                description="The contraction argument covers only an interior region.",
                repair_target_refs=(
                    FramingRepairTargetRef(
                        entity_type="PrimitiveGraph",
                        entity_ref=eref("primitives.certificates"),
                    ),
                ),
                consequence="The comparison is not yet global.",
                resolution_needed="Map the boundary and test multiple equilibria.",
            ),
        ),
        proposed_action="revise_framing",
        action_rationale="Clarify the boundary before promoting the mechanism.",
    )


class FramingQualityStrictnessTests(unittest.TestCase):
    def test_contract_semantic_and_fixing_levels_are_parseable(self) -> None:
        levels = (
            "choice",
            "conditional_distribution",
            "transition_kernel",
            "stationary_distribution",
            "payoff_ledger",
            "equilibrium_correspondence",
        )
        for level in levels:
            with self.subTest(level=level):
                semantic = FramingObjectRef(
                    object_id=f"object.{level}",
                    label=f"Economic object at {level}",
                    semantic_level=level,
                    primitive_node_id=None,
                )
                fixed = HeldFixedObjectRef(
                    object_id=f"fixed.{level}",
                    label=f"Fixed object at {level}",
                    semantic_level=level,
                    primitive_node_id=None,
                    fixing_level=level,
                )
                self.assertEqual(semantic.semantic_level, level)
                self.assertEqual(fixed.fixing_level, level)

    def test_models_are_strict_frozen_and_extra_forbidden(self) -> None:
        original = bundle()
        with self.assertRaises(ValidationError):
            original.model_copy(update={"unknown": "not canonical"}).model_validate(
                {**original.model_dump(mode="python"), "unknown": "not canonical"}
            )
        with self.assertRaises(ValidationError):
            FramingQualityBundle.model_validate(
                {**original.model_dump(mode="python"), "forces": list(original.forces)}
            )
        with self.assertRaises(ValidationError):
            original.proposed_action = "ready_for_g1"  # type: ignore[misc]

    def test_revise_framing_requires_an_exact_typed_bundle_target(self) -> None:
        original = bundle()
        gap = original.disclosed_gaps[0]
        with self.assertRaisesRegex(ValidationError, "at least one exact typed"):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "disclosed_gaps": (
                        gap.model_copy(update={"repair_target_refs": ()}),
                    ),
                }
            )
        wrong_target = gap.repair_target_refs[0].model_copy(
            update={"entity_ref": eref("primitives.foreign")}
        )
        with self.assertRaisesRegex(ValidationError, "exact typed bundle input"):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "disclosed_gaps": (
                        gap.model_copy(
                            update={"repair_target_refs": (wrong_target,)}
                        ),
                    ),
                }
            )

    def test_tension_kind_is_archetype_sensitive(self) -> None:
        causal = ArchetypeTension(
            result_archetype="mechanism_explanation",
            tension_kind="causal_channel",
            conventional_prediction="The benchmark omits an endogenous response.",
            economic_puzzle="The missing response changes the predicted outcome.",
            resolution_target="Trace the active response channel.",
        )
        self.assertIsNone(causal.countervailing_logic)
        with self.assertRaisesRegex(ValidationError, "exact allowed kind"):
            ArchetypeTension(
                result_archetype="comparative_statics_threshold",
                tension_kind="force_conflict",
                conventional_prediction="The comparative static is positive.",
                countervailing_logic="An equilibrium response changes the sign.",
                economic_puzzle="The sign reverses across an endogenous threshold.",
                resolution_target="Locate the threshold and explain both forces.",
            )
        with self.assertRaisesRegex(ValidationError, "countervailing_logic"):
            ArchetypeTension(
                result_archetype="mechanism_explanation",
                tension_kind="force_conflict",
                conventional_prediction="The direct effect is positive.",
                economic_puzzle="An opposing response can reverse it.",
                resolution_target="Compare the two forces.",
            )

    def test_chain_has_exactly_three_ordered_steps_and_known_forces(self) -> None:
        original = bundle()
        with self.assertRaises(ValidationError):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "causal_chain": original.causal_chain[:2],
                }
            )
        bad_steps = (
            original.causal_chain[1],
            original.causal_chain[0],
            original.causal_chain[2],
        )
        with self.assertRaisesRegex(ValidationError, "ordered steps"):
            FramingQualityBundle.model_validate(
                {**original.model_dump(mode="python"), "causal_chain": bad_steps}
            )

    def test_every_force_and_chain_step_is_nonzero_and_used(self) -> None:
        original = bundle()
        baseline_only = tuple(
            step.model_copy(update={"force_ids": ("force.information",)})
            for step in original.causal_chain
        )
        with self.assertRaisesRegex(ValidationError, "every declared economic force"):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "causal_chain": baseline_only,
                }
            )

        zero_force = original.forces[0].model_copy(
            update={
                "source_node_id": "node.match_quality",
                "margin_node_id": "node.match_quality",
                "target_node_id": "node.match_quality",
            }
        )
        with self.assertRaisesRegex(ValidationError, "nonzero source-to-target"):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "forces": (zero_force, original.forces[1]),
                }
            )

    def test_active_margin_witness_requires_distinct_actions_and_payoff_refs(self) -> None:
        original = bundle().causal_chain[0].active_margin_witness
        assert original is not None
        with self.assertRaisesRegex(ValidationError, "focal and alternative actions"):
            ActiveMarginWitness.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "alternative_action": original.focal_action,
                }
            )
        with self.assertRaisesRegex(ValidationError, "payoff node IDs"):
            ActiveMarginWitness.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "payoff_node_ids": (
                        original.payoff_node_ids[0],
                        original.payoff_node_ids[0],
                    ),
                }
            )

    def test_inactive_margin_requires_exact_causal_revision(self) -> None:
        original = bundle()
        first_witness = original.causal_chain[0].active_margin_witness
        assert first_witness is not None
        inactive_step = original.causal_chain[0].model_copy(
            update={
                "active_margin_witness": first_witness.model_copy(
                    update={
                        "activity_status": "inactive",
                        "status_basis": "The alternative strictly dominates throughout.",
                    }
                )
            }
        )
        inactive_steps = (inactive_step, *original.causal_chain[1:])
        with self.assertRaisesRegex(ValidationError, "inactive_mechanism_link"):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "causal_chain": inactive_steps,
                }
            )

        causal_gap = DisclosedFramingGap(
            gap_id="gap.inactive_margin",
            category="causal_attribution",
            description="A claimed choice margin is inactive under the payoff ledger.",
            repair_target_refs=(
                FramingRepairTargetRef(
                    entity_type="ResearchQuestion",
                    entity_ref=original.research_question_ref,
                ),
            ),
            consequence="The proposed mechanism chain is not an equilibrium path.",
            resolution_needed="Revise the payoff tradeoff or remove the inactive link.",
        )
        accepted = FramingQualityBundle.model_validate(
            {
                **original.model_dump(mode="python"),
                "causal_chain": inactive_steps,
                "disclosed_gaps": (*original.disclosed_gaps, causal_gap),
            }
        )
        self.assertEqual(
            accepted.causal_chain[0].active_margin_witness.activity_status,
            "inactive",
        )

    def test_unresolved_margin_cannot_be_ready_for_g1(self) -> None:
        original = bundle()
        first_witness = original.causal_chain[0].active_margin_witness
        assert first_witness is not None
        unresolved_step = original.causal_chain[0].model_copy(
            update={
                "active_margin_witness": first_witness.model_copy(
                    update={
                        "activity_status": "unresolved",
                        "status_basis": "The admissible best-response region is unknown.",
                    }
                )
            }
        )
        causal_gap = DisclosedFramingGap(
            gap_id="gap.unresolved_margin",
            category="causal_attribution",
            description="The payoff comparison has not established an active margin.",
            consequence="The mechanism may be a verbal rather than equilibrium path.",
            resolution_needed="Solve the best-response inequality before G1.",
        )
        with self.assertRaisesRegex(ValidationError, "cannot be promoted|mechanism_link"):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "causal_chain": (unresolved_step, *original.causal_chain[1:]),
                    "disclosed_gaps": (causal_gap,),
                    "proposed_action": "ready_for_g1",
                    "action_rationale": "Attempt readiness without an active margin.",
                }
            )

    def test_nonmechanism_chain_may_omit_payoff_witnesses(self) -> None:
        original = bundle()
        tension = original.tension.model_copy(
            update={
                "result_archetype": "concept_representation_foundation",
                "tension_kind": "conceptual_distinction_or_representation",
                "countervailing_logic": None,
            }
        )
        steps = tuple(
            step.model_copy(update={"active_margin_witness": None})
            for step in original.causal_chain
        )
        accepted = FramingQualityBundle.model_validate(
            {
                **original.model_dump(mode="python"),
                "tension": tension,
                "causal_chain": steps,
            }
        )
        self.assertTrue(
            all(step.active_margin_witness is None for step in accepted.causal_chain)
        )

    def test_ready_blocks_every_disclosed_gap_category(self) -> None:
        original = bundle()
        categories = (
            "benchmark_semantics",
            "aggregate_endogeneity",
            "equilibrium_selection",
            "reoptimization",
            "causal_attribution",
            "scope",
            "minimal_example",
            "other",
        )
        for category in categories:
            with self.subTest(category=category):
                gap = DisclosedFramingGap(
                    gap_id=f"gap.{category}",
                    category=category,
                    description="A material framing issue remains unresolved.",
                    consequence="The current framing can mislead the reader.",
                    resolution_needed="Resolve the issue before G1.",
                )
                with self.assertRaisesRegex(ValidationError, "cannot be promoted"):
                    FramingQualityBundle.model_validate(
                        {
                            **original.model_dump(mode="python"),
                            "disclosed_gaps": (gap,),
                            "proposed_action": "ready_for_g1",
                            "action_rationale": "Attempt readiness with a gap.",
                        }
                    )

    def test_known_endogenous_composition_and_qualified_attribution_can_be_ready(
        self,
    ) -> None:
        original = bundle()
        first = original.benchmark_assessments[0]
        aggregate = first.aggregate_invariance.model_copy(
            update={
                "pointwise_policy_fixed": False,
                "weighting_distribution_status": "endogenous",
                "claims_aggregate_fixed": False,
                "basis": "The policy changes the endogenous stationary composition.",
                "implication_for_attribution": (
                    "Composition is the traced mechanism, not an invariant."
                ),
            }
        )
        qualified = first.model_copy(
            update={
                "aggregate_invariance": aggregate,
                "attribution_strength": "qualified",
                "attribution_basis": (
                    "The active composition channel is identified on the stated region."
                ),
            }
        )
        ready = FramingQualityBundle.model_validate(
            {
                **original.model_dump(mode="python"),
                "benchmark_assessments": (
                    qualified,
                    original.benchmark_assessments[1],
                ),
                "disclosed_gaps": (),
                "proposed_action": "ready_for_g1",
                "action_rationale": "Known composition and scope are fully traced.",
            }
        )
        self.assertEqual(ready.proposed_action, "ready_for_g1")
        self.assertEqual(
            ready.benchmark_assessments[0].attribution_strength, "qualified"
        )

    def test_typed_endogenous_transition_can_supply_the_active_margin(self) -> None:
        original = bundle().benchmark_assessments[0]
        transition = original.still_endogenous[0].model_copy(
            update={"semantic_level": "transition_kernel"}
        )
        active = BenchmarkFramingAssessment.model_validate(
            {
                **original.model_dump(mode="python"),
                "reoptimizing": (),
                "still_endogenous": (transition,),
            }
        )
        self.assertEqual(active.reoptimizing, ())

    def test_causal_channel_does_not_require_an_invented_counterforce(self) -> None:
        original = bundle()
        force = original.forces[1].model_copy(update={"role": "equilibrium_feedback"})
        steps = tuple(
            step.model_copy(update={"force_ids": (force.force_id,)})
            for step in original.causal_chain
        )
        causal = FramingQualityBundle.model_validate(
            {
                **original.model_dump(mode="python"),
                "tension": ArchetypeTension(
                    result_archetype="mechanism_explanation",
                    tension_kind="causal_channel",
                    conventional_prediction="The benchmark freezes the response.",
                    economic_puzzle="Restoring the response changes the outcome.",
                    resolution_target="Trace the missing endogenous channel.",
                ),
                "forces": (force,),
                "causal_chain": steps,
                "disclosed_gaps": (),
                "proposed_action": "ready_for_g1",
                "action_rationale": "The one-direction active channel is traced.",
            }
        )
        self.assertEqual(causal.tension.tension_kind, "causal_channel")
        self.assertEqual(len(causal.forces), 1)

    def test_risky_benchmark_requires_linked_disclosed_gap(self) -> None:
        original = bundle()
        risky = original.benchmark_assessments[0].model_copy(
            update={
                "selection_assurance": original.benchmark_assessments[
                    0
                ].selection_assurance.model_copy(update={"status": "unresolved"}),
                "attribution_strength": "qualified",
            }
        )
        with self.assertRaisesRegex(ValidationError, "linked disclosed gap"):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "benchmark_assessments": (
                        risky,
                        original.benchmark_assessments[1],
                    ),
                }
            )

    def test_diagnostic_errors_are_machine_searchable(self) -> None:
        with self.assertRaisesRegex(
            ValidationError, "aggregate_invariance_unsupported"
        ):
            AggregateInvarianceAssessment(
                aggregate_object="Stationary welfare",
                pointwise_policy_fixed=True,
                weighting_distribution_status="endogenous",
                claims_aggregate_fixed=True,
                basis="Policies are fixed state by state but state weights can move.",
                implication_for_attribution="Aggregate welfare need not be fixed.",
            )

        original = bundle().benchmark_assessments[0]
        inactive = original.still_endogenous[0].model_copy(
            update={"semantic_level": "outcome"}
        )
        with self.assertRaisesRegex(ValidationError, "placebo_control"):
            BenchmarkFramingAssessment.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "reoptimizing": (),
                    "still_endogenous": (inactive,),
                }
            )
        boundary = BenchmarkFramingAssessment.model_validate(
            {
                **original.model_dump(mode="python"),
                "channel_kind": "boundary_or_mapping",
                "reoptimizing": (),
                "still_endogenous": (inactive,),
            }
        )
        self.assertEqual(boundary.reoptimizing, ())

        with self.assertRaisesRegex(
            ValidationError, "diagnostic_only_attribution_overclaim"
        ):
            BenchmarkFramingAssessment.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "channel_kind": "diagnostic_only",
                    "reoptimizing": (),
                }
            )
        with self.assertRaisesRegex(
            ValidationError, "selection_robustness_unsupported"
        ):
            BenchmarkFramingAssessment.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "selection_assurance": original.selection_assurance.model_copy(
                        update={"status": "selector_only"}
                    ),
                }
            )

    def test_opposing_forces_are_archetype_sensitive(self) -> None:
        original = bundle()
        changed_tension = original.tension.model_copy(
            update={
                "result_archetype": "robustness_invariance_equivalence",
                "tension_kind": "invariance_or_equivalence",
            }
        )
        single_force = original.forces[:1]
        single_force_steps = tuple(
            item.model_copy(update={"force_ids": (single_force[0].force_id,)})
            for item in original.causal_chain
        )
        accepted = FramingQualityBundle.model_validate(
            {
                **original.model_dump(mode="python"),
                "tension": changed_tension,
                "forces": single_force,
                "causal_chain": single_force_steps,
            }
        )
        self.assertEqual(len(accepted.forces), 1)

        same_direction = original.forces[1].model_copy(
            update={"direction": "raises_target"}
        )
        with self.assertRaisesRegex(ValidationError, "opposite directions"):
            FramingQualityBundle.model_validate(
                {
                    **original.model_dump(mode="python"),
                    "forces": (original.forces[0], same_direction),
                }
            )


class FramingQualityEnvelopeTests(unittest.TestCase):
    def test_independent_registry_owner_and_json_schema_are_complete(self) -> None:
        self.assertEqual(
            FRAMING_QUALITY_PAYLOAD_MODELS,
            {"FramingQualityBundle": FramingQualityBundle},
        )
        self.assertEqual(
            FRAMING_QUALITY_PAYLOAD_OWNER_FACETS,
            {"FramingQualityBundle": "economic_interpretation"},
        )
        schema_id = framing_quality_schema_id("FramingQualityBundle")
        self.assertEqual(set(FRAMING_QUALITY_JSON_SCHEMA_REGISTRY), {schema_id})
        self.assertEqual(
            FRAMING_QUALITY_JSON_SCHEMA_REGISTRY[schema_id]["title"],
            "FramingQualityBundle",
        )

    def test_pack_parse_round_trip_and_visible_opt_in(self) -> None:
        original = bundle()
        facets = pack_framing_quality_payload(original)
        self.assertEqual(facets.formal, {})
        self.assertEqual(facets.literature_novelty, {})
        self.assertEqual(facets.terminology_presentation, {})
        self.assertEqual(facets.authority, {})
        self.assertEqual(
            facets.economic_interpretation["schema"],
            framing_quality_schema_id("FramingQualityBundle"),
        )
        parsed = parse_framing_quality_payload("FramingQualityBundle", facets)
        self.assertEqual(parsed, original)
        self.assertEqual(
            canonical_json_bytes(pack_framing_quality_payload(parsed)),
            canonical_json_bytes(facets),
        )

        entity = EntityVersion(
            entity_id="framing.certificates",
            entity_type="FramingQualityBundle",
            version=1,
            project_id="project.certificates",
            title="Framing quality preflight",
            summary="Economist-facing benchmark and mechanism audit.",
            status=ScientificStatus(interpretation_validity="hypothesized"),
            facets=facets,
            created_at="2026-07-14T12:00:00Z",
        )
        self.assertTrue(is_packed_framing_quality_entity(entity))

    def test_wrong_schema_cross_facet_and_extra_payload_fail_closed(self) -> None:
        facets = pack_framing_quality_payload(bundle()).model_dump(mode="python")
        wrong_schema = {key: dict(value) for key, value in facets.items()}
        wrong_schema["economic_interpretation"]["schema"] = "wrong"
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            parse_framing_quality_payload("FramingQualityBundle", wrong_schema)

        cross_facet = {key: dict(value) for key, value in facets.items()}
        cross_facet["formal"] = {"note": "hidden coupling"}
        with self.assertRaisesRegex(ValueError, "must be empty"):
            parse_framing_quality_payload("FramingQualityBundle", cross_facet)

        extra = {key: dict(value) for key, value in facets.items()}
        extra["economic_interpretation"]["payload"] = dict(
            extra["economic_interpretation"]["payload"]
        )
        extra["economic_interpretation"]["payload"]["publication_ready"] = True
        with self.assertRaises(ValidationError):
            parse_framing_quality_payload("FramingQualityBundle", extra)


class FramingQualityRendererTests(unittest.TestCase):
    def test_renderer_is_economist_facing_and_omits_canonical_identifiers(self) -> None:
        markdown = render_framing_quality_memo(bundle(), benchmarks())
        self.assertIn("# When quality certificates weaken quality", markdown)
        self.assertIn("| No certification |", markdown)
        self.assertIn("| Fixed public signal |", markdown)
        self.assertIn("## Three-step economic logic", markdown)
        self.assertIn("**Payoff check (active).**", markdown)
        self.assertIn("compares Inspect (payoff u_f", markdown)
        self.assertIn("The response requires u_f >= u_a", markdown)
        self.assertIn("Kill this link if", markdown)
        self.assertIn("## Benchmark comparison", markdown)
        self.assertIn("**Open issues.**", markdown)
        self.assertNotIn("question.certificates", markdown)
        self.assertNotIn("benchmark.no_certificate", markdown)
        self.assertNotIn("force.information", markdown)
        self.assertNotIn("node.buyer_payoff", markdown)
        self.assertNotIn("schema", markdown.lower())
        self.assertNotIn("entity", markdown.lower())
        self.assertNotIn("system", markdown.lower())
        self.assertNotIn("→", markdown)
        self.assertIn("->", markdown)

    def test_renderer_rejects_question_or_benchmark_coverage_mismatch(self) -> None:
        original = bundle()
        wrong_question = benchmarks().model_copy(
            update={"question_ref": eref("question.other")}
        )
        with self.assertRaisesRegex(ValueError, "same research question"):
            render_framing_quality_memo(original, wrong_question)

        missing = original.model_copy(
            update={"benchmark_assessments": original.benchmark_assessments[:1]}
        )
        with self.assertRaisesRegex(ValueError, "every benchmark exactly once"):
            render_framing_quality_memo(missing, benchmarks())


if __name__ == "__main__":
    unittest.main()
