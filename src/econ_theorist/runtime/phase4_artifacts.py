"""Runtime verification of Phase 4 executable artifact protocols."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError as PydanticValidationError

from .. import authoring as a
from .. import profile_craft as pc
from ..authoring_validation import (
    AuthoringValidationError,
    reproducible_harness_artifact_bytes,
)
from ..codec import canonical_json_bytes, object_digest
from ..errors import EconTheoristError, RuntimeStoreError
from ..models import (
    ArtifactDependencyRef,
    ArtifactRegistration,
    CreateEntityOp,
    EntityVersion,
    EntityVersionRef,
    RegisterArtifactOp,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from ..policy import V4_NATIVE_ROUTE_IDS
from ..profile_craft_execution import (
    MANDATORY_MUTATION_KINDS,
    MutationReplayEntry,
    PhraseLeakAuditArtifact,
    PredicateMutationReplayArtifact,
    PredicateMutationResultArtifact,
    PredicateWitnessArtifact,
    ProfileCraftExecutionError,
    build_mutation_replay_artifact,
    build_phrase_leak_audit,
    build_predicate_witness_artifact,
    predicate_fragment_hash,
    replay_contract_mutations,
)
from .layout import StoreLayout
from .objects import ObjectStore


class Phase4ArtifactError(EconTheoristError, ValueError):
    """A Phase 4 record disagrees with immutable executable evidence."""


def _walk_artifact_refs(value: object) -> Iterable[ArtifactDependencyRef]:
    if isinstance(value, ArtifactDependencyRef):
        yield value
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from _walk_artifact_refs(getattr(value, field_name))
        return
    if isinstance(value, Mapping):
        for item in value.values():
            yield from _walk_artifact_refs(item)
        return
    if isinstance(value, (tuple, list)):
        for item in value:
            yield from _walk_artifact_refs(item)


def _registrations(
    base: Snapshot, transaction: Transaction
) -> dict[tuple[str, int], ArtifactRegistration]:
    result = {(item.artifact_id, item.version): item for item in base.artifacts}
    for operation in transaction.operations:
        if not isinstance(operation, RegisterArtifactOp):
            continue
        key = (operation.artifact.artifact_id, operation.artifact.version)
        if key in result:
            raise Phase4ArtifactError("Phase 4 transaction repeats an artifact version")
        result[key] = operation.artifact
    return result


def _entities(
    base: Snapshot, transaction: Transaction
) -> dict[tuple[str, int], EntityVersion]:
    result = {(item.entity_id, item.version): item for item in base.entity_versions}
    for operation in transaction.operations:
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            key = (operation.entity.entity_id, operation.entity.version)
            if key in result:
                raise Phase4ArtifactError("Phase 4 transaction repeats an entity version")
            result[key] = operation.entity
    return result


def _entity(
    entities: Mapping[tuple[str, int], EntityVersion], reference: EntityVersionRef
) -> EntityVersion:
    result = entities.get((reference.entity_id, reference.version))
    if result is None:
        raise Phase4ArtifactError("Phase 4 exact entity reference is unresolved")
    return result


def _read(
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    reference: ArtifactDependencyRef,
) -> bytes:
    registration = registrations.get((reference.artifact_id, reference.version))
    if registration is None or registration.content_hash != reference.content_hash:
        raise Phase4ArtifactError("Phase 4 artifact is unregistered or hash-mismatched")
    try:
        data = ObjectStore(layout).read_bytes(
            "artifacts", reference.content_hash, verify=True
        )
    except RuntimeStoreError as exc:
        raise Phase4ArtifactError(
            "Phase 4 artifact bytes are absent from immutable storage"
        ) from exc
    if len(data) != registration.byte_size:
        raise Phase4ArtifactError("Phase 4 artifact byte_size mismatches")
    return data


def _parse(data: bytes, model, label: str):
    try:
        value = model.model_validate_json(data, strict=True)
    except PydanticValidationError as exc:
        raise Phase4ArtifactError(f"{label} fails its strict byte protocol") from exc
    if canonical_json_bytes(value) != data:
        raise Phase4ArtifactError(f"{label} is not canonical JSON")
    return value


@dataclass(frozen=True, slots=True)
class _ContractExecution:
    predicate_bytes: bytes
    domain_verified: bool
    antecedent_verified: bool
    falsifying_verified: bool
    replay_entries: tuple[MutationReplayEntry, ...]
    unencoded_assumption_clause_ids: tuple[str, ...]


def _assurance_receipt(
    contract: pc.ObligationPredicateContract,
    *,
    entities: Mapping[tuple[str, int], EntityVersion],
) -> tuple[a.AssuranceBundle, a.ToolHarnessReceipt]:
    assurance_entity = _entity(entities, contract.assurance_bundle_ref)
    try:
        assurance = a.parse_authoring_entity(assurance_entity)
    except (TypeError, ValueError) as exc:
        raise Phase4ArtifactError("contract assurance bundle does not parse") from exc
    if not isinstance(assurance, a.AssuranceBundle):
        raise Phase4ArtifactError("contract does not reference an AssuranceBundle")
    if contract.assurance_bundle_hash != object_digest(assurance):
        raise Phase4ArtifactError("contract assurance bundle hash mismatches")
    obligation_receipts = tuple(
        item
        for item in assurance.tool_receipts
        if item.obligation_ref == contract.obligation_ref
    )
    if len(obligation_receipts) != 1:
        raise Phase4ArtifactError(
            "Phase 4 requires one unambiguous executed receipt per obligation"
        )
    receipts = tuple(
        item for item in assurance.tool_receipts if item.receipt_id == contract.receipt_id
    )
    if len(receipts) != 1:
        raise Phase4ArtifactError("contract receipt is not unique in its assurance bundle")
    receipt = receipts[0]
    if contract.receipt_hash != object_digest(receipt):
        raise Phase4ArtifactError("contract receipt hash mismatches")
    if receipt.obligation_ref != contract.obligation_ref:
        raise Phase4ArtifactError("contract receipt belongs to another obligation")
    if receipt.claim_graph_ref != contract.claim_graph_ref:
        raise Phase4ArtifactError("contract receipt belongs to another claim graph")
    if contract.predicate_artifact_ref != receipt.input_ref:
        raise Phase4ArtifactError(
            "predicate_artifact_ref must reuse the assurance receipt canonical input"
        )
    if contract.code_ref != receipt.code_ref:
        raise Phase4ArtifactError("predicate code_ref must reuse the pinned harness code")
    if not isinstance(receipt.reproducible_evidence, a.CounterexampleScanEvidence):
        raise Phase4ArtifactError(
            "Phase 4 predicate execution currently requires a finite exact relation scan"
        )
    return assurance, receipt


def _validate_contract_execution(
    contract: pc.ObligationPredicateContract,
    *,
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    entities: Mapping[tuple[str, int], EntityVersion],
) -> _ContractExecution:
    _, receipt = _assurance_receipt(contract, entities=entities)
    try:
        reproduced = reproducible_harness_artifact_bytes(receipt)
    except AuthoringValidationError as exc:
        raise Phase4ArtifactError("assurance receipt no longer reproduces") from exc
    bindings = {
        "code": receipt.code_ref,
        "input": receipt.input_ref,
        "output": receipt.output_ref,
        "receipt": receipt.receipt_ref,
        "witness": receipt.witness_ref,
    }
    for kind, expected_bytes in reproduced.items():
        reference = bindings.get(kind)
        if reference is None:
            raise Phase4ArtifactError(f"assurance receipt omits reproduced {kind} bytes")
        if _read(layout, registrations, reference) != expected_bytes:
            raise Phase4ArtifactError(
                f"assurance {kind} artifact disagrees with independent reproduction"
            )
    predicate_bytes = reproduced["input"]
    if _read(layout, registrations, contract.predicate_artifact_ref) != predicate_bytes:
        raise Phase4ArtifactError("contract predicate bytes are not the receipt input")

    for mapping in contract.clause_mappings:
        try:
            expected_hash = predicate_fragment_hash(
                predicate_bytes,
                obligation_clause_id=mapping.obligation_clause_id,
                relation=mapping.relation,
                pointers=mapping.predicate_json_pointers,
            )
        except ProfileCraftExecutionError as exc:
            raise Phase4ArtifactError(
                f"predicate clause locator is not executable: {mapping.obligation_clause_id}"
            ) from exc
        if mapping.predicate_fragment_hash != expected_hash:
            raise Phase4ArtifactError(
                f"predicate clause fragment hash mismatches: {mapping.obligation_clause_id}"
            )

    mutation_kinds = tuple(item.mutation_kind for item in contract.mutation_tests)
    missing = set(MANDATORY_MUTATION_KINDS).difference(mutation_kinds)
    if missing:
        raise Phase4ArtifactError(
            "predicate contract omits mandatory executable mutants: "
            + ", ".join(sorted(missing))
        )

    domain_verified = False
    antecedent_verified = False
    falsifying_verified = False
    for witness in contract.witnesses:
        artifact_bytes = _read(layout, registrations, witness.artifact_ref)
        artifact = _parse(
            artifact_bytes, PredicateWitnessArtifact, "predicate witness"
        )
        assignment_bytes = _read(layout, registrations, artifact.assignment_ref)
        try:
            expected = build_predicate_witness_artifact(
                contract_id=contract.contract_id,
                witness_id=witness.witness_id,
                witness_kind=witness.witness_kind,
                case_id=witness.case_id,
                assignment_ref=artifact.assignment_ref,
                assignment_bytes=assignment_bytes,
                predicate_bytes=predicate_bytes,
                limitations=artifact.limitations,
            )
        except ProfileCraftExecutionError as exc:
            raise Phase4ArtifactError(
                f"predicate witness does not execute: {witness.witness_id}"
            ) from exc
        if artifact != expected:
            raise Phase4ArtifactError(
                f"predicate witness self-report disagrees with execution: {witness.witness_id}"
            )
        domain_verified |= witness.witness_kind == "domain_member"
        # The current witness protocol deliberately cannot set this flag: the
        # finite relation scan does not expose an independently executable
        # antecedent.  An antecedent-satisfying claim therefore fails in the
        # builder above instead of inheriting the whole relation's truth value.
        antecedent_verified |= witness.witness_kind == "antecedent_satisfying"
        falsifying_verified |= witness.witness_kind == "predicate_falsifying"

    def read_artifact(reference: ArtifactDependencyRef) -> bytes:
        return _read(layout, registrations, reference)

    try:
        replay_entries = replay_contract_mutations(
            contract, predicate_bytes=predicate_bytes, read_artifact=read_artifact
        )
    except ProfileCraftExecutionError as exc:
        raise Phase4ArtifactError("predicate mutant replay failed") from exc
    unencoded = tuple(
        item.obligation_clause_id
        for item in contract.clause_mappings
        if item.clause_kind == "assumption" and item.relation == "omitted"
    )
    if any(
        item.mutation_kind == "omitted_assumption"
        and item.execution_outcome == "unencoded_assumption_not_executable"
        for item in replay_entries
    ) and not unencoded:
        raise Phase4ArtifactError(
            "omitted-assumption execution requires an honestly omitted assumption mapping"
        )
    if contract.antecedent_satisfiable != antecedent_verified:
        raise Phase4ArtifactError("contract antecedent_satisfiable is a false self-report")
    if contract.predicate_can_return_false != falsifying_verified:
        raise Phase4ArtifactError("contract predicate_can_return_false is a false self-report")
    return _ContractExecution(
        predicate_bytes=predicate_bytes,
        domain_verified=domain_verified,
        antecedent_verified=antecedent_verified,
        falsifying_verified=falsifying_verified,
        replay_entries=replay_entries,
        unencoded_assumption_clause_ids=unencoded,
    )


def _validate_audit_execution(
    audit: pc.PredicateMappingAudit,
    *,
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    entities: Mapping[tuple[str, int], EntityVersion],
) -> None:
    contract_entity = _entity(entities, audit.contract_ref)
    try:
        contract = pc.parse_profile_craft_entity(contract_entity)
    except (TypeError, ValueError) as exc:
        raise Phase4ArtifactError("mapping audit contract does not parse") from exc
    if not isinstance(contract, pc.ObligationPredicateContract):
        raise Phase4ArtifactError("mapping audit does not reference a predicate contract")
    if audit.contract_hash != object_digest(contract):
        raise Phase4ArtifactError("mapping audit contract hash mismatches")
    execution = _validate_contract_execution(
        contract,
        layout=layout,
        registrations=registrations,
        entities=entities,
    )

    replay_bytes = _read(layout, registrations, audit.mutation_replay_ref)
    actual_replay = _parse(
        replay_bytes,
        PredicateMutationReplayArtifact,
        "predicate mutation replay",
    )

    def read_artifact(reference: ArtifactDependencyRef) -> bytes:
        return _read(layout, registrations, reference)

    try:
        expected_replay = build_mutation_replay_artifact(
            audit_id=audit.audit_id,
            contract_ref=audit.contract_ref,
            contract_hash=audit.contract_hash,
            contract=contract,
            predicate_bytes=execution.predicate_bytes,
            read_artifact=read_artifact,
            limitations=actual_replay.limitations,
        )
    except ProfileCraftExecutionError as exc:
        raise Phase4ArtifactError("mapping audit mutant replay does not reproduce") from exc
    if actual_replay != expected_replay:
        raise Phase4ArtifactError("mapping audit replay summary is a false self-report")
    mutation_ids = tuple(item.mutation_id for item in contract.mutation_tests)
    if audit.registered_mutation_ids != mutation_ids:
        raise Phase4ArtifactError("mapping audit registered mutant order mismatches")
    if audit.replayed_mutation_ids != mutation_ids:
        raise Phase4ArtifactError("mapping audit replayed mutant order mismatches")
    replay_passed = (
        expected_replay.executable_controls_passed
        and expected_replay.unexecutable_controls_accounted
    )
    if audit.mutation_replay_passed != replay_passed:
        raise Phase4ArtifactError("mapping audit replay-pass flag is false")
    if audit.unexecutable_mutation_ids != expected_replay.unexecutable_mutation_ids:
        raise Phase4ArtifactError("mapping audit unexecutable-control IDs are false")
    if audit.domain_witness_verified != execution.domain_verified:
        raise Phase4ArtifactError("mapping audit domain-witness flag is false")
    if audit.antecedent_witness_verified != execution.antecedent_verified:
        raise Phase4ArtifactError("mapping audit antecedent flag is false")
    if audit.falsifying_witness_verified != execution.falsifying_verified:
        raise Phase4ArtifactError("mapping audit falsifying flag is false")
    if execution.unencoded_assumption_clause_ids:
        if audit.verdict != "approved_partial":
            raise Phase4ArtifactError(
                "an unencoded assumption forbids exact predicate approval"
            )
        warned = {
            clause_id
            for finding in audit.findings
            if finding.severity == "warning"
            for clause_id in finding.affected_clause_ids
        }
        if not set(execution.unencoded_assumption_clause_ids).issubset(warned):
            raise Phase4ArtifactError(
                "approved partial mapping must warn about every unencoded assumption"
            )
    if audit.verdict == "approved_exact" and expected_replay.unexecutable_mutation_ids:
        raise Phase4ArtifactError(
            "exact predicate approval forbids unexecutable mutation controls"
        )


def _validate_phrase_execution(
    assessment: pc.CraftRealizationAssessment,
    *,
    layout: StoreLayout,
    registrations: Mapping[tuple[str, int], ArtifactRegistration],
    entities: Mapping[tuple[str, int], EntityVersion],
) -> None:
    selection_entity = _entity(entities, assessment.selection_manifest_ref)
    try:
        selection = pc.parse_profile_craft_entity(selection_entity)
    except (TypeError, ValueError) as exc:
        raise Phase4ArtifactError("craft assessment selection does not parse") from exc
    if not isinstance(selection, pc.CraftSelectionManifest):
        raise Phase4ArtifactError("craft assessment does not reference a selection")
    if assessment.selection_manifest_hash != object_digest(selection):
        raise Phase4ArtifactError("craft assessment selection hash mismatches")
    if assessment.selected_move_refs != selection.selected_move_refs:
        raise Phase4ArtifactError("craft assessment selected moves mismatch")
    manuscript_bytes = _read(
        layout, registrations, assessment.manuscript_artifact_ref
    )
    audit_bytes = _read(layout, registrations, assessment.phrase_leak_audit_ref)
    actual = _parse(audit_bytes, PhraseLeakAuditArtifact, "craft phrase audit")
    try:
        expected = build_phrase_leak_audit(
            assessment_id=assessment.assessment_id,
            manuscript_artifact_ref=assessment.manuscript_artifact_ref,
            manuscript_bytes=manuscript_bytes,
            selected_move_refs=assessment.selected_move_refs,
            normalized_ngram_size=actual.normalized_ngram_size,
        )
    except ProfileCraftExecutionError as exc:
        raise Phase4ArtifactError("craft phrase audit does not execute") from exc
    if actual != expected:
        raise Phase4ArtifactError("craft phrase audit is a false self-report")
    if assessment.phrase_leak_audit_outcome != expected.outcome:
        raise Phase4ArtifactError("craft assessment phrase outcome is false")


def validate_phase4_operational_artifacts(
    layout: StoreLayout,
    base_snapshot: Snapshot | None,
    transaction: Transaction,
) -> None:
    """Resolve and independently reproduce every Phase 4 operational artifact."""

    if transaction.route_id not in V4_NATIVE_ROUTE_IDS:
        return
    if base_snapshot is None:
        raise Phase4ArtifactError("Phase 4 routes cannot run at genesis")
    registrations = _registrations(base_snapshot, transaction)
    entities = _entities(base_snapshot, transaction)
    produced: list[pc.ProfileCraftPayload] = []
    for operation in transaction.operations:
        if not isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            continue
        if not pc.is_packed_profile_craft_entity(operation.entity):
            continue
        try:
            produced.append(pc.parse_profile_craft_entity(operation.entity))
        except (TypeError, ValueError) as exc:
            raise Phase4ArtifactError("Phase 4 artifact owner does not parse") from exc

    for payload in produced:
        for reference in _walk_artifact_refs(payload):
            _read(layout, registrations, reference)
        if isinstance(payload, pc.ObligationPredicateContract):
            _validate_contract_execution(
                payload,
                layout=layout,
                registrations=registrations,
                entities=entities,
            )
        elif isinstance(payload, pc.PredicateMappingAudit):
            _validate_audit_execution(
                payload,
                layout=layout,
                registrations=registrations,
                entities=entities,
            )
        elif isinstance(payload, pc.CraftRealizationAssessment):
            _validate_phrase_execution(
                payload,
                layout=layout,
                registrations=registrations,
                entities=entities,
            )


__all__ = [
    "MutationReplayEntry",
    "Phase4ArtifactError",
    "PhraseLeakAuditArtifact",
    "PredicateMutationReplayArtifact",
    "PredicateMutationResultArtifact",
    "PredicateWitnessArtifact",
    "validate_phase4_operational_artifacts",
]
