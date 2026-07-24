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

_EXPECTED_MOVE_ROUTES = {
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
    """Apply the exact first-batch isolation and source-audit policy."""

    corpus = _revalidate(corpus)
    moves = {move.move_id: move for move in corpus.moves}
    if set(moves) != set(_EXPECTED_MOVE_ROUTES):
        raise ResearchCraftPolicyError(
            "the first disabled research-craft release must contain exactly "
            "the researcher-approved three-move batch"
        )
    for move_id, expected_routes in _EXPECTED_MOVE_ROUTES.items():
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
    if corpus.source_audit_report_path != (
        "review_outputs/phase5b_research_move_source_audit_v1.md"
    ):
        raise ResearchCraftPolicyError(
            "research-craft release must bind the approved source-audit report"
        )
    if object_digest(corpus) != RESEARCH_CORPUS_V1_HASH:
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
    if expected_hash != RESEARCH_CORPUS_V1_HASH:
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
    "ResearchCraftPolicyError",
    "load_research_corpus",
]
