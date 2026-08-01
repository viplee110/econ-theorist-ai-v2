"""Focused checks for the checkout-only ResearchMove pilot projection."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.research_craft_pilot import (
    MARKET_OPERATION_MOVE_ID,
    QUESTION_REFRAMER_MOVE_ID,
    ResearchMovePilotError,
    build_research_move_pilot_material,
)
from econ_theorist.research_craft_policy import RESEARCH_CORPUS_V4_HASH


V3_PATH = (REPOSITORY_ROOT / "craft" / "research_corpus.v3.json").resolve()
V4_PATH = (REPOSITORY_ROOT / "craft" / "research_corpus.v4.json").resolve()


class ResearchCraftPilotTests(unittest.TestCase):
    def test_framing_projection_is_exact_source_isolated_and_non_authoritative(
        self,
    ) -> None:
        material = build_research_move_pilot_material(
            V4_PATH,
            route_id="frame.question_and_benchmarks",
        )
        self.assertEqual(
            material.host_provenance.move_ids,
            (MARKET_OPERATION_MOVE_ID, QUESTION_REFRAMER_MOVE_ID),
        )
        self.assertEqual(
            tuple(item.functional_name for item in material.model_visible.moves),
            ("Market-Operation Primitive", "Question Reframer"),
        )
        visible = json.loads(material.model_visible_bytes.decode("utf-8"))
        self.assertEqual(set(visible), {"non_authoritative_notice", "moves"})
        for item in visible["moves"]:
            self.assertEqual(
                set(item),
                {"functional_name", "runtime_projection"},
            )
        serialized = material.model_visible_bytes.decode("utf-8").casefold()
        for forbidden in (
            "citation",
            "https://",
            "sha256",
            "source_cards",
            "authors",
            "source_locator",
            RESEARCH_CORPUS_V4_HASH,
            MARKET_OPERATION_MOVE_ID,
            QUESTION_REFRAMER_MOVE_ID,
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden.casefold(), serialized)

        provenance = material.host_provenance
        self.assertEqual(provenance.corpus_sha256, RESEARCH_CORPUS_V4_HASH)
        self.assertEqual(
            provenance.model_visible_sha256,
            sha256_digest(material.model_visible_bytes),
        )
        self.assertTrue(provenance.none_is_valid)
        self.assertTrue(provenance.short_reason_required)
        self.assertEqual(provenance.maximum_moves_used, 2)
        self.assertEqual(
            provenance.pilot_use_context,
            "existing_revise_framing_only",
        )
        self.assertIn("not for creating a fresh frame", serialized)
        for field_name in (
            "default_activation_authorized",
            "automatic_selection_authorized",
            "route_disposition_authority",
            "canonical_write_authorized",
            "novelty_authority",
            "importance_authority",
            "welfare_authority",
            "venue_authority",
            "human_gate_authority",
        ):
            self.assertIs(getattr(provenance, field_name), False)

    def test_framing_projection_has_exact_deterministic_bytes(self) -> None:
        first = build_research_move_pilot_material(
            V4_PATH,
            route_id="frame.question_and_benchmarks",
        )
        second = build_research_move_pilot_material(
            V4_PATH,
            route_id="frame.question_and_benchmarks",
        )
        self.assertEqual(
            first.host_provenance.move_ids,
            (MARKET_OPERATION_MOVE_ID, QUESTION_REFRAMER_MOVE_ID),
        )
        self.assertEqual(
            tuple(item.functional_name for item in first.model_visible.moves),
            ("Market-Operation Primitive", "Question Reframer"),
        )
        self.assertEqual(first.model_visible, second.model_visible)
        self.assertEqual(first.model_visible_bytes, second.model_visible_bytes)
        self.assertEqual(first.host_provenance, second.host_provenance)
        self.assertEqual(
            first.model_visible_bytes,
            canonical_json_bytes(first.model_visible),
        )

    def test_wrong_path_hash_release_route_and_tamper_fail_closed(self) -> None:
        with self.assertRaisesRegex(ResearchMovePilotError, "absolute"):
            build_research_move_pilot_material(
                Path("craft/research_corpus.v4.json"),
                route_id="frame.question_and_benchmarks",
            )
        with self.assertRaisesRegex(ResearchMovePilotError, "cannot load"):
            build_research_move_pilot_material(
                (REPOSITORY_ROOT / "craft" / "missing.json").resolve(),
                route_id="frame.question_and_benchmarks",
            )
        with patch(
            "econ_theorist.research_craft_pilot.RESEARCH_CORPUS_V4_HASH",
            "0" * 64,
        ):
            with self.assertRaisesRegex(ResearchMovePilotError, "expected hash"):
                build_research_move_pilot_material(
                    V4_PATH,
                    route_id="frame.question_and_benchmarks",
                )
        with self.assertRaisesRegex(ResearchMovePilotError, "hash mismatch"):
            build_research_move_pilot_material(
                V3_PATH,
                route_id="frame.question_and_benchmarks",
            )
        with self.assertRaisesRegex(ResearchMovePilotError, "supports only"):
            build_research_move_pilot_material(
                V4_PATH,
                route_id="discover.claims_and_boundaries",
            )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            craft = root / "craft"
            craft.mkdir()
            tampered_path = craft / "research_corpus.v4.json"
            data = bytearray(V4_PATH.read_bytes())
            data[-2] = ord(" ") if data[-2] != ord(" ") else ord("\t")
            tampered_path.write_bytes(data)
            with self.assertRaisesRegex(ResearchMovePilotError, "cannot load|hash"):
                build_research_move_pilot_material(
                    tampered_path.resolve(),
                    route_id="frame.question_and_benchmarks",
                )

    def test_import_has_no_implicit_file_access_and_construction_never_writes(
        self,
    ) -> None:
        code = """
from pathlib import Path
def fail(*args, **kwargs):
    raise AssertionError('import read a file through pathlib')
Path.read_bytes = fail
import econ_theorist.research_craft_pilot
"""
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)

        with patch.object(Path, "write_bytes", side_effect=AssertionError("write")):
            build_research_move_pilot_material(
                V4_PATH,
                route_id="frame.question_and_benchmarks",
            )


if __name__ == "__main__":
    unittest.main()
