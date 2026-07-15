"""Strict canonical contracts for an economist-facing framing preflight.

This namespace records whether a proposed theory question can be explained as
an economic tension rather than only as a formal construction.  It is
deliberately independent from the route, policy, and runtime registries.  The
payload makes benchmark semantics and attribution risks explicit; it does not
certify that a result is true, novel, or publication ready.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Annotated, Literal, Mapping, TypeAlias

from pydantic import Field, field_validator, model_validator

from .codec import canonical_json_bytes
from .models import (
    EntityVersion,
    EntityVersionRef,
    Facet,
    FacetPayloads,
    NonEmptyString,
    StableId,
    StrictModel,
)
from .theory import BenchmarkSet, ResultArchetype


TensionKind: TypeAlias = Literal[
    "causal_channel",
    "force_conflict",
    "sign_or_threshold_reversal",
    "boundary_or_tightness",
    "invariance_or_equivalence",
    "design_tradeoff_or_impossibility",
    "conceptual_distinction_or_representation",
]
ForceRole: TypeAlias = Literal[
    "baseline_force",
    "countervailing_force",
    "equilibrium_feedback",
    "boundary_force",
]
ForceDirection: TypeAlias = Literal[
    "raises_target",
    "lowers_target",
    "changes_composition",
    "changes_constraint",
    "ambiguous",
]
SemanticLevel: TypeAlias = Literal[
    "primitive",
    "choice",
    "behavioral_response",
    "conditional_distribution",
    "transition_kernel",
    "stationary_distribution",
    "payoff_ledger",
    "equilibrium_object",
    "equilibrium_correspondence",
    "outcome",
    "aggregate",
]
FixingLevel: TypeAlias = Literal[
    "primitive",
    "choice",
    "policy_rule",
    "realized_behavior",
    "conditional_distribution",
    "transition_kernel",
    "stationary_distribution",
    "payoff_ledger",
    "equilibrium_object",
    "equilibrium_correspondence",
    "weighting_distribution",
    "aggregate",
]
WeightingDistributionStatus: TypeAlias = Literal[
    "fixed",
    "endogenous",
    "changed",
    "not_applicable",
    "unresolved",
]
SelectionAssuranceStatus: TypeAlias = Literal[
    "unique_equilibrium",
    "continuous_branch",
    "all_equilibria",
    "selector_only",
    "not_applicable",
    "unresolved",
]
AttributionStrength: TypeAlias = Literal[
    "clean",
    "qualified",
    "weak",
    "unresolved",
]
ChannelKind: TypeAlias = Literal[
    "active_response",
    "boundary_or_mapping",
    "diagnostic_only",
]
FramingGapCategory: TypeAlias = Literal[
    "benchmark_semantics",
    "aggregate_endogeneity",
    "equilibrium_selection",
    "reoptimization",
    "causal_attribution",
    "scope",
    "minimal_example",
    "other",
]
FramingProposedAction: TypeAlias = Literal[
    "ready_for_g1",
    "continue_diagnostic",
    "revise_framing",
]
MarginActivityStatus: TypeAlias = Literal["active", "inactive", "unresolved"]
FramingRepairTargetType: TypeAlias = Literal[
    "ResearchQuestion",
    "BenchmarkSet",
    "PrimitiveGraph",
]


MECHANISM_MARGIN_TENSION_KINDS = frozenset(
    {"causal_channel", "force_conflict", "sign_or_threshold_reversal"}
)


ARCHETYPE_TENSION_KINDS: Mapping[ResultArchetype, TensionKind] = MappingProxyType(
    {
        "mechanism_explanation": "force_conflict",
        "comparative_statics_threshold": "sign_or_threshold_reversal",
        "characterization_bounds": "boundary_or_tightness",
        "robustness_invariance_equivalence": "invariance_or_equivalence",
        "design_implementation_impossibility": "design_tradeoff_or_impossibility",
        "concept_representation_foundation": (
            "conceptual_distinction_or_representation"
        ),
    }
)


ARCHETYPE_ALLOWED_TENSION_KINDS: Mapping[
    ResultArchetype, frozenset[TensionKind]
] = MappingProxyType(
    {
        archetype: (
            frozenset(("causal_channel", "force_conflict"))
            if archetype == "mechanism_explanation"
            else frozenset((tension_kind,))
        )
        for archetype, tension_kind in ARCHETYPE_TENSION_KINDS.items()
    }
)


REOPTIMIZING_SEMANTIC_LEVELS = frozenset({"choice", "behavioral_response"})
ENDOGENOUS_ACTIVE_SEMANTIC_LEVELS = frozenset(
    {
        "choice",
        "behavioral_response",
        "conditional_distribution",
        "transition_kernel",
        "stationary_distribution",
        "equilibrium_object",
        "equilibrium_correspondence",
    }
)


def _unique(values: tuple[object, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


class FramingQualityPayload(StrictModel):
    """Base for the independent framing-quality payload namespace."""

    schema_version: Literal[1] = 1


class ArchetypeTension(StrictModel):
    """The reader's prior and the archetype-specific source of tension."""

    result_archetype: ResultArchetype
    tension_kind: TensionKind
    conventional_prediction: NonEmptyString
    countervailing_logic: NonEmptyString | None = None
    economic_puzzle: NonEmptyString
    resolution_target: NonEmptyString

    @model_validator(mode="after")
    def _kind_matches_archetype(self) -> "ArchetypeTension":
        allowed = ARCHETYPE_ALLOWED_TENSION_KINDS[self.result_archetype]
        if self.tension_kind not in allowed:
            raise ValueError(
                "tension_kind must be an exact allowed kind for result_archetype: "
                + ", ".join(sorted(allowed))
            )
        conflict = self.tension_kind in {
            "force_conflict",
            "sign_or_threshold_reversal",
        }
        if conflict and self.countervailing_logic is None:
            raise ValueError(
                "conflict and reversal tensions require countervailing_logic"
            )
        if self.tension_kind == "causal_channel" and self.countervailing_logic is not None:
            raise ValueError(
                "causal_channel must explain its active channel without inventing "
                "countervailing_logic"
            )
        return self


