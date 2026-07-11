"""Adversarial entry/exit tests for the Phase 2 blind-evaluation protocol."""

from __future__ import annotations

import unittest
from collections.abc import Mapping

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase2_scientific_closure import (
    CREATED_AT,
    HUMAN,
    PROJECT_ID,
    ClosureFixture,
)

from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    ChangedFacets,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EffectiveDecisionRef,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    ScientificStatus,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from econ_theorist.route_registry import get_route
from econ_theorist.theory import (
    BlindCaseManifest,
    PreResultBrief,
    SignatureDimensionComparison,
    TheoryPayload,
    TransformOperation,
    TransformedVariantManifest,
    VAPComparisonRecord,
    ValidatedArgumentPackage,
    pack_theory_payload,
    parse_theory_entity,
)
from econ_theorist.theory_validation import (
    TheoryValidationError,
    validate_phase2_route_entry,
    validate_phase2_route_transaction,
)


HEAD = "a" * 64
ROUTE_HASH = "b" * 64
CONTEXT_HASH = "c" * 64
COMPILED_HASH = "d" * 64
ATTEMPT = "attempt.blind.contract.001"
GENERATOR = Actor(kind="agent", actor_id="agent.blind.generator")
EVALUATOR = Actor(kind="agent", actor_id="agent.blind.evaluator")
BUILDER = Actor(kind="agent", actor_id="agent.blind.case_builder")
SEALED = ("blind_evaluator", "confirmatory_holdout")
GENERATOR_VISIBLE = ("blind_generator", "project_research")
SIGNATURE_DIMENSIONS = (
    "question_delta",
    "benchmarks",
    "mechanism_graph",
    "rivals",
    "frozen_predictions",
    "functional_examples",
    "implementations",
    "formalization",
    "claim_scope",
    "assumptions",
    "proof_obligations",
    "boundaries",
    "absorption",
    "portfolio",
    "gates",
    "prohibited_overclaims",
    "dependency_traces",
)


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def aref(registration: ArtifactRegistration) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=registration.artifact_id,
        version=registration.version,
        content_hash=registration.content_hash,
    )


def _artifact(
    artifact_id: str,
    *,
    media_type: str = "application/json",
    content_hash: str | None = None,
) -> ArtifactRegistration:
    data = artifact_id.encode("utf-8")
    return ArtifactRegistration(
        artifact_id=artifact_id,
        version=1,
        project_id=PROJECT_ID,
        logical_name=f"{artifact_id}.json",
        media_type=media_type,
        content_hash=content_hash or sha256_digest(data),
        byte_size=len(data),
        privacy="restricted",
        access_compartments=SEALED,
        created_at=CREATED_AT,
    )


def _entity(
    entity_id: str,
    payload: TheoryPayload,
    *,
    artifact_refs: tuple[ArtifactDependencyRef, ...] = (),
    privacy: str = "project_private",
    access_compartments: tuple[str, ...] = ("project_research",),
    version: int = 1,
    supersedes: EntityVersionRef | None = None,
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=version,
        project_id=PROJECT_ID,
        title=entity_id,
        summary=f"Blind-evaluation fixture for {type(payload).__name__}.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=pack_theory_payload(payload),
        artifact_refs=artifact_refs,
        privacy=privacy,  # type: ignore[arg-type]
        access_compartments=access_compartments,
        created_at=CREATED_AT,
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
        created_at=CREATED_AT,
    )


def _rewrite_refs(
    value: object,
    entity_ids: Mapping[str, str],
    decision_ids: Mapping[str, str],
) -> object:
    if isinstance(value, dict):
        rewritten = {
            key: _rewrite_refs(item, entity_ids, decision_ids)
            for key, item in value.items()
        }
        entity_id = rewritten.get("entity_id")
        if isinstance(entity_id, str):
            rewritten["entity_id"] = entity_ids.get(entity_id, entity_id)
        decision_id = rewritten.get("decision_id")
        if isinstance(decision_id, str):
            rewritten["decision_id"] = decision_ids.get(decision_id, decision_id)
        return rewritten
    if isinstance(value, tuple):
        return tuple(_rewrite_refs(item, entity_ids, decision_ids) for item in value)
    if isinstance(value, list):
        return [_rewrite_refs(item, entity_ids, decision_ids) for item in value]
    return value


