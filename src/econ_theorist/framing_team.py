"""Noncanonical Phase 5B.0 research-team sidecars for framing.

The module declares and records advisory lanes around one immutable
``frame.question_and_benchmarks`` WorkPacket.  It does not call a model,
construct a scientific candidate, confirm a human Decision, or write canonical
state.  The existing single worker and ``candidate.complete`` path remain the
only route to a canonical commit.
"""

from __future__ import annotations

from typing import Any, Literal, TypeVar

from pydantic import model_serializer, model_validator

from .codec import canonical_json_bytes, sha256_digest
from .machine.models import OperationKey, WorkPacketV1
from .machine.operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
    write_immutable_operational,
)
from .machine.packets import read_work_packet
from .models import Digest, NonEmptyString, StableId, StrictModel
from .runtime.layout import StoreLayout, assert_safe_store_path, path_entry_exists
from .runtime.replay import replay


FramingAdvisoryLaneId = Literal[
    "mentor",
    "collaborator_a",
    "collaborator_b",
]
FramingTeamLaneId = Literal[
    "mentor",
    "collaborator_a",
    "collaborator_b",
    "research_worker",
]
FramingDisposition = Literal["continue", "simplify", "pivot", "park", "kill"]
FramingTeamStopStatus = Literal[
    "awaiting_clarification",
    "new_brief_required",
]
FramingTeamTerminalStatus = Literal[
    "handoff_ready",
    "new_brief_required",
    "parked",
    "killed",
]

_FRAMING_ROUTE_ID = "frame.question_and_benchmarks"
_LANE_ROLES: dict[str, Literal["mentor", "collaborator"]] = {
    "mentor": "mentor",
    "collaborator_a": "collaborator",
    "collaborator_b": "collaborator",
}
_ROLE_OVERLAYS: dict[str, str] = {
    "mentor": (
        "Act as the research mentor. Challenge the question, exact benchmarks, "
        "importance, contribution radius, hidden assumptions, and the conditions "
        "for continuing, simplifying, pivoting, parking, or killing. Return "
        "free-form Markdown advice. Do not author the candidate or decide G1."
    ),
    "collaborator_a": (
        "Act as an independent research collaborator. Develop one defensible "
        "question-and-benchmark framing, explain its economic promise and main "
        "risk, and return free-form Markdown advice. Do not author the candidate "
        "or decide G1."
    ),
    "collaborator_b": (
        "Act as an independent research collaborator. Develop a materially "
        "different defensible question-and-benchmark framing, explain its "
        "economic promise and main risk, and return free-form Markdown advice. "
        "Do not author the candidate or decide G1."
    ),
}


class _FramingPacketBoundV1(StrictModel):
    project_id: NonEmptyString
    route_id: Literal["frame.question_and_benchmarks"] = _FRAMING_ROUTE_ID
    route_run_id: StableId
    base_head: Digest
    work_packet_hash: Digest
    context_manifest_hash: Digest
    compiled_context_hash: Digest
    run_input_brief_hash: Digest | None


class FramingTeamDeliveryAuthorizationV1(_FramingPacketBoundV1):
    """Declare the bounded Phase 5B team after single-host delivery."""

    authorization_schema: Literal[
        "econ-theorist/framing-team-delivery-authorization/v1"
    ] = "econ-theorist/framing-team-delivery-authorization/v1"
    source_delivery_envelope_hash: Digest
    source_capability_receipt_hash: Digest
    source_egress_plan_hash: Digest
    host_product: NonEmptyString
    host_version: NonEmptyString
    adapter_id: NonEmptyString
    adapter_version: NonEmptyString
    host_session_id: NonEmptyString
    source_agent_topology: Literal["single"] = "single"
    authorized_lane_ids: tuple[FramingTeamLaneId, ...] = (
        "mentor",
        "collaborator_a",
        "collaborator_b",
        "research_worker",
    )
    delegated_packet_exposure_count: Literal[4] = 4
    worker_exposure_condition: Literal["after_exact_terminal_handoff"] = (
        "after_exact_terminal_handoff"
    )
    lane_separation_claim: Literal["logical", "host_enforced"]
    direct_user_capture_claim: Literal["current_user_turn"] = "current_user_turn"
    source_aware_choice: Literal["available"] | None = None
    canonical_write_allowed: Literal[False] = False
    authority_semantics: Literal[
        "phase5b_declared_bounded_team_delegation_after_single_coordinator_delivery"
    ] = "phase5b_declared_bounded_team_delegation_after_single_coordinator_delivery"

    @model_validator(mode="after")
    def _exact_advisory_exposures(self) -> "FramingTeamDeliveryAuthorizationV1":
        if self.authorized_lane_ids != (
            "mentor",
            "collaborator_a",
            "collaborator_b",
            "research_worker",
        ):
            raise ValueError("framing team authorization requires the exact four lanes")
        return self

    @model_serializer(mode="wrap")
    def _preserve_legacy_authorization_bytes(self, handler: Any) -> Any:
        data = handler(self)
        if self.source_aware_choice is None:
            data.pop("source_aware_choice", None)
        return data


class FramingTeamPlanV1(_FramingPacketBoundV1):
    plan_schema: Literal["econ-theorist/framing-team-plan/v1"] = (
        "econ-theorist/framing-team-plan/v1"
    )
    execution_mode: Literal["isolated_multi_agent", "sequential_single_model"]
    isolation_claim: Literal["logical", "host_enforced"]
    delivery_authorization_hash: Digest
    role_overlay_version: Literal["framing-team-role-overlay/v1"] = (
        "framing-team-role-overlay/v1"
    )
    role_overlays: dict[FramingAdvisoryLaneId, NonEmptyString]
    worker_lane_id: Literal["research_worker"] = "research_worker"
    single_canonical_writer: Literal[True] = True
    authority_semantics: Literal["advice_then_candidate_authoring"] = (
        "advice_then_candidate_authoring"
    )

    @model_validator(mode="after")
    def _exact_role_overlays(self) -> "FramingTeamPlanV1":
        if self.role_overlays != _ROLE_OVERLAYS:
            raise ValueError("framing team plan must carry the exact v1 role overlays")
        return self


class FramingLaneOutputV1(_FramingPacketBoundV1):
    output_schema: Literal["econ-theorist/framing-lane-output/v1"] = (
        "econ-theorist/framing-lane-output/v1"
    )
    team_plan_hash: Digest
    lane_id: FramingAdvisoryLaneId
    role: Literal["mentor", "collaborator"]
    lane_input_hash: Digest
    agent_label: NonEmptyString
    model_observation: NonEmptyString | None = None
    content_markdown: NonEmptyString
    canonical_write_allowed: Literal[False] = False
    authority_semantics: Literal["advice_only"] = "advice_only"

    @model_validator(mode="after")
    def _lane_role_matches_id(self) -> "FramingLaneOutputV1":
        if self.role != _LANE_ROLES[self.lane_id]:
            raise ValueError("framing lane role does not match its lane id")
        return self


class FramingTeamPanelV1(_FramingPacketBoundV1):
    panel_schema: Literal["econ-theorist/framing-team-panel/v1"] = (
        "econ-theorist/framing-team-panel/v1"
    )
    team_plan_hash: Digest
    mentor: FramingLaneOutputV1
    collaborators: tuple[FramingLaneOutputV1, FramingLaneOutputV1]
    agreement_semantics: Literal["correlated_advice_not_evidence"] = (
        "correlated_advice_not_evidence"
    )

    @model_validator(mode="after")
    def _panel_is_complete_and_bound(self) -> "FramingTeamPanelV1":
        if self.mentor.lane_id != "mentor":
            raise ValueError("framing team panel requires the mentor lane")
        collaborator_ids = tuple(item.lane_id for item in self.collaborators)
        if set(collaborator_ids) != {"collaborator_a", "collaborator_b"}:
            raise ValueError("framing team panel requires two distinct collaborators")
        expected = _binding_tuple(self)
        for output in (self.mentor, *self.collaborators):
            if _binding_tuple(output) != expected:
                raise ValueError("framing team output binding differs from the panel")
            if output.team_plan_hash != self.team_plan_hash:
                raise ValueError("framing team output references a different plan")
        return self


class FramingChoiceSourceV1(StrictModel):
    """One bounded source used only to orient a framing choice."""

    source_schema: Literal["econ-theorist/framing-choice-source/v1"] = (
        "econ-theorist/framing-choice-source/v1"
    )
    source_id: StableId
    citation: NonEmptyString
    locator: NonEmptyString
    source_kind: NonEmptyString
    access_level: Literal["metadata", "abstract", "full_text"]
    retrieved_at: NonEmptyString
    supported_claim_markdown: NonEmptyString
    limitations_markdown: NonEmptyString


