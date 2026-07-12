"""Operational lineage checks for blind Phase 3 re-derivations.

The authoring schema records provenance digests, but a digest written into a
payload is not evidence by itself.  This module resolves those declarations
against immutable ``ObjectStore`` bytes and the canonical ``RouteOutcome``
projection.  It deliberately has no dependency on replay or commit so both
boundaries can call it without creating an import cycle.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from ..authoring import (
    ReDerivationRecord,
    RunProvenanceBinding,
    is_packed_authoring_entity,
    parse_authoring_entity,
)
from ..codec import canonical_json_bytes
from ..errors import EconTheoristError, RuntimeStoreError
from ..models import (
    ArtifactDependencyRef,
    ContextManifest,
    CreateEntityOp,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RouteOutcome,
    RouteRun,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from ..theory import VerificationRecord, is_packed_theory_entity, parse_theory_entity
from .layout import StoreLayout
from .objects import ObjectStore


_REDERIVATION_ROUTE_ID = "verify.independent_rederivation"
_BLIND_VISIBLE_ENTITY_TYPES = frozenset(
    {"AssumptionMap", "ClaimGraph", "FormalModel", "ProofObligation"}
)


class Phase3LineageError(EconTheoristError, ValueError):
    """A declared Phase 3 lineage cannot be established from immutable state."""


@dataclass(frozen=True, slots=True)
class BoundRunProvenance:
    """One strictly decoded content-addressed run/context triple."""

    binding: RunProvenanceBinding
    run: RouteRun
    manifest: ContextManifest
    compiled_context: Mapping[str, Any]


def _entity_ref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def validate_phase3_focus_entity_evidence(
    base_snapshot: Snapshot,
    run: RouteRun,
    transaction: Transaction,
) -> None:
    """Require the route's actual focus to equal its claimed entity evidence."""

    expected: set[EntityVersionRef] = set()
    entity_index = {
        (entity.entity_id, entity.version): entity
        for entity in base_snapshot.entity_versions
    }
    for entity_id in run.focus_entity_ids:
        version = base_snapshot.current_entities.get(entity_id)
        if version is None or (entity_id, version) not in entity_index:
            raise Phase3LineageError(
                f"run focus entity is not current in its base snapshot: {entity_id}"
            )
        expected.add(EntityVersionRef(entity_id=entity_id, version=version))
    actual = {
        reference
        for reference in transaction.evidence_refs
        if isinstance(reference, EntityVersionRef)
    }
    if actual != expected:
        raise Phase3LineageError(
            "run focus and transaction EntityVersion evidence do not match exactly"
        )


def _canonical_model(data: bytes, model: type[RouteRun] | type[ContextManifest]):
    try:
        value = model.model_validate_json(data, strict=True)
    except PydanticValidationError as exc:
        raise Phase3LineageError(
            f"immutable {model.__name__} provenance fails its strict schema"
        ) from exc
    if canonical_json_bytes(value) != data:
        raise Phase3LineageError(
            f"immutable {model.__name__} provenance is not canonical JSON"
        )
    return value


