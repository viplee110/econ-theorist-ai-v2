"""Sound, validator-backed navigation probes for the active route registry."""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from ..codec import canonical_json_bytes, sha256_digest
from ..context import compile_context
from ..framing_quality import (
    FramingQualityBundle,
    parse_framing_quality_entity,
)
from ..models import Actor, EntityVersion, EntityVersionRef, Snapshot
from ..policy import (
    KERNEL_HASH,
    ROUTE_REGISTRY_HASH,
    registry_hash_for_route,
    selector_version_for_route,
)
from ..profile_craft_policy import CRAFT_CORPUS_V1_HASH, PROFILE_CATALOG_V1_HASH
from ..route_registry import load_registry
from ..runs import RouteEntryError, validate_run_entry
from ..runtime.layout import StoreLayout
from ..theory import THEORY_PAYLOAD_MODELS
from .models import (
    DiagnosticV1,
    NavigationCandidateKeyV1,
    NavigationCandidateV1,
    NavigationPlanV1,
    ResumeDescriptorV1,
    RunInputBriefV1,
)
from .resources import NAVIGATION_REGISTRY_HASH, load_navigation_registry


class NavigationError(RuntimeError):
    """Navigation input or policy is incomplete or inconsistent."""


class NavigationUnsupported(NavigationError):
    """The bounded selector cannot prove complete enumeration."""


@dataclass(frozen=True, slots=True)
class CandidateEnumeration:
    focus_sets: tuple[tuple[str, ...], ...]
    truncated: bool = False


def _current_entities(snapshot: Snapshot) -> dict[str, EntityVersion]:
    return {
        entity.entity_id: entity
        for entity in snapshot.entity_versions
        if snapshot.current_entities.get(entity.entity_id) == entity.version
    }


def _bounded_product_count(counts: Sequence[int], limit: int) -> int:
    result = 1
    for count in counts:
        result *= count
        if result > limit:
            return result
    return result


def _registry_focus_sets(
    route: object,
    current: dict[str, EntityVersion],
    *,
    limit: int,
) -> CandidateEnumeration:
    requirements = tuple(getattr(route, "required_input_entities"))
    choices_by_requirement: list[tuple[tuple[str, ...], ...]] = []
    for requirement in requirements:
        pool = tuple(
            sorted(
                entity.entity_id
                for entity in current.values()
                if entity.entity_type == requirement.entity_type
            )
        )
        maximum = len(pool) if requirement.max_count is None else min(
            len(pool), requirement.max_count
        )
        if maximum < requirement.min_count:
            return CandidateEnumeration(())
        choices: list[tuple[str, ...]] = []
        for size in range(requirement.min_count, maximum + 1):
            choices.extend(itertools.combinations(pool, size))
            if len(choices) > limit:
                return CandidateEnumeration((), truncated=True)
        choices_by_requirement.append(tuple(choices))
    if not choices_by_requirement:
        return CandidateEnumeration(((),))
    if _bounded_product_count(
        tuple(len(items) for items in choices_by_requirement), limit
    ) > limit:
        return CandidateEnumeration((), truncated=True)
    focus_sets: list[tuple[str, ...]] = []
    for selection in itertools.product(*choices_by_requirement):
        flattened = tuple(sorted(itertools.chain.from_iterable(selection)))
        if len(set(flattened)) != len(flattened):
            continue
        focus_sets.append(flattened)
    return CandidateEnumeration(tuple(sorted(set(focus_sets))))


