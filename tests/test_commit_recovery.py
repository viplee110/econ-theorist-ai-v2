"""Commit, crash-boundary, human-file, rendering, and recovery contracts."""

from __future__ import annotations

import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from tests.helpers import assert_generated_view, sha256_bytes

from econ_theorist.codec import transaction_digest
from econ_theorist.models import (
    Actor,
    ArtifactRegistration,
    ArtifactVersionRef,
    CreateEntityOp,
    EntityVersion,
    FacetPayloads,
    RecordBlockerOp,
    RegisterArtifactOp,
    RiskOrBlocker,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from econ_theorist.project import init_project
from econ_theorist.policy import ROUTE_REGISTRY_V1_HASH
from econ_theorist.runs import (
    begin_run,
    compiled_context_path,
    transaction_bindings,
)
from econ_theorist.runtime.commit import (
    CandidateArtifactError,
    CandidateError,
    PreparedCandidate,
    StagedArtifact,
    StoreNotVirginError,
    UnsafeHumanPath,
    commit_prepared,
    commit_transaction,
    preflight_candidate,
    reconstruct_reconciliation_conflicts,
)
from econ_theorist.runtime.faults import (
    FAULT_MODE_ENV,
    FAULT_POINT_ENV,
    InjectedFault,
)
from econ_theorist.runtime.layout import StoreLayout
from econ_theorist.runtime.objects import HeadFormatError, HeadStore, ObjectStore
from econ_theorist.runtime.recovery import CorruptHeadError, recover
from econ_theorist.runtime.render import render_status
from econ_theorist.runtime.replay import ReferentialIntegrityError


NOW = "2026-07-11T00:00:00Z"
PROJECT_ID = "project.test"


def blocker_operation(name: str = "blocker.test") -> RecordBlockerOp:
    return RecordBlockerOp(
        blocker=RiskOrBlocker(
            blocker_id=name,
            project_id=PROJECT_ID,
            kind="test.blocker",
            severity="warning",
            summary="A deterministic test blocker",
            created_at=NOW,
        )
    )


def transaction_with(
    *operations: object,
    base: str | None = None,
    transaction_id: str = "txn.test",
    route_run_id: str = "run.test",
    route_id: str = "frame.question_and_benchmarks",
    bindings: dict[str, str] | None = None,
) -> Transaction:
    return Transaction(
        **(bindings or {}),
        transaction_id=transaction_id,
        origin="route_run",
        project_id=PROJECT_ID,
        base_revision=base,
        route_run_id=route_run_id,
        route_id=route_id,
        actor=Actor(kind="agent", actor_id="agent.test"),
        intent="Exercise the local transaction substrate",
        operations=operations,
        created_at=NOW,
        parent_transaction_hash=base,
    )


class CommitRecoveryTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.layout = StoreLayout.at(self.root).ensure()

    def _initialize(self, layout: StoreLayout | None = None) -> Snapshot:
        active = layout or self.layout
        return init_project(
            active.project_root,
            name="Commit fixture",
            actor_id="human.test",
            project_id=PROJECT_ID,
            created_at=NOW,
        )

    def _genesis_transaction(
        self,
        *,
        transaction_id: str = "txn.genesis",
    ) -> Transaction:
        project = EntityVersion(
            entity_id=PROJECT_ID,
            entity_type="Project",
            version=1,
            project_id=PROJECT_ID,
            title="Test theory project",
            summary="Minimal canonical Project genesis",
            status=ScientificStatus(lifecycle="active"),
            facets=FacetPayloads(),
            created_at=NOW,
        )
        return Transaction(
            transaction_id=transaction_id,
            origin="genesis",
            project_id=PROJECT_ID,
            base_revision=None,
            route_run_id=f"run.{transaction_id}",
            actor=Actor(kind="human", actor_id="human.test"),
            intent="Create the canonical Project entity",
            operations=(CreateEntityOp(entity=project),),
            created_at=NOW,
            parent_transaction_hash=None,
        )

    def _begin(self, snapshot: Snapshot, layout: StoreLayout | None = None):
        active = layout or self.layout
        return begin_run(
            active,
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=Actor(kind="agent", actor_id="agent.test"),
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=4000,
            route_registry_hash=ROUTE_REGISTRY_V1_HASH,
        )

    def _prepare_blocker(self):
        snapshot = self._initialize()
        run = self._begin(snapshot)
        transaction = transaction_with(
            blocker_operation(),
            base=snapshot.head,
            route_run_id=run.route_run_id,
            bindings=transaction_bindings(self.layout, run.route_run_id),
        )
        prepared = preflight_candidate(self.layout, transaction)
        return transaction, prepared

    def _register_human_baseline(
        self,
        *,
        content: bytes = b"baseline H0",
        logical_path: str = "paper.tex",
    ):
        snapshot = self._initialize()
        working = self.root / logical_path
        working.parent.mkdir(parents=True, exist_ok=True)
        working.write_bytes(content)
        run = self._begin(snapshot)
        staged = self.layout.staging_dir / "baseline-copy.tex"
        staged.write_bytes(content)
        baseline = ArtifactRegistration(
            artifact_id="artifact.paper",
            version=1,
            project_id=PROJECT_ID,
            logical_name="human baseline",
            media_type="text/x-tex",
            content_hash=sha256_bytes(content),
            byte_size=len(content),
            human_owned=True,
            logical_path=logical_path,
            expected_base_hash=sha256_bytes(content),
            created_at=NOW,
        )
        transaction = transaction_with(
            RegisterArtifactOp(artifact=baseline),
            base=snapshot.head,
            transaction_id="txn.human_baseline",
            route_run_id=run.route_run_id,
            bindings=transaction_bindings(self.layout, run.route_run_id),
        )
        result = commit_transaction(
            self.layout,
            transaction,
            [StagedArtifact(baseline.artifact_id, 1, staged)],
        )
        return result, baseline, working


class CandidatePreflightTests(CommitRecoveryTestCase):
    def test_staged_hash_and_size_are_checked_before_any_install(self) -> None:
        snapshot = self._initialize()
        run = self._begin(snapshot)
        expected = b"expected artifact bytes"
        staged = self.layout.staging_dir / "candidate.bin"
        staged.write_bytes(b"different bytes")
        registration = ArtifactRegistration(
            artifact_id="artifact.test",
            version=1,
            project_id=PROJECT_ID,
            logical_name="candidate",
            media_type="application/octet-stream",
            content_hash=sha256_bytes(expected),
            byte_size=len(expected),
            created_at=NOW,
        )
        transaction = transaction_with(
            RegisterArtifactOp(artifact=registration),
            base=snapshot.head,
            route_run_id=run.route_run_id,
            bindings=transaction_bindings(self.layout, run.route_run_id),
        )

        with self.assertRaises(CandidateArtifactError):
            preflight_candidate(
                self.layout,
                transaction,
                [StagedArtifact("artifact.test", 1, staged)],
            )

        self.assertEqual(HeadStore(self.layout).read(), snapshot.head)
        self.assertEqual(list(self.layout.artifacts_root.iterdir()), [])
        self.assertEqual(len(list(self.layout.transactions_root.iterdir())), 1)

    def test_human_owned_conflict_reports_three_hashes_and_never_writes_path(self) -> None:
        snapshot = self._initialize()
        base_bytes = b"human base H0"
        working_bytes = b"human edit H1"
        proposed_bytes = b"agent proposal H2"
        working = self.root / "paper.tex"
        working.write_bytes(base_bytes)

        baseline_run = self._begin(snapshot)
        baseline_stage = self.layout.staging_dir / "paper-baseline.tex"
        baseline_stage.write_bytes(base_bytes)
        baseline = ArtifactRegistration(
            artifact_id="artifact.paper",
            version=1,
            project_id=PROJECT_ID,
            logical_name="paper baseline",
            media_type="text/x-tex",
            content_hash=sha256_bytes(base_bytes),
            byte_size=len(base_bytes),
            human_owned=True,
            logical_path="paper.tex",
            expected_base_hash=sha256_bytes(base_bytes),
            created_at=NOW,
        )
        baseline_transaction = transaction_with(
            RegisterArtifactOp(artifact=baseline),
            base=snapshot.head,
            transaction_id="txn.paper_baseline",
            route_run_id=baseline_run.route_run_id,
            bindings=transaction_bindings(
                self.layout, baseline_run.route_run_id
            ),
        )
        baseline_result = commit_transaction(
            self.layout,
            baseline_transaction,
            [StagedArtifact("artifact.paper", 1, baseline_stage)],
        )

        working.write_bytes(working_bytes)
        proposal_run = self._begin(baseline_result.snapshot)
        proposal_stage = self.layout.staging_dir / "paper-proposal.tex"
        proposal_stage.write_bytes(proposed_bytes)
        proposal = ArtifactRegistration(
            artifact_id="artifact.paper",
            version=2,
            project_id=PROJECT_ID,
            logical_name="paper proposal",
            media_type="text/x-tex",
            content_hash=sha256_bytes(proposed_bytes),
            byte_size=len(proposed_bytes),
            human_owned=True,
            logical_path="paper.tex",
            expected_base_hash=baseline.content_hash,
            created_at=NOW,
            supersedes=ArtifactVersionRef(
                artifact_id=baseline.artifact_id,
                version=baseline.version,
            ),
        )
        proposal_transaction = transaction_with(
            RegisterArtifactOp(artifact=proposal),
            base=baseline_result.transaction_digest,
            transaction_id="txn.paper_proposal",
            route_run_id=proposal_run.route_run_id,
            bindings=transaction_bindings(
                self.layout, proposal_run.route_run_id
            ),
        )

        result = commit_transaction(
            self.layout,
            proposal_transaction,
            [StagedArtifact("artifact.paper", 2, proposal_stage)],
        )

        self.assertEqual(result.status, "committed")
        self.assertEqual(working.read_bytes(), working_bytes)
        self.assertEqual(len(result.reconciliation_conflicts), 1)
        conflict = result.reconciliation_conflicts[0]
        self.assertEqual(conflict.expected_base_hash, sha256_bytes(base_bytes))
        self.assertEqual(conflict.working_hash, sha256_bytes(working_bytes))
        self.assertEqual(conflict.proposed_hash, sha256_bytes(proposed_bytes))
        self.assertEqual(conflict.working_state, "changed")
        self.assertEqual(
            ObjectStore(self.layout).read_bytes(
                "artifacts", proposal.content_hash
            ),
            proposed_bytes,
        )

    def test_human_v1_checks_safe_path_and_records_explicit_baseline(self) -> None:
        snapshot = self._initialize()
        run = self._begin(snapshot)
        staged_bytes = b"candidate baseline"
        staged = self.layout.staging_dir / "unsafe-baseline.tex"
        staged.write_bytes(staged_bytes)
        unsafe = ArtifactRegistration(
            artifact_id="artifact.unsafe",
            version=1,
            project_id=PROJECT_ID,
            logical_name="unsafe baseline",
            media_type="text/x-tex",
            content_hash=sha256_bytes(staged_bytes),
            byte_size=len(staged_bytes),
            human_owned=True,
            logical_path="../outside.tex",
            expected_base_hash=sha256_bytes(staged_bytes),
            created_at=NOW,
        )
        transaction = transaction_with(
            RegisterArtifactOp(artifact=unsafe),
            base=snapshot.head,
            route_run_id=run.route_run_id,
            bindings=transaction_bindings(self.layout, run.route_run_id),
        )

        with self.assertRaises(UnsafeHumanPath):
            preflight_candidate(
                self.layout,
                transaction,
                [StagedArtifact(unsafe.artifact_id, 1, staged)],
            )

        safe_working = self.root / "paper.tex"
        safe_working.write_bytes(b"different working bytes")
        safe = ArtifactRegistration(
            artifact_id="artifact.safe",
            version=1,
            project_id=PROJECT_ID,
            logical_name="safe baseline with mismatched working bytes",
            media_type="text/x-tex",
            content_hash=sha256_bytes(staged_bytes),
            byte_size=len(staged_bytes),
            human_owned=True,
            logical_path="paper.tex",
            expected_base_hash=sha256_bytes(staged_bytes),
            created_at=NOW,
        )
        safe_transaction = transaction_with(
            RegisterArtifactOp(artifact=safe),
            base=snapshot.head,
            transaction_id="txn.baseline_mismatch",
            route_run_id=run.route_run_id,
            bindings=transaction_bindings(self.layout, run.route_run_id),
        )
        prepared = preflight_candidate(
            self.layout,
            safe_transaction,
            [StagedArtifact(safe.artifact_id, 1, staged)],
        )
        self.assertEqual(len(prepared.reconciliation_conflicts), 1)
        self.assertEqual(
            prepared.reconciliation_conflicts[0].working_hash,
            sha256_bytes(b"different working bytes"),
        )
        self.assertEqual(safe_working.read_bytes(), b"different working bytes")

    def test_human_replacement_binds_exact_predecessor_and_immutable_path(self) -> None:
        baseline_result, baseline, working = self._register_human_baseline()
        proposed = b"replacement H2"

        cases = (
            ("wrong_base", True, "paper.tex", "f" * 64),
            ("changed_path", True, "renamed.tex", baseline.content_hash),
            ("changed_owner", False, None, None),
        )
        for index, (name, human_owned, logical_path, expected_base) in enumerate(cases):
            with self.subTest(case=name):
                run = self._begin(baseline_result.snapshot)
                staged = self.layout.staging_dir / f"replacement-{index}.tex"
                staged.write_bytes(proposed)
                registration = ArtifactRegistration(
                    artifact_id=baseline.artifact_id,
                    version=2,
                    project_id=PROJECT_ID,
                    logical_name=f"invalid replacement {name}",
                    media_type="text/x-tex",
                    content_hash=sha256_bytes(proposed),
                    byte_size=len(proposed),
                    human_owned=human_owned,
                    logical_path=logical_path,
                    expected_base_hash=expected_base,
                    created_at=NOW,
                    supersedes=ArtifactVersionRef(
                        artifact_id=baseline.artifact_id,
                        version=1,
                    ),
                )
                transaction = transaction_with(
                    RegisterArtifactOp(artifact=registration),
                    base=baseline_result.transaction_digest,
                    transaction_id=f"txn.invalid_replacement{index}",
                    route_run_id=run.route_run_id,
                    bindings=transaction_bindings(
                        self.layout, run.route_run_id
                    ),
                )
                with self.assertRaises(
                    (CandidateArtifactError, ReferentialIntegrityError)
                ):
                    preflight_candidate(
                        self.layout,
                        transaction,
                        [
                            StagedArtifact(
                                registration.artifact_id,
                                registration.version,
                                staged,
                            )
                        ],
                    )
        self.assertEqual(working.read_bytes(), b"baseline H0")


class CommitProtocolTests(CommitRecoveryTestCase):
    def test_dataclasses_replace_cannot_forge_a_prepared_commit_token(self) -> None:
        transaction = self._genesis_transaction()
        prepared = preflight_candidate(self.layout, transaction)
        forged_candidates = (
            replace(prepared),
            replace(prepared, transaction_digest="f" * 64),
            replace(prepared, transaction_bytes=b"{}"),
            replace(prepared, base_revision="e" * 64),
            PreparedCandidate(
                store_root=prepared.store_root,
                transaction=prepared.transaction,
                transaction_bytes=prepared.transaction_bytes,
                transaction_digest=prepared.transaction_digest,
                base_revision=prepared.base_revision,
                candidate_snapshot=prepared.candidate_snapshot,
                artifacts=prepared.artifacts,
                provenance=prepared.provenance,
                reconciliation_conflicts=prepared.reconciliation_conflicts,
            ),
        )

        for forged in forged_candidates:
            with self.subTest(forged=forged.transaction_digest):
                with self.assertRaises(CandidateError):
                    commit_prepared(self.layout, forged)
                self.assertIsNone(HeadStore(self.layout).read())
        self.assertEqual(tuple(self.layout.transactions_root.iterdir()), ())

    def test_lock_recalculation_does_not_depend_on_the_preflight_seal(self) -> None:
        transaction = self._genesis_transaction()
        prepared = preflight_candidate(self.layout, transaction)
        forged = replace(prepared, transaction_digest="d" * 64)

        with patch(
            "econ_theorist.runtime.commit._verify_prepared_seal",
            return_value=None,
        ):
            with self.assertRaises(CandidateError):
                commit_prepared(self.layout, forged)

        self.assertIsNone(HeadStore(self.layout).read())
        self.assertEqual(tuple(self.layout.transactions_root.iterdir()), ())

    def test_lock_rereads_staged_artifact_instead_of_trusting_cached_bytes(self) -> None:
        snapshot = self._initialize()
        run = self._begin(snapshot)
        original = b"artifact seen at preflight"
        staged = self.layout.staging_dir / "mutable-stage.bin"
        staged.write_bytes(original)
        registration = ArtifactRegistration(
            artifact_id="artifact.mutable_stage",
            version=1,
            project_id=PROJECT_ID,
            logical_name="mutable stage",
            media_type="application/octet-stream",
            content_hash=sha256_bytes(original),
            byte_size=len(original),
            created_at=NOW,
        )
        transaction = transaction_with(
            RegisterArtifactOp(artifact=registration),
            base=snapshot.head,
            transaction_id="txn.mutable_stage",
            route_run_id=run.route_run_id,
            bindings=transaction_bindings(self.layout, run.route_run_id),
        )
        prepared = preflight_candidate(
            self.layout,
            transaction,
            [StagedArtifact(registration.artifact_id, 1, staged)],
        )
        staged.write_bytes(b"changed after preflight")

        with self.assertRaises(CandidateArtifactError):
            commit_prepared(self.layout, prepared)

        self.assertEqual(HeadStore(self.layout).read(), snapshot.head)
        self.assertFalse(
            ObjectStore(self.layout)
            .path_for("artifacts", registration.content_hash)
            .exists()
        )

    def test_lock_rereads_live_provenance_and_rejects_workspace_tampering(self) -> None:
        snapshot = self._initialize()
        run = self._begin(snapshot)
        transaction = transaction_with(
            blocker_operation("blocker.provenance_tamper"),
            base=snapshot.head,
            transaction_id="txn.provenance_tamper",
            route_run_id=run.route_run_id,
            bindings=transaction_bindings(self.layout, run.route_run_id),
        )
        prepared = preflight_candidate(self.layout, transaction)
        compiled_context_path(self.layout, run.route_run_id).write_bytes(b"{}")

        with self.assertRaises(CandidateError):
            commit_prepared(self.layout, prepared)

        self.assertEqual(HeadStore(self.layout).read(), snapshot.head)
        self.assertFalse(
            ObjectStore(self.layout)
            .path_for("transactions", transaction_digest(transaction))
            .exists()
        )

    def test_live_provenance_must_match_transaction_actor_before_commit(self) -> None:
        snapshot = self._initialize()
        run = self._begin(snapshot)
        bindings = transaction_bindings(self.layout, run.route_run_id)
        transaction = Transaction(
            **bindings,
            transaction_id="txn.wrong_actor",
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=snapshot.head,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=Actor(kind="agent", actor_id="agent.other"),
            intent="Attempt to detach a candidate from its run actor",
            operations=(blocker_operation("blocker.wrong_actor"),),
            created_at=NOW,
            parent_transaction_hash=snapshot.head,
        )

        with self.assertRaises(CandidateError):
            preflight_candidate(self.layout, transaction)

        self.assertEqual(HeadStore(self.layout).read(), snapshot.head)

    def test_replay_provenance_invariant_runs_before_transaction_install(self) -> None:
        transaction, prepared = self._prepare_blocker()
        with patch(
            "econ_theorist.runtime.replay._validate_operational_provenance",
            side_effect=CandidateError("forced provenance rejection"),
        ):
            with self.assertRaises(CandidateError):
                commit_prepared(self.layout, prepared)

        self.assertEqual(HeadStore(self.layout).read(), prepared.base_revision)
        self.assertFalse(
            ObjectStore(self.layout)
            .path_for("transactions", transaction_digest(transaction))
            .exists()
        )

    def test_missing_or_empty_head_with_old_evidence_cannot_start_second_genesis(self) -> None:
        for index, mode in enumerate(("missing", "empty")):
            with self.subTest(mode=mode):
                layout = StoreLayout.at(self.root / f"second-genesis-{index}").ensure()
                first = self._genesis_transaction(
                    transaction_id=f"txn.first_genesis{index}"
                )
                first_result = commit_transaction(layout, first)
                if mode == "missing":
                    layout.main_ref.unlink()
                else:
                    layout.main_ref.write_bytes(b"")
                second = self._genesis_transaction(
                    transaction_id=f"txn.second_genesis{index}"
                )
                if mode == "empty":
                    with self.assertRaises(HeadFormatError):
                        preflight_candidate(layout, second)
                else:
                    prepared = preflight_candidate(layout, second)
                    with self.assertRaises(StoreNotVirginError):
                        commit_prepared(layout, prepared)

                if mode == "missing":
                    self.assertIsNone(HeadStore(layout).read())
                else:
                    self.assertEqual(layout.main_ref.read_bytes(), b"")
                self.assertTrue(
                    ObjectStore(layout)
                    .path_for("transactions", first_result.transaction_digest)
                    .exists()
                )
                self.assertFalse(
                    ObjectStore(layout)
                    .path_for("transactions", transaction_digest(second))
                    .exists()
                )

    def test_real_genesis_commit_replay_and_recovery_round_trip(self) -> None:
        project = EntityVersion(
            entity_id=PROJECT_ID,
            entity_type="Project",
            version=1,
            project_id=PROJECT_ID,
            title="Test theory project",
            summary="Minimal canonical Project genesis",
            status=ScientificStatus(lifecycle="active"),
            facets=FacetPayloads(),
            created_at=NOW,
        )
        genesis = Transaction(
            transaction_id="txn.genesis",
            origin="genesis",
            project_id=PROJECT_ID,
            base_revision=None,
            route_run_id="run.genesis",
            actor=Actor(kind="human", actor_id="human.test"),
            intent="Create the canonical Project entity",
            operations=(CreateEntityOp(entity=project),),
            created_at=NOW,
            parent_transaction_hash=None,
        )

        genesis_commit = commit_transaction(self.layout, genesis)
        follow_up_run = self._begin(genesis_commit.snapshot)
        artifact_bytes = b"registered proof note"
        staged = self.layout.staging_dir / "proof-note.txt"
        staged.write_bytes(artifact_bytes)
        registration = ArtifactRegistration(
            artifact_id="artifact.proof_note",
            version=1,
            project_id=PROJECT_ID,
            logical_name="proof note",
            media_type="text/plain",
            content_hash=sha256_bytes(artifact_bytes),
            byte_size=len(artifact_bytes),
            created_at=NOW,
        )
        follow_up = transaction_with(
            RegisterArtifactOp(artifact=registration),
            base=genesis_commit.transaction_digest,
            transaction_id="txn.register_proof_note",
            route_run_id=follow_up_run.route_run_id,
            bindings=transaction_bindings(
                self.layout, follow_up_run.route_run_id
            ),
        )
        committed = commit_transaction(
            self.layout,
            follow_up,
            [StagedArtifact(registration.artifact_id, 1, staged)],
        )
        first = recover(self.layout)
        second = recover(self.layout)

        self.assertEqual(committed.status, "committed")
        self.assertEqual(first, second)
        self.assertEqual(first.head, transaction_digest(follow_up))
        self.assertEqual(len(first.snapshot.chain), 2)
        self.assertEqual(first.snapshot.current_entities[PROJECT_ID], 1)
        self.assertEqual(first.snapshot.current_artifacts[registration.artifact_id], 1)
        self.assertEqual(first.orphans.transaction_digests, ())
        assert_generated_view(
            self,
            self.layout.status_view.read_text(encoding="utf-8"),
            committed.transaction_digest,
        )

    def test_second_prevalidated_candidate_returns_stale_base_without_install(self) -> None:
        snapshot = self._initialize()
        run_first = self._begin(snapshot)
        run_second = self._begin(snapshot)
        first = transaction_with(
            blocker_operation("blocker.first"),
            base=snapshot.head,
            transaction_id="txn.first",
            route_run_id=run_first.route_run_id,
            bindings=transaction_bindings(self.layout, run_first.route_run_id),
        )
        second = transaction_with(
            blocker_operation("blocker.second"),
            base=snapshot.head,
            transaction_id="txn.second",
            route_run_id=run_second.route_run_id,
            bindings=transaction_bindings(self.layout, run_second.route_run_id),
        )
        prepared_first = preflight_candidate(self.layout, first)
        prepared_second = preflight_candidate(self.layout, second)

        winner = commit_prepared(self.layout, prepared_first)
        loser = commit_prepared(self.layout, prepared_second)

        self.assertEqual(winner.status, "committed")
        self.assertEqual(loser.status, "stale_base")
        self.assertEqual(HeadStore(self.layout).read(), winner.transaction_digest)
        self.assertFalse(
            ObjectStore(self.layout)
            .path_for("transactions", loser.transaction_digest)
            .exists()
        )

    def test_fault_before_head_leaves_installed_objects_as_reported_orphans(self) -> None:
        transaction, prepared = self._prepare_blocker()
        with patch.dict(
            os.environ,
            {
                FAULT_POINT_ENV: "after_transaction_installation",
                FAULT_MODE_ENV: "raise",
            },
        ):
            with self.assertRaises(InjectedFault):
                commit_prepared(self.layout, prepared)

        self.assertEqual(HeadStore(self.layout).read(), prepared.base_revision)
        report = recover(self.layout)
        self.assertEqual(report.head, prepared.base_revision)
        self.assertIn(transaction_digest(transaction), report.orphans.transaction_digests)
        cached = Snapshot.model_validate_json(
            self.layout.latest_snapshot.read_bytes(), strict=True
        )
        self.assertEqual(cached.head, prepared.base_revision)

    def test_fault_after_head_keeps_new_head_for_recovery(self) -> None:
        transaction, prepared = self._prepare_blocker()
        with patch.dict(
            os.environ,
            {
                FAULT_POINT_ENV: "after_head_replacement",
                FAULT_MODE_ENV: "raise",
            },
        ):
            with self.assertRaises(InjectedFault):
                commit_prepared(self.layout, prepared)

        digest = transaction_digest(transaction)
        self.assertEqual(HeadStore(self.layout).read(), digest)
        cached = Snapshot.model_validate_json(
            self.layout.latest_snapshot.read_bytes(), strict=True
        )
        self.assertEqual(cached.head, prepared.base_revision)
        first = recover(self.layout)
        second = recover(self.layout)
        self.assertEqual(first, second)
        self.assertEqual(first.head, digest)
        self.assertEqual(first.snapshot_hash, second.snapshot_hash)
        assert_generated_view(
            self,
            self.layout.status_view.read_text(encoding="utf-8"),
            digest,
        )

    def test_h0_h1_h2_conflict_rebuilds_after_post_head_crash(self) -> None:
        baseline_result, baseline, working = self._register_human_baseline(
            content=b"canonical H0"
        )
        working_bytes = b"uncommitted human H1"
        proposed_bytes = b"agent proposal H2"
        working.write_bytes(working_bytes)
        run = self._begin(baseline_result.snapshot)
        staged = self.layout.staging_dir / "crash-proposal.tex"
        staged.write_bytes(proposed_bytes)
        proposal = ArtifactRegistration(
            artifact_id=baseline.artifact_id,
            version=2,
            project_id=PROJECT_ID,
            logical_name="crash-safe proposal",
            media_type="text/x-tex",
            content_hash=sha256_bytes(proposed_bytes),
            byte_size=len(proposed_bytes),
            human_owned=True,
            logical_path=baseline.logical_path,
            expected_base_hash=baseline.content_hash,
            created_at=NOW,
            supersedes=ArtifactVersionRef(
                artifact_id=baseline.artifact_id,
                version=1,
            ),
        )
        transaction = transaction_with(
            RegisterArtifactOp(artifact=proposal),
            base=baseline_result.transaction_digest,
            transaction_id="txn.crash_safe_proposal",
            route_run_id=run.route_run_id,
            bindings=transaction_bindings(self.layout, run.route_run_id),
        )
        prepared = preflight_candidate(
            self.layout,
            transaction,
            [StagedArtifact(proposal.artifact_id, 2, staged)],
        )

        with patch.dict(
            os.environ,
            {
                FAULT_POINT_ENV: "after_head_replacement",
                FAULT_MODE_ENV: "raise",
            },
        ):
            with self.assertRaises(InjectedFault):
                commit_prepared(self.layout, prepared)

        self.assertEqual(working.read_bytes(), working_bytes)
        recovered = recover(self.layout)
        conflicts = reconstruct_reconciliation_conflicts(
            self.layout,
            recovered.snapshot,
        )
        self.assertEqual(len(conflicts), 1)
        conflict = conflicts[0]
        self.assertEqual(conflict.expected_base_hash, sha256_bytes(b"canonical H0"))
        self.assertEqual(conflict.working_hash, sha256_bytes(working_bytes))
        self.assertEqual(conflict.proposed_hash, sha256_bytes(proposed_bytes))
        self.assertEqual(working.read_bytes(), working_bytes)

    def test_every_named_commit_fault_obeys_the_atomic_head_boundary(self) -> None:
        points = (
            ("after_staging", False),
            ("after_artifact_installation", False),
            ("after_transaction_installation", False),
            ("after_temp_head_write", False),
            ("after_head_replacement", True),
            ("after_snapshot_write", True),
            ("after_view_write", True),
        )
        for index, (point, expects_new_head) in enumerate(points):
            with self.subTest(point=point):
                layout = StoreLayout.at(self.root / f"fault-{index}").ensure()
                base_snapshot = self._initialize(layout)
                run = self._begin(base_snapshot, layout)
                data = f"artifact at {point}".encode()
                staged = layout.staging_dir / "candidate.bin"
                staged.write_bytes(data)
                registration = ArtifactRegistration(
                    artifact_id=f"artifact.fault{index}",
                    version=1,
                    project_id=PROJECT_ID,
                    logical_name=f"fault candidate {index}",
                    media_type="application/octet-stream",
                    content_hash=sha256_bytes(data),
                    byte_size=len(data),
                    created_at=NOW,
                )
                transaction = transaction_with(
                    RegisterArtifactOp(artifact=registration),
                    base=base_snapshot.head,
                    transaction_id=f"txn.fault{index}",
                    route_run_id=run.route_run_id,
                    bindings=transaction_bindings(layout, run.route_run_id),
                )
                staged_ref = StagedArtifact(registration.artifact_id, 1, staged)
                environment = {
                    FAULT_POINT_ENV: point,
                    FAULT_MODE_ENV: "raise",
                }
                if point == "after_staging":
                    with patch.dict(os.environ, environment):
                        with self.assertRaises(InjectedFault):
                            preflight_candidate(layout, transaction, [staged_ref])
                    prepared = None
                else:
                    prepared = preflight_candidate(
                        layout, transaction, [staged_ref]
                    )
                    with patch.dict(os.environ, environment):
                        with self.assertRaises(InjectedFault):
                            commit_prepared(layout, prepared)

                expected = (
                    transaction_digest(transaction)
                    if expects_new_head
                    else base_snapshot.head
                )
                self.assertEqual(HeadStore(layout).read(), expected)
                report = recover(layout)
                self.assertEqual(report.head, expected)
                assert_generated_view(
                    self,
                    layout.status_view.read_text(encoding="utf-8"),
                    expected,
                )


class RecoveryAndRenderingTests(CommitRecoveryTestCase):
    def test_recovery_never_guesses_an_orphan_as_a_missing_head(self) -> None:
        orphan = b"unreachable transaction candidate"
        digest = sha256_bytes(orphan)
        ObjectStore(self.layout).install_bytes("transactions", digest, orphan)

        report = recover(self.layout)

        self.assertIsNone(report.head)
        self.assertEqual(report.canonical_head_count, 0)
        self.assertIn(digest, report.orphans.transaction_digests)
        self.assertIsNone(HeadStore(self.layout).read())

    def test_bad_head_is_left_untouched_and_not_replaced_by_an_orphan(self) -> None:
        missing_digest = "a" * 64
        orphan_digest = sha256_bytes(b"other transaction")
        ObjectStore(self.layout).install_bytes(
            "transactions", orphan_digest, b"other transaction"
        )
        HeadStore(self.layout).replace(None, missing_digest)

        with self.assertRaises(CorruptHeadError):
            recover(self.layout)

        self.assertEqual(HeadStore(self.layout).read(), missing_digest)

    def test_recovery_ignores_a_tampered_view_and_regenerates_markers(self) -> None:
        _transaction, prepared = self._prepare_blocker()
        commit_prepared(self.layout, prepared)
        self.layout.status_view.write_text(
            "CONFIRMED: yes\nVERIFIED: yes\nsource_head: fake\n",
            encoding="utf-8",
        )

        report = recover(self.layout)

        generated = self.layout.status_view.read_text(encoding="utf-8")
        assert_generated_view(self, generated, prepared.transaction_digest)
        self.assertNotIn("source_head: fake", generated)
        self.assertEqual(report.head, prepared.transaction_digest)

    def test_render_is_deterministic_and_declares_its_source(self) -> None:
        _transaction, prepared = self._prepare_blocker()
        snapshot = prepared.candidate_snapshot

        first = render_status(snapshot)
        second = render_status(snapshot)

        self.assertEqual(first, second)
        assert_generated_view(self, first, snapshot.head)


if __name__ == "__main__":  # pragma: no cover - direct test invocation
    unittest.main()
