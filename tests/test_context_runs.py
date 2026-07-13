"""Contracts for exact routes, bounded contexts, and operational route runs."""

from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from tests.helpers import load_json_bytes, sha256_bytes

from econ_theorist.codec import canonical_json_bytes, object_digest
from econ_theorist.errors import IntegrityError, RegistryError
from econ_theorist.context import (
    ContextAccessError,
    ContextBudgetError,
    ContextCompilationError,
    compile_context,
    lexical_units,
    units_for_bytes,
)
from econ_theorist.models import (
    Actor,
    Decision,
    DecisionVersionRef,
    EffectiveDecisionRef,
    EntityDerivedStatus,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    FacetPayloads,
    RelationVersion,
    RiskOrBlocker,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
    StaleDependencyEvidence,
    StaleReason,
)
from econ_theorist.route_registry import (
    RouteAuthorizationError,
    RouteUnavailableError,
    authorize_route,
    get_route,
)
from econ_theorist.policy import (
    KERNEL_HASH,
    KERNEL_VERSION,
    ROUTE_REGISTRY_V1_HASH,
    ROUTE_REGISTRY_V2_HASH,
    ROUTE_REGISTRY_V3_HASH,
    ROUTE_REGISTRY_V4_HASH,
    V2_ENABLED_ROUTE_IDS,
    V4_ENABLED_ROUTE_IDS,
    load_route_registry,
    load_route_registry_by_hash,
    registry_hash,
    theory_kernel,
)
from econ_theorist.project import init_project
from econ_theorist.runs import (
    RunBaseMismatch,
    RunError,
    begin_run,
    candidate_path,
    compiled_context_path,
    context_path,
    read_compiled_context,
    read_context,
    read_run,
    run_path,
)
from econ_theorist.runtime import HeadStore, StoreLayout


HEAD = "a" * 64
ACTOR = Actor(kind="agent", actor_id="agent_context_test")


def make_entity(
    entity_id: str,
    entity_type: str,
    *,
    title: str | None = None,
    formal: dict[str, object] | None = None,
    privacy: str = "project_private",
    compartments: tuple[str, ...] = ("project_research",),
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=entity_type,
        version=1,
        project_id="prj_context",
        title=title or entity_id,
        summary=f"Exact summary for {entity_id}.",
        status=ScientificStatus(lifecycle="active"),
        facets=FacetPayloads(formal=formal or {}),
        privacy=privacy,
        access_compartments=compartments,
        created_at="2026-07-11T00:00:00Z",
    )


def dependency(
    relation_id: str,
    source: EntityVersion,
    target: EntityVersion,
    *,
    privacy: str = "project_private",
) -> RelationVersion:
    return RelationVersion(
        relation_id=relation_id,
        relation_type="supports",
        version=1,
        project_id="prj_context",
        source=EntityVersionRef(entity_id=source.entity_id, version=source.version),
        target=EntityVersionRef(entity_id=target.entity_id, version=target.version),
        dependency_mode="hard",
        upstream=SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet="formal",
            semantic_hash=object_digest(source.facets.formal),
        ),
        downstream=FacetPathRef(
            entity_id=target.entity_id,
            version=target.version,
            facet="formal",
        ),
        privacy=privacy,
        created_at="2026-07-11T00:00:00Z",
    )


def fixture_snapshot(*, private_neighbor: bool = False) -> Snapshot:
    project = make_entity("ent_project", "Project")
    assumption = make_entity(
        "ent_assumption",
        "Assumption",
        formal={"quantifier": "for every type", "scope": "benchmark_domain"},
    )
    claim = make_entity(
        "ent_claim",
        "Claim",
        formal={"statement": "For every type, action x is optimal."},
    )
    verification = make_entity(
        "ent_verification",
        "Verification",
        privacy="restricted" if private_neighbor else "project_private",
    )
    independent = make_entity("ent_independent", "Claim")
    relations = (
        dependency("rel_assumption_claim", assumption, claim),
        dependency("rel_claim_verification", claim, verification),
    )
    entities = (project, assumption, claim, verification, independent)
    return Snapshot(
        project_id="prj_context",
        head=HEAD,
        chain=(HEAD,),
        entity_versions=entities,
        relation_versions=relations,
        current_entities={entity.entity_id: 1 for entity in entities},
        current_relations={relation.relation_id: 1 for relation in relations},
    )


