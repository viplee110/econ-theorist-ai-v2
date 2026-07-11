"""Deterministic, bounded route-context compilation.

``etai_lexical_v1`` is a provider-neutral budget estimator.  Its units are not
OpenAI, Anthropic, or any other model provider's tokens.  An adapter must
recompile a context against the provider tokenizer it actually uses.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .codec import canonical_json_bytes, sha256_digest
from .errors import PolicyError
from .models import (
    Actor,
    ArtifactRegistration,
    ContextManifest,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    PrivacyLabel,
    RelationVersion,
    RiskOrBlocker,
    RouteSpec,
    Snapshot,
)
from .policy import (
    DECISION_REGISTRY_VERSION,
    ISOLATION_POLICY,
    KERNEL_HASH,
    KERNEL_VERSION,
    ROUTE_REGISTRY_HASH,
    SELECTOR_VERSION,
    VALIDATOR_VERSION,
    instruction_bundle_bytes,
    theory_kernel,
)
from .route_registry import clearance_allows


TOKENIZER_ID = "etai_lexical_v1"


class ContextCompilationError(PolicyError):
    """A route context cannot be compiled without weakening its contract."""


class ContextAccessError(ContextCompilationError):
    """Required route material is outside the declared grants."""


class ContextBudgetError(ContextCompilationError):
    """Required exact material does not fit the declared lexical budget."""


@dataclass(frozen=True, slots=True)
class CompiledContext:
    """Provider-neutral compiled bytes and the fields needed by a manifest."""

    payload: Mapping[str, Any]
    encoded: bytes
    context_hash: str
    selected_entity_refs: tuple[EntityVersionRef, ...]
    omissions: tuple[str, ...]
    used_units: int


def _route_instructions(route: RouteSpec) -> tuple[str, ...]:
    """Decode the exact instruction bundle already pinned by the registry."""

    text = instruction_bundle_bytes(route).decode("utf-8")
    lines = tuple(line for line in text.split("\n") if line)
    if not lines:
        raise ContextCompilationError("route instruction bundle has no instructions")
    return lines


def lexical_units(text: str) -> int:
    """Count units under the explicit ``etai_lexical_v1`` estimator.

    ASCII letters form one maximal run, ASCII digits form one maximal run,
    underscores form one maximal run, whitespace costs zero, and every other
    Unicode code point costs one unit.  This definition is intentionally simple
    and independent of a provider vocabulary.
    """

    if not isinstance(text, str):
        raise TypeError("etai_lexical_v1 requires text")
    units = 0
    index = 0
    while index < len(text):
        character = text[index]
        if character.isspace():
            index += 1
            continue
        if "A" <= character <= "Z" or "a" <= character <= "z":
            index += 1
            while index < len(text) and (
                "A" <= text[index] <= "Z" or "a" <= text[index] <= "z"
            ):
                index += 1
            units += 1
            continue
        if "0" <= character <= "9":
            index += 1
            while index < len(text) and "0" <= text[index] <= "9":
                index += 1
            units += 1
            continue
        if character == "_":
            index += 1
            while index < len(text) and text[index] == "_":
                index += 1
            units += 1
            continue
        units += 1
        index += 1
    return units


def units_for_bytes(encoded: bytes) -> int:
    """Count lexical units in canonical UTF-8 context bytes."""

    try:
        text = encoded.decode("utf-8")
    except UnicodeDecodeError as exc:  # pragma: no cover - canonical encoder guards it
        raise ContextCompilationError("compiled context is not UTF-8") from exc
    return lexical_units(text)


def _entity_key(entity: EntityVersion) -> tuple[str, int]:
    return entity.entity_id, entity.version


def _relation_key(relation: RelationVersion) -> tuple[str, int]:
    return relation.relation_id, relation.version


def _decision_key(decision: Decision) -> tuple[str, int]:
    return decision.decision_id, decision.version


def _canonical_ref_id(reference: Any) -> str:
    """Return the stable ID carried by one typed canonical object ref."""

    for field in (
        "entity_id",
        "relation_id",
        "decision_id",
        "artifact_id",
        "blocker_id",
    ):
        value = getattr(reference, field, None)
        if isinstance(value, str):
            return value
    raise ContextCompilationError("canonical object ref has no typed stable ID")


def _entity_accessible(
    entity: EntityVersion,
    *,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> bool:
    if (
        "confirmatory_holdout" in entity.access_compartments
        and purpose != "confirmatory_evaluation"
    ):
        return False
    return clearance_allows(clearance, entity.privacy) and set(
        entity.access_compartments
    ).issubset(grants)


def _relation_accessible(
    relation: RelationVersion,
    *,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> bool:
    if (
        "confirmatory_holdout" in relation.access_compartments
        and purpose != "confirmatory_evaluation"
    ):
        return False
    return clearance_allows(clearance, relation.privacy) and set(
        relation.access_compartments
    ).issubset(grants)


def _decision_accessible(
    decision: Decision,
    *,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> bool:
    if (
        "confirmatory_holdout" in decision.access_compartments
        and purpose != "confirmatory_evaluation"
    ):
        return False
    return clearance_allows(clearance, decision.privacy) and set(
        decision.access_compartments
    ).issubset(grants)


def _blocker_accessible(
    blocker: RiskOrBlocker,
    *,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> bool:
    if (
        "confirmatory_holdout" in blocker.access_compartments
        and purpose != "confirmatory_evaluation"
    ):
        return False
    return clearance_allows(clearance, blocker.privacy) and set(
        blocker.access_compartments
    ).issubset(grants)


def _privacy_record_accessible(
    record: EntityVersion
    | RelationVersion
    | Decision
    | ArtifactRegistration
    | RiskOrBlocker,
    *,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> bool:
    compartments = record.access_compartments
    if "confirmatory_holdout" in compartments and purpose != "confirmatory_evaluation":
        return False
    return clearance_allows(clearance, record.privacy) and set(
        compartments
    ).issubset(grants)


def _current_reference_objects(
    snapshot: Snapshot,
) -> dict[str, EntityVersion | RelationVersion | Decision | ArtifactRegistration | RiskOrBlocker]:
    entities = {_entity_key(item): item for item in snapshot.entity_versions}
    relations = {_relation_key(item): item for item in snapshot.relation_versions}
    decisions = {_decision_key(item): item for item in snapshot.decisions}
    artifacts = {
        (item.artifact_id, item.version): item for item in snapshot.artifacts
    }
    current: dict[
        str,
        EntityVersion
        | RelationVersion
        | Decision
        | ArtifactRegistration
        | RiskOrBlocker,
    ] = {item.blocker_id: item for item in snapshot.blockers}
    for object_id, version in snapshot.current_entities.items():
        current[object_id] = entities[(object_id, version)]
    for object_id, version in snapshot.current_relations.items():
        current[object_id] = relations[(object_id, version)]
    for object_id, version in snapshot.current_decisions.items():
        current[object_id] = decisions[(object_id, version)]
    for object_id, version in snapshot.current_artifacts.items():
        current[object_id] = artifacts[(object_id, version)]
    return current


def _decision_references_accessible(
    snapshot: Snapshot,
    decision: Decision,
    *,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> bool:
    current = _current_reference_objects(snapshot)
    pending = {
        decision.subject_ref,
        *decision.evidence_refs,
        *decision.dissent_refs,
        *decision.affected_scopes,
    }
    if decision.scope_ref is not None:
        pending.add(decision.scope_ref)
    seen: set[str] = set()
    while pending:
        reference_id = min(pending)
        pending.remove(reference_id)
        if reference_id in seen:
            continue
        seen.add(reference_id)
        source = current.get(reference_id)
        if source is None:
            raise ContextCompilationError(
                f"Decision {decision.decision_id} has an unresolved current reference"
            )
        if not _privacy_record_accessible(
            source,
            clearance=clearance,
            grants=grants,
            purpose=purpose,
        ):
            return False
        if isinstance(source, Decision):
            pending.update(
                {
                    source.subject_ref,
                    *source.evidence_refs,
                    *source.dissent_refs,
                    *source.affected_scopes,
                }
            )
            if source.scope_ref is not None:
                pending.add(source.scope_ref)
        elif isinstance(source, EntityVersion) and source.scope_ref is not None:
            pending.add(source.scope_ref)
        elif isinstance(source, RelationVersion):
            if source.scope_ref is not None:
                pending.add(source.scope_ref)
            entity_versions = {
                (item.entity_id, item.version): item
                for item in snapshot.entity_versions
            }
            for endpoint in (source.source, source.target):
                entity = entity_versions.get((endpoint.entity_id, endpoint.version))
                if entity is None:
                    raise ContextCompilationError(
                        "Decision reference relation has an unresolved endpoint"
                    )
                if entity.scope_ref is not None:
                    pending.add(entity.scope_ref)
    return True


def _status_dependency_barrier(
    snapshot: Snapshot,
    entity: EntityVersion,
    *,
    selected_keys: set[tuple[str, int]],
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> str | None:
    """Return why an entity's derived status cannot enter this context."""

    status = snapshot.derived_status.get(entity.entity_id)
    if status is None:
        return None
    decisions = {
        (decision.decision_id, decision.version): decision
        for decision in snapshot.decisions
    }
    for references in status.acceptance_source_refs.values():
        for reference in references:
            decision = decisions.get((reference.decision_id, reference.version))
            if decision is None:
                raise ContextCompilationError(
                    "derived acceptance status has an unresolved exact Decision source"
                )
            if not _decision_accessible(
                decision,
                clearance=clearance,
                grants=grants,
                purpose=purpose,
            ):
                return "privacy"
    relations = {
        (relation.relation_id, relation.version): relation
        for relation in snapshot.relation_versions
    }
    entities = {
        (item.entity_id, item.version): item for item in snapshot.entity_versions
    }
    for reasons in status.stale_reasons.values():
        for reason in reasons:
            for evidence in reason.source_evidence:
                relation = relations.get(
                    (evidence.relation_id, evidence.relation_version)
                )
                source = entities.get(
                    (evidence.upstream.entity_id, evidence.upstream.version)
                )
                if relation is None or source is None:
                    raise ContextCompilationError(
                        "derived stale status has an unresolved exact dependency"
                    )
                if not _relation_accessible(
                    relation,
                    clearance=clearance,
                    grants=grants,
                    purpose=purpose,
                ) or not _entity_accessible(
                    source,
                    clearance=clearance,
                    grants=grants,
                    purpose=purpose,
                ):
                    return "privacy"
                if (source.entity_id, source.version) not in selected_keys:
                    return "dependency"
                if evidence.current_upstream_version is None:
                    continue
                current_source = entities.get(
                    (
                        evidence.upstream.entity_id,
                        evidence.current_upstream_version,
                    )
                )
                if current_source is None:
                    raise ContextCompilationError(
                        "derived stale status has an unresolved current upstream version"
                    )
                if not _entity_accessible(
                    current_source,
                    clearance=clearance,
                    grants=grants,
                    purpose=purpose,
                ):
                    return "privacy"
                if _entity_key(current_source) not in selected_keys:
                    return "dependency"
    return None


