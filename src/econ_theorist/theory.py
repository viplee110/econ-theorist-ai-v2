"""Typed canonical payloads for the Phase 2 positive-theory kernel.

The Phase 1 :class:`~econ_theorist.models.EntityVersion` envelope remains the
canonical storage object.  This module gives selected ``entity_type`` values a
versioned, strict payload contract and assigns each contract to exactly one of
the five semantic facets.  It deliberately describes admissible scientific
records; it does *not* let a payload certify freshness, formal validity,
economic validity, novelty, human acceptance, or argument validation.
"""

from __future__ import annotations

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
    StableId,
    StrictModel,
)


PositiveInt: TypeAlias = Annotated[int, Field(ge=1)]
ExactEvidenceRef: TypeAlias = (
    EntityVersionRef | ArtifactDependencyRef | DecisionVersionRef
)
ResultArchetype: TypeAlias = Literal[
    "mechanism_explanation",
    "comparative_statics_threshold",
    "characterization_bounds",
    "robustness_invariance_equivalence",
    "design_implementation_impossibility",
    "concept_representation_foundation",
]
GateKind: TypeAlias = Literal[
    "G1_question_benchmark",
    "G2_mechanism",
    "G3_formal_base",
    "G4_result_investment",
    "G5_argument_validation",
]


def _unique(values: tuple[object, ...], keys: tuple[object, ...], label: str) -> None:
    if len(set(keys)) != len(values):
        raise ValueError(f"{label} must be unique")


