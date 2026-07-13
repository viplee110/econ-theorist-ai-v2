"""Operational byte checks for Phase 3 manuscripts and reader probes."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import ValidationError as PydanticValidationError

from .. import authoring as a
from ..authoring_artifacts import (
    ProofAuditReportArtifact,
    ReaderAnswerKeyArtifact,
    ReaderProbeArtifact,
    ReaderResponseArtifact,
    ReDerivationTranscript,
)
from ..authoring_validation import (
    AuthoringValidationError,
    validate_manuscript_spans_and_text,
)
from ..codec import canonical_json_bytes, sha256_digest
from ..errors import EconTheoristError, RuntimeStoreError
from ..models import (
    ArtifactDependencyRef,
    ArtifactRegistration,
    CreateEntityOp,
    EntityVersion,
    EntityVersionRef,
    RegisterArtifactOp,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from .layout import StoreLayout
from .objects import ObjectStore


_BYTE_CHECKED_ROUTES = frozenset(
    {
        "verify.independent_rederivation",
        "audit.argument_assurance",
        "compose.manuscript_unit",
        "compose.profiled_manuscript_unit",
        "review.manuscript_unit",
        "prepare.reader_probe",
        "answer.reader_probe",
        "adjudicate.reader_probe",
        "close.manuscript_review",
    }
)


class Phase3ArtifactError(EconTheoristError, ValueError):
    """Phase 3 declarations disagree with immutable artifact bytes."""


def _ref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def _produced_entities(transaction: Transaction) -> tuple[EntityVersion, ...]:
    return tuple(
        operation.entity
        for operation in transaction.operations
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp))
    )


def _payload_index(
    snapshot: Snapshot, transaction: Transaction
) -> dict[tuple[str, int], a.AuthoringPayload]:
    result: dict[tuple[str, int], a.AuthoringPayload] = {}
    for entity in (*snapshot.entity_versions, *_produced_entities(transaction)):
        if not a.is_packed_authoring_entity(entity):
            continue
        try:
            result[(entity.entity_id, entity.version)] = a.parse_authoring_entity(entity)
        except (TypeError, ValueError) as exc:
            raise Phase3ArtifactError(
                f"authoring artifact owner does not parse: {entity.entity_id}@{entity.version}"
            ) from exc
    return result


def _resolve_payload(
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    reference: EntityVersionRef,
    expected: type[a.AuthoringPayload],
    label: str,
) -> a.AuthoringPayload:
    value = payloads.get((reference.entity_id, reference.version))
    if not isinstance(value, expected):
        raise Phase3ArtifactError(f"{label} does not resolve to {expected.__name__}")
    return value


def _artifact_index(
    snapshot: Snapshot, transaction: Transaction
) -> dict[tuple[str, int], ArtifactRegistration]:
    result = {
        (item.artifact_id, item.version): item for item in snapshot.artifacts
    }
    for operation in transaction.operations:
        if not isinstance(operation, RegisterArtifactOp):
            continue
        item = operation.artifact
        key = (item.artifact_id, item.version)
        if key in result:
            raise Phase3ArtifactError("transaction repeats an artifact registration")
        result[key] = item
    return result


def _read_artifact(
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    reference: ArtifactDependencyRef,
) -> bytes:
    registration = registrations.get((reference.artifact_id, reference.version))
    if registration is None or registration.content_hash != reference.content_hash:
        raise Phase3ArtifactError("artifact reference is unregistered or hash-mismatched")
    try:
        data = ObjectStore(layout).read_bytes(
            "artifacts", reference.content_hash, verify=True
        )
    except RuntimeStoreError as exc:
        raise Phase3ArtifactError("artifact bytes are absent from immutable storage") from exc
    if len(data) != registration.byte_size:
        raise Phase3ArtifactError("artifact bytes disagree with registered byte_size")
    return data


def _parse_artifact(data: bytes, model, label: str):
    try:
        value = model.model_validate_json(data, strict=True)
    except PydanticValidationError as exc:
        raise Phase3ArtifactError(f"{label} fails its strict byte protocol") from exc
    if canonical_json_bytes(value) != data:
        raise Phase3ArtifactError(f"{label} is not canonical JSON")
    return value


def _validate_manuscript(
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    unit: a.ManuscriptUnit,
) -> None:
    data = _read_artifact(layout, registrations, unit.manuscript_artifact_ref)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise Phase3ArtifactError("manuscript artifact is not UTF-8") from exc
    if "\r" in text or "\x00" in text:
        raise Phase3ArtifactError("manuscript artifact must use canonical LF text")
    try:
        validate_manuscript_spans_and_text(unit, text)
    except AuthoringValidationError as exc:
        raise Phase3ArtifactError(f"manuscript bytes fail semantic checks: {exc}") from exc


def _validate_writer_binding(
    layout: StoreLayout, transaction: Transaction, unit: a.ManuscriptUnit
) -> None:
    if transaction.compiled_context_hash is None:
        raise Phase3ArtifactError("compose transaction lacks its compiled context")
    try:
        data = ObjectStore(layout).read_bytes(
            "provenance", transaction.compiled_context_hash, verify=True
        )
    except RuntimeStoreError as exc:
        raise Phase3ArtifactError("canonical writer context bytes are unavailable") from exc
    import json

    try:
        context = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Phase3ArtifactError("canonical writer context is not UTF-8 JSON") from exc
    if not isinstance(context, dict) or canonical_json_bytes(context) != data:
        raise Phase3ArtifactError("canonical writer context is not canonical JSON")
    profiled = transaction.route_id == "compose.profiled_manuscript_unit"
    packet = context.get("phase4_role_packet" if profiled else "phase3_role_packet")
    if (
        not isinstance(packet, dict)
        or packet.get("packet_kind")
        != ("profiled_canonical_writer" if profiled else "canonical_writer")
    ):
        raise Phase3ArtifactError("compose context lacks its canonical-writer role packet")
    if unit.writer_role_packet_hash != sha256_digest(canonical_json_bytes(packet)):
        raise Phase3ArtifactError(
            "ManuscriptUnit is not bound to the exact writer role packet"
        )
    if unit.writer_output_hash != unit.manuscript_artifact_ref.content_hash:
        raise Phase3ArtifactError("writer output hash differs from manuscript bytes")


def _reader_artifacts(
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    probe: a.ReaderProbeSet,
) -> tuple[ReaderProbeArtifact, ReaderAnswerKeyArtifact]:
    visible = _parse_artifact(
        _read_artifact(layout, registrations, probe.probe_artifact_ref),
        ReaderProbeArtifact,
        "reader-probe artifact",
    )
    key = _parse_artifact(
        _read_artifact(layout, registrations, probe.answer_key_artifact_ref),
        ReaderAnswerKeyArtifact,
        "reader answer-key artifact",
    )
    expected_probe_rows = tuple(
        (
            item.probe_id,
            item.kind,
            item.prompt_hash,
            item.target_assertion_ids,
            item.target_contract_ids,
        )
        for item in probe.probes
    )
    actual_probe_rows = tuple(
        (
            item.probe_id,
            item.kind,
            item.prompt_hash,
            item.target_assertion_ids,
            item.target_contract_ids,
        )
        for item in visible.probes
    )
    descriptor_rows = tuple((item.probe_id, item.kind) for item in probe.probes)
    if (
        visible.assignment_ref != probe.assignment_ref
        or visible.manuscript_unit_ref != probe.manuscript_unit_ref
        or visible.frozen_manuscript_artifact_ref
        != probe.frozen_manuscript_artifact_ref
        or visible.respondent != probe.respondent
        or visible.transfer_objective != probe.transfer_objective
        or actual_probe_rows != expected_probe_rows
        or key.assignment_ref != probe.assignment_ref
        or key.manuscript_unit_ref != probe.manuscript_unit_ref
        or key.frozen_manuscript_artifact_ref
        != probe.frozen_manuscript_artifact_ref
        or key.adjudicator != probe.adjudicator
        or tuple((item.probe_id, item.kind) for item in key.criteria)
        != descriptor_rows
    ):
        raise Phase3ArtifactError(
            "reader probe/key bytes disagree with the sealed ReaderProbeSet"
        )
    normalized_prompts = tuple(" ".join(item.prompt.lower().split()) for item in visible.probes)
    for criterion in key.criteria:
        normalized = " ".join(criterion.criterion.lower().split())
        if normalized and any(normalized in prompt for prompt in normalized_prompts):
            raise Phase3ArtifactError(
                "visible reader prompt leaks a sealed answer-key criterion"
            )
    return visible, key


def _response_artifact(
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    response: a.ReaderResponse,
    probe: a.ReaderProbeSet,
) -> ReaderResponseArtifact:
    artifact = _parse_artifact(
        _read_artifact(layout, registrations, response.response_artifact_ref),
        ReaderResponseArtifact,
        "reader-response artifact",
    )
    expected = tuple((item.probe_id, item.kind) for item in probe.probes)
    if (
        artifact.probe_set_ref != response.probe_set_ref
        or artifact.manuscript_unit_ref != response.manuscript_unit_ref
        or artifact.respondent != response.respondent
        or tuple((item.probe_id, item.kind) for item in artifact.answers) != expected
        or tuple(item.probe_id for item in artifact.answers)
        != response.answered_probe_ids
    ):
        raise Phase3ArtifactError(
            "reader-response bytes disagree with ReaderResponse/probe lineage"
        )
    return artifact


def _validate_cold_review(
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    review: a.ReviewRecord,
) -> None:
    if review.role != "cold_reader":
        return
    assert review.reader_response_ref is not None
    response = _resolve_payload(
        payloads, review.reader_response_ref, a.ReaderResponse, "cold response"
    )
    assert isinstance(response, a.ReaderResponse)
    probe = _resolve_payload(
        payloads, response.probe_set_ref, a.ReaderProbeSet, "cold probe set"
    )
    assert isinstance(probe, a.ReaderProbeSet)
    _, key = _reader_artifacts(layout, registrations, probe)
    response_bytes = _response_artifact(
        layout, registrations, response, probe
    )
    assessment = review.assessment
    if not isinstance(assessment, a.ColdReaderAssessment):
        raise Phase3ArtifactError("cold review lacks a typed assessment")
    expected = tuple(
        (
            answer.probe_id,
            answer.kind,
            answer.response_hash,
            criterion.criterion_hash,
        )
        for answer, criterion in zip(response_bytes.answers, key.criteria)
    )
    actual = tuple(
        (
            item.probe_id,
            item.kind,
            item.response_excerpt_hash,
            item.answer_key_criterion_hash,
        )
        for item in assessment.probe_results
    )
    if actual != expected:
        raise Phase3ArtifactError(
            "cold-reader scoring hashes do not bind the exact response and answer key"
        )


def validate_phase3_operational_artifacts(
    layout: StoreLayout,
    base_snapshot: Snapshot | None,
    transaction: Transaction,
) -> None:
    """Validate immutable bytes for one Phase 3 authoring transaction."""

    if transaction.route_id not in _BYTE_CHECKED_ROUTES:
        return
    if base_snapshot is None:
        raise Phase3ArtifactError("Phase 3 authoring cannot run at genesis")
    payloads = _payload_index(base_snapshot, transaction)
    registrations = _artifact_index(base_snapshot, transaction)
    produced = {
        _ref(entity): payloads.get((entity.entity_id, entity.version))
        for entity in _produced_entities(transaction)
    }

    if transaction.route_id == "verify.independent_rederivation":
        records = [
            (reference, item)
            for reference, item in produced.items()
            if isinstance(item, a.ReDerivationRecord)
        ]
        if len(records) != 1:
            raise Phase3ArtifactError(
                "blind verification must produce one ReDerivationRecord"
            )
        record_ref, record = records[0]
        transcript = _parse_artifact(
            _read_artifact(layout, registrations, record.derivation_artifact_ref),
            ReDerivationTranscript,
            "independent re-derivation transcript",
        )
        expected = ReDerivationTranscript(
            record_ref=record_ref,
            package_ref=record.package_ref,
            claim_graph_ref=record.claim_graph_ref,
            claim_id=record.claim_id,
            obligation_ref=record.obligation_ref,
            formal_model_ref=record.formal_model_ref,
            assumption_map_ref=record.assumption_map_ref,
            rederiver=record.rederiver,
            steps=record.derivation_steps,
            derived_conclusion=record.derived_conclusion,
            comparison_to_claim=record.comparison_to_claim,
            outcome=record.outcome,
            limitations=record.limitations,
        )
        if transcript != expected:
            raise Phase3ArtifactError(
                "re-derivation transcript bytes disagree with the canonical record"
            )
        return

    if transaction.route_id == "audit.argument_assurance":
        bundles = [
            (reference, item)
            for reference, item in produced.items()
            if isinstance(item, a.AssuranceBundle)
        ]
        if len(bundles) != 1:
            raise Phase3ArtifactError("assurance audit must produce one AssuranceBundle")
        bundle_ref, bundle = bundles[0]
        for audit in bundle.proof_audits:
            report = _parse_artifact(
                _read_artifact(layout, registrations, audit.audit_report_ref),
                ProofAuditReportArtifact,
                "proof-audit report",
            )
            expected = ProofAuditReportArtifact(
                assurance_bundle_ref=bundle_ref,
                audit_id=audit.audit_id,
                claim_graph_ref=audit.claim_graph_ref,
                claim_id=audit.claim_id,
                obligation_ref=audit.obligation_ref,
                formal_model_ref=audit.formal_model_ref,
                assumption_map_ref=audit.assumption_map_ref,
                proof_artifact_ref=audit.proof_artifact_ref,
                verification_record_ref=audit.verification_record_ref,
                rederivation_ref=audit.rederivation_ref,
                originating_verifier=audit.originating_verifier,
                auditor=audit.auditor,
                outcome=audit.outcome,
                comparison_outcome=audit.comparison_outcome,
                findings=audit.findings,
                limitations=audit.limitations,
            )
            if report != expected:
                raise Phase3ArtifactError(
                    "proof-audit report bytes disagree with its exact audit record"
                )
        return

    if transaction.route_id in {
        "compose.manuscript_unit",
        "compose.profiled_manuscript_unit",
    }:
        units = [item for item in produced.values() if isinstance(item, a.ManuscriptUnit)]
        if len(units) != 1:
            raise Phase3ArtifactError("compose must produce one exact ManuscriptUnit")
        _validate_manuscript(layout, registrations, units[0])
        _validate_writer_binding(layout, transaction, units[0])
        return

    if transaction.route_id == "prepare.reader_probe":
        probes = [item for item in produced.values() if isinstance(item, a.ReaderProbeSet)]
        if len(probes) != 1:
            raise Phase3ArtifactError("probe preparation must produce one ReaderProbeSet")
        _reader_artifacts(layout, registrations, probes[0])
        return

    if transaction.route_id == "answer.reader_probe":
        responses = [item for item in produced.values() if isinstance(item, a.ReaderResponse)]
        if len(responses) != 1:
            raise Phase3ArtifactError("reader answer must produce one ReaderResponse")
        response = responses[0]
        probe = _resolve_payload(
            payloads, response.probe_set_ref, a.ReaderProbeSet, "response probe set"
        )
        assert isinstance(probe, a.ReaderProbeSet)
        _reader_artifacts(layout, registrations, probe)
        _response_artifact(layout, registrations, response, probe)
        return

    if transaction.route_id in {
        "review.manuscript_unit",
        "adjudicate.reader_probe",
        "close.manuscript_review",
    }:
        reviews: list[a.ReviewRecord] = []
        if transaction.route_id == "close.manuscript_review":
            closures = [
                item for item in produced.values() if isinstance(item, a.ReviewClosure)
            ]
            if len(closures) != 1:
                raise Phase3ArtifactError("closure must produce one ReviewClosure")
            closure = closures[0]
            unit = _resolve_payload(
                payloads, closure.manuscript_unit_ref, a.ManuscriptUnit, "closure manuscript"
            )
            assert isinstance(unit, a.ManuscriptUnit)
            _validate_manuscript(layout, registrations, unit)
            for reference in (
                closure.formal_fidelity_review_ref,
                closure.economic_reader_review_ref,
                closure.cold_reader_review_ref,
            ):
                value = _resolve_payload(
                    payloads, reference, a.ReviewRecord, "closure review"
                )
                assert isinstance(value, a.ReviewRecord)
                reviews.append(value)
        else:
            reviews = [
                item for item in produced.values() if isinstance(item, a.ReviewRecord)
            ]
            if len(reviews) != 1:
                raise Phase3ArtifactError("review route must produce one ReviewRecord")
            unit = _resolve_payload(
                payloads,
                reviews[0].manuscript_unit_ref,
                a.ManuscriptUnit,
                "review manuscript",
            )
            assert isinstance(unit, a.ManuscriptUnit)
            _validate_manuscript(layout, registrations, unit)
        for review in reviews:
            _validate_cold_review(layout, registrations, payloads, review)


__all__ = [
    "Phase3ArtifactError",
    "validate_phase3_operational_artifacts",
]
