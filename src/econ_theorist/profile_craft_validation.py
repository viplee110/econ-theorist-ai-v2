"""Semantic and route validation for the additive Phase 4 profile/craft slice.

``profile_craft`` owns strict payload shape.  This module resolves those
payloads against one exact snapshot, preserves the frozen Phase 1--3 object
contracts, and derives profile/craft readiness without turning a target or a
craft card into scientific authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from pydantic import BaseModel

from . import authoring as a
from . import profile_craft as pc
from . import theory as t
from .authoring_validation import (
    AuthoringValidationError,
    FacetPathError,
    facet_semantic_hash,
    validate_authoring_entity,
    validate_authoring_projection,
    validate_authoring_ready,
)
from .codec import object_digest
from .models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    BlockerRef,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    RecordBlockerOp,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    RelationVersion,
    RelationVersionRef,
    RouteSpecV4,
    Snapshot,
    SupersedeEntityOp,
    SupersedeRelationOp,
    Transaction,
)
from .profile_craft_policy import (
    ProfileCraftPolicyError,
    load_craft_corpus,
    load_profile_catalog,
    resolve_profile_stack,
    select_craft_moves,
)


PROFILE_CRAFT_READY_VERSION = "PROFILE-CRAFT-READY-0.1"

_PHASE4_ROUTES = frozenset(
    {
        "map.obligation_predicate",
        "audit.obligation_predicate",
        "resolve.profile_stack",
        "diagnose.reader_problem",
        "retrieve.craft_moves",
        "compose.profiled_manuscript_unit",
        "review.craft_realization",
        "close.profile_craft_review",
    }
)

_MANDATORY_TARGET_DECISIONS: Mapping[str, str] = {
    "theory_mode": "theory_mode",
    "ambition": "ambition",
    "field": "field_key",
    "audience": "primary_audience",
}

_AUTHORITY_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3}

_SCIENTIFIC_FINDING_CATEGORIES = frozenset(
    {
        "formal_fidelity",
        "scope",
        "assumption",
        "proof_language",
    }
)
_FORMAL_REPAIR_ACTIONS = frozenset(
    {"correct_formal_expression", "narrow_scope", "restore_assumption"}
)
_UPSTREAM_ROUTE_BY_CAUSAL_CLASS: Mapping[str, str | None] = {
    "initial_planning": "design.reader_path",
    "local_exposition": None,
    "reader_path_design": "design.reader_path",
    "target_profile_mismatch": "resolve.profile_stack",
    "scientific_content": "repair.dependency",
}

_REVIEW_SIGNAL_ORDER = (
    "formal_fidelity",
    "scope_and_assumptions",
    "bounded_evidentiary_language",
    "economic_explanation",
    "cold_reader_transfer",
)



class ProfileCraftValidationError(ValueError):
    """A structurally valid Phase 4 value is semantically inadmissible."""


@dataclass(frozen=True)
class ProfileCraftProjectionReport:
    parsed_entity_count: int
    ready_closure_refs: tuple[EntityVersionRef, ...]


@dataclass(frozen=True)
class ProfileCraftRouteEntryReport:
    route_id: str
    input_entity_refs: tuple[EntityVersionRef, ...]
    actor: Actor


@dataclass(frozen=True)
class _Indices:
    entities: Mapping[tuple[str, int], EntityVersion]
    artifacts: Mapping[tuple[str, int], ArtifactRegistration]
    decisions: Mapping[tuple[str, int], Decision]
    profile_payloads: Mapping[tuple[str, int], pc.ProfileCraftPayload]
    authoring_payloads: Mapping[tuple[str, int], a.AuthoringPayload]
    theory_payloads: Mapping[tuple[str, int], t.TheoryPayload]
    static_resources: Mapping[pc.StaticResourceRef, object]


def _entity_key(value: EntityVersion | EntityVersionRef) -> tuple[str, int]:
    return value.entity_id, value.version


def _artifact_key(
    value: ArtifactRegistration | ArtifactDependencyRef,
) -> tuple[str, int]:
    return value.artifact_id, value.version


def _decision_key(value: Decision | DecisionVersionRef) -> tuple[str, int]:
    return value.decision_id, value.version


def _relation_key(value: RelationVersion | RelationVersionRef) -> tuple[str, int]:
    return value.relation_id, value.version


def _exact_ref_key(value: object) -> tuple[object, ...]:
    if isinstance(value, EntityVersionRef):
        return "entity", value.entity_id, value.version
    if isinstance(value, ArtifactDependencyRef):
        return "artifact", value.artifact_id, value.version, value.content_hash
    if isinstance(value, DecisionVersionRef):
        return "decision", value.decision_id, value.version
    if isinstance(value, RelationVersionRef):
        return "relation", value.relation_id, value.version
    if isinstance(value, BlockerRef):
        return "blocker", value.blocker_id
    raise TypeError(f"unsupported exact reference: {type(value).__name__}")


def _walk_artifact_refs(value: object) -> Iterable[ArtifactDependencyRef]:
    if isinstance(value, ArtifactDependencyRef):
        yield value
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from _walk_artifact_refs(getattr(value, field_name))
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _walk_artifact_refs(nested)
        return
    if isinstance(value, (tuple, list, set, frozenset)):
        for nested in value:
            yield from _walk_artifact_refs(nested)


def _payload_hash(payload: BaseModel) -> str:
    return object_digest(payload)


def _actor_key(value: Actor) -> tuple[str, str]:
    return value.kind, value.actor_id


def _entity_ref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def _owner_facet(entity_type: str) -> str | None:
    return (
        pc.PROFILE_CRAFT_PAYLOAD_OWNER_FACETS.get(entity_type)
        or a.AUTHORING_PAYLOAD_OWNER_FACETS.get(entity_type)
        or t.THEORY_PAYLOAD_OWNER_FACETS.get(entity_type)
    )


def _is_current_and_fresh(snapshot: Snapshot, entity: EntityVersion) -> bool:
    if snapshot.current_entities.get(entity.entity_id) != entity.version:
        return False
    owner = _owner_facet(entity.entity_type)
    status = snapshot.derived_status.get(entity.entity_id)
    return (
        status is None
        or owner is None
        or status.freshness.get(owner, "fresh") == "fresh"
    )


def validate_profile_craft_entity(
    entity: EntityVersion, previous: EntityVersion | None = None
) -> pc.ProfileCraftPayload:
    """Parse one independent envelope and expose every exact artifact ref."""

    if entity.entity_type not in pc.PROFILE_CRAFT_PAYLOAD_MODELS:
        raise ProfileCraftValidationError(
            f"unregistered Phase 4 entity_type: {entity.entity_type}"
        )
    if not pc.is_packed_profile_craft_entity(entity):
        raise ProfileCraftValidationError(
            f"{entity.entity_type} is not a canonical profile/craft envelope"
        )
    try:
        payload = pc.parse_profile_craft_entity(entity)
    except (TypeError, ValueError) as exc:
        raise ProfileCraftValidationError(str(exc)) from exc

    exposed = frozenset(entity.artifact_refs)
    referenced = frozenset(_walk_artifact_refs(payload))
    if exposed != referenced:
        raise ProfileCraftValidationError(
            f"{entity.entity_type} envelope must expose every and only exact artifact dependency"
        )
    if previous is None:
        if entity.version != 1:
            raise ProfileCraftValidationError(
                "a profile/craft history cannot omit its exact predecessor"
            )
        return payload
    if (
        previous.entity_id != entity.entity_id
        or previous.entity_type != entity.entity_type
        or previous.version + 1 != entity.version
        or entity.supersedes != _entity_ref(previous)
    ):
        raise ProfileCraftValidationError(
            "profile/craft supersession has the wrong predecessor"
        )
    raise ProfileCraftValidationError(
        "profile/craft payloads are immutable; create a new exact entity"
    )


def _add_static(
    target: dict[pc.StaticResourceRef, object], resource: object
) -> None:
    reference = pc.static_resource_ref(resource)
    previous = target.get(reference)
    if previous is not None and _payload_hash(previous) != _payload_hash(resource):
        raise ProfileCraftValidationError(
            "one static resource ref resolves to conflicting content"
        )
    target[reference] = resource


def _static_resources(
    payloads: Iterable[pc.ProfileCraftPayload],
) -> Mapping[pc.StaticResourceRef, object]:
    result: dict[pc.StaticResourceRef, object] = {}
    try:
        pinned_resources: tuple[pc.ProfileCraftPayload, ...] = (
            load_profile_catalog(),
            load_craft_corpus(),
        )
    except ProfileCraftPolicyError as exc:
        raise ProfileCraftValidationError(
            "cannot load the pinned Phase 4 profile/craft resources"
        ) from exc

    # Catalogs and corpora are package-pinned policy resources, not project
    # entities or route inputs.  Project payloads may additionally expose an
    # exact custom resource (and selection audits embed candidate moves), but
    # the ordinary route path resolves against these releases without copying
    # the releases into every Snapshot.
    for payload in (*pinned_resources, *payloads):
        if isinstance(
            payload,
            (
                pc.ProfileLayerCard,
                pc.ProfileCatalogRelease,
                pc.CraftSourceCard,
                pc.CraftMove,
                pc.CraftCorpusRelease,
            ),
        ):
            _add_static(result, payload)
        if isinstance(payload, pc.ProfileCatalogRelease):
            for card in payload.cards:
                _add_static(result, card)
        if isinstance(payload, pc.CraftCorpusRelease):
            for source in payload.source_cards:
                _add_static(result, source)
            for move in payload.moves:
                _add_static(result, move)
        if isinstance(payload, pc.CraftSelectionManifest):
            for candidate in payload.candidates:
                _add_static(result, candidate.move)
    return result


def _build_indices(snapshot: Snapshot) -> _Indices:
    entities = {_entity_key(item): item for item in snapshot.entity_versions}
    artifacts = {_artifact_key(item): item for item in snapshot.artifacts}
    decisions = {_decision_key(item): item for item in snapshot.decisions}
    profile_payloads: dict[tuple[str, int], pc.ProfileCraftPayload] = {}
    authoring_payloads: dict[tuple[str, int], a.AuthoringPayload] = {}
    theory_payloads: dict[tuple[str, int], t.TheoryPayload] = {}

    histories: dict[str, EntityVersion] = {}
    for entity in sorted(snapshot.entity_versions, key=lambda item: (item.entity_id, item.version)):
        if entity.entity_type in pc.PROFILE_CRAFT_PAYLOAD_MODELS:
            previous = histories.get(entity.entity_id)
            payload = validate_profile_craft_entity(entity, previous)
            histories[entity.entity_id] = entity
            profile_payloads[_entity_key(entity)] = payload
        elif a.is_packed_authoring_entity(entity):
            try:
                authoring_payloads[_entity_key(entity)] = a.parse_authoring_entity(entity)
            except (TypeError, ValueError) as exc:
                raise ProfileCraftValidationError(str(exc)) from exc
        elif t.is_packed_theory_entity(entity):
            try:
                theory_payloads[_entity_key(entity)] = t.parse_theory_entity(entity)
            except (TypeError, ValueError) as exc:
                raise ProfileCraftValidationError(str(exc)) from exc

    for entity_key, payload in profile_payloads.items():
        entity = entities[entity_key]
        for reference in _walk_artifact_refs(payload):
            registration = artifacts.get(_artifact_key(reference))
            if registration is None or registration.content_hash != reference.content_hash:
                raise ProfileCraftValidationError(
                    f"unresolved profile/craft artifact {reference.artifact_id}@{reference.version}"
                )
            if registration.project_id != entity.project_id:
                raise ProfileCraftValidationError(
                    "profile/craft artifact crosses the project boundary"
                )

    return _Indices(
        entities=entities,
        artifacts=artifacts,
        decisions=decisions,
        profile_payloads=profile_payloads,
        authoring_payloads=authoring_payloads,
        theory_payloads=theory_payloads,
        static_resources=_static_resources(profile_payloads.values()),
    )


def _resolve_profile(
    indices: _Indices,
    reference: EntityVersionRef,
    expected: type[pc.ProfileCraftPayload],
    label: str,
) -> pc.ProfileCraftPayload:
    payload = indices.profile_payloads.get(_entity_key(reference))
    if not isinstance(payload, expected):
        raise ProfileCraftValidationError(
            f"{label} must resolve to exact {expected.__name__}"
        )
    return payload


def _resolve_authoring(
    indices: _Indices,
    reference: EntityVersionRef,
    expected: type[a.AuthoringPayload],
    label: str,
) -> a.AuthoringPayload:
    payload = indices.authoring_payloads.get(_entity_key(reference))
    if not isinstance(payload, expected):
        raise ProfileCraftValidationError(
            f"{label} must resolve to exact {expected.__name__}"
        )
    return payload


def _resolve_theory(
    indices: _Indices,
    reference: EntityVersionRef,
    expected: type[t.TheoryPayload],
    label: str,
) -> t.TheoryPayload:
    payload = indices.theory_payloads.get(_entity_key(reference))
    if not isinstance(payload, expected):
        raise ProfileCraftValidationError(
            f"{label} must resolve to exact {expected.__name__}"
        )
    return payload


def _resolve_static(
    indices: _Indices,
    reference: pc.StaticResourceRef,
    expected: type[object],
    label: str,
) -> object:
    resource = indices.static_resources.get(reference)
    if resource is None or not isinstance(resource, expected):
        raise ProfileCraftValidationError(
            f"{label} does not resolve to its exact static resource"
        )
    return resource


def _decision_is_effective(snapshot: Snapshot, reference: DecisionVersionRef) -> bool:
    return any(
        value.decision_id == reference.decision_id
        and value.version == reference.version
        for value in snapshot.effective_decisions.values()
    )


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))


def _semantic_source_entity(
    indices: _Indices,
    reference: object,
    *,
    label: str,
) -> EntityVersion:
    entity_id = getattr(reference, "entity_id", None)
    version = getattr(reference, "version", None)
    facet = getattr(reference, "facet", None)
    field_path = getattr(reference, "field_path", None)
    semantic_hash = getattr(reference, "semantic_hash", None)
    entity = indices.entities.get((entity_id, version))
    if entity is None:
        raise ProfileCraftValidationError(f"{label} source entity is unresolved")
    owner = _owner_facet(entity.entity_type)
    if owner is None or facet != owner or field_path is None:
        raise ProfileCraftValidationError(
            f"{label} must bind a field in the source entity's owner facet"
        )
    try:
        actual_hash = facet_semantic_hash(entity, facet, field_path)
    except FacetPathError as exc:
        raise ProfileCraftValidationError(f"{label} field path is invalid") from exc
    if actual_hash != semantic_hash:
        raise ProfileCraftValidationError(f"{label} semantic hash is stale or forged")
    return entity


def _expected_causal_class(
    findings: Sequence[a.ReviewFinding],
    instructions: Sequence[a.RevisionInstruction],
) -> str:
    if any(
        finding.blocking and finding.category in _SCIENTIFIC_FINDING_CATEGORIES
        for finding in findings
    ) or any(
        instruction.blocking and instruction.action in _FORMAL_REPAIR_ACTIONS
        for instruction in instructions
    ):
        return "scientific_content"
    if any(
        instruction.blocking and instruction.action == "request_human_decision"
        for instruction in instructions
    ):
        return "target_profile_mismatch"
    if any(
        instruction.blocking and instruction.action == "repair_reader_path"
        for instruction in instructions
    ):
        return "reader_path_design"
    return "local_exposition"


def validate_target_profile(
    snapshot: Snapshot,
    target: pc.TargetProfile,
    *,
    require_current: bool,
    indices: _Indices | None = None,
) -> None:
    """Bind every selected target dimension to exact human L2 authority."""

    resolved = indices or _build_indices(snapshot)
    package = _resolve_theory(
        resolved,
        target.package_ref,
        t.ValidatedArgumentPackage,
        "TargetProfile package",
    )
    if target.package_hash != _payload_hash(package):
        raise ProfileCraftValidationError("TargetProfile package_hash is not exact")
    paper = _resolve_authoring(
        resolved,
        target.paper_ir_ref,
        a.PaperIR,
        "TargetProfile PaperIR",
    )
    reader = _resolve_authoring(
        resolved,
        target.reader_path_ref,
        a.ReaderPath,
        "TargetProfile ReaderPath",
    )
    minimal = _resolve_authoring(
        resolved,
        target.base_profile_manifest_ref,
        a.ResolvedProfileManifest,
        "TargetProfile Phase 3 profile manifest",
    )
    assert isinstance(paper, a.PaperIR)
    assert isinstance(reader, a.ReaderPath)
    assert isinstance(minimal, a.ResolvedProfileManifest)
    if (
        target.paper_ir_hash != _payload_hash(paper)
        or target.reader_path_hash != _payload_hash(reader)
        or target.base_profile_manifest_hash != _payload_hash(minimal)
    ):
        raise ProfileCraftValidationError(
            "TargetProfile project payload hashes are not exact"
        )
    if (
        paper.package_ref != target.package_ref
        or paper.resolved_profile_manifest_ref
        != target.base_profile_manifest_ref
        or reader.paper_ir_ref != target.paper_ir_ref
    ):
        raise ProfileCraftValidationError(
            "TargetProfile crosses its exact package/PaperIR/ReaderPath/profile lineage"
        )
    if (
        target.theory_mode != minimal.theory_mode
        or target.primary_archetype != minimal.primary_result_archetype
    ):
        raise ProfileCraftValidationError(
            "TargetProfile cannot recalibrate the frozen Phase 3 theory_mode or archetype"
        )
    if require_current:
        for reference, label in (
            (target.package_ref, "package"),
            (target.paper_ir_ref, "PaperIR"),
            (target.reader_path_ref, "ReaderPath"),
            (target.base_profile_manifest_ref, "Phase 3 profile manifest"),
        ):
            entity = resolved.entities.get(_entity_key(reference))
            if entity is None or not _is_current_and_fresh(snapshot, entity):
                raise ProfileCraftValidationError(
                    f"TargetProfile exact {label} source is not current and fresh"
                )
    if target.selected_by.kind != "human":
        raise ProfileCraftValidationError("TargetProfile selection requires a human")
    catalog = _resolve_static(
        resolved,
        target.catalog_release_ref,
        pc.ProfileCatalogRelease,
        "TargetProfile catalog",
    )
    assert isinstance(catalog, pc.ProfileCatalogRelease)

    selected_decisions: list[Decision] = []
    for reference in target.human_decision_refs:
        decision = resolved.decisions.get(_decision_key(reference))
        if decision is None:
            raise ProfileCraftValidationError(
                "TargetProfile contains an unresolved exact Decision"
            )
        if (
            decision.decider.kind != "human"
            or _AUTHORITY_RANK[decision.required_authority] < _AUTHORITY_RANK["L2"]
            or decision.status != "confirmed"
            or decision.selected_option is None
        ):
            raise ProfileCraftValidationError(
                "TargetProfile Decisions must be human-confirmed at L2 or higher"
            )
        if (
            decision.subject_ref != target.reader_path_ref.entity_id
            or decision.scope_ref != target.paper_ir_ref.entity_id
        ):
            raise ProfileCraftValidationError(
                "TargetProfile Decisions must govern the exact ReaderPath within its PaperIR"
            )
        if require_current and (
            snapshot.current_decisions.get(decision.decision_id) != decision.version
            or not _decision_is_effective(snapshot, reference)
        ):
            raise ProfileCraftValidationError(
                "TargetProfile Decision is not current and effective"
            )
        selected_decisions.append(decision)

    by_kind: dict[str, list[Decision]] = {}
    for decision in selected_decisions:
        by_kind.setdefault(decision.decision_kind, []).append(decision)
    for decision_kind, target_field in _MANDATORY_TARGET_DECISIONS.items():
        values = by_kind.get(decision_kind, ())
        if len(values) != 1 or values[0].selected_option != getattr(target, target_field):
            raise ProfileCraftValidationError(
                f"TargetProfile does not equal its exact {decision_kind} Decision"
            )

    if target.venue_overlay_ref is not None:
        overlay = _resolve_static(
            resolved,
            target.venue_overlay_ref,
            pc.ProfileLayerCard,
            "TargetProfile venue overlay",
        )
        assert isinstance(overlay, pc.ProfileLayerCard)
        if overlay.layer_kind != "venue_overlay" or not overlay.is_soft_overlay:
            raise ProfileCraftValidationError("TargetProfile venue layer is not soft")
        venue = by_kind.get("venue_overlay", ())
        if len(venue) != 1 or venue[0].selected_option != overlay.selection_key:
            raise ProfileCraftValidationError(
                "TargetProfile venue overlay lacks its exact effective Decision"
            )
    elif by_kind.get("venue_overlay"):
        raise ProfileCraftValidationError(
            "TargetProfile carries venue authority without an overlay"
        )

    constraints = tuple(
        _resolve_static(
            resolved,
            reference,
            pc.ProfileLayerCard,
            "TargetProfile submission constraint",
        )
        for reference in target.submission_constraint_refs
    )
    if any(
        not isinstance(item, pc.ProfileLayerCard)
        or item.layer_kind != "submission_constraint"
        for item in constraints
    ):
        raise ProfileCraftValidationError(
            "TargetProfile submission refs do not resolve to constraints"
        )
    constraint_decisions = by_kind.get("submission_constraints", ())
    if constraints:
        expected = {item.selection_key for item in constraints if isinstance(item, pc.ProfileLayerCard)}
        observed = {item.selected_option for item in constraint_decisions}
        if observed != expected:
            raise ProfileCraftValidationError(
                "TargetProfile submission constraints lack exact Decisions"
            )
    elif constraint_decisions:
        raise ProfileCraftValidationError(
            "TargetProfile carries submission authority without constraints"
        )

    requested = {
        "theory_mode": target.theory_mode,
        "ambition": target.ambition,
        "archetype": target.primary_archetype,
        "field": target.field_key,
        "audience": target.primary_audience,
    }
    cards_by_kind = {
        kind: [card for card in catalog.cards if card.layer_kind == kind]
        for kind in requested
    }
    if any(
        len([card for card in cards_by_kind[kind] if card.selection_key == value]) != 1
        for kind, value in requested.items()
    ):
        raise ProfileCraftValidationError(
            "TargetProfile selection is absent or ambiguous in its exact catalog"
        )


def _validate_profile_stack(
    indices: _Indices, stack: pc.ResolvedProfileStack
) -> None:
    target = _resolve_profile(
        indices, stack.target_profile_ref, pc.TargetProfile, "profile stack target"
    )
    assert isinstance(target, pc.TargetProfile)
    if stack.target_profile_hash != _payload_hash(target):
        raise ProfileCraftValidationError("profile stack target hash mismatches")
    if stack.catalog_release_ref != target.catalog_release_ref:
        raise ProfileCraftValidationError("profile stack uses another catalog")
    catalog = _resolve_static(
        indices,
        stack.catalog_release_ref,
        pc.ProfileCatalogRelease,
        "profile stack catalog",
    )
    assert isinstance(catalog, pc.ProfileCatalogRelease)
    available = {pc.static_resource_ref(card): card for card in catalog.cards}
    for binding in stack.selected_layers:
        card = available.get(binding.layer_ref)
        if (
            card is None
            or card.layer_kind != binding.layer_kind
            or card.selection_key != binding.selection_key
            or card.status != binding.source_status
        ):
            raise ProfileCraftValidationError(
                "profile stack selected layer does not equal its catalog card"
            )
    expected = {
        "theory_mode": target.theory_mode,
        "ambition": target.ambition,
        "archetype": target.primary_archetype,
        "field": target.field_key,
        "audience": target.primary_audience,
    }
    selected = {item.layer_kind: item.selection_key for item in stack.selected_layers}
    if any(selected.get(kind) != value for kind, value in expected.items()):
        raise ProfileCraftValidationError(
            "resolved profile stack differs from its exact TargetProfile"
        )
    overlay_refs = {
        item.layer_ref for item in stack.selected_layers if item.layer_kind == "venue_overlay"
    }
    expected_overlay = (
        set() if target.venue_overlay_ref is None else {target.venue_overlay_ref}
    )
    if overlay_refs != expected_overlay:
        raise ProfileCraftValidationError("resolved stack has the wrong venue overlay")

    # Shape checks above make failures legible; this exact recomputation is the
    # authority boundary.  A route output cannot omit an inconvenient floor
    # directive, invent a catalog directive, or self-report conflict outcomes.
    try:
        expected_stack = resolve_profile_stack(
            target,
            target_profile_ref=stack.target_profile_ref,
            source_state_revision=stack.source_state_revision,
            resolved_by=stack.resolved_by,
            resolved_at=stack.resolved_at,
            catalog=catalog,
        )
    except ProfileCraftPolicyError as exc:
        raise ProfileCraftValidationError(
            "profile stack cannot be deterministically recomputed"
        ) from exc
    if stack != expected_stack:
        raise ProfileCraftValidationError(
            "profile stack is not the exact deterministic catalog resolution"
        )


def _validate_diagnosis(indices: _Indices, diagnosis: pc.ReaderProblemDiagnosis) -> None:
    paper = _resolve_authoring(
        indices, diagnosis.paper_ir_ref, a.PaperIR, "diagnosis PaperIR"
    )
    reader = _resolve_authoring(
        indices, diagnosis.reader_path_ref, a.ReaderPath, "diagnosis ReaderPath"
    )
    stack = _resolve_profile(
        indices,
        diagnosis.profile_stack_ref,
        pc.ResolvedProfileStack,
        "diagnosis profile stack",
    )
    contracts = _resolve_authoring(
        indices,
        diagnosis.result_contract_set_binding.entity_ref,
        a.ResultContractSet,
        "diagnosis ResultContractSet",
    )
    if (
        diagnosis.paper_ir_hash != _payload_hash(paper)
        or diagnosis.reader_path_hash != _payload_hash(reader)
        or diagnosis.profile_stack_hash != _payload_hash(stack)
        or diagnosis.result_contract_set_binding.payload_hash
        != _payload_hash(contracts)
    ):
        raise ProfileCraftValidationError("reader diagnosis exact payload hash mismatches")
    assert isinstance(paper, a.PaperIR)
    assert isinstance(reader, a.ReaderPath)
    assert isinstance(stack, pc.ResolvedProfileStack)
    assert isinstance(contracts, a.ResultContractSet)
    target = _resolve_profile(
        indices,
        stack.target_profile_ref,
        pc.TargetProfile,
        "diagnosis TargetProfile",
    )
    assert isinstance(target, pc.TargetProfile)
    if (
        reader.paper_ir_ref != diagnosis.paper_ir_ref
        or contracts.paper_ir_ref != diagnosis.paper_ir_ref
        or contracts.reader_path_ref != diagnosis.reader_path_ref
        or target.package_ref != paper.package_ref
        or target.paper_ir_ref != diagnosis.paper_ir_ref
        or target.reader_path_ref != diagnosis.reader_path_ref
    ):
        raise ProfileCraftValidationError("reader diagnosis crosses PaperIR lineages")

    if diagnosis.inspected_manuscript_unit_binding is None:
        expected_roles = _ordered_unique(
            item.role for item in reader.section_contracts
        )
        if (
            diagnosis.causal_class != "initial_planning"
            or diagnosis.diagnostic_categories
            or diagnosis.resolution_requirements
            or diagnosis.semantic_input_bindings
            or diagnosis.affected_section_ids
            or diagnosis.affected_section_roles != expected_roles
            or diagnosis.upstream_repair_route
            != _UPSTREAM_ROUTE_BY_CAUSAL_CLASS["initial_planning"]
        ):
            raise ProfileCraftValidationError(
                "pre-manuscript diagnosis is not the exact ReaderPath planning projection"
            )
        return
    unit_binding = diagnosis.inspected_manuscript_unit_binding
    unit = _resolve_authoring(
        indices,
        unit_binding.entity_ref,
        a.ManuscriptUnit,
        "diagnosis inspected ManuscriptUnit",
    )
    assert isinstance(unit, a.ManuscriptUnit)
    if (
        unit_binding.payload_hash != _payload_hash(unit)
        or unit.paper_ir_ref != diagnosis.paper_ir_ref
        or unit.reader_path_ref != diagnosis.reader_path_ref
        or unit.result_contract_set_ref
        != diagnosis.result_contract_set_binding.entity_ref
    ):
        raise ProfileCraftValidationError(
            "diagnosis inspected manuscript crosses its design lineage"
        )

    reviews: list[a.ReviewRecord] = []
    for binding in diagnosis.diagnostic_review_bindings:
        review = _resolve_authoring(
            indices, binding.entity_ref, a.ReviewRecord, "diagnosis ReviewRecord"
        )
        assert isinstance(review, a.ReviewRecord)
        if (
            binding.payload_hash != _payload_hash(review)
            or review.manuscript_unit_ref != unit_binding.entity_ref
            or review.reviewed_artifact_ref != unit.manuscript_artifact_ref
        ):
            raise ProfileCraftValidationError(
                "diagnosis ReviewRecord belongs to another manuscript"
            )
        reviews.append(review)
    if len({item.role for item in reviews}) != len(reviews):
        raise ProfileCraftValidationError(
            "diagnosis may bind at most one exact review per critic role"
        )

    findings: list[a.ReviewFinding] = []
    for binding in diagnosis.diagnostic_finding_bindings:
        finding = _resolve_authoring(
            indices, binding.entity_ref, a.ReviewFinding, "diagnosis ReviewFinding"
        )
        assert isinstance(finding, a.ReviewFinding)
        if (
            binding.payload_hash != _payload_hash(finding)
            or finding.manuscript_unit_ref != unit_binding.entity_ref
            or finding.reviewed_artifact_ref != unit.manuscript_artifact_ref
            or not any(
                review.assignment_ref == finding.assignment_ref
                and review.role == finding.role
                and review.reviewer == finding.critic
                for review in reviews
            )
        ):
            raise ProfileCraftValidationError(
                "diagnosis ReviewFinding belongs to another exact review"
            )
        findings.append(finding)
    expected_finding_refs = {
        reference for review in reviews for reference in review.finding_refs
    }
    observed_finding_refs = {
        binding.entity_ref for binding in diagnosis.diagnostic_finding_bindings
    }
    if not observed_finding_refs or not observed_finding_refs.issubset(
        expected_finding_refs
    ):
        raise ProfileCraftValidationError(
            "diagnosis findings must belong to their exact diagnostic reviews"
        )

    closure_binding = diagnosis.blocked_review_closure_binding
    brief_binding = diagnosis.revision_brief_binding
    if closure_binding is None or brief_binding is None:
        raise ProfileCraftValidationError(
            "post-manuscript diagnosis lacks its blocked closure and RevisionBrief"
        )
    closure = _resolve_authoring(
        indices,
        closure_binding.entity_ref,
        a.ReviewClosure,
        "diagnosis blocked ReviewClosure",
    )
    brief = _resolve_authoring(
        indices,
        brief_binding.entity_ref,
        a.RevisionBrief,
        "diagnosis RevisionBrief",
    )
    assert isinstance(closure, a.ReviewClosure)
    assert isinstance(brief, a.RevisionBrief)
    if (
        closure_binding.payload_hash != _payload_hash(closure)
        or brief_binding.payload_hash != _payload_hash(brief)
    ):
        raise ProfileCraftValidationError(
            "diagnosis blocked closure or RevisionBrief hash mismatches"
        )
    if (
        closure.status != "blocked"
        or closure.paper_ir_ref != diagnosis.paper_ir_ref
        or closure.reader_path_ref != diagnosis.reader_path_ref
        or closure.result_contract_set_ref
        != diagnosis.result_contract_set_binding.entity_ref
        or closure.manuscript_unit_ref != unit_binding.entity_ref
        or closure.revision_brief_ref != brief_binding.entity_ref
        or brief.manuscript_unit_ref != unit_binding.entity_ref
        or brief.review_closure_ref != closure_binding.entity_ref
    ):
        raise ProfileCraftValidationError(
            "diagnosis failure bundle crosses its exact design/manuscript lineage"
        )

    closure_review_refs = (
        closure.formal_fidelity_review_ref,
        closure.economic_reader_review_ref,
        closure.cold_reader_review_ref,
    )
    closure_reviews: dict[EntityVersionRef, a.ReviewRecord] = {}
    for reference in closure_review_refs:
        review = _resolve_authoring(
            indices,
            reference,
            a.ReviewRecord,
            "diagnosis closure ReviewRecord",
        )
        assert isinstance(review, a.ReviewRecord)
        if (
            review.manuscript_unit_ref != unit_binding.entity_ref
            or review.reviewed_artifact_ref != unit.manuscript_artifact_ref
        ):
            raise ProfileCraftValidationError(
                "diagnosis blocked closure reviews another manuscript"
            )
        closure_reviews[reference] = review
    expected_review_bindings = tuple(
        reference
        for reference in closure_review_refs
        if set(closure_reviews[reference].finding_refs).intersection(
            brief.finding_refs
        )
    )
    if tuple(item.entity_ref for item in diagnosis.diagnostic_review_bindings) != (
        expected_review_bindings
    ):
        raise ProfileCraftValidationError(
            "diagnosis reviews are not the exact finding-bearing closure reviews"
        )
    if tuple(brief.finding_refs) != tuple(
        item.entity_ref for item in diagnosis.diagnostic_finding_bindings
    ):
        raise ProfileCraftValidationError(
            "diagnosis findings do not equal the exact RevisionBrief failure set"
        )
    if tuple(item.finding_id for item in findings) != tuple(
        closure.blocking_finding_ids
    ) or any(not item.blocking for item in findings):
        raise ProfileCraftValidationError(
            "diagnosis findings do not equal the blocked closure findings"
        )

    expected_categories = _ordered_unique(item.category for item in findings)
    if diagnosis.diagnostic_categories != expected_categories:
        raise ProfileCraftValidationError(
            "diagnosis categories are not the exact blocking-finding projection"
        )
    blocking_instructions = tuple(
        item for item in brief.instructions if item.blocking
    )
    if tuple(item.requirement_id for item in diagnosis.resolution_requirements) != tuple(
        item.instruction_id for item in blocking_instructions
    ):
        raise ProfileCraftValidationError(
            "diagnosis requirements are not the exact blocking RevisionBrief instructions"
        )
    finding_by_ref = {
        binding.entity_ref: finding
        for binding, finding in zip(diagnosis.diagnostic_finding_bindings, findings)
    }
    brief_entity = indices.entities.get(_entity_key(brief_binding.entity_ref))
    if brief_entity is None:
        raise ProfileCraftValidationError("diagnosis RevisionBrief entity is unresolved")
    matching_rules = {
        object_digest(rule): rule
        for resource in indices.static_resources.values()
        if isinstance(resource, pc.CraftCorpusRelease)
        for rule in resource.reader_problem_rules
        if rule.problem_key == diagnosis.reader_problem_key
    }
    if len(matching_rules) != 1:
        raise ProfileCraftValidationError(
            "diagnosis requires one unambiguous exact reader-problem rule"
        )
    problem_rule = next(iter(matching_rules.values()))
    if (
        not set(expected_categories).issubset(
            problem_rule.accepted_finding_categories
        )
        or not {item.action for item in blocking_instructions}.issubset(
            problem_rule.accepted_repair_actions
        )
    ):
        raise ProfileCraftValidationError(
            "diagnosis category or repair action is outside its reader-problem rule"
        )
    for index, (requirement, instruction) in enumerate(
        zip(diagnosis.resolution_requirements, blocking_instructions)
    ):
        finding = finding_by_ref.get(instruction.finding_ref)
        expected_path = f"/payload/instructions/{brief.instructions.index(instruction)}"
        expected_instruction_hash = facet_semantic_hash(
            brief_entity, "authority", expected_path
        )
        source = requirement.instruction_source
        if (
            finding is None
            or requirement.requirement_id != instruction.instruction_id
            or requirement.finding_ref != instruction.finding_ref
            or requirement.action != instruction.action
            or source.entity_id != brief_binding.entity_ref.entity_id
            or source.version != brief_binding.entity_ref.version
            or source.facet != "authority"
            or source.field_path != expected_path
            or source.semantic_hash != expected_instruction_hash
            or requirement.affected_assertion_ids != finding.assertion_ids
            or requirement.affected_section_ids != (unit.section_contract_id,)
            or requirement.required_semantic_input_ids
            != problem_rule.required_semantic_input_ids
        ):
            raise ProfileCraftValidationError(
                f"diagnosis requirement {index + 1} is not the exact instruction/finding projection"
            )

    section_by_id = {item.section_id: item for item in reader.section_contracts}
    try:
        expected_roles = _ordered_unique(
            section_by_id[section_id].role
            for section_id in diagnosis.affected_section_ids
        )
    except KeyError as exc:
        raise ProfileCraftValidationError(
            "diagnosis names a section outside its exact ReaderPath"
        ) from exc
    if diagnosis.affected_section_roles != expected_roles:
        raise ProfileCraftValidationError(
            "diagnosis section roles are not the exact ReaderPath projection"
        )

    allowed_source_refs: Mapping[str, frozenset[EntityVersionRef]] = {
        "paper_ir": frozenset({diagnosis.paper_ir_ref}),
        "reader_path": frozenset({diagnosis.reader_path_ref}),
        "result_contract": frozenset(
            {diagnosis.result_contract_set_binding.entity_ref}
        ),
        "manuscript_unit": frozenset({unit_binding.entity_ref}),
        "review_finding": frozenset(finding_by_ref),
        "human_decision": frozenset(),
        "derived_diagnosis": frozenset(),
    }
    section = section_by_id[unit.section_contract_id]
    packet_indices = tuple(
        index
        for index, packet in enumerate(contracts.result_packets)
        if packet.claim_projection_id in section.required_claim_projection_ids
    )
    if len(packet_indices) != 1:
        raise ProfileCraftValidationError(
            "diagnosis semantic inputs require one exact affected-section ResultPacket"
        )
    packet_index = packet_indices[0]
    packet = contracts.result_packets[packet_index]
    if (
        packet.primary_archetype != target.primary_archetype
        or packet.primary_archetype not in pc.TYPED_EXTRACTOR_ARCHETYPES
    ):
        raise ProfileCraftValidationError(
            "diagnosis ResultPacket archetype has no exact typed extractor"
        )
    source_rule_by_id = {
        item.input_id: item for item in problem_rule.semantic_input_source_rules
    }
    for binding in diagnosis.semantic_input_bindings:
        source_rule = source_rule_by_id.get(binding.input_id)
        if source_rule is None:
            raise ProfileCraftValidationError(
                "diagnosis semantic input lacks its typed reader-problem source rule"
            )
        expected_source_ref = (
            diagnosis.paper_ir_ref
            if source_rule.source_kind == "paper_ir"
            else diagnosis.result_contract_set_binding.entity_ref
        )
        try:
            expected_path = pc.semantic_input_selector_path(
                source_rule.selector,
                primary_archetype=packet.primary_archetype,
                packet_index=packet_index,
            )
        except ValueError as exc:
            raise ProfileCraftValidationError(
                "diagnosis semantic input selector has no exact archetype extractor"
            ) from exc
        if binding.source_kind != source_rule.source_kind:
            raise ProfileCraftValidationError(
                "diagnosis semantic input violates its typed source kind"
            )
        if binding.source_ref is not None:
            source_entity = _semantic_source_entity(
                indices,
                binding.source_ref,
                label=f"diagnosis semantic input {binding.input_id}",
            )
            exact_ref = _entity_ref(source_entity)
            if (
                binding.source_ref.facet != source_rule.owner_facet
                or exact_ref != expected_source_ref
                or binding.source_ref.field_path != expected_path
                or exact_ref not in allowed_source_refs[binding.source_kind]
            ):
                raise ProfileCraftValidationError(
                    "diagnosis semantic input violates its exact typed source selector"
                )
        if diagnosis.causal_class == "local_exposition" and (
            binding.availability != "available"
            or binding.source_kind
            not in {"paper_ir", "reader_path", "result_contract"}
        ):
            raise ProfileCraftValidationError(
                "local exposition requires available accepted design/contract inputs"
            )

    expected_causal = _expected_causal_class(findings, brief.instructions)
    expected_science_status = (
        "unresolved" if expected_causal == "scientific_content" else "resolved"
    )
    if (
        diagnosis.causal_class != expected_causal
        or diagnosis.upstream_science_status != expected_science_status
        or diagnosis.craft_eligible != (expected_causal == "local_exposition")
        or diagnosis.upstream_repair_route
        != _UPSTREAM_ROUTE_BY_CAUSAL_CLASS[expected_causal]
    ):
        raise ProfileCraftValidationError(
            "diagnosis causal class, science status, or upstream route is not derived"
        )


def _validate_revision_diagnosis_lineage(
    indices: _Indices,
    *,
    diagnosis: pc.ReaderProblemDiagnosis,
    prior_ref: EntityVersionRef,
    closure_ref: EntityVersionRef,
    closure: a.ReviewClosure,
    brief_ref: EntityVersionRef,
    brief: a.RevisionBrief,
) -> None:
    """Bind a profiled revision to the exact failed review it repairs."""

    _validate_diagnosis(indices, diagnosis)
    inspected = diagnosis.inspected_manuscript_unit_binding
    if inspected is None or inspected.entity_ref != prior_ref:
        raise ProfileCraftValidationError(
            "profiled revision diagnosis must inspect the exact prior manuscript"
        )
    if (
        diagnosis.blocked_review_closure_binding
        != pc.ProjectPayloadBinding(
            entity_ref=closure_ref, payload_hash=_payload_hash(closure)
        )
        or diagnosis.revision_brief_binding
        != pc.ProjectPayloadBinding(
            entity_ref=brief_ref, payload_hash=_payload_hash(brief)
        )
    ):
        raise ProfileCraftValidationError(
            "profiled revision diagnosis does not bind the supplied closure and brief"
        )
    if (
        closure.manuscript_unit_ref != prior_ref
        or closure.revision_brief_ref != brief_ref
        or brief.manuscript_unit_ref != prior_ref
        or brief.review_closure_ref != closure_ref
    ):
        raise ProfileCraftValidationError(
            "profiled revision closure and brief must bind the exact prior manuscript"
        )

    closure_review_refs = {
        closure.formal_fidelity_review_ref,
        closure.economic_reader_review_ref,
        closure.cold_reader_review_ref,
    }
    diagnosis_review_refs = {
        item.entity_ref for item in diagnosis.diagnostic_review_bindings
    }
    if not diagnosis_review_refs or not diagnosis_review_refs.issubset(
        closure_review_refs
    ):
        raise ProfileCraftValidationError(
            "profiled revision diagnosis reviews are outside the blocked closure lineage"
        )

    diagnosis_finding_refs = {
        item.entity_ref for item in diagnosis.diagnostic_finding_bindings
    }
    if diagnosis_finding_refs != set(brief.finding_refs):
        raise ProfileCraftValidationError(
            "profiled revision diagnosis findings must equal the RevisionBrief failure set"
        )
    diagnosis_finding_ids = {
        finding.finding_id
        for binding in diagnosis.diagnostic_finding_bindings
        for finding in (
            _resolve_authoring(
                indices,
                binding.entity_ref,
                a.ReviewFinding,
                "profiled revision diagnosis finding",
            ),
        )
        if isinstance(finding, a.ReviewFinding)
    }
    if diagnosis_finding_ids != set(closure.blocking_finding_ids):
        raise ProfileCraftValidationError(
            "profiled revision diagnosis findings differ from the blocked closure failures"
        )


def _validate_selection(indices: _Indices, selection: pc.CraftSelectionManifest) -> None:
    diagnosis = _resolve_profile(
        indices,
        selection.diagnosis_ref,
        pc.ReaderProblemDiagnosis,
        "craft selection diagnosis",
    )
    stack = _resolve_profile(
        indices,
        selection.profile_stack_ref,
        pc.ResolvedProfileStack,
        "craft selection profile stack",
    )
    if (
        selection.diagnosis_hash != _payload_hash(diagnosis)
        or selection.profile_stack_hash != _payload_hash(stack)
    ):
        raise ProfileCraftValidationError("craft selection payload hash mismatches")
    assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
    if (
        diagnosis.profile_stack_ref != selection.profile_stack_ref
        or diagnosis.reader_problem_key != selection.diagnosed_reader_problem_key
        or diagnosis.required_resolution_ids
        != selection.diagnosed_required_resolution_ids
        or diagnosis.upstream_science_status
        != selection.diagnosed_upstream_science_status
    ):
        raise ProfileCraftValidationError(
            "craft selection does not equal its diagnosed reader problem"
        )
    corpus = _resolve_static(
        indices,
        selection.corpus_release_ref,
        pc.CraftCorpusRelease,
        "craft selection corpus",
    )
    assert isinstance(corpus, pc.CraftCorpusRelease)
    if (
        selection.index_version != corpus.index_version
        or selection.retriever_version != corpus.retriever_version
    ):
        raise ProfileCraftValidationError(
            "craft selection does not pin its corpus index/retriever"
        )
    admitted = {pc.static_resource_ref(move) for move in corpus.moves}
    if any(reference not in admitted for reference in selection.selected_move_refs):
        raise ProfileCraftValidationError(
            "craft selection chose a move outside its theory-only corpus"
        )

    # Candidate eligibility, exclusions, functional matching, and minimality
    # are derived policy results, not statements a retriever may attest itself.
    assert isinstance(stack, pc.ResolvedProfileStack)
    try:
        expected_selection = select_craft_moves(
            diagnosis,
            diagnosis_ref=selection.diagnosis_ref,
            profile_stack=stack,
            profile_stack_ref=selection.profile_stack_ref,
            selected_by=selection.selected_by,
            selected_at=selection.selected_at,
            corpus=corpus,
        )
    except ProfileCraftPolicyError as exc:
        raise ProfileCraftValidationError(
            "craft selection cannot be deterministically recomputed"
        ) from exc
    if selection != expected_selection:
        raise ProfileCraftValidationError(
            "craft selection is not the exact deterministic corpus result"
        )


def _validate_predicate_contract(
    indices: _Indices, contract: pc.ObligationPredicateContract
) -> None:
    assurance = _resolve_authoring(
        indices,
        contract.assurance_bundle_ref,
        a.AssuranceBundle,
        "predicate contract AssuranceBundle",
    )
    obligation = _resolve_theory(
        indices,
        contract.obligation_ref,
        t.ProofObligation,
        "predicate contract obligation",
    )
    claim_graph = _resolve_theory(
        indices,
        contract.claim_graph_ref,
        t.ClaimGraph,
        "predicate contract ClaimGraph",
    )
    formal_model = _resolve_theory(
        indices,
        contract.formal_model_ref,
        t.FormalModel,
        "predicate contract FormalModel",
    )
    assumption_map = _resolve_theory(
        indices,
        contract.assumption_map_ref,
        t.AssumptionMap,
        "predicate contract AssumptionMap",
    )
    if (
        contract.assurance_bundle_hash != _payload_hash(assurance)
        or contract.obligation_hash != _payload_hash(obligation)
        or contract.claim_graph_hash != _payload_hash(claim_graph)
        or contract.formal_model_hash != _payload_hash(formal_model)
        or contract.assumption_map_hash != _payload_hash(assumption_map)
    ):
        raise ProfileCraftValidationError("predicate contract exact source hash mismatches")
    assert isinstance(obligation, t.ProofObligation)
    assert isinstance(claim_graph, t.ClaimGraph)
    assert isinstance(assurance, a.AssuranceBundle)
    if (
        assurance.claim_graph_ref != contract.claim_graph_ref
        or assurance.formal_model_ref != contract.formal_model_ref
        or assurance.assumption_map_ref != contract.assumption_map_ref
        or obligation.claim_graph_ref != contract.claim_graph_ref
        or claim_graph.formal_model_ref != contract.formal_model_ref
        or claim_graph.assumption_map_ref != contract.assumption_map_ref
        or tuple(obligation.assumption_ids) != contract.obligation_assumption_ids
    ):
        raise ProfileCraftValidationError(
            "predicate contract does not map its exact scientific topology"
        )
    if contract.mapper == assurance.assembled_by:
        raise ProfileCraftValidationError(
            "predicate mapper must be independent of the AssuranceBundle assembler"
        )
    _validate_contract_receipt_bound(assurance, contract)


def _validate_predicate_auditor_independence(
    indices: _Indices,
    *,
    auditor: Actor,
    mapper: Actor,
    assurance_ref: EntityVersionRef,
) -> None:
    """Keep semantic audit independent of every author of the bound evidence."""

    assurance = _resolve_authoring(
        indices,
        assurance_ref,
        a.AssuranceBundle,
        "predicate auditor AssuranceBundle",
    )
    assert isinstance(assurance, a.AssuranceBundle)
    bound_writers = tuple(
        payload.canonical_writer
        for payload in indices.authoring_payloads.values()
        if isinstance(payload, a.PaperIR)
        and payload.assurance_bundle_ref == assurance_ref
    )
    forbidden = (mapper, assurance.assembled_by, *bound_writers)
    if _actor_key(auditor) in {_actor_key(item) for item in forbidden}:
        raise ProfileCraftValidationError(
            "predicate auditor must be independent of the mapper, "
            "AssuranceBundle assembler, and every canonical writer bound to that assurance"
        )


def _validate_mapping_audit(indices: _Indices, audit: pc.PredicateMappingAudit) -> None:
    contract = _resolve_profile(
        indices,
        audit.contract_ref,
        pc.ObligationPredicateContract,
        "predicate mapping audit contract",
    )
    if audit.contract_hash != _payload_hash(contract):
        raise ProfileCraftValidationError("predicate audit contract_hash mismatches")
    assert isinstance(contract, pc.ObligationPredicateContract)
    _validate_predicate_contract(indices, contract)
    _validate_predicate_auditor_independence(
        indices,
        auditor=audit.auditor,
        mapper=contract.mapper,
        assurance_ref=contract.assurance_bundle_ref,
    )
    if (
        audit.contract_coverage_class != contract.coverage_class
        or audit.contract_mapper != contract.mapper
        or audit.registered_mutation_ids
        != tuple(item.mutation_id for item in contract.mutation_tests)
    ):
        raise ProfileCraftValidationError(
            "predicate audit does not equal its exact mapping contract"
        )
    expected_unexecutable = tuple(
        item.mutation_id
        for item in contract.mutation_tests
        if item.mutation_kind == "omitted_assumption" and not item.detected
    )
    if audit.unexecutable_mutation_ids != expected_unexecutable:
        raise ProfileCraftValidationError(
            "predicate audit unexecutable controls differ from its exact contract"
        )
    if audit.verdict != "rejected" and not audit_is_approved_bounded(audit):
        raise ProfileCraftValidationError(
            "approved predicate audit exceeds its bounded evidence"
        )
    non_exact_clauses = {
        item.obligation_clause_id
        for item in contract.clause_mappings
        if item.relation != "exact"
    }
    warned = {
        clause_id
        for finding in audit.findings
        if finding.severity == "warning"
        for clause_id in finding.affected_clause_ids
    }
    if audit.verdict == "approved_partial" and not non_exact_clauses.issubset(warned):
        raise ProfileCraftValidationError(
            "approved_partial requires an explicit warning for every non-exact clause"
        )
    required_limitations = _required_predicate_limitation_kinds(contract, audit)
    if audit.verdict == "approved_partial" and not required_limitations:
        raise ProfileCraftValidationError(
            "approved_partial requires at least one deterministic typed predicate limitation"
        )
    warning_limitations: list[pc.PredicateLimitationKind] = []
    for finding in audit.findings:
        if finding.severity != "warning":
            continue
        for kind in finding.limitation_kinds:
            if kind not in warning_limitations:
                warning_limitations.append(kind)
    if audit.verdict == "approved_partial" and tuple(
        warning_limitations
    ) != required_limitations:
        raise ProfileCraftValidationError(
            "approved_partial warning limitations must equal every deterministic "
            "non-exact predicate limitation"
        )
    if audit.verdict == "approved_exact" and (
        required_limitations or warning_limitations
    ):
        raise ProfileCraftValidationError(
            "approved_exact cannot retain a typed predicate limitation"
        )


def _required_predicate_limitation_kinds(
    contract: pc.ObligationPredicateContract,
    audit: pc.PredicateMappingAudit,
) -> tuple[pc.PredicateLimitationKind, ...]:
    """Derive the complete, canonically ordered limits of one bounded mapping."""

    present: set[pc.PredicateLimitationKind] = set()
    if any(item.relation != "exact" for item in contract.clause_mappings):
        present.add("nonexact_clause_mapping")
    if contract.domain_relation != "equal":
        present.add("domain_not_equal")
    if contract.quantifier_relation != "equivalent":
        present.add("quantifier_not_equivalent")
    if (
        set(contract.mapped_assumption_ids) != set(contract.obligation_assumption_ids)
        or contract.added_assumption_ids
    ):
        present.add("assumption_mapping_nonexact")
    if contract.execution_scope in {"finite_sample", "diagnostic"}:
        present.add("bounded_execution_scope")
    if contract.coverage_class != "exact":
        present.add("coverage_below_exact")
    if contract.tolerance_policy == "loose":
        present.add("loose_tolerance")
    if not (
        contract.antecedent_satisfiable
        and contract.predicate_can_return_false
        and audit.antecedent_witness_verified
        and audit.falsifying_witness_verified
    ):
        present.add("nonvacuity_unverified")
    if audit.unexecutable_mutation_ids:
        present.add("unexecutable_control")
    return tuple(
        kind for kind in pc.PREDICATE_LIMITATION_KIND_ORDER if kind in present
    )


def _ordered_predicate_limitation_union(
    contracts_and_audits: Iterable[
        tuple[pc.ObligationPredicateContract, pc.PredicateMappingAudit]
    ],
) -> tuple[pc.PredicateLimitationKind, ...]:
    """Union limitations without losing the closure's declared audit order."""

    seen: set[pc.PredicateLimitationKind] = set()
    ordered: list[pc.PredicateLimitationKind] = []
    for contract, audit in contracts_and_audits:
        for kind in _required_predicate_limitation_kinds(contract, audit):
            if kind not in seen:
                seen.add(kind)
                ordered.append(kind)
    return tuple(ordered)