class EconomicForce(StrictModel):
    force_id: StableId
    label: NonEmptyString
    role: ForceRole
    operative_margin: NonEmptyString
    direction: ForceDirection
    economic_logic: NonEmptyString
    active_when: NonEmptyString
    source_node_id: StableId
    margin_node_id: StableId
    target_node_id: StableId


class ActiveMarginWitness(StrictModel):
    """A diagnostic payoff comparison for one choice-dependent mechanism link."""

    decision_node_id: StableId
    payoff_node_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    concrete_state: NonEmptyString
    decision_maker: NonEmptyString
    focal_action: NonEmptyString
    alternative_action: NonEmptyString
    focal_payoff: NonEmptyString
    alternative_payoff: NonEmptyString
    feasibility_basis: NonEmptyString
    best_response_inequality: NonEmptyString
    activity_status: MarginActivityStatus
    status_basis: NonEmptyString
    kill_condition: NonEmptyString

    @model_validator(mode="after")
    def _compares_distinct_actions(self) -> "ActiveMarginWitness":
        _unique(self.payoff_node_ids, "active-margin payoff node IDs")
        if self.focal_action == self.alternative_action:
            raise ValueError(
                "active_margin_witness: focal and alternative actions must differ"
            )
        return self


class CausalChainStep(StrictModel):
    step_number: Literal[1, 2, 3]
    force_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    cause: NonEmptyString
    endogenous_response: NonEmptyString
    consequence: NonEmptyString
    source_node_id: StableId
    target_node_id: StableId
    active_margin_witness: ActiveMarginWitness | None = None

    @field_validator("force_ids")
    @classmethod
    def _force_ids_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "causal-step force IDs")
        return value


class IllustrativeMinimalExample(StrictModel):
    """A mechanism illustration that is explicitly not formal evidence."""

    role: Literal["illustrative_only"] = "illustrative_only"
    title: NonEmptyString
    setup: NonEmptyString
    moving_primitive: NonEmptyString
    held_fixed: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    endogenous_responses: Annotated[
        tuple[NonEmptyString, ...], Field(min_length=1)
    ]
    predicted_pattern: NonEmptyString
    economic_intuition: NonEmptyString
    limitation: NonEmptyString
    cannot_establish: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]


