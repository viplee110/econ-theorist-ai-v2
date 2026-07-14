"""Real-store acceptance tests for the v5 economics-framing preflight.

The fixture deliberately crosses the canonical Phase 2 framing and primitive
routes before exercising ``audit.framing_economics``.  It therefore tests the
same begin-run, provenance, candidate validation, commit, freshness, replay,
and human-decision boundaries used by an IDE host.
"""

from __future__ import annotations

import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path

from pydantic import ValidationError
from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.authoring_validation import facet_semantic_hash
from econ_theorist.candidate_contract import compile_candidate_authoring_contract
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.decisions import DecisionInputError, commit_decision
from econ_theorist.framing_quality import (
    AggregateInvarianceAssessment,
    ArchetypeTension,
    BenchmarkFramingAssessment,
    CausalChainStep,
    DisclosedFramingGap,
    EconomicForce,
    EconomistMemo,
    FramingObjectRef,
    FramingQualityBundle,
    FramingRepairTargetRef,
    HeldFixedObjectRef,
    IllustrativeMinimalExample,
    SelectionAssurance,
    pack_framing_quality_payload,
)
from econ_theorist.machine.models import WorkPacketV1
from econ_theorist.machine.navigation import enumerate_navigation_candidates
from econ_theorist.models import (
    Actor,
    ChangedFacets,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    RecordDecisionOp,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from econ_theorist.policy import (
    instruction_bundle_bytes,
    route_spec_by_hash,
)
from econ_theorist.project import init_project
from econ_theorist.runs import (
    RouteEntryError,
    begin_run,
    read_compiled_context,
    read_context,
    read_run,
    transaction_bindings,
)
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import commit_transaction
from econ_theorist.runtime.freshness import authority_semantic_hash, changed_semantic_facets
from econ_theorist.runtime.replay import (
    CandidateValidationError,
    replay,
    validate_candidate,
)
from econ_theorist.theory import (
    THEORY_PAYLOAD_OWNER_FACETS,
    BenchmarkRecord,
    BenchmarkSet,
    GateDossier,
    GateRequirement,
    PrimitiveEdge,
    PrimitiveGraph,
    PrimitiveNode,
    ResearchQuestion,
    TheoryPayload,
    pack_theory_payload,
    parse_theory_entity,
)


AGENT = Actor(kind="agent", actor_id="framing.route.agent")
HUMAN = Actor(kind="human", actor_id="human.owner")
T0 = "2026-07-14T08:00:00Z"
T1 = "2026-07-14T08:01:00Z"
T2 = "2026-07-14T08:02:00Z"
T3 = "2026-07-14T08:03:00Z"
T4 = "2026-07-14T08:04:00Z"
T5 = "2026-07-14T08:05:00Z"


def eref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def oref(
    object_id: str,
    label: str,
    semantic_level: str,
    node_id: str | None,
) -> FramingObjectRef:
    return FramingObjectRef(
        object_id=object_id,
        label=label,
        semantic_level=semantic_level,
        primitive_node_id=node_id,
    )


def href(
    object_id: str,
    label: str,
    semantic_level: str,
    node_id: str | None,
    fixing_level: str,
) -> HeldFixedObjectRef:
    return HeldFixedObjectRef(
        object_id=object_id,
        label=label,
        semantic_level=semantic_level,
        primitive_node_id=node_id,
        fixing_level=fixing_level,
    )


class FramingQualityRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._reset_project()

    def _reset_project(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.layout = StoreLayout.at(self.root)
        self.snapshot = init_project(
            self.root,
            name="Certification and endogenous quality",
            actor_id=HUMAN.actor_id,
            project_id="project.framing.route",
            created_at=T0,
        )
        self.route_counter = 0

    def _revised_upstream(self, upstream: EntityVersion) -> EntityVersion:
        payload = parse_theory_entity(upstream)
        if isinstance(payload, ResearchQuestion):
            payload = payload.model_copy(
                update={"unresolved_delta": payload.unresolved_delta + " Revised."}
            )
        elif isinstance(payload, BenchmarkSet):
            payload = payload.model_copy(
                update={
                    "exact_question_delta": payload.exact_question_delta
                    + " Revised."
                }
            )
        else:
            assert isinstance(payload, PrimitiveGraph)
            revised_node = payload.nodes[0].model_copy(
                update={
                    "economic_meaning": payload.nodes[0].economic_meaning
                    + " Revised."
                }
            )
            payload = payload.model_copy(
                update={"nodes": (revised_node, *payload.nodes[1:])}
            )
        return self._theory_entity(
            upstream.entity_id,
            payload,
            title=upstream.title,
            created_at=T4,
            version=2,
            supersedes=eref(upstream),
        )

    def _theory_entity(
        self,
        entity_id: str,
        payload: TheoryPayload,
        *,
        title: str,
        created_at: str,
        version: int = 1,
        supersedes: EntityVersionRef | None = None,
    ) -> EntityVersion:
        return EntityVersion(
            entity_id=entity_id,
            entity_type=type(payload).__name__,
            version=version,
            project_id=self.snapshot.project_id,
            title=title,
            summary=f"Canonical test object for {title}.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(payload),
            created_at=created_at,
            supersedes=supersedes,
        )

    def _framing_entity(
        self,
        payload: FramingQualityBundle,
        *,
        entity_id: str = "framing.quality.certification",
        created_at: str,
        version: int = 1,
        supersedes: EntityVersionRef | None = None,
    ) -> EntityVersion:
        return EntityVersion(
            entity_id=entity_id,
            entity_type="FramingQualityBundle",
            version=version,
            project_id=self.snapshot.project_id,
            title="Economics framing preflight",
            summary="Benchmark semantics, economic forces, and attribution risks.",
            status=ScientificStatus(interpretation_validity="hypothesized"),
            facets=pack_framing_quality_payload(payload),
            created_at=created_at,
            supersedes=supersedes,
        )

    def _begin(
        self,
        *,
        route_id: str,
        purpose: str,
        focus: tuple[str, ...],
        created_at: str,
    ) -> tuple[Snapshot, object]:
        self.route_counter += 1
        before = replay(self.layout)
        run = begin_run(
            self.layout,
            before,
            route_id=route_id,
            actor=AGENT,
            purpose=purpose,
            compartments=("project_research",),
            focus_entity_ids=focus,
            budget_units=32_000,
            route_run_id=f"run.framing.{self.route_counter}",
            context_manifest_id=f"context.framing.{self.route_counter}",
            created_at=created_at,
        )
        return before, run

    def _commit_started(
        self,
        before: Snapshot,
        run: object,
        *,
        outputs: tuple[EntityVersion, ...],
        relations: tuple[RelationVersion, ...],
        evidence_refs: tuple[EntityVersionRef, ...],
        created_at: str,
    ) -> Snapshot:
        entity_operations: list[CreateEntityOp | SupersedeEntityOp] = []
        declarations: list[ChangedFacets] = []
        for output in outputs:
            if output.version == 1:
                entity_operations.append(CreateEntityOp(entity=output))
                continue
            assert output.supersedes is not None
            prior = next(
                item
                for item in before.entity_versions
                if eref(item) == output.supersedes
            )
            entity_operations.append(
                SupersedeEntityOp(previous=output.supersedes, entity=output)
            )
            declarations.append(
                ChangedFacets(
                    entity_id=output.entity_id,
                    previous_version=output.version - 1,
                    new_version=output.version,
                    facets=changed_semantic_facets(prior, output),
                )
            )

        relation_refs = tuple(
            RelationVersionRef(relation_id=item.relation_id, version=item.version)
            for item in relations
        )
        run_id = getattr(run, "route_run_id")
        route_id = getattr(run, "route_id")
        transaction = Transaction(
            **transaction_bindings(self.layout, run_id),
            transaction_id=f"transaction.framing.{self.route_counter}",
            origin="route_run",
            project_id=before.project_id,
            base_revision=getattr(run, "base_revision"),
            route_run_id=run_id,
            route_id=route_id,
            actor=AGENT,
            intent=f"Exercise the exact {route_id} acceptance contract.",
            changed_facets=tuple(declarations),
            operations=(
                *entity_operations,
                *(CreateRelationOp(relation=item) for item in relations),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run_id,
                        route_id=route_id,
                        outcome="completed_with_candidate",
                        rationale="Every exact typed candidate passed validation.",
                        candidate_refs=(
                            *(eref(item) for item in outputs),
                            *relation_refs,
                        ),
                    )
                ),
            ),
            evidence_refs=evidence_refs,
            created_at=created_at,
            parent_transaction_hash=getattr(run, "base_revision"),
        )
        committed = commit_transaction(self.layout, transaction)
        self.assertEqual(committed.status, "committed")
        after = replay(self.layout)
        self.assertEqual(after.head, committed.head_after)
        for output in outputs:
            self.assertEqual(after.current_entities[output.entity_id], output.version)
        return after

    def _commit_route(
        self,
        *,
        route_id: str,
        purpose: str,
        focus: tuple[str, ...],
        outputs: tuple[EntityVersion, ...],
        relations: tuple[RelationVersion, ...],
        evidence_refs: tuple[EntityVersionRef, ...],
        created_at: str,
    ) -> Snapshot:
        before, run = self._begin(
            route_id=route_id,
            purpose=purpose,
            focus=focus,
            created_at=created_at,
        )
        return self._commit_started(
            before,
            run,
            outputs=outputs,
            relations=relations,
            evidence_refs=evidence_refs,
            created_at=created_at,
        )

    def _phase2_prefix(
        self,
        *,
        quality_node_kind: str = "choice",
    ) -> tuple[EntityVersion, EntityVersion, EntityVersion, EntityVersion]:
        question = self._theory_entity(
            "question.certification",
            ResearchQuestion(
                phenomenon="More informative certification can reduce realized quality.",
                object_to_explain="The quality reversal induced by seller and buyer responses.",
                unresolved_delta="Fixed-quality benchmarks suppress the supply response.",
                importance="Information policy changes both targeting and product quality.",
                kill_condition="The reversal survives when quality and inspection are fixed.",
                proposed_scope="One certification margin with endogenous quality and inspection.",
                candidate_archetypes=("mechanism_explanation",),
                prohibited_claims=("The framing audit proves the theorem.",),
            ),
            title="Certification question",
            created_at=T1,
        )
        benchmarks = self._theory_entity(
            "benchmarks.certification",
            BenchmarkSet(
                question_ref=eref(question),
                benchmarks=(
                    BenchmarkRecord(
                        benchmark_id="benchmark.fixed_quality",
                        label="Fixed seller quality",
                        exact_primitives=("Quality is fixed before certification.",),
                        timing=("Certification", "Inspection", "Purchase"),
                        solution_concept="Unique equilibrium in the stated region.",
                        prediction="Certification improves buyer targeting.",
                        unresolved_delta="Sellers cannot reoptimize quality.",
                    ),
                ),
                exact_question_delta="Allow quality and inspection to respond to certification.",
            ),
            title="Certification benchmark",
            created_at=T1,
        )
        frame_relations = (
            RelationVersion(
                relation_id="relation.question.frames.benchmarks",
                relation_type="frames",
                version=1,
                project_id=self.snapshot.project_id,
                source=eref(question),
                target=eref(benchmarks),
                created_at=T1,
            ),
            RelationVersion(
                relation_id="relation.question.benchmark.delta",
                relation_type="benchmark_delta",
                version=1,
                project_id=self.snapshot.project_id,
                source=eref(question),
                target=eref(benchmarks),
                created_at=T1,
            ),
        )
        self.snapshot = self._commit_route(
            route_id="frame.question_and_benchmarks",
            purpose="research_framing",
            focus=(),
            outputs=(question, benchmarks),
            relations=frame_relations,
            evidence_refs=(),
            created_at=T1,
        )

        graph = self._theory_entity(
            "primitives.certification",
            PrimitiveGraph(
                question_ref=eref(question),
                benchmark_set_ref=eref(benchmarks),
                nodes=(
                    PrimitiveNode(
                        node_id="node.certification",
                        kind="institution",
                        label="Certification rule",
                        economic_meaning="The institution changes information and incentives.",
                        status="primitive",
                    ),
                    PrimitiveNode(
                        node_id="node.inspection",
                        kind="choice",
                        label="Buyer inspection",
                        economic_meaning="Buyers reoptimize costly inspection.",
                        status="primitive",
                    ),
                    PrimitiveNode(
                        node_id="node.quality",
                        kind=quality_node_kind,
                        label="Seller quality",
                        economic_meaning="Sellers reoptimize hidden quality.",
                        status="primitive",
                    ),
                    PrimitiveNode(
                        node_id="node.match",
                        kind="outcome",
                        label="Realized match quality",
                        economic_meaning="The buyer's realized match value.",
                        status="derived",
                    ),
                    PrimitiveNode(
                        node_id="node.search_cost",
                        kind="preference_technology",
                        label="Search cost",
                        economic_meaning="The benchmark holds search cost fixed.",
                        status="primitive",
                    ),
                ),
                edges=(
                    PrimitiveEdge(
                        edge_id="edge.certification.inspection",
                        source_node_id="node.certification",
                        target_node_id="node.inspection",
                        economic_meaning="Certification changes inspection incentives.",
                    ),
                    PrimitiveEdge(
                        edge_id="edge.inspection.quality",
                        source_node_id="node.inspection",
                        target_node_id="node.quality",
                        economic_meaning="Inspection changes the return to quality.",
                    ),
                    PrimitiveEdge(
                        edge_id="edge.quality.match",
                        source_node_id="node.quality",
                        target_node_id="node.match",
                        economic_meaning="Quality changes the realized match.",
                    ),
                ),
            ),
            title="Certification primitive graph",
            created_at=T2,
        )
        source_dossier = self._theory_entity(
            "dossier.g1.certification.source",
            GateDossier(
                gate_kind="G1_question_benchmark",
                research_question_ref=eref(question),
                ordered_object_refs=(eref(question), eref(benchmarks), eref(graph)),
                requirements=(
                    GateRequirement(
                        requirement_id="g1.delta",
                        description="The exact benchmark delta is explicit.",
                        evidence_refs=(eref(question), eref(benchmarks)),
                        recorded_condition="evidence_supplied",
                    ),
                ),
                proposed_action="approve",
                rationale="The pre-audit dossier exposes the proposed question.",
                prepared_at=T2,
            ),
            title="Source G1 dossier",
            created_at=T2,
        )
        decompose_relations = (
            RelationVersion(
                relation_id="relation.question.decomposes.graph",
                relation_type="decomposes",
                version=1,
                project_id=self.snapshot.project_id,
                source=eref(question),
                target=eref(graph),
                created_at=T2,
            ),
            RelationVersion(
                relation_id="relation.source.dossier.governs.question",
                relation_type="governs",
                version=1,
                project_id=self.snapshot.project_id,
                source=eref(source_dossier),
                target=eref(question),
                created_at=T2,
            ),
        )
        self.snapshot = self._commit_route(
            route_id="decompose.primitives",
            purpose="research_discovery",
            focus=(question.entity_id, benchmarks.entity_id),
            outputs=(graph, source_dossier),
            relations=decompose_relations,
            evidence_refs=(eref(question), eref(benchmarks)),
            created_at=T2,
        )
        return question, benchmarks, graph, source_dossier

    def _assessment(
        self,
        *,
        selection_status: str = "unique_equilibrium",
        attribution_strength: str = "clean",
    ) -> BenchmarkFramingAssessment:
        return BenchmarkFramingAssessment(
            benchmark_id="benchmark.fixed_quality",
            changed=(
                oref(
                    "object.certification",
                    "Certification becomes available",
                    "primitive",
                    "node.certification",
                ),
            ),
            held_fixed=(
                href(
                    "object.search_cost",
                    "Search cost",
                    "primitive",
                    "node.search_cost",
                    "primitive",
                ),
            ),
            reoptimizing=(
                oref(
                    "object.inspection",
                    "Buyer inspection",
                    "behavioral_response",
                    "node.inspection",
                ),
                oref(
                    "object.quality",
                    "Seller quality",
                    "behavioral_response",
                    "node.quality",
                ),
            ),
            still_endogenous=(
                oref(
                    "object.endogenous.quality",
                    "Equilibrium seller quality",
                    "choice",
                    "node.quality",
                ),
            ),
            targets=(
                oref(
                    "object.match",
                    "Realized match quality",
                    "outcome",
                    "node.match",
                ),
            ),
            channel_kind="active_response",
            channel_path=(
                "node.certification",
                "node.inspection",
                "node.quality",
                "node.match",
            ),
            channel_summary="Certification changes inspection, quality, and matching.",
            aggregate_invariance=AggregateInvarianceAssessment(
                aggregate_object="Realized match quality",
                pointwise_policy_fixed=True,
                weighting_distribution_status="fixed",
                claims_aggregate_fixed=True,
                basis="The comparison uses the same ex ante population weights.",
                implication_for_attribution="Composition cannot drive the comparison.",
            ),
            selection_assurance=SelectionAssurance(
                status=selection_status,
                selection_rule="Use the locally continuous equilibrium branch.",
                basis="The branch is unique locally only when stated as such.",
                implication_for_attribution="Selection risk is disclosed at its actual level.",
            ),
            attribution_strength=attribution_strength,
            attribution_basis="The semantic ledger names every moving response margin.",
        )

    def _bundle_payload(
        self,
        question: EntityVersion,
        benchmarks: EntityVersion,
        graph: EntityVersion,
        source_dossier: EntityVersion,
        *,
        proposed_action: str = "ready_for_g1",
        selection_status: str = "unique_equilibrium",
        attribution_strength: str = "clean",
        repair_target: EntityVersion | None = None,
    ) -> FramingQualityBundle:
        risky_selection = selection_status in {"selector_only", "unresolved"}
        selection_gaps = (
            (
                DisclosedFramingGap(
                    gap_id="gap.selection",
                    category="equilibrium_selection",
                    description="The current result follows only a selected branch.",
                    affected_benchmark_ids=("benchmark.fixed_quality",),
                    consequence="A branch jump could contaminate causal attribution.",
                    resolution_needed="Prove uniqueness, continuity, or an all-equilibria result.",
                ),
            )
            if risky_selection
            else ()
        )
        repair_gaps = ()
        if repair_target is not None:
            repair_gaps = (
                DisclosedFramingGap(
                    gap_id="gap.upstream.revision",
                    category="benchmark_semantics",
                    description="The named upstream object misstates the comparison.",
                    affected_benchmark_ids=("benchmark.fixed_quality",),
                    repair_target_refs=(
                        FramingRepairTargetRef(
                            entity_type=repair_target.entity_type,
                            entity_ref=eref(repair_target),
                        ),
                    ),
                    consequence="The current framing cannot support G1.",
                    resolution_needed="Supersede the exact named object and rerun decomposition.",
                ),
            )
        gaps = (*selection_gaps, *repair_gaps)
        return FramingQualityBundle(
            research_question_ref=eref(question),
            benchmark_set_ref=eref(benchmarks),
            primitive_graph_ref=eref(graph),
            source_g1_dossier_ref=eref(source_dossier),
            tension=ArchetypeTension(
                result_archetype="mechanism_explanation",
                tension_kind="force_conflict",
                conventional_prediction="Certification improves buyer targeting.",
                countervailing_logic="Certification weakens inspection and quality incentives.",
                economic_puzzle="Better information can reduce realized match quality.",
                resolution_target="Separate targeting from endogenous quality supply.",
            ),
            forces=(
                EconomicForce(
                    force_id="force.targeting",
                    label="Direct targeting",
                    role="baseline_force",
                    operative_margin="Buyer inspection",
                    direction="raises_target",
                    economic_logic="Certification directs buyers toward better offers.",
                    active_when="Buyers condition inspection on certification.",
                    source_node_id="node.certification",
                    margin_node_id="node.inspection",
                    target_node_id="node.match",
                ),
                EconomicForce(
                    force_id="force.quality",
                    label="Quality-supply response",
                    role="countervailing_force",
                    operative_margin="Seller quality",
                    direction="lowers_target",
                    economic_logic="Reduced inspection weakens quality incentives.",
                    active_when="Sellers reoptimize quality after certification.",
                    source_node_id="node.certification",
                    margin_node_id="node.quality",
                    target_node_id="node.match",
                ),
            ),
            causal_chain=(
                CausalChainStep(
                    step_number=1,
                    force_ids=("force.targeting",),
                    cause="Certification changes buyer information.",
                    endogenous_response="Buyers change inspection.",
                    consequence="The return to hidden quality changes.",
                    source_node_id="node.certification",
                    target_node_id="node.inspection",
                ),
                CausalChainStep(
                    step_number=2,
                    force_ids=("force.quality",),
                    cause="Inspection incentives weaken.",
                    endogenous_response="Sellers reduce quality.",
                    consequence="Offer quality deteriorates.",
                    source_node_id="node.inspection",
                    target_node_id="node.quality",
                ),
                CausalChainStep(
                    step_number=3,
                    force_ids=("force.targeting", "force.quality"),
                    cause="Targeting and supply responses interact.",
                    endogenous_response="Buyers match with changed offers.",
                    consequence="Match quality falls when supply dominates.",
                    source_node_id="node.quality",
                    target_node_id="node.match",
                ),
            ),
            minimal_example=IllustrativeMinimalExample(
                title="Two sellers and one inspection opportunity",
                setup="Certification arrives before inspection and quality choices settle.",
                moving_primitive="Certification precision",
                held_fixed=("Search cost", "Buyer preferences"),
                endogenous_responses=("Inspection", "Seller quality"),
                predicted_pattern="Match quality falls when the quality response dominates.",
                economic_intuition="A targeting benefit can crowd out quality supply.",
                limitation="The example illustrates the mechanism but proves no theorem.",
                cannot_establish=("The theorem", "Novelty", "Global robustness"),
            ),
            economist_memo=EconomistMemo(
                headline="When certification weakens quality",
                opening_question="Can better certification make buyer matches worse?",
                benchmark_message="The benchmark freezes seller quality.",
                tension_message="Targeting improves while quality incentives weaken.",
                mechanism_message="Inspection changes the return to hidden quality.",
                result_preview="Supply deterioration can dominate targeting.",
                contribution_message="The comparison restores the endogenous supply response.",
                scope_condition="The claim is local to the stated equilibrium region.",
                reader_takeaway="Information policy changes what firms choose to supply.",
            ),
            benchmark_assessments=(
                self._assessment(
                    selection_status=selection_status,
                    attribution_strength=attribution_strength,
                ),
            ),
            disclosed_gaps=gaps,
            proposed_action=proposed_action,
            action_rationale=(
                "The active channel and attribution checks are resolved."
                if proposed_action == "ready_for_g1"
                else "Selection remains a disclosed diagnostic risk."
            ),
        )

    def _hard_relation(
        self,
        relation_id: str,
        relation_type: str,
        source: EntityVersion,
        target: EntityVersion,
        *,
        created_at: str,
    ) -> RelationVersion:
        source_owner = (
            THEORY_PAYLOAD_OWNER_FACETS.get(source.entity_type)
            or "economic_interpretation"
        )
        target_owner = (
            THEORY_PAYLOAD_OWNER_FACETS.get(target.entity_type)
            or "economic_interpretation"
        )
        source_hash = (
            authority_semantic_hash(
                source,
                self.snapshot.decisions,
                self.snapshot.effective_decisions,
            )
            if source_owner == "authority"
            else facet_semantic_hash(source, source_owner)
        )
        return RelationVersion(
            relation_id=relation_id,
            relation_type=relation_type,
            version=1,
            project_id=self.snapshot.project_id,
            source=eref(source),
            target=eref(target),
            dependency_mode="hard",
            upstream=SemanticFacetRef(
                entity_id=source.entity_id,
                version=source.version,
                facet=source_owner,
                semantic_hash=source_hash,
            ),
            downstream=FacetPathRef(
                entity_id=target.entity_id,
                version=target.version,
                facet=target_owner,
            ),
            created_at=created_at,
        )

    def _replacement_dossier(
        self,
        source_dossier: EntityVersion,
        bundle: EntityVersion,
        *,
        entity_id: str,
        proposed_action: str,
        created_at: str,
    ) -> EntityVersion:
        source_payload = parse_theory_entity(source_dossier)
        assert isinstance(source_payload, GateDossier)
        ready = proposed_action == "ready_for_g1"
        return self._theory_entity(
            entity_id,
            GateDossier(
                gate_kind="G1_question_benchmark",
                research_question_ref=source_payload.research_question_ref,
                ordered_object_refs=(*source_payload.ordered_object_refs, eref(bundle)),
                requirements=(
                    *source_payload.requirements,
                    GateRequirement(
                        requirement_id="g1.framing_quality",
                        description="Economics framing and attribution pass preflight.",
                        evidence_refs=(eref(bundle),),
                        recorded_condition=(
                            "evidence_supplied" if ready else "risk_disclosed"
                        ),
                    ),
                ),
                proposed_action="approve" if ready else "revise",
                rationale="The source package is strengthened by the framing audit.",
                prepared_at=created_at,
            ),
            title="Replacement G1 dossier",
            created_at=created_at,
        )

    def _commit_audit(
        self,
        core: tuple[EntityVersion, EntityVersion, EntityVersion, EntityVersion],
        *,
        proposed_action: str = "ready_for_g1",
        selection_status: str = "unique_equilibrium",
        attribution_strength: str = "clean",
        prior_bundle: EntityVersion | None = None,
        repair_target: EntityVersion | None = None,
        bundle_mutator: (
            Callable[[FramingQualityBundle], FramingQualityBundle] | None
        ) = None,
        created_at: str = T3,
    ) -> tuple[EntityVersion, EntityVersion, Snapshot]:
        question, benchmarks, graph, source_dossier = core
        bundle_version = 1 if prior_bundle is None else prior_bundle.version + 1
        bundle_payload = self._bundle_payload(
            question,
            benchmarks,
            graph,
            source_dossier,
            proposed_action=proposed_action,
            selection_status=selection_status,
            attribution_strength=attribution_strength,
            repair_target=repair_target,
        )
        if prior_bundle is not None:
            bundle_payload = bundle_payload.model_copy(
                update={
                    "action_rationale": (
                        bundle_payload.action_rationale
                        + " The same-scope audit was independently refreshed."
                    )
                }
            )
        if bundle_mutator is not None:
            bundle_payload = bundle_mutator(bundle_payload)
        bundle = self._framing_entity(
            bundle_payload,
            created_at=created_at,
            version=bundle_version,
            supersedes=eref(prior_bundle) if prior_bundle is not None else None,
        )
        replacement = self._replacement_dossier(
            source_dossier,
            bundle,
            entity_id=f"dossier.g1.certification.audit.{bundle_version}",
            proposed_action=proposed_action,
            created_at=created_at,
        )
        sources = (question, benchmarks, graph, source_dossier)
        relations = (
            *(
                self._hard_relation(
                    f"relation.audit.{bundle_version}.{index}",
                    "audits",
                    source,
                    bundle,
                    created_at=created_at,
                )
                for index, source in enumerate(sources, start=1)
            ),
            self._hard_relation(
                f"relation.audit.{bundle_version}.governs",
                "governs",
                bundle,
                replacement,
                created_at=created_at,
            ),
        )
        evidence = tuple(eref(item) for item in sources)
        focus = tuple(item.entity_id for item in sources)
        if prior_bundle is not None:
            evidence = (*evidence, eref(prior_bundle))
            focus = (*focus, prior_bundle.entity_id)
        before, run = self._begin(
            route_id="audit.framing_economics",
            purpose="scientific_framing_audit",
            focus=focus,
            created_at=created_at,
        )
        self.snapshot = self._commit_started(
            before,
            run,
            outputs=(bundle, replacement),
            relations=relations,
            evidence_refs=evidence,
            created_at=created_at,
        )
        return bundle, replacement, self.snapshot

    def _g1_decision(
        self,
        question: EntityVersion,
        dossier: EntityVersion,
        *,
        decision_id: str,
        decided_at: str,
    ) -> Decision:
        return Decision(
            decision_id=decision_id,
            version=1,
            project_id=self.snapshot.project_id,
            decision_kind="G1_question_benchmark",
            subject_ref=dossier.entity_id,
            scope_ref=question.entity_id,
            question="Approve this exact question and benchmark scope?",
            options=("approve", "revise", "kill"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve only after the economics framing preflight.",
            rationale="The exact benchmark, channel, and risks have been reviewed.",
            evidence_refs=(dossier.entity_id,),
            unresolved_risks=("Novelty is evaluated at a later gate.",),
            required_authority="L2",
            decider=HUMAN,
            decided_at=decided_at,
            status="confirmed",
        )

    def test_ready_candidate_commits_replays_and_controls_g1_approval(self) -> None:
        core = self._phase2_prefix()
        question, _, _, source_dossier = core
        with self.assertRaisesRegex(DecisionInputError, "framing-quality preflight"):
            commit_decision(
                self.layout,
                self._g1_decision(
                    question,
                    source_dossier,
                    decision_id="decision.g1.preflight.bypass",
                    decided_at=T3,
                ),
            )

        bundle, replacement, after = self._commit_audit(core)
        self.assertEqual(after.current_entities[bundle.entity_id], 1)
        self.assertEqual(after.current_entities[replacement.entity_id], 1)
        self.assertEqual(len(after.route_outcomes), 3)
        self.assertEqual(
            canonical_json_bytes(replay(self.layout)), canonical_json_bytes(after)
        )

        committed = commit_decision(
            self.layout,
            self._g1_decision(
                question,
                replacement,
                decision_id="decision.g1.after.framing",
                decided_at=T4,
            ),
            transaction_id="transaction.decision.g1.after.framing",
            route_run_id="run.decision.g1.after.framing",
            created_at=T4,
        )
        self.assertEqual(committed.status, "committed")
        gated = replay(self.layout)
        self.assertEqual(
            gated.current_decisions["decision.g1.after.framing"], 1
        )

    def test_direct_human_decision_transaction_cannot_bypass_g1_preflight(self) -> None:
        core = self._phase2_prefix()
        question, _, _, source_dossier = core
        decision = self._g1_decision(
            question,
            source_dossier,
            decision_id="decision.g1.direct.transaction.bypass",
            decided_at=T3,
        )
        head_before = self.snapshot.head
        transaction = Transaction(
            transaction_id="transaction.decision.g1.direct.transaction.bypass",
            origin="human_decision",
            project_id=self.snapshot.project_id,
            base_revision=head_before,
            route_run_id="run.decision.g1.direct.transaction.bypass",
            actor=HUMAN,
            intent="Attempt to bypass the live v5 G1 framing preflight.",
            operations=(RecordDecisionOp(decision=decision),),
            privacy=decision.privacy,
            access_compartments=decision.access_compartments,
            created_at=T3,
            parent_transaction_hash=head_before,
        )
        historical_projection = validate_candidate(self.snapshot, transaction)
        self.assertEqual(
            historical_projection.current_decisions[decision.decision_id], 1
        )
        with self.assertRaisesRegex(
            CandidateValidationError, "live G1 framing preflight"
        ):
            commit_transaction(self.layout, transaction)
        self.assertEqual(replay(self.layout).head, head_before)

    def test_honest_selector_only_candidate_commits_but_cannot_approve_g1(self) -> None:
        core = self._phase2_prefix()
        question = core[0]
        bundle, replacement, after = self._commit_audit(
            core,
            proposed_action="continue_diagnostic",
            selection_status="selector_only",
            attribution_strength="qualified",
        )
        self.assertEqual(after.current_entities[bundle.entity_id], 1)
        with self.assertRaisesRegex(DecisionInputError, "ready_for_g1"):
            commit_decision(
                self.layout,
                self._g1_decision(
                    question,
                    replacement,
                    decision_id="decision.g1.selector.only",
                    decided_at=T4,
                ),
            )

    def test_same_scope_continuation_stales_old_dossier_and_allows_new_g1(self) -> None:
        core = self._phase2_prefix()
        question = core[0]
        first_bundle, first_dossier, _ = self._commit_audit(
            core, proposed_action="continue_diagnostic"
        )
        second_bundle, second_dossier, after = self._commit_audit(
            core,
            prior_bundle=first_bundle,
            created_at=T4,
        )
        self.assertEqual(after.current_entities[first_bundle.entity_id], 2)
        self.assertEqual(second_bundle.supersedes, eref(first_bundle))
        self.assertEqual(after.current_entities[second_dossier.entity_id], 1)
        old_status = after.derived_status[first_dossier.entity_id]
        self.assertEqual(old_status.freshness["authority"], "stale")
        with self.assertRaises(DecisionInputError):
            commit_decision(
                self.layout,
                self._g1_decision(
                    question,
                    first_dossier,
                    decision_id="decision.g1.stale.replacement",
                    decided_at=T5,
                ),
            )

        committed = commit_decision(
            self.layout,
            self._g1_decision(
                question,
                second_dossier,
                decision_id="decision.g1.after.continued.framing",
                decided_at=T5,
            ),
            transaction_id="transaction.decision.g1.after.continued.framing",
            route_run_id="run.decision.g1.after.continued.framing",
            created_at=T5,
        )
        self.assertEqual(committed.status, "committed")
        gated = replay(self.layout)
        self.assertEqual(
            gated.current_decisions["decision.g1.after.continued.framing"], 1
        )

    def test_ready_or_revise_bundle_cannot_continue_the_same_exact_scope(self) -> None:
        for action in ("ready_for_g1", "revise_framing"):
            with self.subTest(action=action):
                if action == "revise_framing":
                    self._reset_project()
                core = self._phase2_prefix()
                first_bundle, _, _ = self._commit_audit(
                    core,
                    proposed_action=action,
                    repair_target=core[2] if action == "revise_framing" else None,
                )
                with self.assertRaisesRegex(RouteEntryError, "continue_diagnostic"):
                    self._commit_audit(
                        core,
                        prior_bundle=first_bundle,
                        created_at=T4,
                    )

    def test_proactive_repair_cannot_switch_to_an_unnamed_upstream_target(self) -> None:
        core = self._phase2_prefix()
        bundle, _, _ = self._commit_audit(
            core,
            proposed_action="revise_framing",
            repair_target=core[2],
        )
        with self.assertRaisesRegex(RouteEntryError, "not named"):
            self._begin(
                route_id="repair.dependency",
                purpose="research_repair",
                focus=(core[0].entity_id, bundle.entity_id),
                created_at=T4,
            )

    def test_each_gap_named_upstream_revision_commits_stales_and_blocks_g1(self) -> None:
        for upstream_index in range(3):
            with self.subTest(upstream_index=upstream_index):
                if upstream_index:
                    self._reset_project()
                core = self._phase2_prefix()
                question = core[0]
                target = core[upstream_index]
                bundle, replacement, _ = self._commit_audit(
                    core,
                    proposed_action="revise_framing",
                    repair_target=target,
                )
                if upstream_index == 0:
                    candidates, diagnostics = enumerate_navigation_candidates(
                        self.layout,
                        self.snapshot,
                        actor=AGENT,
                        compartments=("project_research",),
                        privacy_clearance="project_private",
                        requested_route_ids=("repair.dependency",),
                    )
                    focus_sets = {
                        frozenset(item.entity_id for item in candidate.key.focus_refs)
                        for candidate in candidates
                    }
                    self.assertIn(
                        frozenset((target.entity_id, bundle.entity_id)),
                        focus_sets,
                        tuple(item.message for item in diagnostics),
                    )
                revised = self._revised_upstream(target)
                self.snapshot = self._commit_route(
                    route_id="repair.dependency",
                    purpose="research_repair",
                    focus=(target.entity_id, bundle.entity_id),
                    outputs=(revised,),
                    relations=(),
                    evidence_refs=(eref(target), eref(bundle)),
                    created_at=T4,
                )
                after = replay(self.layout)
                self.assertEqual(after.current_entities[target.entity_id], 2)
                self.assertEqual(
                    after.derived_status[bundle.entity_id].freshness[
                        "economic_interpretation"
                    ],
                    "stale",
                )
                self.assertEqual(
                    after.derived_status[replacement.entity_id].freshness["authority"],
                    "stale",
                )
                if upstream_index == 0:
                    benchmark_payload = parse_theory_entity(core[1])
                    assert isinstance(benchmark_payload, BenchmarkSet)
                    repaired_benchmark = self._theory_entity(
                        core[1].entity_id,
                        benchmark_payload.model_copy(
                            update={"question_ref": eref(revised)}
                        ),
                        title=core[1].title,
                        created_at=T5,
                        version=2,
                        supersedes=eref(core[1]),
                    )
                    self.snapshot = self._commit_route(
                        route_id="repair.dependency",
                        purpose="research_repair",
                        focus=(core[1].entity_id,),
                        outputs=(repaired_benchmark,),
                        relations=(),
                        evidence_refs=(eref(core[1]),),
                        created_at=T5,
                    )
                    self.assertEqual(
                        self.snapshot.current_entities[core[1].entity_id], 2
                    )
                with self.assertRaises(DecisionInputError):
                    commit_decision(
                        self.layout,
                        self._g1_decision(
                            question,
                            replacement,
                            decision_id=f"decision.g1.stale.upstream.{upstream_index}",
                            decided_at=T5,
                        ),
                    )

    def test_known_composition_and_qualified_attribution_can_reach_human_g1(
        self,
    ) -> None:
        core = self._phase2_prefix()

        def honest_composition(bundle: FramingQualityBundle) -> FramingQualityBundle:
            assessment = bundle.benchmark_assessments[0]
            aggregate = assessment.aggregate_invariance.model_copy(
                update={
                    "pointwise_policy_fixed": False,
                    "weighting_distribution_status": "endogenous",
                    "claims_aggregate_fixed": False,
                    "basis": "Certification changes the stationary composition.",
                    "implication_for_attribution": (
                        "Composition is the active channel, not an invariant."
                    ),
                }
            )
            qualified = assessment.model_copy(
                update={
                    "aggregate_invariance": aggregate,
                    "attribution_strength": "qualified",
                    "attribution_basis": (
                        "The composition channel is identified on the stated region."
                    ),
                }
            )
            return bundle.model_copy(
                update={"benchmark_assessments": (qualified,)}
            )

        _, replacement, _ = self._commit_audit(
            core, bundle_mutator=honest_composition
        )
        result = commit_decision(
            self.layout,
            self._g1_decision(
                core[0],
                replacement,
                decision_id="decision.g1.honest.composition",
                decided_at=T4,
            ),
        )
        self.assertEqual(result.status, "committed")

    def test_endogenous_transition_can_be_the_only_active_margin(self) -> None:
        core = self._phase2_prefix(quality_node_kind="equilibrium_object")

        def transition_channel(bundle: FramingQualityBundle) -> FramingQualityBundle:
            assessment = bundle.benchmark_assessments[0]
            transition = oref(
                "object.quality.transition",
                "Endogenous quality transition",
                "transition_kernel",
                "node.quality",
            )
            return bundle.model_copy(
                update={
                    "benchmark_assessments": (
                        assessment.model_copy(
                            update={
                                "reoptimizing": (),
                                "still_endogenous": (transition,),
                            }
                        ),
                    )
                }
            )

        _, replacement, _ = self._commit_audit(
            core, bundle_mutator=transition_channel
        )
        result = commit_decision(
            self.layout,
            self._g1_decision(
                core[0],
                replacement,
                decision_id="decision.g1.transition.channel",
                decided_at=T4,
            ),
        )
        self.assertEqual(result.status, "committed")

    def test_semantic_placebo_and_fixed_movable_alias_are_rejected(self) -> None:
        outcome_core = self._phase2_prefix(quality_node_kind="outcome")
        with self.assertRaisesRegex(CandidateValidationError, "placebo_control"):
            self._commit_audit(outcome_core)

        self._reset_project()
        fixed_core = self._phase2_prefix()

        def alias_choice(bundle: FramingQualityBundle) -> FramingQualityBundle:
            assessment = bundle.benchmark_assessments[0]
            fixed_choice = href(
                "object.fixed.inspection.alias",
                "Buyer inspection held fixed",
                "choice",
                "node.inspection",
                "choice",
            )
            return bundle.model_copy(
                update={
                    "benchmark_assessments": (
                        assessment.model_copy(
                            update={
                                "held_fixed": (
                                    *assessment.held_fixed,
                                    fixed_choice,
                                )
                            }
                        ),
                    )
                }
            )

        with self.assertRaisesRegex(
            CandidateValidationError, "fixed_endogenous_conflict"
        ):
            self._commit_audit(fixed_core, bundle_mutator=alias_choice)

    def test_force_chain_rejects_unused_zero_and_path_detached_forces(self) -> None:
        def unused_counterforce(bundle: FramingQualityBundle) -> FramingQualityBundle:
            steps = tuple(
                step.model_copy(update={"force_ids": ("force.targeting",)})
                for step in bundle.causal_chain
            )
            return bundle.model_copy(update={"causal_chain": steps})

        def zero_force(bundle: FramingQualityBundle) -> FramingQualityBundle:
            baseline = bundle.forces[0].model_copy(
                update={
                    "source_node_id": "node.match",
                    "margin_node_id": "node.match",
                    "target_node_id": "node.match",
                }
            )
            return bundle.model_copy(
                update={"forces": (baseline, bundle.forces[1])}
            )

        def detached_force(bundle: FramingQualityBundle) -> FramingQualityBundle:
            counterforce = bundle.forces[1].model_copy(
                update={
                    "source_node_id": "node.quality",
                    "margin_node_id": "node.quality",
                }
            )
            return bundle.model_copy(
                update={"forces": (bundle.forces[0], counterforce)}
            )

        cases = (
            (unused_counterforce, "every declared economic force"),
            (zero_force, "nonzero source-to-target"),
            (detached_force, "ordered subpath"),
        )
        for index, (mutator, message) in enumerate(cases):
            with self.subTest(message=message):
                if index:
                    self._reset_project()
                core = self._phase2_prefix()
                with self.assertRaisesRegex(CandidateValidationError, message):
                    self._commit_audit(core, bundle_mutator=mutator)

    def test_one_direction_causal_channel_can_reach_human_g1(self) -> None:
        core = self._phase2_prefix()

        def one_direction(bundle: FramingQualityBundle) -> FramingQualityBundle:
            force = bundle.forces[1].model_copy(
                update={"role": "equilibrium_feedback"}
            )
            steps = tuple(
                step.model_copy(update={"force_ids": (force.force_id,)})
                for step in bundle.causal_chain
            )
            tension = ArchetypeTension(
                result_archetype="mechanism_explanation",
                tension_kind="causal_channel",
                conventional_prediction="The benchmark freezes seller response.",
                economic_puzzle="Restoring the response changes match quality.",
                resolution_target="Trace the endogenous quality channel.",
            )
            return bundle.model_copy(
                update={
                    "tension": tension,
                    "forces": (force,),
                    "causal_chain": steps,
                }
            )

        _, replacement, _ = self._commit_audit(
            core, bundle_mutator=one_direction
        )
        result = commit_decision(
            self.layout,
            self._g1_decision(
                core[0],
                replacement,
                decision_id="decision.g1.causal.channel",
                decided_at=T4,
            ),
        )
        self.assertEqual(result.status, "committed")

    def test_three_framing_defect_codes_are_machine_searchable(self) -> None:
        with self.assertRaisesRegex(
            ValidationError, "aggregate_invariance_unsupported"
        ):
            AggregateInvarianceAssessment(
                aggregate_object="Stationary welfare",
                pointwise_policy_fixed=True,
                weighting_distribution_status="endogenous",
                claims_aggregate_fixed=True,
                basis="State-contingent policies are fixed but state weights move.",
                implication_for_attribution="The aggregate need not remain fixed.",
            )

        assessment = self._assessment()
        inactive = assessment.still_endogenous[0].model_copy(
            update={"semantic_level": "outcome"}
        )
        with self.assertRaisesRegex(ValidationError, "placebo_control"):
            BenchmarkFramingAssessment.model_validate(
                {
                    **assessment.model_dump(mode="python"),
                    "reoptimizing": (),
                    "still_endogenous": (inactive,),
                }
            )
        with self.assertRaisesRegex(
            ValidationError, "selection_robustness_unsupported"
        ):
            BenchmarkFramingAssessment.model_validate(
                {
                    **assessment.model_dump(mode="python"),
                    "selection_assurance": assessment.selection_assurance.model_copy(
                        update={"status": "selector_only"}
                    ),
                }
            )

    def test_candidate_contract_exposes_bundle_schema_and_framing_invariants(self) -> None:
        core = self._phase2_prefix()
        focus = tuple(item.entity_id for item in core)
        snapshot, run = self._begin(
            route_id="audit.framing_economics",
            purpose="scientific_framing_audit",
            focus=focus,
            created_at=T3,
        )
        run_id = getattr(run, "route_run_id")
        manifest = read_context(self.layout, run_id)
        canonical_run = read_run(self.layout, run_id)
        compiled = read_compiled_context(self.layout, run_id)
        bindings = transaction_bindings(self.layout, run_id)
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
            candidate_logical_path=f".econ-theorist/staging/{run_id}/candidate.json",
            shadow_logical_root=f".econ-theorist/operational/v1/runs/{run_id}/shadow",
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
            self.layout, packet, packet_hash
        )
        schemas = {item.entity_type: item for item in contract.payload_schemas}
        self.assertIn("FramingQualityBundle", schemas)
        self.assertEqual(
            schemas["FramingQualityBundle"].payload_schema_id,
            "econ_theorist.framing_quality/FramingQualityBundle/v1",
        )
        invariant_ids = {
            item.invariant_id for item in contract.output_contract.model_invariants
        }
        self.assertTrue(
            {
                "framing.aggregate_invariance",
                "framing.active_response",
                "framing.selection_assurance",
                "framing.semantic_ledger",
                "framing.archetype_tension",
                "framing.replacement_dossier",
            }.issubset(invariant_ids)
        )


if __name__ == "__main__":
    unittest.main()
