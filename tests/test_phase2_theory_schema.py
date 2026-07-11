"""Committed Phase 2 theory schemas are exact projections of strict models."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT

from scripts.export_theory_schemas import check, rendered_schemas


class TheorySchemaExportTests(unittest.TestCase):
    def test_all_registered_theory_schemas_are_committed_exactly(self) -> None:
        destination = REPOSITORY_ROOT / "schemas" / "theory" / "v1"
        self.assertTrue(check(destination))
        self.assertEqual(len(rendered_schemas()), 26)

    def test_theory_schemas_have_no_floating_number_type(self) -> None:
        for filename, text in rendered_schemas().items():
            with self.subTest(filename=filename):
                self.assertNotIn('"type": "number"', text)


if __name__ == "__main__":
    unittest.main()
