"""Strict Phase 3 assurance and authoring payload contracts.

The Phase 1 :class:`~econ_theorist.models.EntityVersion` envelope remains the
canonical storage object and the Phase 2 theory registry remains frozen.  This
module owns a separate ``econ_theorist.authoring`` namespace for thin
assurance, projection, manuscript, review, and human-effort records.

These models establish admissible structure and exact provenance.  They do
not certify mathematical truth, economic importance, publication quality,
human acceptance, or freshness.
"""

from __future__ import annotations

from collections import deque
from math import gcd
from types import MappingProxyType
from typing import Annotated, Literal, Mapping, TypeAlias

from pydantic import Field, field_validator, model_validator

from .codec import canonical_json_bytes
from .models import (
    Actor,
    ArtifactDependencyRef,
    DecisionVersionRef,
    Digest,
    EntityVersion,
    EntityVersionRef,
    Facet,
    FacetPayloads,
    NonEmptyString,
    SemanticFacetRef,
    StableId,
    StrictModel,
)
from .theory import ExactEvidenceRef, ResultArchetype


PositiveInt: TypeAlias = Annotated[int, Field(ge=1)]
NonNegativeInt: TypeAlias = Annotated[int, Field(ge=0)]
ExplanatoryText: TypeAlias = Annotated[str, Field(min_length=32)]
MechanismStepText: TypeAlias = Annotated[str, Field(min_length=24)]


def _actor_key(actor: Actor) -> tuple[str, str]:
    return actor.kind, actor.actor_id


def _ref_key(reference: object) -> tuple[object, ...]:
    if isinstance(reference, EntityVersionRef):
        return ("entity", reference.entity_id, reference.version)
    if isinstance(reference, ArtifactDependencyRef):
        return (
            "artifact",
            reference.artifact_id,
            reference.version,
            reference.content_hash,
        )
    if isinstance(reference, DecisionVersionRef):
        return ("decision", reference.decision_id, reference.version)
    if isinstance(reference, SemanticFacetRef):
        return (
            "semantic_facet",
            reference.entity_id,
            reference.version,
            reference.facet,
            reference.field_path,
            reference.semantic_hash,
        )
    raise TypeError(f"unsupported exact reference: {type(reference).__name__}")


def _unique(values: tuple[object, ...], keys: tuple[object, ...], label: str) -> None:
    if len(values) != len(set(keys)):
        raise ValueError(f"{label} must be unique")


def _unique_ids(values: tuple[object, ...], field: str, label: str) -> None:
    _unique(values, tuple(getattr(item, field) for item in values), label)


def _unique_refs(values: tuple[object, ...], label: str) -> None:
    _unique(values, tuple(_ref_key(item) for item in values), label)


class AuthoringPayload(StrictModel):
    """Base for every payload registered in the Phase 3 namespace."""

    schema_version: Literal[1] = 1


# ---------------------------------------------------------------------------
# Formal assurance


class RunProvenanceBinding(StrictModel):
    route_run_id: StableId
    route_run_hash: Digest
    context_manifest_hash: Digest
    compiled_context_hash: Digest


class DerivationStep(StrictModel):
    step_id: StableId
    statement: NonEmptyString
    justification: NonEmptyString
    dependency_step_ids: tuple[StableId, ...] = ()
    source_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]

    @field_validator("dependency_step_ids")
    @classmethod
    def _dependencies_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "derivation-step dependencies")
        return value

    @field_validator("source_refs")
    @classmethod
    def _sources_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "derivation-step sources")
        return value


class ReDerivationRecord(AuthoringPayload):
    """One blind re-derivation bound to exact scientific revisions."""

    package_ref: EntityVersionRef
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    obligation_ref: EntityVersionRef
    formal_model_ref: EntityVersionRef
    assumption_map_ref: EntityVersionRef
    verification_record_ref: EntityVersionRef
    originating_verifier: Actor
    originating_verifier_run: RunProvenanceBinding
    proof_author: Actor
    proof_author_output_ref: EntityVersionRef
    proof_author_run: RunProvenanceBinding
    rederiver: Actor
    route_run_id: StableId
    route_run_hash: Digest
    parent_runs: tuple[RunProvenanceBinding, ...] = ()
    derivation_artifact_ref: ArtifactDependencyRef
    derivation_steps: Annotated[tuple[DerivationStep, ...], Field(min_length=1)]
    derived_conclusion: NonEmptyString
    comparison_to_claim: Literal[
        "equivalent", "gap", "contradicts", "inconclusive"
    ]
    context_manifest_hash: Digest
    compiled_context_hash: Digest
    excluded_proof_artifact_refs: Annotated[
        tuple[ArtifactDependencyRef, ...], Field(min_length=1)
    ]
    outcome: Literal["agrees", "gap_found", "falsified", "inconclusive"]
    limitations: NonEmptyString
    performed_at: NonEmptyString

    @field_validator("excluded_proof_artifact_refs")
    @classmethod
    def _excluded_proofs_are_unique(
        cls, value: tuple[ArtifactDependencyRef, ...]
    ) -> tuple[ArtifactDependencyRef, ...]:
        _unique_refs(value, "excluded proof artifact refs")
        return value

    @model_validator(mode="after")
    def _rederivation_is_independent(self) -> "ReDerivationRecord":
        excluded_actors = {
            _actor_key(self.originating_verifier),
            _actor_key(self.proof_author),
        }
        if _actor_key(self.rederiver) in excluded_actors:
            raise ValueError(
                "re-deriver must be independent of the verifier and proof author"
            )
        if self.rederiver.kind == "deterministic_tool":
            raise ValueError("an independent re-derivation requires a human or agent")
        parent_ids = tuple(item.route_run_id for item in self.parent_runs)
        parent_hashes = tuple(item.route_run_hash for item in self.parent_runs)
        _unique(self.parent_runs, parent_ids, "re-derivation parent run IDs")
        _unique(self.parent_runs, parent_hashes, "re-derivation parent run hashes")
        if self.route_run_id in parent_ids:
            raise ValueError("a re-derivation run cannot be its own parent")
        run_hashes = (
            self.route_run_hash,
            self.originating_verifier_run.route_run_hash,
            self.proof_author_run.route_run_hash,
        )
        _unique(run_hashes, run_hashes, "re-derivation role run hashes")
        contexts = (
            self.context_manifest_hash,
            self.originating_verifier_run.context_manifest_hash,
            self.proof_author_run.context_manifest_hash,
        )
        _unique(contexts, contexts, "re-derivation role context hashes")
        if self.originating_verifier_run.route_run_id in parent_ids:
            raise ValueError("a blind derivation cannot inherit the verifier run")
        _unique_ids(self.derivation_steps, "step_id", "derivation-step IDs")
        prior: set[str] = set()
        for step in self.derivation_steps:
            if not set(step.dependency_step_ids).issubset(prior):
                raise ValueError(
                    "derivation steps may depend only on earlier sealed steps"
                )
            prior.add(step.step_id)
        required_sources = {
            self.claim_graph_ref,
            self.obligation_ref,
            self.formal_model_ref,
            self.assumption_map_ref,
        }
        cited_sources = {
            reference
            for step in self.derivation_steps
            for reference in step.source_refs
            if isinstance(reference, EntityVersionRef)
        }
        if not required_sources.issubset(cited_sources):
            raise ValueError(
                "blind derivation steps must cite every exact formal input"
            )
        expected_comparison = {
            "agrees": "equivalent",
            "gap_found": "gap",
            "falsified": "contradicts",
            "inconclusive": "inconclusive",
        }[self.outcome]
        if self.comparison_to_claim != expected_comparison:
            raise ValueError(
                "blind derivation outcome disagrees with its conclusion comparison"
            )
        return self


class ProofAuditFinding(StrictModel):
    finding_id: StableId
    kind: Literal[
        "hidden_assumption",
        "direction_error",
        "missing_existence",
        "missing_uniqueness",
        "quantifier_gap",
        "domain_gap",
        "boundary_gap",
        "unsupported_step",
        "notation_mismatch",
        "other",
    ]
    severity: Literal["info", "warning", "error", "critical"]
    summary: NonEmptyString
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_is_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "proof-audit finding evidence")
        return value


class ProofAudit(StrictModel):
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
    audit_report_ref: ArtifactDependencyRef
    outcome: Literal["passed", "gap_found", "falsified", "inconclusive"]
    comparison_outcome: Literal["agrees", "gap_found", "falsified", "inconclusive"]
    findings: tuple[ProofAuditFinding, ...] = ()
    limitations: NonEmptyString
    audited_at: NonEmptyString

    @field_validator("findings")
    @classmethod
    def _finding_ids_are_unique(
        cls, value: tuple[ProofAuditFinding, ...]
    ) -> tuple[ProofAuditFinding, ...]:
        _unique_ids(value, "finding_id", "proof-audit finding IDs")
        return value

    @model_validator(mode="after")
    def _audit_is_independent_and_coherent(self) -> "ProofAudit":
        if _actor_key(self.originating_verifier) == _actor_key(self.auditor):
            raise ValueError("proof auditor must be independent of the verifier")
        if self.auditor.kind == "deterministic_tool":
            raise ValueError("proof audit requires a human or agent auditor")
        if self.outcome == "passed" and any(
            item.severity in {"error", "critical"} for item in self.findings
        ):
            raise ValueError("a passed proof audit cannot retain an error finding")
        structural_kinds = {
            "hidden_assumption",
            "direction_error",
            "missing_existence",
            "missing_uniqueness",
            "quantifier_gap",
            "domain_gap",
            "boundary_gap",
            "unsupported_step",
        }
        if self.outcome == "passed" and any(
            item.kind in structural_kinds for item in self.findings
        ):
            raise ValueError("a passed proof audit cannot retain a structural gap")
        if (self.outcome == "passed") != (self.comparison_outcome == "agrees"):
            raise ValueError(
                "proof-audit outcome must agree with the sealed re-derivation comparison"
            )
        if self.outcome != "passed" and not self.findings:
            raise ValueError("a non-passing proof audit requires a precise finding")
        return self


class ExactRationalValue(StrictModel):
    numerator: int
    denominator: PositiveInt

    @model_validator(mode="after")
    def _fraction_is_canonical(self) -> "ExactRationalValue":
        if self.numerator == 0 and self.denominator != 1:
            raise ValueError("zero rational values require denominator one")
        if gcd(abs(self.numerator), self.denominator) != 1:
            raise ValueError("exact rational values must be reduced")
        return self


