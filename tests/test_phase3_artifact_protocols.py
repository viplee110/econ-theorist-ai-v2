"""Byte-level Phase 3 manuscript and cold-reader protocol tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist import authoring as a
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


PROJECT = "project.phase3.artifacts"
HEAD = "a" * 64
CREATED = "2026-07-12T00:00:00Z"
WRITER = Actor(kind="agent", actor_id="agent.writer")
DESIGNER = Actor(kind="agent", actor_id="agent.probe.designer")
RESPONDENT = Actor(kind="agent", actor_id="agent.cold.reader")
ADJUDICATOR = Actor(kind="agent", actor_id="agent.probe.adjudicator")


def ref(artifact_id: str, data: bytes) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id,
        version=1,
        content_hash=sha256_digest(data),
    )


def registration(reference: ArtifactDependencyRef, data: bytes) -> ArtifactRegistration:
    return ArtifactRegistration(
        artifact_id=reference.artifact_id,
        version=reference.version,
        project_id=PROJECT,
        logical_name=f"artifact bytes for {reference.artifact_id}",
        media_type="application/json",
        content_hash=reference.content_hash,
        byte_size=len(data),
        human_owned=False,
        privacy="restricted",
        access_compartments=("project_research", "cold_reader"),
        created_at=CREATED,
    )


def entity(entity_id: str, payload: a.AuthoringPayload) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=1,
        project_id=PROJECT,
        title=f"Title {entity_id}",
        summary=f"Summary {entity_id}",
        status=ScientificStatus(lifecycle="proposed"),
        facets=a.pack_authoring_payload(payload),
        artifact_refs=tuple(
            sorted(
                {
                    value
                    for value in _walk(payload)
                    if isinstance(value, ArtifactDependencyRef)
                },
                key=lambda item: (item.artifact_id, item.version),
            )
        ),
        privacy="restricted",
        access_compartments=("project_research", "cold_reader"),
        created_at=CREATED,
    )


def _walk(value: object):
    from pydantic import BaseModel

    if isinstance(value, BaseModel):
        for name in type(value).model_fields:
            yield from _walk(getattr(value, name))
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _walk(item)
    else:
        yield value


def transaction(
    route_id: str,
    outputs: tuple[EntityVersion, ...],
    artifacts: tuple[ArtifactRegistration, ...],
) -> Transaction:
    return Transaction(
        transaction_id=f"transaction.{route_id}",
        origin="route_run",
        project_id=PROJECT,
        base_revision=HEAD,
        route_run_id=f"run.{route_id}",
        route_id=route_id,
        route_run_hash="b" * 64,
        context_manifest_hash="c" * 64,
        compiled_context_hash="d" * 64,
        actor=WRITER if route_id == "compose.manuscript_unit" else DESIGNER,
        intent="Exercise exact artifact bytes.",
        operations=(
            *(CreateEntityOp(entity=item) for item in outputs),
            *(RegisterArtifactOp(artifact=item) for item in artifacts),
        ),
        privacy="restricted",
        access_compartments=("project_research", "cold_reader"),
        created_at=CREATED,
        parent_transaction_hash=HEAD,
    )


class Phase3ArtifactProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = StoreLayout.at(Path(self.temporary.name))
        self.layout.ensure()
        self.store = ObjectStore(self.layout)
        self.snapshot = Snapshot(project_id=PROJECT, head=HEAD, chain=(HEAD,))

    def _install(self, reference: ArtifactDependencyRef, data: bytes) -> None:
        self.store.install_bytes("artifacts", reference.content_hash, data)

    def test_compose_reads_real_text_and_rejects_fabricated_span_hash(self) -> None:
        text = "A higher cost weakens the processing response."
        data = text.encode("utf-8")
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
        manuscript_ref = ref("artifact.manuscript", data)
        span = a.ConsequentialSpan(
            assertion_id="assertion.processing",
            role="economic_translation",
            claim_projection_id="projection.processing",
            claim_graph_ref=EntityVersionRef(entity_id="entity.claims", version=1),
            claim_id="claim.processing",
            source_fields=(
                SemanticFacetRef(
                    entity_id="entity.claims",
                    version=1,
                    facet="formal",
                    field_path="/payload/claims/0/semantic_translation",
                    semantic_hash="e" * 64,
                ),
            ),
            scope="Maintained processing-cost domain.",
            assumption_ids=("assumption.cost",),
            location=a.ManuscriptLocation(start_offset=0, end_offset=len(text)),
            text_hash=sha256_digest(data),
            wording_strength="entailed_equivalent",
            presentation="economic_interpretation",
        )
        unit = a.ManuscriptUnit(
            unit_id="unit.processing",
            paper_ir_ref=EntityVersionRef(entity_id="entity.paper", version=1),
            reader_path_ref=EntityVersionRef(entity_id="entity.reader", version=1),
            result_contract_set_ref=EntityVersionRef(entity_id="entity.contracts", version=1),
            section_contract_id="section.result",
            manuscript_artifact_ref=manuscript_ref,
            source_state_revision=HEAD,
            canonical_writer=WRITER,
            writer_role_packet_hash=sha256_digest(canonical_json_bytes(role_packet)),
            writer_output_hash=manuscript_ref.content_hash,
            integration_generation=1,
            spans=(span,),
            terminology=(
                a.TerminologyRealization(
                    object_id="object.cost",
                    realized_name="processing cost",
                    formal_symbol="c",
                    first_use_assertion_id=span.assertion_id,
                ),
            ),
            composed_at=CREATED,
        )
        output = entity("entity.unit", unit)
        reg = registration(manuscript_ref, data)
        self._install(manuscript_ref, data)
        tx = transaction("compose.manuscript_unit", (output,), (reg,)).model_copy(
            update={"compiled_context_hash": context_hash}
        )
        validate_phase3_operational_artifacts(self.layout, self.snapshot, tx)

        forged_span = span.model_copy(update={"text_hash": "f" * 64})
        forged = unit.model_copy(update={"spans": (forged_span,)})
        with self.assertRaisesRegex(Phase3ArtifactError, "text hash"):
            validate_phase3_operational_artifacts(
                self.layout,
                self.snapshot,
                transaction("compose.manuscript_unit", (entity("entity.forged", forged),), (reg,)).model_copy(
                    update={"compiled_context_hash": context_hash}
                ),
            )

    def test_probe_key_and_response_bytes_have_closed_hashes(self) -> None:
        assignment_ref = EntityVersionRef(entity_id="entity.assignment", version=1)
        unit_ref = EntityVersionRef(entity_id="entity.unit", version=1)
        manuscript_ref = ArtifactDependencyRef(
            artifact_id="artifact.manuscript", version=1, content_hash="1" * 64
        )
        prompts = tuple(
            ReaderProbePrompt(
                probe_id=f"probe.{kind}",
                kind=kind,  # type: ignore[arg-type]
                prompt=f"Please answer the {kind.replace('_', ' ')} question.",
                prompt_hash=sha256_digest(
                    f"Please answer the {kind.replace('_', ' ')} question.".encode()
                ),
                target_contract_ids=("contract.result",),
            )
            for kind in a.READER_PROBE_KIND_ORDER
        )
        criteria = tuple(
            ReaderAnswerCriterion(
                probe_id=item.probe_id,
                kind=item.kind,
                criterion=f"Credit requires a precise reconstruction for {item.kind}.",
                criterion_hash=sha256_digest(
                    f"Credit requires a precise reconstruction for {item.kind}.".encode()
                ),
                required_content=("A precise economic statement.",),
            )
            for item in prompts
        )
        visible = ReaderProbeArtifact(
            assignment_ref=assignment_ref,
            manuscript_unit_ref=unit_ref,
            frozen_manuscript_artifact_ref=manuscript_ref,
            respondent=RESPONDENT,
            transfer_objective="Transfer the competing-forces argument once.",
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
        visible_ref = ref("artifact.probes", visible_data)
        key_ref = ref("artifact.answer.key", key_data)
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
            probe_artifact_ref=visible_ref,
            answer_key_artifact_ref=key_ref,
            route_run_id="run.prepare",
            context_manifest_hash="2" * 64,
            sealed_at=CREATED,
        )
        self._install(visible_ref, visible_data)
        self._install(key_ref, key_data)
        tx = transaction(
            "prepare.reader_probe",
            (entity("entity.probes", probe),),
            (registration(visible_ref, visible_data), registration(key_ref, key_data)),
        )
        validate_phase3_operational_artifacts(self.layout, self.snapshot, tx)

        answers = tuple(
            ReaderAnswer(
                probe_id=item.probe_id,
                kind=item.kind,
                response=f"Response for {item.kind}.",
                response_hash=sha256_digest(f"Response for {item.kind}.".encode()),
            )
            for item in prompts
        )
        response = ReaderResponseArtifact(
            probe_set_ref=EntityVersionRef(entity_id="entity.probes", version=1),
            manuscript_unit_ref=unit_ref,
            respondent=RESPONDENT,
            answers=answers,
        )
        with self.assertRaises(ValueError):
            ReaderResponseArtifact(
                **{
                    **response.model_dump(mode="python"),
                    "answers": (
                        answers[0].model_copy(update={"response_hash": "3" * 64}),
                        *answers[1:],
                    ),
                }
            )


if __name__ == "__main__":
    unittest.main()