def _unique_stable_ids(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    _unique(values, values, label)
    return values


def _unique_entity_refs(
    values: tuple[EntityVersionRef, ...], label: str
) -> tuple[EntityVersionRef, ...]:
    keys = tuple((item.entity_id, item.version) for item in values)
    _unique(values, keys, label)
    return values


def _unique_artifact_refs(
    values: tuple[ArtifactDependencyRef, ...], label: str
) -> tuple[ArtifactDependencyRef, ...]:
    keys = tuple((item.artifact_id, item.version, item.content_hash) for item in values)
    _unique(values, keys, label)
    return values


class TheoryPayload(StrictModel):
    """Base for every payload registered as a Phase 2 entity type."""

    schema_version: Literal[1] = 1


class ReducedRational(StrictModel):
    """An exact canonical rational: positive denominator and reduced terms."""

    numerator: int
    denominator: PositiveInt

    @model_validator(mode="after")
    def _is_reduced_with_canonical_zero(self) -> "ReducedRational":
        if self.numerator == 0 and self.denominator != 1:
            raise ValueError("zero must be encoded as 0/1")
        if gcd(abs(self.numerator), self.denominator) != 1:
            raise ValueError("rational numerator and denominator must be coprime")
        return self


class RationalAssignment(StrictModel):
    symbol: StableId
    value: ReducedRational


class ResearchQuestion(TheoryPayload):
    phenomenon: NonEmptyString
    object_to_explain: NonEmptyString
    unresolved_delta: NonEmptyString
    importance: NonEmptyString
    kill_condition: NonEmptyString
    proposed_scope: NonEmptyString
    candidate_archetypes: Annotated[tuple[ResultArchetype, ...], Field(min_length=1)]
    prohibited_claims: tuple[NonEmptyString, ...] = ()

    @field_validator("candidate_archetypes")
    @classmethod
    def _candidate_archetypes_are_unique(
        cls, value: tuple[ResultArchetype, ...]
    ) -> tuple[ResultArchetype, ...]:
        _unique(value, value, "candidate archetypes")
        return value


class BenchmarkRecord(StrictModel):
    benchmark_id: StableId
    label: NonEmptyString
    exact_primitives: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    timing: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    solution_concept: NonEmptyString
    prediction: NonEmptyString
    unresolved_delta: NonEmptyString
    exact_values: tuple[RationalAssignment, ...] = ()
    evidence_refs: tuple[ArtifactDependencyRef, ...] = ()

    @field_validator("evidence_refs")
    @classmethod
    def _evidence_is_unique(
        cls, value: tuple[ArtifactDependencyRef, ...]
    ) -> tuple[ArtifactDependencyRef, ...]:
        return _unique_artifact_refs(value, "benchmark evidence refs")


class BenchmarkSet(TheoryPayload):
    question_ref: EntityVersionRef
    benchmarks: Annotated[tuple[BenchmarkRecord, ...], Field(min_length=1)]
    exact_question_delta: NonEmptyString

    @field_validator("benchmarks")
    @classmethod
    def _benchmark_ids_are_unique(
        cls, value: tuple[BenchmarkRecord, ...]
    ) -> tuple[BenchmarkRecord, ...]:
        _unique(value, tuple(item.benchmark_id for item in value), "benchmark IDs")
        return value


PrimitiveKind: TypeAlias = Literal[
    "actor",
    "choice",
    "constraint",
    "information",
    "timing",
    "institution",
    "preference_technology",
    "interaction",
    "equilibrium_object",
    "perturbation",
    "outcome",
]


class PrimitiveNode(StrictModel):
    node_id: StableId
    kind: PrimitiveKind
    label: NonEmptyString
    economic_meaning: NonEmptyString
    status: Literal["primitive", "reduced_form", "derived", "unresolved_scope_cost"]
    primitive_sufficient_conditions: tuple[NonEmptyString, ...] = ()


class PrimitiveEdge(StrictModel):
    edge_id: StableId
    source_node_id: StableId
    target_node_id: StableId
    economic_meaning: NonEmptyString


class PrimitiveGraph(TheoryPayload):
    question_ref: EntityVersionRef
    benchmark_set_ref: EntityVersionRef
    nodes: Annotated[tuple[PrimitiveNode, ...], Field(min_length=1)]
    edges: tuple[PrimitiveEdge, ...] = ()

    @model_validator(mode="after")
    def _graph_is_closed(self) -> "PrimitiveGraph":
        node_ids = tuple(item.node_id for item in self.nodes)
        _unique(self.nodes, node_ids, "primitive node IDs")
        _unique(self.edges, tuple(item.edge_id for item in self.edges), "primitive edge IDs")
        known = set(node_ids)
        for edge in self.edges:
            if edge.source_node_id not in known or edge.target_node_id not in known:
                raise ValueError("primitive edge endpoint is not a graph node")
        return self


class MechanismStep(StrictModel):
    step_id: StableId
    source: NonEmptyString
    response_or_constraint: NonEmptyString
    target: NonEmptyString
    economic_meaning: NonEmptyString
    effect_kind: Literal[
        "direct", "feedback", "constraint", "transformation", "conflict"
    ]


class MechanismHypothesis(TheoryPayload):
    question_ref: EntityVersionRef
    primitive_graph_ref: EntityVersionRef
    decision_margin_or_foundational_distinction: NonEmptyString
    initiating_wedge: NonEmptyString
    force_chain: Annotated[tuple[MechanismStep, ...], Field(min_length=1)]
    predicted_consequence: NonEmptyString
    boundary: NonEmptyString
    expected_load_bearing_conditions: Annotated[
        tuple[NonEmptyString, ...], Field(min_length=1)
    ]
    distinguishing_signature: NonEmptyString
    killer_test: NonEmptyString

    @field_validator("force_chain")
    @classmethod
    def _step_ids_are_unique(
        cls, value: tuple[MechanismStep, ...]
    ) -> tuple[MechanismStep, ...]:
        _unique(value, tuple(item.step_id for item in value), "mechanism step IDs")
        return value


class MechanismPairComparison(StrictModel):
    left_ref: EntityVersionRef
    right_ref: EntityVersionRef
    distinct_arrow_or_signature: NonEmptyString
    decisive_test: NonEmptyString

    @model_validator(mode="after")
    def _compares_distinct_hypotheses(self) -> "MechanismPairComparison":
        if self.left_ref == self.right_ref:
            raise ValueError("mechanism comparison must compare distinct exact refs")
        return self


class MechanismTournament(TheoryPayload):
    question_ref: EntityVersionRef
    hypothesis_refs: Annotated[tuple[EntityVersionRef, ...], Field(min_length=1)]
    comparisons: tuple[MechanismPairComparison, ...] = ()
    proposed_selected_ref: EntityVersionRef | None = None
    serious_rival_refs: tuple[EntityVersionRef, ...] = ()
    rivalry_waiver_ref: ArtifactDependencyRef | None = None
    selection_rationale: NonEmptyString | None = None

    @model_validator(mode="after")
    def _references_tournament_members(self) -> "MechanismTournament":
        _unique_entity_refs(self.hypothesis_refs, "mechanism hypothesis refs")
        _unique_entity_refs(self.serious_rival_refs, "serious rival refs")
        members = set(self.hypothesis_refs)
        if self.proposed_selected_ref is not None:
            if self.proposed_selected_ref not in members:
                raise ValueError("proposed mechanism is not a tournament member")
            if self.selection_rationale is None:
                raise ValueError("a proposed mechanism requires selection rationale")
        for rival in self.serious_rival_refs:
            if rival not in members or rival == self.proposed_selected_ref:
                raise ValueError("serious rival must be a distinct tournament member")
        for comparison in self.comparisons:
            if comparison.left_ref not in members or comparison.right_ref not in members:
                raise ValueError("mechanism comparison references a nonmember")
        if self.proposed_selected_ref is not None and not self.serious_rival_refs:
            if self.rivalry_waiver_ref is None:
                raise ValueError("proposed selection requires a serious rival or exact waiver")
        elif self.rivalry_waiver_ref is not None:
            raise ValueError("rivalry waiver is valid only when no serious rival is recorded")
        return self


class FrozenPrediction(StrictModel):
    prediction_id: StableId
    hypothesis_ref: EntityVersionRef
    predicted_result: NonEmptyString
    proposed_economic_chain: Annotated[
        tuple[NonEmptyString, ...], Field(min_length=1)
    ]
    expected_conditions: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    expected_ablation_outcome: NonEmptyString
    expected_rival_difference: NonEmptyString
    surprise_or_falsifier: NonEmptyString
    frozen_at: NonEmptyString
    origin: Literal["prospective"] = "prospective"


ReconciliationOutcome: TypeAlias = Literal[
    "confirmed",
    "right_result_wrong_reason",
    "informative_failure",
    "non_discriminating",
    "implementation_failure",
    "unresolved",
]


class PredictionReconciliation(StrictModel):
    reconciliation_id: StableId
    prediction_id: StableId
    outcome: ReconciliationOutcome
    observed_result: NonEmptyString
    mechanism_diagnosis: NonEmptyString
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    recorded_at: NonEmptyString


class PredictionRegister(TheoryPayload):
    question_ref: EntityVersionRef
    mechanism_tournament_ref: EntityVersionRef
    original_predictions: Annotated[tuple[FrozenPrediction, ...], Field(min_length=1)]
    reconciliations: tuple[PredictionReconciliation, ...] = ()

    @model_validator(mode="after")
    def _reconciliations_bind_frozen_predictions(self) -> "PredictionRegister":
        prediction_ids = tuple(item.prediction_id for item in self.original_predictions)
        _unique(self.original_predictions, prediction_ids, "frozen prediction IDs")
        reconciliation_ids = tuple(
            item.reconciliation_id for item in self.reconciliations
        )
        _unique(self.reconciliations, reconciliation_ids, "reconciliation IDs")
        known = set(prediction_ids)
        for reconciliation in self.reconciliations:
            if reconciliation.prediction_id not in known:
                raise ValueError("reconciliation references an unknown frozen prediction")
        return self


def validate_prediction_register_update(
    previous: PredictionRegister, current: PredictionRegister
) -> None:
    """Reject edits to frozen predictions or prior reconciliation history.

    A superseding register may only append reconciliation records.  The return
    value is intentionally ``None``: this function validates history; it does
    not derive whether a prediction or mechanism is scientifically confirmed.
    """

    if previous.question_ref != current.question_ref:
        raise ValueError("prediction register question_ref is immutable")
    if previous.mechanism_tournament_ref != current.mechanism_tournament_ref:
        raise ValueError("prediction register mechanism_tournament_ref is immutable")
    if previous.original_predictions != current.original_predictions:
        raise ValueError("original frozen predictions are immutable")
    prefix_length = len(previous.reconciliations)
    if current.reconciliations[:prefix_length] != previous.reconciliations:
        raise ValueError("prediction reconciliation history is append-only")
    if len(current.reconciliations) < prefix_length:
        raise ValueError("prediction reconciliation history cannot be truncated")


ExampleRole: TypeAlias = Literal[
    "benchmark",
    "mechanism_on",
    "ablation",
    "rival_separator",
    "boundary",
    "failure",
    "tightness",
    "independence",
]


class ExampleCase(StrictModel):
    case_id: StableId
    roles: Annotated[tuple[ExampleRole, ...], Field(min_length=1)]
    setup: NonEmptyString
    exact_values: tuple[RationalAssignment, ...] = ()
    primitive_to_choice_trace: Annotated[
        tuple[NonEmptyString, ...], Field(min_length=1)
    ]
    interaction_to_outcome_trace: Annotated[
        tuple[NonEmptyString, ...], Field(min_length=1)
    ]
    result: NonEmptyString
    method: Literal["hand_solved", "symbolic", "enumeration", "simulation"]
    solution_artifact_ref: ArtifactDependencyRef
    assumption_ids: tuple[StableId, ...] = ()

    @field_validator("roles")
    @classmethod
    def _roles_are_unique(
        cls, value: tuple[ExampleRole, ...]
    ) -> tuple[ExampleRole, ...]:
        _unique(value, value, "example roles")
        return value


class ExampleSuite(TheoryPayload):
    selected_mechanism_ref: EntityVersionRef
    frozen_prediction_register_ref: EntityVersionRef
    cases: Annotated[tuple[ExampleCase, ...], Field(min_length=1)]

    @field_validator("cases")
    @classmethod
    def _case_ids_are_unique(
        cls, value: tuple[ExampleCase, ...]
    ) -> tuple[ExampleCase, ...]:
        _unique(value, tuple(item.case_id for item in value), "example case IDs")
        return value


class EconomicArgumentNode(StrictModel):
    node_id: StableId
    kind: Literal[
        "primitive",
        "assumption",
        "margin",
        "response",
        "constraint",
        "feedback",
        "equilibrium_consequence",
        "outcome",
    ]
    statement: NonEmptyString


class EconomicArgumentEdge(StrictModel):
    edge_id: StableId
    source_node_id: StableId
    target_node_id: StableId
    economic_meaning: NonEmptyString
    effect_kind: Literal["direct", "equilibrium_feedback", "logical"]
    load_bearing: bool
    primitive_or_assumption_refs: Annotated[
        tuple[EntityVersionRef, ...], Field(min_length=1)
    ]
    formal_witness_refs: tuple[ExactEvidenceRef, ...] = ()
    supporting_case_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    conclusion_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]


