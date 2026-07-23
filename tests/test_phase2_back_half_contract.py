"""P0 adversarial acceptance tests for the Phase 2 back-half contract.

These tests exercise the scientific chain from claim discovery through the
G5 candidate handoff.  Each mutation is same-project and, where relevant,
same-ResearchQuestion: a validator must reject the scientific mismatch rather
than relying on a missing reference or a different project scope.
"""

from __future__ import annotations

import unittest
from types import SimpleNamespace

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase2_scientific_closure import (
    CREATED_AT,
    HUMAN,
    PROJECT_ID,
    ClosureFixture,
)

from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ChangedFacets,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    EffectiveDecisionRef,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    RouteSpecV2,
    ScientificStatus,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from econ_theorist.machine.navigation import (
    _claim_verification_focus_sets,
    _focus_sets_for_policy,
    _registry_focus_sets,
)
from econ_theorist.framing_quality_validation import (
    FramingQualityValidationError,
    validate_framing_repair_route_entry,
    validate_framing_repair_route_transaction,
)
from econ_theorist.route_registry import get_route
from econ_theorist.theory import (
    AbsorptionAssessment,
    AssumptionMap,
    BenchmarkSet,
    ClaimGraph,
    ClosestTheoryMap,
    FormalizationMap,
    GateDossier,
    GateRequirement,
    LiteratureEvidence,
    ProofObligation,
    ResultPortfolio,
    ResearchQuestion,
    TheoryPayload,
    ValidatedArgumentPackage,
    VerificationBundle,
    VerificationRecord,
    pack_theory_payload,
)
from econ_theorist.theory_validation import (
    TheoryValidationError,
    validate_phase2_route_entry,
    validate_phase2_route_transaction,
    validate_theory_projection,
)


HEAD = "a" * 64
ROUTE_HASH = "b" * 64
CONTEXT_HASH = "c" * 64
COMPILED_HASH = "d" * 64
AGENT = Actor(kind="agent", actor_id="agent.phase2.back_half.attack")


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def _new_entity(entity_id: str, payload: TheoryPayload) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=1,
        project_id=PROJECT_ID,
        title=entity_id,
        summary=f"Back-half adversarial fixture for {type(payload).__name__}.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=pack_theory_payload(payload),
        created_at=CREATED_AT,
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


def _snapshot(fixture: ClosureFixture) -> Snapshot:
    current_entities: dict[str, int] = {}
    for entity in fixture.entities.values():
        current_entities[entity.entity_id] = max(
            entity.version, current_entities.get(entity.entity_id, 0)
        )
    current_artifacts = {
        item.artifact_id: item.version for item in fixture.artifacts.values()
    }
    current_decisions = {
        item.decision_id: item.version for item in fixture.decisions.values()
    }
    return Snapshot(
        project_id=PROJECT_ID,
        head=HEAD,
        chain=(HEAD,),
        entity_versions=tuple(fixture.entities.values()),
        artifacts=tuple(fixture.artifacts.values()),
        decisions=tuple(fixture.decisions.values()),
        current_entities=current_entities,
        current_artifacts=current_artifacts,
        current_decisions=current_decisions,
        effective_decisions={
            item.decision_id: EffectiveDecisionRef(
                decision_id=item.decision_id,
                version=item.version,
                effective_revision=HEAD,
            )
            for item in fixture.decisions.values()
        },
    )


def _route_transaction(
    route_id: str,
    *,
    outputs: tuple[EntityVersion, ...],
    evidence_refs: tuple[EntityVersionRef, ...],
    authority_basis: tuple[str, ...] = (),
    relations: tuple[RelationVersion, ...] = (),
    outcome: str = "completed_with_candidate",
    validator_report_ref: ArtifactDependencyRef | None = None,
) -> Transaction:
    operations: list[object] = []
    changed_facets: list[ChangedFacets] = []
    for output in outputs:
        if output.supersedes is None:
            operations.append(CreateEntityOp(entity=output))
        else:
            operations.append(
                SupersedeEntityOp(previous=output.supersedes, entity=output)
            )
            changed_facets.append(
                ChangedFacets(
                    entity_id=output.entity_id,
                    previous_version=output.supersedes.version,
                    new_version=output.version,
                    facets=("theory_payload",),
                )
            )
    operations.extend(CreateRelationOp(relation=item) for item in relations)
    candidate_refs = (
        *(eref(item.entity_id, item.version) for item in outputs),
        *(
            RelationVersionRef(relation_id=item.relation_id, version=item.version)
            for item in relations
        ),
    )
    operations.append(
        RecordRouteOutcomeOp(
            outcome=RouteOutcome(
                route_run_id=f"run.{route_id}.negative",
                route_id=route_id,
                outcome=outcome,  # type: ignore[arg-type]
                rationale="Exercise one exact back-half contract violation.",
                candidate_refs=candidate_refs,
                validator_report_refs=(
                    (validator_report_ref,)
                    if validator_report_ref is not None
                    else ()
                ),
            )
        )
    )
    return Transaction(
        transaction_id=f"transaction.{route_id}.negative",
        origin="route_run",
        project_id=PROJECT_ID,
        base_revision=HEAD,
        route_run_id=f"run.{route_id}.negative",
        route_id=route_id,
        route_run_hash=ROUTE_HASH,
        context_manifest_hash=CONTEXT_HASH,
        compiled_context_hash=COMPILED_HASH,
        actor=AGENT,
        intent="Attempt one precise Phase 2 back-half contract violation.",
        changed_facets=tuple(changed_facets),
        operations=tuple(operations),  # type: ignore[arg-type]
        evidence_refs=evidence_refs,
        authority_basis=authority_basis,
        created_at=CREATED_AT,
        parent_transaction_hash=HEAD,
    )