def audit_is_approved_bounded(audit: pc.PredicateMappingAudit) -> bool:
    """Return whether an audit is approved without upgrading bounded evidence."""

    if audit.verdict not in {"approved_exact", "approved_partial"}:
        return False
    if any(item.severity in {"error", "critical"} for item in audit.findings):
        return False
    if not audit.mutation_replay_passed or not audit.domain_witness_verified:
        return False
    if audit.verdict == "approved_exact":
        if (
            not audit.antecedent_witness_verified
            or not audit.falsifying_witness_verified
            or audit.unexecutable_mutation_ids
        ):
            return False
    return True


def _bound_receipt(
    assurance: a.AssuranceBundle,
    contract: pc.ObligationPredicateContract,
) -> a.ToolHarnessReceipt:
    obligation_receipts = tuple(
        item
        for item in assurance.tool_receipts
        if item.obligation_ref == contract.obligation_ref
    )
    if len(obligation_receipts) != 1:
        raise ProfileCraftValidationError(
            "Phase 4 currently requires one unambiguous executed receipt per obligation"
        )
    receipts = tuple(
        item
        for item in assurance.tool_receipts
        if item.receipt_id == contract.receipt_id
    )
    if len(receipts) != 1:
        raise ProfileCraftValidationError(
            "predicate contract must bind exactly one AssuranceBundle receipt_id"
        )
    receipt = receipts[0]
    if object_digest(receipt) != contract.receipt_hash:
        raise ProfileCraftValidationError(
            "predicate contract receipt_hash does not bind the exact receipt"
        )
    if (
        receipt.obligation_ref != contract.obligation_ref
        or receipt.claim_graph_ref != contract.claim_graph_ref
        or receipt.code_ref != contract.code_ref
        or receipt.input_ref != contract.predicate_artifact_ref
    ):
        raise ProfileCraftValidationError(
            "predicate contract code/input/science refs differ from its exact receipt"
        )
    return receipt


