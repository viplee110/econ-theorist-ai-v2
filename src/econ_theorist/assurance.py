"""Small exact-arithmetic harnesses for Phase 3 formal assurance.

The harnesses produce reproducible certificates and falsification witnesses.
They deliberately do not promote scientific status: a finite search that finds
no witness remains finite corroboration, while a normalized polynomial
identity certifies only the exact algebraic identity represented here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
import json
import re
from typing import Literal

from .codec import canonical_json_bytes, object_digest


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
POLYNOMIAL_IDENTITY_PROTOCOL = "exact_polynomial_identity.v1"
POLYNOMIAL_RELATION_SCAN_PROTOCOL = "exact_polynomial_relation_scan.v1"
FINITE_RELATION_EVIDENTIARY_LIMIT = (
    "No witness in a finite exact domain is corroboration, not proof of a universal claim."
)


class AssuranceHarnessError(ValueError):
    """An exact assurance harness received a noncanonical specification."""


def _require_digest(value: object, *, label: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise AssuranceHarnessError(f"{label} must be one lowercase sha256 digest")
    return value


def _require_exact_mapping(
    value: object, *, keys: frozenset[str], label: str
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise AssuranceHarnessError(f"{label} must be an object")
    if not all(isinstance(key, str) for key in value):
        raise AssuranceHarnessError(f"{label} keys must be strings")
    actual = frozenset(value)
    if actual != keys:
        missing = ", ".join(sorted(keys.difference(actual))) or "none"
        extra = ", ".join(sorted(actual.difference(keys))) or "none"
        raise AssuranceHarnessError(
            f"{label} has the wrong fields (missing: {missing}; extra: {extra})"
        )
    return value


def _require_sequence(value: object, *, label: str) -> Sequence[object]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise AssuranceHarnessError(f"{label} must be an array")
    return value


def _fraction_from_canonical_data(value: object) -> Fraction:
    record = _require_exact_mapping(
        value,
        keys=frozenset({"numerator", "denominator"}),
        label="rational",
    )
    numerator = record["numerator"]
    denominator = record["denominator"]
    if (
        isinstance(numerator, bool)
        or not isinstance(numerator, int)
        or isinstance(denominator, bool)
        or not isinstance(denominator, int)
        or denominator <= 0
    ):
        raise AssuranceHarnessError(
            "canonical rationals require an integer numerator and positive denominator"
        )
    result = Fraction(numerator, denominator)
    if _rational(result) != dict(record):
        raise AssuranceHarnessError("rational input is not in reduced canonical form")
    return result


def _canonical_json_value(data: bytes, *, label: str) -> object:
    if not isinstance(data, bytes):
        raise TypeError(f"{label} must be canonical JSON bytes")

    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise AssuranceHarnessError(
                    f"{label} contains duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    def reject_nonfinite_constant(token: str) -> object:
        raise AssuranceHarnessError(
            f"{label} contains forbidden JSON constant {token}"
        )

    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite_constant,
        )
    except AssuranceHarnessError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AssuranceHarnessError(f"{label} is not valid canonical JSON") from exc
    if canonical_json_bytes(value) != data:
        raise AssuranceHarnessError(f"{label} bytes are not canonical JSON")
    return value


def _rational(value: Fraction) -> dict[str, int]:
    return {"numerator": value.numerator, "denominator": value.denominator}


@dataclass(frozen=True, slots=True)
class PolynomialTerm:
    """One nonzero exact term in a commutative multivariate polynomial."""

    coefficient: Fraction
    powers: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.coefficient, Fraction):
            raise AssuranceHarnessError("polynomial coefficients must be Fractions")
        if self.coefficient == 0:
            raise AssuranceHarnessError("zero polynomial terms must be omitted")
        variables = tuple(variable for variable, _ in self.powers)
        if any(
            not isinstance(variable, str) or not variable
            for variable in variables
        ):
            raise AssuranceHarnessError("polynomial variables must be nonempty strings")
        if len(set(variables)) != len(variables) or variables != tuple(sorted(variables)):
            raise AssuranceHarnessError("polynomial powers must use unique sorted variables")
        if any(isinstance(power, bool) or not isinstance(power, int) or power < 1 for _, power in self.powers):
            raise AssuranceHarnessError("polynomial powers must be positive integers")

    @property
    def monomial(self) -> tuple[tuple[str, int], ...]:
        return self.powers

    def canonical_data(self) -> dict[str, object]:
        return {
            "coefficient": _rational(self.coefficient),
            "powers": tuple(
                {"variable": variable, "power": power}
                for variable, power in self.powers
            ),
        }


@dataclass(frozen=True, slots=True)
class ExactPolynomial:
    """A normalized exact polynomial with lexicographically ordered monomials."""

    terms: tuple[PolynomialTerm, ...] = ()

    def __post_init__(self) -> None:
        monomials = tuple(term.monomial for term in self.terms)
        if len(set(monomials)) != len(monomials):
            raise AssuranceHarnessError("polynomial monomials must be unique")
        if monomials != tuple(sorted(monomials)):
            raise AssuranceHarnessError("polynomial monomials must be canonically ordered")

    @classmethod
    def normalized(
        cls,
        terms: Iterable[tuple[Fraction, Mapping[str, int]]],
    ) -> "ExactPolynomial":
        combined: dict[tuple[tuple[str, int], ...], Fraction] = {}
        for coefficient, raw_powers in terms:
            if not isinstance(coefficient, Fraction):
                raise AssuranceHarnessError("polynomial coefficients must be Fractions")
            powers = tuple(sorted(raw_powers.items()))
            if any(
                not isinstance(variable, str)
                or not variable
                or isinstance(power, bool)
                or not isinstance(power, int)
                or power < 1
                for variable, power in powers
            ):
                raise AssuranceHarnessError(
                    "polynomial powers require nonempty variables and positive integers"
                )
            combined[powers] = combined.get(powers, Fraction(0)) + coefficient
        return cls(
            tuple(
                PolynomialTerm(coefficient=coefficient, powers=powers)
                for powers, coefficient in sorted(combined.items())
                if coefficient != 0
            )
        )

    def canonical_data(self) -> dict[str, object]:
        return {"terms": tuple(term.canonical_data() for term in self.terms)}

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "ExactPolynomial":
        record = _require_exact_mapping(
            value, keys=frozenset({"terms"}), label="exact polynomial"
        )
        raw_terms = _require_sequence(
            record["terms"], label="exact polynomial terms"
        )
        terms: list[PolynomialTerm] = []
        for raw_term in raw_terms:
            term_record = _require_exact_mapping(
                raw_term,
                keys=frozenset({"coefficient", "powers"}),
                label="polynomial term",
            )
            raw_powers = _require_sequence(
                term_record["powers"], label="polynomial term powers"
            )
            powers: list[tuple[str, int]] = []
            for raw_power in raw_powers:
                power_record = _require_exact_mapping(
                    raw_power,
                    keys=frozenset({"variable", "power"}),
                    label="polynomial power",
                )
                variable = power_record["variable"]
                power = power_record["power"]
                if not isinstance(variable, str) or not variable:
                    raise AssuranceHarnessError(
                        "polynomial variables must be nonempty strings"
                    )
                if isinstance(power, bool) or not isinstance(power, int) or power < 1:
                    raise AssuranceHarnessError(
                        "polynomial powers must be positive integers"
                    )
                powers.append((variable, power))
            terms.append(
                PolynomialTerm(
                    coefficient=_fraction_from_canonical_data(
                        term_record["coefficient"]
                    ),
                    powers=tuple(powers),
                )
            )
        result = cls(tuple(terms))
        if result.canonical_data() != {
            "terms": tuple(
                {
                    "coefficient": dict(item["coefficient"]),
                    "powers": tuple(dict(power) for power in item["powers"]),
                }
                for item in raw_terms
            )
        }:
            raise AssuranceHarnessError("polynomial input is not canonical")
        return result

    @classmethod
    def from_canonical_bytes(cls, data: bytes) -> "ExactPolynomial":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="exact polynomial")
        )

    @property
    def digest(self) -> str:
        return object_digest(self.canonical_data())

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    variable
                    for term in self.terms
                    for variable, _ in term.powers
                }
            )
        )

    def evaluate(self, assignment: Mapping[str, Fraction]) -> Fraction:
        result = Fraction(0)
        for term in self.terms:
            value = term.coefficient
            for variable, power in term.powers:
                if variable not in assignment:
                    raise AssuranceHarnessError(
                        f"polynomial assignment omits variable {variable!r}"
                    )
                assigned = assignment[variable]
                if not isinstance(assigned, Fraction):
                    raise AssuranceHarnessError(
                        "polynomial assignments must contain Fractions"
                    )
                value *= assigned**power
            result += value
        return result

    def subtract(self, other: "ExactPolynomial") -> "ExactPolynomial":
        return ExactPolynomial.normalized(
            (
                *((term.coefficient, dict(term.powers)) for term in self.terms),
                *((-term.coefficient, dict(term.powers)) for term in other.terms),
            )
        )


@dataclass(frozen=True, slots=True)
class SymbolicIdentityCertificate:
    left_hash: str
    right_hash: str
    difference_hash: str
    outcome: str
    certificate_hash: str
    evidentiary_limit: str = (
        "Certifies only equality of the represented normalized polynomials."
    )


def check_polynomial_identity(
    left: ExactPolynomial, right: ExactPolynomial
) -> SymbolicIdentityCertificate:
    """Normalize two exact polynomials and certify equality of that identity."""

    if not isinstance(left, ExactPolynomial) or not isinstance(right, ExactPolynomial):
        raise TypeError("left and right must be ExactPolynomial values")
    difference = left.subtract(right)
    outcome = "identity_verified" if not difference.terms else "identity_failed"
    payload = {
        "harness": "exact_polynomial_identity.v1",
        "left_hash": left.digest,
        "right_hash": right.digest,
        "difference_hash": difference.digest,
        "outcome": outcome,
    }
    return SymbolicIdentityCertificate(
        left_hash=left.digest,
        right_hash=right.digest,
        difference_hash=difference.digest,
        outcome=outcome,
        certificate_hash=object_digest(payload),
    )


def verify_polynomial_identity_certificate(
    left: ExactPolynomial,
    right: ExactPolynomial,
    certificate: SymbolicIdentityCertificate,
) -> None:
    """Recompute one identity certificate and reject any changed field."""

    if not isinstance(certificate, SymbolicIdentityCertificate):
        raise TypeError("certificate must be a SymbolicIdentityCertificate")
    expected = check_polynomial_identity(left, right)
    if certificate != expected:
        raise AssuranceHarnessError(
            "symbolic identity certificate does not reproduce exactly"
        )


@dataclass(frozen=True, slots=True)
class PolynomialIdentityInput:
    """Canonical exact inputs for the built-in polynomial identity protocol."""

    left: ExactPolynomial
    right: ExactPolynomial
    protocol: str = POLYNOMIAL_IDENTITY_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != POLYNOMIAL_IDENTITY_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial identity protocol")
        if not isinstance(self.left, ExactPolynomial) or not isinstance(
            self.right, ExactPolynomial
        ):
            raise AssuranceHarnessError(
                "polynomial identity inputs must be ExactPolynomial values"
            )

    def canonical_data(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "left": self.left.canonical_data(),
            "right": self.right.canonical_data(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def input_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "PolynomialIdentityInput":
        record = _require_exact_mapping(
            value,
            keys=frozenset({"protocol", "left", "right"}),
            label="polynomial identity input",
        )
        protocol = record["protocol"]
        if protocol != POLYNOMIAL_IDENTITY_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial identity protocol")
        return cls(
            protocol=POLYNOMIAL_IDENTITY_PROTOCOL,
            left=ExactPolynomial.from_canonical_data(record["left"]),
            right=ExactPolynomial.from_canonical_data(record["right"]),
        )

    @classmethod
    def from_canonical_bytes(cls, data: bytes) -> "PolynomialIdentityInput":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="polynomial identity input")
        )


@dataclass(frozen=True, slots=True)
class PolynomialIdentityOutput:
    """Canonical deterministic output for one identity input."""

    input_hash: str
    difference: ExactPolynomial
    outcome: Literal["identity_verified", "identity_failed"]
    protocol: str = POLYNOMIAL_IDENTITY_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != POLYNOMIAL_IDENTITY_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial identity protocol")
        _require_digest(self.input_hash, label="identity input_hash")
        if not isinstance(self.difference, ExactPolynomial):
            raise AssuranceHarnessError(
                "polynomial identity difference must be an ExactPolynomial"
            )
        if self.outcome not in {"identity_verified", "identity_failed"}:
            raise AssuranceHarnessError("unknown polynomial identity outcome")
        expected_outcome = (
            "identity_verified" if not self.difference.terms else "identity_failed"
        )
        if self.outcome != expected_outcome:
            raise AssuranceHarnessError(
                "polynomial identity outcome disagrees with its exact difference"
            )

    def canonical_data(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "input_hash": self.input_hash,
            "difference": self.difference.canonical_data(),
            "difference_hash": self.difference.digest,
            "outcome": self.outcome,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def output_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "PolynomialIdentityOutput":
        record = _require_exact_mapping(
            value,
            keys=frozenset(
                {
                    "protocol",
                    "input_hash",
                    "difference",
                    "difference_hash",
                    "outcome",
                }
            ),
            label="polynomial identity output",
        )
        if record["protocol"] != POLYNOMIAL_IDENTITY_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial identity protocol")
        difference = ExactPolynomial.from_canonical_data(record["difference"])
        if record["difference_hash"] != difference.digest:
            raise AssuranceHarnessError("identity difference hash mismatches")
        outcome = record["outcome"]
        if outcome not in {"identity_verified", "identity_failed"}:
            raise AssuranceHarnessError("unknown polynomial identity outcome")
        return cls(
            protocol=POLYNOMIAL_IDENTITY_PROTOCOL,
            input_hash=_require_digest(
                record["input_hash"], label="identity input_hash"
            ),
            difference=difference,
            outcome=outcome,
        )

    @classmethod
    def from_canonical_bytes(cls, data: bytes) -> "PolynomialIdentityOutput":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="polynomial identity output")
        )


@dataclass(frozen=True, slots=True)
class PolynomialIdentityRunCertificate:
    """Hash closure over one canonical identity input and output."""

    input_hash: str
    output_hash: str
    left_hash: str
    right_hash: str
    difference_hash: str
    outcome: Literal["identity_verified", "identity_failed"]
    certificate_hash: str
    protocol: str = POLYNOMIAL_IDENTITY_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != POLYNOMIAL_IDENTITY_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial identity protocol")
        for label, value in (
            ("input_hash", self.input_hash),
            ("output_hash", self.output_hash),
            ("left_hash", self.left_hash),
            ("right_hash", self.right_hash),
            ("difference_hash", self.difference_hash),
            ("certificate_hash", self.certificate_hash),
        ):
            _require_digest(value, label=f"identity certificate {label}")
        if self.outcome not in {"identity_verified", "identity_failed"}:
            raise AssuranceHarnessError("unknown polynomial identity outcome")
        if self.certificate_hash != object_digest(self.body_data()):
            raise AssuranceHarnessError(
                "polynomial identity certificate body hash mismatches"
            )

    def body_data(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "left_hash": self.left_hash,
            "right_hash": self.right_hash,
            "difference_hash": self.difference_hash,
            "outcome": self.outcome,
        }

    def canonical_data(self) -> dict[str, object]:
        return {**self.body_data(), "certificate_hash": self.certificate_hash}

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def artifact_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(
        cls, value: object
    ) -> "PolynomialIdentityRunCertificate":
        record = _require_exact_mapping(
            value,
            keys=frozenset(
                {
                    "protocol",
                    "input_hash",
                    "output_hash",
                    "left_hash",
                    "right_hash",
                    "difference_hash",
                    "outcome",
                    "certificate_hash",
                }
            ),
            label="polynomial identity certificate",
        )
        if record["protocol"] != POLYNOMIAL_IDENTITY_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial identity protocol")
        outcome = record["outcome"]
        if outcome not in {"identity_verified", "identity_failed"}:
            raise AssuranceHarnessError("unknown polynomial identity outcome")
        return cls(
            protocol=POLYNOMIAL_IDENTITY_PROTOCOL,
            input_hash=_require_digest(
                record["input_hash"], label="identity certificate input_hash"
            ),
            output_hash=_require_digest(
                record["output_hash"], label="identity certificate output_hash"
            ),
            left_hash=_require_digest(
                record["left_hash"], label="identity certificate left_hash"
            ),
            right_hash=_require_digest(
                record["right_hash"], label="identity certificate right_hash"
            ),
            difference_hash=_require_digest(
                record["difference_hash"],
                label="identity certificate difference_hash",
            ),
            outcome=outcome,
            certificate_hash=_require_digest(
                record["certificate_hash"],
                label="identity certificate certificate_hash",
            ),
        )

    @classmethod
    def from_canonical_bytes(
        cls, data: bytes
    ) -> "PolynomialIdentityRunCertificate":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="polynomial identity certificate")
        )


@dataclass(frozen=True, slots=True)
class PolynomialIdentityRun:
    input: PolynomialIdentityInput
    output: PolynomialIdentityOutput
    certificate: PolynomialIdentityRunCertificate
    protocol: str = POLYNOMIAL_IDENTITY_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != POLYNOMIAL_IDENTITY_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial identity protocol")
        if not isinstance(self.input, PolynomialIdentityInput):
            raise AssuranceHarnessError("identity run input has the wrong type")
        if not isinstance(self.output, PolynomialIdentityOutput):
            raise AssuranceHarnessError("identity run output has the wrong type")
        if not isinstance(self.certificate, PolynomialIdentityRunCertificate):
            raise AssuranceHarnessError("identity run certificate has the wrong type")

    def canonical_data(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "input": self.input.canonical_data(),
            "output": self.output.canonical_data(),
            "certificate": self.certificate.canonical_data(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def run_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "PolynomialIdentityRun":
        record = _require_exact_mapping(
            value,
            keys=frozenset({"protocol", "input", "output", "certificate"}),
            label="polynomial identity run",
        )
        if record["protocol"] != POLYNOMIAL_IDENTITY_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial identity protocol")
        return cls(
            protocol=POLYNOMIAL_IDENTITY_PROTOCOL,
            input=PolynomialIdentityInput.from_canonical_data(record["input"]),
            output=PolynomialIdentityOutput.from_canonical_data(record["output"]),
            certificate=PolynomialIdentityRunCertificate.from_canonical_data(
                record["certificate"]
            ),
        )

    @classmethod
    def from_canonical_bytes(cls, data: bytes) -> "PolynomialIdentityRun":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="polynomial identity run")
        )


def run_polynomial_identity(
    left: ExactPolynomial, right: ExactPolynomial
) -> PolynomialIdentityRun:
    """Create the fully canonical, replayable built-in identity run."""

    run_input = PolynomialIdentityInput(left=left, right=right)
    difference = left.subtract(right)
    outcome: Literal["identity_verified", "identity_failed"] = (
        "identity_verified" if not difference.terms else "identity_failed"
    )
    output = PolynomialIdentityOutput(
        input_hash=run_input.input_hash,
        difference=difference,
        outcome=outcome,
    )
    body = {
        "protocol": POLYNOMIAL_IDENTITY_PROTOCOL,
        "input_hash": run_input.input_hash,
        "output_hash": output.output_hash,
        "left_hash": left.digest,
        "right_hash": right.digest,
        "difference_hash": difference.digest,
        "outcome": outcome,
    }
    certificate = PolynomialIdentityRunCertificate(
        input_hash=run_input.input_hash,
        output_hash=output.output_hash,
        left_hash=left.digest,
        right_hash=right.digest,
        difference_hash=difference.digest,
        outcome=outcome,
        certificate_hash=object_digest(body),
    )
    return PolynomialIdentityRun(
        input=run_input, output=output, certificate=certificate
    )


def verify_polynomial_identity_run(run: PolynomialIdentityRun) -> None:
    """Recompute an embedded identity run and reject any changed field or byte."""

    if not isinstance(run, PolynomialIdentityRun):
        raise TypeError("run must be a PolynomialIdentityRun")
    expected = run_polynomial_identity(run.input.left, run.input.right)
    if run != expected:
        raise AssuranceHarnessError(
            "polynomial identity run does not reproduce exactly"
        )


@dataclass(frozen=True, slots=True)
class ExactAssignment:
    case_id: str
    values: tuple[tuple[str, Fraction], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id:
            raise AssuranceHarnessError("exact case IDs must be nonempty strings")
        variables = tuple(variable for variable, _ in self.values)
        if len(set(variables)) != len(variables) or variables != tuple(sorted(variables)):
            raise AssuranceHarnessError("exact assignments require unique sorted variables")
        if any(
            not isinstance(variable, str)
            or not variable
            or not isinstance(value, Fraction)
            for variable, value in self.values
        ):
            raise AssuranceHarnessError(
                "exact assignments require nonempty variables and Fraction values"
            )

    def as_mapping(self) -> Mapping[str, Fraction]:
        return dict(self.values)

    def canonical_data(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "values": tuple(
                {"variable": variable, "value": _rational(value)}
                for variable, value in self.values
            ),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def digest(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "ExactAssignment":
        record = _require_exact_mapping(
            value,
            keys=frozenset({"case_id", "values"}),
            label="exact assignment",
        )
        case_id = record["case_id"]
        if not isinstance(case_id, str) or not case_id:
            raise AssuranceHarnessError("exact case IDs must be nonempty strings")
        raw_values = _require_sequence(
            record["values"], label="exact assignment values"
        )
        values: list[tuple[str, Fraction]] = []
        for raw_value in raw_values:
            value_record = _require_exact_mapping(
                raw_value,
                keys=frozenset({"variable", "value"}),
                label="exact assignment value",
            )
            variable = value_record["variable"]
            if not isinstance(variable, str) or not variable:
                raise AssuranceHarnessError(
                    "exact assignments require nonempty variables"
                )
            values.append(
                (variable, _fraction_from_canonical_data(value_record["value"]))
            )
        result = cls(case_id=case_id, values=tuple(values))
        if result.canonical_data() != {
            "case_id": case_id,
            "values": tuple(
                {
                    "variable": item["variable"],
                    "value": dict(item["value"]),
                }
                for item in raw_values
            ),
        }:
            raise AssuranceHarnessError("exact assignment input is not canonical")
        return result

    @classmethod
    def from_canonical_bytes(cls, data: bytes) -> "ExactAssignment":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="exact assignment")
        )


PolynomialRelationOperator = Literal["eq", "le", "lt", "ge", "gt"]


@dataclass(frozen=True, slots=True)
class ExactPolynomialRelation:
    """One exact pointwise relation used by the finite replay protocol."""

    left: ExactPolynomial
    operator: PolynomialRelationOperator
    right: ExactPolynomial

    def __post_init__(self) -> None:
        if not isinstance(self.left, ExactPolynomial) or not isinstance(
            self.right, ExactPolynomial
        ):
            raise AssuranceHarnessError(
                "polynomial relations require ExactPolynomial operands"
            )
        if self.operator not in {"eq", "le", "lt", "ge", "gt"}:
            raise AssuranceHarnessError("unknown exact polynomial relation")

    @property
    def variables(self) -> tuple[str, ...]:
        return tuple(sorted(set(self.left.variables).union(self.right.variables)))

    def evaluate(self, assignment: Mapping[str, Fraction]) -> bool:
        left_value = self.left.evaluate(assignment)
        right_value = self.right.evaluate(assignment)
        if self.operator == "eq":
            return left_value == right_value
        if self.operator == "le":
            return left_value <= right_value
        if self.operator == "lt":
            return left_value < right_value
        if self.operator == "ge":
            return left_value >= right_value
        return left_value > right_value

    def canonical_data(self) -> dict[str, object]:
        return {
            "left": self.left.canonical_data(),
            "operator": self.operator,
            "right": self.right.canonical_data(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def relation_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "ExactPolynomialRelation":
        record = _require_exact_mapping(
            value,
            keys=frozenset({"left", "operator", "right"}),
            label="exact polynomial relation",
        )
        operator = record["operator"]
        if operator not in {"eq", "le", "lt", "ge", "gt"}:
            raise AssuranceHarnessError("unknown exact polynomial relation")
        return cls(
            left=ExactPolynomial.from_canonical_data(record["left"]),
            operator=operator,
            right=ExactPolynomial.from_canonical_data(record["right"]),
        )

    @classmethod
    def from_canonical_bytes(cls, data: bytes) -> "ExactPolynomialRelation":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="exact polynomial relation")
        )


@dataclass(frozen=True, slots=True)
class PolynomialRelationScanInput:
    relation: ExactPolynomialRelation
    domain: tuple[ExactAssignment, ...]
    code_hash: str
    protocol: str = POLYNOMIAL_RELATION_SCAN_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != POLYNOMIAL_RELATION_SCAN_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial relation scan protocol")
        if not isinstance(self.relation, ExactPolynomialRelation):
            raise AssuranceHarnessError("scan relation has the wrong type")
        _require_digest(self.code_hash, label="relation scan code_hash")
        if not self.domain:
            raise AssuranceHarnessError("relation scans require a nonempty domain")
        if any(not isinstance(case, ExactAssignment) for case in self.domain):
            raise AssuranceHarnessError(
                "relation scan domains require ExactAssignment cases"
            )
        case_ids = tuple(case.case_id for case in self.domain)
        if len(set(case_ids)) != len(case_ids):
            raise AssuranceHarnessError("relation scan case IDs must be unique")
        expected_variables = self.relation.variables
        for case in self.domain:
            actual_variables = tuple(variable for variable, _ in case.values)
            if actual_variables != expected_variables:
                raise AssuranceHarnessError(
                    "each relation-scan case must assign exactly the relation variables"
                )

    def domain_data(self) -> dict[str, object]:
        return {"cases": tuple(case.canonical_data() for case in self.domain)}

    @property
    def domain_hash(self) -> str:
        return object_digest(self.domain_data())

    def canonical_data(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "code_hash": self.code_hash,
            "relation": self.relation.canonical_data(),
            "domain": self.domain_data(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def input_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "PolynomialRelationScanInput":
        record = _require_exact_mapping(
            value,
            keys=frozenset({"protocol", "code_hash", "relation", "domain"}),
            label="polynomial relation scan input",
        )
        if record["protocol"] != POLYNOMIAL_RELATION_SCAN_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial relation scan protocol")
        domain_record = _require_exact_mapping(
            record["domain"],
            keys=frozenset({"cases"}),
            label="polynomial relation scan domain",
        )
        raw_cases = _require_sequence(
            domain_record["cases"], label="polynomial relation scan cases"
        )
        return cls(
            protocol=POLYNOMIAL_RELATION_SCAN_PROTOCOL,
            relation=ExactPolynomialRelation.from_canonical_data(
                record["relation"]
            ),
            domain=tuple(
                ExactAssignment.from_canonical_data(case) for case in raw_cases
            ),
            code_hash=_require_digest(
                record["code_hash"], label="relation scan code_hash"
            ),
        )

    @classmethod
    def from_canonical_bytes(
        cls, data: bytes
    ) -> "PolynomialRelationScanInput":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="polynomial relation scan input")
        )


@dataclass(frozen=True, slots=True)
class PolynomialRelationScanOutput:
    input_hash: str
    domain_hash: str
    relation_hash: str
    checked_count: int
    outcome: Literal["falsified", "no_counterexample_found"]
    witness: ExactAssignment | None
    protocol: str = POLYNOMIAL_RELATION_SCAN_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != POLYNOMIAL_RELATION_SCAN_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial relation scan protocol")
        for label, value in (
            ("input_hash", self.input_hash),
            ("domain_hash", self.domain_hash),
            ("relation_hash", self.relation_hash),
        ):
            _require_digest(value, label=f"relation scan output {label}")
        if (
            isinstance(self.checked_count, bool)
            or not isinstance(self.checked_count, int)
            or self.checked_count < 1
        ):
            raise AssuranceHarnessError(
                "relation scan checked_count must be a positive integer"
            )
        if self.outcome not in {"falsified", "no_counterexample_found"}:
            raise AssuranceHarnessError("unknown polynomial relation scan outcome")
        if self.outcome == "falsified" and not isinstance(
            self.witness, ExactAssignment
        ):
            raise AssuranceHarnessError("falsified relation scan requires a witness")
        if self.outcome == "no_counterexample_found" and self.witness is not None:
            raise AssuranceHarnessError(
                "non-falsified relation scan cannot carry a witness"
            )

    def canonical_data(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "input_hash": self.input_hash,
            "domain_hash": self.domain_hash,
            "relation_hash": self.relation_hash,
            "checked_count": self.checked_count,
            "outcome": self.outcome,
            "witness": (
                self.witness.canonical_data() if self.witness is not None else None
            ),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def output_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "PolynomialRelationScanOutput":
        record = _require_exact_mapping(
            value,
            keys=frozenset(
                {
                    "protocol",
                    "input_hash",
                    "domain_hash",
                    "relation_hash",
                    "checked_count",
                    "outcome",
                    "witness",
                }
            ),
            label="polynomial relation scan output",
        )
        if record["protocol"] != POLYNOMIAL_RELATION_SCAN_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial relation scan protocol")
        outcome = record["outcome"]
        if outcome not in {"falsified", "no_counterexample_found"}:
            raise AssuranceHarnessError("unknown polynomial relation scan outcome")
        witness_value = record["witness"]
        witness = (
            None
            if witness_value is None
            else ExactAssignment.from_canonical_data(witness_value)
        )
        checked_count = record["checked_count"]
        if isinstance(checked_count, bool) or not isinstance(checked_count, int):
            raise AssuranceHarnessError(
                "relation scan checked_count must be an integer"
            )
        return cls(
            protocol=POLYNOMIAL_RELATION_SCAN_PROTOCOL,
            input_hash=_require_digest(
                record["input_hash"], label="relation scan output input_hash"
            ),
            domain_hash=_require_digest(
                record["domain_hash"], label="relation scan output domain_hash"
            ),
            relation_hash=_require_digest(
                record["relation_hash"],
                label="relation scan output relation_hash",
            ),
            checked_count=checked_count,
            outcome=outcome,
            witness=witness,
        )

    @classmethod
    def from_canonical_bytes(
        cls, data: bytes
    ) -> "PolynomialRelationScanOutput":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="polynomial relation scan output")
        )


@dataclass(frozen=True, slots=True)
class PolynomialRelationScanReceipt:
    input_hash: str
    output_hash: str
    code_hash: str
    domain_hash: str
    relation_hash: str
    checked_count: int
    outcome: Literal["falsified", "no_counterexample_found"]
    witness_hash: str | None
    receipt_hash: str
    protocol: str = POLYNOMIAL_RELATION_SCAN_PROTOCOL
    evidentiary_limit: str = FINITE_RELATION_EVIDENTIARY_LIMIT

    def __post_init__(self) -> None:
        if self.protocol != POLYNOMIAL_RELATION_SCAN_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial relation scan protocol")
        for label, value in (
            ("input_hash", self.input_hash),
            ("output_hash", self.output_hash),
            ("code_hash", self.code_hash),
            ("domain_hash", self.domain_hash),
            ("relation_hash", self.relation_hash),
            ("receipt_hash", self.receipt_hash),
        ):
            _require_digest(value, label=f"relation scan receipt {label}")
        if self.witness_hash is not None:
            _require_digest(
                self.witness_hash, label="relation scan receipt witness_hash"
            )
        if (
            isinstance(self.checked_count, bool)
            or not isinstance(self.checked_count, int)
            or self.checked_count < 1
        ):
            raise AssuranceHarnessError(
                "relation scan checked_count must be a positive integer"
            )
        if self.outcome not in {"falsified", "no_counterexample_found"}:
            raise AssuranceHarnessError("unknown polynomial relation scan outcome")
        if self.outcome == "falsified" and self.witness_hash is None:
            raise AssuranceHarnessError("falsified relation scan requires a witness hash")
        if self.outcome == "no_counterexample_found" and self.witness_hash is not None:
            raise AssuranceHarnessError(
                "non-falsified relation scan cannot carry a witness hash"
            )
        if not isinstance(self.evidentiary_limit, str) or not self.evidentiary_limit:
            raise AssuranceHarnessError(
                "relation scan evidentiary limit must be nonempty"
            )
        if self.receipt_hash != object_digest(self.body_data()):
            raise AssuranceHarnessError("polynomial relation receipt body hash mismatches")

    def body_data(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "input_hash": self.input_hash,
            "output_hash": self.output_hash,
            "code_hash": self.code_hash,
            "domain_hash": self.domain_hash,
            "relation_hash": self.relation_hash,
            "checked_count": self.checked_count,
            "outcome": self.outcome,
            "witness_hash": self.witness_hash,
            "evidentiary_limit": self.evidentiary_limit,
        }

    def canonical_data(self) -> dict[str, object]:
        return {
            **self.body_data(),
            "receipt_hash": self.receipt_hash,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def artifact_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(
        cls, value: object
    ) -> "PolynomialRelationScanReceipt":
        record = _require_exact_mapping(
            value,
            keys=frozenset(
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
                }
            ),
            label="polynomial relation scan receipt",
        )
        if record["protocol"] != POLYNOMIAL_RELATION_SCAN_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial relation scan protocol")
        outcome = record["outcome"]
        if outcome not in {"falsified", "no_counterexample_found"}:
            raise AssuranceHarnessError("unknown polynomial relation scan outcome")
        checked_count = record["checked_count"]
        if isinstance(checked_count, bool) or not isinstance(checked_count, int):
            raise AssuranceHarnessError(
                "relation scan checked_count must be an integer"
            )
        witness_hash_value = record["witness_hash"]
        if witness_hash_value is not None:
            witness_hash_value = _require_digest(
                witness_hash_value,
                label="relation scan receipt witness_hash",
            )
        evidentiary_limit = record["evidentiary_limit"]
        if not isinstance(evidentiary_limit, str):
            raise AssuranceHarnessError(
                "relation scan evidentiary_limit must be a string"
            )
        return cls(
            protocol=POLYNOMIAL_RELATION_SCAN_PROTOCOL,
            input_hash=_require_digest(
                record["input_hash"], label="relation scan receipt input_hash"
            ),
            output_hash=_require_digest(
                record["output_hash"], label="relation scan receipt output_hash"
            ),
            code_hash=_require_digest(
                record["code_hash"], label="relation scan receipt code_hash"
            ),
            domain_hash=_require_digest(
                record["domain_hash"], label="relation scan receipt domain_hash"
            ),
            relation_hash=_require_digest(
                record["relation_hash"],
                label="relation scan receipt relation_hash",
            ),
            checked_count=checked_count,
            outcome=outcome,
            witness_hash=witness_hash_value,
            receipt_hash=_require_digest(
                record["receipt_hash"], label="relation scan receipt receipt_hash"
            ),
            evidentiary_limit=evidentiary_limit,
        )

    @classmethod
    def from_canonical_bytes(
        cls, data: bytes
    ) -> "PolynomialRelationScanReceipt":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="polynomial relation scan receipt")
        )


@dataclass(frozen=True, slots=True)
class PolynomialRelationScanRun:
    input: PolynomialRelationScanInput
    output: PolynomialRelationScanOutput
    receipt: PolynomialRelationScanReceipt
    protocol: str = POLYNOMIAL_RELATION_SCAN_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != POLYNOMIAL_RELATION_SCAN_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial relation scan protocol")
        if not isinstance(self.input, PolynomialRelationScanInput):
            raise AssuranceHarnessError("relation scan run input has the wrong type")
        if not isinstance(self.output, PolynomialRelationScanOutput):
            raise AssuranceHarnessError("relation scan run output has the wrong type")
        if not isinstance(self.receipt, PolynomialRelationScanReceipt):
            raise AssuranceHarnessError("relation scan run receipt has the wrong type")

    def canonical_data(self) -> dict[str, object]:
        return {
            "protocol": self.protocol,
            "input": self.input.canonical_data(),
            "output": self.output.canonical_data(),
            "receipt": self.receipt.canonical_data(),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.canonical_data())

    @property
    def run_hash(self) -> str:
        return object_digest(self.canonical_data())

    @classmethod
    def from_canonical_data(cls, value: object) -> "PolynomialRelationScanRun":
        record = _require_exact_mapping(
            value,
            keys=frozenset({"protocol", "input", "output", "receipt"}),
            label="polynomial relation scan run",
        )
        if record["protocol"] != POLYNOMIAL_RELATION_SCAN_PROTOCOL:
            raise AssuranceHarnessError("unknown polynomial relation scan protocol")
        return cls(
            protocol=POLYNOMIAL_RELATION_SCAN_PROTOCOL,
            input=PolynomialRelationScanInput.from_canonical_data(record["input"]),
            output=PolynomialRelationScanOutput.from_canonical_data(
                record["output"]
            ),
            receipt=PolynomialRelationScanReceipt.from_canonical_data(
                record["receipt"]
            ),
        )

    @classmethod
    def from_canonical_bytes(cls, data: bytes) -> "PolynomialRelationScanRun":
        return cls.from_canonical_data(
            _canonical_json_value(data, label="polynomial relation scan run")
        )


def run_exact_polynomial_relation_scan(
    relation: ExactPolynomialRelation,
    cases: Iterable[ExactAssignment],
    *,
    code_hash: str,
) -> PolynomialRelationScanRun:
    """Run the built-in finite exact relation predicate over a sealed domain."""

    run_input = PolynomialRelationScanInput(
        relation=relation,
        domain=tuple(cases),
        code_hash=code_hash,
    )
    witness: ExactAssignment | None = None
    checked_count = 0
    for case in run_input.domain:
        checked_count += 1
        if not relation.evaluate(case.as_mapping()):
            witness = case
            break
    outcome: Literal["falsified", "no_counterexample_found"] = (
        "falsified" if witness is not None else "no_counterexample_found"
    )
    output = PolynomialRelationScanOutput(
        input_hash=run_input.input_hash,
        domain_hash=run_input.domain_hash,
        relation_hash=relation.relation_hash,
        checked_count=checked_count,
        outcome=outcome,
        witness=witness,
    )
    witness_hash = witness.digest if witness is not None else None
    receipt_body = {
        "protocol": POLYNOMIAL_RELATION_SCAN_PROTOCOL,
        "input_hash": run_input.input_hash,
        "output_hash": output.output_hash,
        "code_hash": code_hash,
        "domain_hash": run_input.domain_hash,
        "relation_hash": relation.relation_hash,
        "checked_count": checked_count,
        "outcome": outcome,
        "witness_hash": witness_hash,
        "evidentiary_limit": FINITE_RELATION_EVIDENTIARY_LIMIT,
    }
    receipt = PolynomialRelationScanReceipt(
        input_hash=run_input.input_hash,
        output_hash=output.output_hash,
        code_hash=code_hash,
        domain_hash=run_input.domain_hash,
        relation_hash=relation.relation_hash,
        checked_count=checked_count,
        outcome=outcome,
        witness_hash=witness_hash,
        receipt_hash=object_digest(receipt_body),
    )
    return PolynomialRelationScanRun(
        input=run_input, output=output, receipt=receipt
    )


def verify_exact_polynomial_relation_scan(
    run: PolynomialRelationScanRun, *, expected_code_hash: str
) -> None:
    """Re-run a finite relation scan using a caller-pinned code digest."""

    if not isinstance(run, PolynomialRelationScanRun):
        raise TypeError("run must be a PolynomialRelationScanRun")
    expected_code_hash = _require_digest(
        expected_code_hash, label="expected relation scan code_hash"
    )
    if (
        run.input.code_hash != expected_code_hash
        or run.receipt.code_hash != expected_code_hash
    ):
        raise AssuranceHarnessError(
            "polynomial relation scan code hash differs from caller expectation"
        )
    expected = run_exact_polynomial_relation_scan(
        run.input.relation,
        run.input.domain,
        code_hash=expected_code_hash,
    )
    if run != expected:
        raise AssuranceHarnessError(
            "polynomial relation scan does not reproduce exactly"
        )


@dataclass(frozen=True, slots=True)
class CounterexampleScanReceipt:
    code_hash: str
    domain_hash: str
    checked_count: int
    outcome: str
    witness: ExactAssignment | None
    receipt_hash: str
    evidentiary_limit: str = (
        "No witness in a finite domain is corroboration, not proof of a universal claim."
    )


def scan_exact_domain(
    cases: Iterable[ExactAssignment],
    predicate: Callable[[Mapping[str, Fraction]], bool],
    *,
    code_hash: str,
) -> CounterexampleScanReceipt:
    """Search a finite exact domain and preserve the first falsifying witness."""

    if not callable(predicate):
        raise TypeError("predicate must be callable")
    if not isinstance(code_hash, str) or _DIGEST.fullmatch(code_hash) is None:
        raise AssuranceHarnessError("code_hash must be one lowercase sha256 digest")
    ordered = tuple(cases)
    if not ordered:
        raise AssuranceHarnessError("counterexample scans require a nonempty domain")
    case_ids = tuple(case.case_id for case in ordered)
    if len(set(case_ids)) != len(case_ids):
        raise AssuranceHarnessError("counterexample case IDs must be unique")
    domain_hash = object_digest(
        {"cases": tuple(case.canonical_data() for case in ordered)}
    )
    witness: ExactAssignment | None = None
    checked_count = 0
    for case in ordered:
        checked_count += 1
        result = predicate(case.as_mapping())
        if not isinstance(result, bool):
            raise AssuranceHarnessError("counterexample predicates must return bool")
        if not result:
            witness = case
            break
    outcome = "falsified" if witness is not None else "no_counterexample_found"
    receipt_data = {
        "harness": "exact_counterexample_scan.v1",
        "code_hash": code_hash,
        "domain_hash": domain_hash,
        "checked_count": checked_count,
        "outcome": outcome,
        "witness": witness.canonical_data() if witness is not None else None,
    }
    return CounterexampleScanReceipt(
        code_hash=code_hash,
        domain_hash=domain_hash,
        checked_count=checked_count,
        outcome=outcome,
        witness=witness,
        receipt_hash=object_digest(receipt_data),
    )


def verify_counterexample_scan_receipt(
    cases: Iterable[ExactAssignment],
    predicate: Callable[[Mapping[str, Fraction]], bool],
    receipt: CounterexampleScanReceipt,
    *,
    expected_code_hash: str | None = None,
) -> None:
    """Re-run one legacy finite scan and reject changed input or output.

    Existing callers may omit ``expected_code_hash`` for compatibility.  New
    canonical-state integrations must provide it, or use
    :func:`verify_exact_polynomial_relation_scan`, so the receipt never defines
    its own trust root.
    """

    if not isinstance(receipt, CounterexampleScanReceipt):
        raise TypeError("receipt must be a CounterexampleScanReceipt")
    pinned_code_hash = (
        receipt.code_hash
        if expected_code_hash is None
        else _require_digest(
            expected_code_hash, label="expected counterexample code_hash"
        )
    )
    if receipt.code_hash != pinned_code_hash:
        raise AssuranceHarnessError(
            "counterexample receipt code hash differs from caller expectation"
        )
    expected = scan_exact_domain(cases, predicate, code_hash=pinned_code_hash)
    if receipt != expected:
        raise AssuranceHarnessError(
            "counterexample scan receipt does not reproduce exactly"
        )


__all__ = [
    "AssuranceHarnessError",
    "CounterexampleScanReceipt",
    "ExactAssignment",
    "ExactPolynomial",
    "ExactPolynomialRelation",
    "FINITE_RELATION_EVIDENTIARY_LIMIT",
    "POLYNOMIAL_IDENTITY_PROTOCOL",
    "POLYNOMIAL_RELATION_SCAN_PROTOCOL",
    "PolynomialTerm",
    "PolynomialIdentityInput",
    "PolynomialIdentityOutput",
    "PolynomialIdentityRun",
    "PolynomialIdentityRunCertificate",
    "PolynomialRelationOperator",
    "PolynomialRelationScanInput",
    "PolynomialRelationScanOutput",
    "PolynomialRelationScanReceipt",
    "PolynomialRelationScanRun",
    "SymbolicIdentityCertificate",
    "check_polynomial_identity",
    "run_exact_polynomial_relation_scan",
    "run_polynomial_identity",
    "scan_exact_domain",
    "verify_counterexample_scan_receipt",
    "verify_exact_polynomial_relation_scan",
    "verify_polynomial_identity_certificate",
    "verify_polynomial_identity_run",
]