class FramingDirectionCardV1(StrictModel):
    """Source-oriented comparison card for one unchanged blind-panel lane."""

    card_schema: Literal["econ-theorist/framing-direction-card/v1"] = (
        "econ-theorist/framing-direction-card/v1"
    )
    lane_id: Literal["collaborator_a", "collaborator_b"]
    research_question: NonEmptyString
    exact_benchmark: NonEmptyString
    economic_significance: NonEmptyString
    ordinary_agent_baseline: NonEmptyString
    ai_specific_primitive: NonEmptyString
    why_ai_primitive_is_distinct: NonEmptyString
    mechanism_design_delta: NonEmptyString
    classic_source_ids: tuple[StableId, ...]
    recent_source_ids: tuple[StableId, ...]
    overlap_risk: Literal["high", "medium", "unresolved"]
    closest_literature_overlap: NonEmptyString
    remaining_theory_delta: NonEmptyString
    falsifiable_theory_increment: NonEmptyString
    kill_condition: NonEmptyString
    decision_summary_markdown: NonEmptyString

    @model_validator(mode="after")
    def _source_groups_are_nonempty_and_unique(self) -> "FramingDirectionCardV1":
        if not self.classic_source_ids:
            raise ValueError("direction card requires at least one classic source")
        if not self.recent_source_ids:
            raise ValueError("direction card requires at least one recent source")
        if len(set(self.classic_source_ids)) != len(self.classic_source_ids):
            raise ValueError("direction card classic source ids must be unique")
        if len(set(self.recent_source_ids)) != len(self.recent_source_ids):
            raise ValueError("direction card recent source ids must be unique")
        if set(self.classic_source_ids) & set(self.recent_source_ids):
            raise ValueError(
                "direction card classic and recent source ids must be distinct"
            )
        return self


class FramingChoiceReviewV1(_FramingPacketBoundV1):
    """The one source-aware coordinator review of an immutable raw panel."""

    review_schema: Literal["econ-theorist/framing-choice-review/v1"] = (
        "econ-theorist/framing-choice-review/v1"
    )
    team_plan_hash: Digest
    panel_hash: Digest
    coordinator_agent_label: StableId
    coordinator_model_observation: NonEmptyString
    coordinator_review_count: Literal[1] = 1
    advisory_lanes_reinvoked: Literal[False] = False
    acquisition_mode: Literal["online_host_search", "offline_user_bundle"]
    search_scope: NonEmptyString
    coverage_limits: NonEmptyString
    mentor_screen_markdown: NonEmptyString
    sources: tuple[FramingChoiceSourceV1, ...]
    direction_cards: tuple[
        FramingDirectionCardV1,
        FramingDirectionCardV1,
    ]
    canonical_write_allowed: Literal[False] = False
    authority_semantics: Literal[
        "orientation_only_not_literature_novelty_evidence"
    ] = "orientation_only_not_literature_novelty_evidence"

    @model_validator(mode="after")
    def _complete_source_aware_comparison(self) -> "FramingChoiceReviewV1":
        if len(self.sources) < 2:
            raise ValueError("framing choice review requires at least two sources")
        source_ids = tuple(source.source_id for source in self.sources)
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("framing choice review source ids must be unique")
        lane_ids = tuple(card.lane_id for card in self.direction_cards)
        if set(lane_ids) != {"collaborator_a", "collaborator_b"}:
            raise ValueError(
                "framing choice review requires exactly the two collaborator lanes"
            )
        known_sources = {source.source_id: source for source in self.sources}
        for card in self.direction_cards:
            referenced = set(card.classic_source_ids) | set(card.recent_source_ids)
            unknown = referenced - set(known_sources)
            if unknown:
                raise ValueError(
                    "framing direction card references an unknown source id"
                )
            for label, ids in (
                ("classic", card.classic_source_ids),
                ("recent", card.recent_source_ids),
            ):
                if all(
                    known_sources[source_id].access_level == "metadata"
                    for source_id in ids
                ):
                    raise ValueError(
                        f"direction card requires an inspected {label} source"
                    )
        return self


class FramingResearcherSynthesisV1(_FramingPacketBoundV1):
    synthesis_schema: Literal["econ-theorist/framing-researcher-synthesis/v1"] = (
        "econ-theorist/framing-researcher-synthesis/v1"
    )
    team_plan_hash: Digest
    panel_hash: Digest
    researcher_id: StableId
    capture_channel: Literal["trusted_local_direct_user"] = (
        "trusted_local_direct_user"
    )
    interpretation_status: Literal["clear_within_packet"] = "clear_within_packet"
    researcher_text: NonEmptyString
    disposition: FramingDisposition
    selected_lane_ids: tuple[FramingAdvisoryLaneId, ...] = ()
    synthesis_markdown: NonEmptyString
    worker_brief: NonEmptyString | None = None
    authority_semantics: Literal["noncanonical_direction_not_human_gate"] = (
        "noncanonical_direction_not_human_gate"
    )

    @model_validator(mode="after")
    def _disposition_controls_worker_brief(self) -> "FramingResearcherSynthesisV1":
        if len(set(self.selected_lane_ids)) != len(self.selected_lane_ids):
            raise ValueError("selected framing lane ids must be unique")
        if self.disposition in {"continue", "simplify", "pivot"}:
            if self.worker_brief is None:
                raise ValueError("active framing disposition requires a worker brief")
        elif self.worker_brief is not None:
            raise ValueError("park or kill cannot carry a worker brief")
        return self


class FramingWorkerHandoffV1(_FramingPacketBoundV1):
    handoff_schema: Literal["econ-theorist/framing-worker-handoff/v1"] = (
        "econ-theorist/framing-worker-handoff/v1"
    )
    team_plan_hash: Digest
    panel_hash: Digest
    synthesis_hash: Digest
    preserved_lane_output_hashes: tuple[Digest, Digest, Digest]
    selected_lane_ids: tuple[FramingAdvisoryLaneId, ...]
    worker_lane_id: Literal["research_worker"] = "research_worker"
    candidate_logical_path: NonEmptyString
    validation_operation: Literal["candidate.complete"] = "candidate.complete"
    worker_brief: NonEmptyString
    single_canonical_writer: Literal[True] = True
    authority_semantics: Literal["candidate_authoring_only"] = (
        "candidate_authoring_only"
    )


class FramingWorkerActivationV1(_FramingPacketBoundV1):
    """Fix the one observable worker allowed to use a terminal handoff."""

    activation_schema: Literal[
        "econ-theorist/framing-worker-activation/v1"
    ] = "econ-theorist/framing-worker-activation/v1"
    team_plan_hash: Digest
    panel_hash: Digest
    synthesis_hash: Digest
    worker_handoff_hash: Digest
    delivery_envelope_hash: Digest
    worker_lane_id: Literal["research_worker"] = "research_worker"
    worker_agent_label: StableId
    worker_model_observation: NonEmptyString
    exposure_condition: Literal["exact_terminal_handoff_satisfied"] = (
        "exact_terminal_handoff_satisfied"
    )
    authority_semantics: Literal["one_worker_per_terminal_handoff"] = (
        "one_worker_per_terminal_handoff"
    )


class FramingWorkerCompletionBindingV1(_FramingPacketBoundV1):
    """Operational provenance for one declared team completion request.

    This sidecar deliberately does not change the frozen Phase 5A host receipt.
    A matching host receipt proves the operation completed; this record only
    binds that operation key to the exact worker observation and handoff that
    the Phase 5B host declared before invoking ``candidate.complete``.
    """

    binding_schema: Literal[
        "econ-theorist/framing-worker-completion-binding/v1"
    ] = "econ-theorist/framing-worker-completion-binding/v1"
    team_plan_hash: Digest
    panel_hash: Digest
    synthesis_hash: Digest
    worker_handoff_hash: Digest
    worker_activation_hash: Digest
    completion_operation_key: OperationKey
    delivery_envelope_hash: Digest
    candidate_digest: Digest
    worker_lane_id: Literal["research_worker"] = "research_worker"
    worker_agent_label: StableId
    worker_model_observation: NonEmptyString
    binding_status: Literal["declared_before_candidate_completion"] = (
        "declared_before_candidate_completion"
    )
    authority_semantics: Literal["operational_provenance_not_tool_identity"] = (
        "operational_provenance_not_tool_identity"
    )