def _validate_contract_receipt_bound(
    assurance: a.AssuranceBundle,
    contract: pc.ObligationPredicateContract,
) -> None:
    """Prevent a predicate mapping from upgrading its exact executed receipt."""

    receipt = _bound_receipt(assurance, contract)
    if receipt.harness_kind == "symbolic_identity":
        if (
            receipt.outcome != "identity_verified"
            or receipt.evidentiary_role != "exact_identity_certificate"
            or contract.execution_scope != "symbolic_exact"
            or contract.coverage_class not in {"exact", "partial"}
        ):
            raise ProfileCraftValidationError(
                "symbolic predicate coverage exceeds or misstates its exact receipt"
            )
        return

    if contract.execution_scope not in {"finite_sample", "diagnostic"}:
        raise ProfileCraftValidationError(
            "finite harness evidence cannot claim symbolic or exhaustive coverage"
        )
    if receipt.outcome == "witness_found":
        if (
            receipt.evidentiary_role != "falsification"
            or contract.coverage_class != "falsification_only"
        ):
            raise ProfileCraftValidationError(
                "a found witness supports falsification-only predicate coverage"
            )
        return
    if receipt.outcome == "no_counterexample_found":
        if (
            receipt.evidentiary_role not in {"corroboration_only", "diagnostic"}
            or contract.coverage_class != "diagnostic"
        ):
            raise ProfileCraftValidationError(
                "a finite passing scan supports diagnostic coverage only"
            )
        return
    if contract.coverage_class != "diagnostic":
        raise ProfileCraftValidationError(
            "failed or inconclusive harness evidence is diagnostic only"
        )