def load_bound_run_provenance(
    layout: StoreLayout,
    binding: RunProvenanceBinding,
) -> BoundRunProvenance:
    """Load and cross-check one exact run binding from immutable objects only."""

    store = ObjectStore(layout)
    try:
        run_bytes = store.read_bytes(
            "provenance", binding.route_run_hash, verify=True
        )
        manifest_bytes = store.read_bytes(
            "provenance", binding.context_manifest_hash, verify=True
        )
        context_bytes = store.read_bytes(
            "provenance", binding.compiled_context_hash, verify=True
        )
    except RuntimeStoreError as exc:
        raise Phase3LineageError(
            f"run {binding.route_run_id} lacks its immutable provenance triple"
        ) from exc

    run = _canonical_model(run_bytes, RouteRun)
    manifest = _canonical_model(manifest_bytes, ContextManifest)
    assert isinstance(run, RouteRun)
    assert isinstance(manifest, ContextManifest)
    try:
        context = json.loads(context_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Phase3LineageError("compiled context is not UTF-8 JSON") from exc
    if not isinstance(context, dict) or canonical_json_bytes(context) != context_bytes:
        raise Phase3LineageError("compiled context is not one canonical JSON object")

    if (
        run.route_run_id != binding.route_run_id
        or run.context_hash != binding.compiled_context_hash
        or manifest.context_hash != binding.compiled_context_hash
        or manifest.context_manifest_id != run.context_manifest_id
        or manifest.project_id != run.project_id
        or manifest.source_head != run.base_revision
        or manifest.route_id != run.route_id
        or manifest.route_version != run.route_version
        or manifest.actor != run.actor
        or manifest.purpose != run.purpose
        or manifest.compartments != run.compartments
        or manifest.privacy_clearance != run.privacy_clearance
        or manifest.focus_entity_ids != run.focus_entity_ids
        or manifest.created_at != run.created_at
        or context.get("source_head") != manifest.source_head
        or context.get("project_id") != manifest.project_id
    ):
        raise Phase3LineageError(
            f"run {binding.route_run_id} disagrees with its bound manifest/context"
        )
    return BoundRunProvenance(
        binding=binding,
        run=run,
        manifest=manifest,
        compiled_context=context,
    )


def _entity_index(snapshot: Snapshot) -> dict[tuple[str, int], EntityVersion]:
    return {
        (entity.entity_id, entity.version): entity
        for entity in snapshot.entity_versions
    }


def _resolve_entity(snapshot: Snapshot, reference: EntityVersionRef) -> EntityVersion:
    entity = _entity_index(snapshot).get((reference.entity_id, reference.version))
    if entity is None:
        raise Phase3LineageError(
            f"lineage entity is unresolved: {reference.entity_id}@{reference.version}"
        )
    return entity


def _producer_outcomes(
    snapshot: Snapshot, reference: EntityVersionRef
) -> tuple[RouteOutcome, ...]:
    return tuple(
        outcome
        for outcome in snapshot.route_outcomes
        if reference in outcome.candidate_refs
    )


def _exact_producer(
    snapshot: Snapshot,
    reference: EntityVersionRef,
    *,
    label: str,
) -> RouteOutcome:
    matches = _producer_outcomes(snapshot, reference)
    if len(matches) != 1:
        raise Phase3LineageError(
            f"{label} must have exactly one producer RouteOutcome; found {len(matches)}"
        )
    return matches[0]


def _assert_reachable_binding(
    snapshot: Snapshot,
    binding: RunProvenanceBinding,
    *,
    label: str,
) -> None:
    reachable = set(snapshot.provenance_hashes)
    declared = {
        binding.route_run_hash,
        binding.context_manifest_hash,
        binding.compiled_context_hash,
    }
    missing = declared.difference(reachable)
    if missing:
        raise Phase3LineageError(
            f"{label} provenance is not reachable from the exact base snapshot"
        )


def _assert_binding_produces(
    provenance: BoundRunProvenance,
    outcome: RouteOutcome,
    reference: EntityVersionRef,
    *,
    label: str,
) -> None:
    if (
        provenance.run.route_run_id != outcome.route_run_id
        or provenance.run.route_id != outcome.route_id
        or reference not in outcome.candidate_refs
    ):
        raise Phase3LineageError(
            f"{label} binding is not the immutable producer of the exact entity ref"
        )


def _assert_prior_run_reachable(
    snapshot: Snapshot,
    provenance: BoundRunProvenance,
    *,
    label: str,
) -> None:
    if provenance.run.project_id != snapshot.project_id:
        raise Phase3LineageError(f"{label} crosses the project boundary")
    if provenance.run.base_revision not in snapshot.chain:
        raise Phase3LineageError(f"{label} does not descend from reachable history")


def _mapping_is_entity_ref(value: Mapping[str, Any], reference: EntityVersionRef) -> bool:
    return (
        value.get("entity_id") == reference.entity_id
        and value.get("version") == reference.version
    )


def _mapping_is_artifact_ref(
    value: Mapping[str, Any], reference: ArtifactDependencyRef
) -> bool:
    return (
        value.get("artifact_id") == reference.artifact_id
        and value.get("version") == reference.version
        and value.get("content_hash") == reference.content_hash
    )


def _contains_forbidden_reference(
    value: object,
    verification_ref: EntityVersionRef,
    proof_refs: tuple[ArtifactDependencyRef, ...],
) -> bool:
    if isinstance(value, Mapping):
        if _mapping_is_entity_ref(value, verification_ref):
            return True
        if any(_mapping_is_artifact_ref(value, item) for item in proof_refs):
            return True
        return any(
            _contains_forbidden_reference(nested, verification_ref, proof_refs)
            for nested in value.values()
        )
    if isinstance(value, (tuple, list)):
        return any(
            _contains_forbidden_reference(nested, verification_ref, proof_refs)
            for nested in value
        )
    return isinstance(value, str) and any(
        value == item.content_hash for item in proof_refs
    )


def _validate_blind_context(
    snapshot: Snapshot,
    record: ReDerivationRecord,
    provenance: BoundRunProvenance,
) -> None:
    manifest = provenance.manifest
    payload = provenance.compiled_context
    selected = manifest.selected_entity_refs
    if len(set(selected)) != len(selected):
        raise Phase3LineageError("blind context repeats a selected entity revision")

    selected_entities = tuple(_resolve_entity(snapshot, item) for item in selected)
    selected_types = tuple(entity.entity_type for entity in selected_entities)
    if any(item not in _BLIND_VISIBLE_ENTITY_TYPES for item in selected_types):
        raise Phase3LineageError(
            "blind context selects an entity outside the formal-input allowlist"
        )
    required = {
        record.claim_graph_ref,
        record.obligation_ref,
        record.formal_model_ref,
        record.assumption_map_ref,
        record.proof_author_output_ref,
    }
    if not required.issubset(set(selected)):
        raise Phase3LineageError("blind context omits an exact formal re-derivation input")
    if record.verification_record_ref in selected:
        raise Phase3LineageError("blind context selects the originating verification record")

    selector = payload.get("phase3_selector")
    packet = payload.get("phase3_role_packet")
    if (
        not isinstance(selector, Mapping)
        or selector.get("mode") != "exact_role_packet.v1"
        or selector.get("provider_must_receive_role_packet_only") is not True
        or not isinstance(packet, Mapping)
        or packet.get("packet_kind") != "independent_rederivation"
        or packet.get("actor_kind") != record.rederiver.kind
    ):
        raise Phase3LineageError("blind context lacks the sealed provider-only role packet")

    full_entities = payload.get("entities")
    if not isinstance(full_entities, list):
        raise Phase3LineageError("blind compiled context has no exact entity projection")
    projected_refs: list[EntityVersionRef] = []
    for item in full_entities:
        if not isinstance(item, Mapping):
            raise Phase3LineageError("blind entity projection is malformed")
        try:
            projected_refs.append(
                EntityVersionRef(
                    entity_id=item.get("entity_id"),
                    version=item.get("version"),
                )
            )
        except PydanticValidationError as exc:
            raise Phase3LineageError("blind entity projection has an invalid ref") from exc
    if tuple(projected_refs) != selected:
        raise Phase3LineageError(
            "blind compiled entities differ from ContextManifest.selected_entity_refs"
        )

    semantic_inputs = packet.get("semantic_inputs")
    if (
        not isinstance(semantic_inputs, list)
        or len(semantic_inputs) != len(selected_types)
        or any(not isinstance(item, Mapping) for item in semantic_inputs)
        or any(not isinstance(item.get("kind"), str) for item in semantic_inputs)
        or sorted(item.get("kind") for item in semantic_inputs) != sorted(selected_types)
    ):
        raise Phase3LineageError("blind role packet differs from the selected formal inputs")
    if (
        packet.get("artifacts") not in ([], ())
        or payload.get("phase3_artifacts") not in ([], ())
        or _contains_forbidden_reference(
            packet,
            record.verification_record_ref,
            record.excluded_proof_artifact_refs,
        )
    ):
        raise Phase3LineageError(
            "blind provider context exposes originating verification/proof evidence"
        )


def _transaction_rederivations(
    transaction: Transaction,
) -> tuple[tuple[EntityVersionRef, ReDerivationRecord], ...]:
    values: list[tuple[EntityVersionRef, ReDerivationRecord]] = []
    for operation in transaction.operations:
        if not isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            continue
        entity = operation.entity
        if entity.entity_type != "ReDerivationRecord":
            continue
        if not is_packed_authoring_entity(entity):
            raise Phase3LineageError("ReDerivationRecord output is not a packed payload")
        try:
            payload = parse_authoring_entity(entity)
        except ValueError as exc:
            raise Phase3LineageError("ReDerivationRecord output does not parse") from exc
        if not isinstance(payload, ReDerivationRecord):
            raise Phase3LineageError("authoring payload type disagrees with its envelope")
        values.append((_entity_ref(entity), payload))
    return tuple(values)


def validate_rederivation_operational_lineage(
    layout: StoreLayout,
    base_snapshot: Snapshot,
    transaction: Transaction,
    record: ReDerivationRecord,
    *,
    output_ref: EntityVersionRef,
) -> None:
    """Validate one re-derivation's exact operational and producer lineage."""

    if transaction.origin != "route_run" or transaction.route_id != _REDERIVATION_ROUTE_ID:
        raise Phase3LineageError("a ReDerivationRecord requires its native route run")
    if transaction.base_revision != base_snapshot.head:
        raise Phase3LineageError("re-derivation lineage is checked against the wrong base")
    if (
        transaction.route_run_hash is None
        or transaction.context_manifest_hash is None
        or transaction.compiled_context_hash is None
    ):
        raise Phase3LineageError("re-derivation transaction lacks exact provenance hashes")

    current_binding = RunProvenanceBinding(
        route_run_id=record.route_run_id,
        route_run_hash=record.route_run_hash,
        context_manifest_hash=record.context_manifest_hash,
        compiled_context_hash=record.compiled_context_hash,
    )
    if (
        record.rederiver != transaction.actor
        or record.route_run_id != transaction.route_run_id
        or record.route_run_hash != transaction.route_run_hash
        or record.context_manifest_hash != transaction.context_manifest_hash
        or record.compiled_context_hash != transaction.compiled_context_hash
    ):
        raise Phase3LineageError("re-derivation payload and transaction bind different runs")
    current = load_bound_run_provenance(layout, current_binding)
    if (
        current.run.actor != record.rederiver
        or current.run.route_id != _REDERIVATION_ROUTE_ID
        or current.run.project_id != base_snapshot.project_id
        or current.run.base_revision != base_snapshot.head
    ):
        raise Phase3LineageError("re-derivation run has the wrong actor, route, project, or base")
    validate_phase3_focus_entity_evidence(
        base_snapshot, current.run, transaction
    )

    transaction_outcomes = tuple(
        operation.outcome
        for operation in transaction.operations
        if isinstance(operation, RecordRouteOutcomeOp)
    )
    if (
        len(transaction_outcomes) != 1
        or transaction_outcomes[0].route_run_id != record.route_run_id
        or transaction_outcomes[0].route_id != _REDERIVATION_ROUTE_ID
        or output_ref not in transaction_outcomes[0].candidate_refs
    ):
        raise Phase3LineageError(
            "re-derivation output lacks its exact containing RouteOutcome"
        )

    verification_entity = _resolve_entity(base_snapshot, record.verification_record_ref)
    if (
        verification_entity.entity_type != "VerificationRecord"
        or not is_packed_theory_entity(verification_entity)
    ):
        raise Phase3LineageError("originating verification ref is not a packed record")
    try:
        verification = parse_theory_entity(verification_entity)
    except ValueError as exc:
        raise Phase3LineageError("originating VerificationRecord does not parse") from exc
    if not isinstance(verification, VerificationRecord) or (
        verification.verifier != record.originating_verifier
    ):
        raise Phase3LineageError(
            "originating verifier does not match the exact VerificationRecord"
        )

    origin_outcome = _exact_producer(
        base_snapshot,
        record.verification_record_ref,
        label="originating verification record",
    )
    _assert_reachable_binding(
        base_snapshot,
        record.originating_verifier_run,
        label="originating verifier run",
    )
    origin = load_bound_run_provenance(layout, record.originating_verifier_run)
    _assert_prior_run_reachable(
        base_snapshot, origin, label="originating verifier run"
    )
    _assert_binding_produces(
        origin,
        origin_outcome,
        record.verification_record_ref,
        label="originating verifier run",
    )

    proof_outcome = _exact_producer(
        base_snapshot,
        record.proof_author_output_ref,
        label="proof-author output",
    )
    _assert_reachable_binding(
        base_snapshot, record.proof_author_run, label="proof-author run"
    )
    proof = load_bound_run_provenance(layout, record.proof_author_run)
    _assert_prior_run_reachable(base_snapshot, proof, label="proof-author run")
    _assert_binding_produces(
        proof,
        proof_outcome,
        record.proof_author_output_ref,
        label="proof-author run",
    )
    if proof.run.actor != record.proof_author:
        raise Phase3LineageError("proof-author actor did not produce its declared output")

    _validate_blind_context(base_snapshot, record, current)

    expected_parent_outcomes: dict[str, RouteOutcome] = {}
    expected_parent_refs: dict[str, list[EntityVersionRef]] = {}
    for reference in current.manifest.selected_entity_refs:
        matches = _producer_outcomes(base_snapshot, reference)
        if len(matches) > 1:
            raise Phase3LineageError(
                f"selected entity has multiple producer outcomes: "
                f"{reference.entity_id}@{reference.version}"
            )
        if matches:
            expected_parent_outcomes[matches[0].route_run_id] = matches[0]
            expected_parent_refs.setdefault(matches[0].route_run_id, []).append(reference)

    declared_parents = {
        item.route_run_id: item for item in record.parent_runs
    }
    if set(declared_parents) != set(expected_parent_outcomes):
        raise Phase3LineageError(
            "re-derivation parent_runs is not the exact selected-input producer set"
        )
    if record.originating_verifier_run.route_run_id in declared_parents:
        raise Phase3LineageError("originating verifier run enters blind parent lineage")

    forbidden_outputs: set[object] = {
        record.verification_record_ref,
        *record.excluded_proof_artifact_refs,
    }
    for run_id, binding in declared_parents.items():
        _assert_reachable_binding(base_snapshot, binding, label=f"parent run {run_id}")
        parent = load_bound_run_provenance(layout, binding)
        _assert_prior_run_reachable(
            base_snapshot, parent, label=f"parent run {run_id}"
        )
        outcome = expected_parent_outcomes[run_id]
        for reference in expected_parent_refs[run_id]:
            _assert_binding_produces(
                parent,
                outcome,
                reference,
                label=f"parent run {run_id}",
            )
        if any(reference in forbidden_outputs for reference in outcome.candidate_refs):
            raise Phase3LineageError("a blind parent run produced prohibited proof evidence")
        if _contains_forbidden_reference(
            parent.compiled_context,
            record.verification_record_ref,
            record.excluded_proof_artifact_refs,
        ):
            raise Phase3LineageError("a blind parent inherited prohibited proof context")


def validate_phase3_operational_lineage(
    layout: StoreLayout,
    base_snapshot: Snapshot | None,
    transaction: Transaction,
) -> None:
    """Validate operational lineage for a native re-derivation transaction.

    Other routes are a no-op.  The native route must produce exactly one packed
    ``ReDerivationRecord``; this keeps integration at replay/commit boundaries
    deterministic and fail closed.
    """

    records = _transaction_rederivations(transaction)
    if transaction.route_id != _REDERIVATION_ROUTE_ID and not records:
        return
    if transaction.route_id != _REDERIVATION_ROUTE_ID:
        raise Phase3LineageError("ReDerivationRecord was emitted by the wrong route")
    if base_snapshot is None:
        raise Phase3LineageError("blind re-derivation cannot be a genesis transaction")
    if len(records) != 1:
        raise Phase3LineageError(
            "verify.independent_rederivation must emit exactly one ReDerivationRecord"
        )
    output_ref, record = records[0]
    validate_rederivation_operational_lineage(
        layout,
        base_snapshot,
        transaction,
        record,
        output_ref=output_ref,
    )


__all__ = [
    "BoundRunProvenance",
    "Phase3LineageError",
    "load_bound_run_provenance",
    "validate_phase3_operational_lineage",
    "validate_rederivation_operational_lineage",
]