class PolynomialPowerSpec(StrictModel):
    variable: StableId
    power: PositiveInt


class ExactPolynomialTermSpec(StrictModel):
    coefficient: ExactRationalValue
    powers: tuple[PolynomialPowerSpec, ...] = ()

    @model_validator(mode="after")
    def _term_is_nonzero_and_canonical(self) -> "ExactPolynomialTermSpec":
        if self.coefficient.numerator == 0:
            raise ValueError("zero polynomial terms must be omitted")
        variables = tuple(item.variable for item in self.powers)
        _unique(self.powers, variables, "polynomial variables")
        if variables != tuple(sorted(variables)):
            raise ValueError("polynomial variables must be canonically ordered")
        return self


class ExactPolynomialSpec(StrictModel):
    terms: tuple[ExactPolynomialTermSpec, ...] = ()

    @model_validator(mode="after")
    def _monomials_are_unique_and_ordered(self) -> "ExactPolynomialSpec":
        monomials = tuple(
            tuple((item.variable, item.power) for item in term.powers)
            for term in self.terms
        )
        _unique(self.terms, monomials, "polynomial monomials")
        if monomials != tuple(sorted(monomials)):
            raise ValueError("polynomial monomials must be canonically ordered")
        return self


class ExactAssignmentValue(StrictModel):
    variable: StableId
    value: ExactRationalValue


class ExactAssignmentSpec(StrictModel):
    case_id: StableId
    values: Annotated[tuple[ExactAssignmentValue, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _assignment_is_canonical(self) -> "ExactAssignmentSpec":
        variables = tuple(item.variable for item in self.values)
        _unique(self.values, variables, "assignment variables")
        if variables != tuple(sorted(variables)):
            raise ValueError("assignment variables must be canonically ordered")
        return self


class PolynomialRelationPredicate(StrictModel):
    left: ExactPolynomialSpec
    relation: Literal["eq", "le", "lt", "ge", "gt"]
    right: ExactPolynomialSpec


class SymbolicIdentityEvidence(StrictModel):
    protocol: Literal["exact_polynomial_identity.v1"] = "exact_polynomial_identity.v1"
    left: ExactPolynomialSpec
    right: ExactPolynomialSpec
    input_hash: Digest
    output_hash: Digest
    left_hash: Digest
    right_hash: Digest
    difference_hash: Digest
    outcome: Literal["identity_verified", "identity_failed"]
    certificate_hash: Digest


class CounterexampleScanEvidence(StrictModel):
    protocol: Literal["exact_polynomial_relation_scan.v1"] = (
        "exact_polynomial_relation_scan.v1"
    )
    predicate: PolynomialRelationPredicate
    cases: Annotated[tuple[ExactAssignmentSpec, ...], Field(min_length=1)]
    code_hash: Digest
    input_hash: Digest
    output_hash: Digest
    domain_hash: Digest
    relation_hash: Digest
    checked_count: PositiveInt
    outcome: Literal["falsified", "no_counterexample_found"]
    witness_case_id: StableId | None = None
    witness_hash: Digest | None = None
    receipt_hash: Digest
    evidentiary_limit: Literal[
        "No witness in a finite exact domain is corroboration, not proof of a universal claim."
    ] = "No witness in a finite exact domain is corroboration, not proof of a universal claim."

    @model_validator(mode="after")
    def _scan_result_has_a_coherent_witness(self) -> "CounterexampleScanEvidence":
        _unique_ids(self.cases, "case_id", "counterexample case IDs")
        if self.outcome == "falsified" and self.witness_case_id is None:
            raise ValueError("a falsified scan requires its witness case ID")
        if self.outcome == "falsified" and self.witness_hash is None:
            raise ValueError("a falsified scan requires its witness hash")
        if self.outcome == "no_counterexample_found" and self.witness_case_id is not None:
            raise ValueError("a passing finite scan cannot carry a witness")
        if self.outcome == "no_counterexample_found" and self.witness_hash is not None:
            raise ValueError("a passing finite scan cannot carry a witness hash")
        if self.witness_case_id is not None and self.witness_case_id not in {
            item.case_id for item in self.cases
        }:
            raise ValueError("counterexample witness is outside the exact domain")
        return self


ReproducibleHarnessEvidence: TypeAlias = Annotated[
    SymbolicIdentityEvidence | CounterexampleScanEvidence,
    Field(discriminator="protocol"),
]


class ToolHarnessReceipt(StrictModel):
    receipt_id: StableId
    harness_kind: Literal[
        "symbolic_identity", "counterexample_search", "finite_grid"
    ]
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    obligation_ref: EntityVersionRef
    tool_name: NonEmptyString
    tool_version: NonEmptyString
    code_ref: ArtifactDependencyRef
    input_ref: ArtifactDependencyRef
    output_ref: ArtifactDependencyRef
    receipt_ref: ArtifactDependencyRef | None = None
    domain: NonEmptyString
    seed: NonNegativeInt | None = None
    witness_ref: ArtifactDependencyRef | None = None
    certificate_ref: ArtifactDependencyRef | None = None
    reproducible_evidence: ReproducibleHarnessEvidence | None = None
    outcome: Literal[
        "identity_verified",
        "witness_found",
        "no_counterexample_found",
        "failed",
        "inconclusive",
    ]
    evidentiary_role: Literal[
        "exact_identity_certificate",
        "corroboration_only",
        "falsification",
        "diagnostic",
    ]
    limitations: NonEmptyString
    executed_at: NonEmptyString

    @model_validator(mode="after")
    def _evidentiary_role_is_bounded(self) -> "ToolHarnessReceipt":
        if self.seed is not None:
            raise ValueError("the built-in exact harnesses are deterministic and unseeded")
        if self.outcome == "witness_found" and self.witness_ref is None:
            raise ValueError("a found witness requires its exact artifact")
        if self.evidentiary_role == "falsification" and (
            self.outcome != "witness_found" or self.witness_ref is None
        ):
            raise ValueError("falsification requires an exact found witness")
        if self.outcome == "no_counterexample_found" and self.evidentiary_role not in {
            "corroboration_only",
            "diagnostic",
        }:
            raise ValueError("failure to find a counterexample cannot discharge a claim")
        if self.harness_kind == "finite_grid" and (
            self.evidentiary_role == "exact_identity_certificate"
            or self.outcome == "identity_verified"
        ):
            raise ValueError("finite or simulated evidence cannot prove a universal identity")
        if self.evidentiary_role == "exact_identity_certificate" and (
            self.harness_kind != "symbolic_identity"
            or self.outcome != "identity_verified"
            or self.certificate_ref is None
        ):
            raise ValueError(
                "an exact identity certificate requires a verified symbolic receipt"
            )
        if self.harness_kind == "symbolic_identity" and not isinstance(
            self.reproducible_evidence, SymbolicIdentityEvidence
        ):
            raise ValueError("symbolic identity receipts require canonical evidence")
        if self.harness_kind == "symbolic_identity" and self.receipt_ref is not None:
            raise ValueError("symbolic identity runs use a certificate, not a receipt")
        if self.harness_kind in {"counterexample_search", "finite_grid"} and not isinstance(
            self.reproducible_evidence, CounterexampleScanEvidence
        ):
            raise ValueError("finite exact checks require canonical scan evidence")
        if self.harness_kind in {"counterexample_search", "finite_grid"} and (
            self.receipt_ref is None or self.certificate_ref is not None
        ):
            raise ValueError("finite exact checks require a receipt and no certificate")
        return self


class HarnessNonApplicabilityRecord(StrictModel):
    record_id: StableId
    family: Literal["symbolic_identity", "counterexample_search"]
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    obligation_ref: EntityVersionRef
    reason_code: Literal[
        "no_algebraic_identity",
        "no_finite_domain",
        "check_not_informative",
        "covered_by_stronger_exact_argument",
    ]
    explanation: ExplanatoryText
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    determined_by: Actor

    @field_validator("evidence_refs")
    @classmethod
    def _nonapplicability_evidence_is_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "harness non-applicability evidence")
        return value

    @model_validator(mode="after")
    def _reason_matches_the_check_family(self) -> "HarnessNonApplicabilityRecord":
        if (
            self.reason_code == "no_algebraic_identity"
            and self.family != "symbolic_identity"
        ):
            raise ValueError("no_algebraic_identity applies only to symbolic checks")
        if (
            self.reason_code == "no_finite_domain"
            and self.family != "counterexample_search"
        ):
            raise ValueError("no_finite_domain applies only to finite searches")
        return self


class AssuranceIssue(StrictModel):
    issue_id: StableId
    severity: Literal["info", "warning", "error", "critical"]
    summary: NonEmptyString
    affected_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    blocking: bool

    @field_validator("affected_refs")
    @classmethod
    def _affected_refs_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "assurance issue affected refs")
        return value

    @model_validator(mode="after")
    def _critical_issue_blocks(self) -> "AssuranceIssue":
        if self.severity == "critical" and not self.blocking:
            raise ValueError("a critical assurance issue must be blocking")
        return self


