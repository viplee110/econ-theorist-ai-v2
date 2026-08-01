"""Explicit-path policy for the disabled ResearchMove development corpus.

Nothing in this module discovers an installed resource, retrieves or selects a
move, projects a runtime menu, mutates canonical state, or authorizes a pilot.
Callers must provide the exact development file and fixed release digest.
"""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import ValidationError

from .codec import canonical_json_bytes, object_digest, sha256_digest
from .research_craft import (
    ResearchCorpusRelease,
)


RESEARCH_CORPUS_V1_HASH = (
    "8e62369302e850aa5b6bb439941da08f41edcc80f453a36f3b3d66220abbfe17"
)
RESEARCH_CORPUS_V2_HASH = (
    "ff373babf44100d666f666ad77310d4730ed43179ad094c6ac6961f8f24808ce"
)
RESEARCH_CORPUS_V3_HASH = (
    "74facfbd0a689fd99ff44b11bd0eaebef3d29a7ec5934098bda481131c4c444e"
)
RESEARCH_CORPUS_V4_HASH = (
    "507ca179b7941b737d59a888fbd61453b5aa72ddb415ddf4f47bc43bc74be46f"
)

_EXPECTED_MOVE_ROUTES_V1 = {
    "research.move.computational_structure_probe": {
        "lab.micro_examples_and_ablations",
        "discover.claims_and_boundaries",
    },
    "research.move.representation_hunter": {
        "tournament.mechanisms",
        "tournament.implementations",
    },
    "research.move.analogical_structure_transfer": {
        "tournament.mechanisms",
        "audit.assumptions_generality_and_absorption",
    },
}
_EXPECTED_MOVE_ROUTES_V2 = {
    **_EXPECTED_MOVE_ROUTES_V1,
    "research.move.market_operation_primitive": {
        "frame.question_and_benchmarks",
        "decompose.primitives",
    },
    "research.move.different_implementation_question": {
        "frame.question_and_benchmarks",
        "tournament.mechanisms",
    },
    "research.move.ground_up_constraint_rebuild": {
        "frame.question_and_benchmarks",
        "decompose.primitives",
    },
}
_EXPECTED_MOVE_ROUTES_V3 = {
    **_EXPECTED_MOVE_ROUTES_V2,
    "research.move.institutional_feedback_deepener": {
        "decompose.primitives",
        "tournament.mechanisms",
    },
    "research.move.robustness_axis_switch": {
        "discover.claims_and_boundaries",
        "audit.assumptions_generality_and_absorption",
    },
    "research.move.incentive_implementation_stress_test": {
        "tournament.mechanisms",
        "tournament.implementations",
    },
}
_EXPECTED_MOVE_ROUTES_V4 = {
    **_EXPECTED_MOVE_ROUTES_V3,
    "research.move.question_reframer": {
        "frame.question_and_benchmarks",
        "audit.assumptions_generality_and_absorption",
    },
    "research.move.near_optimal_structure_pivot": {
        "tournament.implementations",
        "audit.assumptions_generality_and_absorption",
    },
}

_RELEASE_POLICIES = {
    "research.corpus.first_batch.v1": {
        "hash": RESEARCH_CORPUS_V1_HASH,
        "moves": _EXPECTED_MOVE_ROUTES_V1,
        "report": "review_outputs/phase5b_research_move_source_audit_v1.md",
    },
    "research.corpus.discovery_distillation.v2": {
        "hash": RESEARCH_CORPUS_V2_HASH,
        "moves": _EXPECTED_MOVE_ROUTES_V2,
        "report": (
            "review_outputs/"
            "phase5b_research_move_discovery_distillation_source_audit_v2.md"
        ),
    },
    "research.corpus.scholar_method_chain.v3": {
        "hash": RESEARCH_CORPUS_V3_HASH,
        "moves": _EXPECTED_MOVE_ROUTES_V3,
        "report": (
            "review_outputs/"
            "phase5b_research_move_scholar_method_chain_source_audit_v3.md"
        ),
    },
    "research.corpus.contribution_structure.v4": {
        "hash": RESEARCH_CORPUS_V4_HASH,
        "moves": _EXPECTED_MOVE_ROUTES_V4,
        "report": (
            "review_outputs/"
            "phase5b_research_move_contribution_structure_source_audit_v4.md"
        ),
    },
}


class ResearchCraftPolicyError(ValueError):
    """A disabled research-craft resource violates its development policy."""


def _revalidate(corpus: ResearchCorpusRelease) -> ResearchCorpusRelease:
    """Re-run strict validators even after unsafe ``model_copy`` updates."""

    try:
        value = ResearchCorpusRelease.model_validate_json(
            canonical_json_bytes(corpus),
            strict=True,
        )
    except (TypeError, ValueError, ValidationError) as exc:
        raise ResearchCraftPolicyError(
            "invalid disabled research-craft corpus"
        ) from exc
    if value != corpus:
        raise ResearchCraftPolicyError(
            "research-craft corpus changed during strict revalidation"
        )
    return value


