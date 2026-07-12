"""Phase 3 selective-freshness and authority-slicing regression tests."""

from __future__ import annotations

import unittest

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.models import (
    Actor,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    FacetPayloads,
    RelationVersion,
    ScientificStatus,
    SemanticFacetRef,
)
from econ_theorist.runtime.freshness import (
    derive_entity_statuses,
    facet_semantic_hash,
)


PROJECT = "project.phase3.selective-invalidation"
HUMAN = Actor(kind="human", actor_id="human.phase3.owner")


def _entity(
    entity_id: str,
    *,
    version: int = 1,
    formal: object | None = None,
    authority: object | None = None,
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type="Phase3FreshnessFixture",
        version=version,
        project_id=PROJECT,
        title=f"Fixture {entity_id}",
        summary="A minimal semantic-freshness fixture.",
        status=ScientificStatus(lifecycle="proposed"),
        facets=FacetPayloads(
            formal={} if formal is None else formal,
            authority={} if authority is None else authority,
        ),
        created_at=f"2026-07-12T00:00:{version:02d}Z",
        supersedes=(
            EntityVersionRef(entity_id=entity_id, version=version - 1)
            if version > 1
            else None
        ),
    )


def _relation(
    relation_id: str,
    source: EntityVersion,
    target: EntityVersion,
    *,
    source_facet: str = "formal",
    source_path: str | None = None,
    target_facet: str = "formal",
) -> RelationVersion:
    return RelationVersion(
        relation_id=relation_id,
        relation_type="depends_on",
        version=1,
        project_id=PROJECT,
        source=EntityVersionRef(entity_id=source.entity_id, version=source.version),
        target=EntityVersionRef(entity_id=target.entity_id, version=target.version),
        dependency_mode="hard",
        upstream=SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet=source_facet,  # type: ignore[arg-type]
            field_path=source_path,
            semantic_hash=facet_semantic_hash(
                source, source_facet, source_path  # type: ignore[arg-type]
            ),
        ),
        downstream=FacetPathRef(
            entity_id=target.entity_id,
            version=target.version,
            facet=target_facet,  # type: ignore[arg-type]
        ),
        created_at="2026-07-12T00:01:00Z",
    )


def _statuses(
    entities: tuple[EntityVersion, ...],
    relations: tuple[RelationVersion, ...],
    *,
    current_entities: dict[str, int],
    decisions: tuple[Decision, ...] = (),
    effective_decisions: dict[str, DecisionVersionRef] | None = None,
):
    return derive_entity_statuses(
        entity_versions=entities,
        relation_versions=relations,
        decisions=decisions,
        current_entities=current_entities,
        current_relations={item.relation_id: item.version for item in relations},
        effective_decisions=effective_decisions or {},
    )


class Phase3SelectiveInvalidationTests(unittest.TestCase):
    def test_one_claim_change_stales_only_its_manuscript_review_and_closure_chain(self) -> None:
        claim_a_v1 = _entity("claim.a", formal={"statement": "A"})
        claim_a_v2 = _entity("claim.a", version=2, formal={"statement": "A revised"})
        unit_a = _entity("unit.a", formal={"span": "A"})
        review_a = _entity("review.a", formal={"assessment": "passed"})
        closure_a = _entity("closure.a", formal={"status": "ready"})

        claim_b = _entity("claim.b", formal={"statement": "B"})
        unit_b = _entity("unit.b", formal={"span": "B"})
        review_b = _entity("review.b", formal={"assessment": "passed"})
        closure_b = _entity("closure.b", formal={"status": "ready"})

        relations = (
            _relation("relation.a.claim-unit", claim_a_v1, unit_a),
            _relation("relation.a.unit-review", unit_a, review_a),
            _relation("relation.a.review-closure", review_a, closure_a),
            _relation("relation.b.claim-unit", claim_b, unit_b),
            _relation("relation.b.unit-review", unit_b, review_b),
            _relation("relation.b.review-closure", review_b, closure_b),
        )
        entities = (
            claim_a_v1,
            claim_a_v2,
            unit_a,
            review_a,
            closure_a,
            claim_b,
            unit_b,
            review_b,
            closure_b,
        )
        current = {item.entity_id: item.version for item in entities}
        statuses = _statuses(entities, relations, current_entities=current)

        for entity_id in ("unit.a", "review.a", "closure.a"):
            self.assertEqual(statuses[entity_id].freshness["formal"], "stale")
        for entity_id in ("claim.b", "unit.b", "review.b", "closure.b"):
            self.assertEqual(statuses[entity_id].freshness["formal"], "fresh")

    def test_profile_decision_does_not_stale_payload_bound_assurance_but_payload_change_does(self) -> None:
        package_v1 = _entity(
            "package.phase3",
            authority={"payload": {"claim_graph_ref": "claims@1"}},
        )
        assurance = _entity("assurance.phase3", formal={"status": "passed"})
        relation = _relation(
            "relation.package-payload-assurance",
            package_v1,
            assurance,
            source_facet="authority",
            source_path="/payload",
        )
        audience = Decision(
            decision_id="decision.phase3.audience",
            version=1,
            project_id=PROJECT,
            decision_kind="audience",
            subject_ref=package_v1.entity_id,
            scope_ref="question.phase3",
            question="Write first for general economic theorists?",
            options=("general_economic_theorists", "field_specialists"),
            selected_option="general_economic_theorists",
            recommendation="Use the general-theorist reader burden.",
            rationale="The human owner fixes the target audience before prose generation.",
            evidence_refs=(package_v1.entity_id,),
            unresolved_risks=("This choice does not certify publication quality.",),
            required_authority="L2",
            decider=HUMAN,
            decided_at="2026-07-12T00:02:00Z",
            status="confirmed",
        )
        decision_ref = DecisionVersionRef(
            decision_id=audience.decision_id, version=audience.version
        )
        statuses = _statuses(
            (package_v1, assurance),
            (relation,),
            current_entities={package_v1.entity_id: 1, assurance.entity_id: 1},
            decisions=(audience,),
            effective_decisions={audience.decision_id: decision_ref},
        )
        self.assertEqual(statuses[assurance.entity_id].freshness["formal"], "fresh")

        package_v2 = _entity(
            package_v1.entity_id,
            version=2,
            authority={"payload": {"claim_graph_ref": "claims@2"}},
        )
        changed = _statuses(
            (package_v1, package_v2, assurance),
            (relation,),
            current_entities={package_v2.entity_id: 2, assurance.entity_id: 1},
            decisions=(audience,),
            effective_decisions={audience.decision_id: decision_ref},
        )
        self.assertEqual(changed[assurance.entity_id].freshness["formal"], "stale")


if __name__ == "__main__":
    unittest.main()
