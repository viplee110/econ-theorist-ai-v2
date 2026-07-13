from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from econ_theorist.codec import canonical_json_bytes
from econ_theorist.machine.dispatcher import MachineDispatcher
from econ_theorist.machine.models import (
    DiscoveryGrantV1,
    MachineRequestV1,
    MachineResponseV1,
    RunInputBriefV1,
)
from econ_theorist.models import Actor


_CHILD = (
    "import os, sys; "
    "from econ_theorist.codec import canonical_json_bytes; "
    "from econ_theorist.machine.dispatcher import MachineDispatcher; "
    "from econ_theorist.machine_cli import invoke_machine_bytes; "
    "d=MachineDispatcher(preproject_operational_home=os.environ['ETAI_TEST_OPERATIONAL_HOME']); "
    "r=invoke_machine_bytes(sys.stdin.buffer.read(), dispatcher=d); "
    "sys.stdout.buffer.write(canonical_json_bytes(r)+b'\\n')"
)


class Phase5AMachineConcurrencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        self.local_home = self.anchor / "local-operations"
        self.grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
        )
        self.environment = os.environ.copy()
        self.environment["PYTHONPATH"] = str(
            Path(__file__).resolve().parents[1] / "src"
        )
        self.environment["ETAI_TEST_OPERATIONAL_HOME"] = str(self.local_home)

    def _request(
        self, operation: str, key: str, parameters: dict
    ) -> MachineRequestV1:
        return MachineRequestV1(
            operation=operation,  # type: ignore[arg-type]
            operation_key=key,
            project_root=str(self.root),
            discovery_grant=self.grant,
            parameters=parameters,
        )

    def _race(
        self, first: MachineRequestV1, second: MachineRequestV1
    ) -> tuple[MachineResponseV1, MachineResponseV1]:
        processes = [
            subprocess.Popen(
                [sys.executable, "-c", _CHILD],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=self.environment,
            )
            for _ in range(2)
        ]
        for process, request in zip(processes, (first, second), strict=True):
            assert process.stdin is not None
            process.stdin.write(canonical_json_bytes(request))
            process.stdin.close()
        outputs = []
        for process in processes:
            assert process.stdout is not None and process.stderr is not None
            stdout = process.stdout.read()
            stderr = process.stderr.read()
            process.wait(timeout=60)
            process.stdout.close()
            process.stderr.close()
            self.assertEqual(process.returncode, 0, stderr.decode("utf-8"))
            self.assertEqual(stderr, b"")
            outputs.append(
                MachineResponseV1.model_validate_json(stdout, strict=True)
            )
        return outputs[0], outputs[1]

    def test_two_initializers_create_exactly_one_genesis(self) -> None:
        parameters = {
            "initialize": True,
            "project_name": "Concurrent initialization fixture",
        }
        first, second = self._race(
            self._request("project.bind_or_initialize", "init.concurrent.a", parameters),
            self._request("project.bind_or_initialize", "init.concurrent.b", parameters),
        )
        self.assertEqual({first.outcome, second.outcome}, {"ok"})
        self.assertEqual(
            {first.result["status"], second.result["status"]},
            {"initialized", "bound"},
        )
        self.assertEqual(first.project_id, second.project_id)
        self.assertEqual(first.head, second.head)

    def test_same_operation_key_replays_one_cross_process_response(self) -> None:
        request = self._request(
            "project.bind_or_initialize",
            "init.concurrent.same-key",
            {
                "initialize": True,
                "project_name": "Same key initialization fixture",
            },
        )
        first, second = self._race(request, request)
        self.assertEqual(first, second)
        self.assertEqual(first.outcome, "ok")
        self.assertEqual(first.result["status"], "initialized")

    def test_two_hosts_open_one_exact_run(self) -> None:
        actor = Actor(kind="agent", actor_id="scientific_agent")
        dispatcher = MachineDispatcher(
            preproject_operational_home=self.local_home,
        )
        initialized = dispatcher.dispatch(
            self._request(
                "project.bind_or_initialize",
                "init.open-race",
                {
                    "initialize": True,
                    "project_name": "Concurrent open fixture",
                },
            )
        )
        self.assertEqual(initialized.outcome, "ok")
        brief = RunInputBriefV1(
            project_id=initialized.project_id,
            base_head=initialized.head,
            requested_scope="Frame one concurrent theory fixture.",
            framing_intent="Which mechanism survives the benchmark?",
            privacy="project_private",
            compartments=("project_research",),
            actor_role=actor.actor_id,
        )
        plan_request = MachineRequestV1(
            operation="navigation.plan_next",
            project_root=str(self.root),
            discovery_grant=self.grant,
            parameters={
                "budget_units": 10_000,
                "run_input_brief": brief.model_dump(mode="json"),
            },
        )
        plan = dispatcher.dispatch(plan_request)
        self.assertEqual(plan.outcome, "ok", plan)
        parameters = {
            "candidate": plan.result["candidates"][0],
            "run_input_brief": brief.model_dump(mode="json"),
        }
        first, second = self._race(
            self._request("run.open_or_resume", "open.concurrent.a", parameters),
            self._request("run.open_or_resume", "open.concurrent.b", parameters),
        )
        self.assertEqual({first.outcome, second.outcome}, {"ok"})
        self.assertEqual(
            {first.result["status"], second.result["status"]},
            {"opened", "resumed"},
        )
        self.assertEqual(
            first.result["route_run_id"], second.result["route_run_id"]
        )
        self.assertEqual(
            first.result["work_packet_hash"], second.result["work_packet_hash"]
        )


if __name__ == "__main__":
    unittest.main()