class EconomistMemo(StrictModel):
    """Fields needed for a compact economist-facing framing memo."""

    headline: NonEmptyString
    opening_question: NonEmptyString
    benchmark_message: NonEmptyString
    tension_message: NonEmptyString
    mechanism_message: NonEmptyString
    result_preview: NonEmptyString
    contribution_message: NonEmptyString
    scope_condition: NonEmptyString
    reader_takeaway: NonEmptyString


class FramingObjectRef(StrictModel):
    """A reader label bound, when possible, to one primitive-graph node."""

    object_id: StableId
    label: NonEmptyString
    semantic_level: SemanticLevel
    primitive_node_id: StableId | None = None


class HeldFixedObjectRef(FramingObjectRef):
    fixing_level: FixingLevel


class AggregateInvarianceAssessment(StrictModel):
    aggregate_object: NonEmptyString
    pointwise_policy_fixed: bool
    weighting_distribution_status: WeightingDistributionStatus
    claims_aggregate_fixed: bool
    basis: NonEmptyString
    implication_for_attribution: NonEmptyString

    @model_validator(mode="after")
    def _aggregate_claim_has_sufficient_support(
        self,
    ) -> "AggregateInvarianceAssessment":
        supported = self.pointwise_policy_fixed and (
            self.weighting_distribution_status in {"fixed", "not_applicable"}
        )
        if self.claims_aggregate_fixed and not supported:
            raise ValueError(
                "aggregate_invariance_unsupported: a pointwise fixed policy does not "
                "hold an aggregate fixed when its weighting distribution can move"
            )
        return self


class SelectionAssurance(StrictModel):
    status: SelectionAssuranceStatus
    selection_rule: NonEmptyString
    basis: NonEmptyString
    implication_for_attribution: NonEmptyString


class BenchmarkFramingAssessment(StrictModel):
    """One semantic ledger row bound to a nested benchmark ID."""

    benchmark_id: StableId
    changed: Annotated[tuple[FramingObjectRef, ...], Field(min_length=1)]
    held_fixed: Annotated[tuple[HeldFixedObjectRef, ...], Field(min_length=1)]
    reoptimizing: tuple[FramingObjectRef, ...]
    still_endogenous: Annotated[
        tuple[FramingObjectRef, ...], Field(min_length=1)
    ]
    targets: Annotated[tuple[FramingObjectRef, ...], Field(min_length=1)]
    channel_kind: ChannelKind
    channel_path: Annotated[tuple[StableId, ...], Field(min_length=2)]
    channel_summary: NonEmptyString
    aggregate_invariance: AggregateInvarianceAssessment
    selection_assurance: SelectionAssurance
    attribution_strength: AttributionStrength
    attribution_basis: NonEmptyString

    @model_validator(mode="after")
    def _semantic_ledger_is_coherent(self) -> "BenchmarkFramingAssessment":
        groups = (
            (self.changed, "changed objects"),
            (self.held_fixed, "held-fixed objects"),
            (self.reoptimizing, "reoptimizing objects"),
            (self.still_endogenous, "still-endogenous objects"),
            (self.targets, "target objects"),
        )
        for values, label in groups:
            _unique(tuple(item.object_id for item in values), label)
        _unique(self.channel_path, "channel-path node IDs")

        held_ids = {item.object_id for item in self.held_fixed}
        movable_ids = {
            item.object_id
            for values in (self.changed, self.reoptimizing, self.still_endogenous)
            for item in values
        }
        if held_ids.intersection(movable_ids):
            raise ValueError(
                "fixed_endogenous_conflict: an object cannot be both held fixed and "
                "changed, reoptimizing, or still endogenous"
            )
        if self.channel_kind == "active_response" and not self.reoptimizing:
            active_endogenous = any(
                item.semantic_level in ENDOGENOUS_ACTIVE_SEMANTIC_LEVELS
                for item in self.still_endogenous
            )
            if not active_endogenous:
                raise ValueError(
                    "placebo_control: an active-response comparison records no "
                    "reoptimizing choice, endogenous transition, distribution, or "
                    "equilibrium response"
                )
        if any(
            item.semantic_level not in REOPTIMIZING_SEMANTIC_LEVELS
            for item in self.reoptimizing
        ):
            raise ValueError(
                "placebo_control: reoptimizing objects must be choices or behavioral "
                "responses"
            )
        if (
            self.channel_kind == "diagnostic_only"
            and self.attribution_strength not in {"weak", "unresolved"}
        ):
            raise ValueError(
                "diagnostic_only_attribution_overclaim: a diagnostic-only channel "
                "cannot claim clean or qualified causal attribution"
            )
        if (
            self.selection_assurance.status in {"selector_only", "unresolved"}
            and self.attribution_strength == "clean"
        ):
            raise ValueError(
                "selection_robustness_unsupported: selector-only or unresolved "
                "equilibrium comparisons cannot claim clean attribution"
            )
        return self


