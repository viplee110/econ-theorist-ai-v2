"""Deterministic oracles for Phase 2 development and blind benchmarks.

Gold cases are evaluation resources, never scientific authority.  The oracle
uses exact rational arithmetic and reads only the evaluator compartment of a
case manifest after the generator output has been frozen.
"""

from __future__ import annotations

import json
import math
from copy import deepcopy
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping

from .codec import ensure_canonical_data
from .errors import CanonicalEncodingError


ATTENTION_CASE_SCHEMA = "econ-theorist/gold-case/attention-precision/v1"
GENERATOR_BRIEF_KEYS = frozenset(
    {
        "question",
        "state_space",
        "prior",
        "precision_domain",
        "signal_accuracy",
        "attention_choice",
        "processing_cost",
        "action_rule",
        "no_attention_accuracy",
        "tie_rule",
        "outcome",
        "task",
        "allowed_tools",
    }
)
EVALUATOR_ONLY_KEYS = frozenset(
    {
        "answer_key",
        "authors",
        "gold_examples",
        "gold_vap",
        "headline_proposition",
        "hidden_probes",
        "holdout_seed",
        "inverse_transform",
        "paper_title",
        "proof",
    }
)
REQUIRED_EXAMPLE_ROLES = frozenset(
    {
        "benchmark",
        "mechanism_on",
        "constant_cost_ablation",
        "rival_separator",
        "lower_boundary",
        "upper_boundary",
        "beyond_boundary",
    }
)


class GoldCaseError(ValueError):
    """A gold manifest or declared answer disagrees with the exact oracle."""


def rational(value: object) -> Fraction:
    """Parse one reduced, positive-denominator canonical rational object."""

    if not isinstance(value, Mapping) or set(value) != {"numerator", "denominator"}:
        raise GoldCaseError("a rational must contain exactly numerator and denominator")
    numerator = value["numerator"]
    denominator = value["denominator"]
    if (
        isinstance(numerator, bool)
        or isinstance(denominator, bool)
        or not isinstance(numerator, int)
        or not isinstance(denominator, int)
    ):
        raise GoldCaseError("rational numerator and denominator must be strict integers")
    if denominator <= 0:
        raise GoldCaseError("a rational denominator must be positive")
    if math.gcd(abs(numerator), denominator) != 1:
        raise GoldCaseError("a rational must be in lowest terms")
    return Fraction(numerator, denominator)


def rational_json(value: Fraction) -> dict[str, int]:
    """Return the unique JSON representation of a ``Fraction``."""

    return {"numerator": value.numerator, "denominator": value.denominator}


def processing_surplus(
    precision: Fraction,
    kappa: Fraction,
    *,
    constant_cost: Fraction | None = None,
) -> Fraction:
    if precision <= 0 or precision > 1:
        raise GoldCaseError("precision must lie in (0,1]")
    if kappa < 0:
        raise GoldCaseError("kappa must be nonnegative")
    cost = kappa * precision * precision if constant_cost is None else constant_cost
    if cost < 0:
        raise GoldCaseError("processing cost must be nonnegative")
    return precision / 2 - cost


def chooses_attention(surplus: Fraction, *, tie_rule: str) -> bool:
    if tie_rule == "process":
        return surplus >= 0
    if tie_rule == "do_not_process":
        return surplus > 0
    raise GoldCaseError("unknown attention tie rule")


def realized_accuracy(precision: Fraction, attention: bool) -> Fraction:
    return Fraction(1, 2) + (precision / 2 if attention else 0)