class FramingTeamStopV1(_FramingPacketBoundV1):
    stop_schema: Literal["econ-theorist/framing-team-stop/v1"] = (
        "econ-theorist/framing-team-stop/v1"
    )
    team_plan_hash: Digest
    panel_hash: Digest
    researcher_id: StableId
    capture_channel: Literal["trusted_local_direct_user"] = (
        "trusted_local_direct_user"
    )
    researcher_text: NonEmptyString
    status: FramingTeamStopStatus
    reason: NonEmptyString
    authority_semantics: Literal["noncanonical_stop_no_handoff"] = (
        "noncanonical_stop_no_handoff"
    )


class FramingSourceAwareSelectionBindingV1(_FramingPacketBoundV1):
    """Bind one user synthesis or stop to the exact source-aware review."""

    binding_schema: Literal[
        "econ-theorist/framing-source-aware-selection-binding/v1"
    ] = "econ-theorist/framing-source-aware-selection-binding/v1"
    team_plan_hash: Digest
    panel_hash: Digest
    review_hash: Digest
    selection_record_kind: Literal["researcher_synthesis", "team_stop"]
    selection_record_hash: Digest
    canonical_write_allowed: Literal[False] = False
    authority_semantics: Literal[
        "orientation_only_not_literature_novelty_evidence"
    ] = "orientation_only_not_literature_novelty_evidence"


class FramingTeamTerminalOutcomeV1(_FramingPacketBoundV1):
    """The one immutable terminal direction allowed for a framing team run."""

    outcome_schema: Literal["econ-theorist/framing-team-terminal-outcome/v1"] = (
        "econ-theorist/framing-team-terminal-outcome/v1"
    )
    team_plan_hash: Digest
    panel_hash: Digest
    status: FramingTeamTerminalStatus
    outcome_record_hash: Digest
    worker_handoff_hash: Digest | None = None
    authority_semantics: Literal["one_terminal_direction_per_route_run"] = (
        "one_terminal_direction_per_route_run"
    )

    @model_validator(mode="after")
    def _worker_hash_matches_status(self) -> "FramingTeamTerminalOutcomeV1":
        if self.status == "handoff_ready":
            if self.worker_handoff_hash != self.outcome_record_hash:
                raise ValueError("handoff outcome must name its exact handoff")
        elif self.worker_handoff_hash is not None:
            raise ValueError("no-worker terminal outcome cannot name a handoff")
        return self


_RecordT = TypeVar("_RecordT", bound=StrictModel)


def _binding_tuple(value: _FramingPacketBoundV1) -> tuple[object, ...]:
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


def build_framing_team_delivery_authorization(
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
    source_aware_choice: Literal["available"] | None = None,
) -> FramingTeamDeliveryAuthorizationV1:
    """Build the declaration for three advisors and one conditional worker."""

    return FramingTeamDeliveryAuthorizationV1(
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
        source_aware_choice=source_aware_choice,
    )


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
        assert_safe_store_path(
            store.anchor, path, expected="file", allow_missing=False
        )
        data = path.read_bytes()
        value = model.model_validate_json(data, strict=True)
    except (OSError, RuntimeError, ValueError) as exc:
        raise OperationalError(f"invalid fixed framing-team record: {filename}") from exc
    if canonical_json_bytes(value) != data:
        raise OperationalError(f"noncanonical fixed framing-team record: {filename}")
    return value


def _read_fixed_content_record(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    filename: str,
    namespace: str,
    model: type[_RecordT],
    *,
    label: str,
    expected_digest: str | None = None,
) -> tuple[str, _RecordT] | None:
    value = _read_fixed_record(
        operational, route_run_id, filename, model
    )
    if value is None:
        return None
    digest = sha256_digest(canonical_json_bytes(value))
    if expected_digest is not None and digest != expected_digest:
        raise OperationalError(f"{label} hash differs from expected binding")
    stored = _read_record(
        _team_store(operational, route_run_id), namespace, digest, model
    )
    if stored != value:
        raise OperationalError(f"fixed {label} differs from content store")
    return digest, value


def _publish_fixed_content_record(
    store: ContentAddressedOperationalStore,
    filename: str,
    namespace: str,
    value: _RecordT,
    *,
    label: str,
) -> tuple[str, _RecordT]:
    expected_hash = sha256_digest(canonical_json_bytes(value))
    digest, _ = store.install(namespace, value)
    if digest != expected_hash:  # pragma: no cover - digest invariant
        raise OperationalError(f"{label} digest changed during publish")
    write_immutable_operational(
        store.anchor, store.root / filename, canonical_json_bytes(value)
    )
    return digest, value


def _load_current_framing_packet(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    require_current_head: bool = True,
) -> WorkPacketV1:
    packet = read_work_packet(operational, route_run_id, work_packet_hash)
    if sha256_digest(canonical_json_bytes(packet)) != work_packet_hash:
        raise OperationalError("framing team WorkPacket hash is invalid")
    if packet.route_id != _FRAMING_ROUTE_ID:
        raise OperationalError("Phase 5B.0 accepts only the framing route")
    snapshot = replay(StoreLayout.from_store_root(operational.store_root))
    if snapshot.project_id != packet.project_id:
        raise OperationalError("framing team project binding is stale")
    if require_current_head and snapshot.head != packet.base_head:
        raise OperationalError("framing team base head is stale")
    return packet


def _require_binding(
    value: _FramingPacketBoundV1,
    packet: WorkPacketV1,
    work_packet_hash: str,
    *,
    label: str,
) -> None:
    expected = _FramingPacketBoundV1(
        **_packet_binding(packet, work_packet_hash)
    )
    if _binding_tuple(value) != _binding_tuple(expected):
        raise OperationalError(f"{label} does not match the WorkPacket binding")


def _read_activation(
    operational: ProjectOperationalLayout,
    packet: WorkPacketV1,
    work_packet_hash: str,
) -> tuple[
    str,
    FramingTeamPlanV1,
    FramingTeamDeliveryAuthorizationV1,
] | None:
    plan = _read_fixed_record(
        operational,
        packet.route_run_id,
        "framing-team-plan.json",
        FramingTeamPlanV1,
    )
    if plan is None:
        return None
    plan_hash = sha256_digest(canonical_json_bytes(plan))
    stored = _read_record(
        _team_store(operational, packet.route_run_id),
        "framing-team-plans",
        plan_hash,
        FramingTeamPlanV1,
    )
    if stored != plan:
        raise OperationalError("fixed framing team plan differs from content store")
    _require_binding(plan, packet, work_packet_hash, label="framing team plan")
    authorization = _read_record(
        _team_store(operational, packet.route_run_id),
        "framing-team-delivery-authorizations",
        plan.delivery_authorization_hash,
        FramingTeamDeliveryAuthorizationV1,
    )
    _require_binding(
        authorization,
        packet,
        work_packet_hash,
        label="framing team delivery authorization",
    )
    if authorization.lane_separation_claim != plan.isolation_claim:
        raise OperationalError("team plan isolation differs from its authorization")
    return plan_hash, plan, authorization


def _publish_terminal_outcome(
    operational: ProjectOperationalLayout,
    packet: WorkPacketV1,
    work_packet_hash: str,
    outcome: FramingTeamTerminalOutcomeV1,
) -> FramingTeamTerminalOutcomeV1:
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != outcome.team_plan_hash:
        raise OperationalError("terminal framing outcome lacks its exact team plan")
    _require_binding(
        outcome, packet, work_packet_hash, label="framing team terminal outcome"
    )
    store = _team_store(operational, packet.route_run_id)
    store.install("framing-team-terminal-outcomes", outcome)
    write_immutable_operational(
        store.anchor,
        store.root / "framing-team-terminal-outcome.json",
        canonical_json_bytes(outcome),
    )
    return outcome


def _read_terminal_outcome(
    operational: ProjectOperationalLayout,
    packet: WorkPacketV1,
    work_packet_hash: str,
) -> FramingTeamTerminalOutcomeV1 | None:
    outcome = _read_fixed_record(
        operational,
        packet.route_run_id,
        "framing-team-terminal-outcome.json",
        FramingTeamTerminalOutcomeV1,
    )
    if outcome is None:
        return None
    digest = sha256_digest(canonical_json_bytes(outcome))
    stored = _read_record(
        _team_store(operational, packet.route_run_id),
        "framing-team-terminal-outcomes",
        digest,
        FramingTeamTerminalOutcomeV1,
    )
    if stored != outcome:
        raise OperationalError("fixed terminal outcome differs from content store")
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != outcome.team_plan_hash:
        raise OperationalError("terminal framing outcome lacks its exact team plan")
    _require_binding(
        outcome, packet, work_packet_hash, label="framing team terminal outcome"
    )
    return outcome


