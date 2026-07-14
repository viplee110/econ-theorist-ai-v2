"""Host-neutral input briefs and deterministic scientific work packets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from .. import __version__
from ..codec import canonical_json_bytes, sha256_digest
from ..models import EntityVersionRef, StrictModel
from ..policy import instruction_bundle_bytes, selector_version_for_route
from ..route_registry import get_route
from ..runs import read_compiled_context, read_context, read_run
from ..runtime.layout import StoreLayout
from ..runtime.layout import assert_safe_store_path
from .models import (
    NavigationCandidateV1,
    RunInputBriefV1,
    WorkPacketV1,
)
from .operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
    write_immutable_operational,
)
from .resources import NAVIGATION_REGISTRY_HASH


_HIDDEN_COMPARTMENTS_BY_ROUTE: dict[str, tuple[str, ...]] = {
    "prepare.blind_case": (
        "blind_generator_workspace",
        "unsealed_evaluator_runtime",
    ),
    "evaluate.blind_argument_package": (
        "blind_generator_workspace",
        "generator_model_memory",
    ),
    "verify.independent_rederivation": (
        "originating_proof_narrative",
        "verifier_persuasion_context",
    ),
    "answer.reader_probe": (
        "reader_answer_key",
        "authoring_rationale",
        "other_reviews",
        "reader_adjudicator_context",
    ),
}


class RunInputBindingV1(StrictModel):
    binding_schema: Literal["econ-theorist/run-input-binding/v1"] = (
        "econ-theorist/run-input-binding/v1"
    )
    route_run_id: str
    navigation_candidate_digest: str
    run_input_brief_hash: str


class WorkPacketBindingV1(StrictModel):
    binding_schema: Literal["econ-theorist/work-packet-binding/v1"] = (
        "econ-theorist/work-packet-binding/v1"
    )
    route_run_id: str
    navigation_candidate_digest: str
    work_packet_hash: str


def _run_operational_root(
    operational: ProjectOperationalLayout, route_run_id: str
) -> Path:
    if not route_run_id or any(
        character not in "abcdefghijklmnopqrstuvwxyz0123456789._-"
        for character in route_run_id
    ):
        raise OperationalError(f"unsafe operational run ID: {route_run_id!r}")
    return operational.runs / route_run_id


def bind_run_input_brief(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    candidate: NavigationCandidateV1,
    brief: RunInputBriefV1,
) -> str:
    """Install an immutable brief and its exact run/candidate binding."""

    operational.ensure()
    root = _run_operational_root(operational, route_run_id)
    store = ContentAddressedOperationalStore(operational.project_root, root)
    digest, _ = store.install("input-briefs", brief)
    if candidate.key.run_input_brief_hash != digest:
        raise OperationalError("navigation candidate does not bind this input brief")
    binding = RunInputBindingV1(
        route_run_id=route_run_id,
        navigation_candidate_digest=candidate.candidate_digest,
        run_input_brief_hash=digest,
    )
    write_immutable_operational(
        operational.project_root,
        root / "input-binding.json",
        canonical_json_bytes(binding),
    )
    return digest


def _read_binding(
    anchor: Path, path: Path, model: type[StrictModel]
) -> StrictModel:
    try:
        assert_safe_store_path(
            anchor, path, expected="file", allow_missing=False
        )
        data = path.read_bytes()
        value = model.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise OperationalError(f"invalid run operational binding: {path}") from exc
    if canonical_json_bytes(value) != data:
        raise OperationalError(f"run operational binding is not canonical: {path}")
    return value


def read_run_input_brief(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    candidate: NavigationCandidateV1,
) -> RunInputBriefV1 | None:
    expected = candidate.key.run_input_brief_hash
    if expected is None:
        return None
    root = _run_operational_root(operational, route_run_id)
    binding = _read_binding(
        operational.project_root,
        root / "input-binding.json",
        RunInputBindingV1,
    )
    assert isinstance(binding, RunInputBindingV1)
    if (
        binding.route_run_id != route_run_id
        or binding.navigation_candidate_digest != candidate.candidate_digest
        or binding.run_input_brief_hash != expected
    ):
        raise OperationalError("run input binding differs from the navigation candidate")
    store = ContentAddressedOperationalStore(operational.project_root, root)
    data = store.read_bytes("input-briefs", expected)
    try:
        brief = RunInputBriefV1.model_validate_json(data, strict=True)
    except ValueError as exc:
        raise OperationalError("stored run input brief is invalid") from exc
    if canonical_json_bytes(brief) != data:
        raise OperationalError("stored run input brief is not canonical")
    return brief


def compile_work_packet(
    layout: StoreLayout,
    operational: ProjectOperationalLayout,
    candidate: NavigationCandidateV1,
    route_run_id: str,
) -> tuple[str, WorkPacketV1]:
    """Compile and persist the exact deterministic packet for one current run."""

    run = read_run(layout, route_run_id)
    manifest = read_context(layout, route_run_id)
    compiled = read_compiled_context(layout, route_run_id)
    key = candidate.key
    current_refs = tuple(
        EntityVersionRef(entity_id=item.entity_id, version=item.version)
        for item in key.focus_refs
    )
    if (
        candidate.candidate_digest != sha256_digest(canonical_json_bytes(key))
        or run.project_id != manifest.project_id
        or run.base_revision != key.base_head
        or run.route_id != key.route_id
        or run.route_version != key.route_version
        or run.purpose != key.purpose
        or run.actor != key.actor
        or run.compartments != key.compartments
        or run.privacy_clearance != key.privacy_clearance
        or run.focus_entity_ids != tuple(item.entity_id for item in current_refs)
        or run.context_hash != key.context_hash
        or manifest.budget_units != key.context_budget
        or manifest.route_registry_hash != key.route_registry_hash
        or manifest.instruction_bundle_hash != key.instruction_bundle_hash
        or manifest.selector_version != key.context_selector_version
        or key.navigation_registry_hash != NAVIGATION_REGISTRY_HASH
    ):
        raise OperationalError("run/context differs from the navigation candidate key")
    route = get_route(
        run.route_id, route_registry_hash=manifest.route_registry_hash
    )
    if selector_version_for_route(route) != key.context_selector_version:
        raise OperationalError("route selector policy differs from candidate key")
    brief = read_run_input_brief(operational, route_run_id, candidate)
    if brief is not None and (
        brief.project_id != run.project_id
        or brief.base_head != run.base_revision
        or brief.actor_role != run.actor.actor_id
    ):
        raise OperationalError("run input brief differs from the immutable run")
    run_bytes = canonical_json_bytes(run)
    manifest_bytes = canonical_json_bytes(manifest)
    compiled_bytes = canonical_json_bytes(compiled)
    if sha256_digest(compiled_bytes) != run.context_hash:
        raise OperationalError("compiled context re-encoding differs from context hash")
    output_entities = tuple(
        requirement.entity_type for requirement in route.required_output_entities
    )
    output_relations = tuple(
        requirement.relation_type for requirement in route.required_output_relations
    )
    from .bootstrap import current_engine_semantics_hash

    packet = WorkPacketV1(
        engine_version=__version__,
        engine_semantics_hash=current_engine_semantics_hash(),
        project_id=run.project_id,
        base_head=run.base_revision,
        route_run_id=route_run_id,
        route_run_hash=sha256_digest(run_bytes),
        context_manifest_hash=sha256_digest(manifest_bytes),
        compiled_context_hash=sha256_digest(compiled_bytes),
        run_input_brief_hash=key.run_input_brief_hash,
        navigation_candidate_digest=candidate.candidate_digest,
        route_id=run.route_id,
        route_version=run.route_version,
        purpose=run.purpose,
        actor_role=run.actor.actor_id,
        focus_refs=current_refs,
        route_registry_hash=manifest.route_registry_hash,
        instruction_bundle_hash=manifest.instruction_bundle_hash,
        context_selector_version=manifest.selector_version,
        policy_hashes=key.policy_hashes,
        privacy_clearance=run.privacy_clearance,
        compartments=run.compartments,
        instruction_text=instruction_bundle_bytes(route).decode("utf-8"),
        compiled_context=compiled,
        run_input=brief,
        omissions=manifest.omissions,
        hidden_compartments=_HIDDEN_COMPARTMENTS_BY_ROUTE.get(run.route_id, ()),
        pending_human_gate_refs=(),
        candidate_logical_path=(
            f".econ-theorist/staging/{route_run_id}/candidate.json"
        ),
        shadow_logical_root=(
            f".econ-theorist/operational/v1/runs/{route_run_id}/shadow"
        ),
        allowed_operation_classes=route.allowed_operations,
        required_output_entity_types=output_entities,
        required_output_relation_types=output_relations,
        forbidden_actions=(
            "canonical_store_direct_write",
            "human_decision_fabrication",
            "human_owned_artifact_overwrite",
            "undeclared_cross_project_read",
            "undeclared_agent_delegation",
        ),
    )
    root = _run_operational_root(operational, route_run_id)
    store = ContentAddressedOperationalStore(operational.project_root, root)
    packet_hash, _ = store.install("packets", packet)
    binding = WorkPacketBindingV1(
        route_run_id=route_run_id,
        navigation_candidate_digest=candidate.candidate_digest,
        work_packet_hash=packet_hash,
    )
    write_immutable_operational(
        operational.project_root,
        root / "packet-binding.json",
        canonical_json_bytes(binding),
    )
    return packet_hash, packet


def read_work_packet(
    operational: ProjectOperationalLayout,
    route_run_id: str,
    packet_hash: str,
) -> WorkPacketV1:
    root = _run_operational_root(operational, route_run_id)
    store = ContentAddressedOperationalStore(operational.project_root, root)
    data = store.read_bytes("packets", packet_hash)
    try:
        packet = WorkPacketV1.model_validate_json(data, strict=True)
    except ValueError as exc:
        raise OperationalError("stored work packet is invalid") from exc
    if canonical_json_bytes(packet) != data or packet.route_run_id != route_run_id:
        raise OperationalError("stored work packet binding is invalid")
    return packet


__all__ = [
    "bind_run_input_brief",
    "compile_work_packet",
    "read_run_input_brief",
    "read_work_packet",
]
