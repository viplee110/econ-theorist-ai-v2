"""Focused tests for the frozen paired-authoring shadow harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src


def _load_harness():
    path = Path(REPOSITORY_ROOT) / "scripts" / "run_framing_authoring_shadow.py"
    spec = importlib.util.spec_from_file_location(
        "test_loaded_framing_authoring_shadow", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load paired-authoring shadow harness")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = _load_harness()


class FramingAuthoringShadowHarnessTests(unittest.TestCase):
    def test_frozen_taxonomy_separates_structural_and_scientific_failures(self) -> None:
        cases = (
            (
                {"layer": "semantic_schema", "type": "missing", "message": "x"},
                "json_or_schema",
            ),
            (
                {
                    "layer": "preflight",
                    "type": "compiler.payload.schema",
                    "rule_id": "compiler.payload.schema",
                    "message": "x",
                },
                "json_or_schema",
            ),
            (
                {
                    "layer": "preflight",
                    "type": "compiler.contract.base_mismatch",
                    "rule_id": "compiler.contract.base_mismatch",
                    "message": "x",
                },
                "setup",
            ),
            (
                {
                    "layer": "preflight",
                    "type": "compiler.payload.exact_input_duplicate_source",
                    "rule_id": "compiler.payload.exact_input_duplicate_source",
                    "message": "x",
                },
                "wrapper_or_binding",
            ),
            (
                {
                    "layer": "transaction_schema",
                    "type": "candidate_draft_template_missing",
                    "message": "x",
                },
                "relation_or_hash",
            ),
            (
                {
                    "layer": "transaction_schema",
                    "type": "missing",
                    "location": ["operations", 2, "relation", "upstream", "semantic_hash"],
                    "message": "Field required",
                },
                "relation_or_hash",
            ),
            (
                {
                    "layer": "validator",
                    "type": "CandidateValidationError",
                    "rule_id": "framing.primitive_paths",
                    "message": "causal_force_binding",
                },
                "path_or_semantic_ledger",
            ),
            (
                {
                    "layer": "validator",
                    "type": "CandidateValidationError",
                    "message": "active_margin_witness_missing",
                },
                "scientific_validator",
            ),
            (
                {
                    "layer": "validator",
                    "type": "CandidateValidationError",
                    "message": "causal_force_binding: every force must appear",
                },
                "scientific_validator",
            ),
            (
                {
                    "layer": "validator",
                    "type": "CandidateValidationError",
                    "message": "FramingQualityBundle does not bind the exact route inputs",
                },
                "wrapper_or_binding",
            ),
        )
        for issue, expected in cases:
            with self.subTest(expected=expected, issue=issue):
                self.assertEqual(HARNESS._issue_bucket(issue), expected)

    def test_unknown_validator_failure_is_not_optimistically_structural(self) -> None:
        issue = {
            "layer": "validator",
            "type": "CandidateValidationError",
            "message": "new V8 economic acceptance rule",
        }
        counts = HARNESS._taxonomy([issue])
        self.assertEqual(counts["scientific_validator"], 1)
        self.assertEqual(sum(counts.values()), 1)

    def test_canonical_source_size_excludes_formatting(self) -> None:
        compact = b'{"a":1,"b":[2,3]}'
        spaced = b'{\n  "b": [2, 3],\n  "a": 1\n}'
        self.assertNotEqual(len(compact), len(spaced))
        self.assertEqual(
            HARNESS._canonical_source_bytes(compact),
            HARNESS._canonical_source_bytes(spaced),
        )
        self.assertIsNone(HARNESS._canonical_source_bytes(b"not json"))


if __name__ == "__main__":
    unittest.main()