def evaluate_binary_attention(
    *,
    ell: Fraction,
    h: Fraction,
    kappa: Fraction,
    tie_rule: str = "process",
    constant_cost: Fraction | None = None,
) -> dict[str, object]:
    """Evaluate the exact two-policy indivisible-attention model."""

    if not (0 < ell < h <= 1):
        raise GoldCaseError("the fixture requires 0 < ell < h <= 1")
    delta_ell = processing_surplus(ell, kappa, constant_cost=constant_cost)
    delta_h = processing_surplus(h, kappa, constant_cost=constant_cost)
    d_ell = chooses_attention(delta_ell, tie_rule=tie_rule)
    d_h = chooses_attention(delta_h, tie_rule=tie_rule)
    y_ell = realized_accuracy(ell, d_ell)
    y_h = realized_accuracy(h, d_h)
    ordering = "ell_gt_h" if y_ell > y_h else "h_gt_ell" if y_h > y_ell else "equal"
    return {
        "delta_ell": delta_ell,
        "delta_h": delta_h,
        "d_ell": d_ell,
        "d_h": d_h,
        "y_ell": y_ell,
        "y_h": y_h,
        "ordering": ordering,
    }


def reversal_predicted(
    *, ell: Fraction, h: Fraction, kappa: Fraction, tie_rule: str = "process"
) -> bool:
    result = evaluate_binary_attention(
        ell=ell, h=h, kappa=kappa, tie_rule=tie_rule
    )
    return result["ordering"] == "ell_gt_h"


def continuous_attention(
    *, precision: Fraction, kappa: Fraction
) -> tuple[Fraction, Fraction]:
    """Return optimal continuous attention and realized accuracy exactly."""

    if precision <= 0 or precision > 1:
        raise GoldCaseError("precision must lie in (0,1]")
    if kappa < 0:
        raise GoldCaseError("kappa must be nonnegative")
    effort = Fraction(1) if kappa == 0 else min(Fraction(1), 1 / (2 * kappa * precision))
    accuracy = Fraction(1, 2) + effort * precision / 2
    return effort, accuracy


def _assert_expected_rational(
    expected: Mapping[str, object], key: str, actual: Fraction
) -> None:
    if key not in expected or rational(expected[key]) != actual:
        raise GoldCaseError(f"declared {key} disagrees with the exact oracle")


def _assert_expected_case(case: Mapping[str, object]) -> set[str]:
    required = {"case_id", "roles", "ell", "h", "kappa", "tie_rule", "expected"}
    optional = {"constant_cost", "rival_fixed_attention"}
    if not required.issubset(case) or not set(case).issubset(required | optional):
        raise GoldCaseError("example case has missing or unknown fields")
    roles = case["roles"]
    if not isinstance(roles, list) or not roles or any(not isinstance(x, str) for x in roles):
        raise GoldCaseError("example roles must be a nonempty string list")
    ell = rational(case["ell"])
    h = rational(case["h"])
    kappa = rational(case["kappa"])
    constant_cost = (
        rational(case["constant_cost"]) if "constant_cost" in case else None
    )
    tie_rule = case["tie_rule"]
    if not isinstance(tie_rule, str):
        raise GoldCaseError("tie_rule must be a string")
    actual = evaluate_binary_attention(
        ell=ell,
        h=h,
        kappa=kappa,
        tie_rule=tie_rule,
        constant_cost=constant_cost,
    )
    expected = case["expected"]
    if not isinstance(expected, Mapping):
        raise GoldCaseError("example expected value must be one object")
    for key in ("delta_ell", "delta_h", "y_ell", "y_h"):
        _assert_expected_rational(expected, key, actual[key])  # type: ignore[arg-type]
    for key in ("d_ell", "d_h"):
        if expected.get(key) is not actual[key]:
            raise GoldCaseError(f"declared {key} disagrees with the exact oracle")
    if expected.get("ordering") != actual["ordering"]:
        raise GoldCaseError("declared ordering disagrees with the exact oracle")
    rival = case.get("rival_fixed_attention")
    if rival is not None:
        if not isinstance(rival, Mapping):
            raise GoldCaseError("rival_fixed_attention must be one object")
        _assert_expected_rational(rival, "y_ell", Fraction(1, 2) + ell / 2)
        _assert_expected_rational(rival, "y_h", Fraction(1, 2) + h / 2)
        if rival.get("ordering") != "h_gt_ell":
            raise GoldCaseError("fixed-attention rival must rank h above ell")
    return set(roles)


