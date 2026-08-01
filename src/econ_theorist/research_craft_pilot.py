"""Checkout-only, default-closed ResearchMove pilot projection.

This module is deliberately independent of machine navigation and canonical
state.  A caller must provide the absolute path to the exact V4 development
corpus.  The returned model-visible view contains only function-level method
cards; source and release provenance is kept in a separate bounded record.

Importing this module performs no file-system access.  Constructing a pilot
material object reads but never writes the explicitly supplied checkout.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal, TypeAlias

from pydantic import Field, model_validator

from .codec import canonical_json_bytes, sha256_digest
from .models import Digest, NonEmptyString, StableId, StrictModel
from .research_craft_policy import (
    RESEARCH_CORPUS_V4_HASH,
    ResearchCraftPolicyError,
    load_research_corpus,
)


PilotRouteId: TypeAlias = Literal[
    "frame.question_and_benchmarks",
]

MARKET_OPERATION_MOVE_ID = "research.move.market_operation_primitive"
QUESTION_REFRAMER_MOVE_ID = "research.move.question_reframer"

_ROUTE_MOVE_IDS: dict[str, tuple[str, str]] = {
    "frame.question_and_benchmarks": (
        MARKET_OPERATION_MOVE_ID,
        QUESTION_REFRAMER_MOVE_ID,
    ),
}

_NON_AUTHORITATIVE_NOTICE = (
    "Optional, non-authoritative research-method candidates for revising an "
    "existing question-and-benchmark frame after a revise-framing diagnosis, "
    "not for creating a fresh frame. Being offered does not establish "
    "applicability. Use zero, one, or two only when useful, and using none is "
    "valid. Give one short missing-input or non-applicability reason for each "
    "unused method. They cannot choose a route, establish novelty or "
    "importance, write canonical state, or replace a human decision."
)


class ResearchMovePilotError(ValueError):
    """The checkout-only pilot projection could not be built safely."""


class ResearchMovePilotProjectionItem(StrictModel):
    """The complete model-visible projection of one ResearchMove."""

    functional_name: NonEmptyString
    runtime_projection: NonEmptyString


class ResearchMovePilotProjection(StrictModel):
    """The complete model-visible pilot view, with no source provenance."""

    non_authoritative_notice: Literal[_NON_AUTHORITATIVE_NOTICE] = (
        _NON_AUTHORITATIVE_NOTICE
    )
    moves: Annotated[
        tuple[ResearchMovePilotProjectionItem, ...],
        Field(min_length=2, max_length=2),
    ]

    @model_validator(mode="after")
    def _functional_names_are_unique(self) -> "ResearchMovePilotProjection":
        names = tuple(item.functional_name for item in self.moves)
        if len(set(names)) != len(names):
            raise ValueError("pilot projection functional names must be unique")
        return self


class ResearchMovePilotProvenance(StrictModel):
    """Bound one source-isolated projection to its exact audited release."""

    release_id: Literal["research.corpus.contribution_structure.v4"]
    corpus_sha256: Digest
    route_id: PilotRouteId
    move_ids: Annotated[tuple[StableId, ...], Field(min_length=2, max_length=2)]
    move_versions: tuple[Literal[1], Literal[1]] = (1, 1)
    model_visible_sha256: Digest
    pilot_use_context: Literal["existing_revise_framing_only"] = (
        "existing_revise_framing_only"
    )
    maximum_moves_used: Literal[2] = 2
    none_is_valid: Literal[True] = True
    short_reason_required: Literal[True] = True
    default_activation_authorized: Literal[False] = False
    automatic_selection_authorized: Literal[False] = False
    route_disposition_authority: Literal[False] = False
    canonical_write_authorized: Literal[False] = False
    novelty_authority: Literal[False] = False
    importance_authority: Literal[False] = False
    welfare_authority: Literal[False] = False
    venue_authority: Literal[False] = False
    human_gate_authority: Literal[False] = False

    @model_validator(mode="after")
    def _provenance_is_the_exact_pilot_release(
        self,
    ) -> "ResearchMovePilotProvenance":
        if self.corpus_sha256 != RESEARCH_CORPUS_V4_HASH:
            raise ValueError("pilot provenance requires the exact V4 corpus")
        expected = _ROUTE_MOVE_IDS[self.route_id]
        if self.move_ids != expected:
            raise ValueError("pilot provenance move order does not match its route")
        return self


@dataclass(frozen=True, slots=True)
class ResearchMovePilotMaterial:
    """Separated model-visible bytes and bounded provenance."""

    model_visible: ResearchMovePilotProjection
    model_visible_bytes: bytes
    host_provenance: ResearchMovePilotProvenance


def research_move_pilot_work_packet_payload(
    material: ResearchMovePilotMaterial,
) -> dict[str, object]:
    """Return the exact derived-only payload embedded in compiled context."""

    if not isinstance(material, ResearchMovePilotMaterial):
        raise TypeError("pilot material has the wrong type")
    return {
        "pilot_schema": "econ-theorist/research-move-pilot/v1",
        "provenance": material.host_provenance.model_dump(mode="json"),
        "model_visible": material.model_visible.model_dump(mode="json"),
    }


def _pilot_route(route_id: str) -> PilotRouteId:
    if not isinstance(route_id, str) or route_id not in _ROUTE_MOVE_IDS:
        raise ResearchMovePilotError(
            "research-move pilot supports only question-and-benchmarks framing"
        )
    return route_id  # type: ignore[return-value]


def build_research_move_pilot_material(
    corpus_path: Path,
    *,
    route_id: str,
) -> ResearchMovePilotMaterial:
    """Build one deterministic, source-isolated two-card pilot material.

    The absolute checkout path is mandatory.  The hash, release, authorized
    move menu, route compatibility, and order are fixed in code and all fail
    closed.  This function has no write path and grants no scientific or
    operational authority.
    """

    route = _pilot_route(route_id)
    if not isinstance(corpus_path, Path):
        raise TypeError("research-move pilot corpus path must be a pathlib.Path")
    if not corpus_path.is_absolute():
        raise ResearchMovePilotError(
            "research-move pilot requires one explicit absolute corpus path"
        )
    try:
        corpus = load_research_corpus(
            corpus_path,
            expected_hash=RESEARCH_CORPUS_V4_HASH,
        )
    except ResearchCraftPolicyError as exc:
        raise ResearchMovePilotError(str(exc)) from exc
    if (
        corpus.release_id != "research.corpus.contribution_structure.v4"
        or corpus.resource_version != 4
    ):
        raise ResearchMovePilotError(
            "research-move pilot requires the exact V4 release"
        )

    moves_by_id = {move.move_id: move for move in corpus.moves}
    selected_ids = _ROUTE_MOVE_IDS[route]
    if not set(selected_ids).issubset(moves_by_id):
        raise ResearchMovePilotError(
            "research-move pilot authorized menu is incomplete"
        )
    selected = []
    for move_id in selected_ids:
        move = moves_by_id[move_id]
        if route not in move.compatible_route_ids:
            raise ResearchMovePilotError(
                f"research move is not compatible with pilot route: {move_id}"
            )
        selected.append(
            ResearchMovePilotProjectionItem(
                functional_name=move.functional_name,
                runtime_projection=move.runtime_projection,
            )
        )

    model_visible = ResearchMovePilotProjection(moves=tuple(selected))
    model_visible_bytes = canonical_json_bytes(model_visible)
    host_provenance = ResearchMovePilotProvenance(
        release_id=corpus.release_id,
        corpus_sha256=RESEARCH_CORPUS_V4_HASH,
        route_id=route,
        move_ids=selected_ids,
        model_visible_sha256=sha256_digest(model_visible_bytes),
    )
    return ResearchMovePilotMaterial(
        model_visible=model_visible,
        model_visible_bytes=model_visible_bytes,
        host_provenance=host_provenance,
    )


__all__ = [
    "MARKET_OPERATION_MOVE_ID",
    "QUESTION_REFRAMER_MOVE_ID",
    "ResearchMovePilotError",
    "ResearchMovePilotMaterial",
    "ResearchMovePilotProjection",
    "ResearchMovePilotProjectionItem",
    "ResearchMovePilotProvenance",
    "build_research_move_pilot_material",
    "research_move_pilot_work_packet_payload",
]
