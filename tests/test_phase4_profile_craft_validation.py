"""Focused semantic and route tests for Phase 4 profile/craft validation."""

from __future__ import annotations

from unittest import mock
import unittest

from pydantic import BaseModel

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase3_authoring_models import paper_ir, reader_path
from tests.test_phase3_downgrade_attacks import manuscript_material
from tests.test_phase4_profile_craft_models import (
    actor,
    craft_material,
    diagnosis,
    mapping_audit,
    predicate_contract,
    profile_material,
    realization,
    selection_material,
)

from econ_theorist import authoring as a
from econ_theorist import profile_craft as pc
from econ_theorist import theory as t
from econ_theorist.codec import object_digest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EffectiveDecisionRef,
    EntityDerivedStatus,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V4_HASH, load_route_registry_by_hash
from econ_theorist.profile_craft_validation import (
    ProfileCraftValidationError,
    _build_indices,
    _validate_contract_receipt_bound,
    _validate_relation_semantics,
    audit_is_approved_bounded,
    validate_phase4_route_entry,
    validate_phase4_route_transaction,
    validate_profile_craft_entity,
    validate_profile_craft_projection,
    validate_profile_craft_ready,
    validate_target_profile,
)
from econ_theorist.profile_craft_policy import (
    load_craft_corpus,
    load_profile_catalog,
    resolve_profile_stack,
    select_craft_moves,
)
from econ_theorist.runtime.freshness import facet_semantic_hash


PROJECT = "project.phase4.validation"
HEAD = "f" * 64
NOW = "2026-07-12T14:00:00Z"
HUMAN = Actor(kind="human", actor_id="human.phase4.owner")
CLOSER = Actor(kind="deterministic_tool", actor_id="tool.phase4.closer")


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def aref(
    artifact_id: str, digest: str = "a" * 64, version: int = 1
) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id, version=version, content_hash=digest
    )


def _walk_artifacts(value: object):
    if isinstance(value, ArtifactDependencyRef):
        yield value
    elif isinstance(value, pc.ProfileCraftPayload):
        for field_name in type(value).model_fields:
            yield from _walk_artifacts(getattr(value, field_name))
    elif isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from _walk_artifacts(getattr(value, field_name))
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _walk_artifacts(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_artifacts(item)


def pc_entity(entity_id: str, payload: pc.ProfileCraftPayload) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=1,
        project_id=PROJECT,
        title=f"Phase 4 {entity_id}",
        summary=f"Exact Phase 4 fixture for {entity_id}.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=pc.pack_profile_craft_payload(payload),
        artifact_refs=tuple(set(_walk_artifacts(payload))),
        created_at=NOW,
    )


def authoring_entity(entity_id: str, payload: a.AuthoringPayload) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=1,
        project_id=PROJECT,
        title=f"Authoring {entity_id}",
        summary=f"Exact authoring fixture for {entity_id}.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=a.pack_authoring_payload(payload),
        artifact_refs=tuple(set(_walk_artifacts(payload))),
        created_at=NOW,
    )


def theory_entity(entity_id: str, payload: t.TheoryPayload) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=1,
        project_id=PROJECT,
        title=f"Theory {entity_id}",
        summary=f"Exact theory fixture for {entity_id}.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=t.pack_theory_payload(payload),
        artifact_refs=tuple(set(_walk_artifacts(payload))),
        created_at=NOW,
    )


def registration(reference: ArtifactDependencyRef) -> ArtifactRegistration:
    return ArtifactRegistration(
        artifact_id=reference.artifact_id,
        version=reference.version,
        project_id=PROJECT,
        logical_name=f"Fixture bytes for {reference.artifact_id}",
        media_type="application/octet-stream",
        content_hash=reference.content_hash,
        byte_size=0,
        created_at=NOW,
    )


def _theory_material():
    formal_model = t.FormalModel(
        question_ref=eref("question"),
        selected_mechanism_ref=eref("mechanism"),
        primitive_graph_ref=eref("primitives"),
        formal_objects=(
            t.FormalObject(
                object_id="object.choice",
                symbol="x",
                object_kind="choice",
                definition="The receiver's binary information-use choice.",
                central=True,
            ),
        ),
        timing=("The receiver observes precision and then chooses whether to process.",),
        choice_or_strategy_spaces=("The processing choice belongs to {0,1}.",),
        feasibility=("Both processing choices are feasible in the maintained domain.",),
        solution_concept="Expected-payoff maximization by the receiver.",
        outcome_definitions=("Realized accuracy is evaluated after the processing choice.",),
        full_specification_ref=ArtifactDependencyRef(
            artifact_id="artifact.formal.model",
            version=1,
            content_hash="1" * 64,
        ),
    )
    assumptions = t.AssumptionMap(
        formal_model_ref=eref("formal.model"),
        formalization_map_ref=eref("formalization.map"),
        assumptions=(
            t.AssumptionRecord(
                assumption_id="assumption.processing",
                exact_content="Processing is indivisible and has positive cost.",
                quantifiers=("For every maintained precision level.",),
                economic_interpretation="The receiver chooses an extensive information-use margin.",
                foundation="primitive",
                roles=("mechanism",),
                satisfying_case_ids=("case.processing",),
                scope_cost="The result does not cover divisible processing.",
                necessity_status="unknown",
            ),
        ),
    )
    obligation = t.ProofObligation(
        claim_graph_ref=eref("claim.graph"),
        claim_id="claim.reversal",
        obligation_id="obligation.reversal",
        statement="Show the exact processing-threshold reversal on the maintained domain.",
        burden="sufficiency",
        quantifier_scope="For every primitive tuple in the stated threshold interval.",
        assumption_ids=("assumption.processing",),
        admissible_methods=("analytic_proof", "symbolic_identity"),
    )
    claim_graph = t.ClaimGraph(
        formal_model_ref=eref("formal.model"),
        formalization_map_ref=eref("formalization.map"),
        assumption_map_ref=eref("assumption.map"),
        claims=(
            t.ClaimNode(
                claim_id="claim.reversal",
                archetype="mechanism_explanation",
                scientific_job="headline",
                formal_statement="A precision-linked processing cost can reverse realized accuracy.",
                domain="The stated binary-processing threshold interval.",
                quantifiers=("For every primitive tuple in the interval.",),
                assumption_ids=("assumption.processing",),
                semantic_translation="Precision can reduce accuracy by deterring information use.",
                dependency_refs=(eref("formal.model"),),
                mechanism_ref=eref("mechanism"),
                proof_obligation_refs=(eref("proof.obligation"),),
            ),
        ),
        contribution_spine=("claim.reversal",),
    )
    package = t.ValidatedArgumentPackage(
        question_ref=eref("question"),
        benchmark_set_ref=eref("benchmarks"),
        primitive_graph_ref=eref("primitives"),
        selected_mechanism_ref=eref("mechanism"),
        serious_rejected_rival_refs=(eref("rival"),),
        prediction_register_ref=eref("predictions"),
        example_suite_ref=eref("examples"),
        economic_argument_graph_ref=eref("argument.graph"),
        implementation_tournament_ref=eref("implementation.tournament"),
        formal_model_ref=eref("formal.model"),
        formalization_map_ref=eref("formalization.map"),
        assumption_map_ref=eref("assumption.map"),
        claim_graph_ref=eref("claim.graph"),
        verification_bundle_ref=eref("verification.bundle"),
        closest_theory_map_ref=eref("closest.theory"),
        absorption_assessment_ref=eref("absorption"),
        result_portfolio_ref=eref("portfolio"),
        prior_gate_decision_refs=tuple(
            DecisionVersionRef(decision_id=f"decision.g{index}", version=1)
            for index in range(1, 5)
        ),
        g5_dossier_ref=eref("g5.dossier"),
        economic_nugget="Information quality changes both conditional value and uptake.",
        qualified_novelty="The result isolates an extensive information-use mechanism.",
        unresolved_risks=("The divisible-processing extension is unresolved.",),
        prohibited_overclaims=("Do not claim that coarse information always dominates.",),
        release_mode="production_candidate",
        novelty_claim_mode="qualified",
    )
    return formal_model, assumptions, obligation, claim_graph, package


