"""Phase 3 provider-packet isolation and exact-selector contracts."""

from __future__ import annotations

import base64
import tempfile
import unittest
from collections.abc import Iterable, Mapping

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.authoring import (
    ConsequentialSpan,
    ManuscriptLocation,
    ManuscriptUnit,
    ReaderProbeDescriptor,
    READER_PROBE_KIND_ORDER,
    ReaderProbeSet,
    ReaderResponse,
    TerminologyRealization,
    pack_authoring_payload,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.context import ContextBudgetError, compile_context
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    EntityVersion,
    EntityVersionRef,
    FacetPayloads,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
)
from econ_theorist.route_registry import authorize_route
from econ_theorist.runtime import ObjectStore, StoreLayout
from econ_theorist.theory import (
    AssumptionMap,
    AssumptionRecord,
    ProofObligation,
    pack_theory_payload,
)


PROJECT_ID = "project.phase3.context.isolation"
HEAD = "3" * 64
CREATED_AT = "2026-07-12T00:00:00Z"
PROJECT_RESEARCH = ("project_research",)
BLIND_REDERIVATION = ("blind_rederivation", "project_research")
COLD_READER = ("cold_reader_evaluation", "project_research")

WRITER = Actor(kind="agent", actor_id="agent.canonical.writer")
PROBE_DESIGNER = Actor(kind="agent", actor_id="agent.probe.designer")
RESPONDENT = Actor(kind="agent", actor_id="agent.cold.respondent")
ADJUDICATOR = Actor(kind="agent", actor_id="agent.reader.adjudicator")
REDERIVER = Actor(kind="agent", actor_id="agent.blind.rederiver")


def _typed_entity(
    entity_id: str,
    payload: object,
    *,
    compartments: tuple[str, ...],
) -> EntityVersion:
    if isinstance(payload, (AssumptionMap, ProofObligation)):
        facets = pack_theory_payload(payload)
    else:
        facets = pack_authoring_payload(payload)  # type: ignore[arg-type]
    return EntityVersion(
        entity_id=entity_id,
        entity_type=type(payload).__name__,
        version=1,
        project_id=PROJECT_ID,
        title=entity_id,
        summary=f"Typed {type(payload).__name__} context fixture.",
        status=ScientificStatus(lifecycle="active"),
        facets=facets,
        access_compartments=compartments,
        created_at=CREATED_AT,
    )


def _opaque_excluded_entity(
    entity_id: str,
    entity_type: str,
    secret: str,
    *,
    compartments: tuple[str, ...],
    artifact_refs: tuple[ArtifactDependencyRef, ...] = (),
) -> EntityVersion:
    """Create an intentionally unpacked object that a role must never parse."""

    return EntityVersion(
        entity_id=entity_id,
        entity_type=entity_type,
        version=1,
        project_id=PROJECT_ID,
        title=entity_id,
        summary=secret,
        status=ScientificStatus(lifecycle="active"),
        facets=FacetPayloads(formal={"forbidden_secret": secret}),
        artifact_refs=artifact_refs,
        access_compartments=compartments,
        created_at=CREATED_AT,
    )


def _snapshot(
    entities: Iterable[EntityVersion],
    artifacts: Iterable[ArtifactRegistration] = (),
) -> Snapshot:
    entity_tuple = tuple(entities)
    artifact_tuple = tuple(artifacts)
    return Snapshot(
        project_id=PROJECT_ID,
        head=HEAD,
        chain=(HEAD,),
        entity_versions=entity_tuple,
        artifacts=artifact_tuple,
        current_entities={item.entity_id: item.version for item in entity_tuple},
        current_artifacts={item.artifact_id: item.version for item in artifact_tuple},
    )


def _walk_keys(value: object) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield str(key)
            yield from _walk_keys(nested)
    elif isinstance(value, (tuple, list)):
        for nested in value:
            yield from _walk_keys(nested)


def _artifact_bytes(packet: Mapping[str, object]) -> dict[str, bytes]:
    artifacts = packet["artifacts"]
    assert isinstance(artifacts, (tuple, list))
    result: dict[str, bytes] = {}
    for record in artifacts:
        assert isinstance(record, Mapping)
        name = record["logical_name"]
        encoded = record["content_base64"]
        assert isinstance(name, str)
        assert isinstance(encoded, str)
        result[name] = base64.b64decode(encoded)
    return result


