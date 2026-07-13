"""Committed Phase 4 profile/craft schemas are exact strict-model projections."""

from __future__ import annotations

import json
import unittest

from tests.helpers import REPOSITORY_ROOT

from econ_theorist.profile_craft import PROFILE_CRAFT_PAYLOAD_MODELS
from scripts.export_profile_craft_schemas import (
    SCHEMA_ID_ROOT,
    check,
    rendered_schemas,
    schema_filename,
)


class ProfileCraftSchemaExportTests(unittest.TestCase):
    def test_all_registered_profile_craft_schemas_are_committed_exactly(self) -> None:
        destination = REPOSITORY_ROOT / "schemas" / "profile_craft" / "v1"
        rendered = rendered_schemas()
        self.assertEqual(
            set(rendered),
            {
                schema_filename(entity_type)
                for entity_type in PROFILE_CRAFT_PAYLOAD_MODELS
            },
        )
        self.assertEqual(len(rendered), len(PROFILE_CRAFT_PAYLOAD_MODELS))
        self.assertTrue(check(destination))

    def test_schema_ids_use_the_independent_profile_craft_namespace(self) -> None:
        for filename, text in rendered_schemas().items():
            with self.subTest(filename=filename):
                schema = json.loads(text)
                self.assertEqual(schema["$id"], f"{SCHEMA_ID_ROOT}/{filename}")

    def test_registered_models_remain_strict_and_float_free(self) -> None:
        def inspect_objects(node: object) -> None:
            if isinstance(node, dict):
                if node.get("type") == "object" and "properties" in node:
                    self.assertFalse(node.get("additionalProperties", True))
                for value in node.values():
                    inspect_objects(value)
            elif isinstance(node, list):
                for value in node:
                    inspect_objects(value)

        for entity_type, model in PROFILE_CRAFT_PAYLOAD_MODELS.items():
            with self.subTest(entity_type=entity_type):
                self.assertEqual(model.model_config.get("extra"), "forbid")
                self.assertTrue(model.model_config.get("strict"))
                self.assertTrue(model.model_config.get("frozen"))
                schema = model.model_json_schema(mode="validation")
                self.assertNotIn('"type": "number"', json.dumps(schema))
                inspect_objects(schema)


if __name__ == "__main__":
    unittest.main()
