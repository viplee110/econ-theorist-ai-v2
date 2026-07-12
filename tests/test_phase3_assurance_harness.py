from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.assurance import (
    AssuranceHarnessError,
    ExactAssignment,
    ExactPolynomial,
    ExactPolynomialRelation,
    POLYNOMIAL_IDENTITY_PROTOCOL,
    POLYNOMIAL_RELATION_SCAN_PROTOCOL,
    PolynomialIdentityRun,
    PolynomialIdentityRunCertificate,
    PolynomialRelationScanReceipt,
    PolynomialRelationScanRun,
    check_polynomial_identity,
    run_exact_polynomial_relation_scan,
    run_polynomial_identity,
    scan_exact_domain,
    verify_counterexample_scan_receipt,
    verify_exact_polynomial_relation_scan,
    verify_polynomial_identity_certificate,
    verify_polynomial_identity_run,
)
from econ_theorist.codec import object_digest, sha256_digest


def polynomial(
    *terms: tuple[int, dict[str, int]],
) -> ExactPolynomial:
    return ExactPolynomial.normalized(
        (Fraction(coefficient), powers) for coefficient, powers in terms
    )


class Phase3AssuranceHarnessTests(unittest.TestCase):
    def test_exact_identity_normalizes_terms_and_reproduces(self) -> None:
        left = ExactPolynomial.normalized(
            (
                (Fraction(1), {"x": 1}),
                (Fraction(2), {"y": 1}),
                (Fraction(-1), {"x": 1}),
            )
        )
        right = ExactPolynomial.normalized(((Fraction(2), {"y": 1}),))
        certificate = check_polynomial_identity(left, right)

        self.assertEqual(certificate.outcome, "identity_verified")
        verify_polynomial_identity_certificate(left, right, certificate)

    def test_symbolic_certificate_tampering_is_rejected(self) -> None:
        left = ExactPolynomial.normalized(((Fraction(1), {"x": 1}),))
        right = ExactPolynomial.normalized(((Fraction(1), {"x": 1}),))
        certificate = check_polynomial_identity(left, right)

        with self.assertRaisesRegex(
            AssuranceHarnessError, "does not reproduce exactly"
        ):
            verify_polynomial_identity_certificate(
                left,
                right,
                replace(certificate, certificate_hash="0" * 64),
            )

    def test_failed_identity_does_not_certify_equality(self) -> None:
        left = ExactPolynomial.normalized(((Fraction(1), {"x": 1}),))
        right = ExactPolynomial.normalized(((Fraction(2), {"x": 1}),))

        self.assertEqual(
            check_polynomial_identity(left, right).outcome,
            "identity_failed",
        )

    def test_counterexample_scan_preserves_first_exact_witness(self) -> None:
        cases = (
            ExactAssignment("positive", (("x", Fraction(1)),)),
            ExactAssignment("zero", (("x", Fraction(0)),)),
            ExactAssignment("negative", (("x", Fraction(-1)),)),
        )
        receipt = scan_exact_domain(
            cases,
            lambda assignment: assignment["x"] > 0,
            code_hash="1" * 64,
        )

        self.assertEqual(receipt.outcome, "falsified")
        self.assertEqual(receipt.checked_count, 2)
        self.assertIsNotNone(receipt.witness)
        self.assertEqual(receipt.witness.case_id, "zero")
        verify_counterexample_scan_receipt(
            cases,
            lambda assignment: assignment["x"] > 0,
            receipt,
        )

    def test_no_finite_witness_remains_bounded_corroboration(self) -> None:
        cases = (
            ExactAssignment("one", (("x", Fraction(1)),)),
            ExactAssignment("two", (("x", Fraction(2)),)),
        )
        receipt = scan_exact_domain(
            cases,
            lambda assignment: assignment["x"] > 0,
            code_hash="2" * 64,
        )

        self.assertEqual(receipt.outcome, "no_counterexample_found")
        self.assertIsNone(receipt.witness)
        self.assertIn("not proof", receipt.evidentiary_limit)

    def test_counterexample_receipt_tampering_is_rejected(self) -> None:
        cases = (ExactAssignment("one", (("x", Fraction(1)),)),)
        receipt = scan_exact_domain(
            cases,
            lambda assignment: assignment["x"] > 0,
            code_hash="3" * 64,
        )

        with self.assertRaisesRegex(
            AssuranceHarnessError, "does not reproduce exactly"
        ):
            verify_counterexample_scan_receipt(
                cases,
                lambda assignment: assignment["x"] > 0,
                replace(receipt, domain_hash="4" * 64),
            )

    def test_predicate_must_return_a_real_bool(self) -> None:
        cases = (ExactAssignment("one", (("x", Fraction(1)),)),)

        with self.assertRaisesRegex(AssuranceHarnessError, "must return bool"):
            scan_exact_domain(
                cases,
                lambda assignment: 1,  # type: ignore[return-value]
                code_hash="5" * 64,
            )