def _authority_through(rank: int) -> tuple[str, ...]:
    return tuple(f"decision.g{item}.closure" for item in range(1, rank + 1))


def _discover_inputs() -> tuple[EntityVersionRef, ...]:
    return (
        eref("assumptions.closure"),
        eref("argument.closure"),
        eref("model.selected.closure"),
        eref("formalization.closure"),
        eref("mechanism.selected.closure"),
        eref("question.closure"),
    )


def _verify_claim_inputs() -> tuple[EntityVersionRef, ...]:
    return (
        eref("assumptions.closure"),
        eref("claims.closure"),
        eref("model.selected.closure"),
        eref("obligation.boundary.closure"),
        eref("obligation.threshold.closure"),
        eref("question.closure"),
    )


def _audit_inputs() -> tuple[EntityVersionRef, ...]:
    return (
        eref("assumptions.closure"),
        eref("claims.closure"),
        eref("model.selected.closure"),
        eref("question.closure"),
        eref("verification.bundle.closure"),
    )


def _curate_inputs() -> tuple[EntityVersionRef, ...]:
    return (
        eref("absorption.closure"),
        eref("claims.closure"),
        eref("question.closure"),
        eref("verification.bundle.closure"),
    )


def _validate_inputs(
    formalization_ref: EntityVersionRef | None = None,
) -> tuple[EntityVersionRef, ...]:
    return (
        eref("absorption.closure"),
        eref("assumptions.closure"),
        eref("benchmarks.closure"),
        eref("claims.closure"),
        eref("closest.closure"),
        eref("argument.closure"),
        eref("examples.closure"),
        eref("model.selected.closure"),
        eref("model.contrast.closure"),
        formalization_ref or eref("formalization.closure"),
        eref("tournament.implementations.closure"),
        eref("literature.closure"),
        eref("mechanism.selected.closure"),
        eref("mechanism.rival.closure"),
        eref("tournament.mechanisms.closure"),
        eref("predictions.closure", 2),
        eref("primitives.closure"),
        eref("obligation.threshold.closure"),
        eref("obligation.boundary.closure"),
        eref("question.closure"),
        eref("portfolio.closure"),
        eref("verification.bundle.closure"),
        eref("verification.threshold.closure"),
        eref("verification.boundary.closure"),
    )


def _with_weakening_attempt(fixture: ClosureFixture) -> None:
    assumptions = fixture.payload("assumptions.closure")
    assert isinstance(assumptions, AssumptionMap)
    record = assumptions.assumptions[0].model_copy(
        update={"weakening_attempts": ("Relax indivisibility and recompute.",)}
    )
    fixture.replace_payload(
        "assumptions.closure",
        assumptions.model_copy(update={"assumptions": (record,)}),
    )


def _audit_outputs(
    fixture: ClosureFixture,
    *,
    suffix: str,
    closest_update: dict[str, object] | None = None,
    absorption_update: dict[str, object] | None = None,
) -> tuple[EntityVersion, EntityVersion, EntityVersion]:
    literature = fixture.payload("literature.closure")
    closest = fixture.payload("closest.closure")
    absorption = fixture.payload("absorption.closure")
    assert isinstance(literature, LiteratureEvidence)
    assert isinstance(closest, ClosestTheoryMap)
    assert isinstance(absorption, AbsorptionAssessment)
    literature_id = f"literature.audit.{suffix}"
    closest_id = f"closest.audit.{suffix}"
    absorption_id = f"absorption.audit.{suffix}"
    closest_changes: dict[str, object] = {
        "literature_evidence_ref": eref(literature_id)
    }
    closest_changes.update(closest_update or {})
    absorption_changes: dict[str, object] = {
        "closest_theory_map_ref": eref(closest_id)
    }
    absorption_changes.update(absorption_update or {})
    return (
        _new_entity(literature_id, literature),
        _new_entity(closest_id, closest.model_copy(update=closest_changes)),
        _new_entity(
            absorption_id, absorption.model_copy(update=absorption_changes)
        ),
    )


