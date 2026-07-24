"""Semantic validators for the Phase 2 positive-theory kernel.

The models in :mod:`econ_theorist.theory` validate canonical shape.  This
module validates facts that can only be checked against an exact projection:
reference targets, proof/verification agreement, gate order, absorption, and
the output contract of one v2 route transaction.  None of these checks awards
scientific merit; they only reject internally inconsistent research records.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from pydantic import BaseModel

from . import theory as t
from .codec import canonical_json_bytes, sha256_digest
from .models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    BlockerRef,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    RecordDecisionOp,
    RecordBlockerOp,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    RelationVersion,
    RelationVersionRef,
    RouteSpecV2,
    Snapshot,
    SupersedeDecisionOp,
    SupersedeEntityOp,
    SupersedeRelationOp,
    Transaction,
)


class TheoryValidationError(ValueError):
    """A canonical Phase 2 object is scientifically inconsistent."""


@dataclass(frozen=True)
class TheoryReadinessReport:
    """Small derived report; it is deliberately not canonical authority."""

    parsed_entity_count: int
    discharged_obligation_count: int
    confirmed_gate_kinds: tuple[str, ...]
    production_blocked_package_refs: tuple[EntityVersionRef, ...]


@dataclass(frozen=True)
class TheoryRouteEntryReport:
    """Derived entry evidence shared by begin-time and commit-time checks."""

    research_question_ref: EntityVersionRef | None
    input_entity_refs: tuple[EntityVersionRef, ...]
    gate_decision_refs: tuple[DecisionVersionRef, ...]


_GATE_ORDER = (
    "G1_question_benchmark",
    "G2_mechanism",
    "G3_formal_base",
    "G4_result_investment",
    "G5_argument_validation",
)
_GATE_RANK = {kind: index for index, kind in enumerate(_GATE_ORDER)}
_NUMERICAL_ONLY_METHODS = frozenset({"finite_example", "enumeration", "simulation"})
_SIGNATURE_DIMENSIONS = frozenset(
    {
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
    }
)
_DOSSIER_ROUTE_GATE = {
    "decompose.primitives": "G1_question_benchmark",
    "promote.mechanism": "G2_mechanism",
    "promote.formal_base": "G3_formal_base",
    "curate.result_portfolio": "G4_result_investment",
    "validate.argument_package": "G5_argument_validation",
}


def _entity_key(reference: EntityVersionRef | EntityVersion) -> tuple[str, int]:
    return (reference.entity_id, reference.version)


def _artifact_key(
    reference: ArtifactDependencyRef | ArtifactRegistration,
) -> tuple[str, int]:
    return (reference.artifact_id, reference.version)


def _decision_key(reference: DecisionVersionRef | Decision) -> tuple[str, int]:
    return (reference.decision_id, reference.version)


def _relation_key(reference: RelationVersionRef | object) -> tuple[str, int]:
    return (reference.relation_id, reference.version)  # type: ignore[attr-defined]


def validate_theory_entity(
    entity: EntityVersion, previous: EntityVersion | None = None
) -> t.TheoryPayload:
    """Parse one registered entity and enforce immutable update semantics."""

    try:
        payload = t.parse_theory_entity(entity)
    except (TypeError, ValueError) as exc:
        raise TheoryValidationError(
            f"invalid {entity.entity_type} entity {entity.entity_id}@{entity.version}: {exc}"
        ) from exc

    if isinstance(payload, t.GateDossier):
        if entity.version != 1 or entity.supersedes is not None or previous is not None:
            raise TheoryValidationError("GateDossier is immutable and must remain at version 1")
    if isinstance(
        payload,
        (
            t.PreResultBrief,
            t.BlindCaseManifest,
            t.TransformedVariantManifest,
            t.VAPComparisonRecord,
        ),
    ):
        if entity.version != 1 or entity.supersedes is not None or previous is not None:
            raise TheoryValidationError(
                f"{type(payload).__name__} is immutable and must remain at version 1"
            )

    if previous is not None:
        if previous.entity_id != entity.entity_id:
            raise TheoryValidationError("typed theory update changes entity_id")
        if previous.project_id != entity.project_id:
            raise TheoryValidationError("typed theory update changes project_id")
        if previous.entity_type != entity.entity_type:
            raise TheoryValidationError("typed theory update changes entity_type")
        if entity.version != previous.version + 1 or entity.supersedes != EntityVersionRef(
            entity_id=previous.entity_id, version=previous.version
        ):
            raise TheoryValidationError("typed theory update is not the exact next version")
        try:
            old_payload = t.parse_theory_entity(previous)
            t.validate_theory_payload_update(old_payload, payload)
        except (TypeError, ValueError) as exc:
            raise TheoryValidationError(str(exc)) from exc
    return payload


def _walk_exact_refs(value: object) -> Iterable[object]:
    """Yield every exact entity/artifact/decision ref nested in a payload."""

    if isinstance(value, (EntityVersionRef, ArtifactDependencyRef, DecisionVersionRef)):
        yield value
        return
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from _walk_exact_refs(getattr(value, field_name))
        return
    if isinstance(value, Mapping):
        for nested in value.values():
            yield from _walk_exact_refs(nested)
        return
    if isinstance(value, (tuple, list)):
        for nested in value:
            yield from _walk_exact_refs(nested)


def _expected_entity_refs(
    payload: t.TheoryPayload,
) -> Iterable[tuple[EntityVersionRef, tuple[str, ...], str]]:
    """Describe typed edges whose target kind is part of their meaning."""

    def one(ref: EntityVersionRef | None, expected: str | tuple[str, ...], label: str):
        if ref is not None:
            yield (ref, (expected,) if isinstance(expected, str) else expected, label)

    if isinstance(payload, t.BenchmarkSet):
        yield from one(payload.question_ref, "ResearchQuestion", "question_ref")
    elif isinstance(payload, t.PrimitiveGraph):
        yield from one(payload.question_ref, "ResearchQuestion", "question_ref")
        yield from one(payload.benchmark_set_ref, "BenchmarkSet", "benchmark_set_ref")
    elif isinstance(payload, t.MechanismHypothesis):
        yield from one(payload.question_ref, "ResearchQuestion", "question_ref")
        yield from one(payload.primitive_graph_ref, "PrimitiveGraph", "primitive_graph_ref")
    elif isinstance(payload, t.MechanismTournament):
        yield from one(payload.question_ref, "ResearchQuestion", "question_ref")
        for ref in payload.hypothesis_refs:
            yield from one(ref, "MechanismHypothesis", "hypothesis_refs")
    elif isinstance(payload, t.PredictionRegister):
        yield from one(payload.question_ref, "ResearchQuestion", "question_ref")
        yield from one(payload.mechanism_tournament_ref, "MechanismTournament", "mechanism_tournament_ref")
        for prediction in payload.original_predictions:
            yield from one(prediction.hypothesis_ref, "MechanismHypothesis", "prediction.hypothesis_ref")
    elif isinstance(payload, t.ExampleSuite):
        yield from one(payload.selected_mechanism_ref, "MechanismHypothesis", "selected_mechanism_ref")
        yield from one(
            payload.frozen_prediction_register_ref,
            "PredictionRegister",
            "frozen_prediction_register_ref",
        )
    elif isinstance(payload, t.EconomicArgumentGraph):
        yield from one(payload.selected_mechanism_ref, "MechanismHypothesis", "selected_mechanism_ref")
        yield from one(payload.primitive_graph_ref, "PrimitiveGraph", "primitive_graph_ref")
        yield from one(payload.prediction_register_ref, "PredictionRegister", "prediction_register_ref")
        yield from one(payload.example_suite_ref, "ExampleSuite", "example_suite_ref")
    elif isinstance(payload, t.ImplementationTournament):
        yield from one(payload.selected_mechanism_ref, "MechanismHypothesis", "selected_mechanism_ref")
        yield from one(payload.economic_argument_graph_ref, "EconomicArgumentGraph", "economic_argument_graph_ref")
        for ref in payload.candidate_model_refs:
            yield from one(ref, "FormalModel", "candidate_model_refs")
    elif isinstance(payload, t.FormalModel):
        yield from one(payload.question_ref, "ResearchQuestion", "question_ref")
        yield from one(payload.selected_mechanism_ref, "MechanismHypothesis", "selected_mechanism_ref")
        yield from one(payload.primitive_graph_ref, "PrimitiveGraph", "primitive_graph_ref")
    elif isinstance(payload, t.FormalizationMap):
        yield from one(payload.economic_argument_graph_ref, "EconomicArgumentGraph", "economic_argument_graph_ref")
        yield from one(payload.formal_model_ref, "FormalModel", "formal_model_ref")
    elif isinstance(payload, t.AssumptionMap):
        yield from one(payload.formal_model_ref, "FormalModel", "formal_model_ref")
        yield from one(payload.formalization_map_ref, "FormalizationMap", "formalization_map_ref")
    elif isinstance(payload, t.ProofObligation):
        yield from one(payload.claim_graph_ref, "ClaimGraph", "claim_graph_ref")
    elif isinstance(payload, t.VerificationRecord):
        yield from one(payload.obligation_ref, "ProofObligation", "obligation_ref")
        yield from one(payload.claim_graph_ref, "ClaimGraph", "claim_graph_ref")
        yield from one(payload.formal_model_ref, "FormalModel", "formal_model_ref")
        yield from one(payload.assumption_map_ref, "AssumptionMap", "assumption_map_ref")
    elif isinstance(payload, t.ClaimGraph):
        yield from one(payload.formal_model_ref, "FormalModel", "formal_model_ref")
        yield from one(payload.formalization_map_ref, "FormalizationMap", "formalization_map_ref")
        yield from one(payload.assumption_map_ref, "AssumptionMap", "assumption_map_ref")
        for claim in payload.claims:
            yield from one(claim.mechanism_ref, "MechanismHypothesis", "claim.mechanism_ref")
            for ref in claim.proof_obligation_refs:
                yield from one(ref, "ProofObligation", "claim.proof_obligation_refs")
            for ref in claim.verification_record_refs:
                yield from one(ref, "VerificationRecord", "claim.verification_record_refs")
    elif isinstance(payload, t.VerificationBundle):
        yield from one(payload.claim_graph_ref, "ClaimGraph", "claim_graph_ref")
        for ref in payload.proof_obligation_refs:
            yield from one(ref, "ProofObligation", "proof_obligation_refs")
        for ref in payload.verification_record_refs:
            yield from one(ref, "VerificationRecord", "verification_record_refs")
    elif isinstance(payload, t.LiteratureEvidence):
        yield from one(payload.question_ref, "ResearchQuestion", "question_ref")
    elif isinstance(payload, t.ClosestTheoryMap):
        yield from one(payload.claim_graph_ref, "ClaimGraph", "claim_graph_ref")
        yield from one(payload.literature_evidence_ref, "LiteratureEvidence", "literature_evidence_ref")
    elif isinstance(payload, t.AbsorptionAssessment):
        yield from one(payload.closest_theory_map_ref, "ClosestTheoryMap", "closest_theory_map_ref")
        yield from one(payload.central_claim_graph_ref, "ClaimGraph", "central_claim_graph_ref")
    elif isinstance(payload, t.ResultPortfolio):
        yield from one(payload.claim_graph_ref, "ClaimGraph", "claim_graph_ref")
    elif isinstance(payload, t.GateDossier):
        yield from one(
            payload.research_question_ref,
            "ResearchQuestion",
            "research_question_ref",
        )
    elif isinstance(payload, t.ValidatedArgumentPackage):
        fields = {
            "question_ref": "ResearchQuestion", "benchmark_set_ref": "BenchmarkSet",
            "primitive_graph_ref": "PrimitiveGraph", "selected_mechanism_ref": "MechanismHypothesis",
            "prediction_register_ref": "PredictionRegister", "example_suite_ref": "ExampleSuite",
            "economic_argument_graph_ref": "EconomicArgumentGraph",
            "implementation_tournament_ref": "ImplementationTournament", "formal_model_ref": "FormalModel",
            "formalization_map_ref": "FormalizationMap", "assumption_map_ref": "AssumptionMap",
            "claim_graph_ref": "ClaimGraph", "verification_bundle_ref": "VerificationBundle",
            "closest_theory_map_ref": "ClosestTheoryMap", "absorption_assessment_ref": "AbsorptionAssessment",
            "result_portfolio_ref": "ResultPortfolio", "g5_dossier_ref": "GateDossier",
        }
        for field, expected in fields.items():
            yield from one(getattr(payload, field), expected, field)
        for ref in payload.serious_rejected_rival_refs:
            yield from one(ref, "MechanismHypothesis", "serious_rejected_rival_refs")
        if payload.pre_result_brief_ref is not None:
            yield from one(
                payload.pre_result_brief_ref,
                "PreResultBrief",
                "pre_result_brief_ref",
            )
    elif isinstance(payload, t.PreResultBrief):
        yield from one(payload.question_ref, "ResearchQuestion", "question_ref")
        yield from one(payload.benchmark_set_ref, "BenchmarkSet", "benchmark_set_ref")
        yield from one(payload.primitive_graph_ref, "PrimitiveGraph", "primitive_graph_ref")
    elif isinstance(payload, t.BlindCaseManifest):
        yield from one(payload.pre_result_brief_ref, "PreResultBrief", "pre_result_brief_ref")
        yield from one(payload.gold_package_ref, "ValidatedArgumentPackage", "gold_package_ref")
    elif isinstance(payload, t.TransformedVariantManifest):
        yield from one(payload.base_case_manifest_ref, "BlindCaseManifest", "base_case_manifest_ref")
        yield from one(payload.transformed_brief_ref, "PreResultBrief", "transformed_brief_ref")
    elif isinstance(payload, t.VAPComparisonRecord):
        yield from one(payload.case_manifest_ref, "BlindCaseManifest", "case_manifest_ref")
        yield from one(payload.candidate_package_ref, "ValidatedArgumentPackage", "candidate_package_ref")
        yield from one(payload.gold_package_ref, "ValidatedArgumentPackage", "gold_package_ref")


def _current_index(items: Iterable[object], id_name: str) -> dict[str, int]:
    result: dict[str, int] = {}
    for item in items:
        stable_id = getattr(item, id_name)
        result[stable_id] = max(result.get(stable_id, 0), item.version)
    return result


def _payload_at(
    payloads: Mapping[tuple[str, int], t.TheoryPayload],
    reference: EntityVersionRef,
    expected: type[t.TheoryPayload],
    label: str,
) -> t.TheoryPayload:
    payload = payloads.get(_entity_key(reference))
    if not isinstance(payload, expected):
        raise TheoryValidationError(f"{label} is unavailable or has the wrong type")
    return payload


def _validate_mechanism_promotion_closure(
    payloads: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    required_roles = {
        "benchmark",
        "mechanism_on",
        "ablation",
        "rival_separator",
        "boundary",
    }
    for argument in payloads.values():
        if not isinstance(argument, t.EconomicArgumentGraph):
            continue
        examples = _payload_at(
            payloads, argument.example_suite_ref, t.ExampleSuite, "ExampleSuite"
        )
        register = _payload_at(
            payloads,
            argument.prediction_register_ref,
            t.PredictionRegister,
            "PredictionRegister",
        )
        tournament = _payload_at(
            payloads,
            register.mechanism_tournament_ref,  # type: ignore[attr-defined]
            t.MechanismTournament,
            "MechanismTournament",
        )
        assert isinstance(examples, t.ExampleSuite)
        assert isinstance(register, t.PredictionRegister)
        assert isinstance(tournament, t.MechanismTournament)
        frozen_register = _payload_at(
            payloads,
            examples.frozen_prediction_register_ref,
            t.PredictionRegister,
            "frozen PredictionRegister",
        )
        assert isinstance(frozen_register, t.PredictionRegister)
        if (
            examples.frozen_prediction_register_ref.entity_id
            != argument.prediction_register_ref.entity_id
            or examples.frozen_prediction_register_ref.version
            > argument.prediction_register_ref.version
            or frozen_register.original_predictions != register.original_predictions
        ):
            raise TheoryValidationError(
                "ExampleSuite does not preserve the exact frozen prediction baseline"
            )
        observed_roles = {role for case in examples.cases for role in case.roles}
        if not required_roles.issubset(observed_roles):
            raise TheoryValidationError(
                "mechanism promotion lacks required functional role coverage: benchmark, ablation, rival separator, or boundary"
            )
        if (
            tournament.proposed_selected_ref != argument.selected_mechanism_ref
            or not tournament.serious_rival_refs
        ):
            raise TheoryValidationError(
                "mechanism promotion requires its selected hypothesis and a serious rival"
            )
        frozen_ids = {item.prediction_id for item in register.original_predictions}
        reconciled_ids = {item.prediction_id for item in register.reconciliations}
        if not frozen_ids.issubset(reconciled_ids):
            raise TheoryValidationError(
                "mechanism promotion requires a reconciliation for every frozen prediction"
            )
        case_ids = {case.case_id for case in examples.cases}
        if any(
            not set(edge.supporting_case_ids).issubset(case_ids)
            for edge in argument.edges
        ):
            raise TheoryValidationError(
                "mechanism promotion economic arrow cites an unknown example case"
            )


def _validate_formalization_coverage(
    payloads: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    for mapping in payloads.values():
        if not isinstance(mapping, t.FormalizationMap):
            continue
        argument = _payload_at(
            payloads,
            mapping.economic_argument_graph_ref,
            t.EconomicArgumentGraph,
            "formalization EconomicArgumentGraph",
        )
        model = _payload_at(
            payloads,
            mapping.formal_model_ref,
            t.FormalModel,
            "formalization FormalModel",
        )
        assert isinstance(argument, t.EconomicArgumentGraph)
        assert isinstance(model, t.FormalModel)
        economic_ids = {
            *(item.node_id for item in argument.nodes),
            *(item.edge_id for item in argument.edges),
        }
        load_bearing_ids = {
            item.edge_id for item in argument.edges if item.load_bearing
        }
        forward_ids = {item.economic_element_id for item in mapping.economic_to_formal}
        if not forward_ids.issubset(economic_ids):
            raise TheoryValidationError(
                "formalization references an unknown economic arrow or node"
            )
        if not load_bearing_ids.issubset(forward_ids):
            raise TheoryValidationError(
                "formalization mapping omits load-bearing economic arrow coverage"
            )
        formal_ids = {item.object_id for item in model.formal_objects}
        forward_formal_ids = {
            formal_id
            for item in mapping.economic_to_formal
            for formal_id in item.formal_object_ids
        }
        reverse_formal_ids = {
            item.formal_object_id for item in mapping.formal_to_economic
        }
        if not forward_formal_ids.issubset(formal_ids) or not reverse_formal_ids.issubset(
            formal_ids
        ):
            raise TheoryValidationError(
                "formalization references an unknown formal object ID"
            )
        central_ids = {item.object_id for item in model.formal_objects if item.central}
        if not central_ids.issubset(reverse_formal_ids):
            raise TheoryValidationError(
                "formalization reverse coverage omits a central formal object"
            )
        if any(
            not set(item.economic_element_ids).issubset(economic_ids)
            for item in mapping.formal_to_economic
        ):
            raise TheoryValidationError(
                "formalization reverse map references an unknown economic element"
            )


def _validate_claim_verification_closure(
    payloads: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    for key, graph in payloads.items():
        if not isinstance(graph, t.ClaimGraph):
            continue
        graph_ref = EntityVersionRef(entity_id=key[0], version=key[1])
        assumptions = _payload_at(
            payloads,
            graph.assumption_map_ref,
            t.AssumptionMap,
            "ClaimGraph AssumptionMap",
        )
        assert isinstance(assumptions, t.AssumptionMap)
        assumption_ids = {item.assumption_id for item in assumptions.assumptions}
        for claim in graph.claims:
            if not set(claim.assumption_ids).issubset(assumption_ids):
                raise TheoryValidationError("claim references an unknown assumption")
            obligation_refs = set(claim.proof_obligation_refs)
            for reference in claim.proof_obligation_refs:
                obligation = _payload_at(
                    payloads, reference, t.ProofObligation, "claim proof obligation"
                )
                assert isinstance(obligation, t.ProofObligation)
                if (
                    obligation.claim_graph_ref != graph_ref
                    or obligation.claim_id != claim.claim_id
                    or not set(obligation.assumption_ids).issubset(assumption_ids)
                ):
                    raise TheoryValidationError(
                        "proof obligation and retained claim mismatch"
                    )
            for reference in claim.verification_record_refs:
                record = _payload_at(
                    payloads,
                    reference,
                    t.VerificationRecord,
                    "claim verification record",
                )
                assert isinstance(record, t.VerificationRecord)
                if (
                    record.claim_graph_ref != graph_ref
                    or record.obligation_ref not in obligation_refs
                ):
                    raise TheoryValidationError(
                        "verification record does not close a claim obligation"
                    )
                if record.outcome == "falsified":
                    raise TheoryValidationError(
                        "a falsified obligation cannot remain in a retained claim"
                    )
    for bundle in payloads.values():
        if not isinstance(bundle, t.VerificationBundle):
            continue
        graph = _payload_at(
            payloads, bundle.claim_graph_ref, t.ClaimGraph, "VerificationBundle ClaimGraph"
        )
        assert isinstance(graph, t.ClaimGraph)
        expected_obligations = {
            reference
            for claim in graph.claims
            for reference in claim.proof_obligation_refs
        }
        declared_records = {
            reference
            for claim in graph.claims
            for reference in claim.verification_record_refs
        }
        if set(bundle.proof_obligation_refs) != expected_obligations:
            raise TheoryValidationError(
                "VerificationBundle does not contain every claim obligation"
            )
        bundle_records: dict[EntityVersionRef, t.VerificationRecord] = {}
        for reference in bundle.verification_record_refs:
            record = _payload_at(
                payloads,
                reference,
                t.VerificationRecord,
                "VerificationBundle record",
            )
            assert isinstance(record, t.VerificationRecord)
            if (
                record.claim_graph_ref != bundle.claim_graph_ref
                or record.obligation_ref not in expected_obligations
                or record.formal_model_ref != graph.formal_model_ref
                or record.assumption_map_ref != graph.assumption_map_ref
            ):
                raise TheoryValidationError(
                    "VerificationBundle record does not bind its exact claim, obligation, model, and assumptions"
                )
            bundle_records[reference] = record
        if {
            record.obligation_ref for record in bundle_records.values()
        } != expected_obligations:
            raise TheoryValidationError(
                "VerificationBundle completeness requires a verification record for every claim obligation"
            )
        if not declared_records.issubset(bundle_records):
            raise TheoryValidationError(
                "VerificationBundle omits a VerificationRecord declared by its ClaimGraph"
            )


def _validate_result_portfolio_membership(
    payloads: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    for portfolio in payloads.values():
        if not isinstance(portfolio, t.ResultPortfolio):
            continue
        graph = _payload_at(
            payloads,
            portfolio.claim_graph_ref,
            t.ClaimGraph,
            "ResultPortfolio ClaimGraph",
        )
        assert isinstance(graph, t.ClaimGraph)
        claim_ids = {item.claim_id for item in graph.claims}
        portfolio_ids = {
            *(item.claim_id for item in portfolio.included_results),
            *(item.claim_id for item in portfolio.excluded_results),
        }
        if not portfolio_ids.issubset(claim_ids):
            raise TheoryValidationError(
                "ResultPortfolio contains an unknown ClaimGraph claim"
            )


def _validate_absorption_closure(
    payloads: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    required_dimensions = {
        "benchmark",
        "primitives",
        "timing",
        "solution_concept",
        "assumptions",
        "quantifiers",
        "formal_result",
        "economic_lesson",
    }
    classification_outcomes = {
        "duplicate": {"absorbed"},
        "direct_corollary": {"absorbed"},
        "special_case": {"absorbed", "partially_absorbed"},
        "application": {"application_only"},
        "unresolved": {"unresolved_evidence"},
        "generalization": {"nonabsorbed", "partially_absorbed"},
        "converse": {"nonabsorbed", "partially_absorbed"},
        "different_mechanism": {"nonabsorbed", "partially_absorbed"},
        "different_boundary": {"nonabsorbed", "partially_absorbed"},
        "non_comparable": {"nonabsorbed", "unresolved_evidence"},
    }
    for assessment in payloads.values():
        if not isinstance(assessment, t.AbsorptionAssessment):
            continue
        closest = _payload_at(
            payloads,
            assessment.closest_theory_map_ref,
            t.ClosestTheoryMap,
            "AbsorptionAssessment ClosestTheoryMap",
        )
        graph = _payload_at(
            payloads,
            assessment.central_claim_graph_ref,
            t.ClaimGraph,
            "AbsorptionAssessment ClaimGraph",
        )
        assert isinstance(closest, t.ClosestTheoryMap)
        assert isinstance(graph, t.ClaimGraph)
        literature = _payload_at(
            payloads,
            closest.literature_evidence_ref,
            t.LiteratureEvidence,
            "ClosestTheoryMap LiteratureEvidence",
        )
        assert isinstance(literature, t.LiteratureEvidence)
        if closest.claim_graph_ref != assessment.central_claim_graph_ref:
            raise TheoryValidationError(
                "AbsorptionAssessment and ClosestTheoryMap bind different ClaimGraphs"
            )
        if assessment.central_claim_id not in {
            claim.claim_id for claim in graph.claims
        }:
            raise TheoryValidationError(
                "AbsorptionAssessment central claim is absent from its ClaimGraph"
            )
        if {item.dimension for item in closest.dimensions} != required_dimensions:
            raise TheoryValidationError(
                "ClosestTheoryMap must cover all eight non-compensatory translation dimensions"
            )
        failed = [item for item in closest.dimensions if item.mapping_status == "fails"]
        unresolved = [
            item for item in closest.dimensions if item.mapping_status == "unresolved"
        ]
        unverified = [
            item
            for item in literature.assertions
            if item.verification_status != "source_verified"
        ]
        if bool(failed) != (closest.first_mapping_failure is not None):
            raise TheoryValidationError(
                "ClosestTheoryMap first mapping failure must match an exact failed dimension"
            )
        if assessment.first_mapping_failure != closest.first_mapping_failure:
            raise TheoryValidationError(
                "AbsorptionAssessment must preserve the exact first mapping failure"
            )
        if assessment.outcome not in classification_outcomes[closest.classification]:
            raise TheoryValidationError(
                "ClosestTheoryMap classification contradicts AbsorptionAssessment outcome"
            )
        if assessment.outcome == "nonabsorbed" and (
            not failed or unresolved or unverified
        ):
            raise TheoryValidationError(
                "nonabsorption requires a verified exact failed mapping dimension"
            )
        if assessment.outcome == "absorbed" and (failed or unresolved or unverified):
            raise TheoryValidationError(
                "absorbed work cannot retain failed, unresolved, or unverified mapping evidence"
            )
        if assessment.outcome == "unresolved_evidence" and not (
            unresolved or unverified
        ):
            raise TheoryValidationError(
                "unresolved absorption requires an unresolved dimension or source"
            )
        if assessment.recommended_route == "proceed" and any(
            item.access_status != "full_text"
            or item.verification_status != "source_verified"
            for item in literature.assertions
        ):
            raise TheoryValidationError(
                "a proceed recommendation requires verified full-text literature"
            )


def _validate_blind_evaluation_closure(
    payloads: Mapping[tuple[str, int], t.TheoryPayload],
    entity_index: Mapping[tuple[str, int], EntityVersion],
    artifact_index: Mapping[tuple[str, int], ArtifactRegistration],
    decision_index: Mapping[tuple[str, int], Decision],
    *,
    current_artifacts: Mapping[str, int],
    current_decisions: Mapping[str, int],
) -> None:
    variants: list[tuple[EntityVersionRef, t.TransformedVariantManifest]] = []
    comparisons_by_attempt: dict[str, list[t.VAPComparisonRecord]] = {}
    for key, payload in payloads.items():
        if isinstance(payload, t.BlindCaseManifest):
            brief = _payload_at(
                payloads,
                payload.pre_result_brief_ref,
                t.PreResultBrief,
                "BlindCaseManifest PreResultBrief",
            )
            assert isinstance(brief, t.PreResultBrief)
            if brief.attempt_id != payload.attempt_id:
                raise TheoryValidationError(
                    "BlindCaseManifest and PreResultBrief attempt IDs disagree"
                )
            if payload.layer in {"transformed", "synthetic_holdout"} and not (
                payload.hidden_probe_refs and payload.source_paper_refs
            ):
                raise TheoryValidationError(
                    "confirmatory blind cases require sealed source and hidden probe artifacts"
                )
        elif isinstance(payload, t.TransformedVariantManifest):
            base = _payload_at(
                payloads,
                payload.base_case_manifest_ref,
                t.BlindCaseManifest,
                "TransformedVariantManifest BlindCaseManifest",
            )
            transformed_brief = _payload_at(
                payloads,
                payload.transformed_brief_ref,
                t.PreResultBrief,
                "TransformedVariantManifest PreResultBrief",
            )
            assert isinstance(base, t.BlindCaseManifest)
            assert isinstance(transformed_brief, t.PreResultBrief)
            if (
                payload.attempt_id != base.attempt_id
                or payload.attempt_id != transformed_brief.attempt_id
            ):
                raise TheoryValidationError(
                    "transformed manifest, base case, and brief must share one attempt ID"
                )
            decision = decision_index.get(_decision_key(payload.implementation_freeze_ref))
            if (
                decision is None
                or decision.decision_kind != "theory_mode"
                or decision.status != "confirmed"
                or decision.decider.kind != "human"
                or decision.selected_option != "freeze"
                or decision.subject_ref != payload.transformed_brief_ref.entity_id
                or decision.scope_ref != payload.attempt_id
            ):
                raise TheoryValidationError(
                    "TransformedVariantManifest requires a current human implementation-freeze Decision"
                )
            variants.append(
                (EntityVersionRef(entity_id=key[0], version=key[1]), payload)
            )
        elif isinstance(payload, t.VAPComparisonRecord):
            comparisons_by_attempt.setdefault(payload.attempt_id, []).append(payload)

    if any(len(records) > 1 for records in comparisons_by_attempt.values()):
        raise TheoryValidationError(
            "one blind attempt can have at most one terminal VAPComparisonRecord"
        )

    for comparison in (
        item for records in comparisons_by_attempt.values() for item in records
    ):
        manifest = _payload_at(
            payloads,
            comparison.case_manifest_ref,
            t.BlindCaseManifest,
            "VAPComparisonRecord BlindCaseManifest",
        )
        candidate = _payload_at(
            payloads,
            comparison.candidate_package_ref,
            t.ValidatedArgumentPackage,
            "VAPComparisonRecord candidate VAP",
        )
        gold = _payload_at(
            payloads,
            comparison.gold_package_ref,
            t.ValidatedArgumentPackage,
            "VAPComparisonRecord gold VAP",
        )
        assert isinstance(manifest, t.BlindCaseManifest)
        assert isinstance(candidate, t.ValidatedArgumentPackage)
        assert isinstance(gold, t.ValidatedArgumentPackage)
        matching_variants = [
            payload
            for _, payload in variants
            if payload.base_case_manifest_ref == comparison.case_manifest_ref
            and payload.attempt_id == comparison.attempt_id
        ]
        expected_brief = manifest.pre_result_brief_ref
        if manifest.layer in {"transformed", "synthetic_holdout"}:
            if len(matching_variants) != 1:
                raise TheoryValidationError(
                    "a confirmatory comparison requires one exact transformed variant"
                )
            expected_brief = matching_variants[0].transformed_brief_ref
        if (
            comparison.attempt_id != manifest.attempt_id
            or comparison.gold_package_ref != manifest.gold_package_ref
            or candidate.release_mode != "evaluation_only"
            or candidate.evaluation_attempt_id != comparison.attempt_id
            or candidate.pre_result_brief_ref != expected_brief
            or candidate.generator_actor is None
            or comparison.evaluator == candidate.generator_actor
        ):
            raise TheoryValidationError(
                "blind comparison does not bind one sealed attempt, candidate, gold, brief, and independent evaluator"
            )
        candidate_entity = entity_index[_entity_key(comparison.candidate_package_ref)]
        candidate_hash = sha256_digest(canonical_json_bytes(candidate_entity))
        lock = artifact_index.get(_artifact_key(comparison.candidate_lock_ref))
        if (
            lock is None
            or lock.content_hash != comparison.candidate_lock_ref.content_hash
            or lock.content_hash != candidate_hash
            or comparison.candidate_package_hash != candidate_hash
            or lock.media_type
            != "application/vnd.econ-theorist.candidate-lock+json"
            or lock.version != 1
            or lock.supersedes is not None
            or lock.artifact_id != f"candidate.lock.{comparison.attempt_id}"
            or current_artifacts.get(lock.artifact_id) != lock.version
        ):
            raise TheoryValidationError(
                "candidate package hash, prior lock artifact, and exact EntityVersion bytes disagree"
            )
        if {
            item.dimension for item in comparison.dimension_comparisons
        } != _SIGNATURE_DIMENSIONS:
            raise TheoryValidationError(
                "VAPComparisonRecord must cover all 17 semantic signature dimensions"
            )
        if (
            comparison.disposition == "confirmatory_clean"
            and manifest.layer == "public_classic"
        ):
            raise TheoryValidationError(
                "a public classic comparison cannot be confirmatory_clean"
            )


def _validate_vap_noncompensatory_floors(
    payloads: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    required_closest_dimensions = {
        "benchmark",
        "primitives",
        "timing",
        "solution_concept",
        "assumptions",
        "quantifiers",
        "formal_result",
        "economic_lesson",
    }
    for package in payloads.values():
        if not isinstance(package, t.ValidatedArgumentPackage):
            continue
        graph = _payload_at(
            payloads, package.claim_graph_ref, t.ClaimGraph, "VAP ClaimGraph"
        )
        bundle = _payload_at(
            payloads,
            package.verification_bundle_ref,
            t.VerificationBundle,
            "VAP VerificationBundle",
        )
        closest = _payload_at(
            payloads,
            package.closest_theory_map_ref,
            t.ClosestTheoryMap,
            "VAP ClosestTheoryMap",
        )
        portfolio = _payload_at(
            payloads,
            package.result_portfolio_ref,
            t.ResultPortfolio,
            "VAP ResultPortfolio",
        )
        implementation = _payload_at(
            payloads,
            package.implementation_tournament_ref,
            t.ImplementationTournament,
            "VAP ImplementationTournament",
        )
        benchmark = _payload_at(
            payloads, package.benchmark_set_ref, t.BenchmarkSet, "VAP BenchmarkSet"
        )
        primitives = _payload_at(
            payloads, package.primitive_graph_ref, t.PrimitiveGraph, "VAP PrimitiveGraph"
        )
        selected_mechanism = _payload_at(
            payloads,
            package.selected_mechanism_ref,
            t.MechanismHypothesis,
            "VAP selected MechanismHypothesis",
        )
        predictions = _payload_at(
            payloads,
            package.prediction_register_ref,
            t.PredictionRegister,
            "VAP PredictionRegister",
        )
        examples = _payload_at(
            payloads, package.example_suite_ref, t.ExampleSuite, "VAP ExampleSuite"
        )
        argument = _payload_at(
            payloads,
            package.economic_argument_graph_ref,
            t.EconomicArgumentGraph,
            "VAP EconomicArgumentGraph",
        )
        model = _payload_at(
            payloads, package.formal_model_ref, t.FormalModel, "VAP FormalModel"
        )
        formalization = _payload_at(
            payloads,
            package.formalization_map_ref,
            t.FormalizationMap,
            "VAP FormalizationMap",
        )
        assumptions = _payload_at(
            payloads, package.assumption_map_ref, t.AssumptionMap, "VAP AssumptionMap"
        )
        absorption = _payload_at(
            payloads,
            package.absorption_assessment_ref,
            t.AbsorptionAssessment,
            "VAP AbsorptionAssessment",
        )
        assert isinstance(graph, t.ClaimGraph)
        assert isinstance(bundle, t.VerificationBundle)
        assert isinstance(closest, t.ClosestTheoryMap)
        assert isinstance(portfolio, t.ResultPortfolio)
        assert isinstance(implementation, t.ImplementationTournament)
        assert isinstance(benchmark, t.BenchmarkSet)
        assert isinstance(primitives, t.PrimitiveGraph)
        assert isinstance(selected_mechanism, t.MechanismHypothesis)
        assert isinstance(predictions, t.PredictionRegister)
        assert isinstance(examples, t.ExampleSuite)
        assert isinstance(argument, t.EconomicArgumentGraph)
        assert isinstance(model, t.FormalModel)
        assert isinstance(formalization, t.FormalizationMap)
        assert isinstance(assumptions, t.AssumptionMap)
        assert isinstance(absorption, t.AbsorptionAssessment)
        mechanism_tournament = _payload_at(
            payloads,
            predictions.mechanism_tournament_ref,
            t.MechanismTournament,
            "VAP MechanismTournament",
        )
        assert isinstance(mechanism_tournament, t.MechanismTournament)
        if package.pre_result_brief_ref is not None:
            brief = _payload_at(
                payloads,
                package.pre_result_brief_ref,
                t.PreResultBrief,
                "VAP PreResultBrief",
            )
            assert isinstance(brief, t.PreResultBrief)
            if (
                brief.question_ref != package.question_ref
                or brief.attempt_id != package.evaluation_attempt_id
            ):
                raise TheoryValidationError(
                    "evaluation VAP does not bind the exact attempt PreResultBrief"
                )
        proposed = implementation.proposed_selected_model_ref
        if (
            proposed is None
            or package.formal_model_ref.entity_id != proposed.entity_id
            or package.formal_model_ref.version < proposed.version
        ):
            raise TheoryValidationError(
                "VAP formal model is not the selected implementation or its promoted successor"
            )
        if (
            benchmark.question_ref != package.question_ref
            or primitives.question_ref != package.question_ref
            or primitives.benchmark_set_ref != package.benchmark_set_ref
            or selected_mechanism.question_ref != package.question_ref
            or selected_mechanism.primitive_graph_ref != package.primitive_graph_ref
            or mechanism_tournament.question_ref != package.question_ref
            or mechanism_tournament.proposed_selected_ref
            != package.selected_mechanism_ref
            or set(mechanism_tournament.serious_rival_refs)
            != set(package.serious_rejected_rival_refs)
            or predictions.question_ref != package.question_ref
            or examples.selected_mechanism_ref != package.selected_mechanism_ref
            or argument.selected_mechanism_ref != package.selected_mechanism_ref
            or argument.primitive_graph_ref != package.primitive_graph_ref
            or argument.prediction_register_ref != package.prediction_register_ref
            or argument.example_suite_ref != package.example_suite_ref
            or implementation.selected_mechanism_ref != package.selected_mechanism_ref
            or implementation.economic_argument_graph_ref
            != package.economic_argument_graph_ref
            or model.question_ref != package.question_ref
            or model.selected_mechanism_ref != package.selected_mechanism_ref
            or model.primitive_graph_ref != package.primitive_graph_ref
            or formalization.economic_argument_graph_ref
            != package.economic_argument_graph_ref
            or formalization.formal_model_ref != package.formal_model_ref
            or assumptions.formal_model_ref != package.formal_model_ref
            or assumptions.formalization_map_ref != package.formalization_map_ref
            or graph.formal_model_ref != package.formal_model_ref
            or graph.formalization_map_ref != package.formalization_map_ref
            or graph.assumption_map_ref != package.assumption_map_ref
            or bundle.claim_graph_ref != package.claim_graph_ref
            or closest.claim_graph_ref != package.claim_graph_ref
            or absorption.closest_theory_map_ref != package.closest_theory_map_ref
            or absorption.central_claim_graph_ref != package.claim_graph_ref
            or portfolio.claim_graph_ref != package.claim_graph_ref
            or portfolio.economic_nugget != package.economic_nugget
        ):
            raise TheoryValidationError(
                "VAP splices incompatible branches instead of preserving one exact scientific argument chain"
            )
        headline = next(
            (item for item in graph.claims if item.claim_id == portfolio.headline_claim_id),
            None,
        )
        if headline is None:
            raise TheoryValidationError("VAP headline is absent from its ClaimGraph")
        if package.release_mode == "production_candidate":
            if not headline.boundary_case_ids:
                raise TheoryValidationError(
                    "production VAP is missing the non-compensatory boundary floor"
                )
            records = {
                reference: _payload_at(
                    payloads,
                    reference,
                    t.VerificationRecord,
                    "VAP verification record",
                )
                for reference in bundle.verification_record_refs
            }
            discharged_obligations = {
                record.obligation_ref
                for record in records.values()
                if isinstance(record, t.VerificationRecord)
                and record.outcome == "discharged"
            }
            if not set(bundle.proof_obligation_refs).issubset(discharged_obligations):
                raise TheoryValidationError(
                    "production VAP is missing the non-compensatory proof floor"
                )
            if any(
                isinstance(record, t.VerificationRecord)
                and record.outcome != "discharged"
                for record in records.values()
            ):
                raise TheoryValidationError(
                    "production VAP cannot retain a failed, inconclusive, or falsified verification record"
                )
            if {
                item.dimension for item in closest.dimensions
            } != required_closest_dimensions:
                raise TheoryValidationError(
                    "production VAP is missing the absorption translation floor"
                )


def validate_theory_projection(
    entities: Iterable[EntityVersion],
    artifacts: Iterable[ArtifactRegistration] = (),
    decisions: Iterable[Decision] = (),
    *,
    current_entities: Mapping[str, int] | None = None,
    current_artifacts: Mapping[str, int] | None = None,
    current_decisions: Mapping[str, int] | None = None,
) -> TheoryReadinessReport:
    """Validate all registered payloads and their exact cross-object semantics."""

    entity_values = tuple(entities)
    artifact_values = tuple(artifacts)
    decision_values = tuple(decisions)
    entity_index = {_entity_key(item): item for item in entity_values}
    artifact_index = {_artifact_key(item): item for item in artifact_values}
    decision_index = {_decision_key(item): item for item in decision_values}
    if len(entity_index) != len(entity_values):
        raise TheoryValidationError("projection repeats an exact entity version")
    if len(artifact_index) != len(artifact_values):
        raise TheoryValidationError("projection repeats an exact artifact version")
    if len(decision_index) != len(decision_values):
        raise TheoryValidationError("projection repeats an exact Decision version")
    current_entities = dict(current_entities or _current_index(entity_values, "entity_id"))
    current_artifacts = dict(current_artifacts or _current_index(artifact_values, "artifact_id"))
    current_decisions = dict(current_decisions or _current_index(decision_values, "decision_id"))

    payloads: dict[tuple[str, int], t.TheoryPayload] = {}
    for entity in entity_values:
        if (
            entity.entity_type not in t.THEORY_PAYLOAD_MODELS
            or not t.is_packed_theory_entity(entity)
        ):
            continue
        previous = entity_index.get((entity.entity_id, entity.version - 1))
        if entity.version > 1 and previous is None:
            raise TheoryValidationError("typed theory history omits an exact predecessor")
        payloads[_entity_key(entity)] = validate_theory_entity(entity, previous)

    # This prohibition is local and must fail even when the surrounding draft
    # projection is incomplete: numerical exploration can never acquire the
    # semantic status of a universal proof merely because other refs exist.
    for payload in payloads.values():
        if (
            isinstance(payload, t.VerificationRecord)
            and payload.outcome == "discharged"
            and payload.method in _NUMERICAL_ONLY_METHODS
        ):
            raise TheoryValidationError(
                "finite example, enumeration, or simulation cannot discharge a universal obligation"
            )

    for key, payload in payloads.items():
        source = entity_index[key]
        for reference in (*source.artifact_refs, *_walk_exact_refs(payload)):
            if isinstance(reference, EntityVersionRef):
                if _entity_key(reference) not in entity_index:
                    raise TheoryValidationError(
                        f"{source.entity_type} contains unresolved exact entity ref "
                        f"{reference.entity_id}@{reference.version}"
                    )
            elif isinstance(reference, ArtifactDependencyRef):
                target = artifact_index.get(_artifact_key(reference))
                if target is None or target.content_hash != reference.content_hash:
                    raise TheoryValidationError(
                        f"{source.entity_type} contains unresolved or hash-mismatched "
                        f"artifact ref {reference.artifact_id}@{reference.version}"
                    )
            elif isinstance(reference, DecisionVersionRef):
                if _decision_key(reference) not in decision_index:
                    raise TheoryValidationError(
                        f"{source.entity_type} contains unresolved exact Decision ref "
                        f"{reference.decision_id}@{reference.version}"
                    )
        for reference, expected, label in _expected_entity_refs(payload):
            target = entity_index.get(_entity_key(reference))
            if target is None:
                continue  # the generic exact-ref error above is more specific
            if target.entity_type not in expected:
                raise TheoryValidationError(
                    f"{source.entity_type}.{label} expects {expected}, got {target.entity_type}"
                )

    _validate_mechanism_promotion_closure(payloads)
    _validate_formalization_coverage(payloads)
    _validate_claim_verification_closure(payloads)
    _validate_result_portfolio_membership(payloads)
    _validate_absorption_closure(payloads)
    _validate_blind_evaluation_closure(
        payloads,
        entity_index,
        artifact_index,
        decision_index,
        current_artifacts=current_artifacts,
        current_decisions=current_decisions,
    )
    _validate_vap_noncompensatory_floors(payloads)

    # Gate dossiers are v1, so a stable citation is also an exact citation.
    dossier_by_id = {
        entity_index[key].entity_id: (entity_index[key], payload)
        for key, payload in payloads.items()
        if isinstance(payload, t.GateDossier)
    }
    confirmed_gates: list[tuple[Decision, t.GateDossier]] = []
    phase2_entity_ids = {entity_index[key].entity_id for key in payloads}
    for decision in decision_values:
        if decision.decision_kind not in _GATE_RANK:
            continue
        cited = [dossier_by_id[item] for item in decision.evidence_refs if item in dossier_by_id]
        # Phase 1 histories may contain old gates created before GateDossier
        # existed.  New semantics apply only when a Decision cites a typed
        # dossier or governs a registered Phase 2 object.
        if not cited and decision.subject_ref not in phase2_entity_ids:
            continue
        if len(cited) != 1:
            raise TheoryValidationError("every G1-G5 Decision must cite exactly one GateDossier")
        dossier_entity, dossier = cited[0]
        if dossier.gate_kind != decision.decision_kind:
            raise TheoryValidationError("GateDossier kind does not match its Decision kind")
        if decision.subject_ref != dossier_entity.entity_id:
            raise TheoryValidationError(
                "a G1-G5 Decision subject_ref must name its exact GateDossier"
            )
        if decision.scope_ref != dossier.research_question_ref.entity_id:
            raise TheoryValidationError(
                "a G1-G5 Decision scope_ref must match the dossier ResearchQuestion"
            )
        if decision.status in {"provisional", "confirmed"}:
            if (
                decision.machine_outcome not in {"approve", "deny"}
                or decision.selected_option != decision.machine_outcome
            ):
                raise TheoryValidationError(
                    "an effective G1-G5 Decision requires matching approve/deny machine_outcome"
                )
        if not dossier.prepared_at < decision.decided_at:
            raise TheoryValidationError("GateDossier must be prepared before its Decision")
        if decision.status == "confirmed" and decision.machine_outcome == "approve":
            if decision.decider.kind != "human":
                raise TheoryValidationError("only a human may confirm a G1-G5 Decision")
            if current_decisions.get(decision.decision_id) != decision.version:
                continue
            confirmed_gates.append((decision, dossier))

    gates_by_scope: dict[
        tuple[str, int], dict[str, list[Decision]]
    ] = {}
    for decision, dossier in confirmed_gates:
        scope_key = _entity_key(dossier.research_question_ref)
        gates_by_scope.setdefault(scope_key, {}).setdefault(
            decision.decision_kind, []
        ).append(decision)
    ready_gate_kinds: set[str] = set()
    for by_kind in gates_by_scope.values():
        latest_prior = ""
        for kind in _GATE_ORDER:
            decisions_for_kind = by_kind.get(kind, ())
            if not decisions_for_kind:
                break
            earliest = min(item.decided_at for item in decisions_for_kind)
            if latest_prior and earliest <= latest_prior:
                break
            ready_gate_kinds.add(kind)
            latest_prior = max(item.decided_at for item in decisions_for_kind)

    discharged: set[tuple[str, int]] = set()
    for key, payload in payloads.items():
        if not isinstance(payload, t.VerificationRecord):
            continue
        obligation = payloads.get(_entity_key(payload.obligation_ref))
        if not isinstance(obligation, t.ProofObligation):
            continue
        if payload.claim_graph_ref != obligation.claim_graph_ref:
            raise TheoryValidationError("VerificationRecord and ProofObligation disagree on ClaimGraph")
        if payload.outcome == "discharged":
            if payload.method in _NUMERICAL_ONLY_METHODS:
                raise TheoryValidationError(
                    "finite example, enumeration, or simulation cannot discharge a universal obligation"
                )
            if payload.method not in obligation.admissible_methods:
                raise TheoryValidationError("verification method is not admissible for its obligation")
            discharged.add(_entity_key(payload.obligation_ref))

    blocked_packages: list[EntityVersionRef] = []
    for key, payload in payloads.items():
        if not isinstance(payload, t.ValidatedArgumentPackage):
            continue
        expected_kinds = _GATE_ORDER[:4]
        prior = [decision_index[_decision_key(ref)] for ref in payload.prior_gate_decision_refs]
        if tuple(item.decision_kind for item in prior) != expected_kinds:
            raise TheoryValidationError("VAP prior_gate_decision_refs must be exact ordered G1-G4")
        if any(
            item.status != "confirmed"
            or item.decider.kind != "human"
            or item.machine_outcome != "approve"
            for item in prior
        ):
            raise TheoryValidationError(
                "VAP prior G1-G4 Decisions must be human-confirmed approvals"
            )
        package_gate_is_stale = any(
            current_decisions.get(item.decision_id) != item.version for item in prior
        )
        package_input_is_stale = any(
            (
                isinstance(reference, EntityVersionRef)
                and current_entities.get(reference.entity_id) != reference.version
            )
            or (
                isinstance(reference, ArtifactDependencyRef)
                and current_artifacts.get(reference.artifact_id) != reference.version
            )
            or (
                isinstance(reference, DecisionVersionRef)
                and current_decisions.get(reference.decision_id) != reference.version
            )
            for reference in _walk_exact_refs(payload)
        )
        for decision in prior:
            cited_dossiers = [
                dossier_by_id[item][1]
                for item in decision.evidence_refs
                if item in dossier_by_id
            ]
            if (
                len(cited_dossiers) != 1
                or cited_dossiers[0].research_question_ref != payload.question_ref
            ):
                raise TheoryValidationError(
                    "VAP prior G1-G4 Decisions must govern the exact package ResearchQuestion"
                )
        dossier = payloads.get(_entity_key(payload.g5_dossier_ref))
        if not isinstance(dossier, t.GateDossier) or dossier.gate_kind != "G5_argument_validation":
            raise TheoryValidationError("VAP g5_dossier_ref must name an exact G5 GateDossier")
        if dossier.research_question_ref != payload.question_ref:
            raise TheoryValidationError(
                "VAP G5 dossier must govern the exact package ResearchQuestion"
            )
        absorption = payloads.get(_entity_key(payload.absorption_assessment_ref))
        if not isinstance(absorption, t.AbsorptionAssessment):
            raise TheoryValidationError("VAP absorption assessment is unavailable")
        if payload.release_mode == "evaluation_only" and payload.novelty_claim_mode != "none":
            raise TheoryValidationError("evaluation-only VAP cannot claim novelty")
        if payload.release_mode == "production_candidate":
            if payload.novelty_claim_mode != "qualified":
                raise TheoryValidationError("production VAP requires qualified novelty")
            if absorption.outcome in {"absorbed", "unresolved_evidence"}:
                raise TheoryValidationError("absorbed or unresolved work cannot be a production VAP")
        if absorption.outcome in {"absorbed", "unresolved_evidence"}:
            blocked_packages.append(EntityVersionRef(entity_id=key[0], version=key[1]))
            if dossier.proposed_action == "approve":
                raise TheoryValidationError("absorption blocks an approving G5 dossier")
        elif package_gate_is_stale or package_input_is_stale:
            blocked_packages.append(EntityVersionRef(entity_id=key[0], version=key[1]))

    return TheoryReadinessReport(
        parsed_entity_count=len(payloads),
        discharged_obligation_count=len(discharged),
        confirmed_gate_kinds=tuple(
            kind
            for kind in _GATE_ORDER
            if kind in ready_gate_kinds
        ),
        production_blocked_package_refs=tuple(blocked_packages),
    )


def _canonical_ref_key(reference: object) -> tuple[object, ...]:
    if isinstance(reference, EntityVersionRef):
        return ("entity", reference.entity_id, reference.version)
    if isinstance(reference, RelationVersionRef):
        return ("relation", reference.relation_id, reference.version)
    if isinstance(reference, ArtifactDependencyRef):
        return ("artifact", reference.artifact_id, reference.version, reference.content_hash)
    if isinstance(reference, DecisionVersionRef):
        return ("decision", reference.decision_id, reference.version)
    if isinstance(reference, BlockerRef):
        return ("blocker", reference.blocker_id)
    raise TheoryValidationError("unsupported canonical candidate reference")


def _research_question_roots(
    reference: EntityVersionRef,
    entity_index: Mapping[tuple[str, int], EntityVersion],
    payload_index: Mapping[tuple[str, int], t.TheoryPayload],
    *,
    memo: dict[tuple[str, int], frozenset[EntityVersionRef]] | None = None,
) -> frozenset[EntityVersionRef]:
    """Resolve every exact ResearchQuestion reachable through a cyclic typed graph.

    Only cache a completed start-node traversal.  Caching recursive partial
    results is unsound for legitimate strongly connected components such as
    ClaimGraph <-> ProofObligation and VAP <-> GateDossier.
    """

    start = _entity_key(reference)
    memo = {} if memo is None else memo
    cached = memo.get(start)
    if cached is not None:
        return cached

    stack = [start]
    visited: set[tuple[str, int]] = set()
    roots: set[EntityVersionRef] = set()
    while stack:
        key = stack.pop()
        if key in visited:
            continue
        visited.add(key)
        if key not in entity_index:
            continue
        payload = payload_index.get(key)
        if payload is None:
            continue
        if isinstance(payload, t.ResearchQuestion):
            roots.add(EntityVersionRef(entity_id=key[0], version=key[1]))
            continue
        for nested in _walk_exact_refs(payload):
            if isinstance(nested, EntityVersionRef):
                nested_key = _entity_key(nested)
                if nested_key not in visited:
                    stack.append(nested_key)
    result = frozenset(roots)
    memo[start] = result
    return result


def _exact_reference_is_current_and_fresh(
    snapshot: Snapshot,
    reference: EntityVersionRef | ArtifactDependencyRef | DecisionVersionRef,
) -> bool:
    if isinstance(reference, EntityVersionRef):
        if snapshot.current_entities.get(reference.entity_id) != reference.version:
            return False
        entity = next(
            (
                item
                for item in snapshot.entity_versions
                if _entity_key(item) == _entity_key(reference)
            ),
            None,
        )
        if entity is None:
            return False
        status = snapshot.derived_status.get(reference.entity_id)
        if (
            status is not None
            and entity.entity_type in t.THEORY_PAYLOAD_OWNER_FACETS
            and status.freshness.get(
                t.THEORY_PAYLOAD_OWNER_FACETS[entity.entity_type], "fresh"
            )
            != "fresh"
        ):
            return False
        return True
    if isinstance(reference, ArtifactDependencyRef):
        if snapshot.current_artifacts.get(reference.artifact_id) != reference.version:
            return False
        return any(
            _artifact_key(item) == _artifact_key(reference)
            and item.content_hash == reference.content_hash
            for item in snapshot.artifacts
        )
    return snapshot.current_decisions.get(reference.decision_id) == reference.version


def _historical_entity_refs(payload: t.TheoryPayload) -> frozenset[EntityVersionRef]:
    """Exact audit baselines that remain meaningful after a promoted successor."""

    if isinstance(payload, t.ExampleSuite):
        return frozenset((payload.frozen_prediction_register_ref,))
    if isinstance(payload, t.ImplementationTournament):
        return frozenset(
            (
                *payload.candidate_model_refs,
                *payload.contrast_model_refs,
                *((payload.proposed_selected_model_ref,) if payload.proposed_selected_model_ref else ()),
            )
        )
    if isinstance(payload, t.VAPComparisonRecord):
        return frozenset(
            (
                payload.case_manifest_ref,
                payload.candidate_package_ref,
                payload.gold_package_ref,
            )
        )
    return frozenset()


def _assumption_map_historical_entity_refs(
    snapshot: Snapshot,
    payload: t.AssumptionMap,
    *,
    visiting: set[tuple[str, int]],
    memo: dict[tuple[str, int], bool],
    historical_overrides: Mapping[
        tuple[str, int], frozenset[EntityVersionRef]
    ]
    | None,
) -> frozenset[EntityVersionRef]:
    """Return only the tournament-selected predecessor used as necessity evidence."""

    successor_ref = payload.formal_model_ref
    if not _exact_reference_is_current_and_fresh(snapshot, successor_ref):
        return frozenset()
    entity_index = {
        _entity_key(item): item for item in snapshot.entity_versions
    }
    successor_entity = entity_index.get(_entity_key(successor_ref))
    if (
        successor_entity is None
        or successor_entity.entity_type != "FormalModel"
        or successor_entity.supersedes is None
    ):
        return frozenset()
    predecessor_ref = successor_entity.supersedes
    successor = validate_theory_entity(successor_entity)
    if not isinstance(successor, t.FormalModel):
        return frozenset()
    mapping_ref = payload.formalization_map_ref
    if not _exact_reference_is_current_and_fresh(snapshot, mapping_ref):
        return frozenset()
    mapping_entity = entity_index.get(_entity_key(mapping_ref))
    if mapping_entity is None or mapping_entity.entity_type != "FormalizationMap":
        return frozenset()
    mapping = validate_theory_entity(mapping_entity)
    if (
        not isinstance(mapping, t.FormalizationMap)
        or mapping.formal_model_ref != successor_ref
    ):
        return frozenset()

    selected_by_current_tournament = False
    for entity in snapshot.entity_versions:
        if (
            entity.entity_type != "ImplementationTournament"
            or snapshot.current_entities.get(entity.entity_id) != entity.version
        ):
            continue
        tournament_ref = EntityVersionRef(
            entity_id=entity.entity_id, version=entity.version
        )
        if not _typed_reference_closure_is_current_and_fresh(
            snapshot,
            tournament_ref,
            visiting=visiting,
            memo=memo,
            historical_overrides=historical_overrides,
        ):
            continue
        tournament = validate_theory_entity(entity)
        if (
            isinstance(tournament, t.ImplementationTournament)
            and tournament.proposed_selected_model_ref == predecessor_ref
            and tournament.selected_mechanism_ref
            == successor.selected_mechanism_ref
            and tournament.economic_argument_graph_ref
            == mapping.economic_argument_graph_ref
        ):
            selected_by_current_tournament = True
            break
    if not selected_by_current_tournament:
        return frozenset()

    necessity_evidence_refs = {
        reference
        for assumption in payload.assumptions
        for reference in assumption.necessity_evidence_refs
        if isinstance(reference, EntityVersionRef)
    }
    if predecessor_ref not in necessity_evidence_refs:
        return frozenset()
    return frozenset((predecessor_ref,))


def _typed_reference_closure_is_current_and_fresh(
    snapshot: Snapshot,
    reference: EntityVersionRef,
    *,
    visiting: set[tuple[str, int]] | None = None,
    memo: dict[tuple[str, int], bool] | None = None,
    historical_overrides: Mapping[
        tuple[str, int], frozenset[EntityVersionRef]
    ]
    | None = None,
) -> bool:
    """Treat typed payload refs as an implicit, cycle-safe freshness graph."""

    key = _entity_key(reference)
    visiting = set() if visiting is None else visiting
    memo = {} if memo is None else memo
    if key in memo:
        return memo[key]
    if key in visiting:
        return True
    if not _exact_reference_is_current_and_fresh(snapshot, reference):
        memo[key] = False
        return False
    entity = next(
        (item for item in snapshot.entity_versions if _entity_key(item) == key), None
    )
    if (
        entity is None
        or entity.entity_type not in t.THEORY_PAYLOAD_MODELS
        or not t.is_packed_theory_entity(entity)
    ):
        memo[key] = entity is not None
        return memo[key]
    payload = validate_theory_entity(entity)
    historical_refs = _historical_entity_refs(payload)
    visiting.add(key)
    try:
        if isinstance(payload, t.AssumptionMap):
            historical_refs = historical_refs.union(
                _assumption_map_historical_entity_refs(
                    snapshot,
                    payload,
                    visiting=visiting,
                    memo=memo,
                    historical_overrides=historical_overrides,
                )
            )
        if historical_overrides is not None:
            historical_refs = historical_refs.union(
                historical_overrides.get(key, frozenset())
            )
        for nested in _walk_exact_refs(payload):
            if isinstance(nested, EntityVersionRef):
                if nested in historical_refs:
                    # This edge records the pre-result commitment.  A later
                    # promotion must not rewrite or erase its audit baseline.
                    continue
                if not _typed_reference_closure_is_current_and_fresh(
                    snapshot,
                    nested,
                    visiting=visiting,
                    memo=memo,
                    historical_overrides=historical_overrides,
                ):
                    memo[key] = False
                    return False
            elif isinstance(nested, (ArtifactDependencyRef, DecisionVersionRef)):
                if not _exact_reference_is_current_and_fresh(snapshot, nested):
                    memo[key] = False
                    return False
    finally:
        visiting.remove(key)
    memo[key] = True
    return True


def is_falsified_verification_repair_root(
    snapshot: Snapshot,
    reference: EntityVersionRef,
    *,
    trigger_bundle_ref: EntityVersionRef | None = None,
) -> bool:
    """Return whether one exact current proof was invalidated by verification.

    This is a narrow entry-time classification, not a new repair mode.  It
    promotes only a current ProofObligation named by a current
    VerificationBundle whose current VerificationRecord is falsified and whose
    current ``challenges`` relation points back to that exact obligation.
    """

    if snapshot.current_entities.get(reference.entity_id) != reference.version:
        return False
    exact = {
        _entity_key(entity): entity for entity in snapshot.entity_versions
    }
    target_entity = exact.get(_entity_key(reference))
    if target_entity is None or target_entity.entity_type != "ProofObligation":
        return False
    target = validate_theory_entity(target_entity)
    if not isinstance(target, t.ProofObligation):
        return False

    current_relations = {
        (relation.relation_id, relation.version): relation
        for relation in snapshot.relation_versions
        if snapshot.current_relations.get(relation.relation_id) == relation.version
    }
    for bundle_entity in snapshot.entity_versions:
        if (
            bundle_entity.entity_type != "VerificationBundle"
            or snapshot.current_entities.get(bundle_entity.entity_id)
            != bundle_entity.version
            or (
                trigger_bundle_ref is not None
                and (
                    bundle_entity.entity_id != trigger_bundle_ref.entity_id
                    or bundle_entity.version != trigger_bundle_ref.version
                )
            )
        ):
            continue
        bundle = validate_theory_entity(bundle_entity)
        if (
            not isinstance(bundle, t.VerificationBundle)
            or reference not in bundle.proof_obligation_refs
            or bundle.claim_graph_ref != target.claim_graph_ref
        ):
            continue
        for record_ref in bundle.verification_record_refs:
            if snapshot.current_entities.get(record_ref.entity_id) != record_ref.version:
                continue
            record_entity = exact.get(_entity_key(record_ref))
            if record_entity is None:
                continue
            record = validate_theory_entity(record_entity)
            if (
                not isinstance(record, t.VerificationRecord)
                or record.outcome != "falsified"
                or record.obligation_ref != reference
                or record.claim_graph_ref != bundle.claim_graph_ref
            ):
                continue
            if any(
                relation.relation_type == "challenges"
                and relation.source == record_ref
                and relation.target == reference
                for relation in current_relations.values()
            ):
                return True
    return False


def _g3_historical_reference_overrides(
    snapshot: Snapshot,
    dossier_entity: EntityVersion,
    dossier: t.GateDossier,
) -> dict[tuple[str, int], frozenset[EntityVersionRef]]:
    """Classify one exact tournament predecessor as G3 audit evidence.

    A formal-base promotion supersedes the model selected by the implementation
    tournament.  The tournament remains an immutable audit baseline, and a G3
    dossier may expose that exact predecessor alongside its promoted successor.
    This exception is deliberately narrower than general staleness:

    * the predecessor must be the current tournament's exact selection;
    * the dossier must expose both that predecessor and its exact current
      successor;
    * the current FormalizationMap and AssumptionMap must bind the successor;
    * only the dossier and AssumptionRecord necessity evidence may retain the
      predecessor.

    Every other reference in the G3 closure keeps the ordinary current/fresh
    requirement.
    """

    if dossier.gate_kind != "G3_formal_base":
        return {}

    entity_index = {
        _entity_key(item): item for item in snapshot.entity_versions
    }
    ordered_refs = set(dossier.ordered_object_refs)
    tournament_entries: list[
        tuple[EntityVersionRef, t.ImplementationTournament]
    ] = []
    for reference in dossier.ordered_object_refs:
        entity = entity_index.get(_entity_key(reference))
        if entity is None or entity.entity_type != "ImplementationTournament":
            continue
        payload = validate_theory_entity(entity)
        if isinstance(payload, t.ImplementationTournament):
            tournament_entries.append((reference, payload))
    if len(tournament_entries) != 1:
        return {}

    tournament_ref, tournament = tournament_entries[0]
    if not _typed_reference_closure_is_current_and_fresh(
        snapshot, tournament_ref
    ):
        return {}
    predecessor_ref = tournament.proposed_selected_model_ref
    if predecessor_ref is None or predecessor_ref not in ordered_refs:
        return {}

    successor_ref = EntityVersionRef(
        entity_id=predecessor_ref.entity_id,
        version=predecessor_ref.version + 1,
    )
    if (
        snapshot.current_entities.get(predecessor_ref.entity_id)
        != successor_ref.version
        or successor_ref not in ordered_refs
    ):
        return {}
    successor_entity = entity_index.get(_entity_key(successor_ref))
    if (
        successor_entity is None
        or successor_entity.entity_type != "FormalModel"
        or successor_entity.supersedes != predecessor_ref
    ):
        return {}
    successor = validate_theory_entity(successor_entity)
    if (
        not isinstance(successor, t.FormalModel)
        or successor.question_ref != dossier.research_question_ref
    ):
        return {}

    mapping_entries: list[
        tuple[EntityVersionRef, t.FormalizationMap]
    ] = []
    for reference in dossier.ordered_object_refs:
        entity = entity_index.get(_entity_key(reference))
        if entity is None or entity.entity_type != "FormalizationMap":
            continue
        payload = validate_theory_entity(entity)
        if (
            isinstance(payload, t.FormalizationMap)
            and payload.formal_model_ref == successor_ref
            and _exact_reference_is_current_and_fresh(snapshot, reference)
        ):
            mapping_entries.append((reference, payload))
    if len(mapping_entries) != 1:
        return {}
    mapping_ref, _ = mapping_entries[0]

    assumption_entries: list[
        tuple[EntityVersionRef, t.AssumptionMap]
    ] = []
    for reference in dossier.ordered_object_refs:
        entity = entity_index.get(_entity_key(reference))
        if entity is None or entity.entity_type != "AssumptionMap":
            continue
        payload = validate_theory_entity(entity)
        if (
            isinstance(payload, t.AssumptionMap)
            and payload.formal_model_ref == successor_ref
            and payload.formalization_map_ref == mapping_ref
            and _exact_reference_is_current_and_fresh(snapshot, reference)
        ):
            assumption_entries.append((reference, payload))
    if len(assumption_entries) != 1:
        return {}

    overrides = {
        _entity_key(dossier_entity): frozenset((predecessor_ref,))
    }
    return overrides


def _gate_dossier_index(
    snapshot: Snapshot,
) -> dict[str, tuple[EntityVersion, t.GateDossier]]:
    result: dict[str, tuple[EntityVersion, t.GateDossier]] = {}
    for entity in snapshot.entity_versions:
        if (
            entity.entity_type != "GateDossier"
            or not t.is_packed_theory_entity(entity)
            or snapshot.current_entities.get(entity.entity_id) != entity.version
        ):
            continue
        payload = validate_theory_entity(entity)
        if isinstance(payload, t.GateDossier):
            result[entity.entity_id] = (entity, payload)
    return result


def _gate_dossier_is_fresh(
    snapshot: Snapshot,
    dossier_entity: EntityVersion,
    dossier: t.GateDossier,
) -> bool:
    dossier_ref = EntityVersionRef(
        entity_id=dossier_entity.entity_id, version=dossier_entity.version
    )
    historical_overrides = _g3_historical_reference_overrides(
        snapshot, dossier_entity, dossier
    )
    if not _typed_reference_closure_is_current_and_fresh(
        snapshot,
        dossier_ref,
        historical_overrides=historical_overrides,
    ):
        return False
    return True


def has_current_fresh_g1_decomposition_package(
    snapshot: Snapshot,
    *,
    research_question_ref: EntityVersionRef,
    benchmark_set_ref: EntityVersionRef,
) -> bool:
    """Return whether automatic discovery already completed this exact scope.

    A direct, explicitly requested decomposition remains a legal scientific
    operation.  Machine navigation uses this predicate only to avoid opening
    the same upstream route indefinitely after one current PrimitiveGraph and
    its exact current pre-audit G1 dossier already exist.  An authorized
    upstream repair makes their exact-reference closure stale and re-enables
    decomposition.  A post-audit replacement dossier cannot close this route.
    """

    if not _exact_reference_is_current_and_fresh(
        snapshot, research_question_ref
    ) or not _exact_reference_is_current_and_fresh(snapshot, benchmark_set_ref):
        return False
    entity_index = {_entity_key(item): item for item in snapshot.entity_versions}
    payload_index = {
        _entity_key(item): validate_theory_entity(item)
        for item in snapshot.entity_versions
        if item.entity_type in t.THEORY_PAYLOAD_MODELS
        and t.is_packed_theory_entity(item)
    }
    graph_refs: list[EntityVersionRef] = []
    for key, payload in payload_index.items():
        if not isinstance(payload, t.PrimitiveGraph):
            continue
        graph_ref = EntityVersionRef(entity_id=key[0], version=key[1])
        if (
            payload.question_ref == research_question_ref
            and payload.benchmark_set_ref == benchmark_set_ref
            and _typed_reference_closure_is_current_and_fresh(snapshot, graph_ref)
        ):
            graph_refs.append(graph_ref)
    for graph_ref in graph_refs:
        required_refs = {
            research_question_ref,
            benchmark_set_ref,
            graph_ref,
        }
        for key, payload in payload_index.items():
            if not isinstance(payload, t.GateDossier):
                continue
            dossier_entity = entity_index[key]
            if any(
                (
                    referenced := entity_index.get(_entity_key(reference))
                ) is not None
                and referenced.entity_type == "FramingQualityBundle"
                for reference in payload.ordered_object_refs
            ):
                continue
            if (
                payload.gate_kind == "G1_question_benchmark"
                and payload.research_question_ref == research_question_ref
                and required_refs.issubset(set(payload.ordered_object_refs))
                and _gate_dossier_is_fresh(snapshot, dossier_entity, payload)
            ):
                return True
    return False


def _effective_approved_gates(
    snapshot: Snapshot,
) -> dict[str, list[tuple[Decision, EntityVersion, t.GateDossier]]]:
    decisions = {_decision_key(item): item for item in snapshot.decisions}
    dossiers = _gate_dossier_index(snapshot)
    result: dict[str, list[tuple[Decision, EntityVersion, t.GateDossier]]] = {}
    for reference in snapshot.effective_decisions.values():
        decision = decisions.get(_decision_key(reference))
        if (
            decision is None
            or decision.decision_kind not in _GATE_RANK
            or decision.status != "confirmed"
            or decision.machine_outcome != "approve"
            or decision.selected_option != "approve"
            or decision.decider.kind != "human"
        ):
            continue
        cited = [dossiers[item] for item in decision.evidence_refs if item in dossiers]
        if len(cited) != 1:
            continue
        dossier_entity, dossier = cited[0]
        if (
            dossier.gate_kind != decision.decision_kind
            or decision.subject_ref != dossier_entity.entity_id
            or decision.scope_ref != dossier.research_question_ref.entity_id
            or not _gate_dossier_is_fresh(snapshot, dossier_entity, dossier)
        ):
            continue
        result.setdefault(decision.decision_kind, []).append(
            (decision, dossier_entity, dossier)
        )
    return result


def _validate_requirement_counts(
    requirements: Iterable[object],
    counts: Mapping[str, int],
    *,
    type_field: str,
    label: str,
) -> None:
    for requirement in requirements:
        object_type = getattr(requirement, type_field)
        count = counts.get(object_type, 0)
        if count < requirement.min_count:
            raise TheoryValidationError(
                f"{label} requires at least {requirement.min_count} {object_type}, got {count}"
            )
        if requirement.max_count is not None and count > requirement.max_count:
            raise TheoryValidationError(
                f"{label} permits at most {requirement.max_count} {object_type}, got {count}"
            )


def _validate_phase2_route_entry_refs(
    snapshot: Snapshot,
    route_spec: RouteSpecV2,
    input_refs: Iterable[EntityVersionRef],
    *,
    allow_fresh_repair: bool = False,
) -> TheoryRouteEntryReport:
    if route_spec.entry_validator_id != "theory_route_entry.v1":
        raise TheoryValidationError("unknown or missing Phase 2 route entry validator")
    references = tuple(input_refs)
    reference_keys = tuple(_entity_key(item) for item in references)
    if len(set(reference_keys)) != len(reference_keys):
        raise TheoryValidationError("route input evidence repeats an exact entity ref")
    entity_index = {_entity_key(item): item for item in snapshot.entity_versions}
    payload_index = {
        _entity_key(item): validate_theory_entity(item)
        for item in snapshot.entity_versions
        if item.entity_type in t.THEORY_PAYLOAD_MODELS
        and t.is_packed_theory_entity(item)
    }
    typed_inputs: list[tuple[EntityVersionRef, EntityVersion]] = []
    counts: dict[str, int] = {}
    is_repair = route_spec.route_id == "repair.dependency"
    for reference in references:
        entity = entity_index.get(_entity_key(reference))
        if entity is None:
            raise TheoryValidationError("route input evidence contains an unresolved entity")
        if is_repair:
            if snapshot.current_entities.get(reference.entity_id) != reference.version:
                raise TheoryValidationError(
                    "repair input must name the exact current version of its stale root"
                )
        elif not _exact_reference_is_current_and_fresh(snapshot, reference):
            raise TheoryValidationError(
                f"route input {reference.entity_id}@{reference.version} is not current and fresh"
            )
        if (
            entity.entity_type in t.THEORY_PAYLOAD_MODELS
            and t.is_packed_theory_entity(entity)
        ):
            if not is_repair and not _typed_reference_closure_is_current_and_fresh(
                snapshot, reference
            ):
                raise TheoryValidationError(
                    f"route input {reference.entity_id}@{reference.version} has a stale exact dependency"
                )
            typed_inputs.append((reference, entity))
            counts[entity.entity_type] = counts.get(entity.entity_type, 0) + 1
    _validate_requirement_counts(
        route_spec.required_input_entities,
        counts,
        type_field="entity_type",
        label=(
            f"route {route_spec.route_id} input; copy exact WorkPacket.focus_refs "
            "into Transaction.evidence_refs"
        ),
    )

    root_memo: dict[tuple[str, int], frozenset[EntityVersionRef]] = {}
    input_root_sets = [
        _research_question_roots(
            reference, entity_index, payload_index, memo=root_memo
        )
        for reference, _ in typed_inputs
    ]
    if any(len(roots) != 1 for roots in input_root_sets):
        raise TheoryValidationError(
            "every typed route input must resolve to one exact ResearchQuestion"
        )
    input_roots = {next(iter(roots)) for roots in input_root_sets}
    if len(input_roots) > 1:
        raise TheoryValidationError(
            "route inputs cannot mix different ResearchQuestion scopes"
        )
    root = next(iter(input_roots), None)

    if is_repair:
        if route_spec.route_version >= 5 and any(
            entity.entity_type not in route_spec.allowed_entity_types
            for _, entity in typed_inputs
        ):
            raise TheoryValidationError(
                "v5 repair target type is not mutable by repair.dependency"
            )
        stale_inputs = [
            reference
            for reference, _ in typed_inputs
            if (
                not _typed_reference_closure_is_current_and_fresh(
                    snapshot, reference
                )
                or is_falsified_verification_repair_root(snapshot, reference)
            )
        ]
        valid_root_count = len(stale_inputs) == 1 or (
            allow_fresh_repair and len(stale_inputs) == 0
        )
        if len(references) != 1 or len(typed_inputs) != 1 or not valid_root_count:
            raise TheoryValidationError(
                "repair.dependency requires exactly one typed stale root"
                if not allow_fresh_repair
                else "v5 repair requires exactly one typed stale or authorized fresh root"
            )

    if route_spec.route_id == "validate.argument_package":
        brief_refs = [
            reference
            for reference, entity in typed_inputs
            if entity.entity_type == "PreResultBrief"
        ]
        if len(brief_refs) > 1:
            raise TheoryValidationError(
                "argument validation can bind at most one blind PreResultBrief"
            )
        if brief_refs:
            brief = payload_index[_entity_key(brief_refs[0])]
            assert isinstance(brief, t.PreResultBrief)
            lock_id = f"candidate.lock.{brief.attempt_id}"
            if lock_id in snapshot.current_artifacts:
                raise TheoryValidationError(
                    "the blind attempt already has an immutable candidate lock"
                )
            if any(
                isinstance(payload, t.VAPComparisonRecord)
                and payload.attempt_id == brief.attempt_id
                and snapshot.current_entities.get(key[0]) == key[1]
                for key, payload in payload_index.items()
            ):
                raise TheoryValidationError(
                    "evaluator feedback permanently closes this blind attempt"
                )

    gate_refs: list[DecisionVersionRef] = []
    selected_gate_dossiers: dict[str, t.GateDossier] = {}
    if route_spec.required_gate_kinds:
        if root is None or not _exact_reference_is_current_and_fresh(snapshot, root):
            raise TheoryValidationError(
                "route is missing required current exact ResearchQuestion root"
            )
        approved = _effective_approved_gates(snapshot)
        highest_rank = max(_GATE_RANK[kind] for kind in route_spec.required_gate_kinds)
        latest_prior = ""
        for kind in _GATE_ORDER[: highest_rank + 1]:
            matching = [
                item
                for item in approved.get(kind, ())
                if item[2].research_question_ref == root
            ]
            if not matching:
                raise TheoryValidationError(
                    f"route is missing required fresh approved gate {kind} in its question scope"
                )
            selected = max(matching, key=lambda item: item[0].decided_at)
            if latest_prior and selected[0].decided_at <= latest_prior:
                raise TheoryValidationError(
                    "the current gate chain is stale after an upstream reapproval"
                )
            latest_prior = selected[0].decided_at
            selected_gate_dossiers[kind] = selected[2]
            gate_refs.append(
                DecisionVersionRef(
                    decision_id=selected[0].decision_id,
                    version=selected[0].version,
                )
            )

    if route_spec.route_id == "discover.claims_and_boundaries":
        inputs_by_type: dict[
            str, list[tuple[EntityVersionRef, t.TheoryPayload]]
        ] = {}
        for reference, entity in typed_inputs:
            payload = payload_index[_entity_key(reference)]
            inputs_by_type.setdefault(entity.entity_type, []).append(
                (reference, payload)
            )

        def exact_input(
            entity_type: str,
        ) -> tuple[EntityVersionRef, t.TheoryPayload]:
            entries = inputs_by_type.get(entity_type, ())
            if len(entries) != 1:
                raise TheoryValidationError(
                    "claim discovery requires one exact "
                    f"{entity_type} in its approved formal-base focus"
                )
            return entries[0]

        question_ref, question = exact_input("ResearchQuestion")
        mechanism_ref, mechanism = exact_input("MechanismHypothesis")
        argument_ref, argument = exact_input("EconomicArgumentGraph")
        formal_model_ref, formal_model = exact_input("FormalModel")
        formalization_ref, formalization = exact_input("FormalizationMap")
        assumptions_ref, assumptions = exact_input("AssumptionMap")
        if (
            not isinstance(question, t.ResearchQuestion)
            or not isinstance(mechanism, t.MechanismHypothesis)
            or not isinstance(argument, t.EconomicArgumentGraph)
            or not isinstance(formal_model, t.FormalModel)
            or not isinstance(formalization, t.FormalizationMap)
            or not isinstance(assumptions, t.AssumptionMap)
            or question_ref != root
            or formal_model.question_ref != question_ref
            or formal_model.selected_mechanism_ref != mechanism_ref
            or argument.selected_mechanism_ref != mechanism_ref
            or argument.primitive_graph_ref != formal_model.primitive_graph_ref
            or formalization.economic_argument_graph_ref != argument_ref
            or formalization.formal_model_ref != formal_model_ref
            or assumptions.formal_model_ref != formal_model_ref
            or assumptions.formalization_map_ref != formalization_ref
        ):
            raise TheoryValidationError(
                "claim discovery inputs do not form one exact approved "
                "question-mechanism-formal-base chain"
            )

        g2_dossier = selected_gate_dossiers.get("G2_mechanism")
        g3_dossier = selected_gate_dossiers.get("G3_formal_base")
        if (
            g2_dossier is None
            or not {mechanism_ref, argument_ref}.issubset(
                set(g2_dossier.ordered_object_refs)
            )
        ):
            raise TheoryValidationError(
                "claim discovery mechanism and economic argument are not "
                "the exact G2-approved chain"
            )
        if (
            g3_dossier is None
            or not {
                formal_model_ref,
                formalization_ref,
                assumptions_ref,
            }.issubset(set(g3_dossier.ordered_object_refs))
        ):
            raise TheoryValidationError(
                "claim discovery formal model, mapping, and assumptions are "
                "not the exact G3-approved formal base"
            )
    elif route_spec.route_id == "verify.claims_proofs_and_interpretation":
        verification_inputs: dict[
            str, list[tuple[EntityVersionRef, t.TheoryPayload]]
        ] = {}
        for reference, entity in typed_inputs:
            payload = payload_index[_entity_key(reference)]
            verification_inputs.setdefault(entity.entity_type, []).append(
                (reference, payload)
            )

        def exact_verification_input(
            entity_type: str,
        ) -> tuple[EntityVersionRef, t.TheoryPayload]:
            entries = verification_inputs.get(entity_type, ())
            if len(entries) != 1:
                raise TheoryValidationError(
                    "claim verification requires one exact "
                    f"{entity_type} in its retained obligation closure"
                )
            return entries[0]

        question_ref, question = exact_verification_input(
            "ResearchQuestion"
        )
        graph_ref, graph = exact_verification_input("ClaimGraph")
        formal_model_ref, formal_model = exact_verification_input(
            "FormalModel"
        )
        assumptions_ref, assumptions = exact_verification_input(
            "AssumptionMap"
        )
        obligation_entries = verification_inputs.get("ProofObligation", ())
        if (
            not isinstance(question, t.ResearchQuestion)
            or not isinstance(graph, t.ClaimGraph)
            or not isinstance(formal_model, t.FormalModel)
            or not isinstance(assumptions, t.AssumptionMap)
            or question_ref != root
            or formal_model.question_ref != question_ref
            or graph.formal_model_ref != formal_model_ref
            or graph.assumption_map_ref != assumptions_ref
        ):
            raise TheoryValidationError(
                "claim verification inputs do not bind one exact approved "
                "question, formal model, assumption map, and ClaimGraph"
            )
        expected_obligation_refs = {
            reference
            for claim in graph.claims
            for reference in claim.proof_obligation_refs
        }
        input_obligation_refs = {
            reference for reference, _ in obligation_entries
        }
        if input_obligation_refs != expected_obligation_refs:
            raise TheoryValidationError(
                "claim verification inputs must contain every and only "
                "retained ClaimGraph ProofObligation"
            )
        claims_by_id = {claim.claim_id: claim for claim in graph.claims}
        for obligation_ref, obligation in obligation_entries:
            if not isinstance(obligation, t.ProofObligation):
                raise TheoryValidationError(
                    "claim verification input contains a non-obligation payload"
                )
            claim = claims_by_id.get(obligation.claim_id)
            if (
                obligation.claim_graph_ref != graph_ref
                or claim is None
                or obligation_ref not in claim.proof_obligation_refs
                or not set(obligation.assumption_ids).issubset(
                    set(claim.assumption_ids)
                )
            ):
                raise TheoryValidationError(
                    "claim verification obligation does not bind its exact "
                    "ClaimGraph, claim, and assumptions"
                )
        g3_dossier = selected_gate_dossiers.get("G3_formal_base")
        if (
            g3_dossier is None
            or formal_model_ref not in g3_dossier.ordered_object_refs
        ):
            raise TheoryValidationError(
                "claim verification model is not the exact G3-approved "
                "formal base"
            )
    elif route_spec.route_id == "audit.assumptions_generality_and_absorption":
        audit_inputs: dict[
            str, list[tuple[EntityVersionRef, t.TheoryPayload]]
        ] = {}
        for reference, entity in typed_inputs:
            payload = payload_index[_entity_key(reference)]
            audit_inputs.setdefault(entity.entity_type, []).append(
                (reference, payload)
            )

        def exact_audit_input(
            entity_type: str,
        ) -> tuple[EntityVersionRef, t.TheoryPayload]:
            entries = audit_inputs.get(entity_type, ())
            if len(entries) != 1:
                raise TheoryValidationError(
                    "assumption audit requires one exact "
                    f"{entity_type} in its verified claim closure"
                )
            return entries[0]

        question_ref, question = exact_audit_input("ResearchQuestion")
        graph_ref, graph = exact_audit_input("ClaimGraph")
        formal_model_ref, formal_model = exact_audit_input("FormalModel")
        assumptions_ref, assumptions = exact_audit_input("AssumptionMap")
        _, bundle = exact_audit_input("VerificationBundle")
        if (
            not isinstance(question, t.ResearchQuestion)
            or not isinstance(graph, t.ClaimGraph)
            or not isinstance(formal_model, t.FormalModel)
            or not isinstance(assumptions, t.AssumptionMap)
            or not isinstance(bundle, t.VerificationBundle)
            or question_ref != root
            or formal_model.question_ref != question_ref
            or graph.formal_model_ref != formal_model_ref
            or graph.assumption_map_ref != assumptions_ref
            or bundle.claim_graph_ref != graph_ref
        ):
            raise TheoryValidationError(
                "assumption audit inputs do not bind one exact verified "
                "question, formal model, assumption map, ClaimGraph, and "
                "VerificationBundle"
            )
        g3_dossier = selected_gate_dossiers.get("G3_formal_base")
        if (
            g3_dossier is None
            or not {formal_model_ref, assumptions_ref}.issubset(
                set(g3_dossier.ordered_object_refs)
            )
        ):
            raise TheoryValidationError(
                "assumption audit model and assumptions are not the exact "
                "G3-approved formal base"
            )
    return TheoryRouteEntryReport(
        research_question_ref=root,
        input_entity_refs=tuple(reference for reference, _ in typed_inputs),
        gate_decision_refs=tuple(gate_refs),
    )


def _validate_evaluation_route_entry_refs(
    snapshot: Snapshot,
    route_spec: RouteSpecV2,
    input_refs: Iterable[EntityVersionRef],
    *,
    actor: Actor,
) -> TheoryRouteEntryReport:
    if route_spec.entry_validator_id != "evaluation_route_entry.v1":
        raise TheoryValidationError("unknown evaluation route entry validator")
    references = tuple(input_refs)
    if len({_entity_key(item) for item in references}) != len(references):
        raise TheoryValidationError("evaluation focus repeats an exact entity ref")
    entity_index = {_entity_key(item): item for item in snapshot.entity_versions}
    payload_index = {
        _entity_key(item): validate_theory_entity(item)
        for item in snapshot.entity_versions
        if item.entity_type in t.THEORY_PAYLOAD_MODELS
        and t.is_packed_theory_entity(item)
    }
    counts: dict[str, int] = {}
    for reference in references:
        entity = entity_index.get(_entity_key(reference))
        if entity is None or snapshot.current_entities.get(reference.entity_id) != reference.version:
            raise TheoryValidationError("evaluation focus must contain exact current entities")
        if (
            entity.entity_type not in t.THEORY_PAYLOAD_MODELS
            or not t.is_packed_theory_entity(entity)
            or not _typed_reference_closure_is_current_and_fresh(snapshot, reference)
        ):
            raise TheoryValidationError(
                "evaluation focus contains an untyped or stale exact dependency"
            )
        counts[entity.entity_type] = counts.get(entity.entity_type, 0) + 1
    _validate_requirement_counts(
        route_spec.required_input_entities,
        counts,
        type_field="entity_type",
        label=f"route {route_spec.route_id} input",
    )
    declared_types = {item.entity_type for item in route_spec.required_input_entities}
    if set(counts).difference(declared_types):
        raise TheoryValidationError("evaluation focus contains an undeclared entity type")

    effective_refs = {
        (item.decision_id, item.version) for item in snapshot.effective_decisions.values()
    }
    current_payloads = {
        key: payload
        for key, payload in payload_index.items()
        if snapshot.current_entities.get(key[0]) == key[1]
    }

    def effective_freeze(
        *, brief_ref: EntityVersionRef, attempt_id: str
    ) -> tuple[Decision, DecisionVersionRef]:
        matching = [
            decision
            for decision in snapshot.decisions
            if _decision_key(decision) in effective_refs
            and decision.decision_kind == "theory_mode"
            and decision.status == "confirmed"
            and decision.decider.kind == "human"
            and decision.selected_option == "freeze"
            and decision.subject_ref == brief_ref.entity_id
            and decision.scope_ref == attempt_id
            and decision.decided_at > entity_index[_entity_key(brief_ref)].created_at
        ]
        if len(matching) != 1:
            raise TheoryValidationError(
                "evaluation route requires one effective human implementation freeze"
            )
        decision = matching[0]
        return decision, DecisionVersionRef(
            decision_id=decision.decision_id, version=decision.version
        )

    if route_spec.route_id == "prepare.blind_case":
        brief_entries = [
            (reference, payload_index[_entity_key(reference)])
            for reference in references
            if entity_index[_entity_key(reference)].entity_type == "PreResultBrief"
        ]
        package_entries = [
            (reference, payload_index[_entity_key(reference)])
            for reference in references
            if entity_index[_entity_key(reference)].entity_type
            == "ValidatedArgumentPackage"
        ]
        if len(brief_entries) != 2 or len(package_entries) != 1:
            raise TheoryValidationError(
                "blind case preparation requires two briefs and one gold package"
            )
        attempts = {
            payload.attempt_id
            for _, payload in brief_entries
            if isinstance(payload, t.PreResultBrief)
        }
        if len(attempts) != 1:
            raise TheoryValidationError("base and transformed briefs must share one attempt")
        attempt_id = next(iter(attempts))
        freeze_matches: list[tuple[EntityVersionRef, Decision, DecisionVersionRef]] = []
        for brief_ref, _ in brief_entries:
            try:
                decision, decision_ref = effective_freeze(
                    brief_ref=brief_ref, attempt_id=attempt_id
                )
            except TheoryValidationError:
                continue
            freeze_matches.append((brief_ref, decision, decision_ref))
        if len(freeze_matches) != 1:
            raise TheoryValidationError(
                "implementation freeze must identify exactly the transformed brief"
            )
        transformed_ref = freeze_matches[0][0]
        base_entries = [item for item in brief_entries if item[0] != transformed_ref]
        gold = package_entries[0][1]
        if (
            len(base_entries) != 1
            or not isinstance(base_entries[0][1], t.PreResultBrief)
            or not isinstance(gold, t.ValidatedArgumentPackage)
            or gold.question_ref != base_entries[0][1].question_ref
        ):
            raise TheoryValidationError(
                "gold package must bind the exact untransformed base brief"
            )
        if any(
            (
                isinstance(payload, t.BlindCaseManifest)
                and payload.attempt_id == attempt_id
            )
            or (
                isinstance(payload, t.TransformedVariantManifest)
                and payload.attempt_id == attempt_id
            )
            for payload in current_payloads.values()
        ):
            raise TheoryValidationError("blind attempt has already been prepared")
        return TheoryRouteEntryReport(
            research_question_ref=None,
            input_entity_refs=references,
            gate_decision_refs=(freeze_matches[0][2],),
        )

    if route_spec.route_id == "evaluate.blind_argument_package":
        by_type: dict[str, list[tuple[EntityVersionRef, t.TheoryPayload]]] = {}
        for reference in references:
            entity_type = entity_index[_entity_key(reference)].entity_type
            by_type.setdefault(entity_type, []).append(
                (reference, payload_index[_entity_key(reference)])
            )
        manifest_ref, manifest = by_type["BlindCaseManifest"][0]
        _, variant = by_type["TransformedVariantManifest"][0]
        brief_ref, brief = by_type["PreResultBrief"][0]
        packages = by_type["ValidatedArgumentPackage"]
        if (
            not isinstance(manifest, t.BlindCaseManifest)
            or not isinstance(variant, t.TransformedVariantManifest)
            or not isinstance(brief, t.PreResultBrief)
            or variant.base_case_manifest_ref != manifest_ref
            or variant.transformed_brief_ref != brief_ref
            or variant.attempt_id != manifest.attempt_id
            or brief.attempt_id != manifest.attempt_id
        ):
            raise TheoryValidationError(
                "evaluation inputs do not bind one exact transformed blind attempt"
            )
        package_by_ref = {reference: payload for reference, payload in packages}
        gold = package_by_ref.get(manifest.gold_package_ref)
        candidates = [
            (reference, payload)
            for reference, payload in packages
            if reference != manifest.gold_package_ref
        ]
        if len(candidates) != 1 or not isinstance(gold, t.ValidatedArgumentPackage):
            raise TheoryValidationError("evaluation requires exact candidate and gold packages")
        candidate_ref, candidate = candidates[0]
        if (
            not isinstance(candidate, t.ValidatedArgumentPackage)
            or candidate.release_mode != "evaluation_only"
            or candidate.evaluation_attempt_id != manifest.attempt_id
            or candidate.pre_result_brief_ref != brief_ref
            or candidate.generator_actor is None
        ):
            raise TheoryValidationError(
                "candidate package lacks exact sealed-attempt metadata"
            )
        if candidate.generator_actor == actor:
            raise TheoryValidationError(
                "evaluator independence: candidate generator cannot begin the "
                "evaluator route or read its sealed context"
            )
        _, freeze_ref = effective_freeze(
            brief_ref=brief_ref, attempt_id=manifest.attempt_id
        )
        if variant.implementation_freeze_ref != freeze_ref:
            raise TheoryValidationError(
                "transformed variant cites a different implementation freeze"
            )
        lock_id = f"candidate.lock.{manifest.attempt_id}"
        lock_version = snapshot.current_artifacts.get(lock_id)
        lock = next(
            (
                item
                for item in snapshot.artifacts
                if item.artifact_id == lock_id and item.version == lock_version
            ),
            None,
        )
        candidate_entity = entity_index[_entity_key(candidate_ref)]
        if (
            lock is None
            or lock.version != 1
            or lock.supersedes is not None
            or lock.media_type
            != "application/vnd.econ-theorist.candidate-lock+json"
            or lock.content_hash
            != sha256_digest(canonical_json_bytes(candidate_entity))
        ):
            raise TheoryValidationError(
                "evaluation requires a prior exact candidate-lock artifact"
            )
        if any(
            isinstance(payload, t.VAPComparisonRecord)
            and payload.attempt_id == manifest.attempt_id
            for payload in current_payloads.values()
        ):
            raise TheoryValidationError("blind attempt already has terminal evaluator feedback")
        return TheoryRouteEntryReport(
            research_question_ref=None,
            input_entity_refs=references,
            gate_decision_refs=(freeze_ref,),
        )

    raise TheoryValidationError("unknown evaluation route")


def _validate_route_entry_refs(
    snapshot: Snapshot,
    route_spec: RouteSpecV2,
    input_refs: Iterable[EntityVersionRef],
    *,
    actor: Actor,
    allow_fresh_repair: bool = False,
) -> TheoryRouteEntryReport:
    if route_spec.entry_validator_id == "evaluation_route_entry.v1":
        return _validate_evaluation_route_entry_refs(
            snapshot, route_spec, input_refs, actor=actor
        )
    return _validate_phase2_route_entry_refs(
        snapshot,
        route_spec,
        input_refs,
        allow_fresh_repair=allow_fresh_repair,
    )


def validate_phase2_route_entry(
    snapshot: Snapshot,
    route_spec: RouteSpecV2,
    focus_entity_ids: Iterable[str],
    *,
    actor: Actor,
    allow_fresh_repair: bool = False,
) -> TheoryRouteEntryReport:
    """Validate begin-time entry against exact current focus entities."""

    focus_ids = tuple(focus_entity_ids)
    if len(set(focus_ids)) != len(focus_ids):
        raise TheoryValidationError("route focus_entity_ids must not repeat")
    current_entities = {
        item.entity_id: item
        for item in snapshot.entity_versions
        if snapshot.current_entities.get(item.entity_id) == item.version
    }
    missing = [entity_id for entity_id in focus_ids if entity_id not in current_entities]
    if missing:
        raise TheoryValidationError(
            "route focus contains unknown current entities: " + ", ".join(sorted(missing))
        )
    return _validate_route_entry_refs(
        snapshot,
        route_spec,
        (
            EntityVersionRef(entity_id=entity_id, version=current_entities[entity_id].version)
            for entity_id in focus_ids
        ),
        actor=actor,
        allow_fresh_repair=allow_fresh_repair,
    )


def validate_phase2_human_gate_transaction(
    snapshot: Snapshot, transaction: Transaction
) -> None:
    """Check a newly recorded human gate without making revocation impossible."""

    if transaction.origin != "human_decision":
        raise TheoryValidationError("gate validation requires a human_decision transaction")
    prior_gates = _effective_approved_gates(snapshot)
    for operation in transaction.operations:
        if not isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp)):
            continue
        decision = operation.decision
        if decision.decision_kind not in _GATE_RANK:
            continue
        if decision.status != "confirmed" or decision.machine_outcome != "approve":
            continue
        cited = [
            item
            for item in _gate_dossier_index(snapshot).values()
            if item[0].entity_id in decision.evidence_refs
        ]
        if len(cited) != 1:
            raise TheoryValidationError(
                "an approving G1-G5 Decision must cite one current typed GateDossier"
            )
        dossier_entity, dossier = cited[0]
        if not _gate_dossier_is_fresh(snapshot, dossier_entity, dossier):
            raise TheoryValidationError("an approving gate cannot use a stale dossier")
        if snapshot.current_entities.get(
            dossier.research_question_ref.entity_id
        ) != dossier.research_question_ref.version:
            raise TheoryValidationError("an approving gate cannot govern a stale question")
        rank = _GATE_RANK[decision.decision_kind]
        for prior_kind in _GATE_ORDER[:rank]:
            matching = [
                item
                for item in prior_gates.get(prior_kind, ())
                if item[2].research_question_ref == dossier.research_question_ref
                and item[0].decided_at < decision.decided_at
            ]
            if not matching:
                raise TheoryValidationError(
                    f"{decision.decision_kind} approval requires fresh prior {prior_kind}"
                )


def _validate_phase2_route_exit_semantics(
    route_spec: RouteSpecV2,
    entry_report: TheoryRouteEntryReport,
    produced_entity_refs: tuple[EntityVersionRef, ...],
    produced_relations: tuple[RelationVersion, ...],
    produced_artifacts: tuple[ArtifactRegistration, ...],
    transaction_actor: Actor,
    transaction_evidence_refs: tuple[object, ...],
    entity_index: Mapping[tuple[str, int], EntityVersion],
    payload_index: Mapping[tuple[str, int], t.TheoryPayload],
) -> None:
    """Route-specific scientific closure beyond type cardinalities."""

    new_payloads: dict[str, list[tuple[EntityVersionRef, t.TheoryPayload]]] = {}
    for reference in produced_entity_refs:
        payload = payload_index.get(_entity_key(reference))
        if payload is not None:
            new_payloads.setdefault(type(payload).__name__, []).append(
                (reference, payload)
            )
    input_by_type: dict[str, list[EntityVersionRef]] = {}
    for reference in entry_report.input_entity_refs:
        entity = entity_index[_entity_key(reference)]
        input_by_type.setdefault(entity.entity_type, []).append(reference)

    for requirement in route_spec.required_output_relations:
        matching = [
            relation
            for relation in produced_relations
            if relation.relation_type == requirement.relation_type
        ]
        if matching and not any(
            relation.source in produced_entity_refs
            or relation.target in produced_entity_refs
            for relation in matching
        ):
            raise TheoryValidationError(
                f"required {requirement.relation_type} relation does not involve a route output"
            )

    def exactly_one(entity_type: str) -> tuple[EntityVersionRef, t.TheoryPayload]:
        values = new_payloads.get(entity_type, ())
        if len(values) != 1:
            raise TheoryValidationError(
                f"route-specific exit expected exactly one {entity_type}"
            )
        return values[0]

    def exactly_one_input(
        entity_type: str,
    ) -> tuple[EntityVersionRef, t.TheoryPayload]:
        references = input_by_type.get(entity_type, ())
        if len(references) != 1:
            raise TheoryValidationError(
                f"route-specific exit expected exactly one input {entity_type}"
            )
        reference = references[0]
        payload = payload_index.get(_entity_key(reference))
        if payload is None:
            raise TheoryValidationError(
                f"route-specific exit cannot resolve input {entity_type}"
            )
        return reference, payload

    route_id = route_spec.route_id
    if route_id == "frame.question_and_benchmarks":
        question_ref, _ = exactly_one("ResearchQuestion")
        benchmark_ref, benchmark = exactly_one("BenchmarkSet")
        if not isinstance(benchmark, t.BenchmarkSet) or benchmark.question_ref != question_ref:
            raise TheoryValidationError("BenchmarkSet does not bind the framed ResearchQuestion")
        if not any(
            relation.relation_type == "frames"
            and relation.source == question_ref
            and relation.target == benchmark_ref
            for relation in produced_relations
        ):
            raise TheoryValidationError(
                "frames must bind the exact question to its BenchmarkSet"
            )
        if not any(
            relation.relation_type == "benchmark_delta"
            and {relation.source, relation.target} == {question_ref, benchmark_ref}
            for relation in produced_relations
        ):
            raise TheoryValidationError(
                "benchmark_delta must bind the exact question and BenchmarkSet"
            )
    elif route_id == "decompose.primitives":
        primitive_ref, primitive = exactly_one("PrimitiveGraph")
        dossier_ref, dossier = exactly_one("GateDossier")
        question_refs = input_by_type.get("ResearchQuestion", ())
        benchmark_refs = input_by_type.get("BenchmarkSet", ())
        if (
            not isinstance(primitive, t.PrimitiveGraph)
            or not isinstance(dossier, t.GateDossier)
            or primitive.question_ref not in question_refs
            or primitive.benchmark_set_ref not in benchmark_refs
        ):
            raise TheoryValidationError("PrimitiveGraph does not bind the exact framed inputs")
        required_dossier_refs = {
            primitive.question_ref,
            primitive.benchmark_set_ref,
            primitive_ref,
        }
        if not required_dossier_refs.issubset(dossier.ordered_object_refs):
            raise TheoryValidationError("G1 dossier omits a required framed or primitive object")
        if not any(
            relation.relation_type == "decomposes"
            and relation.target == primitive_ref
            for relation in produced_relations
        ):
            raise TheoryValidationError(
                "decomposes relation does not target PrimitiveGraph; "
                "set operations[*].relation.target to the new PrimitiveGraph "
                "output (swap source and target if the relation is reversed)"
            )
        if not any(
            relation.relation_type == "governs"
            and dossier_ref in {relation.source, relation.target}
            for relation in produced_relations
        ):
            raise TheoryValidationError("G1 governs relation does not involve its dossier")
    elif route_id == "tournament.mechanisms":
        tournament_ref, tournament = exactly_one("MechanismTournament")
        del tournament_ref
        hypotheses = new_payloads.get("MechanismHypothesis", ())
        hypothesis_refs = {reference for reference, _ in hypotheses}
        if (
            not isinstance(tournament, t.MechanismTournament)
            or set(tournament.hypothesis_refs) != hypothesis_refs
            or tournament.proposed_selected_ref is None
            or not tournament.serious_rival_refs
        ):
            raise TheoryValidationError(
                "mechanism tournament must contain every produced hypothesis, a selection, and a serious rival"
            )
        compared_pairs = {
            frozenset((item.left_ref, item.right_ref))
            for item in tournament.comparisons
        }
        if any(
            frozenset((tournament.proposed_selected_ref, rival)) not in compared_pairs
            for rival in tournament.serious_rival_refs
        ):
            raise TheoryValidationError("selected mechanism lacks an exact rival comparison")
    elif route_id == "freeze.predictions":
        _, brief = exactly_one("PreResultBrief")
        _, register = exactly_one("PredictionRegister")
        if not isinstance(brief, t.PreResultBrief) or not isinstance(
            register, t.PredictionRegister
        ):
            raise TheoryValidationError("freeze route produced the wrong typed payloads")
        required_brief_refs = {
            *input_by_type.get("ResearchQuestion", ()),
            *input_by_type.get("BenchmarkSet", ()),
            *input_by_type.get("PrimitiveGraph", ()),
        }
        if not required_brief_refs.issubset(brief.allowed_context_refs):
            raise TheoryValidationError("PreResultBrief omits a required allowed context ref")
        if (
            brief.question_ref not in input_by_type.get("ResearchQuestion", ())
            or brief.benchmark_set_ref not in input_by_type.get("BenchmarkSet", ())
            or brief.primitive_graph_ref not in input_by_type.get("PrimitiveGraph", ())
            or register.question_ref != brief.question_ref
            or register.mechanism_tournament_ref
            not in input_by_type.get("MechanismTournament", ())
        ):
            raise TheoryValidationError("frozen brief and PredictionRegister disagree on exact inputs")
        predicted_hypotheses = {
            item.hypothesis_ref for item in register.original_predictions
        }
        if predicted_hypotheses != set(input_by_type.get("MechanismHypothesis", ())):
            raise TheoryValidationError("frozen predictions do not cover every mechanism hypothesis")
    elif route_id == "lab.micro_examples_and_ablations":
        example_ref, examples = exactly_one("ExampleSuite")
        register_ref, register = exactly_one("PredictionRegister")
        prior_registers = input_by_type.get("PredictionRegister", ())
        if (
            not isinstance(examples, t.ExampleSuite)
            or not isinstance(register, t.PredictionRegister)
            or len(prior_registers) != 1
            or register_ref.entity_id != prior_registers[0].entity_id
            or register_ref.version != prior_registers[0].version + 1
            or examples.frozen_prediction_register_ref != prior_registers[0]
        ):
            raise TheoryValidationError(
                "lab route must append-reconcile the exact PredictionRegister and bind its ExampleSuite"
            )
        required_roles = {
            "benchmark",
            "mechanism_on",
            "ablation",
            "rival_separator",
            "boundary",
        }
        observed_roles = {role for case in examples.cases for role in case.roles}
        if not required_roles.issubset(observed_roles):
            raise TheoryValidationError(
                "mechanism-explanation ExampleSuite lacks benchmark, mechanism, ablation, separator, or boundary coverage"
            )
        if not all(
            any(
                relation.relation_type == relation_type
                and example_ref in {relation.source, relation.target}
                for relation in produced_relations
            )
            for relation_type in ("ablates", "separates", "tests")
        ):
            raise TheoryValidationError("ExampleSuite required relations do not bind the suite")
        if not any(
            relation.relation_type == "reconciles"
            and register_ref in {relation.source, relation.target}
            for relation in produced_relations
        ):
            raise TheoryValidationError(
                "reconciles relation does not bind the appended PredictionRegister"
            )
    elif route_id == "promote.mechanism":
        argument_ref, argument = exactly_one("EconomicArgumentGraph")
        _, dossier = exactly_one("GateDossier")
        if not isinstance(argument, t.EconomicArgumentGraph) or not isinstance(
            dossier, t.GateDossier
        ):
            raise TheoryValidationError("mechanism promotion produced the wrong payloads")
        tournaments = input_by_type.get("MechanismTournament", ())
        if len(tournaments) != 1:
            raise TheoryValidationError("mechanism promotion requires one exact tournament")
        tournament = payload_index[_entity_key(tournaments[0])]
        if not isinstance(tournament, t.MechanismTournament):
            raise TheoryValidationError("mechanism tournament input is unavailable")
        if (
            argument.selected_mechanism_ref != tournament.proposed_selected_ref
            or argument.primitive_graph_ref not in input_by_type.get("PrimitiveGraph", ())
            or argument.prediction_register_ref
            not in input_by_type.get("PredictionRegister", ())
            or argument.example_suite_ref not in input_by_type.get("ExampleSuite", ())
            or not any(edge.load_bearing for edge in argument.edges)
        ):
            raise TheoryValidationError(
                "EconomicArgumentGraph does not preserve the selected mechanism and load-bearing evidence"
            )
        example_payload = payload_index[_entity_key(argument.example_suite_ref)]
        if not isinstance(example_payload, t.ExampleSuite):
            raise TheoryValidationError("EconomicArgumentGraph example suite is unavailable")
        case_ids = {case.case_id for case in example_payload.cases}
        if any(
            not set(edge.supporting_case_ids).issubset(case_ids)
            for edge in argument.edges
        ):
            raise TheoryValidationError("economic argument edge cites an unknown example case")
        required_dossier_refs = {
            argument_ref,
            *entry_report.input_entity_refs,
        }
        if not required_dossier_refs.issubset(dossier.ordered_object_refs):
            raise TheoryValidationError("G2 dossier omits required tournament evidence")
    elif route_id == "tournament.implementations":
        _, tournament = exactly_one("ImplementationTournament")
        model_entries = new_payloads.get("FormalModel", ())
        model_refs = {reference for reference, _ in model_entries}
        if (
            not isinstance(tournament, t.ImplementationTournament)
            or set(tournament.candidate_model_refs) != model_refs
            or tournament.proposed_selected_model_ref is None
            or not tournament.contrast_model_refs
        ):
            raise TheoryValidationError(
                "implementation tournament must contain every produced model, a selection, and a contrast"
            )
        argument_refs = input_by_type.get("EconomicArgumentGraph", ())
        if len(argument_refs) != 1 or tournament.economic_argument_graph_ref != argument_refs[0]:
            raise TheoryValidationError(
                "implementation tournament does not bind the promoted economic argument"
            )
        argument = payload_index[_entity_key(argument_refs[0])]
        if not isinstance(argument, t.EconomicArgumentGraph):
            raise TheoryValidationError("implementation tournament argument is unavailable")
        for reference, model in model_entries:
            del reference
            if (
                not isinstance(model, t.FormalModel)
                or model.question_ref not in input_by_type.get("ResearchQuestion", ())
                or model.primitive_graph_ref not in input_by_type.get("PrimitiveGraph", ())
                or model.selected_mechanism_ref != argument.selected_mechanism_ref
            ):
                raise TheoryValidationError(
                    "candidate FormalModel deletes or changes the promoted mechanism scope"
                )
        compared_pairs = {
            frozenset((item.left_model_ref, item.right_model_ref))
            for item in tournament.comparisons
        }
        if any(
            frozenset((tournament.proposed_selected_model_ref, contrast))
            not in compared_pairs
            for contrast in tournament.contrast_model_refs
        ):
            raise TheoryValidationError(
                "selected formal implementation lacks an exact contrast comparison"
            )
    elif route_id == "promote.formal_base":
        selected_ref, selected_model = exactly_one("FormalModel")
        mapping_ref, mapping = exactly_one("FormalizationMap")
        _, assumptions = exactly_one("AssumptionMap")
        _, dossier = exactly_one("GateDossier")
        tournaments = input_by_type.get("ImplementationTournament", ())
        if len(tournaments) != 1:
            raise TheoryValidationError("formal-base promotion requires one ImplementationTournament")
        tournament = payload_index[_entity_key(tournaments[0])]
        if not isinstance(tournament, t.ImplementationTournament):
            raise TheoryValidationError("formal-base tournament input is unavailable")
        prior_selected = tournament.proposed_selected_model_ref
        if (
            prior_selected is None
            or selected_ref.entity_id != prior_selected.entity_id
            or selected_ref.version != prior_selected.version + 1
        ):
            raise TheoryValidationError(
                "formal-base promotion must supersede the exact tournament selection"
            )
        if (
            not isinstance(selected_model, t.FormalModel)
            or not isinstance(mapping, t.FormalizationMap)
            or not isinstance(assumptions, t.AssumptionMap)
            or not isinstance(dossier, t.GateDossier)
            or mapping.formal_model_ref != selected_ref
            or assumptions.formal_model_ref != selected_ref
            or assumptions.formalization_map_ref != mapping_ref
        ):
            raise TheoryValidationError(
                "formal-base mapping and assumptions do not bind the selected FormalModel"
            )
        required_dossier_refs = {selected_ref, mapping_ref}
        required_dossier_refs.update(
            reference
            for reference in entry_report.input_entity_refs
            if reference.entity_id != selected_ref.entity_id
        )
        assumption_refs = {
            reference
            for reference, payload in new_payloads.get("AssumptionMap", ())
            if isinstance(payload, t.AssumptionMap)
        }
        required_dossier_refs.update(assumption_refs)
        if not required_dossier_refs.issubset(dossier.ordered_object_refs):
            raise TheoryValidationError("G3 dossier omits implementation or mapping evidence")
    elif route_id == "discover.claims_and_boundaries":
        graph_ref, graph = exactly_one("ClaimGraph")
        obligation_entries = new_payloads.get("ProofObligation", ())
        prior_assumptions_ref, prior_assumptions = exactly_one_input("AssumptionMap")
        formal_model_ref, _ = exactly_one_input("FormalModel")
        formalization_ref, _ = exactly_one_input("FormalizationMap")
        mechanism_ref, _ = exactly_one_input("MechanismHypothesis")
        updated_assumptions = new_payloads.get("AssumptionMap", ())
        if len(updated_assumptions) > 1:
            raise TheoryValidationError("claim discovery can supersede at most one AssumptionMap")
        if updated_assumptions:
            assumptions_ref, assumptions = updated_assumptions[0]
            assumptions_entity = entity_index[_entity_key(assumptions_ref)]
            if assumptions_entity.supersedes != prior_assumptions_ref:
                raise TheoryValidationError(
                    "an updated claim AssumptionMap must supersede the exact G3 map"
                )
        else:
            assumptions_ref, assumptions = prior_assumptions_ref, prior_assumptions
        if (
            not isinstance(graph, t.ClaimGraph)
            or not isinstance(assumptions, t.AssumptionMap)
            or assumptions.formal_model_ref != formal_model_ref
            or assumptions.formalization_map_ref != formalization_ref
            or graph.formal_model_ref != formal_model_ref
            or graph.formalization_map_ref != formalization_ref
            or graph.assumption_map_ref != assumptions_ref
        ):
            raise TheoryValidationError(
                "ClaimGraph and AssumptionMap do not bind the exact human-confirmed formal base"
            )
        claim_by_id = {claim.claim_id: claim for claim in graph.claims}
        assumption_ids = {item.assumption_id for item in assumptions.assumptions}
        output_obligation_refs = {reference for reference, _ in obligation_entries}
        graph_obligation_refs = {
            reference
            for claim in graph.claims
            for reference in claim.proof_obligation_refs
        }
        if graph_obligation_refs != output_obligation_refs:
            raise TheoryValidationError(
                "ClaimGraph proof obligations must equal the exact route outputs"
            )
        obligation_ids: set[str] = set()
        obligations_by_assumption: dict[str, set[str]] = {
            assumption_id: set() for assumption_id in assumption_ids
        }
        claims_by_assumption: dict[str, set[str]] = {
            assumption_id: set() for assumption_id in assumption_ids
        }
        for claim in graph.claims:
            if claim.mechanism_ref != mechanism_ref:
                raise TheoryValidationError(
                    "every discovered claim must preserve the promoted mechanism"
                )
            if claim.verification_record_refs:
                raise TheoryValidationError(
                    "claim discovery cannot forward-reference future VerificationRecords"
                )
            if not set(claim.assumption_ids).issubset(assumption_ids):
                raise TheoryValidationError("discovered claim cites an unknown assumption")
            for assumption_id in claim.assumption_ids:
                claims_by_assumption[assumption_id].add(claim.claim_id)
        for reference, payload in obligation_entries:
            if not isinstance(payload, t.ProofObligation):
                raise TheoryValidationError("claim route emitted a non-obligation payload")
            claim = claim_by_id.get(payload.claim_id)
            if (
                payload.claim_graph_ref != graph_ref
                or claim is None
                or reference not in claim.proof_obligation_refs
                or not set(payload.assumption_ids).issubset(set(claim.assumption_ids))
            ):
                raise TheoryValidationError(
                    "ProofObligation does not bind its exact ClaimGraph, claim, and assumptions"
                )
            if payload.obligation_id in obligation_ids:
                raise TheoryValidationError("ProofObligation IDs must be unique within a ClaimGraph")
            obligation_ids.add(payload.obligation_id)
            for assumption_id in payload.assumption_ids:
                obligations_by_assumption[assumption_id].add(payload.obligation_id)
        if updated_assumptions:
            for record in assumptions.assumptions:
                if set(record.dependent_claim_ids) != claims_by_assumption[record.assumption_id]:
                    raise TheoryValidationError(
                        "updated AssumptionMap does not exactly index dependent claims"
                    )
                if set(record.proof_obligation_ids) != obligations_by_assumption[
                    record.assumption_id
                ]:
                    raise TheoryValidationError(
                        "updated AssumptionMap does not exactly index proof obligations"
                    )
        if not any(
            relation.relation_type == "bounds"
            and relation.source == assumptions_ref
            and relation.target == graph_ref
            for relation in produced_relations
        ):
            raise TheoryValidationError("bounds must bind the exact AssumptionMap to ClaimGraph")
        if not any(
            relation.relation_type == "entails"
            and relation.source in {formal_model_ref, formalization_ref}
            and relation.target == graph_ref
            for relation in produced_relations
        ):
            raise TheoryValidationError("entails must bind the formal base to ClaimGraph")
        for obligation_ref in output_obligation_refs:
            if not any(
                relation.relation_type == "requires"
                and relation.source == graph_ref
                and relation.target == obligation_ref
                for relation in produced_relations
            ):
                raise TheoryValidationError(
                    "every ProofObligation requires an exact ClaimGraph relation"
                )
    elif route_id == "verify.claims_proofs_and_interpretation":
        bundle_ref, bundle = exactly_one("VerificationBundle")
        record_entries = new_payloads.get("VerificationRecord", ())
        graph_ref, graph = exactly_one_input("ClaimGraph")
        formal_model_ref, _ = exactly_one_input("FormalModel")
        assumptions_ref, _ = exactly_one_input("AssumptionMap")
        input_obligation_refs = set(input_by_type.get("ProofObligation", ()))
        output_record_refs = {reference for reference, _ in record_entries}
        if (
            not isinstance(bundle, t.VerificationBundle)
            or not isinstance(graph, t.ClaimGraph)
            or bundle.claim_graph_ref != graph_ref
            or set(bundle.proof_obligation_refs) != input_obligation_refs
            or set(bundle.verification_record_refs) != output_record_refs
        ):
            raise TheoryValidationError(
                "VerificationBundle must bind the exact ClaimGraph, obligations, and produced records"
            )
        expected_obligations = {
            reference
            for claim in graph.claims
            for reference in claim.proof_obligation_refs
        }
        if input_obligation_refs != expected_obligations:
            raise TheoryValidationError(
                "verification inputs must contain every and only retained claim obligation"
            )
        records_by_obligation: dict[EntityVersionRef, list[EntityVersionRef]] = {
            reference: [] for reference in input_obligation_refs
        }
        for record_ref, payload in record_entries:
            if (
                not isinstance(payload, t.VerificationRecord)
                or payload.claim_graph_ref != graph_ref
                or payload.formal_model_ref != formal_model_ref
                or payload.assumption_map_ref != assumptions_ref
                or payload.obligation_ref not in input_obligation_refs
            ):
                raise TheoryValidationError(
                    "VerificationRecord does not bind the exact obligation, graph, model, and assumptions"
                )
            required_checked_refs = {
                payload.obligation_ref,
                graph_ref,
                formal_model_ref,
                assumptions_ref,
            }
            if not required_checked_refs.issubset(payload.checked_refs):
                raise TheoryValidationError(
                    "VerificationRecord checked_refs omit a load-bearing exact object"
                )
            records_by_obligation[payload.obligation_ref].append(record_ref)
            if not any(
                relation.relation_type == "verifies"
                and relation.source == record_ref
                and relation.target == payload.obligation_ref
                for relation in produced_relations
            ):
                raise TheoryValidationError(
                    "every VerificationRecord must verify its exact ProofObligation"
                )
        if any(not values for values in records_by_obligation.values()):
            raise TheoryValidationError(
                "verification must produce at least one record for every obligation"
            )
        if not bundle.interpretation_evidence_refs:
            raise TheoryValidationError(
                "VerificationBundle requires exact economic interpretation evidence"
            )
        if any(claim.boundary_case_ids for claim in graph.claims) and not bundle.counterexample_evidence_refs:
            raise TheoryValidationError(
                "claims with boundaries require exact boundary or counterexample evidence"
            )
        if not any(
            relation.relation_type == "supports"
            and relation.source == bundle_ref
            and relation.target == graph_ref
            for relation in produced_relations
        ):
            raise TheoryValidationError(
                "VerificationBundle must support its exact ClaimGraph"
            )
    elif route_id == "audit.assumptions_generality_and_absorption":
        literature_ref, literature = exactly_one("LiteratureEvidence")
        closest_ref, closest = exactly_one("ClosestTheoryMap")
        absorption_ref, absorption = exactly_one("AbsorptionAssessment")
        question_ref, _ = exactly_one_input("ResearchQuestion")
        formal_model_ref, _ = exactly_one_input("FormalModel")
        assumptions_ref, assumptions = exactly_one_input("AssumptionMap")
        graph_ref, graph = exactly_one_input("ClaimGraph")
        bundle_ref, bundle = exactly_one_input("VerificationBundle")
        required_dimensions = {
            "benchmark",
            "primitives",
            "timing",
            "solution_concept",
            "assumptions",
            "quantifiers",
            "formal_result",
            "economic_lesson",
        }
        if (
            not isinstance(literature, t.LiteratureEvidence)
            or not isinstance(closest, t.ClosestTheoryMap)
            or not isinstance(absorption, t.AbsorptionAssessment)
            or not isinstance(assumptions, t.AssumptionMap)
            or not isinstance(graph, t.ClaimGraph)
            or not isinstance(bundle, t.VerificationBundle)
            or literature.question_ref != question_ref
            or graph.formal_model_ref != formal_model_ref
            or graph.assumption_map_ref != assumptions_ref
            or bundle.claim_graph_ref != graph_ref
            or closest.claim_graph_ref != graph_ref
            or closest.literature_evidence_ref != literature_ref
            or absorption.closest_theory_map_ref != closest_ref
            or absorption.central_claim_graph_ref != graph_ref
            or absorption.central_claim_id not in graph.contribution_spine
            or {item.dimension for item in closest.dimensions} != required_dimensions
        ):
            raise TheoryValidationError(
                "absorption audit does not close the exact question, model, claims, evidence, and eight comparison dimensions"
            )
        if any(not item.weakening_attempts for item in assumptions.assumptions):
            raise TheoryValidationError(
                "every assumption requires at least one recorded weakening attempt before absorption audit"
            )
        failed_dimensions = [
            item for item in closest.dimensions if item.mapping_status == "fails"
        ]
        unresolved_dimensions = [
            item for item in closest.dimensions if item.mapping_status == "unresolved"
        ]
        unverified_literature = [
            item
            for item in literature.assertions
            if item.verification_status != "source_verified"
        ]
        if absorption.first_mapping_failure != closest.first_mapping_failure:
            raise TheoryValidationError(
                "AbsorptionAssessment must preserve the ClosestTheoryMap first mapping failure"
            )
        if absorption.outcome == "nonabsorbed" and (
            not failed_dimensions
            or unverified_literature
            or unresolved_dimensions
            or closest.first_mapping_failure is None
        ):
            raise TheoryValidationError(
                "nonabsorption requires a verified exact first mapping failure"
            )
        if absorption.outcome == "absorbed" and (
            failed_dimensions or unresolved_dimensions or unverified_literature
        ):
            raise TheoryValidationError(
                "an absorbed result cannot retain a failed, unresolved, or unverified mapping"
            )
        if absorption.outcome == "unresolved_evidence" and not (
            unresolved_dimensions or unverified_literature
        ):
            raise TheoryValidationError(
                "unresolved absorption requires an explicit unresolved dimension or source"
            )
        classification_outcomes = {
            "duplicate": {"absorbed"},
            "direct_corollary": {"absorbed"},
            "special_case": {"absorbed", "partially_absorbed"},
            "application": {"application_only"},
            "unresolved": {"unresolved_evidence"},
            "generalization": {"nonabsorbed", "partially_absorbed"},
            "converse": {"nonabsorbed", "partially_absorbed"},
            "different_mechanism": {"nonabsorbed", "partially_absorbed"},
            "different_boundary": {"nonabsorbed", "partially_absorbed"},
            "non_comparable": {"nonabsorbed", "unresolved_evidence"},
        }
        if absorption.outcome not in classification_outcomes[closest.classification]:
            raise TheoryValidationError(
                "ClosestTheoryMap classification contradicts AbsorptionAssessment outcome"
            )
        if absorption.recommended_route == "proceed":
            if absorption.outcome not in {"nonabsorbed", "partially_absorbed"}:
                raise TheoryValidationError(
                    "only nonabsorbed or partially absorbed work may proceed"
                )
            if any(
                item.access_status != "full_text"
                or item.verification_status != "source_verified"
                for item in literature.assertions
            ):
                raise TheoryValidationError(
                    "a proceed recommendation requires verified full-text closest-theory evidence"
                )
        required_relation_pairs = (
            ("compares_to", closest_ref, literature_ref),
            ("maps_to", closest_ref, graph_ref),
        )
        for relation_type, source, target in required_relation_pairs:
            if not any(
                relation.relation_type == relation_type
                and relation.source == source
                and relation.target == target
                for relation in produced_relations
            ):
                raise TheoryValidationError(
                    f"{relation_type} must bind the exact absorption-audit objects"
                )
        exact_absorbs = any(
            relation.relation_type == "absorbs"
            and relation.source == absorption_ref
            and relation.target == closest_ref
            for relation in produced_relations
        )
        if absorption.outcome in {
            "absorbed",
            "partially_absorbed",
            "application_only",
        }:
            if not exact_absorbs:
                raise TheoryValidationError(
                    "an absorbed or partially absorbed assessment requires its exact absorbs relation"
                )
        elif any(
            relation.relation_type == "absorbs" for relation in produced_relations
        ):
            raise TheoryValidationError(
                "a nonabsorbed or unresolved assessment cannot emit an absorbs relation"
            )
    elif route_id == "curate.result_portfolio":
        portfolio_ref, portfolio = exactly_one("ResultPortfolio")
        dossier_ref, dossier = exactly_one("GateDossier")
        graph_ref, graph = exactly_one_input("ClaimGraph")
        bundle_ref, bundle = exactly_one_input("VerificationBundle")
        absorption_ref, absorption = exactly_one_input("AbsorptionAssessment")
        if (
            not isinstance(portfolio, t.ResultPortfolio)
            or not isinstance(dossier, t.GateDossier)
            or not isinstance(graph, t.ClaimGraph)
            or not isinstance(bundle, t.VerificationBundle)
            or not isinstance(absorption, t.AbsorptionAssessment)
            or portfolio.claim_graph_ref != graph_ref
            or bundle.claim_graph_ref != graph_ref
            or absorption.central_claim_graph_ref != graph_ref
            or absorption.central_claim_id != portfolio.headline_claim_id
        ):
            raise TheoryValidationError(
                "ResultPortfolio does not bind the exact verified and absorption-audited ClaimGraph"
            )
        claim_by_id = {item.claim_id: item for item in graph.claims}
        included_ids = {item.claim_id for item in portfolio.included_results}
        excluded_ids = {item.claim_id for item in portfolio.excluded_results}
        if included_ids | excluded_ids != set(claim_by_id):
            raise TheoryValidationError(
                "ResultPortfolio must explicitly include or exclude every retained claim"
            )
        if not set(graph.contribution_spine).issubset(included_ids):
            raise TheoryValidationError(
                "ResultPortfolio cannot exclude a contribution-spine claim"
            )
        headline = claim_by_id.get(portfolio.headline_claim_id)
        if headline is None or headline.scientific_job != "headline":
            raise TheoryValidationError(
                "ResultPortfolio headline must be the ClaimGraph headline claim"
            )
        required_dossier_refs = {
            portfolio_ref,
            *entry_report.input_entity_refs,
        }
        if not required_dossier_refs.issubset(dossier.ordered_object_refs):
            raise TheoryValidationError("G4 dossier omits a required result-investment object")
        records = [
            payload_index[_entity_key(reference)]
            for reference in bundle.verification_record_refs
        ]
        if dossier.proposed_action == "approve" and (
            absorption.outcome in {"absorbed", "unresolved_evidence"}
            or absorption.recommended_route != "proceed"
            or any(
                not isinstance(record, t.VerificationRecord)
                or record.outcome != "discharged"
                for record in records
            )
        ):
            raise TheoryValidationError(
                "an approving G4 dossier requires nonabsorbed, fully discharged, proceed-worthy results"
            )
        required_relation_pairs = (
            ("includes", portfolio_ref, graph_ref),
            ("governs", dossier_ref, portfolio_ref),
        )
        for relation_type, source, target in required_relation_pairs:
            if not any(
                relation.relation_type == relation_type
                and relation.source == source
                and relation.target == target
                for relation in produced_relations
            ):
                raise TheoryValidationError(
                    f"{relation_type} must bind the exact result-portfolio objects"
                )
    elif route_id == "validate.argument_package":
        package_ref, package = exactly_one("ValidatedArgumentPackage")
        dossier_ref, dossier = exactly_one("GateDossier")
        if not isinstance(package, t.ValidatedArgumentPackage) or not isinstance(
            dossier, t.GateDossier
        ):
            raise TheoryValidationError("argument validation emitted malformed package objects")

        direct_input_fields = {
            "question_ref": "ResearchQuestion",
            "benchmark_set_ref": "BenchmarkSet",
            "primitive_graph_ref": "PrimitiveGraph",
            "selected_mechanism_ref": "MechanismHypothesis",
            "prediction_register_ref": "PredictionRegister",
            "example_suite_ref": "ExampleSuite",
            "economic_argument_graph_ref": "EconomicArgumentGraph",
            "implementation_tournament_ref": "ImplementationTournament",
            "formal_model_ref": "FormalModel",
            "formalization_map_ref": "FormalizationMap",
            "assumption_map_ref": "AssumptionMap",
            "claim_graph_ref": "ClaimGraph",
            "verification_bundle_ref": "VerificationBundle",
            "closest_theory_map_ref": "ClosestTheoryMap",
            "absorption_assessment_ref": "AbsorptionAssessment",
            "result_portfolio_ref": "ResultPortfolio",
        }
        for field_name, entity_type in direct_input_fields.items():
            if getattr(package, field_name) not in input_by_type.get(entity_type, ()):
                raise TheoryValidationError(
                    f"VAP.{field_name} is not an exact current route input"
                )
        if not package.serious_rejected_rival_refs or not set(
            package.serious_rejected_rival_refs
        ).issubset(input_by_type.get("MechanismHypothesis", ())):
            raise TheoryValidationError(
                "VAP must retain exact current serious rival inputs"
            )
        if tuple(package.prior_gate_decision_refs) != tuple(
            entry_report.gate_decision_refs
        ):
            raise TheoryValidationError(
                "VAP prior gates must equal the exact ordered G1-G4 entry chain"
            )
        if package.g5_dossier_ref != dossier_ref:
            raise TheoryValidationError("VAP does not point to the exact same-transaction G5 dossier")
        required_dossier_refs = {
            package_ref,
            *entry_report.input_entity_refs,
        }
        if not required_dossier_refs.issubset(dossier.ordered_object_refs):
            raise TheoryValidationError(
                "G5 dossier omits the package or a load-bearing exact input"
            )

        def package_payload(
            reference: EntityVersionRef, expected_type: type[t.TheoryPayload]
        ) -> t.TheoryPayload:
            payload = payload_index.get(_entity_key(reference))
            if payload is None or not isinstance(payload, expected_type):
                raise TheoryValidationError(
                    f"VAP exact chain cannot resolve {expected_type.__name__}"
                )
            return payload

        benchmark = package_payload(package.benchmark_set_ref, t.BenchmarkSet)
        primitives = package_payload(package.primitive_graph_ref, t.PrimitiveGraph)
        selected_mechanism = package_payload(
            package.selected_mechanism_ref, t.MechanismHypothesis
        )
        mechanism_tournament_ref, mechanism_tournament = exactly_one_input(
            "MechanismTournament"
        )
        predictions = package_payload(
            package.prediction_register_ref, t.PredictionRegister
        )
        examples = package_payload(package.example_suite_ref, t.ExampleSuite)
        argument = package_payload(
            package.economic_argument_graph_ref, t.EconomicArgumentGraph
        )
        implementation = package_payload(
            package.implementation_tournament_ref, t.ImplementationTournament
        )
        formal_model = package_payload(package.formal_model_ref, t.FormalModel)
        formalization = package_payload(
            package.formalization_map_ref, t.FormalizationMap
        )
        assumptions = package_payload(package.assumption_map_ref, t.AssumptionMap)
        graph = package_payload(package.claim_graph_ref, t.ClaimGraph)
        bundle = package_payload(
            package.verification_bundle_ref, t.VerificationBundle
        )
        closest = package_payload(package.closest_theory_map_ref, t.ClosestTheoryMap)
        absorption = package_payload(
            package.absorption_assessment_ref, t.AbsorptionAssessment
        )
        portfolio = package_payload(package.result_portfolio_ref, t.ResultPortfolio)
        if not isinstance(mechanism_tournament, t.MechanismTournament):
            raise TheoryValidationError("VAP mechanism tournament input is unavailable")
        literature_refs = input_by_type.get("LiteratureEvidence", ())
        if len(literature_refs) != 1:
            raise TheoryValidationError("VAP requires one exact LiteratureEvidence input")
        input_obligations = set(input_by_type.get("ProofObligation", ()))
        input_records = set(input_by_type.get("VerificationRecord", ()))

        if (
            not isinstance(benchmark, t.BenchmarkSet)
            or not isinstance(primitives, t.PrimitiveGraph)
            or not isinstance(selected_mechanism, t.MechanismHypothesis)
            or not isinstance(predictions, t.PredictionRegister)
            or not isinstance(examples, t.ExampleSuite)
            or not isinstance(argument, t.EconomicArgumentGraph)
            or not isinstance(implementation, t.ImplementationTournament)
            or not isinstance(formal_model, t.FormalModel)
            or not isinstance(formalization, t.FormalizationMap)
            or not isinstance(assumptions, t.AssumptionMap)
            or not isinstance(graph, t.ClaimGraph)
            or not isinstance(bundle, t.VerificationBundle)
            or not isinstance(closest, t.ClosestTheoryMap)
            or not isinstance(absorption, t.AbsorptionAssessment)
            or not isinstance(portfolio, t.ResultPortfolio)
        ):
            raise TheoryValidationError("VAP exact chain contains an unexpected payload type")
        if (
            benchmark.question_ref != package.question_ref
            or primitives.question_ref != package.question_ref
            or primitives.benchmark_set_ref != package.benchmark_set_ref
            or selected_mechanism.question_ref != package.question_ref
            or selected_mechanism.primitive_graph_ref != package.primitive_graph_ref
            or mechanism_tournament.question_ref != package.question_ref
            or predictions.question_ref != package.question_ref
            or predictions.mechanism_tournament_ref != mechanism_tournament_ref
            or examples.selected_mechanism_ref != package.selected_mechanism_ref
            or argument.selected_mechanism_ref != package.selected_mechanism_ref
            or argument.primitive_graph_ref != package.primitive_graph_ref
            or argument.prediction_register_ref != package.prediction_register_ref
            or argument.example_suite_ref != package.example_suite_ref
            or implementation.selected_mechanism_ref != package.selected_mechanism_ref
            or implementation.economic_argument_graph_ref
            != package.economic_argument_graph_ref
            or formal_model.question_ref != package.question_ref
            or formal_model.selected_mechanism_ref != package.selected_mechanism_ref
            or formal_model.primitive_graph_ref != package.primitive_graph_ref
            or formalization.economic_argument_graph_ref
            != package.economic_argument_graph_ref
            or formalization.formal_model_ref != package.formal_model_ref
            or assumptions.formal_model_ref != package.formal_model_ref
            or assumptions.formalization_map_ref != package.formalization_map_ref
            or graph.formal_model_ref != package.formal_model_ref
            or graph.formalization_map_ref != package.formalization_map_ref
            or graph.assumption_map_ref != package.assumption_map_ref
            or bundle.claim_graph_ref != package.claim_graph_ref
            or closest.claim_graph_ref != package.claim_graph_ref
            or closest.literature_evidence_ref != literature_refs[0]
            or absorption.closest_theory_map_ref != package.closest_theory_map_ref
            or absorption.central_claim_graph_ref != package.claim_graph_ref
            or portfolio.claim_graph_ref != package.claim_graph_ref
            or package.economic_nugget != portfolio.economic_nugget
        ):
            raise TheoryValidationError(
                "VAP splices incompatible branches instead of preserving one exact argument chain"
            )
        if (
            mechanism_tournament.proposed_selected_ref
            != package.selected_mechanism_ref
            or set(mechanism_tournament.serious_rival_refs)
            != set(package.serious_rejected_rival_refs)
            or set(mechanism_tournament.hypothesis_refs)
            != set(input_by_type.get("MechanismHypothesis", ()))
        ):
            raise TheoryValidationError(
                "VAP mechanism selection and serious rivals do not match the exact tournament"
            )
        proposed_model = implementation.proposed_selected_model_ref
        if (
            proposed_model is None
            or package.formal_model_ref.entity_id != proposed_model.entity_id
            or package.formal_model_ref.version != proposed_model.version + 1
        ):
            raise TheoryValidationError(
                "VAP must use the exact promoted successor of the tournament selection"
            )
        current_formal_inputs = set(input_by_type.get("FormalModel", ()))
        expected_current_formal_inputs = {
            (
                package.formal_model_ref
                if candidate_ref.entity_id == package.formal_model_ref.entity_id
                else candidate_ref
            )
            for candidate_ref in implementation.candidate_model_refs
        }
        if current_formal_inputs != expected_current_formal_inputs:
            raise TheoryValidationError(
                "VAP formal inputs must equal every current implementation candidate lineage"
            )
        if (
            set(bundle.proof_obligation_refs) != input_obligations
            or set(bundle.verification_record_refs) != input_records
        ):
            raise TheoryValidationError(
                "VAP proof and verification inputs do not equal its VerificationBundle"
            )
        brief_inputs = input_by_type.get("PreResultBrief", ())
        lock_artifacts = [
            item
            for item in produced_artifacts
            if item.media_type
            == "application/vnd.econ-theorist.candidate-lock+json"
        ]
        if package.evaluation_attempt_id is not None:
            candidate_entity = entity_index[_entity_key(package_ref)]
            candidate_bytes = canonical_json_bytes(candidate_entity)
            candidate_hash = sha256_digest(candidate_bytes)
            expected_lock_id = f"candidate.lock.{package.evaluation_attempt_id}"
            if (
                package.release_mode != "evaluation_only"
                or len(brief_inputs) != 1
                or package.pre_result_brief_ref != brief_inputs[0]
                or package.generator_actor != transaction_actor
                or len(lock_artifacts) != 1
                or lock_artifacts[0].artifact_id != expected_lock_id
                or lock_artifacts[0].version != 1
                or lock_artifacts[0].supersedes is not None
                or lock_artifacts[0].content_hash != candidate_hash
                or lock_artifacts[0].byte_size != len(candidate_bytes)
            ):
                raise TheoryValidationError(
                    "blind evaluation VAP requires one exact same-transaction candidate lock"
                )
            if not any(
                relation.relation_type == "supports"
                and relation.source == package_ref
                and relation.target == brief_inputs[0]
                for relation in produced_relations
            ):
                raise TheoryValidationError(
                    "blind evaluation VAP must bind its attempt PreResultBrief by exact supports relation"
                )
        elif brief_inputs or lock_artifacts:
            raise TheoryValidationError(
                "non-blind VAP cannot consume a blind brief or emit a candidate lock"
            )
        required_relation_pairs = (
            ("governs", dossier_ref, package_ref),
            ("includes", package_ref, package.result_portfolio_ref),
            ("validates", package.verification_bundle_ref, package_ref),
        )
        for relation_type, source, target in required_relation_pairs:
            if not any(
                relation.relation_type == relation_type
                and relation.source == source
                and relation.target == target
                for relation in produced_relations
            ):
                raise TheoryValidationError(
                    f"{relation_type} must bind the exact G5 package objects"
                )
    elif route_id == "prepare.blind_case":
        manifest_ref, manifest = exactly_one("BlindCaseManifest")
        variant_ref, variant = exactly_one("TransformedVariantManifest")
        brief_refs = input_by_type.get("PreResultBrief", ())
        gold_refs = input_by_type.get("ValidatedArgumentPackage", ())
        if (
            not isinstance(manifest, t.BlindCaseManifest)
            or not isinstance(variant, t.TransformedVariantManifest)
            or len(brief_refs) != 2
            or len(gold_refs) != 1
            or variant.base_case_manifest_ref != manifest_ref
            or variant.transformed_brief_ref not in brief_refs
            or manifest.pre_result_brief_ref not in brief_refs
            or variant.transformed_brief_ref == manifest.pre_result_brief_ref
            or manifest.gold_package_ref != gold_refs[0]
            or variant.attempt_id != manifest.attempt_id
            or variant.implementation_freeze_ref
            not in entry_report.gate_decision_refs
        ):
            raise TheoryValidationError(
                "blind case outputs do not bind the exact base, transform, gold, and freeze inputs"
            )
        base_brief = payload_index[_entity_key(manifest.pre_result_brief_ref)]
        transformed_brief = payload_index[_entity_key(variant.transformed_brief_ref)]
        if (
            not isinstance(base_brief, t.PreResultBrief)
            or not isinstance(transformed_brief, t.PreResultBrief)
            or base_brief.attempt_id != manifest.attempt_id
            or transformed_brief.attempt_id != manifest.attempt_id
        ):
            raise TheoryValidationError("blind case briefs disagree on the sealed attempt")
        embedded_artifact_refs = {
            reference
            for payload in (manifest, variant)
            for reference in _walk_exact_refs(payload)
            if isinstance(reference, ArtifactDependencyRef)
        }
        produced_artifact_refs = {
            ArtifactDependencyRef(
                artifact_id=item.artifact_id,
                version=item.version,
                content_hash=item.content_hash,
            )
            for item in produced_artifacts
        }
        if embedded_artifact_refs != produced_artifact_refs:
            raise TheoryValidationError(
                "blind case preparation must register every and only sealed manifest artifact"
            )
        manifest_entity = entity_index[_entity_key(manifest_ref)]
        variant_entity = entity_index[_entity_key(variant_ref)]
        manifest_refs = {
            reference
            for reference in _walk_exact_refs(manifest)
            if isinstance(reference, ArtifactDependencyRef)
        }
        variant_refs = {
            reference
            for reference in _walk_exact_refs(variant)
            if isinstance(reference, ArtifactDependencyRef)
        }
        if set(manifest_entity.artifact_refs) != manifest_refs or set(
            variant_entity.artifact_refs
        ) != variant_refs:
            raise TheoryValidationError(
                "blind manifest envelopes must expose every exact artifact dependency to privacy validation"
            )
        generator_grants = {"project_research", *manifest.generator_compartments}
        transformed_entity = entity_index[_entity_key(variant.transformed_brief_ref)]
        gold_entity = entity_index[_entity_key(manifest.gold_package_ref)]
        if not set(transformed_entity.access_compartments).issubset(generator_grants):
            raise TheoryValidationError(
                "generator compartments cannot read the transformed PreResultBrief"
            )
        if set(gold_entity.access_compartments).issubset(generator_grants):
            raise TheoryValidationError(
                "generator compartments would disclose the sealed gold package"
            )
        for artifact in produced_artifacts:
            if (
                "confirmatory_holdout" not in artifact.access_compartments
                or not set(manifest.evaluator_compartments).issubset(
                    artifact.access_compartments
                )
            ):
                raise TheoryValidationError(
                    "sealed blind artifacts must retain holdout and evaluator compartments"
                )
        required_relation_pairs = (
            ("seals", manifest_ref, manifest.gold_package_ref),
            ("transforms", variant_ref, variant.transformed_brief_ref),
        )
        for relation_type, source, target in required_relation_pairs:
            if not any(
                relation.relation_type == relation_type
                and relation.source == source
                and relation.target == target
                for relation in produced_relations
            ):
                raise TheoryValidationError(
                    f"{relation_type} must bind the exact blind-case objects"
                )
    elif route_id == "evaluate.blind_argument_package":
        comparison_ref, comparison = exactly_one("VAPComparisonRecord")
        if not isinstance(comparison, t.VAPComparisonRecord):
            raise TheoryValidationError("evaluation emitted a malformed comparison")
        manifest_refs = input_by_type.get("BlindCaseManifest", ())
        variant_refs = input_by_type.get("TransformedVariantManifest", ())
        brief_refs = input_by_type.get("PreResultBrief", ())
        package_refs = set(input_by_type.get("ValidatedArgumentPackage", ()))
        if (
            len(manifest_refs) != 1
            or len(variant_refs) != 1
            or len(brief_refs) != 1
            or len(package_refs) != 2
            or comparison.case_manifest_ref != manifest_refs[0]
            or comparison.candidate_package_ref not in package_refs
            or comparison.gold_package_ref not in package_refs
            or comparison.candidate_package_ref == comparison.gold_package_ref
            or comparison.evaluator != transaction_actor
        ):
            raise TheoryValidationError(
                "evaluator comparison does not bind the exact focused attempt objects and actor"
            )
        manifest = payload_index[_entity_key(manifest_refs[0])]
        variant = payload_index[_entity_key(variant_refs[0])]
        candidate = payload_index[_entity_key(comparison.candidate_package_ref)]
        if (
            not isinstance(manifest, t.BlindCaseManifest)
            or not isinstance(variant, t.TransformedVariantManifest)
            or not isinstance(candidate, t.ValidatedArgumentPackage)
            or comparison.attempt_id != manifest.attempt_id
            or variant.base_case_manifest_ref != manifest_refs[0]
            or variant.transformed_brief_ref != brief_refs[0]
            or manifest.gold_package_ref != comparison.gold_package_ref
            or candidate.generator_actor is None
            or candidate.generator_actor == transaction_actor
        ):
            raise TheoryValidationError(
                "comparison violates sealed attempt lineage or evaluator independence"
            )
        evidence_artifact_refs = {
            reference
            for reference in transaction_evidence_refs
            if isinstance(reference, ArtifactDependencyRef)
        }
        sealed_refs = {
            reference
            for payload in (manifest, variant)
            for reference in _walk_exact_refs(payload)
            if isinstance(reference, ArtifactDependencyRef)
        }
        sealed_refs.add(comparison.candidate_lock_ref)
        if not sealed_refs.issubset(evidence_artifact_refs):
            raise TheoryValidationError(
                "evaluation evidence omits a sealed probe, key, transform, signature, or candidate lock"
            )
        produced_artifact_refs = {
            ArtifactDependencyRef(
                artifact_id=item.artifact_id,
                version=item.version,
                content_hash=item.content_hash,
            )
            for item in produced_artifacts
        }
        if set(comparison.evaluator_evidence_refs) != produced_artifact_refs:
            raise TheoryValidationError(
                "comparison evaluator evidence must equal the exact produced artifacts"
            )
        comparison_entity = entity_index[_entity_key(comparison_ref)]
        comparison_artifact_refs = {
            reference
            for reference in _walk_exact_refs(comparison)
            if isinstance(reference, ArtifactDependencyRef)
        }
        if set(comparison_entity.artifact_refs) != comparison_artifact_refs:
            raise TheoryValidationError(
                "comparison envelope omits an exact artifact dependency"
            )
        if not any(
            relation.relation_type == "compares_to"
            and relation.source == comparison_ref
            and relation.target == comparison.candidate_package_ref
            for relation in produced_relations
        ):
            raise TheoryValidationError(
                "comparison must point to its exact candidate package"
            )


def validate_phase2_route_transaction(
    snapshot: Snapshot,
    transaction: Transaction,
    route_spec: RouteSpecV2,
    *,
    route_input_refs: Iterable[EntityVersionRef] | None = None,
    allow_fresh_repair: bool = False,
    allow_research_question_revision: bool = False,
) -> TheoryReadinessReport:
    """Validate Phase 2-specific semantics for one staged v2 route transaction."""

    if transaction.origin != "route_run" or transaction.route_id != route_spec.route_id:
        raise TheoryValidationError("transaction is not bound to the supplied v2 route")
    if route_spec.availability != "enabled":
        raise TheoryValidationError("a not-implemented v2 route cannot commit")
    if route_spec.exit_validator_id not in {
        "theory_route_exit.v1",
        "evaluation_route_exit.v1",
    }:
        raise TheoryValidationError("unknown or missing Phase 2 route exit validator")
    entry_report = _validate_route_entry_refs(
        snapshot,
        route_spec,
        (
            route_input_refs
            if route_input_refs is not None
            else (
                reference
                for reference in transaction.evidence_refs
                if isinstance(reference, EntityVersionRef)
            )
        ),
        actor=transaction.actor,
        allow_fresh_repair=allow_fresh_repair,
    )

    entities = list(snapshot.entity_versions)
    artifacts = list(snapshot.artifacts)
    decisions = list(snapshot.decisions)
    produced: set[tuple[object, ...]] = set()
    scientific_outputs: set[tuple[object, ...]] = set()
    produced_entity_refs: list[EntityVersionRef] = []
    produced_relations: list[RelationVersion] = []
    produced_artifacts: list[ArtifactRegistration] = []
    outcome_ops: list[RecordRouteOutcomeOp] = []
    dossier_ids_written = {
        operation.entity.entity_id
        for operation in transaction.operations
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp))
        and operation.entity.entity_type == "GateDossier"
    }
    prior_entity_index = {
        (entity.entity_id, entity.version): entity
        for entity in snapshot.entity_versions
    }
    for operation in transaction.operations:
        if operation.op not in route_spec.allowed_operations:
            raise TheoryValidationError(f"operation {operation.op} is outside the v2 route contract")
        if isinstance(operation, (CreateEntityOp, SupersedeEntityOp)):
            entity = operation.entity
            if entity.entity_type not in route_spec.allowed_entity_types:
                raise TheoryValidationError(
                    f"output entity type {entity.entity_type} is outside the v2 route allowlist"
                )
            previous = None
            if isinstance(operation, SupersedeEntityOp):
                previous = prior_entity_index.get(
                    (operation.previous.entity_id, operation.previous.version)
                )
            validate_theory_entity(entity, previous)
            entities.append(entity)
            ref = EntityVersionRef(entity_id=entity.entity_id, version=entity.version)
            produced_entity_refs.append(ref)
            produced.add(_canonical_ref_key(ref))
            scientific_outputs.add(_canonical_ref_key(ref))
        elif isinstance(operation, (CreateRelationOp, SupersedeRelationOp)):
            relation = operation.relation
            if relation.relation_type not in route_spec.allowed_relation_types:
                raise TheoryValidationError(
                    f"output relation type {relation.relation_type} is outside the v2 route allowlist"
                )
            ref = RelationVersionRef(relation_id=relation.relation_id, version=relation.version)
            produced_relations.append(relation)
            produced.add(_canonical_ref_key(ref))
            scientific_outputs.add(_canonical_ref_key(ref))
        elif isinstance(operation, RegisterArtifactOp):
            artifacts.append(operation.artifact)
            produced_artifacts.append(operation.artifact)
            produced.add(
                _canonical_ref_key(
                    ArtifactDependencyRef(
                        artifact_id=operation.artifact.artifact_id,
                        version=operation.artifact.version,
                        content_hash=operation.artifact.content_hash,
                    )
                )
            )
        elif isinstance(operation, (RecordDecisionOp, SupersedeDecisionOp)):
            if operation.decision.decision_kind in _GATE_RANK and operation.decision.status == "confirmed":
                raise TheoryValidationError("G1-G5 confirmation must be a later human Decision transaction")
            if any(item in dossier_ids_written for item in operation.decision.evidence_refs):
                raise TheoryValidationError("a Decision cannot cite a GateDossier from the same transaction")
            decisions.append(operation.decision)
            produced.add(
                _canonical_ref_key(
                    DecisionVersionRef(
                        decision_id=operation.decision.decision_id,
                        version=operation.decision.version,
                    )
                )
            )
        elif isinstance(operation, RecordBlockerOp):
            produced.add(
                _canonical_ref_key(BlockerRef(blocker_id=operation.blocker.blocker_id))
            )
        elif isinstance(operation, RecordRouteOutcomeOp):
            outcome_ops.append(operation)

    output_entity_counts: dict[str, int] = {}
    for reference in produced_entity_refs:
        output = next(
            item for item in entities if _entity_key(item) == _entity_key(reference)
        )
        output_entity_counts[output.entity_type] = (
            output_entity_counts.get(output.entity_type, 0) + 1
        )
    _validate_requirement_counts(
        route_spec.required_output_entities,
        output_entity_counts,
        type_field="entity_type",
        label=f"route {route_spec.route_id} output",
    )
    output_relation_counts: dict[str, int] = {}
    for relation in produced_relations:
        output_relation_counts[relation.relation_type] = (
            output_relation_counts.get(relation.relation_type, 0) + 1
        )
    _validate_requirement_counts(
        route_spec.required_output_relations,
        output_relation_counts,
        type_field="relation_type",
        label=f"route {route_spec.route_id} relation output",
    )

    if len(outcome_ops) != 1:
        raise TheoryValidationError("a v2 route transaction requires exactly one RouteOutcome")
    outcome = outcome_ops[0].outcome
    if outcome.route_id != route_spec.route_id or outcome.route_run_id != transaction.route_run_id:
        raise TheoryValidationError("RouteOutcome is not bound to the exact route run")
    if (
        route_spec.route_id == "validate.argument_package"
        and outcome.outcome != "completed_with_candidate"
    ):
        raise TheoryValidationError(
            "the agent may only propose a G5 candidate; it cannot mark the package validated"
        )
    if (
        route_spec.exit_validator_id == "evaluation_route_exit.v1"
        and outcome.outcome != "completed_with_candidate"
    ):
        raise TheoryValidationError(
            "evaluation routes record evidence candidates; they cannot self-declare validation"
        )
    candidate_keys = {_canonical_ref_key(ref) for ref in outcome.candidate_refs}
    if not candidate_keys.issubset(produced):
        raise TheoryValidationError("RouteOutcome contains a candidate not produced by this transaction")
    if outcome.outcome in {"completed_with_candidate", "validated"}:
        if not scientific_outputs.issubset(candidate_keys):
            raise TheoryValidationError("RouteOutcome omits an exact scientific output candidate")
    elif scientific_outputs:
        raise TheoryValidationError("failed/rejected route outcomes cannot commit scientific outputs")

    current_entity_versions = {
        **snapshot.current_entities,
        **{
            item.entity_id: item.version
            for item in entities[len(snapshot.entity_versions):]
        },
    }
    current_artifact_versions = {
        **snapshot.current_artifacts,
        **{
            item.artifact_id: item.version
            for item in artifacts[len(snapshot.artifacts):]
        },
    }
    current_decision_versions = {
        **snapshot.current_decisions,
        **{
            item.decision_id: item.version
            for item in decisions[len(snapshot.decisions):]
        },
    }
    projection_report = validate_theory_projection(
        entities,
        artifacts,
        decisions,
        current_entities=current_entity_versions,
        current_artifacts=current_artifact_versions,
        current_decisions=current_decision_versions,
    )
    blocked_package_refs = set(projection_report.production_blocked_package_refs)
    for reference in produced_entity_refs:
        entity = next(item for item in entities if _entity_key(item) == _entity_key(reference))
        if entity.entity_type != "ValidatedArgumentPackage":
            continue
        package = t.parse_theory_entity(entity)
        if (
            isinstance(package, t.ValidatedArgumentPackage)
            and package.release_mode == "production_candidate"
            and reference in blocked_package_refs
        ):
            raise TheoryValidationError(
                "validate.argument_package cannot commit a blocked production VAP"
            )

    entity_index = {_entity_key(item): item for item in entities}
    payload_index = {
        _entity_key(item): validate_theory_entity(item)
        for item in entities
        if item.entity_type in t.THEORY_PAYLOAD_MODELS
        and t.is_packed_theory_entity(item)
    }
    output_root: EntityVersionRef | None = None
    if route_spec.exit_validator_id == "theory_route_exit.v1":
        root_memo: dict[tuple[str, int], frozenset[EntityVersionRef]] = {}
        output_root_sets: list[frozenset[EntityVersionRef]] = []
        for reference in produced_entity_refs:
            output_root_sets.append(
                _research_question_roots(
                    reference, entity_index, payload_index, memo=root_memo
                )
            )
        for relation in produced_relations:
            output_root_sets.extend(
                (
                    _research_question_roots(
                        relation.source, entity_index, payload_index, memo=root_memo
                    ),
                    _research_question_roots(
                        relation.target, entity_index, payload_index, memo=root_memo
                    ),
                )
            )
        if any(len(roots) != 1 for roots in output_root_sets):
            raise TheoryValidationError(
                "every v2 scientific output and relation endpoint must resolve to one exact ResearchQuestion"
            )
        output_roots = {next(iter(roots)) for roots in output_root_sets}
        if len(output_roots) > 1:
            raise TheoryValidationError(
                "one v2 route transaction cannot mix ResearchQuestion scopes"
            )
        output_root = next(iter(output_roots), None)
    elif route_spec.exit_validator_id != "evaluation_route_exit.v1":
        raise TheoryValidationError("unknown Phase 2 route exit validator")

    required_gate_ids = {item.decision_id for item in entry_report.gate_decision_refs}
    missing_gate_ids = required_gate_ids.difference(transaction.authority_basis)
    if missing_gate_ids:
        raise TheoryValidationError(
            "route authority_basis is missing required fresh gate Decisions: "
            + ", ".join(sorted(missing_gate_ids))
        )
    known_gate_ids = {
        item.decision_id for item in snapshot.decisions if item.decision_kind in _GATE_RANK
    }
    extra_gate_ids = set(transaction.authority_basis).intersection(
        known_gate_ids
    ).difference(required_gate_ids)
    if extra_gate_ids:
        raise TheoryValidationError(
            "route authority_basis contains an unrelated or foreign G1-G5 Decision: "
            + ", ".join(sorted(extra_gate_ids))
        )
    root_is_authorized_revision = (
        allow_research_question_revision
        and entry_report.research_question_ref is not None
        and output_root is not None
        and output_root.entity_id == entry_report.research_question_ref.entity_id
        and output_root.version == entry_report.research_question_ref.version + 1
    )
    if (
        entry_report.research_question_ref is not None
        and output_root is not None
        and output_root != entry_report.research_question_ref
        and not root_is_authorized_revision
    ):
        raise TheoryValidationError(
            "route inputs, required gates, and outputs govern different ResearchQuestion scopes"
        )

    expected_gate = _DOSSIER_ROUTE_GATE.get(route_spec.route_id)
    if expected_gate is not None:
        for entity in entities[len(snapshot.entity_versions):]:
            if entity.entity_type == "GateDossier":
                dossier = t.parse_theory_entity(entity)
                if not isinstance(dossier, t.GateDossier) or dossier.gate_kind != expected_gate:
                    raise TheoryValidationError("route emitted the wrong GateDossier kind")

    _validate_phase2_route_exit_semantics(
        route_spec,
        entry_report,
        tuple(produced_entity_refs),
        tuple(produced_relations),
        tuple(produced_artifacts),
        transaction.actor,
        tuple(transaction.evidence_refs),
        entity_index,
        payload_index,
    )

    return projection_report


__all__ = [
    "TheoryReadinessReport",
    "TheoryRouteEntryReport",
    "TheoryValidationError",
    "has_current_fresh_g1_decomposition_package",
    "is_falsified_verification_repair_root",
    "validate_phase2_human_gate_transaction",
    "validate_phase2_route_transaction",
    "validate_phase2_route_entry",
    "validate_theory_entity",
    "validate_theory_projection",
]
