"""Fail-closed transaction replay and candidate validation for Phase 1."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import TypeAlias

from pydantic import ValidationError as PydanticValidationError

from ..context import compile_context, make_context_manifest
from ..codec import (
    canonical_json_bytes,
    sha256_digest,
    transaction_bytes,
    transaction_digest,
)
from ..errors import EconTheoristError, RuntimeStoreError
from ..models import (
    ArtifactDependencyRef,
    ArtifactPrivacySubject,
    ArtifactRegistration,
    BlockerRef,
    CanonicalObjectRef,
    ContextManifest,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EffectiveDecisionRef,
    EntityPrivacySubject,
    EntityVersion,
    EntityVersionRef,
    RecordBlockerOp,
    RecordDecisionOp,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    RelationPrivacySubject,
    RelationVersion,
    RelationVersionRef,
    RiskOrBlocker,
    RouteOutcome,
    RouteRun,
    RetireEntityOp,
    RetireRelationOp,
    Snapshot,
    StatusTransitionOp,
    SupersedeDecisionOp,
    SupersedeEntityOp,
    SupersedeRelationOp,
    Transaction,
)
from ..policy import (
    AUTHORITY_RANK,
    DECISION_REGISTRY_VERSION,
    ISOLATION_POLICY,
    KERNEL_HASH,
    KERNEL_VERSION,
    ROUTE_REGISTRY_HASH,
    SELECTOR_VERSION,
    VALIDATOR_VERSION,
    route_spec,
    validate_decision_authority,
    validate_runtime_validator,
)
from .freshness import (
    FacetPathError,
    authority_semantic_hash,
    changed_semantic_facets,
    derive_entity_statuses,
    facet_semantic_hash,
    facet_semantic_value,
    field_paths_overlap,
)
from .layout import STORE_DIRECTORY, StoreLayout
from .objects import HeadStore, ObjectStore


class ReplayError(RuntimeStoreError):
    """A canonical head cannot be replayed without guessing or rewriting."""


class EmptyHistoryError(ReplayError):
    """The project has no committed canonical head."""


class ChainIntegrityError(ReplayError):
    """The reachable transaction chain is malformed or discontinuous."""


class CandidateValidationError(EconTheoristError, ValueError):
    """A candidate transaction is structurally inadmissible."""


class ReferentialIntegrityError(CandidateValidationError):
    """A canonical reference does not resolve to the exact required object."""


class ChangedFacetError(CandidateValidationError):
    """Declared changed facets differ from the exact semantic diff."""


class DependencyCycleError(CandidateValidationError):
    """The invalidating relation projection contains a directed cycle."""


class UnsupportedOperationError(CandidateValidationError):
    """An operation is modeled for the architecture but disabled in Phase 1."""


class PrivacyFlowError(CandidateValidationError):
    """A relation would make protected source material more permissive."""


DependencyNode: TypeAlias = tuple[str, int, str, str | None]
PrivacyObject: TypeAlias = (
    EntityVersion
    | RelationVersion
    | Decision
    | ArtifactRegistration
    | RouteOutcome
    | RiskOrBlocker
)

_EFFECTIVE_DECISION_STATUSES = frozenset(
    {"provisional", "confirmed", "rejected"}
)
_PRIVACY_RANK = {
    "public": 0,
    "project_private": 1,
    "restricted": 2,
    "local_only": 3,
}


def decision_scope_key(decision: Decision) -> str:
    """Return an unambiguous canonical key for one authority scope."""

    return canonical_json_bytes(
        [decision.decision_kind, decision.subject_ref, decision.scope_ref]
    ).decode("utf-8")


def _coerce_layout(layout: StoreLayout | str | Path) -> StoreLayout:
    if isinstance(layout, StoreLayout):
        return layout
    path = Path(layout)
    if path.name == STORE_DIRECTORY:
        return StoreLayout.from_store_root(path)
    return StoreLayout.at(path)


def _route_output_record(operation: object) -> object | None:
    if isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
        return operation.entity
    if isinstance(operation, (CreateRelationOp, SupersedeRelationOp)):
        return operation.relation
    if isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp)):
        return operation.decision
    if isinstance(operation, RegisterArtifactOp):
        return operation.artifact
    if isinstance(operation, RecordRouteOutcomeOp):
        return operation.outcome
    if isinstance(operation, RecordBlockerOp):
        return operation.blocker
    return None


def validate_route_context_output_flow(
    transaction: Transaction, context_payload: object
) -> None:
    """Apply a conservative privacy/compartment join to route outputs.

    Phase 1 has no typed proof that a route output is independent of material
    present in its compiled context.  Every output must therefore be at least
    as private as every selected entity, relation, Decision, and blocker, and
    must retain their compartment restrictions.  A future independence or
    release route may narrow this rule only with an explicit typed contract.
    """

    if transaction.origin != "route_run":
        return
    if not isinstance(context_payload, dict):
        raise PrivacyFlowError("compiled route context must be one JSON object")
    if context_payload.get("context_schema") != "econ-theorist/compiled-context/v1":
        raise PrivacyFlowError("compiled route context has an unknown schema")

    input_records: list[dict[str, object]] = []
    for family in (
        "entities",
        "relations",
        "effective_decisions",
        "status_source_decisions",
        "blockers",
    ):
        records = context_payload.get(family)
        if not isinstance(records, list):
            raise PrivacyFlowError(
                f"compiled route context {family} must be an exact list"
            )
        if any(not isinstance(record, dict) for record in records):
            raise PrivacyFlowError(
                f"compiled route context {family} contains a malformed record"
            )
        input_records.extend(records)  # type: ignore[arg-type]

    privacy_floor = "public"
    compartment_floor: set[str] = set()
    for record in input_records:
        privacy = record.get("privacy")
        compartments = record.get("access_compartments")
        if privacy not in _PRIVACY_RANK or not isinstance(compartments, list):
            raise PrivacyFlowError(
                "compiled route context omits a privacy or compartment binding"
            )
        if any(not isinstance(item, str) for item in compartments):
            raise PrivacyFlowError(
                "compiled route context has malformed compartment bindings"
            )
        if _PRIVACY_RANK[privacy] > _PRIVACY_RANK[privacy_floor]:
            privacy_floor = privacy
        compartment_floor.update(compartments)

    labelled_outputs = [("transaction", transaction)]
    labelled_outputs.extend(
        (operation.op, output)
        for operation in transaction.operations
        if (output := _route_output_record(operation)) is not None
    )
    for label, output in labelled_outputs:
        output_privacy = getattr(output, "privacy", None)
        output_compartments = getattr(output, "access_compartments", None)
        if output_privacy not in _PRIVACY_RANK or output_compartments is None:
            raise PrivacyFlowError(
                f"route output {label} has no canonical privacy binding"
            )
        if _PRIVACY_RANK[output_privacy] < _PRIVACY_RANK[privacy_floor]:
            raise PrivacyFlowError(
                f"route output {label} privacy {output_privacy} is more "
                f"open than compiled-context floor {privacy_floor}"
            )
        if not compartment_floor.issubset(output_compartments):
            missing = sorted(compartment_floor.difference(output_compartments))
            raise PrivacyFlowError(
                f"route output {label} drops context compartments: "
                + ", ".join(missing)
            )


def _validate_operational_provenance(
    layout: StoreLayout,
    transaction: Transaction,
    base_snapshot: Snapshot | None,
) -> None:
    if transaction.origin != "route_run":
        return
    if base_snapshot is None:
        raise ChainIntegrityError("route provenance requires a canonical base snapshot")
    assert transaction.route_id is not None
    assert transaction.route_run_hash is not None
    store = ObjectStore(layout)
    expected = {
        "run": transaction.route_run_hash,
        "manifest": transaction.context_manifest_hash,
        "context": transaction.compiled_context_hash,
    }
    try:
        data = {
            label: store.read_bytes("provenance", digest, verify=True)
            for label, digest in expected.items()
            if digest is not None
        }
    except RuntimeStoreError as exc:
        raise ChainIntegrityError(
            "committed transaction lacks content-addressed provenance"
        ) from exc
    try:
        run = RouteRun.model_validate_json(data["run"], strict=True)
        manifest = ContextManifest.model_validate_json(data["manifest"], strict=True)
        context_payload = json.loads(data["context"].decode("utf-8"))
    except PydanticValidationError as exc:
        raise ChainIntegrityError("committed run provenance fails its strict schema") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ChainIntegrityError("committed compiled context is not UTF-8 JSON") from exc
    if (
        canonical_json_bytes(run) != data["run"]
        or canonical_json_bytes(manifest) != data["manifest"]
        or canonical_json_bytes(context_payload) != data["context"]
    ):
        raise ChainIntegrityError("committed run provenance is not canonical JSON")
    if (
        run.status != "running"
        or run.route_run_id != transaction.route_run_id
        or run.project_id != transaction.project_id
        or run.base_revision != transaction.base_revision
        or run.route_id != transaction.route_id
        or run.actor != transaction.actor
        or manifest.project_id != transaction.project_id
        or manifest.route_id != transaction.route_id
        or manifest.route_version != run.route_version
        or manifest.actor != run.actor
        or manifest.purpose != run.purpose
        or manifest.compartments != run.compartments
        or manifest.privacy_clearance != run.privacy_clearance
        or manifest.focus_entity_ids != run.focus_entity_ids
        or manifest.created_at != run.created_at
        or run.context_hash != transaction.compiled_context_hash
        or manifest.context_manifest_id != run.context_manifest_id
        or manifest.source_head != transaction.base_revision
        or manifest.context_hash != transaction.compiled_context_hash
    ):
        raise ChainIntegrityError(
            "committed transaction and route/context provenance disagree"
        )

    try:
        route = route_spec(transaction.route_id)
    except Exception as exc:
        raise ChainIntegrityError("committed transaction names an invalid route") from exc
    if (
        route.availability != "enabled"
        or route.route_version != run.route_version
        or run.purpose not in route.allowed_purposes
        or not set(route.required_compartments).issubset(run.compartments)
        or manifest.route_registry_hash != ROUTE_REGISTRY_HASH
        or manifest.decision_registry_version != DECISION_REGISTRY_VERSION
        or manifest.validator_version != VALIDATOR_VERSION
        or manifest.selector_version != SELECTOR_VERSION
        or manifest.kernel_version != KERNEL_VERSION
        or manifest.kernel_hash != KERNEL_HASH
        or manifest.instruction_bundle_id != route.instruction_bundle_id
        or manifest.instruction_bundle_hash != route.instruction_bundle_hash
        or manifest.isolation_policy != ISOLATION_POLICY
        or manifest.write_allowlist != route.allowed_operations
    ):
        raise ChainIntegrityError(
            "committed route provenance differs from the pinned route contract"
        )
    try:
        compiled = compile_context(
            base_snapshot,
            route=route,
            actor=run.actor,
            purpose=run.purpose,
            compartments=run.compartments,
            privacy_clearance=run.privacy_clearance,
            focus_entity_ids=run.focus_entity_ids,
            budget_units=manifest.budget_units,
        )
        expected_manifest = make_context_manifest(
            compiled,
            context_manifest_id=manifest.context_manifest_id,
            snapshot=base_snapshot,
            route=route,
            actor=run.actor,
            purpose=run.purpose,
            compartments=run.compartments,
            privacy_clearance=run.privacy_clearance,
            focus_entity_ids=run.focus_entity_ids,
            budget_units=manifest.budget_units,
            created_at=manifest.created_at,
        )
    except (EconTheoristError, RuntimeError, ValueError) as exc:
        raise ChainIntegrityError(
            "committed route provenance cannot be reproduced from its base"
        ) from exc
    if compiled.encoded != data["context"]:
        raise ChainIntegrityError(
            "committed compiled context is not the deterministic base projection"
        )
    if canonical_json_bytes(expected_manifest) != data["manifest"]:
        raise ChainIntegrityError(
            "committed context manifest is not the deterministic base projection"
        )
    expected_run = run.model_copy(update={"context_hash": compiled.context_hash})
    if canonical_json_bytes(expected_run) != data["run"]:
        raise ChainIntegrityError(
            "committed route run is not the deterministic creation record"
        )
    try:
        validate_route_context_output_flow(transaction, context_payload)
    except PrivacyFlowError as exc:
        raise ChainIntegrityError(
            "committed route output violates its compiled-context privacy join"
        ) from exc


def _validate_route_transaction_contract(transaction: Transaction) -> None:
    """Enforce route write/authority policy inside canonical validation."""

    if transaction.origin != "route_run":
        return
    assert transaction.route_id is not None
    try:
        route = route_spec(transaction.route_id)
    except Exception as exc:
        raise CandidateValidationError(
            f"route_run transaction names an invalid route: {transaction.route_id}"
        ) from exc
    if route.availability != "enabled":
        raise CandidateValidationError(
            f"route {route.route_id} is not enabled in Phase 1"
        )
    disallowed = sorted(
        {operation.op for operation in transaction.operations}
        - set(route.allowed_operations)
    )
    if disallowed:
        raise CandidateValidationError(
            f"route {route.route_id} cannot commit operations: "
            + ", ".join(disallowed)
        )
    for operation in transaction.operations:
        if not isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp)):
            continue
        decision = operation.decision
        if (
            decision.status != "proposed"
            and AUTHORITY_RANK[decision.required_authority]
            > AUTHORITY_RANK[route.authority_ceiling]
        ):
            raise CandidateValidationError(
                f"route {route.route_id} ceiling {route.authority_ceiling} "
                f"cannot exercise {decision.required_authority} Decision authority"
            )


def _entity_index(
    entities: list[EntityVersion] | tuple[EntityVersion, ...],
) -> dict[tuple[str, int], EntityVersion]:
    index: dict[tuple[str, int], EntityVersion] = {}
    for entity in entities:
        key = (entity.entity_id, entity.version)
        if key in index:
            raise ReferentialIntegrityError(
                f"duplicate entity version {entity.entity_id}@{entity.version}"
            )
        index[key] = entity
    return index


def _relation_index(
    relations: list[RelationVersion] | tuple[RelationVersion, ...],
) -> dict[tuple[str, int], RelationVersion]:
    index: dict[tuple[str, int], RelationVersion] = {}
    for relation in relations:
        key = (relation.relation_id, relation.version)
        if key in index:
            raise ReferentialIntegrityError(
                f"duplicate relation version {relation.relation_id}@{relation.version}"
            )
        index[key] = relation
    return index


def _decision_index(
    decisions: list[Decision] | tuple[Decision, ...],
) -> dict[tuple[str, int], Decision]:
    index: dict[tuple[str, int], Decision] = {}
    for decision in decisions:
        key = (decision.decision_id, decision.version)
        if key in index:
            raise ReferentialIntegrityError(
                f"duplicate Decision version {decision.decision_id}@{decision.version}"
            )
        index[key] = decision
    return index


def _artifact_index(
    artifacts: list[ArtifactRegistration]
    | tuple[ArtifactRegistration, ...],
) -> dict[tuple[str, int], ArtifactRegistration]:
    index: dict[tuple[str, int], ArtifactRegistration] = {}
    for artifact in artifacts:
        key = (artifact.artifact_id, artifact.version)
        if key in index:
            raise ReferentialIntegrityError(
                f"duplicate artifact version {artifact.artifact_id}@{artifact.version}"
            )
        index[key] = artifact
    return index


def _blocker_index(
    blockers: list[RiskOrBlocker] | tuple[RiskOrBlocker, ...],
) -> dict[str, RiskOrBlocker]:
    index: dict[str, RiskOrBlocker] = {}
    for blocker in blockers:
        if blocker.blocker_id in index:
            raise ReferentialIntegrityError(
                f"duplicate canonical blocker ID {blocker.blocker_id!r}"
            )
        index[blocker.blocker_id] = blocker
    return index


def _resolve_canonical_object_ref(
    reference: CanonicalObjectRef,
    *,
    entities: dict[tuple[str, int], EntityVersion],
    relations: dict[tuple[str, int], RelationVersion],
    decisions: dict[tuple[str, int], Decision],
    artifacts: dict[tuple[str, int], ArtifactRegistration],
    blockers: dict[str, RiskOrBlocker],
) -> PrivacyObject:
    """Resolve one typed exact ref and verify artifact-byte identity."""

    result: PrivacyObject | None
    if isinstance(reference, ArtifactDependencyRef):
        result = artifacts.get((reference.artifact_id, reference.version))
        if result is not None and result.content_hash != reference.content_hash:
            raise ReferentialIntegrityError(
                f"artifact ref {reference.artifact_id}@{reference.version} "
                "binds the wrong content hash"
            )
    elif isinstance(reference, EntityVersionRef):
        result = entities.get((reference.entity_id, reference.version))
    elif isinstance(reference, RelationVersionRef):
        result = relations.get((reference.relation_id, reference.version))
    elif isinstance(reference, DecisionVersionRef):
        result = decisions.get((reference.decision_id, reference.version))
    elif isinstance(reference, BlockerRef):
        result = blockers.get(reference.blocker_id)
    else:  # pragma: no cover - the strict model union prevents this
        raise ReferentialIntegrityError("unknown canonical object reference type")
    if result is None:
        raise ReferentialIntegrityError(
            f"canonical object ref does not resolve: {reference!r}"
        )
    return result


def _canonical_ref_key(reference: CanonicalObjectRef) -> tuple[object, ...]:
    if isinstance(reference, ArtifactDependencyRef):
        return (
            "artifact",
            reference.artifact_id,
            reference.version,
            reference.content_hash,
        )
    if isinstance(reference, EntityVersionRef):
        return ("entity", reference.entity_id, reference.version)
    if isinstance(reference, RelationVersionRef):
        return ("relation", reference.relation_id, reference.version)
    if isinstance(reference, DecisionVersionRef):
        return ("decision", reference.decision_id, reference.version)
    if isinstance(reference, BlockerRef):
        return ("blocker", reference.blocker_id)
    raise ReferentialIntegrityError("unknown canonical object reference type")


def _transaction_output_ref_keys(transaction: Transaction) -> set[tuple[object, ...]]:
    keys: set[tuple[object, ...]] = set()
    for operation in transaction.operations:
        output = _route_output_record(operation)
        if isinstance(output, EntityVersion):
            keys.add(("entity", output.entity_id, output.version))
        elif isinstance(output, RelationVersion):
            keys.add(("relation", output.relation_id, output.version))
        elif isinstance(output, Decision):
            keys.add(("decision", output.decision_id, output.version))
        elif isinstance(output, ArtifactRegistration):
            keys.add(
                (
                    "artifact",
                    output.artifact_id,
                    output.version,
                    output.content_hash,
                )
            )
        elif isinstance(output, RiskOrBlocker):
            keys.add(("blocker", output.blocker_id))
    return keys


def _validate_referenced_privacy(
    target: PrivacyObject | RouteOutcome | Transaction,
    references: tuple[CanonicalObjectRef, ...],
    *,
    entities: dict[tuple[str, int], EntityVersion],
    relations: dict[tuple[str, int], RelationVersion],
    decisions: dict[tuple[str, int], Decision],
    artifacts: dict[tuple[str, int], ArtifactRegistration],
    blockers: dict[str, RiskOrBlocker],
    transaction: Transaction,
    prior_effective: dict[tuple[str, int], Decision],
    label: str,
) -> tuple[PrivacyObject, ...]:
    resolved: list[PrivacyObject] = []
    for reference in references:
        source = _resolve_canonical_object_ref(
            reference,
            entities=entities,
            relations=relations,
            decisions=decisions,
            artifacts=artifacts,
            blockers=blockers,
        )
        _validate_privacy_flow(
            source,
            target_privacy=target.privacy,
            target_compartments=target.access_compartments,
            transaction=transaction,
            prior_effective=prior_effective,
            label=label,
        )
        resolved.append(source)
    return tuple(resolved)


def _validate_artifact_content_privacy(
    artifacts: list[ArtifactRegistration] | tuple[ArtifactRegistration, ...],
    *,
    transaction: Transaction | None = None,
    prior_effective: dict[tuple[str, int], Decision] | None = None,
    decisions: list[Decision] | tuple[Decision, ...] = (),
    changed_refs: frozenset[tuple[str, int]] | None = None,
) -> None:
    """One byte sequence keeps one floor unless its exact source was released."""

    by_hash: dict[str, list[ArtifactRegistration]] = defaultdict(list)
    for artifact in artifacts:
        by_hash[artifact.content_hash].append(artifact)
    for content_hash, registrations in by_hash.items():
        if (
            transaction is not None
            and changed_refs is not None
            and not any(
                (item.artifact_id, item.version) in changed_refs
                for item in registrations
            )
        ):
            # The base snapshot was validated before this transaction.  A
            # completed exact release is durable history; an unrelated later
            # transaction need not repeat its authority_basis.
            continue
        privacy_floor = max(
            registrations, key=lambda item: _PRIVACY_RANK[item.privacy]
        ).privacy
        compartment_floor = {
            compartment
            for item in registrations
            for compartment in item.access_compartments
        }
        for item in registrations:
            if _PRIVACY_RANK[item.privacy] < _PRIVACY_RANK[privacy_floor]:
                floor_sources = tuple(
                    source
                    for source in registrations
                    if source.privacy == privacy_floor
                )
                authorized = False
                if transaction is not None and prior_effective is not None:
                    authorized = any(
                        _privacy_declassification_authorized(
                            source,
                            item.privacy,
                            transaction,
                            prior_effective,
                        )
                        for source in floor_sources
                    )
                else:
                    authorized = any(
                        decision.decision_kind == "privacy_declassification"
                        and decision.status == "confirmed"
                        and decision.machine_outcome == "approve"
                        and decision.privacy_change is not None
                        and decision.privacy_change.from_privacy == source.privacy
                        and decision.privacy_change.to_privacy == item.privacy
                        and _privacy_subject_matches(source, decision)
                        and _PRIVACY_RANK[decision.privacy]
                        >= _PRIVACY_RANK[source.privacy]
                        and set(source.access_compartments).issubset(
                            decision.access_compartments
                        )
                        and source.privacy != "local_only"
                        for source in floor_sources
                        for decision in decisions
                    )
                if not authorized:
                    raise PrivacyFlowError(
                        f"artifact bytes {content_hash} have conflicting privacy "
                        f"labels; {item.artifact_id}@{item.version} is more open "
                        f"than {privacy_floor} without an exact release Decision"
                    )
            if not compartment_floor.issubset(item.access_compartments):
                raise PrivacyFlowError(
                    f"artifact bytes {content_hash} have conflicting compartments"
                )


def _assert_project(project_id: str, object_project_id: str, label: str) -> None:
    if object_project_id != project_id:
        raise ReferentialIntegrityError(
            f"{label} belongs to project {object_project_id!r}, not {project_id!r}"
        )


def _canonical_object_namespaces(
    *,
    entities: list[EntityVersion] | tuple[EntityVersion, ...],
    relations: list[RelationVersion] | tuple[RelationVersion, ...],
    decisions: list[Decision] | tuple[Decision, ...],
    artifacts: list[ArtifactRegistration] | tuple[ArtifactRegistration, ...],
    blockers: list[RiskOrBlocker] | tuple[RiskOrBlocker, ...],
) -> dict[str, str]:
    """Bind every bare canonical object ID to exactly one object family."""

    namespaces: dict[str, str] = {}

    def register(object_id: str, family: str) -> None:
        existing = namespaces.get(object_id)
        if existing is not None and existing != family:
            raise ReferentialIntegrityError(
                f"canonical object ID {object_id!r} is ambiguous across "
                f"{existing} and {family}"
            )
        namespaces[object_id] = family

    for entity in entities:
        register(entity.entity_id, "entity")
    for relation in relations:
        register(relation.relation_id, "relation")
    for decision in decisions:
        register(decision.decision_id, "decision")
    for artifact in artifacts:
        register(artifact.artifact_id, "artifact")

    blocker_ids: set[str] = set()
    for blocker in blockers:
        if blocker.blocker_id in blocker_ids:
            raise ReferentialIntegrityError(
                f"duplicate canonical blocker ID {blocker.blocker_id!r}"
            )
        blocker_ids.add(blocker.blocker_id)
        register(blocker.blocker_id, "blocker")
    return namespaces


def _validate_decision_references(
    decision: Decision,
    *,
    current_entity_ids: set[str],
    current_canonical_ids: set[str],
) -> None:
    """Resolve every bare Decision reference without namespace guessing."""

    if decision.subject_ref not in current_canonical_ids:
        raise ReferentialIntegrityError(
            f"Decision {decision.decision_id} subject "
            f"{decision.subject_ref!r} does not resolve"
        )
    if (
        decision.scope_ref is not None
        and decision.scope_ref not in current_entity_ids
    ):
        raise ReferentialIntegrityError(
            f"Decision {decision.decision_id} scope_ref must resolve to a "
            "current Entity"
        )
    for reference in decision.dissent_refs:
        if reference not in current_entity_ids:
            raise ReferentialIntegrityError(
                f"Decision {decision.decision_id} dissent_ref {reference!r} "
                "must resolve to a current Entity"
            )
    for reference in decision.affected_scopes:
        if reference not in current_entity_ids:
            raise ReferentialIntegrityError(
                f"Decision {decision.decision_id} affected scope {reference!r} "
                "must resolve to a current Entity"
            )
    for reference in decision.evidence_refs:
        if reference not in current_canonical_ids:
            raise ReferentialIntegrityError(
                f"Decision {decision.decision_id} evidence_ref {reference!r} "
                "does not resolve to a canonical object"
            )


def _current_privacy_objects(
    *,
    entities: dict[tuple[str, int], EntityVersion],
    relations: dict[tuple[str, int], RelationVersion],
    decisions: dict[tuple[str, int], Decision],
    artifacts: dict[tuple[str, int], ArtifactRegistration],
    blockers: dict[str, RiskOrBlocker],
    current_entities: dict[str, int],
    current_relations: dict[str, int],
    current_decisions: dict[str, int],
    current_artifacts: dict[str, int],
) -> dict[str, PrivacyObject]:
    current: dict[str, PrivacyObject] = dict(blockers)
    for index, versions in (
        (entities, current_entities),
        (relations, current_relations),
        (decisions, current_decisions),
        (artifacts, current_artifacts),
    ):
        for object_id, version in versions.items():
            current[object_id] = index[(object_id, version)]
    return current


def _validate_decision_reference_privacy(
    decision: Decision,
    *,
    current_objects: dict[str, PrivacyObject],
    transaction: Transaction,
    prior_effective: dict[tuple[str, int], Decision],
) -> tuple[PrivacyObject, ...]:
    source_ids = {
        decision.subject_ref,
        *decision.evidence_refs,
        *decision.dissent_refs,
        *decision.affected_scopes,
    }
    if decision.scope_ref is not None:
        source_ids.add(decision.scope_ref)
    sources: list[PrivacyObject] = []
    for source_id in sorted(source_ids):
        source = current_objects.get(source_id)
        if source is None:
            raise ReferentialIntegrityError(
                f"Decision {decision.decision_id} reference {source_id!r} "
                "does not resolve to a current canonical object"
            )
        _validate_privacy_flow(
            source,
            target_privacy=decision.privacy,
            target_compartments=decision.access_compartments,
            transaction=transaction,
            prior_effective=prior_effective,
            label=f"Decision {decision.decision_id}@{decision.version}",
        )
        sources.append(source)
    return tuple(sources)


def _validate_snapshot_shape(snapshot: Snapshot) -> None:
    if not snapshot.chain or snapshot.chain[-1] != snapshot.head:
        raise ChainIntegrityError("snapshot chain must be nonempty and end at head")
    if len(snapshot.transaction_ids) != len(snapshot.chain):
        raise ChainIntegrityError(
            "snapshot transaction_ids must align one-for-one with its chain"
        )
    if len(set(snapshot.transaction_ids)) != len(snapshot.transaction_ids):
        raise ChainIntegrityError("snapshot contains duplicate transaction_id values")

    entities = _entity_index(snapshot.entity_versions)
    relations = _relation_index(snapshot.relation_versions)
    decisions = _decision_index(snapshot.decisions)
    artifacts = _artifact_index(snapshot.artifacts)
    blocker_by_id = _blocker_index(snapshot.blockers)
    _validate_artifact_content_privacy(
        snapshot.artifacts,
        decisions=snapshot.decisions,
    )
    namespaces = _canonical_object_namespaces(
        entities=snapshot.entity_versions,
        relations=snapshot.relation_versions,
        decisions=snapshot.decisions,
        artifacts=snapshot.artifacts,
        blockers=snapshot.blockers,
    )

    for entity_id, version in snapshot.current_entities.items():
        if (entity_id, version) not in entities:
            raise ReferentialIntegrityError(
                f"current entity {entity_id}@{version} does not exist"
            )
    for relation_id, version in snapshot.current_relations.items():
        if (relation_id, version) not in relations:
            raise ReferentialIntegrityError(
                f"current relation {relation_id}@{version} does not exist"
            )
    for decision_id, version in snapshot.current_decisions.items():
        if (decision_id, version) not in decisions:
            raise ReferentialIntegrityError(
                f"current Decision {decision_id}@{version} does not exist"
            )
    for artifact_id, version in snapshot.current_artifacts.items():
        if (artifact_id, version) not in artifacts:
            raise ReferentialIntegrityError(
                f"current artifact {artifact_id}@{version} does not exist"
            )
    current_canonical_ids = (
        set(snapshot.current_entities)
        | set(snapshot.current_relations)
        | set(snapshot.current_decisions)
        | set(snapshot.current_artifacts)
        | {blocker.blocker_id for blocker in snapshot.blockers}
    )
    if not current_canonical_ids.issubset(namespaces):
        raise ReferentialIntegrityError(
            "snapshot current-object projection contains an unknown canonical ID"
        )
    for decision in snapshot.decisions:
        _validate_decision_references(
            decision,
            current_entity_ids=set(snapshot.current_entities),
            current_canonical_ids=current_canonical_ids,
        )
    outcome_run_ids: set[str] = set()
    for outcome in snapshot.route_outcomes:
        if outcome.route_run_id in outcome_run_ids:
            raise ReferentialIntegrityError(
                f"route run {outcome.route_run_id} has duplicate canonical outcomes"
            )
        outcome_run_ids.add(outcome.route_run_id)
        try:
            route_spec(outcome.route_id)
        except Exception as exc:
            raise ReferentialIntegrityError(
                f"RouteOutcome {outcome.route_run_id} names an unregistered route"
            ) from exc
        for reference in (*outcome.candidate_refs, *outcome.validator_report_refs):
            _resolve_canonical_object_ref(
                reference,
                entities=entities,
                relations=relations,
                decisions=decisions,
                artifacts=artifacts,
                blockers=blocker_by_id,
            )
    for blocker in snapshot.blockers:
        if blocker.required_route is not None:
            try:
                route_spec(blocker.required_route)
            except Exception as exc:
                raise ReferentialIntegrityError(
                    f"blocker {blocker.blocker_id} names an unregistered route"
                ) from exc
        for reference in blocker.affected_refs:
            _resolve_canonical_object_ref(
                reference,
                entities=entities,
                relations=relations,
                decisions=decisions,
                artifacts=artifacts,
                blockers=blocker_by_id,
            )
    for key, reference in snapshot.effective_decisions.items():
        decision = decisions.get((reference.decision_id, reference.version))
        if decision is None:
            raise ReferentialIntegrityError(
                f"effective Decision {reference.decision_id}@{reference.version} "
                "does not exist"
            )
        if decision.status not in _EFFECTIVE_DECISION_STATUSES:
            raise ReferentialIntegrityError(
                f"Decision {reference.decision_id}@{reference.version} is not effective"
            )
        if decision_scope_key(decision) != key:
            raise ReferentialIntegrityError("effective Decision scope key is corrupt")
        if reference.effective_revision not in snapshot.chain:
            raise ReferentialIntegrityError(
                "effective Decision revision is not in the canonical chain"
            )
    expected_derived = derive_entity_statuses(
        entity_versions=snapshot.entity_versions,
        relation_versions=snapshot.relation_versions,
        decisions=snapshot.decisions,
        current_entities=snapshot.current_entities,
        current_relations=snapshot.current_relations,
        effective_decisions=snapshot.effective_decisions,
    )
    if snapshot.derived_status != expected_derived:
        raise ChainIntegrityError(
            "snapshot derived_status is not the exact replay projection"
        )


def _validate_preconditions(snapshot: Snapshot | None, transaction: Transaction) -> None:
    if transaction.preconditions and snapshot is None:
        raise ReferentialIntegrityError("genesis cannot satisfy entity preconditions")
    if snapshot is None:
        return
    entities = _entity_index(snapshot.entity_versions)
    for precondition in transaction.preconditions:
        current = snapshot.current_entities.get(precondition.entity.entity_id)
        if current != precondition.entity.version:
            raise CandidateValidationError(
                f"precondition failed for {precondition.entity.entity_id}: "
                f"expected version {precondition.entity.version}, found {current}"
            )
        entity = entities.get(
            (precondition.entity.entity_id, precondition.entity.version)
        )
        if entity is None:
            raise ReferentialIntegrityError("precondition entity does not exist")
        for facet, expected_hash in precondition.expected_semantic_hashes.items():
            actual_hash = (
                authority_semantic_hash(
                    entity,
                    snapshot.decisions,
                    snapshot.effective_decisions,
                )
                if facet == "authority"
                else facet_semantic_hash(entity, facet)
            )
            if actual_hash != expected_hash:
                raise CandidateValidationError(
                    f"precondition semantic hash failed for "
                    f"{entity.entity_id}@{entity.version}:{facet}"
                )


def _validate_authority_basis(
    snapshot: Snapshot | None, transaction: Transaction
) -> dict[tuple[str, int], Decision]:
    if len(set(transaction.authority_basis)) != len(transaction.authority_basis):
        raise CandidateValidationError("authority_basis contains duplicate Decision IDs")
    if snapshot is None:
        if transaction.authority_basis:
            raise CandidateValidationError(
                "genesis authority_basis cannot cite a same-transaction Decision"
            )
        return {}
    decisions = _decision_index(snapshot.decisions)
    effective = {
        (reference.decision_id, reference.version): decisions[
            (reference.decision_id, reference.version)
        ]
        for reference in snapshot.effective_decisions.values()
    }
    effective_ids = {decision_id for decision_id, _ in effective}
    missing = set(transaction.authority_basis) - effective_ids
    if missing:
        names = ", ".join(sorted(missing))
        raise CandidateValidationError(
            "authority_basis may cite only previously effective Decisions; "
            f"invalid: {names}"
        )
    return effective


def _privacy_subject_matches(source: PrivacyObject, decision: Decision) -> bool:
    change = decision.privacy_change
    if change is None:
        return False
    subject = change.subject
    if isinstance(source, EntityVersion) and isinstance(subject, EntityPrivacySubject):
        return subject.entity == EntityVersionRef(
            entity_id=source.entity_id, version=source.version
        )
    if isinstance(source, RelationVersion) and isinstance(
        subject, RelationPrivacySubject
    ):
        return subject.relation.relation_id == source.relation_id and (
            subject.relation.version == source.version
        )
    if isinstance(source, ArtifactRegistration) and isinstance(
        subject, ArtifactPrivacySubject
    ):
        return subject.artifact.artifact_id == source.artifact_id and (
            subject.artifact.version == source.version
        )
    return False


def _privacy_declassification_authorized(
    source: PrivacyObject,
    target_privacy: str,
    transaction: Transaction,
    prior_effective: dict[tuple[str, int], Decision],
) -> bool:
    if source.privacy == "local_only":
        return False
    for (decision_id, _), decision in prior_effective.items():
        if decision_id not in transaction.authority_basis:
            continue
        change = decision.privacy_change
        if (
            decision.decision_kind == "privacy_declassification"
            and decision.status == "confirmed"
            and decision.machine_outcome == "approve"
            and change is not None
            and _privacy_subject_matches(source, decision)
            and change.from_privacy == source.privacy
            and change.to_privacy == target_privacy
            and _PRIVACY_RANK[decision.privacy] >= _PRIVACY_RANK[source.privacy]
            and set(source.access_compartments).issubset(
                decision.access_compartments
            )
        ):
            return True
    return False


def _validate_privacy_flow(
    source: PrivacyObject,
    *,
    target_privacy: str,
    target_compartments: tuple[str, ...],
    transaction: Transaction,
    prior_effective: dict[tuple[str, int], Decision],
    label: str,
) -> None:
    removed_compartments = sorted(
        set(source.access_compartments) - set(target_compartments)
    )
    if removed_compartments:
        raise PrivacyFlowError(
            f"{label} removes protected compartments: "
            + ", ".join(removed_compartments)
        )
    if _PRIVACY_RANK[target_privacy] >= _PRIVACY_RANK[source.privacy]:
        return
    if not _privacy_declassification_authorized(
        source, target_privacy, transaction, prior_effective
    ):
        raise PrivacyFlowError(
            f"{label} would flow {source.privacy} material into more open "
            f"{target_privacy} state without an exact prior approve Decision"
        )


def _validate_relation(
    relation: RelationVersion,
    *,
    entities: dict[tuple[str, int], EntityVersion],
    transaction: Transaction,
    prior_effective: dict[tuple[str, int], Decision],
    decisions: list[Decision],
    effective_decisions: dict[str, DecisionVersionRef],
) -> None:
    source = entities.get((relation.source.entity_id, relation.source.version))
    target = entities.get((relation.target.entity_id, relation.target.version))
    if source is None or target is None:
        raise ReferentialIntegrityError(
            f"relation {relation.relation_id}@{relation.version} has a missing "
            "exact entity endpoint"
        )
    if relation.upstream is not None:
        try:
            if (
                relation.upstream.facet == "authority"
                and relation.upstream.field_path is None
            ):
                actual_hash = authority_semantic_hash(
                    source, decisions, effective_decisions
                )
            else:
                actual_hash = facet_semantic_hash(
                    source,
                    relation.upstream.facet,
                    relation.upstream.field_path,
                )
        except FacetPathError as exc:
            raise ReferentialIntegrityError(str(exc)) from exc
        if actual_hash != relation.upstream.semantic_hash:
            raise ReferentialIntegrityError(
                f"relation {relation.relation_id}@{relation.version} binds an "
                "incorrect upstream semantic hash"
            )
        assert relation.downstream is not None
        try:
            facet_semantic_value(
                target,
                relation.downstream.facet,
                relation.downstream.field_path,
            )
        except FacetPathError as exc:
            raise ReferentialIntegrityError(str(exc)) from exc

    if relation.dependency_mode == "scope_sensitive":
        scope_sources: tuple[EntityVersion, ...]
        if relation.scope_overlap is not None:
            source_scope = entities.get(
                (
                    relation.scope_overlap.source_scope.entity_id,
                    relation.scope_overlap.source_scope.version,
                )
            )
            target_scope = entities.get(
                (
                    relation.scope_overlap.target_scope.entity_id,
                    relation.scope_overlap.target_scope.version,
                )
            )
            if source_scope is None or target_scope is None:
                raise ReferentialIntegrityError(
                    "typed scope overlap evidence must resolve both exact scope versions"
                )
            if (
                source.scope_ref != source_scope.entity_id
                or target.scope_ref != target_scope.entity_id
            ):
                raise ReferentialIntegrityError(
                    "typed scope overlap evidence does not bind endpoint scopes"
                )
            scope_sources = (source_scope, target_scope)
        elif not (
            relation.scope_ref is not None
            and source.scope_ref == relation.scope_ref
            and target.scope_ref == relation.scope_ref
        ):
            raise ReferentialIntegrityError(
                "scope_sensitive relation lacks exact endpoint scope equality"
            )
        else:
            scope_sources = tuple(
                entity
                for (entity_id, _), entity in entities.items()
                if entity_id == relation.scope_ref
            )
        if not scope_sources:
            raise ReferentialIntegrityError(
                "scope_sensitive equality refers to a missing scope entity"
            )
        for scope_source in scope_sources:
            _validate_privacy_flow(
                scope_source,
                target_privacy=relation.privacy,
                target_compartments=relation.access_compartments,
                transaction=transaction,
                prior_effective=prior_effective,
                label=f"relation {relation.relation_id}@{relation.version} scope",
            )

    _validate_privacy_flow(
        source,
        target_privacy=relation.privacy,
        target_compartments=relation.access_compartments,
        transaction=transaction,
        prior_effective=prior_effective,
        label=f"relation {relation.relation_id}@{relation.version}",
    )
    _validate_privacy_flow(
        target,
        target_privacy=relation.privacy,
        target_compartments=relation.access_compartments,
        transaction=transaction,
        prior_effective=prior_effective,
        label=f"relation {relation.relation_id}@{relation.version}",
    )
    _validate_privacy_flow(
        source,
        target_privacy=target.privacy,
        target_compartments=target.access_compartments,
        transaction=transaction,
        prior_effective=prior_effective,
        label=f"dependency {relation.relation_id}@{relation.version}",
    )


def _dependency_node(
    entity_id: str, version: int, facet: str, field_path: str | None
) -> DependencyNode:
    return entity_id, version, facet, field_path


def _validate_invalidating_dag(
    relations: list[RelationVersion],
    current_relations: dict[str, int],
    entities: list[EntityVersion],
    current_entities: dict[str, int],
    decisions: list[Decision],
    effective_decisions: dict[str, DecisionVersionRef],
) -> None:
    by_ref = _relation_index(relations)
    entity_by_ref = _entity_index(entities)

    def node_hash(entity: EntityVersion, node: DependencyNode) -> str:
        _, _, facet, field_path = node
        if facet == "authority" and field_path is None:
            return authority_semantic_hash(entity, decisions, effective_decisions)
        return facet_semantic_hash(entity, facet, field_path)

    def nodes_connect(left_target: DependencyNode, right_source: DependencyNode) -> bool:
        if (
            left_target[0] != right_source[0]
            or left_target[2] != right_source[2]
            or not field_paths_overlap(left_target[3], right_source[3])
        ):
            return False
        if left_target[1] == right_source[1]:
            return True
        entity_id = left_target[0]
        if right_source[1] != current_entities.get(entity_id):
            return False
        historical = entity_by_ref.get((entity_id, left_target[1]))
        current = entity_by_ref.get((entity_id, right_source[1]))
        if historical is None or current is None:
            return False
        try:
            return node_hash(historical, left_target) == node_hash(
                current,
                (entity_id, current.version, left_target[2], left_target[3]),
            )
        except FacetPathError:
            return False
    active = tuple(
        relation
        for relation_id, version in sorted(current_relations.items())
        if (relation := by_ref[(relation_id, version)]).dependency_mode
        != "trace_only"
    )
    endpoints: dict[str, tuple[DependencyNode, DependencyNode]] = {}
    for relation in active:
        assert relation.upstream is not None
        assert relation.downstream is not None
        endpoints[relation.relation_id] = (
            _dependency_node(
                relation.upstream.entity_id,
                relation.upstream.version,
                relation.upstream.facet,
                relation.upstream.field_path,
            ),
            _dependency_node(
                relation.downstream.entity_id,
                relation.downstream.version,
                relation.downstream.facet,
                relation.downstream.field_path,
            ),
        )

    adjacency: dict[str, set[str]] = {
        relation.relation_id: set() for relation in active
    }
    indegree: dict[str, int] = {
        relation.relation_id: 0 for relation in active
    }
    for left in active:
        _, left_target = endpoints[left.relation_id]
        for right in active:
            right_source, _ = endpoints[right.relation_id]
            if not nodes_connect(left_target, right_source):
                continue
            if right.relation_id not in adjacency[left.relation_id]:
                adjacency[left.relation_id].add(right.relation_id)
                indegree[right.relation_id] += 1

    ready = sorted(node for node, degree in indegree.items() if degree == 0)
    visited = 0
    while ready:
        node = ready.pop(0)
        visited += 1
        for target in sorted(adjacency.get(node, ())):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
                ready.sort()
    if visited != len(indegree):
        raise DependencyCycleError(
            "invalidating dependency projection must be acyclic"
        )


def _validate_entity_status_write(
    transaction: Transaction,
    entity: EntityVersion,
    previous: EntityVersion | None,
) -> None:
    """Keep Phase 1 L1 entity writes from impersonating scientific promotion."""

    if transaction.origin == "genesis":
        return
    if previous is not None:
        if entity.status != previous.status:
            raise CandidateValidationError(
                "stored scientific status cannot change through entity.supersede; "
                "use a reviewed status-transition policy"
            )
        return
    if entity.status.lifecycle != "proposed":
        raise CandidateValidationError(
            "non-genesis entity.create must remain lifecycle=proposed"
        )
    if entity.status.formal_validity not in {
        None,
        "not_applicable",
        "unassessed",
        "exploratory_only",
    }:
        raise CandidateValidationError(
            "entity.create cannot self-assert checked or terminal formal validity"
        )
    if entity.status.interpretation_validity not in {
        None,
        "not_applicable",
        "unassessed",
        "hypothesized",
    }:
        raise CandidateValidationError(
            "entity.create cannot self-assert validated interpretation"
        )
    if entity.status.literature is not None and (
        entity.status.literature.coverage not in {"not_started", "partial"}
        or entity.status.literature.novelty not in {"unassessed", "unresolved"}
    ):
        raise CandidateValidationError(
            "entity.create cannot self-assert current literature or differentiated novelty"
        )


def _privacy_decision_source(
    decision: Decision,
    *,
    entities: dict[tuple[str, int], EntityVersion],
    relations: dict[tuple[str, int], RelationVersion],
    artifacts: dict[tuple[str, int], ArtifactRegistration],
) -> PrivacyObject | None:
    change = decision.privacy_change
    if change is None:
        return None
    subject = change.subject
    if isinstance(subject, EntityPrivacySubject):
        return entities.get((subject.entity.entity_id, subject.entity.version))
    if isinstance(subject, RelationPrivacySubject):
        return relations.get((subject.relation.relation_id, subject.relation.version))
    assert isinstance(subject, ArtifactPrivacySubject)
    return artifacts.get((subject.artifact.artifact_id, subject.artifact.version))


def _validate_privacy_decision(
    decision: Decision,
    *,
    entities: dict[tuple[str, int], EntityVersion],
    relations: dict[tuple[str, int], RelationVersion],
    artifacts: dict[tuple[str, int], ArtifactRegistration],
) -> None:
    if decision.decision_kind != "privacy_declassification":
        return
    source = _privacy_decision_source(
        decision, entities=entities, relations=relations, artifacts=artifacts
    )
    if source is None or decision.privacy_change is None:
        raise ReferentialIntegrityError(
            "privacy Decision subject does not resolve to its exact typed version"
        )
    if decision.privacy_change.from_privacy != source.privacy:
        raise PrivacyFlowError(
            "privacy Decision from_privacy does not match its exact subject"
        )
    if _PRIVACY_RANK[decision.privacy] < _PRIVACY_RANK[source.privacy] or not set(
        source.access_compartments
    ).issubset(decision.access_compartments):
        raise PrivacyFlowError(
            "privacy Decision is itself less protected than its subject"
        )
    if source.privacy == "local_only" and decision.machine_outcome == "approve":
        raise PrivacyFlowError("local_only material cannot be declassified")


def _validate_route_outcome_references(
    outcome: RouteOutcome,
    *,
    entities: dict[tuple[str, int], EntityVersion],
    relations: dict[tuple[str, int], RelationVersion],
    decisions: dict[tuple[str, int], Decision],
    artifacts: dict[tuple[str, int], ArtifactRegistration],
    blockers: dict[str, RiskOrBlocker],
    transaction: Transaction,
    prior_effective: dict[tuple[str, int], Decision],
) -> tuple[PrivacyObject, ...]:
    references: tuple[CanonicalObjectRef, ...] = (
        *outcome.candidate_refs,
        *outcome.validator_report_refs,
    )
    return _validate_referenced_privacy(
        outcome,
        references,
        entities=entities,
        relations=relations,
        decisions=decisions,
        artifacts=artifacts,
        blockers=blockers,
        transaction=transaction,
        prior_effective=prior_effective,
        label=f"RouteOutcome {outcome.route_run_id}",
    )


def _validate_blocker_references(
    blocker: RiskOrBlocker,
    *,
    entities: dict[tuple[str, int], EntityVersion],
    relations: dict[tuple[str, int], RelationVersion],
    decisions: dict[tuple[str, int], Decision],
    artifacts: dict[tuple[str, int], ArtifactRegistration],
    blockers: dict[str, RiskOrBlocker],
    transaction: Transaction,
    prior_effective: dict[tuple[str, int], Decision],
) -> tuple[PrivacyObject, ...]:
    if blocker.required_route is not None:
        try:
            route_spec(blocker.required_route)
        except Exception as exc:
            raise ReferentialIntegrityError(
                f"blocker {blocker.blocker_id} names an unregistered exact route"
            ) from exc
    if any(
        isinstance(reference, BlockerRef)
        and reference.blocker_id == blocker.blocker_id
        for reference in blocker.affected_refs
    ):
        raise ReferentialIntegrityError("a blocker cannot affect itself")
    return _validate_referenced_privacy(
        blocker,
        blocker.affected_refs,
        entities=entities,
        relations=relations,
        decisions=decisions,
        artifacts=artifacts,
        blockers=blockers,
        transaction=transaction,
        prior_effective=prior_effective,
        label=f"blocker {blocker.blocker_id}",
    )


def _validate_transaction_privacy_envelope(
    transaction: Transaction,
    sources: list[PrivacyObject],
    *,
    prior_effective: dict[tuple[str, int], Decision],
) -> None:
    """Protect canonical intent/provenance at the join of everything it cites."""

    seen: set[int] = set()
    for source in sources:
        marker = id(source)
        if marker in seen:
            continue
        seen.add(marker)
        _validate_privacy_flow(
            source,
            target_privacy=transaction.privacy,
            target_compartments=transaction.access_compartments,
            transaction=transaction,
            prior_effective=prior_effective,
            label=f"transaction {transaction.transaction_id}",
        )


def validate_candidate(
    snapshot: Snapshot | None, transaction: Transaction
) -> Snapshot:
    """Apply one transaction to an isolated projection or reject it atomically.

    Passing ``None`` is the explicit genesis path.  The returned snapshot has
    the candidate transaction digest as its head but does not write any bytes.
    """

    validate_runtime_validator()
    digest = transaction_digest(transaction)
    if snapshot is None:
        if transaction.base_revision is not None:
            raise ChainIntegrityError("genesis transaction must have no parent")
        chain: tuple[str, ...] = ()
        transaction_ids: tuple[str, ...] = ()
        provenance_hashes: tuple[str, ...] = ()
        entities: list[EntityVersion] = []
        relations: list[RelationVersion] = []
        decisions: list[Decision] = []
        artifacts: list[ArtifactRegistration] = []
        outcomes = []
        blockers = []
        current_entities: dict[str, int] = {}
        current_relations: dict[str, int] = {}
        current_decisions: dict[str, int] = {}
        current_artifacts: dict[str, int] = {}
        effective_decisions: dict[str, EffectiveDecisionRef] = {}
    else:
        _validate_snapshot_shape(snapshot)
        if snapshot.project_id != transaction.project_id:
            raise ReferentialIntegrityError("transaction crosses project boundary")
        if transaction.base_revision != snapshot.head:
            raise ChainIntegrityError(
                f"candidate base {transaction.base_revision!r} does not match "
                f"snapshot head {snapshot.head!r}"
            )
        chain = snapshot.chain
        transaction_ids = snapshot.transaction_ids
        provenance_hashes = snapshot.provenance_hashes
        if transaction.transaction_id in transaction_ids:
            raise ChainIntegrityError(
                f"transaction_id already exists in canonical history: "
                f"{transaction.transaction_id}"
            )
        entities = list(snapshot.entity_versions)
        relations = list(snapshot.relation_versions)
        decisions = list(snapshot.decisions)
        artifacts = list(snapshot.artifacts)
        outcomes = list(snapshot.route_outcomes)
        blockers = list(snapshot.blockers)
        current_entities = dict(snapshot.current_entities)
        current_relations = dict(snapshot.current_relations)
        current_decisions = dict(snapshot.current_decisions)
        current_artifacts = dict(snapshot.current_artifacts)
        effective_decisions = dict(snapshot.effective_decisions)

    _validate_preconditions(snapshot, transaction)
    prior_effective = _validate_authority_basis(snapshot, transaction)

    if snapshot is None and transaction.origin != "genesis":
        raise CandidateValidationError("an empty store accepts only a genesis transaction")
    if snapshot is not None and transaction.origin == "genesis":
        raise CandidateValidationError("genesis cannot appear after canonical history exists")
    if transaction.origin == "human_decision":
        if transaction.actor.kind != "human" or not all(
            isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp))
            for operation in transaction.operations
        ):
            raise CandidateValidationError(
                "human_decision origin requires a human actor and Decision-only operations"
            )

    if snapshot is None:
        creates = [
            operation
            for operation in transaction.operations
            if isinstance(operation, CreateEntityOp)
        ]
        if (
            len(transaction.operations) != 1
            or len(creates) != 1
            or creates[0].entity.entity_type != "Project"
            or creates[0].entity.entity_id != transaction.project_id
            or transaction.actor.kind != "human"
            or transaction.origin != "genesis"
        ):
            raise CandidateValidationError(
                "genesis must be one human-committed Project entity whose "
                "entity_id equals project_id"
            )

    for operation in transaction.operations:
        if isinstance(
            operation, (RetireEntityOp, RetireRelationOp, StatusTransitionOp)
        ):
            raise UnsupportedOperationError(
                f"{operation.op} is fail-closed until its Phase 1 transition "
                "policy is executable"
            )

    _validate_route_transaction_contract(transaction)

    entity_by_ref = _entity_index(entities)
    relation_by_ref = _relation_index(relations)
    decision_by_ref = _decision_index(decisions)
    artifact_by_ref = _artifact_index(artifacts)
    _canonical_object_namespaces(
        entities=entities
        + [
            operation.entity
            for operation in transaction.operations
            if isinstance(operation, (CreateEntityOp, SupersedeEntityOp))
        ],
        relations=relations
        + [
            operation.relation
            for operation in transaction.operations
            if isinstance(operation, (CreateRelationOp, SupersedeRelationOp))
        ],
        decisions=decisions
        + [
            operation.decision
            for operation in transaction.operations
            if isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp))
        ],
        artifacts=artifacts
        + [
            operation.artifact
            for operation in transaction.operations
            if isinstance(operation, RegisterArtifactOp)
        ],
        blockers=blockers
        + [
            operation.blocker
            for operation in transaction.operations
            if isinstance(operation, RecordBlockerOp)
        ],
    )

    declarations = {
        (
            declaration.entity_id,
            declaration.previous_version,
            declaration.new_version,
        ): declaration.facets
        for declaration in transaction.changed_facets
    }

    touched_entities: set[str] = set()
    for operation in transaction.operations:
        if not isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            continue
        entity = operation.entity
        _assert_project(transaction.project_id, entity.project_id, "entity")
        if entity.entity_id in touched_entities:
            raise ReferentialIntegrityError(
                f"entity {entity.entity_id} is modified twice in one transaction"
            )
        touched_entities.add(entity.entity_id)
        previous: EntityVersion | None = None
        if isinstance(operation, CreateEntityOp):
            if entity.version != 1 or any(
                existing_id == entity.entity_id for existing_id, _ in entity_by_ref
            ):
                raise ReferentialIntegrityError(
                    f"entity.create requires a new {entity.entity_id}@1"
                )
            if snapshot is not None and entity.entity_type == "Project":
                raise ReferentialIntegrityError(
                    "the canonical Project entity may only be created by genesis"
                )
        else:
            previous = entity_by_ref.get(
                (operation.previous.entity_id, operation.previous.version)
            )
            if (
                previous is None
                or current_entities.get(entity.entity_id)
                != operation.previous.version
            ):
                raise ReferentialIntegrityError(
                    f"entity.supersede requires exact current predecessor "
                    f"{operation.previous.entity_id}@{operation.previous.version}"
                )
            if entity.entity_type != previous.entity_type:
                raise ReferentialIntegrityError("entity_type cannot change across versions")
            _validate_privacy_flow(
                previous,
                target_privacy=entity.privacy,
                target_compartments=entity.access_compartments,
                transaction=transaction,
                prior_effective=prior_effective,
                label=f"entity {entity.entity_id}@{entity.version}",
            )
            actual = changed_semantic_facets(previous, entity)
            declared = declarations[
                (entity.entity_id, previous.version, entity.version)
            ]
            if actual != declared:
                raise ChangedFacetError(
                    f"changed_facets for {entity.entity_id}@{entity.version} "
                    f"declared {declared!r}, actual semantic diff is {actual!r}"
                )
        _validate_entity_status_write(transaction, entity, previous)
        key = (entity.entity_id, entity.version)
        if key in entity_by_ref:
            raise ReferentialIntegrityError(
                f"entity version already exists: {entity.entity_id}@{entity.version}"
            )
        entities.append(entity)
        entity_by_ref[key] = entity
        current_entities[entity.entity_id] = entity.version

    known_entity_ids = {entity_id for entity_id, _ in entity_by_ref}
    for entity_id in touched_entities:
        entity = entity_by_ref[(entity_id, current_entities[entity_id])]
        if entity.scope_ref is not None and entity.scope_ref not in known_entity_ids:
            raise ReferentialIntegrityError(
                f"entity {entity.entity_id}@{entity.version} has a dangling scope_ref"
            )

    touched_artifacts: set[str] = set()
    for operation in transaction.operations:
        if not isinstance(operation, RegisterArtifactOp):
            continue
        artifact = operation.artifact
        _assert_project(transaction.project_id, artifact.project_id, "artifact")
        if artifact.artifact_id in touched_artifacts:
            raise ReferentialIntegrityError(
                f"artifact {artifact.artifact_id} is registered twice"
            )
        touched_artifacts.add(artifact.artifact_id)
        previous_artifact: ArtifactRegistration | None = None
        if artifact.version == 1:
            if any(
                existing_id == artifact.artifact_id
                for existing_id, _ in artifact_by_ref
            ):
                raise ReferentialIntegrityError("artifact ID already exists")
        else:
            assert artifact.supersedes is not None
            previous_key = (
                artifact.supersedes.artifact_id,
                artifact.supersedes.version,
            )
            if (
                previous_key not in artifact_by_ref
                or current_artifacts.get(artifact.artifact_id)
                != artifact.supersedes.version
            ):
                raise ReferentialIntegrityError(
                    "artifact registration requires its exact current predecessor"
                )
            previous_artifact = artifact_by_ref[previous_key]
            if (
                artifact.human_owned != previous_artifact.human_owned
                or artifact.logical_path != previous_artifact.logical_path
            ):
                raise ReferentialIntegrityError(
                    "artifact ownership and human-owned logical_path are immutable"
                )
            if artifact.human_owned and (
                artifact.expected_base_hash != previous_artifact.content_hash
            ):
                raise ReferentialIntegrityError(
                    "human-owned artifact expected_base_hash must bind its predecessor"
                )
            if (
                _PRIVACY_RANK[artifact.privacy]
                < _PRIVACY_RANK[previous_artifact.privacy]
                and artifact.content_hash != previous_artifact.content_hash
            ):
                raise PrivacyFlowError(
                    "an exact artifact release cannot relabel different bytes"
                )
            _validate_privacy_flow(
                previous_artifact,
                target_privacy=artifact.privacy,
                target_compartments=artifact.access_compartments,
                transaction=transaction,
                prior_effective=prior_effective,
                label=f"artifact {artifact.artifact_id}@{artifact.version}",
            )
        key = (artifact.artifact_id, artifact.version)
        if key in artifact_by_ref:
            raise ReferentialIntegrityError("artifact version already exists")
        artifacts.append(artifact)
        artifact_by_ref[key] = artifact
        current_artifacts[artifact.artifact_id] = artifact.version

    _validate_artifact_content_privacy(
        artifacts,
        transaction=transaction,
        prior_effective=prior_effective,
        changed_refs=frozenset(
            (operation.artifact.artifact_id, operation.artifact.version)
            for operation in transaction.operations
            if isinstance(operation, RegisterArtifactOp)
        ),
    )

    for entity_id in touched_entities:
        entity = entity_by_ref[(entity_id, current_entities[entity_id])]
        for reference in entity.artifact_refs:
            artifact = artifact_by_ref.get((reference.artifact_id, reference.version))
            if artifact is None or artifact.content_hash != reference.content_hash:
                raise ReferentialIntegrityError(
                    f"entity {entity_id} has an unresolved exact artifact dependency"
                )
            _validate_privacy_flow(
                artifact,
                target_privacy=entity.privacy,
                target_compartments=entity.access_compartments,
                transaction=transaction,
                prior_effective=prior_effective,
                label=f"entity {entity.entity_id}@{entity.version} artifact dependency",
            )

    touched_decisions: set[str] = set()
    for operation in transaction.operations:
        if not isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp)):
            continue
        decision = operation.decision
        _assert_project(transaction.project_id, decision.project_id, "Decision")
        validate_decision_authority(decision)
        _validate_privacy_decision(
            decision,
            entities=entity_by_ref,
            relations=relation_by_ref,
            artifacts=artifact_by_ref,
        )
        if transaction.actor != decision.decider:
            raise CandidateValidationError(
                "a Decision must be committed by its declared decider actor"
            )
        if decision.decision_id in touched_decisions:
            raise ReferentialIntegrityError(
                f"Decision {decision.decision_id} is modified twice"
            )
        touched_decisions.add(decision.decision_id)
        scope_key = decision_scope_key(decision)
        if isinstance(operation, RecordDecisionOp):
            if decision.version != 1 or any(
                existing_id == decision.decision_id
                for existing_id, _ in decision_by_ref
            ):
                raise ReferentialIntegrityError(
                    "decision.record requires a new Decision ID at version 1"
                )
            if (
                decision.status in _EFFECTIVE_DECISION_STATUSES
                and scope_key in effective_decisions
            ):
                raise CandidateValidationError(
                    "effective human Decisions for one kind/subject/scope must "
                    "form one supersession chain"
                )
        else:
            previous = decision_by_ref.get(
                (operation.previous.decision_id, operation.previous.version)
            )
            if (
                previous is None
                or current_decisions.get(decision.decision_id)
                != operation.previous.version
            ):
                raise ReferentialIntegrityError(
                    "decision.supersede requires its exact current predecessor"
                )
            if decision_scope_key(previous) != scope_key:
                raise CandidateValidationError(
                    "Decision kind, subject, and scope cannot change in a "
                    "supersession chain"
                )
            if previous.privacy_change != decision.privacy_change:
                raise CandidateValidationError(
                    "Decision supersession cannot change its exact privacy action"
                )
            if (
                _PRIVACY_RANK[decision.privacy] < _PRIVACY_RANK[previous.privacy]
                or not set(previous.access_compartments).issubset(
                    decision.access_compartments
                )
            ):
                raise PrivacyFlowError(
                    "Decision supersession cannot weaken privacy or compartments"
                )
            existing_effective = effective_decisions.get(scope_key)
            if (
                decision.status in _EFFECTIVE_DECISION_STATUSES
                and existing_effective is not None
                and existing_effective.decision_id != decision.decision_id
            ):
                raise CandidateValidationError(
                    "effective Decision is not connected to the existing chain"
                )
        key = (decision.decision_id, decision.version)
        if key in decision_by_ref:
            raise ReferentialIntegrityError("Decision version already exists")
        decisions.append(decision)
        decision_by_ref[key] = decision
        current_decisions[decision.decision_id] = decision.version
        if decision.status in _EFFECTIVE_DECISION_STATUSES:
            effective_decisions[scope_key] = EffectiveDecisionRef(
                decision_id=decision.decision_id,
                version=decision.version,
                effective_revision=digest,
            )
        elif decision.status == "superseded":
            current_effective = effective_decisions.get(scope_key)
            if (
                current_effective is not None
                and current_effective.decision_id == decision.decision_id
            ):
                effective_decisions.pop(scope_key)

    touched_relations: set[str] = set()
    for operation in transaction.operations:
        if not isinstance(operation, (CreateRelationOp, SupersedeRelationOp)):
            continue
        relation = operation.relation
        _assert_project(transaction.project_id, relation.project_id, "relation")
        if relation.relation_id in touched_relations:
            raise ReferentialIntegrityError(
                f"relation {relation.relation_id} is modified twice"
            )
        touched_relations.add(relation.relation_id)
        if isinstance(operation, CreateRelationOp):
            if relation.version != 1 or any(
                existing_id == relation.relation_id
                for existing_id, _ in relation_by_ref
            ):
                raise ReferentialIntegrityError(
                    "relation.create requires a new relation ID at version 1"
                )
        else:
            previous = relation_by_ref.get(
                (operation.previous.relation_id, operation.previous.version)
            )
            if (
                previous is None
                or current_relations.get(relation.relation_id)
                != operation.previous.version
            ):
                raise ReferentialIntegrityError(
                    "relation.supersede requires its exact current predecessor"
                )
            if relation.relation_type != previous.relation_type:
                raise ReferentialIntegrityError(
                    "relation_type cannot change across versions"
                )
            _validate_privacy_flow(
                previous,
                target_privacy=relation.privacy,
                target_compartments=relation.access_compartments,
                transaction=transaction,
                prior_effective=prior_effective,
                label=f"relation {relation.relation_id}@{relation.version}",
            )
        _validate_relation(
            relation,
            entities=entity_by_ref,
            transaction=transaction,
            prior_effective=prior_effective,
            decisions=decisions,
            effective_decisions=effective_decisions,
        )
        key = (relation.relation_id, relation.version)
        if key in relation_by_ref:
            raise ReferentialIntegrityError("relation version already exists")
        relations.append(relation)
        relation_by_ref[key] = relation
        current_relations[relation.relation_id] = relation.version

    _validate_invalidating_dag(
        relations,
        current_relations,
        entities,
        current_entities,
        decisions,
        effective_decisions,
    )

    blocker_ids = {blocker.blocker_id for blocker in blockers}
    outcome_run_ids = {outcome.route_run_id for outcome in outcomes}
    output_ref_keys = _transaction_output_ref_keys(transaction)
    scientific_mutations = tuple(
        operation
        for operation in transaction.operations
        if isinstance(
            operation,
            (
                CreateEntityOp,
                SupersedeEntityOp,
                CreateRelationOp,
                SupersedeRelationOp,
                RecordDecisionOp,
                SupersedeDecisionOp,
            ),
        )
    )
    for operation in transaction.operations:
        if isinstance(operation, RecordRouteOutcomeOp):
            outcome = operation.outcome
            if (
                transaction.origin != "route_run"
                or outcome.route_run_id != transaction.route_run_id
                or outcome.route_id != transaction.route_id
            ):
                raise ReferentialIntegrityError(
                    "RouteOutcome must bind the exact containing route run and route"
                )
            if outcome.route_run_id in outcome_run_ids:
                raise ReferentialIntegrityError(
                    f"route run {outcome.route_run_id} already has a canonical outcome"
                )
            if outcome.outcome in {
                "failed",
                "interrupted",
                "rejected",
                "superseded",
            } and scientific_mutations:
                raise CandidateValidationError(
                    f"{outcome.outcome} RouteOutcome cannot commit scientific mutations"
                )
            if outcome.outcome == "completed_with_candidate" and not any(
                _canonical_ref_key(reference) in output_ref_keys
                for reference in outcome.candidate_refs
            ):
                raise ReferentialIntegrityError(
                    "completed_with_candidate must reference an output of its transaction"
                )
            outcomes.append(outcome)
            outcome_run_ids.add(outcome.route_run_id)
        elif isinstance(operation, RecordBlockerOp):
            blocker = operation.blocker
            _assert_project(transaction.project_id, blocker.project_id, "blocker")
            if blocker.blocker_id in blocker_ids:
                raise ReferentialIntegrityError(
                    f"blocker ID already exists: {blocker.blocker_id}"
                )
            blockers.append(blocker)
            blocker_ids.add(blocker.blocker_id)

    namespaces = _canonical_object_namespaces(
        entities=entities,
        relations=relations,
        decisions=decisions,
        artifacts=artifacts,
        blockers=blockers,
    )
    current_canonical_ids = (
        set(current_entities)
        | set(current_relations)
        | set(current_decisions)
        | set(current_artifacts)
        | blocker_ids
    )
    if not current_canonical_ids.issubset(namespaces):
        raise ReferentialIntegrityError(
            "candidate current-object projection contains an unknown canonical ID"
        )
    blocker_by_id = _blocker_index(blockers)
    current_objects = _current_privacy_objects(
        entities=entity_by_ref,
        relations=relation_by_ref,
        decisions=decision_by_ref,
        artifacts=artifact_by_ref,
        blockers=blocker_by_id,
        current_entities=current_entities,
        current_relations=current_relations,
        current_decisions=current_decisions,
        current_artifacts=current_artifacts,
    )
    transaction_sources: list[PrivacyObject] = []
    for entity_id in touched_entities:
        entity = entity_by_ref[(entity_id, current_entities[entity_id])]
        if entity.scope_ref is None:
            continue
        scope_source = current_objects.get(entity.scope_ref)
        if not isinstance(scope_source, EntityVersion):
            raise ReferentialIntegrityError(
                f"entity {entity.entity_id}@{entity.version} scope is not a current Entity"
            )
        _validate_privacy_flow(
            scope_source,
            target_privacy=entity.privacy,
            target_compartments=entity.access_compartments,
            transaction=transaction,
            prior_effective=prior_effective,
            label=f"entity {entity.entity_id}@{entity.version} scope",
        )
        transaction_sources.append(scope_source)
    for decision_id in touched_decisions:
        decision = decision_by_ref[(decision_id, current_decisions[decision_id])]
        _validate_decision_references(
            decision,
            current_entity_ids=set(current_entities),
            current_canonical_ids=current_canonical_ids,
        )
        transaction_sources.extend(
            _validate_decision_reference_privacy(
                decision,
                current_objects=current_objects,
                transaction=transaction,
                prior_effective=prior_effective,
            )
        )

    for operation in transaction.operations:
        output = _route_output_record(operation)
        if isinstance(
            output,
            (
                EntityVersion,
                RelationVersion,
                Decision,
                ArtifactRegistration,
                RouteOutcome,
                RiskOrBlocker,
            ),
        ):
            transaction_sources.append(output)
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            for reference in operation.entity.artifact_refs:
                transaction_sources.append(
                    _resolve_canonical_object_ref(
                        reference,
                        entities=entity_by_ref,
                        relations=relation_by_ref,
                        decisions=decision_by_ref,
                        artifacts=artifact_by_ref,
                        blockers=blocker_by_id,
                    )
                )
        if isinstance(operation, (CreateRelationOp, SupersedeRelationOp)):
            for reference in (operation.relation.source, operation.relation.target):
                transaction_sources.append(
                    _resolve_canonical_object_ref(
                        reference,
                        entities=entity_by_ref,
                        relations=relation_by_ref,
                        decisions=decision_by_ref,
                        artifacts=artifact_by_ref,
                        blockers=blocker_by_id,
                    )
                )
        if isinstance(operation, RecordRouteOutcomeOp):
            transaction_sources.extend(
                _validate_route_outcome_references(
                    operation.outcome,
                    entities=entity_by_ref,
                    relations=relation_by_ref,
                    decisions=decision_by_ref,
                    artifacts=artifact_by_ref,
                    blockers=blocker_by_id,
                    transaction=transaction,
                    prior_effective=prior_effective,
                )
            )
        elif isinstance(operation, RecordBlockerOp):
            transaction_sources.extend(
                _validate_blocker_references(
                    operation.blocker,
                    entities=entity_by_ref,
                    relations=relation_by_ref,
                    decisions=decision_by_ref,
                    artifacts=artifact_by_ref,
                    blockers=blocker_by_id,
                    transaction=transaction,
                    prior_effective=prior_effective,
                )
            )
        elif isinstance(operation, SupersedeEntityOp):
            transaction_sources.append(
                entity_by_ref[(operation.previous.entity_id, operation.previous.version)]
            )
        elif isinstance(operation, SupersedeRelationOp):
            transaction_sources.append(
                relation_by_ref[
                    (operation.previous.relation_id, operation.previous.version)
                ]
            )
        elif isinstance(operation, SupersedeDecisionOp):
            transaction_sources.append(
                decision_by_ref[
                    (operation.previous.decision_id, operation.previous.version)
                ]
            )
        elif (
            isinstance(operation, RegisterArtifactOp)
            and operation.artifact.supersedes is not None
        ):
            previous = operation.artifact.supersedes
            transaction_sources.append(
                artifact_by_ref[(previous.artifact_id, previous.version)]
            )

    transaction_sources.extend(
        _validate_referenced_privacy(
            transaction,
            transaction.evidence_refs,
            entities=entity_by_ref,
            relations=relation_by_ref,
            decisions=decision_by_ref,
            artifacts=artifact_by_ref,
            blockers=blocker_by_id,
            transaction=transaction,
            prior_effective=prior_effective,
            label=f"transaction {transaction.transaction_id} evidence",
        )
    )
    for precondition in transaction.preconditions:
        source = entity_by_ref.get(
            (precondition.entity.entity_id, precondition.entity.version)
        )
        if source is None:
            raise ReferentialIntegrityError(
                "transaction precondition has an unresolved exact Entity source"
            )
        transaction_sources.append(source)
    transaction_sources.extend(
        decision
        for (decision_id, _), decision in prior_effective.items()
        if decision_id in transaction.authority_basis
    )
    _validate_transaction_privacy_envelope(
        transaction,
        transaction_sources,
        prior_effective=prior_effective,
    )

    if digest in chain:
        raise ChainIntegrityError("candidate transaction is already reachable")
    provisional = Snapshot(
        project_id=transaction.project_id,
        head=digest,
        chain=chain + (digest,),
        transaction_ids=transaction_ids + (transaction.transaction_id,),
        provenance_hashes=tuple(
            dict.fromkeys(
                (
                    *provenance_hashes,
                    *(
                        value
                        for value in (
                            transaction.route_run_hash,
                            transaction.context_manifest_hash,
                            transaction.compiled_context_hash,
                        )
                        if value is not None
                    ),
                )
            )
        ),
        entity_versions=tuple(entities),
        relation_versions=tuple(relations),
        decisions=tuple(decisions),
        artifacts=tuple(artifacts),
        route_outcomes=tuple(outcomes),
        blockers=tuple(blockers),
        current_entities=dict(sorted(current_entities.items())),
        current_relations=dict(sorted(current_relations.items())),
        current_decisions=dict(sorted(current_decisions.items())),
        current_artifacts=dict(sorted(current_artifacts.items())),
        effective_decisions=dict(sorted(effective_decisions.items())),
    )
    derived = derive_entity_statuses(
        entity_versions=provisional.entity_versions,
        relation_versions=provisional.relation_versions,
        decisions=provisional.decisions,
        current_entities=provisional.current_entities,
        current_relations=provisional.current_relations,
        effective_decisions=provisional.effective_decisions,
    )
    return Snapshot(**{
        **provisional.model_dump(mode="python"),
        "derived_status": derived,
    })


def _replay_head(active_layout: StoreLayout, head: str) -> Snapshot:
    """Replay one exact transaction head without consulting ``refs/main``."""

    validate_runtime_validator()
    store = ObjectStore(active_layout)
    reverse_chain: list[tuple[str, Transaction]] = []
    seen_digests: set[str] = set()
    seen_transaction_ids: set[str] = set()
    cursor: str | None = head
    while cursor is not None:
        if cursor in seen_digests:
            raise ChainIntegrityError("transaction parent chain contains a cycle")
        seen_digests.add(cursor)
        data = store.read_bytes("transactions", cursor, verify=True)
        try:
            transaction = Transaction.model_validate_json(data, strict=True)
        except PydanticValidationError as exc:
            raise ChainIntegrityError(
                f"transaction object {cursor} fails its strict schema"
            ) from exc
        if transaction_bytes(transaction) != data:
            raise ChainIntegrityError(
                f"transaction object {cursor} is valid JSON but not canonical bytes"
            )
        if transaction_digest(transaction) != cursor:
            raise ChainIntegrityError(
                f"transaction object filename/hash mismatch at {cursor}"
            )
        if transaction.transaction_id in seen_transaction_ids:
            raise ChainIntegrityError(
                f"duplicate transaction_id in reachable chain: "
                f"{transaction.transaction_id}"
            )
        seen_transaction_ids.add(transaction.transaction_id)
        reverse_chain.append((cursor, transaction))
        cursor = transaction.parent_transaction_hash

    snapshot: Snapshot | None = None
    for expected_digest, transaction in reversed(reverse_chain):
        try:
            _validate_operational_provenance(
                active_layout, transaction, snapshot
            )
            snapshot = validate_candidate(snapshot, transaction)
        except (CandidateValidationError, ChainIntegrityError) as exc:
            raise ChainIntegrityError(
                f"reachable transaction {expected_digest} is inadmissible: {exc}"
            ) from exc
        if snapshot.head != expected_digest:
            raise ChainIntegrityError(
                "replay-derived digest differs from reachable transaction name"
            )
    assert snapshot is not None
    if snapshot.head != head:
        raise ChainIntegrityError("replay did not terminate at refs/main")

    # Registered artifact bytes are part of the consistency oracle even though
    # registrations, rather than bytes, appear in the typed snapshot.
    for artifact in snapshot.artifacts:
        data = store.read_bytes("artifacts", artifact.content_hash, verify=True)
        if len(data) != artifact.byte_size:
            raise ChainIntegrityError(
                f"artifact {artifact.artifact_id}@{artifact.version} byte_size "
                "does not match its registered content"
            )
    return snapshot


def replay_at(layout: StoreLayout | str | Path, head_digest: str) -> Snapshot:
    """Replay a complete, content-verified chain ending at ``head_digest``.

    The target need not be the current ``refs/main``. This is required to
    reconstruct a route context pinned to a formerly current base revision.
    No orphan is promoted and no pointer or cache is written.
    """

    if not isinstance(head_digest, str) or not head_digest:
        raise ChainIntegrityError("replay_at requires one SHA-256 head digest")
    return _replay_head(_coerce_layout(layout), head_digest)


def replay(layout: StoreLayout | str | Path) -> Snapshot:
    """Traverse, verify, and replay every transaction reachable from main."""

    active_layout = _coerce_layout(layout)
    head = HeadStore(active_layout).read()
    if head is None:
        raise EmptyHistoryError("project has no committed main head")
    return _replay_head(active_layout, head)


__all__ = [
    "CandidateValidationError",
    "ChainIntegrityError",
    "ChangedFacetError",
    "DependencyCycleError",
    "EmptyHistoryError",
    "PrivacyFlowError",
    "ReferentialIntegrityError",
    "ReplayError",
    "UnsupportedOperationError",
    "decision_scope_key",
    "replay",
    "replay_at",
    "validate_candidate",
    "validate_route_context_output_flow",
]
