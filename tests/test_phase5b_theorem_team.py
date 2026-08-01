from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from econ_theorist import theory as t
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.machine.models import WorkPacketV1
from econ_theorist.machine.operational import (
    ContentAddressedOperationalStore,
    OperationalError,
    ProjectOperationalLayout,
)
from econ_theorist.models import (
    EntityVersion,
    EntityVersionRef,
    ScientificStatus,
)
from econ_theorist.runtime import StoreLayout
from econ_theorist.theorem_team import (
    build_theorem_lane_output,
    build_theorem_team_delivery_authorization,
    open_theorem_team_plan,
    publish_theorem_team_completion_binding,
    publish_theorem_team_review,
    read_theorem_team_delivery_authorization,
    read_theorem_team_plan,
    read_theorem_team_review,
    theorem_team_completion_binding_exists,
    theorem_team_is_active,
    theorem_team_review_exists,
)


class Phase5BTheoremTeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name) / "paper"
        self.root.mkdir()
        self.layout = StoreLayout.at(self.root)
        self.operational = ProjectOperationalLayout.at(self.layout).ensure()
        self.project_id = "project.theorem.team"
        self.base_head = "1" * 64
        self.route_run_id = "run.theorem.team"
        self.graph_ref = EntityVersionRef(entity_id="claim.graph", version=1)
        self.obligation_refs = (
            EntityVersionRef(entity_id="obligation.boundary", version=1),
            EntityVersionRef(entity_id="obligation.existence", version=1),
        )
        entities = self._theory_entities()
        compiled_context = {
            "context_schema": "econ-theorist/compiled-context/v1",
            "source_head": self.base_head,
            "project_id": self.project_id,
            "route": {"route_id": "verify.claims_proofs_and_interpretation"},
            "entities": tuple(item.model_dump(mode="json") for item in entities),
            "relations": (),
            "effective_decisions": (),
            "status_source_decisions": (),
            "derived_status": {},
            "blockers": (),
            "omissions": (),
        }
        self.packet = WorkPacketV1(
            packet_compiler_version=2,
            engine_version="test-engine",
            engine_semantics_hash="2" * 64,
            project_id=self.project_id,
            base_head=self.base_head,
            route_run_id=self.route_run_id,
            route_run_hash="3" * 64,
            context_manifest_hash="4" * 64,
            compiled_context_hash=sha256_digest(canonical_json_bytes(compiled_context)),
            run_input_brief_hash=None,
            navigation_candidate_digest="5" * 64,
            route_id="verify.claims_proofs_and_interpretation",
            route_version=2,
            purpose="research_verification",
            actor_role="scientific.coordinator",
            focus_refs=(self.graph_ref, *self.obligation_refs),
            route_registry_hash="6" * 64,
            instruction_bundle_hash="7" * 64,
            context_selector_version="context_selector.v1",
            policy_hashes={"kernel": "8" * 64},
            privacy_clearance="project_private",
            compartments=("project_research",),
            instruction_text="Verify every retained proof obligation independently.",
            compiled_context=compiled_context,
            run_input=None,
            omissions=(),
            hidden_compartments=(),
            pending_human_gate_refs=(),
            candidate_logical_path=(
                f".econ-theorist/staging/{self.route_run_id}/candidate.json"
            ),
            shadow_logical_root=(
                f".econ-theorist/operational/v1/runs/{self.route_run_id}/shadow"
            ),
            allowed_operation_classes=("entity.create", "relation.create"),
            required_output_entity_types=(
                "VerificationBundle",
                "VerificationRecord",
            ),
            required_output_relation_types=("supports", "verifies"),
            forbidden_actions=(
                "canonical_store_direct_write",
                "human_decision_fabrication",
                "undeclared_agent_delegation",
            ),
        )
        store = ContentAddressedOperationalStore(
            self.operational.project_root,
            self.operational.runs / self.route_run_id,
        )
        self.work_packet_hash, _ = store.install("packets", self.packet)
        replay_patch = mock.patch(
            "econ_theorist.theorem_team.replay",
            return_value=SimpleNamespace(
                project_id=self.project_id,
                head=self.base_head,
            ),
        )
        self.mock_replay = replay_patch.start()
        self.addCleanup(replay_patch.stop)

    def _entity(self, entity_id: str, payload: t.TheoryPayload) -> EntityVersion:
        return EntityVersion(
            entity_id=entity_id,
            entity_type=type(payload).__name__,
            version=1,
            project_id=self.project_id,
            title=entity_id,
            summary=f"Test payload for {entity_id}.",
            status=ScientificStatus(lifecycle="active"),
            facets=t.pack_theory_payload(payload),
            privacy="project_private",
            access_compartments=("project_research",),
            created_at="2026-08-01T00:00:00Z",
        )

    def _theory_entities(self) -> tuple[EntityVersion, ...]:
        claim = t.ClaimNode(
            claim_id="claim.headline",
            archetype="mechanism_explanation",
            scientific_job="headline",
            formal_statement="For every admissible type, an equilibrium exists.",
            domain="The approved finite type space.",
            quantifiers=("for every admissible type",),
            assumption_ids=("assumption.compact",),
            semantic_translation="The mechanism remains operational on its domain.",
            dependency_refs=(),
            mechanism_ref=EntityVersionRef(entity_id="mechanism.main", version=1),
            proof_obligation_refs=self.obligation_refs,
            boundary_case_ids=("boundary.zero",),
        )
        graph = t.ClaimGraph(
            formal_model_ref=EntityVersionRef(entity_id="formal.model", version=1),
            formalization_map_ref=EntityVersionRef(
                entity_id="formalization.map", version=1
            ),
            assumption_map_ref=EntityVersionRef(
                entity_id="assumption.map", version=1
            ),
            claims=(claim,),
            dependency_edges=(),
            contribution_spine=("claim.headline",),
        )
        boundary = t.ProofObligation(
            claim_graph_ref=self.graph_ref,
            claim_id="claim.headline",
            obligation_id="proof.boundary",
            statement="Exclude the zero-transfer boundary counterexample.",
            burden="counterexample_exclusion",
            quantifier_scope="Every admissible zero-transfer boundary state.",
            assumption_ids=("assumption.compact",),
            admissible_methods=("counterexample", "analytic_proof"),
        )
        existence = t.ProofObligation(
            claim_graph_ref=self.graph_ref,
            claim_id="claim.headline",
            obligation_id="proof.existence",
            statement="Establish equilibrium existence.",
            burden="existence",
            quantifier_scope="Every admissible type profile.",
            assumption_ids=("assumption.compact",),
            admissible_methods=("analytic_proof", "formal_proof"),
        )
        return (
            self._entity("claim.graph", graph),
            self._entity("obligation.boundary", boundary),
            self._entity("obligation.existence", existence),
        )

    def _authorization(self):
        return build_theorem_team_delivery_authorization(
            self.packet,
            self.work_packet_hash,
            source_delivery_envelope_hash="a" * 64,
            source_capability_receipt_hash="b" * 64,
            source_egress_plan_hash="c" * 64,
            host_product="focused-test-host",
            host_version="1",
            adapter_id="focused-test-adapter",
            adapter_version="1",
            host_session_id="focused-test-session",
            lane_separation_claim="logical",
        )

    def _open(self):
        return open_theorem_team_plan(
            self.operational,
            route_run_id=self.route_run_id,
            work_packet_hash=self.work_packet_hash,
            delivery_authorization=self._authorization(),
        )

    def _outputs(self):
        plan_hash, plan = self._open()
        proof = build_theorem_lane_output(
            plan,
            plan_hash,
            lane_id="proof_worker",
            agent_label="proof.worker.test",
            model_observation="test-model",
            content_markdown=(
                "Existence: analytic fixed-point skeleton. Boundary: the stated "
                "exclusion fails at the zero-transfer state; narrow the claim."
            ),
        )
        challenger = build_theorem_lane_output(
            plan,
            plan_hash,
            lane_id="counterexample_economics_challenger",
            agent_label="challenger.test",
            model_observation="test-model",
            content_markdown=(
                "The boundary counterexample survives and the economic translation "
                "is broader than the formal existence statement."
            ),
        )
        return plan_hash, plan, proof, challenger

    def _review(self):
        plan_hash, plan, proof, challenger = self._outputs()
        review_hash, review = publish_theorem_team_review(
            self.operational,
            route_run_id=self.route_run_id,
            work_packet_hash=self.work_packet_hash,
            proof_worker=proof,
            counterexample_economics_challenger=challenger,
        )
        return plan_hash, plan, review_hash, review

    def _nonoperational_files(self) -> tuple[str, ...]:
        store = self.layout.store_root
        operational = self.operational.root
        return tuple(
            sorted(
                str(path.relative_to(store))
                for path in store.rglob("*")
                if path.is_file() and operational not in path.parents
            )
        )

    def test_plan_binds_full_obligation_set_and_exact_retry(self) -> None:
        before = self._nonoperational_files()
        plan_hash, plan = self._open()
        retry_hash, retry = self._open()

        self.assertEqual((retry_hash, retry), (plan_hash, plan))
        self.assertEqual(plan.proof_obligation_refs, self.obligation_refs)
        self.assertTrue(plan.single_canonical_writer)
        self.assertEqual(plan.canonical_writer_role, "coordinator")
        self.assertFalse(plan.canonical_write_allowed)
        self.assertEqual(
            set(plan.role_overlays),
            {"proof_worker", "counterexample_economics_challenger"},
        )
        self.assertTrue(
            theorem_team_is_active(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
            )
        )
        self.assertEqual(
            read_theorem_team_plan(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
            ),
            plan,
        )
        self.assertEqual(
            read_theorem_team_delivery_authorization(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
                team_plan_hash=plan_hash,
            ),
            self._authorization(),
        )
        self.assertEqual(self._nonoperational_files(), before)

    def test_review_requires_both_exact_lane_assignments_and_retries(self) -> None:
        plan_hash, plan, proof, challenger = self._outputs()
        duplicate_agent = challenger.model_copy(
            update={"agent_label": proof.agent_label}
        )
        with self.assertRaisesRegex(ValueError, "distinct advisory agents"):
            publish_theorem_team_review(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
                proof_worker=proof,
                counterexample_economics_challenger=duplicate_agent,
            )
        reserved_agent = challenger.model_copy(
            update={"agent_label": plan.coordinator_agent_label}
        )
        with self.assertRaisesRegex(ValueError, "reserves the coordinator"):
            publish_theorem_team_review(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
                proof_worker=proof,
                counterexample_economics_challenger=reserved_agent,
            )
        review_hash, review = publish_theorem_team_review(
            self.operational,
            route_run_id=self.route_run_id,
            work_packet_hash=self.work_packet_hash,
            proof_worker=proof,
            counterexample_economics_challenger=challenger,
        )
        retry_hash, retry = publish_theorem_team_review(
            self.operational,
            route_run_id=self.route_run_id,
            work_packet_hash=self.work_packet_hash,
            proof_worker=proof,
            counterexample_economics_challenger=challenger,
        )

        self.assertEqual((retry_hash, retry), (review_hash, review))
        self.assertEqual(review.team_plan_hash, plan_hash)
        self.assertEqual(review.proof_obligation_refs, plan.proof_obligation_refs)
        self.assertTrue(
            theorem_team_review_exists(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
            )
        )
        self.assertEqual(
            read_theorem_team_review(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
                review_hash=review_hash,
            ),
            review,
        )

        tampered = proof.model_copy(update={"lane_input_hash": "f" * 64})
        with self.assertRaisesRegex(OperationalError, "invalid assignment"):
            publish_theorem_team_review(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
                proof_worker=tampered,
                counterexample_economics_challenger=challenger,
            )

    def test_completion_binding_is_coordinator_owned_and_exact_retry(self) -> None:
        _, plan, review_hash, _ = self._review()
        first_hash, first, first_mutated = publish_theorem_team_completion_binding(
            self.operational,
            route_run_id=self.route_run_id,
            work_packet_hash=self.work_packet_hash,
            review_hash=review_hash,
            completion_operation_key="complete.theorem.team",
            delivery_envelope_hash="a" * 64,
            candidate_digest="d" * 64,
            coordinator_agent_label=plan.coordinator_agent_label,
            coordinator_model_observation="test-model",
        )
        retry_hash, retry, retry_mutated = publish_theorem_team_completion_binding(
            self.operational,
            route_run_id=self.route_run_id,
            work_packet_hash=self.work_packet_hash,
            review_hash=review_hash,
            completion_operation_key="complete.theorem.team",
            delivery_envelope_hash="a" * 64,
            candidate_digest="d" * 64,
            coordinator_agent_label=plan.coordinator_agent_label,
            coordinator_model_observation="test-model",
        )

        self.assertTrue(first_mutated)
        self.assertFalse(retry_mutated)
        self.assertEqual((retry_hash, retry), (first_hash, first))
        self.assertEqual(first.canonical_writer_role, "coordinator")
        self.assertTrue(
            theorem_team_completion_binding_exists(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
                completion_operation_key="complete.theorem.team",
            )
        )

        with self.assertRaisesRegex(OperationalError, "different theorem provenance"):
            publish_theorem_team_completion_binding(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
                review_hash=review_hash,
                completion_operation_key="complete.theorem.team",
                delivery_envelope_hash="a" * 64,
                candidate_digest="e" * 64,
                coordinator_agent_label=plan.coordinator_agent_label,
                coordinator_model_observation="test-model",
            )
        with self.assertRaisesRegex(OperationalError, "different coordinator"):
            publish_theorem_team_completion_binding(
                self.operational,
                route_run_id=self.route_run_id,
                work_packet_hash=self.work_packet_hash,
                review_hash=review_hash,
                completion_operation_key="complete.theorem.team.second",
                delivery_envelope_hash="a" * 64,
                candidate_digest="d" * 64,
                coordinator_agent_label="proof.worker.test",
                coordinator_model_observation="test-model",
            )

    def test_wrong_route_incomplete_closure_and_stale_head_fail_closed(self) -> None:
        wrong_route = self.packet.model_copy(update={"route_id": "curate.result_portfolio"})
        with self.assertRaisesRegex(OperationalError, "only claim verification"):
            build_theorem_team_delivery_authorization(
                wrong_route,
                sha256_digest(canonical_json_bytes(wrong_route)),
                source_delivery_envelope_hash="a" * 64,
                source_capability_receipt_hash="b" * 64,
                source_egress_plan_hash="c" * 64,
                host_product="test",
                host_version="1",
                adapter_id="test",
                adapter_version="1",
                host_session_id="test",
                lane_separation_claim="logical",
            )

        incomplete = self.packet.model_copy(
            update={
                "focus_refs": (self.graph_ref, self.obligation_refs[0]),
            }
        )
        with self.assertRaisesRegex(OperationalError, "every and only"):
            build_theorem_team_delivery_authorization(
                incomplete,
                sha256_digest(canonical_json_bytes(incomplete)),
                source_delivery_envelope_hash="a" * 64,
                source_capability_receipt_hash="b" * 64,
                source_egress_plan_hash="c" * 64,
                host_product="test",
                host_version="1",
                adapter_id="test",
                adapter_version="1",
                host_session_id="test",
                lane_separation_claim="logical",
            )

        self.mock_replay.return_value = SimpleNamespace(
            project_id=self.project_id,
            head="9" * 64,
        )
        with self.assertRaisesRegex(OperationalError, "base head is stale"):
            self._open()


if __name__ == "__main__":
    unittest.main()