class AssuranceBundle(AuthoringPayload):
    package_ref: EntityVersionRef
    g5_decision_ref: DecisionVersionRef
    claim_graph_ref: EntityVersionRef
    headline_claim_id: StableId
    formal_model_ref: EntityVersionRef
    assumption_map_ref: EntityVersionRef
    verification_bundle_ref: EntityVersionRef
    rederivation_refs: Annotated[tuple[EntityVersionRef, ...], Field(min_length=1)]
    proof_audits: Annotated[tuple[ProofAudit, ...], Field(min_length=1)]
    tool_receipts: tuple[ToolHarnessReceipt, ...] = ()
    tool_non_applicability: tuple[HarnessNonApplicabilityRecord, ...] = ()
    unresolved_issues: tuple[AssuranceIssue, ...] = ()
    assembled_by: Actor
    route_run_id: StableId
    route_run_hash: Digest
    context_manifest_hash: Digest
    compiled_context_hash: Digest
    assembled_at: NonEmptyString

    @field_validator("rederivation_refs")
    @classmethod
    def _rederivation_refs_are_unique(
        cls, value: tuple[EntityVersionRef, ...]
    ) -> tuple[EntityVersionRef, ...]:
        _unique_refs(value, "re-derivation refs")
        return value

    @field_validator("proof_audits")
    @classmethod
    def _audit_ids_are_unique(
        cls, value: tuple[ProofAudit, ...]
    ) -> tuple[ProofAudit, ...]:
        _unique_ids(value, "audit_id", "proof-audit IDs")
        return value

    @field_validator("tool_receipts")
    @classmethod
    def _receipt_ids_are_unique(
        cls, value: tuple[ToolHarnessReceipt, ...]
    ) -> tuple[ToolHarnessReceipt, ...]:
        _unique_ids(value, "receipt_id", "tool receipt IDs")
        return value

    @field_validator("tool_non_applicability")
    @classmethod
    def _nonapplicability_ids_are_unique(
        cls, value: tuple[HarnessNonApplicabilityRecord, ...]
    ) -> tuple[HarnessNonApplicabilityRecord, ...]:
        _unique_ids(value, "record_id", "harness non-applicability IDs")
        return value

    @field_validator("unresolved_issues")
    @classmethod
    def _issue_ids_are_unique(
        cls, value: tuple[AssuranceIssue, ...]
    ) -> tuple[AssuranceIssue, ...]:
        _unique_ids(value, "issue_id", "assurance issue IDs")
        return value

    @model_validator(mode="after")
    def _bundle_covers_the_headline_without_self_certifying(self) -> "AssuranceBundle":
        receipt_keys = tuple(
            (item.harness_kind, item.obligation_ref) for item in self.tool_receipts
        )
        _unique(self.tool_receipts, receipt_keys, "harness family/obligation receipts")
        nonapplicability_keys = tuple(
            (item.family, item.obligation_ref)
            for item in self.tool_non_applicability
        )
        _unique(
            self.tool_non_applicability,
            nonapplicability_keys,
            "harness family/obligation non-applicability records",
        )
        if not any(
            item.claim_id == self.headline_claim_id for item in self.proof_audits
        ):
            raise ValueError("the headline claim requires an exact proof audit")
        if not any(
            item.claim_id == self.headline_claim_id for item in self.tool_receipts
        ):
            raise ValueError(
                "headline assurance requires at least one executed reproducible harness"
            )
        coverage = {
            (item.harness_kind, item.obligation_ref) for item in self.tool_receipts
        }
        nonapplicable = {
            (item.family, item.obligation_ref)
            for item in self.tool_non_applicability
        }
        if coverage.intersection(nonapplicable):
            raise ValueError("one harness check cannot be both executed and not applicable")
        headline_obligations = {
            item.obligation_ref
            for item in self.proof_audits
            if item.claim_id == self.headline_claim_id
        }
        for obligation_ref in headline_obligations:
            for family in ("symbolic_identity", "counterexample_search"):
                if (
                    (family, obligation_ref) not in coverage
                    and (family, obligation_ref) not in nonapplicable
                ):
                    raise ValueError(
                        "each headline obligation requires a harness receipt or typed non-applicability"
                    )
        return self


# ---------------------------------------------------------------------------
# Paper IR


class ResolvedProfileManifest(AuthoringPayload):
    """Minimal Phase 3 universal-floor projection, not a Phase 4 profile stack."""

    universal_floor_version: StableId
    theory_mode: NonEmptyString
    theory_mode_decision_ref: DecisionVersionRef
    ambition: NonEmptyString
    ambition_decision_ref: DecisionVersionRef
    primary_result_archetype: ResultArchetype
    result_archetype_source: SemanticFacetRef
    g4_decision_ref: DecisionVersionRef
    primary_audience: NonEmptyString
    audience_decision_ref: DecisionVersionRef
    source_state_revision: Digest
    profile_artifact_ref: ArtifactDependencyRef
    projection_hash: Digest
    resolved_at: NonEmptyString

    @model_validator(mode="after")
    def _profile_decisions_are_distinct(self) -> "ResolvedProfileManifest":
        refs = (
            self.theory_mode_decision_ref,
            self.ambition_decision_ref,
            self.g4_decision_ref,
            self.audience_decision_ref,
        )
        _unique_refs(refs, "minimal profile Decision refs")
        if self.result_archetype_source.field_path is None:
            raise ValueError("primary result archetype requires an exact source field")
        return self


class ClaimProjection(StrictModel):
    projection_id: StableId
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    formal_statement: NonEmptyString
    scope: NonEmptyString
    assumption_ids: tuple[StableId, ...]
    semantic_translation: NonEmptyString
    formal_statement_source: SemanticFacetRef
    scope_source: SemanticFacetRef
    assumption_source_refs: tuple[SemanticFacetRef, ...]
    translation_source: SemanticFacetRef
    allowed_wording_strength: Literal[
        "exact", "entailed_equivalent", "entailed_weaker"
    ]
    permitted_locations: Annotated[tuple[StableId, ...], Field(min_length=1)]
    prohibited_extensions: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]

    @field_validator("assumption_ids", "permitted_locations")
    @classmethod
    def _stable_id_sets_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "claim projection stable-ID list")
        return value

    @field_validator("assumption_source_refs")
    @classmethod
    def _assumption_sources_are_unique(
        cls, value: tuple[SemanticFacetRef, ...]
    ) -> tuple[SemanticFacetRef, ...]:
        _unique_refs(value, "assumption source refs")
        return value

    @model_validator(mode="after")
    def _sources_bind_the_exact_graph(self) -> "ClaimProjection":
        for source in (
            self.formal_statement_source,
            self.scope_source,
            self.translation_source,
            *self.assumption_source_refs,
        ):
            if (
                source.entity_id != self.claim_graph_ref.entity_id
                or source.version != self.claim_graph_ref.version
            ):
                raise ValueError("claim projection source does not bind its exact ClaimGraph")
            if source.field_path is None:
                raise ValueError("claim projection sources require exact JSON Pointers")
        return self


class EconomicOntologyEntry(StrictModel):
    object_id: StableId
    formal_symbol: NonEmptyString
    preferred_economic_name: NonEmptyString
    short_definition: NonEmptyString
    economic_interpretation: NonEmptyString
    mechanism_role: NonEmptyString
    allowed_aliases: tuple[NonEmptyString, ...] = ()
    forbidden_names: tuple[NonEmptyString, ...] = ()
    first_use_section_id: StableId

    @model_validator(mode="after")
    def _names_do_not_conflict(self) -> "EconomicOntologyEntry":
        _unique(self.allowed_aliases, self.allowed_aliases, "allowed aliases")
        _unique(self.forbidden_names, self.forbidden_names, "forbidden names")
        if self.preferred_economic_name in self.forbidden_names:
            raise ValueError("the preferred economic name cannot be forbidden")
        if set(self.allowed_aliases).intersection(self.forbidden_names):
            raise ValueError("an ontology name cannot be both allowed and forbidden")
        return self


class NarrativeSpine(StrictModel):
    phenomenon_or_question: NonEmptyString
    natural_benchmark: NonEmptyString
    unresolved_benchmark_delta: NonEmptyString
    new_economic_or_conceptual_object: NonEmptyString
    central_result: NonEmptyString
    why_not_immediate: NonEmptyString
    boundary_and_failure_conditions: NonEmptyString
    economic_consequence_or_changed_practice: NonEmptyString
    literature_update: NonEmptyString
    source_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]

    @field_validator("source_refs")
    @classmethod
    def _sources_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "narrative spine source refs")
        return value


class PaperIR(AuthoringPayload):
    compiler_mode: Literal["preview", "working", "submission"]
    package_ref: EntityVersionRef
    assurance_bundle_ref: EntityVersionRef | None = None
    g5_decision_ref: DecisionVersionRef | None = None
    manuscript_version_promotion_ref: DecisionVersionRef | None = None
    source_state_revision: Digest
    upstream_projection_hash: Digest
    language: NonEmptyString
    resolved_profile_manifest_ref: EntityVersionRef
    claim_projections: Annotated[tuple[ClaimProjection, ...], Field(min_length=1)]
    ontology: Annotated[tuple[EconomicOntologyEntry, ...], Field(min_length=1)]
    narrative_spine: NarrativeSpine
    canonical_writer: Actor
    preview_label: NonEmptyString | None = None
    built_at: NonEmptyString

    @field_validator("claim_projections")
    @classmethod
    def _claim_projections_are_unique(
        cls, value: tuple[ClaimProjection, ...]
    ) -> tuple[ClaimProjection, ...]:
        _unique_ids(value, "projection_id", "claim projection IDs")
        _unique(value, tuple(item.claim_id for item in value), "projected claim IDs")
        return value

    @field_validator("ontology")
    @classmethod
    def _ontology_is_unique(
        cls, value: tuple[EconomicOntologyEntry, ...]
    ) -> tuple[EconomicOntologyEntry, ...]:
        _unique_ids(value, "object_id", "ontology object IDs")
        _unique(
            value,
            tuple(item.formal_symbol for item in value),
            "ontology formal symbols",
        )
        return value

    @model_validator(mode="after")
    def _compiler_mode_has_exact_authority(self) -> "PaperIR":
        if self.canonical_writer.kind == "deterministic_tool":
            raise ValueError("the canonical writer must be a human or agent")
        if self.compiler_mode == "preview":
            if self.preview_label is None:
                raise ValueError("preview Paper IR requires a visible preview label")
            if self.manuscript_version_promotion_ref is not None:
                raise ValueError("preview Paper IR cannot carry manuscript promotion")
        else:
            if self.g5_decision_ref is None:
                raise ValueError("working/submission Paper IR requires the exact G5 Decision")
            if self.assurance_bundle_ref is None:
                raise ValueError(
                    "working/submission Paper IR requires an exact AssuranceBundle"
                )
            if self.preview_label is not None:
                raise ValueError("working/submission Paper IR cannot carry a preview label")
        if self.compiler_mode == "submission":
            if self.manuscript_version_promotion_ref is None:
                raise ValueError("submission Paper IR requires manuscript promotion")
        elif self.manuscript_version_promotion_ref is not None:
            raise ValueError("only submission Paper IR may carry manuscript promotion")
        return self


# ---------------------------------------------------------------------------
# Reader path


class ReaderKnowledgeItem(StrictModel):
    knowledge_id: StableId
    content: NonEmptyString
    origin: Literal["target_audience_background", "delivered_update"]
    producer_state_id: StableId | None = None

    @model_validator(mode="after")
    def _origin_is_explicit(self) -> "ReaderKnowledgeItem":
        if self.origin == "target_audience_background":
            if self.producer_state_id is not None:
                raise ValueError("background knowledge cannot have a producer state")
        elif self.producer_state_id is None:
            raise ValueError("a delivered update requires its producer state")
        return self