def _validate_bounded_audits_against_assurance(
    indices: _Indices,
    audits: Iterable[pc.PredicateMappingAudit],
    assurance: a.AssuranceBundle,
    assurance_ref: EntityVersionRef,
) -> None:
    resolved_audits = tuple(audits)
    observed: list[tuple[str, str]] = []
    for audit in resolved_audits:
        if not audit_is_approved_bounded(audit):
            raise ProfileCraftValidationError(
                "Phase 4 requires an approved bounded predicate mapping audit"
            )
        contract = _resolve_profile(
            indices,
            audit.contract_ref,
            pc.ObligationPredicateContract,
            "bounded predicate audit contract",
        )
        assert isinstance(contract, pc.ObligationPredicateContract)
        if (
            contract.assurance_bundle_ref != assurance_ref
            or contract.assurance_bundle_hash != _payload_hash(assurance)
        ):
            raise ProfileCraftValidationError(
                "predicate audit contract binds another AssuranceBundle"
            )
        _validate_contract_receipt_bound(assurance, contract)
        receipt = _bound_receipt(assurance, contract)
        if receipt.outcome in {"failed", "inconclusive"}:
            raise ProfileCraftValidationError(
                "failed or inconclusive receipts cannot support an approved mapping audit"
            )
        observed.append((contract.receipt_id, contract.receipt_hash))

    expected = tuple(
        (receipt.receipt_id, object_digest(receipt))
        for receipt in assurance.tool_receipts
    )
    if len(observed) != len(expected) or set(observed) != set(expected):
        raise ProfileCraftValidationError(
            "approved predicate audits must cover every AssuranceBundle receipt exactly once"
        )


def _validate_assessment(
    indices: _Indices, assessment: pc.CraftRealizationAssessment
) -> None:
    selection = _resolve_profile(
        indices,
        assessment.selection_manifest_ref,
        pc.CraftSelectionManifest,
        "craft assessment selection",
    )
    stack = _resolve_profile(
        indices,
        assessment.profile_stack_ref,
        pc.ResolvedProfileStack,
        "craft assessment profile stack",
    )
    diagnosis = _resolve_profile(
        indices,
        assessment.reader_problem_diagnosis_ref,
        pc.ReaderProblemDiagnosis,
        "craft assessment reader diagnosis",
    )
    reader = _resolve_authoring(
        indices,
        assessment.reader_path_ref,
        a.ReaderPath,
        "craft assessment ReaderPath",
    )
    contracts = _resolve_authoring(
        indices,
        assessment.result_contract_set_ref,
        a.ResultContractSet,
        "craft assessment ResultContractSet",
    )
    unit = _resolve_authoring(
        indices,
        assessment.manuscript_unit_ref,
        a.ManuscriptUnit,
        "craft assessment manuscript",
    )
    base = _resolve_authoring(
        indices,
        assessment.base_authoring_closure_ref,
        a.ReviewClosure,
        "craft assessment authoring closure",
    )
    formal_review = _resolve_authoring(
        indices,
        assessment.formal_fidelity_review_ref,
        a.ReviewRecord,
        "craft assessment formal review",
    )
    economic_review = _resolve_authoring(
        indices,
        assessment.economic_reader_review_ref,
        a.ReviewRecord,
        "craft assessment economic review",
    )
    cold_review = _resolve_authoring(
        indices,
        assessment.cold_reader_review_ref,
        a.ReviewRecord,
        "craft assessment cold review",
    )
    if (
        assessment.selection_manifest_hash != _payload_hash(selection)
        or assessment.profile_stack_hash != _payload_hash(stack)
        or assessment.reader_problem_diagnosis_hash != _payload_hash(diagnosis)
        or assessment.reader_path_hash != _payload_hash(reader)
        or assessment.result_contract_set_hash != _payload_hash(contracts)
        or assessment.manuscript_unit_hash != _payload_hash(unit)
        or assessment.base_authoring_closure_hash != _payload_hash(base)
        or assessment.formal_fidelity_review_hash != _payload_hash(formal_review)
        or assessment.economic_reader_review_hash != _payload_hash(economic_review)
        or assessment.cold_reader_review_hash != _payload_hash(cold_review)
    ):
        raise ProfileCraftValidationError("craft assessment payload hash mismatches")
    assert isinstance(selection, pc.CraftSelectionManifest)
    assert isinstance(stack, pc.ResolvedProfileStack)
    assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
    assert isinstance(reader, a.ReaderPath)
    assert isinstance(contracts, a.ResultContractSet)
    assert isinstance(unit, a.ManuscriptUnit)
    assert isinstance(base, a.ReviewClosure)
    assert isinstance(formal_review, a.ReviewRecord)
    assert isinstance(economic_review, a.ReviewRecord)
    assert isinstance(cold_review, a.ReviewRecord)
    target = _resolve_profile(
        indices,
        stack.target_profile_ref,
        pc.TargetProfile,
        "craft assessment TargetProfile",
    )
    assert isinstance(target, pc.TargetProfile)
    if (
        assessment.selected_move_refs != selection.selected_move_refs
        or assessment.profile_stack_ref != selection.profile_stack_ref
        or assessment.reader_problem_diagnosis_ref != selection.diagnosis_ref
        or diagnosis.profile_stack_ref != assessment.profile_stack_ref
        or diagnosis.reader_path_ref != assessment.reader_path_ref
        or diagnosis.result_contract_set_binding.entity_ref
        != assessment.result_contract_set_ref
        or reader.paper_ir_ref != diagnosis.paper_ir_ref
        or contracts.paper_ir_ref != diagnosis.paper_ir_ref
        or contracts.reader_path_ref != assessment.reader_path_ref
        or unit.paper_ir_ref != diagnosis.paper_ir_ref
        or unit.reader_path_ref != assessment.reader_path_ref
        or unit.result_contract_set_ref != assessment.result_contract_set_ref
        or target.paper_ir_ref != diagnosis.paper_ir_ref
        or target.reader_path_ref != assessment.reader_path_ref
        or assessment.primary_audience != target.primary_audience
        or assessment.manuscript_artifact_ref != unit.manuscript_artifact_ref
        or assessment.writer != unit.canonical_writer
        or base.status != "authoring_ready"
        or base.manuscript_unit_ref != assessment.manuscript_unit_ref
        or base.formal_fidelity_review_ref
        != assessment.formal_fidelity_review_ref
        or base.economic_reader_review_ref
        != assessment.economic_reader_review_ref
        or base.cold_reader_review_ref != assessment.cold_reader_review_ref
    ):
        raise ProfileCraftValidationError(
            "craft assessment belongs to another selection or manuscript"
        )
    reviews = (
        (formal_review, "formal_fidelity"),
        (economic_review, "economic_reader"),
        (cold_review, "cold_reader"),
    )
    for review, role in reviews:
        if (
            review.role != role
            or review.manuscript_unit_ref != assessment.manuscript_unit_ref
            or review.reviewed_artifact_ref != assessment.manuscript_artifact_ref
            or review.canonical_writer != assessment.writer
        ):
            raise ProfileCraftValidationError(
                "craft assessment review role or manuscript lineage mismatches"
            )
    participants = (
        assessment.assessor,
        assessment.writer,
        formal_review.reviewer,
        economic_review.reviewer,
        cold_review.reviewer,
    )
    if len({_actor_key(item) for item in participants}) != len(participants):
        raise ProfileCraftValidationError(
            "craft assessor, writer, and three base reviewers must be pairwise distinct"
        )

    formal = formal_review.assessment
    economic = economic_review.assessment
    cold = cold_review.assessment
    formal_passed = isinstance(formal, a.FormalFidelityAssessment) and all(
        (
            formal.theorem_statement_exact,
            formal.scope_preserved,
            formal.assumptions_preserved,
            formal.proof_language_honest,
            formal.numerical_evidence_bounded,
            all(item.outcome == "passed" for item in formal.entailment_checks),
        )
    )
    economic_passed = isinstance(economic, a.EconomicReaderAssessment) and all(
        (
            economic.question_and_benchmark_reconstructible,
            economic.explanation_is_not_restatement,
            economic.mechanism_or_conceptual_logic_reconstructible,
            economic.diagnostic_example_or_witness_present,
            economic.boundary_is_economically_interpretable,
        )
    )
    cold_passed = isinstance(cold, a.ColdReaderAssessment) and all(
        (
            cold.question_and_benchmark_retell_passed,
            cold.exact_scope_recovery_passed,
            cold.assumption_role_recovery_passed,
            cold.boundary_discrimination_passed,
            cold.near_transfer_passed,
        )
    )
    if assessment.outcome == "pass" and not (
        formal_passed and economic_passed and cold_passed
    ):
        raise ProfileCraftValidationError(
            "passing craft assessment requires the exact three passing authoring reviews"
        )
    if assessment.formal_fidelity_outcome != (
        "pass" if formal_passed else "fail"
    ):
        raise ProfileCraftValidationError(
            "craft formal-fidelity outcome differs from the exact formal review"
        )

    assertion_ids = {item.assertion_id for item in unit.spans}
    realized_assertion_roles = _ordered_unique(item.role for item in unit.spans)
    signal_results = {
        "formal_fidelity": formal_passed,
        "scope_and_assumptions": isinstance(
            formal, a.FormalFidelityAssessment
        )
        and formal.scope_preserved
        and formal.assumptions_preserved,
        "bounded_evidentiary_language": isinstance(
            formal, a.FormalFidelityAssessment
        )
        and formal.proof_language_honest
        and formal.numerical_evidence_bounded,
        "economic_explanation": economic_passed,
        "cold_reader_transfer": cold_passed,
    }
    observed_review_signals = tuple(
        signal for signal in _REVIEW_SIGNAL_ORDER if signal_results[signal]
    )
    required_evidence = {
        _exact_ref_key(assessment.selection_manifest_ref),
        _exact_ref_key(assessment.profile_stack_ref),
        _exact_ref_key(assessment.reader_problem_diagnosis_ref),
        _exact_ref_key(assessment.reader_path_ref),
        _exact_ref_key(assessment.result_contract_set_ref),
        _exact_ref_key(assessment.manuscript_unit_ref),
        _exact_ref_key(assessment.manuscript_artifact_ref),
        _exact_ref_key(assessment.base_authoring_closure_ref),
        _exact_ref_key(assessment.formal_fidelity_review_ref),
        _exact_ref_key(assessment.economic_reader_review_ref),
        _exact_ref_key(assessment.cold_reader_review_ref),
    }
    candidates = {
        item.move_ref: item for item in selection.candidates if item.selected
    }
    semantic_binding_by_id = {
        item.input_id: item for item in diagnosis.semantic_input_bindings
    }
    realization_by_ref = {
        item.move_ref: item for item in assessment.move_realizations
    }
    for realization in assessment.move_realizations:
        candidate = candidates.get(realization.move_ref)
        if candidate is None:
            raise ProfileCraftValidationError(
                "craft realization references an unselected move"
            )
        expected_source_refs = tuple(
            semantic_binding_by_id[input_id].source_ref
            for input_id in realization.realized_semantic_input_ids
        )
        if (
            realization.realized_semantic_input_ids
            != candidate.move.required_semantic_inputs
            or any(item is None for item in expected_source_refs)
            or realization.realized_semantic_source_refs
            != expected_source_refs
            or not set(realization.realized_assertion_ids).issubset(assertion_ids)
            or not required_evidence.issubset(
                {_exact_ref_key(item) for item in realization.evidence_refs}
            )
        ):
            raise ProfileCraftValidationError(
                "craft realization lacks exact semantic, assertion, or review evidence"
            )

    active_directives = tuple(
        item
        for item in stack.directive_resolutions
        if item.outcome == "active" and item.directive.strength != "soft"
    )
    if assessment.required_directive_ids != stack.active_requirements or tuple(
        item.directive.directive_id for item in active_directives
    ) != assessment.required_directive_ids:
        raise ProfileCraftValidationError(
            "craft assessment directive IDs differ from the exact resolved profile stack"
        )
    for check, resolution in zip(
        assessment.directive_acceptance_checks, active_directives
    ):
        criterion = resolution.directive.acceptance_criterion
        if any(
            signal not in signal_results
            for signal in criterion.required_review_signals
        ):
            raise ProfileCraftValidationError(
                "profile directive uses an unsupported review signal"
            )
        if (
            check.directive_id != resolution.directive.directive_id
            or check.criterion_id != criterion.criterion_id
            or check.required_assertion_roles
            != criterion.required_assertion_roles
            or check.realized_assertion_roles != realized_assertion_roles
            or check.required_review_signals
            != criterion.required_review_signals
            or check.observed_review_signals != observed_review_signals
            or not required_evidence.issubset(
                {_exact_ref_key(item) for item in check.evidence_refs}
            )
        ):
            raise ProfileCraftValidationError(
                "directive acceptance check is not the exact stack/manuscript/review projection"
            )

    requirements = diagnosis.resolution_requirements
    if assessment.required_resolution_ids != tuple(
        item.requirement_id for item in requirements
    ):
        raise ProfileCraftValidationError(
            "craft assessment resolution IDs differ from the exact diagnosis"
        )
    for check, requirement in zip(
        assessment.resolution_requirement_checks, requirements
    ):
        expected_move_refs = tuple(
            candidate.move_ref
            for candidate in selection.candidates
            if candidate.selected
            and requirement.requirement_id in candidate.covered_requirement_ids
        )
        realized_inputs = _ordered_unique(
            semantic_input
            for move_ref in expected_move_refs
            for semantic_input in realization_by_ref[
                move_ref
            ].realized_semantic_input_ids
        )
        realizing_assertion_ids = {
            assertion_id
            for move_ref in expected_move_refs
            for assertion_id in realization_by_ref[
                move_ref
            ].realized_assertion_ids
        }
        required_sources = {
            binding.source_ref
            for input_id in requirement.required_semantic_input_ids
            for binding in (semantic_binding_by_id[input_id],)
            if binding.source_ref is not None
        }
        realized_sources = {
            source
            for move_ref in expected_move_refs
            for source in realization_by_ref[
                move_ref
            ].realized_semantic_source_refs
        }
        if (
            not expected_move_refs
            or check.requirement_id != requirement.requirement_id
            or check.repair_action != requirement.action
            or check.realizing_move_refs != expected_move_refs
            or check.affected_assertion_ids
            != requirement.affected_assertion_ids
            or not set(check.affected_assertion_ids).issubset(assertion_ids)
            or not set(requirement.affected_assertion_ids).issubset(
                realizing_assertion_ids
            )
            or check.affected_section_ids != requirement.affected_section_ids
            or unit.section_contract_id not in requirement.affected_section_ids
            or check.required_semantic_input_ids
            != requirement.required_semantic_input_ids
            or check.realized_semantic_input_ids != realized_inputs
            or not required_sources.issubset(realized_sources)
            or not required_evidence.issubset(
                {_exact_ref_key(item) for item in check.evidence_refs}
            )
        ):
            raise ProfileCraftValidationError(
                "resolution check is not the exact diagnosis/selection/realization projection"
            )

    reader_evidence = {
        _exact_ref_key(assessment.manuscript_unit_ref),
        _exact_ref_key(assessment.manuscript_artifact_ref),
        _exact_ref_key(assessment.economic_reader_review_ref),
        _exact_ref_key(assessment.cold_reader_review_ref),
        _exact_ref_key(assessment.reader_path_ref),
        _exact_ref_key(assessment.result_contract_set_ref),
    }
    expected_reader_flags = (
        isinstance(economic, a.EconomicReaderAssessment)
        and economic.question_and_benchmark_reconstructible
        and isinstance(cold, a.ColdReaderAssessment)
        and cold.question_and_benchmark_retell_passed,
        isinstance(economic, a.EconomicReaderAssessment)
        and economic.explanation_is_not_restatement
        and economic.mechanism_or_conceptual_logic_reconstructible,
        isinstance(economic, a.EconomicReaderAssessment)
        and economic.boundary_is_economically_interpretable
        and isinstance(cold, a.ColdReaderAssessment)
        and cold.boundary_discrimination_passed,
        isinstance(cold, a.ColdReaderAssessment) and cold.near_transfer_passed,
    )
    reader_outcome = assessment.target_reader_outcome
    if (
        reader_outcome.primary_audience != target.primary_audience
        or (
            reader_outcome.benchmark_delta_reconstructible,
            reader_outcome.operative_force_reconstructible,
            reader_outcome.boundary_reconstructible,
            reader_outcome.nearby_case_predictable,
        )
        != expected_reader_flags
        or not reader_evidence.issubset(
            {
                _exact_ref_key(item)
                for item in reader_outcome.evidence_refs
            }
        )
    ):
        raise ProfileCraftValidationError(
            "target-reader outcome lacks its exact audience/design/manuscript/review lineage"
        )


