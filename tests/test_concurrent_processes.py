"""True two-process head race under the mandatory OS commit lock."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
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
from econ_theorist.runs import begin_run, transaction_bindings
from econ_theorist.runtime import ObjectStore, StoreLayout
from econ_theorist.runtime.replay import replay


class TwoProcessCommitRaceTests(unittest.TestCase):
    def _transaction(
        self,
        project_id: str,
        head: str,
        suffix: str,
        route_run_id: str,
        bindings: dict[str, str],
    ) -> Transaction:
        entity = EntityVersion(
            entity_id=f"ent_race_{suffix}",
            entity_type="TheoryObject",
            version=1,
            project_id=project_id,
            title=f"Race {suffix}",
            summary="One competing proposal.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=FacetPayloads(formal={"candidate": suffix}),
            created_at="2026-07-11T03:00:00Z",
        )
        return Transaction(
            **bindings,
            transaction_id=f"txn_race_{suffix}",
            origin="route_run",
            project_id=project_id,
            base_revision=head,
            route_run_id=route_run_id,
            route_id="frame.question_and_benchmarks",
            actor=Actor(kind="agent", actor_id=f"agent_{suffix}"),
            intent=f"Competing candidate {suffix}.",
            operations=(CreateEntityOp(entity=entity),),
            created_at="2026-07-11T03:00:01Z",
            parent_transaction_hash=head,
        )

    def test_exactly_one_process_advances_head_and_loser_stays_proposal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            initial = init_project(root, name="Race case", actor_id="human_owner")
            layout = StoreLayout.at(root)
            transactions = []
            for suffix in ("a", "b"):
                actor = Actor(kind="agent", actor_id=f"agent_{suffix}")
                run = begin_run(
                    layout,
                    initial,
                    route_id="frame.question_and_benchmarks",
                    actor=actor,
                    purpose="research_framing",
                    compartments=("project_research",),
                    budget_units=4000,
                )
                transactions.append(
                    self._transaction(
                        initial.project_id,
                        initial.head,
                        suffix,
                        run.route_run_id,
                        transaction_bindings(layout, run.route_run_id),
                    )
                )
            candidate_paths: list[Path] = []
            for transaction in transactions:
                path = root / f"{transaction.transaction_id}.json"
                path.write_bytes(transaction_bytes(transaction))
                candidate_paths.append(path)

            go = root / "go"
            env = os.environ.copy()
            existing = env.get("PYTHONPATH")
            env["PYTHONPATH"] = (
                str(SOURCE_ROOT)
                if not existing
                else os.pathsep.join((str(SOURCE_ROOT), str(REPOSITORY_ROOT), existing))
            )
            processes: list[subprocess.Popen[str]] = []
            ready_paths: list[Path] = []
            result_paths: list[Path] = []
            for index, candidate in enumerate(candidate_paths):
                ready = root / f"ready-{index}"
                result = root / f"result-{index}.json"
                ready_paths.append(ready)
                result_paths.append(result)
                processes.append(
                    subprocess.Popen(
                        [
                            sys.executable,
                            "-m",
                            "tests.race_worker",
                            str(root),
                            str(candidate),
                            str(ready),
                            str(go),
                            str(result),
                        ],
                        cwd=REPOSITORY_ROOT,
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                    )
                )

            deadline = time.monotonic() + 20
            while not all(path.exists() for path in ready_paths):
                if any(process.poll() not in (None, 0) for process in processes):
                    self.fail("a race worker failed before the commit barrier")
                if time.monotonic() >= deadline:
                    self.fail("race workers did not reach the prepared barrier")
                time.sleep(0.01)
            go.write_text("go\n", encoding="ascii")

            diagnostics: list[str] = []
            for process in processes:
                stdout, stderr = process.communicate(timeout=20)
                diagnostics.append(stdout + stderr)
                self.assertEqual(process.returncode, 0, diagnostics[-1])
            results = [
                json.loads(path.read_text(encoding="utf-8")) for path in result_paths
            ]
            self.assertEqual(
                sorted(result["status"] for result in results),
                ["committed", "stale_base"],
            )

            final = replay(StoreLayout.at(root))
            winner = next(result for result in results if result["status"] == "committed")
            loser = next(result for result in results if result["status"] == "stale_base")
            self.assertEqual(final.head, winner["transaction_digest"])
            self.assertEqual(len(final.chain), 2)
            self.assertTrue(
                ObjectStore(StoreLayout.at(root)).path_for(
                    "transactions", winner["transaction_digest"]
                ).exists()
            )
            self.assertFalse(
                ObjectStore(StoreLayout.at(root)).path_for(
                    "transactions", loser["transaction_digest"]
                ).exists()
            )
            self.assertTrue(all(path.exists() for path in candidate_paths))


if __name__ == "__main__":
    unittest.main()
