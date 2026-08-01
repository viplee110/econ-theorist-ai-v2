from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest
from unittest import mock

import econ_theorist.codex_bridge as codex_bridge
from econ_theorist.codec import canonical_json_bytes
from econ_theorist.codex_bridge import (
    CODEX_BRIDGE_REQUEST_ADAPTER,
    CodexBridge,
    CodexCompleteRequestV1,
    codex_bridge_schema,
)
from econ_theorist.codex_cli import invoke_codex_bytes


class Phase5BTheoremTeamBridgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name) / "paper"
        self.root.mkdir()

    def _complete_request(self, **changes) -> CodexCompleteRequestV1:
        values = {
            "project_root": str(self.root),
            "route_run_id": "run.theorem.test",
            "work_packet_hash": "a" * 64,
            "delivery_envelope_hash": "b" * 64,
        }
        values.update(changes)
        return CodexCompleteRequestV1(**values)

    def _invoke_completion_guard(
        self, request: CodexCompleteRequestV1, *, active: bool
    ):
        packet = SimpleNamespace(
            route_id="verify.claims_proofs_and_interpretation",
            route_run_id=request.route_run_id,
            candidate_logical_path=".econ-theorist/staging/candidate.json",
        )
        with (
            mock.patch.object(codex_bridge, "_grant", return_value=object()),
            mock.patch.object(
                codex_bridge,
                "_read_provider_delivery",
                return_value=(SimpleNamespace(), SimpleNamespace(), packet),
            ),
            mock.patch.object(
                codex_bridge,
                "replay",
                return_value=SimpleNamespace(route_outcomes=()),
            ),
            mock.patch.object(
                codex_bridge, "theorem_team_is_active", return_value=active
            ),
        ):
            return CodexBridge().invoke(request)

    def test_active_team_requires_exact_review_hash(self) -> None:
        response = self._invoke_completion_guard(
            self._complete_request(), active=True
        )
        self.assertEqual(response.outcome, "error")
        self.assertIn("requires its exact published review", response.diagnostics[0].message)

    def test_active_team_requires_atomic_stage_and_commit(self) -> None:
        response = self._invoke_completion_guard(
            self._complete_request(
                theorem_team_review_hash="c" * 64,
                action="stage_only",
            ),
            active=True,
        )
        self.assertEqual(response.outcome, "error")
        self.assertIn("requires stage_and_commit", response.diagnostics[0].message)

    def test_review_without_active_team_fails_closed(self) -> None:
        response = self._invoke_completion_guard(
            self._complete_request(theorem_team_review_hash="c" * 64),
            active=False,
        )
        self.assertEqual(response.outcome, "error")
        self.assertIn("without an active team plan", response.diagnostics[0].message)

    def test_repaired_candidate_is_not_blocked_by_prior_staged_digest(self) -> None:
        request = self._complete_request(theorem_team_review_hash="c" * 64)
        packet = SimpleNamespace(
            route_id="verify.claims_proofs_and_interpretation",
            route_run_id=request.route_run_id,
            candidate_logical_path=".econ-theorist/staging/candidate.json",
        )
        staged_probe = mock.Mock(return_value=True)
        with (
            mock.patch.object(codex_bridge, "_grant", return_value=object()),
            mock.patch.object(
                codex_bridge,
                "_read_provider_delivery",
                return_value=(SimpleNamespace(), SimpleNamespace(), packet),
            ),
            mock.patch.object(
                codex_bridge,
                "replay",
                return_value=SimpleNamespace(route_outcomes=()),
            ),
            mock.patch.object(
                codex_bridge, "theorem_team_is_active", return_value=True
            ),
            mock.patch.object(
                codex_bridge,
                "read_theorem_team_review",
                return_value=SimpleNamespace(team_plan_hash="d" * 64),
            ),
            mock.patch.object(
                codex_bridge,
                "read_theorem_team_delivery_authorization",
                return_value=SimpleNamespace(
                    source_delivery_envelope_hash=request.delivery_envelope_hash
                ),
            ),
            mock.patch.object(
                codex_bridge,
                "candidate_source_digest",
                side_effect=ValueError("repaired candidate reached digest"),
            ),
            mock.patch.object(
                codex_bridge, "_has_active_staged_candidate", staged_probe
            ),
        ):
            response = CodexBridge().invoke(request)

        self.assertEqual(response.outcome, "error")
        self.assertIn("repaired candidate reached digest", response.diagnostics[0].message)
        staged_probe.assert_not_called()

    def test_legacy_complete_bytes_omit_additive_field(self) -> None:
        request = self._complete_request()
        encoded = canonical_json_bytes(request)
        self.assertNotIn(b"theorem_team_review_hash", encoded)
        decoded = CODEX_BRIDGE_REQUEST_ADAPTER.validate_json(encoded, strict=True)
        self.assertEqual(canonical_json_bytes(decoded), encoded)

        with_review = self._complete_request(theorem_team_review_hash="c" * 64)
        self.assertIn(b"theorem_team_review_hash", canonical_json_bytes(with_review))

    def test_schema_and_cli_recognize_both_theorem_operations(self) -> None:
        request_schema = json.dumps(codex_bridge_schema("request"))
        self.assertIn("theorem_team.open", request_schema)
        self.assertIn("theorem_team.publish_review", request_schema)

        for operation in ("theorem_team.open", "theorem_team.publish_review"):
            response = invoke_codex_bytes(canonical_json_bytes({"operation": operation}))
            self.assertEqual(response.outcome, "error")
            self.assertEqual(response.operation, operation)


if __name__ == "__main__":
    unittest.main()
