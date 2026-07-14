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

from pydantic import Field, TypeAdapter, model_validator

from .candidate_contract import (
    CandidateAuthoringContractV1,
    candidate_authoring_contract_hash,
    compile_candidate_authoring_contract,
)
from .codec import canonical_json_bytes, sha256_digest
from .ids import utc_now
from .models import Digest, StrictModel
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
    RunInputBriefV1,
    WorkPacketV1,
)
from .machine.operational import (
    ContentAddressedOperationalStore,
    ProjectOperationalLayout,
)
from .machine.packets import read_work_packet
from .runtime import StoreLayout
from .runtime.replay import replay


CODEX_HOST_PRODUCT = "OpenAI Codex"
CODEX_HOST_VERSION = "phase5a2-pilot"
CODEX_ADAPTER_ID = "econ-theorist.codex.phase5a2"
CODEX_ADAPTER_VERSION = "1"
CODEX_PROVIDER = "openai"

CodexBridgeOperation: TypeAlias = Literal["start_or_resume", "complete"]
CodexBridgeOutcome: TypeAlias = Literal[
    "ready",
    "staged",
    "committed",
    "stale_base",
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
        return self


CodexBridgeRequest: TypeAlias = Annotated[
    CodexStartRequestV1 | CodexCompleteRequestV1,
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
    completion: CandidateCompletionResultV1 | None = None
    diagnostics: tuple[DiagnosticV1, ...] = ()

    @model_validator(mode="after")
    def _outcome_payload_is_complete(self) -> "CodexBridgeResponseV1":
        if self.outcome == "ready" and any(
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
        if self.outcome == "ready":
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
                    "ready Codex response has a mismatched candidate authoring contract"
                )
        if self.outcome in {"staged", "committed", "stale_base"} and (
            self.completion is None
        ):
            raise ValueError("completion outcomes require a completion result")
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


def _request_digest(request: CodexStartRequestV1 | CodexCompleteRequestV1) -> str:
    return sha256_digest(canonical_json_bytes(request))


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
        self, request: CodexStartRequestV1 | CodexCompleteRequestV1
    ) -> CodexBridgeResponseV1:
        try:
            if isinstance(request, CodexStartRequestV1):
                return self._start(request)
            return self._complete(request)
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
        request: CodexStartRequestV1 | CodexCompleteRequestV1,
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

    def _start(self, request: CodexStartRequestV1) -> CodexBridgeResponseV1:
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

        brief = None
        if request.requested_scope is not None:
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
        navigation_parameters: dict[str, Any] = {
            "compartments": ["project_research"],
            "privacy_clearance": "public",
        }
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
        if navigation.outcome != "ok":
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
        elif navigation_outcome == "resume_required":
            descriptors = navigation.result.get("resume_descriptors", [])
            if len(descriptors) == 1:
                candidate_data = descriptors[0].get("navigation_candidate")
                brief_data = descriptors[0].get("run_input_brief")
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
            tool_identities=("openai.codex",),
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
                    "tool_identities": ["openai.codex"],
                },
            )
        )
        if completed.outcome not in {"ok", "conflict"} or not completed.result:
            return self._blocked_from_machine(
                request,
                completed,
                mutated=completed.mutated,
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
            mutated=completed.mutated,
            project_id=packet.project_id,
            head=completion.head_after,
            route_run_id=request.route_run_id,
            work_packet_hash=request.work_packet_hash,
            delivery_envelope_hash=request.delivery_envelope_hash,
            candidate_logical_path=packet.candidate_logical_path,
            completion=completion,
            diagnostics=completed.diagnostics,
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
    "CodexBridgeResponseV1",
    "CodexCompleteRequestV1",
    "CodexSessionV1",
    "CodexStartRequestV1",
    "codex_bridge_schema",
]