def _snapshot(
    fixture: "BlindProtocolFixture",
    *,
    extra_entities: tuple[EntityVersion, ...] = (),
    extra_artifacts: tuple[ArtifactRegistration, ...] = (),
    extra_relations: tuple[RelationVersion, ...] = (),
    freeze_override: Decision | None = None,
) -> Snapshot:
    entities = (*fixture.entities.values(), *extra_entities)
    artifacts = (*fixture.artifacts.values(), *extra_artifacts)
    relations = extra_relations
    decisions_by_id = {
        item.decision_id: item for item in fixture.decisions.values()
    }
    if freeze_override is not None:
        decisions_by_id[fixture.freeze.decision_id] = freeze_override
    decisions = tuple(decisions_by_id.values())
    current_entities: dict[str, int] = {}
    for item in entities:
        current_entities[item.entity_id] = max(
            item.version, current_entities.get(item.entity_id, 0)
        )
    current_artifacts: dict[str, int] = {}
    for item in artifacts:
        current_artifacts[item.artifact_id] = max(
            item.version, current_artifacts.get(item.artifact_id, 0)
        )
    current_relations = {item.relation_id: item.version for item in relations}
    current_decisions = {item.decision_id: item.version for item in decisions}
    return Snapshot(
        project_id=PROJECT_ID,
        head=HEAD,
        chain=(HEAD,),
        entity_versions=tuple(entities),
        relation_versions=relations,
        artifacts=tuple(artifacts),
        decisions=decisions,
        current_entities=current_entities,
        current_relations=current_relations,
        current_artifacts=current_artifacts,
        current_decisions=current_decisions,
        effective_decisions={
            item.decision_id: EffectiveDecisionRef(
                decision_id=item.decision_id,
                version=item.version,
                effective_revision=HEAD,
            )
            for item in decisions
        },
    )


def _transaction(
    route_id: str,
    *,
    outputs: tuple[EntityVersion, ...],
    relations: tuple[RelationVersion, ...],
    artifacts: tuple[ArtifactRegistration, ...],
    evidence_refs: tuple[object, ...],
    authority_basis: tuple[str, ...],
    actor: Actor,
    outcome: str = "completed_with_candidate",
    validator_report_ref: ArtifactDependencyRef | None = None,
) -> Transaction:
    entity_operations: list[CreateEntityOp | SupersedeEntityOp] = []
    changed_facets: list[ChangedFacets] = []
    for output in outputs:
        if output.supersedes is None:
            entity_operations.append(CreateEntityOp(entity=output))
        else:
            entity_operations.append(
                SupersedeEntityOp(previous=output.supersedes, entity=output)
            )
            changed_facets.append(
                ChangedFacets(
                    entity_id=output.entity_id,
                    previous_version=output.supersedes.version,
                    new_version=output.version,
                    facets=("authority",),
                )
            )
    candidate_refs = (
        *(eref(item.entity_id, item.version) for item in outputs),
        *(
            RelationVersionRef(relation_id=item.relation_id, version=item.version)
            for item in relations
        ),
        *(aref(item) for item in artifacts),
    )
    return Transaction(
        transaction_id=f"transaction.{route_id}.contract",
        origin="route_run",
        project_id=PROJECT_ID,
        base_revision=HEAD,
        route_run_id=f"run.{route_id}.contract",
        route_id=route_id,
        route_run_hash=ROUTE_HASH,
        context_manifest_hash=CONTEXT_HASH,
        compiled_context_hash=COMPILED_HASH,
        actor=actor,
        intent="Exercise the exact sealed blind-evaluation contract.",
        changed_facets=tuple(changed_facets),
        operations=(
            *(RegisterArtifactOp(artifact=item) for item in artifacts),
            *entity_operations,
            *(CreateRelationOp(relation=item) for item in relations),
            RecordRouteOutcomeOp(
                outcome=RouteOutcome(
                    route_run_id=f"run.{route_id}.contract",
                    route_id=route_id,
                    outcome=outcome,  # type: ignore[arg-type]
                    rationale="The route emitted its exact sealed evidence candidate.",
                    candidate_refs=candidate_refs,
                    validator_report_refs=(
                        (validator_report_ref,)
                        if validator_report_ref is not None
                        else ()
                    ),
                )
            ),
        ),
        evidence_refs=evidence_refs,  # type: ignore[arg-type]
        authority_basis=authority_basis,
        created_at=CREATED_AT,
        parent_transaction_hash=HEAD,
    )


