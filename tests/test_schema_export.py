from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT

from scripts.export_schemas import MODELS, check


class SchemaExportTests(unittest.TestCase):
    def test_committed_schemas_match_strict_models(self) -> None:
        self.assertGreaterEqual(len(MODELS), 8)
        self.assertTrue(check(REPOSITORY_ROOT / "schemas" / "v1"))


if __name__ == "__main__":
    unittest.main()
