"""Route-bound mechanical authoring contract for external scientific agents.

The contract exposes schemas and immutable bindings that an agent otherwise
would have to infer from Python source.  It deliberately contains no proposed
scientific content and does not weaken canonical candidate validation.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Annotated, Any, Literal

from pydantic import Field, model_serializer, model_validator

from . import authoring as a
from . import framing_quality as fq
from . import profile_craft as pc
from . import theory as t
from .codec import canonical_json_bytes, sha256_digest
from .machine.models import WorkPacketV1
from .models import (
    FACET_ORDER,
    Actor,
    Digest,
    EntityVersion,
    EntityVersionRef,
    Facet,
    PrivacyLabel,
    NonEmptyString,
    RelationVersion,
    RouteEntityRequirement,
    RouteOutcome,
    RouteRelationRequirement,
    RouteSpecV2,
    Snapshot,
    StableId,
    StrictModel,
    Transaction,
)
from .policy import (
    ROUTE_REGISTRY_V5_HASH,
    ROUTE_REGISTRY_V6_HASH,
    ROUTE_REGISTRY_V7_HASH,
    ROUTE_REGISTRY_V8_HASH,
    SELECTOR_VERSION_DECOMPOSITION_REFRESH,
    route_spec_by_hash,
)
from .runs import read_run, transaction_bindings
from .runtime import StoreLayout
from .runtime.freshness import authority_semantic_hash, facet_semantic_hash
from .runtime.replay import replay_at


class CandidateTransactionBindingsV1(StrictModel):
    """Fields that must be copied exactly into the candidate Transaction."""

    binding_schema: Literal[
        "econ-theorist/candidate-transaction-bindings/v1"
    ] = "econ-theorist/candidate-transaction-bindings/v1"
    transaction_schema: Literal[1] = 1
    origin: Literal["route_run"] = "route_run"
    project_id: StableId
    base_revision: Digest
    parent_transaction_hash: Digest
    route_run_id: StableId
    route_id: StableId
    route_run_hash: Digest
    context_manifest_hash: Digest
    compiled_context_hash: Digest
    actor: Actor
    privacy: PrivacyLabel
    access_compartments: tuple[StableId, ...]
    created_at: NonEmptyString
    required_entity_evidence_refs: tuple[EntityVersionRef, ...] = ()

    @model_serializer(mode="wrap")
    def _omit_historical_evidence_binding(self, handler: Any) -> dict[str, Any]:
        serialized = handler(self)
        if not self.required_entity_evidence_refs:
            serialized.pop("required_entity_evidence_refs", None)
        return serialized

    def model_post_init(self, __context: Any) -> None:
        if self.base_revision != self.parent_transaction_hash:
            raise ValueError(
                "candidate base revision must equal its parent transaction hash"
            )


class CandidateOutputLocationsV1(StrictModel):
    """Engine-declared writable locations; these are not Transaction fields."""

    output_locations_schema: Literal[
        "econ-theorist/candidate-output-locations/v1"
    ] = "econ-theorist/candidate-output-locations/v1"
    candidate_logical_path: NonEmptyString
    shadow_logical_root: NonEmptyString


class CandidatePayloadSchemaV1(StrictModel):
    """Typed payload and five-facet packing contract for one route output."""

    payload_contract_schema: Literal[
        "econ-theorist/candidate-payload-schema/v1"
    ] = "econ-theorist/candidate-payload-schema/v1"
    entity_type: StableId
    min_count: Annotated[int, Field(ge=0)]
    max_count: Annotated[int, Field(ge=1)] | None
    owner_facet: Facet
    empty_facets: tuple[Facet, ...]
    payload_schema_id: NonEmptyString
    payload_json_schema: dict[str, Any]


class CandidateModelInvariantV1(StrictModel):
    """Cross-field rule that ordinary JSON Schema cannot express exactly."""

    model_invariant_schema: Literal[
        "econ-theorist/candidate-model-invariant/v1"
    ] = "econ-theorist/candidate-model-invariant/v1"
    invariant_id: StableId
    model: StableId
    condition: NonEmptyString
    requirement: NonEmptyString
    repair_hint: NonEmptyString


class CandidateRelationEndpointV1(StrictModel):
    """One exact input or uniquely indexed candidate-output relation endpoint."""

    endpoint_schema: Literal[
        "econ-theorist/candidate-relation-endpoint/v1"
    ] = "econ-theorist/candidate-relation-endpoint/v1"
    binding_kind: Literal["exact_input", "candidate_output"]
    entity_type: StableId
    entity_ref: EntityVersionRef | None = None
    output_ordinal: Annotated[int, Field(ge=1)] | None = None
    facet: Facet
    field_path: Literal[None] = None

    @model_validator(mode="after")
    def _binding_is_unambiguous(self) -> "CandidateRelationEndpointV1":
        if self.binding_kind == "exact_input":
            if self.entity_ref is None or self.output_ordinal is not None:
                raise ValueError(
                    "exact-input relation endpoints require only an entity_ref"
                )
        elif self.entity_ref is not None or self.output_ordinal is None:
            raise ValueError(
                "candidate-output relation endpoints require only an output_ordinal"
            )
        return self


class CandidateHardRelationTemplateV1(StrictModel):
    """Required whole-facet hard relation projected by a route exit validator."""

    relation_template_schema: Literal[
        "econ-theorist/candidate-hard-relation-template/v1"
    ] = "econ-theorist/candidate-hard-relation-template/v1"
    template_id: StableId
    relation_type: StableId
    count: Literal[1] = 1
    relation_id_policy: Literal["new_unique"] = "new_unique"
    version: Literal[1] = 1
    supersedes: Literal[None] = None
    dependency_mode: Literal["hard"] = "hard"
    source: CandidateRelationEndpointV1
    target: CandidateRelationEndpointV1
    upstream_semantic_hash_binding: Literal[
        "contract_value", "runtime_facet_semantic_hash_v1"
    ]
    upstream_semantic_hash: Digest | None = None

    @model_validator(mode="after")
    def _hash_binding_is_exact(self) -> "CandidateHardRelationTemplateV1":
        if self.upstream_semantic_hash_binding == "contract_value":
            if self.upstream_semantic_hash is None:
                raise ValueError(
                    "contract-value relation templates require a semantic hash"
                )
        else:
            if self.upstream_semantic_hash is not None:
                raise ValueError(
                    "runtime facet hash templates cannot carry a precomputed hash"
                )
            if self.source.binding_kind != "candidate_output":
                raise ValueError(
                    "runtime facet hash templates require a candidate-output source"
                )
        return self


class CandidateEndpointConstraintV1(StrictModel):
    """A small route-exit endpoint fact exposed to the authoring model."""

    endpoint_constraint_schema: Literal[
        "econ-theorist/candidate-endpoint-constraint/v1"
    ] = "econ-theorist/candidate-endpoint-constraint/v1"
    relation_type: StableId
    endpoint_role: Literal["source", "target"]
    entity_type: StableId
    output_ordinal: Annotated[int, Field(ge=1)]
    count: Literal[1] = 1
    repair_hint: NonEmptyString


class CandidateRouteOutputContractV1(StrictModel):
    """Exact generic route exit surface; route instructions retain science."""

    output_contract_schema: Literal[
        "econ-theorist/candidate-route-output-contract/v1"
    ] = "econ-theorist/candidate-route-output-contract/v1"
    route_id: StableId
    route_version: Annotated[int, Field(ge=1)]
    entry_validator_id: StableId
    exit_validator_id: StableId
    allowed_operation_classes: tuple[StableId, ...]
    allowed_entity_types: tuple[StableId, ...]
    allowed_relation_types: tuple[StableId, ...]
    required_output_entities: tuple[RouteEntityRequirement, ...]
    required_output_relations: tuple[RouteRelationRequirement, ...]
    required_relation_templates: tuple[CandidateHardRelationTemplateV1, ...] = ()
    required_endpoint_constraints: tuple[CandidateEndpointConstraintV1, ...] = ()
    required_route_outcome_count: Literal[1] = 1
    model_invariants: tuple[CandidateModelInvariantV1, ...]
    relation_json_schema: dict[str, Any]
    route_outcome_json_schema: dict[str, Any]

    @model_serializer(mode="wrap")
    def _omit_pre_projection_default(self, handler: Any) -> dict[str, Any]:
        """Keep frozen contracts byte-compatible while extending this v1 model."""

        serialized = handler(self)
        if not self.required_relation_templates:
            serialized.pop("required_relation_templates", None)
        if not self.required_endpoint_constraints:
            serialized.pop("required_endpoint_constraints", None)
        return serialized


class CandidateAuthoringContractV1(StrictModel):
    """Self-contained mechanical contract attached to a delivered WorkPacket."""

    authoring_contract_schema: Literal[
        "econ-theorist/candidate-authoring-contract/v1"
    ] = "econ-theorist/candidate-authoring-contract/v1"
    work_packet_hash: Digest
    packet_schema: Literal["econ-theorist/work-packet/v1"]
    packet_compiler_version: Literal[1, 2]
    engine_version: NonEmptyString
    engine_semantics_hash: Digest
    candidate_draft_semantics: Literal[
        "runtime_facet_hash_materialization_v1"
    ] | None = None
    transaction_bindings: CandidateTransactionBindingsV1
    output_locations: CandidateOutputLocationsV1
    transaction_json_schema: dict[str, Any]
    payload_schemas: tuple[CandidatePayloadSchemaV1, ...]
    output_contract: CandidateRouteOutputContractV1
    authoring_instructions: tuple[NonEmptyString, ...]

    @model_serializer(mode="wrap")
    def _omit_historical_draft_default(self, handler: Any) -> dict[str, Any]:
        """Keep pre-materialization contracts byte-for-byte resumable."""

        serialized = handler(self)
        if self.candidate_draft_semantics is None:
            serialized.pop("candidate_draft_semantics", None)
        return serialized


_HISTORICAL_RELATION_TEMPLATE_AUTHORING_INSTRUCTION = (
    "Instantiate every output_contract.required_relation_template exactly. Copy exact_input entity_ref values; bind candidate_output endpoints to the exact output of that entity type and ordinal. For runtime_facet_semantic_hash_v1, compute econ_theorist.runtime.freshness.facet_semantic_hash over the complete candidate source EntityVersion and the declared whole facet; do not hash the raw facet JSON alone."
)


_RELATION_TEMPLATE_AUTHORING_INSTRUCTION = (
    "Instantiate every output_contract.required_relation_template exactly. Copy exact_input entity_ref values; bind candidate_output endpoints to the exact output of that entity type and ordinal. Only for a template whose upstream_semantic_hash_binding is runtime_facet_semantic_hash_v1, write upstream.semantic_hash as explicit JSON null. The bridge computes and injects the exact hash in memory from the complete candidate source EntityVersion before strict canonical validation, candidate identity, capture, staging, or commit; do not compute, copy, or guess that hash."
)


_AUTHORING_INSTRUCTION_PREFIX = (
    "Use work_packet.instruction_text and work_packet.compiled_context for scientific judgment; this authoring contract supplies mechanics only.",
    "Write one bare Transaction JSON object, not a candidate wrapper, at output_locations.candidate_logical_path; write helper files only below output_locations.shadow_logical_root.",
    "Copy every field in transaction_bindings that also appears in transaction_json_schema exactly into the Transaction (binding_schema is contract metadata), including base_revision and created_at; choose only transaction_id, intent, preconditions, changed_facets, operations, evidence_refs, and authority_basis as the route and schemas require.",
    "For each typed entity, put {schema: payload_schema_id, payload: <schema-valid object>} in owner_facet and set every listed empty_facet to an empty object.",
    "Set every new EntityVersion and RelationVersion project_id, privacy, access_compartments, and created_at exactly to the corresponding transaction_bindings values; never rely on privacy or compartment defaults.",
    "Use only output_contract allowed operation, entity, and relation types; satisfy every output cardinality and the exact scientific exit conditions in work_packet.instruction_text.",
)


_AUTHORING_INSTRUCTION_SUFFIX = (
    "JSON Schema is necessary but not sufficient: obey output_contract.model_invariants exactly and use the bridge's structured candidate diagnostics for any remaining model-level repair.",
    "Include exactly one route.outcome operation bound to transaction_bindings.route_run_id and transaction_bindings.route_id, with the same privacy and access compartments; candidate_refs must enumerate every exact canonical object produced by the Transaction, including any entity, relation, artifact, blocker, or other schema-permitted reference required by the route validator.",
    "Do not fabricate a human decision or approval; obey every work_packet.forbidden_actions entry and stop if the route requires unavailable human authority.",
    "The candidate source may be ordinary readable UTF-8 JSON and may end with a newline. The bridge validates it as a strict Transaction and computes the digest from engine-canonical Transaction bytes; do not hash the source file bytes or put a digest inside the object.",
)


_AUTHORING_INSTRUCTIONS = (
    *_AUTHORING_INSTRUCTION_PREFIX,
    _RELATION_TEMPLATE_AUTHORING_INSTRUCTION,
    *_AUTHORING_INSTRUCTION_SUFFIX,
)


_PRE_MATERIALIZATION_AUTHORING_INSTRUCTIONS = (
    *_AUTHORING_INSTRUCTION_PREFIX,
    _HISTORICAL_RELATION_TEMPLATE_AUTHORING_INSTRUCTION,
    *_AUTHORING_INSTRUCTION_SUFFIX,
)


_HISTORICAL_AUTHORING_INSTRUCTIONS = (
    *_AUTHORING_INSTRUCTION_PREFIX,
    *_AUTHORING_INSTRUCTION_SUFFIX,
)


_V2_INPUT_EVIDENCE_AUTHORING_INSTRUCTION = (
    "For packet compiler v2, copy output_contract.required_entity_evidence_refs "
    "exactly, in order, into Transaction.evidence_refs as EntityVersionRefs. "
    "Preconditions and route.outcome candidate_refs do not substitute for "
    "Transaction.evidence_refs; they have different meanings."
)


_MODEL_INVARIANTS = (
    CandidateModelInvariantV1(
        invariant_id="relation.trace_only_facets",
        model="RelationVersion",
        condition="dependency_mode == 'trace_only'",
        requirement="upstream and downstream must both be null",
        repair_hint="Use trace_only for provenance links; relation importance alone does not justify hard invalidation.",
    ),
    CandidateModelInvariantV1(
        invariant_id="relation.invalidating_exact_facets",
        model="RelationVersion",
        condition="dependency_mode != 'trace_only'",
        requirement="upstream must bind the exact source entity/version and downstream must bind the exact target entity/version",
        repair_hint="Either add both exact facet endpoints or change a provenance-only link to trace_only.",
    ),
    CandidateModelInvariantV1(
        invariant_id="relation.scope_sensitive_xor",
        model="RelationVersion",
        condition="dependency_mode == 'scope_sensitive'",
        requirement="exactly one of scope_ref or scope_overlap is required; other modes must omit scope_overlap",
        repair_hint="Choose exact scope equality or typed overlap evidence, but never both.",
    ),
    CandidateModelInvariantV1(
        invariant_id="relation.version_chain",
        model="RelationVersion",
        condition="all relation versions",
        requirement="version 1 omits supersedes; version n > 1 supersedes version n - 1 with the same relation_id",
        repair_hint="Bind the exact immediately preceding immutable relation version.",
    ),
)


_FRAMING_MODEL_INVARIANTS = (
    CandidateModelInvariantV1(
        invariant_id="framing.aggregate_invariance",
        model="AggregateInvarianceAssessment",
        condition="claims_aggregate_fixed == true",
        requirement="pointwise_policy_fixed must be true and weighting_distribution_status must be fixed or not_applicable",
        repair_hint="Downgrade the aggregate claim or record how the weighting distribution, transition law, and composition remain fixed; otherwise expect aggregate_invariance_unsupported.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.active_response",
        model="BenchmarkFramingAssessment",
        condition="channel_kind == active_response",
        requirement="at least one type-compatible reoptimizing choice or endogenous transition, distribution, or equilibrium margin must lie on the interior of the exact PrimitiveGraph channel_path",
        repair_hint="Bind the actual active response margin to a compatible PrimitiveGraph node or downgrade the row to a diagnostic/boundary comparison; an outcome label or frozen payoff ledger is placebo_control.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.selection_assurance",
        model="BenchmarkFramingAssessment",
        condition="selection_assurance.status is selector_only or unresolved",
        requirement="attribution_strength cannot be clean, a linked disclosed gap is required, and proposed_action cannot be ready_for_g1",
        repair_hint="State that the selector is only a convention, downgrade attribution, and continue diagnosis; do not claim selection robustness.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.benchmark_coverage",
        model="FramingQualityBundle",
        condition="all framing candidates",
        requirement="benchmark_assessments must cover every BenchmarkSet benchmark_id exactly once",
        repair_hint="Copy the exact nested benchmark IDs and provide one semantic-ledger row per benchmark.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.primitive_paths",
        model="FramingQualityBundle",
        condition="all forces, causal steps, and benchmark channels",
        requirement="every node must exist in PrimitiveGraph; forces and causal steps must be nonzero; every declared force must be used; each cited step must be an ordered subpath of its force; channel_path neighbors must be exact directed edges; the three causal steps must close",
        repair_hint="Use the supplied PrimitiveGraph node IDs and edges; if the required path is absent, propose revise_framing rather than inventing a connection.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.semantic_ledger",
        model="BenchmarkFramingAssessment",
        condition="objects bind primitive_node_id values",
        requirement="reoptimizing choices and endogenous active margins must match PrimitiveNode.kind, and one node cannot be fixed and movable at an overlapping semantic level",
        repair_hint="Bind choices to choice nodes and transitions, distributions, or equilibrium margins to equilibrium-object nodes; split distinct semantic levels into distinct graph nodes when necessary.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.archetype_tension",
        model="ArchetypeTension",
        condition="result_archetype == mechanism_explanation",
        requirement="use causal_channel for a one-direction mechanism or force_conflict when opposing forces actually generate the puzzle; only conflict and reversal tensions require a counterforce",
        repair_hint="Do not invent an opposing force for a single active channel, and do not omit the baseline/counterforce structure from a genuine reversal.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.force_conflict_geometry",
        model="FramingQualityBundle",
        condition="tension.tension_kind is force_conflict or sign_or_threshold_reversal",
        requirement="include at least one baseline_force and one countervailing_force; every baseline and countervailing force must act on the same target_node_id; all baseline directions must be raises_target and all countervailing directions lowers_target, or all baseline directions lowers_target and all countervailing directions raises_target; the causal chain must use both roles",
        repair_hint="Bind the two forces to one shared economic target and encode genuinely opposite effects; if there is no shared-target opposition, use causal_channel rather than manufacturing a force conflict.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.active_margin_witness",
        model="FramingQualityBundle",
        condition="a mechanism-oriented causal-chain step relies on an operative PrimitiveGraph choice margin",
        requirement="identify one concrete state and two feasible actions available at that same choice margin, compare their payoffs, and state the inequality under which the response is nontrivial; do not invent an action witness for a purely mechanical or technological step with no choice on its ordered path; an inactive margin kills or downgrades the claimed link, and an unresolved margin cannot support ready_for_g1",
        repair_hint="Supply the same-state two-action payoff comparison for each operative choice margin, or honestly mark the link inactive or unresolved and downgrade the proposed action.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.noncompensatory_action",
        model="FramingQualityBundle",
        condition="proposed_action == ready_for_g1",
        requirement="no disclosed gap, unresolved selection or aggregate weighting risk, diagnostic-only channel, or weak/unresolved attribution may remain; known endogenous composition and qualified attribution are admissible when fully traced",
        repair_hint="Use continue_diagnostic or revise_framing and let the replacement dossier propose revise whenever a material framing risk remains.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.replacement_dossier",
        model="GateDossier",
        condition="audit.framing_economics output",
        requirement="create a new ID at version 1, preserve the source dossier requirements and ordered refs, append the bundle ref and g1.framing_quality requirement, and never supersede the immutable source dossier",
        repair_hint="Create a replacement GateDossier; propose approve only for ready_for_g1, otherwise propose revise.",
    ),
)


_V6_ONLY_FRAMING_INVARIANTS = frozenset(
    {
        "framing.force_conflict_geometry",
        "framing.active_margin_witness",
    }
)
_HISTORICAL_FRAMING_MODEL_INVARIANTS = tuple(
    invariant
    for invariant in _FRAMING_MODEL_INVARIANTS
    if invariant.invariant_id not in _V6_ONLY_FRAMING_INVARIANTS
)


_V7_FRAMING_MODEL_INVARIANTS = (
    CandidateModelInvariantV1(
        invariant_id="framing.choice_consequence_binding",
        model="ActiveMarginWitness",
        condition="audit.framing_economics route version 7 payoff witness",
        requirement="consequence_binding must be explicit and must connect the witnessed action comparison to one exact causal consequence through ordered PrimitiveGraph edges under an explicit public-state class",
        repair_hint="Name the consequence node, transition direction, ordered causal edge IDs, and public-state conditions that make the focal and alternative actions economically distinct.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.distinctive_mechanism_spine",
        model="BenchmarkFramingAssessment",
        condition="audit.framing_economics route version 7 benchmark row",
        requirement="distinctive_mechanism must be explicit; an active claim must identify a different contrast benchmark and an exact focal-only node/edge spine, consequence, transition, and public-state class, while an honest same-mechanism comparison must use not_claimed",
        repair_hint="Do not manufacture benchmark distinctiveness: either bind the exact contrast-specific spine or record not_claimed; use unresolved only with the required causal-attribution disclosure.",
    ),
    CandidateModelInvariantV1(
        invariant_id="framing.distinctive_mechanism_contribution_status",
        model="FramingQualityBundle",
        condition="audit.framing_economics route version 7 output",
        requirement="distinctive_mechanism_contribution_status must be explicit and agree with every benchmark row: claimed needs at least one supported active distinctive mechanism and no unresolved row; not_claimed requires every row to disclaim distinctiveness; unresolved requires an unresolved row and the prescribed downgrade",
        repair_hint="Choose claimed, not_claimed, or unresolved only after completing every benchmark-level distinctive_mechanism assessment; an honest shared mechanism is not_claimed, not a failed active claim.",
    ),
)

_V8_FRAMING_MODEL_INVARIANTS = (
    CandidateModelInvariantV1(
        invariant_id="framing.unwitnessed_negative_revision",
        model="FramingQualityBundle",
        condition="audit.framing_economics route version 8 has no active-margin payoff witness",
        requirement="use revise_framing only; disclose a causal-attribution or reoptimization gap with an exact current upstream repair target; leave every witness absent, downgrade every benchmark away from active_response and clean attribution, make no aggregate-fixed or distinctive-mechanism claim, and never use this diagnosis for ready_for_g1",
        repair_hint="Do not fabricate a payoff comparison. Repair the named upstream object, then rerun the audit with a connected concrete payoff witness if the mechanism is to be claimed active.",
    ),
)


def _model_invariants_for_route(
    route_id: str,
    *,
    relation_templates_enabled: bool = False,
    route_version: int | None = None,
) -> tuple[CandidateModelInvariantV1, ...]:
    if route_id == "audit.framing_economics":
        framing_invariants = (
            _FRAMING_MODEL_INVARIANTS
            if relation_templates_enabled
            else _HISTORICAL_FRAMING_MODEL_INVARIANTS
        )
        v7_invariants = (
            _V7_FRAMING_MODEL_INVARIANTS if route_version in {7, 8} else ()
        )
        v8_invariants = (
            _V8_FRAMING_MODEL_INVARIANTS if route_version == 8 else ()
        )
        return (
            *_MODEL_INVARIANTS,
            *framing_invariants,
            *v7_invariants,
            *v8_invariants,
        )
    return _MODEL_INVARIANTS


def _payload_registration(
    entity_type: str,
) -> tuple[type[StrictModel], Facet, str]:
    registrations: list[tuple[type[StrictModel], Facet, str]] = []
    theory_model = t.THEORY_PAYLOAD_MODELS.get(entity_type)
    if theory_model is not None:
        registrations.append(
            (
                theory_model,
                t.THEORY_PAYLOAD_OWNER_FACETS[entity_type],
                t.theory_schema_id(entity_type),
            )
        )
    authoring_model = a.AUTHORING_PAYLOAD_MODELS.get(entity_type)
    if authoring_model is not None:
        registrations.append(
            (
                authoring_model,
                a.AUTHORING_PAYLOAD_OWNER_FACETS[entity_type],
                a.authoring_schema_id(entity_type),
            )
        )
    profile_model = pc.PROFILE_CRAFT_PAYLOAD_MODELS.get(entity_type)
    if profile_model is not None:
        registrations.append(
            (
                profile_model,
                pc.PROFILE_CRAFT_PAYLOAD_OWNER_FACETS[entity_type],
                pc.profile_craft_schema_id(entity_type),
            )
        )
    framing_model = fq.FRAMING_QUALITY_PAYLOAD_MODELS.get(entity_type)
    if framing_model is not None:
        registrations.append(
            (
                framing_model,
                fq.FRAMING_QUALITY_PAYLOAD_OWNER_FACETS[entity_type],
                fq.framing_quality_schema_id(entity_type),
            )
        )
    if len(registrations) != 1:
        raise ValueError(
            f"route output {entity_type!r} must have one exact typed payload registration"
        )
    return registrations[0]


def _payload_contract(
    requirement: RouteEntityRequirement,
) -> CandidatePayloadSchemaV1:
    model, owner, schema_id = _payload_registration(requirement.entity_type)
    return CandidatePayloadSchemaV1(
        entity_type=requirement.entity_type,
        min_count=requirement.min_count,
        max_count=requirement.max_count,
        owner_facet=owner,
        empty_facets=tuple(facet for facet in FACET_ORDER if facet != owner),
        payload_schema_id=schema_id,
        payload_json_schema=model.model_json_schema(mode="validation"),
    )


def _freeze_pre_v7_framing_payload_contract(
    contract: CandidatePayloadSchemaV1,
    *,
    route_version: int,
) -> CandidatePayloadSchemaV1:
    """Remove v7-only optional surfaces from exact frozen v5/v6 schemas."""

    if contract.entity_type != "FramingQualityBundle":
        return contract
    schema = deepcopy(contract.payload_json_schema)
    definitions = schema.get("$defs", {})
    schema.get("properties", {}).pop(
        "distinctive_mechanism_contribution_status", None
    )
    schema["required"] = [
        name
        for name in schema.get("required", [])
        if name != "distinctive_mechanism_contribution_status"
    ]
    active_margin = definitions.get("ActiveMarginWitness", {}).get(
        "properties", {}
    )
    active_margin.pop("consequence_binding", None)
    active_schema = definitions.get("ActiveMarginWitness", {})
    active_schema["required"] = [
        name
        for name in active_schema.get("required", [])
        if name != "consequence_binding"
    ]
    assessment = definitions.get("BenchmarkFramingAssessment", {}).get(
        "properties", {}
    )
    assessment.pop("distinctive_mechanism", None)
    assessment_schema = definitions.get("BenchmarkFramingAssessment", {})
    assessment_schema["required"] = [
        name
        for name in assessment_schema.get("required", [])
        if name != "distinctive_mechanism"
    ]
    for name in (
        "ChoiceConsequenceBinding",
        "DistinctiveMechanismAssessment",
        "PublicStateCondition",
    ):
        definitions.pop(name, None)
    if route_version == 5:
        causal_schema = definitions.get("CausalChainStep", {})
        causal_schema.get("properties", {}).pop("active_margin_witness", None)
        causal_schema["required"] = [
            name
            for name in causal_schema.get("required", [])
            if name != "active_margin_witness"
        ]
        definitions.pop("ActiveMarginWitness", None)
    return contract.model_copy(update={"payload_json_schema": schema})


def _require_schema_property(
    object_schema: dict[str, Any],
    property_name: str,
    *,
    model_name: str,
) -> None:
    properties = object_schema.get("properties")
    if not isinstance(properties, dict) or property_name not in properties:
        raise ValueError(
            f"v7 candidate schema lacks {model_name}.{property_name}"
        )
    required = set(object_schema.get("required", []))
    required.add(property_name)
    object_schema["required"] = [
        name for name in properties if name in required
    ]


def _make_schema_property_non_null(
    object_schema: dict[str, Any],
    property_name: str,
    *,
    model_name: str,
) -> None:
    properties = object_schema.get("properties")
    if not isinstance(properties, dict):
        raise ValueError(f"v7 candidate schema lacks {model_name} properties")
    property_schema = properties.get(property_name)
    if not isinstance(property_schema, dict):
        raise ValueError(
            f"v7 candidate schema lacks {model_name}.{property_name}"
        )
    alternatives = property_schema.get("anyOf")
    if not isinstance(alternatives, list):
        raise ValueError(
            f"v7 candidate schema cannot narrow {model_name}.{property_name}"
        )
    non_null = [
        item
        for item in alternatives
        if not (isinstance(item, dict) and item.get("type") == "null")
    ]
    if len(non_null) != 1 or len(non_null) == len(alternatives):
        raise ValueError(
            f"v7 candidate schema has ambiguous {model_name}.{property_name}"
        )
    narrowed = deepcopy(non_null[0])
    for metadata in ("description", "title"):
        if metadata in property_schema and metadata not in narrowed:
            narrowed[metadata] = property_schema[metadata]
    properties[property_name] = narrowed


def _project_v7_framing_payload_contract(
    contract: CandidatePayloadSchemaV1,
) -> CandidatePayloadSchemaV1:
    """Make v7's route-required research declarations visible to agents."""

    if contract.entity_type != "FramingQualityBundle":
        return contract
    schema = deepcopy(contract.payload_json_schema)
    definitions = schema.get("$defs")
    if not isinstance(definitions, dict):
        raise ValueError("v7 framing candidate schema lacks model definitions")
    _require_schema_property(
        schema,
        "distinctive_mechanism_contribution_status",
        model_name="FramingQualityBundle",
    )
    _make_schema_property_non_null(
        schema,
        "distinctive_mechanism_contribution_status",
        model_name="FramingQualityBundle",
    )
    for model_name, property_name in (
        ("BenchmarkFramingAssessment", "distinctive_mechanism"),
        ("ActiveMarginWitness", "consequence_binding"),
    ):
        object_schema = definitions.get(model_name)
        if not isinstance(object_schema, dict):
            raise ValueError(f"v7 candidate schema lacks {model_name}")
        _require_schema_property(
            object_schema,
            property_name,
            model_name=model_name,
        )
        _make_schema_property_non_null(
            object_schema,
            property_name,
            model_name=model_name,
        )
    return contract.model_copy(update={"payload_json_schema": schema})