def _g5_candidate(
    fixture: ClosureFixture,
    *,
    suffix: str,
    inputs: tuple[EntityVersionRef, ...],
    package_update: dict[str, object] | None = None,
) -> tuple[EntityVersion, EntityVersion, tuple[RelationVersion, ...]]:
    package = fixture.payload("vap.closure")
    dossier = fixture.payload("dossier.g5.closure")
    assert isinstance(package, ValidatedArgumentPackage)
    assert isinstance(dossier, GateDossier)
    package_id = f"vap.validate.{suffix}"
    dossier_id = f"dossier.g5.validate.{suffix}"
    package_changes: dict[str, object] = {"g5_dossier_ref": eref(dossier_id)}
    package_changes.update(package_update or {})
    package_entity = _new_entity(
        package_id, package.model_copy(update=package_changes)
    )
    ordered = (
        eref("question.closure"),
        *(item for item in inputs if item != eref("question.closure")),
        eref(package_id),
    )
    dossier_entity = _new_entity(
        dossier_id,
        dossier.model_copy(
            update={
                "ordered_object_refs": ordered,
                "requirements": (
                    GateRequirement(
                        requirement_id=f"requirement.g5.validate.{suffix}",
                        description="Every exact G5 candidate input is supplied.",
                        evidence_refs=ordered,
                        recorded_condition="evidence_supplied",
                    ),
                ),
                "prepared_at": "2026-07-11T16:09:30Z",
            }
        ),
    )
    relations = (
        _relation(
            f"relation.governs.g5.{suffix}",
            "governs",
            eref(dossier_id),
            eref(package_id),
        ),
        _relation(
            f"relation.includes.g5.{suffix}",
            "includes",
            eref(package_id),
            eref("portfolio.closure"),
        ),
        _relation(
            f"relation.validates.g5.{suffix}",
            "validates",
            eref("verification.bundle.closure"),
            eref(package_id),
        ),
    )
    return package_entity, dossier_entity, relations


class ClaimDiscoveryRouteEntryTests(unittest.TestCase):
    def test_exact_g2_and_g3_approved_chain_can_enter(self) -> None:
        fixture = ClosureFixture()

        entry = validate_phase2_route_entry(
            _snapshot(fixture),
            get_route("discover.claims_and_boundaries"),
            tuple(reference.entity_id for reference in _discover_inputs()),
            actor=AGENT,
        )

        self.assertEqual(entry.research_question_ref, eref("question.closure"))
        self.assertEqual(len(entry.gate_decision_refs), 3)

    def test_mixed_formal_model_or_mechanism_cannot_enter(self) -> None:
        fixture = ClosureFixture()
        substitutions = (
            (
                "model",
                tuple(
                    "model.contrast.closure"
                    if reference.entity_id == "model.selected.closure"
                    else reference.entity_id
                    for reference in _discover_inputs()
                ),
            ),
            (
                "mechanism",
                tuple(
                    "mechanism.rival.closure"
                    if reference.entity_id == "mechanism.selected.closure"
                    else reference.entity_id
                    for reference in _discover_inputs()
                ),
            ),
        )

        for label, focus in substitutions:
            with self.subTest(substitution=label), self.assertRaisesRegex(
                TheoryValidationError, r"(?i)(approved|formal-base chain)"
            ):
                validate_phase2_route_entry(
                    _snapshot(fixture),
                    get_route("discover.claims_and_boundaries"),
                    focus,
                    actor=AGENT,
                )

    def test_coherent_but_unapproved_same_question_base_cannot_enter(self) -> None:
        fixture = ClosureFixture()
        mapping = fixture.payload("formalization.closure")
        assumptions = fixture.payload("assumptions.closure")
        assert isinstance(mapping, FormalizationMap)
        assert isinstance(assumptions, AssumptionMap)
        alternate_mapping_id = "formalization.unapproved.closure"
        alternate_assumptions_id = "assumptions.unapproved.closure"
        fixture.add(
            _new_entity(
                alternate_mapping_id,
                mapping.model_copy(
                    update={"formal_model_ref": eref("model.contrast.closure")}
                ),
            )
        )
        fixture.add(
            _new_entity(
                alternate_assumptions_id,
                assumptions.model_copy(
                    update={
                        "formal_model_ref": eref("model.contrast.closure"),
                        "formalization_map_ref": eref(alternate_mapping_id),
                    }
                ),
            )
        )
        focus = (
            alternate_assumptions_id,
            "argument.closure",
            "model.contrast.closure",
            alternate_mapping_id,
            "mechanism.selected.closure",
            "question.closure",
        )

        with self.assertRaisesRegex(TheoryValidationError, r"(?i)G3-approved"):
            validate_phase2_route_entry(
                _snapshot(fixture),
                get_route("discover.claims_and_boundaries"),
                focus,
                actor=AGENT,
            )


