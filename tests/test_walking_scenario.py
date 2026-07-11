"""End-to-end Phase 1 walking scenario through the public runtime APIs."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from tests.helpers import SOURCE_ROOT  # noqa: F401

from econ_theorist.cli import main
from econ_theorist.codec import canonical_json_bytes, sha256_digest, transaction_bytes
from econ_theorist.models import (
    Actor,
    ArtifactRegistration,
    ChangedFacets,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    FacetPayloads,
    RecordDecisionOp,
    RegisterArtifactOp,
    RelationVersion,
    RelationVersionRef,
    ScientificStatus,
    SemanticFacetRef,
    SupersedeEntityOp,
    SupersedeRelationOp,
    Transaction,
)
from econ_theorist.project import init_project
from econ_theorist.runs import (
    RunError,
    begin_run,
    compiled_context_path,
    context_path,
    run_path,
    transaction_bindings,
)
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import (
    CandidateError,
    StagedArtifact,
    commit_transaction,
    preflight_candidate,
)
from econ_theorist.runtime.freshness import facet_semantic_hash, stale_reason_chains
from econ_theorist.runtime.objects import HeadStore, ObjectStore
from econ_theorist.runtime.recovery import recover
from econ_theorist.runtime.replay import (
    CandidateValidationError,
    ChainIntegrityError,
    replay,
)
from econ_theorist.staging import StagingError, commit_run, stage_candidate


def make_entity(
    project_id: str,
    entity_id: str,
    entity_type: str,
    *,
    formal: str | None = None,
    presentation: str | None = None,
    version: int = 1,
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=entity_type,
        version=version,
        project_id=project_id,
        title=entity_id,
        summary=f"Walking fixture {entity_id}.",
        status=ScientificStatus(
            lifecycle="proposed",
            formal_validity="unassessed" if formal is not None else None,
        ),
        facets=FacetPayloads(
            formal={} if formal is None else {"statement": formal},
            terminology_presentation=(
                {} if presentation is None else {"text": presentation}
            ),
        ),
        created_at=f"2026-07-11T01:00:{version:02d}Z",
        supersedes=(
            EntityVersionRef(entity_id=entity_id, version=version - 1)
            if version > 1
            else None
        ),
    )


def dependency(
    project_id: str,
    relation_id: str,
    source: EntityVersion,
    target: EntityVersion,
    *,
    target_facet: str = "formal",
    mode: str = "hard",
) -> RelationVersion:
    return RelationVersion(
        relation_id=relation_id,
        relation_type="depends_on",
        version=1,
        project_id=project_id,
        source=EntityVersionRef(entity_id=source.entity_id, version=source.version),
        target=EntityVersionRef(entity_id=target.entity_id, version=target.version),
        dependency_mode=mode,
        upstream=SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet="formal",
            semantic_hash=facet_semantic_hash(source, "formal"),
        ),
        downstream=FacetPathRef(
            entity_id=target.entity_id,
            version=target.version,
            facet=target_facet,
        ),
        created_at="2026-07-11T01:01:00Z",
    )


class WalkingScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.layout = StoreLayout.at(self.root)

    def _install_unchecked_route_transaction(
        self,
        *,
        snapshot,
        run,
        run_bytes: bytes,
        manifest_bytes: bytes,
        context_bytes: bytes,
        transaction_id: str,
    ) -> str:
        store = ObjectStore(self.layout)
        bindings = {
            "route_run_hash": sha256_digest(run_bytes),
            "context_manifest_hash": sha256_digest(manifest_bytes),
            "compiled_context_hash": sha256_digest(context_bytes),
        }
        for data in (run_bytes, manifest_bytes, context_bytes):
            store.install_bytes("provenance", sha256_digest(data), data)
        proposal = make_entity(
            snapshot.project_id,
            f"ent_{transaction_id}",
            "ResearchQuestion",
            formal="provenance must reproduce from the exact base",
        )
        transaction = Transaction(
            **bindings,
            transaction_id=transaction_id,
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=snapshot.head,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=run.actor,
            intent="Install a self-consistent but invalid provenance fixture.",
            operations=(CreateEntityOp(entity=proposal),),
            created_at="2026-07-11T00:20:00Z",
            parent_transaction_hash=snapshot.head,
        )
        body = transaction_bytes(transaction)
        digest = sha256_digest(body)
        store.install_bytes("transactions", digest, body)
        HeadStore(self.layout).replace(snapshot.head, digest)
        return digest

    def test_run_creation_status_cannot_be_rewritten_into_history(self) -> None:
        snapshot = init_project(
            self.root, name="Run creation status", actor_id="human_owner"
        )
        run = begin_run(
            self.layout,
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=Actor(kind="agent", actor_id="agent_run_status"),
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=4000,
        )
        run_payload = json.loads(
            run_path(self.layout, run.route_run_id).read_text(encoding="utf-8")
        )
        run_payload["status"] = "committed"
        forged_run = canonical_json_bytes(run_payload)
        run_path(self.layout, run.route_run_id).write_bytes(forged_run)
        with self.assertRaises(RunError):
            transaction_bindings(self.layout, run.route_run_id)
        self._install_unchecked_route_transaction(
            snapshot=snapshot,
            run=run,
            run_bytes=forged_run,
            manifest_bytes=context_path(
                self.layout, run.route_run_id
            ).read_bytes(),
            context_bytes=compiled_context_path(
                self.layout, run.route_run_id
            ).read_bytes(),
            transaction_id="txn_forged_run_status",
        )
        with self.assertRaises(ChainIntegrityError):
            replay(self.layout)

    def test_replay_recompiles_operational_context_from_the_exact_base(self) -> None:
        snapshot = init_project(
            self.root, name="Replay provenance", actor_id="human_owner"
        )
        run = begin_run(
            self.layout,
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=Actor(kind="agent", actor_id="agent_replay_provenance"),
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=4000,
        )
        context_payload = json.loads(
            compiled_context_path(
                self.layout, run.route_run_id
            ).read_text(encoding="utf-8")
        )
        context_payload["source_head"] = "f" * 64
        forged_context = canonical_json_bytes(context_payload)
        forged_context_hash = sha256_digest(forged_context)

        run_payload = json.loads(
            run_path(self.layout, run.route_run_id).read_text(encoding="utf-8")
        )
        run_payload["context_hash"] = forged_context_hash
        manifest_payload = json.loads(
            context_path(self.layout, run.route_run_id).read_text(encoding="utf-8")
        )
        manifest_payload["context_hash"] = forged_context_hash
        self._install_unchecked_route_transaction(
            snapshot=snapshot,
            run=run,
            run_bytes=canonical_json_bytes(run_payload),
            manifest_bytes=canonical_json_bytes(manifest_payload),
            context_bytes=forged_context,
            transaction_id="txn_forged_compiled_source_head",
        )
        with self.assertRaises(ChainIntegrityError):
            replay(self.layout)

    def test_cli_initialization_is_idempotent_and_replayable(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            first = main(
                [
                    "--project",
                    str(self.root),
                    "init",
                    "--name",
                    "Walking theory",
                    "--actor",
                    "human_owner",
                ]
            )
            second = main(
                [
                    "--project",
                    str(self.root),
                    "init",
                    "--name",
                    "Ignored duplicate name",
                    "--actor",
                    "human_owner",
                ]
            )
            valid = main(["--project", str(self.root), "validate"])

        self.assertEqual((first, second, valid), (0, 0, 0))
        snapshot = replay(self.layout)
        self.assertEqual(len(snapshot.chain), 1)
        self.assertEqual(snapshot.current_entities[snapshot.project_id], 1)

    def test_decide_records_human_authority_without_changing_truth_status(self) -> None:
        snapshot = init_project(
            self.root, name="Decision case", actor_id="human_owner"
        )
        decision = Decision(
            decision_id="dec_g1",
            version=1,
            project_id=snapshot.project_id,
            decision_kind="G1_question_benchmark",
            subject_ref=snapshot.project_id,
            question="Use this question and benchmark as the current research base?",
            options=("confirm", "revise"),
            selected_option="confirm",
            recommendation="confirm",
            rationale="The human accepts the exact current framing provisionally for investment.",
            required_authority="L2",
            decider=Actor(kind="human", actor_id="human_owner"),
            decided_at="2026-07-11T00:10:00Z",
            status="confirmed",
            privacy="restricted",
        )
        path = self.root / "decision.json"
        path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(
                ["--project", str(self.root), "decide", str(path)]
            )

        self.assertEqual(code, 0)
        revised = replay(self.layout)
        committed_transaction = Transaction.model_validate_json(
            ObjectStore(self.layout).read_bytes(
                "transactions", revised.head, verify=True
            ),
            strict=True,
        )
        self.assertEqual(committed_transaction.privacy, "restricted")
        self.assertEqual(len(revised.effective_decisions), 1)
        self.assertEqual(
            revised.derived_status[snapshot.project_id].human_acceptance,
            "human_confirmed",
        )
        project = next(
            entity
            for entity in revised.entity_versions
            if entity.entity_id == snapshot.project_id
        )
        self.assertIsNone(project.status.formal_validity)

    def test_l1_route_cannot_smuggle_an_effective_l2_decision(self) -> None:
        snapshot = init_project(
            self.root, name="Route ceiling case", actor_id="human_owner"
        )
        human = Actor(kind="human", actor_id="human_owner")
        run = begin_run(
            self.layout,
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=human,
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=4000,
        )
        decision = Decision(
            decision_id="dec_smuggled",
            version=1,
            project_id=snapshot.project_id,
            decision_kind="G1_question_benchmark",
            subject_ref=snapshot.project_id,
            question="Confirm through an L1 route?",
            options=("confirm", "reject"),
            selected_option="confirm",
            recommendation="confirm",
            rationale="This must be rejected at the route boundary.",
            required_authority="L2",
            decider=human,
            decided_at="2026-07-11T00:11:00Z",
            status="confirmed",
        )
        transaction = Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id="txn_smuggled_decision",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=human,
            intent="Attempt an invalid authority transition.",
            operations=(RecordDecisionOp(decision=decision),),
            created_at="2026-07-11T00:11:01Z",
            parent_transaction_hash=run.base_revision,
        )
        path = self.root / "smuggled.json"
        path.write_bytes(transaction_bytes(transaction))

        with self.assertRaises(StagingError):
            stage_candidate(self.layout, run.route_run_id, path)
        self.assertEqual(replay(self.layout).head, snapshot.head)

    def test_raw_commit_cannot_bypass_route_operation_allowlist(self) -> None:
        snapshot = init_project(
            self.root, name="Route operation case", actor_id="human_owner"
        )
        agent = Actor(kind="agent", actor_id="agent_route_contract")
        run = begin_run(
            self.layout,
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=agent,
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=4000,
        )
        previous = RelationVersionRef(relation_id="rel_missing", version=1)
        disallowed = RelationVersion(
            relation_id=previous.relation_id,
            relation_type="supports",
            version=2,
            project_id=snapshot.project_id,
            source=EntityVersionRef(entity_id=snapshot.project_id, version=1),
            target=EntityVersionRef(entity_id=snapshot.project_id, version=1),
            dependency_mode="trace_only",
            created_at="2026-07-11T00:11:30Z",
            supersedes=previous,
        )
        transaction = Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id="txn_disallowed_route_operation",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=agent,
            intent="Attempt a raw commit outside the route write allowlist.",
            operations=(
                SupersedeRelationOp(previous=previous, relation=disallowed),
            ),
            created_at="2026-07-11T00:11:31Z",
            parent_transaction_hash=run.base_revision,
        )

        with self.assertRaisesRegex(
            CandidateValidationError, "cannot commit operations"
        ):
            preflight_candidate(self.layout, transaction)
        self.assertEqual(replay(self.layout).head, snapshot.head)

    def test_restricted_route_context_taints_new_entity_and_artifact_outputs(self) -> None:
        snapshot = init_project(
            self.root, name="Context privacy case", actor_id="human_owner"
        )
        agent = Actor(kind="agent", actor_id="agent_context_privacy")
        setup_run = begin_run(
            self.layout,
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=agent,
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=4000,
        )
        secret = make_entity(
            snapshot.project_id,
            "ent_restricted_context",
            "ResearchQuestion",
            formal="TOP_SECRET",
        ).model_copy(update={"privacy": "restricted"})
        setup_transaction = Transaction(
            **transaction_bindings(self.layout, setup_run.route_run_id),
            transaction_id="txn_create_restricted_context",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=setup_run.base_revision,
            route_run_id=setup_run.route_run_id,
            route_id=setup_run.route_id,
            actor=agent,
            intent="Create one restricted context input.",
            operations=(CreateEntityOp(entity=secret),),
            privacy="restricted",
            created_at="2026-07-11T00:12:00Z",
            parent_transaction_hash=setup_run.base_revision,
        )
        committed = commit_transaction(self.layout, setup_transaction)
        self.assertEqual(committed.status, "committed")
        assert committed.snapshot is not None

        entity_run = begin_run(
            self.layout,
            committed.snapshot,
            route_id="frame.question_and_benchmarks",
            actor=agent,
            purpose="research_framing",
            compartments=("project_research",),
            privacy_clearance="restricted",
            focus_entity_ids=(secret.entity_id,),
            budget_units=4000,
        )
        public_entity = make_entity(
            snapshot.project_id,
            "ent_public_leak",
            "ResearchQuestion",
            formal="TOP_SECRET",
        ).model_copy(update={"privacy": "public"})
        entity_transaction = Transaction(
            **transaction_bindings(self.layout, entity_run.route_run_id),
            transaction_id="txn_public_entity_from_restricted_context",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=entity_run.base_revision,
            route_run_id=entity_run.route_run_id,
            route_id=entity_run.route_id,
            actor=agent,
            intent="Attempt to publish a restricted context as a new entity.",
            operations=(CreateEntityOp(entity=public_entity),),
            created_at="2026-07-11T00:12:01Z",
            parent_transaction_hash=entity_run.base_revision,
        )
        with self.assertRaises(CandidateError):
            preflight_candidate(self.layout, entity_transaction)

        artifact_run = begin_run(
            self.layout,
            committed.snapshot,
            route_id="frame.question_and_benchmarks",
            actor=agent,
            purpose="research_framing",
            compartments=("project_research",),
            privacy_clearance="restricted",
            focus_entity_ids=(secret.entity_id,),
            budget_units=4000,
        )
        secret_bytes = b"TOP_SECRET"
        staged = self.root / "proposed-public-leak.bin"
        staged.write_bytes(secret_bytes)
        artifact = ArtifactRegistration(
            artifact_id="art_public_leak",
            version=1,
            project_id=snapshot.project_id,
            logical_name="public leak",
            media_type="application/octet-stream",
            content_hash=sha256_digest(secret_bytes),
            byte_size=len(secret_bytes),
            privacy="public",
            created_at="2026-07-11T00:12:02Z",
        )
        artifact_transaction = Transaction(
            **transaction_bindings(self.layout, artifact_run.route_run_id),
            transaction_id="txn_public_artifact_from_restricted_context",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=artifact_run.base_revision,
            route_run_id=artifact_run.route_run_id,
            route_id=artifact_run.route_id,
            actor=agent,
            intent="Attempt to publish restricted context bytes under a new ID.",
            operations=(RegisterArtifactOp(artifact=artifact),),
            created_at="2026-07-11T00:12:03Z",
            parent_transaction_hash=artifact_run.base_revision,
        )
        with self.assertRaises(CandidateError):
            preflight_candidate(
                self.layout,
                artifact_transaction,
                [StagedArtifact(artifact.artifact_id, 1, staged)],
            )
        self.assertEqual(replay(self.layout).head, committed.head_after)

    def test_workspace_tamper_cannot_change_preserved_context_provenance(self) -> None:
        snapshot = init_project(
            self.root, name="Provenance case", actor_id="human_owner"
        )
        agent = Actor(kind="agent", actor_id="agent_provenance")
        run = begin_run(
            self.layout,
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=agent,
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=4000,
        )
        proposal = make_entity(
            snapshot.project_id,
            "ent_provenance",
            "ResearchQuestion",
            formal="why does the benchmark fail?",
        )
        transaction = Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id="txn_bound_context",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=agent,
            intent="Commit one context-bound proposal.",
            operations=(CreateEntityOp(entity=proposal),),
            created_at="2026-07-11T00:12:00Z",
            parent_transaction_hash=run.base_revision,
        )
        candidate = self.root / "bound.json"
        candidate.write_bytes(transaction_bytes(transaction))
        stage_candidate(self.layout, run.route_run_id, candidate)
        result = commit_run(self.layout, run.route_run_id)
        self.assertEqual(result.status, "committed")

        manifest_path = context_path(self.layout, run.route_run_id)
        manifest_path.write_bytes(manifest_path.read_bytes() + b" ")
        self.assertEqual(replay(self.layout).head, result.head_after)

        preserved = self.layout.provenance_root / transaction.context_manifest_hash
        preserved.write_bytes(b"corrupt canonical provenance")
        with self.assertRaises(ChainIntegrityError):
            replay(self.layout)
        self.assertEqual(self.layout.main_ref.read_text(encoding="ascii").strip(), result.head_after)

    def test_init_begin_stage_commit_stale_render_recover(self) -> None:
        snapshot = init_project(
            self.root, name="R0 walking case", actor_id="human_owner"
        )
        agent = Actor(kind="agent", actor_id="agent_walking")
        run = begin_run(
            self.layout,
            snapshot,
            route_id="frame.question_and_benchmarks",
            actor=agent,
            purpose="research_framing",
            compartments=("project_research",),
            focus_entity_ids=(snapshot.project_id,),
            budget_units=4000,
        )

        assumption = make_entity(
            snapshot.project_id, "ent_assumption", "Assumption", formal="theta <= 1"
        )
        claim = make_entity(
            snapshot.project_id, "ent_claim", "Claim", formal="payoff is bounded"
        )
        verification = make_entity(
            snapshot.project_id,
            "ent_verification",
            "VerificationRecord",
            formal="verified under theta <= 1",
        )
        manuscript = make_entity(
            snapshot.project_id,
            "ent_manuscript",
            "ManuscriptUnit",
            presentation="The payoff is bounded.",
        )
        independent = make_entity(
            snapshot.project_id,
            "ent_independent",
            "Claim",
            formal="an independent result",
        )
        operations = (
            *(CreateEntityOp(entity=item) for item in (
                assumption,
                claim,
                verification,
                manuscript,
                independent,
            )),
            CreateRelationOp(
                relation=dependency(
                    snapshot.project_id, "rel_a_c", assumption, claim
                )
            ),
            CreateRelationOp(
                relation=dependency(
                    snapshot.project_id, "rel_c_v", claim, verification
                )
            ),
            CreateRelationOp(
                relation=dependency(
                    snapshot.project_id,
                    "rel_c_m",
                    claim,
                    manuscript,
                    target_facet="terminology_presentation",
                    mode="presentation",
                )
            ),
        )
        transaction = Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id="txn_r0_entities",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=agent,
            intent="Create the R0 dependency fixture.",
            operations=operations,
            created_at="2026-07-11T01:02:00Z",
            parent_transaction_hash=run.base_revision,
        )
        transaction_file = self.root / "candidate-r0.json"
        transaction_file.write_bytes(transaction_bytes(transaction))
        stage_candidate(self.layout, run.route_run_id, transaction_file)
        first_commit = commit_run(self.layout, run.route_run_id)
        self.assertEqual(first_commit.status, "committed")

        first_snapshot = replay(self.layout)
        repair_run = begin_run(
            self.layout,
            first_snapshot,
            route_id="repair.dependency",
            actor=agent,
            purpose="research_repair",
            compartments=("project_research",),
            focus_entity_ids=(assumption.entity_id,),
            budget_units=5000,
        )
        revised_assumption = make_entity(
            snapshot.project_id,
            assumption.entity_id,
            "Assumption",
            formal="theta <= 2",
            version=2,
        )
        revision = Transaction(
            **transaction_bindings(self.layout, repair_run.route_run_id),
            transaction_id="txn_change_assumption",
            origin="route_run",
            project_id=snapshot.project_id,
            base_revision=repair_run.base_revision,
            route_run_id=repair_run.route_run_id,
            route_id=repair_run.route_id,
            actor=agent,
            intent="Change the load-bearing formal assumption.",
            changed_facets=(
                ChangedFacets(
                    entity_id=assumption.entity_id,
                    previous_version=1,
                    new_version=2,
                    facets=("formal",),
                ),
            ),
            operations=(
                SupersedeEntityOp(
                    previous=EntityVersionRef(
                        entity_id=assumption.entity_id, version=1
                    ),
                    entity=revised_assumption,
                ),
            ),
            created_at="2026-07-11T01:03:00Z",
            parent_transaction_hash=repair_run.base_revision,
        )
        revision_file = self.root / "candidate-revision.json"
        revision_file.write_bytes(transaction_bytes(revision))
        stage_candidate(self.layout, repair_run.route_run_id, revision_file)
        second_commit = commit_run(self.layout, repair_run.route_run_id)
        self.assertEqual(second_commit.status, "committed")

        final = replay(self.layout)
        self.assertEqual(final.derived_status["ent_claim"].freshness["formal"], "stale")
        self.assertEqual(
            final.derived_status["ent_verification"].freshness["formal"], "stale"
        )
        self.assertEqual(
            final.derived_status["ent_manuscript"].freshness[
                "terminology_presentation"
            ],
            "stale",
        )
        self.assertEqual(
            final.derived_status["ent_independent"].freshness["formal"], "fresh"
        )
        self.assertTrue(stale_reason_chains(final, "ent_verification", "formal"))

        self.layout.status_view.write_text(
            "human_confirmed=true\nformal=verified\n", encoding="utf-8"
        )
        report = recover(self.layout)
        self.assertEqual(report.head, final.head)
        regenerated = self.layout.status_view.read_text(encoding="utf-8")
        self.assertIn("GENERATED", regenerated)
        self.assertIn("NONCANONICAL", regenerated)
        self.assertIn(final.head, regenerated)


if __name__ == "__main__":
    unittest.main()
