"""Noncanonical Phase 5B theorem-team sidecars for claim verification.

The module declares two sealed advisory lanes around one immutable
``verify.claims_proofs_and_interpretation`` WorkPacket.  Both lanes are bound
to every and only ``ProofObligation`` retained by the packet's exact
``ClaimGraph`` closure.  They cannot write canonical state, construct a
candidate, or confirm a human gate.  The coordinator remains the sole
candidate author and uses the unchanged ``candidate.complete`` path.
"""

from __future__ import annotations

from typing import Any, Literal, TypeVar

from pydantic import model_validator

from . import theory as t
from .codec import canonical_json_bytes, sha256_digest
from .machine.models import OperationKey, WorkPacketV1
from .machine.operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
    write_immutable_operational,
)
from .machine.packets import read_work_packet
from .models import (
    Digest,
    EntityVersion,
    EntityVersionRef,
    NonEmptyString,
    StableId,
    StrictModel,
)
from .runtime.layout import StoreLayout, assert_safe_store_path, path_entry_exists
from .runtime.replay import replay
from .theory_validation import validate_theory_entity


TheoremAdvisoryLaneId = Literal[
    "proof_worker",
    "counterexample_economics_challenger",
]
TheoremRoleOverlayVersion = Literal["theorem-team-role-overlay/v1"]

_THEOREM_ROUTE_ID = "verify.claims_proofs_and_interpretation"
_LANE_IDS: tuple[TheoremAdvisoryLaneId, TheoremAdvisoryLaneId] = (
    "proof_worker",
    "counterexample_economics_challenger",
)
_ROLE_OVERLAYS: dict[TheoremAdvisoryLaneId, str] = {
    "proof_worker": (
        "Work independently from the exact WorkPacket. Address every assigned "
        "ProofObligation with an admissible method. Return only the final proof "
        "or counterproof skeleton, the decisive step or precise failed step, "
        "scope, and limitations. Finite computation is not a universal proof. "
        "This is advice only: do not write, complete, see peer output, or delegate."
    ),
    "counterexample_economics_challenger": (
        "Work independently from the exact WorkPacket. Challenge every assigned "
        "ProofObligation with in-domain boundary or counterexample search and "
        "separately test whether the formal statement supports its economic "
        "interpretation. Return final findings and limitations, not private "
        "reasoning. This is advice only: do not write, complete, see peer output, "
        "or delegate."
    ),
}


class _TheoremPacketBoundV1(StrictModel):
    project_id: NonEmptyString
    route_id: Literal["verify.claims_proofs_and_interpretation"] = _THEOREM_ROUTE_ID
    route_run_id: StableId
    base_head: Digest
    work_packet_hash: Digest
    context_manifest_hash: Digest
    compiled_context_hash: Digest
    run_input_brief_hash: Digest | None


class TheoremTeamDeliveryAuthorizationV1(_TheoremPacketBoundV1):
    """Declare exactly two advisory exposures after single-host delivery."""

    authorization_schema: Literal[
        "econ-theorist/theorem-team-delivery-authorization/v1"
    ] = "econ-theorist/theorem-team-delivery-authorization/v1"
    source_delivery_envelope_hash: Digest
    source_capability_receipt_hash: Digest
    source_egress_plan_hash: Digest
    host_product: NonEmptyString
    host_version: NonEmptyString
    adapter_id: NonEmptyString
    adapter_version: NonEmptyString
    host_session_id: NonEmptyString
    source_agent_topology: Literal["single"] = "single"
    authorized_lane_ids: tuple[
        TheoremAdvisoryLaneId, TheoremAdvisoryLaneId
    ] = _LANE_IDS
    delegated_packet_exposure_count: Literal[2] = 2
    lane_separation_claim: Literal["logical", "host_enforced"]
    canonical_write_allowed: Literal[False] = False
    authority_semantics: Literal[
        "phase5b_declared_two_adviser_delegation_after_single_coordinator_delivery"
    ] = "phase5b_declared_two_adviser_delegation_after_single_coordinator_delivery"

    @model_validator(mode="after")
    def _exact_two_lanes(self) -> "TheoremTeamDeliveryAuthorizationV1":
        if self.authorized_lane_ids != _LANE_IDS:
            raise ValueError("theorem team authorization requires the exact two lanes")
        return self


