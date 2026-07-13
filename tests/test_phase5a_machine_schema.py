"""Phase 5A machine schemas are exact, deterministic model projections."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_machine_schemas import (
    MACHINE_SCHEMA_MODELS,
    SCHEMA_ID_ROOT,
    check,
    export,
    model_files,
    rendered_schemas,
    schema_filename,
)
from tests.helpers import REPOSITORY_ROOT


class Phase5AMachineSchemaTests(unittest.TestCase):
    def test_exact_model_and_committed_file_coverage(self) -> None:
        destination = REPOSITORY_ROOT / "schemas" / "machine" / "v1"
        mapped = model_files()

        self.assertEqual(len(mapped), len(MACHINE_SCHEMA_MODELS))
        self.assertEqual(set(mapped.values()), set(MACHINE_SCHEMA_MODELS))
        self.assertEqual(
            set(mapped),
            {schema_filename(model.__name__) for model in MACHINE_SCHEMA_MODELS},
        )
        self.assertEqual(
            {path.name for path in destination.glob("*.schema.json")},
            set(mapped),
        )
        self.assertTrue(check(destination))

    def test_export_is_byte_for_byte_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "schemas"
            export(destination)
            first = {
                path.name: path.read_bytes()
                for path in sorted(destination.glob("*.schema.json"))
            }
            export(destination)
            second = {
                path.name: path.read_bytes()
                for path in sorted(destination.glob("*.schema.json"))
            }

        self.assertEqual(first, second)
        self.assertEqual(
            first,
            {
                filename: content.encode("utf-8")
                for filename, content in rendered_schemas().items()
            },
        )

    def test_schema_ids_match_machine_namespace_and_filenames(self) -> None:
        for filename, content in rendered_schemas().items():
            schema = json.loads(content)
            self.assertEqual(schema["$id"], f"{SCHEMA_ID_ROOT}/{filename}")


if __name__ == "__main__":
    unittest.main()