class ReaderBeliefState(StrictModel):
    state_id: StableId
    known_on_entry: tuple[StableId, ...]
    default_expectation: NonEmptyString
    live_question: NonEmptyString
    misconception_risks: tuple[NonEmptyString, ...] = ()
    update: NonEmptyString
    delivered_knowledge_ids: tuple[StableId, ...]
    support_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    transfer_objective: NonEmptyString
    unresolved_on_exit: NonEmptyString

    @field_validator("known_on_entry", "delivered_knowledge_ids")
    @classmethod
    def _knowledge_sets_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "reader-state knowledge IDs")
        return value

    @field_validator("support_refs")
    @classmethod
    def _support_refs_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "reader-state support refs")
        return value

    @model_validator(mode="after")
    def _state_does_not_redeliver_known_content(self) -> "ReaderBeliefState":
        if set(self.known_on_entry).intersection(self.delivered_knowledge_ids):
            raise ValueError("a reader state cannot deliver knowledge already assumed on entry")
        return self


class ReaderStateEdge(StrictModel):
    source_state_id: StableId
    target_state_id: StableId

    @model_validator(mode="after")
    def _edge_is_not_reflexive(self) -> "ReaderStateEdge":
        if self.source_state_id == self.target_state_id:
            raise ValueError("reader-state edges cannot be self-loops")
        return self


class SectionContract(StrictModel):
    section_id: StableId
    role: Literal[
        "introduction",
        "model_motivation",
        "model",
        "result_block",
        "extension",
        "conclusion",
        "appendix",
    ]
    entry_state_id: StableId
    exit_state_id: StableId
    central_question: NonEmptyString
    required_claim_projection_ids: tuple[StableId, ...]
    claims_introduced: tuple[StableId, ...]
    economic_object_ids_to_interpret: tuple[StableId, ...]
    reader_update_on_exit: NonEmptyString
    open_question_for_next_section: NonEmptyString
    reader_cost_constraint: NonEmptyString
    appendix_boundary: Literal["main_text", "appendix", "mixed"]
    forbidden_detours: tuple[NonEmptyString, ...] = ()

    @field_validator(
        "required_claim_projection_ids",
        "claims_introduced",
        "economic_object_ids_to_interpret",
    )
    @classmethod
    def _section_id_sets_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "section-contract ID list")
        return value

    @model_validator(mode="after")
    def _section_advances_reader_state(self) -> "SectionContract":
        if self.entry_state_id == self.exit_state_id:
            raise ValueError("a section must advance the reader to a distinct state")
        return self


class ReaderPath(AuthoringPayload):
    paper_ir_ref: EntityVersionRef
    knowledge_items: Annotated[tuple[ReaderKnowledgeItem, ...], Field(min_length=1)]
    reader_states: Annotated[tuple[ReaderBeliefState, ...], Field(min_length=2)]
    state_edges: Annotated[tuple[ReaderStateEdge, ...], Field(min_length=1)]
    section_contracts: Annotated[tuple[SectionContract, ...], Field(min_length=1)]
    ordered_section_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    built_at: NonEmptyString

    @model_validator(mode="after")
    def _reader_path_is_a_closed_ordered_dag(self) -> "ReaderPath":
        _unique_ids(self.knowledge_items, "knowledge_id", "reader knowledge IDs")
        _unique_ids(self.reader_states, "state_id", "reader-state IDs")
        _unique(
            self.state_edges,
            tuple((item.source_state_id, item.target_state_id) for item in self.state_edges),
            "reader-state edges",
        )
        _unique_ids(self.section_contracts, "section_id", "section-contract IDs")
        _unique(self.ordered_section_ids, self.ordered_section_ids, "ordered section IDs")
        section_ids = {item.section_id for item in self.section_contracts}
        if set(self.ordered_section_ids) != section_ids:
            raise ValueError("ordered_section_ids must contain every and only section contract")

        states = {item.state_id: item for item in self.reader_states}
        incoming: dict[str, set[str]] = {item: set() for item in states}
        outgoing: dict[str, set[str]] = {item: set() for item in states}
        for edge in self.state_edges:
            if edge.source_state_id not in states or edge.target_state_id not in states:
                raise ValueError("reader-state edge references an unknown state")
            incoming[edge.target_state_id].add(edge.source_state_id)
            outgoing[edge.source_state_id].add(edge.target_state_id)
        queue = deque(sorted(item for item, values in incoming.items() if not values))
        topological: list[str] = []
        remaining = {item: set(values) for item, values in incoming.items()}
        while queue:
            item = queue.popleft()
            topological.append(item)
            for target in sorted(outgoing[item]):
                remaining[target].discard(item)
                if not remaining[target]:
                    queue.append(target)
        if len(topological) != len(states):
            raise ValueError("ReaderPath state graph must be acyclic")

        knowledge = {item.knowledge_id: item for item in self.knowledge_items}
        for state in self.reader_states:
            unknown = set((*state.known_on_entry, *state.delivered_knowledge_ids)).difference(
                knowledge
            )
            if unknown:
                raise ValueError("reader state references an unknown knowledge item")
            for knowledge_id in state.delivered_knowledge_ids:
                item = knowledge[knowledge_id]
                if (
                    item.origin != "delivered_update"
                    or item.producer_state_id != state.state_id
                ):
                    raise ValueError("delivered knowledge has the wrong producer state")

        background = {
            item.knowledge_id
            for item in self.knowledge_items
            if item.origin == "target_audience_background"
        }
        ancestors: dict[str, set[str]] = {item: set() for item in states}
        for state_id in topological:
            for parent in incoming[state_id]:
                ancestors[state_id].add(parent)
                ancestors[state_id].update(ancestors[parent])
            available = set(background)
            for predecessor in ancestors[state_id]:
                available.update(states[predecessor].delivered_knowledge_ids)
            if not set(states[state_id].known_on_entry).issubset(available):
                raise ValueError(
                    "reader state assumes knowledge not delivered by an ancestor or audience"
                )

        def reachable(source: str, target: str) -> bool:
            stack = [source]
            visited: set[str] = set()
            while stack:
                node = stack.pop()
                if node == target:
                    return True
                if node in visited:
                    continue
                visited.add(node)
                stack.extend(outgoing[node])
            return False

        for section in self.section_contracts:
            if section.entry_state_id not in states or section.exit_state_id not in states:
                raise ValueError("section contract references an unknown reader state")
            if not reachable(section.entry_state_id, section.exit_state_id):
                raise ValueError("section exit state is not downstream of its entry state")
        return self


# ---------------------------------------------------------------------------
# Result, assumption, and proof-roadmap contracts


class LayerContract(StrictModel):
    applicability: Literal["applicable", "not_applicable"]
    content: NonEmptyString | None = None
    source_refs: tuple[ExactEvidenceRef, ...] = ()
    not_applicable_reason: NonEmptyString | None = None

    @field_validator("source_refs")
    @classmethod
    def _layer_sources_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "layer source refs")
        return value

    @model_validator(mode="after")
    def _applicability_has_evidence_or_reason(self) -> "LayerContract":
        if self.applicability == "applicable":
            if self.content is None or not self.source_refs:
                raise ValueError("an applicable layer requires content and exact sources")
            if self.not_applicable_reason is not None:
                raise ValueError("an applicable layer cannot carry a non-applicability reason")
        else:
            if self.content is not None or self.source_refs:
                raise ValueError("a non-applicable layer cannot carry content or sources")
            if self.not_applicable_reason is None:
                raise ValueError("not_applicable requires a reason")
        return self


class ContractElement(StrictModel):
    content: NonEmptyString
    source_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]

    @field_validator("source_refs")
    @classmethod
    def _element_sources_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "contract element source refs")
        return value


class MechanismExplanationModule(StrictModel):
    archetype: Literal["mechanism_explanation"] = "mechanism_explanation"
    initiating_force: ContractElement
    affected_margin: ContractElement
    serious_rival: ContractElement
    separating_example: ContractElement
    ablation: ContractElement
    failure_case: ContractElement


class ComparativeStaticsThresholdModule(StrictModel):
    archetype: Literal["comparative_statics_threshold"] = "comparative_statics_threshold"
    perturbation: ContractElement
    competing_effects: ContractElement
    monotonicity_domain: ContractElement
    threshold_or_regime_logic: ContractElement
    reversal_or_boundary_witness: ContractElement


class CharacterizationBoundsModule(StrictModel):
    archetype: Literal["characterization_bounds"] = "characterization_bounds"
    object_characterized: ContractElement
    necessity_witness: ContractElement
    sufficiency_witness: ContractElement
    tightness_or_independence: ContractElement
    interpretation_of_conditions: ContractElement


class RobustnessInvarianceEquivalenceModule(StrictModel):
    archetype: Literal[
        "robustness_invariance_equivalence"
    ] = "robustness_invariance_equivalence"
    environments_mapped: ContractElement
    preserved_object_or_claim: ContractElement
    mapping: ContractElement
    economically_meaningful_variation: ContractElement
    failure_boundary: ContractElement


class DesignImplementationImpossibilityModule(StrictModel):
    archetype: Literal[
        "design_implementation_impossibility"
    ] = "design_implementation_impossibility"
    objective_or_desiderata: ContractElement
    incentive_feasibility_map: ContractElement
    construction_or_minimal_conflict: ContractElement
    decisive_relaxation: ContractElement


class ConceptRepresentationFoundationModule(StrictModel):
    archetype: Literal[
        "concept_representation_foundation"
    ] = "concept_representation_foundation"
    concept_axioms_or_representation: ContractElement
    economic_identity: ContractElement
    representation_or_independence_burden: ContractElement
    changed_conclusion_or_modeling_practice: ContractElement


ArchetypeModule: TypeAlias = Annotated[
    MechanismExplanationModule
    | ComparativeStaticsThresholdModule
    | CharacterizationBoundsModule
    | RobustnessInvarianceEquivalenceModule
    | DesignImplementationImpossibilityModule
    | ConceptRepresentationFoundationModule,
    Field(discriminator="archetype"),
]


class ResultPacket(StrictModel):
    packet_id: StableId
    claim_projection_id: StableId
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    primary_archetype: ResultArchetype
    question: LayerContract
    pre_result_expectation: LayerContract
    formal_statement_and_scope: LayerContract
    economic_translation: LayerContract
    archetype_explanation: LayerContract
    boundary: LayerContract
    proof_roadmap: LayerContract
    consequence: LayerContract
    archetype_module: ArchetypeModule

    @model_validator(mode="after")
    def _packet_has_every_required_layer(self) -> "ResultPacket":
        required = (
            self.question,
            self.formal_statement_and_scope,
            self.economic_translation,
            self.archetype_explanation,
            self.boundary,
            self.proof_roadmap,
            self.consequence,
        )
        if any(item.applicability != "applicable" for item in required):
            raise ValueError("every shared ResultPacket layer except expectation is required")
        if self.primary_archetype != self.archetype_module.archetype:
            raise ValueError("ResultPacket archetype and module disagree")
        return self