def _focus_sets_for_policy(
    selector_id: str,
    route: object,
    snapshot: Snapshot,
    current: dict[str, EntityVersion],
    *,
    limit: int,
) -> CandidateEnumeration:
    if selector_id == "empty_focus.v1":
        return CandidateEnumeration(((),))
    if selector_id == "registry_cardinality.v1":
        return _registry_focus_sets(route, current, limit=limit)
    if selector_id == "stale_current_typed_root.v1":
        ids = tuple(
            (entity.entity_id,)
            for entity in sorted(current.values(), key=lambda item: item.entity_id)
            if entity.entity_type in THEORY_PAYLOAD_MODELS
        )
        if len(ids) > limit:
            return CandidateEnumeration((), truncated=True)
        return CandidateEnumeration(ids)
    if selector_id == "framing_or_stale_repair_root.v1":
        focus_sets = {
            (entity.entity_id,)
            for entity in current.values()
            if entity.entity_type in THEORY_PAYLOAD_MODELS
        }
        for entity in current.values():
            if entity.entity_type != "FramingQualityBundle":
                continue
            payload = parse_framing_quality_entity(entity)
            if not isinstance(payload, FramingQualityBundle):
                continue
            for gap in payload.disclosed_gaps:
                for target in gap.repair_target_refs:
                    current_target = current.get(target.entity_ref.entity_id)
                    if (
                        payload.proposed_action == "revise_framing"
                        and current_target is not None
                        and current_target.version == target.entity_ref.version
                        and current_target.entity_type == target.entity_type
                    ):
                        focus_sets.add(
                            tuple(sorted((entity.entity_id, current_target.entity_id)))
                        )
        if len(focus_sets) > limit:
            return CandidateEnumeration((), truncated=True)
        return CandidateEnumeration(tuple(sorted(focus_sets)))
    raise NavigationUnsupported(f"unknown focus selector: {selector_id}")


def _diagnostic_code(message: str) -> str:
    lowered = message.lower()
    if "gate" in lowered or "decision" in lowered or "human" in lowered:
        return "human_decision_prerequisite"
    if "stale" in lowered or "fresh" in lowered or "current" in lowered:
        return "stale_or_invalid_prerequisite"
    if "budget" in lowered:
        return "context_budget_insufficient"
    if "privacy" in lowered or "compartment" in lowered:
        return "privacy_or_compartment_blocker"
    return "route_prerequisite_unsatisfied"


def _brief_hash(
    snapshot: Snapshot,
    actor: Actor,
    brief: RunInputBriefV1 | None,
) -> str | None:
    if brief is None:
        return None
    if brief.project_id != snapshot.project_id or brief.base_head != snapshot.head:
        raise NavigationError("run input brief is bound to a different project/head")
    if brief.actor_role != actor.actor_id:
        raise NavigationError("run input brief actor role differs from navigation actor")
    return sha256_digest(canonical_json_bytes(brief))


