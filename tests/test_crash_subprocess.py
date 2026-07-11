"""Abrupt child-process crash tests at both sides of the atomic head boundary."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT, SOURCE_ROOT

from econ_theorist.codec import transaction_bytes, transaction_digest
from econ_theorist.models import (
    Actor,
    CreateEntityOp,
    EntityVersion,
    FacetPayloads,
    ScientificStatus,
    Transaction,
)
from econ_theorist.project import init_project
from econ_theorist.policy import ROUTE_REGISTRY_V1_HASH
from econ_theorist.runs import begin_run, transaction_bindings
from econ_theorist.runtime import HeadStore, StoreLayout
from econ_theorist.runtime.faults import DEFAULT_FAULT_EXIT_CODE, FAULT_POINT_ENV
from econ_theorist.runtime.recovery import recover
from econ_theorist.runtime.replay import replay


class AbruptCrashTests(unittest.TestCase):
    def _candidate(self, root: Path) -> tuple[StoreLayout, Transaction, Path, str]:
        snapshot = init_project(root, name="Crash case", actor_id="human_owner")
        agent = Actor(kind="agent", actor_id="agent_crash")
        run = begin_run(
            StoreLayout.at(root),
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=agent,
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=4000,
            route_registry_hash=ROUTE_REGISTRY_V1_HASH,
        )
        entity = EntityVersion(
            entity_id="ent_after_crash",
            entity_type="TheoryObject",
            version=1,
            project_id=snapshot.project_id,
            title="Crash witness",
            summary="Created by the interrupted candidate.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=FacetPayloads(formal={"claim": "x"}),
            created_at="2026-07-11T02:00:00Z",
        )
        transaction = Transaction(
            **transaction_bindings(StoreLayout.at(root), run.route_run_id),
            transaction_id="txn_abrupt_crash",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=snapshot.head,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=agent,
            intent="Exercise an abrupt process death.",
            operations=(CreateEntityOp(entity=entity),),
            created_at="2026-07-11T02:00:01Z",
            parent_transaction_hash=snapshot.head,
        )
        path = root / "candidate.json"
        path.write_bytes(transaction_bytes(transaction))
        return StoreLayout.at(root), transaction, path, snapshot.head

    def _crash(self, root: Path, candidate: Path, point: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env[FAULT_POINT_ENV] = point
        env.pop("ECON_THEORIST_FAULT_MODE", None)
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            str(SOURCE_ROOT)
            if not existing
            else os.pathsep.join((str(SOURCE_ROOT), str(REPOSITORY_ROOT), existing))
        )
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "tests.fault_worker",
                str(root),
                str(candidate),
            ],
            cwd=REPOSITORY_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

    def test_exit_before_head_keeps_old_canonical_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout, transaction, candidate, old_head = self._candidate(root)
            result = self._crash(root, candidate, "after_transaction_installation")

            self.assertEqual(result.returncode, DEFAULT_FAULT_EXIT_CODE)
            self.assertEqual(HeadStore(layout).read(), old_head)
            report = recover(layout)
            self.assertNotIn("ent_after_crash", report.snapshot.current_entities)
            self.assertIn(
                transaction_digest(transaction), report.orphans.transaction_digests
            )

    def test_exit_after_head_recovers_new_canonical_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            layout, transaction, candidate, old_head = self._candidate(root)
            new_head = transaction_digest(transaction)
            result = self._crash(root, candidate, "after_head_replacement")

            self.assertEqual(result.returncode, DEFAULT_FAULT_EXIT_CODE)
            self.assertNotEqual(HeadStore(layout).read(), old_head)
            self.assertEqual(HeadStore(layout).read(), new_head)
            report = recover(layout)
            self.assertEqual(report.head, new_head)
            self.assertIn("ent_after_crash", report.snapshot.current_entities)
            self.assertEqual(replay(layout).head, new_head)


if __name__ == "__main__":
    unittest.main()