class AssumptionContract(StrictModel):
    assumption_id: StableId
    formal_source: SemanticFacetRef
    economic_content: NonEmptyString
    supported_claim_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    proof_steps: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    foundation: Literal["primitive", "reduced_form"]
    satisfying_example_refs: tuple[ExactEvidenceRef, ...] = ()
    failure_without: NonEmptyString
    weaker_condition_status: NonEmptyString
    first_needed_section_id: StableId

    @field_validator("supported_claim_ids")
    @classmethod
    def _supported_claims_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "assumption supported claim IDs")
        return value

    @field_validator("satisfying_example_refs")
    @classmethod
    def _examples_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "assumption satisfying-example refs")
        return value


class ProofRoadmapContract(StrictModel):
    roadmap_id: StableId
    claim_id: StableId
    object_constructed_or_compared: NonEmptyString
    key_decomposition_or_monotonicity_step: NonEmptyString
    assumption_roles: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    main_technical_obstacle: NonEmptyString
    method_or_certificate: NonEmptyString
    scope_not_established: NonEmptyString
    proof_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]

    @field_validator("proof_refs")
    @classmethod
    def _proof_refs_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "proof-roadmap refs")
        return value


class ResultContractSet(AuthoringPayload):
    paper_ir_ref: EntityVersionRef
    reader_path_ref: EntityVersionRef
    claim_graph_ref: EntityVersionRef
    assumption_map_ref: EntityVersionRef
    economic_argument_graph_ref: EntityVersionRef
    example_suite_ref: EntityVersionRef
    verification_bundle_ref: EntityVersionRef
    result_packets: Annotated[tuple[ResultPacket, ...], Field(min_length=1)]
    assumption_contracts: tuple[AssumptionContract, ...] = ()
    proof_roadmaps: Annotated[tuple[ProofRoadmapContract, ...], Field(min_length=1)]
    built_at: NonEmptyString

    @model_validator(mode="after")
    def _contracts_are_closed_and_unique(self) -> "ResultContractSet":
        _unique_ids(self.result_packets, "packet_id", "ResultPacket IDs")
        _unique(
            self.result_packets,
            tuple(item.claim_projection_id for item in self.result_packets),
            "ResultPacket claim projections",
        )
        _unique_ids(self.assumption_contracts, "assumption_id", "assumption contracts")
        _unique_ids(self.proof_roadmaps, "roadmap_id", "proof-roadmap IDs")
        roadmap_claims = {item.claim_id for item in self.proof_roadmaps}
        if any(item.claim_id not in roadmap_claims for item in self.result_packets):
            raise ValueError("every ResultPacket requires a proof roadmap for its claim")
        return self


# ---------------------------------------------------------------------------
# Critic assignment and manuscript realization


CriticRole: TypeAlias = Literal["formal_fidelity", "economic_reader", "cold_reader"]

ReaderProbeKind: TypeAlias = Literal[
    "question_benchmark_retell",
    "exact_scope_recovery",
    "assumption_role_recovery",
    "boundary_discrimination",
    "near_transfer",
]
READER_PROBE_KIND_ORDER: tuple[str, ...] = (
    "question_benchmark_retell",
    "exact_scope_recovery",
    "assumption_role_recovery",
    "boundary_discrimination",
    "near_transfer",
)


class InformationGrant(StrictModel):
    information_kind: Literal[
        "formal_claim",
        "assumptions",
        "examples",
        "economic_argument",
        "reader_background",
        "transfer_objective",
        "manuscript_unit",
        "paper_ir_contract",
    ]
    source_refs: tuple[ExactEvidenceRef, ...] = ()
    description: NonEmptyString

    @field_validator("source_refs")
    @classmethod
    def _grant_refs_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "information grant refs")
        return value


class CriticAssignment(AuthoringPayload):
    assignment_id: StableId
    role: CriticRole
    paper_ir_ref: EntityVersionRef
    reader_path_ref: EntityVersionRef
    result_contract_set_ref: EntityVersionRef
    assigned_actor: Actor
    canonical_writer: Actor
    probe_designer: Actor | None = None
    adjudicator: Actor | None = None
    allowed_information: Annotated[tuple[InformationGrant, ...], Field(min_length=1)]
    forbidden_context: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    transfer_objective: NonEmptyString | None = None
    sealed_context_hash: Digest
    sealed_at: NonEmptyString

    @model_validator(mode="after")
    def _critic_is_independent_and_role_scoped(self) -> "CriticAssignment":
        if _actor_key(self.assigned_actor) == _actor_key(self.canonical_writer):
            raise ValueError("a critic cannot be the canonical writer")
        if self.assigned_actor.kind == "deterministic_tool":
            raise ValueError("assigned critics must be humans or agents")
        if self.role == "cold_reader":
            if self.transfer_objective is None:
                raise ValueError("cold-reader assignment requires a transfer objective")
            if self.probe_designer is None or self.adjudicator is None:
                raise ValueError(
                    "cold-reader assignment requires a probe designer and adjudicator"
                )
            actors = (
                self.canonical_writer,
                self.probe_designer,
                self.assigned_actor,
                self.adjudicator,
            )
            _unique(actors, tuple(_actor_key(item) for item in actors), "cold-reader actors")
            if any(item.kind == "deterministic_tool" for item in actors[1:]):
                raise ValueError("cold-reader roles require human or agent actors")
        elif self.transfer_objective is not None:
            raise ValueError("only the cold reader receives a transfer objective")
        elif self.probe_designer is not None or self.adjudicator is not None:
            raise ValueError("only cold-reader assignments bind probe and adjudication roles")
        lowered = " ".join(self.forbidden_context).lower()
        required = {"hidden", "answer", "other critic"}
        if self.role == "cold_reader" and not all(item in lowered for item in required):
            raise ValueError(
                "cold-reader forbidden context must cover hidden probes, answer keys, "
                "and other critics"
            )
        return self


class ReaderProbeDescriptor(StrictModel):
    """Public probe metadata; the answer criterion remains in the sealed key."""

    probe_id: StableId
    kind: ReaderProbeKind
    prompt_hash: Digest
    target_assertion_ids: tuple[StableId, ...] = ()
    target_contract_ids: tuple[StableId, ...] = ()

    @field_validator("target_assertion_ids", "target_contract_ids")
    @classmethod
    def _targets_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "reader-probe target IDs")
        return value

    @model_validator(mode="after")
    def _probe_has_an_exact_target(self) -> "ReaderProbeDescriptor":
        if not self.target_assertion_ids and not self.target_contract_ids:
            raise ValueError("a reader probe requires an assertion or contract target")
        return self


class ReaderProbeSet(AuthoringPayload):
    """Sealed cold-reader probes over one exact frozen manuscript unit."""

    assignment_ref: EntityVersionRef
    manuscript_unit_ref: EntityVersionRef
    frozen_manuscript_artifact_ref: ArtifactDependencyRef
    probe_designer: Actor
    respondent: Actor
    adjudicator: Actor
    canonical_writer: Actor
    transfer_objective: NonEmptyString
    probes: Annotated[tuple[ReaderProbeDescriptor, ...], Field(min_length=5, max_length=5)]
    probe_artifact_ref: ArtifactDependencyRef
    answer_key_artifact_ref: ArtifactDependencyRef
    route_run_id: StableId
    context_manifest_hash: Digest
    sealed_at: NonEmptyString

    @model_validator(mode="after")
    def _probe_roles_are_four_way_independent(self) -> "ReaderProbeSet":
        actors = (
            self.canonical_writer,
            self.probe_designer,
            self.respondent,
            self.adjudicator,
        )
        _unique(actors, tuple(_actor_key(item) for item in actors), "reader-probe actors")
        if any(item.kind == "deterministic_tool" for item in actors):
            raise ValueError("reader-probe roles require human or agent actors")
        if self.probe_artifact_ref == self.answer_key_artifact_ref:
            raise ValueError("reader probes and the sealed answer key must be distinct")
        _unique_ids(self.probes, "probe_id", "reader-probe IDs")
        if tuple(item.kind for item in self.probes) != READER_PROBE_KIND_ORDER:
            raise ValueError(
                "reader probes must contain the five canonical transfer tests in order"
            )
        return self


class ReaderResponse(AuthoringPayload):
    """A respondent output that deliberately has no answer-key field."""

    probe_set_ref: EntityVersionRef
    manuscript_unit_ref: EntityVersionRef
    respondent: Actor
    answered_probe_ids: Annotated[tuple[StableId, ...], Field(min_length=5)]
    response_artifact_ref: ArtifactDependencyRef
    route_run_id: StableId
    context_manifest_hash: Digest
    submitted_at: NonEmptyString

    @model_validator(mode="after")
    def _response_requires_a_real_reader(self) -> "ReaderResponse":
        if self.respondent.kind == "deterministic_tool":
            raise ValueError("a cold-reader response requires a human or agent")
        _unique(
            self.answered_probe_ids,
            self.answered_probe_ids,
            "answered reader-probe IDs",
        )
        return self


class ManuscriptLocation(StrictModel):
    start_offset: NonNegativeInt
    end_offset: PositiveInt

    @model_validator(mode="after")
    def _range_is_nonempty(self) -> "ManuscriptLocation":
        if self.end_offset <= self.start_offset:
            raise ValueError("manuscript span end must exceed its start")
        return self


AssertionRole: TypeAlias = Literal[
    "formal_statement",
    "economic_translation",
    "mechanism_or_conceptual_explanation",
    "example_or_witness",
    "assumption_interpretation",
    "boundary",
    "proof_roadmap",
    "literature_comparison",
    "consequence",
    "conjecture",
]