class Phase3ContextIsolationTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.layout = StoreLayout.at(temporary.name).ensure()
        self.store = ObjectStore(self.layout)

    def _artifact(
        self,
        artifact_id: str,
        logical_name: str,
        data: bytes,
        *,
        compartments: tuple[str, ...],
    ) -> tuple[ArtifactRegistration, ArtifactDependencyRef]:
        digest = sha256_digest(data)
        registration = ArtifactRegistration(
            artifact_id=artifact_id,
            version=1,
            project_id=PROJECT_ID,
            logical_name=logical_name,
            media_type="text/plain",
            content_hash=digest,
            byte_size=len(data),
            access_compartments=compartments,
            created_at=CREATED_AT,
        )
        self.store.install_bytes("artifacts", digest, data)
        return registration, ArtifactDependencyRef(
            artifact_id=artifact_id,
            version=1,
            content_hash=digest,
        )

    @staticmethod
    def _route(
        route_id: str,
        *,
        purpose: str,
        compartments: tuple[str, ...],
    ):
        return authorize_route(
            route_id,
            purpose=purpose,
            compartments=compartments,
            privacy_clearance="project_private",
        )

    def _reader_material(self):
        manuscript_data = b"Frozen economic manuscript: benchmark, mechanism, boundary."
        probe_data = b"Retell the benchmark and apply the boundary to a nearby case."
        key_data = b"SEALED KEY: benchmark, exact scope, boundary, near transfer."
        response_data = b"The reader recovers the benchmark, scope, and boundary."
        manuscript_reg, manuscript_ref = self._artifact(
            "artifact.manuscript.frozen",
            "frozen manuscript",
            manuscript_data,
            compartments=COLD_READER,
        )
        probe_reg, probe_ref = self._artifact(
            "artifact.reader.probe",
            "cold reader probe",
            probe_data,
            compartments=COLD_READER,
        )
        key_reg, key_ref = self._artifact(
            "artifact.reader.answer.key",
            "sealed answer key",
            key_data,
            compartments=COLD_READER,
        )
        response_reg, response_ref = self._artifact(
            "artifact.reader.response",
            "cold reader response",
            response_data,
            compartments=COLD_READER,
        )

        source = SemanticFacetRef(
            entity_id="entity.claim.graph",
            version=1,
            facet="formal",
            field_path="/claims/0/formal_statement",
            semantic_hash="4" * 64,
        )
        unit = _typed_entity(
            "entity.manuscript.unit",
            ManuscriptUnit(
                unit_id="unit.mechanism.explanation",
                paper_ir_ref=EntityVersionRef(entity_id="entity.paper.ir", version=1),
                reader_path_ref=EntityVersionRef(
                    entity_id="entity.reader.path", version=1
                ),
                result_contract_set_ref=EntityVersionRef(
                    entity_id="entity.result.contracts", version=1
                ),
                section_contract_id="section.mechanism",
                manuscript_artifact_ref=manuscript_ref,
                source_state_revision=HEAD,
                canonical_writer=WRITER,
                writer_role_packet_hash="7" * 64,
                writer_output_hash=manuscript_ref.content_hash,
                integration_generation=1,
                spans=(
                    ConsequentialSpan(
                        assertion_id="assertion.headline",
                        role="formal_statement",
                        claim_projection_id="projection.headline",
                        claim_graph_ref=EntityVersionRef(
                            entity_id="entity.claim.graph", version=1
                        ),
                        claim_id="claim.headline",
                        source_fields=(source,),
                        scope="The maintained domain.",
                        assumption_ids=("assumption.attention",),
                        location=ManuscriptLocation(start_offset=0, end_offset=20),
                        text_hash=sha256_digest(manuscript_data[:20]),
                        wording_strength="exact",
                        presentation="theorem_statement",
                    ),
                ),
                terminology=(
                    TerminologyRealization(
                        object_id="object.attention",
                        realized_name="attention threshold",
                        formal_symbol="kappa",
                        first_use_assertion_id="assertion.headline",
                    ),
                ),
                composed_at=CREATED_AT,
            ),
            compartments=COLD_READER,
        )
        probe_set = _typed_entity(
            "entity.reader.probe.set",
            ReaderProbeSet(
                assignment_ref=EntityVersionRef(
                    entity_id="entity.assignment.cold", version=1
                ),
                manuscript_unit_ref=EntityVersionRef(
                    entity_id=unit.entity_id, version=unit.version
                ),
                frozen_manuscript_artifact_ref=manuscript_ref,
                probe_designer=PROBE_DESIGNER,
                respondent=RESPONDENT,
                adjudicator=ADJUDICATOR,
                canonical_writer=WRITER,
                transfer_objective="Recover scope and transfer the mechanism once.",
                probes=tuple(
                    ReaderProbeDescriptor(
                        probe_id=f"probe.{kind}",
                        kind=kind,
                        prompt_hash=sha256_digest(
                            f"prompt:{kind}".encode("utf-8")
                        ),
                        target_contract_ids=("contract.reader.transfer",),
                    )
                    for kind in READER_PROBE_KIND_ORDER
                ),
                probe_artifact_ref=probe_ref,
                answer_key_artifact_ref=key_ref,
                route_run_id="run.prepare.reader.probe",
                context_manifest_hash="5" * 64,
                sealed_at=CREATED_AT,
            ),
            compartments=COLD_READER,
        )
        response = _typed_entity(
            "entity.reader.response",
            ReaderResponse(
                probe_set_ref=EntityVersionRef(
                    entity_id=probe_set.entity_id, version=probe_set.version
                ),
                manuscript_unit_ref=EntityVersionRef(
                    entity_id=unit.entity_id, version=unit.version
                ),
                respondent=RESPONDENT,
                answered_probe_ids=tuple(
                    f"probe.{kind}" for kind in READER_PROBE_KIND_ORDER
                ),
                response_artifact_ref=response_ref,
                route_run_id="run.answer.reader.probe",
                context_manifest_hash="6" * 64,
                submitted_at=CREATED_AT,
            ),
            compartments=COLD_READER,
        )
        registrations = (manuscript_reg, probe_reg, key_reg, response_reg)
        values = {
            "frozen manuscript": manuscript_data,
            "cold reader probe": probe_data,
            "sealed answer key": key_data,
            "cold reader response": response_data,
        }
        return unit, probe_set, response, registrations, values

    def test_blind_rederivation_packet_excludes_vap_verification_and_proof(self) -> None:
        proof_data = b"FORBIDDEN ORIGINATING PROOF TRANSCRIPT"
        proof_reg, proof_ref = self._artifact(
            "artifact.originating.proof",
            "originating proof transcript",
            proof_data,
            compartments=BLIND_REDERIVATION,
        )
        obligation = _typed_entity(
            "entity.proof.obligation",
            ProofObligation(
                claim_graph_ref=EntityVersionRef(
                    entity_id="entity.claim.graph", version=1
                ),
                claim_id="claim.headline",
                obligation_id="obligation.headline",
                statement="For every admissible type, the threshold comparison holds.",
                burden="comparative_static",
                quantifier_scope="Every type in the maintained domain.",
                assumption_ids=("assumption.attention",),
                admissible_methods=("analytic_proof",),
            ),
            compartments=BLIND_REDERIVATION,
        )
        vap_secret = "FORBIDDEN G5 PACKAGE PROSE"
        verification_secret = "FORBIDDEN VERIFIER CONCLUSION"
        vap = _opaque_excluded_entity(
            "entity.validated.argument.package",
            "ValidatedArgumentPackage",
            vap_secret,
            compartments=BLIND_REDERIVATION,
        )
        verification = _opaque_excluded_entity(
            "entity.verification.record",
            "VerificationRecord",
            verification_secret,
            compartments=BLIND_REDERIVATION,
            artifact_refs=(proof_ref,),
        )
        snapshot = _snapshot((obligation, vap, verification), (proof_reg,))
        route = self._route(
            "verify.independent_rederivation",
            purpose="research_verification",
            compartments=BLIND_REDERIVATION,
        )

        compiled = compile_context(
            snapshot,
            route=route,
            actor=REDERIVER,
            purpose="research_verification",
            compartments=BLIND_REDERIVATION,
            privacy_clearance="project_private",
            focus_entity_ids=(vap.entity_id, verification.entity_id, obligation.entity_id),
            budget_units=100_000,
            layout=self.layout,
        )

        packet = compiled.payload["phase3_role_packet"]
        packet_bytes = canonical_json_bytes(packet)
        self.assertEqual(packet["packet_kind"], "independent_rederivation")
        self.assertEqual(
            {item["kind"] for item in packet["semantic_inputs"]},
            {"ProofObligation"},
        )
        self.assertEqual(packet["artifacts"], ())
        self.assertEqual(
            tuple(ref.entity_id for ref in compiled.selected_entity_refs),
            (obligation.entity_id,),
        )
        for forbidden in (
            proof_data,
            vap_secret.encode(),
            verification_secret.encode(),
            proof_ref.content_hash.encode(),
        ):
            self.assertNotIn(forbidden, packet_bytes)
        self.assertEqual(compiled.payload["phase3_artifacts"], ())

    def test_canonical_writer_packet_is_semantic_and_governance_free(self) -> None:
        proof_data = b"RAW PROOF THAT MUST NOT PERSUADE THE WRITER"
        proof_reg, proof_ref = self._artifact(
            "artifact.writer.forbidden.proof",
            "raw proof transcript",
            proof_data,
            compartments=PROJECT_RESEARCH,
        )
        assumptions = _typed_entity(
            "entity.assumption.map",
            AssumptionMap(
                formal_model_ref=EntityVersionRef(
                    entity_id="entity.formal.model", version=1
                ),
                formalization_map_ref=EntityVersionRef(
                    entity_id="entity.formalization.map", version=1
                ),
                assumptions=(
                    AssumptionRecord(
                        assumption_id="assumption.attention",
                        exact_content="Processing is indivisible and costly.",
                        quantifiers=("For each signal precision.",),
                        economic_interpretation="Attention is purchased only when useful.",
                        foundation="primitive",
                        roles=("mechanism",),
                        satisfying_case_ids=("case.attention",),
                        scope_cost="The reversal disappears without indivisibility.",
                        necessity_status="unknown",
                    ),
                ),
            ),
            compartments=PROJECT_RESEARCH,
        )
        excluded = (
            _opaque_excluded_entity(
                "entity.assurance.bundle",
                "AssuranceBundle",
                "FORBIDDEN RAW ASSURANCE FINDINGS",
                compartments=PROJECT_RESEARCH,
            ),
            _opaque_excluded_entity(
                "entity.critic.assignment",
                "CriticAssignment",
                "FORBIDDEN CRITIC INSTRUCTIONS",
                compartments=PROJECT_RESEARCH,
            ),
            _opaque_excluded_entity(
                "entity.validated.argument.package.writer",
                "ValidatedArgumentPackage",
                "FORBIDDEN G5 GOVERNANCE PROSE",
                compartments=PROJECT_RESEARCH,
            ),
            _opaque_excluded_entity(
                "entity.verification.record.writer",
                "VerificationRecord",
                "FORBIDDEN VERIFICATION PERSUASION",
                compartments=PROJECT_RESEARCH,
                artifact_refs=(proof_ref,),
            ),
        )
        snapshot = _snapshot((assumptions, *excluded), (proof_reg,))
        route = self._route(
            "compose.manuscript_unit",
            purpose="research_authoring",
            compartments=PROJECT_RESEARCH,
        )
        focus = tuple(item.entity_id for item in (assumptions, *excluded))

        compiled = compile_context(
            snapshot,
            route=route,
            actor=WRITER,
            purpose="research_authoring",
            compartments=PROJECT_RESEARCH,
            privacy_clearance="project_private",
            focus_entity_ids=focus,
            budget_units=100_000,
            layout=self.layout,
        )

        packet = compiled.payload["phase3_role_packet"]
        packet_bytes = canonical_json_bytes(packet)
        self.assertEqual(packet["packet_kind"], "canonical_writer")
        self.assertEqual(
            {item["kind"] for item in packet["semantic_inputs"]},
            {"AssumptionMap"},
        )
        self.assertEqual(packet["artifacts"], ())
        self.assertEqual(compiled.payload["phase3_artifacts"], ())
        keys = set(_walk_keys(packet))
        forbidden_exact_keys = {
            "schema_version",
            "source_state_revision",
            "upstream_projection_hash",
            "context_manifest_hash",
            "compiled_context_hash",
            "route_run_id",
            "g5_decision_ref",
            "g4_decision_ref",
            "manuscript_version_promotion_ref",
            "route",
            "kernel",
            "effective_decisions",
            "status_source_decisions",
            "derived_status",
            "blockers",
            "budget",
            "focus_entity_ids",
        }
        self.assertFalse(keys.intersection(forbidden_exact_keys))
        self.assertFalse(
            any(
                key.lower().endswith(suffix)
                for key in keys
                for suffix in ("_ref", "_refs", "_id", "_ids", "_hash")
            )
        )
        for forbidden in (
            proof_data,
            proof_ref.content_hash.encode(),
            b"FORBIDDEN RAW ASSURANCE FINDINGS",
            b"FORBIDDEN CRITIC INSTRUCTIONS",
            b"FORBIDDEN G5 GOVERNANCE PROSE",
            b"FORBIDDEN VERIFICATION PERSUASION",
        ):
            self.assertNotIn(forbidden, packet_bytes)

    def test_cold_reader_gets_probe_and_manuscript_but_never_answer_key(self) -> None:
        unit, probe_set, response, registrations, values = self._reader_material()
        snapshot = _snapshot((unit, probe_set, response), registrations)
        route = self._route(
            "answer.reader_probe",
            purpose="cold_reader_evaluation",
            compartments=COLD_READER,
        )

        compiled = compile_context(
            snapshot,
            route=route,
            actor=RESPONDENT,
            purpose="cold_reader_evaluation",
            compartments=COLD_READER,
            privacy_clearance="project_private",
            focus_entity_ids=(probe_set.entity_id, unit.entity_id),
            budget_units=100_000,
            layout=self.layout,
        )

        packet = compiled.payload["phase3_role_packet"]
        visible = _artifact_bytes(packet)
        self.assertEqual(packet["packet_kind"], "cold_reader")
        self.assertEqual(
            visible,
            {
                "frozen manuscript": values["frozen manuscript"],
                "cold reader probe": values["cold reader probe"],
            },
        )
        self.assertNotIn("sealed answer key", visible)
        self.assertNotIn(values["sealed answer key"], visible.values())
        self.assertNotIn("answer_key_artifact_ref", set(_walk_keys(packet)))
        self.assertTrue(
            compiled.payload["phase3_selector"][
                "provider_must_receive_role_packet_only"
            ]
        )
        self.assertEqual(
            {
                item["registration"]["artifact_id"]
                for item in compiled.payload["phase3_artifacts"]
            },
            {"artifact.manuscript.frozen", "artifact.reader.probe"},
        )

    def test_adjudicator_gets_exact_sealed_key_and_response(self) -> None:
        unit, probe_set, response, registrations, values = self._reader_material()
        snapshot = _snapshot((unit, probe_set, response), registrations)
        route = self._route(
            "adjudicate.reader_probe",
            purpose="reader_evaluation_adjudication",
            compartments=COLD_READER,
        )

        compiled = compile_context(
            snapshot,
            route=route,
            actor=ADJUDICATOR,
            purpose="reader_evaluation_adjudication",
            compartments=COLD_READER,
            privacy_clearance="project_private",
            focus_entity_ids=(response.entity_id, probe_set.entity_id),
            budget_units=100_000,
            layout=self.layout,
        )

        packet = compiled.payload["phase3_role_packet"]
        visible = _artifact_bytes(packet)
        self.assertEqual(packet["packet_kind"], "reader_adjudicator")
        self.assertEqual(
            visible,
            {
                "cold reader probe": values["cold reader probe"],
                "sealed answer key": values["sealed answer key"],
                "cold reader response": values["cold reader response"],
            },
        )
        self.assertEqual(
            {item["kind"] for item in packet["semantic_inputs"]},
            {"ReaderProbeSet", "ReaderResponse"},
        )

    def test_native_v3_exact_selector_and_budget_are_deterministic(self) -> None:
        unit, probe_set, response, registrations, _ = self._reader_material()
        snapshot = _snapshot((unit, probe_set, response), registrations)
        route = self._route(
            "answer.reader_probe",
            purpose="cold_reader_evaluation",
            compartments=COLD_READER,
        )
        common = dict(
            route=route,
            actor=RESPONDENT,
            purpose="cold_reader_evaluation",
            compartments=COLD_READER,
            privacy_clearance="project_private",
            budget_units=100_000,
            layout=self.layout,
        )

        first = compile_context(
            snapshot,
            focus_entity_ids=(unit.entity_id, probe_set.entity_id),
            **common,
        )
        second = compile_context(
            snapshot,
            focus_entity_ids=(probe_set.entity_id, unit.entity_id),
            **common,
        )
        self.assertEqual(first.encoded, second.encoded)
        self.assertEqual(first.context_hash, second.context_hash)
        self.assertEqual(first.used_units, second.used_units)
        self.assertEqual(first.omissions, ())
        self.assertEqual(
            first.payload["phase3_selector"],
            {
                "mode": "exact_role_packet.v1",
                "provider_must_receive_role_packet_only": True,
            },
        )
        exact = compile_context(
            snapshot,
            route=route,
            actor=RESPONDENT,
            purpose="cold_reader_evaluation",
            compartments=COLD_READER,
            privacy_clearance="project_private",
            focus_entity_ids=(unit.entity_id, probe_set.entity_id),
            budget_units=first.used_units,
            layout=self.layout,
        )
        self.assertEqual(exact.used_units, first.used_units)
        with self.assertRaises(ContextBudgetError):
            compile_context(
                snapshot,
                route=route,
                actor=RESPONDENT,
                purpose="cold_reader_evaluation",
                compartments=COLD_READER,
                privacy_clearance="project_private",
                focus_entity_ids=(unit.entity_id, probe_set.entity_id),
                budget_units=first.used_units - 1,
                layout=self.layout,
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
