"""Strict noncanonical models for the Phase 5A.1 machine protocol."""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypeAlias

from pydantic import Field, StringConstraints, field_validator, model_validator

from ..models import Actor, Digest, EntityVersionRef, PrivacyLabel, StrictModel


NonEmpty: TypeAlias = Annotated[str, StringConstraints(min_length=1)]
OperationKey: TypeAlias = Annotated[
    str, StringConstraints(pattern=r"^[A-Za-z][A-Za-z0-9._:-]{0,127}$")
]
RECEIPT_TOKEN_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._:+/@-]{0,127}$"
ReceiptToken: TypeAlias = Annotated[
    str,
    StringConstraints(pattern=RECEIPT_TOKEN_PATTERN),
]

MachineOperation: TypeAlias = Literal[
    "bootstrap.plan",
    "bootstrap.verify",
    "project.bind_or_initialize",
    "project.inspect",
    "navigation.plan_next",
    "run.open_or_resume",
    "egress.plan",
    "packet.deliver",
    "candidate.complete",
    "host.finish",
    "decision.confirm",
    "operation.inspect",
]

MachineOutcome: TypeAlias = Literal[
    "ok",
    "blocked",
    "permission_required",
    "human_decision_required",
    "ambiguous_next",
    "repair_required",
    "unsupported_host",
    "conflict",
    "error",
]


class DiagnosticV1(StrictModel):
    diagnostic_schema: Literal["econ-theorist/diagnostic/v1"] = (
        "econ-theorist/diagnostic/v1"
    )
    code: NonEmpty
    severity: Literal["info", "warning", "error"]
    message: NonEmpty
    details: dict[str, Any] = Field(default_factory=dict)