class ClaimVerificationRouteEntryTests(unittest.TestCase):
    def test_every_retained_obligation_can_enter_as_one_closure(self) -> None:
        fixture = ClosureFixture()

        entry = validate_phase2_route_entry(
            _snapshot(fixture),
            get_route("verify.claims_proofs_and_interpretation"),
            tuple(
                reference.entity_id for reference in _verify_claim_inputs()
            ),
            actor=AGENT,
        )

        self.assertEqual(entry.research_question_ref, eref("question.closure"))
        self.assertEqual(len(entry.gate_decision_refs), 3)

    def test_partial_obligation_subset_cannot_enter(self) -> None:
        fixture = ClosureFixture()
        partial_focus = tuple(
            reference.entity_id
            for reference in _verify_claim_inputs()
            if reference.entity_id != "obligation.boundary.closure"
        )

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)every and only.*ProofObligation"
        ):
            validate_phase2_route_entry(
                _snapshot(fixture),
                get_route("verify.claims_proofs_and_interpretation"),
                partial_focus,
                actor=AGENT,
            )

    def test_falsified_obligation_enters_existing_single_root_repair(self) -> None:
        fixture = ClosureFixture()
        record = fixture.payload("verification.threshold.closure")
        assert isinstance(record, VerificationRecord)
        fixture.replace_payload(
            "verification.threshold.closure",
            record.model_copy(update={"outcome": "falsified"}),
        )
        graph = fixture.payload("claims.closure")
        assert isinstance(graph, ClaimGraph)
        fixture.replace_payload(
            "claims.closure",
            graph.model_copy(
                update={
                    "claims": tuple(
                        claim.model_copy(update={"verification_record_refs": ()})
                        for claim in graph.claims
                    )
                }
            ),
        )
        for entity_id in (
            "absorption.closure",
            "closest.closure",
            "dossier.g4.closure",
            "dossier.g5.closure",
            "literature.closure",
            "portfolio.closure",
            "vap.closure",
        ):
            fixture.entities.pop((entity_id, 1), None)
        fixture.decisions.pop(("decision.g4.closure", 1), None)
        challenge = _relation(
            "relation.challenge.threshold.closure",
            "challenges",
            eref("verification.threshold.closure"),
            eref("obligation.threshold.closure"),
        )
        snapshot = _snapshot(fixture).model_copy(
            update={
                "relation_versions": (challenge,),
                "current_relations": {challenge.relation_id: challenge.version},
            }
        )

        entry = validate_framing_repair_route_entry(
            snapshot,
            get_route("repair.dependency"),
            ("obligation.threshold.closure",),
            actor=AGENT,
        )

        self.assertEqual(entry.repair_mode, "stale_root")
        self.assertEqual(entry.target_ref, eref("obligation.threshold.closure"))
        replay_entry = validate_framing_repair_route_entry(
            snapshot,
            get_route("repair.dependency"),
            (
                "verification.bundle.closure",
                "obligation.threshold.closure",
            ),
            actor=AGENT,
        )
        self.assertEqual(replay_entry.repair_mode, "verification_revision")
        current = {
            entity.entity_id: entity
            for entity in snapshot.entity_versions
            if snapshot.current_entities.get(entity.entity_id) == entity.version
        }
        enumerated = _focus_sets_for_policy(
            "framing_or_stale_repair_root.v1",
            get_route("repair.dependency"),
            snapshot,
            current,
            limit=4096,
        )
        self.assertIn(("obligation.threshold.closure",), enumerated.focus_sets)
        self.assertNotIn(
            tuple(
                sorted(
                    (
                        "verification.bundle.closure",
                        "obligation.threshold.closure",
                    )
                )
            ),
            enumerated.focus_sets,
        )

        def repair_transaction(target_id: str) -> Transaction:
            previous = fixture.entities[(target_id, 1)]
            payload = fixture.payload(target_id)
            assert isinstance(payload, ProofObligation)
            revised = previous.model_copy(
                update={
                    "version": 2,
                    "supersedes": eref(target_id),
                    "facets": pack_theory_payload(
                        payload.model_copy(
                            update={
                                "statement": (
                                    payload.statement
                                    + " Apply the corrected exact quantifier."
                                )
                            }
                        )
                    ),
                }
            )
            return Transaction(
                transaction_id=f"transaction.repair.{target_id}",
                origin="route_run",
                project_id=PROJECT_ID,
                base_revision=HEAD,
                route_run_id=f"run.repair.{target_id}",
                route_id="repair.dependency",
                route_run_hash=ROUTE_HASH,
                context_manifest_hash=CONTEXT_HASH,
                compiled_context_hash=COMPILED_HASH,
                actor=AGENT,
                intent="Replace exactly one falsified proof obligation.",
                changed_facets=(
                    ChangedFacets(
                        entity_id=target_id,
                        previous_version=1,
                        new_version=2,
                        facets=("formal",),
                    ),
                ),
                operations=(
                    SupersedeEntityOp(
                        previous=eref(target_id),
                        entity=revised,
                    ),
                    RecordRouteOutcomeOp(
                        outcome=RouteOutcome(
                            route_run_id=f"run.repair.{target_id}",
                            route_id="repair.dependency",
                            outcome="completed_with_candidate",
                            rationale="Replace the exact falsified obligation.",
                            candidate_refs=(eref(target_id, 2),),
                        )
                    ),
                ),
                evidence_refs=(eref("obligation.threshold.closure"),),
                created_at=CREATED_AT,
                parent_transaction_hash=HEAD,
            )

        validate_framing_repair_route_transaction(
            snapshot,
            repair_transaction("obligation.threshold.closure"),
            get_route("repair.dependency"),
        )
        with self.assertRaisesRegex(
            FramingQualityValidationError, "one exact target"
        ):
            validate_framing_repair_route_transaction(
                snapshot,
                repair_transaction("obligation.boundary.closure"),
                get_route("repair.dependency"),
            )

        without_challenge = snapshot.model_copy(
            update={"relation_versions": (), "current_relations": {}}
        )
        with self.assertRaisesRegex(
            FramingQualityValidationError, "exactly one typed stale root"
        ):
            validate_framing_repair_route_entry(
                without_challenge,
                get_route("repair.dependency"),
                ("obligation.threshold.closure",),
                actor=AGENT,
            )

    def test_navigation_uses_twenty_obligations_as_one_closure(self) -> None:
        fixture = ClosureFixture()
        graph = fixture.payload("claims.closure")
        template = fixture.payload("obligation.threshold.closure")
        assert isinstance(graph, ClaimGraph)
        assert isinstance(template, ProofObligation)
        extra_refs: list[EntityVersionRef] = []
        for index in range(18):
            entity_id = f"obligation.extra.{index:02d}.closure"
            extra_refs.append(eref(entity_id))
            fixture.add(
                _new_entity(
                    entity_id,
                    template.model_copy(
                        update={
                            "obligation_id": f"obligation.extra.{index:02d}"
                        }
                    ),
                )
            )
        first_claim, *remaining_claims = graph.claims
        fixture.replace_payload(
            "claims.closure",
            graph.model_copy(
                update={
                    "claims": (
                        first_claim.model_copy(
                            update={
                                "proof_obligation_refs": (
                                    *first_claim.proof_obligation_refs,
                                    *extra_refs,
                                )
                            }
                        ),
                        *remaining_claims,
                    )
                }
            ),
        )
        unretained_id = "obligation.unretained.closure"
        fixture.add(
            _new_entity(
                unretained_id,
                template.model_copy(
                    update={"obligation_id": "obligation.unretained"}
                ),
            )
        )
        current = {
            entity.entity_id: entity
            for entity in fixture.entities.values()
        }

        enumeration = _claim_verification_focus_sets(
            get_route("verify.claims_proofs_and_interpretation"),
            current,
            limit=64,
        )

        self.assertFalse(enumeration.truncated)
        self.assertEqual(len(enumeration.focus_sets), 1)
        for focus in enumeration.focus_sets:
            self.assertEqual(len(focus), 24)
            self.assertNotIn(unretained_id, focus)
            self.assertEqual(
                len(
                    {
                        entity_id
                        for entity_id in focus
                        if current[entity_id].entity_type
                        == "ProofObligation"
                    }
                ),
                20,
            )

    def test_other_registry_cardinality_routes_keep_subset_semantics(
        self,
    ) -> None:
        fixture = ClosureFixture()
        selected = fixture.entities[("model.selected.closure", 1)]
        current = {
            "model.one": selected.model_copy(
                update={"entity_id": "model.one"}
            ),
            "model.two": selected.model_copy(
                update={"entity_id": "model.two"}
            ),
            "model.three": selected.model_copy(
                update={"entity_id": "model.three"}
            ),
        }
        bounded_route = SimpleNamespace(
            required_input_entities=(
                SimpleNamespace(
                    entity_type="FormalModel",
                    min_count=1,
                    max_count=2,
                ),
            )
        )
        unbounded_route = SimpleNamespace(
            required_input_entities=(
                SimpleNamespace(
                    entity_type="FormalModel",
                    min_count=1,
                    max_count=None,
                ),
            )
        )

        bounded = _registry_focus_sets(
            bounded_route, current, limit=64
        )
        unbounded = _registry_focus_sets(
            unbounded_route, current, limit=64
        )

        self.assertFalse(bounded.truncated)
        self.assertEqual(len(bounded.focus_sets), 6)
        self.assertFalse(unbounded.truncated)
        self.assertEqual(len(unbounded.focus_sets), 7)

    def test_missing_later_requirement_prevents_irrelevant_subset_expansion(
        self,
    ) -> None:
        fixture = ClosureFixture()
        current = {
            entity.entity_id: entity
            for entity in fixture.entities.values()
            if entity.entity_type == "ProofObligation"
        }
        template = next(iter(current.values()))
        for index in range(18):
            entity_id = f"obligation.preflight.{index:02d}"
            current[entity_id] = template.model_copy(
                update={"entity_id": entity_id}
            )
        route = SimpleNamespace(
            required_input_entities=(
                SimpleNamespace(
                    entity_type="ProofObligation",
                    min_count=1,
                    max_count=None,
                ),
                SimpleNamespace(
                    entity_type="ValidatedArgumentPackage",
                    min_count=1,
                    max_count=1,
                ),
            )
        )

        enumeration = _registry_focus_sets(route, current, limit=64)

        self.assertFalse(enumeration.truncated)
        self.assertFalse(enumeration.focus_sets)