def framing_lane_input_hash(
    plan: FramingTeamPlanV1,
    plan_hash: str,
    lane_id: FramingAdvisoryLaneId,
) -> str:
    """Bind the exact packet identity and role overlay delivered to one lane."""

    return sha256_digest(
        canonical_json_bytes(
            {
                "team_plan_hash": plan_hash,
                "work_packet_hash": plan.work_packet_hash,
                "lane_id": lane_id,
                "role_overlay": plan.role_overlays[lane_id],
            }
        )
    )


def open_framing_team_plan(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    delivery_authorization: FramingTeamDeliveryAuthorizationV1,
    execution_mode: Literal[
        "isolated_multi_agent", "sequential_single_model"
    ] = "isolated_multi_agent",
    isolation_claim: Literal["logical", "host_enforced"] = "logical",
) -> tuple[str, FramingTeamPlanV1]:
    """Declare the bounded advisory team before any lane invocation."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    _require_binding(
        delivery_authorization,
        packet,
        work_packet_hash,
        label="framing team delivery authorization",
    )
    if delivery_authorization.lane_separation_claim != isolation_claim:
        raise OperationalError(
            "requested team isolation differs from delivery authorization"
        )
    authorization_hash = sha256_digest(
        canonical_json_bytes(delivery_authorization)
    )
    plan = FramingTeamPlanV1(
        **_packet_binding(packet, work_packet_hash),
        execution_mode=execution_mode,
        isolation_claim=isolation_claim,
        delivery_authorization_hash=authorization_hash,
        role_overlays=dict(_ROLE_OVERLAYS),
    )
    existing = _read_activation(operational, packet, work_packet_hash)
    if existing is not None:
        if existing[2] != delivery_authorization or existing[1] != plan:
            raise OperationalError(
                "framing team is already active under a different authorization"
            )
        return existing[0], existing[1]
    store = _team_store(operational, route_run_id)
    installed_authorization_hash, _ = store.install(
        "framing-team-delivery-authorizations", delivery_authorization
    )
    if installed_authorization_hash != authorization_hash:  # pragma: no cover
        raise OperationalError("framing team authorization digest changed")
    plan_hash, _ = store.install("framing-team-plans", plan)
    write_immutable_operational(
        store.anchor,
        store.root / "framing-team-plan.json",
        canonical_json_bytes(plan),
    )
    return plan_hash, plan


def framing_team_is_active(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    require_current_head: bool = True,
) -> bool:
    """Return whether this exact packet has entered the declared team path."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    return _read_activation(operational, packet, work_packet_hash) is not None


def read_framing_team_plan(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    team_plan_hash: str,
) -> FramingTeamPlanV1:
    """Read one declared team plan and revalidate its live packet binding."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != team_plan_hash:
        raise OperationalError("framing team plan is not the active plan")
    plan = activation[1]
    return plan


def read_framing_team_delivery_authorization(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    team_plan_hash: str,
    require_current_head: bool = True,
) -> FramingTeamDeliveryAuthorizationV1:
    """Read the exact host/session declaration behind one active team plan."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != team_plan_hash:
        raise OperationalError("framing team authorization is not active")
    return activation[2]


def build_framing_lane_output(
    plan: FramingTeamPlanV1,
    plan_hash: str,
    *,
    lane_id: FramingAdvisoryLaneId,
    agent_label: str,
    content_markdown: str,
    model_observation: str | None = None,
) -> FramingLaneOutputV1:
    """Build one complete advisory output without exposing binding fields."""

    return FramingLaneOutputV1(
        **plan.model_dump(
            include={
                "project_id",
                "route_id",
                "route_run_id",
                "base_head",
                "work_packet_hash",
                "context_manifest_hash",
                "compiled_context_hash",
                "run_input_brief_hash",
            }
        ),
        team_plan_hash=plan_hash,
        lane_id=lane_id,
        role=_LANE_ROLES[lane_id],
        lane_input_hash=framing_lane_input_hash(plan, plan_hash, lane_id),
        agent_label=agent_label,
        model_observation=model_observation,
        content_markdown=content_markdown,
    )


