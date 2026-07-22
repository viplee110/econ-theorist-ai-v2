"""Build the exact Scheme-B PrimitiveGraph repair from one delivered WorkPacket."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from econ_theorist.models import (
    Actor,
    ChangedFacets,
    EntityVersion,
    EntityVersionRef,
    RecordRouteOutcomeOp,
    RouteOutcome,
    SupersedeEntityOp,
    Transaction,
)
from econ_theorist.runtime.freshness import changed_semantic_facets
from econ_theorist.theory import PrimitiveGraph, pack_theory_payload, parse_theory_entity


TARGET_ID = "pg_score_disclosure_appeal_selection"
AUDIT_ID = "fqb_score_disclosure_audit_0c7f1a94"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("response", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    response = json.loads(args.response.read_text(encoding="utf-8"))
    packet = response["work_packet"]
    contract = response["candidate_authoring_contract"]
    if (
        response["outcome"] != "ready"
        or packet["route_id"] != "repair.dependency"
        or packet["focus_refs"]
        != [
            {"entity_id": AUDIT_ID, "version": 1},
            {"entity_id": TARGET_ID, "version": 1},
        ]
        or "φ(s,r)=ψ(r)" not in packet["run_input"]["requested_scope"]
        or "φ(s,r)=r" not in packet["run_input"]["framing_intent"]
    ):
        raise ValueError("response is not the exact Scheme-B repair WorkPacket")

    entities = packet["compiled_context"]["entities"]
    raw = next(
        item
        for item in entities
        if item["entity_id"] == TARGET_ID and item["version"] == 1
    )
    previous = EntityVersion.model_validate_json(
        json.dumps(raw, ensure_ascii=False), strict=True
    )
    payload = parse_theory_entity(previous)
    if not isinstance(payload, PrimitiveGraph):
        raise TypeError("repair target is not a PrimitiveGraph")

    nodes = []
    for node in payload.nodes:
        if node.node_id == "fresh_review_signal":
            node = node.model_copy(
                update={
                    "economic_meaning": (
                        "An appeal produces a fresh binary review signal r, coded "
                        "r=1 for favorable and r=0 for unfavorable evidence.  Write "
                        "rho_q=Pr(r=1|qualification=q), with 0<rho_0<rho_1<1 in "
                        "the maintained informative full-support baseline."
                    ),
                    "primitive_sufficient_conditions": (
                        "The review technology and the favorable/unfavorable coding are fixed across regimes.",
                        "The maintained baseline has 0 < rho_0 < rho_1 < 1, and the review signal is realized only after the appeal choice.",
                    ),
                }
            )
        elif node.node_id == "final_review_rule":
            node = node.model_copy(
                update={
                    "economic_meaning": (
                        "The common final rule is score-blind and depends only on "
                        "the fresh review signal: phi(s,r)=psi(r), where "
                        "0<=psi(0)<psi(1)<=1.  The minimal deterministic benchmark "
                        "sets psi(0)=0 and psi(1)=1, hence phi(s,r)=r: final "
                        "acceptance occurs exactly after a favorable fresh review."
                    ),
                    "primitive_sufficient_conditions": (
                        "Score blindness requires phi(low,r)=phi(middle,r)=psi(r) for each review realization r.",
                        "Strict review monotonicity requires psi(1)>psi(0); the same fixed psi applies under decision_only and score_disclosure.",
                        "The hand-solvable baseline is deterministic, psi(0)=0 and psi(1)=1, and the rule never infers the private applicant signal from the appeal act.",
                    ),
                    "status": "primitive",
                }
            )
        elif node.node_id == "applicant_posterior":
            node = node.model_copy(
                update={
                    "economic_meaning": (
                        "Let p be the applicant's posterior qualification probability "
                        "after the regime-specific rejection message and private signal. "
                        "Under conditional independence and the score-blind rule, the "
                        "anticipated acceptance probability is A_psi(p)=psi(0)+"
                        "[psi(1)-psi(0)]*[p*rho_1+(1-p)*rho_0].  In the minimal "
                        "phi(s,r)=r benchmark this reduces to p*rho_1+(1-p)*rho_0."
                    ),
                    "primitive_sufficient_conditions": (
                        "Applicants know the maintained prior, signal technologies, rho_0, rho_1, and the common rule psi and update Bayesianly.",
                        "Because rho_1>rho_0 and psi(1)>psi(0), A_psi(p) is strictly increasing in p; disclosure changes it only through the refined score message.",
                    ),
                }
            )
        elif node.node_id == "appeal_choice":
            node = node.model_copy(
                update={
                    "economic_meaning": (
                        "With acceptance value v>0, appeal cost c>0, and the "
                        "no-appeal continuation payoff normalized to zero, a rejected "
                        "applicant appeals exactly when v*A_psi(p)-c>=0.  Indifference "
                        "is resolved in favor of appeal."
                    ),
                    "primitive_sufficient_conditions": (
                        "Non-appellants remain finally rejected, so their continuation payoff is zero under the maintained normalization.",
                        "Disclosure changes the appeal set only when the disclosed-cell and pooled-rejection values of v*A_psi(p)-c lie on different sides of zero.",
                    ),
                }
            )
        nodes.append(node)

    edges = []
    for edge in payload.edges:
        if edge.edge_id == "review_signal_to_final_rule":
            edge = edge.model_copy(
                update={
                    "economic_meaning": (
                        "The favorable review indicator r enters the score-blind "
                        "mapping phi(s,r)=psi(r); the minimal benchmark applies phi=r."
                    )
                }
            )
        elif edge.edge_id == "final_rule_to_appeal_choice":
            edge = edge.model_copy(
                update={
                    "economic_meaning": (
                        "The fixed pair psi(0), psi(1) converts the posterior-implied "
                        "review distribution into A_psi(p), which enters the appeal payoff."
                    )
                }
            )
        elif edge.edge_id == "posterior_to_appeal_choice":
            edge = edge.model_copy(
                update={
                    "economic_meaning": (
                        "The posterior p determines A_psi(p), and the applicant appeals "
                        "if and only if v*A_psi(p)-c>=0."
                    )
                }
            )
        edges.append(edge)

    revised_payload = payload.model_copy(
        update={"nodes": tuple(nodes), "edges": tuple(edges)}
    )
    bindings = contract["transaction_bindings"]
    current_ref = EntityVersionRef(entity_id=TARGET_ID, version=1)
    revised = previous.model_copy(
        update={
            "version": 2,
            "summary": (
                "A benchmark-bound decomposition in which only the rejected "
                "applicant's information partition changes and the common final "
                "review mapping is the score-blind, strictly review-monotone class "
                "phi(s,r)=psi(r), with phi(s,r)=r as its deterministic baseline."
            ),
            "facets": pack_theory_payload(revised_payload),
            "created_at": bindings["created_at"],
            "supersedes": current_ref,
        }
    )
    revised_ref = EntityVersionRef(entity_id=TARGET_ID, version=2)
    transaction = Transaction(
        transaction_id="tx_scheme_b_final_review_rule_repair",
        origin=bindings["origin"],
        project_id=bindings["project_id"],
        base_revision=bindings["base_revision"],
        route_run_id=bindings["route_run_id"],
        route_id=bindings["route_id"],
        actor=Actor.model_validate_json(
            json.dumps(bindings["actor"], ensure_ascii=False), strict=True
        ),
        intent=(
            "Implement the researcher's Scheme-B final-review rule choice in "
            "the exact named PrimitiveGraph and leave the separate RQ repair open."
        ),
        changed_facets=(
            ChangedFacets(
                entity_id=TARGET_ID,
                previous_version=1,
                new_version=2,
                facets=changed_semantic_facets(previous, revised),
            ),
        ),
        operations=(
            SupersedeEntityOp(previous=current_ref, entity=revised),
            RecordRouteOutcomeOp(
                outcome=RouteOutcome(
                    route_run_id=bindings["route_run_id"],
                    route_id=bindings["route_id"],
                    outcome="completed_with_candidate",
                    rationale=(
                        "The exact PrimitiveGraph now fixes the score-blind, "
                        "strictly review-monotone rule class and phi=r baseline. "
                        "No audit, theorem, G1 decision, or RQ terminology repair "
                        "is claimed by this route."
                    ),
                    candidate_refs=(revised_ref,),
                    privacy=bindings["privacy"],
                    access_compartments=tuple(bindings["access_compartments"]),
                )
            ),
        ),
        evidence_refs=tuple(
            EntityVersionRef.model_validate_json(
                json.dumps(item, ensure_ascii=False), strict=True
            )
            for item in bindings["required_entity_evidence_refs"]
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
