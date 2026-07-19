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
from dataclasses import dataclass
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
        expected: Any | None = None,
        observed: Any | None = None,
        mismatch_kind: str | None = None,
    ) -> None:
        super().__init__(message)
        self.location = location
        self.issue_type = issue_type
        self.message = message
        self.expected = expected
        self.observed = observed
        self.mismatch_kind = mismatch_kind
        self.json_pointer = _json_pointer(location)


class _DuplicateJsonKey(ValueError):
    pass


_MISSING = object()
_ABSENT = object()
_PRESENT = object()


@dataclass(frozen=True)
class _TopologyMismatch:
    location: tuple[str, ...]
    kind: str
    expected: Any
    observed: Any
    cost: int = 1


def _json_pointer(location: tuple[str | int, ...]) -> str:
    if not location:
        return ""
    return "/" + "/".join(
        _safe_text(str(item), limit=96).replace("~", "~0").replace("/", "~1")
        for item in location
    )


def _safe_text(value: str, *, limit: int = 160) -> str:
    encoded = value.encode("utf-8", errors="backslashreplace")
    safe = encoded.decode("utf-8")
    return safe if len(safe) <= limit else safe[: max(0, limit - 3)] + "..."


def _diagnostic_value(value: Any) -> Any:
    if value is _MISSING:
        return "<missing>"
    if value is _ABSENT:
        return "<absent>"
    if value is _PRESENT:
        return "<present>"
    if value is None or type(value) in {bool, int}:
        return value
    if isinstance(value, float):
        return _safe_text(f"{value!r} (float)")
    if isinstance(value, str):
        return _safe_text(value)
    if isinstance(value, dict):
        return "<object>"
    if isinstance(value, list):
        return "<array>"
    return f"<{type(value).__name__}>"


def _diagnostic_text(value: Any) -> str:
    normalized = _diagnostic_value(value)
    return json.dumps(normalized, ensure_ascii=False, allow_nan=False)


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


def _mapping_mismatches(
    raw: Any,
    *,
    expected: dict[str, Any],
    permitted: frozenset[str] | None,
    required: frozenset[str],
    location: tuple[str, ...],
) -> list[_TopologyMismatch]:
    if not isinstance(raw, dict):
        return [
            _TopologyMismatch(
                location=location,
                kind="mismatched field",
                expected=f"{location[-1] if location else 'relation'} object",
                observed=raw,
                cost=max(1, len(required)),
            )
        ]

    mismatches: list[_TopologyMismatch] = []
    if permitted is not None:
        for key in sorted(set(raw) - permitted):
            mismatches.append(
                _TopologyMismatch(
                    location=location + (_safe_text(key, limit=96),),
                    kind="extra field",
                    expected=_ABSENT,
                    observed=_PRESENT,
                )
            )
    for key, expected_value in expected.items():
        if key not in raw:
            if key in required:
                mismatches.append(
                    _TopologyMismatch(
                        location=location + (key,),
                        kind="missing field",
                        expected=expected_value,
                        observed=_MISSING,
                    )
                )
            continue
        if not _strict_scalar_equal(raw[key], expected_value):
            mismatches.append(
                _TopologyMismatch(
                    location=location + (key,),
                    kind="mismatched field",
                    expected=expected_value,
                    observed=raw[key],
                )
            )
    return mismatches


def _relation_topology_mismatches(
    raw: dict[str, Any],
    *,
    template: CandidateHardRelationTemplateV1,
    source_ref: EntityVersionRef,
    target_ref: EntityVersionRef,
) -> tuple[_TopologyMismatch, ...]:
    """Describe the exact matcher-relevant differences without relaxing it."""

    ref_keys = frozenset({"entity_id", "version"})
    facet_keys = frozenset({"entity_id", "version", "facet"})
    facet_permitted = facet_keys | {"field_path"}
    source = {"entity_id": source_ref.entity_id, "version": source_ref.version}
    target = {"entity_id": target_ref.entity_id, "version": target_ref.version}
    comparisons = (
        (
            (),
            raw,
            {
                "relation_type": template.relation_type,
                "version": template.version,
                "supersedes": template.supersedes,
                "dependency_mode": template.dependency_mode,
            },
            None,
            frozenset({"relation_type", "version", "dependency_mode"}),
        ),
        (("source",), raw.get("source"), source, ref_keys, ref_keys),
        (("target",), raw.get("target"), target, ref_keys, ref_keys),
        (
            ("upstream",),
            raw.get("upstream"),
            source
            | {
                "facet": template.source.facet,
                "field_path": template.source.field_path,
            },
            facet_permitted | {"semantic_hash"},
            facet_keys,
        ),
        (
            ("downstream",),
            raw.get("downstream"),
            target
            | {
                "facet": template.target.facet,
                "field_path": template.target.field_path,
            },
            facet_permitted,
            facet_keys,
        ),
    )
    mismatches: list[_TopologyMismatch] = []
    for location, raw_value, expected, permitted, required in comparisons:
        mismatches.extend(
            _mapping_mismatches(
                raw_value,
                expected=expected,
                permitted=permitted,
                required=required,
                location=location,
            )
        )
    return tuple(mismatches)


def _nearest_relation_mismatch(
    relations: list[tuple[int, dict[str, Any]]],
    *,
    template: CandidateHardRelationTemplateV1,
    source_ref: EntityVersionRef,
    target_ref: EntityVersionRef,
) -> tuple[int, _TopologyMismatch] | None:
    candidates: list[tuple[int, tuple[_TopologyMismatch, ...]]] = []
    for operation_index, relation in relations:
        mismatches = _relation_topology_mismatches(
            relation,
            template=template,
            source_ref=source_ref,
            target_ref=target_ref,
        )
        if mismatches:
            candidates.append((operation_index, mismatches))
    if not candidates:
        return None
    ranked = [
        (
            (sum(mismatch.cost for mismatch in mismatches), len(mismatches)),
            operation_index,
            mismatches,
        )
        for operation_index, mismatches in candidates
    ]
    best_score = min(item[0] for item in ranked)
    best = [item for item in ranked if item[0] == best_score]
    if len(best) != 1 or len(best[0][2]) != 1:
        return None
    _, operation_index, mismatches = best[0]
    return operation_index, mismatches[0]


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
            if not matches:
                nearest = _nearest_relation_mismatch(
                    relations,
                    template=template,
                    source_ref=source_ref,
                    target_ref=target_ref,
                )
                if nearest is not None:
                    operation_index, mismatch = nearest
                    location = (
                        "operations",
                        operation_index,
                        "relation",
                        *mismatch.location,
                    )
                    expected = _diagnostic_value(mismatch.expected)
                    observed = _diagnostic_value(mismatch.observed)
                    pointer = _json_pointer(location)
                    raise CandidateDraftMaterializationError(
                        location=location,
                        issue_type="candidate_draft_template_missing",
                        message=(
                            f"runtime template {template.template_id!r} must match "
                            "exactly one relation topology; found 0. Closest "
                            f"relation differs at {pointer}: {mismatch.kind}; "
                            f"expected {_diagnostic_text(mismatch.expected)}, "
                            f"observed {_diagnostic_text(mismatch.observed)}"
                        ),
                        expected=expected,
                        observed=observed,
                        mismatch_kind=mismatch.kind,
                    )
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
