"""Fail-closed semantic validation for the Phase 3 authoring slice.

``authoring`` owns strict payload *shape*.  This module owns facts that can
only be established against an exact projection: reference resolution,
freshness, actor isolation, route topology, assurance, and review closure.

The two derived predicates in this module are deliberately not stored
authority.  A payload cannot make either predicate true by saying that it is
true; the validators recompute the result from the exact revisions in the
snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import re
from typing import Iterable, Mapping, Sequence

from pydantic import BaseModel

from . import authoring as a
from . import theory as t
from .assurance import (
    AssuranceHarnessError,
    ExactAssignment,
    ExactPolynomial,
    ExactPolynomialRelation,
    run_exact_polynomial_relation_scan,
    run_polynomial_identity,
    verify_exact_polynomial_relation_scan,
    verify_polynomial_identity_run,
)
from .codec import canonical_json_bytes, object_digest, sha256_digest
from .models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    BlockerRef,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    RecordBlockerOp,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    RelationVersion,
    RelationVersionRef,
    RouteSpecV3,
    SemanticFacetRef,
    Snapshot,
    SupersedeEntityOp,
    SupersedeRelationOp,
    Transaction,
)
from .theory_validation import (
    TheoryReadinessReport,
    TheoryValidationError,
    _typed_reference_closure_is_current_and_fresh,
    validate_theory_entity,
    validate_theory_projection,
)


ASSURANCE_PREDICATE_VERSION = "ASSURANCE-PASS-0.1"
AUTHORING_LEAKAGE_LINT_VERSION = "AUTHORING-LEAKAGE-LINT-0.1"

_SYMBOLIC_PROTOCOL_DESCRIPTOR = {
    "implementation": "econ_theorist.assurance",
    "protocol": "exact_polynomial_identity.v1",
    "validator": ASSURANCE_PREDICATE_VERSION,
}
_FINITE_PROTOCOL_DESCRIPTOR = {
    "implementation": "econ_theorist.assurance",
    "protocol": "exact_polynomial_relation_scan.v1",
    "validator": ASSURANCE_PREDICATE_VERSION,
}


def harness_protocol_code_bytes(protocol: str) -> bytes:
    descriptors = {
        "exact_polynomial_identity.v1": _SYMBOLIC_PROTOCOL_DESCRIPTOR,
        "exact_polynomial_relation_scan.v1": _FINITE_PROTOCOL_DESCRIPTOR,
    }
    try:
        descriptor = descriptors[protocol]
    except KeyError as exc:
        raise AuthoringValidationError(
            f"unknown built-in assurance protocol: {protocol}"
        ) from exc
    return canonical_json_bytes(descriptor)


def harness_protocol_code_hash(protocol: str) -> str:
    return sha256_digest(harness_protocol_code_bytes(protocol))

_PHASE3_ROUTES = frozenset(
    {
        "verify.independent_rederivation",
        "audit.argument_assurance",
        "design.reader_path",
        "compose.manuscript_unit",
        "review.manuscript_unit",
        "prepare.reader_probe",
        "answer.reader_probe",
        "adjudicate.reader_probe",
        "close.manuscript_review",
        "record.human_effort",
    }
)
_ASSURANCE_ROUTES = frozenset(
    {"verify.independent_rederivation", "audit.argument_assurance"}
)
_PHASE3_ENTRY_TYPES: Mapping[str, frozenset[str]] = {
    "verify.independent_rederivation": frozenset(
        {
            "AssumptionMap",
            "ClaimGraph",
            "FormalModel",
            "ProofObligation",
            "ValidatedArgumentPackage",
        }
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
            "AssuranceBundle",
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
            "ReviewClosure",
            "RevisionBrief",
            "ValidatedArgumentPackage",
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
_PRESENTATION_SOURCE_TYPES = frozenset(
    {
        "ResolvedProfileManifest",
        "PaperIR",
        "ReaderPath",
        "ResultContractSet",
        "ManuscriptUnit",
    }
)
_PROFILE_DECISION_KINDS = {
    "theory_mode_decision_ref": "theory_mode",
    "ambition_decision_ref": "ambition",
    "g4_decision_ref": "G4_result_investment",
    "audience_decision_ref": "audience",
}


class AuthoringValidationError(ValueError):
    """A Phase 3 object is structurally valid but semantically inadmissible."""


class FacetPathError(ValueError):
    """A copied exact semantic pointer cannot be resolved."""


@dataclass(frozen=True)
class AssurancePassReport:
    predicate_version: str
    bundle_ref: EntityVersionRef
    passed: bool
    failed_requirements: tuple[str, ...]


@dataclass(frozen=True)
class AuthoringProjectionReport:
    parsed_entity_count: int
    assurance_pass_refs: tuple[EntityVersionRef, ...]
    authoring_ready_refs: tuple[EntityVersionRef, ...]


@dataclass(frozen=True)
class AuthoringRouteEntryReport:
    route_id: str
    compiler_mode: str | None
    input_entity_refs: tuple[EntityVersionRef, ...]
    package_ref: EntityVersionRef | None
    assurance_bundle_ref: EntityVersionRef | None
    canonical_writer: Actor | None


@dataclass(frozen=True)
class GovernanceLeak:
    rule_id: str
    start_offset: int
    end_offset: int
    matched_text: str


def resolved_profile_projection_hash(profile: a.ResolvedProfileManifest) -> str:
    """Canonical ``ResolvedProfileManifest`` semantic projection digest."""

    data = profile.model_dump(mode="json", exclude={"projection_hash", "resolved_at"})
    return object_digest(
        {"projection": "RESOLVED-PROFILE-0.1", "profile": data}
    )


def paper_ir_upstream_projection_hash(
    paper: a.PaperIR, profile: a.ResolvedProfileManifest
) -> str:
    """Digest the exact authority/science inputs from which one Paper IR is built."""

    return object_digest(
        {
            "projection": "PAPER-IR-UPSTREAM-0.1",
            "source_state_revision": paper.source_state_revision,
            "package_ref": paper.package_ref,
            "assurance_bundle_ref": paper.assurance_bundle_ref,
            "g5_decision_ref": paper.g5_decision_ref,
            "manuscript_version_promotion_ref": paper.manuscript_version_promotion_ref,
            "resolved_profile_manifest_ref": paper.resolved_profile_manifest_ref,
            "resolved_profile_projection_hash": profile.projection_hash,
        }
    )


def critic_assignment_contract_hash(assignment: a.CriticAssignment) -> str:
    """Seal the role/information contract, not a future run context digest."""

    data = assignment.model_dump(
        mode="json", exclude={"sealed_context_hash", "sealed_at"}
    )
    return object_digest(
        {"projection": "CRITIC-ASSIGNMENT-CONTRACT-0.1", "assignment": data}
    )


def _fraction(value: a.ExactRationalValue) -> Fraction:
    return Fraction(value.numerator, value.denominator)


def _exact_polynomial(value: a.ExactPolynomialSpec) -> ExactPolynomial:
    return ExactPolynomial.normalized(
        (
            _fraction(term.coefficient),
            {item.variable: item.power for item in term.powers},
        )
        for term in value.terms
    )


def _exact_assignment(value: a.ExactAssignmentSpec) -> ExactAssignment:
    return ExactAssignment(
        case_id=value.case_id,
        values=tuple(
            (item.variable, _fraction(item.value)) for item in value.values
        ),
    )


def reproducible_harness_artifact_bytes(
    receipt: a.ToolHarnessReceipt,
) -> dict[str, bytes]:
    """Recompute the exact canonical bytes bound by one built-in receipt."""

    evidence = receipt.reproducible_evidence
    if isinstance(evidence, a.SymbolicIdentityEvidence):
        left = _exact_polynomial(evidence.left)
        right = _exact_polynomial(evidence.right)
        try:
            run = run_polynomial_identity(left, right)
            verify_polynomial_identity_run(run)
        except AssuranceHarnessError as exc:
            raise AuthoringValidationError(
                "symbolic evidence cannot be reproduced"
            ) from exc
        expected = {
            "protocol": run.protocol,
            "left": evidence.left.model_dump(mode="json"),
            "right": evidence.right.model_dump(mode="json"),
            "input_hash": run.input.input_hash,
            "output_hash": run.output.output_hash,
            "left_hash": run.certificate.left_hash,
            "right_hash": run.certificate.right_hash,
            "difference_hash": run.certificate.difference_hash,
            "outcome": run.output.outcome,
            "certificate_hash": run.certificate.certificate_hash,
        }
        if evidence.model_dump(mode="json") != expected:
            raise AuthoringValidationError(
                "symbolic evidence does not reproduce its exact certificate"
            )
        return {
            "code": harness_protocol_code_bytes(evidence.protocol),
            "input": run.input.canonical_bytes(),
            "output": run.output.canonical_bytes(),
            "certificate": run.certificate.canonical_bytes(),
        }
    if isinstance(evidence, a.CounterexampleScanEvidence):
        cases = tuple(_exact_assignment(item) for item in evidence.cases)
        expected_code_hash = harness_protocol_code_hash(evidence.protocol)
        if evidence.code_hash != expected_code_hash:
            raise AuthoringValidationError(
                "finite scan code hash is not the pinned built-in protocol"
            )
        relation = ExactPolynomialRelation(
            left=_exact_polynomial(evidence.predicate.left),
            operator=evidence.predicate.relation,
            right=_exact_polynomial(evidence.predicate.right),
        )
        try:
            run = run_exact_polynomial_relation_scan(
                relation, cases, code_hash=expected_code_hash
            )
            verify_exact_polynomial_relation_scan(
                run, expected_code_hash=expected_code_hash
            )
        except AssuranceHarnessError as exc:
            raise AuthoringValidationError(
                "finite counterexample evidence cannot be reproduced"
            ) from exc
        witness_case_id = (
            run.output.witness.case_id if run.output.witness is not None else None
        )
        expected = {
            "protocol": run.protocol,
            "predicate": evidence.predicate.model_dump(mode="json"),
            "cases": [item.model_dump(mode="json") for item in evidence.cases],
            "code_hash": run.input.code_hash,
            "input_hash": run.input.input_hash,
            "output_hash": run.output.output_hash,
            "domain_hash": run.output.domain_hash,
            "relation_hash": run.output.relation_hash,
            "checked_count": run.output.checked_count,
            "outcome": run.output.outcome,
            "witness_case_id": witness_case_id,
            "witness_hash": run.receipt.witness_hash,
            "receipt_hash": run.receipt.receipt_hash,
            "evidentiary_limit": run.receipt.evidentiary_limit,
        }
        if evidence.model_dump(mode="json") != expected:
            raise AuthoringValidationError(
                "finite counterexample evidence does not reproduce exactly"
            )
        result = {
            "code": harness_protocol_code_bytes(evidence.protocol),
            "input": run.input.canonical_bytes(),
            "output": run.output.canonical_bytes(),
            "receipt": run.receipt.canonical_bytes(),
        }
        if run.output.witness is not None:
            result["witness"] = run.output.witness.canonical_bytes()
        return result
    raise AuthoringValidationError(
        "passing built-in harness receipt lacks typed reproducible evidence"
    )


def validate_reproducible_tool_receipt(receipt: a.ToolHarnessReceipt) -> None:
    artifacts = reproducible_harness_artifact_bytes(receipt)
    bindings = {
        "code": receipt.code_ref,
        "input": receipt.input_ref,
        "output": receipt.output_ref,
        "receipt": receipt.receipt_ref,
        "certificate": receipt.certificate_ref,
        "witness": receipt.witness_ref,
    }
    for kind, data in artifacts.items():
        reference = bindings[kind]
        if reference is None or reference.content_hash != sha256_digest(data):
            raise AuthoringValidationError(
                f"{kind} artifact hash does not bind the reproduced harness bytes"
            )
    for kind in {"receipt", "certificate", "witness"}.difference(artifacts):
        if bindings[kind] is not None:
            raise AuthoringValidationError(
                f"harness carries an unexpected {kind} artifact"
            )
    evidence = receipt.reproducible_evidence
    if isinstance(evidence, a.SymbolicIdentityEvidence):
        if receipt.tool_name != "econ_theorist.assurance" or receipt.tool_version != evidence.protocol:
            raise AuthoringValidationError("symbolic receipt tool/version is not pinned")
        expected_outcome = (
            "identity_verified" if evidence.outcome == "identity_verified" else "failed"
        )
        if receipt.outcome != expected_outcome:
            raise AuthoringValidationError("symbolic receipt outcome disagrees with evidence")
    elif isinstance(evidence, a.CounterexampleScanEvidence):
        expected_outcome = (
            "witness_found" if evidence.outcome == "falsified" else "no_counterexample_found"
        )
        if (
            receipt.tool_name != "econ_theorist.assurance"
            or receipt.tool_version != evidence.protocol
            or receipt.outcome != expected_outcome
        ):
            raise AuthoringValidationError("finite receipt tool/version/outcome is not pinned")


_JSON_ARRAY_INDEX = re.compile(r"0|[1-9][0-9]*")


def _path_parts(field_path: str) -> tuple[str, ...]:
    return tuple(
        part.replace("~1", "/").replace("~0", "~")
        for part in field_path[1:].split("/")
    )


def facet_semantic_value(
    entity: EntityVersion, facet: str, field_path: str | None = None
) -> object:
    """Resolve the exact stored facet value without importing runtime.__init__."""

    payload: object = getattr(entity.facets, facet)
    if field_path is None:
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
            return {"payload": payload, "title": entity.title, "summary": entity.summary}
        return {
            "payload": payload,
            "lifecycle": entity.status.lifecycle,
            "privacy": entity.privacy,
            "access_compartments": entity.access_compartments,
            "artifact_refs": entity.artifact_refs,
        }
    if not field_path.startswith("/"):
        raise FacetPathError("facet path must be an RFC 6901 JSON Pointer")
    value = payload
    for part in _path_parts(field_path):
        if isinstance(value, Mapping):
            if part not in value:
                raise FacetPathError(f"missing facet path {field_path!r}")
            value = value[part]
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            if _JSON_ARRAY_INDEX.fullmatch(part) is None:
                raise FacetPathError(f"noncanonical array component in {field_path!r}")
            try:
                value = value[int(part, 10)]
            except IndexError as exc:
                raise FacetPathError(f"invalid array component in {field_path!r}") from exc
        else:
            raise FacetPathError(f"facet path {field_path!r} traverses a scalar")
    return value


def facet_semantic_hash(
    entity: EntityVersion, facet: str, field_path: str | None = None
) -> str:
    return object_digest(facet_semantic_value(entity, facet, field_path))


def _actor_key(actor: Actor) -> tuple[str, str]:
    return actor.kind, actor.actor_id


def _entity_key(value: EntityVersion | EntityVersionRef) -> tuple[str, int]:
    return value.entity_id, value.version


def _artifact_key(
    value: ArtifactRegistration | ArtifactDependencyRef,
) -> tuple[str, int]:
    return value.artifact_id, value.version


def _decision_key(value: Decision | DecisionVersionRef) -> tuple[str, int]:
    return value.decision_id, value.version


def _relation_key(value: RelationVersion | RelationVersionRef) -> tuple[str, int]:
    return value.relation_id, value.version


def _ref_key(value: object) -> tuple[object, ...]:
    if isinstance(value, SemanticFacetRef):
        return (
            "semantic",
            value.entity_id,
            value.version,
            value.facet,
            value.field_path,
            value.semantic_hash,
        )
    if isinstance(value, EntityVersionRef):
        return ("entity", value.entity_id, value.version)
    if isinstance(value, ArtifactDependencyRef):
        return ("artifact", value.artifact_id, value.version, value.content_hash)
    if isinstance(value, DecisionVersionRef):
        return ("decision", value.decision_id, value.version)
    if isinstance(value, RelationVersionRef):
        return ("relation", value.relation_id, value.version)
    if isinstance(value, BlockerRef):
        return ("blocker", value.blocker_id)
    raise TypeError(f"unsupported exact reference {type(value).__name__}")


def _walk_exact_refs(value: object) -> Iterable[object]:
    if isinstance(
        value,
        (
            SemanticFacetRef,
            EntityVersionRef,
            ArtifactDependencyRef,
            DecisionVersionRef,
            RelationVersionRef,
            BlockerRef,
        ),
    ):
        yield value
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from _walk_exact_refs(getattr(value, field_name))
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _walk_exact_refs(nested)
        return
    if isinstance(value, (tuple, list, set, frozenset)):
        for nested in value:
            yield from _walk_exact_refs(nested)


def _current_index(values: Iterable[object], id_field: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        object_id = getattr(value, id_field)
        result[object_id] = max(result.get(object_id, 0), value.version)
    return result


def _unique_index(values: Sequence[object], key, label: str) -> dict[object, object]:
    result = {key(value): value for value in values}
    if len(result) != len(values):
        raise AuthoringValidationError(f"projection repeats an exact {label} version")
    return result


def _payload_artifact_refs(payload: a.AuthoringPayload) -> frozenset[ArtifactDependencyRef]:
    referenced = {
        ref for ref in _walk_exact_refs(payload) if isinstance(ref, ArtifactDependencyRef)
    }
    if isinstance(payload, a.ReDerivationRecord):
        # These refs attest to what the blind role packet excluded. Treating
        # them as positive envelope dependencies would disclose precisely the
        # proof artifacts whose absence establishes independent re-derivation.
        referenced.difference_update(payload.excluded_proof_artifact_refs)
    return frozenset(referenced)


def validate_authoring_entity(
    entity: EntityVersion, previous: EntityVersion | None = None
) -> a.AuthoringPayload:
    """Parse one authoring envelope and enforce its immutable update rules."""

    if entity.entity_type not in a.AUTHORING_PAYLOAD_MODELS:
        raise AuthoringValidationError(
            f"unregistered Phase 3 entity_type: {entity.entity_type}"
        )
    if not a.is_packed_authoring_entity(entity):
        raise AuthoringValidationError(
            f"{entity.entity_type} is not a canonical authoring envelope"
        )
    try:
        payload = a.parse_authoring_entity(entity)
    except (TypeError, ValueError) as exc:
        raise AuthoringValidationError(str(exc)) from exc

    exposed = frozenset(entity.artifact_refs)
    referenced = _payload_artifact_refs(payload)
    if exposed != referenced:
        raise AuthoringValidationError(
            f"{entity.entity_type} envelope must expose every and only exact artifact dependency"
        )

    if previous is None:
        if entity.version != 1:
            raise AuthoringValidationError(
                "a typed authoring history cannot omit the exact predecessor"
            )
        return payload
    if (
        previous.entity_id != entity.entity_id
        or previous.entity_type != entity.entity_type
        or previous.version + 1 != entity.version
        or entity.supersedes
        != EntityVersionRef(entity_id=previous.entity_id, version=previous.version)
    ):
        raise AuthoringValidationError("authoring supersession has the wrong predecessor")
    try:
        old_payload = a.parse_authoring_entity(previous)
        if isinstance(old_payload, a.AssuranceBundle):
            raise AuthoringValidationError(
                "AssuranceBundle is immutable; assemble a new exact bundle"
            )
        a.validate_authoring_payload_update(old_payload, payload)
    except AuthoringValidationError:
        raise
    except (TypeError, ValueError) as exc:
        raise AuthoringValidationError(str(exc)) from exc
    return payload


def validate_authoring_update(
    previous: EntityVersion, current: EntityVersion
) -> a.AuthoringPayload:
    """Public explicit alias for authoring supersession validation."""

    return validate_authoring_entity(current, previous)


def _is_effective(snapshot: Snapshot, reference: DecisionVersionRef) -> bool:
    return any(
        value.decision_id == reference.decision_id and value.version == reference.version
        for value in snapshot.effective_decisions.values()
    )


def _decision_is_current_confirmed_human(
    snapshot: Snapshot, decision: Decision, *, expected_kind: str | None = None
) -> bool:
    return (
        (expected_kind is None or decision.decision_kind == expected_kind)
        and snapshot.current_decisions.get(decision.decision_id) == decision.version
        and _is_effective(
            snapshot,
            DecisionVersionRef(
                decision_id=decision.decision_id, version=decision.version
            ),
        )
        and decision.status == "confirmed"
        and decision.decider.kind == "human"
        and decision.selected_option is not None
    )


def _decision_is_confirmed_human(
    decision: Decision, *, expected_kind: str | None = None
) -> bool:
    return (
        (expected_kind is None or decision.decision_kind == expected_kind)
        and decision.status == "confirmed"
        and decision.decider.kind == "human"
        and decision.selected_option is not None
    )


def _entity_is_current_and_fresh(snapshot: Snapshot, entity: EntityVersion) -> bool:
    if snapshot.current_entities.get(entity.entity_id) != entity.version:
        return False
    owner = a.AUTHORING_PAYLOAD_OWNER_FACETS.get(entity.entity_type)
    status = snapshot.derived_status.get(entity.entity_id)
    return status is None or owner is None or status.freshness.get(owner, "fresh") == "fresh"


def _expect_entity_type(
    entity_index: Mapping[tuple[str, int], EntityVersion],
    reference: EntityVersionRef,
    expected: str | frozenset[str],
    label: str,
) -> EntityVersion:
    entity = entity_index.get(_entity_key(reference))
    allowed = frozenset((expected,)) if isinstance(expected, str) else expected
    if entity is None or entity.entity_type not in allowed:
        raise AuthoringValidationError(
            f"{label} must resolve to exact type {'/'.join(sorted(allowed))}"
        )
    return entity


def _resolve_payload(
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    reference: EntityVersionRef,
    expected: type[a.AuthoringPayload],
    label: str,
) -> a.AuthoringPayload:
    payload = payloads.get(_entity_key(reference))
    if not isinstance(payload, expected):
        raise AuthoringValidationError(
            f"{label} must resolve to exact {expected.__name__}"
        )
    return payload


def _validate_profile(
    snapshot: Snapshot,
    profile: a.ResolvedProfileManifest,
    entity_index: Mapping[tuple[str, int], EntityVersion],
    decision_index: Mapping[tuple[str, int], Decision],
    *,
    require_current: bool = False,
) -> None:
    if profile.projection_hash != resolved_profile_projection_hash(profile):
        raise AuthoringValidationError("ResolvedProfileManifest projection_hash is not canonical")
    for field_name, expected_kind in _PROFILE_DECISION_KINDS.items():
        reference = getattr(profile, field_name)
        decision = decision_index.get(_decision_key(reference))
        valid = decision is not None and _decision_is_confirmed_human(
            decision, expected_kind=expected_kind
        )
        if valid and require_current:
            assert decision is not None
            valid = _decision_is_current_confirmed_human(
                snapshot, decision, expected_kind=expected_kind
            )
        if not valid:
            raise AuthoringValidationError(
                f"minimal profile requires an effective human-confirmed {expected_kind} Decision"
            )
    if decision_index[_decision_key(profile.theory_mode_decision_ref)].selected_option != profile.theory_mode:
        raise AuthoringValidationError("profile theory_mode does not equal its exact Decision")
    if decision_index[_decision_key(profile.ambition_decision_ref)].selected_option != profile.ambition:
        raise AuthoringValidationError("profile ambition does not equal its exact Decision")
    if decision_index[_decision_key(profile.audience_decision_ref)].selected_option != profile.primary_audience:
        raise AuthoringValidationError("profile audience does not equal its exact Decision")
    source = _expect_entity_type(
        entity_index,
        EntityVersionRef(
            entity_id=profile.result_archetype_source.entity_id,
            version=profile.result_archetype_source.version,
        ),
        "ClaimGraph",
        "primary result archetype source",
    )
    try:
        projected_value = facet_semantic_value(
            source,
            profile.result_archetype_source.facet,
            profile.result_archetype_source.field_path,
        )
        actual = facet_semantic_hash(
            source,
            profile.result_archetype_source.facet,
            profile.result_archetype_source.field_path,
        )
    except FacetPathError as exc:
        raise AuthoringValidationError(str(exc)) from exc
    if actual != profile.result_archetype_source.semantic_hash:
        raise AuthoringValidationError("profile result-archetype source hash is stale or forged")
    if projected_value != profile.primary_result_archetype:
        raise AuthoringValidationError(
            "profile primary archetype differs from its exact G4/G5 hierarchy field"
        )


def _validate_paper_ir(
    snapshot: Snapshot,
    paper: a.PaperIR,
    entity_index: Mapping[tuple[str, int], EntityVersion],
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    theory_payloads: Mapping[tuple[str, int], t.TheoryPayload],
    decision_index: Mapping[tuple[str, int], Decision],
    *,
    require_current: bool = False,
) -> None:
    package_entity = _expect_entity_type(
        entity_index, paper.package_ref, "ValidatedArgumentPackage", "Paper IR package"
    )
    package = theory_payloads.get(_entity_key(paper.package_ref))
    if not isinstance(package, t.ValidatedArgumentPackage):
        raise AuthoringValidationError("Paper IR package is not a packed VAP")
    profile = _resolve_payload(
        payloads,
        paper.resolved_profile_manifest_ref,
        a.ResolvedProfileManifest,
        "Paper IR profile",
    )
    assert isinstance(profile, a.ResolvedProfileManifest)
    if paper.upstream_projection_hash != paper_ir_upstream_projection_hash(paper, profile):
        raise AuthoringValidationError("Paper IR upstream projection hash is not canonical")
    if paper.compiler_mode in {"working", "submission"}:
        if require_current and not _entity_is_current_and_fresh(snapshot, package_entity):
            raise AuthoringValidationError("working/submission Paper IR package is stale")
        if paper.g5_decision_ref is None or paper.assurance_bundle_ref is None:
            raise AuthoringValidationError("working/submission mode lacks G5 or assurance")
        g5 = decision_index.get(_decision_key(paper.g5_decision_ref))
        valid_g5 = g5 is not None and _decision_is_confirmed_human(
            g5, expected_kind="G5_argument_validation"
        )
        if valid_g5 and require_current:
            assert g5 is not None
            valid_g5 = _decision_is_current_confirmed_human(
                snapshot, g5, expected_kind="G5_argument_validation"
            )
        if not valid_g5:
            raise AuthoringValidationError("working/submission requires an effective exact G5")
        if (
            g5.machine_outcome != "approve"
            or g5.selected_option != "approve"
            or g5.subject_ref != package.g5_dossier_ref.entity_id
            or g5.scope_ref != package.question_ref.entity_id
        ):
            raise AuthoringValidationError("Paper IR G5 does not approve its exact package")
        bundle = _resolve_payload(
            payloads,
            paper.assurance_bundle_ref,
            a.AssuranceBundle,
            "Paper IR assurance",
        )
        assert isinstance(bundle, a.AssuranceBundle)
        if bundle.package_ref != paper.package_ref or bundle.g5_decision_ref != paper.g5_decision_ref:
            raise AuthoringValidationError("Paper IR assurance belongs to another package or G5")
    if paper.compiler_mode == "submission":
        promotion = decision_index.get(_decision_key(paper.manuscript_version_promotion_ref))
        valid_promotion = promotion is not None and _decision_is_confirmed_human(
            promotion, expected_kind="manuscript_version_promotion"
        )
        if valid_promotion and require_current:
            assert promotion is not None
            valid_promotion = _decision_is_current_confirmed_human(
                snapshot, promotion, expected_kind="manuscript_version_promotion"
            )
        if not valid_promotion:
            raise AuthoringValidationError("submission requires an effective human promotion")
        assert promotion is not None
        if (
            promotion.machine_outcome != "approve"
            or promotion.selected_option != "approve"
            or promotion.scope_ref != package.question_ref.entity_id
        ):
            raise AuthoringValidationError(
                "submission promotion must explicitly approve this package's working manuscript"
            )
        closure_entity = next(
            (
                entity
                for entity in entity_index.values()
                if entity.entity_id == promotion.subject_ref
                and (
                    not require_current
                    or snapshot.current_entities.get(entity.entity_id) == entity.version
                )
                and isinstance(
                    payloads.get(_entity_key(entity)), a.ReviewClosure
                )
                and payloads[_entity_key(entity)].status == "authoring_ready"
                and payloads[_entity_key(entity)].compiler_mode == "working"
            ),
            None,
        )
        if closure_entity is None or closure_entity.entity_type != "ReviewClosure":
            raise AuthoringValidationError("submission promotion must govern an exact current closure")
        promoted_closure = payloads[_entity_key(closure_entity)]
        assert isinstance(promoted_closure, a.ReviewClosure)
        promoted_paper = _resolve_payload(
            payloads,
            promoted_closure.paper_ir_ref,
            a.PaperIR,
            "promoted working Paper IR",
        )
        assert isinstance(promoted_paper, a.PaperIR)
        promoted_profile = _resolve_payload(
            payloads,
            promoted_paper.resolved_profile_manifest_ref,
            a.ResolvedProfileManifest,
            "promoted working profile",
        )
        assert isinstance(promoted_profile, a.ResolvedProfileManifest)
        if (
            promoted_paper.package_ref != paper.package_ref
            or promoted_paper.assurance_bundle_ref != paper.assurance_bundle_ref
            or promoted_profile.theory_mode != profile.theory_mode
            or promoted_profile.ambition != profile.ambition
            or promoted_profile.primary_result_archetype
            != profile.primary_result_archetype
            or promoted_profile.primary_audience != profile.primary_audience
        ):
            raise AuthoringValidationError(
                "submission projection does not descend from the promoted working lineage"
            )
        if require_current:
            validate_authoring_ready(
                snapshot,
                EntityVersionRef(
                    entity_id=closure_entity.entity_id, version=closure_entity.version
                ),
            )

    claims = theory_payloads.get(_entity_key(package.claim_graph_ref))
    if not isinstance(claims, t.ClaimGraph):
        raise AuthoringValidationError("Paper IR package ClaimGraph is unavailable")
    claim_by_id = {item.claim_id: item for item in claims.claims}
    portfolio = theory_payloads.get(_entity_key(package.result_portfolio_ref))
    if (
        not isinstance(portfolio, t.ResultPortfolio)
        or portfolio.headline_claim_id not in claim_by_id
        or claim_by_id[portfolio.headline_claim_id].archetype
        != profile.primary_result_archetype
    ):
        raise AuthoringValidationError(
            "minimal profile archetype does not equal the exact headline result hierarchy"
        )
    headline_index = next(
        index
        for index, claim in enumerate(claims.claims)
        if claim.claim_id == portfolio.headline_claim_id
    )
    if (
        profile.g4_decision_ref != package.prior_gate_decision_refs[-1]
        or profile.result_archetype_source.entity_id != package.claim_graph_ref.entity_id
        or profile.result_archetype_source.version != package.claim_graph_ref.version
        or profile.result_archetype_source.facet != "formal"
        or profile.result_archetype_source.field_path
        != f"/payload/claims/{headline_index}/archetype"
    ):
        raise AuthoringValidationError(
            "minimal profile G4/archetype source does not bind the package headline hierarchy"
        )
    for projection in paper.claim_projections:
        if projection.claim_graph_ref != package.claim_graph_ref:
            raise AuthoringValidationError("Paper IR projects a foreign ClaimGraph")
        claim = claim_by_id.get(projection.claim_id)
        if claim is None:
            raise AuthoringValidationError("Paper IR projects an unknown claim")
        if (
            projection.formal_statement != claim.formal_statement
            or projection.scope != claim.domain
            or projection.assumption_ids != claim.assumption_ids
            or projection.semantic_translation != claim.semantic_translation
        ):
            raise AuthoringValidationError("Paper IR claim cache differs from its exact ClaimGraph")
        for source in (
            projection.formal_statement_source,
            projection.scope_source,
            projection.translation_source,
            *projection.assumption_source_refs,
        ):
            source_entity = entity_index.get((source.entity_id, source.version))
            if source_entity is None:
                raise AuthoringValidationError("Paper IR claim source is unresolved")
            try:
                actual = facet_semantic_hash(source_entity, source.facet, source.field_path)
            except FacetPathError as exc:
                raise AuthoringValidationError(str(exc)) from exc
            if actual != source.semantic_hash:
                raise AuthoringValidationError("Paper IR claim source semantic hash mismatches")


def _validate_assurance_cross_refs(
    bundle: a.AssuranceBundle,
    entity_index: Mapping[tuple[str, int], EntityVersion],
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    theory_payloads: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    package = theory_payloads.get(_entity_key(bundle.package_ref))
    if not isinstance(package, t.ValidatedArgumentPackage):
        raise AuthoringValidationError("AssuranceBundle package_ref is not a VAP")
    expected = {
        "claim_graph_ref": package.claim_graph_ref,
        "formal_model_ref": package.formal_model_ref,
        "assumption_map_ref": package.assumption_map_ref,
        "verification_bundle_ref": package.verification_bundle_ref,
    }
    if any(getattr(bundle, field) != reference for field, reference in expected.items()):
        raise AuthoringValidationError("AssuranceBundle does not bind the exact VAP inputs")
    claim_graph = theory_payloads.get(_entity_key(bundle.claim_graph_ref))
    verification_bundle = theory_payloads.get(_entity_key(bundle.verification_bundle_ref))
    if not isinstance(claim_graph, t.ClaimGraph) or not isinstance(
        verification_bundle, t.VerificationBundle
    ):
        raise AuthoringValidationError("AssuranceBundle scientific inputs are unavailable")
    claims = {item.claim_id: item for item in claim_graph.claims}
    headline = claims.get(bundle.headline_claim_id)
    portfolio = theory_payloads.get(_entity_key(package.result_portfolio_ref))
    if (
        headline is None
        or not isinstance(portfolio, t.ResultPortfolio)
        or portfolio.headline_claim_id != bundle.headline_claim_id
    ):
        raise AuthoringValidationError("AssuranceBundle identifies the wrong headline claim")
    for reference in bundle.rederivation_refs:
        record = _resolve_payload(
            payloads, reference, a.ReDerivationRecord, "assurance re-derivation"
        )
        assert isinstance(record, a.ReDerivationRecord)
        if (
            record.package_ref != bundle.package_ref
            or record.claim_graph_ref != bundle.claim_graph_ref
            or record.claim_id not in claims
            or record.formal_model_ref != bundle.formal_model_ref
            or record.assumption_map_ref != bundle.assumption_map_ref
        ):
            raise AuthoringValidationError("re-derivation is not for the exact assurance inputs")
    records = {
        ref: theory_payloads.get(_entity_key(ref))
        for ref in verification_bundle.verification_record_refs
    }
    obligations = {
        ref: theory_payloads.get(_entity_key(ref))
        for ref in verification_bundle.proof_obligation_refs
    }
    for audit in bundle.proof_audits:
        record = records.get(audit.verification_record_ref)
        obligation = obligations.get(audit.obligation_ref)
        rederivation = payloads.get(_entity_key(audit.rederivation_ref))
        if not isinstance(record, t.VerificationRecord) or not isinstance(
            obligation, t.ProofObligation
        ) or not isinstance(rederivation, a.ReDerivationRecord):
            raise AuthoringValidationError("proof audit references a record outside the bundle")
        if (
            audit.claim_graph_ref != bundle.claim_graph_ref
            or audit.formal_model_ref != bundle.formal_model_ref
            or audit.assumption_map_ref != bundle.assumption_map_ref
            or audit.claim_id != obligation.claim_id
            or record.obligation_ref != audit.obligation_ref
            or record.claim_graph_ref != audit.claim_graph_ref
            or record.formal_model_ref != audit.formal_model_ref
            or record.assumption_map_ref != audit.assumption_map_ref
            or audit.proof_artifact_ref not in record.evidence_refs
            or audit.originating_verifier != record.verifier
            or audit.rederivation_ref not in bundle.rederivation_refs
            or rederivation.obligation_ref != audit.obligation_ref
            or rederivation.verification_record_ref
            != audit.verification_record_ref
            or rederivation.claim_graph_ref != audit.claim_graph_ref
            or rederivation.formal_model_ref != audit.formal_model_ref
            or rederivation.assumption_map_ref != audit.assumption_map_ref
            or rederivation.claim_id != audit.claim_id
            or audit.comparison_outcome != rederivation.outcome
        ):
            raise AuthoringValidationError(
                "proof audit revision, re-derivation, or proof evidence mismatches"
            )
    for receipt in bundle.tool_receipts:
        obligation = obligations.get(receipt.obligation_ref)
        if (
            not isinstance(obligation, t.ProofObligation)
            or receipt.claim_graph_ref != bundle.claim_graph_ref
            or receipt.claim_id != obligation.claim_id
        ):
            raise AuthoringValidationError("tool receipt is not tied to an exact bundle obligation")
        validate_reproducible_tool_receipt(receipt)
    for record in bundle.tool_non_applicability:
        obligation = obligations.get(record.obligation_ref)
        matching_audit_reports = {
            audit.audit_report_ref
            for audit in bundle.proof_audits
            if audit.obligation_ref == record.obligation_ref
            and audit.outcome == "passed"
        }
        if (
            not isinstance(obligation, t.ProofObligation)
            or record.claim_graph_ref != bundle.claim_graph_ref
            or record.claim_id != obligation.claim_id
            or record.determined_by != bundle.assembled_by
            or record.obligation_ref not in record.evidence_refs
            or (
                record.reason_code == "covered_by_stronger_exact_argument"
                and not matching_audit_reports.intersection(record.evidence_refs)
            )
        ):
            raise AuthoringValidationError(
                "harness non-applicability is not tied to an exact audited obligation"
            )
    if set(bundle.rederivation_refs) != {
        audit.rederivation_ref for audit in bundle.proof_audits
    }:
        raise AuthoringValidationError(
            "AssuranceBundle re-derivations must equal those compared by its proof audits"
        )


def _assurance_report(
    snapshot: Snapshot,
    bundle_ref: EntityVersionRef,
    entity_index: Mapping[tuple[str, int], EntityVersion],
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    theory_payloads: Mapping[tuple[str, int], t.TheoryPayload],
    decision_index: Mapping[tuple[str, int], Decision],
    theory_report: TheoryReadinessReport,
) -> AssurancePassReport:
    failures: list[str] = []
    bundle_entity = entity_index.get(_entity_key(bundle_ref))
    bundle = payloads.get(_entity_key(bundle_ref))
    if bundle_entity is None or not isinstance(bundle, a.AssuranceBundle):
        return AssurancePassReport(
            ASSURANCE_PREDICATE_VERSION,
            bundle_ref,
            False,
            ("unresolved AssuranceBundle",),
        )
    if not _entity_is_current_and_fresh(snapshot, bundle_entity):
        failures.append("AssuranceBundle is not current and fresh")
    package_entity = entity_index.get(_entity_key(bundle.package_ref))
    package = theory_payloads.get(_entity_key(bundle.package_ref))
    if (
        package_entity is None
        or not isinstance(package, t.ValidatedArgumentPackage)
        or package.release_mode != "production_candidate"
        or not _typed_reference_closure_is_current_and_fresh(snapshot, bundle.package_ref)
        or bundle.package_ref in theory_report.production_blocked_package_refs
    ):
        failures.append("exact production G5 package closure is not current and fresh")
    g5 = decision_index.get(_decision_key(bundle.g5_decision_ref))
    if (
        g5 is None
        or not _decision_is_current_confirmed_human(
            snapshot, g5, expected_kind="G5_argument_validation"
        )
        or g5.machine_outcome != "approve"
        or g5.selected_option != "approve"
        or not isinstance(package, t.ValidatedArgumentPackage)
        or g5.subject_ref != package.g5_dossier_ref.entity_id
        or g5.scope_ref != package.question_ref.entity_id
    ):
        failures.append("exact G5 approval is absent, stale, or governs another package")

    valid_rederivations: list[a.ReDerivationRecord] = []
    for reference in bundle.rederivation_refs:
        entity = entity_index.get(_entity_key(reference))
        record = payloads.get(_entity_key(reference))
        if not isinstance(record, a.ReDerivationRecord) or entity is None:
            continue
        provenance = {
            record.route_run_hash,
            record.context_manifest_hash,
            record.compiled_context_hash,
            record.originating_verifier_run.route_run_hash,
            record.originating_verifier_run.context_manifest_hash,
            record.originating_verifier_run.compiled_context_hash,
            record.proof_author_run.route_run_hash,
            record.proof_author_run.context_manifest_hash,
            record.proof_author_run.compiled_context_hash,
            *(
                digest
                for parent in record.parent_runs
                for digest in (
                    parent.route_run_hash,
                    parent.context_manifest_hash,
                    parent.compiled_context_hash,
                )
            ),
        }
        if (
            _entity_is_current_and_fresh(snapshot, entity)
            and record.outcome == "agrees"
            and record.route_run_id
            not in {
                record.originating_verifier_run.route_run_id,
                record.proof_author_run.route_run_id,
            }
            and bundle.route_run_id
            not in {
                record.route_run_id,
                record.originating_verifier_run.route_run_id,
                record.proof_author_run.route_run_id,
            }
            and record.originating_verifier_run.route_run_id
            not in {item.route_run_id for item in record.parent_runs}
            and record.context_manifest_hash != bundle.context_manifest_hash
            and record.compiled_context_hash != bundle.compiled_context_hash
            and record.originating_verifier_run.context_manifest_hash
            not in {record.context_manifest_hash, bundle.context_manifest_hash}
            and record.proof_author_run.context_manifest_hash
            not in {
                record.context_manifest_hash,
                record.originating_verifier_run.context_manifest_hash,
                bundle.context_manifest_hash,
            }
            and provenance.issubset(set(snapshot.provenance_hashes))
            and bundle.route_run_hash in snapshot.provenance_hashes
            and _actor_key(record.rederiver) != _actor_key(bundle.assembled_by)
        ):
            valid_rederivations.append(record)
    if not valid_rederivations or len(valid_rederivations) != len(bundle.rederivation_refs):
        failures.append(
            "every referenced re-derivation must be sealed, agreeing, and actor/run/context-independent"
        )

    verification_bundle = (
        theory_payloads.get(_entity_key(bundle.verification_bundle_ref))
        if isinstance(bundle, a.AssuranceBundle)
        else None
    )
    required_records = (
        set(verification_bundle.verification_record_refs)
        if isinstance(verification_bundle, t.VerificationBundle)
        else set()
    )
    passed_records = {
        audit.verification_record_ref
        for audit in bundle.proof_audits
        if audit.outcome == "passed"
        and audit.auditor == bundle.assembled_by
        and all(item.severity not in {"error", "critical"} for item in audit.findings)
    }
    if (
        not required_records
        or passed_records != required_records
        or len(bundle.proof_audits) != len(required_records)
    ):
        failures.append("proof audits do not pass every exact verification revision")
    if valid_rederivations and any(
        _actor_key(audit.auditor)
        in {
            _actor_key(record.rederiver),
            _actor_key(record.originating_verifier),
            _actor_key(record.proof_author),
        }
        for audit in bundle.proof_audits
        for record in valid_rederivations
    ):
        failures.append("proof audit actor is not independent")

    claim_graph = theory_payloads.get(_entity_key(bundle.claim_graph_ref))
    headline_obligations: set[EntityVersionRef] = set()
    if isinstance(claim_graph, t.ClaimGraph):
        headline = next(
            (
                claim
                for claim in claim_graph.claims
                if claim.claim_id == bundle.headline_claim_id
            ),
            None,
        )
        if headline is not None:
            headline_obligations = set(headline.proof_obligation_refs)
    symbolic = [
        item
        for item in bundle.tool_receipts
        if item.claim_id == bundle.headline_claim_id
        and item.obligation_ref in headline_obligations
        and item.harness_kind == "symbolic_identity"
        and item.outcome == "identity_verified"
        and item.evidentiary_role == "exact_identity_certificate"
        and item.certificate_ref is not None
    ]
    finite = [
        item
        for item in bundle.tool_receipts
        if item.claim_id == bundle.headline_claim_id
        and item.obligation_ref in headline_obligations
        and item.harness_kind == "counterexample_search"
        and item.outcome == "no_counterexample_found"
        and item.evidentiary_role in {"corroboration_only", "diagnostic"}
    ]
    nonapplicable = {
        (item.family, item.obligation_ref)
        for item in bundle.tool_non_applicability
        if item.claim_id == bundle.headline_claim_id
        and item.obligation_ref in headline_obligations
    }
    successful = {
        *(('symbolic_identity', item.obligation_ref) for item in symbolic),
        *(('counterexample_search', item.obligation_ref) for item in finite),
    }
    missing_harness_coverage = {
        (family, obligation)
        for obligation in headline_obligations
        for family in ("symbolic_identity", "counterexample_search")
        if (family, obligation) not in successful
        and (family, obligation) not in nonapplicable
    }
    if not headline_obligations or missing_harness_coverage:
        failures.append(
            "each headline obligation requires a passing built-in harness or typed non-applicability"
        )
    def receipt_is_admissible_nonfalsifying(item: a.ToolHarnessReceipt) -> bool:
        if item.harness_kind == "symbolic_identity":
            return (
                item.outcome == "identity_verified"
                and item.evidentiary_role == "exact_identity_certificate"
                and item.certificate_ref is not None
                and item.witness_ref is None
            )
        return (
            item.harness_kind
            in {"counterexample_search", "finite_grid"}
            and item.outcome == "no_counterexample_found"
            and item.evidentiary_role in {"corroboration_only", "diagnostic"}
            and item.witness_ref is None
            and item.certificate_ref is None
            and item.receipt_ref is not None
        )

    if any(
        not receipt_is_admissible_nonfalsifying(item)
        for item in bundle.tool_receipts
    ):
        failures.append("a harness failed, falsified, or is inconclusive")
    if any(
        item.severity == "critical" or item.blocking
        for item in bundle.unresolved_issues
    ):
        failures.append("assurance retains an unresolved critical/blocking issue")
    return AssurancePassReport(
        ASSURANCE_PREDICATE_VERSION,
        bundle_ref,
        not failures,
        tuple(failures),
    )


def derive_assurance_pass(
    snapshot: Snapshot, bundle_ref: EntityVersionRef
) -> AssurancePassReport:
    """Derive ``ASSURANCE-PASS-0.1`` from one exact snapshot."""

    entity_index, _, decision_index, payloads, theory_payloads, theory_report = (
        _validated_indices(snapshot)
    )
    bundle = payloads.get(_entity_key(bundle_ref))
    if isinstance(bundle, a.AssuranceBundle):
        _validate_assurance_cross_refs(
            bundle, entity_index, payloads, theory_payloads
        )
    return _assurance_report(
        snapshot,
        bundle_ref,
        entity_index,
        payloads,
        theory_payloads,
        decision_index,
        theory_report,
    )


def validate_assurance_pass(snapshot: Snapshot, bundle_ref: EntityVersionRef) -> None:
    report = derive_assurance_pass(snapshot, bundle_ref)
    if not report.passed:
        raise AuthoringValidationError(
            f"{ASSURANCE_PREDICATE_VERSION} failed: "
            + "; ".join(report.failed_requirements)
        )


def _validate_scientific_source_refs(
    refs: Iterable[object],
    entity_index: Mapping[tuple[str, int], EntityVersion],
    label: str,
) -> None:
    for reference in refs:
        if not isinstance(reference, EntityVersionRef):
            continue
        entity = entity_index.get(_entity_key(reference))
        if entity is not None and entity.entity_type in _PRESENTATION_SOURCE_TYPES:
            raise AuthoringValidationError(
                f"{label} cannot cite {entity.entity_type} as scientific evidence"
            )


def _validate_result_contracts(
    contracts: a.ResultContractSet,
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    theory_payloads: Mapping[tuple[str, int], t.TheoryPayload],
    entity_index: Mapping[tuple[str, int], EntityVersion],
) -> None:
    paper = _resolve_payload(payloads, contracts.paper_ir_ref, a.PaperIR, "contract Paper IR")
    reader = _resolve_payload(
        payloads, contracts.reader_path_ref, a.ReaderPath, "contract ReaderPath"
    )
    assert isinstance(paper, a.PaperIR) and isinstance(reader, a.ReaderPath)
    if reader.paper_ir_ref != contracts.paper_ir_ref:
        raise AuthoringValidationError("ResultContractSet and ReaderPath bind different Paper IRs")
    package = theory_payloads.get(_entity_key(paper.package_ref))
    if not isinstance(package, t.ValidatedArgumentPackage):
        raise AuthoringValidationError("ResultContractSet Paper IR package is unavailable")
    expected = {
        "claim_graph_ref": package.claim_graph_ref,
        "assumption_map_ref": package.assumption_map_ref,
        "economic_argument_graph_ref": package.economic_argument_graph_ref,
        "example_suite_ref": package.example_suite_ref,
        "verification_bundle_ref": package.verification_bundle_ref,
    }
    if any(getattr(contracts, field) != ref for field, ref in expected.items()):
        raise AuthoringValidationError("ResultContractSet projects a foreign scientific input")
    projection_by_id = {item.projection_id: item for item in paper.claim_projections}
    graph = theory_payloads.get(_entity_key(contracts.claim_graph_ref))
    if not isinstance(graph, t.ClaimGraph):
        raise AuthoringValidationError("ResultContractSet ClaimGraph is unavailable")
    claim_by_id = {item.claim_id: item for item in graph.claims}
    for packet in contracts.result_packets:
        projection = projection_by_id.get(packet.claim_projection_id)
        claim = claim_by_id.get(packet.claim_id)
        if (
            projection is None
            or claim is None
            or projection.claim_id != packet.claim_id
            or packet.claim_graph_ref != contracts.claim_graph_ref
            or packet.primary_archetype != claim.archetype
        ):
            raise AuthoringValidationError("ResultPacket does not bind an exact projected claim")
        sources: list[object] = []
        for layer in (
            packet.question,
            packet.pre_result_expectation,
            packet.formal_statement_and_scope,
            packet.economic_translation,
            packet.archetype_explanation,
            packet.boundary,
            packet.proof_roadmap,
            packet.consequence,
        ):
            sources.extend(layer.source_refs)
        sources.extend(_walk_exact_refs(packet.archetype_module))
        _validate_scientific_source_refs(sources, entity_index, "ResultPacket")
    known_claims = set(claim_by_id)
    if any(
        claim_id not in known_claims
        for contract in contracts.assumption_contracts
        for claim_id in contract.supported_claim_ids
    ):
        raise AuthoringValidationError("assumption contract supports an unknown claim")
    if any(item.claim_id not in known_claims for item in contracts.proof_roadmaps):
        raise AuthoringValidationError("proof roadmap names an unknown claim")
    required_assumption_ids = {
        assumption_id
        for packet in contracts.result_packets
        for assumption_id in projection_by_id[packet.claim_projection_id].assumption_ids
    }
    if {item.assumption_id for item in contracts.assumption_contracts} != required_assumption_ids:
        raise AuthoringValidationError(
            "ResultContractSet requires one exact contract for every maintained claim assumption"
        )
    assumption_map = theory_payloads.get(_entity_key(contracts.assumption_map_ref))
    if not isinstance(assumption_map, t.AssumptionMap):
        raise AuthoringValidationError("ResultContractSet AssumptionMap is unavailable")
    assumption_index = {
        item.assumption_id: (index, item)
        for index, item in enumerate(assumption_map.assumptions)
    }
    for item in contracts.assumption_contracts:
        source = assumption_index.get(item.assumption_id)
        if (
            source is None
            or item.formal_source.entity_id != contracts.assumption_map_ref.entity_id
            or item.formal_source.version != contracts.assumption_map_ref.version
            or item.formal_source.facet != "formal"
            or item.formal_source.field_path
            != f"/payload/assumptions/{source[0]}/exact_content"
            or item.economic_content != source[1].economic_interpretation
        ):
            raise AuthoringValidationError(
                "assumption contract does not bind the exact formal/economic assumption"
            )
        _validate_scientific_source_refs(
            (*item.satisfying_example_refs, item.formal_source),
            entity_index,
            "assumption contract",
        )
    for item in contracts.proof_roadmaps:
        _validate_scientific_source_refs(item.proof_refs, entity_index, "proof roadmap")


def _validate_design_topology(
    paper_ref: EntityVersionRef,
    paper: a.PaperIR,
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
) -> None:
    readers = [
        (ref, value)
        for ref, value in payloads.items()
        if isinstance(value, a.ReaderPath) and value.paper_ir_ref == paper_ref
    ]
    contracts = [
        (ref, value)
        for ref, value in payloads.items()
        if isinstance(value, a.ResultContractSet) and value.paper_ir_ref == paper_ref
    ]
    assignments = [
        value
        for value in payloads.values()
        if isinstance(value, a.CriticAssignment) and value.paper_ir_ref == paper_ref
    ]
    if not readers and not contracts and not assignments:
        # A PaperIR may be validated before the rest of its design transaction.
        return
    if len(readers) != 1 or len(contracts) != 1:
        raise AuthoringValidationError("one Paper IR design requires one ReaderPath and contract set")
    reader_ref = EntityVersionRef(entity_id=readers[0][0][0], version=readers[0][0][1])
    contract_ref = EntityVersionRef(entity_id=contracts[0][0][0], version=contracts[0][0][1])
    if len(assignments) != 3 or {item.role for item in assignments} != {
        "formal_fidelity",
        "economic_reader",
        "cold_reader",
    }:
        raise AuthoringValidationError("one design requires exactly the three isolated critic roles")
    if any(
        item.reader_path_ref != reader_ref
        or item.result_contract_set_ref != contract_ref
        or item.canonical_writer != paper.canonical_writer
        for item in assignments
    ):
        raise AuthoringValidationError("critic assignments do not bind one exact design topology")
    formal = next(item for item in assignments if item.role == "formal_fidelity")
    economic = next(item for item in assignments if item.role == "economic_reader")
    cold = next(item for item in assignments if item.role == "cold_reader")
    actor_keys = {
        _actor_key(paper.canonical_writer),
        _actor_key(formal.assigned_actor),
        _actor_key(economic.assigned_actor),
        _actor_key(cold.assigned_actor),
        _actor_key(cold.probe_designer),
        _actor_key(cold.adjudicator),
    }
    if len(actor_keys) != 6:
        raise AuthoringValidationError("design writer, critics, probe designer, and adjudicator must be distinct")


def _validate_submission_unit_semantics(
    source_unit: a.ManuscriptUnit, submission_unit: a.ManuscriptUnit
) -> None:
    """Allow formatting movement but no unapproved consequential prose change."""

    source_spans = tuple(
        item.model_dump(mode="json", exclude={"location"})
        for item in source_unit.spans
    )
    submission_spans = tuple(
        item.model_dump(mode="json", exclude={"location"})
        for item in submission_unit.spans
    )
    if (
        submission_spans != source_spans
        or submission_unit.terminology != source_unit.terminology
        or submission_unit.section_contract_id != source_unit.section_contract_id
    ):
        raise AuthoringValidationError(
            "submission compilation may change formatting but not approved prose semantics"
        )


def _validate_manuscript_cross_refs(
    unit_ref: EntityVersionRef,
    unit: a.ManuscriptUnit,
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    entity_index: Mapping[tuple[str, int], EntityVersion],
) -> None:
    paper = _resolve_payload(payloads, unit.paper_ir_ref, a.PaperIR, "manuscript Paper IR")
    reader = _resolve_payload(payloads, unit.reader_path_ref, a.ReaderPath, "manuscript ReaderPath")
    contracts = _resolve_payload(
        payloads, unit.result_contract_set_ref, a.ResultContractSet, "manuscript contracts"
    )
    assert isinstance(paper, a.PaperIR)
    assert isinstance(reader, a.ReaderPath)
    assert isinstance(contracts, a.ResultContractSet)
    if (
        reader.paper_ir_ref != unit.paper_ir_ref
        or contracts.paper_ir_ref != unit.paper_ir_ref
        or contracts.reader_path_ref != unit.reader_path_ref
        or unit.canonical_writer != paper.canonical_writer
    ):
        raise AuthoringValidationError("ManuscriptUnit mixes design outputs or writer ownership")
    if paper.compiler_mode == "submission":
        if (
            unit.submission_source_unit_ref is None
            or unit.submission_source_artifact_ref is None
        ):
            raise AuthoringValidationError(
                "submission ManuscriptUnit lacks its promoted working source"
            )
        source_unit = _resolve_payload(
            payloads,
            unit.submission_source_unit_ref,
            a.ManuscriptUnit,
            "submission source unit",
        )
        assert isinstance(source_unit, a.ManuscriptUnit)
        if source_unit.manuscript_artifact_ref != unit.submission_source_artifact_ref:
            raise AuthoringValidationError(
                "submission source artifact differs from the promoted working unit"
            )
        _validate_submission_unit_semantics(source_unit, unit)
    elif (
        unit.submission_source_unit_ref is not None
        or unit.submission_source_artifact_ref is not None
    ):
        raise AuthoringValidationError(
            "only submission ManuscriptUnits may bind a promoted working source"
        )
    sections = {item.section_id: item for item in reader.section_contracts}
    section = sections.get(unit.section_contract_id)
    if section is None:
        raise AuthoringValidationError("ManuscriptUnit names an unknown section contract")
    projection_by_id = {item.projection_id: item for item in paper.claim_projections}
    for span in unit.spans:
        projection = projection_by_id.get(span.claim_projection_id)
        if (
            projection is None
            or span.claim_graph_ref != projection.claim_graph_ref
            or span.claim_id != projection.claim_id
        ):
            raise AuthoringValidationError("manuscript span does not bind its exact claim projection")
        if span.role == "formal_statement" and (
            span.scope != projection.scope or span.assumption_ids != projection.assumption_ids
        ):
            raise AuthoringValidationError("formal statement span changes scope or assumptions")
        projected_sources = {
            _ref_key(item)
            for item in (
                projection.formal_statement_source,
                projection.scope_source,
                projection.translation_source,
                *projection.assumption_source_refs,
            )
        }
        if not {_ref_key(item) for item in span.source_fields}.issubset(projected_sources):
            raise AuthoringValidationError("manuscript span cites a source outside its exact projection")
        _validate_scientific_source_refs(span.support_refs, entity_index, "manuscript span")
    required_projections = set(section.required_claim_projection_ids)
    realized_projections = {item.claim_projection_id for item in unit.spans}
    if not required_projections or realized_projections != required_projections:
        raise AuthoringValidationError(
            "ManuscriptUnit must realize every and only its section's required claim projections"
        )
    packet_by_projection = {
        item.claim_projection_id: item for item in contracts.result_packets
    }
    spans_by_projection: dict[str, list[a.ConsequentialSpan]] = {}
    for span in unit.spans:
        spans_by_projection.setdefault(span.claim_projection_id, []).append(span)
    shared_roles = {
        "formal_statement",
        "economic_translation",
        "mechanism_or_conceptual_explanation",
        "example_or_witness",
        "boundary",
        "proof_roadmap",
        "consequence",
    }
    for projection_id in required_projections:
        packet = packet_by_projection.get(projection_id)
        projection = projection_by_id.get(projection_id)
        if packet is None or projection is None:
            raise AuthoringValidationError(
                "required manuscript projection lacks its exact ResultPacket"
            )
        projection_spans = spans_by_projection[projection_id]
        required_roles = set(shared_roles)
        if any(
            projection.claim_id in item.supported_claim_ids
            for item in contracts.assumption_contracts
        ):
            required_roles.add("assumption_interpretation")
        if not required_roles.issubset({item.role for item in projection_spans}):
            raise AuthoringValidationError(
                "each ResultPacket must realize every required prose layer for its own claim"
            )
        mechanism_spans = [
            item
            for item in projection_spans
            if item.role == "mechanism_or_conceptual_explanation"
        ]
        diagnostic_spans = [
            item for item in projection_spans if item.role == "example_or_witness"
        ]
        boundary_spans = [item for item in projection_spans if item.role == "boundary"]
        if any(
            contracts.economic_argument_graph_ref not in item.support_refs
            for item in mechanism_spans
        ):
            raise AuthoringValidationError(
                "mechanism prose must cite the exact EconomicArgumentGraph"
            )
        if any(
            contracts.example_suite_ref not in item.support_refs
            for item in diagnostic_spans
        ):
            raise AuthoringValidationError(
                "diagnostic prose must cite the exact registered ExampleSuite"
            )
        if any(
            not {
                contracts.example_suite_ref,
                packet.claim_graph_ref,
            }.intersection(item.support_refs)
            for item in boundary_spans
        ):
            raise AuthoringValidationError(
                "boundary prose must cite an exact claim or boundary witness"
            )
    ontology = {item.object_id: item for item in paper.ontology}
    for term in unit.terminology:
        source = ontology.get(term.object_id)
        if source is None or term.formal_symbol != source.formal_symbol:
            raise AuthoringValidationError("manuscript terminology does not bind the Paper IR ontology")
        allowed_names = {source.preferred_economic_name, *source.allowed_aliases}
        if term.realized_name not in allowed_names or term.realized_name in source.forbidden_names:
            raise AuthoringValidationError("manuscript uses a forbidden or unstable economic name")
    if unit.previous_manuscript_unit_ref is not None:
        previous = _resolve_payload(
            payloads,
            unit.previous_manuscript_unit_ref,
            a.ManuscriptUnit,
            "prior manuscript unit",
        )
        brief = _resolve_payload(
            payloads, unit.revision_brief_ref, a.RevisionBrief, "revision brief"
        )
        assert isinstance(previous, a.ManuscriptUnit) and isinstance(brief, a.RevisionBrief)
        if brief.manuscript_unit_ref != unit.previous_manuscript_unit_ref:
            raise AuthoringValidationError("revision brief belongs to another prior unit")
        affected_assertions: set[str] = set()
        for finding_ref in brief.finding_refs:
            finding = _resolve_payload(
                payloads, finding_ref, a.ReviewFinding, "revision finding"
            )
            assert isinstance(finding, a.ReviewFinding)
            affected_assertions.update(finding.assertion_ids)
        current_spans = {span.assertion_id: span for span in unit.spans}
        for old_span in previous.spans:
            if old_span.assertion_id in affected_assertions:
                continue
            new_span = current_spans.get(old_span.assertion_id)
            old_semantics = old_span.model_dump(mode="json", exclude={"location"})
            new_semantics = (
                None
                if new_span is None
                else new_span.model_dump(mode="json", exclude={"location"})
            )
            if new_semantics != old_semantics:
                raise AuthoringValidationError(
                    "canonical revision changed accepted span content or semantics outside its RevisionBrief"
                )
        try:
            a.validate_manuscript_unit_update(previous, unit)
        except ValueError as exc:
            raise AuthoringValidationError(str(exc)) from exc


def _validate_economic_reconstruction(
    reconstruction: a.EconomicReconstruction,
    *,
    review: a.ReviewRecord,
    unit: a.ManuscriptUnit,
    paper: a.PaperIR,
    contracts: a.ResultContractSet,
) -> None:
    """Validate one packet-scoped economic reconstruction against exact prose."""

    spans = {item.assertion_id: item for item in unit.spans}
    projection = next(
        (
            item
            for item in paper.claim_projections
            if item.projection_id == reconstruction.claim_projection_id
        ),
        None,
    )
    packet = next(
        (
            item
            for item in contracts.result_packets
            if item.packet_id == reconstruction.result_packet_id
        ),
        None,
    )
    if (
        projection is None
        or packet is None
        or projection.claim_id != reconstruction.claim_id
        or packet.claim_projection_id != reconstruction.claim_projection_id
        or packet.claim_id != reconstruction.claim_id
    ):
        raise AuthoringValidationError(
            "economic reconstruction is not bound to one exact claim and ResultPacket"
        )
    role_requirements = (
        (
            reconstruction.mechanism_assertion_ids,
            {"mechanism_or_conceptual_explanation"},
        ),
        (reconstruction.diagnostic_assertion_ids, {"example_or_witness"}),
        (reconstruction.boundary_assertion_ids, {"boundary"}),
    )
    if any(
        assertion_id not in spans
        or spans[assertion_id].role not in roles
        or spans[assertion_id].claim_projection_id
        != reconstruction.claim_projection_id
        or spans[assertion_id].claim_id != reconstruction.claim_id
        for assertion_ids, roles in role_requirements
        for assertion_id in assertion_ids
    ):
        raise AuthoringValidationError(
            "economic reconstruction cites an assertion with the wrong prose role"
        )
    required_evidence = {
        review.manuscript_unit_ref,
        unit.manuscript_artifact_ref,
    }
    if not required_evidence.issubset(set(reconstruction.evidence_refs)):
        raise AuthoringValidationError(
            "economic reconstruction must cite the exact unit and manuscript bytes"
        )
    normalized_delta = " ".join(
        reconstruction.explanatory_delta_from_formal_statement.lower().split()
    )
    source_restatements = {
        " ".join(value.lower().split())
        for value in (
            projection.formal_statement,
            projection.scope,
            projection.semantic_translation,
        )
    }
    if normalized_delta in source_restatements:
        raise AuthoringValidationError(
            "economic reconstruction merely repeats a projected claim field"
        )
    stopwords = {
        "a", "an", "and", "are", "as", "at", "be", "because", "by",
        "for", "from", "if", "in", "is", "it", "of", "on", "or",
        "that", "the", "then", "this", "to", "under", "when", "with",
    }

    def content_tokens(value: str) -> set[str]:
        return {
            item
            for item in re.findall(r"[a-z0-9]+", value.lower())
            if len(item) > 2 and item not in stopwords
        }

    delta_tokens = content_tokens(
        reconstruction.explanatory_delta_from_formal_statement
    )
    source_tokens = set().union(
        *(content_tokens(item) for item in source_restatements)
    )
    components = (
        reconstruction.operative_force,
        reconstruction.affected_margin,
        reconstruction.serious_rival_and_separator,
    )
    if (
        len(delta_tokens) < 10
        or len(delta_tokens.difference(source_tokens)) < 4
        or any(
            len(delta_tokens.intersection(content_tokens(item))) < 2
            for item in components
        )
    ):
        raise AuthoringValidationError(
            "economic explanation lacks a distinct force-margin-rival explanatory delta"
        )
    if any(
        len(content_tokens(item)) < 4 for item in reconstruction.mechanism_steps
    ):
        raise AuthoringValidationError(
            "economic reconstruction mechanism steps are not substantively specified"
        )
    minimum_span_lengths = {
        "mechanism_or_conceptual_explanation": 80,
        "example_or_witness": 48,
        "boundary": 40,
    }
    if any(
        spans[assertion_id].location.end_offset
        - spans[assertion_id].location.start_offset
        < minimum_span_lengths[spans[assertion_id].role]
        for assertion_ids, _ in role_requirements
        for assertion_id in assertion_ids
    ):
        raise AuthoringValidationError(
            "economic reconstruction relies on an undeveloped mechanism/example/boundary span"
        )


def _validate_reader_probe_packet_coverage(
    probe: a.ReaderProbeSet,
    unit: a.ManuscriptUnit,
    reader: a.ReaderPath,
    contracts: a.ResultContractSet,
) -> None:
    """Require every canonical probe kind to reach every section result packet."""

    known_assertions = {item.assertion_id for item in unit.spans}
    known_contracts = {
        *(item.section_id for item in reader.section_contracts),
        *(item.packet_id for item in contracts.result_packets),
        *(item.roadmap_id for item in contracts.proof_roadmaps),
        *(item.assumption_id for item in contracts.assumption_contracts),
    }
    if any(
        not set(descriptor.target_assertion_ids).issubset(known_assertions)
        or not set(descriptor.target_contract_ids).issubset(known_contracts)
        for descriptor in probe.probes
    ):
        raise AuthoringValidationError(
            "reader probe descriptor targets an unknown assertion/contract"
        )
    section = next(
        item
        for item in reader.section_contracts
        if item.section_id == unit.section_contract_id
    )
    required_projection_ids = set(section.required_claim_projection_ids)
    required_packet_ids = {
        item.packet_id
        for item in contracts.result_packets
        if item.claim_projection_id in required_projection_ids
    }
    spans = {item.assertion_id: item for item in unit.spans}
    kind_roles: dict[str, tuple[frozenset[str], ...]] = {
        "question_benchmark_retell": (
            frozenset({"formal_statement", "economic_translation"}),
        ),
        "exact_scope_recovery": (
            frozenset({"formal_statement", "boundary"}),
        ),
        "assumption_role_recovery": (
            frozenset({"assumption_interpretation"}),
        ),
        "boundary_discrimination": (frozenset({"boundary"}),),
        "near_transfer": (
            frozenset({"mechanism_or_conceptual_explanation"}),
            frozenset({"boundary"}),
        ),
    }
    for descriptor in probe.probes:
        if not required_packet_ids.issubset(descriptor.target_contract_ids):
            raise AuthoringValidationError(
                "every cold-reader probe must cover every section ResultPacket"
            )
        targeted = [spans[item] for item in descriptor.target_assertion_ids]
        for projection_id in required_projection_ids:
            projection_roles = {
                item.role
                for item in targeted
                if item.claim_projection_id == projection_id
            }
            if any(
                not projection_roles.intersection(allowed_roles)
                for allowed_roles in kind_roles[descriptor.kind]
            ):
                raise AuthoringValidationError(
                    "cold-reader probe kind lacks packet-specific prose targets"
                )


def _validate_review_lineage(
    review_ref: EntityVersionRef,
    review: a.ReviewRecord,
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
) -> None:
    assignment = _resolve_payload(
        payloads, review.assignment_ref, a.CriticAssignment, "review assignment"
    )
    unit = _resolve_payload(
        payloads, review.manuscript_unit_ref, a.ManuscriptUnit, "review manuscript"
    )
    assert isinstance(assignment, a.CriticAssignment) and isinstance(unit, a.ManuscriptUnit)
    if (
        review.role != assignment.role
        or review.reviewer != assignment.assigned_actor
        and review.role != "cold_reader"
        or review.canonical_writer != assignment.canonical_writer
        or review.canonical_writer != unit.canonical_writer
        or review.reviewed_artifact_ref != unit.manuscript_artifact_ref
    ):
        raise AuthoringValidationError("review actor, assignment, context, or artifact mismatches")
    if review.role == "economic_reader":
        if not isinstance(review.assessment, a.EconomicReaderAssessment):
            raise AuthoringValidationError(
                "economic review lacks its typed reconstruction"
            )
        paper = _resolve_payload(
            payloads, unit.paper_ir_ref, a.PaperIR, "economic review Paper IR"
        )
        reader = _resolve_payload(
            payloads, unit.reader_path_ref, a.ReaderPath, "economic review ReaderPath"
        )
        contracts = _resolve_payload(
            payloads,
            unit.result_contract_set_ref,
            a.ResultContractSet,
            "economic review contracts",
        )
        assert isinstance(paper, a.PaperIR)
        assert isinstance(reader, a.ReaderPath)
        assert isinstance(contracts, a.ResultContractSet)
        section = next(
            (
                item
                for item in reader.section_contracts
                if item.section_id == unit.section_contract_id
            ),
            None,
        )
        if section is None:
            raise AuthoringValidationError(
                "economic review manuscript section is not in its ReaderPath"
            )
        required_projection_ids = set(section.required_claim_projection_ids)
        required_packet_ids = {
            item.packet_id
            for item in contracts.result_packets
            if item.claim_projection_id in required_projection_ids
        }
        reconstructions = review.assessment.reconstructions
        if (
            {item.claim_projection_id for item in reconstructions}
            != required_projection_ids
            or {item.result_packet_id for item in reconstructions}
            != required_packet_ids
        ):
            raise AuthoringValidationError(
                "economic review requires one reconstruction for every section ResultPacket"
            )
        for item in reconstructions:
            _validate_economic_reconstruction(
                item,
                review=review,
                unit=unit,
                paper=paper,
                contracts=contracts,
            )

    elif review.role == "cold_reader":
        if review.reviewer != assignment.adjudicator:
            raise AuthoringValidationError("cold review must be written by its adjudicator")
        response = _resolve_payload(
            payloads, review.reader_response_ref, a.ReaderResponse, "cold response"
        )
        assert isinstance(response, a.ReaderResponse)
        probe = _resolve_payload(payloads, response.probe_set_ref, a.ReaderProbeSet, "probe set")
        assert isinstance(probe, a.ReaderProbeSet)
        assessment = review.assessment
        if not isinstance(assessment, a.ColdReaderAssessment):
            raise AuthoringValidationError("cold review lacks per-probe adjudication")
        descriptor_keys = tuple((item.probe_id, item.kind) for item in probe.probes)
        result_keys = tuple(
            (item.probe_id, item.kind) for item in assessment.probe_results
        )
        if (
            response.manuscript_unit_ref != review.manuscript_unit_ref
            or probe.manuscript_unit_ref != review.manuscript_unit_ref
            or response.respondent != assignment.assigned_actor
            or probe.respondent != assignment.assigned_actor
            or probe.adjudicator != review.adjudicator
            or review.answer_key_artifact_ref != probe.answer_key_artifact_ref
            or assessment.response_artifact_ref != response.response_artifact_ref
            or response.answered_probe_ids
            != tuple(item.probe_id for item in probe.probes)
            or result_keys != descriptor_keys
        ):
            raise AuthoringValidationError("cold review lacks exact probe-response-key lineage")
    for finding_ref in review.finding_refs:
        finding = _resolve_payload(
            payloads, finding_ref, a.ReviewFinding, "review finding"
        )
        assert isinstance(finding, a.ReviewFinding)
        if (
            finding.assignment_ref != review.assignment_ref
            or finding.manuscript_unit_ref != review.manuscript_unit_ref
            or finding.reviewed_artifact_ref != review.reviewed_artifact_ref
            or finding.role != review.role
            or finding.critic != review.reviewer
        ):
            raise AuthoringValidationError("ReviewFinding and ReviewRecord lineage disagree")
    if not _all_assessment_flags(review.assessment):
        referenced_findings = [
            payloads.get(_entity_key(reference)) for reference in review.finding_refs
        ]
        if not any(
            isinstance(item, a.ReviewFinding) and item.blocking
            for item in referenced_findings
        ):
            raise AuthoringValidationError(
                "a failed review dimension requires an exact blocking ReviewFinding"
            )


def _validated_indices(snapshot: Snapshot) -> tuple[
    dict[tuple[str, int], EntityVersion],
    dict[tuple[str, int], ArtifactRegistration],
    dict[tuple[str, int], Decision],
    dict[tuple[str, int], a.AuthoringPayload],
    dict[tuple[str, int], t.TheoryPayload],
    TheoryReadinessReport,
]:
    entities = tuple(snapshot.entity_versions)
    artifacts = tuple(snapshot.artifacts)
    decisions = tuple(snapshot.decisions)
    entity_index = _unique_index(entities, _entity_key, "entity")
    artifact_index = _unique_index(artifacts, _artifact_key, "artifact")
    decision_index = _unique_index(decisions, _decision_key, "Decision")
    theory_report = validate_theory_projection(
        entities,
        artifacts,
        decisions,
        current_entities=snapshot.current_entities,
        current_artifacts=snapshot.current_artifacts,
        current_decisions=snapshot.current_decisions,
    )
    payloads: dict[tuple[str, int], a.AuthoringPayload] = {}
    theory_payloads: dict[tuple[str, int], t.TheoryPayload] = {}
    for entity in entities:
        key = _entity_key(entity)
        if entity.entity_type in a.AUTHORING_PAYLOAD_MODELS:
            previous = entity_index.get((entity.entity_id, entity.version - 1))
            payloads[key] = validate_authoring_entity(entity, previous)
        elif entity.entity_type in t.THEORY_PAYLOAD_MODELS and t.is_packed_theory_entity(entity):
            theory_payloads[key] = validate_theory_entity(
                entity, entity_index.get((entity.entity_id, entity.version - 1))
            )
    return (
        entity_index,
        artifact_index,
        decision_index,
        payloads,
        theory_payloads,
        theory_report,
    )


def validate_authoring_projection(snapshot: Snapshot) -> AuthoringProjectionReport:
    """Validate all Phase 3 objects while accepting a legacy projection with none."""

    try:
        (
            entity_index,
            artifact_index,
            decision_index,
            payloads,
            theory_payloads,
            theory_report,
        ) = _validated_indices(snapshot)
    except (TheoryValidationError, TypeError, ValueError) as exc:
        if isinstance(exc, AuthoringValidationError):
            raise
        raise AuthoringValidationError(str(exc)) from exc

    for key, payload in payloads.items():
        source = entity_index[key]
        for reference in _walk_exact_refs(payload):
            if isinstance(reference, SemanticFacetRef):
                target = entity_index.get((reference.entity_id, reference.version))
                if target is None:
                    raise AuthoringValidationError("authoring semantic source is unresolved")
                try:
                    actual = facet_semantic_hash(
                        target, reference.facet, reference.field_path
                    )
                except FacetPathError as exc:
                    raise AuthoringValidationError(str(exc)) from exc
                if actual != reference.semantic_hash:
                    raise AuthoringValidationError("authoring semantic source hash mismatches")
            elif isinstance(reference, EntityVersionRef):
                if _entity_key(reference) not in entity_index:
                    raise AuthoringValidationError(
                        f"{source.entity_type} has unresolved entity ref "
                        f"{reference.entity_id}@{reference.version}"
                    )
            elif isinstance(reference, ArtifactDependencyRef):
                target = artifact_index.get(_artifact_key(reference))
                if target is None or target.content_hash != reference.content_hash:
                    raise AuthoringValidationError(
                        f"{source.entity_type} has unresolved/hash-mismatched artifact ref"
                    )
            elif isinstance(reference, DecisionVersionRef):
                if _decision_key(reference) not in decision_index:
                    raise AuthoringValidationError(
                        f"{source.entity_type} has unresolved exact Decision ref"
                    )

    for key, payload in payloads.items():
        reference = EntityVersionRef(entity_id=key[0], version=key[1])
        if isinstance(payload, a.ReDerivationRecord):
            _expect_entity_type(
                entity_index, payload.package_ref, "ValidatedArgumentPackage", "re-derivation package"
            )
            expected_types = {
                payload.claim_graph_ref: "ClaimGraph",
                payload.obligation_ref: "ProofObligation",
                payload.formal_model_ref: "FormalModel",
                payload.assumption_map_ref: "AssumptionMap",
                payload.verification_record_ref: "VerificationRecord",
            }
            for exact_ref, expected in expected_types.items():
                _expect_entity_type(entity_index, exact_ref, expected, "re-derivation input")
            record = theory_payloads.get(_entity_key(payload.verification_record_ref))
            obligation = theory_payloads.get(_entity_key(payload.obligation_ref))
            package = theory_payloads.get(_entity_key(payload.package_ref))
            verification_bundle = (
                theory_payloads.get(_entity_key(package.verification_bundle_ref))
                if isinstance(package, t.ValidatedArgumentPackage)
                else None
            )
            if (
                not isinstance(record, t.VerificationRecord)
                or not isinstance(obligation, t.ProofObligation)
                or not isinstance(package, t.ValidatedArgumentPackage)
                or not isinstance(verification_bundle, t.VerificationBundle)
                or payload.claim_graph_ref != package.claim_graph_ref
                or payload.formal_model_ref != package.formal_model_ref
                or payload.assumption_map_ref != package.assumption_map_ref
                or payload.obligation_ref
                not in verification_bundle.proof_obligation_refs
                or payload.verification_record_ref
                not in verification_bundle.verification_record_refs
                or record.obligation_ref != payload.obligation_ref
                or record.verifier != payload.originating_verifier
                or obligation.claim_id != payload.claim_id
                or payload.claim_graph_ref != obligation.claim_graph_ref
                or payload.formal_model_ref != record.formal_model_ref
                or payload.assumption_map_ref != record.assumption_map_ref
                or not set(record.evidence_refs).issubset(payload.excluded_proof_artifact_refs)
                or payload.proof_author_output_ref
                not in {payload.claim_graph_ref, payload.obligation_ref}
            ):
                raise AuthoringValidationError("ReDerivationRecord scientific or exclusion lineage mismatches")
        elif isinstance(payload, a.AssuranceBundle):
            _validate_assurance_cross_refs(payload, entity_index, payloads, theory_payloads)
        elif isinstance(payload, a.ResolvedProfileManifest):
            _validate_profile(snapshot, payload, entity_index, decision_index)
        elif isinstance(payload, a.PaperIR):
            _validate_paper_ir(
                snapshot,
                payload,
                entity_index,
                payloads,
                theory_payloads,
                decision_index,
            )
            _validate_design_topology(reference, payload, payloads)
        elif isinstance(payload, a.ReaderPath):
            _resolve_payload(payloads, payload.paper_ir_ref, a.PaperIR, "ReaderPath Paper IR")
        elif isinstance(payload, a.ResultContractSet):
            _validate_result_contracts(payload, payloads, theory_payloads, entity_index)
        elif isinstance(payload, a.CriticAssignment):
            paper = _resolve_payload(payloads, payload.paper_ir_ref, a.PaperIR, "assignment Paper IR")
            assert isinstance(paper, a.PaperIR)
            if payload.canonical_writer != paper.canonical_writer:
                raise AuthoringValidationError("critic assignment canonical writer mismatches")
            if payload.sealed_context_hash != critic_assignment_contract_hash(payload):
                raise AuthoringValidationError(
                    "CriticAssignment sealed_context_hash is not its canonical information contract hash"
                )
        elif isinstance(payload, a.ManuscriptUnit):
            _validate_manuscript_cross_refs(reference, payload, payloads, entity_index)
        elif isinstance(payload, a.ReaderProbeSet):
            assignment = _resolve_payload(
                payloads, payload.assignment_ref, a.CriticAssignment, "probe assignment"
            )
            unit = _resolve_payload(
                payloads, payload.manuscript_unit_ref, a.ManuscriptUnit, "probe manuscript"
            )
            assert isinstance(assignment, a.CriticAssignment) and isinstance(unit, a.ManuscriptUnit)
            if (
                assignment.role != "cold_reader"
                or payload.probe_designer != assignment.probe_designer
                or payload.respondent != assignment.assigned_actor
                or payload.adjudicator != assignment.adjudicator
                or payload.canonical_writer != assignment.canonical_writer
                or payload.frozen_manuscript_artifact_ref != unit.manuscript_artifact_ref
            ):
                raise AuthoringValidationError("ReaderProbeSet actor or frozen-unit lineage mismatches")
        elif isinstance(payload, a.ReaderResponse):
            probe = _resolve_payload(payloads, payload.probe_set_ref, a.ReaderProbeSet, "response probe")
            assert isinstance(probe, a.ReaderProbeSet)
            if (
                payload.manuscript_unit_ref != probe.manuscript_unit_ref
                or payload.respondent != probe.respondent
                or payload.answered_probe_ids
                != tuple(item.probe_id for item in probe.probes)
            ):
                raise AuthoringValidationError(
                    "ReaderResponse substitutes respondent/manuscript or omits a probe"
                )
        elif isinstance(payload, a.ReviewFinding):
            assignment = _resolve_payload(
                payloads, payload.assignment_ref, a.CriticAssignment, "finding assignment"
            )
            unit = _resolve_payload(
                payloads, payload.manuscript_unit_ref, a.ManuscriptUnit, "finding manuscript"
            )
            assert isinstance(assignment, a.CriticAssignment) and isinstance(unit, a.ManuscriptUnit)
            if (
                payload.role != assignment.role
                or payload.critic
                != (assignment.adjudicator if payload.role == "cold_reader" else assignment.assigned_actor)
                or payload.reviewed_artifact_ref != unit.manuscript_artifact_ref
            ):
                raise AuthoringValidationError("ReviewFinding actor or manuscript lineage mismatches")
        elif isinstance(payload, a.ReviewRecord):
            _validate_review_lineage(reference, payload, payloads)
        elif isinstance(payload, a.ReviewClosure):
            _resolve_payload(payloads, payload.paper_ir_ref, a.PaperIR, "closure Paper IR")
            _resolve_payload(payloads, payload.reader_path_ref, a.ReaderPath, "closure ReaderPath")
            _resolve_payload(
                payloads,
                payload.result_contract_set_ref,
                a.ResultContractSet,
                "closure contracts",
            )
            _resolve_payload(
                payloads,
                payload.assurance_bundle_ref,
                a.AssuranceBundle,
                "closure assurance",
            )
            unit = _resolve_payload(
                payloads, payload.manuscript_unit_ref, a.ManuscriptUnit, "closure manuscript"
            )
            assert isinstance(unit, a.ManuscriptUnit)
            for role, review_ref in (
                ("formal_fidelity", payload.formal_fidelity_review_ref),
                ("economic_reader", payload.economic_reader_review_ref),
                ("cold_reader", payload.cold_reader_review_ref),
            ):
                review = _resolve_payload(
                    payloads, review_ref, a.ReviewRecord, f"closure {role} review"
                )
                assert isinstance(review, a.ReviewRecord)
                if (
                    review.role != role
                    or review.manuscript_unit_ref != payload.manuscript_unit_ref
                    or review.reviewed_artifact_ref != unit.manuscript_artifact_ref
                ):
                    raise AuthoringValidationError("ReviewClosure review lineage mismatches")
        elif isinstance(payload, a.RevisionBrief):
            closure = _resolve_payload(
                payloads, payload.review_closure_ref, a.ReviewClosure, "brief closure"
            )
            assert isinstance(closure, a.ReviewClosure)
            if (
                closure.manuscript_unit_ref != payload.manuscript_unit_ref
                or closure.revision_brief_ref != reference
            ):
                raise AuthoringValidationError("RevisionBrief and ReviewClosure do not bind each other")
        elif isinstance(payload, a.HumanEffortRecord):
            _resolve_payload(
                payloads, payload.manuscript_unit_ref, a.ManuscriptUnit, "effort manuscript"
            )

    assurance_passes: list[EntityVersionRef] = []
    for key, payload in payloads.items():
        if not isinstance(payload, a.AssuranceBundle):
            continue
        reference = EntityVersionRef(entity_id=key[0], version=key[1])
        report = _assurance_report(
            snapshot,
            reference,
            entity_index,
            payloads,
            theory_payloads,
            decision_index,
            theory_report,
        )
        if report.passed:
            assurance_passes.append(reference)
    ready: list[EntityVersionRef] = []
    for key, payload in payloads.items():
        if not isinstance(payload, a.ReviewClosure) or payload.status != "authoring_ready":
            continue
        reference = EntityVersionRef(entity_id=key[0], version=key[1])
        entity = entity_index[key]
        if not _entity_is_current_and_fresh(snapshot, entity):
            continue
        try:
            _validate_review_closure(
                snapshot,
                reference,
                payload,
                entity_index,
                payloads,
                theory_payloads,
                decision_index,
                theory_report,
            )
        except AuthoringValidationError:
            # Historical readiness is allowed to become stale.  Explicit live
            # validation and route exit retain the detailed failure.
            continue
        else:
            ready.append(reference)
    return AuthoringProjectionReport(
        parsed_entity_count=len(payloads),
        assurance_pass_refs=tuple(sorted(assurance_passes, key=_entity_key)),
        authoring_ready_refs=tuple(sorted(ready, key=_entity_key)),
    )


def _all_assessment_flags(assessment: BaseModel) -> bool:
    ignored = {"role", "entailment_checks", "response_artifact_ref"}
    return all(
        value
        for field_name, value in assessment.__dict__.items()
        if field_name not in ignored and isinstance(value, bool)
    )


def _validate_review_closure(
    snapshot: Snapshot,
    closure_ref: EntityVersionRef,
    closure: a.ReviewClosure,
    entity_index: Mapping[tuple[str, int], EntityVersion],
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    theory_payloads: Mapping[tuple[str, int], t.TheoryPayload],
    decision_index: Mapping[tuple[str, int], Decision],
    theory_report: TheoryReadinessReport,
) -> None:
    unit = _resolve_payload(
        payloads, closure.manuscript_unit_ref, a.ManuscriptUnit, "closure manuscript"
    )
    paper = _resolve_payload(payloads, closure.paper_ir_ref, a.PaperIR, "closure Paper IR")
    reader = _resolve_payload(
        payloads, closure.reader_path_ref, a.ReaderPath, "closure ReaderPath"
    )
    contracts = _resolve_payload(
        payloads,
        closure.result_contract_set_ref,
        a.ResultContractSet,
        "closure ResultContractSet",
    )
    assurance = _resolve_payload(
        payloads,
        closure.assurance_bundle_ref,
        a.AssuranceBundle,
        "closure assurance",
    )
    assert isinstance(unit, a.ManuscriptUnit)
    assert isinstance(paper, a.PaperIR)
    assert isinstance(reader, a.ReaderPath)
    assert isinstance(contracts, a.ResultContractSet)
    assert isinstance(assurance, a.AssuranceBundle)
    if (
        unit.paper_ir_ref != closure.paper_ir_ref
        or unit.reader_path_ref != closure.reader_path_ref
        or unit.result_contract_set_ref != closure.result_contract_set_ref
        or reader.paper_ir_ref != closure.paper_ir_ref
        or contracts.paper_ir_ref != closure.paper_ir_ref
        or contracts.reader_path_ref != closure.reader_path_ref
        or paper.assurance_bundle_ref != closure.assurance_bundle_ref
        or closure.compiler_mode != paper.compiler_mode
    ):
        raise AuthoringValidationError("ReviewClosure mixes different design/manuscript lineages")

    named_reviews = (
        ("formal_fidelity", closure.formal_fidelity_review_ref),
        ("economic_reader", closure.economic_reader_review_ref),
        ("cold_reader", closure.cold_reader_review_ref),
    )
    reviews: dict[str, a.ReviewRecord] = {}
    for role, reference in named_reviews:
        review = _resolve_payload(payloads, reference, a.ReviewRecord, f"{role} review")
        assert isinstance(review, a.ReviewRecord)
        review_entity = entity_index[_entity_key(reference)]
        if (
            review.role != role
            or review.manuscript_unit_ref != closure.manuscript_unit_ref
            or review.reviewed_artifact_ref != unit.manuscript_artifact_ref
            or not _entity_is_current_and_fresh(snapshot, review_entity)
        ):
            raise AuthoringValidationError("closure review is stale or reviews another manuscript")
        reviews[role] = review
    if len({_actor_key(review.reviewer) for review in reviews.values()}) != 3:
        raise AuthoringValidationError("the three closure reviews require distinct actors")

    all_finding_refs = {
        reference for review in reviews.values() for reference in review.finding_refs
    }
    findings: list[a.ReviewFinding] = []
    for reference in all_finding_refs:
        finding = _resolve_payload(payloads, reference, a.ReviewFinding, "closure finding")
        assert isinstance(finding, a.ReviewFinding)
        findings.append(finding)
    blocking_ids = tuple(
        sorted(finding.finding_id for finding in findings if finding.blocking)
    )
    if tuple(sorted(closure.blocking_finding_ids)) != blocking_ids:
        raise AuthoringValidationError("ReviewClosure blocking findings are not derived from its reviews")

    formal = reviews["formal_fidelity"]
    economic = reviews["economic_reader"]
    cold = reviews["cold_reader"]
    if not isinstance(formal.assessment, a.FormalFidelityAssessment):
        raise AuthoringValidationError("formal-fidelity review has the wrong assessment")
    if not isinstance(economic.assessment, a.EconomicReaderAssessment):
        raise AuthoringValidationError("economic review has the wrong assessment")
    if not isinstance(cold.assessment, a.ColdReaderAssessment):
        raise AuthoringValidationError("cold review has the wrong assessment")
    assertion_ids = {span.assertion_id for span in unit.spans}
    entailment_ids = {item.assertion_id for item in formal.assessment.entailment_checks}
    spans_by_id = {span.assertion_id: span for span in unit.spans}

    def entailment_matches_span(check: a.EntailmentCheck) -> bool:
        span = spans_by_id.get(check.assertion_id)
        if span is None or check.outcome != "passed":
            return False
        if not any(
            isinstance(reference, EntityVersionRef)
            and reference == span.claim_graph_ref
            for reference in check.source_refs
        ):
            return False
        if span.wording_strength == "exact":
            return (
                check.scope_relation == "equal"
                and check.conclusion_relation == "equivalent"
                and (
                    span.role != "formal_statement"
                    or span.presentation == "theorem_statement"
                )
            )
        if span.wording_strength == "entailed_equivalent":
            return (
                check.scope_relation == "equal"
                and check.conclusion_relation == "equivalent"
            )
        if span.wording_strength == "entailed_weaker":
            return (
                check.scope_relation in {"equal", "subset"}
                and check.conclusion_relation in {"equivalent", "weaker"}
                and (
                    check.scope_relation == "subset"
                    or check.conclusion_relation == "weaker"
                )
            )
        return (
            span.wording_strength == "explicit_conjecture"
            and span.role == "conjecture"
            and span.presentation == "conjecture"
            and check.conclusion_relation == "explicit_conjecture"
        )

    exact_entailment = assertion_ids == entailment_ids and all(
        entailment_matches_span(item)
        for item in formal.assessment.entailment_checks
    )

    profile = _resolve_payload(
        payloads,
        paper.resolved_profile_manifest_ref,
        a.ResolvedProfileManifest,
        "closure profile",
    )
    assert isinstance(profile, a.ResolvedProfileManifest)
    package_entity = entity_index.get(_entity_key(paper.package_ref))
    profile_entity = entity_index.get(_entity_key(paper.resolved_profile_manifest_ref))
    exact_authority = (
        package_entity is not None
        and profile_entity is not None
        and _entity_is_current_and_fresh(snapshot, package_entity)
        and _entity_is_current_and_fresh(snapshot, profile_entity)
        and paper.g5_decision_ref is not None
        and paper.g5_decision_ref == assurance.g5_decision_ref
        and all(
            (
                decision := decision_index.get(
                    _decision_key(getattr(profile, field_name))
                )
            )
            is not None
            and _decision_is_current_confirmed_human(
                snapshot, decision, expected_kind=expected_kind
            )
            for field_name, expected_kind in _PROFILE_DECISION_KINDS.items()
        )
    )
    assurance_report = _assurance_report(
        snapshot,
        closure.assurance_bundle_ref,
        entity_index,
        payloads,
        theory_payloads,
        decision_index,
        theory_report,
    )
    source_trace = all(
        snapshot.current_entities.get(source.entity_id) == source.version
        and facet_semantic_hash(
            entity_index[(source.entity_id, source.version)],
            source.facet,
            source.field_path,
        )
        == source.semantic_hash
        for span in unit.spans
        for source in span.source_fields
    )
    required_roles = {
        "formal_statement",
        "economic_translation",
        "mechanism_or_conceptual_explanation",
        "example_or_witness",
        "boundary",
        "proof_roadmap",
        "consequence",
    }
    section = next(
        item
        for item in reader.section_contracts
        if item.section_id == unit.section_contract_id
    )
    spans_by_projection: dict[str, set[str]] = {}
    for span in unit.spans:
        spans_by_projection.setdefault(span.claim_projection_id, set()).add(span.role)
    packet_by_projection = {
        item.claim_projection_id: item for item in contracts.result_packets
    }
    layer_realization = bool(section.required_claim_projection_ids)
    for projection_id in section.required_claim_projection_ids:
        packet = packet_by_projection.get(projection_id)
        projection = next(
            (
                item
                for item in paper.claim_projections
                if item.projection_id == projection_id
            ),
            None,
        )
        packet_roles = set(required_roles)
        if projection is not None and any(
            projection.claim_id in item.supported_claim_ids
            for item in contracts.assumption_contracts
        ):
            packet_roles.add("assumption_interpretation")
        if (
            packet is None
            or projection is None
            or not packet_roles.issubset(spans_by_projection.get(projection_id, set()))
        ):
            layer_realization = False
    formal_finding_clear = not any(
        finding.role == "formal_fidelity"
        and finding.severity == "critical"
        and finding.blocking
        for finding in findings
    )
    formal_pass = (
        _all_assessment_flags(formal.assessment)
        and exact_entailment
        and formal_finding_clear
    )
    economic_pass = _all_assessment_flags(economic.assessment) and not any(
        finding.role == "economic_reader" and finding.blocking for finding in findings
    )
    cold_pass = _all_assessment_flags(cold.assessment) and not any(
        finding.role == "cold_reader" and finding.blocking for finding in findings
    )
    reader_and_terms = len(unit.terminology) == len(paper.ontology) and {
        item.object_id for item in unit.terminology
    } == {item.object_id for item in paper.ontology}
    no_leak_finding = not any(
        finding.category == "governance_leakage" and finding.blocking
        for finding in findings
    )
    canonical_integration = (
        len({item.formal_symbol for item in unit.terminology}) == len(unit.terminology)
        and len({item.realized_name for item in unit.terminology}) == len(unit.terminology)
        and all(
            packet.claim_projection_id
            in {projection.projection_id for projection in paper.claim_projections}
            for packet in contracts.result_packets
        )
    )
    pending_human = False
    if closure.revision_brief_ref is not None:
        brief = _resolve_payload(
            payloads, closure.revision_brief_ref, a.RevisionBrief, "closure revision brief"
        )
        assert isinstance(brief, a.RevisionBrief)
        if (
            brief.manuscript_unit_ref != closure.manuscript_unit_ref
            or brief.review_closure_ref != closure_ref
            or {reference for reference in brief.finding_refs}
            != {
                reference
                for reference in all_finding_refs
                if isinstance(payloads.get(_entity_key(reference)), a.ReviewFinding)
                and payloads[_entity_key(reference)].blocking
            }
        ):
            raise AuthoringValidationError("RevisionBrief does not cover this exact closure")
        pending_human = any(
            item.action == "request_human_decision" and item.blocking
            for item in brief.instructions
        )
    no_blockers = not blocking_ids and not pending_human

    actual = {
        "exact_g5_and_profile": exact_authority,
        "assurance_pass": assurance_report.passed,
        "exact_span_trace": source_trace,
        "layer_realization": layer_realization,
        "scope_and_assumptions": exact_entailment
        and formal.assessment.scope_preserved
        and formal.assessment.assumptions_preserved,
        "bounded_evidentiary_language": formal.assessment.proof_language_honest
        and formal.assessment.numerical_evidence_bounded,
        "formal_fidelity": formal_pass,
        "economic_explanation": economic_pass,
        "cold_reader_transfer": cold_pass,
        "reader_dag_and_terminology": reader_and_terms,
        "no_governance_or_probe_leakage": no_leak_finding,
        "canonical_integration": canonical_integration,
        "blocking_findings": no_blockers,
    }
    for check in closure.checks:
        expected = "passed" if actual[check.check_id] else "failed"
        if check.outcome != expected:
            raise AuthoringValidationError(
                f"ReviewClosure check {check.check_id} is self-certified rather than derived"
            )
    derived_ready = closure.compiler_mode != "preview" and all(actual.values())
    if (closure.status == "authoring_ready") != derived_ready:
        raise AuthoringValidationError(
            "ReviewClosure status disagrees with derived AUTHORING-READY-0.1"
        )


def validate_authoring_ready(
    snapshot: Snapshot,
    closure_ref: EntityVersionRef,
    *,
    manuscript_text: str | None = None,
) -> None:
    """Require a derived authoring-ready closure, optionally checking exact bytes."""

    (
        entity_index,
        _,
        decision_index,
        payloads,
        theory_payloads,
        theory_report,
    ) = _validated_indices(snapshot)
    closure = payloads.get(_entity_key(closure_ref))
    if not isinstance(closure, a.ReviewClosure):
        raise AuthoringValidationError("closure_ref does not resolve to ReviewClosure")
    readiness_refs = (
        closure_ref,
        closure.paper_ir_ref,
        closure.reader_path_ref,
        closure.result_contract_set_ref,
        closure.assurance_bundle_ref,
        closure.manuscript_unit_ref,
        closure.formal_fidelity_review_ref,
        closure.economic_reader_review_ref,
        closure.cold_reader_review_ref,
    )
    if any(
        (entity := entity_index.get(_entity_key(reference))) is None
        or snapshot.current_entities.get(reference.entity_id) != reference.version
        or not _entity_is_current_and_fresh(snapshot, entity)
        for reference in readiness_refs
    ):
        raise AuthoringValidationError(
            "AUTHORING-READY requires a current and fresh closure/design/review chain"
        )
    _validate_review_closure(
        snapshot,
        closure_ref,
        closure,
        entity_index,
        payloads,
        theory_payloads,
        decision_index,
        theory_report,
    )
    if closure.status != "authoring_ready":
        raise AuthoringValidationError("AUTHORING-READY-0.1 is blocked")
    if manuscript_text is not None:
        unit = payloads[_entity_key(closure.manuscript_unit_ref)]
        assert isinstance(unit, a.ManuscriptUnit)
        validate_manuscript_spans_and_text(unit, manuscript_text)


_LEAK_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "internal_gate_label",
        re.compile(
            r"(?<![A-Za-z0-9_])G[1-5](?:_(?:question_benchmark|mechanism|formal_base|result_investment|argument_validation))?(?![A-Za-z0-9_])",
            re.IGNORECASE,
        ),
    ),
    (
        "canonical_id_pattern",
        re.compile(
            r"\b(?:entity|relation)(?:_id|[.:-][A-Za-z][A-Za-z0-9_.:-]*(?:@\d+)?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "schema_identifier",
        re.compile(
            r"(?:econ_theorist\.(?:authoring|theory)/\S+|\bschema_(?:id|version)\b|\$schema)",
            re.IGNORECASE,
        ),
    ),
    (
        "context_manifest_key",
        re.compile(
            r"\b(?:context_manifest(?:_hash|_id)?|compiled_context_hash|route_run_id|source_state_revision|upstream_projection_hash)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "prompt_directive",
        re.compile(
            r"\b(?:system prompt|developer message|prompt directive|ignore (?:all )?previous instructions)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "hidden_evaluation_artifact",
        re.compile(
            r"\b(?:ReaderProbeSet|PreResultBrief|answer[- ]key artifact|hidden probe|gold prose|confirmatory_holdout)\b",
            re.IGNORECASE,
        ),
    ),
)


def lint_authoring_governance_leakage(
    text: str, *, route_ids: Iterable[str] = _PHASE3_ROUTES
) -> tuple[GovernanceLeak, ...]:
    """Run the narrow, versioned ``AUTHORING-LEAKAGE-LINT-0.1`` rules."""

    if not isinstance(text, str):
        raise TypeError("authoring leakage lint requires text")
    findings: list[GovernanceLeak] = []
    for rule_id, pattern in _LEAK_RULES:
        findings.extend(
            GovernanceLeak(rule_id, match.start(), match.end(), match.group(0))
            for match in pattern.finditer(text)
        )
    route_values = tuple(sorted(set(route_ids), key=lambda item: (-len(item), item)))
    if route_values:
        route_pattern = re.compile(
            r"(?<![A-Za-z0-9_.:-])(?:"
            + "|".join(re.escape(item) for item in route_values)
            + r")(?![A-Za-z0-9_.:-])"
        )
        findings.extend(
            GovernanceLeak("exact_route_id", match.start(), match.end(), match.group(0))
            for match in route_pattern.finditer(text)
        )
    return tuple(sorted(findings, key=lambda item: (item.start_offset, item.rule_id)))


_NUMERICAL_AS_PROOF = re.compile(
    r"(?is)\b(?:finite (?:grid|search|enumeration)|simulation|numerical (?:check|experiment)|failure to find a counterexample)\b"
    r"[^.!?]{0,160}\b(?:prove[sd]?|establish(?:es|ed)? universally|guarantee[sd]? for all)\b"
)


def validate_manuscript_spans_and_text(
    unit: a.ManuscriptUnit,
    text: str,
    *,
    check_artifact_hash: bool = True,
) -> None:
    """Validate exact manuscript bytes, span hashes, and narrow leakage rules."""

    if not isinstance(text, str):
        raise TypeError("manuscript text must be a string")
    encoded = text.encode("utf-8")
    if check_artifact_hash and sha256_digest(encoded) != unit.manuscript_artifact_ref.content_hash:
        raise AuthoringValidationError("manuscript bytes do not match the registered artifact hash")
    for span in unit.spans:
        if span.location.end_offset > len(text):
            raise AuthoringValidationError("manuscript span lies outside the artifact text")
        exact_text = text[span.location.start_offset : span.location.end_offset]
        if sha256_digest(exact_text.encode("utf-8")) != span.text_hash:
            raise AuthoringValidationError(
                f"manuscript assertion {span.assertion_id} text hash mismatches"
            )
        if span.presentation == "theorem_statement" and _NUMERICAL_AS_PROOF.search(exact_text):
            raise AuthoringValidationError("finite or numerical evidence is described as universal proof")
    covered = bytearray(len(text))
    for span in unit.spans:
        covered[span.location.start_offset : span.location.end_offset] = b"\x01" * (
            span.location.end_offset - span.location.start_offset
        )
    if any(not character.isspace() and not covered[index] for index, character in enumerate(text)):
        raise AuthoringValidationError(
            "manuscript contains undeclared consequential prose outside typed spans"
        )
    if _NUMERICAL_AS_PROOF.search(text):
        raise AuthoringValidationError("finite or numerical evidence is described as universal proof")
    leaks = lint_authoring_governance_leakage(text)
    if leaks:
        first = leaks[0]
        raise AuthoringValidationError(
            f"{AUTHORING_LEAKAGE_LINT_VERSION} {first.rule_id} at "
            f"{first.start_offset}:{first.end_offset}"
        )


validate_manuscript_text = validate_manuscript_spans_and_text


def _require_counts(route: RouteSpecV3, entities: Iterable[EntityVersion], *, output: bool) -> None:
    counts: dict[str, int] = {}
    for entity in entities:
        counts[entity.entity_type] = counts.get(entity.entity_type, 0) + 1
    requirements = (
        route.required_output_entities if output else route.required_input_entities
    )
    if not output:
        allowed_types = {item.entity_type for item in requirements}
        unexpected = sorted(set(counts).difference(allowed_types))
        if unexpected:
            raise AuthoringValidationError(
                f"route {route.route_id} received foreign input types: "
                + ", ".join(unexpected)
            )
    for requirement in requirements:
        count = counts.get(requirement.entity_type, 0)
        if count < requirement.min_count:
            raise AuthoringValidationError(
                f"route {route.route_id} requires at least {requirement.min_count} "
                f"{requirement.entity_type}, got {count}"
            )
        if requirement.max_count is not None and count > requirement.max_count:
            raise AuthoringValidationError(
                f"route {route.route_id} permits at most {requirement.max_count} "
                f"{requirement.entity_type}, got {count}"
            )


def _validate_exact_route_input_lineage(
    route_id: str,
    input_by_type: Mapping[str, Sequence[EntityVersionRef]],
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
) -> None:
    """Close same-type substitution channels inside a route's actual context.

    Cardinality alone is insufficient: a critic could otherwise receive one
    current PaperIR while its output cites another current PaperIR already in
    the snapshot.  These checks bind the exact selected inputs to one internal
    authoring topology before output-specific checks bind the result to it.
    """

    def fail(detail: str) -> None:
        raise AuthoringValidationError(f"exact input lineage mismatch: {detail}")

    def refs(entity_type: str) -> tuple[EntityVersionRef, ...]:
        return tuple(input_by_type.get(entity_type, ()))

    def one_ref(entity_type: str) -> EntityVersionRef:
        values = refs(entity_type)
        if len(values) != 1:
            fail(f"{route_id} requires one exact {entity_type}")
        return values[0]

    def one_payload(
        entity_type: str, expected: type[a.AuthoringPayload]
    ) -> tuple[EntityVersionRef, a.AuthoringPayload]:
        reference = one_ref(entity_type)
        value = payloads.get(_entity_key(reference))
        if not isinstance(value, expected):
            fail(f"{route_id} cannot resolve its exact {entity_type}")
        return reference, value

    if route_id == "verify.independent_rederivation":
        if len(refs("ProofObligation")) != 1:
            fail("one blind re-derivation may consume only one ProofObligation")
        return

    if route_id == "audit.argument_assurance":
        return

    if route_id == "design.reader_path":
        return

    if route_id == "compose.manuscript_unit":
        paper_ref, paper_value = one_payload("PaperIR", a.PaperIR)
        profile_ref, _ = one_payload("ResolvedProfileManifest", a.ResolvedProfileManifest)
        reader_ref, reader_value = one_payload("ReaderPath", a.ReaderPath)
        contracts_ref, contracts_value = one_payload("ResultContractSet", a.ResultContractSet)
        package_ref = one_ref("ValidatedArgumentPackage")
        assert isinstance(paper_value, a.PaperIR)
        assert isinstance(reader_value, a.ReaderPath)
        assert isinstance(contracts_value, a.ResultContractSet)
        if (
            paper_value.package_ref != package_ref
            or paper_value.resolved_profile_manifest_ref != profile_ref
            or reader_value.paper_ir_ref != paper_ref
            or contracts_value.paper_ir_ref != paper_ref
            or contracts_value.reader_path_ref != reader_ref
        ):
            fail("compose inputs do not form one PaperIR/ReaderPath/contract topology")
        assurance_refs = refs("AssuranceBundle")
        expected_assurance = (
            ()
            if paper_value.assurance_bundle_ref is None
            else (paper_value.assurance_bundle_ref,)
        )
        if assurance_refs != expected_assurance:
            fail("compose AssuranceBundle is not the one named by PaperIR")

        prior_refs = refs("ManuscriptUnit")
        closure_refs = refs("ReviewClosure")
        brief_refs = refs("RevisionBrief")
        if not prior_refs:
            if closure_refs or brief_refs:
                fail("initial composition cannot consume a closure or revision brief")
            return
        if len(prior_refs) != 1 or len(closure_refs) != 1:
            fail("revision/submission requires one exact prior unit and closure")
        prior_ref = prior_refs[0]
        closure_ref = closure_refs[0]
        prior = payloads.get(_entity_key(prior_ref))
        closure = payloads.get(_entity_key(closure_ref))
        if not isinstance(prior, a.ManuscriptUnit) or not isinstance(
            closure, a.ReviewClosure
        ):
            fail("revision/submission prior unit or closure cannot be resolved")
        if closure.manuscript_unit_ref != prior_ref:
            fail("composition closure does not govern the selected prior unit")
        if paper_value.compiler_mode == "submission":
            if brief_refs or closure.status != "authoring_ready" or closure.compiler_mode != "working":
                fail("submission must consume an authoring-ready working unit without a brief")
            return
        if len(brief_refs) != 1:
            fail("a non-submission revision requires one exact RevisionBrief")
        brief_ref = brief_refs[0]
        brief = payloads.get(_entity_key(brief_ref))
        if (
            not isinstance(brief, a.RevisionBrief)
            or closure.status != "blocked"
            or brief.manuscript_unit_ref != prior_ref
            or brief.review_closure_ref != closure_ref
            or closure.revision_brief_ref != brief_ref
        ):
            fail("revision brief, blocked closure, and prior unit do not agree")
        return

    if route_id == "review.manuscript_unit":
        assignment_ref, assignment_value = one_payload("CriticAssignment", a.CriticAssignment)
        unit_ref, unit_value = one_payload("ManuscriptUnit", a.ManuscriptUnit)
        paper_ref, _ = one_payload("PaperIR", a.PaperIR)
        contracts_ref, contracts_value = one_payload("ResultContractSet", a.ResultContractSet)
        assert isinstance(assignment_value, a.CriticAssignment)
        assert isinstance(unit_value, a.ManuscriptUnit)
        assert isinstance(contracts_value, a.ResultContractSet)
        if (
            unit_value.paper_ir_ref != paper_ref
            or unit_value.result_contract_set_ref != contracts_ref
            or assignment_value.paper_ir_ref != paper_ref
            or assignment_value.reader_path_ref != unit_value.reader_path_ref
            or assignment_value.result_contract_set_ref != contracts_ref
            or assignment_value.canonical_writer != unit_value.canonical_writer
            or contracts_value.paper_ir_ref != paper_ref
            or contracts_value.reader_path_ref != unit_value.reader_path_ref
        ):
            fail(
                f"review inputs {assignment_ref.entity_id}/{unit_ref.entity_id} "
                "do not share one exact design"
            )
        return

    if route_id == "prepare.reader_probe":
        _, assignment_value = one_payload("CriticAssignment", a.CriticAssignment)
        _, unit_value = one_payload("ManuscriptUnit", a.ManuscriptUnit)
        reader_ref, reader_value = one_payload("ReaderPath", a.ReaderPath)
        assert isinstance(assignment_value, a.CriticAssignment)
        assert isinstance(unit_value, a.ManuscriptUnit)
        assert isinstance(reader_value, a.ReaderPath)
        if (
            assignment_value.role != "cold_reader"
            or assignment_value.paper_ir_ref != unit_value.paper_ir_ref
            or assignment_value.reader_path_ref != reader_ref
            or assignment_value.result_contract_set_ref
            != unit_value.result_contract_set_ref
            or unit_value.reader_path_ref != reader_ref
            or reader_value.paper_ir_ref != unit_value.paper_ir_ref
        ):
            fail("probe preparation inputs do not share one cold-reader topology")
        return

    if route_id in {"answer.reader_probe", "adjudicate.reader_probe"}:
        assignment_ref, assignment_value = one_payload("CriticAssignment", a.CriticAssignment)
        unit_ref, unit_value = one_payload("ManuscriptUnit", a.ManuscriptUnit)
        probe_ref, probe_value = one_payload("ReaderProbeSet", a.ReaderProbeSet)
        assert isinstance(assignment_value, a.CriticAssignment)
        assert isinstance(unit_value, a.ManuscriptUnit)
        assert isinstance(probe_value, a.ReaderProbeSet)
        if (
            assignment_value.role != "cold_reader"
            or probe_value.assignment_ref != assignment_ref
            or probe_value.manuscript_unit_ref != unit_ref
            or probe_value.frozen_manuscript_artifact_ref
            != unit_value.manuscript_artifact_ref
            or assignment_value.paper_ir_ref != unit_value.paper_ir_ref
            or assignment_value.reader_path_ref != unit_value.reader_path_ref
            or assignment_value.result_contract_set_ref
            != unit_value.result_contract_set_ref
        ):
            fail(f"{route_id} inputs do not share one exact probe/manuscript topology")
        if route_id == "adjudicate.reader_probe":
            response_ref, response_value = one_payload("ReaderResponse", a.ReaderResponse)
            assert isinstance(response_value, a.ReaderResponse)
            if (
                response_value.probe_set_ref != probe_ref
                or response_value.manuscript_unit_ref != unit_ref
                or response_value.respondent != probe_value.respondent
            ):
                fail(
                    f"adjudication response {response_ref.entity_id} belongs to another probe or unit"
                )
        return

    if route_id == "close.manuscript_review":
        unit_ref, unit_value = one_payload("ManuscriptUnit", a.ManuscriptUnit)
        assert isinstance(unit_value, a.ManuscriptUnit)
        review_refs = refs("ReviewRecord")
        reviews = tuple(payloads.get(_entity_key(reference)) for reference in review_refs)
        if (
            len(review_refs) != 3
            or any(not isinstance(item, a.ReviewRecord) for item in reviews)
            or {item.role for item in reviews if isinstance(item, a.ReviewRecord)}
            != {"formal_fidelity", "economic_reader", "cold_reader"}
            or any(
                isinstance(item, a.ReviewRecord)
                and (
                    item.manuscript_unit_ref != unit_ref
                    or item.reviewed_artifact_ref != unit_value.manuscript_artifact_ref
                )
                for item in reviews
            )
        ):
            fail("closure reviews do not all govern the selected manuscript bytes")
        paper = payloads.get(_entity_key(unit_value.paper_ir_ref))
        if not isinstance(paper, a.PaperIR) or paper.assurance_bundle_ref is None:
            fail("closure manuscript lacks its exact assured PaperIR")
        if refs("AssuranceBundle") != (paper.assurance_bundle_ref,):
            fail("closure AssuranceBundle is not the one named by the manuscript PaperIR")
        return

    if route_id == "record.human_effort":
        unit_ref = one_ref("ManuscriptUnit")
        prior_refs = refs("HumanEffortRecord")
        if prior_refs:
            if len(prior_refs) != 1:
                fail("effort append accepts only one exact prior record")
            prior = payloads.get(_entity_key(prior_refs[0]))
            if not isinstance(prior, a.HumanEffortRecord) or prior.manuscript_unit_ref != unit_ref:
                fail("prior effort record belongs to another ManuscriptUnit")
        return


def _validate_exact_package_input_lineage(
    route_id: str,
    input_by_type: Mapping[str, Sequence[EntityVersionRef]],
    theory_payloads: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    """Bind assurance authority to the scientific objects inside that VAP."""

    if route_id not in _ASSURANCE_ROUTES:
        return

    def fail(detail: str) -> None:
        raise AuthoringValidationError(
            f"exact package input lineage mismatch: {detail}"
        )

    def one(entity_type: str) -> EntityVersionRef:
        values = tuple(input_by_type.get(entity_type, ()))
        if len(values) != 1:
            fail(f"{route_id} requires one exact {entity_type}")
        return values[0]

    package_ref = one("ValidatedArgumentPackage")
    package = theory_payloads.get(_entity_key(package_ref))
    if not isinstance(package, t.ValidatedArgumentPackage):
        fail("selected ValidatedArgumentPackage cannot be resolved")
    if (
        one("ClaimGraph") != package.claim_graph_ref
        or one("FormalModel") != package.formal_model_ref
        or one("AssumptionMap") != package.assumption_map_ref
    ):
        fail("claim graph, formal model, or assumption map belongs to another package")
    verification_bundle = theory_payloads.get(
        _entity_key(package.verification_bundle_ref)
    )
    if not isinstance(verification_bundle, t.VerificationBundle):
        fail("package VerificationBundle cannot be resolved")

    obligation_inputs = set(input_by_type.get("ProofObligation", ()))
    if route_id == "verify.independent_rederivation":
        if (
            len(obligation_inputs) != 1
            or not obligation_inputs.issubset(
                set(verification_bundle.proof_obligation_refs)
            )
        ):
            fail("selected ProofObligation is not the package bundle obligation")
        return

    if (
        one("VerificationBundle") != package.verification_bundle_ref
        or obligation_inputs != set(verification_bundle.proof_obligation_refs)
        or set(input_by_type.get("VerificationRecord", ()))
        != set(verification_bundle.verification_record_refs)
    ):
        fail(
            "assurance audit inputs do not equal the package VerificationBundle closure"
        )


def _input_mode_and_lineage(
    snapshot: Snapshot,
    route: RouteSpecV3,
    references: tuple[EntityVersionRef, ...],
    entities: tuple[EntityVersion, ...],
    payloads: Mapping[tuple[str, int], a.AuthoringPayload],
    theory_payloads: Mapping[tuple[str, int], t.TheoryPayload],
    *,
    actor: Actor,
    compiler_mode: str | None,
) -> AuthoringRouteEntryReport:
    by_type: dict[str, list[tuple[EntityVersionRef, EntityVersion]]] = {}
    for reference, entity in zip(references, entities):
        by_type.setdefault(entity.entity_type, []).append((reference, entity))
    input_refs_by_type = {
        entity_type: tuple(reference for reference, _entity in values)
        for entity_type, values in by_type.items()
    }
    _validate_exact_package_input_lineage(
        route.route_id, input_refs_by_type, theory_payloads
    )
    package_ref = (
        by_type.get("ValidatedArgumentPackage", [(None, None)])[0][0]
        if by_type.get("ValidatedArgumentPackage")
        else None
    )
    assurance_ref = (
        by_type.get("AssuranceBundle", [(None, None)])[0][0]
        if by_type.get("AssuranceBundle")
        else None
    )
    paper: a.PaperIR | None = None
    if by_type.get("PaperIR"):
        value = payloads.get(_entity_key(by_type["PaperIR"][0][0]))
        if isinstance(value, a.PaperIR):
            paper = value
    if paper is None and by_type.get("ManuscriptUnit"):
        unit = payloads.get(_entity_key(by_type["ManuscriptUnit"][0][0]))
        if isinstance(unit, a.ManuscriptUnit):
            value = payloads.get(_entity_key(unit.paper_ir_ref))
            if isinstance(value, a.PaperIR):
                paper = value
    inferred_mode = paper.compiler_mode if paper is not None else compiler_mode
    if compiler_mode is not None and inferred_mode is not None and compiler_mode != inferred_mode:
        raise AuthoringValidationError("begin-time compiler mode disagrees with the exact Paper IR")
    mode = inferred_mode
    if route.route_id == "design.reader_path":
        if compiler_mode is not None:
            mode = compiler_mode
        elif assurance_ref is None:
            mode = "preview"
        else:
            promoted_closure_ids = {
                decision.subject_ref
                for decision in snapshot.decisions
                if decision.decision_kind == "manuscript_version_promotion"
                and _decision_is_current_confirmed_human(
                    snapshot,
                    decision,
                    expected_kind="manuscript_version_promotion",
                )
            }
            has_live_promotion = any(
                entity.entity_id in promoted_closure_ids
                and snapshot.current_entities.get(entity.entity_id) == entity.version
                and isinstance(payloads.get(_entity_key(entity)), a.ReviewClosure)
                and payloads[_entity_key(entity)].status == "authoring_ready"
                for entity in snapshot.entity_versions
            )
            mode = "submission" if has_live_promotion else "working"
    if mode not in {None, "preview", "working", "submission"}:
        raise AuthoringValidationError("unknown authoring compiler mode")

    canonical_writer = paper.canonical_writer if paper is not None else None
    if route.route_id in _ASSURANCE_ROUTES:
        if package_ref is None:
            raise AuthoringValidationError("assurance route lacks its exact package")
        package = theory_payloads.get(_entity_key(package_ref))
        if not isinstance(package, t.ValidatedArgumentPackage) or package.release_mode != "production_candidate":
            raise AuthoringValidationError("assurance routes require a production-candidate VAP")
        decisions = {_decision_key(item): item for item in snapshot.decisions}
        matching_g5 = [
            decision
            for decision in decisions.values()
            if _decision_is_current_confirmed_human(
                snapshot, decision, expected_kind="G5_argument_validation"
            )
            and decision.machine_outcome == "approve"
            and decision.selected_option == "approve"
            and decision.subject_ref == package.g5_dossier_ref.entity_id
            and decision.scope_ref == package.question_ref.entity_id
        ]
        if len(matching_g5) != 1:
            raise AuthoringValidationError(
                "assurance routes require one exact current human-approved G5"
            )
    if route.route_id == "verify.independent_rederivation":
        if actor.kind == "deterministic_tool":
            raise AuthoringValidationError("independent re-derivation requires a human or agent")
        obligation_refs = {
            item[0] for item in by_type.get("ProofObligation", ())
        }
        assert isinstance(package, t.ValidatedArgumentPackage)
        verification_bundle = theory_payloads.get(
            _entity_key(package.verification_bundle_ref)
        )
        assert isinstance(verification_bundle, t.VerificationBundle)
        records = []
        for reference in verification_bundle.verification_record_refs:
            value = theory_payloads.get(_entity_key(reference))
            if (
                isinstance(value, t.VerificationRecord)
                and value.obligation_ref in obligation_refs
            ):
                records.append(value)
        if len(records) != 1:
            raise AuthoringValidationError(
                "blind re-derivation requires the package bundle's one exact verification lineage"
            )
        if any(value.verifier == actor for value in records):
            raise AuthoringValidationError("originating verifier cannot re-derive its own result")
    elif route.route_id == "audit.argument_assurance":
        records = tuple(
            payloads.get(_entity_key(reference))
            for reference, _entity in by_type["ReDerivationRecord"]
        )
        if any(
            not isinstance(record, a.ReDerivationRecord)
            or _actor_key(actor)
            in {
                _actor_key(record.rederiver),
                _actor_key(record.originating_verifier),
                _actor_key(record.proof_author),
            }
            for record in records
        ):
            raise AuthoringValidationError("assurance auditor is not actor-independent")
        assert isinstance(package, t.ValidatedArgumentPackage)
        verification_bundle = theory_payloads.get(
            _entity_key(package.verification_bundle_ref)
        )
        assert isinstance(verification_bundle, t.VerificationBundle)
        package_obligations = set(verification_bundle.proof_obligation_refs)
        package_verifications = set(verification_bundle.verification_record_refs)
        expected_pairs: set[tuple[EntityVersionRef, EntityVersionRef]] = set()
        for verification_ref in input_refs_by_type.get("VerificationRecord", ()):
            verification = theory_payloads.get(_entity_key(verification_ref))
            if not isinstance(verification, t.VerificationRecord):
                raise AuthoringValidationError(
                    "assurance audit selected an unresolved VerificationRecord"
                )
            expected_pairs.add((verification.obligation_ref, verification_ref))
        actual_pairs = tuple(
            (record.obligation_ref, record.verification_record_ref)
            for record in records
            if isinstance(record, a.ReDerivationRecord)
        )
        if any(
            not isinstance(record, a.ReDerivationRecord)
            or record.package_ref != package_ref
            or record.claim_graph_ref != package.claim_graph_ref
            or record.formal_model_ref != package.formal_model_ref
            or record.assumption_map_ref != package.assumption_map_ref
            or record.obligation_ref not in package_obligations
            or record.verification_record_ref not in package_verifications
            for record in records
        ):
            raise AuthoringValidationError(
                "assurance audit re-derivations belong to another package lineage"
            )
        if set(actual_pairs) != expected_pairs or len(actual_pairs) != len(
            expected_pairs
        ):
            raise AuthoringValidationError(
                "assurance audit requires one exact re-derivation per verification record"
            )
    elif route.route_id == "compose.manuscript_unit":
        if paper is None or actor != paper.canonical_writer:
            raise AuthoringValidationError("only the exact Paper IR canonical writer may compose")
    elif route.route_id == "review.manuscript_unit":
        assignment = payloads.get(_entity_key(by_type["CriticAssignment"][0][0]))
        if (
            not isinstance(assignment, a.CriticAssignment)
            or assignment.role not in {"formal_fidelity", "economic_reader"}
            or actor != assignment.assigned_actor
        ):
            raise AuthoringValidationError("review actor does not match a formal/economic assignment")
    elif route.route_id == "prepare.reader_probe":
        assignment = payloads.get(_entity_key(by_type["CriticAssignment"][0][0]))
        if not isinstance(assignment, a.CriticAssignment) or actor != assignment.probe_designer:
            raise AuthoringValidationError("probe preparation actor is not the assigned designer")
    elif route.route_id == "answer.reader_probe":
        assignment = payloads.get(_entity_key(by_type["CriticAssignment"][0][0]))
        probe = payloads.get(_entity_key(by_type["ReaderProbeSet"][0][0]))
        if (
            not isinstance(assignment, a.CriticAssignment)
            or not isinstance(probe, a.ReaderProbeSet)
            or actor != assignment.assigned_actor
            or actor != probe.respondent
        ):
            raise AuthoringValidationError("reader response actor or probe lineage mismatches")
    elif route.route_id == "adjudicate.reader_probe":
        assignment = payloads.get(_entity_key(by_type["CriticAssignment"][0][0]))
        if not isinstance(assignment, a.CriticAssignment) or actor != assignment.adjudicator:
            raise AuthoringValidationError("reader adjudication actor is not assigned")
    elif route.route_id == "close.manuscript_review":
        if actor.kind != "deterministic_tool":
            raise AuthoringValidationError("review closure requires a deterministic actor")
    elif route.route_id == "record.human_effort":
        if actor.kind != "human":
            raise AuthoringValidationError("human effort may be recorded only by a human")

    if mode in {"working", "submission"}:
        if assurance_ref is None:
            if paper is None or paper.assurance_bundle_ref is None:
                raise AuthoringValidationError("working/submission entry requires exact assurance")
            assurance_ref = paper.assurance_bundle_ref
        validate_assurance_pass(snapshot, assurance_ref)
        if paper is not None:
            entity_index, _, decision_index, all_payloads, all_theory, _ = _validated_indices(snapshot)
            _validate_paper_ir(
                snapshot,
                paper,
                entity_index,
                all_payloads,
                all_theory,
                decision_index,
                require_current=True,
            )
    return AuthoringRouteEntryReport(
        route_id=route.route_id,
        compiler_mode=mode,
        input_entity_refs=references,
        package_ref=package_ref,
        assurance_bundle_ref=assurance_ref,
        canonical_writer=canonical_writer,
    )


def _validate_phase3_route_entry_refs(
    snapshot: Snapshot,
    route_spec: RouteSpecV3,
    input_refs: Iterable[EntityVersionRef],
    *,
    actor: Actor,
    compiler_mode: str | None = None,
) -> AuthoringRouteEntryReport:
    if (
        route_spec.route_id not in _PHASE3_ROUTES
        or route_spec.route_version != 3
        or route_spec.availability != "enabled"
        or route_spec.entry_validator_id
        != (
            "assurance_route_entry.v1"
            if route_spec.route_id in _ASSURANCE_ROUTES
            else "authoring_route_entry.v1"
        )
    ):
        raise AuthoringValidationError("unknown, disabled, or malformed Phase 3 route")
    references = tuple(input_refs)
    if len({_entity_key(item) for item in references}) != len(references):
        raise AuthoringValidationError("route input repeats an exact entity ref")
    entity_index, _, _, payloads, theory_payloads, _ = _validated_indices(snapshot)
    entities: list[EntityVersion] = []
    for reference in references:
        entity = entity_index.get(_entity_key(reference))
        if entity is None:
            raise AuthoringValidationError("route input contains an unresolved entity")
        if entity.entity_type in t.THEORY_PAYLOAD_MODELS:
            if not _typed_reference_closure_is_current_and_fresh(snapshot, reference):
                raise AuthoringValidationError("route theory input is not current and fresh")
        elif entity.entity_type in a.AUTHORING_PAYLOAD_MODELS:
            if not _entity_is_current_and_fresh(snapshot, entity):
                raise AuthoringValidationError("route authoring input is not current and fresh")
        else:
            raise AuthoringValidationError("Phase 3 route input must be a packed typed entity")
        if entity.entity_type not in _PHASE3_ENTRY_TYPES[route_spec.route_id]:
            raise AuthoringValidationError(
                f"{entity.entity_type} is outside the exact {route_spec.route_id} input shape"
            )
        entities.append(entity)
    _require_counts(route_spec, entities, output=False)
    return _input_mode_and_lineage(
        snapshot,
        route_spec,
        references,
        tuple(entities),
        payloads,
        theory_payloads,
        actor=actor,
        compiler_mode=compiler_mode,
    )


def validate_phase3_route_entry(
    snapshot: Snapshot,
    route_spec: RouteSpecV3,
    focus_entity_ids: Iterable[str],
    *,
    actor: Actor,
    compiler_mode: str | None = None,
) -> AuthoringRouteEntryReport:
    """Validate begin-time current focus, role actor, mode, and assurance."""

    focus_ids = tuple(focus_entity_ids)
    if len(set(focus_ids)) != len(focus_ids):
        raise AuthoringValidationError("route focus_entity_ids must not repeat")
    current = {
        entity.entity_id: entity
        for entity in snapshot.entity_versions
        if snapshot.current_entities.get(entity.entity_id) == entity.version
    }
    missing = sorted(set(focus_ids).difference(current))
    if missing:
        raise AuthoringValidationError(
            "route focus contains unknown current entities: " + ", ".join(missing)
        )
    return _validate_phase3_route_entry_refs(
        snapshot,
        route_spec,
        (
            EntityVersionRef(entity_id=entity_id, version=current[entity_id].version)
            for entity_id in focus_ids
        ),
        actor=actor,
        compiler_mode=compiler_mode,
    )


def _edge_matches(
    relation: RelationVersion,
    source: EntityVersionRef,
    target: EntityVersionRef,
    relation_types: frozenset[str],
    *,
    invalidating: bool,
) -> bool:
    return (
        relation.source == source
        and relation.target == target
        and relation.relation_type in relation_types
        and (not invalidating or relation.dependency_mode != "trace_only")
        and (
            not invalidating
            or (
                relation.upstream is not None
                and relation.downstream is not None
                and relation.upstream.entity_id == source.entity_id
                and relation.upstream.version == source.version
                and relation.downstream.entity_id == target.entity_id
                and relation.downstream.version == target.version
            )
        )
    )


def _require_edge(
    relations: Sequence[RelationVersion],
    source: EntityVersionRef,
    target: EntityVersionRef,
    relation_types: Iterable[str],
    label: str,
    *,
    invalidating: bool = True,
) -> None:
    allowed = frozenset(relation_types)
    if not any(
        _edge_matches(
            relation, source, target, allowed, invalidating=invalidating
        )
        for relation in relations
    ):
        raise AuthoringValidationError(
            f"{label} requires exact {'/'.join(sorted(allowed))} relation "
            f"{source.entity_id}@{source.version} -> {target.entity_id}@{target.version}"
        )


def _require_span_relations(
    relations: Sequence[RelationVersion],
    unit_ref: EntityVersionRef,
    unit: a.ManuscriptUnit,
) -> None:
    for index, span in enumerate(unit.spans):
        target_path = f"/payload/spans/{index}"
        for source in span.source_fields:
            matching = [
                relation
                for relation in relations
                if relation.source
                == EntityVersionRef(entity_id=source.entity_id, version=source.version)
                and relation.target == unit_ref
                and relation.dependency_mode != "trace_only"
                and relation.upstream == source
                and relation.downstream is not None
                and relation.downstream.facet == "terminology_presentation"
                and relation.downstream.field_path is not None
                and (
                    relation.downstream.field_path == target_path
                    or relation.downstream.field_path.startswith(target_path + "/")
                )
            ]
            if len(matching) != 1:
                raise AuthoringValidationError(
                    f"span {span.assertion_id} requires exactly one field-level invalidating source relation"
                )


def _as_ref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def _route_output_semantics(
    before: Snapshot,
    after: Snapshot,
    transaction: Transaction,
    route: RouteSpecV3,
    produced_entities: tuple[EntityVersion, ...],
    produced_relations: tuple[RelationVersion, ...],
    produced_artifacts: tuple[ArtifactRegistration, ...],
) -> None:
    entity_index, artifact_index, _, payloads, theory_payloads, theory_report = _validated_indices(after)
    del artifact_index, theory_report
    outputs_by_type: dict[str, list[tuple[EntityVersionRef, a.AuthoringPayload]]] = {}
    for entity in produced_entities:
        payload = payloads.get(_entity_key(entity))
        if not isinstance(payload, a.AuthoringPayload):
            raise AuthoringValidationError("Phase 3 route emitted a non-authoring entity")
        outputs_by_type.setdefault(entity.entity_type, []).append((_as_ref(entity), payload))

    def one(entity_type: str) -> tuple[EntityVersionRef, a.AuthoringPayload]:
        values = outputs_by_type.get(entity_type, ())
        if len(values) != 1:
            raise AuthoringValidationError(
                f"route {route.route_id} requires exactly one {entity_type}"
            )
        return values[0]

    input_refs = tuple(
        reference
        for reference in transaction.evidence_refs
        if isinstance(reference, EntityVersionRef)
    )
    input_entities = {
        reference: next(
            entity for entity in before.entity_versions if _entity_key(entity) == _entity_key(reference)
        )
        for reference in input_refs
    }
    input_by_type: dict[str, list[EntityVersionRef]] = {}
    for reference, entity in input_entities.items():
        input_by_type.setdefault(entity.entity_type, []).append(reference)
    _validate_exact_route_input_lineage(route.route_id, input_by_type, payloads)

    def exact_input(entity_type: str) -> EntityVersionRef:
        values = input_by_type.get(entity_type, ())
        if len(values) != 1:
            raise AuthoringValidationError(
                f"exact input lineage requires one {entity_type} for {route.route_id}"
            )
        return values[0]

    produced_blockers = tuple(
        operation.blocker
        for operation in transaction.operations
        if isinstance(operation, RecordBlockerOp)
    )

    def matching_repair_blockers(affected: set[object]) -> tuple[object, ...]:
        return tuple(
            blocker
            for blocker in produced_blockers
            if blocker.required_route == "repair.dependency"
            and blocker.severity in {"error", "critical"}
            and any(reference in affected for reference in blocker.affected_refs)
        )

    if route.route_id == "verify.independent_rederivation":
        output_ref, output = one("ReDerivationRecord")
        assert isinstance(output, a.ReDerivationRecord)
        package = theory_payloads.get(_entity_key(output.package_ref))
        assert isinstance(package, t.ValidatedArgumentPackage)
        matching_g5 = [
            decision
            for decision in after.decisions
            if _decision_is_current_confirmed_human(
                after, decision, expected_kind="G5_argument_validation"
            )
            and decision.machine_outcome == "approve"
            and decision.subject_ref == package.g5_dossier_ref.entity_id
            and decision.scope_ref == package.question_ref.entity_id
        ]
        if (
            len(matching_g5) != 1
            or DecisionVersionRef(
                decision_id=matching_g5[0].decision_id,
                version=matching_g5[0].version,
            )
            not in transaction.evidence_refs
            or matching_g5[0].decision_id not in transaction.authority_basis
        ):
            raise AuthoringValidationError(
                "re-derivation transaction omits its exact G5 evidence/authority"
            )
        if (
            output.rederiver != transaction.actor
            or output.route_run_id != transaction.route_run_id
            or output.route_run_hash != transaction.route_run_hash
            or output.context_manifest_hash != transaction.context_manifest_hash
            or output.compiled_context_hash != transaction.compiled_context_hash
        ):
            raise AuthoringValidationError("re-derivation actor/run/context does not match transaction")
        exact_inputs = {
            output.package_ref,
            output.claim_graph_ref,
            output.obligation_ref,
            output.formal_model_ref,
            output.assumption_map_ref,
        }
        if exact_inputs != set(input_refs):
            raise AuthoringValidationError(
                "re-derivation output does not equal its exact blind input lineage"
            )
        forbidden_evidence = {
            output.verification_record_ref,
            *output.excluded_proof_artifact_refs,
        }
        if any(reference in transaction.evidence_refs for reference in forbidden_evidence):
            raise AuthoringValidationError("blind re-derivation transaction exposes prohibited proof evidence")
        produced_artifact_refs = {
            ArtifactDependencyRef(
                artifact_id=item.artifact_id,
                version=item.version,
                content_hash=item.content_hash,
            )
            for item in produced_artifacts
        }
        if output.derivation_artifact_ref not in produced_artifact_refs:
            raise AuthoringValidationError("re-derivation artifact was not registered by this run")
        for source in (
            output.package_ref,
            output.claim_graph_ref,
            output.obligation_ref,
            output.formal_model_ref,
            output.assumption_map_ref,
            output.verification_record_ref,
        ):
            _require_edge(
                produced_relations,
                source,
                output_ref,
                {"depends_on"},
                "re-derivation provenance",
            )
        repair_blockers = matching_repair_blockers(
            {output_ref, output.package_ref, output.obligation_ref}
        )
        if output.outcome in {"gap_found", "falsified", "inconclusive"}:
            if not repair_blockers:
                raise AuthoringValidationError(
                    "failed/inconclusive re-derivation requires an exact theory-repair blocker"
                )
        elif repair_blockers:
            raise AuthoringValidationError(
                "agreeing re-derivation cannot carry a contradictory failure blocker"
            )
    elif route.route_id == "audit.argument_assurance":
        output_ref, output = one("AssuranceBundle")
        assert isinstance(output, a.AssuranceBundle)
        if (
            output.g5_decision_ref not in transaction.evidence_refs
            or output.g5_decision_ref.decision_id not in transaction.authority_basis
        ):
            raise AuthoringValidationError(
                "assurance transaction omits its exact G5 evidence/authority"
            )
        if (
            output.assembled_by != transaction.actor
            or output.route_run_id != transaction.route_run_id
            or output.route_run_hash != transaction.route_run_hash
            or output.context_manifest_hash != transaction.context_manifest_hash
            or output.compiled_context_hash != transaction.compiled_context_hash
            or any(audit.auditor != transaction.actor for audit in output.proof_audits)
        ):
            raise AuthoringValidationError("AssuranceBundle actor/run/context/auditor mismatches")
        produced_artifact_refs = {
            ArtifactDependencyRef(
                artifact_id=item.artifact_id,
                version=item.version,
                content_hash=item.content_hash,
            )
            for item in produced_artifacts
        }
        required_run_artifacts = {
            *(audit.audit_report_ref for audit in output.proof_audits),
            *(receipt.output_ref for receipt in output.tool_receipts),
            *(
                receipt.receipt_ref
                for receipt in output.tool_receipts
                if receipt.receipt_ref is not None
            ),
            *(
                receipt.certificate_ref
                for receipt in output.tool_receipts
                if receipt.certificate_ref is not None
            ),
            *(
                receipt.witness_ref
                for receipt in output.tool_receipts
                if receipt.witness_ref is not None
            ),
        }
        if not required_run_artifacts.issubset(produced_artifact_refs):
            raise AuthoringValidationError(
                "proof-audit reports and harness outputs/certificates/witnesses must be registered by this run"
            )
        available_harness_inputs = {
            reference
            for reference in transaction.evidence_refs
            if isinstance(reference, ArtifactDependencyRef)
        }.union(produced_artifact_refs)
        if any(
            receipt.code_ref not in available_harness_inputs
            or receipt.input_ref not in available_harness_inputs
            for receipt in output.tool_receipts
        ):
            raise AuthoringValidationError(
                "harness code/input artifacts must be exact transaction evidence or same-run products"
            )
        verification_bundle = theory_payloads.get(
            _entity_key(output.verification_bundle_ref)
        )
        obligation_inputs = set(input_by_type.get("ProofObligation", ()))
        verification_inputs = set(input_by_type.get("VerificationRecord", ()))
        rederivation_inputs = set(input_by_type.get("ReDerivationRecord", ()))
        audited_obligations = tuple(item.obligation_ref for item in output.proof_audits)
        audited_verifications = tuple(
            item.verification_record_ref for item in output.proof_audits
        )
        audited_rederivations = tuple(
            item.rederivation_ref for item in output.proof_audits
        )
        if (
            output.package_ref != exact_input("ValidatedArgumentPackage")
            or output.claim_graph_ref != exact_input("ClaimGraph")
            or output.formal_model_ref != exact_input("FormalModel")
            or output.assumption_map_ref != exact_input("AssumptionMap")
            or output.verification_bundle_ref != exact_input("VerificationBundle")
            or set(output.rederivation_refs) != rederivation_inputs
            or set(audited_obligations) != obligation_inputs
            or len(audited_obligations) != len(obligation_inputs)
            or set(audited_verifications) != verification_inputs
            or len(audited_verifications) != len(verification_inputs)
            or set(audited_rederivations) != rederivation_inputs
            or len(audited_rederivations) != len(rederivation_inputs)
            or not isinstance(verification_bundle, t.VerificationBundle)
            or set(verification_bundle.proof_obligation_refs) != obligation_inputs
            or set(verification_bundle.verification_record_refs)
            != verification_inputs
        ):
            raise AuthoringValidationError(
                "AssuranceBundle does not equal its exact obligation/verification/re-derivation inputs"
            )
        required_sources = {
            output.package_ref,
            output.claim_graph_ref,
            output.formal_model_ref,
            output.assumption_map_ref,
            output.verification_bundle_ref,
            *output.rederivation_refs,
            *(item.obligation_ref for item in output.proof_audits),
            *(item.verification_record_ref for item in output.proof_audits),
            *(item.rederivation_ref for item in output.proof_audits),
            *(item.obligation_ref for item in output.tool_non_applicability),
            *(
                reference
                for item in output.tool_non_applicability
                for reference in item.evidence_refs
                if isinstance(reference, EntityVersionRef)
            ),
        }
        if not required_sources.issubset(set(input_refs)):
            raise AuthoringValidationError("assurance output is not closed over exact route inputs")
        nonapplicability_evidence = {
            reference
            for item in output.tool_non_applicability
            for reference in item.evidence_refs
        }
        if not nonapplicability_evidence.issubset(
            set(transaction.evidence_refs).union(produced_artifact_refs)
        ):
            raise AuthoringValidationError(
                "typed harness non-applicability omits its exact route evidence"
            )
        for source in required_sources:
            _require_edge(
                produced_relations,
                source,
                output_ref,
                {"depends_on", "supports", "validates"},
                "assurance provenance",
            )
        assurance_failed = not derive_assurance_pass(after, output_ref).passed
        affected = {
            output_ref,
            output.package_ref,
            *(audit.obligation_ref for audit in output.proof_audits),
        }
        repair_blockers = matching_repair_blockers(affected)
        if assurance_failed and not repair_blockers:
            raise AuthoringValidationError(
                "failed assurance requires an exact error/critical repair.dependency blocker"
            )
        if not assurance_failed and repair_blockers:
            raise AuthoringValidationError(
                "non-failing AssuranceBundle cannot carry a contradictory failure blocker"
            )
        # A failing bundle remains valid evidence; only a passing bundle may
        # unlock authoring.  Do not coerce failure into a route rejection.
    elif route.route_id == "design.reader_path":
        paper_ref, paper = one("PaperIR")
        profile_ref, profile = one("ResolvedProfileManifest")
        reader_ref, reader = one("ReaderPath")
        contracts_ref, contracts = one("ResultContractSet")
        assert isinstance(paper, a.PaperIR)
        assert isinstance(profile, a.ResolvedProfileManifest)
        assert isinstance(reader, a.ReaderPath)
        assert isinstance(contracts, a.ResultContractSet)
        if (
            profile.source_state_revision != before.head
            or paper.source_state_revision != before.head
        ):
            raise AuthoringValidationError(
                "design projections must bind the exact entry snapshot revision"
            )
        if (
            paper.resolved_profile_manifest_ref != profile_ref
            or reader.paper_ir_ref != paper_ref
            or contracts.paper_ir_ref != paper_ref
            or contracts.reader_path_ref != reader_ref
            or paper.package_ref != exact_input("ValidatedArgumentPackage")
        ):
            raise AuthoringValidationError("design route emitted more than one topology")
        package = theory_payloads.get(_entity_key(paper.package_ref))
        assurance_inputs = input_by_type.get("AssuranceBundle", ())
        expected_assurance_inputs = (
            () if paper.assurance_bundle_ref is None else (paper.assurance_bundle_ref,)
        )
        if (
            tuple(assurance_inputs) != expected_assurance_inputs
            or not isinstance(package, t.ValidatedArgumentPackage)
            or contracts.claim_graph_ref != package.claim_graph_ref
            or contracts.assumption_map_ref != package.assumption_map_ref
            or contracts.economic_argument_graph_ref
            != package.economic_argument_graph_ref
            or contracts.example_suite_ref != package.example_suite_ref
            or contracts.verification_bundle_ref != package.verification_bundle_ref
        ):
            raise AuthoringValidationError(
                "design output is not closed over the exact package/assurance inputs"
            )
        if paper.assurance_bundle_ref is not None:
            assurance = payloads.get(_entity_key(paper.assurance_bundle_ref))
            if (
                not isinstance(assurance, a.AssuranceBundle)
                or assurance.package_ref != paper.package_ref
            ):
                raise AuthoringValidationError(
                    "design AssuranceBundle belongs to another package"
                )
        required_decision_evidence = {
            profile.theory_mode_decision_ref,
            profile.ambition_decision_ref,
            profile.g4_decision_ref,
            profile.audience_decision_ref,
            *(
                (paper.g5_decision_ref,)
                if paper.g5_decision_ref is not None
                else ()
            ),
            *(
                (paper.manuscript_version_promotion_ref,)
                if paper.manuscript_version_promotion_ref is not None
                else ()
            ),
        }
        if not required_decision_evidence.issubset(set(transaction.evidence_refs)):
            raise AuthoringValidationError(
                "design transaction evidence omits an exact profile/G5/promotion Decision"
            )
        if not {
            reference.decision_id for reference in required_decision_evidence
        }.issubset(set(transaction.authority_basis)):
            raise AuthoringValidationError(
                "design authority_basis omits an exact profile/G5/promotion Decision"
            )
        assignments = outputs_by_type.get("CriticAssignment", ())
        if len(assignments) != 3:
            raise AuthoringValidationError("design requires exactly three CriticAssignments")
        _require_edge(
            produced_relations, paper.package_ref, paper_ref, {"projects"}, "Paper IR projection"
        )
        _require_edge(
            produced_relations, profile_ref, paper_ref, {"governs"}, "profile authority"
        )
        _require_edge(
            produced_relations, paper_ref, reader_ref, {"depends_on", "projects"}, "reader projection"
        )
        _require_edge(
            produced_relations,
            paper_ref,
            contracts_ref,
            {"depends_on", "projects"},
            "result contract projection",
        )
        if paper.assurance_bundle_ref is not None:
            _require_edge(
                produced_relations,
                paper.assurance_bundle_ref,
                paper_ref,
                {"validates"},
                "Paper IR assurance",
            )
        for assignment_ref, assignment in assignments:
            assert isinstance(assignment, a.CriticAssignment)
            if (
                assignment.paper_ir_ref != paper_ref
                or assignment.reader_path_ref != reader_ref
                or assignment.result_contract_set_ref != contracts_ref
            ):
                raise AuthoringValidationError("CriticAssignment belongs to another design")
            _require_edge(
                produced_relations,
                paper_ref,
                assignment_ref,
                {"assigns"},
                "critic assignment",
            )
        if paper.compiler_mode in {"working", "submission"}:
            validate_assurance_pass(after, paper.assurance_bundle_ref)
    elif route.route_id == "compose.manuscript_unit":
        unit_ref, unit = one("ManuscriptUnit")
        assert isinstance(unit, a.ManuscriptUnit)
        paper = payloads[_entity_key(unit.paper_ir_ref)]
        assert isinstance(paper, a.PaperIR)
        profile = payloads[_entity_key(paper.resolved_profile_manifest_ref)]
        assert isinstance(profile, a.ResolvedProfileManifest)
        if (
            unit.paper_ir_ref != exact_input("PaperIR")
            or unit.reader_path_ref != exact_input("ReaderPath")
            or unit.result_contract_set_ref != exact_input("ResultContractSet")
            or paper.resolved_profile_manifest_ref
            != exact_input("ResolvedProfileManifest")
            or paper.package_ref != exact_input("ValidatedArgumentPackage")
        ):
            raise AuthoringValidationError(
                "ManuscriptUnit output does not realize its exact selected design inputs"
            )
        compose_authority = {
            profile.theory_mode_decision_ref,
            profile.ambition_decision_ref,
            profile.g4_decision_ref,
            profile.audience_decision_ref,
            *((paper.g5_decision_ref,) if paper.g5_decision_ref is not None else ()),
            *(
                (paper.manuscript_version_promotion_ref,)
                if paper.manuscript_version_promotion_ref is not None
                else ()
            ),
        }
        if not compose_authority.issubset(set(transaction.evidence_refs)) or not {
            reference.decision_id for reference in compose_authority
        }.issubset(set(transaction.authority_basis)):
            raise AuthoringValidationError(
                "compose transaction omits exact profile/G5/promotion authority"
            )
        if unit.source_state_revision != before.head:
            raise AuthoringValidationError(
                "ManuscriptUnit source_state_revision must equal the compose entry head"
            )
        if transaction.actor != unit.canonical_writer or transaction.actor != paper.canonical_writer:
            raise AuthoringValidationError("compose transaction actor is not the canonical writer")
        forbidden_writer_artifacts: set[ArtifactDependencyRef] = set()
        for value in payloads.values():
            if isinstance(value, a.ReaderProbeSet):
                forbidden_writer_artifacts.update(
                    {value.probe_artifact_ref, value.answer_key_artifact_ref}
                )
            elif isinstance(value, a.ReaderResponse):
                forbidden_writer_artifacts.add(value.response_artifact_ref)
            elif isinstance(value, a.ReDerivationRecord):
                forbidden_writer_artifacts.add(value.derivation_artifact_ref)
                forbidden_writer_artifacts.update(value.excluded_proof_artifact_refs)
            elif isinstance(value, a.AssuranceBundle):
                for audit in value.proof_audits:
                    forbidden_writer_artifacts.update(
                        {audit.proof_artifact_ref, audit.audit_report_ref}
                    )
                for receipt in value.tool_receipts:
                    forbidden_writer_artifacts.update(
                        {receipt.code_ref, receipt.input_ref, receipt.output_ref}
                    )
                    if receipt.receipt_ref is not None:
                        forbidden_writer_artifacts.add(receipt.receipt_ref)
                    if receipt.certificate_ref is not None:
                        forbidden_writer_artifacts.add(receipt.certificate_ref)
                    if receipt.witness_ref is not None:
                        forbidden_writer_artifacts.add(receipt.witness_ref)
        if any(
            isinstance(reference, ArtifactDependencyRef)
            and reference in forbidden_writer_artifacts
            for reference in transaction.evidence_refs
        ):
            raise AuthoringValidationError(
                "canonical writer evidence exposes a hidden probe, response, proof, or raw assurance artifact"
            )
        matching_artifacts = [
            item
            for item in produced_artifacts
            if _artifact_key(item) == _artifact_key(unit.manuscript_artifact_ref)
            and item.content_hash == unit.manuscript_artifact_ref.content_hash
        ]
        if len(matching_artifacts) != 1:
            raise AuthoringValidationError("compose must register its one exact manuscript artifact")
        if unit.integration_generation == 1:
            if not any(
                isinstance(item, CreateEntityOp) and item.entity.entity_id == unit_ref.entity_id
                for item in transaction.operations
            ) or any(isinstance(item, SupersedeEntityOp) for item in transaction.operations):
                raise AuthoringValidationError("initial composition must create, not supersede, a unit")
        else:
            prior_refs = input_by_type.get("ManuscriptUnit", ())
            brief_refs = input_by_type.get("RevisionBrief", ())
            closure_refs = input_by_type.get("ReviewClosure", ())
            if (
                prior_refs != [unit.previous_manuscript_unit_ref]
                or brief_refs != [unit.revision_brief_ref]
                or len(closure_refs) != 1
            ):
                raise AuthoringValidationError("canonical revision lacks one prior unit/brief/closure")
            if not any(
                isinstance(item, SupersedeEntityOp)
                and item.previous == unit.previous_manuscript_unit_ref
                and _as_ref(item.entity) == unit_ref
                for item in transaction.operations
            ):
                raise AuthoringValidationError(
                    "canonical revision must supersede the exact prior ManuscriptUnit"
                )
        for source in (
            unit.paper_ir_ref,
            unit.reader_path_ref,
            unit.result_contract_set_ref,
        ):
            _require_edge(
                produced_relations,
                source,
                unit_ref,
                {"depends_on", "governs", "realizes"},
                "manuscript design dependency",
            )
        _require_span_relations(produced_relations, unit_ref, unit)
        if paper.compiler_mode == "submission":
            closure_refs = input_by_type.get("ReviewClosure", ())
            working_refs = input_by_type.get("ManuscriptUnit", ())
            if len(closure_refs) != 1 or len(working_refs) != 1:
                raise AuthoringValidationError("submission compilation requires exact working unit and closure")
            promoted_closure = payloads[_entity_key(closure_refs[0])]
            assert isinstance(promoted_closure, a.ReviewClosure)
            promotion = after.decisions[
                next(
                    index
                    for index, decision in enumerate(after.decisions)
                    if paper.manuscript_version_promotion_ref is not None
                    and decision.decision_id
                    == paper.manuscript_version_promotion_ref.decision_id
                    and decision.version
                    == paper.manuscript_version_promotion_ref.version
                )
            ]
            if (
                promoted_closure.status != "authoring_ready"
                or promoted_closure.compiler_mode != "working"
                or promoted_closure.manuscript_unit_ref != working_refs[0]
                or promotion.subject_ref != closure_refs[0].entity_id
                or unit.submission_source_unit_ref != working_refs[0]
                or unit.submission_source_artifact_ref
                != payloads[_entity_key(working_refs[0])].manuscript_artifact_ref
            ):
                raise AuthoringValidationError(
                    "submission output is not bound to its approved working closure/unit"
                )
        if paper.compiler_mode in {"working", "submission"}:
            validate_assurance_pass(after, paper.assurance_bundle_ref)
    elif route.route_id == "review.manuscript_unit":
        review_ref, review = one("ReviewRecord")
        assert isinstance(review, a.ReviewRecord)
        input_unit_ref = exact_input("ManuscriptUnit")
        input_unit = payloads.get(_entity_key(input_unit_ref))
        if (
            not isinstance(input_unit, a.ManuscriptUnit)
            or review.assignment_ref != exact_input("CriticAssignment")
            or review.manuscript_unit_ref != input_unit_ref
            or review.reviewed_artifact_ref != input_unit.manuscript_artifact_ref
        ):
            raise AuthoringValidationError(
                "ReviewRecord output is not bound to the exact selected assignment/manuscript"
            )
        if review.role not in {"formal_fidelity", "economic_reader"} or review.reviewer != transaction.actor:
            raise AuthoringValidationError("review route has the wrong role or actor")
        if review.context_hash != transaction.compiled_context_hash:
            raise AuthoringValidationError("review context_hash is not the exact compiled run context")
        if review.reviewed_artifact_ref not in transaction.evidence_refs:
            raise AuthoringValidationError("review transaction omits the exact manuscript artifact")
        for finding_ref, finding in outputs_by_type.get("ReviewFinding", ()):
            assert isinstance(finding, a.ReviewFinding)
            if (
                finding_ref not in review.finding_refs
                or finding.assignment_ref != review.assignment_ref
                or finding.manuscript_unit_ref != review.manuscript_unit_ref
                or finding.reviewed_artifact_ref != review.reviewed_artifact_ref
                or finding.role != review.role
                or finding.critic != review.reviewer
            ):
                raise AuthoringValidationError(
                    "ReviewRecord finding does not share its exact selected review lineage"
                )
            _require_edge(
                produced_relations,
                review.manuscript_unit_ref,
                finding_ref,
                {"reviews", "depends_on"},
                "review finding",
            )
        if set(review.finding_refs) != {
            reference for reference, _ in outputs_by_type.get("ReviewFinding", ())
        }:
            raise AuthoringValidationError("ReviewRecord findings must equal this run's outputs")
        _require_edge(
            produced_relations,
            review.manuscript_unit_ref,
            review_ref,
            {"reviews"},
            "manuscript review",
        )
        _require_edge(
            produced_relations,
            review.assignment_ref,
            review_ref,
            {"depends_on"},
            "review assignment",
        )
    elif route.route_id == "prepare.reader_probe":
        probe_ref, probe = one("ReaderProbeSet")
        assert isinstance(probe, a.ReaderProbeSet)
        if probe.probe_designer != transaction.actor or probe.route_run_id != transaction.route_run_id or probe.context_manifest_hash != transaction.context_manifest_hash:
            raise AuthoringValidationError("ReaderProbeSet actor/run/context mismatches")
        if probe.frozen_manuscript_artifact_ref not in transaction.evidence_refs:
            raise AuthoringValidationError("probe design omits the exact frozen manuscript artifact")
        unit = payloads[_entity_key(probe.manuscript_unit_ref)]
        assignment = payloads[_entity_key(probe.assignment_ref)]
        assert isinstance(unit, a.ManuscriptUnit) and isinstance(
            assignment, a.CriticAssignment
        )
        if (
            probe.assignment_ref != exact_input("CriticAssignment")
            or probe.manuscript_unit_ref != exact_input("ManuscriptUnit")
            or assignment.reader_path_ref != exact_input("ReaderPath")
            or probe.frozen_manuscript_artifact_ref
            != unit.manuscript_artifact_ref
            or probe.canonical_writer != assignment.canonical_writer
            or probe.probe_designer != assignment.probe_designer
            or probe.respondent != assignment.assigned_actor
            or probe.adjudicator != assignment.adjudicator
            or probe.transfer_objective != assignment.transfer_objective
        ):
            raise AuthoringValidationError(
                "ReaderProbeSet output does not equal its selected cold-reader assignment"
            )
        reader = payloads[_entity_key(assignment.reader_path_ref)]
        contracts = payloads[_entity_key(assignment.result_contract_set_ref)]
        assert isinstance(reader, a.ReaderPath) and isinstance(
            contracts, a.ResultContractSet
        )
        _validate_reader_probe_packet_coverage(probe, unit, reader, contracts)
        produced_refs = {
            ArtifactDependencyRef(artifact_id=item.artifact_id, version=item.version, content_hash=item.content_hash): item
            for item in produced_artifacts
        }
        if probe.probe_artifact_ref not in produced_refs or probe.answer_key_artifact_ref not in produced_refs:
            raise AuthoringValidationError("probe route must register exact probe and sealed key artifacts")
        key = produced_refs[probe.answer_key_artifact_ref]
        if key.privacy not in {"restricted", "local_only"} or "cold_reader_evaluation" not in key.access_compartments:
            raise AuthoringValidationError("reader answer key is not sealed in its evaluation compartment")
        _require_edge(
            produced_relations, probe.manuscript_unit_ref, probe_ref, {"tests"}, "reader probes"
        )
        _require_edge(
            produced_relations, probe.assignment_ref, probe_ref, {"depends_on"}, "probe assignment"
        )
    elif route.route_id == "answer.reader_probe":
        response_ref, response = one("ReaderResponse")
        assert isinstance(response, a.ReaderResponse)
        if response.respondent != transaction.actor or response.route_run_id != transaction.route_run_id or response.context_manifest_hash != transaction.context_manifest_hash:
            raise AuthoringValidationError("ReaderResponse actor/run/context mismatches")
        probe = payloads[_entity_key(response.probe_set_ref)]
        assert isinstance(probe, a.ReaderProbeSet)
        assignment = payloads.get(_entity_key(exact_input("CriticAssignment")))
        if (
            not isinstance(assignment, a.CriticAssignment)
            or response.probe_set_ref != exact_input("ReaderProbeSet")
            or response.manuscript_unit_ref != exact_input("ManuscriptUnit")
            or probe.assignment_ref != exact_input("CriticAssignment")
            or response.respondent != assignment.assigned_actor
            or response.respondent != probe.respondent
        ):
            raise AuthoringValidationError(
                "ReaderResponse output does not equal its selected probe/manuscript lineage"
            )
        all_answer_keys = {
            value.answer_key_artifact_ref
            for value in payloads.values()
            if isinstance(value, a.ReaderProbeSet)
        }
        if any(key in transaction.evidence_refs for key in all_answer_keys):
            raise AuthoringValidationError("cold respondent transaction contains the sealed answer key")
        unit = payloads[_entity_key(response.manuscript_unit_ref)]
        assert isinstance(unit, a.ManuscriptUnit)
        if not {probe.probe_artifact_ref, unit.manuscript_artifact_ref}.issubset(
            set(transaction.evidence_refs)
        ):
            raise AuthoringValidationError(
                "cold respondent evidence omits the exact probe or manuscript artifact"
            )
        if not any(
            _artifact_key(item) == _artifact_key(response.response_artifact_ref)
            and item.content_hash == response.response_artifact_ref.content_hash
            for item in produced_artifacts
        ):
            raise AuthoringValidationError("reader response artifact was not registered by this run")
        _require_edge(
            produced_relations, response.probe_set_ref, response_ref, {"tests"}, "reader response"
        )
        _require_edge(
            produced_relations,
            response.manuscript_unit_ref,
            response_ref,
            {"depends_on"},
            "response manuscript",
        )
    elif route.route_id == "adjudicate.reader_probe":
        review_ref, review = one("ReviewRecord")
        assert isinstance(review, a.ReviewRecord)
        if review.role != "cold_reader" or review.reviewer != transaction.actor:
            raise AuthoringValidationError("cold ReviewRecord has the wrong adjudicator")
        if review.context_hash != transaction.compiled_context_hash:
            raise AuthoringValidationError("cold review context_hash is not the adjudication context")
        response = payloads[_entity_key(review.reader_response_ref)]
        assert isinstance(response, a.ReaderResponse)
        probe = payloads[_entity_key(response.probe_set_ref)]
        assert isinstance(probe, a.ReaderProbeSet)
        assignment = payloads.get(_entity_key(exact_input("CriticAssignment")))
        input_unit = payloads.get(_entity_key(exact_input("ManuscriptUnit")))
        if (
            not isinstance(assignment, a.CriticAssignment)
            or not isinstance(input_unit, a.ManuscriptUnit)
            or review.assignment_ref != exact_input("CriticAssignment")
            or review.manuscript_unit_ref != exact_input("ManuscriptUnit")
            or review.reader_response_ref != exact_input("ReaderResponse")
            or response.probe_set_ref != exact_input("ReaderProbeSet")
            or review.reviewed_artifact_ref
            != input_unit.manuscript_artifact_ref
            or review.answer_key_artifact_ref != probe.answer_key_artifact_ref
            or review.reviewer != assignment.adjudicator
        ):
            raise AuthoringValidationError(
                "cold ReviewRecord output does not equal its selected adjudication lineage"
            )
        if not {
            probe.probe_artifact_ref,
            probe.answer_key_artifact_ref,
            response.response_artifact_ref,
            review.reviewed_artifact_ref,
        }.issubset(set(transaction.evidence_refs)):
            raise AuthoringValidationError(
                "cold adjudication omits exact probe/key/response/manuscript artifacts"
            )
        if set(review.finding_refs) != {
            reference for reference, _ in outputs_by_type.get("ReviewFinding", ())
        }:
            raise AuthoringValidationError("cold ReviewRecord findings must equal run outputs")
        for finding_ref, finding in outputs_by_type.get("ReviewFinding", ()):
            assert isinstance(finding, a.ReviewFinding)
            if (
                finding.assignment_ref != review.assignment_ref
                or finding.manuscript_unit_ref != review.manuscript_unit_ref
                or finding.reviewed_artifact_ref != review.reviewed_artifact_ref
                or finding.role != review.role
                or finding.critic != review.reviewer
            ):
                raise AuthoringValidationError(
                    "cold finding does not share the exact adjudication lineage"
                )
            _require_edge(
                produced_relations,
                review.manuscript_unit_ref,
                finding_ref,
                {"reviews", "depends_on"},
                "cold review finding",
            )
        _require_edge(
            produced_relations,
            review.reader_response_ref,
            review_ref,
            {"validates"},
            "reader adjudication",
        )
        _require_edge(
            produced_relations,
            review.manuscript_unit_ref,
            review_ref,
            {"reviews"},
            "cold manuscript review",
        )
    elif route.route_id == "close.manuscript_review":
        closure_ref, closure = one("ReviewClosure")
        assert isinstance(closure, a.ReviewClosure)
        if closure.closure_actor != transaction.actor:
            raise AuthoringValidationError("closure payload actor differs from transaction actor")
        input_unit_ref = exact_input("ManuscriptUnit")
        input_unit = payloads.get(_entity_key(input_unit_ref))
        if (
            not isinstance(input_unit, a.ManuscriptUnit)
            or closure.manuscript_unit_ref != input_unit_ref
            or closure.assurance_bundle_ref != exact_input("AssuranceBundle")
            or closure.paper_ir_ref != input_unit.paper_ir_ref
            or closure.reader_path_ref != input_unit.reader_path_ref
            or closure.result_contract_set_ref
            != input_unit.result_contract_set_ref
        ):
            raise AuthoringValidationError(
                "ReviewClosure output does not equal its selected manuscript/design/assurance lineage"
            )
        exact_review_inputs = set(input_by_type.get("ReviewRecord", ()))
        closure_reviews = {
            closure.formal_fidelity_review_ref,
            closure.economic_reader_review_ref,
            closure.cold_reader_review_ref,
        }
        if exact_review_inputs != closure_reviews:
            raise AuthoringValidationError("closure must consume exactly its three ReviewRecords")
        review_payloads = [payloads[_entity_key(reference)] for reference in closure_reviews]
        exact_finding_inputs = set(input_by_type.get("ReviewFinding", ()))
        review_findings = {
            reference
            for review in review_payloads
            if isinstance(review, a.ReviewRecord)
            for reference in review.finding_refs
        }
        if exact_finding_inputs != review_findings:
            raise AuthoringValidationError("closure must consume every and only review finding")
        briefs = outputs_by_type.get("RevisionBrief", ())
        if closure.status == "authoring_ready" and briefs:
            raise AuthoringValidationError("authoring-ready closure cannot emit a RevisionBrief")
        if closure.status == "blocked":
            if len(briefs) != 1 or closure.revision_brief_ref != briefs[0][0]:
                raise AuthoringValidationError("blocked closure requires its one exact RevisionBrief")
        for review_ref in (
            closure.formal_fidelity_review_ref,
            closure.economic_reader_review_ref,
            closure.cold_reader_review_ref,
        ):
            _require_edge(
                produced_relations,
                review_ref,
                closure_ref,
                {"validates"},
                "review closure",
            )
        _require_edge(
            produced_relations,
            closure.assurance_bundle_ref,
            closure_ref,
            {"depends_on"},
            "closure assurance",
        )
        for brief_ref, _ in briefs:
            _require_edge(
                produced_relations,
                closure_ref,
                brief_ref,
                {"depends_on"},
                "closure revision brief",
            )
        # Recompute against the post-transaction state.  This catches favorable
        # but false check labels while still allowing old closures to stale.
        if closure.status == "authoring_ready":
            validate_authoring_ready(after, closure_ref)
        else:
            (
                post_entities,
                _,
                post_decisions,
                post_payloads,
                post_theory,
                post_theory_report,
            ) = _validated_indices(after)
            _validate_review_closure(
                after,
                closure_ref,
                closure,
                post_entities,
                post_payloads,
                post_theory,
                post_decisions,
                post_theory_report,
            )
    elif route.route_id == "record.human_effort":
        record_ref, record = one("HumanEffortRecord")
        assert isinstance(record, a.HumanEffortRecord)
        if record.human != transaction.actor:
            raise AuthoringValidationError("effort record reporter differs from transaction actor")
        if record.manuscript_unit_ref != exact_input("ManuscriptUnit"):
            raise AuthoringValidationError(
                "HumanEffortRecord output belongs to another ManuscriptUnit"
            )
        prior = input_by_type.get("HumanEffortRecord", ())
        if prior:
            if len(prior) != 1:
                raise AuthoringValidationError("effort append accepts at most one prior record")
            old = payloads[_entity_key(prior[0])]
            assert isinstance(old, a.HumanEffortRecord)
            try:
                a.validate_human_effort_update(old, record)
            except ValueError as exc:
                raise AuthoringValidationError(str(exc)) from exc
            if not any(
                isinstance(item, SupersedeEntityOp)
                and item.previous == prior[0]
                and _as_ref(item.entity) == record_ref
                for item in transaction.operations
            ):
                raise AuthoringValidationError(
                    "human effort append must supersede its exact current record"
                )
        elif not any(
            isinstance(item, CreateEntityOp) and _as_ref(item.entity) == record_ref
            for item in transaction.operations
        ):
            raise AuthoringValidationError("initial HumanEffortRecord must be created")
        _require_edge(
            produced_relations,
            record.manuscript_unit_ref,
            record_ref,
            {"reports_effort"},
            "human effort report",
        )


def validate_phase3_route_transaction(
    snapshot: Snapshot, transaction: Transaction, route_spec: RouteSpecV3
) -> AuthoringProjectionReport:
    """Validate one of the ten Phase 3 transaction shapes and its exact topology."""

    if (
        transaction.origin != "route_run"
        or transaction.route_id != route_spec.route_id
        or route_spec.route_id not in _PHASE3_ROUTES
        or route_spec.route_version != 3
        or route_spec.availability != "enabled"
        or route_spec.exit_validator_id
        != (
            "assurance_route_exit.v1"
            if route_spec.route_id in _ASSURANCE_ROUTES
            else "authoring_route_exit.v1"
        )
    ):
        raise AuthoringValidationError("transaction is not bound to an enabled Phase 3 route")
    if transaction.project_id != snapshot.project_id:
        raise AuthoringValidationError("Phase 3 transaction belongs to another project")
    if len({_ref_key(reference) for reference in transaction.evidence_refs}) != len(
        transaction.evidence_refs
    ):
        raise AuthoringValidationError("Phase 3 transaction repeats exact evidence")

    compiler_mode: str | None = None
    if route_spec.route_id == "design.reader_path":
        paper_ops = [
            operation
            for operation in transaction.operations
            if isinstance(operation, (CreateEntityOp, SupersedeEntityOp))
            and operation.entity.entity_type == "PaperIR"
        ]
        if len(paper_ops) == 1:
            paper_op = paper_ops[0]
            previous = (
                next(
                    (
                        item
                        for item in snapshot.entity_versions
                        if _entity_key(item) == _entity_key(paper_op.previous)
                    ),
                    None,
                )
                if isinstance(paper_op, SupersedeEntityOp)
                else None
            )
            parsed = validate_authoring_entity(
                paper_op.entity,
                previous,
            )
            assert isinstance(parsed, a.PaperIR)
            compiler_mode = parsed.compiler_mode
    entry_report = _validate_phase3_route_entry_refs(
        snapshot,
        route_spec,
        (
            reference
            for reference in transaction.evidence_refs
            if isinstance(reference, EntityVersionRef)
        ),
        actor=transaction.actor,
        compiler_mode=compiler_mode,
    )
    del entry_report

    prior_entities = {_entity_key(item): item for item in snapshot.entity_versions}
    prior_relations = {_relation_key(item): item for item in snapshot.relation_versions}
    produced_entities: list[EntityVersion] = []
    produced_relations: list[RelationVersion] = []
    produced_artifacts: list[ArtifactRegistration] = []
    outcomes: list[RecordRouteOutcomeOp] = []
    blockers = list(snapshot.blockers)
    for operation in transaction.operations:
        if operation.op not in route_spec.allowed_operations:
            raise AuthoringValidationError(
                f"operation {operation.op} is outside the Phase 3 route allowlist"
            )
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            entity = operation.entity
            if entity.entity_type not in route_spec.allowed_entity_types:
                raise AuthoringValidationError("route emitted a disallowed entity type")
            previous = None
            if isinstance(operation, SupersedeEntityOp):
                previous = prior_entities.get(_entity_key(operation.previous))
                if (
                    previous is None
                    or snapshot.current_entities.get(previous.entity_id) != previous.version
                ):
                    raise AuthoringValidationError("route supersedes a non-current authoring entity")
            validate_authoring_entity(entity, previous)
            produced_entities.append(entity)
        elif isinstance(operation, (CreateRelationOp, SupersedeRelationOp)):
            relation = operation.relation
            if relation.relation_type not in route_spec.allowed_relation_types:
                raise AuthoringValidationError("route emitted a disallowed relation type")
            if isinstance(operation, SupersedeRelationOp):
                previous = prior_relations.get(_relation_key(operation.previous))
                if previous is None or snapshot.current_relations.get(previous.relation_id) != previous.version:
                    raise AuthoringValidationError("route supersedes a non-current relation")
            produced_relations.append(relation)
        elif isinstance(operation, RegisterArtifactOp):
            produced_artifacts.append(operation.artifact)
        elif isinstance(operation, RecordBlockerOp):
            blockers.append(operation.blocker)
        elif isinstance(operation, RecordRouteOutcomeOp):
            outcomes.append(operation)
        else:
            raise AuthoringValidationError("Phase 3 route contains an unsupported operation shape")

    _require_counts(route_spec, produced_entities, output=True)
    relation_counts: dict[str, int] = {}
    for relation in produced_relations:
        relation_counts[relation.relation_type] = relation_counts.get(relation.relation_type, 0) + 1
    for requirement in route_spec.required_output_relations:
        count = relation_counts.get(requirement.relation_type, 0)
        if count < requirement.min_count or (
            requirement.max_count is not None and count > requirement.max_count
        ):
            raise AuthoringValidationError("route relation output cardinality is invalid")
    if len(outcomes) != 1:
        raise AuthoringValidationError("Phase 3 transaction requires exactly one RouteOutcome")
    outcome = outcomes[0].outcome
    if outcome.route_id != route_spec.route_id or outcome.route_run_id != transaction.route_run_id:
        raise AuthoringValidationError("RouteOutcome is not bound to this exact run")
    produced_object_keys = {
        *(_ref_key(_as_ref(item)) for item in produced_entities),
        *(
            _ref_key(RelationVersionRef(relation_id=item.relation_id, version=item.version))
            for item in produced_relations
        ),
        *(
            _ref_key(
                ArtifactDependencyRef(
                    artifact_id=item.artifact_id,
                    version=item.version,
                    content_hash=item.content_hash,
                )
            )
            for item in produced_artifacts
        ),
        *(
            _ref_key(BlockerRef(blocker_id=item.blocker.blocker_id))
            for item in transaction.operations
            if isinstance(item, RecordBlockerOp)
        ),
    }
    candidate_keys = {_ref_key(reference) for reference in outcome.candidate_refs}
    if len(candidate_keys) != len(outcome.candidate_refs):
        raise AuthoringValidationError("RouteOutcome repeats an exact candidate ref")
    if candidate_keys != produced_object_keys:
        raise AuthoringValidationError(
            "RouteOutcome candidate_refs must equal every produced entity, relation, artifact, and blocker"
        )
    if outcome.outcome in {"failed", "interrupted", "rejected"} and (
        produced_entities or produced_relations
    ):
        raise AuthoringValidationError("failed/rejected Phase 3 route cannot commit authoring outputs")
    produced_artifact_dependencies = {
        ArtifactDependencyRef(
            artifact_id=item.artifact_id,
            version=item.version,
            content_hash=item.content_hash,
        )
        for item in produced_artifacts
    }
    if not set(outcome.validator_report_refs).issubset(produced_artifact_dependencies):
        raise AuthoringValidationError(
            "RouteOutcome validator reports must be exact artifacts from this transaction"
        )

    all_entities = (*snapshot.entity_versions, *produced_entities)
    all_relations = (*snapshot.relation_versions, *produced_relations)
    all_artifacts = (*snapshot.artifacts, *produced_artifacts)
    current_entities = dict(snapshot.current_entities)
    current_relations = dict(snapshot.current_relations)
    current_artifacts = dict(snapshot.current_artifacts)
    for entity in produced_entities:
        current_entities[entity.entity_id] = entity.version
    for relation in produced_relations:
        current_relations[relation.relation_id] = relation.version
    for artifact in produced_artifacts:
        current_artifacts[artifact.artifact_id] = artifact.version
    complete_entity_index = {_entity_key(item): item for item in all_entities}
    for relation in produced_relations:
        if (
            _entity_key(relation.source) not in complete_entity_index
            or _entity_key(relation.target) not in complete_entity_index
            or relation.project_id != snapshot.project_id
        ):
            raise AuthoringValidationError("route relation endpoint is unresolved or foreign")
        source_entity = complete_entity_index[_entity_key(relation.source)]
        target_entity = complete_entity_index[_entity_key(relation.target)]
        source_owner = a.AUTHORING_PAYLOAD_OWNER_FACETS.get(
            source_entity.entity_type
        ) or t.THEORY_PAYLOAD_OWNER_FACETS.get(source_entity.entity_type)
        target_owner = a.AUTHORING_PAYLOAD_OWNER_FACETS.get(
            target_entity.entity_type
        ) or t.THEORY_PAYLOAD_OWNER_FACETS.get(target_entity.entity_type)
        if relation.dependency_mode != "trace_only" and (
            relation.upstream is None
            or relation.downstream is None
            or (source_owner is not None and relation.upstream.facet != source_owner)
            or (target_owner is not None and relation.downstream.facet != target_owner)
        ):
            raise AuthoringValidationError(
                "invalidating Phase 3 relation uses the wrong semantic owner facet"
            )
        if relation.source not in {_as_ref(item) for item in produced_entities} and relation.target not in {
            _as_ref(item) for item in produced_entities
        }:
            raise AuthoringValidationError("route relation is disconnected from every route output")
    after = snapshot.model_copy(
        update={
            "entity_versions": all_entities,
            "relation_versions": all_relations,
            "artifacts": all_artifacts,
            "route_outcomes": (*snapshot.route_outcomes, outcome),
            "blockers": tuple(blockers),
            "provenance_hashes": tuple(
                dict.fromkeys(
                    (
                        *snapshot.provenance_hashes,
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
            "current_entities": current_entities,
            "current_relations": current_relations,
            "current_artifacts": current_artifacts,
        }
    )
    projection = validate_authoring_projection(after)
    _route_output_semantics(
        snapshot,
        after,
        transaction,
        route_spec,
        tuple(produced_entities),
        tuple(produced_relations),
        tuple(produced_artifacts),
    )
    return projection


__all__ = [
    "ASSURANCE_PREDICATE_VERSION",
    "AUTHORING_LEAKAGE_LINT_VERSION",
    "AssurancePassReport",
    "AuthoringProjectionReport",
    "AuthoringRouteEntryReport",
    "AuthoringValidationError",
    "GovernanceLeak",
    "derive_assurance_pass",
    "harness_protocol_code_bytes",
    "harness_protocol_code_hash",
    "lint_authoring_governance_leakage",
    "paper_ir_upstream_projection_hash",
    "resolved_profile_projection_hash",
    "reproducible_harness_artifact_bytes",
    "validate_assurance_pass",
    "validate_authoring_entity",
    "validate_authoring_projection",
    "validate_authoring_ready",
    "validate_authoring_update",
    "validate_manuscript_spans_and_text",
    "validate_manuscript_text",
    "validate_phase3_route_entry",
    "validate_phase3_route_transaction",
    "validate_reproducible_tool_receipt",
]
