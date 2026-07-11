"""Semantic acceptance tests for the Phase 2 theory validator."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    ChangedFacets,
    CreateEntityOp,
    Decision,
    EffectiveDecisionRef,
    EntityVersion,
    EntityVersionRef,
    FacetPayloads,
    RecordRouteOutcomeOp,
    RouteOutcome,
    RouteSpecV2,
    ScientificStatus,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from econ_theorist.theory import (
    BenchmarkRecord,
    BenchmarkSet,
    FrozenPrediction,
    GateDossier,
    GateRequirement,
    PredictionRegister,
    ResearchQuestion,
    VerificationRecord,
    pack_theory_payload,
)
from econ_theorist.theory_validation import (
    TheoryValidationError,
    validate_phase2_route_transaction,
    validate_theory_entity,
    validate_theory_projection,
)


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
NOW = "2026-07-11T12:00:00Z"


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def aref(artifact_id: str, digest: str = DIGEST_A) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id, version=1, content_hash=digest
    )


def question_payload() -> ResearchQuestion:
    return ResearchQuestion(
        phenomenon="A comparative static can reverse.",
        object_to_explain="The reversal.",
        unresolved_delta="The benchmark omits participation.",
        importance="Participation changes the policy ranking.",
        kill_condition="The benchmark already yields the reversal.",
        proposed_scope="A finite-state decision problem.",
        candidate_archetypes=("mechanism_explanation",),
    )


def entity(
    entity_id: str,
    payload: object,
    *,
    version: int = 1,
    supersedes: EntityVersionRef | None = None,
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=version,
        project_id="project.phase2",
        title=entity_id,
        summary="Phase 2 semantic test object.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=pack_theory_payload(payload),  # type: ignore[arg-type]
        created_at=NOW,
        supersedes=supersedes,
    )


def generic_entity(entity_id: str, entity_type: str = "GenericThing") -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=entity_type,
        version=1,
        project_id="project.phase2",
        title=entity_id,
        summary="Generic exact target.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=FacetPayloads(),
        created_at=NOW,
    )


def benchmark_payload(question_ref: EntityVersionRef, label: str) -> BenchmarkSet:
    return BenchmarkSet(
        question_ref=question_ref,
        benchmarks=(
            BenchmarkRecord(
                benchmark_id=f"benchmark.{label}",
                label=f"Benchmark for {label}.",
                exact_primitives=("one decision maker",),
                timing=("information then action",),
                solution_concept="optimal action",
                prediction="the benchmark ranking",
                unresolved_delta="the target margin is absent",
            ),
        ),
        exact_question_delta=f"Introduce the {label} margin.",
    )


def scoped_g1(
    label: str,
    question: EntityVersion,
    *,
    decision_scope_ref: str | None = None,
) -> tuple[EntityVersion, Decision]:
    question_ref = eref(question.entity_id, question.version)
    dossier = entity(
        f"dossier.g1.{label}",
        GateDossier(
            gate_kind="G1_question_benchmark",
            research_question_ref=question_ref,
            ordered_object_refs=(question_ref,),
            requirements=(
                GateRequirement(
                    requirement_id=f"requirement.delta.{label}",
                    description="The exact benchmark delta is explicit.",
                    evidence_refs=(question_ref,),
                    recorded_condition="evidence_supplied",
                ),
            ),
            proposed_action="approve",
            rationale="The scoped question is ready for human confirmation.",
            prepared_at=NOW,
        ),
    )
    decision = Decision(
        decision_id=f"decision.g1.{label}",
        version=1,
        project_id="project.phase2",
        decision_kind="G1_question_benchmark",
        subject_ref=dossier.entity_id,
        scope_ref=(
            question.entity_id
            if decision_scope_ref is None
            else decision_scope_ref
        ),
        question="Approve this exact question and benchmark scope?",
        options=("approve", "deny"),
        selected_option="approve",
        machine_outcome="approve",
        recommendation="Approve.",
        rationale="The exact scoped dossier is complete.",
        evidence_refs=(dossier.entity_id,),
        required_authority="L2",
        decider=Actor(kind="human", actor_id="researcher"),
        decided_at="2026-07-11T13:00:00Z",
        status="confirmed",
    )
    return dossier, decision


class EntityAndProjectionTests(unittest.TestCase):
    def _legacy_gate(self) -> Decision:
        return Decision(
            decision_id="decision.legacy.g1",
            version=1,
            project_id="project.phase2",
            decision_kind="G1_question_benchmark",
            subject_ref="project.phase2",
            question="Continue?",
            options=("approve", "deny"),
            selected_option="approve",
            recommendation="Approve.",
            rationale="Legacy Phase 1 gate without a typed dossier.",
            required_authority="L2",
            decider=Actor(kind="human", actor_id="researcher"),
            decided_at="2026-07-11T13:00:00Z",
            status="confirmed",
        )

    def test_legacy_phase1_gate_without_dossier_remains_replayable(self) -> None:
        report = validate_theory_projection((), decisions=(self._legacy_gate(),))
        self.assertEqual(report.confirmed_gate_kinds, ())

    def test_registered_entity_parses_and_gate_dossier_cannot_be_superseded(self) -> None:
        question = entity("question.one", question_payload())
        self.assertIsInstance(validate_theory_entity(question), ResearchQuestion)

        dossier_payload = GateDossier(
            gate_kind="G1_question_benchmark",
            research_question_ref=eref(question.entity_id),
            ordered_object_refs=(eref(question.entity_id),),
            requirements=(
                GateRequirement(
                    requirement_id="requirement.delta",
                    description="The benchmark delta is explicit.",
                    evidence_refs=(eref(question.entity_id),),
                    recorded_condition="evidence_supplied",
                ),
            ),
            proposed_action="approve",
            rationale="Ready for a later human decision.",
            prepared_at=NOW,
        )
        first = entity("dossier.g1", dossier_payload)
        second = entity(
            "dossier.g1",
            dossier_payload,
            version=2,
            supersedes=eref("dossier.g1"),
        )
        with self.assertRaisesRegex(TheoryValidationError, "immutable"):
            validate_theory_entity(second, first)

    def test_prediction_register_update_is_append_only(self) -> None:
        prediction = FrozenPrediction(
            prediction_id="prediction.one",
            hypothesis_ref=eref("mechanism.one"),
            predicted_result="Participation reverses the ranking.",
            proposed_economic_chain=("cost changes participation",),
            expected_conditions=("binary participation",),
            expected_ablation_outcome="The reversal disappears.",
            expected_rival_difference="The rival conditions on participation.",
            surprise_or_falsifier="A divisible-choice reversal.",
            frozen_at=NOW,
        )
        before_payload = PredictionRegister(
            question_ref=eref("question.one"),
            mechanism_tournament_ref=eref("tournament.one"),
            original_predictions=(prediction,),
        )
        after_payload = before_payload.model_copy(
            update={
                "original_predictions": (
                    prediction.model_copy(update={"predicted_result": "Post-hoc edit."}),
                )
            }
        )
        before = entity("predictions.one", before_payload)
        after = entity(
            "predictions.one",
            after_payload,
            version=2,
            supersedes=eref("predictions.one"),
        )
        with self.assertRaisesRegex(TheoryValidationError, "immutable"):
            validate_theory_entity(after, before)

    def test_projection_resolves_exact_refs_and_expected_entity_types(self) -> None:
        wrong_target = generic_entity("not.a.question")
        benchmarks = entity(
            "benchmarks.one",
            BenchmarkSet(
                question_ref=eref(wrong_target.entity_id),
                benchmarks=(
                    BenchmarkRecord(
                        benchmark_id="benchmark.zero",
                        label="No participation margin.",
                        exact_primitives=("one receiver",),
                        timing=("signal then action",),
                        solution_concept="optimal action",
                        prediction="higher precision helps",
                        unresolved_delta="participation is fixed",
                    ),
                ),
                exact_question_delta="Endogenize participation.",
            ),
        )
        with self.assertRaisesRegex(TheoryValidationError, "expects.*ResearchQuestion"):
            validate_theory_projection((wrong_target, benchmarks))

    def test_projection_rejects_artifact_hash_mismatch(self) -> None:
        question = entity("question.one", question_payload())
        benchmarks = entity(
            "benchmarks.one",
            BenchmarkSet(
                question_ref=eref(question.entity_id),
                benchmarks=(
                    BenchmarkRecord(
                        benchmark_id="benchmark.zero",
                        label="Benchmark.",
                        exact_primitives=("one receiver",),
                        timing=("signal then action",),
                        solution_concept="optimal action",
                        prediction="precision helps",
                        unresolved_delta="participation is fixed",
                        evidence_refs=(aref("artifact.benchmark", DIGEST_B),),
                    ),
                ),
                exact_question_delta="Endogenize participation.",
            ),
        )
        artifact = ArtifactRegistration(
            artifact_id="artifact.benchmark",
            version=1,
            project_id="project.phase2",
            logical_name="benchmark.txt",
            media_type="text/plain",
            content_hash=DIGEST_A,
            byte_size=1,
            created_at=NOW,
        )
        with self.assertRaisesRegex(TheoryValidationError, "hash-mismatched"):
            validate_theory_projection((question, benchmarks), (artifact,))

    def test_numerical_exploration_cannot_discharge_universal_obligation(self) -> None:
        record = entity(
            "verification.bad",
            VerificationRecord(
                obligation_ref=eref("obligation.universal"),
                claim_graph_ref=eref("claims.one"),
                formal_model_ref=eref("model.one"),
                assumption_map_ref=eref("assumptions.one"),
                verifier=Actor(kind="deterministic_tool", actor_id="enumerator"),
                method="simulation",
                outcome="discharged",
                checked_refs=(eref("obligation.universal"),),
                evidence_refs=(aref("artifact.simulation"),),
                limitations="Only finitely many parameter values were sampled.",
                checked_at=NOW,
            ),
        )
        with self.assertRaisesRegex(TheoryValidationError, "cannot discharge"):
            validate_theory_projection((record,))


class RouteContractTests(unittest.TestCase):
    def _snapshot(self) -> Snapshot:
        return Snapshot(
            project_id="project.phase2",
            head=DIGEST_A,
            chain=(DIGEST_A,),
        )

    def _spec(self, allowed_type: str) -> RouteSpecV2:
        return RouteSpecV2(
            route_id="test.phase2",
            availability="enabled",
            allowed_purposes=("research_discovery",),
            allowed_operations=("entity.create", "route.outcome"),
            allowed_entity_types=(allowed_type,),
            allowed_relation_types=("supports",),
            entry_validator_id="theory_route_entry.v1",
            exit_validator_id="theory_route_exit.v1",
            instruction_bundle_id="test.phase2.v2",
            instruction_bundle_hash=DIGEST_B,
        )

    def _transaction(self, output: EntityVersion) -> Transaction:
        output_ref = eref(output.entity_id, output.version)
        return Transaction(
            transaction_id="transaction.phase2",
            origin="route_run",
            project_id="project.phase2",
            base_revision=DIGEST_A,
            route_run_id="run.phase2",
            route_id="test.phase2",
            route_run_hash=DIGEST_B,
            context_manifest_hash="c" * 64,
            compiled_context_hash="d" * 64,
            actor=Actor(kind="agent", actor_id="theory.agent"),
            intent="Produce one exact theory candidate.",
            operations=(
                CreateEntityOp(entity=output),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id="run.phase2",
                        route_id="test.phase2",
                        outcome="completed_with_candidate",
                        rationale="Candidate produced.",
                        candidate_refs=(output_ref,),
                    )
                ),
            ),
            created_at=NOW,
            parent_transaction_hash=DIGEST_A,
        )

    def test_route_accepts_exact_allowed_candidate(self) -> None:
        output = entity("question.route", question_payload())
        report = validate_phase2_route_transaction(
            self._snapshot(), self._transaction(output), self._spec("ResearchQuestion")
        )
        self.assertEqual(report.parsed_entity_count, 1)

    def test_route_rejects_entity_type_outside_allowlist(self) -> None:
        output = entity("question.route", question_payload())
        with self.assertRaisesRegex(TheoryValidationError, "allowlist"):
            validate_phase2_route_transaction(
                self._snapshot(), self._transaction(output), self._spec("BenchmarkSet")
            )

    def test_route_outcome_must_name_every_exact_scientific_output(self) -> None:
        output = entity("question.route", question_payload())
        transaction = self._transaction(output)
        bad_outcome = RouteOutcome(
            route_run_id="run.phase2",
            route_id="test.phase2",
            outcome="completed_with_candidate",
            rationale="Names a different output.",
            candidate_refs=(eref("question.ghost"),),
        )
        transaction = transaction.model_copy(
            update={
                "operations": (
                    transaction.operations[0],
                    RecordRouteOutcomeOp(outcome=bad_outcome),
                )
            }
        )
        with self.assertRaisesRegex(TheoryValidationError, "not produced"):
            validate_phase2_route_transaction(
                self._snapshot(), transaction, self._spec("ResearchQuestion")
            )

    def test_arbitrary_legacy_decision_cannot_satisfy_required_phase2_gate(self) -> None:
        legacy = EntityAndProjectionTests()._legacy_gate()
        snapshot = self._snapshot().model_copy(
            update={
                "decisions": (legacy,),
                "current_decisions": {legacy.decision_id: 1},
                "effective_decisions": {
                    "legacy": EffectiveDecisionRef(
                        decision_id=legacy.decision_id,
                        version=1,
                        effective_revision=DIGEST_A,
                    )
                },
            }
        )
        transaction = self._transaction(entity("question.route", question_payload())).model_copy(
            update={"authority_basis": (legacy.decision_id,)}
        )
        spec = self._spec("ResearchQuestion").model_copy(
            update={"required_gate_kinds": ("G1_question_benchmark",)}
        )
        with self.assertRaisesRegex(TheoryValidationError, "missing required"):
            validate_phase2_route_transaction(snapshot, transaction, spec)


class RouteScopeBindingTests(unittest.TestCase):
    def _snapshot(
        self,
        questions: tuple[EntityVersion, ...],
        dossier: EntityVersion | None = None,
        decision: Decision | None = None,
    ) -> Snapshot:
        entities = questions + ((dossier,) if dossier is not None else ())
        decisions = (decision,) if decision is not None else ()
        effective = (
            {
                f"effective.{decision.decision_id}": EffectiveDecisionRef(
                    decision_id=decision.decision_id,
                    version=decision.version,
                    effective_revision=DIGEST_A,
                )
            }
            if decision is not None
            else {}
        )
        return Snapshot(
            project_id="project.phase2",
            head=DIGEST_A,
            chain=(DIGEST_A,),
            entity_versions=entities,
            decisions=decisions,
            current_entities={item.entity_id: item.version for item in entities},
            current_decisions=(
                {decision.decision_id: decision.version}
                if decision is not None
                else {}
            ),
            effective_decisions=effective,
        )

    def _spec(
        self,
        allowed_type: str,
        *,
        required_g1: bool,
        supersede: bool = False,
    ) -> RouteSpecV2:
        operations = ["entity.create", "route.outcome"]
        if supersede:
            operations.append("entity.supersede")
        return RouteSpecV2(
            route_id="test.scope.binding",
            availability="enabled",
            allowed_purposes=("research_discovery",),
            allowed_operations=tuple(sorted(operations)),
            allowed_entity_types=(allowed_type,),
            allowed_relation_types=("supports",),
            required_gate_kinds=(
                ("G1_question_benchmark",) if required_g1 else ()
            ),
            entry_validator_id="theory_route_entry.v1",
            exit_validator_id="theory_route_exit.v1",
            instruction_bundle_id="test.scope.binding.v2",
            instruction_bundle_hash=DIGEST_B,
        )

    def _transaction(
        self,
        outputs: tuple[EntityVersion, ...],
        *,
        evidence_refs: tuple[EntityVersionRef, ...],
        decision: Decision | None = None,
        supersede: bool = False,
    ) -> Transaction:
        entity_ops = []
        changed_facets = []
        for output in outputs:
            if supersede:
                previous = eref(output.entity_id, output.version - 1)
                entity_ops.append(
                    SupersedeEntityOp(previous=previous, entity=output)
                )
                changed_facets.append(
                    ChangedFacets(
                        entity_id=output.entity_id,
                        previous_version=output.version - 1,
                        new_version=output.version,
                        facets=("economic_interpretation",),
                    )
                )
            else:
                entity_ops.append(CreateEntityOp(entity=output))
        candidates = tuple(eref(item.entity_id, item.version) for item in outputs)
        return Transaction(
            transaction_id="transaction.scope.binding",
            origin="route_run",
            project_id="project.phase2",
            base_revision=DIGEST_A,
            route_run_id="run.scope.binding",
            route_id="test.scope.binding",
            route_run_hash=DIGEST_B,
            context_manifest_hash="c" * 64,
            compiled_context_hash="d" * 64,
            actor=Actor(kind="agent", actor_id="theory.agent"),
            intent="Test exact ResearchQuestion scope binding.",
            changed_facets=tuple(changed_facets),
            operations=(
                *entity_ops,
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id="run.scope.binding",
                        route_id="test.scope.binding",
                        outcome="completed_with_candidate",
                        rationale="Exact scoped candidates produced.",
                        candidate_refs=candidates,
                    )
                ),
            ),
            evidence_refs=evidence_refs,
            authority_basis=((decision.decision_id,) if decision is not None else ()),
            created_at=NOW,
            parent_transaction_hash=DIGEST_A,
        )

    def test_same_scope_required_g1_route_is_accepted(self) -> None:
        question = entity("question.scope.a", question_payload())
        dossier, decision = scoped_g1("scope.a", question)
        output = entity(
            "benchmarks.scope.a",
            benchmark_payload(eref(question.entity_id), "scope.a"),
        )
        report = validate_phase2_route_transaction(
            self._snapshot((question,), dossier, decision),
            self._transaction(
                (output,), evidence_refs=(eref(question.entity_id),), decision=decision
            ),
            self._spec("BenchmarkSet", required_g1=True),
        )
        self.assertEqual(report.confirmed_gate_kinds, ("G1_question_benchmark",))

    def test_gate_for_question_a_cannot_authorize_question_b_with_padding(self) -> None:
        question_a = entity("question.scope.a", question_payload())
        question_b = entity("question.scope.b", question_payload())
        dossier_a, decision_a = scoped_g1("scope.a", question_a)
        output_b = entity(
            "benchmarks.scope.b",
            benchmark_payload(eref(question_b.entity_id), "scope.b"),
        )
        transaction = self._transaction(
            (output_b,),
            # The attack explicitly pads the correct A root alongside B.
            evidence_refs=(eref(question_a.entity_id), eref(question_b.entity_id)),
            decision=decision_a,
        )
        with self.assertRaisesRegex(
            TheoryValidationError, "different ResearchQuestion scopes"
        ):
            validate_phase2_route_transaction(
                self._snapshot((question_a, question_b), dossier_a, decision_a),
                transaction,
                self._spec("BenchmarkSet", required_g1=True),
            )

    def test_decision_scope_ref_mismatch_is_rejected_in_projection(self) -> None:
        question_a = entity("question.scope.a", question_payload())
        dossier_a, bad_decision = scoped_g1(
            "scope.a", question_a, decision_scope_ref="question.scope.b"
        )
        with self.assertRaisesRegex(TheoryValidationError, "scope_ref"):
            validate_theory_projection(
                (question_a, dossier_a), decisions=(bad_decision,)
            )

    def test_question_v1_gate_cannot_authorize_question_v2_output(self) -> None:
        question_v1 = entity("question.scope.versioned", question_payload())
        dossier_v1, decision_v1 = scoped_g1("scope.versioned.v1", question_v1)
        question_v2 = entity(
            question_v1.entity_id,
            question_payload().model_copy(
                update={"unresolved_delta": "A revised exact benchmark delta."}
            ),
            version=2,
            supersedes=eref(question_v1.entity_id),
        )
        with self.assertRaisesRegex(
            TheoryValidationError, "different ResearchQuestion scopes"
        ):
            validate_phase2_route_transaction(
                self._snapshot((question_v1,), dossier_v1, decision_v1),
                self._transaction(
                    (question_v2,),
                    evidence_refs=(eref(question_v1.entity_id),),
                    decision=decision_v1,
                    supersede=True,
                ),
                self._spec(
                    "ResearchQuestion", required_g1=True, supersede=True
                ),
            )

    def test_one_transaction_cannot_mix_two_question_scopes(self) -> None:
        question_a = entity("question.scope.a", question_payload())
        question_b = entity("question.scope.b", question_payload())
        output_a = entity(
            "benchmarks.scope.a",
            benchmark_payload(eref(question_a.entity_id), "scope.a"),
        )
        output_b = entity(
            "benchmarks.scope.b",
            benchmark_payload(eref(question_b.entity_id), "scope.b"),
        )
        with self.assertRaisesRegex(TheoryValidationError, "cannot mix"):
            validate_phase2_route_transaction(
                self._snapshot((question_a, question_b)),
                self._transaction(
                    (output_a, output_b),
                    evidence_refs=(
                        eref(question_a.entity_id),
                        eref(question_b.entity_id),
                    ),
                ),
                self._spec("BenchmarkSet", required_g1=False),
            )


if __name__ == "__main__":
    unittest.main()
