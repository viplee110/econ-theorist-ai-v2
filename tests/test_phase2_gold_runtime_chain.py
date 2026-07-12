"""End-to-end runtime chain for the Phase 2 development gold case.

This test deliberately exercises the canonical runtime instead of calling the
Phase 2 semantic validator directly.  It is the smallest useful prefix of the
eventual G1--G5 gold reconstruction: framing, primitive decomposition, a later
human G1 decision, and a G1-gated mechanism tournament.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import canonical_json_bytes, sha256_digest, transaction_bytes
from econ_theorist.decisions import commit_decision
from econ_theorist.gold_cases import load_attention_fixture
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    ChangedFacets,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    RouteRun,
    ScientificStatus,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V2_HASH
from econ_theorist.project import init_project
from econ_theorist.runs import (
    RouteEntryError,
    begin_run,
    read_context,
    transaction_bindings,
)
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import (
    StagedArtifact,
    commit_prepared,
    preflight_candidate,
)
from econ_theorist.runtime.freshness import changed_semantic_facets
from econ_theorist.runtime.replay import replay, replay_at
from econ_theorist.staging import (
    read_staged_transaction,
    stage_candidate,
    staged_artifact_path,
)
from econ_theorist.theory import (
    AbsorptionAssessment,
    BenchmarkRecord,
    BenchmarkSet,
    ClaimDependencyEdge,
    ClaimGraph,
    ClaimNode,
    ClosestTheoryDimension,
    ClosestTheoryMap,
    EconomicArgumentEdge,
    EconomicArgumentGraph,
    EconomicArgumentNode,
    EconomicToFormalEntry,
    ExampleCase,
    ExampleSuite,
    FrozenPrediction,
    FormalModel,
    FormalObject,
    FormalToEconomicEntry,
    FormalizationMap,
    GateDossier,
    GateRequirement,
    MechanismHypothesis,
    MechanismPairComparison,
    MechanismStep,
    MechanismTournament,
    ImplementationPairComparison,
    ImplementationTournament,
    LiteratureAssertion,
    LiteratureEvidence,
    PredictionRegister,
    PredictionReconciliation,
    ProofObligation,
    PreResultBrief,
    PrimitiveEdge,
    PrimitiveGraph,
    PrimitiveNode,
    RationalAssignment,
    ReducedRational,
    ResultPortfolio,
    PortfolioItem,
    AssumptionMap,
    AssumptionRecord,
    ResearchQuestion,
    TheoryPayload,
    ValidatedArgumentPackage,
    VerificationBundle,
    VerificationRecord,
    pack_theory_payload,
    parse_theory_entity,
)
from econ_theorist.theory_validation import (
    _effective_approved_gates,
    _typed_reference_closure_is_current_and_fresh,
)


AGENT = Actor(kind="agent", actor_id="gold.runtime.agent")
HUMAN = Actor(kind="human", actor_id="human.owner")
T0 = "2026-07-11T15:00:00Z"
T1 = "2026-07-11T15:01:00Z"
T2 = "2026-07-11T15:02:00Z"
T3 = "2026-07-11T15:03:00Z"
T4 = "2026-07-11T15:04:00Z"
T5 = "2026-07-11T15:05:00Z"
T6 = "2026-07-11T15:06:00Z"
T7 = "2026-07-11T15:07:00Z"
T8 = "2026-07-11T15:08:00Z"
T9 = "2026-07-11T15:09:00Z"
T10 = "2026-07-11T15:10:00Z"
T11 = "2026-07-11T15:11:00Z"
T12 = "2026-07-11T15:12:00Z"
T13 = "2026-07-11T15:13:00Z"
T14 = "2026-07-11T15:14:00Z"
T15 = "2026-07-11T15:15:00Z"
T16 = "2026-07-11T15:16:00Z"
T17 = "2026-07-11T15:17:00Z"
T18 = "2026-07-11T15:18:00Z"
T19 = "2026-07-11T15:19:00Z"
FIXTURE = (
    REPOSITORY_ROOT
    / "tests"
    / "fixtures"
    / "phase2_attention_precision_gold.v1.json"
)


def eref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


class Phase2GoldRuntimeChainTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.layout = StoreLayout.at(self.root)
        self.snapshot = init_project(
            self.root,
            name="Attention, precision, and indivisible processing",
            actor_id=HUMAN.actor_id,
            project_id="project.gold.attention.runtime",
            created_at=T0,
        )
        self.route_counter = 0

    def _after_fresh_g5(self, handoff: Mapping[str, object]) -> bool:
        """Optional continuation point for later-phase real-store acceptance tests.

        The Phase 2 test itself returns ``False`` and continues into its sealed
        absorption mutation.  A later-phase subclass may consume the exact
        local scientific objects and return ``True`` after completing its own
        continuation, without weakening or duplicating the Phase 2 setup.
        """

        del handoff
        return False

    def _entity(
        self,
        entity_id: str,
        payload: TheoryPayload,
        *,
        title: str,
        summary: str,
        created_at: str,
        artifact_refs: tuple[ArtifactDependencyRef, ...] = (),
        version: int = 1,
        supersedes: EntityVersionRef | None = None,
    ) -> EntityVersion:
        return EntityVersion(
            entity_id=entity_id,
            entity_type=type(payload).__name__,
            version=version,
            project_id=self.snapshot.project_id,
            title=title,
            summary=summary,
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(payload),
            artifact_refs=artifact_refs,
            created_at=created_at,
            supersedes=supersedes,
        )

    def _artifact(
        self,
        artifact_id: str,
        *,
        logical_name: str,
        media_type: str,
        data: bytes,
        created_at: str,
    ) -> tuple[ArtifactRegistration, ArtifactDependencyRef, bytes]:
        digest = sha256_digest(data)
        registration = ArtifactRegistration(
            artifact_id=artifact_id,
            version=1,
            project_id=self.snapshot.project_id,
            logical_name=logical_name,
            media_type=media_type,
            content_hash=digest,
            byte_size=len(data),
            created_at=created_at,
        )
        return (
            registration,
            ArtifactDependencyRef(
                artifact_id=artifact_id,
                version=1,
                content_hash=digest,
            ),
            data,
        )

    def _commit_route(
        self,
        *,
        route_id: str,
        purpose: str,
        outputs: tuple[EntityVersion, ...],
        relations: tuple[RelationVersion, ...] = (),
        artifacts: tuple[tuple[ArtifactRegistration, bytes], ...] = (),
        evidence_refs: tuple[EntityVersionRef, ...] = (),
        authority_basis: tuple[str, ...] = (),
        focus_entity_ids: tuple[str, ...] = (),
        created_at: str,
        actor: Actor = AGENT,
        compartments: tuple[str, ...] = ("project_research",),
        route_registry_hash: str = ROUTE_REGISTRY_V2_HASH,
    ) -> tuple[RouteRun, Snapshot]:
        """Run the real begin -> stage -> preflight -> commit -> replay path."""

        self.route_counter += 1
        before = replay(self.layout)
        run = begin_run(
            self.layout,
            before,
            route_id=route_id,
            actor=actor,
            purpose=purpose,
            compartments=compartments,
            focus_entity_ids=focus_entity_ids,
            budget_units=32_000,
            route_run_id=f"run.gold.{self.route_counter}",
            context_manifest_id=f"context.gold.{self.route_counter}",
            created_at=created_at,
            route_registry_hash=route_registry_hash,
        )
        context = read_context(self.layout, run.route_run_id)
        self.assertEqual(context.route_registry_hash, route_registry_hash)
        selected_refs = set(context.selected_entity_refs)
        if run.route_version < 3:
            for entity_id in focus_entity_ids:
                self.assertIn(
                    EntityVersionRef(
                        entity_id=entity_id,
                        version=before.current_entities[entity_id],
                    ),
                    selected_refs,
                )

        candidate_refs = (
            *(eref(item) for item in outputs),
            *(
                RelationVersionRef(
                    relation_id=item.relation_id, version=item.version
                )
                for item in relations
            ),
            *(
                ArtifactDependencyRef(
                    artifact_id=item.artifact_id,
                    version=item.version,
                    content_hash=item.content_hash,
                )
                for item, _ in artifacts
            ),
        )
        entity_operations: list[CreateEntityOp | SupersedeEntityOp] = []
        changed_facets: list[ChangedFacets] = []
        for item in outputs:
            if item.version == 1:
                entity_operations.append(CreateEntityOp(entity=item))
                continue
            if item.supersedes is None:
                self.fail("versioned test output must name its exact predecessor")
            entity_operations.append(
                SupersedeEntityOp(previous=item.supersedes, entity=item)
            )
            previous_entity = next(
                existing
                for existing in before.entity_versions
                if existing.entity_id == item.supersedes.entity_id
                and existing.version == item.supersedes.version
            )
            changed_facets.append(
                ChangedFacets(
                    entity_id=item.entity_id,
                    previous_version=item.supersedes.version,
                    new_version=item.version,
                    facets=changed_semantic_facets(previous_entity, item),
                )
            )
        transaction = Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id=f"transaction.gold.{self.route_counter}",
            origin="route_run",
            project_id=before.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=actor,
            intent=f"Advance the gold case through {route_id}.",
            changed_facets=tuple(changed_facets),
            operations=(
                *(RegisterArtifactOp(artifact=item) for item, _ in artifacts),
                *entity_operations,
                *(CreateRelationOp(relation=item) for item in relations),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run.route_run_id,
                        route_id=run.route_id,
                        outcome="completed_with_candidate",
                        rationale="The route produced every listed exact typed candidate.",
                        candidate_refs=candidate_refs,
                    )
                ),
            ),
            evidence_refs=evidence_refs,
            authority_basis=authority_basis,
            created_at=created_at,
            parent_transaction_hash=run.base_revision,
        )
        candidate_path = self.root / f"candidate-{self.route_counter}.json"
        candidate_path.write_bytes(transaction_bytes(transaction))
        artifact_paths: dict[str, Path] = {}
        for index, (registration, data) in enumerate(artifacts):
            path = self.root / f"artifact-{self.route_counter}-{index}.bin"
            path.write_bytes(data)
            artifact_paths[registration.artifact_id] = path
        digest = stage_candidate(
            self.layout,
            run.route_run_id,
            candidate_path,
            artifacts=artifact_paths,
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
                for registration, _ in artifacts
            ),
        )
        committed = commit_prepared(self.layout, prepared)
        self.assertEqual(committed.status, "committed")
        after = replay(self.layout)
        self.assertEqual(after.head, committed.head_after)
        for output in outputs:
            self.assertEqual(after.current_entities[output.entity_id], output.version)
            replayed_output = next(
                item
                for item in after.entity_versions
                if item.entity_id == output.entity_id
                and item.version == output.version
            )
            self.assertEqual(
                canonical_json_bytes(replayed_output), canonical_json_bytes(output)
            )
        for relation in relations:
            self.assertEqual(
                after.current_relations[relation.relation_id], relation.version
            )
        for registration, _ in artifacts:
            self.assertEqual(
                after.current_artifacts[registration.artifact_id],
                registration.version,
            )
        return run, after

    def test_gold_chain_crosses_real_human_g1_through_g5_gates(self) -> None:
        fixture_payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
        fixture_summary = load_attention_fixture(FIXTURE)
        self.assertEqual(
            fixture_summary["case_id"],
            "phase2.attention_precision.indivisible.v1",
        )
        question = self._entity(
            "question.attention_precision",
            ResearchQuestion(
                phenomenon=(
                    "A less precise signal can induce greater realized decision accuracy."
                ),
                object_to_explain=(
                    "The reversal in accuracy when signal precision changes processing incentives."
                ),
                unresolved_delta=(
                    "Fixed-attention benchmarks omit the endogenous extensive processing margin."
                ),
                importance=(
                    "Information design can change whether information is used, not only its conditional quality."
                ),
                kill_condition=(
                    "The reversal survives fixed attention or does not require precision-linked processing costs."
                ),
                proposed_scope=(
                    "Binary states and actions, precision in (0,1], and indivisible attention chosen before the signal."
                ),
                candidate_archetypes=(
                    "mechanism_explanation",
                    "comparative_statics_threshold",
                ),
                prohibited_claims=(
                    "Accuracy is welfare without an explicit social objective.",
                    "The result is robust to divisible attention.",
                ),
            ),
            title="Can coarser information improve realized accuracy?",
            summary="Exact question for the attention-precision development case.",
            created_at=T1,
        )
        question_ref = eref(question)
        benchmarks = self._entity(
            "benchmarks.attention_precision",
            BenchmarkSet(
                question_ref=question_ref,
                benchmarks=(
                    BenchmarkRecord(
                        benchmark_id="benchmark.fixed_attention",
                        label="Fixed processing",
                        exact_primitives=(
                            "binary state with prior one half",
                            "binary action",
                            "processing fixed at one",
                        ),
                        timing=("precision is set", "signal is observed", "action is chosen"),
                        solution_concept="Optimal binary action after the signal.",
                        prediction="Higher precision weakly raises realized accuracy.",
                        unresolved_delta="There is no endogenous decision to process the signal.",
                    ),
                    BenchmarkRecord(
                        benchmark_id="benchmark.free_processing",
                        label="Costless processing",
                        exact_primitives=(
                            "binary state with prior one half",
                            "processing cost equals zero",
                        ),
                        timing=("precision is set", "processing is chosen", "action is chosen"),
                        solution_concept="Optimal processing and binary action.",
                        prediction="Every signal is processed and higher precision raises accuracy.",
                        unresolved_delta="Processing participation never responds to precision.",
                    ),
                ),
                exact_question_delta=(
                    "Allow precision-linked processing cost kappa*x^2 and an indivisible pre-signal processing choice."
                ),
            ),
            title="Exact comparison benchmarks",
            summary="Fixed-attention and costless-processing baselines.",
            created_at=T1,
        )
        frame_run, framed = self._commit_route(
            route_id="frame.question_and_benchmarks",
            purpose="research_framing",
            outputs=(question, benchmarks),
            relations=(
                RelationVersion(
                    relation_id="relation.question_frames_benchmarks",
                    relation_type="frames",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=question_ref,
                    target=eref(benchmarks),
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T1,
                ),
                RelationVersion(
                    relation_id="relation.question_benchmark_delta",
                    relation_type="benchmark_delta",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=question_ref,
                    target=eref(benchmarks),
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T1,
                ),
            ),
            focus_entity_ids=(self.snapshot.project_id,),
            created_at=T1,
        )
        self.assertEqual(frame_run.base_revision, self.snapshot.head)
        self.assertEqual(len(framed.route_outcomes), 1)

        benchmark_ref = eref(benchmarks)
        primitive_graph = self._entity(
            "primitives.attention_precision",
            PrimitiveGraph(
                question_ref=question_ref,
                benchmark_set_ref=benchmark_ref,
                nodes=(
                    PrimitiveNode(
                        node_id="primitive.precision",
                        kind="information",
                        label="Signal precision x",
                        economic_meaning="Precision raises conditional accuracy to (1+x)/2.",
                        status="primitive",
                    ),
                    PrimitiveNode(
                        node_id="primitive.attention",
                        kind="choice",
                        label="Indivisible processing d",
                        economic_meaning="The receiver chooses d in {0,1} before seeing the signal.",
                        status="primitive",
                    ),
                    PrimitiveNode(
                        node_id="primitive.cost",
                        kind="preference_technology",
                        label="Processing cost kappa*x^2",
                        economic_meaning="More precise signals are more costly to process.",
                        status="primitive",
                    ),
                    PrimitiveNode(
                        node_id="outcome.accuracy",
                        kind="outcome",
                        label="Realized accuracy",
                        economic_meaning="Probability that the binary action equals the state.",
                        status="derived",
                    ),
                ),
                edges=(
                    PrimitiveEdge(
                        edge_id="edge.precision_cost",
                        source_node_id="primitive.precision",
                        target_node_id="primitive.cost",
                        economic_meaning="Precision increases the cost of processing.",
                    ),
                    PrimitiveEdge(
                        edge_id="edge.attention_accuracy",
                        source_node_id="primitive.attention",
                        target_node_id="outcome.accuracy",
                        economic_meaning="Processing determines whether precision can affect the action.",
                    ),
                ),
            ),
            title="Primitive graph",
            summary="Exact extensive-attention primitive decomposition.",
            created_at=T2,
        )
        primitive_ref = eref(primitive_graph)
        g1_dossier = self._entity(
            "dossier.g1.attention_precision",
            GateDossier(
                gate_kind="G1_question_benchmark",
                research_question_ref=question_ref,
                ordered_object_refs=(question_ref, benchmark_ref, primitive_ref),
                requirements=(
                    GateRequirement(
                        requirement_id="g1.delta",
                        description="The exact delta from both benchmarks is explicit.",
                        evidence_refs=(question_ref, benchmark_ref),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g1.kill_condition",
                        description="A fixed-attention falsifier is stated before mechanism search.",
                        evidence_refs=(question_ref, primitive_ref),
                        recorded_condition="evidence_supplied",
                    ),
                ),
                proposed_action="approve",
                rationale="The question is important, falsifiable, and separated from its benchmarks.",
                prepared_at=T2,
            ),
            title="G1 question and benchmark dossier",
            summary="Immutable evidence package for a later human G1 decision.",
            created_at=T2,
        )
        _, decomposed = self._commit_route(
            route_id="decompose.primitives",
            purpose="research_discovery",
            outputs=(primitive_graph, g1_dossier),
            relations=(
                RelationVersion(
                    relation_id="relation.question_decomposes_to_primitives",
                    relation_type="decomposes",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=question_ref,
                    target=primitive_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T2,
                ),
                RelationVersion(
                    relation_id="relation.g1_governs_question",
                    relation_type="governs",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(g1_dossier),
                    target=question_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T2,
                ),
            ),
            evidence_refs=(question_ref, benchmark_ref),
            focus_entity_ids=(question.entity_id, benchmarks.entity_id),
            created_at=T2,
        )
        self.assertEqual(len(decomposed.route_outcomes), 2)

        g1 = Decision(
            decision_id="decision.g1.attention_precision",
            version=1,
            project_id=self.snapshot.project_id,
            decision_kind="G1_question_benchmark",
            subject_ref=g1_dossier.entity_id,
            scope_ref=question.entity_id,
            question="Approve this exact question and benchmark scope for mechanism investment?",
            options=("approve", "revise", "kill"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve the exact scoped dossier.",
            rationale="The extensive processing margin is economically meaningful and the kill test is decisive.",
            evidence_refs=(g1_dossier.entity_id,),
            unresolved_risks=("Novelty has not been evaluated at G1.",),
            required_authority="L2",
            decider=HUMAN,
            decided_at=T3,
            status="confirmed",
        )
        decision_result = commit_decision(self.layout, g1)
        self.assertEqual(decision_result.status, "committed")
        gated = replay(self.layout)
        self.assertEqual(gated.current_decisions[g1.decision_id], 1)
        self.assertIn(
            g1.decision_id,
            {reference.decision_id for reference in gated.effective_decisions.values()},
        )

        selected = self._entity(
            "mechanism.extensive_attention",
            MechanismHypothesis(
                question_ref=question_ref,
                primitive_graph_ref=primitive_ref,
                decision_margin_or_foundational_distinction="Whether the receiver processes the signal.",
                initiating_wedge="An increase in precision raises both conditional value and convex processing cost.",
                force_chain=(
                    MechanismStep(
                        step_id="step.cost",
                        source="Higher signal precision",
                        response_or_constraint="raises kappa*x^2",
                        target="processing surplus",
                        economic_meaning="The extensive attention margin can switch off.",
                        effect_kind="conflict",
                    ),
                    MechanismStep(
                        step_id="step.use",
                        source="Processing participation",
                        response_or_constraint="determines whether the signal enters the action",
                        target="realized accuracy",
                        economic_meaning="A precise ignored signal can underperform a coarser processed signal.",
                        effect_kind="transformation",
                    ),
                ),
                predicted_consequence="Accuracy reverses exactly when only the coarse signal is processed.",
                boundary="1/(2*h) < kappa <= 1/(2*ell) under processing at indifference.",
                expected_load_bearing_conditions=(
                    "indivisible processing",
                    "precision-linked convex processing cost",
                ),
                distinguishing_signature="The reversal disappears when attention is fixed or processing cost is constant.",
                killer_test="If divisible attention preserves a strict coarse advantage, this mechanism is incomplete.",
            ),
            title="Extensive-attention mechanism",
            summary="Precision changes the decision to process information.",
            created_at=T4,
        )
        rival = self._entity(
            "mechanism.direct_information",
            MechanismHypothesis(
                question_ref=question_ref,
                primitive_graph_ref=primitive_ref,
                decision_margin_or_foundational_distinction="Conditional informativeness with processing fixed.",
                initiating_wedge="Higher precision makes the signal more likely to match the state.",
                force_chain=(
                    MechanismStep(
                        step_id="step.direct_accuracy",
                        source="Higher signal precision",
                        response_or_constraint="raises conditional signal accuracy",
                        target="realized accuracy",
                        economic_meaning="With fixed use, more information improves the binary action.",
                        effect_kind="direct",
                    ),
                ),
                predicted_consequence="Higher precision weakly raises accuracy.",
                boundary="No strict coarse advantage when both signals are processed.",
                expected_load_bearing_conditions=("processing is fixed at one",),
                distinguishing_signature="The prediction remains monotone when attention cannot change.",
                killer_test="A strict coarse advantage under fixed processing rejects this rival.",
            ),
            title="Direct-information rival",
            summary="The standard conditional informativeness force with fixed attention.",
            created_at=T4,
        )
        tournament = self._entity(
            "tournament.mechanisms.attention_precision",
            MechanismTournament(
                question_ref=question_ref,
                hypothesis_refs=(eref(selected), eref(rival)),
                comparisons=(
                    MechanismPairComparison(
                        left_ref=eref(selected),
                        right_ref=eref(rival),
                        distinct_arrow_or_signature="Only the extensive-attention chain changes processing participation.",
                        decisive_test="Hold processing fixed and compare the accuracy ordering.",
                    ),
                ),
                proposed_selected_ref=eref(selected),
                serious_rival_refs=(eref(rival),),
                selection_rationale="The fixed-attention ablation separates the reversal from the direct information force.",
            ),
            title="Mechanism tournament",
            summary="Extensive attention is selected against a serious fixed-attention rival.",
            created_at=T4,
        )
        tournament_run, final = self._commit_route(
            route_id="tournament.mechanisms",
            purpose="research_discovery",
            outputs=(selected, rival, tournament),
            relations=(
                RelationVersion(
                    relation_id="relation.extensive_attention_explains_question",
                    relation_type="explains",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(selected),
                    target=question_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T4,
                ),
                RelationVersion(
                    relation_id="relation.selected_compares_to_direct_rival",
                    relation_type="compares_to",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(selected),
                    target=eref(rival),
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T4,
                ),
            ),
            # Every exact prior typed input is both selected into context and
            # cited by the candidate.  This is intentionally stronger than the
            # initial v2 validator and keeps the chain compatible with explicit
            # route input contracts.
            evidence_refs=(
                question_ref,
                benchmark_ref,
                primitive_ref,
                eref(g1_dossier),
            ),
            authority_basis=(g1.decision_id,),
            focus_entity_ids=(
                question.entity_id,
                benchmarks.entity_id,
                primitive_graph.entity_id,
                g1_dossier.entity_id,
            ),
            created_at=T4,
        )

        self.assertEqual(tournament_run.base_revision, gated.head)
        self.assertEqual(len(final.chain), 5)  # genesis + three routes + human G1
        self.assertEqual(len(final.route_outcomes), 3)
        self.assertEqual(final.route_outcomes[-1].route_id, "tournament.mechanisms")
        self.assertEqual(
            final.route_outcomes[-1].candidate_refs,
            (
                eref(selected),
                eref(rival),
                eref(tournament),
                RelationVersionRef(
                    relation_id="relation.extensive_attention_explains_question",
                    version=1,
                ),
                RelationVersionRef(
                    relation_id="relation.selected_compares_to_direct_rival",
                    version=1,
                ),
            ),
        )
        self.assertEqual(final.current_entities[tournament.entity_id], 1)

        brief_bytes = canonical_json_bytes(
            fixture_payload["generator"]["pre_result_brief"]
        )
        brief_registration, brief_artifact_ref, _ = self._artifact(
            "artifact.pre_result_brief.attention_precision",
            logical_name="Sealed attention-precision pre-result brief",
            media_type="application/json",
            data=brief_bytes,
            created_at=T5,
        )
        pre_result_brief = self._entity(
            "brief.pre_result.attention_precision",
            PreResultBrief(
                question_ref=question_ref,
                benchmark_set_ref=benchmark_ref,
                primitive_graph_ref=primitive_ref,
                institution="A receiver chooses whether to process a binary signal before observing it.",
                allowed_context_refs=(
                    question_ref,
                    benchmark_ref,
                    primitive_ref,
                    eref(selected),
                    eref(rival),
                    eref(tournament),
                ),
                allowed_tools=(
                    "exact_rational_arithmetic",
                    "hand_derivation",
                    "finite_falsification",
                ),
                budget_units=8_000,
                excluded_information=(
                    "The headline reversal interval.",
                    "Gold examples E0-E6 and their answers.",
                    "The absorption comparator and translation map.",
                ),
                attempt_id="attempt.attention_precision.development.v1",
            ),
            title="Sealed pre-result brief",
            summary="Generator-visible inputs fixed before examples and solutions.",
            created_at=T5,
            artifact_refs=(brief_artifact_ref,),
        )
        prediction_register = self._entity(
            "predictions.attention_precision",
            PredictionRegister(
                question_ref=question_ref,
                mechanism_tournament_ref=eref(tournament),
                original_predictions=(
                    FrozenPrediction(
                        prediction_id="prediction.extensive_attention",
                        hypothesis_ref=eref(selected),
                        predicted_result=(
                            "Accuracy is strictly higher under ell than h exactly when only ell is processed."
                        ),
                        proposed_economic_chain=(
                            "precision raises conditional information value",
                            "precision raises processing cost kappa*x^2",
                            "the extensive processing margin can switch off",
                            "use of information determines realized accuracy",
                        ),
                        expected_conditions=(
                            "0 < ell < h <= 1",
                            "indivisible processing chosen before the signal",
                            "process at indifference",
                        ),
                        expected_ablation_outcome=(
                            "Fixing processing or replacing kappa*x^2 by a common cost eliminates the strict coarse advantage."
                        ),
                        expected_rival_difference=(
                            "The fixed-attention rival predicts weakly higher accuracy under h."
                        ),
                        surprise_or_falsifier=(
                            "A strict coarse advantage with fixed attention or divisible attention falsifies this chain."
                        ),
                        frozen_at=T5,
                    ),
                    FrozenPrediction(
                        prediction_id="prediction.direct_information",
                        hypothesis_ref=eref(rival),
                        predicted_result=(
                            "When both signals are processed, accuracy is weakly increasing in precision."
                        ),
                        proposed_economic_chain=(
                            "precision raises conditional signal accuracy",
                            "the signal enters the action under fixed processing",
                        ),
                        expected_conditions=(
                            "processing is fixed at one",
                            "the receiver follows the processed signal",
                        ),
                        expected_ablation_outcome=(
                            "Removing the extensive processing margin restores monotonicity."
                        ),
                        expected_rival_difference=(
                            "Unlike extensive attention, direct information cannot generate ell beating h."
                        ),
                        surprise_or_falsifier=(
                            "A strict coarse advantage with both signals processed rejects the rival."
                        ),
                        frozen_at=T5,
                    ),
                ),
            ),
            title="Frozen prediction register",
            summary="Prospective predictions for the selected mechanism and serious rival.",
            created_at=T5,
        )
        prediction_ref = eref(prediction_register)
        _, frozen = self._commit_route(
            route_id="freeze.predictions",
            purpose="research_discovery",
            outputs=(pre_result_brief, prediction_register),
            relations=(
                RelationVersion(
                    relation_id="relation.selected_predicts_register",
                    relation_type="predicts",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(selected),
                    target=prediction_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T5,
                ),
                RelationVersion(
                    relation_id="relation.rival_predicts_register",
                    relation_type="predicts",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(rival),
                    target=prediction_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T5,
                ),
                RelationVersion(
                    relation_id="relation.brief_tests_predictions",
                    relation_type="tests",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(pre_result_brief),
                    target=prediction_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T5,
                ),
            ),
            artifacts=((brief_registration, brief_bytes),),
            evidence_refs=(
                question_ref,
                benchmark_ref,
                primitive_ref,
                eref(selected),
                eref(rival),
                eref(tournament),
            ),
            authority_basis=(g1.decision_id,),
            focus_entity_ids=(
                question.entity_id,
                benchmarks.entity_id,
                primitive_graph.entity_id,
                selected.entity_id,
                rival.entity_id,
                tournament.entity_id,
            ),
            created_at=T5,
        )
        self.assertEqual(frozen.current_artifacts[brief_registration.artifact_id], 1)
        self.assertEqual(frozen.route_outcomes[-1].route_id, "freeze.predictions")

        gold_cases = fixture_payload["evaluator"]["gold_examples"]
        role_by_case = {
            "E0": ("benchmark",),
            "E1": ("mechanism_on",),
            "E2": ("ablation",),
            "E3": ("rival_separator",),
            "E4": ("boundary",),
            "E5": ("boundary", "tightness"),
            "E6": ("failure",),
        }
        example_cases: list[ExampleCase] = []
        example_artifacts: list[tuple[ArtifactRegistration, bytes]] = []
        example_artifact_refs: list[ArtifactDependencyRef] = []
        for gold_case in gold_cases:
            case_id = gold_case["case_id"]
            case_bytes = canonical_json_bytes(gold_case)
            registration, solution_ref, _ = self._artifact(
                f"artifact.example.{case_id}",
                logical_name=f"Exact hand solution for {case_id}",
                media_type="application/json",
                data=case_bytes,
                created_at=T6,
            )
            example_artifacts.append((registration, case_bytes))
            example_artifact_refs.append(solution_ref)

            rational_values: list[RationalAssignment] = []
            for symbol in ("ell", "h", "kappa", "constant_cost"):
                raw = gold_case.get(symbol)
                if isinstance(raw, dict) and {
                    "numerator",
                    "denominator",
                }.issubset(raw):
                    rational_values.append(
                        RationalAssignment(
                            symbol=symbol,
                            value=ReducedRational(
                                numerator=raw["numerator"],
                                denominator=raw["denominator"],
                            ),
                        )
                    )
            for symbol in ("delta_ell", "delta_h", "y_ell", "y_h"):
                raw = gold_case["expected"].get(symbol)
                if isinstance(raw, dict):
                    rational_values.append(
                        RationalAssignment(
                            symbol=f"expected.{symbol}",
                            value=ReducedRational(
                                numerator=raw["numerator"],
                                denominator=raw["denominator"],
                            ),
                        )
                    )
            expected = gold_case["expected"]
            example_cases.append(
                ExampleCase(
                    case_id=case_id,
                    roles=role_by_case[case_id],
                    setup=(
                        f"Use the exact rational parameters registered for {case_id}; "
                        f"the tie rule is {gold_case['tie_rule']}."
                    ),
                    exact_values=tuple(rational_values),
                    primitive_to_choice_trace=(
                        "Compute processing surplus Delta(x)=x/2-kappa*x^2, or the stated constant-cost ablation.",
                        f"The exact choices are d(ell)={expected['d_ell']} and d(h)={expected['d_h']}.",
                    ),
                    interaction_to_outcome_trace=(
                        "Processed information yields accuracy (1+x)/2; ignored information yields one half.",
                        f"The resulting exact ordering is {expected['ordering']}.",
                    ),
                    result=(
                        f"{case_id} yields {expected['ordering']} with the exact outputs in its immutable solution artifact."
                    ),
                    method="hand_solved",
                    solution_artifact_ref=solution_ref,
                    assumption_ids=(
                        "assumption.binary_attention",
                        "assumption.process_at_indifference",
                    ),
                )
            )

        solution_ref_by_case = {
            reference.artifact_id.rsplit(".", 1)[-1]: reference
            for reference in example_artifact_refs
        }
        prospective_example_ref = EntityVersionRef(
            entity_id="examples.attention_precision", version=1
        )
        reconciled_prediction_register = self._entity(
            prediction_register.entity_id,
            PredictionRegister(
                question_ref=question_ref,
                mechanism_tournament_ref=eref(tournament),
                original_predictions=parse_theory_entity(
                    prediction_register
                ).original_predictions,
                reconciliations=(
                    PredictionReconciliation(
                        reconciliation_id="reconciliation.extensive_attention",
                        prediction_id="prediction.extensive_attention",
                        outcome="confirmed",
                        observed_result=(
                            "E1 has ell processed and h ignored; E2 removes the reversal under constant cost."
                        ),
                        mechanism_diagnosis=(
                            "The extensive processing margin, not conditional information quality alone, generates the reversal."
                        ),
                        evidence_refs=(
                            prospective_example_ref,
                            solution_ref_by_case["E1"],
                            solution_ref_by_case["E2"],
                        ),
                        recorded_at=T6,
                    ),
                    PredictionReconciliation(
                        reconciliation_id="reconciliation.direct_information",
                        prediction_id="prediction.direct_information",
                        outcome="confirmed",
                        observed_result=(
                            "E0, E2, and the fixed-attention branch of E3 are monotone in precision."
                        ),
                        mechanism_diagnosis=(
                            "The direct information force survives, but it is dominated when precision switches processing participation."
                        ),
                        evidence_refs=(
                            prospective_example_ref,
                            solution_ref_by_case["E0"],
                            solution_ref_by_case["E2"],
                            solution_ref_by_case["E3"],
                        ),
                        recorded_at=T6,
                    ),
                ),
            ),
            title=prediction_register.title,
            summary=prediction_register.summary,
            created_at=T6,
            version=2,
            supersedes=prediction_ref,
        )
        reconciled_prediction_ref = eref(reconciled_prediction_register)
        example_suite = self._entity(
            "examples.attention_precision",
            ExampleSuite(
                selected_mechanism_ref=eref(selected),
                frozen_prediction_register_ref=prediction_ref,
                cases=tuple(example_cases),
            ),
            title="E0-E6 mechanism laboratory",
            summary="Exact benchmark, mechanism, ablation, separator, boundary, and failure cases.",
            created_at=T6,
            artifact_refs=tuple(example_artifact_refs),
        )
        example_ref = eref(example_suite)
        self.assertEqual(example_ref, prospective_example_ref)
        _, lab_snapshot = self._commit_route(
            route_id="lab.micro_examples_and_ablations",
            purpose="research_discovery",
            outputs=(reconciled_prediction_register, example_suite),
            relations=(
                RelationVersion(
                    relation_id="relation.examples_test_predictions",
                    relation_type="tests",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=example_ref,
                    target=prediction_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T6,
                ),
                RelationVersion(
                    relation_id="relation.examples_ablate_selected_mechanism",
                    relation_type="ablates",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=example_ref,
                    target=eref(selected),
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T6,
                ),
                RelationVersion(
                    relation_id="relation.examples_separate_direct_rival",
                    relation_type="separates",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=example_ref,
                    target=eref(rival),
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T6,
                ),
                RelationVersion(
                    relation_id="relation.examples_reconcile_predictions",
                    relation_type="reconciles",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=example_ref,
                    target=reconciled_prediction_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T6,
                ),
            ),
            artifacts=tuple(example_artifacts),
            evidence_refs=(
                question_ref,
                eref(selected),
                eref(rival),
                eref(tournament),
                prediction_ref,
                eref(pre_result_brief),
            ),
            authority_basis=(g1.decision_id,),
            focus_entity_ids=(
                question.entity_id,
                selected.entity_id,
                rival.entity_id,
                tournament.entity_id,
                prediction_register.entity_id,
                pre_result_brief.entity_id,
            ),
            created_at=T6,
        )
        self.assertEqual(
            {case.case_id for case in parse_theory_entity(example_suite).cases},
            {"E0", "E1", "E2", "E3", "E4", "E5", "E6"},
        )
        self.assertEqual(len(lab_snapshot.current_artifacts), 8)
        self.assertEqual(
            lab_snapshot.route_outcomes[-1].route_id,
            "lab.micro_examples_and_ablations",
        )

        argument_graph = self._entity(
            "argument.economic.attention_precision",
            EconomicArgumentGraph(
                selected_mechanism_ref=eref(selected),
                primitive_graph_ref=primitive_ref,
                prediction_register_ref=reconciled_prediction_ref,
                example_suite_ref=example_ref,
                nodes=(
                    EconomicArgumentNode(
                        node_id="argument.precision",
                        kind="primitive",
                        statement="Signal precision x raises conditional signal accuracy.",
                    ),
                    EconomicArgumentNode(
                        node_id="argument.processing_cost",
                        kind="constraint",
                        statement="Processing costs kappa*x^2.",
                    ),
                    EconomicArgumentNode(
                        node_id="argument.processing_margin",
                        kind="margin",
                        statement="The receiver chooses indivisible processing before observing the signal.",
                    ),
                    EconomicArgumentNode(
                        node_id="argument.participation_response",
                        kind="response",
                        statement="The receiver processes iff x/2-kappa*x^2 is nonnegative.",
                    ),
                    EconomicArgumentNode(
                        node_id="argument.accuracy",
                        kind="outcome",
                        statement="Realized accuracy is one half without processing and (1+x)/2 with processing.",
                    ),
                ),
                edges=(
                    EconomicArgumentEdge(
                        edge_id="argument.edge.precision_cost",
                        source_node_id="argument.precision",
                        target_node_id="argument.processing_cost",
                        economic_meaning="A more precise signal is more costly to process.",
                        effect_kind="direct",
                        load_bearing=True,
                        primitive_or_assumption_refs=(primitive_ref,),
                        supporting_case_ids=("E1", "E2"),
                        conclusion_ids=("conclusion.cost_force",),
                    ),
                    EconomicArgumentEdge(
                        edge_id="argument.edge.cost_margin",
                        source_node_id="argument.processing_cost",
                        target_node_id="argument.processing_margin",
                        economic_meaning="Processing cost enters the extensive attention choice.",
                        effect_kind="logical",
                        load_bearing=True,
                        primitive_or_assumption_refs=(primitive_ref,),
                        supporting_case_ids=("E1", "E4", "E5", "E6"),
                        conclusion_ids=("conclusion.attention_threshold",),
                    ),
                    EconomicArgumentEdge(
                        edge_id="argument.edge.margin_response",
                        source_node_id="argument.processing_margin",
                        target_node_id="argument.participation_response",
                        economic_meaning="The sign of processing surplus determines participation.",
                        effect_kind="direct",
                        load_bearing=True,
                        primitive_or_assumption_refs=(eref(selected),),
                        supporting_case_ids=("E1", "E4", "E5", "E6"),
                        conclusion_ids=("conclusion.extensive_margin",),
                    ),
                    EconomicArgumentEdge(
                        edge_id="argument.edge.response_accuracy",
                        source_node_id="argument.participation_response",
                        target_node_id="argument.accuracy",
                        economic_meaning="Participation determines whether conditional information quality reaches the action.",
                        effect_kind="direct",
                        load_bearing=True,
                        primitive_or_assumption_refs=(eref(selected),),
                        supporting_case_ids=("E0", "E1", "E3"),
                        conclusion_ids=("conclusion.reversal",),
                    ),
                    EconomicArgumentEdge(
                        edge_id="argument.edge.direct_information",
                        source_node_id="argument.precision",
                        target_node_id="argument.accuracy",
                        economic_meaning="Conditional on processing, higher precision directly raises accuracy.",
                        effect_kind="direct",
                        load_bearing=True,
                        primitive_or_assumption_refs=(eref(rival),),
                        supporting_case_ids=("E0", "E2", "E3"),
                        conclusion_ids=("conclusion.direct_force",),
                    ),
                ),
            ),
            title="Economic argument graph",
            summary="The direct information force and extensive processing response are kept distinct.",
            created_at=T7,
        )
        argument_ref = eref(argument_graph)
        g2_dossier = self._entity(
            "dossier.g2.attention_precision",
            GateDossier(
                gate_kind="G2_mechanism",
                research_question_ref=question_ref,
                ordered_object_refs=(
                    question_ref,
                    primitive_ref,
                    eref(selected),
                    eref(rival),
                    eref(tournament),
                    reconciled_prediction_ref,
                    example_ref,
                    argument_ref,
                ),
                requirements=(
                    GateRequirement(
                        requirement_id="g2.rival",
                        description="The selected mechanism defeats a serious direct-information rival.",
                        evidence_refs=(eref(selected), eref(rival), eref(tournament)),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g2.prediction",
                        description="Both surviving hypotheses were frozen before examples.",
                        evidence_refs=(reconciled_prediction_ref,),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g2.functional_examples",
                        description="Benchmark, mechanism-on, ablation, separator, boundary, and failure cases are present.",
                        evidence_refs=(example_ref,),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g2.argument_chain",
                        description="Every promoted load-bearing arrow names functional case support.",
                        evidence_refs=(primitive_ref, argument_ref),
                        recorded_condition="evidence_supplied",
                    ),
                ),
                proposed_action="approve",
                rationale=(
                    "The reversal is supported by frozen predictions, a serious rival, exact ablations, separators, and boundary cases without treating examples as proof."
                ),
                prepared_at=T7,
            ),
            title="G2 mechanism dossier",
            summary="Immutable evidence package for human promotion of the economic mechanism.",
            created_at=T7,
        )
        _, promoted = self._commit_route(
            route_id="promote.mechanism",
            purpose="research_discovery",
            outputs=(argument_graph, g2_dossier),
            relations=(
                RelationVersion(
                    relation_id="relation.tournament_promotes_argument",
                    relation_type="promotes",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(tournament),
                    target=argument_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T7,
                ),
                RelationVersion(
                    relation_id="relation.g2_governs_question",
                    relation_type="governs",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(g2_dossier),
                    target=question_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T7,
                ),
                RelationVersion(
                    relation_id="relation.examples_support_argument",
                    relation_type="supports",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=example_ref,
                    target=argument_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T7,
                ),
            ),
            evidence_refs=(
                question_ref,
                primitive_ref,
                eref(selected),
                eref(rival),
                eref(tournament),
                reconciled_prediction_ref,
                example_ref,
            ),
            authority_basis=(g1.decision_id,),
            focus_entity_ids=(
                question.entity_id,
                primitive_graph.entity_id,
                selected.entity_id,
                rival.entity_id,
                tournament.entity_id,
                prediction_register.entity_id,
                example_suite.entity_id,
            ),
            created_at=T7,
        )
        self.assertEqual(promoted.route_outcomes[-1].route_id, "promote.mechanism")

        g2 = Decision(
            decision_id="decision.g2.attention_precision",
            version=1,
            project_id=self.snapshot.project_id,
            decision_kind="G2_mechanism",
            subject_ref=g2_dossier.entity_id,
            scope_ref=question.entity_id,
            question="Approve this exact economic mechanism for formal implementation investment?",
            options=("approve", "revise", "kill"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve the mechanism while preserving its direct-force rival.",
            rationale=(
                "The exact examples discriminate the extensive participation mechanism from direct information and identify indivisibility as load bearing."
            ),
            evidence_refs=(g2_dossier.entity_id,),
            unresolved_risks=(
                "The examples do not prove the quantified characterization.",
                "Novelty and absorption remain unevaluated.",
            ),
            required_authority="L2",
            decider=HUMAN,
            decided_at=T8,
            status="confirmed",
        )
        g2_result = commit_decision(self.layout, g2)
        self.assertEqual(g2_result.status, "committed")
        through_g2 = replay(self.layout)
        self.assertEqual(len(through_g2.chain), 9)
        self.assertEqual(len(through_g2.route_outcomes), 6)
        self.assertEqual(through_g2.current_decisions[g2.decision_id], 1)
        self.assertEqual(len(through_g2.current_artifacts), 8)
        self.assertEqual(through_g2.current_entities[argument_graph.entity_id], 1)
        effective_gate_ids = {
            reference.decision_id
            for reference in through_g2.effective_decisions.values()
        }
        self.assertTrue({g1.decision_id, g2.decision_id}.issubset(effective_gate_ids))

        indivisible_spec_bytes = canonical_json_bytes(
            {
                "model": "F1.binary_attention",
                "state": "theta in {0,1}, prior one half",
                "precision": "0 < x <= 1",
                "signal": "Pr(s=theta|theta,x)=(1+x)/2",
                "attention": "d in {0,1} before observing s",
                "processing_cost": "d*kappa*x^2",
                "action": "a=s if d=1; otherwise either binary action",
                "outcome": "Y=1/2+d*x/2",
                "solution": "d=1 iff x/2-kappa*x^2 >= 0",
            }
        )
        indivisible_registration, indivisible_spec_ref, _ = self._artifact(
            "artifact.formal.indivisible_attention.v1",
            logical_name="Indivisible-attention formal specification v1",
            media_type="application/json",
            data=indivisible_spec_bytes,
            created_at=T9,
        )
        continuous_spec_bytes = canonical_json_bytes(
            {
                "model": "F2.continuous_attention",
                "state": "theta in {0,1}, prior one half",
                "precision": "0 < x <= 1",
                "attention": "e in [0,1] before observing s",
                "processing_cost": "kappa*x^2*e^2/2",
                "outcome": "Y=1/2+e*x/2",
                "solution": "e*=min{1,1/(2*kappa*x)}",
                "boundary": "Y is weakly increasing in x; no strict coarse advantage",
            }
        )
        continuous_registration, continuous_spec_ref, _ = self._artifact(
            "artifact.formal.continuous_attention.v1",
            logical_name="Continuous-attention contrast specification",
            media_type="application/json",
            data=continuous_spec_bytes,
            created_at=T9,
        )
        indivisible_model = self._entity(
            "formal_model.indivisible_attention",
            FormalModel(
                question_ref=question_ref,
                selected_mechanism_ref=eref(selected),
                primitive_graph_ref=primitive_ref,
                formal_objects=(
                    FormalObject(
                        object_id="formal.receiver",
                        symbol="R",
                        object_kind="agent",
                        definition="The receiver who chooses processing and a binary action.",
                        central=True,
                    ),
                    FormalObject(
                        object_id="formal.theta",
                        symbol="theta",
                        object_kind="state",
                        definition="A binary payoff-relevant state in {0,1}.",
                        central=False,
                    ),
                    FormalObject(
                        object_id="formal.prior",
                        symbol="pi",
                        object_kind="belief",
                        definition="The symmetric prior Pr(theta=1)=1/2.",
                        central=False,
                    ),
                    FormalObject(
                        object_id="formal.x",
                        symbol="x",
                        object_kind="parameter",
                        definition="Signal precision in (0,1].",
                        central=True,
                    ),
                    FormalObject(
                        object_id="formal.kappa",
                        symbol="kappa",
                        object_kind="parameter",
                        definition="The positive processing-cost coefficient.",
                        central=True,
                    ),
                    FormalObject(
                        object_id="formal.d",
                        symbol="d",
                        object_kind="choice",
                        definition="The indivisible pre-signal processing choice in {0,1}.",
                        central=True,
                    ),
                    FormalObject(
                        object_id="formal.signal",
                        symbol="s",
                        object_kind="information",
                        definition="A binary signal correct with probability (1+x)/2.",
                        central=True,
                    ),
                    FormalObject(
                        object_id="formal.action",
                        symbol="a",
                        object_kind="choice",
                        definition="A binary action chosen after any processed signal.",
                        central=False,
                    ),
                    FormalObject(
                        object_id="formal.processing_surplus",
                        symbol="Delta(x)",
                        object_kind="payoff",
                        definition="The processing surplus x/2-kappa*x^2.",
                        central=True,
                    ),
                    FormalObject(
                        object_id="formal.accuracy",
                        symbol="Y(x)",
                        object_kind="outcome",
                        definition="Realized probability that a equals theta.",
                        central=True,
                    ),
                ),
                timing=(
                    "Nature draws theta and the information designer fixes x.",
                    "The receiver chooses d before observing the signal.",
                    "If d=1 the receiver observes s and then chooses a; otherwise the receiver chooses without s.",
                ),
                choice_or_strategy_spaces=(
                    "d belongs to {0,1}.",
                    "a belongs to {0,1} after each available information set.",
                ),
                information_and_beliefs=(
                    "The prior is one half on each state.",
                    "Conditional on processing, Pr(s=theta)=(1+x)/2.",
                ),
                feasibility=("0 < x <= 1 and kappa >= 0.",),
                solution_concept="Receiver-optimal processing and action under the stated tie rule.",
                outcome_definitions=(
                    "Accuracy Y(x)=1/2+d*x/2 excludes the processing cost.",
                    "Processing surplus is Delta(x)=x/2-kappa*x^2.",
                ),
                full_specification_ref=indivisible_spec_ref,
            ),
            title="Indivisible-attention implementation",
            summary="A minimal binary model preserving the extensive processing mechanism.",
            created_at=T9,
        )
        continuous_model = self._entity(
            "formal_model.continuous_attention",
            FormalModel(
                question_ref=question_ref,
                selected_mechanism_ref=eref(selected),
                primitive_graph_ref=primitive_ref,
                formal_objects=(
                    FormalObject(
                        object_id="contrast.receiver",
                        symbol="R",
                        object_kind="agent",
                        definition="The receiver with a divisible processing choice.",
                        central=True,
                    ),
                    FormalObject(
                        object_id="contrast.theta",
                        symbol="theta",
                        object_kind="state",
                        definition="The binary payoff-relevant state.",
                        central=False,
                    ),
                    FormalObject(
                        object_id="contrast.x",
                        symbol="x",
                        object_kind="parameter",
                        definition="Signal precision in (0,1].",
                        central=True,
                    ),
                    FormalObject(
                        object_id="contrast.kappa",
                        symbol="kappa",
                        object_kind="parameter",
                        definition="The positive attention-cost coefficient.",
                        central=True,
                    ),
                    FormalObject(
                        object_id="contrast.e",
                        symbol="e",
                        object_kind="choice",
                        definition="A divisible attention choice in [0,1].",
                        central=True,
                    ),
                    FormalObject(
                        object_id="contrast.accuracy",
                        symbol="Y_c(x)",
                        object_kind="outcome",
                        definition="Accuracy 1/2+e*x/2.",
                        central=True,
                    ),
                ),
                timing=(
                    "Nature draws theta and x is fixed.",
                    "The receiver chooses e in [0,1] before the signal.",
                    "The receiver acts after the attenuated signal.",
                ),
                choice_or_strategy_spaces=(
                    "e belongs to [0,1].",
                    "a belongs to {0,1}.",
                ),
                information_and_beliefs=("The prior is symmetric.",),
                feasibility=("0 < x <= 1 and kappa >= 0.",),
                solution_concept="Receiver-optimal continuous attention and binary action.",
                outcome_definitions=(
                    "e*=min{1,1/(2*kappa*x)} when kappa>0.",
                    "Y_c(x)=1/2+min{x/2,1/(4*kappa)}.",
                ),
                full_specification_ref=continuous_spec_ref,
            ),
            title="Continuous-attention contrast",
            summary="A meaningful implementation that weakens indivisibility and removes the strict reversal.",
            created_at=T9,
        )
        implementation_tournament = self._entity(
            "tournament.implementations.attention_precision",
            ImplementationTournament(
                selected_mechanism_ref=eref(selected),
                economic_argument_graph_ref=argument_ref,
                candidate_model_refs=(eref(indivisible_model), eref(continuous_model)),
                comparisons=(
                    ImplementationPairComparison(
                        left_model_ref=eref(indivisible_model),
                        right_model_ref=eref(continuous_model),
                        fidelity_difference=(
                            "The binary model preserves the participation switch; continuous attention smooths it away."
                        ),
                        minimality_difference=(
                            "Both use binary states, but the binary model has one discrete processing decision."
                        ),
                        proof_risk_difference=(
                            "The binary threshold creates endpoint cases; the continuous model needs an interior/corner solution split."
                        ),
                        mapping_transparency_difference=(
                            "d maps directly to processing participation, whereas e mixes participation and intensity."
                        ),
                        theorem_leverage_difference=(
                            "Only the binary model supports a strict coarse-information advantage."
                        ),
                    ),
                ),
                proposed_selected_model_ref=eref(indivisible_model),
                contrast_model_refs=(eref(continuous_model),),
                selection_rationale=(
                    "Indivisible attention is selected because it is the load-bearing economic condition, not because it is algebraically convenient."
                ),
            ),
            title="Formal implementation tournament",
            summary="Indivisible and continuous attention implementations are compared directly.",
            created_at=T9,
        )
        _, implementation_snapshot = self._commit_route(
            route_id="tournament.implementations",
            purpose="research_discovery",
            outputs=(
                indivisible_model,
                continuous_model,
                implementation_tournament,
            ),
            relations=(
                RelationVersion(
                    relation_id="relation.indivisible_compares_continuous",
                    relation_type="compares_to",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(indivisible_model),
                    target=eref(continuous_model),
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T9,
                ),
                RelationVersion(
                    relation_id="relation.indivisible_implements_argument",
                    relation_type="implements",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(indivisible_model),
                    target=argument_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T9,
                ),
                RelationVersion(
                    relation_id="relation.continuous_implements_argument_contrast",
                    relation_type="implements",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(continuous_model),
                    target=argument_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T9,
                ),
                RelationVersion(
                    relation_id="relation.tournament_rejects_continuous_for_headline",
                    relation_type="rejects",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(implementation_tournament),
                    target=eref(continuous_model),
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T9,
                ),
            ),
            artifacts=(
                (indivisible_registration, indivisible_spec_bytes),
                (continuous_registration, continuous_spec_bytes),
            ),
            evidence_refs=(
                question_ref,
                primitive_ref,
                eref(selected),
                argument_ref,
            ),
            authority_basis=(g1.decision_id, g2.decision_id),
            focus_entity_ids=(
                question.entity_id,
                primitive_graph.entity_id,
                selected.entity_id,
                argument_graph.entity_id,
            ),
            created_at=T9,
        )
        self.assertEqual(
            implementation_snapshot.route_outcomes[-1].route_id,
            "tournament.implementations",
        )

        locked_spec_bytes = canonical_json_bytes(
            {
                "model": "F1.binary_attention.locked",
                "state_and_signal": "theta,s in {0,1}; Pr(theta=1)=1/2; Pr(s=theta|x)=(1+x)/2",
                "processing": "d in {0,1} is chosen before s and costs d*kappa*x^2",
                "action": "a=s after processing; without processing accuracy is one half",
                "surplus": "Delta(x)=x/2-kappa*x^2",
                "threshold": "d=1 iff kappa <= 1/(2*x), with processing at equality",
                "accuracy": "Y(x)=1/2+d*x/2",
                "headline_boundary": "Y(ell)>Y(h) iff 1/(2*h)<kappa<=1/(2*ell)",
                "continuous_contrast": "e*=min{1,1/(2*kappa*x)} eliminates a strict coarse advantage",
            }
        )
        locked_registration, locked_spec_ref, _ = self._artifact(
            "artifact.formal.indivisible_attention.locked.v2",
            logical_name="Locked indivisible-attention formal specification v2",
            media_type="application/json",
            data=locked_spec_bytes,
            created_at=T10,
        )
        indivisible_payload = parse_theory_entity(indivisible_model)
        self.assertIsInstance(indivisible_payload, FormalModel)
        locked_model = self._entity(
            indivisible_model.entity_id,
            FormalModel(
                question_ref=question_ref,
                selected_mechanism_ref=eref(selected),
                primitive_graph_ref=primitive_ref,
                formal_objects=(
                    *indivisible_payload.formal_objects,
                    FormalObject(
                        object_id="formal.processing_threshold",
                        symbol="tau(x)",
                        object_kind="constraint",
                        definition="The exact condition kappa <= 1/(2*x) for processing.",
                        central=True,
                    ),
                ),
                timing=indivisible_payload.timing,
                choice_or_strategy_spaces=indivisible_payload.choice_or_strategy_spaces,
                information_and_beliefs=indivisible_payload.information_and_beliefs,
                feasibility=indivisible_payload.feasibility,
                solution_concept=indivisible_payload.solution_concept,
                outcome_definitions=(
                    *indivisible_payload.outcome_definitions,
                    "The strict reversal region is 1/(2*h)<kappa<=1/(2*ell).",
                ),
                full_specification_ref=locked_spec_ref,
            ),
            title=indivisible_model.title,
            summary=indivisible_model.summary,
            created_at=T10,
            version=2,
            supersedes=eref(indivisible_model),
        )
        locked_model_ref = eref(locked_model)
        formalization_map = self._entity(
            "formalization.attention_precision",
            FormalizationMap(
                economic_argument_graph_ref=argument_ref,
                formal_model_ref=locked_model_ref,
                economic_to_formal=(
                    EconomicToFormalEntry(
                        economic_element_id="argument.edge.precision_cost",
                        formal_object_ids=(
                            "formal.x",
                            "formal.kappa",
                            "formal.processing_surplus",
                        ),
                        implementation_statement="x and kappa enter Delta(x)=x/2-kappa*x^2.",
                        witness_refs=(argument_ref, locked_spec_ref),
                    ),
                    EconomicToFormalEntry(
                        economic_element_id="argument.edge.cost_margin",
                        formal_object_ids=(
                            "formal.processing_surplus",
                            "formal.d",
                        ),
                        implementation_statement="The sign of Delta(x) governs the binary choice d.",
                        witness_refs=(argument_ref, locked_spec_ref),
                    ),
                    EconomicToFormalEntry(
                        economic_element_id="argument.edge.margin_response",
                        formal_object_ids=(
                            "formal.d",
                            "formal.processing_threshold",
                        ),
                        implementation_statement="d switches at kappa=1/(2*x), including the stated tie rule.",
                        witness_refs=(argument_ref, locked_spec_ref),
                    ),
                    EconomicToFormalEntry(
                        economic_element_id="argument.edge.response_accuracy",
                        formal_object_ids=(
                            "formal.d",
                            "formal.signal",
                            "formal.accuracy",
                        ),
                        implementation_statement="Y(x)=1/2+d*x/2 maps participation into accuracy.",
                        witness_refs=(argument_ref, locked_spec_ref),
                    ),
                    EconomicToFormalEntry(
                        economic_element_id="argument.edge.direct_information",
                        formal_object_ids=(
                            "formal.x",
                            "formal.signal",
                            "formal.accuracy",
                        ),
                        implementation_statement="Conditional on d=1, x raises signal and action accuracy.",
                        witness_refs=(argument_ref, locked_spec_ref),
                    ),
                ),
                formal_to_economic=(
                    FormalToEconomicEntry(
                        formal_object_id="formal.receiver",
                        economic_identity="The receiver owning the processing margin.",
                        research_job="Locates the endogenous attention decision.",
                        economic_element_ids=("argument.processing_margin",),
                    ),
                    FormalToEconomicEntry(
                        formal_object_id="formal.x",
                        economic_identity="Signal precision and direct informativeness.",
                        research_job="Moves both the direct accuracy force and processing cost.",
                        economic_element_ids=(
                            "argument.precision",
                            "argument.edge.direct_information",
                        ),
                    ),
                    FormalToEconomicEntry(
                        formal_object_id="formal.kappa",
                        economic_identity="Marginal difficulty of processing precision.",
                        research_job="Determines where processing participation switches.",
                        economic_element_ids=("argument.processing_cost",),
                    ),
                    FormalToEconomicEntry(
                        formal_object_id="formal.d",
                        economic_identity="Indivisible information-processing participation.",
                        research_job="Creates the load-bearing extensive margin.",
                        economic_element_ids=(
                            "argument.processing_margin",
                            "argument.participation_response",
                        ),
                    ),
                    FormalToEconomicEntry(
                        formal_object_id="formal.signal",
                        economic_identity="The information used by the action when processing occurs.",
                        research_job="Carries conditional precision into the action.",
                        economic_element_ids=("argument.edge.direct_information",),
                    ),
                    FormalToEconomicEntry(
                        formal_object_id="formal.processing_surplus",
                        economic_identity="Net private value of processing.",
                        research_job="Translates precision and cost into participation.",
                        economic_element_ids=(
                            "argument.processing_cost",
                            "argument.participation_response",
                        ),
                    ),
                    FormalToEconomicEntry(
                        formal_object_id="formal.accuracy",
                        economic_identity="Realized match probability between action and state.",
                        research_job="Measures the consequence to be explained.",
                        economic_element_ids=("argument.accuracy",),
                    ),
                    FormalToEconomicEntry(
                        formal_object_id="formal.processing_threshold",
                        economic_identity="The boundary between using and ignoring information.",
                        research_job="Pins down the exact reversal interval and endpoints.",
                        economic_element_ids=("argument.edge.cost_margin",),
                    ),
                ),
            ),
            title="Bidirectional economic-formal map",
            summary="Every load-bearing economic arrow and central formal object is mapped.",
            created_at=T10,
        )
        formalization_ref = eref(formalization_map)
        assumption_map = self._entity(
            "assumptions.attention_precision",
            AssumptionMap(
                formal_model_ref=locked_model_ref,
                formalization_map_ref=formalization_ref,
                assumptions=(
                    AssumptionRecord(
                        assumption_id="assumption.binary_attention",
                        exact_content="Processing is indivisible: d belongs to {0,1}.",
                        quantifiers=("For every admissible x, d is binary.",),
                        economic_interpretation="The receiver either uses the signal or ignores it.",
                        foundation="primitive",
                        roles=("mechanism", "domain"),
                        argument_edge_ids=(
                            "argument.edge.margin_response",
                            "argument.edge.response_accuracy",
                        ),
                        satisfying_case_ids=("E0", "E1", "E4", "E5", "E6"),
                        weakening_attempts=(
                            "Allow e in [0,1] and solve the continuous-attention contrast.",
                        ),
                        violation_attempts=(
                            "The continuous contrast eliminates a strict coarse advantage.",
                        ),
                        scope_cost="The theorem does not extend to divisible attention.",
                        necessity_status="result_necessary",
                        necessity_evidence_refs=(
                            example_ref,
                            eref(continuous_model),
                        ),
                    ),
                    AssumptionRecord(
                        assumption_id="assumption.precision_linked_cost",
                        exact_content="Processing precision x costs kappa*x^2.",
                        quantifiers=("For every x in (0,1] and kappa>=0.",),
                        economic_interpretation="More precise signals require greater processing effort.",
                        foundation="primitive",
                        roles=("mechanism", "sign"),
                        argument_edge_ids=(
                            "argument.edge.precision_cost",
                            "argument.edge.cost_margin",
                        ),
                        satisfying_case_ids=("E1", "E3", "E4", "E5"),
                        weakening_attempts=("Replace kappa*x^2 by a common processing cost.",),
                        violation_attempts=("E2 restores monotone accuracy under constant cost.",),
                        scope_cost="The result needs precision to affect processing participation.",
                        necessity_status="result_necessary",
                        necessity_evidence_refs=(example_ref, argument_ref),
                    ),
                    AssumptionRecord(
                        assumption_id="assumption.process_at_indifference",
                        exact_content="The receiver processes when Delta(x)=0.",
                        quantifiers=("At every exact zero-surplus endpoint.",),
                        economic_interpretation="The selection rule determines endpoint inclusion only.",
                        foundation="reduced_form",
                        roles=("selection",),
                        argument_edge_ids=("argument.edge.margin_response",),
                        satisfying_case_ids=("E4", "E5"),
                        weakening_attempts=("Select non-processing at indifference.",),
                        violation_attempts=("The hidden probes flip endpoint inclusion but not the interior mechanism.",),
                        scope_cost="Boundary inequalities depend on the tie rule.",
                        necessity_status="not_result_necessary",
                    ),
                    AssumptionRecord(
                        assumption_id="assumption.binary_symmetric_state",
                        exact_content="The state and action are binary and the prior is one half.",
                        quantifiers=("theta and a belong to {0,1}.",),
                        economic_interpretation="Accuracy has a transparent one-half no-information benchmark.",
                        foundation="primitive",
                        roles=("domain", "tractability"),
                        argument_edge_ids=("argument.edge.direct_information",),
                        satisfying_case_ids=("E0", "E1"),
                        weakening_attempts=("Allow asymmetric priors and more than two actions.",),
                        scope_cost="The first characterization is deliberately binary and symmetric.",
                        necessity_status="unknown",
                    ),
                ),
            ),
            title="Economic and proof assumption map",
            summary="Load-bearing, selection, domain, and tractability assumptions are separated.",
            created_at=T10,
        )
        assumption_ref = eref(assumption_map)
        g3_dossier = self._entity(
            "dossier.g3.attention_precision",
            GateDossier(
                gate_kind="G3_formal_base",
                research_question_ref=question_ref,
                ordered_object_refs=(
                    question_ref,
                    primitive_ref,
                    eref(selected),
                    argument_ref,
                    eref(continuous_model),
                    eref(implementation_tournament),
                    locked_model_ref,
                    formalization_ref,
                    assumption_ref,
                ),
                requirements=(
                    GateRequirement(
                        requirement_id="g3.implementation_contrast",
                        description="The selected indivisible model is compared with a meaningful continuous-attention contrast.",
                        evidence_refs=(
                            eref(implementation_tournament),
                            eref(continuous_model),
                        ),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g3.mapping_coverage",
                        description="Every load-bearing economic arrow and every central formal object has a valid bidirectional map.",
                        evidence_refs=(argument_ref, locked_model_ref, formalization_ref),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g3.assumptions",
                        description="Mechanism, selection, domain, and tractability assumptions are separated with scope costs.",
                        evidence_refs=(assumption_ref,),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g3.boundary",
                        description="The locked specification states the exact threshold and continuous-attention boundary.",
                        evidence_refs=(locked_spec_ref,),
                        recorded_condition="evidence_supplied",
                    ),
                ),
                proposed_action="approve",
                rationale=(
                    "The selected formal base preserves every load-bearing economic force, exposes indivisibility as necessary, and records the continuous-attention boundary."
                ),
                prepared_at=T10,
            ),
            title="G3 formal-base dossier",
            summary="Immutable formal implementation, mapping, and assumption evidence for human review.",
            created_at=T10,
        )
        _, formal_base_snapshot = self._commit_route(
            route_id="promote.formal_base",
            purpose="research_discovery",
            outputs=(locked_model, formalization_map, assumption_map, g3_dossier),
            relations=(
                RelationVersion(
                    relation_id="relation.locked_model_implements_argument",
                    relation_type="implements",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=locked_model_ref,
                    target=argument_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T10,
                ),
                RelationVersion(
                    relation_id="relation.formalization_maps_to_locked_model",
                    relation_type="maps_to",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=formalization_ref,
                    target=locked_model_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T10,
                ),
                RelationVersion(
                    relation_id="relation.g3_governs_question",
                    relation_type="governs",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(g3_dossier),
                    target=question_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T10,
                ),
                RelationVersion(
                    relation_id="relation.assumptions_support_mapping",
                    relation_type="supports",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=assumption_ref,
                    target=formalization_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T10,
                ),
            ),
            artifacts=((locked_registration, locked_spec_bytes),),
            evidence_refs=(
                question_ref,
                primitive_ref,
                eref(selected),
                argument_ref,
                eref(indivisible_model),
                eref(continuous_model),
                eref(implementation_tournament),
            ),
            authority_basis=(g1.decision_id, g2.decision_id),
            focus_entity_ids=(
                question.entity_id,
                primitive_graph.entity_id,
                selected.entity_id,
                argument_graph.entity_id,
                indivisible_model.entity_id,
                continuous_model.entity_id,
                implementation_tournament.entity_id,
            ),
            created_at=T10,
        )
        self.assertEqual(
            formal_base_snapshot.route_outcomes[-1].route_id,
            "promote.formal_base",
        )

        g3 = Decision(
            decision_id="decision.g3.attention_precision",
            version=1,
            project_id=self.snapshot.project_id,
            decision_kind="G3_formal_base",
            subject_ref=g3_dossier.entity_id,
            scope_ref=question.entity_id,
            question="Approve this exact formal base for theorem and proof investment?",
            options=("approve", "revise", "kill"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve the mapped indivisible-attention formal base.",
            rationale=(
                "Every load-bearing economic arrow has a formal witness, every central formal object has an economic interpretation, and the continuous contrast identifies the exact scope cost."
            ),
            evidence_refs=(g3_dossier.entity_id,),
            unresolved_risks=(
                "Formal claims and universal proof obligations have not yet been created.",
                "Novelty and absorption remain unevaluated.",
            ),
            required_authority="L2",
            decider=HUMAN,
            decided_at=T11,
            status="confirmed",
        )
        g3_result = commit_decision(self.layout, g3)
        self.assertEqual(g3_result.status, "committed")
        through_g3 = replay(self.layout)
        self.assertEqual(len(through_g3.chain), 12)
        self.assertEqual(len(through_g3.route_outcomes), 8)
        self.assertEqual(through_g3.current_decisions[g3.decision_id], 1)
        self.assertEqual(len(through_g3.current_artifacts), 11)
        self.assertEqual(through_g3.current_entities[locked_model.entity_id], 2)
        self.assertEqual(through_g3.current_entities[formalization_map.entity_id], 1)
        effective_gate_ids = {
            reference.decision_id
            for reference in through_g3.effective_decisions.values()
        }
        self.assertTrue(
            {g1.decision_id, g2.decision_id, g3.decision_id}.issubset(
                effective_gate_ids
            )
        )

        claim_graph_ref = EntityVersionRef(
            entity_id="claims.attention_precision", version=1
        )
        headline_obligation_ref = EntityVersionRef(
            entity_id="obligation.headline_reversal", version=1
        )
        boundary_obligation_ref = EntityVersionRef(
            entity_id="obligation.tie_boundaries", version=1
        )
        ablation_obligation_ref = EntityVersionRef(
            entity_id="obligation.constant_cost_ablation", version=1
        )
        claim_graph = self._entity(
            claim_graph_ref.entity_id,
            ClaimGraph(
                formal_model_ref=locked_model_ref,
                formalization_map_ref=formalization_ref,
                assumption_map_ref=assumption_ref,
                claims=(
                    ClaimNode(
                        claim_id="claim.headline_reversal",
                        archetype="comparative_statics_threshold",
                        scientific_job="headline",
                        formal_statement=(
                            "For 0<ell<h<=1 with processing at indifference, Y(ell)>Y(h) iff 1/(2*h)<kappa<=1/(2*ell)."
                        ),
                        domain="Binary symmetric state, action, signal, and indivisible processing.",
                        quantifiers=(
                            "For every 0<ell<h<=1.",
                            "For every kappa>=0.",
                        ),
                        assumption_ids=(
                            "assumption.binary_attention",
                            "assumption.precision_linked_cost",
                            "assumption.process_at_indifference",
                            "assumption.binary_symmetric_state",
                        ),
                        semantic_translation=(
                            "A coarser signal yields higher realized accuracy exactly when only it remains worth processing."
                        ),
                        dependency_refs=(
                            argument_ref,
                            locked_model_ref,
                            formalization_ref,
                            reconciled_prediction_ref,
                        ),
                        mechanism_ref=eref(selected),
                        proof_obligation_refs=(headline_obligation_ref,),
                        verification_record_refs=(),
                        boundary_case_ids=("E4", "E5", "E6"),
                    ),
                    ClaimNode(
                        claim_id="claim.tie_boundaries",
                        archetype="characterization_bounds",
                        scientific_job="boundary",
                        formal_statement=(
                            "Changing the tie rule changes endpoint inclusion: the lower endpoint enters and the upper endpoint exits under non-processing at indifference."
                        ),
                        domain="The same binary model evaluated at exact zero-surplus endpoints.",
                        quantifiers=(
                            "At kappa=1/(2*h).",
                            "At kappa=1/(2*ell).",
                        ),
                        assumption_ids=(
                            "assumption.binary_attention",
                            "assumption.precision_linked_cost",
                            "assumption.binary_symmetric_state",
                        ),
                        semantic_translation=(
                            "The economic mechanism is interiorly stable, while exact boundary inequalities depend on selection."
                        ),
                        dependency_refs=(locked_model_ref, example_ref),
                        mechanism_ref=eref(selected),
                        proof_obligation_refs=(boundary_obligation_ref,),
                        verification_record_refs=(),
                        boundary_case_ids=("E4", "E5"),
                    ),
                    ClaimNode(
                        claim_id="claim.constant_cost_ablation",
                        archetype="design_implementation_impossibility",
                        scientific_job="necessity",
                        formal_statement=(
                            "With a common processing cost independent of x, no strict coarse-information advantage is generated by processing participation."
                        ),
                        domain="Binary attention with the precision-linked cost channel removed.",
                        quantifiers=(
                            "For every 0<ell<h<=1.",
                            "For every common processing cost c>=0.",
                        ),
                        assumption_ids=(
                            "assumption.binary_attention",
                            "assumption.binary_symmetric_state",
                        ),
                        semantic_translation=(
                            "Endogenous attention alone is insufficient; precision must alter the participation incentive."
                        ),
                        dependency_refs=(argument_ref, example_ref),
                        mechanism_ref=eref(selected),
                        proof_obligation_refs=(ablation_obligation_ref,),
                        verification_record_refs=(),
                        boundary_case_ids=("E2",),
                    ),
                ),
                dependency_edges=(
                    ClaimDependencyEdge(
                        source_claim_id="claim.headline_reversal",
                        target_claim_id="claim.tie_boundaries",
                        dependency_kind="scope",
                    ),
                    ClaimDependencyEdge(
                        source_claim_id="claim.headline_reversal",
                        target_claim_id="claim.constant_cost_ablation",
                        dependency_kind="mechanism",
                    ),
                ),
                contribution_spine=(
                    "claim.headline_reversal",
                    "claim.constant_cost_ablation",
                ),
            ),
            title="Scoped claim and boundary graph",
            summary="Headline characterization, endpoint scope, and cost-channel necessity are separated.",
            created_at=T12,
        )
        self.assertEqual(eref(claim_graph), claim_graph_ref)
        headline_obligation = self._entity(
            headline_obligation_ref.entity_id,
            ProofObligation(
                claim_graph_ref=claim_graph_ref,
                claim_id="claim.headline_reversal",
                obligation_id="PO.headline_reversal",
                statement=(
                    "Derive both processing thresholds and prove all outcome orderings on and off the interval."
                ),
                burden="comparative_static",
                quantifier_scope="All 0<ell<h<=1 and kappa>=0 under the stated tie rule.",
                assumption_ids=(
                    "assumption.binary_attention",
                    "assumption.precision_linked_cost",
                    "assumption.process_at_indifference",
                    "assumption.binary_symmetric_state",
                ),
                admissible_methods=("analytic_proof", "formal_proof"),
            ),
            title="Headline reversal proof obligation",
            summary="Universal analytic characterization burden.",
            created_at=T12,
        )
        boundary_obligation = self._entity(
            boundary_obligation_ref.entity_id,
            ProofObligation(
                claim_graph_ref=claim_graph_ref,
                claim_id="claim.tie_boundaries",
                obligation_id="PO.tie_boundaries",
                statement="Check both exact endpoints under both processing tie rules.",
                burden="boundary",
                quantifier_scope="The lower and upper zero-surplus boundaries.",
                assumption_ids=(
                    "assumption.binary_attention",
                    "assumption.precision_linked_cost",
                    "assumption.binary_symmetric_state",
                ),
                admissible_methods=("analytic_proof", "counterexample"),
            ),
            title="Tie-rule boundary obligation",
            summary="Exact endpoint inclusion and exclusion burden.",
            created_at=T12,
        )
        ablation_obligation = self._entity(
            ablation_obligation_ref.entity_id,
            ProofObligation(
                claim_graph_ref=claim_graph_ref,
                claim_id="claim.constant_cost_ablation",
                obligation_id="PO.constant_cost_ablation",
                statement=(
                    "Show that a common processing cost preserves weak monotonicity in signal precision."
                ),
                burden="necessity",
                quantifier_scope="All ordered precisions and all common nonnegative costs.",
                assumption_ids=(
                    "assumption.binary_attention",
                    "assumption.binary_symmetric_state",
                ),
                admissible_methods=("analytic_proof", "counterexample"),
            ),
            title="Constant-cost ablation obligation",
            summary="Necessity of the precision-linked processing-cost channel.",
            created_at=T12,
        )
        obligation_refs = (
            headline_obligation_ref,
            boundary_obligation_ref,
            ablation_obligation_ref,
        )
        _, claims_snapshot = self._commit_route(
            route_id="discover.claims_and_boundaries",
            purpose="research_discovery",
            outputs=(
                claim_graph,
                headline_obligation,
                boundary_obligation,
                ablation_obligation,
            ),
            relations=(
                RelationVersion(
                    relation_id="relation.assumptions_bound_claims",
                    relation_type="bounds",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=assumption_ref,
                    target=claim_graph_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T12,
                ),
                RelationVersion(
                    relation_id="relation.formalization_entails_claims",
                    relation_type="entails",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=formalization_ref,
                    target=claim_graph_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T12,
                ),
                *(
                    RelationVersion(
                        relation_id=f"relation.claims_require_{index}",
                        relation_type="requires",
                        version=1,
                        project_id=self.snapshot.project_id,
                        source=claim_graph_ref,
                        target=obligation_ref,
                        dependency_mode="trace_only",
                        scope_ref=question.entity_id,
                        created_at=T12,
                    )
                    for index, obligation_ref in enumerate(obligation_refs, start=1)
                ),
            ),
            evidence_refs=(
                question_ref,
                assumption_ref,
                argument_ref,
                locked_model_ref,
                formalization_ref,
                eref(selected),
            ),
            authority_basis=(g1.decision_id, g2.decision_id, g3.decision_id),
            focus_entity_ids=(
                question.entity_id,
                assumption_map.entity_id,
                argument_graph.entity_id,
                locked_model.entity_id,
                formalization_map.entity_id,
                selected.entity_id,
            ),
            created_at=T12,
        )
        self.assertEqual(
            claims_snapshot.route_outcomes[-1].route_id,
            "discover.claims_and_boundaries",
        )

        headline_proof_bytes = canonical_json_bytes(
            {
                "obligation": "PO.headline_reversal",
                "steps": [
                    "Delta(x)=x/2-kappa*x^2=x*(1/2-kappa*x)",
                    "d(x)=1 iff kappa<=1/(2*x)",
                    "because ell<h, 1/(2*h)<1/(2*ell)",
                    "Y(ell)>Y(h) exactly when d(ell)=1 and d(h)=0",
                    "therefore 1/(2*h)<kappa<=1/(2*ell)",
                ],
                "scope": "0<ell<h<=1; process at indifference",
            }
        )
        headline_proof_registration, headline_proof_ref, _ = self._artifact(
            "artifact.proof.headline_reversal",
            logical_name="Analytic proof of the headline reversal",
            media_type="application/json",
            data=headline_proof_bytes,
            created_at=T13,
        )
        boundary_proof_bytes = canonical_json_bytes(
            {
                "obligation": "PO.tie_boundaries",
                "process_at_indifference": {
                    "lower": "no strict reversal",
                    "upper": "strict reversal",
                },
                "do_not_process_at_indifference": {
                    "lower": "strict reversal",
                    "upper": "no strict reversal",
                },
                "interpretation": "tie-breaking changes endpoint inclusion, not the interior mechanism",
            }
        )
        boundary_proof_registration, boundary_proof_ref, _ = self._artifact(
            "artifact.proof.tie_boundaries",
            logical_name="Endpoint and counterexample audit",
            media_type="application/json",
            data=boundary_proof_bytes,
            created_at=T13,
        )
        ablation_proof_bytes = canonical_json_bytes(
            {
                "obligation": "PO.constant_cost_ablation",
                "surplus": "Delta_c(x)=x/2-c",
                "monotonicity": "Delta_c(x) is increasing in x",
                "participation": "if ell is processed then h is processed",
                "outcome": "higher h cannot have lower accuracy than ell",
                "conclusion": "a common cost cannot create a strict coarse-information advantage",
            }
        )
        ablation_proof_registration, ablation_proof_ref, _ = self._artifact(
            "artifact.proof.constant_cost_ablation",
            logical_name="Analytic constant-cost ablation proof",
            media_type="application/json",
            data=ablation_proof_bytes,
            created_at=T13,
        )
        interpretation_bytes = canonical_json_bytes(
            {
                "formal_claim": "exact processing-threshold characterization",
                "economic_translation": (
                    "precision has a direct accuracy benefit and an opposing extensive-processing effect"
                ),
                "prohibited_translation": [
                    "accuracy is welfare",
                    "coarse information is always better",
                    "the reversal survives divisible attention",
                ],
            }
        )
        interpretation_registration, interpretation_ref, _ = self._artifact(
            "artifact.verification.economic_interpretation",
            logical_name="Independent economic interpretation audit",
            media_type="application/json",
            data=interpretation_bytes,
            created_at=T13,
        )
        verifier = Actor(kind="agent", actor_id="gold.independent.verifier")
        headline_record = self._entity(
            "verification.headline_reversal",
            VerificationRecord(
                obligation_ref=headline_obligation_ref,
                claim_graph_ref=claim_graph_ref,
                formal_model_ref=locked_model_ref,
                assumption_map_ref=assumption_ref,
                verifier=verifier,
                method="analytic_proof",
                outcome="discharged",
                checked_refs=(
                    headline_obligation_ref,
                    claim_graph_ref,
                    locked_model_ref,
                    assumption_ref,
                    formalization_ref,
                ),
                evidence_refs=(headline_proof_ref,),
                limitations=(
                    "The proof establishes accuracy, not welfare, and retains the binary-attention scope."
                ),
                checked_at=T13,
            ),
            title="Independent headline verification",
            summary="Analytic verification of the exact reversal interval.",
            created_at=T13,
        )
        boundary_record = self._entity(
            "verification.tie_boundaries",
            VerificationRecord(
                obligation_ref=boundary_obligation_ref,
                claim_graph_ref=claim_graph_ref,
                formal_model_ref=locked_model_ref,
                assumption_map_ref=assumption_ref,
                verifier=verifier,
                method="analytic_proof",
                outcome="discharged",
                checked_refs=(
                    boundary_obligation_ref,
                    claim_graph_ref,
                    locked_model_ref,
                    assumption_ref,
                    example_ref,
                ),
                evidence_refs=(boundary_proof_ref,),
                limitations="Endpoint inclusion changes with the exact tie rule.",
                checked_at=T13,
            ),
            title="Independent boundary verification",
            summary="Both endpoints and both tie rules are checked.",
            created_at=T13,
        )
        ablation_record = self._entity(
            "verification.constant_cost_ablation",
            VerificationRecord(
                obligation_ref=ablation_obligation_ref,
                claim_graph_ref=claim_graph_ref,
                formal_model_ref=locked_model_ref,
                assumption_map_ref=assumption_ref,
                verifier=verifier,
                method="analytic_proof",
                outcome="discharged",
                checked_refs=(
                    ablation_obligation_ref,
                    claim_graph_ref,
                    locked_model_ref,
                    assumption_ref,
                    example_ref,
                ),
                evidence_refs=(ablation_proof_ref,),
                limitations=(
                    "The ablation proves necessity of a precision-linked participation channel within this binary environment."
                ),
                checked_at=T13,
            ),
            title="Independent ablation verification",
            summary="Analytic monotonicity under a common processing cost.",
            created_at=T13,
        )
        verification_record_refs = (
            eref(headline_record),
            eref(boundary_record),
            eref(ablation_record),
        )
        verification_bundle = self._entity(
            "verification.bundle.attention_precision",
            VerificationBundle(
                claim_graph_ref=claim_graph_ref,
                proof_obligation_refs=obligation_refs,
                verification_record_refs=verification_record_refs,
                interpretation_evidence_refs=(
                    interpretation_ref,
                    argument_ref,
                    formalization_ref,
                ),
                counterexample_evidence_refs=(
                    boundary_proof_ref,
                    ablation_proof_ref,
                ),
            ),
            title="Complete verification bundle",
            summary="Every obligation, boundary, and economic translation is independently checked.",
            created_at=T13,
        )
        verification_bundle_ref = eref(verification_bundle)
        verification_artifacts = (
            (headline_proof_registration, headline_proof_bytes),
            (boundary_proof_registration, boundary_proof_bytes),
            (ablation_proof_registration, ablation_proof_bytes),
            (interpretation_registration, interpretation_bytes),
        )
        _, verified_snapshot = self._commit_route(
            route_id="verify.claims_proofs_and_interpretation",
            purpose="research_verification",
            outputs=(
                headline_record,
                boundary_record,
                ablation_record,
                verification_bundle,
            ),
            relations=(
                *(
                    RelationVersion(
                        relation_id=f"relation.verification_{index}_verifies_obligation",
                        relation_type="verifies",
                        version=1,
                        project_id=self.snapshot.project_id,
                        source=record_ref,
                        target=obligation_ref,
                        dependency_mode="trace_only",
                        scope_ref=question.entity_id,
                        created_at=T13,
                    )
                    for index, (record_ref, obligation_ref) in enumerate(
                        zip(verification_record_refs, obligation_refs), start=1
                    )
                ),
                RelationVersion(
                    relation_id="relation.verification_bundle_supports_claims",
                    relation_type="supports",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=verification_bundle_ref,
                    target=claim_graph_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T13,
                ),
            ),
            artifacts=verification_artifacts,
            evidence_refs=(
                question_ref,
                assumption_ref,
                claim_graph_ref,
                locked_model_ref,
                *obligation_refs,
            ),
            authority_basis=(g1.decision_id, g2.decision_id, g3.decision_id),
            focus_entity_ids=(
                question.entity_id,
                assumption_map.entity_id,
                claim_graph.entity_id,
                locked_model.entity_id,
                headline_obligation.entity_id,
                boundary_obligation.entity_id,
                ablation_obligation.entity_id,
            ),
            created_at=T13,
        )
        self.assertEqual(
            verified_snapshot.route_outcomes[-1].route_id,
            "verify.claims_proofs_and_interpretation",
        )

        literature_bytes = canonical_json_bytes(
            {
                "document": "Synthetic closest-theory control comparator",
                "access": "full_text development fixture",
                "verified_results": [
                    "A generic adoption project is undertaken iff its benefit exceeds its cost.",
                    "Conditional output rises with project quality when adoption is fixed.",
                    "The comparator permits a divisible adoption intensity and does not derive the binary information-use reversal interval.",
                ],
                "purpose": (
                    "Development control only; the sealed exact absorber is withheld for the later mutation test."
                ),
            }
        )
        literature_registration, literature_artifact_ref, _ = self._artifact(
            "artifact.literature.closest_control",
            logical_name="Verified full-text closest-theory control",
            media_type="application/json",
            data=literature_bytes,
            created_at=T14,
        )
        literature_evidence = self._entity(
            "literature.attention_precision.control",
            LiteratureEvidence(
                question_ref=question_ref,
                assertions=(
                    LiteratureAssertion(
                        assertion_id="literature.adoption_threshold",
                        assertion=(
                            "The comparator contains a generic benefit-cost adoption threshold."
                        ),
                        source_locator="fixture:closest_control#threshold",
                        access_status="full_text",
                        evidence_ref=literature_artifact_ref,
                        verification_status="source_verified",
                    ),
                    LiteratureAssertion(
                        assertion_id="literature.divisible_intensity",
                        assertion=(
                            "The comparator allows divisible intensity and does not establish the binary attention reversal boundary."
                        ),
                        source_locator="fixture:closest_control#scope",
                        access_status="full_text",
                        evidence_ref=literature_artifact_ref,
                        verification_status="source_verified",
                    ),
                ),
            ),
            title="Verified closest-theory evidence",
            summary="Full-text control evidence for primitive-by-primitive comparison.",
            created_at=T14,
        )
        literature_ref = eref(literature_evidence)
        first_mapping_failure = (
            "Assumptions: the verified control comparator allows divisible intensity and lacks the indivisible information-use margin that generates the strict reversal."
        )
        closest_theory_map = self._entity(
            "closest_theory.attention_precision.control",
            ClosestTheoryMap(
                claim_graph_ref=claim_graph_ref,
                literature_evidence_ref=literature_ref,
                comparator_label="Verified divisible-adoption control comparator",
                dimensions=(
                    ClosestTheoryDimension(
                        dimension="benchmark",
                        project_side="No processing gives accuracy one half.",
                        comparator_side="No adoption gives baseline output.",
                        translation="Ignoring information maps to non-adoption.",
                        mapping_status="exact",
                        evidence_refs=(literature_artifact_ref, benchmark_ref),
                    ),
                    ClosestTheoryDimension(
                        dimension="primitives",
                        project_side="Precision changes conditional accuracy and processing cost.",
                        comparator_side="Project quality changes benefit and cost.",
                        translation="Precision maps to project quality.",
                        mapping_status="standard_argument",
                        evidence_refs=(literature_artifact_ref, primitive_ref),
                    ),
                    ClosestTheoryDimension(
                        dimension="timing",
                        project_side="Processing is chosen before the signal is observed.",
                        comparator_side="Adoption is chosen before project output realizes.",
                        translation="Both decisions precede the payoff-relevant realization.",
                        mapping_status="exact",
                        evidence_refs=(literature_artifact_ref, locked_model_ref),
                    ),
                    ClosestTheoryDimension(
                        dimension="solution_concept",
                        project_side="Receiver-optimal information processing.",
                        comparator_side="Privately optimal project adoption.",
                        translation="Both maximize a private benefit minus cost.",
                        mapping_status="standard_argument",
                        evidence_refs=(literature_artifact_ref, locked_model_ref),
                    ),
                    ClosestTheoryDimension(
                        dimension="assumptions",
                        project_side="Processing is indivisible and precision-linked.",
                        comparator_side="Adoption intensity is divisible in the verified control.",
                        translation="No exact translation preserves the load-bearing binary margin.",
                        mapping_status="fails",
                        evidence_refs=(literature_artifact_ref, assumption_ref),
                    ),
                    ClosestTheoryDimension(
                        dimension="quantifiers",
                        project_side="All ordered ell<h and nonnegative kappa.",
                        comparator_side="All project qualities and admissible costs.",
                        translation="Both characterize a parameterized threshold family.",
                        mapping_status="standard_argument",
                        evidence_refs=(literature_artifact_ref, claim_graph_ref),
                    ),
                    ClosestTheoryDimension(
                        dimension="formal_result",
                        project_side="Exact interval in which coarse accuracy exceeds precise accuracy.",
                        comparator_side="A generic monotone adoption threshold.",
                        translation="The adoption threshold alone does not imply the reversal ordering.",
                        mapping_status="fails",
                        evidence_refs=(literature_artifact_ref, claim_graph_ref),
                    ),
                    ClosestTheoryDimension(
                        dimension="economic_lesson",
                        project_side="Information quality changes whether information is used.",
                        comparator_side="Project quality changes divisible investment intensity.",
                        translation="The comparator lacks the conflict between direct informativeness and discrete use.",
                        mapping_status="fails",
                        evidence_refs=(literature_artifact_ref, argument_ref),
                    ),
                ),
                classification="different_mechanism",
                first_mapping_failure=first_mapping_failure,
            ),
            title="Eight-dimensional closest-theory map",
            summary="The first verified mapping failure occurs at the indivisible information-use assumption.",
            created_at=T14,
        )
        closest_theory_ref = eref(closest_theory_map)
        absorption_assessment = self._entity(
            "absorption.attention_precision.control",
            AbsorptionAssessment(
                closest_theory_map_ref=closest_theory_ref,
                central_claim_graph_ref=claim_graph_ref,
                central_claim_id="claim.headline_reversal",
                outcome="nonabsorbed",
                rationale=(
                    "The full-text control comparator maps generic participation thresholds but fails at the load-bearing indivisible information-use margin and the exact reversal result."
                ),
                standard_argument_refs=(literature_artifact_ref,),
                first_mapping_failure=first_mapping_failure,
                recommended_route="proceed",
            ),
            title="Control absorption assessment",
            summary="The development control is nonabsorbed pending the sealed-comparator mutation.",
            created_at=T14,
        )
        absorption_ref = eref(absorption_assessment)
        _, audited_snapshot = self._commit_route(
            route_id="audit.assumptions_generality_and_absorption",
            purpose="research_verification",
            outputs=(
                literature_evidence,
                closest_theory_map,
                absorption_assessment,
            ),
            relations=(
                RelationVersion(
                    relation_id="relation.closest_compares_to_literature",
                    relation_type="compares_to",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=closest_theory_ref,
                    target=literature_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T14,
                ),
                RelationVersion(
                    relation_id="relation.closest_maps_to_claim_graph",
                    relation_type="maps_to",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=closest_theory_ref,
                    target=claim_graph_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T14,
                ),
            ),
            artifacts=((literature_registration, literature_bytes),),
            evidence_refs=(
                question_ref,
                assumption_ref,
                claim_graph_ref,
                locked_model_ref,
                verification_bundle_ref,
            ),
            authority_basis=(g1.decision_id, g2.decision_id, g3.decision_id),
            focus_entity_ids=(
                question.entity_id,
                assumption_map.entity_id,
                claim_graph.entity_id,
                locked_model.entity_id,
                verification_bundle.entity_id,
            ),
            created_at=T14,
        )
        self.assertEqual(
            audited_snapshot.route_outcomes[-1].route_id,
            "audit.assumptions_generality_and_absorption",
        )
        self.assertNotIn(
            "absorbs",
            {
                relation.relation_type
                for relation in audited_snapshot.relation_versions
                if relation.created_at == T14
            },
        )

        result_portfolio = self._entity(
            "portfolio.attention_precision",
            ResultPortfolio(
                claim_graph_ref=claim_graph_ref,
                headline_claim_id="claim.headline_reversal",
                included_results=(
                    PortfolioItem(
                        claim_id="claim.headline_reversal",
                        scientific_job="Headline characterization of the exact reversal region.",
                        marginal_value="Identifies when better information lowers realized accuracy through non-use.",
                    ),
                    PortfolioItem(
                        claim_id="claim.tie_boundaries",
                        scientific_job="Boundary discipline for endpoint inclusion.",
                        marginal_value="Prevents the headline from hiding dependence on the tie rule.",
                    ),
                    PortfolioItem(
                        claim_id="claim.constant_cost_ablation",
                        scientific_job="Necessity result separating endogenous attention from precision-linked incentives.",
                        marginal_value="Shows why endogenous attention alone cannot carry the economic lesson.",
                    ),
                ),
                excluded_results=(),
                economic_nugget=(
                    "Information quality changes outcomes through two opposing forces: conditional accuracy and the decision to use information."
                ),
                reader_belief_update=(
                    "A more precise signal need not improve realized decisions when its precision changes whether it is processed."
                ),
                economic_consequence=(
                    "Information design must account for adoption of information, not only informativeness conditional on use."
                ),
            ),
            title="Minimal result portfolio",
            summary="Headline, boundary, and necessity results perform distinct scientific jobs.",
            created_at=T15,
        )
        portfolio_ref = eref(result_portfolio)
        g4_dossier = self._entity(
            "dossier.g4.attention_precision",
            GateDossier(
                gate_kind="G4_result_investment",
                research_question_ref=question_ref,
                ordered_object_refs=(
                    question_ref,
                    claim_graph_ref,
                    verification_bundle_ref,
                    absorption_ref,
                    portfolio_ref,
                ),
                ordered_artifact_refs=(
                    headline_proof_ref,
                    boundary_proof_ref,
                    ablation_proof_ref,
                    literature_artifact_ref,
                ),
                requirements=(
                    GateRequirement(
                        requirement_id="g4.proof_floor",
                        description="Every retained proof obligation has an independent discharged record.",
                        evidence_refs=(verification_bundle_ref,),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g4.boundary_floor",
                        description="Endpoint and ablation boundaries remain visible in the portfolio.",
                        evidence_refs=(claim_graph_ref, boundary_proof_ref),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g4.absorption_floor",
                        description="Verified full-text control evidence establishes a first substantive mapping failure.",
                        evidence_refs=(absorption_ref, literature_artifact_ref),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g4.portfolio_discipline",
                        description="Every retained claim performs a distinct scientific job.",
                        evidence_refs=(portfolio_ref,),
                        recorded_condition="evidence_supplied",
                    ),
                ),
                proposed_action="approve",
                rationale=(
                    "The minimal portfolio is fully verified, boundary-disciplined, nonabsorbed against the full-text control, and worth continued argument investment."
                ),
                prepared_at=T15,
            ),
            title="G4 result-investment dossier",
            summary="Proof, boundary, absorption, and portfolio floors for human review.",
            created_at=T15,
        )
        _, curated_snapshot = self._commit_route(
            route_id="curate.result_portfolio",
            purpose="research_discovery",
            outputs=(result_portfolio, g4_dossier),
            relations=(
                RelationVersion(
                    relation_id="relation.portfolio_includes_claim_graph",
                    relation_type="includes",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=portfolio_ref,
                    target=claim_graph_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T15,
                ),
                RelationVersion(
                    relation_id="relation.g4_governs_portfolio",
                    relation_type="governs",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=eref(g4_dossier),
                    target=portfolio_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T15,
                ),
            ),
            evidence_refs=(
                question_ref,
                absorption_ref,
                claim_graph_ref,
                verification_bundle_ref,
            ),
            authority_basis=(g1.decision_id, g2.decision_id, g3.decision_id),
            focus_entity_ids=(
                question.entity_id,
                absorption_assessment.entity_id,
                claim_graph.entity_id,
                verification_bundle.entity_id,
            ),
            created_at=T15,
        )
        self.assertEqual(
            curated_snapshot.route_outcomes[-1].route_id,
            "curate.result_portfolio",
        )

        g4 = Decision(
            decision_id="decision.g4.attention_precision",
            version=1,
            project_id=self.snapshot.project_id,
            decision_kind="G4_result_investment",
            subject_ref=g4_dossier.entity_id,
            scope_ref=question.entity_id,
            question="Approve this exact verified result portfolio for argument-package assembly?",
            options=("approve", "revise", "kill"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve the minimal three-result portfolio.",
            rationale=(
                "The headline, boundary, and necessity results are independently verified, nonredundant, and nonabsorbed against the current full-text control."
            ),
            evidence_refs=(g4_dossier.entity_id,),
            unresolved_risks=(
                "The sealed exact absorber has not yet been injected into this control branch.",
                "No external novelty claim is authorized for this development fixture.",
            ),
            required_authority="L2",
            decider=HUMAN,
            decided_at=T16,
            status="confirmed",
        )
        g4_result = commit_decision(self.layout, g4)
        self.assertEqual(g4_result.status, "committed")
        through_g4 = replay(self.layout)
        self.assertEqual(through_g4.current_decisions[g4.decision_id], 1)

        package_ref = EntityVersionRef(
            entity_id="package.validated_argument.attention_precision", version=1
        )
        g5_dossier_ref = EntityVersionRef(
            entity_id="dossier.g5.attention_precision", version=1
        )
        prior_gate_refs = (
            DecisionVersionRef(decision_id=g1.decision_id, version=1),
            DecisionVersionRef(decision_id=g2.decision_id, version=1),
            DecisionVersionRef(decision_id=g3.decision_id, version=1),
            DecisionVersionRef(decision_id=g4.decision_id, version=1),
        )
        argument_package = self._entity(
            package_ref.entity_id,
            ValidatedArgumentPackage(
                question_ref=question_ref,
                benchmark_set_ref=benchmark_ref,
                primitive_graph_ref=primitive_ref,
                selected_mechanism_ref=eref(selected),
                serious_rejected_rival_refs=(eref(rival),),
                prediction_register_ref=reconciled_prediction_ref,
                example_suite_ref=example_ref,
                economic_argument_graph_ref=argument_ref,
                implementation_tournament_ref=eref(implementation_tournament),
                formal_model_ref=locked_model_ref,
                formalization_map_ref=formalization_ref,
                assumption_map_ref=assumption_ref,
                claim_graph_ref=claim_graph_ref,
                verification_bundle_ref=verification_bundle_ref,
                closest_theory_map_ref=closest_theory_ref,
                absorption_assessment_ref=absorption_ref,
                result_portfolio_ref=portfolio_ref,
                prior_gate_decision_refs=prior_gate_refs,
                g5_dossier_ref=g5_dossier_ref,
                economic_nugget=parse_theory_entity(
                    result_portfolio
                ).economic_nugget,
                qualified_novelty=(
                    "No external novelty claim is made; the development control records only its verified first mapping failure."
                ),
                unresolved_risks=(
                    "The sealed exact absorber remains withheld from this control branch.",
                    "This development fixture is not eligible for external publication claims.",
                ),
                prohibited_overclaims=tuple(
                    fixture_payload["evaluator"]["prohibited_overclaims"]
                ),
                release_mode="evaluation_only",
                novelty_claim_mode="none",
            ),
            title="Evaluation-only validated argument package",
            summary="The complete exact G1-G4 argument chain, pending human G5 control approval.",
            created_at=T17,
        )
        self.assertEqual(eref(argument_package), package_ref)
        g5_ordered_refs = (
            question_ref,
            benchmark_ref,
            primitive_ref,
            eref(selected),
            eref(rival),
            eref(tournament),
            reconciled_prediction_ref,
            example_ref,
            argument_ref,
            eref(implementation_tournament),
            locked_model_ref,
            eref(continuous_model),
            formalization_ref,
            assumption_ref,
            claim_graph_ref,
            *obligation_refs,
            *verification_record_refs,
            verification_bundle_ref,
            literature_ref,
            closest_theory_ref,
            absorption_ref,
            portfolio_ref,
            package_ref,
        )
        g5_dossier = self._entity(
            g5_dossier_ref.entity_id,
            GateDossier(
                gate_kind="G5_argument_validation",
                research_question_ref=question_ref,
                ordered_object_refs=g5_ordered_refs,
                ordered_artifact_refs=(
                    brief_artifact_ref,
                    headline_proof_ref,
                    boundary_proof_ref,
                    ablation_proof_ref,
                    interpretation_ref,
                    literature_artifact_ref,
                ),
                requirements=(
                    GateRequirement(
                        requirement_id="g5.exact_chain",
                        description="Question, benchmarks, mechanisms, models, claims, proofs, absorption, and portfolio form one exact current chain.",
                        evidence_refs=(package_ref,),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g5.proof_and_interpretation",
                        description="Every proof obligation is discharged and economic interpretation evidence is explicit.",
                        evidence_refs=(verification_bundle_ref, interpretation_ref),
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g5.absorption_control",
                        description="The control branch is nonabsorbed on verified full-text evidence, while the sealed absorber risk remains disclosed.",
                        evidence_refs=(absorption_ref, literature_artifact_ref),
                        recorded_condition="risk_disclosed",
                    ),
                    GateRequirement(
                        requirement_id="g5.human_gate_chain",
                        description="G1-G4 are exact current human approvals in this ResearchQuestion scope.",
                        evidence_refs=prior_gate_refs,
                        recorded_condition="evidence_supplied",
                    ),
                    GateRequirement(
                        requirement_id="g5.no_external_claim",
                        description="The package is evaluation-only and makes no external novelty or publication claim.",
                        evidence_refs=(package_ref,),
                        recorded_condition="risk_disclosed",
                    ),
                ),
                proposed_action="approve",
                rationale=(
                    "All non-compensatory structural floors pass for an evaluation-only control handoff; external release remains unauthorized."
                ),
                prepared_at=T17,
            ),
            title="G5 argument-validation dossier",
            summary="Complete exact-chain and non-compensatory-floor evidence for human control approval.",
            created_at=T17,
        )
        self.assertEqual(eref(g5_dossier), g5_dossier_ref)
        validate_inputs = (
            question_ref,
            benchmark_ref,
            primitive_ref,
            eref(selected),
            eref(rival),
            eref(tournament),
            reconciled_prediction_ref,
            example_ref,
            argument_ref,
            eref(implementation_tournament),
            locked_model_ref,
            eref(continuous_model),
            formalization_ref,
            assumption_ref,
            claim_graph_ref,
            *obligation_refs,
            *verification_record_refs,
            verification_bundle_ref,
            literature_ref,
            closest_theory_ref,
            absorption_ref,
            portfolio_ref,
        )
        _, package_snapshot = self._commit_route(
            route_id="validate.argument_package",
            purpose="research_verification",
            outputs=(argument_package, g5_dossier),
            relations=(
                RelationVersion(
                    relation_id="relation.g5_governs_package",
                    relation_type="governs",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=g5_dossier_ref,
                    target=package_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T17,
                ),
                RelationVersion(
                    relation_id="relation.package_includes_portfolio",
                    relation_type="includes",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=package_ref,
                    target=portfolio_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T17,
                ),
                RelationVersion(
                    relation_id="relation.verification_bundle_validates_package",
                    relation_type="validates",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=verification_bundle_ref,
                    target=package_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T17,
                ),
            ),
            evidence_refs=validate_inputs,
            authority_basis=(
                g1.decision_id,
                g2.decision_id,
                g3.decision_id,
                g4.decision_id,
            ),
            focus_entity_ids=tuple(reference.entity_id for reference in validate_inputs),
            created_at=T17,
        )
        self.assertEqual(
            package_snapshot.route_outcomes[-1].route_id,
            "validate.argument_package",
        )
        self.assertEqual(
            package_snapshot.route_outcomes[-1].outcome,
            "completed_with_candidate",
        )

        g5 = Decision(
            decision_id="decision.g5.attention_precision",
            version=1,
            project_id=self.snapshot.project_id,
            decision_kind="G5_argument_validation",
            subject_ref=g5_dossier.entity_id,
            scope_ref=question.entity_id,
            question="Approve this exact package for evaluation-only handoff?",
            options=("approve", "reopen", "kill"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve evaluation-only control handoff.",
            rationale=(
                "The exact argument chain, proof records, interpretation, boundaries, absorption control, and G1-G4 authorities all close without authorizing external release."
            ),
            evidence_refs=(g5_dossier.entity_id,),
            unresolved_risks=(
                "The sealed absorber mutation must reopen this control G5 if exact absorption is established.",
                "External submission still requires a separate L3 handoff after later phases.",
            ),
            required_authority="L2",
            decider=HUMAN,
            decided_at=T18,
            status="confirmed",
        )
        g5_result = commit_decision(self.layout, g5)
        self.assertEqual(g5_result.status, "committed")
        final_snapshot = replay(self.layout)
        rebuilt_from_head = replay_at(self.layout, final_snapshot.head)
        self.assertEqual(
            canonical_json_bytes(rebuilt_from_head),
            canonical_json_bytes(final_snapshot),
        )
        self.assertEqual(final_snapshot.chain[0], self.snapshot.head)
        self.assertEqual(len(final_snapshot.chain), 19)
        self.assertEqual(len(final_snapshot.route_outcomes), 13)
        self.assertEqual(len(final_snapshot.current_artifacts), 16)
        self.assertEqual(final_snapshot.current_entities[argument_package.entity_id], 1)
        self.assertEqual(final_snapshot.current_decisions[g5.decision_id], 1)
        self.assertEqual(
            tuple(outcome.route_id for outcome in final_snapshot.route_outcomes),
            (
                "frame.question_and_benchmarks",
                "decompose.primitives",
                "tournament.mechanisms",
                "freeze.predictions",
                "lab.micro_examples_and_ablations",
                "promote.mechanism",
                "tournament.implementations",
                "promote.formal_base",
                "discover.claims_and_boundaries",
                "verify.claims_proofs_and_interpretation",
                "audit.assumptions_generality_and_absorption",
                "curate.result_portfolio",
                "validate.argument_package",
            ),
        )
        effective_gate_ids = {
            reference.decision_id
            for reference in final_snapshot.effective_decisions.values()
        }
        self.assertTrue(
            {
                g1.decision_id,
                g2.decision_id,
                g3.decision_id,
                g4.decision_id,
                g5.decision_id,
            }.issubset(effective_gate_ids)
        )

        if self._after_fresh_g5(
            {key: value for key, value in locals().items() if key != "self"}
        ):
            return

        sealed_comparator_bytes = canonical_json_bytes(
            fixture_payload["evaluator"]["absorption_decoy"]
        )
        sealed_registration, sealed_comparator_ref, _ = self._artifact(
            "artifact.literature.sealed_exact_absorber",
            logical_name="Sealed verified adoption-threshold absorber",
            media_type="application/json",
            data=sealed_comparator_bytes,
            created_at=T19,
        )
        absorbed_literature = self._entity(
            literature_evidence.entity_id,
            LiteratureEvidence(
                question_ref=question_ref,
                assertions=(
                    LiteratureAssertion(
                        assertion_id="literature.sealed_exact_threshold",
                        assertion=(
                            "The sealed comparator proves the same benefit-cost adoption threshold under the exact receiver-processing translation."
                        ),
                        source_locator="sealed-fixture:adoption-threshold#exact-map",
                        access_status="full_text",
                        evidence_ref=sealed_comparator_ref,
                        verification_status="source_verified",
                    ),
                    LiteratureAssertion(
                        assertion_id="literature.sealed_exact_output",
                        assertion=(
                            "Its baseline output, adoption decision, cost, gain, and output translation reproduce the headline reversal as a direct corollary."
                        ),
                        source_locator="sealed-fixture:adoption-threshold#corollary",
                        access_status="full_text",
                        evidence_ref=sealed_comparator_ref,
                        verification_status="source_verified",
                    ),
                ),
            ),
            title="Verified sealed-absorber evidence",
            summary="Full-text evidence for the exact adoption-threshold translation.",
            created_at=T19,
            version=2,
            supersedes=literature_ref,
        )
        absorbed_literature_ref = eref(absorbed_literature)

        def absorbed_dimension(
            dimension: str,
            project_side: str,
            comparator_side: str,
            translation: str,
            mapping_status: str,
            *evidence: object,
        ) -> ClosestTheoryDimension:
            return ClosestTheoryDimension(
                dimension=dimension,  # type: ignore[arg-type]
                project_side=project_side,
                comparator_side=comparator_side,
                translation=translation,
                mapping_status=mapping_status,  # type: ignore[arg-type]
                evidence_refs=(sealed_comparator_ref, *evidence),  # type: ignore[arg-type]
            )

        absorbed_closest = self._entity(
            closest_theory_map.entity_id,
            ClosestTheoryMap(
                claim_graph_ref=claim_graph_ref,
                literature_evidence_ref=absorbed_literature_ref,
                comparator_label="Sealed verified adoption-threshold absorber",
                dimensions=(
                    absorbed_dimension(
                        "benchmark",
                        "No processing yields accuracy one half.",
                        "No adoption yields baseline output one half.",
                        "Baseline output maps exactly to no-information accuracy.",
                        "exact",
                        benchmark_ref,
                    ),
                    absorbed_dimension(
                        "primitives",
                        "Precision x creates gain x/2 and cost kappa*x^2.",
                        "Project quality creates benefit x/2 and cost kappa*x^2.",
                        "Signal policy maps to project quality and processing maps to adoption.",
                        "exact",
                        primitive_ref,
                    ),
                    absorbed_dimension(
                        "timing",
                        "Processing is chosen before the signal.",
                        "Adoption is chosen before project output.",
                        "Both participation choices precede realization.",
                        "exact",
                        locked_model_ref,
                    ),
                    absorbed_dimension(
                        "solution_concept",
                        "Process iff information gain covers cost.",
                        "Adopt iff project benefit covers cost.",
                        "Receiver optimality is the comparator's adoption optimality.",
                        "exact",
                        locked_model_ref,
                    ),
                    absorbed_dimension(
                        "assumptions",
                        "Indivisible processing with gain x/2 and cost kappa*x^2.",
                        "Indivisible adoption with benefit x/2 and cost kappa*x^2.",
                        "Every load-bearing assumption maps without residue.",
                        "exact",
                        assumption_ref,
                    ),
                    absorbed_dimension(
                        "quantifiers",
                        "All 0<ell<h<=1 and kappa>=0.",
                        "All ordered project qualities and nonnegative cost coefficients.",
                        "The domains and threshold order are identical.",
                        "exact",
                        claim_graph_ref,
                    ),
                    absorbed_dimension(
                        "formal_result",
                        "Y(ell)>Y(h) iff only ell is processed.",
                        "Lower-quality output exceeds higher-quality output iff only the lower project is adopted.",
                        "The headline theorem is the translated adoption corollary.",
                        "standard_argument",
                        claim_graph_ref,
                    ),
                    absorbed_dimension(
                        "economic_lesson",
                        "Quality changes participation as well as conditional output.",
                        "Project quality changes adoption as well as adopted output.",
                        "The claimed economic lesson is preserved by the exact translation.",
                        "standard_argument",
                        argument_ref,
                    ),
                ),
                classification="direct_corollary",
                first_mapping_failure=None,
            ),
            title="Eight-dimensional exact absorber map",
            summary="Every dimension maps exactly or by a verified standard argument.",
            created_at=T19,
            version=2,
            supersedes=closest_theory_ref,
        )
        absorbed_closest_ref = eref(absorbed_closest)
        absorbed_assessment = self._entity(
            absorption_assessment.entity_id,
            AbsorptionAssessment(
                closest_theory_map_ref=absorbed_closest_ref,
                central_claim_graph_ref=claim_graph_ref,
                central_claim_id="claim.headline_reversal",
                outcome="absorbed",
                rationale=(
                    "The sealed verified comparator translates every primitive and assumption and makes the headline theorem a direct adoption-threshold corollary."
                ),
                standard_argument_refs=(sealed_comparator_ref,),
                first_mapping_failure=None,
                recommended_route="mutate",
            ),
            title="Absorbed contribution assessment",
            summary="The headline is a direct corollary under the sealed exact translation.",
            created_at=T19,
            version=2,
            supersedes=absorption_ref,
        )
        absorbed_assessment_ref = eref(absorbed_assessment)
        _, absorbed_snapshot = self._commit_route(
            route_id="audit.assumptions_generality_and_absorption",
            purpose="research_verification",
            outputs=(
                absorbed_literature,
                absorbed_closest,
                absorbed_assessment,
            ),
            relations=(
                RelationVersion(
                    relation_id="relation.absorbed_closest_compares_literature",
                    relation_type="compares_to",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=absorbed_closest_ref,
                    target=absorbed_literature_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T19,
                ),
                RelationVersion(
                    relation_id="relation.absorbed_closest_maps_claims",
                    relation_type="maps_to",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=absorbed_closest_ref,
                    target=claim_graph_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T19,
                ),
                RelationVersion(
                    relation_id="relation.assessment_absorbs_closest",
                    relation_type="absorbs",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=absorbed_assessment_ref,
                    target=absorbed_closest_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=T19,
                ),
            ),
            artifacts=((sealed_registration, sealed_comparator_bytes),),
            evidence_refs=(
                question_ref,
                assumption_ref,
                claim_graph_ref,
                locked_model_ref,
                verification_bundle_ref,
            ),
            authority_basis=(g1.decision_id, g2.decision_id, g3.decision_id),
            focus_entity_ids=(
                question.entity_id,
                assumption_map.entity_id,
                claim_graph.entity_id,
                locked_model.entity_id,
                verification_bundle.entity_id,
            ),
            created_at=T19,
        )

        def exact_entity_bytes(
            snapshot: Snapshot, reference: EntityVersionRef
        ) -> bytes:
            return canonical_json_bytes(
                next(
                    item
                    for item in snapshot.entity_versions
                    if item.entity_id == reference.entity_id
                    and item.version == reference.version
                )
            )

        immutable_scientific_refs = (
            locked_model_ref,
            claim_graph_ref,
            *verification_record_refs,
            verification_bundle_ref,
        )
        for reference in immutable_scientific_refs:
            self.assertEqual(
                exact_entity_bytes(final_snapshot, reference),
                exact_entity_bytes(absorbed_snapshot, reference),
            )
            self.assertEqual(
                absorbed_snapshot.current_entities[reference.entity_id],
                reference.version,
            )
        self.assertEqual(
            absorbed_snapshot.current_entities[absorbed_literature.entity_id], 2
        )
        self.assertEqual(
            absorbed_snapshot.current_entities[absorbed_closest.entity_id], 2
        )
        self.assertEqual(
            absorbed_snapshot.current_entities[absorbed_assessment.entity_id], 2
        )
        self.assertEqual(len(absorbed_snapshot.chain), 20)
        self.assertEqual(len(absorbed_snapshot.route_outcomes), 14)
        self.assertEqual(len(absorbed_snapshot.current_artifacts), 17)

        # The portfolio's scientific claims remain byte-identical, but its G4
        # investment authority and the downstream package are stale because
        # they cite the superseded nonabsorption branch.
        self.assertTrue(
            _typed_reference_closure_is_current_and_fresh(
                absorbed_snapshot, portfolio_ref
            )
        )
        self.assertFalse(
            _typed_reference_closure_is_current_and_fresh(
                absorbed_snapshot, eref(g4_dossier)
            )
        )
        self.assertFalse(
            _typed_reference_closure_is_current_and_fresh(
                absorbed_snapshot, package_ref
            )
        )
        self.assertFalse(
            _typed_reference_closure_is_current_and_fresh(
                absorbed_snapshot, g5_dossier_ref
            )
        )
        scientifically_approved = _effective_approved_gates(absorbed_snapshot)
        self.assertIn("G3_formal_base", scientifically_approved)
        self.assertNotIn("G4_result_investment", scientifically_approved)
        self.assertNotIn("G5_argument_validation", scientifically_approved)

        absorbed_head = absorbed_snapshot.head
        with self.assertRaisesRegex(
            RouteEntryError,
            r"missing required fresh approved gate G4_result_investment",
        ):
            begin_run(
                self.layout,
                absorbed_snapshot,
                route_id="validate.argument_package",
                actor=AGENT,
                purpose="research_verification",
                compartments=("project_research",),
                focus_entity_ids=tuple(
                    reference.entity_id for reference in validate_inputs
                ),
                budget_units=32_000,
                route_run_id="run.gold.absorbed.production_revalidation",
                context_manifest_id="context.gold.absorbed.production_revalidation",
                created_at=T19,
                route_registry_hash=ROUTE_REGISTRY_V2_HASH,
            )
        self.assertEqual(replay(self.layout).head, absorbed_head)
        self.assertEqual(
            parse_theory_entity(argument_package).release_mode,
            "evaluation_only",
        )
        rebuilt_absorbed = replay_at(self.layout, absorbed_head)
        self.assertEqual(
            canonical_json_bytes(rebuilt_absorbed),
            canonical_json_bytes(absorbed_snapshot),
        )


if __name__ == "__main__":
    unittest.main()