class ConsequentialSpan(StrictModel):
    assertion_id: StableId
    role: AssertionRole
    claim_projection_id: StableId
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    source_fields: Annotated[tuple[SemanticFacetRef, ...], Field(min_length=1)]
    scope: NonEmptyString
    assumption_ids: tuple[StableId, ...]
    support_refs: tuple[ExactEvidenceRef, ...] = ()
    location: ManuscriptLocation
    text_hash: Digest
    wording_strength: Literal[
        "exact",
        "entailed_equivalent",
        "entailed_weaker",
        "explicit_conjecture",
    ]
    presentation: Literal[
        "theorem_statement",
        "economic_interpretation",
        "mechanism_explanation",
        "evidence_description",
        "consequence",
        "conjecture",
    ]

    @field_validator("source_fields")
    @classmethod
    def _source_fields_are_unique(
        cls, value: tuple[SemanticFacetRef, ...]
    ) -> tuple[SemanticFacetRef, ...]:
        _unique_refs(value, "span source fields")
        if any(item.field_path is None for item in value):
            raise ValueError("consequential spans require field-level sources")
        return value

    @field_validator("assumption_ids")
    @classmethod
    def _assumptions_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "span assumption IDs")
        return value

    @field_validator("support_refs")
    @classmethod
    def _supports_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "span support refs")
        return value

    @model_validator(mode="after")
    def _span_role_bounds_claim_strength(self) -> "ConsequentialSpan":
        if self.role == "formal_statement" and (
            self.wording_strength != "exact" or self.presentation != "theorem_statement"
        ):
            raise ValueError("formal statements must be exact theorem statements")
        if self.role == "economic_translation" and self.wording_strength not in {
            "exact",
            "entailed_equivalent",
            "entailed_weaker",
        }:
            raise ValueError("economic translations must be entailed or weaker")
        if self.role == "mechanism_or_conceptual_explanation" and not self.support_refs:
            raise ValueError("mechanism explanations require exact supporting evidence")
        if self.role == "conjecture" and (
            self.wording_strength != "explicit_conjecture"
            or self.presentation != "conjecture"
        ):
            raise ValueError("conjectures must be explicitly conjectural")
        if self.role == "consequence" and self.presentation != "consequence":
            raise ValueError("consequences cannot be rendered as theorem statements")
        if self.role != "conjecture" and self.wording_strength == "explicit_conjecture":
            raise ValueError("only conjecture spans may use conjectural strength")
        return self


class TerminologyRealization(StrictModel):
    object_id: StableId
    realized_name: NonEmptyString
    formal_symbol: NonEmptyString
    first_use_assertion_id: StableId


class ManuscriptUnit(AuthoringPayload):
    unit_id: StableId
    paper_ir_ref: EntityVersionRef
    reader_path_ref: EntityVersionRef
    result_contract_set_ref: EntityVersionRef
    section_contract_id: StableId
    manuscript_artifact_ref: ArtifactDependencyRef
    source_state_revision: Digest
    canonical_writer: Actor
    writer_role_packet_hash: Digest
    writer_output_hash: Digest
    integration_generation: PositiveInt
    previous_manuscript_unit_ref: EntityVersionRef | None = None
    previous_manuscript_artifact_ref: ArtifactDependencyRef | None = None
    revision_brief_ref: EntityVersionRef | None = None
    submission_source_unit_ref: EntityVersionRef | None = None
    submission_source_artifact_ref: ArtifactDependencyRef | None = None
    spans: Annotated[tuple[ConsequentialSpan, ...], Field(min_length=1)]
    terminology: Annotated[tuple[TerminologyRealization, ...], Field(min_length=1)]
    composed_at: NonEmptyString

    @model_validator(mode="after")
    def _unit_is_canonical_and_nonoverlapping(self) -> "ManuscriptUnit":
        if self.canonical_writer.kind == "deterministic_tool":
            raise ValueError("a manuscript unit requires a human or agent writer")
        if self.writer_output_hash != self.manuscript_artifact_ref.content_hash:
            raise ValueError(
                "ManuscriptUnit writer output hash must equal the exact manuscript bytes"
            )
        _unique_ids(self.spans, "assertion_id", "manuscript assertion IDs")
        ordered = tuple(
            sorted(self.spans, key=lambda item: item.location.start_offset)
        )
        if ordered != self.spans:
            raise ValueError("manuscript spans must be ordered by start offset")
        for left, right in zip(self.spans, self.spans[1:]):
            if left.location.end_offset > right.location.start_offset:
                raise ValueError("consequential manuscript spans cannot overlap")
        _unique_ids(self.terminology, "object_id", "terminology object IDs")
        assertion_ids = {item.assertion_id for item in self.spans}
        if any(item.first_use_assertion_id not in assertion_ids for item in self.terminology):
            raise ValueError("terminology first use must name a realized assertion")
        revision_refs = (
            self.previous_manuscript_unit_ref,
            self.previous_manuscript_artifact_ref,
            self.revision_brief_ref,
        )
        if self.integration_generation == 1:
            if any(item is not None for item in revision_refs):
                raise ValueError("an initial manuscript unit cannot claim a revision basis")
        elif not all(item is not None for item in revision_refs):
            raise ValueError(
                "a revised manuscript unit requires its exact prior unit, artifact, and brief"
            )
        submission_refs = (
            self.submission_source_unit_ref,
            self.submission_source_artifact_ref,
        )
        if any(item is not None for item in submission_refs) and not all(
            item is not None for item in submission_refs
        ):
            raise ValueError(
                "submission source unit and artifact must be bound together"
            )
        return self


# ---------------------------------------------------------------------------
# Reviews and deterministic closure


class ReviewFinding(AuthoringPayload):
    finding_id: StableId
    assignment_ref: EntityVersionRef
    manuscript_unit_ref: EntityVersionRef
    reviewed_artifact_ref: ArtifactDependencyRef
    role: CriticRole
    critic: Actor
    category: Literal[
        "formal_fidelity",
        "scope",
        "assumption",
        "proof_language",
        "economic_explanation",
        "example_or_witness",
        "reader_prerequisite",
        "terminology",
        "boundary",
        "transfer",
        "governance_leakage",
        "other",
    ]
    severity: Literal["info", "warning", "error", "critical"]
    assertion_ids: tuple[StableId, ...]
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    summary: NonEmptyString
    recommended_repair: NonEmptyString
    blocking: bool
    reported_at: NonEmptyString

    @field_validator("assertion_ids")
    @classmethod
    def _assertion_ids_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "review finding assertion IDs")
        return value

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "review finding evidence refs")
        return value

    @model_validator(mode="after")
    def _critical_finding_blocks(self) -> "ReviewFinding":
        if self.critic.kind == "deterministic_tool":
            raise ValueError("a granular ReviewFinding requires a human or agent critic")
        if self.severity == "critical" and not self.blocking:
            raise ValueError("a critical review finding must be blocking")
        return self


class EntailmentCheck(StrictModel):
    assertion_id: StableId
    scope_relation: Literal["equal", "subset", "stronger", "incomparable"]
    conclusion_relation: Literal[
        "equivalent",
        "weaker",
        "stronger",
        "unsupported",
        "inconclusive",
        "explicit_conjecture",
    ]
    assumptions_preserved: bool
    source_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    outcome: Literal["passed", "failed"]
    rationale: NonEmptyString

    @field_validator("source_refs")
    @classmethod
    def _source_refs_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "entailment-check source refs")
        return value

    @model_validator(mode="after")
    def _outcome_matches_the_closed_entailment_order(self) -> "EntailmentCheck":
        admissible = (
            self.scope_relation in {"equal", "subset"}
            and self.conclusion_relation
            in {"equivalent", "weaker", "explicit_conjecture"}
            and self.assumptions_preserved
        )
        if (self.outcome == "passed") != admissible:
            raise ValueError(
                "entailment outcome disagrees with scope, conclusion, or assumptions"
            )
        return self


class FormalFidelityAssessment(StrictModel):
    role: Literal["formal_fidelity"] = "formal_fidelity"
    theorem_statement_exact: bool
    scope_preserved: bool
    assumptions_preserved: bool
    proof_language_honest: bool
    numerical_evidence_bounded: bool
    entailment_checks: Annotated[tuple[EntailmentCheck, ...], Field(min_length=1)]

    @field_validator("entailment_checks")
    @classmethod
    def _assertions_are_checked_once(
        cls, value: tuple[EntailmentCheck, ...]
    ) -> tuple[EntailmentCheck, ...]:
        _unique_ids(value, "assertion_id", "entailment-check assertion IDs")
        return value

    @model_validator(mode="after")
    def _summary_cannot_hide_a_failed_assertion(self) -> "FormalFidelityAssessment":
        summary_passed = all(
            (
                self.theorem_statement_exact,
                self.scope_preserved,
                self.assumptions_preserved,
                self.proof_language_honest,
                self.numerical_evidence_bounded,
            )
        )
        if summary_passed and any(
            item.outcome != "passed" for item in self.entailment_checks
        ):
            raise ValueError("a passing fidelity summary cannot hide a failed span")
        return self


class EconomicReconstruction(StrictModel):
    """What an isolated economic reader could reconstruct from the prose."""

    claim_projection_id: StableId
    claim_id: StableId
    result_packet_id: StableId
    question_and_benchmark: ExplanatoryText
    operative_force: ExplanatoryText
    affected_margin: ExplanatoryText
    serious_rival_and_separator: ExplanatoryText
    mechanism_steps: Annotated[tuple[MechanismStepText, ...], Field(min_length=3)]
    mechanism_assertion_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    diagnostic_assertion_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    boundary_assertion_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    near_transfer_prediction: ExplanatoryText
    explanatory_delta_from_formal_statement: ExplanatoryText
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]

    @field_validator(
        "mechanism_steps",
        "mechanism_assertion_ids",
        "diagnostic_assertion_ids",
        "boundary_assertion_ids",
    )
    @classmethod
    def _reconstruction_lists_are_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        _unique(value, value, "economic reconstruction list")
        return value

    @field_validator("evidence_refs")
    @classmethod
    def _reconstruction_evidence_is_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "economic reconstruction evidence")
        return value


class EconomicReaderAssessment(StrictModel):
    role: Literal["economic_reader"] = "economic_reader"
    question_and_benchmark_reconstructible: bool
    explanation_is_not_restatement: bool
    mechanism_or_conceptual_logic_reconstructible: bool
    diagnostic_example_or_witness_present: bool
    boundary_is_economically_interpretable: bool
    reconstructions: Annotated[
        tuple[EconomicReconstruction, ...], Field(min_length=1)
    ]

    @model_validator(mode="after")
    def _reconstructions_cover_distinct_packets(self) -> "EconomicReaderAssessment":
        _unique_ids(
            self.reconstructions,
            "result_packet_id",
            "economic reconstruction ResultPacket IDs",
        )
        _unique_ids(
            self.reconstructions,
            "claim_projection_id",
            "economic reconstruction claim projections",
        )
        return self


