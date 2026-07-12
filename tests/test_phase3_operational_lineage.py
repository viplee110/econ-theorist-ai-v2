"""Focused immutable-lineage tests for Phase 3 blind re-derivation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src

from econ_theorist.authoring import (
    DerivationStep,
    ReDerivationRecord,
    RunProvenanceBinding,
    pack_authoring_payload,
)
from econ_theorist.authoring_validation import (
    AuthoringValidationError,
    validate_authoring_entity,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ContextManifest,
    CreateEntityOp,
    EntityVersion,
    EntityVersionRef,
    FacetPayloads,
    RecordRouteOutcomeOp,
    RouteOutcome,
    RouteRun,
    ScientificStatus,
    Snapshot,
    Transaction,
)
from econ_theorist.runtime.layout import StoreLayout
from econ_theorist.runtime.objects import ObjectStore
from econ_theorist.runtime.phase3_lineage import (
    Phase3LineageError,
    validate_phase3_operational_lineage,
)
from econ_theorist.theory import VerificationRecord, pack_theory_payload


PROJECT_ID = "project.phase3.lineage"
HEAD = "a" * 64
CREATED_AT = "2026-07-12T00:00:00Z"
PROOF_AUTHOR = Actor(kind="agent", actor_id="agent.proof.author")
INPUT_AUTHOR = Actor(kind="agent", actor_id="agent.formal.inputs")
VERIFIER = Actor(kind="agent", actor_id="agent.scientific.verifier")
LEGACY_VERIFICATION_ROUTE_ACTOR = Actor(
    kind="agent", actor_id="agent.legacy.verification.route"
)
REDERIVER = Actor(kind="agent", actor_id="agent.blind.rederiver")


def _ref(entity: EntityVersion) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity.entity_id, version=entity.version)


def _entity(
    entity_id: str,
    entity_type: str,
    *,
    facets: FacetPayloads | None = None,
    artifact_refs: tuple[ArtifactDependencyRef, ...] = (),
) -> EntityVersion:
    return EntityVersion(
        entity_id=entity_id,
        entity_type=entity_type,
        version=1,
        project_id=PROJECT_ID,
        title=f"Title for {entity_id}",
        summary=f"Summary for {entity_id}",
        status=ScientificStatus(lifecycle="proposed"),
        facets=facets or FacetPayloads(),
        artifact_refs=artifact_refs,
        created_at=CREATED_AT,
    )


class Phase3OperationalLineageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.layout = StoreLayout.at(Path(self.temporary.name))
        self.layout.ensure()
        self.store = ObjectStore(self.layout)

        self.proof_ref = ArtifactDependencyRef(
            artifact_id="artifact.originating.proof",
            version=1,
            content_hash="b" * 64,
        )
        self.derivation_ref = ArtifactDependencyRef(
            artifact_id="artifact.blind.derivation",
            version=1,
            content_hash="c" * 64,
        )
        self.package = _entity("entity.package", "ValidatedArgumentPackage")
        self.claim = _entity("entity.claim.graph", "ClaimGraph")
        self.obligation = _entity("entity.proof.obligation", "ProofObligation")
        self.formal_model = _entity("entity.formal.model", "FormalModel")
        self.assumptions = _entity("entity.assumption.map", "AssumptionMap")
        verification_payload = VerificationRecord(
            obligation_ref=_ref(self.obligation),
            claim_graph_ref=_ref(self.claim),
            formal_model_ref=_ref(self.formal_model),
            assumption_map_ref=_ref(self.assumptions),
            verifier=VERIFIER,
            method="analytic_proof",
            outcome="discharged",
            checked_refs=(_ref(self.obligation),),
            evidence_refs=(self.proof_ref,),
            limitations="The exact maintained scope remains binding.",
            checked_at=CREATED_AT,
        )
        self.verification = _entity(
            "entity.verification.record",
            "VerificationRecord",
            facets=pack_theory_payload(verification_payload),
            artifact_refs=(self.proof_ref,),
        )

        self.proof_binding = self._seal_run(
            "run.proof.author",
            actor=PROOF_AUTHOR,
            route_id="discover.claims_and_boundaries",
            selected_refs=(_ref(self.formal_model),),
        )
        self.input_binding = self._seal_run(
            "run.formal.inputs",
            actor=INPUT_AUTHOR,
            route_id="formalize.selected_mechanism",
            selected_refs=(),
        )
        # The Phase 2 gold chain distinguishes the route actor from the
        # VerificationRecord.verifier.  Producer identity and scientific actor
        # attribution are therefore checked separately.
        self.verification_binding = self._seal_run(
            "run.verification",
            actor=LEGACY_VERIFICATION_ROUTE_ACTOR,
            route_id="verify.claims_proofs_and_interpretation",
            selected_refs=(_ref(self.obligation),),
        )

        self.focus_refs = (
            _ref(self.package),
            _ref(self.claim),
            _ref(self.obligation),
            _ref(self.formal_model),
            _ref(self.assumptions),
        )
        self.selected_refs = self.focus_refs[1:]
        self.current_binding = self._seal_current(self.selected_refs)
        self.snapshot = self._snapshot()
        self.record = self._record()
        self.transaction = self._transaction(self.record)

    def _base_context(
        self,
        *,
        entities: tuple[EntityVersion, ...] = (),
    ) -> dict[str, object]:
        return {
            "source_head": HEAD,
            "project_id": PROJECT_ID,
            "entities": tuple(item.model_dump(mode="json") for item in entities),
        }

    def _seal_run(
        self,
        route_run_id: str,
        *,
        actor: Actor,
        route_id: str,
        selected_refs: tuple[EntityVersionRef, ...],
        focus_refs: tuple[EntityVersionRef, ...] | None = None,
        context: dict[str, object] | None = None,
        route_version: int = 2,
    ) -> RunProvenanceBinding:
        context_payload = context or self._base_context()
        context_bytes = canonical_json_bytes(context_payload)
        context_hash = sha256_digest(context_bytes)
        manifest = ContextManifest(
            context_manifest_id=f"context.{route_run_id}",
            project_id=PROJECT_ID,
            source_head=HEAD,
            route_id=route_id,
            route_version=route_version,
            route_registry_hash="1" * 64,
            decision_registry_version=2,
            validator_version="validator.phase3.test",
            selector_version="selector.phase3.test",
            kernel_version="kernel.phase3.test",
            kernel_hash="2" * 64,
            instruction_bundle_id=f"instruction.{route_id}",
            instruction_bundle_hash="3" * 64,
            isolation_policy="isolation.phase3.test",
            write_allowlist=("entity.create", "route.outcome"),
            purpose="research_verification",
            actor=actor,
            focus_entity_ids=tuple(
                item.entity_id
                for item in (selected_refs if focus_refs is None else focus_refs)
            ),
            selected_entity_refs=selected_refs,
            compartments=("project_research",),
            budget_units=100_000,
            used_units=1,
            context_hash=context_hash,
            created_at=CREATED_AT,
        )
        manifest_bytes = canonical_json_bytes(manifest)
        manifest_hash = sha256_digest(manifest_bytes)
        run = RouteRun(
            route_run_id=route_run_id,
            project_id=PROJECT_ID,
            base_revision=HEAD,
            route_id=route_id,
            route_version=route_version,
            actor=actor,
            purpose=manifest.purpose,
            compartments=manifest.compartments,
            privacy_clearance=manifest.privacy_clearance,
            focus_entity_ids=manifest.focus_entity_ids,
            context_manifest_id=manifest.context_manifest_id,
            context_hash=context_hash,
            status="running",
            created_at=CREATED_AT,
        )
        run_bytes = canonical_json_bytes(run)
        run_hash = sha256_digest(run_bytes)
        self.store.install_bytes("provenance", context_hash, context_bytes)
        self.store.install_bytes("provenance", manifest_hash, manifest_bytes)
        self.store.install_bytes("provenance", run_hash, run_bytes)
        return RunProvenanceBinding(
            route_run_id=route_run_id,
            route_run_hash=run_hash,
            context_manifest_hash=manifest_hash,
            compiled_context_hash=context_hash,
        )

    def _blind_context(
        self,
        selected_refs: tuple[EntityVersionRef, ...],
        *,
        packet_artifacts: tuple[object, ...] = (),
        phase3_artifacts: tuple[object, ...] = (),
    ) -> dict[str, object]:
        by_ref = {
            _ref(item): item
            for item in (
                self.package,
                self.claim,
                self.obligation,
                self.formal_model,
                self.assumptions,
                self.verification,
            )
        }
        selected_entities = tuple(by_ref[item] for item in selected_refs)
        return {
            **self._base_context(entities=selected_entities),
            "phase3_selector": {
                "mode": "exact_role_packet.v1",
                "provider_must_receive_role_packet_only": True,
            },
            "phase3_role_packet": {
                "packet_schema": "econ-theorist/role-packet/v1",
                "packet_kind": "independent_rederivation",
                "actor_kind": REDERIVER.kind,
                "constraints": ("Re-derive without proof evidence.",),
                "semantic_inputs": tuple(
                    {"kind": item.entity_type, "content": {}}
                    for item in selected_entities
                ),
                "artifacts": packet_artifacts,
            },
            "phase3_artifacts": phase3_artifacts,
        }

    def _seal_current(
        self,
        selected_refs: tuple[EntityVersionRef, ...],
        *,
        packet_artifacts: tuple[object, ...] = (),
        phase3_artifacts: tuple[object, ...] = (),
    ) -> RunProvenanceBinding:
        return self._seal_run(
            "run.blind.rederivation",
            actor=REDERIVER,
            route_id="verify.independent_rederivation",
            selected_refs=selected_refs,
            focus_refs=self.focus_refs,
            context=self._blind_context(
                selected_refs,
                packet_artifacts=packet_artifacts,
                phase3_artifacts=phase3_artifacts,
            ),
            route_version=3,
        )

    def _snapshot(self) -> Snapshot:
        prior_bindings = (
            self.proof_binding,
            self.input_binding,
            self.verification_binding,
        )
        entities = (
            self.package,
            self.claim,
            self.obligation,
            self.formal_model,
            self.assumptions,
            self.verification,
        )
        return Snapshot(
            project_id=PROJECT_ID,
            head=HEAD,
            chain=(HEAD,),
            provenance_hashes=tuple(
                digest
                for binding in prior_bindings
                for digest in (
                    binding.route_run_hash,
                    binding.context_manifest_hash,
                    binding.compiled_context_hash,
                )
            ),
            entity_versions=entities,
            route_outcomes=(
                RouteOutcome(
                    route_run_id=self.proof_binding.route_run_id,
                    route_id="discover.claims_and_boundaries",
                    outcome="completed_with_candidate",
                    rationale="Produced exact claims and obligations.",
                    candidate_refs=(_ref(self.claim), _ref(self.obligation)),
                ),
                RouteOutcome(
                    route_run_id=self.input_binding.route_run_id,
                    route_id="formalize.selected_mechanism",
                    outcome="completed_with_candidate",
                    rationale="Produced exact formal inputs.",
                    candidate_refs=(_ref(self.formal_model), _ref(self.assumptions)),
                ),
                RouteOutcome(
                    route_run_id=self.verification_binding.route_run_id,
                    route_id="verify.claims_proofs_and_interpretation",
                    outcome="completed_with_candidate",
                    rationale="Produced exact verification evidence.",
                    candidate_refs=(_ref(self.verification), self.proof_ref),
                ),
            ),
            current_entities={item.entity_id: item.version for item in entities},
        )

    def _record(self, **updates: object) -> ReDerivationRecord:
        values: dict[str, object] = {
            "package_ref": _ref(self.package),
            "claim_graph_ref": _ref(self.claim),
            "claim_id": "claim.headline",
            "obligation_ref": _ref(self.obligation),
            "formal_model_ref": _ref(self.formal_model),
            "assumption_map_ref": _ref(self.assumptions),
            "verification_record_ref": _ref(self.verification),
            "originating_verifier": VERIFIER,
            "originating_verifier_run": self.verification_binding,
            "proof_author": PROOF_AUTHOR,
            "proof_author_output_ref": _ref(self.claim),
            "proof_author_run": self.proof_binding,
            "rederiver": REDERIVER,
            "route_run_id": self.current_binding.route_run_id,
            "route_run_hash": self.current_binding.route_run_hash,
            "parent_runs": (self.input_binding, self.proof_binding),
            "derivation_artifact_ref": self.derivation_ref,
            "derivation_steps": (
                DerivationStep(
                    step_id="step.independent.derivation",
                    statement="Reconstruct the headline comparison from the maintained primitives.",
                    justification="The exact model, assumptions, claim, and obligation jointly imply the comparison.",
                    source_refs=(
                        _ref(self.claim),
                        _ref(self.obligation),
                        _ref(self.formal_model),
                        _ref(self.assumptions),
                    ),
                ),
            ),
            "derived_conclusion": "The exact headline comparison holds on the maintained domain.",
            "comparison_to_claim": "equivalent",
            "context_manifest_hash": self.current_binding.context_manifest_hash,
            "compiled_context_hash": self.current_binding.compiled_context_hash,
            "excluded_proof_artifact_refs": (self.proof_ref,),
            "outcome": "agrees",
            "limitations": "This is an independent derivation within the exact scope.",
            "performed_at": CREATED_AT,
        }
        values.update(updates)
        return ReDerivationRecord(**values)

    def _transaction(self, record: ReDerivationRecord) -> Transaction:
        output = _entity(
            "entity.rederivation.record",
            "ReDerivationRecord",
            facets=pack_authoring_payload(record),
            artifact_refs=(self.derivation_ref,),
        )
        output_ref = _ref(output)
        return Transaction(
            transaction_id="transaction.blind.rederivation",
            origin="route_run",
            project_id=PROJECT_ID,
            base_revision=HEAD,
            route_run_id=record.route_run_id,
            route_id="verify.independent_rederivation",
            route_run_hash=record.route_run_hash,
            context_manifest_hash=record.context_manifest_hash,
            compiled_context_hash=record.compiled_context_hash,
            actor=REDERIVER,
            intent="Commit the exact blind re-derivation.",
            operations=(
                CreateEntityOp(entity=output),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=record.route_run_id,
                        route_id="verify.independent_rederivation",
                        outcome="completed_with_candidate",
                        rationale="Produced one exact blind re-derivation record.",
                        candidate_refs=(output_ref,),
                    )
                ),
            ),
            evidence_refs=self.focus_refs,
            created_at=CREATED_AT,
            parent_transaction_hash=HEAD,
        )

    def _with_current_binding(
        self, binding: RunProvenanceBinding, **updates: object
    ) -> ReDerivationRecord:
        return self._record(
            route_run_id=binding.route_run_id,
            route_run_hash=binding.route_run_hash,
            context_manifest_hash=binding.context_manifest_hash,
            compiled_context_hash=binding.compiled_context_hash,
            **updates,
        )

    def test_excluded_proof_refs_are_negative_evidence_not_envelope_dependencies(self) -> None:
        record = self._record()
        output = _entity(
            "entity.rederivation.negative-evidence",
            "ReDerivationRecord",
            facets=pack_authoring_payload(record),
            artifact_refs=(self.derivation_ref,),
        )
        self.assertEqual(validate_authoring_entity(output), record)

        leaked = output.model_copy(
            update={"artifact_refs": (self.derivation_ref, self.proof_ref)}
        )
        with self.assertRaisesRegex(
            AuthoringValidationError, "every and only exact artifact dependency"
        ):
            validate_authoring_entity(leaked)

    def test_exact_immutable_lineage_passes_with_legacy_verifier_route_actor(self) -> None:
        validate_phase3_operational_lineage(
            self.layout, self.snapshot, self.transaction
        )

    def test_run_focus_and_transaction_entity_evidence_must_match_exactly(self) -> None:
        validate_phase3_operational_lineage(
            self.layout, self.snapshot, self.transaction
        )

        attacks = {
            "missing": self.focus_refs[:-1],
            "extra": (*self.focus_refs, _ref(self.verification)),
        }
        for label, evidence_refs in attacks.items():
            with self.subTest(attack=label), self.assertRaisesRegex(
                Phase3LineageError, "focus.*evidence|evidence.*focus"
            ):
                validate_phase3_operational_lineage(
                    self.layout,
                    self.snapshot,
                    self.transaction.model_copy(
                        update={"evidence_refs": evidence_refs}
                    ),
                )

    def test_current_run_binding_fields_must_match_immutable_bytes(self) -> None:
        substitutions = {
            "route_run_id": "run.false.rederivation",
            "route_run_hash": "d" * 64,
            "context_manifest_hash": "e" * 64,
            "compiled_context_hash": "f" * 64,
        }
        for field, false_value in substitutions.items():
            with self.subTest(field=field):
                record = self._record(**{field: false_value})
                with self.assertRaises(Phase3LineageError):
                    validate_phase3_operational_lineage(
                        self.layout, self.snapshot, self._transaction(record)
                    )

    def test_proof_author_binding_must_be_the_exact_entity_producer(self) -> None:
        record = self._record(proof_author_run=self.input_binding)
        with self.assertRaisesRegex(Phase3LineageError, "proof-author run binding"):
            validate_phase3_operational_lineage(
                self.layout, self.snapshot, self._transaction(record)
            )

    def test_parent_runs_are_exactly_selected_entity_producers(self) -> None:
        record = self._record(parent_runs=(self.proof_binding,))
        with self.assertRaisesRegex(Phase3LineageError, "exact selected-input producer set"):
            validate_phase3_operational_lineage(
                self.layout, self.snapshot, self._transaction(record)
            )

    def test_parent_binding_must_be_reachable_from_base_snapshot(self) -> None:
        unreachable = self.snapshot.model_copy(
            update={
                "provenance_hashes": tuple(
                    value
                    for value in self.snapshot.provenance_hashes
                    if value
                    not in {
                        self.input_binding.route_run_hash,
                        self.input_binding.context_manifest_hash,
                        self.input_binding.compiled_context_hash,
                    }
                )
            }
        )
        with self.assertRaisesRegex(Phase3LineageError, "not reachable"):
            validate_phase3_operational_lineage(
                self.layout, unreachable, self.transaction
            )

    def test_blind_manifest_cannot_select_verification_record(self) -> None:
        selected = (*self.selected_refs, _ref(self.verification))
        binding = self._seal_current(selected)
        record = self._with_current_binding(binding)
        with self.assertRaisesRegex(Phase3LineageError, "formal-input allowlist"):
            validate_phase3_operational_lineage(
                self.layout, self.snapshot, self._transaction(record)
            )

    def test_blind_role_packet_cannot_expose_proof_artifact(self) -> None:
        proof_mapping = self.proof_ref.model_dump(mode="json")
        binding = self._seal_current(
            self.selected_refs,
            packet_artifacts=(proof_mapping,),
            phase3_artifacts=(proof_mapping,),
        )
        record = self._with_current_binding(binding)
        with self.assertRaisesRegex(Phase3LineageError, "proof evidence"):
            validate_phase3_operational_lineage(
                self.layout, self.snapshot, self._transaction(record)
            )

    def test_originating_verifier_must_match_exact_verification_record(self) -> None:
        record = self._record(
            originating_verifier=Actor(kind="agent", actor_id="agent.false.verifier")
        )
        with self.assertRaisesRegex(Phase3LineageError, "originating verifier"):
            validate_phase3_operational_lineage(
                self.layout, self.snapshot, self._transaction(record)
            )

    def test_originating_verifier_binding_must_be_record_producer(self) -> None:
        unrelated = self._seal_run(
            "run.unrelated",
            actor=INPUT_AUTHOR,
            route_id="lab.micro_examples_and_ablations",
            selected_refs=(),
        )
        snapshot = self.snapshot.model_copy(
            update={
                "provenance_hashes": (
                    *self.snapshot.provenance_hashes,
                    unrelated.route_run_hash,
                    unrelated.context_manifest_hash,
                    unrelated.compiled_context_hash,
                )
            }
        )
        record = self._record(originating_verifier_run=unrelated)
        with self.assertRaisesRegex(Phase3LineageError, "originating verifier run binding"):
            validate_phase3_operational_lineage(
                self.layout, snapshot, self._transaction(record)
            )


if __name__ == "__main__":
    unittest.main()
