"""Adversarial semantic tests for Phase 4 derived-policy boundaries.

These attacks deliberately preserve Pydantic shape while falsifying derived
claims.  The semantic validators must recompute policy results and exact
lineage instead of trusting output booleans, hashes, or self-reported audits.
"""

from __future__ import annotations

from unittest import mock
import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase4_profile_craft_validation import (
    CLOSER,
    HEAD,
    NOW,
    PROJECT,
    aref,
    authoring_entity,
    eref,
    pc_entity,
    relation,
    world,
)

from econ_theorist import authoring as a
from econ_theorist import profile_craft as pc
from econ_theorist.codec import object_digest
from econ_theorist.models import (
    CreateEntityOp,
    CreateRelationOp,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RelationVersionRef,
    SemanticFacetRef,
    RouteOutcome,
    Snapshot,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V4_HASH, load_route_registry_by_hash
from econ_theorist.profile_craft_validation import (
    ProfileCraftValidationError,
    _build_indices,
    _route_output_topology,
    _validate_assessment,
    _validate_bounded_audits_against_assurance,
    _validate_closure_cross_refs,
    _validate_diagnosis,
    _validate_mapping_audit,
    _validate_profile_stack,
    _validate_revision_diagnosis_lineage,
    _validate_selection,
    validate_profile_craft_projection,
    validate_profile_craft_ready,
    validate_phase4_route_transaction,
)


def _replace_entity(snapshot: Snapshot, replacement: EntityVersion) -> Snapshot:
    """Replace one exact fixture version without changing snapshot currency."""

    replaced = tuple(
        replacement
        if (item.entity_id, item.version)
        == (replacement.entity_id, replacement.version)
        else item
        for item in snapshot.entity_versions
    )
    return snapshot.model_copy(update={"entity_versions": replaced})


def _profile(entities: dict[str, EntityVersion], entity_id: str) -> pc.ProfileCraftPayload:
    return pc.parse_profile_craft_entity(entities[entity_id])


def _authoring(entities: dict[str, EntityVersion], entity_id: str) -> a.AuthoringPayload:
    return a.parse_authoring_entity(entities[entity_id])


def _close_transaction(
    base: Snapshot,
    entities: dict[str, EntityVersion],
    closure_entity: EntityVersion,
    *,
    omit_dependency: str | None = None,
) -> Transaction:
    """Build the canonical close transaction, optionally deleting one hard edge."""

    base_relation = relation(
        "relation.base.validates.profile.craft.adversarial",
        "validates",
        entities["authoring.review.closure"],
        closure_entity,
    )
    assessment_relation = relation(
        "relation.assessment.validates.profile.craft.adversarial",
        "validates",
        entities["craft.assessment"],
        closure_entity,
    )
    dependency_ids = (
        "manuscript.unit",
        "diagnosis.reader.problem",
        "profile.stack",
        "craft.selection",
        "predicate.audit",
    )
    dependency_relations = tuple(
        relation(
            f"relation.{source_id}.depends.profile.craft.adversarial",
            "depends_on",
            entities[source_id],
            closure_entity,
        )
        for source_id in dependency_ids
        if source_id != omit_dependency
    )
    relations = (base_relation, assessment_relation, *dependency_relations)
    evidence_ids = (
        "craft.assessment",
        "craft.selection",
        "manuscript.unit",
        "predicate.audit",
        "diagnosis.reader.problem",
        "profile.stack",
        "authoring.review.closure",
    )
    candidate_refs = (
        eref(closure_entity.entity_id),
        *(
            RelationVersionRef(
                relation_id=item.relation_id,
                version=item.version,
            )
            for item in relations
        ),
    )
    return Transaction(
        transaction_id="transaction.phase4.close.adversarial",
        origin="route_run",
        project_id=PROJECT,
        base_revision=HEAD,
        route_run_id="run.phase4.close.adversarial",
        route_id="close.profile_craft_review",
        route_run_hash="1" * 64,
        context_manifest_hash="2" * 64,
        compiled_context_hash="3" * 64,
        actor=CLOSER,
        intent="Exercise exact Phase 4 closure topology under mutation.",
        operations=(
            CreateEntityOp(entity=closure_entity),
            *(CreateRelationOp(relation=item) for item in relations),
            RecordRouteOutcomeOp(
                outcome=RouteOutcome(
                    route_run_id="run.phase4.close.adversarial",
                    route_id="close.profile_craft_review",
                    outcome="completed_with_candidate",
                    rationale="The candidate closure is submitted for semantic validation.",
                    candidate_refs=candidate_refs,
                )
            ),
        ),
        evidence_refs=tuple(eref(item) for item in evidence_ids),
        created_at=NOW,
        parent_transaction_hash=base.head,
    )


class DeterministicRecomputationAttacks(unittest.TestCase):
    def test_profile_stack_rejects_shape_valid_missing_and_injected_directives(self) -> None:
        snapshot, entities = world()
        stack = _profile(entities, "profile.stack")
        assert isinstance(stack, pc.ResolvedProfileStack)
        indices = _build_indices(snapshot)

        rejected = next(
            item for item in stack.directive_resolutions if item.outcome == "rejected"
        )
        missing = pc.ResolvedProfileStack.model_validate(
            {
                **stack.model_dump(mode="python"),
                "directive_resolutions": tuple(
                    item
                    for item in stack.directive_resolutions
                    if item.directive.directive_id != rejected.directive.directive_id
                ),
            }
        )

        injected_directive = rejected.directive.model_copy(
            update={
                "directive_id": "directive.injected.self.report",
                "conflict_key": "injected.self.report",
            }
        )
        injected_resolution = rejected.model_copy(
            update={"directive": injected_directive}
        )
        injected = pc.ResolvedProfileStack.model_validate(
            {
                **stack.model_dump(mode="python"),
                "directive_resolutions": (
                    *stack.directive_resolutions,
                    injected_resolution,
                ),
            }
        )

        for label, forged in (("missing", missing), ("injected", injected)):
            with self.subTest(label=label), self.assertRaisesRegex(
                ProfileCraftValidationError, "exact deterministic catalog resolution"
            ):
                _validate_profile_stack(indices, forged)

    def test_selection_rejects_self_reported_eligibility_order_and_minimality(self) -> None:
        snapshot, entities = world()
        selection = _profile(entities, "craft.selection")
        assert isinstance(selection, pc.CraftSelectionManifest)
        indices = _build_indices(snapshot)
        decoy = next(item for item in selection.candidates if not item.selected)

        eligibility = pc.CraftSelectionManifest.model_validate(
            {
                **selection.model_dump(mode="python"),
                "candidates": tuple(
                    item
                    if item.selected
                    else pc.CraftCandidateAudit.model_validate(
                        {
                            **item.model_dump(mode="python"),
                            "semantic_inputs_present": False,
                            "exclusion_reason": "missing_semantic_inputs",
                        }
                    )
                    for item in selection.candidates
                ),
            }
        )
        reordered = pc.CraftSelectionManifest.model_validate(
            {
                **selection.model_dump(mode="python"),
                "candidates": tuple(reversed(selection.candidates)),
            }
        )
        claimed_minimal = pc.CraftSelectionManifest.model_validate(
            {
                **selection.model_dump(mode="python"),
                "candidates": tuple(
                    item for item in selection.candidates if item.move_ref != decoy.move_ref
                ),
            }
        )

        for label, forged in (
            ("eligibility", eligibility),
            ("order", reordered),
            ("minimality", claimed_minimal),
        ):
            with self.subTest(label=label), self.assertRaisesRegex(
                ProfileCraftValidationError, "exact deterministic corpus result"
            ):
                _validate_selection(indices, forged)


class ReceiptAndDiagnosisLineageAttacks(unittest.TestCase):
    def test_exact_mapping_cannot_receive_unqualified_partial_approval(self) -> None:
        snapshot, entities = world()
        audit = _profile(entities, "predicate.audit")
        assert isinstance(audit, pc.PredicateMappingAudit)
        self.assertEqual(audit.contract_coverage_class, "exact")
        self.assertEqual(audit.verdict, "approved_exact")

        unqualified_partial = audit.model_copy(
            update={"verdict": "approved_partial"}
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError,
            "approved_partial requires at least one deterministic typed predicate limitation",
        ):
            _validate_mapping_audit(_build_indices(snapshot), unqualified_partial)

    def test_predicate_auditor_is_independent_of_assurance_assembler_and_writer(self) -> None:
        snapshot, entities = world()
        audit = _profile(entities, "predicate.audit")
        assurance = _authoring(entities, "assurance.bundle")
        paper = _authoring(entities, "entity.paper")
        assert isinstance(audit, pc.PredicateMappingAudit)
        assert isinstance(assurance, a.AssuranceBundle)
        assert isinstance(paper, a.PaperIR)

        for label, conflicted_actor in (
            ("assembler", assurance.assembled_by),
            ("canonical_writer", paper.canonical_writer),
        ):
            forged = audit.model_copy(update={"auditor": conflicted_actor})
            with self.subTest(label=label), self.assertRaisesRegex(
                ProfileCraftValidationError,
                "AssuranceBundle assembler, and every canonical writer",
            ):
                _validate_mapping_audit(_build_indices(snapshot), forged)

    def test_partial_approval_warns_for_every_non_exact_clause(self) -> None:
        snapshot, entities = world()
        contract = _profile(entities, "predicate.contract")
        audit = _profile(entities, "predicate.audit")
        assert isinstance(contract, pc.ObligationPredicateContract)
        assert isinstance(audit, pc.PredicateMappingAudit)

        non_exact = tuple(
            item.model_copy(update={"relation": "partial"})
            if index < 2
            else item
            for index, item in enumerate(contract.clause_mappings)
        )
        partial_contract = pc.ObligationPredicateContract.model_validate(
            {
                **contract.model_dump(mode="python"),
                "coverage_class": "partial",
                "clause_mappings": non_exact,
            }
        )
        warning_one = pc.PredicateMappingFinding(
            finding_id="finding.partial.first",
            severity="warning",
            summary="The first clause is represented only partially.",
            affected_clause_ids=(non_exact[0].obligation_clause_id,),
            limitation_kinds=(
                "nonexact_clause_mapping",
                "coverage_below_exact",
            ),
        )
        partial_audit = pc.PredicateMappingAudit.model_validate(
            {
                **audit.model_dump(mode="python"),
                "contract_hash": object_digest(partial_contract),
                "contract_coverage_class": "partial",
                "findings": (warning_one,),
                "verdict": "approved_partial",
            }
        )
        partial_snapshot = _replace_entity(
            snapshot,
            pc_entity("predicate.contract", partial_contract),
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "warning for every non-exact clause"
        ):
            _validate_mapping_audit(_build_indices(partial_snapshot), partial_audit)

        warning_two = pc.PredicateMappingFinding(
            finding_id="finding.partial.second",
            severity="warning",
            summary="The second clause is represented only partially.",
            affected_clause_ids=(non_exact[1].obligation_clause_id,),
            limitation_kinds=("nonexact_clause_mapping",),
        )
        complete_audit = partial_audit.model_copy(
            update={"findings": (warning_one, warning_two)}
        )
        _validate_mapping_audit(_build_indices(partial_snapshot), complete_audit)

    def test_partial_approval_cannot_omit_any_typed_limitation_dimension(self) -> None:
        snapshot, entities = world(bounded_partial=True)
        contract = _profile(entities, "predicate.contract")
        audit = _profile(entities, "predicate.audit")
        assert isinstance(contract, pc.ObligationPredicateContract)
        assert isinstance(audit, pc.PredicateMappingAudit)
        warning = audit.findings[0]

        for omitted in (
            "domain_not_equal",
            "quantifier_not_equivalent",
            "coverage_below_exact",
        ):
            forged_warning = warning.model_copy(
                update={
                    "limitation_kinds": tuple(
                        kind for kind in warning.limitation_kinds if kind != omitted
                    )
                }
            )
            forged = audit.model_copy(update={"findings": (forged_warning,)})
            with self.subTest(omitted=omitted), self.assertRaisesRegex(
                ProfileCraftValidationError,
                "warning limitations must equal every deterministic",
            ):
                _validate_mapping_audit(_build_indices(snapshot), forged)

        mutations = tuple(
            item.model_copy(update={"detected": False})
            if item.mutation_kind == "omitted_assumption"
            else item
            for item in contract.mutation_tests
        )
        unexecutable_id = next(
            item.mutation_id
            for item in mutations
            if item.mutation_kind == "omitted_assumption"
        )
        unexecutable_contract = contract.model_copy(
            update={"mutation_tests": mutations}
        )
        unexecutable_audit = audit.model_copy(
            update={
                "contract_hash": object_digest(unexecutable_contract),
                "unexecutable_mutation_ids": (unexecutable_id,),
            }
        )
        unexecutable_snapshot = _replace_entity(
            snapshot,
            pc_entity("predicate.contract", unexecutable_contract),
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError,
            "warning limitations must equal every deterministic",
        ):
            _validate_mapping_audit(
                _build_indices(unexecutable_snapshot), unexecutable_audit
            )

    def test_closure_cannot_forge_exact_projection_of_partial_audit(self) -> None:
        snapshot, entities = world(bounded_partial=True)
        closure = _profile(entities, "profile.craft.closure")
        assert isinstance(closure, pc.ProfileCraftClosure)
        forged = closure.model_copy(
            update={
                "predicate_mapping_coverage_classes": ("exact",),
                "predicate_limitation_kinds": (),
            }
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError,
            "coverage classes do not exactly project audit order",
        ):
            _validate_closure_cross_refs(_build_indices(snapshot), forged)

    def test_receipt_audit_bijection_rejects_missing_duplicate_and_foreign_binding(self) -> None:
        snapshot, entities = world()
        audit = _profile(entities, "predicate.audit")
        contract = _profile(entities, "predicate.contract")
        assurance = _authoring(entities, "assurance.bundle")
        assert isinstance(audit, pc.PredicateMappingAudit)
        assert isinstance(contract, pc.ObligationPredicateContract)
        assert isinstance(assurance, a.AssuranceBundle)
        indices = _build_indices(snapshot)

        for label, audits in (("missing", ()), ("duplicate", (audit, audit))):
            with self.subTest(label=label), self.assertRaisesRegex(
                ProfileCraftValidationError, "every AssuranceBundle receipt exactly once"
            ):
                _validate_bounded_audits_against_assurance(
                    indices,
                    audits,
                    assurance,
                    eref("assurance.bundle"),
                )

        foreign_contract = pc.ObligationPredicateContract.model_validate(
            {
                **contract.model_dump(mode="python"),
                "assurance_bundle_ref": eref("assurance.foreign"),
            }
        )
        foreign_snapshot = _replace_entity(
            snapshot,
            pc_entity("predicate.contract", foreign_contract),
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "binds another AssuranceBundle"
        ):
            _validate_bounded_audits_against_assurance(
                _build_indices(foreign_snapshot),
                (audit,),
                assurance,
                eref("assurance.bundle"),
            )

    def test_diagnosis_rejects_unit_review_and_finding_lineage_or_hash_substitution(self) -> None:
        snapshot, entities = world()
        diagnosis = _profile(entities, "diagnosis.reader.problem")
        unit = _authoring(entities, "diagnosed.manuscript.unit")
        finding = _authoring(entities, "finding.economic.diagnosed")
        assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
        assert isinstance(unit, a.ManuscriptUnit)
        assert isinstance(finding, a.ReviewFinding)

        bad_review_binding = diagnosis.diagnostic_review_bindings[0].model_copy(
            update={"payload_hash": "0" * 64}
        )
        hash_substitution = pc.ReaderProblemDiagnosis.model_validate(
            {
                **diagnosis.model_dump(mode="python"),
                "diagnostic_review_bindings": (bad_review_binding,),
            }
        )
        with self.assertRaisesRegex(ProfileCraftValidationError, "another manuscript"):
            _validate_diagnosis(_build_indices(snapshot), hash_substitution)

        foreign_unit = a.ManuscriptUnit.model_validate(
            {
                **unit.model_dump(mode="python"),
                "paper_ir_ref": eref("paper.foreign"),
            }
        )
        unit_snapshot = _replace_entity(
            snapshot,
            authoring_entity("diagnosed.manuscript.unit", foreign_unit),
        )
        unit_substitution = pc.ReaderProblemDiagnosis.model_validate(
            {
                **diagnosis.model_dump(mode="python"),
                "inspected_manuscript_unit_binding": pc.ProjectPayloadBinding(
                    entity_ref=eref("diagnosed.manuscript.unit"),
                    payload_hash=object_digest(foreign_unit),
                ),
            }
        )
        with self.assertRaisesRegex(ProfileCraftValidationError, "design lineage"):
            _validate_diagnosis(_build_indices(unit_snapshot), unit_substitution)

        foreign_finding = a.ReviewFinding.model_validate(
            {
                **finding.model_dump(mode="python"),
                "manuscript_unit_ref": eref("manuscript.foreign"),
            }
        )
        finding_snapshot = _replace_entity(
            snapshot,
            authoring_entity("finding.economic.diagnosed", foreign_finding),
        )
        finding_substitution = pc.ReaderProblemDiagnosis.model_validate(
            {
                **diagnosis.model_dump(mode="python"),
                "diagnostic_finding_bindings": (
                    pc.ProjectPayloadBinding(
                        entity_ref=eref("finding.economic.diagnosed"),
                        payload_hash=object_digest(foreign_finding),
                    ),
                ),
            }
        )
        with self.assertRaisesRegex(ProfileCraftValidationError, "exact review"):
            _validate_diagnosis(
                _build_indices(finding_snapshot),
                finding_substitution,
            )

    def test_craft_eligibility_requires_an_exact_blocking_reader_failure(self) -> None:
        snapshot, entities = world()
        diagnosis = _profile(entities, "diagnosis.reader.problem")
        finding = _authoring(entities, "finding.economic.diagnosed")
        assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
        assert isinstance(finding, a.ReviewFinding)

        nonblocking = a.ReviewFinding.model_validate(
            {
                **finding.model_dump(mode="python"),
                "severity": "warning",
                "blocking": False,
            }
        )
        forged_snapshot = _replace_entity(
            snapshot,
            authoring_entity("finding.economic.diagnosed", nonblocking),
        )
        forged_diagnosis = pc.ReaderProblemDiagnosis.model_validate(
            {
                **diagnosis.model_dump(mode="python"),
                "diagnostic_finding_bindings": (
                    pc.ProjectPayloadBinding(
                        entity_ref=eref("finding.economic.diagnosed"),
                        payload_hash=object_digest(nonblocking),
                    ),
                ),
            }
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "blocked closure findings"
        ):
            _validate_diagnosis(_build_indices(forged_snapshot), forged_diagnosis)

    def test_semantic_input_ids_cannot_alias_one_valid_source_field(self) -> None:
        snapshot, entities = world()
        diagnosis = _profile(entities, "diagnosis.reader.problem")
        assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
        aliased_source = diagnosis.semantic_input_bindings[-1]
        forged_bindings = tuple(
            binding.model_copy(
                update={
                    "source_ref": aliased_source.source_ref,
                    "source_kind": aliased_source.source_kind,
                }
            )
            for binding in diagnosis.semantic_input_bindings
        )
        forged = pc.ReaderProblemDiagnosis.model_validate(
            {
                **diagnosis.model_dump(mode="python"),
                "semantic_input_bindings": forged_bindings,
            }
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "typed source"
        ):
            _validate_diagnosis(_build_indices(snapshot), forged)

    def test_mechanism_packet_rejects_comparative_statics_extractor_path(self) -> None:
        snapshot, entities = world()
        diagnosis = _profile(entities, "diagnosis.reader.problem")
        assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
        operative = diagnosis.semantic_input_bindings[1]
        assert isinstance(operative.source_ref, SemanticFacetRef)
        cross_archetype_ref = operative.source_ref.model_copy(
            update={
                "field_path": (
                    "/payload/result_packets/0/archetype_module/"
                    "competing_effects/content"
                )
            }
        )
        forged_bindings = tuple(
            binding.model_copy(update={"source_ref": cross_archetype_ref})
            if binding.input_id == operative.input_id
            else binding
            for binding in diagnosis.semantic_input_bindings
        )
        forged = pc.ReaderProblemDiagnosis.model_validate(
            {
                **diagnosis.model_dump(mode="python"),
                "semantic_input_bindings": forged_bindings,
            }
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError,
            "field path is invalid|exact typed source selector",
        ):
            _validate_diagnosis(_build_indices(snapshot), forged)


class ComposeLineageAttacks(unittest.TestCase):
    def test_revision_requires_diagnosis_closure_and_brief_failure_lineage(self) -> None:
        snapshot, entities = world()
        diagnosis = _profile(entities, "diagnosis.reader.problem")
        blocked = _authoring(entities, "review.closure.diagnosed")
        brief = _authoring(entities, "revision.brief.diagnosed")
        assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
        assert isinstance(blocked, a.ReviewClosure)
        assert isinstance(brief, a.RevisionBrief)

        brief_ref = eref("revision.brief.diagnosed")
        closure_ref = eref("review.closure.diagnosed")
        indices = _build_indices(snapshot)
        _validate_revision_diagnosis_lineage(
            indices,
            diagnosis=diagnosis,
            prior_ref=eref("diagnosed.manuscript.unit"),
            closure_ref=closure_ref,
            closure=blocked,
            brief_ref=brief_ref,
            brief=brief,
        )

        with self.assertRaisesRegex(
            ProfileCraftValidationError, "exact prior manuscript"
        ):
            _validate_revision_diagnosis_lineage(
                indices,
                diagnosis=diagnosis,
                prior_ref=eref("manuscript.unit"),
                closure_ref=closure_ref,
                closure=blocked,
                brief_ref=brief_ref,
                brief=brief,
            )

        outside_review = blocked.model_copy(
            update={"economic_reader_review_ref": eref("review.economic")}
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "does not bind the supplied closure and brief"
        ):
            _validate_revision_diagnosis_lineage(
                indices,
                diagnosis=diagnosis,
                prior_ref=eref("diagnosed.manuscript.unit"),
                closure_ref=closure_ref,
                closure=outside_review,
                brief_ref=brief_ref,
                brief=brief,
            )

        foreign_brief = brief.model_copy(
            update={"finding_refs": (eref("finding.foreign"),)}
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "does not bind the supplied closure and brief"
        ):
            _validate_revision_diagnosis_lineage(
                indices,
                diagnosis=diagnosis,
                prior_ref=eref("diagnosed.manuscript.unit"),
                closure_ref=closure_ref,
                closure=blocked,
                brief_ref=brief_ref,
                brief=foreign_brief,
            )

    def test_compose_output_binds_source_revision_to_exact_before_head(self) -> None:
        snapshot, entities = world()
        unit = _authoring(entities, "manuscript.unit")
        assert isinstance(unit, a.ManuscriptUnit)
        registry = load_route_registry_by_hash(ROUTE_REGISTRY_V4_HASH)
        route = next(
            item
            for item in registry.routes
            if item.route_id == "compose.profiled_manuscript_unit"
        )
        transaction = Transaction(
            transaction_id="transaction.phase4.compose.source.attack",
            origin="route_run",
            project_id=PROJECT,
            base_revision=HEAD,
            route_run_id="run.phase4.compose.source.attack",
            route_id=route.route_id,
            route_run_hash="1" * 64,
            context_manifest_hash="2" * 64,
            compiled_context_hash="3" * 64,
            actor=unit.canonical_writer,
            intent="Attempt to compose from an unrelated source revision.",
            operations=(
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id="run.phase4.compose.source.attack",
                        route_id=route.route_id,
                        outcome="completed_with_candidate",
                        rationale="Submit a shape-valid but revision-forged manuscript.",
                        candidate_refs=(eref("manuscript.unit"),),
                    )
                ),
            ),
            evidence_refs=(eref("entity.paper"),),
            created_at=NOW,
            parent_transaction_hash=snapshot.head,
        )
        inputs = {
            "PaperIR": (eref("entity.paper"),),
            "ReaderPath": (eref("entity.reader.path"),),
            "ResultContractSet": (eref("entity.result.contracts"),),
        }
        outputs = {
            "ManuscriptUnit": ((eref("manuscript.unit"), unit),),
        }
        self.assertNotEqual(unit.source_state_revision, snapshot.head)
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "profiled manuscript output crosses lineages"
        ):
            _route_output_topology(
                snapshot,
                snapshot,
                transaction,
                route,
                inputs,
                outputs,
                (),
            )