def decision(decision_id: str, kind: str, selected: str) -> Decision:
    return Decision(
        decision_id=decision_id,
        version=1,
        project_id=PROJECT,
        decision_kind=kind,  # type: ignore[arg-type]
        subject_ref="entity.reader.path",
        scope_ref="entity.paper",
        question=f"Confirm the exact {kind} target?",
        options=(selected, "revise"),
        selected_option=selected,
        recommendation=f"Confirm {selected}.",
        rationale="The human owner explicitly selects this target dimension.",
        required_authority="L2",
        decider=HUMAN,
        decided_at=NOW,
        status="confirmed",
    )


def _base_authoring_closure(unit_ref: EntityVersionRef) -> a.ReviewClosure:
    checks = tuple(
        a.AuthoringReadyCheck(
            check_id=check_id,
            outcome="passed",
            evidence_refs=(unit_ref,),
            rationale=f"The exact {check_id} component passed.",
        )
        for check_id in a.AUTHORING_READY_CHECK_ORDER
    )
    return a.ReviewClosure(
        compiler_mode="working",
        paper_ir_ref=eref("entity.paper"),
        reader_path_ref=eref("entity.reader.path"),
        result_contract_set_ref=eref("entity.result.contracts"),
        assurance_bundle_ref=eref("assurance.bundle"),
        manuscript_unit_ref=unit_ref,
        formal_fidelity_review_ref=eref("review.formal"),
        economic_reader_review_ref=eref("review.economic"),
        cold_reader_review_ref=eref("review.cold"),
        closure_actor=Actor(kind="deterministic_tool", actor_id="tool.phase3.closer"),
        checks=checks,
        status="authoring_ready",
        evaluated_at=NOW,
    )


def _result_contracts(paper: a.PaperIR) -> a.ResultContractSet:
    projection = paper.claim_projections[0]
    economic_ref = eref("economic.argument.graph")

    def layer(content: str) -> a.LayerContract:
        return a.LayerContract(
            applicability="applicable", content=content, source_refs=(economic_ref,)
        )

    def element(content: str) -> a.ContractElement:
        return a.ContractElement(content=content, source_refs=(economic_ref,))

    packet = a.ResultPacket(
        packet_id="packet.reversal",
        claim_projection_id=projection.projection_id,
        claim_graph_ref=projection.claim_graph_ref,
        claim_id=projection.claim_id,
        primary_archetype="mechanism_explanation",
        question=layer("Can precision reduce realized accuracy with endogenous use?"),
        pre_result_expectation=a.LayerContract(
            applicability="not_applicable",
            not_applicable_reason="The exact reader path already states the benchmark.",
        ),
        formal_statement_and_scope=layer(projection.formal_statement),
        economic_translation=layer(projection.semantic_translation),
        archetype_explanation=layer(
            "A direct accuracy gain competes with a precision-linked uptake cost."
        ),
        boundary=layer("The reversal vanishes when precision no longer changes uptake."),
        proof_roadmap=layer("Order the two uptake thresholds on the maintained domain."),
        consequence=layer("Information quality cannot be ranked independently of use."),
        archetype_module=a.MechanismExplanationModule(
            initiating_force=element("Precision raises the cost of processing."),
            affected_margin=element("The receiver's discrete information-use decision."),
            serious_rival=element("Precision directly raises conditional accuracy."),
            separating_example=element("Only the coarse signal is used between thresholds."),
            ablation=element("Fixing processing cost removes the uptake response."),
            failure_case=element("Outside the separating interval both signals are used."),
        ),
    )
    return a.ResultContractSet(
        paper_ir_ref=eref("entity.paper"),
        reader_path_ref=eref("entity.reader.path"),
        claim_graph_ref=projection.claim_graph_ref,
        assumption_map_ref=eref("assumption.map"),
        economic_argument_graph_ref=economic_ref,
        example_suite_ref=eref("example.suite"),
        verification_bundle_ref=eref("verification.bundle"),
        result_packets=(packet,),
        proof_roadmaps=(
            a.ProofRoadmapContract(
                roadmap_id="roadmap.reversal",
                claim_id=projection.claim_id,
                object_constructed_or_compared="The low- and high-precision uptake thresholds.",
                key_decomposition_or_monotonicity_step="Separate conditional accuracy from the extensive uptake response.",
                assumption_roles=("Indivisible processing creates the extensive margin.",),
                main_technical_obstacle="Track the exact endpoints and tie-breaking cases.",
                method_or_certificate="Analytic threshold ordering on the maintained domain.",
                scope_not_established="No welfare ranking is established outside the domain.",
                proof_refs=(eref("verification.bundle"),),
            ),
        ),
        built_at=NOW,
    )


def _formal_review(
    unit: a.ManuscriptUnit,
    *,
    unit_ref: EntityVersionRef = eref("manuscript.unit"),
    assignment_ref: EntityVersionRef = eref("assignment.formal"),
) -> a.ReviewRecord:
    span = unit.spans[0]
    return a.ReviewRecord(
        assignment_ref=assignment_ref,
        manuscript_unit_ref=unit_ref,
        reviewed_artifact_ref=unit.manuscript_artifact_ref,
        role="formal_fidelity",
        reviewer=actor("critic.formal"),
        canonical_writer=unit.canonical_writer,
        context_hash="9" * 64,
        assessment=a.FormalFidelityAssessment(
            theorem_statement_exact=True,
            scope_preserved=True,
            assumptions_preserved=True,
            proof_language_honest=True,
            numerical_evidence_bounded=True,
            entailment_checks=(
                a.EntailmentCheck(
                    assertion_id=span.assertion_id,
                    scope_relation="equal",
                    conclusion_relation="equivalent",
                    assumptions_preserved=True,
                    source_refs=(eref("claim.graph"),),
                    outcome="passed",
                    rationale="The exact consequential span is entailed by its sources.",
                ),
            ),
        ),
        reviewed_at=NOW,
    )


def _economic_review(
    unit: a.ManuscriptUnit,
    contracts: a.ResultContractSet,
    *,
    unit_ref: EntityVersionRef,
    passed: bool,
    finding_ref: EntityVersionRef | None = None,
) -> a.ReviewRecord:
    packet = contracts.result_packets[0]
    assertion_ids = tuple(item.assertion_id for item in unit.spans)
    reconstruction = a.EconomicReconstruction(
        claim_projection_id=packet.claim_projection_id,
        claim_id=packet.claim_id,
        result_packet_id=packet.packet_id,
        question_and_benchmark="The benchmark fixes uptake; the paper studies realized accuracy when use is endogenous.",
        operative_force="Precision raises both conditional accuracy and the cost of using information.",
        affected_margin="The discrete decision to use the signal.",
        serious_rival_and_separator="The direct accuracy gain is separated by the between-threshold case.",
        mechanism_steps=(
            "Precision improves accuracy conditional on processing.",
            "Precision-linked cost shifts the uptake threshold.",
            "Between thresholds only coarse information is used.",
        ),
        mechanism_assertion_ids=(assertion_ids[0],),
        diagnostic_assertion_ids=(assertion_ids[min(1, len(assertion_ids) - 1)],),
        boundary_assertion_ids=(assertion_ids[-1],),
        near_transfer_prediction="Holding the cost fixed removes the reversal.",
        explanatory_delta_from_formal_statement="The threshold gap turns precision into an extensive-margin force.",
        evidence_refs=(unit_ref, unit.manuscript_artifact_ref),
    )
    return a.ReviewRecord(
        assignment_ref=eref("assignment.economic.old" if not passed else "assignment.economic"),
        manuscript_unit_ref=unit_ref,
        reviewed_artifact_ref=unit.manuscript_artifact_ref,
        role="economic_reader",
        reviewer=actor("critic.economic"),
        canonical_writer=unit.canonical_writer,
        context_hash="8" * 64,
        assessment=a.EconomicReaderAssessment(
            question_and_benchmark_reconstructible=passed,
            explanation_is_not_restatement=passed,
            mechanism_or_conceptual_logic_reconstructible=passed,
            diagnostic_example_or_witness_present=passed,
            boundary_is_economically_interpretable=passed,
            reconstructions=(reconstruction,),
        ),
        finding_refs=() if finding_ref is None else (finding_ref,),
        reviewed_at=NOW,
    )