class EconomicArgumentGraph(TheoryPayload):
    selected_mechanism_ref: EntityVersionRef
    primitive_graph_ref: EntityVersionRef
    prediction_register_ref: EntityVersionRef
    example_suite_ref: EntityVersionRef
    nodes: Annotated[tuple[EconomicArgumentNode, ...], Field(min_length=1)]
    edges: Annotated[tuple[EconomicArgumentEdge, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _argument_graph_is_closed(self) -> "EconomicArgumentGraph":
        node_ids = tuple(item.node_id for item in self.nodes)
        edge_ids = tuple(item.edge_id for item in self.edges)
        _unique(self.nodes, node_ids, "economic argument node IDs")
        _unique(self.edges, edge_ids, "economic argument edge IDs")
        known = set(node_ids)
        for edge in self.edges:
            if edge.source_node_id not in known or edge.target_node_id not in known:
                raise ValueError("economic argument edge endpoint is not a graph node")
        return self


class ImplementationPairComparison(StrictModel):
    left_model_ref: EntityVersionRef
    right_model_ref: EntityVersionRef
    fidelity_difference: NonEmptyString
    minimality_difference: NonEmptyString
    proof_risk_difference: NonEmptyString
    mapping_transparency_difference: NonEmptyString
    theorem_leverage_difference: NonEmptyString

    @model_validator(mode="after")
    def _compares_distinct_models(self) -> "ImplementationPairComparison":
        if self.left_model_ref == self.right_model_ref:
            raise ValueError("implementation comparison requires distinct model refs")
        return self


class ImplementationTournament(TheoryPayload):
    selected_mechanism_ref: EntityVersionRef
    economic_argument_graph_ref: EntityVersionRef
    candidate_model_refs: Annotated[tuple[EntityVersionRef, ...], Field(min_length=1)]
    comparisons: tuple[ImplementationPairComparison, ...] = ()
    proposed_selected_model_ref: EntityVersionRef | None = None
    contrast_model_refs: tuple[EntityVersionRef, ...] = ()
    contrast_waiver_ref: ArtifactDependencyRef | None = None
    selection_rationale: NonEmptyString | None = None

    @model_validator(mode="after")
    def _selection_and_contrasts_are_members(self) -> "ImplementationTournament":
        _unique_entity_refs(self.candidate_model_refs, "candidate model refs")
        _unique_entity_refs(self.contrast_model_refs, "contrast model refs")
        members = set(self.candidate_model_refs)
        if self.proposed_selected_model_ref is not None:
            if self.proposed_selected_model_ref not in members:
                raise ValueError("proposed formal model is not a tournament member")
            if self.selection_rationale is None:
                raise ValueError("proposed formal model requires selection rationale")
        for contrast in self.contrast_model_refs:
            if contrast not in members or contrast == self.proposed_selected_model_ref:
                raise ValueError("contrast model must be a distinct tournament member")
        for comparison in self.comparisons:
            if (
                comparison.left_model_ref not in members
                or comparison.right_model_ref not in members
            ):
                raise ValueError("implementation comparison references a nonmember")
        if self.proposed_selected_model_ref is not None and not self.contrast_model_refs:
            if self.contrast_waiver_ref is None:
                raise ValueError("formal selection requires a contrast or exact waiver")
        elif self.contrast_waiver_ref is not None:
            raise ValueError("contrast waiver is valid only without a contrast model")
        return self


class FormalObject(StrictModel):
    object_id: StableId
    symbol: NonEmptyString
    object_kind: Literal[
        "agent",
        "state",
        "parameter",
        "choice",
        "strategy",
        "information",
        "belief",
        "constraint",
        "payoff",
        "technology",
        "solution_object",
        "outcome",
    ]
    definition: NonEmptyString
    central: bool


class FormalModel(TheoryPayload):
    question_ref: EntityVersionRef
    selected_mechanism_ref: EntityVersionRef
    primitive_graph_ref: EntityVersionRef
    formal_objects: Annotated[tuple[FormalObject, ...], Field(min_length=1)]
    timing: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    choice_or_strategy_spaces: Annotated[
        tuple[NonEmptyString, ...], Field(min_length=1)
    ]
    information_and_beliefs: tuple[NonEmptyString, ...] = ()
    feasibility: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    solution_concept: NonEmptyString
    outcome_definitions: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    full_specification_ref: ArtifactDependencyRef

    @field_validator("formal_objects")
    @classmethod
    def _formal_object_ids_are_unique(
        cls, value: tuple[FormalObject, ...]
    ) -> tuple[FormalObject, ...]:
        _unique(value, tuple(item.object_id for item in value), "formal object IDs")
        return value


class EconomicToFormalEntry(StrictModel):
    economic_element_id: StableId
    formal_object_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    implementation_statement: NonEmptyString
    witness_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]

    @field_validator("formal_object_ids")
    @classmethod
    def _formal_ids_are_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _unique_stable_ids(value, "formal object IDs in mapping")


class FormalToEconomicEntry(StrictModel):
    formal_object_id: StableId
    economic_identity: NonEmptyString
    research_job: NonEmptyString
    economic_element_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]

    @field_validator("economic_element_ids")
    @classmethod
    def _economic_ids_are_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        return _unique_stable_ids(value, "economic element IDs in mapping")


