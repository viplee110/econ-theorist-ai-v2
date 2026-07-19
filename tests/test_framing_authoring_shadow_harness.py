"""Focused tests for the frozen paired-authoring shadow harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.framing_quality_authoring import (
    FramingAuditSemanticDraftV1,
    FramingAuditSemanticDraftV2,
    compile_framing_audit_semantic_draft,
    compile_framing_audit_semantic_draft_v2,
    preflight_framing_audit_semantic_draft,
    preflight_framing_audit_semantic_draft_v2,
)
from econ_theorist.policy import ROUTE_REGISTRY_V8_HASH
from econ_theorist.project import init_project
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.replay import replay, validate_candidate


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
PREPARER_V2 = _load_script(
    "test_loaded_prepare_framing_authoring_pair_v2",
    "prepare_framing_authoring_pair_v2.py",
)


class FramingAuthoringShadowHarnessTests(unittest.TestCase):
    def test_semantic_v2_surface_dispatches_only_to_v2_authoring(self) -> None:
        self.assertIn("semantic_v2", HARNESS._SURFACES)
        self.assertEqual(
            HARNESS._semantic_surface_handlers("semantic"),
            (
                FramingAuditSemanticDraftV1,
                preflight_framing_audit_semantic_draft,
                compile_framing_audit_semantic_draft,
            ),
        )
        self.assertEqual(
            HARNESS._semantic_surface_handlers("semantic_v2"),
            (
                FramingAuditSemanticDraftV2,
                preflight_framing_audit_semantic_draft_v2,
                compile_framing_audit_semantic_draft_v2,
            ),
        )

    def test_unknown_semantic_surface_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            HARNESS.SetupError, "unknown semantic authoring surface"
        ):
            HARNESS._semantic_surface_handlers("semantic-v3")

    def test_new_liability_oracle_passes_v2_and_unchanged_v8(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-liability-pair-test-") as raw:
            root = Path(raw) / "project"
            init_project(
                root,
                name="Accident-liability oracle test",
                actor_id=PREPARER_V2.HUMAN_ID,
                project_id="project.accident.liability.test",
                created_at=PREPARER_V2.T0,
                transaction_id="transaction.liability.test.genesis",
                route_run_id="run.liability.test.genesis",
            )
            layout = StoreLayout.at(root)
            prefix, core = PREPARER_V2._build_prefix(layout)
            _, contract, snapshot = PREPARER_V2._open_audit(layout, prefix)
            draft = PREPARER_V2._semantic_draft(
                PREPARER_V2._oracle_bundle(core)
            )
            report = preflight_framing_audit_semantic_draft_v2(
                snapshot, contract, draft
            )
            self.assertTrue(report.passed, report.issues)
            transaction = compile_framing_audit_semantic_draft_v2(
                snapshot, contract, draft
            )
            validate_candidate(
                snapshot,
                transaction,
                route_registry_hash=ROUTE_REGISTRY_V8_HASH,
                enforce_live_current_policy=True,
            )
            self.assertEqual(replay(layout).head, prefix.head)

    def test_new_semantic_prompt_exposes_v2_without_full_witness(self) -> None:
        prompt = PREPARER_V2._task_prompt("semantic_v2").decode("utf-8")
        self.assertIn("FramingAuditSemanticDraftV2", prompt)
        self.assertIn("margin_intent", prompt)
        self.assertIn("omit", prompt)
        self.assertIn("active_margin_witness", prompt)

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
                    "layer": "framing_payload_preflight",
                    "type": "framing.payload.schema",
                    "rule_id": "framing.payload.schema",
                    "message": "x",
                },
                "json_or_schema",
            ),
            (
                {
                    "layer": "framing_payload_preflight",
                    "type": "framing.envelope.schema_id",
                    "rule_id": "framing.envelope.schema_id",
                    "message": "x",
                },
                "wrapper_or_binding",
            ),
            (
                {
                    "layer": "framing_payload_preflight",
                    "type": "framing.payload.semantic_ledger",
                    "rule_id": "framing.payload.semantic_ledger",
                    "diagnostic_category": "semantic_ledger",
                    "message": "fixed_endogenous_conflict",
                },
                "path_or_semantic_ledger",
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
