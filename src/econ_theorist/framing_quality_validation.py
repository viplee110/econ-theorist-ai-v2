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
from typing import Literal

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
    StrictModel,
    SupersedeEntityOp,
    Transaction,
)
from .authoring_validation import facet_semantic_hash, facet_semantic_value
from .codec import object_digest
from .theory_validation import (
    TheoryValidationError,
    validate_phase2_route_entry,
    validate_phase2_route_transaction,
    validate_theory_entity,
)


FRAMING_ROUTE_ID = "audit.framing_economics"
FRAMING_ENTRY_VALIDATOR_ID = "framing_quality_route_entry.v1"
FRAMING_EXIT_VALIDATOR_ID = "framing_quality_route_exit.v1"
FRAMING_REPAIR_ROUTE_ID = "repair.dependency"
FRAMING_REPAIR_ENTRY_VALIDATOR_ID = "framing_repair_route_entry.v1"
FRAMING_REPAIR_EXIT_VALIDATOR_ID = "framing_repair_route_exit.v1"
FRAMING_REQUIREMENT_ID = "g1.framing_quality"


class FramingQualityValidationError(ValueError):
    """A v5 framing-quality object or route transaction is inadmissible."""


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
        or route_spec.route_version != 5
        or route_spec.availability != "enabled"
        or route_spec.entry_validator_id != FRAMING_ENTRY_VALIDATOR_ID
    ):
        raise FramingQualityValidationError("unknown or malformed v5 framing route")
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


def _validate_bundle_science(
    bundle: fq.FramingQualityBundle,
    *,
    rq: t.ResearchQuestion,
    benchmarks: t.BenchmarkSet,
    graph: t.PrimitiveGraph,
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
    for step in steps:
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
        for force_id in step.force_ids:
            force = force_by_id[force_id]
            if not _step_is_on_force_path(frozen_adjacency, force, step):
                raise FramingQualityValidationError(
                    "causal_force_binding: a causal-chain step is not an ordered "
                    "subpath of its cited economic force"
                )
            used_force_ids.add(force_id)
    if steps[0].target_node_id != steps[1].source_node_id or (
        steps[1].target_node_id != steps[2].source_node_id
    ):
        raise FramingQualityValidationError(
            "causal chain is not closed across its three ordered steps"
        )
    missing_force_ids = sorted(set(force_by_id).difference(used_force_ids))
    if missing_force_ids:
        raise FramingQualityValidationError(
            "causal_force_binding: every declared economic force must appear in "
            "the causal chain; missing=" + ",".join(missing_force_ids)
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
    for assessment in bundle.benchmark_assessments:
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

        movable_objects = (
            *assessment.changed,
            *assessment.reoptimizing,
            *assessment.still_endogenous,
        )
        for held in assessment.held_fixed:
            if held.primitive_node_id is None:
                continue
            overlapping_levels = _FIXING_LEVEL_OVERLAPS.get(
                held.fixing_level, frozenset()
            )
            if any(
                item.primitive_node_id == held.primitive_node_id
                and item.semantic_level in overlapping_levels
                for item in movable_objects
            ):
                raise FramingQualityValidationError(
                    "fixed_endogenous_conflict: one PrimitiveGraph object is held "
                    "fixed and movable at the same semantic level"
                )
        if path[0] not in changed_nodes or path[-1] not in target_nodes:
            raise FramingQualityValidationError(
                "benchmark channel endpoints do not match changed and target objects"
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

    if (
        bundle.tension.tension_kind
        in {"causal_channel", "force_conflict", "sign_or_threshold_reversal"}
        and active_response_count == 0
    ):
        raise FramingQualityValidationError(
            "a causal-channel, conflict, or reversal framing requires at least one "
            "active-response benchmark"
        )

    if bundle.proposed_action == "ready_for_g1" and unresolved_blocker:
        raise FramingQualityValidationError(
            "unresolved framing risks cannot be promoted to ready_for_g1"
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
        _validate_bundle_science(bundle, rq=rq, benchmarks=benchmarks, graph=graph)
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
    """Validate one additive v5 route transaction against its exact base."""

    if (
        transaction.origin != "route_run"
        or transaction.route_id != FRAMING_ROUTE_ID
        or route_spec.route_id != FRAMING_ROUTE_ID
        or route_spec.route_version != 5
        or route_spec.availability != "enabled"
        or route_spec.exit_validator_id != FRAMING_EXIT_VALIDATOR_ID
    ):
        raise FramingQualityValidationError(
            "transaction is not bound to the enabled v5 framing route"
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
    _validate_bundle_science(bundle, rq=rq, benchmarks=benchmarks, graph=graph)

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
    "FRAMING_REQUIREMENT_ID",
    "FRAMING_REPAIR_ENTRY_VALIDATOR_ID",
    "FRAMING_REPAIR_EXIT_VALIDATOR_ID",
    "FRAMING_REPAIR_ROUTE_ID",
    "FRAMING_ROUTE_ID",
    "FramingQualityProjectionReport",
    "FramingQualityRouteEntryReport",
    "FramingRepairRouteEntryReport",
    "FramingQualityValidationError",
    "validate_current_g1_framing_decision",
    "validate_framing_quality_entity",
    "validate_framing_quality_projection",
    "validate_framing_quality_route_entry",
    "validate_framing_quality_route_transaction",
    "validate_framing_repair_route_entry",
    "validate_framing_repair_route_transaction",
    "validate_phase5_route_entry",
    "validate_phase5_route_transaction",
]
