"""Executable and adversarial tests for Phase 4 evidence protocols."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase3_assurance_evidence import finite_receipt

from econ_theorist import authoring as a
from econ_theorist import profile_craft as pc
from econ_theorist.authoring_validation import reproducible_harness_artifact_bytes
from econ_theorist.codec import canonical_json_bytes, object_digest, sha256_digest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    CreateEntityOp,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    RegisterArtifactOp,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from econ_theorist.profile_craft_execution import (
    PHRASE_AUDIT_LIMITATIONS,
    PredicateMutationReplayArtifact,
    PredicateMutationResultArtifact,
    ProfileCraftExecutionError,
    build_mutated_predicate_bytes,
    build_mutation_replay_artifact,
    build_phrase_leak_audit,
    build_predicate_mutation_result,
    build_predicate_witness_artifact,
    canonical_json_pointer_get,
    predicate_fragment_hash,
    protected_material_projection,
    replay_contract_mutations,
    selected_source_cards,
    witness_assignment_bytes,
)
from econ_theorist.profile_craft_policy import load_craft_corpus
from econ_theorist.runtime.layout import StoreLayout
from econ_theorist.runtime.objects import ObjectStore
from econ_theorist.runtime.phase4_artifacts import (
    validate_phase4_operational_artifacts,
)


MAPPER = Actor(kind="agent", actor_id="agent.phase4.mapper.fixture")
OTHER = Actor(kind="agent", actor_id="agent.phase4.other.fixture")
PROJECT = "project.phase4.execution.fixture"
NOW = "2026-07-12T15:00:00Z"
HEAD = "9" * 64


def _ref(artifact_id: str, data: bytes) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id,
        version=1,
        content_hash=sha256_digest(data),
    )


def _mapping(
    predicate_bytes: bytes,
    clause_id: str,
    kind: str,
    relation: str,
    pointers: tuple[str, ...],
) -> pc.PredicateClauseMapping:
    return pc.PredicateClauseMapping(
        obligation_clause_id=clause_id,
        clause_kind=kind,  # type: ignore[arg-type]
        relation=relation,  # type: ignore[arg-type]
        predicate_json_pointers=pointers,
        predicate_fragment_hash=predicate_fragment_hash(
            predicate_bytes,
            obligation_clause_id=clause_id,
            relation=relation,
            pointers=pointers,
        ),
        explanation="This mapping states exactly which canonical input fragment is covered.",
    )


def _contract_material():
    receipt = finite_receipt()
    harness = reproducible_harness_artifact_bytes(receipt)
    predicate_bytes = harness["input"]
    mappings = (
        _mapping(
            predicate_bytes,
            "clause.domain",
            "domain",
            "narrowed",
            ("/domain",),
        ),
        _mapping(
            predicate_bytes,
            "clause.quantifier",
            "quantifier",
            "partial",
            ("/domain/cases",),
        ),
        _mapping(
            predicate_bytes,
            "clause.assumption.nonnegative",
            "assumption",
            "omitted",
            (),
        ),
        _mapping(
            predicate_bytes,
            "clause.conclusion",
            "conclusion",
            "partial",
            ("/relation",),
        ),
        _mapping(
            predicate_bytes,
            "clause.boundary",
            "boundary",
            "partial",
            ("/domain/cases/0",),
        ),
    )
    assets: dict[tuple[str, int, str], bytes] = {}

    assignment_bytes = witness_assignment_bytes(predicate_bytes, "case.zero")
    assignment_ref = _ref("artifact.assignment.case.zero", assignment_bytes)
    assets[(assignment_ref.artifact_id, assignment_ref.version, assignment_ref.content_hash)] = assignment_bytes
    witness = build_predicate_witness_artifact(
        contract_id="predicate.contract.fixture",
        witness_id="witness.domain.fixture",
        witness_kind="domain_member",
        case_id="case.zero",
        assignment_ref=assignment_ref,
        assignment_bytes=assignment_bytes,
        predicate_bytes=predicate_bytes,
        limitations="This exact assignment is one finite-domain witness only.",
    )
    witness_bytes = canonical_json_bytes(witness)
    witness_ref = _ref("artifact.witness.domain.fixture", witness_bytes)
    assets[(witness_ref.artifact_id, witness_ref.version, witness_ref.content_hash)] = witness_bytes

    mutation_descriptors: list[pc.PredicateMutationTest] = []
    mutation_results: list[PredicateMutationResultArtifact] = []
    for kind in (
        "empty_domain",
        "constant_true",
        "conclusion_flip",
        "domain_narrowing",
        "omitted_assumption",
    ):
        mutation_id = f"mutation.fixture.{kind}"
        mutant_bytes = build_mutated_predicate_bytes(predicate_bytes, kind)
        mutant_ref = _ref(f"artifact.mutant.{kind}", mutant_bytes)
        assets[(mutant_ref.artifact_id, mutant_ref.version, mutant_ref.content_hash)] = mutant_bytes
        result = build_predicate_mutation_result(
            contract_id="predicate.contract.fixture",
            mutation_id=mutation_id,
            mutation_kind=kind,
            predicate_bytes=predicate_bytes,
            mappings=mappings,
            mutated_predicate_ref=mutant_ref,
            mutated_predicate_bytes=mutant_bytes,
            limitations="This attack tests only the exact finite executable mapping.",
        )
        result_bytes = canonical_json_bytes(result)
        result_ref = _ref(f"artifact.mutant.result.{kind}", result_bytes)
        assets[(result_ref.artifact_id, result_ref.version, result_ref.content_hash)] = result_bytes
        mutation_results.append(result)
        mutation_descriptors.append(
            pc.PredicateMutationTest(
                mutation_id=mutation_id,
                mutation_kind=kind,  # type: ignore[arg-type]
                mutated_predicate_ref=mutant_ref,
                result_ref=result_ref,
                detected=result.detected,
            )
        )

    contract = pc.ObligationPredicateContract(
        contract_id="predicate.contract.fixture",
        assurance_bundle_ref=EntityVersionRef(
            entity_id="assurance.bundle.fixture", version=1
        ),
        assurance_bundle_hash="a" * 64,
        receipt_id=receipt.receipt_id,
        receipt_hash=object_digest(receipt),
        obligation_ref=receipt.obligation_ref,
        obligation_hash="b" * 64,
        claim_graph_ref=receipt.claim_graph_ref,
        claim_graph_hash="c" * 64,
        formal_model_ref=EntityVersionRef(entity_id="formal.model.fixture", version=1),
        formal_model_hash="d" * 64,
        assumption_map_ref=EntityVersionRef(entity_id="assumptions.fixture", version=1),
        assumption_map_hash="e" * 64,
        obligation_clause_ids=tuple(item.obligation_clause_id for item in mappings),
        obligation_assumption_ids=("assumption.nonnegative",),
        mapped_assumption_ids=(),
        clause_mappings=mappings,
        domain_relation="narrowed",
        quantifier_relation="weakened",
        execution_scope="finite_sample",
        coverage_class="diagnostic",
        predicate_artifact_ref=receipt.input_ref,
        code_ref=receipt.code_ref,
        antecedent_satisfiable=False,
        predicate_can_return_false=False,
        witnesses=(
            pc.PredicateWitness(
                witness_id=witness.witness_id,
                case_id=witness.case_id,
                witness_kind=witness.witness_kind,
                artifact_ref=witness_ref,
                explanation="The stored assignment is a member of the sealed finite domain.",
            ),
        ),
        mutation_tests=tuple(mutation_descriptors),
        tolerance_policy="exact",
        mapper=MAPPER,
        mapped_at="2026-07-12T15:00:00Z",
        limitations="Finite diagnostic coverage is not a universal theorem certificate.",
    )

    def read(reference: ArtifactDependencyRef) -> bytes:
        return assets[(reference.artifact_id, reference.version, reference.content_hash)]

    return contract, receipt, predicate_bytes, assets, read, tuple(mutation_results)


def _assurance(receipt: a.ToolHarnessReceipt) -> a.AssuranceBundle:
    proof = a.ProofAudit(
        audit_id="audit.proof.fixture",
        claim_graph_ref=receipt.claim_graph_ref,
        claim_id=receipt.claim_id,
        obligation_ref=receipt.obligation_ref,
        formal_model_ref=EntityVersionRef(entity_id="formal.model.fixture", version=1),
        assumption_map_ref=EntityVersionRef(entity_id="assumptions.fixture", version=1),
        proof_artifact_ref=ArtifactDependencyRef(
            artifact_id="artifact.proof.fixture", version=1, content_hash="1" * 64
        ),
        verification_record_ref=EntityVersionRef(
            entity_id="verification.record.fixture", version=1
        ),
        rederivation_ref=EntityVersionRef(
            entity_id="rederivation.fixture", version=1
        ),
        originating_verifier=Actor(kind="agent", actor_id="agent.verifier.fixture"),
        auditor=Actor(kind="agent", actor_id="agent.auditor.fixture"),
        audit_report_ref=ArtifactDependencyRef(
            artifact_id="artifact.proof.audit.fixture",
            version=1,
            content_hash="2" * 64,
        ),
        outcome="passed",
        comparison_outcome="agrees",
        limitations="This proof audit is limited to the maintained obligation.",
        audited_at=NOW,
    )
    nonapplicable = a.HarnessNonApplicabilityRecord(
        record_id="nonapplicable.symbolic.fixture",
        family="symbolic_identity",
        claim_graph_ref=receipt.claim_graph_ref,
        claim_id=receipt.claim_id,
        obligation_ref=receipt.obligation_ref,
        reason_code="no_algebraic_identity",
        explanation="The maintained inequality is not an algebraic identity check.",
        evidence_refs=(receipt.obligation_ref,),
        determined_by=Actor(kind="agent", actor_id="agent.assurance.fixture"),
    )
    return a.AssuranceBundle(
        package_ref=EntityVersionRef(entity_id="package.fixture", version=1),
        g5_decision_ref=DecisionVersionRef(decision_id="decision.g5.fixture", version=1),
        claim_graph_ref=receipt.claim_graph_ref,
        headline_claim_id=receipt.claim_id,
        formal_model_ref=proof.formal_model_ref,
        assumption_map_ref=proof.assumption_map_ref,
        verification_bundle_ref=EntityVersionRef(
            entity_id="verification.bundle.fixture", version=1
        ),
        rederivation_refs=(proof.rederivation_ref,),
        proof_audits=(proof,),
        tool_receipts=(receipt,),
        tool_non_applicability=(nonapplicable,),
        assembled_by=Actor(kind="agent", actor_id="agent.assurance.fixture"),
        route_run_id="run.assurance.fixture",
        route_run_hash="3" * 64,
        context_manifest_hash="4" * 64,
        compiled_context_hash="5" * 64,
        assembled_at=NOW,
    )


def _registration(reference: ArtifactDependencyRef, data: bytes) -> ArtifactRegistration:
    return ArtifactRegistration(
        artifact_id=reference.artifact_id,
        version=reference.version,
        project_id=PROJECT,
        logical_name=f"Exact bytes for {reference.artifact_id}",
        media_type="application/octet-stream",
        content_hash=reference.content_hash,
        byte_size=len(data),
        created_at=NOW,
    )


class Phase4ArtifactProtocolTests(unittest.TestCase):
    def test_runtime_rebuilds_contract_from_the_exact_assurance_receipt(self) -> None:
        contract, receipt, _, assets, _, _ = _contract_material()
        assurance = _assurance(receipt)
        assurance_entity = EntityVersion(
            entity_id="assurance.bundle.fixture",
            entity_type="AssuranceBundle",
            version=1,
            project_id=PROJECT,
            title="Executable assurance fixture",
            summary="A finite exact relation scan sealed by Phase 3.",
            status=ScientificStatus(lifecycle="active"),
            facets=a.pack_authoring_payload(assurance),
            created_at=NOW,
        )
        contract = contract.model_copy(
            update={
                "assurance_bundle_ref": EntityVersionRef(
                    entity_id=assurance_entity.entity_id,
                    version=assurance_entity.version,
                ),
                "assurance_bundle_hash": object_digest(assurance),
            }
        )
        contract_entity = EntityVersion(
            entity_id="predicate.contract.fixture",
            entity_type="ObligationPredicateContract",
            version=1,
            project_id=PROJECT,
            title="Executable predicate mapping fixture",
            summary="A bounded mapping whose evidence is independently replayed.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pc.pack_profile_craft_payload(contract),
            artifact_refs=tuple(
                {
                    (reference.artifact_id, reference.version): reference
                    for reference in (
                        contract.predicate_artifact_ref,
                        contract.code_ref,
                        *(item.artifact_ref for item in contract.witnesses),
                        *(item.mutated_predicate_ref for item in contract.mutation_tests),
                        *(item.result_ref for item in contract.mutation_tests),
                    )
                }.values()
            ),
            created_at=NOW,
        )
        harness = reproducible_harness_artifact_bytes(receipt)
        harness_refs = {
            "code": receipt.code_ref,
            "input": receipt.input_ref,
            "output": receipt.output_ref,
            "receipt": receipt.receipt_ref,
        }
        base_registrations = tuple(
            _registration(harness_refs[kind], data)  # type: ignore[arg-type]
            for kind, data in harness.items()
        )
        snapshot = Snapshot(
            project_id=PROJECT,
            head=HEAD,
            chain=(HEAD,),
            entity_versions=(assurance_entity,),
            artifacts=base_registrations,
            current_entities={assurance_entity.entity_id: 1},
            current_artifacts={item.artifact_id: 1 for item in base_registrations},
        )
        with tempfile.TemporaryDirectory() as temporary:
            layout = StoreLayout.at(Path(temporary)).ensure()
            store = ObjectStore(layout)
            for data in harness.values():
                store.install_bytes("artifacts", sha256_digest(data), data)
            for data in assets.values():
                store.install_bytes("artifacts", sha256_digest(data), data)
            transaction = Transaction(
                transaction_id="transaction.map.predicate.fixture",
                origin="route_run",
                project_id=PROJECT,
                base_revision=HEAD,
                route_run_id="run.map.predicate.fixture",
                route_id="map.obligation_predicate",
                route_run_hash="6" * 64,
                context_manifest_hash="7" * 64,
                compiled_context_hash="8" * 64,
                actor=MAPPER,
                intent="Independently validate exact predicate evidence.",
                operations=(
                    CreateEntityOp(entity=contract_entity),
                    *(
                        RegisterArtifactOp(
                            artifact=_registration(
                                ArtifactDependencyRef(
                                    artifact_id=key[0],
                                    version=key[1],
                                    content_hash=key[2],
                                ),
                                data,
                            )
                        )
                        for key, data in assets.items()
                    ),
                ),
                created_at=NOW,
                parent_transaction_hash=HEAD,
            )
            validate_phase4_operational_artifacts(layout, snapshot, transaction)

    def test_clause_hashes_are_recomputed_from_canonical_json_pointers(self) -> None:
        _, _, predicate_bytes, _, _, _ = _contract_material()
        document = __import__("json").loads(predicate_bytes)
        self.assertEqual(
            canonical_json_pointer_get(document, "/domain/cases/0/case_id"),
            "case.zero",
        )
        first = predicate_fragment_hash(
            predicate_bytes,
            obligation_clause_id="clause.domain",
            relation="narrowed",
            pointers=("/domain",),
        )
        second = predicate_fragment_hash(
            predicate_bytes,
            obligation_clause_id="clause.domain",
            relation="narrowed",
            pointers=("/domain/cases/0",),
        )
        self.assertNotEqual(first, second)
        omitted = predicate_fragment_hash(
            predicate_bytes,
            obligation_clause_id="clause.assumption",
            relation="omitted",
            pointers=(),
        )
        self.assertEqual(omitted, predicate_fragment_hash(
            predicate_bytes,
            obligation_clause_id="clause.assumption",
            relation="omitted",
            pointers=(),
        ))
        with self.assertRaisesRegex(ProfileCraftExecutionError, "does not exist"):
            predicate_fragment_hash(
                predicate_bytes,
                obligation_clause_id="clause.domain",
                relation="narrowed",
                pointers=("/domain/not_a_field",),
            )

    def test_domain_witness_does_not_promote_relation_truth_to_antecedent(self) -> None:
        _, _, predicate_bytes, assets, read, _ = _contract_material()
        assignment_bytes = witness_assignment_bytes(predicate_bytes, "case.zero")
        assignment_ref = next(
            ArtifactDependencyRef(artifact_id=key[0], version=key[1], content_hash=key[2])
            for key in assets
            if key[0] == "artifact.assignment.case.zero"
        )
        witness = build_predicate_witness_artifact(
            contract_id="predicate.contract.fixture",
            witness_id="witness.fixture",
            witness_kind="domain_member",
            case_id="case.zero",
            assignment_ref=assignment_ref,
            assignment_bytes=read(assignment_ref),
            predicate_bytes=predicate_bytes,
            limitations="A finite exact case.",
        )
        self.assertTrue(witness.predicate_result)
        self.assertTrue(witness.domain_membership_verified)
        self.assertFalse(witness.antecedent_satisfiability_verified)
        self.assertEqual(witness.assignment_hash, assignment_ref.content_hash)
        with self.assertRaisesRegex(
            ProfileCraftExecutionError, "cannot verify antecedent"
        ):
            build_predicate_witness_artifact(
                contract_id="predicate.contract.fixture",
                witness_id="witness.forged.antecedent",
                witness_kind="antecedent_satisfying",
                case_id="case.zero",
                assignment_ref=assignment_ref,
                assignment_bytes=assignment_bytes,
                predicate_bytes=predicate_bytes,
                limitations="A true full relation is not an antecedent protocol.",
            )
        with self.assertRaisesRegex(ProfileCraftExecutionError, "must evaluate false"):
            build_predicate_witness_artifact(
                contract_id="predicate.contract.fixture",
                witness_id="witness.forged.false",
                witness_kind="predicate_falsifying",
                case_id="case.zero",
                assignment_ref=assignment_ref,
                assignment_bytes=assignment_bytes,
                predicate_bytes=predicate_bytes,
                limitations="A forged claim must fail.",
            )

    def test_all_mandatory_mutants_are_real_and_replayed(self) -> None:
        contract, _, predicate_bytes, _, read, results = _contract_material()
        by_kind = {item.mutation_kind: item for item in results}
        self.assertEqual(
            by_kind["empty_domain"].execution_outcome,
            "invalid_empty_domain_rejected",
        )
        self.assertEqual(
            by_kind["omitted_assumption"].execution_outcome,
            "unencoded_assumption_not_executable",
        )
        self.assertFalse(by_kind["omitted_assumption"].detected)
        self.assertEqual(by_kind["omitted_assumption"].changed_clause_ids, ())
        for kind in ("constant_true", "conclusion_flip", "domain_narrowing"):
            self.assertIsNotNone(by_kind[kind].output_hash)
            self.assertIsNotNone(by_kind[kind].receipt_hash)
        entries = replay_contract_mutations(
            contract, predicate_bytes=predicate_bytes, read_artifact=read
        )
        omitted = next(
            item for item in entries if item.mutation_kind == "omitted_assumption"
        )
        self.assertFalse(omitted.detected)
        self.assertTrue(
            all(
                item.detected
                for item in entries
                if item.mutation_kind != "omitted_assumption"
            )
        )
        self.assertEqual(
            tuple(item.mutation_id for item in entries),
            tuple(item.mutation_id for item in contract.mutation_tests),
        )

    def test_arbitrary_mutant_and_false_detection_report_are_rejected(self) -> None:
        contract, _, predicate_bytes, assets, _, _ = _contract_material()
        target = next(
            item for item in contract.mutation_tests if item.mutation_kind == "constant_true"
        )
        arbitrary = predicate_bytes
        with self.assertRaisesRegex(ProfileCraftExecutionError, "fixed protocol mutant"):
            build_predicate_mutation_result(
                contract_id=contract.contract_id,
                mutation_id=target.mutation_id,
                mutation_kind=target.mutation_kind,
                predicate_bytes=predicate_bytes,
                mappings=contract.clause_mappings,
                mutated_predicate_ref=_ref("artifact.arbitrary", arbitrary),
                mutated_predicate_bytes=arbitrary,
                limitations="Arbitrary bytes are inadmissible.",
            )

        result_key = next(key for key in assets if key[0] == "artifact.mutant.result.constant_true")
        actual = PredicateMutationResultArtifact.model_validate_json(assets[result_key], strict=True)
        forged = actual.model_copy(update={"detected": False})
        forged_bytes = canonical_json_bytes(forged)
        forged_key = (result_key[0], result_key[1], sha256_digest(forged_bytes))
        replacement = dict(assets)
        replacement[forged_key] = forged_bytes
        forged_descriptor = target.model_copy(
            update={
                "result_ref": ArtifactDependencyRef(
                    artifact_id=forged_key[0], version=forged_key[1], content_hash=forged_key[2]
                )
            }
        )
        forged_contract = contract.model_copy(
            update={
                "mutation_tests": tuple(
                    forged_descriptor if item.mutation_id == target.mutation_id else item
                    for item in contract.mutation_tests
                )
            }
        )

        def read_forged(reference: ArtifactDependencyRef) -> bytes:
            return replacement[(reference.artifact_id, reference.version, reference.content_hash)]

        with self.assertRaisesRegex(ProfileCraftExecutionError, "does not reproduce"):
            replay_contract_mutations(
                forged_contract,
                predicate_bytes=predicate_bytes,
                read_artifact=read_forged,
            )

    def test_wrong_locator_cannot_detect_conclusion_mutation(self) -> None:
        contract, _, predicate_bytes, _, _, _ = _contract_material()
        mappings = tuple(
            item.model_copy(
                update={
                    "predicate_json_pointers": ("/code_hash",),
                    "predicate_fragment_hash": predicate_fragment_hash(
                        predicate_bytes,
                        obligation_clause_id=item.obligation_clause_id,
                        relation=item.relation,
                        pointers=("/code_hash",),
                    ),
                }
            )
            if item.clause_kind == "conclusion"
            else item
            for item in contract.clause_mappings
        )
        mutant = build_mutated_predicate_bytes(predicate_bytes, "conclusion_flip")
        result = build_predicate_mutation_result(
            contract_id=contract.contract_id,
            mutation_id="mutation.wrong_locator",
            mutation_kind="conclusion_flip",
            predicate_bytes=predicate_bytes,
            mappings=mappings,
            mutated_predicate_ref=_ref("artifact.wrong.locator", mutant),
            mutated_predicate_bytes=mutant,
            limitations="A wrong locator must not count as detection.",
        )
        self.assertFalse(result.detected)
        self.assertNotIn("clause.conclusion", result.changed_clause_ids)

    def test_replay_summary_is_derived_from_every_exact_result(self) -> None:
        contract, _, predicate_bytes, _, read, _ = _contract_material()
        summary = build_mutation_replay_artifact(
            audit_id="audit.fixture",
            contract_ref=EntityVersionRef(entity_id="contract.fixture", version=1),
            contract_hash=object_digest(contract),
            contract=contract,
            predicate_bytes=predicate_bytes,
            read_artifact=read,
            limitations="The deterministic executor reruns every registered mutant.",
        )
        self.assertEqual(summary.outcome, "pass_with_limitations")
        self.assertFalse(summary.all_detected)
        self.assertTrue(summary.executable_controls_passed)
        self.assertTrue(summary.unexecutable_controls_accounted)
        self.assertEqual(summary.surviving_mutation_ids, ())
        self.assertEqual(
            summary.unexecutable_mutation_ids,
            ("mutation.fixture.omitted_assumption",),
        )
        self.assertNotIn(
            "mutation.fixture.omitted_assumption", summary.killed_mutation_ids
        )
        self.assertEqual(len(summary.entries), len(contract.mutation_tests))
        values = {
            field: getattr(summary, field)
            for field in PredicateMutationReplayArtifact.model_fields
        }
        with self.assertRaisesRegex(ValueError, "killed-control IDs are inconsistent"):
            PredicateMutationReplayArtifact(
                **{
                    **values,
                    "killed_mutation_ids": (
                        *summary.killed_mutation_ids,
                        "mutation.fixture.omitted_assumption",
                    ),
                }
            )

    def test_unexecutable_omitted_assumption_cannot_be_forged_as_killed(self) -> None:
        _, _, _, _, _, results = _contract_material()
        omitted = next(
            item for item in results if item.mutation_kind == "omitted_assumption"
        )
        values = {
            field: getattr(omitted, field)
            for field in PredicateMutationResultArtifact.model_fields
        }
        with self.assertRaisesRegex(ValueError, "cannot be marked detected"):
            PredicateMutationResultArtifact(**{**values, "detected": True})
        with self.assertRaisesRegex(ValueError, "preserve the exact input bytes"):
            PredicateMutationResultArtifact(
                **{**values, "mutated_predicate_hash": "f" * 64}
            )

    def test_phrase_scan_uses_only_pinned_internal_derived_fields(self) -> None:
        corpus = load_craft_corpus()
        selected_move_refs = (pc.static_resource_ref(corpus.moves[0]),)
        clean = b"A fixed benchmark makes the participation margin transparent."
        clean_ref = _ref("artifact.manuscript.clean", clean)
        audit = build_phrase_leak_audit(
            assessment_id="assessment.clean",
            manuscript_artifact_ref=clean_ref,
            manuscript_bytes=clean,
            selected_move_refs=selected_move_refs,
            normalized_ngram_size=8,
            corpus=corpus,
        )
        self.assertEqual(audit.outcome, "pass")
        self.assertEqual(audit.limitations, PHRASE_AUDIT_LIMITATIONS)

        cards = selected_source_cards(selected_move_refs, corpus=corpus)
        projection = protected_material_projection(cards)
        copied = projection[0]["functional_summary"].encode("utf-8")
        copied_ref = _ref("artifact.manuscript.copied", copied)
        copied_audit = build_phrase_leak_audit(
            assessment_id="assessment.copied",
            manuscript_artifact_ref=copied_ref,
            manuscript_bytes=copied,
            selected_move_refs=selected_move_refs,
            normalized_ngram_size=8,
            corpus=corpus,
        )
        self.assertEqual(copied_audit.outcome, "fail")
        self.assertTrue(copied_audit.suspicious_match_hashes)
        with self.assertRaises(ValueError):
            copied_audit.model_copy(update={"outcome": "pass"}).model_validate(
                copied_audit.model_copy(update={"outcome": "pass"}).model_dump()
            )


if __name__ == "__main__":
    unittest.main()
