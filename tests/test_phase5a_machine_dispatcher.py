from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import os
import subprocess
import sys

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.machine.dispatcher import (
    MachineDispatcher,
    TrustedHostCompletionObservation,
    TrustedHostDeliverySession,
    error_response,
)
from econ_theorist.machine.egress import _events
from econ_theorist.machine.models import (
    CapabilityV1,
    CapabilityReceiptV1,
    DiscoveryGrantV1,
    MachineRequestV1,
    RunInputBriefV1,
)
from econ_theorist.machine_cli import invoke_machine_bytes
from econ_theorist.models import Actor
from econ_theorist.compatibility import probe_project_root
from econ_theorist.runtime.faults import FAULT_MODE_ENV, FAULT_POINT_ENV
from econ_theorist.runtime.layout import StoreLayout
from econ_theorist.runtime.replay import CandidateValidationError
from econ_theorist.machine.operational import ProjectOperationalLayout


class Phase5AMachineDispatcherTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        self.local_home = self.anchor / "local-operations"
        self.actor = Actor(kind="agent", actor_id="scientific_agent")
        self.grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
        )
        self.dispatcher = MachineDispatcher(
            preproject_operational_home=self.local_home,
        )

    def _request(
        self,
        operation: str,
        *,
        operation_key: str | None = None,
        parameters: dict | None = None,
    ) -> MachineRequestV1:
        return MachineRequestV1(
            operation=operation,  # type: ignore[arg-type]
            operation_key=operation_key,
            project_root=str(self.root),
            discovery_grant=self.grant,
            parameters=parameters or {},
        )

    def _initialize(self):
        request = self._request(
            "project.bind_or_initialize",
            operation_key="initialize.dispatcher",
            parameters={
                "initialize": True,
                "project_name": "Dispatcher fixture",
            },
        )
        response = self.dispatcher.dispatch(request)
        self.assertEqual(response.outcome, "ok", response)
        self.assertEqual(response.result["status"], "initialized")
        return request, response

    def _plan_and_open(self):
        _, initialized = self._initialize()
        actor = self.actor
        brief = RunInputBriefV1(
            project_id=initialized.project_id,
            base_head=initialized.head,
            requested_scope="Frame one theory question and its benchmarks.",
            framing_intent="How does costly search change on a graph?",
            privacy="project_private",
            compartments=("project_research",),
            actor_role=actor.actor_id,
        )
        navigation = self.dispatcher.dispatch(
            self._request(
                "navigation.plan_next",
                parameters={
                    "budget_units": 10_000,
                    "run_input_brief": brief.model_dump(mode="json"),
                },
            )
        )
        self.assertEqual(navigation.outcome, "ok", navigation)
        self.assertEqual(navigation.result["outcome"], "unique_next")
        candidate = navigation.result["candidates"][0]
        request = self._request(
            "run.open_or_resume",
            operation_key="open.dispatcher",
            parameters={
                "candidate": candidate,
                "run_input_brief": brief.model_dump(mode="json"),
            },
        )
        opened = self.dispatcher.dispatch(request)
        self.assertEqual(opened.outcome, "ok", opened)
        return brief, candidate, request, opened

    def test_invalid_transport_still_returns_one_strict_response(self) -> None:
        response = invoke_machine_bytes(b"{not-json", dispatcher=self.dispatcher)
        self.assertEqual(response.outcome, "error")
        self.assertEqual(response.operation, "operation.inspect")
        self.assertEqual(response.diagnostics[0].code, "invalid_machine_request")
        reparsed = type(response).model_validate_json(
            canonical_json_bytes(response), strict=True
        )
        self.assertEqual(reparsed, response)

    def test_candidate_validation_details_survive_machine_error_projection(
        self,
    ) -> None:
        request = self._request("project.inspect")
        details = {
            "validation_stage": "canonical_candidate_preflight",
            "rule_id": "framing.primitive_paths",
            "repairable": True,
            "retry_action": "edit_declared_candidate_and_retry_same_request",
            "repair_hint": "Close the exact path without inventing a connection.",
            "issue_count": 1,
            "truncated": False,
            "issues": [
                {
                    "location": ["causal_chain", 0, "force_ids", 0],
                    "type": "causal_step_not_on_force_path",
                    "step_number": 1,
                    "step_source_node_id": "node.source",
                    "step_target_node_id": "node.target",
                    "force_id": "force.one",
                    "force_source_node_id": "node.force_source",
                    "force_margin_node_id": "node.force_margin",
                    "force_target_node_id": "node.force_target",
                }
            ],
        }

        response = error_response(
            request,
            CandidateValidationError(
                "causal_force_binding: one exact path issue",
                diagnostic_details=details,
            ),
        )

        self.assertEqual(response.outcome, "error")
        self.assertEqual(response.diagnostics[0].code, "CandidateValidationError")
        self.assertEqual(response.diagnostics[0].details, details)
        self.assertNotIn("traceback", response.model_dump_json().lower())

    def test_untrusted_or_unbounded_exception_details_are_not_projected(
        self,
    ) -> None:
        request = self._request("project.inspect")
        arbitrary = RuntimeError("bounded public message")
        arbitrary.diagnostic_details = {"secret_path": str(self.root)}  # type: ignore[attr-defined]

        unrelated = error_response(request, arbitrary)
        malformed = error_response(
            request,
            CandidateValidationError(
                "candidate rejected",
                diagnostic_details={"unexpected": object()},
            ),
        )

        self.assertEqual(unrelated.diagnostics[0].details, {})
        self.assertEqual(malformed.diagnostics[0].details, {})
        self.assertNotIn(str(self.root), unrelated.model_dump_json())

    def test_cli_stdout_is_exactly_one_machine_response(self) -> None:
        environment = os.environ.copy()
        source = Path(__file__).resolve().parents[1] / "src"
        environment["PYTHONPATH"] = str(source)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from econ_theorist.cli import main; "
                    "raise SystemExit(main(['machine','invoke','--request','-']))"
                ),
            ],
            input=b"{not-json",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout.count(b"\n"), 1)
        parsed = invoke_machine_bytes(result.stdout.rstrip(b"\n"))
        # Parsing the response as a request must fail; validate against the
        # response schema directly and confirm there was no extra output.
        from econ_theorist.machine.models import MachineResponseV1

        response = MachineResponseV1.model_validate_json(
            result.stdout.rstrip(b"\n"), strict=True
        )
        self.assertEqual(response.diagnostics[0].code, "invalid_machine_request")
        self.assertEqual(parsed.outcome, "error")

    def test_initialize_and_open_are_exactly_idempotent(self) -> None:
        init_request, initialized = self._initialize()
        self.assertEqual(self.dispatcher.dispatch(init_request), initialized)

        actor = self.actor
        brief = RunInputBriefV1(
            project_id=initialized.project_id,
            base_head=initialized.head,
            requested_scope="Frame one bounded question.",
            framing_intent="What mechanism changes search incentives?",
            privacy="project_private",
            compartments=("project_research",),
            actor_role=actor.actor_id,
        )
        planned = self.dispatcher.dispatch(
            self._request(
                "navigation.plan_next",
                parameters={
                    "budget_units": 10_000,
                    "run_input_brief": brief.model_dump(mode="json"),
                },
            )
        )
        candidate = planned.result["candidates"][0]
        open_request = self._request(
            "run.open_or_resume",
            operation_key="open.dispatcher",
            parameters={
                "candidate": candidate,
                "run_input_brief": brief.model_dump(mode="json"),
            },
        )
        first = self.dispatcher.dispatch(open_request)
        second = self.dispatcher.dispatch(open_request)
        self.assertEqual(first, second)
        self.assertEqual(first.result["status"], "opened")

        cross_host = self.dispatcher.dispatch(
            open_request.model_copy(update={"operation_key": "open.other-host"})
        )
        self.assertEqual(cross_host.result["status"], "resumed")
        self.assertEqual(
            cross_host.result["work_packet_hash"],
            first.result["work_packet_hash"],
        )

    def test_exact_initialization_retry_recovers_orphan_genesis(self) -> None:
        request = self._request(
            "project.bind_or_initialize",
            operation_key="initialize.crash-retry",
            parameters={
                "initialize": True,
                "project_name": "Crash recovery fixture",
            },
        )
        with patch.dict(
            "os.environ",
            {
                FAULT_POINT_ENV: "after_transaction_installation",
                FAULT_MODE_ENV: "raise",
            },
        ):
            interrupted = self.dispatcher.dispatch(request)
        self.assertEqual(interrupted.outcome, "error")
        self.assertEqual(
            probe_project_root(self.root).classification, "recovery_required"
        )

        recovered = self.dispatcher.dispatch(request)
        self.assertEqual(recovered.outcome, "ok", recovered)
        self.assertEqual(recovered.result["status"], "initialized")
        self.assertEqual(
            probe_project_root(self.root).classification, "valid_existing"
        )

    def test_inspection_is_read_only_and_operation_inspect_does_not_ensure(self) -> None:
        self._initialize()
        before = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        inspection = self.dispatcher.dispatch(
            self._request("project.inspect", parameters={"budget_units": 10_000})
        )
        self.assertEqual(inspection.outcome, "ok")
        self.assertEqual(
            inspection.result["navigation"]["outcome"], "repair_required"
        )
        # Framing requires an explicit RunInputBrief, but inspection itself is
        # a valid strict response and must not mutate the project.
        after = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, after)

        absent = self.dispatcher.dispatch(
            self._request(
                "operation.inspect",
                parameters={"operation_key": "never.used"},
            )
        )
        self.assertEqual(absent.outcome, "ok")
        self.assertEqual(absent.result["status"], "absent")
        final = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(before, final)

    def test_delivery_never_replays_packet_bytes(self) -> None:
        _, _, _, opened = self._plan_and_open()
        capability = CapabilityReceiptV1(
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            adapter_version="1.0",
            execution_class="local",
            technically_accessible_roots=(str(self.root),),
            model_tool_isolation="verified",
            trusted_human_channel="verified",
            capabilities=tuple(
                CapabilityV1(
                    capability_id=identifier,
                    available=True,
                    required=True,
                    evidence="trusted test adapter",
                )
                for identifier in (
                    "python_runtime",
                    "structured_process_invocation",
                    "single_agent_topology",
                )
            ),
            observed_at="2026-07-13T00:00:03Z",
        )
        plan_response = self.dispatcher.dispatch(
            self._request(
                "egress.plan",
                parameters={
                    "route_run_id": opened.result["route_run_id"],
                    "work_packet_hash": opened.result["work_packet_hash"],
                    "capability": capability.model_dump(mode="json"),
                    "host_product": "test-host",
                    "host_version": "1.0",
                    "adapter_id": "generic.test",
                    "provider": "local-runtime",
                    "model": "local-model",
                    "execution_class": "local",
                },
            )
        )
        self.assertEqual(plan_response.outcome, "ok", plan_response)
        request = self._request(
            "packet.deliver",
            operation_key="deliver.dispatcher",
            parameters={
                "route_run_id": opened.result["route_run_id"],
                "work_packet_hash": opened.result["work_packet_hash"],
                "plan": plan_response.result,
            },
        )
        untrusted = self.dispatcher.dispatch(
            request.model_copy(update={"operation_key": "deliver.untrusted"})
        )
        self.assertEqual(untrusted.outcome, "unsupported_host", untrusted)
        self.assertNotIn("work_packet", untrusted.result)

        local_request = request.model_copy(
            update={
                "operation_key": "deliver.local-self-use",
                "parameters": {
                    **request.parameters,
                    "capability": capability.model_dump(mode="json"),
                },
            }
        )
        local_delivery = self.dispatcher.dispatch(local_request)
        self.assertEqual(local_delivery.outcome, "ok", local_delivery)
        self.assertIsNotNone(local_delivery.result["work_packet"])

        local_finish = self.dispatcher.dispatch(
            self._request(
                "host.finish",
                operation_key="finish.local-self-use",
                parameters={
                    "route_run_id": opened.result["route_run_id"],
                    "work_packet_hash": opened.result["work_packet_hash"],
                    "delivery_envelope_hash": local_delivery.result[
                        "delivery_envelope_hash"
                    ],
                    "completion_status": "cancelled",
                    "warnings": ["local_fixture_cancelled"],
                },
            )
        )
        self.assertEqual(local_finish.outcome, "blocked", local_finish)
        self.assertEqual(local_finish.result["status"], "recorded_failure")

        delivery_session = TrustedHostDeliverySession(
            operation_key="deliver.dispatcher",
            adapter_id="generic.test",
            host_session_id="session.test",
            fresh_session=True,
            cross_run_memory_disabled=True,
        )
        trusted_dispatcher = MachineDispatcher(
            host_capabilities={capability.adapter_id: capability},
            trusted_clock=lambda: "2026-07-13T00:00:04Z",
            delivery_sessions={delivery_session.operation_key: delivery_session},
            preproject_operational_home=self.local_home,
        )
        delivered = trusted_dispatcher.dispatch(request)
        self.assertEqual(delivered.outcome, "ok", delivered)
        self.assertIsNotNone(delivered.result["work_packet"])

        inspected = self.dispatcher.dispatch(
            self._request(
                "operation.inspect",
                parameters={"operation_key": "deliver.dispatcher"},
            )
        )
        inspected_delivery = inspected.result["response"]
        self.assertEqual(
            inspected_delivery["result"]["status"],
            "unknown_possible_egress",
        )
        self.assertIsNone(inspected_delivery["result"]["work_packet"])

        finish_request = self._request(
            "host.finish",
            operation_key="finish.dispatcher",
            parameters={
                "route_run_id": opened.result["route_run_id"],
                "work_packet_hash": opened.result["work_packet_hash"],
                "delivery_envelope_hash": delivered.result[
                    "delivery_envelope_hash"
                ],
            },
        )
        observation = TrustedHostCompletionObservation(
            operation_key="finish.dispatcher",
            delivery_envelope_hash=delivered.result["delivery_envelope_hash"],
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            adapter_version="1.0",
            provider="local-runtime",
            model="local-model",
            reasoning_class="not_exposed",
            completion_status="failed_no_effect",
            warnings=("host_cancelled",),
        )
        completion_dispatcher = MachineDispatcher(
            host_capabilities={capability.adapter_id: capability},
            trusted_clock=lambda: "2026-07-13T00:00:05Z",
            completion_observations={observation.operation_key: observation},
            preproject_operational_home=self.local_home,
        )
        finished = completion_dispatcher.dispatch(finish_request)
        self.assertEqual(finished.outcome, "blocked", finished)
        self.assertEqual(finished.result["status"], "recorded_failure")
        self.assertEqual(completion_dispatcher.dispatch(finish_request), finished)

        retry = trusted_dispatcher.dispatch(request)
        self.assertEqual(retry.outcome, "conflict")
        self.assertEqual(retry.result["status"], "unknown_possible_egress")
        self.assertIsNone(retry.result["work_packet"])

    def test_delivery_crash_retry_keeps_original_envelope_for_host_finish(self) -> None:
        _, _, _, opened = self._plan_and_open()
        capability = CapabilityReceiptV1(
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            adapter_version="1.0",
            execution_class="local",
            technically_accessible_roots=(str(self.root),),
            model_tool_isolation="verified",
            trusted_human_channel="verified",
            capabilities=tuple(
                CapabilityV1(
                    capability_id=identifier,
                    available=True,
                    required=True,
                    evidence="trusted test adapter",
                )
                for identifier in (
                    "python_runtime",
                    "structured_process_invocation",
                    "single_agent_topology",
                )
            ),
            observed_at="2026-07-13T00:00:03Z",
        )
        plan_response = self.dispatcher.dispatch(
            self._request(
                "egress.plan",
                parameters={
                    "route_run_id": opened.result["route_run_id"],
                    "work_packet_hash": opened.result["work_packet_hash"],
                    "capability": capability.model_dump(mode="json"),
                    "host_product": "test-host",
                    "host_version": "1.0",
                    "adapter_id": "generic.test",
                    "provider": "local-runtime",
                    "model": "local-model",
                    "execution_class": "local",
                },
            )
        )
        request = self._request(
            "packet.deliver",
            operation_key="deliver.crash-after-start",
            parameters={
                "route_run_id": opened.result["route_run_id"],
                "work_packet_hash": opened.result["work_packet_hash"],
                "plan": plan_response.result,
                "capability": capability.model_dump(mode="json"),
            },
        )

        with patch.dict(
            "os.environ",
            {
                FAULT_POINT_ENV: "after_delivery_started",
                FAULT_MODE_ENV: "raise",
            },
        ):
            interrupted = self.dispatcher.dispatch(request)
        self.assertEqual(interrupted.outcome, "error", interrupted)

        plan_hash = sha256_digest(canonical_json_bytes(plan_response.result))
        operational = ProjectOperationalLayout.at(StoreLayout.at(self.root))
        starts = [
            event
            for _, event in _events(operational, f"local_{plan_hash[:48]}")
            if event.event == "delivery_started"
            and event.operation_key == request.operation_key
        ]
        self.assertEqual(len(starts), 1)
        original_envelope_hash = starts[0].payload_hash
        self.assertIsNotNone(original_envelope_hash)

        recovered = self.dispatcher.dispatch(request)
        self.assertEqual(recovered.outcome, "conflict", recovered)
        self.assertEqual(recovered.result["status"], "unknown_possible_egress")
        self.assertEqual(
            recovered.result["delivery_envelope_hash"], original_envelope_hash
        )
        self.assertIsNone(recovered.result["work_packet"])
        self.assertEqual(self.dispatcher.dispatch(request), recovered)

        finished = self.dispatcher.dispatch(
            self._request(
                "host.finish",
                operation_key="finish.crash-after-start",
                parameters={
                    "route_run_id": opened.result["route_run_id"],
                    "work_packet_hash": opened.result["work_packet_hash"],
                    "delivery_envelope_hash": original_envelope_hash,
                    "completion_status": "cancelled",
                    "warnings": ["delivery_response_lost"],
                },
            )
        )
        self.assertEqual(finished.outcome, "blocked", finished)
        self.assertEqual(finished.result["status"], "recorded_failure")


if __name__ == "__main__":
    unittest.main()
