"""Contract tests for replay, authority, dependencies, and freshness."""

from __future__ import annotations

import tempfile
import unittest
from unittest.mock import patch

from tests.helpers import SOURCE_ROOT  # noqa: F401 - establishes src import path

from econ_theorist.codec import object_digest, transaction_bytes, transaction_digest
from econ_theorist.context import ContextAccessError, compile_context
from econ_theorist.errors import AuthorityError, RegistryError
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactPrivacySubject,
    ArtifactRegistration,
    ArtifactVersionRef,
    BlockerRef,
    ChangedFacets,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EntityPrivacySubject,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    FacetPayloads,
    RecordBlockerOp,
    RecordDecisionOp,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    PrivacyChange,
    Precondition,
    RelationVersion,
    RelationVersionRef,
    ScopeOverlapEvidence,
    RetireEntityOp,
    RiskOrBlocker,
    RouteOutcome,
    ScientificStatus,
    SemanticFacetRef,
    StatusTransition,
    StatusTransitionOp,
    SupersedeDecisionOp,
    SupersedeEntityOp,
    SupersedeRelationOp,
    Transaction,
)
from econ_theorist.runtime.freshness import (
    FacetPathError,
    authority_semantic_hash,
    facet_semantic_hash,
    stale_reason_chains,
)
from econ_theorist.runtime.layout import StoreLayout
from econ_theorist.runtime.objects import HeadStore, ObjectStore
from econ_theorist.runtime.replay import (
    CandidateValidationError,
    ChangedFacetError,
    DependencyCycleError,
    PrivacyFlowError,
    ReferentialIntegrityError,
    UnsupportedOperationError,
    replay,
    replay_at,
    validate_candidate,
    validate_route_context_output_flow,
)
from econ_theorist.route_registry import get_route


PROJECT_ID = "prj_replay"
AGENT = Actor(kind="agent", actor_id="agent_replay")
HUMAN = Actor(kind="human", actor_id="human_researcher")
OTHER_HUMAN = Actor(kind="human", actor_id="human_other")


def entity(
    entity_id: str,
    *,
    version: int = 1,
    formal: object | None = None,
    interpretation: object | None = None,
    presentation: object | None = None,
    privacy: str = "project_private",
    scope_ref: str | None = None,
) -> EntityVersion:
    supersedes = (
        EntityVersionRef(entity_id=entity_id, version=version - 1)
        if version > 1
        else None
    )
    return EntityVersion(
        entity_id=entity_id,
        entity_type="TheoryObject",
        version=version,
        project_id=PROJECT_ID,
        title=entity_id,
        summary=f"Fixture entity {entity_id}.",
        scope_ref=scope_ref,
        status=ScientificStatus(lifecycle="proposed"),
        facets=FacetPayloads(
            formal={} if formal is None else {"value": formal},
            economic_interpretation=(
                {} if interpretation is None else {"value": interpretation}
            ),
            terminology_presentation=(
                {} if presentation is None else {"value": presentation}
            ),
        ),
        privacy=privacy,
        created_at=f"2026-07-11T00:00:{version:02d}Z",
        supersedes=supersedes,
    )


def relation(
    relation_id: str,
    source: EntityVersion,
    target: EntityVersion,
    *,
    source_facet: str = "formal",
    target_facet: str = "formal",
    mode: str = "hard",
    semantic_hash: str | None = None,
    scope_ref: str | None = None,
    scope_overlap: ScopeOverlapEvidence | None = None,
) -> RelationVersion:
    if mode == "trace_only":
        upstream = None
        downstream = None
    else:
        upstream = SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet=source_facet,
            semantic_hash=(
                semantic_hash
                if semantic_hash is not None
                else facet_semantic_hash(source, source_facet)
            ),
        )
        downstream = FacetPathRef(
            entity_id=target.entity_id,
            version=target.version,
            facet=target_facet,
        )
    return RelationVersion(
        relation_id=relation_id,
        relation_type="depends_on",
        version=1,
        project_id=PROJECT_ID,
        source=EntityVersionRef(
            entity_id=source.entity_id, version=source.version
        ),
        target=EntityVersionRef(
            entity_id=target.entity_id, version=target.version
        ),
        dependency_mode=mode,
        upstream=upstream,
        downstream=downstream,
        scope_ref=scope_ref,
        scope_overlap=scope_overlap,
        created_at="2026-07-11T00:01:00Z",
    )


def transaction(
    transaction_id: str,
    operations: tuple[object, ...],
    *,
    base: str | None = None,
    actor: Actor = AGENT,
    changed_facets: tuple[ChangedFacets, ...] = (),
    authority_basis: tuple[str, ...] = (),
    preconditions: tuple[Precondition, ...] = (),
    privacy: str | None = None,
    access_compartments: tuple[str, ...] | None = None,
) -> Transaction:
    if base is None:
        origin = "genesis"
        provenance: dict[str, str] = {}
        route_id = None
    elif actor.kind == "human":
        origin = "human_decision"
        provenance = {}
        route_id = None
    else:
        origin = "route_run"
        operation_names = {operation.op for operation in operations}
        route_id = (
            "repair.dependency"
            if operation_names.intersection(
                {"entity.supersede", "relation.supersede", "artifact.register"}
            )
            else "frame.question_and_benchmarks"
        )
        provenance = {
            "route_run_hash": "a" * 64,
            "context_manifest_hash": "b" * 64,
            "compiled_context_hash": "c" * 64,
        }
    output_records = tuple(
        record
        for operation in operations
        for record in (
            getattr(operation, "entity", None),
            getattr(operation, "relation", None),
            getattr(operation, "decision", None),
            getattr(operation, "artifact", None),
            getattr(operation, "outcome", None),
            getattr(operation, "blocker", None),
        )
        if record is not None and hasattr(record, "privacy")
    )
    privacy_rank = {
        "public": 0,
        "project_private": 1,
        "restricted": 2,
        "local_only": 3,
    }
    transaction_privacy = privacy or max(
        (record.privacy for record in output_records),
        key=privacy_rank.__getitem__,
        default="project_private",
    )
    transaction_compartments = access_compartments or tuple(
        sorted(
            {
                compartment
                for record in output_records
                for compartment in record.access_compartments
            }
            or {"project_research"}
        )
    )
    return Transaction(
        **provenance,
        transaction_id=transaction_id,
        origin=origin,
        project_id=PROJECT_ID,
        base_revision=base,
        route_run_id=f"run_{transaction_id}",
        route_id=route_id,
        actor=actor,
        intent=f"Apply {transaction_id}.",
        preconditions=preconditions,
        changed_facets=changed_facets,
        operations=operations,
        authority_basis=authority_basis,
        privacy=transaction_privacy,
        access_compartments=transaction_compartments,
        created_at="2026-07-11T00:02:00Z",
        parent_transaction_hash=base,
    )


def project_entity() -> EntityVersion:
    return EntityVersion(
        entity_id=PROJECT_ID,
        entity_type="Project",
        version=1,
        project_id=PROJECT_ID,
        title="Replay fixture",
        summary="The canonical project root.",
        status=ScientificStatus(lifecycle="active"),
        facets=FacetPayloads(),
        created_at="2026-07-11T00:00:00Z",
    )


def genesis(*entities: EntityVersion):
    root_txn = transaction(
        "txn_genesis",
        (CreateEntityOp(entity=project_entity()),),
        actor=HUMAN,
    )
    snapshot = validate_candidate(None, root_txn)
    transactions = [root_txn]
    if entities:
        fixture_txn = transaction(
            "txn_fixture_entities",
            tuple(CreateEntityOp(entity=item) for item in entities),
            base=snapshot.head,
        )
        snapshot = validate_candidate(snapshot, fixture_txn)
        transactions.append(fixture_txn)
    return tuple(transactions), snapshot


def confirmed_decision(
    decision_id: str,
    subject_ref: str,
    *,
    kind: str = "G1_question_benchmark",
    decider: Actor = HUMAN,
    required_authority: str = "L2",
) -> Decision:
    return Decision(
        decision_id=decision_id,
        version=1,
        project_id=PROJECT_ID,
        decision_kind=kind,
        subject_ref=subject_ref,
        question="Confirm this structural choice?",
        options=("confirm", "reject"),
        selected_option="confirm",
        recommendation="confirm",
        rationale="The human accepts this exact scoped choice.",
        required_authority=required_authority,
        decider=decider,
        decided_at="2026-07-11T00:03:00Z",
        status="confirmed",
    )


