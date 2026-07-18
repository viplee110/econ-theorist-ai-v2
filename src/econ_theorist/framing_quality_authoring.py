"""Noncanonical semantic authoring compiler for a fresh registry-v8 framing audit.

The canonical framing payloads and validators remain the scientific owners.
This module removes mechanical candidate work: it binds exact route inputs,
resolves declared benchmark paths, wraps the two output entities, instantiates
the five engine-declared hard relations, and builds the route outcome.  It
never writes an ObjectStore, commits a Transaction, or records a human gate.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import Field, ValidationError, field_validator

from .candidate_contract import (
    CandidateAuthoringContractV1,
    CandidateHardRelationTemplateV1,
    CandidateRelationEndpointV1,
)
from .codec import canonical_json_bytes, ensure_canonical_data
from .framing_quality import (
    ENDOGENOUS_ACTIVE_SEMANTIC_LEVELS,
    FramingQualityBundle,
    pack_framing_quality_payload,
)
from .framing_quality_validation import (
    active_semantic_node_kinds,
    fixing_level_overlaps,
)
from .models import (
    CreateEntityOp,
    CreateRelationOp,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    NonEmptyString,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
    StableId,
    StrictModel,
    Transaction,
)
from .runtime.freshness import facet_semantic_hash
from .theory import (
    GateDossier,
    GateRequirement,
    PrimitiveGraph,
    pack_theory_payload,
    parse_theory_entity,
)


_FRAMING_ROUTE_ID = "audit.framing_economics"
_FRAMING_ROUTE_VERSION = 8
_FRAMING_EXIT_VALIDATOR_ID = "framing_quality_route_exit.v2"
_EXPECTED_TEMPLATE_IDS = (
    "framing.audits.research_question",
    "framing.audits.benchmark_set",
    "framing.audits.primitive_graph",
    "framing.audits.source_g1_dossier",
    "framing.governs.replacement_g1_dossier",
)
_INPUT_REF_FIELDS = {
    "ResearchQuestion": "research_question_ref",
    "BenchmarkSet": "benchmark_set_ref",
    "PrimitiveGraph": "primitive_graph_ref",
    "GateDossier": "source_g1_dossier_ref",
}
_MAX_PATH_ALTERNATIVES = 3


class BenchmarkChannelIntentV1(StrictModel):
    """Economist-facing endpoint objects plus only needed disambiguating nodes."""

    channel_intent_schema: Literal[
        "econ-theorist/framing-channel-intent/v1"
    ] = "econ-theorist/framing-channel-intent/v1"
    benchmark_id: StableId
    changed_object_id: StableId
    target_object_id: StableId
    ordered_waypoint_node_ids: tuple[StableId, ...] = ()

    @field_validator("ordered_waypoint_node_ids")
    @classmethod
    def _waypoints_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("channel intent waypoints must be unique")
        return value


class FramingAuditSemanticDraftV1(StrictModel):
    """Scientific content without canonical wrappers, relations, hashes, or IDs."""

    semantic_draft_schema: Literal[
        "econ-theorist/framing-audit-semantic-draft/v1"
    ] = "econ-theorist/framing-audit-semantic-draft/v1"
    bundle_payload: dict[str, Any]
    channel_intents: Annotated[
        tuple[BenchmarkChannelIntentV1, ...], Field(min_length=1)
    ]
    transaction_intent: NonEmptyString = (
        "Compile the declared economics-framing audit for canonical validation."
    )
    outcome_rationale: NonEmptyString = (
        "The semantic draft was mechanically compiled under the exact V8 contract."
    )
    bundle_title: NonEmptyString = "Economics framing preflight"
    bundle_summary: NonEmptyString = (
        "Benchmark semantics, economic forces, and disclosed attribution risks."
    )
    replacement_dossier_title: NonEmptyString = "Replacement G1 dossier"
    replacement_dossier_summary: NonEmptyString = (
        "The source G1 package strengthened by the framing audit."
    )

    @field_validator("bundle_payload", mode="before")
    @classmethod
    def _payload_is_canonical_json(cls, value: Any) -> dict[str, Any]:
        normalized = ensure_canonical_data(value)
        if not isinstance(normalized, dict):
            raise ValueError("bundle_payload must be one canonical JSON object")
        return normalized

    @field_validator("channel_intents")
    @classmethod
    def _benchmark_intents_are_unique(
        cls, value: tuple[BenchmarkChannelIntentV1, ...]
    ) -> tuple[BenchmarkChannelIntentV1, ...]:
        identifiers = tuple(item.benchmark_id for item in value)
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("channel intents must have unique benchmark IDs")
        return value


class FramingAuditPreflightIssueV1(StrictModel):
    """One bounded, location-specific compiler issue returned before a retry."""

    issue_schema: Literal[
        "econ-theorist/framing-audit-preflight-issue/v1"
    ] = "econ-theorist/framing-audit-preflight-issue/v1"
    rule_id: StableId
    location: tuple[str | int, ...]
    message: NonEmptyString
    benchmark_id: StableId | None = None
    object_id: StableId | None = None
    options: tuple[NonEmptyString, ...] = ()


class FramingAuditPreflightReportV1(StrictModel):
    """Deterministic aggregate preflight; no issue consumes a route repair."""

    preflight_schema: Literal[
        "econ-theorist/framing-audit-preflight/v1"
    ] = "econ-theorist/framing-audit-preflight/v1"
    passed: bool
    issues: tuple[FramingAuditPreflightIssueV1, ...] = ()
    active_semantic_node_ids: tuple[StableId, ...] = ()

    def model_post_init(self, __context: Any) -> None:
        if self.passed == bool(self.issues):
            raise ValueError("preflight passed must be the inverse of issue presence")


class FramingAuditCompilationError(ValueError):
    """Aggregate compiler failure with stable machine-readable issues."""

    def __init__(self, issues: tuple[FramingAuditPreflightIssueV1, ...]) -> None:
        if not issues:
            raise ValueError("FramingAuditCompilationError requires at least one issue")
        self.issues = issues
        codes = ", ".join(issue.rule_id for issue in issues)
        super().__init__(
            f"framing semantic preflight rejected {len(issues)} issue(s): {codes}"
        )


@dataclass(frozen=True)
class _PreparedDraft:
    payload: dict[str, Any]
    bundle: FramingQualityBundle | None
    inputs_by_type: Mapping[str, EntityVersion]
    graph: PrimitiveGraph | None
    report: FramingAuditPreflightReportV1


def _issue(
    rule_id: str,
    location: tuple[str | int, ...],
    message: str,
    *,
    benchmark_id: str | None = None,
    object_id: str | None = None,
    options: tuple[str, ...] = (),
) -> FramingAuditPreflightIssueV1:
    return FramingAuditPreflightIssueV1(
        rule_id=rule_id,
        location=location,
        message=message,
        benchmark_id=benchmark_id,
        object_id=object_id,
        options=options,
    )


def _deduplicate_issues(
    issues: list[FramingAuditPreflightIssueV1],
) -> tuple[FramingAuditPreflightIssueV1, ...]:
    unique: dict[
        tuple[str, tuple[str | int, ...], str | None, str | None],
        FramingAuditPreflightIssueV1,
    ] = {}
    for issue in issues:
        key = (
            issue.rule_id,
            issue.location,
            issue.benchmark_id,
            issue.object_id,
        )
        unique.setdefault(key, issue)
    return tuple(unique.values())


def _contract_inputs(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
) -> tuple[
    dict[str, EntityVersion],
    list[FramingAuditPreflightIssueV1],
]:
    issues: list[FramingAuditPreflightIssueV1] = []
    output = contract.output_contract
    if (
        output.route_id != _FRAMING_ROUTE_ID
        or output.route_version != _FRAMING_ROUTE_VERSION
        or output.exit_validator_id != _FRAMING_EXIT_VALIDATOR_ID
        or contract.packet_compiler_version != 2
        or contract.candidate_draft_semantics
        != "runtime_facet_hash_materialization_v1"
    ):
        issues.append(
            _issue(
                "compiler.contract.v8_required",
                ("contract", "output_contract"),
                "The semantic compiler accepts only the exact registry-v8 framing route.",
            )
        )
    if (
        snapshot.project_id != contract.transaction_bindings.project_id
        or snapshot.head != contract.transaction_bindings.base_revision
    ):
        issues.append(
            _issue(
                "compiler.contract.base_mismatch",
                ("contract", "transaction_bindings", "base_revision"),
                "The contract is not bound to this exact snapshot project and head.",
            )
        )

    templates = output.required_relation_templates
    if tuple(item.template_id for item in templates) != _EXPECTED_TEMPLATE_IDS:
        issues.append(
            _issue(
                "compiler.contract.relation_templates",
                ("contract", "output_contract", "required_relation_templates"),
                "The exact four audits and one governs templates are required in order.",
            )
        )
    exact_entities = {
        (entity.entity_id, entity.version): entity
        for entity in snapshot.entity_versions
    }
    for evidence_index, reference in enumerate(
        contract.transaction_bindings.required_entity_evidence_refs
    ):
        entity = exact_entities.get((reference.entity_id, reference.version))
        if entity is None:
            issues.append(
                _issue(
                    "compiler.contract.evidence_input_missing",
                    (
                        "contract",
                        "transaction_bindings",
                        "required_entity_evidence_refs",
                        evidence_index,
                    ),
                    "A required exact evidence input is absent from the base snapshot.",
                )
            )
        elif entity.entity_type == "FramingQualityBundle":
            issues.append(
                _issue(
                    "compiler.contract.continuation_unsupported",
                    (
                        "contract",
                        "transaction_bindings",
                        "required_entity_evidence_refs",
                        evidence_index,
                    ),
                    "This prototype compiles only a fresh V8 audit, not bundle continuation.",
                    options=(
                        "Use the existing canonical continuation authoring path.",
                        "Add exact supersession support before compiler integration.",
                    ),
                )
            )
    inputs_by_type: dict[str, EntityVersion] = {}
    for template_index, template in enumerate(templates):
        endpoint = template.source
        if endpoint.binding_kind != "exact_input":
            continue
        assert endpoint.entity_ref is not None
        entity = exact_entities.get(
            (endpoint.entity_ref.entity_id, endpoint.entity_ref.version)
        )
        location = (
            "contract",
            "output_contract",
            "required_relation_templates",
            template_index,
            "source",
        )
        if entity is None or entity.entity_type != endpoint.entity_type:
            issues.append(
                _issue(
                    "compiler.contract.exact_input_missing",
                    location,
                    "A relation template input is absent or has the wrong entity type.",
                )
            )
            continue
        if endpoint.entity_type in inputs_by_type:
            issues.append(
                _issue(
                    "compiler.contract.exact_input_duplicated",
                    location,
                    "Each framing input entity type must resolve exactly once.",
                )
            )
            continue
        inputs_by_type[endpoint.entity_type] = entity
    missing_types = sorted(set(_INPUT_REF_FIELDS).difference(inputs_by_type))
    if missing_types:
        issues.append(
            _issue(
                "compiler.contract.exact_inputs_incomplete",
                ("contract", "output_contract", "required_relation_templates"),
                "Missing exact input types: " + ", ".join(missing_types),
            )
        )
    return inputs_by_type, issues


def _bind_exact_inputs(
    payload: dict[str, Any],
    inputs_by_type: Mapping[str, EntityVersion],
) -> list[FramingAuditPreflightIssueV1]:
    issues: list[FramingAuditPreflightIssueV1] = []
    for entity_type, field_name in _INPUT_REF_FIELDS.items():
        entity = inputs_by_type.get(entity_type)
        if entity is None:
            continue
        expected = {
            "entity_id": entity.entity_id,
            "version": entity.version,
        }
        supplied = payload.get(field_name)
        if supplied is None:
            payload[field_name] = expected
        elif supplied != expected:
            issues.append(
                _issue(
                    "compiler.payload.exact_input_mismatch",
                    ("bundle_payload", field_name),
                    f"{field_name} differs from the engine-bound exact input.",
                    options=("Remove the field and let the compiler bind it.",),
                )
            )
    return issues


def _find_simple_paths(
    adjacency: Mapping[str, tuple[str, ...]],
    source: str,
    target: str,
) -> tuple[tuple[str, ...], ...]:
    if source == target:
        return ((source,),)
    found: list[tuple[str, ...]] = []
    stack: list[tuple[str, tuple[str, ...]]] = [(source, (source,))]
    while stack and len(found) < _MAX_PATH_ALTERNATIVES:
        node, path = stack.pop()
        for neighbor in reversed(adjacency.get(node, ())):
            if neighbor in path:
                continue
            candidate = (*path, neighbor)
            if neighbor == target:
                found.append(candidate)
                if len(found) >= _MAX_PATH_ALTERNATIVES:
                    break
            else:
                stack.append((neighbor, candidate))
    return tuple(found)


def _resolve_channel_path(
    graph: PrimitiveGraph,
    *,
    source_node_id: str,
    target_node_id: str,
    waypoints: tuple[str, ...],
    location: tuple[str | int, ...],
    benchmark_id: str,
) -> tuple[tuple[str, ...] | None, list[FramingAuditPreflightIssueV1]]:
    issues: list[FramingAuditPreflightIssueV1] = []
    node_ids = {node.node_id for node in graph.nodes}
    requested = (source_node_id, *waypoints, target_node_id)
    unknown = tuple(node_id for node_id in requested if node_id not in node_ids)
    if unknown:
        issues.append(
            _issue(
                "compiler.channel_path.unknown_node",
                location,
                "Channel intent references unknown PrimitiveGraph nodes: "
                + ", ".join(unknown),
                benchmark_id=benchmark_id,
            )
        )
        return None, issues
    if len(set(requested)) != len(requested):
        issues.append(
            _issue(
                "compiler.channel_path.repeated_node",
                location,
                "Channel endpoints and waypoints must describe a simple path.",
                benchmark_id=benchmark_id,
            )
        )
        return None, issues

    adjacency_sets: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for edge in graph.edges:
        adjacency_sets[edge.source_node_id].add(edge.target_node_id)
    adjacency = {
        node_id: tuple(sorted(neighbors))
        for node_id, neighbors in adjacency_sets.items()
    }
    resolved: list[str] = []
    for segment_index, (source, target) in enumerate(zip(requested, requested[1:])):
        alternatives = _find_simple_paths(adjacency, source, target)
        segment_location = (*location, "segment", segment_index)
        if not alternatives:
            issues.append(
                _issue(
                    "compiler.channel_path.unreachable",
                    segment_location,
                    f"No directed PrimitiveGraph path connects {source} to {target}.",
                    benchmark_id=benchmark_id,
                )
            )
            return None, issues
        if len(alternatives) > 1:
            issues.append(
                _issue(
                    "compiler.channel_path.ambiguous",
                    segment_location,
                    f"More than one directed path connects {source} to {target}.",
                    benchmark_id=benchmark_id,
                    options=tuple(" -> ".join(path) for path in alternatives),
                )
            )
            return None, issues
        segment = alternatives[0]
        resolved.extend(segment if not resolved else segment[1:])
    if len(set(resolved)) != len(resolved):
        issues.append(
            _issue(
                "compiler.channel_path.non_simple_resolution",
                location,
                "The uniquely resolved segments revisit a PrimitiveGraph node.",
                benchmark_id=benchmark_id,
            )
        )
        return None, issues
    return tuple(resolved), issues


def _mapping_list(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _object_binding(
    row: Mapping[str, Any], group: str, object_id: str
) -> Mapping[str, Any] | None:
    matches = [
        item
        for item in _mapping_list(row.get(group))
        if item.get("object_id") == object_id
    ]
    return matches[0] if len(matches) == 1 else None


def _apply_channel_intents(
    payload: dict[str, Any],
    graph: PrimitiveGraph,
    intents: tuple[BenchmarkChannelIntentV1, ...],
) -> list[FramingAuditPreflightIssueV1]:
    issues: list[FramingAuditPreflightIssueV1] = []
    rows = _mapping_list(payload.get("benchmark_assessments"))
    intent_by_id = {item.benchmark_id: item for item in intents}
    row_ids = {
        row.get("benchmark_id") for row in rows if isinstance(row.get("benchmark_id"), str)
    }
    for intent_index, intent in enumerate(intents):
        if intent.benchmark_id not in row_ids:
            issues.append(
                _issue(
                    "compiler.channel_intent.unknown_benchmark",
                    ("channel_intents", intent_index, "benchmark_id"),
                    "Channel intent does not match a benchmark assessment.",
                    benchmark_id=intent.benchmark_id,
                )
            )
    for row_index, row in enumerate(rows):
        benchmark_id = row.get("benchmark_id")
        if not isinstance(benchmark_id, str):
            continue
        intent = intent_by_id.get(benchmark_id)
        path_location = (
            "bundle_payload",
            "benchmark_assessments",
            row_index,
            "channel_path",
        )
        if "channel_path" in row:
            issues.append(
                _issue(
                    "compiler.channel_path.duplicate_source",
                    path_location,
                    "Semantic drafts must omit channel_path and let one channel intent compile it.",
                    benchmark_id=benchmark_id,
                    options=("Remove channel_path from bundle_payload.",),
                )
            )
            row.pop("channel_path")
        if intent is None:
            issues.append(
                _issue(
                    "compiler.channel_intent.missing",
                    path_location,
                    "Every benchmark assessment requires one channel intent.",
                    benchmark_id=benchmark_id,
                )
            )
            continue
        changed = _object_binding(row, "changed", intent.changed_object_id)
        target = _object_binding(row, "targets", intent.target_object_id)
        if changed is None:
            issues.append(
                _issue(
                    "compiler.channel_intent.changed_object",
                    path_location,
                    "changed_object_id must identify exactly one changed object.",
                    benchmark_id=benchmark_id,
                    object_id=intent.changed_object_id,
                )
            )
        if target is None:
            issues.append(
                _issue(
                    "compiler.channel_intent.target_object",
                    path_location,
                    "target_object_id must identify exactly one target object.",
                    benchmark_id=benchmark_id,
                    object_id=intent.target_object_id,
                )
            )
        if changed is None or target is None:
            continue
        source_node_id = changed.get("primitive_node_id")
        target_node_id = target.get("primitive_node_id")
        if not isinstance(source_node_id, str) or not isinstance(target_node_id, str):
            issues.append(
                _issue(
                    "compiler.channel_intent.unbound_endpoint",
                    path_location,
                    "Selected changed and target objects need exact primitive_node_id bindings.",
                    benchmark_id=benchmark_id,
                    options=(
                        "Bind the exact graph nodes.",
                        "Select different endpoint objects.",
                    ),
                )
            )
            continue
        path, path_issues = _resolve_channel_path(
            graph,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            waypoints=intent.ordered_waypoint_node_ids,
            location=path_location,
            benchmark_id=benchmark_id,
        )
        issues.extend(path_issues)
        if path is not None:
            row["channel_path"] = list(path)
    return issues


def _collect_semantic_ledger_issues(
    payload: Mapping[str, Any], graph: PrimitiveGraph
) -> tuple[list[FramingAuditPreflightIssueV1], tuple[str, ...]]:
    issues: list[FramingAuditPreflightIssueV1] = []
    node_kind = {node.node_id: node.kind for node in graph.nodes}
    direct_edges = {
        (edge.source_node_id, edge.target_node_id) for edge in graph.edges
    }
    active_nodes: set[str] = set()
    rows = _mapping_list(payload.get("benchmark_assessments"))
    for row_index, row in enumerate(rows):
        row_active_nodes: set[str] = set()
        benchmark_id = row.get("benchmark_id")
        stable_benchmark_id = benchmark_id if isinstance(benchmark_id, str) else None
        groups = {
            name: _mapping_list(row.get(name))
            for name in (
                "changed",
                "held_fixed",
                "reoptimizing",
                "still_endogenous",
                "targets",
            )
        }
        for group_name, objects in groups.items():
            for object_index, item in enumerate(objects):
                primitive_node_id = item.get("primitive_node_id")
                if primitive_node_id is None:
                    continue
                location = (
                    "bundle_payload",
                    "benchmark_assessments",
                    row_index,
                    group_name,
                    object_index,
                    "primitive_node_id",
                )
                if not isinstance(primitive_node_id, str) or primitive_node_id not in node_kind:
                    issues.append(
                        _issue(
                            "compiler.semantic_ledger.unknown_node",
                            location,
                            "Semantic ledger object references an unknown PrimitiveGraph node.",
                            benchmark_id=stable_benchmark_id,
                            object_id=(
                                item.get("object_id")
                                if isinstance(item.get("object_id"), str)
                                else None
                            ),
                        )
                    )

        for object_index, item in enumerate(groups["reoptimizing"]):
            primitive_node_id = item.get("primitive_node_id")
            object_id = item.get("object_id")
            if primitive_node_id is None:
                issues.append(
                    _issue(
                        "compiler.semantic_ledger.reoptimizing_binding_missing",
                        (
                            "bundle_payload",
                            "benchmark_assessments",
                            row_index,
                            "reoptimizing",
                            object_index,
                            "primitive_node_id",
                        ),
                        "A reoptimizing object requires an exact PrimitiveGraph choice binding.",
                        benchmark_id=stable_benchmark_id,
                        object_id=object_id if isinstance(object_id, str) else None,
                        options=(
                            "Bind the exact choice node.",
                            "Move a non-choice object out of reoptimizing.",
                        ),
                    )
                )
                continue
            if not isinstance(primitive_node_id, str) or primitive_node_id not in node_kind:
                continue
            if node_kind[primitive_node_id] != "choice":
                issues.append(
                    _issue(
                        "compiler.semantic_ledger.reoptimizing_node_kind",
                        (
                            "bundle_payload",
                            "benchmark_assessments",
                            row_index,
                            "reoptimizing",
                            object_index,
                            "primitive_node_id",
                        ),
                        "A reoptimizing object must bind an exact choice node.",
                        benchmark_id=stable_benchmark_id,
                        object_id=object_id if isinstance(object_id, str) else None,
                        options=(
                            "Bind the exact choice node.",
                            "Move a non-choice object out of reoptimizing.",
                        ),
                    )
                )
            else:
                active_nodes.add(primitive_node_id)
                row_active_nodes.add(primitive_node_id)

        for object_index, item in enumerate(groups["still_endogenous"]):
            semantic_level = item.get("semantic_level")
            primitive_node_id = item.get("primitive_node_id")
            object_id = item.get("object_id")
            allowed_kinds = (
                active_semantic_node_kinds(semantic_level)
                if isinstance(semantic_level, str)
                else None
            )
            # payoff_ledger and other non-active accounting levels deliberately
            # remain outside active-margin classification.
            if allowed_kinds is None:
                continue
            if primitive_node_id is None:
                issues.append(
                    _issue(
                        "compiler.semantic_ledger.endogenous_binding_missing",
                        (
                            "bundle_payload",
                            "benchmark_assessments",
                            row_index,
                            "still_endogenous",
                            object_index,
                            "primitive_node_id",
                        ),
                        "An active endogenous object requires an exact type-compatible graph binding.",
                        benchmark_id=stable_benchmark_id,
                        object_id=object_id if isinstance(object_id, str) else None,
                        options=(
                            "Bind an exact type-compatible PrimitiveGraph node.",
                            "Use a non-active accounting level only for a genuinely diagnostic row.",
                        ),
                    )
                )
                continue
            if not isinstance(primitive_node_id, str) or primitive_node_id not in node_kind:
                continue
            actual_kind = node_kind[primitive_node_id]
            if actual_kind not in allowed_kinds:
                compatible_levels = tuple(
                    sorted(
                        level
                        for level in ENDOGENOUS_ACTIVE_SEMANTIC_LEVELS
                        if actual_kind in (active_semantic_node_kinds(level) or ())
                    )
                )
                issues.append(
                    _issue(
                        "compiler.semantic_ledger.endogenous_node_kind",
                        (
                            "bundle_payload",
                            "benchmark_assessments",
                            row_index,
                            "still_endogenous",
                            object_index,
                            "semantic_level",
                        ),
                        "The declared endogenous semantic level is incompatible "
                        f"with PrimitiveGraph node kind {actual_kind}.",
                        benchmark_id=stable_benchmark_id,
                        object_id=object_id if isinstance(object_id, str) else None,
                        options=(
                            *(
                                f"Use {level} only if that is the honest economic role."
                                for level in compatible_levels
                            ),
                            "Bind a different type-compatible PrimitiveGraph node.",
                            "Use a non-active accounting level only for a genuinely diagnostic row.",
                        ),
                    )
                )
            else:
                active_nodes.add(primitive_node_id)
                row_active_nodes.add(primitive_node_id)

        movable_groups = (
            ("changed", groups["changed"]),
            ("reoptimizing", groups["reoptimizing"]),
            ("still_endogenous", groups["still_endogenous"]),
        )
        for held_index, held in enumerate(groups["held_fixed"]):
            held_node_id = held.get("primitive_node_id")
            fixing_level = held.get("fixing_level")
            overlaps = (
                fixing_level_overlaps(fixing_level)
                if isinstance(fixing_level, str)
                else frozenset()
            )
            if not isinstance(held_node_id, str):
                continue
            for movable_group, movable in movable_groups:
                for movable_index, item in enumerate(movable):
                    if (
                        item.get("primitive_node_id") != held_node_id
                        or item.get("semantic_level") not in overlaps
                    ):
                        continue
                    object_id = item.get("object_id")
                    issues.append(
                        _issue(
                            "compiler.semantic_ledger.fixed_movable_conflict",
                            (
                                "bundle_payload",
                                "benchmark_assessments",
                                row_index,
                                movable_group,
                                movable_index,
                                "primitive_node_id",
                            ),
                            "One graph node is held fixed and movable at overlapping semantic levels.",
                            benchmark_id=stable_benchmark_id,
                            object_id=object_id if isinstance(object_id, str) else None,
                            options=(
                                "Keep the node in only its honest fixed or movable role.",
                                "Split genuinely distinct semantic objects in the upstream PrimitiveGraph.",
                            ),
                        )
                    )

        path = row.get("channel_path")
        if not isinstance(path, list) or not all(isinstance(item, str) for item in path):
            continue
        if any((source, target) not in direct_edges for source, target in zip(path, path[1:])):
            issues.append(
                _issue(
                    "compiler.channel_path.not_exact",
                    (
                        "bundle_payload",
                        "benchmark_assessments",
                        row_index,
                        "channel_path",
                    ),
                    "channel_path contains a pair that is not a directed PrimitiveGraph edge.",
                    benchmark_id=stable_benchmark_id,
                )
            )
        changed_nodes = {
            item.get("primitive_node_id")
            for item in groups["changed"]
            if isinstance(item.get("primitive_node_id"), str)
        }
        target_nodes = {
            item.get("primitive_node_id")
            for item in groups["targets"]
            if isinstance(item.get("primitive_node_id"), str)
        }
        if len(path) >= 2 and (path[0] not in changed_nodes or path[-1] not in target_nodes):
            issues.append(
                _issue(
                    "compiler.channel_path.endpoint_mismatch",
                    (
                        "bundle_payload",
                        "benchmark_assessments",
                        row_index,
                        "channel_path",
                    ),
                    "Channel endpoints must be exact changed and target object bindings.",
                    benchmark_id=stable_benchmark_id,
                )
            )
        if (
            row.get("channel_kind") == "active_response"
            and len(path) >= 2
            and not set(path[1:-1]).intersection(row_active_nodes)
        ):
            issues.append(
                _issue(
                    "compiler.semantic_ledger.active_margin_missing",
                    (
                        "bundle_payload",
                        "benchmark_assessments",
                        row_index,
                        "channel_kind",
                    ),
                    "An active-response path needs an interior compatible response margin.",
                    benchmark_id=stable_benchmark_id,
                    options=(
                        "Bind the exact active response margin.",
                        "Downgrade the row if it is only diagnostic or a boundary comparison.",
                    ),
                )
            )
    return issues, tuple(sorted(active_nodes))


def _schema_issues(error: ValidationError) -> list[FramingAuditPreflightIssueV1]:
    return [
        _issue(
            "compiler.payload.schema",
            ("bundle_payload", *tuple(item["loc"])),
            str(item["msg"]),
        )
        for item in error.errors(include_url=False)
    ]


def _prepare_semantic_draft(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV1,
) -> _PreparedDraft:
    inputs_by_type, issues = _contract_inputs(snapshot, contract)
    payload = deepcopy(draft.bundle_payload)
    issues.extend(_bind_exact_inputs(payload, inputs_by_type))

    graph: PrimitiveGraph | None = None
    graph_entity = inputs_by_type.get("PrimitiveGraph")
    if graph_entity is not None:
        parsed_graph = parse_theory_entity(graph_entity)
        if isinstance(parsed_graph, PrimitiveGraph):
            graph = parsed_graph
        else:
            issues.append(
                _issue(
                    "compiler.contract.primitive_graph_payload",
                    ("contract", "inputs", "PrimitiveGraph"),
                    "The exact PrimitiveGraph input has the wrong typed payload.",
                )
            )

    active_nodes: tuple[str, ...] = ()
    if graph is not None:
        issues.extend(_apply_channel_intents(payload, graph, draft.channel_intents))
        ledger_issues, active_nodes = _collect_semantic_ledger_issues(payload, graph)
        issues.extend(ledger_issues)

    bundle: FramingQualityBundle | None = None
    try:
        bundle = FramingQualityBundle.model_validate_json(
            canonical_json_bytes(payload), strict=True
        )
    except ValidationError as error:
        issues.extend(_schema_issues(error))

    exact_issues = _deduplicate_issues(issues)
    report = FramingAuditPreflightReportV1(
        passed=not exact_issues,
        issues=exact_issues,
        active_semantic_node_ids=active_nodes,
    )
    return _PreparedDraft(
        payload=payload,
        bundle=bundle,
        inputs_by_type=inputs_by_type,
        graph=graph,
        report=report,
    )


def preflight_framing_audit_semantic_draft(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV1,
) -> FramingAuditPreflightReportV1:
    """Batch the compiler-owned channel and semantic-ledger issues without writes."""

    return _prepare_semantic_draft(snapshot, contract, draft).report


def _entity_ref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def _resolve_endpoint(
    endpoint: CandidateRelationEndpointV1,
    *,
    inputs_by_type: Mapping[str, EntityVersion],
    candidate_outputs: Mapping[str, tuple[EntityVersion, ...]],
) -> EntityVersion:
    if endpoint.binding_kind == "exact_input":
        entity = inputs_by_type[endpoint.entity_type]
        assert endpoint.entity_ref == _entity_ref(entity)
        return entity
    assert endpoint.output_ordinal is not None
    return candidate_outputs[endpoint.entity_type][endpoint.output_ordinal - 1]


def _compile_relation(
    template: CandidateHardRelationTemplateV1,
    *,
    relation_id: str,
    inputs_by_type: Mapping[str, EntityVersion],
    candidate_outputs: Mapping[str, tuple[EntityVersion, ...]],
    contract: CandidateAuthoringContractV1,
) -> RelationVersion:
    source = _resolve_endpoint(
        template.source,
        inputs_by_type=inputs_by_type,
        candidate_outputs=candidate_outputs,
    )
    target = _resolve_endpoint(
        template.target,
        inputs_by_type=inputs_by_type,
        candidate_outputs=candidate_outputs,
    )
    semantic_hash = template.upstream_semantic_hash
    if template.upstream_semantic_hash_binding == "runtime_facet_semantic_hash_v1":
        semantic_hash = facet_semantic_hash(source, template.source.facet)
    assert semantic_hash is not None
    bindings = contract.transaction_bindings
    return RelationVersion(
        relation_id=relation_id,
        relation_type=template.relation_type,
        version=1,
        project_id=bindings.project_id,
        source=_entity_ref(source),
        target=_entity_ref(target),
        dependency_mode="hard",
        upstream=SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet=template.source.facet,
            semantic_hash=semantic_hash,
        ),
        downstream=FacetPathRef(
            entity_id=target.entity_id,
            version=target.version,
            facet=template.target.facet,
        ),
        privacy=bindings.privacy,
        access_compartments=bindings.access_compartments,
        created_at=bindings.created_at,
    )


def compile_framing_audit_semantic_draft(
    snapshot: Snapshot,
    contract: CandidateAuthoringContractV1,
    draft: FramingAuditSemanticDraftV1,
) -> Transaction:
    """Compile one fresh-audit semantic draft without accepting the Transaction.

    The returned object must still pass the unchanged registry-v8 canonical
    candidate validator.  Calling this function is pure and does not consume a
    model repair, create a run record, stage bytes, or update the canonical head.
    """

    prepared = _prepare_semantic_draft(snapshot, contract, draft)
    if not prepared.report.passed:
        raise FramingAuditCompilationError(prepared.report.issues)
    assert prepared.bundle is not None
    bundle_payload = prepared.bundle
    bindings = contract.transaction_bindings
    run_id = bindings.route_run_id
    transaction_id = f"transaction.{run_id}.framing.audit"
    bundle_id = f"framing.quality.{run_id}"
    dossier_id = f"dossier.g1.framing.{run_id}"
    relation_ids = tuple(
        f"relation.{run_id}.framing.{index}"
        for index in range(1, len(_EXPECTED_TEMPLATE_IDS) + 1)
    )
    historical_entity_ids = {entity.entity_id for entity in snapshot.entity_versions}
    historical_relation_ids = {
        relation.relation_id for relation in snapshot.relation_versions
    }
    collisions = tuple(
        object_id
        for object_id in (bundle_id, dossier_id)
        if object_id in historical_entity_ids
    )
    relation_collisions = tuple(
        relation_id
        for relation_id in relation_ids
        if relation_id in historical_relation_ids
    )
    if transaction_id in snapshot.transaction_ids or collisions or relation_collisions:
        collision_issues: list[FramingAuditPreflightIssueV1] = []
        if transaction_id in snapshot.transaction_ids:
            collision_issues.append(
                _issue(
                    "compiler.generated_id.transaction_collision",
                    ("generated_ids", "transaction_id"),
                    f"Generated transaction ID already exists: {transaction_id}.",
                )
            )
        for object_id in collisions:
            collision_issues.append(
                _issue(
                    "compiler.generated_id.entity_collision",
                    ("generated_ids", "entity_id"),
                    f"Generated entity ID already exists: {object_id}.",
                )
            )
        for relation_id in relation_collisions:
            collision_issues.append(
                _issue(
                    "compiler.generated_id.relation_collision",
                    ("generated_ids", "relation_id"),
                    f"Generated relation ID already exists: {relation_id}.",
                )
            )
        raise FramingAuditCompilationError(tuple(collision_issues))

    bundle_entity = EntityVersion(
        entity_id=bundle_id,
        entity_type="FramingQualityBundle",
        version=1,
        project_id=bindings.project_id,
        title=draft.bundle_title,
        summary=draft.bundle_summary,
        status=ScientificStatus(
            formal_validity="not_applicable",
            interpretation_validity="unassessed",
        ),
        facets=pack_framing_quality_payload(bundle_payload),
        privacy=bindings.privacy,
        access_compartments=bindings.access_compartments,
        created_at=bindings.created_at,
    )
    source_dossier_entity = prepared.inputs_by_type["GateDossier"]
    source_dossier = parse_theory_entity(source_dossier_entity)
    assert isinstance(source_dossier, GateDossier)
    bundle_ref = _entity_ref(bundle_entity)
    replacement_payload = GateDossier(
        gate_kind="G1_question_benchmark",
        research_question_ref=bundle_payload.research_question_ref,
        ordered_object_refs=(*source_dossier.ordered_object_refs, bundle_ref),
        ordered_artifact_refs=source_dossier.ordered_artifact_refs,
        requirements=(
            *source_dossier.requirements,
            GateRequirement(
                requirement_id="g1.framing_quality",
                description="Economics framing and attribution pass preflight.",
                evidence_refs=(bundle_ref,),
                recorded_condition=(
                    "evidence_supplied"
                    if bundle_payload.proposed_action == "ready_for_g1"
                    else "risk_disclosed"
                ),
            ),
        ),
        proposed_action=(
            "approve"
            if bundle_payload.proposed_action == "ready_for_g1"
            else "revise"
        ),
        rationale="The source package is strengthened by the framing audit.",
        prepared_at=bindings.created_at,
    )
    dossier_entity = EntityVersion(
        entity_id=dossier_id,
        entity_type="GateDossier",
        version=1,
        project_id=bindings.project_id,
        title=draft.replacement_dossier_title,
        summary=draft.replacement_dossier_summary,
        status=ScientificStatus(
            formal_validity="not_applicable",
            interpretation_validity="unassessed",
        ),
        facets=pack_theory_payload(replacement_payload),
        privacy=bindings.privacy,
        access_compartments=bindings.access_compartments,
        created_at=bindings.created_at,
    )
    candidate_outputs = {
        "FramingQualityBundle": (bundle_entity,),
        "GateDossier": (dossier_entity,),
    }
    relations = tuple(
        _compile_relation(
            template,
            relation_id=relation_id,
            inputs_by_type=prepared.inputs_by_type,
            candidate_outputs=candidate_outputs,
            contract=contract,
        )
        for template, relation_id in zip(
            contract.output_contract.required_relation_templates,
            relation_ids,
        )
    )
    candidate_refs = (
        _entity_ref(bundle_entity),
        _entity_ref(dossier_entity),
        *(
            RelationVersionRef(
                relation_id=relation.relation_id,
                version=relation.version,
            )
            for relation in relations
        ),
    )
    return Transaction(
        transaction_id=transaction_id,
        transaction_schema=bindings.transaction_schema,
        origin=bindings.origin,
        project_id=bindings.project_id,
        base_revision=bindings.base_revision,
        route_run_id=bindings.route_run_id,
        route_id=bindings.route_id,
        route_run_hash=bindings.route_run_hash,
        context_manifest_hash=bindings.context_manifest_hash,
        compiled_context_hash=bindings.compiled_context_hash,
        actor=bindings.actor,
        intent=draft.transaction_intent,
        operations=(
            CreateEntityOp(entity=bundle_entity),
            CreateEntityOp(entity=dossier_entity),
            *(CreateRelationOp(relation=relation) for relation in relations),
            RecordRouteOutcomeOp(
                outcome=RouteOutcome(
                    route_run_id=bindings.route_run_id,
                    route_id=bindings.route_id,
                    outcome="completed_with_candidate",
                    rationale=draft.outcome_rationale,
                    candidate_refs=candidate_refs,
                    privacy=bindings.privacy,
                    access_compartments=bindings.access_compartments,
                )
            ),
        ),
        evidence_refs=bindings.required_entity_evidence_refs,
        privacy=bindings.privacy,
        access_compartments=bindings.access_compartments,
        created_at=bindings.created_at,
        parent_transaction_hash=bindings.parent_transaction_hash,
    )


__all__ = [
    "BenchmarkChannelIntentV1",
    "FramingAuditCompilationError",
    "FramingAuditPreflightIssueV1",
    "FramingAuditPreflightReportV1",
    "FramingAuditSemanticDraftV1",
    "compile_framing_audit_semantic_draft",
    "preflight_framing_audit_semantic_draft",
]
