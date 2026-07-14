from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.machine.dispatcher import MachineDispatcher
from econ_theorist.machine.lifecycle import derive_all_run_execution_views
from econ_theorist.machine.models import (
    DiscoveryGrantV1,
    MachineRequestV1,
    NavigationPlanV1,
    ResumeDescriptorV1,
    RunInputBriefV1,
)
from econ_theorist.machine.resources import NAVIGATION_REGISTRY_V2_HASH
from econ_theorist.machine.operational import ProjectOperationalLayout
from econ_theorist.machine.resume import ResumeDescriptorError, derive_resume_descriptor
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.replay import replay


class Phase5AResumeDescriptorTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.anchor = Path(temporary.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        self.local_home = self.anchor / "local-operations"
        self.grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
        )
        self.dispatcher = MachineDispatcher(
            preproject_operational_home=self.local_home
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

    def _open_run(self):
        initialized = self.dispatcher.dispatch(
            self._request(
                "project.bind_or_initialize",
                operation_key="initialize.resume-fixture",
                parameters={
                    "initialize": True,
                    "project_name": "Fresh session recovery fixture",
                },
            )
        )
        self.assertEqual(initialized.outcome, "ok", initialized)
        brief = RunInputBriefV1(
            project_id=initialized.project_id,
            base_head=initialized.head,
            requested_scope="Frame one bounded theory question.",
            framing_intent="How does costly search change on a graph?",
            privacy="project_private",
            compartments=("project_research",),
            actor_role="scientific_agent",
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
        self.assertEqual(planned.result["outcome"], "unique_next")
        opened = self.dispatcher.dispatch(
            self._request(
                "run.open_or_resume",
                operation_key="open.resume-fixture",
                parameters={
                    "candidate": planned.result["candidates"][0],
                    "run_input_brief": brief.model_dump(mode="json"),
                },
            )
        )
        self.assertEqual(opened.outcome, "ok", opened)
        return opened

    def test_fresh_dispatcher_resumes_from_navigation_response_only(self) -> None:
        opened = self._open_run()

        # Simulate a new IDE/model process with no prior request objects or
        # dispatcher memory.  The active run takes precedence over a missing
        # navigation brief and returns its exact persisted resume inputs.
        fresh = MachineDispatcher(preproject_operational_home=self.local_home)
        navigation_response = fresh.dispatch(
            self._request("navigation.plan_next")
        )
        self.assertEqual(navigation_response.outcome, "ok", navigation_response)
        plan = NavigationPlanV1.model_validate_json(
            canonical_json_bytes(navigation_response.result), strict=True
        )
        self.assertEqual(plan.outcome, "resume_required")
        self.assertEqual(plan.active_run_ids, (opened.result["route_run_id"],))
        self.assertEqual(len(plan.resume_descriptors), 1)
        descriptor = plan.resume_descriptors[0]
        self.assertEqual(descriptor.next_action, "run.open_or_resume")
        self.assertEqual(
            descriptor.work_packet_hash,
            opened.result["work_packet_hash"],
        )
        self.assertEqual(
            descriptor.candidate_logical_path,
            opened.result["candidate_logical_path"],
        )

        # Build the next request exclusively from the returned descriptor.
        resumed = fresh.dispatch(
            self._request(
                descriptor.next_action,
                operation_key="resume.from-fresh-response",
                parameters={
                    "candidate": descriptor.navigation_candidate.model_dump(
                        mode="json"
                    ),
                    "run_input_brief": (
                        descriptor.run_input_brief.model_dump(mode="json")
                        if descriptor.run_input_brief is not None
                        else None
                    ),
                },
            )
        )
        self.assertEqual(resumed.outcome, "ok", resumed)
        self.assertEqual(resumed.result["status"], "resumed")
        self.assertEqual(
            resumed.result["work_packet_hash"], descriptor.work_packet_hash
        )

        inspected = fresh.dispatch(self._request("project.inspect"))
        nested = NavigationPlanV1.model_validate_json(
            canonical_json_bytes(inspected.result["navigation"]), strict=True
        )
        self.assertEqual(nested.resume_descriptors, plan.resume_descriptors)

    def test_descriptor_rejects_retargeting_and_corruption_requires_repair(self) -> None:
        opened = self._open_run()
        fresh = MachineDispatcher(preproject_operational_home=self.local_home)
        planned = fresh.dispatch(self._request("navigation.plan_next"))
        descriptor_payload = dict(planned.result["resume_descriptors"][0])
        descriptor_payload["candidate_logical_path"] = (
            ".econ-theorist/staging/a-different-run/candidate.json"
        )
        with self.assertRaises(ValueError):
            ResumeDescriptorV1.model_validate_json(
                canonical_json_bytes(descriptor_payload), strict=True
            )

        binding_path = (
            self.root
            / ".econ-theorist"
            / "operational"
            / "v1"
            / "runs"
            / opened.result["route_run_id"]
            / "packet-binding.json"
        )
        binding_path.write_bytes(b"{}")
        repaired = MachineDispatcher(
            preproject_operational_home=self.local_home
        ).dispatch(self._request("navigation.plan_next"))
        self.assertEqual(repaired.outcome, "repair_required", repaired)
        self.assertEqual(repaired.result["outcome"], "repair_required")
        self.assertEqual(repaired.result["resume_descriptors"], [])
        self.assertEqual(
            repaired.result["active_run_ids"],
            [opened.result["route_run_id"]],
        )

    def test_incomplete_run_from_inactive_navigation_policy_requires_repair(self) -> None:
        opened = self._open_run()
        binding_path = (
            self.root
            / ".econ-theorist"
            / "operational"
            / "v1"
            / "runs"
            / opened.result["route_run_id"]
            / "navigation-candidate.json"
        )
        candidate = json.loads(binding_path.read_text(encoding="utf-8"))
        candidate["key"]["navigation_registry_hash"] = NAVIGATION_REGISTRY_V2_HASH
        candidate["candidate_digest"] = sha256_digest(
            canonical_json_bytes(candidate["key"])
        )
        binding_path.write_bytes(canonical_json_bytes(candidate))

        layout = StoreLayout.at(self.root)
        snapshot = replay(layout)
        view = next(
            item
            for item in derive_all_run_execution_views(layout, snapshot)
            if item.route_run_id == opened.result["route_run_id"]
        )
        with self.assertRaisesRegex(
            ResumeDescriptorError, "inactive navigation policy"
        ):
            derive_resume_descriptor(
                layout,
                ProjectOperationalLayout.at(layout),
                view,
            )

        inspected = MachineDispatcher(
            preproject_operational_home=self.local_home
        ).dispatch(self._request("navigation.plan_next"))
        self.assertEqual(inspected.outcome, "repair_required", inspected)
        self.assertEqual(inspected.result["outcome"], "repair_required")
        self.assertEqual(inspected.result["resume_descriptors"], [])
        self.assertEqual(
            inspected.result["active_run_ids"],
            [opened.result["route_run_id"]],
        )


if __name__ == "__main__":
    unittest.main()
