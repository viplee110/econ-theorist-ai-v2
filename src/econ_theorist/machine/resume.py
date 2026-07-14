"""Read-only reconstruction of exact unfinished-run resume inputs."""

from __future__ import annotations

import re
from pathlib import Path

from ..codec import canonical_json_bytes
from ..errors import RuntimeStoreError
from ..runtime.layout import StoreLayout, UnsafeStorePath, assert_safe_store_path
from .models import (
    NavigationCandidateV1,
    ResumeDescriptorV1,
    RunExecutionViewV1,
)
from .operational import OperationalError, ProjectOperationalLayout
from .resources import NAVIGATION_REGISTRY_HASH
from .packets import (
    WorkPacketBindingV1,
    read_run_input_brief,
    read_work_packet,
)


_SAFE_RUN_ID = re.compile(r"[a-z0-9._-]+")


class ResumeDescriptorError(OperationalError):
    """An unfinished run lacks one exact, trustworthy resume binding."""


def _read_exact_model(
    anchor: Path,
    path: Path,
    model: type[NavigationCandidateV1] | type[WorkPacketBindingV1],
) -> NavigationCandidateV1 | WorkPacketBindingV1:
    try:
        assert_safe_store_path(
            anchor, path, expected="file", allow_missing=False
        )
        data = path.read_bytes()
        value = model.model_validate_json(data, strict=True)
    except (OSError, ValueError, UnsafeStorePath) as exc:
        raise ResumeDescriptorError(
            f"resume binding is unavailable or invalid: {path}"
        ) from exc
    if canonical_json_bytes(value) != data:
        raise ResumeDescriptorError(
            f"resume binding is not canonical JSON: {path}"
        )
    return value


def derive_resume_descriptor(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    view: RunExecutionViewV1,
) -> ResumeDescriptorV1:
    """Recover the complete immutable request input for one current run.

    This function is deliberately read-only.  It verifies every persisted
    navigation, input, packet, and logical-path binding before exposing the
    descriptor to a new host process.
    """

    route_run_id = view.route_run_id
    if (
        _SAFE_RUN_ID.fullmatch(route_run_id) is None
        or view.integrity != "valid"
        or view.base_freshness != "current"
        or view.lifecycle not in {"opened", "candidate_present", "staged"}
    ):
        raise ResumeDescriptorError("run execution view is not safely resumable")

    root = operational.runs / route_run_id
    try:
        candidate = _read_exact_model(
            operational.project_root,
            root / "navigation-candidate.json",
            NavigationCandidateV1,
        )
        assert isinstance(candidate, NavigationCandidateV1)
        if candidate.key.navigation_registry_hash != NAVIGATION_REGISTRY_HASH:
            raise ResumeDescriptorError(
                "unfinished run uses an inactive navigation policy and requires inspection"
            )
        packet_binding = _read_exact_model(
            operational.project_root,
            root / "packet-binding.json",
            WorkPacketBindingV1,
        )
        assert isinstance(packet_binding, WorkPacketBindingV1)
        packet = read_work_packet(
            operational, route_run_id, packet_binding.work_packet_hash
        )
        brief = read_run_input_brief(operational, route_run_id, candidate)
    except (OSError, ValueError, RuntimeStoreError, UnsafeStorePath) as exc:
        if isinstance(exc, ResumeDescriptorError):
            raise
        raise ResumeDescriptorError(
            f"cannot reconstruct unfinished run {route_run_id}"
        ) from exc

    key = candidate.key
    if (
        packet_binding.route_run_id != route_run_id
        or packet_binding.navigation_candidate_digest
        != candidate.candidate_digest
        or packet.route_run_id != route_run_id
        or packet.navigation_candidate_digest != candidate.candidate_digest
        or packet.base_head != key.base_head
        or packet.route_id != key.route_id
        or packet.route_version != key.route_version
        or packet.purpose != key.purpose
        or packet.actor_role != key.actor.actor_id
        or packet.focus_refs != key.focus_refs
        or packet.route_registry_hash != key.route_registry_hash
        or packet.instruction_bundle_hash != key.instruction_bundle_hash
        or packet.context_selector_version != key.context_selector_version
        or packet.policy_hashes != key.policy_hashes
        or packet.privacy_clearance != key.privacy_clearance
        or packet.compartments != key.compartments
        or packet.compiled_context_hash != key.context_hash
        or packet.run_input_brief_hash != key.run_input_brief_hash
        or packet.run_input != brief
        or view.base_head != key.base_head
    ):
        raise ResumeDescriptorError(
            "persisted navigation candidate and WorkPacket bindings disagree"
        )

    return ResumeDescriptorV1(
        route_run_id=route_run_id,
        lifecycle=view.lifecycle,
        navigation_candidate=candidate,
        run_input_brief=brief,
        work_packet_hash=packet_binding.work_packet_hash,
        candidate_logical_path=packet.candidate_logical_path,
    )


__all__ = ["ResumeDescriptorError", "derive_resume_descriptor"]