class ProjectionBackHalfClosureTests(unittest.TestCase):
    def test_bundle_cannot_omit_one_retained_claim_obligation(self) -> None:
        fixture = ClosureFixture()
        bundle = fixture.payload("verification.bundle.closure")
        assert isinstance(bundle, VerificationBundle)
        fixture.replace_payload(
            "verification.bundle.closure",
            bundle.model_copy(
                update={"proof_obligation_refs": bundle.proof_obligation_refs[:1]}
            ),
        )

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)(every claim obligation|obligation)"
        ):
            fixture.validate()

    def test_verification_record_cannot_splice_foreign_model_or_assumption_map(
        self,
    ) -> None:
        def foreign_model(fixture: ClosureFixture) -> None:
            record = fixture.payload("verification.threshold.closure")
            assert isinstance(record, VerificationRecord)
            fixture.replace_payload(
                "verification.threshold.closure",
                record.model_copy(
                    update={
                        "formal_model_ref": eref("model.contrast.closure"),
                        "checked_refs": (
                            record.obligation_ref,
                            record.claim_graph_ref,
                            eref("model.contrast.closure"),
                            record.assumption_map_ref,
                        ),
                    }
                ),
            )

        def foreign_assumption_map(fixture: ClosureFixture) -> None:
            assumptions = fixture.payload("assumptions.closure")
            assert isinstance(assumptions, AssumptionMap)
            fixture.add(_new_entity("assumptions.foreign.branch", assumptions))
            record = fixture.payload("verification.threshold.closure")
            assert isinstance(record, VerificationRecord)
            fixture.replace_payload(
                "verification.threshold.closure",
                record.model_copy(
                    update={
                        "assumption_map_ref": eref("assumptions.foreign.branch"),
                        "checked_refs": (
                            record.obligation_ref,
                            record.claim_graph_ref,
                            record.formal_model_ref,
                            eref("assumptions.foreign.branch"),
                        ),
                    }
                ),
            )

        for label, mutation in (
            ("formal model", foreign_model),
            ("assumption map", foreign_assumption_map),
        ):
            with self.subTest(foreign=label):
                fixture = ClosureFixture()
                mutation(fixture)
                with self.assertRaisesRegex(
                    TheoryValidationError,
                    r"(?i)(exact claim, obligation, model, and assumptions|verification)",
                ):
                    fixture.validate()

    def test_stale_selected_model_blocks_the_production_vap(self) -> None:
        fixture = ClosureFixture()
        selected = fixture.entities[("model.selected.closure", 1)]
        fixture.add(
            selected.model_copy(
                update={
                    "version": 2,
                    "supersedes": eref("model.selected.closure"),
                }
            )
        )

        report = validate_theory_projection(
            tuple(fixture.entities.values()),
            tuple(fixture.artifacts.values()),
            tuple(fixture.decisions.values()),
        )

        self.assertIn(
            eref("vap.closure"), report.production_blocked_package_refs
        )