class DiscoveryGrantV1(StrictModel):
    grant_schema: Literal["econ-theorist/discovery-grant/v1"] = (
        "econ-theorist/discovery-grant/v1"
    )
    selected_root: NonEmpty
    allowed_discovery_roots: tuple[NonEmpty, ...]
    ancestor_check_boundary: NonEmpty | None = None
    stable_workspace_root: NonEmpty

    @field_validator("allowed_discovery_roots")
    @classmethod
    def _unique_discovery_roots(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value:
            raise ValueError("at least one allowed discovery root is required")
        if len(set(value)) != len(value):
            raise ValueError("allowed discovery roots must be unique")
        return value


class MachineRequestV1(StrictModel):
    request_schema: Literal["econ-theorist/machine-request/v1"] = (
        "econ-theorist/machine-request/v1"
    )
    operation: MachineOperation
    operation_key: OperationKey | None = None
    project_root: NonEmpty | None = None
    discovery_grant: DiscoveryGrantV1 | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class MachineResponseV1(StrictModel):
    response_schema: Literal["econ-theorist/machine-response/v1"] = (
        "econ-theorist/machine-response/v1"
    )
    protocol_version: Literal[1] = 1
    operation: MachineOperation
    request_digest: Digest
    outcome: MachineOutcome
    mutated: bool
    project_id: str | None = None
    head: Digest | None = None
    result: dict[str, Any] = Field(default_factory=dict)
    diagnostics: tuple[DiagnosticV1, ...] = ()
    operation_receipt_hash: Digest | None = None


class CapabilityV1(StrictModel):
    capability_id: NonEmpty
    available: bool
    required: bool
    evidence: NonEmpty


class CapabilityReceiptV1(StrictModel):
    capability_schema: Literal["econ-theorist/capability-receipt/v1"] = (
        "econ-theorist/capability-receipt/v1"
    )
    host_product: NonEmpty
    host_version: NonEmpty
    adapter_id: NonEmpty
    adapter_version: NonEmpty
    execution_class: Literal["local", "provider_backed", "unknown"]
    agent_topology: Literal["single"] = "single"
    technically_accessible_roots: tuple[NonEmpty, ...]
    model_tool_isolation: Literal["verified", "unverified", "unavailable"]
    trusted_human_channel: Literal["verified", "unverified", "unavailable"]
    environment_redaction: Literal["verified", "unverified", "unavailable"] = (
        "unavailable"
    )
    credential_store_isolation: Literal[
        "verified", "unverified", "unavailable"
    ] = "unavailable"
    secret_file_denial: Literal["verified", "unverified", "unavailable"] = (
        "unavailable"
    )
    shadow_workspace_isolation: Literal[
        "verified", "unverified", "unavailable"
    ] = "unavailable"
    enforced_denied_compartments: tuple[NonEmpty, ...] = ()
    capabilities: Annotated[tuple[CapabilityV1, ...], Field(min_length=1)]
    observed_at: NonEmpty

    @model_validator(mode="after")
    def _capabilities_are_unique_and_required_checks_pass(
        self,
    ) -> "CapabilityReceiptV1":
        identifiers = [item.capability_id for item in self.capabilities]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("capability IDs must be unique")
        if len(set(self.enforced_denied_compartments)) != len(
            self.enforced_denied_compartments
        ):
            raise ValueError("enforced denied compartments must be unique")
        if any(item.required and not item.available for item in self.capabilities):
            raise ValueError("every required capability must be available")
        return self


class BootstrapArtifactV1(StrictModel):
    filename: NonEmpty
    sha256: Digest
    byte_size: Annotated[int, Field(ge=0)]
    role: Literal[
        "wheel", "dependency", "host_manifest", "engine_manifest", "descriptor"
    ]


class BootstrapDescriptorV1(StrictModel):
    descriptor_schema: Literal["econ-theorist/bootstrap-descriptor/v1"] = (
        "econ-theorist/bootstrap-descriptor/v1"
    )
    publisher_id: NonEmpty
    canonical_source: NonEmpty
    release_version: NonEmpty
    python_constraint: NonEmpty
    supported_platform_tags: tuple[NonEmpty, ...]
    artifacts: Annotated[tuple[BootstrapArtifactV1, ...], Field(min_length=1)]
    dependency_lock_hash: Digest
    host_manifest_hash: Digest
    engine_manifest_hash: Digest
    issued_at: NonEmpty
    expires_at: NonEmpty
    revocation_policy_id: NonEmpty
    signature_algorithm: NonEmpty
    signature: NonEmpty

    @model_validator(mode="after")
    def _artifacts_are_unique_and_include_engine(self) -> "BootstrapDescriptorV1":
        filenames = [item.filename for item in self.artifacts]
        if len(set(filenames)) != len(filenames):
            raise ValueError("bootstrap artifact filenames must be unique")
        if not any(item.role == "wheel" for item in self.artifacts):
            raise ValueError("bootstrap descriptor requires an engine wheel")
        manifests = [item for item in self.artifacts if item.role == "engine_manifest"]
        if len(manifests) != 1 or manifests[0].sha256 != self.engine_manifest_hash:
            raise ValueError(
                "bootstrap descriptor requires one exact engine release manifest"
            )
        return self


class InstallPlanV1(StrictModel):
    install_plan_schema: Literal["econ-theorist/install-plan/v1"] = (
        "econ-theorist/install-plan/v1"
    )
    descriptor_hash: Digest
    release_version: NonEmpty
    canonical_source: NonEmpty
    installation_scope: Literal["user_isolated", "host_managed"]
    environment_root: NonEmpty
    absolute_launcher: NonEmpty
    network_origins: tuple[NonEmpty, ...]
    files_to_create: tuple[NonEmpty, ...]
    files_to_modify: tuple[NonEmpty, ...] = ()
    project_initialization_requested: bool = False
    project_root: NonEmpty | None = None
    project_name: NonEmpty | None = None
    requires_external_bootstrap_executor: bool = True

    @model_validator(mode="after")
    def _initialization_fields_are_explicit(self) -> "InstallPlanV1":
        if self.project_initialization_requested != (
            self.project_root is not None and self.project_name is not None
        ):
            raise ValueError(
                "project initialization requires both exact root and project name"
            )
        return self


class EngineResourceV1(StrictModel):
    logical_path: NonEmpty
    sha256: Digest
    byte_size: Annotated[int, Field(ge=0)]


class InstalledDistributionV1(StrictModel):
    name: NonEmpty
    version: NonEmpty
    files: Annotated[tuple[EngineResourceV1, ...], Field(min_length=1)]
    file_inventory_hash: Digest


class EngineReleaseTargetV1(StrictModel):
    target_id: NonEmpty
    python_tag: NonEmpty
    platform_tag: NonEmpty
    engine_inventory_hash: Digest


class EngineReleaseManifestV1(StrictModel):
    release_manifest_schema: Literal[
        "econ-theorist/engine-release-manifest/v1"
    ] = "econ-theorist/engine-release-manifest/v1"
    publisher_id: NonEmpty
    release_version: NonEmpty
    engine_version: NonEmpty
    dependency_lock_hash: Digest
    targets: Annotated[tuple[EngineReleaseTargetV1, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _targets_are_unique(self) -> "EngineReleaseManifestV1":
        identifiers = [item.target_id for item in self.targets]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("engine release target IDs must be unique")
        return self


class EngineReleaseInventoryV1(StrictModel):
    inventory_schema: Literal[
        "econ-theorist/engine-release-inventory/v1"
    ] = "econ-theorist/engine-release-inventory/v1"
    engine_version: NonEmpty
    distributions: Annotated[
        tuple[InstalledDistributionV1, ...], Field(min_length=1)
    ]
    resources: Annotated[tuple[EngineResourceV1, ...], Field(min_length=1)]
    host_manifest_hash: Digest
    navigation_registry_hash: Digest


class EngineManifestV1(StrictModel):
    engine_manifest_schema: Literal["econ-theorist/engine-manifest/v1"] = (
        "econ-theorist/engine-manifest/v1"
    )
    engine_version: NonEmpty
    python_executable: NonEmpty
    launcher_path: NonEmpty
    package_root: NonEmpty
    install_mode: Literal["verified_release", "development_checkout", "unknown"]
    release_inventory: EngineReleaseInventoryV1
    release_inventory_hash: Digest


class EngineVerificationV1(StrictModel):
    verification_schema: Literal["econ-theorist/engine-verification/v1"] = (
        "econ-theorist/engine-verification/v1"
    )
    verified: bool
    release_integrity: Literal[
        "verified", "development_only", "external_bootstrap_required", "failed"
    ]
    engine_manifest_hash: Digest
    expected_engine_inventory_hash: Digest | None = None
    release_manifest_hash: Digest | None = None
    absolute_launcher_verified: bool
    doctor_required_ok: bool
    diagnostics: tuple[DiagnosticV1, ...] = ()


class CompatibilityProbeV1(StrictModel):
    probe_schema: Literal["econ-theorist/compatibility-probe/v1"] = (
        "econ-theorist/compatibility-probe/v1"
    )
    classification: Literal[
        "absent",
        "virgin",
        "valid_existing",
        "recovery_required",
        "corrupt",
        "incompatible",
    ]
    project_root: NonEmpty
    store_root: NonEmpty
    head: Digest | None = None
    project_id: NonEmpty | None = None
    transaction_schema: int | None = None
    chain_length: Annotated[int, Field(ge=0)] = 0
    engine_version_hint: NonEmpty | None = None
    compatible_engine_version: NonEmpty | None = None
    diagnostics: tuple[NonEmpty, ...] = ()


class ProjectBindingV1(StrictModel):
    binding_schema: Literal["econ-theorist/project-binding/v1"] = (
        "econ-theorist/project-binding/v1"
    )
    status: Literal[
        "bound",
        "initialized",
        "project_initialization_required",
        "project_identity_conflict",
        "root_scope_incomplete",
        "recovery_required",
        "corrupt",
        "incompatible",
    ]
    project_root: NonEmpty
    project_id: NonEmpty | None = None
    head: Digest | None = None
    canonical_validation: Literal["valid", "not_run", "failed"]
    probe: CompatibilityProbeV1
    mutated: bool
    diagnostics: tuple[DiagnosticV1, ...] = ()


class RunInputBriefV1(StrictModel):
    brief_schema: Literal["econ-theorist/run-input-brief/v1"] = (
        "econ-theorist/run-input-brief/v1"
    )
    project_id: NonEmpty
    base_head: Digest
    requested_scope: NonEmpty
    framing_intent: NonEmpty
    privacy: PrivacyLabel
    compartments: tuple[NonEmpty, ...]
    actor_role: NonEmpty
    profile_request: NonEmpty | None = None

    @field_validator("compartments")
    @classmethod
    def _brief_compartments(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if not value or len(set(value)) != len(value):
            raise ValueError("brief compartments must be non-empty and unique")
        return value


class NavigationCandidateKeyV1(StrictModel):
    candidate_key_schema: Literal["econ-theorist/navigation-candidate-key/v1"] = (
        "econ-theorist/navigation-candidate-key/v1"
    )
    base_head: Digest
    route_id: NonEmpty
    route_version: Annotated[int, Field(ge=1)]
    purpose: NonEmpty
    actor: Actor
    compartments: tuple[NonEmpty, ...]
    privacy_clearance: PrivacyLabel
    focus_refs: tuple[EntityVersionRef, ...]
    context_budget: Annotated[int, Field(ge=1)]
    context_hash: Digest
    route_registry_hash: Digest
    instruction_bundle_hash: Digest
    context_selector_version: NonEmpty
    navigation_registry_hash: Digest
    policy_hashes: dict[NonEmpty, Digest]
    run_input_brief_hash: Digest | None = None


class NavigationCandidateV1(StrictModel):
    candidate_schema: Literal["econ-theorist/navigation-candidate/v1"] = (
        "econ-theorist/navigation-candidate/v1"
    )
    candidate_digest: Digest
    key: NavigationCandidateKeyV1
    explanation: NonEmpty


class ResumeDescriptorV1(StrictModel):
    """Complete immutable input for re-entering one unfinished run."""

    resume_descriptor_schema: Literal[
        "econ-theorist/resume-descriptor/v1"
    ] = "econ-theorist/resume-descriptor/v1"
    route_run_id: NonEmpty
    lifecycle: Literal["opened", "candidate_present", "staged"]
    navigation_candidate: NavigationCandidateV1
    run_input_brief: RunInputBriefV1 | None
    work_packet_hash: Digest
    candidate_logical_path: NonEmpty
    next_action: Literal["run.open_or_resume"] = "run.open_or_resume"

    @model_validator(mode="after")
    def _exact_resume_bindings(self) -> "ResumeDescriptorV1":
        from ..codec import canonical_json_bytes, sha256_digest

        candidate = self.navigation_candidate
        if candidate.candidate_digest != sha256_digest(
            canonical_json_bytes(candidate.key)
        ):
            raise ValueError("resume candidate digest differs from its immutable key")
        expected_path = (
            f".econ-theorist/staging/{self.route_run_id}/candidate.json"
        )
        if self.candidate_logical_path != expected_path:
            raise ValueError("resume candidate path differs from the route run")
        brief = self.run_input_brief
        expected_brief_hash = candidate.key.run_input_brief_hash
        if brief is None:
            if expected_brief_hash is not None:
                raise ValueError("resume descriptor omits the candidate input brief")
            return self
        if (
            expected_brief_hash != sha256_digest(canonical_json_bytes(brief))
            or brief.base_head != candidate.key.base_head
            or brief.actor_role != candidate.key.actor.actor_id
            or brief.compartments != candidate.key.compartments
            or brief.privacy != candidate.key.privacy_clearance
        ):
            raise ValueError("resume input brief differs from the candidate key")
        return self


class NavigationPlanV1(StrictModel):
    plan_schema: Literal["econ-theorist/navigation-plan/v1"] = (
        "econ-theorist/navigation-plan/v1"
    )
    outcome: Literal[
        "unique_next",
        "resume_required",
        "human_decision_required",
        "ambiguous_next",
        "repair_required",
        "complete_for_requested_scope",
        "navigation_unsupported",
        "unsupported_host",
    ]
    project_id: NonEmpty
    base_head: Digest
    candidates: tuple[NavigationCandidateV1, ...] = ()
    active_run_ids: tuple[NonEmpty, ...] = ()
    resume_descriptors: tuple[ResumeDescriptorV1, ...] = ()
    blockers: tuple[DiagnosticV1, ...] = ()

    @model_validator(mode="after")
    def _resume_descriptor_set(self) -> "NavigationPlanV1":
        descriptor_ids = tuple(
            item.route_run_id for item in self.resume_descriptors
        )
        if len(set(descriptor_ids)) != len(descriptor_ids):
            raise ValueError("resume descriptor route-run IDs must be unique")
        if descriptor_ids and descriptor_ids != self.active_run_ids:
            raise ValueError(
                "resume descriptors must bind the ordered active-run set"
            )
        if descriptor_ids and self.outcome not in {
            "resume_required",
            "ambiguous_next",
        }:
            raise ValueError("resume descriptors require a resume navigation outcome")
        if self.outcome == "resume_required" and (
            len(self.active_run_ids) != 1
            or descriptor_ids != self.active_run_ids
        ):
            raise ValueError(
                "resume_required must expose the exact single active-run descriptor"
            )
        if (
            self.outcome == "ambiguous_next"
            and self.active_run_ids
            and descriptor_ids != self.active_run_ids
        ):
            raise ValueError(
                "active ambiguous runs must expose their exact resume descriptors"
            )
        return self


class RunExecutionViewV1(StrictModel):
    view_schema: Literal["econ-theorist/run-execution-view/v1"] = (
        "econ-theorist/run-execution-view/v1"
    )
    route_run_id: NonEmpty
    integrity: Literal["valid", "invalid"]
    base_freshness: Literal["current", "stale", "unknown", "not_applicable"]
    lifecycle: Literal[
        "opened",
        "candidate_present",
        "staged",
        "commit_conflict",
        "committed",
        "unknown",
    ]
    base_head: Digest | None
    current_head: Digest | None
    candidate_digest: Digest | None = None
    committed_transaction_digest: Digest | None = None
    diagnostics: tuple[DiagnosticV1, ...] = ()


class ProjectInspectionV1(StrictModel):
    inspection_schema: Literal["econ-theorist/project-inspection/v1"] = (
        "econ-theorist/project-inspection/v1"
    )
    project_id: NonEmpty
    head: Digest
    engine_version: NonEmpty
    route_registry_hash: Digest
    navigation_registry_hash: Digest
    profile_catalog_hash: Digest | None = None
    craft_corpus_hash: Digest | None = None
    run_views: tuple[RunExecutionViewV1, ...] = ()
    pending_decision_refs: tuple[NonEmpty, ...] = ()
    blocker_ids: tuple[NonEmpty, ...] = ()
    navigation: NavigationPlanV1 | None = None


class WorkPacketV1(StrictModel):
    packet_schema: Literal["econ-theorist/work-packet/v1"] = (
        "econ-theorist/work-packet/v1"
    )
    # Compiler v1 packets remain byte-frozen for historical replay.  New
    # packets use v2 to expose deterministic input-evidence bindings to the
    # candidate authoring contract.
    packet_compiler_version: Literal[1, 2] = 1
    engine_version: NonEmpty
    engine_semantics_hash: Digest
    project_id: NonEmpty
    base_head: Digest
    route_run_id: NonEmpty
    route_run_hash: Digest
    context_manifest_hash: Digest
    compiled_context_hash: Digest
    run_input_brief_hash: Digest | None
    navigation_candidate_digest: Digest
    route_id: NonEmpty
    route_version: Annotated[int, Field(ge=1)]
    purpose: NonEmpty
    actor_role: NonEmpty
    focus_refs: tuple[EntityVersionRef, ...]
    route_registry_hash: Digest
    instruction_bundle_hash: Digest
    context_selector_version: NonEmpty
    policy_hashes: dict[NonEmpty, Digest]
    privacy_clearance: PrivacyLabel
    compartments: tuple[NonEmpty, ...]
    instruction_text: NonEmpty
    compiled_context: dict[str, Any]
    run_input: RunInputBriefV1 | None
    omissions: tuple[NonEmpty, ...]
    hidden_compartments: tuple[NonEmpty, ...]
    pending_human_gate_refs: tuple[NonEmpty, ...]
    candidate_logical_path: NonEmpty
    shadow_logical_root: NonEmpty
    allowed_operation_classes: tuple[NonEmpty, ...]
    required_output_entity_types: tuple[NonEmpty, ...]
    required_output_relation_types: tuple[NonEmpty, ...]
    validation_operation: Literal["candidate.complete"] = "candidate.complete"
    forbidden_actions: tuple[NonEmpty, ...]
    stale_base_behavior: Literal["stop_and_reinspect"] = "stop_and_reinspect"
    supersedes_packet_hash: Digest | None = None
    supersession_reason: NonEmpty | None = None

    @model_validator(mode="after")
    def _supersession_pair(self) -> "WorkPacketV1":
        if (self.supersedes_packet_hash is None) != (self.supersession_reason is None):
            raise ValueError("packet supersession hash and reason must appear together")
        return self


class OpenRunResultV1(StrictModel):
    open_result_schema: Literal["econ-theorist/open-run-result/v1"] = (
        "econ-theorist/open-run-result/v1"
    )
    status: Literal["opened", "resumed"]
    route_run_id: NonEmpty
    navigation_candidate_digest: Digest
    work_packet_hash: Digest
    candidate_logical_path: NonEmpty


class EgressPlanV1(StrictModel):
    egress_plan_schema: Literal["econ-theorist/egress-plan/v1"] = (
        "econ-theorist/egress-plan/v1"
    )
    project_id: NonEmpty
    head: Digest
    work_packet_hash: Digest
    host_product: NonEmpty
    host_version: NonEmpty
    adapter_id: NonEmpty
    adapter_version: NonEmpty
    capability_receipt_hash: Digest
    provider: NonEmpty
    model: NonEmpty
    execution_class: Literal["local", "provider_backed"]
    technically_accessible_roots: tuple[NonEmpty, ...]
    data_classes: tuple[NonEmpty, ...]
    privacy_labels: tuple[PrivacyLabel, ...]
    compartments: tuple[NonEmpty, ...]
    hidden_compartments: tuple[NonEmpty, ...]
    enforced_denied_compartments: tuple[NonEmpty, ...]
    purpose: NonEmpty
    retention: NonEmpty
    training_use: NonEmpty
    logging: NonEmpty
    region: NonEmpty
    human_review: NonEmpty
    memory_scope: Literal["disabled", "project_scoped", "cross_project", "unknown"]
    technical_isolation: Literal["verified", "unverified", "unavailable"]
    trusted_human_channel: Literal["verified", "unverified", "unavailable"]
    environment_redaction: Literal["verified", "unverified", "unavailable"]
    credential_store_isolation: Literal[
        "verified", "unverified", "unavailable"
    ]
    secret_file_denial: Literal["verified", "unverified", "unavailable"]
    shadow_workspace_isolation: Literal[
        "verified", "unverified", "unavailable"
    ]
    authorization_required: bool


class HumanApprovalChallengeV1(StrictModel):
    challenge_schema: Literal["econ-theorist/human-approval-challenge/v1"] = (
        "econ-theorist/human-approval-challenge/v1"
    )
    challenge_id: NonEmpty
    project_id: NonEmpty
    head: Digest
    action: NonEmpty
    decision_digest: Digest
    options: tuple[NonEmpty, ...]
    selected_option: NonEmpty
    authority_level: Literal["L2", "L3"]
    blast_radius_summary: NonEmpty
    expires_at: NonEmpty


class HumanApprovalReceiptV1(StrictModel):
    receipt_schema: Literal["econ-theorist/human-approval-receipt/v1"] = (
        "econ-theorist/human-approval-receipt/v1"
    )
    receipt_id: NonEmpty
    challenge_hash: Digest
    project_id: NonEmpty
    head: Digest
    action: NonEmpty
    decision_digest: Digest
    selected_option: NonEmpty
    authority_level: Literal["L2", "L3"]
    issued_at: NonEmpty
    expires_at: NonEmpty
    issuer_channel_id: NonEmpty
    nonce: NonEmpty
    authenticator: NonEmpty


class DecisionConfirmationResultV1(StrictModel):
    confirmation_schema: Literal["econ-theorist/decision-confirmation/v1"] = (
        "econ-theorist/decision-confirmation/v1"
    )
    status: Literal["committed", "already_committed", "stale_base"]
    decision_digest: Digest
    transaction_digest: Digest | None
    head_before: Digest
    head_after: Digest


class EgressAuthorizationV1(StrictModel):
    authorization_schema: Literal["econ-theorist/egress-authorization/v1"] = (
        "econ-theorist/egress-authorization/v1"
    )
    authorization_id: NonEmpty
    egress_plan_hash: Digest
    project_id: NonEmpty
    head: Digest
    work_packet_hash: Digest
    provider: NonEmpty
    purpose: NonEmpty
    allowed_data_classes: tuple[NonEmpty, ...]
    issued_at: NonEmpty
    expires_at: NonEmpty
    reuse: Literal["single_delivery", "bounded_reuse"]
    max_deliveries: Annotated[int, Field(ge=1)] = 1
    issuer_channel_id: NonEmpty
    nonce: NonEmpty
    authenticator: NonEmpty

    @model_validator(mode="after")
    def _reuse_has_an_exact_bound(self) -> "EgressAuthorizationV1":
        if self.reuse == "single_delivery" and self.max_deliveries != 1:
            raise ValueError("single_delivery authorization must have bound 1")
        if self.reuse == "bounded_reuse" and self.max_deliveries <= 1:
            raise ValueError("bounded_reuse requires an explicit bound greater than 1")
        return self


class LedgerEventV1(StrictModel):
    ledger_event_schema: Literal["econ-theorist/ledger-event/v1"] = (
        "econ-theorist/ledger-event/v1"
    )
    ledger_kind: Literal["operation", "approval", "egress"]
    subject_id: NonEmpty
    sequence: Annotated[int, Field(ge=1)]
    event: NonEmpty
    operation_key: OperationKey | None
    request_digest: Digest | None
    payload_hash: Digest | None
    previous_event_hash: Digest | None
    recorded_at: NonEmpty


class DeliveryEnvelopeV1(StrictModel):
    envelope_schema: Literal["econ-theorist/delivery-envelope/v1"] = (
        "econ-theorist/delivery-envelope/v1"
    )
    work_packet_hash: Digest
    operation_key: OperationKey
    host_product: NonEmpty
    host_version: NonEmpty
    adapter_id: NonEmpty
    adapter_version: NonEmpty
    host_session_id: NonEmpty
    session_fresh: bool
    cross_run_memory_disabled: bool
    project_root: NonEmpty
    candidate_root: NonEmpty
    projection_id: NonEmpty | None
    projection_hash: Digest | None
    host_manifest_hash: Digest
    capability_receipt_hash: Digest
    egress_plan_hash: Digest | None
    egress_authorization_hash: Digest | None
    delivery_time: NonEmpty
    agent_topology: Literal["single"] = "single"
    pre_delivery_status: Literal[
        "authorized_to_deliver", "blocked_before_delivery"
    ]


class PacketDeliveryResultV1(StrictModel):
    delivery_result_schema: Literal["econ-theorist/packet-delivery-result/v1"] = (
        "econ-theorist/packet-delivery-result/v1"
    )
    status: Literal[
        "delivery_started", "blocked_before_delivery", "unknown_possible_egress"
    ]
    delivery_envelope_hash: Digest
    work_packet_hash: Digest
    work_packet: WorkPacketV1 | None = None
    diagnostics: tuple[DiagnosticV1, ...] = ()


class HostOperationReceiptV1(StrictModel):
    host_receipt_schema: Literal["econ-theorist/host-operation-receipt/v1"] = (
        "econ-theorist/host-operation-receipt/v1"
    )
    delivery_envelope_hash: Digest | None
    work_packet_hash: Digest | None
    operation_key: OperationKey
    host_product: NonEmpty
    host_version: NonEmpty
    adapter_id: NonEmpty
    adapter_version: NonEmpty
    provider: NonEmpty
    model: NonEmpty
    reasoning_class: NonEmpty
    tool_identities: tuple[NonEmpty, ...]
    candidate_digest: Digest | None
    artifact_digests: tuple[Digest, ...]
    stage_outcome: NonEmpty | None
    commit_outcome: NonEmpty | None
    head_before: Digest | None
    head_after: Digest | None
    warnings: tuple[NonEmpty, ...]
    completion_status: Literal[
        "completed",
        "failed_no_effect",
        "failed_terminal",
        "cancelled",
        "unknown_possible_effect",
        "unknown_possible_egress",
    ]
    completed_at: NonEmpty


class CandidateCompletionResultV1(StrictModel):
    completion_result_schema: Literal[
        "econ-theorist/candidate-completion-result/v1"
    ] = "econ-theorist/candidate-completion-result/v1"
    status: Literal["staged", "committed", "stale_base", "recorded_failure"]
    route_run_id: NonEmpty
    candidate_digest: Digest | None
    transaction_digest: Digest | None
    head_before: Digest
    head_after: Digest
    host_receipt_hash: Digest


MACHINE_SCHEMA_MODELS = (
    MachineRequestV1,
    MachineResponseV1,
    DiscoveryGrantV1,
    DiagnosticV1,
    CapabilityReceiptV1,
    BootstrapDescriptorV1,
    InstallPlanV1,
    EngineResourceV1,
    InstalledDistributionV1,
    EngineReleaseTargetV1,
    EngineReleaseManifestV1,
    EngineReleaseInventoryV1,
    EngineManifestV1,
    EngineVerificationV1,
    CompatibilityProbeV1,
    ProjectBindingV1,
    RunInputBriefV1,
    NavigationCandidateKeyV1,
    ResumeDescriptorV1,
    NavigationPlanV1,
    RunExecutionViewV1,
    ProjectInspectionV1,
    WorkPacketV1,
    OpenRunResultV1,
    EgressPlanV1,
    HumanApprovalChallengeV1,
    HumanApprovalReceiptV1,
    DecisionConfirmationResultV1,
    EgressAuthorizationV1,
    LedgerEventV1,
    DeliveryEnvelopeV1,
    PacketDeliveryResultV1,
    HostOperationReceiptV1,
    CandidateCompletionResultV1,
)


__all__ = [model.__name__ for model in MACHINE_SCHEMA_MODELS] + [
    "MachineOperation",
    "MachineOutcome",
    "OperationKey",
    "RECEIPT_TOKEN_PATTERN",
    "ReceiptToken",
]
