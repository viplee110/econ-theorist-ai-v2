"""Focused executable invariants for the independent Phase 4 contracts."""

from __future__ import annotations

import unittest

from pydantic import ValidationError
from tests.helpers import REPOSITORY_ROOT  # noqa: F401

from econ_theorist.codec import canonical_json_bytes, object_digest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    DecisionVersionRef,
    EntityVersionRef,
    SemanticFacetRef,
)
from econ_theorist.profile_craft import (
    PROFILE_CRAFT_PAYLOAD_MODELS,
    PROFILE_CRAFT_READY_CHECK_ORDER,
    CraftCandidateAudit,
    CraftCorpusRelease,
    CraftMove,
    CraftMoveRealization,
    CraftRealizationAssessment,
    CraftSelectionManifest,
    CraftSourceCard,
    DirectiveAcceptanceCheck,
    DirectiveAcceptanceCriterion,
    ObligationPredicateContract,
    PredicateClauseMapping,
    PredicateMappingAudit,
    PredicateMappingFinding,
    PredicateMutationTest,
    PredicateWitness,
    ProfileCatalogRelease,
    ProfileCraftClosure,
    ProfileCraftClosureCheck,
    ProfileDirective,
    ProfileLayerCard,
    ProjectPayloadBinding,
    ReaderProblemRule,
    ReaderProblemDiagnosis,
    ResolutionRequirement,
    ResolutionRequirementCheck,
    ResolvedProfileStack,
    SourceAdmissionAudit,
    TargetProfile,
    TargetReaderOutcome,
    SemanticInputBinding,
    SemanticInputSourceRule,
    semantic_input_selector_path,
    pack_profile_craft_payload,
    parse_profile_craft_payload,
    profile_craft_schema_id,
    static_resource_ref,
)
from econ_theorist.profile_craft_policy import (
    resolve_profile_stack,
    select_craft_moves,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64
DIGEST_D = "d" * 64
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64


def actor(actor_id: str, kind: str = "agent") -> Actor:
    return Actor(kind=kind, actor_id=actor_id)


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def dref(decision_id: str, version: int = 1) -> DecisionVersionRef:
    return DecisionVersionRef(decision_id=decision_id, version=version)


def aref(
    artifact_id: str, digest: str = DIGEST_A, version: int = 1
) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id,
        version=version,
        content_hash=digest,
    )


def sref(
    entity_id: str,
    field_path: str,
    digest: str = DIGEST_A,
    facet: str = "terminology_presentation",
) -> SemanticFacetRef:
    return SemanticFacetRef(
        entity_id=entity_id,
        version=1,
        facet=facet,
        field_path=field_path,
        semantic_hash=digest,
    )


def directive(
    directive_id: str,
    *,
    conflict_key: str | None = None,
    strength: str = "required",
    scope: str = "authoring",
    kind: str = "calibrate_reader",
) -> ProfileDirective:
    return ProfileDirective(
        directive_id=directive_id,
        conflict_key=conflict_key or directive_id,
        statement=f"A sufficiently explicit profile instruction for {directive_id}.",
        strength=strength,
        effect_scope=scope,
        directive_kind=kind,
        acceptance_criterion=DirectiveAcceptanceCriterion(
            criterion_id=f"criterion.{directive_id}",
            required_assertion_roles=("formal_statement",),
        ),
    )


def layer(
    layer_id: str,
    layer_kind: str,
    selection_key: str,
    directives: tuple[ProfileDirective, ...],
    *,
    overlay: bool = False,
) -> ProfileLayerCard:
    evidence = (aref(f"evidence.{layer_id}"),) if overlay else ()
    return ProfileLayerCard(
        layer_id=layer_id,
        resource_version=1,
        layer_kind=layer_kind,
        selection_key=selection_key,
        status="active",
        is_soft_overlay=overlay,
        directives=directives,
        evidence_refs=evidence,
        evidence_as_of="2026-07-12" if overlay else None,
        confidence="provisional",
        non_applicability=(
            "Do not apply when the proposed calibration changes scientific content.",
        ),
        created_by=actor("profile.curator"),
        created_at="2026-07-12T01:00:00Z",
    )


def profile_material() -> tuple[
    ProfileCatalogRelease, TargetProfile, ResolvedProfileStack
]:
    floor = layer(
        "profile.floor",
        "universal_floor",
        "frontier.theory.floor",
        (
            directive(
                "directive.truth",
                conflict_key="truth.scope",
                strength="invariant",
                scope="formal_truth",
                kind="preserve_floor",
            ),
        ),
    )
    theory = layer(
        "profile.mode",
        "theory_mode",
        "applied_theory",
        (directive("directive.theory"),),
    )
    ambition = layer(
        "profile.ambition",
        "ambition",
        "frontier_general_interest",
        (directive("directive.ambition"),),
    )
    archetype = layer(
        "profile.archetype",
        "archetype",
        "mechanism_explanation",
        (directive("directive.archetype"),),
    )
    field = layer(
        "profile.field",
        "field",
        "information.economics",
        (directive("directive.field"),),
    )
    audience = layer(
        "profile.audience",
        "audience",
        "general_economist",
        (directive("directive.audience"),),
    )
    overlay = layer(
        "profile.overlay",
        "venue_overlay",
        "venue.soft",
        (
            directive(
                "directive.overlay.pace",
                strength="soft",
                scope="authoring",
                kind="adjust_presentation",
            ),
            directive(
                "directive.overlay.template",
                strength="soft",
                scope="authoring",
                kind="hard_template",
            ),
        ),
        overlay=True,
    )
    cards = (floor, theory, ambition, archetype, field, audience, overlay)
    catalog = ProfileCatalogRelease(
        release_id="profile.catalog.release",
        resource_version=1,
        universal_floor_ref=static_resource_ref(floor),
        cards=cards,
        release_notes="Initial theory-only profile catalog for focused Phase 4 validation.",
        released_by=actor("profile.publisher", "human"),
        released_at="2026-07-12T02:00:00Z",
    )
    target = TargetProfile(
        target_profile_id="target.profile",
        package_ref=eref("package.validated"),
        package_hash=DIGEST_D,
        paper_ir_ref=eref("paper.ir"),
        paper_ir_hash=DIGEST_B,
        reader_path_ref=eref("reader.path"),
        reader_path_hash=DIGEST_C,
        base_profile_manifest_ref=eref("profile.manifest.base"),
        base_profile_manifest_hash=DIGEST_E,
        source_state_revision=DIGEST_A,
        catalog_release_ref=static_resource_ref(catalog),
        theory_mode="applied_theory",
        ambition="frontier_general_interest",
        primary_archetype="mechanism_explanation",
        field_key="information.economics",
        primary_audience="general_economist",
        venue_overlay_ref=static_resource_ref(overlay),
        human_decision_refs=(
            dref("decision.theory"),
            dref("decision.ambition"),
            dref("decision.archetype"),
            dref("decision.audience"),
        ),
        selected_by=actor("researcher", "human"),
        selected_at="2026-07-12T03:00:00Z",
    )
    stack = resolve_profile_stack(
        target,
        target_profile_ref=eref("target.profile"),
        source_state_revision=DIGEST_A,
        resolved_by=actor("profile.resolver"),
        resolved_at="2026-07-12T04:00:00Z",
        catalog=catalog,
    )
    return catalog, target, stack