class CanonicalPolynomialIdentityProtocolTests(unittest.TestCase):
    def identity_run(self) -> PolynomialIdentityRun:
        left = polynomial(
            (1, {"x": 1}),
            (2, {"y": 1}),
            (-1, {"x": 1}),
        )
        right = polynomial((2, {"y": 1}))
        return run_polynomial_identity(left, right)

    def test_identity_input_output_certificate_are_independently_canonical(self) -> None:
        run = self.identity_run()
        verify_polynomial_identity_run(run)

        self.assertEqual(run.protocol, POLYNOMIAL_IDENTITY_PROTOCOL)
        self.assertEqual(
            set(run.input.canonical_data()), {"protocol", "left", "right"}
        )
        self.assertEqual(
            set(run.output.canonical_data()),
            {
                "protocol",
                "input_hash",
                "difference",
                "difference_hash",
                "outcome",
            },
        )
        self.assertEqual(
            set(run.certificate.canonical_data()),
            {
                "protocol",
                "input_hash",
                "output_hash",
                "left_hash",
                "right_hash",
                "difference_hash",
                "outcome",
                "certificate_hash",
            },
        )
        self.assertEqual(
            run.input.input_hash, sha256_digest(run.input.canonical_bytes())
        )
        self.assertEqual(
            run.output.output_hash, sha256_digest(run.output.canonical_bytes())
        )
        self.assertEqual(
            run.certificate.artifact_hash,
            sha256_digest(run.certificate.canonical_bytes()),
        )

        parsed = PolynomialIdentityRun.from_canonical_bytes(run.canonical_bytes())
        self.assertEqual(parsed, run)
        verify_polynomial_identity_run(parsed)

    def test_failed_identity_run_is_replayable_failure_evidence(self) -> None:
        run = run_polynomial_identity(
            polynomial((1, {"x": 1})),
            polynomial((2, {"x": 1})),
        )
        self.assertEqual(run.output.outcome, "identity_failed")
        self.assertTrue(run.output.difference.terms)
        verify_polynomial_identity_run(run)

    def test_identity_protocol_and_input_tampering_fail(self) -> None:
        run = self.identity_run()
        tampered_protocol = run.canonical_data()
        tampered_protocol["protocol"] = "exact_polynomial_identity.v2"
        with self.assertRaisesRegex(AssuranceHarnessError, "unknown"):
            PolynomialIdentityRun.from_canonical_data(tampered_protocol)

        changed_input = replace(
            run.input,
            left=polynomial((3, {"y": 1})),
        )
        with self.assertRaisesRegex(AssuranceHarnessError, "does not reproduce"):
            verify_polynomial_identity_run(replace(run, input=changed_input))

    def test_identity_output_and_certificate_tampering_fail(self) -> None:
        run = self.identity_run()
        forged_output = replace(
            run.output,
            difference=polynomial((1, {"x": 1})),
            outcome="identity_failed",
        )
        with self.assertRaisesRegex(AssuranceHarnessError, "does not reproduce"):
            verify_polynomial_identity_run(replace(run, output=forged_output))

        certificate_body = {
            **run.certificate.body_data(),
            "left_hash": "9" * 64,
        }
        forged_certificate = PolynomialIdentityRunCertificate(
            input_hash=run.certificate.input_hash,
            output_hash=run.certificate.output_hash,
            left_hash="9" * 64,
            right_hash=run.certificate.right_hash,
            difference_hash=run.certificate.difference_hash,
            outcome=run.certificate.outcome,
            certificate_hash=object_digest(certificate_body),
        )
        with self.assertRaisesRegex(AssuranceHarnessError, "does not reproduce"):
            verify_polynomial_identity_run(
                replace(run, certificate=forged_certificate)
            )

        serialized = run.certificate.canonical_data()
        serialized["certificate_hash"] = "0" * 64
        with self.assertRaisesRegex(AssuranceHarnessError, "body hash"):
            PolynomialIdentityRunCertificate.from_canonical_data(serialized)

    def test_noncanonical_identity_bytes_are_rejected(self) -> None:
        run = self.identity_run()
        with self.assertRaisesRegex(AssuranceHarnessError, "not canonical JSON"):
            PolynomialIdentityRun.from_canonical_bytes(
                run.canonical_bytes() + b"\n"
            )


