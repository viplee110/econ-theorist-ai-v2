"""Noncanonical Phase 5B.0 research-team sidecars for framing.

The module declares and records advisory lanes around one immutable
``frame.question_and_benchmarks`` WorkPacket.  It does not call a model,
construct a scientific candidate, confirm a human Decision, or write canonical
state.  The existing single worker and ``candidate.complete`` path remain the
only route to a canonical commit.
"""

from __future__ import annotations

from typing import Literal, TypeVar

from pydantic import model_validator

from .codec import canonical_json_bytes, sha256_digest
from .machine.models import WorkPacketV1
from .machine.operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
)
from .machine.packets import read_work_packet
from .models import Digest, NonEmptyString, StableId, StrictModel
from .runtime.layout import StoreLayout
from .runtime.replay import replay


FramingAdvisoryLaneId = Literal[
    "mentor",
    "collaborator_a",
    "collaborator_b",
]
FramingDisposition = Literal["continue", "simplify", "pivot", "park", "kill"]

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


class FramingTeamPlanV1(_FramingPacketBoundV1):
    plan_schema: Literal["econ-theorist/framing-team-plan/v1"] = (
        "econ-theorist/framing-team-plan/v1"
    )
    execution_mode: Literal["isolated_multi_agent", "sequential_single_model"]
    isolation_claim: Literal["logical", "host_enforced"]
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


def _load_current_framing_packet(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
) -> WorkPacketV1:
    packet = read_work_packet(operational, route_run_id, work_packet_hash)
    if sha256_digest(canonical_json_bytes(packet)) != work_packet_hash:
        raise OperationalError("framing team WorkPacket hash is invalid")
    if packet.route_id != _FRAMING_ROUTE_ID:
        raise OperationalError("Phase 5B.0 accepts only the framing route")
    snapshot = replay(StoreLayout.from_store_root(operational.store_root))
    if snapshot.project_id != packet.project_id:
        raise OperationalError("framing team project binding is stale")
    if snapshot.head != packet.base_head:
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
    plan = FramingTeamPlanV1(
        **_packet_binding(packet, work_packet_hash),
        execution_mode=execution_mode,
        isolation_claim=isolation_claim,
        role_overlays=dict(_ROLE_OVERLAYS),
    )
    return _team_store(operational, route_run_id).install(
        "framing-team-plans", plan
    )[0], plan


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
    plan = _read_record(
        store, "framing-team-plans", team_plan_hash, FramingTeamPlanV1
    )
    _require_binding(plan, packet, work_packet_hash, label="framing team plan")
    for output in (mentor, *collaborators):
        _require_binding(output, packet, work_packet_hash, label="framing lane output")
        if output.team_plan_hash != team_plan_hash:
            raise OperationalError("framing lane output references a different plan")
        expected_input = framing_lane_input_hash(plan, team_plan_hash, output.lane_id)
        if output.lane_input_hash != expected_input:
            raise OperationalError("framing lane input binding is invalid")
        store.install("framing-lane-outputs", output)
    panel = FramingTeamPanelV1(
        **_packet_binding(packet, work_packet_hash),
        team_plan_hash=team_plan_hash,
        mentor=mentor,
        collaborators=collaborators,
    )
    panel_hash, _ = store.install("framing-team-panels", panel)
    return panel_hash, panel


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
    plan = _read_record(
        store,
        "framing-team-plans",
        panel.team_plan_hash,
        FramingTeamPlanV1,
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
    synthesis_hash, _ = store.install("framing-team-syntheses", synthesis)
    return synthesis_hash, synthesis


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
    handoff_hash, _ = store.install("framing-team-handoffs", handoff)
    return handoff_hash, handoff


def read_framing_worker_inputs(
    operational: ProjectOperationalLayout,
    *,
    route_run_id: str,
    work_packet_hash: str,
    handoff_hash: str,
) -> tuple[
    WorkPacketV1,
    FramingTeamPanelV1,
    FramingResearcherSynthesisV1,
    FramingWorkerHandoffV1,
]:
    """Read and revalidate the complete bounded input for the one worker."""

    packet = _load_current_framing_packet(
        operational,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
    )
    store = _team_store(operational, route_run_id)
    handoff = _read_record(
        store, "framing-team-handoffs", handoff_hash, FramingWorkerHandoffV1
    )
    panel = _read_record(
        store, "framing-team-panels", handoff.panel_hash, FramingTeamPanelV1
    )
    plan = _read_record(
        store,
        "framing-team-plans",
        handoff.team_plan_hash,
        FramingTeamPlanV1,
    )
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
    return packet, panel, synthesis, handoff


__all__ = [
    "FramingLaneOutputV1",
    "FramingResearcherSynthesisV1",
    "FramingTeamPanelV1",
    "FramingTeamPlanV1",
    "FramingWorkerHandoffV1",
    "build_framing_lane_output",
    "build_framing_researcher_synthesis",
    "framing_lane_input_hash",
    "open_framing_team_plan",
    "publish_framing_researcher_synthesis",
    "publish_framing_team_panel",
    "publish_framing_worker_handoff",
    "read_framing_worker_inputs",
]
