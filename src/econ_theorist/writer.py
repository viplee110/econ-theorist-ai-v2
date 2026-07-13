"""Provider-neutral canonical-writer boundary for Phase 3 and Phase 4.

The runtime passes only the clean role packet to this interface. Phase 4 uses
the same canonical writer with a narrower profiled packet containing selected
functional moves but no anchor prose.
Provider adapters can implement the protocol later; deterministic fixtures make
the boundary executable in CI without credentials or network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Protocol

from .codec import canonical_json_bytes, sha256_digest
from .models import Actor


class WriterBoundaryError(ValueError):
    """A writer received a noncanonical or non-writer role packet."""


@dataclass(frozen=True, slots=True)
class WriterOutput:
    writer: Actor
    role_packet_hash: str
    manuscript_key: str
    text: str
    content_hash: str

    @property
    def data(self) -> bytes:
        return self.text.encode("utf-8")


class CanonicalWriter(Protocol):
    actor: Actor

    def compose(
        self, role_packet: Mapping[str, object], *, manuscript_key: str
    ) -> WriterOutput: ...


class DeterministicFixtureWriter:
    """Return one pinned manuscript fixture for an exact clean role packet."""

    def __init__(self, *, actor: Actor, fixtures: Mapping[str, str]) -> None:
        if actor.kind == "deterministic_tool":
            raise WriterBoundaryError("the canonical writer must be a human or agent")
        if not fixtures:
            raise WriterBoundaryError("a deterministic writer requires a fixture")
        normalized: dict[str, str] = {}
        for key, text in fixtures.items():
            if not isinstance(key, str) or not key:
                raise WriterBoundaryError("fixture keys must be nonempty strings")
            if not isinstance(text, str) or not text.strip():
                raise WriterBoundaryError("fixture manuscript text must be nonempty")
            if "\r" in text or "\x00" in text:
                raise WriterBoundaryError("fixture text must be canonical LF UTF-8 text")
            normalized[key] = text
        self.actor = actor
        self._fixtures = MappingProxyType(normalized)

    def compose(
        self, role_packet: Mapping[str, object], *, manuscript_key: str
    ) -> WriterOutput:
        if not isinstance(role_packet, Mapping):
            raise WriterBoundaryError("role_packet must be a mapping")
        if role_packet.get("packet_schema") != "econ-theorist/role-packet/v1":
            raise WriterBoundaryError("writer role packet has an unknown schema")
        if role_packet.get("packet_kind") not in {
            "canonical_writer",
            "profiled_canonical_writer",
        }:
            raise WriterBoundaryError("canonical writer received another role's packet")
        try:
            text = self._fixtures[manuscript_key]
        except KeyError as exc:
            raise WriterBoundaryError(
                f"unknown deterministic manuscript fixture: {manuscript_key}"
            ) from exc
        packet_hash = sha256_digest(canonical_json_bytes(dict(role_packet)))
        return WriterOutput(
            writer=self.actor,
            role_packet_hash=packet_hash,
            manuscript_key=manuscript_key,
            text=text,
            content_hash=sha256_digest(text.encode("utf-8")),
        )


__all__ = [
    "CanonicalWriter",
    "DeterministicFixtureWriter",
    "WriterBoundaryError",
    "WriterOutput",
]