class FramingRepairTargetRef(StrictModel):
    entity_type: FramingRepairTargetType
    entity_ref: EntityVersionRef


class DisclosedFramingGap(StrictModel):
    gap_id: StableId
    category: FramingGapCategory
    description: NonEmptyString
    affected_benchmark_ids: tuple[StableId, ...] = ()
    repair_target_refs: tuple[FramingRepairTargetRef, ...] = ()
    consequence: NonEmptyString
    resolution_needed: NonEmptyString

    @field_validator("affected_benchmark_ids")
    @classmethod
    def _benchmark_ids_are_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        _unique(value, "gap benchmark IDs")
        return value

    @field_validator("repair_target_refs")
    @classmethod
    def _repair_targets_are_unique(
        cls, value: tuple[FramingRepairTargetRef, ...]
    ) -> tuple[FramingRepairTargetRef, ...]:
        _unique(
            tuple((item.entity_type, item.entity_ref) for item in value),
            "gap repair targets",
        )
        return value


class FramingQualityBundle(FramingQualityPayload):
    """Canonical preflight joining framing intuition to exact Phase 2 inputs."""

    research_question_ref: EntityVersionRef
    benchmark_set_ref: EntityVersionRef
    primitive_graph_ref: EntityVersionRef
    source_g1_dossier_ref: EntityVersionRef
    tension: ArchetypeTension
    forces: Annotated[tuple[EconomicForce, ...], Field(min_length=1)]
    causal_chain: Annotated[
        tuple[CausalChainStep, ...], Field(min_length=3, max_length=3)
    ]
    minimal_example: IllustrativeMinimalExample
    economist_memo: EconomistMemo
    benchmark_assessments: Annotated[
        tuple[BenchmarkFramingAssessment, ...], Field(min_length=1)
    ]
    disclosed_gaps: tuple[DisclosedFramingGap, ...]
    proposed_action: FramingProposedAction
    action_rationale: NonEmptyString

    @model_validator(mode="after")
    def _is_closed_and_noncompensatory(self) -> "FramingQualityBundle":
        exact_refs = (
            self.research_question_ref,
            self.benchmark_set_ref,
            self.primitive_graph_ref,
            self.source_g1_dossier_ref,
        )
        _unique(exact_refs, "framing-quality exact input refs")

        if self.tension.result_archetype not in ARCHETYPE_TENSION_KINDS:
            raise ValueError("unsupported result archetype")

        force_ids = tuple(item.force_id for item in self.forces)
        _unique(force_ids, "economic force IDs")
        if any(item.source_node_id == item.target_node_id for item in self.forces):
            raise ValueError(
                "causal_force_binding: an economic force must have a nonzero "
                "source-to-target path"
            )
        if self.tension.tension_kind in {
            "force_conflict",
            "sign_or_threshold_reversal",
        }:
            baseline = tuple(
                item for item in self.forces if item.role == "baseline_force"
            )
            countervailing = tuple(
                item for item in self.forces if item.role == "countervailing_force"
            )
            if not baseline or not countervailing:
                raise ValueError(
                    "conflict and sign-reversal tensions require a baseline_force "
                    "and a countervailing_force"
                )
            focal_forces = (*baseline, *countervailing)
            if len({item.target_node_id for item in focal_forces}) != 1:
                raise ValueError(
                    "baseline and countervailing forces must act on the same target"
                )
            baseline_directions = {item.direction for item in baseline}
            countervailing_directions = {item.direction for item in countervailing}
            opposite = (
                baseline_directions == {"raises_target"}
                and countervailing_directions == {"lowers_target"}
            ) or (
                baseline_directions == {"lowers_target"}
                and countervailing_directions == {"raises_target"}
            )
            if not opposite:
                raise ValueError(
                    "baseline and countervailing forces must have opposite directions"
                )

        if tuple(item.step_number for item in self.causal_chain) != (1, 2, 3):
            raise ValueError("causal_chain must contain ordered steps 1, 2, and 3")
        known_force_ids = set(force_ids)
        used_force_ids: set[str] = set()
        for step in self.causal_chain:
            if not set(step.force_ids).issubset(known_force_ids):
                raise ValueError("causal_chain references an unknown economic force")
            if step.source_node_id == step.target_node_id:
                raise ValueError(
                    "causal_force_binding: every causal-chain step must be nonzero"
                )
            used_force_ids.update(step.force_ids)
        if used_force_ids != known_force_ids:
            missing = sorted(known_force_ids.difference(used_force_ids))
            raise ValueError(
                "causal_force_binding: every declared economic force must appear in "
                "the causal chain; missing=" + ",".join(missing)
            )
        if self.tension.tension_kind in {
            "force_conflict",
            "sign_or_threshold_reversal",
        }:
            used_roles = {
                item.role for item in self.forces if item.force_id in used_force_ids
            }
            if not {"baseline_force", "countervailing_force"}.issubset(used_roles):
                raise ValueError(
                    "causal_force_binding: conflict and reversal chains must use a "
                    "baseline and countervailing force"
                )

        benchmark_ids = tuple(
            item.benchmark_id for item in self.benchmark_assessments
        )
        _unique(benchmark_ids, "benchmark assessment IDs")
        known_benchmark_ids = set(benchmark_ids)
        gap_ids = tuple(item.gap_id for item in self.disclosed_gaps)
        _unique(gap_ids, "disclosed framing gap IDs")
        for gap in self.disclosed_gaps:
            if not set(gap.affected_benchmark_ids).issubset(known_benchmark_ids):
                raise ValueError("disclosed gap references an unknown benchmark")

        supplied_witnesses = tuple(
            step.active_margin_witness
            for step in self.causal_chain
            if step.active_margin_witness is not None
        )
        inactive_witnesses = tuple(
            witness
            for witness in supplied_witnesses
            if witness.activity_status == "inactive"
        )
        unresolved_witnesses = tuple(
            witness
            for witness in supplied_witnesses
            if witness.activity_status == "unresolved"
        )
        causal_gaps = tuple(
            gap
            for gap in self.disclosed_gaps
            if gap.category == "causal_attribution"
        )
        if inactive_witnesses and (
            self.proposed_action != "revise_framing"
            or not any(gap.repair_target_refs for gap in causal_gaps)
        ):
            raise ValueError(
                "inactive_mechanism_link: an inactive payoff margin requires "
                "revise_framing and a causal-attribution gap with an exact repair "
                "target"
            )
        if unresolved_witnesses and not causal_gaps:
            raise ValueError(
                "unresolved_active_margin: an unresolved payoff margin requires a "
                "causal-attribution gap"
            )
        if (
            self.proposed_action == "ready_for_g1"
            and (inactive_witnesses or unresolved_witnesses)
        ):
            raise ValueError(
                "inactive_mechanism_link: inactive or unresolved mechanism links "
                "cannot be promoted to ready_for_g1"
            )

        exact_repair_targets = {
            "ResearchQuestion": self.research_question_ref,
            "BenchmarkSet": self.benchmark_set_ref,
            "PrimitiveGraph": self.primitive_graph_ref,
        }
        repair_targets = tuple(
            target
            for gap in self.disclosed_gaps
            for target in gap.repair_target_refs
        )
        for target in repair_targets:
            if target.entity_ref != exact_repair_targets[target.entity_type]:
                raise ValueError(
                    "framing repair target must name its exact typed bundle input"
                )
        if self.proposed_action == "revise_framing" and not repair_targets:
            raise ValueError(
                "revise_framing requires at least one exact typed repair target"
            )
        if self.proposed_action != "revise_framing" and repair_targets:
            raise ValueError(
                "exact repair targets are admissible only for revise_framing"
            )

        gap_coverage = {
            benchmark_id
            for gap in self.disclosed_gaps
            for benchmark_id in gap.affected_benchmark_ids
        }
        for assessment in self.benchmark_assessments:
            risky = (
                assessment.aggregate_invariance.weighting_distribution_status
                == "unresolved"
                or assessment.selection_assurance.status
                in {"selector_only", "unresolved"}
                or assessment.attribution_strength in {"weak", "unresolved"}
            )
            if risky and assessment.benchmark_id not in gap_coverage:
                raise ValueError(
                    "every benchmark with unresolved attribution risk requires "
                    "an explicitly linked disclosed gap"
                )
        if self.proposed_action == "ready_for_g1" and self.disclosed_gaps:
            raise ValueError(
                "unresolved framing gaps cannot be promoted to ready_for_g1"
            )
        return self


