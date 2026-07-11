"""Deterministic facet hashes and derived freshness for Phase 1.

Freshness is deliberately a projection.  Nothing in this module mutates an
entity or records a scientific status transition.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any, TypeAlias

from ..codec import object_digest
from ..models import (
    FACET_ORDER,
    Decision,
    DecisionKind,
    DecisionVersionRef,
    EntityDerivedStatus,
    EntityVersion,
    Facet,
    FacetPathRef,
    HumanAcceptance,
    RelationVersion,
    SemanticFacetRef,
    Snapshot,
    StaleDependencyEvidence,
    StaleReason,
)


FacetNode: TypeAlias = tuple[str, int, Facet, str | None]
_JSON_ARRAY_INDEX = re.compile(r"0|[1-9][0-9]*")


class FacetPathError(ValueError):
    """A semantic facet field path cannot be resolved exactly."""


def _path_parts(field_path: str) -> tuple[str, ...]:
    if not field_path.startswith("/"):
        raise FacetPathError("facet field paths must be RFC 6901 JSON Pointers")
    return tuple(
        part.replace("~1", "/").replace("~0", "~")
        for part in field_path[1:].split("/")
    )


def facet_semantic_value(
    entity: EntityVersion,
    facet: Facet,
    field_path: str | None = None,
) -> Any:
    """Return the exact JSON-native value governed by a facet reference."""

    payload: Any = getattr(entity.facets, facet)
    if field_path is None:
        # Whole-facet hashes cover every stored field whose change carries that
        # scientific meaning. Identity/version/provenance fields stay outside
        # the semantic comparison; created_at must never stale research.
        if facet == "formal":
            return {
                "payload": payload,
                "scope_ref": entity.scope_ref,
                "formal_validity": entity.status.formal_validity,
            }
        if facet == "economic_interpretation":
            return {
                "payload": payload,
                "scope_ref": entity.scope_ref,
                "interpretation_validity": entity.status.interpretation_validity,
            }
        if facet == "literature_novelty":
            return {
                "payload": payload,
                "scope_ref": entity.scope_ref,
                "literature": entity.status.literature,
            }
        if facet == "terminology_presentation":
            return {
                "payload": payload,
                "title": entity.title,
                "summary": entity.summary,
            }
        return {
            "payload": payload,
            "lifecycle": entity.status.lifecycle,
            "privacy": entity.privacy,
            "access_compartments": entity.access_compartments,
            "artifact_refs": entity.artifact_refs,
        }
    value = payload
    for part in _path_parts(field_path):
        if isinstance(value, Mapping):
            if part not in value:
                raise FacetPathError(
                    f"missing facet path {field_path!r} on "
                    f"{entity.entity_id}@{entity.version}:{facet}"
                )
            value = value[part]
        elif isinstance(value, Sequence) and not isinstance(
            value, (str, bytes, bytearray)
        ):
            if _JSON_ARRAY_INDEX.fullmatch(part) is None:
                raise FacetPathError(
                    f"noncanonical sequence component {part!r} in facet path "
                    f"{field_path!r}"
                )
            try:
                index = int(part, 10)
                value = value[index]
            except (ValueError, IndexError) as exc:
                raise FacetPathError(
                    f"invalid sequence component {part!r} in facet path "
                    f"{field_path!r}"
                ) from exc
        else:
            raise FacetPathError(
                f"facet path {field_path!r} traverses a scalar at {part!r}"
            )
    return value


def facet_semantic_hash(
    entity: EntityVersion,
    facet: Facet,
    field_path: str | None = None,
) -> str:
    """Hash one whole semantic facet or one exact field within it."""

    return object_digest(facet_semantic_value(entity, facet, field_path))


def authority_semantic_hash(
    entity: EntityVersion,
    decisions: Sequence[Decision],
    effective_decisions: Mapping[str, DecisionVersionRef],
) -> str:
    """Hash stored authority fields plus effective Decisions governing an entity.

    This is the binding used by an invalidating relation whose upstream facet
    is the whole ``authority`` facet. Proposed or superseded Decisions are not
    effective authority and therefore do not enter the digest.
    """

    effective_refs = {
        (reference.decision_id, reference.version)
        for reference in effective_decisions.values()
    }
    governing = [
        {
            "decision_id": decision.decision_id,
            "version": decision.version,
            "decision_kind": decision.decision_kind,
            "subject_ref": decision.subject_ref,
            "scope_ref": decision.scope_ref,
            "selected_option": decision.selected_option,
            "status": decision.status,
        }
        for decision in decisions
        if (decision.decision_id, decision.version) in effective_refs
        and _governs(decision, entity.entity_id)
    ]
    governing.sort(key=lambda item: (item["decision_kind"], item["decision_id"], item["version"]))
    return object_digest(
        {
            "stored_authority": facet_semantic_value(entity, "authority"),
            "effective_decisions": governing,
        }
    )


def changed_semantic_facets(
    previous: EntityVersion, current: EntityVersion
) -> tuple[Facet, ...]:
    """Return the canonical ordered set of actually changed facet payloads."""

    return tuple(
        facet
        for facet in FACET_ORDER
        if facet_semantic_hash(previous, facet)
        != facet_semantic_hash(current, facet)
    )


def _decision_ref_key(reference: DecisionVersionRef) -> tuple[str, int]:
    return reference.decision_id, reference.version


def _governs(decision: Decision, entity_id: str) -> bool:
    return (
        decision.subject_ref == entity_id
        or entity_id in decision.affected_scopes
    )


def _human_acceptance_projection(
    entity_id: str,
    decisions: Sequence[Decision],
    effective_decisions: Mapping[str, DecisionVersionRef],
) -> tuple[
    HumanAcceptance,
    dict[DecisionKind, HumanAcceptance],
    dict[DecisionKind, tuple[DecisionVersionRef, ...]],
]:
    effective_refs = {
        _decision_ref_key(reference)
        for reference in effective_decisions.values()
    }
    governing = [
        decision
        for decision in decisions
        if _decision_ref_key(
            DecisionVersionRef(
                decision_id=decision.decision_id,
                version=decision.version,
            )
        )
        in effective_refs
        and _governs(decision, entity_id)
    ]
    def acceptance(status: str) -> HumanAcceptance:
        return {
            "provisional": "human_provisional",
            "confirmed": "human_confirmed",
            "rejected": "human_rejected",
            "superseded": "superseded",
        }.get(status, "agent_proposed")  # type: ignore[return-value]

    def combine(values: Sequence[HumanAcceptance]) -> HumanAcceptance:
        unique = set(values)
        if not unique:
            return "agent_proposed"
        if len(unique) == 1:
            return next(iter(unique))
        return "human_mixed"

    by_kind_values: dict[DecisionKind, list[HumanAcceptance]] = {}
    by_kind_sources: dict[DecisionKind, list[DecisionVersionRef]] = {}
    for decision in governing:
        by_kind_values.setdefault(decision.decision_kind, []).append(
            acceptance(decision.status)
        )
        by_kind_sources.setdefault(decision.decision_kind, []).append(
            DecisionVersionRef(
                decision_id=decision.decision_id,
                version=decision.version,
            )
        )

    # An explicit terminal supersession remains visible even when it leaves no
    # effective choice for that kind. Mere proposals never erase acceptance.
    for decision in reversed(decisions):
        if (
            decision.status == "superseded"
            and _governs(decision, entity_id)
            and decision.decision_kind not in by_kind_values
        ):
            by_kind_values[decision.decision_kind] = ["superseded"]
            by_kind_sources[decision.decision_kind] = [
                DecisionVersionRef(
                    decision_id=decision.decision_id,
                    version=decision.version,
                )
            ]

    by_kind = {
        kind: combine(values)
        for kind, values in sorted(by_kind_values.items())
    }
    source_refs = {
        kind: tuple(
            sorted(
                references,
                key=lambda reference: (reference.decision_id, reference.version),
            )
        )
        for kind, references in sorted(by_kind_sources.items())
    }
    return combine(tuple(by_kind.values())), by_kind, source_refs


def _node(reference: FacetPathRef) -> FacetNode:
    return (
        reference.entity_id,
        reference.version,
        reference.facet,
        reference.field_path,
    )


def field_paths_overlap(left: str | None, right: str | None) -> bool:
    """Whether two canonical JSON Pointer regions can change one another."""

    if left is None or right is None:
        return True
    return (
        left == right
        or left.startswith(right + "/")
        or right.startswith(left + "/")
    )


def facet_nodes_overlap(left: FacetNode, right: FacetNode) -> bool:
    return (
        left[:3] == right[:3]
        and field_paths_overlap(left[3], right[3])
    )


def _node_is_stale(node: FacetNode, stale_nodes: set[FacetNode]) -> bool:
    return any(facet_nodes_overlap(node, stale) for stale in stale_nodes)


def _stale_evidence_key(
    evidence: StaleDependencyEvidence,
) -> tuple[str, int, str, int, str, str, str, int, str]:
    return (
        evidence.relation_id,
        evidence.relation_version,
        evidence.upstream.entity_id,
        evidence.upstream.version,
        evidence.upstream.facet,
        evidence.upstream.field_path or "",
        evidence.upstream.semantic_hash,
        evidence.current_upstream_version or 0,
        evidence.current_semantic_hash or "",
    )


def _merge_stale_evidence(
    evidence: Sequence[StaleDependencyEvidence],
) -> tuple[StaleDependencyEvidence, ...]:
    by_key = {_stale_evidence_key(item): item for item in evidence}
    return tuple(by_key[key] for key in sorted(by_key))


def derive_entity_statuses(
    *,
    entity_versions: Sequence[EntityVersion],
    relation_versions: Sequence[RelationVersion],
    decisions: Sequence[Decision],
    current_entities: Mapping[str, int],
    current_relations: Mapping[str, int],
    effective_decisions: Mapping[str, DecisionVersionRef],
) -> dict[str, EntityDerivedStatus]:
    """Derive the smallest stale current-facet subgraph and its reasons."""

    entities = {
        (entity.entity_id, entity.version): entity for entity in entity_versions
    }
    relations = {
        (relation.relation_id, relation.version): relation
        for relation in relation_versions
    }
    current_entity_objects = {
        entity_id: entities[(entity_id, version)]
        for entity_id, version in current_entities.items()
    }
    active_relations = sorted(
        (
            relations[(relation_id, version)]
            for relation_id, version in current_relations.items()
        ),
        key=lambda relation: (relation.relation_id, relation.version),
    )
    invalidating = [
        relation
        for relation in active_relations
        if relation.dependency_mode != "trace_only"
    ]

    stale_nodes: set[FacetNode] = set()
    reasons: dict[FacetNode, list[StaleReason]] = {}

    def current_hash_for(entity: EntityVersion, reference: SemanticFacetRef) -> str:
        if reference.facet == "authority" and reference.field_path is None:
            return authority_semantic_hash(entity, decisions, effective_decisions)
        return facet_semantic_hash(
            entity,
            reference.facet,
            reference.field_path,
        )

    def add_reason(node: FacetNode, reason: StaleReason) -> bool:
        bucket = reasons.setdefault(node, [])
        marker = (reason.relation_id, reason.relation_version, reason.inherited_from)
        for index, item in enumerate(bucket):
            if (
                item.relation_id,
                item.relation_version,
                item.inherited_from,
            ) != marker:
                continue
            merged = _merge_stale_evidence(
                (*item.source_evidence, *reason.source_evidence)
            )
            if merged == item.source_evidence:
                return False
            bucket[index] = item.model_copy(update={"source_evidence": merged})
            return True
        bucket.append(reason)
        stale_nodes.add(node)
        return True

    def relation_evidence(
        relation: RelationVersion,
        current: EntityVersion | None,
        current_hash: str | None,
    ) -> StaleDependencyEvidence:
        assert relation.upstream is not None
        return StaleDependencyEvidence(
            relation_id=relation.relation_id,
            relation_version=relation.version,
            dependency_mode=relation.dependency_mode,
            upstream=relation.upstream,
            current_upstream_version=(
                current.version if current is not None else None
            ),
            current_semantic_hash=current_hash,
        )

    def source_evidence_for_node(node: FacetNode) -> tuple[StaleDependencyEvidence, ...]:
        return _merge_stale_evidence(
            tuple(
                evidence
                for stale_node, stale_reasons in reasons.items()
                if facet_nodes_overlap(node, stale_node)
                for stale_reason in stale_reasons
                for evidence in stale_reason.source_evidence
            )
        )

    def semantic_hash_for_node(entity: EntityVersion, node: FacetNode) -> str:
        _, _, facet, field_path = node
        if facet == "authority" and field_path is None:
            return authority_semantic_hash(entity, decisions, effective_decisions)
        return facet_semantic_hash(entity, facet, field_path)

    def carry_forward_to_current_versions() -> bool:
        changed_projection = False
        for stale_node in tuple(stale_nodes):
            entity_id, stale_version, facet, field_path = stale_node
            current_version = current_entities.get(entity_id)
            if current_version is None or current_version == stale_version:
                continue
            historical = entities.get((entity_id, stale_version))
            current = entities.get((entity_id, current_version))
            if historical is None or current is None:
                continue
            try:
                unchanged = semantic_hash_for_node(
                    historical, stale_node
                ) == semantic_hash_for_node(
                    current,
                    (entity_id, current_version, facet, field_path),
                )
            except FacetPathError:
                unchanged = False
            if not unchanged:
                continue
            current_node = (entity_id, current_version, facet, field_path)
            for reason in tuple(reasons.get(stale_node, ())):
                changed_projection = add_reason(current_node, reason) or changed_projection
        return changed_projection

    # Direct invalidation compares the exact bound semantic value with the
    # current version of that entity.  A version-only supersession is harmless.
    for relation in invalidating:
        assert relation.upstream is not None
        assert relation.downstream is not None
        current = current_entity_objects.get(relation.upstream.entity_id)
        current_hash: str | None = None
        if current is not None:
            try:
                current_hash = current_hash_for(current, relation.upstream)
            except FacetPathError:
                # Removing a previously bound field is itself a semantic change.
                current_hash = None
        if current is None or current_hash != relation.upstream.semantic_hash:
            evidence = relation_evidence(relation, current, current_hash)
            add_reason(
                _node(relation.downstream),
                StaleReason(
                    relation_id=relation.relation_id,
                    relation_version=relation.version,
                    dependency_mode=relation.dependency_mode,
                    upstream=relation.upstream,
                    current_upstream_version=(
                        current.version if current is not None else None
                    ),
                    current_semantic_hash=current_hash,
                    source_evidence=(evidence,),
                    message=(
                        "the current upstream semantic value no longer matches "
                        "the exact value bound by this dependency"
                    ),
                ),
            )

    carry_forward_to_current_versions()

    # The invalidating graph is acyclic, but a fixed point makes field-path to
    # whole-facet aggregation explicit and deterministic.
    changed = True
    while changed:
        changed = carry_forward_to_current_versions()
        for relation in invalidating:
            assert relation.upstream is not None
            assert relation.downstream is not None
            upstream_node = _node(relation.upstream)
            if not _node_is_stale(upstream_node, stale_nodes):
                continue
            current = current_entity_objects.get(relation.upstream.entity_id)
            current_hash: str | None = None
            if current is not None:
                try:
                    current_hash = current_hash_for(current, relation.upstream)
                except FacetPathError:
                    pass
            inherited = FacetPathRef(
                entity_id=relation.upstream.entity_id,
                version=relation.upstream.version,
                facet=relation.upstream.facet,
                field_path=relation.upstream.field_path,
            )
            evidence = relation_evidence(relation, current, current_hash)
            source_evidence = _merge_stale_evidence(
                (*source_evidence_for_node(upstream_node), evidence)
            )
            changed = add_reason(
                _node(relation.downstream),
                StaleReason(
                    relation_id=relation.relation_id,
                    relation_version=relation.version,
                    dependency_mode=relation.dependency_mode,
                    upstream=relation.upstream,
                    current_upstream_version=(
                        current.version if current is not None else None
                    ),
                    current_semantic_hash=current_hash,
                    inherited_from=inherited,
                    source_evidence=source_evidence,
                    message=(
                        "the dependency is blocked by an already stale "
                        "upstream facet"
                    ),
                ),
            ) or changed

    result: dict[str, EntityDerivedStatus] = {}
    for entity_id in sorted(current_entities):
        current_version = current_entities[entity_id]
        freshness = {facet: "fresh" for facet in FACET_ORDER}
        stale_reasons: dict[Facet, tuple[StaleReason, ...]] = {}
        for facet in FACET_ORDER:
            facet_nodes = [
                node
                for node in stale_nodes
                if node[0] == entity_id
                and node[1] == current_version
                and node[2] == facet
            ]
            if facet_nodes:
                freshness[facet] = "stale"
                collected = {
                    (
                        reason.relation_id,
                        reason.relation_version,
                        reason.inherited_from,
                    ): reason
                    for node in facet_nodes
                    for reason in reasons.get(node, ())
                }
                stale_reasons[facet] = tuple(
                    sorted(
                        collected.values(),
                        key=lambda reason: (
                            reason.relation_id,
                            reason.relation_version,
                            "" if reason.inherited_from is None else str(reason.inherited_from),
                        ),
                    )
                )
        (
            human_acceptance,
            acceptance_by_kind,
            acceptance_source_refs,
        ) = _human_acceptance_projection(
            entity_id, decisions, effective_decisions
        )
        result[entity_id] = EntityDerivedStatus(
            human_acceptance=human_acceptance,
            acceptance_by_kind=acceptance_by_kind,
            acceptance_source_refs=acceptance_source_refs,
            freshness=freshness,
            stale_reasons=stale_reasons,
        )
    return result


def stale_reason_chains(
    snapshot: Snapshot,
    entity_id: str,
    facet: Facet,
) -> tuple[tuple[StaleReason, ...], ...]:
    """Return finite upstream-to-downstream explanations for one stale facet."""

    def walk(
        current_entity: str,
        current_facet: Facet,
        seen: frozenset[tuple[str, Facet]],
    ) -> tuple[tuple[StaleReason, ...], ...]:
        marker = (current_entity, current_facet)
        if marker in seen:
            return ()
        status = snapshot.derived_status.get(current_entity)
        if status is None:
            return ()
        chains: list[tuple[StaleReason, ...]] = []
        for reason in status.stale_reasons.get(current_facet, ()):
            if reason.inherited_from is None:
                chains.append((reason,))
                continue
            prefixes = walk(
                reason.inherited_from.entity_id,
                reason.inherited_from.facet,
                seen | {marker},
            )
            if prefixes:
                chains.extend(prefix + (reason,) for prefix in prefixes)
            else:
                chains.append((reason,))
        return tuple(chains)

    return walk(entity_id, facet, frozenset())


__all__ = [
    "FacetPathError",
    "authority_semantic_hash",
    "changed_semantic_facets",
    "derive_entity_statuses",
    "facet_nodes_overlap",
    "facet_semantic_hash",
    "facet_semantic_value",
    "field_paths_overlap",
    "stale_reason_chains",
]