def publish_framing_team_panel(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    team_plan_hash: str,
    mentor: FramingLaneOutputV1,
    collaborators: tuple[FramingLaneOutputV1, FramingLaneOutputV1],
) -> tuple[str, FramingTeamPanelV1]:
    """Validate and immutably publish all advisory opinions together."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    store = _team_store(operational, route_run_id)
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != team_plan_hash:
        raise OperationalError("framing team panel uses a non-active plan")
    plan = activation[1]
    _require_binding(plan, packet, work_packet_hash, label="framing team plan")
    for output in (mentor, *collaborators):
        _require_binding(output, packet, work_packet_hash, label="framing lane output")
        if output.team_plan_hash != team_plan_hash:
            raise OperationalError("framing lane output references a different plan")
        expected_input = framing_lane_input_hash(plan, team_plan_hash, output.lane_id)
        if output.lane_input_hash != expected_input:
            raise OperationalError("framing lane input binding is invalid")
    panel = FramingTeamPanelV1(
        **_packet_binding(packet, work_packet_hash),
        team_plan_hash=team_plan_hash,
        mentor=mentor,
        collaborators=collaborators,
    )
    expected_panel_hash = sha256_digest(canonical_json_bytes(panel))
    terminal = _read_terminal_outcome(operational, packet, work_packet_hash)
    if terminal is not None and terminal.panel_hash != expected_panel_hash:
        raise OperationalError("framing team already has a terminal direction")
    for output in (mentor, *collaborators):
        store.install("framing-lane-outputs", output)
    panel_hash, _ = store.install("framing-team-panels", panel)
    if panel_hash != expected_panel_hash:  # pragma: no cover
        raise OperationalError("framing team panel digest changed during publish")
    return panel_hash, panel


def read_framing_team_panel(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    panel_hash: str,
) -> FramingTeamPanelV1:
    """Read one complete panel and revalidate its plan and packet binding."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    store = _team_store(operational, route_run_id)
    panel = _read_record(
        store, "framing-team-panels", panel_hash, FramingTeamPanelV1
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != panel.team_plan_hash:
        raise OperationalError("framing team panel uses a non-active plan")
    plan = activation[1]
    _require_binding(plan, packet, work_packet_hash, label="framing team plan")
    _require_binding(panel, packet, work_packet_hash, label="framing team panel")
    return panel


def framing_choice_review_required(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    require_current_head: bool = True,
) -> bool:
    """Return the immutable source-aware mode of the active team plan."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None:
        raise OperationalError("framing team is not active")
    return activation[2].source_aware_choice == "available"


def build_framing_choice_review(
    panel: FramingTeamPanelV1,
    panel_hash: str,
    *,
    coordinator_agent_label: str,
    coordinator_model_observation: str,
    acquisition_mode: Literal["online_host_search", "offline_user_bundle"],
    search_scope: str,
    coverage_limits: str,
    mentor_screen_markdown: str,
    sources: tuple[FramingChoiceSourceV1, ...],
    direction_cards: tuple[
        FramingDirectionCardV1,
        FramingDirectionCardV1,
    ],
) -> FramingChoiceReviewV1:
    """Build one comparison review without changing the raw blind panel."""

    return FramingChoiceReviewV1(
        **panel.model_dump(include=set(_FramingPacketBoundV1.model_fields)),
        team_plan_hash=panel.team_plan_hash,
        panel_hash=panel_hash,
        coordinator_agent_label=coordinator_agent_label,
        coordinator_model_observation=coordinator_model_observation,
        acquisition_mode=acquisition_mode,
        search_scope=search_scope,
        coverage_limits=coverage_limits,
        mentor_screen_markdown=mentor_screen_markdown,
        sources=sources,
        direction_cards=direction_cards,
    )


def _validate_choice_review(
    operational: ProjectOperationalLayout,
    packet: WorkPacketV1,
    work_packet_hash: str,
    review: FramingChoiceReviewV1,
) -> None:
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[2].source_aware_choice != "available":
        raise OperationalError(
            "framing choice review was not authorized at team activation"
        )
    _require_binding(review, packet, work_packet_hash, label="framing choice review")
    if review.team_plan_hash != activation[0]:
        raise OperationalError("framing choice review references a different team plan")
    panel = _read_record(
        _team_store(operational, packet.route_run_id),
        "framing-team-panels",
        review.panel_hash,
        FramingTeamPanelV1,
    )
    _require_binding(panel, packet, work_packet_hash, label="framing team panel")
    if panel.team_plan_hash != review.team_plan_hash:
        raise OperationalError(
            "framing choice review references a panel from a different plan"
        )


def _read_choice_review_for_packet(
    operational: ProjectOperationalLayout,
    packet: WorkPacketV1,
    work_packet_hash: str,
    *,
    expected_review_hash: str | None = None,
) -> tuple[str, FramingChoiceReviewV1] | None:
    result = _read_fixed_content_record(
        operational,
        packet.route_run_id,
        "framing-choice-review.json",
        "framing-choice-reviews",
        FramingChoiceReviewV1,
        label="framing choice review",
        expected_digest=expected_review_hash,
    )
    if result is None:
        return None
    review_hash, review = result
    _validate_choice_review(operational, packet, work_packet_hash, review)
    return result


def publish_framing_choice_review(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    panel_hash: str,
    review: FramingChoiceReviewV1,
) -> tuple[str, FramingChoiceReviewV1]:
    """Publish the one immutable source-aware review, with exact retry."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    if review.panel_hash != panel_hash:
        raise OperationalError("framing choice review references a different panel")
    _validate_choice_review(operational, packet, work_packet_hash, review)
    expected_hash = sha256_digest(canonical_json_bytes(review))
    existing = _read_choice_review_for_packet(
        operational, packet, work_packet_hash
    )
    if existing is not None:
        if existing != (expected_hash, review):
            raise OperationalError(
                "framing run already has a different source-aware choice review"
            )
        return existing
    if _read_terminal_outcome(operational, packet, work_packet_hash) is not None:
        raise OperationalError(
            "cannot publish a framing choice review after terminal direction"
        )
    return _publish_fixed_content_record(
        _team_store(operational, route_run_id),
        "framing-choice-review.json",
        "framing-choice-reviews",
        review,
        label="framing choice review",
    )


def read_framing_choice_review(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    review_hash: str,
    require_current_head: bool = True,
) -> FramingChoiceReviewV1:
    """Read the exact fixed review and all of its packet/panel bindings."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    result = _read_choice_review_for_packet(
        operational,
        packet,
        work_packet_hash,
        expected_review_hash=review_hash,
    )
    if result is None:
        raise OperationalError("framing choice review is missing")
    return result[1]


def _selection_binding_filename(selection_record_hash: str) -> str:
    key_digest = sha256_digest(selection_record_hash.encode("utf-8"))
    # Keep the fixed index below the ordinary Windows path limit even when the
    # operational run id and temporary project root are both long.
    return f"choice/{key_digest}.json"


def _read_choice_selection(
    store: ContentAddressedOperationalStore,
    kind: Literal["researcher_synthesis", "team_stop"],
    digest: str,
) -> FramingResearcherSynthesisV1 | FramingTeamStopV1:
    if kind == "researcher_synthesis":
        return _read_record(
            store, "framing-team-syntheses", digest, FramingResearcherSynthesisV1
        )
    return _read_record(store, "framing-team-stops", digest, FramingTeamStopV1)


def _require_choice_selection(
    selection: FramingResearcherSynthesisV1 | FramingTeamStopV1,
    packet: WorkPacketV1,
    work_packet_hash: str,
    *,
    team_plan_hash: str,
    panel_hash: str,
) -> None:
    _require_binding(
        selection, packet, work_packet_hash, label="framing choice selection"
    )
    if (
        selection.team_plan_hash != team_plan_hash
        or selection.panel_hash != panel_hash
    ):
        raise OperationalError(
            "source-aware selection differs from its review binding"
        )


def _read_source_aware_selection_for_packet(
    operational: ProjectOperationalLayout,
    packet: WorkPacketV1,
    work_packet_hash: str,
    *,
    selection_record_hash: str,
) -> tuple[str, FramingSourceAwareSelectionBindingV1] | None:
    result = _read_fixed_content_record(
        operational,
        packet.route_run_id,
        _selection_binding_filename(selection_record_hash),
        "choice-links",
        FramingSourceAwareSelectionBindingV1,
        label="source-aware selection binding",
    )
    if result is None:
        return None
    _, binding = result
    _require_binding(
        binding,
        packet,
        work_packet_hash,
        label="source-aware selection binding",
    )
    if binding.selection_record_hash != selection_record_hash:
        raise OperationalError(
            "source-aware selection binding names a different selection record"
        )
    review_result = _read_choice_review_for_packet(
        operational,
        packet,
        work_packet_hash,
        expected_review_hash=binding.review_hash,
    )
    if review_result is None:
        raise OperationalError(
            "source-aware selection binding lacks its exact choice review"
        )
    review = review_result[1]
    if (
        binding.team_plan_hash != review.team_plan_hash
        or binding.panel_hash != review.panel_hash
    ):
        raise OperationalError(
            "source-aware selection binding differs from its choice review"
        )
    selection = _read_choice_selection(
        _team_store(operational, packet.route_run_id),
        binding.selection_record_kind,
        selection_record_hash,
    )
    _require_choice_selection(
        selection,
        packet,
        work_packet_hash,
        team_plan_hash=binding.team_plan_hash,
        panel_hash=binding.panel_hash,
    )
    return result


def publish_framing_source_aware_selection_binding(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    review_hash: str,
    selection_record_kind: Literal["researcher_synthesis", "team_stop"],
    selection_record_hash: str,
) -> tuple[str, FramingSourceAwareSelectionBindingV1]:
    """Bind one existing synthesis or stop to the exact fixed review."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    review_result = _read_choice_review_for_packet(
        operational,
        packet,
        work_packet_hash,
        expected_review_hash=review_hash,
    )
    if review_result is None:
        raise OperationalError("source-aware selection lacks a choice review")
    review = review_result[1]
    store = _team_store(operational, route_run_id)
    selection = _read_choice_selection(
        store, selection_record_kind, selection_record_hash
    )
    if (
        isinstance(selection, FramingResearcherSynthesisV1)
        and "mentor" in selection.selected_lane_ids
    ):
        raise OperationalError(
            "source-aware choice cannot select the mentor as a direction"
        )
    _require_choice_selection(
        selection,
        packet,
        work_packet_hash,
        team_plan_hash=review.team_plan_hash,
        panel_hash=review.panel_hash,
    )
    binding = FramingSourceAwareSelectionBindingV1(
        **_packet_binding(packet, work_packet_hash),
        team_plan_hash=review.team_plan_hash,
        panel_hash=review.panel_hash,
        review_hash=review_hash,
        selection_record_kind=selection_record_kind,
        selection_record_hash=selection_record_hash,
    )
    expected_hash = sha256_digest(canonical_json_bytes(binding))
    existing = _read_source_aware_selection_for_packet(
        operational,
        packet,
        work_packet_hash,
        selection_record_hash=selection_record_hash,
    )
    if existing is not None:
        if existing != (expected_hash, binding):
            raise OperationalError(
                "selection already has a different source-aware review binding"
            )
        result = existing
    else:
        result = _publish_fixed_content_record(
            store,
            _selection_binding_filename(selection_record_hash),
            "choice-links",
            binding,
            label="source-aware selection binding",
        )
    if isinstance(selection, FramingResearcherSynthesisV1):
        if selection.disposition in {"park", "kill"}:
            terminal_status: FramingTeamTerminalStatus = (
                "parked" if selection.disposition == "park" else "killed"
            )
            _publish_terminal_outcome(
                operational,
                packet,
                work_packet_hash,
                FramingTeamTerminalOutcomeV1(
                    **_packet_binding(packet, work_packet_hash),
                    team_plan_hash=selection.team_plan_hash,
                    panel_hash=selection.panel_hash,
                    status=terminal_status,
                    outcome_record_hash=selection_record_hash,
                ),
            )
    elif selection.status == "new_brief_required":
        _publish_terminal_outcome(
            operational,
            packet,
            work_packet_hash,
            FramingTeamTerminalOutcomeV1(
                **_packet_binding(packet, work_packet_hash),
                team_plan_hash=selection.team_plan_hash,
                panel_hash=selection.panel_hash,
                status="new_brief_required",
                outcome_record_hash=selection_record_hash,
            ),
        )
    return result