# ---------------------------------------------------------------------------
# Independent payload registry and envelope helpers


FRAMING_QUALITY_PAYLOAD_MODELS: Mapping[
    str, type[FramingQualityPayload]
] = MappingProxyType({"FramingQualityBundle": FramingQualityBundle})
FRAMING_QUALITY_PAYLOAD_OWNER_FACETS: Mapping[str, Facet] = MappingProxyType(
    {"FramingQualityBundle": "economic_interpretation"}
)


def framing_quality_schema_id(entity_type: str) -> str:
    if entity_type not in FRAMING_QUALITY_PAYLOAD_MODELS:
        raise ValueError(f"unregistered framing-quality entity_type: {entity_type}")
    return f"econ_theorist.framing_quality/{entity_type}/v1"


FRAMING_QUALITY_JSON_SCHEMA_REGISTRY: Mapping[str, Mapping[str, object]] = (
    MappingProxyType(
        {
            framing_quality_schema_id(entity_type): model.model_json_schema(
                mode="validation"
            )
            for entity_type, model in FRAMING_QUALITY_PAYLOAD_MODELS.items()
        }
    )
)


def framing_quality_payload_entity_type(payload: FramingQualityPayload) -> str:
    entity_type = type(payload).__name__
    if FRAMING_QUALITY_PAYLOAD_MODELS.get(entity_type) is not type(payload):
        raise ValueError(
            f"unregistered framing-quality payload model: {entity_type}"
        )
    return entity_type