class RouteRegistryTests(unittest.TestCase):
    def test_frozen_v2_disables_authoring_while_active_v4_preserves_phase3_and_adds_phase4(self) -> None:
        framing = authorize_route(
            "frame.question_and_benchmarks",
            purpose="research_framing",
            compartments=("project_research",),
            privacy_clearance="project_private",
        )
        repair = authorize_route(
            "repair.dependency",
            purpose="research_repair",
            compartments=("project_research",),
            privacy_clearance="project_private",
        )
        self.assertEqual(framing.availability, "enabled")
        self.assertEqual(repair.availability, "enabled")

        decomposition = authorize_route(
            "decompose.primitives",
            purpose="research_discovery",
            compartments=("project_research",),
            privacy_clearance="project_private",
        )
        self.assertEqual(decomposition.route_version, 2)
        with self.assertRaises(RouteUnavailableError):
            authorize_route(
                "design.reader_path",
                purpose="research_authoring",
                compartments=("project_research",),
                privacy_clearance="project_private",
                route_registry_hash=ROUTE_REGISTRY_V2_HASH,
            )
        authoring = authorize_route(
            "design.reader_path",
            purpose="research_authoring",
            compartments=("project_research",),
            privacy_clearance="project_private",
        )
        self.assertEqual(authoring.route_version, 3)
        profiled_authoring = authorize_route(
            "resolve.profile_stack",
            purpose="research_authoring",
            compartments=("project_research",),
            privacy_clearance="project_private",
        )
        self.assertEqual(profiled_authoring.route_version, 4)
        with self.assertRaises(RouteAuthorizationError):
            authorize_route(
                "repair.dependency",
                purpose="research_authoring",
                compartments=("project_research",),
                privacy_clearance="project_private",
            )
        with self.assertRaises(RouteAuthorizationError):
            authorize_route(
                "repair.dependency",
                purpose="research_repair",
                compartments=(),
                privacy_clearance="project_private",
            )

    def test_registry_content_is_pinned_not_just_route_ids(self) -> None:
        source = Path(__file__).parents[1] / "routes" / "registry.v1.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["routes"][0]["allowed_purposes"] = ["confirmatory_evaluation"]
        with tempfile.TemporaryDirectory() as directory:
            tampered = Path(directory) / "registry.json"
            tampered.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(RegistryError):
                load_route_registry(tampered)

    def test_v1_v2_v3_are_historical_and_v4_is_the_active_catalog(self) -> None:
        active = load_route_registry()
        historical_v1 = load_route_registry_by_hash(ROUTE_REGISTRY_V1_HASH)
        historical_v2 = load_route_registry_by_hash(ROUTE_REGISTRY_V2_HASH)
        historical_v3 = load_route_registry_by_hash(ROUTE_REGISTRY_V3_HASH)
        self.assertEqual(active.registry_version, 4)
        self.assertEqual(registry_hash(active), ROUTE_REGISTRY_V4_HASH)
        self.assertEqual(historical_v1.registry_version, 1)
        self.assertEqual(registry_hash(historical_v1), ROUTE_REGISTRY_V1_HASH)
        self.assertEqual(historical_v2.registry_version, 2)
        self.assertEqual(registry_hash(historical_v2), ROUTE_REGISTRY_V2_HASH)
        self.assertEqual(historical_v3.registry_version, 3)
        self.assertEqual(registry_hash(historical_v3), ROUTE_REGISTRY_V3_HASH)
        self.assertEqual(
            sum(route.availability == "enabled" for route in active.routes),
            len(V4_ENABLED_ROUTE_IDS),
        )
        self.assertEqual(
            sum(route.availability == "enabled" for route in historical_v1.routes), 2
        )
        self.assertEqual(
            sum(route.availability == "enabled" for route in historical_v2.routes),
            len(V2_ENABLED_ROUTE_IDS),
        )