def source(
    source_id: str,
    family: str,
    role: str,
    *,
    research_mode: str = "pure_theory",
    function_key: str = "benchmark.before.mechanism",
    reader_problem_key: str = "opaque.benchmark",
) -> CraftSourceCard:
    split = "contrast" if role == "contrast" else "anchor"
    if role == "provisional":
        split = "development"
    return CraftSourceCard(
        source_card_id=source_id,
        resource_version=1,
        citation=f"Project-owned source record {source_id}",
        source_locator=f"fixture:{source_id}",
        source_content_hash=DIGEST_B,
        access_status="project_owned",
        access_evidence_ref=aref(f"access.{source_id}", DIGEST_C),
        access_verified_at="2026-07-12",
        research_mode=research_mode,
        evidence_role=role,
        corpus_split=split,
        paper_family_id=family,
        author_lineage_ids=(f"lineage.{family}",),
        reader_problem_key=reader_problem_key,
        function_key=function_key,
        functional_summary="The source exposes the benchmark before adding the operative force.",
        transferable_content="Transfer the benchmark-to-delta function using only project economics.",
        paper_specific_nontransferable="Do not transfer wording, cadence, notation, or paper-specific examples.",
        confidence="supported",
        non_applicability=(
            "Do not use when the benchmark or operative economic force is unresolved.",
        ),
        phrase_audit_ref=aref(f"phrase.audit.{source_id}", DIGEST_D),
        derived_by=actor("craft.curator"),
        derived_at="2026-07-12T05:00:00Z",
    )


def craft_material() -> tuple[CraftCorpusRelease, CraftMove, CraftMove]:
    first = source("source.anchor.one", "family.one", "matched_anchor")
    second = source("source.anchor.two", "family.two", "matched_anchor")
    contrast = source("source.contrast", "family.contrast", "contrast")
    empirical = source(
        "source.empirical",
        "family.empirical",
        "provisional",
        research_mode="empirical",
    )
    move = CraftMove(
        move_id="move.benchmark.first",
        resource_version=1,
        functional_name="Expose the fixed benchmark before the new force",
        reader_problem_key="opaque.benchmark",
        function_key="benchmark.before.mechanism",
        trigger_conditions=(
            "The reader sees a theorem before understanding what its benchmark holds fixed.",
        ),
        required_semantic_inputs=("input.benchmark", "input.mechanism"),
        supported_repair_actions=(
            "repair_explanation",
            "add_boundary",
            "replace_example_or_witness",
        ),
        intended_reader_update="The reader separates the natural benchmark from the new force.",
        typical_placements=("section.introduction", "section.results"),
        valid_variants=("A hand-solvable example may expose the same functional contrast.",),
        failure_modes=("Do not turn the move into a fixed journal-specific paragraph template.",),
        compatible_archetypes=("mechanism_explanation",),
        compatible_audiences=("general_economist", "economic_theorist"),
        compatible_theory_modes=("pure_theory", "applied_theory"),
        compatible_field_keys=("information.economics",),
        eligible_section_roles=("introduction", "result_block"),
        compatible_causal_classes=("local_exposition",),
        non_applicability_rule_ids=(
            "upstream_science_unresolved",
            "nonlocal_causal_class",
            "semantic_inputs_unavailable",
            "theory_mode_incompatible",
            "field_incompatible",
            "section_role_incompatible",
        ),
        matched_anchor_refs=(static_resource_ref(first), static_resource_ref(second)),
        contrast_refs=(static_resource_ref(contrast),),
        confidence="supported",
        non_applicability=("Do not use before the mechanism itself is scientifically resolved.",),
        created_by=actor("craft.curator"),
        created_at="2026-07-12T06:00:00Z",
    )
    decoy_first = source(
        "source.decoy.anchor.one",
        "family.decoy.one",
        "matched_anchor",
        function_key="explain.neighbor.mechanism",
        reader_problem_key="opaque.neighbor",
    )
    decoy_second = source(
        "source.decoy.anchor.two",
        "family.decoy.two",
        "matched_anchor",
        function_key="explain.neighbor.mechanism",
        reader_problem_key="opaque.neighbor",
    )
    decoy_contrast = source(
        "source.decoy.contrast",
        "family.decoy.contrast",
        "contrast",
        function_key="explain.neighbor.mechanism",
        reader_problem_key="opaque.neighbor",
    )
    decoy = move.model_copy(
        update={
            "move_id": "move.lexical.decoy",
            "function_key": "explain.neighbor.mechanism",
            "reader_problem_key": "opaque.neighbor",
            "matched_anchor_refs": (
                static_resource_ref(decoy_first),
                static_resource_ref(decoy_second),
            ),
            "contrast_refs": (static_resource_ref(decoy_contrast),),
        }
    )
    audits = (
        SourceAdmissionAudit(source=first, included_in_core=True),
        SourceAdmissionAudit(source=second, included_in_core=True),
        SourceAdmissionAudit(source=contrast, included_in_core=True),
        SourceAdmissionAudit(source=decoy_first, included_in_core=True),
        SourceAdmissionAudit(source=decoy_second, included_in_core=True),
        SourceAdmissionAudit(source=decoy_contrast, included_in_core=True),
        SourceAdmissionAudit(
            source=empirical,
            included_in_core=False,
            exclusion_reason="empirical_or_mixed",
        ),
    )
    corpus = CraftCorpusRelease(
        release_id="craft.corpus.release",
        resource_version=1,
        split_id="craft.split.development",
        source_admission_audits=audits,
        source_cards=(
            first,
            second,
            contrast,
            decoy_first,
            decoy_second,
            decoy_contrast,
        ),
        reader_problem_rules=(
            ReaderProblemRule(
                problem_key="opaque.benchmark",
                accepted_finding_categories=(
                    "economic_explanation",
                    "boundary",
                    "transfer",
                ),
                accepted_repair_actions=(
                    "repair_explanation",
                    "add_boundary",
                    "replace_example_or_witness",
                ),
                required_semantic_input_ids=("input.benchmark", "input.mechanism"),
                semantic_input_source_rules=(
                    SemanticInputSourceRule(
                        input_id="input.benchmark",
                        source_kind="paper_ir",
                        owner_facet="terminology_presentation",
                        selector="paper.narrative_spine.natural_benchmark",
                    ),
                    SemanticInputSourceRule(
                        input_id="input.mechanism",
                        source_kind="result_contract",
                        owner_facet="terminology_presentation",
                        selector="result_packet.archetype.operative_force",
                    ),
                ),
                allowed_causal_classes=("local_exposition",),
            ),
            ReaderProblemRule(
                problem_key="opaque.neighbor",
                accepted_finding_categories=("economic_explanation",),
                accepted_repair_actions=(
                    "repair_explanation",
                    "add_boundary",
                    "replace_example_or_witness",
                ),
                required_semantic_input_ids=("input.benchmark", "input.mechanism"),
                semantic_input_source_rules=(
                    SemanticInputSourceRule(
                        input_id="input.benchmark",
                        source_kind="paper_ir",
                        owner_facet="terminology_presentation",
                        selector="paper.narrative_spine.natural_benchmark",
                    ),
                    SemanticInputSourceRule(
                        input_id="input.mechanism",
                        source_kind="result_contract",
                        owner_facet="terminology_presentation",
                        selector="result_packet.archetype.operative_force",
                    ),
                ),
                allowed_causal_classes=("local_exposition",),
            ),
        ),
        moves=(decoy, move),
        index_version="craft.index.v1",
        retriever_version="craft.retriever.v1",
        released_by=actor("craft.publisher", "human"),
        released_at="2026-07-12T07:00:00Z",
    )
    return corpus, move, decoy


