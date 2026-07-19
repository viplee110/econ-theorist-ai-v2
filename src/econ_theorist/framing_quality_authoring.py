"""Noncanonical semantic authoring compiler for a fresh registry-v8 framing audit.

The canonical framing payloads and validators remain the scientific owners.
This module removes mechanical candidate work: it binds exact route inputs,
resolves declared benchmark paths, wraps the two output entities, instantiates
the five engine-declared hard relations, and builds the route outcome.  It
never writes an ObjectStore, commits a Transaction, or records a human gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from . import framing_quality as fq
from .candidate_contract import (
    CandidateAuthoringContractV1,
    CandidateHardRelationTemplateV1,
    CandidateRelationEndpointV1,
    candidate_authoring_contract_hash,
)
from .codec import canonical_json_bytes, ensure_canonical_data
from .framing_quality import (
    ActiveMarginWitness,
    ChoiceConsequenceBinding,
    ENDOGENOUS_ACTIVE_SEMANTIC_LEVELS,
    FramingQualityBundle,
    PublicStateCondition,
    pack_framing_quality_payload,
)
from .framing_quality_validation import (
    _is_permitted_unwitnessed_negative_revision,
    active_semantic_node_kinds,
    fixing_level_overlaps,
)
from .models import (
    CreateEntityOp,
    CreateRelationOp,
    Digest,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    NonEmptyString,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
    StableId,
    StrictModel,
    Transaction,
)
from .runtime.freshness import facet_semantic_hash
from .theory import (
    GateDossier,
    GateRequirement,
    PrimitiveGraph,
    pack_theory_payload,
    parse_theory_entity,
)


_FRAMING_ROUTE_ID = "audit.framing_economics"
_FRAMING_ROUTE_VERSION = 8
_FRAMING_EXIT_VALIDATOR_ID = "framing_quality_route_exit.v2"
_EXPECTED_TEMPLATE_IDS = (
    "framing.audits.research_question",
    "framing.audits.benchmark_set",
    "framing.audits.primitive_graph",
    "framing.audits.source_g1_dossier",
    "framing.governs.replacement_g1_dossier",
)
_INPUT_REF_FIELDS = {
    "ResearchQuestion": "research_question_ref",
    "BenchmarkSet": "benchmark_set_ref",
    "PrimitiveGraph": "primitive_graph_ref",
    "GateDossier": "source_g1_dossier_ref",
}
_MAX_PATH_ALTERNATIVES = 3
_SEMANTIC_AUTHORING_INSTRUCTIONS = (
    "Return one JSON object matching semantic_draft_json_schema; do not author "
    "Transaction wrappers, canonical IDs, relations, facet hashes, or a route outcome.",
    "Author the FramingQualityBundle scientific content, but omit the four exact "
    "input refs and every benchmark_assessments[*].channel_path; the compiler binds "
    "the refs and derives paths from channel_intents.",
    "Provide exactly one channel_intent for each benchmark assessment, naming its "
    "changed and target objects and only the PrimitiveGraph waypoints needed to "
    "disambiguate the directed path.",
)
_SEMANTIC_V2_AUTHORING_INSTRUCTIONS = (
    "Return one JSON object matching semantic_draft_json_schema; do not author "
    "Transaction wrappers, canonical IDs, relations, facet hashes, or a route outcome.",
    "Author the FramingQualityBundle scientific content, but omit the four exact "
    "input refs, every benchmark_assessments[*].channel_path, and all "
    "causal_chain[*].active_margin_witness values; the compiler binds those "
    "fields only when the declared graph makes them exact and unambiguous.",
    "Omit every forces[*].margin_node_id; keep the scientifically intended force "
    "source and target endpoints. The compiler derives the operative margin only "
    "from an exact cited causal step. Omit channel waypoints when the selected "
    "ledger endpoints already have one unique directed PrimitiveGraph path.",
    "Provide exactly one channel_intent for each benchmark assessment, naming its "
    "changed and target objects and only the PrimitiveGraph waypoints needed to "
    "disambiguate the directed path.",
    "Use margin_intents for the economic payoff comparison itself: actions, "
    "payoffs, feasibility, inequality, activity judgment, and kill condition are "
    "model-authored; graph node IDs and edge paths are compiler-bound or rejected "
    "as ambiguous.",
    "A margin_intent locates its force when decision_force_id is explicit or its "
    "causal step names one force. For every remaining force, provide one "
    "entry in force_margin_locators using source, target, or unique_interior "
    "position on a force-cited causal step; never author the graph node ID.",
    "Put an intentional research boundary in economist_memo.scope_condition. "
    "Use disclosed_gaps only for a genuinely unresolved defect with a repair path: "
    "every disclosed gap blocks ready_for_g1.",
)
_SEMANTIC_DRAFT_V2_SCHEMA = "econ-theorist/framing-audit-semantic-draft/v2"
_MARGIN_POSITIONS = Literal["source", "target", "unique_interior"]


class BenchmarkChannelIntentV1(StrictModel):
    """Economist-facing endpoint objects plus only needed disambiguating nodes."""

    channel_intent_schema: Literal[
        "econ-theorist/framing-channel-intent/v1"
    ] = "econ-theorist/framing-channel-intent/v1"
    benchmark_id: StableId
    changed_object_id: StableId
    target_object_id: StableId
    ordered_waypoint_node_ids: tuple[StableId, ...] = ()

    @field_validator("ordered_waypoint_node_ids")
    @classmethod
    def _waypoints_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("channel intent waypoints must be unique")
        return value


class PublicStateConditionIntentV2(StrictModel):
    """One model-authored public-state assertion resolved through a ledger object."""

    benchmark_id: StableId
    object_id: StableId
    relation: Literal[
        "equals", "not_equals", "positive", "zero", "interior", "boundary"
    ]
    value: NonEmptyString | None = None

    @model_validator(mode="after")
    def _value_matches_relation(self) -> "PublicStateConditionIntentV2":
        value_relation = self.relation in {"equals", "not_equals"}
        if value_relation != (self.value is not None):
            raise ValueError(
                "public-state intent: equals/not_equals require one value and "
                "qualitative relations must omit it"
            )
        return self


class MarginWitnessIntentV2(StrictModel):
    """Scientific payoff content whose exact graph bindings are compiler-owned."""

    step_number: Literal[1, 2, 3]
    decision_force_id: StableId | None = None
    margin_position: _MARGIN_POSITIONS
    payoff_node_id_disambiguators: tuple[StableId, ...] = ()
    consequence_step_number: Literal[1, 2, 3]
    concrete_state: NonEmptyString
    decision_maker: NonEmptyString
    focal_action: NonEmptyString
    alternative_action: NonEmptyString
    focal_payoff: NonEmptyString
    alternative_payoff: NonEmptyString
    feasibility_basis: NonEmptyString
    best_response_inequality: NonEmptyString
    activity_status: Literal["active", "inactive", "unresolved"]
    status_basis: NonEmptyString
    kill_condition: NonEmptyString
    transition_kind: Literal["increase", "decrease", "switch", "reweight"]
    focal_consequence: NonEmptyString
    alternative_consequence: NonEmptyString
    consequence_feasibility_basis: NonEmptyString
    public_state_conditions: Annotated[
        tuple[PublicStateConditionIntentV2, ...], Field(min_length=1)
    ]

    @field_validator("payoff_node_id_disambiguators")
    @classmethod
    def _payoff_disambiguators_are_unique(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("payoff-node disambiguators must be unique")
        return value

    @field_validator("public_state_conditions")
    @classmethod
    def _public_state_objects_are_unique(
        cls,
        value: tuple[PublicStateConditionIntentV2, ...],
    ) -> tuple[PublicStateConditionIntentV2, ...]:
        keys = tuple((item.benchmark_id, item.object_id) for item in value)
        if len(set(keys)) != len(keys):
            raise ValueError("public-state intent objects must be unique")
        return value

    @model_validator(mode="after")
    def _compares_distinct_actions(self) -> "MarginWitnessIntentV2":
        if self.focal_action == self.alternative_action:
            raise ValueError("margin intent focal and alternative actions must differ")
        return self


class ForceMarginLocatorV2(StrictModel):
    """A semantic step position for a force not located by a payoff intent."""

    force_id: StableId
    step_number: Literal[1, 2, 3]
    margin_position: _MARGIN_POSITIONS


class FramingAuditSemanticDraftV1(StrictModel):
    """Scientific content without canonical wrappers, relations, hashes, or IDs."""

    semantic_draft_schema: Literal[
        "econ-theorist/framing-audit-semantic-draft/v1"
    ] = "econ-theorist/framing-audit-semantic-draft/v1"
    bundle_payload: dict[str, Any]
    channel_intents: Annotated[
        tuple[BenchmarkChannelIntentV1, ...], Field(min_length=1)
    ]
    transaction_intent: NonEmptyString = (
        "Compile the declared economics-framing audit for canonical validation."
    )
    outcome_rationale: NonEmptyString = (
        "The semantic draft was mechanically compiled under the exact V8 contract."
    )
    bundle_title: NonEmptyString = "Economics framing preflight"
    bundle_summary: NonEmptyString = (
        "Benchmark semantics, economic forces, and disclosed attribution risks."
    )
    replacement_dossier_title: NonEmptyString = "Replacement G1 dossier"
    replacement_dossier_summary: NonEmptyString = (
        "The source G1 package strengthened by the framing audit."
    )

    @field_validator("bundle_payload", mode="before")
    @classmethod
    def _payload_is_canonical_json(cls, value: Any) -> dict[str, Any]:
        normalized = ensure_canonical_data(value)
        if not isinstance(normalized, dict):
            raise ValueError("bundle_payload must be one canonical JSON object")
        return normalized

    @field_validator("channel_intents")
    @classmethod
    def _benchmark_intents_are_unique(
        cls, value: tuple[BenchmarkChannelIntentV1, ...]
    ) -> tuple[BenchmarkChannelIntentV1, ...]:
        identifiers = tuple(item.benchmark_id for item in value)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("channel intents must have unique benchmark IDs")
        return value


class FramingAuditSemanticDraftV2(FramingAuditSemanticDraftV1):
    """V2 semantic surface with deterministic active-margin witness binding."""

    semantic_draft_schema: Literal[
        _SEMANTIC_DRAFT_V2_SCHEMA
    ] = _SEMANTIC_DRAFT_V2_SCHEMA
    margin_intents: tuple[MarginWitnessIntentV2, ...] = ()
    force_margin_locators: tuple[ForceMarginLocatorV2, ...] = ()

    @field_validator("margin_intents")
    @classmethod
    def _margin_intents_are_unique(
        cls, value: tuple[MarginWitnessIntentV2, ...]
    ) -> tuple[MarginWitnessIntentV2, ...]:
        step_numbers = tuple(item.step_number for item in value)
        if len(set(step_numbers)) != len(step_numbers):
            raise ValueError("margin intents must name distinct causal steps")
        return value

    @field_validator("force_margin_locators")
    @classmethod
    def _force_margin_locators_are_unique(
        cls, value: tuple[ForceMarginLocatorV2, ...]
    ) -> tuple[ForceMarginLocatorV2, ...]:
        force_ids = tuple(item.force_id for item in value)
        if len(set(force_ids)) != len(force_ids):
            raise ValueError("force margin locators must name distinct forces")
        return value


class FramingAuditSemanticAuthoringSurfaceV1(StrictModel):
    """Exact, noncanonical model-facing contract for one semantic draft."""

    semantic_surface_schema: Literal[
        "econ-theorist/framing-audit-semantic-authoring-surface/v1"
    ] = "econ-theorist/framing-audit-semantic-authoring-surface/v1"
    candidate_authoring_contract_hash: Digest
    work_packet_hash: Digest
    project_id: StableId
    base_revision: Digest
    route_run_id: StableId
    route_id: Literal["audit.framing_economics"] = "audit.framing_economics"
    route_version: Literal[8] = 8
    semantic_draft_schema_id: Literal[
        "econ-theorist/framing-audit-semantic-draft/v1"
    ] = "econ-theorist/framing-audit-semantic-draft/v1"
    semantic_draft_json_schema: dict[str, Any]
    authoring_instructions: tuple[NonEmptyString, ...] = (
        _SEMANTIC_AUTHORING_INSTRUCTIONS
    )


class FramingAuditSemanticAuthoringSurfaceV2(
    FramingAuditSemanticAuthoringSurfaceV1
):
    """V2 projection preserving V1 while removing deterministic witness fields."""

    semantic_surface_schema: Literal[
        "econ-theorist/framing-audit-semantic-authoring-surface/v2"
    ] = "econ-theorist/framing-audit-semantic-authoring-surface/v2"
    semantic_draft_schema_id: Literal[
        "econ-theorist/framing-audit-semantic-draft/v2"
    ] = "econ-theorist/framing-audit-semantic-draft/v2"
    authoring_instructions: tuple[NonEmptyString, ...] = (
        _SEMANTIC_V2_AUTHORING_INSTRUCTIONS
    )


def _remove_compiler_bound_schema_property(
    object_schema: dict[str, Any],
    property_name: str,
    *,
    model_name: str,
) -> None:
    properties = object_schema.get("properties")
    required = object_schema.get("required")
    if not isinstance(properties, dict) or property_name not in properties:
        raise ValueError(
            f"semantic surface source schema lacks {model_name}.{property_name}"
        )
    if not isinstance(required, list) or property_name not in required:
        raise ValueError(
            f"semantic surface source schema does not require "
            f"{model_name}.{property_name}"
        )
    properties.pop(property_name)
    object_schema["required"] = [
        name for name in required if name != property_name
    ]


def _remove_compiler_optional_schema_property(
    object_schema: dict[str, Any],
    property_name: str,
    *,
    model_name: str,
) -> None:
    properties = object_schema.get("properties")
    if not isinstance(properties, dict) or property_name not in properties:
        raise ValueError(
            f"semantic surface source schema lacks {model_name}.{property_name}"
        )
    properties.pop(property_name)
    required = object_schema.get("required")
    if isinstance(required, list):
        object_schema["required"] = [
            name for name in required if name != property_name
        ]


def _project_semantic_draft_json_schema(
    bundle_payload_schema: Mapping[str, Any],
    *,
    draft_model: type[FramingAuditSemanticDraftV1] = FramingAuditSemanticDraftV1,
    omit_active_margin_witness: bool = False,
    omit_force_margin_binding: bool = False,
) -> dict[str, Any]:
    projected_bundle = deepcopy(dict(bundle_payload_schema))
    for field_name in _INPUT_REF_FIELDS.values():
        _remove_compiler_bound_schema_property(
            projected_bundle,
            field_name,
            model_name="FramingQualityBundle",
        )

    bundle_definitions = projected_bundle.get("$defs")
    if not isinstance(bundle_definitions, dict):
        raise ValueError(
            "semantic surface source schema lacks FramingQualityBundle definitions"
        )
    assessment_schema = bundle_definitions.get("BenchmarkFramingAssessment")
    if not isinstance(assessment_schema, dict):
        raise ValueError(
            "semantic surface source schema lacks BenchmarkFramingAssessment"
        )
    _remove_compiler_bound_schema_property(
        assessment_schema,
        "channel_path",
        model_name="BenchmarkFramingAssessment",
    )
    if omit_active_margin_witness:
        causal_step_schema = bundle_definitions.get("CausalChainStep")
        if not isinstance(causal_step_schema, dict):
            raise ValueError(
                "semantic surface source schema lacks CausalChainStep definition"
            )
        _remove_compiler_optional_schema_property(
            causal_step_schema,
            "active_margin_witness",
            model_name="CausalChainStep",
        )
    if omit_force_margin_binding:
        force_schema = bundle_definitions.get("EconomicForce")
        if not isinstance(force_schema, dict):
            raise ValueError(
                "semantic surface source schema lacks EconomicForce definition"
            )
        _remove_compiler_bound_schema_property(
            force_schema,
            "margin_node_id",
            model_name="EconomicForce",
        )

    projected_bundle.pop("$defs")
    draft_schema = deepcopy(draft_model.model_json_schema(mode="validation"))
    draft_properties = draft_schema.get("properties")
    if not isinstance(draft_properties, dict) or "bundle_payload" not in draft_properties:
        raise ValueError("semantic draft schema lacks bundle_payload")
    draft_properties["bundle_payload"] = projected_bundle

    draft_definitions = draft_schema.setdefault("$defs", {})
    if not isinstance(draft_definitions, dict):
        raise ValueError("semantic draft schema definitions are malformed")
    collisions = {
        name
        for name, definition in bundle_definitions.items()
        if name in draft_definitions and draft_definitions[name] != definition
    }
    if collisions:
        raise ValueError(
            "semantic surface schema definition collision: "
            + ", ".join(sorted(collisions))
        )
    for name, definition in bundle_definitions.items():
        draft_definitions.setdefault(name, definition)
    return draft_schema


def compile_framing_audit_semantic_authoring_contract(
    contract: CandidateAuthoringContractV1,
) -> FramingAuditSemanticAuthoringSurfaceV1:
    """Project one exact V8 candidate contract into the smaller draft surface."""

    output = contract.output_contract
    exact_template_refs = frozenset(
        item.source.entity_ref
        for item in output.required_relation_templates
        if item.source.binding_kind == "exact_input"
        and item.source.entity_ref is not None
    )
    evidence_refs = contract.transaction_bindings.required_entity_evidence_refs
    if (
        output.route_id != _FRAMING_ROUTE_ID
        or output.route_version != _FRAMING_ROUTE_VERSION
        or output.exit_validator_id != _FRAMING_EXIT_VALIDATOR_ID
        or contract.packet_compiler_version != 2
        or contract.candidate_draft_semantics
        != "runtime_facet_hash_materialization_v1"
        or tuple(item.template_id for item in output.required_relation_templates)
        != _EXPECTED_TEMPLATE_IDS
        or len(evidence_refs) != len(_INPUT_REF_FIELDS)
        or frozenset(evidence_refs) != exact_template_refs
    ):
        raise ValueError(
            "semantic authoring surface requires the exact fresh registry-v8 "
            "framing candidate contract"
        )
    bundle_contracts = tuple(
        item
        for item in contract.payload_schemas
        if item.entity_type == "FramingQualityBundle"
    )
    if len(bundle_contracts) != 1:
        raise ValueError(
            "semantic authoring surface requires one FramingQualityBundle payload schema"
        )
    bindings = contract.transaction_bindings
    return FramingAuditSemanticAuthoringSurfaceV1(
        candidate_authoring_contract_hash=candidate_authoring_contract_hash(contract),
        work_packet_hash=contract.work_packet_hash,
        project_id=bindings.project_id,
        base_revision=bindings.base_revision,
        route_run_id=bindings.route_run_id,
        semantic_draft_json_schema=_project_semantic_draft_json_schema(
            bundle_contracts[0].payload_json_schema
        ),
    )


def compile_framing_audit_semantic_authoring_contract_v2(
    contract: CandidateAuthoringContractV1,
) -> FramingAuditSemanticAuthoringSurfaceV2:
    """Project the exact V8 contract into the additive V2 semantic surface."""

    # Reuse the V1 exact-contract checks without changing its bytes or semantics.
    v1_surface = compile_framing_audit_semantic_authoring_contract(contract)
    bundle_contracts = tuple(
        item
        for item in contract.payload_schemas
        if item.entity_type == "FramingQualityBundle"
    )
    assert len(bundle_contracts) == 1
    return FramingAuditSemanticAuthoringSurfaceV2(
        candidate_authoring_contract_hash=v1_surface.candidate_authoring_contract_hash,
        work_packet_hash=v1_surface.work_packet_hash,
        project_id=v1_surface.project_id,
        base_revision=v1_surface.base_revision,
        route_run_id=v1_surface.route_run_id,
        semantic_draft_json_schema=_project_semantic_draft_json_schema(
            bundle_contracts[0].payload_json_schema,
            draft_model=FramingAuditSemanticDraftV2,
            omit_active_margin_witness=True,
            omit_force_margin_binding=True,
        ),
    )


class FramingAuditPreflightIssueV1(StrictModel):
    """One bounded, location-specific compiler issue returned before a retry."""

    issue_schema: Literal[
        "econ-theorist/framing-audit-preflight-issue/v1"
    ] = "econ-theorist/framing-audit-preflight-issue/v1"
    rule_id: StableId
    location: tuple[str | int, ...]
    json_pointer: NonEmptyString
    message: NonEmptyString
    benchmark_id: StableId | None = None
    object_id: StableId | None = None
    options: tuple[NonEmptyString, ...] = ()
    expected: NonEmptyString | None = None
    observed: NonEmptyString | None = None


class FramingAuditPreflightReportV1(StrictModel):
    """Deterministic aggregate preflight; no issue consumes a route repair."""

    preflight_schema: Literal[
        "econ-theorist/framing-audit-preflight/v1"
    ] = "econ-theorist/framing-audit-preflight/v1"
    passed: bool
    issues: tuple[FramingAuditPreflightIssueV1, ...] = ()
    active_semantic_node_ids: tuple[StableId, ...] = ()

    def model_post_init(self, __context: Any) -> None:
        if self.passed == bool(self.issues):
            raise ValueError("preflight passed must be the inverse of issue presence")


class FramingAuditCompilationError(ValueError):
    """Aggregate compiler failure with stable machine-readable issues."""

    def __init__(self, issues: tuple[FramingAuditPreflightIssueV1, ...]) -> None:
        if not issues:
            raise ValueError("FramingAuditCompilationError requires at least one issue")
        self.issues = issues
        codes = ", ".join(issue.rule_id for issue in issues)
        super().__init__(
            f"framing semantic preflight rejected {len(issues)} issue(s): {codes}"
        )


@dataclass(frozen=True)
class _PreparedDraft:
    payload: dict[str, Any]
    bundle: FramingQualityBundle | None
    inputs_by_type: Mapping[str, EntityVersion]
    graph: PrimitiveGraph | None
    report: FramingAuditPreflightReportV1


def _issue(
    rule_id: str,
    location: tuple[str | int, ...],
    message: str,
    *,
    benchmark_id: str | None = None,
    object_id: str | None = None,
    options: tuple[str, ...] = (),
    expected: str | None = None,
    observed: str | None = None,
) -> FramingAuditPreflightIssueV1:
    pointer = "/" + "/".join(
        str(item).replace("~", "~0").replace("/", "~1")
        for item in location
    )
    return FramingAuditPreflightIssueV1(
        rule_id=rule_id,
        location=location,
        json_pointer=pointer,
        message=message,
        benchmark_id=benchmark_id,
        object_id=object_id,
        options=options,
        expected=expected,
        observed=observed,
    )


def _deduplicate_issues(
    issues: list[FramingAuditPreflightIssueV1],
) -> tuple[FramingAuditPreflightIssueV1, ...]:
    unique: dict[
        tuple[str, tuple[str | int, ...], str | None, str | None],
        FramingAuditPreflightIssueV1,
    ] = {}
    for issue in issues:
        key = (
            issue.rule_id,
            issue.location,
            issue.benchmark_id,
            issue.object_id,
        )
        unique.setdefault(key, issue)
    return tuple(unique.values())


def _contract_inputs(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
) -> tuple[
    dict[str, EntityVersion],
    list[FramingAuditPreflightIssueV1],
]:
    issues: list[FramingAuditPreflightIssueV1] = []
    output = contract.output_contract
    if (
        output.route_id != _FRAMING_ROUTE_ID
        or output.route_version != _FRAMING_ROUTE_VERSION
        or output.exit_validator_id != _FRAMING_EXIT_VALIDATOR_ID
        or contract.packet_compiler_version != 2
        or contract.candidate_draft_semantics
        != "runtime_facet_hash_materialization_v1"
    ):
        issues.append(
            _issue(
                "compiler.contract.v8_required",
                ("contract", "output_contract"),
                "The semantic compiler accepts only the exact registry-v8 framing route.",
            )
        )
    if (
        snapshot.project_id != contract.transaction_bindings.project_id
        or snapshot.head != contract.transaction_bindings.base_revision
    ):
        issues.append(
            _issue(
                "compiler.contract.base_mismatch",
                ("contract", "transaction_bindings", "base_revision"),
                "The contract is not bound to this exact snapshot project and head.",
            )
        )

    templates = output.required_relation_templates
    if tuple(item.template_id for item in templates) != _EXPECTED_TEMPLATE_IDS:
        issues.append(
            _issue(
                "compiler.contract.relation_templates",
                ("contract", "output_contract", "required_relation_templates"),
                "The exact four audits and one governs templates are required in order.",
            )
        )
    exact_entities = {
        (entity.entity_id, entity.version): entity
        for entity in snapshot.entity_versions
    }
    for evidence_index, reference in enumerate(
        contract.transaction_bindings.required_entity_evidence_refs
    ):
        entity = exact_entities.get((reference.entity_id, reference.version))
        if entity is None:
            issues.append(
                _issue(
                    "compiler.contract.evidence_input_missing",
                    (
                        "contract",
                        "transaction_bindings",
                        "required_entity_evidence_refs",
                        evidence_index,
                    ),
                    "A required exact evidence input is absent from the base snapshot.",
                )
            )
        elif entity.entity_type == "FramingQualityBundle":
            issues.append(
                _issue(
                    "compiler.contract.continuation_unsupported",
                    (
                        "contract",
                        "transaction_bindings",
                        "required_entity_evidence_refs",
                        evidence_index,
                    ),
                    "This prototype compiles only a fresh V8 audit, not bundle continuation.",
                    options=(
                        "Use the existing canonical continuation authoring path.",
                        "Add exact supersession support before compiler integration.",
                    ),
                )
            )
    inputs_by_type: dict[str, EntityVersion] = {}
    for template_index, template in enumerate(templates):
        endpoint = template.source
        if endpoint.binding_kind != "exact_input":
            continue
        assert endpoint.entity_ref is not None
        entity = exact_entities.get(
            (endpoint.entity_ref.entity_id, endpoint.entity_ref.version)
        )
        location = (
            "contract",
            "output_contract",
            "required_relation_templates",
            template_index,
            "source",
        )
        if entity is None or entity.entity_type != endpoint.entity_type:
            issues.append(
                _issue(
                    "compiler.contract.exact_input_missing",
                    location,
                    "A relation template input is absent or has the wrong entity type.",
                )
            )
            continue
        if endpoint.entity_type in inputs_by_type:
            issues.append(
                _issue(
                    "compiler.contract.exact_input_duplicated",
                    location,
                    "Each framing input entity type must resolve exactly once.",
                )
            )
            continue
        inputs_by_type[endpoint.entity_type] = entity
    missing_types = sorted(set(_INPUT_REF_FIELDS).difference(inputs_by_type))
    if missing_types:
        issues.append(
            _issue(
                "compiler.contract.exact_inputs_incomplete",
                ("contract", "output_contract", "required_relation_templates"),
                "Missing exact input types: " + ", ".join(missing_types),
            )
        )
    return inputs_by_type, issues


def _bind_exact_inputs(
    payload: dict[str, Any],
    inputs_by_type: Mapping[str, EntityVersion],
) -> list[FramingAuditPreflightIssueV1]:
    issues: list[FramingAuditPreflightIssueV1] = []
    for entity_type, field_name in _INPUT_REF_FIELDS.items():
        entity = inputs_by_type.get(entity_type)
        if entity is None:
            continue
        expected = {
            "entity_id": entity.entity_id,
            "version": entity.version,
        }
        if field_name in payload:
            issues.append(
                _issue(
                    "compiler.payload.exact_input_duplicate_source",
                    ("bundle_payload", field_name),
                    f"Semantic drafts must omit compiler-owned {field_name}.",
                    options=("Remove the field and let the compiler bind it.",),
                )
            )
        payload[field_name] = expected
    return issues


def _find_simple_paths(
    adjacency: Mapping[str, tuple[str, ...]],
    source: str,
    target: str,
) -> tuple[tuple[str, ...], ...]:
    if source == target:
        return ((source,),)
    found: list[tuple[str, ...]] = []
    stack: list[tuple[str, tuple[str, ...]]] = [(source, (source,))]
    while stack and len(found) < _MAX_PATH_ALTERNATIVES:
        node, path = stack.pop()
        for neighbor in reversed(adjacency.get(node, ())):
            if neighbor in path:
                continue
            candidate = (*path, neighbor)
            if neighbor == target:
                found.append(candidate)
                if len(found) >= _MAX_PATH_ALTERNATIVES:
                    break
            else:
                stack.append((neighbor, candidate))
    return tuple(found)


def _resolve_channel_path(
    graph: PrimitiveGraph,
    *,
    source_node_id: str,
    target_node_id: str,
    waypoints: tuple[str, ...],
    location: tuple[str | int, ...],
    benchmark_id: str,
) -> tuple[tuple[str, ...] | None, list[FramingAuditPreflightIssueV1]]:
    issues: list[FramingAuditPreflightIssueV1] = []
    node_ids = {node.node_id for node in graph.nodes}
    requested = (source_node_id, *waypoints, target_node_id)
    unknown = tuple(node_id for node_id in requested if node_id not in node_ids)
    if unknown:
        issues.append(
            _issue(
                "compiler.channel_path.unknown_node",
                location,
                "Channel intent references unknown PrimitiveGraph nodes: "
                + ", ".join(unknown),
                benchmark_id=benchmark_id,
            )
        )
        return None, issues
    if len(set(requested)) != len(requested):
        issues.append(
            _issue(
                "compiler.channel_path.repeated_node",
                location,
                "Channel endpoints and waypoints must describe a simple path.",
                benchmark_id=benchmark_id,
            )
        )
        return None, issues

    adjacency_sets: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in graph.edges:
        adjacency_sets[edge.source_node_id].add(edge.target_node_id)
    adjacency = {
        node_id: tuple(sorted(neighbors))
        for node_id, neighbors in adjacency_sets.items()
    }
    resolved: list[str] = []
    for segment_index, (source, target) in enumerate(zip(requested, requested[1:])):
        alternatives = _find_simple_paths(adjacency, source, target)
        segment_location = (*location, "segment", segment_index)
        if not alternatives:
            issues.append(
                _issue(
                    "compiler.channel_path.unreachable",
                    segment_location,
                    f"No directed PrimitiveGraph path connects {source} to {target}.",
                    benchmark_id=benchmark_id,
                )
            )
            return None, issues
        if len(alternatives) > 1:
            issues.append(
                _issue(
                    "compiler.channel_path.ambiguous",
                    segment_location,
                    f"More than one directed path connects {source} to {target}.",
                    benchmark_id=benchmark_id,
                    options=tuple(" -> ".join(path) for path in alternatives),
                )
            )
            return None, issues
        segment = alternatives[0]
        resolved.extend(segment if not resolved else segment[1:])
    if len(set(resolved)) != len(resolved):
        issues.append(
            _issue(
                "compiler.channel_path.non_simple_resolution",
                location,
                "The uniquely resolved segments revisit a PrimitiveGraph node.",
                benchmark_id=benchmark_id,
            )
        )
        return None, issues
    return tuple(resolved), issues


def _mapping_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _object_binding(
    row: Mapping[str, Any], group: str, object_id: str
) -> Mapping[str, Any] | None:
    matches = [
        item
        for item in _mapping_list(row.get(group))
        if item.get("object_id") == object_id
    ]
    return matches[0] if len(matches) == 1 else None


def _apply_channel_intents(
    payload: dict[str, Any],
    graph: PrimitiveGraph,
    intents: tuple[BenchmarkChannelIntentV1, ...],
) -> list[FramingAuditPreflightIssueV1]:
    issues: list[FramingAuditPreflightIssueV1] = []
    rows = _mapping_list(payload.get("benchmark_assessments"))
    intent_by_id = {item.benchmark_id: item for item in intents}
    row_ids = {
        row.get("benchmark_id") for row in rows if isinstance(row.get("benchmark_id"), str)
    }
    for intent_index, intent in enumerate(intents):
        if intent.benchmark_id not in row_ids:
            issues.append(
                _issue(
                    "compiler.channel_intent.unknown_benchmark",
                    ("channel_intents", intent_index, "benchmark_id"),
                    "Channel intent does not match a benchmark assessment.",
                    benchmark_id=intent.benchmark_id,
                )
            )
    for row_index, row in enumerate(rows):
        benchmark_id = row.get("benchmark_id")
        if not isinstance(benchmark_id, str):
            continue
        intent = intent_by_id.get(benchmark_id)
        path_location = (
            "bundle_payload",
            "benchmark_assessments",
            row_index,
            "channel_path",
        )
        if "channel_path" in row:
            issues.append(
                _issue(
                    "compiler.channel_path.duplicate_source",
                    path_location,
                    "Semantic drafts must omit channel_path and let one channel intent compile it.",
                    benchmark_id=benchmark_id,
                    options=("Remove channel_path from bundle_payload.",),
                )
            )
            row.pop("channel_path")
        if intent is None:
            issues.append(
                _issue(
                    "compiler.channel_intent.missing",
                    path_location,
                    "Every benchmark assessment requires one channel intent.",
                    benchmark_id=benchmark_id,
                )
            )
            continue
        changed = _object_binding(row, "changed", intent.changed_object_id)
        target = _object_binding(row, "targets", intent.target_object_id)
        if changed is None:
            issues.append(
                _issue(
                    "compiler.channel_intent.changed_object",
                    path_location,
                    "changed_object_id must identify exactly one changed object.",
                    benchmark_id=benchmark_id,
                    object_id=intent.changed_object_id,
                )
            )
        if target is None:
            issues.append(
                _issue(
                    "compiler.channel_intent.target_object",
                    path_location,
                    "target_object_id must identify exactly one target object.",
                    benchmark_id=benchmark_id,
                    object_id=intent.target_object_id,
                )
            )
        if changed is None or target is None:
            continue
        source_node_id = changed.get("primitive_node_id")
        target_node_id = target.get("primitive_node_id")
        if not isinstance(source_node_id, str) or not isinstance(target_node_id, str):
            issues.append(
                _issue(
                    "compiler.channel_intent.unbound_endpoint",
                    path_location,
                    "Selected changed and target objects need exact primitive_node_id bindings.",
                    benchmark_id=benchmark_id,
                    options=(
                        "Bind the exact graph nodes.",
                        "Select different endpoint objects.",
                    ),
                )
            )
            continue
        path, path_issues = _resolve_channel_path(
            graph,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            waypoints=intent.ordered_waypoint_node_ids,
            location=path_location,
            benchmark_id=benchmark_id,
        )
        issues.extend(path_issues)
        if path is not None:
            row["channel_path"] = list(path)
    return issues


def _graph_adjacency(graph: PrimitiveGraph) -> dict[str, tuple[str, ...]]:
    adjacency_sets: dict[str, set[str]] = {
        node.node_id: set() for node in graph.nodes
    }
    for edge in graph.edges:
        adjacency_sets[edge.source_node_id].add(edge.target_node_id)
    return {
        node_id: tuple(sorted(neighbors))
        for node_id, neighbors in adjacency_sets.items()
    }


def _node_is_on_step(
    adjacency: Mapping[str, tuple[str, ...]],
    *,
    source_node_id: str,
    target_node_id: str,
    node_id: str,
) -> bool:
    return bool(
        _find_simple_paths(adjacency, source_node_id, node_id)
        and _find_simple_paths(adjacency, node_id, target_node_id)
    )


def _choice_nodes_on_step(
    graph: PrimitiveGraph,
    adjacency: Mapping[str, tuple[str, ...]],
    *,
    source_node_id: str,
    target_node_id: str,
    exclude_source: bool,
) -> tuple[str, ...]:
    """Return every graph choice compatible with one declared causal step."""

    return tuple(
        sorted(
            node.node_id
            for node in graph.nodes
            if node.kind == "choice"
            and (not exclude_source or node.node_id != source_node_id)
            and _node_is_on_step(
                adjacency,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                node_id=node.node_id,
            )
        )
    )


def _graph_node_observation(
    node_id: object,
    node_by_id: Mapping[str, Any],
) -> str:
    if not isinstance(node_id, str):
        return _diagnostic_scalar(node_id)
    node = node_by_id.get(node_id)
    kind = node.kind if node is not None else "<unknown>"
    return f"{node_id} (kind={kind})"


def _apply_force_margin_bindings(
    payload: dict[str, Any],
    graph: PrimitiveGraph,
    intents: tuple[MarginWitnessIntentV2, ...],
    locators: tuple[ForceMarginLocatorV2, ...],
) -> list[FramingAuditPreflightIssueV1]:
    """Bind a force margin only from one explicit semantic step position."""

    issues: list[FramingAuditPreflightIssueV1] = []
    forces = _mapping_list(payload.get("forces"))
    causal_steps = _mapping_list(payload.get("causal_chain"))
    node_by_id = {node.node_id: node for node in graph.nodes}
    adjacency = _graph_adjacency(graph)
    steps_by_number = {
        step.get("step_number"): (step_index, step)
        for step_index, step in enumerate(causal_steps)
        if isinstance(step.get("step_number"), int)
    }
    force_ids = {
        force.get("force_id")
        for force in forces
        if isinstance(force.get("force_id"), str)
    }

    for locator_index, locator in enumerate(locators):
        if locator.force_id not in force_ids:
            issues.append(
                _issue(
                    "compiler.force.margin_locator_unknown_force",
                    ("force_margin_locators", locator_index, "force_id"),
                    "A force margin locator must name one declared force.",
                    options=tuple(sorted(force_ids)),
                    observed=locator.force_id,
                )
            )

    for force_index, force in enumerate(forces):
        force_id = force.get("force_id")
        if not isinstance(force_id, str):
            continue
        location = ("bundle_payload", "forces", force_index)
        authored_margin = force.pop("margin_node_id", _MISSING)
        cited_step_numbers = tuple(
            sorted(
                step_number
                for step_number, (_, step) in steps_by_number.items()
                if isinstance(step.get("force_ids"), list)
                and force_id in step["force_ids"]
            )
        )
        if not cited_step_numbers:
            issues.append(
                _issue(
                    "compiler.force.causal_step_missing",
                    (*location, "force_id"),
                    "A declared force must be cited by at least one causal step.",
                    observed=force_id,
                )
            )
            continue

        locator_candidates: list[
            tuple[int, Literal["source", "target", "unique_interior"], str]
        ] = [
            (locator.step_number, locator.margin_position, "force_margin_locator")
            for locator in locators
            if locator.force_id == force_id
        ]
        for intent_index, intent in enumerate(intents):
            step_entry = steps_by_number.get(intent.step_number)
            if step_entry is None:
                continue
            _, step = step_entry
            step_force_ids = step.get("force_ids")
            if not isinstance(step_force_ids, list):
                continue
            selected_force_id = intent.decision_force_id
            if selected_force_id is None and len(step_force_ids) == 1:
                selected_force_id = step_force_ids[0]
            if selected_force_id != force_id:
                continue
            locator_candidates.append(
                (
                    intent.step_number,
                    intent.margin_position,
                    f"margin_intents/{intent_index}",
                )
            )

        exact_locators = sorted(set(locator_candidates))
        margin_node_id: str | None = None
        compatible_choice_options: tuple[str, ...] = ()
        diagnostic_options = tuple(
            f"step {step_number} {position} ({source})"
            for step_number, position, source in exact_locators
        )
        if len(exact_locators) != 1:
            issues.append(
                _issue(
                    (
                        "compiler.force.margin_locator_missing"
                        if not exact_locators
                        else "compiler.force.margin_locator_ambiguous"
                    ),
                    (*location, "margin_node_id"),
                    "Each V2 force needs one unambiguous semantic step position for its operative margin.",
                    options=(
                        diagnostic_options
                        if diagnostic_options
                        else tuple(f"Use cited causal step {item}." for item in cited_step_numbers)
                    ),
                    observed=_graph_node_observation(authored_margin, node_by_id),
                )
            )
        else:
            step_number, position, _ = exact_locators[0]
            step_entry = steps_by_number.get(step_number)
            if step_entry is None:
                issues.append(
                    _issue(
                        "compiler.force.margin_locator_unknown_step",
                        (*location, "margin_node_id"),
                        "The force margin locator names no causal step.",
                        options=tuple(str(item) for item in cited_step_numbers),
                        observed=str(step_number),
                    )
                )
            else:
                _, step = step_entry
                step_force_ids = step.get("force_ids")
                if not isinstance(step_force_ids, list) or force_id not in step_force_ids:
                    issues.append(
                        _issue(
                            "compiler.force.margin_locator_uncited_step",
                            (*location, "margin_node_id"),
                            "The selected margin step must cite this force.",
                            options=tuple(str(item) for item in cited_step_numbers),
                            observed=str(step_number),
                        )
                    )
                else:
                    step_source = step.get("source_node_id")
                    step_target = step.get("target_node_id")
                    if isinstance(step_source, str) and isinstance(step_target, str):
                        compatible_choice_options = _choice_nodes_on_step(
                            graph,
                            adjacency,
                            source_node_id=step_source,
                            target_node_id=step_target,
                            exclude_source=False,
                        )
                    if position == "source":
                        candidate = step_source
                    elif position == "target":
                        candidate = step_target
                    else:
                        paths = (
                            _find_simple_paths(adjacency, step_source, step_target)
                            if isinstance(step_source, str)
                            and isinstance(step_target, str)
                            else ()
                        )
                        interiors = tuple(
                            path[1:-1]
                            for path in paths
                            if len(path[1:-1]) == 1
                        )
                        candidate = (
                            interiors[0][0]
                            if len(paths) == 1 and len(interiors) == 1
                            else None
                        )
                        if candidate is None:
                            issues.append(
                                _issue(
                                    "compiler.force.margin_locator_interior_ambiguous",
                                    (*location, "margin_node_id"),
                                    "unique_interior requires one directed path with exactly one interior node.",
                                    options=tuple(" -> ".join(path) for path in paths),
                                )
                            )
                    if isinstance(candidate, str) and candidate in node_by_id:
                        margin_node_id = candidate
                        force["margin_node_id"] = candidate
                    elif candidate is not None:
                        issues.append(
                            _issue(
                                "compiler.force.margin_locator_unknown_node",
                                (*location, "margin_node_id"),
                                "The selected causal-step position does not bind a known PrimitiveGraph node.",
                                observed=_graph_node_observation(candidate, node_by_id),
                            )
                        )

        if authored_margin is not _MISSING:
            if margin_node_id is not None and authored_margin != margin_node_id:
                issues.append(
                    _issue(
                        "compiler.margin.force_binding",
                        (*location, "margin_node_id"),
                        "The authored force margin differs from the semantic step position; V2 owns this graph binding.",
                        options=(
                            compatible_choice_options
                            or (
                                (margin_node_id,)
                                if margin_node_id is not None
                                else ()
                            )
                        ),
                        expected=_graph_node_observation(
                            margin_node_id, node_by_id
                        ),
                        observed=_graph_node_observation(
                            authored_margin, node_by_id
                        ),
                    )
                )
            else:
                issues.append(
                    _issue(
                        "compiler.force.binding_duplicate_source",
                        (*location, "margin_node_id"),
                        "Semantic V2 drafts must omit compiler-owned margin_node_id.",
                        options=(
                            f"Remove forces[{force_index}].margin_node_id and let the compiler bind it.",
                        ),
                        expected=_graph_node_observation(
                            force.get("margin_node_id", _MISSING), node_by_id
                        ),
                        observed=_graph_node_observation(
                            authored_margin, node_by_id
                        ),
                    )
                )
    return issues


def _find_simple_edge_paths(
    graph: PrimitiveGraph,
    source_node_id: str,
    target_node_id: str,
) -> tuple[tuple[str, ...], ...]:
    """Enumerate a bounded number of distinct directed edge paths.

    Node-only path resolution cannot distinguish two parallel PrimitiveGraph
    edges.  The V2 compiler must reject that ambiguity rather than choosing one
    arbitrary causal edge for a payoff witness.
    """

    if source_node_id == target_node_id:
        return ()
    outgoing: dict[str, list[tuple[str, str]]] = {
        node.node_id: [] for node in graph.nodes
    }
    for edge in graph.edges:
        outgoing[edge.source_node_id].append((edge.edge_id, edge.target_node_id))
    for edges in outgoing.values():
        edges.sort()
    found: list[tuple[str, ...]] = []
    stack: list[tuple[str, tuple[str, ...], tuple[str, ...]]] = [
        (source_node_id, (source_node_id,), ())
    ]
    while stack and len(found) < _MAX_PATH_ALTERNATIVES:
        node_id, seen_nodes, edge_ids = stack.pop()
        for edge_id, next_node_id in reversed(outgoing.get(node_id, [])):
            if next_node_id in seen_nodes:
                continue
            candidate_nodes = (*seen_nodes, next_node_id)
            candidate_edges = (*edge_ids, edge_id)
            if next_node_id == target_node_id:
                found.append(candidate_edges)
                if len(found) >= _MAX_PATH_ALTERNATIVES:
                    break
            else:
                stack.append((next_node_id, candidate_nodes, candidate_edges))
    return tuple(found)


def _margin_issue(
    issues: list[FramingAuditPreflightIssueV1],
    rule_id: str,
    location: tuple[str | int, ...],
    message: str,
    *,
    options: tuple[str, ...] = (),
    expected: str | None = None,
    observed: str | None = None,
) -> None:
    issues.append(
        _issue(
            rule_id,
            location,
            message,
            options=options,
            expected=expected,
            observed=observed,
        )
    )


def _reject_v2_hand_authored_margin_witnesses(
    payload: Mapping[str, Any],
) -> list[FramingAuditPreflightIssueV1]:
    """Keep every V2 witness binding compiler-owned, including null placeholders.

    V2 receives a free-form bundle payload so the projected JSON schema alone is
    not an enforcement boundary.  A hand-authored key on a step without a
    corresponding intent could otherwise bypass the V2 compiler entirely.
    V1 remains the explicit surface for a fully hand-authored canonical witness.
    """

    raw_steps = payload.get("causal_chain")
    if not isinstance(raw_steps, (list, tuple)):
        return []
    issues: list[FramingAuditPreflightIssueV1] = []
    for step_index, step in enumerate(raw_steps):
        if not isinstance(step, Mapping) or "active_margin_witness" not in step:
            continue
        _margin_issue(
            issues,
            "compiler.margin.full_witness_forbidden",
            (
                "bundle_payload",
                "causal_chain",
                step_index,
                "active_margin_witness",
            ),
            "V2 reserves active_margin_witness for deterministic compiler binding.",
            options=(
                "Remove active_margin_witness and provide a margin intent.",
                "Use the V1 semantic surface for a fully hand-authored witness.",
            ),
        )
    return issues


def _v2_missing_margin_intent_issues(
    bundle: FramingQualityBundle,
    graph: PrimitiveGraph,
    intents: tuple[MarginWitnessIntentV2, ...],
) -> list[FramingAuditPreflightIssueV1]:
    """Require V2 to name every V8-required witness before compilation ends.

    This is not a second economic acceptance test.  It reuses V8's exact
    fully-downgraded negative-revision predicate and otherwise asks only whether
    the model supplied an intent for a graph choice that V8 would require to be
    payoff-witnessed.  The unchanged candidate validator remains the final
    scientific authority.
    """

    all_witnesses_absent = all(
        step.active_margin_witness is None for step in bundle.causal_chain
    )
    if (
        bundle.proposed_action == "revise_framing"
        and all_witnesses_absent
        and _is_permitted_unwitnessed_negative_revision(bundle)
    ):
        return []
    if bundle.tension.tension_kind not in fq.MECHANISM_MARGIN_TENSION_KINDS:
        return []

    intent_steps = {intent.step_number for intent in intents}
    adjacency = _graph_adjacency(graph)
    node_by_id = {node.node_id: node for node in graph.nodes}
    issues: list[FramingAuditPreflightIssueV1] = []
    witnessed_choice_nodes = {
        step.active_margin_witness.decision_node_id
        for step in bundle.causal_chain
        if step.active_margin_witness is not None
    }
    missing_step_choice_nodes: set[str] = set()
    for step_index, step in enumerate(bundle.causal_chain):
        choice_nodes_on_step = {
            node.node_id
            for node in graph.nodes
            if node.kind == "choice"
            and _node_is_on_step(
                adjacency,
                source_node_id=step.source_node_id,
                target_node_id=step.target_node_id,
                node_id=node.node_id,
            )
        }
        newly_reached_choices = choice_nodes_on_step.difference(
            {step.source_node_id}
        )
        if newly_reached_choices and step.step_number not in intent_steps:
            missing_step_choice_nodes.update(newly_reached_choices)
            _margin_issue(
                issues,
                "compiler.margin.intent_missing",
                ("bundle_payload", "causal_chain", step_index),
                "A choice-dependent causal step needs one V2 margin intent.",
                options=(
                    f"Add a margin intent for causal step {step.step_number}.",
                    "Use the V1 semantic surface for a fully hand-authored witness.",
                ),
            )

    for force in bundle.forces:
        margin_node = node_by_id.get(force.margin_node_id)
        if (
            margin_node is None
            or margin_node.kind != "choice"
            or force.margin_node_id in witnessed_choice_nodes
            or force.margin_node_id in missing_step_choice_nodes
        ):
            continue
        _margin_issue(
            issues,
            "compiler.margin.intent_missing_force",
            ("margin_intents",),
            "An operative choice margin lacks a V2 intent that binds its payoff witness.",
            options=(
                f"Add an intent that binds force {force.force_id}.",
                "Use a fully downgraded V8 negative revision only when its exact predicate holds.",
            ),
        )
    return issues


def _apply_margin_intents(
    payload: dict[str, Any],
    graph: PrimitiveGraph,
    intents: tuple[MarginWitnessIntentV2, ...],
) -> list[FramingAuditPreflightIssueV1]:
    """Compile scientific margin intents only where graph bindings are exact."""

    issues: list[FramingAuditPreflightIssueV1] = []
    if not intents:
        return issues
    causal_steps = _mapping_list(payload.get("causal_chain"))
    steps_by_number: dict[int, tuple[int, dict[str, Any]]] = {}
    for step_index, step in enumerate(causal_steps):
        step_number = step.get("step_number")
        if isinstance(step_number, int) and step_number not in steps_by_number:
            steps_by_number[step_number] = (step_index, step)
    forces = {
        force.get("force_id"): force
        for force in _mapping_list(payload.get("forces"))
        if isinstance(force.get("force_id"), str)
    }
    node_by_id = {node.node_id: node for node in graph.nodes}
    adjacency = _graph_adjacency(graph)
    public_state_kinds = {
        "constraint",
        "equilibrium_object",
        "information",
        "institution",
        "interaction",
        "timing",
    }
    assessment_rows = _mapping_list(payload.get("benchmark_assessments"))

    for intent_index, intent in enumerate(intents):
        base_location = ("margin_intents", intent_index)
        start_count = len(issues)
        step_entry = steps_by_number.get(intent.step_number)
        if step_entry is None:
            _margin_issue(
                issues,
                "compiler.margin.step_unknown",
                (*base_location, "step_number"),
                "Margin intent does not name a causal-chain step.",
            )
            continue
        step_index, step = step_entry
        witness_location = (
            "bundle_payload",
            "causal_chain",
            step_index,
            "active_margin_witness",
        )
        source_node_id = step.get("source_node_id")
        target_node_id = step.get("target_node_id")
        force_ids = step.get("force_ids")
        if not (
            isinstance(source_node_id, str)
            and isinstance(target_node_id, str)
            and isinstance(force_ids, list)
            and all(isinstance(force_id, str) for force_id in force_ids)
        ):
            _margin_issue(
                issues,
                "compiler.margin.step_shape",
                witness_location,
                "The causal step must expose exact source, target, and force IDs.",
            )
            continue
        candidate_force_ids = tuple(force_ids)
        if intent.decision_force_id is not None:
            if intent.decision_force_id not in candidate_force_ids:
                _margin_issue(
                    issues,
                    "compiler.margin.decision_force",
                    (*base_location, "decision_force_id"),
                    "decision_force_id must be one of this causal step's declared forces.",
                    options=tuple(sorted(candidate_force_ids)),
                )
                continue
            candidate_force_ids = (intent.decision_force_id,)
        decision_candidates: list[str] = []
        for force_id in candidate_force_ids:
            force = forces.get(force_id)
            if force is None:
                _margin_issue(
                    issues,
                    "compiler.margin.force_unknown",
                    (*base_location, "decision_force_id"),
                    "The causal step names a force absent from the payload.",
                    options=tuple(sorted(forces)),
                )
                continue
            node_id = force.get("margin_node_id")
            node = node_by_id.get(node_id) if isinstance(node_id, str) else None
            if (
                node is not None
                and node.kind == "choice"
                and _node_is_on_step(
                    adjacency,
                    source_node_id=source_node_id,
                    target_node_id=target_node_id,
                    node_id=node.node_id,
                )
            ):
                decision_candidates.append(node.node_id)
        decision_candidates = sorted(set(decision_candidates))
        if len(decision_candidates) != 1:
            _margin_issue(
                issues,
                (
                    "compiler.margin.decision_missing"
                    if not decision_candidates
                    else "compiler.margin.decision_ambiguous"
                ),
                (*base_location, "decision_force_id"),
                "The compiler could not identify one exact choice margin on this step.",
                options=tuple(decision_candidates),
            )
            continue
        decision_node_id = decision_candidates[0]

        payoff_candidates = tuple(
            sorted(
                node.node_id
                for node in graph.nodes
                if node.kind == "preference_technology"
                and _find_simple_paths(adjacency, node.node_id, decision_node_id)
            )
        )
        payoff_node_ids: tuple[str, ...]
        if intent.payoff_node_id_disambiguators:
            invalid = tuple(
                node_id
                for node_id in intent.payoff_node_id_disambiguators
                if node_id not in payoff_candidates
            )
            if invalid:
                _margin_issue(
                    issues,
                    "compiler.margin.payoff_disambiguator",
                    (*base_location, "payoff_node_id_disambiguators"),
                    "Each payoff disambiguator must be an upstream payoff-basis node.",
                    options=payoff_candidates,
                )
                continue
            payoff_node_ids = intent.payoff_node_id_disambiguators
        elif len(payoff_candidates) == 1:
            payoff_node_ids = payoff_candidates
        else:
            _margin_issue(
                issues,
                (
                    "compiler.margin.payoff_missing"
                    if not payoff_candidates
                    else "compiler.margin.payoff_ambiguous"
                ),
                (*base_location, "payoff_node_id_disambiguators"),
                "The compiler could not identify one exact upstream payoff basis.",
                options=payoff_candidates,
            )
            continue

        consequence_entry = steps_by_number.get(intent.consequence_step_number)
        if consequence_entry is None:
            _margin_issue(
                issues,
                "compiler.margin.consequence_step_unknown",
                (*base_location, "consequence_step_number"),
                "consequence_step_number does not name a causal-chain step.",
            )
            continue
        _, consequence_step = consequence_entry
        consequence_node_id = consequence_step.get("target_node_id")
        if not isinstance(consequence_node_id, str):
            _margin_issue(
                issues,
                "compiler.margin.consequence_unbound",
                (*base_location, "consequence_step_number"),
                "The selected consequence step has no exact target node.",
            )
            continue
        edge_paths = _find_simple_edge_paths(
            graph, decision_node_id, consequence_node_id
        )
        if len(edge_paths) != 1:
            _margin_issue(
                issues,
                (
                    "compiler.margin.consequence_unreachable"
                    if not edge_paths
                    else "compiler.margin.consequence_ambiguous"
                ),
                (*base_location, "consequence_step_number"),
                "The decision-to-consequence graph path must be exact and unique.",
                options=tuple(" -> ".join(path) for path in edge_paths),
            )
            continue
        if not (
            _find_simple_paths(adjacency, target_node_id, consequence_node_id)
            or _find_simple_paths(adjacency, consequence_node_id, target_node_id)
        ):
            _margin_issue(
                issues,
                "compiler.margin.consequence_off_spine",
                (*base_location, "consequence_step_number"),
                "The selected consequence must remain on the witnessed causal spine.",
            )
            continue

        public_conditions: list[PublicStateCondition] = []
        for condition_index, condition in enumerate(intent.public_state_conditions):
            condition_location = (
                *base_location,
                "public_state_conditions",
                condition_index,
            )
            matching_rows = [
                row
                for row in assessment_rows
                if row.get("benchmark_id") == condition.benchmark_id
            ]
            if len(matching_rows) != 1:
                _margin_issue(
                    issues,
                    "compiler.margin.public_state_benchmark",
                    (*condition_location, "benchmark_id"),
                    "A public-state intent must name exactly one benchmark assessment.",
                    options=tuple(
                        sorted(
                            str(row["benchmark_id"])
                            for row in assessment_rows
                            if isinstance(row.get("benchmark_id"), str)
                        )
                    ),
                )
                continue
            matching_objects = [
                item
                for group_name in (
                    "changed",
                    "held_fixed",
                    "reoptimizing",
                    "still_endogenous",
                    "targets",
                )
                for item in _mapping_list(matching_rows[0].get(group_name))
                if item.get("object_id") == condition.object_id
            ]
            if len(matching_objects) != 1:
                _margin_issue(
                    issues,
                    (
                        "compiler.margin.public_state_object_missing"
                        if not matching_objects
                        else "compiler.margin.public_state_object_ambiguous"
                    ),
                    (*condition_location, "object_id"),
                    "A public-state intent must name one uniquely bound ledger object.",
                )
                continue
            state_node_id = matching_objects[0].get("primitive_node_id")
            state_node = (
                node_by_id.get(state_node_id)
                if isinstance(state_node_id, str)
                else None
            )
            if state_node is None or state_node.kind not in public_state_kinds:
                _margin_issue(
                    issues,
                    "compiler.margin.public_state_node",
                    (*condition_location, "object_id"),
                    "The selected ledger object must bind a public-state-compatible node.",
                )
                continue
            public_conditions.append(
                PublicStateCondition(
                    node_id=state_node.node_id,
                    relation=condition.relation,
                    value=condition.value,
                )
            )
        if len({item.node_id for item in public_conditions}) != len(public_conditions):
            _margin_issue(
                issues,
                "compiler.margin.public_state_duplicate_node",
                (*base_location, "public_state_conditions"),
                "Public-state conditions must resolve to distinct PrimitiveGraph nodes.",
            )
        if len(issues) != start_count:
            continue

        witness = ActiveMarginWitness(
            decision_node_id=decision_node_id,
            payoff_node_ids=payoff_node_ids,
            concrete_state=intent.concrete_state,
            decision_maker=intent.decision_maker,
            focal_action=intent.focal_action,
            alternative_action=intent.alternative_action,
            focal_payoff=intent.focal_payoff,
            alternative_payoff=intent.alternative_payoff,
            feasibility_basis=intent.feasibility_basis,
            best_response_inequality=intent.best_response_inequality,
            activity_status=intent.activity_status,
            status_basis=intent.status_basis,
            kill_condition=intent.kill_condition,
            consequence_binding=ChoiceConsequenceBinding(
                consequence_node_id=consequence_node_id,
                transition_kind=intent.transition_kind,
                causal_edge_ids=edge_paths[0],
                public_state_conditions=tuple(public_conditions),
                focal_consequence=intent.focal_consequence,
                alternative_consequence=intent.alternative_consequence,
                feasibility_basis=intent.consequence_feasibility_basis,
            ),
        )
        step["active_margin_witness"] = witness.model_dump(
            mode="json", exclude_none=False
        )
    return issues


def _v2_cross_field_issues(
    payload: Mapping[str, Any],
    graph: PrimitiveGraph,
    intents: tuple[MarginWitnessIntentV2, ...],
) -> list[FramingAuditPreflightIssueV1]:
    """Reject locked pair contradictions before unchanged V8 validation."""

    issues: list[FramingAuditPreflightIssueV1] = []
    node_by_id = {node.node_id: node for node in graph.nodes}
    rows = _mapping_list(payload.get("benchmark_assessments"))
    for row_index, row in enumerate(rows):
        benchmark_id = row.get("benchmark_id")
        stable_benchmark_id = (
            benchmark_id if isinstance(benchmark_id, str) else None
        )
        path = row.get("channel_path")
        if not (
            isinstance(path, list)
            and path
            and all(isinstance(node_id, str) for node_id in path)
        ):
            continue
        held_choices = {
            item.get("primitive_node_id"): item
            for item in _mapping_list(row.get("held_fixed"))
            if isinstance(item.get("primitive_node_id"), str)
            and node_by_id.get(item["primitive_node_id"]) is not None
            and node_by_id[item["primitive_node_id"]].kind == "choice"
        }
        traversed_fixed_choices = tuple(
            node_id for node_id in path if node_id in held_choices
        )
        target_node = node_by_id.get(path[-1])
        if traversed_fixed_choices and target_node is not None and target_node.kind == "outcome":
            first_fixed = traversed_fixed_choices[0]
            first_fixed_index = path.index(first_fixed)
            boundary = path[first_fixed_index - 1] if first_fixed_index else path[0]
            held_object_id = held_choices[first_fixed].get("object_id")
            issues.append(
                _issue(
                    "compiler.semantic_ledger.fixed_choice_channel",
                    (
                        "bundle_payload",
                        "benchmark_assessments",
                        row_index,
                        "channel_path",
                    ),
                    "A fixed comparison cannot carry its channel through a held-fixed choice to an outcome.",
                    benchmark_id=stable_benchmark_id,
                    object_id=(
                        held_object_id
                        if isinstance(held_object_id, str)
                        else None
                    ),
                    options=(
                        f"End the fixed comparison at {boundary} before {first_fixed}.",
                        "Move the choice to reoptimizing only if it honestly responds.",
                    ),
                    expected=f"channel terminating before held-fixed choice {first_fixed}",
                    observed=" -> ".join(path),
                )
            )

    force_entries = {
        force.get("force_id"): (force_index, force)
        for force_index, force in enumerate(_mapping_list(payload.get("forces")))
        if isinstance(force.get("force_id"), str)
    }
    steps_by_number = {
        step.get("step_number"): step
        for step in _mapping_list(payload.get("causal_chain"))
        if isinstance(step.get("step_number"), int)
    }
    adjacency = _graph_adjacency(graph)
    for intent in intents:
        step = steps_by_number.get(intent.step_number)
        if step is None:
            continue
        witness = step.get("active_margin_witness")
        if not isinstance(witness, Mapping):
            continue
        decision_node_id = witness.get("decision_node_id")
        if not isinstance(decision_node_id, str):
            continue
        force_ids = step.get("force_ids")
        if not isinstance(force_ids, list):
            continue
        selected_force_ids: tuple[str, ...]
        if intent.decision_force_id is not None:
            selected_force_ids = (intent.decision_force_id,)
        elif len(force_ids) == 1 and isinstance(force_ids[0], str):
            selected_force_ids = (force_ids[0],)
        else:
            selected_force_ids = tuple(
                force_id
                for force_id in force_ids
                if isinstance(force_id, str)
                and force_entries.get(force_id, (None, {}))[1].get(
                    "margin_node_id"
                )
                == decision_node_id
            )
        source_node_id = step.get("source_node_id")
        target_node_id = step.get("target_node_id")
        choice_options = (
            _choice_nodes_on_step(
                graph,
                adjacency,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                exclude_source=False,
            )
            if isinstance(source_node_id, str) and isinstance(target_node_id, str)
            else ()
        )
        for force_id in selected_force_ids:
            force_entry = force_entries.get(force_id)
            if force_entry is None:
                continue
            force_index, force = force_entry
            margin_node_id = force.get("margin_node_id")
            margin_node = (
                node_by_id.get(margin_node_id)
                if isinstance(margin_node_id, str)
                else None
            )
            if (
                margin_node is not None
                and margin_node.kind == "choice"
                and margin_node_id == decision_node_id
            ):
                continue
            issues.append(
                _issue(
                    "compiler.margin.witnessed_force_binding",
                    (
                        "bundle_payload",
                        "forces",
                        force_index,
                        "margin_node_id",
                    ),
                    "A force selected by a payoff witness must bind that exact choice node.",
                    options=choice_options,
                    expected=_graph_node_observation(
                        decision_node_id, node_by_id
                    ),
                    observed=_graph_node_observation(
                        margin_node_id, node_by_id
                    ),
                )
            )
    return issues


def _collect_semantic_ledger_issues(
    payload: Mapping[str, Any], graph: PrimitiveGraph
) -> tuple[list[FramingAuditPreflightIssueV1], tuple[str, ...]]:
    issues: list[FramingAuditPreflightIssueV1] = []
    node_kind = {node.node_id: node.kind for node in graph.nodes}
    direct_edges = {
        (edge.source_node_id, edge.target_node_id) for edge in graph.edges
    }
    active_nodes: set[str] = set()
    rows = _mapping_list(payload.get("benchmark_assessments"))
    for row_index, row in enumerate(rows):
        row_active_nodes: set[str] = set()
        benchmark_id = row.get("benchmark_id")
        stable_benchmark_id = benchmark_id if isinstance(benchmark_id, str) else None
        groups = {
            name: _mapping_list(row.get(name))
            for name in (
                "changed",
                "held_fixed",
                "reoptimizing",
                "still_endogenous",
                "targets",
            )
        }
        for group_name, objects in groups.items():
            for object_index, item in enumerate(objects):
                primitive_node_id = item.get("primitive_node_id")
                if primitive_node_id is None:
                    continue
                location = (
                    "bundle_payload",
                    "benchmark_assessments",
                    row_index,
                    group_name,
                    object_index,
                    "primitive_node_id",
                )
                if not isinstance(primitive_node_id, str) or primitive_node_id not in node_kind:
                    issues.append(
                        _issue(
                            "compiler.semantic_ledger.unknown_node",
                            location,
                            "Semantic ledger object references an unknown PrimitiveGraph node.",
                            benchmark_id=stable_benchmark_id,
                            object_id=(
                                item.get("object_id")
                                if isinstance(item.get("object_id"), str)
                                else None
                            ),
                        )
                    )

        for object_index, item in enumerate(groups["reoptimizing"]):
            primitive_node_id = item.get("primitive_node_id")
            object_id = item.get("object_id")
            if primitive_node_id is None:
                issues.append(
                    _issue(
                        "compiler.semantic_ledger.reoptimizing_binding_missing",
                        (
                            "bundle_payload",
                            "benchmark_assessments",
                            row_index,
                            "reoptimizing",
                            object_index,
                            "primitive_node_id",
                        ),
                        "A reoptimizing object requires an exact PrimitiveGraph choice binding.",
                        benchmark_id=stable_benchmark_id,
                        object_id=object_id if isinstance(object_id, str) else None,
                        options=(
                            "Bind the exact choice node.",
                            "Move a non-choice object out of reoptimizing.",
                        ),
                    )
                )
                continue
            if not isinstance(primitive_node_id, str) or primitive_node_id not in node_kind:
                continue
            if node_kind[primitive_node_id] != "choice":
                issues.append(
                    _issue(
                        "compiler.semantic_ledger.reoptimizing_node_kind",
                        (
                            "bundle_payload",
                            "benchmark_assessments",
                            row_index,
                            "reoptimizing",
                            object_index,
                            "primitive_node_id",
                        ),
                        "A reoptimizing object must bind an exact choice node.",
                        benchmark_id=stable_benchmark_id,
                        object_id=object_id if isinstance(object_id, str) else None,
                        options=(
                            "Bind the exact choice node.",
                            "Move a non-choice object out of reoptimizing.",
                        ),
                    )
                )
            else:
                active_nodes.add(primitive_node_id)
                row_active_nodes.add(primitive_node_id)

        for object_index, item in enumerate(groups["still_endogenous"]):
            semantic_level = item.get("semantic_level")
            primitive_node_id = item.get("primitive_node_id")
            object_id = item.get("object_id")
            allowed_kinds = (
                active_semantic_node_kinds(semantic_level)
                if isinstance(semantic_level, str)
                else None
            )
            # payoff_ledger and other non-active accounting levels deliberately
            # remain outside active-margin classification.
            if allowed_kinds is None:
                continue
            if primitive_node_id is None:
                issues.append(
                    _issue(
                        "compiler.semantic_ledger.endogenous_binding_missing",
                        (
                            "bundle_payload",
                            "benchmark_assessments",
                            row_index,
                            "still_endogenous",
                            object_index,
                            "primitive_node_id",
                        ),
                        "An active endogenous object requires an exact type-compatible graph binding.",
                        benchmark_id=stable_benchmark_id,
                        object_id=object_id if isinstance(object_id, str) else None,
                        options=(
                            "Bind an exact type-compatible PrimitiveGraph node.",
                            "Use a non-active accounting level only for a genuinely diagnostic row.",
                        ),
                    )
                )
                continue
            if not isinstance(primitive_node_id, str) or primitive_node_id not in node_kind:
                continue
            actual_kind = node_kind[primitive_node_id]
            if actual_kind not in allowed_kinds:
                compatible_levels = tuple(
                    sorted(
                        level
                        for level in ENDOGENOUS_ACTIVE_SEMANTIC_LEVELS
                        if actual_kind in (active_semantic_node_kinds(level) or ())
                    )
                )
                issues.append(
                    _issue(
                        "compiler.semantic_ledger.endogenous_node_kind",
                        (
                            "bundle_payload",
                            "benchmark_assessments",
                            row_index,
                            "still_endogenous",
                            object_index,
                            "semantic_level",
                        ),
                        "The declared endogenous semantic level is incompatible "
                        f"with PrimitiveGraph node kind {actual_kind}.",
                        benchmark_id=stable_benchmark_id,
                        object_id=object_id if isinstance(object_id, str) else None,
                        options=(
                            *(
                                f"Use {level} only if that is the honest economic role."
                                for level in compatible_levels
                            ),
                            "Bind a different type-compatible PrimitiveGraph node.",
                            "Use a non-active accounting level only for a genuinely diagnostic row.",
                        ),
                    )
                )
            else:
                active_nodes.add(primitive_node_id)
                row_active_nodes.add(primitive_node_id)

        movable_groups = (
            ("changed", groups["changed"]),
            ("reoptimizing", groups["reoptimizing"]),
            ("still_endogenous", groups["still_endogenous"]),
        )
        for held_index, held in enumerate(groups["held_fixed"]):
            held_node_id = held.get("primitive_node_id")
            fixing_level = held.get("fixing_level")
            overlaps = (
                fixing_level_overlaps(fixing_level)
                if isinstance(fixing_level, str)
                else frozenset()
            )
            if not isinstance(held_node_id, str):
                continue
            for movable_group, movable in movable_groups:
                for movable_index, item in enumerate(movable):
                    if (
                        item.get("primitive_node_id") != held_node_id
                        or item.get("semantic_level") not in overlaps
                    ):
                        continue
                    object_id = item.get("object_id")
                    issues.append(
                        _issue(
                            "compiler.semantic_ledger.fixed_movable_conflict",
                            (
                                "bundle_payload",
                                "benchmark_assessments",
                                row_index,
                                movable_group,
                                movable_index,
                                "primitive_node_id",
                            ),
                            "One graph node is held fixed and movable at overlapping semantic levels.",
                            benchmark_id=stable_benchmark_id,
                            object_id=object_id if isinstance(object_id, str) else None,
                            options=(
                                "Keep the node in only its honest fixed or movable role.",
                                "Split genuinely distinct semantic objects in the upstream PrimitiveGraph.",
                            ),
                        )
                    )

        path = row.get("channel_path")
        if not isinstance(path, list) or not all(isinstance(item, str) for item in path):
            continue
        if any((source, target) not in direct_edges for source, target in zip(path, path[1:])):
            issues.append(
                _issue(
                    "compiler.channel_path.not_exact",
                    (
                        "bundle_payload",
                        "benchmark_assessments",
                        row_index,
                        "channel_path",
                    ),
                    "channel_path contains a pair that is not a directed PrimitiveGraph edge.",
                    benchmark_id=stable_benchmark_id,
                )
            )
        changed_nodes = {
            item.get("primitive_node_id")
            for item in groups["changed"]
            if isinstance(item.get("primitive_node_id"), str)
        }
        target_nodes = {
            item.get("primitive_node_id")
            for item in groups["targets"]
            if isinstance(item.get("primitive_node_id"), str)
        }
        if len(path) >= 2 and (path[0] not in changed_nodes or path[-1] not in target_nodes):
            issues.append(
                _issue(
                    "compiler.channel_path.endpoint_mismatch",
                    (
                        "bundle_payload",
                        "benchmark_assessments",
                        row_index,
                        "channel_path",
                    ),
                    "Channel endpoints must be exact changed and target object bindings.",
                    benchmark_id=stable_benchmark_id,
                )
            )
        if (
            row.get("channel_kind") == "active_response"
            and len(path) >= 2
            and not set(path[1:-1]).intersection(row_active_nodes)
        ):
            issues.append(
                _issue(
                    "compiler.semantic_ledger.active_margin_missing",
                    (
                        "bundle_payload",
                        "benchmark_assessments",
                        row_index,
                        "channel_kind",
                    ),
                    "An active-response path needs an interior compatible response margin.",
                    benchmark_id=stable_benchmark_id,
                    options=(
                        "Bind the exact active response margin.",
                        "Downgrade the row if it is only diagnostic or a boundary comparison.",
                    ),
                )
            )
    return issues, tuple(sorted(active_nodes))


_MISSING = object()


def _payload_value_at_location(value: object, location: tuple[object, ...]) -> object:
    current = value
    for item in location:
        if isinstance(current, Mapping) and isinstance(item, str):
            current = current.get(item, _MISSING)
        elif isinstance(current, list) and isinstance(item, int):
            current = current[item] if 0 <= item < len(current) else _MISSING
        else:
            return _MISSING
        if current is _MISSING:
            return _MISSING
    return current


def _diagnostic_scalar(value: object) -> str:
    if value is _MISSING:
        return "<missing>"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value[:512] or "<empty>"
    if isinstance(value, Mapping):
        return "JSON object"
    if isinstance(value, list):
        return "JSON array"
    return type(value).__name__


def _schema_issues(
    error: ValidationError,
    payload: Mapping[str, Any],
) -> list[FramingAuditPreflightIssueV1]:
    issues: list[FramingAuditPreflightIssueV1] = []
    for item in error.errors(include_url=False):
        raw_location = tuple(item["loc"])
        context = item.get("ctx")
        expected = (
            _diagnostic_scalar(context["expected"])
            if isinstance(context, Mapping)
            and isinstance(context.get("expected"), str)
            else str(item["type"])
        )
        issues.append(
            _issue(
                "compiler.payload.schema",
                ("bundle_payload", *raw_location),
                str(item["msg"]),
                expected=expected,
                observed=_diagnostic_scalar(
                    _payload_value_at_location(payload, raw_location)
                ),
            )
        )
    return issues


def _prepare_semantic_draft(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV1 | FramingAuditSemanticDraftV2,
) -> _PreparedDraft:
    inputs_by_type, issues = _contract_inputs(snapshot, contract)
    payload = deepcopy(draft.bundle_payload)
    issues.extend(_bind_exact_inputs(payload, inputs_by_type))
    if isinstance(draft, FramingAuditSemanticDraftV2):
        issues.extend(_reject_v2_hand_authored_margin_witnesses(payload))

    graph: PrimitiveGraph | None = None
    graph_entity = inputs_by_type.get("PrimitiveGraph")
    if graph_entity is not None:
        parsed_graph = parse_theory_entity(graph_entity)
        if isinstance(parsed_graph, PrimitiveGraph):
            graph = parsed_graph
        else:
            issues.append(
                _issue(
                    "compiler.contract.primitive_graph_payload",
                    ("contract", "inputs", "PrimitiveGraph"),
                    "The exact PrimitiveGraph input has the wrong typed payload.",
                )
            )

    active_nodes: tuple[str, ...] = ()
    if graph is not None:
        if isinstance(draft, FramingAuditSemanticDraftV2):
            issues.extend(
                _apply_force_margin_bindings(
                    payload,
                    graph,
                    draft.margin_intents,
                    draft.force_margin_locators,
                )
            )
        issues.extend(_apply_channel_intents(payload, graph, draft.channel_intents))
        if isinstance(draft, FramingAuditSemanticDraftV2):
            issues.extend(_apply_margin_intents(payload, graph, draft.margin_intents))
            issues.extend(
                _v2_cross_field_issues(
                    payload,
                    graph,
                    draft.margin_intents,
                )
            )
        ledger_issues, active_nodes = _collect_semantic_ledger_issues(payload, graph)
        issues.extend(ledger_issues)

    bundle: FramingQualityBundle | None = None
    try:
        bundle = FramingQualityBundle.model_validate_json(
            canonical_json_bytes(payload), strict=True
        )
    except ValidationError as error:
        issues.extend(_schema_issues(error, payload))
    if (
        isinstance(draft, FramingAuditSemanticDraftV2)
        and graph is not None
        and bundle is not None
    ):
        issues.extend(
            _v2_missing_margin_intent_issues(
                bundle,
                graph,
                draft.margin_intents,
            )
        )

    exact_issues = _deduplicate_issues(issues)
    report = FramingAuditPreflightReportV1(
        passed=not exact_issues,
        issues=exact_issues,
        active_semantic_node_ids=active_nodes,
    )
    return _PreparedDraft(
        payload=payload,
        bundle=bundle,
        inputs_by_type=inputs_by_type,
        graph=graph,
        report=report,
    )


def preflight_framing_audit_semantic_draft(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV1,
) -> FramingAuditPreflightReportV1:
    """Batch the compiler-owned channel and semantic-ledger issues without writes."""

    return _prepare_semantic_draft(snapshot, contract, draft).report


def _v2_draft_guard_issues(
    draft: object,
) -> tuple[FramingAuditPreflightIssueV1, ...]:
    """Reject V1 or forged draft instances at the additive V2 entry points."""

    if type(draft) is not FramingAuditSemanticDraftV2:
        return (
            _issue(
                "compiler.v2.draft_type",
                ("semantic_draft_schema",),
                "The V2 compiler accepts an exact FramingAuditSemanticDraftV2 only.",
                expected="FramingAuditSemanticDraftV2",
                observed=type(draft).__name__,
            ),
        )
    if draft.semantic_draft_schema != _SEMANTIC_DRAFT_V2_SCHEMA:
        return (
            _issue(
                "compiler.v2.draft_schema",
                ("semantic_draft_schema",),
                "The V2 compiler requires its exact semantic draft schema.",
                expected=_SEMANTIC_DRAFT_V2_SCHEMA,
                observed=draft.semantic_draft_schema,
            ),
        )
    return ()


def preflight_framing_audit_semantic_draft_v2(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV2,
) -> FramingAuditPreflightReportV1:
    """Batch V2 graph binding and payload issues without writes or repair use."""

    guard_issues = _v2_draft_guard_issues(draft)
    if guard_issues:
        return FramingAuditPreflightReportV1(
            passed=False,
            issues=guard_issues,
        )
    assert type(draft) is FramingAuditSemanticDraftV2
    return _prepare_semantic_draft(snapshot, contract, draft).report


def _entity_ref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def _resolve_endpoint(
    endpoint: CandidateRelationEndpointV1,
    *,
    inputs_by_type: Mapping[str, EntityVersion],
    candidate_outputs: Mapping[str, tuple[EntityVersion, ...]],
) -> EntityVersion:
    if endpoint.binding_kind == "exact_input":
        entity = inputs_by_type[endpoint.entity_type]
        assert endpoint.entity_ref == _entity_ref(entity)
        return entity
    assert endpoint.output_ordinal is not None
    return candidate_outputs[endpoint.entity_type][endpoint.output_ordinal - 1]


def _compile_relation(
    template: CandidateHardRelationTemplateV1,
    *,
    relation_id: str,
    inputs_by_type: Mapping[str, EntityVersion],
    candidate_outputs: Mapping[str, tuple[EntityVersion, ...]],
    contract: CandidateAuthoringContractV1,
) -> RelationVersion:
    source = _resolve_endpoint(
        template.source,
        inputs_by_type=inputs_by_type,
        candidate_outputs=candidate_outputs,
    )
    target = _resolve_endpoint(
        template.target,
        inputs_by_type=inputs_by_type,
        candidate_outputs=candidate_outputs,
    )
    semantic_hash = template.upstream_semantic_hash
    if template.upstream_semantic_hash_binding == "runtime_facet_semantic_hash_v1":
        semantic_hash = facet_semantic_hash(source, template.source.facet)
    assert semantic_hash is not None
    bindings = contract.transaction_bindings
    return RelationVersion(
        relation_id=relation_id,
        relation_type=template.relation_type,
        version=1,
        project_id=bindings.project_id,
        source=_entity_ref(source),
        target=_entity_ref(target),
        dependency_mode="hard",
        upstream=SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet=template.source.facet,
            semantic_hash=semantic_hash,
        ),
        downstream=FacetPathRef(
            entity_id=target.entity_id,
            version=target.version,
            facet=template.target.facet,
        ),
        privacy=bindings.privacy,
        access_compartments=bindings.access_compartments,
        created_at=bindings.created_at,
    )


def _compile_framing_audit_semantic_draft(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV1 | FramingAuditSemanticDraftV2,
) -> Transaction:
    """Compile one fresh-audit semantic draft without accepting the Transaction.

    The returned object must still pass the unchanged registry-v8 canonical
    candidate validator.  Calling this function is pure and does not consume a
    model repair, create a run record, stage bytes, or update the canonical head.
    """

    prepared = _prepare_semantic_draft(snapshot, contract, draft)
    if not prepared.report.passed:
        raise FramingAuditCompilationError(prepared.report.issues)
    assert prepared.bundle is not None
    bundle_payload = prepared.bundle
    bindings = contract.transaction_bindings
    run_id = bindings.route_run_id
    transaction_id = f"transaction.{run_id}.framing.audit"
    bundle_id = f"framing.quality.{run_id}"
    dossier_id = f"dossier.g1.framing.{run_id}"
    relation_ids = tuple(
        f"relation.{run_id}.framing.{index}"
        for index in range(1, len(_EXPECTED_TEMPLATE_IDS) + 1)
    )
    historical_entity_ids = {entity.entity_id for entity in snapshot.entity_versions}
    historical_relation_ids = {
        relation.relation_id for relation in snapshot.relation_versions
    }
    collisions = tuple(
        object_id
        for object_id in (bundle_id, dossier_id)
        if object_id in historical_entity_ids
    )
    relation_collisions = tuple(
        relation_id
        for relation_id in relation_ids
        if relation_id in historical_relation_ids
    )
    if transaction_id in snapshot.transaction_ids or collisions or relation_collisions:
        collision_issues: list[FramingAuditPreflightIssueV1] = []
        if transaction_id in snapshot.transaction_ids:
            collision_issues.append(
                _issue(
                    "compiler.generated_id.transaction_collision",
                    ("generated_ids", "transaction_id"),
                    f"Generated transaction ID already exists: {transaction_id}.",
                )
            )
        for object_id in collisions:
            collision_issues.append(
                _issue(
                    "compiler.generated_id.entity_collision",
                    ("generated_ids", "entity_id"),
                    f"Generated entity ID already exists: {object_id}.",
                )
            )
        for relation_id in relation_collisions:
            collision_issues.append(
                _issue(
                    "compiler.generated_id.relation_collision",
                    ("generated_ids", "relation_id"),
                    f"Generated relation ID already exists: {relation_id}.",
                )
            )
        raise FramingAuditCompilationError(tuple(collision_issues))

    bundle_entity = EntityVersion(
        entity_id=bundle_id,
        entity_type="FramingQualityBundle",
        version=1,
        project_id=bindings.project_id,
        title=draft.bundle_title,
        summary=draft.bundle_summary,
        status=ScientificStatus(
            formal_validity="not_applicable",
            interpretation_validity="unassessed",
        ),
        facets=pack_framing_quality_payload(bundle_payload),
        privacy=bindings.privacy,
        access_compartments=bindings.access_compartments,
        created_at=bindings.created_at,
    )
    source_dossier_entity = prepared.inputs_by_type["GateDossier"]
    source_dossier = parse_theory_entity(source_dossier_entity)
    assert isinstance(source_dossier, GateDossier)
    bundle_ref = _entity_ref(bundle_entity)
    replacement_payload = GateDossier(
        gate_kind="G1_question_benchmark",
        research_question_ref=bundle_payload.research_question_ref,
        ordered_object_refs=(*source_dossier.ordered_object_refs, bundle_ref),
        ordered_artifact_refs=source_dossier.ordered_artifact_refs,
        requirements=(
            *source_dossier.requirements,
            GateRequirement(
                requirement_id="g1.framing_quality",
                description="Economics framing and attribution pass preflight.",
                evidence_refs=(bundle_ref,),
                recorded_condition=(
                    "evidence_supplied"
                    if bundle_payload.proposed_action == "ready_for_g1"
                    else "risk_disclosed"
                ),
            ),
        ),
        proposed_action=(
            "approve"
            if bundle_payload.proposed_action == "ready_for_g1"
            else "revise"
        ),
        rationale="The source package is strengthened by the framing audit.",
        prepared_at=bindings.created_at,
    )
    dossier_entity = EntityVersion(
        entity_id=dossier_id,
        entity_type="GateDossier",
        version=1,
        project_id=bindings.project_id,
        title=draft.replacement_dossier_title,
        summary=draft.replacement_dossier_summary,
        status=ScientificStatus(
            formal_validity="not_applicable",
            interpretation_validity="unassessed",
        ),
        facets=pack_theory_payload(replacement_payload),
        privacy=bindings.privacy,
        access_compartments=bindings.access_compartments,
        created_at=bindings.created_at,
    )
    candidate_outputs = {
        "FramingQualityBundle": (bundle_entity,),
        "GateDossier": (dossier_entity,),
    }
    relations = tuple(
        _compile_relation(
            template,
            relation_id=relation_id,
            inputs_by_type=prepared.inputs_by_type,
            candidate_outputs=candidate_outputs,
            contract=contract,
        )
        for template, relation_id in zip(
            contract.output_contract.required_relation_templates,
            relation_ids,
        )
    )
    candidate_refs = (
        _entity_ref(bundle_entity),
        _entity_ref(dossier_entity),
        *(
            RelationVersionRef(
                relation_id=relation.relation_id,
                version=relation.version,
            )
            for relation in relations
        ),
    )
    return Transaction(
        transaction_id=transaction_id,
        transaction_schema=bindings.transaction_schema,
        origin=bindings.origin,
        project_id=bindings.project_id,
        base_revision=bindings.base_revision,
        route_run_id=bindings.route_run_id,
        route_id=bindings.route_id,
        route_run_hash=bindings.route_run_hash,
        context_manifest_hash=bindings.context_manifest_hash,
        compiled_context_hash=bindings.compiled_context_hash,
        actor=bindings.actor,
        intent=draft.transaction_intent,
        operations=(
            CreateEntityOp(entity=bundle_entity),
            CreateEntityOp(entity=dossier_entity),
            *(CreateRelationOp(relation=relation) for relation in relations),
            RecordRouteOutcomeOp(
                outcome=RouteOutcome(
                    route_run_id=bindings.route_run_id,
                    route_id=bindings.route_id,
                    outcome="completed_with_candidate",
                    rationale=draft.outcome_rationale,
                    candidate_refs=candidate_refs,
                    privacy=bindings.privacy,
                    access_compartments=bindings.access_compartments,
                )
            ),
        ),
        evidence_refs=bindings.required_entity_evidence_refs,
        privacy=bindings.privacy,
        access_compartments=bindings.access_compartments,
        created_at=bindings.created_at,
        parent_transaction_hash=bindings.parent_transaction_hash,
    )


def compile_framing_audit_semantic_draft(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV1,
) -> Transaction:
    """Compile one V1 semantic draft without accepting the Transaction."""

    return _compile_framing_audit_semantic_draft(snapshot, contract, draft)


def compile_framing_audit_semantic_draft_v2(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV2,
) -> Transaction:
    """Compile one V2 semantic draft without accepting the Transaction."""

    guard_issues = _v2_draft_guard_issues(draft)
    if guard_issues:
        raise FramingAuditCompilationError(guard_issues)
    assert type(draft) is FramingAuditSemanticDraftV2
    return _compile_framing_audit_semantic_draft(snapshot, contract, draft)


__all__ = [
    "BenchmarkChannelIntentV1",
    "FramingAuditCompilationError",
    "FramingAuditPreflightIssueV1",
    "FramingAuditPreflightReportV1",
    "FramingAuditSemanticAuthoringSurfaceV1",
    "FramingAuditSemanticAuthoringSurfaceV2",
    "FramingAuditSemanticDraftV1",
    "FramingAuditSemanticDraftV2",
    "ForceMarginLocatorV2",
    "MarginWitnessIntentV2",
    "PublicStateConditionIntentV2",
    "compile_framing_audit_semantic_authoring_contract",
    "compile_framing_audit_semantic_authoring_contract_v2",
    "compile_framing_audit_semantic_draft",
    "compile_framing_audit_semantic_draft_v2",
    "preflight_framing_audit_semantic_draft",
    "preflight_framing_audit_semantic_draft_v2",
]