class FormalizationMap(TheoryPayload):
    economic_argument_graph_ref: EntityVersionRef
    formal_model_ref: EntityVersionRef
    economic_to_formal: Annotated[
        tuple[EconomicToFormalEntry, ...], Field(min_length=1)
    ]
    formal_to_economic: Annotated[
        tuple[FormalToEconomicEntry, ...], Field(min_length=1)
    ]

    @model_validator(mode="after")
    def _mapping_keys_are_unique(self) -> "FormalizationMap":
        _unique(
            self.economic_to_formal,
            tuple(item.economic_element_id for item in self.economic_to_formal),
            "economic-to-formal mapping keys",
        )
        _unique(
            self.formal_to_economic,
            tuple(item.formal_object_id for item in self.formal_to_economic),
            "formal-to-economic mapping keys",
        )
        return self


AssumptionRole: TypeAlias = Literal[
    "definition",
    "mechanism",
    "existence",
    "uniqueness",
    "selection",
    "tractability",
    "regularity",
    "sign",
    "domain",
]


class AssumptionRecord(StrictModel):
    assumption_id: StableId
    exact_content: NonEmptyString
    quantifiers: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    economic_interpretation: NonEmptyString
    foundation: Literal["primitive", "reduced_form"]
    roles: Annotated[tuple[AssumptionRole, ...], Field(min_length=1)]
    dependent_claim_ids: tuple[StableId, ...] = ()
    proof_obligation_ids: tuple[StableId, ...] = ()
    argument_edge_ids: tuple[StableId, ...] = ()
    satisfying_case_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    weakening_attempts: tuple[NonEmptyString, ...] = ()
    violation_attempts: tuple[NonEmptyString, ...] = ()
    primitive_sufficient_conditions: tuple[NonEmptyString, ...] = ()
    scope_cost: NonEmptyString
    necessity_status: Literal[
        "result_necessary", "proof_only", "unknown", "not_result_necessary"
    ]
    necessity_evidence_refs: tuple[ExactEvidenceRef, ...] = ()

    @model_validator(mode="after")
    def _necessity_claim_has_evidence(self) -> "AssumptionRecord":
        if self.necessity_status == "result_necessary" and not self.necessity_evidence_refs:
            raise ValueError("result necessity requires exact evidence")
        return self


class AssumptionMap(TheoryPayload):
    formal_model_ref: EntityVersionRef
    formalization_map_ref: EntityVersionRef
    assumptions: Annotated[tuple[AssumptionRecord, ...], Field(min_length=1)]

    @field_validator("assumptions")
    @classmethod
    def _assumption_ids_are_unique(
        cls, value: tuple[AssumptionRecord, ...]
    ) -> tuple[AssumptionRecord, ...]:
        _unique(value, tuple(item.assumption_id for item in value), "assumption IDs")
        return value


class ProofObligation(TheoryPayload):
    claim_graph_ref: EntityVersionRef
    claim_id: StableId
    obligation_id: StableId
    statement: NonEmptyString
    burden: Literal[
        "existence",
        "necessity",
        "sufficiency",
        "uniqueness",
        "comparative_static",
        "boundary",
        "counterexample_exclusion",
        "semantic_entailment",
        "mechanism_witness",
    ]
    quantifier_scope: NonEmptyString
    assumption_ids: tuple[StableId, ...]
    admissible_methods: Annotated[
        tuple[
            Literal[
                "analytic_proof",
                "formal_proof",
                "symbolic_identity",
                "exhaustive_finite_proof",
                "counterexample",
                "semantic_audit",
            ],
            ...,
        ],
        Field(min_length=1),
    ]


class VerificationRecord(TheoryPayload):
    obligation_ref: EntityVersionRef
    claim_graph_ref: EntityVersionRef
    formal_model_ref: EntityVersionRef
    assumption_map_ref: EntityVersionRef
    verifier: Actor
    method: Literal[
        "analytic_proof",
        "formal_proof",
        "symbolic_identity",
        "exhaustive_finite_proof",
        "finite_example",
        "enumeration",
        "simulation",
        "counterexample",
        "semantic_audit",
        "mechanism_audit",
    ]
    outcome: Literal["discharged", "failed", "inconclusive", "falsified"]
    checked_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    evidence_refs: Annotated[
        tuple[ArtifactDependencyRef, ...], Field(min_length=1)
    ]
    limitations: NonEmptyString
    checked_at: NonEmptyString