class TheoremTeamPlanV1(_TheoremPacketBoundV1):
    plan_schema: Literal["econ-theorist/theorem-team-plan/v1"] = (
        "econ-theorist/theorem-team-plan/v1"
    )
    delivery_authorization_hash: Digest
    execution_mode: Literal["isolated_multi_agent", "sequential_single_model"]
    isolation_claim: Literal["logical", "host_enforced"]
    role_overlay_version: TheoremRoleOverlayVersion = "theorem-team-role-overlay/v1"
    role_overlays: dict[TheoremAdvisoryLaneId, NonEmptyString]
    proof_obligation_refs: tuple[EntityVersionRef, ...]
    single_canonical_writer: Literal[True] = True
    canonical_writer_role: Literal["coordinator"] = "coordinator"
    coordinator_agent_label: Literal["scientific_agent"] = "scientific_agent"
    canonical_write_allowed: Literal[False] = False
    authority_semantics: Literal["advice_then_coordinator_candidate_authoring"] = (
        "advice_then_coordinator_candidate_authoring"
    )

    @model_validator(mode="after")
    def _exact_plan(self) -> "TheoremTeamPlanV1":
        if self.role_overlays != _ROLE_OVERLAYS:
            raise ValueError("theorem team plan must carry the exact role overlays")
        keys = tuple((item.entity_id, item.version) for item in self.proof_obligation_refs)
        if not keys or len(set(keys)) != len(keys) or keys != tuple(sorted(keys)):
            raise ValueError(
                "theorem team plan requires a nonempty canonical ProofObligation ref set"
            )
        return self


class TheoremLaneOutputV1(_TheoremPacketBoundV1):
    output_schema: Literal["econ-theorist/theorem-lane-output/v1"] = (
        "econ-theorist/theorem-lane-output/v1"
    )
    team_plan_hash: Digest
    lane_id: TheoremAdvisoryLaneId
    lane_input_hash: Digest
    proof_obligation_refs: tuple[EntityVersionRef, ...]
    agent_label: NonEmptyString
    model_observation: NonEmptyString | None = None
    content_markdown: NonEmptyString
    canonical_write_allowed: Literal[False] = False
    authority_semantics: Literal["advice_only"] = "advice_only"


class TheoremTeamReviewV1(_TheoremPacketBoundV1):
    review_schema: Literal["econ-theorist/theorem-team-review/v1"] = (
        "econ-theorist/theorem-team-review/v1"
    )
    team_plan_hash: Digest
    proof_obligation_refs: tuple[EntityVersionRef, ...]
    coordinator_agent_label: Literal["scientific_agent"]
    proof_worker: TheoremLaneOutputV1
    counterexample_economics_challenger: TheoremLaneOutputV1
    coordinator_integration_required: Literal[True] = True
    agreement_semantics: Literal["independent_advice_not_verification_evidence"] = (
        "independent_advice_not_verification_evidence"
    )
    canonical_write_allowed: Literal[False] = False

    @model_validator(mode="after")
    def _complete_bound_review(self) -> "TheoremTeamReviewV1":
        if self.proof_worker.lane_id != "proof_worker":
            raise ValueError("theorem review requires the proof worker lane")
        if (
            self.counterexample_economics_challenger.lane_id
            != "counterexample_economics_challenger"
        ):
            raise ValueError("theorem review requires the challenger lane")
        if (
            self.proof_worker.agent_label
            == self.counterexample_economics_challenger.agent_label
        ):
            raise ValueError("theorem review requires two distinct advisory agents")
        if self.coordinator_agent_label in {
            self.proof_worker.agent_label,
            self.counterexample_economics_challenger.agent_label,
        }:
            raise ValueError("theorem review reserves the coordinator agent identity")
        expected_binding = _binding_tuple(self)
        for output in (
            self.proof_worker,
            self.counterexample_economics_challenger,
        ):
            if _binding_tuple(output) != expected_binding:
                raise ValueError("theorem lane output differs from the review packet")
            if output.team_plan_hash != self.team_plan_hash:
                raise ValueError("theorem lane output differs from the review plan")
            if output.proof_obligation_refs != self.proof_obligation_refs:
                raise ValueError("theorem lane output omits an assigned obligation")
        return self


