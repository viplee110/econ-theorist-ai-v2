"""Focused tests for the frozen paired-authoring shadow harness."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import canonical_json_bytes, sha256_digest
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
PUBLISHER = _load_script(
    "test_loaded_publish_json_only_artifact",
    "publish_json_only_artifact.py",
)


class JsonOnlyArtifactPublisherTests(unittest.TestCase):
    def test_valid_object_preserves_exact_bom_free_source_bytes(self) -> None:
        source_bytes = b'{\n  "b": [2, 3],\n  "a": 1\n}\n'
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_01.scratch.json"
            target = root / "attempt_01.json"
            scratch.write_bytes(source_bytes)

            published = PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertEqual(published, source_bytes)
            self.assertEqual(target.read_bytes(), source_bytes)

    def test_one_utf8_bom_is_removed_without_other_byte_changes(self) -> None:
        source_bytes = b'{\r\n  "a": 1\r\n}\r\n'
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_01.scratch.json"
            target = root / "attempt_01.json"
            scratch.write_bytes(b"\xef\xbb\xbf" + source_bytes)

            published = PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertEqual(published, source_bytes)
            self.assertEqual(target.read_bytes(), source_bytes)

    def test_shell_result_prefix_is_rejected_without_target(self) -> None:
        source_bytes = (
            b"Exit code: 0\nWall time: 1 seconds\nOutput:\n"
            b'{"candidate":true}\n'
        )
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_02.scratch.json"
            target = root / "attempt_02.json"
            scratch.write_bytes(source_bytes)

            with self.assertRaisesRegex(
                PUBLISHER.JsonOnlyArtifactError,
                "one complete JSON object",
            ):
                PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertFalse(target.exists())

    def test_trailing_brace_is_rejected_without_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_03.scratch.json"
            target = root / "attempt_03.json"
            scratch.write_bytes(b'{"candidate":true}\n}\n')

            with self.assertRaisesRegex(
                PUBLISHER.JsonOnlyArtifactError,
                "one complete JSON object",
            ):
                PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertFalse(target.exists())

    def test_top_level_array_is_rejected_without_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_01.scratch.json"
            target = root / "attempt_01.json"
            scratch.write_bytes(b'[{"candidate":true}]')

            with self.assertRaisesRegex(
                PUBLISHER.JsonOnlyArtifactError,
                "top-level JSON value must be an object",
            ):
                PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertFalse(target.exists())

    def test_existing_published_artifact_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_01.scratch.json"
            target = root / "attempt_01.json"
            scratch.write_bytes(b'{"candidate":"new"}')
            target.write_bytes(b'{"candidate":"old"}')

            with self.assertRaisesRegex(
                PUBLISHER.JsonOnlyArtifactError,
                "refusing to overwrite",
            ):
                PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertEqual(target.read_bytes(), b'{"candidate":"old"}')

    def test_exact_published_artifact_replay_is_idempotent(self) -> None:
        source_bytes = b'{"candidate":"same"}'
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_01.scratch.json"
            target = root / "attempt_01.json"
            scratch.write_bytes(source_bytes)

            first = PUBLISHER.publish_json_only_artifact(scratch, target)
            second = PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertEqual(first, source_bytes)
            self.assertEqual(second, source_bytes)
            self.assertEqual(target.read_bytes(), source_bytes)

    def test_duplicate_object_key_is_rejected_without_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_01.scratch.json"
            target = root / "attempt_01.json"
            scratch.write_bytes(b'{"candidate":true,"candidate":false}')

            with self.assertRaisesRegex(
                PUBLISHER.JsonOnlyArtifactError,
                "duplicate JSON object key",
            ):
                PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertFalse(target.exists())

    def test_atomic_publish_failure_leaves_no_target_or_temporary_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_01.scratch.json"
            target = root / "attempt_01.json"
            scratch.write_bytes(b'{"candidate":true}')

            with patch.object(PUBLISHER.os, "link", side_effect=OSError("boom")):
                with self.assertRaisesRegex(
                    PUBLISHER.JsonOnlyArtifactError,
                    "cannot atomically publish",
                ):
                    PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertFalse(target.exists())
            self.assertEqual(list(root.glob(f".{target.name}.*.tmp")), [])

    def test_generic_link_race_accepts_exact_winner_and_rejects_conflict(self) -> None:
        source_bytes = b'{"candidate":"ours"}'
        for winner, accepted in (
            (source_bytes, True),
            (b'{"candidate":"other"}', False),
        ):
            with self.subTest(accepted=accepted), tempfile.TemporaryDirectory(
                prefix="etai-json-publish-race-"
            ) as raw:
                root = Path(raw)
                scratch = root / "attempt_01.scratch.json"
                target = root / "attempt_01.json"
                scratch.write_bytes(source_bytes)

                def lose_race(source, destination):
                    Path(destination).write_bytes(winner)
                    raise OSError("simulated Windows losing race")

                with patch.object(PUBLISHER.os, "link", side_effect=lose_race):
                    if accepted:
                        published = PUBLISHER.publish_json_only_artifact(
                            scratch, target
                        )
                        self.assertEqual(published, source_bytes)
                    else:
                        with self.assertRaisesRegex(
                            PUBLISHER.JsonOnlyArtifactError,
                            "different bytes",
                        ):
                            PUBLISHER.publish_json_only_artifact(scratch, target)

                self.assertEqual(target.read_bytes(), winner)
                self.assertEqual(list(root.glob(f".{target.name}.*.tmp")), [])

    def test_invalid_utf8_is_rejected_without_target(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-json-publish-") as raw:
            root = Path(raw)
            scratch = root / "attempt_01.scratch.json"
            target = root / "attempt_01.json"
            scratch.write_bytes(b'{"candidate":"\xff"}')

            with self.assertRaisesRegex(
                PUBLISHER.JsonOnlyArtifactError,
                "not valid UTF-8",
            ):
                PUBLISHER.publish_json_only_artifact(scratch, target)

            self.assertFalse(target.exists())


class FramingAuthoringShadowHarnessTests(unittest.TestCase):
    def test_transaction_near_match_metadata_survives_issue_adapter(self) -> None:
        issue = HARNESS._single_issue(
            layer="transaction_schema",
            issue_type="candidate_draft_template_missing",
            message="closest relation has one extra field",
            location=("operations", 6, "relation", "downstream", "semantic_hash"),
            json_pointer="/operations/6/relation/downstream/semantic_hash",
            expected="<absent>",
            observed="<present>",
            mismatch_kind="extra field",
        )

        self.assertEqual(
            issue["json_pointer"],
            "/operations/6/relation/downstream/semantic_hash",
        )
        self.assertEqual(issue["expected"], "<absent>")
        self.assertEqual(issue["observed"], "<present>")
        self.assertEqual(issue["mismatch_kind"], "extra field")

    def test_immutable_output_write_is_atomic_and_exactly_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-shadow-output-") as raw:
            root = Path(raw)
            target = root / "attempt_01.receipt.json"
            data = b'{"receipt":true}'

            HARNESS._write_new(target, data)
            HARNESS._write_new(target, data)
            self.assertEqual(target.read_bytes(), data)
            with self.assertRaisesRegex(HARNESS.SetupError, "different bytes"):
                HARNESS._write_new(target, b'{"receipt":false}')
            self.assertEqual(target.read_bytes(), data)

    def test_immutable_output_atomic_failure_leaves_no_partial_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-shadow-output-") as raw:
            root = Path(raw)
            target = root / "attempt_01.receipt.json"

            with patch.object(HARNESS.os, "link", side_effect=OSError("boom")):
                with self.assertRaisesRegex(
                    HARNESS.SetupError,
                    "cannot atomically publish",
                ):
                    HARNESS._write_new(target, b'{"receipt":true}')

            self.assertFalse(target.exists())
            self.assertEqual(list(root.glob(f".{target.name}.*.tmp")), [])

    def test_immutable_output_handles_generic_windows_link_race(self) -> None:
        data = b'{"receipt":"ours"}'
        for winner, accepted in (
            (data, True),
            (b'{"receipt":"other"}', False),
        ):
            with self.subTest(accepted=accepted), tempfile.TemporaryDirectory(
                prefix="etai-shadow-output-race-"
            ) as raw:
                root = Path(raw)
                target = root / "attempt_01.receipt.json"

                def lose_race(source, destination):
                    Path(destination).write_bytes(winner)
                    raise OSError("simulated Windows losing race")

                with patch.object(HARNESS.os, "link", side_effect=lose_race):
                    if accepted:
                        HARNESS._write_new(target, data)
                    else:
                        with self.assertRaisesRegex(
                            HARNESS.SetupError,
                            "different bytes",
                        ):
                            HARNESS._write_new(target, data)

                self.assertEqual(target.read_bytes(), winner)
                self.assertEqual(list(root.glob(f".{target.name}.*.tmp")), [])

    def test_harness_publishes_projection_before_completion_receipt(self) -> None:
        writes: list[str] = []
        with (
            patch.object(
                HARNESS,
                "_run",
                return_value=(0, {"receipt": True}, {"projection": True}),
            ),
            patch.object(
                HARNESS,
                "_write_new",
                side_effect=lambda path, data: writes.append(path.name),
            ),
            patch("builtins.print"),
        ):
            status = HARNESS.main(
                [
                    "--case",
                    "case.json",
                    "--surface",
                    "semantic_v2",
                    "--arm-id",
                    "arm.semantic",
                    "--attempt",
                    "1",
                    "--source",
                    "attempt_01.json",
                    "--receipt",
                    "attempt_01.receipt.json",
                    "--projection",
                    "attempt_01.projection.json",
                ]
            )

        self.assertEqual(status, 0)
        self.assertEqual(
            writes,
            ["attempt_01.projection.json", "attempt_01.receipt.json"],
        )

    def test_setup_only_validates_bindings_without_reading_candidate(self) -> None:
        with (
            patch.object(HARNESS, "_bound_setup") as bound_setup,
            patch.object(HARNESS, "_run") as run,
            patch("builtins.print"),
        ):
            status = HARNESS.main(
                [
                    "--case",
                    "case.json",
                    "--surface",
                    "semantic_v2",
                    "--arm-id",
                    "arm.semantic",
                    "--attempt",
                    "2",
                    "--source",
                    "attempt_02.json",
                    "--receipt",
                    "attempt_02.receipt.json",
                    "--prior-receipt",
                    "attempt_01.receipt.json",
                    "--check-setup-only",
                ]
            )

        self.assertEqual(status, 0)
        bound_setup.assert_called_once()
        run.assert_not_called()

    def test_stale_projection_blocks_a_no_projection_receipt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="etai-shadow-output-") as raw:
            root = Path(raw)
            projection = root / "attempt_01.projection.json"
            receipt = root / "attempt_01.receipt.json"
            projection.write_bytes(b'{"stale":true}')
            with (
                patch.object(
                    HARNESS,
                    "_run",
                    return_value=(1, {"validator_pass": False}, None),
                ),
                patch("builtins.print"),
            ):
                status = HARNESS.main(
                    [
                        "--case",
                        str(root / "case.json"),
                        "--surface",
                        "semantic_v2",
                        "--arm-id",
                        "arm.semantic",
                        "--attempt",
                        "1",
                        "--source",
                        str(root / "attempt_01.json"),
                        "--receipt",
                        str(receipt),
                        "--projection",
                        str(projection),
                    ]
                )

            self.assertEqual(status, 2)
            self.assertFalse(receipt.exists())
            self.assertEqual(projection.read_bytes(), b'{"stale":true}')

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
        self.assertIn("force_margin_locators", prompt)
        self.assertNotIn("exactly under `SURFACE.json`", prompt)
        self.assertIn("omit", prompt)
        self.assertIn("active_margin_witness", prompt)

    def test_v2_runner_publishes_json_only_scratch_before_harness(self) -> None:
        prompt = PREPARER_V2._task_prompt("semantic_v2").decode("utf-8")
        runner = PREPARER_V2._runner_script(
            output_root=Path("C:/tmp/frozen-pair"),
            arm_root=Path("C:/tmp/frozen-pair/arm-semantic"),
            surface="semantic_v2",
            python_runtime=Path("C:/runtime/python.exe"),
            runtime_manifest_sha256="1" * 64,
        ).decode("utf-8")

        self.assertIn("work/attempt_01.scratch.json", prompt)
        self.assertIn("one complete top-level JSON object", prompt)
        self.assertIn("never trims, extracts, reserializes", prompt)
        self.assertIn("artifact-hygiene correction", prompt)
        self.assertIn("receipt is the completion marker", prompt)
        self.assertIn("do not rerun the attempt", prompt)
        self.assertIn('attempt_$number.scratch.json', runner)
        self.assertIn("publish_json_only_artifact.py", runner)
        self.assertLess(
            runner.index("--check-setup-only"),
            runner.index("publish_json_only_artifact.py"),
        )
        self.assertLess(
            runner.index("missing prior receipt"),
            runner.index("publish_json_only_artifact.py"),
        )
        self.assertLess(
            runner.index("attempt already has an immutable receipt"),
            runner.index("publish_json_only_artifact.py"),
        )
        self.assertLess(
            runner.index("publish_json_only_artifact.py"),
            runner.rindex("@arguments"),
        )

    @unittest.skipUnless(sys.platform == "win32", "PowerShell runner is Windows-only")
    def test_generated_runner_executes_valid_and_rejects_invalid_scratch(
        self,
    ) -> None:
        stub_harness = b"""from __future__ import annotations
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--case', type=Path, required=True)
parser.add_argument('--surface', required=True)
parser.add_argument('--arm-id', required=True)
parser.add_argument('--attempt', type=int, required=True)
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--receipt', type=Path, required=True)
parser.add_argument('--projection', type=Path)
parser.add_argument('--prior-receipt', type=Path)
parser.add_argument('--check-setup-only', action='store_true')
args = parser.parse_args()
if args.check_setup_only:
    print('SETUP_OK')
    raise SystemExit(0)
