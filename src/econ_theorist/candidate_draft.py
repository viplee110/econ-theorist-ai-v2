"""Minimal, fail-closed materialization for one declared candidate draft value.

Canonical ``Transaction`` and relation models remain unchanged.  This module
only recognizes an explicit JSON null at the unique relation topology declared
by a ``runtime_facet_semantic_hash_v1`` contract template, computes that value
from the complete candidate source entity, and returns in-memory JSON for a
second strict canonical parse.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from typing import Any

from .candidate_contract import (
    CandidateAuthoringContractV1,
    CandidateHardRelationTemplateV1,
    CandidateRelationEndpointV1,
)
from .codec import canonical_json_bytes
from .models import EntityVersion, EntityVersionRef
from .runtime.freshness import facet_semantic_hash


class CandidateDraftMaterializationError(ValueError):
    """A draft null did not occupy one unique, exact contract location."""

    def __init__(
        self,
        *,
        location: tuple[str | int, ...],
        issue_type: str,
        message: str,
    ) -> None:
        super().__init__(message)
        self.location = location
        self.issue_type = issue_type
        self.message = message


class _DuplicateJsonKey(ValueError):
    pass


def _object_without_duplicate_keys(
    pairs: Iterable[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJsonKey(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON constant: {value}")


def _parse_candidate_object(data: bytes) -> dict[str, Any] | None:
    try:
        decoded = data.decode("utf-8")
        value = json.loads(
            decoded,
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_nonfinite_constant,
        )
    except _DuplicateJsonKey as exc:
        raise CandidateDraftMaterializationError(
            location=(),
            issue_type="candidate_draft_duplicate_json_key",
            message=str(exc),
        ) from exc
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        # The original strict Transaction diagnostic is more useful for
        # ordinary malformed input that never reached draft semantics.
        return None
    return value if isinstance(value, dict) else None


def _runtime_templates(
    contract: CandidateAuthoringContractV1,
) -> tuple[CandidateHardRelationTemplateV1, ...]:
    return tuple(
        item
        for item in contract.output_contract.required_relation_templates
        if item.upstream_semantic_hash_binding
        == "runtime_facet_semantic_hash_v1"
    )


def _candidate_entities(root: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    operations = root.get("operations")
    if not isinstance(operations, list):
        return []
    found: list[tuple[int, dict[str, Any]]] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or operation.get("op") not in {
            "entity.create",
            "entity.supersede",
        }:
            continue
        entity = operation.get("entity")
        if isinstance(entity, dict):
            found.append((index, entity))
    return found


def _candidate_relations(root: dict[str, Any]) -> list[tuple[int, dict[str, Any]]]:
    operations = root.get("operations")
    if not isinstance(operations, list):
        return []
    found: list[tuple[int, dict[str, Any]]] = []
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or operation.get("op") not in {
            "relation.create",
            "relation.supersede",
        }:
            continue
        relation = operation.get("relation")
        if isinstance(relation, dict):
            found.append((index, relation))
    return found


def _resolve_endpoint(
    endpoint: CandidateRelationEndpointV1,
    entities: list[tuple[int, dict[str, Any]]],
    *,
    template_id: str,
) -> tuple[EntityVersionRef, dict[str, Any] | None]:
    if endpoint.binding_kind == "exact_input":
        assert endpoint.entity_ref is not None
        return endpoint.entity_ref, None

    assert endpoint.output_ordinal is not None
    matches = tuple(
        (index, entity)
        for index, entity in entities
        if entity.get("entity_type") == endpoint.entity_type
    )
    ordinal = endpoint.output_ordinal
    if len(matches) < ordinal:
        raise CandidateDraftMaterializationError(
            location=("operations",),
            issue_type="candidate_draft_endpoint_unresolved",
            message=(
                f"runtime template {template_id!r} requires candidate output "
                f"{endpoint.entity_type!r} ordinal {ordinal}"
            ),
        )
    operation_index, raw_entity = matches[ordinal - 1]
    try:
        # Strict JSON parsing accepts JSON arrays for tuple-valued canonical
        # fields while still rejecting coercions.  Strict Python validation
        # would incorrectly reject every ordinary serialized entity array.
        entity = EntityVersion.model_validate_json(
            canonical_json_bytes(raw_entity),
            strict=True,
        )
    except ValueError as exc:
        raise CandidateDraftMaterializationError(
            location=("operations", operation_index, "entity"),
            issue_type="candidate_draft_source_entity_invalid",
            message=(
                f"runtime template {template_id!r} cannot hash an invalid "
                "candidate source EntityVersion"
            ),
        ) from exc
    return (
        EntityVersionRef(entity_id=entity.entity_id, version=entity.version),
        raw_entity,
    )


def _strict_scalar_equal(value: Any, expected: Any) -> bool:
    return type(value) is type(expected) and value == expected


def _ref_matches(raw: Any, expected: EntityVersionRef) -> bool:
    return (
        isinstance(raw, dict)
        and set(raw) == {"entity_id", "version"}
        and _strict_scalar_equal(raw.get("entity_id"), expected.entity_id)
        and _strict_scalar_equal(raw.get("version"), expected.version)
    )


def _facet_ref_matches(
    raw: Any,
    *,
    expected: EntityVersionRef,
    facet: str,
    field_path: None,
    semantic: bool,
) -> bool:
    if not isinstance(raw, dict):
        return False
    permitted = {"entity_id", "version", "facet", "field_path"}
    if semantic:
        permitted.add("semantic_hash")
    if not set(raw).issubset(permitted):
        return False
    if not {"entity_id", "version", "facet"}.issubset(raw):
        return False
    return (
        _strict_scalar_equal(raw.get("entity_id"), expected.entity_id)
        and _strict_scalar_equal(raw.get("version"), expected.version)
        and _strict_scalar_equal(raw.get("facet"), facet)
        and raw.get("field_path") is field_path
    )


def _relation_topology_matches(
    raw: dict[str, Any],
    *,
    template: CandidateHardRelationTemplateV1,
    source_ref: EntityVersionRef,
    target_ref: EntityVersionRef,
) -> bool:
    if not (
        _strict_scalar_equal(raw.get("relation_type"), template.relation_type)
        and _strict_scalar_equal(raw.get("version"), template.version)
        and raw.get("supersedes") is template.supersedes
        and _strict_scalar_equal(raw.get("dependency_mode"), template.dependency_mode)
        and _ref_matches(raw.get("source"), source_ref)
        and _ref_matches(raw.get("target"), target_ref)
    ):
        return False
    return _facet_ref_matches(
        raw.get("upstream"),
        expected=source_ref,
        facet=template.source.facet,
        field_path=template.source.field_path,
        semantic=True,
    ) and _facet_ref_matches(
        raw.get("downstream"),
        expected=target_ref,
        facet=template.target.facet,
        field_path=template.target.field_path,
        semantic=False,
    )


def _contains_explicit_null_semantic_hash(root: dict[str, Any]) -> bool:
    return any(
        isinstance(relation.get("upstream"), dict)
        and "semantic_hash" in relation["upstream"]
        and relation["upstream"]["semantic_hash"] is None
        for _, relation in _candidate_relations(root)
    )


def materialize_runtime_facet_hashes(
    data: bytes,
    contract: CandidateAuthoringContractV1,
) -> bytes | None:
    """Return materialized in-memory JSON, or ``None`` when not applicable.

    Applicability requires both a runtime template and an explicit null
    semantic hash.  Every applicable template must match one and only one
    exact candidate relation topology.  Nothing else is repaired.
    """

    templates = _runtime_templates(contract)
    if not templates:
        return None
    root = _parse_candidate_object(data)
    if root is None or not _contains_explicit_null_semantic_hash(root):
        return None

    entities = _candidate_entities(root)
    relations = _candidate_relations(root)
    changed = False
    for template in templates:
        source_ref, raw_source = _resolve_endpoint(
            template.source,
            entities,
            template_id=template.template_id,
        )
        target_ref, _ = _resolve_endpoint(
            template.target,
            entities,
            template_id=template.template_id,
        )
        matches = tuple(
            (index, relation)
            for index, relation in relations
            if _relation_topology_matches(
                relation,
                template=template,
                source_ref=source_ref,
                target_ref=target_ref,
            )
        )
        if len(matches) != 1:
            raise CandidateDraftMaterializationError(
                location=("operations",),
                issue_type=(
                    "candidate_draft_template_missing"
                    if not matches
                    else "candidate_draft_template_duplicated"
                ),
                message=(
                    f"runtime template {template.template_id!r} must match "
                    f"exactly one relation topology; found {len(matches)}"
                ),
            )
        operation_index, relation = matches[0]
        upstream = relation["upstream"]
        assert isinstance(upstream, dict)
        if "semantic_hash" not in upstream:
            raise CandidateDraftMaterializationError(
                location=("operations", operation_index, "relation", "upstream"),
                issue_type="candidate_draft_hash_missing",
                message=(
                    f"runtime template {template.template_id!r} requires an "
                    "explicit semantic_hash value or JSON null"
                ),
            )
        if upstream["semantic_hash"] is not None:
            # A valid explicit digest is canonical input, not a draft value.
            continue
        if raw_source is None:
            raise CandidateDraftMaterializationError(
                location=("operations", operation_index, "relation", "upstream"),
                issue_type="candidate_draft_source_not_candidate_output",
                message="runtime facet hashes require a candidate-output source",
            )
        source_entity = EntityVersion.model_validate_json(
            canonical_json_bytes(raw_source),
            strict=True,
        )
        upstream["semantic_hash"] = facet_semantic_hash(
            source_entity,
            template.source.facet,
            template.source.field_path,
        )
        changed = True

    if not changed:
        return None
    # This is still draft input to a second strict model parse, not canonical
    # Transaction bytes.  Ordinary JSON serialization lets that model report
    # unrelated invalid values instead of turning them into bridge internals.
    return json.dumps(
        root,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


__all__ = [
    "CandidateDraftMaterializationError",
    "materialize_runtime_facet_hashes",
]