def read_framing_source_aware_selection_binding(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    selection_record_hash: str,
    require_current_head: bool = True,
) -> FramingSourceAwareSelectionBindingV1:
    """Read and revalidate a synthesis/stop-to-review binding."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    result = _read_source_aware_selection_for_packet(
        operational,
        packet,
        work_packet_hash,
        selection_record_hash=selection_record_hash,
    )
    if result is None:
        raise OperationalError(
            "source-aware selection binding is required but missing"
        )
    return result[1]


def build_framing_researcher_synthesis(
    panel: FramingTeamPanelV1,
    panel_hash: str,
    *,
    researcher_id: str,
    researcher_text: str,
    disposition: FramingDisposition,
    selected_lane_ids: tuple[FramingAdvisoryLaneId, ...] = (),
    synthesis_markdown: str,
    worker_brief: str | None = None,
) -> FramingResearcherSynthesisV1:
    """Normalize an attributed user direction without creating a Decision."""

    return FramingResearcherSynthesisV1(
        **panel.model_dump(
            include={
                "project_id",
                "route_id",
                "route_run_id",
                "base_head",
                "work_packet_hash",
                "context_manifest_hash",
                "compiled_context_hash",
                "run_input_brief_hash",
            }
        ),
        team_plan_hash=panel.team_plan_hash,
        panel_hash=panel_hash,
        researcher_id=researcher_id,
        researcher_text=researcher_text,
        disposition=disposition,
        selected_lane_ids=selected_lane_ids,
        synthesis_markdown=synthesis_markdown,
        worker_brief=worker_brief,
    )


def publish_framing_researcher_synthesis(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    panel_hash: str,
    synthesis: FramingResearcherSynthesisV1,
) -> tuple[str, FramingResearcherSynthesisV1]:
    """Publish an exact user direction even when it produces no handoff."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    store = _team_store(operational, route_run_id)
    panel = _read_record(
        store, "framing-team-panels", panel_hash, FramingTeamPanelV1
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != panel.team_plan_hash:
        raise OperationalError("researcher synthesis uses a non-active plan")
    plan = activation[1]
    source_aware = activation[2].source_aware_choice == "available"
    if source_aware:
        review_result = _read_choice_review_for_packet(
            operational, packet, work_packet_hash
        )
        if review_result is None:
            raise OperationalError(
                "source-aware researcher synthesis requires the fixed choice review"
            )
        if review_result[1].panel_hash != panel_hash:
            raise OperationalError(
                "source-aware researcher synthesis differs from the reviewed panel"
            )
        if "mentor" in synthesis.selected_lane_ids:
            raise OperationalError(
                "source-aware choice cannot select the mentor as a direction"
            )
    _require_binding(plan, packet, work_packet_hash, label="framing team plan")
    _require_binding(panel, packet, work_packet_hash, label="framing team panel")
    _require_binding(
        synthesis, packet, work_packet_hash, label="researcher synthesis"
    )
    if synthesis.panel_hash != panel_hash:
        raise OperationalError("researcher synthesis references a different panel")
    if synthesis.team_plan_hash != panel.team_plan_hash:
        raise OperationalError("researcher synthesis references a different plan")
    expected_synthesis_hash = sha256_digest(canonical_json_bytes(synthesis))
    terminal = _read_terminal_outcome(operational, packet, work_packet_hash)
    if terminal is not None:
        if synthesis.disposition in {"park", "kill"}:
            expected_status = (
                "parked" if synthesis.disposition == "park" else "killed"
            )
            exact_retry = (
                terminal.status == expected_status
                and terminal.outcome_record_hash == expected_synthesis_hash
            )
        elif terminal.status == "handoff_ready" and terminal.worker_handoff_hash:
            prior_handoff = _read_record(
                store,
                "framing-team-handoffs",
                terminal.worker_handoff_hash,
                FramingWorkerHandoffV1,
            )
            exact_retry = prior_handoff.synthesis_hash == expected_synthesis_hash
        else:
            exact_retry = False
        if not exact_retry:
            raise OperationalError(
                "framing team already has a different terminal direction"
            )
    synthesis_hash, _ = store.install("framing-team-syntheses", synthesis)
    if synthesis_hash != expected_synthesis_hash:  # pragma: no cover
        raise OperationalError("researcher synthesis digest changed during publish")
    if synthesis.disposition in {"park", "kill"} and not source_aware:
        status: FramingTeamTerminalStatus = (
            "parked" if synthesis.disposition == "park" else "killed"
        )
        _publish_terminal_outcome(
            operational,
            packet,
            work_packet_hash,
            FramingTeamTerminalOutcomeV1(
                **_packet_binding(packet, work_packet_hash),
                team_plan_hash=synthesis.team_plan_hash,
                panel_hash=panel_hash,
                status=status,
                outcome_record_hash=synthesis_hash,
            ),
        )
    return synthesis_hash, synthesis


def build_framing_team_stop(
    panel: FramingTeamPanelV1,
    panel_hash: str,
    *,
    researcher_id: str,
    researcher_text: str,
    status: FramingTeamStopStatus,
    reason: str,
) -> FramingTeamStopV1:
    """Build an attributed clarification or new-brief stop without a handoff."""

    return FramingTeamStopV1(
        **panel.model_dump(
            include={
                "project_id",
                "route_id",
                "route_run_id",
                "base_head",
                "work_packet_hash",
                "context_manifest_hash",
                "compiled_context_hash",
                "run_input_brief_hash",
            }
        ),
        team_plan_hash=panel.team_plan_hash,
        panel_hash=panel_hash,
        researcher_id=researcher_id,
        researcher_text=researcher_text,
        status=status,
        reason=reason,
    )


def publish_framing_team_stop(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    panel_hash: str,
    stop: FramingTeamStopV1,
) -> tuple[str, FramingTeamStopV1]:
    """Persist one typed stop while proving that no worker handoff was made."""

    panel = read_framing_team_panel(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        panel_hash=panel_hash,
    )
    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != panel.team_plan_hash:
        raise OperationalError("framing team stop uses a non-active plan")
    source_aware = activation[2].source_aware_choice == "available"
    if source_aware:
        review_result = _read_choice_review_for_packet(
            operational, packet, work_packet_hash
        )
        if review_result is None:
            raise OperationalError(
                "source-aware framing stop requires the fixed choice review"
            )
        if review_result[1].panel_hash != panel_hash:
            raise OperationalError(
                "source-aware framing stop differs from the reviewed panel"
            )
    _require_binding(stop, packet, work_packet_hash, label="framing team stop")
    if stop.panel_hash != panel_hash:
        raise OperationalError("framing team stop references a different panel")
    if stop.team_plan_hash != panel.team_plan_hash:
        raise OperationalError("framing team stop references a different plan")
    expected_stop_hash = sha256_digest(canonical_json_bytes(stop))
    terminal = _read_terminal_outcome(operational, packet, work_packet_hash)
    if terminal is not None:
        exact_retry = (
            stop.status == "new_brief_required"
            and terminal.status == "new_brief_required"
            and terminal.outcome_record_hash == expected_stop_hash
        )
        if not exact_retry:
            raise OperationalError(
                "framing team already has a different terminal direction"
            )
    stop_hash, _ = _team_store(operational, route_run_id).install(
        "framing-team-stops", stop
    )
    if stop_hash != expected_stop_hash:  # pragma: no cover
        raise OperationalError("framing team stop digest changed during publish")
    if stop.status == "new_brief_required" and not source_aware:
        _publish_terminal_outcome(
            operational,
            packet,
            work_packet_hash,
            FramingTeamTerminalOutcomeV1(
                **_packet_binding(packet, work_packet_hash),
                team_plan_hash=stop.team_plan_hash,
                panel_hash=panel_hash,
                status="new_brief_required",
                outcome_record_hash=stop_hash,
            ),
        )
    return stop_hash, stop


def publish_framing_worker_handoff(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    synthesis_hash: str,
) -> tuple[str, FramingWorkerHandoffV1]:
    """Publish exactly one worker handoff for an active user synthesis."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    store = _team_store(operational, route_run_id)
    synthesis = _read_record(
        store,
        "framing-team-syntheses",
        synthesis_hash,
        FramingResearcherSynthesisV1,
    )
    panel = _read_record(
        store, "framing-team-panels", synthesis.panel_hash, FramingTeamPanelV1
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != panel.team_plan_hash:
        raise OperationalError("worker handoff uses a non-active plan")
    _require_binding(panel, packet, work_packet_hash, label="framing team panel")
    _require_binding(
        synthesis, packet, work_packet_hash, label="researcher synthesis"
    )
    if synthesis.team_plan_hash != panel.team_plan_hash:
        raise OperationalError("researcher synthesis references a different plan")
    if synthesis.disposition in {"park", "kill"}:
        raise OperationalError(
            f"{synthesis.disposition} framing disposition has no worker handoff"
        )
    if activation[2].source_aware_choice == "available":
        selection_binding = _read_source_aware_selection_for_packet(
            operational,
            packet,
            work_packet_hash,
            selection_record_hash=synthesis_hash,
        )
        if selection_binding is None:
            raise OperationalError(
                "source-aware worker handoff requires the synthesis selection binding"
            )
        if selection_binding[1].selection_record_kind != "researcher_synthesis":
            raise OperationalError(
                "source-aware worker selection is not a researcher synthesis"
            )
    assert synthesis.worker_brief is not None
    lane_outputs = (panel.mentor, *panel.collaborators)
    lane_hashes = tuple(
        sha256_digest(canonical_json_bytes(output)) for output in lane_outputs
    )
    handoff = FramingWorkerHandoffV1(
        **_packet_binding(packet, work_packet_hash),
        team_plan_hash=panel.team_plan_hash,
        panel_hash=synthesis.panel_hash,
        synthesis_hash=synthesis_hash,
        preserved_lane_output_hashes=lane_hashes,
        selected_lane_ids=synthesis.selected_lane_ids,
        candidate_logical_path=packet.candidate_logical_path,
        worker_brief=synthesis.worker_brief,
    )
    expected_handoff_hash = sha256_digest(canonical_json_bytes(handoff))
    terminal = _read_terminal_outcome(operational, packet, work_packet_hash)
    if terminal is not None and (
        terminal.status != "handoff_ready"
        or terminal.worker_handoff_hash != expected_handoff_hash
    ):
        raise OperationalError(
            "framing team already has a different terminal direction"
        )
    handoff_hash, _ = store.install("framing-team-handoffs", handoff)
    if handoff_hash != expected_handoff_hash:  # pragma: no cover - digest invariant
        raise OperationalError("framing worker handoff digest changed during publish")
    _publish_terminal_outcome(
        operational,
        packet,
        work_packet_hash,
        FramingTeamTerminalOutcomeV1(
            **_packet_binding(packet, work_packet_hash),
            team_plan_hash=handoff.team_plan_hash,
            panel_hash=handoff.panel_hash,
            status="handoff_ready",
            outcome_record_hash=handoff_hash,
            worker_handoff_hash=handoff_hash,
        ),
    )
    return handoff_hash, handoff


def read_framing_worker_inputs(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    handoff_hash: str,
    require_current_head: bool = True,
) -> tuple[
    WorkPacketV1,
    FramingTeamPanelV1,
    FramingResearcherSynthesisV1,
    FramingWorkerHandoffV1,
]:
    """Read and revalidate the complete bounded input for the one worker.

    ``require_current_head=False`` is reserved for an exact completion retry
    after this route already has a canonical outcome; all immutable packet and
    sidecar bindings are still revalidated.
    """

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    store = _team_store(operational, route_run_id)
    handoff = _read_record(
        store, "framing-team-handoffs", handoff_hash, FramingWorkerHandoffV1
    )
    panel = _read_record(
        store, "framing-team-panels", handoff.panel_hash, FramingTeamPanelV1
    )
    activation = _read_activation(operational, packet, work_packet_hash)
    if activation is None or activation[0] != handoff.team_plan_hash:
        raise OperationalError("worker handoff uses a non-active plan")
    plan = activation[1]
    synthesis = _read_record(
        store,
        "framing-team-syntheses",
        handoff.synthesis_hash,
        FramingResearcherSynthesisV1,
    )
    for label, value in (
        ("framing team plan", plan),
        ("framing worker handoff", handoff),
        ("framing team panel", panel),
        ("researcher synthesis", synthesis),
    ):
        _require_binding(value, packet, work_packet_hash, label=label)
    if synthesis.panel_hash != handoff.panel_hash:
        raise OperationalError("worker input panel hashes disagree")
    if synthesis.team_plan_hash != handoff.team_plan_hash:
        raise OperationalError("worker input plan hashes disagree")
    if panel.team_plan_hash != handoff.team_plan_hash:
        raise OperationalError("worker input panel and handoff plans disagree")
    if synthesis.disposition not in {"continue", "simplify", "pivot"}:
        raise OperationalError("inactive researcher synthesis cannot reach a worker")
    if synthesis.worker_brief is None:
        raise OperationalError("active researcher synthesis lacks a worker brief")
    if handoff.worker_brief != synthesis.worker_brief:
        raise OperationalError("worker handoff brief differs from researcher synthesis")
    if handoff.selected_lane_ids != synthesis.selected_lane_ids:
        raise OperationalError("worker handoff selection differs from researcher synthesis")
    if activation[2].source_aware_choice == "available":
        selection_binding = _read_source_aware_selection_for_packet(
            operational,
            packet,
            work_packet_hash,
            selection_record_hash=handoff.synthesis_hash,
        )
        if selection_binding is None:
            raise OperationalError(
                "source-aware choice review lacks the synthesis selection binding"
            )
        if selection_binding[1].selection_record_kind != "researcher_synthesis":
            raise OperationalError(
                "source-aware worker selection is not a researcher synthesis"
            )
    lane_hashes = tuple(
        sha256_digest(canonical_json_bytes(output))
        for output in (panel.mentor, *panel.collaborators)
    )
    if lane_hashes != handoff.preserved_lane_output_hashes:
        raise OperationalError("worker handoff does not preserve every lane output")
    for digest, embedded in zip(
        handoff.preserved_lane_output_hashes,
        (panel.mentor, *panel.collaborators),
        strict=True,
    ):
        stored = _read_record(
            store, "framing-lane-outputs", digest, FramingLaneOutputV1
        )
        if stored != embedded:
            raise OperationalError("stored lane output differs from the panel")
    if handoff.candidate_logical_path != packet.candidate_logical_path:
        raise OperationalError("worker handoff candidate path differs from WorkPacket")
    terminal = _read_terminal_outcome(operational, packet, work_packet_hash)
    if (
        terminal is None
        or terminal.status != "handoff_ready"
        or terminal.worker_handoff_hash != handoff_hash
        or terminal.outcome_record_hash != handoff_hash
    ):
        raise OperationalError("worker handoff is not the terminal team direction")
    return packet, panel, synthesis, handoff


def _completion_binding_filename(completion_operation_key: str) -> str:
    key_digest = sha256_digest(completion_operation_key.encode("utf-8"))
    return f"team-completions/by-key/{key_digest}.json"


def _worker_activation_filename(handoff_hash: str) -> str:
    return f"team-workers/by-handoff/{handoff_hash}.json"


def publish_framing_worker_completion_binding(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    handoff_hash: str,
    completion_operation_key: str,
    delivery_envelope_hash: str,
    candidate_digest: str,
    worker_agent_label: str,
    worker_model_observation: str,
    require_current_head: bool = True,
) -> tuple[str, FramingWorkerCompletionBindingV1, bool]:
    """Bind one team-authored completion request without changing its receipt."""

    packet, panel, synthesis, handoff = read_framing_worker_inputs(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        handoff_hash=handoff_hash,
        require_current_head=require_current_head,
    )
    authorization = read_framing_team_delivery_authorization(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        team_plan_hash=handoff.team_plan_hash,
        require_current_head=require_current_head,
    )
    if authorization.source_delivery_envelope_hash != delivery_envelope_hash:
        raise OperationalError(
            "worker completion delivery differs from team authorization"
        )
    activation = FramingWorkerActivationV1(
        **_packet_binding(packet, work_packet_hash),
        team_plan_hash=handoff.team_plan_hash,
        panel_hash=handoff.panel_hash,
        synthesis_hash=handoff.synthesis_hash,
        worker_handoff_hash=handoff_hash,
        delivery_envelope_hash=delivery_envelope_hash,
        worker_agent_label=worker_agent_label,
        worker_model_observation=worker_model_observation,
    )
    store = _team_store(operational, route_run_id)
    existing_activation = _read_fixed_record(
        operational,
        route_run_id,
        _worker_activation_filename(handoff_hash),
        FramingWorkerActivationV1,
    )
    if existing_activation is not None and existing_activation != activation:
        raise OperationalError(
            "framing handoff is already assigned to a different research worker"
        )
    activation_hash = sha256_digest(canonical_json_bytes(activation))
    if existing_activation is None:
        activation_content_was_present = path_entry_exists(
            store.path_for("team-workers", activation_hash)
        )
        installed_activation_hash, _ = store.install("team-workers", activation)
        if installed_activation_hash != activation_hash:  # pragma: no cover
            raise OperationalError("worker activation digest changed")
        activation_fixed_written = write_immutable_operational(
            store.anchor,
            store.root / _worker_activation_filename(handoff_hash),
            canonical_json_bytes(activation),
        )
        activation_mutated = (
            not activation_content_was_present or activation_fixed_written
        )
    else:
        stored_activation = _read_record(
            store,
            "team-workers",
            activation_hash,
            FramingWorkerActivationV1,
        )
        if stored_activation != existing_activation:
            raise OperationalError(
                "fixed worker activation differs from content store"
            )
        activation_mutated = False
    binding = FramingWorkerCompletionBindingV1(
        **_packet_binding(packet, work_packet_hash),
        team_plan_hash=handoff.team_plan_hash,
        panel_hash=handoff.panel_hash,
        synthesis_hash=handoff.synthesis_hash,
        worker_handoff_hash=handoff_hash,
        worker_activation_hash=activation_hash,
        completion_operation_key=completion_operation_key,
        delivery_envelope_hash=delivery_envelope_hash,
        candidate_digest=candidate_digest,
        worker_agent_label=worker_agent_label,
        worker_model_observation=worker_model_observation,
    )
    if binding.panel_hash != sha256_digest(canonical_json_bytes(panel)):
        raise OperationalError("worker completion panel hash is invalid")
    if binding.synthesis_hash != sha256_digest(canonical_json_bytes(synthesis)):
        raise OperationalError("worker completion synthesis hash is invalid")
    binding_hash = sha256_digest(canonical_json_bytes(binding))
    content_path = store.path_for("team-completions", binding_hash)
    content_was_present = path_entry_exists(content_path)
    installed_hash, _ = store.install("team-completions", binding)
    if installed_hash != binding_hash:  # pragma: no cover - digest invariant
        raise OperationalError("worker completion binding digest changed")
    fixed_written = write_immutable_operational(
        store.anchor,
        store.root / _completion_binding_filename(binding.completion_operation_key),
        canonical_json_bytes(binding),
    )
    return binding_hash, binding, (
        activation_mutated or not content_was_present or fixed_written
    )


def read_framing_worker_activation(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    handoff_hash: str,
    require_current_head: bool = True,
) -> FramingWorkerActivationV1:
    """Read and revalidate the one worker fixed for a terminal handoff."""

    packet, panel, synthesis, handoff = read_framing_worker_inputs(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        handoff_hash=handoff_hash,
        require_current_head=require_current_head,
    )
    activation = _read_fixed_record(
        operational,
        route_run_id,
        _worker_activation_filename(handoff_hash),
        FramingWorkerActivationV1,
    )
    if activation is None:
        raise OperationalError("framing worker activation is unavailable")
    _require_binding(activation, packet, work_packet_hash, label="worker activation")
    if (
        activation.team_plan_hash != handoff.team_plan_hash
        or activation.panel_hash != handoff.panel_hash
        or activation.synthesis_hash != handoff.synthesis_hash
        or activation.worker_handoff_hash != handoff_hash
        or activation.panel_hash != sha256_digest(canonical_json_bytes(panel))
        or activation.synthesis_hash
        != sha256_digest(canonical_json_bytes(synthesis))
    ):
        raise OperationalError("worker activation differs from its handoff")
    activation_hash = sha256_digest(canonical_json_bytes(activation))
    stored = _read_record(
        _team_store(operational, route_run_id),
        "team-workers",
        activation_hash,
        FramingWorkerActivationV1,
    )
    if stored != activation:
        raise OperationalError("fixed worker activation differs from content store")
    authorization = read_framing_team_delivery_authorization(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        team_plan_hash=activation.team_plan_hash,
        require_current_head=require_current_head,
    )
    if (
        activation.delivery_envelope_hash
        != authorization.source_delivery_envelope_hash
    ):
        raise OperationalError("worker activation delivery differs from authorization")
    return activation


def framing_worker_activation_exists(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    handoff_hash: str,
    require_current_head: bool = True,
) -> bool:
    """Probe the fixed worker for a handoff and validate any present record."""

    store = _team_store(operational, route_run_id)
    path = store.root / _worker_activation_filename(handoff_hash)
    if not path_entry_exists(path):
        return False
    read_framing_worker_activation(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        handoff_hash=handoff_hash,
        require_current_head=require_current_head,
    )
    return True


def read_framing_worker_completion_binding(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    completion_operation_key: str,
    require_current_head: bool = True,
) -> FramingWorkerCompletionBindingV1:
    """Read and revalidate the Phase 5B provenance for one completion key."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        require_current_head=require_current_head,
    )
    binding = _read_fixed_record(
        operational,
        route_run_id,
        _completion_binding_filename(completion_operation_key),
        FramingWorkerCompletionBindingV1,
    )
    if binding is None:
        raise OperationalError("framing worker completion binding is unavailable")
    if binding.completion_operation_key != completion_operation_key:
        raise OperationalError("framing worker completion operation key differs")
    binding_hash = sha256_digest(canonical_json_bytes(binding))
    stored = _read_record(
        _team_store(operational, route_run_id),
        "team-completions",
        binding_hash,
        FramingWorkerCompletionBindingV1,
    )
    if stored != binding:
        raise OperationalError(
            "fixed worker completion binding differs from content store"
        )
    _require_binding(
        binding, packet, work_packet_hash, label="worker completion binding"
    )
    _, panel, synthesis, handoff = read_framing_worker_inputs(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        handoff_hash=binding.worker_handoff_hash,
        require_current_head=require_current_head,
    )
    if (
        binding.team_plan_hash != handoff.team_plan_hash
        or binding.panel_hash != handoff.panel_hash
        or binding.synthesis_hash != handoff.synthesis_hash
        or binding.panel_hash != sha256_digest(canonical_json_bytes(panel))
        or binding.synthesis_hash != sha256_digest(canonical_json_bytes(synthesis))
    ):
        raise OperationalError("worker completion binding differs from its handoff")
    authorization = read_framing_team_delivery_authorization(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        team_plan_hash=binding.team_plan_hash,
        require_current_head=require_current_head,
    )
    if (
        binding.delivery_envelope_hash
        != authorization.source_delivery_envelope_hash
    ):
        raise OperationalError(
            "worker completion binding delivery differs from authorization"
        )
    activation = read_framing_worker_activation(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        handoff_hash=binding.worker_handoff_hash,
        require_current_head=require_current_head,
    )
    if (
        binding.worker_activation_hash
        != sha256_digest(canonical_json_bytes(activation))
        or binding.worker_agent_label != activation.worker_agent_label
        or binding.worker_model_observation != activation.worker_model_observation
        or binding.delivery_envelope_hash != activation.delivery_envelope_hash
    ):
        raise OperationalError("worker completion binding differs from activation")
    return binding


