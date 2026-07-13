from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.machine.binding import bind_or_initialize_project
from econ_theorist.machine.lifecycle import derive_all_run_execution_views
from econ_theorist.machine.models import (
    DiagnosticV1,
    DiscoveryGrantV1,
    MachineRequestV1,
    MachineResponseV1,
    RunInputBriefV1,
)
from econ_theorist.machine.navigation import plan_next
from econ_theorist.machine.operational import (
    OperationJournal,
    OperationKeyConflict,
    LockedOperation,
    OperationalError,
    PreProjectOperationalLayout,
    ProjectOperationalLayout,
)
from econ_theorist.machine.packets import read_work_packet
from econ_theorist.machine.resources import (
    HOST_MANIFEST_V1_HASH,
    NAVIGATION_REGISTRY_V1_HASH,
    load_host_manifest,
    load_navigation_registry,
)
from econ_theorist.machine.run_service import open_or_resume_run
from econ_theorist.models import Actor
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.replay import replay
from econ_theorist.runs import candidate_path


class Phase5AMachineCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        self.operational_home = self.anchor / "local-operations"
        self.grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
        )

    def _initialize(self):
        return bind_or_initialize_project(
            self.root,
            discovery_grant=self.grant,
            initialize=True,
            project_name="Machine facade test",
            actor_id="human.owner",
            operation_key="initialize.test",
            reserved_at="2026-07-13T00:00:00Z",
            operational_home=self.operational_home,
        )

    def test_pinned_machine_resources_cover_all_active_routes(self) -> None:
        navigation = load_navigation_registry()
        self.assertEqual(len(navigation.routes), 34)
        self.assertEqual(
            sha256_digest(canonical_json_bytes(navigation)),
            NAVIGATION_REGISTRY_V1_HASH,
        )
        manifest = load_host_manifest()
        self.assertEqual(
            sha256_digest(canonical_json_bytes(manifest)), HOST_MANIFEST_V1_HASH
        )
        surface = {
            item["operation"]: item["surface"] for item in manifest["operations"]
        }
        self.assertEqual(surface["approval.issue"], "trusted_human_only")
        self.assertEqual(surface["decide.raw"], "excluded_from_official_adapter")

    def test_operation_key_is_exactly_bound_and_replayed(self) -> None:
        preproject = PreProjectOperationalLayout.for_project(
            self.root, operational_home=self.operational_home
        )
        journal = OperationJournal.for_preproject(preproject)
        request = MachineRequestV1(
            operation="bootstrap.verify",
            operation_key="verify.once",
            parameters={"engine_manifest_hash": "a" * 64},
        )
        digest = sha256_digest(canonical_json_bytes(request))
        response = MachineResponseV1(
            operation=request.operation,
            request_digest=digest,
            outcome="ok",
            mutated=True,
            result={"verified": True},
        )
        with journal.locked("verify.once") as operation:
            state = operation.reserve(request)
            self.assertIsNone(state.response)
            completed = operation.complete(response)
            self.assertEqual(completed.response, response)
        with journal.locked("verify.once") as operation:
            replayed = operation.reserve(request)
            self.assertEqual(replayed.response, response)
            with self.assertRaises(OperationKeyConflict):
                operation.reserve(
                    request.model_copy(update={"parameters": {"changed": True}})
                )

    def test_operation_journal_recovers_both_publication_crash_windows(self) -> None:
        preproject = PreProjectOperationalLayout.for_project(
            self.root, operational_home=self.operational_home
        )
        journal = OperationJournal.for_preproject(preproject)
        request = MachineRequestV1(
            operation="bootstrap.verify",
            operation_key="verify.crash-window",
            parameters={"fixture": True},
        )
        with journal.locked("verify.crash-window") as operation:
            with patch.object(
                LockedOperation,
                "_append_event",
                side_effect=OperationalError("crash after reservation"),
            ):
                with self.assertRaises(OperationalError):
                    operation.reserve(request)

        with journal.locked("verify.crash-window") as operation:
            recovered = operation.reserve(request)
            self.assertIsNone(recovered.response)
            response = MachineResponseV1(
                operation=request.operation,
                request_digest=sha256_digest(canonical_json_bytes(request)),
                outcome="ok",
                mutated=True,
                result={"verified": True},
            )
            with patch.object(
                LockedOperation,
                "_append_event",
                side_effect=OperationalError("crash after terminal"),
            ):
                with self.assertRaises(OperationalError):
                    operation.complete(response)

        terminal = journal.inspect("verify.crash-window")
        self.assertIsNotNone(terminal)
        assert terminal is not None
        self.assertEqual(terminal.response, response)
        with journal.locked("verify.crash-window") as operation:
            replayed = operation.reserve(request)
            self.assertEqual(replayed.response, response)

    def test_bind_initializes_once_and_existing_bind_is_read_only(self) -> None:
        first = self._initialize()
        self.assertEqual(first.status, "initialized")
        self.assertTrue(first.mutated)
        layout = StoreLayout.at(self.root)
        before = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        second = bind_or_initialize_project(
            self.root,
            discovery_grant=self.grant,
            initialize=True,
            project_name="Machine facade test",
            actor_id="human.owner",
            operation_key="another.request",
            reserved_at="2026-07-13T00:00:01Z",
            operational_home=self.operational_home,
        )
        after = {
            path.relative_to(self.root).as_posix(): path.read_bytes()
            for path in self.root.rglob("*")
            if path.is_file()
        }
        self.assertEqual(second.status, "bound")
        self.assertFalse(second.mutated)
        self.assertEqual(before, after)
        self.assertEqual(len(replay(layout).chain), 1)

    def test_plan_open_resume_and_packet_are_host_neutral(self) -> None:
        binding = self._initialize()
        layout = StoreLayout.at(self.root)
        snapshot = replay(layout)
        actor = Actor(kind="agent", actor_id="scientific_writer")
        brief = RunInputBriefV1(
            project_id=snapshot.project_id,
            base_head=snapshot.head,
            requested_scope="Frame one theory question and its benchmarks.",
            framing_intent="How does costly search change when information travels on a graph?",
            privacy="project_private",
            compartments=("project_research",),
            actor_role=actor.actor_id,
        )
        plan = plan_next(
            layout,
            snapshot,
            actor=actor,
            compartments=("project_research",),
            privacy_clearance="project_private",
            budget_units=10_000,
            run_input_brief=brief,
        )
        self.assertEqual(plan.outcome, "unique_next", plan)
        self.assertEqual(len(plan.candidates), 1)
        candidate = plan.candidates[0]
        self.assertEqual(candidate.key.route_id, "frame.question_and_benchmarks")

        operational = ProjectOperationalLayout.at(layout)
        opened = open_or_resume_run(
            layout,
            operation_key="open.framing",
            reserved_at="2026-07-13T00:00:02Z",
            candidate=candidate,
            run_input_brief=brief,
            operational=operational,
        )
        self.assertEqual(opened.status, "opened")
        packet = read_work_packet(
            operational, opened.route_run_id, opened.work_packet_hash
        )
        self.assertEqual(packet.run_input, brief)
        self.assertNotIn(str(self.root), canonical_json_bytes(packet).decode("utf-8"))
        self.assertEqual(packet.route_id, candidate.key.route_id)

        resumed = open_or_resume_run(
            layout,
            operation_key="different.host.retry",
            reserved_at="2026-07-13T00:00:03Z",
            candidate=candidate,
            run_input_brief=brief,
            operational=operational,
        )
        self.assertEqual(resumed.status, "resumed")
        self.assertEqual(resumed.route_run_id, opened.route_run_id)
        self.assertEqual(resumed.work_packet_hash, opened.work_packet_hash)

        views = derive_all_run_execution_views(layout, replay(layout))
        view = next(item for item in views if item.route_run_id == opened.route_run_id)
        self.assertEqual((view.integrity, view.lifecycle), ("valid", "opened"))
        path = candidate_path(layout, opened.route_run_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["rationale"] = "A first host-neutral framing note."
        path.write_bytes(canonical_json_bytes(payload))
        changed = derive_all_run_execution_views(layout, replay(layout))
        changed_view = next(
            item for item in changed if item.route_run_id == opened.route_run_id
        )
        self.assertEqual(changed_view.lifecycle, "candidate_present")


if __name__ == "__main__":
    unittest.main()