def _cold_review(
    unit: a.ManuscriptUnit,
    *,
    unit_ref: EntityVersionRef = eref("manuscript.unit"),
    assignment_ref: EntityVersionRef = eref("assignment.cold"),
) -> a.ReviewRecord:
    kinds = a.READER_PROBE_KIND_ORDER
    return a.ReviewRecord(
        assignment_ref=assignment_ref,
        manuscript_unit_ref=unit_ref,
        reviewed_artifact_ref=unit.manuscript_artifact_ref,
        role="cold_reader",
        reviewer=actor("critic.cold.adjudicator"),
        canonical_writer=unit.canonical_writer,
        context_hash="7" * 64,
        assessment=a.ColdReaderAssessment(
            question_and_benchmark_retell_passed=True,
            exact_scope_recovery_passed=True,
            assumption_role_recovery_passed=True,
            boundary_discrimination_passed=True,
            near_transfer_passed=True,
            response_artifact_ref=aref("cold.response", "6" * 64),
            probe_results=tuple(
                a.ColdReaderProbeResult(
                    probe_id=f"probe.{kind}",
                    kind=kind,  # type: ignore[arg-type]
                    outcome="passed",
                    response_excerpt_hash="5" * 64,
                    answer_key_criterion_hash="4" * 64,
                    rationale="The isolated reader recovered the exact requested update.",
                )
                for kind in kinds
            ),
        ),
        reader_response_ref=eref("reader.response"),
        answer_key_artifact_ref=aref("reader.answer.key", "3" * 64),
        adjudicator=actor("critic.cold.adjudicator"),
        reviewed_at=NOW,
    )


def _assurance_bundle(*, exact: bool) -> a.AssuranceBundle:
    obligation_ref = eref("proof.obligation")
    proof_audit = a.ProofAudit(
        audit_id="audit.phase4.fixture",
        claim_graph_ref=eref("claim.graph"),
        claim_id="claim.reversal",
        obligation_ref=obligation_ref,
        formal_model_ref=eref("formal.model"),
        assumption_map_ref=eref("assumption.map"),
        proof_artifact_ref=aref("artifact.proof"),
        verification_record_ref=eref("verification.record"),
        rederivation_ref=eref("rederivation.record"),
        originating_verifier=actor("agent.verifier"),
        auditor=actor("agent.proof.auditor"),
        audit_report_ref=aref("artifact.proof.audit", "b" * 64),
        outcome="passed",
        comparison_outcome="agrees",
        limitations="The proof audit is limited to the exact maintained obligation.",
        audited_at=NOW,
    )
    zero = a.ExactPolynomialSpec()
    if exact:
        evidence: a.SymbolicIdentityEvidence | a.CounterexampleScanEvidence = (
            a.SymbolicIdentityEvidence(
                left=zero,
                right=zero,
                input_hash="1" * 64,
                output_hash="2" * 64,
                left_hash="3" * 64,
                right_hash="3" * 64,
                difference_hash="4" * 64,
                outcome="identity_verified",
                certificate_hash="5" * 64,
            )
        )
        receipt = a.ToolHarnessReceipt(
            receipt_id="receipt.phase4.symbolic",
            harness_kind="symbolic_identity",
            claim_graph_ref=eref("claim.graph"),
            claim_id="claim.reversal",
            obligation_ref=obligation_ref,
            tool_name="fixture.symbolic",
            tool_version="1",
            code_ref=aref("predicate.code", "b" * 64),
            input_ref=aref("predicate.input", "1" * 64),
            output_ref=aref("predicate.output", "2" * 64),
            certificate_ref=aref("predicate.certificate", "5" * 64),
            reproducible_evidence=evidence,
            domain="The exact symbolic identity domain bound by the obligation.",
            outcome="identity_verified",
            evidentiary_role="exact_identity_certificate",
            limitations="The certificate applies only to the exact symbolic identity.",
            executed_at=NOW,
        )
        nonapplicable_family = "counterexample_search"
        reason_code = "covered_by_stronger_exact_argument"
    else:
        evidence = a.CounterexampleScanEvidence(
            predicate=a.PolynomialRelationPredicate(
                left=zero, relation="eq", right=zero
            ),
            cases=(
                a.ExactAssignmentSpec(
                    case_id="case.zero",
                    values=(
                        a.ExactAssignmentValue(
                            variable="x",
                            value=a.ExactRationalValue(numerator=0, denominator=1),
                        ),
                    ),
                ),
            ),
            code_hash="b" * 64,
            input_hash="1" * 64,
            output_hash="2" * 64,
            domain_hash="3" * 64,
            relation_hash="4" * 64,
            checked_count=1,
            outcome="no_counterexample_found",
            receipt_hash="5" * 64,
        )
        receipt = a.ToolHarnessReceipt(
            receipt_id="receipt.phase4.finite",
            harness_kind="counterexample_search",
            claim_graph_ref=eref("claim.graph"),
            claim_id="claim.reversal",
            obligation_ref=obligation_ref,
            tool_name="fixture.finite_scan",
            tool_version="1",
            code_ref=aref("predicate.code", "b" * 64),
            input_ref=aref("predicate.input", "1" * 64),
            output_ref=aref("predicate.output", "2" * 64),
            receipt_ref=aref("predicate.receipt", "5" * 64),
            reproducible_evidence=evidence,
            domain="One finite exact diagnostic case inside the universal obligation.",
            outcome="no_counterexample_found",
            evidentiary_role="corroboration_only",
            limitations="The finite diagnostic cannot prove the universal obligation.",
            executed_at=NOW,
        )
        nonapplicable_family = "symbolic_identity"
        reason_code = "no_algebraic_identity"
    nonapplicable = a.HarnessNonApplicabilityRecord(
        record_id=f"nonapplicable.{nonapplicable_family}",
        family=nonapplicable_family,  # type: ignore[arg-type]
        claim_graph_ref=eref("claim.graph"),
        claim_id="claim.reversal",
        obligation_ref=obligation_ref,
        reason_code=reason_code,  # type: ignore[arg-type]
        explanation="The other harness family adds no admissible exact evidence here.",
        evidence_refs=(obligation_ref,),
        determined_by=actor("agent.assurance"),
    )
    return a.AssuranceBundle(
        package_ref=eref("package.validated"),
        g5_decision_ref=DecisionVersionRef(decision_id="decision.g5", version=1),
        claim_graph_ref=eref("claim.graph"),
        headline_claim_id="claim.reversal",
        formal_model_ref=eref("formal.model"),
        assumption_map_ref=eref("assumption.map"),
        verification_bundle_ref=eref("verification.bundle"),
        rederivation_refs=(eref("rederivation.record"),),
        proof_audits=(proof_audit,),
        tool_receipts=(receipt,),
        tool_non_applicability=(nonapplicable,),
        assembled_by=actor("agent.assurance"),
        route_run_id="run.phase4.assurance",
        route_run_hash="6" * 64,
        context_manifest_hash="7" * 64,
        compiled_context_hash="8" * 64,
        assembled_at=NOW,
    )