def diagnosis(stack: ResolvedProfileStack, *, resolved: bool = True) -> ReaderProblemDiagnosis:
    paper_ref = eref("paper.ir")
    reader_ref = eref("reader.path")
    stack_ref = eref(stack.stack_id)
    contract_ref = eref("result.contracts")
    unit_ref = eref("manuscript.unit.prior")
    review_ref = eref("review.economic")
    finding_ref = eref("finding.opaque.benchmark")
    closure_ref = eref("review.closure.blocked")
    brief_ref = eref("revision.brief")
    requirement = ResolutionRequirement(
        requirement_id="resolution.benchmark",
        finding_ref=finding_ref,
        action="repair_explanation",
        instruction_source=sref(
            brief_ref.entity_id,
            "/instructions/0",
            DIGEST_B,
            "authority",
        ),
        affected_assertion_ids=("assertion.mechanism",),
        affected_section_ids=("section.results",),
        required_semantic_input_ids=("input.benchmark", "input.mechanism"),
    )
    return ReaderProblemDiagnosis(
        diagnosis_id="diagnosis.reader.problem",
        paper_ir_ref=paper_ref,
        paper_ir_hash=DIGEST_B,
        reader_path_ref=reader_ref,
        reader_path_hash=DIGEST_C,
        profile_stack_ref=stack_ref,
        profile_stack_hash=object_digest(stack),
        result_contract_set_binding=ProjectPayloadBinding(
            entity_ref=contract_ref,
            payload_hash=DIGEST_A,
        ),
        inspected_manuscript_unit_binding=ProjectPayloadBinding(
            entity_ref=unit_ref,
            payload_hash=DIGEST_D,
        ),
        diagnostic_review_bindings=(
            ProjectPayloadBinding(entity_ref=review_ref, payload_hash=DIGEST_E),
        ),
        diagnostic_finding_bindings=(
            ProjectPayloadBinding(entity_ref=finding_ref, payload_hash=DIGEST_F),
        ),
        blocked_review_closure_binding=ProjectPayloadBinding(
            entity_ref=closure_ref, payload_hash=DIGEST_B
        ),
        revision_brief_binding=ProjectPayloadBinding(
            entity_ref=brief_ref, payload_hash=DIGEST_C
        ),
        diagnostic_categories=("economic_explanation",),
        affected_section_roles=("result_block",),
        causal_class="local_exposition" if resolved else "scientific_content",
        resolution_requirements=(requirement,),
        semantic_input_bindings=(
            SemanticInputBinding(
                input_id="input.benchmark",
                source_ref=sref("paper.ir", "/economic_objects/0", DIGEST_B),
                source_kind="paper_ir",
                availability="available",
                explanation="The accepted PaperIR identifies the exact natural benchmark.",
            ),
            SemanticInputBinding(
                input_id="input.mechanism",
                source_ref=sref("result.contracts", "/result_packets/0", DIGEST_C),
                source_kind="result_contract",
                availability="available",
                explanation="The accepted result contract identifies the operative mechanism.",
            ),
        ),
        affected_section_ids=("section.results",),
        reader_problem_key="opaque.benchmark",
        required_resolution_ids=("resolution.benchmark",),
        observed_problem="The result appears before the reader can recover the fixed benchmark.",
        required_semantic_input_ids=("input.benchmark", "input.mechanism"),
        upstream_science_status="resolved" if resolved else "unresolved",
        craft_eligible=resolved,
        upstream_repair_route=None if resolved else "repair.mechanism",
        evidence_refs=(
            paper_ref,
            reader_ref,
            stack_ref,
            contract_ref,
            unit_ref,
            review_ref,
            finding_ref,
            closure_ref,
            brief_ref,
        ),
        diagnosed_by=actor("reader.diagnostician"),
        diagnosed_at="2026-07-12T08:00:00Z",
    )


def selection_material() -> tuple[CraftSelectionManifest, ResolvedProfileStack]:
    _, _, stack = profile_material()
    corpus, _, _ = craft_material()
    problem = diagnosis(stack)
    manifest = select_craft_moves(
        problem,
        diagnosis_ref=eref(problem.diagnosis_id),
        profile_stack=stack,
        profile_stack_ref=eref(stack.stack_id),
        selected_by=actor("craft.selector"),
        selected_at="2026-07-12T09:00:00Z",
        corpus=corpus,
    )
    return manifest, stack


