"""Canonical evidence bindings for the two built-in Phase 3 assurance checks."""

from __future__ import annotations

import unittest
from fractions import Fraction

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.assurance import (
    ExactAssignment,
    ExactPolynomial,
    ExactPolynomialRelation,
    run_exact_polynomial_relation_scan,
    run_polynomial_identity,
)
from econ_theorist.authoring import (
    CounterexampleScanEvidence,
    ExactAssignmentSpec,
    ExactAssignmentValue,
    ExactPolynomialSpec,
    ExactPolynomialTermSpec,
    ExactRationalValue,
    PolynomialPowerSpec,
    PolynomialRelationPredicate,
    SymbolicIdentityEvidence,
    ToolHarnessReceipt,
)
from econ_theorist.authoring_validation import (
    AuthoringValidationError,
    harness_protocol_code_hash,
    reproducible_harness_artifact_bytes,
    validate_reproducible_tool_receipt,
)
from econ_theorist.codec import sha256_digest
from econ_theorist.models import ArtifactDependencyRef, EntityVersionRef


DUMMY = "a" * 64


def rational(numerator: int, denominator: int = 1) -> ExactRationalValue:
    return ExactRationalValue(numerator=numerator, denominator=denominator)


def polynomial(coefficient: int = 1) -> ExactPolynomialSpec:
    return ExactPolynomialSpec(
        terms=(
            ExactPolynomialTermSpec(
                coefficient=rational(coefficient),
                powers=(PolynomialPowerSpec(variable="x", power=1),),
            ),
        )
    )


def artifact(artifact_id: str, digest: str = DUMMY) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id, version=1, content_hash=digest
    )


def bind_artifacts(receipt: ToolHarnessReceipt) -> ToolHarnessReceipt:
    data = reproducible_harness_artifact_bytes(receipt)
    values = receipt.model_dump(mode="python")
    values.update(
        code_ref=artifact("artifact.harness.code", sha256_digest(data["code"])),
        input_ref=artifact("artifact.harness.input", sha256_digest(data["input"])),
        output_ref=artifact("artifact.harness.output", sha256_digest(data["output"])),
        receipt_ref=(
            artifact("artifact.harness.receipt", sha256_digest(data["receipt"]))
            if "receipt" in data
            else None
        ),
        certificate_ref=(
            artifact("artifact.harness.certificate", sha256_digest(data["certificate"]))
            if "certificate" in data
            else None
        ),
        witness_ref=(
            artifact("artifact.harness.witness", sha256_digest(data["witness"]))
            if "witness" in data
            else None
        ),
    )
    return ToolHarnessReceipt(**values)


def symbolic_receipt() -> ToolHarnessReceipt:
    left_spec = polynomial(2)
    right_spec = polynomial(2)
    exact = ExactPolynomial.normalized(
        ((Fraction(2), {"x": 1}),)
    )
    run = run_polynomial_identity(exact, exact)
    evidence = SymbolicIdentityEvidence(
        left=left_spec,
        right=right_spec,
        input_hash=run.input.input_hash,
        output_hash=run.output.output_hash,
        left_hash=run.certificate.left_hash,
        right_hash=run.certificate.right_hash,
        difference_hash=run.certificate.difference_hash,
        outcome="identity_verified",
        certificate_hash=run.certificate.certificate_hash,
    )
    draft = ToolHarnessReceipt(
        receipt_id="receipt.symbolic",
        harness_kind="symbolic_identity",
        claim_graph_ref=EntityVersionRef(entity_id="claims.main", version=1),
        claim_id="claim.main",
        obligation_ref=EntityVersionRef(entity_id="obligation.main", version=1),
        tool_name="econ_theorist.assurance",
        tool_version=evidence.protocol,
        code_ref=artifact("artifact.harness.code"),
        input_ref=artifact("artifact.harness.input"),
        output_ref=artifact("artifact.harness.output"),
        domain="Exact normalized polynomials over rational coefficients.",
        certificate_ref=artifact("artifact.harness.certificate"),
        outcome="identity_verified",
        evidentiary_role="exact_identity_certificate",
        reproducible_evidence=evidence,
        limitations="Only the represented polynomial identity is certified.",
        executed_at="2026-07-12T00:00:00Z",
    )
    return bind_artifacts(draft)