def world(
    *, include_closure: bool = True, bounded_partial: bool = False
) -> tuple[Snapshot, dict[str, EntityVersion]]:
    formal, assumptions, obligation, claim_graph, package = _theory_material()
    theory_entities = (
        theory_entity("formal.model", formal),
        theory_entity("assumption.map", assumptions),
        theory_entity("proof.obligation", obligation),
        theory_entity("claim.graph", claim_graph),
        theory_entity("package.validated", package),
    )

    catalog, target_template, stack_template = profile_material()
    overlay = next(card for card in catalog.cards if card.layer_kind == "venue_overlay")
    decisions = (
        decision("decision.theory", "theory_mode", target_template.theory_mode),
        decision("decision.ambition", "ambition", target_template.ambition),
        decision("decision.archetype", "field", target_template.field_key),
        decision("decision.audience", "audience", target_template.primary_audience),
        decision("decision.venue", "venue_overlay", overlay.selection_key),
    )
    _text, _data, _manuscript_ref, unit = manuscript_material(
        writer_packet_hash="2" * 64
    )
    base_span = unit.spans[0]
    formal_span = base_span.model_copy(
        update={
            "assertion_id": "assertion.processing.formal",
            "role": "formal_statement",
            "location": a.ManuscriptLocation(
                start_offset=base_span.location.end_offset,
                end_offset=base_span.location.end_offset + 32,
            ),
            "wording_strength": "exact",
            "presentation": "theorem_statement",
        }
    )
    unit = a.ManuscriptUnit.model_validate(
        {**unit.model_dump(mode="python"), "spans": (*unit.spans, formal_span)}
    )
    minimal_profile = a.ResolvedProfileManifest(
        universal_floor_version="universal.floor.fixture.v1",
        theory_mode=target_template.theory_mode,
        theory_mode_decision_ref=DecisionVersionRef(
            decision_id="decision.phase3.theory", version=1
        ),
        ambition="frontier_general_interest",
        ambition_decision_ref=DecisionVersionRef(
            decision_id="decision.phase3.ambition", version=1
        ),
        primary_result_archetype=target_template.primary_archetype,
        result_archetype_source=SemanticFacetRef(
            entity_id="claim.graph",
            version=1,
            facet="formal",
            field_path="/payload/claims/0/archetype",
            semantic_hash=facet_semantic_hash(
                theory_entities[3], "formal", "/payload/claims/0/archetype"
            ),
        ),
        g4_decision_ref=DecisionVersionRef(
            decision_id="decision.phase3.g4", version=1
        ),
        primary_audience="economic_theorist",
        audience_decision_ref=DecisionVersionRef(
            decision_id="decision.phase3.audience", version=1
        ),
        source_state_revision=HEAD,
        profile_artifact_ref=aref("artifact.profile.phase3", "2" * 64),
        projection_hash="3" * 64,
        resolved_at=NOW,
    )
    paper_template = paper_ir(mode="working")
    paper = a.PaperIR.model_validate(
        {
            **paper_template.model_dump(mode="python"),
            "package_ref": eref("package.validated"),
            "resolved_profile_manifest_ref": eref("profile.universal"),
            "canonical_writer": unit.canonical_writer,
        }
    )
    reader_template = reader_path()
    reader = a.ReaderPath.model_validate(
        {
            **reader_template.model_dump(mode="python"),
            "paper_ir_ref": eref("entity.paper"),
        }
    )
    contracts = _result_contracts(paper)
    paper_entity = authoring_entity("entity.paper", paper)
    contracts_entity = authoring_entity("entity.result.contracts", contracts)
    benchmark_source = SemanticFacetRef(
        entity_id="entity.paper",
        version=1,
        facet="terminology_presentation",
        field_path="/payload/narrative_spine/natural_benchmark",
        semantic_hash=facet_semantic_hash(
            paper_entity,
            "terminology_presentation",
            "/payload/narrative_spine/natural_benchmark",
        ),
    )
    mechanism_source = SemanticFacetRef(
        entity_id="entity.result.contracts",
        version=1,
        facet="terminology_presentation",
        field_path="/payload/result_packets/0/archetype_module/initiating_force/content",
        semantic_hash=facet_semantic_hash(
            contracts_entity,
            "terminology_presentation",
            "/payload/result_packets/0/archetype_module/initiating_force/content",
        ),
    )
    target = pc.TargetProfile.model_validate(
        {
            **target_template.model_dump(mode="python"),
            "package_ref": eref("package.validated"),
            "package_hash": object_digest(package),
            "paper_ir_ref": eref("entity.paper"),
            "paper_ir_hash": object_digest(paper),
            "reader_path_ref": eref("entity.reader.path"),
            "reader_path_hash": object_digest(reader),
            "base_profile_manifest_ref": eref("profile.universal"),
            "base_profile_manifest_hash": object_digest(minimal_profile),
            "source_state_revision": HEAD,
            "human_decision_refs": tuple(
                DecisionVersionRef(decision_id=item.decision_id, version=item.version)
                for item in decisions
            ),
            "selected_by": HUMAN,
        }
    )
    stack = resolve_profile_stack(
        target,
        target_profile_ref=eref("target.profile"),
        source_state_revision=HEAD,
        resolved_by=stack_template.resolved_by,
        resolved_at=stack_template.resolved_at,
        catalog=catalog,
    )
    old_artifact = aref("artifact.manuscript.diagnosed", "0" * 64)
    old_unit = unit.model_copy(
        update={
            "unit_id": "unit.processing.response.diagnosed",
            "manuscript_artifact_ref": old_artifact,
            "writer_output_hash": old_artifact.content_hash,
        }
    )
    finding_ref = eref("finding.economic.diagnosed")
    failed_review = _economic_review(
        old_unit,
        contracts,
        unit_ref=eref("diagnosed.manuscript.unit"),
        passed=False,
        finding_ref=finding_ref,
    )
    finding = a.ReviewFinding(
        finding_id="finding.economic.diagnosed",
        assignment_ref=failed_review.assignment_ref,
        manuscript_unit_ref=eref("diagnosed.manuscript.unit"),
        reviewed_artifact_ref=old_unit.manuscript_artifact_ref,
        role="economic_reader",
        critic=failed_review.reviewer,
        category="economic_explanation",
        severity="error",
        assertion_ids=(old_unit.spans[0].assertion_id,),
        evidence_refs=(
            eref("diagnosed.manuscript.unit"),
            old_unit.manuscript_artifact_ref,
        ),
        summary="The reader cannot recover the benchmark-to-mechanism transition.",
        recommended_repair="Expose the fixed benchmark before the operative uptake force.",
        blocking=True,
        reported_at=NOW,
    )
    old_formal_review = _formal_review(
        old_unit,
        unit_ref=eref("diagnosed.manuscript.unit"),
        assignment_ref=eref("assignment.formal.diagnosed"),
    )
    old_cold_review = _cold_review(
        old_unit,
        unit_ref=eref("diagnosed.manuscript.unit"),
        assignment_ref=eref("assignment.cold.diagnosed"),
    )
    blocked_closure_ref = eref("review.closure.diagnosed")
    brief_ref = eref("revision.brief.diagnosed")
    blocked_checks = tuple(
        item.model_copy(update={"outcome": "failed"})
        if item.check_id in {"economic_explanation", "blocking_findings"}
        else item
        for item in _base_authoring_closure(
            eref("diagnosed.manuscript.unit")
        ).checks
    )
    blocked_closure = a.ReviewClosure(
        compiler_mode="working",
        paper_ir_ref=eref("entity.paper"),
        reader_path_ref=eref("entity.reader.path"),
        result_contract_set_ref=eref("entity.result.contracts"),
        assurance_bundle_ref=eref("assurance.bundle"),
        manuscript_unit_ref=eref("diagnosed.manuscript.unit"),
        formal_fidelity_review_ref=eref("review.formal.diagnosed"),
        economic_reader_review_ref=eref("review.economic.diagnosed"),
        cold_reader_review_ref=eref("review.cold.diagnosed"),
        closure_actor=Actor(
            kind="deterministic_tool", actor_id="tool.phase3.closer"
        ),
        checks=blocked_checks,
        blocking_finding_ids=(finding.finding_id,),
        revision_brief_ref=brief_ref,
        status="blocked",
        evaluated_at=NOW,
    )
    brief = a.RevisionBrief(
        manuscript_unit_ref=eref("diagnosed.manuscript.unit"),
        review_closure_ref=blocked_closure_ref,
        finding_refs=(finding_ref,),
        instructions=(
            a.RevisionInstruction(
                instruction_id="instruction.repair.explanation",
                finding_ref=finding_ref,
                action="repair_explanation",
                requirement="Expose the fixed benchmark before the operative uptake force.",
                blocking=True,
            ),
        ),
        brief_artifact_ref=aref("artifact.revision.brief.diagnosed", "8" * 64),
        prepared_by=CLOSER,
        prepared_at=NOW,
    )
    brief_entity = authoring_entity(brief_ref.entity_id, brief)
    resolution_requirement = pc.ResolutionRequirement(
        requirement_id=brief.instructions[0].instruction_id,
        finding_ref=finding_ref,
        action=brief.instructions[0].action,
        instruction_source=SemanticFacetRef(
            entity_id=brief_ref.entity_id,
            version=brief_ref.version,
            facet="authority",
            field_path="/payload/instructions/0",
            semantic_hash=facet_semantic_hash(
                brief_entity, "authority", "/payload/instructions/0"
            ),
        ),
        affected_assertion_ids=finding.assertion_ids,
        affected_section_ids=(old_unit.section_contract_id,),
        required_semantic_input_ids=("input.benchmark", "input.mechanism"),
    )
    problem_template = diagnosis(stack)
    problem = pc.ReaderProblemDiagnosis.model_validate(
        {
            **problem_template.model_dump(mode="python"),
            "paper_ir_ref": eref("entity.paper"),
            "paper_ir_hash": object_digest(paper),
            "reader_path_ref": eref("entity.reader.path"),
            "reader_path_hash": object_digest(reader),
            "profile_stack_ref": eref("profile.stack"),
            "profile_stack_hash": object_digest(stack),
            "result_contract_set_binding": pc.ProjectPayloadBinding(
                entity_ref=eref("entity.result.contracts"),
                payload_hash=object_digest(contracts),
            ),
            "inspected_manuscript_unit_binding": pc.ProjectPayloadBinding(
                entity_ref=eref("diagnosed.manuscript.unit"),
                payload_hash=object_digest(old_unit),
            ),
            "no_prior_manuscript_unit_reason": None,
            "diagnostic_review_bindings": (
                pc.ProjectPayloadBinding(
                    entity_ref=eref("review.economic.diagnosed"),
                    payload_hash=object_digest(failed_review),
                ),
            ),
            "diagnostic_finding_bindings": (
                pc.ProjectPayloadBinding(
                    entity_ref=finding_ref,
                    payload_hash=object_digest(finding),
                ),
            ),
            "blocked_review_closure_binding": pc.ProjectPayloadBinding(
                entity_ref=blocked_closure_ref,
                payload_hash=object_digest(blocked_closure),
            ),
            "revision_brief_binding": pc.ProjectPayloadBinding(
                entity_ref=brief_ref,
                payload_hash=object_digest(brief),
            ),
            "no_prior_review_reason": None,
            "diagnostic_categories": (finding.category,),
            "affected_section_roles": (reader.section_contracts[0].role,),
            "causal_class": "local_exposition",
            "resolution_requirements": (resolution_requirement,),
            "semantic_input_bindings": (
                pc.SemanticInputBinding(
                    input_id="input.benchmark",
                    source_ref=benchmark_source,
                    source_kind="paper_ir",
                    availability="available",
                    explanation="The accepted PaperIR fixes the exact natural benchmark.",
                ),
                pc.SemanticInputBinding(
                    input_id="input.mechanism",
                    source_ref=mechanism_source,
                    source_kind="result_contract",
                    availability="available",
                    explanation="The accepted ResultContractSet fixes the operative mechanism.",
                ),
            ),
            "affected_section_ids": (old_unit.section_contract_id,),
            "required_resolution_ids": (resolution_requirement.requirement_id,),
            "required_semantic_input_ids": (
                "input.benchmark",
                "input.mechanism",
            ),
            "evidence_refs": (
                eref("entity.paper"),
                eref("entity.reader.path"),
                eref("profile.stack"),
                eref("entity.result.contracts"),
                eref("diagnosed.manuscript.unit"),
                eref("review.economic.diagnosed"),
                finding_ref,
                blocked_closure_ref,
                brief_ref,
            ),
        }
    )
    selection_template, _ = selection_material()
    corpus, _move, _decoy = craft_material()
    selection = select_craft_moves(
        problem,
        diagnosis_ref=eref("diagnosis.reader.problem"),
        profile_stack=stack,
        profile_stack_ref=eref("profile.stack"),
        selected_by=selection_template.selected_by,
        selected_at=selection_template.selected_at,
        corpus=corpus,
    )

    assurance = _assurance_bundle(exact=not bounded_partial)
    receipt = assurance.tool_receipts[0]
    exact_contract_template = predicate_contract()
    contract_template = (
        pc.ObligationPredicateContract.model_validate(
            {
                **exact_contract_template.model_dump(mode="python"),
                "domain_relation": "narrowed",
                "quantifier_relation": "weakened",
                "execution_scope": "finite_sample",
                "coverage_class": "diagnostic",
            }
        )
        if bounded_partial
        else exact_contract_template
    )
    contract = pc.ObligationPredicateContract.model_validate(
        {
            **contract_template.model_dump(mode="python"),
            "assurance_bundle_ref": eref("assurance.bundle"),
            "assurance_bundle_hash": object_digest(assurance),
            "receipt_id": receipt.receipt_id,
            "receipt_hash": object_digest(receipt),
            "obligation_hash": object_digest(obligation),
            "claim_graph_hash": object_digest(claim_graph),
            "formal_model_hash": object_digest(formal),
            "assumption_map_hash": object_digest(assumptions),
            "predicate_artifact_ref": receipt.input_ref,
            "code_ref": receipt.code_ref,
        }
    )
    exact_audit_template = mapping_audit(exact_contract_template)
    audit = pc.PredicateMappingAudit.model_validate(
        {
            **exact_audit_template.model_dump(mode="python"),
            "contract_ref": eref("predicate.contract"),
            "contract_hash": object_digest(contract),
            "contract_coverage_class": contract.coverage_class,
            "falsifying_witness_verified": not bounded_partial,
            "findings": (
                (
                    pc.PredicateMappingFinding(
                        finding_id="finding.predicate.bounded.limitations",
                        severity="warning",
                        summary="The finite diagnostic remains explicitly below exact predicate assurance.",
                        limitation_kinds=(
                            "domain_not_equal",
                            "quantifier_not_equivalent",
                            "bounded_execution_scope",
                            "coverage_below_exact",
                            "nonvacuity_unverified",
                        ),
                    ),
                )
                if bounded_partial
                else ()
            ),
            "verdict": "approved_partial" if bounded_partial else "approved_exact",
        }
    )
    formal_review = _formal_review(unit)
    economic_review = _economic_review(
        unit,
        contracts,
        unit_ref=eref("manuscript.unit"),
        passed=True,
    )
    cold_review = _cold_review(unit)
    base = _base_authoring_closure(eref("manuscript.unit"))
    assessment_template = realization(selection)
    assessment_evidence = (
        eref("craft.selection"),
        eref("diagnosis.reader.problem"),
        eref("profile.stack"),
        eref("manuscript.unit"),
        unit.manuscript_artifact_ref,
        eref("authoring.review.closure"),
        eref("review.formal"),
        eref("review.economic"),
        eref("review.cold"),
        eref("entity.reader.path"),
        eref("entity.result.contracts"),
    )
    realized = tuple(
        pc.CraftMoveRealization(
            move_ref=candidate.move_ref,
            realized_assertion_ids=(unit.spans[0].assertion_id,),
            realized_semantic_input_ids=candidate.move.required_semantic_inputs,
            realized_semantic_source_refs=tuple(
                binding.source_ref
                for input_id in candidate.move.required_semantic_inputs
                for binding in problem.semantic_input_bindings
                if binding.input_id == input_id and binding.source_ref is not None
            ),
            realized_function=True,
            intended_reader_update_delivered=True,
            formal_fidelity_preserved=True,
            evidence_refs=assessment_evidence,
            explanation="The exact reviewed manuscript realizes the selected reader function.",
        )
        for candidate in selection.candidates
        if candidate.selected
    )
    realized_roles = tuple(dict.fromkeys(item.role for item in unit.spans))
    observed_signals = (
        "formal_fidelity",
        "scope_and_assumptions",
        "bounded_evidentiary_language",
        "economic_explanation",
        "cold_reader_transfer",
    )
    active_directives = tuple(
        item
        for item in stack.directive_resolutions
        if item.outcome == "active" and item.directive.strength != "soft"
    )
    directive_checks = tuple(
        pc.DirectiveAcceptanceCheck(
            directive_id=item.directive.directive_id,
            criterion_id=item.directive.acceptance_criterion.criterion_id,
            required_assertion_roles=(
                item.directive.acceptance_criterion.required_assertion_roles
            ),
            realized_assertion_roles=realized_roles,
            required_review_signals=(
                item.directive.acceptance_criterion.required_review_signals
            ),
            observed_review_signals=observed_signals,
            outcome="pass",
            evidence_refs=assessment_evidence,
            explanation="The exact manuscript and independent reviews satisfy this resolved directive.",
        )
        for item in active_directives
    )
    resolution_checks = tuple(
        pc.ResolutionRequirementCheck(
            requirement_id=requirement.requirement_id,
            repair_action=requirement.action,
            realizing_move_refs=tuple(
                candidate.move_ref
                for candidate in selection.candidates
                if candidate.selected
                and requirement.requirement_id
                in candidate.covered_requirement_ids
            ),
            affected_assertion_ids=requirement.affected_assertion_ids,
            affected_section_ids=requirement.affected_section_ids,
            required_semantic_input_ids=(
                requirement.required_semantic_input_ids
            ),
            realized_semantic_input_ids=tuple(
                dict.fromkeys(
                    input_id
                    for realization_item in realized
                    for input_id in realization_item.realized_semantic_input_ids
                )
            ),
            outcome="pass",
            evidence_refs=assessment_evidence,
            explanation="The selected move realizes every exact semantic input in the RevisionBrief repair.",
        )
        for requirement in problem.resolution_requirements
    )
    target_reader_evidence = (
        eref("manuscript.unit"),
        unit.manuscript_artifact_ref,
        eref("review.economic"),
        eref("review.cold"),
        eref("entity.reader.path"),
        eref("entity.result.contracts"),
    )
    target_reader_outcome = pc.TargetReaderOutcome(
        primary_audience=target.primary_audience,
        benchmark_delta_reconstructible=True,
        operative_force_reconstructible=True,
        boundary_reconstructible=True,
        nearby_case_predictable=True,
        outcome="pass",
        evidence_refs=target_reader_evidence,
        explanation="The independent economic and cold readers reconstruct the benchmark, force, boundary, and transfer.",
    )
    assessment = pc.CraftRealizationAssessment.model_validate(
        {
            **assessment_template.model_dump(mode="python"),
            "selection_manifest_ref": eref("craft.selection"),
            "selection_manifest_hash": object_digest(selection),
            "profile_stack_ref": eref("profile.stack"),
            "profile_stack_hash": object_digest(stack),
            "reader_problem_diagnosis_ref": eref("diagnosis.reader.problem"),
            "reader_problem_diagnosis_hash": object_digest(problem),
            "reader_path_ref": eref("entity.reader.path"),
            "reader_path_hash": object_digest(reader),
            "result_contract_set_ref": eref("entity.result.contracts"),
            "result_contract_set_hash": object_digest(contracts),
            "primary_audience": target.primary_audience,
            "manuscript_unit_ref": eref("manuscript.unit"),
            "manuscript_unit_hash": object_digest(unit),
            "manuscript_artifact_ref": unit.manuscript_artifact_ref,
            "base_authoring_closure_ref": eref("authoring.review.closure"),
            "base_authoring_closure_hash": object_digest(base),
            "formal_fidelity_review_ref": eref("review.formal"),
            "formal_fidelity_review_hash": object_digest(formal_review),
            "economic_reader_review_ref": eref("review.economic"),
            "economic_reader_review_hash": object_digest(economic_review),
            "cold_reader_review_ref": eref("review.cold"),
            "cold_reader_review_hash": object_digest(cold_review),
            "writer": unit.canonical_writer,
            "move_realizations": realized,
            "required_directive_ids": tuple(
                item.directive.directive_id for item in active_directives
            ),
            "directive_acceptance_checks": directive_checks,
            "required_resolution_ids": problem.required_resolution_ids,
            "resolution_requirement_checks": resolution_checks,
            "target_reader_outcome": target_reader_outcome,
        }
    )
    closure_checks = tuple(
        pc.ProfileCraftClosureCheck(
            check_id=f"closure.check.{kind}",
            check_kind=kind,
            outcome="pass",
            evidence_refs=(
                (
                    eref("craft.assessment"),
                    *target_reader_outcome.evidence_refs,
                )
                if kind == "target_reader_fit"
                else (
                    (eref("craft.assessment"),)
                    if kind == "craft_realization"
                    else (eref("manuscript.unit"),)
                )
            ),
            explanation=f"The exact {kind} profile/craft requirement passed.",
        )
        for kind in pc.PROFILE_CRAFT_READY_CHECK_ORDER
    )
    closure = pc.ProfileCraftClosure(
        closure_id="profile.craft.closure",
        base_authoring_closure_ref=eref("authoring.review.closure"),
        base_authoring_closure_hash=object_digest(base),
        base_authoring_closure_outcome="authoring_ready",
        manuscript_unit_ref=eref("manuscript.unit"),
        manuscript_unit_hash=object_digest(unit),
        reader_problem_diagnosis_ref=eref("diagnosis.reader.problem"),
        reader_problem_diagnosis_hash=object_digest(problem),
        profile_stack=pc.ProjectPayloadBinding(
            entity_ref=eref("profile.stack"), payload_hash=object_digest(stack)
        ),
        craft_selection=pc.ProjectPayloadBinding(
            entity_ref=eref("craft.selection"), payload_hash=object_digest(selection)
        ),
        predicate_mapping_audits=(
            pc.ProjectPayloadBinding(
                entity_ref=eref("predicate.audit"), payload_hash=object_digest(audit)
            ),
        ),
        predicate_mapping_coverage_classes=(audit.contract_coverage_class,),
        predicate_limitation_kinds=(
            (
                "domain_not_equal",
                "quantifier_not_equivalent",
                "bounded_execution_scope",
                "coverage_below_exact",
                "nonvacuity_unverified",
            )
            if bounded_partial
            else ()
        ),
        realization_assessment=pc.ProjectPayloadBinding(
            entity_ref=eref("craft.assessment"),
            payload_hash=object_digest(assessment),
        ),
        source_state_revision=HEAD,
        all_dependencies_current_and_fresh=True,
        checks=closure_checks,
        outcome="ready",
        determined_by=CLOSER,
        determined_at=NOW,
    )

    profile_payloads: tuple[tuple[str, pc.ProfileCraftPayload], ...] = (
        ("profile.catalog.release", catalog),
        ("target.profile", target),
        ("profile.stack", stack),
        ("craft.corpus.release", corpus),
        ("diagnosis.reader.problem", problem),
        ("craft.selection", selection),
        ("predicate.contract", contract),
        ("predicate.audit", audit),
        ("craft.assessment", assessment),
        *(((("profile.craft.closure", closure),) if include_closure else ())),
    )
    authoring_entities = (
        authoring_entity("assurance.bundle", assurance),
        authoring_entity("profile.universal", minimal_profile),
        paper_entity,
        authoring_entity("entity.reader.path", reader),
        contracts_entity,
        authoring_entity("diagnosed.manuscript.unit", old_unit),
        authoring_entity("review.formal.diagnosed", old_formal_review),
        authoring_entity("review.economic.diagnosed", failed_review),
        authoring_entity("review.cold.diagnosed", old_cold_review),
        authoring_entity("finding.economic.diagnosed", finding),
        authoring_entity("review.closure.diagnosed", blocked_closure),
        brief_entity,
        authoring_entity("manuscript.unit", unit),
        authoring_entity("review.formal", formal_review),
        authoring_entity("review.economic", economic_review),
        authoring_entity("review.cold", cold_review),
        authoring_entity("authoring.review.closure", base),
    )
    profile_entities = tuple(
        pc_entity(entity_id, payload) for entity_id, payload in profile_payloads
    )
    entities = (*theory_entities, *authoring_entities, *profile_entities)
    all_artifact_refs = {
        reference
        for entity in profile_entities
        for reference in entity.artifact_refs
    }
    artifacts = tuple(
        registration(reference)
        for reference in sorted(
            all_artifact_refs,
            key=lambda item: (item.artifact_id, item.version),
        )
    )
    effective = {
        item.decision_kind: EffectiveDecisionRef(
            decision_id=item.decision_id,
            version=item.version,
            effective_revision=HEAD,
        )
        for item in decisions
    }
    snapshot = Snapshot(
        project_id=PROJECT,
        head=HEAD,
        chain=(HEAD,),
        entity_versions=entities,
        decisions=decisions,
        artifacts=artifacts,
        current_entities={item.entity_id: item.version for item in entities},
        current_decisions={item.decision_id: item.version for item in decisions},
        current_artifacts={item.artifact_id: item.version for item in artifacts},
        effective_decisions=effective,
    )
    return snapshot, {item.entity_id: item for item in entities}