def predicate_contract() -> ObligationPredicateContract:
    clause_specs = (
        ("clause.domain", "domain", "/domain"),
        ("clause.quantifier", "quantifier", "/quantifier"),
        ("clause.assumption", "assumption", "/assumptions/0"),
        ("clause.conclusion", "conclusion", "/relation"),
        ("clause.boundary", "boundary", "/boundary"),
    )
    mappings = tuple(
        PredicateClauseMapping(
            obligation_clause_id=clause_id,
            clause_kind=kind,
            relation="exact",
            predicate_json_pointers=(pointer,),
            predicate_fragment_hash=DIGEST_A,
            explanation=f"The predicate fragment exactly represents the {kind} clause.",
        )
        for clause_id, kind, pointer in clause_specs
    )
    witnesses = (
        PredicateWitness(
            witness_id="witness.domain.member",
            case_id="case.antecedent.x.one",
            witness_kind="domain_member",
            artifact_ref=aref("witness.domain.member", DIGEST_A),
            explanation="This executable assignment is a member of the represented domain.",
        ),
        PredicateWitness(
            witness_id="witness.antecedent",
            case_id="case.antecedent.x.one",
            witness_kind="antecedent_satisfying",
            artifact_ref=aref("witness.antecedent", DIGEST_B),
            explanation="This exact assignment demonstrates that the antecedent is satisfiable.",
        ),
        PredicateWitness(
            witness_id="witness.false",
            case_id="case.predicate.false.x.zero",
            witness_kind="predicate_falsifying",
            artifact_ref=aref("witness.false", DIGEST_C),
            explanation="This negative control demonstrates that the predicate can return false.",
        ),
    )
    mutations = (
        PredicateMutationTest(
            mutation_id="mutation.empty.domain",
            mutation_kind="empty_domain",
            mutated_predicate_ref=aref("mutant.empty.domain"),
            result_ref=aref("mutant.empty.domain.result", DIGEST_E),
            detected=True,
        ),
        PredicateMutationTest(
            mutation_id="mutation.constant.true",
            mutation_kind="constant_true",
            mutated_predicate_ref=aref("mutant.constant.true"),
            result_ref=aref("mutant.constant.true.result", DIGEST_B),
            detected=True,
        ),
        PredicateMutationTest(
            mutation_id="mutation.conclusion.flip",
            mutation_kind="conclusion_flip",
            mutated_predicate_ref=aref("mutant.conclusion.flip"),
            result_ref=aref("mutant.conclusion.flip.result", DIGEST_C),
            detected=True,
        ),
        PredicateMutationTest(
            mutation_id="mutation.domain.narrow",
            mutation_kind="domain_narrowing",
            mutated_predicate_ref=aref("mutant.domain.narrow"),
            result_ref=aref("mutant.domain.narrow.result", DIGEST_D),
            detected=True,
        ),
        PredicateMutationTest(
            mutation_id="mutation.omitted.assumption",
            mutation_kind="omitted_assumption",
            mutated_predicate_ref=aref("mutant.omitted.assumption"),
            result_ref=aref("mutant.omitted.assumption.result", DIGEST_F),
            detected=True,
        ),
    )
    return ObligationPredicateContract(
        contract_id="predicate.contract",
        assurance_bundle_ref=eref("assurance.bundle"),
        assurance_bundle_hash=DIGEST_E,
        receipt_id="receipt.symbolic.identity",
        receipt_hash=DIGEST_F,
        obligation_ref=eref("proof.obligation"),
        obligation_hash=DIGEST_A,
        claim_graph_ref=eref("claim.graph"),
        claim_graph_hash=DIGEST_B,
        formal_model_ref=eref("formal.model"),
        formal_model_hash=DIGEST_C,
        assumption_map_ref=eref("assumption.map"),
        assumption_map_hash=DIGEST_D,
        obligation_clause_ids=tuple(item[0] for item in clause_specs),
        obligation_assumption_ids=("assumption.processing",),
        mapped_assumption_ids=("assumption.processing",),
        clause_mappings=mappings,
        domain_relation="equal",
        quantifier_relation="equivalent",
        execution_scope="symbolic_exact",
        coverage_class="exact",
        predicate_artifact_ref=aref("predicate.spec"),
        code_ref=aref("predicate.code", DIGEST_B),
        antecedent_satisfiable=True,
        predicate_can_return_false=True,
        witnesses=witnesses,
        mutation_tests=mutations,
        tolerance_policy="exact",
        mapper=actor("predicate.mapper"),
        mapped_at="2026-07-12T10:00:00Z",
        limitations="The contract covers only the exact obligation and cannot broaden its theorem scope.",
    )


def mapping_audit(contract: ObligationPredicateContract) -> PredicateMappingAudit:
    mutation_ids = tuple(item.mutation_id for item in contract.mutation_tests)
    return PredicateMappingAudit(
        audit_id="predicate.audit",
        contract_ref=eref(contract.contract_id),
        contract_hash=object_digest(contract),
        contract_coverage_class=contract.coverage_class,
        contract_mapper=contract.mapper,
        registered_mutation_ids=mutation_ids,
        auditor=actor("predicate.auditor"),
        mutation_executor=actor("predicate.mutation.runner", "deterministic_tool"),
        mutation_replay_ref=aref("predicate.mutation.replay", DIGEST_D),
        route_run_id="route.run.predicate.audit",
        route_run_hash=DIGEST_A,
        context_manifest_hash=DIGEST_B,
        compiled_context_hash=DIGEST_C,
        replayed_mutation_ids=mutation_ids,
        mutation_replay_passed=True,
        unexecutable_mutation_ids=(),
        domain_witness_verified=True,
        antecedent_witness_verified=True,
        falsifying_witness_verified=True,
        verdict="approved_exact",
        audited_at="2026-07-12T11:00:00Z",
    )


def realization(selection: CraftSelectionManifest) -> CraftRealizationAssessment:
    candidates_by_ref = {item.move_ref: item.move for item in selection.candidates}
    selection_ref = eref(selection.selection_id)
    manuscript_ref = eref("manuscript.unit")
    manuscript_artifact_ref = aref("manuscript.bytes", DIGEST_D)
    base_closure_ref = eref("authoring.review.closure")
    formal_review_ref = eref("review.formal")
    economic_review_ref = eref("review.economic")
    cold_review_ref = eref("review.cold")
    phrase_audit_ref = aref("phrase.audit.manuscript", DIGEST_C)
    directive_check = DirectiveAcceptanceCheck(
        directive_id="directive.mechanism",
        criterion_id="criterion.directive.mechanism",
        required_assertion_roles=("mechanism_or_conceptual_explanation",),
        realized_assertion_roles=("mechanism_or_conceptual_explanation",),
        outcome="pass",
        evidence_refs=(manuscript_ref, economic_review_ref),
        explanation="The manuscript realizes the required mechanism-explanation role.",
    )
    resolution_checks = tuple(
        ResolutionRequirementCheck(
            requirement_id=requirement_id,
            repair_action="repair_explanation",
            realizing_move_refs=selection.selected_move_refs,
            affected_assertion_ids=("assertion.mechanism",),
            affected_section_ids=("section.results",),
            required_semantic_input_ids=("input.benchmark", "input.mechanism"),
            realized_semantic_input_ids=("input.benchmark", "input.mechanism"),
            outcome="pass",
            evidence_refs=(selection_ref, manuscript_ref, economic_review_ref),
            explanation="The selected move realizes every semantic input required by the repair.",
        )
        for requirement_id in selection.diagnosed_required_resolution_ids
    )
    target_outcome = TargetReaderOutcome(
        primary_audience="general_economist",
        benchmark_delta_reconstructible=True,
        operative_force_reconstructible=True,
        boundary_reconstructible=True,
        nearby_case_predictable=True,
        outcome="pass",
        evidence_refs=(economic_review_ref, cold_review_ref),
        explanation="Independent reader checks recover the benchmark, force, boundary, and transfer.",
    )
    realized = tuple(
        CraftMoveRealization(
            move_ref=move_ref,
            realized_assertion_ids=("assertion.benchmark", "assertion.mechanism"),
            realized_semantic_input_ids=candidates_by_ref[
                move_ref
            ].required_semantic_inputs,
            realized_semantic_source_refs=(
                sref("paper.ir", "/economic_objects/0", DIGEST_B),
                sref("result.contracts", "/result_packets/0", DIGEST_C),
            ),
            realized_function=True,
            intended_reader_update_delivered=True,
            formal_fidelity_preserved=True,
            evidence_refs=(
                selection_ref,
                manuscript_ref,
                manuscript_artifact_ref,
                base_closure_ref,
                formal_review_ref,
                economic_review_ref,
                cold_review_ref,
                phrase_audit_ref,
            ),
            explanation="The manuscript realizes the selected function in project-specific language.",
        )
        for move_ref in selection.selected_move_refs
    )
    return CraftRealizationAssessment(
        assessment_id="craft.realization",
        selection_manifest_ref=selection_ref,
        selection_manifest_hash=object_digest(selection),
        profile_stack_ref=selection.profile_stack_ref,
        profile_stack_hash=selection.profile_stack_hash,
        reader_problem_diagnosis_ref=selection.diagnosis_ref,
        reader_problem_diagnosis_hash=selection.diagnosis_hash,
        reader_path_ref=eref("reader.path"),
        reader_path_hash=DIGEST_C,
        result_contract_set_ref=eref("result.contracts"),
        result_contract_set_hash=DIGEST_A,
        primary_audience="general_economist",
        selected_move_refs=selection.selected_move_refs,
        manuscript_unit_ref=manuscript_ref,
        manuscript_unit_hash=DIGEST_D,
        manuscript_artifact_ref=manuscript_artifact_ref,
        base_authoring_closure_ref=base_closure_ref,
        base_authoring_closure_hash=DIGEST_A,
        formal_fidelity_review_ref=formal_review_ref,
        formal_fidelity_review_hash=DIGEST_B,
        economic_reader_review_ref=economic_review_ref,
        economic_reader_review_hash=DIGEST_C,
        cold_reader_review_ref=cold_review_ref,
        cold_reader_review_hash=DIGEST_E,
        writer=actor("writer.canonical"),
        assessor=actor("craft.assessor"),
        move_realizations=realized,
        required_directive_ids=(directive_check.directive_id,),
        directive_acceptance_checks=(directive_check,),
        required_resolution_ids=selection.diagnosed_required_resolution_ids,
        resolution_requirement_checks=resolution_checks,
        target_reader_outcome=target_outcome,
        formal_fidelity_outcome="pass",
        phrase_leak_audit_outcome="pass",
        phrase_leak_audit_ref=phrase_audit_ref,
        named_voice_imitation_outcome="pass",
        empirical_template_contamination_outcome="pass",
        outcome="pass",
        assessed_at="2026-07-12T12:00:00Z",
    )