class ClaimNode(StrictModel):
    claim_id: StableId
    archetype: ResultArchetype
    scientific_job: Literal[
        "headline",
        "enabling",
        "decomposition",
        "necessity",
        "converse",
        "boundary",
        "robustness",
        "negative_result",
        "application",
    ]
    formal_statement: NonEmptyString
    domain: NonEmptyString
    quantifiers: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    assumption_ids: tuple[StableId, ...]
    semantic_translation: NonEmptyString
    dependency_refs: tuple[EntityVersionRef, ...]
    mechanism_ref: EntityVersionRef
    proof_obligation_refs: Annotated[
        tuple[EntityVersionRef, ...], Field(min_length=1)
    ]
    verification_record_refs: tuple[EntityVersionRef, ...] = ()
    closest_theory_map_ref: EntityVersionRef | None = None
    boundary_case_ids: tuple[StableId, ...] = ()


class ClaimDependencyEdge(StrictModel):
    source_claim_id: StableId
    target_claim_id: StableId
    dependency_kind: Literal[
        "logical", "enabling", "scope", "mechanism", "interpretation"
    ]


class ClaimGraph(TheoryPayload):
    formal_model_ref: EntityVersionRef
    formalization_map_ref: EntityVersionRef
    assumption_map_ref: EntityVersionRef
    claims: Annotated[tuple[ClaimNode, ...], Field(min_length=1)]
    dependency_edges: tuple[ClaimDependencyEdge, ...] = ()
    contribution_spine: Annotated[tuple[StableId, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _claim_graph_is_closed(self) -> "ClaimGraph":
        claim_ids = tuple(item.claim_id for item in self.claims)
        _unique(self.claims, claim_ids, "claim IDs")
        known = set(claim_ids)
        if len(set(self.contribution_spine)) != len(self.contribution_spine):
            raise ValueError("contribution spine cannot repeat a claim")
        if any(item not in known for item in self.contribution_spine):
            raise ValueError("contribution spine references an unknown claim")
        for edge in self.dependency_edges:
            if edge.source_claim_id not in known or edge.target_claim_id not in known:
                raise ValueError("claim dependency edge references an unknown claim")
            if edge.source_claim_id == edge.target_claim_id:
                raise ValueError("claim dependency edge cannot be a self-loop")
        return self


class VerificationBundle(TheoryPayload):
    claim_graph_ref: EntityVersionRef
    proof_obligation_refs: Annotated[
        tuple[EntityVersionRef, ...], Field(min_length=1)
    ]
    verification_record_refs: Annotated[
        tuple[EntityVersionRef, ...], Field(min_length=1)
    ]
    interpretation_evidence_refs: tuple[ExactEvidenceRef, ...] = ()
    counterexample_evidence_refs: tuple[ArtifactDependencyRef, ...] = ()

    @model_validator(mode="after")
    def _bundle_refs_are_unique(self) -> "VerificationBundle":
        _unique_entity_refs(self.proof_obligation_refs, "proof obligation refs")
        _unique_entity_refs(self.verification_record_refs, "verification record refs")
        _unique_artifact_refs(
            self.counterexample_evidence_refs, "counterexample evidence refs"
        )
        return self


class LiteratureAssertion(StrictModel):
    assertion_id: StableId
    assertion: NonEmptyString
    source_locator: NonEmptyString
    access_status: Literal["full_text", "abstract_only", "metadata_only"]
    evidence_ref: ArtifactDependencyRef
    verification_status: Literal["source_verified", "unverified"]
    inference: NonEmptyString | None = None


class LiteratureEvidence(TheoryPayload):
    question_ref: EntityVersionRef
    assertions: Annotated[tuple[LiteratureAssertion, ...], Field(min_length=1)]

    @field_validator("assertions")
    @classmethod
    def _assertion_ids_are_unique(
        cls, value: tuple[LiteratureAssertion, ...]
    ) -> tuple[LiteratureAssertion, ...]:
        _unique(value, tuple(item.assertion_id for item in value), "literature assertion IDs")
        return value


class ClosestTheoryDimension(StrictModel):
    dimension: Literal[
        "benchmark",
        "primitives",
        "timing",
        "solution_concept",
        "assumptions",
        "quantifiers",
        "formal_result",
        "economic_lesson",
    ]
    project_side: NonEmptyString
    comparator_side: NonEmptyString
    translation: NonEmptyString
    mapping_status: Literal["exact", "standard_argument", "fails", "unresolved"]
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]


class ClosestTheoryMap(TheoryPayload):
    claim_graph_ref: EntityVersionRef
    literature_evidence_ref: EntityVersionRef
    comparator_label: NonEmptyString
    dimensions: Annotated[tuple[ClosestTheoryDimension, ...], Field(min_length=1)]
    classification: Literal[
        "duplicate",
        "direct_corollary",
        "special_case",
        "generalization",
        "converse",
        "different_mechanism",
        "different_boundary",
        "application",
        "non_comparable",
        "unresolved",
    ]
    first_mapping_failure: NonEmptyString | None = None

    @field_validator("dimensions")
    @classmethod
    def _dimensions_are_unique(
        cls, value: tuple[ClosestTheoryDimension, ...]
    ) -> tuple[ClosestTheoryDimension, ...]:
        _unique(value, tuple(item.dimension for item in value), "closest-theory dimensions")
        return value


class AbsorptionAssessment(TheoryPayload):
    closest_theory_map_ref: EntityVersionRef
    central_claim_graph_ref: EntityVersionRef
    central_claim_id: StableId
    outcome: Literal[
        "nonabsorbed",
        "partially_absorbed",
        "application_only",
        "unresolved_evidence",
        "absorbed",
    ]
    rationale: NonEmptyString
    standard_argument_refs: tuple[ArtifactDependencyRef, ...] = ()
    first_mapping_failure: NonEmptyString | None = None
    recommended_route: Literal["mutate", "demote", "pivot", "park", "kill", "proceed"]

    @model_validator(mode="after")
    def _mapping_failure_matches_outcome(self) -> "AbsorptionAssessment":
        if self.outcome == "absorbed" and self.first_mapping_failure is not None:
            raise ValueError("absorbed assessment cannot claim a mapping failure")
        if self.outcome == "nonabsorbed" and self.first_mapping_failure is None:
            raise ValueError("nonabsorbed assessment requires the first mapping failure")
        if self.outcome == "absorbed" and self.recommended_route == "proceed":
            raise ValueError("absorbed assessment cannot recommend proceeding")
        return self


class PortfolioItem(StrictModel):
    claim_id: StableId
    scientific_job: NonEmptyString
    marginal_value: NonEmptyString


class ExcludedResult(StrictModel):
    claim_id: StableId
    exclusion_reason: NonEmptyString


class ResultPortfolio(TheoryPayload):
    claim_graph_ref: EntityVersionRef
    headline_claim_id: StableId
    included_results: Annotated[tuple[PortfolioItem, ...], Field(min_length=1)]
    excluded_results: tuple[ExcludedResult, ...] = ()
    economic_nugget: NonEmptyString
    reader_belief_update: NonEmptyString
    economic_consequence: NonEmptyString

    @model_validator(mode="after")
    def _portfolio_has_one_job_per_claim(self) -> "ResultPortfolio":
        included_ids = tuple(item.claim_id for item in self.included_results)
        excluded_ids = tuple(item.claim_id for item in self.excluded_results)
        _unique(self.included_results, included_ids, "included portfolio claim IDs")
        _unique(self.excluded_results, excluded_ids, "excluded portfolio claim IDs")
        if set(included_ids).intersection(excluded_ids):
            raise ValueError("a claim cannot be both included and excluded")
        if self.headline_claim_id not in included_ids:
            raise ValueError("headline claim must be included in the portfolio")
        return self


class GateRequirement(StrictModel):
    requirement_id: StableId
    description: NonEmptyString
    evidence_refs: tuple[ExactEvidenceRef, ...] = ()
    recorded_condition: Literal["evidence_supplied", "gap_disclosed", "risk_disclosed"]


class GateDossier(TheoryPayload):
    gate_kind: GateKind
    research_question_ref: EntityVersionRef
    ordered_object_refs: Annotated[
        tuple[EntityVersionRef, ...], Field(min_length=1)
    ]
    ordered_artifact_refs: tuple[ArtifactDependencyRef, ...] = ()
    requirements: Annotated[tuple[GateRequirement, ...], Field(min_length=1)]
    proposed_action: Literal[
        "approve",
        "revise",
        "reopen",
        "narrow",
        "mutate",
        "pivot",
        "park",
        "kill",
    ]
    rationale: NonEmptyString
    prepared_at: NonEmptyString

    @model_validator(mode="after")
    def _ordered_refs_and_requirements_are_unique(self) -> "GateDossier":
        _unique_entity_refs(self.ordered_object_refs, "ordered dossier object refs")
        if self.research_question_ref not in self.ordered_object_refs:
            raise ValueError(
                "the exact research_question_ref must appear in ordered_object_refs"
            )
        _unique_artifact_refs(self.ordered_artifact_refs, "ordered dossier artifact refs")
        _unique(
            self.requirements,
            tuple(item.requirement_id for item in self.requirements),
            "gate requirement IDs",
        )
        return self


class ValidatedArgumentPackage(TheoryPayload):
    question_ref: EntityVersionRef
    benchmark_set_ref: EntityVersionRef
    primitive_graph_ref: EntityVersionRef
    selected_mechanism_ref: EntityVersionRef
    serious_rejected_rival_refs: tuple[EntityVersionRef, ...]
    prediction_register_ref: EntityVersionRef
    example_suite_ref: EntityVersionRef
    economic_argument_graph_ref: EntityVersionRef
    implementation_tournament_ref: EntityVersionRef
    formal_model_ref: EntityVersionRef
    formalization_map_ref: EntityVersionRef
    assumption_map_ref: EntityVersionRef
    claim_graph_ref: EntityVersionRef
    verification_bundle_ref: EntityVersionRef
    closest_theory_map_ref: EntityVersionRef
    absorption_assessment_ref: EntityVersionRef
    result_portfolio_ref: EntityVersionRef
    prior_gate_decision_refs: Annotated[
        tuple[DecisionVersionRef, ...], Field(min_length=4, max_length=4)
    ]
    g5_dossier_ref: EntityVersionRef
    economic_nugget: NonEmptyString
    qualified_novelty: NonEmptyString
    unresolved_risks: tuple[NonEmptyString, ...]
    prohibited_overclaims: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    release_mode: Literal["production_candidate", "evaluation_only"]
    novelty_claim_mode: Literal["qualified", "none"]
    evaluation_attempt_id: StableId | None = None
    pre_result_brief_ref: EntityVersionRef | None = None
    generator_actor: Actor | None = None

    @model_validator(mode="after")
    def _package_mode_is_coherent(self) -> "ValidatedArgumentPackage":
        _unique_entity_refs(
            self.serious_rejected_rival_refs, "serious rejected rival refs"
        )
        decision_keys = tuple(
            (item.decision_id, item.version) for item in self.prior_gate_decision_refs
        )
        _unique(self.prior_gate_decision_refs, decision_keys, "prior gate decisions")
        if self.release_mode == "evaluation_only" and self.novelty_claim_mode != "none":
            raise ValueError("evaluation-only package cannot make an external novelty claim")
        evaluation_metadata = (
            self.evaluation_attempt_id,
            self.pre_result_brief_ref,
            self.generator_actor,
        )
        if any(item is not None for item in evaluation_metadata) and not all(
            item is not None for item in evaluation_metadata
        ):
            raise ValueError("blind evaluation metadata must be supplied as one complete set")
        if self.release_mode != "evaluation_only" and any(
            item is not None for item in evaluation_metadata
        ):
            raise ValueError("production packages cannot carry blind evaluation metadata")
        return self


class PreResultBrief(TheoryPayload):
    question_ref: EntityVersionRef
    benchmark_set_ref: EntityVersionRef
    primitive_graph_ref: EntityVersionRef
    institution: NonEmptyString
    allowed_context_refs: tuple[EntityVersionRef, ...]
    allowed_tools: tuple[StableId, ...]
    budget_units: PositiveInt
    excluded_information: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    attempt_id: StableId

    @model_validator(mode="after")
    def _brief_sets_are_unique(self) -> "PreResultBrief":
        _unique_entity_refs(self.allowed_context_refs, "allowed context refs")
        _unique_stable_ids(self.allowed_tools, "allowed tools")
        return self


class BlindCaseManifest(TheoryPayload):
    case_id: StableId
    layer: Literal["public_classic", "transformed", "synthetic_holdout"]
    pre_result_brief_ref: EntityVersionRef
    gold_package_ref: EntityVersionRef
    source_paper_refs: tuple[ArtifactDependencyRef, ...]
    gold_semantic_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    hidden_probe_refs: tuple[ArtifactDependencyRef, ...]
    answer_key_ref: ArtifactDependencyRef
    generator_compartments: Annotated[tuple[StableId, ...], Field(min_length=1)]
    evaluator_compartments: Annotated[tuple[StableId, ...], Field(min_length=1)]
    attempt_id: StableId

    @model_validator(mode="after")
    def _blind_compartments_are_separated(self) -> "BlindCaseManifest":
        _unique_artifact_refs(self.source_paper_refs, "source paper refs")
        _unique_artifact_refs(self.hidden_probe_refs, "hidden probe refs")
        _unique_stable_ids(self.generator_compartments, "generator compartments")
        _unique_stable_ids(self.evaluator_compartments, "evaluator compartments")
        if set(self.generator_compartments).intersection(self.evaluator_compartments):
            raise ValueError("generator and evaluator compartments must be disjoint")
        return self


class TransformOperation(StrictModel):
    operation_id: StableId
    kind: Literal[
        "semantic_rename",
        "label_permutation",
        "timing_change",
        "information_change",
        "parameter_transform",
    ]
    public_description: NonEmptyString
    exact_forward_map_ref: ArtifactDependencyRef


class TransformedVariantManifest(TheoryPayload):
    attempt_id: StableId
    base_case_manifest_ref: EntityVersionRef
    transformed_brief_ref: EntityVersionRef
    operations: Annotated[tuple[TransformOperation, ...], Field(min_length=1)]
    hidden_inverse_map_ref: ArtifactDependencyRef
    invariant_signature_ref: ArtifactDependencyRef
    implementation_freeze_ref: DecisionVersionRef
    generated_at: NonEmptyString

    @field_validator("operations")
    @classmethod
    def _transform_operation_ids_are_unique(
        cls, value: tuple[TransformOperation, ...]
    ) -> tuple[TransformOperation, ...]:
        _unique(value, tuple(item.operation_id for item in value), "transform operation IDs")
        return value


class SignatureDimensionComparison(StrictModel):
    dimension: Literal[
        "question_delta",
        "benchmarks",
        "mechanism_graph",
        "rivals",
        "frozen_predictions",
        "functional_examples",
        "implementations",
        "formalization",
        "claim_scope",
        "assumptions",
        "proof_obligations",
        "boundaries",
        "absorption",
        "portfolio",
        "gates",
        "prohibited_overclaims",
        "dependency_traces",
    ]
    candidate_signature_ref: ArtifactDependencyRef
    gold_signature_ref: ArtifactDependencyRef
    comparison: Literal["match", "partial", "mismatch", "not_applicable"]
    diagnostic: NonEmptyString


class VAPComparisonRecord(TheoryPayload):
    attempt_id: StableId
    case_manifest_ref: EntityVersionRef
    candidate_package_ref: EntityVersionRef
    gold_package_ref: EntityVersionRef
    candidate_package_hash: Digest
    candidate_lock_ref: ArtifactDependencyRef
    evaluator: Actor
    dimension_comparisons: Annotated[
        tuple[SignatureDimensionComparison, ...], Field(min_length=1)
    ]
    evaluator_evidence_refs: Annotated[
        tuple[ArtifactDependencyRef, ...], Field(min_length=1)
    ]
    disposition: Literal[
        "confirmatory_clean", "diagnostic_contaminated", "invalid_attempt"
    ]
    compared_at: NonEmptyString

    @field_validator("dimension_comparisons")
    @classmethod
    def _comparison_dimensions_are_unique(
        cls, value: tuple[SignatureDimensionComparison, ...]
    ) -> tuple[SignatureDimensionComparison, ...]:
        _unique(value, tuple(item.dimension for item in value), "comparison dimensions")
        return value


# One primary facet owns each typed payload.  Keeping the other four empty makes
# Phase 1 facet hashes meaningful and avoids silently coupling unrelated
# invalidation domains during this first vertical slice.
_ECONOMIC_TYPES = (
    ResearchQuestion,
    BenchmarkSet,
    PrimitiveGraph,
    MechanismHypothesis,
    MechanismTournament,
    PredictionRegister,
    ExampleSuite,
    EconomicArgumentGraph,
    PreResultBrief,
)
_FORMAL_TYPES = (
    ImplementationTournament,
    FormalModel,
    FormalizationMap,
    AssumptionMap,
    ProofObligation,
    VerificationRecord,
    ClaimGraph,
    VerificationBundle,
)
_LITERATURE_TYPES = (
    LiteratureEvidence,
    ClosestTheoryMap,
    AbsorptionAssessment,
    ResultPortfolio,
)
_AUTHORITY_TYPES = (
    GateDossier,
    ValidatedArgumentPackage,
    BlindCaseManifest,
    TransformedVariantManifest,
    VAPComparisonRecord,
)

_ALL_PAYLOAD_TYPES = (
    *_ECONOMIC_TYPES,
    *_FORMAL_TYPES,
    *_LITERATURE_TYPES,
    *_AUTHORITY_TYPES,
)

THEORY_PAYLOAD_MODELS: Mapping[str, type[TheoryPayload]] = MappingProxyType(
    {model.__name__: model for model in _ALL_PAYLOAD_TYPES}
)
THEORY_PAYLOAD_OWNER_FACETS: Mapping[str, Facet] = MappingProxyType(
    {
        **{model.__name__: "economic_interpretation" for model in _ECONOMIC_TYPES},
        **{model.__name__: "formal" for model in _FORMAL_TYPES},
        **{model.__name__: "literature_novelty" for model in _LITERATURE_TYPES},
        **{model.__name__: "authority" for model in _AUTHORITY_TYPES},
    }
)


def theory_schema_id(entity_type: str) -> str:
    if entity_type not in THEORY_PAYLOAD_MODELS:
        raise ValueError(f"unregistered Phase 2 entity_type: {entity_type}")
    return f"econ_theorist.theory/{entity_type}/v1"


def payload_entity_type(payload: TheoryPayload) -> str:
    entity_type = type(payload).__name__
    if THEORY_PAYLOAD_MODELS.get(entity_type) is not type(payload):
        raise ValueError(f"unregistered Phase 2 payload model: {type(payload).__name__}")
    return entity_type


def pack_theory_payload(payload: TheoryPayload) -> FacetPayloads:
    """Place a registered payload in its sole owner facet."""

    entity_type = payload_entity_type(payload)
    owner = THEORY_PAYLOAD_OWNER_FACETS[entity_type]
    facet_values: dict[str, object] = {
        "formal": {},
        "economic_interpretation": {},
        "literature_novelty": {},
        "terminology_presentation": {},
        "authority": {},
    }
    facet_values[owner] = {
        "schema": theory_schema_id(entity_type),
        "payload": payload.model_dump(mode="json", exclude_none=False),
    }
    return FacetPayloads.model_validate(facet_values)


def parse_theory_payload(
    entity_type: str, facets: FacetPayloads | Mapping[str, object]
) -> TheoryPayload:
    """Validate a five-facet envelope and return its registered typed payload."""

    model = THEORY_PAYLOAD_MODELS.get(entity_type)
    if model is None:
        raise ValueError(f"unregistered Phase 2 entity_type: {entity_type}")
    if not isinstance(facets, FacetPayloads):
        facets = FacetPayloads.model_validate(facets)
    owner = THEORY_PAYLOAD_OWNER_FACETS[entity_type]
    dumped = facets.model_dump(mode="python")
    for facet, value in dumped.items():
        if facet != owner and value != {}:
            raise ValueError(
                f"{entity_type} payload is owned by {owner}; facet {facet} must be empty"
            )
    wrapper = dumped[owner]
    if set(wrapper) != {"schema", "payload"}:
        raise ValueError("typed theory facet must contain exactly schema and payload")
    expected_schema = theory_schema_id(entity_type)
    if wrapper["schema"] != expected_schema:
        raise ValueError(
            f"typed theory schema mismatch: expected {expected_schema}"
        )
    payload_data = wrapper["payload"]
    if not isinstance(payload_data, dict):
        raise ValueError("typed theory payload must be a JSON object")
    # JSON validation preserves strict scalar typing while accepting JSON arrays
    # for canonical tuple fields.
    return model.model_validate_json(canonical_json_bytes(payload_data), strict=True)


def parse_theory_entity(entity: EntityVersion) -> TheoryPayload:
    """Parse one registered ``EntityVersion`` without changing its envelope."""

    return parse_theory_payload(entity.entity_type, entity.facets)


def is_packed_theory_entity(entity: EntityVersion) -> bool:
    """Whether an entity visibly opts into the versioned Phase 2 payload contract.

    Phase 1 allowed generic entity-type labels such as ``ResearchQuestion``.
    Those historical envelopes remain legacy objects unless the owner facet
    contains the exact Phase 2 schema wrapper. New v2 routes separately require
    every allowed theory output to parse, so this compatibility check cannot be
    used to smuggle an untyped v2 output.
    """

    owner = THEORY_PAYLOAD_OWNER_FACETS.get(entity.entity_type)
    if owner is None:
        return False
    value = getattr(entity.facets, owner)
    return (
        isinstance(value, dict)
        and set(value) == {"schema", "payload"}
        and value.get("schema") == theory_schema_id(entity.entity_type)
        and isinstance(value.get("payload"), dict)
    )


def validate_theory_payload_update(
    previous: TheoryPayload, current: TheoryPayload
) -> None:
    """Apply type-specific immutable-history rules for a superseding payload."""

    if type(previous) is not type(current):
        raise ValueError("a typed theory entity cannot change payload model")
    if isinstance(previous, PredictionRegister):
        validate_prediction_register_update(previous, current)


__all__ = [
    "AbsorptionAssessment",
    "AssumptionMap",
    "AssumptionRecord",
    "BenchmarkSet",
    "BlindCaseManifest",
    "ClaimGraph",
    "ClaimNode",
    "EconomicArgumentGraph",
    "EconomicArgumentEdge",
    "EconomicArgumentNode",
    "ExampleCase",
    "ExampleSuite",
    "FormalModel",
    "FormalizationMap",
    "FrozenPrediction",
    "GateDossier",
    "GateRequirement",
    "ImplementationTournament",
    "LiteratureEvidence",
    "ClosestTheoryMap",
    "MechanismHypothesis",
    "MechanismPairComparison",
    "MechanismTournament",
    "PredictionReconciliation",
    "PredictionRegister",
    "PreResultBrief",
    "PrimitiveGraph",
    "ProofObligation",
    "ReducedRational",
    "ResearchQuestion",
    "ResultPortfolio",
    "THEORY_PAYLOAD_MODELS",
    "THEORY_PAYLOAD_OWNER_FACETS",
    "TransformedVariantManifest",
    "VAPComparisonRecord",
    "ValidatedArgumentPackage",
    "VerificationBundle",
    "VerificationRecord",
    "pack_theory_payload",
    "parse_theory_entity",
    "is_packed_theory_entity",
    "parse_theory_payload",
    "payload_entity_type",
    "theory_schema_id",
    "validate_prediction_register_update",
    "validate_theory_payload_update",
]