class TheoremTeamCompletionBindingV1(_TheoremPacketBoundV1):
    """Bind coordinator provenance before the unchanged completion call."""

    binding_schema: Literal[
        "econ-theorist/theorem-team-completion-binding/v1"
    ] = "econ-theorist/theorem-team-completion-binding/v1"
    team_plan_hash: Digest
    review_hash: Digest
    completion_operation_key: OperationKey
    delivery_envelope_hash: Digest
    candidate_digest: Digest
    coordinator_agent_label: NonEmptyString
    coordinator_model_observation: NonEmptyString
    canonical_writer_role: Literal["coordinator"] = "coordinator"
    single_canonical_writer: Literal[True] = True
    binding_status: Literal["declared_before_candidate_completion"] = (
        "declared_before_candidate_completion"
    )
    authority_semantics: Literal["operational_provenance_not_tool_identity"] = (
        "operational_provenance_not_tool_identity"
    )


_RecordT = TypeVar("_RecordT", bound=StrictModel)


def _binding_tuple(value: _TheoremPacketBoundV1) -> tuple[object, ...]:
    return (
        value.project_id,
        value.route_id,
        value.route_run_id,
        value.base_head,
        value.work_packet_hash,
        value.context_manifest_hash,
        value.compiled_context_hash,
        value.run_input_brief_hash,
    )


def _packet_binding(packet: WorkPacketV1, work_packet_hash: str) -> dict[str, object]:
    return {
        "project_id": packet.project_id,
        "route_id": packet.route_id,
        "route_run_id": packet.route_run_id,
        "base_head": packet.base_head,
        "work_packet_hash": work_packet_hash,
        "context_manifest_hash": packet.context_manifest_hash,
        "compiled_context_hash": packet.compiled_context_hash,
        "run_input_brief_hash": packet.run_input_brief_hash,
    }


def _team_store(
    operational: ProjectOperationalLayout, route_run_id: str
) -> ContentAddressedOperationalStore:
    if not route_run_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
        for character in route_run_id
    ):
        raise OperationalError(f"unsafe operational run ID: {route_run_id!r}")
    return ContentAddressedOperationalStore(
        operational.project_root,
        operational.runs / route_run_id,
    )


def _read_record(
    store: ContentAddressedOperationalStore,
    namespace: str,
    digest: str,
    model: type[_RecordT],
) -> _RecordT:
    data = store.read_bytes(namespace, digest)
    try:
        value = model.model_validate_json(data, strict=True)
    except ValueError as exc:
        raise OperationalError(f"stored {namespace} record is invalid") from exc
    if canonical_json_bytes(value) != data:
        raise OperationalError(f"stored {namespace} record is not canonical JSON")
    return value