class BackHalfRouteExitTests(unittest.TestCase):
    def test_discover_cannot_fork_a_new_assumption_map_id(self) -> None:
        fixture = ClosureFixture()
        assumptions = fixture.payload("assumptions.closure")
        graph = fixture.payload("claims.closure")
        threshold = fixture.payload("obligation.threshold.closure")
        boundary = fixture.payload("obligation.boundary.closure")
        assert isinstance(assumptions, AssumptionMap)
        assert isinstance(graph, ClaimGraph)
        assert isinstance(threshold, ProofObligation)
        assert isinstance(boundary, ProofObligation)

        assumptions_id = "assumptions.discover.fork"
        graph_id = "claims.discover.fork"
        threshold_id = "obligation.threshold.discover.fork"
        boundary_id = "obligation.boundary.discover.fork"
        claim = graph.claims[0].model_copy(
            update={
                "proof_obligation_refs": (
                    eref(threshold_id),
                    eref(boundary_id),
                ),
                "verification_record_refs": (),
            }
        )
        outputs = (
            _new_entity(assumptions_id, assumptions),
            _new_entity(
                graph_id,
                graph.model_copy(
                    update={
                        "assumption_map_ref": eref(assumptions_id),
                        "claims": (claim,),
                    }
                ),
            ),
            _new_entity(
                threshold_id,
                threshold.model_copy(update={"claim_graph_ref": eref(graph_id)}),
            ),
            _new_entity(
                boundary_id,
                boundary.model_copy(update={"claim_graph_ref": eref(graph_id)}),
            ),
        )
        relations = (
            _relation(
                "relation.bounds.discover.fork",
                "bounds",
                eref(assumptions_id),
                eref(graph_id),
            ),
            _relation(
                "relation.entails.discover.fork",
                "entails",
                eref("formalization.closure"),
                eref(graph_id),
            ),
            _relation(
                "relation.requires.threshold.discover.fork",
                "requires",
                eref(graph_id),
                eref(threshold_id),
            ),
            _relation(
                "relation.requires.boundary.discover.fork",
                "requires",
                eref(graph_id),
                eref(boundary_id),
            ),
        )
        route_id = "discover.claims_and_boundaries"

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)(supersede.*exact G3 map|AssumptionMap)"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=outputs,
                    relations=relations,
                    evidence_refs=_discover_inputs(),
                    authority_basis=_authority_through(3),
                ),
                get_route(route_id),
            )

    def test_audit_route_cannot_output_an_assumption_map(self) -> None:
        fixture = ClosureFixture()
        assumptions = fixture.payload("assumptions.closure")
        assert isinstance(assumptions, AssumptionMap)
        route_id = "audit.assumptions_generality_and_absorption"

        with self.assertRaisesRegex(TheoryValidationError, r"(?i)(allowlist|AssumptionMap)"):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=(
                        _new_entity("assumptions.audit.illegal", assumptions),
                    ),
                    evidence_refs=_audit_inputs(),
                    authority_basis=_authority_through(3),
                ),
                get_route(route_id),
            )

    def test_nonabsorbed_assessment_cannot_emit_absorbs_relation(self) -> None:
        fixture = ClosureFixture()
        _with_weakening_attempt(fixture)
        outputs = _audit_outputs(fixture, suffix="nonabsorbed")
        literature, closest, absorption = outputs
        relations = (
            _relation(
                "relation.compares.audit.nonabsorbed",
                "compares_to",
                eref(closest.entity_id),
                eref(literature.entity_id),
            ),
            _relation(
                "relation.maps.audit.nonabsorbed",
                "maps_to",
                eref(closest.entity_id),
                eref("claims.closure"),
            ),
            _relation(
                "relation.absorbs.audit.nonabsorbed",
                "absorbs",
                eref(absorption.entity_id),
                eref(closest.entity_id),
            ),
        )
        route_id = "audit.assumptions_generality_and_absorption"

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)(nonabsorbed.*cannot emit|absorbs relation)"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=outputs,
                    relations=relations,
                    evidence_refs=_audit_inputs(),
                    authority_basis=_authority_through(3),
                ),
                get_route(route_id),
            )

    def test_closest_theory_classification_cannot_contradict_absorption_outcome(
        self,
    ) -> None:
        fixture = ClosureFixture()
        _with_weakening_attempt(fixture)
        closest = fixture.payload("closest.closure")
        assert isinstance(closest, ClosestTheoryMap)
        exact_dimensions = tuple(
            item.model_copy(update={"mapping_status": "exact"})
            for item in closest.dimensions
        )
        outputs = _audit_outputs(
            fixture,
            suffix="classification",
            closest_update={
                "classification": "duplicate",
                "dimensions": exact_dimensions,
                "first_mapping_failure": None,
            },
            absorption_update={
                "outcome": "partially_absorbed",
                "first_mapping_failure": None,
                "recommended_route": "proceed",
            },
        )
        literature, closest_entity, absorption = outputs
        relations = (
            _relation(
                "relation.compares.audit.classification",
                "compares_to",
                eref(closest_entity.entity_id),
                eref(literature.entity_id),
            ),
            _relation(
                "relation.maps.audit.classification",
                "maps_to",
                eref(closest_entity.entity_id),
                eref("claims.closure"),
            ),
            _relation(
                "relation.absorbs.audit.classification",
                "absorbs",
                eref(absorption.entity_id),
                eref(closest_entity.entity_id),
            ),
        )
        route_id = "audit.assumptions_generality_and_absorption"

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)classification contradicts"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=outputs,
                    relations=relations,
                    evidence_refs=_audit_inputs(),
                    authority_basis=_authority_through(3),
                ),
                get_route(route_id),
            )

    def test_g4_dossier_cannot_omit_core_result_objects(self) -> None:
        fixture = ClosureFixture()
        portfolio = fixture.payload("portfolio.closure")
        dossier = fixture.payload("dossier.g4.closure")
        assert isinstance(portfolio, ResultPortfolio)
        assert isinstance(dossier, GateDossier)
        portfolio_id = "portfolio.curate.incomplete"
        dossier_id = "dossier.g4.curate.incomplete"
        incomplete_dossier = dossier.model_copy(
            update={
                "ordered_object_refs": (eref("question.closure"),),
                "requirements": (
                    GateRequirement(
                        requirement_id="requirement.g4.curate.incomplete",
                        description="Only the question was supplied.",
                        evidence_refs=(eref("question.closure"),),
                        recorded_condition="evidence_supplied",
                    ),
                ),
                "prepared_at": "2026-07-11T16:07:30Z",
            }
        )
        outputs = (
            _new_entity(portfolio_id, portfolio),
            _new_entity(dossier_id, incomplete_dossier),
        )
        relations = (
            _relation(
                "relation.includes.curate.incomplete",
                "includes",
                eref(portfolio_id),
                eref("claims.closure"),
            ),
            _relation(
                "relation.governs.curate.incomplete",
                "governs",
                eref(dossier_id),
                eref(portfolio_id),
            ),
        )
        route_id = "curate.result_portfolio"

        with self.assertRaisesRegex(TheoryValidationError, r"(?i)G4 dossier omits"):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=outputs,
                    relations=relations,
                    evidence_refs=_curate_inputs(),
                    authority_basis=_authority_through(3),
                ),
                get_route(route_id),
            )

    def test_same_scope_formalization_branch_splice_is_rejected(self) -> None:
        fixture = ClosureFixture()
        formalization = fixture.payload("formalization.closure")
        assert isinstance(formalization, FormalizationMap)
        fork_ref = eref("formalization.same_scope.fork")
        fixture.add(_new_entity(fork_ref.entity_id, formalization))
        inputs = _validate_inputs(fork_ref)
        package, dossier, relations = _g5_candidate(
            fixture,
            suffix="branch.splice",
            inputs=inputs,
            package_update={"formalization_map_ref": fork_ref},
        )
        route_id = "validate.argument_package"

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)splices incompatible branches"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=(package, dossier),
                    relations=relations,
                    evidence_refs=inputs,
                    authority_basis=_authority_through(4),
                ),
                get_route(route_id),
            )

    def test_g5_package_and_dossier_must_be_mutually_bound(self) -> None:
        fixture = ClosureFixture()
        alternate = fixture.payload("dossier.g5.closure")
        assert isinstance(alternate, GateDossier)
        alternate_id = "dossier.g5.alternate"
        fixture.add(_new_entity(alternate_id, alternate))
        inputs = _validate_inputs()
        package, dossier, relations = _g5_candidate(
            fixture,
            suffix="mutual.mismatch",
            inputs=inputs,
            package_update={"g5_dossier_ref": eref(alternate_id)},
        )
        route_id = "validate.argument_package"

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)exact same-transaction G5 dossier"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=(package, dossier),
                    relations=relations,
                    evidence_refs=inputs,
                    authority_basis=_authority_through(4),
                ),
                get_route(route_id),
            )

    def test_validate_route_cannot_self_declare_validated(self) -> None:
        fixture = ClosureFixture()
        inputs = _validate_inputs()
        package, dossier, relations = _g5_candidate(
            fixture,
            suffix="self.validated",
            inputs=inputs,
        )
        route_id = "validate.argument_package"

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)(only propose a G5 candidate|cannot mark.*validated)"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=(package, dossier),
                    relations=relations,
                    evidence_refs=inputs,
                    authority_basis=_authority_through(4),
                    outcome="validated",
                    validator_report_ref=fixture.artifact_ref(
                        "artifact.proof.threshold"
                    ),
                ),
                get_route(route_id),
            )