def relation(
    relation_id: str,
    relation_type: str,
    source: EntityVersion,
    target: EntityVersion,
) -> RelationVersion:
    source_owner = pc.PROFILE_CRAFT_PAYLOAD_OWNER_FACETS.get(
        source.entity_type
    ) or a.AUTHORING_PAYLOAD_OWNER_FACETS.get(
        source.entity_type
    ) or t.THEORY_PAYLOAD_OWNER_FACETS.get(source.entity_type)
    target_owner = pc.PROFILE_CRAFT_PAYLOAD_OWNER_FACETS.get(
        target.entity_type
    ) or a.AUTHORING_PAYLOAD_OWNER_FACETS.get(
        target.entity_type
    ) or t.THEORY_PAYLOAD_OWNER_FACETS.get(target.entity_type)
    assert source_owner is not None and target_owner is not None
    return RelationVersion(
        relation_id=relation_id,
        relation_type=relation_type,
        version=1,
        project_id=PROJECT,
        source=eref(source.entity_id),
        target=eref(target.entity_id),
        dependency_mode="hard",
        upstream=SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet=source_owner,  # type: ignore[arg-type]
            semantic_hash=facet_semantic_hash(source, source_owner),  # type: ignore[arg-type]
        ),
        downstream=FacetPathRef(
            entity_id=target.entity_id,
            version=target.version,
            facet=target_owner,  # type: ignore[arg-type]
        ),
        created_at=NOW,
    )


