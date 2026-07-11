"""Isolation and replay contracts for evaluation-specific route contexts."""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.context import (
    ContextAccessError,
    ContextCompilationError,
    compile_context,
    make_context_manifest,
)
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    ContextManifest,
    Decision,
    DecisionVersionRef,
    EffectiveDecisionRef,
    EntityVersion,
    EntityVersionRef,
    FacetPayloads,
    RecordRouteOutcomeOp,
    RelationVersion,
    RiskOrBlocker,
    RouteOutcome,
    RouteRun,
    RouteSpecV2,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V2_HASH
from econ_theorist.runs import (
    compiled_context_path,
    context_path,
    provenance_bytes,
    run_directory,
    run_path,
)
from econ_theorist.runtime import ObjectStore, StoreLayout
from econ_theorist.runtime.replay import (
    PrivacyFlowError,
    _validate_operational_provenance,
    validate_route_context_output_flow,
)
from econ_theorist.theory import (
    BlindCaseManifest,
    PreResultBrief,
    TransformOperation,
    TransformedVariantManifest,
    ValidatedArgumentPackage,
    pack_theory_payload,
)


PROJECT_ID = "project.evaluation.context"
HEAD = "1" * 64
AGENT = Actor(kind="agent", actor_id="agent.evaluator")
HUMAN = Actor(kind="human", actor_id="human.protocol.owner")
SEALED = (
    "confirmatory_holdout",
    "project_research",
    "sealed_evaluator",
)


def _route(route_id: str, purpose: str) -> RouteSpecV2:
    return RouteSpecV2(
        route_id=route_id,
        route_version=2,
        availability="enabled",
        authority_ceiling="L1",
        allowed_purposes=(purpose,),
        required_compartments=("project_research",),
        allowed_operations=("route.outcome",),
        allowed_entity_types=("VAPComparisonRecord",),
        allowed_relation_types=("tests",),
        required_input_entities=(),
        required_output_entities=(),
        required_output_relations=(),
        required_gate_kinds=(),
        entry_validator_id="theory_route_entry.v1",
        exit_validator_id="theory_route_exit.v1",
        instruction_bundle_id=f"{route_id}.v2",
        instruction_bundle_hash="2" * 64,
    )


def _legacy_entity(
    entity_id: str,
    entity_type: str,
    *,
    privacy: str = "project_private",
    compartments: tuple[str, ...] = ("project_research",),
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=entity_type,
        version=1,
        project_id=PROJECT_ID,
        title=entity_id,
        summary=f"Legacy {entity_type} context fixture.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=FacetPayloads(formal={"fixture": entity_id}),
        privacy=privacy,  # type: ignore[arg-type]
        access_compartments=compartments,
        created_at="2026-07-11T16:00:00Z",
    )


class EvaluationContextTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.layout = StoreLayout.at(temporary.name).ensure()

        artifact_values = {
            "artifact.source.paper": b"sealed source paper excerpt",
            "artifact.gold.signature": b'{"gold":"signature"}',
            "artifact.hidden.probe": b'{"probe":"boundary"}',
            "artifact.answer.key": b'{"answer":"hidden"}',
            "artifact.forward.map": b'{"forward":"rename"}',
            "artifact.inverse.map": b'{"inverse":"rename"}',
            "artifact.invariant": b'{"signature":"invariant"}',
        }
        registrations: list[ArtifactRegistration] = []
        refs: dict[str, ArtifactDependencyRef] = {}
        store = ObjectStore(self.layout)
        for artifact_id, data in artifact_values.items():
            digest = sha256_digest(data)
            registration = ArtifactRegistration(
                artifact_id=artifact_id,
                version=1,
                project_id=PROJECT_ID,
                logical_name=artifact_id,
                media_type="application/json",
                content_hash=digest,
                byte_size=len(data),
                privacy="restricted",
                access_compartments=SEALED,
                created_at="2026-07-11T16:00:01Z",
            )
            registrations.append(registration)
            refs[artifact_id] = ArtifactDependencyRef(
                artifact_id=artifact_id, version=1, content_hash=digest
            )
            store.install_bytes("artifacts", digest, data)
        self.artifact_values = artifact_values
        self.refs = refs

        base_brief_ref = EntityVersionRef(entity_id="brief.base.sealed", version=1)
        transformed_brief_ref = EntityVersionRef(
            entity_id="brief.transformed", version=1
        )
        candidate_ref = EntityVersionRef(entity_id="vap.candidate.sealed", version=1)
        blind_ref = EntityVersionRef(entity_id="case.blind.manifest", version=1)
        transformed_ref = EntityVersionRef(
            entity_id="case.transformed.manifest", version=1
        )
        freeze_ref = DecisionVersionRef(
            decision_id="decision.evaluation.freeze", version=1
        )
        blind = EntityVersion(
            entity_id=blind_ref.entity_id,
            entity_type="BlindCaseManifest",
            version=1,
            project_id=PROJECT_ID,
            title="Sealed blind case",
            summary="Exact blind case manifest.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                BlindCaseManifest(
                    case_id="case.sealed.001",
                    layer="transformed",
                    pre_result_brief_ref=base_brief_ref,
                    gold_package_ref=EntityVersionRef(
                        entity_id="vap.gold.sealed", version=1
                    ),
                    source_paper_refs=(refs["artifact.source.paper"],),
                    gold_semantic_refs=(refs["artifact.gold.signature"],),
                    hidden_probe_refs=(refs["artifact.hidden.probe"],),
                    answer_key_ref=refs["artifact.answer.key"],
                    generator_compartments=("sealed_generator",),
                    evaluator_compartments=("sealed_evaluator",),
                    attempt_id="attempt.sealed.001",
                )
            ),
            # Deliberately less restrictive than its nested artifacts.  The
            # privacy-join test proves the nested registrations still govern.
            privacy="project_private",
            access_compartments=("project_research",),
            created_at="2026-07-11T16:00:02Z",
        )
        transformed = EntityVersion(
            entity_id=transformed_ref.entity_id,
            entity_type="TransformedVariantManifest",
            version=1,
            project_id=PROJECT_ID,
            title="Sealed transform",
            summary="Exact forward and inverse transform evidence.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                TransformedVariantManifest(
                    attempt_id="attempt.sealed.001",
                    base_case_manifest_ref=blind_ref,
                    transformed_brief_ref=transformed_brief_ref,
                    operations=(
                        TransformOperation(
                            operation_id="transform.rename",
                            kind="semantic_rename",
                            public_description="Rename economic labels.",
                            exact_forward_map_ref=refs["artifact.forward.map"],
                        ),
                    ),
                    hidden_inverse_map_ref=refs["artifact.inverse.map"],
                    invariant_signature_ref=refs["artifact.invariant"],
                    implementation_freeze_ref=freeze_ref,
                    generated_at="2026-07-11T16:00:03Z",
                )
            ),
            privacy="project_private",
            access_compartments=("project_research",),
            created_at="2026-07-11T16:00:03Z",
        )
        question_ref = EntityVersionRef(entity_id="question.sealed", version=1)
        benchmark_ref = EntityVersionRef(entity_id="benchmarks.sealed", version=1)
        primitive_ref = EntityVersionRef(entity_id="primitives.sealed", version=1)
        base_brief = EntityVersion(
            entity_id=base_brief_ref.entity_id,
            entity_type="PreResultBrief",
            version=1,
            project_id=PROJECT_ID,
            title="Base pre-result brief",
            summary="The frozen base brief for one sealed attempt.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                PreResultBrief(
                    question_ref=question_ref,
                    benchmark_set_ref=benchmark_ref,
                    primitive_graph_ref=primitive_ref,
                    institution="The untransformed benchmark institution.",
                    allowed_context_refs=(question_ref, benchmark_ref, primitive_ref),
                    allowed_tools=("hand_derivation",),
                    budget_units=8_000,
                    excluded_information=("The transformed labels and inverse map.",),
                    attempt_id="attempt.sealed.001",
                )
            ),
            privacy="restricted",
            access_compartments=SEALED,
            created_at="2026-07-11T16:00:01Z",
        )
        transformed_brief = EntityVersion(
            entity_id=transformed_brief_ref.entity_id,
            entity_type="PreResultBrief",
            version=1,
            project_id=PROJECT_ID,
            title="Transformed pre-result brief",
            summary="The frozen transformed brief for one sealed attempt.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(
                PreResultBrief(
                    question_ref=question_ref,
                    benchmark_set_ref=benchmark_ref,
                    primitive_graph_ref=primitive_ref,
                    institution="The semantically transformed institution.",
                    allowed_context_refs=(question_ref, benchmark_ref, primitive_ref),
                    allowed_tools=("hand_derivation",),
                    budget_units=8_000,
                    excluded_information=("Base labels, gold result, and inverse map.",),
                    attempt_id="attempt.sealed.001",
                )
            ),
            privacy="restricted",
            access_compartments=SEALED,
            created_at="2026-07-11T16:00:02Z",
        )
        entity_ref = lambda entity_id: EntityVersionRef(  # noqa: E731
            entity_id=entity_id, version=1
        )
        candidate_payload = ValidatedArgumentPackage(
            question_ref=question_ref,
            benchmark_set_ref=benchmark_ref,
            primitive_graph_ref=primitive_ref,
            selected_mechanism_ref=entity_ref("mechanism.candidate"),
            serious_rejected_rival_refs=(entity_ref("mechanism.rival"),),
            prediction_register_ref=entity_ref("predictions.candidate"),
            example_suite_ref=entity_ref("examples.candidate"),
            economic_argument_graph_ref=entity_ref("argument.candidate"),
            implementation_tournament_ref=entity_ref("implementations.candidate"),
            formal_model_ref=entity_ref("formal.candidate"),
            formalization_map_ref=entity_ref("formalization.candidate"),
            assumption_map_ref=entity_ref("assumptions.candidate"),
            claim_graph_ref=entity_ref("claims.candidate"),
            verification_bundle_ref=entity_ref("verification.candidate"),
            closest_theory_map_ref=entity_ref("closest.candidate"),
            absorption_assessment_ref=entity_ref("absorption.candidate"),
            result_portfolio_ref=entity_ref("portfolio.candidate"),
            prior_gate_decision_refs=tuple(
                DecisionVersionRef(decision_id=f"decision.g{index}", version=1)
                for index in range(1, 5)
            ),
            g5_dossier_ref=entity_ref("dossier.g5.candidate"),
            economic_nugget="The sealed candidate's economic mechanism.",
            qualified_novelty="Evaluation fixture; no novelty is released.",
            unresolved_risks=("The attempt remains evaluator-only.",),
            prohibited_overclaims=("Do not release a confirmatory claim.",),
            release_mode="evaluation_only",
            novelty_claim_mode="none",
            evaluation_attempt_id="attempt.sealed.001",
            pre_result_brief_ref=transformed_brief_ref,
            generator_actor=Actor(kind="agent", actor_id="agent.blind.generator"),
        )
        candidate = EntityVersion(
            entity_id=candidate_ref.entity_id,
            entity_type="ValidatedArgumentPackage",
            version=1,
            project_id=PROJECT_ID,
            title="Locked evaluation candidate",
            summary="Candidate fixed before the evaluator sees sealed materials.",
            status=ScientificStatus(lifecycle="proposed"),
            facets=pack_theory_payload(candidate_payload),
            privacy="restricted",
            access_compartments=SEALED,
            created_at="2026-07-11T16:00:04Z",
        )
        candidate_bytes = canonical_json_bytes(candidate)
        candidate_lock_id = "candidate.lock.attempt.sealed.001"
        candidate_lock = ArtifactRegistration(
            artifact_id=candidate_lock_id,
            version=1,
            project_id=PROJECT_ID,
            logical_name="Exact pre-evaluation candidate lock",
            media_type="application/vnd.econ-theorist.candidate-lock+json",
            content_hash=sha256_digest(candidate_bytes),
            byte_size=len(candidate_bytes),
            privacy="restricted",
            access_compartments=SEALED,
            created_at="2026-07-11T16:00:04Z",
        )
        registrations.append(candidate_lock)
        refs[candidate_lock_id] = ArtifactDependencyRef(
            artifact_id=candidate_lock.artifact_id,
            version=candidate_lock.version,
            content_hash=candidate_lock.content_hash,
        )
        artifact_values[candidate_lock_id] = candidate_bytes
        store.install_bytes("artifacts", candidate_lock.content_hash, candidate_bytes)
        neighbor = _legacy_entity("hidden.neighbor.identity", "HiddenNote")
        holdout = _legacy_entity(
            "holdout.prepare.focus",
            "HoldoutInput",
            privacy="restricted",
            compartments=SEALED,
        )
        freeze = Decision(
            decision_id=freeze_ref.decision_id,
            version=1,
            project_id=PROJECT_ID,
            decision_kind="theory_mode",
            subject_ref=transformed_brief.entity_id,
            scope_ref="attempt.sealed.001",
            question="Freeze this evaluation implementation?",
            options=("freeze", "reopen"),
            selected_option="freeze",
            recommendation="Freeze before the hidden evaluation.",
            rationale="The implementation is fixed before evaluator access.",
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-11T16:00:05Z",
            status="confirmed",
            privacy="restricted",
            access_compartments=SEALED,
        )
        relation = RelationVersion(
            relation_id="relation.manifest.hidden.neighbor",
            relation_type="includes",
            version=1,
            project_id=PROJECT_ID,
            source=blind_ref,
            target=EntityVersionRef(entity_id=neighbor.entity_id, version=1),
            dependency_mode="trace_only",
            privacy="restricted",
            access_compartments=SEALED,
            created_at="2026-07-11T16:00:04Z",
        )
        blocker = RiskOrBlocker(
            blocker_id="blocker.hidden.neighbor.identity",
            project_id=PROJECT_ID,
            kind="sealed_evaluation_note",
            severity="warning",
            summary="This protected identity must not enter evaluator context.",
            affected_refs=(EntityVersionRef(entity_id=neighbor.entity_id, version=1),),
            created_at="2026-07-11T16:00:04Z",
            privacy="restricted",
            access_compartments=SEALED,
        )
        entities = (
            blind,
            transformed,
            base_brief,
            transformed_brief,
            candidate,
            neighbor,
            holdout,
        )
        self.snapshot = Snapshot(
            project_id=PROJECT_ID,
            head=HEAD,
            chain=(HEAD,),
            entity_versions=entities,
            relation_versions=(relation,),
            decisions=(freeze,),
            artifacts=tuple(registrations),
            blockers=(blocker,),
            current_entities={item.entity_id: 1 for item in entities},
            current_relations={relation.relation_id: 1},
            current_decisions={freeze.decision_id: 1},
            current_artifacts={item.artifact_id: 1 for item in registrations},
            effective_decisions={
                "evaluation.freeze.attempt.sealed.001": EffectiveDecisionRef(
                    decision_id=freeze.decision_id,
                    version=freeze.version,
                    effective_revision=HEAD,
                )
            },
        )
        self.blind = blind
        self.transformed = transformed
        self.base_brief = base_brief
        self.transformed_brief = transformed_brief
        self.candidate = candidate
        self.candidate_lock = candidate_lock
        self.evaluate_route = _route(
            "evaluate.blind_argument_package", "confirmatory_evaluation"
        )
        self.prepare_route = _route(
            "prepare.blind_case", "confirmatory_case_preparation"
        )

    def _compile_evaluate(self, *focus: str):
        if self.candidate.entity_id not in focus:
            focus = (*focus, self.candidate.entity_id)
        with patch(
            "econ_theorist.context._route_instructions",
            return_value=("Evaluate only the exact sealed focus.",),
        ):
            return compile_context(
                self.snapshot,
                route=self.evaluate_route,
                actor=AGENT,
                purpose="confirmatory_evaluation",
                compartments=SEALED,
                privacy_clearance="restricted",
                focus_entity_ids=focus,
                budget_units=100_000,
                layout=self.layout,
            )

    def _outcome_transaction(self, *, restricted: bool) -> Transaction:
        privacy = "restricted" if restricted else "project_private"
        compartments = SEALED if restricted else ("project_research",)
        outcome = RouteOutcome(
            route_run_id="run.evaluation.context",
            route_id=self.evaluate_route.route_id,
            outcome="failed",
            rationale="Exercise the evaluation context privacy join.",
            privacy=privacy,  # type: ignore[arg-type]
            access_compartments=compartments,
        )
        return Transaction(
            transaction_id=(
                "transaction.evaluation.context.restricted"
                if restricted
                else "transaction.evaluation.context.open"
            ),
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=HEAD,
            route_run_id=outcome.route_run_id,
            route_id=outcome.route_id,
            route_run_hash="3" * 64,
            context_manifest_hash="4" * 64,
            compiled_context_hash="5" * 64,
            actor=AGENT,
            intent="Exercise the sealed evaluation output join.",
            operations=(RecordRouteOutcomeOp(outcome=outcome),),
            privacy=privacy,  # type: ignore[arg-type]
            access_compartments=compartments,
            created_at="2026-07-11T16:01:00Z",
            parent_transaction_hash=HEAD,
        )

    def test_evaluate_uses_exact_focus_and_embeds_verified_inputs(self) -> None:
        compiled = self._compile_evaluate(
            self.blind.entity_id, self.transformed.entity_id
        )
        payload = compiled.payload
        self.assertEqual(
            payload["evaluation_selector"],
            {"mode": "exact_focus.v1", "optional_neighbors": False},
        )
        self.assertEqual(payload["relations"], ())
        self.assertEqual(payload["effective_decisions"], ())
        self.assertEqual(payload["status_source_decisions"], ())
        self.assertEqual(payload["derived_status"], {})
        self.assertEqual(payload["blockers"], ())
        self.assertEqual(payload["omissions"], ())
        selected_ids = {item["entity_id"] for item in payload["entities"]}
        self.assertEqual(
            selected_ids,
            {
                self.blind.entity_id,
                self.transformed.entity_id,
                self.candidate.entity_id,
            },
        )
        self.assertNotIn("hidden.neighbor.identity", compiled.encoded.decode("utf-8"))
        self.assertNotIn("privacy:neighbor", compiled.encoded.decode("utf-8"))

        artifact_records = payload["evaluation_artifacts"]
        self.assertEqual(len(artifact_records), len(self.artifact_values))
        decoded = {
            item["registration"]["artifact_id"]: base64.b64decode(
                item["content_base64"], validate=True
            )
            for item in artifact_records
        }
        self.assertEqual(decoded, self.artifact_values)
        self.assertEqual(
            decoded[self.candidate_lock.artifact_id],
            canonical_json_bytes(self.candidate),
        )
        for item in artifact_records:
            registration = item["registration"]
            data = decoded[registration["artifact_id"]]
            self.assertEqual(sha256_digest(data), registration["content_hash"])
            self.assertEqual(len(data), registration["byte_size"])
        self.assertEqual(
            [item["decision_id"] for item in payload["evaluation_decisions"]],
            ["decision.evaluation.freeze"],
        )
        self.assertEqual(sha256_digest(compiled.encoded), compiled.context_hash)

    def test_holdout_purposes_are_narrow_and_prepare_is_exact_focus(self) -> None:
        holdout_id = "holdout.prepare.focus"
        prepare_focus = (
            self.base_brief.entity_id,
            self.transformed_brief.entity_id,
        )
        with patch(
            "econ_theorist.context._route_instructions",
            return_value=("Prepare only the exact holdout focus.",),
        ):
            prepared = compile_context(
                self.snapshot,
                route=self.prepare_route,
                actor=HUMAN,
                purpose="confirmatory_case_preparation",
                compartments=SEALED,
                privacy_clearance="restricted",
                focus_entity_ids=prepare_focus,
                budget_units=20_000,
                layout=self.layout,
            )
            self.assertEqual(
                [item["entity_id"] for item in prepared.payload["entities"]],
                sorted(prepare_focus),
            )
            self.assertEqual(prepared.payload["relations"], ())
            self.assertEqual(prepared.payload["evaluation_artifacts"], ())
            self.assertEqual(
                [
                    item["decision_id"]
                    for item in prepared.payload["evaluation_decisions"]
                ],
                ["decision.evaluation.freeze"],
            )
            with self.assertRaisesRegex(ContextAccessError, "requires purpose"):
                compile_context(
                    self.snapshot,
                    route=self.prepare_route,
                    actor=HUMAN,
                    purpose="research_repair",
                    compartments=SEALED,
                    privacy_clearance="restricted",
                    focus_entity_ids=prepare_focus,
                    budget_units=20_000,
                    layout=self.layout,
                )

            ordinary = _route("repair.dependency", "research_repair")
            with self.assertRaises(ContextAccessError):
                compile_context(
                    self.snapshot,
                    route=ordinary,
                    actor=AGENT,
                    purpose="research_repair",
                    compartments=SEALED,
                    privacy_clearance="restricted",
                    focus_entity_ids=(holdout_id,),
                    budget_units=20_000,
                    layout=self.layout,
                )

    def test_evaluation_artifact_bytes_must_exist_in_the_object_store(self) -> None:
        empty_layout = StoreLayout.at(Path(self.layout.project_root) / "empty").ensure()
        with patch(
            "econ_theorist.context._route_instructions",
            return_value=("Evaluate only the exact sealed focus.",),
        ):
            with self.assertRaisesRegex(
                ContextCompilationError, "unavailable or corrupt"
            ):
                compile_context(
                    self.snapshot,
                    route=self.evaluate_route,
                    actor=AGENT,
                    purpose="confirmatory_evaluation",
                    compartments=SEALED,
                    privacy_clearance="restricted",
                    focus_entity_ids=(
                        self.blind.entity_id,
                        self.candidate.entity_id,
                    ),
                    budget_units=100_000,
                    layout=empty_layout,
                )

    def test_evaluation_rejects_a_candidate_lock_over_different_bytes(self) -> None:
        mismatched = self.candidate_lock.model_copy(
            update={"content_hash": "0" * 64}
        )
        snapshot = self.snapshot.model_copy(
            update={
                "artifacts": tuple(
                    mismatched
                    if item.artifact_id == mismatched.artifact_id
                    else item
                    for item in self.snapshot.artifacts
                )
            }
        )
        with patch(
            "econ_theorist.context._route_instructions",
            return_value=("Evaluate only the exact sealed focus.",),
        ):
            with self.assertRaisesRegex(ContextCompilationError, "candidate lock"):
                compile_context(
                    snapshot,
                    route=self.evaluate_route,
                    actor=AGENT,
                    purpose="confirmatory_evaluation",
                    compartments=SEALED,
                    privacy_clearance="restricted",
                    focus_entity_ids=(
                        self.blind.entity_id,
                        self.candidate.entity_id,
                    ),
                    budget_units=100_000,
                    layout=self.layout,
                )

    def test_prepare_rejects_a_freeze_that_is_not_effective(self) -> None:
        snapshot = self.snapshot.model_copy(update={"effective_decisions": {}})
        with patch(
            "econ_theorist.context._route_instructions",
            return_value=("Prepare only the exact holdout focus.",),
        ):
            with self.assertRaisesRegex(ContextCompilationError, "effective human"):
                compile_context(
                    snapshot,
                    route=self.prepare_route,
                    actor=HUMAN,
                    purpose="confirmatory_case_preparation",
                    compartments=SEALED,
                    privacy_clearance="restricted",
                    focus_entity_ids=(
                        self.base_brief.entity_id,
                        self.transformed_brief.entity_id,
                    ),
                    budget_units=20_000,
                    layout=self.layout,
                )

    def test_output_privacy_join_includes_nested_artifact_records(self) -> None:
        compiled = self._compile_evaluate(self.blind.entity_id)
        with self.assertRaisesRegex(
            PrivacyFlowError, "more open|drops context compartments"
        ):
            validate_route_context_output_flow(
                self._outcome_transaction(restricted=False),
                json.loads(compiled.encoded.decode("utf-8")),
            )
        validate_route_context_output_flow(
            self._outcome_transaction(restricted=True),
            json.loads(compiled.encoded.decode("utf-8")),
        )

    def test_provenance_and_replay_recompile_the_same_evaluation_bytes(self) -> None:
        focus = (self.blind.entity_id, self.candidate.entity_id)
        compiled = self._compile_evaluate(*focus)
        manifest = make_context_manifest(
            compiled,
            context_manifest_id="context.evaluation.exact",
            snapshot=self.snapshot,
            route=self.evaluate_route,
            actor=AGENT,
            purpose="confirmatory_evaluation",
            compartments=SEALED,
            privacy_clearance="restricted",
            focus_entity_ids=focus,
            budget_units=100_000,
            created_at="2026-07-11T16:02:00Z",
        )
        self.assertEqual(manifest.decision_registry_version, 1)
        run = RouteRun(
            route_run_id="run.evaluation.context",
            project_id=PROJECT_ID,
            base_revision=HEAD,
            route_id=self.evaluate_route.route_id,
            route_version=2,
            actor=AGENT,
            purpose="confirmatory_evaluation",
            compartments=SEALED,
            privacy_clearance="restricted",
            focus_entity_ids=focus,
            context_manifest_id=manifest.context_manifest_id,
            context_hash=compiled.context_hash,
            status="running",
            created_at=manifest.created_at,
        )
        run_directory(self.layout, run.route_run_id).mkdir(parents=True)
        run_bytes = canonical_json_bytes(run)
        manifest_bytes = canonical_json_bytes(manifest)
        run_path(self.layout, run.route_run_id).write_bytes(run_bytes)
        context_path(self.layout, run.route_run_id).write_bytes(manifest_bytes)
        compiled_context_path(self.layout, run.route_run_id).write_bytes(
            compiled.encoded
        )

        with (
            patch("econ_theorist.runs.get_route", return_value=self.evaluate_route),
            patch(
                "econ_theorist.runs.instruction_bundle_bytes",
                return_value=b"Evaluate only the exact sealed focus.\n",
            ),
            patch(
                "econ_theorist.runs.authorize_route",
                return_value=self.evaluate_route,
            ),
            patch("econ_theorist.runs.validate_phase2_route_entry"),
            patch("econ_theorist.runtime.replay.replay", return_value=self.snapshot),
            patch(
                "econ_theorist.context._route_instructions",
                return_value=("Evaluate only the exact sealed focus.",),
            ),
        ):
            preserved = provenance_bytes(self.layout, run.route_run_id)
        self.assertEqual(
            preserved,
            {
                "run": run_bytes,
                "manifest": manifest_bytes,
                "context": compiled.encoded,
            },
        )

        transaction = self._outcome_transaction(restricted=True).model_copy(
            update={
                "route_run_hash": sha256_digest(run_bytes),
                "context_manifest_hash": sha256_digest(manifest_bytes),
                "compiled_context_hash": sha256_digest(compiled.encoded),
            }
        )
        store = ObjectStore(self.layout)
        for data in preserved.values():
            store.install_bytes("provenance", sha256_digest(data), data)
        with (
            patch(
                "econ_theorist.runtime.replay.load_route_registry_by_hash",
                return_value=object(),
            ),
            patch(
                "econ_theorist.runtime.replay.route_spec",
                return_value=self.evaluate_route,
            ),
            patch(
                "econ_theorist.context._route_instructions",
                return_value=("Evaluate only the exact sealed focus.",),
            ),
        ):
            bound_hash = _validate_operational_provenance(
                self.layout, transaction, self.snapshot
            )
        self.assertEqual(bound_hash, ROUTE_REGISTRY_V2_HASH)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