_FRAMING_RELATION_INPUTS = (
    ("ResearchQuestion", "framing.audits.research_question"),
    ("BenchmarkSet", "framing.audits.benchmark_set"),
    ("PrimitiveGraph", "framing.audits.primitive_graph"),
    ("GateDossier", "framing.audits.source_g1_dossier"),
)
_FRAMING_ROUTE_ID = "audit.framing_economics"
_FRAMING_FROZEN_ROUTE_VERSION = 5
_FRAMING_V6_ROUTE_VERSION = 6
_FRAMING_ROUTE_VERSION = 7
_FRAMING_V8_ROUTE_VERSION = 8
_FRAMING_EXIT_VALIDATOR_ID = "framing_quality_route_exit.v1"
_FRAMING_V8_EXIT_VALIDATOR_ID = "framing_quality_route_exit.v2"
_FRAMING_RELATION_CARDINALITIES = (
    ("audits", 4, 4),
    ("governs", 1, 1),
)


def _candidate_output_endpoint(entity_type: str) -> CandidateRelationEndpointV1:
    _, owner_facet, _ = _payload_registration(entity_type)
    return CandidateRelationEndpointV1(
        binding_kind="candidate_output",
        entity_type=entity_type,
        output_ordinal=1,
        facet=owner_facet,
    )