def _read_fixed_record(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    filename: str,
    model: type[_RecordT],
) -> _RecordT | None:
    store = _team_store(operational, route_run_id)
    path = store.root / filename
    if not path_entry_exists(path):
        return None
    try:
        assert_safe_store_path(store.anchor, path, expected="file", allow_missing=False)
        data = path.read_bytes()
        value = model.model_validate_json(data, strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise OperationalError(f"invalid fixed theorem-team record: {filename}") from exc
    if canonical_json_bytes(value) != data:
        raise OperationalError(f"noncanonical fixed theorem-team record: {filename}")
    return value


def _publish_fixed_content_record(
    store: ContentAddressedOperationalStore,
    filename: str,
    namespace: str,
    value: _RecordT,
    *,
    label: str,
) -> tuple[str, _RecordT, bool]:
    expected_hash = sha256_digest(canonical_json_bytes(value))
    content_was_present = path_entry_exists(store.path_for(namespace, expected_hash))
    digest, _ = store.install(namespace, value)
    if digest != expected_hash:  # pragma: no cover - digest invariant
        raise OperationalError(f"{label} digest changed during publish")
    fixed_written = write_immutable_operational(
        store.anchor, store.root / filename, canonical_json_bytes(value)
    )
    return digest, value, (not content_was_present or fixed_written)


def _compiled_entities(packet: WorkPacketV1) -> dict[tuple[str, int], EntityVersion]:
    raw_entities = packet.compiled_context.get("entities")
    if not isinstance(raw_entities, (tuple, list)):
        raise OperationalError("theorem team WorkPacket lacks compiled entities")
    parsed: dict[tuple[str, int], EntityVersion] = {}
    for raw in raw_entities:
        try:
            entity = EntityVersion.model_validate_json(
                canonical_json_bytes(raw), strict=True
            )
        except (TypeError, ValueError) as exc:
            raise OperationalError(
                "theorem team WorkPacket contains an invalid compiled entity"
            ) from exc
        key = (entity.entity_id, entity.version)
        if key in parsed:
            raise OperationalError("theorem team WorkPacket repeats a compiled entity")
        parsed[key] = entity
    return parsed


def _exact_proof_obligation_refs(
    packet: WorkPacketV1,
) -> tuple[EntityVersionRef, ...]:
    """Recover the every-and-only retained obligation closure from the packet."""

    if packet.route_id != _THEOREM_ROUTE_ID or packet.route_version != 2:
        raise OperationalError("theorem team accepts only claim verification v2")
    entities = _compiled_entities(packet)
    focus_entities: list[EntityVersion] = []
    for reference in packet.focus_refs:
        entity = entities.get((reference.entity_id, reference.version))
        if entity is None:
            raise OperationalError("theorem team WorkPacket focus is absent from context")
        focus_entities.append(entity)
    graph_entities = tuple(
        item for item in focus_entities if item.entity_type == "ClaimGraph"
    )
    obligation_entities = tuple(
        item for item in focus_entities if item.entity_type == "ProofObligation"
    )
    if len(graph_entities) != 1 or not obligation_entities:
        raise OperationalError(
            "theorem team requires one ClaimGraph and at least one ProofObligation"
        )
    graph_ref = EntityVersionRef(
        entity_id=graph_entities[0].entity_id, version=graph_entities[0].version
    )
    graph = validate_theory_entity(graph_entities[0])
    if not isinstance(graph, t.ClaimGraph):  # pragma: no cover - entity type guard
        raise OperationalError("theorem team ClaimGraph payload is invalid")
    expected_refs = {
        reference
        for claim in graph.claims
        for reference in claim.proof_obligation_refs
    }
    input_refs = {
        EntityVersionRef(entity_id=item.entity_id, version=item.version)
        for item in obligation_entities
    }
    if input_refs != expected_refs:
        raise OperationalError(
            "theorem team WorkPacket must contain every and only retained obligations"
        )
    claims_by_id = {claim.claim_id: claim for claim in graph.claims}
    for entity in obligation_entities:
        obligation = validate_theory_entity(entity)
        if not isinstance(obligation, t.ProofObligation):  # pragma: no cover
            raise OperationalError("theorem team obligation payload is invalid")
        reference = EntityVersionRef(entity_id=entity.entity_id, version=entity.version)
        claim = claims_by_id.get(obligation.claim_id)
        if (
            obligation.claim_graph_ref != graph_ref
            or claim is None
            or reference not in claim.proof_obligation_refs
            or not set(obligation.assumption_ids).issubset(set(claim.assumption_ids))
        ):
            raise OperationalError(
                "theorem team obligation does not bind its exact graph and claim"
            )
    return tuple(sorted(input_refs, key=lambda item: (item.entity_id, item.version)))


def _load_current_theorem_packet(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    require_current_head: bool = True,
) -> WorkPacketV1:
    packet = read_work_packet(operational, route_run_id, work_packet_hash)
    if sha256_digest(canonical_json_bytes(packet)) != work_packet_hash:
        raise OperationalError("theorem team WorkPacket hash is invalid")
    _exact_proof_obligation_refs(packet)
    snapshot = replay(StoreLayout.from_store_root(operational.store_root))
    if snapshot.project_id != packet.project_id:
        raise OperationalError("theorem team project binding is stale")
    if require_current_head and snapshot.head != packet.base_head:
        raise OperationalError("theorem team base head is stale")
    return packet


def _require_binding(
    value: _TheoremPacketBoundV1,
    packet: WorkPacketV1,
    work_packet_hash: str,
    *,
    label: str,
) -> None:
    expected = _TheoremPacketBoundV1(**_packet_binding(packet, work_packet_hash))
    if _binding_tuple(value) != _binding_tuple(expected):
        raise OperationalError(f"{label} does not match the WorkPacket binding")


def build_theorem_team_delivery_authorization(
    packet: WorkPacketV1,
    work_packet_hash: str,
    *,
    source_delivery_envelope_hash: str,
    source_capability_receipt_hash: str,
    source_egress_plan_hash: str,
    host_product: str,
    host_version: str,
    adapter_id: str,
    adapter_version: str,
    host_session_id: str,
    lane_separation_claim: Literal["logical", "host_enforced"],
) -> TheoremTeamDeliveryAuthorizationV1:
    """Build the exact declaration for two non-writing advisory lanes."""

    obligation_refs = _exact_proof_obligation_refs(packet)
    if not obligation_refs:  # pragma: no cover - extraction invariant
        raise OperationalError("theorem team has no exact proof obligations")
    return TheoremTeamDeliveryAuthorizationV1(
        **_packet_binding(packet, work_packet_hash),
        source_delivery_envelope_hash=source_delivery_envelope_hash,
        source_capability_receipt_hash=source_capability_receipt_hash,
        source_egress_plan_hash=source_egress_plan_hash,
        host_product=host_product,
        host_version=host_version,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        host_session_id=host_session_id,
        lane_separation_claim=lane_separation_claim,
    )


def _read_activation(
    operational: ProjectOperationalLayout,
    packet: WorkPacketV1,
    work_packet_hash: str,
) -> tuple[
    str, TheoremTeamPlanV1, TheoremTeamDeliveryAuthorizationV1
] | None:
    plan = _read_fixed_record(
        operational, packet.route_run_id, "theorem-team-plan.json", TheoremTeamPlanV1
    )
    if plan is None:
        return None
    plan_hash = sha256_digest(canonical_json_bytes(plan))
    stored = _read_record(
        _team_store(operational, packet.route_run_id),
        "theorem-team-plans",
        plan_hash,
        TheoremTeamPlanV1,
    )
    if stored != plan:
        raise OperationalError("fixed theorem team plan differs from content store")
    _require_binding(plan, packet, work_packet_hash, label="theorem team plan")
    expected_refs = _exact_proof_obligation_refs(packet)
    if plan.proof_obligation_refs != expected_refs:
        raise OperationalError("theorem team plan differs from exact obligations")
    authorization = _read_record(
        _team_store(operational, packet.route_run_id),
        "theorem-team-delivery-authorizations",
        plan.delivery_authorization_hash,
        TheoremTeamDeliveryAuthorizationV1,
    )
    _require_binding(
        authorization,
        packet,
        work_packet_hash,
        label="theorem team delivery authorization",
    )
    if authorization.lane_separation_claim != plan.isolation_claim:
        raise OperationalError("theorem team isolation differs from its authorization")
    return plan_hash, plan, authorization


def open_theorem_team_plan(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    delivery_authorization: TheoremTeamDeliveryAuthorizationV1,
    execution_mode: Literal[
        "isolated_multi_agent", "sequential_single_model"
    ] = "isolated_multi_agent",
    isolation_claim: Literal["logical", "host_enforced"] = "logical",
) -> tuple[str, TheoremTeamPlanV1]:
    """Declare the bounded two-adviser team before either lane invocation."""

    packet = _load_current_theorem_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    _require_binding(
        delivery_authorization,
        packet,
        work_packet_hash,
        label="theorem team delivery authorization",
    )
    if delivery_authorization.lane_separation_claim != isolation_claim:
        raise OperationalError(
            "requested theorem team isolation differs from delivery authorization"
        )
    existing = _read_activation(operational, packet, work_packet_hash)
    if existing is not None:
        if (
            existing[2] != delivery_authorization
            or existing[1].execution_mode != execution_mode
            or existing[1].isolation_claim != isolation_claim
        ):
            raise OperationalError(
                "theorem team is already active under a different authorization"
            )
        return existing[0], existing[1]
    authorization_hash = sha256_digest(canonical_json_bytes(delivery_authorization))
    plan = TheoremTeamPlanV1(
        **_packet_binding(packet, work_packet_hash),
        delivery_authorization_hash=authorization_hash,
        execution_mode=execution_mode,
        isolation_claim=isolation_claim,
        role_overlays=dict(_ROLE_OVERLAYS),
        proof_obligation_refs=_exact_proof_obligation_refs(packet),
    )
    store = _team_store(operational, route_run_id)
    installed_authorization_hash, _ = store.install(
        "theorem-team-delivery-authorizations", delivery_authorization
    )
    if installed_authorization_hash != authorization_hash:  # pragma: no cover
        raise OperationalError("theorem team authorization digest changed")
    plan_hash, _, _ = _publish_fixed_content_record(
        store,
        "theorem-team-plan.json",
        "theorem-team-plans",
        plan,
        label="theorem team plan",
    )
    return plan_hash, plan


def theorem_team_is_active(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    require_current_head: bool = True,
) -> bool:
    packet = _load_current_theorem_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    return _read_activation(operational, packet, work_packet_hash) is not None


def read_theorem_team_plan(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    team_plan_hash: str | None = None,
    require_current_head: bool = True,
) -> TheoremTeamPlanV1:
    packet = _load_current_theorem_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None:
        raise OperationalError("theorem team plan is unavailable")
    if team_plan_hash is not None and activation[0] != team_plan_hash:
        raise OperationalError("theorem team plan hash differs from expected binding")
    return activation[1]


def read_theorem_team_delivery_authorization(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    team_plan_hash: str,
    require_current_head: bool = True,
) -> TheoremTeamDeliveryAuthorizationV1:
    packet = _load_current_theorem_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != team_plan_hash:
        raise OperationalError("theorem team plan binding is unavailable")
    return activation[2]


def theorem_lane_input_hash(
    plan: TheoremTeamPlanV1,
    plan_hash: str,
    lane_id: TheoremAdvisoryLaneId,
) -> str:
    """Bind the exact packet, role overlay, and full obligation assignment."""

    if lane_id not in _LANE_IDS:
        raise ValueError(f"unknown theorem advisory lane: {lane_id}")
    return sha256_digest(
        canonical_json_bytes(
            {
                "team_plan_hash": plan_hash,
                "work_packet_hash": plan.work_packet_hash,
                "lane_id": lane_id,
                "role_overlay": plan.role_overlays[lane_id],
                "proof_obligation_refs": plan.proof_obligation_refs,
            }
        )
    )


def build_theorem_lane_output(
    plan: TheoremTeamPlanV1,
    plan_hash: str,
    *,
    lane_id: TheoremAdvisoryLaneId,
    agent_label: str,
    content_markdown: str,
    model_observation: str | None = None,
) -> TheoremLaneOutputV1:
    if sha256_digest(canonical_json_bytes(plan)) != plan_hash:
        raise ValueError("theorem lane received an invalid team plan hash")
    return TheoremLaneOutputV1(
        **{
            "project_id": plan.project_id,
            "route_id": plan.route_id,
            "route_run_id": plan.route_run_id,
            "base_head": plan.base_head,
            "work_packet_hash": plan.work_packet_hash,
            "context_manifest_hash": plan.context_manifest_hash,
            "compiled_context_hash": plan.compiled_context_hash,
            "run_input_brief_hash": plan.run_input_brief_hash,
        },
        team_plan_hash=plan_hash,
        lane_id=lane_id,
        lane_input_hash=theorem_lane_input_hash(plan, plan_hash, lane_id),
        proof_obligation_refs=plan.proof_obligation_refs,
        agent_label=agent_label,
        model_observation=model_observation,
        content_markdown=content_markdown,
    )


def publish_theorem_team_review(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    proof_worker: TheoremLaneOutputV1,
    counterexample_economics_challenger: TheoremLaneOutputV1,
) -> tuple[str, TheoremTeamReviewV1]:
    packet = _load_current_theorem_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None:
        raise OperationalError("theorem team is not active")
    plan_hash, plan, _ = activation
    for output, lane_id in (
        (proof_worker, "proof_worker"),
        (
            counterexample_economics_challenger,
            "counterexample_economics_challenger",
        ),
    ):
        _require_binding(output, packet, work_packet_hash, label="theorem lane output")
        if (
            output.team_plan_hash != plan_hash
            or output.lane_id != lane_id
            or output.lane_input_hash
            != theorem_lane_input_hash(plan, plan_hash, lane_id)
            or output.proof_obligation_refs != plan.proof_obligation_refs
        ):
            raise OperationalError("theorem lane output has an invalid assignment")
    review = TheoremTeamReviewV1(
        **_packet_binding(packet, work_packet_hash),
        team_plan_hash=plan_hash,
        proof_obligation_refs=plan.proof_obligation_refs,
        coordinator_agent_label=plan.coordinator_agent_label,
        proof_worker=proof_worker,
        counterexample_economics_challenger=counterexample_economics_challenger,
    )
    existing = _read_fixed_record(
        operational,
        route_run_id,
        "theorem-team-review.json",
        TheoremTeamReviewV1,
    )
    if existing is not None and existing != review:
        raise OperationalError("theorem team review is already published")
    if existing is not None:
        review_hash = sha256_digest(canonical_json_bytes(existing))
        stored = _read_record(
            _team_store(operational, route_run_id),
            "theorem-team-reviews",
            review_hash,
            TheoremTeamReviewV1,
        )
        if stored != existing:
            raise OperationalError("fixed theorem team review differs from content store")
        return review_hash, existing
    review_hash, _, _ = _publish_fixed_content_record(
        _team_store(operational, route_run_id),
        "theorem-team-review.json",
        "theorem-team-reviews",
        review,
        label="theorem team review",
    )
    return review_hash, review


def read_theorem_team_review(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    review_hash: str | None = None,
    require_current_head: bool = True,
) -> TheoremTeamReviewV1:
    packet = _load_current_theorem_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None:
        raise OperationalError("theorem team is not active")
    review = _read_fixed_record(
        operational,
        route_run_id,
        "theorem-team-review.json",
        TheoremTeamReviewV1,
    )
    if review is None:
        raise OperationalError("theorem team review is unavailable")
    actual_hash = sha256_digest(canonical_json_bytes(review))
    if review_hash is not None and actual_hash != review_hash:
        raise OperationalError("theorem team review hash differs from expected binding")
    stored = _read_record(
        _team_store(operational, route_run_id),
        "theorem-team-reviews",
        actual_hash,
        TheoremTeamReviewV1,
    )
    if stored != review:
        raise OperationalError("fixed theorem team review differs from content store")
    _require_binding(review, packet, work_packet_hash, label="theorem team review")
    if (
        review.team_plan_hash != activation[0]
        or review.proof_obligation_refs != activation[1].proof_obligation_refs
    ):
        raise OperationalError("theorem team review differs from its exact plan")
    return review


def theorem_team_review_exists(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    require_current_head: bool = True,
) -> bool:
    """Probe the immutable review while validating any record that is present."""

    review = _read_fixed_record(
        operational,
        route_run_id,
        "theorem-team-review.json",
        TheoremTeamReviewV1,
    )
    if review is None:
        return False
    read_theorem_team_review(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        review_hash=sha256_digest(canonical_json_bytes(review)),
        require_current_head=require_current_head,
    )
    return True


def _completion_binding_filename(completion_operation_key: str) -> str:
    key_digest = sha256_digest(completion_operation_key.encode("utf-8"))
    return f"theorem-team-completions/by-key/{key_digest}.json"


def publish_theorem_team_completion_binding(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    review_hash: str,
    completion_operation_key: str,
    delivery_envelope_hash: str,
    candidate_digest: str,
    coordinator_agent_label: str,
    coordinator_model_observation: str,
    require_current_head: bool = True,
) -> tuple[str, TheoremTeamCompletionBindingV1, bool]:
    """Bind one coordinator-owned completion request without changing its receipt."""

    packet = _load_current_theorem_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None:
        raise OperationalError("theorem team is not active")
    review = read_theorem_team_review(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        review_hash=review_hash,
        require_current_head=require_current_head,
    )
    authorization = activation[2]
    if authorization.source_delivery_envelope_hash != delivery_envelope_hash:
        raise OperationalError(
            "theorem completion delivery differs from team authorization"
        )
    if coordinator_agent_label != review.coordinator_agent_label:
        raise OperationalError("theorem completion uses a different coordinator")
    binding = TheoremTeamCompletionBindingV1(
        **_packet_binding(packet, work_packet_hash),
        team_plan_hash=activation[0],
        review_hash=review_hash,
        completion_operation_key=completion_operation_key,
        delivery_envelope_hash=delivery_envelope_hash,
        candidate_digest=candidate_digest,
        coordinator_agent_label=coordinator_agent_label,
        coordinator_model_observation=coordinator_model_observation,
    )
    store = _team_store(operational, route_run_id)
    fixed_name = _completion_binding_filename(binding.completion_operation_key)
    existing = _read_fixed_record(
        operational,
        route_run_id,
        fixed_name,
        TheoremTeamCompletionBindingV1,
    )
    if existing is not None and existing != binding:
        raise OperationalError(
            "completion operation key is already bound to different theorem provenance"
        )
    if existing is not None:
        binding_hash = sha256_digest(canonical_json_bytes(existing))
        stored = _read_record(
            store,
            "theorem-team-completions",
            binding_hash,
            TheoremTeamCompletionBindingV1,
        )
        if stored != existing:
            raise OperationalError(
                "fixed theorem completion binding differs from content store"
            )
        return binding_hash, existing, False
    return _publish_fixed_content_record(
        store,
        fixed_name,
        "theorem-team-completions",
        binding,
        label="theorem team completion binding",
    )


def theorem_team_completion_binding_exists(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    completion_operation_key: str,
    require_current_head: bool = True,
) -> bool:
    store = _team_store(operational, route_run_id)
    fixed_name = _completion_binding_filename(completion_operation_key)
    binding = _read_fixed_record(
        operational,
        route_run_id,
        fixed_name,
        TheoremTeamCompletionBindingV1,
    )
    if binding is None:
        return False
    packet = _load_current_theorem_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    _require_binding(
        binding, packet, work_packet_hash, label="theorem completion binding"
    )
    binding_hash = sha256_digest(canonical_json_bytes(binding))
    stored = _read_record(
        store,
        "theorem-team-completions",
        binding_hash,
        TheoremTeamCompletionBindingV1,
    )
    if stored != binding:
        raise OperationalError(
            "fixed theorem completion binding differs from content store"
        )
    read_theorem_team_review(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        review_hash=binding.review_hash,
        require_current_head=require_current_head,
    )
    return True


__all__ = [
    "TheoremAdvisoryLaneId",
    "TheoremLaneOutputV1",
    "TheoremTeamCompletionBindingV1",
    "TheoremTeamDeliveryAuthorizationV1",
    "TheoremTeamPlanV1",
    "TheoremTeamReviewV1",
    "build_theorem_lane_output",
    "build_theorem_team_delivery_authorization",
    "open_theorem_team_plan",
    "publish_theorem_team_completion_binding",
    "publish_theorem_team_review",
    "read_theorem_team_delivery_authorization",
    "read_theorem_team_plan",
    "read_theorem_team_review",
    "theorem_lane_input_hash",
    "theorem_team_completion_binding_exists",
    "theorem_team_is_active",
    "theorem_team_review_exists",
]