def enumerate_navigation_candidates(
    layout: StoreLayout,
    snapshot: Snapshot,
    *,
    actor: Actor,
    compartments: Iterable[str],
    privacy_clearance: str,
    budget_units: int | None = None,
    requested_route_ids: Iterable[str] | None = None,
    run_input_brief: RunInputBriefV1 | None = None,
) -> tuple[tuple[NavigationCandidateV1, ...], tuple[DiagnosticV1, ...]]:
    """Enumerate candidates and pass every one through the real entry boundary.

    Completeness is claimed only inside the explicit finite candidate cap in
    the pinned navigation registry.  Exceeding the cap raises
    :class:`NavigationUnsupported` rather than silently truncating.
    """

    if not isinstance(layout, StoreLayout) or not isinstance(snapshot, Snapshot):
        raise TypeError("layout and snapshot must be exact runtime objects")
    if budget_units is not None and budget_units < 1:
        raise NavigationError("context budget must be positive")
    compartment_tuple = tuple(compartments)
    if not compartment_tuple or len(set(compartment_tuple)) != len(compartment_tuple):
        raise NavigationError("compartments must be non-empty and unique")
    compartment_tuple = tuple(sorted(compartment_tuple))
    requested = None if requested_route_ids is None else tuple(requested_route_ids)
    if requested is not None and (not requested or len(set(requested)) != len(requested)):
        raise NavigationError("requested route IDs must be non-empty and unique")

    navigation = load_navigation_registry()
    active = load_registry()
    route_by_id = {
        route.route_id: route
        for route in active.routes
        if route.availability == "enabled"
    }
    policies = {policy.route_id: policy for policy in navigation.routes}
    selected_ids = tuple(route_by_id) if requested is None else requested
    unknown = sorted(set(selected_ids).difference(route_by_id))
    if unknown:
        raise NavigationUnsupported(
            "requested routes are unknown or unavailable: " + ", ".join(unknown)
        )
    missing_policy = sorted(set(selected_ids).difference(policies))
    if missing_policy:
        raise NavigationUnsupported(
            "routes lack navigation probes: " + ", ".join(missing_policy)
        )

    brief_digest = _brief_hash(snapshot, actor, run_input_brief)
    current = _current_entities(snapshot)
    candidates: list[NavigationCandidateV1] = []
    diagnostics: dict[tuple[str, str], DiagnosticV1] = {}
    for route_id in selected_ids:
        route = route_by_id[route_id]
        policy = policies[route_id]
        if route_id == "frame.question_and_benchmarks" and brief_digest is None:
            diagnostics[(route_id, "run_input_brief_required")] = DiagnosticV1(
                code="run_input_brief_required",
                severity="error",
                message="framing navigation requires an immutable host-neutral run input brief",
                details={"route_id": route_id},
            )
            continue
        enumeration = _focus_sets_for_policy(
            policy.selector_id,
            route,
            snapshot,
            current,
            limit=navigation.max_candidate_sets,
        )
        if enumeration.truncated:
            raise NavigationUnsupported(
                f"focus enumeration exceeds the tested cap for route {route_id}"
            )
        if not enumeration.focus_sets:
            diagnostics[(route_id, "missing_required_input_shape")] = DiagnosticV1(
                code="missing_required_input_shape",
                severity="info",
                message=f"route {route_id} has no candidate focus satisfying registry cardinality",
                details={"route_id": route_id},
            )
            continue
        for focus_ids in enumeration.focus_sets:
            effective_budget = budget_units or policy.default_budget_units
            try:
                validated_route, clearance = validate_run_entry(
                    snapshot,
                    route_id=route_id,
                    actor=actor,
                    purpose=policy.purpose,
                    compartments=compartment_tuple,
                    privacy_clearance=privacy_clearance,
                    focus_entity_ids=focus_ids,
                    route_registry_hash=ROUTE_REGISTRY_HASH,
                )
                compiled = compile_context(
                    snapshot,
                    route=validated_route,
                    actor=actor,
                    purpose=policy.purpose,
                    compartments=compartment_tuple,
                    privacy_clearance=clearance,
                    focus_entity_ids=focus_ids,
                    budget_units=effective_budget,
                    layout=layout,
                )
            except (RouteEntryError, RuntimeError, ValueError) as exc:
                message = str(exc)
                code = _diagnostic_code(message)
                diagnostics.setdefault(
                    (route_id, code),
                    DiagnosticV1(
                        code=code,
                        severity="info",
                        message=f"route {route_id} is not currently enterable: {message}",
                        details={"route_id": route_id},
                    ),
                )
                continue
            refs = tuple(
                EntityVersionRef(
                    entity_id=entity_id, version=current[entity_id].version
                )
                for entity_id in focus_ids
            )
            key = NavigationCandidateKeyV1(
                base_head=snapshot.head,
                route_id=route_id,
                route_version=validated_route.route_version,
                purpose=policy.purpose,
                actor=actor,
                compartments=compartment_tuple,
                privacy_clearance=clearance,
                focus_refs=refs,
                context_budget=effective_budget,
                context_hash=sha256_digest(compiled.encoded),
                route_registry_hash=registry_hash_for_route(validated_route),
                instruction_bundle_hash=validated_route.instruction_bundle_hash,
                context_selector_version=selector_version_for_route(validated_route),
                navigation_registry_hash=NAVIGATION_REGISTRY_HASH,
                policy_hashes={
                    "kernel": KERNEL_HASH,
                    "profile_catalog": PROFILE_CATALOG_V1_HASH,
                    "craft_corpus": CRAFT_CORPUS_V1_HASH,
                },
                run_input_brief_hash=brief_digest,
            )
            candidates.append(
                NavigationCandidateV1(
                    candidate_digest=sha256_digest(canonical_json_bytes(key)),
                    key=key,
                    explanation=(
                        f"Exact {route_id} focus passed registry authorization, "
                        "the authoritative entry validator, privacy selection, and context compilation."
                    ),
                )
            )
            if len(candidates) > navigation.max_candidate_sets:
                raise NavigationUnsupported("legal navigation candidate set exceeds cap")
    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.key.route_id,
                tuple((ref.entity_id, ref.version) for ref in item.key.focus_refs),
                item.candidate_digest,
            ),
        )
    )
    return ordered, tuple(diagnostics[key] for key in sorted(diagnostics))


