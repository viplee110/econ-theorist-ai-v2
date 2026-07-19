"""Run one noncanonical arm of the V8 framing-authoring shadow pair.

The harness deliberately accepts a frozen Snapshot and candidate authoring
contract rather than a project root.  It therefore cannot stage, commit, or
confirm a human gate.  Every authoring surface ends at the same unchanged V8
``validate_candidate`` call.
"""

from __future__ import annotations

import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sys
from time import perf_counter
from typing import Any, Literal

from pydantic import ValidationError

from econ_theorist.candidate_contract import CandidateAuthoringContractV1
from econ_theorist.candidate_draft import (
    CandidateDraftMaterializationError,
    materialize_runtime_facet_hashes,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.framing_quality import (
    FramingQualityBundle,
    parse_framing_quality_payload,
)
from econ_theorist.framing_quality_authoring import (
    FramingAuditCompilationError,
    FramingAuditSemanticDraftV1,
    FramingAuditSemanticDraftV2,
    compile_framing_audit_semantic_draft,
    compile_framing_audit_semantic_draft_v2,
    preflight_framing_audit_semantic_draft,
    preflight_framing_audit_semantic_draft_v2,
)
from econ_theorist.framing_quality_validation import (
    FramingQualityEntityPreflightReportV1,
    diagnose_framing_quality_entity,
)
from econ_theorist.models import CreateEntityOp, Snapshot, Transaction
from econ_theorist.policy import ROUTE_REGISTRY_V8_HASH
from econ_theorist.runtime.replay import (
    CandidateValidationError,
    ChainIntegrityError,
    validate_candidate,
)


_UTF8_BOM = b"\xef\xbb\xbf"
_CASE_SCHEMA = "econ-theorist/framing-authoring-shadow-case/v1"
_RECEIPT_SCHEMA = "econ-theorist/framing-authoring-shadow-receipt/v1"
_SURFACES = ("transaction", "semantic", "semantic_v2")
_TAXONOMY_BUCKETS = (
    "json_or_schema",
    "wrapper_or_binding",
    "relation_or_hash",
    "path_or_semantic_ledger",
    "scientific_validator",
    "setup",
)


class SetupError(ValueError):
    """The frozen experiment boundary is incomplete or inconsistent."""


def _read_bytes(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as exc:
        raise SetupError(f"cannot read required file: {path}") from exc


def _load_case(path: Path) -> tuple[dict[str, Any], Snapshot, CandidateAuthoringContractV1]:
    data = _read_bytes(path)
    try:
        raw = json.loads(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise SetupError("frozen harness case is not valid UTF-8 JSON") from exc
    if not isinstance(raw, dict) or raw.get("case_schema") != _CASE_SCHEMA:
        raise SetupError("unknown frozen harness case schema")
    if canonical_json_bytes(raw) != data:
        raise SetupError("frozen harness case is not canonical JSON")
    requirements = raw.get("runtime_requirements")
    if not isinstance(requirements, dict):
        raise SetupError("frozen harness case omits runtime requirements")
    dependencies = requirements.get("dependencies")
    try:
        dependency_mismatch = not isinstance(dependencies, dict) or any(
            importlib.metadata.version(str(name)) != version
            for name, version in (
                dependencies.items() if isinstance(dependencies, dict) else ()
            )
        )
    except importlib.metadata.PackageNotFoundError as exc:
        raise SetupError("a frozen runtime dependency is unavailable") from exc
    if requirements.get("python") != platform.python_version() or dependency_mismatch:
        raise SetupError("active Python or dependency versions differ from the frozen runtime")
    try:
        snapshot_raw = raw["snapshot"]
        contract_raw = raw["authoring_contract"]
        expected_snapshot_hash = raw["snapshot_sha256"]
        expected_contract_hash = raw["authoring_contract_sha256"]
        route_registry_hash = raw["route_registry_hash"]
    except KeyError as exc:
        raise SetupError(f"frozen harness case omits {exc.args[0]}") from exc
    snapshot_bytes = canonical_json_bytes(snapshot_raw)
    contract_bytes = canonical_json_bytes(contract_raw)
    if sha256_digest(snapshot_bytes) != expected_snapshot_hash:
        raise SetupError("snapshot digest differs from the frozen harness binding")
    if sha256_digest(contract_bytes) != expected_contract_hash:
        raise SetupError("authoring contract digest differs from the frozen harness binding")
    try:
        snapshot = Snapshot.model_validate_json(snapshot_bytes, strict=True)
        contract = CandidateAuthoringContractV1.model_validate_json(
            contract_bytes, strict=True
        )
    except ValidationError as exc:
        raise SetupError("frozen snapshot or authoring contract is invalid") from exc
    if (
        snapshot.head != raw.get("base_head")
        or contract.transaction_bindings.base_revision != snapshot.head
        or contract.transaction_bindings.project_id != snapshot.project_id
        or contract.output_contract.route_id != "audit.framing_economics"
        or contract.output_contract.route_version != 8
        or route_registry_hash != ROUTE_REGISTRY_V8_HASH
        or contract.work_packet_hash != raw.get("work_packet_sha256")
    ):
        raise SetupError("frozen snapshot, route, and contract bindings disagree")
    return raw, snapshot, contract


def _pydantic_issues(exc: ValidationError, *, layer: str) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for error in exc.errors(
        include_url=False,
        include_context=False,
        include_input=False,
    )[:50]:
        output.append(
            {
                "layer": layer,
                "type": str(error["type"]),
                "location": [
                    item if isinstance(item, int) else str(item)
                    for item in error["loc"]
                ],
                "message": str(error["msg"])[:1000],
                "options": [],
                "rule_id": None,
                "json_pointer": None,
                "expected": None,
                "observed": None,
            }
        )
    return output


def _single_issue(
    *, layer: str, issue_type: str, message: str, location: tuple[str | int, ...] = ()
) -> dict[str, Any]:
    return {
        "layer": layer,
        "type": issue_type,
        "location": list(location),
        "message": message[:1000],
        "options": [],
        "rule_id": issue_type,
        "json_pointer": None,
        "expected": None,
        "observed": None,
    }


def _compiler_issues(exc: FramingAuditCompilationError) -> list[dict[str, Any]]:
    return [
        {
            "layer": "preflight",
            "type": issue.rule_id,
            "location": list(issue.location),
            "message": issue.message,
            "options": list(issue.options),
            "rule_id": issue.rule_id,
            "json_pointer": issue.json_pointer,
            "expected": issue.expected,
            "observed": issue.observed,
        }
        for issue in exc.issues
    ]


def _framing_entity_preflight_issues(
    report: FramingQualityEntityPreflightReportV1,
) -> list[dict[str, Any]]:
    return [
        {
            "layer": "framing_payload_preflight",
            "type": issue.rule_id,
            "location": list(issue.location),
            "message": issue.message,
            "options": [],
            "rule_id": issue.rule_id,
            "json_pointer": issue.json_pointer,
            "expected": issue.expected,
            "observed": issue.observed,
            "diagnostic_category": issue.category,
        }
        for issue in report.issues
    ]


def _preflight_transaction_framing_payloads(
    transaction: Transaction,
) -> tuple[list[dict[str, Any]], bool]:
    """Collect all payload diagnostics; block V8 only on structural failures."""

    issues: list[dict[str, Any]] = []
    blocks_canonical_validation = False
    for operation_index, operation in enumerate(transaction.operations):
        if not (
            isinstance(operation, CreateEntityOp)
            and operation.entity.entity_type == "FramingQualityBundle"
        ):
            continue
        report = diagnose_framing_quality_entity(
            operation.entity,
            location_prefix=("operations", operation_index, "entity"),
        )
        if report.issues:
            issues.extend(_framing_entity_preflight_issues(report))
        if any(
            issue.category in {"envelope", "payload_schema", "wrapper_binding"}
            for issue in report.issues
        ):
            blocks_canonical_validation = True
    return issues, blocks_canonical_validation


def _issue_bucket(issue: dict[str, Any]) -> str:
    """Classify diagnostics without changing either authoring surface or V8.

    The ordering is deliberately conservative and frozen in this harness.  A
    known mechanical rule wins over the broad validator layer; an unknown V8
    rejection remains scientific rather than being optimistically counted as
    structural tax.
    """

    layer = str(issue.get("layer", "")).lower()
    issue_type = str(issue.get("type", "")).lower()
    rule_id = str(issue.get("rule_id") or "").lower()
    message = str(issue.get("message", "")).lower()
    location = tuple(str(item).lower() for item in issue.get("location", ()))
    combined = " ".join((rule_id, issue_type, message))
    diagnostic_category = str(issue.get("diagnostic_category") or "").lower()

    if layer == "setup":
        return "setup"
    if diagnostic_category == "scientific_validator":
        return "scientific_validator"
    if diagnostic_category == "semantic_ledger":
        return "path_or_semantic_ledger"
    if layer in {"json", "semantic_schema"}:
        return "json_or_schema"
    if rule_id == "compiler.payload.schema":
        return "json_or_schema"
    if rule_id == "framing.payload.schema":
        return "json_or_schema"
    if rule_id.startswith("framing.envelope.") or rule_id in {
        "framing.entity_type",
        "framing.entity_version",
        "framing.entity_supersession",
    }:
        return "wrapper_or_binding"
    if any(
        marker in combined
        for marker in (
            "duplicate_json_key",
            "candidate_draft_source_entity_invalid",
            "json_invalid",
            "invalid json",
            "invalid framingqualitybundle",
            "framing-quality payload has the wrong model",
            "framing-quality payload is not canonical",
        )
    ):
        return "json_or_schema"

    if rule_id.startswith("compiler.contract.") or rule_id.startswith(
        "compiler.generated_id."
    ):
        return "setup"

    if rule_id.startswith("compiler.channel_") or rule_id.startswith(
        "compiler.channel_path."
    ) or rule_id.startswith("compiler.semantic_ledger."):
        return "path_or_semantic_ledger"
    if rule_id in {
        "framing.primitive_paths",
        "framing.benchmark_fixed_endogenous",
        "framing.benchmark_channel_endpoints",
    }:
        return "path_or_semantic_ledger"
    if any(
        marker in combined
        for marker in (
            "channel_path",
            "channel path",
            "channel endpoints",
            "semantic ledger",
            "primitive-path",
            "primitivegraph path",
            "placebo_control",
            "fixed_endogenous_conflict",
        )
    ):
        return "path_or_semantic_ledger"

    if rule_id == "compiler.contract.relation_templates" or any(
        marker in combined
        for marker in (
            "candidate_draft_template_",
            "candidate_draft_hash_",
            "candidate_draft_endpoint_",
            "candidate_draft_source_not_candidate_output",
            "relationversion",
            "dependencycycleerror",
            "semantic_hash",
            "semantic hash",
            "framing relation",
            "framing dependencies",
            "audits dependency",
            "audits edges",
            "governs dependency",
        )
    ) or (
        layer == "transaction_schema"
        and bool({"relation", "upstream", "downstream", "semantic_hash"}.intersection(location))
    ):
        return "relation_or_hash"

    if layer == "transaction_schema":
        return "wrapper_or_binding"
    if rule_id.startswith("compiler.payload.exact_input_"):
        return "wrapper_or_binding"
    if any(
        marker in combined
        for marker in (
            "transaction is not bound",
            "transaction crosses",
            "transaction repeats",
            "transaction evidence",
            "transaction origin",
            "route allowlist",
            "disallowed entity",
            "disallowed relation",
            "unsupported operation",
            "must create exactly",
            "version 1",
            "version-1",
            "exact entities bound",
            "exact route inputs",
            "replacement g1 dossier",
            "replacement dossier",
            "routeoutcome",
            "route outcome",
            "candidate_refs",
            "candidate refs",
            "privacyflowerror",
            "unsupportedoperationerror",
            "project_id",
            "base_revision",
            "evidence_refs",
            "route_run_id",
            "candidate base",
            "snapshot head",
            "referentialintegrityerror",
            "changedfaceterror",
        )
    ):
        return "wrapper_or_binding"
    if layer == "validator":
        return "scientific_validator"
    return "wrapper_or_binding"


def _taxonomy(issues: list[dict[str, Any]]) -> dict[str, int]:
    counts = {bucket: 0 for bucket in _TAXONOMY_BUCKETS}
    for issue in issues:
        counts[_issue_bucket(issue)] += 1
    return counts


def _assert_preflight_setup_valid(issues: list[Any]) -> None:
    setup_rules = sorted(
        {
            str(issue.rule_id)
            for issue in issues
            if str(issue.rule_id).startswith("compiler.contract.")
            or str(issue.rule_id).startswith("compiler.generated_id.")
        }
    )
    if setup_rules:
        raise SetupError(
            "frozen compiler boundary failed its own preflight: "
            + ", ".join(setup_rules)
        )


def _normalize_source(data: bytes) -> bytes:
    return data[len(_UTF8_BOM) :] if data.startswith(_UTF8_BOM) else data


def _canonical_source_bytes(data: bytes) -> int | None:
    try:
        value = json.loads(data)
        return len(canonical_json_bytes(value))
    except (TypeError, UnicodeDecodeError, ValueError):
        return None


def _parse_transaction(
    data: bytes,
    contract: CandidateAuthoringContractV1,
) -> Transaction:
    try:
        return Transaction.model_validate_json(data, strict=True)
    except ValidationError as initial_error:
        materialized = materialize_runtime_facet_hashes(data, contract)
        if materialized is None:
            raise initial_error
        return Transaction.model_validate_json(materialized, strict=True)


def _semantic_surface_handlers(surface: str) -> tuple[Any, Any, Any]:
    """Select one additive semantic surface without changing the V1 path."""

    if surface == "semantic":
        return (
            FramingAuditSemanticDraftV1,
            preflight_framing_audit_semantic_draft,
            compile_framing_audit_semantic_draft,
        )
    if surface == "semantic_v2":
        return (
            FramingAuditSemanticDraftV2,
            preflight_framing_audit_semantic_draft_v2,
            compile_framing_audit_semantic_draft_v2,
        )
    raise SetupError(f"unknown semantic authoring surface: {surface}")


def _scientific_projection(transaction: Transaction) -> dict[str, Any] | None:
    bundles = [
        operation.entity
        for operation in transaction.operations
        if isinstance(operation, CreateEntityOp)
        and operation.entity.entity_type == "FramingQualityBundle"
    ]
    if len(bundles) != 1:
        return None
    payload = parse_framing_quality_payload(
        "FramingQualityBundle", bundles[0].facets
    )
    if not isinstance(payload, FramingQualityBundle):
        return None
    raw = payload.model_dump(mode="json", exclude_none=False)
    for field_name in (
        "research_question_ref",
        "benchmark_set_ref",
        "primitive_graph_ref",
        "source_g1_dossier_ref",
    ):
        raw.pop(field_name, None)
    for row in raw.get("benchmark_assessments", []):
        if isinstance(row, dict):
            row.pop("channel_path", None)
    return raw


def _write_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise SetupError(f"refusing to overwrite immutable output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def _prior_hash(
    path: Path | None,
    attempt: int,
    *,
    pair_id: str,
    arm_id: str,
    surface: str,
) -> str | None:
    if attempt == 1:
        if path is not None:
            raise SetupError("attempt 1 cannot name a prior receipt")
        return None
    if path is None:
        raise SetupError("revision attempts require the exact prior receipt")
    data = _read_bytes(path)
    try:
        receipt = json.loads(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise SetupError("prior receipt is not valid UTF-8 JSON") from exc
    if (
        canonical_json_bytes(receipt) != data
        or receipt.get("receipt_schema") != _RECEIPT_SCHEMA
        or receipt.get("pair_id") != pair_id
        or receipt.get("arm_id") != arm_id
        or receipt.get("surface") != surface
        or receipt.get("attempt") != attempt - 1
        or receipt.get("validator_pass") is not False
    ):
        raise SetupError("prior receipt does not bind the previous failed arm attempt")
    return sha256_digest(data)


def _run(args: argparse.Namespace) -> tuple[int, dict[str, Any], dict[str, Any] | None]:
    started = perf_counter()
    raw_case, snapshot, contract = _load_case(args.case)
    expected_arm = raw_case.get("arm_ids", {}).get(args.surface)
    if expected_arm != args.arm_id:
        raise SetupError("surface and arm ID differ from the frozen assignment")
    prior_receipt_hash = _prior_hash(
        args.prior_receipt,
        args.attempt,
        pair_id=raw_case["pair_id"],
        arm_id=args.arm_id,
        surface=args.surface,
    )
    source_data = _normalize_source(_read_bytes(args.source))
    source_hash = sha256_digest(source_data)
    source_bytes = len(source_data)
    source_canonical_bytes = _canonical_source_bytes(source_data)
    issues: list[dict[str, Any]] = []
    parse_pass = False
    preflight_pass: bool | None = None
    compile_pass: bool | None = None
    validator_pass = False
    transaction: Transaction | None = None
    payload_preflight_blocks_canonical_validation = False

    if args.surface == "transaction":
        try:
            transaction = _parse_transaction(source_data, contract)
            parse_pass = True
            (
                payload_issues,
                payload_preflight_blocks_canonical_validation,
            ) = _preflight_transaction_framing_payloads(transaction)
            preflight_pass = not payload_issues
            issues.extend(payload_issues)
        except CandidateDraftMaterializationError as exc:
            issues.append(
                _single_issue(
                    layer="transaction_schema",
                    issue_type=exc.issue_type,
                    message=exc.message,
                    location=exc.location,
                )
            )
        except ValidationError as exc:
            issues.extend(_pydantic_issues(exc, layer="transaction_schema"))
    else:
        draft_model, preflight_draft, compile_draft = _semantic_surface_handlers(
            args.surface
        )
        try:
            draft = draft_model.model_validate_json(source_data, strict=True)
            parse_pass = True
        except ValidationError as exc:
            issues.extend(_pydantic_issues(exc, layer="semantic_schema"))
            draft = None
        if draft is not None:
            report = preflight_draft(snapshot, contract, draft)
            _assert_preflight_setup_valid(list(report.issues))
            preflight_pass = report.passed
            if not report.passed:
                issues.extend(
                    {
                        "layer": "preflight",
                        "type": issue.rule_id,
                        "location": list(issue.location),
                        "message": issue.message,
                        "options": list(issue.options),
                        "rule_id": issue.rule_id,
                        "json_pointer": issue.json_pointer,
                        "expected": issue.expected,
                        "observed": issue.observed,
                    }
                    for issue in report.issues
                )
                compile_pass = False
            else:
                try:
                    transaction = compile_draft(snapshot, contract, draft)
                    compile_pass = True
                except FramingAuditCompilationError as exc:
                    compile_pass = False
                    issues.extend(_compiler_issues(exc))

    compiled_digest: str | None = None
    compiled_bytes: int | None = None
    projection: dict[str, Any] | None = None
    if transaction is not None:
        body = canonical_json_bytes(transaction)
        compiled_digest = sha256_digest(body)
        compiled_bytes = len(body)
        if not (
            args.surface == "transaction"
            and payload_preflight_blocks_canonical_validation
        ):
            try:
                validate_candidate(
                    snapshot,
                    transaction,
                    route_registry_hash=raw_case["route_registry_hash"],
                    enforce_live_current_policy=True,
                )
                validator_pass = True
                projection = _scientific_projection(transaction)
            except (CandidateValidationError, ChainIntegrityError) as exc:
                details = getattr(exc, "diagnostic_details", None)
                options = []
                if isinstance(details, dict) and details:
                    options = [
                        canonical_json_bytes(details).decode("utf-8")[:1000]
                    ]
                issues.append(
                    {
                        "layer": "validator",
                        "type": type(exc).__name__,
                        "location": [],
                        "message": str(exc)[:1000],
                        "options": options,
                        "rule_id": (
                            str(details["rule_id"])
                            if isinstance(details, dict)
                            and isinstance(details.get("rule_id"), str)
                            else None
                        ),
                        "diagnostic_details": (
                            json.loads(canonical_json_bytes(details))
                            if isinstance(details, dict) and details
                            else None
                        ),
                    }
                )

    elapsed_ms = max(0, round((perf_counter() - started) * 1000))
    receipt = {
        "receipt_schema": _RECEIPT_SCHEMA,
        "pair_id": raw_case["pair_id"],
        "arm_id": args.arm_id,
        "surface": args.surface,
        "attempt": args.attempt,
        "source_sha256": source_hash,
        "source_bytes": source_bytes,
        "source_canonical_json_bytes": source_canonical_bytes,
        "parse_pass": parse_pass,
        "preflight_pass": preflight_pass,
        "compile_pass": compile_pass,
        "validator_pass": validator_pass,
        "issues": issues,
        "issue_taxonomy": _taxonomy(issues),
        "compiled_transaction_sha256": compiled_digest,
        "compiled_transaction_bytes": compiled_bytes,
        "first_pass": args.attempt == 1 and validator_pass,
        "final_pass": validator_pass,
        "elapsed_ms": elapsed_ms,
        "prior_receipt_hash": prior_receipt_hash,
        "head_before": snapshot.head,
        "head_after": snapshot.head,
        "canonical_writes": 0,
        "experimental_repairs_submitted": args.attempt - 1,
        "experimental_repair_required": not validator_pass,
        "engine_route_repair_equivalent": (
            1
            if args.surface == "transaction" and not validator_pass
            else 1
            if args.surface in {"semantic", "semantic_v2"}
            and transaction is not None
            and not validator_pass
            else 0
        ),
        "engine_route_repair_eligible_for_burden_comparison": False,
    }
    return (0 if validator_pass else 1), receipt, projection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--surface", choices=_SURFACES, required=True)
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--attempt", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--projection", type=Path)
    parser.add_argument("--prior-receipt", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        status, receipt, projection = _run(args)
        _write_new(args.receipt, canonical_json_bytes(receipt))
        if args.projection is not None and projection is not None:
            _write_new(args.projection, canonical_json_bytes(projection))
        print(canonical_json_bytes(receipt).decode("utf-8"))
        return status
    except SetupError as exc:
        print(f"INVALID_SETUP: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
