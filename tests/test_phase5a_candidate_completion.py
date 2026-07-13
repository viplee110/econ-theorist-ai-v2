from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from econ_theorist.codec import canonical_json_bytes, sha256_digest, transaction_bytes
from econ_theorist.decisions import commit_decision
from econ_theorist.machine.binding import bind_or_initialize_project
from econ_theorist.machine.completion import (
    CompletionError,
    complete_candidate,
    record_host_finish,
)
from econ_theorist.machine.dispatcher import MachineDispatcher
from econ_theorist.machine.egress import create_egress_plan, deliver_work_packet
from econ_theorist.machine.inspection import inspect_project
from econ_theorist.machine.lifecycle import derive_run_execution_view
from econ_theorist.machine.models import (
    CapabilityV1,
    CapabilityReceiptV1,
    DiscoveryGrantV1,
    HostOperationReceiptV1,
    MachineRequestV1,
    RunInputBriefV1,
)
from econ_theorist.machine.navigation import plan_next
from econ_theorist.machine.operational import (
    ContentAddressedOperationalStore,
    ProjectOperationalLayout,
)
from econ_theorist.machine.packets import read_work_packet
from econ_theorist.machine.run_service import open_or_resume_run
from econ_theorist.models import (
    Actor,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
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
from econ_theorist.runtime.replay import CandidateValidationError, replay
from econ_theorist.staging import active_candidate_path
from econ_theorist.theory import (
    BenchmarkRecord,
    BenchmarkSet,
    ResearchQuestion,
    pack_theory_payload,
)


NOW = "2026-07-13T00:00:00Z"


class Phase5ACandidateCompletionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.anchor = Path(self.temporary_directory.name)
        self.root = self.anchor / "paper"
        self.root.mkdir()
        grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
        )
        bind_or_initialize_project(
            self.root,
            discovery_grant=grant,
            initialize=True,
            project_name="Candidate completion fixture",
            actor_id="human.owner",
            operation_key="initialize.completion",
            reserved_at=NOW,
            operational_home=self.anchor / "local-home",
        )
        self.layout = StoreLayout.at(self.root)
        self.operational = ProjectOperationalLayout.at(self.layout)
        self.opened, self.packet, self.envelope_hash = self._open_and_deliver()

    def _open_and_deliver(self):
        snapshot = replay(self.layout)
        actor = Actor(kind="agent", actor_id="scientific_writer")
        brief = RunInputBriefV1(
            project_id=snapshot.project_id,
            base_head=snapshot.head,
            requested_scope="Frame one bounded theoretical mechanism.",
            framing_intent="Why can costly search reverse a benchmark prediction?",
            privacy="project_private",
            compartments=("project_research",),
            actor_role=actor.actor_id,
        )
        plan = plan_next(
            self.layout,
            snapshot,
            actor=actor,
            compartments=("project_research",),
            privacy_clearance="project_private",
            budget_units=10_000,
            run_input_brief=brief,
        )
        self.assertEqual(plan.outcome, "unique_next")
        opened = open_or_resume_run(
            self.layout,
            operation_key="open.completion.fixture",
            reserved_at="2026-07-13T00:00:01Z",
            candidate=plan.candidates[0],
            run_input_brief=brief,
            operational=self.operational,
        )
        packet = read_work_packet(
            self.operational, opened.route_run_id, opened.work_packet_hash
        )
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
            observed_at="2026-07-13T00:00:02Z",
        )
        egress_plan = create_egress_plan(
            packet,
            capability,
            host_product="test-host",
            host_version="1.0",
            adapter_id="generic.test",
            provider="local.engine",
            model="model.test",
            execution_class="local",
        )
        delivery = deliver_work_packet(
            self.layout,
            self.operational,
            route_run_id=opened.route_run_id,
            packet_hash=opened.work_packet_hash,
            operation_key="deliver.completion.fixture",
            request_digest="d" * 64,
            plan=egress_plan,
            capability=capability,
            host_session_id="session.completion",
            adapter_version="1.0",
            delivery_time="2026-07-13T00:00:03Z",
        )
        self.assertEqual(delivery.status, "delivery_started")
        return opened, packet, delivery.delivery_envelope_hash

    def _valid_transaction(self) -> Transaction:
        snapshot = replay(self.layout)
        run = read_run(self.layout, self.opened.route_run_id)
        question = EntityVersion(
            entity_id="question.completion",
            entity_type="ResearchQuestion",
            version=1,
            project_id=snapshot.project_id,
            title="Completion question",
            summary="A bounded mechanism question for machine completion.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                ResearchQuestion(
                    phenomenon="A comparative static can reverse.",
                    object_to_explain="The reversal.",
                    unresolved_delta="The benchmark fixes participation.",
                    importance="Participation changes the policy ranking.",
                    kill_condition="The fixed-participation benchmark reverses too.",
                    proposed_scope="A finite-state decision problem.",
                    candidate_archetypes=("mechanism_explanation",),
                )
            ),
            created_at=NOW,
        )
        question_ref = EntityVersionRef(entity_id=question.entity_id, version=1)
        benchmark = EntityVersion(
            entity_id="benchmarks.completion",
            entity_type="BenchmarkSet",
            version=1,
            project_id=snapshot.project_id,
            title="Completion benchmarks",
            summary="The exact benchmark delta for completion.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                BenchmarkSet(
                    question_ref=question_ref,
                    benchmarks=(
                        BenchmarkRecord(
                            benchmark_id="benchmark.completion",
                            label="Fixed-participation benchmark",
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
        benchmark_ref = EntityVersionRef(entity_id=benchmark.entity_id, version=1)
        frames = RelationVersion(
            relation_id="relation.completion.frames",
            relation_type="frames",
            version=1,
            project_id=snapshot.project_id,
            source=question_ref,
            target=benchmark_ref,
            dependency_mode="trace_only",
            created_at=NOW,
        )
        delta = RelationVersion(
            relation_id="relation.completion.delta",
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
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id="transaction.completion",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=run.actor,
            intent="Frame one exact research question.",
            operations=(
                CreateEntityOp(entity=question),
                CreateEntityOp(entity=benchmark),
                CreateRelationOp(relation=frames),
                CreateRelationOp(relation=delta),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run.route_run_id,
                        route_id=run.route_id,
                        outcome="completed_with_candidate",
                        rationale="The framing route produced one exact bundle.",
                        candidate_refs=refs,
                    )
                ),
            ),
            created_at=NOW,
            parent_transaction_hash=run.base_revision,
        )

    def _write_candidate(self, transaction: Transaction) -> Path:
        path = self.root / self.packet.candidate_logical_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(transaction_bytes(transaction))
        return path

    def _kwargs(self, operation_key: str, request_digest: str) -> dict[str, object]:
        return {
            "operation_key": operation_key,
            "request_digest": request_digest,
            "route_run_id": self.opened.route_run_id,
            "work_packet_hash": self.opened.work_packet_hash,
            "delivery_envelope_hash": self.envelope_hash,
            "host_product": "test-host",
            "host_version": "1.0",
            "adapter_id": "generic.test",
            "adapter_version": "1.0",
            "provider": "local.engine",
            "model": "model.test",
            "reasoning_class": "not_exposed",
            "tool_identities": ("filesystem.read", "candidate.write"),
            "completed_at": "2026-07-13T00:00:04Z",
        }

    def _read_receipt(self, digest: str) -> HostOperationReceiptV1:
        store = ContentAddressedOperationalStore(
            self.operational.project_root,
            self.operational.runs / self.opened.route_run_id,
        )
        data = store.read_bytes("host-receipts", digest)
        receipt = HostOperationReceiptV1.model_validate_json(data, strict=True)
        self.assertEqual(canonical_json_bytes(receipt), data)
        return receipt

    def test_stage_and_commit_is_exact_idempotent_and_receipt_is_bounded(self) -> None:
        transaction = self._valid_transaction()
        candidate_path = self._write_candidate(transaction)
        digest = sha256_digest(transaction_bytes(transaction))
        kwargs = self._kwargs("complete.once", "a" * 64)
        result = complete_candidate(
            self.layout,
            self.operational,
            action="stage_and_commit",
            transaction_path=candidate_path,
            expected_candidate_digest=digest,
            **kwargs,  # type: ignore[arg-type]
        )
        self.assertEqual(result.status, "committed")
        self.assertEqual(result.transaction_digest, digest)
        self.assertEqual(replay(self.layout).head, digest)
        receipt = self._read_receipt(result.host_receipt_hash)
        self.assertEqual(receipt.delivery_envelope_hash, self.envelope_hash)
        self.assertEqual(receipt.work_packet_hash, self.opened.work_packet_hash)
        self.assertEqual(receipt.completion_status, "completed")
        self.assertEqual(receipt.reasoning_class, "not_exposed")
        self.assertNotIn("rationale", receipt.model_fields_set)

        retry = complete_candidate(
            self.layout,
            self.operational,
            action="stage_and_commit",
            transaction_path=candidate_path,
            expected_candidate_digest=digest,
            **kwargs,  # type: ignore[arg-type]
        )
        self.assertEqual(retry, result)
        with self.assertRaises(CompletionError):
            complete_candidate(
                self.layout,
                self.operational,
                action="stage_and_commit",
                transaction_path=candidate_path,
                expected_candidate_digest=digest,
                **self._kwargs("complete.once", "b" * 64),  # type: ignore[arg-type]
            )
        with self.assertRaisesRegex(
            CompletionError, "committed before this operation started"
        ):
            complete_candidate(
                self.layout,
                self.operational,
                action="stage_and_commit",
                transaction_path=candidate_path,
                expected_candidate_digest=digest,
                **self._kwargs("complete.too.late", "9" * 64),  # type: ignore[arg-type]
            )

    def test_completed_candidate_survives_restart_inspection_and_completion(self) -> None:
        transaction = self._valid_transaction()
        candidate_path = self._write_candidate(transaction)
        digest = sha256_digest(transaction_bytes(transaction))

        # The host may exit after publishing the exact candidate but before it
        # calls candidate.complete.  A fresh engine process must recognize the
        # raw canonical Transaction rather than misclassifying the run as
        # corrupt.
        view = derive_run_execution_view(
            self.layout, replay(self.layout), self.opened.route_run_id
        )
        self.assertEqual(
            (view.integrity, view.base_freshness, view.lifecycle),
            ("valid", "current", "candidate_present"),
        )
        self.assertEqual(view.candidate_digest, digest)

        result = complete_candidate(
            self.layout,
            self.operational,
            action="stage_and_commit",
            transaction_path=candidate_path,
            expected_candidate_digest=digest,
            **self._kwargs("complete.after.restart", "7" * 64),  # type: ignore[arg-type]
        )
        self.assertEqual(result.status, "committed")
        self.assertEqual(replay(self.layout).head, digest)

    def test_local_machine_facade_can_validate_and_commit_without_adapter_attestation(self) -> None:
        transaction = self._valid_transaction()
        candidate_path = self._write_candidate(transaction)
        digest = sha256_digest(transaction_bytes(transaction))
        grant = DiscoveryGrantV1(
            selected_root=str(self.root),
            allowed_discovery_roots=(str(self.root),),
            ancestor_check_boundary=str(self.root),
            stable_workspace_root=str(self.root),
        )
        request = MachineRequestV1(
            operation="candidate.complete",
            operation_key="complete.local-machine",
            project_root=str(self.root),
            discovery_grant=grant,
            parameters={
                "action": "stage_and_commit",
                "route_run_id": self.opened.route_run_id,
                "work_packet_hash": self.opened.work_packet_hash,
                "delivery_envelope_hash": self.envelope_hash,
                "transaction_path": str(candidate_path),
                "expected_candidate_digest": digest,
                "tool_identities": ["candidate.write"],
            },
        )
        response = MachineDispatcher().dispatch(request)
        self.assertEqual(response.outcome, "ok", response)
        self.assertEqual(response.result["status"], "committed")
        self.assertEqual(replay(self.layout).head, digest)

    def test_conflicting_immutable_outcomes_require_repair_not_resume(self) -> None:
        outcome_root = (
            self.layout.runs_dir / self.opened.route_run_id / "outcomes"
        )
        outcome_root.mkdir(parents=True, exist_ok=True)
        for digit in ("1", "2"):
            digest = digit * 64
            outcome = {
                "outcome_schema": "econ-theorist/run-outcome/v1",
                "route_run_id": self.opened.route_run_id,
                "candidate_digest": digest,
                "status": "stale_base",
                "head_before": self.packet.base_head,
                "head_after": self.packet.base_head,
                "reconciliation_conflicts": [],
            }
            (outcome_root / f"{digest}.json").write_bytes(
                canonical_json_bytes(outcome)
            )

        snapshot = replay(self.layout)
        view = derive_run_execution_view(
            self.layout, snapshot, self.opened.route_run_id
        )
        self.assertEqual((view.integrity, view.lifecycle), ("invalid", "unknown"))
        inspection = inspect_project(
            self.layout,
            actor=Actor(kind="agent", actor_id="scientific_writer"),
            compartments=("project_research",),
            privacy_clearance="project_private",
            budget_units=10_000,
            snapshot=snapshot,
        )
        assert inspection.navigation is not None
        self.assertEqual(inspection.navigation.outcome, "repair_required")
        self.assertEqual(
            inspection.navigation.blockers[0].code,
            "incomplete_run_requires_repair",
        )

    def test_crash_after_commit_recovers_from_start_and_captured_bytes(self) -> None:
        transaction = self._valid_transaction()
        candidate_path = self._write_candidate(transaction)
        digest = sha256_digest(transaction_bytes(transaction))
        kwargs = self._kwargs("complete.crash.retry", "8" * 64)
        with patch(
            "econ_theorist.machine.completion._persist_operation_result",
            side_effect=RuntimeError("simulated post-commit crash"),
        ):
            with self.assertRaisesRegex(RuntimeError, "post-commit crash"):
                complete_candidate(
                    self.layout,
                    self.operational,
                    action="stage_and_commit",
                    transaction_path=candidate_path,
                    expected_candidate_digest=digest,
                    **kwargs,  # type: ignore[arg-type]
                )
        self.assertEqual(replay(self.layout).head, digest)
        candidate_path.unlink()
        recovered = complete_candidate(
            self.layout,
            self.operational,
            action="stage_and_commit",
            transaction_path=candidate_path,
            expected_candidate_digest=digest,
            **kwargs,  # type: ignore[arg-type]
        )
        self.assertEqual(recovered.status, "committed")
        self.assertEqual(recovered.transaction_digest, digest)
        self.assertEqual(self._read_receipt(recovered.host_receipt_hash).head_after, digest)

    def test_crash_between_capture_and_start_recovers_without_disposable_source(self) -> None:
        transaction = self._valid_transaction()
        candidate_path = self._write_candidate(transaction)
        digest = sha256_digest(transaction_bytes(transaction))
        kwargs = self._kwargs("complete.capture.retry", "6" * 64)
        with patch(
            "econ_theorist.machine.completion._persist_completion_start",
            side_effect=RuntimeError("simulated pre-start crash"),
        ):
            with self.assertRaisesRegex(RuntimeError, "pre-start crash"):
                complete_candidate(
                    self.layout,
                    self.operational,
                    action="stage_and_commit",
                    transaction_path=candidate_path,
                    expected_candidate_digest=digest,
                    **kwargs,  # type: ignore[arg-type]
                )

        self.assertEqual(replay(self.layout).head, self.packet.base_head)
        captured = (
            self.operational.runs
            / self.opened.route_run_id
            / "host-candidates"
            / "sha256"
            / f"{digest}.json"
        )
        self.assertTrue(captured.is_file())
        candidate_path.unlink()

        recovered = complete_candidate(
            self.layout,
            self.operational,
            action="stage_and_commit",
            transaction_path=candidate_path,
            expected_candidate_digest=digest,
            **kwargs,  # type: ignore[arg-type]
        )
        self.assertEqual(recovered.status, "committed")
        self.assertEqual(recovered.transaction_digest, digest)
        self.assertEqual(replay(self.layout).head, digest)

    def test_stage_only_then_commit_staged_preserves_frozen_boundaries(self) -> None:
        transaction = self._valid_transaction()
        candidate_path = self._write_candidate(transaction)
        staged = complete_candidate(
            self.layout,
            self.operational,
            action="stage_only",
            transaction_path=candidate_path,
            **self._kwargs("stage.once", "c" * 64),  # type: ignore[arg-type]
        )
        self.assertEqual(staged.status, "staged")
        self.assertEqual(replay(self.layout).head, self.packet.base_head)

        committed = complete_candidate(
            self.layout,
            self.operational,
            action="commit_staged",
            **self._kwargs("commit.staged.once", "e" * 64),  # type: ignore[arg-type]
        )
        self.assertEqual(committed.status, "committed")
        self.assertEqual(replay(self.layout).head, committed.transaction_digest)

    def test_stale_base_is_terminal_and_never_stages_or_rebases(self) -> None:
        transaction = self._valid_transaction()
        candidate_path = self._write_candidate(transaction)
        snapshot = replay(self.layout)
        decision = Decision(
            decision_id="decision.advance.head",
            version=1,
            project_id=snapshot.project_id,
            decision_kind="theory_mode",
            subject_ref=snapshot.project_id,
            question="Advance the test head?",
            options=("advance", "hold"),
            selected_option="advance",
            recommendation="advance",
            rationale="Explicit human fixture action.",
            required_authority="L2",
            decider=Actor(kind="human", actor_id="human.owner"),
            decided_at="2026-07-13T00:00:04Z",
            status="confirmed",
        )
        advanced = commit_decision(
            self.layout,
            decision,
            transaction_id="transaction.advance.head",
            route_run_id="run.advance.head",
            created_at="2026-07-13T00:00:04Z",
        )
        self.assertEqual(advanced.status, "committed")
        result = complete_candidate(
            self.layout,
            self.operational,
            action="stage_and_commit",
            transaction_path=candidate_path,
            **self._kwargs("complete.stale", "f" * 64),  # type: ignore[arg-type]
        )
        self.assertEqual(result.status, "stale_base")
        self.assertEqual(replay(self.layout).head, advanced.head_after)
        receipt = self._read_receipt(result.host_receipt_hash)
        self.assertEqual(receipt.commit_outcome, "stale_base")
        self.assertEqual(receipt.completion_status, "failed_terminal")

    def test_host_finish_records_failure_cancel_and_unknown_without_effect(self) -> None:
        before = replay(self.layout).head
        statuses = (
            "failed_no_effect",
            "failed_terminal",
            "cancelled",
            "unknown_possible_effect",
            "unknown_possible_egress",
        )
        results = []
        for index, status in enumerate(statuses, start=1):
            result = record_host_finish(
                self.layout,
                self.operational,
                completion_status=status,  # type: ignore[arg-type]
                warnings=(f"host.{status}",),
                **self._kwargs(
                    f"finish.{status}", str(index) * 64
                ),  # type: ignore[arg-type]
            )
            self.assertEqual(result.status, "recorded_failure")
            receipt = self._read_receipt(result.host_receipt_hash)
            self.assertEqual(receipt.completion_status, status)
            self.assertIsNone(receipt.candidate_digest)
            results.append(result)
        self.assertEqual(replay(self.layout).head, before)
        retry = record_host_finish(
            self.layout,
            self.operational,
            completion_status="cancelled",
            warnings=("host.cancelled",),
            **self._kwargs("finish.cancelled", "3" * 64),  # type: ignore[arg-type]
        )
        self.assertEqual(retry, results[2])

    def test_receipt_rejects_freeform_reasoning_and_wrong_delivery_identity(self) -> None:
        transaction = self._valid_transaction()
        candidate_path = self._write_candidate(transaction)
        kwargs = self._kwargs("complete.bad.metadata", "2" * 64)
        kwargs["reasoning_class"] = "Here is my private chain of thought"
        with self.assertRaises(CompletionError):
            complete_candidate(
                self.layout,
                self.operational,
                action="stage_only",
                transaction_path=candidate_path,
                **kwargs,  # type: ignore[arg-type]
            )
        self.assertFalse(
            active_candidate_path(self.layout, self.opened.route_run_id).exists()
        )
        wrong_host = self._kwargs("complete.bad.host", "3" * 64)
        wrong_host["model"] = "different.model"
        with self.assertRaises(CompletionError):
            complete_candidate(
                self.layout,
                self.operational,
                action="stage_only",
                transaction_path=candidate_path,
                **wrong_host,  # type: ignore[arg-type]
            )

    def test_commit_still_runs_the_exact_scientific_validator(self) -> None:
        valid = self._valid_transaction()
        invalid = valid.model_copy(update={"operations": valid.operations[:1]})
        candidate_path = self._write_candidate(invalid)
        before = replay(self.layout).head
        with self.assertRaises(CandidateValidationError):
            complete_candidate(
                self.layout,
                self.operational,
                action="stage_and_commit",
                transaction_path=candidate_path,
                **self._kwargs("complete.invalid", "4" * 64),  # type: ignore[arg-type]
            )
        self.assertEqual(replay(self.layout).head, before)


if __name__ == "__main__":
    unittest.main()