class ColdReaderProbeResult(StrictModel):
    probe_id: StableId
    kind: ReaderProbeKind
    outcome: Literal["passed", "failed"]
    response_excerpt_hash: Digest
    answer_key_criterion_hash: Digest
    rationale: NonEmptyString


class ColdReaderAssessment(StrictModel):
    role: Literal["cold_reader"] = "cold_reader"
    question_and_benchmark_retell_passed: bool
    exact_scope_recovery_passed: bool
    assumption_role_recovery_passed: bool
    boundary_discrimination_passed: bool
    near_transfer_passed: bool
    response_artifact_ref: ArtifactDependencyRef
    probe_results: Annotated[
        tuple[ColdReaderProbeResult, ...], Field(min_length=5, max_length=5)
    ]

    @model_validator(mode="after")
    def _summary_is_derived_from_each_probe(self) -> "ColdReaderAssessment":
        _unique_ids(self.probe_results, "probe_id", "cold-reader probe-result IDs")
        if tuple(item.kind for item in self.probe_results) != READER_PROBE_KIND_ORDER:
            raise ValueError(
                "cold-reader results must cover the five canonical probes in order"
            )
        outcomes = {
            item.kind: item.outcome == "passed" for item in self.probe_results
        }
        summaries = {
            "question_benchmark_retell": self.question_and_benchmark_retell_passed,
            "exact_scope_recovery": self.exact_scope_recovery_passed,
            "assumption_role_recovery": self.assumption_role_recovery_passed,
            "boundary_discrimination": self.boundary_discrimination_passed,
            "near_transfer": self.near_transfer_passed,
        }
        if outcomes != summaries:
            raise ValueError("cold-reader summary flags must equal per-probe outcomes")
        return self


ReviewAssessment: TypeAlias = Annotated[
    FormalFidelityAssessment | EconomicReaderAssessment | ColdReaderAssessment,
    Field(discriminator="role"),
]


class ReviewRecord(AuthoringPayload):
    assignment_ref: EntityVersionRef
    manuscript_unit_ref: EntityVersionRef
    reviewed_artifact_ref: ArtifactDependencyRef
    role: CriticRole
    reviewer: Actor
    canonical_writer: Actor
    context_hash: Digest
    assessment: ReviewAssessment
    finding_refs: tuple[EntityVersionRef, ...] = ()
    reader_response_ref: EntityVersionRef | None = None
    answer_key_artifact_ref: ArtifactDependencyRef | None = None
    adjudicator: Actor | None = None
    reviewed_at: NonEmptyString

    @field_validator("finding_refs")
    @classmethod
    def _finding_refs_are_unique(
        cls, value: tuple[EntityVersionRef, ...]
    ) -> tuple[EntityVersionRef, ...]:
        _unique_refs(value, "review finding refs")
        return value

    @model_validator(mode="after")
    def _reviewer_and_assessment_match(self) -> "ReviewRecord":
        if _actor_key(self.reviewer) == _actor_key(self.canonical_writer):
            raise ValueError("a manuscript critic cannot be the canonical writer")
        if self.reviewer.kind == "deterministic_tool":
            raise ValueError("a review record requires a human or agent critic")
        if self.assessment.role != self.role:
            raise ValueError("review role and role-specific assessment disagree")
        if self.role == "cold_reader":
            if (
                self.reader_response_ref is None
                or self.answer_key_artifact_ref is None
                or self.adjudicator is None
            ):
                raise ValueError(
                    "cold review requires the exact response, sealed key, and adjudicator"
                )
            if self.reviewer != self.adjudicator:
                raise ValueError("the cold ReviewRecord reviewer must be its adjudicator")
        elif any(
            item is not None
            for item in (
                self.reader_response_ref,
                self.answer_key_artifact_ref,
                self.adjudicator,
            )
        ):
            raise ValueError("only the cold review may bind response/key/adjudicator data")
        return self


AuthoringReadyCheckId: TypeAlias = Literal[
    "exact_g5_and_profile",
    "assurance_pass",
    "exact_span_trace",
    "layer_realization",
    "scope_and_assumptions",
    "bounded_evidentiary_language",
    "formal_fidelity",
    "economic_explanation",
    "cold_reader_transfer",
    "reader_dag_and_terminology",
    "no_governance_or_probe_leakage",
    "canonical_integration",
    "blocking_findings",
]

AUTHORING_READY_CHECK_ORDER: tuple[str, ...] = (
    "exact_g5_and_profile",
    "assurance_pass",
    "exact_span_trace",
    "layer_realization",
    "scope_and_assumptions",
    "bounded_evidentiary_language",
    "formal_fidelity",
    "economic_explanation",
    "cold_reader_transfer",
    "reader_dag_and_terminology",
    "no_governance_or_probe_leakage",
    "canonical_integration",
    "blocking_findings",
)


class AuthoringReadyCheck(StrictModel):
    check_id: AuthoringReadyCheckId
    outcome: Literal["passed", "failed"]
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    rationale: NonEmptyString

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_refs_are_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "authoring-ready check evidence")
        return value


class RevisionInstruction(StrictModel):
    instruction_id: StableId
    finding_ref: EntityVersionRef
    action: Literal[
        "correct_formal_expression",
        "narrow_scope",
        "restore_assumption",
        "repair_explanation",
        "replace_example_or_witness",
        "repair_reader_path",
        "stabilize_terminology",
        "add_boundary",
        "remove_governance_language",
        "request_human_decision",
    ]
    requirement: NonEmptyString
    blocking: bool


class RevisionBrief(AuthoringPayload):
    manuscript_unit_ref: EntityVersionRef
    review_closure_ref: EntityVersionRef
    finding_refs: Annotated[tuple[EntityVersionRef, ...], Field(min_length=1)]
    instructions: Annotated[tuple[RevisionInstruction, ...], Field(min_length=1)]
    brief_artifact_ref: ArtifactDependencyRef
    prepared_by: Actor
    prepared_at: NonEmptyString

    @model_validator(mode="after")
    def _brief_covers_exact_findings(self) -> "RevisionBrief":
        _unique_refs(self.finding_refs, "RevisionBrief finding refs")
        _unique_ids(self.instructions, "instruction_id", "revision instruction IDs")
        known = set(self.finding_refs)
        if any(item.finding_ref not in known for item in self.instructions):
            raise ValueError("revision instruction references a finding outside the brief")
        if not any(item.blocking for item in self.instructions):
            raise ValueError("a blocked revision brief requires a blocking instruction")
        return self


class ReviewClosure(AuthoringPayload):
    predicate_version: Literal["AUTHORING-READY-0.1"] = "AUTHORING-READY-0.1"
    compiler_mode: Literal["preview", "working", "submission"]
    paper_ir_ref: EntityVersionRef
    reader_path_ref: EntityVersionRef
    result_contract_set_ref: EntityVersionRef
    assurance_bundle_ref: EntityVersionRef
    manuscript_unit_ref: EntityVersionRef
    formal_fidelity_review_ref: EntityVersionRef
    economic_reader_review_ref: EntityVersionRef
    cold_reader_review_ref: EntityVersionRef
    closure_actor: Actor
    checks: Annotated[tuple[AuthoringReadyCheck, ...], Field(min_length=13, max_length=13)]
    blocking_finding_ids: tuple[StableId, ...] = ()
    revision_brief_ref: EntityVersionRef | None = None
    status: Literal["authoring_ready", "blocked"]
    evaluated_at: NonEmptyString

    @model_validator(mode="after")
    def _closure_is_a_deterministic_noncompensatory_predicate(self) -> "ReviewClosure":
        reviews = (
            self.formal_fidelity_review_ref,
            self.economic_reader_review_ref,
            self.cold_reader_review_ref,
        )
        _unique_refs(reviews, "ReviewClosure review refs")
        if self.closure_actor.kind != "deterministic_tool":
            raise ValueError("ReviewClosure must be evaluated by a deterministic tool")
        check_ids = tuple(item.check_id for item in self.checks)
        if check_ids != AUTHORING_READY_CHECK_ORDER:
            raise ValueError("ReviewClosure checks must use the exact canonical predicate order")
        _unique(self.blocking_finding_ids, self.blocking_finding_ids, "blocking finding IDs")
        all_passed = all(item.outcome == "passed" for item in self.checks)
        if self.status == "authoring_ready":
            if self.compiler_mode == "preview":
                raise ValueError("preview output can never be authoring-ready")
            if not all_passed or self.blocking_finding_ids:
                raise ValueError("authoring-ready requires every check and no blocker")
            if self.revision_brief_ref is not None:
                raise ValueError("authoring-ready closure cannot require a revision brief")
        else:
            if all_passed and not self.blocking_finding_ids:
                raise ValueError("a blocked closure requires a failed check or blocking finding")
            if self.revision_brief_ref is None:
                raise ValueError("a blocked closure must point to its exact RevisionBrief")
        return self


# ---------------------------------------------------------------------------
# Human effort


class HumanEffortEvent(StrictModel):
    event_id: StableId
    occurred_at: NonEmptyString
    active_minutes: PositiveInt
    affected_assertion_ids: tuple[StableId, ...]
    disposition: Literal[
        "accepted_unchanged", "light_edit", "substantial_rewrite", "deleted"
    ]
    severity: Literal["none", "low", "medium", "high", "critical"]
    category: Literal[
        "formal_correction",
        "mechanism_intuition_repair",
        "assumption_interpretation",
        "reader_path_result_hierarchy",
        "literature_positioning",
        "voice_language",
        "formatting_only",
        "deletion_or_scope_reduction",
    ]
    before_artifact_ref: ArtifactDependencyRef
    after_artifact_ref: ArtifactDependencyRef
    note: NonEmptyString

    @field_validator("affected_assertion_ids")
    @classmethod
    def _affected_assertions_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, value, "effort-event assertion IDs")
        return value

    @model_validator(mode="after")
    def _deletion_categories_are_coherent(self) -> "HumanEffortEvent":
        if self.disposition == "deleted" and self.category not in {
            "deletion_or_scope_reduction",
            "formal_correction",
        }:
            raise ValueError("a deletion must record deletion/scope or formal correction")
        if self.category == "formatting_only" and self.severity in {"high", "critical"}:
            raise ValueError("formatting-only work cannot be high-severity substantive repair")
        return self


