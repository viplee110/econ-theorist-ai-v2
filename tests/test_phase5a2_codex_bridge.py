from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from econ_theorist.cli import build_parser
from econ_theorist.codec import canonical_json_bytes, sha256_digest, transaction_bytes
from econ_theorist.codex_bridge import (
    CODEX_ADAPTER_ID,
    CODEX_HOST_PRODUCT,
    CODEX_PROVIDER,
    CodexBridge,
    CodexBridgeResponseV1,
    CodexCompleteRequestV1,
    CodexFinishRequestV1,
    CodexSessionV1,
    CodexStartRequestV1,
    codex_bridge_schema,
)
from econ_theorist.candidate_contract import candidate_authoring_contract_hash
from econ_theorist.codex_cli import invoke_codex_bytes
from econ_theorist.machine.binding import bind_or_initialize_project
from econ_theorist.machine.binding import _deterministic_genesis_ids
from econ_theorist.machine.egress import _automatic_delivery_subject, _events
from econ_theorist.machine.models import DeliveryEnvelopeV1, EgressPlanV1, RunInputBriefV1
from econ_theorist.machine.navigation import plan_next
from econ_theorist.machine.operational import (
    ContentAddressedOperationalStore,
    ProjectOperationalLayout,
)
from econ_theorist.machine.run_service import open_or_resume_run
from econ_theorist.models import (
    Actor,
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
from econ_theorist.project import _genesis_transaction
from econ_theorist.runs import read_context, read_run, transaction_bindings
from econ_theorist.runtime import ObjectStore, StoreLayout
from econ_theorist.runtime.replay import replay
from econ_theorist.theory import (
    THEORY_PAYLOAD_MODELS,
    BenchmarkRecord,
    BenchmarkSet,
    GateDossier,
    GateRequirement,
    PrimitiveGraph,
    PrimitiveNode,
    ResearchQuestion,
    pack_theory_payload,
)


NOW = "2026-07-14T00:00:00Z"


class Phase5A2CodexBridgeTests(unittest.TestCase):
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
            session_id="codex-session-phase5a2",
            selected_model="gpt-5",
            installed_models=("gpt-5", "gpt-5-mini"),
            observed_at=NOW,
        )

    def _start_request(self, root: Path | None = None) -> CodexStartRequestV1:
        return CodexStartRequestV1(
            project_root=str(root or self.root),
            initialize=True,
            project_name="Codex bridge fixture",
            requested_scope="Frame one bounded theory question and benchmark.",
            framing_intent="When can costly participation reverse a benchmark?",
            session=self.session,
        )

    def _framing_transaction(self, route_run_id: str) -> Transaction:
        layout = StoreLayout.at(self.root)
        snapshot = replay(layout)
        run = read_run(layout, route_run_id)
        question = EntityVersion(
            entity_id="question.codex.bridge",
            entity_type="ResearchQuestion",
            version=1,
            project_id=snapshot.project_id,
            title="Codex bridge question",
            summary="A bounded framing object produced by the deterministic bridge fixture.",
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
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
        )
        question_ref = EntityVersionRef(entity_id=question.entity_id, version=1)
        benchmarks = EntityVersion(
            entity_id="benchmarks.codex.bridge",
            entity_type="BenchmarkSet",
            version=1,
            project_id=snapshot.project_id,
            title="Codex bridge benchmarks",
            summary="The exact benchmark delta for the bridge fixture.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                BenchmarkSet(
                    question_ref=question_ref,
                    benchmarks=(
                        BenchmarkRecord(
                            benchmark_id="benchmark.codex.bridge",
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
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
        )
        benchmark_ref = EntityVersionRef(entity_id=benchmarks.entity_id, version=1)
        frames = RelationVersion(
            relation_id="relation.codex.bridge.frames",
            relation_type="frames",
            version=1,
            project_id=snapshot.project_id,
            source=question_ref,
            target=benchmark_ref,
            dependency_mode="trace_only",
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
        )
        delta = RelationVersion(
            relation_id="relation.codex.bridge.delta",
            relation_type="benchmark_delta",
            version=1,
            project_id=snapshot.project_id,
            source=benchmark_ref,
            target=question_ref,
            dependency_mode="trace_only",
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
        )
        refs = (
            question_ref,
            benchmark_ref,
            RelationVersionRef(relation_id=frames.relation_id, version=1),
            RelationVersionRef(relation_id=delta.relation_id, version=1),
        )
        return Transaction(
            **transaction_bindings(layout, route_run_id),
            transaction_id="transaction.codex.bridge",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=run.actor,
            intent="Frame one exact question through the Codex bridge.",
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
                        rationale="The bridge fixture produced one exact framing bundle.",
                        candidate_refs=refs,
                        privacy="public",
                        access_compartments=("project_research",),
                    )
                ),
            ),
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
            parent_transaction_hash=run.base_revision,
        )

    def _decomposition_transaction(self, route_run_id: str) -> Transaction:
        layout = StoreLayout.at(self.root)
        snapshot = replay(layout)
        run = read_run(layout, route_run_id)
        current = tuple(
            item
            for item in snapshot.entity_versions
            if snapshot.current_entities.get(item.entity_id) == item.version
        )
        question = next(
            item for item in current if item.entity_type == "ResearchQuestion"
        )
        benchmarks = next(
            item for item in current if item.entity_type == "BenchmarkSet"
        )
        question_ref = EntityVersionRef(
            entity_id=question.entity_id, version=question.version
        )
        benchmark_ref = EntityVersionRef(
            entity_id=benchmarks.entity_id, version=benchmarks.version
        )
        graph = EntityVersion(
            entity_id="primitives.codex.bridge",
            entity_type="PrimitiveGraph",
            version=1,
            project_id=snapshot.project_id,
            title="Codex bridge primitive graph",
            summary="The exact primitive closure for the bridge fixture.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                PrimitiveGraph(
                    question_ref=question_ref,
                    benchmark_set_ref=benchmark_ref,
                    nodes=(
                        PrimitiveNode(
                            node_id="node.codex.bridge.participation",
                            kind="choice",
                            label="Participation",
                            economic_meaning=(
                                "The decision maker chooses whether to participate."
                            ),
                            status="primitive",
                        ),
                    ),
                )
            ),
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
        )
        graph_ref = EntityVersionRef(entity_id=graph.entity_id, version=1)
        dossier = EntityVersion(
            entity_id="dossier.g1.codex.bridge",
            entity_type="GateDossier",
            version=1,
            project_id=snapshot.project_id,
            title="Codex bridge G1 dossier",
            summary="The exact G1 package for the bridge fixture.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                GateDossier(
                    gate_kind="G1_question_benchmark",
                    research_question_ref=question_ref,
                    ordered_object_refs=(question_ref, benchmark_ref, graph_ref),
                    requirements=(
                        GateRequirement(
                            requirement_id="g1.codex.bridge.delta",
                            description=(
                                "The question and benchmark delta are explicit."
                            ),
                            evidence_refs=(question_ref, benchmark_ref, graph_ref),
                            recorded_condition="evidence_supplied",
                        ),
                    ),
                    proposed_action="approve",
                    rationale=(
                        "The package is ready for an economics audit, but this "
                        "does not confirm G1."
                    ),
                    prepared_at=run.created_at,
                )
            ),
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
        )
        dossier_ref = EntityVersionRef(entity_id=dossier.entity_id, version=1)
        decomposes = RelationVersion(
            relation_id="relation.codex.bridge.decomposes",
            relation_type="decomposes",
            version=1,
            project_id=snapshot.project_id,
            source=question_ref,
            target=graph_ref,
            dependency_mode="trace_only",
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
        )
        governs = RelationVersion(
            relation_id="relation.codex.bridge.governs",
            relation_type="governs",
            version=1,
            project_id=snapshot.project_id,
            source=dossier_ref,
            target=question_ref,
            dependency_mode="trace_only",
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
        )
        refs = (
            graph_ref,
            dossier_ref,
            RelationVersionRef(relation_id=decomposes.relation_id, version=1),
            RelationVersionRef(relation_id=governs.relation_id, version=1),
        )
        return Transaction(
            **transaction_bindings(layout, route_run_id),
            transaction_id="transaction.codex.bridge.decomposition",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=run.actor,
            intent="Commit one exact decomposition package.",
            operations=(
                CreateEntityOp(entity=graph),
                CreateEntityOp(entity=dossier),
                CreateRelationOp(relation=decomposes),
                CreateRelationOp(relation=governs),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run.route_run_id,
                        route_id=run.route_id,
                        outcome="completed_with_candidate",
                        rationale="One exact decomposition package was produced.",
                        candidate_refs=refs,
                        privacy="public",
                        access_compartments=("project_research",),
                    )
                ),
            ),
            evidence_refs=(question_ref, benchmark_ref),
            privacy="public",
            access_compartments=("project_research",),
            created_at=run.created_at,
            parent_transaction_hash=run.base_revision,
        )

    def _delivery_identity(
        self, response: CodexBridgeResponseV1
    ) -> tuple[ProjectOperationalLayout, DeliveryEnvelopeV1, EgressPlanV1]:
        layout = StoreLayout.at(self.root)
        operational = ProjectOperationalLayout.at(layout)
        store = ContentAddressedOperationalStore(
            operational.project_root, operational.runs / response.route_run_id
        )
        envelope = DeliveryEnvelopeV1.model_validate_json(
            store.read_bytes("envelopes", response.delivery_envelope_hash), strict=True
        )
        plan = EgressPlanV1.model_validate_json(
            store.read_bytes("egress-plans", envelope.egress_plan_hash), strict=True
        )
        return operational, envelope, plan

    def test_provider_identity_exact_retry_and_canonical_commit(self) -> None:
        request = self._start_request()
        first = self.bridge.invoke(request)
        self.assertEqual(first.outcome, "ready", first)
        self.assertEqual(first.work_packet.privacy_clearance, "public")
        self.assertFalse(first.work_packet.hidden_compartments)
        initial_snapshot = replay(StoreLayout.at(self.root))
        project_version = initial_snapshot.current_entities[initial_snapshot.project_id]
        project_entity = next(
            entity
            for entity in initial_snapshot.entity_versions
            if entity.entity_id == initial_snapshot.project_id
            and entity.version == project_version
        )
        genesis = Transaction.model_validate_json(
            ObjectStore(StoreLayout.at(self.root)).read_bytes(
                "transactions", initial_snapshot.chain[0]
            ),
            strict=True,
        )
        self.assertEqual(project_entity.privacy, "public")
        self.assertEqual(genesis.privacy, "public")

        operational, envelope, plan = self._delivery_identity(first)
        self.assertEqual(envelope.host_product, CODEX_HOST_PRODUCT)
        self.assertEqual(envelope.adapter_id, CODEX_ADAPTER_ID)
        self.assertEqual(plan.provider, CODEX_PROVIDER)
        self.assertEqual(plan.model, self.session.selected_model)
        self.assertEqual(plan.execution_class, "provider_backed")
        self.assertFalse(plan.authorization_required)
        subject_id = _automatic_delivery_subject(plan)
        events_before = _events(operational, subject_id)
        self.assertEqual(
            sum(event.event == "delivery_started" for _, event in events_before), 1
        )

        retried = self.bridge.invoke(request)
        self.assertEqual(retried, first)
        events_after = _events(operational, subject_id)
        self.assertEqual(events_after, events_before)

        continued = self.bridge.invoke(
            CodexStartRequestV1(
                project_root=str(self.root),
                session=self.session,
            )
        )
        self.assertEqual(continued.outcome, "ready", continued)
        self.assertEqual(continued.delivery_envelope_hash, first.delivery_envelope_hash)

        transaction = self._framing_transaction(first.route_run_id)
        candidate_path = self.root / first.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(
            json.dumps(transaction.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        digest = sha256_digest(transaction_bytes(transaction))
        completion_request = CodexCompleteRequestV1(
            project_root=str(self.root),
            route_run_id=first.route_run_id,
            work_packet_hash=first.work_packet_hash,
            delivery_envelope_hash=first.delivery_envelope_hash,
        )
        wrong_digest = self.bridge.invoke(
            completion_request.model_copy(
                update={"expected_candidate_digest": "0" * 64}
            )
        )
        self.assertEqual(wrong_digest.outcome, "error", wrong_digest)
        self.assertFalse(wrong_digest.mutated)
        self.assertEqual(replay(StoreLayout.at(self.root)).head, first.head)
        completed = self.bridge.invoke(completion_request)
        self.assertEqual(completed.outcome, "committed", completed)
        self.assertEqual(completed.completion.transaction_digest, digest)
        self.assertEqual(replay(StoreLayout.at(self.root)).head, digest)
        layout = StoreLayout.at(self.root)
        operational_run = (
            ProjectOperationalLayout.at(layout).runs / first.route_run_id
        )
        transaction_names = {item.name for item in layout.transactions_root.iterdir()}
        operation_names = {
            item.name
            for item in (operational_run / "completion-operations").iterdir()
        }
        receipt_names = {
            item.name for item in (operational_run / "host-receipts").iterdir()
        }
        main_bytes = layout.main_ref.read_bytes()
        replayed_completion = self.bridge.invoke(completion_request)
        self.assertEqual(replayed_completion, completed)
        self.assertEqual(layout.main_ref.read_bytes(), main_bytes)
        self.assertEqual(
            {item.name for item in layout.transactions_root.iterdir()},
            transaction_names,
        )
        self.assertEqual(
            {
                item.name
                for item in (operational_run / "completion-operations").iterdir()
            },
            operation_names,
        )
        self.assertEqual(
            {item.name for item in (operational_run / "host-receipts").iterdir()},
            receipt_names,
        )

        next_route = self.bridge.invoke(
            CodexStartRequestV1(
                project_root=str(self.root),
                session=self.session.model_copy(
                    update={"session_id": "codex-session-after-framing"}
                ),
            )
        )
        self.assertEqual(next_route.outcome, "ready", next_route)
        self.assertTrue(next_route.mutated)
        self.assertEqual(next_route.head, digest)
        self.assertEqual(next_route.work_packet.route_id, "decompose.primitives")
        self.assertIn(
            "Do not confirm G1",
            next_route.work_packet.instruction_text,
        )

        altered = transaction.model_copy(
            update={
                "transaction_id": "transaction.codex.bridge.altered",
                "intent": "A changed source must not retarget an exact retry.",
            }
        )
        candidate_path.write_text(
            json.dumps(altered.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        conflict = self.bridge.invoke(completion_request)
        self.assertEqual(conflict.outcome, "error", conflict)
        self.assertIn(
            "canonically bound to a different transaction",
            conflict.diagnostics[0].message,
        )
        self.assertEqual(replay(StoreLayout.at(self.root)).head, digest)

    def test_explicit_different_brief_cannot_silently_resume_active_run(
        self,
    ) -> None:
        ready = self.bridge.invoke(self._start_request())
        self.assertEqual(ready.outcome, "ready", ready)

        blocked = self.bridge.invoke(
            CodexStartRequestV1(
                project_root=str(self.root),
                requested_scope="Replace the active frame with a different scope.",
                framing_intent="Use a newly chosen primitive restriction.",
                session=self.session.model_copy(
                    update={"session_id": "codex-session-explicit-reframe"}
                ),
            )
        )
        self.assertEqual(blocked.outcome, "blocked", blocked)
        self.assertFalse(blocked.mutated)
        self.assertEqual(
            blocked.diagnostics[0].code,
            "explicit_reframe_requires_disposition",
        )
        self.assertEqual(replay(StoreLayout.at(self.root)).head, ready.head)

        resumed = self.bridge.invoke(
            CodexStartRequestV1(
                project_root=str(self.root),
                session=self.session.model_copy(
                    update={"session_id": "codex-session-ordinary-resume"}
                ),
            )
        )
        self.assertEqual(resumed.outcome, "ready", resumed)
        self.assertEqual(resumed.route_run_id, ready.route_run_id)
        self.assertEqual(resumed.work_packet_hash, ready.work_packet_hash)

    def test_finish_records_terminal_host_receipt_and_same_run_can_resume(
        self,
    ) -> None:
        ready = self.bridge.invoke(self._start_request())
        self.assertEqual(ready.outcome, "ready", ready)
        layout = StoreLayout.at(self.root)
        original_head = replay(layout).head
        valid = self._framing_transaction(ready.route_run_id)
        operations = list(valid.operations)
        frames = operations[2]
        self.assertIsInstance(frames, CreateRelationOp)
        assert isinstance(frames, CreateRelationOp)
        operations[2] = frames.model_copy(
            update={
                "relation": frames.relation.model_copy(
                    update={
                        "source": frames.relation.target,
                        "target": frames.relation.source,
                    }
                )
            }
        )
        invalid = valid.model_copy(
            update={
                "transaction_id": "transaction.codex.bridge.before.finish",
                "operations": tuple(operations),
            }
        )
        candidate_path = self.root / ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(
            json.dumps(invalid.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        rejected = self.bridge.invoke(
            CodexCompleteRequestV1(
                project_root=str(self.root),
                route_run_id=ready.route_run_id,
                work_packet_hash=ready.work_packet_hash,
                delivery_envelope_hash=ready.delivery_envelope_hash,
            )
        )
        self.assertEqual(rejected.outcome, "error", rejected)
        self.assertEqual(replay(layout).head, original_head)
        finish_request = CodexFinishRequestV1(
            project_root=str(self.root),
            route_run_id=ready.route_run_id,
            work_packet_hash=ready.work_packet_hash,
            delivery_envelope_hash=ready.delivery_envelope_hash,
            completion_status="failed_terminal",
            warnings=("retry_budget_exhausted",),
        )

        finished = self.bridge.invoke(finish_request)
        self.assertEqual(finished.outcome, "recorded_failure", finished)
        self.assertTrue(finished.mutated)
        self.assertEqual(finished.completion.status, "recorded_failure")
        self.assertIsNotNone(finished.completion.candidate_digest)
        self.assertEqual(finished.head, original_head)
        self.assertEqual(replay(layout).head, original_head)
        self.assertEqual(read_run(layout, ready.route_run_id).status, "running")
        operational_run = (
            ProjectOperationalLayout.at(layout).runs / ready.route_run_id
        )
        operation_names = {
            item.name
            for item in (operational_run / "completion-operations").iterdir()
        }
        receipt_names = {
            item.name for item in (operational_run / "host-receipts").iterdir()
        }
        self.assertEqual(self.bridge.invoke(finish_request), finished)
        self.assertEqual(
            {
                item.name
                for item in (operational_run / "completion-operations").iterdir()
            },
            operation_names,
        )
        self.assertEqual(
            {item.name for item in (operational_run / "host-receipts").iterdir()},
            receipt_names,
        )

        recovered = self.bridge.invoke(
            CodexStartRequestV1(
                project_root=str(self.root),
                session=self.session.model_copy(
                    update={"session_id": "codex-session-after-terminal-stop"}
                ),
            )
        )
        self.assertEqual(recovered.outcome, "ready", recovered)
        self.assertEqual(recovered.route_run_id, ready.route_run_id)
        self.assertEqual(recovered.work_packet_hash, ready.work_packet_hash)
        self.assertEqual(recovered.head, original_head)

        candidate_path = self.root / recovered.candidate_logical_path
        candidate_path.write_text(
            json.dumps(valid.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        committed = self.bridge.invoke(
            CodexCompleteRequestV1(
                project_root=str(self.root),
                route_run_id=recovered.route_run_id,
                work_packet_hash=recovered.work_packet_hash,
                delivery_envelope_hash=recovered.delivery_envelope_hash,
            )
        )
        self.assertEqual(committed.outcome, "committed", committed)
        self.assertEqual(replay(layout).head, committed.head)

    def test_omitted_decomposition_budget_and_explicit_audit_cap_are_exact(self) -> None:
        layout = StoreLayout.at(self.root)
        start_request = self._start_request()
        self.assertIsNone(start_request.budget_units)

        framing = self.bridge.invoke(start_request)
        self.assertEqual(framing.outcome, "ready", framing)
        self.assertEqual(
            framing.work_packet.route_id, "frame.question_and_benchmarks"
        )
        self.assertEqual(read_context(layout, framing.route_run_id).budget_units, 4_000)
        framing_transaction = self._framing_transaction(framing.route_run_id)
        framing_path = self.root / framing.candidate_logical_path
        framing_path.parent.mkdir(parents=True, exist_ok=True)
        framing_path.write_text(
            json.dumps(framing_transaction.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        framing_completed = self.bridge.invoke(
            CodexCompleteRequestV1(
                project_root=str(self.root),
                route_run_id=framing.route_run_id,
                work_packet_hash=framing.work_packet_hash,
                delivery_envelope_hash=framing.delivery_envelope_hash,
            )
        )
        self.assertEqual(framing_completed.outcome, "committed", framing_completed)

        continuation_request = CodexStartRequestV1(
            project_root=str(self.root),
            session=self.session.model_copy(
                update={"session_id": "codex-session-decomposition"}
            ),
        )
        self.assertIsNone(continuation_request.requested_scope)
        self.assertIsNone(continuation_request.framing_intent)
        decomposition = self.bridge.invoke(continuation_request)
        self.assertEqual(decomposition.outcome, "ready", decomposition)
        self.assertEqual(decomposition.work_packet.route_id, "decompose.primitives")
        self.assertEqual(
            read_context(layout, decomposition.route_run_id).budget_units, 8_000
        )
        decomposition_transaction = self._decomposition_transaction(
            decomposition.route_run_id
        )
        decomposition_path = self.root / decomposition.candidate_logical_path
        decomposition_path.parent.mkdir(parents=True, exist_ok=True)
        decomposition_path.write_text(
            json.dumps(
                decomposition_transaction.model_dump(mode="json"), indent=2
            )
            + "\n",
            encoding="utf-8",
        )
        decomposition_completed = self.bridge.invoke(
            CodexCompleteRequestV1(
                project_root=str(self.root),
                route_run_id=decomposition.route_run_id,
                work_packet_hash=decomposition.work_packet_hash,
                delivery_envelope_hash=decomposition.delivery_envelope_hash,
            )
        )
        self.assertEqual(
            decomposition_completed.outcome,
            "committed",
            decomposition_completed,
        )

        audit_request = CodexStartRequestV1(
            project_root=str(self.root),
            budget_units=10_000,
            session=self.session.model_copy(
                update={"session_id": "codex-session-framing-audit"}
            ),
        )
        self.assertEqual(audit_request.budget_units, 10_000)
        audit = self.bridge.invoke(audit_request)
        self.assertEqual(audit.outcome, "ready", audit)
        self.assertEqual(audit.work_packet.route_id, "audit.framing_economics")
        self.assertNotEqual(audit.work_packet.route_id, "decompose.primitives")
        self.assertEqual(read_context(layout, audit.route_run_id).budget_units, 10_000)

    def test_route_invalid_candidate_can_be_repaired_with_same_auto_digest_request(
        self,
    ) -> None:
        ready = self.bridge.invoke(self._start_request())
        self.assertEqual(ready.outcome, "ready", ready)
        valid = self._framing_transaction(ready.route_run_id)
        operations = list(valid.operations)
        frames = operations[2]
        self.assertIsInstance(frames, CreateRelationOp)
        assert isinstance(frames, CreateRelationOp)
        operations[2] = frames.model_copy(
            update={
                "relation": frames.relation.model_copy(
                    update={
                        "source": frames.relation.target,
                        "target": frames.relation.source,
                    }
                )
            }
        )
        invalid = valid.model_copy(
            update={
                "transaction_id": "transaction.codex.bridge.invalid",
                "operations": tuple(operations),
            }
        )
        candidate_path = self.root / ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text(
            json.dumps(invalid.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        completion_request = CodexCompleteRequestV1(
            project_root=str(self.root),
            route_run_id=ready.route_run_id,
            work_packet_hash=ready.work_packet_hash,
            delivery_envelope_hash=ready.delivery_envelope_hash,
        )
        rejected = self.bridge.invoke(completion_request)
        self.assertEqual(rejected.outcome, "error", rejected)
        self.assertIn("frames must bind", rejected.diagnostics[0].message)
        self.assertEqual(replay(StoreLayout.at(self.root)).head, ready.head)

        candidate_path.write_text(
            json.dumps(valid.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        repaired = self.bridge.invoke(completion_request)
        self.assertEqual(repaired.outcome, "committed", repaired)
        expected = sha256_digest(transaction_bytes(valid))
        self.assertEqual(repaired.completion.transaction_digest, expected)
        self.assertEqual(replay(StoreLayout.at(self.root)).head, expected)

    def test_model_level_candidate_error_is_structured_and_repairable(self) -> None:
        ready = self.bridge.invoke(self._start_request())
        self.assertEqual(ready.outcome, "ready", ready)
        valid = self._framing_transaction(ready.route_run_id)
        operations = list(valid.operations)
        frames = operations[2]
        self.assertIsInstance(frames, CreateRelationOp)
        assert isinstance(frames, CreateRelationOp)
        invalid_data = valid.model_dump(mode="json")
        invalid_data["operations"][2]["relation"]["dependency_mode"] = "hard"

        candidate_path = self.root / ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        completion_request = CodexCompleteRequestV1(
            project_root=str(self.root),
            route_run_id=ready.route_run_id,
            work_packet_hash=ready.work_packet_hash,
            delivery_envelope_hash=ready.delivery_envelope_hash,
        )
        candidate_path.write_text('{"operations":', encoding="utf-8")
        malformed = self.bridge.invoke(completion_request)
        self.assertEqual(malformed.outcome, "error", malformed)
        self.assertEqual(
            malformed.diagnostics[0].code, "codex_candidate_transaction_invalid"
        )
        self.assertEqual(
            malformed.diagnostics[0].details["issues"][0]["type"], "json_invalid"
        )

        candidate_path.write_text(
            json.dumps(invalid_data, indent=2) + "\n", encoding="utf-8"
        )
        rejected = self.bridge.invoke(completion_request)
        self.assertEqual(rejected.outcome, "error", rejected)
        self.assertFalse(rejected.mutated)
        self.assertEqual(
            rejected.diagnostics[0].code, "codex_candidate_transaction_invalid"
        )
        self.assertNotIn("operations.2", rejected.diagnostics[0].message)
        self.assertNotIn("input_value", rejected.diagnostics[0].message)
        details = rejected.diagnostics[0].details
        self.assertEqual(details["model"], "Transaction")
        self.assertTrue(details["repairable"])
        self.assertEqual(
            details["retry_action"],
            "edit_declared_candidate_and_retry_same_request",
        )
        self.assertEqual(details["issue_count"], 1)
        self.assertFalse(details["truncated"])
        self.assertEqual(
            details["issues"][0]["location"],
            ["operations", 2, "relation.create", "relation"],
        )
        self.assertIn(
            "invalidating relations require both exact facet endpoints",
            details["issues"][0]["message"],
        )
        self.assertNotIn("input_value", json.dumps(details))
        self.assertEqual(replay(StoreLayout.at(self.root)).head, ready.head)
        run_root = (
            ProjectOperationalLayout.at(StoreLayout.at(self.root)).runs
            / ready.route_run_id
        )
        self.assertFalse((run_root / "completion-starts").exists())
        self.assertFalse((run_root / "completion-operations").exists())

        candidate_path.write_text(
            json.dumps(valid.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        repaired = self.bridge.invoke(completion_request)
        self.assertEqual(repaired.outcome, "committed", repaired)
        self.assertEqual(
            replay(StoreLayout.at(self.root)).head,
            sha256_digest(transaction_bytes(valid)),
        )

    def test_candidate_source_accepts_one_utf8_bom_without_changing_identity(
        self,
    ) -> None:
        ready = self.bridge.invoke(self._start_request())
        self.assertEqual(ready.outcome, "ready", ready)
        valid = self._framing_transaction(ready.route_run_id)
        candidate_path = self.root / ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        source = (json.dumps(valid.model_dump(mode="json"), indent=2) + "\n").encode(
            "utf-8"
        )
        candidate_path.write_bytes(b"\xef\xbb\xbf" + source)

        completed = self.bridge.invoke(
            CodexCompleteRequestV1(
                project_root=str(self.root),
                route_run_id=ready.route_run_id,
                work_packet_hash=ready.work_packet_hash,
                delivery_envelope_hash=ready.delivery_envelope_hash,
            )
        )

        expected = sha256_digest(transaction_bytes(valid))
        self.assertEqual(completed.outcome, "committed", completed)
        self.assertEqual(completed.completion.candidate_digest, expected)
        self.assertEqual(completed.completion.transaction_digest, expected)
        self.assertEqual(replay(StoreLayout.at(self.root)).head, expected)
        run_root = (
            ProjectOperationalLayout.at(StoreLayout.at(self.root)).runs
            / ready.route_run_id
        )
        captured = run_root / "host-candidates" / "sha256" / f"{expected}.json"
        self.assertEqual(captured.read_bytes(), transaction_bytes(valid))

    def test_candidate_source_rejects_two_utf8_boms(self) -> None:
        ready = self.bridge.invoke(self._start_request())
        self.assertEqual(ready.outcome, "ready", ready)
        valid = self._framing_transaction(ready.route_run_id)
        candidate_path = self.root / ready.candidate_logical_path
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        source = (json.dumps(valid.model_dump(mode="json"), indent=2) + "\n").encode(
            "utf-8"
        )
        candidate_path.write_bytes(b"\xef\xbb\xbf\xef\xbb\xbf" + source)

        rejected = self.bridge.invoke(
            CodexCompleteRequestV1(
                project_root=str(self.root),
                route_run_id=ready.route_run_id,
                work_packet_hash=ready.work_packet_hash,
                delivery_envelope_hash=ready.delivery_envelope_hash,
            )
        )

        self.assertEqual(rejected.outcome, "error", rejected)
        self.assertFalse(rejected.mutated)
        self.assertEqual(
            rejected.diagnostics[0].code,
            "codex_candidate_transaction_invalid",
        )
        self.assertEqual(replay(StoreLayout.at(self.root)).head, ready.head)

    def test_finish_warning_contract_exposes_the_opaque_token_constraint(
        self,
    ) -> None:
        self.assertIn(
            "^[A-Za-z0-9][A-Za-z0-9._:+/@-]{0,127}$",
            json.dumps(codex_bridge_schema("request")),
        )
        with self.assertRaisesRegex(ValueError, "pattern"):
            CodexFinishRequestV1(
                project_root=str(self.root),
                route_run_id="run.warning.contract",
                work_packet_hash="1" * 64,
                delivery_envelope_hash="2" * 64,
                completion_status="failed_terminal",
                warnings=("free text is not an opaque token",),
            )

    def test_ready_response_has_self_contained_route_bound_authoring_contract(
        self,
    ) -> None:
        response = self.bridge.invoke(self._start_request())
        self.assertEqual(response.outcome, "ready", response)
        contract = response.candidate_authoring_contract
        self.assertIsNotNone(contract)
        assert contract is not None
        self.assertEqual(
            response.candidate_authoring_contract_hash,
            candidate_authoring_contract_hash(contract),
        )
        packet = response.work_packet
        assert packet is not None
        run = read_run(StoreLayout.at(self.root), response.route_run_id)
        provenance = transaction_bindings(StoreLayout.at(self.root), run.route_run_id)
        bindings = contract.transaction_bindings
        locations = contract.output_locations
        self.assertEqual(contract.work_packet_hash, response.work_packet_hash)
        self.assertEqual(bindings.project_id, packet.project_id)
        self.assertEqual(bindings.base_revision, packet.base_head)
        self.assertEqual(bindings.parent_transaction_hash, packet.base_head)
        self.assertEqual(bindings.route_run_id, packet.route_run_id)
        self.assertEqual(bindings.route_id, packet.route_id)
        self.assertEqual(bindings.actor, run.actor)
        self.assertEqual(bindings.privacy, packet.privacy_clearance)
        self.assertEqual(bindings.access_compartments, packet.compartments)
        self.assertEqual(bindings.created_at, run.created_at)
        self.assertEqual(
            locations.candidate_logical_path, packet.candidate_logical_path
        )
        self.assertEqual(locations.shadow_logical_root, packet.shadow_logical_root)
        self.assertEqual(bindings.route_run_hash, provenance["route_run_hash"])
        self.assertEqual(
            bindings.context_manifest_hash, provenance["context_manifest_hash"]
        )
        self.assertEqual(
            bindings.compiled_context_hash, provenance["compiled_context_hash"]
        )

        output = contract.output_contract
        self.assertEqual(output.route_id, packet.route_id)
        self.assertEqual(output.route_version, packet.route_version)
        self.assertEqual(
            output.allowed_operation_classes, packet.allowed_operation_classes
        )
        self.assertEqual(
            tuple(item.entity_type for item in output.required_output_entities),
            packet.required_output_entity_types,
        )
        self.assertEqual(
            tuple(item.relation_type for item in output.required_output_relations),
            packet.required_output_relation_types,
        )
        self.assertEqual(contract.transaction_json_schema["title"], "Transaction")
        self.assertEqual(output.relation_json_schema["title"], "RelationVersion")
        self.assertEqual(output.route_outcome_json_schema["title"], "RouteOutcome")
        invariants = {item.invariant_id: item for item in output.model_invariants}
        self.assertEqual(
            set(invariants),
            {
                "relation.trace_only_facets",
                "relation.invalidating_exact_facets",
                "relation.scope_sensitive_xor",
                "relation.version_chain",
            },
        )
        self.assertEqual(
            invariants["relation.invalidating_exact_facets"].model,
            "RelationVersion",
        )
        self.assertIn(
            "trace_only",
            invariants["relation.invalidating_exact_facets"].repair_hint,
        )

        transaction = self._framing_transaction(run.route_run_id)
        parsed = Transaction.model_validate_json(
            transaction_bytes(transaction), strict=True
        )
        self.assertEqual(parsed.project_id, bindings.project_id)
        self.assertEqual(parsed.base_revision, bindings.base_revision)
        self.assertEqual(parsed.parent_transaction_hash, bindings.base_revision)
        self.assertEqual(parsed.route_run_id, bindings.route_run_id)
        self.assertEqual(parsed.route_id, bindings.route_id)
        self.assertEqual(parsed.actor, bindings.actor)
        self.assertEqual(parsed.privacy, bindings.privacy)
        self.assertEqual(parsed.access_compartments, bindings.access_compartments)
        self.assertEqual(parsed.created_at, bindings.created_at)

        entities = {
            operation.entity.entity_type: operation.entity
            for operation in parsed.operations
            if isinstance(operation, CreateEntityOp)
        }
        self.assertEqual(
            tuple(item.entity_type for item in contract.payload_schemas),
            packet.required_output_entity_types,
        )
        for payload_contract in contract.payload_schemas:
            model = THEORY_PAYLOAD_MODELS[payload_contract.entity_type]
            self.assertEqual(
                payload_contract.payload_json_schema,
                model.model_json_schema(mode="validation"),
            )
            entity = entities[payload_contract.entity_type]
            self.assertEqual(entity.project_id, bindings.project_id)
            self.assertEqual(entity.privacy, bindings.privacy)
            self.assertEqual(entity.access_compartments, bindings.access_compartments)
            self.assertEqual(entity.created_at, bindings.created_at)
            facets = entity.facets.model_dump(mode="python")
            for empty_facet in payload_contract.empty_facets:
                self.assertEqual(facets[empty_facet], {})
            envelope = facets[payload_contract.owner_facet]
            self.assertEqual(envelope["schema"], payload_contract.payload_schema_id)
            model.model_validate_json(
                canonical_json_bytes(envelope["payload"]), strict=True
            )

        produced_refs = set()
        route_outcomes = []
        for operation in parsed.operations:
            if isinstance(operation, CreateEntityOp):
                produced_refs.add(
                    EntityVersionRef(
                        entity_id=operation.entity.entity_id,
                        version=operation.entity.version,
                    )
                )
            elif isinstance(operation, CreateRelationOp):
                relation = operation.relation
                self.assertEqual(relation.project_id, bindings.project_id)
                self.assertEqual(relation.privacy, bindings.privacy)
                self.assertEqual(
                    relation.access_compartments, bindings.access_compartments
                )
                self.assertEqual(relation.created_at, bindings.created_at)
                produced_refs.add(
                    RelationVersionRef(
                        relation_id=relation.relation_id,
                        version=relation.version,
                    )
                )
            elif isinstance(operation, RecordRouteOutcomeOp):
                route_outcomes.append(operation.outcome)
        self.assertEqual(len(route_outcomes), 1)
        outcome = route_outcomes[0]
        self.assertEqual(outcome.route_run_id, bindings.route_run_id)
        self.assertEqual(outcome.route_id, bindings.route_id)
        self.assertEqual(outcome.privacy, bindings.privacy)
        self.assertEqual(outcome.access_compartments, bindings.access_compartments)
        self.assertEqual(set(outcome.candidate_refs), produced_refs)

        retried = self.bridge.invoke(self._start_request())
        self.assertEqual(retried.candidate_authoring_contract, contract)
        self.assertEqual(
            retried.candidate_authoring_contract_hash,
            response.candidate_authoring_contract_hash,
        )
        tampered = response.model_dump(mode="json")
        tampered["work_packet"]["purpose"] = "tampered-purpose"
        with self.assertRaisesRegex(
            ValueError, "mismatched candidate authoring contract"
        ):
            CodexBridgeResponseV1.model_validate_json(
                canonical_json_bytes(tampered), strict=True
            )

    def test_private_resumed_packet_is_blocked_before_delivery(self) -> None:
        private_root = self.anchor / "private-paper"
        private_root.mkdir()
        from econ_theorist.machine.models import DiscoveryGrantV1

        grant = DiscoveryGrantV1(
            selected_root=str(private_root),
            allowed_discovery_roots=(str(private_root),),
            ancestor_check_boundary=str(private_root),
            stable_workspace_root=str(private_root),
        )
        bind_or_initialize_project(
            private_root,
            discovery_grant=grant,
            initialize=True,
            project_name="Private bridge fixture",
            actor_id="human.owner",
            operation_key="initialize.private.codex",
            reserved_at=NOW,
            operational_home=self.anchor / "local-operations",
        )
        layout = StoreLayout.at(private_root)
        snapshot = replay(layout)
        actor = Actor(kind="agent", actor_id="scientific_agent")
        brief = RunInputBriefV1(
            project_id=snapshot.project_id,
            base_head=snapshot.head,
            requested_scope="Frame one private theory question.",
            framing_intent="A private pilot must not leave the local engine.",
            privacy="project_private",
            compartments=("project_research",),
            actor_role=actor.actor_id,
        )
        navigation = plan_next(
            layout,
            snapshot,
            actor=actor,
            compartments=("project_research",),
            privacy_clearance="project_private",
            budget_units=10_000,
            run_input_brief=brief,
        )
        open_or_resume_run(
            layout,
            operation_key="open.private.codex",
            reserved_at=NOW,
            candidate=navigation.candidates[0],
            run_input_brief=brief,
            operational=ProjectOperationalLayout.at(layout),
        )

        blocked = self.bridge.invoke(
            CodexStartRequestV1(
                project_root=str(private_root),
                session=self.session,
            )
        )
        self.assertEqual(blocked.outcome, "blocked", blocked)
        self.assertEqual(blocked.diagnostics[0].code, "codex_public_pilot_only")
        self.assertIsNone(blocked.delivery_envelope_hash)
        egress = ProjectOperationalLayout.at(layout).egress
        self.assertTrue(egress.is_dir())
        self.assertEqual(tuple(egress.iterdir()), ())

        virgin_root = self.anchor / "virgin-no-consent"
        virgin_root.mkdir()
        not_initialized = self.bridge.invoke(
            CodexStartRequestV1(
                project_root=str(virgin_root),
                session=self.session,
            )
        )
        self.assertEqual(not_initialized.outcome, "blocked")
        self.assertEqual(
            not_initialized.diagnostics[0].code,
            "codex_project_initialization_required",
        )
        self.assertFalse((virgin_root / ".econ-theorist").exists())

    def test_cli_schema_and_strict_transport_are_machine_readable(self) -> None:
        request_schema = codex_bridge_schema("request")
        response_schema = codex_bridge_schema("response")
        self.assertIn("oneOf", request_schema)
        self.assertIn("CodexFinishRequestV1", request_schema["$defs"])
        start_properties = request_schema["$defs"]["CodexStartRequestV1"][
            "properties"
        ]
        self.assertIn(
            "Omit for ordinary continuation",
            start_properties["requested_scope"]["description"],
        )
        self.assertIn(
            "omit for ordinary continuation",
            start_properties["framing_intent"]["description"],
        )
        self.assertEqual(response_schema["title"], "CodexBridgeResponseV1")
        parsed = build_parser().parse_args(
            ["codex", "invoke", "--schema", "bundle"]
        )
        self.assertEqual(parsed.schema, "bundle")
        self.assertIsNone(self._start_request().budget_units)
        explicit_null = CodexStartRequestV1.model_validate_json(
            canonical_json_bytes(
                {
                    **self._start_request().model_dump(mode="json"),
                    "budget_units": None,
                }
            ),
            strict=True,
        )
        self.assertIsNone(explicit_null.budget_units)
        with self.assertRaises(ValueError):
            CodexStartRequestV1.model_validate_json(
                canonical_json_bytes(
                    {
                        **self._start_request().model_dump(mode="json"),
                        "budget_units": 0,
                    }
                ),
                strict=True,
            )
        environment = os.environ.copy()
        environment["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
        emitted = subprocess.run(
            [
                sys.executable,
                "-c",
                (
                    "from econ_theorist.cli import main; "
                    "raise SystemExit(main(['codex','invoke','--schema','bundle']))"
                ),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=environment,
            check=False,
        )
        self.assertEqual(emitted.returncode, 0, emitted.stderr.decode("utf-8"))
        self.assertEqual(emitted.stdout.count(b"\n"), 1)
        self.assertEqual(
            json.loads(emitted.stdout)["schema_bundle"],
            "econ-theorist/codex-bridge-schema-bundle/v1",
        )

        response = invoke_codex_bytes(
            canonical_json_bytes(self._start_request()), bridge=self.bridge
        )
        self.assertEqual(response.outcome, "ready", response)
        invalid = invoke_codex_bytes(b'{"operation":"start_or_resume"}')
        self.assertEqual(invalid.outcome, "error")
        self.assertEqual(
            invalid.diagnostics[0].code, "invalid_codex_bridge_request"
        )
        invalid_finish = invoke_codex_bytes(b'{"operation":"finish"}')
        self.assertEqual(invalid_finish.operation, "finish")
        self.assertEqual(invalid_finish.outcome, "error")

    def test_default_private_genesis_bytes_and_ids_remain_unchanged(self) -> None:
        arguments = {
            "name": "Historical default",
            "actor_id": "human.owner",
            "project_id": "prj_historical_default",
            "created_at": NOW,
            "transaction_id": "txn_historical_default",
            "route_run_id": "run_historical_default",
        }
        implicit = _genesis_transaction(**arguments)
        explicit = _genesis_transaction(
            **arguments, project_privacy="project_private"
        )
        public = _genesis_transaction(**arguments, project_privacy="public")
        self.assertEqual(transaction_bytes(implicit), transaction_bytes(explicit))
        self.assertNotEqual(transaction_bytes(implicit), transaction_bytes(public))

        root = self.anchor / "stable-id-root"
        root.mkdir()
        operation_key = "initialize.historical.default"
        default_ids = _deterministic_genesis_ids(
            root, operation_key, "Historical default"
        )
        expected_seed = sha256_digest(
            canonical_json_bytes(
                {
                    "project_root": str(root),
                    "operation_key": operation_key,
                    "project_name": "Historical default",
                }
            )
        )
        self.assertEqual(default_ids[0], f"prj_{expected_seed[:48]}")
        self.assertNotEqual(
            default_ids,
            _deterministic_genesis_ids(
                root, operation_key, "Historical default", "public"
            ),
        )


if __name__ == "__main__":
    unittest.main()