class ProfileCraftEntityAndProjectionTests(unittest.TestCase):
    def test_pinned_catalog_and_corpus_are_policy_resources_not_snapshot_entities(self) -> None:
        snapshot = Snapshot(project_id=PROJECT, head=HEAD, chain=(HEAD,))
        indices = _build_indices(snapshot)
        catalog = load_profile_catalog()
        corpus = load_craft_corpus()

        self.assertFalse(indices.entities)
        self.assertIs(indices.static_resources[pc.static_resource_ref(catalog)], catalog)
        self.assertIs(indices.static_resources[pc.static_resource_ref(corpus)], corpus)
        for resource in (*catalog.cards, *corpus.source_cards, *corpus.moves):
            self.assertEqual(
                indices.static_resources[pc.static_resource_ref(resource)], resource
            )

    def test_envelope_exposes_every_artifact_and_projection_resolves_it(self) -> None:
        corpus, _move, _decoy = craft_material()
        source = corpus.source_cards[0]
        packed = pc_entity("source.card", source)
        self.assertEqual(validate_profile_craft_entity(packed), source)

        hidden = packed.model_copy(update={"artifact_refs": ()})
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "every and only exact artifact"
        ):
            validate_profile_craft_entity(hidden)

        artifacts = tuple(registration(item) for item in packed.artifact_refs)
        snapshot = Snapshot(
            project_id=PROJECT,
            head=HEAD,
            chain=(HEAD,),
            entity_versions=(packed,),
            artifacts=artifacts,
            current_entities={packed.entity_id: 1},
            current_artifacts={item.artifact_id: 1 for item in artifacts},
        )
        self.assertEqual(validate_profile_craft_projection(snapshot).parsed_entity_count, 1)
        missing = snapshot.model_copy(update={"artifacts": (), "current_artifacts": {}})
        with self.assertRaisesRegex(ProfileCraftValidationError, "unresolved.*artifact"):
            validate_profile_craft_projection(missing)

    def test_target_profile_matches_exact_current_effective_human_l2_decisions(self) -> None:
        snapshot, entities = world()
        target = pc.parse_profile_craft_entity(entities["target.profile"])
        assert isinstance(target, pc.TargetProfile)
        validate_target_profile(snapshot, target, require_current=True)

        mismatched = target.model_copy(update={"theory_mode": "pure_theory"})
        with self.assertRaisesRegex(ProfileCraftValidationError, "theory_mode"):
            validate_target_profile(snapshot, mismatched, require_current=True)

        stale_current = dict(snapshot.current_decisions)
        stale_current["decision.theory"] = 2
        stale = snapshot.model_copy(update={"current_decisions": stale_current})
        with self.assertRaisesRegex(ProfileCraftValidationError, "current and effective"):
            validate_target_profile(stale, target, require_current=True)

        stale_source = snapshot.model_copy(
            update={
                "derived_status": {
                    "entity.paper": EntityDerivedStatus(
                        freshness={"terminology_presentation": "stale"}
                    )
                }
            }
        )
        with self.assertRaisesRegex(ProfileCraftValidationError, "exact PaperIR source"):
            validate_target_profile(stale_source, target, require_current=True)

    def test_full_projection_resolves_hashes_and_cross_object_topology(self) -> None:
        snapshot, entities = world()
        report = validate_profile_craft_projection(snapshot)
        self.assertEqual(report.parsed_entity_count, 10)
        self.assertEqual(
            report.ready_closure_refs, (eref("profile.craft.closure"),)
        )

        audit_entity = entities["predicate.audit"]
        audit = pc.parse_profile_craft_entity(audit_entity)
        assert isinstance(audit, pc.PredicateMappingAudit)
        forged = pc_entity(
            audit_entity.entity_id,
            audit.model_copy(update={"contract_hash": "0" * 64}),
        )
        replaced = tuple(
            forged if item.entity_id == audit_entity.entity_id else item
            for item in snapshot.entity_versions
        )
        tampered = snapshot.model_copy(update={"entity_versions": replaced})
        with self.assertRaisesRegex(ProfileCraftValidationError, "contract_hash"):
            validate_profile_craft_projection(tampered)


class ProfileCraftReadinessAndRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = load_route_registry_by_hash(ROUTE_REGISTRY_V4_HASH)
        self.routes = {item.route_id: item for item in self.registry.routes}

    def test_ready_closure_wraps_current_fresh_phase3_ready_and_passed_reviews(self) -> None:
        snapshot, _entities = world()
        with mock.patch(
            "econ_theorist.profile_craft_validation.validate_authoring_ready"
        ) as phase3_ready:
            validate_profile_craft_ready(snapshot, eref("profile.craft.closure"))
        phase3_ready.assert_called_once_with(
            snapshot, eref("authoring.review.closure")
        )

        stale_status = EntityDerivedStatus(
            freshness={"terminology_presentation": "stale"}
        )
        stale = snapshot.model_copy(
            update={
                "derived_status": {"craft.assessment": stale_status},
            }
        )
        with self.assertRaisesRegex(ProfileCraftValidationError, "stale dependency"):
            validate_profile_craft_ready(stale, eref("profile.craft.closure"))

    def test_finite_partial_mapping_is_admissible_but_cannot_become_exact(self) -> None:
        snapshot, entities = world(bounded_partial=True)
        audit = pc.parse_profile_craft_entity(entities["predicate.audit"])
        contract = pc.parse_profile_craft_entity(entities["predicate.contract"])
        assurance = a.parse_authoring_entity(entities["assurance.bundle"])
        assert isinstance(audit, pc.PredicateMappingAudit)
        assert isinstance(contract, pc.ObligationPredicateContract)
        assert isinstance(assurance, a.AssuranceBundle)
        self.assertEqual(audit.verdict, "approved_partial")
        self.assertTrue(audit_is_approved_bounded(audit))
        with mock.patch(
            "econ_theorist.profile_craft_validation.validate_authoring_ready"
        ):
            validate_profile_craft_ready(snapshot, eref("profile.craft.closure"))

        upgraded = contract.model_copy(
            update={"coverage_class": "exact", "execution_scope": "symbolic_exact"}
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "finite harness evidence cannot claim"
        ):
            _validate_contract_receipt_bound(assurance, upgraded)

        blocking = pc.PredicateMappingFinding(
            finding_id="finding.bounded.error",
            severity="error",
            summary="The bounded diagnostic omits a required universal-domain case.",
        )
        self.assertFalse(
            audit_is_approved_bounded(audit.model_copy(update={"findings": (blocking,)}))
        )

    def test_all_eight_route_entries_enforce_cardinality_and_close_actor(self) -> None:
        empty = Snapshot(project_id=PROJECT, head=HEAD, chain=(HEAD,))
        for route_id in (
            "map.obligation_predicate",
            "audit.obligation_predicate",
            "resolve.profile_stack",
            "diagnose.reader_problem",
            "retrieve.craft_moves",
            "compose.profiled_manuscript_unit",
            "review.craft_realization",
            "close.profile_craft_review",
        ):
            with self.subTest(route=route_id), self.assertRaisesRegex(
                ProfileCraftValidationError, "cardinality"
            ):
                validate_phase4_route_entry(
                    empty,
                    self.routes[route_id],
                    (),
                    actor=CLOSER,
                )

        snapshot, entities = world()
        close_focus = tuple(
            entities[entity_id].entity_id
            for entity_id in (
                "craft.assessment",
                "craft.selection",
                "manuscript.unit",
                "predicate.audit",
                "diagnosis.reader.problem",
                "profile.stack",
                "authoring.review.closure",
            )
        )
        report = validate_phase4_route_entry(
            snapshot,
            self.routes["close.profile_craft_review"],
            close_focus,
            actor=CLOSER,
        )
        self.assertEqual(report.route_id, "close.profile_craft_review")
        with self.assertRaisesRegex(ProfileCraftValidationError, "deterministic actor"):
            validate_phase4_route_entry(
                snapshot,
                self.routes["close.profile_craft_review"],
                close_focus,
                actor=actor("agent.not.closer"),
            )

        stale = snapshot.model_copy(
            update={
                "derived_status": {
                    "authoring.review.closure": EntityDerivedStatus(
                        freshness={"authority": "stale"}
                    )
                }
            }
        )
        with self.assertRaisesRegex(ProfileCraftValidationError, "current and fresh"):
            validate_phase4_route_entry(
                stale,
                self.routes["close.profile_craft_review"],
                close_focus,
                actor=CLOSER,
            )

    def test_craft_review_requires_exact_reader_and_contract_inputs(self) -> None:
        snapshot, entities = world()
        focus = tuple(
            entities[entity_id].entity_id
            for entity_id in (
                "craft.selection",
                "manuscript.unit",
                "entity.paper",
                "entity.reader.path",
                "entity.result.contracts",
                "diagnosis.reader.problem",
                "profile.stack",
                "authoring.review.closure",
                "review.formal",
                "review.economic",
                "review.cold",
            )
        )
        report = validate_phase4_route_entry(
            snapshot,
            self.routes["review.craft_realization"],
            focus,
            actor=actor("agent.independent.craft.reviewer"),
        )
        self.assertEqual(report.route_id, "review.craft_realization")
        self.assertIn("entity.reader.path", focus)
        self.assertIn("entity.result.contracts", focus)

    def test_close_transaction_enforces_output_cardinality_and_exact_topology(self) -> None:
        base, entities = world(include_closure=False)
        full, full_entities = world(include_closure=True)
        del full
        closure_entity = full_entities["profile.craft.closure"]
        base_relation = relation(
            "relation.base.validates.profile.craft",
            "validates",
            entities["authoring.review.closure"],
            closure_entity,
        )
        assessment_relation = relation(
            "relation.assessment.validates.profile.craft",
            "validates",
            entities["craft.assessment"],
            closure_entity,
        )
        dependency_relations = tuple(
            relation(
                f"relation.{source_id}.depends.profile.craft",
                "depends_on",
                entities[source_id],
                closure_entity,
            )
            for source_id in (
                "manuscript.unit",
                "diagnosis.reader.problem",
                "profile.stack",
                "craft.selection",
                "predicate.audit",
            )
        )
        focus_ids = (
            "craft.assessment",
            "craft.selection",
            "manuscript.unit",
            "predicate.audit",
            "diagnosis.reader.problem",
            "profile.stack",
            "authoring.review.closure",
        )
        evidence = tuple(eref(item) for item in focus_ids)
        candidate_refs = (
            eref(closure_entity.entity_id),
            RelationVersionRef(
                relation_id=base_relation.relation_id, version=base_relation.version
            ),
            RelationVersionRef(
                relation_id=assessment_relation.relation_id,
                version=assessment_relation.version,
            ),
            *(
                RelationVersionRef(
                    relation_id=item.relation_id, version=item.version
                )
                for item in dependency_relations
            ),
        )
        transaction = Transaction(
            transaction_id="transaction.phase4.close",
            origin="route_run",
            project_id=PROJECT,
            base_revision=HEAD,
            route_run_id="run.phase4.close",
            route_id="close.profile_craft_review",
            route_run_hash="1" * 64,
            context_manifest_hash="2" * 64,
            compiled_context_hash="3" * 64,
            actor=CLOSER,
            intent="Close the exact current profile/craft review chain.",
            operations=(
                CreateEntityOp(entity=closure_entity),
                CreateRelationOp(relation=base_relation),
                CreateRelationOp(relation=assessment_relation),
                *(CreateRelationOp(relation=item) for item in dependency_relations),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id="run.phase4.close",
                        route_id="close.profile_craft_review",
                        outcome="completed_with_candidate",
                        rationale="The exact noncompensatory closure was derived.",
                        candidate_refs=candidate_refs,
                    )
                ),
            ),
            evidence_refs=evidence,
            created_at=NOW,
            parent_transaction_hash=HEAD,
        )
        with mock.patch(
            "econ_theorist.profile_craft_validation.validate_authoring_ready"
        ):
            result = validate_phase4_route_transaction(
                base,
                transaction,
                self.routes["close.profile_craft_review"],
            )
        self.assertIn(eref("profile.craft.closure"), result.ready_closure_refs)

        missing_output = transaction.model_copy(
            update={
                "operations": (
                    RecordRouteOutcomeOp(
                        outcome=RouteOutcome(
                            route_run_id="run.phase4.close",
                            route_id="close.profile_craft_review",
                            outcome="failed",
                            rationale="No closure output was produced.",
                        )
                    ),
                )
            }
        )
        with self.assertRaisesRegex(ProfileCraftValidationError, "cardinality"):
            validate_phase4_route_transaction(
                base,
                missing_output,
                self.routes["close.profile_craft_review"],
            )

    def test_profile_presentation_relation_cannot_invalidate_scientific_source(self) -> None:
        snapshot, entities = world()
        malicious = relation(
            "relation.profile.pollutes.claim",
            "depends_on",
            entities["profile.stack"],
            entities["claim.graph"],
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "cannot invalidate scientific sources"
        ):
            _validate_relation_semantics(
                malicious,
                {
                    (item.entity_id, item.version): item
                    for item in snapshot.entity_versions
                },
                frozenset({eref("profile.stack")}),
            )


if __name__ == "__main__":
    unittest.main()