def _validate_research_corpus_policy(
    corpus: ResearchCorpusRelease,
) -> ResearchCorpusRelease:
    """Apply one exact disabled-release isolation and source-audit policy."""

    corpus = _revalidate(corpus)
    release_policy = _RELEASE_POLICIES.get(corpus.release_id)
    if release_policy is None:
        raise ResearchCraftPolicyError(
            "research-craft policy does not recognize this disabled release"
        )
    expected_moves = release_policy["moves"]
    assert isinstance(expected_moves, dict)
    moves = {move.move_id: move for move in corpus.moves}
    if set(moves) != set(expected_moves):
        raise ResearchCraftPolicyError(
            "the disabled research-craft release does not contain its exact "
            "researcher-approved move batch"
        )
    for move_id, expected_routes in expected_moves.items():
        move = moves[move_id]
        if set(move.compatible_route_ids) != expected_routes:
            raise ResearchCraftPolicyError(
                f"research move route compatibility changed: {move_id}"
            )
    analogical = moves["research.move.analogical_structure_transfer"]
    if analogical.variant_id != "first_mapping_failure":
        raise ResearchCraftPolicyError(
            "the analogical move must retain the approved first-mapping-failure variant"
        )
    if not any(
        binding.use_role == "skeptical_contrast"
        for binding in analogical.evidence_bindings
    ):
        raise ResearchCraftPolicyError(
            "the analogical move must retain its skeptical contrast"
        )
    expected_report = release_policy["report"]
    assert isinstance(expected_report, str)
    if corpus.source_audit_report_path != expected_report:
        raise ResearchCraftPolicyError(
            "research-craft release must bind the approved source-audit report"
        )
    expected_release_hash = release_policy["hash"]
    assert isinstance(expected_release_hash, str)
    if object_digest(corpus) != expected_release_hash:
        raise ResearchCraftPolicyError(
            "research-craft policy requires the exact fixed development release"
        )
    return corpus


def load_research_corpus(
    path: Path,
    *,
    expected_hash: str,
) -> ResearchCorpusRelease:
    """Load one exact checkout-only development corpus.

    The path and digest are mandatory.  Relative paths, installed-resource
    fallback, caching, and implicit defaults are intentionally unsupported.
    """

    if not isinstance(path, Path):
        raise TypeError("research corpus path must be a pathlib.Path")
    if not path.is_absolute():
        raise ResearchCraftPolicyError(
            "disabled research corpus requires one explicit absolute path"
        )
    if not isinstance(expected_hash, str) or re.fullmatch(
        r"[0-9a-f]{64}", expected_hash
    ) is None:
        raise ResearchCraftPolicyError("research corpus expected hash is invalid")
    if expected_hash not in {
        RESEARCH_CORPUS_V1_HASH,
        RESEARCH_CORPUS_V2_HASH,
        RESEARCH_CORPUS_V3_HASH,
        RESEARCH_CORPUS_V4_HASH,
    }:
        raise ResearchCraftPolicyError(
            "research corpus expected hash is not the fixed development release"
        )
    try:
        data = path.read_bytes()
        corpus = ResearchCorpusRelease.model_validate_json(data, strict=True)
    except (OSError, ValueError, ValidationError) as exc:
        raise ResearchCraftPolicyError(
            f"cannot load disabled research corpus: {path}"
        ) from exc
    if canonical_json_bytes(corpus) != data:
        raise ResearchCraftPolicyError(
            "disabled research corpus is not exact canonical JSON"
        )
    if (
        sha256_digest(data) != expected_hash
        or object_digest(corpus) != expected_hash
    ):
        raise ResearchCraftPolicyError("disabled research corpus hash mismatch")
    corpus = _validate_research_corpus_policy(corpus)

    repository_root = path.parent.parent.resolve()
    report = (repository_root / corpus.source_audit_report_path).resolve()
    if not report.is_relative_to(repository_root):
        raise ResearchCraftPolicyError("source-audit report escapes the checkout")
    try:
        report_digest = sha256_digest(report.read_bytes())
    except OSError as exc:
        raise ResearchCraftPolicyError(
            "disabled research corpus source-audit report is missing"
        ) from exc
    if report_digest != corpus.source_audit_report_sha256:
        raise ResearchCraftPolicyError(
            "disabled research corpus source-audit report hash mismatch"
        )
    return corpus


__all__ = [
    "RESEARCH_CORPUS_V1_HASH",
    "RESEARCH_CORPUS_V2_HASH",
    "RESEARCH_CORPUS_V3_HASH",
    "RESEARCH_CORPUS_V4_HASH",
    "ResearchCraftPolicyError",
    "load_research_corpus",
]