def _validate_closure_cross_refs(
    indices: _Indices, closure: pc.ProfileCraftClosure
) -> None:
    authoring_closure = _resolve_authoring(
        indices,
        closure.base_authoring_closure_ref,
        a.ReviewClosure,
        "profile/craft base authoring closure",
    )
    unit = _resolve_authoring(
        indices,
        closure.manuscript_unit_ref,
        a.ManuscriptUnit,
        "profile/craft manuscript",
    )
    diagnosis = _resolve_profile(
        indices,
        closure.reader_problem_diagnosis_ref,
        pc.ReaderProblemDiagnosis,
        "profile/craft diagnosis",
    )
    stack = _resolve_profile(
        indices,
        closure.profile_stack.entity_ref,
        pc.ResolvedProfileStack,
        "profile/craft stack",
    )
    selection = _resolve_profile(
        indices,
        closure.craft_selection.entity_ref,
        pc.CraftSelectionManifest,
        "profile/craft selection",
    )
    assessment = _resolve_profile(
        indices,
        closure.realization_assessment.entity_ref,
        pc.CraftRealizationAssessment,
        "profile/craft assessment",
    )
    audits = tuple(
        _resolve_profile(
            indices,
            binding.entity_ref,
            pc.PredicateMappingAudit,
            "profile/craft predicate audit",
        )
        for binding in closure.predicate_mapping_audits
    )
    expected_hashes = (
        (closure.base_authoring_closure_hash, authoring_closure),
        (closure.manuscript_unit_hash, unit),
        (closure.reader_problem_diagnosis_hash, diagnosis),
        (closure.profile_stack.payload_hash, stack),
        (closure.craft_selection.payload_hash, selection),
        (closure.realization_assessment.payload_hash, assessment),
    )
    if any(expected != _payload_hash(payload) for expected, payload in expected_hashes):
        raise ProfileCraftValidationError("profile/craft closure payload hash mismatches")
    for binding, audit in zip(closure.predicate_mapping_audits, audits):
        if binding.payload_hash != _payload_hash(audit):
            raise ProfileCraftValidationError(
                "profile/craft closure predicate-audit hash mismatches"
            )
    typed_audits: list[pc.PredicateMappingAudit] = []
    contracts_and_audits: list[
        tuple[pc.ObligationPredicateContract, pc.PredicateMappingAudit]
    ] = []
    for audit in audits:
        assert isinstance(audit, pc.PredicateMappingAudit)
        _validate_mapping_audit(indices, audit)
        contract = _resolve_profile(
            indices,
            audit.contract_ref,
            pc.ObligationPredicateContract,
            "profile/craft closure predicate contract",
        )
        assert isinstance(contract, pc.ObligationPredicateContract)
        typed_audits.append(audit)
        contracts_and_audits.append((contract, audit))
    expected_coverage_classes = tuple(
        audit.contract_coverage_class for audit in typed_audits
    )
    if closure.predicate_mapping_coverage_classes != expected_coverage_classes:
        raise ProfileCraftValidationError(
            "profile/craft closure coverage classes do not exactly project audit order"
        )
    expected_limitations = _ordered_predicate_limitation_union(
        contracts_and_audits
    )
    if closure.predicate_limitation_kinds != expected_limitations:
        raise ProfileCraftValidationError(
            "profile/craft closure predicate limitations do not exactly project "
            "the bounded audits"
        )
    assert isinstance(authoring_closure, a.ReviewClosure)
    assert isinstance(unit, a.ManuscriptUnit)
    assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
    assert isinstance(selection, pc.CraftSelectionManifest)
    assert isinstance(assessment, pc.CraftRealizationAssessment)
    if (
        authoring_closure.status != "authoring_ready"
        or authoring_closure.manuscript_unit_ref != closure.manuscript_unit_ref
        or closure.base_authoring_closure_outcome != "authoring_ready"
        or diagnosis.profile_stack_ref != closure.profile_stack.entity_ref
        or selection.profile_stack_ref != closure.profile_stack.entity_ref
        or selection.diagnosis_ref != closure.reader_problem_diagnosis_ref
        or assessment.selection_manifest_ref != closure.craft_selection.entity_ref
        or assessment.manuscript_unit_ref != closure.manuscript_unit_ref
        or assessment.base_authoring_closure_ref
        != closure.base_authoring_closure_ref
        or assessment.formal_fidelity_review_ref
        != authoring_closure.formal_fidelity_review_ref
        or assessment.economic_reader_review_ref
        != authoring_closure.economic_reader_review_ref
        or assessment.cold_reader_review_ref
        != authoring_closure.cold_reader_review_ref
    ):
        raise ProfileCraftValidationError(
            "profile/craft closure does not form one exact authoring/profile/craft topology"
        )
    checks = {item.check_kind: item for item in closure.checks}
    craft_check = checks["craft_realization"]
    reader_check = checks["target_reader_fit"]
    if craft_check.outcome != (
        "pass" if assessment.outcome == "pass" else "fail"
    ) or _exact_ref_key(closure.realization_assessment.entity_ref) not in {
        _exact_ref_key(item) for item in craft_check.evidence_refs
    }:
        raise ProfileCraftValidationError(
            "craft-realization closure check is not derived from its exact assessment"
        )
    required_reader_evidence = {
        _exact_ref_key(closure.realization_assessment.entity_ref),
        *(
            _exact_ref_key(item)
            for item in assessment.target_reader_outcome.evidence_refs
        ),
    }
    if reader_check.outcome != (
        "pass" if assessment.target_reader_outcome.outcome == "pass" else "fail"
    ) or required_reader_evidence != {
        _exact_ref_key(item) for item in reader_check.evidence_refs
    }:
        raise ProfileCraftValidationError(
            "target-reader-fit closure check is not derived from its exact reader outcome"
        )


def validate_profile_craft_ready(
    snapshot: Snapshot, closure_ref: EntityVersionRef
) -> None:
    """Derive the noncompensatory Phase 4 readiness predicate."""

    indices = _build_indices(snapshot)
    closure = _resolve_profile(
        indices, closure_ref, pc.ProfileCraftClosure, "profile/craft closure"
    )
    assert isinstance(closure, pc.ProfileCraftClosure)
    closure_entity = indices.entities.get(_entity_key(closure_ref))
    if closure_entity is None or not _is_current_and_fresh(snapshot, closure_entity):
        raise ProfileCraftValidationError("ProfileCraftClosure is not current and fresh")
    if closure.outcome != "ready":
        raise ProfileCraftValidationError("ProfileCraftClosure is blocked")
    _validate_closure_cross_refs(indices, closure)

    exact_dependencies = (
        closure.base_authoring_closure_ref,
        closure.manuscript_unit_ref,
        closure.reader_problem_diagnosis_ref,
        closure.profile_stack.entity_ref,
        closure.craft_selection.entity_ref,
        *(item.entity_ref for item in closure.predicate_mapping_audits),
        closure.realization_assessment.entity_ref,
    )
    for reference in exact_dependencies:
        entity = indices.entities.get(_entity_key(reference))
        if entity is None or not _is_current_and_fresh(snapshot, entity):
            raise ProfileCraftValidationError(
                "profile/craft readiness has a non-current or stale dependency"
            )

    stack = _resolve_profile(
        indices,
        closure.profile_stack.entity_ref,
        pc.ResolvedProfileStack,
        "ready profile stack",
    )
    assert isinstance(stack, pc.ResolvedProfileStack)
    _validate_profile_stack(indices, stack)
    target = _resolve_profile(
        indices, stack.target_profile_ref, pc.TargetProfile, "ready target profile"
    )
    assert isinstance(target, pc.TargetProfile)
    validate_target_profile(snapshot, target, require_current=True, indices=indices)
    target_entity = indices.entities.get(_entity_key(stack.target_profile_ref))
    if target_entity is None or not _is_current_and_fresh(snapshot, target_entity):
        raise ProfileCraftValidationError("ready TargetProfile is not current and fresh")

    diagnosis = _resolve_profile(
        indices,
        closure.reader_problem_diagnosis_ref,
        pc.ReaderProblemDiagnosis,
        "ready diagnosis",
    )
    assessment = _resolve_profile(
        indices,
        closure.realization_assessment.entity_ref,
        pc.CraftRealizationAssessment,
        "ready craft assessment",
    )
    assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
    assert isinstance(assessment, pc.CraftRealizationAssessment)
    _validate_diagnosis(indices, diagnosis)
    if (
        diagnosis.inspected_manuscript_unit_binding is None
        or not diagnosis.diagnostic_review_bindings
        or not diagnosis.diagnostic_finding_bindings
    ):
        raise ProfileCraftValidationError(
            "ready closure requires a review-grounded diagnosis; "
            "a pre-manuscript diagnosis cannot become ready"
        )
    selection = _resolve_profile(
        indices,
        closure.craft_selection.entity_ref,
        pc.CraftSelectionManifest,
        "ready craft selection",
    )
    assert isinstance(selection, pc.CraftSelectionManifest)
    _validate_selection(indices, selection)
    _validate_assessment(indices, assessment)
    if not isinstance(diagnosis, pc.ReaderProblemDiagnosis) or (
        diagnosis.upstream_science_status != "resolved" or not diagnosis.craft_eligible
    ):
        raise ProfileCraftValidationError(
            "ready closure requires a resolved craft-eligible diagnosis"
        )
    if not isinstance(assessment, pc.CraftRealizationAssessment) or assessment.outcome != "pass":
        raise ProfileCraftValidationError(
            "ready closure requires a passing craft realization assessment"
        )
    audits: list[pc.PredicateMappingAudit] = []
    for binding in closure.predicate_mapping_audits:
        resolved_audit = _resolve_profile(
            indices,
            binding.entity_ref,
            pc.PredicateMappingAudit,
            "ready predicate mapping audit",
        )
        assert isinstance(resolved_audit, pc.PredicateMappingAudit)
        _validate_mapping_audit(indices, resolved_audit)
        audits.append(resolved_audit)

    base_closure = _resolve_authoring(
        indices,
        closure.base_authoring_closure_ref,
        a.ReviewClosure,
        "ready base authoring closure",
    )
    assert isinstance(base_closure, a.ReviewClosure)
    assurance = _resolve_authoring(
        indices,
        base_closure.assurance_bundle_ref,
        a.AssuranceBundle,
        "ready AssuranceBundle",
    )
    assert isinstance(assurance, a.AssuranceBundle)
    _validate_bounded_audits_against_assurance(
        indices, audits, assurance, base_closure.assurance_bundle_ref
    )

    try:
        validate_authoring_ready(snapshot, closure.base_authoring_closure_ref)
    except AuthoringValidationError as exc:
        raise ProfileCraftValidationError(
            "base Phase 3 authoring closure is not authoring-ready"
        ) from exc


def validate_profile_craft_projection(
    snapshot: Snapshot,
) -> ProfileCraftProjectionReport:
    """Resolve every Phase 4 payload without making historical readiness sticky."""

    indices = _build_indices(snapshot)
    for payload in indices.profile_payloads.values():
        if isinstance(payload, pc.TargetProfile):
            validate_target_profile(
                snapshot, payload, require_current=False, indices=indices
            )
        elif isinstance(payload, pc.ResolvedProfileStack):
            _validate_profile_stack(indices, payload)
        elif isinstance(payload, pc.ReaderProblemDiagnosis):
            _validate_diagnosis(indices, payload)
        elif isinstance(payload, pc.CraftSelectionManifest):
            _validate_selection(indices, payload)
        elif isinstance(payload, pc.ObligationPredicateContract):
            _validate_predicate_contract(indices, payload)
        elif isinstance(payload, pc.PredicateMappingAudit):
            _validate_mapping_audit(indices, payload)
        elif isinstance(payload, pc.CraftRealizationAssessment):
            _validate_assessment(indices, payload)
        elif isinstance(payload, pc.ProfileCraftClosure):
            _validate_closure_cross_refs(indices, payload)

    ready: list[EntityVersionRef] = []
    for key, payload in indices.profile_payloads.items():
        if not isinstance(payload, pc.ProfileCraftClosure) or payload.outcome != "ready":
            continue
        entity = indices.entities[key]
        if not _is_current_and_fresh(snapshot, entity):
            continue

        exact_dependencies = (
            payload.base_authoring_closure_ref,
            payload.manuscript_unit_ref,
            payload.reader_problem_diagnosis_ref,
            payload.profile_stack.entity_ref,
            payload.craft_selection.entity_ref,
            *(item.entity_ref for item in payload.predicate_mapping_audits),
            payload.realization_assessment.entity_ref,
        )
        if any(
            (dependency := indices.entities.get(_entity_key(reference))) is None
            or not _is_current_and_fresh(snapshot, dependency)
            for reference in exact_dependencies
        ):
            continue

        stack = _resolve_profile(
            indices,
            payload.profile_stack.entity_ref,
            pc.ResolvedProfileStack,
            "projected ready profile stack",
        )
        assert isinstance(stack, pc.ResolvedProfileStack)
        target = _resolve_profile(
            indices,
            stack.target_profile_ref,
            pc.TargetProfile,
            "projected ready target profile",
        )
        assert isinstance(target, pc.TargetProfile)
        target_entity = indices.entities.get(_entity_key(stack.target_profile_ref))
        if target_entity is None or not _is_current_and_fresh(snapshot, target_entity):
            continue
        try:
            validate_target_profile(
                snapshot, target, require_current=True, indices=indices
            )
        except ProfileCraftValidationError:
            continue
        ready.append(_entity_ref(entity))
    return ProfileCraftProjectionReport(
        parsed_entity_count=len(indices.profile_payloads),
        ready_closure_refs=tuple(sorted(ready, key=lambda item: (item.entity_id, item.version))),
    )


def _require_counts(
    route: RouteSpecV4, entities: Sequence[EntityVersion], *, output: bool
) -> None:
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity.entity_type] = counts.get(entity.entity_type, 0) + 1
    requirements = route.required_output_entities if output else route.required_input_entities
    permitted = {item.entity_type for item in requirements}
    unexpected = sorted(set(counts).difference(permitted))
    if unexpected:
        raise ProfileCraftValidationError(
            f"route {route.route_id} received disallowed entity types: "
            + ", ".join(unexpected)
        )
    for requirement in requirements:
        count = counts.get(requirement.entity_type, 0)
        if count < requirement.min_count or (
            requirement.max_count is not None and count > requirement.max_count
        ):
            raise ProfileCraftValidationError(
                f"route {route.route_id} has invalid {requirement.entity_type} cardinality"
            )