if args.projection is not None:
    args.projection.write_bytes(b'{\"projection\":true}')
args.receipt.write_bytes(b'{\"receipt\":true}')
print('{\"receipt\":true}')
"""
        publisher = (
            Path(REPOSITORY_ROOT) / "scripts" / "publish_json_only_artifact.py"
        ).read_bytes()
        for scratch_bytes, expected_status in (
            (b'{"candidate":true}', 0),
            (b'prefix {"candidate":true}', 2),
        ):
            with self.subTest(expected_status=expected_status), tempfile.TemporaryDirectory(
                prefix="etai-generated-runner-"
            ) as raw:
                output_root = Path(raw) / "pair"
                runtime = output_root / "runtime"
                arm_root = output_root / "arm-semantic"
                work = arm_root / "work"
                runtime.mkdir(parents=True)
                work.mkdir(parents=True)
                (arm_root / "report").mkdir()
                harness_path = runtime / "run_framing_authoring_shadow.py"
                publisher_path = runtime / "publish_json_only_artifact.py"
                harness_path.write_bytes(stub_harness)
                publisher_path.write_bytes(publisher)
                files = []
                for path in (harness_path, publisher_path):
                    data = path.read_bytes()
                    files.append(
                        {
                            "path": path.relative_to(runtime).as_posix(),
                            "bytes": len(data),
                            "sha256": sha256_digest(data),
                        }
                    )
                manifest_bytes = canonical_json_bytes({"files": files})
                (runtime / "RUNTIME_MANIFEST.json").write_bytes(manifest_bytes)
                (work / "attempt_01.scratch.json").write_bytes(scratch_bytes)
                runner_path = arm_root / "RUN_ATTEMPT.ps1"
                runner_path.write_bytes(
                    PREPARER_V2._runner_script(
                        output_root=output_root,
                        arm_root=arm_root,
                        surface="semantic_v2",
                        python_runtime=Path(sys.executable).resolve(),
                        runtime_manifest_sha256=sha256_digest(manifest_bytes),
                    )
                )

                completed = subprocess.run(
                    (
                        "powershell.exe",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(runner_path),
                        "-Attempt",
                        "1",
                    ),
                    cwd=arm_root,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )

                self.assertEqual(
                    completed.returncode,
                    expected_status,
                    completed.stdout + completed.stderr,
                )
                source = work / "attempt_01.json"
                receipt = work / "attempt_01.receipt.json"
                if expected_status == 0:
                    self.assertEqual(source.read_bytes(), scratch_bytes)
                    self.assertTrue(receipt.is_file())
                else:
                    self.assertFalse(source.exists())
                    self.assertFalse(receipt.exists())

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
