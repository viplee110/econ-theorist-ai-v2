from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests.helpers import REPOSITORY_ROOT

from econ_theorist.codec import object_digest
from econ_theorist.theory import THEORY_PAYLOAD_MODELS


ORACLE = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "phase2_frozen_v2"
    / "canonical_semantics.v2.json"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Phase2FrozenSemanticTests(unittest.TestCase):
    def test_accepted_phase2_semantic_surface_is_unchanged(self) -> None:
        expected = json.loads(ORACLE.read_text(encoding="utf-8"))
        theory_schemas = {
            path.name: sha256(path)
            for path in sorted(
                (REPOSITORY_ROOT / "schemas" / "theory" / "v1").glob(
                    "*.schema.json"
                )
            )
        }
        v2_instructions = {
            path.name: sha256(path)
            for path in sorted(
                (REPOSITORY_ROOT / "routes" / "instructions").glob("*.v2.txt")
            )
        }
        model_schemas = {
            name: model.model_json_schema(mode="validation")
            for name, model in sorted(THEORY_PAYLOAD_MODELS.items())
        }
        actual = {
            "accepted_commit": "6a14d52e4655dc8b7d5a42e43467f4c58faba510",
            "gold_fixture_hash": sha256(
                REPOSITORY_ROOT
                / "tests"
                / "fixtures"
                / "phase2_attention_precision_gold.v1.json"
            ),
            "instruction_directory_hash": object_digest(v2_instructions),
            "route_registry_v2_file_hash": sha256(
                REPOSITORY_ROOT / "routes" / "registry.v2.json"
            ),
            "schema_directory_hash": object_digest(theory_schemas),
            "theory_model_schema_hash": object_digest(model_schemas),
            "theory_payload_count": len(model_schemas),
        }
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