def finite_receipt() -> ToolHarnessReceipt:
    predicate = PolynomialRelationPredicate(
        left=polynomial(1), relation="ge", right=ExactPolynomialSpec()
    )
    case_specs = (
        ExactAssignmentSpec(
            case_id="case.zero",
            values=(ExactAssignmentValue(variable="x", value=rational(0)),),
        ),
        ExactAssignmentSpec(
            case_id="case.one",
            values=(ExactAssignmentValue(variable="x", value=rational(1)),),
        ),
    )
    cases = tuple(
        ExactAssignment(
            case_id=item.case_id,
            values=tuple(
                (
                    value.variable,
                    Fraction(value.value.numerator, value.value.denominator),
                )
                for value in item.values
            ),
        )
        for item in case_specs
    )
    protocol = "exact_polynomial_relation_scan.v1"
    code_hash = harness_protocol_code_hash(protocol)
    scan = run_exact_polynomial_relation_scan(
        ExactPolynomialRelation(
            left=ExactPolynomial.normalized(((Fraction(1), {"x": 1}),)),
            operator="ge",
            right=ExactPolynomial(),
        ),
        cases,
        code_hash=code_hash,
    )
    evidence = CounterexampleScanEvidence(
        predicate=predicate,
        cases=case_specs,
        code_hash=scan.input.code_hash,
        input_hash=scan.input.input_hash,
        output_hash=scan.output.output_hash,
        domain_hash=scan.output.domain_hash,
        relation_hash=scan.output.relation_hash,
        checked_count=scan.output.checked_count,
        outcome=scan.output.outcome,
        witness_case_id=None,
        witness_hash=None,
        receipt_hash=scan.receipt.receipt_hash,
    )
    draft = ToolHarnessReceipt(
        receipt_id="receipt.finite",
        harness_kind="counterexample_search",
        claim_graph_ref=EntityVersionRef(entity_id="claims.main", version=1),
        claim_id="claim.main",
        obligation_ref=EntityVersionRef(entity_id="obligation.main", version=1),
        tool_name="econ_theorist.assurance",
        tool_version=protocol,
        code_ref=artifact("artifact.harness.code"),
        input_ref=artifact("artifact.harness.input"),
        output_ref=artifact("artifact.harness.output"),
        receipt_ref=artifact("artifact.harness.receipt"),
        domain="The exact ordered cases x=0 and x=1.",
        outcome="no_counterexample_found",
        evidentiary_role="corroboration_only",
        reproducible_evidence=evidence,
        limitations="This finite domain corroborates but cannot prove a universal claim.",
        executed_at="2026-07-12T00:01:00Z",
    )
    return bind_artifacts(draft)


class CanonicalAssuranceEvidenceTests(unittest.TestCase):
    def test_symbolic_receipt_recomputes_and_binds_all_artifact_bytes(self) -> None:
        receipt = symbolic_receipt()
        validate_reproducible_tool_receipt(receipt)
        bound = reproducible_harness_artifact_bytes(receipt)
        self.assertEqual(receipt.code_ref.content_hash, sha256_digest(bound["code"]))
        self.assertEqual(
            receipt.certificate_ref.content_hash,
            sha256_digest(bound["certificate"]),
        )

    def test_symbolic_certificate_and_artifact_tampering_fail(self) -> None:
        receipt = symbolic_receipt()
        evidence = receipt.reproducible_evidence
        assert isinstance(evidence, SymbolicIdentityEvidence)
        forged = evidence.model_copy(update={"certificate_hash": "b" * 64})
        with self.assertRaisesRegex(AuthoringValidationError, "does not reproduce"):
            validate_reproducible_tool_receipt(
                receipt.model_copy(update={"reproducible_evidence": forged})
            )
        with self.assertRaisesRegex(AuthoringValidationError, "input artifact hash"):
            validate_reproducible_tool_receipt(
                receipt.model_copy(
                    update={"input_ref": artifact("artifact.harness.input", "c" * 64)}
                )
            )

    def test_finite_relation_scan_replays_with_external_pinned_code_hash(self) -> None:
        receipt = finite_receipt()
        validate_reproducible_tool_receipt(receipt)
        evidence = receipt.reproducible_evidence
        assert isinstance(evidence, CounterexampleScanEvidence)
        self.assertEqual(
            evidence.code_hash,
            harness_protocol_code_hash("exact_polynomial_relation_scan.v1"),
        )
        self.assertEqual(
            receipt.receipt_ref.content_hash,
            sha256_digest(reproducible_harness_artifact_bytes(receipt)["receipt"]),
        )

    def test_finite_relation_domain_code_and_outcome_tampering_fail(self) -> None:
        receipt = finite_receipt()
        evidence = receipt.reproducible_evidence
        assert isinstance(evidence, CounterexampleScanEvidence)
        forged_relation = evidence.predicate.model_copy(update={"relation": "gt"})
        forged = evidence.model_copy(update={"predicate": forged_relation})
        with self.assertRaisesRegex(AuthoringValidationError, "does not reproduce"):
            validate_reproducible_tool_receipt(
                receipt.model_copy(update={"reproducible_evidence": forged})
            )
        forged_code = evidence.model_copy(update={"code_hash": "d" * 64})
        with self.assertRaisesRegex(AuthoringValidationError, "not the pinned"):
            validate_reproducible_tool_receipt(
                receipt.model_copy(update={"reproducible_evidence": forged_code})
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