def framing_worker_completion_binding_exists(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    completion_operation_key: str,
    require_current_head: bool = True,
) -> bool:
    """Probe one exact binding while still validating any present record."""

    store = _team_store(operational, route_run_id)
    path = store.root / _completion_binding_filename(completion_operation_key)
    if not path_entry_exists(path):
        return False
    read_framing_worker_completion_binding(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        completion_operation_key=completion_operation_key,
        require_current_head=require_current_head,
    )
    return True


__all__ = [
    "FramingAdvisoryLaneId",
    "FramingChoiceReviewV1",
    "FramingChoiceSourceV1",
    "FramingDirectionCardV1",
    "FramingDisposition",
    "FramingLaneOutputV1",
    "FramingResearcherSynthesisV1",
    "FramingSourceAwareSelectionBindingV1",
    "FramingTeamDeliveryAuthorizationV1",
    "FramingTeamPanelV1",
    "FramingTeamPlanV1",
    "FramingTeamStopV1",
    "FramingTeamStopStatus",
    "FramingTeamTerminalOutcomeV1",
    "FramingTeamTerminalStatus",
    "FramingTeamLaneId",
    "FramingWorkerActivationV1",
    "FramingWorkerCompletionBindingV1",
    "FramingWorkerHandoffV1",
    "build_framing_lane_output",
    "build_framing_choice_review",
    "build_framing_researcher_synthesis",
    "build_framing_team_delivery_authorization",
    "build_framing_team_stop",
    "framing_choice_review_required",
    "framing_lane_input_hash",
    "framing_worker_activation_exists",
    "framing_worker_completion_binding_exists",
    "framing_team_is_active",
    "open_framing_team_plan",
    "publish_framing_choice_review",
    "publish_framing_researcher_synthesis",
    "publish_framing_source_aware_selection_binding",
    "publish_framing_team_stop",
    "publish_framing_team_panel",
    "publish_framing_worker_completion_binding",
    "publish_framing_worker_handoff",
    "read_framing_choice_review",
    "read_framing_source_aware_selection_binding",
    "read_framing_worker_completion_binding",
    "read_framing_worker_activation",
    "read_framing_worker_inputs",
    "read_framing_team_panel",
    "read_framing_team_plan",
    "read_framing_team_delivery_authorization",
]
