"""Runtime integration contracts for versioned Phase 2 theory payloads."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import sha256_digest, transaction_bytes
from econ_theorist.models import (
    Actor,
    ArtifactRegistration,
    CreateEntityOp,
    CreateRelationOp,
    EntityVersion,
    EntityVersionRef,
    FacetPayloads,
    RegisterArtifactOp,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    RouteRun,
    ScientificStatus,
    Transaction,
)
from econ_theorist.policy import (
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V5_HASH,
)
from econ_theorist.project import init_project
from econ_theorist.runs import (
    RouteEntryError,
    begin_run,
    read_context,
    transaction_bindings,
)
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import (
    CandidateError,
    commit_prepared,
    preflight_candidate,
)
from econ_theorist.runtime.replay import CandidateValidationError, replay
from econ_theorist.staging import (
    commit_run,
    read_staged_transaction,
    stage_candidate,
)
from econ_theorist.theory import (
    BenchmarkRecord,
    BenchmarkSet,
    ResearchQuestion,
    pack_theory_payload,
)


NOW = "2026-07-11T14:00:00Z"
ACTOR = Actor(kind="agent", actor_id="theory.agent")


class Phase2RuntimeIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.layout = StoreLayout.at(self.root)
        self.snapshot = init_project(
            self.root,
            name="Phase 2 runtime integration",
            actor_id="human.owner",
            project_id="project.phase2.runtime",
            created_at=NOW,
        )

    def _begin(self, *, registry_hash: str | None = None) -> RouteRun:
        return begin_run(
            self.layout,
            self.snapshot,
            route_id="frame.question_and_benchmarks",
            actor=ACTOR,
            purpose="research_framing",
            compartments=("project_research",),
            focus_entity_ids=(self.snapshot.project_id,),
            budget_units=4_000,
            route_registry_hash=registry_hash,
        )

    def _question(self, *, typed: bool) -> EntityVersion:
        facets = (
            pack_theory_payload(
                ResearchQuestion(
                    phenomenon="A comparative static can reverse.",
                    object_to_explain="The reversal.",
                    unresolved_delta="The benchmark fixes participation.",
                    importance="Participation changes the policy ranking.",
                    kill_condition="The fixed-participation benchmark reverses too.",
                    proposed_scope="A finite-state decision problem.",
                    candidate_archetypes=("mechanism_explanation",),
                )
            )
            if typed
            else FacetPayloads(
                formal={"statement": "Why can the comparative static reverse?"}
            )
        )
        return EntityVersion(
            entity_id="question.runtime",
            entity_type="ResearchQuestion",
            version=1,
            project_id=self.snapshot.project_id,
            title="Runtime question",
            summary="An exact runtime-bound framing candidate.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=facets,
            created_at=NOW,
        )

    def _benchmark(self, question: EntityVersion) -> EntityVersion:
        question_ref = EntityVersionRef(
            entity_id=question.entity_id, version=question.version
        )
        return EntityVersion(
            entity_id="benchmarks.runtime",
            entity_type="BenchmarkSet",
            version=1,
            project_id=self.snapshot.project_id,
            title="Runtime benchmarks",
            summary="The exact benchmark delta for the runtime question.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                BenchmarkSet(
                    question_ref=question_ref,
                    benchmarks=(
                        BenchmarkRecord(
                            benchmark_id="benchmark.runtime",
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

    def _framing_relations(
        self, question: EntityVersion, benchmark: EntityVersion
    ) -> tuple[RelationVersion, RelationVersion]:
        question_ref = EntityVersionRef(
            entity_id=question.entity_id, version=question.version
        )
        benchmark_ref = EntityVersionRef(
            entity_id=benchmark.entity_id, version=benchmark.version
        )
        return (
            RelationVersion(
                relation_id="relation.runtime.frames",
                relation_type="frames",
                version=1,
                project_id=self.snapshot.project_id,
                source=question_ref,
                target=benchmark_ref,
                dependency_mode="trace_only",
                created_at=NOW,
            ),
            RelationVersion(
                relation_id="relation.runtime.benchmark_delta",
                relation_type="benchmark_delta",
                version=1,
                project_id=self.snapshot.project_id,
                source=benchmark_ref,
                target=question_ref,
                dependency_mode="trace_only",
                created_at=NOW,
            ),
        )
    def _transaction(
        self,
        run: RouteRun,
        question: EntityVersion,
        *,
        include_outcome: bool,
        full_bundle: bool = False,
    ) -> Transaction:
        operations: list[
            CreateEntityOp | CreateRelationOp | RecordRouteOutcomeOp
        ] = [
            CreateEntityOp(entity=question)
        ]
        candidate_refs: list[EntityVersionRef | RelationVersionRef] = [
            EntityVersionRef(entity_id=question.entity_id, version=question.version)
        ]
        if full_bundle:
            benchmark = self._benchmark(question)
            relations = self._framing_relations(question, benchmark)
            operations.append(CreateEntityOp(entity=benchmark))
            operations.extend(CreateRelationOp(relation=item) for item in relations)
            candidate_refs.append(
                EntityVersionRef(
                    entity_id=benchmark.entity_id, version=benchmark.version
                )
            )
            candidate_refs.extend(
                RelationVersionRef(
                    relation_id=item.relation_id, version=item.version
                )
                for item in relations
            )
        if include_outcome:
            operations.append(
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run.route_run_id,
                        route_id=run.route_id,
                        outcome="completed_with_candidate",
                        rationale="The framing route produced one complete exact bundle.",
                        candidate_refs=tuple(candidate_refs),
                    )
                )
            )
        return Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id="transaction.question.runtime",
            origin="route_run",
            project_id=self.snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=ACTOR,
            intent="Frame one exact research question.",
            operations=tuple(operations),
            created_at=NOW,
            parent_transaction_hash=run.base_revision,
        )

    def _stage(self, run: RouteRun, transaction: Transaction) -> str:
        path = self.root / "candidate.json"
        path.write_bytes(transaction_bytes(transaction))
        return stage_candidate(
            self.layout,
            run.route_run_id,
            path,
        )

    def test_active_catalog_preserves_phase2_rejection_of_untyped_question(self) -> None:
        run = self._begin()
        self.assertEqual(
            read_context(self.layout, run.route_run_id).route_registry_hash,
            ROUTE_REGISTRY_V5_HASH,
        )
        transaction = self._transaction(
            run, self._question(typed=False), include_outcome=True
        )
        self._stage(run, transaction)

        with self.assertRaisesRegex(
            CandidateValidationError,
            r"Phase 2 route contract rejected.*invalid ResearchQuestion",
        ):
            commit_run(self.layout, run.route_run_id)

        unchanged = replay(self.layout)
        self.assertEqual(unchanged.head, self.snapshot.head)
        self.assertNotIn("question.runtime", unchanged.current_entities)

    def test_active_catalog_preserves_phase2_route_outcome_requirement(self) -> None:
        run = self._begin()
        transaction = self._transaction(
            run,
            self._question(typed=True),
            include_outcome=False,
            full_bundle=True,
        )
        self._stage(run, transaction)

        with self.assertRaisesRegex(
            CandidateValidationError,
            r"requires exactly one RouteOutcome",
        ):
            commit_run(self.layout, run.route_run_id)

        unchanged = replay(self.layout)
        self.assertEqual(unchanged.head, self.snapshot.head)
        self.assertNotIn("question.runtime", unchanged.current_entities)

    def test_typed_question_and_exact_outcome_prepare_commit_and_replay(self) -> None:
        run = self._begin()
        question = self._question(typed=True)
        transaction = self._transaction(
            run, question, include_outcome=True, full_bundle=True
        )
        digest = self._stage(run, transaction)

        staged = read_staged_transaction(self.layout, run.route_run_id, digest)
        prepared = preflight_candidate(self.layout, staged)
        result = commit_prepared(self.layout, prepared)

        self.assertEqual(result.status, "committed")
        committed = replay(self.layout)
        self.assertEqual(committed.head, result.head_after)
        self.assertEqual(committed.current_entities[question.entity_id], 1)
        self.assertEqual(committed.current_entities["benchmarks.runtime"], 1)
        self.assertIn(question, committed.entity_versions)
        self.assertEqual(len(committed.route_outcomes), 1)
        self.assertEqual(
            committed.route_outcomes[0].candidate_refs,
            (
                EntityVersionRef(entity_id=question.entity_id, version=1),
                EntityVersionRef(entity_id="benchmarks.runtime", version=1),
                RelationVersionRef(
                    relation_id="relation.runtime.frames", version=1
                ),
                RelationVersionRef(
                    relation_id="relation.runtime.benchmark_delta", version=1
                ),
            ),
        )
        with self.assertRaisesRegex(RouteEntryError, r"v1 routes are replay-only"):
            begin_run(
                self.layout,
                committed,
                route_id="frame.question_and_benchmarks",
                actor=ACTOR,
                purpose="research_framing",
                compartments=("project_research",),
                focus_entity_ids=(committed.project_id,),
                route_registry_hash=ROUTE_REGISTRY_V1_HASH,
            )

    def test_frozen_v1_cannot_create_a_packed_phase2_entity(self) -> None:
        run = self._begin(registry_hash=ROUTE_REGISTRY_V1_HASH)
        transaction = self._transaction(
            run, self._question(typed=True), include_outcome=False
        )
        self._stage(run, transaction)

        with self.assertRaisesRegex(
            CandidateError, r"v1 live writes cannot create or mutate packed Phase 2"
        ):
            commit_run(self.layout, run.route_run_id)

        unchanged = replay(self.layout)
        self.assertEqual(unchanged.head, self.snapshot.head)
        self.assertNotIn("question.runtime", unchanged.current_entities)

    def test_frozen_v1_cannot_register_a_candidate_lock_by_id_or_media_type(self) -> None:
        data = b"canonical candidate bytes"
        cases = (
            (
                "candidate.lock.attempt.downgrade",
                "application/octet-stream",
            ),
            (
                "artifact.disguised.candidate_lock",
                "application/vnd.econ-theorist.candidate-lock+json",
            ),
        )
        for index, (artifact_id, media_type) in enumerate(cases, start=1):
            with self.subTest(artifact_id=artifact_id, media_type=media_type):
                run = self._begin(registry_hash=ROUTE_REGISTRY_V1_HASH)
                registration = ArtifactRegistration(
                    artifact_id=artifact_id,
                    version=1,
                    project_id=self.snapshot.project_id,
                    logical_name="Disallowed legacy blind lock",
                    media_type=media_type,
                    content_hash=sha256_digest(data),
                    byte_size=len(data),
                    created_at=NOW,
                )
                transaction = Transaction(
                    **transaction_bindings(self.layout, run.route_run_id),
                    transaction_id=f"transaction.candidate.lock.downgrade.{index}",
                    origin="route_run",
                    project_id=self.snapshot.project_id,
                    base_revision=run.base_revision,
                    route_run_id=run.route_run_id,
                    route_id=run.route_id,
                    actor=ACTOR,
                    intent="Attempt to bypass the v2 candidate-lock contract.",
                    operations=(RegisterArtifactOp(artifact=registration),),
                    created_at=NOW,
                    parent_transaction_hash=run.base_revision,
                )
                candidate = self.root / f"candidate-lock-{index}.json"
                artifact = self.root / f"candidate-lock-{index}.bin"
                candidate.write_bytes(transaction_bytes(transaction))
                artifact.write_bytes(data)
                stage_candidate(
                    self.layout,
                    run.route_run_id,
                    candidate,
                    artifacts={artifact_id: artifact},
                )

                with self.assertRaisesRegex(
                    CandidateError, r"register blind candidate locks"
                ):
                    commit_run(self.layout, run.route_run_id)

                self.assertEqual(replay(self.layout).head, self.snapshot.head)

    def test_frozen_v1_generic_research_question_still_commits_and_replays(self) -> None:
        run = self._begin(registry_hash=ROUTE_REGISTRY_V1_HASH)
        self.assertEqual(
            read_context(self.layout, run.route_run_id).route_registry_hash,
            ROUTE_REGISTRY_V1_HASH,
        )
        question = self._question(typed=False)
        transaction = self._transaction(run, question, include_outcome=False)
        self._stage(run, transaction)

        result = commit_run(self.layout, run.route_run_id)

        self.assertEqual(result.status, "committed")
        committed = replay(self.layout)
        self.assertEqual(committed.head, result.head_after)
        self.assertEqual(committed.current_entities[question.entity_id], 1)
        self.assertEqual(committed.entity_versions[-1], question)
        self.assertEqual(committed.route_outcomes, ())


if __name__ == "__main__":
    unittest.main()
