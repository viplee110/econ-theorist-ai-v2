"""Thin engine-owned bridge between Codex and the machine protocol.

The bridge deliberately contains no scientific route rules and does not
compile prose into canonical state.  It only composes existing machine
operations, returns the exact WorkPacket to Codex, and later validates the
canonical Transaction that Codex wrote for that packet.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field, TypeAdapter, model_serializer, model_validator

from .candidate_contract import (
    CandidateAuthoringContractV1,
    candidate_authoring_contract_hash,
    compile_candidate_authoring_contract,
)
from .codec import canonical_json_bytes, sha256_digest
from .errors import RuntimeStoreError
from .framing_team import (
    FramingAdvisoryLaneId,
    FramingDisposition,
    FramingResearcherSynthesisV1,
    FramingTeamPanelV1,
    FramingTeamPlanV1,
    FramingTeamStopV1,
    FramingWorkerHandoffV1,
    build_framing_lane_output,
    build_framing_researcher_synthesis,
    build_framing_team_delivery_authorization,
    build_framing_team_stop,
    framing_team_is_active,
    framing_worker_activation_exists,
    framing_worker_completion_binding_exists,
    open_framing_team_plan,
    publish_framing_researcher_synthesis,
    publish_framing_team_panel,
    publish_framing_team_stop,
    publish_framing_worker_completion_binding,
    publish_framing_worker_handoff,
    read_framing_team_panel,
    read_framing_team_delivery_authorization,
    read_framing_team_plan,
    read_framing_worker_activation,
    read_framing_worker_inputs,
)
from .ids import utc_now
from .models import Actor, Digest, EntityVersionRef, StableId, StrictModel
from .machine.dispatcher import (
    MachineDispatcher,
    TrustedHostCompletionObservation,
    TrustedHostDeliverySession,
)
from .machine.completion import (
    CandidateTransactionValidationError,
    CompletionError,
    candidate_source_digest,
)
from .machine.disposition import (
    assert_run_not_disposed,
    dispose_run_for_reframe,
    read_reframe_bridge_result_bytes,
    read_run_reframe_disposition,
    recoverable_reframe_successor,
    write_reframe_bridge_result_bytes,
)
from .machine.models import (
    CandidateCompletionResultV1,
    CapabilityReceiptV1,
    CapabilityV1,
    DeliveryEnvelopeV1,
    DiagnosticV1,
    DiscoveryGrantV1,
    EgressPlanV1,
    MachineRequestV1,
    MachineResponseV1,
    NavigationCandidateV1,
    NonEmpty,
    ReceiptToken,
    RunInputBriefV1,
    WorkPacketV1,
)
from .machine.operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
)
from .machine.navigation import enumerate_navigation_candidates
from .machine.packets import read_work_packet
from .runtime import StoreLayout
from .runtime.lock import ExclusiveFileLock
from .runtime.replay import replay
from .staging import StagingError, read_staged_transaction


CODEX_HOST_PRODUCT = "OpenAI Codex"
CODEX_HOST_VERSION = "phase5a2-pilot"
CODEX_ADAPTER_ID = "econ-theorist.codex.phase5a2"
CODEX_ADAPTER_VERSION = "1"
CODEX_PROVIDER = "openai"
_CODEX_SCIENTIFIC_AGENT = Actor(kind="agent", actor_id="scientific_agent")

CodexBridgeOperation: TypeAlias = Literal[
    "start_or_resume",
    "reframe.repair",
    "complete",
    "finish",
    "framing_team.open",
    "framing_team.publish_panel",
    "framing_team.apply_user_turn",
]
CodexBridgeOutcome: TypeAlias = Literal[
    "ready",
    "team_ready",
    "single_fallback",
    "awaiting_user_choice",
    "handoff_ready",
    "awaiting_clarification",
    "new_brief_required",
    "parked",
    "killed",
    "stale_team_session",
    "staged",
    "committed",
    "stale_base",
    "recorded_failure",
    "complete",
    "blocked",
    "human_decision_required",
    "ambiguous_next",
    "conflict",
    "error",
]


class CodexSessionV1(StrictModel):
    """Codex session facts relayed by the thin repository skill."""

    session_schema: Literal["econ-theorist/codex-session/v1"] = (
        "econ-theorist/codex-session/v1"
    )
    session_id: NonEmpty
    selected_model: NonEmpty
    installed_models: tuple[NonEmpty, ...]
    observed_at: NonEmpty

    @model_validator(mode="after")
    def _selected_model_is_installed(self) -> "CodexSessionV1":
        if not self.installed_models:
            raise ValueError("Codex must report at least one installed model")
        if len(set(self.installed_models)) != len(self.installed_models):
            raise ValueError("installed Codex models must be unique")
        if self.selected_model not in self.installed_models:
            raise ValueError("selected Codex model is not in installed_models")
        return self


class CodexFramingWorkerObservationV1(StrictModel):
    """Observable worker identity attached to a declared team completion."""

    observation_schema: Literal[
        "econ-theorist/codex-framing-worker-observation/v1"
    ] = "econ-theorist/codex-framing-worker-observation/v1"
    lane_id: Literal["research_worker"] = "research_worker"
    agent_label: StableId
    model_observation: NonEmpty


class CodexStartRequestV1(StrictModel):
    bridge_request_schema: Literal[
        "econ-theorist/codex-start-request/v1"
    ] = "econ-theorist/codex-start-request/v1"
    bridge_version: Literal[1] = 1
    operation: Literal["start_or_resume"] = "start_or_resume"
    project_root: NonEmpty
    initialize: bool = False
    project_name: NonEmpty | None = None
    requested_scope: NonEmpty | None = Field(
        default=None,
        description=(
            "Initial framing or an explicitly requested reframe only. Omit for "
            "ordinary continuation so the engine can select the next route."
        ),
    )
    framing_intent: NonEmpty | None = Field(
        default=None,
        description=(
            "Initial framing or an explicitly requested reframe only; provide "
            "together with requested_scope and omit for ordinary continuation."
        ),
    )
    requested_route_id: StableId | None = Field(
        default=None,
        description=(
            "One explicit route choice after ambiguous_next. Omit for ordinary "
            "automatic continuation and for frame/reframe requests."
        ),
    )
    profile_request: NonEmpty | None = None
    budget_units: Annotated[int, Field(ge=1)] | None = None
    session: CodexSessionV1

    @model_validator(mode="after")
    def _initialization_and_framing_inputs_are_explicit(self) -> "CodexStartRequestV1":
        if self.initialize and self.project_name is None:
            raise ValueError("project_name is required when initialize is true")
        if (self.requested_scope is None) != (self.framing_intent is None):
            raise ValueError(
                "requested_scope and framing_intent must be provided together"
            )
        if self.requested_route_id is not None and self.requested_scope is not None:
            raise ValueError(
                "requested_route_id cannot be combined with a frame/reframe brief"
            )
        return self


class CodexCompleteRequestV1(StrictModel):
    bridge_request_schema: Literal[
        "econ-theorist/codex-complete-request/v1"
    ] = "econ-theorist/codex-complete-request/v1"
    bridge_version: Literal[1] = 1
    operation: Literal["complete"] = "complete"
    project_root: NonEmpty
    route_run_id: NonEmpty
    work_packet_hash: Digest
    delivery_envelope_hash: Digest
    framing_team_handoff_hash: Digest | None = None
    framing_team_worker: CodexFramingWorkerObservationV1 | None = None
    expected_candidate_digest: Digest | None = None
    transaction_path: NonEmpty | None = None
    artifacts: dict[NonEmpty, NonEmpty] = Field(default_factory=dict)
    action: Literal[
        "stage_only", "commit_staged", "stage_and_commit"
    ] = "stage_and_commit"

    @model_validator(mode="after")
    def _staged_commit_keeps_an_exact_identity(self) -> "CodexCompleteRequestV1":
        if self.action == "commit_staged" and self.expected_candidate_digest is None:
            raise ValueError(
                "commit_staged requires the exact staged candidate digest"
            )
        if (self.framing_team_handoff_hash is None) != (
            self.framing_team_worker is None
        ):
            raise ValueError(
                "framing team handoff and worker observation must be provided together"
            )
        return self


class CodexFinishRequestV1(StrictModel):
    """Record an honest host-session stop without abandoning the route."""

    bridge_request_schema: Literal[
        "econ-theorist/codex-finish-request/v1"
    ] = "econ-theorist/codex-finish-request/v1"
    bridge_version: Literal[1] = 1
    operation: Literal["finish"] = "finish"
    project_root: NonEmpty
    route_run_id: NonEmpty
    work_packet_hash: Digest
    delivery_envelope_hash: Digest
    expected_candidate_digest: Digest | None = None
    completion_status: Literal[
        "failed_no_effect",
        "failed_terminal",
        "cancelled",
        "unknown_possible_effect",
    ]
    warnings: tuple[ReceiptToken, ...] = ()


class CodexFramingTeamCapabilityV1(StrictModel):
    """Observable Codex host facts needed by the bounded team surface."""

    capability_schema: Literal[
        "econ-theorist/codex-framing-team-capability/v1"
    ] = "econ-theorist/codex-framing-team-capability/v1"
    team_surface: Literal["available", "unavailable"]
    lane_separation: Literal["logical", "unavailable"]
    direct_user_capture: Literal["current_user_turn", "unavailable"]
    fallback_reason: NonEmpty | None = None

    @property
    def available(self) -> bool:
        return (
            self.team_surface == "available"
            and self.lane_separation == "logical"
            and self.direct_user_capture == "current_user_turn"
        )

    @model_validator(mode="after")
    def _fallback_is_explicit(self) -> "CodexFramingTeamCapabilityV1":
        if self.available and self.fallback_reason is not None:
            raise ValueError("available framing-team capability cannot claim fallback")
        if not self.available and self.fallback_reason is None:
            raise ValueError("unavailable framing-team capability requires fallback_reason")
        return self


class _CodexFramingTeamDeliveryRequestV1(StrictModel):
    bridge_version: Literal[1] = 1
    project_root: NonEmpty
    route_run_id: NonEmpty
    work_packet_hash: Digest
    delivery_envelope_hash: Digest


class CodexFramingTeamOpenRequestV1(_CodexFramingTeamDeliveryRequestV1):
    bridge_request_schema: Literal[
        "econ-theorist/codex-framing-team-open-request/v1"
    ] = "econ-theorist/codex-framing-team-open-request/v1"
    operation: Literal["framing_team.open"] = "framing_team.open"
    session: CodexSessionV1
    capability: CodexFramingTeamCapabilityV1


class CodexFramingLaneDraftV1(StrictModel):
    """Free-text host output; the bridge supplies every authoritative binding."""

    agent_label: NonEmpty
    model_observation: NonEmpty | None = None
    content_markdown: NonEmpty


class CodexFramingTeamPanelRequestV1(_CodexFramingTeamDeliveryRequestV1):
    bridge_request_schema: Literal[
        "econ-theorist/codex-framing-team-panel-request/v1"
    ] = "econ-theorist/codex-framing-team-panel-request/v1"
    operation: Literal[
        "framing_team.publish_panel"
    ] = "framing_team.publish_panel"
    team_plan_hash: Digest
    session: CodexSessionV1
    mentor: CodexFramingLaneDraftV1
    collaborator_a: CodexFramingLaneDraftV1
    collaborator_b: CodexFramingLaneDraftV1


class CodexDirectUserCaptureV1(StrictModel):
    capture_schema: Literal[
        "econ-theorist/codex-direct-user-capture/v1"
    ] = "econ-theorist/codex-direct-user-capture/v1"
    source: Literal["current_user_turn"] = "current_user_turn"
    session_id: NonEmpty
    researcher_id: StableId
    captured_at: NonEmpty
    text: NonEmpty


class CodexReframeRepairRequestV1(_CodexFramingTeamDeliveryRequestV1):
    """Replace one untouched framing run with one exact dependency repair."""

    bridge_request_schema: Literal[
        "econ-theorist/codex-reframe-repair-request/v1"
    ] = "econ-theorist/codex-reframe-repair-request/v1"
    operation: Literal["reframe.repair"] = "reframe.repair"
    requested_scope: NonEmpty
    framing_intent: NonEmpty
    repair_target_ref: EntityVersionRef
    profile_request: NonEmpty | None = None
    budget_units: Annotated[int, Field(ge=1)] | None = None
    session: CodexSessionV1
    capture: CodexDirectUserCaptureV1

    @model_validator(mode="after")
    def _capture_belongs_to_current_session(self) -> "CodexReframeRepairRequestV1":
        if self.capture.session_id != self.session.session_id:
            raise ValueError("direct user capture belongs to a different Codex session")
        return self


class CodexFramingClearInterpretationV1(StrictModel):
    status: Literal["clear_within_packet"] = "clear_within_packet"
    disposition: FramingDisposition
    selected_lane_ids: tuple[FramingAdvisoryLaneId, ...] = ()
    synthesis_markdown: NonEmpty
    worker_brief: NonEmpty | None = None

    @model_validator(mode="after")
    def _active_direction_has_one_worker_brief(
        self,
    ) -> "CodexFramingClearInterpretationV1":
        if len(set(self.selected_lane_ids)) != len(self.selected_lane_ids):
            raise ValueError("selected framing lane ids must be unique")
        if self.disposition in {"continue", "simplify", "pivot"}:
            if self.worker_brief is None:
                raise ValueError("active framing direction requires worker_brief")
        elif self.worker_brief is not None:
            raise ValueError("park or kill cannot carry worker_brief")
        return self


class CodexFramingAmbiguousInterpretationV1(StrictModel):
    status: Literal["awaiting_clarification"] = "awaiting_clarification"
    clarification_question: NonEmpty


class CodexFramingNewBriefInterpretationV1(StrictModel):
    status: Literal["new_brief_required"] = "new_brief_required"
    reason: NonEmpty


CodexFramingUserInterpretation: TypeAlias = Annotated[
    CodexFramingClearInterpretationV1
    | CodexFramingAmbiguousInterpretationV1
    | CodexFramingNewBriefInterpretationV1,
    Field(discriminator="status"),
]


class CodexFramingTeamUserTurnRequestV1(_CodexFramingTeamDeliveryRequestV1):
    bridge_request_schema: Literal[
        "econ-theorist/codex-framing-team-user-turn-request/v1"
    ] = "econ-theorist/codex-framing-team-user-turn-request/v1"
    operation: Literal[
        "framing_team.apply_user_turn"
    ] = "framing_team.apply_user_turn"
    panel_hash: Digest
    session: CodexSessionV1
    capture: CodexDirectUserCaptureV1
    interpretation: CodexFramingUserInterpretation

    @model_validator(mode="after")
    def _capture_belongs_to_current_session(
        self,
    ) -> "CodexFramingTeamUserTurnRequestV1":
        if self.capture.session_id != self.session.session_id:
            raise ValueError("direct user capture belongs to a different Codex session")
        return self


CodexFramingTeamStatus: TypeAlias = Literal[
    "team_ready",
    "single_fallback",
    "awaiting_user_choice",
    "handoff_ready",
    "awaiting_clarification",
    "new_brief_required",
    "parked",
    "killed",
    "stale_team_session",
]


class CodexFramingTeamResultV1(StrictModel):
    """Self-contained noncanonical result for one bounded team transition."""

    result_schema: Literal[
        "econ-theorist/codex-framing-team-result/v1"
    ] = "econ-theorist/codex-framing-team-result/v1"
    status: CodexFramingTeamStatus
    capability: CodexFramingTeamCapabilityV1 | None = None
    reason: NonEmpty | None = None
    team_plan_hash: Digest | None = None
    team_plan: FramingTeamPlanV1 | None = None
    panel_hash: Digest | None = None
    panel: FramingTeamPanelV1 | None = None
    synthesis_hash: Digest | None = None
    synthesis: FramingResearcherSynthesisV1 | None = None
    handoff_hash: Digest | None = None
    handoff: FramingWorkerHandoffV1 | None = None
    stop_hash: Digest | None = None
    stop: FramingTeamStopV1 | None = None

    @model_validator(mode="after")
    def _payload_matches_status(self) -> "CodexFramingTeamResultV1":
        pairs = (
            ("team plan", self.team_plan_hash, self.team_plan),
            ("panel", self.panel_hash, self.panel),
            ("synthesis", self.synthesis_hash, self.synthesis),
            ("handoff", self.handoff_hash, self.handoff),
            ("stop", self.stop_hash, self.stop),
        )
        present: set[str] = set()
        for label, digest, value in pairs:
            if (digest is None) != (value is None):
                raise ValueError(f"framing-team {label} hash and value must be paired")
            if digest is not None and value is not None:
                if sha256_digest(canonical_json_bytes(value)) != digest:
                    raise ValueError(f"framing-team {label} digest is invalid")
                present.add(label)
        required: dict[str, set[str]] = {
            "team_ready": {"team plan"},
            "single_fallback": set(),
            "awaiting_user_choice": {"team plan", "panel"},
            "handoff_ready": {"team plan", "panel", "synthesis", "handoff"},
            "awaiting_clarification": {"team plan", "panel", "stop"},
            "new_brief_required": {"team plan", "panel", "stop"},
            "parked": {"team plan", "panel", "synthesis"},
            "killed": {"team plan", "panel", "synthesis"},
            "stale_team_session": set(),
        }
        if present != required[self.status]:
            raise ValueError("framing-team result records do not match its status")
        if self.status in {"single_fallback", "stale_team_session"}:
            if self.reason is None:
                raise ValueError(f"{self.status} requires a reason")
        if self.status == "single_fallback":
            if self.capability is None or self.capability.available:
                raise ValueError("single_fallback requires unavailable capability facts")
        elif self.status == "team_ready":
            if self.capability is None or not self.capability.available:
                raise ValueError("team_ready requires available capability facts")
        elif self.capability is not None:
            raise ValueError("capability facts belong only to team open results")
        if self.stop is not None and self.stop.status != self.status:
            raise ValueError("framing-team stop status differs from the result")
        if self.synthesis is not None:
            expected = (
                "parked"
                if self.synthesis.disposition == "park"
                else "killed"
                if self.synthesis.disposition == "kill"
                else "handoff_ready"
            )
            if self.status != expected:
                raise ValueError("researcher disposition differs from team result")
        return self


CodexBridgeRequestValue: TypeAlias = (
    CodexStartRequestV1
    | CodexReframeRepairRequestV1
    | CodexCompleteRequestV1
    | CodexFinishRequestV1
    | CodexFramingTeamOpenRequestV1
    | CodexFramingTeamPanelRequestV1
    | CodexFramingTeamUserTurnRequestV1
)
CodexBridgeRequest: TypeAlias = Annotated[
    CodexBridgeRequestValue,
    Field(discriminator="operation"),
]
CODEX_BRIDGE_REQUEST_ADAPTER = TypeAdapter(CodexBridgeRequest)


class CodexBridgeResponseV1(StrictModel):
    bridge_response_schema: Literal[
        "econ-theorist/codex-bridge-response/v1"
    ] = "econ-theorist/codex-bridge-response/v1"
    bridge_version: Literal[1] = 1
    operation: CodexBridgeOperation
    request_digest: Digest
    outcome: CodexBridgeOutcome
    mutated: bool
    project_id: NonEmpty | None = None
    head: Digest | None = None
    route_run_id: NonEmpty | None = None
    work_packet_hash: Digest | None = None
    delivery_envelope_hash: Digest | None = None
    candidate_logical_path: NonEmpty | None = None
    work_packet: WorkPacketV1 | None = None
    candidate_authoring_contract_hash: Digest | None = None
    candidate_authoring_contract: CandidateAuthoringContractV1 | None = None
    framing_team: CodexFramingTeamResultV1 | None = None
    completion: CandidateCompletionResultV1 | None = None
    diagnostics: tuple[DiagnosticV1, ...] = ()

    @model_serializer(mode="wrap")
    def _preserve_absent_additive_fields(self, handler: Any) -> Any:
        """Keep pre-team response bytes stable when the field was absent."""

        data = handler(self)
        if "framing_team" not in self.model_fields_set:
            data.pop("framing_team", None)
        return data

    @model_validator(mode="after")
    def _outcome_payload_is_complete(self) -> "CodexBridgeResponseV1":
        packet_bound_outcomes = {
            "ready",
            "team_ready",
            "single_fallback",
            "awaiting_user_choice",
            "handoff_ready",
            "awaiting_clarification",
            "new_brief_required",
            "parked",
            "killed",
        }
        if self.outcome in packet_bound_outcomes and any(
            value is None
            for value in (
                self.route_run_id,
                self.work_packet_hash,
                self.delivery_envelope_hash,
                self.candidate_logical_path,
                self.work_packet,
                self.candidate_authoring_contract_hash,
                self.candidate_authoring_contract,
            )
        ):
            raise ValueError("ready Codex responses require the exact WorkPacket binding")
        if self.outcome in packet_bound_outcomes:
            assert self.work_packet_hash is not None
            assert self.candidate_logical_path is not None
            assert self.work_packet is not None
            assert self.candidate_authoring_contract_hash is not None
            assert self.candidate_authoring_contract is not None
            contract = self.candidate_authoring_contract
            packet = self.work_packet
            if (
                sha256_digest(canonical_json_bytes(packet)) != self.work_packet_hash
                or contract.work_packet_hash != self.work_packet_hash
                or contract.transaction_bindings.project_id != packet.project_id
                or contract.transaction_bindings.base_revision != packet.base_head
                or contract.transaction_bindings.route_run_id != packet.route_run_id
                or contract.transaction_bindings.route_id != packet.route_id
                or contract.transaction_bindings.route_run_hash != packet.route_run_hash
                or contract.transaction_bindings.context_manifest_hash
                != packet.context_manifest_hash
                or contract.transaction_bindings.compiled_context_hash
                != packet.compiled_context_hash
                or contract.output_locations.candidate_logical_path
                != self.candidate_logical_path
                or self.project_id != packet.project_id
                or self.head != packet.base_head
                or self.route_run_id != packet.route_run_id
                or candidate_authoring_contract_hash(contract)
                != self.candidate_authoring_contract_hash
            ):
                raise ValueError(
                    "packet-bound Codex response has a mismatched candidate authoring contract"
                )
        team_outcomes = {
            "team_ready",
            "single_fallback",
            "awaiting_user_choice",
            "handoff_ready",
            "awaiting_clarification",
            "new_brief_required",
            "parked",
            "killed",
            "stale_team_session",
        }
        if self.outcome in team_outcomes:
            if self.framing_team is None or self.framing_team.status != self.outcome:
                raise ValueError("team outcome requires the matching framing-team result")
        elif self.framing_team is not None:
            raise ValueError("non-team response cannot carry a framing-team result")
        if self.outcome in {
            "staged",
            "committed",
            "stale_base",
            "recorded_failure",
        } and (
            self.completion is None
        ):
            raise ValueError("completion outcomes require a completion result")
        if self.outcome == "recorded_failure":
            assert self.completion is not None
            if self.completion.status != "recorded_failure":
                raise ValueError(
                    "recorded_failure responses require a recorded host failure"
                )
        return self


def codex_bridge_schema(kind: Literal["request", "response", "bundle"]) -> dict[str, Any]:
    """Return the authoritative bridge schema without duplicating fields in a skill."""

    request_schema = CODEX_BRIDGE_REQUEST_ADAPTER.json_schema(mode="validation")
    response_schema = CodexBridgeResponseV1.model_json_schema(mode="validation")
    if kind == "request":
        return request_schema
    if kind == "response":
        return response_schema
    if kind == "bundle":
        return {
            "schema_bundle": "econ-theorist/codex-bridge-schema-bundle/v1",
            "request": request_schema,
            "response": response_schema,
        }
    raise ValueError(f"unknown Codex bridge schema kind: {kind}")


def _operation_key(step: str, payload: Any) -> str:
    digest = sha256_digest(canonical_json_bytes(payload))
    return f"codex.{step}.{digest[:48]}"


def _request_digest(request: CodexBridgeRequestValue) -> str:
    return sha256_digest(canonical_json_bytes(request))


def _has_active_staged_candidate(root: Path, route_run_id: str) -> bool:
    try:
        read_staged_transaction(StoreLayout.at(root), route_run_id)
    except StagingError as exc:
        if str(exc) == "run has no active staged candidate":
            return False
        raise
    return True


def _diagnostic(code: str, message: str) -> DiagnosticV1:
    return DiagnosticV1(code=code, severity="error", message=message)


def _grant(root: Path) -> DiscoveryGrantV1:
    value = str(root)
    return DiscoveryGrantV1(
        selected_root=value,
        allowed_discovery_roots=(value,),
        ancestor_check_boundary=value,
        stable_workspace_root=value,
    )


def _machine_request(
    root: Path,
    grant: DiscoveryGrantV1,
    operation: str,
    *,
    operation_key: str | None = None,
    parameters: dict[str, Any] | None = None,
) -> MachineRequestV1:
    return MachineRequestV1(
        operation=operation,  # type: ignore[arg-type]
        operation_key=operation_key,
        project_root=str(root),
        discovery_grant=grant,
        parameters=parameters or {},
    )


def _capability(request: CodexStartRequestV1, root: Path) -> CapabilityReceiptV1:
    """Build one honest provider-backed public-pilot capability receipt."""

    return CapabilityReceiptV1(
        host_product=CODEX_HOST_PRODUCT,
        host_version=CODEX_HOST_VERSION,
        adapter_id=CODEX_ADAPTER_ID,
        adapter_version=CODEX_ADAPTER_VERSION,
        execution_class="provider_backed",
        technically_accessible_roots=(str(root),),
        model_tool_isolation="unverified",
        trusted_human_channel="unavailable",
        environment_redaction="unavailable",
        credential_store_isolation="unavailable",
        secret_file_denial="unavailable",
        shadow_workspace_isolation="unavailable",
        capabilities=tuple(
            CapabilityV1(
                capability_id=identifier,
                available=True,
                required=True,
                evidence="Codex Phase 5A.2 public-only bridge",
            )
            for identifier in (
                "python_runtime",
                "structured_process_invocation",
                "single_agent_topology",
            )
        ),
        observed_at=request.session.observed_at,
    )


def _public_pilot_blocker(packet: WorkPacketV1) -> DiagnosticV1 | None:
    labels = {packet.privacy_clearance}
    if packet.run_input is not None:
        labels.add(packet.run_input.privacy)
    if labels != {"public"} or packet.hidden_compartments:
        return _diagnostic(
            "codex_public_pilot_only",
            "Phase 5A.2 Codex delivery accepts only public WorkPackets with no hidden compartments",
        )
    return None


def _canonical_project_is_public(root: Path, project_id: str) -> bool:
    snapshot = replay(StoreLayout.at(root))
    version = snapshot.current_entities.get(project_id)
    matches = tuple(
        entity
        for entity in snapshot.entity_versions
        if entity.entity_id == project_id and entity.version == version
    )
    return (
        len(matches) == 1
        and matches[0].entity_type == "Project"
        and matches[0].privacy == "public"
    )


def _read_provider_delivery(
    root: Path,
    *,
    route_run_id: str,
    work_packet_hash: str,
    delivery_envelope_hash: str,
    expected_operation_key: str | None = None,
) -> tuple[DeliveryEnvelopeV1, EgressPlanV1, WorkPacketV1]:
    """Recover and verify one immutable Codex public delivery binding."""

    layout = StoreLayout.at(root)
    operational = ProjectOperationalLayout.at(layout)
    store = ContentAddressedOperationalStore(
        operational.project_root, operational.runs / route_run_id
    )
    envelope_bytes = store.read_bytes("envelopes", delivery_envelope_hash)
    envelope = DeliveryEnvelopeV1.model_validate_json(envelope_bytes, strict=True)
    if canonical_json_bytes(envelope) != envelope_bytes:
        raise ValueError("Codex delivery envelope is not canonical JSON")
    if (
        envelope.work_packet_hash != work_packet_hash
        or envelope.egress_plan_hash is None
        or envelope.pre_delivery_status != "authorized_to_deliver"
        or envelope.host_product != CODEX_HOST_PRODUCT
        or envelope.host_version != CODEX_HOST_VERSION
        or envelope.adapter_id != CODEX_ADAPTER_ID
        or envelope.adapter_version != CODEX_ADAPTER_VERSION
        or (
            expected_operation_key is not None
            and envelope.operation_key != expected_operation_key
        )
    ):
        raise ValueError("delivery envelope differs from the exact Codex invocation")
    plan_bytes = store.read_bytes("egress-plans", envelope.egress_plan_hash)
    plan = EgressPlanV1.model_validate_json(plan_bytes, strict=True)
    if canonical_json_bytes(plan) != plan_bytes:
        raise ValueError("Codex egress plan is not canonical JSON")
    if (
        plan.work_packet_hash != work_packet_hash
        or plan.host_product != envelope.host_product
        or plan.host_version != envelope.host_version
        or plan.adapter_id != envelope.adapter_id
        or plan.adapter_version != envelope.adapter_version
        or plan.provider != CODEX_PROVIDER
        or plan.execution_class != "provider_backed"
        or plan.authorization_required
        or envelope.egress_authorization_hash is not None
        or plan.hidden_compartments
        or set(plan.privacy_labels) != {"public"}
    ):
        raise ValueError("immutable egress plan is not a public Codex delivery")
    packet = read_work_packet(operational, route_run_id, work_packet_hash)
    blocker = _public_pilot_blocker(packet)
    if blocker is not None:
        raise ValueError(blocker.message)
    return envelope, plan, packet


def _read_framing_team_delivery(
    root: Path,
    *,
    route_run_id: str,
    work_packet_hash: str,
    delivery_envelope_hash: str,
) -> tuple[DeliveryEnvelopeV1, EgressPlanV1, WorkPacketV1]:
    """Recover one live public framing packet without opening a team record."""

    envelope, plan, packet = _read_provider_delivery(
        root,
        route_run_id=route_run_id,
        work_packet_hash=work_packet_hash,
        delivery_envelope_hash=delivery_envelope_hash,
    )
    if packet.route_id != "frame.question_and_benchmarks":
        raise ValueError("Phase 5B.0 accepts only the framing route")
    snapshot = replay(StoreLayout.at(root))
    if snapshot.project_id != packet.project_id or snapshot.head != packet.base_head:
        raise OperationalError("framing team packet binding is stale")
    return envelope, plan, packet


def _framing_team_response(
    request: (
        CodexFramingTeamOpenRequestV1
        | CodexFramingTeamPanelRequestV1
        | CodexFramingTeamUserTurnRequestV1
    ),
    *,
    root: Path,
    packet: WorkPacketV1,
    result: CodexFramingTeamResultV1,
    mutated: bool,
) -> CodexBridgeResponseV1:
    """Return one self-contained team transition over the unchanged packet."""

    contract = compile_candidate_authoring_contract(
        StoreLayout.at(root), packet, request.work_packet_hash
    )
    return CodexBridgeResponseV1(
        operation=request.operation,
        request_digest=_request_digest(request),
        outcome=result.status,
        mutated=mutated,
        project_id=packet.project_id,
        head=packet.base_head,
        route_run_id=packet.route_run_id,
        work_packet_hash=request.work_packet_hash,
        delivery_envelope_hash=request.delivery_envelope_hash,
        candidate_logical_path=packet.candidate_logical_path,
        work_packet=packet,
        candidate_authoring_contract_hash=candidate_authoring_contract_hash(contract),
        candidate_authoring_contract=contract,
        framing_team=result,
    )


class CodexBridge:
    """Compose machine operations for one narrow public Codex pilot."""

    def __init__(
        self,
        *,
        trusted_clock: Callable[[], str] = utc_now,
        preproject_operational_home: str | Path | None = None,
    ) -> None:
        self._trusted_clock = trusted_clock
        self._preproject_operational_home = preproject_operational_home

    def invoke(
        self,
        request: CodexBridgeRequestValue,
    ) -> CodexBridgeResponseV1:
        try:
            if isinstance(request, CodexStartRequestV1):
                return self._start(request)
            if isinstance(request, CodexReframeRepairRequestV1):
                return self._reframe_repair(request)
            if isinstance(request, CodexCompleteRequestV1):
                return self._complete(request)
            if isinstance(request, CodexFinishRequestV1):
                return self._finish(request)
            if isinstance(request, CodexFramingTeamOpenRequestV1):
                return self._open_framing_team(request)
            if isinstance(request, CodexFramingTeamPanelRequestV1):
                return self._publish_framing_team_panel(request)
            return self._apply_framing_user_turn(request)
        except RuntimeStoreError as exc:
            message = str(exc) or type(exc).__name__
            if (
                isinstance(exc, OperationalError)
                and request.operation.startswith("framing_team.")
                and "stale" in message
            ):
                result = CodexFramingTeamResultV1(
                    status="stale_team_session",
                    reason=message,
                )
                return CodexBridgeResponseV1(
                    operation=request.operation,
                    request_digest=_request_digest(request),
                    outcome="stale_team_session",
                    mutated=False,
                    framing_team=result,
                    diagnostics=(
                        _diagnostic("codex_framing_team_stale", message),
                    ),
                )
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome="error",
                mutated=False,
                diagnostics=(
                    _diagnostic("codex_operational_integrity_error", message),
                ),
            )
        except (CompletionError, OSError, RuntimeError, ValueError) as exc:
            code = (
                "codex_completion_protocol_error"
                if isinstance(exc, CompletionError)
                else "codex_bridge_error"
            )
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome="error",
                mutated=False,
                diagnostics=(
                    _diagnostic(code, str(exc) or type(exc).__name__),
                ),
            )

    def _blocked_from_machine(
        self,
        request: CodexBridgeRequestValue,
        response: MachineResponseV1,
        *,
        mutated: bool,
        fallback_code: str,
    ) -> CodexBridgeResponseV1:
        diagnostics = response.diagnostics or (
            _diagnostic(fallback_code, f"machine operation {response.operation} did not complete"),
        )
        outcome: CodexBridgeOutcome
        if response.outcome == "human_decision_required":
            outcome = "human_decision_required"
        elif response.outcome == "ambiguous_next":
            outcome = "ambiguous_next"
        elif response.outcome == "conflict":
            outcome = "conflict"
        elif response.outcome == "error":
            outcome = "error"
        else:
            outcome = "blocked"
        return CodexBridgeResponseV1(
            operation=request.operation,
            request_digest=_request_digest(request),
            outcome=outcome,
            mutated=mutated or response.mutated,
            project_id=response.project_id,
            head=response.head,
            diagnostics=diagnostics,
        )

    def _reframe_repair(
        self, request: CodexReframeRepairRequestV1
    ) -> CodexBridgeResponseV1:
        """Dispose one untouched empty framing run and open its exact repair."""

        root = Path(request.project_root).resolve()
        if not root.is_dir():
            raise ValueError("Codex project_root must be an existing directory")
        layout = StoreLayout.at(root)
        operational = ProjectOperationalLayout.at(layout)
        request_digest = _request_digest(request)
        _, _, source_packet = _read_provider_delivery(
            root,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
        )
        existing = read_run_reframe_disposition(
            operational, request.route_run_id
        )
        if existing is None:
            snapshot = replay(layout)
            if (
                source_packet.project_id != snapshot.project_id
                or source_packet.base_head != snapshot.head
            ):
                raise ValueError(
                    "reframe source delivery is not bound to the current head"
                )
            successor_brief = RunInputBriefV1(
                project_id=snapshot.project_id,
                base_head=snapshot.head,
                requested_scope=request.requested_scope,
                framing_intent=request.framing_intent,
                privacy="public",
                compartments=("project_research",),
                actor_role="scientific_agent",
                profile_request=request.profile_request,
            )
            candidates, _ = enumerate_navigation_candidates(
                layout,
                snapshot,
                actor=_CODEX_SCIENTIFIC_AGENT,
                compartments=("project_research",),
                privacy_clearance="public",
                budget_units=request.budget_units,
                requested_route_ids=("repair.dependency",),
                run_input_brief=successor_brief,
            )
            matching = tuple(
                candidate
                for candidate in candidates
                if request.repair_target_ref in candidate.key.focus_refs
            )
            if len(matching) != 1:
                return CodexBridgeResponseV1(
                    operation=request.operation,
                    request_digest=request_digest,
                    outcome="blocked",
                    mutated=False,
                    project_id=snapshot.project_id,
                    head=snapshot.head,
                    diagnostics=(
                        _diagnostic(
                            "codex_reframe_candidate_not_unique",
                            "the exact requested dependency repair is unavailable or ambiguous",
                        ),
                    ),
                )
            successor_candidate = matching[0]
        else:
            successor_brief, successor_candidate = (
                recoverable_reframe_successor(existing)
            )
            if (
                source_packet.project_id != existing.project_id
                or source_packet.base_head != existing.head
            ):
                raise OperationalError(
                    "reframe source delivery differs from its disposition"
                )

        disposition_key = _operation_key(
            "dispose-for-reframe",
            {
                "request_digest": request_digest,
                "successor_run_input_brief": successor_brief.model_dump(
                    mode="json"
                ),
                "repair_target_ref": request.repair_target_ref.model_dump(
                    mode="json"
                ),
                "successor_navigation_candidate_digest": (
                    successor_candidate.candidate_digest
                ),
            },
        )
        disposition, disposition_mutated = dispose_run_for_reframe(
            layout,
            operational,
            operation_key=disposition_key,
            disposed_at=self._trusted_clock(),
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
            successor_run_input_brief=successor_brief,
            successor_candidate=successor_candidate,
            repair_target_ref=request.repair_target_ref,
            direct_user_capture_hash=sha256_digest(
                canonical_json_bytes(request.capture)
            ),
        )
        disposition_diagnostic = DiagnosticV1(
            code="reframe_disposition_bound",
            severity="info",
            message="the source run was durably disposed for this exact repair",
            details={
                "source_route_run_id": request.route_run_id,
                "disposition_hash": disposition.disposition_hash,
                "successor_navigation_candidate_digest": (
                    disposition.successor_navigation_candidate_digest
                ),
            },
        )

        start_request = CodexStartRequestV1(
            project_root=str(root),
            requested_scope=request.requested_scope,
            framing_intent=request.framing_intent,
            profile_request=request.profile_request,
            budget_units=request.budget_units,
            session=request.session,
        )
        # Exact retries replay the outcome of one composite operation.  Once
        # its durable disposition exists, the operation has mutated state even
        # when this particular recovery call did not create that file.  This
        # also prevents a post-open exception from hiding a newly published
        # successor run behind ``mutated=false``.
        reframe_mutated = True
        try:
            persisted_bytes = read_reframe_bridge_result_bytes(
                operational, request.route_run_id
            )
            if persisted_bytes is not None:
                persisted = CodexBridgeResponseV1.model_validate_json(
                    persisted_bytes, strict=True
                )
                if (
                    canonical_json_bytes(persisted) != persisted_bytes
                    or persisted.operation != request.operation
                    or persisted.request_digest != request_digest
                    or persisted.outcome != "ready"
                    or not persisted.mutated
                    or persisted.project_id != successor_brief.project_id
                    or persisted.head != successor_brief.base_head
                    or persisted.work_packet is None
                    or persisted.work_packet.route_id != "repair.dependency"
                    or persisted.work_packet.navigation_candidate_digest
                    != disposition.successor_navigation_candidate_digest
                    or request.repair_target_ref
                    not in persisted.work_packet.focus_refs
                    or disposition_diagnostic not in persisted.diagnostics
                ):
                    raise OperationalError(
                        "persisted reframe bridge result is invalid"
                    )
                assert persisted.route_run_id is not None
                assert persisted.work_packet_hash is not None
                assert persisted.delivery_envelope_hash is not None
                _, _, delivered_packet = _read_provider_delivery(
                    root,
                    route_run_id=persisted.route_run_id,
                    work_packet_hash=persisted.work_packet_hash,
                    delivery_envelope_hash=persisted.delivery_envelope_hash,
                )
                if delivered_packet != persisted.work_packet:
                    raise OperationalError(
                        "persisted reframe result differs from its delivery"
                    )
                return persisted

            response = self._start(
                start_request,
                requested_route_ids=("repair.dependency",),
                required_focus_ref=request.repair_target_ref,
                required_candidate_digest=(
                    disposition.successor_navigation_candidate_digest
                ),
                exact_brief=successor_brief,
            )
            reframe_mutated = reframe_mutated or response.mutated
            final_response = response.model_copy(
                update={
                    "operation": request.operation,
                    "request_digest": request_digest,
                    "mutated": reframe_mutated,
                    "diagnostics": (
                        *response.diagnostics,
                        disposition_diagnostic,
                    ),
                }
            )
            if final_response.outcome == "ready":
                final_response = final_response.model_copy(
                    update={"mutated": True}
                )
                write_reframe_bridge_result_bytes(
                    operational,
                    request.route_run_id,
                    canonical_json_bytes(final_response),
                )
            return final_response
        except (
            CompletionError,
            RuntimeStoreError,
            OSError,
            RuntimeError,
            ValueError,
        ) as exc:
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=request_digest,
                outcome="error",
                mutated=reframe_mutated,
                project_id=successor_brief.project_id,
                head=successor_brief.base_head,
                diagnostics=(
                    _diagnostic(
                        "codex_reframe_successor_open_failed",
                        str(exc) or type(exc).__name__,
                    ),
                    DiagnosticV1(
                        code="reframe_disposition_bound",
                        severity="info",
                        message="the source run was durably disposed for this exact repair",
                        details={
                            "source_route_run_id": request.route_run_id,
                            "disposition_hash": disposition.disposition_hash,
                            "successor_navigation_candidate_digest": (
                                disposition.successor_navigation_candidate_digest
                            ),
                        },
                    ),
                ),
            )

    def _start(
        self,
        request: CodexStartRequestV1,
        *,
        requested_route_ids: tuple[str, ...] | None = None,
        required_focus_ref: EntityVersionRef | None = None,
        required_candidate_digest: str | None = None,
        exact_brief: RunInputBriefV1 | None = None,
    ) -> CodexBridgeResponseV1:
        root = Path(request.project_root).resolve()
        if not root.is_dir():
            raise ValueError("Codex project_root must be an existing directory")
        grant = _grant(root)
        dispatcher = MachineDispatcher(
            trusted_clock=self._trusted_clock,
            preproject_operational_home=self._preproject_operational_home,
        )
        mutated = False

        # Read-only bind first.  Initialization is attempted only when the
        # machine protocol explicitly reports that the selected root is virgin.
        bound = dispatcher.dispatch(
            _machine_request(root, grant, "project.bind_or_initialize")
        )
        if bound.outcome == "permission_required":
            if not request.initialize:
                return CodexBridgeResponseV1(
                    operation=request.operation,
                    request_digest=_request_digest(request),
                    outcome="blocked",
                    mutated=False,
                    diagnostics=(
                        _diagnostic(
                            "codex_project_initialization_required",
                            "the selected root is virgin; repeat with initialize=true and an explicit project_name",
                        ),
                    ),
                )
            assert request.project_name is not None
            init_key = _operation_key(
                "initialize",
                {
                    "project_root": str(root),
                    "project_name": request.project_name,
                    "project_privacy": "public",
                },
            )
            initialized = dispatcher.dispatch(
                _machine_request(
                    root,
                    grant,
                    "project.bind_or_initialize",
                    operation_key=init_key,
                    parameters={
                        "initialize": True,
                        "project_name": request.project_name,
                        "project_privacy": "public",
                    },
                )
            )
            mutated = initialized.mutated
            if initialized.outcome != "ok":
                return self._blocked_from_machine(
                    request,
                    initialized,
                    mutated=mutated,
                    fallback_code="codex_initialization_blocked",
                )
            # Rebind read-only so repeated requests always see the current head,
            # rather than a journaled genesis response.
            bound = dispatcher.dispatch(
                _machine_request(root, grant, "project.bind_or_initialize")
            )
        if bound.outcome != "ok" or bound.project_id is None or bound.head is None:
            return self._blocked_from_machine(
                request,
                bound,
                mutated=mutated,
                fallback_code="codex_project_binding_blocked",
            )
        if not _canonical_project_is_public(root, bound.project_id):
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome="blocked",
                mutated=mutated,
                project_id=bound.project_id,
                head=bound.head,
                diagnostics=(
                    _diagnostic(
                        "codex_public_pilot_only",
                        "Phase 5A.2 requires the canonical Project entity to be public before Codex delivery",
                    ),
                ),
            )

        brief = exact_brief
        if brief is not None and (
            brief.project_id != bound.project_id
            or brief.base_head != bound.head
        ):
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome="conflict",
                mutated=mutated,
                project_id=bound.project_id,
                head=bound.head,
                diagnostics=(
                    _diagnostic(
                        "codex_reframe_base_changed",
                        "the canonical head changed before the exact repair run opened",
                    ),
                ),
            )
        if brief is None and request.requested_scope is not None:
            assert request.framing_intent is not None
            brief = RunInputBriefV1(
                project_id=bound.project_id,
                base_head=bound.head,
                requested_scope=request.requested_scope,
                framing_intent=request.framing_intent,
                privacy="public",
                compartments=("project_research",),
                actor_role="scientific_agent",
                profile_request=request.profile_request,
            )
        effective_requested_route_ids = requested_route_ids
        if (
            effective_requested_route_ids is None
            and request.requested_route_id is not None
        ):
            effective_requested_route_ids = (request.requested_route_id,)
        if (
            effective_requested_route_ids is None
            and request.requested_scope is not None
        ):
            # The public start schema defines requested_scope + framing_intent
            # as an explicit frame/reframe request.  Constrain that request to
            # its owning route so unrelated legal continuations cannot turn a
            # clear user reframe into ambiguous_next.
            effective_requested_route_ids = ("frame.question_and_benchmarks",)
        navigation_parameters: dict[str, Any] = {
            "compartments": ["project_research"],
            "privacy_clearance": "public",
        }
        if effective_requested_route_ids is not None:
            navigation_parameters["requested_route_ids"] = list(
                effective_requested_route_ids
            )
        if request.budget_units is not None:
            navigation_parameters["budget_units"] = request.budget_units
        if brief is not None:
            navigation_parameters["run_input_brief"] = brief.model_dump(mode="json")
        navigation = dispatcher.dispatch(
            _machine_request(
                root,
                grant,
                "navigation.plan_next",
                parameters=navigation_parameters,
            )
        )
        selectable_ambiguity = (
            required_candidate_digest is not None
            and navigation.outcome == "ambiguous_next"
        )
        if navigation.outcome != "ok" and not selectable_ambiguity:
            return self._blocked_from_machine(
                request,
                navigation,
                mutated=mutated,
                fallback_code="codex_navigation_blocked",
            )

        candidate_data: dict[str, Any] | None = None
        brief_data: dict[str, Any] | None = None
        navigation_outcome = navigation.result.get("outcome")
        if navigation_outcome == "unique_next":
            candidates = navigation.result.get("candidates", [])
            if len(candidates) == 1:
                candidate_data = candidates[0]
                brief_data = (
                    None if brief is None else brief.model_dump(mode="json")
                )
        elif (
            navigation_outcome == "ambiguous_next"
            and required_candidate_digest is not None
        ):
            matching = [
                item
                for item in navigation.result.get("candidates", [])
                if item.get("candidate_digest") == required_candidate_digest
            ]
            if len(matching) == 1:
                candidate_data = matching[0]
                brief_data = (
                    None if brief is None else brief.model_dump(mode="json")
                )
        elif navigation_outcome == "resume_required":
            descriptors = navigation.result.get("resume_descriptors", [])
            if len(descriptors) == 1:
                descriptor_brief = descriptors[0].get("run_input_brief")
                requested_brief = (
                    None if brief is None else brief.model_dump(mode="json")
                )
                if requested_brief is not None and descriptor_brief != requested_brief:
                    return CodexBridgeResponseV1(
                        operation=request.operation,
                        request_digest=_request_digest(request),
                        outcome="blocked",
                        mutated=mutated,
                        project_id=navigation.project_id,
                        head=navigation.head,
                        diagnostics=(
                            _diagnostic(
                                "explicit_reframe_requires_disposition",
                                "an explicit new framing brief cannot silently resume an unfinished run; dispose or complete the exact run before reframing",
                            ),
                        ),
                    )
                candidate_data = descriptors[0].get("navigation_candidate")
                brief_data = descriptor_brief
        elif navigation_outcome == "complete_for_requested_scope":
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome="complete",
                mutated=mutated,
                project_id=navigation.project_id,
                head=navigation.head,
            )
        if candidate_data is None:
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome=(
                    "human_decision_required"
                    if navigation_outcome == "human_decision_required"
                    else "ambiguous_next"
                    if navigation_outcome == "ambiguous_next"
                    else "blocked"
                ),
                mutated=mutated,
                project_id=navigation.project_id,
                head=navigation.head,
                diagnostics=navigation.diagnostics
                or (
                    _diagnostic(
                        "codex_navigation_not_unique",
                        "navigation did not expose one route candidate or one resumable run",
                    ),
                ),
            )

        candidate = NavigationCandidateV1.model_validate_json(
            canonical_json_bytes(candidate_data), strict=True
        )
        if (
            required_candidate_digest is not None
            and candidate.candidate_digest != required_candidate_digest
        ):
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome="blocked",
                mutated=mutated,
                project_id=navigation.project_id,
                head=navigation.head,
                diagnostics=(
                    _diagnostic(
                        "requested_repair_candidate_unavailable",
                        "navigation did not preserve the exact preflighted repair candidate",
                    ),
                ),
            )
        if required_focus_ref is not None and required_focus_ref not in candidate.key.focus_refs:
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome="blocked",
                mutated=mutated,
                project_id=navigation.project_id,
                head=navigation.head,
                diagnostics=(
                    _diagnostic(
                        "requested_repair_focus_unavailable",
                        "navigation did not expose exactly one repair candidate containing the requested current target",
                    ),
                ),
            )
        open_key = _operation_key(
            "open",
            {
                "candidate_digest": candidate.candidate_digest,
                "run_input_brief": brief_data,
            },
        )
        opened = dispatcher.dispatch(
            _machine_request(
                root,
                grant,
                "run.open_or_resume",
                operation_key=open_key,
                parameters={
                    "candidate": candidate.model_dump(mode="json"),
                    "run_input_brief": brief_data,
                },
            )
        )
        mutated = mutated or opened.mutated
        if opened.outcome != "ok":
            return self._blocked_from_machine(
                request,
                opened,
                mutated=mutated,
                fallback_code="codex_run_open_blocked",
            )
        route_run_id = str(opened.result["route_run_id"])
        packet_hash = str(opened.result["work_packet_hash"])
        candidate_path = str(opened.result["candidate_logical_path"])
        layout = StoreLayout.at(root)
        packet = read_work_packet(
            ProjectOperationalLayout.at(layout), route_run_id, packet_hash
        )
        blocker = _public_pilot_blocker(packet)
        if blocker is not None:
            return CodexBridgeResponseV1(
                operation=request.operation,
                request_digest=_request_digest(request),
                outcome="blocked",
                mutated=mutated,
                project_id=packet.project_id,
                head=packet.base_head,
                route_run_id=route_run_id,
                work_packet_hash=packet_hash,
                candidate_logical_path=candidate_path,
                diagnostics=(blocker,),
            )

        capability = _capability(request, root)
        planned = dispatcher.dispatch(
            _machine_request(
                root,
                grant,
                "egress.plan",
                parameters={
                    "route_run_id": route_run_id,
                    "work_packet_hash": packet_hash,
                    "capability": capability.model_dump(mode="json"),
                    "host_product": CODEX_HOST_PRODUCT,
                    "host_version": CODEX_HOST_VERSION,
                    "adapter_id": CODEX_ADAPTER_ID,
                    "provider": CODEX_PROVIDER,
                    "model": request.session.selected_model,
                    "execution_class": "provider_backed",
                    "memory_scope": "project_scoped",
                },
            )
        )
        if planned.outcome != "ok":
            return self._blocked_from_machine(
                request,
                planned,
                mutated=mutated,
                fallback_code="codex_egress_plan_blocked",
            )
        plan = EgressPlanV1.model_validate_json(
            canonical_json_bytes(planned.result), strict=True
        )
        delivery_key = _operation_key(
            "deliver",
            {
                "work_packet_hash": packet_hash,
                "capability_receipt_hash": plan.capability_receipt_hash,
                "host_session_id": request.session.session_id,
                "model": request.session.selected_model,
            },
        )
        delivery_dispatcher = MachineDispatcher(
            trusted_clock=self._trusted_clock,
            host_capabilities={CODEX_ADAPTER_ID: capability},
            delivery_sessions={
                delivery_key: TrustedHostDeliverySession(
                    operation_key=delivery_key,
                    adapter_id=CODEX_ADAPTER_ID,
                    host_session_id=request.session.session_id,
                    fresh_session=False,
                    cross_run_memory_disabled=False,
                )
            },
        )
        delivered = delivery_dispatcher.dispatch(
            _machine_request(
                root,
                grant,
                "packet.deliver",
                operation_key=delivery_key,
                parameters={
                    "route_run_id": route_run_id,
                    "work_packet_hash": packet_hash,
                    "plan": plan.model_dump(mode="json"),
                },
            )
        )
        mutated = mutated or delivered.mutated
        envelope_hash = delivered.result.get("delivery_envelope_hash")
        delivered_status = delivered.result.get("status")
        if delivered_status == "delivery_started" and envelope_hash is not None:
            returned_packet = delivered.result.get("work_packet")
            if returned_packet is not None:
                packet = WorkPacketV1.model_validate_json(
                    canonical_json_bytes(returned_packet), strict=True
                )
            else:
                _, _, packet = _read_provider_delivery(
                    root,
                    route_run_id=route_run_id,
                    work_packet_hash=packet_hash,
                    delivery_envelope_hash=str(envelope_hash),
                    expected_operation_key=delivery_key,
                )
        elif delivered_status == "unknown_possible_egress" and envelope_hash is not None:
            # The machine dispatcher correctly refuses to expose packet bytes a
            # second time.  The engine-owned bridge recovers the exact immutable
            # public packet for the same completed delivery operation.
            _, _, packet = _read_provider_delivery(
                root,
                route_run_id=route_run_id,
                work_packet_hash=packet_hash,
                delivery_envelope_hash=str(envelope_hash),
                expected_operation_key=delivery_key,
            )
        else:
            return self._blocked_from_machine(
                request,
                delivered,
                mutated=mutated,
                fallback_code="codex_delivery_blocked",
            )

        authoring_contract = compile_candidate_authoring_contract(
            StoreLayout.at(root), packet, packet_hash
        )
        return CodexBridgeResponseV1(
            operation=request.operation,
            request_digest=_request_digest(request),
            outcome="ready",
            mutated=mutated,
            project_id=packet.project_id,
            head=packet.base_head,
            route_run_id=route_run_id,
            work_packet_hash=packet_hash,
            delivery_envelope_hash=str(envelope_hash),
            candidate_logical_path=candidate_path,
            work_packet=packet,
            candidate_authoring_contract_hash=candidate_authoring_contract_hash(
                authoring_contract
            ),
            candidate_authoring_contract=authoring_contract,
        )

    def _open_framing_team(
        self, request: CodexFramingTeamOpenRequestV1
    ) -> CodexBridgeResponseV1:
        root = Path(request.project_root).resolve()
        if not root.is_dir():
            raise ValueError("Codex project_root must be an existing directory")
        envelope, _, packet = _read_framing_team_delivery(
            root,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
        )
        if envelope.host_session_id != request.session.session_id:
            raise ValueError("framing team open uses a different Codex session")
        operational = ProjectOperationalLayout.at(StoreLayout.at(root))
        with ExclusiveFileLock(operational.navigation_lock):
            assert_run_not_disposed(operational, request.route_run_id)
            if not request.capability.available:
                if framing_team_is_active(
                    operational,
                    route_run_id=request.route_run_id,
                    work_packet_hash=request.work_packet_hash,
                ):
                    raise OperationalError(
                        "an active framing team cannot downgrade to single fallback"
                    )
                assert request.capability.fallback_reason is not None
                return _framing_team_response(
                    request,
                    root=root,
                    packet=packet,
                    result=CodexFramingTeamResultV1(
                        status="single_fallback",
                        capability=request.capability,
                        reason=request.capability.fallback_reason,
                    ),
                    mutated=False,
                )
            team_already_active = framing_team_is_active(
                operational,
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
            )
            if (
                _has_active_staged_candidate(root, request.route_run_id)
                and not team_already_active
            ):
                raise OperationalError(
                    "framing team cannot activate after a candidate was staged"
                )
            assert envelope.egress_plan_hash is not None
            authorization = build_framing_team_delivery_authorization(
                packet,
                request.work_packet_hash,
                source_delivery_envelope_hash=request.delivery_envelope_hash,
                source_capability_receipt_hash=envelope.capability_receipt_hash,
                source_egress_plan_hash=envelope.egress_plan_hash,
                host_product=envelope.host_product,
                host_version=envelope.host_version,
                adapter_id=envelope.adapter_id,
                adapter_version=envelope.adapter_version,
                host_session_id=envelope.host_session_id,
                lane_separation_claim="logical",
            )
            plan_hash, plan = open_framing_team_plan(
                operational,
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
                delivery_authorization=authorization,
                execution_mode="isolated_multi_agent",
                isolation_claim="logical",
            )
        return _framing_team_response(
            request,
            root=root,
            packet=packet,
            result=CodexFramingTeamResultV1(
                status="team_ready",
                capability=request.capability,
                team_plan_hash=plan_hash,
                team_plan=plan,
            ),
            mutated=True,
        )

    def _publish_framing_team_panel(
        self, request: CodexFramingTeamPanelRequestV1
    ) -> CodexBridgeResponseV1:
        root = Path(request.project_root).resolve()
        if not root.is_dir():
            raise ValueError("Codex project_root must be an existing directory")
        envelope, _, packet = _read_framing_team_delivery(
            root,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
        )
        operational = ProjectOperationalLayout.at(StoreLayout.at(root))
        plan = read_framing_team_plan(
            operational,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            team_plan_hash=request.team_plan_hash,
        )
        authorization = read_framing_team_delivery_authorization(
            operational,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            team_plan_hash=request.team_plan_hash,
        )
        if (
            authorization.source_delivery_envelope_hash
            != request.delivery_envelope_hash
            or authorization.host_session_id != envelope.host_session_id
            or authorization.host_session_id != request.session.session_id
        ):
            raise ValueError(
                "panel delivery or Codex session differs from team authorization"
            )

        def output(
            lane_id: FramingAdvisoryLaneId, draft: CodexFramingLaneDraftV1
        ):
            return build_framing_lane_output(
                plan,
                request.team_plan_hash,
                lane_id=lane_id,
                agent_label=draft.agent_label,
                model_observation=draft.model_observation,
                content_markdown=draft.content_markdown,
            )

        panel_hash, panel = publish_framing_team_panel(
            operational,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            team_plan_hash=request.team_plan_hash,
            mentor=output("mentor", request.mentor),
            collaborators=(
                output("collaborator_a", request.collaborator_a),
                output("collaborator_b", request.collaborator_b),
            ),
        )
        return _framing_team_response(
            request,
            root=root,
            packet=packet,
            result=CodexFramingTeamResultV1(
                status="awaiting_user_choice",
                team_plan_hash=request.team_plan_hash,
                team_plan=plan,
                panel_hash=panel_hash,
                panel=panel,
            ),
            mutated=True,
        )

    def _apply_framing_user_turn(
        self, request: CodexFramingTeamUserTurnRequestV1
    ) -> CodexBridgeResponseV1:
        root = Path(request.project_root).resolve()
        if not root.is_dir():
            raise ValueError("Codex project_root must be an existing directory")
        envelope, _, packet = _read_framing_team_delivery(
            root,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
        )
        if envelope.host_session_id != request.session.session_id:
            raise ValueError("direct user turn uses a different delivery session")
        operational = ProjectOperationalLayout.at(StoreLayout.at(root))
        panel = read_framing_team_panel(
            operational,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            panel_hash=request.panel_hash,
        )
        plan = read_framing_team_plan(
            operational,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            team_plan_hash=panel.team_plan_hash,
        )
        authorization = read_framing_team_delivery_authorization(
            operational,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            team_plan_hash=panel.team_plan_hash,
        )
        if (
            authorization.source_delivery_envelope_hash
            != request.delivery_envelope_hash
            or authorization.host_session_id != request.session.session_id
        ):
            raise ValueError("direct user turn differs from team authorization")
        interpretation = request.interpretation
        if isinstance(interpretation, CodexFramingClearInterpretationV1):
            synthesis = build_framing_researcher_synthesis(
                panel,
                request.panel_hash,
                researcher_id=request.capture.researcher_id,
                researcher_text=request.capture.text,
                disposition=interpretation.disposition,
                selected_lane_ids=interpretation.selected_lane_ids,
                synthesis_markdown=interpretation.synthesis_markdown,
                worker_brief=interpretation.worker_brief,
            )
            synthesis_hash, synthesis = publish_framing_researcher_synthesis(
                operational,
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
                panel_hash=request.panel_hash,
                synthesis=synthesis,
            )
            common = {
                "team_plan_hash": panel.team_plan_hash,
                "team_plan": plan,
                "panel_hash": request.panel_hash,
                "panel": panel,
                "synthesis_hash": synthesis_hash,
                "synthesis": synthesis,
            }
            if interpretation.disposition in {"park", "kill"}:
                status: CodexFramingTeamStatus = (
                    "parked" if interpretation.disposition == "park" else "killed"
                )
                result = CodexFramingTeamResultV1(status=status, **common)
            else:
                handoff_hash, handoff = publish_framing_worker_handoff(
                    operational,
                    route_run_id=request.route_run_id,
                    work_packet_hash=request.work_packet_hash,
                    synthesis_hash=synthesis_hash,
                )
                read_framing_worker_inputs(
                    operational,
                    route_run_id=request.route_run_id,
                    work_packet_hash=request.work_packet_hash,
                    handoff_hash=handoff_hash,
                )
                result = CodexFramingTeamResultV1(
                    status="handoff_ready",
                    handoff_hash=handoff_hash,
                    handoff=handoff,
                    **common,
                )
        else:
            if isinstance(
                interpretation, CodexFramingAmbiguousInterpretationV1
            ):
                status = "awaiting_clarification"
                reason = interpretation.clarification_question
            else:
                status = "new_brief_required"
                reason = interpretation.reason
            stop = build_framing_team_stop(
                panel,
                request.panel_hash,
                researcher_id=request.capture.researcher_id,
                researcher_text=request.capture.text,
                status=status,
                reason=reason,
            )
            stop_hash, stop = publish_framing_team_stop(
                operational,
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
                panel_hash=request.panel_hash,
                stop=stop,
            )
            result = CodexFramingTeamResultV1(
                status=status,
                reason=reason,
                team_plan_hash=panel.team_plan_hash,
                team_plan=plan,
                panel_hash=request.panel_hash,
                panel=panel,
                stop_hash=stop_hash,
                stop=stop,
            )
        return _framing_team_response(
            request,
            root=root,
            packet=packet,
            result=result,
            mutated=True,
        )

    def _complete(self, request: CodexCompleteRequestV1) -> CodexBridgeResponseV1:
        root = Path(request.project_root).resolve()
        if not root.is_dir():
            raise ValueError("Codex project_root must be an existing directory")
        grant = _grant(root)
        envelope, plan, packet = _read_provider_delivery(
            root,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
        )
        snapshot = replay(StoreLayout.at(root))
        already_recorded = any(
            outcome.route_run_id == request.route_run_id
            for outcome in snapshot.route_outcomes
        )
        team_active = False
        if packet.route_id == "frame.question_and_benchmarks":
            team_active = framing_team_is_active(
                ProjectOperationalLayout.at(StoreLayout.at(root)),
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
                require_current_head=not already_recorded,
            )
        if team_active and request.framing_team_handoff_hash is None:
            raise OperationalError(
                "a declared framing team requires its exact worker handoff"
            )
        if team_active and request.action != "stage_and_commit":
            raise OperationalError(
                "declared framing-team completion requires stage_and_commit"
            )
        if request.framing_team_handoff_hash is not None:
            if not team_active:
                raise OperationalError(
                    "framing team handoff supplied without an active team plan"
                )
            _, _, _, team_handoff = read_framing_worker_inputs(
                ProjectOperationalLayout.at(StoreLayout.at(root)),
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
                handoff_hash=request.framing_team_handoff_hash,
                require_current_head=not already_recorded,
            )
            authorization = read_framing_team_delivery_authorization(
                ProjectOperationalLayout.at(StoreLayout.at(root)),
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
                team_plan_hash=team_handoff.team_plan_hash,
                require_current_head=not already_recorded,
            )
            if (
                authorization.source_delivery_envelope_hash
                != request.delivery_envelope_hash
            ):
                raise OperationalError(
                    "completion delivery differs from team authorization"
                )
            assert request.framing_team_worker is not None
            if request.framing_team_worker.model_observation != plan.model:
                raise OperationalError(
                    "research worker model observation differs from source delivery"
                )
        tool_identities = ("openai.codex",)
        transaction_path = request.transaction_path
        effective_candidate_digest = request.expected_candidate_digest
        if request.action != "commit_staged":
            if transaction_path is None:
                transaction_path = str(root / packet.candidate_logical_path)
            try:
                computed_digest = candidate_source_digest(
                    StoreLayout.at(root), packet, transaction_path
                )
            except CandidateTransactionValidationError as exc:
                return CodexBridgeResponseV1(
                    operation=request.operation,
                    request_digest=_request_digest(request),
                    outcome="error",
                    mutated=False,
                    project_id=packet.project_id,
                    head=replay(StoreLayout.at(root)).head,
                    route_run_id=packet.route_run_id,
                    work_packet_hash=request.work_packet_hash,
                    delivery_envelope_hash=request.delivery_envelope_hash,
                    candidate_logical_path=packet.candidate_logical_path,
                    diagnostics=(
                        DiagnosticV1(
                            code="codex_candidate_transaction_invalid",
                            severity="error",
                            message=(
                                "Candidate Transaction failed strict model validation; "
                                "edit the declared candidate and retry the same complete request."
                            ),
                            details={
                                "model": "Transaction",
                                "repairable": True,
                                "retry_action": (
                                    "edit_declared_candidate_and_retry_same_request"
                                ),
                                "issue_count": exc.issue_count,
                                "truncated": exc.truncated,
                                "issues": list(exc.issues),
                            },
                        ),
                    ),
                )
            if (
                effective_candidate_digest is not None
                and effective_candidate_digest != computed_digest
            ):
                raise ValueError(
                    "provided candidate digest differs from the engine-canonical Transaction"
                )
            effective_candidate_digest = computed_digest
        assert effective_candidate_digest is not None
        completion_key = _operation_key(
            "complete",
            {
                "request": request.model_dump(mode="json"),
                "effective_candidate_digest": effective_candidate_digest,
                "provider": plan.provider,
                "model": plan.model,
                "adapter_id": envelope.adapter_id,
            },
        )
        completion_binding_mutated = False
        if request.framing_team_handoff_hash is not None:
            assert request.framing_team_worker is not None
            prior_binding_exists = framing_worker_completion_binding_exists(
                ProjectOperationalLayout.at(StoreLayout.at(root)),
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
                completion_operation_key=completion_key,
                require_current_head=not already_recorded,
            )
            existing_activation = None
            if framing_worker_activation_exists(
                ProjectOperationalLayout.at(StoreLayout.at(root)),
                route_run_id=request.route_run_id,
                work_packet_hash=request.work_packet_hash,
                handoff_hash=request.framing_team_handoff_hash,
                require_current_head=not already_recorded,
            ):
                existing_activation = read_framing_worker_activation(
                    ProjectOperationalLayout.at(StoreLayout.at(root)),
                    route_run_id=request.route_run_id,
                    work_packet_hash=request.work_packet_hash,
                    handoff_hash=request.framing_team_handoff_hash,
                    require_current_head=not already_recorded,
                )
                if (
                    existing_activation.worker_agent_label
                    != request.framing_team_worker.agent_label
                    or existing_activation.worker_model_observation
                    != request.framing_team_worker.model_observation
                ):
                    raise OperationalError(
                        "framing handoff is already assigned to a different "
                        "research worker"
                    )
            if (
                _has_active_staged_candidate(root, request.route_run_id)
                and not prior_binding_exists
                and existing_activation is None
            ):
                raise OperationalError(
                    "framing team cannot claim a candidate staged before this "
                    "exact worker completion"
                )
            _, _, completion_binding_mutated = (
                publish_framing_worker_completion_binding(
                    ProjectOperationalLayout.at(StoreLayout.at(root)),
                    route_run_id=request.route_run_id,
                    work_packet_hash=request.work_packet_hash,
                    handoff_hash=request.framing_team_handoff_hash,
                    completion_operation_key=completion_key,
                    delivery_envelope_hash=request.delivery_envelope_hash,
                    candidate_digest=effective_candidate_digest,
                    worker_agent_label=request.framing_team_worker.agent_label,
                    worker_model_observation=(
                        request.framing_team_worker.model_observation
                    ),
                    require_current_head=not already_recorded,
                )
            )
        observation = TrustedHostCompletionObservation(
            operation_key=completion_key,
            delivery_envelope_hash=request.delivery_envelope_hash,
            host_product=envelope.host_product,
            host_version=envelope.host_version,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            provider=plan.provider,
            model=plan.model,
            reasoning_class="provider_hidden",
            tool_identities=tool_identities,
            completion_status="completed",
        )
        dispatcher = MachineDispatcher(
            trusted_clock=self._trusted_clock,
            completion_observations={completion_key: observation},
        )
        completed = dispatcher.dispatch(
            _machine_request(
                root,
                grant,
                "candidate.complete",
                operation_key=completion_key,
                parameters={
                    "action": request.action,
                    "route_run_id": request.route_run_id,
                    "work_packet_hash": request.work_packet_hash,
                    "delivery_envelope_hash": request.delivery_envelope_hash,
                    "transaction_path": transaction_path,
                    "artifacts": request.artifacts,
                    "expected_candidate_digest": effective_candidate_digest,
                    "reasoning_class": "provider_hidden",
                    "tool_identities": list(tool_identities),
                },
            )
        )
        if completed.outcome not in {"ok", "conflict"} or not completed.result:
            return self._blocked_from_machine(
                request,
                completed,
                mutated=(completed.mutated or completion_binding_mutated),
                fallback_code="codex_candidate_completion_blocked",
            )
        completion = CandidateCompletionResultV1.model_validate_json(
            canonical_json_bytes(completed.result), strict=True
        )
        outcome: CodexBridgeOutcome = {
            "staged": "staged",
            "committed": "committed",
            "stale_base": "stale_base",
            "recorded_failure": "blocked",
        }[completion.status]
        return CodexBridgeResponseV1(
            operation=request.operation,
            request_digest=_request_digest(request),
            outcome=outcome,
            mutated=(completed.mutated or completion_binding_mutated),
            project_id=packet.project_id,
            head=completion.head_after,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
            candidate_logical_path=packet.candidate_logical_path,
            completion=completion,
            diagnostics=completed.diagnostics,
        )

    def _finish(self, request: CodexFinishRequestV1) -> CodexBridgeResponseV1:
        """Persist a bounded terminal host receipt while leaving the run resumable."""

        root = Path(request.project_root).resolve()
        if not root.is_dir():
            raise ValueError("Codex project_root must be an existing directory")
        grant = _grant(root)
        envelope, plan, packet = _read_provider_delivery(
            root,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
        )
        finish_key = _operation_key(
            "finish",
            {
                "request": request.model_dump(mode="json"),
                "provider": plan.provider,
                "model": plan.model,
                "adapter_id": envelope.adapter_id,
            },
        )
        observation = TrustedHostCompletionObservation(
            operation_key=finish_key,
            delivery_envelope_hash=request.delivery_envelope_hash,
            host_product=envelope.host_product,
            host_version=envelope.host_version,
            adapter_id=envelope.adapter_id,
            adapter_version=envelope.adapter_version,
            provider=plan.provider,
            model=plan.model,
            reasoning_class="provider_hidden",
            tool_identities=("openai.codex",),
            completion_status=request.completion_status,
            warnings=request.warnings,
        )
        dispatcher = MachineDispatcher(
            trusted_clock=self._trusted_clock,
            completion_observations={finish_key: observation},
        )
        finished = dispatcher.dispatch(
            _machine_request(
                root,
                grant,
                "host.finish",
                operation_key=finish_key,
                parameters={
                    "route_run_id": request.route_run_id,
                    "work_packet_hash": request.work_packet_hash,
                    "delivery_envelope_hash": request.delivery_envelope_hash,
                    "expected_candidate_digest": request.expected_candidate_digest,
                    "reasoning_class": "provider_hidden",
                    "tool_identities": ["openai.codex"],
                    "completion_status": request.completion_status,
                    "warnings": list(request.warnings),
                },
            )
        )
        if finished.outcome != "blocked" or not finished.result:
            return self._blocked_from_machine(
                request,
                finished,
                mutated=finished.mutated,
                fallback_code="codex_host_finish_blocked",
            )
        completion = CandidateCompletionResultV1.model_validate_json(
            canonical_json_bytes(finished.result), strict=True
        )
        if completion.status != "recorded_failure":
            raise ValueError("host.finish did not return a recorded failure")
        return CodexBridgeResponseV1(
            operation=request.operation,
            request_digest=_request_digest(request),
            outcome="recorded_failure",
            mutated=finished.mutated,
            project_id=packet.project_id,
            head=completion.head_after,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
            candidate_logical_path=packet.candidate_logical_path,
            completion=completion,
            diagnostics=finished.diagnostics,
        )


__all__ = [
    "CODEX_ADAPTER_ID",
    "CODEX_ADAPTER_VERSION",
    "CODEX_BRIDGE_REQUEST_ADAPTER",
    "CODEX_HOST_PRODUCT",
    "CODEX_HOST_VERSION",
    "CODEX_PROVIDER",
    "CodexBridge",
    "CodexBridgeRequest",
    "CodexBridgeRequestValue",
    "CodexBridgeResponseV1",
    "CodexCompleteRequestV1",
    "CodexDirectUserCaptureV1",
    "CodexFinishRequestV1",
    "CodexFramingAmbiguousInterpretationV1",
    "CodexFramingClearInterpretationV1",
    "CodexFramingLaneDraftV1",
    "CodexFramingNewBriefInterpretationV1",
    "CodexFramingTeamCapabilityV1",
    "CodexFramingTeamOpenRequestV1",
    "CodexFramingTeamPanelRequestV1",
    "CodexFramingTeamResultV1",
    "CodexFramingTeamUserTurnRequestV1",
    "CodexFramingWorkerObservationV1",
    "CodexReframeRepairRequestV1",
    "CodexSessionV1",
    "CodexStartRequestV1",
    "codex_bridge_schema",
]
