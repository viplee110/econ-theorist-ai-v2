"""Canonical validation for the additive v5 economics-framing preflight.

The validator deliberately checks a narrow scientific contract.  It verifies
that benchmark comparisons have an active economic channel, that aggregate
claims do not smuggle in changing weights, and that equilibrium selection is
described at its actual level of assurance.  It does not decide whether the
question is important or confirm G1; those remain human judgments.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from typing import Annotated, Any, Literal

from pydantic import Field, ValidationError

from . import framing_quality as fq
from . import theory as t
from .models import (
    Actor,
    BlockerRef,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    EntityVersion,
    EntityVersionRef,
    RecordBlockerOp,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteSpecV5,
    Snapshot,
    StableId,
    StrictModel,
    SupersedeEntityOp,
    Transaction,
)
from .authoring_validation import facet_semantic_hash, facet_semantic_value
from .codec import canonical_json_bytes, object_digest
from .theory_validation import (
    TheoryValidationError,
    validate_phase2_route_entry,
    validate_phase2_route_transaction,
    validate_theory_entity,
)


FRAMING_ROUTE_ID = "audit.framing_economics"
FRAMING_ENTRY_VALIDATOR_ID = "framing_quality_route_entry.v1"
FRAMING_EXIT_VALIDATOR_ID = "framing_quality_route_exit.v1"
FRAMING_NEGATIVE_EXIT_VALIDATOR_ID = "framing_quality_route_exit.v2"
FRAMING_REPAIR_ROUTE_ID = "repair.dependency"
FRAMING_REPAIR_ENTRY_VALIDATOR_ID = "framing_repair_route_entry.v1"
FRAMING_REPAIR_EXIT_VALIDATOR_ID = "framing_repair_route_exit.v1"
FRAMING_REQUIREMENT_ID = "g1.framing_quality"
FRAMING_ROUTE_VERSIONS = frozenset((6, 7, 8))
_MAX_ENTITY_PREFLIGHT_ISSUES = 50


_BoundedDiagnosticText = Annotated[str, Field(min_length=1, max_length=512)]
_DiagnosticLocation = Annotated[
    tuple[str | int, ...], Field(min_length=1, max_length=32)
]
_EntityPreflightCategory = Literal[
    "envelope",
    "payload_schema",
    "wrapper_binding",
    "semantic_ledger",
    "scientific_validator",
]
class FramingQualityEntityPreflightIssueV1(StrictModel):
    """One bounded structural diagnostic for a bundle envelope or payload."""

    issue_schema: Literal[
        "econ-theorist/framing-quality-entity-preflight-issue/v1"
    ] = "econ-theorist/framing-quality-entity-preflight-issue/v1"
    rule_id: StableId
    category: _EntityPreflightCategory
    location: _DiagnosticLocation
    json_pointer: _BoundedDiagnosticText
    message: _BoundedDiagnosticText
    expected: _BoundedDiagnosticText | None = None
    observed: _BoundedDiagnosticText | None = None


class FramingQualityEntityPreflightReportV1(StrictModel):
    """Deterministic typed-payload diagnostics for noncanonical authoring."""

    diagnostic_schema: Literal[
        "econ-theorist/framing-quality-entity-preflight/v1"
    ] = "econ-theorist/framing-quality-entity-preflight/v1"
    validation_stage: Literal["noncanonical_authoring_preflight"] = (
        "noncanonical_authoring_preflight"
    )
    rule_id: Literal["framing.entity_preflight"] = "framing.entity_preflight"
    repairable: Literal[True] = True
    retry_action: Literal["edit_declared_candidate_and_retry_same_request"] = (
        "edit_declared_candidate_and_retry_same_request"
    )
    repair_hint: _BoundedDiagnosticText = (
        "Correct the exact envelope or payload fields listed below, then retry "
        "the same declared candidate."
    )
    passed: bool
    issue_count: int = Field(ge=0, le=100000)
    truncated: bool
    issues: Annotated[
        tuple[FramingQualityEntityPreflightIssueV1, ...], Field(max_length=50)
    ] = ()

    def model_post_init(self, __context: Any) -> None:
        if self.passed != (self.issue_count == 0):
            raise ValueError("entity preflight passed must match issue_count")
        if self.issue_count < len(self.issues):
            raise ValueError("entity preflight cannot report more issues than exist")
        if self.truncated != (self.issue_count > len(self.issues)):
            raise ValueError("entity preflight truncation flag is inconsistent")


class FramingQualityValidationError(ValueError):
    """A framing-quality object or route transaction is inadmissible."""

    def __init__(
        self,
        message: str,
        *,
        diagnostic_details: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.diagnostic_details = dict(diagnostic_details or {})


class FramingQualityRouteEntryReport(StrictModel):
    route_id: Literal["audit.framing_economics"] = "audit.framing_economics"
    research_question_ref: EntityVersionRef
    benchmark_set_ref: EntityVersionRef
    primitive_graph_ref: EntityVersionRef
    source_g1_dossier_ref: EntityVersionRef
    prior_bundle_ref: EntityVersionRef | None = None
    input_entity_refs: tuple[EntityVersionRef, ...]
    actor: Actor


class FramingQualityProjectionReport(StrictModel):
    bundle_refs: tuple[EntityVersionRef, ...]


class FramingRepairRouteEntryReport(StrictModel):
    route_id: Literal["repair.dependency"] = "repair.dependency"
    repair_mode: Literal["stale_root", "framing_revision"]
    target_ref: EntityVersionRef
    trigger_bundle_ref: EntityVersionRef | None = None
    input_entity_refs: tuple[EntityVersionRef, ...]
    actor: Actor


def _entity_key(value: EntityVersion | EntityVersionRef) -> tuple[str, int]:
    return value.entity_id, value.version


def _entity_ref(value: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=value.entity_id, version=value.version)


def _relation_ref(value: RelationVersion) -> RelationVersionRef:
    return RelationVersionRef(relation_id=value.relation_id, version=value.version)


def _json_pointer(location: tuple[str | int, ...]) -> str:
    """Render a bounded RFC-6901-style pointer without candidate values."""

    return "/" + "/".join(
        str(item).replace("~", "~0").replace("/", "~1") for item in location
    )


def _bounded_diagnostic_text(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value[:512] or "<empty>"
    if isinstance(value, dict):
        return "JSON object"
    if isinstance(value, (tuple, list)):
        return "JSON array"
    return type(value).__name__[:512]


_MISSING = object()


def _value_at_location(value: object, location: tuple[object, ...]) -> object:
    current = value
    for item in location:
        if isinstance(current, Mapping) and isinstance(item, str):
            current = current.get(item, _MISSING)
        elif isinstance(current, (tuple, list)) and isinstance(item, int):
            current = current[item] if 0 <= item < len(current) else _MISSING
        else:
            return _MISSING
        if current is _MISSING:
            return _MISSING
    return current


def _payload_expected_value(error: Mapping[str, object]) -> str | None:
    context = error.get("ctx")
    if isinstance(context, Mapping):
        expected = context.get("expected")
        if isinstance(expected, str) and expected:
            return _bounded_diagnostic_text(expected)
    error_type = error.get("type")
    if isinstance(error_type, str) and error_type:
        return error_type
    return None


_MECHANICAL_PAYLOAD_VALIDATOR_MESSAGES = frozenset(
    {
        (
            "public_state_condition: equals/not_equals require one value and "
            "qualitative relations must omit it"
        ),
        "choice_consequence_binding: focal and alternative consequences must differ",
        "active_margin_witness: focal and alternative actions must differ",
        "causal_chain must contain ordered steps 1, 2, and 3",
        "causal_chain references an unknown economic force",
        "disclosed gap references an unknown benchmark",
        "framing repair target must name its exact typed bundle input",
        (
            "fixed_endogenous_conflict: an object cannot be both held fixed and "
            "changed, reoptimizing, or still endogenous"
        ),
    }
)
_MECHANICAL_PAYLOAD_UNIQUE_MESSAGES = frozenset(
    {
        "choice-consequence edge IDs must be unique",
        "choice-consequence public-state node IDs must be unique",
        "active-margin payoff node IDs must be unique",
        "causal-step force IDs must be unique",
        "distinctive mechanism node IDs must be unique",
        "distinctive mechanism edge IDs must be unique",
        "distinctive mechanism public-state node IDs must be unique",
        "changed objects must be unique",
        "held-fixed objects must be unique",
        "reoptimizing objects must be unique",
        "still-endogenous objects must be unique",
        "target objects must be unique",
        "channel-path node IDs must be unique",
        "gap benchmark IDs must be unique",
        "gap repair targets must be unique",
        "framing-quality exact input refs must be unique",
        "economic force IDs must be unique",
        "benchmark assessment IDs must be unique",
        "disclosed framing gap IDs must be unique",
    }
)


def _payload_validation_kind(
    error: Mapping[str, object],
) -> tuple[str, _EntityPreflightCategory]:
    """Classify only known mechanical validators; unknown checks stay scientific.

    Pydantic locations identify where a validator happened to run, not whether
    its predicate is a mechanical payload error or a V8 scientific gate.  Keep
    the classification closed: new or unknown value errors cannot silently be
    counted as structural tax.
    """

    if error.get("type") != "value_error":
        return "framing.payload.schema", "payload_schema"
    message = str(error.get("msg") or "")
    if message.startswith("Value error, "):
        message = message.removeprefix("Value error, ")
    if (
        message in _MECHANICAL_PAYLOAD_VALIDATOR_MESSAGES
        or message in _MECHANICAL_PAYLOAD_UNIQUE_MESSAGES
    ):
        return "framing.payload.semantic_ledger", "semantic_ledger"
    return "framing.payload.scientific_validator", "scientific_validator"


def _entity_preflight_issue(
    *,
    rule_id: str,
    category: _EntityPreflightCategory,
    location: tuple[str | int, ...],
    message: str,
    expected: object | None = None,
    observed: object | None = None,
) -> FramingQualityEntityPreflightIssueV1:
    return FramingQualityEntityPreflightIssueV1(
        rule_id=rule_id,
        category=category,
        location=location,
        json_pointer=_json_pointer(location),
        message=_bounded_diagnostic_text(message),
        expected=(
            _bounded_diagnostic_text(expected) if expected is not None else None
        ),
        observed=(
            _bounded_diagnostic_text(observed) if observed is not None else None
        ),
    )


def diagnose_framing_quality_entity(
    entity: EntityVersion,
    *,
    location_prefix: tuple[str | int, ...] = (),
) -> FramingQualityEntityPreflightReportV1:
    """Aggregate typed bundle-envelope and payload errors without route writes.

    The ordinary parser stops at its first malformed envelope field.  Candidate
    authors instead need every independent envelope and payload issue in one
    bounded receipt, including a schema mismatch that otherwise hides payload
    validation.  This helper is diagnostic only: it does not relax or replace
    the canonical parser or route validator.
    """

    issues: list[FramingQualityEntityPreflightIssueV1] = []
    prefix = tuple(location_prefix)
    if entity.entity_type != "FramingQualityBundle":
        issues.append(
            _entity_preflight_issue(
                rule_id="framing.entity_type",
                category="wrapper_binding",
                location=(*prefix, "entity_type"),
                message="The typed payload preflight accepts FramingQualityBundle only.",
                expected="FramingQualityBundle",
                observed=entity.entity_type,
            )
        )
    owner = fq.FRAMING_QUALITY_PAYLOAD_OWNER_FACETS.get(entity.entity_type)
    model = fq.FRAMING_QUALITY_PAYLOAD_MODELS.get(entity.entity_type)
    if owner is None or model is None:
        reported = tuple(issues[:_MAX_ENTITY_PREFLIGHT_ISSUES])
        return FramingQualityEntityPreflightReportV1(
            passed=False,
            issue_count=len(issues),
            truncated=len(reported) < len(issues),
            issues=reported,
        )

    facets = entity.facets.model_dump(mode="python")
    for facet_name in sorted(facets):
        if facet_name == owner or facets[facet_name] == {}:
            continue
        issues.append(
            _entity_preflight_issue(
                rule_id="framing.envelope.owner_facet",
                category="envelope",
                location=(*prefix, "facets", facet_name),
                message=(
                    "A framing-quality payload must leave every non-owner facet "
                    "empty."
                ),
                expected="empty JSON object",
                observed=facets[facet_name],
            )
        )

    wrapper = facets.get(owner)
    wrapper_location = (*prefix, "facets", owner)
    if not isinstance(wrapper, Mapping):
        issues.append(
            _entity_preflight_issue(
                rule_id="framing.envelope.wrapper_type",
                category="envelope",
                location=wrapper_location,
                message="The framing-quality owner facet must be a JSON object.",
                expected="JSON object",
                observed=wrapper,
            )
        )
    else:
        required_keys = {"schema", "payload"}
        actual_keys = set(wrapper)
        if actual_keys != required_keys:
            issues.append(
                _entity_preflight_issue(
                    rule_id="framing.envelope.wrapper_keys",
                    category="envelope",
                    location=wrapper_location,
                    message=(
                        "The framing-quality owner facet must contain exactly "
                        "schema and payload."
                    ),
                    expected="payload, schema",
                    observed=", ".join(sorted(str(key) for key in actual_keys))
                    or "<none>",
                )
            )
        expected_schema = fq.framing_quality_schema_id(entity.entity_type)
        observed_schema = wrapper.get("schema", _MISSING)
        if observed_schema != expected_schema:
            issues.append(
                _entity_preflight_issue(
                    rule_id="framing.envelope.schema_id",
                    category="envelope",
                    location=(*wrapper_location, "schema"),
                    message=(
                        "The framing-quality owner facet has the wrong exact "
                        "schema identifier."
                    ),
                    expected=expected_schema,
                    observed=(
                        "<missing>" if observed_schema is _MISSING else observed_schema
                    ),
                )
            )
        payload_data = wrapper.get("payload", _MISSING)
        if not isinstance(payload_data, dict):
            issues.append(
                _entity_preflight_issue(
                    rule_id="framing.envelope.payload_type",
                    category="envelope",
                    location=(*wrapper_location, "payload"),
                    message="The framing-quality payload must be one JSON object.",
                    expected="JSON object",
                    observed=(
                        "<missing>" if payload_data is _MISSING else payload_data
                    ),
                )
            )
        else:
            try:
                model.model_validate_json(
                    canonical_json_bytes(payload_data), strict=True
                )
            except ValidationError as error:
                for item in error.errors(include_url=False):
                    raw_location = tuple(item["loc"])
                    location = (*wrapper_location, "payload", *raw_location)
                    observed = _value_at_location(payload_data, raw_location)
                    rule_id, category = _payload_validation_kind(item)
                    issues.append(
                        _entity_preflight_issue(
                            rule_id=rule_id,
                            category=category,
                            location=location,
                            message=str(item["msg"]),
                            expected=_payload_expected_value(item),
                            observed=(
                                "<missing>" if observed is _MISSING else observed
                            ),
                        )
                    )

    reported = tuple(issues[:_MAX_ENTITY_PREFLIGHT_ISSUES])
    return FramingQualityEntityPreflightReportV1(
        passed=not issues,
        issue_count=len(issues),
        truncated=len(reported) < len(issues),
        issues=reported,
    )


def _owner_facet(entity_type: str) -> str | None:
    return (
        fq.FRAMING_QUALITY_PAYLOAD_OWNER_FACETS.get(entity_type)
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


def _current_entities(snapshot: Snapshot) -> dict[str, EntityVersion]:
    return {
        item.entity_id: item
        for item in snapshot.entity_versions
        if snapshot.current_entities.get(item.entity_id) == item.version
    }


def _exact_entities(snapshot: Snapshot) -> dict[tuple[str, int], EntityVersion]:
    return {_entity_key(item): item for item in snapshot.entity_versions}


def _one_by_type(
    entities: Sequence[EntityVersion], entity_type: str
) -> EntityVersion:
    selected = [item for item in entities if item.entity_type == entity_type]
    if len(selected) != 1:
        raise FramingQualityValidationError(
            f"framing route requires exactly one {entity_type}, got {len(selected)}"
        )
    return selected[0]


def _parse_theory(entity: EntityVersion, expected: type[t.TheoryPayload]) -> t.TheoryPayload:
    try:
        payload = validate_theory_entity(entity)
    except TheoryValidationError as exc:
        raise FramingQualityValidationError(str(exc)) from exc
    if not isinstance(payload, expected):
        raise FramingQualityValidationError(
            f"{entity.entity_id}@{entity.version} is not {expected.__name__}"
        )
    return payload


def validate_framing_quality_entity(
    entity: EntityVersion, previous: EntityVersion | None = None
) -> fq.FramingQualityBundle:
    """Parse a bundle and, when supplied, its same-scope continuation."""

    if entity.entity_type != "FramingQualityBundle":
        raise FramingQualityValidationError(
            f"unregistered framing-quality entity_type: {entity.entity_type}"
        )
    if previous is None:
        if entity.version != 1 or entity.supersedes is not None:
            raise FramingQualityValidationError(
                "a new FramingQualityBundle must begin at version 1"
            )
    elif (
        previous.entity_type != entity.entity_type
        or previous.entity_id != entity.entity_id
        or previous.project_id != entity.project_id
        or entity.version != previous.version + 1
        or entity.supersedes != _entity_ref(previous)
    ):
        raise FramingQualityValidationError(
            "FramingQualityBundle continuation must supersede its exact prior version"
        )
    if not fq.is_packed_framing_quality_entity(entity):
        raise FramingQualityValidationError(
            "FramingQualityBundle is not a canonical framing-quality envelope"
        )
    try:
        payload = fq.parse_framing_quality_entity(entity)
    except (TypeError, ValueError) as exc:
        raise FramingQualityValidationError(
            f"invalid FramingQualityBundle {entity.entity_id}@{entity.version}: {exc}"
        ) from exc
    if not isinstance(payload, fq.FramingQualityBundle):
        raise FramingQualityValidationError("framing-quality payload has the wrong model")
    if previous is not None:
        prior_payload = fq.parse_framing_quality_entity(previous)
        assert isinstance(prior_payload, fq.FramingQualityBundle)
        if prior_payload.proposed_action != "continue_diagnostic":
            raise FramingQualityValidationError(
                "only continue_diagnostic permits same-scope bundle continuation"
            )
        prior_scope = (
            prior_payload.research_question_ref,
            prior_payload.benchmark_set_ref,
            prior_payload.primitive_graph_ref,
            prior_payload.source_g1_dossier_ref,
        )
        current_scope = (
            payload.research_question_ref,
            payload.benchmark_set_ref,
            payload.primitive_graph_ref,
            payload.source_g1_dossier_ref,
        )
        if current_scope != prior_scope:
            raise FramingQualityValidationError(
                "a continued FramingQualityBundle cannot change its exact upstream scope"
            )
    return payload


def _approved_g1_exists(snapshot: Snapshot, research_question_id: str) -> bool:
    decisions = {
        (item.decision_id, item.version): item for item in snapshot.decisions
    }
    for reference in snapshot.effective_decisions.values():
        decision = decisions.get((reference.decision_id, reference.version))
        if (
            decision is not None
            and decision.decision_kind == "G1_question_benchmark"
            and decision.status == "confirmed"
            and decision.decider.kind == "human"
            and decision.machine_outcome == "approve"
            and decision.selected_option == "approve"
            and decision.scope_ref == research_question_id
        ):
            return True
    return False


def _validate_entry_refs(
    snapshot: Snapshot,
    route_spec: RouteSpecV5,
    references: tuple[EntityVersionRef, ...],
    *,
    actor: Actor,
) -> FramingQualityRouteEntryReport:
    if (
        route_spec.route_id != FRAMING_ROUTE_ID
        or route_spec.route_version not in FRAMING_ROUTE_VERSIONS
        or route_spec.availability != "enabled"
        or route_spec.entry_validator_id != FRAMING_ENTRY_VALIDATOR_ID
    ):
        raise FramingQualityValidationError("unknown or malformed framing route")
    if len({_entity_key(item) for item in references}) != len(references):
        raise FramingQualityValidationError("framing route input repeats an exact ref")

    exact = _exact_entities(snapshot)
    entities: list[EntityVersion] = []
    for reference in references:
        entity = exact.get(_entity_key(reference))
        if entity is None:
            raise FramingQualityValidationError("framing route input is unresolved")
        if not _is_current_and_fresh(snapshot, entity):
            raise FramingQualityValidationError(
                "framing route input is not current and fresh"
            )
        entities.append(entity)

    core_types = {
        "ResearchQuestion",
        "BenchmarkSet",
        "PrimitiveGraph",
        "GateDossier",
    }
    entity_types = {item.entity_type for item in entities}
    if (
        len(entities) not in {4, 5}
        or not core_types.issubset(entity_types)
        or entity_types.difference({*core_types, "FramingQualityBundle"})
        or len([item for item in entities if item.entity_type == "FramingQualityBundle"])
        > 1
    ):
        raise FramingQualityValidationError(
            "framing route requires one exact ResearchQuestion, BenchmarkSet, "
            "PrimitiveGraph, and G1 GateDossier, plus at most one current bundle"
        )

    rq_entity = _one_by_type(entities, "ResearchQuestion")
    benchmark_entity = _one_by_type(entities, "BenchmarkSet")
    graph_entity = _one_by_type(entities, "PrimitiveGraph")
    dossier_entity = _one_by_type(entities, "GateDossier")
    supplied_bundle_entity = next(
        (item for item in entities if item.entity_type == "FramingQualityBundle"),
        None,
    )
    rq = _parse_theory(rq_entity, t.ResearchQuestion)
    benchmarks = _parse_theory(benchmark_entity, t.BenchmarkSet)
    graph = _parse_theory(graph_entity, t.PrimitiveGraph)
    dossier = _parse_theory(dossier_entity, t.GateDossier)
    assert isinstance(rq, t.ResearchQuestion)
    assert isinstance(benchmarks, t.BenchmarkSet)
    assert isinstance(graph, t.PrimitiveGraph)
    assert isinstance(dossier, t.GateDossier)

    rq_ref = _entity_ref(rq_entity)
    benchmark_ref = _entity_ref(benchmark_entity)
    graph_ref = _entity_ref(graph_entity)
    dossier_ref = _entity_ref(dossier_entity)
    if benchmarks.question_ref != rq_ref:
        raise FramingQualityValidationError("BenchmarkSet crosses research questions")
    if graph.question_ref != rq_ref or graph.benchmark_set_ref != benchmark_ref:
        raise FramingQualityValidationError("PrimitiveGraph crosses framing lineages")
    if (
        dossier.gate_kind != "G1_question_benchmark"
        or dossier.research_question_ref != rq_ref
        or not {rq_ref, benchmark_ref, graph_ref}.issubset(
            set(dossier.ordered_object_refs)
        )
    ):
        raise FramingQualityValidationError(
            "source GateDossier is not the exact G1 package for these inputs"
        )
    if any(
        exact.get(_entity_key(reference), None) is not None
        and exact[_entity_key(reference)].entity_type == "FramingQualityBundle"
        for reference in dossier.ordered_object_refs
    ):
        raise FramingQualityValidationError(
            "the supplied G1 dossier is already a post-audit replacement"
        )
    if _approved_g1_exists(snapshot, rq_entity.entity_id):
        raise FramingQualityValidationError(
            "framing audit must run before an effective human G1 approval"
        )

    current_bundle_refs: list[EntityVersionRef] = []
    for entity in snapshot.entity_versions:
        if (
            entity.entity_type == "FramingQualityBundle"
            and snapshot.current_entities.get(entity.entity_id) == entity.version
        ):
            previous = (
                exact.get((entity.entity_id, entity.version - 1))
                if entity.version > 1
                else None
            )
            bundle = validate_framing_quality_entity(entity, previous)
            if (
                bundle.research_question_ref == rq_ref
                and bundle.benchmark_set_ref == benchmark_ref
                and bundle.primitive_graph_ref == graph_ref
                and bundle.source_g1_dossier_ref == dossier_ref
            ):
                current_bundle_refs.append(_entity_ref(entity))
    if len(current_bundle_refs) > 1:
        raise FramingQualityValidationError(
            "this exact framing lineage has multiple current audit bundles"
        )
    supplied_bundle_ref = (
        _entity_ref(supplied_bundle_entity)
        if supplied_bundle_entity is not None
        else None
    )
    current_bundle_ref = current_bundle_refs[0] if current_bundle_refs else None
    if supplied_bundle_ref != current_bundle_ref:
        raise FramingQualityValidationError(
            "framing continuation must include its exact current bundle predecessor"
        )
    if supplied_bundle_entity is not None:
        previous_bundle = (
            exact.get(
                (supplied_bundle_entity.entity_id, supplied_bundle_entity.version - 1)
            )
            if supplied_bundle_entity.version > 1
            else None
        )
        supplied_bundle = validate_framing_quality_entity(
            supplied_bundle_entity, previous_bundle
        )
        if supplied_bundle.proposed_action != "continue_diagnostic":
            raise FramingQualityValidationError(
                "only continue_diagnostic may continue the same exact framing scope"
            )

    return FramingQualityRouteEntryReport(
        research_question_ref=rq_ref,
        benchmark_set_ref=benchmark_ref,
        primitive_graph_ref=graph_ref,
        source_g1_dossier_ref=dossier_ref,
        prior_bundle_ref=current_bundle_ref,
        input_entity_refs=references,
        actor=actor,
    )


def validate_framing_quality_route_entry(
    snapshot: Snapshot,
    route_spec: RouteSpecV5,
    focus_entity_ids: Iterable[str],
    *,
    actor: Actor,
) -> FramingQualityRouteEntryReport:
    focus = tuple(focus_entity_ids)
    if len(set(focus)) != len(focus):
        raise FramingQualityValidationError("framing route focus IDs must be unique")
    current = _current_entities(snapshot)
    missing = sorted(set(focus).difference(current))
    if missing:
        raise FramingQualityValidationError(
            "framing route focus contains unknown current entities: "
            + ", ".join(missing)
        )
    return _validate_entry_refs(
        snapshot,
        route_spec,
        tuple(_entity_ref(current[entity_id]) for entity_id in focus),
        actor=actor,
    )


def _phase2_repair_spec(route_spec: RouteSpecV5) -> RouteSpecV5:
    return route_spec.model_copy(
        update={
            "entry_validator_id": "theory_route_entry.v1",
            "exit_validator_id": "theory_route_exit.v1",
        }
    )


def _validate_framing_repair_entry_refs(
    snapshot: Snapshot,
    route_spec: RouteSpecV5,
    references: tuple[EntityVersionRef, ...],
    *,
    actor: Actor,
) -> FramingRepairRouteEntryReport:
    if (
        route_spec.route_id != FRAMING_REPAIR_ROUTE_ID
        or route_spec.route_version != 5
        or route_spec.availability != "enabled"
        or route_spec.entry_validator_id != FRAMING_REPAIR_ENTRY_VALIDATOR_ID
    ):
        raise FramingQualityValidationError("unknown or malformed v5 repair route")
    if len({_entity_key(item) for item in references}) != len(references):
        raise FramingQualityValidationError("v5 repair input repeats an exact ref")

    exact = _exact_entities(snapshot)
    entities: list[EntityVersion] = []
    for reference in references:
        entity = exact.get(_entity_key(reference))
        if entity is None or snapshot.current_entities.get(entity.entity_id) != entity.version:
            raise FramingQualityValidationError(
                "v5 repair input must name exact current entities"
            )
        entities.append(entity)

    normalized = _phase2_repair_spec(route_spec)
    if len(entities) == 1:
        target = entities[0]
        try:
            validate_phase2_route_entry(
                snapshot,
                normalized,
                (target.entity_id,),
                actor=actor,
            )
        except TheoryValidationError as exc:
            raise FramingQualityValidationError(str(exc)) from exc
        return FramingRepairRouteEntryReport(
            repair_mode="stale_root",
            target_ref=_entity_ref(target),
            input_entity_refs=references,
            actor=actor,
        )

    if len(entities) != 2:
        raise FramingQualityValidationError(
            "v5 repair requires one stale root or one target plus its revise_framing bundle"
        )
    bundle_entities = [
        item for item in entities if item.entity_type == "FramingQualityBundle"
    ]
    targets = [
        item
        for item in entities
        if item.entity_type in {"ResearchQuestion", "BenchmarkSet", "PrimitiveGraph"}
    ]
    if len(bundle_entities) != 1 or len(targets) != 1:
        raise FramingQualityValidationError(
            "proactive framing repair requires one bundle and one typed framing target"
        )
    bundle_entity = bundle_entities[0]
    target = targets[0]
    if not _is_current_and_fresh(snapshot, bundle_entity) or not _is_current_and_fresh(
        snapshot, target
    ):
        raise FramingQualityValidationError(
            "proactive framing repair requires a current fresh bundle and target"
        )
    previous_bundle = (
        exact.get((bundle_entity.entity_id, bundle_entity.version - 1))
        if bundle_entity.version > 1
        else None
    )
    bundle = validate_framing_quality_entity(bundle_entity, previous_bundle)
    if bundle.proposed_action != "revise_framing":
        raise FramingQualityValidationError(
            "proactive framing repair requires proposed_action revise_framing"
        )
    for reference in (
        bundle.research_question_ref,
        bundle.benchmark_set_ref,
        bundle.primitive_graph_ref,
        bundle.source_g1_dossier_ref,
    ):
        scoped = exact.get(_entity_key(reference))
        if scoped is None or not _is_current_and_fresh(snapshot, scoped):
            raise FramingQualityValidationError(
                "proactive framing repair requires the bundle's exact scope to remain current and fresh"
            )
    target_ref = _entity_ref(target)
    named_targets = {
        (item.entity_type, item.entity_ref)
        for gap in bundle.disclosed_gaps
        for item in gap.repair_target_refs
    }
    if (target.entity_type, target_ref) not in named_targets:
        raise FramingQualityValidationError(
            "proactive framing repair target is not named by a disclosed gap"
        )
    try:
        validate_phase2_route_entry(
            snapshot,
            normalized,
            (target.entity_id,),
            actor=actor,
            allow_fresh_repair=True,
        )
    except TheoryValidationError as exc:
        raise FramingQualityValidationError(str(exc)) from exc
    return FramingRepairRouteEntryReport(
        repair_mode="framing_revision",
        target_ref=target_ref,
        trigger_bundle_ref=_entity_ref(bundle_entity),
        input_entity_refs=references,
        actor=actor,
    )


def validate_framing_repair_route_entry(
    snapshot: Snapshot,
    route_spec: RouteSpecV5,
    focus_entity_ids: Iterable[str],
    *,
    actor: Actor,
) -> FramingRepairRouteEntryReport:
    focus = tuple(focus_entity_ids)
    if len(set(focus)) != len(focus):
        raise FramingQualityValidationError("v5 repair focus IDs must be unique")
    current = _current_entities(snapshot)
    missing = sorted(set(focus).difference(current))
    if missing:
        raise FramingQualityValidationError(
            "v5 repair focus contains unknown current entities: "
            + ", ".join(missing)
        )
    return _validate_framing_repair_entry_refs(
        snapshot,
        route_spec,
        tuple(_entity_ref(current[entity_id]) for entity_id in focus),
        actor=actor,
    )


def _reachable(
    adjacency: Mapping[str, frozenset[str]], source: str, target: str
) -> bool:
    if source == target:
        return True
    pending: deque[str] = deque((source,))
    visited = {source}
    while pending:
        node = pending.popleft()
        for neighbor in adjacency.get(node, frozenset()):
            if neighbor == target:
                return True
            if neighbor not in visited:
                visited.add(neighbor)
                pending.append(neighbor)
    return False


_ACTIVE_SEMANTIC_NODE_KINDS: Mapping[str, frozenset[str]] = {
    "choice": frozenset(("choice",)),
    "behavioral_response": frozenset(("choice",)),
    "conditional_distribution": frozenset(("equilibrium_object",)),
    "transition_kernel": frozenset(("equilibrium_object",)),
    "stationary_distribution": frozenset(("equilibrium_object",)),
    "equilibrium_object": frozenset(("equilibrium_object",)),
    "equilibrium_correspondence": frozenset(("equilibrium_object",)),
}


_FIXING_LEVEL_OVERLAPS: Mapping[str, frozenset[str]] = {
    "primitive": frozenset(("primitive",)),
    "choice": frozenset(("choice", "behavioral_response")),
    "realized_behavior": frozenset(("choice", "behavioral_response")),
    "conditional_distribution": frozenset(("conditional_distribution",)),
    "transition_kernel": frozenset(("transition_kernel",)),
    "stationary_distribution": frozenset(("stationary_distribution",)),
    "weighting_distribution": frozenset(
        ("stationary_distribution", "aggregate")
    ),
    "payoff_ledger": frozenset(("payoff_ledger",)),
    "equilibrium_object": frozenset(("equilibrium_object",)),
    "equilibrium_correspondence": frozenset(("equilibrium_correspondence",)),
    "aggregate": frozenset(("aggregate",)),
}


def active_semantic_node_kinds(semantic_level: str) -> frozenset[str] | None:
    """Expose the canonical V8 node-kind lookup to mechanical authoring tools."""

    return _ACTIVE_SEMANTIC_NODE_KINDS.get(semantic_level)


def fixing_level_overlaps(fixing_level: str) -> frozenset[str]:
    """Expose the canonical fixed/movable overlap lookup without duplicating it."""

    return _FIXING_LEVEL_OVERLAPS.get(fixing_level, frozenset())


_MAX_STRUCTURED_DIAGNOSTIC_ISSUES = 20


def _step_is_on_force_path(
    adjacency: Mapping[str, frozenset[str]],
    force: fq.EconomicForce,
    step: fq.CausalChainStep,
) -> bool:
    """Return whether one cited step is ordered on source--margin--target."""

    if not _reachable(adjacency, force.source_node_id, step.source_node_id):
        return False
    if not _reachable(adjacency, step.target_node_id, force.target_node_id):
        return False
    return (
        _reachable(adjacency, step.target_node_id, force.margin_node_id)
        or (
            _reachable(adjacency, step.source_node_id, force.margin_node_id)
            and _reachable(adjacency, force.margin_node_id, step.target_node_id)
        )
        or _reachable(adjacency, force.margin_node_id, step.source_node_id)
    )


_PUBLIC_STATE_NODE_KINDS = frozenset(
    {
        "constraint",
        "equilibrium_object",
        "information",
        "institution",
        "interaction",
        "timing",
    }
)


def _state_condition_key(
    condition: fq.PublicStateCondition,
) -> tuple[str, str, str | None]:
    return condition.node_id, condition.relation, condition.value


def _node_kind_diagnostic(
    node_id: str,
    node: t.PrimitiveNode | None,
) -> str:
    return f"{node_id}({node.kind if node is not None else 'missing'})"


def _validate_choice_consequence_binding(
    *,
    step: fq.CausalChainStep,
    witness: fq.ActiveMarginWitness,
    node_by_id: Mapping[str, t.PrimitiveNode],
    edge_by_id: Mapping[str, t.PrimitiveEdge],
    adjacency: Mapping[str, frozenset[str]],
) -> None:
    binding = witness.consequence_binding
    if binding is None:
        return
    edges = tuple(edge_by_id.get(edge_id) for edge_id in binding.causal_edge_ids)
    if any(edge is None for edge in edges):
        raise FramingQualityValidationError(
            "choice_consequence_binding: causal edge references an unknown "
            "PrimitiveGraph edge"
        )
    exact_edges = tuple(edge for edge in edges if edge is not None)
    if (
        exact_edges[0].source_node_id != witness.decision_node_id
        or exact_edges[-1].target_node_id != binding.consequence_node_id
        or any(
            left.target_node_id != right.source_node_id
            for left, right in zip(exact_edges, exact_edges[1:])
        )
    ):
        raise FramingQualityValidationError(
            "choice_consequence_binding: edges must form one exact ordered path "
            "from the witnessed decision to the claimed consequence"
        )
    if not (
        _reachable(adjacency, step.target_node_id, binding.consequence_node_id)
        or _reachable(adjacency, binding.consequence_node_id, step.target_node_id)
    ):
        raise FramingQualityValidationError(
            "choice_consequence_binding: the claimed consequence is not on the "
            "witnessed causal spine"
        )
    invalid_conditions = tuple(
        (condition.node_id, node_by_id.get(condition.node_id))
        for condition in binding.public_state_conditions
        if (
            node_by_id.get(condition.node_id) is None
            or node_by_id[condition.node_id].kind not in _PUBLIC_STATE_NODE_KINDS
        )
    )
    if invalid_conditions:
        invalid = ", ".join(
            _node_kind_diagnostic(node_id, node)
            for node_id, node in invalid_conditions
        )
        raise FramingQualityValidationError(
            "choice_consequence_binding: every public-state condition must bind "
            "an exact state, information, institution, or transition node; "
            f"invalid conditions: {invalid}"
        )


def _validate_distinctive_mechanism(
    *,
    assessment: fq.BenchmarkFramingAssessment,
    assessments_by_id: Mapping[str, fq.BenchmarkFramingAssessment],
    node_by_id: Mapping[str, t.PrimitiveNode],
    edge_by_id: Mapping[str, t.PrimitiveEdge],
    witnessed_steps: tuple[
        tuple[fq.CausalChainStep, fq.ActiveMarginWitness], ...
    ],
) -> None:
    claim = assessment.distinctive_mechanism
    if claim is None or claim.claim_kind in {"not_claimed", "unresolved"}:
        return
    contrast_id = claim.contrast_benchmark_id
    assert contrast_id is not None
    contrast = assessments_by_id.get(contrast_id)
    if contrast is None or contrast is assessment:
        raise FramingQualityValidationError(
            "distinctive_mechanism: the contrast must be a different audited "
            "benchmark"
        )
    focal_path = assessment.channel_path
    contrast_path = contrast.channel_path
    if focal_path == contrast_path:
        raise FramingQualityValidationError(
            "distinctive_mechanism_same_spine: focal and contrast benchmarks cannot "
            "reuse the same path for a claimed distinctive mechanism"
        )
    focal_positions = {node_id: index for index, node_id in enumerate(focal_path)}
    focal_pairs = set(zip(focal_path, focal_path[1:]))
    contrast_pairs = set(zip(contrast_path, contrast_path[1:]))
    if any(node_id not in focal_positions for node_id in claim.distinctive_node_ids):
        raise FramingQualityValidationError(
            "distinctive_mechanism_spine: every distinctive node must appear on the "
            "focal benchmark path"
        )
    distinctive_edges = tuple(
        edge_by_id.get(edge_id) for edge_id in claim.distinctive_edge_ids
    )
    if any(edge is None for edge in distinctive_edges):
        raise FramingQualityValidationError(
            "distinctive_mechanism_spine: a distinctive transition edge is unknown"
        )
    exact_edges = tuple(edge for edge in distinctive_edges if edge is not None)
    if any(
        (edge.source_node_id, edge.target_node_id) not in focal_pairs
        for edge in exact_edges
    ):
        raise FramingQualityValidationError(
            "distinctive_mechanism_spine: every distinctive edge must be an exact "
            "neighbor transition on the focal benchmark path"
        )
    consequence_id = claim.consequence_node_id
    assert consequence_id is not None
    if consequence_id not in focal_positions:
        raise FramingQualityValidationError(
            "distinctive_mechanism_spine: the claimed consequence must appear on "
            "the focal benchmark path"
        )
    last_spine_position = max(
        *(focal_positions[node_id] for node_id in claim.distinctive_node_ids),
        *(
            focal_positions[edge.target_node_id]
            for edge in exact_edges
        ),
    )
    if focal_positions[consequence_id] < last_spine_position:
        raise FramingQualityValidationError(
            "distinctive_mechanism_spine: the claimed consequence cannot precede "
            "the distinctive node or transition spine"
        )
    if any(
        (node := node_by_id.get(condition.node_id)) is None
        or node.kind not in _PUBLIC_STATE_NODE_KINDS
        for condition in claim.required_public_state_conditions
    ):
        raise FramingQualityValidationError(
            "distinctive_mechanism_state: every required public-state condition "
            "must bind an exact known state, information, institution, or transition "
            "node; the condition need not be forced into the linear channel path"
        )
    distinct_from_contrast = any(
        node_id not in contrast_path for node_id in claim.distinctive_node_ids
    ) or any(
        (edge.source_node_id, edge.target_node_id) not in contrast_pairs
        for edge in exact_edges
    )
    if not distinct_from_contrast:
        raise FramingQualityValidationError(
            "distinctive_mechanism_same_spine: the declared distinctive nodes and "
            "transitions are also present on the contrast path"
        )

    if claim.claim_kind == "mechanical_transition":
        mechanical_nodes = {
            *claim.distinctive_node_ids,
            *(edge.source_node_id for edge in exact_edges),
            *(edge.target_node_id for edge in exact_edges),
        }
        if any(node_by_id[node_id].kind == "choice" for node_id in mechanical_nodes):
            raise FramingQualityValidationError(
                "distinctive_mechanism_mechanical_choice: a mechanical transition "
                "cannot conceal a choice node in its distinctive spine"
            )
        return

    assert claim.claim_kind == "choice_mediated"
    required_conditions = {
        _state_condition_key(item)
        for item in claim.required_public_state_conditions
    }
    required_edges = set(claim.distinctive_edge_ids)
    matching_witness = False
    for _, witness in witnessed_steps:
        binding = witness.consequence_binding
        if binding is None or witness.activity_status != "active":
            continue
        if (
            binding.consequence_node_id != consequence_id
            or binding.transition_kind != claim.transition_kind
            or not required_edges.issubset(binding.causal_edge_ids)
            or required_conditions
            != {_state_condition_key(item) for item in binding.public_state_conditions}
            or witness.decision_node_id not in focal_positions
            or focal_positions[witness.decision_node_id]
            > focal_positions[consequence_id]
        ):
            continue
        matching_witness = True
        break
    if not matching_witness:
        raise FramingQualityValidationError(
            "choice_consequence_binding_mismatch: a choice-mediated distinctive "
            "mechanism requires one active payoff witness bound to its exact "
            "consequence, transition, and public-state class"
        )


def _is_permitted_unwitnessed_negative_revision(
    bundle: fq.FramingQualityBundle,
) -> bool:
    """Return the exact V8 exception predicate without accepting a candidate.

    The noncanonical V2 compiler reuses this narrow predicate solely to know
    whether omitted margin intents can be an honest fully-downgraded diagnosis.
    Route acceptance remains owned by ``_validate_bundle_science``.
    """

    return (
        bundle.tension.tension_kind in fq.MECHANISM_MARGIN_TENSION_KINDS
        and any(
            gap.category in {"causal_attribution", "reoptimization"}
            and gap.repair_target_refs
            for gap in bundle.disclosed_gaps
        )
        and all(
            assessment.channel_kind != "active_response"
            and assessment.attribution_strength in {"weak", "unresolved"}
            and not assessment.aggregate_invariance.claims_aggregate_fixed
            and assessment.selection_assurance.status
            in {"selector_only", "not_applicable", "unresolved"}
            and assessment.distinctive_mechanism is not None
            and assessment.distinctive_mechanism.claim_kind
            in {"not_claimed", "unresolved"}
            for assessment in bundle.benchmark_assessments
        )
        and bundle.distinctive_mechanism_contribution_status
        in {"not_claimed", "unresolved"}
    )


def _validate_bundle_science(
    bundle: fq.FramingQualityBundle,
    *,
    rq: t.ResearchQuestion,
    benchmarks: t.BenchmarkSet,
    graph: t.PrimitiveGraph,
    require_research_first_bindings: bool = False,
    allow_unwitnessed_negative_revision: bool = False,
) -> None:
    if bundle.tension.result_archetype not in rq.candidate_archetypes:
        raise FramingQualityValidationError(
            "framing tension uses an archetype outside the ResearchQuestion"
        )
    expected_benchmarks = {item.benchmark_id for item in benchmarks.benchmarks}
    actual_benchmarks = {
        item.benchmark_id for item in bundle.benchmark_assessments
    }
    if actual_benchmarks != expected_benchmarks:
        raise FramingQualityValidationError(
            "FramingQualityBundle must audit every benchmark exactly once"
        )

    node_by_id = {item.node_id: item for item in graph.nodes}
    edge_by_id = {item.edge_id: item for item in graph.edges}
    node_ids = set(node_by_id)
    direct_edges = {(item.source_node_id, item.target_node_id) for item in graph.edges}
    adjacency: dict[str, set[str]] = {node_id: set() for node_id in node_ids}
    for source, target in direct_edges:
        adjacency[source].add(target)
    frozen_adjacency = {
        node_id: frozenset(targets) for node_id, targets in adjacency.items()
    }

    force_by_id = {item.force_id: item for item in bundle.forces}
    for force in bundle.forces:
        force_nodes = {
            force.source_node_id,
            force.margin_node_id,
            force.target_node_id,
        }
        if not force_nodes.issubset(node_ids):
            raise FramingQualityValidationError(
                "economic force references a node outside PrimitiveGraph"
            )
        if not _reachable(frozen_adjacency, force.source_node_id, force.margin_node_id):
            raise FramingQualityValidationError(
                "economic force has no path from source to operative margin"
            )
        if not _reachable(frozen_adjacency, force.margin_node_id, force.target_node_id):
            raise FramingQualityValidationError(
                "economic force has no path from operative margin to target"
            )
        if force.source_node_id == force.target_node_id:
            raise FramingQualityValidationError(
                "causal_force_binding: an economic force must have a nonzero "
                "source-to-target path"
            )

    steps = bundle.causal_chain
    used_force_ids: set[str] = set()
    witnessed_choice_nodes: set[str] = set()
    witnessed_steps: list[tuple[fq.CausalChainStep, fq.ActiveMarginWitness]] = []
    mechanism_margin_audit = (
        bundle.tension.tension_kind in fq.MECHANISM_MARGIN_TENSION_KINDS
    )
    negative_revision_requested = (
        allow_unwitnessed_negative_revision
        and bundle.proposed_action == "revise_framing"
        and all(step.active_margin_witness is None for step in steps)
    )
    negative_revision = (
        negative_revision_requested
        and _is_permitted_unwitnessed_negative_revision(bundle)
    )
    if negative_revision_requested and not negative_revision:
        raise FramingQualityValidationError(
            "unwitnessed_negative_revision_invalid: v8 permits an absent payoff "
            "witness only for a fully downgraded revise_framing diagnosis with "
            "an exact causal-attribution or reoptimization repair target"
        )
    primitive_path_issues: list[dict[str, object]] = []
    for step_index, step in enumerate(steps):
        if {step.source_node_id, step.target_node_id}.difference(node_ids):
            raise FramingQualityValidationError(
                "causal chain references a node outside PrimitiveGraph"
            )
        if not _reachable(frozen_adjacency, step.source_node_id, step.target_node_id):
            raise FramingQualityValidationError(
                "causal chain step is not reachable in PrimitiveGraph"
            )
        if step.source_node_id == step.target_node_id:
            raise FramingQualityValidationError(
                "causal_force_binding: every causal-chain step must be nonzero"
            )
        choice_nodes_on_step = {
            node_id
            for node_id, node in node_by_id.items()
            if node.kind == "choice"
            and _reachable(frozen_adjacency, step.source_node_id, node_id)
            and _reachable(frozen_adjacency, node_id, step.target_node_id)
        }
        # A choice already realized at the source can support a downstream
        # mechanical consequence without repeating the same payoff comparison.
        # Supplied witnesses may still bind that source choice, and the global
        # force-margin check below still requires every operative choice to be
        # witnessed somewhere in the chain.
        newly_reached_choice_nodes = choice_nodes_on_step.difference(
            {step.source_node_id}
        )
        witness = step.active_margin_witness
        if (
            mechanism_margin_audit
            and newly_reached_choice_nodes
            and witness is None
            and not negative_revision
        ):
            raise FramingQualityValidationError(
                "active_margin_witness_missing: every choice-dependent mechanism "
                "step requires a concrete payoff comparison"
            )
        if witness is not None:
            decision = node_by_id.get(witness.decision_node_id)
            if (
                decision is None
                or decision.kind != "choice"
                or witness.decision_node_id not in choice_nodes_on_step
            ):
                raise FramingQualityValidationError(
                    "active_margin_witness_binding: the witnessed decision must be "
                    "an exact PrimitiveGraph choice on the causal step"
                )
            payoff_nodes = tuple(
                node_by_id.get(node_id) for node_id in witness.payoff_node_ids
            )
            witness_issues: list[str] = []
            invalid_payoff_nodes = tuple(
                (node_id, node)
                for node_id, node in zip(witness.payoff_node_ids, payoff_nodes)
                if node is None
                or node.kind
                not in {"preference_technology", "equilibrium_object"}
            )
            if invalid_payoff_nodes:
                invalid = ", ".join(
                    _node_kind_diagnostic(node_id, node)
                    for node_id, node in invalid_payoff_nodes
                )
                witness_issues.append(
                    "active_margin_payoff_binding: every payoff reference must bind "
                    "an exact PrimitiveGraph payoff-basis or continuation node; "
                    f"invalid references: {invalid}"
                )
            disconnected_payoff_nodes = tuple(
                node_id
                for node_id in witness.payoff_node_ids
                if not (
                    _reachable(
                        frozen_adjacency, node_id, witness.decision_node_id
                    )
                    or _reachable(
                        frozen_adjacency, witness.decision_node_id, node_id
                    )
                )
            )
            if disconnected_payoff_nodes:
                witness_issues.append(
                    "active_margin_payoff_binding: every cited payoff object must be "
                    "connected to the witnessed decision; disconnected references: "
                    + ", ".join(disconnected_payoff_nodes)
                )
            if not any(
                node is not None
                and node.kind == "preference_technology"
                and _reachable(
                    frozen_adjacency, node.node_id, witness.decision_node_id
                )
                for node in payoff_nodes
            ):
                witness_issues.append(
                    "active_margin_payoff_binding: at least one exact payoff-basis "
                    "node must reach the witnessed decision"
                )
            if require_research_first_bindings and witness.consequence_binding is None:
                witness_issues.append(
                    "choice_consequence_binding_missing: every v7 payoff witness "
                    "must bind the action comparison to its claimed causal "
                    "consequence and public-state class"
                )
            elif witness.consequence_binding is not None:
                try:
                    _validate_choice_consequence_binding(
                        step=step,
                        witness=witness,
                        node_by_id=node_by_id,
                        edge_by_id=edge_by_id,
                        adjacency=frozen_adjacency,
                    )
                except FramingQualityValidationError as exc:
                    witness_issues.append(str(exc))
            if witness_issues:
                raise FramingQualityValidationError(" | ".join(witness_issues))
            witnessed_choice_nodes.add(witness.decision_node_id)
            witnessed_steps.append((step, witness))
        for force_index, force_id in enumerate(step.force_ids):
            force = force_by_id[force_id]
            if not _step_is_on_force_path(frozen_adjacency, force, step):
                primitive_path_issues.append(
                    {
                        "location": [
                            "causal_chain",
                            step_index,
                            "force_ids",
                            force_index,
                        ],
                        "type": "causal_step_not_on_force_path",
                        "step_number": step.step_number,
                        "step_source_node_id": step.source_node_id,
                        "step_target_node_id": step.target_node_id,
                        "force_id": force.force_id,
                        "force_source_node_id": force.source_node_id,
                        "force_margin_node_id": force.margin_node_id,
                        "force_target_node_id": force.target_node_id,
                    }
                )
            else:
                used_force_ids.add(force_id)
    for left_index, (left, right) in enumerate(zip(steps, steps[1:])):
        if left.target_node_id == right.source_node_id:
            continue
        primitive_path_issues.append(
            {
                "location": ["causal_chain", left_index + 1, "source_node_id"],
                "type": "causal_chain_not_closed",
                "left_step_number": left.step_number,
                "left_target_node_id": left.target_node_id,
                "right_step_number": right.step_number,
                "right_source_node_id": right.source_node_id,
            }
        )
    if primitive_path_issues:
        reported_issues = primitive_path_issues[:_MAX_STRUCTURED_DIAGNOSTIC_ISSUES]
        summaries: list[str] = []
        for issue in reported_issues:
            if issue["type"] == "causal_step_not_on_force_path":
                summaries.append(
                    "step "
                    f"{issue['step_number']} "
                    f"{issue['step_source_node_id']}->{issue['step_target_node_id']} "
                    f"is not an ordered subpath of force {issue['force_id']} "
                    f"{issue['force_source_node_id']}->{issue['force_margin_node_id']}"
                    f"->{issue['force_target_node_id']}"
                )
            else:
                summaries.append(
                    "chain gap between steps "
                    f"{issue['left_step_number']} and {issue['right_step_number']}: "
                    f"{issue['left_target_node_id']} != "
                    f"{issue['right_source_node_id']}"
                )
        raise FramingQualityValidationError(
            "causal_force_binding: primitive-path contract rejected "
            f"{len(primitive_path_issues)} issue(s): " + "; ".join(summaries),
            diagnostic_details={
                "validation_stage": "canonical_candidate_preflight",
                "rule_id": "framing.primitive_paths",
                "repairable": True,
                "retry_action": "edit_declared_candidate_and_retry_same_request",
                "repair_hint": (
                    "Use only exact PrimitiveGraph node IDs and directed paths; "
                    "bind each step to a force that contains it and close adjacent "
                    "step endpoints without inventing an absent connection."
                ),
                "issue_count": len(primitive_path_issues),
                "truncated": len(reported_issues) < len(primitive_path_issues),
                "issues": reported_issues,
            },
        )
    missing_force_ids = sorted(set(force_by_id).difference(used_force_ids))
    if missing_force_ids:
        raise FramingQualityValidationError(
            "causal_force_binding: every declared economic force must appear in "
            "the causal chain; missing=" + ",".join(missing_force_ids)
        )
    unwitnessed_force_margins = sorted(
        force.margin_node_id
        for force in bundle.forces
        if node_by_id[force.margin_node_id].kind == "choice"
        and force.margin_node_id not in witnessed_choice_nodes
    )
    if unwitnessed_force_margins and not negative_revision:
        raise FramingQualityValidationError(
            "active_margin_witness_missing: every operative choice margin used "
            "by an economic force must be payoff-witnessed; missing="
            + ",".join(unwitnessed_force_margins)
        )
    if bundle.tension.tension_kind in {
        "force_conflict",
        "sign_or_threshold_reversal",
    }:
        used_roles = {
            force_by_id[force_id].role for force_id in used_force_ids
        }
        if not {"baseline_force", "countervailing_force"}.issubset(used_roles):
            raise FramingQualityValidationError(
                "causal_force_binding: conflict and reversal chains must use a "
                "baseline and countervailing force"
            )

    unresolved_blocker = bool(bundle.disclosed_gaps)
    active_response_count = 0
    assessments_by_id = {
        item.benchmark_id: item for item in bundle.benchmark_assessments
    }
    for assessment_index, assessment in enumerate(bundle.benchmark_assessments):
        if (
            require_research_first_bindings
            and assessment.distinctive_mechanism is None
        ):
            raise FramingQualityValidationError(
                "distinctive_mechanism_declaration_missing: every v7 benchmark row "
                "must explicitly claim, disclaim, or mark unresolved its mechanism "
                "relative to a contrast"
            )
        if assessment.channel_kind == "active_response":
            active_response_count += 1
        path = assessment.channel_path
        if set(path).difference(node_ids):
            raise FramingQualityValidationError(
                "benchmark channel_path references a node outside PrimitiveGraph"
            )
        if any(edge not in direct_edges for edge in zip(path, path[1:])):
            raise FramingQualityValidationError(
                "benchmark channel_path is not an exact PrimitiveGraph path"
            )
        objects = (
            *assessment.changed,
            *assessment.held_fixed,
            *assessment.reoptimizing,
            *assessment.still_endogenous,
            *assessment.targets,
        )
        if any(
            item.primitive_node_id is not None
            and item.primitive_node_id not in node_ids
            for item in objects
        ):
            raise FramingQualityValidationError(
                "benchmark semantic ledger references an unknown primitive node"
            )
        changed_nodes = {
            item.primitive_node_id
            for item in assessment.changed
            if item.primitive_node_id is not None
        }
        target_nodes = {
            item.primitive_node_id
            for item in assessment.targets
            if item.primitive_node_id is not None
        }
        active_nodes: set[str] = set()
        for item in assessment.reoptimizing:
            if (
                item.primitive_node_id is None
                or item.semantic_level not in fq.REOPTIMIZING_SEMANTIC_LEVELS
                or node_by_id[item.primitive_node_id].kind != "choice"
            ):
                raise FramingQualityValidationError(
                    "placebo_control: a reoptimizing object must bind an exact "
                    "PrimitiveGraph choice node"
                )
            active_nodes.add(item.primitive_node_id)
        for item in assessment.still_endogenous:
            allowed_kinds = _ACTIVE_SEMANTIC_NODE_KINDS.get(item.semantic_level)
            if allowed_kinds is None:
                continue
            if (
                item.primitive_node_id is None
                or node_by_id[item.primitive_node_id].kind not in allowed_kinds
            ):
                raise FramingQualityValidationError(
                    "placebo_control: an endogenous active margin is incompatible "
                    "with its PrimitiveGraph node kind"
                )
            active_nodes.add(item.primitive_node_id)

        movable_groups = (
            ("changed", assessment.changed),
            ("reoptimizing", assessment.reoptimizing),
            ("still_endogenous", assessment.still_endogenous),
        )
        for held_index, held in enumerate(assessment.held_fixed):
            if held.primitive_node_id is None:
                continue
            overlapping_levels = _FIXING_LEVEL_OVERLAPS.get(
                held.fixing_level, frozenset()
            )
            for movable_group, movable_items in movable_groups:
                for movable_index, item in enumerate(movable_items):
                    if not (
                        item.primitive_node_id == held.primitive_node_id
                        and item.semantic_level in overlapping_levels
                    ):
                        continue
                    raise FramingQualityValidationError(
                        "fixed_endogenous_conflict: one PrimitiveGraph object is "
                        "held fixed and movable at the same semantic level",
                        diagnostic_details={
                            "validation_stage": "canonical_candidate_preflight",
                            "rule_id": "framing.benchmark_fixed_endogenous",
                            "location_root": (
                                "FramingQualityBundle.economic_interpretation.payload"
                            ),
                            "repairable": True,
                            "retry_action": (
                                "edit_declared_candidate_and_retry_same_request"
                            ),
                            "repair_hint": (
                                "Choose the object's actual economic role, then bind "
                                "this PrimitiveGraph node at one compatible fixing "
                                "or movability level; do not rename or rebind it "
                                "merely to bypass the conflict."
                            ),
                            "benchmark_id": assessment.benchmark_id,
                            "primitive_node_id": held.primitive_node_id,
                            "held_object_id": held.object_id,
                            "held_semantic_level": held.semantic_level,
                            "held_fixing_level": held.fixing_level,
                            "held_primitive_node_location": [
                                "benchmark_assessments",
                                assessment_index,
                                "held_fixed",
                                held_index,
                                "primitive_node_id",
                            ],
                            "held_fixing_level_location": [
                                "benchmark_assessments",
                                assessment_index,
                                "held_fixed",
                                held_index,
                                "fixing_level",
                            ],
                            "movable_group": movable_group,
                            "movable_object_id": item.object_id,
                            "movable_semantic_level": item.semantic_level,
                            "movable_primitive_node_location": [
                                "benchmark_assessments",
                                assessment_index,
                                movable_group,
                                movable_index,
                                "primitive_node_id",
                            ],
                            "movable_semantic_level_location": [
                                "benchmark_assessments",
                                assessment_index,
                                movable_group,
                                movable_index,
                                "semantic_level",
                            ],
                            "conflicting_semantic_levels": sorted(
                                overlapping_levels
                            ),
                        },
                    )
        if path[0] not in changed_nodes or path[-1] not in target_nodes:
            changed_bindings = [
                {
                    "object_id": item.object_id,
                    "primitive_node_id": item.primitive_node_id,
                    "location": [
                        "benchmark_assessments",
                        assessment_index,
                        "changed",
                        item_index,
                        "primitive_node_id",
                    ],
                }
                for item_index, item in enumerate(assessment.changed)
            ]
            target_bindings = [
                {
                    "object_id": item.object_id,
                    "primitive_node_id": item.primitive_node_id,
                    "location": [
                        "benchmark_assessments",
                        assessment_index,
                        "targets",
                        item_index,
                        "primitive_node_id",
                    ],
                }
                for item_index, item in enumerate(assessment.targets)
            ]
            expected_source_node_ids = sorted(changed_nodes)
            expected_target_node_ids = sorted(target_nodes)
            reported_changed_bindings = changed_bindings[
                :_MAX_STRUCTURED_DIAGNOSTIC_ISSUES
            ]
            reported_target_bindings = target_bindings[
                :_MAX_STRUCTURED_DIAGNOSTIC_ISSUES
            ]
            reported_source_node_ids = expected_source_node_ids[
                :_MAX_STRUCTURED_DIAGNOSTIC_ISSUES
            ]
            reported_target_node_ids = expected_target_node_ids[
                :_MAX_STRUCTURED_DIAGNOSTIC_ISSUES
            ]
            diagnostic_truncated = any(
                (
                    len(reported_changed_bindings) < len(changed_bindings),
                    len(reported_target_bindings) < len(target_bindings),
                    len(reported_source_node_ids) < len(expected_source_node_ids),
                    len(reported_target_node_ids) < len(expected_target_node_ids),
                )
            )
            raise FramingQualityValidationError(
                "benchmark channel endpoints do not match changed and target objects",
                diagnostic_details={
                    "validation_stage": "canonical_candidate_preflight",
                    "rule_id": "framing.benchmark_channel_endpoints",
                    "location_root": (
                        "FramingQualityBundle.economic_interpretation.payload"
                    ),
                    "repairable": True,
                    "retry_action": "edit_declared_candidate_and_retry_same_request",
                    "repair_hint": (
                        "First bind every relevant changed or target object that "
                        "has no primitive_node_id; then set channel_path[0] to a "
                        "changed node and channel_path[-1] to a target node, using "
                        "an exact PrimitiveGraph path rather than a truncated proxy."
                    ),
                    "benchmark_id": assessment.benchmark_id,
                    "channel_source_location": [
                        "benchmark_assessments",
                        assessment_index,
                        "channel_path",
                        0,
                    ],
                    "channel_target_location": [
                        "benchmark_assessments",
                        assessment_index,
                        "channel_path",
                        len(path) - 1,
                    ],
                    "actual_source_node_id": path[0],
                    "actual_target_node_id": path[-1],
                    "source_matches": path[0] in changed_nodes,
                    "target_matches": path[-1] in target_nodes,
                    "changed_binding_count": len(changed_bindings),
                    "target_binding_count": len(target_bindings),
                    "expected_source_node_count": len(expected_source_node_ids),
                    "expected_target_node_count": len(expected_target_node_ids),
                    "changed_bindings": reported_changed_bindings,
                    "target_bindings": reported_target_bindings,
                    "expected_source_node_ids": reported_source_node_ids,
                    "expected_target_node_ids": reported_target_node_ids,
                    "truncated": diagnostic_truncated,
                },
            )
        if (
            assessment.channel_kind == "active_response"
            and not set(path[1:-1]).intersection(active_nodes)
        ):
            raise FramingQualityValidationError(
                "placebo_control: the changed object reaches the target without an "
                "identified reoptimizing or still-endogenous response margin"
            )
        risky = (
            assessment.aggregate_invariance.weighting_distribution_status
            == "unresolved"
            or assessment.selection_assurance.status in {"selector_only", "unresolved"}
            or assessment.attribution_strength in {"weak", "unresolved"}
            or assessment.channel_kind == "diagnostic_only"
        )
        unresolved_blocker = unresolved_blocker or risky
        _validate_distinctive_mechanism(
            assessment=assessment,
            assessments_by_id=assessments_by_id,
            node_by_id=node_by_id,
            edge_by_id=edge_by_id,
            witnessed_steps=tuple(witnessed_steps),
        )

    if (
        require_research_first_bindings
        and bundle.distinctive_mechanism_contribution_status is None
    ):
        raise FramingQualityValidationError(
            "distinctive_mechanism_contribution_missing: v7 must explicitly state "
            "whether benchmark-distinctive mechanism is claimed, not claimed, or "
            "unresolved"
        )

    if (
        bundle.tension.tension_kind
        in {"causal_channel", "force_conflict", "sign_or_threshold_reversal"}
        and active_response_count == 0
        and not negative_revision
    ):
        raise FramingQualityValidationError(
            "a causal-channel, conflict, or reversal framing requires at least one "
            "active-response benchmark"
        )

    if bundle.proposed_action == "ready_for_g1" and unresolved_blocker:
        raise FramingQualityValidationError(
            "unresolved framing risks cannot be promoted to ready_for_g1"
        )


def validate_research_first_framing_science(
    bundle: fq.FramingQualityBundle,
    *,
    research_question: t.ResearchQuestion,
    benchmark_set: t.BenchmarkSet,
    primitive_graph: t.PrimitiveGraph,
) -> None:
    """Validate the v7 research-first scientific bindings without route plumbing."""

    _validate_bundle_science(
        bundle,
        rq=research_question,
        benchmarks=benchmark_set,
        graph=primitive_graph,
        require_research_first_bindings=True,
    )


def _validate_hard_relation(
    relation: RelationVersion,
    *,
    relation_type: str,
    source: EntityVersion,
    target: EntityVersion,
    snapshot: Snapshot,
) -> None:
    source_ref = _entity_ref(source)
    target_ref = _entity_ref(target)
    source_owner = _owner_facet(source.entity_type)
    target_owner = _owner_facet(target.entity_type)
    if source_owner is None or target_owner is None:
        raise FramingQualityValidationError("framing relation has an unowned endpoint")
    if source_owner == "authority":
        effective_refs = {
            (reference.decision_id, reference.version)
            for reference in snapshot.effective_decisions.values()
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
            for decision in snapshot.decisions
            if (decision.decision_id, decision.version) in effective_refs
            and (
                decision.subject_ref == source.entity_id
                or source.entity_id in decision.affected_scopes
            )
        ]
        governing.sort(
            key=lambda item: (
                item["decision_kind"], item["decision_id"], item["version"]
            )
        )
        expected_source_hash = object_digest(
            {
                "stored_authority": facet_semantic_value(source, "authority"),
                "effective_decisions": governing,
            }
        )
    else:
        expected_source_hash = facet_semantic_hash(source, source_owner)
    if (
        relation.relation_type != relation_type
        or relation.source != source_ref
        or relation.target != target_ref
        or relation.dependency_mode != "hard"
        or relation.upstream is None
        or relation.downstream is None
        or relation.upstream.entity_id != source.entity_id
        or relation.upstream.version != source.version
        or relation.upstream.facet != source_owner
        or relation.upstream.field_path is not None
        or relation.upstream.semantic_hash
        != expected_source_hash
        or relation.downstream.entity_id != target.entity_id
        or relation.downstream.version != target.version
        or relation.downstream.facet != target_owner
        or relation.downstream.field_path is not None
    ):
        raise FramingQualityValidationError(
            f"{relation_type} must be one whole-facet hard dependency with exact hashes"
        )


def _candidate_key(value: object) -> tuple[str, str, int]:
    if isinstance(value, EntityVersionRef):
        return "entity", value.entity_id, value.version
    if isinstance(value, RelationVersionRef):
        return "relation", value.relation_id, value.version
    if isinstance(value, BlockerRef):
        return "blocker", value.blocker_id, 0
    raise FramingQualityValidationError(
        "framing RouteOutcome contains an unsupported candidate ref"
    )


def validate_framing_quality_projection(
    snapshot: Snapshot,
) -> FramingQualityProjectionReport:
    exact = _exact_entities(snapshot)
    bundle_refs: list[EntityVersionRef] = []
    current_scopes: set[tuple[tuple[str, int], ...]] = set()
    for entity in snapshot.entity_versions:
        if entity.entity_type != "FramingQualityBundle":
            continue
        previous = (
            exact.get((entity.entity_id, entity.version - 1))
            if entity.version > 1
            else None
        )
        bundle = validate_framing_quality_entity(entity, previous)
        refs = (
            bundle.research_question_ref,
            bundle.benchmark_set_ref,
            bundle.primitive_graph_ref,
            bundle.source_g1_dossier_ref,
        )
        resolved = [exact.get(_entity_key(reference)) for reference in refs]
        if any(item is None for item in resolved):
            raise FramingQualityValidationError(
                "FramingQualityBundle contains an unresolved exact input ref"
            )
        rq_entity, benchmark_entity, graph_entity, dossier_entity = resolved
        assert rq_entity is not None
        assert benchmark_entity is not None
        assert graph_entity is not None
        assert dossier_entity is not None
        rq = _parse_theory(rq_entity, t.ResearchQuestion)
        benchmarks = _parse_theory(benchmark_entity, t.BenchmarkSet)
        graph = _parse_theory(graph_entity, t.PrimitiveGraph)
        dossier = _parse_theory(dossier_entity, t.GateDossier)
        assert isinstance(rq, t.ResearchQuestion)
        assert isinstance(benchmarks, t.BenchmarkSet)
        assert isinstance(graph, t.PrimitiveGraph)
        assert isinstance(dossier, t.GateDossier)
        if dossier.gate_kind != "G1_question_benchmark":
            raise FramingQualityValidationError(
                "FramingQualityBundle source dossier is not G1"
            )
        _validate_bundle_science(
            bundle,
            rq=rq,
            benchmarks=benchmarks,
            graph=graph,
            allow_unwitnessed_negative_revision=True,
        )
        reference = _entity_ref(entity)
        bundle_refs.append(reference)
        if _is_current_and_fresh(snapshot, entity):
            scope = tuple(_entity_key(item) for item in refs)
            if scope in current_scopes:
                raise FramingQualityValidationError(
                    "one exact framing lineage has multiple current audit bundles"
                )
            current_scopes.add(scope)
    return FramingQualityProjectionReport(
        bundle_refs=tuple(sorted(bundle_refs, key=_entity_key))
    )


def validate_framing_quality_route_transaction(
    snapshot: Snapshot, transaction: Transaction, route_spec: RouteSpecV5
) -> FramingQualityProjectionReport:
    """Validate one active v6/v7 audit transaction against its exact base."""

    if (
        transaction.origin != "route_run"
        or transaction.route_id != FRAMING_ROUTE_ID
        or route_spec.route_id != FRAMING_ROUTE_ID
        or route_spec.route_version not in FRAMING_ROUTE_VERSIONS
        or route_spec.availability != "enabled"
        or route_spec.exit_validator_id
        != (
            FRAMING_NEGATIVE_EXIT_VALIDATOR_ID
            if route_spec.route_version == 8
            else FRAMING_EXIT_VALIDATOR_ID
        )
    ):
        raise FramingQualityValidationError(
            "transaction is not bound to an enabled framing route"
        )
    if transaction.project_id != snapshot.project_id:
        raise FramingQualityValidationError("framing transaction crosses projects")
    if len({_candidate_key(item) for item in transaction.evidence_refs}) != len(
        transaction.evidence_refs
    ):
        raise FramingQualityValidationError("framing transaction repeats exact evidence")
    if not all(isinstance(item, EntityVersionRef) for item in transaction.evidence_refs):
        raise FramingQualityValidationError(
            "framing transaction evidence must be the four exact input entities"
        )
    entry = _validate_entry_refs(
        snapshot,
        route_spec,
        tuple(
            item for item in transaction.evidence_refs if isinstance(item, EntityVersionRef)
        ),
        actor=transaction.actor,
    )

    produced_entities: list[EntityVersion] = []
    produced_relations: list[RelationVersion] = []
    blockers = []
    outcomes: list[RecordRouteOutcomeOp] = []
    for operation in transaction.operations:
        if operation.op not in route_spec.allowed_operations:
            raise FramingQualityValidationError(
                f"operation {operation.op} is outside the framing route allowlist"
            )
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            if operation.entity.entity_type not in route_spec.allowed_entity_types:
                raise FramingQualityValidationError(
                    "framing route emitted a disallowed entity type"
                )
            produced_entities.append(operation.entity)
        elif isinstance(operation, CreateRelationOp):
            if operation.relation.relation_type not in route_spec.allowed_relation_types:
                raise FramingQualityValidationError(
                    "framing route emitted a disallowed relation type"
                )
            produced_relations.append(operation.relation)
        elif isinstance(operation, RecordBlockerOp):
            blockers.append(operation.blocker)
        elif isinstance(operation, RecordRouteOutcomeOp):
            outcomes.append(operation)
        else:
            raise FramingQualityValidationError(
                "framing route contains an unsupported operation shape"
            )

    bundle_entity = _one_by_type(produced_entities, "FramingQualityBundle")
    replacement_entity = _one_by_type(produced_entities, "GateDossier")
    if len(produced_entities) != 2:
        raise FramingQualityValidationError(
            "framing route must create exactly one bundle and one replacement dossier"
        )
    exact_prior = _exact_entities(snapshot)
    entity_operations = {
        operation.entity.entity_type: operation
        for operation in transaction.operations
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp))
    }
    bundle_operation = entity_operations["FramingQualityBundle"]
    dossier_operation = entity_operations["GateDossier"]
    if not isinstance(dossier_operation, CreateEntityOp):
        raise FramingQualityValidationError(
            "the immutable replacement GateDossier must be created, never superseded"
        )
    if entry.prior_bundle_ref is None:
        if not isinstance(bundle_operation, CreateEntityOp):
            raise FramingQualityValidationError(
                "a new framing lineage must create FramingQualityBundle version 1"
            )
        if (
            bundle_entity.version != 1
            or bundle_entity.supersedes is not None
            or bundle_entity.entity_id in snapshot.current_entities
        ):
            raise FramingQualityValidationError(
                "a new framing lineage must use a new bundle ID at version 1"
            )
    elif (
        not isinstance(bundle_operation, SupersedeEntityOp)
        or bundle_operation.previous != entry.prior_bundle_ref
    ):
        raise FramingQualityValidationError(
            "same-scope framing continuation must supersede the current bundle"
        )
    if (
        replacement_entity.version != 1
        or replacement_entity.supersedes is not None
        or replacement_entity.entity_id in snapshot.current_entities
    ):
        raise FramingQualityValidationError(
            "replacement GateDossier must use a new ID at version 1"
        )

    for entity in produced_entities:
        if (
            entity.project_id != transaction.project_id
            or entity.privacy != transaction.privacy
            or entity.access_compartments != transaction.access_compartments
            or entity.created_at != transaction.created_at
        ):
            raise FramingQualityValidationError(
                "framing outputs must be exact entities bound to the transaction"
            )

    prior_bundle_entity = (
        exact_prior.get(_entity_key(entry.prior_bundle_ref))
        if entry.prior_bundle_ref is not None
        else None
    )
    bundle = validate_framing_quality_entity(bundle_entity, prior_bundle_entity)
    if route_spec.route_version < 7 and (
        bundle.distinctive_mechanism_contribution_status is not None
        or any(
            step.active_margin_witness is not None
            and step.active_margin_witness.consequence_binding is not None
            for step in bundle.causal_chain
        )
        or any(
            assessment.distinctive_mechanism is not None
            for assessment in bundle.benchmark_assessments
        )
    ):
        raise FramingQualityValidationError(
            "v7 research-first bindings are outside the frozen v6 route semantics"
        )
    try:
        replacement = validate_theory_entity(replacement_entity)
    except TheoryValidationError as exc:
        raise FramingQualityValidationError(str(exc)) from exc
    if not isinstance(replacement, t.GateDossier):
        raise FramingQualityValidationError("replacement output is not a GateDossier")

    if (
        bundle.research_question_ref != entry.research_question_ref
        or bundle.benchmark_set_ref != entry.benchmark_set_ref
        or bundle.primitive_graph_ref != entry.primitive_graph_ref
        or bundle.source_g1_dossier_ref != entry.source_g1_dossier_ref
    ):
        raise FramingQualityValidationError(
            "FramingQualityBundle does not bind the exact route inputs"
        )
    rq_entity = exact_prior[_entity_key(entry.research_question_ref)]
    benchmark_entity = exact_prior[_entity_key(entry.benchmark_set_ref)]
    graph_entity = exact_prior[_entity_key(entry.primitive_graph_ref)]
    source_dossier_entity = exact_prior[_entity_key(entry.source_g1_dossier_ref)]
    rq = _parse_theory(rq_entity, t.ResearchQuestion)
    benchmarks = _parse_theory(benchmark_entity, t.BenchmarkSet)
    graph = _parse_theory(graph_entity, t.PrimitiveGraph)
    source_dossier = _parse_theory(source_dossier_entity, t.GateDossier)
    assert isinstance(rq, t.ResearchQuestion)
    assert isinstance(benchmarks, t.BenchmarkSet)
    assert isinstance(graph, t.PrimitiveGraph)
    assert isinstance(source_dossier, t.GateDossier)
    _validate_bundle_science(
        bundle,
        rq=rq,
        benchmarks=benchmarks,
        graph=graph,
        require_research_first_bindings=route_spec.route_version >= 7,
        allow_unwitnessed_negative_revision=route_spec.route_version == 8,
    )

    bundle_ref = _entity_ref(bundle_entity)
    expected_action = "approve" if bundle.proposed_action == "ready_for_g1" else "revise"
    if (
        replacement.gate_kind != "G1_question_benchmark"
        or replacement.research_question_ref != entry.research_question_ref
        or replacement.ordered_object_refs
        != (*source_dossier.ordered_object_refs, bundle_ref)
        or replacement.proposed_action != expected_action
        or replacement.prepared_at != transaction.created_at
        or len(replacement.requirements) != len(source_dossier.requirements) + 1
        or replacement.requirements[:-1] != source_dossier.requirements
    ):
        raise FramingQualityValidationError(
            "replacement G1 dossier does not preserve and strengthen its source package"
        )
    added_requirement = replacement.requirements[-1]
    expected_condition = (
        "evidence_supplied"
        if bundle.proposed_action == "ready_for_g1"
        else "risk_disclosed"
    )
    if (
        added_requirement.requirement_id != FRAMING_REQUIREMENT_ID
        or added_requirement.evidence_refs != (bundle_ref,)
        or added_requirement.recorded_condition != expected_condition
    ):
        raise FramingQualityValidationError(
            "replacement dossier lacks the exact framing-quality requirement"
        )

    if len(produced_relations) != 5:
        raise FramingQualityValidationError(
            "framing route requires four audits edges and one governs edge"
        )
    audit_sources = (
        rq_entity,
        benchmark_entity,
        graph_entity,
        source_dossier_entity,
    )
    unused = list(produced_relations)
    for source in audit_sources:
        matches = [
            item
            for item in unused
            if item.relation_type == "audits"
            and item.source == _entity_ref(source)
            and item.target == bundle_ref
        ]
        if len(matches) != 1:
            raise FramingQualityValidationError(
                "framing bundle requires one audits dependency from every exact input"
            )
        _validate_hard_relation(
            matches[0],
            relation_type="audits",
            source=source,
            target=bundle_entity,
            snapshot=snapshot,
        )
        unused.remove(matches[0])
    governs = [
        item
        for item in unused
        if item.relation_type == "governs"
        and item.source == bundle_ref
        and item.target == _entity_ref(replacement_entity)
    ]
    if len(governs) != 1 or len(unused) != 1:
        raise FramingQualityValidationError(
            "replacement dossier requires one exact governs dependency from the bundle"
        )
    _validate_hard_relation(
        governs[0],
        relation_type="governs",
        source=bundle_entity,
        target=replacement_entity,
        snapshot=snapshot,
    )
    for relation in produced_relations:
        if (
            relation.version != 1
            or relation.supersedes is not None
            or relation.relation_id in snapshot.current_relations
            or relation.project_id != transaction.project_id
            or relation.privacy != transaction.privacy
            or relation.access_compartments != transaction.access_compartments
            or relation.created_at != transaction.created_at
        ):
            raise FramingQualityValidationError(
                "framing dependencies must be new version-1 relations bound to the transaction"
            )

    if len(outcomes) != 1:
        raise FramingQualityValidationError(
            "framing route requires exactly one RouteOutcome"
        )
    outcome = outcomes[0].outcome
    if (
        outcome.route_id != FRAMING_ROUTE_ID
        or outcome.route_run_id != transaction.route_run_id
        or outcome.outcome != "completed_with_candidate"
        or outcome.privacy != transaction.privacy
        or outcome.access_compartments != transaction.access_compartments
    ):
        raise FramingQualityValidationError(
            "framing RouteOutcome is not an exact completed candidate for this run"
        )
    produced_keys = {
        *(_candidate_key(_entity_ref(item)) for item in produced_entities),
        *(_candidate_key(_relation_ref(item)) for item in produced_relations),
        *(_candidate_key(BlockerRef(blocker_id=item.blocker_id)) for item in blockers),
    }
    outcome_keys = {_candidate_key(item) for item in outcome.candidate_refs}
    if len(outcome_keys) != len(outcome.candidate_refs) or outcome_keys != produced_keys:
        raise FramingQualityValidationError(
            "framing RouteOutcome candidate_refs must equal every produced exact object"
        )

    after = snapshot.model_copy(
        update={
            "entity_versions": (*snapshot.entity_versions, *produced_entities),
            "relation_versions": (*snapshot.relation_versions, *produced_relations),
            "route_outcomes": (*snapshot.route_outcomes, outcome),
            "blockers": (*snapshot.blockers, *blockers),
            "current_entities": {
                **snapshot.current_entities,
                **{item.entity_id: item.version for item in produced_entities},
            },
            "current_relations": {
                **snapshot.current_relations,
                **{item.relation_id: item.version for item in produced_relations},
            },
        }
    )
    return validate_framing_quality_projection(after)


def validate_framing_repair_route_transaction(
    snapshot: Snapshot, transaction: Transaction, route_spec: RouteSpecV5
) -> FramingQualityProjectionReport:
    """Validate v5 stale repair or one gap-authorized proactive revision."""

    if (
        transaction.origin != "route_run"
        or transaction.route_id != FRAMING_REPAIR_ROUTE_ID
        or route_spec.route_id != FRAMING_REPAIR_ROUTE_ID
        or route_spec.route_version != 5
        or route_spec.availability != "enabled"
        or route_spec.exit_validator_id != FRAMING_REPAIR_EXIT_VALIDATOR_ID
    ):
        raise FramingQualityValidationError(
            "transaction is not bound to the enabled v5 repair route"
        )
    entity_evidence = tuple(
        item for item in transaction.evidence_refs if isinstance(item, EntityVersionRef)
    )
    entry = _validate_framing_repair_entry_refs(
        snapshot,
        route_spec,
        entity_evidence,
        actor=transaction.actor,
    )
    normalized = _phase2_repair_spec(route_spec)

    if entry.repair_mode == "framing_revision":
        supersessions = [
            operation
            for operation in transaction.operations
            if isinstance(operation, SupersedeEntityOp)
        ]
        if len(supersessions) != 1:
            raise FramingQualityValidationError(
                "proactive framing repair must supersede exactly one entity"
            )
        operation = supersessions[0]
        exact = _exact_entities(snapshot)
        previous = exact.get(_entity_key(entry.target_ref))
        if (
            previous is None
            or operation.previous != entry.target_ref
            or operation.entity.entity_id != previous.entity_id
            or operation.entity.entity_type != previous.entity_type
            or operation.entity.version != previous.version + 1
            or operation.entity.supersedes != entry.target_ref
        ):
            raise FramingQualityValidationError(
                "proactive framing repair must replace its one exact named target"
            )

    try:
        validate_phase2_route_transaction(
            snapshot,
            transaction,
            normalized,
            route_input_refs=(entry.target_ref,),
            allow_fresh_repair=entry.repair_mode == "framing_revision",
            allow_research_question_revision=True,
        )
    except TheoryValidationError as exc:
        raise FramingQualityValidationError(str(exc)) from exc
    return validate_framing_quality_projection(snapshot)


def validate_current_g1_framing_decision(
    snapshot: Snapshot, decision: Decision
) -> None:
    """Preflight a *new* approving G1 action without rewriting old replay."""

    if not (
        decision.decision_kind == "G1_question_benchmark"
        and decision.status == "confirmed"
        and decision.machine_outcome == "approve"
        and decision.selected_option == "approve"
    ):
        return
    current = _current_entities(snapshot)
    exact = _exact_entities(snapshot)
    dossier_entity = current.get(decision.subject_ref)
    if (
        dossier_entity is None
        or dossier_entity.entity_type != "GateDossier"
        or dossier_entity.entity_id not in decision.evidence_refs
        or not _is_current_and_fresh(snapshot, dossier_entity)
    ):
        raise FramingQualityValidationError(
            "current G1 approval requires one fresh strengthened GateDossier"
        )
    dossier = _parse_theory(dossier_entity, t.GateDossier)
    assert isinstance(dossier, t.GateDossier)
    if decision.scope_ref != dossier.research_question_ref.entity_id:
        raise FramingQualityValidationError(
            "current G1 approval scope differs from its strengthened dossier"
        )
    bundle_entities = [
        current.get(reference.entity_id)
        for reference in dossier.ordered_object_refs
        if current.get(reference.entity_id) is not None
        and current[reference.entity_id].version == reference.version
        and current[reference.entity_id].entity_type == "FramingQualityBundle"
    ]
    if len(bundle_entities) != 1 or bundle_entities[0] is None:
        raise FramingQualityValidationError(
            "current G1 approval cannot bypass the framing-quality preflight"
        )
    bundle_entity = bundle_entities[0]
    assert bundle_entity is not None
    if not _is_current_and_fresh(snapshot, bundle_entity):
        raise FramingQualityValidationError(
            "current G1 approval cannot use a stale framing-quality bundle"
        )
    previous_bundle = (
        exact.get((bundle_entity.entity_id, bundle_entity.version - 1))
        if bundle_entity.version > 1
        else None
    )
    bundle = validate_framing_quality_entity(bundle_entity, previous_bundle)
    if (
        bundle.proposed_action != "ready_for_g1"
        or bundle.research_question_ref != dossier.research_question_ref
        or not any(
            item.requirement_id == FRAMING_REQUIREMENT_ID
            and item.evidence_refs == (_entity_ref(bundle_entity),)
            and item.recorded_condition == "evidence_supplied"
            for item in dossier.requirements
        )
    ):
        raise FramingQualityValidationError(
            "current G1 approval requires a ready_for_g1 framing bundle"
        )
    for reference in (
        bundle.research_question_ref,
        bundle.benchmark_set_ref,
        bundle.primitive_graph_ref,
        bundle.source_g1_dossier_ref,
    ):
        entity = exact.get(_entity_key(reference))
        if entity is None or not _is_current_and_fresh(snapshot, entity):
            raise FramingQualityValidationError(
                "current G1 approval contains a stale framing input"
            )


def validate_phase5_route_entry(
    snapshot: Snapshot,
    route_spec: RouteSpecV5,
    focus_entity_ids: Iterable[str],
    *,
    actor: Actor,
) -> FramingQualityRouteEntryReport | FramingRepairRouteEntryReport:
    if route_spec.route_id == FRAMING_REPAIR_ROUTE_ID:
        return validate_framing_repair_route_entry(
            snapshot, route_spec, focus_entity_ids, actor=actor
        )
    return validate_framing_quality_route_entry(
        snapshot, route_spec, focus_entity_ids, actor=actor
    )


def validate_phase5_route_transaction(
    snapshot: Snapshot, transaction: Transaction, route_spec: RouteSpecV5
) -> FramingQualityProjectionReport:
    if route_spec.route_id == FRAMING_REPAIR_ROUTE_ID:
        return validate_framing_repair_route_transaction(
            snapshot, transaction, route_spec
        )
    return validate_framing_quality_route_transaction(
        snapshot, transaction, route_spec
    )


__all__ = [
    "FRAMING_ENTRY_VALIDATOR_ID",
    "FRAMING_EXIT_VALIDATOR_ID",
    "FRAMING_NEGATIVE_EXIT_VALIDATOR_ID",
    "FRAMING_REQUIREMENT_ID",
    "FRAMING_REPAIR_ENTRY_VALIDATOR_ID",
    "FRAMING_REPAIR_EXIT_VALIDATOR_ID",
    "FRAMING_REPAIR_ROUTE_ID",
    "FRAMING_ROUTE_ID",
    "FramingQualityEntityPreflightIssueV1",
    "FramingQualityEntityPreflightReportV1",
    "FramingQualityProjectionReport",
    "FramingQualityRouteEntryReport",
    "FramingRepairRouteEntryReport",
    "FramingQualityValidationError",
    "active_semantic_node_kinds",
    "diagnose_framing_quality_entity",
    "fixing_level_overlaps",
    "validate_current_g1_framing_decision",
    "validate_framing_quality_entity",
    "validate_framing_quality_projection",
    "validate_framing_quality_route_entry",
    "validate_framing_quality_route_transaction",
    "validate_framing_repair_route_entry",
    "validate_framing_repair_route_transaction",
    "validate_phase5_route_entry",
    "validate_phase5_route_transaction",
    "validate_research_first_framing_science",
]