def _input_maps(
    entities: Sequence[EntityVersion], indices: _Indices
) -> tuple[
    Mapping[str, tuple[EntityVersionRef, ...]],
    Mapping[str, tuple[object, ...]],
]:
    refs: dict[str, list[EntityVersionRef]] = {}
    payloads: dict[str, list[object]] = {}
    for entity in entities:
        refs.setdefault(entity.entity_type, []).append(_entity_ref(entity))
        key = _entity_key(entity)
        payload = (
            indices.profile_payloads.get(key)
            or indices.authoring_payloads.get(key)
            or indices.theory_payloads.get(key)
        )
        if payload is None:
            raise ProfileCraftValidationError(
                "Phase 4 route inputs must be packed typed entities"
            )
        payloads.setdefault(entity.entity_type, []).append(payload)
    return (
        {key: tuple(value) for key, value in refs.items()},
        {key: tuple(value) for key, value in payloads.items()},
    )


def _one_ref(
    refs: Mapping[str, tuple[EntityVersionRef, ...]], entity_type: str
) -> EntityVersionRef:
    values = refs.get(entity_type, ())
    if len(values) != 1:
        raise ProfileCraftValidationError(f"expected one exact {entity_type}")
    return values[0]


def _one_payload(
    payloads: Mapping[str, tuple[object, ...]], entity_type: str, expected: type[object]
) -> object:
    values = payloads.get(entity_type, ())
    if len(values) != 1 or not isinstance(values[0], expected):
        raise ProfileCraftValidationError(f"expected one exact {entity_type} payload")
    return values[0]


def _validate_entry_topology(
    route_id: str,
    refs: Mapping[str, tuple[EntityVersionRef, ...]],
    payloads: Mapping[str, tuple[object, ...]],
    indices: _Indices,
    *,
    actor: Actor,
) -> None:
    if route_id in {"map.obligation_predicate", "audit.obligation_predicate"}:
        assurance = _one_payload(payloads, "AssuranceBundle", a.AssuranceBundle)
        assert isinstance(assurance, a.AssuranceBundle)
        if (
            _one_ref(refs, "ClaimGraph") != assurance.claim_graph_ref
            or _one_ref(refs, "FormalModel") != assurance.formal_model_ref
            or _one_ref(refs, "AssumptionMap") != assurance.assumption_map_ref
        ):
            raise ProfileCraftValidationError(
                "predicate route scientific inputs belong to another assurance bundle"
            )
        obligation_ref = _one_ref(refs, "ProofObligation")
        covered = {
            item.obligation_ref for item in assurance.proof_audits
        } | {item.obligation_ref for item in assurance.tool_receipts}
        if obligation_ref not in covered:
            raise ProfileCraftValidationError(
                "predicate route obligation is absent from assurance coverage"
            )
        if actor.kind == "deterministic_tool":
            raise ProfileCraftValidationError(
                "obligation mapping and audit require a human or agent"
            )
        if route_id == "audit.obligation_predicate":
            contract = _one_payload(
                payloads,
                "ObligationPredicateContract",
                pc.ObligationPredicateContract,
            )
            assert isinstance(contract, pc.ObligationPredicateContract)
            if (
                contract.assurance_bundle_ref != _one_ref(refs, "AssuranceBundle")
                or contract.assurance_bundle_hash != _payload_hash(assurance)
                or contract.obligation_ref != obligation_ref
                or contract.claim_graph_ref != _one_ref(refs, "ClaimGraph")
                or contract.formal_model_ref != _one_ref(refs, "FormalModel")
                or contract.assumption_map_ref != _one_ref(refs, "AssumptionMap")
                or actor == contract.mapper
            ):
                raise ProfileCraftValidationError(
                    "predicate audit input topology or actor independence is invalid"
                )
            _validate_predicate_auditor_independence(
                indices,
                auditor=actor,
                mapper=contract.mapper,
                assurance_ref=contract.assurance_bundle_ref,
            )
            _validate_contract_receipt_bound(assurance, contract)
        return

    if route_id == "resolve.profile_stack":
        if actor.kind != "deterministic_tool":
            raise ProfileCraftValidationError(
                "profile resolution requires a deterministic actor"
            )
        paper = _one_payload(payloads, "PaperIR", a.PaperIR)
        reader = _one_payload(payloads, "ReaderPath", a.ReaderPath)
        minimal = _one_payload(
            payloads, "ResolvedProfileManifest", a.ResolvedProfileManifest
        )
        assurance = _one_payload(payloads, "AssuranceBundle", a.AssuranceBundle)
        assert isinstance(paper, a.PaperIR)
        assert isinstance(reader, a.ReaderPath)
        assert isinstance(minimal, a.ResolvedProfileManifest)
        assert isinstance(assurance, a.AssuranceBundle)
        package_ref = _one_ref(refs, "ValidatedArgumentPackage")
        if (
            paper.package_ref != package_ref
            or paper.assurance_bundle_ref != _one_ref(refs, "AssuranceBundle")
            or paper.resolved_profile_manifest_ref
            != _one_ref(refs, "ResolvedProfileManifest")
            or reader.paper_ir_ref != _one_ref(refs, "PaperIR")
            or assurance.package_ref != package_ref
        ):
            raise ProfileCraftValidationError("profile resolution inputs cross lineages")
        audits = payloads.get("PredicateMappingAudit", ())
        if not audits or any(
            not isinstance(item, pc.PredicateMappingAudit)
            or not audit_is_approved_bounded(item)
            for item in audits
        ):
            raise ProfileCraftValidationError(
                "profile resolution requires approved bounded mapping audits"
            )
        _validate_bounded_audits_against_assurance(
            indices,
            (item for item in audits if isinstance(item, pc.PredicateMappingAudit)),
            assurance,
            _one_ref(refs, "AssuranceBundle"),
        )
        return

    if route_id in {
        "diagnose.reader_problem",
        "retrieve.craft_moves",
        "compose.profiled_manuscript_unit",
        "review.craft_realization",
    }:
        paper = _one_payload(payloads, "PaperIR", a.PaperIR)
        stack = _one_payload(
            payloads, "ResolvedProfileStack", pc.ResolvedProfileStack
        )
        assert isinstance(paper, a.PaperIR)
        assert isinstance(stack, pc.ResolvedProfileStack)
        paper_ref = _one_ref(refs, "PaperIR")
        stack_ref = _one_ref(refs, "ResolvedProfileStack")
        target = _resolve_profile(
            indices,
            stack.target_profile_ref,
            pc.TargetProfile,
            "profile/craft route TargetProfile",
        )
        assert isinstance(target, pc.TargetProfile)
        if target.package_ref != paper.package_ref:
            raise ProfileCraftValidationError(
                "profile stack target belongs to another scientific package"
            )
        reader = _one_payload(payloads, "ReaderPath", a.ReaderPath)
        contracts = _one_payload(
            payloads, "ResultContractSet", a.ResultContractSet
        )
        assert isinstance(reader, a.ReaderPath)
        assert isinstance(contracts, a.ResultContractSet)
        reader_ref = _one_ref(refs, "ReaderPath")
        contracts_ref = _one_ref(refs, "ResultContractSet")
        if (
            reader.paper_ir_ref != paper_ref
            or contracts.paper_ir_ref != paper_ref
            or contracts.reader_path_ref != reader_ref
        ):
            raise ProfileCraftValidationError(
                "profile/craft route ReaderPath or ResultContractSet crosses lineages"
            )
        if route_id == "diagnose.reader_problem":
            unit_refs = refs.get("ManuscriptUnit", ())
            review_refs = refs.get("ReviewRecord", ())
            finding_refs = refs.get("ReviewFinding", ())
            closure_refs = refs.get("ReviewClosure", ())
            brief_refs = refs.get("RevisionBrief", ())
            if not unit_refs:
                if review_refs or finding_refs or closure_refs or brief_refs:
                    raise ProfileCraftValidationError(
                        "pre-manuscript diagnosis cannot receive review evidence"
                    )
            else:
                if len(closure_refs) != 1 or len(brief_refs) != 1:
                    raise ProfileCraftValidationError(
                        "post-manuscript diagnosis requires one blocked closure and RevisionBrief"
                    )
                unit = _one_payload(payloads, "ManuscriptUnit", a.ManuscriptUnit)
                blocked = _one_payload(payloads, "ReviewClosure", a.ReviewClosure)
                brief = _one_payload(payloads, "RevisionBrief", a.RevisionBrief)
                assert isinstance(unit, a.ManuscriptUnit)
                assert isinstance(blocked, a.ReviewClosure)
                assert isinstance(brief, a.RevisionBrief)
                if (
                    unit.paper_ir_ref != paper_ref
                    or unit.reader_path_ref != reader_ref
                    or unit.result_contract_set_ref
                    != contracts_ref
                    or not review_refs
                    or not finding_refs
                    or blocked.status != "blocked"
                    or blocked.paper_ir_ref != paper_ref
                    or blocked.reader_path_ref != reader_ref
                    or blocked.result_contract_set_ref != contracts_ref
                    or blocked.manuscript_unit_ref != unit_refs[0]
                    or blocked.revision_brief_ref != brief_refs[0]
                    or brief.manuscript_unit_ref != unit_refs[0]
                    or brief.review_closure_ref != closure_refs[0]
                ):
                    raise ProfileCraftValidationError(
                        "diagnosis manuscript/review evidence crosses lineages or is incomplete"
                    )
                reviews = payloads.get("ReviewRecord", ())
                findings = payloads.get("ReviewFinding", ())
                if any(
                    not isinstance(item, a.ReviewRecord)
                    or item.manuscript_unit_ref != unit_refs[0]
                    or item.reviewed_artifact_ref != unit.manuscript_artifact_ref
                    for item in reviews
                ) or any(
                    not isinstance(item, a.ReviewFinding)
                    or item.manuscript_unit_ref != unit_refs[0]
                    or item.reviewed_artifact_ref != unit.manuscript_artifact_ref
                    for item in findings
                ):
                    raise ProfileCraftValidationError(
                        "diagnosis reviews/findings belong to another manuscript"
                    )
                if {
                    reference
                    for item in reviews
                    if isinstance(item, a.ReviewRecord)
                    for reference in item.finding_refs
                }.intersection(finding_refs) != set(finding_refs) or set(
                    brief.finding_refs
                ) != set(finding_refs):
                    raise ProfileCraftValidationError(
                        "diagnosis route must receive every exact blocked RevisionBrief finding"
                    )
                closure_review_refs = {
                    blocked.formal_fidelity_review_ref,
                    blocked.economic_reader_review_ref,
                    blocked.cold_reader_review_ref,
                }
                if not set(review_refs).issubset(closure_review_refs):
                    raise ProfileCraftValidationError(
                        "diagnosis reviews are outside the blocked closure"
                    )
            if actor.kind == "deterministic_tool":
                raise ProfileCraftValidationError("reader diagnosis requires judgement")
            return

        diagnosis = _one_payload(
            payloads, "ReaderProblemDiagnosis", pc.ReaderProblemDiagnosis
        )
        assert isinstance(diagnosis, pc.ReaderProblemDiagnosis)
        if (
            diagnosis.paper_ir_ref != paper_ref
            or diagnosis.profile_stack_ref != stack_ref
            or diagnosis.reader_path_ref != reader_ref
            or diagnosis.result_contract_set_binding.entity_ref != contracts_ref
        ):
            raise ProfileCraftValidationError("diagnosis belongs to another design")
        if route_id == "retrieve.craft_moves":
            if actor.kind != "deterministic_tool":
                raise ProfileCraftValidationError(
                    "function-first craft retrieval requires a deterministic actor"
                )
            return

        selection = _one_payload(
            payloads, "CraftSelectionManifest", pc.CraftSelectionManifest
        )
        assert isinstance(selection, pc.CraftSelectionManifest)
        if (
            selection.diagnosis_ref != _one_ref(refs, "ReaderProblemDiagnosis")
            or selection.profile_stack_ref != stack_ref
        ):
            raise ProfileCraftValidationError("craft selection belongs to another design")
        if route_id == "compose.profiled_manuscript_unit":
            if actor != paper.canonical_writer:
                raise ProfileCraftValidationError(
                    "only the exact PaperIR canonical writer may compose"
                )
            minimal = _one_payload(
                payloads, "ResolvedProfileManifest", a.ResolvedProfileManifest
            )
            assert isinstance(minimal, a.ResolvedProfileManifest)
            if (
                paper.package_ref != _one_ref(refs, "ValidatedArgumentPackage")
                or paper.resolved_profile_manifest_ref
                != _one_ref(refs, "ResolvedProfileManifest")
                or contracts.paper_ir_ref != paper_ref
                or contracts.reader_path_ref != reader_ref
            ):
                raise ProfileCraftValidationError("profiled compose inputs cross lineages")
            expected_assurance = (
                ()
                if paper.assurance_bundle_ref is None
                else (paper.assurance_bundle_ref,)
            )
            if refs.get("AssuranceBundle", ()) != expected_assurance:
                raise ProfileCraftValidationError(
                    "profiled compose selected another AssuranceBundle"
                )
            prior_refs = refs.get("ManuscriptUnit", ())
            closure_refs = refs.get("ReviewClosure", ())
            brief_refs = refs.get("RevisionBrief", ())
            if not prior_refs:
                if closure_refs or brief_refs:
                    raise ProfileCraftValidationError(
                        "initial profiled composition cannot claim revision evidence"
                    )
            else:
                if len(closure_refs) != 1 or len(brief_refs) != 1:
                    raise ProfileCraftValidationError(
                        "profiled revision requires one blocked closure and RevisionBrief"
                    )
                prior = _one_payload(payloads, "ManuscriptUnit", a.ManuscriptUnit)
                closure = _one_payload(payloads, "ReviewClosure", a.ReviewClosure)
                brief = _one_payload(payloads, "RevisionBrief", a.RevisionBrief)
                assert isinstance(prior, a.ManuscriptUnit)
                assert isinstance(closure, a.ReviewClosure)
                assert isinstance(brief, a.RevisionBrief)
                if (
                    prior.paper_ir_ref != paper_ref
                    or prior.reader_path_ref != reader_ref
                    or prior.result_contract_set_ref
                    != _one_ref(refs, "ResultContractSet")
                    or closure.status != "blocked"
                    or closure.manuscript_unit_ref != prior_refs[0]
                    or closure.revision_brief_ref != brief_refs[0]
                    or brief.manuscript_unit_ref != prior_refs[0]
                    or brief.review_closure_ref != closure_refs[0]
                ):
                    raise ProfileCraftValidationError(
                        "profiled revision evidence does not form one failed-review lineage"
                    )
                _validate_revision_diagnosis_lineage(
                    indices,
                    diagnosis=diagnosis,
                    prior_ref=prior_refs[0],
                    closure_ref=closure_refs[0],
                    closure=closure,
                    brief_ref=brief_refs[0],
                    brief=brief,
                )
            return

        unit = _one_payload(payloads, "ManuscriptUnit", a.ManuscriptUnit)
        assert isinstance(unit, a.ManuscriptUnit)
        if (
            unit.paper_ir_ref != paper_ref
            or unit.reader_path_ref != reader_ref
            or unit.result_contract_set_ref != contracts_ref
            or actor == unit.canonical_writer
        ):
            raise ProfileCraftValidationError(
                "craft review manuscript lineage or actor independence is invalid"
            )
        if actor.kind == "deterministic_tool":
            raise ProfileCraftValidationError("craft review requires a human or agent")
        base = _one_payload(payloads, "ReviewClosure", a.ReviewClosure)
        reviews = payloads.get("ReviewRecord", ())
        assert isinstance(base, a.ReviewClosure)
        if len(reviews) != 3 or any(
            not isinstance(item, a.ReviewRecord) for item in reviews
        ):
            raise ProfileCraftValidationError(
                "craft review requires the exact three authoring ReviewRecords"
            )
        expected_review_refs = {
            base.formal_fidelity_review_ref,
            base.economic_reader_review_ref,
            base.cold_reader_review_ref,
        }
        observed_review_refs = set(refs.get("ReviewRecord", ()))
        if (
            base.status != "authoring_ready"
            or base.paper_ir_ref != paper_ref
            or base.reader_path_ref != reader_ref
            or base.result_contract_set_ref != contracts_ref
            or base.manuscript_unit_ref != _one_ref(refs, "ManuscriptUnit")
            or expected_review_refs != observed_review_refs
        ):
            raise ProfileCraftValidationError(
                "craft review is not grounded in one exact authoring-ready closure"
            )
        by_role = {
            item.role: item
            for item in reviews
            if isinstance(item, a.ReviewRecord)
        }
        if set(by_role) != {"formal_fidelity", "economic_reader", "cold_reader"}:
            raise ProfileCraftValidationError(
                "craft review requires one ReviewRecord for each canonical critic role"
            )
        if any(
            item.manuscript_unit_ref != _one_ref(refs, "ManuscriptUnit")
            or item.reviewed_artifact_ref != unit.manuscript_artifact_ref
            for item in by_role.values()
        ):
            raise ProfileCraftValidationError(
                "craft review records belong to another manuscript"
            )
        participants = (
            actor,
            unit.canonical_writer,
            by_role["formal_fidelity"].reviewer,
            by_role["economic_reader"].reviewer,
            by_role["cold_reader"].reviewer,
        )
        if len({_actor_key(item) for item in participants}) != len(participants):
            raise ProfileCraftValidationError(
                "craft assessor, writer, and three base reviewers must be pairwise distinct"
            )
        return

    if route_id == "close.profile_craft_review":
        if actor.kind != "deterministic_tool":
            raise ProfileCraftValidationError(
                "profile/craft closure requires a deterministic actor"
            )
        unit_ref = _one_ref(refs, "ManuscriptUnit")
        unit = _one_payload(payloads, "ManuscriptUnit", a.ManuscriptUnit)
        base = _one_payload(payloads, "ReviewClosure", a.ReviewClosure)
        assessment = _one_payload(
            payloads, "CraftRealizationAssessment", pc.CraftRealizationAssessment
        )
        selection_ref = _one_ref(refs, "CraftSelectionManifest")
        diagnosis_ref = _one_ref(refs, "ReaderProblemDiagnosis")
        stack_ref = _one_ref(refs, "ResolvedProfileStack")
        assert isinstance(unit, a.ManuscriptUnit)
        assert isinstance(base, a.ReviewClosure)
        assert isinstance(assessment, pc.CraftRealizationAssessment)
        if (
            base.status != "authoring_ready"
            or base.manuscript_unit_ref != unit_ref
            or assessment.manuscript_unit_ref != unit_ref
            or assessment.selection_manifest_ref != selection_ref
        ):
            raise ProfileCraftValidationError(
                "profile/craft closure inputs do not govern one ready manuscript"
            )
        selection = _one_payload(
            payloads, "CraftSelectionManifest", pc.CraftSelectionManifest
        )
        assert isinstance(selection, pc.CraftSelectionManifest)
        if selection.diagnosis_ref != diagnosis_ref or selection.profile_stack_ref != stack_ref:
            raise ProfileCraftValidationError("closure selection crosses profile lineages")
        audits = payloads.get("PredicateMappingAudit", ())
        if not audits or any(
            not isinstance(item, pc.PredicateMappingAudit)
            or not audit_is_approved_bounded(item)
            for item in audits
        ):
            raise ProfileCraftValidationError(
                "profile/craft closure requires approved bounded mapping audits"
            )
        assurance = _resolve_authoring(
            indices,
            base.assurance_bundle_ref,
            a.AssuranceBundle,
            "profile/craft closure AssuranceBundle",
        )
        assert isinstance(assurance, a.AssuranceBundle)
        _validate_bounded_audits_against_assurance(
            indices,
            (item for item in audits if isinstance(item, pc.PredicateMappingAudit)),
            assurance,
            base.assurance_bundle_ref,
        )
        if assessment.outcome != "pass":
            raise ProfileCraftValidationError(
                "profile/craft closure requires a passing craft assessment"
            )
        return

    raise ProfileCraftValidationError(f"unknown Phase 4 route: {route_id}")


