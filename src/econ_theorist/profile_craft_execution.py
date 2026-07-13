"""Deterministic execution protocols for Phase 4 predicate and craft evidence.

The functions in this module are deliberately narrower than a general code
runner.  Phase 4 reuses the canonical finite polynomial-relation input already
sealed by Phase 3, creates a fixed set of semantic downgrade mutants, and
replays them with exact arithmetic.  No result boolean supplied by an agent is
accepted as evidence.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from fractions import Fraction
import json
import re
import unicodedata
from typing import Annotated, Literal, TypeAlias

from pydantic import Field, model_validator

from . import profile_craft as pc
from .assurance import (
    AssuranceHarnessError,
    ExactAssignment,
    ExactPolynomial,
    ExactPolynomialRelation,
    PolynomialRelationScanInput,
    run_exact_polynomial_relation_scan,
    verify_exact_polynomial_relation_scan,
)
from .codec import canonical_json_bytes, object_digest, sha256_digest
from .models import (
    ArtifactDependencyRef,
    Digest,
    EntityVersionRef,
    StableId,
    StrictModel,
)


class ProfileCraftExecutionError(ValueError):
    """Phase 4 executable evidence is noncanonical or does not reproduce."""


MANDATORY_MUTATION_KINDS: tuple[str, ...] = (
    "empty_domain",
    "constant_true",
    "conclusion_flip",
    "domain_narrowing",
    "omitted_assumption",
)
SUPPORTED_MUTATION_KINDS = frozenset(MANDATORY_MUTATION_KINDS)
MUTATION_EXECUTOR_VERSION = "predicate.mutation.exact_polynomial.v1"
PHRASE_DETECTOR_VERSION = "phrase.audit.internal_derived_ngram.v1"
PHRASE_AUDIT_LIMITATIONS = (
    "This deterministic scan compares only copyright-safe derived fields in the "
    "pinned internal craft corpus. It does not inspect external source prose and "
    "cannot establish authorship, legal originality, or absence of copying outside "
    "that registered comparison set."
)


MutationKind: TypeAlias = Literal[
    "empty_domain",
    "constant_true",
    "conclusion_flip",
    "domain_narrowing",
    "omitted_assumption",
]


class PredicateWitnessArtifact(StrictModel):
    protocol: Literal["obligation_predicate_witness.v3"] = (
        "obligation_predicate_witness.v3"
    )
    contract_id: StableId
    witness_id: StableId
    witness_kind: Literal[
        "domain_member", "predicate_falsifying", "boundary"
    ]
    case_id: StableId
    assignment_ref: ArtifactDependencyRef
    assignment_hash: Digest
    base_input_hash: Digest
    predicate_result: bool
    domain_membership_verified: Literal[True] = True
    antecedent_satisfiability_verified: Literal[False] = False
    verified: Literal[True] = True
    limitations: str


class PredicateMutationResultArtifact(StrictModel):
    protocol: Literal["obligation_predicate_mutation_result.v2"] = (
        "obligation_predicate_mutation_result.v2"
    )
    executor_version: Literal[
        "predicate.mutation.exact_polynomial.v1"
    ] = MUTATION_EXECUTOR_VERSION
    contract_id: StableId
    mutation_id: StableId
    mutation_kind: MutationKind
    base_input_hash: Digest
    mutated_predicate_hash: Digest
    output_hash: Digest | None
    receipt_hash: Digest | None
    execution_outcome: Literal[
        "falsified",
        "no_counterexample_found",
        "invalid_empty_domain_rejected",
        "unencoded_assumption_not_executable",
    ]
    changed_clause_ids: tuple[StableId, ...]
    locator_comparison_hash: Digest
    expected_to_fail: Literal[True] = True
    detected: bool
    limitations: str

    @model_validator(mode="after")
    def _execution_fields_are_coherent(self) -> "PredicateMutationResultArtifact":
        executed = self.execution_outcome in {
            "falsified",
            "no_counterexample_found",
        }
        if executed != (self.output_hash is not None and self.receipt_hash is not None):
            raise ValueError("executed mutants require exact output and receipt hashes")
        if self.execution_outcome == "invalid_empty_domain_rejected" and (
            self.mutation_kind != "empty_domain"
        ):
            raise ValueError("only the empty-domain mutant may be protocol-rejected")
        if self.execution_outcome == "unencoded_assumption_not_executable" and (
            self.mutation_kind != "omitted_assumption"
        ):
            raise ValueError("only omitted-assumption may be unencoded")
        if self.execution_outcome == "unencoded_assumption_not_executable":
            if self.mutated_predicate_hash != self.base_input_hash:
                raise ValueError("an unencoded control must preserve the exact input bytes")
            if self.detected:
                raise ValueError("an unexecutable control cannot be marked detected")
            if self.changed_clause_ids:
                raise ValueError("an unencoded control cannot claim changed predicate clauses")
        return self


class MutationReplayEntry(StrictModel):
    mutation_id: StableId
    mutation_kind: MutationKind
    mutated_predicate_hash: Digest
    result_artifact_hash: Digest
    execution_outcome: Literal[
        "falsified",
        "no_counterexample_found",
        "invalid_empty_domain_rejected",
        "unencoded_assumption_not_executable",
    ]
    detected: bool

    @model_validator(mode="after")
    def _unexecutable_is_not_a_killed_mutant(self) -> "MutationReplayEntry":
        if (
            self.execution_outcome == "unencoded_assumption_not_executable"
            and self.detected
        ):
            raise ValueError("an unexecutable control cannot be counted as detected")
        return self


class PredicateMutationReplayArtifact(StrictModel):
    protocol: Literal["obligation_predicate_mutation_replay.v2"] = (
        "obligation_predicate_mutation_replay.v2"
    )
    executor_version: Literal[
        "predicate.mutation.exact_polynomial.v1"
    ] = MUTATION_EXECUTOR_VERSION
    audit_id: StableId
    contract_ref: EntityVersionRef
    contract_hash: Digest
    contract_id: StableId
    base_input_hash: Digest
    entries: Annotated[tuple[MutationReplayEntry, ...], Field(min_length=1)]
    killed_mutation_ids: tuple[StableId, ...]
    surviving_mutation_ids: tuple[StableId, ...]
    unexecutable_mutation_ids: tuple[StableId, ...]
    executable_controls_passed: bool
    unexecutable_controls_accounted: bool
    all_detected: bool
    outcome: Literal["pass", "pass_with_limitations", "fail"]
    limitations: str

    @model_validator(mode="after")
    def _summary_is_coherent(self) -> "PredicateMutationReplayArtifact":
        mutation_ids = tuple(item.mutation_id for item in self.entries)
        if len(mutation_ids) != len(set(mutation_ids)):
            raise ValueError("mutation replay entries must be unique")
        unexecutable = tuple(
            item.mutation_id
            for item in self.entries
            if item.execution_outcome == "unencoded_assumption_not_executable"
        )
        killed = tuple(
            item.mutation_id
            for item in self.entries
            if item.execution_outcome != "unencoded_assumption_not_executable"
            and item.detected
        )
        surviving = tuple(
            item.mutation_id
            for item in self.entries
            if item.execution_outcome != "unencoded_assumption_not_executable"
            and not item.detected
        )
        if self.killed_mutation_ids != killed:
            raise ValueError("mutation replay killed-control IDs are inconsistent")
        if self.surviving_mutation_ids != surviving:
            raise ValueError("mutation replay surviving-control IDs are inconsistent")
        if self.unexecutable_mutation_ids != unexecutable:
            raise ValueError("mutation replay unexecutable-control IDs are inconsistent")
        executable_passed = not surviving
        if self.executable_controls_passed != executable_passed:
            raise ValueError("mutation replay executable-control status is inconsistent")
        accounted = all(
            not item.detected
            for item in self.entries
            if item.execution_outcome == "unencoded_assumption_not_executable"
        )
        if self.unexecutable_controls_accounted != accounted:
            raise ValueError("mutation replay unexecutable-control status is inconsistent")
        all_detected = all(item.detected for item in self.entries)
        if self.all_detected != all_detected:
            raise ValueError("mutation replay all_detected is inconsistent")
        expected_outcome = (
            "fail"
            if not executable_passed or not accounted
            else "pass_with_limitations"
            if unexecutable
            else "pass"
        )
        if self.outcome != expected_outcome:
            raise ValueError("mutation replay outcome is inconsistent")
        return self


class PhraseLeakAuditArtifact(StrictModel):
    protocol: Literal["profile_craft_phrase_audit.v2"] = (
        "profile_craft_phrase_audit.v2"
    )
    detector_version: Literal[
        "phrase.audit.internal_derived_ngram.v1"
    ] = PHRASE_DETECTOR_VERSION
    assessment_id: StableId
    manuscript_artifact_ref: ArtifactDependencyRef
    selected_move_refs: Annotated[
        tuple[pc.StaticResourceRef, ...], Field(min_length=1)
    ]
    normalized_ngram_size: Annotated[int, Field(ge=8)]
    compared_source_card_refs: Annotated[
        tuple[pc.StaticResourceRef, ...], Field(min_length=1)
    ]
    protected_material_projection_hash: Digest
    protected_ngram_set_hash: Digest
    manuscript_ngram_set_hash: Digest
    suspicious_match_hashes: tuple[Digest, ...] = ()
    outcome: Literal["pass", "fail"]
    limitations: Literal[
        "This deterministic scan compares only copyright-safe derived fields in the pinned internal craft corpus. It does not inspect external source prose and cannot establish authorship, legal originality, or absence of copying outside that registered comparison set."
    ] = PHRASE_AUDIT_LIMITATIONS

    @model_validator(mode="after")
    def _outcome_matches_matches(self) -> "PhraseLeakAuditArtifact":
        if tuple(sorted(set(self.suspicious_match_hashes))) != self.suspicious_match_hashes:
            raise ValueError("suspicious phrase hashes must be unique and sorted")
        if self.outcome != ("fail" if self.suspicious_match_hashes else "pass"):
            raise ValueError("phrase audit outcome must follow the exact intersection")
        return self


def _canonical_json_tree(data: bytes, *, label: str) -> object:
    if not isinstance(data, bytes):
        raise TypeError(f"{label} must be bytes")

    def pairs_hook(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ProfileCraftExecutionError(
                    f"{label} contains duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    def reject_float(_: str) -> object:
        raise ProfileCraftExecutionError(f"{label} contains a forbidden float")

    def reject_constant(token: str) -> object:
        raise ProfileCraftExecutionError(
            f"{label} contains a forbidden JSON constant {token}"
        )

    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=pairs_hook,
            parse_float=reject_float,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProfileCraftExecutionError(f"{label} is not strict UTF-8 JSON") from exc
    if canonical_json_bytes(value) != data:
        raise ProfileCraftExecutionError(f"{label} is not canonical JSON")
    return value


_ARRAY_INDEX = re.compile(r"0|[1-9][0-9]*")


def _pointer_token(token: str) -> str:
    decoded: list[str] = []
    index = 0
    while index < len(token):
        character = token[index]
        if character != "~":
            decoded.append(character)
            index += 1
            continue
        if index + 1 >= len(token) or token[index + 1] not in {"0", "1"}:
            raise ProfileCraftExecutionError("JSON Pointer contains an invalid escape")
        decoded.append("~" if token[index + 1] == "0" else "/")
        index += 2
    result = "".join(decoded)
    canonical = result.replace("~", "~0").replace("/", "~1")
    if canonical != token:
        raise ProfileCraftExecutionError("JSON Pointer is not canonically escaped")
    return result


def canonical_json_pointer_get(document: object, pointer: str) -> object:
    """Resolve one RFC 6901 pointer with canonical array and escape syntax."""

    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise ProfileCraftExecutionError("predicate locator must start with '/'")
    current = document
    for raw_token in pointer[1:].split("/"):
        token = _pointer_token(raw_token)
        if isinstance(current, Mapping):
            if token not in current:
                raise ProfileCraftExecutionError(
                    f"predicate locator does not exist: {pointer}"
                )
            current = current[token]
        elif isinstance(current, Sequence) and not isinstance(
            current, (str, bytes, bytearray)
        ):
            if _ARRAY_INDEX.fullmatch(token) is None:
                raise ProfileCraftExecutionError(
                    f"predicate array locator is noncanonical: {pointer}"
                )
            position = int(token)
            if position >= len(current):
                raise ProfileCraftExecutionError(
                    f"predicate locator does not exist: {pointer}"
                )
            current = current[position]
        else:
            raise ProfileCraftExecutionError(
                f"predicate locator descends through a scalar: {pointer}"
            )
    return current


def predicate_fragment_projection(
    predicate_bytes: bytes,
    *,
    obligation_clause_id: str,
    relation: str,
    pointers: tuple[str, ...],
) -> dict[str, object]:
    """Build the exact fragment projection sealed by one clause mapping."""

    document = _canonical_json_tree(predicate_bytes, label="predicate input")
    if relation == "omitted":
        if pointers:
            raise ProfileCraftExecutionError("omitted mappings cannot have locators")
        fragments: tuple[dict[str, object], ...] = ()
    else:
        if not pointers:
            raise ProfileCraftExecutionError("mapped clauses require locators")
        fragments = tuple(
            {"pointer": pointer, "value": canonical_json_pointer_get(document, pointer)}
            for pointer in pointers
        )
    return {
        "protocol": "predicate_clause_fragment.v1",
        "base_predicate_hash": sha256_digest(predicate_bytes),
        "obligation_clause_id": obligation_clause_id,
        "relation": relation,
        "omitted": relation == "omitted",
        "fragments": fragments,
    }


def predicate_fragment_hash(
    predicate_bytes: bytes,
    *,
    obligation_clause_id: str,
    relation: str,
    pointers: tuple[str, ...],
) -> str:
    """Hash a canonical clause projection, including deterministic omission."""

    return object_digest(
        predicate_fragment_projection(
            predicate_bytes,
            obligation_clause_id=obligation_clause_id,
            relation=relation,
            pointers=pointers,
        )
    )


def witness_assignment_bytes(predicate_bytes: bytes, case_id: str) -> bytes:
    """Return the exact assignment bytes for a case in a sealed scan input."""

    try:
        scan_input = PolynomialRelationScanInput.from_canonical_bytes(predicate_bytes)
    except AssuranceHarnessError as exc:
        raise ProfileCraftExecutionError("predicate input is not a relation scan") from exc
    matches = tuple(case for case in scan_input.domain if case.case_id == case_id)
    if len(matches) != 1:
        raise ProfileCraftExecutionError("witness case is not unique in the scan input")
    return matches[0].canonical_bytes()


def build_predicate_witness_artifact(
    *,
    contract_id: str,
    witness_id: str,
    witness_kind: Literal[
        "domain_member",
        "antecedent_satisfying",
        "predicate_falsifying",
        "boundary",
    ],
    case_id: str,
    assignment_ref: ArtifactDependencyRef,
    assignment_bytes: bytes,
    predicate_bytes: bytes,
    limitations: str,
) -> PredicateWitnessArtifact:
    """Verify domain membership and record the full relation's observed value.

    A bare relation scan has no independently executable antecedent component.
    Consequently, a true relation value is never accepted as proof that the
    antecedent is satisfiable.  A future antecedent protocol must encode and
    execute that claim separately.
    """

    try:
        scan_input = PolynomialRelationScanInput.from_canonical_bytes(predicate_bytes)
        assignment = ExactAssignment.from_canonical_bytes(assignment_bytes)
    except AssuranceHarnessError as exc:
        raise ProfileCraftExecutionError("witness input is not canonical exact data") from exc
    if assignment_ref.content_hash != sha256_digest(assignment_bytes):
        raise ProfileCraftExecutionError("witness assignment ref does not bind its bytes")
    if assignment.case_id != case_id:
        raise ProfileCraftExecutionError("witness case_id disagrees with assignment bytes")
    matching = tuple(case for case in scan_input.domain if case.case_id == case_id)
    if len(matching) != 1 or matching[0] != assignment:
        raise ProfileCraftExecutionError("witness assignment is outside the sealed domain")
    result = scan_input.relation.evaluate(assignment.as_mapping())
    if witness_kind == "antecedent_satisfying":
        raise ProfileCraftExecutionError(
            "bare relation scan cannot verify antecedent satisfiability"
        )
    if witness_kind == "predicate_falsifying" and result:
        raise ProfileCraftExecutionError("predicate-falsifying witness must evaluate false")
    return PredicateWitnessArtifact(
        contract_id=contract_id,
        witness_id=witness_id,
        witness_kind=witness_kind,  # type: ignore[arg-type]
        case_id=case_id,
        assignment_ref=assignment_ref,
        assignment_hash=sha256_digest(assignment_bytes),
        base_input_hash=sha256_digest(predicate_bytes),
        predicate_result=result,
        limitations=limitations,
    )


def _tautology_relation(scan_input: PolynomialRelationScanInput) -> ExactPolynomialRelation:
    polynomial = ExactPolynomial.normalized(
        (Fraction(1), {variable: 1}) for variable in scan_input.relation.variables
    )
    return ExactPolynomialRelation(left=polynomial, operator="eq", right=polynomial)


def _flipped_relation(scan_input: PolynomialRelationScanInput) -> ExactPolynomialRelation:
    flipped = {
        "eq": "lt",
        "le": "gt",
        "lt": "ge",
        "ge": "lt",
        "gt": "le",
    }[scan_input.relation.operator]
    return ExactPolynomialRelation(
        left=scan_input.relation.left,
        operator=flipped,  # type: ignore[arg-type]
        right=scan_input.relation.right,
    )


def build_mutated_predicate_bytes(
    predicate_bytes: bytes, mutation_kind: str
) -> bytes:
    """Create the only accepted canonical mutant for one mandatory attack."""

    if mutation_kind not in SUPPORTED_MUTATION_KINDS:
        raise ProfileCraftExecutionError(
            f"unsupported predicate mutation protocol: {mutation_kind}"
        )
    try:
        base = PolynomialRelationScanInput.from_canonical_bytes(predicate_bytes)
    except AssuranceHarnessError as exc:
        raise ProfileCraftExecutionError("base predicate is not a relation scan") from exc
    if mutation_kind == "empty_domain":
        data = base.canonical_data()
        data["domain"] = {"cases": ()}
        return canonical_json_bytes(data)
    if mutation_kind == "constant_true":
        relation = _tautology_relation(base)
        return PolynomialRelationScanInput(
            relation=relation, domain=base.domain, code_hash=base.code_hash
        ).canonical_bytes()
    if mutation_kind == "conclusion_flip":
        relation = _flipped_relation(base)
        return PolynomialRelationScanInput(
            relation=relation, domain=base.domain, code_hash=base.code_hash
        ).canonical_bytes()
    if mutation_kind == "domain_narrowing":
        if len(base.domain) < 2:
            raise ProfileCraftExecutionError(
                "domain-narrowing attack requires at least two sealed cases"
            )
        return PolynomialRelationScanInput(
            relation=base.relation,
            domain=base.domain[:-1],
            code_hash=base.code_hash,
        ).canonical_bytes()
    # The scan input has no assumption component.  Preserving the bytes is the
    # deterministic evidence that this semantic mutation cannot be expressed.
    return predicate_bytes


def _pointer_value_or_missing(document: object, pointer: str) -> dict[str, object]:
    try:
        return {"present": True, "value": canonical_json_pointer_get(document, pointer)}
    except ProfileCraftExecutionError:
        return {"present": False, "value": None}


def _mapping_comparison(
    predicate_bytes: bytes,
    mutant_bytes: bytes,
    mappings: tuple[pc.PredicateClauseMapping, ...],
) -> tuple[tuple[str, ...], str]:
    base_document = _canonical_json_tree(predicate_bytes, label="base predicate")
    mutant_document = _canonical_json_tree(mutant_bytes, label="mutated predicate")
    comparisons: list[dict[str, object]] = []
    changed: list[str] = []
    for mapping in mappings:
        pointer_rows = tuple(
            {
                "pointer": pointer,
                "base": _pointer_value_or_missing(base_document, pointer),
                "mutant": _pointer_value_or_missing(mutant_document, pointer),
            }
            for pointer in mapping.predicate_json_pointers
        )
        is_changed = any(row["base"] != row["mutant"] for row in pointer_rows)
        if is_changed:
            changed.append(mapping.obligation_clause_id)
        comparisons.append(
            {
                "obligation_clause_id": mapping.obligation_clause_id,
                "clause_kind": mapping.clause_kind,
                "relation": mapping.relation,
                "pointers": pointer_rows,
                "changed": is_changed,
            }
        )
    projection = {
        "protocol": "predicate_locator_comparison.v1",
        "base_input_hash": sha256_digest(predicate_bytes),
        "mutated_input_hash": sha256_digest(mutant_bytes),
        "comparisons": tuple(comparisons),
    }
    return tuple(changed), object_digest(projection)


def _mutation_detected(
    mutation_kind: str,
    mappings: tuple[pc.PredicateClauseMapping, ...],
    changed_clause_ids: tuple[str, ...],
) -> bool:
    by_id = {item.obligation_clause_id: item for item in mappings}
    changed_kinds = {by_id[item].clause_kind for item in changed_clause_ids}
    if mutation_kind in {"empty_domain", "domain_narrowing"}:
        return "domain" in changed_kinds
    if mutation_kind in {"constant_true", "conclusion_flip"}:
        return "conclusion" in changed_kinds
    # The current finite relation input has no executable assumption component.
    # Merely recording that an assumption is omitted accounts for the gap; it
    # does not kill the omitted-assumption control.
    return False


def build_predicate_mutation_result(
    *,
    contract_id: str,
    mutation_id: str,
    mutation_kind: str,
    predicate_bytes: bytes,
    mappings: tuple[pc.PredicateClauseMapping, ...],
    mutated_predicate_ref: ArtifactDependencyRef,
    mutated_predicate_bytes: bytes,
    limitations: str,
) -> PredicateMutationResultArtifact:
    """Execute and summarize one fixed downgrade mutant with exact arithmetic."""

    expected_mutant = build_mutated_predicate_bytes(predicate_bytes, mutation_kind)
    if mutated_predicate_bytes != expected_mutant:
        raise ProfileCraftExecutionError("mutated predicate is not the fixed protocol mutant")
    if mutated_predicate_ref.content_hash != sha256_digest(mutated_predicate_bytes):
        raise ProfileCraftExecutionError("mutated predicate ref does not bind exact bytes")
    changed, comparison_hash = _mapping_comparison(
        predicate_bytes, mutated_predicate_bytes, mappings
    )
    output_hash: str | None = None
    receipt_hash: str | None = None
    if mutation_kind == "empty_domain":
        try:
            PolynomialRelationScanInput.from_canonical_bytes(mutated_predicate_bytes)
        except AssuranceHarnessError:
            execution_outcome = "invalid_empty_domain_rejected"
        else:  # pragma: no cover - a regression in the Phase 3 protocol
            raise ProfileCraftExecutionError("empty-domain mutant was not rejected")
    elif mutation_kind == "omitted_assumption":
        execution_outcome = "unencoded_assumption_not_executable"
    else:
        try:
            mutant = PolynomialRelationScanInput.from_canonical_bytes(
                mutated_predicate_bytes
            )
            run = run_exact_polynomial_relation_scan(
                mutant.relation, mutant.domain, code_hash=mutant.code_hash
            )
            verify_exact_polynomial_relation_scan(
                run, expected_code_hash=mutant.code_hash
            )
        except AssuranceHarnessError as exc:
            raise ProfileCraftExecutionError("mutated predicate did not execute") from exc
        output_hash = run.output.output_hash
        receipt_hash = run.receipt.receipt_hash
        execution_outcome = run.output.outcome
    detected = (
        False
        if execution_outcome == "unencoded_assumption_not_executable"
        else _mutation_detected(mutation_kind, mappings, changed)
    )
    return PredicateMutationResultArtifact(
        contract_id=contract_id,
        mutation_id=mutation_id,
        mutation_kind=mutation_kind,  # type: ignore[arg-type]
        base_input_hash=sha256_digest(predicate_bytes),
        mutated_predicate_hash=sha256_digest(mutated_predicate_bytes),
        output_hash=output_hash,
        receipt_hash=receipt_hash,
        execution_outcome=execution_outcome,  # type: ignore[arg-type]
        changed_clause_ids=changed,
        locator_comparison_hash=comparison_hash,
        detected=detected,
        limitations=limitations,
    )


ArtifactReader: TypeAlias = Callable[[ArtifactDependencyRef], bytes]


def replay_contract_mutations(
    contract: pc.ObligationPredicateContract,
    *,
    predicate_bytes: bytes,
    read_artifact: ArtifactReader,
) -> tuple[MutationReplayEntry, ...]:
    """Independently rerun every registered mutant and compare result bytes."""

    entries: list[MutationReplayEntry] = []
    for mutation in contract.mutation_tests:
        mutated_bytes = read_artifact(mutation.mutated_predicate_ref)
        result_bytes = read_artifact(mutation.result_ref)
        try:
            actual = PredicateMutationResultArtifact.model_validate_json(
                result_bytes, strict=True
            )
        except ValueError as exc:
            raise ProfileCraftExecutionError("mutation result is not typed JSON") from exc
        if canonical_json_bytes(actual) != result_bytes:
            raise ProfileCraftExecutionError("mutation result is not canonical JSON")
        expected = build_predicate_mutation_result(
            contract_id=contract.contract_id,
            mutation_id=mutation.mutation_id,
            mutation_kind=mutation.mutation_kind,
            predicate_bytes=predicate_bytes,
            mappings=contract.clause_mappings,
            mutated_predicate_ref=mutation.mutated_predicate_ref,
            mutated_predicate_bytes=mutated_bytes,
            limitations=actual.limitations,
        )
        if actual != expected:
            raise ProfileCraftExecutionError(
                f"mutation result does not reproduce: {mutation.mutation_id}"
            )
        if mutation.detected != expected.detected:
            raise ProfileCraftExecutionError(
                f"mutation descriptor self-report is false: {mutation.mutation_id}"
            )
        entries.append(
            MutationReplayEntry(
                mutation_id=mutation.mutation_id,
                mutation_kind=mutation.mutation_kind,  # type: ignore[arg-type]
                mutated_predicate_hash=mutation.mutated_predicate_ref.content_hash,
                result_artifact_hash=sha256_digest(result_bytes),
                execution_outcome=expected.execution_outcome,
                detected=expected.detected,
            )
        )
    return tuple(entries)


def build_mutation_replay_artifact(
    *,
    audit_id: str,
    contract_ref: EntityVersionRef,
    contract_hash: str,
    contract: pc.ObligationPredicateContract,
    predicate_bytes: bytes,
    read_artifact: ArtifactReader,
    limitations: str,
) -> PredicateMutationReplayArtifact:
    entries = replay_contract_mutations(
        contract, predicate_bytes=predicate_bytes, read_artifact=read_artifact
    )
    unexecutable = tuple(
        item.mutation_id
        for item in entries
        if item.execution_outcome == "unencoded_assumption_not_executable"
    )
    killed = tuple(
        item.mutation_id
        for item in entries
        if item.execution_outcome != "unencoded_assumption_not_executable"
        and item.detected
    )
    surviving = tuple(
        item.mutation_id
        for item in entries
        if item.execution_outcome != "unencoded_assumption_not_executable"
        and not item.detected
    )
    executable_controls_passed = not surviving
    unexecutable_controls_accounted = all(
        not item.detected
        for item in entries
        if item.execution_outcome == "unencoded_assumption_not_executable"
    )
    all_detected = all(item.detected for item in entries)
    outcome = (
        "fail"
        if not executable_controls_passed or not unexecutable_controls_accounted
        else "pass_with_limitations"
        if unexecutable
        else "pass"
    )
    return PredicateMutationReplayArtifact(
        audit_id=audit_id,
        contract_ref=contract_ref,
        contract_hash=contract_hash,
        contract_id=contract.contract_id,
        base_input_hash=sha256_digest(predicate_bytes),
        entries=entries,
        killed_mutation_ids=killed,
        surviving_mutation_ids=surviving,
        unexecutable_mutation_ids=unexecutable,
        executable_controls_passed=executable_controls_passed,
        unexecutable_controls_accounted=unexecutable_controls_accounted,
        all_detected=all_detected,
        outcome=outcome,
        limitations=limitations,
    )


def _deduplicate_refs(
    references: Sequence[pc.StaticResourceRef],
) -> tuple[pc.StaticResourceRef, ...]:
    result: list[pc.StaticResourceRef] = []
    seen: set[tuple[str, int, str]] = set()
    for reference in references:
        key = (reference.resource_id, reference.version, reference.content_hash)
        if key not in seen:
            seen.add(key)
            result.append(reference)
    return tuple(result)


def selected_source_cards(
    selected_move_refs: tuple[pc.StaticResourceRef, ...],
    *,
    corpus: pc.CraftCorpusRelease | None = None,
) -> tuple[pc.CraftSourceCard, ...]:
    """Resolve selected moves and their exact admitted cards from the pinned corpus."""

    if corpus is None:
        from .profile_craft_policy import load_craft_corpus

        corpus = load_craft_corpus()
    move_by_ref = {pc.static_resource_ref(item): item for item in corpus.moves}
    source_by_ref = {pc.static_resource_ref(item): item for item in corpus.source_cards}
    moves: list[pc.CraftMove] = []
    for reference in selected_move_refs:
        move = move_by_ref.get(reference)
        if move is None:
            raise ProfileCraftExecutionError("selected move is absent from pinned corpus")
        moves.append(move)
    source_refs = _deduplicate_refs(
        tuple(
            reference
            for move in moves
            for reference in (*move.matched_anchor_refs, *move.contrast_refs)
        )
    )
    cards: list[pc.CraftSourceCard] = []
    for reference in source_refs:
        card = source_by_ref.get(reference)
        if card is None:
            raise ProfileCraftExecutionError("selected source card is absent from core corpus")
        cards.append(card)
    return tuple(cards)


def protected_material_projection(
    cards: tuple[pc.CraftSourceCard, ...],
) -> tuple[dict[str, object], ...]:
    """Project only internally authored, copyright-safe derived card fields."""

    return tuple(
        {
            "source_ref": pc.static_resource_ref(card),
            "functional_summary": card.functional_summary,
            "transferable_content": card.transferable_content,
            "paper_specific_nontransferable": card.paper_specific_nontransferable,
            "non_applicability": card.non_applicability,
        }
        for card in cards
    )


_TOKEN = re.compile(r"[^\W_]+", flags=re.UNICODE)


def normalized_token_ngrams(text: str, size: int) -> tuple[str, ...]:
    if isinstance(size, bool) or not isinstance(size, int) or size < 8:
        raise ProfileCraftExecutionError("phrase audit ngram size must be at least eight")
    normalized = unicodedata.normalize("NFKC", text).casefold()
    tokens = tuple(_TOKEN.findall(normalized))
    if len(tokens) < size:
        return ()
    return tuple(" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1))


def _ngram_hashes(texts: Sequence[str], size: int) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                sha256_digest(ngram.encode("utf-8"))
                for text in texts
                for ngram in normalized_token_ngrams(text, size)
            }
        )
    )


def build_phrase_leak_audit(
    *,
    assessment_id: str,
    manuscript_artifact_ref: ArtifactDependencyRef,
    manuscript_bytes: bytes,
    selected_move_refs: tuple[pc.StaticResourceRef, ...],
    normalized_ngram_size: int = 8,
    corpus: pc.CraftCorpusRelease | None = None,
) -> PhraseLeakAuditArtifact:
    """Scan a manuscript against derived internal material, never source originals."""

    if manuscript_artifact_ref.content_hash != sha256_digest(manuscript_bytes):
        raise ProfileCraftExecutionError("manuscript ref does not bind exact bytes")
    try:
        manuscript = manuscript_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProfileCraftExecutionError("phrase audit manuscript is not UTF-8") from exc
    cards = selected_source_cards(selected_move_refs, corpus=corpus)
    projection = protected_material_projection(cards)
    protected_texts = tuple(
        text
        for row in projection
        for text in (
            row["functional_summary"],
            row["transferable_content"],
            row["paper_specific_nontransferable"],
            *row["non_applicability"],
        )
        if isinstance(text, str)
    )
    protected_hashes = _ngram_hashes(protected_texts, normalized_ngram_size)
    manuscript_hashes = _ngram_hashes((manuscript,), normalized_ngram_size)
    suspicious = tuple(sorted(set(protected_hashes).intersection(manuscript_hashes)))
    return PhraseLeakAuditArtifact(
        assessment_id=assessment_id,
        manuscript_artifact_ref=manuscript_artifact_ref,
        selected_move_refs=selected_move_refs,
        normalized_ngram_size=normalized_ngram_size,
        compared_source_card_refs=tuple(pc.static_resource_ref(card) for card in cards),
        protected_material_projection_hash=object_digest(projection),
        protected_ngram_set_hash=object_digest(
            {"ngram_size": normalized_ngram_size, "hashes": protected_hashes}
        ),
        manuscript_ngram_set_hash=object_digest(
            {"ngram_size": normalized_ngram_size, "hashes": manuscript_hashes}
        ),
        suspicious_match_hashes=suspicious,
        outcome="fail" if suspicious else "pass",
    )


__all__ = [
    "MANDATORY_MUTATION_KINDS",
    "MUTATION_EXECUTOR_VERSION",
    "PHRASE_AUDIT_LIMITATIONS",
    "PHRASE_DETECTOR_VERSION",
    "MutationReplayEntry",
    "PhraseLeakAuditArtifact",
    "PredicateMutationReplayArtifact",
    "PredicateMutationResultArtifact",
    "PredicateWitnessArtifact",
    "ProfileCraftExecutionError",
    "build_mutated_predicate_bytes",
    "build_mutation_replay_artifact",
    "build_phrase_leak_audit",
    "build_predicate_mutation_result",
    "build_predicate_witness_artifact",
    "canonical_json_pointer_get",
    "normalized_token_ngrams",
    "predicate_fragment_hash",
    "predicate_fragment_projection",
    "protected_material_projection",
    "replay_contract_mutations",
    "selected_source_cards",
    "witness_assignment_bytes",
]