def pack_framing_quality_payload(payload: FramingQualityPayload) -> FacetPayloads:
    """Place a registered framing-quality payload in its sole owner facet."""

    entity_type = framing_quality_payload_entity_type(payload)
    owner = FRAMING_QUALITY_PAYLOAD_OWNER_FACETS[entity_type]
    facets: dict[str, object] = {
        "formal": {},
        "economic_interpretation": {},
        "literature_novelty": {},
        "terminology_presentation": {},
        "authority": {},
    }
    facets[owner] = {
        "schema": framing_quality_schema_id(entity_type),
        "payload": payload.model_dump(mode="json", exclude_none=False),
    }
    return FacetPayloads.model_validate(facets)


def parse_framing_quality_payload(
    entity_type: str, facets: FacetPayloads | Mapping[str, object]
) -> FramingQualityPayload:
    """Parse only the independent framing-quality namespace."""

    model = FRAMING_QUALITY_PAYLOAD_MODELS.get(entity_type)
    if model is None:
        raise ValueError(f"unregistered framing-quality entity_type: {entity_type}")
    if not isinstance(facets, FacetPayloads):
        facets = FacetPayloads.model_validate(facets)
    owner = FRAMING_QUALITY_PAYLOAD_OWNER_FACETS[entity_type]
    dumped = facets.model_dump(mode="python")
    for facet, value in dumped.items():
        if facet != owner and value != {}:
            raise ValueError(
                f"{entity_type} payload is owned by {owner}; facet {facet} must be empty"
            )
    wrapper = dumped[owner]
    if set(wrapper) != {"schema", "payload"}:
        raise ValueError(
            "typed framing-quality facet must contain exactly schema and payload"
        )
    expected_schema = framing_quality_schema_id(entity_type)
    if wrapper["schema"] != expected_schema:
        raise ValueError(
            f"typed framing-quality schema mismatch: expected {expected_schema}"
        )
    payload_data = wrapper["payload"]
    if not isinstance(payload_data, dict):
        raise ValueError("typed framing-quality payload must be a JSON object")
    return model.model_validate_json(canonical_json_bytes(payload_data), strict=True)


def parse_framing_quality_entity(entity: EntityVersion) -> FramingQualityPayload:
    return parse_framing_quality_payload(entity.entity_type, entity.facets)