def _current_entities(snapshot: Snapshot) -> dict[tuple[str, int], EntityVersion]:
    all_versions = {_entity_key(entity): entity for entity in snapshot.entity_versions}
    current: dict[tuple[str, int], EntityVersion] = {}
    for entity_id, version in snapshot.current_entities.items():
        key = (entity_id, version)
        try:
            current[key] = all_versions[key]
        except KeyError as exc:
            raise ContextCompilationError(
                f"snapshot current entity index points to missing {entity_id}@{version}"
            ) from exc
    return current


def _current_relations(snapshot: Snapshot) -> tuple[RelationVersion, ...]:
    all_versions = {
        _relation_key(relation): relation for relation in snapshot.relation_versions
    }
    current: list[RelationVersion] = []
    for relation_id, version in snapshot.current_relations.items():
        key = (relation_id, version)
        try:
            current.append(all_versions[key])
        except KeyError as exc:
            raise ContextCompilationError(
                f"snapshot current relation index points to missing "
                f"{relation_id}@{version}"
            ) from exc
    return tuple(sorted(current, key=_relation_key))


def _effective_decisions(snapshot: Snapshot) -> tuple[Decision, ...]:
    versions = {_decision_key(decision): decision for decision in snapshot.decisions}
    refs: set[tuple[str, int]] = {
        (ref.decision_id, ref.version)
        for ref in snapshot.effective_decisions.values()
    }
    selected: list[Decision] = []
    for key in sorted(refs):
        try:
            selected.append(versions[key])
        except KeyError as exc:
            raise ContextCompilationError(
                f"effective Decision index points to missing {key[0]}@{key[1]}"
            ) from exc
    return tuple(selected)


