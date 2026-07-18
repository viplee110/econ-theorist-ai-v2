"""Focused tests for the noncanonical registry-v8 semantic compiler."""

from __future__ import annotations

from copy import deepcopy
import unittest

from tests import test_framing_quality_route as framing_fixture
from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.candidate_contract import compile_candidate_authoring_contract
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.framing_quality import (
    FramingObjectRef,
    HeldFixedObjectRef,
    parse_framing_quality_payload,
)
from econ_theorist.framing_quality_authoring import (
    BenchmarkChannelIntentV1,
    FramingAuditCompilationError,
    FramingAuditSemanticDraftV1,
    compile_framing_audit_semantic_draft,
    preflight_framing_audit_semantic_draft,
)
from econ_theorist.machine.models import WorkPacketV1
from econ_theorist.models import (
    CreateEntityOp,
    CreateRelationOp,
    EntityVersion,
    EntityVersionRef,
    RecordDecisionOp,
    RecordRouteOutcomeOp,
    RelationVersionRef,
)
from econ_theorist.policy import (
    ROUTE_REGISTRY_V6_HASH,
    ROUTE_REGISTRY_V8_HASH,
    instruction_bundle_bytes,
    route_spec_by_hash,
)
from econ_theorist.runs import (
    read_compiled_context,
    read_context,
    read_run,
    transaction_bindings,
)
from econ_theorist.runtime.freshness import facet_semantic_hash
from econ_theorist.runtime.replay import replay, validate_candidate


class FramingQualitySemanticAuthoringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = framing_fixture.FramingQualityRouteTests(
            methodName=(
                "test_candidate_contract_exposes_bundle_schema_and_framing_invariants"
            )
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def _open_v8_contract(
        self,
        *,
        quality_node_kind: str = "choice",
        continuation: bool = False,
    ) -> tuple[object, object, tuple[EntityVersion, ...]]:
        core = self.fixture._phase2_prefix(quality_node_kind=quality_node_kind)
        focus = tuple(item.entity_id for item in core)
        created_at = framing_fixture.T3
        if continuation:
            prior_bundle, _, _ = self.fixture._commit_audit(
                core,
                proposed_action="continue_diagnostic",
                route_registry_hash=ROUTE_REGISTRY_V6_HASH,
            )
            focus = (*focus, prior_bundle.entity_id)
            created_at = framing_fixture.T4
        snapshot, run = self.fixture._begin(
            route_id="audit.framing_economics",
            purpose="scientific_framing_audit",
            focus=focus,
            created_at=created_at,
            route_registry_hash=ROUTE_REGISTRY_V8_HASH,
        )
        run_id = run.route_run_id
        manifest = read_context(self.fixture.layout, run_id)
        canonical_run = read_run(self.fixture.layout, run_id)
        compiled = read_compiled_context(self.fixture.layout, run_id)
        bindings = transaction_bindings(self.fixture.layout, run_id)
        route = route_spec_by_hash(canonical_run.route_id, manifest.route_registry_hash)
        packet = WorkPacketV1(
            packet_compiler_version=2,
            engine_version="test",
            engine_semantics_hash="a" * 64,
            project_id=canonical_run.project_id,
            base_head=canonical_run.base_revision,
            route_run_id=run_id,
            route_run_hash=bindings["route_run_hash"],
            context_manifest_hash=bindings["context_manifest_hash"],
            compiled_context_hash=bindings["compiled_context_hash"],
            run_input_brief_hash=None,
            navigation_candidate_digest="b" * 64,
            route_id=canonical_run.route_id,
            route_version=canonical_run.route_version,
            purpose=canonical_run.purpose,
            actor_role=canonical_run.actor.actor_id,
            focus_refs=tuple(
                EntityVersionRef(
                    entity_id=entity_id,
                    version=snapshot.current_entities[entity_id],
                )
                for entity_id in canonical_run.focus_entity_ids
            ),
            route_registry_hash=manifest.route_registry_hash,
            instruction_bundle_hash=manifest.instruction_bundle_hash,
            context_selector_version=manifest.selector_version,
            policy_hashes={},
            privacy_clearance=canonical_run.privacy_clearance,
            compartments=canonical_run.compartments,
            instruction_text=instruction_bundle_bytes(route).decode("utf-8"),
            compiled_context=compiled,
            run_input=None,
            omissions=manifest.omissions,
            hidden_compartments=(),
            pending_human_gate_refs=(),
            candidate_logical_path=(
                f".econ-theorist/staging/{run_id}/candidate.json"
            ),
            shadow_logical_root=(
                f".econ-theorist/operational/v1/runs/{run_id}/shadow"
            ),
            allowed_operation_classes=route.allowed_operations,
            required_output_entity_types=tuple(
                item.entity_type for item in route.required_output_entities
            ),
            required_output_relation_types=tuple(
                item.relation_type for item in route.required_output_relations
            ),
            forbidden_actions=("human_decision_fabrication",),
        )
        contract = compile_candidate_authoring_contract(
            self.fixture.layout,
            packet,
            sha256_digest(canonical_json_bytes(packet)),
        )
        return snapshot, contract, core

    def _negative_payload(self, core: tuple[EntityVersion, ...]):
        payload = self.fixture._bundle_payload(*core)
        return self.fixture._unwitnessed_negative_revision(
            self.fixture._research_first_bundle(payload)
        )

    def _semantic_draft(
        self,
        payload: object,
        *,
        waypoint_override: tuple[str, ...] | None = None,
    ) -> FramingAuditSemanticDraftV1:
        raw = payload.model_dump(mode="json", exclude_none=False)
        for field_name in (
            "research_question_ref",
            "benchmark_set_ref",
            "primitive_graph_ref",
            "source_g1_dossier_ref",
        ):
            raw.pop(field_name)
        intents = []
        for row in raw["benchmark_assessments"]:
            path = tuple(row.pop("channel_path"))
            intents.append(
                BenchmarkChannelIntentV1(
                    benchmark_id=row["benchmark_id"],
                    changed_object_id=row["changed"][0]["object_id"],
                    target_object_id=row["targets"][0]["object_id"],
                    ordered_waypoint_node_ids=(
                        path[1:-1]
                        if waypoint_override is None
                        else waypoint_override
                    ),
                )
            )
        return FramingAuditSemanticDraftV1(
            bundle_payload=raw,
            channel_intents=tuple(intents),
        )

    def test_compiler_wraps_outputs_and_instantiates_exact_v8_relations(
        self,
    ) -> None:
        snapshot, contract, core = self._open_v8_contract()
        head_before = replay(self.fixture.layout).head
        draft = self._semantic_draft(self._negative_payload(core))

        first = compile_framing_audit_semantic_draft(snapshot, contract, draft)
        second = compile_framing_audit_semantic_draft(snapshot, contract, draft)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))

        bindings = contract.transaction_bindings
        for field_name in (
            "transaction_schema",
            "origin",
            "project_id",
            "base_revision",
            "route_run_id",
            "route_id",
            "route_run_hash",
            "context_manifest_hash",
            "compiled_context_hash",
            "actor",
            "privacy",
            "access_compartments",
            "created_at",
            "parent_transaction_hash",
        ):
            self.assertEqual(getattr(first, field_name), getattr(bindings, field_name))
        self.assertEqual(first.evidence_refs, bindings.required_entity_evidence_refs)

        entity_ops = [
            operation
            for operation in first.operations
            if isinstance(operation, CreateEntityOp)
        ]
        relation_ops = [
            operation
            for operation in first.operations
            if isinstance(operation, CreateRelationOp)
        ]
        outcomes = [
            operation
            for operation in first.operations
            if isinstance(operation, RecordRouteOutcomeOp)
        ]
        self.assertEqual(len(entity_ops), 2)
        self.assertEqual(len(relation_ops), 5)
        self.assertEqual(len(outcomes), 1)
        self.assertFalse(
            any(isinstance(operation, RecordDecisionOp) for operation in first.operations)
        )
        outputs_by_type = {
            operation.entity.entity_type: operation.entity for operation in entity_ops
        }
        bundle_entity = outputs_by_type["FramingQualityBundle"]
        dossier_entity = outputs_by_type["GateDossier"]
        for entity in (bundle_entity, dossier_entity):
            self.assertEqual(entity.version, 1)
            self.assertEqual(entity.project_id, bindings.project_id)
            self.assertEqual(entity.privacy, bindings.privacy)
            self.assertEqual(
                entity.access_compartments, bindings.access_compartments
            )
            self.assertEqual(entity.created_at, bindings.created_at)

        exact_entities = {
            (entity.entity_id, entity.version): entity
            for entity in snapshot.entity_versions
        }
        candidate_outputs = {
            "FramingQualityBundle": bundle_entity,
            "GateDossier": dossier_entity,
        }
        for operation, template in zip(
            relation_ops, contract.output_contract.required_relation_templates
        ):
            relation = operation.relation
            source = (
                exact_entities[
                    (template.source.entity_ref.entity_id, template.source.entity_ref.version)
                ]
                if template.source.binding_kind == "exact_input"
                else candidate_outputs[template.source.entity_type]
            )
            target = (
                exact_entities[
                    (template.target.entity_ref.entity_id, template.target.entity_ref.version)
                ]
                if template.target.binding_kind == "exact_input"
                else candidate_outputs[template.target.entity_type]
            )
            self.assertEqual(relation.source, framing_fixture.eref(source))
            self.assertEqual(relation.target, framing_fixture.eref(target))
            self.assertEqual(relation.relation_type, template.relation_type)
            self.assertEqual(relation.dependency_mode, "hard")
            self.assertIsNone(relation.supersedes)
            self.assertEqual(relation.upstream.facet, template.source.facet)
            self.assertEqual(relation.downstream.facet, template.target.facet)
            expected_hash = (
                template.upstream_semantic_hash
                if template.upstream_semantic_hash_binding == "contract_value"
                else facet_semantic_hash(source, template.source.facet)
            )
            self.assertEqual(relation.upstream.semantic_hash, expected_hash)

        expected_refs = (
            framing_fixture.eref(bundle_entity),
            framing_fixture.eref(dossier_entity),
            *(
                RelationVersionRef(
                    relation_id=item.relation.relation_id,
                    version=item.relation.version,
                )
                for item in relation_ops
            ),
        )
        self.assertEqual(outcomes[0].outcome.candidate_refs, expected_refs)
        validate_candidate(
            snapshot,
            first,
            route_registry_hash=ROUTE_REGISTRY_V8_HASH,
            enforce_live_current_policy=True,
        )
        self.assertEqual(replay(self.fixture.layout).head, head_before)

    def test_structural_preflight_batches_independent_issues(self) -> None:
        snapshot, contract, core = self._open_v8_contract()
        head_before = replay(self.fixture.layout).head
        payload = self._negative_payload(core)
        row = payload.benchmark_assessments[0]
        incompatible = row.still_endogenous[0].model_copy(
            update={
                "object_id": "object.incompatible.response",
                "semantic_level": "behavioral_response",
                "primitive_node_id": "node.certification",
            }
        )
        fixed_same_node = HeldFixedObjectRef(
            object_id="object.fixed.response",
            label="The same response is held fixed",
            semantic_level="behavioral_response",
            primitive_node_id="node.certification",
            fixing_level="choice",
        )
        broken_row = row.model_copy(
            update={
                "held_fixed": (*row.held_fixed, fixed_same_node),
                "still_endogenous": (incompatible,),
            }
        )
        broken_payload = payload.model_copy(
            update={"benchmark_assessments": (broken_row,)}
        )
        draft = self._semantic_draft(
            broken_payload,
            waypoint_override=("node.search_cost",),
        )

        first = preflight_framing_audit_semantic_draft(snapshot, contract, draft)
        second = preflight_framing_audit_semantic_draft(snapshot, contract, draft)
        self.assertFalse(first.passed)
        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))
        codes = {issue.rule_id for issue in first.issues}
        self.assertTrue(
            {
                "compiler.channel_path.unreachable",
                "compiler.semantic_ledger.endogenous_node_kind",
                "compiler.semantic_ledger.fixed_movable_conflict",
            }.issubset(codes)
        )
        with self.assertRaises(FramingAuditCompilationError) as caught:
            compile_framing_audit_semantic_draft(snapshot, contract, draft)
        self.assertEqual(caught.exception.issues, first.issues)
        self.assertEqual(replay(self.fixture.layout).head, head_before)

    def test_preflight_reports_missing_active_node_bindings_together(self) -> None:
        snapshot, contract, core = self._open_v8_contract()
        head_before = replay(self.fixture.layout).head
        payload = self._negative_payload(core)
        row = payload.benchmark_assessments[0]
        missing_choice = row.reoptimizing[0].model_copy(
            update={"primitive_node_id": None}
        )
        missing_endogenous = row.still_endogenous[0].model_copy(
            update={"primitive_node_id": None}
        )
        broken_row = row.model_copy(
            update={
                "reoptimizing": (missing_choice, *row.reoptimizing[1:]),
                "still_endogenous": (missing_endogenous,),
            }
        )
        broken_payload = payload.model_copy(
            update={"benchmark_assessments": (broken_row,)}
        )
        draft = self._semantic_draft(broken_payload)

        report = preflight_framing_audit_semantic_draft(snapshot, contract, draft)
        self.assertFalse(report.passed)
        codes = {issue.rule_id for issue in report.issues}
        self.assertTrue(
            {
                "compiler.semantic_ledger.reoptimizing_binding_missing",
                "compiler.semantic_ledger.endogenous_binding_missing",
            }.issubset(codes)
        )
        with self.assertRaises(FramingAuditCompilationError):
            compile_framing_audit_semantic_draft(snapshot, contract, draft)
        self.assertEqual(replay(self.fixture.layout).head, head_before)

    def test_existing_channel_path_is_rejected_as_a_second_source(self) -> None:
        snapshot, contract, core = self._open_v8_contract()
        head_before = replay(self.fixture.layout).head
        draft = self._semantic_draft(self._negative_payload(core))
        raw = deepcopy(draft.bundle_payload)
        raw["benchmark_assessments"][0]["channel_path"] = [
            "node.certification",
            "node.inspection",
            "node.quality",
            "node.match",
        ]
        duplicated = FramingAuditSemanticDraftV1(
            bundle_payload=raw,
            channel_intents=draft.channel_intents,
        )

        report = preflight_framing_audit_semantic_draft(
            snapshot, contract, duplicated
        )
        self.assertFalse(report.passed)
        self.assertIn(
            "compiler.channel_path.duplicate_source",
            {issue.rule_id for issue in report.issues},
        )
        with self.assertRaises(FramingAuditCompilationError):
            compile_framing_audit_semantic_draft(snapshot, contract, duplicated)
        self.assertEqual(replay(self.fixture.layout).head, head_before)

    def test_continuation_contract_fails_closed_before_compilation(self) -> None:
        snapshot, contract, core = self._open_v8_contract(continuation=True)
        head_before = replay(self.fixture.layout).head
        draft = self._semantic_draft(self._negative_payload(core))

        report = preflight_framing_audit_semantic_draft(snapshot, contract, draft)
        self.assertFalse(report.passed)
        self.assertIn(
            "compiler.contract.continuation_unsupported",
            {issue.rule_id for issue in report.issues},
        )
        with self.assertRaises(FramingAuditCompilationError):
            compile_framing_audit_semantic_draft(snapshot, contract, draft)
        self.assertEqual(replay(self.fixture.layout).head, head_before)

    def test_fixed_policy_and_law_accounting_row_is_not_an_active_margin(
        self,
    ) -> None:
        snapshot, contract, core = self._open_v8_contract(
            quality_node_kind="equilibrium_object"
        )
        head_before = replay(self.fixture.layout).head
        payload = self._negative_payload(core)
        row = payload.benchmark_assessments[0]
        fixed_policy = HeldFixedObjectRef(
            object_id="object.fixed.policy",
            label="Buyer policy rule held fixed",
            semantic_level="behavioral_response",
            primitive_node_id="node.inspection",
            fixing_level="policy_rule",
        )
        fixed_law = HeldFixedObjectRef(
            object_id="object.fixed.stationary.law",
            label="Stationary public law held fixed",
            semantic_level="stationary_distribution",
            primitive_node_id="node.quality",
            fixing_level="stationary_distribution",
        )
        accounting = FramingObjectRef(
            object_id="object.accounting.cost",
            label="Certificate cost accounting entry",
            semantic_level="payoff_ledger",
            primitive_node_id="node.certification",
        )
        diagnostic_row = row.model_copy(
            update={
                "held_fixed": (*row.held_fixed, fixed_policy, fixed_law),
                "reoptimizing": (),
                "still_endogenous": (accounting,),
            }
        )
        diagnostic_payload = payload.model_copy(
            update={"benchmark_assessments": (diagnostic_row,)}
        )
        draft = self._semantic_draft(diagnostic_payload)

        report = preflight_framing_audit_semantic_draft(snapshot, contract, draft)
        self.assertTrue(report.passed, report.issues)
        self.assertEqual(report.active_semantic_node_ids, ())
        transaction = compile_framing_audit_semantic_draft(
            snapshot, contract, draft
        )
        bundle_entity = next(
            operation.entity
            for operation in transaction.operations
            if isinstance(operation, CreateEntityOp)
            and operation.entity.entity_type == "FramingQualityBundle"
        )
        compiled = parse_framing_quality_payload(
            "FramingQualityBundle", bundle_entity.facets
        )
        compiled_row = compiled.benchmark_assessments[0]
        self.assertEqual(compiled_row.channel_kind, "diagnostic_only")
        self.assertEqual(compiled_row.reoptimizing, ())
        self.assertEqual(compiled_row.still_endogenous, (accounting,))
        self.assertTrue(
            all(step.active_margin_witness is None for step in compiled.causal_chain)
        )
        self.assertEqual(compiled.proposed_action, "revise_framing")
        self.assertFalse(
            any(
                isinstance(operation, RecordDecisionOp)
                for operation in transaction.operations
            )
        )
        validate_candidate(
            snapshot,
            transaction,
            route_registry_hash=ROUTE_REGISTRY_V8_HASH,
            enforce_live_current_policy=True,
        )
        self.assertEqual(replay(self.fixture.layout).head, head_before)


if __name__ == "__main__":
    unittest.main()
