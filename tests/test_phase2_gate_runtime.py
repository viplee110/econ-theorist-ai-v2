"""End-to-end runtime contracts for typed Phase 2 promotion gates."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.decisions import commit_decision
from econ_theorist.models import (
    Actor,
    ChangedFacets,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    RecordDecisionOp,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    ScientificStatus,
    SupersedeEntityOp,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V1_HASH
from econ_theorist.project import init_project
from econ_theorist.route_registry import RouteAuthorizationError, get_route
from econ_theorist.runs import RunError, begin_run, transaction_bindings
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.commit import commit_transaction
from econ_theorist.runtime.replay import (
    CandidateValidationError,
    replay,
    validate_candidate,
)
from econ_theorist.theory import (
    BenchmarkRecord,
    BenchmarkSet,
    GateDossier,
    GateRequirement,
    MechanismHypothesis,
    MechanismPairComparison,
    MechanismStep,
    MechanismTournament,
    PrimitiveGraph,
    PrimitiveNode,
    ResearchQuestion,
    pack_theory_payload,
)
from econ_theorist.theory_validation import (
    TheoryValidationError,
    validate_phase2_route_entry,
    validate_phase2_route_transaction,
    validate_theory_projection,
)


PROJECT_ID = "project.phase2.gate.runtime"
AGENT = Actor(kind="agent", actor_id="agent.theory")
HUMAN = Actor(kind="human", actor_id="human.owner")
QUESTION_REF = EntityVersionRef(entity_id="question.gate.runtime", version=1)
BENCHMARK_REF = EntityVersionRef(entity_id="benchmarks.gate.runtime", version=1)
PRIMITIVE_REF = EntityVersionRef(entity_id="primitives.gate.runtime", version=1)
DOSSIER_REF = EntityVersionRef(entity_id="dossier.g1.gate.runtime", version=1)


def _entity(
    reference: EntityVersionRef,
    entity_type: str,
    payload: object,
    *,
    created_at: str,
    supersedes: EntityVersionRef | None = None,
) -> EntityVersion:
    return EntityVersion(
        entity_id=reference.entity_id,
        entity_type=entity_type,
        version=reference.version,
        project_id=PROJECT_ID,
        title=reference.entity_id,
        summary=f"Typed {entity_type} runtime fixture.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=pack_theory_payload(payload),
        created_at=created_at,
        supersedes=supersedes,
    )


def _relation(
    relation_id: str,
    relation_type: str,
    source: EntityVersionRef,
    target: EntityVersionRef,
) -> RelationVersion:
    return RelationVersion(
        relation_id=relation_id,
        relation_type=relation_type,
        version=1,
        project_id=PROJECT_ID,
        source=source,
        target=target,
        dependency_mode="trace_only",
        created_at="2026-07-11T10:08:00Z",
    )


def _question() -> EntityVersion:
    return _entity(
        QUESTION_REF,
        "ResearchQuestion",
        ResearchQuestion(
            phenomenon="A comparative static can reverse.",
            object_to_explain="The reversal in the outcome ranking.",
            unresolved_delta="The benchmark suppresses an extensive margin.",
            importance="The margin changes the policy ranking.",
            kill_condition="Stop if the fixed-margin benchmark also reverses.",
            proposed_scope="A finite-state binary-action environment.",
            candidate_archetypes=("mechanism_explanation",),
        ),
        created_at="2026-07-11T10:01:00Z",
    )


def _benchmark() -> EntityVersion:
    return _entity(
        BENCHMARK_REF,
        "BenchmarkSet",
        BenchmarkSet(
            question_ref=QUESTION_REF,
            benchmarks=(
                BenchmarkRecord(
                    benchmark_id="benchmark.gate.runtime",
                    label="Fixed-margin benchmark",
                    exact_primitives=("one decision maker",),
                    timing=("information then action",),
                    solution_concept="optimal action",
                    prediction="more precise information weakly improves accuracy",
                    unresolved_delta="the participation margin is absent",
                ),
            ),
            exact_question_delta="Introduce the participation margin.",
        ),
        created_at="2026-07-11T10:01:01Z",
    )


def _question_v2() -> EntityVersion:
    reference = EntityVersionRef(entity_id=QUESTION_REF.entity_id, version=2)
    return _entity(
        reference,
        "ResearchQuestion",
        ResearchQuestion(
            phenomenon="A comparative static can reverse after the scope is revised.",
            object_to_explain="The revised reversal in the outcome ranking.",
            unresolved_delta="The benchmark suppresses two extensive margins.",
            importance="The revised margins change the policy ranking.",
            kill_condition="Stop if the fixed-margin benchmark also reverses.",
            proposed_scope="A revised finite-state binary-action environment.",
            candidate_archetypes=("mechanism_explanation",),
        ),
        created_at="2026-07-11T10:10:00Z",
        supersedes=QUESTION_REF,
    )


def _benchmark_v2() -> EntityVersion:
    reference = EntityVersionRef(entity_id=BENCHMARK_REF.entity_id, version=2)
    return _entity(
        reference,
        "BenchmarkSet",
        BenchmarkSet(
            question_ref=QUESTION_REF,
            benchmarks=(
                BenchmarkRecord(
                    benchmark_id="benchmark.gate.runtime",
                    label="Fixed-margin benchmark",
                    exact_primitives=("one decision maker",),
                    timing=("information then action",),
                    solution_concept="optimal action",
                    prediction="more precise information weakly improves accuracy",
                    unresolved_delta="participation and acquisition margins are absent",
                ),
            ),
            exact_question_delta="Introduce participation and acquisition margins.",
        ),
        created_at="2026-07-11T10:10:00Z",
        supersedes=BENCHMARK_REF,
    )


def _primitive_graph() -> EntityVersion:
    return _entity(
        PRIMITIVE_REF,
        "PrimitiveGraph",
        PrimitiveGraph(
            question_ref=QUESTION_REF,
            benchmark_set_ref=BENCHMARK_REF,
            nodes=(
                PrimitiveNode(
                    node_id="primitive.participation",
                    kind="choice",
                    label="Participation",
                    economic_meaning="The receiver chooses whether to process.",
                    status="primitive",
                ),
            ),
        ),
        created_at="2026-07-11T10:03:00Z",
    )


def _dossier(
    reference: EntityVersionRef = DOSSIER_REF,
) -> EntityVersion:
    return _entity(
        reference,
        "GateDossier",
        GateDossier(
            gate_kind="G1_question_benchmark",
            research_question_ref=QUESTION_REF,
            ordered_object_refs=(QUESTION_REF, BENCHMARK_REF, PRIMITIVE_REF),
            requirements=(
                GateRequirement(
                    requirement_id="requirement.exact.delta",
                    description="The question and benchmark expose one exact delta.",
                    evidence_refs=(QUESTION_REF, BENCHMARK_REF),
                    recorded_condition="evidence_supplied",
                ),
            ),
            proposed_action="approve",
            rationale="The exact question and benchmark are ready for human review.",
            prepared_at="2026-07-11T10:04:00Z",
        ),
        created_at="2026-07-11T10:04:00Z",
    )


def _mechanism(
    reference: EntityVersionRef,
    *,
    wedge: str,
    consequence: str,
) -> EntityVersion:
    return _entity(
        reference,
        "MechanismHypothesis",
        MechanismHypothesis(
            question_ref=QUESTION_REF,
            primitive_graph_ref=PRIMITIVE_REF,
            decision_margin_or_foundational_distinction="Whether to process.",
            initiating_wedge=wedge,
            force_chain=(
                MechanismStep(
                    step_id="step.participation",
                    source="precision",
                    response_or_constraint="processing becomes unattractive",
                    target="participation",
                    economic_meaning="Information quality changes take-up.",
                    effect_kind="direct",
                ),
            ),
            predicted_consequence=consequence,
            boundary="The effect disappears when processing is compulsory.",
            expected_load_bearing_conditions=("processing is optional",),
            distinguishing_signature="Nonparticipation occurs only at high precision.",
            killer_test="Force processing and check that the reversal disappears.",
        ),
        created_at="2026-07-11T10:07:00Z",
    )


def _mechanism_outputs() -> tuple[tuple[EntityVersion, ...], tuple[RelationVersion, ...]]:
    selected_ref = EntityVersionRef(
        entity_id="mechanism.gate.runtime", version=1
    )
    rival_ref = EntityVersionRef(
        entity_id="mechanism.rival.gate.runtime", version=1
    )
    tournament_ref = EntityVersionRef(
        entity_id="tournament.mechanisms.gate.runtime", version=1
    )
    selected = _mechanism(
        selected_ref,
        wedge="Precision raises the cost of processing.",
        consequence="High precision can lower realized accuracy.",
    )
    rival = _mechanism(
        rival_ref,
        wedge="Precision changes only conditional action quality.",
        consequence="Higher precision always improves conditional accuracy.",
    )
    tournament = _entity(
        tournament_ref,
        "MechanismTournament",
        MechanismTournament(
            question_ref=QUESTION_REF,
            hypothesis_refs=(selected_ref, rival_ref),
            comparisons=(
                MechanismPairComparison(
                    left_ref=selected_ref,
                    right_ref=rival_ref,
                    distinct_arrow_or_signature="Only the selected mechanism changes participation.",
                    decisive_test="Force processing and compare the rankings.",
                ),
            ),
            proposed_selected_ref=selected_ref,
            serious_rival_refs=(rival_ref,),
            selection_rationale="The participation response separates the mechanisms.",
        ),
        created_at="2026-07-11T10:07:01Z",
    )
    relations = (
        _relation(
            "relation.mechanisms.compare",
            "compares_to",
            selected_ref,
            rival_ref,
        ),
        _relation(
            "relation.mechanism.explains",
            "explains",
            selected_ref,
            QUESTION_REF,
        ),
    )
    return (selected, rival, tournament), relations


class Phase2GateRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.layout = StoreLayout.at(self.root)
        self.snapshot = init_project(
            self.root,
            name="Phase 2 gate runtime",
            actor_id=HUMAN.actor_id,
            project_id=PROJECT_ID,
            created_at="2026-07-11T10:00:00Z",
        )

    def _route_transaction(
        self,
        *,
        route_id: str,
        purpose: str,
        outputs: tuple[EntityVersion, ...],
        relations: tuple[RelationVersion, ...] = (),
        evidence_refs: tuple[EntityVersionRef, ...] = (),
        authority_basis: tuple[str, ...] = (),
        extra_operations: tuple[object, ...] = (),
        transaction_id: str,
    ) -> Transaction:
        if route_id == "frame.question_and_benchmarks":
            focus_entity_ids = (self.snapshot.project_id,)
        elif route_id == "decompose.primitives":
            focus_entity_ids = (QUESTION_REF.entity_id, BENCHMARK_REF.entity_id)
        else:
            focus_entity_ids = (
                QUESTION_REF.entity_id,
                BENCHMARK_REF.entity_id,
                PRIMITIVE_REF.entity_id,
            )
        run = begin_run(
            self.layout,
            self.snapshot,
            route_id=route_id,
            actor=AGENT,
            purpose=purpose,
            compartments=("project_research",),
            focus_entity_ids=focus_entity_ids,
            budget_units=30_000,
        )
        candidates = tuple(
            EntityVersionRef(entity_id=item.entity_id, version=item.version)
            for item in outputs
        ) + tuple(
            RelationVersionRef(
                relation_id=item.relation_id, version=item.version
            )
            for item in relations
        )
        return Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id=transaction_id,
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=self.snapshot.head,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=AGENT,
            intent=f"Exercise {route_id} gate semantics.",
            operations=(
                *(CreateEntityOp(entity=item) for item in outputs),
                *(CreateRelationOp(relation=item) for item in relations),
                *extra_operations,
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run.route_run_id,
                        route_id=run.route_id,
                        outcome="completed_with_candidate",
                        rationale="The exact typed candidates were produced.",
                        candidate_refs=candidates,
                    )
                ),
            ),
            evidence_refs=evidence_refs,
            authority_basis=authority_basis,
            created_at="2026-07-11T10:08:00Z",
            parent_transaction_hash=self.snapshot.head,
        )

    def _commit(self, transaction: Transaction) -> None:
        result = commit_transaction(self.layout, transaction)
        self.assertEqual(result.status, "committed")
        self.snapshot = replay(self.layout)

    def _supersede_in_legacy_projection(
        self,
        previous: EntityVersionRef,
        current: EntityVersion,
        *,
        transaction_id: str,
    ) -> None:
        """Build an in-memory old-catalog projection for gate invalidation.

        Live v1 writes over Phase 2 state are forbidden. This helper exercises
        the pure historical validator only; runtime downgrade rejection has a
        separate integration contract.
        """

        current_ref = EntityVersionRef(
            entity_id=current.entity_id, version=current.version
        )
        run_id = f"run.legacy.projection.{transaction_id}"
        transaction = Transaction(
            route_run_hash="1" * 64,
            context_manifest_hash="2" * 64,
            compiled_context_hash="3" * 64,
            transaction_id=transaction_id,
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=self.snapshot.head,
            route_run_id=run_id,
            route_id="repair.dependency",
            actor=AGENT,
            intent="Project one historical exact dependency supersession.",
            changed_facets=(
                ChangedFacets(
                    entity_id=current.entity_id,
                    previous_version=previous.version,
                    new_version=current.version,
                    facets=("economic_interpretation",),
                ),
            ),
            operations=(
                SupersedeEntityOp(previous=previous, entity=current),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run_id,
                        route_id="repair.dependency",
                        outcome="completed_with_candidate",
                        rationale="The historical projection superseded one dependency.",
                        candidate_refs=(current_ref,),
                    )
                ),
            ),
            evidence_refs=(previous,),
            created_at="2026-07-11T10:10:00Z",
            parent_transaction_hash=self.snapshot.head,
        )
        self.snapshot = validate_candidate(
            self.snapshot,
            transaction,
            route_registry_hash=ROUTE_REGISTRY_V1_HASH,
        )

    def _through_g1_dossier(self) -> EntityVersion:
        self._commit(
            self._route_transaction(
                route_id="frame.question_and_benchmarks",
                purpose="research_framing",
                outputs=(_question(), _benchmark()),
                relations=(
                    _relation(
                        "relation.question.frames.benchmark",
                        "frames",
                        QUESTION_REF,
                        BENCHMARK_REF,
                    ),
                    _relation(
                        "relation.benchmark.delta.question",
                        "benchmark_delta",
                        BENCHMARK_REF,
                        QUESTION_REF,
                    ),
                ),
                transaction_id="transaction.frame.gate.runtime",
            )
        )
        dossier = _dossier()
        self._commit(
            self._route_transaction(
                route_id="decompose.primitives",
                purpose="research_discovery",
                outputs=(_primitive_graph(), dossier),
                relations=(
                    _relation(
                        "relation.question.decomposes.primitives",
                        "decomposes",
                        QUESTION_REF,
                        PRIMITIVE_REF,
                    ),
                    _relation(
                        "relation.dossier.governs.primitives",
                        "governs",
                        DOSSIER_REF,
                        PRIMITIVE_REF,
                    ),
                ),
                evidence_refs=(QUESTION_REF, BENCHMARK_REF),
                transaction_id="transaction.dossier.gate.runtime",
            )
        )
        return dossier

    def _decision(
        self,
        dossier: EntityVersion,
        *,
        decision_id: str,
        decider: Actor = HUMAN,
        scope_ref: str = QUESTION_REF.entity_id,
        status: str = "confirmed",
        machine_outcome: str = "approve",
    ) -> Decision:
        return Decision(
            decision_id=decision_id,
            version=1,
            project_id=PROJECT_ID,
            decision_kind="G1_question_benchmark",
            subject_ref=dossier.entity_id,
            scope_ref=scope_ref,
            question="Approve this exact G1 dossier?",
            options=("approve", "deny"),
            selected_option=machine_outcome if status != "proposed" else None,
            machine_outcome=machine_outcome if status != "proposed" else None,
            recommendation=f"{machine_outcome.title()} the exact dossier.",
            rationale="The typed evidence is complete.",
            evidence_refs=(dossier.entity_id,),
            required_authority="L2",
            decider=decider,
            decided_at="2026-07-11T10:05:00Z",
            status=status,
        )

    def _approve_g1(
        self, dossier: EntityVersion, *, decision_id: str
    ) -> Decision:
        decision = self._decision(dossier, decision_id=decision_id)
        result = commit_decision(self.layout, decision)
        self.assertEqual(result.status, "committed")
        self.snapshot = replay(self.layout)
        return decision

    def _unbound_gated_transaction(
        self, decision: Decision
    ) -> Transaction:
        outputs, relations = _mechanism_outputs()
        candidates = tuple(
            EntityVersionRef(entity_id=item.entity_id, version=item.version)
            for item in outputs
        ) + tuple(
            RelationVersionRef(
                relation_id=item.relation_id, version=item.version
            )
            for item in relations
        )
        return Transaction(
            transaction_id="transaction.gated.deny.predicate",
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=self.snapshot.head,
            route_run_id="run.gated.deny.predicate",
            route_id="tournament.mechanisms",
            route_run_hash="a" * 64,
            context_manifest_hash="b" * 64,
            compiled_context_hash="c" * 64,
            actor=AGENT,
            intent="Exercise the commit-time approve predicate.",
            operations=(
                *(CreateEntityOp(entity=item) for item in outputs),
                *(CreateRelationOp(relation=item) for item in relations),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id="run.gated.deny.predicate",
                        route_id="tournament.mechanisms",
                        outcome="completed_with_candidate",
                        rationale="Exact candidates produced.",
                        candidate_refs=candidates,
                    )
                ),
            ),
            evidence_refs=(QUESTION_REF, BENCHMARK_REF, PRIMITIVE_REF),
            authority_basis=(decision.decision_id,),
            created_at="2026-07-11T10:08:00Z",
            parent_transaction_hash=self.snapshot.head,
        )

    def test_begin_rejects_gated_route_before_confirmed_gate(self) -> None:
        self._through_g1_dossier()

        with self.assertRaisesRegex(
            (
                RunError,
                RouteAuthorizationError,
                TheoryValidationError,
                CandidateValidationError,
            ),
            r"G1|gate|confirmed",
        ):
            begin_run(
                self.layout,
                self.snapshot,
                route_id="tournament.mechanisms",
                actor=AGENT,
                purpose="research_discovery",
                compartments=("project_research",),
                focus_entity_ids=(
                    QUESTION_REF.entity_id,
                    BENCHMARK_REF.entity_id,
                    PRIMITIVE_REF.entity_id,
                ),
                budget_units=30_000,
            )

    def test_human_gate_and_gated_commit_require_exact_bindings(self) -> None:
        dossier = self._through_g1_dossier()
        base_head = self.snapshot.head

        bad_scope = self._decision(
            dossier,
            decision_id="decision.g1.bad.scope",
            scope_ref=self.snapshot.project_id,
        )
        with self.assertRaisesRegex(CandidateValidationError, "scope_ref"):
            commit_decision(self.layout, bad_scope)
        self.assertEqual(replay(self.layout).head, base_head)

        agent_confirmation = self._decision(
            dossier,
            decision_id="decision.g1.agent.confirmation",
            decider=AGENT,
        )
        with self.assertRaises(CandidateValidationError):
            commit_decision(self.layout, agent_confirmation)
        self.assertEqual(replay(self.layout).head, base_head)

        same_transaction_dossier = _dossier(
            EntityVersionRef(entity_id="dossier.g1.same.transaction", version=1)
        )
        proposed = self._decision(
            same_transaction_dossier,
            decision_id="decision.g1.same.transaction",
            decider=AGENT,
            status="proposed",
        )
        same_transaction = self._route_transaction(
            route_id="decompose.primitives",
            purpose="research_discovery",
            outputs=(same_transaction_dossier,),
            evidence_refs=(QUESTION_REF, BENCHMARK_REF),
            extra_operations=(RecordDecisionOp(decision=proposed),),
            transaction_id="transaction.same.gate.and.decision",
        )
        with self.assertRaisesRegex(CandidateValidationError, "same transaction"):
            commit_transaction(self.layout, same_transaction)
        self.assertEqual(replay(self.layout).head, base_head)

        decision = self._decision(
            dossier,
            decision_id="decision.g1.gate.runtime",
        )
        decision_result = commit_decision(self.layout, decision)
        self.assertEqual(decision_result.status, "committed")
        self.snapshot = replay(self.layout)
        self.assertEqual(
            self.snapshot.current_decisions[decision.decision_id], decision.version
        )
        self.assertIn(
            DecisionVersionRef(
                decision_id=decision.decision_id, version=decision.version
            ),
            tuple(
                DecisionVersionRef(
                    decision_id=item.decision_id, version=item.version
                )
                for item in self.snapshot.effective_decisions.values()
            ),
        )

        mechanism_outputs, mechanism_relations = _mechanism_outputs()

        missing_authority = self._route_transaction(
            route_id="tournament.mechanisms",
            purpose="research_discovery",
            outputs=mechanism_outputs,
            relations=mechanism_relations,
            evidence_refs=(QUESTION_REF, BENCHMARK_REF, PRIMITIVE_REF),
            transaction_id="transaction.gated.missing.authority",
        )
        with self.assertRaisesRegex(
            CandidateValidationError, r"authority_basis.*(omit|required)"
        ):
            commit_transaction(self.layout, missing_authority)

        missing_question_evidence = self._route_transaction(
            route_id="tournament.mechanisms",
            purpose="research_discovery",
            outputs=mechanism_outputs,
            relations=mechanism_relations,
            evidence_refs=(BENCHMARK_REF, PRIMITIVE_REF),
            authority_basis=(decision.decision_id,),
            transaction_id="transaction.gated.missing.question",
        )
        with self.assertRaisesRegex(CandidateValidationError, "ResearchQuestion"):
            commit_transaction(self.layout, missing_question_evidence)

        valid = self._route_transaction(
            route_id="tournament.mechanisms",
            purpose="research_discovery",
            outputs=mechanism_outputs,
            relations=mechanism_relations,
            evidence_refs=(QUESTION_REF, BENCHMARK_REF, PRIMITIVE_REF),
            authority_basis=(decision.decision_id,),
            transaction_id="transaction.gated.valid",
        )
        self._commit(valid)
        self.assertEqual(
            self.snapshot.current_entities["mechanism.gate.runtime"], 1
        )

    def test_question_supersession_revokes_old_gate_for_entry_and_commit(self) -> None:
        dossier = self._through_g1_dossier()
        decision = self._approve_g1(
            dossier, decision_id="decision.g1.question.supersession"
        )

        self._supersede_in_legacy_projection(
            QUESTION_REF,
            _question_v2(),
            transaction_id="transaction.supersede.question.gate.runtime",
        )
        self.assertEqual(self.snapshot.current_entities[QUESTION_REF.entity_id], 2)

        route = get_route("tournament.mechanisms")
        with self.assertRaisesRegex(
            TheoryValidationError, r"not current and fresh|stale exact dependency"
        ):
            validate_phase2_route_transaction(
                self.snapshot,
                self._unbound_gated_transaction(decision),
                route,  # type: ignore[arg-type]
            )

        with self.assertRaisesRegex(TheoryValidationError, r"stale|fresh|G1|gate"):
            validate_phase2_route_entry(
                self.snapshot,
                route,  # type: ignore[arg-type]
                (
                    QUESTION_REF.entity_id,
                    BENCHMARK_REF.entity_id,
                    PRIMITIVE_REF.entity_id,
                ),
                actor=AGENT,
            )

    def test_confirmed_deny_supersession_preserves_downstream_history_but_blocks_begin(
        self,
    ) -> None:
        dossier = self._through_g1_dossier()
        approval = self._approve_g1(
            dossier, decision_id="decision.g1.revoked.runtime"
        )
        mechanism_outputs, mechanism_relations = _mechanism_outputs()
        self._commit(
            self._route_transaction(
                route_id="tournament.mechanisms",
                purpose="research_discovery",
                outputs=mechanism_outputs,
                relations=mechanism_relations,
                evidence_refs=(QUESTION_REF, BENCHMARK_REF, PRIMITIVE_REF),
                authority_basis=(approval.decision_id,),
                transaction_id="transaction.gated.before.revocation",
            )
        )

        denial = Decision.model_validate(
            {
                **approval.model_dump(mode="python"),
                "version": 2,
                "selected_option": "deny",
                "machine_outcome": "deny",
                "recommendation": "Deny the previously approved exact dossier.",
                "rationale": "Human review revokes the earlier promotion authority.",
                "decided_at": "2026-07-11T10:11:00Z",
                "supersedes": DecisionVersionRef(
                    decision_id=approval.decision_id, version=approval.version
                ),
            }
        )
        result = commit_decision(self.layout, denial)
        self.assertEqual(result.status, "committed")
        self.snapshot = replay(self.layout)

        self.assertEqual(
            self.snapshot.current_decisions[approval.decision_id], denial.version
        )
        self.assertEqual(
            self.snapshot.current_entities["mechanism.gate.runtime"], 1
        )
        report = validate_theory_projection(
            self.snapshot.entity_versions,
            self.snapshot.artifacts,
            self.snapshot.decisions,
            current_entities=self.snapshot.current_entities,
            current_artifacts=self.snapshot.current_artifacts,
            current_decisions=self.snapshot.current_decisions,
        )
        self.assertEqual(report.confirmed_gate_kinds, ())

        with self.assertRaisesRegex(
            (
                RunError,
                RouteAuthorizationError,
                TheoryValidationError,
                CandidateValidationError,
            ),
            r"G1|gate|approve|confirmed",
        ):
            begin_run(
                self.layout,
                self.snapshot,
                route_id="tournament.mechanisms",
                actor=AGENT,
                purpose="research_discovery",
                compartments=("project_research",),
                focus_entity_ids=(
                    QUESTION_REF.entity_id,
                    BENCHMARK_REF.entity_id,
                    PRIMITIVE_REF.entity_id,
                ),
                budget_units=30_000,
            )

    def test_ordered_dossier_input_supersession_revokes_old_gate(self) -> None:
        dossier = self._through_g1_dossier()
        decision = self._approve_g1(
            dossier, decision_id="decision.g1.ordered.input.supersession"
        )

        self._supersede_in_legacy_projection(
            BENCHMARK_REF,
            _benchmark_v2(),
            transaction_id="transaction.supersede.benchmark.gate.runtime",
        )
        self.assertEqual(self.snapshot.current_entities[BENCHMARK_REF.entity_id], 2)

        route = get_route("tournament.mechanisms")
        with self.assertRaisesRegex(
            TheoryValidationError, r"not current and fresh|stale exact dependency"
        ):
            validate_phase2_route_transaction(
                self.snapshot,
                self._unbound_gated_transaction(decision),
                route,  # type: ignore[arg-type]
            )

        with self.assertRaisesRegex(TheoryValidationError, r"stale|fresh|G1|gate"):
            validate_phase2_route_entry(
                self.snapshot,
                route,  # type: ignore[arg-type]
                (
                    QUESTION_REF.entity_id,
                    BENCHMARK_REF.entity_id,
                    PRIMITIVE_REF.entity_id,
                ),
                actor=AGENT,
            )

    def test_confirmed_deny_does_not_unlock_begin_or_commit_predicate(self) -> None:
        dossier = self._through_g1_dossier()
        denial = self._decision(
            dossier,
            decision_id="decision.g1.denied",
            machine_outcome="deny",
        )
        result = commit_decision(self.layout, denial)
        self.assertEqual(result.status, "committed")
        self.snapshot = replay(self.layout)

        route = get_route("tournament.mechanisms")
        with self.assertRaisesRegex(
            TheoryValidationError, r"missing.*(approved gate|required)"
        ):
            validate_phase2_route_transaction(
                self.snapshot,
                self._unbound_gated_transaction(denial),
                route,  # type: ignore[arg-type]
            )

        with self.assertRaisesRegex(
            (
                RunError,
                RouteAuthorizationError,
                TheoryValidationError,
                CandidateValidationError,
            ),
            r"G1|gate|confirmed|approve",
        ):
            begin_run(
                self.layout,
                self.snapshot,
                route_id="tournament.mechanisms",
                actor=AGENT,
                purpose="research_discovery",
                compartments=("project_research",),
                focus_entity_ids=(
                    QUESTION_REF.entity_id,
                    BENCHMARK_REF.entity_id,
                    PRIMITIVE_REF.entity_id,
                ),
                budget_units=30_000,
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
