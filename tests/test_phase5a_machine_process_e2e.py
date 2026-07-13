"""One complete deterministic route through the public process boundary."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from econ_theorist.codec import canonical_json_bytes, sha256_digest, transaction_bytes
from econ_theorist.machine.models import (
    CapabilityReceiptV1,
    CapabilityV1,
    DiscoveryGrantV1,
    MachineRequestV1,
    MachineResponseV1,
    RunInputBriefV1,
)
from econ_theorist.models import (
    CreateEntityOp,
    CreateRelationOp,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    ScientificStatus,
    Transaction,
)
from econ_theorist.runs import read_run, transaction_bindings
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.replay import replay
from econ_theorist.theory import (
    BenchmarkRecord,
    BenchmarkSet,
    ResearchQuestion,
    pack_theory_payload,
)


NOW = "2026-07-13T00:00:00Z"


class Phase5AMachineProcessE2ETests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        self.local_app_data = self.anchor / "local-app-data"
        self.local_app_data.mkdir()
        self.source = Path(__file__).resolve().parents[1] / "src"
        self.grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
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

    def _invoke(self, request: MachineRequestV1) -> MachineResponseV1:
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(self.source)
        environment["LOCALAPPDATA"] = str(self.local_app_data)
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from econ_theorist.cli import main; "
                    "raise SystemExit(main(['machine','invoke','--request','-']))"
                ),
            ],
            input=canonical_json_bytes(request),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        self.assertEqual(result.stderr, b"")
        self.assertEqual(result.stdout.count(b"\n"), 1)
        return MachineResponseV1.model_validate_json(
            result.stdout.rstrip(b"\n"), strict=True
        )

    def _framing_transaction(self, route_run_id: str) -> Transaction:
        layout = StoreLayout.at(self.root)
        snapshot = replay(layout)
        run = read_run(layout, route_run_id)
        question = EntityVersion(
            entity_id="question.process.e2e",
            entity_type="ResearchQuestion",
            version=1,
            project_id=snapshot.project_id,
            title="Process-boundary question",
            summary="A bounded framing object produced by the fixture writer.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                ResearchQuestion(
                    phenomenon="A benchmark prediction can reverse.",
                    object_to_explain="The reversal.",
                    unresolved_delta="The benchmark fixes participation.",
                    importance="Endogenous participation changes the ranking.",
                    kill_condition="The fixed-participation benchmark also reverses.",
                    proposed_scope="A finite-state decision problem.",
                    candidate_archetypes=("mechanism_explanation",),
                )
            ),
            created_at=NOW,
        )
        question_ref = EntityVersionRef(entity_id=question.entity_id, version=1)
        benchmarks = EntityVersion(
            entity_id="benchmarks.process.e2e",
            entity_type="BenchmarkSet",
            version=1,
            project_id=snapshot.project_id,
            title="Process-boundary benchmarks",
            summary="The exact benchmark delta for the process fixture.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                BenchmarkSet(
                    question_ref=question_ref,
                    benchmarks=(
                        BenchmarkRecord(
                            benchmark_id="benchmark.process.e2e",
                            label="Fixed participation",
                            exact_primitives=("one decision maker",),
                            timing=("information then action",),
                            solution_concept="optimal action",
                            prediction="precision improves conditional accuracy",
                            unresolved_delta="participation is fixed",
                        ),
                    ),
                    exact_question_delta="Allow participation to respond to precision.",
                )
            ),
            created_at=NOW,
        )
        benchmark_ref = EntityVersionRef(entity_id=benchmarks.entity_id, version=1)
        frames = RelationVersion(
            relation_id="relation.process.e2e.frames",
            relation_type="frames",
            version=1,
            project_id=snapshot.project_id,
            source=question_ref,
            target=benchmark_ref,
            dependency_mode="trace_only",
            created_at=NOW,
        )
        delta = RelationVersion(
            relation_id="relation.process.e2e.delta",
            relation_type="benchmark_delta",
            version=1,
            project_id=snapshot.project_id,
            source=benchmark_ref,
            target=question_ref,
            dependency_mode="trace_only",
            created_at=NOW,
        )
        refs = (
            question_ref,
            benchmark_ref,
            RelationVersionRef(relation_id=frames.relation_id, version=1),
            RelationVersionRef(relation_id=delta.relation_id, version=1),
        )
        return Transaction(
            **transaction_bindings(layout, route_run_id),
            transaction_id="transaction.process.e2e",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=run.actor,
            intent="Frame one exact research question through the public process.",
            operations=(
                CreateEntityOp(entity=question),
                CreateEntityOp(entity=benchmarks),
                CreateRelationOp(relation=frames),
                CreateRelationOp(relation=delta),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run.route_run_id,
                        route_id=run.route_id,
                        outcome="completed_with_candidate",
                        rationale="The process fixture produced one exact framing bundle.",
                        candidate_refs=refs,
                    )
                ),
            ),
            created_at=NOW,
            parent_transaction_hash=run.base_revision,
        )

    def test_public_process_composes_initialize_packet_and_commit(self) -> None:
        initialized = self._invoke(
            self._request(
                "project.bind_or_initialize",
                operation_key="process.initialize",
                parameters={"initialize": True, "project_name": "Process fixture"},
            )
        )
        self.assertEqual(initialized.outcome, "ok", initialized)
        brief = RunInputBriefV1(
            project_id=initialized.project_id,
            base_head=initialized.head,
            requested_scope="Frame one bounded theory question and benchmark.",
            framing_intent="When can costly participation reverse a benchmark?",
            privacy="project_private",
            compartments=("project_research",),
            actor_role="scientific_agent",
        )
        planned = self._invoke(
            self._request(
                "navigation.plan_next",
                parameters={
                    "budget_units": 10_000,
                    "run_input_brief": brief.model_dump(mode="json"),
                },
            )
        )
        self.assertEqual(planned.result["outcome"], "unique_next")
        opened = self._invoke(
            self._request(
                "run.open_or_resume",
                operation_key="process.open",
                parameters={
                    "candidate": planned.result["candidates"][0],
                    "run_input_brief": brief.model_dump(mode="json"),
                },
            )
        )
        capability = CapabilityReceiptV1(
            host_product="process-fixture",
            host_version="1",
            adapter_id="generic.process-fixture",
            adapter_version="1",
            execution_class="local",
            technically_accessible_roots=(str(self.root),),
            model_tool_isolation="verified",
            trusted_human_channel="verified",
            capabilities=tuple(
                CapabilityV1(
                    capability_id=identifier,
                    available=True,
                    required=True,
                    evidence="deterministic process fixture",
                )
                for identifier in (
                    "python_runtime",
                    "structured_process_invocation",
                    "single_agent_topology",
                )
            ),
            observed_at=NOW,
        )
        plan = self._invoke(
            self._request(
                "egress.plan",
                parameters={
                    "route_run_id": opened.result["route_run_id"],
                    "work_packet_hash": opened.result["work_packet_hash"],
                    "capability": capability.model_dump(mode="json"),
                    "host_product": capability.host_product,
                    "host_version": capability.host_version,
                    "adapter_id": capability.adapter_id,
                    "provider": "deterministic.local",
                    "model": "fixture-writer",
                    "execution_class": "local",
                },
            )
        )
        delivered = self._invoke(
            self._request(
                "packet.deliver",
                operation_key="process.deliver",
                parameters={
                    "route_run_id": opened.result["route_run_id"],
                    "work_packet_hash": opened.result["work_packet_hash"],
                    "plan": plan.result,
                    "capability": capability.model_dump(mode="json"),
                },
            )
        )
        self.assertEqual(delivered.result["status"], "delivery_started")
        self.assertIsNotNone(delivered.result["work_packet"])

        transaction = self._framing_transaction(opened.result["route_run_id"])
        candidate_path = self.root / opened.result["candidate_logical_path"]
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_bytes(transaction_bytes(transaction))
        digest = sha256_digest(transaction_bytes(transaction))
        completion_request = self._request(
            "candidate.complete",
            operation_key="process.complete",
            parameters={
                "action": "stage_and_commit",
                "route_run_id": opened.result["route_run_id"],
                "work_packet_hash": opened.result["work_packet_hash"],
                "delivery_envelope_hash": delivered.result[
                    "delivery_envelope_hash"
                ],
                "transaction_path": str(candidate_path),
                "expected_candidate_digest": digest,
                "tool_identities": ["fixture.candidate-write"],
            },
        )
        completed = self._invoke(completion_request)
        self.assertEqual(completed.result["status"], "committed")
        self.assertEqual(replay(StoreLayout.at(self.root)).head, digest)

        retried_from_a_fresh_process = self._invoke(completion_request)
        self.assertEqual(retried_from_a_fresh_process, completed)
        self.assertEqual(
            len(
                tuple(
                    (self.root / ".econ-theorist" / "runs").glob("*/run.json")
                )
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
