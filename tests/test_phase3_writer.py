"""Provider-neutral boundary tests for the Phase 3 canonical writer."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.models import Actor
from econ_theorist.writer import (
    DeterministicFixtureWriter,
    WriterBoundaryError,
)


def role_packet(*, packet_kind: str = "canonical_writer") -> dict[str, object]:
    return {
        "packet_schema": "econ-theorist/role-packet/v1",
        "packet_kind": packet_kind,
        "purpose": "compose one mechanism-explanation unit",
        "payload": {
            "question": "Can precision deter information processing?",
            "scope": "Binary state and indivisible processing.",
        },
    }


class DeterministicFixtureWriterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actor = Actor(kind="agent", actor_id="writer.canonical")
        self.text = (
            "Conditional on processing, precision improves accuracy.\n"
            "The reversal comes from the processing margin, not that conditional comparison.\n"
        )
        self.writer = DeterministicFixtureWriter(
            actor=self.actor,
            fixtures={"mechanism.good": self.text},
        )

    def test_exact_role_packet_produces_reproducible_canonical_output(self) -> None:
        packet = role_packet()
        first = self.writer.compose(packet, manuscript_key="mechanism.good")
        reordered = {
            "payload": packet["payload"],
            "purpose": packet["purpose"],
            "packet_kind": packet["packet_kind"],
            "packet_schema": packet["packet_schema"],
        }
        second = self.writer.compose(reordered, manuscript_key="mechanism.good")

        self.assertEqual(first, second)
        self.assertEqual(first.writer, self.actor)
        self.assertEqual(first.data, self.text.encode("utf-8"))
        self.assertEqual(first.role_packet_hash, sha256_digest(canonical_json_bytes(packet)))
        self.assertEqual(first.content_hash, sha256_digest(first.data))

    def test_unknown_schema_and_non_writer_role_packets_fail_closed(self) -> None:
        wrong_schema = role_packet()
        wrong_schema["packet_schema"] = "econ-theorist/role-packet/v0"
        with self.assertRaisesRegex(WriterBoundaryError, "unknown schema"):
            self.writer.compose(wrong_schema, manuscript_key="mechanism.good")

        with self.assertRaisesRegex(WriterBoundaryError, "another role"):
            self.writer.compose(
                role_packet(packet_kind="cold_reader"),
                manuscript_key="mechanism.good",
            )
        with self.assertRaisesRegex(WriterBoundaryError, "must be a mapping"):
            self.writer.compose([], manuscript_key="mechanism.good")  # type: ignore[arg-type]

    def test_unknown_fixture_and_noncanonical_fixture_configuration_are_rejected(self) -> None:
        with self.assertRaisesRegex(WriterBoundaryError, "unknown deterministic"):
            self.writer.compose(role_packet(), manuscript_key="mechanism.missing")
        with self.assertRaisesRegex(WriterBoundaryError, "human or agent"):
            DeterministicFixtureWriter(
                actor=Actor(kind="deterministic_tool", actor_id="tool.writer"),
                fixtures={"unit": "Text."},
            )
        for fixtures in ({}, {"unit": "\r\n"}, {"unit": "contains\x00nul"}):
            with self.subTest(fixtures=fixtures), self.assertRaises(WriterBoundaryError):
                DeterministicFixtureWriter(actor=self.actor, fixtures=fixtures)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