def is_packed_framing_quality_entity(entity: EntityVersion) -> bool:
    owner = FRAMING_QUALITY_PAYLOAD_OWNER_FACETS.get(entity.entity_type)
    if owner is None:
        return False
    value = getattr(entity.facets, owner)
    return (
        isinstance(value, dict)
        and set(value) == {"schema", "payload"}
        and value.get("schema") == framing_quality_schema_id(entity.entity_type)
        and isinstance(value.get("payload"), dict)
    )


# ---------------------------------------------------------------------------
# Pure economist-facing projection


def _markdown_text(value: str) -> str:
    """Keep canonical prose from changing the compact table structure."""

    return value.replace("\r", " ").replace("\n", " ").replace("|", "\\|")


def _markdown_items(values: tuple[str, ...]) -> str:
    return "<br>".join(_markdown_text(value) for value in values)


def _markdown_objects(values: tuple[FramingObjectRef, ...]) -> str:
    return "<br>".join(_markdown_text(value.label) for value in values)


def _display_token(value: str) -> str:
    return value.replace("_", " ")


def _display_action(value: FramingProposedAction) -> str:
    return {
        "ready_for_g1": "framing is ready for review",
        "continue_diagnostic": "continue the economic diagnosis",
        "revise_framing": "revise the framing",
    }[value]