class BlindProtocolFixture:
    """Two complete theory branches plus one sealed blind attempt."""

    def __init__(self) -> None:
        closure = ClosureFixture()
        self.entities = dict(closure.entities)
        self.artifacts = dict(closure.artifacts)
        self.decisions = dict(closure.decisions)
        self.gold_ref = eref("vap.closure")
        self.entities[(self.gold_ref.entity_id, 1)] = self.entities[
            (self.gold_ref.entity_id, 1)
        ].model_copy(
            update={
                "privacy": "restricted",
                "access_compartments": SEALED,
            }
        )

        source_entities = tuple(self.entities.values())
        source_decisions = tuple(self.decisions.values())
        self.entity_ids = {
            item.entity_id: f"{item.entity_id}.blind_candidate"
            for item in source_entities
        }
        self.decision_ids = {
            item.decision_id: f"{item.decision_id}.blind_candidate"
            for item in source_decisions
        }
        self.base_question_ref = eref("question.closure")
        self.candidate_question_ref = eref(
            self.entity_ids[self.base_question_ref.entity_id]
        )
        self.base_brief_ref = eref("brief.blind.base")
        self.transformed_brief_ref = eref("brief.blind.transformed")

        for source in source_entities:
            payload = parse_theory_entity(source)
            data = _rewrite_refs(
                payload.model_dump(mode="python"),
                self.entity_ids,
                self.decision_ids,
            )
            cloned_payload = type(payload).model_validate(data)
            if isinstance(cloned_payload, ValidatedArgumentPackage):
                cloned_payload = ValidatedArgumentPackage.model_validate(
                    {
                        **cloned_payload.model_dump(mode="python"),
                        "release_mode": "evaluation_only",
                        "novelty_claim_mode": "none",
                        "evaluation_attempt_id": ATTEMPT,
                        "pre_result_brief_ref": self.transformed_brief_ref,
                        "generator_actor": GENERATOR,
                    }
                )
            supersedes = (
                eref(
                    self.entity_ids[source.supersedes.entity_id],
                    source.supersedes.version,
                )
                if source.supersedes is not None
                else None
            )
            cloned = source.model_copy(
                update={
                    "entity_id": self.entity_ids[source.entity_id],
                    "title": f"Blind candidate: {source.title}",
                    "summary": f"Transformed branch: {source.summary}",
                    "facets": pack_theory_payload(cloned_payload),
                    "supersedes": supersedes,
                    "privacy": "project_private",
                    "access_compartments": ("project_research",),
                }
            )
            self.entities[(cloned.entity_id, cloned.version)] = cloned

        for source in source_decisions:
            cloned = source.model_copy(
                update={
                    "decision_id": self.decision_ids[source.decision_id],
                    "subject_ref": self.entity_ids.get(
                        source.subject_ref, source.subject_ref
                    ),
                    "scope_ref": self.entity_ids.get(
                        source.scope_ref, source.scope_ref
                    ),
                    "evidence_refs": tuple(
                        self.entity_ids.get(item, item)
                        for item in source.evidence_refs
                    ),
                }
            )
            self.decisions[(cloned.decision_id, cloned.version)] = cloned

        self.candidate_ref = eref(self.entity_ids[self.gold_ref.entity_id])
        base_brief = PreResultBrief(
            question_ref=self.base_question_ref,
            benchmark_set_ref=eref("benchmarks.closure"),
            primitive_graph_ref=eref("primitives.closure"),
            institution="A sealed base institution for exact reconstruction.",
            allowed_context_refs=(
                self.base_question_ref,
                eref("benchmarks.closure"),
                eref("primitives.closure"),
            ),
            allowed_tools=("hand_derivation",),
            budget_units=8_000,
            excluded_information=("Gold result and answer key.",),
            attempt_id=ATTEMPT,
        )
        transformed_brief = PreResultBrief(
            question_ref=self.candidate_question_ref,
            benchmark_set_ref=eref(self.entity_ids["benchmarks.closure"]),
            primitive_graph_ref=eref(self.entity_ids["primitives.closure"]),
            institution="A transformed institution with sealed inverse mapping.",
            allowed_context_refs=(
                self.candidate_question_ref,
                eref(self.entity_ids["benchmarks.closure"]),
                eref(self.entity_ids["primitives.closure"]),
            ),
            allowed_tools=("hand_derivation",),
            budget_units=8_000,
            excluded_information=("Base labels, gold result, and inverse map.",),
            attempt_id=ATTEMPT,
        )
        self.entities[(self.base_brief_ref.entity_id, 1)] = _entity(
            self.base_brief_ref.entity_id, base_brief
        )
        self.entities[(self.transformed_brief_ref.entity_id, 1)] = _entity(
            self.transformed_brief_ref.entity_id,
            transformed_brief,
            access_compartments=GENERATOR_VISIBLE,
        )

        self.freeze_ref = DecisionVersionRef(
            decision_id="decision.blind.implementation_freeze", version=1
        )
        self.freeze = Decision(
            decision_id=self.freeze_ref.decision_id,
            version=1,
            project_id=PROJECT_ID,
            decision_kind="theory_mode",
            subject_ref=self.transformed_brief_ref.entity_id,
            scope_ref=ATTEMPT,
            question="Freeze the transformed implementation for this attempt?",
            options=("freeze", "reopen"),
            selected_option="freeze",
            recommendation="Freeze before generator access.",
            rationale="Labels and implementation are now immutable for this attempt.",
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-11T16:10:00Z",
            status="confirmed",
        )
        self.decisions[(self.freeze.decision_id, 1)] = self.freeze

        self.sealed_artifacts = (
            _artifact("artifact.blind.source_paper"),
            _artifact("artifact.blind.hidden_probe"),
            _artifact("artifact.blind.answer_key"),
            _artifact("artifact.blind.forward_map"),
            _artifact("artifact.blind.inverse_map"),
            _artifact("artifact.blind.invariant_signature"),
        )
        refs = {item.artifact_id: aref(item) for item in self.sealed_artifacts}
        self.manifest_ref = eref("manifest.blind.case")
        self.variant_ref = eref("manifest.blind.variant")
        self.manifest_payload = BlindCaseManifest(
            case_id="case.blind.contract",
            layer="transformed",
            pre_result_brief_ref=self.base_brief_ref,
            gold_package_ref=self.gold_ref,
            source_paper_refs=(refs["artifact.blind.source_paper"],),
            gold_semantic_refs=(self.gold_ref,),
            hidden_probe_refs=(refs["artifact.blind.hidden_probe"],),
            answer_key_ref=refs["artifact.blind.answer_key"],
            generator_compartments=("blind_generator",),
            evaluator_compartments=("blind_evaluator",),
            attempt_id=ATTEMPT,
        )
        self.variant_payload = TransformedVariantManifest(
            attempt_id=ATTEMPT,
            base_case_manifest_ref=self.manifest_ref,
            transformed_brief_ref=self.transformed_brief_ref,
            operations=(
                TransformOperation(
                    operation_id="transform.blind.semantic_rename",
                    kind="semantic_rename",
                    public_description="Rename every economic label bijectively.",
                    exact_forward_map_ref=refs["artifact.blind.forward_map"],
                ),
            ),
            hidden_inverse_map_ref=refs["artifact.blind.inverse_map"],
            invariant_signature_ref=refs["artifact.blind.invariant_signature"],
            implementation_freeze_ref=self.freeze_ref,
            generated_at="2026-07-11T16:11:00Z",
        )
        self.manifest = _entity(
            self.manifest_ref.entity_id,
            self.manifest_payload,
            artifact_refs=(
                refs["artifact.blind.source_paper"],
                refs["artifact.blind.hidden_probe"],
                refs["artifact.blind.answer_key"],
            ),
            privacy="restricted",
            access_compartments=SEALED,
        )
        self.variant = _entity(
            self.variant_ref.entity_id,
            self.variant_payload,
            artifact_refs=(
                refs["artifact.blind.forward_map"],
                refs["artifact.blind.inverse_map"],
                refs["artifact.blind.invariant_signature"],
            ),
            privacy="restricted",
            access_compartments=SEALED,
        )
        self.prepare_relations = (
            _relation(
                "relation.blind.seals",
                "seals",
                self.manifest_ref,
                self.gold_ref,
            ),
            _relation(
                "relation.blind.transforms",
                "transforms",
                self.variant_ref,
                self.transformed_brief_ref,
            ),
        )

    def prepare_inputs(self) -> tuple[EntityVersionRef, ...]:
        return (self.base_brief_ref, self.transformed_brief_ref, self.gold_ref)

    def prepare_transaction(
        self,
        *,
        manifest: EntityVersion | None = None,
        variant: EntityVersion | None = None,
        artifacts: tuple[ArtifactRegistration, ...] | None = None,
        outcome: str = "completed_with_candidate",
    ) -> Transaction:
        produced_artifacts = self.sealed_artifacts if artifacts is None else artifacts
        return _transaction(
            "prepare.blind_case",
            outputs=(manifest or self.manifest, variant or self.variant),
            relations=self.prepare_relations,
            artifacts=produced_artifacts,
            evidence_refs=self.prepare_inputs(),
            authority_basis=(self.freeze.decision_id,),
            actor=BUILDER,
            outcome=outcome,
            validator_report_ref=(
                aref(produced_artifacts[0]) if outcome == "validated" else None
            ),
        )

    def candidate_lock(self, *, tampered: bool = False) -> ArtifactRegistration:
        candidate = self.entities[(self.candidate_ref.entity_id, 1)]
        digest = (
            "f" * 64
            if tampered
            else sha256_digest(canonical_json_bytes(candidate))
        )
        return _artifact(
            f"candidate.lock.{ATTEMPT}",
            media_type="application/vnd.econ-theorist.candidate-lock+json",
            content_hash=digest,
        )

    def prepared_snapshot(
        self,
        *,
        lock: ArtifactRegistration | None,
        manifest: EntityVersion | None = None,
        extra_entities: tuple[EntityVersion, ...] = (),
        extra_artifacts: tuple[ArtifactRegistration, ...] = (),
    ) -> Snapshot:
        lock_items = (lock,) if lock is not None else ()
        return _snapshot(
            self,
            extra_entities=(
                manifest or self.manifest,
                self.variant,
                *extra_entities,
            ),
            extra_artifacts=(
                *self.sealed_artifacts,
                *lock_items,
                *extra_artifacts,
            ),
            extra_relations=self.prepare_relations,
        )

    def evaluation_candidate(
        self,
        *,
        lock: ArtifactRegistration,
        comparison_id: str = "comparison.blind.contract",
        attempt_id: str = ATTEMPT,
        evaluator: Actor = EVALUATOR,
        dimensions: tuple[str, ...] = SIGNATURE_DIMENSIONS,
        disposition: str = "confirmatory_clean",
        report_id: str = "artifact.blind.evaluator_report",
        version: int = 1,
        supersedes: EntityVersionRef | None = None,
    ) -> tuple[EntityVersion, ArtifactRegistration, RelationVersion]:
        report = _artifact(report_id)
        report_ref = aref(report)
        candidate = self.entities[(self.candidate_ref.entity_id, 1)]
        candidate_hash = sha256_digest(canonical_json_bytes(candidate))
        comparisons = tuple(
            SignatureDimensionComparison(
                dimension=item,  # type: ignore[arg-type]
                candidate_signature_ref=report_ref,
                gold_signature_ref=report_ref,
                comparison="match",
                diagnostic=f"Exact semantic comparison for {item}.",
            )
            for item in dimensions
        )
        payload = VAPComparisonRecord(
            attempt_id=attempt_id,
            case_manifest_ref=self.manifest_ref,
            candidate_package_ref=self.candidate_ref,
            gold_package_ref=self.gold_ref,
            candidate_package_hash=candidate_hash,
            candidate_lock_ref=aref(lock),
            evaluator=evaluator,
            dimension_comparisons=comparisons,
            evaluator_evidence_refs=(report_ref,),
            disposition=disposition,  # type: ignore[arg-type]
            compared_at="2026-07-11T16:20:00Z",
        )
        entity = _entity(
            comparison_id,
            payload,
            artifact_refs=(aref(lock), report_ref),
            privacy="restricted",
            access_compartments=SEALED,
            version=version,
            supersedes=supersedes,
        )
        relation = _relation(
            f"relation.{comparison_id}.candidate",
            "compares_to",
            eref(comparison_id, version),
            self.candidate_ref,
        )
        return entity, report, relation

    def evaluation_inputs(self) -> tuple[EntityVersionRef, ...]:
        return (
            self.manifest_ref,
            self.transformed_brief_ref,
            self.variant_ref,
            self.candidate_ref,
            self.gold_ref,
        )

    def evaluation_transaction(
        self,
        *,
        comparison: EntityVersion,
        report: ArtifactRegistration,
        relation: RelationVersion,
        lock: ArtifactRegistration,
        actor: Actor = EVALUATOR,
        outcome: str = "completed_with_candidate",
    ) -> Transaction:
        sealed_evidence = tuple(aref(item) for item in self.sealed_artifacts)
        return _transaction(
            "evaluate.blind_argument_package",
            outputs=(comparison,),
            relations=(relation,),
            artifacts=(report,),
            evidence_refs=(
                *self.evaluation_inputs(),
                *sealed_evidence,
                aref(lock),
            ),
            authority_basis=(self.freeze.decision_id,),
            actor=actor,
            outcome=outcome,
            validator_report_ref=(aref(report) if outcome == "validated" else None),
        )


