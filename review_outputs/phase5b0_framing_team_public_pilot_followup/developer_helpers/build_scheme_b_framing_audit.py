"""Author a WorkPacket-only V8 economics audit for the Scheme-B frame."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from econ_theorist.authoring_validation import (
    facet_semantic_hash,
    facet_semantic_value,
)
from econ_theorist.codec import object_digest
from econ_theorist.models import (
    Actor,
    CreateEntityOp,
    CreateRelationOp,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    SemanticFacetRef,
    Transaction,
)
from econ_theorist.framing_quality import (
    FramingQualityBundle,
    pack_framing_quality_payload,
)
from econ_theorist.theory import (
    GateDossier,
    PrimitiveGraph,
    ResearchQuestion,
    pack_theory_payload,
    parse_theory_entity,
)


RQ_REF = EntityVersionRef(
    entity_id="rq_score_disclosure_appeal_selection", version=1
)
BMK_REF = EntityVersionRef(
    entity_id="bmk_decision_only_disclosure_delta", version=1
)
PG_REF = EntityVersionRef(
    entity_id="pg_score_disclosure_appeal_selection", version=3
)
SOURCE_GATE_REF = EntityVersionRef(
    entity_id="gate_g1_score_disclosure_appeal_selection_scheme_b", version=1
)
FQB_REF = EntityVersionRef(
    entity_id="fqb_score_disclosure_scheme_b_audit", version=1
)
NEW_GATE_REF = EntityVersionRef(
    entity_id="gate_g1_score_disclosure_scheme_b_audit", version=1
)


def _ref_dict(reference: EntityVersionRef) -> dict[str, object]:
    return reference.model_dump(mode="json")


def _owner_facet(entity: EntityVersion) -> str:
    if entity.entity_type == "GateDossier":
        return "authority"
    if entity.entity_type in {
        "BenchmarkSet",
        "FramingQualityBundle",
        "PrimitiveGraph",
        "ResearchQuestion",
    }:
        return "economic_interpretation"
    raise ValueError(f"unsupported hard-relation endpoint {entity.entity_type}")


def _hard_relation(
    *,
    relation_id: str,
    relation_type: str,
    source: EntityVersion,
    target: EntityVersion,
    bindings: dict[str, object],
) -> RelationVersion:
    source_owner = _owner_facet(source)
    target_owner = _owner_facet(target)
    if source_owner == "authority":
        source_hash = object_digest(
            {
                "stored_authority": facet_semantic_value(source, "authority"),
                "effective_decisions": [],
            }
        )
    else:
        source_hash = facet_semantic_hash(source, source_owner)
    return RelationVersion(
        relation_id=relation_id,
        relation_type=relation_type,
        version=1,
        project_id=str(bindings["project_id"]),
        source=EntityVersionRef(entity_id=source.entity_id, version=source.version),
        target=EntityVersionRef(entity_id=target.entity_id, version=target.version),
        dependency_mode="hard",
        upstream=SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet=source_owner,
            field_path=None,
            semantic_hash=source_hash,
        ),
        downstream=FacetPathRef(
            entity_id=target.entity_id,
            version=target.version,
            facet=target_owner,
            field_path=None,
        ),
        scope_ref=RQ_REF.entity_id,
        scope_overlap=None,
        supersedes=None,
        created_at=str(bindings["created_at"]),
        privacy=str(bindings["privacy"]),
        access_compartments=tuple(bindings["access_compartments"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("response", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    response = json.loads(args.response.read_text(encoding="utf-8"))
    packet = response["work_packet"]
    contract = response["candidate_authoring_contract"]
    bindings = contract["transaction_bindings"]
    expected_focus = [
        _ref_dict(BMK_REF),
        _ref_dict(SOURCE_GATE_REF),
        _ref_dict(PG_REF),
        _ref_dict(RQ_REF),
    ]
    if (
        response["outcome"] != "ready"
        or packet["route_id"] != "audit.framing_economics"
        or packet["route_version"] != 8
        or packet["focus_refs"] != expected_focus
    ):
        raise ValueError("response is not the exact Scheme-B V8 audit packet")
    expected_logical_path = contract["output_locations"][
        "candidate_logical_path"
    ].replace("\\", "/")
    supplied_path = str(args.output).replace("\\", "/")
    if not supplied_path.lower().endswith("/" + expected_logical_path.lower()):
        raise ValueError("output does not match the WorkPacket-bound candidate path")

    entities = {
        item["entity_type"]: EntityVersion.model_validate_json(
            json.dumps(item), strict=True
        )
        for item in packet["compiled_context"]["entities"]
    }
    if set(entities) != {
        "BenchmarkSet",
        "GateDossier",
        "PrimitiveGraph",
        "ResearchQuestion",
    }:
        raise ValueError("audit packet contains an unexpected entity set")
    if (
        packet["compiled_context"]["effective_decisions"]
        or packet["compiled_context"]["status_source_decisions"]
    ):
        raise ValueError("audit packet unexpectedly contains a human decision")
    if [
        {"entity_id": item["entity_id"], "version": item["version"]}
        for item in packet["compiled_context"]["entities"]
    ] != expected_focus:
        raise ValueError("compiled context does not preserve exact focus order")

    rq_payload = parse_theory_entity(entities["ResearchQuestion"])
    pg_payload = parse_theory_entity(entities["PrimitiveGraph"])
    source_gate_payload = parse_theory_entity(entities["GateDossier"])
    if not isinstance(rq_payload, ResearchQuestion):
        raise TypeError("ResearchQuestion payload is unavailable")
    if not isinstance(pg_payload, PrimitiveGraph):
        raise TypeError("PrimitiveGraph payload is unavailable")
    if not isinstance(source_gate_payload, GateDossier):
        raise TypeError("source GateDossier payload is unavailable")
    final_rule = next(
        node for node in pg_payload.nodes if node.node_id == "final_review_rule"
    )
    if (
        "phi(s,r)=psi(r)" not in final_rule.economic_meaning
        or "phi(s,r)=r" not in final_rule.economic_meaning
        or "frontier" not in rq_payload.unresolved_delta.lower()
        or source_gate_payload.proposed_action != "revise"
    ):
        raise ValueError("packet does not contain the selected Scheme-B scope")

    fqb_payload = FramingQualityBundle.model_validate_json(
        json.dumps(
            {
            "research_question_ref": _ref_dict(RQ_REF),
            "benchmark_set_ref": _ref_dict(BMK_REF),
            "primitive_graph_ref": _ref_dict(PG_REF),
            "source_g1_dossier_ref": _ref_dict(SOURCE_GATE_REF),
            "tension": {
                "result_archetype": "comparative_statics_threshold",
                "tension_kind": "sign_or_threshold_reversal",
                "conventional_prediction": (
                    "Finer disclosure after rejection may appear to make appeal "
                    "decisions uniformly more accurate or to move one institutional "
                    "performance measure in a common direction."
                ),
                "countervailing_logic": (
                    "The refinement separates low- and middle-score posteriors around "
                    "the pooled posterior: some positive-probability cells can enter "
                    "appeal while others can exit, so volume, composition, corrected "
                    "rejections, erroneous acceptances, and burden need not share a sign."
                ),
                "economic_puzzle": (
                    "When does truthful rejected-score disclosure change the selected "
                    "appeal pool on an open parameter region even though every signal "
                    "technology, payoff, initial rule, and final review rule is fixed?"
                ),
                "resolution_target": (
                    "Characterize cell-specific posterior threshold crossings and map "
                    "them into an outcome-vector locus, without calling that locus a "
                    "frontier or imposing a welfare ranking."
                ),
            },
            "forces": [
                {
                    "force_id": "middle_cell_entry_force",
                    "label": "Middle-score posterior entry",
                    "role": "baseline_force",
                    "operative_margin": (
                        "A middle-score disclosed posterior can lie above the pooled "
                        "rejection posterior for the same private signal."
                    ),
                    "direction": "raises_target",
                    "economic_logic": (
                        "Because A_psi(p) is strictly increasing, disclosure raises the "
                        "net appeal payoff in such a middle-score cell and can move it "
                        "from no appeal to appeal."
                    ),
                    "active_when": (
                        "For a positive-probability cell, p_Mx>p_Px and "
                        "A_psi(p_Px)<c/v<A_psi(p_Mx)."
                    ),
                    "source_node_id": "disclosure_partition_delta",
                    "margin_node_id": "applicant_posterior",
                    "target_node_id": "institutional_outcome_vector",
                },
                {
                    "force_id": "low_cell_exit_force",
                    "label": "Low-score posterior exit",
                    "role": "countervailing_force",
                    "operative_margin": (
                        "A low-score disclosed posterior can lie below the pooled "
                        "rejection posterior for the same private signal."
                    ),
                    "direction": "lowers_target",
                    "economic_logic": (
                        "Strict review monotonicity converts the lower posterior into a "
                        "lower net appeal payoff and can move a pooled appellant out of "
                        "the appeal set after disclosure."
                    ),
                    "active_when": (
                        "For a positive-probability cell, p_Lx<p_Px and "
                        "A_psi(p_Lx)<c/v<A_psi(p_Px)."
                    ),
                    "source_node_id": "disclosure_partition_delta",
                    "margin_node_id": "applicant_posterior",
                    "target_node_id": "institutional_outcome_vector",
                },
            ],
            "causal_chain": [
                {
                    "step_number": 1,
                    "force_ids": [
                        "middle_cell_entry_force",
                        "low_cell_exit_force",
                    ],
                    "cause": (
                        "The rejected applicant learns low versus middle rather than "
                        "only the pooled rejection event."
                    ),
                    "endogenous_response": (
                        "For the same private signal, the pooled posterior separates "
                        "into score-specific posteriors."
                    ),
                    "consequence": (
                        "Cell-specific anticipated review acceptance probabilities "
                        "separate because A_psi(p) is strictly increasing."
                    ),
                    "source_node_id": "disclosure_partition_delta",
                    "target_node_id": "applicant_posterior",
                },
                {
                    "step_number": 2,
                    "force_ids": [
                        "middle_cell_entry_force",
                        "low_cell_exit_force",
                    ],
                    "cause": (
                        "The score-specific posterior changes v*A_psi(p)-c while v, c, "
                        "rho, and psi remain fixed."
                    ),
                    "endogenous_response": (
                        "A positive-probability cell crosses the binary appeal threshold "
                        "when c/v lies strictly between its pooled and disclosed A_psi."
                    ),
                    "consequence": (
                        "The cell enters or exits the appeal pool under score_disclosure."
                    ),
                    "source_node_id": "applicant_posterior",
                    "target_node_id": "appeal_choice",
                    "active_margin_witness": {
                        "decision_node_id": "appeal_choice",
                        "payoff_node_ids": ["appeal_value_and_cost"],
                        "concrete_state": (
                            "Take a positive-probability rejected cell with score=middle "
                            "and private signal x, after disclosure and before fresh "
                            "review, with p_Mx>p_Px. Choose the interior cost ratio "
                            "A_psi(p_Px)<c/v<A_psi(p_Mx)."
                        ),
                        "decision_maker": "The rejected applicant in that exact cell",
                        "focal_action": "Appeal",
                        "alternative_action": "Do not appeal",
                        "focal_payoff": "v*A_psi(p_Mx)-c>0",
                        "alternative_payoff": (
                            "0, because a non-appellant remains finally rejected"
                        ),
                        "feasibility_basis": (
                            "Appeal and no appeal are the exhaustive binary actions at "
                            "the same timing, information, beliefs, and continuation "
                            "convention; fresh review is realized only after appeal."
                        ),
                        "best_response_inequality": (
                            "v*A_psi(p_Mx)-c>0>v*A_psi(p_Px)-c, so appeal is strictly "
                            "optimal after middle disclosure while no appeal is strictly "
                            "optimal under the pooled message."
                        ),
                        "activity_status": "active",
                        "status_basis": (
                            "A_psi'(p)=[psi(1)-psi(0)]*(rho_1-rho_0)>0. The information "
                            "refinement therefore changes the appeal payoff difference "
                            "by v[A_psi(p_Mx)-A_psi(p_Px)]>0; the strict cost sandwich "
                            "defines a nonempty open region."
                        ),
                        "kill_condition": (
                            "This link is inactive if the review rule or signal is "
                            "uninformative, the disclosed and pooled posteriors coincide, "
                            "the cell has zero probability, or no admissible positive "
                            "cost ratio lies between the two A_psi values."
                        ),
                        "consequence_binding": {
                            "consequence_node_id": "institutional_outcome_vector",
                            "transition_kind": "switch",
                            "causal_edge_ids": ["appeal_choice_to_outcomes"],
                            "public_state_conditions": [
                                {
                                    "node_id": "initial_decision_rule",
                                    "relation": "equals",
                                    "value": "reject",
                                },
                                {
                                    "node_id": "institutional_score",
                                    "relation": "equals",
                                    "value": "middle",
                                },
                                {
                                    "node_id": "applicant_private_signal",
                                    "relation": "equals",
                                    "value": "x",
                                },
                            ],
                            "focal_consequence": (
                                "The positive-mass cell enters the appeal pool and can "
                                "contribute processing burden plus review-contingent "
                                "classification outcomes."
                            ),
                            "alternative_consequence": (
                                "The same cell does not appeal, remains finally rejected, "
                                "and creates no appeal-processing burden."
                            ),
                            "feasibility_basis": (
                                "Both actions are feasible at the same pre-review state; "
                                "the fixed model maps appeal into review and no appeal "
                                "into final rejection."
                            ),
                        },
                    },
                },
                {
                    "step_number": 3,
                    "force_ids": [
                        "middle_cell_entry_force",
                        "low_cell_exit_force",
                    ],
                    "cause": (
                        "The set and composition of appellants changes across the two "
                        "information regimes."
                    ),
                    "endogenous_response": (
                        "The appeal-weighted distribution of qualification and review "
                        "outcomes is reweighted."
                    ),
                    "consequence": (
                        "Appeal load, qualified appellants, corrected qualified "
                        "rejections, unqualified final acceptances, composition, and "
                        "processing burden change as an outcome vector with no common sign."
                    ),
                    "source_node_id": "appeal_choice",
                    "target_node_id": "institutional_outcome_vector",
                },
            ],
            "minimal_example": {
                "title": "One middle-score cell crosses an interior appeal threshold",
                "setup": (
                    "Fix one private-signal realization x in the full-support binary-state "
                    "baseline. Conditional independence and the ordered rejected scores "
                    "give p_Mx>p_Px>p_Lx. Under Scheme B, A_psi is strictly increasing."
                ),
                "moving_primitive": (
                    "Only the rejection message moves from pooled {low,middle} to the "
                    "realized low or middle score."
                ),
                "held_fixed": [
                    "The prior and all score, private-signal, and review-signal laws",
                    "The initial high-accept/low-middle-reject rule",
                    "The score-blind strictly review-monotone psi, including phi=r as the minimal baseline",
                    "Applicant value v, appeal cost c, tie rule, and no-appeal continuation",
                    "Per-appeal burden and every institutional outcome definition",
                ],
                "endogenous_responses": [
                    "The applicant's posterior after the message and private signal",
                    "The cell's binary appeal choice",
                    "The selected appeal pool and its outcome-vector contributions",
                ],
                "predicted_pattern": (
                    "For any c/v strictly between A_psi(p_Px) and A_psi(p_Mx), "
                    "the middle-x cell does not appeal under decision_only and appeals "
                    "under score_disclosure; an analogous low-x interval can produce exit."
                ),
                "economic_intuition": (
                    "Finer information matters because it changes a privately chosen "
                    "selection threshold, not because the institution changes its rules."
                ),
                "limitation": (
                    "This symbolic cell illustrates an open-region threshold crossing; "
                    "it is not a calibrated example or a proof of an aggregate sign."
                ),
                "cannot_establish": [
                    "A common sign for total appeal volume or any classification component",
                    "A welfare ranking or optimal disclosure policy",
                    "A capacity or optimization frontier",
                    "Novelty, full formal validity, or human G1 approval",
                ],
            },
            "economist_memo": {
                "headline": (
                    "Rejected-score disclosure reshuffles who appeals; it does not by "
                    "itself trace an institutional frontier"
                ),
                "opening_question": (
                    "When does telling a rejected applicant whether the score was low or "
                    "middle change a costly appeal decision?"
                ),
                "benchmark_message": (
                    "Decision_only reveals only pooled rejection. Score_disclosure changes "
                    "only that information partition; all technologies, payoffs, and rules "
                    "remain fixed."
                ),
                "tension_message": (
                    "The middle-score posterior may induce entry while the low-score "
                    "posterior induces exit, so more information has no automatic volume "
                    "or classification sign."
                ),
                "mechanism_message": (
                    "Scheme B makes anticipated final acceptance strictly increasing in "
                    "the applicant posterior; disclosure then moves cell-specific net "
                    "appeal payoffs across a fixed threshold."
                ),
                "result_preview": (
                    "Strict cost sandwiches between pooled and disclosed A_psi values "
                    "generate nonempty open entry or exit regions, followed by a transparent "
                    "selection decomposition of the institutional outcome vector."
                ),
                "contribution_message": (
                    "The plausible contribution is a posterior-ordering and selection "
                    "characterization, not a sign theorem, welfare result, or claim that a "
                    "mechanism is absent from a coequal contrast benchmark."
                ),
                "scope_condition": (
                    "The conclusion uses conditional independence, full support, informative "
                    "review, a score-blind strictly review-monotone final rule, and no hard "
                    "capacity, rationing, congestion, or endogenous review quality."
                ),
                "reader_takeaway": (
                    "The active economics is the applicant's threshold response to refined "
                    "information; the remaining repair is to call the downstream object an "
                    "outcome-vector comparison or locus rather than a frontier."
                ),
            },
            "benchmark_assessments": [
                {
                    "benchmark_id": "decision_only",
                    "changed": [
                        {
                            "object_id": "rejection_message_partition",
                            "label": "Rejected applicant's information partition",
                            "semantic_level": "primitive",
                            "primitive_node_id": "disclosure_partition_delta",
                        }
                    ],
                    "held_fixed": [
                        {
                            "object_id": "initial_rule",
                            "label": "Initial high-accept and low-middle-reject rule",
                            "semantic_level": "primitive",
                            "primitive_node_id": "initial_decision_rule",
                            "fixing_level": "policy_rule",
                        },
                        {
                            "object_id": "signal_laws",
                            "label": "Prior and score, private, and review signal laws",
                            "semantic_level": "conditional_distribution",
                            "primitive_node_id": "conditional_independence_normalization",
                            "fixing_level": "conditional_distribution",
                        },
                        {
                            "object_id": "final_rule",
                            "label": "Score-blind strictly review-monotone psi",
                            "semantic_level": "primitive",
                            "primitive_node_id": "final_review_rule",
                            "fixing_level": "policy_rule",
                        },
                        {
                            "object_id": "appeal_payoffs",
                            "label": "Applicant value, appeal cost, and tie rule",
                            "semantic_level": "primitive",
                            "primitive_node_id": "appeal_value_and_cost",
                            "fixing_level": "payoff_ledger",
                        },
                        {
                            "object_id": "processing_technology",
                            "label": "Positive constant burden per appeal",
                            "semantic_level": "primitive",
                            "primitive_node_id": "processing_burden",
                            "fixing_level": "primitive",
                        },
                    ],
                    "reoptimizing": [
                        {
                            "object_id": "appeal_decision",
                            "label": "Binary costly appeal choice",
                            "semantic_level": "choice",
                            "primitive_node_id": "appeal_choice",
                        }
                    ],
                    "still_endogenous": [
                        {
                            "object_id": "posterior",
                            "label": "Regime-contingent applicant posterior",
                            "semantic_level": "equilibrium_object",
                            "primitive_node_id": "applicant_posterior",
                        },
                        {
                            "object_id": "selected_appeal_pool",
                            "label": "Appeal set and appellant composition",
                            "semantic_level": "behavioral_response",
                            "primitive_node_id": "appeal_choice",
                        },
                        {
                            "object_id": "institutional_vector",
                            "label": "Classification and processing outcome vector",
                            "semantic_level": "outcome",
                            "primitive_node_id": "institutional_outcome_vector",
                        },
                    ],
                    "targets": [
                        {
                            "object_id": "appeal_load",
                            "label": "Total appeal processing load",
                            "semantic_level": "aggregate",
                            "primitive_node_id": "institutional_outcome_vector",
                        },
                        {
                            "object_id": "classification_components",
                            "label": "Corrected qualified rejections and unqualified acceptances",
                            "semantic_level": "aggregate",
                            "primitive_node_id": "institutional_outcome_vector",
                        },
                    ],
                    "channel_kind": "active_response",
                    "channel_path": [
                        "disclosure_partition_delta",
                        "applicant_posterior",
                        "appeal_choice",
                        "institutional_outcome_vector",
                    ],
                    "channel_summary": (
                        "Only the information message changes; it separates posteriors, "
                        "moves a binary appeal best response on strict cost intervals, and "
                        "thereby reweights the outcome vector."
                    ),
                    "aggregate_invariance": {
                        "aggregate_object": (
                            "Appeal-weighted classification and processing outcome vector"
                        ),
                        "pointwise_policy_fixed": True,
                        "weighting_distribution_status": "changed",
                        "claims_aggregate_fixed": False,
                        "basis": (
                            "The initial and final rules are pointwise fixed, but the mass "
                            "and type distribution selecting into appeal changes endogenously."
                        ),
                        "implication_for_attribution": (
                            "Outcome changes can be attributed to information-induced appeal "
                            "selection, but no aggregate component is invariant or signed."
                        ),
                    },
                    "selection_assurance": {
                        "status": "unique_equilibrium",
                        "selection_rule": (
                            "Appeal iff v*A_psi(p)-c>=0, with indifference resolved in favor "
                            "of appeal"
                        ),
                        "basis": (
                            "The applicant has an exhaustive binary action set and no "
                            "strategic feedback; the stated tie rule selects the boundary."
                        ),
                        "implication_for_attribution": (
                            "The open-region threshold crossing does not depend on an "
                            "arbitrary equilibrium selector."
                        ),
                    },
                    "attribution_strength": "qualified",
                    "attribution_basis": (
                        "The exact active path and payoff witness are established on an open "
                        "region, but aggregate signs remain distribution-dependent and the "
                        "ResearchQuestion's frontier label exceeds the supplied structure."
                    ),
                    "distinctive_mechanism": {
                        "claim_kind": "not_claimed",
                        "mechanism_label": (
                            "Information-induced appeal selection relative to decision_only"
                        ),
                        "basis": (
                            "The exact delta has an active choice channel, but the package "
                            "contains no coequal contrast benchmark from which to claim a "
                            "mechanism is absent; no benchmark-distinctive mechanism "
                            "contribution is asserted."
                        ),
                    },
                }
            ],
            "distinctive_mechanism_contribution_status": "not_claimed",
            "disclosed_gaps": [
                {
                    "gap_id": "gap_frontier_terminology",
                    "category": "scope",
                    "description": (
                        "The ResearchQuestion asks for a classification-processing frontier, "
                        "but the maintained frame defines only an outcome vector and its "
                        "regime difference. It supplies no feasible-set boundary, objective, "
                        "capacity, rationing, congestion, or optimization problem."
                    ),
                    "consequence": (
                        "The active threshold mechanism can support an outcome-vector locus "
                        "or comparison, but not a strict frontier claim or G1 readiness."
                    ),
                    "resolution_needed": (
                        "Supersede the ResearchQuestion so the unresolved delta and importance "
                        "refer to an outcome-vector comparison or locus. Add a true frontier "
                        "only through a separately authorized framing decision that supplies "
                        "the missing capacity or optimization structure."
                    ),
                    "affected_benchmark_ids": ["decision_only"],
                    "repair_target_refs": [
                        {
                            "entity_type": "ResearchQuestion",
                            "entity_ref": _ref_dict(RQ_REF),
                        }
                    ],
                }
            ],
            "proposed_action": "revise_framing",
            "action_rationale": (
                "Scheme B establishes an active, consequence-bound appeal margin on a "
                "nonempty open cost region, so the former final-rule defect is resolved. "
                "The separate ResearchQuestion frontier terminology remains false to the "
                "maintained model and must be repaired at rq_score_disclosure_appeal_selection@1 "
                "before any ready_for_g1 proposal. No human G1 decision is recorded."
            ),
            }
        ),
        strict=True,
    )

    fqb_entity = EntityVersion(
        entity_id=FQB_REF.entity_id,
        entity_type="FramingQualityBundle",
        version=1,
        project_id=str(bindings["project_id"]),
        title="Scheme-B economics audit of rejected-score disclosure",
        summary=(
            "A V8 framing audit finding an active posterior-threshold appeal margin "
            "under Scheme B while retaining one exact ResearchQuestion terminology repair."
        ),
        status=entities["GateDossier"].status,
        facets=pack_framing_quality_payload(fqb_payload),
        supersedes=None,
        created_at=str(bindings["created_at"]),
        privacy=str(bindings["privacy"]),
        access_compartments=tuple(bindings["access_compartments"]),
        artifact_refs=(),
        scope_ref=RQ_REF.entity_id,
    )

    preserved_requirements = [
        requirement.model_dump(mode="json")
        for requirement in source_gate_payload.requirements
    ]
    strengthened_requirements = [
        *preserved_requirements,
        {
            "requirement_id": "g1.framing_quality",
            "description": (
                "The current V8 audit establishes an active same-state binary appeal "
                "margin under Scheme B, binds the action to the exact appeal-to-outcome "
                "edge, identifies a nonempty open cost region, and discloses the remaining "
                "ResearchQuestion frontier-terminology risk."
            ),
            "recorded_condition": "risk_disclosed",
            "evidence_refs": [_ref_dict(FQB_REF)],
        },
    ]
    new_gate_payload = GateDossier.model_validate_json(
        json.dumps(
            {
                "gate_kind": source_gate_payload.gate_kind,
                "research_question_ref": _ref_dict(
                    source_gate_payload.research_question_ref
                ),
                "ordered_object_refs": [
                    *(
                        _ref_dict(reference)
                        for reference in source_gate_payload.ordered_object_refs
                    ),
                    _ref_dict(FQB_REF),
                ],
                "requirements": strengthened_requirements,
                "proposed_action": "revise",
                "rationale": (
                    "Scheme B resolves the former final-rule and active-margin defect: a "
                    "strictly positive posterior response creates open cost intervals with "
                    "cell entry or exit, and the exact appeal-to-outcome consequence is bound. "
                    "Every source-dossier requirement remains preserved. G1 nevertheless "
                    "remains unconfirmed because the ResearchQuestion still uses frontier "
                    "terminology unsupported by the maintained outcome-vector model. Repair "
                    "that exact RQ wording and audit the refreshed package; do not add "
                    "capacity, welfare, or a human decision implicitly."
                ),
                "prepared_at": str(bindings["created_at"]),
                "ordered_artifact_refs": [
                    reference.model_dump(mode="json")
                    for reference in source_gate_payload.ordered_artifact_refs
                ],
            }
        ),
        strict=True,
    )
    new_gate_entity = entities["GateDossier"].model_copy(
        update={
            "entity_id": NEW_GATE_REF.entity_id,
            "version": 1,
            "title": "Post-Scheme-B G1 economics-audit dossier",
            "summary": (
                "An unconfirmed G1 dossier that accepts the Scheme-B active-margin "
                "evidence but requires exact repair of unsupported frontier terminology."
            ),
            "facets": pack_theory_payload(new_gate_payload),
            "supersedes": None,
            "created_at": str(bindings["created_at"]),
        }
    )

    audit_relations = tuple(
        _hard_relation(
            relation_id=relation_id,
            relation_type="audits",
            source=entities[source_type],
            target=fqb_entity,
            bindings=bindings,
        )
        for relation_id, source_type in (
            ("rel_scheme_b_audit_rq", "ResearchQuestion"),
            ("rel_scheme_b_audit_benchmark", "BenchmarkSet"),
            ("rel_scheme_b_audit_primitives", "PrimitiveGraph"),
            ("rel_scheme_b_audit_source_gate", "GateDossier"),
        )
    )
    governs_relation = _hard_relation(
        relation_id="rel_scheme_b_audit_governs_gate",
        relation_type="governs",
        source=fqb_entity,
        target=new_gate_entity,
        bindings=bindings,
    )
    relation_refs = tuple(
        RelationVersionRef(
            relation_id=relation.relation_id, version=relation.version
        )
        for relation in (*audit_relations, governs_relation)
    )

    transaction = Transaction(
        transaction_id="tx_audit_scheme_b_framing_economics",
        origin=str(bindings["origin"]),
        project_id=str(bindings["project_id"]),
        base_revision=str(bindings["base_revision"]),
        route_run_id=str(bindings["route_run_id"]),
        route_id=str(bindings["route_id"]),
        actor=Actor.model_validate(bindings["actor"], strict=True),
        intent=(
            "Audit Scheme B's active appeal margin and preserve the separate exact "
            "ResearchQuestion terminology repair without confirming G1."
        ),
        changed_facets=(),
        operations=(
            CreateEntityOp(entity=fqb_entity),
            CreateEntityOp(entity=new_gate_entity),
            *(CreateRelationOp(relation=relation) for relation in audit_relations),
            CreateRelationOp(relation=governs_relation),
            RecordRouteOutcomeOp(
                outcome=RouteOutcome(
                    route_run_id=str(bindings["route_run_id"]),
                    route_id=str(bindings["route_id"]),
                    outcome="completed_with_candidate",
                    rationale=(
                        "Scheme B passes the active-margin and consequence-binding audit, "
                        "but unsupported frontier terminology requires exact RQ revision; "
                        "no human G1 decision is recorded."
                    ),
                    candidate_refs=(
                        FQB_REF,
                        NEW_GATE_REF,
                        *relation_refs,
                    ),
                    privacy=str(bindings["privacy"]),
                    access_compartments=tuple(bindings["access_compartments"]),
                )
            ),
        ),
        evidence_refs=tuple(
            EntityVersionRef.model_validate(reference, strict=True)
            for reference in bindings["required_entity_evidence_refs"]
        ),
        privacy=str(bindings["privacy"]),
        access_compartments=tuple(bindings["access_compartments"]),
        created_at=str(bindings["created_at"]),
        parent_transaction_hash=str(bindings["parent_transaction_hash"]),
        route_run_hash=str(bindings["route_run_hash"]),
        context_manifest_hash=str(bindings["context_manifest_hash"]),
        compiled_context_hash=str(bindings["compiled_context_hash"]),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(transaction.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