class AssessmentAndClosureAttacks(unittest.TestCase):
    def test_projection_ready_status_is_not_sticky_after_decision_supersession(
        self,
    ) -> None:
        snapshot, _entities = world()
        closure_ref = eref("profile.craft.closure")
        self.assertIn(
            closure_ref,
            validate_profile_craft_projection(snapshot).ready_closure_refs,
        )

        current_decisions = dict(snapshot.current_decisions)
        current_decisions["decision.theory"] = 2
        superseded = snapshot.model_copy(
            update={"current_decisions": current_decisions}
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError,
            "TargetProfile Decision is not current and effective",
        ):
            validate_profile_craft_ready(superseded, closure_ref)
        self.assertNotIn(
            closure_ref,
            validate_profile_craft_projection(superseded).ready_closure_refs,
        )

    def test_closure_target_reader_fit_requires_the_exact_reader_evidence(self) -> None:
        snapshot, entities = world()
        closure = _profile(entities, "profile.craft.closure")
        assert isinstance(closure, pc.ProfileCraftClosure)
        reader_check = next(
            item for item in closure.checks if item.check_kind == "target_reader_fit"
        )
        self.assertGreater(len(reader_check.evidence_refs), 1)
        evidence_attacks = tuple(
            reader_check.evidence_refs[:index] + reader_check.evidence_refs[index + 1 :]
            for index in range(1, len(reader_check.evidence_refs))
        ) + (reader_check.evidence_refs + (eref("entity.paper"),),)
        for forged_evidence in evidence_attacks:
            with self.subTest(forged_evidence=forged_evidence):
                forged_reader_check = reader_check.model_copy(
                    update={"evidence_refs": forged_evidence}
                )
                forged = closure.model_copy(
                    update={
                        "checks": tuple(
                            forged_reader_check
                            if item.check_kind == "target_reader_fit"
                            else item
                            for item in closure.checks
                        )
                    }
                )

                with self.assertRaisesRegex(
                    ProfileCraftValidationError,
                    "target-reader-fit closure check is not derived from its exact reader outcome",
                ):
                    _validate_closure_cross_refs(_build_indices(snapshot), forged)

    def test_craft_assessor_is_distinct_from_all_three_base_reviewers(self) -> None:
        snapshot, entities = world()
        assessment = _profile(entities, "craft.assessment")
        formal_review = _authoring(entities, "review.formal")
        assert isinstance(assessment, pc.CraftRealizationAssessment)
        assert isinstance(formal_review, a.ReviewRecord)

        conflicted = assessment.model_copy(
            update={"assessor": formal_review.reviewer}
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError,
            "assessor, writer, and three base reviewers must be pairwise distinct",
        ):
            _validate_assessment(_build_indices(snapshot), conflicted)

    def test_target_reader_flags_are_derived_from_the_exact_reviews(self) -> None:
        snapshot, entities = world()
        assessment = _profile(entities, "craft.assessment")
        assert isinstance(assessment, pc.CraftRealizationAssessment)
        forged_reader = assessment.target_reader_outcome.model_copy(
            update={"nearby_case_predictable": False, "outcome": "fail"}
        )
        forged = assessment.model_copy(
            update={"target_reader_outcome": forged_reader, "outcome": "revise"}
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "target-reader outcome"
        ):
            _validate_assessment(_build_indices(snapshot), forged)

    def test_resolution_requires_affected_assertions_and_semantic_sources(self) -> None:
        snapshot, entities = world()
        assessment = _profile(entities, "craft.assessment")
        unit = _authoring(entities, "manuscript.unit")
        assert isinstance(assessment, pc.CraftRealizationAssessment)
        assert isinstance(unit, a.ManuscriptUnit)

        wrong_assertion = assessment.move_realizations[0].model_copy(
            update={"realized_assertion_ids": (unit.spans[-1].assertion_id,)}
        )
        assertion_forgery = assessment.model_copy(
            update={"move_realizations": (wrong_assertion,)}
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "resolution check"
        ):
            _validate_assessment(_build_indices(snapshot), assertion_forgery)

        sources = assessment.move_realizations[0].realized_semantic_source_refs
        source_attacks = (
            sources[:-1],
            tuple(reversed(sources)),
            (
                sources[0].model_copy(update={"semantic_hash": "0" * 64}),
                *sources[1:],
            ),
        )
        for forged_sources in source_attacks:
            with self.subTest(forged_sources=forged_sources):
                forged_realization = assessment.move_realizations[0].model_copy(
                    update={"realized_semantic_source_refs": forged_sources}
                )
                source_forgery = assessment.model_copy(
                    update={"move_realizations": (forged_realization,)}
                )
                with self.assertRaisesRegex(
                    ProfileCraftValidationError,
                    "craft realization lacks exact semantic",
                ):
                    _validate_assessment(_build_indices(snapshot), source_forgery)

    def test_ready_rejects_a_coherent_pre_manuscript_diagnosis(self) -> None:
        snapshot, entities = world()
        diagnosis = _profile(entities, "diagnosis.reader.problem")
        selection = _profile(entities, "craft.selection")
        assessment = _profile(entities, "craft.assessment")
        closure = _profile(entities, "profile.craft.closure")
        assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
        assert isinstance(selection, pc.CraftSelectionManifest)
        assert isinstance(assessment, pc.CraftRealizationAssessment)
        assert isinstance(closure, pc.ProfileCraftClosure)

        pre_manuscript = pc.ReaderProblemDiagnosis.model_validate(
            {
                **diagnosis.model_dump(mode="python"),
                "inspected_manuscript_unit_binding": None,
                "no_prior_manuscript_unit_reason": "initial_composition_not_yet_realized",
                "diagnostic_review_bindings": (),
                "diagnostic_finding_bindings": (),
                "blocked_review_closure_binding": None,
                "revision_brief_binding": None,
                "no_prior_review_reason": "initial_composition_not_yet_reviewable",
                "diagnostic_categories": (),
                "causal_class": "initial_planning",
                "resolution_requirements": (),
                "semantic_input_bindings": (),
                "affected_section_ids": (),
                "required_resolution_ids": (),
                "required_semantic_input_ids": (),
                "upstream_science_status": "resolved",
                "craft_eligible": False,
                "upstream_repair_route": "design.reader_path",
                "evidence_refs": (
                    diagnosis.paper_ir_ref,
                    diagnosis.reader_path_ref,
                    diagnosis.profile_stack_ref,
                    diagnosis.result_contract_set_binding.entity_ref,
                ),
            }
        )
        pre_selection = selection.model_copy(
            update={"diagnosis_hash": object_digest(pre_manuscript)}
        )
        pre_assessment = assessment.model_copy(
            update={"selection_manifest_hash": object_digest(pre_selection)}
        )
        pre_closure = closure.model_copy(
            update={
                "reader_problem_diagnosis_hash": object_digest(pre_manuscript),
                "craft_selection": closure.craft_selection.model_copy(
                    update={"payload_hash": object_digest(pre_selection)}
                ),
                "realization_assessment": closure.realization_assessment.model_copy(
                    update={"payload_hash": object_digest(pre_assessment)}
                ),
            }
        )
        forged = snapshot
        for replacement in (
            pc_entity("diagnosis.reader.problem", pre_manuscript),
            pc_entity("craft.selection", pre_selection),
            pc_entity("craft.assessment", pre_assessment),
            pc_entity("profile.craft.closure", pre_closure),
        ):
            forged = _replace_entity(forged, replacement)

        with mock.patch(
            "econ_theorist.profile_craft_validation.validate_authoring_ready"
        ), self.assertRaisesRegex(
            ProfileCraftValidationError, "pre-manuscript diagnosis cannot become ready"
        ):
            validate_profile_craft_ready(forged, eref("profile.craft.closure"))

    def test_passing_assessment_rejects_failing_and_foreign_authoring_reviews(self) -> None:
        snapshot, entities = world()
        assessment = _profile(entities, "craft.assessment")
        review = _authoring(entities, "review.formal")
        assert isinstance(assessment, pc.CraftRealizationAssessment)
        assert isinstance(review, a.ReviewRecord)
        assert isinstance(review.assessment, a.FormalFidelityAssessment)

        failed_formal = a.FormalFidelityAssessment.model_validate(
            {
                **review.assessment.model_dump(mode="python"),
                "theorem_statement_exact": False,
            }
        )
        failed_review = a.ReviewRecord.model_validate(
            {
                **review.model_dump(mode="python"),
                "assessment": failed_formal,
            }
        )
        failed_snapshot = _replace_entity(
            snapshot,
            authoring_entity("review.formal", failed_review),
        )
        failed_claim = pc.CraftRealizationAssessment.model_validate(
            {
                **assessment.model_dump(mode="python"),
                "formal_fidelity_review_hash": object_digest(failed_review),
            }
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "three passing authoring reviews"
        ):
            _validate_assessment(_build_indices(failed_snapshot), failed_claim)

        foreign_review = a.ReviewRecord.model_validate(
            {
                **review.model_dump(mode="python"),
                "manuscript_unit_ref": eref("manuscript.foreign"),
                "reviewed_artifact_ref": aref("artifact.manuscript.foreign", "d" * 64),
            }
        )
        foreign_snapshot = _replace_entity(
            snapshot,
            authoring_entity("review.formal", foreign_review),
        )
        foreign_claim = pc.CraftRealizationAssessment.model_validate(
            {
                **assessment.model_dump(mode="python"),
                "formal_fidelity_review_hash": object_digest(foreign_review),
            }
        )
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "review role or manuscript lineage"
        ):
            _validate_assessment(_build_indices(foreign_snapshot), foreign_claim)

    def test_close_transaction_rejects_forged_source_revision_and_missing_edge(self) -> None:
        base, entities = world(include_closure=False)
        _full, full_entities = world(include_closure=True)
        closure = _profile(full_entities, "profile.craft.closure")
        assert isinstance(closure, pc.ProfileCraftClosure)
        registry = load_route_registry_by_hash(ROUTE_REGISTRY_V4_HASH)
        route = next(
            item for item in registry.routes if item.route_id == "close.profile_craft_review"
        )

        forged_closure = pc.ProfileCraftClosure.model_validate(
            {
                **closure.model_dump(mode="python"),
                "source_state_revision": "e" * 64,
            }
        )
        forged_entity = pc_entity("profile.craft.closure", forged_closure)
        with self.assertRaisesRegex(
            ProfileCraftValidationError, "exact inputs mismatch"
        ):
            validate_phase4_route_transaction(
                base,
                _close_transaction(base, entities, forged_entity),
                route,
            )

        closure_entity = full_entities["profile.craft.closure"]
        missing_edge = _close_transaction(
            base,
            entities,
            closure_entity,
            omit_dependency="profile.stack",
        )
        with mock.patch(
            "econ_theorist.profile_craft_validation.validate_authoring_ready"
        ), self.assertRaisesRegex(
            ProfileCraftValidationError, "profile/craft stack lacks its exact invalidating relation"
        ):
            validate_phase4_route_transaction(base, missing_edge, route)


if __name__ == "__main__":
    unittest.main()