class RouteAuthorityAndReleaseTests(unittest.TestCase):
    def _custom_spec(
        self,
        route_id: str,
        output_type: str,
        *,
        required_gate_kinds: tuple[str, ...] = (),
    ) -> RouteSpecV2:
        return RouteSpecV2(
            route_id=route_id,
            availability="enabled",
            allowed_purposes=("research_discovery",),
            allowed_operations=("entity.create", "route.outcome"),
            allowed_entity_types=(output_type,),
            allowed_relation_types=("supports",),
            required_gate_kinds=required_gate_kinds,  # type: ignore[arg-type]
            entry_validator_id="theory_route_entry.v1",
            exit_validator_id="theory_route_exit.v1",
            instruction_bundle_id=f"{route_id}.v2",
            instruction_bundle_hash=ROUTE_HASH,
        )

    def test_extra_foreign_gate_cannot_pad_authority_basis(self) -> None:
        fixture = ClosureFixture()
        question = fixture.payload("question.closure")
        assert isinstance(question, ResearchQuestion)
        foreign_question_id = "question.foreign.authority"
        foreign_dossier_id = "dossier.g1.foreign.authority"
        fixture.add(_new_entity(foreign_question_id, question))
        fixture.add(
            _new_entity(
                foreign_dossier_id,
                GateDossier(
                    gate_kind="G1_question_benchmark",
                    research_question_ref=eref(foreign_question_id),
                    ordered_object_refs=(eref(foreign_question_id),),
                    requirements=(
                        GateRequirement(
                            requirement_id="requirement.g1.foreign.authority",
                            description="Foreign-scope question evidence.",
                            evidence_refs=(eref(foreign_question_id),),
                            recorded_condition="evidence_supplied",
                        ),
                    ),
                    proposed_action="approve",
                    rationale="A distinct question has its own G1 dossier.",
                    prepared_at="2026-07-11T16:00:30Z",
                ),
            )
        )
        foreign_decision = Decision(
            decision_id="decision.g1.foreign.authority",
            version=1,
            project_id=PROJECT_ID,
            decision_kind="G1_question_benchmark",
            subject_ref=foreign_dossier_id,
            scope_ref=foreign_question_id,
            question="Approve the foreign question?",
            options=("approve", "deny"),
            selected_option="approve",
            machine_outcome="approve",
            recommendation="Approve the separate scope.",
            rationale="The foreign dossier is complete.",
            evidence_refs=(foreign_dossier_id,),
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-11T16:01:30Z",
            status="confirmed",
        )
        fixture.decisions[(foreign_decision.decision_id, 1)] = foreign_decision
        benchmark = fixture.payload("benchmarks.closure")
        assert isinstance(benchmark, BenchmarkSet)
        route_id = "test.authority.foreign_gate"
        output = _new_entity("benchmarks.authority.attack", benchmark)

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)(unrelated or foreign).*Decision"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=(output,),
                    evidence_refs=(eref("question.closure"),),
                    authority_basis=(
                        *_authority_through(3),
                        foreign_decision.decision_id,
                    ),
                ),
                self._custom_spec(
                    route_id,
                    "BenchmarkSet",
                    required_gate_kinds=("G3_formal_base",),
                ),
            )

    def test_route_cannot_commit_a_blocked_production_vap(self) -> None:
        fixture = ClosureFixture()
        selected = fixture.entities[("model.selected.closure", 1)]
        fixture.add(
            selected.model_copy(
                update={
                    "version": 2,
                    "supersedes": eref("model.selected.closure"),
                }
            )
        )
        package = fixture.payload("vap.closure")
        assert isinstance(package, ValidatedArgumentPackage)
        output = _new_entity("vap.blocked.production", package)
        route_id = "test.release.blocked_vap"

        with self.assertRaisesRegex(
            TheoryValidationError, r"(?i)blocked production VAP"
        ):
            validate_phase2_route_transaction(
                _snapshot(fixture),
                _route_transaction(
                    route_id,
                    outputs=(output,),
                    evidence_refs=(eref("question.closure"),),
                ),
                self._custom_spec(route_id, "ValidatedArgumentPackage"),
            )


if __name__ == "__main__":
    unittest.main()