def _validate_generator_isolation(generator: object) -> None:
    if not isinstance(generator, Mapping) or set(generator) != {"pre_result_brief"}:
        raise GoldCaseError("generator compartment must contain only pre_result_brief")
    brief = generator["pre_result_brief"]
    if not isinstance(brief, Mapping) or set(brief) != GENERATOR_BRIEF_KEYS:
        raise GoldCaseError("pre_result_brief has missing or evaluator-only fields")
    pending: list[object] = [brief]
    while pending:
        value = pending.pop()
        if isinstance(value, Mapping):
            leaked = EVALUATOR_ONLY_KEYS.intersection(value)
            if leaked:
                raise GoldCaseError(
                    "generator compartment leaks evaluator fields: "
                    + ", ".join(sorted(leaked))
                )
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)


def validate_attention_fixture(payload: object) -> Mapping[str, object]:
    """Validate a complete fixture and return an immutable-useful summary."""

    try:
        normalized = ensure_canonical_data(payload)
    except CanonicalEncodingError as exc:
        raise GoldCaseError("gold case violates canonical JSON rules") from exc
    if not isinstance(normalized, dict):
        raise GoldCaseError("gold case must be one JSON object")
    if set(normalized) != {"schema", "case_id", "split", "generator", "evaluator"}:
        raise GoldCaseError("gold case has missing or unknown top-level fields")
    if normalized["schema"] != ATTENTION_CASE_SCHEMA:
        raise GoldCaseError("unknown gold case schema")
    if normalized["split"] not in {"development", "pilot", "confirmatory_holdout"}:
        raise GoldCaseError("unknown evaluation split")
    _validate_generator_isolation(normalized["generator"])

    evaluator = normalized["evaluator"]
    if not isinstance(evaluator, Mapping):
        raise GoldCaseError("evaluator compartment must be one object")
    expected_evaluator_fields = {
        "headline_proposition",
        "proof_obligations",
        "gold_examples",
        "continuous_attention",
        "hidden_probes",
        "absorption_decoy",
        "prohibited_overclaims",
        "gate_expectations",
        "semantic_signature",
    }
    if set(evaluator) != expected_evaluator_fields:
        raise GoldCaseError("evaluator compartment has missing or unknown fields")

    examples = evaluator["gold_examples"]
    if not isinstance(examples, list) or len(examples) < 7:
        raise GoldCaseError("gold case requires the full transparent example suite")
    case_ids: set[str] = set()
    roles: set[str] = set()
    for case in examples:
        if not isinstance(case, Mapping):
            raise GoldCaseError("every gold example must be one object")
        case_id = case.get("case_id")
        if not isinstance(case_id, str) or not case_id or case_id in case_ids:
            raise GoldCaseError("gold example IDs must be nonempty and unique")
        case_ids.add(case_id)
        roles.update(_assert_expected_case(case))
    if not REQUIRED_EXAMPLE_ROLES.issubset(roles):
        raise GoldCaseError("gold examples do not cover every required function")

    continuous = evaluator["continuous_attention"]
    if not isinstance(continuous, Mapping) or set(continuous) != {
        "ell",
        "h",
        "kappa",
        "expected",
    }:
        raise GoldCaseError("continuous-attention oracle has the wrong shape")
    ell = rational(continuous["ell"])
    h = rational(continuous["h"])
    kappa = rational(continuous["kappa"])
    e_ell, y_ell = continuous_attention(precision=ell, kappa=kappa)
    e_h, y_h = continuous_attention(precision=h, kappa=kappa)
    expected = continuous["expected"]
    if not isinstance(expected, Mapping):
        raise GoldCaseError("continuous expected answer must be one object")
    for key, actual in (
        ("e_ell", e_ell),
        ("e_h", e_h),
        ("y_ell", y_ell),
        ("y_h", y_h),
    ):
        _assert_expected_rational(expected, key, actual)
    if expected.get("ordering") != (
        "h_gt_ell" if y_h > y_ell else "equal" if y_h == y_ell else "ell_gt_h"
    ):
        raise GoldCaseError("continuous-attention ordering is incorrect")

    probes = evaluator["hidden_probes"]
    if not isinstance(probes, list) or not probes:
        raise GoldCaseError("at least one hidden boundary probe is required")
    for probe in probes:
        if not isinstance(probe, Mapping) or set(probe) != {
            "probe_id",
            "ell",
            "h",
            "kappa",
            "tie_rule",
            "expected_ordering",
        }:
            raise GoldCaseError("hidden probe has the wrong shape")
        actual = evaluate_binary_attention(
            ell=rational(probe["ell"]),
            h=rational(probe["h"]),
            kappa=rational(probe["kappa"]),
            tie_rule=probe["tie_rule"],  # type: ignore[arg-type]
        )
        if actual["ordering"] != probe["expected_ordering"]:
            raise GoldCaseError("hidden boundary probe answer is incorrect")

    absorption = evaluator["absorption_decoy"]
    if not isinstance(absorption, Mapping) or set(absorption) != {
        "comparator_id",
        "classification",
        "first_mapping_failure",
        "translation",
        "expected_effects",
    }:
        raise GoldCaseError("absorption decoy has the wrong shape")
    if (
        absorption["classification"] != "direct_corollary"
        or absorption["first_mapping_failure"] is not None
    ):
        raise GoldCaseError("the decoy must be a mapping-complete direct corollary")
    translation = absorption["translation"]
    expected_translation = {
        "adopter": "receiver",
        "project": "signal_policy",
        "adoption": "processing_attention",
        "benefit": "x_over_2",
        "cost": "kappa_x_squared",
        "output_gain": "x_over_2",
        "baseline_output": "one_half",
    }
    if translation != expected_translation:
        raise GoldCaseError("absorption translation omits or changes an exact mapping")
    effects = absorption["expected_effects"]
    required_effects = {
        "formal_validity_preserved",
        "mechanism_validity_preserved",
        "novelty_absorbed",
        "g5_denied_or_reopened",
        "package_stale",
    }
    if not isinstance(effects, list) or set(effects) != required_effects:
        raise GoldCaseError("absorption expected effects are incomplete")

    prohibited = evaluator["prohibited_overclaims"]
    if not isinstance(prohibited, list) or len(prohibited) < 5:
        raise GoldCaseError("fixture must name its prohibited overclaims")
    if any(not isinstance(item, str) or not item for item in prohibited):
        raise GoldCaseError("prohibited overclaims must be nonempty strings")

    return {
        "case_id": normalized["case_id"],
        "split": normalized["split"],
        "case_ids": tuple(sorted(case_ids)),
        "roles": tuple(sorted(roles)),
        "absorption": "absorbed",
        "publication_eligible": False,
    }


def load_attention_fixture(path: str | Path) -> Mapping[str, object]:
    """Read canonical UTF-8 JSON and validate the Phase 2 attention fixture."""

    try:
        data = Path(path).read_bytes()
        payload = json.loads(data.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GoldCaseError("cannot read canonical attention fixture") from exc
    return validate_attention_fixture(payload)


def mutated_fixture(payload: Mapping[str, object]) -> dict[str, object]:
    """Return a deep copy for negative tests without mutating a shared oracle."""

    return deepcopy(dict(payload))


__all__ = [
    "ATTENTION_CASE_SCHEMA",
    "GoldCaseError",
    "continuous_attention",
    "evaluate_binary_attention",
    "load_attention_fixture",
    "mutated_fixture",
    "processing_surplus",
    "rational",
    "rational_json",
    "realized_accuracy",
    "reversal_predicted",
    "validate_attention_fixture",
]