def render_framing_quality_memo(
    bundle: FramingQualityBundle, benchmark_set: BenchmarkSet
) -> str:
    """Render a compact one-page memo without canonical IDs or storage jargon."""

    if bundle.research_question_ref != benchmark_set.question_ref:
        raise ValueError("bundle and benchmark set must bind the same research question")

    benchmark_ids = tuple(item.benchmark_id for item in benchmark_set.benchmarks)
    assessment_ids = tuple(
        item.benchmark_id for item in bundle.benchmark_assessments
    )
    if len(set(benchmark_ids)) != len(benchmark_ids):
        raise ValueError("benchmark set contains duplicate benchmark IDs")
    if set(assessment_ids) != set(benchmark_ids) or len(assessment_ids) != len(
        benchmark_ids
    ):
        raise ValueError(
            "benchmark assessments must cover every benchmark exactly once"
        )

    assessments = {
        item.benchmark_id: item for item in bundle.benchmark_assessments
    }
    force_heading = (
        "Competing economic forces"
        if bundle.tension.tension_kind
        in {"force_conflict", "sign_or_threshold_reversal"}
        else "Economic mechanism forces"
    )
    lines = [
        f"# {_markdown_text(bundle.economist_memo.headline)}",
        "",
        _markdown_text(bundle.economist_memo.opening_question),
        "",
        f"**Benchmark.** {_markdown_text(bundle.economist_memo.benchmark_message)}",
        "",
        f"**Tension.** {_markdown_text(bundle.economist_memo.tension_message)}",
        "",
        f"**Mechanism.** {_markdown_text(bundle.economist_memo.mechanism_message)}",
        "",
        f"## {force_heading}",
        "",
    ]
    force_roles = {
        "baseline_force": "baseline",
        "countervailing_force": "countervailing",
        "equilibrium_feedback": "equilibrium feedback",
        "boundary_force": "boundary",
    }
    for force in bundle.forces:
        lines.append(
            f"- **{_markdown_text(force.label)} ({force_roles[force.role]}).** "
            f"{_markdown_text(force.economic_logic)}"
        )
    lines.extend(
        [
        "",
        "## Three-step economic logic",
        "",
        ]
    )
    for step in bundle.causal_chain:
        lines.append(
            f"{step.step_number}. {_markdown_text(step.cause)} "
            f"-> {_markdown_text(step.endogenous_response)} "
            f"-> {_markdown_text(step.consequence)}"
        )
        witness = step.active_margin_witness
        if witness is not None:
            lines.append(
                f"   - **Payoff check ({_display_token(witness.activity_status)}).** "
                f"At {_markdown_text(witness.concrete_state)}, "
                f"{_markdown_text(witness.decision_maker)} compares "
                f"{_markdown_text(witness.focal_action)} "
                f"(payoff {_markdown_text(witness.focal_payoff)}) with "
                f"{_markdown_text(witness.alternative_action)} "
                f"(payoff {_markdown_text(witness.alternative_payoff)}). "
                f"The response requires {_markdown_text(witness.best_response_inequality)}. "
                f"{_markdown_text(witness.status_basis)} "
                f"Kill this link if {_markdown_text(witness.kill_condition)}"
            )

    lines.extend(
        [
            "",
            "## Benchmark comparison",
            "",
            "| Benchmark | Changes | Held fixed | Reoptimizes | Still endogenous | "
            "Target | Channel | Aggregate check | Selection check | Attribution |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
    )
    for benchmark in benchmark_set.benchmarks:
        assessment = assessments[benchmark.benchmark_id]
        aggregate = assessment.aggregate_invariance
        selection = assessment.selection_assurance
        lines.append(
            "| "
            + " | ".join(
                (
                    _markdown_text(benchmark.label),
                    _markdown_objects(assessment.changed),
                    _markdown_objects(assessment.held_fixed),
                    _markdown_objects(assessment.reoptimizing),
                    _markdown_objects(assessment.still_endogenous),
                    _markdown_objects(assessment.targets),
                    _markdown_text(assessment.channel_summary),
                    _markdown_text(
                        f"pointwise policy "
                        f"{'fixed' if aggregate.pointwise_policy_fixed else 'not fixed'}; "
                        f"weights {_display_token(aggregate.weighting_distribution_status)}; "
                        f"aggregate "
                        f"{'held fixed' if aggregate.claims_aggregate_fixed else 'not claimed fixed'}; "
                        f"{aggregate.basis}"
                    ),
                    _markdown_text(
                        f"{_display_token(selection.status)}: {selection.basis}"
                    ),
                    _markdown_text(
                        f"{_display_token(assessment.attribution_strength)}: "
                        f"{assessment.attribution_basis}"
                    ),
                )
            )
            + " |"
        )

    example = bundle.minimal_example
    lines.extend(
        [
            "",
            "## Small illustration",
            "",
            f"**{_markdown_text(example.title)}.** {_markdown_text(example.setup)} "
            f"Move {_markdown_text(example.moving_primitive)} while holding "
            f"{_markdown_items(example.held_fixed)} fixed. "
            f"{_markdown_text(example.economic_intuition)} "
            f"This only illustrates the logic: {_markdown_text(example.limitation)}",
            "",
            f"**Result preview.** {_markdown_text(bundle.economist_memo.result_preview)}",
            "",
            f"**Contribution.** {_markdown_text(bundle.economist_memo.contribution_message)}",
            "",
            f"**Scope.** {_markdown_text(bundle.economist_memo.scope_condition)}",
        ]
    )
    if bundle.disclosed_gaps:
        lines.extend(["", "**Open issues.**"])
        for gap in bundle.disclosed_gaps:
            lines.append(
                f"- {_markdown_text(gap.description)} "
                f"Next: {_markdown_text(gap.resolution_needed)}"
            )
    lines.extend(
        [
            "",
            f"**Recommended next move.** {_display_action(bundle.proposed_action)} -- "
            f"{_markdown_text(bundle.action_rationale)}",
            "",
            f"**Reader takeaway.** {_markdown_text(bundle.economist_memo.reader_takeaway)}",
            "",
        ]
    )
    return "\n".join(lines)


__all__ = [
    "ARCHETYPE_ALLOWED_TENSION_KINDS",
    "ARCHETYPE_TENSION_KINDS",
    "FRAMING_QUALITY_JSON_SCHEMA_REGISTRY",
    "FRAMING_QUALITY_PAYLOAD_MODELS",
    "FRAMING_QUALITY_PAYLOAD_OWNER_FACETS",
    "AggregateInvarianceAssessment",
    "ActiveMarginWitness",
    "ArchetypeTension",
    "BenchmarkFramingAssessment",
    "CausalChainStep",
    "ChannelKind",
    "DisclosedFramingGap",
    "EconomicForce",
    "EconomistMemo",
    "FramingObjectRef",
    "FramingQualityBundle",
    "FramingQualityPayload",
    "FramingRepairTargetRef",
    "HeldFixedObjectRef",
    "IllustrativeMinimalExample",
    "MECHANISM_MARGIN_TENSION_KINDS",
    "MarginActivityStatus",
    "SelectionAssurance",
    "framing_quality_payload_entity_type",
    "framing_quality_schema_id",
    "is_packed_framing_quality_entity",
    "pack_framing_quality_payload",
    "parse_framing_quality_entity",
    "parse_framing_quality_payload",
    "render_framing_quality_memo",
]