class FacetAndFreshnessTests(unittest.TestCase):
    def test_changed_facets_must_equal_the_exact_semantic_diff(self) -> None:
        first = entity("ent_a", formal="old", presentation="old wording")
        _, snapshot = genesis(first)
        second = entity(
            "ent_a", version=2, formal="new", presentation="new wording"
        )
        txn = transaction(
            "txn_incomplete_diff",
            (
                SupersedeEntityOp(
                    previous=EntityVersionRef(entity_id="ent_a", version=1),
                    entity=second,
                ),
            ),
            base=snapshot.head,
            changed_facets=(
                ChangedFacets(
                    entity_id="ent_a",
                    previous_version=1,
                    new_version=2,
                    facets=("formal",),
                ),
            ),
        )

        with self.assertRaises(ChangedFacetError):
            validate_candidate(snapshot, txn)

    def test_semantically_equal_bound_facet_does_not_stale_dependents(self) -> None:
        assumption = entity("ent_a", formal="fixed", presentation="old name")
        claim = entity("ent_c", formal="claim")
        _, root = genesis()
        genesis_txn = transaction(
            "txn_equal_genesis",
            (
                CreateEntityOp(entity=assumption),
                CreateEntityOp(entity=claim),
                CreateRelationOp(
                    relation=relation("rel_ac", assumption, claim)
                ),
            ),
            base=root.head,
        )
        snapshot = validate_candidate(root, genesis_txn)
        renamed = entity(
            "ent_a", version=2, formal="fixed", presentation="new name"
        )
        rename_txn = transaction(
            "txn_rename",
            (
                SupersedeEntityOp(
                    previous=EntityVersionRef(entity_id="ent_a", version=1),
                    entity=renamed,
                ),
            ),
            base=snapshot.head,
            changed_facets=(
                ChangedFacets(
                    entity_id="ent_a",
                    previous_version=1,
                    new_version=2,
                    facets=("terminology_presentation",),
                ),
            ),
        )

        updated = validate_candidate(snapshot, rename_txn)

        self.assertEqual(updated.derived_status["ent_c"].freshness["formal"], "fresh")
        self.assertEqual(
            facet_semantic_hash(assumption, "formal"),
            facet_semantic_hash(renamed, "formal"),
        )

    def test_formal_change_stales_only_minimal_descendants_with_why_chain(self) -> None:
        assumption = entity("ent_a", formal="A0")
        claim = entity("ent_c", formal="C")
        verification = entity("ent_v", formal="V")
        manuscript = entity("ent_m", presentation="M")
        independent = entity("ent_u", formal="U")
        _, root = genesis()
        initial = transaction(
            "txn_graph_genesis",
            (
                *(CreateEntityOp(entity=item) for item in (
                    assumption,
                    claim,
                    verification,
                    manuscript,
                    independent,
                )),
                CreateRelationOp(relation=relation("rel_ac", assumption, claim)),
                CreateRelationOp(relation=relation("rel_cv", claim, verification)),
                CreateRelationOp(
                    relation=relation(
                        "rel_cm",
                        claim,
                        manuscript,
                        target_facet="terminology_presentation",
                        mode="presentation",
                    )
                ),
            ),
            base=root.head,
        )
        snapshot = validate_candidate(root, initial)
        revised = entity("ent_a", version=2, formal="A1")
        revise = transaction(
            "txn_formal_change",
            (
                SupersedeEntityOp(
                    previous=EntityVersionRef(entity_id="ent_a", version=1),
                    entity=revised,
                ),
            ),
            base=snapshot.head,
            changed_facets=(
                ChangedFacets(
                    entity_id="ent_a",
                    previous_version=1,
                    new_version=2,
                    facets=("formal",),
                ),
            ),
        )

        updated = validate_candidate(snapshot, revise)

        self.assertEqual(updated.derived_status["ent_c"].freshness["formal"], "stale")
        self.assertEqual(updated.derived_status["ent_v"].freshness["formal"], "stale")
        self.assertEqual(
            updated.derived_status["ent_m"].freshness["terminology_presentation"],
            "stale",
        )
        self.assertTrue(
            all(
                value == "fresh"
                for value in updated.derived_status["ent_u"].freshness.values()
            )
        )
        self.assertEqual(
            updated.derived_status["ent_c"].freshness["economic_interpretation"],
            "fresh",
        )
        chains = stale_reason_chains(updated, "ent_v", "formal")
        self.assertEqual(
            tuple(reason.relation_id for reason in chains[0]),
            ("rel_ac", "rel_cv"),
        )


class DependencyValidationTests(unittest.TestCase):
    def test_invalidating_cycle_rejects_whole_candidate(self) -> None:
        left = entity("ent_left", formal="L")
        right = entity("ent_right", formal="R")
        _, snapshot = genesis(left, right)
        cycle = transaction(
            "txn_cycle",
            (
                CreateRelationOp(relation=relation("rel_lr", left, right)),
                CreateRelationOp(relation=relation("rel_rl", right, left)),
            ),
            base=snapshot.head,
        )

        with self.assertRaises(DependencyCycleError):
            validate_candidate(snapshot, cycle)
        self.assertEqual(snapshot.current_relations, {})

    def test_trace_only_feedback_is_allowed(self) -> None:
        left = entity("ent_left", formal="L")
        right = entity("ent_right", formal="R")
        _, snapshot = genesis(left, right)
        feedback = transaction(
            "txn_trace_feedback",
            (
                CreateRelationOp(
                    relation=relation("rel_lr_trace", left, right, mode="trace_only")
                ),
                CreateRelationOp(
                    relation=relation("rel_rl_trace", right, left, mode="trace_only")
                ),
            ),
            base=snapshot.head,
        )

        updated = validate_candidate(snapshot, feedback)

        self.assertEqual(set(updated.current_relations), {"rel_lr_trace", "rel_rl_trace"})

    def test_trace_only_link_does_not_claim_source_to_target_information_flow(self) -> None:
        sealed = entity("ent_sealed_trace", formal="hidden", privacy="restricted")
        visible = entity("ent_visible_trace", formal="already visible", privacy="public")
        _, snapshot = genesis(sealed, visible)
        protected_pointer = relation(
            "rel_sealed_trace_pointer", sealed, visible, mode="trace_only"
        ).model_copy(
            update={
                "privacy": "restricted",
                "access_compartments": ("confirmatory_holdout", "project_research"),
            }
        )

        updated = validate_candidate(
            snapshot,
            transaction(
                "txn_sealed_trace_pointer",
                (CreateRelationOp(relation=protected_pointer),),
                base=snapshot.head,
                privacy="restricted",
                access_compartments=("confirmatory_holdout", "project_research"),
            ),
        )

        self.assertEqual(
            updated.current_relations[protected_pointer.relation_id], 1
        )

    def test_trace_only_link_envelope_cannot_drop_source_protection(self) -> None:
        sealed = entity("ent_sealed_trace", formal="hidden", privacy="restricted")
        visible = entity("ent_visible_trace", formal="already visible", privacy="public")
        _, snapshot = genesis(sealed, visible)
        underprotected_pointer = relation(
            "rel_underprotected_trace", sealed, visible, mode="trace_only"
        ).model_copy(update={"privacy": "public"})

        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_underprotected_trace",
                    (CreateRelationOp(relation=underprotected_pointer),),
                    base=snapshot.head,
                ),
            )

    def test_overlapping_json_pointer_regions_cannot_hide_a_cycle(self) -> None:
        left = entity("ent_pointer_left", formal={"x": {"z": 1}})
        right = entity("ent_pointer_right", formal={"y": {"z": 1}})
        _, snapshot = genesis(left, right)

        def exact_relation(
            relation_id: str,
            source: EntityVersion,
            target: EntityVersion,
            source_path: str,
            target_path: str,
        ) -> RelationVersion:
            return RelationVersion(
                relation_id=relation_id,
                relation_type="depends_on",
                version=1,
                project_id=PROJECT_ID,
                source=EntityVersionRef(
                    entity_id=source.entity_id, version=source.version
                ),
                target=EntityVersionRef(
                    entity_id=target.entity_id, version=target.version
                ),
                dependency_mode="hard",
                upstream=SemanticFacetRef(
                    entity_id=source.entity_id,
                    version=source.version,
                    facet="formal",
                    field_path=source_path,
                    semantic_hash=facet_semantic_hash(
                        source, "formal", source_path
                    ),
                ),
                downstream=FacetPathRef(
                    entity_id=target.entity_id,
                    version=target.version,
                    facet="formal",
                    field_path=target_path,
                ),
                created_at="2026-07-11T00:01:30Z",
            )

        cycle = transaction(
            "txn_pointer_overlap_cycle",
            (
                CreateRelationOp(
                    relation=exact_relation(
                        "rel_pointer_left_right",
                        left,
                        right,
                        "/value/x",
                        "/value/y",
                    )
                ),
                CreateRelationOp(
                    relation=exact_relation(
                        "rel_pointer_right_left",
                        right,
                        left,
                        "/value/y/z",
                        "/value/x/z",
                    )
                ),
            ),
            base=snapshot.head,
        )
        with self.assertRaises(DependencyCycleError):
            validate_candidate(snapshot, cycle)

    def test_unchanged_current_version_bridge_cannot_hide_a_cycle(self) -> None:
        left = entity("ent_bridge_left", formal="left")
        right_v1 = entity(
            "ent_bridge_right", formal="right", presentation="old"
        )
        _, snapshot = genesis(left, right_v1)
        first = relation("rel_bridge_left_right", left, right_v1)
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_bridge_first_edge",
                (CreateRelationOp(relation=first),),
                base=snapshot.head,
            ),
        )
        right_v2 = entity(
            right_v1.entity_id,
            version=2,
            formal="right",
            presentation="new",
        )
        reverse = relation("rel_bridge_right_left", right_v2, left)
        candidate = transaction(
            "txn_bridge_hidden_cycle",
            (
                SupersedeEntityOp(
                    previous=EntityVersionRef(
                        entity_id=right_v1.entity_id, version=1
                    ),
                    entity=right_v2,
                ),
                CreateRelationOp(relation=reverse),
            ),
            base=snapshot.head,
            changed_facets=(
                ChangedFacets(
                    entity_id=right_v1.entity_id,
                    previous_version=1,
                    new_version=2,
                    facets=("terminology_presentation",),
                ),
            ),
        )
        with self.assertRaises(DependencyCycleError):
            validate_candidate(snapshot, candidate)

    def test_relation_requires_exact_endpoint_and_semantic_hash(self) -> None:
        left = entity("ent_left", formal="L")
        right = entity("ent_right", formal="R")
        _, snapshot = genesis(left, right)
        bad = relation(
            "rel_bad_hash",
            left,
            right,
            semantic_hash="0" * 64,
        )

        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_bad_hash",
                    (CreateRelationOp(relation=bad),),
                    base=snapshot.head,
                ),
            )

