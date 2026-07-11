"""Strict canonical models for the Phase 1 walking substrate.

These models describe admissible bytes and references.  They do not certify
economic merit, mathematical validity, human acceptance, or freshness.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from .codec import ensure_canonical_data

NonEmptyString: TypeAlias = Annotated[str, StringConstraints(min_length=1)]
Digest: TypeAlias = Annotated[
    str, StringConstraints(pattern=r"^[0-9a-f]{64}$")
]
StableId: TypeAlias = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9_.:-]*$")
]

Facet: TypeAlias = Literal[
    "formal",
    "economic_interpretation",
    "literature_novelty",
    "terminology_presentation",
    "authority",
]
FACET_ORDER: tuple[Facet, ...] = (
    "formal",
    "economic_interpretation",
    "literature_novelty",
    "terminology_presentation",
    "authority",
)

ActorKind: TypeAlias = Literal["human", "agent", "deterministic_tool"]
AuthorityLevel: TypeAlias = Literal["L0", "L1", "L2", "L3"]
PrivacyLabel: TypeAlias = Literal[
    "public", "project_private", "restricted", "local_only"
]
Lifecycle: TypeAlias = Literal["proposed", "active", "superseded", "retired"]
FormalValidity: TypeAlias = Literal[
    "not_applicable",
    "unassessed",
    "exploratory_only",
    "partially_checked",
    "verified_in_scope",
    "failed",
    "disputed",
]
InterpretationValidity: TypeAlias = Literal[
    "not_applicable",
    "unassessed",
    "hypothesized",
    "example_supported",
    "stress_tested",
    "validated",
    "failed",
    "disputed",
]
LiteratureCoverage: TypeAlias = Literal[
    "not_started", "partial", "current", "needs_refresh"
]
LiteratureNovelty: TypeAlias = Literal[
    "unassessed", "unresolved", "differentiated", "absorbed", "disputed"
]
DependencyMode: TypeAlias = Literal[
    "hard", "scope_sensitive", "evidentiary", "presentation", "trace_only"
]
DecisionStatus: TypeAlias = Literal[
    "proposed", "provisional", "confirmed", "rejected", "superseded"
]
Freshness: TypeAlias = Literal[
    "fresh", "stale", "revalidating", "blocked_by_stale_input"
]
HumanAcceptance: TypeAlias = Literal[
    "agent_proposed",
    "human_provisional",
    "human_confirmed",
    "human_rejected",
    "human_mixed",
    "superseded",
]
DecisionKind: TypeAlias = Literal[
    "G1_question_benchmark",
    "G2_mechanism",
    "G3_formal_base",
    "G4_result_investment",
    "G5_argument_validation",
    "primitive_promotion",
    "solution_concept",
    "main_result_scope",
    "novelty_contribution",
    "argument_spine",
    "narrative_material_order",
    "theory_mode",
    "ambition",
    "field",
    "audience",
    "venue_overlay",
    "submission_constraints",
    "target_profile",
    "voice_charter",
    "manuscript_version_promotion",
    "privacy_declassification",
    "external_release",
    "submission_handoff",
    "external_communication",
    "destructive_cleanup",
]
GATE_DECISION_KINDS = frozenset(
    {
        "G1_question_benchmark",
        "G2_mechanism",
        "G3_formal_base",
        "G4_result_investment",
        "G5_argument_validation",
    }
)
StoredStatusDimension: TypeAlias = Literal[
    "lifecycle",
    "formal_validity",
    "interpretation_validity",
    "literature.coverage",
    "literature.novelty",
]
RouteAvailability: TypeAlias = Literal["enabled", "not_implemented"]


class StrictModel(BaseModel):
    """Common fail-closed Pydantic configuration for canonical models."""

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        frozen=True,
        validate_default=True,
    )


class Actor(StrictModel):
    kind: ActorKind
    actor_id: StableId


class LiteratureStatus(StrictModel):
    coverage: LiteratureCoverage
    novelty: LiteratureNovelty


class ScientificStatus(StrictModel):
    """Stored dimensions only; acceptance and freshness are projections."""

    lifecycle: Lifecycle = "proposed"
    formal_validity: FormalValidity | None = None
    interpretation_validity: InterpretationValidity | None = None
    literature: LiteratureStatus | None = None


class FacetPayloads(StrictModel):
    """Generic Phase 1 payload partitioned into the five semantic facets."""

    formal: dict[str, Any] = Field(default_factory=dict)
    economic_interpretation: dict[str, Any] = Field(default_factory=dict)
    literature_novelty: dict[str, Any] = Field(default_factory=dict)
    terminology_presentation: dict[str, Any] = Field(default_factory=dict)
    authority: dict[str, Any] = Field(default_factory=dict)

    @field_validator("*", mode="before")
    @classmethod
    def _canonical_payload(cls, value: Any) -> Any:
        normalized = ensure_canonical_data(value)
        if not isinstance(normalized, dict):
            raise ValueError("each semantic facet must be a JSON object")
        return normalized


class EntityVersionRef(StrictModel):
    entity_id: StableId
    version: Annotated[int, Field(ge=1)]


class RelationVersionRef(StrictModel):
    relation_id: StableId
    version: Annotated[int, Field(ge=1)]


class DecisionVersionRef(StrictModel):
    decision_id: StableId
    version: Annotated[int, Field(ge=1)]


class EffectiveDecisionRef(DecisionVersionRef):
    """Replay projection binding an effective Decision to its transaction."""

    effective_revision: Digest


class ArtifactVersionRef(StrictModel):
    artifact_id: StableId
    version: Annotated[int, Field(ge=1)]


class ArtifactDependencyRef(ArtifactVersionRef):
    """Exact immutable artifact bytes consumed by a canonical entity."""

    content_hash: Digest


class BlockerRef(StrictModel):
    blocker_id: StableId


CanonicalObjectRef: TypeAlias = (
    EntityVersionRef
    | RelationVersionRef
    | DecisionVersionRef
    | ArtifactDependencyRef
    | BlockerRef
)


class FacetPathRef(StrictModel):
    entity_id: StableId
    version: Annotated[int, Field(ge=1)]
    facet: Facet
    field_path: NonEmptyString | None = None

    @field_validator("field_path")
    @classmethod
    def _field_path_is_canonical_json_pointer(
        cls, value: str | None
    ) -> str | None:
        if value is None:
            return None
        if not value.startswith("/"):
            raise ValueError("field_path must be an RFC 6901 JSON Pointer")
        index = 0
        while index < len(value):
            if value[index] != "~":
                index += 1
                continue
            if index + 1 >= len(value) or value[index + 1] not in {"0", "1"}:
                raise ValueError("field_path contains a noncanonical JSON Pointer escape")
            index += 2
        return value


class SemanticFacetRef(FacetPathRef):
    semantic_hash: Digest


class EntityPrivacySubject(StrictModel):
    subject_type: Literal["entity"] = "entity"
    entity: EntityVersionRef


class RelationPrivacySubject(StrictModel):
    subject_type: Literal["relation"] = "relation"
    relation: RelationVersionRef


class ArtifactPrivacySubject(StrictModel):
    subject_type: Literal["artifact"] = "artifact"
    artifact: ArtifactVersionRef


PrivacySubject: TypeAlias = Annotated[
    EntityPrivacySubject | RelationPrivacySubject | ArtifactPrivacySubject,
    Field(discriminator="subject_type"),
]


class PrivacyChange(StrictModel):
    """One exact requested release of an immutable canonical object version."""

    subject: PrivacySubject
    from_privacy: PrivacyLabel
    to_privacy: PrivacyLabel

    @model_validator(mode="after")
    def _is_a_real_downgrade(self) -> "PrivacyChange":
        ranks = {"public": 0, "project_private": 1, "restricted": 2, "local_only": 3}
        if ranks[self.to_privacy] >= ranks[self.from_privacy]:
            raise ValueError("privacy declassification must name a strict downgrade")
        return self


class ScopeOverlapEvidence(StrictModel):
    """Typed exact scope versions supporting one scope-sensitive dependency."""

    source_scope: EntityVersionRef
    target_scope: EntityVersionRef


def _canonical_compartments(value: tuple[str, ...]) -> tuple[str, ...]:
    if len(set(value)) != len(value):
        raise ValueError("access compartments must be unique")
    return tuple(sorted(value))


class EntityVersion(StrictModel):
    entity_id: StableId
    entity_type: StableId
    version: Annotated[int, Field(ge=1)]
    project_id: StableId
    title: NonEmptyString
    summary: NonEmptyString
    scope_ref: StableId | None = None
    status: ScientificStatus
    facets: FacetPayloads
    artifact_refs: tuple[ArtifactDependencyRef, ...] = ()
    privacy: PrivacyLabel = "project_private"
    access_compartments: tuple[StableId, ...] = ("project_research",)
    created_at: NonEmptyString
    supersedes: EntityVersionRef | None = None

    @field_validator("access_compartments")
    @classmethod
    def _compartments_are_a_canonical_set(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _canonical_compartments(value)

    @field_validator("artifact_refs")
    @classmethod
    def _artifact_refs_are_exact_and_unique(
        cls, value: tuple[ArtifactDependencyRef, ...]
    ) -> tuple[ArtifactDependencyRef, ...]:
        keys = [(item.artifact_id, item.version) for item in value]
        if len(set(keys)) != len(keys):
            raise ValueError("artifact_refs must not repeat an artifact version")
        return tuple(sorted(value, key=lambda item: (item.artifact_id, item.version)))

    @model_validator(mode="after")
    def _version_chain_is_explicit(self) -> "EntityVersion":
        if self.version == 1 and self.supersedes is not None:
            raise ValueError("entity version 1 cannot supersede an earlier version")
        if self.version > 1:
            if self.supersedes is None:
                raise ValueError("entity version >1 requires an exact supersedes ref")
            if self.supersedes.entity_id != self.entity_id:
                raise ValueError("entity supersedes ref must have the same entity_id")
            if self.supersedes.version != self.version - 1:
                raise ValueError("entity versions must form a contiguous chain")
        return self


class RelationVersion(StrictModel):
    relation_id: StableId
    relation_type: StableId
    version: Annotated[int, Field(ge=1)]
    project_id: StableId
    source: EntityVersionRef
    target: EntityVersionRef
    dependency_mode: DependencyMode = "trace_only"
    upstream: SemanticFacetRef | None = None
    downstream: FacetPathRef | None = None
    scope_ref: StableId | None = None
    scope_overlap: ScopeOverlapEvidence | None = None
    privacy: PrivacyLabel = "project_private"
    access_compartments: tuple[StableId, ...] = ("project_research",)
    created_at: NonEmptyString
    supersedes: RelationVersionRef | None = None

    @field_validator("access_compartments")
    @classmethod
    def _compartments_are_a_canonical_set(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _canonical_compartments(value)

    @model_validator(mode="after")
    def _dependency_and_version_are_exact(self) -> "RelationVersion":
        if self.version == 1 and self.supersedes is not None:
            raise ValueError("relation version 1 cannot supersede an earlier version")
        if self.version > 1:
            if self.supersedes is None:
                raise ValueError("relation version >1 requires an exact supersedes ref")
            if self.supersedes.relation_id != self.relation_id:
                raise ValueError("relation supersedes ref must keep relation_id")
            if self.supersedes.version != self.version - 1:
                raise ValueError("relation versions must form a contiguous chain")

        if self.dependency_mode == "trace_only":
            if self.upstream is not None or self.downstream is not None:
                raise ValueError("trace_only relations cannot invalidate facet refs")
            return self

        if self.upstream is None or self.downstream is None:
            raise ValueError("invalidating relations require both exact facet endpoints")
        if (
            self.upstream.entity_id != self.source.entity_id
            or self.upstream.version != self.source.version
        ):
            raise ValueError("upstream facet must bind the exact source version")
        if (
            self.downstream.entity_id != self.target.entity_id
            or self.downstream.version != self.target.version
        ):
            raise ValueError("downstream facet must bind the exact target version")
        if self.dependency_mode == "scope_sensitive":
            if (self.scope_ref is None) == (self.scope_overlap is None):
                raise ValueError(
                    "scope_sensitive invalidation needs exactly one of exact "
                    "scope equality or typed overlap evidence"
                )
        elif self.scope_overlap is not None:
            raise ValueError("scope_overlap is valid only for scope_sensitive dependencies")
        return self


class Decision(StrictModel):
    """Immutable authority evidence; effective_revision is replay-derived."""

    decision_id: StableId
    version: Annotated[int, Field(ge=1)]
    project_id: StableId
    decision_kind: DecisionKind
    subject_ref: StableId
    scope_ref: StableId | None = None
    question: NonEmptyString
    options: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    selected_option: NonEmptyString | None = None
    machine_outcome: Literal["approve", "deny"] | None = None
    privacy_change: PrivacyChange | None = None
    recommendation: NonEmptyString
    rationale: NonEmptyString
    evidence_refs: tuple[StableId, ...] = ()
    dissent_refs: tuple[StableId, ...] = ()
    unresolved_risks: tuple[NonEmptyString, ...] = ()
    required_authority: AuthorityLevel
    decider: Actor
    decided_at: NonEmptyString
    affected_scopes: tuple[StableId, ...] = ()
    status: DecisionStatus
    privacy: PrivacyLabel = "project_private"
    access_compartments: tuple[StableId, ...] = ("project_research",)
    supersedes: DecisionVersionRef | None = None

    @field_validator("access_compartments")
    @classmethod
    def _compartments_are_a_canonical_set(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _canonical_compartments(value)

    @model_validator(mode="after")
    def _decision_is_complete(self) -> "Decision":
        if len(set(self.options)) != len(self.options):
            raise ValueError("decision options must be unique")
        if self.selected_option is not None and self.selected_option not in self.options:
            raise ValueError("selected_option must be one of the available options")
        if self.status in {"provisional", "confirmed"} and self.selected_option is None:
            raise ValueError("a provisional or confirmed decision must select an option")
        if self.decision_kind == "privacy_declassification":
            if self.privacy_change is None:
                raise ValueError(
                    "privacy_declassification requires one exact typed privacy_change"
                )
            subject = self.privacy_change.subject
            if isinstance(subject, EntityPrivacySubject):
                subject_id = subject.entity.entity_id
            elif isinstance(subject, RelationPrivacySubject):
                subject_id = subject.relation.relation_id
            else:
                subject_id = subject.artifact.artifact_id
            if self.subject_ref != subject_id:
                raise ValueError(
                    "privacy Decision subject_ref must match its typed exact subject"
                )
            if self.status in {"provisional", "confirmed"}:
                if self.machine_outcome not in {"approve", "deny"}:
                    raise ValueError(
                        "effective privacy Decisions require approve or deny outcome"
                    )
                if self.selected_option != self.machine_outcome:
                    raise ValueError(
                        "privacy Decision selected_option must equal machine_outcome"
                    )
            elif self.machine_outcome is not None:
                raise ValueError(
                    "non-effective privacy Decisions cannot carry a machine outcome"
                )
        elif self.decision_kind in GATE_DECISION_KINDS:
            if self.privacy_change is not None:
                raise ValueError("G1-G5 Decisions cannot carry a privacy_change")
            # ``None`` remains valid for frozen Phase 1 histories.  Phase 2's
            # typed GateDossier validator requires an explicit machine outcome.
            if self.machine_outcome is not None:
                if self.status not in {"provisional", "confirmed"}:
                    raise ValueError(
                        "non-effective G1-G5 Decisions cannot carry a machine outcome"
                    )
                if self.selected_option != self.machine_outcome:
                    raise ValueError(
                        "G1-G5 Decision selected_option must equal machine_outcome"
                    )
        elif self.privacy_change is not None or self.machine_outcome is not None:
            raise ValueError(
                "privacy_change and machine_outcome are reserved for typed gate Decisions"
            )
        if self.version == 1 and self.supersedes is not None:
            raise ValueError("decision version 1 cannot supersede an earlier version")
        if self.version > 1:
            if self.supersedes is None:
                raise ValueError("decision version >1 requires an exact supersedes ref")
            if self.supersedes.decision_id != self.decision_id:
                raise ValueError("decision supersedes ref must keep decision_id")
            if self.supersedes.version != self.version - 1:
                raise ValueError("decision versions must form a contiguous chain")
        return self


class ArtifactRegistration(StrictModel):
    artifact_id: StableId
    version: Annotated[int, Field(ge=1)]
    project_id: StableId
    logical_name: NonEmptyString
    media_type: NonEmptyString
    content_hash: Digest
    byte_size: Annotated[int, Field(ge=0)]
    privacy: PrivacyLabel = "project_private"
    access_compartments: tuple[StableId, ...] = ("project_research",)
    human_owned: bool = False
    logical_path: NonEmptyString | None = None
    expected_base_hash: Digest | None = None
    created_at: NonEmptyString
    supersedes: ArtifactVersionRef | None = None

    @field_validator("access_compartments")
    @classmethod
    def _compartments_are_a_canonical_set(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _canonical_compartments(value)

    @model_validator(mode="after")
    def _human_owned_registration_is_reconcilable(self) -> "ArtifactRegistration":
        if self.human_owned and (
            self.logical_path is None or self.expected_base_hash is None
        ):
            raise ValueError(
                "human-owned artifact proposals require logical_path and expected_base_hash"
            )
        if not self.human_owned and (
            self.logical_path is not None or self.expected_base_hash is not None
        ):
            raise ValueError(
                "only human-owned artifact proposals may name a working path or base hash"
            )
        if self.version == 1 and self.supersedes is not None:
            raise ValueError("artifact version 1 cannot supersede an earlier version")
        if self.version > 1:
            if self.supersedes is None:
                raise ValueError("artifact version >1 requires an exact supersedes ref")
            if self.supersedes.artifact_id != self.artifact_id:
                raise ValueError("artifact supersedes ref must keep artifact_id")
            if self.supersedes.version != self.version - 1:
                raise ValueError("artifact versions must form a contiguous chain")
        return self


class Precondition(StrictModel):
    entity: EntityVersionRef
    expected_semantic_hashes: dict[Facet, Digest] = Field(default_factory=dict)


class ChangedFacets(StrictModel):
    entity_id: StableId
    previous_version: Annotated[int, Field(ge=1)]
    new_version: Annotated[int, Field(ge=2)]
    facets: Annotated[tuple[Facet, ...], Field(min_length=1)]

    @field_validator("facets")
    @classmethod
    def _facets_are_a_canonical_set(cls, value: tuple[Facet, ...]) -> tuple[Facet, ...]:
        if len(set(value)) != len(value):
            raise ValueError("changed facets must be unique")
        return tuple(facet for facet in FACET_ORDER if facet in value)

    @model_validator(mode="after")
    def _versions_are_adjacent(self) -> "ChangedFacets":
        if self.new_version != self.previous_version + 1:
            raise ValueError("changed-facet versions must be adjacent")
        return self


class StatusTransition(StrictModel):
    entity: EntityVersionRef
    dimension: StoredStatusDimension
    from_value: NonEmptyString | None = None
    to_value: NonEmptyString
    evidence_refs: tuple[StableId, ...] = ()


class RouteOutcome(StrictModel):
    route_run_id: StableId
    route_id: StableId
    outcome: Literal[
        "completed_with_candidate",
        "failed",
        "interrupted",
        "validated",
        "rejected",
        "superseded",
    ]
    rationale: NonEmptyString
    candidate_refs: tuple[CanonicalObjectRef, ...] = ()
    validator_report_refs: tuple[ArtifactDependencyRef, ...] = ()
    privacy: PrivacyLabel = "project_private"
    access_compartments: tuple[StableId, ...] = ("project_research",)

    @field_validator("access_compartments")
    @classmethod
    def _compartments_are_a_canonical_set(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _canonical_compartments(value)

    @model_validator(mode="after")
    def _validated_outcome_has_exact_evidence(self) -> "RouteOutcome":
        if self.outcome in {
            "completed_with_candidate",
            "validated",
            "rejected",
            "superseded",
        } and not self.candidate_refs:
            raise ValueError(
                f"{self.outcome} RouteOutcome requires an exact candidate ref"
            )
        if self.outcome == "validated" and not self.validator_report_refs:
            raise ValueError(
                "validated RouteOutcome requires an exact validator report artifact"
            )
        return self


class RiskOrBlocker(StrictModel):
    blocker_id: StableId
    project_id: StableId
    kind: StableId
    severity: Literal["info", "warning", "error", "critical"]
    summary: NonEmptyString
    affected_refs: tuple[CanonicalObjectRef, ...] = ()
    required_route: StableId | None = None
    created_at: NonEmptyString
    privacy: PrivacyLabel = "project_private"
    access_compartments: tuple[StableId, ...] = ("project_research",)

    @field_validator("access_compartments")
    @classmethod
    def _compartments_are_a_canonical_set(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _canonical_compartments(value)


class CreateEntityOp(StrictModel):
    op: Literal["entity.create"] = "entity.create"
    entity: EntityVersion


class SupersedeEntityOp(StrictModel):
    op: Literal["entity.supersede"] = "entity.supersede"
    previous: EntityVersionRef
    entity: EntityVersion

    @model_validator(mode="after")
    def _refs_match(self) -> "SupersedeEntityOp":
        if self.entity.supersedes != self.previous:
            raise ValueError("new entity supersedes ref must match previous")
        return self


class RetireEntityOp(StrictModel):
    op: Literal["entity.retire"] = "entity.retire"
    entity: EntityVersionRef
    reason: NonEmptyString


class CreateRelationOp(StrictModel):
    op: Literal["relation.create"] = "relation.create"
    relation: RelationVersion


class SupersedeRelationOp(StrictModel):
    op: Literal["relation.supersede"] = "relation.supersede"
    previous: RelationVersionRef
    relation: RelationVersion

    @model_validator(mode="after")
    def _refs_match(self) -> "SupersedeRelationOp":
        if self.relation.supersedes != self.previous:
            raise ValueError("new relation supersedes ref must match previous")
        return self


class RetireRelationOp(StrictModel):
    op: Literal["relation.retire"] = "relation.retire"
    relation: RelationVersionRef
    reason: NonEmptyString


class StatusTransitionOp(StrictModel):
    op: Literal["status.transition"] = "status.transition"
    transition: StatusTransition


class RecordDecisionOp(StrictModel):
    op: Literal["decision.record"] = "decision.record"
    decision: Decision


class SupersedeDecisionOp(StrictModel):
    op: Literal["decision.supersede"] = "decision.supersede"
    previous: DecisionVersionRef
    decision: Decision

    @model_validator(mode="after")
    def _refs_match(self) -> "SupersedeDecisionOp":
        if self.decision.supersedes != self.previous:
            raise ValueError("new Decision supersedes ref must match previous")
        return self


class RegisterArtifactOp(StrictModel):
    op: Literal["artifact.register"] = "artifact.register"
    artifact: ArtifactRegistration


class RecordRouteOutcomeOp(StrictModel):
    op: Literal["route.outcome"] = "route.outcome"
    outcome: RouteOutcome


class RecordBlockerOp(StrictModel):
    op: Literal["blocker.record"] = "blocker.record"
    blocker: RiskOrBlocker


Operation: TypeAlias = Annotated[
    CreateEntityOp
    | SupersedeEntityOp
    | RetireEntityOp
    | CreateRelationOp
    | SupersedeRelationOp
    | RetireRelationOp
    | StatusTransitionOp
    | RecordDecisionOp
    | SupersedeDecisionOp
    | RegisterArtifactOp
    | RecordRouteOutcomeOp
    | RecordBlockerOp,
    Field(discriminator="op"),
]


class Transaction(StrictModel):
    """Canonical transaction body.  Its digest is intentionally absent."""

    transaction_id: StableId
    transaction_schema: Literal[1] = 1
    origin: Literal["genesis", "route_run", "human_decision"]
    project_id: StableId
    base_revision: Digest | None
    route_run_id: StableId
    route_id: StableId | None = None
    route_run_hash: Digest | None = None
    context_manifest_hash: Digest | None = None
    compiled_context_hash: Digest | None = None
    actor: Actor
    intent: NonEmptyString
    preconditions: tuple[Precondition, ...] = ()
    changed_facets: tuple[ChangedFacets, ...] = ()
    operations: Annotated[tuple[Operation, ...], Field(min_length=1)]
    evidence_refs: tuple[CanonicalObjectRef, ...] = ()
    authority_basis: tuple[StableId, ...] = ()
    privacy: PrivacyLabel = "project_private"
    access_compartments: tuple[StableId, ...] = ("project_research",)
    created_at: NonEmptyString
    parent_transaction_hash: Digest | None

    @field_validator("access_compartments")
    @classmethod
    def _transaction_compartments_are_a_canonical_set(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _canonical_compartments(value)

    @model_validator(mode="after")
    def _chain_and_changed_facets_are_explicit(self) -> "Transaction":
        if self.base_revision != self.parent_transaction_hash:
            raise ValueError("base_revision must equal parent_transaction_hash")
        provenance_hashes = (
            self.route_run_hash,
            self.context_manifest_hash,
            self.compiled_context_hash,
        )
        if self.origin == "route_run" and not all(
            value is not None for value in provenance_hashes
        ):
            raise ValueError(
                "route_run transactions require route run, context manifest, "
                "and compiled context hashes"
            )
        if self.origin == "route_run" and self.route_id is None:
            raise ValueError("route_run transactions require an exact route_id")
        if self.origin != "route_run" and any(
            value is not None for value in provenance_hashes
        ):
            raise ValueError(
                "genesis and human_decision transactions cannot carry route provenance"
            )
        if self.origin != "route_run" and self.route_id is not None:
            raise ValueError("only route_run transactions may carry route_id")

        supersessions: dict[tuple[str, int, int], SupersedeEntityOp] = {}
        for operation in self.operations:
            if isinstance(operation, SupersedeEntityOp):
                key = (
                    operation.entity.entity_id,
                    operation.previous.version,
                    operation.entity.version,
                )
                if key in supersessions:
                    raise ValueError("an entity version may be superseded only once per transaction")
                supersessions[key] = operation

        declarations: set[tuple[str, int, int]] = set()
        for declaration in self.changed_facets:
            key = (
                declaration.entity_id,
                declaration.previous_version,
                declaration.new_version,
            )
            if key in declarations:
                raise ValueError("changed_facets contains a duplicate entity declaration")
            declarations.add(key)

        if set(supersessions) != declarations:
            raise ValueError(
                "changed_facets must declare exactly every superseding entity operation"
            )
        return self


class RouteSpec(StrictModel):
    route_id: StableId
    route_version: Literal[1] = 1
    availability: RouteAvailability
    authority_ceiling: AuthorityLevel = "L1"
    allowed_purposes: Annotated[tuple[StableId, ...], Field(min_length=1)]
    required_compartments: tuple[StableId, ...] = ("project_research",)
    allowed_operations: tuple[StableId, ...] = ()
    instruction_bundle_id: StableId | None = None
    instruction_bundle_hash: Digest | None = None

    @model_validator(mode="after")
    def _enabled_route_is_executable(self) -> "RouteSpec":
        if self.availability == "enabled" and (
            not self.allowed_operations
            or self.instruction_bundle_id is None
            or self.instruction_bundle_hash is None
        ):
            raise ValueError(
                "enabled routes require allowed operations and a hashed instruction bundle"
            )
        return self


class RouteRegistry(StrictModel):
    registry_version: Literal[1] = 1
    aliases: dict[StableId, StableId] = Field(default_factory=dict)
    routes: Annotated[tuple[RouteSpec, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _route_ids_are_unique(self) -> "RouteRegistry":
        route_ids = [route.route_id for route in self.routes]
        if len(set(route_ids)) != len(route_ids):
            raise ValueError("route registry contains duplicate exact IDs")
        return self


class RouteEntityRequirement(StrictModel):
    """Exact entity-type cardinality required at one v2 route boundary."""

    entity_type: StableId
    min_count: Annotated[int, Field(ge=0)] = 1
    max_count: Annotated[int, Field(ge=1)] | None = None

    @model_validator(mode="after")
    def _maximum_does_not_precede_minimum(self) -> "RouteEntityRequirement":
        if self.max_count is not None and self.max_count < self.min_count:
            raise ValueError("route entity maximum cannot be below its minimum")
        return self


class RouteRelationRequirement(StrictModel):
    """Exact relation-type cardinality required at one v2 route exit."""

    relation_type: StableId
    min_count: Annotated[int, Field(ge=1)] = 1
    max_count: Annotated[int, Field(ge=1)] | None = None

    @model_validator(mode="after")
    def _maximum_does_not_precede_minimum(self) -> "RouteRelationRequirement":
        if self.max_count is not None and self.max_count < self.min_count:
            raise ValueError("route relation maximum cannot be below its minimum")
        return self


class RouteSpecV2(StrictModel):
    """Phase 2 route contract without changing the frozen v1 projection."""

    route_id: StableId
    route_version: Literal[2] = 2
    availability: RouteAvailability
    authority_ceiling: AuthorityLevel = "L1"
    allowed_purposes: Annotated[tuple[StableId, ...], Field(min_length=1)]
    required_compartments: tuple[StableId, ...] = ("project_research",)
    allowed_operations: tuple[StableId, ...] = ()
    allowed_entity_types: tuple[StableId, ...] = ()
    allowed_relation_types: tuple[StableId, ...] = ()
    required_input_entities: tuple[RouteEntityRequirement, ...] = ()
    required_output_entities: tuple[RouteEntityRequirement, ...] = ()
    required_output_relations: tuple[RouteRelationRequirement, ...] = ()
    required_gate_kinds: tuple[DecisionKind, ...] = ()
    entry_validator_id: StableId | None = None
    exit_validator_id: StableId | None = None
    instruction_bundle_id: StableId | None = None
    instruction_bundle_hash: Digest | None = None

    @field_validator(
        "required_compartments",
        "allowed_operations",
        "allowed_entity_types",
        "allowed_relation_types",
        "required_gate_kinds",
    )
    @classmethod
    def _contract_sets_are_canonical(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("v2 route contract lists must not contain duplicates")
        if value != tuple(sorted(value)):
            raise ValueError("v2 route contract lists must be canonically ordered")
        return value

    @field_validator("required_input_entities", "required_output_entities")
    @classmethod
    def _entity_requirements_are_canonical(
        cls, value: tuple[RouteEntityRequirement, ...]
    ) -> tuple[RouteEntityRequirement, ...]:
        entity_types = tuple(item.entity_type for item in value)
        if len(set(entity_types)) != len(entity_types):
            raise ValueError("v2 route entity requirements must not repeat a type")
        if entity_types != tuple(sorted(entity_types)):
            raise ValueError("v2 route entity requirements must be canonically ordered")
        return value

    @field_validator("required_output_relations")
    @classmethod
    def _relation_requirements_are_canonical(
        cls, value: tuple[RouteRelationRequirement, ...]
    ) -> tuple[RouteRelationRequirement, ...]:
        relation_types = tuple(item.relation_type for item in value)
        if len(set(relation_types)) != len(relation_types):
            raise ValueError("v2 route relation requirements must not repeat a type")
        if relation_types != tuple(sorted(relation_types)):
            raise ValueError("v2 route relation requirements must be canonically ordered")
        return value

    @model_validator(mode="after")
    def _enabled_route_is_executable(self) -> "RouteSpecV2":
        if self.availability == "enabled" and (
            not self.allowed_operations
            or not self.allowed_entity_types
            or not self.allowed_relation_types
            or self.entry_validator_id is None
            or self.exit_validator_id is None
            or self.instruction_bundle_id is None
            or self.instruction_bundle_hash is None
        ):
            raise ValueError(
                "enabled v2 routes require operation/entity/relation allowlists "
                "and a hashed instruction bundle"
            )
        unknown_outputs = {
            item.entity_type for item in self.required_output_entities
        }.difference(self.allowed_entity_types)
        if unknown_outputs:
            raise ValueError(
                "required v2 output entity types must be allowed route outputs"
            )
        unknown_relations = {
            item.relation_type for item in self.required_output_relations
        }.difference(self.allowed_relation_types)
        if unknown_relations:
            raise ValueError(
                "required v2 output relation types must be allowed route outputs"
            )
        return self


class RouteRegistryV2(StrictModel):
    registry_version: Literal[2] = 2
    aliases: dict[StableId, StableId] = Field(default_factory=dict)
    routes: Annotated[tuple[RouteSpecV2, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _route_ids_are_unique(self) -> "RouteRegistryV2":
        route_ids = [route.route_id for route in self.routes]
        if len(set(route_ids)) != len(route_ids):
            raise ValueError("route registry contains duplicate exact IDs")
        return self


RouteSpecLike: TypeAlias = RouteSpec | RouteSpecV2
RouteRegistryLike: TypeAlias = RouteRegistry | RouteRegistryV2


class StaleDependencyEvidence(StrictModel):
    relation_id: StableId
    relation_version: Annotated[int, Field(ge=1)]
    dependency_mode: DependencyMode
    upstream: SemanticFacetRef
    current_upstream_version: Annotated[int, Field(ge=1)] | None = None
    current_semantic_hash: Digest | None = None


class StaleReason(StaleDependencyEvidence):
    inherited_from: FacetPathRef | None = None
    message: NonEmptyString
    source_evidence: Annotated[
        tuple[StaleDependencyEvidence, ...], Field(min_length=1)
    ]

    @field_validator("source_evidence")
    @classmethod
    def _source_evidence_is_exact_and_canonical(
        cls, value: tuple[StaleDependencyEvidence, ...]
    ) -> tuple[StaleDependencyEvidence, ...]:
        keys = [
            (
                item.relation_id,
                item.relation_version,
                item.upstream.entity_id,
                item.upstream.version,
                item.upstream.facet,
                item.upstream.field_path or "",
                item.upstream.semantic_hash,
                item.current_upstream_version or 0,
                item.current_semantic_hash or "",
            )
            for item in value
        ]
        if len(set(keys)) != len(keys):
            raise ValueError("stale source_evidence must not repeat exact evidence")
        if keys != sorted(keys):
            raise ValueError("stale source_evidence must be canonically ordered")
        return value


class EntityDerivedStatus(StrictModel):
    human_acceptance: HumanAcceptance = "agent_proposed"
    acceptance_by_kind: dict[DecisionKind, HumanAcceptance] = Field(
        default_factory=dict
    )
    acceptance_source_refs: dict[
        DecisionKind, tuple[DecisionVersionRef, ...]
    ] = Field(default_factory=dict)
    freshness: dict[Facet, Freshness] = Field(default_factory=dict)
    stale_reasons: dict[Facet, tuple[StaleReason, ...]] = Field(
        default_factory=dict
    )

    @model_validator(mode="after")
    def _acceptance_projection_has_exact_sources(self) -> "EntityDerivedStatus":
        if set(self.acceptance_by_kind) != set(self.acceptance_source_refs):
            raise ValueError(
                "every per-kind acceptance projection requires exact Decision sources"
            )
        for kind, references in self.acceptance_source_refs.items():
            if not references:
                raise ValueError(f"acceptance source list is empty for {kind}")
            keys = [
                (reference.decision_id, reference.version)
                for reference in references
            ]
            if len(set(keys)) != len(keys):
                raise ValueError(f"acceptance sources repeat a Decision for {kind}")
            if keys != sorted(keys):
                raise ValueError(f"acceptance sources are not canonical for {kind}")
        return self


class Snapshot(StrictModel):
    """Rebuildable materialized projection of one reachable transaction chain."""

    snapshot_schema: Literal[1] = 1
    project_id: StableId
    head: Digest
    chain: tuple[Digest, ...]
    transaction_ids: tuple[StableId, ...] = ()
    provenance_hashes: tuple[Digest, ...] = ()
    entity_versions: tuple[EntityVersion, ...] = ()
    relation_versions: tuple[RelationVersion, ...] = ()
    decisions: tuple[Decision, ...] = ()
    artifacts: tuple[ArtifactRegistration, ...] = ()
    route_outcomes: tuple[RouteOutcome, ...] = ()
    blockers: tuple[RiskOrBlocker, ...] = ()
    current_entities: dict[StableId, Annotated[int, Field(ge=1)]] = Field(
        default_factory=dict
    )
    current_relations: dict[StableId, Annotated[int, Field(ge=1)]] = Field(
        default_factory=dict
    )
    current_decisions: dict[StableId, Annotated[int, Field(ge=1)]] = Field(
        default_factory=dict
    )
    current_artifacts: dict[StableId, Annotated[int, Field(ge=1)]] = Field(
        default_factory=dict
    )
    effective_decisions: dict[str, EffectiveDecisionRef] = Field(default_factory=dict)
    derived_status: dict[StableId, EntityDerivedStatus] = Field(default_factory=dict)


class ContextManifest(StrictModel):
    manifest_schema: Literal[1] = 1
    context_manifest_id: StableId
    project_id: StableId
    source_head: Digest
    route_id: StableId
    route_version: Annotated[int, Field(ge=1)]
    route_registry_hash: Digest
    decision_registry_version: Annotated[int, Field(ge=1)]
    validator_version: StableId
    selector_version: StableId
    kernel_version: StableId
    kernel_hash: Digest
    instruction_bundle_id: StableId
    instruction_bundle_hash: Digest
    isolation_policy: StableId
    write_allowlist: tuple[StableId, ...]
    purpose: StableId
    actor: Actor
    focus_entity_ids: tuple[StableId, ...] = ()
    selected_entity_refs: tuple[EntityVersionRef, ...] = ()
    compartments: tuple[StableId, ...] = ()
    privacy_clearance: PrivacyLabel = "project_private"
    tokenizer_id: Literal["etai_lexical_v1"] = "etai_lexical_v1"
    budget_units: Annotated[int, Field(ge=1)]
    used_units: Annotated[int, Field(ge=0)]
    omissions: tuple[NonEmptyString, ...] = ()
    context_hash: Digest
    created_at: NonEmptyString


class RouteRun(StrictModel):
    run_schema: Literal[1] = 1
    route_run_id: StableId
    project_id: StableId
    base_revision: Digest
    route_id: StableId
    route_version: Annotated[int, Field(ge=1)]
    actor: Actor
    purpose: StableId
    compartments: tuple[StableId, ...]
    privacy_clearance: PrivacyLabel
    focus_entity_ids: tuple[StableId, ...] = ()
    context_manifest_id: StableId
    context_hash: Digest
    status: Literal["running"]
    created_at: NonEmptyString
