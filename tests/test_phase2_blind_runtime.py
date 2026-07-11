"""Canonical ObjectStore runtime path for one sealed blind attempt.

The scientific inputs are installed as an explicitly historical, content-
addressed v1 fixture and then replay-validated before use. Live v1 writes are
not used and cannot bypass the v2 scientific contracts. The two blind routes
themselves must use their active v2 contracts and the complete
begin -> compile -> stage -> preflight -> commit -> replay path.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase2_blind_evaluation_contract import (
    ATTEMPT,
    BUILDER,
    EVALUATOR,
    GENERATOR,
    SEALED,
    BlindProtocolFixture,
)
from tests.test_phase2_scientific_closure import CREATED_AT, HUMAN, PROJECT_ID

from econ_theorist.codec import canonical_json_bytes, sha256_digest, transaction_bytes
from econ_theorist.context import compile_context, make_context_manifest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    EntityVersion,
    EntityVersionRef,
    FacetPayloads,
    RecordDecisionOp,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    RouteRun,
    ScientificStatus,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V1_HASH, ROUTE_REGISTRY_V2_HASH
from econ_theorist.route_registry import authorize_route
from econ_theorist.runs import (
    RouteEntryError,
    begin_run,
    read_compiled_context,
    read_context,
    transaction_bindings,
)
from econ_theorist.runtime import HeadStore, ObjectStore, StoreLayout
from econ_theorist.runtime.commit import (
    StagedArtifact,
    commit_prepared,
    commit_transaction,
    preflight_candidate,
)
from econ_theorist.runtime.replay import replay, validate_candidate
from econ_theorist.staging import (
    read_staged_transaction,
    stage_candidate,
    staged_artifact_path,
)
from econ_theorist.theory import (
    VAPComparisonRecord,
    pack_theory_payload,
    parse_theory_entity,
)


SEED_ACTOR = Actor(kind="agent", actor_id="agent.blind.runtime.seed")
RUNTIME_COMPARTMENTS = (
    "blind_evaluator",
    "confirmatory_holdout",
    "project_research",
)
PREPARE_GRANTS = (
    "blind_case_builder",
    "blind_evaluator",
    "blind_generator",
    "confirmatory_holdout",
    "project_research",
)


def _eref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def _aref(artifact: ArtifactRegistration) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact.artifact_id,
        version=artifact.version,
        content_hash=artifact.content_hash,
    )


def _rewrite_prediction_versions(value: object, prediction_ids: set[str]) -> object:
    if isinstance(value, dict):
        rewritten = {
            key: _rewrite_prediction_versions(item, prediction_ids)
            for key, item in value.items()
        }
        if (
            rewritten.get("entity_id") in prediction_ids
            and rewritten.get("version") == 2
        ):
            rewritten["version"] = 1
        return rewritten
    if isinstance(value, tuple):
        return tuple(
            _rewrite_prediction_versions(item, prediction_ids) for item in value
        )
    if isinstance(value, list):
        return [
            _rewrite_prediction_versions(item, prediction_ids) for item in value
        ]
    return value


class Phase2BlindRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.layout = StoreLayout.at(self.root)
        project = EntityVersion(
            entity_id=PROJECT_ID,
            entity_type="Project",
            version=1,
            project_id=PROJECT_ID,
            title="Canonical blind evaluation runtime",
            summary="A deterministic test project for one sealed blind attempt.",
            status=ScientificStatus(lifecycle="active"),
            facets=FacetPayloads(
                terminology_presentation={"project_name": "Blind runtime"},
                authority={"scope": "economic_theory_only"},
            ),
            created_at="2026-07-11T15:59:00Z",
        )
        genesis = Transaction(
            transaction_id="transaction.blind.runtime.genesis",
            origin="genesis",
            project_id=PROJECT_ID,
            base_revision=None,
            route_run_id="run.blind.runtime.genesis",
            actor=HUMAN,
            intent="Create the deterministic blind-runtime fixture project.",
            operations=(CreateEntityOp(entity=project),),
            created_at="2026-07-11T15:59:00Z",
            parent_transaction_hash=None,
        )
        self.assertEqual(commit_transaction(self.layout, genesis).status, "committed")
        self.snapshot = replay(self.layout)
        self.fixture = BlindProtocolFixture()

        # A candidate is shared with the evaluator but the gold remains sealed.
        # The transformed brief itself contains no hidden artifact bytes.
        transformed = self.fixture.entities[
            (self.fixture.transformed_brief_ref.entity_id, 1)
        ]
        self.fixture.entities[(transformed.entity_id, 1)] = transformed.model_copy(
            update={"access_compartments": ("project_research",)}
        )
        candidate = self.fixture.entities[(self.fixture.candidate_ref.entity_id, 1)]
        self.fixture.entities[(candidate.entity_id, 1)] = candidate.model_copy(
            update={
                "privacy": "restricted",
                "access_compartments": RUNTIME_COMPARTMENTS,
            }
        )
        gold = self.fixture.entities[(self.fixture.gold_ref.entity_id, 1)]
        self.fixture.entities[(gold.entity_id, 1)] = gold.model_copy(
            update={"access_compartments": RUNTIME_COMPARTMENTS}
        )
        self.fixture.sealed_artifacts = tuple(
            item.model_copy(update={"access_compartments": RUNTIME_COMPARTMENTS})
            for item in self.fixture.sealed_artifacts
        )
        self.fixture.manifest = self.fixture.manifest.model_copy(
            update={"access_compartments": RUNTIME_COMPARTMENTS}
        )
        self.fixture.variant = self.fixture.variant.model_copy(
            update={"access_compartments": RUNTIME_COMPARTMENTS}
        )
        self._collapse_prediction_history()
        attempt_scope = EntityVersion(
            entity_id=ATTEMPT,
            entity_type="BlindAttempt",
            version=1,
            project_id=PROJECT_ID,
            title="Canonical blind attempt scope",
            summary="Exact runtime scope for the implementation-freeze Decision.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=FacetPayloads(
                authority={"attempt_id": ATTEMPT, "state": "implementation_frozen"}
            ),
            created_at=CREATED_AT,
        )
        self.fixture.entities[(attempt_scope.entity_id, 1)] = attempt_scope
        self.route_counter = 0

    def _collapse_prediction_history(self) -> None:
        """Keep the closed fixture seed create-only without changing its science."""

        prediction_ids = {
            "predictions.closure",
            self.fixture.entity_ids["predictions.closure"],
        }
        for prediction_id in prediction_ids:
            version_two = self.fixture.entities[(prediction_id, 2)]
            reconciled = parse_theory_entity(version_two)
            version_one = self.fixture.entities[(prediction_id, 1)]
            self.fixture.entities[(prediction_id, 1)] = version_one.model_copy(
                update={"facets": pack_theory_payload(reconciled)}
            )
            del self.fixture.entities[(prediction_id, 2)]
        for key, entity in tuple(self.fixture.entities.items()):
            payload = parse_theory_entity(entity)
            rewritten = _rewrite_prediction_versions(
                payload.model_dump(mode="python"), prediction_ids
            )
            rewritten_payload = type(payload).model_validate(rewritten)
            self.fixture.entities[key] = entity.model_copy(
                update={"facets": pack_theory_payload(rewritten_payload)}
            )

    def _stage_preflight_commit(
        self,
        *,
        run: RouteRun,
        transaction: Transaction,
        artifact_bytes: dict[str, bytes],
        label: str,
    ):
        candidate_path = self.root / f"candidate-{label}.json"
        candidate_path.write_bytes(transaction_bytes(transaction))
        paths: dict[str, Path] = {}
        registrations = {
            operation.artifact.artifact_id: operation.artifact
            for operation in transaction.operations
            if isinstance(operation, RegisterArtifactOp)
        }
        for index, (artifact_id, data) in enumerate(sorted(artifact_bytes.items())):
            path = self.root / f"artifact-{label}-{index}.bin"
            path.write_bytes(data)
            paths[artifact_id] = path
        digest = stage_candidate(
            self.layout,
            run.route_run_id,
            candidate_path,
            artifacts=paths,
        )
        staged = read_staged_transaction(self.layout, run.route_run_id, digest)
        self.assertEqual(staged, transaction)
        prepared = preflight_candidate(
            self.layout,
            staged,
            tuple(
                StagedArtifact(
                    artifact_id=registration.artifact_id,
                    version=registration.version,
                    path=staged_artifact_path(
                        self.layout,
                        run.route_run_id,
                        registration.content_hash,
                    ),
                )
                for registration in registrations.values()
            ),
        )
        result = commit_prepared(self.layout, prepared)
        self.assertEqual(result.status, "committed")
        committed = replay(self.layout)
        self.assertEqual(committed.head, result.head_after)
        self.snapshot = committed
        return result, committed

    def _begin(
        self,
        *,
        route_id: str,
        actor: Actor,
        purpose: str,
        compartments: tuple[str, ...],
        focus_entity_ids: tuple[str, ...],
        registry_hash: str,
        privacy_clearance: str,
        label: str,
    ) -> tuple[RouteRun, object, dict[str, object]]:
        self.route_counter += 1
        run = begin_run(
            self.layout,
            self.snapshot,
            route_id=route_id,
            actor=actor,
            purpose=purpose,
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            focus_entity_ids=focus_entity_ids,
            budget_units=2_000_000,
            route_run_id=f"run.blind.runtime.{self.route_counter}.{label}",
            context_manifest_id=f"context.blind.runtime.{self.route_counter}.{label}",
            created_at=f"2026-07-11T17:{self.route_counter:02d}:00Z",
            route_registry_hash=registry_hash,
        )
        manifest = read_context(self.layout, run.route_run_id)
        compiled = read_compiled_context(self.layout, run.route_run_id)
        self.assertEqual(manifest.source_head, self.snapshot.head)
        self.assertEqual(compiled["source_head"], self.snapshot.head)
        self.assertEqual(compiled["route"]["route_id"], route_id)
        return run, manifest, compiled

    def _install_historical_seed_route(
        self,
        *,
        outputs: tuple[EntityVersion, ...],
        artifacts: tuple[tuple[ArtifactRegistration, bytes], ...],
        label: str,
        restricted: bool,
    ) -> None:
        """Install replay-valid old history without exercising a live v1 write."""

        compartments = RUNTIME_COMPARTMENTS if restricted else ("project_research",)
        privacy_clearance = "restricted" if restricted else "project_private"
        self.route_counter += 1
        route = authorize_route(
            "frame.question_and_benchmarks",
            purpose="research_framing",
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            route_registry_hash=ROUTE_REGISTRY_V1_HASH,
        )
        compiled = compile_context(
            self.snapshot,
            route=route,
            actor=SEED_ACTOR,
            purpose="research_framing",
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            focus_entity_ids=(PROJECT_ID,),
            budget_units=2_000_000,
            layout=self.layout,
        )
        run_id = f"run.blind.runtime.{self.route_counter}.{label}"
        context_id = f"context.blind.runtime.{self.route_counter}.{label}"
        timestamp = f"2026-07-11T17:{self.route_counter:02d}:00Z"
        manifest = make_context_manifest(
            compiled,
            context_manifest_id=context_id,
            snapshot=self.snapshot,
            route=route,
            actor=SEED_ACTOR,
            purpose="research_framing",
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            focus_entity_ids=(PROJECT_ID,),
            budget_units=2_000_000,
            created_at=timestamp,
        )
        run = RouteRun(
            route_run_id=run_id,
            project_id=PROJECT_ID,
            base_revision=self.snapshot.head,
            route_id=route.route_id,
            route_version=route.route_version,
            actor=SEED_ACTOR,
            purpose="research_framing",
            compartments=tuple(sorted(compartments)),
            privacy_clearance=privacy_clearance,
            focus_entity_ids=(PROJECT_ID,),
            context_manifest_id=context_id,
            context_hash=compiled.context_hash,
            status="running",
            created_at=timestamp,
        )
        run_bytes = canonical_json_bytes(run)
        manifest_bytes = canonical_json_bytes(manifest)
        provenance = {
            sha256_digest(run_bytes): run_bytes,
            sha256_digest(manifest_bytes): manifest_bytes,
            compiled.context_hash: compiled.encoded,
        }
        transaction = Transaction(
            route_run_hash=sha256_digest(run_bytes),
            context_manifest_hash=sha256_digest(manifest_bytes),
            compiled_context_hash=compiled.context_hash,
            transaction_id=f"transaction.blind.runtime.seed.{label}",
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=SEED_ACTOR,
            intent="Install a closed canonical blind-runtime seed projection.",
            operations=(
                *(RegisterArtifactOp(artifact=item) for item, _ in artifacts),
                *(CreateEntityOp(entity=item) for item in outputs),
            ),
            privacy=("restricted" if restricted else "project_private"),
            access_compartments=compartments,
            created_at="2026-07-11T17:10:00Z",
            parent_transaction_hash=run.base_revision,
        )
        expected = validate_candidate(
            self.snapshot,
            transaction,
            route_registry_hash=ROUTE_REGISTRY_V1_HASH,
        )
        objects = ObjectStore(self.layout)
        for registration, data in artifacts:
            self.assertEqual(sha256_digest(data), registration.content_hash)
            self.assertEqual(len(data), registration.byte_size)
            objects.install_bytes("artifacts", registration.content_hash, data)
        for digest, data in provenance.items():
            objects.install_bytes("provenance", digest, data)
        body = transaction_bytes(transaction)
        digest = sha256_digest(body)
        self.assertEqual(expected.head, digest)
        objects.install_bytes("transactions", digest, body)
        HeadStore(self.layout).replace(self.snapshot.head, digest)
        self.snapshot = replay(self.layout)
        self.assertEqual(self.snapshot, expected)

    def _record_human_decisions(self) -> None:
        by_kind: dict[str, list[Decision]] = {}
        for decision in self.fixture.decisions.values():
            by_kind.setdefault(decision.decision_kind, []).append(decision)
        order = (
            "G1_question_benchmark",
            "G2_mechanism",
            "G3_formal_base",
            "G4_result_investment",
            "theory_mode",
        )
        for index, kind in enumerate(order, start=1):
            decisions = tuple(by_kind.get(kind, ()))
            self.assertTrue(decisions)
            before = replay(self.layout)
            transaction = Transaction(
                transaction_id=f"transaction.blind.runtime.decision.{index}",
                origin="human_decision",
                project_id=PROJECT_ID,
                base_revision=before.head,
                route_run_id=f"run.blind.runtime.decision.{index}",
                actor=HUMAN,
                intent=f"Record exact canonical {kind} authority for the seed.",
                operations=tuple(
                    RecordDecisionOp(decision=item) for item in decisions
                ),
                created_at=f"2026-07-11T17:{10 + index:02d}:00Z",
                parent_transaction_hash=before.head,
            )
            result = commit_transaction(self.layout, transaction)
            self.assertEqual(result.status, "committed")
            self.snapshot = replay(self.layout)

    def _candidate_lock(self) -> tuple[ArtifactRegistration, bytes]:
        candidate = self.fixture.entities[(self.fixture.candidate_ref.entity_id, 1)]
        data = canonical_json_bytes(candidate)
        registration = ArtifactRegistration(
            artifact_id=f"candidate.lock.{ATTEMPT}",
            version=1,
            project_id=PROJECT_ID,
            logical_name="Exact prior blind candidate lock",
            media_type="application/vnd.econ-theorist.candidate-lock+json",
            content_hash=sha256_digest(data),
            byte_size=len(data),
            privacy="restricted",
            access_compartments=RUNTIME_COMPARTMENTS,
            created_at="2026-07-11T17:16:00Z",
        )
        return registration, data

    def _prepare_transaction(
        self, run: RouteRun
    ) -> tuple[Transaction, dict[str, bytes]]:
        relation_compartments = RUNTIME_COMPARTMENTS
        seals = self.fixture.prepare_relations[0].model_copy(
            update={
                "privacy": "restricted",
                "access_compartments": relation_compartments,
            }
        )
        transforms = self.fixture.prepare_relations[1].model_copy(
            update={
                "privacy": "restricted",
                "access_compartments": relation_compartments,
            }
        )
        artifacts = self.fixture.sealed_artifacts
        candidate_refs = (
            _eref(self.fixture.manifest),
            _eref(self.fixture.variant),
            RelationVersionRef(relation_id=seals.relation_id, version=1),
            RelationVersionRef(relation_id=transforms.relation_id, version=1),
            *(_aref(item) for item in artifacts),
        )
        outcome = RouteOutcome(
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            outcome="completed_with_candidate",
            rationale="Seal the exact transformed attempt and hidden bytes.",
            candidate_refs=candidate_refs,
            privacy="restricted",
            access_compartments=RUNTIME_COMPARTMENTS,
        )
        transaction = Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id="transaction.blind.runtime.prepare",
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=BUILDER,
            intent="Prepare one immutable transformed blind case.",
            operations=(
                *(RegisterArtifactOp(artifact=item) for item in artifacts),
                CreateEntityOp(entity=self.fixture.manifest),
                CreateEntityOp(entity=self.fixture.variant),
                CreateRelationOp(relation=seals),
                CreateRelationOp(relation=transforms),
                RecordRouteOutcomeOp(outcome=outcome),
            ),
            evidence_refs=self.fixture.prepare_inputs(),
            authority_basis=(self.fixture.freeze.decision_id,),
            privacy="restricted",
            access_compartments=RUNTIME_COMPARTMENTS,
            created_at="2026-07-11T17:20:00Z",
            parent_transaction_hash=run.base_revision,
        )
        return transaction, {
            item.artifact_id: item.artifact_id.encode("utf-8")
            for item in artifacts
        }

    def _evaluate_transaction(
        self,
        run: RouteRun,
        lock: ArtifactRegistration,
    ) -> tuple[Transaction, dict[str, bytes], EntityVersion]:
        comparison, report, relation = self.fixture.evaluation_candidate(lock=lock)
        comparison = comparison.model_copy(
            update={"access_compartments": RUNTIME_COMPARTMENTS}
        )
        report = report.model_copy(
            update={"access_compartments": RUNTIME_COMPARTMENTS}
        )
        relation = relation.model_copy(
            update={
                "privacy": "restricted",
                "access_compartments": RUNTIME_COMPARTMENTS,
            }
        )
        candidate_refs = (
            _eref(comparison),
            RelationVersionRef(relation_id=relation.relation_id, version=1),
            _aref(report),
        )
        outcome = RouteOutcome(
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            outcome="completed_with_candidate",
            rationale="Record the one terminal independent comparison.",
            candidate_refs=candidate_refs,
            privacy="restricted",
            access_compartments=RUNTIME_COMPARTMENTS,
        )
        transaction = Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id="transaction.blind.runtime.evaluate",
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=EVALUATOR,
            intent="Evaluate the locked blind candidate once and close the attempt.",
            operations=(
                RegisterArtifactOp(artifact=report),
                CreateEntityOp(entity=comparison),
                CreateRelationOp(relation=relation),
                RecordRouteOutcomeOp(outcome=outcome),
            ),
            evidence_refs=(
                *self.fixture.evaluation_inputs(),
                *(_aref(item) for item in self.fixture.sealed_artifacts),
                _aref(lock),
            ),
            authority_basis=(self.fixture.freeze.decision_id,),
            privacy="restricted",
            access_compartments=RUNTIME_COMPARTMENTS,
            created_at="2026-07-11T17:30:00Z",
            parent_transaction_hash=run.base_revision,
        )
        return transaction, {report.artifact_id: report.artifact_id.encode("utf-8")}, comparison

    def test_prepare_and_evaluate_commit_and_replay_from_genesis(self) -> None:
        excluded = {
            self.fixture.gold_ref.entity_id,
            self.fixture.candidate_ref.entity_id,
            "dossier.g5.closure",
            self.fixture.entity_ids["dossier.g5.closure"],
        }
        seed_entities = tuple(
            item
            for item in self.fixture.entities.values()
            if item.entity_id not in excluded
        )
        seed_artifacts = tuple(
            (item, item.artifact_id.encode("utf-8"))
            for item in self.fixture.artifacts.values()
        )
        self._install_historical_seed_route(
            outputs=seed_entities,
            artifacts=seed_artifacts,
            label="closed_inputs",
            restricted=False,
        )
        self._record_human_decisions()

        lock, lock_bytes = self._candidate_lock()
        package_entities = tuple(
            self.fixture.entities[(entity_id, 1)] for entity_id in sorted(excluded)
        )
        self._install_historical_seed_route(
            outputs=package_entities,
            artifacts=((lock, lock_bytes),),
            label="packages_and_lock",
            restricted=True,
        )
        stored_lock = ObjectStore(self.layout).read_bytes(
            "artifacts", lock.content_hash, verify=True
        )
        self.assertEqual(stored_lock, lock_bytes)

        prepare_run, prepare_manifest, prepare_context = self._begin(
            route_id="prepare.blind_case",
            actor=BUILDER,
            purpose="confirmatory_case_preparation",
            compartments=PREPARE_GRANTS,
            focus_entity_ids=tuple(
                item.entity_id for item in self.fixture.prepare_inputs()
            ),
            registry_hash=ROUTE_REGISTRY_V2_HASH,
            privacy_clearance="restricted",
            label="prepare",
        )
        self.assertEqual(
            set(prepare_manifest.selected_entity_refs),
            set(self.fixture.prepare_inputs()),
        )
        self.assertEqual(prepare_context["route"]["route_version"], 2)
        prepare_transaction, prepare_bytes = self._prepare_transaction(prepare_run)
        _, after_prepare = self._stage_preflight_commit(
            run=prepare_run,
            transaction=prepare_transaction,
            artifact_bytes=prepare_bytes,
            label="prepare",
        )
        self.assertEqual(
            after_prepare.current_entities[self.fixture.manifest_ref.entity_id], 1
        )
        store = ObjectStore(self.layout)
        for registration in self.fixture.sealed_artifacts:
            self.assertEqual(
                store.read_bytes("artifacts", registration.content_hash, verify=True),
                prepare_bytes[registration.artifact_id],
            )

        # Independence is an entry condition, not merely an exit condition:
        # the generator must be rejected before any gold-bearing context bytes
        # or immutable run workspace are written.
        runs_before_rejected_begin = tuple(sorted(self.layout.runs_dir.iterdir()))
        with self.assertRaisesRegex(
            RouteEntryError, r"(?i)generator.*cannot begin.*evaluator"
        ):
            self._begin(
                route_id="evaluate.blind_argument_package",
                actor=GENERATOR,
                purpose="confirmatory_evaluation",
                compartments=RUNTIME_COMPARTMENTS,
                focus_entity_ids=tuple(
                    item.entity_id for item in self.fixture.evaluation_inputs()
                ),
                registry_hash=ROUTE_REGISTRY_V2_HASH,
                privacy_clearance="restricted",
                label="rejected_generator_evaluator",
            )
        self.assertEqual(
            tuple(sorted(self.layout.runs_dir.iterdir())),
            runs_before_rejected_begin,
        )

        evaluate_run, evaluate_manifest, evaluate_context = self._begin(
            route_id="evaluate.blind_argument_package",
            actor=EVALUATOR,
            purpose="confirmatory_evaluation",
            compartments=RUNTIME_COMPARTMENTS,
            focus_entity_ids=tuple(
                item.entity_id for item in self.fixture.evaluation_inputs()
            ),
            registry_hash=ROUTE_REGISTRY_V2_HASH,
            privacy_clearance="restricted",
            label="evaluate",
        )
        self.assertEqual(
            set(evaluate_manifest.selected_entity_refs),
            set(self.fixture.evaluation_inputs()),
        )
        self.assertEqual(evaluate_context["route"]["route_version"], 2)
        evaluate_transaction, evaluator_bytes, comparison = self._evaluate_transaction(
            evaluate_run, lock
        )
        _, final = self._stage_preflight_commit(
            run=evaluate_run,
            transaction=evaluate_transaction,
            artifact_bytes=evaluator_bytes,
            label="evaluate",
        )

        # Snapshot/status files are disposable; replay must still reconstruct
        # the terminal comparison and every isolated byte from genesis objects.
        for disposable in (self.layout.latest_snapshot, self.layout.status_view):
            if disposable.exists():
                disposable.unlink()
        replayed = replay(self.layout)
        self.assertEqual(replayed, final)
        self.assertGreaterEqual(len(replayed.chain), 10)
        self.assertEqual(replayed.current_entities[comparison.entity_id], 1)
        terminal = [
            parse_theory_entity(item)
            for item in replayed.entity_versions
            if item.entity_type == "VAPComparisonRecord"
        ]
        self.assertEqual(len(terminal), 1)
        self.assertIsInstance(terminal[0], VAPComparisonRecord)
        self.assertEqual(terminal[0].attempt_id, ATTEMPT)
        self.assertEqual(
            tuple(item.route_id for item in replayed.route_outcomes[-2:]),
            ("prepare.blind_case", "evaluate.blind_argument_package"),
        )
        self.assertEqual(
            store.read_bytes("artifacts", lock.content_hash, verify=True), lock_bytes
        )


if __name__ == "__main__":
    unittest.main()