class AuthorityAndPrivacyTests(unittest.TestCase):
    def test_effective_decision_requires_policy_authority_and_same_actor(self) -> None:
        subject = entity("ent_subject", formal="question")
        _, snapshot = genesis(subject)
        weak = confirmed_decision(
            "dec_weak", "ent_subject", required_authority="L1"
        )
        with self.assertRaises(AuthorityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_weak_decision",
                    (RecordDecisionOp(decision=weak),),
                    base=snapshot.head,
                    actor=HUMAN,
                ),
            )

        valid = confirmed_decision("dec_valid", "ent_subject")
        with self.assertRaises(CandidateValidationError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_wrong_decider",
                    (RecordDecisionOp(decision=valid),),
                    base=snapshot.head,
                    actor=OTHER_HUMAN,
                ),
            )

    def test_authority_basis_can_only_name_a_prior_effective_decision(self) -> None:
        subject = entity("ent_subject", formal="question")
        _, snapshot = genesis(subject)
        decision = confirmed_decision("dec_gate", "ent_subject")
        same_transaction = transaction(
            "txn_self_authorize",
            (RecordDecisionOp(decision=decision),),
            base=snapshot.head,
            actor=HUMAN,
            authority_basis=("dec_gate",),
        )
        with self.assertRaises(CandidateValidationError):
            validate_candidate(snapshot, same_transaction)

        decision_txn = transaction(
            "txn_confirm_gate",
            (RecordDecisionOp(decision=decision),),
            base=snapshot.head,
            actor=HUMAN,
        )
        with_decision = validate_candidate(snapshot, decision_txn)
        blocker = RiskOrBlocker(
            blocker_id="blk_followup",
            project_id=PROJECT_ID,
            kind="followup",
            severity="warning",
            summary="A governed follow-up remains.",
            created_at="2026-07-11T00:04:00Z",
        )
        governed = validate_candidate(
            with_decision,
            transaction(
                "txn_governed",
                (RecordBlockerOp(blocker=blocker),),
                base=with_decision.head,
                authority_basis=("dec_gate",),
            ),
        )
        self.assertEqual(
            governed.derived_status["ent_subject"].human_acceptance,
            "human_confirmed",
        )

    def test_authority_precondition_uses_the_effective_decision_projection(self) -> None:
        subject = entity("ent_authority_precondition", formal="question")
        _, snapshot = genesis(subject)
        decision = confirmed_decision(
            "dec_authority_precondition", subject.entity_id
        )
        governed = validate_candidate(
            snapshot,
            transaction(
                "txn_authority_precondition_decision",
                (RecordDecisionOp(decision=decision),),
                base=snapshot.head,
                actor=HUMAN,
            ),
        )
        effective_hash = authority_semantic_hash(
            subject,
            governed.decisions,
            governed.effective_decisions,
        )
        stored_only_hash = facet_semantic_hash(subject, "authority")
        self.assertNotEqual(effective_hash, stored_only_hash)

        accepted = validate_candidate(
            governed,
            transaction(
                "txn_true_authority_precondition",
                (CreateEntityOp(entity=entity("ent_true_authority_probe")),),
                base=governed.head,
                preconditions=(
                    Precondition(
                        entity=EntityVersionRef(
                            entity_id=subject.entity_id, version=1
                        ),
                        expected_semantic_hashes={"authority": effective_hash},
                    ),
                ),
            ),
        )
        self.assertIn("ent_true_authority_probe", accepted.current_entities)

        with self.assertRaises(CandidateValidationError):
            validate_candidate(
                governed,
                transaction(
                    "txn_stored_only_authority_precondition",
                    (CreateEntityOp(entity=entity("ent_bad_authority_probe")),),
                    base=governed.head,
                    preconditions=(
                        Precondition(
                            entity=EntityVersionRef(
                                entity_id=subject.entity_id, version=1
                            ),
                            expected_semantic_hashes={
                                "authority": stored_only_hash
                            },
                        ),
                    ),
                ),
            )

    def test_privacy_downgrade_needs_prior_confirmed_declassification(self) -> None:
        source = entity("ent_private", formal="secret", privacy="restricted")
        target = entity("ent_public", formal="derived", privacy="public")
        _, snapshot = genesis(source, target)
        flow = relation("rel_private_public", source, target).model_copy(
            update={"privacy": "restricted"}
        )
        without_authority = transaction(
            "txn_private_flow",
            (CreateRelationOp(relation=flow),),
            base=snapshot.head,
        )
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(snapshot, without_authority)

        change = PrivacyChange(
            subject=EntityPrivacySubject(
                entity=EntityVersionRef(entity_id=source.entity_id, version=1)
            ),
            from_privacy="restricted",
            to_privacy="public",
        )
        deny = Decision(
            decision_id="dec_declassify",
            version=1,
            project_id=PROJECT_ID,
            decision_kind="privacy_declassification",
            subject_ref=source.entity_id,
            question="Release this exact source version?",
            options=("approve", "deny"),
            selected_option="deny",
            machine_outcome="deny",
            privacy_change=change,
            recommendation="deny",
            rationale="The human denies release.",
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-11T00:03:00Z",
            status="confirmed",
            privacy="restricted",
        )
        denial = transaction(
            "txn_deny_declassify",
            (RecordDecisionOp(decision=deny),),
            base=snapshot.head,
            actor=HUMAN,
        )
        denied_snapshot = validate_candidate(snapshot, denial)
        denied_flow = transaction(
            "txn_denied_flow",
            (CreateRelationOp(relation=flow),),
            base=denied_snapshot.head,
            authority_basis=(deny.decision_id,),
        )
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(denied_snapshot, denied_flow)

        approve = Decision(
            **{
                **deny.model_dump(mode="python"),
                "version": 2,
                "selected_option": "approve",
                "machine_outcome": "approve",
                "recommendation": "approve",
                "rationale": "The human authorizes this exact release.",
                "decided_at": "2026-07-11T00:04:00Z",
                "supersedes": DecisionVersionRef(
                    decision_id=deny.decision_id, version=1
                ),
            }
        )
        confirmation = transaction(
            "txn_approve_declassify",
            (
                SupersedeDecisionOp(
                    previous=DecisionVersionRef(
                        decision_id=deny.decision_id, version=1
                    ),
                    decision=approve,
                ),
            ),
            base=denied_snapshot.head,
            actor=HUMAN,
        )
        authorized_snapshot = validate_candidate(denied_snapshot, confirmation)
        authorized = transaction(
            "txn_authorized_flow",
            (CreateRelationOp(relation=flow),),
            base=authorized_snapshot.head,
            authority_basis=(approve.decision_id,),
        )

        updated = validate_candidate(authorized_snapshot, authorized)
        self.assertIn("rel_private_public", updated.current_relations)