class ContextCompilerTests(unittest.TestCase):
    def test_etai_lexical_v1_has_an_explicit_provider_neutral_definition(self) -> None:
        # ASCII runs, a digit run, punctuation, and each CJK codepoint.
        self.assertEqual(lexical_units("Alpha_beta 123, \u7ecf\u6d4e"), 7)

    def test_always_on_kernel_has_a_hard_architecture_budget(self) -> None:
        encoded = canonical_json_bytes(
            {
                "kernel_version": KERNEL_VERSION,
                "kernel_hash": KERNEL_HASH,
                "content": dict(theory_kernel()),
            }
        )
        units = units_for_bytes(encoded)
        self.assertGreater(units, 50)
        self.assertLessEqual(units, 2_000)

    def test_context_is_deterministic_and_contains_exact_ancestor(self) -> None:
        snapshot = fixture_snapshot()
        route = get_route("repair.dependency")
        arguments = {
            "route": route,
            "actor": ACTOR,
            "purpose": "research_repair",
            "compartments": ("project_research",),
            "privacy_clearance": "project_private",
            "focus_entity_ids": ("ent_claim",),
            "budget_units": 10_000,
        }

        first = compile_context(snapshot, **arguments)
        second = compile_context(snapshot, **arguments)

        self.assertEqual(first.encoded, second.encoded)
        self.assertEqual(first.context_hash, second.context_hash)
        selected = {
            (ref.entity_id, ref.version) for ref in first.selected_entity_refs
        }
        self.assertIn(("ent_claim", 1), selected)
        self.assertIn(("ent_assumption", 1), selected)
        self.assertIn(("ent_verification", 1), selected)
        self.assertNotIn(("ent_independent", 1), selected)
        self.assertEqual(first.context_hash, sha256_bytes(first.encoded))

    def test_budget_omits_optional_neighbor_but_never_required_ancestor(self) -> None:
        snapshot = fixture_snapshot()
        route = get_route("repair.dependency")
        common = {
            "route": route,
            "actor": ACTOR,
            "purpose": "research_repair",
            "compartments": ("project_research",),
            "privacy_clearance": "project_private",
            "focus_entity_ids": ("ent_claim",),
        }
        full = compile_context(snapshot, budget_units=10_000, **common)
        bounded = compile_context(
            snapshot, budget_units=full.used_units - 1, **common
        )

        selected = {ref.entity_id for ref in bounded.selected_entity_refs}
        self.assertIn("ent_assumption", selected)
        self.assertIn("ent_claim", selected)
        self.assertNotIn("ent_verification", selected)
        self.assertIn("budget:neighbor:ent_verification@1", bounded.omissions)
        self.assertLessEqual(bounded.used_units, full.used_units - 1)

    def test_privacy_denial_is_recorded_for_optional_neighbor(self) -> None:
        compiled = compile_context(
            fixture_snapshot(private_neighbor=True),
            route=get_route("repair.dependency"),
            actor=ACTOR,
            purpose="research_repair",
            compartments=("project_research",),
            privacy_clearance="project_private",
            focus_entity_ids=("ent_claim",),
            budget_units=10_000,
        )
        self.assertIn(
            "privacy:neighbor:ent_verification@1", compiled.omissions
        )

    def test_optional_neighbor_closes_ancestors_before_exposing_status(self) -> None:
        public_source = make_entity(
            "ent_public_source", "Claim", privacy="public"
        )
        public_neighbor = make_entity(
            "ent_public_neighbor", "Claim", privacy="public"
        )
        secret_v1 = make_entity(
            "ent_secret_source",
            "Assumption",
            formal={"value": "old secret"},
            privacy="restricted",
        )
        secret_v2 = EntityVersion(
            **{
                **secret_v1.model_dump(mode="python"),
                "version": 2,
                "facets": FacetPayloads(formal={"value": "new secret"}),
                "created_at": "2026-07-11T00:00:01Z",
                "supersedes": EntityVersionRef(
                    entity_id=secret_v1.entity_id, version=1
                ),
            }
        )
        public_trace = RelationVersion(
            relation_id="rel_public_neighbor",
            relation_type="mentions",
            version=1,
            project_id="prj_context",
            source=EntityVersionRef(
                entity_id=public_source.entity_id, version=1
            ),
            target=EntityVersionRef(
                entity_id=public_neighbor.entity_id, version=1
            ),
            dependency_mode="trace_only",
            privacy="public",
            created_at="2026-07-11T00:00:00Z",
        )
        secret_dependency = dependency(
            "rel_secret_dependency",
            secret_v1,
            public_neighbor,
            privacy="restricted",
        )
        assert secret_dependency.upstream is not None
        stale_reason = StaleReason(
            relation_id=secret_dependency.relation_id,
            relation_version=1,
            dependency_mode="hard",
            upstream=secret_dependency.upstream,
            current_upstream_version=2,
            current_semantic_hash=object_digest(
                {
                    "payload": secret_v2.facets.formal,
                    "scope_ref": secret_v2.scope_ref,
                    "formal_validity": secret_v2.status.formal_validity,
                }
            ),
            message="Restricted upstream changed.",
            source_evidence=(
                StaleDependencyEvidence(
                    relation_id=secret_dependency.relation_id,
                    relation_version=1,
                    dependency_mode="hard",
                    upstream=secret_dependency.upstream,
                    current_upstream_version=2,
                    current_semantic_hash=object_digest(
                        {
                            "payload": secret_v2.facets.formal,
                            "scope_ref": secret_v2.scope_ref,
                            "formal_validity": secret_v2.status.formal_validity,
                        }
                    ),
                ),
            ),
        )
        snapshot = Snapshot(
            project_id="prj_context",
            head=HEAD,
            chain=(HEAD,),
            entity_versions=(
                public_source,
                public_neighbor,
                secret_v1,
                secret_v2,
            ),
            relation_versions=(public_trace, secret_dependency),
            current_entities={
                public_source.entity_id: 1,
                public_neighbor.entity_id: 1,
                secret_v1.entity_id: 2,
            },
            current_relations={
                public_trace.relation_id: 1,
                secret_dependency.relation_id: 1,
            },
            derived_status={
                public_neighbor.entity_id: EntityDerivedStatus(
                    freshness={"formal": "stale"},
                    stale_reasons={"formal": (stale_reason,)},
                )
            },
        )
        compiled = compile_context(
            snapshot,
            route=get_route("repair.dependency"),
            actor=ACTOR,
            purpose="research_repair",
            compartments=("project_research",),
            privacy_clearance="public",
            focus_entity_ids=(public_source.entity_id,),
            budget_units=10_000,
        )
        self.assertIn(
            f"privacy:neighbor:{public_neighbor.entity_id}@1", compiled.omissions
        )
        self.assertNotIn(public_neighbor.entity_id, {
            ref.entity_id for ref in compiled.selected_entity_refs
        })
        self.assertNotIn(secret_dependency.relation_id, compiled.encoded.decode("utf-8"))
        self.assertNotIn(secret_v1.entity_id, compiled.encoded.decode("utf-8"))

    def test_required_private_focus_fails_closed(self) -> None:
        with self.assertRaises(ContextAccessError):
            compile_context(
                fixture_snapshot(private_neighbor=True),
                route=get_route("repair.dependency"),
                actor=ACTOR,
                purpose="research_repair",
                compartments=("project_research",),
                privacy_clearance="project_private",
                focus_entity_ids=("ent_verification",),
                budget_units=10_000,
            )

    def test_holdout_compartment_denies_repair_even_with_explicit_grant(self) -> None:
        snapshot = fixture_snapshot()
        holdout = make_entity(
            "ent_verification",
            "Verification",
            compartments=("project_research", "confirmatory_holdout"),
        )
        entities = tuple(
            holdout if entity.entity_id == holdout.entity_id else entity
            for entity in snapshot.entity_versions
        )
        protected = Snapshot(
            **{
                **snapshot.model_dump(mode="python"),
                "entity_versions": entities,
            }
        )

        with self.assertRaises(ContextAccessError):
            compile_context(
                protected,
                route=get_route("repair.dependency"),
                actor=ACTOR,
                purpose="research_repair",
                compartments=("project_research", "confirmatory_holdout"),
                privacy_clearance="project_private",
                focus_entity_ids=("ent_verification",),
                budget_units=10_000,
            )

    def test_relevant_restricted_authority_decision_fails_closed(self) -> None:
        snapshot = fixture_snapshot()
        decision = Decision(
            decision_id="dec_private_authority",
            version=1,
            project_id=snapshot.project_id,
            decision_kind="G1_question_benchmark",
            subject_ref="ent_claim",
            question="Confirm the exact claim framing?",
            options=("confirm", "revise"),
            selected_option="confirm",
            recommendation="confirm",
            rationale="Restricted rationale must not leak into a lower-clearance route.",
            required_authority="L2",
            decider=Actor(kind="human", actor_id="human_owner"),
            decided_at="2026-07-11T00:00:00Z",
            status="confirmed",
            privacy="restricted",
        )
        protected = Snapshot(
            **{
                **snapshot.model_dump(mode="python"),
                "decisions": (decision,),
                "current_decisions": {decision.decision_id: 1},
                "effective_decisions": {
                    "G1_question_benchmark:ent_claim": EffectiveDecisionRef(
                        decision_id=decision.decision_id,
                        version=1,
                        effective_revision=HEAD,
                    )
                },
            }
        )
        with self.assertRaises(ContextAccessError):
            compile_context(
                protected,
                route=get_route("repair.dependency"),
                actor=ACTOR,
                purpose="research_repair",
                compartments=("project_research",),
                privacy_clearance="project_private",
                focus_entity_ids=("ent_claim",),
                budget_units=10_000,
            )

    def test_hidden_superseded_decision_cannot_leak_through_derived_status(self) -> None:
        snapshot = fixture_snapshot()
        hidden = Decision(
            decision_id="dec_hidden_terminal_status",
            version=2,
            project_id=snapshot.project_id,
            decision_kind="G1_question_benchmark",
            subject_ref="ent_claim",
            question="Withdraw the prior gate choice?",
            options=("confirm", "withdraw"),
            recommendation="withdraw",
            rationale="This local-only history must not leak through a status field.",
            required_authority="L2",
            decider=Actor(kind="human", actor_id="human_owner"),
            decided_at="2026-07-11T00:00:01Z",
            status="superseded",
            privacy="local_only",
            supersedes=DecisionVersionRef(
                decision_id="dec_hidden_terminal_status", version=1
            ),
        )
        protected = Snapshot(
            **{
                **snapshot.model_dump(mode="python"),
                "decisions": (hidden,),
                "current_decisions": {hidden.decision_id: 2},
                "effective_decisions": {},
                "derived_status": {
                    "ent_claim": EntityDerivedStatus(
                        human_acceptance="superseded",
                        acceptance_by_kind={
                            "G1_question_benchmark": "superseded"
                        },
                        acceptance_source_refs={
                            "G1_question_benchmark": (
                                DecisionVersionRef(
                                    decision_id=hidden.decision_id,
                                    version=hidden.version,
                                ),
                            )
                        },
                    )
                },
            }
        )
        with self.assertRaises(ContextAccessError):
            compile_context(
                protected,
                route=get_route("repair.dependency"),
                actor=ACTOR,
                purpose="research_repair",
                compartments=("project_research",),
                privacy_clearance="public",
                focus_entity_ids=("ent_claim",),
                budget_units=10_000,
            )

    def test_old_public_decision_rechecks_current_reference_privacy(self) -> None:
        subject_v1 = make_entity(
            "ent_decision_subject", "ResearchQuestion", privacy="public"
        )
        subject_v2 = EntityVersion(
            **{
                **subject_v1.model_dump(mode="python"),
                "version": 2,
                "privacy": "restricted",
                "created_at": "2026-07-11T00:00:02Z",
                "supersedes": EntityVersionRef(
                    entity_id=subject_v1.entity_id, version=1
                ),
            }
        )
        focus = make_entity("ent_public_focus", "Claim", privacy="public")
        decision = Decision(
            decision_id="dec_old_public_current_secret",
            version=1,
            project_id="prj_context",
            decision_kind="G1_question_benchmark",
            subject_ref=subject_v1.entity_id,
            question="Use this subject?",
            options=("confirm", "revise"),
            selected_option="confirm",
            recommendation="confirm",
            rationale="This Decision predates the subject's privacy strengthening.",
            affected_scopes=(focus.entity_id,),
            required_authority="L2",
            decider=Actor(kind="human", actor_id="human_owner"),
            decided_at="2026-07-11T00:00:01Z",
            status="confirmed",
            privacy="public",
        )
        snapshot = Snapshot(
            project_id="prj_context",
            head=HEAD,
            chain=(HEAD,),
            entity_versions=(subject_v1, subject_v2, focus),
            decisions=(decision,),
            current_entities={subject_v1.entity_id: 2, focus.entity_id: 1},
            current_decisions={decision.decision_id: 1},
            effective_decisions={
                '["G1_question_benchmark","ent_decision_subject",null]': (
                    EffectiveDecisionRef(
                        decision_id=decision.decision_id,
                        version=1,
                        effective_revision=HEAD,
                    )
                )
            },
        )
        with self.assertRaises(ContextAccessError):
            compile_context(
                snapshot,
                route=get_route("repair.dependency"),
                actor=ACTOR,
                purpose="research_repair",
                compartments=("project_research",),
                privacy_clearance="public",
                focus_entity_ids=(focus.entity_id,),
                budget_units=10_000,
            )

        scope_v1 = make_entity("ent_scope_history", "Scope", privacy="public")
        scope_v2 = EntityVersion(
            **{
                **scope_v1.model_dump(mode="python"),
                "version": 2,
                "privacy": "restricted",
                "created_at": "2026-07-11T00:00:03Z",
                "supersedes": EntityVersionRef(
                    entity_id=scope_v1.entity_id, version=1
                ),
            }
        )
        scoped = make_entity("ent_public_scoped", "Claim", privacy="public").model_copy(
            update={"scope_ref": scope_v1.entity_id}
        )
        scoped_snapshot = Snapshot(
            project_id="prj_context",
            head=HEAD,
            chain=(HEAD,),
            entity_versions=(scope_v1, scope_v2, scoped),
            current_entities={scope_v1.entity_id: 2, scoped.entity_id: 1},
        )
        with self.assertRaises(ContextAccessError):
            compile_context(
                scoped_snapshot,
                route=get_route("repair.dependency"),
                actor=ACTOR,
                purpose="research_repair",
                compartments=("project_research",),
                privacy_clearance="public",
                focus_entity_ids=(scoped.entity_id,),
                budget_units=10_000,
            )

    def test_relevant_restricted_blocker_fails_closed(self) -> None:
        snapshot = fixture_snapshot()
        blocker = RiskOrBlocker(
            blocker_id="blk_private",
            project_id=snapshot.project_id,
            kind="scope_conflict",
            severity="critical",
            summary="Restricted blocker content.",
            affected_refs=(EntityVersionRef(entity_id="ent_claim", version=1),),
            created_at="2026-07-11T00:00:00Z",
            privacy="restricted",
        )
        protected = Snapshot(
            **{
                **snapshot.model_dump(mode="python"),
                "blockers": (blocker,),
            }
        )
        with self.assertRaises(ContextAccessError):
            compile_context(
                protected,
                route=get_route("repair.dependency"),
                actor=ACTOR,
                purpose="research_repair",
                compartments=("project_research",),
                privacy_clearance="project_private",
                focus_entity_ids=("ent_claim",),
                budget_units=10_000,
            )

    def test_unresolved_required_dissent_ref_fails_closed(self) -> None:
        snapshot = fixture_snapshot()
        decision = Decision(
            decision_id="dec_missing_dissent",
            version=1,
            project_id=snapshot.project_id,
            decision_kind="G1_question_benchmark",
            subject_ref="ent_claim",
            question="Confirm despite dissent?",
            options=("confirm", "revise"),
            selected_option="confirm",
            recommendation="revise",
            rationale="The dissent reference must resolve before context compilation.",
            dissent_refs=("ent_missing_dissent",),
            required_authority="L2",
            decider=Actor(kind="human", actor_id="human_owner"),
            decided_at="2026-07-11T00:00:00Z",
            status="confirmed",
        )
        malformed = Snapshot(
            **{
                **snapshot.model_dump(mode="python"),
                "decisions": (decision,),
                "current_decisions": {decision.decision_id: 1},
                "effective_decisions": {
                    "G1_question_benchmark:ent_claim": EffectiveDecisionRef(
                        decision_id=decision.decision_id,
                        version=1,
                        effective_revision=HEAD,
                    )
                },
            }
        )
        with self.assertRaises(ContextCompilationError):
            compile_context(
                malformed,
                route=get_route("repair.dependency"),
                actor=ACTOR,
                purpose="research_repair",
                compartments=("project_research",),
                privacy_clearance="project_private",
                focus_entity_ids=("ent_claim",),
                budget_units=10_000,
            )


class RouteRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        root = Path(self.temporary_directory.name)
        self.layout = StoreLayout.at(root)
        self.snapshot = init_project(
            root, name="Route run contract", actor_id="human_owner"
        )

    def test_begin_writes_immutable_run_context_and_noncanonical_candidate(self) -> None:
        run = begin_run(
            self.layout,
            self.snapshot,
            route_id="frame.question_and_benchmarks",
            actor=ACTOR,
            purpose="research_framing",
            compartments=("project_research",),
            privacy_clearance="project_private",
            focus_entity_ids=(self.snapshot.project_id,),
            budget_units=10_000,
            route_run_id="run_contract",
            context_manifest_id="ctx_contract",
            created_at="2026-07-11T00:00:01Z",
        )

        self.assertEqual(run.status, "running")
        self.assertEqual(HeadStore(self.layout).read(), self.snapshot.head)
        self.assertEqual(read_run(self.layout, "run_contract"), run)
        manifest = read_context(self.layout, "run_contract")
        payload = read_compiled_context(self.layout, "run_contract")
        self.assertEqual(manifest.context_hash, run.context_hash)
        self.assertEqual(payload["source_head"], self.snapshot.head)
        self.assertTrue(run_path(self.layout, "run_contract").is_file())
        self.assertTrue(context_path(self.layout, "run_contract").is_file())
        self.assertTrue(
            compiled_context_path(self.layout, "run_contract").is_file()
        )
        candidate = load_json_bytes(
            candidate_path(self.layout, "run_contract").read_bytes()
        )
        self.assertIn("GENERATED", candidate["markers"])
        self.assertIn("NONCANONICAL", candidate["markers"])
        self.assertIsNone(candidate["candidate_transaction"])

    def test_required_budget_failure_creates_no_running_run_or_staging(self) -> None:
        with self.assertRaises(ContextBudgetError):
            begin_run(
                self.layout,
                self.snapshot,
                route_id="frame.question_and_benchmarks",
                actor=ACTOR,
                purpose="research_framing",
                compartments=("project_research",),
                privacy_clearance="project_private",
                focus_entity_ids=(self.snapshot.project_id,),
                budget_units=1,
                route_run_id="run_too_small",
                context_manifest_id="ctx_too_small",
                created_at="2026-07-11T00:00:01Z",
            )

        self.assertFalse(run_path(self.layout, "run_too_small").exists())
        self.assertFalse(context_path(self.layout, "run_too_small").exists())
        self.assertFalse(candidate_path(self.layout, "run_too_small").exists())
        self.assertEqual(HeadStore(self.layout).read(), self.snapshot.head)

    def test_begin_rejects_same_head_snapshot_with_forged_projection(self) -> None:
        forged = Snapshot(
            **{
                **self.snapshot.model_dump(mode="python"),
                "current_entities": {},
            }
        )
        with self.assertRaises(RunBaseMismatch):
            begin_run(
                self.layout,
                forged,
                route_id="frame.question_and_benchmarks",
                actor=ACTOR,
                purpose="research_framing",
                compartments=("project_research",),
                budget_units=10_000,
            )

    def test_run_and_manifest_require_canonical_raw_json(self) -> None:
        run = begin_run(
            self.layout,
            self.snapshot,
            route_id="frame.question_and_benchmarks",
            actor=ACTOR,
            purpose="research_framing",
            compartments=("project_research",),
            budget_units=10_000,
            route_run_id="run_canonical_bytes",
            context_manifest_id="ctx_canonical_bytes",
        )
        path = run_path(self.layout, run.route_run_id)
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(IntegrityError):
            read_run(self.layout, run.route_run_id)

    def test_file_bound_run_ids_reject_windows_aliases_and_case_collisions(self) -> None:
        for unsafe in ("CON", "run:escape", "Run_Case", "run.", "run/escape"):
            with self.subTest(route_run_id=unsafe):
                with self.assertRaises(RunError):
                    run_path(self.layout, unsafe)


if __name__ == "__main__":  # pragma: no cover - direct test invocation
    unittest.main()