def closure() -> ProfileCraftClosure:
    selection, stack = selection_material()
    problem = diagnosis(stack)
    contract = predicate_contract()
    audit = mapping_audit(contract)
    assessed = realization(selection)
    checks = tuple(
        ProfileCraftClosureCheck(
            check_id=f"closure.check.{kind}",
            check_kind=kind,
            outcome="pass",
            evidence_refs=(eref(f"evidence.{kind}"),),
            explanation=f"The noncompensatory {kind} requirement passed exact validation.",
        )
        for kind in PROFILE_CRAFT_READY_CHECK_ORDER
    )
    return ProfileCraftClosure(
        closure_id="profile.craft.closure",
        base_authoring_closure_ref=eref("authoring.review.closure"),
        base_authoring_closure_hash=DIGEST_A,
        base_authoring_closure_outcome="authoring_ready",
        manuscript_unit_ref=eref("manuscript.unit"),
        manuscript_unit_hash=DIGEST_D,
        reader_problem_diagnosis_ref=eref(problem.diagnosis_id),
        reader_problem_diagnosis_hash=object_digest(problem),
        profile_stack=ProjectPayloadBinding(
            entity_ref=eref(stack.stack_id), payload_hash=object_digest(stack)
        ),
        craft_selection=ProjectPayloadBinding(
            entity_ref=eref(selection.selection_id), payload_hash=object_digest(selection)
        ),
        predicate_mapping_audits=(
            ProjectPayloadBinding(
                entity_ref=eref(audit.audit_id), payload_hash=object_digest(audit)
            ),
        ),
        predicate_mapping_coverage_classes=(audit.contract_coverage_class,),
        predicate_limitation_kinds=(),
        realization_assessment=ProjectPayloadBinding(
            entity_ref=eref(assessed.assessment_id), payload_hash=object_digest(assessed)
        ),
        source_state_revision=DIGEST_A,
        all_dependencies_current_and_fresh=True,
        checks=checks,
        outcome="ready",
        determined_by=actor("profile.craft.closer"),
        determined_at="2026-07-12T13:00:00Z",
    )