class SupportedOperationProjectionTests(unittest.TestCase):
    def test_supported_operation_families_materialize_in_typed_snapshot(self) -> None:
        left = entity("ent_left", formal="L")
        right = entity("ent_right", formal="R")
        _, snapshot = genesis(left, right)
        first_relation = relation("rel_versioned", left, right)
        first_artifact = ArtifactRegistration(
            artifact_id="art_note",
            version=1,
            project_id=PROJECT_ID,
            logical_name="note-v1",
            media_type="text/plain",
            content_hash="a" * 64,
            byte_size=1,
            created_at="2026-07-11T00:05:00Z",
        )
        outcome = RouteOutcome(
            route_run_id="run_txn_supported_records",
            route_id="repair.dependency",
            outcome="validated",
            rationale="The structural candidate passed validation.",
            candidate_refs=(
                RelationVersionRef(
                    relation_id=first_relation.relation_id,
                    version=first_relation.version,
                ),
            ),
            validator_report_refs=(
                ArtifactDependencyRef(
                    artifact_id=first_artifact.artifact_id,
                    version=first_artifact.version,
                    content_hash=first_artifact.content_hash,
                ),
            ),
        )
        blocker = RiskOrBlocker(
            blocker_id="blk_supported_ops",
            project_id=PROJECT_ID,
            kind="remaining_check",
            severity="warning",
            summary="One later scientific check remains.",
            created_at="2026-07-11T00:05:01Z",
        )
        recorded = validate_candidate(
            snapshot,
            transaction(
                "txn_supported_records",
                (
                    CreateRelationOp(relation=first_relation),
                    RegisterArtifactOp(artifact=first_artifact),
                    RecordRouteOutcomeOp(outcome=outcome),
                    RecordBlockerOp(blocker=blocker),
                ),
                base=snapshot.head,
            ),
        )
        self.assertEqual(recorded.current_artifacts["art_note"], 1)
        self.assertEqual(recorded.route_outcomes[-1], outcome)
        self.assertEqual(recorded.blockers[-1], blocker)

        second_relation = RelationVersion(
            relation_id="rel_versioned",
            relation_type="depends_on",
            version=2,
            project_id=PROJECT_ID,
            source=EntityVersionRef(entity_id="ent_right", version=1),
            target=EntityVersionRef(entity_id="ent_left", version=1),
            dependency_mode="trace_only",
            created_at="2026-07-11T00:06:00Z",
            supersedes=RelationVersionRef(
                relation_id="rel_versioned", version=1
            ),
        )
        relation_updated = validate_candidate(
            recorded,
            transaction(
                "txn_supersede_relation",
                (
                    SupersedeRelationOp(
                        previous=RelationVersionRef(
                            relation_id="rel_versioned", version=1
                        ),
                        relation=second_relation,
                    ),
                ),
                base=recorded.head,
            ),
        )
        self.assertEqual(relation_updated.current_relations["rel_versioned"], 2)

        first_decision = confirmed_decision("dec_versioned", "ent_left")
        decision_recorded = validate_candidate(
            relation_updated,
            transaction(
                "txn_record_decision",
                (RecordDecisionOp(decision=first_decision),),
                base=relation_updated.head,
                actor=HUMAN,
            ),
        )
        second_decision = Decision(
            **{
                **first_decision.model_dump(mode="python"),
                "version": 2,
                "rationale": "The human reconfirmed after reviewing new evidence.",
                "decided_at": "2026-07-11T00:07:00Z",
                "supersedes": DecisionVersionRef(
                    decision_id="dec_versioned", version=1
                ),
            }
        )
        decision_updated = validate_candidate(
            decision_recorded,
            transaction(
                "txn_supersede_decision",
                (
                    SupersedeDecisionOp(
                        previous=DecisionVersionRef(
                            decision_id="dec_versioned", version=1
                        ),
                        decision=second_decision,
                    ),
                ),
                base=decision_recorded.head,
                actor=HUMAN,
            ),
        )
        self.assertEqual(decision_updated.current_decisions["dec_versioned"], 2)

        second_artifact = ArtifactRegistration(
            artifact_id="art_note",
            version=2,
            project_id=PROJECT_ID,
            logical_name="note-v2",
            media_type="text/plain",
            content_hash="b" * 64,
            byte_size=2,
            created_at="2026-07-11T00:08:00Z",
            supersedes=ArtifactVersionRef(artifact_id="art_note", version=1),
        )
        artifact_updated = validate_candidate(
            decision_updated,
            transaction(
                "txn_supersede_artifact",
                (RegisterArtifactOp(artifact=second_artifact),),
                base=decision_updated.head,
            ),
        )
        self.assertEqual(artifact_updated.current_artifacts["art_note"], 2)
        self.assertEqual(len(artifact_updated.artifacts), 2)

    def test_route_outcome_binds_one_exact_containing_run(self) -> None:
        _, snapshot = genesis()

        def outcome(run_id: str, route_id: str, status: str) -> RouteOutcome:
            candidate_refs = (
                (EntityVersionRef(entity_id=PROJECT_ID, version=1),)
                if status in {"completed_with_candidate", "validated", "rejected", "superseded"}
                else ()
            )
            return RouteOutcome(
                route_run_id=run_id,
                route_id=route_id,
                outcome=status,
                rationale="Exact canonical route outcome.",
                candidate_refs=candidate_refs,
            )

        wrong_run = transaction(
            "txn_wrong_outcome_run",
            (
                RecordRouteOutcomeOp(
                    outcome=outcome(
                        "run_someone_else",
                        "frame.question_and_benchmarks",
                        "failed",
                    )
                ),
            ),
            base=snapshot.head,
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(snapshot, wrong_run)

        wrong_route = transaction(
            "txn_wrong_outcome_route",
            (
                RecordRouteOutcomeOp(
                    outcome=outcome(
                        "run_txn_wrong_outcome_route",
                        "repair.dependency",
                        "failed",
                    )
                ),
            ),
            base=snapshot.head,
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(snapshot, wrong_route)

        conflicting = transaction(
            "txn_conflicting_outcomes",
            (
                RecordRouteOutcomeOp(
                    outcome=outcome(
                        "run_txn_conflicting_outcomes",
                        "frame.question_and_benchmarks",
                        "failed",
                    )
                ),
                RecordRouteOutcomeOp(
                    outcome=outcome(
                        "run_txn_conflicting_outcomes",
                        "frame.question_and_benchmarks",
                        "rejected",
                    )
                ),
            ),
            base=snapshot.head,
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(snapshot, conflicting)


class ReplayAndUnsupportedOperationTests(unittest.TestCase):
    def test_retire_and_status_transition_fail_closed(self) -> None:
        item = entity("ent_item", formal="value")
        _, snapshot = genesis(item)
        retire = transaction(
            "txn_retire",
            (
                RetireEntityOp(
                    entity=EntityVersionRef(entity_id="ent_item", version=1),
                    reason="Not enabled in Phase 1.",
                ),
            ),
            base=snapshot.head,
        )
        transition = transaction(
            "txn_transition",
            (
                StatusTransitionOp(
                    transition=StatusTransition(
                        entity=EntityVersionRef(entity_id="ent_item", version=1),
                        dimension="formal_validity",
                        to_value="verified_in_scope",
                    )
                ),
            ),
            base=snapshot.head,
        )
        for candidate in (retire, transition):
            with self.subTest(operation=candidate.operations[0].op):
                with self.assertRaises(UnsupportedOperationError):
                    validate_candidate(snapshot, candidate)

    def test_replay_walks_and_validates_the_exact_head_chain(self) -> None:
        genesis_txns, snapshot = genesis()
        decision = confirmed_decision("dec_replay", PROJECT_ID)
        update_txn = transaction(
            "txn_replay_decision",
            (RecordDecisionOp(decision=decision),),
            base=snapshot.head,
            actor=HUMAN,
        )
        expected = validate_candidate(snapshot, update_txn)

        with tempfile.TemporaryDirectory() as directory:
            layout = StoreLayout.at(directory).ensure()
            store = ObjectStore(layout)
            for txn in (*genesis_txns, update_txn):
                store.install_bytes(
                    "transactions",
                    transaction_digest(txn),
                    transaction_bytes(txn),
                )
            heads = HeadStore(layout)
            previous = None
            for txn in (*genesis_txns, update_txn):
                heads.replace(previous, transaction_digest(txn))
                previous = transaction_digest(txn)

            rebuilt = replay(layout)
            historical = replay_at(layout, transaction_digest(genesis_txns[0]))

        self.assertEqual(rebuilt, expected)
        self.assertEqual(historical.head, transaction_digest(genesis_txns[0]))
        self.assertEqual(len(historical.chain), 1)
        self.assertEqual(
            rebuilt.chain,
            tuple(transaction_digest(txn) for txn in genesis_txns)
            + (expected.head,),
        )


class DecisionFreshnessProjectionTests(unittest.TestCase):
    def test_superseding_effective_decision_stales_authority_dependents(self) -> None:
        governed = entity("ent_governed", formal="choice")
        dependent = entity("ent_dependent", formal="result")
        _, snapshot = genesis(governed, dependent)
        first_decision = confirmed_decision("dec_choice", governed.entity_id)
        decision_txn = transaction(
            "txn_decision_v1",
            (RecordDecisionOp(decision=first_decision),),
            base=snapshot.head,
            actor=HUMAN,
        )
        snapshot = validate_candidate(snapshot, decision_txn)

        authority_relation = RelationVersion(
            relation_id="rel_authority",
            relation_type="governed_by_decision",
            version=1,
            project_id=PROJECT_ID,
            source=EntityVersionRef(entity_id=governed.entity_id, version=1),
            target=EntityVersionRef(entity_id=dependent.entity_id, version=1),
            dependency_mode="hard",
            upstream=SemanticFacetRef(
                entity_id=governed.entity_id,
                version=1,
                facet="authority",
                semantic_hash=authority_semantic_hash(
                    governed,
                    snapshot.decisions,
                    snapshot.effective_decisions,
                ),
            ),
            downstream=FacetPathRef(
                entity_id=dependent.entity_id,
                version=1,
                facet="authority",
            ),
            created_at="2026-07-11T00:04:00Z",
        )
        relation_txn = transaction(
            "txn_authority_relation",
            (CreateRelationOp(relation=authority_relation),),
            base=snapshot.head,
        )
        snapshot = validate_candidate(snapshot, relation_txn)
        self.assertEqual(
            snapshot.derived_status[dependent.entity_id].freshness["authority"],
            "fresh",
        )

        replacement = Decision(
            **{
                **first_decision.model_dump(mode="python"),
                "version": 2,
                "selected_option": "reject",
                "recommendation": "reject",
                "rationale": "The human reverses the exact structural choice.",
                "decided_at": "2026-07-11T00:05:00Z",
                "supersedes": DecisionVersionRef(
                    decision_id=first_decision.decision_id, version=1
                ),
            }
        )
        reverse_txn = transaction(
            "txn_decision_v2",
            (
                SupersedeDecisionOp(
                    previous=DecisionVersionRef(
                        decision_id=first_decision.decision_id, version=1
                    ),
                    decision=replacement,
                ),
            ),
            base=snapshot.head,
            actor=HUMAN,
        )
        revised = validate_candidate(snapshot, reverse_txn)

        self.assertEqual(
            revised.derived_status[dependent.entity_id].freshness["authority"],
            "stale",
        )
        self.assertTrue(
            stale_reason_chains(revised, dependent.entity_id, "authority")
        )


class ArchitectureAuditRegressionTests(unittest.TestCase):
    def test_context_privacy_join_covers_every_text_bearing_output_family(self) -> None:
        source = entity("ent_context_floor", formal="secret", privacy="restricted")
        target = entity("ent_context_target", formal="target", privacy="public")
        context_payload = {
            "context_schema": "econ-theorist/compiled-context/v1",
            "entities": [source.model_dump(mode="json")],
            "relations": [],
            "effective_decisions": [],
            "status_source_decisions": [],
            "blockers": [],
        }
        proposed_decision = Decision(
            decision_id="dec_context_leak",
            version=1,
            project_id=PROJECT_ID,
            decision_kind="field",
            subject_ref=source.entity_id,
            question="Leak the restricted context?",
            options=("yes", "no"),
            recommendation="no",
            rationale="Restricted context must not enter a public Decision.",
            required_authority="L2",
            decider=AGENT,
            decided_at="2026-07-11T00:16:00Z",
            status="proposed",
            privacy="public",
        )
        public_artifact = ArtifactRegistration(
            artifact_id="art_context_leak",
            version=1,
            project_id=PROJECT_ID,
            logical_name="context leak",
            media_type="text/plain",
            content_hash="f" * 64,
            byte_size=1,
            privacy="public",
            created_at="2026-07-11T00:16:00Z",
        )
        public_blocker = RiskOrBlocker(
            blocker_id="blk_context_leak",
            project_id=PROJECT_ID,
            kind="leak",
            severity="warning",
            summary="Restricted context must not enter a public blocker.",
            privacy="public",
            created_at="2026-07-11T00:16:00Z",
        )
        public_relation = relation(
            "rel_context_leak", source, target, mode="trace_only"
        ).model_copy(update={"privacy": "public"})
        operation_sets = (
            (CreateEntityOp(entity=target),),
            (CreateRelationOp(relation=public_relation),),
            (RegisterArtifactOp(artifact=public_artifact),),
            (RecordDecisionOp(decision=proposed_decision),),
            (RecordBlockerOp(blocker=public_blocker),),
            (
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id="run_txn_context_outcome_leak",
                        route_id="frame.question_and_benchmarks",
                        outcome="failed",
                        rationale="Restricted context must not enter a public outcome.",
                        privacy="public",
                    )
                ),
            ),
        )
        for index, operations in enumerate(operation_sets):
            with self.subTest(operation=operations[0].op):
                candidate = transaction(
                    f"txn_context_output_leak_{index}",
                    operations,
                    base="e" * 64,
                )
                with self.assertRaises(PrivacyFlowError):
                    validate_route_context_output_flow(candidate, context_payload)

    def test_every_canonical_origin_requires_the_pinned_validator(self) -> None:
        root = project_entity()
        genesis_transaction = transaction(
            "txn_validator_genesis",
            (CreateEntityOp(entity=root),),
        )

        def drifted(name: str) -> str:
            return "9.9.9" if name == "pydantic" else "2.46.4"

        with patch("econ_theorist.policy.package_version", side_effect=drifted):
            with self.assertRaises(RegistryError):
                validate_candidate(None, genesis_transaction)

        _, snapshot = genesis()
        decision = confirmed_decision("dec_validator_human", PROJECT_ID)
        human_transaction = transaction(
            "txn_validator_human",
            (RecordDecisionOp(decision=decision),),
            base=snapshot.head,
            actor=HUMAN,
        )
        with patch("econ_theorist.policy.package_version", side_effect=drifted):
            with self.assertRaises(RegistryError):
                validate_candidate(snapshot, human_transaction)

    def test_canonical_object_ids_are_unique_across_object_families(self) -> None:
        left = entity("ent_global_id_left", formal="left")
        right = entity("ent_global_id_right", formal="right")
        _, snapshot = genesis(left, right)

        colliding_relation = relation(left.entity_id, left, right)
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_relation_entity_id_collision",
                    (CreateRelationOp(relation=colliding_relation),),
                    base=snapshot.head,
                ),
            )

        colliding_decision = confirmed_decision(left.entity_id, right.entity_id)
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_decision_entity_id_collision",
                    (RecordDecisionOp(decision=colliding_decision),),
                    base=snapshot.head,
                    actor=HUMAN,
                ),
            )

        shared_id = "obj_artifact_blocker_collision"
        artifact = ArtifactRegistration(
            artifact_id=shared_id,
            version=1,
            project_id=PROJECT_ID,
            logical_name="collision evidence",
            media_type="text/plain",
            content_hash="f" * 64,
            byte_size=1,
            created_at="2026-07-11T00:15:00Z",
        )
        blocker = RiskOrBlocker(
            blocker_id=shared_id,
            project_id=PROJECT_ID,
            kind="integrity_test",
            severity="error",
            summary="This ID intentionally collides with an artifact.",
            created_at="2026-07-11T00:15:01Z",
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_artifact_blocker_id_collision",
                    (
                        RegisterArtifactOp(artifact=artifact),
                        RecordBlockerOp(blocker=blocker),
                    ),
                    base=snapshot.head,
                ),
            )

        forged_artifact = artifact.model_copy(
            update={"artifact_id": left.entity_id}
        )
        malformed_snapshot = snapshot.model_copy(
            update={
                "artifacts": snapshot.artifacts + (forged_artifact,),
                "current_artifacts": {forged_artifact.artifact_id: 1},
            }
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                malformed_snapshot,
                transaction(
                    "txn_after_ambiguous_snapshot",
                    (CreateEntityOp(entity=entity("ent_after_ambiguous_snapshot")),),
                    base=malformed_snapshot.head,
                ),
            )

    def test_decision_references_resolve_to_canonical_object_families(self) -> None:
        subject = entity("ent_ref_subject", formal="subject")
        scope = entity("ent_ref_scope", formal="scope")
        dissent = entity("ent_ref_dissent", formal="dissent")
        affected = entity("ent_ref_affected", formal="affected scope")
        _, snapshot = genesis(subject, scope, dissent, affected)
        artifact = ArtifactRegistration(
            artifact_id="art_decision_evidence",
            version=1,
            project_id=PROJECT_ID,
            logical_name="decision evidence",
            media_type="text/plain",
            content_hash="1" * 64,
            byte_size=1,
            created_at="2026-07-11T00:16:00Z",
        )
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_decision_evidence_artifact",
                (RegisterArtifactOp(artifact=artifact),),
                base=snapshot.head,
            ),
        )

        template = confirmed_decision("dec_reference_template", subject.entity_id)
        invalid_updates = {
            "scope": {"scope_ref": artifact.artifact_id},
            "dissent": {"dissent_refs": (artifact.artifact_id,)},
            "affected": {"affected_scopes": (artifact.artifact_id,)},
            "evidence": {"evidence_refs": ("obj_missing_evidence",)},
        }
        for label, update in invalid_updates.items():
            with self.subTest(reference=label), self.assertRaises(
                ReferentialIntegrityError
            ):
                invalid = template.model_copy(
                    update={"decision_id": f"dec_bad_{label}_ref", **update}
                )
                validate_candidate(
                    snapshot,
                    transaction(
                        f"txn_bad_{label}_ref",
                        (RecordDecisionOp(decision=invalid),),
                        base=snapshot.head,
                        actor=HUMAN,
                    ),
                )

        malformed_decision = template.model_copy(
            update={
                "decision_id": "dec_snapshot_dangling_ref",
                "evidence_refs": ("obj_snapshot_missing_evidence",),
            }
        )
        malformed_snapshot = snapshot.model_copy(
            update={
                "decisions": snapshot.decisions + (malformed_decision,),
                "current_decisions": {malformed_decision.decision_id: 1},
            }
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                malformed_snapshot,
                transaction(
                    "txn_after_dangling_snapshot",
                    (CreateEntityOp(entity=entity("ent_after_dangling_snapshot")),),
                    base=malformed_snapshot.head,
                ),
            )

        valid = template.model_copy(
            update={
                "decision_id": "dec_valid_canonical_refs",
                "scope_ref": scope.entity_id,
                "dissent_refs": (dissent.entity_id,),
                "affected_scopes": (affected.entity_id,),
                "evidence_refs": (artifact.artifact_id,),
            }
        )
        updated = validate_candidate(
            snapshot,
            transaction(
                "txn_valid_canonical_refs",
                (RecordDecisionOp(decision=valid),),
                base=snapshot.head,
                actor=HUMAN,
            ),
        )
        self.assertEqual(updated.current_decisions[valid.decision_id], 1)

    def test_agent_entity_writes_cannot_self_promote_status(self) -> None:
        _, snapshot = genesis()
        promoted = entity("ent_promoted", formal="claim").model_copy(
            update={
                "status": ScientificStatus(
                    lifecycle="active", formal_validity="verified_in_scope"
                )
            }
        )
        with self.assertRaises(CandidateValidationError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_self_promote",
                    (CreateEntityOp(entity=promoted),),
                    base=snapshot.head,
                ),
            )

        proposed = entity("ent_proposed", formal="claim")
        _, snapshot = genesis(proposed)
        changed_status = entity("ent_proposed", version=2, formal="claim").model_copy(
            update={
                "status": ScientificStatus(
                    lifecycle="proposed", formal_validity="verified_in_scope"
                )
            }
        )
        with self.assertRaises(CandidateValidationError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_status_through_supersede",
                    (
                        SupersedeEntityOp(
                            previous=EntityVersionRef(
                                entity_id=proposed.entity_id, version=1
                            ),
                            entity=changed_status,
                        ),
                    ),
                    base=snapshot.head,
                    changed_facets=(
                        ChangedFacets(
                            entity_id=proposed.entity_id,
                            previous_version=1,
                            new_version=2,
                            facets=("formal",),
                        ),
                    ),
                ),
            )

    def test_artifact_and_compartment_downgrades_fail_closed(self) -> None:
        _, snapshot = genesis()
        first = ArtifactRegistration(
            artifact_id="art_secret",
            version=1,
            project_id=PROJECT_ID,
            logical_name="restricted note",
            media_type="text/plain",
            content_hash="a" * 64,
            byte_size=1,
            privacy="restricted",
            created_at="2026-07-11T00:10:00Z",
        )
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_secret_artifact",
                (RegisterArtifactOp(artifact=first),),
                base=snapshot.head,
            ),
        )
        public_version = ArtifactRegistration(
            artifact_id=first.artifact_id,
            version=2,
            project_id=PROJECT_ID,
            logical_name="public note",
            media_type="text/plain",
            content_hash="b" * 64,
            byte_size=1,
            privacy="public",
            created_at="2026-07-11T00:11:00Z",
            supersedes=ArtifactVersionRef(artifact_id=first.artifact_id, version=1),
        )
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_artifact_downgrade",
                    (RegisterArtifactOp(artifact=public_version),),
                    base=snapshot.head,
                ),
            )

        protected = entity("ent_holdout", formal="result").model_copy(
            update={
                "access_compartments": (
                    "project_research",
                    "confirmatory_holdout",
                )
            }
        )
        _, protected_snapshot = genesis(protected)
        weakened = entity(
            protected.entity_id, version=2, formal="result", presentation="rename"
        )
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                protected_snapshot,
                transaction(
                    "txn_remove_holdout",
                    (
                        SupersedeEntityOp(
                            previous=EntityVersionRef(
                                entity_id=protected.entity_id, version=1
                            ),
                            entity=weakened,
                        ),
                    ),
                    base=protected_snapshot.head,
                    changed_facets=(
                        ChangedFacets(
                            entity_id=protected.entity_id,
                            previous_version=1,
                            new_version=2,
                            facets=(
                                "terminology_presentation",
                                "authority",
                            ),
                        ),
                    ),
                ),
            )

    def test_local_only_cannot_be_declassified_even_by_approve(self) -> None:
        secret = entity("ent_local", formal="secret", privacy="local_only")
        _, snapshot = genesis(secret)
        change = PrivacyChange(
            subject=EntityPrivacySubject(
                entity=EntityVersionRef(entity_id=secret.entity_id, version=1)
            ),
            from_privacy="local_only",
            to_privacy="restricted",
        )
        decision = Decision(
            decision_id="dec_local_release",
            version=1,
            project_id=PROJECT_ID,
            decision_kind="privacy_declassification",
            subject_ref=secret.entity_id,
            question="Release local-only material?",
            options=("approve", "deny"),
            selected_option="approve",
            machine_outcome="approve",
            privacy_change=change,
            recommendation="deny",
            rationale="The runtime must reject this despite the selected option.",
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-11T00:12:00Z",
            status="confirmed",
            privacy="local_only",
        )
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_local_release",
                    (RecordDecisionOp(decision=decision),),
                    base=snapshot.head,
                    actor=HUMAN,
                ),
            )

    def test_exact_artifact_dependency_requires_version_and_hash(self) -> None:
        _, snapshot = genesis()
        artifact = ArtifactRegistration(
            artifact_id="art_exact",
            version=1,
            project_id=PROJECT_ID,
            logical_name="exact note",
            media_type="text/plain",
            content_hash="d" * 64,
            byte_size=1,
            created_at="2026-07-11T00:13:00Z",
        )
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_exact_artifact",
                (RegisterArtifactOp(artifact=artifact),),
                base=snapshot.head,
            ),
        )
        bad = entity("ent_bad_artifact", formal="claim").model_copy(
            update={
                "artifact_refs": (
                    ArtifactDependencyRef(
                        artifact_id=artifact.artifact_id,
                        version=artifact.version,
                        content_hash="e" * 64,
                    ),
                )
            }
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_bad_artifact_ref",
                    (CreateEntityOp(entity=bad),),
                    base=snapshot.head,
                ),
            )

        exact = entity("ent_exact_artifact", formal="claim").model_copy(
            update={
                "artifact_refs": (
                    ArtifactDependencyRef(
                        artifact_id=artifact.artifact_id,
                        version=artifact.version,
                        content_hash=artifact.content_hash,
                    ),
                )
            }
        )
        updated = validate_candidate(
            snapshot,
            transaction(
                "txn_exact_artifact_ref",
                (CreateEntityOp(entity=exact),),
                base=snapshot.head,
            ),
        )
        self.assertEqual(updated.current_entities[exact.entity_id], 1)

    def test_same_artifact_bytes_keep_one_cross_id_privacy_floor(self) -> None:
        _, snapshot = genesis()
        shared_hash = "d" * 64

        def registration(artifact_id: str, privacy: str) -> ArtifactRegistration:
            return ArtifactRegistration(
                artifact_id=artifact_id,
                version=1,
                project_id=PROJECT_ID,
                logical_name=artifact_id,
                media_type="application/octet-stream",
                content_hash=shared_hash,
                byte_size=10,
                privacy=privacy,
                created_at="2026-07-11T00:15:00Z",
            )

        secret = registration("art_secret_alias", "local_only")
        public = registration("art_public_alias", "public")
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_same_hash_same_batch",
                    (
                        RegisterArtifactOp(artifact=public),
                        RegisterArtifactOp(artifact=secret),
                    ),
                    base=snapshot.head,
                ),
            )

        secret_snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_secret_hash_first",
                (RegisterArtifactOp(artifact=secret),),
                base=snapshot.head,
            ),
        )
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                secret_snapshot,
                transaction(
                    "txn_public_hash_later",
                    (RegisterArtifactOp(artifact=public),),
                    base=secret_snapshot.head,
                ),
            )

    def test_exact_artifact_release_persists_without_repeating_authority(self) -> None:
        _, snapshot = genesis()
        first = ArtifactRegistration(
            artifact_id="art_exact_release",
            version=1,
            project_id=PROJECT_ID,
            logical_name="restricted exact bytes",
            media_type="application/octet-stream",
            content_hash="9" * 64,
            byte_size=7,
            privacy="restricted",
            created_at="2026-07-11T00:17:00Z",
        )
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_exact_release_source",
                (RegisterArtifactOp(artifact=first),),
                base=snapshot.head,
            ),
        )
        release = Decision(
            decision_id="dec_exact_artifact_release",
            version=1,
            project_id=PROJECT_ID,
            decision_kind="privacy_declassification",
            subject_ref=first.artifact_id,
            question="Release these exact immutable bytes?",
            options=("approve", "deny"),
            selected_option="approve",
            machine_outcome="approve",
            privacy_change=PrivacyChange(
                subject=ArtifactPrivacySubject(
                    artifact=ArtifactVersionRef(
                        artifact_id=first.artifact_id, version=1
                    )
                ),
                from_privacy="restricted",
                to_privacy="public",
            ),
            recommendation="approve",
            rationale="The human authorizes this exact byte sequence.",
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-11T00:17:01Z",
            status="confirmed",
            privacy="restricted",
        )
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_exact_release_decision",
                (RecordDecisionOp(decision=release),),
                base=snapshot.head,
                actor=HUMAN,
            ),
        )
        public = ArtifactRegistration(
            artifact_id=first.artifact_id,
            version=2,
            project_id=PROJECT_ID,
            logical_name="released exact bytes",
            media_type=first.media_type,
            content_hash=first.content_hash,
            byte_size=first.byte_size,
            privacy="public",
            created_at="2026-07-11T00:17:02Z",
            supersedes=ArtifactVersionRef(
                artifact_id=first.artifact_id, version=1
            ),
        )
        changed_bytes = public.model_copy(update={"content_hash": "7" * 64})
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_exact_release_changed_bytes",
                    (RegisterArtifactOp(artifact=changed_bytes),),
                    base=snapshot.head,
                    authority_basis=(release.decision_id,),
                    privacy="restricted",
                ),
            )
        released = validate_candidate(
            snapshot,
            transaction(
                "txn_exact_release_apply",
                (RegisterArtifactOp(artifact=public),),
                base=snapshot.head,
                authority_basis=(release.decision_id,),
                privacy="restricted",
            ),
        )
        unrelated = entity("ent_after_exact_release", formal="unrelated")
        advanced = validate_candidate(
            released,
            transaction(
                "txn_after_exact_release",
                (CreateEntityOp(entity=unrelated),),
                base=released.head,
            ),
        )
        self.assertEqual(advanced.current_artifacts[first.artifact_id], 2)
        self.assertEqual(advanced.current_entities[unrelated.entity_id], 1)

    def test_route_outcome_and_blocker_refs_resolve_exactly(self) -> None:
        subject = entity("ent_exact_record_subject", formal="subject")
        _, snapshot = genesis(subject)
        ghost_outcome = RouteOutcome(
            route_run_id="run_txn_ghost_outcome_ref",
            route_id="frame.question_and_benchmarks",
            outcome="completed_with_candidate",
            rationale="A missing candidate cannot become canonical.",
            candidate_refs=(
                EntityVersionRef(entity_id="ent_missing_candidate", version=1),
            ),
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_ghost_outcome_ref",
                    (RecordRouteOutcomeOp(outcome=ghost_outcome),),
                    base=snapshot.head,
                ),
            )

        ghost_report = RouteOutcome(
            route_run_id="run_txn_ghost_validator_ref",
            route_id="frame.question_and_benchmarks",
            outcome="validated",
            rationale="Validation requires an exact report artifact.",
            candidate_refs=(
                EntityVersionRef(entity_id=subject.entity_id, version=1),
            ),
            validator_report_refs=(
                ArtifactDependencyRef(
                    artifact_id="art_missing_validator",
                    version=1,
                    content_hash="8" * 64,
                ),
            ),
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_ghost_validator_ref",
                    (RecordRouteOutcomeOp(outcome=ghost_report),),
                    base=snapshot.head,
                ),
            )

        for blocker in (
            RiskOrBlocker(
                blocker_id="blk_ghost_affected",
                project_id=PROJECT_ID,
                kind="missing_ref",
                severity="critical",
                summary="The affected object must exist.",
                affected_refs=(
                    EntityVersionRef(entity_id="ent_missing_affected", version=1),
                ),
                created_at="2026-07-11T00:18:00Z",
            ),
            RiskOrBlocker(
                blocker_id="blk_bad_required_route",
                project_id=PROJECT_ID,
                kind="bad_route",
                severity="critical",
                summary="The required route must be registered exactly.",
                required_route="repair.dependncy",
                created_at="2026-07-11T00:18:01Z",
            ),
            RiskOrBlocker(
                blocker_id="blk_self_ref",
                project_id=PROJECT_ID,
                kind="self_ref",
                severity="error",
                summary="A blocker cannot create a self-reference.",
                affected_refs=(BlockerRef(blocker_id="blk_self_ref"),),
                created_at="2026-07-11T00:18:02Z",
            ),
        ):
            with self.subTest(blocker=blocker.blocker_id), self.assertRaises(
                ReferentialIntegrityError
            ):
                validate_candidate(
                    snapshot,
                    transaction(
                        f"txn_{blocker.blocker_id}",
                        (RecordBlockerOp(blocker=blocker),),
                        base=snapshot.head,
                    ),
                )

    def test_cross_version_stale_evidence_closes_overlapping_path_roots(self) -> None:
        upstream_v1 = entity(
            "ent_stale_root", formal={"x": 1}
        )
        middle_v1 = entity(
            "ent_stale_middle", formal={"x": {"y": 1}}
        )
        downstream = entity("ent_stale_downstream", formal="claim")
        _, snapshot = genesis(upstream_v1, middle_v1, downstream)

        first = RelationVersion(
            relation_id="rel_stale_root_middle",
            relation_type="depends_on",
            version=1,
            project_id=PROJECT_ID,
            source=EntityVersionRef(entity_id=upstream_v1.entity_id, version=1),
            target=EntityVersionRef(entity_id=middle_v1.entity_id, version=1),
            dependency_mode="hard",
            upstream=SemanticFacetRef(
                entity_id=upstream_v1.entity_id,
                version=1,
                facet="formal",
                field_path="/value/x",
                semantic_hash=facet_semantic_hash(
                    upstream_v1, "formal", "/value/x"
                ),
            ),
            downstream=FacetPathRef(
                entity_id=middle_v1.entity_id,
                version=1,
                facet="formal",
                field_path="/value/x",
            ),
            created_at="2026-07-11T00:19:00Z",
        )
        second = RelationVersion(
            relation_id="rel_stale_middle_downstream",
            relation_type="depends_on",
            version=1,
            project_id=PROJECT_ID,
            source=EntityVersionRef(entity_id=middle_v1.entity_id, version=1),
            target=EntityVersionRef(entity_id=downstream.entity_id, version=1),
            dependency_mode="hard",
            upstream=SemanticFacetRef(
                entity_id=middle_v1.entity_id,
                version=1,
                facet="formal",
                field_path="/value/x/y",
                semantic_hash=facet_semantic_hash(
                    middle_v1, "formal", "/value/x/y"
                ),
            ),
            downstream=FacetPathRef(
                entity_id=downstream.entity_id,
                version=1,
                facet="formal",
            ),
            created_at="2026-07-11T00:19:01Z",
        )
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_stale_overlap_relations",
                (
                    CreateRelationOp(relation=first),
                    CreateRelationOp(relation=second),
                ),
                base=snapshot.head,
            ),
        )
        middle_v2 = entity(
            middle_v1.entity_id,
            version=2,
            formal={"x": {"y": 1}},
            presentation="renamed only",
        )
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_stale_middle_presentation_only",
                (
                    SupersedeEntityOp(
                        previous=EntityVersionRef(
                            entity_id=middle_v1.entity_id, version=1
                        ),
                        entity=middle_v2,
                    ),
                ),
                base=snapshot.head,
                changed_facets=(
                    ChangedFacets(
                        entity_id=middle_v1.entity_id,
                        previous_version=1,
                        new_version=2,
                        facets=("terminology_presentation",),
                    ),
                ),
            ),
        )
        upstream_v2 = entity(
            upstream_v1.entity_id,
            version=2,
            formal={"x": 2},
            privacy="restricted",
        )
        revised = validate_candidate(
            snapshot,
            transaction(
                "txn_stale_root_restricted_change",
                (
                    SupersedeEntityOp(
                        previous=EntityVersionRef(
                            entity_id=upstream_v1.entity_id, version=1
                        ),
                        entity=upstream_v2,
                    ),
                ),
                base=snapshot.head,
                changed_facets=(
                    ChangedFacets(
                        entity_id=upstream_v1.entity_id,
                        previous_version=1,
                        new_version=2,
                        facets=("formal", "authority"),
                    ),
                ),
            ),
        )
        status = revised.derived_status[downstream.entity_id]
        self.assertEqual(status.freshness["formal"], "stale")
        self.assertEqual(
            revised.derived_status[middle_v2.entity_id].freshness["formal"],
            "stale",
        )
        evidence_ids = {
            evidence.relation_id
            for reason in status.stale_reasons["formal"]
            for evidence in reason.source_evidence
        }
        self.assertEqual(
            evidence_ids,
            {first.relation_id, second.relation_id},
        )
        with self.assertRaises(ContextAccessError):
            compile_context(
                revised,
                route=get_route("repair.dependency"),
                actor=AGENT,
                purpose="research_repair",
                compartments=("project_research",),
                privacy_clearance="project_private",
                focus_entity_ids=(downstream.entity_id,),
                budget_units=20_000,
            )
        compiled = compile_context(
            revised,
            route=get_route("repair.dependency"),
            actor=AGENT,
            purpose="research_repair",
            compartments=("project_research",),
            privacy_clearance="restricted",
            focus_entity_ids=(downstream.entity_id,),
            budget_units=20_000,
        )
        selected = {
            (reference.entity_id, reference.version)
            for reference in compiled.selected_entity_refs
        }
        self.assertTrue(
            {
                (upstream_v1.entity_id, 1),
                (upstream_v2.entity_id, 2),
                (middle_v1.entity_id, 1),
                (middle_v2.entity_id, 2),
            }.issubset(selected)
        )

    def test_reference_privacy_is_minimal_but_preconditions_are_tainted(self) -> None:
        restricted = entity(
            "ent_restricted_reference", formal="secret", privacy="restricted"
        )
        _, snapshot = genesis(restricted)
        underlabelled = confirmed_decision(
            "dec_underlabelled_reference", restricted.entity_id
        )
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_underlabelled_reference",
                    (RecordDecisionOp(decision=underlabelled),),
                    base=snapshot.head,
                    actor=HUMAN,
                ),
            )

        underlabelled_scope = entity(
            "ent_underlabelled_scope",
            formal="public envelope",
            scope_ref=restricted.entity_id,
        )
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_underlabelled_scope",
                    (CreateEntityOp(entity=underlabelled_scope),),
                    base=snapshot.head,
                ),
            )

        protected_decision = underlabelled.model_copy(
            update={
                "decision_id": "dec_protected_reference",
                "privacy": "restricted",
            }
        )
        governed = validate_candidate(
            snapshot,
            transaction(
                "txn_protected_reference",
                (RecordDecisionOp(decision=protected_decision),),
                base=snapshot.head,
                actor=HUMAN,
            ),
        )
        unrelated = entity("ent_unrelated_after_restricted_decision", formal="plain")
        advanced = validate_candidate(
            governed,
            transaction(
                "txn_unrelated_after_restricted_decision",
                (CreateEntityOp(entity=unrelated),),
                base=governed.head,
            ),
        )
        self.assertEqual(advanced.current_entities[unrelated.entity_id], 1)

        preconditioned = entity("ent_precondition_output", formal="plain")
        with self.assertRaises(PrivacyFlowError):
            validate_candidate(
                governed,
                transaction(
                    "txn_restricted_precondition",
                    (CreateEntityOp(entity=preconditioned),),
                    base=governed.head,
                    preconditions=(
                        Precondition(
                            entity=EntityVersionRef(
                                entity_id=restricted.entity_id, version=1
                            ),
                            expected_semantic_hashes={
                                "formal": facet_semantic_hash(restricted, "formal")
                            },
                        ),
                    ),
                    privacy="project_private",
                ),
            )

    def test_stale_base_is_operational_not_a_canonical_route_outcome(self) -> None:
        with self.assertRaises(ValueError):
            RouteOutcome(
                route_run_id="run_stale_base_only",
                route_id="frame.question_and_benchmarks",
                outcome="stale_base",
                rationale="Lock-time staleness belongs to an operational sidecar.",
            )

    def test_route_outcome_status_constrains_canonical_writes(self) -> None:
        subject = entity("ent_outcome_existing_candidate", formal="existing")
        _, snapshot = genesis(subject)
        with self.assertRaises(ValueError):
            RouteOutcome(
                route_run_id="run_completed_without_candidate",
                route_id="frame.question_and_benchmarks",
                outcome="completed_with_candidate",
                rationale="Completion without a candidate is contradictory.",
            )

        rejected_write = entity("ent_rejected_write", formal="must not commit")
        rejected = RouteOutcome(
            route_run_id="run_txn_rejected_scientific_write",
            route_id="frame.question_and_benchmarks",
            outcome="rejected",
            rationale="A rejected run cannot apply its scientific write.",
            candidate_refs=(
                EntityVersionRef(entity_id=subject.entity_id, version=1),
            ),
        )
        with self.assertRaises(CandidateValidationError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_rejected_scientific_write",
                    (
                        CreateEntityOp(entity=rejected_write),
                        RecordRouteOutcomeOp(outcome=rejected),
                    ),
                    base=snapshot.head,
                ),
            )

        proposal = entity("ent_completed_candidate", formal="new candidate")
        wrong_candidate = RouteOutcome(
            route_run_id="run_txn_completed_wrong_candidate",
            route_id="frame.question_and_benchmarks",
            outcome="completed_with_candidate",
            rationale="The candidate ref must name this transaction's output.",
            candidate_refs=(
                EntityVersionRef(entity_id=subject.entity_id, version=1),
            ),
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_completed_wrong_candidate",
                    (
                        CreateEntityOp(entity=proposal),
                        RecordRouteOutcomeOp(outcome=wrong_candidate),
                    ),
                    base=snapshot.head,
                ),
            )

        completed = wrong_candidate.model_copy(
            update={
                "route_run_id": "run_txn_completed_exact_candidate",
                "candidate_refs": (
                    EntityVersionRef(entity_id=proposal.entity_id, version=1),
                ),
            }
        )
        updated = validate_candidate(
            snapshot,
            transaction(
                "txn_completed_exact_candidate",
                (
                    CreateEntityOp(entity=proposal),
                    RecordRouteOutcomeOp(outcome=completed),
                ),
                base=snapshot.head,
            ),
        )
        self.assertEqual(updated.current_entities[proposal.entity_id], 1)

    def test_scope_overlap_is_typed_and_binds_exact_scope_versions(self) -> None:
        scope_left = entity("scope_left", formal="left scope")
        scope_right = entity("scope_right", formal="right scope")
        left = entity("ent_left_scope", formal="left", scope_ref=scope_left.entity_id)
        right = entity(
            "ent_right_scope", formal="right", scope_ref=scope_right.entity_id
        )
        _, snapshot = genesis(scope_left, scope_right, left, right)
        scoped = relation(
            "rel_scoped",
            left,
            right,
            mode="scope_sensitive",
            scope_overlap=ScopeOverlapEvidence(
                source_scope=EntityVersionRef(
                    entity_id=scope_left.entity_id, version=1
                ),
                target_scope=EntityVersionRef(
                    entity_id=scope_right.entity_id, version=1
                ),
            ),
        )
        updated = validate_candidate(
            snapshot,
            transaction(
                "txn_typed_overlap",
                (CreateRelationOp(relation=scoped),),
                base=snapshot.head,
            ),
        )
        self.assertIn(scoped.relation_id, updated.current_relations)

        wrong = scoped.model_copy(
            update={
                "relation_id": "rel_wrong_overlap",
                "scope_overlap": ScopeOverlapEvidence(
                    source_scope=EntityVersionRef(
                        entity_id=scope_right.entity_id, version=1
                    ),
                    target_scope=EntityVersionRef(
                        entity_id=scope_left.entity_id, version=1
                    ),
                ),
            }
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_wrong_overlap",
                    (CreateRelationOp(relation=wrong),),
                    base=snapshot.head,
                ),
            )

    def test_cross_version_edges_carry_stale_unchanged_facets_forward(self) -> None:
        left_v1 = entity("ent_cycle_left", formal="L1")
        right_v1 = entity(
            "ent_cycle_right", formal="R1", presentation="old wording"
        )
        _, snapshot = genesis(left_v1, right_v1)
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_first_edge",
                (
                    CreateRelationOp(
                        relation=relation("rel_left_right", left_v1, right_v1)
                    ),
                ),
                base=snapshot.head,
            ),
        )
        left_v2 = entity("ent_cycle_left", version=2, formal="L2")
        right_v2 = entity(
            "ent_cycle_right", version=2, formal="R1", presentation="new wording"
        )
        candidate = transaction(
            "txn_cross_version_edges",
            (
                SupersedeEntityOp(
                    previous=EntityVersionRef(entity_id=left_v1.entity_id, version=1),
                    entity=left_v2,
                ),
                SupersedeEntityOp(
                    previous=EntityVersionRef(entity_id=right_v1.entity_id, version=1),
                    entity=right_v2,
                ),
                CreateRelationOp(
                    relation=relation("rel_right_left", right_v2, left_v2)
                ),
            ),
            base=snapshot.head,
            changed_facets=(
                ChangedFacets(
                    entity_id=left_v1.entity_id,
                    previous_version=1,
                    new_version=2,
                    facets=("formal",),
                ),
                ChangedFacets(
                    entity_id=right_v1.entity_id,
                    previous_version=1,
                    new_version=2,
                    facets=("terminology_presentation",),
                ),
            ),
        )
        updated = validate_candidate(snapshot, candidate)
        self.assertEqual(
            updated.derived_status[left_v2.entity_id].freshness["formal"], "stale"
        )
        self.assertEqual(
            updated.derived_status[right_v2.entity_id].freshness["formal"], "stale"
        )

    def test_effective_revision_and_acceptance_remain_separate_by_kind(self) -> None:
        subject = entity("ent_multi_decision", formal="question")
        _, snapshot = genesis(subject)
        framing = confirmed_decision("dec_framing", subject.entity_id)
        framing_txn = transaction(
            "txn_framing_decision",
            (RecordDecisionOp(decision=framing),),
            base=snapshot.head,
            actor=HUMAN,
        )
        snapshot = validate_candidate(snapshot, framing_txn)
        framing_ref = next(iter(snapshot.effective_decisions.values()))
        self.assertEqual(framing_ref.effective_revision, transaction_digest(framing_txn))

        field_rejection = Decision(
            decision_id="dec_field",
            version=1,
            project_id=PROJECT_ID,
            decision_kind="field",
            subject_ref=subject.entity_id,
            question="Use this field classification?",
            options=("micro", "macro"),
            recommendation="micro",
            rationale="The human rejects the current classification.",
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-11T00:14:00Z",
            status="rejected",
        )
        snapshot = validate_candidate(
            snapshot,
            transaction(
                "txn_field_rejection",
                (RecordDecisionOp(decision=field_rejection),),
                base=snapshot.head,
                actor=HUMAN,
            ),
        )
        derived = snapshot.derived_status[subject.entity_id]
        self.assertEqual(derived.human_acceptance, "human_mixed")
        self.assertEqual(
            derived.acceptance_by_kind["G1_question_benchmark"], "human_confirmed"
        )
        self.assertEqual(derived.acceptance_by_kind["field"], "human_rejected")

    def test_field_paths_require_canonical_rfc6901_pointers(self) -> None:
        with self.assertRaises(ValueError):
            FacetPathRef(
                entity_id="ent_pointer",
                version=1,
                facet="formal",
                field_path="nested.value",
            )
        with self.assertRaises(ValueError):
            FacetPathRef(
                entity_id="ent_pointer",
                version=1,
                facet="formal",
                field_path="/bad~2escape",
            )
        valid = FacetPathRef(
            entity_id="ent_pointer",
            version=1,
            facet="formal",
            field_path="/nested/key~1with~0escape",
        )
        self.assertEqual(valid.field_path, "/nested/key~1with~0escape")

        sequence_entity = entity("ent_sequence_path").model_copy(
            update={"facets": FacetPayloads(formal={"arr": ["x", "y"]})}
        )
        self.assertEqual(
            facet_semantic_hash(sequence_entity, "formal", "/arr/0"),
            object_digest("x"),
        )
        for alias in ("/arr/00", "/arr/+0", "/arr/-1"):
            with self.subTest(alias=alias):
                with self.assertRaises(FacetPathError):
                    facet_semantic_hash(sequence_entity, "formal", alias)

        other = entity("ent_sequence_other").model_copy(
            update={"facets": FacetPayloads(formal={"arr": ["z"]})}
        )
        _, snapshot = genesis(sequence_entity, other)
        valid_edge = relation("rel_sequence_valid", sequence_entity, other).model_copy(
            update={
                "upstream": SemanticFacetRef(
                    entity_id=sequence_entity.entity_id,
                    version=1,
                    facet="formal",
                    field_path="/arr/0",
                    semantic_hash=facet_semantic_hash(
                        sequence_entity, "formal", "/arr/0"
                    ),
                ),
                "downstream": FacetPathRef(
                    entity_id=other.entity_id,
                    version=1,
                    facet="formal",
                    field_path="/arr/0",
                ),
            }
        )
        alias_edge = relation("rel_sequence_alias", other, sequence_entity).model_copy(
            update={
                "upstream": SemanticFacetRef(
                    entity_id=other.entity_id,
                    version=1,
                    facet="formal",
                    field_path="/arr/00",
                    semantic_hash=facet_semantic_hash(other, "formal", "/arr/0"),
                ),
                "downstream": FacetPathRef(
                    entity_id=sequence_entity.entity_id,
                    version=1,
                    facet="formal",
                    field_path="/arr/00",
                ),
            }
        )
        with self.assertRaises(ReferentialIntegrityError):
            validate_candidate(
                snapshot,
                transaction(
                    "txn_sequence_alias_cycle",
                    (
                        CreateRelationOp(relation=valid_edge),
                        CreateRelationOp(relation=alias_edge),
                    ),
                    base=snapshot.head,
                ),
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