class HumanEffortRecord(AuthoringPayload):
    manuscript_unit_ref: EntityVersionRef
    human: Actor
    events: Annotated[tuple[HumanEffortEvent, ...], Field(min_length=1)]
    recorded_at: NonEmptyString

    @model_validator(mode="after")
    def _record_is_human_and_ordered(self) -> "HumanEffortRecord":
        if self.human.kind != "human":
            raise ValueError("HumanEffortRecord requires a human reporter")
        _unique_ids(self.events, "event_id", "human-effort event IDs")
        timestamps = tuple(item.occurred_at for item in self.events)
        if timestamps != tuple(sorted(timestamps)):
            raise ValueError("human-effort events must be ordered by occurred_at")
        if self.recorded_at < timestamps[-1]:
            raise ValueError("recorded_at cannot precede the last effort event")
        return self


# ---------------------------------------------------------------------------
# Independent payload registry and envelope helpers


_FORMAL_TYPES = (ReDerivationRecord, AssuranceBundle)
_PRESENTATION_TYPES = (
    ResolvedProfileManifest,
    PaperIR,
    ReaderPath,
    ResultContractSet,
    ManuscriptUnit,
)
_AUTHORITY_TYPES = (
    CriticAssignment,
    ReaderProbeSet,
    ReaderResponse,
    ReviewFinding,
    ReviewRecord,
    ReviewClosure,
    RevisionBrief,
    HumanEffortRecord,
)
_ALL_PAYLOAD_TYPES = (*_FORMAL_TYPES, *_PRESENTATION_TYPES, *_AUTHORITY_TYPES)

AUTHORING_PAYLOAD_MODELS: Mapping[str, type[AuthoringPayload]] = MappingProxyType(
    {model.__name__: model for model in _ALL_PAYLOAD_TYPES}
)
AUTHORING_PAYLOAD_OWNER_FACETS: Mapping[str, Facet] = MappingProxyType(
    {
        **{model.__name__: "formal" for model in _FORMAL_TYPES},
        **{
            model.__name__: "terminology_presentation"
            for model in _PRESENTATION_TYPES
        },
        **{model.__name__: "authority" for model in _AUTHORITY_TYPES},
    }
)


def authoring_schema_id(entity_type: str) -> str:
    if entity_type not in AUTHORING_PAYLOAD_MODELS:
        raise ValueError(f"unregistered Phase 3 entity_type: {entity_type}")
    return f"econ_theorist.authoring/{entity_type}/v1"


def payload_entity_type(payload: AuthoringPayload) -> str:
    entity_type = type(payload).__name__
    if AUTHORING_PAYLOAD_MODELS.get(entity_type) is not type(payload):
        raise ValueError(
            f"unregistered Phase 3 payload model: {type(payload).__name__}"
        )
    return entity_type


def pack_authoring_payload(payload: AuthoringPayload) -> FacetPayloads:
    """Place a registered Phase 3 payload in its sole semantic owner facet."""

    entity_type = payload_entity_type(payload)
    owner = AUTHORING_PAYLOAD_OWNER_FACETS[entity_type]
    facets: dict[str, object] = {
        "formal": {},
        "economic_interpretation": {},
        "literature_novelty": {},
        "terminology_presentation": {},
        "authority": {},
    }
    facets[owner] = {
        "schema": authoring_schema_id(entity_type),
        "payload": payload.model_dump(mode="json", exclude_none=False),
    }
    return FacetPayloads.model_validate(facets)


def parse_authoring_payload(
    entity_type: str, facets: FacetPayloads | Mapping[str, object]
) -> AuthoringPayload:
    """Validate and parse one independently namespaced authoring envelope."""

    model = AUTHORING_PAYLOAD_MODELS.get(entity_type)
    if model is None:
        raise ValueError(f"unregistered Phase 3 entity_type: {entity_type}")
    if not isinstance(facets, FacetPayloads):
        facets = FacetPayloads.model_validate(facets)
    owner = AUTHORING_PAYLOAD_OWNER_FACETS[entity_type]
    dumped = facets.model_dump(mode="python")
    for facet, value in dumped.items():
        if facet != owner and value != {}:
            raise ValueError(
                f"{entity_type} payload is owned by {owner}; facet {facet} must be empty"
            )
    wrapper = dumped[owner]
    if set(wrapper) != {"schema", "payload"}:
        raise ValueError("typed authoring facet must contain exactly schema and payload")
    expected_schema = authoring_schema_id(entity_type)
    if wrapper["schema"] != expected_schema:
        raise ValueError(f"typed authoring schema mismatch: expected {expected_schema}")
    payload_data = wrapper["payload"]
    if not isinstance(payload_data, dict):
        raise ValueError("typed authoring payload must be a JSON object")
    return model.model_validate_json(canonical_json_bytes(payload_data), strict=True)


def parse_authoring_entity(entity: EntityVersion) -> AuthoringPayload:
    return parse_authoring_payload(entity.entity_type, entity.facets)


def is_packed_authoring_entity(entity: EntityVersion) -> bool:
    owner = AUTHORING_PAYLOAD_OWNER_FACETS.get(entity.entity_type)
    if owner is None:
        return False
    value = getattr(entity.facets, owner)
    return (
        isinstance(value, dict)
        and set(value) == {"schema", "payload"}
        and value.get("schema") == authoring_schema_id(entity.entity_type)
        and isinstance(value.get("payload"), dict)
    )


def validate_human_effort_update(
    previous: HumanEffortRecord, current: HumanEffortRecord
) -> None:
    """Require byte-exact prefix preservation and at least one later event."""

    if previous.manuscript_unit_ref != current.manuscript_unit_ref:
        raise ValueError("HumanEffortRecord cannot change its manuscript unit")
    if previous.human != current.human:
        raise ValueError("HumanEffortRecord cannot change its human reporter")
    if len(current.events) <= len(previous.events):
        raise ValueError("HumanEffortRecord supersession must append an event")
    if canonical_json_bytes(current.events[: len(previous.events)]) != canonical_json_bytes(
        previous.events
    ):
        raise ValueError("HumanEffortRecord must preserve every prior event byte-for-byte")
    if current.events[len(previous.events)].occurred_at < previous.events[-1].occurred_at:
        raise ValueError("appended HumanEffort events must be later than prior events")


def validate_manuscript_unit_update(
    previous: ManuscriptUnit, current: ManuscriptUnit
) -> None:
    """Bind a canonical-writer revision to the prior artifact and one brief."""

    stable_fields = (
        "unit_id",
        "paper_ir_ref",
        "reader_path_ref",
        "result_contract_set_ref",
        "section_contract_id",
        "canonical_writer",
        "submission_source_unit_ref",
        "submission_source_artifact_ref",
    )
    for field in stable_fields:
        if getattr(previous, field) != getattr(current, field):
            raise ValueError(f"ManuscriptUnit revision cannot change {field}")
    if current.integration_generation != previous.integration_generation + 1:
        raise ValueError("ManuscriptUnit integration generation must advance by one")
    if current.previous_manuscript_artifact_ref != previous.manuscript_artifact_ref:
        raise ValueError("ManuscriptUnit revision does not bind the exact prior artifact")
    if current.previous_manuscript_unit_ref is None or current.revision_brief_ref is None:
        raise ValueError("ManuscriptUnit revision requires its exact prior unit and brief")


def validate_authoring_payload_update(
    previous: AuthoringPayload, current: AuthoringPayload
) -> None:
    """Apply type-specific immutable-history rules to a superseding payload."""

    if type(previous) is not type(current):
        raise ValueError("a typed authoring entity cannot change payload model")
    if isinstance(previous, HumanEffortRecord):
        assert isinstance(current, HumanEffortRecord)
        validate_human_effort_update(previous, current)
    elif isinstance(previous, ManuscriptUnit):
        assert isinstance(current, ManuscriptUnit)
        validate_manuscript_unit_update(previous, current)
    elif isinstance(
        previous,
        (
            ReDerivationRecord,
            AssuranceBundle,
            CriticAssignment,
            ReaderProbeSet,
            ReaderResponse,
            ReviewFinding,
            ReviewRecord,
            ReviewClosure,
            RevisionBrief,
        ),
    ):
        raise ValueError(f"{type(previous).__name__} is immutable; create a new entity")


__all__ = [
    "AUTHORING_PAYLOAD_MODELS",
    "AUTHORING_PAYLOAD_OWNER_FACETS",
    "AUTHORING_READY_CHECK_ORDER",
    "AssuranceBundle",
    "AssuranceIssue",
    "AssumptionContract",
    "AuthoringPayload",
    "AuthoringReadyCheck",
    "ClaimProjection",
    "ColdReaderProbeResult",
    "ColdReaderAssessment",
    "ConsequentialSpan",
    "ContractElement",
    "CounterexampleScanEvidence",
    "CriticAssignment",
    "DerivationStep",
    "EconomicOntologyEntry",
    "EconomicReconstruction",
    "EconomicReaderAssessment",
    "EntailmentCheck",
    "ExactAssignmentSpec",
    "ExactAssignmentValue",
    "ExactPolynomialSpec",
    "ExactPolynomialTermSpec",
    "ExactRationalValue",
    "FormalFidelityAssessment",
    "HumanEffortEvent",
    "HumanEffortRecord",
    "HarnessNonApplicabilityRecord",
    "InformationGrant",
    "LayerContract",
    "ManuscriptLocation",
    "ManuscriptUnit",
    "NarrativeSpine",
    "PaperIR",
    "ProofAudit",
    "ProofAuditFinding",
    "PolynomialPowerSpec",
    "PolynomialRelationPredicate",
    "ProofRoadmapContract",
    "ReDerivationRecord",
    "ReaderBeliefState",
    "ReaderKnowledgeItem",
    "ReaderPath",
    "ReaderProbeDescriptor",
    "READER_PROBE_KIND_ORDER",
    "ReaderProbeSet",
    "ReaderResponse",
    "ReaderStateEdge",
    "ResolvedProfileManifest",
    "ResultContractSet",
    "ResultPacket",
    "RunProvenanceBinding",
    "ReviewClosure",
    "ReviewFinding",
    "ReviewRecord",
    "RevisionBrief",
    "RevisionInstruction",
    "SectionContract",
    "SymbolicIdentityEvidence",
    "TerminologyRealization",
    "ToolHarnessReceipt",
    "authoring_schema_id",
    "is_packed_authoring_entity",
    "pack_authoring_payload",
    "parse_authoring_entity",
    "parse_authoring_payload",
    "payload_entity_type",
    "validate_authoring_payload_update",
    "validate_human_effort_update",
    "validate_manuscript_unit_update",
]