def _exact_input_endpoint(entity: EntityVersion) -> CandidateRelationEndpointV1:
    _, owner_facet, _ = _payload_registration(entity.entity_type)
    return CandidateRelationEndpointV1(
        binding_kind="exact_input",
        entity_type=entity.entity_type,
        entity_ref=EntityVersionRef(
            entity_id=entity.entity_id,
            version=entity.version,
        ),
        facet=owner_facet,
    )


def _whole_facet_hash(snapshot: Snapshot, entity: EntityVersion, facet: Facet) -> str:
    if facet == "authority":
        return authority_semantic_hash(
            entity,
            snapshot.decisions,
            snapshot.effective_decisions,
        )
    return facet_semantic_hash(entity, facet)


def _relation_templates_for_route(
    route: RouteSpecV2,
    packet: WorkPacketV1,
    snapshot: Snapshot,
) -> tuple[CandidateHardRelationTemplateV1, ...]:
    """Project exact route-specific hard dependencies without changing a route."""

    if route.route_id != packet.route_id or route.route_version != packet.route_version:
        raise ValueError(
            "relation-template projection requires the exact resolved WorkPacket route"
        )
    if route.route_id != _FRAMING_ROUTE_ID:
        return ()

    if packet.route_registry_hash == ROUTE_REGISTRY_V5_HASH:
        expected_version = _FRAMING_FROZEN_ROUTE_VERSION
    elif packet.route_registry_hash == ROUTE_REGISTRY_V6_HASH:
        expected_version = _FRAMING_V6_ROUTE_VERSION
    elif packet.route_registry_hash == ROUTE_REGISTRY_V7_HASH:
        expected_version = _FRAMING_ROUTE_VERSION
    elif packet.route_registry_hash == ROUTE_REGISTRY_V8_HASH:
        expected_version = _FRAMING_V8_ROUTE_VERSION
    else:
        raise ValueError(
            "framing relation templates reject an unknown route registry"
        )
    expected_route = route_spec_by_hash(
        _FRAMING_ROUTE_ID,
        packet.route_registry_hash,
    )
    if (
        route.route_version != expected_version
        or canonical_json_bytes(route) != canonical_json_bytes(expected_route)
    ):
        raise ValueError(
            "framing relation templates require the exact frozen or active "
            "framing route semantics"
        )

    # Registry v5 predates relation-template projection.  Its immutable packets
    # must remain byte-for-byte resumable with the historical empty contract.
    if expected_version == _FRAMING_FROZEN_ROUTE_VERSION:
        return ()

    relation_cardinalities = tuple(
        (item.relation_type, item.min_count, item.max_count)
        for item in route.required_output_relations
    )
    if (
        route.route_version
        not in {
            _FRAMING_V6_ROUTE_VERSION,
            _FRAMING_ROUTE_VERSION,
            _FRAMING_V8_ROUTE_VERSION,
        }
        or route.exit_validator_id
        != (
            _FRAMING_V8_EXIT_VALIDATOR_ID
            if route.route_version == _FRAMING_V8_ROUTE_VERSION
            else _FRAMING_EXIT_VALIDATOR_ID
        )
        or relation_cardinalities != _FRAMING_RELATION_CARDINALITIES
    ):
        raise ValueError(
            "framing relation templates require the exact active framing route "
            "version, exit validator, and relation cardinalities"
        )

    exact_entities = {
        (entity.entity_id, entity.version): entity
        for entity in snapshot.entity_versions
    }
    focused_entities: list[EntityVersion] = []
    for reference in packet.focus_refs:
        entity = exact_entities.get((reference.entity_id, reference.version))
        if entity is None:
            raise ValueError(
                "framing relation templates require every exact WorkPacket focus"
            )
        focused_entities.append(entity)

    by_type: dict[str, list[EntityVersion]] = {}
    for entity in focused_entities:
        by_type.setdefault(entity.entity_type, []).append(entity)
    resolved_inputs: dict[str, EntityVersion] = {}
    for entity_type, _ in _FRAMING_RELATION_INPUTS:
        matches = by_type.get(entity_type, [])
        if len(matches) != 1:
            raise ValueError(
                "framing relation templates require one exact focused "
                f"{entity_type}"
            )
        resolved_inputs[entity_type] = matches[0]

    bundle_output = _candidate_output_endpoint("FramingQualityBundle")
    dossier_output = _candidate_output_endpoint("GateDossier")
    audit_templates: list[CandidateHardRelationTemplateV1] = []
    for entity_type, template_id in _FRAMING_RELATION_INPUTS:
        source = _exact_input_endpoint(resolved_inputs[entity_type])
        audit_templates.append(
            CandidateHardRelationTemplateV1(
                template_id=template_id,
                relation_type="audits",
                source=source,
                target=bundle_output,
                upstream_semantic_hash_binding="contract_value",
                upstream_semantic_hash=_whole_facet_hash(
                    snapshot,
                    resolved_inputs[entity_type],
                    source.facet,
                ),
            )
        )
    return (
        *audit_templates,
        CandidateHardRelationTemplateV1(
            template_id="framing.governs.replacement_g1_dossier",
            relation_type="governs",
            source=bundle_output,
            target=dossier_output,
            upstream_semantic_hash_binding="runtime_facet_semantic_hash_v1",
        ),
    )


