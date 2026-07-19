"""Focused tests for the frozen paired-authoring shadow harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src


def _load_script(name: str, filename: str):
    path = Path(REPOSITORY_ROOT) / "scripts" / filename
    spec = importlib.util.spec_from_file_location(
        name, path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load paired-authoring shadow harness")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


HARNESS = _load_script(
    "test_loaded_framing_authoring_shadow",
    "run_framing_authoring_shadow.py",
)
PREPARER = _load_script(
    "test_loaded_prepare_framing_authoring_pair",
    "prepare_framing_authoring_pair.py",
)


class FramingAuthoringShadowHarnessTests(unittest.TestCase):
    def test_launch_prompt_treats_task_creation_as_an_operator_precondition(
        self,
    ) -> None:
        prompt = PREPARER._launch_prompt(
            arm_root=Path("C:/tmp/frozen-pair/arm-semantic"),
            surface="semantic",
            arm_manifest_sha256="1" * 64,
        ).decode("utf-8")
        normalized = " ".join(prompt.split())
        self.assertIn("user already created this Codex task", normalized)
        self.assertIn(
            "Do not create, fork, delegate, or hand off another task", normalized
        )
        self.assertNotIn("Open the new Codex task", prompt)

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
