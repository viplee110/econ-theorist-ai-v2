"""Canonical byte protocols for Phase 3 reader evaluation artifacts.

The entity payloads intentionally expose only public descriptors and exact
artifact references.  These strict artifact schemas bind those descriptors to
the actual prompt, answer-key, and response bytes consumed by isolated roles.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .authoring import (
    READER_PROBE_KIND_ORDER,
    DerivationStep,
    ProofAuditFinding,
    ReaderProbeKind,
)
from .codec import sha256_digest
from .models import (
    Actor,
    ArtifactDependencyRef,
    Digest,
    EntityVersionRef,
    NonEmptyString,
    StableId,
    StrictModel,
)


def _unique(values: tuple[str, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _text_hash(value: str) -> str:
    return sha256_digest(value.encode("utf-8"))


class ReaderProbePrompt(StrictModel):
    probe_id: StableId
    kind: ReaderProbeKind
    prompt: NonEmptyString
    prompt_hash: Digest
    target_assertion_ids: tuple[StableId, ...] = ()
    target_contract_ids: tuple[StableId, ...] = ()

    @model_validator(mode="after")
    def _prompt_is_exact_and_targeted(self) -> "ReaderProbePrompt":
        _unique(self.target_assertion_ids, "probe assertion targets")
        _unique(self.target_contract_ids, "probe contract targets")
        if not self.target_assertion_ids and not self.target_contract_ids:
            raise ValueError("a reader probe requires an exact assertion or contract target")
        if self.prompt_hash != _text_hash(self.prompt):
            raise ValueError("reader-probe prompt hash does not match its exact text")
        return self


class ReaderProbeArtifact(StrictModel):
    protocol: Literal["reader_probe_artifact.v1"] = "reader_probe_artifact.v1"
    assignment_ref: EntityVersionRef
    manuscript_unit_ref: EntityVersionRef
    frozen_manuscript_artifact_ref: ArtifactDependencyRef
    respondent: Actor
    transfer_objective: NonEmptyString
    probes: Annotated[tuple[ReaderProbePrompt, ...], Field(min_length=5, max_length=5)]

    @model_validator(mode="after")
    def _five_probes_are_exact(self) -> "ReaderProbeArtifact":
        _unique(tuple(item.probe_id for item in self.probes), "reader-probe IDs")
        if tuple(item.kind for item in self.probes) != READER_PROBE_KIND_ORDER:
            raise ValueError("reader-probe artifact must contain the five canonical probes in order")
        return self


class ReaderAnswerCriterion(StrictModel):
    probe_id: StableId
    kind: ReaderProbeKind
    criterion: NonEmptyString
    criterion_hash: Digest
    required_content: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    failure_signals: tuple[NonEmptyString, ...] = ()

    @model_validator(mode="after")
    def _criterion_is_exact(self) -> "ReaderAnswerCriterion":
        _unique(self.required_content, "answer-key required content")
        _unique(self.failure_signals, "answer-key failure signals")
        if self.criterion_hash != _text_hash(self.criterion):
            raise ValueError("answer-key criterion hash does not match its exact text")
        return self


class ReaderAnswerKeyArtifact(StrictModel):
    protocol: Literal["reader_answer_key_artifact.v1"] = (
        "reader_answer_key_artifact.v1"
    )
    assignment_ref: EntityVersionRef
    manuscript_unit_ref: EntityVersionRef
    frozen_manuscript_artifact_ref: ArtifactDependencyRef
    adjudicator: Actor
    criteria: Annotated[
        tuple[ReaderAnswerCriterion, ...], Field(min_length=5, max_length=5)
    ]

    @model_validator(mode="after")
    def _five_criteria_are_exact(self) -> "ReaderAnswerKeyArtifact":
        _unique(tuple(item.probe_id for item in self.criteria), "answer-key probe IDs")
        if tuple(item.kind for item in self.criteria) != READER_PROBE_KIND_ORDER:
            raise ValueError("answer key must cover the five canonical probes in order")
        return self


class ReaderAnswer(StrictModel):
    probe_id: StableId
    kind: ReaderProbeKind
    response: NonEmptyString
    response_hash: Digest

    @model_validator(mode="after")
    def _response_is_exact(self) -> "ReaderAnswer":
        if self.response_hash != _text_hash(self.response):
            raise ValueError("reader-response hash does not match its exact text")
        return self


class ReaderResponseArtifact(StrictModel):
    protocol: Literal["reader_response_artifact.v1"] = "reader_response_artifact.v1"
    probe_set_ref: EntityVersionRef
    manuscript_unit_ref: EntityVersionRef
    respondent: Actor
    answers: Annotated[tuple[ReaderAnswer, ...], Field(min_length=5, max_length=5)]

    @model_validator(mode="after")
    def _five_answers_are_exact(self) -> "ReaderResponseArtifact":
        _unique(tuple(item.probe_id for item in self.answers), "reader-response probe IDs")
        if tuple(item.kind for item in self.answers) != READER_PROBE_KIND_ORDER:
            raise ValueError("reader response must answer the five canonical probes in order")
        return self


class ReDerivationTranscript(StrictModel):
    protocol: Literal["independent_rederivation_transcript.v1"] = (
        "independent_rederivation_transcript.v1"
    )
    record_ref: EntityVersionRef
    package_ref: EntityVersionRef
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    obligation_ref: EntityVersionRef
    formal_model_ref: EntityVersionRef
    assumption_map_ref: EntityVersionRef
    rederiver: Actor
    steps: Annotated[tuple[DerivationStep, ...], Field(min_length=1)]
    derived_conclusion: NonEmptyString
    comparison_to_claim: Literal[
        "equivalent", "gap", "contradicts", "inconclusive"
    ]
    outcome: Literal["agrees", "gap_found", "falsified", "inconclusive"]
    limitations: NonEmptyString


class ProofAuditReportArtifact(StrictModel):
    protocol: Literal["proof_audit_report.v1"] = "proof_audit_report.v1"
    assurance_bundle_ref: EntityVersionRef
    audit_id: StableId
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    obligation_ref: EntityVersionRef
    formal_model_ref: EntityVersionRef
    assumption_map_ref: EntityVersionRef
    proof_artifact_ref: ArtifactDependencyRef
    verification_record_ref: EntityVersionRef
    rederivation_ref: EntityVersionRef
    originating_verifier: Actor
    auditor: Actor
    outcome: Literal["passed", "gap_found", "falsified", "inconclusive"]
    comparison_outcome: Literal[
        "agrees", "gap_found", "falsified", "inconclusive"
    ]
    findings: tuple[ProofAuditFinding, ...] = ()
    limitations: NonEmptyString


__all__ = [
    "ReaderAnswer",
    "ReaderAnswerCriterion",
    "ReaderAnswerKeyArtifact",
    "ReaderProbeArtifact",
    "ReaderProbePrompt",
    "ReaderResponseArtifact",
    "ReDerivationTranscript",
    "ProofAuditReportArtifact",
]