def _endpoint_constraints_for_route(
    route: RouteSpecV2, packet: WorkPacketV1
) -> tuple[CandidateEndpointConstraintV1, ...]:
    if packet.packet_compiler_version < 2 or route.route_id != "decompose.primitives":
        return ()
    refresh_v2 = (
        packet.context_selector_version == SELECTOR_VERSION_DECOMPOSITION_REFRESH
    )
    return (
        CandidateEndpointConstraintV1(
            relation_type="decomposes",
            endpoint_role="target",
            entity_type="PrimitiveGraph",
            output_ordinal=1,
            repair_hint=(
                (
                    "Use the exact focused ResearchQuestion as source and the "
                    "new PrimitiveGraph as target. This is provenance-only: "
                    "set dependency_mode to trace_only and set upstream and "
                    "downstream to null; do not compute a semantic hash."
                )
                if refresh_v2
                else (
                    "At least one decomposes relation must target the new "
                    "PrimitiveGraph output; if the endpoints are reversed, "
                    "swap source and target."
                )
            ),
        ),
    )


def _candidate_transaction_schema(
    *, runtime_facet_hash_drafts: bool
) -> dict[str, Any]:
    """Expose a draft-only null without weakening canonical Transaction."""

    schema = Transaction.model_json_schema(mode="validation")
    if not runtime_facet_hash_drafts:
        return schema
    schema = deepcopy(schema)
    semantic_hash = schema["$defs"]["SemanticFacetRef"]["properties"][
        "semantic_hash"
    ]
    title = semantic_hash.get("title", "Semantic Hash")
    digest_schema = {
        key: value for key, value in semantic_hash.items() if key != "title"
    }
    schema["$defs"]["SemanticFacetRef"]["properties"]["semantic_hash"] = {
        "anyOf": [digest_schema, {"type": "null"}],
        "description": (
            "A digest in canonical Transactions. Candidate drafts may use null "
            "only at the exact runtime_facet_semantic_hash_v1 template location."
        ),
        "title": title,
    }
    return schema