def plan_next(
    layout: StoreLayout,
    snapshot: Snapshot,
    *,
    actor: Actor,
    compartments: Iterable[str],
    privacy_clearance: str,
    budget_units: int | None = None,
    requested_route_ids: Iterable[str] | None = None,
    run_input_brief: RunInputBriefV1 | None = None,
    active_run_ids: Iterable[str] = (),
    resume_descriptors: Iterable[ResumeDescriptorV1] = (),
    repair_run_ids: Iterable[str] = (),
    complete_if_none: bool = False,
) -> NavigationPlanV1:
    repair = tuple(sorted(set(repair_run_ids)))
    if repair:
        return NavigationPlanV1(
            outcome="repair_required",
            project_id=snapshot.project_id,
            base_head=snapshot.head,
            active_run_ids=repair,
            blockers=(
                DiagnosticV1(
                    code="incomplete_run_requires_repair",
                    severity="error",
                    message=(
                        "incomplete run evidence is stale, conflicting, or invalid; "
                        "repair or explicit disposition is required"
                    ),
                    details={"route_run_ids": repair},
                ),
            ),
        )
    descriptors = tuple(
        sorted(resume_descriptors, key=lambda item: item.route_run_id)
    )
    descriptor_ids = tuple(item.route_run_id for item in descriptors)
    active = tuple(sorted(set(active_run_ids)))
    if descriptor_ids != active:
        raise NavigationError(
            "resume descriptors differ from the active unfinished-run set"
        )
    if active:
        return NavigationPlanV1(
            outcome="resume_required" if len(active) == 1 else "ambiguous_next",
            project_id=snapshot.project_id,
            base_head=snapshot.head,
            active_run_ids=active,
            resume_descriptors=descriptors,
            blockers=(
                DiagnosticV1(
                    code="incomplete_run_owns_navigation",
                    severity="error",
                    message="an incomplete run must be resumed or explicitly repaired before opening another",
                    details={"route_run_ids": active},
                ),
            ),
        )
    try:
        candidates, diagnostics = enumerate_navigation_candidates(
            layout,
            snapshot,
            actor=actor,
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            budget_units=budget_units,
            requested_route_ids=requested_route_ids,
            run_input_brief=run_input_brief,
        )
    except NavigationUnsupported as exc:
        return NavigationPlanV1(
            outcome="navigation_unsupported",
            project_id=snapshot.project_id,
            base_head=snapshot.head,
            blockers=(
                DiagnosticV1(
                    code="navigation_unsupported",
                    severity="error",
                    message=str(exc),
                ),
            ),
        )
    if len(candidates) == 1:
        outcome = "unique_next"
    elif len(candidates) > 1:
        outcome = "ambiguous_next"
    elif any(item.code == "human_decision_prerequisite" for item in diagnostics):
        outcome = "human_decision_required"
    elif complete_if_none:
        outcome = "complete_for_requested_scope"
    else:
        outcome = "repair_required"
    return NavigationPlanV1(
        outcome=outcome,
        project_id=snapshot.project_id,
        base_head=snapshot.head,
        candidates=candidates,
        blockers=diagnostics,
    )


__all__ = [
    "NavigationError",
    "NavigationUnsupported",
    "enumerate_navigation_candidates",
    "plan_next",
]
