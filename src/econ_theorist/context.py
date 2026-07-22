"""Deterministic, bounded route-context compilation.

``etai_lexical_v1`` is a provider-neutral budget estimator.  Its units are not
OpenAI, Anthropic, or any other model provider's tokens.  An adapter must
recompile a context against the provider tokenizer it actually uses.
"""

from __future__ import annotations

import base64
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from .codec import canonical_json_bytes, sha256_digest
from .errors import PolicyError, RuntimeStoreError
from .models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    ContextManifest,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    PrivacyLabel,
    RelationVersion,
    RiskOrBlocker,
    RouteSpecLike,
    RouteSpecV2,
    RouteSpecV3,
    RouteSpecV4,
    Snapshot,
)
from .policy import (
    ISOLATION_POLICY,
    KERNEL_HASH,
    KERNEL_VERSION,
    SELECTOR_VERSION_DECOMPOSITION_REFRESH,
    SELECTOR_VERSION_DECOMPOSITION_REFRESH_V1,
    VALIDATOR_VERSION,
    V3_NATIVE_ROUTE_IDS,
    V4_NATIVE_ROUTE_IDS,
    decision_registry_version_for_route,
    instruction_bundle_bytes,
    registry_hash_for_route,
    selector_version_is_supported,
    selector_version_for_route,
    theory_kernel,
)
from .route_registry import clearance_allows

if TYPE_CHECKING:
    from .runtime.layout import StoreLayout


TOKENIZER_ID = "etai_lexical_v1"

_EVALUATION_ROUTE_PURPOSES = {
    "prepare.blind_case": "confirmatory_case_preparation",
    "evaluate.blind_argument_package": "confirmatory_evaluation",
}
_HOLDOUT_PURPOSES = frozenset(_EVALUATION_ROUTE_PURPOSES.values())
_EVALUATION_FOCUS_ENTITY_TYPES = frozenset(
    {"BlindCaseManifest", "TransformedVariantManifest"}
)
_PHASE3_NATIVE_ROUTE_IDS = V3_NATIVE_ROUTE_IDS
_PHASE4_NATIVE_ROUTE_IDS = V4_NATIVE_ROUTE_IDS


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


def _route_instructions(route: RouteSpecLike) -> tuple[str, ...]:
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
        and purpose not in _HOLDOUT_PURPOSES
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
        and purpose not in _HOLDOUT_PURPOSES
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
        and purpose not in _HOLDOUT_PURPOSES
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
        and purpose not in _HOLDOUT_PURPOSES
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
    if "confirmatory_holdout" in compartments and purpose not in _HOLDOUT_PURPOSES:
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


def _decomposition_preservation_entities(
    all_entities: Mapping[tuple[str, int], EntityVersion],
    current_entities: Mapping[tuple[str, int], EntityVersion],
    required_entities: Mapping[tuple[str, int], EntityVersion],
) -> tuple[EntityVersion, ...]:
    """Expose one exact prior decomposition package for a bounded refresh.

    The route focus and evidence contract remain the current question and
    benchmark.  This extra read-only context is selected only by exact typed
    lineage IDs, so a refresh can preserve an existing PrimitiveGraph instead
    of reconstructing unexposed scientific choices from memory.
    """

    from .theory import GateDossier, PrimitiveGraph, parse_theory_entity

    questions = tuple(
        entity
        for entity in required_entities.values()
        if entity.entity_type == "ResearchQuestion"
    )
    benchmarks = tuple(
        entity
        for entity in required_entities.values()
        if entity.entity_type == "BenchmarkSet"
    )
    if len(questions) != 1 or not benchmarks:
        return ()
    question_id = questions[0].entity_id
    benchmark_ids = {entity.entity_id for entity in benchmarks}

    matching_graphs: list[tuple[EntityVersion, PrimitiveGraph]] = []
    for entity in current_entities.values():
        if entity.entity_type != "PrimitiveGraph":
            continue
        try:
            payload = parse_theory_entity(entity)
        except (TypeError, ValueError):
            continue
        if (
            isinstance(payload, PrimitiveGraph)
            and payload.question_ref.entity_id == question_id
            and payload.benchmark_set_ref.entity_id in benchmark_ids
        ):
            matching_graphs.append((entity, payload))
    if not matching_graphs:
        return ()
    if len(matching_graphs) != 1:
        raise ContextCompilationError(
            "decomposition refresh has multiple current PrimitiveGraph lineages"
        )

    graph_entity, graph = matching_graphs[0]
    selected = [graph_entity]
    prior_graph_ref = graph_entity.supersedes
    if prior_graph_ref is None:
        return tuple(selected)
    prior_graph_entity = all_entities.get(
        (prior_graph_ref.entity_id, prior_graph_ref.version)
    )
    if prior_graph_entity is None:
        raise ContextCompilationError(
            "decomposition refresh graph supersedes a missing exact predecessor"
        )
    prior_graph = parse_theory_entity(prior_graph_entity)
    if not isinstance(prior_graph, PrimitiveGraph):
        raise ContextCompilationError(
            "decomposition refresh predecessor is not a PrimitiveGraph"
        )
    required_old_refs = {
        prior_graph_ref,
        prior_graph.question_ref,
        prior_graph.benchmark_set_ref,
    }
    matching_dossiers: list[EntityVersion] = []
    for entity in current_entities.values():
        if entity.entity_type != "GateDossier":
            continue
        try:
            payload = parse_theory_entity(entity)
        except (TypeError, ValueError):
            continue
        if (
            isinstance(payload, GateDossier)
            and payload.gate_kind == "G1_question_benchmark"
            and payload.research_question_ref == prior_graph.question_ref
            and set(payload.ordered_object_refs) == required_old_refs
        ):
            matching_dossiers.append(entity)
    if len(matching_dossiers) > 1:
        raise ContextCompilationError(
            "decomposition refresh has multiple exact prior G1 dossiers"
        )
    selected.extend(matching_dossiers)
    return tuple(selected)


