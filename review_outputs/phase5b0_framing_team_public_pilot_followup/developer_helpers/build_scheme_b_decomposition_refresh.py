"""Deterministically refresh the G1 decomposition package after Scheme B."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from econ_theorist.models import (
    Actor,
    ChangedFacets,
    CreateEntityOp,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    SupersedeEntityOp,
    SupersedeRelationOp,
    Transaction,
)
from econ_theorist.runtime import StoreLayout
from econ_theorist.runtime.freshness import changed_semantic_facets
from econ_theorist.runtime.replay import replay
from econ_theorist.theory import (
    GateDossier,
    PrimitiveGraph,
    pack_theory_payload,
    parse_theory_entity,
)


PG_ID = "pg_score_disclosure_appeal_selection"
GATE_ID = "gate_g1_score_disclosure_appeal_selection"
REFRESHED_GATE_ID = "gate_g1_score_disclosure_appeal_selection_scheme_b"
DECOMPOSES_ID = "rel_rq_decomposes_pg_score_disclosure"
GOVERNS_ID = "rel_gate_governs_rq_score_disclosure"


def _exact_entity(snapshot, entity_id: str) -> EntityVersion:
    version = snapshot.current_entities[entity_id]
    return next(
        entity
        for entity in snapshot.entity_versions
        if entity.entity_id == entity_id and entity.version == version
    )


def _exact_relation(snapshot, relation_id: str) -> RelationVersion:
    version = snapshot.current_relations[relation_id]
    return next(
        relation
        for relation in snapshot.relation_versions
        if relation.relation_id == relation_id and relation.version == version
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("response", type=Path)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    response = json.loads(args.response.read_text(encoding="utf-8"))
    packet = response["work_packet"]
    contract = response["candidate_authoring_contract"]
    if (
        response["outcome"] != "ready"
        or packet["route_id"] != "decompose.primitives"
        or packet["focus_refs"]
        != [
            {"entity_id": "bmk_decision_only_disclosure_delta", "version": 1},
            {"entity_id": "rq_score_disclosure_appeal_selection", "version": 1},
        ]
    ):
        raise ValueError("response is not the exact post-Scheme-B decomposition")

    snapshot = replay(StoreLayout.at(args.project_root))
    bindings = contract["transaction_bindings"]
    if snapshot.head != bindings["base_revision"]:
        raise ValueError("canonical head changed after WorkPacket delivery")
    previous_pg = _exact_entity(snapshot, PG_ID)
    previous_gate = _exact_entity(snapshot, GATE_ID)
    previous_decomposes = _exact_relation(snapshot, DECOMPOSES_ID)
    previous_governs = _exact_relation(snapshot, GOVERNS_ID)
    if (
        previous_pg.version != 2
        or previous_gate.version != 1
        or previous_decomposes.version != 1
        or previous_governs.version != 1
    ):
        raise ValueError("unexpected decomposition lineage before refresh")

    pg_payload = parse_theory_entity(previous_pg)
    gate_payload = parse_theory_entity(previous_gate)
    if not isinstance(pg_payload, PrimitiveGraph) or not isinstance(
        gate_payload, GateDossier
    ):
        raise TypeError("current decomposition objects have unexpected types")
    final_rule = next(
        node for node in pg_payload.nodes if node.node_id == "final_review_rule"
    )
    if (
        "phi(s,r)=psi(r)" not in final_rule.economic_meaning
        or "phi(s,r)=r" not in final_rule.economic_meaning
        or final_rule.status != "primitive"
    ):
        raise ValueError("current PrimitiveGraph does not preserve Scheme B")

    refreshed_nodes = tuple(
        node.model_copy(
            update={
                "label": "Score-blind strictly review-monotone final mapping"
            }
        )
        if node.node_id == "final_review_rule"
        else node
        for node in pg_payload.nodes
    )
    refreshed_pg_payload = pg_payload.model_copy(
        update={"nodes": refreshed_nodes}
    )
    pg2_ref = EntityVersionRef(entity_id=PG_ID, version=2)
    pg3_ref = EntityVersionRef(entity_id=PG_ID, version=3)
    refreshed_pg = previous_pg.model_copy(
        update={
            "version": 3,
            "summary": (
                previous_pg.summary
                + " This version re-anchors that unchanged Scheme-B specification "
                "in the refreshed pre-G1 decomposition package."
            ),
            "facets": pack_theory_payload(refreshed_pg_payload),
            "created_at": bindings["created_at"],
            "supersedes": pg2_ref,
        }
    )

    def update_ref(reference: EntityVersionRef) -> EntityVersionRef:
        return pg3_ref if reference.entity_id == PG_ID else reference

    requirements = []
    for requirement in gate_payload.requirements:
        update = {
            "evidence_refs": tuple(
                update_ref(reference)
                for reference in requirement.evidence_refs
            )
        }
        if requirement.requirement_id == "g1_final_rule_gap":
            update.update(
                {
                    "description": (
                        "The researcher selected the score-blind class "
                        "phi(s,r)=psi(r), psi(1)>psi(0), with phi(s,r)=r as "
                        "the deterministic baseline; PrimitiveGraph version 3 "
                        "states its implied acceptance probability and appeal payoff."
                    ),
                    "recorded_condition": "evidence_supplied",
                }
            )
        requirements.append(requirement.model_copy(update=update))
    refreshed_gate_payload = gate_payload.model_copy(
        update={
            "ordered_object_refs": tuple(
                update_ref(reference)
                for reference in gate_payload.ordered_object_refs
            ),
            "requirements": tuple(requirements),
            "proposed_action": "revise",
            "rationale": (
                "Scheme B resolves the final-review mapping gap while preserving "
                "the exact decision_only benchmark and all no-sign, no-welfare, "
                "and no-capacity boundaries.  G1 remains unconfirmed and this "
                "dossier still recommends revision because the ResearchQuestion's "
                "strict frontier terminology remains a separate named repair and "
                "the refreshed frame must pass a new economics audit."
            ),
            "prepared_at": bindings["created_at"],
        }
    )
    refreshed_gate_ref = EntityVersionRef(
        entity_id=REFRESHED_GATE_ID, version=1
    )
    refreshed_gate = previous_gate.model_copy(
        update={
            "entity_id": REFRESHED_GATE_ID,
            "version": 1,
            "summary": (
                "An unconfirmed refreshed G1 dossier that records Scheme B as "
                "resolved, preserves the exact benchmark, and retains the separate "
                "frontier-terminology and fresh-audit requirements."
            ),
            "facets": pack_theory_payload(refreshed_gate_payload),
            "created_at": bindings["created_at"],
            "supersedes": None,
        }
    )

    decomposes2 = previous_decomposes.model_copy(
        update={
            "version": 2,
            "target": pg3_ref,
            "created_at": bindings["created_at"],
            "supersedes": RelationVersionRef(
                relation_id=DECOMPOSES_ID, version=1
            ),
        }
    )
    governs2 = previous_governs.model_copy(
        update={
            "version": 2,
            "source": refreshed_gate_ref,
            "created_at": bindings["created_at"],
            "supersedes": RelationVersionRef(
                relation_id=GOVERNS_ID, version=1
            ),
        }
    )
    decomposes2_ref = RelationVersionRef(
        relation_id=DECOMPOSES_ID, version=2
    )
    governs2_ref = RelationVersionRef(relation_id=GOVERNS_ID, version=2)
    transaction = Transaction(
        transaction_id="tx_refresh_scheme_b_g1_decomposition",
        origin=bindings["origin"],
        project_id=bindings["project_id"],
        base_revision=bindings["base_revision"],
        route_run_id=bindings["route_run_id"],
        route_id=bindings["route_id"],
        actor=Actor.model_validate_json(
            json.dumps(bindings["actor"]), strict=True
        ),
        intent=(
            "Carry Scheme B forward unchanged and refresh only its exact "
            "pre-G1 decomposition dossier and trace relations."
        ),
        changed_facets=(
            ChangedFacets(
                entity_id=PG_ID,
                previous_version=2,
                new_version=3,
                facets=changed_semantic_facets(previous_pg, refreshed_pg),
            ),
        ),
        operations=(
            SupersedeEntityOp(previous=pg2_ref, entity=refreshed_pg),
            CreateEntityOp(entity=refreshed_gate),
            SupersedeRelationOp(
                previous=RelationVersionRef(
                    relation_id=DECOMPOSES_ID, version=1
                ),
                relation=decomposes2,
            ),
            SupersedeRelationOp(
                previous=RelationVersionRef(
                    relation_id=GOVERNS_ID, version=1
                ),
                relation=governs2,
            ),
            RecordRouteOutcomeOp(
                outcome=RouteOutcome(
                    route_run_id=bindings["route_run_id"],
                    route_id=bindings["route_id"],
                    outcome="completed_with_candidate",
                    rationale=(
                        "The refreshed package preserves Scheme B, marks only the "
                        "final-rule requirement resolved, retains the separate RQ "
                        "terminology repair, and does not confirm G1."
                    ),
                    candidate_refs=(
                        pg3_ref,
                        refreshed_gate_ref,
                        decomposes2_ref,
                        governs2_ref,
                    ),
                    privacy=bindings["privacy"],
                    access_compartments=tuple(bindings["access_compartments"]),
                )
            ),
        ),
        evidence_refs=tuple(
            EntityVersionRef.model_validate_json(
                json.dumps(reference), strict=True
            )
            for reference in bindings["required_entity_evidence_refs"]
        ),
        privacy=bindings["privacy"],
        access_compartments=tuple(bindings["access_compartments"]),
        created_at=bindings["created_at"],
        parent_transaction_hash=bindings["parent_transaction_hash"],
        route_run_hash=bindings["route_run_hash"],
        context_manifest_hash=bindings["context_manifest_hash"],
        compiled_context_hash=bindings["compiled_context_hash"],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(transaction.model_dump(mode="json"), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