class CanonicalPolynomialRelationScanProtocolTests(unittest.TestCase):
    CODE_HASH = "7" * 64

    @staticmethod
    def cases() -> tuple[ExactAssignment, ...]:
        return (
            ExactAssignment("positive", (("x", Fraction(1)),)),
            ExactAssignment("zero", (("x", Fraction(0)),)),
            ExactAssignment("negative", (("x", Fraction(-1)),)),
        )

    @staticmethod
    def positive_relation(operator: str = "gt") -> ExactPolynomialRelation:
        return ExactPolynomialRelation(
            left=polynomial((1, {"x": 1})),
            operator=operator,  # type: ignore[arg-type]
            right=ExactPolynomial(),
        )

    def scan_run(self) -> PolynomialRelationScanRun:
        return run_exact_polynomial_relation_scan(
            self.positive_relation(),
            self.cases(),
            code_hash=self.CODE_HASH,
        )

    def test_relation_scan_segments_are_canonical_and_replayable(self) -> None:
        run = self.scan_run()
        verify_exact_polynomial_relation_scan(
            run, expected_code_hash=self.CODE_HASH
        )

        self.assertEqual(run.protocol, POLYNOMIAL_RELATION_SCAN_PROTOCOL)
        self.assertEqual(run.output.outcome, "falsified")
        self.assertEqual(run.output.checked_count, 2)
        self.assertEqual(run.output.witness, self.cases()[1])
        self.assertEqual(
            set(run.input.canonical_data()),
            {"protocol", "code_hash", "relation", "domain"},
        )
        self.assertEqual(
            set(run.output.canonical_data()),
            {
                "protocol",
                "input_hash",
                "domain_hash",
                "relation_hash",
                "checked_count",
                "outcome",
                "witness",
            },
        )
        self.assertEqual(
            set(run.receipt.canonical_data()),
            {
                "protocol",
                "input_hash",
                "output_hash",
                "code_hash",
                "domain_hash",
                "relation_hash",
                "checked_count",
                "outcome",
                "witness_hash",
                "receipt_hash",
                "evidentiary_limit",
            },
        )
        self.assertEqual(
            run.input.input_hash, sha256_digest(run.input.canonical_bytes())
        )
        self.assertEqual(
            run.output.output_hash, sha256_digest(run.output.canonical_bytes())
        )
        self.assertEqual(
            run.receipt.artifact_hash,
            sha256_digest(run.receipt.canonical_bytes()),
        )
        parsed = PolynomialRelationScanRun.from_canonical_bytes(
            run.canonical_bytes()
        )
        self.assertEqual(parsed, run)
        verify_exact_polynomial_relation_scan(
            parsed, expected_code_hash=self.CODE_HASH
        )

    def test_all_relation_operators_have_exact_pointwise_semantics(self) -> None:
        cases = (ExactAssignment("one", (("x", Fraction(1)),)),)
        expected = {
            "eq": "falsified",
            "le": "falsified",
            "lt": "falsified",
            "ge": "no_counterexample_found",
            "gt": "no_counterexample_found",
        }
        for operator, outcome in expected.items():
            with self.subTest(operator=operator):
                run = run_exact_polynomial_relation_scan(
                    self.positive_relation(operator),
                    cases,
                    code_hash=self.CODE_HASH,
                )
                self.assertEqual(run.output.outcome, outcome)
                verify_exact_polynomial_relation_scan(
                    run, expected_code_hash=self.CODE_HASH
                )

    def test_expected_code_hash_is_external_to_the_receipt(self) -> None:
        run = self.scan_run()
        with self.assertRaisesRegex(AssuranceHarnessError, "caller expectation"):
            verify_exact_polynomial_relation_scan(
                run, expected_code_hash="8" * 64
            )

        self_consistent_other_code = run_exact_polynomial_relation_scan(
            run.input.relation,
            run.input.domain,
            code_hash="8" * 64,
        )
        with self.assertRaisesRegex(AssuranceHarnessError, "caller expectation"):
            verify_exact_polynomial_relation_scan(
                self_consistent_other_code,
                expected_code_hash=self.CODE_HASH,
            )

        legacy = scan_exact_domain(
            self.cases(),
            lambda assignment: assignment["x"] > 0,
            code_hash=self.CODE_HASH,
        )
        with self.assertRaisesRegex(AssuranceHarnessError, "caller expectation"):
            verify_counterexample_scan_receipt(
                self.cases(),
                lambda assignment: assignment["x"] > 0,
                legacy,
                expected_code_hash="8" * 64,
            )

    def test_domain_and_relation_tampering_fail_replay(self) -> None:
        run = self.scan_run()
        changed_domain = replace(
            run.input,
            domain=(run.input.domain[0], run.input.domain[2]),
        )
        with self.assertRaisesRegex(AssuranceHarnessError, "does not reproduce"):
            verify_exact_polynomial_relation_scan(
                replace(run, input=changed_domain),
                expected_code_hash=self.CODE_HASH,
            )

        changed_relation = replace(
            run.input,
            relation=self.positive_relation("ge"),
        )
        with self.assertRaisesRegex(AssuranceHarnessError, "does not reproduce"):
            verify_exact_polynomial_relation_scan(
                replace(run, input=changed_relation),
                expected_code_hash=self.CODE_HASH,
            )

    def test_output_receipt_and_witness_tampering_fail_replay(self) -> None:
        run = self.scan_run()
        forged_output = replace(run.output, checked_count=1)
        with self.assertRaisesRegex(AssuranceHarnessError, "does not reproduce"):
            verify_exact_polynomial_relation_scan(
                replace(run, output=forged_output),
                expected_code_hash=self.CODE_HASH,
            )

        forged_limit_text = "This finite scan proves the universal theorem."
        forged_limit_body = {
            **run.receipt.body_data(),
            "evidentiary_limit": forged_limit_text,
        }
        forged_limit = replace(
            run.receipt,
            evidentiary_limit=forged_limit_text,
            receipt_hash=object_digest(forged_limit_body),
        )
        with self.assertRaisesRegex(AssuranceHarnessError, "does not reproduce"):
            verify_exact_polynomial_relation_scan(
                replace(run, receipt=forged_limit),
                expected_code_hash=self.CODE_HASH,
            )

        wrong_witness = run.input.domain[0]
        wrong_output = replace(
            run.output,
            checked_count=1,
            witness=wrong_witness,
        )
        receipt_body = {
            **run.receipt.body_data(),
            "output_hash": wrong_output.output_hash,
            "checked_count": 1,
            "witness_hash": wrong_witness.digest,
        }
        wrong_receipt = PolynomialRelationScanReceipt(
            input_hash=run.receipt.input_hash,
            output_hash=wrong_output.output_hash,
            code_hash=run.receipt.code_hash,
            domain_hash=run.receipt.domain_hash,
            relation_hash=run.receipt.relation_hash,
            checked_count=1,
            outcome="falsified",
            witness_hash=wrong_witness.digest,
            receipt_hash=object_digest(receipt_body),
        )
        forged_run = replace(run, output=wrong_output, receipt=wrong_receipt)
        with self.assertRaisesRegex(AssuranceHarnessError, "does not reproduce"):
            verify_exact_polynomial_relation_scan(
                forged_run, expected_code_hash=self.CODE_HASH
            )

    def test_relation_scan_protocol_tampering_fails_parse(self) -> None:
        run = self.scan_run()
        data = run.canonical_data()
        data["protocol"] = "exact_polynomial_relation_scan.v2"
        with self.assertRaisesRegex(AssuranceHarnessError, "unknown"):
            PolynomialRelationScanRun.from_canonical_data(data)


if __name__ == "__main__":
    unittest.main()