def _status_source_decisions(
    snapshot: Snapshot, entity_ids: Iterable[str]
) -> tuple[Decision, ...]:
    """Resolve the exact Decisions that produced selected acceptance fields."""

    versions = {_decision_key(decision): decision for decision in snapshot.decisions}
    refs: set[tuple[str, int]] = set()
    for entity_id in entity_ids:
        status = snapshot.derived_status.get(entity_id)
        if status is None:
            continue
        for references in status.acceptance_source_refs.values():
            refs.update(
                (reference.decision_id, reference.version)
                for reference in references
            )
    selected: list[Decision] = []
    for key in sorted(refs):
        try:
            selected.append(versions[key])
        except KeyError as exc:
            raise ContextCompilationError(
                f"derived acceptance source points to missing {key[0]}@{key[1]}"
            ) from exc
    return tuple(selected)


def _decision_is_relevant(
    decision: Decision,
    selected_ids: frozenset[str],
    project_id: str,
) -> bool:
    return (
        decision.subject_ref == project_id
        or decision.subject_ref in selected_ids
        or decision.scope_ref in selected_ids
        or bool(selected_ids.intersection(decision.affected_scopes))
    )


def _blocker_is_relevant(
    blocker: RiskOrBlocker,
    selected_object_ids: frozenset[str],
    route_id: str,
) -> bool:
    return (
        blocker.required_route == route_id
        or not blocker.affected_refs
        or bool(
            selected_object_ids.intersection(
                _canonical_ref_id(reference)
                for reference in blocker.affected_refs
            )
        )
    )