class BlindPreparationContractTests(unittest.TestCase):
    def test_prepare_accepts_one_controlled_attempt_with_two_question_roots(self) -> None:
        fixture = BlindProtocolFixture()
        self.assertNotEqual(
            fixture.base_question_ref, fixture.candidate_question_ref
        )
        snapshot = _snapshot(fixture)
        entry = validate_phase2_route_entry(
            snapshot,
            get_route("prepare.blind_case"),
            tuple(item.entity_id for item in fixture.prepare_inputs()),
            actor=BUILDER,
        )
        self.assertIsNone(entry.research_question_ref)
        self.assertEqual(entry.gate_decision_refs, (fixture.freeze_ref,))

        report = validate_phase2_route_transaction(
            snapshot,
            fixture.prepare_transaction(),
            get_route("prepare.blind_case"),
        )
        self.assertGreater(report.parsed_entity_count, 0)

    def test_freeze_kind_status_subject_and_attempt_are_exact(self) -> None:
        mutations = (
            ("kind", {"decision_kind": "ambition"}),
            ("status", {"status": "provisional"}),
            ("subject", {"subject_ref": "brief.blind.ghost"}),
            ("attempt", {"scope_ref": "attempt.blind.other"}),
        )
        for label, update in mutations:
            with self.subTest(invalid_freeze=label):
                fixture = BlindProtocolFixture()
                bad_freeze = fixture.freeze.model_copy(update=update)
                with self.assertRaisesRegex(
                    TheoryValidationError, r"(?i)implementation freeze"
                ):
                    validate_phase2_route_transaction(
                        _snapshot(fixture, freeze_override=bad_freeze),
                        fixture.prepare_transaction(),
                        get_route("prepare.blind_case"),
                    )

    def test_generator_cannot_read_the_gold_package(self) -> None:
        fixture = BlindProtocolFixture()
        gold = fixture.entities[(fixture.gold_ref.entity_id, 1)]
        fixture.entities[(fixture.gold_ref.entity_id, 1)] = gold.model_copy(
            update={
                "privacy": "project_private",
                "access_compartments": GENERATOR_VISIBLE,
            }
        )

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)generator.*disclose.*gold"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                fixture.prepare_transaction(),
                get_route("prepare.blind_case"),
            )

    def test_manifest_cannot_omit_payload_or_envelope_artifact_refs(self) -> None:
        for label in ("payload", "envelope"):
            with self.subTest(missing=label):
                fixture = BlindProtocolFixture()
                if label == "payload":
                    payload = fixture.manifest_payload.model_copy(
                        update={"source_paper_refs": ()}
                    )
                    manifest = fixture.manifest.model_copy(
                        update={"facets": pack_theory_payload(payload)}
                    )
                    pattern = r"(?i)(sealed source|hidden probe)"
                else:
                    manifest = fixture.manifest.model_copy(
                        update={
                            "artifact_refs": fixture.manifest.artifact_refs[1:]
                        }
                    )
                    pattern = r"(?i)envelopes.*every exact artifact"
                with self.assertRaisesRegex(TheoryValidationError, pattern):
                    validate_phase2_route_transaction(
                        _snapshot(fixture),
                        fixture.prepare_transaction(manifest=manifest),
                        get_route("prepare.blind_case"),
                    )


