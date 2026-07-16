from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from econ_theorist.codec import canonical_json_bytes
from econ_theorist.codex_bridge import (
    CodexBridge,
    CodexCompleteRequestV1,
    CodexSessionV1,
    CodexStartRequestV1,
)
from scripts.capture_codex_invocation import _capture_exit_code, capture_invocation


ROOT = Path(__file__).resolve().parents[1]
NOW = "2026-07-15T00:00:00Z"


class CodexInvocationCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.request = self.root / "request.json"
        self._write_request(self.root)
        self.stdout = self.root / "evidence" / "stdout.jsonl"
        self.stderr = self.root / "evidence" / "stderr.txt"
        self.metadata = self.root / "evidence" / "meta.json"
        self.local_app_data = self.root / ".host-state"

    def _request(self, project_root: Path) -> CodexStartRequestV1:
        return CodexStartRequestV1(
            project_root=str(project_root),
            initialize=True,
            project_name="Capture harness fixture",
            requested_scope="Frame one bounded theory question.",
            framing_intent="When can a benchmark prediction reverse?",
            session=CodexSessionV1(
                session_id="capture-harness-session",
                selected_model="gpt-5",
                installed_models=("gpt-5",),
                observed_at=NOW,
            ),
        )

    def _write_request(self, project_root: Path) -> bytes:
        data = canonical_json_bytes(self._request(project_root))
        self.request.write_bytes(data)
        return data

    def _invoke(
        self,
        command: list[str],
        *,
        candidate_source: Path | None = None,
    ) -> tuple[int, dict]:
        return capture_invocation(
            command,
            request_path=self.request,
            project_root=self.root,
            local_app_data=self.local_app_data,
            stdout_path=self.stdout,
            stderr_path=self.stderr,
            metadata_path=self.metadata,
            candidate_source_path=candidate_source,
        )

    def _prepare_complete_capture(
        self,
    ) -> tuple[CodexCompleteRequestV1, Path]:
        bridge = CodexBridge(
            trusted_clock=lambda: NOW,
            preproject_operational_home=self.root.parent / "preproject-operations",
        )
        ready = bridge.invoke(self._request(self.root))
        self.assertEqual(ready.outcome, "ready", ready)
        assert ready.route_run_id is not None
        assert ready.work_packet_hash is not None
        assert ready.delivery_envelope_hash is not None
        assert ready.candidate_logical_path is not None
        complete = CodexCompleteRequestV1(
            project_root=str(self.root),
            route_run_id=ready.route_run_id,
            work_packet_hash=ready.work_packet_hash,
            delivery_envelope_hash=ready.delivery_envelope_hash,
        )
        self.request.write_bytes(canonical_json_bytes(complete))
        candidate = self.root / ready.candidate_logical_path
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return complete, candidate

    @staticmethod
    def _completion_child(route_run_id: str, candidate_digest: str) -> str:
        return (
            "import hashlib,json,sys; data=sys.stdin.buffer.read(); "
            "value={'bridge_response_schema':"
            "'econ-theorist/codex-bridge-response/v1','bridge_version':1,"
            "'operation':'complete','request_digest':hashlib.sha256(data).hexdigest(),"
            "'outcome':'staged','mutated':True,'completion':{"
            "'completion_result_schema':"
            "'econ-theorist/candidate-completion-result/v1','status':'staged',"
            f"'route_run_id':{route_run_id!r},"
            f"'candidate_digest':{candidate_digest!r},"
            "'transaction_digest':None,'head_before':'0'*64,'head_after':'0'*64,"
            "'host_receipt_hash':'1'*64}}; "
            "sys.stdout.write(json.dumps(value,separators=(',',':'))+'\\n')"
        )

    def test_large_raw_response_and_portable_state_are_captured_directly(
        self,
    ) -> None:
        payload_size = 300_000
        child = (
            "import hashlib,json,os,sys; data=sys.stdin.buffer.read(); "
            "digest=hashlib.sha256(data).hexdigest(); "
            "details={'stdin_sha256':digest,"
            "'localappdata':os.environ.get('LOCALAPPDATA'),"
            "'home':os.environ.get('HOME'),"
            "'xdg':os.environ.get('XDG_STATE_HOME')}; "
            "diagnostic={'diagnostic_schema':'econ-theorist/diagnostic/v1',"
            "'code':'capture_probe','severity':'info',"
            f"'message':'x'*{payload_size},'details':details}}; "
            "value={'bridge_response_schema':'econ-theorist/codex-bridge-response/v1',"
            "'bridge_version':1,'operation':'start_or_resume',"
            "'request_digest':digest,'outcome':'blocked','mutated':False,"
            "'diagnostics':[diagnostic]}; "
            "sys.stdout.write(json.dumps(value,separators=(',',':'))+'\\n'); "
            "sys.stderr.write('bounded-stderr\\n')"
        )
        exit_code, metadata = self._invoke([sys.executable, "-c", child])

        self.assertEqual(exit_code, 0)
        self.assertTrue(metadata["response_valid"])
        self.assertEqual(
            metadata["capture_schema"],
            "econ-theorist/codex-invocation-capture/v2",
        )
        self.assertTrue(metadata["stdout_json_object_valid"])
        self.assertTrue(metadata["bridge_response_valid"])
        self.assertGreater(metadata["stdout_bytes"], 256 * 1024)
        response = json.loads(self.stdout.read_bytes())
        diagnostic = response["diagnostics"][0]
        self.assertEqual(len(diagnostic["message"]), payload_size)
        details = diagnostic["details"]
        self.assertEqual(details["stdin_sha256"], metadata["request_sha256"])
        self.assertEqual(
            details["localappdata"], str(self.local_app_data.resolve())
        )
        self.assertEqual(details["home"], metadata["home"])
        self.assertEqual(details["xdg"], metadata["xdg_state_home"])
        self.assertEqual(
            self.stderr.read_text(encoding="utf-8").splitlines(),
            ["bounded-stderr"],
        )
        self.assertTrue(
            (
                self.local_app_data
                / "EconTheoristAI"
                / "operational"
                / "v1"
            ).is_dir()
        )
        self.assertTrue(
            (
                Path(metadata["home"])
                / ".local"
                / "state"
                / "econ-theorist"
                / "operational"
                / "v1"
            ).is_dir()
        )
        persisted = json.loads(self.metadata.read_bytes())
        self.assertEqual(persisted["stdout_sha256"], metadata["stdout_sha256"])
        self.assertEqual(persisted["request_transport"], "stdin")
        self.assertEqual(
            Path(metadata["captured_request_path"]).read_bytes(),
            self.request.read_bytes(),
        )
        self.assertEqual(
            metadata["captured_request_sha256"], metadata["request_sha256"]
        )

    def test_pre_read_request_bytes_remain_bound_when_source_changes(self) -> None:
        original = self.request.read_bytes()
        child = (
            "import hashlib,json,pathlib,sys; data=sys.stdin.buffer.read(); "
            "pathlib.Path(sys.argv[1]).write_bytes(b'changed-after-read'); "
            "digest=hashlib.sha256(data).hexdigest(); "
            "diagnostic={'diagnostic_schema':'econ-theorist/diagnostic/v1',"
            "'code':'capture_probe','severity':'info','message':'probe',"
            "'details':{'stdin_sha256':digest}}; "
            "value={'bridge_response_schema':'econ-theorist/codex-bridge-response/v1',"
            "'bridge_version':1,'operation':'start_or_resume',"
            "'request_digest':digest,'outcome':'blocked','mutated':False,"
            "'diagnostics':[diagnostic]}; "
            "sys.stdout.write(json.dumps(value,separators=(',',':'))+'\\n')"
        )
        exit_code, metadata = self._invoke(
            [sys.executable, "-c", child, str(self.request)]
        )

        self.assertEqual(exit_code, 0)
        response = json.loads(self.stdout.read_bytes())
        expected = hashlib.sha256(original).hexdigest()
        self.assertEqual(response["diagnostics"][0]["details"]["stdin_sha256"], expected)
        self.assertEqual(metadata["request_sha256"], expected)
        self.assertTrue(metadata["source_request_changed_after_read"])
        self.assertEqual(self.request.read_bytes(), b"changed-after-read")
        self.assertEqual(
            Path(metadata["captured_request_path"]).read_bytes(), original
        )

    def test_complete_capture_freezes_pre_invocation_candidate_bytes(self) -> None:
        _, candidate = self._prepare_complete_capture()
        original = b"\xef\xbb\xbf{\"candidate\":\"before\"}\n"
        candidate.write_bytes(original)

        with self.assertRaisesRegex(ValueError, "candidate_source_path is required"):
            self._invoke([sys.executable, "-c", "raise SystemExit(99)"])

        child = (
            "import hashlib,json,sys; data=sys.stdin.buffer.read(); "
            "value={'bridge_response_schema':'econ-theorist/codex-bridge-response/v1',"
            "'bridge_version':1,'operation':'complete',"
            "'request_digest':hashlib.sha256(data).hexdigest(),"
            "'outcome':'blocked','mutated':False}; "
            "sys.stdout.write(json.dumps(value,separators=(',',':'))+'\\n')"
        )
        exit_code, metadata = self._invoke(
            [sys.executable, "-c", child],
            candidate_source=candidate,
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(metadata["response_valid"])
        self.assertEqual(
            metadata["candidate_sha256"], hashlib.sha256(original).hexdigest()
        )
        self.assertEqual(
            Path(metadata["captured_candidate_path"]).read_bytes(), original
        )
        self.assertFalse(metadata["source_candidate_changed_after_read"])
        self.assertIsNotNone(metadata["candidate_preflight_validation_error"])
        self.assertEqual(candidate.read_bytes(), original)

    def test_complete_capture_rejects_wrong_or_changed_candidate_source(
        self,
    ) -> None:
        _, candidate = self._prepare_complete_capture()
        original = b'{"candidate":"before"}\n'
        candidate.write_bytes(original)
        wrong = self.root / ".econ-theorist" / "staging" / "wrong.json"
        wrong.write_bytes(original)

        with self.assertRaisesRegex(ValueError, "differs from the complete request"):
            self._invoke(
                [sys.executable, "-c", "raise SystemExit(99)"],
                candidate_source=wrong,
            )

        child = (
            "import hashlib,json,pathlib,sys; data=sys.stdin.buffer.read(); "
            "pathlib.Path(sys.argv[1]).write_bytes(b'candidate-after'); "
            "value={'bridge_response_schema':'econ-theorist/codex-bridge-response/v1',"
            "'bridge_version':1,'operation':'complete',"
            "'request_digest':hashlib.sha256(data).hexdigest(),"
            "'outcome':'blocked','mutated':False}; "
            "sys.stdout.write(json.dumps(value,separators=(',',':'))+'\\n')"
        )
        exit_code, metadata = self._invoke(
            [sys.executable, "-c", child, str(candidate)],
            candidate_source=candidate,
        )

        self.assertEqual(exit_code, 0)
        self.assertTrue(metadata["bridge_schema_valid"])
        self.assertFalse(metadata["response_valid"])
        self.assertTrue(metadata["source_candidate_changed_after_read"])
        self.assertIn("candidate source changed", metadata["response_binding_error"])
        self.assertEqual(
            Path(metadata["captured_candidate_path"]).read_bytes(), original
        )
        self.assertEqual(_capture_exit_code(exit_code, False), 3)

    def test_complete_capture_binds_completion_candidate_digest(self) -> None:
        complete, candidate = self._prepare_complete_capture()
        candidate.write_bytes(b'{"candidate":"before"}\n')
        expected = "a" * 64

        with patch(
            "scripts.capture_codex_invocation.candidate_source_digest",
            return_value=expected,
        ):
            exit_code, metadata = self._invoke(
                [
                    sys.executable,
                    "-c",
                    self._completion_child(complete.route_run_id, expected),
                ],
                candidate_source=candidate,
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(metadata["response_valid"])
        self.assertTrue(metadata["candidate_digest_matches_response"])
        self.assertEqual(metadata["candidate_canonical_digest_before"], expected)

    def test_complete_capture_rejects_completion_candidate_digest_mismatch(
        self,
    ) -> None:
        complete, candidate = self._prepare_complete_capture()
        candidate.write_bytes(b'{"candidate":"before"}\n')
        expected = "a" * 64

        with patch(
            "scripts.capture_codex_invocation.candidate_source_digest",
            return_value=expected,
        ):
            exit_code, metadata = self._invoke(
                [
                    sys.executable,
                    "-c",
                    self._completion_child(complete.route_run_id, "b" * 64),
                ],
                candidate_source=candidate,
            )

        self.assertEqual(exit_code, 0)
        self.assertTrue(metadata["bridge_schema_valid"])
        self.assertFalse(metadata["response_valid"])
        self.assertFalse(metadata["candidate_digest_matches_response"])
        self.assertIn(
            "candidate digest differs",
            metadata["response_binding_error"],
        )

    def test_json_object_is_not_mistaken_for_a_bridge_response(self) -> None:
        child = "import sys; sys.stdout.write('{}\\n')"
        child_exit, metadata = self._invoke([sys.executable, "-c", child])

        self.assertEqual(child_exit, 0)
        self.assertTrue(metadata["stdout_json_object_valid"])
        self.assertFalse(metadata["bridge_schema_valid"])
        self.assertFalse(metadata["bridge_response_valid"])
        self.assertFalse(metadata["response_valid"])
        self.assertIsNone(metadata["json_shape_error"])
        self.assertIn("operation", metadata["bridge_validation_error"])
        self.assertEqual(_capture_exit_code(child_exit, False), 3)
        persisted = json.loads(self.metadata.read_bytes())
        self.assertTrue(persisted["stdout_json_object_valid"])
        self.assertFalse(persisted["bridge_response_valid"])

    def test_schema_valid_response_with_wrong_operation_is_rejected(self) -> None:
        child = (
            "import hashlib,json,sys; data=sys.stdin.buffer.read(); "
            "value={'bridge_response_schema':'econ-theorist/codex-bridge-response/v1',"
            "'bridge_version':1,'operation':'complete',"
            "'request_digest':hashlib.sha256(data).hexdigest(),"
            "'outcome':'blocked','mutated':False}; "
            "sys.stdout.write(json.dumps(value,separators=(',',':'))+'\\n')"
        )
        child_exit, metadata = self._invoke([sys.executable, "-c", child])

        self.assertEqual(child_exit, 0)
        self.assertTrue(metadata["stdout_json_object_valid"])
        self.assertTrue(metadata["bridge_schema_valid"])
        self.assertFalse(metadata["bridge_response_valid"])
        self.assertIn("operation", metadata["response_binding_error"])
        self.assertEqual(_capture_exit_code(child_exit, False), 3)

    def test_schema_valid_response_with_wrong_request_digest_is_rejected(
        self,
    ) -> None:
        child = (
            "import json,sys; sys.stdin.buffer.read(); "
            "value={'bridge_response_schema':'econ-theorist/codex-bridge-response/v1',"
            "'bridge_version':1,'operation':'start_or_resume',"
            "'request_digest':'0'*64,'outcome':'blocked','mutated':False}; "
            "sys.stdout.write(json.dumps(value,separators=(',',':'))+'\\n')"
        )
        child_exit, metadata = self._invoke([sys.executable, "-c", child])

        self.assertEqual(child_exit, 0)
        self.assertTrue(metadata["stdout_json_object_valid"])
        self.assertTrue(metadata["bridge_schema_valid"])
        self.assertFalse(metadata["bridge_response_valid"])
        self.assertIn("request_digest", metadata["response_binding_error"])
        self.assertEqual(_capture_exit_code(child_exit, False), 3)

    def test_request_root_must_match_selected_pilot_root(self) -> None:
        other = self.root / "other-project"
        other.mkdir()
        self._write_request(other)
        with self.assertRaisesRegex(ValueError, "project_root does not match"):
            self._invoke([sys.executable, "-c", "raise SystemExit(99)"])
        self.assertFalse(self.stdout.exists())
        self.assertFalse(self.metadata.exists())

    def test_outputs_are_distinct_inside_root_and_never_overwritten(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be distinct"):
            capture_invocation(
                [sys.executable, "-c", "raise SystemExit(99)"],
                request_path=self.request,
                project_root=self.root,
                local_app_data=self.local_app_data,
                stdout_path=self.stdout,
                stderr_path=self.stdout,
                metadata_path=self.metadata,
            )

        nested = self.root / "nested-output"
        with self.assertRaisesRegex(ValueError, "cannot contain one another"):
            capture_invocation(
                [sys.executable, "-c", "raise SystemExit(99)"],
                request_path=self.request,
                project_root=self.root,
                local_app_data=self.local_app_data,
                stdout_path=nested,
                stderr_path=nested / "stderr.txt",
                metadata_path=self.metadata,
            )

        outside = self.root.parent / f"{self.root.name}-outside"
        with self.assertRaisesRegex(ValueError, "inside the selected pilot root"):
            capture_invocation(
                [sys.executable, "-c", "raise SystemExit(99)"],
                request_path=self.request,
                project_root=self.root,
                local_app_data=self.local_app_data,
                stdout_path=outside / "stdout.jsonl",
                stderr_path=self.stderr,
                metadata_path=self.metadata,
            )

        self.stdout.parent.mkdir(parents=True)
        self.stdout.write_bytes(b"owned")
        with self.assertRaises(FileExistsError):
            self._invoke([sys.executable, "-c", "raise SystemExit(99)"])
        self.assertEqual(self.stdout.read_bytes(), b"owned")

    def test_real_first_bridge_call_uses_stdin_and_isolated_state(self) -> None:
        probe = CodexStartRequestV1(
            project_root=str(self.root),
            session=self._request(self.root).session,
        )
        self.request.write_bytes(canonical_json_bytes(probe))
        absolute_source = str(ROOT / "src")
        with patch.dict(os.environ, {"PYTHONPATH": absolute_source}):
            exit_code, metadata = self._invoke(
                [
                    sys.executable,
                    "-m",
                    "econ_theorist",
                    "codex",
                    "invoke",
                    "--request",
                    "-",
                ]
            )

        self.assertEqual(
            exit_code,
            0,
            self.stdout.read_text(encoding="utf-8")
            + self.stderr.read_text(encoding="utf-8"),
        )
        response = json.loads(self.stdout.read_bytes())
        self.assertEqual(response["operation"], "start_or_resume")
        self.assertEqual(response["outcome"], "blocked")
        self.assertEqual(
            response["diagnostics"][0]["code"],
            "codex_project_initialization_required",
        )
        self.assertEqual(response["request_digest"], metadata["request_sha256"])
        self.assertEqual(metadata["request_transport"], "stdin")
        self.assertFalse(metadata["source_request_changed_after_read"])
        self.assertFalse((self.root / ".econ-theorist").exists())


if __name__ == "__main__":
    unittest.main()
