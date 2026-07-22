"""Focused V5.3 projection regressions for model-authored framing candidates."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tests import test_framing_quality_route as framing_fixture
from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.candidate_contract import (
    _endpoint_constraints_for_route,
    _relation_templates_for_route,
    candidate_authoring_contract_hash,
    compile_candidate_authoring_contract,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.codex_bridge import CodexBridgeResponseV1
from econ_theorist.framing_quality import FRAMING_QUALITY_PAYLOAD_OWNER_FACETS
from econ_theorist.machine.models import WorkPacketV1
from econ_theorist.models import EntityVersion, EntityVersionRef
from econ_theorist.policy import (
    ROUTE_REGISTRY_V5_HASH,
    ROUTE_REGISTRY_V6_HASH,
    ROUTE_REGISTRY_V7_HASH,
    SELECTOR_VERSION_DECOMPOSITION_REFRESH,
    SELECTOR_VERSION_DECOMPOSITION_REFRESH_V1,
    instruction_bundle_bytes,
    route_spec_by_hash,
)
from econ_theorist.runs import (
    begin_run,
    read_compiled_context,
    read_context,
    read_run,
    transaction_bindings,
)
from econ_theorist.runtime.freshness import (
    authority_semantic_hash,
    facet_semantic_hash,
)
from econ_theorist.runtime.replay import replay
from econ_theorist.theory import THEORY_PAYLOAD_OWNER_FACETS


class V53CandidateContractProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = framing_fixture.FramingQualityRouteTests(
            methodName="test_candidate_contract_exposes_bundle_schema_and_framing_invariants"
        )
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)

    def _open_audit_contract(
        self,
        *,
        continuation: bool = False,
        route_registry_hash: str | None = None,
    ) -> tuple[object, WorkPacketV1, object, tuple[EntityVersion, ...], EntityVersion | None]:
        core = self.fixture._phase2_prefix()
        prior_bundle = None
        created_at = framing_fixture.T3
        focus = tuple(item.entity_id for item in core)
        if continuation:
            # The shared fixture intentionally remains a frozen v6-valid
            # scientific example.  Commit that predecessor under its exact
            # historical route, then inspect how active v7 projects the same
            # optional predecessor without making it an audits source.
            prior_bundle, _, _ = self.fixture._commit_audit(
                core,
                proposed_action="continue_diagnostic",
                route_registry_hash=ROUTE_REGISTRY_V6_HASH,
            )
            created_at = framing_fixture.T4
            focus = (*focus, prior_bundle.entity_id)

        if route_registry_hash is None:
            snapshot, run = self.fixture._begin(
                route_id="audit.framing_economics",
                purpose="scientific_framing_audit",
                focus=focus,
                created_at=created_at,
                route_registry_hash=ROUTE_REGISTRY_V7_HASH,
            )
        else:
            self.fixture.route_counter += 1
            snapshot = replay(self.fixture.layout)
            # Materialize the shape of a pre-upgrade, already-running v5 run.
            # Current entry validation properly targets v6; resume compilation
            # must nevertheless continue to understand this frozen record.
            historical_entry = patch(
                "econ_theorist.runs.validate_phase5_route_entry",
                return_value=None,
            )
            historical_entry.start()
            self.addCleanup(historical_entry.stop)
            run = begin_run(
                self.fixture.layout,
                snapshot,
                route_id="audit.framing_economics",
                actor=framing_fixture.AGENT,
                purpose="scientific_framing_audit",
                compartments=("project_research",),
                focus_entity_ids=focus,
                budget_units=32_000,
                route_run_id=f"run.framing.{self.fixture.route_counter}",
                context_manifest_id=(
                    f"context.framing.{self.fixture.route_counter}"
                ),
                created_at=created_at,
                route_registry_hash=route_registry_hash,
            )
        run_id = getattr(run, "route_run_id")
        manifest = read_context(self.fixture.layout, run_id)
        canonical_run = read_run(self.fixture.layout, run_id)
        compiled = read_compiled_context(self.fixture.layout, run_id)
        bindings = transaction_bindings(self.fixture.layout, run_id)
        route = route_spec_by_hash(canonical_run.route_id, manifest.route_registry_hash)
        packet = WorkPacketV1(
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
        packet_hash = sha256_digest(canonical_json_bytes(packet))
        contract = compile_candidate_authoring_contract(
            self.fixture.layout,
            packet,
            packet_hash,
        )
        return contract, packet, snapshot, core, prior_bundle

    def test_audit_contract_projects_five_exact_hard_relation_templates(self) -> None:
        contract, packet, snapshot, core, _ = self._open_audit_contract()
        self.assertEqual(packet.route_registry_hash, ROUTE_REGISTRY_V7_HASH)
        self.assertEqual(packet.route_version, 7)
        self.assertEqual(
            contract.candidate_draft_semantics,
            "runtime_facet_hash_materialization_v1",
        )
        semantic_hash_schema = contract.transaction_json_schema["$defs"][
            "SemanticFacetRef"
        ]["properties"]["semantic_hash"]
        self.assertIn({"type": "null"}, semantic_hash_schema["anyOf"])
        self.assertTrue(
            any(
                "do not compute, copy, or guess" in instruction
                for instruction in contract.authoring_instructions
            )
        )
        bundle_schema = next(
            item.payload_json_schema
            for item in contract.payload_schemas
            if item.entity_type == "FramingQualityBundle"
        )
        self.assertIn(
            "distinctive_mechanism_contribution_status",
            bundle_schema["required"],
        )
        self.assertIn(
            "distinctive_mechanism",
            bundle_schema["$defs"]["BenchmarkFramingAssessment"]["required"],
        )
        self.assertIn(
            "consequence_binding",
            bundle_schema["$defs"]["ActiveMarginWitness"]["required"],
        )
        self.assertNotIn(
            "anyOf",
            bundle_schema["properties"][
                "distinctive_mechanism_contribution_status"
            ],
        )
        self.assertNotIn(
            "anyOf",
            bundle_schema["$defs"]["BenchmarkFramingAssessment"][
                "properties"
            ]["distinctive_mechanism"],
        )
        self.assertNotIn(
            "anyOf",
            bundle_schema["$defs"]["ActiveMarginWitness"]["properties"][
                "consequence_binding"
            ],
        )
        templates = contract.output_contract.required_relation_templates
        self.assertEqual(len(templates), 5)
        self.assertEqual(
            tuple(item.relation_type for item in templates),
            ("audits", "audits", "audits", "audits", "governs"),
        )
        self.assertTrue(
            all(
                item.dependency_mode == "hard"
                and item.version == 1
                and item.supersedes is None
                for item in templates
            )
        )

        source_by_type = {item.entity_type: item for item in core}
        audits = templates[:4]
        for template in audits:
            source_entity = source_by_type[template.source.entity_type]
            self.assertEqual(
                template.source.entity_ref,
                EntityVersionRef(
                    entity_id=source_entity.entity_id,
                    version=source_entity.version,
                ),
            )
            self.assertEqual(template.source.binding_kind, "exact_input")
            self.assertEqual(template.target.binding_kind, "candidate_output")
            self.assertEqual(template.target.entity_type, "FramingQualityBundle")
            self.assertEqual(template.target.output_ordinal, 1)
            self.assertEqual(
                template.target.facet,
                FRAMING_QUALITY_PAYLOAD_OWNER_FACETS["FramingQualityBundle"],
            )
            owner = THEORY_PAYLOAD_OWNER_FACETS[source_entity.entity_type]
            self.assertEqual(template.source.facet, owner)
            expected_hash = (
                authority_semantic_hash(
                    source_entity,
                    snapshot.decisions,
                    snapshot.effective_decisions,
                )
                if owner == "authority"
                else facet_semantic_hash(source_entity, owner)
            )
            self.assertEqual(
                template.upstream_semantic_hash_binding,
                "contract_value",
            )
            self.assertEqual(template.upstream_semantic_hash, expected_hash)

        governs = templates[-1]
        self.assertEqual(governs.source.binding_kind, "candidate_output")
        self.assertEqual(governs.source.entity_type, "FramingQualityBundle")
        self.assertEqual(governs.source.facet, "economic_interpretation")
        self.assertEqual(governs.target.binding_kind, "candidate_output")
        self.assertEqual(governs.target.entity_type, "GateDossier")
        self.assertEqual(governs.target.facet, "authority")
        self.assertEqual(
            governs.upstream_semantic_hash_binding,
            "runtime_facet_semantic_hash_v1",
        )
        self.assertIsNone(governs.upstream_semantic_hash)

        invariants = {
            item.invariant_id: item
            for item in contract.output_contract.model_invariants
        }
        conflict = invariants["framing.force_conflict_geometry"]
        self.assertIn("same target_node_id", conflict.requirement)
        self.assertIn("opposite", conflict.repair_hint)
        active_margin = invariants["framing.active_margin_witness"]
        self.assertIn("two feasible actions", active_margin.requirement)
        self.assertIn("purely mechanical or technological", active_margin.requirement)
        self.assertIn("cannot support ready_for_g1", active_margin.requirement)
        self.assertTrue(
            {
                "framing.choice_consequence_binding",
                "framing.distinctive_mechanism_spine",
                "framing.distinctive_mechanism_contribution_status",
            }.issubset(invariants)
        )
        self.assertTrue(
            any(
                "required_relation_template" in instruction
                for instruction in contract.authoring_instructions
            )
        )

        packet_hash = sha256_digest(canonical_json_bytes(packet))
        repeated = compile_candidate_authoring_contract(
            self.fixture.layout,
            packet,
            packet_hash,
        )
        self.assertEqual(repeated, contract)
        self.assertEqual(
            candidate_authoring_contract_hash(repeated),
            candidate_authoring_contract_hash(contract),
        )

    def test_continuation_does_not_turn_prior_bundle_into_an_audits_source(self) -> None:
        contract, _, _, core, prior_bundle = self._open_audit_contract(
            continuation=True
        )
        assert prior_bundle is not None
        templates = contract.output_contract.required_relation_templates
        exact_sources = {
            item.source.entity_ref
            for item in templates
            if item.source.binding_kind == "exact_input"
        }
        self.assertEqual(
            exact_sources,
            {
                EntityVersionRef(entity_id=item.entity_id, version=item.version)
                for item in core
            },
        )
        self.assertNotIn(
            EntityVersionRef(
                entity_id=prior_bundle.entity_id,
                version=prior_bundle.version,
            ),
            exact_sources,
        )
        governs = templates[-1]
        self.assertEqual(governs.source.binding_kind, "candidate_output")
        self.assertEqual(governs.source.entity_type, "FramingQualityBundle")

    def test_candidate_output_hash_recipe_matches_canonical_governs_validation(
        self,
    ) -> None:
        contract, packet, snapshot, core, _ = self._open_audit_contract(
            route_registry_hash=ROUTE_REGISTRY_V6_HASH
        )
        run = read_run(self.fixture.layout, packet.route_run_id)
        created_at = run.created_at
        question, benchmarks, graph, source_dossier = core
        bundle_payload = self.fixture._bundle_payload(
            question,
            benchmarks,
            graph,
            source_dossier,
        )
        bundle = self.fixture._framing_entity(
            bundle_payload,
            created_at=created_at,
        )
        replacement = self.fixture._replacement_dossier(
            source_dossier,
            bundle,
            entity_id="dossier.g1.contract.projection",
            proposed_action="ready_for_g1",
            created_at=created_at,
        )
        audit_relations = tuple(
            self.fixture._hard_relation(
                f"relation.contract.audit.{index}",
                "audits",
                source,
                bundle,
                created_at=created_at,
            )
            for index, source in enumerate(core, start=1)
        )
        governs_relation = self.fixture._hard_relation(
            "relation.contract.governs",
            "governs",
            bundle,
            replacement,
            created_at=created_at,
        )
        committed = self.fixture._commit_started(
            snapshot,
            run,
            outputs=(bundle, replacement),
            relations=(*audit_relations, governs_relation),
            evidence_refs=tuple(framing_fixture.eref(item) for item in core),
            created_at=created_at,
        )
        canonical_governs = next(
            item
            for item in committed.relation_versions
            if item.relation_id == governs_relation.relation_id
        )
        template = contract.output_contract.required_relation_templates[-1]
        self.assertEqual(
            template.upstream_semantic_hash_binding,
            "runtime_facet_semantic_hash_v1",
        )
        assert canonical_governs.upstream is not None
        self.assertEqual(canonical_governs.upstream.facet, template.source.facet)
        self.assertEqual(
            canonical_governs.upstream.semantic_hash,
            facet_semantic_hash(bundle, template.source.facet),
        )
        assert canonical_governs.downstream is not None
        self.assertEqual(canonical_governs.downstream.facet, template.target.facet)

    def test_work_packet_focus_must_equal_canonical_run_focus_at_base(self) -> None:
        _, packet, snapshot, _, _ = self._open_audit_contract()
        tampered = packet.model_copy(
            update={"focus_refs": tuple(reversed(packet.focus_refs))}
        )
        tampered_hash = sha256_digest(canonical_json_bytes(tampered))
        with self.assertRaisesRegex(ValueError, "focus refs differ"):
            compile_candidate_authoring_contract(
                self.fixture.layout,
                tampered,
                tampered_hash,
            )

    def test_projector_requires_exact_v7_semantics_and_generic_routes_are_empty(
        self,
    ) -> None:
        _, packet, snapshot, _, _ = self._open_audit_contract()
        route = route_spec_by_hash(packet.route_id, packet.route_registry_hash)
        self.assertEqual(route.route_version, 7)
        self.assertEqual(
            len(_relation_templates_for_route(route, packet, snapshot)),
            5,
        )

        wrong_exit = route.model_copy(
            update={"exit_validator_id": "framing_quality_route_exit.stale"}
        )
        with self.assertRaisesRegex(ValueError, "exact frozen or active"):
            _relation_templates_for_route(wrong_exit, packet, snapshot)

        first_requirement = route.required_output_relations[0].model_copy(
            update={"min_count": 3}
        )
        wrong_cardinality = route.model_copy(
            update={
                "required_output_relations": (
                    first_requirement,
                    *route.required_output_relations[1:],
                )
            }
        )
        with self.assertRaisesRegex(ValueError, "exact frozen or active"):
            _relation_templates_for_route(wrong_cardinality, packet, snapshot)

        generic_route = route_spec_by_hash(
            "frame.question_and_benchmarks",
            packet.route_registry_hash,
        )
        generic_packet = packet.model_copy(
            update={
                "route_id": generic_route.route_id,
                "route_version": generic_route.route_version,
            }
        )
        with patch("econ_theorist.candidate_contract.replay_at") as replay_call:
            self.assertEqual(
                _relation_templates_for_route(
                    generic_route,
                    generic_packet,
                    snapshot,
                ),
                (),
            )
        replay_call.assert_not_called()

    def test_frozen_v5_packet_projects_historical_templates_and_schema(self) -> None:
        contract, packet, snapshot, _, _ = self._open_audit_contract(
            route_registry_hash=ROUTE_REGISTRY_V5_HASH
        )
        self.assertEqual(packet.route_registry_hash, ROUTE_REGISTRY_V5_HASH)
        self.assertEqual(packet.route_version, 5)
        self.assertEqual(contract.output_contract.required_relation_templates, ())
        self.assertNotIn(
            "required_relation_templates",
            contract.output_contract.model_dump(mode="json"),
        )
        self.assertFalse(
            any(
                "required_relation_template" in instruction
                for instruction in contract.authoring_instructions
            )
        )
        invariant_ids = {
            item.invariant_id for item in contract.output_contract.model_invariants
        }
        self.assertNotIn("framing.force_conflict_geometry", invariant_ids)
        self.assertNotIn("framing.active_margin_witness", invariant_ids)
        bundle_schema = next(
            item.payload_json_schema
            for item in contract.payload_schemas
            if item.entity_type == "FramingQualityBundle"
        )
        self.assertNotIn(
            "distinctive_mechanism_contribution_status",
            bundle_schema["properties"],
        )
        self.assertNotIn(
            "distinctive_mechanism",
            bundle_schema["$defs"]["BenchmarkFramingAssessment"]["properties"],
        )
        self.assertNotIn("ActiveMarginWitness", bundle_schema["$defs"])
        self.assertNotIn(
            "active_margin_witness",
            bundle_schema["$defs"]["CausalChainStep"]["properties"],
        )

        route = route_spec_by_hash(packet.route_id, packet.route_registry_hash)
        self.assertEqual(
            _relation_templates_for_route(route, packet, snapshot),
            (),
        )
        packet_hash = sha256_digest(canonical_json_bytes(packet))
        repeated = compile_candidate_authoring_contract(
            self.fixture.layout,
            packet,
            packet_hash,
        )
        self.assertEqual(repeated, contract)

        changed_v5 = route.model_copy(
            update={"instruction_bundle_id": "audit.framing_economics.changed"}
        )
        with self.assertRaisesRegex(ValueError, "exact frozen or active"):
            _relation_templates_for_route(changed_v5, packet, snapshot)

    def test_frozen_v6_packet_retains_the_same_five_exact_templates(self) -> None:
        contract, packet, snapshot, _, _ = self._open_audit_contract(
            route_registry_hash=ROUTE_REGISTRY_V6_HASH
        )
        self.assertEqual(packet.route_registry_hash, ROUTE_REGISTRY_V6_HASH)
        self.assertEqual(packet.route_version, 6)
        self.assertEqual(
            tuple(
                item.relation_type
                for item in contract.output_contract.required_relation_templates
            ),
            ("audits", "audits", "audits", "audits", "governs"),
        )
        route = route_spec_by_hash(packet.route_id, packet.route_registry_hash)
        self.assertEqual(
            _relation_templates_for_route(route, packet, snapshot),
            contract.output_contract.required_relation_templates,
        )
        bundle_schema = next(
            item.payload_json_schema
            for item in contract.payload_schemas
            if item.entity_type == "FramingQualityBundle"
        )
        self.assertNotIn(
            "distinctive_mechanism_contribution_status",
            bundle_schema["properties"],
        )
        self.assertNotIn(
            "distinctive_mechanism",
            bundle_schema["$defs"]["BenchmarkFramingAssessment"]["properties"],
        )
        self.assertNotIn(
            "consequence_binding",
            bundle_schema["$defs"]["ActiveMarginWitness"]["properties"],
        )
        invariant_ids = {
            item.invariant_id for item in contract.output_contract.model_invariants
        }
        self.assertFalse(
            {
                "framing.choice_consequence_binding",
                "framing.distinctive_mechanism_spine",
                "framing.distinctive_mechanism_contribution_status",
            }.intersection(invariant_ids)
        )

    def test_archived_v5_public_response_parses_and_reserializes_exactly(
        self,
    ) -> None:
        archived_path = (
            REPOSITORY_ROOT
            / "review_outputs"
            / "phase5a2_v5_2_codex_public_pilot"
            / "run"
            / "011_continue_after_decompose_stdout.jsonl"
        )
        archived = archived_path.read_bytes()
        self.assertEqual(
            sha256_digest(archived),
            "6649463b50278b475234c086e507270f4955ff01c368f9a3d38434aaad9301b7",
        )
        self.assertTrue(archived.endswith(b"\n"))

        response = CodexBridgeResponseV1.model_validate_json(
            archived,
            strict=True,
        )
        assert response.candidate_authoring_contract is not None
        self.assertEqual(
            response.candidate_authoring_contract.output_contract.required_relation_templates,
            (),
        )
        reserialized = canonical_json_bytes(response)
        self.assertEqual(
            sha256_digest(reserialized),
            "66d147bfe390ed1efb5775af9366163e492c7b691912a6a268c81524a902d9ba",
        )
        self.assertEqual(reserialized, archived[:-1])

    def test_framing_projector_fails_closed_on_unknown_or_changed_semantics(
        self,
    ) -> None:
        _, packet, snapshot, _, _ = self._open_audit_contract()
        route = route_spec_by_hash(packet.route_id, packet.route_registry_hash)
        self.assertEqual(packet.route_registry_hash, ROUTE_REGISTRY_V7_HASH)

        changed_instruction = route.model_copy(
            update={"instruction_bundle_id": "audit.framing_economics.future"}
        )
        with self.assertRaisesRegex(ValueError, "exact frozen or active"):
            _relation_templates_for_route(changed_instruction, packet, snapshot)

        future_route = route.model_copy(update={"route_version": 8})
        future_packet = packet.model_copy(update={"route_version": 8})
        with self.assertRaisesRegex(ValueError, "exact frozen or active"):
            _relation_templates_for_route(future_route, future_packet, snapshot)

        unknown_packet = packet.model_copy(
            update={"route_registry_hash": "f" * 64}
        )
        with self.assertRaisesRegex(ValueError, "unknown route registry"):
            _relation_templates_for_route(route, unknown_packet, snapshot)

    def test_compiler_v2_exposes_exact_focus_evidence_binding(self) -> None:
        _, packet, _, _, _ = self._open_audit_contract()
        packet = packet.model_copy(update={"packet_compiler_version": 2})
        contract = compile_candidate_authoring_contract(
            self.fixture.layout,
            packet,
            sha256_digest(canonical_json_bytes(packet)),
        )
        self.assertEqual(
            contract.transaction_bindings.required_entity_evidence_refs,
            packet.focus_refs,
        )
        self.assertTrue(
            any(
                "Transaction.evidence_refs" in instruction
                for instruction in contract.authoring_instructions
            )
        )

    def test_decompose_endpoint_constraint_targets_primitive_graph_output(self) -> None:
        _, packet, _, _, _ = self._open_audit_contract()
        route = route_spec_by_hash("decompose.primitives", ROUTE_REGISTRY_V7_HASH)
        decompose_packet = packet.model_copy(
            update={
                "packet_compiler_version": 2,
                "route_id": "decompose.primitives",
                "route_version": route.route_version,
            }
        )
        constraints = _endpoint_constraints_for_route(route, decompose_packet)
        self.assertEqual(len(constraints), 1)
        self.assertEqual(constraints[0].relation_type, "decomposes")
        self.assertEqual(constraints[0].endpoint_role, "target")
        self.assertEqual(constraints[0].entity_type, "PrimitiveGraph")
        self.assertEqual(constraints[0].output_ordinal, 1)

    def test_decomposition_refresh_v2_exposes_trace_only_topology_hint(self) -> None:
        _, packet, snapshot, _, _ = self._open_audit_contract()
        route = route_spec_by_hash("decompose.primitives", ROUTE_REGISTRY_V7_HASH)
        decompose_packet = packet.model_copy(
            update={
                "packet_compiler_version": 2,
                "route_id": route.route_id,
                "route_version": route.route_version,
                "context_selector_version": SELECTOR_VERSION_DECOMPOSITION_REFRESH,
            }
        )
        constraints = _endpoint_constraints_for_route(route, decompose_packet)
        self.assertEqual(len(constraints), 1)
        self.assertIn(
            "exact focused ResearchQuestion as source",
            constraints[0].repair_hint,
        )
        self.assertIn("dependency_mode to trace_only", constraints[0].repair_hint)
        self.assertIn("do not compute a semantic hash", constraints[0].repair_hint)
        self.assertEqual(
            _relation_templates_for_route(route, decompose_packet, snapshot),
            (),
        )

        historical_packet = decompose_packet.model_copy(
            update={
                "context_selector_version": SELECTOR_VERSION_DECOMPOSITION_REFRESH_V1
            }
        )
        historical_constraints = _endpoint_constraints_for_route(
            route,
            historical_packet,
        )
        self.assertEqual(len(historical_constraints), 1)
        self.assertEqual(
            historical_constraints[0].repair_hint,
            (
                "At least one decomposes relation must target the new "
                "PrimitiveGraph output; if the endpoints are reversed, swap "
                "source and target."
            ),
        )



if __name__ == "__main__":
    unittest.main()
