from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests import test_phase5a2_codex_bridge as phase5a_fixture

from econ_theorist.codec import canonical_json_bytes
from econ_theorist.codex_bridge import (
    CODEX_BRIDGE_REQUEST_ADAPTER,
    CodexBridge,
    CodexCompleteRequestV1,
    CodexDirectUserCaptureV1,
    CodexFramingAmbiguousInterpretationV1,
    CodexFramingClearInterpretationV1,
    CodexFramingLaneDraftV1,
    CodexFramingNewBriefInterpretationV1,
    CodexFramingTeamCapabilityV1,
    CodexFramingTeamOpenRequestV1,
    CodexFramingTeamPanelRequestV1,
    CodexFramingTeamUserTurnRequestV1,
    CodexFramingWorkerObservationV1,
    CodexSessionV1,
    CodexStartRequestV1,
)
from econ_theorist.codex_cli import invoke_codex_bytes
from econ_theorist.framing_team import (
    read_framing_team_delivery_authorization,
    read_framing_worker_activation,
    read_framing_worker_completion_binding,
)
from econ_theorist.machine.models import HostOperationReceiptV1
from econ_theorist.machine.operational import (
    ContentAddressedOperationalStore,
    ProjectOperationalLayout,
)
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.replay import replay


NOW = "2026-07-22T00:00:00Z"