def compile_candidate_authoring_contract(
    layout: StoreLayout,
    packet: WorkPacketV1,
    work_packet_hash: str,
) -> CandidateAuthoringContractV1:
    """Compile one deterministic contract from exact canonical run resources."""

    if sha256_digest(canonical_json_bytes(packet)) != work_packet_hash:
        raise ValueError("candidate contract received a mismatched WorkPacket hash")
    run = read_run(layout, packet.route_run_id)
    route = route_spec_by_hash(packet.route_id, packet.route_registry_hash)
    if not isinstance(route, RouteSpecV2):
        raise ValueError("candidate authoring contracts require a typed v2+ route")
    provenance = transaction_bindings(layout, packet.route_run_id)
    expected_entity_types = tuple(
        item.entity_type for item in route.required_output_entities
    )
    expected_relation_types = tuple(
        item.relation_type for item in route.required_output_relations
    )
    if (
        run.project_id != packet.project_id
        or run.base_revision != packet.base_head
        or run.route_run_id != packet.route_run_id
        or run.route_id != packet.route_id
        or run.route_version != packet.route_version
        or run.actor.actor_id != packet.actor_role
        or run.privacy_clearance != packet.privacy_clearance
        or run.compartments != packet.compartments
        or route.route_version != packet.route_version
        or packet.allowed_operation_classes != route.allowed_operations
        or packet.required_output_entity_types != expected_entity_types
        or packet.required_output_relation_types != expected_relation_types
        or provenance["route_run_hash"] != packet.route_run_hash
        or provenance["context_manifest_hash"] != packet.context_manifest_hash
        or provenance["compiled_context_hash"] != packet.compiled_context_hash
    ):
        raise ValueError("candidate contract resources differ from the exact WorkPacket")
    if route.entry_validator_id is None or route.exit_validator_id is None:
        raise ValueError("typed route lacks exact entry or exit validator binding")

    base_snapshot = replay_at(layout, packet.base_head)
    try:
        expected_focus_refs = tuple(
            EntityVersionRef(
                entity_id=entity_id,
                version=base_snapshot.current_entities[entity_id],
            )
            for entity_id in run.focus_entity_ids
        )
    except KeyError as exc:
        raise ValueError(
            "candidate contract canonical run focus is absent at its exact base"
        ) from exc
    if packet.focus_refs != expected_focus_refs:
        raise ValueError(
            "candidate contract WorkPacket focus refs differ from the canonical "
            "run focus at its exact base"
        )

    bindings = CandidateTransactionBindingsV1(
        project_id=packet.project_id,
        base_revision=packet.base_head,
        parent_transaction_hash=packet.base_head,
        route_run_id=packet.route_run_id,
        route_id=packet.route_id,
        route_run_hash=packet.route_run_hash,
        context_manifest_hash=packet.context_manifest_hash,
        compiled_context_hash=packet.compiled_context_hash,
        actor=run.actor,
        privacy=packet.privacy_clearance,
        access_compartments=packet.compartments,
        created_at=run.created_at,
        required_entity_evidence_refs=(
            packet.focus_refs if packet.packet_compiler_version >= 2 else ()
        ),
    )
    output_locations = CandidateOutputLocationsV1(
        candidate_logical_path=packet.candidate_logical_path,
        shadow_logical_root=packet.shadow_logical_root,
    )
    relation_templates = _relation_templates_for_route(
        route,
        packet,
        base_snapshot,
    )
    output_contract = CandidateRouteOutputContractV1(
        route_id=route.route_id,
        route_version=route.route_version,
        entry_validator_id=route.entry_validator_id,
        exit_validator_id=route.exit_validator_id,
        allowed_operation_classes=route.allowed_operations,
        allowed_entity_types=route.allowed_entity_types,
        allowed_relation_types=route.allowed_relation_types,
        required_output_entities=route.required_output_entities,
        required_output_relations=route.required_output_relations,
        required_endpoint_constraints=_endpoint_constraints_for_route(route, packet),
        required_relation_templates=relation_templates,
        model_invariants=_model_invariants_for_route(
            route.route_id,
            relation_templates_enabled=bool(relation_templates),
            route_version=route.route_version,
        ),
        relation_json_schema=RelationVersion.model_json_schema(mode="validation"),
        route_outcome_json_schema=RouteOutcome.model_json_schema(mode="validation"),
    )
    # Registry/route v7-v8 are durable public contract boundaries. They keep
    # every v1-v6 contract byte-frozen while preserving their own exact drafts.
    runtime_hash_drafts = bool(relation_templates) and (
        (
            packet.route_registry_hash == ROUTE_REGISTRY_V7_HASH
            and route.route_version == _FRAMING_ROUTE_VERSION
        )
        or (
            packet.route_registry_hash == ROUTE_REGISTRY_V8_HASH
            and route.route_version == _FRAMING_V8_ROUTE_VERSION
        )
    )
    authoring_instructions = (
        _AUTHORING_INSTRUCTIONS
        if runtime_hash_drafts
        else (
            _PRE_MATERIALIZATION_AUTHORING_INSTRUCTIONS
            if relation_templates
            else _HISTORICAL_AUTHORING_INSTRUCTIONS
        )
    )
    if packet.packet_compiler_version >= 2:
        authoring_instructions = (
            *authoring_instructions,
            _V2_INPUT_EVIDENCE_AUTHORING_INSTRUCTION,
        )
    return CandidateAuthoringContractV1(
        work_packet_hash=work_packet_hash,
        packet_schema=packet.packet_schema,
        packet_compiler_version=packet.packet_compiler_version,
        engine_version=packet.engine_version,
        engine_semantics_hash=packet.engine_semantics_hash,
        candidate_draft_semantics=(
            "runtime_facet_hash_materialization_v1"
            if runtime_hash_drafts
            else None
        ),
        transaction_bindings=bindings,
        output_locations=output_locations,
        transaction_json_schema=_candidate_transaction_schema(
            runtime_facet_hash_drafts=runtime_hash_drafts
        ),
        payload_schemas=tuple(
            (
                _freeze_pre_v7_framing_payload_contract(
                    _payload_contract(requirement),
                    route_version=route.route_version,
                )
                if route.route_id == _FRAMING_ROUTE_ID
                and route.route_version
                in {_FRAMING_FROZEN_ROUTE_VERSION, _FRAMING_V6_ROUTE_VERSION}
                else (
                    _project_v7_framing_payload_contract(
                        _payload_contract(requirement)
                    )
                    if route.route_id == _FRAMING_ROUTE_ID
                    and route.route_version
                    in {_FRAMING_ROUTE_VERSION, _FRAMING_V8_ROUTE_VERSION}
                    else _payload_contract(requirement)
                )
            )
            for requirement in route.required_output_entities
        ),
        output_contract=output_contract,
        authoring_instructions=authoring_instructions,
    )


def candidate_authoring_contract_hash(
    contract: CandidateAuthoringContractV1,
) -> str:
    return sha256_digest(canonical_json_bytes(contract))


__all__ = [
    "CandidateAuthoringContractV1",
    "CandidateHardRelationTemplateV1",
    "CandidateEndpointConstraintV1",
    "CandidateOutputLocationsV1",
    "CandidatePayloadSchemaV1",
    "CandidateRelationEndpointV1",
    "CandidateRouteOutputContractV1",
    "CandidateTransactionBindingsV1",
    "candidate_authoring_contract_hash",
    "compile_candidate_authoring_contract",
]
