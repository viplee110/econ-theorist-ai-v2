"""Executable invariants for the Phase 3 authoring payload namespace."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from tests.helpers import REPOSITORY_ROOT

from econ_theorist.authoring import (
    AUTHORING_PAYLOAD_MODELS,
    AUTHORING_PAYLOAD_OWNER_FACETS,
    AUTHORING_READY_CHECK_ORDER,
    AuthoringReadyCheck,
    ClaimProjection,
    ConsequentialSpan,
    CriticAssignment,
    EconomicOntologyEntry,
    EntailmentCheck,
    FormalFidelityAssessment,
    HumanEffortEvent,
    HumanEffortRecord,
    InformationGrant,
    ManuscriptLocation,
    ManuscriptUnit,
    NarrativeSpine,
    PaperIR,
    ReaderBeliefState,
    ReaderKnowledgeItem,
    ReaderPath,
    ReaderProbeDescriptor,
    READER_PROBE_KIND_ORDER,
    ReaderProbeSet,
    ReaderResponse,
    ReaderStateEdge,
    ReviewClosure,
    SectionContract,
    TerminologyRealization,
    pack_authoring_payload,
    parse_authoring_payload,
    validate_human_effort_update,
    validate_manuscript_unit_update,
)
from econ_theorist.codec import canonical_json_bytes
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    DecisionVersionRef,
    EntityVersionRef,
    SemanticFacetRef,
)
from scripts.export_authoring_schemas import check, rendered_schemas


DIGEST_A = "a" * 64
DIGEST_B = "b" * 64
DIGEST_C = "c" * 64


def actor(actor_id: str, kind: str = "agent") -> Actor:
    return Actor(kind=kind, actor_id=actor_id)


def eref(entity_id: str, version: int = 1) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=version)


def dref(decision_id: str, version: int = 1) -> DecisionVersionRef:
    return DecisionVersionRef(decision_id=decision_id, version=version)


def aref(
    artifact_id: str, digest: str = DIGEST_A, version: int = 1
) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id,
        version=version,
        content_hash=digest,
    )


def sref(
    field_path: str,
    *,
    facet: str = "formal",
    digest: str = DIGEST_A,
) -> SemanticFacetRef:
    return SemanticFacetRef(
        entity_id="claim.graph",
        version=1,
        facet=facet,
        field_path=field_path,
        semantic_hash=digest,
    )


def paper_ir(*, mode: str = "preview") -> PaperIR:
    values = {
        "compiler_mode": mode,
        "package_ref": eref("package.validated"),
        "assurance_bundle_ref": None,
        "g5_decision_ref": None,
        "manuscript_version_promotion_ref": None,
        "source_state_revision": DIGEST_A,
        "upstream_projection_hash": DIGEST_B,
        "language": "English",
        "resolved_profile_manifest_ref": eref("profile.universal"),
        "claim_projections": (
            ClaimProjection(
                projection_id="projection.reversal",
                claim_graph_ref=eref("claim.graph"),
                claim_id="claim.reversal",
                formal_statement="Accuracy is lower under high precision in the stated interval.",
                scope="Binary state, indivisible processing, and interior precision levels.",
                assumption_ids=("assumption.indivisible",),
                semantic_translation="Precision can reduce realized accuracy by deterring processing.",
                formal_statement_source=sref("/claims/0/formal_statement"),
                scope_source=sref("/claims/0/scope", digest=DIGEST_B),
                assumption_source_refs=(
                    sref("/claims/0/assumption_ids", digest=DIGEST_C),
                ),
                translation_source=sref(
                    "/claims/0/semantic_translation",
                    facet="economic_interpretation",
                ),
                allowed_wording_strength="entailed_equivalent",
                permitted_locations=("section.results",),
                prohibited_extensions=("Do not claim that coarse information always wins.",),
            ),
        ),
        "ontology": (
            EconomicOntologyEntry(
                object_id="object.processing",
                formal_symbol="d",
                preferred_economic_name="processing decision",
                short_definition="Whether the receiver processes the signal.",
                economic_interpretation="The extensive attention margin.",
                mechanism_role="It converts precision into a participation tradeoff.",
                allowed_aliases=("attention decision",),
                forbidden_names=("estimator",),
                first_use_section_id="section.results",
            ),
        ),
        "narrative_spine": NarrativeSpine(
            phenomenon_or_question="Can better information reduce realized accuracy?",
            natural_benchmark="Conditional on processing, precision improves accuracy.",
            unresolved_benchmark_delta="The benchmark holds processing fixed.",
            new_economic_or_conceptual_object="A precision-linked extensive attention margin.",
            central_result="High precision can deter processing over an exact interval.",
            why_not_immediate="Gross value and processing cost move at different rates.",
            boundary_and_failure_conditions="The reversal disappears with fixed processing cost.",
            economic_consequence_or_changed_practice="Information quality cannot be ranked independently of uptake.",
            literature_update="The result adds an endogenous-processing qualification.",
            source_refs=(eref("package.validated"),),
        ),
        "canonical_writer": actor("writer.canonical"),
        "preview_label": "PREVIEW — not authoring ready",
        "built_at": "2026-07-12T10:00:00Z",
    }
    if mode in {"working", "submission"}:
        values.update(
            assurance_bundle_ref=eref("assurance.bundle"),
            g5_decision_ref=dref("gate.g5"),
            preview_label=None,
        )
    if mode == "submission":
        values["manuscript_version_promotion_ref"] = dref("promotion.manuscript")
    return PaperIR(**values)


def reader_path() -> ReaderPath:
    background = ReaderKnowledgeItem(
        knowledge_id="knowledge.binary_state",
        content="The state and action are binary.",
        origin="target_audience_background",
    )
    benchmark = ReaderKnowledgeItem(
        knowledge_id="knowledge.benchmark",
        content="Conditional accuracy rises with precision.",
        origin="delivered_update",
        producer_state_id="state.benchmark",
    )
    mechanism = ReaderKnowledgeItem(
        knowledge_id="knowledge.mechanism",
        content="Precision also changes the processing decision.",
        origin="delivered_update",
        producer_state_id="state.mechanism",
    )
    first = ReaderBeliefState(
        state_id="state.benchmark",
        known_on_entry=(background.knowledge_id,),
        default_expectation="Higher precision improves accuracy.",
        live_question="What does the benchmark hold fixed?",
        update="It conditions on processing.",
        delivered_knowledge_ids=(benchmark.knowledge_id,),
        support_refs=(eref("benchmark.set"),),
        transfer_objective="Separate conditional value from information uptake.",
        unresolved_on_exit="Whether precision changes uptake.",
    )
    second = ReaderBeliefState(
        state_id="state.mechanism",
        known_on_entry=(background.knowledge_id, benchmark.knowledge_id),
        default_expectation="The conditional comparison determines realized accuracy.",
        live_question="Can precision deter processing?",
        update="A convex precision-linked cost creates an extensive-margin reversal.",
        delivered_knowledge_ids=(mechanism.knowledge_id,),
        support_refs=(eref("argument.graph"),),
        transfer_objective="Reconstruct the reversal and its boundary.",
        unresolved_on_exit="How the exact threshold interval is derived.",
    )
    section = SectionContract(
        section_id="section.results",
        role="result_block",
        entry_state_id=first.state_id,
        exit_state_id=second.state_id,
        central_question="When does precision deter processing?",
        required_claim_projection_ids=("projection.reversal",),
        claims_introduced=("claim.reversal",),
        economic_object_ids_to_interpret=("object.processing",),
        reader_update_on_exit="The reader can explain the extensive-margin reversal.",
        open_question_for_next_section="Which assumptions are essential?",
        reader_cost_constraint="Introduce only the processing threshold before the theorem.",
        appendix_boundary="main_text",
    )
    return ReaderPath(
        paper_ir_ref=eref("paper.ir"),
        knowledge_items=(background, benchmark, mechanism),
        reader_states=(first, second),
        state_edges=(
            ReaderStateEdge(
                source_state_id=first.state_id,
                target_state_id=second.state_id,
            ),
        ),
        section_contracts=(section,),
        ordered_section_ids=(section.section_id,),
        built_at="2026-07-12T10:05:00Z",
    )


def manuscript_unit(
    *,
    artifact: ArtifactDependencyRef | None = None,
    generation: int = 1,
    previous_unit_ref: EntityVersionRef | None = None,
    previous_artifact_ref: ArtifactDependencyRef | None = None,
    revision_brief_ref: EntityVersionRef | None = None,
) -> ManuscriptUnit:
    span = ConsequentialSpan(
        assertion_id="assertion.theorem",
        role="formal_statement",
        claim_projection_id="projection.reversal",
        claim_graph_ref=eref("claim.graph"),
        claim_id="claim.reversal",
        source_fields=(sref("/claims/0/formal_statement"),),
        scope="Binary state and indivisible processing.",
        assumption_ids=("assumption.indivisible",),
        support_refs=(eref("verification.bundle"),),
        location=ManuscriptLocation(start_offset=0, end_offset=42),
        text_hash=DIGEST_B,
        wording_strength="exact",
        presentation="theorem_statement",
    )
    manuscript_artifact = artifact or aref("manuscript.results")
    return ManuscriptUnit(
        unit_id="unit.results",
        paper_ir_ref=eref("paper.ir"),
        reader_path_ref=eref("reader.path"),
        result_contract_set_ref=eref("result.contracts"),
        section_contract_id="section.results",
        manuscript_artifact_ref=manuscript_artifact,
        source_state_revision=DIGEST_C,
        canonical_writer=actor("writer.canonical"),
        writer_role_packet_hash=DIGEST_A,
        writer_output_hash=manuscript_artifact.content_hash,
        integration_generation=generation,
        previous_manuscript_unit_ref=previous_unit_ref,
        previous_manuscript_artifact_ref=previous_artifact_ref,
        revision_brief_ref=revision_brief_ref,
        spans=(span,),
        terminology=(
            TerminologyRealization(
                object_id="object.processing",
                realized_name="processing decision",
                formal_symbol="d",
                first_use_assertion_id=span.assertion_id,
            ),
        ),
        composed_at="2026-07-12T10:10:00Z",
    )


def effort_event(
    event_id: str,
    occurred_at: str,
    *,
    note: str = "Clarified the extensive-margin mechanism.",
) -> HumanEffortEvent:
    return HumanEffortEvent(
        event_id=event_id,
        occurred_at=occurred_at,
        active_minutes=12,
        affected_assertion_ids=("assertion.theorem",),
        disposition="light_edit",
        severity="medium",
        category="mechanism_intuition_repair",
        before_artifact_ref=aref(f"before.{event_id}"),
        after_artifact_ref=aref(f"after.{event_id}", DIGEST_B),
        note=note,
    )


class RegistryAndSchemaTests(unittest.TestCase):
    def test_registry_has_exactly_fifteen_independently_owned_payloads(self) -> None:
        expected = {
            "AssuranceBundle",
            "CriticAssignment",
            "HumanEffortRecord",
            "ManuscriptUnit",
            "PaperIR",
            "ReaderPath",
            "ReaderProbeSet",
            "ReaderResponse",
            "ReDerivationRecord",
            "ResolvedProfileManifest",
            "ResultContractSet",
            "ReviewClosure",
            "ReviewFinding",
            "ReviewRecord",
            "RevisionBrief",
        }
        self.assertEqual(set(AUTHORING_PAYLOAD_MODELS), expected)
        self.assertEqual(set(AUTHORING_PAYLOAD_OWNER_FACETS), expected)
        self.assertEqual(len(rendered_schemas()), 15)
        self.assertTrue(check(REPOSITORY_ROOT / "schemas" / "authoring" / "v1"))

    def test_all_registered_models_are_strict_and_schemas_forbid_floats_and_extras(self) -> None:
        def inspect_objects(node: object) -> None:
            if isinstance(node, dict):
                if node.get("type") == "object" and "properties" in node:
                    self.assertFalse(node.get("additionalProperties", True))
                for value in node.values():
                    inspect_objects(value)
            elif isinstance(node, list):
                for value in node:
                    inspect_objects(value)

        for name, model in AUTHORING_PAYLOAD_MODELS.items():
            with self.subTest(model=name):
                self.assertEqual(model.model_config.get("extra"), "forbid")
                self.assertTrue(model.model_config.get("strict"))
                self.assertTrue(model.model_config.get("frozen"))
                schema = model.model_json_schema(mode="validation")
                self.assertNotIn(b'"type":"number"', canonical_json_bytes(schema))
                inspect_objects(schema)

    def test_typed_envelope_round_trip_and_extra_field_fail_closed(self) -> None:
        record = HumanEffortRecord(
            manuscript_unit_ref=eref("manuscript.unit"),
            human=actor("human.author", "human"),
            events=(effort_event("effort.001", "2026-07-12T11:00:00Z"),),
            recorded_at="2026-07-12T11:05:00Z",
        )
        facets = pack_authoring_payload(record)
        self.assertEqual(parse_authoring_payload("HumanEffortRecord", facets), record)
        tampered = facets.model_dump(mode="python")
        tampered["authority"]["payload"]["self_certified_ready"] = True
        with self.assertRaises(ValidationError):
            parse_authoring_payload("HumanEffortRecord", tampered)


class PaperIRAndReaderPathTests(unittest.TestCase):
    def test_preview_may_omit_assurance_but_working_and_submission_cannot(self) -> None:
        preview = paper_ir(mode="preview")
        self.assertIsNone(preview.assurance_bundle_ref)
        self.assertIsNone(preview.g5_decision_ref)
        self.assertIsNotNone(preview.preview_label)

        working = paper_ir(mode="working")
        self.assertIsNotNone(working.assurance_bundle_ref)
        self.assertIsNotNone(working.g5_decision_ref)

        missing_assurance = working.model_dump(mode="python")
        missing_assurance["assurance_bundle_ref"] = None
        with self.assertRaisesRegex(ValidationError, "AssuranceBundle"):
            PaperIR(**missing_assurance)

        missing_promotion = working.model_dump(mode="python")
        missing_promotion["compiler_mode"] = "submission"
        with self.assertRaisesRegex(ValidationError, "promotion"):
            PaperIR(**missing_promotion)
        self.assertIsNotNone(paper_ir(mode="submission").manuscript_version_promotion_ref)

    def test_reader_path_accepts_only_closed_acyclic_prerequisites(self) -> None:
        valid = reader_path()
        self.assertEqual(valid.ordered_section_ids, ("section.results",))

        cyclic = valid.model_dump(mode="python")
        cyclic["state_edges"] = (*valid.state_edges, ReaderStateEdge(
            source_state_id="state.mechanism",
            target_state_id="state.benchmark",
        ))
        with self.assertRaisesRegex(ValidationError, "acyclic"):
            ReaderPath(**cyclic)

        premature = valid.model_dump(mode="python")
        first = valid.reader_states[0]
        premature_first = ReaderBeliefState(
            **{
                **first.model_dump(mode="python"),
                "known_on_entry": (*first.known_on_entry, "knowledge.mechanism"),
            }
        )
        premature["reader_states"] = (premature_first, valid.reader_states[1])
        with self.assertRaisesRegex(ValidationError, "not delivered by an ancestor"):
            ReaderPath(**premature)


class EntailmentAndColdReaderTests(unittest.TestCase):
    def test_entailment_uses_a_closed_noncompensatory_lattice(self) -> None:
        passed = EntailmentCheck(
            assertion_id="assertion.translation",
            scope_relation="subset",
            conclusion_relation="weaker",
            assumptions_preserved=True,
            source_refs=(eref("claim.graph"),),
            outcome="passed",
            rationale="The prose narrows both scope and conclusion.",
        )
        self.assertEqual(passed.outcome, "passed")

        for update in (
            {"scope_relation": "stronger"},
            {"conclusion_relation": "unsupported"},
            {"assumptions_preserved": False},
        ):
            values = {**passed.model_dump(mode="python"), **update}
            with self.subTest(update=update), self.assertRaisesRegex(
                ValidationError, "entailment outcome disagrees"
            ):
                EntailmentCheck(**values)

        invalid_label = passed.model_dump(mode="python")
        invalid_label["conclusion_relation"] = "roughly_similar"
        with self.assertRaises(ValidationError):
            EntailmentCheck(**invalid_label)

        failed_span = EntailmentCheck(
            assertion_id="assertion.overclaim",
            scope_relation="stronger",
            conclusion_relation="unsupported",
            assumptions_preserved=False,
            source_refs=(eref("claim.graph"),),
            outcome="failed",
            rationale="The prose exceeds the proved scope.",
        )
        with self.assertRaisesRegex(ValidationError, "cannot hide a failed span"):
            FormalFidelityAssessment(
                theorem_statement_exact=True,
                scope_preserved=True,
                assumptions_preserved=True,
                proof_language_honest=True,
                numerical_evidence_bounded=True,
                entailment_checks=(failed_span,),
            )

    def test_cold_reader_protocol_requires_four_distinct_real_actors(self) -> None:
        probes = tuple(
            ReaderProbeDescriptor(
                probe_id=f"probe.{kind}",
                kind=kind,
                prompt_hash=DIGEST_A,
                target_contract_ids=("contract.result",),
            )
            for kind in READER_PROBE_KIND_ORDER
        )
        values = {
            "assignment_ref": eref("assignment.cold"),
            "manuscript_unit_ref": eref("manuscript.unit"),
            "frozen_manuscript_artifact_ref": aref("manuscript.frozen"),
            "probe_designer": actor("reader.probe_designer"),
            "respondent": actor("reader.respondent"),
            "adjudicator": actor("reader.adjudicator"),
            "canonical_writer": actor("writer.canonical"),
            "transfer_objective": "Apply the mechanism to a nearby precision-cost case.",
            "probes": probes,
            "probe_artifact_ref": aref("reader.probes"),
            "answer_key_artifact_ref": aref("reader.answer_key", DIGEST_B),
            "route_run_id": "run.reader_probe",
            "context_manifest_hash": DIGEST_A,
            "sealed_at": "2026-07-12T12:00:00Z",
        }
        probe_set = ReaderProbeSet(**values)
        self.assertNotEqual(probe_set.probe_artifact_ref, probe_set.answer_key_artifact_ref)

        with self.assertRaisesRegex(ValidationError, "must be unique"):
            ReaderProbeSet(**{**values, "respondent": values["canonical_writer"]})
        with self.assertRaisesRegex(ValidationError, "human or agent"):
            ReaderProbeSet(
                **{**values, "adjudicator": actor("tool.adjudicator", "deterministic_tool")}
            )

        assignment = CriticAssignment(
            assignment_id="assignment.cold",
            role="cold_reader",
            paper_ir_ref=eref("paper.ir"),
            reader_path_ref=eref("reader.path"),
            result_contract_set_ref=eref("result.contracts"),
            assigned_actor=values["respondent"],
            canonical_writer=values["canonical_writer"],
            probe_designer=values["probe_designer"],
            adjudicator=values["adjudicator"],
            allowed_information=(
                InformationGrant(
                    information_kind="manuscript_unit",
                    source_refs=(eref("manuscript.unit"),),
                    description="Only the frozen manuscript and visible probes.",
                ),
            ),
            forbidden_context=(
                "No hidden probes, answer key, or other critic material.",
            ),
            transfer_objective=values["transfer_objective"],
            sealed_context_hash=DIGEST_C,
            sealed_at="2026-07-12T11:55:00Z",
        )
        self.assertEqual(assignment.assigned_actor, probe_set.respondent)
        self.assertNotIn("answer_key_artifact_ref", ReaderResponse.model_fields)
        self.assertEqual(
            tuple(item.kind for item in probe_set.probes), READER_PROBE_KIND_ORDER
        )


class ClosureRevisionAndEffortTests(unittest.TestCase):
    def test_review_closure_requires_exactly_thirteen_ordered_passing_checks(self) -> None:
        checks = tuple(
            AuthoringReadyCheck(
                check_id=check_id,
                outcome="passed",
                evidence_refs=(eref(f"evidence.{index}"),),
                rationale=f"Predicate component {check_id} passed.",
            )
            for index, check_id in enumerate(AUTHORING_READY_CHECK_ORDER, start=1)
        )
        ready = ReviewClosure(
            compiler_mode="working",
            paper_ir_ref=eref("paper.ir"),
            reader_path_ref=eref("reader.path"),
            result_contract_set_ref=eref("result.contracts"),
            assurance_bundle_ref=eref("assurance.bundle"),
            manuscript_unit_ref=eref("manuscript.unit"),
            formal_fidelity_review_ref=eref("review.formal"),
            economic_reader_review_ref=eref("review.economic"),
            cold_reader_review_ref=eref("review.cold"),
            closure_actor=actor("tool.authoring_ready", "deterministic_tool"),
            checks=checks,
            status="authoring_ready",
            evaluated_at="2026-07-12T13:00:00Z",
        )
        self.assertEqual(len(ready.checks), 13)
        self.assertEqual(tuple(item.check_id for item in ready.checks), AUTHORING_READY_CHECK_ORDER)

        preview = ready.model_dump(mode="python")
        preview["compiler_mode"] = "preview"
        with self.assertRaisesRegex(ValidationError, "preview"):
            ReviewClosure(**preview)

        reordered = ready.model_dump(mode="python")
        reordered["checks"] = (checks[1], checks[0], *checks[2:])
        with self.assertRaisesRegex(ValidationError, "canonical predicate order"):
            ReviewClosure(**reordered)

        failed = ready.model_dump(mode="python")
        failed_checks = list(checks)
        failed_checks[0] = AuthoringReadyCheck(
            **{**checks[0].model_dump(mode="python"), "outcome": "failed"}
        )
        failed["checks"] = tuple(failed_checks)
        with self.assertRaisesRegex(ValidationError, "every check"):
            ReviewClosure(**failed)

    def test_manuscript_revision_binds_exact_prior_artifact_and_stable_contract(self) -> None:
        previous = manuscript_unit()
        current = manuscript_unit(
            artifact=aref("manuscript.results", DIGEST_B, version=2),
            generation=2,
            previous_unit_ref=eref("manuscript.unit", version=1),
            previous_artifact_ref=previous.manuscript_artifact_ref,
            revision_brief_ref=eref("revision.brief"),
        )
        validate_manuscript_unit_update(previous, current)

        wrong_artifact = current.model_copy(
            update={"previous_manuscript_artifact_ref": aref("manuscript.other")}
        )
        with self.assertRaisesRegex(ValueError, "exact prior artifact"):
            validate_manuscript_unit_update(previous, wrong_artifact)

        changed_contract = current.model_copy(update={"section_contract_id": "section.other"})
        with self.assertRaisesRegex(ValueError, "section_contract_id"):
            validate_manuscript_unit_update(previous, changed_contract)

        with self.assertRaisesRegex(ValidationError, "prior unit, artifact, and brief"):
            manuscript_unit(generation=2)

    def test_human_effort_supersession_is_byte_exact_append_only(self) -> None:
        first_event = effort_event("effort.001", "2026-07-12T11:00:00Z")
        previous = HumanEffortRecord(
            manuscript_unit_ref=eref("manuscript.unit"),
            human=actor("human.author", "human"),
            events=(first_event,),
            recorded_at="2026-07-12T11:05:00Z",
        )
        current = HumanEffortRecord(
            manuscript_unit_ref=previous.manuscript_unit_ref,
            human=previous.human,
            events=(
                first_event,
                effort_event("effort.002", "2026-07-12T11:30:00Z"),
            ),
            recorded_at="2026-07-12T11:35:00Z",
        )
        validate_human_effort_update(previous, current)

        rewritten_event = effort_event(
            "effort.001",
            "2026-07-12T11:00:00Z",
            note="Rewrote history after the fact.",
        )
        rewritten = current.model_copy(update={"events": (rewritten_event, current.events[1])})
        with self.assertRaisesRegex(ValueError, "byte-for-byte"):
            validate_human_effort_update(previous, rewritten)

        with self.assertRaisesRegex(ValueError, "append"):
            validate_human_effort_update(previous, previous)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