class Phase5BCodexBridgeTests(unittest.TestCase):
    """Focused trusted-local host checks over one public framing delivery."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        self.bridge = CodexBridge(
            trusted_clock=lambda: NOW,
            preproject_operational_home=self.anchor / "preproject-operations",
        )
        self.session = CodexSessionV1(
            session_id="codex-session-phase5b",
            selected_model="gpt-5",
            installed_models=("gpt-5", "gpt-5-mini"),
            observed_at=NOW,
        )
        self.ready = self.bridge.invoke(
            CodexStartRequestV1(
                project_root=str(self.root),
                initialize=True,
                project_name="Phase 5B public framing fixture",
                requested_scope="Frame one bounded economic-theory question.",
                framing_intent=(
                    "When can endogenous participation reverse a fixed-participation "
                    "benchmark?"
                ),
                session=self.session,
            )
        )
        self.assertEqual(self.ready.outcome, "ready", self.ready)
        self.assertIsNotNone(self.ready.work_packet)
        assert self.ready.work_packet is not None
        self.assertEqual(
            self.ready.work_packet.route_id, "frame.question_and_benchmarks"
        )
        self.assertEqual(self.ready.work_packet.privacy_clearance, "public")
        self.assertFalse(self.ready.work_packet.hidden_compartments)
        for value in (
            self.ready.route_run_id,
            self.ready.work_packet_hash,
            self.ready.delivery_envelope_hash,
        ):
            self.assertIsNotNone(value)

    def _delivery_binding(self) -> dict[str, str]:
        assert self.ready.route_run_id is not None
        assert self.ready.work_packet_hash is not None
        assert self.ready.delivery_envelope_hash is not None
        return {
            "project_root": str(self.root),
            "route_run_id": self.ready.route_run_id,
            "work_packet_hash": self.ready.work_packet_hash,
            "delivery_envelope_hash": self.ready.delivery_envelope_hash,
        }

    def _available_capability(self) -> CodexFramingTeamCapabilityV1:
        return CodexFramingTeamCapabilityV1(
            team_surface="available",
            lane_separation="logical",
            direct_user_capture="current_user_turn",
        )

    def _open_team(self):
        return self.bridge.invoke(
            CodexFramingTeamOpenRequestV1(
                **self._delivery_binding(),
                session=self.session,
                capability=self._available_capability(),
            )
        )

    def _publish_panel(self):
        opened = self._open_team()
        self.assertEqual(opened.outcome, "team_ready", opened)
        assert opened.framing_team is not None
        assert opened.framing_team.team_plan_hash is not None
        panel = self.bridge.invoke(
            CodexFramingTeamPanelRequestV1(
                **self._delivery_binding(),
                team_plan_hash=opened.framing_team.team_plan_hash,
                session=self.session,
                mentor=CodexFramingLaneDraftV1(
                    agent_label="mentor-agent",
                    model_observation="gpt-5",
                    content_markdown=(
                        "Challenge whether participation is the smallest exact delta."
                    ),
                ),
                collaborator_a=CodexFramingLaneDraftV1(
                    agent_label="collaborator-a-agent",
                    model_observation="gpt-5",
                    content_markdown="Keep the fixed-participation benchmark explicit.",
                ),
                collaborator_b=CodexFramingLaneDraftV1(
                    agent_label="collaborator-b-agent",
                    model_observation="gpt-5-mini",
                    content_markdown="Try a simpler binary participation margin.",
                ),
            )
        )
        self.assertEqual(panel.outcome, "awaiting_user_choice", panel)
        assert panel.framing_team is not None
        assert panel.framing_team.panel_hash is not None
        return panel

    def _capture(self, text: str) -> CodexDirectUserCaptureV1:
        return CodexDirectUserCaptureV1(
            session_id=self.session.session_id,
            researcher_id="researcher.local",
            captured_at=NOW,
            text=text,
        )

    def _handoff_paths(self) -> tuple[Path, ...]:
        assert self.ready.route_run_id is not None
        operational = ProjectOperationalLayout.at(StoreLayout.at(self.root))
        directory = (
            operational.runs
            / self.ready.route_run_id
            / "framing-team-handoffs"
            / "sha256"
        )
        return tuple(directory.glob("*.json")) if directory.is_dir() else ()

    def _head(self) -> str:
        return replay(StoreLayout.at(self.root)).head

    def test_open_team_and_honest_capability_fallback(self) -> None:
        head_before = self._head()
        unavailable = CodexFramingTeamCapabilityV1(
            team_surface="unavailable",
            lane_separation="unavailable",
            direct_user_capture="current_user_turn",
            fallback_reason="This host cannot create isolated advisory lanes.",
        )
        fallback = self.bridge.invoke(
            CodexFramingTeamOpenRequestV1(
                **self._delivery_binding(),
                session=self.session,
                capability=unavailable,
            )
        )
        self.assertEqual(fallback.outcome, "single_fallback", fallback)
        self.assertFalse(fallback.mutated)
        self.assertEqual(fallback.work_packet_hash, self.ready.work_packet_hash)
        assert fallback.framing_team is not None
        self.assertEqual(
            fallback.framing_team.reason,
            "This host cannot create isolated advisory lanes.",
        )
        self.assertIsNone(fallback.framing_team.team_plan_hash)
        self.assertIsNone(fallback.framing_team.team_plan)
        self.assertEqual(self._head(), head_before)

        opened = self._open_team()
        self.assertEqual(opened.outcome, "team_ready", opened)
        self.assertTrue(opened.mutated)
        assert opened.framing_team is not None
        assert opened.framing_team.team_plan is not None
        self.assertEqual(
            opened.framing_team.team_plan.execution_mode,
            "isolated_multi_agent",
        )
        self.assertEqual(opened.framing_team.team_plan.isolation_claim, "logical")
        assert opened.framing_team.team_plan_hash is not None
        authorization = read_framing_team_delivery_authorization(
            ProjectOperationalLayout.at(StoreLayout.at(self.root)),
            route_run_id=self._delivery_binding()["route_run_id"],
            work_packet_hash=self._delivery_binding()["work_packet_hash"],
            team_plan_hash=opened.framing_team.team_plan_hash,
        )
        self.assertEqual(authorization.source_agent_topology, "single")
        self.assertEqual(
            authorization.authorized_lane_ids,
            (
                "mentor",
                "collaborator_a",
                "collaborator_b",
                "research_worker",
            ),
        )
        self.assertEqual(authorization.delegated_packet_exposure_count, 4)
        self.assertEqual(
            authorization.worker_exposure_condition,
            "after_exact_terminal_handoff",
        )
        self.assertEqual(authorization.host_session_id, self.session.session_id)
        self.assertEqual(
            authorization.source_delivery_envelope_hash,
            self.ready.delivery_envelope_hash,
        )
        late_fallback = self.bridge.invoke(
            CodexFramingTeamOpenRequestV1(
                **self._delivery_binding(),
                session=self.session,
                capability=unavailable,
            )
        )
        self.assertEqual(late_fallback.outcome, "error", late_fallback)
        self.assertIn("cannot downgrade", late_fallback.diagnostics[0].message)
        self.assertEqual(self._head(), head_before)

    def test_panel_clear_user_turn_preserves_exact_text_and_one_handoff(self) -> None:
        panel_response = self._publish_panel()
        assert panel_response.framing_team is not None
        assert panel_response.framing_team.panel is not None
        assert panel_response.framing_team.panel_hash is not None
        panel = panel_response.framing_team.panel
        self.assertEqual(panel.mentor.agent_label, "mentor-agent")
        self.assertEqual(
            tuple(item.lane_id for item in panel.collaborators),
            ("collaborator_a", "collaborator_b"),
        )

        researcher_text = "继续导师路线，但把基准压缩到一个。"
        request = CodexFramingTeamUserTurnRequestV1(
            **self._delivery_binding(),
            panel_hash=panel_response.framing_team.panel_hash,
            session=self.session,
            capture=self._capture(researcher_text),
            interpretation=CodexFramingClearInterpretationV1(
                disposition="simplify",
                selected_lane_ids=("mentor", "collaborator_b"),
                synthesis_markdown=(
                    "The researcher chose the mentor direction with the binary "
                    "simplification."
                ),
                worker_brief=(
                    "Author one framing candidate with one exact benchmark and a "
                    "binary participation margin."
                ),
            ),
        )
        head_before = self._head()
        first = self.bridge.invoke(request)
        second = self.bridge.invoke(request)
        self.assertEqual(first.outcome, "handoff_ready", first)
        self.assertEqual(second, first)
        self.assertTrue(first.mutated)
        assert first.framing_team is not None
        assert first.framing_team.synthesis is not None
        self.assertEqual(
            first.framing_team.synthesis.researcher_text, researcher_text
        )
        self.assertEqual(
            first.framing_team.synthesis.capture_channel,
            "trusted_local_direct_user",
        )
        self.assertIsNotNone(first.framing_team.handoff_hash)
        self.assertIsNotNone(first.framing_team.handoff)
        self.assertEqual(len(self._handoff_paths()), 1)
        self.assertEqual(self._head(), head_before)

        different = self.bridge.invoke(
            request.model_copy(
                update={
                    "capture": self._capture("Use collaborator A instead."),
                    "interpretation": CodexFramingClearInterpretationV1(
                        disposition="continue",
                        selected_lane_ids=("collaborator_a",),
                        synthesis_markdown="Use collaborator A instead.",
                        worker_brief="Author collaborator A's framing.",
                    ),
                }
            )
        )
        self.assertEqual(different.outcome, "error", different)
        self.assertEqual(
            different.diagnostics[0].code,
            "codex_operational_integrity_error",
        )
        self.assertIn("terminal direction", different.diagnostics[0].message)
        self.assertEqual(len(self._handoff_paths()), 1)

        assert first.framing_team.handoff_hash is not None
        assert self.ready.candidate_logical_path is not None
        candidate_path = self.root / self.ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text("not yet a Transaction", encoding="utf-8")
        completion = self.bridge.invoke(
            CodexCompleteRequestV1(
                **self._delivery_binding(),
                framing_team_handoff_hash=first.framing_team.handoff_hash,
                framing_team_worker=CodexFramingWorkerObservationV1(
                    agent_label="worker.agent",
                    model_observation="gpt-5",
                ),
            )
        )
        self.assertEqual(completion.outcome, "error", completion)
        self.assertEqual(
            completion.diagnostics[0].code,
            "codex_candidate_transaction_invalid",
        )
        self.assertEqual(self._head(), head_before)

    def test_ambiguous_and_new_brief_stops_are_distinct_and_do_not_handoff(
        self,
    ) -> None:
        panel_response = self._publish_panel()
        assert panel_response.framing_team is not None
        assert panel_response.framing_team.panel_hash is not None
        head_before = self._head()

        ambiguous_text = "也许选第二个，但我不确定第二个指哪个。"
        ambiguous = self.bridge.invoke(
            CodexFramingTeamUserTurnRequestV1(
                **self._delivery_binding(),
                panel_hash=panel_response.framing_team.panel_hash,
                session=self.session,
                capture=self._capture(ambiguous_text),
                interpretation=CodexFramingAmbiguousInterpretationV1(
                    clarification_question=(
                        "你说的第二个，是 collaborator_a 还是 collaborator_b？"
                    )
                ),
            )
        )
        new_brief_text = "改成研究拍卖中的串谋，并加入实证估计。"
        new_brief = self.bridge.invoke(
            CodexFramingTeamUserTurnRequestV1(
                **self._delivery_binding(),
                panel_hash=panel_response.framing_team.panel_hash,
                session=self.session,
                capture=self._capture(new_brief_text),
                interpretation=CodexFramingNewBriefInterpretationV1(
                    reason="The request changes the question and leaves theory-only scope."
                ),
            )
        )

        self.assertEqual(ambiguous.outcome, "awaiting_clarification", ambiguous)
        self.assertEqual(new_brief.outcome, "new_brief_required", new_brief)
        assert ambiguous.framing_team is not None
        assert new_brief.framing_team is not None
        assert ambiguous.framing_team.stop is not None
        assert new_brief.framing_team.stop is not None
        self.assertEqual(
            ambiguous.framing_team.stop.researcher_text, ambiguous_text
        )
        self.assertEqual(new_brief.framing_team.stop.researcher_text, new_brief_text)
        self.assertNotEqual(
            ambiguous.framing_team.stop_hash, new_brief.framing_team.stop_hash
        )
        for result in (ambiguous.framing_team, new_brief.framing_team):
            self.assertIsNone(result.synthesis_hash)
            self.assertIsNone(result.handoff_hash)
        blocked_worker = self.bridge.invoke(
            CodexFramingTeamUserTurnRequestV1(
                **self._delivery_binding(),
                panel_hash=panel_response.framing_team.panel_hash,
                session=self.session,
                capture=self._capture("Actually continue with collaborator A."),
                interpretation=CodexFramingClearInterpretationV1(
                    disposition="continue",
                    selected_lane_ids=("collaborator_a",),
                    synthesis_markdown="Continue with collaborator A.",
                    worker_brief="Author collaborator A's framing.",
                ),
            )
        )
        self.assertEqual(blocked_worker.outcome, "error", blocked_worker)
        self.assertEqual(
            blocked_worker.diagnostics[0].code,
            "codex_operational_integrity_error",
        )
        self.assertEqual(self._handoff_paths(), ())
        self.assertEqual(self._head(), head_before)

    def _assert_inactive_disposition_has_no_handoff(
        self, disposition: str, expected: str
    ) -> None:
        panel_response = self._publish_panel()
        assert panel_response.framing_team is not None
        assert panel_response.framing_team.panel_hash is not None
        head_before = self._head()

        response = self.bridge.invoke(
            CodexFramingTeamUserTurnRequestV1(
                **self._delivery_binding(),
                panel_hash=panel_response.framing_team.panel_hash,
                session=self.session,
                capture=self._capture(f"Researcher says: {disposition}."),
                interpretation=CodexFramingClearInterpretationV1(
                    disposition=disposition,
                    synthesis_markdown=f"The researcher chose to {disposition}.",
                ),
            )
        )
        self.assertEqual(response.outcome, expected, response)
        assert response.framing_team is not None
        self.assertIsNotNone(response.framing_team.synthesis_hash)
        self.assertIsNone(response.framing_team.handoff_hash)
        self.assertIsNone(response.framing_team.handoff)

        blocked_worker = self.bridge.invoke(
            CodexFramingTeamUserTurnRequestV1(
                **self._delivery_binding(),
                panel_hash=panel_response.framing_team.panel_hash,
                session=self.session,
                capture=self._capture("Continue after all."),
                interpretation=CodexFramingClearInterpretationV1(
                    disposition="continue",
                    synthesis_markdown="Continue after all.",
                    worker_brief="Author a framing candidate.",
                ),
            )
        )
        self.assertEqual(blocked_worker.outcome, "error", blocked_worker)

        self.assertEqual(self._handoff_paths(), ())
        self.assertEqual(self._head(), head_before)

    def test_park_never_creates_worker_handoff(self) -> None:
        self._assert_inactive_disposition_has_no_handoff("park", "parked")

    def test_kill_never_creates_worker_handoff(self) -> None:
        self._assert_inactive_disposition_has_no_handoff("kill", "killed")

    def test_transport_recognizes_team_operations_and_rejects_session_mismatch(
        self,
    ) -> None:
        for operation in (
            "framing_team.open",
            "framing_team.publish_panel",
            "framing_team.apply_user_turn",
        ):
            with self.subTest(operation=operation):
                response = invoke_codex_bytes(
                    canonical_json_bytes({"operation": operation}),
                    bridge=self.bridge,
                )
                self.assertEqual(response.operation, operation)
                self.assertEqual(response.outcome, "error")
                self.assertEqual(
                    response.diagnostics[0].code,
                    "invalid_codex_bridge_request",
                )

        opened = self._open_team()
        self.assertEqual(opened.outcome, "team_ready", opened)
        assert opened.framing_team is not None
        assert opened.framing_team.team_plan_hash is not None
        wrong_panel_session = self.session.model_copy(
            update={"session_id": "different-codex-session"}
        )
        wrong_panel = self.bridge.invoke(
            CodexFramingTeamPanelRequestV1(
                **self._delivery_binding(),
                team_plan_hash=opened.framing_team.team_plan_hash,
                session=wrong_panel_session,
                mentor=CodexFramingLaneDraftV1(
                    agent_label="mentor-agent",
                    content_markdown="Mentor advice.",
                ),
                collaborator_a=CodexFramingLaneDraftV1(
                    agent_label="collaborator-a-agent",
                    content_markdown="Proposal A.",
                ),
                collaborator_b=CodexFramingLaneDraftV1(
                    agent_label="collaborator-b-agent",
                    content_markdown="Proposal B.",
                ),
            )
        )
        self.assertEqual(wrong_panel.outcome, "error", wrong_panel)
        self.assertIn("Codex session", wrong_panel.diagnostics[0].message)

        panel_response = self._publish_panel()
        assert panel_response.framing_team is not None
        assert panel_response.framing_team.panel_hash is not None
        valid = CodexFramingTeamUserTurnRequestV1(
            **self._delivery_binding(),
            panel_hash=panel_response.framing_team.panel_hash,
            session=self.session,
            capture=self._capture("Continue with the mentor direction."),
            interpretation=CodexFramingClearInterpretationV1(
                disposition="continue",
                selected_lane_ids=("mentor",),
                synthesis_markdown="Continue with the mentor direction.",
                worker_brief="Author the exact framing candidate.",
            ),
        ).model_dump(mode="json")
        valid["capture"]["session_id"] = "different-codex-session"
        invalid_bytes = canonical_json_bytes(valid)
        with self.assertRaisesRegex(ValueError, "different Codex session"):
            CODEX_BRIDGE_REQUEST_ADAPTER.validate_json(invalid_bytes, strict=True)
        mismatch = invoke_codex_bytes(invalid_bytes, bridge=self.bridge)
        self.assertEqual(mismatch.operation, "framing_team.apply_user_turn")
        self.assertEqual(mismatch.outcome, "error")
        self.assertEqual(
            mismatch.diagnostics[0].code, "invalid_codex_bridge_request"
        )
        self.assertIn("value_error", mismatch.diagnostics[0].message)
        self.assertEqual(self._handoff_paths(), ())

    def test_complete_rejects_bogus_handoff_before_reading_candidate(self) -> None:
        opened = self._open_team()
        self.assertEqual(opened.outcome, "team_ready", opened)
        assert self.ready.candidate_logical_path is not None
        candidate_path = self.root / self.ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text("not a Transaction", encoding="utf-8")
        head_before = self._head()

        missing = self.bridge.invoke(
            CodexCompleteRequestV1(**self._delivery_binding())
        )
        self.assertEqual(missing.outcome, "error", missing)
        self.assertIn("requires its exact worker handoff", missing.diagnostics[0].message)

        response = self.bridge.invoke(
            CodexCompleteRequestV1(
                **self._delivery_binding(),
                framing_team_handoff_hash="0" * 64,
                framing_team_worker=CodexFramingWorkerObservationV1(
                    agent_label="worker.agent",
                    model_observation="gpt-5",
                ),
            )
        )
        self.assertEqual(response.outcome, "error", response)
        self.assertFalse(response.mutated)
        self.assertEqual(
            response.diagnostics[0].code,
            "codex_operational_integrity_error",
        )
        self.assertIn("framing-team-handoffs", response.diagnostics[0].message)
        self.assertNotEqual(
            response.diagnostics[0].code,
            "codex_candidate_transaction_invalid",
        )
        self.assertEqual(
            candidate_path.read_text(encoding="utf-8"), "not a Transaction"
        )
        self.assertEqual(self._head(), head_before)

    def test_team_open_rejects_a_preexisting_staged_candidate(self) -> None:
        assert self.ready.route_run_id is not None
        assert self.ready.candidate_logical_path is not None
        transaction = phase5a_fixture.Phase5A2CodexBridgeTests._framing_transaction(
            self, self.ready.route_run_id
        )
        candidate_path = self.root / self.ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_bytes(canonical_json_bytes(transaction))
        staged = self.bridge.invoke(
            CodexCompleteRequestV1(
                **self._delivery_binding(),
                action="stage_only",
            )
        )
        self.assertEqual(staged.outcome, "staged", staged)

        opened = self._open_team()
        self.assertEqual(opened.outcome, "error", opened)
        self.assertIn("after a candidate was staged", opened.diagnostics[0].message)

    def test_tampered_team_sidecar_returns_strict_bridge_error(self) -> None:
        panel_response = self._publish_panel()
        assert panel_response.framing_team is not None
        assert panel_response.framing_team.panel_hash is not None
        binding = self._delivery_binding()
        operational = ProjectOperationalLayout.at(StoreLayout.at(self.root))
        panel_path = (
            operational.runs
            / binding["route_run_id"]
            / "framing-team-panels"
            / "sha256"
            / f"{panel_response.framing_team.panel_hash}.json"
        )
        panel_path.write_bytes(b"{}")

        response = self.bridge.invoke(
            CodexFramingTeamUserTurnRequestV1(
                **binding,
                panel_hash=panel_response.framing_team.panel_hash,
                session=self.session,
                capture=self._capture("Please clarify route A."),
                interpretation=CodexFramingAmbiguousInterpretationV1(
                    clarification_question="Do you mean collaborator A?"
                ),
            )
        )
        self.assertEqual(response.outcome, "error", response)
        self.assertEqual(
            response.diagnostics[0].code,
            "codex_operational_integrity_error",
        )

    def test_team_completion_records_worker_and_exact_handoff(self) -> None:
        panel_response = self._publish_panel()
        assert panel_response.framing_team is not None
        assert panel_response.framing_team.panel_hash is not None
        handoff_response = self.bridge.invoke(
            CodexFramingTeamUserTurnRequestV1(
                **self._delivery_binding(),
                panel_hash=panel_response.framing_team.panel_hash,
                session=self.session,
                capture=self._capture("Continue with the mentor direction."),
                interpretation=CodexFramingClearInterpretationV1(
                    disposition="continue",
                    selected_lane_ids=("mentor",),
                    synthesis_markdown="Continue with the mentor direction.",
                    worker_brief="Author the exact bounded framing candidate.",
                ),
            )
        )
        self.assertEqual(handoff_response.outcome, "handoff_ready", handoff_response)
        assert handoff_response.framing_team is not None
        assert handoff_response.framing_team.handoff_hash is not None
        assert self.ready.route_run_id is not None
        assert self.ready.candidate_logical_path is not None

        transaction = (
            phase5a_fixture.Phase5A2CodexBridgeTests._framing_transaction(
                self, self.ready.route_run_id
            )
        )
        candidate_path = self.root / self.ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        worker_agent_label = "worker." + ("a" * 256)
        completion_request = CodexCompleteRequestV1(
            **self._delivery_binding(),
            framing_team_handoff_hash=handoff_response.framing_team.handoff_hash,
            framing_team_worker=CodexFramingWorkerObservationV1(
                agent_label=worker_agent_label,
                model_observation="gpt-5",
            ),
        )
        stage_only = self.bridge.invoke(
            completion_request.model_copy(update={"action": "stage_only"})
        )
        self.assertEqual(stage_only.outcome, "error", stage_only)
        self.assertIn("requires stage_and_commit", stage_only.diagnostics[0].message)

        invalid_candidate = transaction.model_dump(mode="json")
        invalid_relation = invalid_candidate["operations"][2]["relation"]
        invalid_relation["source"], invalid_relation["target"] = (
            invalid_relation["target"],
            invalid_relation["source"],
        )
        candidate_path.write_bytes(canonical_json_bytes(invalid_candidate))
        rejected = self.bridge.invoke(completion_request)
        self.assertEqual(rejected.outcome, "error", rejected)
        self.assertTrue(rejected.mutated)
        reopened = self._open_team()
        self.assertEqual(reopened.outcome, "team_ready", reopened)
        assert reopened.framing_team is not None
        self.assertEqual(
            reopened.framing_team.team_plan_hash,
            handoff_response.framing_team.team_plan_hash,
        )

        different_worker = self.bridge.invoke(
            completion_request.model_copy(
                update={
                    "framing_team_worker": CodexFramingWorkerObservationV1(
                        agent_label="different.worker",
                        model_observation="gpt-5",
                    )
                }
            )
        )
        self.assertEqual(different_worker.outcome, "error", different_worker)
        self.assertFalse(different_worker.mutated)
        self.assertIn(
            "different research worker", different_worker.diagnostics[0].message
        )

        candidate_path.write_bytes(canonical_json_bytes(transaction))
        completed = self.bridge.invoke(completion_request)
        self.assertEqual(completed.outcome, "committed", completed)
        assert completed.completion is not None
        store = ContentAddressedOperationalStore(
            self.root,
            ProjectOperationalLayout.at(StoreLayout.at(self.root)).runs
            / self.ready.route_run_id,
        )
        receipt = HostOperationReceiptV1.model_validate_json(
            store.read_bytes("host-receipts", completed.completion.host_receipt_hash),
            strict=True,
        )
        self.assertEqual(receipt.tool_identities, ("openai.codex",))
        binding = read_framing_worker_completion_binding(
            ProjectOperationalLayout.at(StoreLayout.at(self.root)),
            route_run_id=self.ready.route_run_id,
            work_packet_hash=self.ready.work_packet_hash,
            completion_operation_key=receipt.operation_key,
            require_current_head=False,
        )
        self.assertEqual(
            binding.worker_handoff_hash,
            handoff_response.framing_team.handoff_hash,
        )
        self.assertEqual(binding.worker_agent_label, worker_agent_label)
        self.assertEqual(binding.worker_model_observation, "gpt-5")
        self.assertEqual(binding.delivery_envelope_hash, receipt.delivery_envelope_hash)
        self.assertEqual(binding.candidate_digest, completed.completion.candidate_digest)
        activation = read_framing_worker_activation(
            ProjectOperationalLayout.at(StoreLayout.at(self.root)),
            route_run_id=self.ready.route_run_id,
            work_packet_hash=self.ready.work_packet_hash,
            handoff_hash=handoff_response.framing_team.handoff_hash,
            require_current_head=False,
        )
        self.assertEqual(activation.worker_agent_label, worker_agent_label)
        self.assertEqual(activation.worker_model_observation, "gpt-5")
        self.assertEqual(self.bridge.invoke(completion_request), completed)


if __name__ == "__main__":
    unittest.main()