class BlindEvaluationContractTests(unittest.TestCase):
    def _valid_candidate(
        self,
        fixture: BlindProtocolFixture,
        lock: ArtifactRegistration,
        **kwargs: object,
    ) -> tuple[EntityVersion, ArtifactRegistration, RelationVersion]:
        return fixture.evaluation_candidate(lock=lock, **kwargs)  # type: ignore[arg-type]

    def test_evaluate_accepts_the_controlled_two_root_attempt(self) -> None:
        fixture = BlindProtocolFixture()
        lock = fixture.candidate_lock()
        snapshot = fixture.prepared_snapshot(lock=lock)
        entry = validate_phase2_route_entry(
            snapshot,
            get_route("evaluate.blind_argument_package"),
            tuple(item.entity_id for item in fixture.evaluation_inputs()),
            actor=EVALUATOR,
        )
        self.assertIsNone(entry.research_question_ref)
        self.assertEqual(entry.gate_decision_refs, (fixture.freeze_ref,))
        comparison, report, relation = self._valid_candidate(fixture, lock)

        readiness = validate_phase2_route_transaction(
            snapshot,
            fixture.evaluation_transaction(
                comparison=comparison,
                report=report,
                relation=relation,
                lock=lock,
            ),
            get_route("evaluate.blind_argument_package"),
        )
        self.assertGreater(readiness.parsed_entity_count, 0)

    def test_generator_cannot_begin_the_evaluator_route(self) -> None:
        fixture = BlindProtocolFixture()
        lock = fixture.candidate_lock()
        snapshot = fixture.prepared_snapshot(lock=lock)

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)generator.*cannot begin.*evaluator"
        ):
            validate_phase2_route_entry(
                snapshot,
                get_route("evaluate.blind_argument_package"),
                tuple(item.entity_id for item in fixture.evaluation_inputs()),
                actor=GENERATOR,
            )

    def test_evaluation_requires_a_prior_untampered_candidate_lock(self) -> None:
        for label, lock_in_snapshot, tampered in (
            ("nonprior", False, False),
            ("tampered", True, True),
        ):
            with self.subTest(lock=label):
                fixture = BlindProtocolFixture()
                lock = fixture.candidate_lock(tampered=tampered)
                comparison, report, relation = self._valid_candidate(fixture, lock)
                with self.assertRaisesRegex(
                    TheoryValidationError, r"(?i)prior exact candidate-lock"
                ):
                    validate_phase2_route_transaction(
                        fixture.prepared_snapshot(
                            lock=(lock if lock_in_snapshot else None)
                        ),
                        fixture.evaluation_transaction(
                            comparison=comparison,
                            report=report,
                            relation=relation,
                            lock=lock,
                        ),
                        get_route("evaluate.blind_argument_package"),
                    )

    def test_comparison_attempt_must_match_every_sealed_input(self) -> None:
        fixture = BlindProtocolFixture()
        lock = fixture.candidate_lock()
        comparison, report, relation = self._valid_candidate(
            fixture, lock, attempt_id="attempt.blind.other"
        )

        with self.assertRaisesRegex(
            TheoryValidationError,
            r"(?i)(sealed attempt|attempt.*bind|exact transformed variant)",
        ):
            validate_phase2_route_transaction(
                fixture.prepared_snapshot(lock=lock),
                fixture.evaluation_transaction(
                    comparison=comparison,
                    report=report,
                    relation=relation,
                    lock=lock,
                ),
                get_route("evaluate.blind_argument_package"),
            )

    def test_one_attempt_cannot_receive_a_second_terminal_comparison(self) -> None:
        fixture = BlindProtocolFixture()
        lock = fixture.candidate_lock()
        prior, prior_report, _ = self._valid_candidate(
            fixture,
            lock,
            comparison_id="comparison.blind.prior",
            report_id="artifact.blind.prior_report",
        )
        second, report, relation = self._valid_candidate(
            fixture,
            lock,
            comparison_id="comparison.blind.second",
            report_id="artifact.blind.second_report",
        )

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)already has terminal evaluator feedback"
        ):
            validate_phase2_route_transaction(
                fixture.prepared_snapshot(
                    lock=lock,
                    extra_entities=(prior,),
                    extra_artifacts=(prior_report,),
                ),
                fixture.evaluation_transaction(
                    comparison=second,
                    report=report,
                    relation=relation,
                    lock=lock,
                ),
                get_route("evaluate.blind_argument_package"),
            )

    def test_comparison_must_cover_all_seventeen_dimensions(self) -> None:
        fixture = BlindProtocolFixture()
        lock = fixture.candidate_lock()
        comparison, report, relation = self._valid_candidate(
            fixture, lock, dimensions=SIGNATURE_DIMENSIONS[:-1]
        )

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)all 17 semantic signature dimensions"
        ):
            validate_phase2_route_transaction(
                fixture.prepared_snapshot(lock=lock),
                fixture.evaluation_transaction(
                    comparison=comparison,
                    report=report,
                    relation=relation,
                    lock=lock,
                ),
                get_route("evaluate.blind_argument_package"),
            )

    def test_evaluator_must_be_independent_of_generator(self) -> None:
        fixture = BlindProtocolFixture()
        lock = fixture.candidate_lock()
        comparison, report, relation = self._valid_candidate(
            fixture, lock, evaluator=GENERATOR
        )

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)(independent evaluator|evaluator independence)"
        ):
            validate_phase2_route_transaction(
                fixture.prepared_snapshot(lock=lock),
                fixture.evaluation_transaction(
                    comparison=comparison,
                    report=report,
                    relation=relation,
                    lock=lock,
                    actor=GENERATOR,
                ),
                get_route("evaluate.blind_argument_package"),
            )

    def test_public_classic_cannot_masquerade_as_confirmatory_clean(self) -> None:
        fixture = BlindProtocolFixture()
        public_payload = fixture.manifest_payload.model_copy(
            update={
                "layer": "public_classic",
                "pre_result_brief_ref": fixture.transformed_brief_ref,
            }
        )
        public_manifest = fixture.manifest.model_copy(
            update={"facets": pack_theory_payload(public_payload)}
        )
        lock = fixture.candidate_lock()
        comparison, report, relation = self._valid_candidate(
            fixture, lock, disposition="confirmatory_clean"
        )

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)public classic.*cannot be confirmatory_clean"
        ):
            validate_phase2_route_transaction(
                fixture.prepared_snapshot(lock=lock, manifest=public_manifest),
                fixture.evaluation_transaction(
                    comparison=comparison,
                    report=report,
                    relation=relation,
                    lock=lock,
                ),
                get_route("evaluate.blind_argument_package"),
            )

    def test_evaluator_cannot_supersede_a_comparison_record(self) -> None:
        fixture = BlindProtocolFixture()
        lock = fixture.candidate_lock()
        prior, prior_report, _ = self._valid_candidate(
            fixture,
            lock,
            comparison_id="comparison.blind.immutable",
            attempt_id="attempt.blind.prior.other",
            report_id="artifact.blind.immutable.prior",
        )
        current, report, relation = self._valid_candidate(
            fixture,
            lock,
            comparison_id=prior.entity_id,
            version=2,
            supersedes=eref(prior.entity_id),
            report_id="artifact.blind.immutable.current",
        )

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)entity.supersede.*outside.*contract"
        ):
            validate_phase2_route_transaction(
                fixture.prepared_snapshot(
                    lock=lock,
                    extra_entities=(prior,),
                    extra_artifacts=(prior_report,),
                ),
                fixture.evaluation_transaction(
                    comparison=current,
                    report=report,
                    relation=relation,
                    lock=lock,
                ),
                get_route("evaluate.blind_argument_package"),
            )

    def test_evaluation_route_cannot_self_declare_validated(self) -> None:
        fixture = BlindProtocolFixture()
        lock = fixture.candidate_lock()
        comparison, report, relation = self._valid_candidate(fixture, lock)

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)cannot self-declare validation"
        ):
            validate_phase2_route_transaction(
                fixture.prepared_snapshot(lock=lock),
                fixture.evaluation_transaction(
                    comparison=comparison,
                    report=report,
                    relation=relation,
                    lock=lock,
                    outcome="validated",
                ),
                get_route("evaluate.blind_argument_package"),
            )


if __name__ == "__main__":
    unittest.main()