def _validate_profile_craft_route_entry_refs(
    snapshot: Snapshot,
    route_spec: RouteSpecV4,
    references: tuple[EntityVersionRef, ...],
    *,
    actor: Actor,
) -> ProfileCraftRouteEntryReport:
    if (
        route_spec.route_id not in _PHASE4_ROUTES
        or route_spec.route_version != 4
        or route_spec.availability != "enabled"
        or route_spec.entry_validator_id != "profile_craft_route_entry.v1"
    ):
        raise ProfileCraftValidationError("unknown or malformed Phase 4 route")
    if len({_entity_key(item) for item in references}) != len(references):
        raise ProfileCraftValidationError("route input repeats an exact entity ref")
    indices = _build_indices(snapshot)
    entities: list[EntityVersion] = []
    for reference in references:
        entity = indices.entities.get(_entity_key(reference))
        if entity is None:
            raise ProfileCraftValidationError("route input is unresolved")
        if not _is_current_and_fresh(snapshot, entity):
            raise ProfileCraftValidationError("route input is not current and fresh")
        entities.append(entity)
    _require_counts(route_spec, entities, output=False)
    refs, payloads = _input_maps(entities, indices)
    _validate_entry_topology(
        route_spec.route_id, refs, payloads, indices, actor=actor
    )
    return ProfileCraftRouteEntryReport(
        route_id=route_spec.route_id,
        input_entity_refs=references,
        actor=actor,
    )


def validate_profile_craft_route_entry(
    snapshot: Snapshot,
    route_spec: RouteSpecV4,
    focus_entity_ids: Iterable[str],
    *,
    actor: Actor,
) -> ProfileCraftRouteEntryReport:
    focus = tuple(focus_entity_ids)
    if len(set(focus)) != len(focus):
        raise ProfileCraftValidationError("route focus IDs must be unique")
    current = {
        entity.entity_id: entity
        for entity in snapshot.entity_versions
        if snapshot.current_entities.get(entity.entity_id) == entity.version
    }
    missing = sorted(set(focus).difference(current))
    if missing:
        raise ProfileCraftValidationError(
            "route focus contains unknown current entities: " + ", ".join(missing)
        )
    return _validate_profile_craft_route_entry_refs(
        snapshot,
        route_spec,
        tuple(_entity_ref(current[entity_id]) for entity_id in focus),
        actor=actor,
    )


def _edge_exists(
    relations: Sequence[RelationVersion],
    source: EntityVersionRef,
    target: EntityVersionRef,
    relation_types: Iterable[str],
) -> bool:
    allowed = frozenset(relation_types)
    return any(
        item.source == source
        and item.target == target
        and item.relation_type in allowed
        and item.dependency_mode != "trace_only"
        and item.upstream is not None
        and item.downstream is not None
        for item in relations
    )


def _require_edge(
    relations: Sequence[RelationVersion],
    source: EntityVersionRef,
    target: EntityVersionRef,
    relation_types: Iterable[str],
    label: str,
) -> None:
    if not _edge_exists(relations, source, target, relation_types):
        raise ProfileCraftValidationError(f"{label} lacks its exact invalidating relation")


def _require_trace_edge(
    relations: Sequence[RelationVersion],
    source: EntityVersionRef,
    target: EntityVersionRef,
    relation_types: Iterable[str],
    label: str,
) -> None:
    allowed = frozenset(relation_types)
    if not any(
        item.source == source
        and item.target == target
        and item.relation_type in allowed
        and item.dependency_mode == "trace_only"
        and item.upstream is None
        and item.downstream is None
        for item in relations
    ):
        raise ProfileCraftValidationError(
            f"{label} lacks its exact non-invalidating repair trace"
        )


def _validate_relation_semantics(
    relation: RelationVersion,
    entities: Mapping[tuple[str, int], EntityVersion],
    produced_refs: frozenset[EntityVersionRef],
) -> None:
    source = entities.get(_entity_key(relation.source))
    target = entities.get(_entity_key(relation.target))
    if source is None or target is None:
        raise ProfileCraftValidationError("Phase 4 relation endpoint is unresolved")
    if source.project_id != target.project_id or relation.project_id != source.project_id:
        raise ProfileCraftValidationError("Phase 4 relation crosses the project boundary")
    if relation.source not in produced_refs and relation.target not in produced_refs:
        raise ProfileCraftValidationError("Phase 4 relation is disconnected from every output")
    source_owner = _owner_facet(source.entity_type)
    target_owner = _owner_facet(target.entity_type)
    if relation.dependency_mode != "trace_only":
        if (
            relation.upstream is None
            or relation.downstream is None
            or (source_owner is not None and relation.upstream.facet != source_owner)
            or (target_owner is not None and relation.downstream.facet != target_owner)
        ):
            raise ProfileCraftValidationError(
                "Phase 4 invalidating relation uses a non-owner semantic facet"
            )
        if (
            source.entity_type in pc.PROFILE_CRAFT_PAYLOAD_MODELS
            or source_owner == "terminology_presentation"
        ) and target.entity_type in t.THEORY_PAYLOAD_MODELS:
            raise ProfileCraftValidationError(
                "profile/presentation dependencies cannot invalidate scientific sources"
            )


def _output_payloads(
    entities: Sequence[EntityVersion], indices: _Indices
) -> Mapping[str, tuple[tuple[EntityVersionRef, object], ...]]:
    result: dict[str, list[tuple[EntityVersionRef, object]]] = {}
    for entity in entities:
        key = _entity_key(entity)
        payload = (
            indices.profile_payloads.get(key)
            or indices.authoring_payloads.get(key)
            or indices.theory_payloads.get(key)
        )
        if payload is None:
            raise ProfileCraftValidationError("Phase 4 output does not parse")
        result.setdefault(entity.entity_type, []).append((_entity_ref(entity), payload))
    return {key: tuple(value) for key, value in result.items()}


def _one_output(
    outputs: Mapping[str, tuple[tuple[EntityVersionRef, object], ...]],
    entity_type: str,
    expected: type[object],
) -> tuple[EntityVersionRef, object]:
    values = outputs.get(entity_type, ())
    if len(values) != 1 or not isinstance(values[0][1], expected):
        raise ProfileCraftValidationError(f"expected one {entity_type} output")
    return values[0]


