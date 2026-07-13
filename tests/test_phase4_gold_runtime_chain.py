"""Real-store Phase 4 continuation of the complete Phase 2/3 gold case.

The test intentionally starts from the accepted Phase 3 authoring closure.  It
then exercises every native Phase 4 route through the ordinary begin, stage,
preflight, commit, replay, and freshness boundaries.  The executable harness
in the inherited case is finite corroboration, so this chain records an
approved *partial* predicate mapping and explicitly refuses to promote it to
an exact theorem certificate.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from pydantic import BaseModel

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase2_gold_runtime_chain import HUMAN, eref
from tests.test_phase3_gold_runtime_chain import (
    WRITER,
    Phase3GoldRuntimeChainTests,
    _timestamp,
)

from econ_theorist import authoring as a
from econ_theorist import profile_craft as pc
from econ_theorist import theory as t
from econ_theorist.authoring_validation import validate_authoring_ready
from econ_theorist.codec import (
    canonical_json_bytes,
    object_digest,
    sha256_digest,
)
from econ_theorist.decisions import commit_decision
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    RelationVersion,
    RouteRun,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
)
from econ_theorist.policy import ROUTE_REGISTRY_V4_HASH
from econ_theorist.profile_craft_policy import (
    load_craft_corpus,
    load_profile_catalog,
    resolve_profile_stack,
    select_craft_moves,
)
from econ_theorist.profile_craft_execution import (
    MUTATION_EXECUTOR_VERSION,
    build_mutated_predicate_bytes,
    build_mutation_replay_artifact,
    build_phrase_leak_audit,
    build_predicate_mutation_result,
    build_predicate_witness_artifact,
    predicate_fragment_hash,
    witness_assignment_bytes,
)
from econ_theorist.profile_craft_validation import validate_profile_craft_ready
from econ_theorist.runs import begin_run, read_compiled_context, transaction_bindings
from econ_theorist.runtime.freshness import (
    authority_semantic_hash,
    facet_semantic_hash as runtime_facet_semantic_hash,
)
from econ_theorist.runtime.objects import ObjectStore
from econ_theorist.runtime.replay import replay, replay_at
from econ_theorist.writer import DeterministicFixtureWriter


PREDICATE_MAPPER = Actor(kind="agent", actor_id="gold.phase4.predicate_mapper")
PREDICATE_AUDITOR = Actor(kind="agent", actor_id="gold.phase4.predicate_auditor")
MUTATION_EXECUTOR = Actor(
    kind="deterministic_tool", actor_id=MUTATION_EXECUTOR_VERSION
)
PROFILE_RESOLVER = Actor(
    kind="deterministic_tool", actor_id="gold.phase4.profile_resolver"
)
READER_DIAGNOSER = Actor(kind="agent", actor_id="gold.phase4.reader_diagnoser")
CRAFT_RETRIEVER = Actor(
    kind="deterministic_tool", actor_id="gold.phase4.craft_retriever"
)
CRAFT_ASSESSOR = Actor(kind="agent", actor_id="gold.phase4.craft_assessor")
PROFILE_CRAFT_CLOSER = Actor(
    kind="deterministic_tool", actor_id="gold.phase4.closure"
)

RESTRICTED_COMPARTMENTS = (
    "cold_reader",
    "cold_reader_evaluation",
    "project_research",
)


def _walk_artifact_refs(value: object) -> Iterable[ArtifactDependencyRef]:
    if isinstance(value, ArtifactDependencyRef):
        yield value
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from _walk_artifact_refs(getattr(value, field_name))
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _walk_artifact_refs(nested)
        return
    if isinstance(value, (tuple, list, set, frozenset)):
        for nested in value:
            yield from _walk_artifact_refs(nested)


class Phase4GoldRuntimeChainTests(Phase3GoldRuntimeChainTests):
    """Continue the inherited real Phase 3 test at its fresh closure."""

    def _begin_v3(
        self,
        *,
        route_id: str,
        actor: Actor,
        purpose: str,
        focus_refs: Iterable[EntityVersionRef],
        created_at: str,
        compartments: tuple[str, ...] = ("project_research",),
        privacy_clearance: str = "project_private",
    ) -> tuple[Snapshot, RouteRun]:
        # The inherited Phase 3 chain must remain byte-for-byte on registry.v3.
        # Once a Phase 4 payload exists, live v3 catalog writes are replay-only;
        # the unchanged v3 routes continue through their copies in registry.v4.
        if not getattr(self, "phase4_active", False):
            return super()._begin_v3(
                route_id=route_id,
                actor=actor,
                purpose=purpose,
                focus_refs=focus_refs,
                created_at=created_at,
                compartments=compartments,
                privacy_clearance=privacy_clearance,
            )
        return self._begin_v4_catalog_route(
            route_id=route_id,
            actor=actor,
            purpose=purpose,
            focus_refs=focus_refs,
            created_at=created_at,
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            expected_route_version=3,
        )

    def _begin_v4_catalog_route(
        self,
        *,
        route_id: str,
        actor: Actor,
        purpose: str,
        focus_refs: Iterable[EntityVersionRef],
        created_at: str,
        expected_route_version: int,
        compartments: tuple[str, ...] = ("project_research",),
        privacy_clearance: str = "project_private",
    ) -> tuple[Snapshot, RouteRun]:
        self.route_counter += 1
        before = replay(self.layout)
        run = begin_run(
            self.layout,
            before,
            route_id=route_id,
            actor=actor,
            purpose=purpose,
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            focus_entity_ids=tuple(
                dict.fromkeys(reference.entity_id for reference in focus_refs)
            ),
            budget_units=96_000,
            route_run_id=f"run.gold.{self.route_counter}",
            context_manifest_id=f"context.gold.{self.route_counter}",
            created_at=created_at,
            route_registry_hash=ROUTE_REGISTRY_V4_HASH,
        )
        self.assertEqual(run.route_version, expected_route_version)
        return before, run

    def _begin_phase4(
        self,
        *,
        route_id: str,
        actor: Actor,
        purpose: str,
        focus_refs: Iterable[EntityVersionRef],
        created_at: str,
        compartments: tuple[str, ...] = ("project_research",),
        privacy_clearance: str = "project_private",
    ) -> tuple[Snapshot, RouteRun]:
        return self._begin_v4_catalog_route(
            route_id=route_id,
            actor=actor,
            purpose=purpose,
            focus_refs=focus_refs,
            created_at=created_at,
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            expected_route_version=4,
        )

    def _profile_craft_entity(
        self,
        entity_id: str,
        payload: pc.ProfileCraftPayload,
        *,
        title: str,
        summary: str,
        created_at: str,
        privacy: str = "project_private",
        access_compartments: tuple[str, ...] = ("project_research",),
    ) -> EntityVersion:
        return EntityVersion(
            entity_id=entity_id,
            entity_type=type(payload).__name__,
            version=1,
            project_id=self.snapshot.project_id,
            title=title,
            summary=summary,
            status=ScientificStatus(lifecycle="proposed"),
            facets=pc.pack_profile_craft_payload(payload),
            artifact_refs=tuple(dict.fromkeys(_walk_artifact_refs(payload))),
            privacy=privacy,  # type: ignore[arg-type]
            access_compartments=access_compartments,
            created_at=created_at,
        )

    def _relation(
        self,
        snapshot: Snapshot,
        *,
        relation_id: str,
        relation_type: str,
        source: EntityVersionRef,
        target: EntityVersionRef,
        created_at: str,
        source_field: SemanticFacetRef | None = None,
        target_path: str | None = None,
        target_facet: str | None = None,
        dependency_mode: str = "hard",
        output_entities: Sequence[EntityVersion] = (),
        privacy: str = "project_private",
        access_compartments: tuple[str, ...] = ("project_research",),
    ) -> RelationVersion:
        available = (*snapshot.entity_versions, *output_entities)
        source_entity = next(item for item in available if eref(item) == source)
        target_entity = next(item for item in available if eref(item) == target)
        if dependency_mode == "trace_only":
            return RelationVersion(
                relation_id=relation_id,
                relation_type=relation_type,
                version=1,
                project_id=self.snapshot.project_id,
                source=source,
                target=target,
                dependency_mode="trace_only",
                privacy=privacy,  # type: ignore[arg-type]
                access_compartments=access_compartments,
                created_at=created_at,
            )
        if dependency_mode != "hard":
            raise ValueError("Phase 4 gold helper supports hard or trace_only edges")
        if (
            source_entity.entity_type not in pc.PROFILE_CRAFT_PAYLOAD_MODELS
            and target_entity.entity_type not in pc.PROFILE_CRAFT_PAYLOAD_MODELS
        ):
            return super()._relation(
                snapshot,
                relation_id=relation_id,
                relation_type=relation_type,
                source=source,
                target=target,
                created_at=created_at,
                source_field=source_field,
                target_path=target_path,
                target_facet=target_facet,
                output_entities=output_entities,
                privacy=privacy,
                access_compartments=access_compartments,
            )
        source_owner = (
            pc.PROFILE_CRAFT_PAYLOAD_OWNER_FACETS.get(source_entity.entity_type)
            or a.AUTHORING_PAYLOAD_OWNER_FACETS.get(source_entity.entity_type)
            or t.THEORY_PAYLOAD_OWNER_FACETS[source_entity.entity_type]
        )
        target_owner = target_facet or (
            pc.PROFILE_CRAFT_PAYLOAD_OWNER_FACETS.get(target_entity.entity_type)
            or a.AUTHORING_PAYLOAD_OWNER_FACETS.get(target_entity.entity_type)
            or t.THEORY_PAYLOAD_OWNER_FACETS[target_entity.entity_type]
        )
        source_hash = (
            authority_semantic_hash(
                source_entity, snapshot.decisions, snapshot.effective_decisions
            )
            if source_owner == "authority"
            else runtime_facet_semantic_hash(source_entity, source_owner, None)  # type: ignore[arg-type]
        )
        upstream = source_field or SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet=source_owner,  # type: ignore[arg-type]
            semantic_hash=source_hash,
        )
        return RelationVersion(
            relation_id=relation_id,
            relation_type=relation_type,
            version=1,
            project_id=self.snapshot.project_id,
            source=source,
            target=target,
            dependency_mode="hard",
            upstream=upstream,
            downstream=FacetPathRef(
                entity_id=target.entity_id,
                version=target.version,
                facet=target_owner,  # type: ignore[arg-type]
                field_path=target_path,
            ),
            privacy=privacy,  # type: ignore[arg-type]
            access_compartments=access_compartments,
            created_at=created_at,
        )

    def _current_entity(self, snapshot: Snapshot, entity_type: str) -> EntityVersion:
        values = [
            item
            for item in snapshot.entity_versions
            if item.entity_type == entity_type
            and snapshot.current_entities.get(item.entity_id) == item.version
        ]
        self.assertEqual(len(values), 1, entity_type)
        return values[0]

    def _mapping_contract(
        self,
        *,
        assurance: EntityVersion,
        claim_graph: EntityVersion,
        formal_model: EntityVersion,
        assumption_map: EntityVersion,
        obligation: EntityVersion,
        created_at: str,
    ) -> tuple[EntityVersion, a.ToolHarnessReceipt]:
        assurance_payload = a.parse_authoring_entity(assurance)
        obligation_payload = t.parse_theory_entity(obligation)
        claim_payload = t.parse_theory_entity(claim_graph)
        formal_payload = t.parse_theory_entity(formal_model)
        assumption_payload = t.parse_theory_entity(assumption_map)
        assert isinstance(assurance_payload, a.AssuranceBundle)
        assert isinstance(obligation_payload, t.ProofObligation)
        assert isinstance(claim_payload, t.ClaimGraph)
        assert isinstance(formal_payload, t.FormalModel)
        assert isinstance(assumption_payload, t.AssumptionMap)
        receipt = next(
            item
            for item in assurance_payload.tool_receipts
            if item.obligation_ref == eref(obligation)
            and item.harness_kind in {"counterexample_search", "finite_grid"}
        )
        self.assertEqual(receipt.evidentiary_role, "corroboration_only")
        self.assertEqual(receipt.outcome, "no_counterexample_found")
        scan = receipt.reproducible_evidence
        assert isinstance(scan, a.CounterexampleScanEvidence)

        focus = (
            eref(assumption_map),
            eref(assurance),
            eref(claim_graph),
            eref(formal_model),
            eref(obligation),
        )
        before, run = self._begin_phase4(
            route_id="map.obligation_predicate",
            actor=PREDICATE_MAPPER,
            purpose="research_assurance",
            focus_refs=focus,
            created_at=created_at,
        )
        contract_id = "predicate.contract.phase4.headline_reversal"
        predicate_bytes = ObjectStore(self.layout).read_bytes(
            "artifacts", receipt.input_ref.content_hash, verify=True
        )
        witness_case_id = scan.cases[0].case_id
        assignment_bytes = witness_assignment_bytes(predicate_bytes, witness_case_id)
        assignment_registration, assignment_ref, _ = self._registered_artifact(
            "artifact.phase4.predicate.assignment.domain_member",
            assignment_bytes,
            logical_name="Exact Phase 4 domain-member assignment",
            media_type="application/json",
            created_at=created_at,
        )
        witness_artifact = build_predicate_witness_artifact(
            contract_id=contract_id,
            witness_id="witness.phase4.domain_member",
            witness_kind="domain_member",
            case_id=witness_case_id,
            assignment_ref=assignment_ref,
            assignment_bytes=assignment_bytes,
            predicate_bytes=predicate_bytes,
            limitations=(
                "This executed case establishes sealed-domain membership only; it does not establish an unencoded antecedent or the universal obligation."
            ),
        )
        witness_bytes = canonical_json_bytes(witness_artifact)
        witness_registration, witness_ref, _ = self._registered_artifact(
            "artifact.phase4.predicate.witness.domain_member",
            witness_bytes,
            logical_name="Phase 4 domain-member predicate witness",
            media_type="application/json",
            created_at=created_at,
        )
        registrations: list[tuple[ArtifactRegistration, bytes]] = [
            (assignment_registration, assignment_bytes),
            (witness_registration, witness_bytes)
        ]

        clause_rows = (
            (
                "clause.obligation.domain",
                "domain",
                "narrowed",
                ("/domain",),
                "The executable scan covers registered finite assignments, not the maintained primitive domain.",
            ),
            (
                "clause.obligation.quantifier",
                "quantifier",
                "partial",
                ("/domain",),
                "A finite conjunction replaces the obligation's universal quantifier and is strictly weaker.",
            ),
            (
                "clause.obligation.assumptions",
                "assumption",
                "omitted",
                (),
                "The receipt input contains no explicit economic-assumption component, so the assumption is honestly unmapped.",
            ),
            (
                "clause.obligation.conclusion",
                "conclusion",
                "partial",
                ("/relation",),
                "The relation is checked only on the registered finite diagnostic cases.",
            ),
            (
                "clause.obligation.boundary",
                "boundary",
                "omitted",
                (),
                "The finite receipt does not encode every endpoint and tie-boundary configuration.",
            ),
        )
        mappings = tuple(
            pc.PredicateClauseMapping(
                obligation_clause_id=clause_id,
                clause_kind=kind,  # type: ignore[arg-type]
                relation=relation,  # type: ignore[arg-type]
                predicate_json_pointers=pointers,
                predicate_fragment_hash=predicate_fragment_hash(
                    predicate_bytes,
                    obligation_clause_id=clause_id,
                    relation=relation,
                    pointers=pointers,
                ),
                explanation=explanation,
            )
            for clause_id, kind, relation, pointers, explanation in clause_rows
        )
        mutations: list[pc.PredicateMutationTest] = []
        for index, mutation_kind in enumerate(
            (
                "empty_domain",
                "constant_true",
                "conclusion_flip",
                "domain_narrowing",
                "omitted_assumption",
            ),
            start=1,
        ):
            mutated_bytes = build_mutated_predicate_bytes(
                predicate_bytes, mutation_kind
            )
            mutated_registration, mutated_ref, _ = self._registered_artifact(
                f"artifact.phase4.predicate.mutant.{index}",
                mutated_bytes,
                logical_name=f"Phase 4 {mutation_kind} predicate mutant",
                media_type="application/json",
                created_at=created_at,
            )
            mutation_id = f"mutation.phase4.{mutation_kind}"
            mutation_result = build_predicate_mutation_result(
                contract_id=contract_id,
                mutation_id=mutation_id,
                mutation_kind=mutation_kind,
                predicate_bytes=predicate_bytes,
                mappings=mappings,
                mutated_predicate_ref=mutated_ref,
                mutated_predicate_bytes=mutated_bytes,
                limitations=(
                    "This fixed downgrade attack tests the executable finite mapping and cannot upgrade quantified coverage."
                ),
            )
            result_bytes = canonical_json_bytes(mutation_result)
            result_registration, result_ref, _ = self._registered_artifact(
                f"artifact.phase4.predicate.mutation_result.{index}",
                result_bytes,
                logical_name=f"Phase 4 {mutation_kind} mutation result",
                media_type="application/json",
                created_at=created_at,
            )
            registrations.extend(
                ((mutated_registration, mutated_bytes), (result_registration, result_bytes))
            )
            mutations.append(
                pc.PredicateMutationTest(
                    mutation_id=mutation_id,
                    mutation_kind=mutation_kind,  # type: ignore[arg-type]
                    mutated_predicate_ref=mutated_ref,
                    result_ref=result_ref,
                    detected=mutation_kind != "omitted_assumption",
                )
            )
        contract = pc.ObligationPredicateContract(
            contract_id=contract_id,
            assurance_bundle_ref=eref(assurance),
            assurance_bundle_hash=object_digest(assurance_payload),
            receipt_id=receipt.receipt_id,
            receipt_hash=object_digest(receipt),
            obligation_ref=eref(obligation),
            obligation_hash=object_digest(obligation_payload),
            claim_graph_ref=eref(claim_graph),
            claim_graph_hash=object_digest(claim_payload),
            formal_model_ref=eref(formal_model),
            formal_model_hash=object_digest(formal_payload),
            assumption_map_ref=eref(assumption_map),
            assumption_map_hash=object_digest(assumption_payload),
            obligation_clause_ids=tuple(item[0] for item in clause_rows),
            obligation_assumption_ids=obligation_payload.assumption_ids,
            mapped_assumption_ids=(),
            clause_mappings=mappings,
            domain_relation="narrowed",
            quantifier_relation="weakened",
            execution_scope="finite_sample",
            coverage_class="diagnostic",
            predicate_artifact_ref=receipt.input_ref,
            code_ref=receipt.code_ref,
            antecedent_satisfiable=False,
            predicate_can_return_false=False,
            witnesses=(
                pc.PredicateWitness(
                    witness_id=witness_artifact.witness_id,
                    case_id=witness_artifact.case_id,
                    witness_kind=witness_artifact.witness_kind,
                    artifact_ref=witness_ref,
                    explanation=(
                        "The exact registered assignment belongs to the sealed finite domain; the bare relation input has no separately executable antecedent."
                    ),
                ),
            ),
            mutation_tests=tuple(mutations),
            tolerance_policy="exact",
            mapper=PREDICATE_MAPPER,
            mapped_at=created_at,
            limitations=(
                "This contract is a diagnostic mapping of one finite counterexample-search receipt. It is not equivalent to, and cannot discharge, the universal proof obligation."
            ),
        )
        entity = self._profile_craft_entity(
            "predicate.contract.phase4.headline_reversal",
            contract,
            title="Bounded executable mapping of the headline obligation",
            summary=(
                "A clause-level finite diagnostic mapping with an executed domain witness and typed mutation controls, explicitly below exact coverage."
            ),
            created_at=created_at,
        )
        relations = (
            self._relation(
                before,
                relation_id="relation.phase4.obligation.maps_to.contract",
                relation_type="maps_to",
                source=eref(obligation),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
            ),
            *(
                self._relation(
                    before,
                    relation_id=f"relation.phase4.mapping.input.{index}",
                    relation_type="depends_on",
                    source=source,
                    target=eref(entity),
                    created_at=created_at,
                    output_entities=(entity,),
                )
                for index, source in enumerate(
                    (
                        eref(claim_graph),
                        eref(formal_model),
                        eref(assumption_map),
                        eref(assurance),
                    ),
                    start=1,
                )
            ),
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=relations,
            artifacts=tuple(registrations),
            evidence_refs=focus,
            created_at=created_at,
        )
        return entity, receipt

    def _audit_mapping(
        self,
        *,
        contract_entity: EntityVersion,
        assurance: EntityVersion,
        claim_graph: EntityVersion,
        formal_model: EntityVersion,
        assumption_map: EntityVersion,
        obligation: EntityVersion,
        created_at: str,
    ) -> EntityVersion:
        contract = pc.parse_profile_craft_entity(contract_entity)
        assert isinstance(contract, pc.ObligationPredicateContract)
        focus = (
            eref(assumption_map),
            eref(assurance),
            eref(claim_graph),
            eref(formal_model),
            eref(contract_entity),
            eref(obligation),
        )
        before, run = self._begin_phase4(
            route_id="audit.obligation_predicate",
            actor=PREDICATE_AUDITOR,
            purpose="research_assurance",
            focus_refs=focus,
            created_at=created_at,
        )
        bindings = transaction_bindings(self.layout, run.route_run_id)
        mutation_ids = tuple(item.mutation_id for item in contract.mutation_tests)
        predicate_bytes = ObjectStore(self.layout).read_bytes(
            "artifacts", contract.predicate_artifact_ref.content_hash, verify=True
        )

        def read_artifact(reference: ArtifactDependencyRef) -> bytes:
            return ObjectStore(self.layout).read_bytes(
                "artifacts", reference.content_hash, verify=True
            )

        audit_id = "predicate.audit.phase4.headline_reversal"
        replay_artifact = build_mutation_replay_artifact(
            audit_id=audit_id,
            contract_ref=eref(contract_entity),
            contract_hash=object_digest(contract),
            contract=contract,
            predicate_bytes=predicate_bytes,
            read_artifact=read_artifact,
            limitations=(
                "The deterministic replay checks the registered finite mapping attacks and does not certify the universal theorem."
            ),
        )
        replay_bytes = canonical_json_bytes(replay_artifact)
        replay_registration, replay_ref, _ = self._registered_artifact(
            "artifact.phase4.predicate.mutation_replay",
            replay_bytes,
            logical_name="Independent Phase 4 predicate mutation replay",
            media_type="application/json",
            created_at=created_at,
        )
        audit = pc.PredicateMappingAudit(
            audit_id=audit_id,
            contract_ref=eref(contract_entity),
            contract_hash=object_digest(contract),
            contract_coverage_class=contract.coverage_class,
            contract_mapper=contract.mapper,
            registered_mutation_ids=mutation_ids,
            auditor=PREDICATE_AUDITOR,
            mutation_executor=MUTATION_EXECUTOR,
            mutation_replay_ref=replay_ref,
            route_run_id=run.route_run_id,
            route_run_hash=bindings["route_run_hash"],
            context_manifest_hash=bindings["context_manifest_hash"],
            compiled_context_hash=bindings["compiled_context_hash"],
            replayed_mutation_ids=mutation_ids,
            mutation_replay_passed=True,
            unexecutable_mutation_ids=("mutation.phase4.omitted_assumption",),
            domain_witness_verified=True,
            antecedent_witness_verified=False,
            falsifying_witness_verified=False,
            findings=(
                pc.PredicateMappingFinding(
                    finding_id="finding.phase4.mapping.bounded",
                    severity="warning",
                    summary=(
                        "The mapping is useful finite diagnostic evidence, but its narrowed domain and weakened quantifier forbid exact approval."
                    ),
                    affected_clause_ids=(
                        "clause.obligation.domain",
                        "clause.obligation.quantifier",
                        "clause.obligation.assumptions",
                        "clause.obligation.conclusion",
                        "clause.obligation.boundary",
                    ),
                    limitation_kinds=(
                        "nonexact_clause_mapping",
                        "domain_not_equal",
                        "quantifier_not_equivalent",
                        "assumption_mapping_nonexact",
                        "bounded_execution_scope",
                        "coverage_below_exact",
                        "nonvacuity_unverified",
                        "unexecutable_control",
                    ),
                ),
            ),
            verdict="approved_partial",
            audited_at=created_at,
        )
        entity = self._profile_craft_entity(
            "predicate.audit.phase4.headline_reversal",
            audit,
            title="Independent bounded predicate-mapping audit",
            summary=(
                "The audit replays every mutant and approves only the finite diagnostic coverage actually established."
            ),
            created_at=created_at,
        )
        relation = self._relation(
            before,
            relation_id="relation.phase4.contract.validates.audit",
            relation_type="validates",
            source=eref(contract_entity),
            target=eref(entity),
            created_at=created_at,
            output_entities=(entity,),
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=(relation,),
            artifacts=((replay_registration, replay_bytes),),
            evidence_refs=focus,
            created_at=created_at,
        )
        return entity

    def _target_decisions(
        self,
        *,
        package: EntityVersion,
        paper: EntityVersion,
        reader: EntityVersion,
    ) -> tuple[Decision, ...]:
        rows = (
            (
                "decision.phase4.target.theory_mode",
                "theory_mode",
                "pure_theory",
                "Use the pure-theory profile for this Phase 4 manuscript comparison?",
            ),
            (
                "decision.phase4.target.ambition",
                "ambition",
                "frontier_general_interest",
                "Calibrate the manuscript toward a frontier general-interest contribution?",
            ),
            (
                "decision.phase4.target.field",
                "field",
                "information_economics",
                "Use information economics as the primary field profile?",
            ),
            (
                "decision.phase4.target.audience",
                "audience",
                "theory_and_field_bridge",
                "Write for readers bridging general theory and the information-economics field?",
            ),
        )
        decisions: list[Decision] = []
        for index, (decision_id, kind, selected, question) in enumerate(rows, start=27):
            decision = Decision(
                decision_id=decision_id,
                version=1,
                project_id=self.snapshot.project_id,
                decision_kind=kind,  # type: ignore[arg-type]
                # The profile calibrates the exact reader path. Binding these
                # Decisions to the package itself would legitimately change
                # the package's authority hash and stale the accepted Phase 3
                # science/authoring chain before profile resolution.
                subject_ref=reader.entity_id,
                scope_ref=paper.entity_id,
                question=question,
                options=(selected, "revise_target"),
                selected_option=selected,
                recommendation=f"Confirm the exact {selected} target dimension.",
                rationale=(
                    "The human owner fixes this Phase 4 target dimension before profile resolution and profiled prose generation."
                ),
                evidence_refs=(package.entity_id, paper.entity_id, reader.entity_id),
                unresolved_risks=(
                    "A target profile calibrates authoring and review; it does not certify publication quality or scientific truth.",
                ),
                required_authority="L2",
                decider=HUMAN,
                decided_at=_timestamp(index),
                status="confirmed",
            )
            result = commit_decision(self.layout, decision)
            self.assertEqual(result.status, "committed")
            decisions.append(decision)
        return tuple(decisions)

    def _resolve_target_profile(
        self,
        *,
        package: EntityVersion,
        assurance: EntityVersion,
        paper: EntityVersion,
        reader: EntityVersion,
        minimal_profile: EntityVersion,
        mapping_audit: EntityVersion,
        decisions: tuple[Decision, ...],
        created_at: str,
    ) -> tuple[EntityVersion, EntityVersion]:
        package_payload = t.parse_theory_entity(package)
        paper_payload = a.parse_authoring_entity(paper)
        reader_payload = a.parse_authoring_entity(reader)
        minimal_payload = a.parse_authoring_entity(minimal_profile)
        assert isinstance(package_payload, t.ValidatedArgumentPackage)
        assert isinstance(paper_payload, a.PaperIR)
        assert isinstance(reader_payload, a.ReaderPath)
        assert isinstance(minimal_payload, a.ResolvedProfileManifest)
        focus = (
            eref(assurance),
            eref(paper),
            eref(mapping_audit),
            eref(reader),
            eref(minimal_profile),
            eref(package),
        )
        before, run = self._begin_phase4(
            route_id="resolve.profile_stack",
            actor=PROFILE_RESOLVER,
            purpose="research_authoring",
            focus_refs=focus,
            created_at=created_at,
        )
        catalog = load_profile_catalog()
        decision_refs = tuple(
            DecisionVersionRef(decision_id=item.decision_id, version=item.version)
            for item in decisions
        )
        target = pc.TargetProfile(
            target_profile_id="target.phase4.attention_precision",
            package_ref=eref(package),
            package_hash=object_digest(package_payload),
            paper_ir_ref=eref(paper),
            paper_ir_hash=object_digest(paper_payload),
            reader_path_ref=eref(reader),
            reader_path_hash=object_digest(reader_payload),
            base_profile_manifest_ref=eref(minimal_profile),
            base_profile_manifest_hash=object_digest(minimal_payload),
            source_state_revision=before.head,
            catalog_release_ref=pc.static_resource_ref(catalog),
            theory_mode="pure_theory",
            ambition="frontier_general_interest",
            primary_archetype=minimal_payload.primary_result_archetype,
            field_key="information_economics",
            primary_audience="theory_and_field_bridge",
            human_decision_refs=decision_refs,
            selected_by=HUMAN,
            selected_at=created_at,
        )
        target_entity = self._profile_craft_entity(
            "target.profile.phase4.attention_precision",
            target,
            title="Human-confirmed Phase 4 theory target",
            summary=(
                "A pure-theory frontier target for a theory-and-field bridge audience, without a venue voice or content overlay."
            ),
            created_at=created_at,
        )
        stack = resolve_profile_stack(
            target,
            target_profile_ref=eref(target_entity),
            source_state_revision=before.head,
            resolved_by=PROFILE_RESOLVER,
            resolved_at=created_at,
            catalog=catalog,
        )
        stack_entity = self._profile_craft_entity(
            "profile.stack.phase4.attention_precision",
            stack,
            title="Deterministically resolved Phase 4 profile stack",
            summary=(
                "The universal floor, theory mode, ambition, archetype, field, and audience layers resolve with explicit precedence."
            ),
            created_at=created_at,
        )
        outputs = (target_entity, stack_entity)
        relations = [
            self._relation(
                before,
                relation_id="relation.phase4.package.depends.target",
                relation_type="depends_on",
                source=eref(package),
                target=eref(target_entity),
                created_at=created_at,
                output_entities=outputs,
            ),
            self._relation(
                before,
                relation_id="relation.phase4.paper.depends.target",
                relation_type="depends_on",
                source=eref(paper),
                target=eref(target_entity),
                created_at=created_at,
                output_entities=outputs,
            ),
            self._relation(
                before,
                relation_id="relation.phase4.reader.depends.target",
                relation_type="depends_on",
                source=eref(reader),
                target=eref(target_entity),
                created_at=created_at,
                output_entities=outputs,
            ),
            self._relation(
                before,
                relation_id="relation.phase4.base_profile.depends.target",
                relation_type="depends_on",
                source=eref(minimal_profile),
                target=eref(target_entity),
                created_at=created_at,
                output_entities=outputs,
            ),
            self._relation(
                before,
                relation_id="relation.phase4.target.governs.stack",
                relation_type="governs",
                source=eref(target_entity),
                target=eref(stack_entity),
                created_at=created_at,
                output_entities=outputs,
            ),
        ]
        for index, source in enumerate(
            (
                eref(mapping_audit),
                eref(assurance),
                eref(paper),
                eref(reader),
                eref(minimal_profile),
            ),
            start=1,
        ):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase4.stack.input.{index}",
                    relation_type="depends_on",
                    source=source,
                    target=eref(stack_entity),
                    created_at=created_at,
                    output_entities=outputs,
                )
            )
        self._commit_started_v3(
            before,
            run,
            outputs=outputs,
            relations=tuple(relations),
            evidence_refs=(*focus, *decision_refs),
            authority_basis=tuple(item.decision_id for item in decision_refs),
            created_at=created_at,
        )
        return target_entity, stack_entity

    def _diagnose_target_reader_problem(
        self,
        *,
        paper: EntityVersion,
        reader: EntityVersion,
        contracts: EntityVersion,
        stack: EntityVersion,
        base_unit: EntityVersion,
        diagnostic_reviews: tuple[EntityVersion, ...],
        diagnostic_findings: tuple[EntityVersion, ...],
        blocked_closure: EntityVersion,
        revision_brief: EntityVersion,
        created_at: str,
    ) -> EntityVersion:
        paper_payload = a.parse_authoring_entity(paper)
        reader_payload = a.parse_authoring_entity(reader)
        unit_payload = a.parse_authoring_entity(base_unit)
        contracts_payload = a.parse_authoring_entity(contracts)
        stack_payload = pc.parse_profile_craft_entity(stack)
        closure_payload = a.parse_authoring_entity(blocked_closure)
        brief_payload = a.parse_authoring_entity(revision_brief)
        assert isinstance(paper_payload, a.PaperIR)
        assert isinstance(reader_payload, a.ReaderPath)
        assert isinstance(unit_payload, a.ManuscriptUnit)
        assert isinstance(contracts_payload, a.ResultContractSet)
        assert isinstance(stack_payload, pc.ResolvedProfileStack)
        assert isinstance(closure_payload, a.ReviewClosure)
        assert isinstance(brief_payload, a.RevisionBrief)
        self.assertEqual(closure_payload.status, "blocked")
        self.assertEqual(closure_payload.manuscript_unit_ref, eref(base_unit))
        self.assertEqual(closure_payload.revision_brief_ref, eref(revision_brief))
        self.assertEqual(brief_payload.review_closure_ref, eref(blocked_closure))
        self.assertEqual(brief_payload.manuscript_unit_ref, eref(base_unit))
        review_payloads = tuple(
            a.parse_authoring_entity(item) for item in diagnostic_reviews
        )
        finding_payloads = tuple(
            a.parse_authoring_entity(item) for item in diagnostic_findings
        )
        self.assertTrue(
            all(isinstance(item, a.ReviewRecord) for item in review_payloads)
        )
        self.assertTrue(
            all(isinstance(item, a.ReviewFinding) for item in finding_payloads)
        )
        focus = (
            eref(base_unit),
            eref(paper),
            eref(reader),
            eref(stack),
            eref(contracts),
            *(eref(item) for item in diagnostic_reviews),
            *(eref(item) for item in diagnostic_findings),
            eref(blocked_closure),
            eref(revision_brief),
        )
        before, run = self._begin_phase4(
            route_id="diagnose.reader_problem",
            actor=READER_DIAGNOSER,
            purpose="research_authoring",
            focus_refs=focus,
            created_at=created_at,
            compartments=RESTRICTED_COMPARTMENTS,
            privacy_clearance="restricted",
        )
        move = load_craft_corpus().moves[0]
        section = next(
            item
            for item in reader_payload.section_contracts
            if item.section_id == unit_payload.section_contract_id
        )
        finding_by_ref = {
            eref(entity): payload
            for entity, payload in zip(diagnostic_findings, finding_payloads)
            if isinstance(payload, a.ReviewFinding)
        }
        requirements = tuple(
            pc.ResolutionRequirement(
                requirement_id=instruction.instruction_id,
                finding_ref=instruction.finding_ref,
                action=instruction.action,
                instruction_source=self._facet_ref(
                    before,
                    eref(revision_brief),
                    facet="authority",
                    field_path=f"/payload/instructions/{index}",
                ),
                affected_assertion_ids=finding_by_ref[
                    instruction.finding_ref
                ].assertion_ids,
                affected_section_ids=(unit_payload.section_contract_id,),
                required_semantic_input_ids=move.required_semantic_inputs,
            )
            for index, instruction in enumerate(brief_payload.instructions)
            if instruction.blocking
        )
        semantic_bindings = (
            pc.SemanticInputBinding(
                input_id="semantic_input.natural_benchmark",
                source_ref=self._facet_ref(
                    before,
                    eref(paper),
                    facet="terminology_presentation",
                    field_path="/payload/narrative_spine/natural_benchmark",
                ),
                source_kind="paper_ir",
                availability="available",
                explanation=(
                    "The exact current PaperIR fixes the natural conditional-information benchmark."
                ),
            ),
            pc.SemanticInputBinding(
                input_id="semantic_input.operative_force",
                source_ref=self._facet_ref(
                    before,
                    eref(contracts),
                    facet="terminology_presentation",
                    field_path=(
                        "/payload/result_packets/0/archetype_module/competing_effects/content"
                    ),
                ),
                source_kind="result_contract",
                availability="available",
                explanation=(
                    "The exact ResultPacket states the competing conditional-value and precision-linked-cost forces."
                ),
            ),
            pc.SemanticInputBinding(
                input_id="semantic_input.affected_margin",
                source_ref=self._facet_ref(
                    before,
                    eref(contracts),
                    facet="terminology_presentation",
                    field_path=(
                        "/payload/result_packets/0/archetype_module/threshold_or_regime_logic/content"
                    ),
                ),
                source_kind="result_contract",
                availability="available",
                explanation=(
                    "The exact archetype contract identifies the threshold governing the extensive information-use margin."
                ),
            ),
            pc.SemanticInputBinding(
                input_id="semantic_input.boundary",
                source_ref=self._facet_ref(
                    before,
                    eref(contracts),
                    facet="terminology_presentation",
                    field_path="/payload/result_packets/0/boundary/content",
                ),
                source_kind="result_contract",
                availability="available",
                explanation=(
                    "The exact ResultPacket records the tie and common-cost failure boundary."
                ),
            ),
        )
        self.assertEqual(
            tuple(item.input_id for item in semantic_bindings),
            move.required_semantic_inputs,
        )
        diagnosis = pc.ReaderProblemDiagnosis(
            diagnosis_id="diagnosis.phase4.opaque_benchmark",
            paper_ir_ref=eref(paper),
            paper_ir_hash=object_digest(paper_payload),
            reader_path_ref=eref(reader),
            reader_path_hash=object_digest(reader_payload),
            profile_stack_ref=eref(stack),
            profile_stack_hash=object_digest(stack_payload),
            result_contract_set_binding=pc.ProjectPayloadBinding(
                entity_ref=eref(contracts),
                payload_hash=object_digest(contracts_payload),
            ),
            inspected_manuscript_unit_binding=pc.ProjectPayloadBinding(
                entity_ref=eref(base_unit), payload_hash=object_digest(unit_payload)
            ),
            diagnostic_review_bindings=tuple(
                pc.ProjectPayloadBinding(
                    entity_ref=eref(entity), payload_hash=object_digest(payload)
                )
                for entity, payload in zip(diagnostic_reviews, review_payloads)
            ),
            diagnostic_finding_bindings=tuple(
                pc.ProjectPayloadBinding(
                    entity_ref=eref(entity), payload_hash=object_digest(payload)
                )
                for entity, payload in zip(diagnostic_findings, finding_payloads)
            ),
            blocked_review_closure_binding=pc.ProjectPayloadBinding(
                entity_ref=eref(blocked_closure),
                payload_hash=object_digest(closure_payload),
            ),
            revision_brief_binding=pc.ProjectPayloadBinding(
                entity_ref=eref(revision_brief),
                payload_hash=object_digest(brief_payload),
            ),
            diagnostic_categories=tuple(
                dict.fromkeys(
                    item.category
                    for item in finding_payloads
                    if isinstance(item, a.ReviewFinding) and item.blocking
                )
            ),
            affected_section_roles=(section.role,),
            causal_class="local_exposition",
            resolution_requirements=requirements,
            semantic_input_bindings=semantic_bindings,
            affected_section_ids=(unit_payload.section_contract_id,),
            reader_problem_key=move.reader_problem_key,
            required_resolution_ids=tuple(
                item.requirement_id for item in requirements
            ),
            observed_problem=(
                "A fresh target-audience economic-reader review of the exact Phase 3 unit fails the boundary explanation: the fixed-use benchmark and endogenous-uptake force remain dispersed, so the bridge reader cannot reconstruct why the common-cost boundary kills the reversal."
            ),
            required_semantic_input_ids=tuple(
                item.input_id for item in semantic_bindings
            ),
            upstream_science_status="resolved",
            craft_eligible=True,
            upstream_repair_route=None,
            evidence_refs=(
                eref(paper),
                eref(reader),
                eref(stack),
                eref(contracts),
                eref(base_unit),
                *(eref(item) for item in diagnostic_reviews),
                *(eref(item) for item in diagnostic_findings),
                eref(blocked_closure),
                eref(revision_brief),
            ),
            diagnosed_by=READER_DIAGNOSER,
            diagnosed_at=created_at,
        )
        entity = self._profile_craft_entity(
            "diagnosis.phase4.opaque_benchmark",
            diagnosis,
            title="Target-specific reader-problem diagnosis",
            summary=(
                "The science is resolved; the remaining problem is the inference burden of reconstructing benchmark, force, margin, and boundary."
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        relations = [
            self._relation(
                before,
                relation_id="relation.phase4.paper.diagnoses.reader_problem",
                relation_type="diagnoses",
                source=eref(paper),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=RESTRICTED_COMPARTMENTS,
            )
        ]
        diagnosis_inputs = (
            (eref(reader), "hard"),
            (eref(stack), "hard"),
            (eref(contracts), "hard"),
            (eref(base_unit), "trace_only"),
            *((eref(item), "trace_only") for item in diagnostic_reviews),
            *((eref(item), "trace_only") for item in diagnostic_findings),
            (eref(blocked_closure), "trace_only"),
            (eref(revision_brief), "trace_only"),
        )
        for index, (source, dependency_mode) in enumerate(
            diagnosis_inputs, start=1
        ):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase4.diagnosis.input.{index}",
                    relation_type="depends_on",
                    source=source,
                    target=eref(entity),
                    dependency_mode=dependency_mode,
                    created_at=created_at,
                    output_entities=(entity,),
                    privacy="restricted",
                    access_compartments=RESTRICTED_COMPARTMENTS,
                )
            )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=tuple(relations),
            evidence_refs=focus,
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        return entity

    def _retrieve_craft_move(
        self,
        *,
        paper: EntityVersion,
        reader: EntityVersion,
        contracts: EntityVersion,
        stack: EntityVersion,
        diagnosis: EntityVersion,
        created_at: str,
    ) -> EntityVersion:
        stack_payload = pc.parse_profile_craft_entity(stack)
        diagnosis_payload = pc.parse_profile_craft_entity(diagnosis)
        assert isinstance(stack_payload, pc.ResolvedProfileStack)
        assert isinstance(diagnosis_payload, pc.ReaderProblemDiagnosis)
        focus = (eref(paper), eref(reader), eref(diagnosis), eref(stack), eref(contracts))
        before, run = self._begin_phase4(
            route_id="retrieve.craft_moves",
            actor=CRAFT_RETRIEVER,
            purpose="research_authoring",
            focus_refs=focus,
            created_at=created_at,
            compartments=RESTRICTED_COMPARTMENTS,
            privacy_clearance="restricted",
        )
        selection = select_craft_moves(
            diagnosis_payload,
            diagnosis_ref=eref(diagnosis),
            profile_stack=stack_payload,
            profile_stack_ref=eref(stack),
            selected_by=CRAFT_RETRIEVER,
            selected_at=created_at,
        )
        self.assertEqual(selection.outcome, "selected")
        self.assertEqual(len(selection.selected_move_refs), 1)
        entity = self._profile_craft_entity(
            "craft.selection.phase4.opaque_benchmark",
            selection,
            title="Function-first matched-and-contrast craft selection",
            summary=(
                "The deterministic selector chooses the inclusion-minimal benchmark-before-mechanism move from a theory-only corpus."
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        relations = [
            self._relation(
                before,
                relation_id="relation.phase4.diagnosis.selects_for.craft",
                relation_type="selects_for",
                source=eref(diagnosis),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=RESTRICTED_COMPARTMENTS,
            )
        ]
        for index, source in enumerate(
            (eref(stack), eref(paper), eref(reader), eref(contracts)), start=1
        ):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase4.selection.input.{index}",
                    relation_type="depends_on",
                    source=source,
                    target=eref(entity),
                    created_at=created_at,
                    output_entities=(entity,),
                    privacy="restricted",
                    access_compartments=RESTRICTED_COMPARTMENTS,
                )
            )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=tuple(relations),
            evidence_refs=focus,
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        return entity

    def _compose_profiled_unit(
        self,
        *,
        package: EntityVersion,
        assurance: EntityVersion,
        minimal_profile: EntityVersion,
        paper: EntityVersion,
        reader: EntityVersion,
        contracts: EntityVersion,
        stack: EntityVersion,
        diagnosis: EntityVersion,
        selection: EntityVersion,
        base_unit: EntityVersion,
        blocked_closure: EntityVersion,
        revision_brief: EntityVersion,
        decisions: tuple[Decision, ...],
        created_at: str,
    ) -> tuple[EntityVersion, str, Mapping[str, object]]:
        paper_payload = a.parse_authoring_entity(paper)
        contracts_payload = a.parse_authoring_entity(contracts)
        base_payload = a.parse_authoring_entity(base_unit)
        blocked_payload = a.parse_authoring_entity(blocked_closure)
        brief_payload = a.parse_authoring_entity(revision_brief)
        diagnosis_payload = pc.parse_profile_craft_entity(diagnosis)
        assert isinstance(paper_payload, a.PaperIR)
        assert isinstance(contracts_payload, a.ResultContractSet)
        assert isinstance(base_payload, a.ManuscriptUnit)
        assert isinstance(blocked_payload, a.ReviewClosure)
        assert isinstance(brief_payload, a.RevisionBrief)
        assert isinstance(diagnosis_payload, pc.ReaderProblemDiagnosis)
        self.assertEqual(blocked_payload.status, "blocked")
        self.assertEqual(blocked_payload.manuscript_unit_ref, eref(base_unit))
        self.assertEqual(brief_payload.manuscript_unit_ref, eref(base_unit))
        base_text = ObjectStore(self.layout).read_bytes(
            "artifacts", base_payload.manuscript_artifact_ref.content_hash, verify=True
        ).decode("utf-8")
        benchmark_text = (
            "Start with the fixed-use benchmark. If the receiver were forced to process either signal, greater precision would improve accuracy. The new force is endogenous uptake: processing is indivisible and its cost rises with precision, so precision can move the receiver across the use threshold. When the precise signal is rejected while the coarse signal is used, realized accuracy reverses; if the cost difference is removed, that gap closes."
        )
        separator = "\n\n"
        text = benchmark_text + separator + base_text
        focus = (
            eref(assurance),
            eref(selection),
            eref(paper),
            eref(reader),
            eref(diagnosis),
            eref(minimal_profile),
            eref(stack),
            eref(contracts),
            eref(package),
            eref(base_unit),
            eref(blocked_closure),
            eref(revision_brief),
        )
        before, run = self._begin_phase4(
            route_id="compose.profiled_manuscript_unit",
            actor=WRITER,
            purpose="research_authoring",
            focus_refs=focus,
            created_at=created_at,
            compartments=RESTRICTED_COMPARTMENTS,
            privacy_clearance="restricted",
        )
        packet = read_compiled_context(self.layout, run.route_run_id)[
            "phase4_role_packet"
        ]
        self.assertEqual(packet["packet_kind"], "profiled_canonical_writer")
        packet_bytes = canonical_json_bytes(packet)
        self.assertNotIn(b"craft.source.", packet_bytes)
        self.assertNotIn(b"matched_anchor", packet_bytes)
        writer = DeterministicFixtureWriter(
            actor=WRITER, fixtures={"profiled_main_result": text}
        )
        output = writer.compose(packet, manuscript_key="profiled_main_result")
        registration, manuscript_ref, _ = self._registered_artifact(
            "artifact.phase4.manuscript.profiled_main_result",
            output.data,
            logical_name="Phase 4 profiled main-result manuscript",
            media_type="text/plain; charset=utf-8",
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        projection = paper_payload.claim_projections[0]
        prefix_span = a.ConsequentialSpan(
            assertion_id="assertion.phase4.benchmark_delta",
            role="mechanism_or_conceptual_explanation",
            claim_projection_id=projection.projection_id,
            claim_graph_ref=projection.claim_graph_ref,
            claim_id=projection.claim_id,
            source_fields=(
                projection.translation_source,
                projection.scope_source,
            ),
            scope=projection.scope,
            assumption_ids=projection.assumption_ids,
            support_refs=(
                contracts_payload.economic_argument_graph_ref,
                contracts_payload.example_suite_ref,
            ),
            location=a.ManuscriptLocation(
                start_offset=0, end_offset=len(benchmark_text)
            ),
            text_hash=sha256_digest(benchmark_text.encode("utf-8")),
            wording_strength="entailed_weaker",
            presentation="mechanism_explanation",
        )
        shift = len(benchmark_text) + len(separator)
        shifted_spans = tuple(
            span.model_copy(
                update={
                    "location": a.ManuscriptLocation(
                        start_offset=span.location.start_offset + shift,
                        end_offset=span.location.end_offset + shift,
                    )
                }
            )
            for span in base_payload.spans
        )
        payload = a.ManuscriptUnit(
            unit_id=base_payload.unit_id,
            paper_ir_ref=eref(paper),
            reader_path_ref=eref(reader),
            result_contract_set_ref=eref(contracts),
            section_contract_id=base_payload.section_contract_id,
            manuscript_artifact_ref=manuscript_ref,
            source_state_revision=before.head,
            canonical_writer=output.writer,
            writer_role_packet_hash=output.role_packet_hash,
            writer_output_hash=output.content_hash,
            integration_generation=base_payload.integration_generation + 1,
            previous_manuscript_unit_ref=eref(base_unit),
            previous_manuscript_artifact_ref=base_payload.manuscript_artifact_ref,
            revision_brief_ref=eref(revision_brief),
            spans=(prefix_span, *shifted_spans),
            terminology=base_payload.terminology,
            composed_at=created_at,
        )
        entity = self._authoring_entity(
            base_unit.entity_id,
            payload,
            title="Profiled theory manuscript revision",
            summary=(
                "The next exact integration generation exposes the natural benchmark before the operative uptake mechanism."
            ),
            created_at=created_at,
            artifact_refs=(
                manuscript_ref,
                base_payload.manuscript_artifact_ref,
            ),
            version=base_unit.version + 1,
            supersedes=eref(base_unit),
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        relations = [
            self._relation(
                before,
                relation_id="relation.phase4.stack.governs.manuscript",
                relation_type="governs",
                source=eref(stack),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=RESTRICTED_COMPARTMENTS,
            ),
            self._relation(
                before,
                relation_id="relation.phase4.selection.realizes.manuscript",
                relation_type="realizes",
                source=eref(selection),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=RESTRICTED_COMPARTMENTS,
            ),
            self._relation(
                before,
                relation_id="relation.phase4.diagnosis.depends.manuscript",
                relation_type="depends_on",
                source=eref(diagnosis),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=RESTRICTED_COMPARTMENTS,
            ),
        ]
        manuscript_inputs = (
            (eref(paper), "hard"),
            (eref(reader), "hard"),
            (eref(contracts), "hard"),
            (eref(package), "hard"),
            (eref(assurance), "hard"),
            (eref(minimal_profile), "hard"),
            (eref(base_unit), "trace_only"),
            (eref(blocked_closure), "trace_only"),
            (eref(revision_brief), "trace_only"),
        )
        for index, (source, dependency_mode) in enumerate(
            manuscript_inputs, start=1
        ):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase4.manuscript.input.{index}",
                    relation_type="depends_on",
                    source=source,
                    target=eref(entity),
                    dependency_mode=dependency_mode,
                    created_at=created_at,
                    output_entities=(entity,),
                    privacy="restricted",
                    access_compartments=RESTRICTED_COMPARTMENTS,
                )
            )
        for span_index, span in enumerate(payload.spans):
            for source_index, source_field in enumerate(span.source_fields):
                relations.append(
                    self._relation(
                        before,
                        relation_id=(
                            f"relation.phase4.manuscript.span.{span_index}.{source_index}"
                        ),
                        relation_type="realizes",
                        source=EntityVersionRef(
                            entity_id=source_field.entity_id,
                            version=source_field.version,
                        ),
                        target=eref(entity),
                        source_field=source_field,
                        target_path=f"/payload/spans/{span_index}",
                        target_facet="terminology_presentation",
                        created_at=created_at,
                        output_entities=(entity,),
                        privacy="restricted",
                        access_compartments=RESTRICTED_COMPARTMENTS,
                    )
                )
        decision_refs = tuple(
            DecisionVersionRef(decision_id=item.decision_id, version=item.version)
            for item in decisions
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=tuple(relations),
            artifacts=((registration, output.data),),
            evidence_refs=(*focus, *decision_refs),
            authority_basis=tuple(item.decision_id for item in decision_refs),
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        return entity, text, packet

    def _review_craft_realization(
        self,
        *,
        paper: EntityVersion,
        reader: EntityVersion,
        contracts: EntityVersion,
        stack: EntityVersion,
        diagnosis: EntityVersion,
        selection: EntityVersion,
        unit: EntityVersion,
        base_closure: EntityVersion,
        formal_review: EntityVersion,
        economic_review: EntityVersion,
        cold_review: EntityVersion,
        created_at: str,
    ) -> EntityVersion:
        selection_payload = pc.parse_profile_craft_entity(selection)
        stack_payload = pc.parse_profile_craft_entity(stack)
        diagnosis_payload = pc.parse_profile_craft_entity(diagnosis)
        reader_payload = a.parse_authoring_entity(reader)
        contracts_payload = a.parse_authoring_entity(contracts)
        unit_payload = a.parse_authoring_entity(unit)
        base_payload = a.parse_authoring_entity(base_closure)
        formal_payload = a.parse_authoring_entity(formal_review)
        economic_payload = a.parse_authoring_entity(economic_review)
        cold_payload = a.parse_authoring_entity(cold_review)
        assert isinstance(selection_payload, pc.CraftSelectionManifest)
        assert isinstance(stack_payload, pc.ResolvedProfileStack)
        assert isinstance(diagnosis_payload, pc.ReaderProblemDiagnosis)
        assert isinstance(reader_payload, a.ReaderPath)
        assert isinstance(contracts_payload, a.ResultContractSet)
        assert isinstance(unit_payload, a.ManuscriptUnit)
        assert isinstance(base_payload, a.ReviewClosure)
        assert isinstance(formal_payload, a.ReviewRecord)
        assert isinstance(economic_payload, a.ReviewRecord)
        assert isinstance(cold_payload, a.ReviewRecord)
        focus = (
            eref(selection),
            eref(unit),
            eref(paper),
            eref(diagnosis),
            eref(stack),
            eref(reader),
            eref(contracts),
            eref(base_closure),
            eref(formal_review),
            eref(economic_review),
            eref(cold_review),
        )
        before, run = self._begin_phase4(
            route_id="review.craft_realization",
            actor=CRAFT_ASSESSOR,
            purpose="research_review",
            focus_refs=focus,
            created_at=created_at,
            compartments=RESTRICTED_COMPARTMENTS,
            privacy_clearance="restricted",
        )
        assessment_id = "craft.assessment.phase4.profiled_main_result"
        manuscript_bytes = ObjectStore(self.layout).read_bytes(
            "artifacts", unit_payload.manuscript_artifact_ref.content_hash, verify=True
        )
        phrase_audit = build_phrase_leak_audit(
            assessment_id=assessment_id,
            manuscript_artifact_ref=unit_payload.manuscript_artifact_ref,
            manuscript_bytes=manuscript_bytes,
            selected_move_refs=selection_payload.selected_move_refs,
            normalized_ngram_size=8,
        )
        self.assertEqual(phrase_audit.outcome, "pass")
        phrase_bytes = canonical_json_bytes(phrase_audit)
        registration, phrase_ref, _ = self._registered_artifact(
            "artifact.phase4.craft.phrase_audit",
            phrase_bytes,
            logical_name="Phase 4 profiled-manuscript phrase-leak audit",
            media_type="application/json",
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        assessment_evidence = (
            eref(selection),
            eref(diagnosis),
            eref(stack),
            eref(unit),
            unit_payload.manuscript_artifact_ref,
            eref(base_closure),
            eref(formal_review),
            eref(economic_review),
            eref(cold_review),
            eref(reader),
            eref(contracts),
        )
        move_realizations = tuple(
            pc.CraftMoveRealization(
                move_ref=candidate.move_ref,
                realized_assertion_ids=tuple(
                    dict.fromkeys(
                        (
                            *(
                                assertion_id
                                for requirement in diagnosis_payload.resolution_requirements
                                for assertion_id in requirement.affected_assertion_ids
                            ),
                            "assertion.phase4.benchmark_delta",
                        )
                    )
                ),
                realized_semantic_input_ids=candidate.move.required_semantic_inputs,
                realized_semantic_source_refs=tuple(
                    binding.source_ref
                    for input_id in candidate.move.required_semantic_inputs
                    for binding in diagnosis_payload.semantic_input_bindings
                    if binding.input_id == input_id
                    and binding.source_ref is not None
                ),
                realized_function=True,
                intended_reader_update_delivered=True,
                formal_fidelity_preserved=True,
                evidence_refs=assessment_evidence,
                explanation=(
                    "The exact opening span states the fixed-use benchmark, introduces endogenous uptake as the operative force, identifies the participation margin, and names the failure boundary before the general result block."
                ),
            )
            for candidate in selection_payload.candidates
            if candidate.selected
        )
        active_directives = tuple(
            resolution.directive
            for resolution in stack_payload.directive_resolutions
            if resolution.outcome == "active"
            and resolution.directive.strength != "soft"
        )
        self.assertEqual(
            tuple(item.directive_id for item in active_directives),
            stack_payload.active_requirements,
        )
        realized_roles = tuple(
            dict.fromkeys(span.role for span in unit_payload.spans)
        )
        observed_review_signals = tuple(
            signal
            for signal, passed in (
                (
                    "formal_fidelity",
                    formal_payload.assessment.theorem_statement_exact
                    and formal_payload.assessment.scope_preserved
                    and formal_payload.assessment.assumptions_preserved
                    and formal_payload.assessment.proof_language_honest
                    and formal_payload.assessment.numerical_evidence_bounded,
                ),
                (
                    "scope_and_assumptions",
                    formal_payload.assessment.scope_preserved
                    and formal_payload.assessment.assumptions_preserved,
                ),
                (
                    "bounded_evidentiary_language",
                    formal_payload.assessment.proof_language_honest
                    and formal_payload.assessment.numerical_evidence_bounded,
                ),
                (
                    "economic_explanation",
                    economic_payload.assessment.question_and_benchmark_reconstructible
                    and economic_payload.assessment.explanation_is_not_restatement
                    and economic_payload.assessment.mechanism_or_conceptual_logic_reconstructible
                    and economic_payload.assessment.diagnostic_example_or_witness_present
                    and economic_payload.assessment.boundary_is_economically_interpretable,
                ),
                (
                    "cold_reader_transfer",
                    cold_payload.assessment.question_and_benchmark_retell_passed
                    and cold_payload.assessment.exact_scope_recovery_passed
                    and cold_payload.assessment.assumption_role_recovery_passed
                    and cold_payload.assessment.boundary_discrimination_passed
                    and cold_payload.assessment.near_transfer_passed,
                ),
            )
            if passed
        )
        directive_checks = tuple(
            pc.DirectiveAcceptanceCheck(
                directive_id=directive.directive_id,
                criterion_id=directive.acceptance_criterion.criterion_id,
                required_assertion_roles=(
                    directive.acceptance_criterion.required_assertion_roles
                ),
                realized_assertion_roles=realized_roles,
                required_review_signals=(
                    directive.acceptance_criterion.required_review_signals
                ),
                observed_review_signals=observed_review_signals,
                outcome="pass",
                evidence_refs=assessment_evidence,
                explanation=(
                    "The exact manuscript spans and independent review signals jointly satisfy this active profile directive's observable acceptance criterion."
                ),
            )
            for directive in active_directives
        )
        realization_by_move = {
            item.move_ref: item for item in move_realizations
        }
        resolution_checks = tuple(
            pc.ResolutionRequirementCheck(
                requirement_id=requirement.requirement_id,
                repair_action=requirement.action,
                realizing_move_refs=tuple(
                    candidate.move_ref
                    for candidate in selection_payload.candidates
                    if candidate.selected
                    and requirement.requirement_id
                    in candidate.covered_requirement_ids
                ),
                affected_assertion_ids=requirement.affected_assertion_ids,
                affected_section_ids=requirement.affected_section_ids,
                required_semantic_input_ids=(
                    requirement.required_semantic_input_ids
                ),
                realized_semantic_input_ids=tuple(
                    dict.fromkeys(
                        input_id
                        for candidate in selection_payload.candidates
                        if candidate.selected
                        and requirement.requirement_id
                        in candidate.covered_requirement_ids
                        for input_id in realization_by_move[
                            candidate.move_ref
                        ].realized_semantic_input_ids
                    )
                ),
                outcome="pass",
                evidence_refs=assessment_evidence,
                explanation=(
                    "The selected function-first move realizes every semantic input required by this exact blocking RevisionBrief instruction."
                ),
            )
            for requirement in diagnosis_payload.resolution_requirements
        )
        primary_audience = next(
            item.selection_key
            for item in stack_payload.selected_layers
            if item.layer_kind == "audience"
        )
        assessment = pc.CraftRealizationAssessment(
            assessment_id=assessment_id,
            selection_manifest_ref=eref(selection),
            selection_manifest_hash=object_digest(selection_payload),
            profile_stack_ref=eref(stack),
            profile_stack_hash=object_digest(stack_payload),
            reader_problem_diagnosis_ref=eref(diagnosis),
            reader_problem_diagnosis_hash=object_digest(diagnosis_payload),
            reader_path_ref=eref(reader),
            reader_path_hash=object_digest(reader_payload),
            result_contract_set_ref=eref(contracts),
            result_contract_set_hash=object_digest(contracts_payload),
            primary_audience=primary_audience,  # type: ignore[arg-type]
            selected_move_refs=selection_payload.selected_move_refs,
            manuscript_unit_ref=eref(unit),
            manuscript_unit_hash=object_digest(unit_payload),
            manuscript_artifact_ref=unit_payload.manuscript_artifact_ref,
            base_authoring_closure_ref=eref(base_closure),
            base_authoring_closure_hash=object_digest(base_payload),
            formal_fidelity_review_ref=eref(formal_review),
            formal_fidelity_review_hash=object_digest(formal_payload),
            economic_reader_review_ref=eref(economic_review),
            economic_reader_review_hash=object_digest(economic_payload),
            cold_reader_review_ref=eref(cold_review),
            cold_reader_review_hash=object_digest(cold_payload),
            writer=unit_payload.canonical_writer,
            assessor=CRAFT_ASSESSOR,
            move_realizations=move_realizations,
            required_directive_ids=stack_payload.active_requirements,
            directive_acceptance_checks=directive_checks,
            required_resolution_ids=diagnosis_payload.required_resolution_ids,
            resolution_requirement_checks=resolution_checks,
            target_reader_outcome=pc.TargetReaderOutcome(
                primary_audience=primary_audience,  # type: ignore[arg-type]
                benchmark_delta_reconstructible=True,
                operative_force_reconstructible=True,
                boundary_reconstructible=True,
                nearby_case_predictable=True,
                outcome="pass",
                evidence_refs=(
                    eref(unit),
                    unit_payload.manuscript_artifact_ref,
                    eref(economic_review),
                    eref(cold_review),
                    eref(reader),
                    eref(contracts),
                ),
                explanation=(
                    "The target bridge reader recovers the benchmark delta, operative force, boundary, and near-transfer prediction from the exact revised unit."
                ),
            ),
            formal_fidelity_outcome="pass",
            phrase_leak_audit_outcome="pass",
            phrase_leak_audit_ref=phrase_ref,
            named_voice_imitation_outcome="pass",
            empirical_template_contamination_outcome="pass",
            outcome="pass",
            assessed_at=created_at,
        )
        entity = self._profile_craft_entity(
            "craft.assessment.phase4.profiled_main_result",
            assessment,
            title="Independent craft-realization assessment",
            summary=(
                "The selected function is realized, formal fidelity is preserved, and phrase, voice, and empirical-template audits pass."
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        relations = [
            self._relation(
                before,
                relation_id="relation.phase4.manuscript.reviews.craft",
                relation_type="reviews",
                source=eref(unit),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=RESTRICTED_COMPARTMENTS,
            )
        ]
        for index, source in enumerate(
            (
                eref(selection),
                eref(diagnosis),
                eref(stack),
                eref(paper),
                eref(reader),
                eref(contracts),
                eref(base_closure),
                eref(formal_review),
                eref(economic_review),
                eref(cold_review),
            ),
            start=1,
        ):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase4.craft_review.input.{index}",
                    relation_type="depends_on",
                    source=source,
                    target=eref(entity),
                    created_at=created_at,
                    output_entities=(entity,),
                    privacy="restricted",
                    access_compartments=RESTRICTED_COMPARTMENTS,
                )
            )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=tuple(relations),
            artifacts=((registration, phrase_bytes),),
            evidence_refs=focus,
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        return entity

    def _close_profile_craft(
        self,
        *,
        base_closure: EntityVersion,
        unit: EntityVersion,
        diagnosis: EntityVersion,
        stack: EntityVersion,
        selection: EntityVersion,
        mapping_audit: EntityVersion,
        assessment: EntityVersion,
        created_at: str,
    ) -> EntityVersion:
        base_payload = a.parse_authoring_entity(base_closure)
        unit_payload = a.parse_authoring_entity(unit)
        diagnosis_payload = pc.parse_profile_craft_entity(diagnosis)
        stack_payload = pc.parse_profile_craft_entity(stack)
        selection_payload = pc.parse_profile_craft_entity(selection)
        audit_payload = pc.parse_profile_craft_entity(mapping_audit)
        assessment_payload = pc.parse_profile_craft_entity(assessment)
        assert isinstance(base_payload, a.ReviewClosure)
        assert isinstance(unit_payload, a.ManuscriptUnit)
        assert isinstance(diagnosis_payload, pc.ReaderProblemDiagnosis)
        assert isinstance(stack_payload, pc.ResolvedProfileStack)
        assert isinstance(selection_payload, pc.CraftSelectionManifest)
        assert isinstance(audit_payload, pc.PredicateMappingAudit)
        assert isinstance(assessment_payload, pc.CraftRealizationAssessment)
        focus = (
            eref(assessment),
            eref(selection),
            eref(unit),
            eref(mapping_audit),
            eref(diagnosis),
            eref(stack),
            eref(base_closure),
        )
        before, run = self._begin_phase4(
            route_id="close.profile_craft_review",
            actor=PROFILE_CRAFT_CLOSER,
            purpose="research_review",
            focus_refs=focus,
            created_at=created_at,
            compartments=RESTRICTED_COMPARTMENTS,
            privacy_clearance="restricted",
        )
        evidence_by_kind: dict[str, tuple[object, ...]] = {
            "universal_floor": (eref(stack),),
            "overlay_conflicts": (eref(stack),),
            "theory_only_corpus": (eref(selection),),
            "functional_matched_contrast": (eref(selection),),
            "provenance_access_confidence": (eref(selection),),
            "copyright_and_voice": (
                eref(assessment),
                assessment_payload.phrase_leak_audit_ref,
            ),
            "predicate_mapping": (eref(mapping_audit),),
            "craft_realization": (eref(assessment),),
            "target_reader_fit": (
                eref(assessment),
                *assessment_payload.target_reader_outcome.evidence_refs,
            ),
        }
        checks = tuple(
            pc.ProfileCraftClosureCheck(
                check_id=f"closure.phase4.check.{kind}",
                check_kind=kind,  # type: ignore[arg-type]
                outcome="pass",
                evidence_refs=evidence_by_kind[kind],  # type: ignore[arg-type]
                explanation=(
                    f"The exact current {kind} evidence passes its noncompensatory Phase 4 requirement without changing scientific truth or claim scope."
                ),
            )
            for kind in pc.PROFILE_CRAFT_READY_CHECK_ORDER
        )
        closure = pc.ProfileCraftClosure(
            closure_id="closure.phase4.profile_craft_ready",
            base_authoring_closure_ref=eref(base_closure),
            base_authoring_closure_hash=object_digest(base_payload),
            base_authoring_closure_outcome="authoring_ready",
            manuscript_unit_ref=eref(unit),
            manuscript_unit_hash=object_digest(unit_payload),
            reader_problem_diagnosis_ref=eref(diagnosis),
            reader_problem_diagnosis_hash=object_digest(diagnosis_payload),
            profile_stack=pc.ProjectPayloadBinding(
                entity_ref=eref(stack), payload_hash=object_digest(stack_payload)
            ),
            craft_selection=pc.ProjectPayloadBinding(
                entity_ref=eref(selection), payload_hash=object_digest(selection_payload)
            ),
            predicate_mapping_audits=(
                pc.ProjectPayloadBinding(
                    entity_ref=eref(mapping_audit),
                    payload_hash=object_digest(audit_payload),
                ),
            ),
            predicate_mapping_coverage_classes=(audit_payload.contract_coverage_class,),
            predicate_limitation_kinds=(
                "nonexact_clause_mapping",
                "domain_not_equal",
                "quantifier_not_equivalent",
                "assumption_mapping_nonexact",
                "bounded_execution_scope",
                "coverage_below_exact",
                "nonvacuity_unverified",
                "unexecutable_control",
            ),
            realization_assessment=pc.ProjectPayloadBinding(
                entity_ref=eref(assessment),
                payload_hash=object_digest(assessment_payload),
            ),
            source_state_revision=before.head,
            all_dependencies_current_and_fresh=True,
            checks=checks,
            outcome="ready",
            determined_by=PROFILE_CRAFT_CLOSER,
            determined_at=created_at,
        )
        entity = self._profile_craft_entity(
            "closure.phase4.profile_craft_ready",
            closure,
            title="Noncompensatory Phase 4 profile/craft closure",
            summary=(
                "The current Phase 3 authoring-ready manuscript also passes bounded mapping, profile, theory-only craft, realization, and copyright/voice checks."
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        relations = [
            self._relation(
                before,
                relation_id="relation.phase4.base_closure.validates.profile_craft",
                relation_type="validates",
                source=eref(base_closure),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=RESTRICTED_COMPARTMENTS,
            ),
            self._relation(
                before,
                relation_id="relation.phase4.assessment.validates.profile_craft",
                relation_type="validates",
                source=eref(assessment),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=RESTRICTED_COMPARTMENTS,
            ),
        ]
        for index, source in enumerate(
            (
                eref(unit),
                eref(stack),
                eref(selection),
                eref(diagnosis),
                eref(mapping_audit),
            ),
            start=1,
        ):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase4.closure.input.{index}",
                    relation_type="depends_on",
                    source=source,
                    target=eref(entity),
                    created_at=created_at,
                    output_entities=(entity,),
                    privacy="restricted",
                    access_compartments=RESTRICTED_COMPARTMENTS,
                )
            )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=tuple(relations),
            evidence_refs=focus,
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        return entity

    def _record_phase4_human_effort(
        self,
        *,
        prior_unit: EntityVersion,
        revised_unit: EntityVersion,
        created_at: str,
    ) -> EntityVersion:
        prior = a.parse_authoring_entity(prior_unit)
        revised = a.parse_authoring_entity(revised_unit)
        assert isinstance(prior, a.ManuscriptUnit)
        assert isinstance(revised, a.ManuscriptUnit)
        before, run = self._begin_v3(
            route_id="record.human_effort",
            actor=HUMAN,
            purpose="human_effort_measurement",
            focus_refs=(eref(revised_unit),),
            created_at=created_at,
            compartments=RESTRICTED_COMPARTMENTS,
            privacy_clearance="restricted",
        )
        payload = a.HumanEffortRecord(
            manuscript_unit_ref=eref(revised_unit),
            human=HUMAN,
            events=(
                a.HumanEffortEvent(
                    event_id="effort.phase4.profile_craft_repair",
                    occurred_at=created_at,
                    active_minutes=6,
                    affected_assertion_ids=("assertion.phase4.benchmark_delta",),
                    disposition="light_edit",
                    severity="low",
                    category="reader_path_result_hierarchy",
                    before_artifact_ref=prior.manuscript_artifact_ref,
                    after_artifact_ref=revised.manuscript_artifact_ref,
                    note=(
                        "The human inspected the target-specific benchmark-to-mechanism repair and accepted it with a light reader-path edit."
                    ),
                ),
            ),
            recorded_at=created_at,
        )
        entity = self._authoring_entity(
            "effort.phase4.profile_craft_repair",
            payload,
            title="Human effort for the Phase 4 target-specific repair",
            summary="Exact active human intervention is recorded for the profiled revision.",
            created_at=created_at,
            artifact_refs=(
                prior.manuscript_artifact_ref,
                revised.manuscript_artifact_ref,
            ),
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        relation = self._relation(
            before,
            relation_id="relation.phase4.effort.profiled_unit",
            relation_type="reports_effort",
            source=eref(revised_unit),
            target=eref(entity),
            created_at=created_at,
            output_entities=(entity,),
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=(relation,),
            evidence_refs=(
                eref(revised_unit),
                prior.manuscript_artifact_ref,
                revised.manuscript_artifact_ref,
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=RESTRICTED_COMPARTMENTS,
        )
        return entity

    def _after_fresh_g5(self, handoff: Mapping[str, object]) -> bool:
        inherited = super()._after_fresh_g5(handoff)
        self._run_phase4_continuation()
        return inherited

    def _run_phase4_continuation(self) -> bool:
        phase3_snapshot = replay(self.layout)
        historical_bytes = {
            (item.entity_id, item.version): canonical_json_bytes(item)
            for item in phase3_snapshot.entity_versions
        }
        package = self._current_entity(phase3_snapshot, "ValidatedArgumentPackage")
        assurance = self._current_entity(phase3_snapshot, "AssuranceBundle")
        minimal_profile = self._current_entity(
            phase3_snapshot, "ResolvedProfileManifest"
        )
        paper = self._current_entity(phase3_snapshot, "PaperIR")
        reader = self._current_entity(phase3_snapshot, "ReaderPath")
        contracts = self._current_entity(phase3_snapshot, "ResultContractSet")
        base_unit = self._current_entity(phase3_snapshot, "ManuscriptUnit")
        assurance_payload = a.parse_authoring_entity(assurance)
        assert isinstance(assurance_payload, a.AssuranceBundle)
        receipt = next(
            item
            for item in assurance_payload.tool_receipts
            if item.harness_kind in {"counterexample_search", "finite_grid"}
        )
        obligation = self._entity_at(phase3_snapshot, receipt.obligation_ref)
        claim_graph = self._entity_at(phase3_snapshot, assurance_payload.claim_graph_ref)
        formal_model = self._entity_at(phase3_snapshot, assurance_payload.formal_model_ref)
        assumption_map = self._entity_at(
            phase3_snapshot, assurance_payload.assumption_map_ref
        )

        self.phase4_active = True
        contract, _receipt = self._mapping_contract(
            assurance=assurance,
            claim_graph=claim_graph,
            formal_model=formal_model,
            assumption_map=assumption_map,
            obligation=obligation,
            created_at=_timestamp(25),
        )
        mapping_audit = self._audit_mapping(
            contract_entity=contract,
            assurance=assurance,
            claim_graph=claim_graph,
            formal_model=formal_model,
            assumption_map=assumption_map,
            obligation=obligation,
            created_at=_timestamp(26),
        )
        decisions = self._target_decisions(
            package=package, paper=paper, reader=reader
        )
        _target, stack = self._resolve_target_profile(
            package=package,
            assurance=assurance,
            paper=paper,
            reader=reader,
            minimal_profile=minimal_profile,
            mapping_audit=mapping_audit,
            decisions=decisions,
            created_at=_timestamp(31),
        )

        current = replay(self.layout)
        assignments = [
            item
            for item in current.entity_versions
            if item.entity_type == "CriticAssignment"
            and current.current_entities.get(item.entity_id) == item.version
        ]
        assignment_by_role = {
            payload.role: entity
            for entity in assignments
            if isinstance(
                (payload := a.parse_authoring_entity(entity)), a.CriticAssignment
            )
        }
        base_reviews = [
            item
            for item in current.entity_versions
            if item.entity_type == "ReviewRecord"
            and current.current_entities.get(item.entity_id) == item.version
            and isinstance(
                (payload := a.parse_authoring_entity(item)), a.ReviewRecord
            )
            and payload.manuscript_unit_ref == eref(base_unit)
        ]
        base_review_by_role = {
            payload.role: entity
            for entity in base_reviews
            if isinstance(
                (payload := a.parse_authoring_entity(entity)), a.ReviewRecord
            )
        }
        target_economic_review, target_findings = self._review_unit(
            unit=base_unit,
            paper=paper,
            contracts=contracts,
            assignment=assignment_by_role["economic_reader"],
            generation=4,
            economic_pass=False,
            created_at=_timestamp(32),
        )
        target_blocked_closure, target_brief = self._close_reviews(
            paper=paper,
            reader=reader,
            contracts=contracts,
            assurance=assurance,
            unit=base_unit,
            formal_review=base_review_by_role["formal_fidelity"],
            economic_review=target_economic_review,
            cold_review=base_review_by_role["cold_reader"],
            findings=target_findings,
            generation=4,
            ready=False,
            created_at=_timestamp(33),
            economic_ready=False,
            cold_ready=True,
        )
        self.assertIsNotNone(target_brief)
        assert target_brief is not None
        diagnosis = self._diagnose_target_reader_problem(
            paper=paper,
            reader=reader,
            contracts=contracts,
            stack=stack,
            base_unit=base_unit,
            diagnostic_reviews=(target_economic_review,),
            diagnostic_findings=target_findings,
            blocked_closure=target_blocked_closure,
            revision_brief=target_brief,
            created_at=_timestamp(34),
        )
        selection = self._retrieve_craft_move(
            paper=paper,
            reader=reader,
            contracts=contracts,
            stack=stack,
            diagnosis=diagnosis,
            created_at=_timestamp(35),
        )
        profiled_unit, profiled_text, writer_packet = self._compose_profiled_unit(
            package=package,
            assurance=assurance,
            minimal_profile=minimal_profile,
            paper=paper,
            reader=reader,
            contracts=contracts,
            stack=stack,
            diagnosis=diagnosis,
            selection=selection,
            base_unit=base_unit,
            blocked_closure=target_blocked_closure,
            revision_brief=target_brief,
            decisions=decisions,
            created_at=_timestamp(36),
        )
        formal_review, formal_findings = self._review_unit(
            unit=profiled_unit,
            paper=paper,
            contracts=contracts,
            assignment=assignment_by_role["formal_fidelity"],
            generation=5,
            economic_pass=True,
            created_at=_timestamp(37),
        )
        economic_review, economic_findings = self._review_unit(
            unit=profiled_unit,
            paper=paper,
            contracts=contracts,
            assignment=assignment_by_role["economic_reader"],
            generation=5,
            economic_pass=True,
            created_at=_timestamp(38),
        )
        probe = self._prepare_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=profiled_unit,
            reader=reader,
            generation=5,
            created_at=_timestamp(39),
        )
        response = self._answer_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=profiled_unit,
            probe=probe,
            generation=5,
            created_at=_timestamp(40),
        )
        cold_review, cold_findings = self._adjudicate_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=profiled_unit,
            probe=probe,
            response=response,
            generation=5,
            transfer_pass=True,
            created_at=_timestamp(41),
        )
        self.assertFalse(formal_findings or economic_findings or cold_findings)
        authoring_closure, brief = self._close_reviews(
            paper=paper,
            reader=reader,
            contracts=contracts,
            assurance=assurance,
            unit=profiled_unit,
            formal_review=formal_review,
            economic_review=economic_review,
            cold_review=cold_review,
            findings=(),
            generation=5,
            ready=True,
            created_at=_timestamp(42),
        )
        self.assertIsNone(brief)
        validate_authoring_ready(
            replay(self.layout), eref(authoring_closure), manuscript_text=profiled_text
        )
        assessment = self._review_craft_realization(
            paper=paper,
            reader=reader,
            contracts=contracts,
            stack=stack,
            diagnosis=diagnosis,
            selection=selection,
            unit=profiled_unit,
            base_closure=authoring_closure,
            formal_review=formal_review,
            economic_review=economic_review,
            cold_review=cold_review,
            created_at=_timestamp(43),
        )
        closure = self._close_profile_craft(
            base_closure=authoring_closure,
            unit=profiled_unit,
            diagnosis=diagnosis,
            stack=stack,
            selection=selection,
            mapping_audit=mapping_audit,
            assessment=assessment,
            created_at=_timestamp(44),
        )
        effort = self._record_phase4_human_effort(
            prior_unit=base_unit,
            revised_unit=profiled_unit,
            created_at=_timestamp(45),
        )
        final = replay(self.layout)
        validate_profile_craft_ready(final, eref(closure))
        self.assertEqual(
            canonical_json_bytes(replay_at(self.layout, final.head)),
            canonical_json_bytes(final),
        )
        final_historical = {
            (item.entity_id, item.version): canonical_json_bytes(item)
            for item in final.entity_versions
            if (item.entity_id, item.version) in historical_bytes
        }
        self.assertEqual(final_historical, historical_bytes)
        audit_payload = pc.parse_profile_craft_entity(mapping_audit)
        assert isinstance(audit_payload, pc.PredicateMappingAudit)
        self.assertEqual(audit_payload.verdict, "approved_partial")
        self.assertEqual(audit_payload.contract_coverage_class, "diagnostic")
        self.assertEqual(
            audit_payload.unexecutable_mutation_ids,
            ("mutation.phase4.omitted_assumption",),
        )
        self.assertTrue(audit_payload.domain_witness_verified)
        self.assertFalse(audit_payload.antecedent_witness_verified)
        self.assertEqual(writer_packet["packet_kind"], "profiled_canonical_writer")
        diagnosis_payload = pc.parse_profile_craft_entity(diagnosis)
        assert isinstance(diagnosis_payload, pc.ReaderProblemDiagnosis)
        self.assertEqual(diagnosis_payload.causal_class, "local_exposition")
        self.assertEqual(
            diagnosis_payload.blocked_review_closure_binding.entity_ref,
            eref(target_blocked_closure),
        )
        self.assertEqual(
            diagnosis_payload.revision_brief_binding.entity_ref,
            eref(target_brief),
        )
        target_brief_payload = a.parse_authoring_entity(target_brief)
        assert isinstance(target_brief_payload, a.RevisionBrief)
        self.assertEqual(
            diagnosis_payload.required_resolution_ids,
            tuple(
                item.instruction_id
                for item in target_brief_payload.instructions
                if item.blocking
            ),
        )
        assessment_payload = pc.parse_profile_craft_entity(assessment)
        assert isinstance(assessment_payload, pc.CraftRealizationAssessment)
        self.assertEqual(assessment_payload.target_reader_outcome.outcome, "pass")
        self.assertEqual(
            assessment_payload.required_resolution_ids,
            diagnosis_payload.required_resolution_ids,
        )
        closure_payload = pc.parse_profile_craft_entity(closure)
        assert isinstance(closure_payload, pc.ProfileCraftClosure)
        self.assertEqual(closure_payload.outcome, "ready")
        profiled_payload = a.parse_authoring_entity(profiled_unit)
        assert isinstance(profiled_payload, a.ManuscriptUnit)
        self.assertEqual(profiled_payload.previous_manuscript_unit_ref, eref(base_unit))
        self.assertEqual(profiled_payload.revision_brief_ref, eref(target_brief))
        self.assertEqual(final.current_entities[effort.entity_id], effort.version)
        return True


if __name__ == "__main__":
    import unittest

    unittest.main()
