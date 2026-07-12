"""Fast fail-closed attacks against the Phase 3 authoring boundary.

These tests deliberately avoid the multi-minute gold chain.  They exercise
the strict payload models and the operational byte validator directly so a
self-consistent declaration cannot substitute for immutable evidence.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase3_authoring_models import paper_ir, reader_path

from econ_theorist import authoring as a
from econ_theorist import authoring_validation as av
from econ_theorist import theory as t
from econ_theorist.authoring_artifacts import (
    ReaderAnswer,
    ReaderAnswerCriterion,
    ReaderAnswerKeyArtifact,
    ReaderProbeArtifact,
    ReaderProbePrompt,
    ReaderResponseArtifact,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    CreateEntityOp,
    Decision,
    DecisionVersionRef,
    EntityDerivedStatus,
    EntityVersion,
    EntityVersionRef,
    RegisterArtifactOp,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
    Transaction,
)
from econ_theorist.runtime.layout import StoreLayout
from econ_theorist.runtime.objects import ObjectStore
from econ_theorist.runtime.phase3_artifacts import (
    Phase3ArtifactError,
    validate_phase3_operational_artifacts,
)
from econ_theorist.route_registry import get_route


PROJECT = "project.phase3.downgrade"
HEAD = "a" * 64
CREATED = "2026-07-12T00:00:00Z"
WRITER = Actor(kind="agent", actor_id="agent.writer")
ECONOMIC_READER = Actor(kind="agent", actor_id="agent.economic.reader")
DESIGNER = Actor(kind="agent", actor_id="agent.probe.designer")
RESPONDENT = Actor(kind="agent", actor_id="agent.cold.reader")
ADJUDICATOR = Actor(kind="agent", actor_id="agent.probe.adjudicator")
HUMAN = Actor(kind="human", actor_id="human.author")


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def aref(artifact_id: str, data: bytes | None = None) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id,
        version=1,
        content_hash=sha256_digest(data) if data is not None else "b" * 64,
    )


def registration(
    reference: ArtifactDependencyRef,
    data: bytes,
    *,
    media_type: str = "application/json",
) -> ArtifactRegistration:
    return ArtifactRegistration(
        artifact_id=reference.artifact_id,
        version=reference.version,
        project_id=PROJECT,
        logical_name=f"Bytes for {reference.artifact_id}",
        media_type=media_type,
        content_hash=reference.content_hash,
        byte_size=len(data),
        human_owned=False,
        privacy="restricted",
        access_compartments=("cold_reader", "project_research"),
        created_at=CREATED,
    )


def entity(
    entity_id: str,
    payload: a.AuthoringPayload,
    *,
    artifact_refs: tuple[ArtifactDependencyRef, ...] = (),
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=1,
        project_id=PROJECT,
        title=f"Title for {entity_id}",
        summary=f"Summary for {entity_id}",
        status=ScientificStatus(lifecycle="proposed"),
        facets=a.pack_authoring_payload(payload),
        artifact_refs=artifact_refs,
        privacy="restricted",
        access_compartments=("cold_reader", "project_research"),
        created_at=CREATED,
    )


def transaction(
    route_id: str,
    outputs: tuple[EntityVersion, ...],
    *,
    artifacts: tuple[ArtifactRegistration, ...] = (),
    actor: Actor = DESIGNER,
    compiled_context_hash: str = "d" * 64,
) -> Transaction:
    return Transaction(
        transaction_id=f"transaction.{route_id}.downgrade",
        origin="route_run",
        project_id=PROJECT,
        base_revision=HEAD,
        route_run_id=f"run.{route_id}.downgrade",
        route_id=route_id,
        route_run_hash="b" * 64,
        context_manifest_hash="c" * 64,
        compiled_context_hash=compiled_context_hash,
        actor=actor,
        intent="Exercise a fail-closed Phase 3 boundary.",
        operations=(
            *(CreateEntityOp(entity=item) for item in outputs),
            *(RegisterArtifactOp(artifact=item) for item in artifacts),
        ),
        privacy="restricted",
        access_compartments=("cold_reader", "project_research"),
        created_at=CREATED,
        parent_transaction_hash=HEAD,
    )


def manuscript_material(
    *,
    writer_packet_hash: str,
) -> tuple[str, bytes, ArtifactDependencyRef, a.ManuscriptUnit]:
    text = "A higher processing cost weakens the receiver's information-use response."
    data = text.encode("utf-8")
    manuscript_ref = aref("artifact.manuscript.downgrade", data)
    span = a.ConsequentialSpan(
        assertion_id="assertion.processing.response",
        role="economic_translation",
        claim_projection_id="projection.processing.response",
        claim_graph_ref=eref("entity.claim.graph"),
        claim_id="claim.processing.response",
        source_fields=(
            SemanticFacetRef(
                entity_id="entity.claim.graph",
                version=1,
                facet="economic_interpretation",
                field_path="/payload/claims/0/semantic_translation",
                semantic_hash="e" * 64,
            ),
        ),
        scope="Maintained positive processing-cost domain.",
        assumption_ids=("assumption.processing.cost",),
        location=a.ManuscriptLocation(start_offset=0, end_offset=len(text)),
        text_hash=sha256_digest(data),
        wording_strength="entailed_equivalent",
        presentation="economic_interpretation",
    )
    unit = a.ManuscriptUnit(
        unit_id="unit.processing.response",
        paper_ir_ref=eref("entity.paper"),
        reader_path_ref=eref("entity.reader.path"),
        result_contract_set_ref=eref("entity.result.contracts"),
        section_contract_id="section.results",
        manuscript_artifact_ref=manuscript_ref,
        source_state_revision=HEAD,
        canonical_writer=WRITER,
        writer_role_packet_hash=writer_packet_hash,
        writer_output_hash=manuscript_ref.content_hash,
        integration_generation=1,
        spans=(span,),
        terminology=(
            a.TerminologyRealization(
                object_id="object.processing.cost",
                realized_name="processing cost",
                formal_symbol="c",
                first_use_assertion_id=span.assertion_id,
            ),
        ),
        composed_at=CREATED,
    )
    return text, data, manuscript_ref, unit


def probe_material() -> tuple[
    a.ReaderProbeSet,
    ReaderProbeArtifact,
    ReaderAnswerKeyArtifact,
    bytes,
    bytes,
]:
    assignment_ref = eref("entity.assignment.cold")
    unit_ref = eref("entity.unit.processing")
    manuscript_ref = ArtifactDependencyRef(
        artifact_id="artifact.manuscript.downgrade",
        version=1,
        content_hash="1" * 64,
    )
    prompts = tuple(
        ReaderProbePrompt(
            probe_id=f"probe.{kind}",
            kind=kind,  # type: ignore[arg-type]
            prompt=f"Reconstruct the {kind.replace('_', ' ')} from the manuscript.",
            prompt_hash=sha256_digest(
                f"Reconstruct the {kind.replace('_', ' ')} from the manuscript.".encode()
            ),
            target_contract_ids=("contract.headline",),
        )
        for kind in a.READER_PROBE_KIND_ORDER
    )
    criteria = tuple(
        ReaderAnswerCriterion(
            probe_id=item.probe_id,
            kind=item.kind,
            criterion=f"Credit requires the exact economic distinction for {item.kind}.",
            criterion_hash=sha256_digest(
                f"Credit requires the exact economic distinction for {item.kind}.".encode()
            ),
            required_content=("State the economically operative distinction.",),
        )
        for item in prompts
    )
    visible = ReaderProbeArtifact(
        assignment_ref=assignment_ref,
        manuscript_unit_ref=unit_ref,
        frozen_manuscript_artifact_ref=manuscript_ref,
        respondent=RESPONDENT,
        transfer_objective="Transfer the competing-forces mechanism to one nearby case.",
        probes=prompts,
    )
    key = ReaderAnswerKeyArtifact(
        assignment_ref=assignment_ref,
        manuscript_unit_ref=unit_ref,
        frozen_manuscript_artifact_ref=manuscript_ref,
        adjudicator=ADJUDICATOR,
        criteria=criteria,
    )
    visible_data = canonical_json_bytes(visible)
    key_data = canonical_json_bytes(key)
    probe_ref = aref("artifact.reader.probes", visible_data)
    key_ref = aref("artifact.reader.key", key_data)
    probe = a.ReaderProbeSet(
        assignment_ref=assignment_ref,
        manuscript_unit_ref=unit_ref,
        frozen_manuscript_artifact_ref=manuscript_ref,
        probe_designer=DESIGNER,
        respondent=RESPONDENT,
        adjudicator=ADJUDICATOR,
        canonical_writer=WRITER,
        transfer_objective=visible.transfer_objective,
        probes=tuple(
            a.ReaderProbeDescriptor(
                probe_id=item.probe_id,
                kind=item.kind,
                prompt_hash=item.prompt_hash,
                target_contract_ids=item.target_contract_ids,
            )
            for item in prompts
        ),
        probe_artifact_ref=probe_ref,
        answer_key_artifact_ref=key_ref,
        route_run_id="run.prepare.reader.probe",
        context_manifest_hash="2" * 64,
        sealed_at=CREATED,
    )
    return probe, visible, key, visible_data, key_data


def decision(
    *,
    decision_id: str,
    kind: str,
    subject: str,
    scope: str,
    selected: str,
    machine_outcome: str | None,
) -> Decision:
    return Decision(
        decision_id=decision_id,
        version=1,
        project_id=PROJECT,
        decision_kind=kind,  # type: ignore[arg-type]
        subject_ref=subject,
        scope_ref=scope,
        question="Should this exact object be approved?",
        options=("approve", "deny"),
        selected_option=selected,
        machine_outcome=machine_outcome,  # type: ignore[arg-type]
        recommendation="Apply the explicit typed outcome.",
        rationale="The decision binds one exact immutable subject and scope.",
        required_authority="L2",
        decider=HUMAN,
        decided_at=CREATED,
        status="confirmed",
    )


class AssuranceDowngradeTests(unittest.TestCase):
    def test_headline_cannot_be_assured_by_all_non_applicability_records(self) -> None:
        obligation = eref("entity.obligation.headline")
        claim_graph = eref("entity.claim.graph")
        audit_report = aref("artifact.audit.report")
        audit = a.ProofAudit(
            audit_id="audit.headline",
            claim_graph_ref=claim_graph,
            claim_id="claim.headline",
            obligation_ref=obligation,
            formal_model_ref=eref("entity.formal.model"),
            assumption_map_ref=eref("entity.assumption.map"),
            proof_artifact_ref=aref("artifact.proof"),
            verification_record_ref=eref("entity.verification.record"),
            rederivation_ref=eref("entity.rederivation"),
            originating_verifier=Actor(kind="agent", actor_id="agent.verifier"),
            auditor=Actor(kind="agent", actor_id="agent.auditor"),
            audit_report_ref=audit_report,
            outcome="passed",
            comparison_outcome="agrees",
            limitations="The conclusion is limited to the exact maintained domain.",
            audited_at=CREATED,
        )
        non_applicability = tuple(
            a.HarnessNonApplicabilityRecord(
                record_id=f"nonapplicable.{family}",
                family=family,  # type: ignore[arg-type]
                claim_graph_ref=claim_graph,
                claim_id="claim.headline",
                obligation_ref=obligation,
                reason_code=(
                    "no_algebraic_identity"
                    if family == "symbolic_identity"
                    else "no_finite_domain"
                ),
                explanation=(
                    "This harness family has no exact informative target for the "
                    "maintained obligation."
                ),
                evidence_refs=(audit_report,),
                determined_by=Actor(kind="agent", actor_id="agent.assurance"),
            )
            for family in ("symbolic_identity", "counterexample_search")
        )

        with self.assertRaisesRegex(
            ValidationError, "at least one executed reproducible harness"
        ):
            a.AssuranceBundle(
                package_ref=eref("entity.package"),
                g5_decision_ref=DecisionVersionRef(decision_id="decision.g5", version=1),
                claim_graph_ref=claim_graph,
                headline_claim_id="claim.headline",
                formal_model_ref=eref("entity.formal.model"),
                assumption_map_ref=eref("entity.assumption.map"),
                verification_bundle_ref=eref("entity.verification.bundle"),
                rederivation_refs=(eref("entity.rederivation"),),
                proof_audits=(audit,),
                tool_receipts=(),
                tool_non_applicability=non_applicability,
                assembled_by=Actor(kind="agent", actor_id="agent.assurance"),
                route_run_id="run.assurance",
                route_run_hash="3" * 64,
                context_manifest_hash="4" * 64,
                compiled_context_hash="5" * 64,
                assembled_at=CREATED,
            )


class AssurancePackageInputSubstitutionTests(unittest.TestCase):
    def _package_fixture(self) -> tuple[
        dict[str, dict[str, EntityVersionRef]],
        dict[tuple[str, int], t.TheoryPayload],
    ]:
        refs: dict[str, dict[str, EntityVersionRef]] = {}
        payloads: dict[tuple[str, int], t.TheoryPayload] = {}
        for suffix in ("a", "b"):
            values = {
                "package": eref(f"package.{suffix}"),
                "claim": eref(f"claim.graph.{suffix}"),
                "formal": eref(f"formal.model.{suffix}"),
                "assumptions": eref(f"assumption.map.{suffix}"),
                "bundle": eref(f"verification.bundle.{suffix}"),
                "obligation": eref(f"proof.obligation.{suffix}"),
                "verification": eref(f"verification.record.{suffix}"),
            }
            refs[suffix] = values
            package = t.ValidatedArgumentPackage.model_construct(
                claim_graph_ref=values["claim"],
                formal_model_ref=values["formal"],
                assumption_map_ref=values["assumptions"],
                verification_bundle_ref=values["bundle"],
                release_mode="production_candidate",
            )
            claim = t.ClaimGraph.model_construct(
                formal_model_ref=values["formal"],
                assumption_map_ref=values["assumptions"],
            )
            formal = t.FormalModel.model_construct()
            assumptions = t.AssumptionMap.model_construct(
                formal_model_ref=values["formal"]
            )
            obligation = t.ProofObligation.model_construct(
                claim_graph_ref=values["claim"],
                claim_id=f"claim.{suffix}",
                obligation_id=f"obligation.{suffix}",
            )
            bundle = t.VerificationBundle.model_construct(
                claim_graph_ref=values["claim"],
                proof_obligation_refs=(values["obligation"],),
                verification_record_refs=(values["verification"],),
            )
            for reference, payload in (
                (values["package"], package),
                (values["claim"], claim),
                (values["formal"], formal),
                (values["assumptions"], assumptions),
                (values["obligation"], obligation),
                (values["bundle"], bundle),
            ):
                payloads[(reference.entity_id, reference.version)] = payload
        return refs, payloads

    def _verify_inputs(
        self,
        package: EntityVersionRef,
        claim: EntityVersionRef,
        formal: EntityVersionRef,
        assumptions: EntityVersionRef,
        obligation: EntityVersionRef,
    ) -> dict[str, tuple[EntityVersionRef, ...]]:
        return {
            "ValidatedArgumentPackage": (package,),
            "ClaimGraph": (claim,),
            "FormalModel": (formal,),
            "AssumptionMap": (assumptions,),
            "ProofObligation": (obligation,),
        }

    def test_approved_package_rejects_scientific_inputs_from_another_package(self) -> None:
        refs, payloads = self._package_fixture()
        with self.assertRaisesRegex(
            av.AuthoringValidationError,
            "package.*input lineage|input lineage.*package",
        ):
            av._validate_exact_package_input_lineage(
                "verify.independent_rederivation",
                self._verify_inputs(
                    refs["a"]["package"],
                    refs["b"]["claim"],
                    refs["b"]["formal"],
                    refs["b"]["assumptions"],
                    refs["b"]["obligation"],
                ),
                payloads,
            )

    def test_package_rejects_unbundled_proof_obligation(self) -> None:
        refs, payloads = self._package_fixture()
        rogue_ref = eref("proof.obligation.rogue")
        payloads[(rogue_ref.entity_id, rogue_ref.version)] = (
            t.ProofObligation.model_construct(
                claim_graph_ref=refs["a"]["claim"],
                claim_id="claim.a",
                obligation_id="obligation.rogue",
            )
        )
        with self.assertRaisesRegex(
            av.AuthoringValidationError,
            "package.*input lineage|input lineage.*package",
        ):
            av._validate_exact_package_input_lineage(
                "verify.independent_rederivation",
                self._verify_inputs(
                    refs["a"]["package"],
                    refs["a"]["claim"],
                    refs["a"]["formal"],
                    refs["a"]["assumptions"],
                    rogue_ref,
                ),
                payloads,
            )


class AssuranceAuditBijectionDowngradeTests(unittest.TestCase):
    def test_audit_requires_exact_one_to_one_rederivation_mapping(self) -> None:
        package_ref = eref("package.audit")
        claim_ref = eref("claim.graph.audit")
        formal_ref = eref("formal.model.audit")
        assumption_ref = eref("assumption.map.audit")
        bundle_ref = eref("verification.bundle.audit")
        obligation_refs = (
            eref("proof.obligation.audit.one"),
            eref("proof.obligation.audit.two"),
        )
        verification_refs = (
            eref("verification.record.audit.one"),
            eref("verification.record.audit.two"),
        )
        rederivation_refs = (
            eref("rederivation.audit.one"),
            eref("rederivation.audit.two"),
        )
        package = t.ValidatedArgumentPackage.model_construct(
            question_ref=eref("question.audit"),
            claim_graph_ref=claim_ref,
            formal_model_ref=formal_ref,
            assumption_map_ref=assumption_ref,
            verification_bundle_ref=bundle_ref,
            g5_dossier_ref=eref("dossier.g5.audit"),
            release_mode="production_candidate",
        )
        theory_payloads: dict[tuple[str, int], t.TheoryPayload] = {
            (package_ref.entity_id, package_ref.version): package,
            (claim_ref.entity_id, claim_ref.version): t.ClaimGraph.model_construct(
                formal_model_ref=formal_ref,
                assumption_map_ref=assumption_ref,
            ),
            (formal_ref.entity_id, formal_ref.version): t.FormalModel.model_construct(),
            (assumption_ref.entity_id, assumption_ref.version): (
                t.AssumptionMap.model_construct(formal_model_ref=formal_ref)
            ),
            (bundle_ref.entity_id, bundle_ref.version): (
                t.VerificationBundle.model_construct(
                    claim_graph_ref=claim_ref,
                    proof_obligation_refs=obligation_refs,
                    verification_record_refs=verification_refs,
                )
            ),
        }
        for index, (obligation_ref, verification_ref) in enumerate(
            zip(obligation_refs, verification_refs), start=1
        ):
            theory_payloads[(obligation_ref.entity_id, obligation_ref.version)] = (
                t.ProofObligation.model_construct(
                    claim_graph_ref=claim_ref,
                    claim_id=f"claim.audit.{index}",
                    obligation_id=f"obligation.audit.{index}",
                )
            )
            theory_payloads[(verification_ref.entity_id, verification_ref.version)] = (
                t.VerificationRecord.model_construct(
                    obligation_ref=obligation_ref,
                    claim_graph_ref=claim_ref,
                    formal_model_ref=formal_ref,
                    assumption_map_ref=assumption_ref,
                )
            )

        verifier = Actor(kind="agent", actor_id="agent.audit.originating.verifier")
        proof_author = Actor(kind="agent", actor_id="agent.audit.proof.author")
        rederiver = Actor(kind="agent", actor_id="agent.audit.rederiver")
        auditor = Actor(kind="agent", actor_id="agent.audit.independent")

        def record(
            obligation_ref: EntityVersionRef,
            verification_ref: EntityVersionRef,
            **updates: object,
        ) -> a.ReDerivationRecord:
            values: dict[str, object] = {
                "package_ref": package_ref,
                "claim_graph_ref": claim_ref,
                "formal_model_ref": formal_ref,
                "assumption_map_ref": assumption_ref,
                "obligation_ref": obligation_ref,
                "verification_record_ref": verification_ref,
                "rederiver": rederiver,
                "originating_verifier": verifier,
                "proof_author": proof_author,
            }
            values.update(updates)
            return a.ReDerivationRecord.model_construct(**values)

        base_payloads: dict[tuple[str, int], a.AuthoringPayload] = {
            (rederivation_refs[0].entity_id, rederivation_refs[0].version): record(
                obligation_refs[0], verification_refs[0]
            ),
            (rederivation_refs[1].entity_id, rederivation_refs[1].version): record(
                obligation_refs[1], verification_refs[1]
            ),
        }
        duplicate_ref = eref("rederivation.audit.duplicate")
        base_payloads[(duplicate_ref.entity_id, duplicate_ref.version)] = record(
            obligation_refs[0], verification_refs[0]
        )
        g5 = decision(
            decision_id="gate.g5.audit",
            kind="G5_argument_validation",
            subject=package.g5_dossier_ref.entity_id,
            scope=package.question_ref.entity_id,
            selected="approve",
            machine_outcome="approve",
        )
        snapshot = Snapshot(
            project_id=PROJECT,
            head=HEAD,
            chain=(HEAD,),
            decisions=(g5,),
        )
        fixed_inputs: dict[str, tuple[EntityVersionRef, ...]] = {
            "ValidatedArgumentPackage": (package_ref,),
            "ClaimGraph": (claim_ref,),
            "FormalModel": (formal_ref,),
            "AssumptionMap": (assumption_ref,),
            "VerificationBundle": (bundle_ref,),
            "ProofObligation": obligation_refs,
            "VerificationRecord": verification_refs,
        }

        def run(
            selected_rederivations: tuple[EntityVersionRef, ...],
            payloads: dict[tuple[str, int], a.AuthoringPayload],
        ) -> None:
            inputs = {
                **fixed_inputs,
                "ReDerivationRecord": selected_rederivations,
            }
            references = tuple(
                reference for values in inputs.values() for reference in values
            )
            type_by_ref = {
                reference: entity_type
                for entity_type, values in inputs.items()
                for reference in values
            }
            entities = tuple(
                EntityVersion.model_construct(
                    entity_id=reference.entity_id,
                    entity_type=type_by_ref[reference],
                    version=reference.version,
                )
                for reference in references
            )
            with patch.object(
                av, "_decision_is_current_confirmed_human", return_value=True
            ):
                av._input_mode_and_lineage(
                    snapshot,
                    get_route("audit.argument_assurance"),
                    references,
                    entities,
                    payloads,
                    theory_payloads,
                    actor=auditor,
                    compiler_mode=None,
                )

        scenarios: list[
            tuple[
                str,
                tuple[EntityVersionRef, ...],
                dict[tuple[str, int], a.AuthoringPayload],
                str,
            ]
        ] = [
            (
                "missing_verification_mapping",
                (rederivation_refs[0],),
                dict(base_payloads),
                "one exact re-derivation per verification record",
            ),
            (
                "duplicate_obligation_record_pair",
                (*rederivation_refs, duplicate_ref),
                dict(base_payloads),
                "one exact re-derivation per verification record",
            ),
        ]
        for field, foreign_ref in (
            ("package_ref", eref("package.foreign.audit")),
            ("claim_graph_ref", eref("claim.graph.foreign.audit")),
            ("formal_model_ref", eref("formal.model.foreign.audit")),
            ("assumption_map_ref", eref("assumption.map.foreign.audit")),
        ):
            forged_ref = eref(f"rederivation.audit.foreign.{field}")
            forged_payloads = dict(base_payloads)
            forged_payloads[(forged_ref.entity_id, forged_ref.version)] = record(
                obligation_refs[0], verification_refs[0], **{field: foreign_ref}
            )
            scenarios.append(
                (
                    f"foreign_{field}",
                    (forged_ref, rederivation_refs[1]),
                    forged_payloads,
                    "another package lineage",
                )
            )

        for label, selected, payloads, message in scenarios:
            with self.subTest(attack=label), self.assertRaisesRegex(
                av.AuthoringValidationError, message
            ):
                run(selected, payloads)


class OperationalByteDowngradeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = StoreLayout.at(Path(self.temporary.name))
        self.layout.ensure()
        self.store = ObjectStore(self.layout)
        self.empty_snapshot = Snapshot(project_id=PROJECT, head=HEAD, chain=(HEAD,))

    def _compose_case(self, *, claimed_packet_hash: str) -> tuple[
        Transaction, ArtifactDependencyRef, bytes
    ]:
        role_packet = {
            "packet_schema": "econ-theorist/role-packet/v1",
            "packet_kind": "canonical_writer",
            "semantic_inputs": [],
        }
        context_data = canonical_json_bytes(
            {
                "project_id": PROJECT,
                "source_head": HEAD,
                "phase3_role_packet": role_packet,
            }
        )
        context_hash = sha256_digest(context_data)
        self.store.install_bytes("provenance", context_hash, context_data)
        _, manuscript_data, manuscript_ref, unit = manuscript_material(
            writer_packet_hash=claimed_packet_hash
        )
        self.store.install_bytes("artifacts", manuscript_ref.content_hash, manuscript_data)
        reg = registration(manuscript_ref, manuscript_data, media_type="text/plain")
        output = entity(
            "entity.unit.processing",
            unit,
            artifact_refs=(manuscript_ref,),
        )
        tx = transaction(
            "compose.manuscript_unit",
            (output,),
            artifacts=(reg,),
            actor=WRITER,
            compiled_context_hash=context_hash,
        )
        return tx, manuscript_ref, manuscript_data

    def test_writer_cannot_claim_a_different_role_packet(self) -> None:
        tx, _, _ = self._compose_case(claimed_packet_hash="9" * 64)
        with self.assertRaisesRegex(Phase3ArtifactError, "exact writer role packet"):
            validate_phase3_operational_artifacts(
                self.layout, self.empty_snapshot, tx
            )

    def test_mutated_manuscript_object_is_rejected_when_runtime_rereads_bytes(self) -> None:
        packet = {
            "packet_schema": "econ-theorist/role-packet/v1",
            "packet_kind": "canonical_writer",
            "semantic_inputs": [],
        }
        tx, manuscript_ref, manuscript_data = self._compose_case(
            claimed_packet_hash=sha256_digest(canonical_json_bytes(packet))
        )
        validate_phase3_operational_artifacts(self.layout, self.empty_snapshot, tx)

        object_path = self.store.path_for("artifacts", manuscript_ref.content_hash)
        object_path.write_bytes(manuscript_data + b" TAMPERED")
        with self.assertRaisesRegex(Phase3ArtifactError, "immutable storage"):
            validate_phase3_operational_artifacts(
                self.layout, self.empty_snapshot, tx
            )

    def test_probe_descriptor_cannot_claim_a_different_prompt_hash(self) -> None:
        probe, _, _, visible_data, key_data = probe_material()
        forged_first = probe.probes[0].model_copy(update={"prompt_hash": "8" * 64})
        forged = probe.model_copy(update={"probes": (forged_first, *probe.probes[1:])})
        visible_ref = probe.probe_artifact_ref
        key_ref = probe.answer_key_artifact_ref
        self.store.install_bytes("artifacts", visible_ref.content_hash, visible_data)
        self.store.install_bytes("artifacts", key_ref.content_hash, key_data)
        tx = transaction(
            "prepare.reader_probe",
            (
                entity(
                    "entity.probes.forged",
                    forged,
                    artifact_refs=(visible_ref, key_ref),
                ),
            ),
            artifacts=(
                registration(visible_ref, visible_data),
                registration(key_ref, key_data),
            ),
        )
        with self.assertRaisesRegex(Phase3ArtifactError, "disagree"):
            validate_phase3_operational_artifacts(
                self.layout, self.empty_snapshot, tx
            )

    def test_key_and_response_inner_hash_tampering_is_rejected(self) -> None:
        _, visible, key, _, _ = probe_material()
        criterion_values = key.criteria[0].model_dump(mode="python")
        criterion_values["criterion_hash"] = "7" * 64
        with self.subTest(artifact="answer_key"), self.assertRaisesRegex(
            ValidationError, "criterion hash"
        ):
            ReaderAnswerCriterion(**criterion_values)

        prompt = visible.probes[0]
        response_text = "The affected margin is the discrete information-use decision."
        valid_answer = ReaderAnswer(
            probe_id=prompt.probe_id,
            kind=prompt.kind,
            response=response_text,
            response_hash=sha256_digest(response_text.encode()),
        )
        response_values = valid_answer.model_dump(mode="python")
        response_values["response_hash"] = "6" * 64
        with self.subTest(artifact="reader_response"), self.assertRaisesRegex(
            ValidationError, "response hash"
        ):
            ReaderAnswer(**response_values)

    def test_cold_scoring_cannot_rebind_response_or_key_hashes(self) -> None:
        probe, visible, key, visible_data, key_data = probe_material()
        text, manuscript_data, manuscript_ref, unit = manuscript_material(
            writer_packet_hash="0" * 64
        )
        # Bind the probe fixture to the exact manuscript used by this snapshot.
        probe_values = probe.model_dump(mode="python")
        probe_values["manuscript_unit_ref"] = eref("entity.unit.processing")
        probe_values["frozen_manuscript_artifact_ref"] = manuscript_ref
        visible_values = visible.model_dump(mode="python")
        visible_values["manuscript_unit_ref"] = eref("entity.unit.processing")
        visible_values["frozen_manuscript_artifact_ref"] = manuscript_ref
        visible = ReaderProbeArtifact(**visible_values)
        key_values = key.model_dump(mode="python")
        key_values["manuscript_unit_ref"] = eref("entity.unit.processing")
        key_values["frozen_manuscript_artifact_ref"] = manuscript_ref
        key = ReaderAnswerKeyArtifact(**key_values)
        visible_data = canonical_json_bytes(visible)
        key_data = canonical_json_bytes(key)
        visible_ref = aref("artifact.reader.probes.bound", visible_data)
        key_ref = aref("artifact.reader.key.bound", key_data)
        probe_values["probe_artifact_ref"] = visible_ref
        probe_values["answer_key_artifact_ref"] = key_ref
        probe = a.ReaderProbeSet(**probe_values)

        answers = tuple(
            ReaderAnswer(
                probe_id=item.probe_id,
                kind=item.kind,
                response=f"A substantive reconstruction for {item.kind}.",
                response_hash=sha256_digest(
                    f"A substantive reconstruction for {item.kind}.".encode()
                ),
            )
            for item in visible.probes
        )
        response_artifact = ReaderResponseArtifact(
            probe_set_ref=eref("entity.probes.bound"),
            manuscript_unit_ref=eref("entity.unit.processing"),
            respondent=RESPONDENT,
            answers=answers,
        )
        response_data = canonical_json_bytes(response_artifact)
        response_ref = aref("artifact.reader.response", response_data)
        response = a.ReaderResponse(
            probe_set_ref=eref("entity.probes.bound"),
            manuscript_unit_ref=eref("entity.unit.processing"),
            respondent=RESPONDENT,
            answered_probe_ids=tuple(item.probe_id for item in answers),
            response_artifact_ref=response_ref,
            route_run_id="run.answer.reader.probe",
            context_manifest_hash="3" * 64,
            submitted_at=CREATED,
        )
        results = tuple(
            a.ColdReaderProbeResult(
                probe_id=answer.probe_id,
                kind=answer.kind,
                outcome="passed",
                response_excerpt_hash=(
                    "f" * 64 if index == 0 else answer.response_hash
                ),
                answer_key_criterion_hash=criterion.criterion_hash,
                rationale="The response reconstructs the requested economic distinction.",
            )
            for index, (answer, criterion) in enumerate(zip(answers, key.criteria))
        )
        assessment = a.ColdReaderAssessment(
            question_and_benchmark_retell_passed=True,
            exact_scope_recovery_passed=True,
            assumption_role_recovery_passed=True,
            boundary_discrimination_passed=True,
            near_transfer_passed=True,
            response_artifact_ref=response_ref,
            probe_results=results,
        )
        review = a.ReviewRecord(
            assignment_ref=probe.assignment_ref,
            manuscript_unit_ref=eref("entity.unit.processing"),
            reviewed_artifact_ref=manuscript_ref,
            role="cold_reader",
            reviewer=ADJUDICATOR,
            canonical_writer=WRITER,
            context_hash="4" * 64,
            assessment=assessment,
            reader_response_ref=eref("entity.response.bound"),
            answer_key_artifact_ref=key_ref,
            adjudicator=ADJUDICATOR,
            reviewed_at=CREATED,
        )

        registrations = (
            registration(manuscript_ref, manuscript_data, media_type="text/plain"),
            registration(visible_ref, visible_data),
            registration(key_ref, key_data),
            registration(response_ref, response_data),
        )
        for reference, data in (
            (manuscript_ref, manuscript_data),
            (visible_ref, visible_data),
            (key_ref, key_data),
            (response_ref, response_data),
        ):
            self.store.install_bytes("artifacts", reference.content_hash, data)
        snapshot = Snapshot(
            project_id=PROJECT,
            head=HEAD,
            chain=(HEAD,),
            entity_versions=(
                entity(
                    "entity.unit.processing", unit, artifact_refs=(manuscript_ref,)
                ),
                entity(
                    "entity.probes.bound",
                    probe,
                    artifact_refs=(visible_ref, key_ref, manuscript_ref),
                ),
                entity(
                    "entity.response.bound",
                    response,
                    artifact_refs=(response_ref,),
                ),
            ),
            artifacts=registrations,
        )
        tx = transaction(
            "adjudicate.reader_probe",
            (
                entity(
                    "entity.review.cold.forged",
                    review,
                    artifact_refs=(manuscript_ref, response_ref, key_ref),
                ),
            ),
            actor=ADJUDICATOR,
        )

        with self.assertRaisesRegex(Phase3ArtifactError, "scoring hashes"):
            validate_phase3_operational_artifacts(self.layout, snapshot, tx)


class ExactInputLineageSubstitutionTests(unittest.TestCase):
    def _cold_fixture(self) -> tuple[
        EntityVersionRef,
        a.ManuscriptUnit,
        EntityVersionRef,
        a.CriticAssignment,
        EntityVersionRef,
        a.ReaderProbeSet,
        dict[tuple[str, int], a.AuthoringPayload],
    ]:
        _, _, _, unit = manuscript_material(writer_packet_hash="0" * 64)
        unit_ref = eref("entity.unit.processing")
        assignment_ref = eref("entity.assignment.cold")
        assignment = a.CriticAssignment(
            assignment_id="assignment.cold",
            role="cold_reader",
            paper_ir_ref=unit.paper_ir_ref,
            reader_path_ref=unit.reader_path_ref,
            result_contract_set_ref=unit.result_contract_set_ref,
            assigned_actor=RESPONDENT,
            canonical_writer=WRITER,
            probe_designer=DESIGNER,
            adjudicator=ADJUDICATOR,
            allowed_information=(
                a.InformationGrant(
                    information_kind="manuscript_unit",
                    source_refs=(unit_ref,),
                    description="Read only the exact frozen manuscript unit.",
                ),
            ),
            forbidden_context=(
                "Exclude hidden probes, the answer key, and every other critic report.",
            ),
            transfer_objective="Transfer the competing-forces mechanism to one nearby case.",
            sealed_context_hash="5" * 64,
            sealed_at=CREATED,
        )
        probe_ref = eref("entity.probe.correct")
        probe, _, _, _, _ = probe_material()
        probe = probe.model_copy(
            update={
                "assignment_ref": assignment_ref,
                "manuscript_unit_ref": unit_ref,
                "frozen_manuscript_artifact_ref": unit.manuscript_artifact_ref,
            }
        )
        payloads: dict[tuple[str, int], a.AuthoringPayload] = {
            (unit_ref.entity_id, unit_ref.version): unit,
            (assignment_ref.entity_id, assignment_ref.version): assignment,
            (probe_ref.entity_id, probe_ref.version): probe,
        }
        return (
            unit_ref,
            unit,
            assignment_ref,
            assignment,
            probe_ref,
            probe,
            payloads,
        )

    def test_answer_rejects_foreign_same_type_probe(self) -> None:
        (
            unit_ref,
            _,
            assignment_ref,
            _,
            _,
            probe,
            payloads,
        ) = self._cold_fixture()
        foreign_probe_ref = eref("entity.probe.foreign")
        payloads[(foreign_probe_ref.entity_id, foreign_probe_ref.version)] = (
            probe.model_copy(
                update={"manuscript_unit_ref": eref("entity.unit.foreign")}
            )
        )

        with self.assertRaisesRegex(
            av.AuthoringValidationError, "exact input lineage"
        ):
            av._validate_exact_route_input_lineage(
                "answer.reader_probe",
                {
                    "CriticAssignment": (assignment_ref,),
                    "ManuscriptUnit": (unit_ref,),
                    "ReaderProbeSet": (foreign_probe_ref,),
                },
                payloads,
            )

    def test_adjudication_rejects_foreign_same_type_response(self) -> None:
        (
            unit_ref,
            _,
            assignment_ref,
            _,
            probe_ref,
            _,
            payloads,
        ) = self._cold_fixture()
        response_ref = eref("entity.response.foreign")
        payloads[(response_ref.entity_id, response_ref.version)] = a.ReaderResponse(
            probe_set_ref=eref("entity.probe.other"),
            manuscript_unit_ref=unit_ref,
            respondent=RESPONDENT,
            answered_probe_ids=tuple(
                f"probe.{kind}" for kind in a.READER_PROBE_KIND_ORDER
            ),
            response_artifact_ref=aref("artifact.response.foreign"),
            route_run_id="run.answer.foreign",
            context_manifest_hash="6" * 64,
            submitted_at=CREATED,
        )

        with self.assertRaisesRegex(
            av.AuthoringValidationError, "exact input lineage"
        ):
            av._validate_exact_route_input_lineage(
                "adjudicate.reader_probe",
                {
                    "CriticAssignment": (assignment_ref,),
                    "ManuscriptUnit": (unit_ref,),
                    "ReaderProbeSet": (probe_ref,),
                    "ReaderResponse": (response_ref,),
                },
                payloads,
            )

    def _closure_fixture(self) -> tuple[
        EntityVersionRef,
        a.ManuscriptUnit,
        EntityVersionRef,
        tuple[EntityVersionRef, ...],
        dict[tuple[str, int], a.AuthoringPayload],
    ]:
        _, _, _, unit = manuscript_material(writer_packet_hash="0" * 64)
        unit_ref = eref("entity.unit.processing")
        paper = paper_ir(mode="working")
        assurance_ref = paper.assurance_bundle_ref
        assert assurance_ref is not None
        review_refs = (
            eref("review.formal.close"),
            eref("review.economic.close"),
            eref("review.cold.close"),
        )
        payloads: dict[tuple[str, int], a.AuthoringPayload] = {
            (unit_ref.entity_id, unit_ref.version): unit,
            (unit.paper_ir_ref.entity_id, unit.paper_ir_ref.version): paper,
            (assurance_ref.entity_id, assurance_ref.version): (
                a.AssuranceBundle.model_construct()
            ),
        }
        for role, reference in zip(
            ("formal_fidelity", "economic_reader", "cold_reader"), review_refs
        ):
            payloads[(reference.entity_id, reference.version)] = (
                a.ReviewRecord.model_construct(
                    role=role,
                    manuscript_unit_ref=unit_ref,
                    reviewed_artifact_ref=unit.manuscript_artifact_ref,
                )
            )
        return unit_ref, unit, assurance_ref, review_refs, payloads

    def test_closure_rejects_foreign_same_type_assurance(self) -> None:
        unit_ref, _, _, review_refs, payloads = self._closure_fixture()
        foreign_assurance_ref = eref("assurance.foreign")
        payloads[(foreign_assurance_ref.entity_id, foreign_assurance_ref.version)] = (
            a.AssuranceBundle.model_construct()
        )

        with self.assertRaisesRegex(
            av.AuthoringValidationError, "exact input lineage"
        ):
            av._validate_exact_route_input_lineage(
                "close.manuscript_review",
                {
                    "AssuranceBundle": (foreign_assurance_ref,),
                    "ManuscriptUnit": (unit_ref,),
                    "ReviewRecord": review_refs,
                },
                payloads,
            )

    def test_closure_rejects_review_of_another_same_type_unit(self) -> None:
        unit_ref, unit, assurance_ref, review_refs, payloads = self._closure_fixture()
        replaced_ref = review_refs[1]
        payloads[(replaced_ref.entity_id, replaced_ref.version)] = (
            a.ReviewRecord.model_construct(
                role="economic_reader",
                manuscript_unit_ref=eref("entity.unit.foreign"),
                reviewed_artifact_ref=unit.manuscript_artifact_ref,
            )
        )

        with self.assertRaisesRegex(
            av.AuthoringValidationError, "exact input lineage"
        ):
            av._validate_exact_route_input_lineage(
                "close.manuscript_review",
                {
                    "AssuranceBundle": (assurance_ref,),
                    "ManuscriptUnit": (unit_ref,),
                    "ReviewRecord": review_refs,
                },
                payloads,
            )


class EconomicExplanationDowngradeTests(unittest.TestCase):
    def _fixture(self, *, restatement: bool) -> tuple[
        EntityVersionRef, a.ReviewRecord, dict[tuple[str, int], a.AuthoringPayload]
    ]:
        paper = paper_ir(mode="preview")
        reader = reader_path()
        projection = paper.claim_projections[0]
        paper_ref = eref("paper.ir")
        reader_ref = eref("reader.path")
        contracts_ref = eref("result.contracts")
        unit_ref = eref("manuscript.unit")
        source_ref = eref("economic.argument.graph")

        def layer(content: str) -> a.LayerContract:
            return a.LayerContract(
                applicability="applicable", content=content, source_refs=(source_ref,)
            )

        def element(content: str) -> a.ContractElement:
            return a.ContractElement(content=content, source_refs=(source_ref,))

        packet = a.ResultPacket(
            packet_id="packet.reversal",
            claim_projection_id=projection.projection_id,
            claim_graph_ref=projection.claim_graph_ref,
            claim_id=projection.claim_id,
            primary_archetype="comparative_statics_threshold",
            question=layer("Can precision reduce realized accuracy with endogenous use?"),
            pre_result_expectation=a.LayerContract(
                applicability="not_applicable",
                not_applicable_reason="The reader path already states the maintained benchmark.",
            ),
            formal_statement_and_scope=layer(projection.formal_statement),
            economic_translation=layer(projection.semantic_translation),
            archetype_explanation=layer(
                "A direct accuracy gain competes with a precision-linked participation cost."
            ),
            boundary=layer(
                "The reversal vanishes when precision no longer changes information uptake."
            ),
            proof_roadmap=layer(
                "Order the participation thresholds and compare realized actions by regime."
            ),
            consequence=layer(
                "Information quality cannot be ranked independently of endogenous use."
            ),
            archetype_module=a.ComparativeStaticsThresholdModule(
                perturbation=element("Increase signal precision from the low to high level."),
                competing_effects=element(
                    "Conditional accuracy rises while the participation cost also rises."
                ),
                monotonicity_domain=element("Use the maintained interior precision domain."),
                threshold_or_regime_logic=element(
                    "The high-precision participation threshold crosses first."
                ),
                reversal_or_boundary_witness=element(
                    "Only coarse information is used inside the separating interval."
                ),
            ),
        )
        contracts = a.ResultContractSet(
            paper_ir_ref=paper_ref,
            reader_path_ref=reader_ref,
            claim_graph_ref=projection.claim_graph_ref,
            assumption_map_ref=eref("assumption.map"),
            economic_argument_graph_ref=source_ref,
            example_suite_ref=eref("example.suite"),
            verification_bundle_ref=eref("verification.bundle"),
            result_packets=(packet,),
            proof_roadmaps=(
                a.ProofRoadmapContract(
                    roadmap_id="roadmap.reversal",
                    claim_id=projection.claim_id,
                    object_constructed_or_compared="The low- and high-precision participation thresholds.",
                    key_decomposition_or_monotonicity_step="Separate conditional accuracy from the extensive participation response.",
                    assumption_roles=("Indivisible use creates the relevant extensive margin.",),
                    main_technical_obstacle="Track the exact endpoint and tie-breaking cases.",
                    method_or_certificate="Analytic threshold ordering over the maintained domain.",
                    scope_not_established="No welfare comparison is established outside this domain.",
                    proof_refs=(eref("verification.bundle"),),
                ),
            ),
            built_at=CREATED,
        )
        source_field = SemanticFacetRef(
            entity_id=projection.claim_graph_ref.entity_id,
            version=projection.claim_graph_ref.version,
            facet="economic_interpretation",
            field_path="/payload/claims/0/semantic_translation",
            semantic_hash="5" * 64,
        )

        def span(
            assertion_id: str,
            role: str,
            start: int,
            end: int,
        ) -> a.ConsequentialSpan:
            return a.ConsequentialSpan(
                assertion_id=assertion_id,
                role=role,  # type: ignore[arg-type]
                claim_projection_id=projection.projection_id,
                claim_graph_ref=projection.claim_graph_ref,
                claim_id=projection.claim_id,
                source_fields=(source_field,),
                scope=projection.scope,
                assumption_ids=projection.assumption_ids,
                support_refs=(source_ref,) if role == "mechanism_or_conceptual_explanation" else (),
                location=a.ManuscriptLocation(start_offset=start, end_offset=end),
                text_hash="6" * 64,
                wording_strength="entailed_weaker",
                presentation=(
                    "mechanism_explanation"
                    if role == "mechanism_or_conceptual_explanation"
                    else "evidence_description"
                ),
            )

        manuscript_ref = aref("artifact.economic.manuscript")
        unit = a.ManuscriptUnit(
            unit_id="unit.economic",
            paper_ir_ref=paper_ref,
            reader_path_ref=reader_ref,
            result_contract_set_ref=contracts_ref,
            section_contract_id="section.results",
            manuscript_artifact_ref=manuscript_ref,
            source_state_revision=HEAD,
            canonical_writer=WRITER,
            writer_role_packet_hash="7" * 64,
            writer_output_hash=manuscript_ref.content_hash,
            integration_generation=1,
            spans=(
                span("assertion.mechanism", "mechanism_or_conceptual_explanation", 0, 100),
                span("assertion.example", "example_or_witness", 100, 160),
                span("assertion.boundary", "boundary", 160, 210),
            ),
            terminology=(
                a.TerminologyRealization(
                    object_id="object.processing",
                    realized_name="information-use decision",
                    formal_symbol="d",
                    first_use_assertion_id="assertion.mechanism",
                ),
            ),
            composed_at=CREATED,
        )
        assignment_ref = eref("assignment.economic")
        assignment = a.CriticAssignment(
            assignment_id="assignment.economic",
            role="economic_reader",
            paper_ir_ref=paper_ref,
            reader_path_ref=reader_ref,
            result_contract_set_ref=contracts_ref,
            assigned_actor=ECONOMIC_READER,
            canonical_writer=WRITER,
            allowed_information=(
                a.InformationGrant(
                    information_kind="manuscript_unit",
                    source_refs=(unit_ref,),
                    description="Read the exact manuscript unit as an economic reader.",
                ),
            ),
            forbidden_context=("Do not inspect other critic reports.",),
            sealed_context_hash="8" * 64,
            sealed_at=CREATED,
        )
        reconstruction = a.EconomicReconstruction(
            claim_projection_id=projection.projection_id,
            claim_id=projection.claim_id,
            result_packet_id=packet.packet_id,
            question_and_benchmark="The benchmark fixes information use, while the paper asks about realized accuracy with endogenous use.",
            operative_force="A precision-linked cost pushes against the conditional accuracy gain from a sharper signal.",
            affected_margin="The affected margin is the receiver's discrete decision to use information at all.",
            serious_rival_and_separator="The serious rival is the direct accuracy gain, separated by a case where uptake changes across signals.",
            mechanism_steps=(
                "Precision first improves accuracy conditional on processing the available signal.",
                "The same change raises processing cost and shifts the discrete participation threshold.",
                "Between thresholds the coarse signal is used while the precise signal is ignored.",
            ),
            mechanism_assertion_ids=("assertion.mechanism",),
            diagnostic_assertion_ids=("assertion.example",),
            boundary_assertion_ids=("assertion.boundary",),
            near_transfer_prediction="Reducing the precision-linked cost closes the threshold gap and removes the reversal.",
            explanatory_delta_from_formal_statement=(
                projection.formal_statement
                if restatement
                else "Precision-linked cost opposes accuracy at the discrete uptake margin; threshold ordering separates used coarse information from ignored precise information."
            ),
            evidence_refs=(unit_ref, manuscript_ref),
        )
        review = a.ReviewRecord(
            assignment_ref=assignment_ref,
            manuscript_unit_ref=unit_ref,
            reviewed_artifact_ref=manuscript_ref,
            role="economic_reader",
            reviewer=ECONOMIC_READER,
            canonical_writer=WRITER,
            context_hash="9" * 64,
            assessment=a.EconomicReaderAssessment(
                question_and_benchmark_reconstructible=True,
                explanation_is_not_restatement=True,
                mechanism_or_conceptual_logic_reconstructible=True,
                diagnostic_example_or_witness_present=True,
                boundary_is_economically_interpretable=True,
                reconstructions=(reconstruction,),
            ),
            reviewed_at=CREATED,
        )
        payloads: dict[tuple[str, int], a.AuthoringPayload] = {
            (paper_ref.entity_id, paper_ref.version): paper,
            (reader_ref.entity_id, reader_ref.version): reader,
            (contracts_ref.entity_id, contracts_ref.version): contracts,
            (unit_ref.entity_id, unit_ref.version): unit,
            (assignment_ref.entity_id, assignment_ref.version): assignment,
        }
        return eref("review.economic"), review, payloads

    def test_empty_economic_reconstruction_is_rejected_by_the_schema(self) -> None:
        _, review, _ = self._fixture(restatement=False)
        reconstruction = review.assessment.reconstructions[0]
        values = reconstruction.model_dump(mode="python")
        values["operative_force"] = "empty"
        with self.assertRaises(ValidationError):
            a.EconomicReconstruction(**values)

    def test_formal_restatement_cannot_pass_as_economic_explanation(self) -> None:
        review_ref, review, payloads = self._fixture(restatement=True)
        with self.assertRaisesRegex(
            av.AuthoringValidationError, "merely repeats a projected claim field"
        ):
            av._validate_review_lineage(review_ref, review, payloads)

    def test_review_route_rejects_foreign_same_type_design_inputs(self) -> None:
        _, review, payloads = self._fixture(restatement=False)
        foreign_paper_ref = eref("paper.foreign")
        foreign_contracts_ref = eref("contracts.foreign")
        original_paper = payloads[("paper.ir", 1)]
        original_contracts = payloads[("result.contracts", 1)]
        assert isinstance(original_paper, a.PaperIR)
        assert isinstance(original_contracts, a.ResultContractSet)
        payloads[(foreign_paper_ref.entity_id, foreign_paper_ref.version)] = (
            original_paper
        )
        payloads[(foreign_contracts_ref.entity_id, foreign_contracts_ref.version)] = (
            original_contracts.model_copy(update={"paper_ir_ref": foreign_paper_ref})
        )
        actual_inputs = {
            "CriticAssignment": (review.assignment_ref,),
            "ManuscriptUnit": (review.manuscript_unit_ref,),
            "PaperIR": (foreign_paper_ref,),
            "ResultContractSet": (foreign_contracts_ref,),
        }

        with self.assertRaisesRegex(
            av.AuthoringValidationError, "exact input lineage"
        ):
            av._validate_exact_route_input_lineage(
                "review.manuscript_unit", actual_inputs, payloads
            )

    def test_one_good_result_cannot_hide_an_unreviewed_second_result_packet(self) -> None:
        review_ref, review, payloads = self._fixture(restatement=False)
        paper_ref = eref("paper.ir")
        reader_ref = eref("reader.path")
        contracts_ref = eref("result.contracts")
        unit_ref = eref("manuscript.unit")
        paper = payloads[(paper_ref.entity_id, paper_ref.version)]
        reader = payloads[(reader_ref.entity_id, reader_ref.version)]
        contracts = payloads[(contracts_ref.entity_id, contracts_ref.version)]
        unit = payloads[(unit_ref.entity_id, unit_ref.version)]
        assert isinstance(paper, a.PaperIR)
        assert isinstance(reader, a.ReaderPath)
        assert isinstance(contracts, a.ResultContractSet)
        assert isinstance(unit, a.ManuscriptUnit)

        second_projection = paper.claim_projections[0].model_copy(
            update={
                "projection_id": "projection.reversal.second",
                "claim_id": "claim.reversal.second",
            }
        )
        second_packet = contracts.result_packets[0].model_copy(
            update={
                "packet_id": "packet.reversal.second",
                "claim_projection_id": second_projection.projection_id,
                "claim_id": second_projection.claim_id,
            }
        )
        second_spans = tuple(
            span.model_copy(
                update={
                    "assertion_id": f"{span.assertion_id}.second",
                    "claim_projection_id": second_projection.projection_id,
                    "claim_id": second_projection.claim_id,
                    "location": a.ManuscriptLocation(
                        start_offset=span.location.start_offset + 300,
                        end_offset=span.location.end_offset + 300,
                    ),
                }
            )
            for span in unit.spans
        )
        section = reader.section_contracts[0].model_copy(
            update={
                "required_claim_projection_ids": (
                    paper.claim_projections[0].projection_id,
                    second_projection.projection_id,
                )
            }
        )
        payloads[(paper_ref.entity_id, paper_ref.version)] = paper.model_copy(
            update={"claim_projections": (*paper.claim_projections, second_projection)}
        )
        payloads[(reader_ref.entity_id, reader_ref.version)] = reader.model_copy(
            update={"section_contracts": (section,)}
        )
        payloads[(contracts_ref.entity_id, contracts_ref.version)] = contracts.model_copy(
            update={"result_packets": (*contracts.result_packets, second_packet)}
        )
        payloads[(unit_ref.entity_id, unit_ref.version)] = unit.model_copy(
            update={"spans": (*unit.spans, *second_spans)}
        )

        with self.assertRaisesRegex(
            av.AuthoringValidationError,
            "one reconstruction for every section ResultPacket",
        ):
            av._validate_review_lineage(review_ref, review, payloads)

    def test_cold_probes_cannot_target_only_one_of_two_required_packets(self) -> None:
        _, _, payloads = self._fixture(restatement=False)
        reader_ref = eref("reader.path")
        contracts_ref = eref("result.contracts")
        unit_ref = eref("manuscript.unit")
        reader = payloads[(reader_ref.entity_id, reader_ref.version)]
        contracts = payloads[(contracts_ref.entity_id, contracts_ref.version)]
        unit = payloads[(unit_ref.entity_id, unit_ref.version)]
        assert isinstance(reader, a.ReaderPath)
        assert isinstance(contracts, a.ResultContractSet)
        assert isinstance(unit, a.ManuscriptUnit)

        first_packet = contracts.result_packets[0]
        second_packet = first_packet.model_copy(
            update={
                "packet_id": "packet.reversal.second",
                "claim_projection_id": "projection.reversal.second",
                "claim_id": "claim.reversal.second",
            }
        )
        section = reader.section_contracts[0].model_copy(
            update={
                "required_claim_projection_ids": (
                    first_packet.claim_projection_id,
                    second_packet.claim_projection_id,
                )
            }
        )
        reader = reader.model_copy(update={"section_contracts": (section,)})
        contracts = contracts.model_copy(
            update={"result_packets": (first_packet, second_packet)}
        )
        base_probe, _, _, _, _ = probe_material()
        probe = base_probe.model_copy(
            update={
                "probes": tuple(
                    descriptor.model_copy(
                        update={
                            "target_assertion_ids": ("assertion.mechanism",),
                            "target_contract_ids": (first_packet.packet_id,),
                        }
                    )
                    for descriptor in base_probe.probes
                )
            }
        )

        with self.assertRaisesRegex(
            av.AuthoringValidationError,
            "every cold-reader probe must cover every section ResultPacket",
        ):
            av._validate_reader_probe_packet_coverage(
                probe, unit, reader, contracts
            )


class SubmissionFormattingDowngradeTests(unittest.TestCase):
    def setUp(self) -> None:
        _, _, _, self.source = manuscript_material(writer_packet_hash="0" * 64)

    def test_formatting_only_may_move_span_offsets(self) -> None:
        source_span = self.source.spans[0]
        moved_span = source_span.model_copy(
            update={
                "location": a.ManuscriptLocation(
                    start_offset=11,
                    end_offset=11
                    + source_span.location.end_offset
                    - source_span.location.start_offset,
                )
            }
        )
        submission = self.source.model_copy(update={"spans": (moved_span,)})

        av._validate_submission_unit_semantics(self.source, submission)

    def test_formatting_only_rejects_text_hash_or_span_semantic_changes(self) -> None:
        source_span = self.source.spans[0]
        attacks = (
            ("text_hash", source_span.model_copy(update={"text_hash": "1" * 64})),
            (
                "scope",
                source_span.model_copy(
                    update={"scope": "A broader domain that was never approved."}
                ),
            ),
        )
        for label, forged_span in attacks:
            with self.subTest(attack=label), self.assertRaisesRegex(
                av.AuthoringValidationError,
                "formatting but not approved prose semantics",
            ):
                av._validate_submission_unit_semantics(
                    self.source,
                    self.source.model_copy(update={"spans": (forged_span,)}),
                )

    def test_formatting_only_rejects_relative_span_order_reversal(self) -> None:
        first = self.source.spans[0]
        width = first.location.end_offset - first.location.start_offset
        second = first.model_copy(
            update={
                "assertion_id": "assertion.processing.response.second",
                "location": a.ManuscriptLocation(
                    start_offset=width, end_offset=2 * width
                ),
            }
        )
        approved = self.source.model_copy(update={"spans": (first, second)})
        moved_second = second.model_copy(
            update={
                "location": a.ManuscriptLocation(start_offset=0, end_offset=width)
            }
        )
        moved_first = first.model_copy(
            update={
                "location": a.ManuscriptLocation(
                    start_offset=width, end_offset=2 * width
                )
            }
        )
        reordered = self.source.model_copy(
            update={"spans": (moved_second, moved_first)}
        )

        with self.assertRaisesRegex(
            av.AuthoringValidationError,
            "formatting but not approved prose semantics",
        ):
            av._validate_submission_unit_semantics(approved, reordered)


class AuthoringReadyFreshnessDowngradeTests(unittest.TestCase):
    def _guard_fixture(self) -> tuple[
        EntityVersionRef,
        a.ReviewClosure,
        dict[tuple[str, int], EntityVersion],
        dict[tuple[str, int], a.AuthoringPayload],
        dict[str, int],
    ]:
        closure_ref = eref("closure.authoring.ready")
        references = {
            "paper_ir_ref": (eref("paper.authoring.ready"), "PaperIR"),
            "reader_path_ref": (eref("reader.authoring.ready"), "ReaderPath"),
            "result_contract_set_ref": (
                eref("contracts.authoring.ready"),
                "ResultContractSet",
            ),
            "assurance_bundle_ref": (
                eref("assurance.authoring.ready"),
                "AssuranceBundle",
            ),
            "manuscript_unit_ref": (
                eref("unit.authoring.ready"),
                "ManuscriptUnit",
            ),
            "formal_fidelity_review_ref": (
                eref("review.formal.authoring.ready"),
                "ReviewRecord",
            ),
            "economic_reader_review_ref": (
                eref("review.economic.authoring.ready"),
                "ReviewRecord",
            ),
            "cold_reader_review_ref": (
                eref("review.cold.authoring.ready"),
                "ReviewRecord",
            ),
        }
        closure = a.ReviewClosure.model_construct(
            compiler_mode="working",
            **{field: reference for field, (reference, _) in references.items()},
            status="authoring_ready",
        )
        entity_index = {
            (closure_ref.entity_id, closure_ref.version): EntityVersion.model_construct(
                entity_id=closure_ref.entity_id,
                entity_type="ReviewClosure",
                version=closure_ref.version,
            ),
            **{
                (reference.entity_id, reference.version): EntityVersion.model_construct(
                    entity_id=reference.entity_id,
                    entity_type=entity_type,
                    version=reference.version,
                )
                for reference, entity_type in references.values()
            },
        }
        payloads: dict[tuple[str, int], a.AuthoringPayload] = {
            (closure_ref.entity_id, closure_ref.version): closure
        }
        current = {
            reference.entity_id: reference.version
            for reference in (
                closure_ref,
                *(reference for reference, _ in references.values()),
            )
        }
        return closure_ref, closure, entity_index, payloads, current

    def _assert_guard_rejects(
        self,
        snapshot: Snapshot,
        closure_ref: EntityVersionRef,
        entity_index: dict[tuple[str, int], EntityVersion],
        payloads: dict[tuple[str, int], a.AuthoringPayload],
    ) -> None:
        with (
            patch.object(
                av,
                "_validated_indices",
                return_value=(entity_index, {}, {}, payloads, {}, None),
            ),
            self.assertRaisesRegex(
                av.AuthoringValidationError,
                "current and fresh closure/design/review chain",
            ),
        ):
            av.validate_authoring_ready(snapshot, closure_ref)

    def test_authoring_ready_rejects_non_current_closure(self) -> None:
        closure_ref, _, entity_index, payloads, current = self._guard_fixture()
        current.pop(closure_ref.entity_id)
        self._assert_guard_rejects(
            Snapshot(
                project_id=PROJECT,
                head=HEAD,
                chain=(HEAD,),
                current_entities=current,
            ),
            closure_ref,
            entity_index,
            payloads,
        )

    def test_authoring_ready_rejects_stale_key_chain_object(self) -> None:
        closure_ref, closure, entity_index, payloads, current = self._guard_fixture()
        unit_ref = closure.manuscript_unit_ref
        self._assert_guard_rejects(
            Snapshot(
                project_id=PROJECT,
                head=HEAD,
                chain=(HEAD,),
                current_entities=current,
                derived_status={
                    unit_ref.entity_id: EntityDerivedStatus(
                        freshness={"terminology_presentation": "stale"}
                    )
                },
            ),
            closure_ref,
            entity_index,
            payloads,
        )


class SubmissionPromotionDowngradeTests(unittest.TestCase):
    def test_promotion_requires_an_explicit_matching_machine_outcome(self) -> None:
        approved = decision(
            decision_id="promotion.manuscript",
            kind="manuscript_version_promotion",
            subject="closure.working",
            scope="question",
            selected="approve",
            machine_outcome="approve",
        )
        self.assertEqual(
            (approved.selected_option, approved.machine_outcome),
            ("approve", "approve"),
        )

        base = approved.model_dump(mode="python")
        for label, changes in (
            ("missing", {"machine_outcome": None}),
            ("mismatch", {"selected_option": "deny"}),
        ):
            with self.subTest(label=label), self.assertRaises(ValidationError):
                Decision(**{**base, **changes})

    def test_deny_promotion_cannot_unlock_submission_paper_ir(self) -> None:
        paper = paper_ir(mode="submission")
        package = t.ValidatedArgumentPackage.model_construct(
            question_ref=eref("question"),
            g5_dossier_ref=eref("g5.dossier"),
        )
        profile = a.ResolvedProfileManifest.model_construct()
        bundle = a.AssuranceBundle.model_construct(
            package_ref=paper.package_ref,
            g5_decision_ref=paper.g5_decision_ref,
        )
        g5 = decision(
            decision_id="gate.g5",
            kind="G5_argument_validation",
            subject="g5.dossier",
            scope="question",
            selected="approve",
            machine_outcome="approve",
        )
        denied = decision(
            decision_id="promotion.manuscript",
            kind="manuscript_version_promotion",
            subject="closure.working",
            scope="question",
            selected="deny",
            machine_outcome="deny",
        )
        package_entity = EntityVersion.model_construct(
            entity_id=paper.package_ref.entity_id,
            entity_type="ValidatedArgumentPackage",
            version=paper.package_ref.version,
        )

        def resolve_payload(_payloads, _reference, expected, _label):
            if expected is a.ResolvedProfileManifest:
                return profile
            if expected is a.AssuranceBundle:
                return bundle
            raise AssertionError(f"unexpected resolution request: {expected}")

        with (
            patch.object(av, "_expect_entity_type", return_value=package_entity),
            patch.object(av, "_resolve_payload", side_effect=resolve_payload),
            patch.object(
                av,
                "paper_ir_upstream_projection_hash",
                return_value=paper.upstream_projection_hash,
            ),
            self.assertRaisesRegex(
                av.AuthoringValidationError, "must explicitly approve"
            ),
        ):
            av._validate_paper_ir(
                Snapshot(project_id=PROJECT, head=HEAD, chain=(HEAD,)),
                paper,
                {},
                {},
                {(paper.package_ref.entity_id, paper.package_ref.version): package},
                {
                    (g5.decision_id, g5.version): g5,
                    (denied.decision_id, denied.version): denied,
                },
            )


if __name__ == "__main__":
    unittest.main()