def _route_output_topology(
    before: Snapshot,
    after: Snapshot,
    transaction: Transaction,
    route: RouteSpecV4,
    inputs: Mapping[str, tuple[EntityVersionRef, ...]],
    outputs: Mapping[str, tuple[tuple[EntityVersionRef, object], ...]],
    relations: Sequence[RelationVersion],
) -> None:
    indices = _build_indices(after)
    route_id = route.route_id
    if route_id == "map.obligation_predicate":
        output_ref, output = _one_output(
            outputs, "ObligationPredicateContract", pc.ObligationPredicateContract
        )
        assert isinstance(output, pc.ObligationPredicateContract)
        assurance = _resolve_authoring(
            indices,
            _one_ref(inputs, "AssuranceBundle"),
            a.AssuranceBundle,
            "predicate mapping AssuranceBundle",
        )
        assert isinstance(assurance, a.AssuranceBundle)
        if (
            output.assurance_bundle_ref != _one_ref(inputs, "AssuranceBundle")
            or output.assurance_bundle_hash != _payload_hash(assurance)
            or output.obligation_ref != _one_ref(inputs, "ProofObligation")
            or output.claim_graph_ref != _one_ref(inputs, "ClaimGraph")
            or output.formal_model_ref != _one_ref(inputs, "FormalModel")
            or output.assumption_map_ref != _one_ref(inputs, "AssumptionMap")
            or output.mapper != transaction.actor
        ):
            raise ProfileCraftValidationError("mapping output differs from exact inputs")
        _validate_contract_receipt_bound(assurance, output)
        _require_edge(relations, output.obligation_ref, output_ref, {"maps_to"}, "mapping")
        for source in (
            output.claim_graph_ref,
            output.formal_model_ref,
            output.assumption_map_ref,
            _one_ref(inputs, "AssuranceBundle"),
        ):
            _require_edge(relations, source, output_ref, {"depends_on"}, "mapping input")
        return

    if route_id == "audit.obligation_predicate":
        output_ref, output = _one_output(
            outputs, "PredicateMappingAudit", pc.PredicateMappingAudit
        )
        assert isinstance(output, pc.PredicateMappingAudit)
        contract_ref = _one_ref(inputs, "ObligationPredicateContract")
        if (
            output.contract_ref != contract_ref
            or output.auditor != transaction.actor
            or output.route_run_id != transaction.route_run_id
            or output.route_run_hash != transaction.route_run_hash
            or output.context_manifest_hash != transaction.context_manifest_hash
            or output.compiled_context_hash != transaction.compiled_context_hash
        ):
            raise ProfileCraftValidationError("predicate audit run/input lineage mismatches")
        _require_edge(relations, contract_ref, output_ref, {"validates"}, "mapping audit")
        return

    if route_id == "resolve.profile_stack":
        target_ref, target = _one_output(outputs, "TargetProfile", pc.TargetProfile)
        stack_ref, stack = _one_output(
            outputs, "ResolvedProfileStack", pc.ResolvedProfileStack
        )
        assert isinstance(target, pc.TargetProfile)
        assert isinstance(stack, pc.ResolvedProfileStack)
        if (
            target.package_ref != _one_ref(inputs, "ValidatedArgumentPackage")
            or stack.target_profile_ref != target_ref
            or stack.target_profile_hash != _payload_hash(target)
            or stack.resolved_by != transaction.actor
            or target.source_state_revision != before.head
            or stack.source_state_revision != before.head
        ):
            raise ProfileCraftValidationError("resolved profile output topology mismatches")
        validate_target_profile(after, target, require_current=True, indices=indices)
        required_decisions = set(target.human_decision_refs)
        if not required_decisions.issubset(set(transaction.evidence_refs)) or not {
            item.decision_id for item in required_decisions
        }.issubset(set(transaction.authority_basis)):
            raise ProfileCraftValidationError(
                "profile resolution omits exact Decision evidence/authority"
            )
        for source, label in (
            (target.package_ref, "profile package"),
            (target.paper_ir_ref, "profile PaperIR"),
            (target.reader_path_ref, "profile ReaderPath"),
            (target.base_profile_manifest_ref, "profile Phase 3 manifest"),
        ):
            _require_edge(
                relations,
                source,
                target_ref,
                {"depends_on"},
                label,
            )
        _require_edge(relations, target_ref, stack_ref, {"governs"}, "profile resolution")
        for audit_ref in inputs.get("PredicateMappingAudit", ()):
            _require_edge(relations, audit_ref, stack_ref, {"depends_on"}, "profile mapping")
        return

    if route_id == "diagnose.reader_problem":
        output_ref, output = _one_output(
            outputs, "ReaderProblemDiagnosis", pc.ReaderProblemDiagnosis
        )
        assert isinstance(output, pc.ReaderProblemDiagnosis)
        contracts_ref = _one_ref(inputs, "ResultContractSet")
        contracts = _resolve_authoring(
            indices, contracts_ref, a.ResultContractSet, "diagnosis output contracts"
        )
        assert isinstance(contracts, a.ResultContractSet)
        unit_refs = inputs.get("ManuscriptUnit", ())
        review_refs = inputs.get("ReviewRecord", ())
        finding_refs = inputs.get("ReviewFinding", ())
        closure_refs = inputs.get("ReviewClosure", ())
        brief_refs = inputs.get("RevisionBrief", ())
        expected_unit_binding: pc.ProjectPayloadBinding | None = None
        if unit_refs:
            unit_payload = _resolve_authoring(
                indices, unit_refs[0], a.ManuscriptUnit, "diagnosis output manuscript"
            )
            expected_unit_binding = pc.ProjectPayloadBinding(
                entity_ref=unit_refs[0], payload_hash=_payload_hash(unit_payload)
            )
        expected_review_bindings = tuple(
            pc.ProjectPayloadBinding(
                entity_ref=reference,
                payload_hash=_payload_hash(
                    _resolve_authoring(
                        indices,
                        reference,
                        a.ReviewRecord,
                        "diagnosis output review",
                    )
                ),
            )
            for reference in review_refs
        )
        expected_finding_bindings = tuple(
            pc.ProjectPayloadBinding(
                entity_ref=reference,
                payload_hash=_payload_hash(
                    _resolve_authoring(
                        indices,
                        reference,
                        a.ReviewFinding,
                        "diagnosis output finding",
                    )
                ),
            )
            for reference in finding_refs
        )
        expected_closure_binding = (
            None
            if not closure_refs
            else pc.ProjectPayloadBinding(
                entity_ref=closure_refs[0],
                payload_hash=_payload_hash(
                    _resolve_authoring(
                        indices,
                        closure_refs[0],
                        a.ReviewClosure,
                        "diagnosis output blocked closure",
                    )
                ),
            )
        )
        expected_brief_binding = (
            None
            if not brief_refs
            else pc.ProjectPayloadBinding(
                entity_ref=brief_refs[0],
                payload_hash=_payload_hash(
                    _resolve_authoring(
                        indices,
                        brief_refs[0],
                        a.RevisionBrief,
                        "diagnosis output RevisionBrief",
                    )
                ),
            )
        )
        if (
            output.paper_ir_ref != _one_ref(inputs, "PaperIR")
            or output.reader_path_ref != _one_ref(inputs, "ReaderPath")
            or output.profile_stack_ref != _one_ref(inputs, "ResolvedProfileStack")
            or output.result_contract_set_binding
            != pc.ProjectPayloadBinding(
                entity_ref=contracts_ref, payload_hash=_payload_hash(contracts)
            )
            or output.inspected_manuscript_unit_binding != expected_unit_binding
            or output.diagnostic_review_bindings != expected_review_bindings
            or output.diagnostic_finding_bindings != expected_finding_bindings
            or output.blocked_review_closure_binding
            != expected_closure_binding
            or output.revision_brief_binding != expected_brief_binding
            or output.diagnosed_by != transaction.actor
        ):
            raise ProfileCraftValidationError("diagnosis output differs from exact inputs")
        _require_edge(
            relations, output.paper_ir_ref, output_ref, {"diagnoses", "depends_on"}, "diagnosis"
        )
        for source in (
            output.reader_path_ref,
            output.profile_stack_ref,
            output.result_contract_set_binding.entity_ref,
        ):
            _require_edge(
                relations,
                source,
                output_ref,
                {"diagnoses", "depends_on"},
                "diagnosis evidence",
            )
        for source in (
            *(
                ()
                if output.inspected_manuscript_unit_binding is None
                else (output.inspected_manuscript_unit_binding.entity_ref,)
            ),
            *(item.entity_ref for item in output.diagnostic_review_bindings),
            *(item.entity_ref for item in output.diagnostic_finding_bindings),
            *(
                ()
                if output.blocked_review_closure_binding is None
                else (output.blocked_review_closure_binding.entity_ref,)
            ),
            *(
                ()
                if output.revision_brief_binding is None
                else (output.revision_brief_binding.entity_ref,)
            ),
        ):
            _require_trace_edge(
                relations,
                source,
                output_ref,
                {"diagnoses", "depends_on"},
                "diagnosis historical evidence",
            )
        return

    if route_id == "retrieve.craft_moves":
        output_ref, output = _one_output(
            outputs, "CraftSelectionManifest", pc.CraftSelectionManifest
        )
        assert isinstance(output, pc.CraftSelectionManifest)
        if (
            output.diagnosis_ref != _one_ref(inputs, "ReaderProblemDiagnosis")
            or output.profile_stack_ref != _one_ref(inputs, "ResolvedProfileStack")
            or output.selected_by != transaction.actor
        ):
            raise ProfileCraftValidationError("craft selection differs from exact inputs")
        _require_edge(
            relations, output.diagnosis_ref, output_ref, {"selects_for"}, "craft selection"
        )
        return

    if route_id == "compose.profiled_manuscript_unit":
        output_ref, output = _one_output(outputs, "ManuscriptUnit", a.ManuscriptUnit)
        assert isinstance(output, a.ManuscriptUnit)
        prior_refs = inputs.get("ManuscriptUnit", ())
        closure_refs = inputs.get("ReviewClosure", ())
        brief_refs = inputs.get("RevisionBrief", ())
        if (
            output.paper_ir_ref != _one_ref(inputs, "PaperIR")
            or output.reader_path_ref != _one_ref(inputs, "ReaderPath")
            or output.result_contract_set_ref != _one_ref(inputs, "ResultContractSet")
            or output.source_state_revision != before.head
            or output.canonical_writer != transaction.actor
            or (
                bool(prior_refs)
                and (
                    output.previous_manuscript_unit_ref != prior_refs[0]
                    or output.previous_manuscript_artifact_ref
                    != _resolve_authoring(
                        indices,
                        prior_refs[0],
                        a.ManuscriptUnit,
                        "profiled revision prior manuscript",
                    ).manuscript_artifact_ref
                    or output.revision_brief_ref != brief_refs[0]
                    or output.integration_generation
                    != _resolve_authoring(
                        indices,
                        prior_refs[0],
                        a.ManuscriptUnit,
                        "profiled revision prior generation",
                    ).integration_generation
                    + 1
                )
            )
            or (
                not prior_refs
                and (
                    output.integration_generation != 1
                    or output.previous_manuscript_unit_ref is not None
                    or output.previous_manuscript_artifact_ref is not None
                    or output.revision_brief_ref is not None
                )
            )
        ):
            raise ProfileCraftValidationError("profiled manuscript output crosses lineages")
        _require_edge(
            relations,
            _one_ref(inputs, "ResolvedProfileStack"),
            output_ref,
            {"governs"},
            "profiled manuscript",
        )
        _require_edge(
            relations,
            _one_ref(inputs, "CraftSelectionManifest"),
            output_ref,
            {"realizes"},
            "craft realization",
        )
        _require_edge(
            relations,
            _one_ref(inputs, "ReaderProblemDiagnosis"),
            output_ref,
            {"depends_on"},
            "diagnosed repair",
        )
        if prior_refs:
            for source, label in (
                (prior_refs[0], "profiled prior manuscript"),
                (closure_refs[0], "profiled blocked closure"),
                (brief_refs[0], "profiled revision brief"),
            ):
                _require_trace_edge(
                    relations,
                    source,
                    output_ref,
                    {"depends_on", "revises"},
                    label,
                )
        return

    if route_id == "review.craft_realization":
        output_ref, output = _one_output(
            outputs, "CraftRealizationAssessment", pc.CraftRealizationAssessment
        )
        assert isinstance(output, pc.CraftRealizationAssessment)
        base_ref = _one_ref(inputs, "ReviewClosure")
        review_refs = inputs.get("ReviewRecord", ())
        review_payloads = tuple(
            _resolve_authoring(
                indices, reference, a.ReviewRecord, "craft review input ReviewRecord"
            )
            for reference in review_refs
        )
        by_role = {
            review.role: (reference, review)
            for reference, review in zip(review_refs, review_payloads)
            if isinstance(review, a.ReviewRecord)
        }
        base = _resolve_authoring(
            indices, base_ref, a.ReviewClosure, "craft review input ReviewClosure"
        )
        assert isinstance(base, a.ReviewClosure)
        selection_ref = _one_ref(inputs, "CraftSelectionManifest")
        stack_ref = _one_ref(inputs, "ResolvedProfileStack")
        diagnosis_ref = _one_ref(inputs, "ReaderProblemDiagnosis")
        reader_ref = _one_ref(inputs, "ReaderPath")
        contracts_ref = _one_ref(inputs, "ResultContractSet")
        selection = _resolve_profile(
            indices,
            selection_ref,
            pc.CraftSelectionManifest,
            "craft review input selection",
        )
        stack = _resolve_profile(
            indices,
            stack_ref,
            pc.ResolvedProfileStack,
            "craft review input stack",
        )
        diagnosis = _resolve_profile(
            indices,
            diagnosis_ref,
            pc.ReaderProblemDiagnosis,
            "craft review input diagnosis",
        )
        reader = _resolve_authoring(
            indices,
            reader_ref,
            a.ReaderPath,
            "craft review input ReaderPath",
        )
        contracts = _resolve_authoring(
            indices,
            contracts_ref,
            a.ResultContractSet,
            "craft review input ResultContractSet",
        )
        if (
            output.selection_manifest_ref != selection_ref
            or output.selection_manifest_hash != _payload_hash(selection)
            or output.profile_stack_ref != stack_ref
            or output.profile_stack_hash != _payload_hash(stack)
            or output.reader_problem_diagnosis_ref != diagnosis_ref
            or output.reader_problem_diagnosis_hash != _payload_hash(diagnosis)
            or output.reader_path_ref != reader_ref
            or output.reader_path_hash != _payload_hash(reader)
            or output.result_contract_set_ref != contracts_ref
            or output.result_contract_set_hash != _payload_hash(contracts)
            or output.manuscript_unit_ref != _one_ref(inputs, "ManuscriptUnit")
            or output.base_authoring_closure_ref != base_ref
            or output.base_authoring_closure_hash != _payload_hash(base)
            or output.formal_fidelity_review_ref
            != by_role["formal_fidelity"][0]
            or output.formal_fidelity_review_hash
            != _payload_hash(by_role["formal_fidelity"][1])
            or output.economic_reader_review_ref
            != by_role["economic_reader"][0]
            or output.economic_reader_review_hash
            != _payload_hash(by_role["economic_reader"][1])
            or output.cold_reader_review_ref != by_role["cold_reader"][0]
            or output.cold_reader_review_hash
            != _payload_hash(by_role["cold_reader"][1])
            or output.assessor != transaction.actor
        ):
            raise ProfileCraftValidationError("craft assessment differs from exact inputs")
        _require_edge(
            relations, output.manuscript_unit_ref, output_ref, {"reviews"}, "craft review"
        )
        _require_edge(
            relations, base_ref, output_ref, {"depends_on", "validates"}, "craft review closure"
        )
        for source, label in (
            (selection_ref, "craft review selection"),
            (stack_ref, "craft review profile stack"),
            (diagnosis_ref, "craft review diagnosis"),
            (reader_ref, "craft review ReaderPath"),
            (contracts_ref, "craft review ResultContractSet"),
        ):
            _require_edge(
                relations,
                source,
                output_ref,
                {"depends_on", "validates"},
                label,
            )
        for review_ref in review_refs:
            _require_edge(
                relations,
                review_ref,
                output_ref,
                {"depends_on", "validates"},
                "craft review evidence",
            )
        return

    if route_id == "close.profile_craft_review":
        output_ref, output = _one_output(
            outputs, "ProfileCraftClosure", pc.ProfileCraftClosure
        )
        assert isinstance(output, pc.ProfileCraftClosure)
        if (
            output.base_authoring_closure_ref != _one_ref(inputs, "ReviewClosure")
            or output.manuscript_unit_ref != _one_ref(inputs, "ManuscriptUnit")
            or output.reader_problem_diagnosis_ref
            != _one_ref(inputs, "ReaderProblemDiagnosis")
            or output.profile_stack.entity_ref != _one_ref(inputs, "ResolvedProfileStack")
            or output.craft_selection.entity_ref
            != _one_ref(inputs, "CraftSelectionManifest")
            or output.realization_assessment.entity_ref
            != _one_ref(inputs, "CraftRealizationAssessment")
            or {item.entity_ref for item in output.predicate_mapping_audits}
            != set(inputs.get("PredicateMappingAudit", ()))
            or output.determined_by != transaction.actor
            or output.source_state_revision != before.head
        ):
            raise ProfileCraftValidationError("ProfileCraftClosure exact inputs mismatch")
        _require_edge(
            relations,
            output.base_authoring_closure_ref,
            output_ref,
            {"validates"},
            "base authoring closure",
        )
        _require_edge(
            relations,
            output.realization_assessment.entity_ref,
            output_ref,
            {"validates"},
            "craft closure assessment",
        )
        for source, label in (
            (output.manuscript_unit_ref, "profile/craft manuscript"),
            (output.reader_problem_diagnosis_ref, "profile/craft diagnosis"),
            (output.profile_stack.entity_ref, "profile/craft stack"),
            (output.craft_selection.entity_ref, "profile/craft selection"),
            *(
                (item.entity_ref, "profile/craft predicate audit")
                for item in output.predicate_mapping_audits
            ),
        ):
            _require_edge(
                relations,
                source,
                output_ref,
                {"depends_on", "validates", "governs"},
                label,
            )
        validate_profile_craft_ready(after, output_ref)
        return

    raise ProfileCraftValidationError(f"unknown Phase 4 output route: {route_id}")


def validate_profile_craft_route_transaction(
    snapshot: Snapshot, transaction: Transaction, route_spec: RouteSpecV4
) -> ProfileCraftProjectionReport:
    """Validate one additive v4 route transaction against its exact base."""

    if (
        transaction.origin != "route_run"
        or transaction.route_id != route_spec.route_id
        or route_spec.route_id not in _PHASE4_ROUTES
        or route_spec.route_version != 4
        or route_spec.availability != "enabled"
        or route_spec.exit_validator_id != "profile_craft_route_exit.v1"
    ):
        raise ProfileCraftValidationError(
            "transaction is not bound to an enabled Phase 4 route"
        )
    if transaction.project_id != snapshot.project_id:
        raise ProfileCraftValidationError("Phase 4 transaction crosses projects")
    if len({_exact_ref_key(item) for item in transaction.evidence_refs}) != len(
        transaction.evidence_refs
    ):
        raise ProfileCraftValidationError("Phase 4 transaction repeats exact evidence")

    input_refs = tuple(
        item for item in transaction.evidence_refs if isinstance(item, EntityVersionRef)
    )
    _validate_profile_craft_route_entry_refs(
        snapshot, route_spec, input_refs, actor=transaction.actor
    )

    prior_entities = {_entity_key(item): item for item in snapshot.entity_versions}
    prior_relations = {_relation_key(item): item for item in snapshot.relation_versions}
    produced_entities: list[EntityVersion] = []
    produced_relations: list[RelationVersion] = []
    produced_artifacts: list[ArtifactRegistration] = []
    produced_blockers = []
    outcomes: list[RecordRouteOutcomeOp] = []

    for operation in transaction.operations:
        if operation.op not in route_spec.allowed_operations:
            raise ProfileCraftValidationError(
                f"operation {operation.op} is outside the Phase 4 route allowlist"
            )
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            entity = operation.entity
            if entity.entity_type not in route_spec.allowed_entity_types:
                raise ProfileCraftValidationError("route emitted a disallowed entity type")
            previous = None
            if isinstance(operation, SupersedeEntityOp):
                previous = prior_entities.get(_entity_key(operation.previous))
                if previous is None or not _is_current_and_fresh(snapshot, previous):
                    raise ProfileCraftValidationError(
                        "route supersedes a non-current or stale entity"
                    )
            if entity.entity_type == "ManuscriptUnit":
                try:
                    validate_authoring_entity(entity, previous)
                except AuthoringValidationError as exc:
                    raise ProfileCraftValidationError(str(exc)) from exc
            else:
                validate_profile_craft_entity(entity, previous)
            produced_entities.append(entity)
        elif isinstance(operation, (CreateRelationOp, SupersedeRelationOp)):
            relation = operation.relation
            if relation.relation_type not in route_spec.allowed_relation_types:
                raise ProfileCraftValidationError("route emitted a disallowed relation type")
            if isinstance(operation, SupersedeRelationOp):
                previous = prior_relations.get(_relation_key(operation.previous))
                if (
                    previous is None
                    or snapshot.current_relations.get(previous.relation_id)
                    != previous.version
                ):
                    raise ProfileCraftValidationError(
                        "route supersedes a non-current relation"
                    )
            produced_relations.append(relation)
        elif isinstance(operation, RegisterArtifactOp):
            produced_artifacts.append(operation.artifact)
        elif isinstance(operation, RecordBlockerOp):
            produced_blockers.append(operation.blocker)
        elif isinstance(operation, RecordRouteOutcomeOp):
            outcomes.append(operation)
        else:
            raise ProfileCraftValidationError(
                "Phase 4 route contains an unsupported operation shape"
            )

    _require_counts(route_spec, produced_entities, output=True)
    relation_counts: dict[str, int] = {}
    for relation in produced_relations:
        relation_counts[relation.relation_type] = (
            relation_counts.get(relation.relation_type, 0) + 1
        )
    for requirement in route_spec.required_output_relations:
        count = relation_counts.get(requirement.relation_type, 0)
        if count < requirement.min_count or (
            requirement.max_count is not None and count > requirement.max_count
        ):
            raise ProfileCraftValidationError("route relation cardinality is invalid")
    if len(outcomes) != 1:
        raise ProfileCraftValidationError(
            "Phase 4 transaction requires exactly one RouteOutcome"
        )
    outcome = outcomes[0].outcome
    if (
        outcome.route_id != route_spec.route_id
        or outcome.route_run_id != transaction.route_run_id
    ):
        raise ProfileCraftValidationError("RouteOutcome is bound to another run")

    produced_keys = {
        *(_exact_ref_key(_entity_ref(item)) for item in produced_entities),
        *(
            _exact_ref_key(
                RelationVersionRef(relation_id=item.relation_id, version=item.version)
            )
            for item in produced_relations
        ),
        *(
            _exact_ref_key(
                ArtifactDependencyRef(
                    artifact_id=item.artifact_id,
                    version=item.version,
                    content_hash=item.content_hash,
                )
            )
            for item in produced_artifacts
        ),
        *(_exact_ref_key(BlockerRef(blocker_id=item.blocker_id)) for item in produced_blockers),
    }
    candidate_keys = {_exact_ref_key(item) for item in outcome.candidate_refs}
    if len(candidate_keys) != len(outcome.candidate_refs) or candidate_keys != produced_keys:
        raise ProfileCraftValidationError(
            "RouteOutcome candidate_refs must equal every produced exact object"
        )
    if outcome.outcome in {"failed", "interrupted", "rejected"} and (
        produced_entities or produced_relations
    ):
        raise ProfileCraftValidationError(
            "failed or rejected Phase 4 routes cannot commit semantic outputs"
        )

    all_entities = (*snapshot.entity_versions, *produced_entities)
    all_relations = (*snapshot.relation_versions, *produced_relations)
    all_artifacts = (*snapshot.artifacts, *produced_artifacts)
    current_entities = dict(snapshot.current_entities)
    current_relations = dict(snapshot.current_relations)
    current_artifacts = dict(snapshot.current_artifacts)
    for entity in produced_entities:
        current_entities[entity.entity_id] = entity.version
    for relation in produced_relations:
        current_relations[relation.relation_id] = relation.version
    for artifact in produced_artifacts:
        current_artifacts[artifact.artifact_id] = artifact.version
    after = snapshot.model_copy(
        update={
            "entity_versions": all_entities,
            "relation_versions": all_relations,
            "artifacts": all_artifacts,
            "route_outcomes": (*snapshot.route_outcomes, outcome),
            "blockers": (*snapshot.blockers, *produced_blockers),
            "current_entities": current_entities,
            "current_relations": current_relations,
            "current_artifacts": current_artifacts,
        }
    )

    complete_entities = {_entity_key(item): item for item in all_entities}
    produced_refs = frozenset(_entity_ref(item) for item in produced_entities)
    for relation in produced_relations:
        _validate_relation_semantics(relation, complete_entities, produced_refs)

    if route_spec.route_id == "compose.profiled_manuscript_unit":
        try:
            validate_authoring_projection(after)
        except AuthoringValidationError as exc:
            raise ProfileCraftValidationError(
                "profiled ManuscriptUnit violates frozen Phase 3 invariants"
            ) from exc
    projection = validate_profile_craft_projection(after)
    after_indices = _build_indices(after)
    input_entities = [
        after_indices.entities[_entity_key(reference)] for reference in input_refs
    ]
    input_by_type, _ = _input_maps(input_entities, after_indices)
    outputs = _output_payloads(produced_entities, after_indices)
    _route_output_topology(
        snapshot,
        after,
        transaction,
        route_spec,
        input_by_type,
        outputs,
        produced_relations,
    )
    return projection


# Public Phase-numbered names make the additive boundary explicit while the
# descriptive names remain available to existing callers.
validate_phase4_route_entry = validate_profile_craft_route_entry
validate_phase4_route_transaction = validate_profile_craft_route_transaction


__all__ = [
    "PROFILE_CRAFT_READY_VERSION",
    "ProfileCraftProjectionReport",
    "ProfileCraftRouteEntryReport",
    "ProfileCraftValidationError",
    "audit_is_approved_bounded",
    "validate_profile_craft_entity",
    "validate_profile_craft_projection",
    "validate_profile_craft_ready",
    "validate_profile_craft_route_entry",
    "validate_profile_craft_route_transaction",
    "validate_phase4_route_entry",
    "validate_phase4_route_transaction",
    "validate_target_profile",
]