def _required_slice(
    snapshot: Snapshot,
    *,
    route: RouteSpecLike,
    focus_entity_ids: tuple[str, ...],
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
    include_decomposition_preservation: bool = False,
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

    if (
        route.route_id == "decompose.primitives"
        and include_decomposition_preservation
    ):
        for entity in _decomposition_preservation_entities(
            all_entities, current_entities, required_entities
        ):
            required_entities[_entity_key(entity)] = entity

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
    route: RouteSpecLike,
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


def _evaluation_exact_entities(
    snapshot: Snapshot,
    *,
    focus_entity_ids: tuple[str, ...],
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
    require_manifest: bool,
) -> dict[tuple[str, int], EntityVersion]:
    """Select only exact current focus entities for a sealed evaluation run."""

    if not focus_entity_ids:
        raise ContextCompilationError(
            "evaluation contexts require at least one exact focus entity"
        )
    current = _current_entities(snapshot)
    by_id = {entity.entity_id: entity for entity in current.values()}
    selected: dict[tuple[str, int], EntityVersion] = {}
    for entity_id in focus_entity_ids:
        entity = by_id.get(entity_id)
        if entity is None:
            raise ContextCompilationError(
                f"evaluation focus entity is not current: {entity_id}"
            )
        if not _entity_accessible(
            entity, clearance=clearance, grants=grants, purpose=purpose
        ):
            raise ContextAccessError(
                f"evaluation focus entity is not readable: "
                f"{entity.entity_id}@{entity.version}"
            )
        selected[_entity_key(entity)] = entity
    if require_manifest and not any(
        entity.entity_type in _EVALUATION_FOCUS_ENTITY_TYPES
        for entity in selected.values()
    ):
        raise ContextCompilationError(
            "evaluation contexts require a focused BlindCaseManifest or "
            "TransformedVariantManifest"
        )
    return selected


def _walk_direct_evaluation_refs(value: object) -> Iterable[object]:
    """Yield exact artifact/Decision refs directly encoded in one payload."""

    if isinstance(value, (ArtifactDependencyRef, DecisionVersionRef)):
        yield value
        return
    if isinstance(value, EntityVersionRef):
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from _walk_direct_evaluation_refs(getattr(value, field_name))
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _walk_direct_evaluation_refs(nested)
        return
    if isinstance(value, (tuple, list)):
        for nested in value:
            yield from _walk_direct_evaluation_refs(nested)


def _evaluation_context_inputs(
    snapshot: Snapshot,
    selected: Mapping[tuple[str, int], EntityVersion],
    *,
    route_id: str,
    layout: StoreLayout | None,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> tuple[tuple[dict[str, Any], ...], tuple[Decision, ...]]:
    """Resolve sealed manifest refs to exact registrations, bytes, and Decisions."""

    if layout is None:
        raise ContextCompilationError(
            "evaluation context compilation requires the canonical StoreLayout"
        )
    from .runtime.objects import ObjectStore
    from .theory import PreResultBrief, ValidatedArgumentPackage, parse_theory_entity

    artifact_refs: dict[tuple[str, int], ArtifactDependencyRef] = {}
    decision_refs: set[tuple[str, int]] = set()
    parsed_entities: list[tuple[EntityVersion, BaseModel]] = []
    for entity in selected.values():
        relevant_type = (
            entity.entity_type in _EVALUATION_FOCUS_ENTITY_TYPES
            or (
                route_id == "prepare.blind_case"
                and entity.entity_type == "PreResultBrief"
            )
            or (
                route_id == "evaluate.blind_argument_package"
                and entity.entity_type == "ValidatedArgumentPackage"
            )
        )
        if not relevant_type:
            continue
        try:
            payload = parse_theory_entity(entity)
        except (TypeError, ValueError) as exc:
            raise ContextCompilationError(
                f"evaluation focus is not a typed {entity.entity_type}: "
                f"{entity.entity_id}@{entity.version}"
            ) from exc
        parsed_entities.append((entity, payload))
        if entity.entity_type not in _EVALUATION_FOCUS_ENTITY_TYPES:
            continue
        references = (*entity.artifact_refs, *_walk_direct_evaluation_refs(payload))
        for reference in references:
            if isinstance(reference, ArtifactDependencyRef):
                key = (reference.artifact_id, reference.version)
                prior = artifact_refs.get(key)
                if prior is not None and prior.content_hash != reference.content_hash:
                    raise ContextCompilationError(
                        "evaluation manifest repeats an artifact version with "
                        "conflicting hashes"
                    )
                artifact_refs[key] = reference
            elif isinstance(reference, DecisionVersionRef):
                decision_refs.add((reference.decision_id, reference.version))

    if route_id == "prepare.blind_case":
        briefs = [
            (entity, payload)
            for entity, payload in parsed_entities
            if isinstance(payload, PreResultBrief)
        ]
        attempts = {payload.attempt_id for _, payload in briefs}
        if len(briefs) != 2 or len(attempts) != 1:
            raise ContextCompilationError(
                "blind case preparation context requires two focused "
                "PreResultBrief entities with one shared attempt"
            )
        attempt_id = next(iter(attempts))
        brief_entities = {entity.entity_id: entity for entity, _ in briefs}
        effective_refs = {
            (reference.decision_id, reference.version)
            for reference in snapshot.effective_decisions.values()
        }
        freezes = [
            decision
            for decision in snapshot.decisions
            if (decision.decision_id, decision.version) in effective_refs
            and decision.decision_kind == "theory_mode"
            and decision.status == "confirmed"
            and decision.decider.kind == "human"
            and decision.selected_option == "freeze"
            and decision.subject_ref in brief_entities
            and decision.scope_ref == attempt_id
            and decision.decided_at
            > brief_entities[decision.subject_ref].created_at
        ]
        if len(freezes) != 1:
            raise ContextCompilationError(
                "blind case preparation context requires one effective human "
                "implementation freeze for the transformed brief"
            )
        decision_refs.add((freezes[0].decision_id, freezes[0].version))

    if route_id == "evaluate.blind_argument_package":
        candidates = [
            (entity, payload)
            for entity, payload in parsed_entities
            if isinstance(payload, ValidatedArgumentPackage)
            and payload.release_mode == "evaluation_only"
            and payload.evaluation_attempt_id is not None
        ]
        if len(candidates) != 1:
            raise ContextCompilationError(
                "evaluation context requires one focused evaluation-only "
                "ValidatedArgumentPackage with an attempt ID"
            )
        candidate_entity, candidate = candidates[0]
        lock_id = f"candidate.lock.{candidate.evaluation_attempt_id}"
        lock_version = snapshot.current_artifacts.get(lock_id)
        locks = [
            item
            for item in snapshot.artifacts
            if item.artifact_id == lock_id and item.version == lock_version
        ]
        expected_hash = sha256_digest(canonical_json_bytes(candidate_entity))
        if (
            lock_version != 1
            or len(locks) != 1
            or locks[0].supersedes is not None
            or locks[0].project_id != snapshot.project_id
            or locks[0].media_type
            != "application/vnd.econ-theorist.candidate-lock+json"
            or locks[0].content_hash != expected_hash
        ):
            raise ContextCompilationError(
                "evaluation context requires the unique current v1 candidate "
                "lock over the exact focused candidate bytes"
            )
        lock = locks[0]
        artifact_refs[(lock.artifact_id, lock.version)] = ArtifactDependencyRef(
            artifact_id=lock.artifact_id,
            version=lock.version,
            content_hash=lock.content_hash,
        )

    evaluation_attempt_ids = {
        attempt_id
        for _, payload in parsed_entities
        for attempt_id in (
            getattr(payload, "attempt_id", None),
            getattr(payload, "evaluation_attempt_id", None),
        )
        if isinstance(attempt_id, str)
    }

    artifact_index = {
        (item.artifact_id, item.version): item for item in snapshot.artifacts
    }
    store = ObjectStore(layout)
    artifact_records: list[dict[str, Any]] = []
    for key in sorted(artifact_refs):
        reference = artifact_refs[key]
        registration = artifact_index.get(key)
        if (
            registration is None
            or registration.content_hash != reference.content_hash
        ):
            raise ContextCompilationError(
                "evaluation manifest contains an unresolved or hash-mismatched "
                f"artifact ref {reference.artifact_id}@{reference.version}"
            )
        if not _privacy_record_accessible(
            registration,
            clearance=clearance,
            grants=grants,
            purpose=purpose,
        ):
            raise ContextAccessError(
                "evaluation artifact is not readable: "
                f"{registration.artifact_id}@{registration.version}"
            )
        try:
            data = store.read_bytes(
                "artifacts", registration.content_hash, verify=True
            )
        except RuntimeStoreError as exc:
            raise ContextCompilationError(
                "evaluation artifact bytes are unavailable or corrupt: "
                f"{registration.artifact_id}@{registration.version}"
            ) from exc
        if len(data) != registration.byte_size:
            raise ContextCompilationError(
                "evaluation artifact byte_size does not match registered bytes: "
                f"{registration.artifact_id}@{registration.version}"
            )
        artifact_records.append(
            {
                "registration": registration.model_dump(mode="json"),
                "content_encoding": "base64",
                "content_base64": base64.b64encode(data).decode("ascii"),
            }
        )

    decision_index = {
        (item.decision_id, item.version): item for item in snapshot.decisions
    }
    decisions: list[Decision] = []
    for key in sorted(decision_refs):
        decision = decision_index.get(key)
        if decision is None:
            raise ContextCompilationError(
                "evaluation manifest contains an unresolved exact Decision ref "
                f"{key[0]}@{key[1]}"
            )
        reference_check = decision
        if (
            decision.decision_kind == "theory_mode"
            and decision.status == "confirmed"
            and decision.decider.kind == "human"
            and decision.selected_option == "freeze"
            and decision.scope_ref in evaluation_attempt_ids
        ):
            # The sealed evaluation protocol uses ``scope_ref`` as its typed
            # attempt identifier, not as a mutable canonical-object pointer.
            # All other Decision references still receive the ordinary
            # current-object privacy walk.
            reference_check = decision.model_copy(update={"scope_ref": None})
        if not _decision_accessible(
            decision, clearance=clearance, grants=grants, purpose=purpose
        ) or not _decision_references_accessible(
            snapshot,
            reference_check,
            clearance=clearance,
            grants=grants,
            purpose=purpose,
        ):
            raise ContextAccessError(
                f"evaluation Decision is not readable: {key[0]}@{key[1]}"
            )
        decisions.append(decision)
    return tuple(artifact_records), tuple(decisions)


_PHASE3_VISIBLE_ENTITY_TYPES: Mapping[str, frozenset[str]] = {
    "verify.independent_rederivation": frozenset(
        {"AssumptionMap", "ClaimGraph", "FormalModel", "ProofObligation"}
    ),
    "audit.argument_assurance": frozenset(
        {
            "AssumptionMap",
            "ClaimGraph",
            "FormalModel",
            "ProofObligation",
            "ReDerivationRecord",
            "ValidatedArgumentPackage",
            "VerificationBundle",
            "VerificationRecord",
        }
    ),
    "design.reader_path": frozenset(
        {
            "AssumptionMap",
            "AssuranceBundle",
            "BenchmarkSet",
            "ClaimGraph",
            "ClosestTheoryMap",
            "EconomicArgumentGraph",
            "ExampleSuite",
            "FormalModel",
            "ResearchQuestion",
            "ResultPortfolio",
            "ValidatedArgumentPackage",
            "VerificationBundle",
        }
    ),
    "compose.manuscript_unit": frozenset(
        {
            "AssumptionMap",
            "BenchmarkSet",
            "ClaimGraph",
            "ClosestTheoryMap",
            "EconomicArgumentGraph",
            "ExampleSuite",
            "FormalModel",
            "ManuscriptUnit",
            "PaperIR",
            "ReaderPath",
            "ResolvedProfileManifest",
            "ResultContractSet",
            "ResultPortfolio",
            "RevisionBrief",
        }
    ),
    "review.manuscript_unit": frozenset(
        {
            "AssumptionMap",
            "ClaimGraph",
            "CriticAssignment",
            "EconomicArgumentGraph",
            "ExampleSuite",
            "ManuscriptUnit",
            "PaperIR",
            "ResultContractSet",
        }
    ),
    "prepare.reader_probe": frozenset(
        {"CriticAssignment", "ManuscriptUnit", "ReaderPath"}
    ),
    "answer.reader_probe": frozenset(
        {"CriticAssignment", "ManuscriptUnit", "ReaderProbeSet"}
    ),
    "adjudicate.reader_probe": frozenset(
        {
            "CriticAssignment",
            "ManuscriptUnit",
            "ReaderProbeSet",
            "ReaderResponse",
        }
    ),
    "close.manuscript_review": frozenset(
        {
            "AssuranceBundle",
            "ManuscriptUnit",
            "PaperIR",
            "ReviewFinding",
            "ReviewRecord",
        }
    ),
    "record.human_effort": frozenset(
        {"HumanEffortRecord", "ManuscriptUnit"}
    ),
}

_PHASE3_PACKET_KINDS: Mapping[str, str] = {
    "verify.independent_rederivation": "independent_rederivation",
    "audit.argument_assurance": "assurance_audit",
    "design.reader_path": "authoring_planner",
    "compose.manuscript_unit": "canonical_writer",
    "review.manuscript_unit": "assigned_critic",
    "prepare.reader_probe": "probe_designer",
    "answer.reader_probe": "cold_reader",
    "adjudicate.reader_probe": "reader_adjudicator",
    "close.manuscript_review": "deterministic_review_closure",
    "record.human_effort": "human_effort_reporter",
}

_PHASE4_VISIBLE_ENTITY_TYPES: Mapping[str, frozenset[str]] = {
    "map.obligation_predicate": frozenset(
        {
            "AssumptionMap",
            "AssuranceBundle",
            "ClaimGraph",
            "FormalModel",
            "ProofObligation",
        }
    ),
    "audit.obligation_predicate": frozenset(
        {
            "AssumptionMap",
            "AssuranceBundle",
            "ClaimGraph",
            "FormalModel",
            "ObligationPredicateContract",
            "ProofObligation",
        }
    ),
    "resolve.profile_stack": frozenset(
        {
            "AssuranceBundle",
            "PaperIR",
            "PredicateMappingAudit",
            "ReaderPath",
            "ResolvedProfileManifest",
            "ValidatedArgumentPackage",
        }
    ),
    "diagnose.reader_problem": frozenset(
        {
            "ManuscriptUnit",
            "PaperIR",
            "ReaderPath",
            "ResolvedProfileStack",
            "ResultContractSet",
            "ReviewClosure",
            "ReviewFinding",
            "ReviewRecord",
            "RevisionBrief",
        }
    ),
    "retrieve.craft_moves": frozenset(
        {
            "PaperIR",
            "ReaderPath",
            "ReaderProblemDiagnosis",
            "ResolvedProfileStack",
            "ResultContractSet",
        }
    ),
    "compose.profiled_manuscript_unit": frozenset(
        {
            "AssuranceBundle",
            "CraftSelectionManifest",
            "ManuscriptUnit",
            "PaperIR",
            "ReaderPath",
            "ReaderProblemDiagnosis",
            "ResolvedProfileManifest",
            "ResolvedProfileStack",
            "ResultContractSet",
            "ReviewClosure",
            "RevisionBrief",
            "ValidatedArgumentPackage",
        }
    ),
    "review.craft_realization": frozenset(
        {
            "CraftSelectionManifest",
            "ManuscriptUnit",
            "PaperIR",
            "ReaderPath",
            "ReaderProblemDiagnosis",
            "ResolvedProfileStack",
            "ResultContractSet",
            "ReviewClosure",
            "ReviewRecord",
        }
    ),
    "close.profile_craft_review": frozenset(
        {
            "CraftRealizationAssessment",
            "CraftSelectionManifest",
            "ManuscriptUnit",
            "PredicateMappingAudit",
            "ProfileCraftClosure",
            "ReaderProblemDiagnosis",
            "ResolvedProfileStack",
            "ReviewClosure",
        }
    ),
}

_PHASE4_PACKET_KINDS: Mapping[str, str] = {
    "map.obligation_predicate": "obligation_predicate_mapper",
    "audit.obligation_predicate": "obligation_predicate_auditor",
    "resolve.profile_stack": "profile_resolver",
    "diagnose.reader_problem": "reader_problem_diagnostician",
    "retrieve.craft_moves": "functional_craft_retriever",
    "compose.profiled_manuscript_unit": "profiled_canonical_writer",
    "review.craft_realization": "craft_realization_critic",
    "close.profile_craft_review": "profile_craft_closure",
}

_ROLE_CONSTRAINTS: Mapping[str, tuple[str, ...]] = {
    "independent_rederivation": (
        "Derive from the formal statement, model, assumptions, and obligations only.",
        "Do not infer correctness from an originating proof or proposed explanation.",
    ),
    "assurance_audit": (
        "Compare the sealed independent derivation with exact proof evidence.",
        "A finite search may falsify but cannot prove a universal statement.",
    ),
    "authoring_planner": (
        "Plan reader updates from the accepted economic argument and exact result scope.",
        "Do not create a new scientific claim or journal-specific template.",
    ),
    "canonical_writer": (
        "Use one coherent economic voice and stable terminology.",
        "Preserve formal scope, assumptions, boundaries, and evidentiary roles.",
        "Explain the benchmark, operative margin, diagnostic example, and proof roadmap.",
    ),
    "assigned_critic": (
        "Diagnose the frozen manuscript unit; do not rewrite it.",
        "Treat proposed explanations as claims to test, not facts to inherit.",
    ),
    "probe_designer": (
        "Create post-freeze retell, scope, boundary, and near-transfer probes.",
        "Keep the concrete probes and answer key unavailable to the writer.",
    ),
    "cold_reader": (
        "Answer from the manuscript and declared reader background only.",
        "Do not assume access to an answer key, author rationale, or other reviews.",
    ),
    "reader_adjudicator": (
        "Judge the exact response against the sealed key without changing either.",
    ),
    "deterministic_review_closure": (
        "Apply every noncompensatory readiness check to exact current evidence.",
    ),
    "human_effort_reporter": (
        "Record active human time and semantic edit categories without estimation.",
    ),
    "obligation_predicate_mapper": (
        "Map every quantified domain, assumption, conclusion, and boundary clause explicitly.",
        "A runnable predicate does not certify semantic equivalence or theorem truth.",
    ),
    "obligation_predicate_auditor": (
        "Audit independently from the mapper and replay every registered negative mutant.",
        "Reject vacuous, constant-true, narrowed-domain, or weakened encodings.",
    ),
    "profile_resolver": (
        "Apply the universal floor and exact human target decisions before any soft overlay.",
        "Reject and record target directives that alter science, discovery, scope, or voice.",
    ),
    "reader_problem_diagnostician": (
        "Identify one exact failed reader update and its available semantic inputs.",
        "Route unresolved science upstream instead of treating it as an exposition defect.",
    ),
    "functional_craft_retriever": (
        "Select by reader function and semantic inputs, with matched and contrast evidence.",
        "Exclude empirical templates, raw anchor prose, phrase banks, and holdouts.",
    ),
    "profiled_canonical_writer": (
        "Use the project economics and one canonical voice, never an anchor's wording.",
        "Preserve exact scope, assumptions, boundaries, and evidentiary roles.",
        "Realize only the selected functional moves for the diagnosed reader update.",
    ),
    "craft_realization_critic": (
        "Test whether the selected reader function was realized without rewriting the unit.",
        "Do not reward visible templates, journal tone, abstraction, or theorem density.",
    ),
    "profile_craft_closure": (
        "Apply every PROFILE-CRAFT-READY check noncompensatorily to exact current evidence.",
        "Do not infer publication quality, legal compliance, or causal improvement.",
    ),
}


def _phase3_payload(entity: EntityVersion) -> BaseModel:
    from .authoring import is_packed_authoring_entity, parse_authoring_entity
    from .theory import is_packed_theory_entity, parse_theory_entity

    if is_packed_authoring_entity(entity):
        return parse_authoring_entity(entity)
    if is_packed_theory_entity(entity):
        return parse_theory_entity(entity)
    raise ContextCompilationError(
        f"Phase 3 focus is not a packed typed entity: {entity.entity_id}@{entity.version}"
    )


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
    if isinstance(value, (tuple, list)):
        for nested in value:
            yield from _walk_artifact_refs(nested)


def _strip_role_internal(value: object) -> object:
    """Remove governance/provenance keys from the provider-facing role packet."""

    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, nested in value.items():
            lowered = key.lower()
            if (
                lowered in {
                    "schema_version",
                    "source_state_revision",
                    "upstream_projection_hash",
                    "context_manifest_hash",
                    "compiled_context_hash",
                    "route_run_id",
                    "g5_decision_ref",
                    "g4_decision_ref",
                    "manuscript_version_promotion_ref",
                    "answer_key_artifact_ref",
                }
                or lowered.endswith("_ref")
                or lowered.endswith("_refs")
                or lowered.endswith("_id")
                or lowered.endswith("_ids")
                or lowered.endswith("_hash")
            ):
                continue
            result[key] = _strip_role_internal(nested)
        return result
    if isinstance(value, (tuple, list)):
        return tuple(_strip_role_internal(item) for item in value)
    return value


def _phase3_artifact_refs(
    route_id: str, parsed: tuple[tuple[EntityVersion, BaseModel], ...]
) -> tuple[ArtifactDependencyRef, ...]:
    from .authoring import (
        ManuscriptUnit,
        ReaderProbeSet,
        ReaderResponse,
        RevisionBrief,
    )

    selected: dict[tuple[str, int], ArtifactDependencyRef] = {}

    def add(reference: ArtifactDependencyRef) -> None:
        key = (reference.artifact_id, reference.version)
        prior = selected.get(key)
        if prior is not None and prior.content_hash != reference.content_hash:
            raise ContextCompilationError(
                "Phase 3 context repeats an artifact version with conflicting hashes"
            )
        selected[key] = reference

    if route_id == "audit.argument_assurance":
        for _, payload in parsed:
            for reference in _walk_artifact_refs(payload):
                add(reference)
    else:
        for _, payload in parsed:
            if isinstance(payload, ManuscriptUnit) and route_id in {
                "compose.manuscript_unit",
                "review.manuscript_unit",
                "prepare.reader_probe",
                "answer.reader_probe",
                "adjudicate.reader_probe",
                "record.human_effort",
            }:
                add(payload.manuscript_artifact_ref)
            if isinstance(payload, RevisionBrief) and route_id == "compose.manuscript_unit":
                add(payload.brief_artifact_ref)
            if isinstance(payload, ReaderProbeSet):
                if route_id in {"answer.reader_probe", "adjudicate.reader_probe"}:
                    add(payload.probe_artifact_ref)
                if route_id == "adjudicate.reader_probe":
                    add(payload.answer_key_artifact_ref)
            if isinstance(payload, ReaderResponse) and route_id == "adjudicate.reader_probe":
                add(payload.response_artifact_ref)
    return tuple(selected[key] for key in sorted(selected))


def _phase3_context_inputs(
    snapshot: Snapshot,
    *,
    route: RouteSpecV3,
    actor: Actor,
    focus_entity_ids: tuple[str, ...],
    layout: StoreLayout | None,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> tuple[
    dict[tuple[str, int], EntityVersion],
    tuple[dict[str, Any], ...],
    dict[str, Any],
]:
    if layout is None:
        raise ContextCompilationError(
            "Phase 3 role context compilation requires the canonical StoreLayout"
        )
    visible_types = _PHASE3_VISIBLE_ENTITY_TYPES.get(route.route_id)
    packet_kind = _PHASE3_PACKET_KINDS.get(route.route_id)
    if visible_types is None or packet_kind is None:
        raise ContextCompilationError(f"unknown Phase 3 role route: {route.route_id}")
    current = _current_entities(snapshot)
    by_id = {entity.entity_id: entity for entity in current.values()}
    entities: dict[tuple[str, int], EntityVersion] = {}
    parsed: list[tuple[EntityVersion, BaseModel]] = []
    for entity_id in focus_entity_ids:
        entity = by_id.get(entity_id)
        if entity is None:
            raise ContextCompilationError(
                f"Phase 3 focus entity is not current: {entity_id}"
            )
        if entity.entity_type not in visible_types:
            # Some exact inputs, notably the G5 package for blind re-derivation,
            # are checked at entry but intentionally absent from role context.
            continue
        if not _entity_accessible(
            entity, clearance=clearance, grants=grants, purpose=purpose
        ):
            raise ContextAccessError(
                f"Phase 3 focus entity is not readable: {entity.entity_id}@{entity.version}"
            )
        payload = _phase3_payload(entity)
        entities[_entity_key(entity)] = entity
        parsed.append((entity, payload))
    if not parsed:
        raise ContextCompilationError("Phase 3 role context selected no visible exact input")

    artifact_refs = _phase3_artifact_refs(route.route_id, tuple(parsed))
    artifact_index = {
        (item.artifact_id, item.version): item for item in snapshot.artifacts
    }
    from .runtime.objects import ObjectStore

    store = ObjectStore(layout)
    full_artifacts: list[dict[str, Any]] = []
    role_artifacts: list[dict[str, Any]] = []
    for reference in artifact_refs:
        registration = artifact_index.get((reference.artifact_id, reference.version))
        if registration is None or registration.content_hash != reference.content_hash:
            raise ContextCompilationError(
                f"Phase 3 artifact is unresolved or hash-mismatched: "
                f"{reference.artifact_id}@{reference.version}"
            )
        if not _privacy_record_accessible(
            registration,
            clearance=clearance,
            grants=grants,
            purpose=purpose,
        ):
            raise ContextAccessError(
                f"Phase 3 artifact is not readable: "
                f"{registration.artifact_id}@{registration.version}"
            )
        data = store.read_bytes("artifacts", registration.content_hash, verify=True)
        if len(data) != registration.byte_size:
            raise ContextCompilationError("Phase 3 artifact byte_size mismatch")
        encoded = base64.b64encode(data).decode("ascii")
        full_artifacts.append(
            {
                "registration": registration.model_dump(mode="json"),
                "content_encoding": "base64",
                "content_base64": encoded,
            }
        )
        role_artifacts.append(
            {
                "logical_name": registration.logical_name,
                "media_type": registration.media_type,
                "content_encoding": "base64",
                "content_base64": encoded,
            }
        )

    semantic_inputs = tuple(
        {
            "kind": entity.entity_type,
            "content": _strip_role_internal(payload.model_dump(mode="json")),
        }
        for entity, payload in parsed
    )
    role_packet = {
        "packet_schema": "econ-theorist/role-packet/v1",
        "packet_kind": packet_kind,
        "actor_kind": actor.kind,
        "constraints": _ROLE_CONSTRAINTS[packet_kind],
        "semantic_inputs": semantic_inputs,
        "artifacts": tuple(role_artifacts),
    }
    return entities, tuple(full_artifacts), role_packet


def _phase4_payload(entity: EntityVersion) -> BaseModel:
    """Parse one exact Phase 4 input without widening older namespaces."""

    from .profile_craft import (
        is_packed_profile_craft_entity,
        parse_profile_craft_entity,
    )

    if is_packed_profile_craft_entity(entity):
        return parse_profile_craft_entity(entity)
    return _phase3_payload(entity)


def _phase4_role_content(
    payload: BaseModel,
    *,
    packet_kind: str,
    predicate_receipt: BaseModel | None = None,
) -> object:
    """Return the narrow provider-facing projection for a Phase 4 payload.

    Project manifests retain exact IDs and hashes, while a writer receives
    only active profile directives, the diagnosed reader update, and selected
    copyright-safe functional moves.  In particular, no source card, anchor
    locator, full corpus, or phrase material enters this projection.
    """

    from . import profile_craft as pc
    from .authoring import AssuranceBundle

    if isinstance(payload, AssuranceBundle) and predicate_receipt is not None:
        obligation_ref = getattr(predicate_receipt, "obligation_ref", None)
        return {
            "headline_claim_id": payload.headline_claim_id,
            "relevant_proof_audits": tuple(
                _strip_role_internal(item.model_dump(mode="json"))
                for item in payload.proof_audits
                if item.obligation_ref == obligation_ref
            ),
            "selected_tool_receipt": _strip_role_internal(
                predicate_receipt.model_dump(mode="json")
            ),
            "unresolved_issues": tuple(
                _strip_role_internal(item.model_dump(mode="json"))
                for item in payload.unresolved_issues
            ),
        }

    if isinstance(payload, pc.ResolvedProfileStack):
        if packet_kind == "profile_resolver":
            return _strip_role_internal(payload.model_dump(mode="json"))
        active = tuple(
            {
                "source_layer_kind": item.source_layer_kind,
                "statement": item.directive.statement,
                "strength": item.directive.strength,
                "effect_scope": item.directive.effect_scope,
                "directive_kind": item.directive.directive_kind,
                "acceptance_criterion": {
                    "criterion_id": item.directive.acceptance_criterion.criterion_id,
                    "required_assertion_roles": (
                        item.directive.acceptance_criterion.required_assertion_roles
                    ),
                    "required_review_signals": (
                        item.directive.acceptance_criterion.required_review_signals
                    ),
                },
                "non_applicability": item.directive.non_applicability,
            }
            for item in payload.directive_resolutions
            if item.outcome == "active"
        )
        rejected = tuple(
            {
                "source_layer_kind": item.source_layer_kind,
                "directive_kind": item.directive.directive_kind,
                "conflict_key": item.directive.conflict_key,
                "effect_scope": item.directive.effect_scope,
                "strength": item.directive.strength,
                "rejection_reason": item.rejection_reason,
            }
            for item in payload.directive_resolutions
            if item.outcome == "rejected"
        )
        return {
            "selected_layers": tuple(
                {
                    "layer_kind": item.layer_kind,
                    "selection_key": item.selection_key,
                    "source_status": item.source_status,
                }
                for item in payload.selected_layers
            ),
            "active_directives": active,
            "rejected_conflicts": rejected,
        }
    if isinstance(payload, pc.ReaderProblemDiagnosis):
        return {
            "affected_sections": payload.affected_section_ids,
            "affected_section_roles": payload.affected_section_roles,
            "reader_problem": payload.reader_problem_key,
            "diagnostic_categories": payload.diagnostic_categories,
            "causal_class": payload.causal_class,
            "required_updates": payload.required_resolution_ids,
            "resolution_requirements": tuple(
                {
                    "requirement_id": item.requirement_id,
                    "action": item.action,
                    "affected_assertion_ids": item.affected_assertion_ids,
                    "affected_section_ids": item.affected_section_ids,
                    "required_semantic_input_ids": (
                        item.required_semantic_input_ids
                    ),
                }
                for item in payload.resolution_requirements
            ),
            "observed_problem": payload.observed_problem,
            "required_semantic_inputs": payload.required_semantic_input_ids,
            "semantic_input_bindings": tuple(
                {
                    "input_id": item.input_id,
                    "source_kind": item.source_kind,
                    "availability": item.availability,
                    "explanation": item.explanation,
                }
                for item in payload.semantic_input_bindings
            ),
            "upstream_science_status": payload.upstream_science_status,
            "craft_eligible": payload.craft_eligible,
            "upstream_repair_route": payload.upstream_repair_route,
        }
    if isinstance(payload, pc.CraftSelectionManifest):
        selected_moves = []
        for candidate in payload.candidates:
            if not candidate.selected:
                continue
            move = candidate.move
            selected_moves.append(
                {
                    "functional_name": move.functional_name,
                    "reader_problem": move.reader_problem_key,
                    "function": move.function_key,
                    "trigger_conditions": move.trigger_conditions,
                    "required_semantic_inputs": move.required_semantic_inputs,
                    "supported_repair_actions": move.supported_repair_actions,
                    "intended_reader_update": move.intended_reader_update,
                    "typical_placements": move.typical_placements,
                    "eligible_section_roles": move.eligible_section_roles,
                    "compatible_causal_classes": move.compatible_causal_classes,
                    "valid_variants": move.valid_variants,
                    "failure_modes": move.failure_modes,
                    "non_applicability": move.non_applicability,
                    "covered_requirement_ids": candidate.covered_requirement_ids,
                }
            )
        return {
            "selection_strategy": payload.selection_strategy,
            "outcome": payload.outcome,
            "diagnosed_reader_problem": payload.diagnosed_reader_problem_key,
            "diagnosed_required_updates": payload.diagnosed_required_resolution_ids,
            "selected_functional_moves": tuple(selected_moves),
        }
    if isinstance(payload, pc.CraftRealizationAssessment):
        return {
            "primary_audience": payload.primary_audience,
            "required_directive_ids": payload.required_directive_ids,
            "directive_acceptance_checks": tuple(
                {
                    "directive_id": item.directive_id,
                    "criterion_id": item.criterion_id,
                    "required_assertion_roles": item.required_assertion_roles,
                    "realized_assertion_roles": item.realized_assertion_roles,
                    "required_review_signals": item.required_review_signals,
                    "observed_review_signals": item.observed_review_signals,
                    "outcome": item.outcome,
                    "explanation": item.explanation,
                }
                for item in payload.directive_acceptance_checks
            ),
            "required_resolution_ids": payload.required_resolution_ids,
            "resolution_requirement_checks": tuple(
                {
                    "requirement_id": item.requirement_id,
                    "repair_action": item.repair_action,
                    "affected_assertion_ids": item.affected_assertion_ids,
                    "affected_section_ids": item.affected_section_ids,
                    "required_semantic_input_ids": (
                        item.required_semantic_input_ids
                    ),
                    "realized_semantic_input_ids": (
                        item.realized_semantic_input_ids
                    ),
                    "outcome": item.outcome,
                    "explanation": item.explanation,
                }
                for item in payload.resolution_requirement_checks
            ),
            "target_reader_outcome": {
                "primary_audience": payload.target_reader_outcome.primary_audience,
                "benchmark_delta_reconstructible": (
                    payload.target_reader_outcome.benchmark_delta_reconstructible
                ),
                "operative_force_reconstructible": (
                    payload.target_reader_outcome.operative_force_reconstructible
                ),
                "boundary_reconstructible": (
                    payload.target_reader_outcome.boundary_reconstructible
                ),
                "nearby_case_predictable": (
                    payload.target_reader_outcome.nearby_case_predictable
                ),
                "outcome": payload.target_reader_outcome.outcome,
                "explanation": payload.target_reader_outcome.explanation,
            },
            "move_realizations": tuple(
                {
                    "realized_semantic_input_ids": (
                        item.realized_semantic_input_ids
                    ),
                    "realized_semantic_source_count": len(
                        item.realized_semantic_source_refs
                    ),
                    "realized_function": item.realized_function,
                    "intended_reader_update_delivered": (
                        item.intended_reader_update_delivered
                    ),
                    "formal_fidelity_preserved": item.formal_fidelity_preserved,
                    "explanation": item.explanation,
                }
                for item in payload.move_realizations
            ),
            "formal_fidelity_outcome": payload.formal_fidelity_outcome,
            "phrase_leak_audit_outcome": payload.phrase_leak_audit_outcome,
            "named_voice_imitation_outcome": payload.named_voice_imitation_outcome,
            "empirical_template_contamination_outcome": (
                payload.empirical_template_contamination_outcome
            ),
            "outcome": payload.outcome,
        }
    return _strip_role_internal(payload.model_dump(mode="json"))


def _phase4_predicate_receipt(
    parsed: tuple[tuple[EntityVersion, BaseModel], ...],
) -> BaseModel:
    """Select the one receipt bound to the exact focused proof obligation.

    An assurance bundle can contain evidence for many obligations.  Predicate
    mapping and audit packets must never inherit those unrelated artifacts.  A
    mapping request without one unambiguous receipt is therefore rejected; an
    audit may use its contract's code/predicate binding to disambiguate two
    harness families for the same obligation.
    """

    from .authoring import AssuranceBundle
    from .profile_craft import ObligationPredicateContract
    from .theory import ProofObligation

    obligations = tuple(
        (entity, payload)
        for entity, payload in parsed
        if isinstance(payload, ProofObligation)
    )
    assurances = tuple(
        payload for _, payload in parsed if isinstance(payload, AssuranceBundle)
    )
    contracts = tuple(
        payload
        for _, payload in parsed
        if isinstance(payload, ObligationPredicateContract)
    )
    if len(obligations) != 1 or len(assurances) != 1:
        raise ContextCompilationError(
            "predicate context requires exactly one ProofObligation and one AssuranceBundle"
        )
    obligation_entity, _ = obligations[0]
    obligation_ref = EntityVersionRef(
        entity_id=obligation_entity.entity_id,
        version=obligation_entity.version,
    )
    candidates = tuple(
        item
        for item in assurances[0].tool_receipts
        if item.obligation_ref == obligation_ref
    )
    if len(contracts) > 1:
        raise ContextCompilationError(
            "predicate audit context requires exactly one mapping contract"
        )
    if len(contracts) == 1:
        from .codec import object_digest

        contract = contracts[0]
        candidates = tuple(
            item
            for item in candidates
            if item.receipt_id == contract.receipt_id
            and object_digest(item) == contract.receipt_hash
            and item.code_ref == contract.code_ref
            and contract.predicate_artifact_ref == item.input_ref
        )
    if len(candidates) != 1:
        raise ContextCompilationError(
            "predicate context requires one unambiguous ToolHarnessReceipt for the focused obligation"
        )
    return candidates[0]


def _phase4_artifact_refs(
    route_id: str, parsed: tuple[tuple[EntityVersion, BaseModel], ...]
) -> tuple[ArtifactDependencyRef, ...]:
    from .authoring import ManuscriptUnit, RevisionBrief
    from .profile_craft import (
        CraftRealizationAssessment,
        ObligationPredicateContract,
    )

    selected: dict[tuple[str, int], ArtifactDependencyRef] = {}

    def add(reference: ArtifactDependencyRef) -> None:
        key = (reference.artifact_id, reference.version)
        prior = selected.get(key)
        if prior is not None and prior.content_hash != reference.content_hash:
            raise ContextCompilationError(
                "Phase 4 context repeats an artifact version with conflicting hashes"
            )
        selected[key] = reference

    if route_id in {
        "map.obligation_predicate",
        "audit.obligation_predicate",
    }:
        receipt = _phase4_predicate_receipt(parsed)
        for field_name in (
            "code_ref",
            "input_ref",
            "output_ref",
            "receipt_ref",
            "certificate_ref",
            "witness_ref",
        ):
            reference = getattr(receipt, field_name)
            if reference is not None:
                add(reference)
        for _, payload in parsed:
            if isinstance(payload, ObligationPredicateContract):
                for reference in _walk_artifact_refs(payload):
                    add(reference)

    for _, payload in parsed:
        if isinstance(payload, ManuscriptUnit) and route_id in {
            "diagnose.reader_problem",
            "compose.profiled_manuscript_unit",
            "review.craft_realization",
            "close.profile_craft_review",
        }:
            add(payload.manuscript_artifact_ref)
        # The diagnostician may inspect the exact brief attachment.  The writer
        # receives only the typed, identity-stripped RevisionBrief projection:
        # arbitrary brief bytes may contain reviewer/source identity metadata.
        if isinstance(payload, RevisionBrief) and route_id == "diagnose.reader_problem":
            add(payload.brief_artifact_ref)
        if isinstance(payload, CraftRealizationAssessment) and route_id == "close.profile_craft_review":
            add(payload.phrase_leak_audit_ref)
    return tuple(selected[key] for key in sorted(selected))


def _phase4_context_inputs(
    snapshot: Snapshot,
    *,
    route: RouteSpecV4,
    actor: Actor,
    focus_entity_ids: tuple[str, ...],
    layout: StoreLayout | None,
    clearance: PrivacyLabel,
    grants: frozenset[str],
    purpose: str,
) -> tuple[
    dict[tuple[str, int], EntityVersion],
    tuple[dict[str, Any], ...],
    dict[str, Any],
]:
    if layout is None:
        raise ContextCompilationError(
            "Phase 4 role context compilation requires the canonical StoreLayout"
        )
    visible_types = _PHASE4_VISIBLE_ENTITY_TYPES.get(route.route_id)
    packet_kind = _PHASE4_PACKET_KINDS.get(route.route_id)
    if visible_types is None or packet_kind is None:
        raise ContextCompilationError(f"unknown Phase 4 role route: {route.route_id}")
    current = _current_entities(snapshot)
    by_id = {entity.entity_id: entity for entity in current.values()}
    entities: dict[tuple[str, int], EntityVersion] = {}
    parsed: list[tuple[EntityVersion, BaseModel]] = []
    for entity_id in focus_entity_ids:
        entity = by_id.get(entity_id)
        if entity is None:
            raise ContextCompilationError(
                f"Phase 4 focus entity is not current: {entity_id}"
            )
        if entity.entity_type not in visible_types:
            continue
        if not _entity_accessible(
            entity, clearance=clearance, grants=grants, purpose=purpose
        ):
            raise ContextAccessError(
                f"Phase 4 focus entity is not readable: {entity.entity_id}@{entity.version}"
            )
        payload = _phase4_payload(entity)
        entities[_entity_key(entity)] = entity
        parsed.append((entity, payload))
    if not parsed:
        raise ContextCompilationError("Phase 4 role context selected no visible exact input")

    predicate_receipt: BaseModel | None = None
    if route.route_id in {
        "map.obligation_predicate",
        "audit.obligation_predicate",
    }:
        predicate_receipt = _phase4_predicate_receipt(tuple(parsed))
    artifact_refs = _phase4_artifact_refs(route.route_id, tuple(parsed))
    artifact_index = {
        (item.artifact_id, item.version): item for item in snapshot.artifacts
    }
    from .runtime.objects import ObjectStore

    store = ObjectStore(layout)
    full_artifacts: list[dict[str, Any]] = []
    role_artifacts: list[dict[str, Any]] = []
    for reference in artifact_refs:
        registration = artifact_index.get((reference.artifact_id, reference.version))
        if registration is None or registration.content_hash != reference.content_hash:
            raise ContextCompilationError(
                f"Phase 4 artifact is unresolved or hash-mismatched: "
                f"{reference.artifact_id}@{reference.version}"
            )
        if not _privacy_record_accessible(
            registration,
            clearance=clearance,
            grants=grants,
            purpose=purpose,
        ):
            raise ContextAccessError(
                f"Phase 4 artifact is not readable: "
                f"{registration.artifact_id}@{registration.version}"
            )
        data = store.read_bytes("artifacts", registration.content_hash, verify=True)
        if len(data) != registration.byte_size:
            raise ContextCompilationError("Phase 4 artifact byte_size mismatch")
        encoded = base64.b64encode(data).decode("ascii")
        full_artifacts.append(
            {
                "registration": registration.model_dump(mode="json"),
                "content_encoding": "base64",
                "content_base64": encoded,
            }
        )
        role_artifacts.append(
            {
                "logical_name": registration.logical_name,
                "media_type": registration.media_type,
                "content_encoding": "base64",
                "content_base64": encoded,
            }
        )

    semantic_inputs = tuple(
        {
            "kind": entity.entity_type,
            "content": _phase4_role_content(
                payload,
                packet_kind=packet_kind,
                predicate_receipt=predicate_receipt,
            ),
        }
        for entity, payload in parsed
    )
    role_packet = {
        "packet_schema": "econ-theorist/role-packet/v1",
        "packet_kind": packet_kind,
        "actor_kind": actor.kind,
        "constraints": _ROLE_CONSTRAINTS[packet_kind],
        "semantic_inputs": semantic_inputs,
        "artifacts": tuple(role_artifacts),
    }
    if route.route_id == "resolve.profile_stack":
        from .profile_craft_policy import profile_catalog_role_resource

        role_packet["static_resources"] = (profile_catalog_role_resource(),)
    elif route.route_id == "retrieve.craft_moves":
        from .profile_craft_policy import craft_corpus_role_resource

        role_packet["static_resources"] = (craft_corpus_role_resource(),)
    return entities, tuple(full_artifacts), role_packet


def _payload(
    snapshot: Snapshot,
    *,
    route: RouteSpecLike,
    purpose: str,
    focus_entity_ids: tuple[str, ...],
    budget_units: int,
    entities: Mapping[tuple[str, int], EntityVersion],
    relations: Mapping[tuple[str, int], RelationVersion],
    decisions: tuple[Decision, ...],
    omissions: tuple[str, ...],
    clearance: PrivacyLabel,
    grants: frozenset[str],
    exact_evaluation: bool = False,
    evaluation_artifacts: tuple[dict[str, Any], ...] = (),
    evaluation_decisions: tuple[Decision, ...] = (),
    phase3_role_packet: Mapping[str, Any] | None = None,
    phase4_role_packet: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selected_ids = frozenset(entity.entity_id for entity in entities.values())
    relevant_decisions = (
        ()
        if exact_evaluation
        else tuple(
            decision
            for decision in decisions
            if _decision_is_relevant(decision, selected_ids, snapshot.project_id)
        )
    )
    status_source_decisions = (
        ()
        if exact_evaluation
        else _status_source_decisions(snapshot, selected_ids)
    )
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
    blockers = (
        ()
        if exact_evaluation
        else tuple(
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
    derived_status = (
        {}
        if exact_evaluation
        else {
            entity_id: snapshot.derived_status[entity_id].model_dump(mode="json")
            for entity_id in sorted(selected_ids)
            if entity_id in snapshot.derived_status
        }
    )
    route_contract: dict[str, Any] = {
        "route_id": route.route_id,
        "route_version": route.route_version,
        "purpose": purpose,
        "authority_ceiling": route.authority_ceiling,
        "route_registry_hash": registry_hash_for_route(route),
        "instruction_bundle_id": route.instruction_bundle_id,
        "instruction_bundle_hash": route.instruction_bundle_hash,
        "allowed_operations": route.allowed_operations,
        "instructions": _route_instructions(route),
    }
    if isinstance(route, RouteSpecV2):
        route_contract.update(
            {
                "allowed_entity_types": route.allowed_entity_types,
                "allowed_relation_types": route.allowed_relation_types,
                "required_input_entities": tuple(
                    item.model_dump(mode="json")
                    for item in route.required_input_entities
                ),
                "required_output_entities": tuple(
                    item.model_dump(mode="json")
                    for item in route.required_output_entities
                ),
                "required_output_relations": tuple(
                    item.model_dump(mode="json")
                    for item in route.required_output_relations
                ),
                "required_gate_kinds": route.required_gate_kinds,
                "entry_validator_id": route.entry_validator_id,
                "exit_validator_id": route.exit_validator_id,
            }
        )
    payload = {
        "context_schema": "econ-theorist/compiled-context/v1",
        "source_head": snapshot.head,
        "project_id": snapshot.project_id,
        "route": route_contract,
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
    if exact_evaluation:
        payload.update(
            {
                "evaluation_selector": {
                    "mode": "exact_focus.v1",
                    "optional_neighbors": False,
                },
                "evaluation_artifacts": evaluation_artifacts,
                "evaluation_decisions": tuple(
                    decision.model_dump(mode="json")
                    for decision in sorted(evaluation_decisions, key=_decision_key)
                ),
            }
        )
    if phase3_role_packet is not None:
        payload.update(
            {
                "phase3_selector": {
                    "mode": "exact_role_packet.v1",
                    "provider_must_receive_role_packet_only": True,
                },
                "phase3_role_packet": dict(phase3_role_packet),
            }
        )
    if phase4_role_packet is not None:
        payload.update(
            {
                "phase4_selector": {
                    "mode": "exact_profile_craft_role_packet.v1",
                    "provider_must_receive_role_packet_only": True,
                    "raw_anchor_material_allowed": False,
                },
                "phase4_role_packet": dict(phase4_role_packet),
            }
        )
    return payload


def compile_context(
    snapshot: Snapshot,
    *,
    route: RouteSpecLike,
    actor: Actor,
    purpose: str,
    compartments: Iterable[str],
    privacy_clearance: PrivacyLabel,
    focus_entity_ids: Iterable[str] = (),
    budget_units: int,
    layout: StoreLayout | None = None,
    selector_version: str | None = None,
) -> CompiledContext:
    """Compile a deterministic exact-version context without touching disk."""

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
    selected_selector_version = (
        selector_version_for_route(route)
        if selector_version is None
        else selector_version
    )
    if not selector_version_is_supported(route, selected_selector_version):
        raise ContextCompilationError(
            f"unsupported selector version for route {route.route_id}: "
            f"{selected_selector_version}"
        )

    if isinstance(route, RouteSpecV4) and route.route_id in _PHASE4_NATIVE_ROUTE_IDS:
        exact_entities, phase4_artifacts, role_packet = _phase4_context_inputs(
            snapshot,
            route=route,
            actor=actor,
            focus_entity_ids=focus,
            layout=layout,
            clearance=privacy_clearance,
            grants=grants,
            purpose=purpose,
        )
        payload = _payload(
            snapshot,
            route=route,
            purpose=purpose,
            focus_entity_ids=focus,
            budget_units=budget_units,
            entities=exact_entities,
            relations={},
            decisions=snapshot.decisions,
            omissions=(),
            clearance=privacy_clearance,
            grants=grants,
            phase4_role_packet=role_packet,
        )
        payload["phase4_artifacts"] = phase4_artifacts
        encoded = canonical_json_bytes(payload)
        used_units = units_for_bytes(encoded)
        if used_units > budget_units:
            raise ContextBudgetError(
                f"required exact Phase 4 role context needs {used_units} "
                f"{TOKENIZER_ID} units; budget is {budget_units}"
            )
        selected_refs = tuple(
            EntityVersionRef(entity_id=entity.entity_id, version=entity.version)
            for entity in sorted(exact_entities.values(), key=_entity_key)
        )
        return CompiledContext(
            payload=payload,
            encoded=encoded,
            context_hash=sha256_digest(encoded),
            selected_entity_refs=selected_refs,
            omissions=(),
            used_units=used_units,
        )

    if isinstance(route, RouteSpecV3) and route.route_id in _PHASE3_NATIVE_ROUTE_IDS:
        exact_entities, phase3_artifacts, role_packet = _phase3_context_inputs(
            snapshot,
            route=route,
            actor=actor,
            focus_entity_ids=focus,
            layout=layout,
            clearance=privacy_clearance,
            grants=grants,
            purpose=purpose,
        )
        payload = _payload(
            snapshot,
            route=route,
            purpose=purpose,
            focus_entity_ids=focus,
            budget_units=budget_units,
            entities=exact_entities,
            relations={},
            decisions=(),
            omissions=(),
            clearance=privacy_clearance,
            grants=grants,
            phase3_role_packet=role_packet,
        )
        payload["phase3_artifacts"] = phase3_artifacts
        encoded = canonical_json_bytes(payload)
        used_units = units_for_bytes(encoded)
        if used_units > budget_units:
            raise ContextBudgetError(
                f"required exact Phase 3 role context needs {used_units} "
                f"{TOKENIZER_ID} units; budget is {budget_units}"
            )
        selected_refs = tuple(
            EntityVersionRef(entity_id=entity.entity_id, version=entity.version)
            for entity in sorted(exact_entities.values(), key=_entity_key)
        )
        return CompiledContext(
            payload=payload,
            encoded=encoded,
            context_hash=sha256_digest(encoded),
            selected_entity_refs=selected_refs,
            omissions=(),
            used_units=used_units,
        )

    expected_evaluation_purpose = _EVALUATION_ROUTE_PURPOSES.get(route.route_id)
    if expected_evaluation_purpose is not None:
        if purpose != expected_evaluation_purpose:
            raise ContextAccessError(
                f"route {route.route_id} requires purpose "
                f"{expected_evaluation_purpose!r}"
            )
        exact_entities = _evaluation_exact_entities(
            snapshot,
            focus_entity_ids=focus,
            clearance=privacy_clearance,
            grants=grants,
            purpose=purpose,
            require_manifest=route.route_id == "evaluate.blind_argument_package",
        )
        evaluation_artifacts, evaluation_decisions = _evaluation_context_inputs(
            snapshot,
            exact_entities,
            route_id=route.route_id,
            layout=layout,
            clearance=privacy_clearance,
            grants=grants,
            purpose=purpose,
        )
        payload = _payload(
            snapshot,
            route=route,
            purpose=purpose,
            focus_entity_ids=focus,
            budget_units=budget_units,
            entities=exact_entities,
            relations={},
            decisions=(),
            omissions=(),
            clearance=privacy_clearance,
            grants=grants,
            exact_evaluation=True,
            evaluation_artifacts=evaluation_artifacts,
            evaluation_decisions=evaluation_decisions,
        )
        encoded = canonical_json_bytes(payload)
        used_units = units_for_bytes(encoded)
        if used_units > budget_units:
            raise ContextBudgetError(
                f"required exact evaluation context needs {used_units} "
                f"{TOKENIZER_ID} units; budget is {budget_units}"
            )
        selected_refs = tuple(
            EntityVersionRef(entity_id=entity.entity_id, version=entity.version)
            for entity in sorted(exact_entities.values(), key=_entity_key)
        )
        return CompiledContext(
            payload=payload,
            encoded=encoded,
            context_hash=sha256_digest(encoded),
            selected_entity_refs=selected_refs,
            omissions=(),
            used_units=used_units,
        )

    required_entities, required_relations, decisions = _required_slice(
        snapshot,
        route=route,
        focus_entity_ids=focus,
        clearance=privacy_clearance,
        grants=grants,
        purpose=purpose,
        include_decomposition_preservation=(
            selected_selector_version
            in {
                SELECTOR_VERSION_DECOMPOSITION_REFRESH_V1,
                SELECTOR_VERSION_DECOMPOSITION_REFRESH,
            }
        ),
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
    route: RouteSpecLike,
    actor: Actor,
    purpose: str,
    compartments: Iterable[str],
    privacy_clearance: PrivacyLabel,
    focus_entity_ids: Iterable[str],
    budget_units: int,
    created_at: str,
    selector_version: str | None = None,
) -> ContextManifest:
    """Bind compiled bytes to one immutable operational manifest."""

    selected_selector_version = (
        selector_version_for_route(route)
        if selector_version is None
        else selector_version
    )
    if not selector_version_is_supported(route, selected_selector_version):
        raise ContextCompilationError(
            f"unsupported selector version for route {route.route_id}: "
            f"{selected_selector_version}"
        )
    return ContextManifest(
        context_manifest_id=context_manifest_id,
        project_id=snapshot.project_id,
        source_head=snapshot.head,
        route_id=route.route_id,
        route_version=route.route_version,
        route_registry_hash=registry_hash_for_route(route),
        decision_registry_version=decision_registry_version_for_route(route),
        selector_version=selected_selector_version,
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
