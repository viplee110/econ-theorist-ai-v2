"""Route-bound mechanical authoring contract for external scientific agents.

The contract exposes schemas and immutable bindings that an agent otherwise
would have to infer from Python source.  It deliberately contains no proposed
scientific content and does not weaken canonical candidate validation.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from . import authoring as a
from . import profile_craft as pc
from . import theory as t
from .codec import canonical_json_bytes, sha256_digest
from .machine.models import WorkPacketV1
from .models import (
    FACET_ORDER,
    Actor,
    Digest,
    Facet,
    PrivacyLabel,
    NonEmptyString,
    RelationVersion,
    RouteEntityRequirement,
    RouteOutcome,
    RouteRelationRequirement,
    RouteSpecV2,
    StableId,
    StrictModel,
    Transaction,
)
from .policy import route_spec_by_hash
from .runs import read_run, transaction_bindings
from .runtime import StoreLayout


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
    required_route_outcome_count: Literal[1] = 1
    relation_json_schema: dict[str, Any]
    route_outcome_json_schema: dict[str, Any]


class CandidateAuthoringContractV1(StrictModel):
    """Self-contained mechanical contract attached to a delivered WorkPacket."""

    authoring_contract_schema: Literal[
        "econ-theorist/candidate-authoring-contract/v1"
    ] = "econ-theorist/candidate-authoring-contract/v1"
    work_packet_hash: Digest
    packet_schema: Literal["econ-theorist/work-packet/v1"]
    packet_compiler_version: Literal[1]
    engine_version: NonEmptyString
    engine_semantics_hash: Digest
    transaction_bindings: CandidateTransactionBindingsV1
    output_locations: CandidateOutputLocationsV1
    transaction_json_schema: dict[str, Any]
    payload_schemas: tuple[CandidatePayloadSchemaV1, ...]
    output_contract: CandidateRouteOutputContractV1
    authoring_instructions: tuple[NonEmptyString, ...]


_AUTHORING_INSTRUCTIONS = (
    "Use work_packet.instruction_text and work_packet.compiled_context for scientific judgment; this authoring contract supplies mechanics only.",
    "Write one bare Transaction JSON object, not a candidate wrapper, at output_locations.candidate_logical_path; write helper files only below output_locations.shadow_logical_root.",
    "Copy every field in transaction_bindings that also appears in transaction_json_schema exactly into the Transaction (binding_schema is contract metadata), including base_revision and created_at; choose only transaction_id, intent, preconditions, changed_facets, operations, evidence_refs, and authority_basis as the route and schemas require.",
    "For each typed entity, put {schema: payload_schema_id, payload: <schema-valid object>} in owner_facet and set every listed empty_facet to an empty object.",
    "Set every new EntityVersion and RelationVersion project_id, privacy, access_compartments, and created_at exactly to the corresponding transaction_bindings values; never rely on privacy or compartment defaults.",
    "Use only output_contract allowed operation, entity, and relation types; satisfy every output cardinality and the exact scientific exit conditions in work_packet.instruction_text.",
    "Include exactly one route.outcome operation bound to transaction_bindings.route_run_id and transaction_bindings.route_id, with the same privacy and access compartments; candidate_refs must enumerate every exact canonical object produced by the Transaction, including any entity, relation, artifact, blocker, or other schema-permitted reference required by the route validator.",
    "Do not fabricate a human decision or approval; obey every work_packet.forbidden_actions entry and stop if the route requires unavailable human authority.",
    "The candidate source may be ordinary readable UTF-8 JSON and may end with a newline. The bridge validates it as a strict Transaction and computes the digest from engine-canonical Transaction bytes; do not hash the source file bytes or put a digest inside the object.",
)


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
    )
    output_locations = CandidateOutputLocationsV1(
        candidate_logical_path=packet.candidate_logical_path,
        shadow_logical_root=packet.shadow_logical_root,
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
        relation_json_schema=RelationVersion.model_json_schema(mode="validation"),
        route_outcome_json_schema=RouteOutcome.model_json_schema(mode="validation"),
    )
    return CandidateAuthoringContractV1(
        work_packet_hash=work_packet_hash,
        packet_schema=packet.packet_schema,
        packet_compiler_version=packet.packet_compiler_version,
        engine_version=packet.engine_version,
        engine_semantics_hash=packet.engine_semantics_hash,
        transaction_bindings=bindings,
        output_locations=output_locations,
        transaction_json_schema=Transaction.model_json_schema(mode="validation"),
        payload_schemas=tuple(
            _payload_contract(requirement)
            for requirement in route.required_output_entities
        ),
        output_contract=output_contract,
        authoring_instructions=_AUTHORING_INSTRUCTIONS,
    )


def candidate_authoring_contract_hash(
    contract: CandidateAuthoringContractV1,
) -> str:
    return sha256_digest(canonical_json_bytes(contract))


__all__ = [
    "CandidateAuthoringContractV1",
    "CandidateOutputLocationsV1",
    "CandidatePayloadSchemaV1",
    "CandidateRouteOutputContractV1",
    "CandidateTransactionBindingsV1",
    "candidate_authoring_contract_hash",
    "compile_candidate_authoring_contract",
]