class Phase4ProfileCraftModelTests(unittest.TestCase):
    def test_registry_is_independent_strict_frozen_and_round_trips(self) -> None:
        payload = closure()
        self.assertEqual(len(PROFILE_CRAFT_PAYLOAD_MODELS), 13)
        self.assertEqual(
            profile_craft_schema_id("ProfileCraftClosure"),
            "econ_theorist.profile_craft/ProfileCraftClosure/v1",
        )
        facets = pack_profile_craft_payload(payload)
        parsed = parse_profile_craft_payload("ProfileCraftClosure", facets)
        self.assertEqual(parsed, payload)
        self.assertEqual(canonical_json_bytes(parsed), canonical_json_bytes(payload))
        with self.assertRaises(ValidationError):
            payload.outcome = "blocked"  # type: ignore[misc]
        with self.assertRaises(ValueError):
            parse_profile_craft_payload("ResolvedProfileManifest", facets)

    def test_universal_floor_wins_and_hard_overlay_is_rejected(self) -> None:
        with self.assertRaises(ValidationError):
            layer(
                "profile.field.unsafe",
                "field",
                "unsafe",
                (
                    directive(
                        "directive.field.science",
                        scope="scientific_claim",
                        kind="require_scientific_content",
                    ),
                ),
            )
        catalog, target, stack = profile_material()
        self.assertEqual(
            stack,
            resolve_profile_stack(
                target,
                target_profile_ref=eref("target.profile"),
                source_state_revision=DIGEST_A,
                resolved_by=actor("profile.resolver"),
                resolved_at="2026-07-12T04:00:00Z",
                catalog=catalog,
            ),
        )
        rejected = {
            item.directive.directive_id: item.rejection_reason
            for item in stack.directive_resolutions
            if item.outcome == "rejected"
        }
        self.assertEqual(
            rejected["directive.overlay.template"], "hard_venue_template"
        )
        bad = tuple(
            item.model_copy(update={"outcome": "active", "rejection_reason": None})
            if item.directive.directive_id == "directive.overlay.template"
            else item
            for item in stack.directive_resolutions
        )
        values = {
            field: getattr(stack, field)
            for field in ResolvedProfileStack.model_fields
            if field != "directive_resolutions"
        }
        with self.assertRaises(ValidationError):
            ResolvedProfileStack(**values, directive_resolutions=bad)

    def test_reader_problem_rules_bind_ordered_typed_sources(self) -> None:
        rule = craft_material()[0].reader_problem_rules[0]
        self.assertEqual(
            tuple(item.input_id for item in rule.semantic_input_source_rules),
            rule.required_semantic_input_ids,
        )
        values = rule.model_dump(mode="python")
        values["semantic_input_source_rules"] = tuple(
            reversed(values["semantic_input_source_rules"])
        )
        with self.assertRaisesRegex(ValidationError, "exactly follow required input order"):
            ReaderProblemRule.model_validate(values)
        with self.assertRaisesRegex(ValidationError, "wrong source kind or owner facet"):
            SemanticInputSourceRule(
                input_id="input.benchmark",
                source_kind="result_contract",
                owner_facet="terminology_presentation",
                selector="paper.narrative_spine.natural_benchmark",
            )
        self.assertEqual(
            semantic_input_selector_path(
                "result_packet.archetype.operative_force",
                primary_archetype="mechanism_explanation",
                packet_index=2,
            ),
            "/payload/result_packets/2/archetype_module/initiating_force/content",
        )
        self.assertEqual(
            semantic_input_selector_path(
                "result_packet.archetype.operative_force",
                primary_archetype="comparative_statics_threshold",
                packet_index=2,
            ),
            "/payload/result_packets/2/archetype_module/competing_effects/content",
        )
        self.assertEqual(
            semantic_input_selector_path(
                "result_packet.archetype.affected_margin",
                primary_archetype="comparative_statics_threshold",
                packet_index=0,
            ),
            (
                "/payload/result_packets/0/archetype_module/"
                "threshold_or_regime_logic/content"
            ),
        )
        with self.assertRaisesRegex(ValueError, "unsupported typed semantic extractor"):
            semantic_input_selector_path(
                "result_packet.boundary",
                primary_archetype="characterization_bounds",
                packet_index=0,
            )

    def test_empirical_sources_and_duplicate_paper_lineage_cannot_support_core(self) -> None:
        corpus, move, _ = craft_material()
        empirical_audit = next(
            item
            for item in corpus.source_admission_audits
            if item.source.research_mode == "empirical"
        )
        with self.assertRaises(ValidationError):
            SourceAdmissionAudit(
                source=empirical_audit.source,
                included_in_core=True,
            )

        anchor = corpus.source_cards[0]
        duplicate = corpus.source_cards[1].model_copy(
            update={"paper_family_id": anchor.paper_family_id}
        )
        contrast = corpus.source_cards[2]
        duplicated_move = move.model_copy(
            update={
                "matched_anchor_refs": (
                    static_resource_ref(anchor),
                    static_resource_ref(duplicate),
                )
            }
        )
        audits = (
            SourceAdmissionAudit(source=anchor, included_in_core=True),
            SourceAdmissionAudit(source=duplicate, included_in_core=True),
            SourceAdmissionAudit(source=contrast, included_in_core=True),
        )
        with self.assertRaises(ValidationError):
            CraftCorpusRelease(
                release_id="craft.corpus.duplicate",
                resource_version=1,
                split_id="craft.split.duplicate",
                source_admission_audits=audits,
                source_cards=(anchor, duplicate, contrast),
                reader_problem_rules=corpus.reader_problem_rules,
                moves=(duplicated_move,),
                index_version="craft.index.v1",
                retriever_version="craft.retriever.v1",
                released_by=actor("craft.publisher"),
                released_at="2026-07-12T14:00:00Z",
            )

    def test_raw_anchor_prose_and_imitation_fields_are_forbidden(self) -> None:
        card = source("source.safe", "family.safe", "matched_anchor")
        values = card.model_dump(mode="python")
        values["raw_anchor_prose"] = "A reusable copyrighted paragraph."
        with self.assertRaises(ValidationError):
            CraftSourceCard.model_validate(values)
        move = craft_material()[1]
        move_values = move.model_dump(mode="python")
        move_values["imitation_target"] = "named.author"
        with self.assertRaises(ValidationError):
            CraftMove.model_validate(move_values)

    def test_selection_is_function_first_matched_contrast_and_minimal(self) -> None:
        selection, stack = selection_material()
        corpus, _, _ = craft_material()
        problem = diagnosis(stack)
        self.assertEqual(
            selection,
            select_craft_moves(
                problem,
                diagnosis_ref=eref(problem.diagnosis_id),
                profile_stack=stack,
                profile_stack_ref=eref(stack.stack_id),
                selected_by=actor("craft.selector"),
                selected_at="2026-07-12T09:00:00Z",
                corpus=corpus,
            ),
        )
        self.assertEqual(selection.selected_move_refs[0].resource_id, "move.benchmark.first")
        self.assertEqual(selection.candidates[0].lexical_similarity_rank, 1)
        self.assertFalse(selection.candidates[0].selected)
        self.assertEqual(selection.candidates[0].exclusion_reason, "function_mismatch")
        decoy = selection.candidates[0]
        with self.assertRaises(ValidationError):
            CraftCandidateAudit(
                **{
                    **{
                        field: getattr(decoy, field)
                        for field in CraftCandidateAudit.model_fields
                        if field not in {"selected", "exclusion_reason", "covered_requirement_ids"}
                    },
                    "selected": True,
                    "exclusion_reason": None,
                    "covered_requirement_ids": ("resolution.benchmark",),
                }
            )

        good = selection.candidates[1]
        redundant = good.model_copy(
            update={
                "move_ref": static_resource_ref(
                    good.move.model_copy(update={"move_id": "move.redundant"})
                ),
                "move": good.move.model_copy(update={"move_id": "move.redundant"}),
            }
        )
        with self.assertRaises(ValidationError):
            CraftSelectionManifest(
                **{
                    **{
                        field: getattr(selection, field)
                        for field in CraftSelectionManifest.model_fields
                        if field not in {"candidates", "selected_move_refs"}
                    },
                    "candidates": (good, redundant),
                    "selected_move_refs": (good.move_ref, redundant.move_ref),
                }
            )

    def test_selector_computes_requirement_coverage_and_minimum_cardinality(self) -> None:
        _, _, stack = profile_material()
        corpus, move, decoy = craft_material()
        base = diagnosis(stack)
        original = base.resolution_requirements[0]
        explain = original.model_copy(
            update={
                "requirement_id": "resolution.explain",
                "action": "repair_explanation",
                "required_semantic_input_ids": ("input.benchmark",),
            }
        )
        boundary = original.model_copy(
            update={
                "requirement_id": "resolution.boundary",
                "action": "add_boundary",
                "instruction_source": sref(
                    "revision.brief", "/instructions/1", DIGEST_C, "authority"
                ),
                "required_semantic_input_ids": ("input.mechanism",),
            }
        )
        problem = ReaderProblemDiagnosis(
            **{
                **{
                    field: getattr(base, field)
                    for field in ReaderProblemDiagnosis.model_fields
                },
                "diagnostic_categories": ("economic_explanation", "boundary"),
                "resolution_requirements": (explain, boundary),
                "required_resolution_ids": (
                    explain.requirement_id,
                    boundary.requirement_id,
                ),
            }
        )
        partial = move.model_copy(
            update={
                "move_id": "move.partial.first",
                "supported_repair_actions": ("repair_explanation",),
            }
        )
        full_b = move.model_copy(update={"move_id": "move.full.b"})
        full_a = move.model_copy(update={"move_id": "move.full.a"})
        expanded = CraftCorpusRelease(
            **{
                **{
                    field: getattr(corpus, field)
                    for field in CraftCorpusRelease.model_fields
                    if field != "moves"
                },
                "moves": (partial, full_b, full_a, decoy),
            }
        )
        selection = select_craft_moves(
            problem,
            diagnosis_ref=eref(problem.diagnosis_id),
            profile_stack=stack,
            profile_stack_ref=problem.profile_stack_ref,
            selected_by=actor("craft.selector"),
            selected_at="2026-07-12T09:30:00Z",
            corpus=expanded,
        )
        self.assertEqual(
            tuple(item.resource_id for item in selection.selected_move_refs),
            ("move.full.a",),
        )
        partial_audit = next(
            item for item in selection.candidates if item.move.move_id == "move.partial.first"
        )
        self.assertEqual(
            partial_audit.covered_requirement_ids,
            ("resolution.explain",),
        )
        self.assertEqual(
            tuple(item.covered for item in partial_audit.requirement_coverages),
            (True, False),
        )

    def test_reader_diagnosis_binds_exact_failure_and_repair_evidence(self) -> None:
        _, _, stack = profile_material()
        problem = diagnosis(stack)
        self.assertEqual(
            problem.result_contract_set_binding.entity_ref,
            eref("result.contracts"),
        )
        self.assertEqual(
            problem.inspected_manuscript_unit_binding.entity_ref,  # type: ignore[union-attr]
            eref("manuscript.unit.prior"),
        )
        self.assertEqual(
            tuple(item.entity_ref for item in problem.diagnostic_review_bindings),
            (eref("review.economic"),),
        )
        self.assertEqual(
            tuple(item.entity_ref for item in problem.diagnostic_finding_bindings),
            (eref("finding.opaque.benchmark"),),
        )

        values = {
            field: getattr(problem, field)
            for field in ReaderProblemDiagnosis.model_fields
        }
        with self.assertRaises(ValidationError):
            ReaderProblemDiagnosis(
                **{
                    **values,
                    "no_prior_manuscript_unit_reason": (
                        "initial_composition_not_yet_realized"
                    ),
                }
            )
        with self.assertRaises(ValidationError):
            ReaderProblemDiagnosis(
                **{
                    **values,
                    "diagnostic_review_bindings": (),
                    "diagnostic_finding_bindings": (),
                    "no_prior_review_reason": None,
                }
            )

        second_review = ProjectPayloadBinding(
            entity_ref=eref("review.cold"),
            payload_hash=problem.diagnostic_review_bindings[0].payload_hash,
        )
        with self.assertRaises(ValidationError):
            ReaderProblemDiagnosis(
                **{
                    **values,
                    "diagnostic_review_bindings": (
                        *problem.diagnostic_review_bindings,
                        second_review,
                    ),
                    "evidence_refs": (*problem.evidence_refs, second_review.entity_ref),
                }
            )

        with self.assertRaises(ValidationError):
            ReaderProblemDiagnosis(
                **{
                    **values,
                    "evidence_refs": tuple(
                        ref
                        for ref in problem.evidence_refs
                        if ref != eref("finding.opaque.benchmark")
                    ),
                }
            )

    def test_pre_manuscript_diagnosis_requires_both_typed_absence_reasons(self) -> None:
        _, _, stack = profile_material()
        problem = diagnosis(stack)
        retained_refs = {
            problem.paper_ir_ref,
            problem.reader_path_ref,
            problem.profile_stack_ref,
            problem.result_contract_set_binding.entity_ref,
        }
        values = {
            field: getattr(problem, field)
            for field in ReaderProblemDiagnosis.model_fields
        }
        pre_manuscript = ReaderProblemDiagnosis(
            **{
                **values,
                "inspected_manuscript_unit_binding": None,
                "no_prior_manuscript_unit_reason": (
                    "initial_composition_not_yet_realized"
                ),
                "diagnostic_review_bindings": (),
                "diagnostic_finding_bindings": (),
                "blocked_review_closure_binding": None,
                "revision_brief_binding": None,
                "no_prior_review_reason": (
                    "initial_composition_not_yet_reviewable"
                ),
                "diagnostic_categories": (),
                "causal_class": "initial_planning",
                "resolution_requirements": (),
                "semantic_input_bindings": (),
                "affected_section_ids": (),
                "required_resolution_ids": (),
                "required_semantic_input_ids": (),
                "craft_eligible": False,
                "upstream_repair_route": "compose.initial_manuscript",
                "evidence_refs": tuple(
                    ref for ref in problem.evidence_refs if ref in retained_refs
                ),
            }
        )
        self.assertIsNone(pre_manuscript.inspected_manuscript_unit_binding)
        self.assertEqual(pre_manuscript.diagnostic_review_bindings, ())

        pre_values = {
            field: getattr(pre_manuscript, field)
            for field in ReaderProblemDiagnosis.model_fields
        }
        with self.assertRaises(ValidationError):
            ReaderProblemDiagnosis(
                **{**pre_values, "no_prior_review_reason": None}
            )

    def test_unresolved_science_forces_craft_abstention(self) -> None:
        _, _, stack = profile_material()
        problem = diagnosis(stack, resolved=False)
        corpus, _, _ = craft_material()
        abstained = select_craft_moves(
            problem,
            diagnosis_ref=eref(problem.diagnosis_id),
            profile_stack=stack,
            profile_stack_ref=problem.profile_stack_ref,
            selected_by=actor("craft.selector"),
            selected_at="2026-07-12T15:00:00Z",
            corpus=corpus,
        )
        self.assertEqual(abstained.outcome, "abstained_upstream")
        self.assertFalse(any(item.selected for item in abstained.candidates))
        self.assertTrue(
            all(
                item.exclusion_reason == "non_applicable"
                for item in abstained.candidates
            )
        )

    def test_exact_predicate_mapping_rejects_vacuity_and_narrowing(self) -> None:
        contract = predicate_contract()
        self.assertEqual(contract.coverage_class, "exact")
        self.assertEqual(
            {item.mutation_kind for item in contract.mutation_tests},
            {
                "empty_domain",
                "constant_true",
                "conclusion_flip",
                "domain_narrowing",
                "omitted_assumption",
            },
        )
        base = {
            field: getattr(contract, field)
            for field in ObligationPredicateContract.model_fields
        }
        with self.assertRaises(ValidationError):
            ObligationPredicateContract(**{**base, "antecedent_satisfiable": False})
        with self.assertRaises(ValidationError):
            ObligationPredicateContract(**{**base, "predicate_can_return_false": False})
        with self.assertRaises(ValidationError):
            ObligationPredicateContract(**{**base, "domain_relation": "narrowed"})
        with self.assertRaises(ValidationError):
            ObligationPredicateContract(
                **{
                    **base,
                    "added_assumption_ids": ("assumption.hidden",),
                }
            )
        missing_mandatory_attack = tuple(
            item
            for item in contract.mutation_tests
            if item.mutation_kind != "omitted_assumption"
        )
        with self.assertRaises(ValidationError):
            ObligationPredicateContract(
                **{**base, "mutation_tests": missing_mandatory_attack}
            )

    def test_partial_predicate_mapping_separates_domain_from_antecedent(self) -> None:
        exact = predicate_contract()
        omitted_mapping = next(
            item
            for item in exact.clause_mappings
            if item.clause_kind == "assumption"
        ).model_copy(
            update={
                "relation": "omitted",
                "predicate_json_pointers": (),
            }
        )
        mappings = tuple(
            omitted_mapping if item.clause_kind == "assumption" else item
            for item in exact.clause_mappings
        )
        mutations = tuple(
            item.model_copy(update={"detected": False})
            if item.mutation_kind == "omitted_assumption"
            else item
            for item in exact.mutation_tests
        )
        domain_witness = next(
            item for item in exact.witnesses if item.witness_kind == "domain_member"
        )
        values = {
            field: getattr(exact, field)
            for field in ObligationPredicateContract.model_fields
        }
        partial = ObligationPredicateContract(
            **{
                **values,
                "mapped_assumption_ids": (),
                "clause_mappings": mappings,
                "domain_relation": "narrowed",
                "quantifier_relation": "weakened",
                "execution_scope": "finite_sample",
                "coverage_class": "diagnostic",
                "antecedent_satisfiable": False,
                "predicate_can_return_false": False,
                "witnesses": (domain_witness,),
                "mutation_tests": mutations,
            }
        )
        self.assertFalse(partial.antecedent_satisfiable)
        self.assertEqual(partial.witnesses[0].witness_kind, "domain_member")
        omitted = next(
            item
            for item in partial.mutation_tests
            if item.mutation_kind == "omitted_assumption"
        )
        self.assertFalse(omitted.detected)

        mutation_ids = tuple(item.mutation_id for item in partial.mutation_tests)
        warning = PredicateMappingFinding(
            finding_id="finding.unexecutable.assumption",
            severity="warning",
            summary="The finite predicate has no executable assumption component.",
            affected_clause_ids=("clause.assumption",),
            limitation_kinds=(
                "nonexact_clause_mapping",
                "domain_not_equal",
                "quantifier_not_equivalent",
                "assumption_mapping_nonexact",
                "bounded_execution_scope",
                "coverage_below_exact",
                "nonvacuity_unverified",
                "unexecutable_control",
            ),
        )
        audit = PredicateMappingAudit(
            audit_id="predicate.audit.partial",
            contract_ref=eref(partial.contract_id),
            contract_hash=object_digest(partial),
            contract_coverage_class=partial.coverage_class,
            contract_mapper=partial.mapper,
            registered_mutation_ids=mutation_ids,
            auditor=actor("predicate.auditor"),
            mutation_executor=actor(
                "predicate.mutation.runner", "deterministic_tool"
            ),
            mutation_replay_ref=aref("predicate.mutation.replay", DIGEST_D),
            route_run_id="route.run.predicate.audit.partial",
            route_run_hash=DIGEST_A,
            context_manifest_hash=DIGEST_B,
            compiled_context_hash=DIGEST_C,
            replayed_mutation_ids=mutation_ids,
            mutation_replay_passed=True,
            unexecutable_mutation_ids=(omitted.mutation_id,),
            domain_witness_verified=True,
            antecedent_witness_verified=False,
            falsifying_witness_verified=False,
            findings=(warning,),
            verdict="approved_partial",
            audited_at="2026-07-12T11:00:00Z",
        )
        self.assertEqual(audit.verdict, "approved_partial")

        audit_values = {
            field: getattr(audit, field)
            for field in PredicateMappingAudit.model_fields
        }
        with self.assertRaises(ValidationError):
            PredicateMappingAudit(
                **{
                    **audit_values,
                    "contract_coverage_class": "exact",
                    "antecedent_witness_verified": True,
                    "falsifying_witness_verified": True,
                    "verdict": "approved_exact",
                }
            )

    def test_predicate_clause_mapping_requires_canonical_executable_locator(self) -> None:
        mapping = predicate_contract().clause_mappings[0]
        values = {
            field: getattr(mapping, field)
            for field in PredicateClauseMapping.model_fields
        }
        with self.assertRaises(ValidationError):
            PredicateClauseMapping(
                **{**values, "predicate_json_pointers": ()}
            )
        with self.assertRaises(ValidationError):
            PredicateClauseMapping(
                **{**values, "predicate_json_pointers": ("domain",)}
            )

    def test_mapping_audit_is_independent_and_replays_every_mutant(self) -> None:
        contract = predicate_contract()
        audit = mapping_audit(contract)
        values = {
            field: getattr(audit, field)
            for field in PredicateMappingAudit.model_fields
        }
        with self.assertRaises(ValidationError):
            PredicateMappingAudit(**{**values, "auditor": contract.mapper})
        with self.assertRaises(ValidationError):
            PredicateMappingAudit(
                **{
                    **values,
                    "mutation_executor": actor("predicate.mutation.runner"),
                }
            )
        with self.assertRaises(ValidationError):
            PredicateMappingAudit(
                **{
                    **values,
                    "replayed_mutation_ids": audit.replayed_mutation_ids[:-1],
                }
            )
        blocking = PredicateMappingFinding(
            finding_id="finding.semantic.gap",
            severity="critical",
            summary="The executable predicate omits one theorem boundary condition.",
            affected_clause_ids=("clause.boundary",),
        )
        with self.assertRaises(ValidationError):
            PredicateMappingAudit(
                **{**values, "findings": (blocking,), "verdict": "approved_exact"}
            )

    def test_realization_and_closure_are_noncompensatory(self) -> None:
        selection, _ = selection_material()
        assessed = realization(selection)
        realized = assessed.move_realizations[0]
        with self.assertRaises(ValidationError):
            CraftMoveRealization.model_validate(
                {
                    **realized.model_dump(mode="python"),
                    "realized_semantic_source_refs": (
                        realized.realized_semantic_source_refs[0],
                        realized.realized_semantic_source_refs[0],
                    ),
                }
            )
        values = {
            field: getattr(assessed, field)
            for field in CraftRealizationAssessment.model_fields
        }
        with self.assertRaises(ValidationError):
            CraftRealizationAssessment(
                **{
                    **values,
                    "phrase_leak_audit_outcome": "fail",
                    "outcome": "pass",
                }
            )

        ready = closure()
        failed_checks = tuple(
            item.model_copy(update={"outcome": "fail"})
            if item.check_kind == "copyright_and_voice"
            else item
            for item in ready.checks
        )
        closure_values = {
            field: getattr(ready, field)
            for field in ProfileCraftClosure.model_fields
            if field != "checks"
        }
        with self.assertRaises(ValidationError):
            ProfileCraftClosure(**closure_values, checks=failed_checks)
        blocked = ProfileCraftClosure(
            **{
                **closure_values,
                "checks": failed_checks,
                "outcome": "blocked",
                "blocking_reasons": (
                    "Copyright or named-voice leakage blocks Phase 4 readiness.",
                ),
            }
        )
        self.assertEqual(blocked.outcome, "blocked")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