def _required_slice(
    snapshot: Snapshot,
    *,
    route: RouteSpec,
    focus_entity_ids: tuple[str, ...],
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> tuple[
    dict[tuple[str, int], EntityVersion],
    dict[tuple[str, int], RelationVersion],
    tuple[Decision, ...],
]:
    all_entities = {_entity_key(entity): entity for entity in snapshot.entity_versions}
    all_relations = {
        _relation_key(relation): relation for relation in snapshot.relation_versions
    }
    current_entities = _current_entities(snapshot)
    by_current_id = {entity.entity_id: entity for entity in current_entities.values()}
    current_relations = _current_relations(snapshot)

    required_entities: dict[tuple[str, int], EntityVersion] = {}
    required_relations: dict[tuple[str, int], RelationVersion] = {}
    for entity_id in focus_entity_ids:
        try:
            entity = by_current_id[entity_id]
        except KeyError as exc:
            raise ContextCompilationError(
                f"focus entity is not current in snapshot: {entity_id}"
            ) from exc
        required_entities[_entity_key(entity)] = entity

    # A framing run without a focus still needs the canonical Project envelope.
    if route.route_id == "frame.question_and_benchmarks" and not required_entities:
        project_entities = sorted(
            (
                entity
                for entity in current_entities.values()
                if entity.entity_type == "Project"
            ),
            key=_entity_key,
        )
        if project_entities:
            required_entities[_entity_key(project_entities[0])] = project_entities[0]

    effective = _effective_decisions(snapshot)
    while True:
        before = set(required_entities)
        selected_refs = set(required_entities)

        # Exact invalidating ancestors are required, recursively.
        for relation in current_relations:
            target_key = (relation.target.entity_id, relation.target.version)
            if relation.dependency_mode == "trace_only" or target_key not in selected_refs:
                continue
            if not _relation_accessible(
                relation, clearance=clearance, grants=grants, purpose=purpose
            ):
                raise ContextAccessError(
                    f"required ancestor relation is not readable: "
                    f"{relation.relation_id}@{relation.version}"
                )
            source_key = (relation.source.entity_id, relation.source.version)
            try:
                source = all_entities[source_key]
            except KeyError as exc:
                raise ContextCompilationError(
                    f"ancestor relation references missing entity "
                    f"{source_key[0]}@{source_key[1]}"
                ) from exc
            required_relations[_relation_key(relation)] = relation
            required_entities[source_key] = source

        # Derived stale fields disclose both the bound upstream and the current
        # version/hash used in their comparison.  Carry those exact sources in
        # the required closure before the status itself can enter a context.
        for selected_entity in tuple(required_entities.values()):
            status = snapshot.derived_status.get(selected_entity.entity_id)
            if status is None:
                continue
            for reasons in status.stale_reasons.values():
                for reason in reasons:
                    for evidence in reason.source_evidence:
                        relation_key = (
                            evidence.relation_id,
                            evidence.relation_version,
                        )
                        relation = all_relations.get(relation_key)
                        if relation is None:
                            raise ContextCompilationError(
                                "derived stale status cites a missing exact relation"
                            )
                        if not _relation_accessible(
                            relation,
                            clearance=clearance,
                            grants=grants,
                            purpose=purpose,
                        ):
                            raise ContextAccessError(
                                "required stale-status relation is not readable: "
                                f"{relation.relation_id}@{relation.version}"
                            )
                        required_relations[relation_key] = relation
                        source_versions = {evidence.upstream.version}
                        if evidence.current_upstream_version is not None:
                            source_versions.add(evidence.current_upstream_version)
                        for version in source_versions:
                            source_key = (evidence.upstream.entity_id, version)
                            source = all_entities.get(source_key)
                            if source is None:
                                raise ContextCompilationError(
                                    "derived stale status cites a missing upstream version"
                                )
                            required_entities[source_key] = source

        # Exact scope records and addressable dissent are never summarized away.
        selected_ids = frozenset(entity.entity_id for entity in required_entities.values())
        relevant_decisions = tuple(
            decision
            for decision in effective
            if _decision_is_relevant(decision, selected_ids, snapshot.project_id)
        )
        status_decisions = _status_source_decisions(snapshot, selected_ids)
        required_decision_index = {
            _decision_key(decision): decision
            for decision in (*relevant_decisions, *status_decisions)
        }
        required_decisions = tuple(
            required_decision_index[key]
            for key in sorted(required_decision_index)
        )
        for decision in required_decisions:
            if not _decision_accessible(
                decision,
                clearance=clearance,
                grants=grants,
                purpose=purpose,
            ):
                raise ContextAccessError(
                    "required authority Decision is not readable: "
                    f"{decision.decision_id}@{decision.version}"
                )
            if not _decision_references_accessible(
                snapshot,
                decision,
                clearance=clearance,
                grants=grants,
                purpose=purpose,
            ):
                raise ContextAccessError(
                    "required Decision has a protected current reference: "
                    f"{decision.decision_id}@{decision.version}"
                )
        referenced_ids = {
            entity.scope_ref
            for entity in required_entities.values()
            if entity.scope_ref is not None
        }
        for decision in required_decisions:
            referenced_ids.update(decision.dissent_refs)
            if decision.scope_ref is not None:
                referenced_ids.add(decision.scope_ref)
        for entity_id in sorted(referenced_ids):
            entity = by_current_id.get(entity_id)
            if entity is None:
                raise ContextCompilationError(
                    f"required scope or dissent ref is not a current entity: {entity_id}"
                )
            required_entities[_entity_key(entity)] = entity

        if set(required_entities) == before:
            break

    for entity in required_entities.values():
        if not _entity_accessible(
            entity, clearance=clearance, grants=grants, purpose=purpose
        ):
            raise ContextAccessError(
                f"required entity is not readable: {entity.entity_id}@{entity.version}"
            )

    required_keys = set(required_entities)
    for entity in required_entities.values():
        barrier = _status_dependency_barrier(
            snapshot,
            entity,
            selected_keys=required_keys,
            clearance=clearance,
            grants=grants,
            purpose=purpose,
        )
        if barrier is not None:
            raise ContextAccessError(
                f"required derived status crosses a {barrier} boundary: "
                f"{entity.entity_id}@{entity.version}"
            )

    selected_ids = frozenset(entity.entity_id for entity in required_entities.values())
    selected_object_ids = frozenset(
        {
            *selected_ids,
            *(relation.relation_id for relation in required_relations.values()),
            *(
                reference.artifact_id
                for entity in required_entities.values()
                for reference in entity.artifact_refs
            ),
            *(
                decision.decision_id
                for decision in _status_source_decisions(snapshot, selected_ids)
            ),
        }
    )
    for blocker in snapshot.blockers:
        if _blocker_is_relevant(
            blocker, selected_object_ids, route.route_id
        ) and not (
            _blocker_accessible(
                blocker,
                clearance=clearance,
                grants=grants,
                purpose=purpose,
            )
        ):
            raise ContextAccessError(
                f"required blocker is not readable: {blocker.blocker_id}"
            )
    return required_entities, required_relations, effective


def _optional_neighbor_groups(
    snapshot: Snapshot,
    *,
    route: RouteSpec,
    focus_entity_ids: tuple[str, ...],
    selected: Mapping[tuple[str, int], EntityVersion],
    selected_relations: Mapping[tuple[str, int], RelationVersion],
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> tuple[
    tuple[
        tuple[
            EntityVersion,
            tuple[EntityVersion, ...],
            tuple[RelationVersion, ...],
        ],
        ...,
    ],
    tuple[str, ...],
]:
    all_entities = {_entity_key(entity): entity for entity in snapshot.entity_versions}
    relations_by_target: dict[tuple[str, int], list[RelationVersion]] = {}
    privacy_omissions: set[str] = set()
    selected_keys = set(selected)

    for relation in _current_relations(snapshot):
        relation_key = _relation_key(relation)
        source_key = (relation.source.entity_id, relation.source.version)
        target_key = (relation.target.entity_id, relation.target.version)
        if (
            source_key not in selected_keys
            or target_key in selected_keys
            or relation_key in selected_relations
        ):
            continue
        target = all_entities.get(target_key)
        if target is None:
            raise ContextCompilationError(
                f"neighbor relation references missing entity {target_key[0]}@{target_key[1]}"
            )
        if not _relation_accessible(
            relation, clearance=clearance, grants=grants, purpose=purpose
        ) or not _entity_accessible(
            target, clearance=clearance, grants=grants, purpose=purpose
        ):
            privacy_omissions.add(f"privacy:neighbor:{target.entity_id}@{target.version}")
            continue
        relations_by_target.setdefault(target_key, []).append(relation)

    groups: list[
        tuple[
            EntityVersion,
            tuple[EntityVersion, ...],
            tuple[RelationVersion, ...],
        ]
    ] = []
    for target_key in sorted(relations_by_target):
        target = all_entities[target_key]
        try:
            closure_entities, closure_relations, _ = _required_slice(
                snapshot,
                route=route,
                focus_entity_ids=tuple(
                    sorted((*focus_entity_ids, target.entity_id))
                ),
                clearance=clearance,
                grants=grants,
                purpose=purpose,
            )
        except ContextAccessError:
            privacy_omissions.add(
                f"privacy:neighbor:{target.entity_id}@{target.version}"
            )
            continue
        group_entities = tuple(
            sorted(
                (
                    entity
                    for key, entity in closure_entities.items()
                    if key not in selected_keys
                ),
                key=_entity_key,
            )
        )
        relation_values = {
            **closure_relations,
            **{
                _relation_key(relation): relation
                for relation in relations_by_target[target_key]
            },
        }
        group_relations = tuple(
            sorted(
                (
                    relation
                    for key, relation in relation_values.items()
                    if key not in selected_relations
                ),
                key=_relation_key,
            )
        )
        groups.append(
            (
                target,
                group_entities,
                group_relations,
            )
        )
    return tuple(groups), tuple(sorted(privacy_omissions))


def _payload(
    snapshot: Snapshot,
    *,
    route: RouteSpec,
    purpose: str,
    focus_entity_ids: tuple[str, ...],
    budget_units: int,
    entities: Mapping[tuple[str, int], EntityVersion],
    relations: Mapping[tuple[str, int], RelationVersion],
    decisions: tuple[Decision, ...],
    omissions: tuple[str, ...],
    clearance: PrivacyLabel,
    grants: frozenset[str],
) -> dict[str, Any]:
    selected_ids = frozenset(entity.entity_id for entity in entities.values())
    relevant_decisions = tuple(
        decision
        for decision in decisions
        if _decision_is_relevant(decision, selected_ids, snapshot.project_id)
    )
    status_source_decisions = _status_source_decisions(snapshot, selected_ids)
    selected_object_ids = frozenset(
        {
            *selected_ids,
            *(relation.relation_id for relation in relations.values()),
            *(
                reference.artifact_id
                for entity in entities.values()
                for reference in entity.artifact_refs
            ),
            *(decision.decision_id for decision in relevant_decisions),
            *(decision.decision_id for decision in status_source_decisions),
        }
    )
    blockers = tuple(
        sorted(
            (
                blocker
                for blocker in snapshot.blockers
                if _blocker_is_relevant(
                    blocker, selected_object_ids, route.route_id
                )
            ),
            key=lambda blocker: blocker.blocker_id,
        )
    )
    for decision in relevant_decisions:
        if not _decision_accessible(
            decision, clearance=clearance, grants=grants, purpose=purpose
        ):
            raise ContextAccessError(
                "selected context would disclose authority Decision "
                f"{decision.decision_id}@{decision.version}"
            )
        if not _decision_references_accessible(
            snapshot,
            decision,
            clearance=clearance,
            grants=grants,
            purpose=purpose,
        ):
            raise ContextAccessError(
                "selected authority Decision has a protected current reference "
                f"{decision.decision_id}@{decision.version}"
            )
    for decision in status_source_decisions:
        if not _decision_accessible(
            decision, clearance=clearance, grants=grants, purpose=purpose
        ):
            raise ContextAccessError(
                "selected context would disclose derived-status Decision "
                f"{decision.decision_id}@{decision.version}"
            )
        if not _decision_references_accessible(
            snapshot,
            decision,
            clearance=clearance,
            grants=grants,
            purpose=purpose,
        ):
            raise ContextAccessError(
                "selected status Decision has a protected current reference "
                f"{decision.decision_id}@{decision.version}"
            )
    for blocker in blockers:
        if not _blocker_accessible(
            blocker, clearance=clearance, grants=grants, purpose=purpose
        ):
            raise ContextAccessError(
                f"selected context would disclose blocker {blocker.blocker_id}"
            )
    derived_status = {
        entity_id: snapshot.derived_status[entity_id].model_dump(mode="json")
        for entity_id in sorted(selected_ids)
        if entity_id in snapshot.derived_status
    }
    return {
        "context_schema": "econ-theorist/compiled-context/v1",
        "source_head": snapshot.head,
        "project_id": snapshot.project_id,
        "route": {
            "route_id": route.route_id,
            "route_version": route.route_version,
            "purpose": purpose,
            "authority_ceiling": route.authority_ceiling,
            "route_registry_hash": ROUTE_REGISTRY_HASH,
            "instruction_bundle_id": route.instruction_bundle_id,
            "instruction_bundle_hash": route.instruction_bundle_hash,
            "allowed_operations": route.allowed_operations,
            "instructions": _route_instructions(route),
        },
        "budget": {
            "estimator": TOKENIZER_ID,
            "units": budget_units,
            "provider_token_count": False,
        },
        "focus_entity_ids": focus_entity_ids,
        "kernel": {
            "kernel_version": KERNEL_VERSION,
            "kernel_hash": KERNEL_HASH,
            "content": dict(theory_kernel()),
        },
        "entities": tuple(
            entity.model_dump(mode="json")
            for entity in sorted(entities.values(), key=_entity_key)
        ),
        "relations": tuple(
            relation.model_dump(mode="json")
            for relation in sorted(relations.values(), key=_relation_key)
        ),
        "effective_decisions": tuple(
            decision.model_dump(mode="json")
            for decision in sorted(relevant_decisions, key=_decision_key)
        ),
        "status_source_decisions": tuple(
            decision.model_dump(mode="json")
            for decision in sorted(status_source_decisions, key=_decision_key)
        ),
        "derived_status": derived_status,
        "blockers": tuple(blocker.model_dump(mode="json") for blocker in blockers),
        "omissions": omissions,
    }


def compile_context(
    snapshot: Snapshot,
    *,
    route: RouteSpec,
    actor: Actor,
    purpose: str,
    compartments: Iterable[str],
    privacy_clearance: PrivacyLabel,
    focus_entity_ids: Iterable[str] = (),
    budget_units: int,
) -> CompiledContext:
    """Compile a deterministic exact-version context without touching disk."""

    del actor  # actor is recorded by the manifest; it does not alter scientific bytes.
    if isinstance(budget_units, bool) or not isinstance(budget_units, int):
        raise ContextBudgetError("budget_units must be an integer")
    if budget_units < 1:
        raise ContextBudgetError("budget_units must be positive")
    if isinstance(compartments, str) or isinstance(focus_entity_ids, str):
        raise ContextCompilationError(
            "compartments and focus_entity_ids must be iterables, not strings"
        )
    grants_tuple = tuple(compartments)
    focus_tuple = tuple(focus_entity_ids)
    if len(set(grants_tuple)) != len(grants_tuple):
        raise ContextCompilationError("compartment grants must be unique")
    if len(set(focus_tuple)) != len(focus_tuple):
        raise ContextCompilationError("focus entity IDs must be unique")
    grants = frozenset(grants_tuple)
    focus = tuple(sorted(focus_tuple))

    required_entities, required_relations, decisions = _required_slice(
        snapshot,
        route=route,
        focus_entity_ids=focus,
        clearance=privacy_clearance,
        grants=grants,
        purpose=purpose,
    )
    neighbors, privacy_omissions = _optional_neighbor_groups(
        snapshot,
        route=route,
        focus_entity_ids=focus,
        selected=required_entities,
        selected_relations=required_relations,
        clearance=privacy_clearance,
        grants=grants,
        purpose=purpose,
    )

    chosen_payload: dict[str, Any] | None = None
    chosen_entities: dict[tuple[str, int], EntityVersion] | None = None
    chosen_omissions: tuple[str, ...] | None = None
    chosen_encoded: bytes | None = None

    # Neighbor priority is deterministic.  Search the longest admissible prefix;
    # every excluded neighbor is named explicitly as a budget omission.
    for count in range(len(neighbors), -1, -1):
        entities = dict(required_entities)
        relations = dict(required_relations)
        for _, neighbor_entities, neighbor_relations in neighbors[:count]:
            for entity in neighbor_entities:
                entities[_entity_key(entity)] = entity
            for relation in neighbor_relations:
                relations[_relation_key(relation)] = relation
        budget_omissions = tuple(
            f"budget:neighbor:{entity.entity_id}@{entity.version}"
            for entity, _, _ in neighbors[count:]
        )
        omissions = tuple(sorted((*privacy_omissions, *budget_omissions)))
        payload = _payload(
            snapshot,
            route=route,
            purpose=purpose,
            focus_entity_ids=focus,
            budget_units=budget_units,
            entities=entities,
            relations=relations,
            decisions=decisions,
            omissions=omissions,
            clearance=privacy_clearance,
            grants=grants,
        )
        encoded = canonical_json_bytes(payload)
        if units_for_bytes(encoded) <= budget_units:
            chosen_payload = payload
            chosen_entities = entities
            chosen_omissions = omissions
            chosen_encoded = encoded
            break

    if chosen_payload is None or chosen_entities is None or chosen_encoded is None:
        # This includes the explicit omission ledger: required context never
        # starts a run by silently dropping or truncating that record.
        required_payload = _payload(
            snapshot,
            route=route,
            purpose=purpose,
            focus_entity_ids=focus,
            budget_units=budget_units,
            entities=required_entities,
            relations=required_relations,
            decisions=decisions,
            omissions=tuple(
                sorted(
                    (
                        *privacy_omissions,
                        *(
                            f"budget:neighbor:{entity.entity_id}@{entity.version}"
                            for entity, _, _ in neighbors
                        ),
                    )
                )
            ),
            clearance=privacy_clearance,
            grants=grants,
        )
        required_units = units_for_bytes(canonical_json_bytes(required_payload))
        raise ContextBudgetError(
            f"required exact context needs {required_units} {TOKENIZER_ID} units; "
            f"budget is {budget_units}"
        )

    used_units = units_for_bytes(chosen_encoded)
    selected_refs = tuple(
        EntityVersionRef(entity_id=entity.entity_id, version=entity.version)
        for entity in sorted(chosen_entities.values(), key=_entity_key)
    )
    return CompiledContext(
        payload=chosen_payload,
        encoded=chosen_encoded,
        context_hash=sha256_digest(chosen_encoded),
        selected_entity_refs=selected_refs,
        omissions=chosen_omissions or (),
        used_units=used_units,
    )


def make_context_manifest(
    compiled: CompiledContext,
    *,
    context_manifest_id: str,
    snapshot: Snapshot,
    route: RouteSpec,
    actor: Actor,
    purpose: str,
    compartments: Iterable[str],
    privacy_clearance: PrivacyLabel,
    focus_entity_ids: Iterable[str],
    budget_units: int,
    created_at: str,
) -> ContextManifest:
    """Bind compiled bytes to one immutable operational manifest."""

    return ContextManifest(
        context_manifest_id=context_manifest_id,
        project_id=snapshot.project_id,
        source_head=snapshot.head,
        route_id=route.route_id,
        route_version=route.route_version,
        route_registry_hash=ROUTE_REGISTRY_HASH,
        decision_registry_version=DECISION_REGISTRY_VERSION,
        selector_version=SELECTOR_VERSION,
        kernel_version=KERNEL_VERSION,
        kernel_hash=KERNEL_HASH,
        validator_version=VALIDATOR_VERSION,
        instruction_bundle_id=route.instruction_bundle_id,
        instruction_bundle_hash=route.instruction_bundle_hash,
        isolation_policy=ISOLATION_POLICY,
        write_allowlist=route.allowed_operations,
        purpose=purpose,
        actor=actor,
        focus_entity_ids=tuple(sorted(focus_entity_ids)),
        selected_entity_refs=compiled.selected_entity_refs,
        compartments=tuple(sorted(compartments)),
        privacy_clearance=privacy_clearance,
        tokenizer_id=TOKENIZER_ID,
        budget_units=budget_units,
        used_units=compiled.used_units,
        omissions=compiled.omissions,
        context_hash=compiled.context_hash,
        created_at=created_at,
    )


__all__ = [
    "CompiledContext",
    "ContextAccessError",
    "ContextBudgetError",
    "ContextCompilationError",
    "TOKENIZER_ID",
    "compile_context",
    "lexical_units",
    "make_context_manifest",
    "units_for_bytes",
]
