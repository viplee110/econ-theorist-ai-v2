"""Real-store Phase 3 continuation of the Phase 2 attention gold case.

The fixture deliberately subclasses the Phase 2 runtime chain.  Consequently
none of the authoring objects below can exist unless the complete G1--G5
scientific chain has first crossed the ordinary begin/stage/preflight/commit
boundary.  The continuation then exercises the same boundary for every native
Phase 3 route, including one deliberately blocked manuscript generation and a
fresh reviewed revision.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from fractions import Fraction
from pathlib import Path

from tests.helpers import REPOSITORY_ROOT  # noqa: F401  # installs src
from tests.test_phase2_gold_runtime_chain import (
    AGENT,
    HUMAN,
    Phase2GoldRuntimeChainTests,
    eref,
)

from econ_theorist import authoring as a
from econ_theorist import theory as t
from econ_theorist.assurance import (
    ExactAssignment,
    ExactPolynomial,
    ExactPolynomialRelation,
    run_exact_polynomial_relation_scan,
)
from econ_theorist.authoring_artifacts import (
    ProofAuditReportArtifact,
    ReaderAnswer,
    ReaderAnswerCriterion,
    ReaderAnswerKeyArtifact,
    ReaderProbeArtifact,
    ReaderProbePrompt,
    ReaderResponseArtifact,
    ReDerivationTranscript,
)
from econ_theorist.authoring_validation import (
    critic_assignment_contract_hash,
    paper_ir_upstream_projection_hash,
    resolved_profile_projection_hash,
    harness_protocol_code_bytes,
    harness_protocol_code_hash,
    validate_authoring_ready,
)
from econ_theorist.codec import canonical_json_bytes, sha256_digest, transaction_bytes
from econ_theorist.decisions import commit_decision
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    ArtifactRegistration,
    ArtifactVersionRef,
    ChangedFacets,
    CreateEntityOp,
    CreateRelationOp,
    Decision,
    DecisionVersionRef,
    EntityVersion,
    EntityVersionRef,
    FacetPathRef,
    RecordRouteOutcomeOp,
    RegisterArtifactOp,
    RelationVersion,
    RelationVersionRef,
    RouteOutcome,
    RouteRun,
    ScientificStatus,
    SemanticFacetRef,
    Snapshot,
    SupersedeEntityOp,
    Transaction,
)
from econ_theorist.policy import ROUTE_REGISTRY_V3_HASH
from econ_theorist.runs import (
    begin_run,
    read_compiled_context,
    read_context,
    read_run,
    transaction_bindings,
)
from econ_theorist.runtime.commit import StagedArtifact, commit_prepared, preflight_candidate
from econ_theorist.runtime.freshness import (
    authority_semantic_hash,
    changed_semantic_facets,
    facet_semantic_hash as runtime_facet_semantic_hash,
)
from econ_theorist.runtime.objects import ObjectStore
from econ_theorist.runtime.replay import replay, replay_at
from econ_theorist.staging import (
    read_staged_transaction,
    stage_candidate,
    staged_artifact_path,
)
from econ_theorist.theory_validation import (
    _typed_reference_closure_is_current_and_fresh,
)


WRITER = Actor(kind="agent", actor_id="gold.phase3.writer")
FORMAL_CRITIC = Actor(kind="agent", actor_id="gold.phase3.formal_critic")
ECONOMIC_CRITIC = Actor(kind="agent", actor_id="gold.phase3.economic_critic")
COLD_READER = Actor(kind="agent", actor_id="gold.phase3.cold_reader")
PROBE_DESIGNER = Actor(kind="agent", actor_id="gold.phase3.probe_designer")
PROBE_ADJUDICATOR = Actor(kind="agent", actor_id="gold.phase3.probe_adjudicator")
ASSURANCE_AUDITOR = Actor(kind="agent", actor_id="gold.phase3.assurance_auditor")
CLOSURE_TOOL = Actor(kind="deterministic_tool", actor_id="gold.phase3.closure")


def _timestamp(minute: int) -> str:
    return f"2026-07-11T16:{minute:02d}:00Z"


class Phase3GoldRuntimeChainTests(Phase2GoldRuntimeChainTests):
    """Continue the inherited real Phase 2 test at its fresh-G5 hook."""

    def _authoring_entity(
        self,
        entity_id: str,
        payload: a.AuthoringPayload,
        *,
        title: str,
        summary: str,
        created_at: str,
        artifact_refs: tuple[ArtifactDependencyRef, ...] = (),
        version: int = 1,
        supersedes: EntityVersionRef | None = None,
        privacy: str = "project_private",
        access_compartments: tuple[str, ...] = ("project_research",),
    ) -> EntityVersion:
        return EntityVersion(
            entity_id=entity_id,
            entity_type=type(payload).__name__,
            version=version,
            project_id=self.snapshot.project_id,
            title=title,
            summary=summary,
            status=ScientificStatus(lifecycle="proposed"),
            facets=a.pack_authoring_payload(payload),
            artifact_refs=artifact_refs,
            privacy=privacy,  # type: ignore[arg-type]
            access_compartments=access_compartments,
            created_at=created_at,
            supersedes=supersedes,
        )

    def _registered_artifact(
        self,
        artifact_id: str,
        data: bytes,
        *,
        logical_name: str,
        media_type: str,
        created_at: str,
        privacy: str = "project_private",
        access_compartments: tuple[str, ...] = ("project_research",),
        version: int = 1,
        supersedes: ArtifactVersionRef | None = None,
    ) -> tuple[ArtifactRegistration, ArtifactDependencyRef, bytes]:
        digest = sha256_digest(data)
        registration = ArtifactRegistration(
            artifact_id=artifact_id,
            version=version,
            project_id=self.snapshot.project_id,
            logical_name=logical_name,
            media_type=media_type,
            content_hash=digest,
            byte_size=len(data),
            privacy=privacy,  # type: ignore[arg-type]
            access_compartments=access_compartments,
            created_at=created_at,
            supersedes=supersedes,
        )
        return (
            registration,
            ArtifactDependencyRef(
                artifact_id=artifact_id, version=version, content_hash=digest
            ),
            data,
        )

    def _begin_v3(
        self,
        *,
        route_id: str,
        actor: Actor,
        purpose: str,
        focus_refs: Iterable[EntityVersionRef],
        created_at: str,
        compartments: tuple[str, ...] = ("project_research",),
        privacy_clearance: str = "project_private",
    ) -> tuple[Snapshot, RouteRun]:
        self.route_counter += 1
        before = replay(self.layout)
        run = begin_run(
            self.layout,
            before,
            route_id=route_id,
            actor=actor,
            purpose=purpose,
            compartments=compartments,
            privacy_clearance=privacy_clearance,
            focus_entity_ids=tuple(dict.fromkeys(ref.entity_id for ref in focus_refs)),
            budget_units=64_000,
            route_run_id=f"run.gold.{self.route_counter}",
            context_manifest_id=f"context.gold.{self.route_counter}",
            created_at=created_at,
            route_registry_hash=ROUTE_REGISTRY_V3_HASH,
        )
        self.assertEqual(run.route_version, 3)
        return before, run

    def _commit_started_v3(
        self,
        before: Snapshot,
        run: RouteRun,
        *,
        outputs: tuple[EntityVersion, ...],
        relations: tuple[RelationVersion, ...] = (),
        artifacts: tuple[tuple[ArtifactRegistration, bytes], ...] = (),
        evidence_refs: tuple[object, ...],
        authority_basis: tuple[str, ...] = (),
        created_at: str,
        privacy: str = "project_private",
        access_compartments: tuple[str, ...] = ("project_research",),
    ) -> Snapshot:
        candidate_refs = (
            *(eref(item) for item in outputs),
            *(
                RelationVersionRef(relation_id=item.relation_id, version=item.version)
                for item in relations
            ),
            *(
                ArtifactDependencyRef(
                    artifact_id=item.artifact_id,
                    version=item.version,
                    content_hash=item.content_hash,
                )
                for item, _ in artifacts
            ),
        )
        entity_operations: list[CreateEntityOp | SupersedeEntityOp] = []
        changed_facets: list[ChangedFacets] = []
        for item in outputs:
            if item.version == 1:
                entity_operations.append(CreateEntityOp(entity=item))
                continue
            assert item.supersedes is not None
            entity_operations.append(
                SupersedeEntityOp(previous=item.supersedes, entity=item)
            )
            previous = next(
                entity
                for entity in before.entity_versions
                if eref(entity) == item.supersedes
            )
            changed_facets.append(
                ChangedFacets(
                    entity_id=item.entity_id,
                    previous_version=previous.version,
                    new_version=item.version,
                    facets=changed_semantic_facets(previous, item),
                )
            )
        transaction = Transaction(
            **transaction_bindings(self.layout, run.route_run_id),
            transaction_id=f"transaction.gold.{self.route_counter}",
            origin="route_run",
            project_id=before.project_id,
            base_revision=run.base_revision,
            route_run_id=run.route_run_id,
            route_id=run.route_id,
            actor=run.actor,
            intent=f"Advance the Phase 3 gold chain through {run.route_id}.",
            changed_facets=tuple(changed_facets),
            operations=(
                *(RegisterArtifactOp(artifact=item) for item, _ in artifacts),
                *entity_operations,
                *(CreateRelationOp(relation=item) for item in relations),
                RecordRouteOutcomeOp(
                    outcome=RouteOutcome(
                        route_run_id=run.route_run_id,
                        route_id=run.route_id,
                        outcome="completed_with_candidate",
                        rationale="Every exact typed Phase 3 candidate was produced.",
                        candidate_refs=candidate_refs,
                        privacy=privacy,  # type: ignore[arg-type]
                        access_compartments=access_compartments,
                    )
                ),
            ),
            evidence_refs=evidence_refs,  # type: ignore[arg-type]
            authority_basis=authority_basis,
            privacy=privacy,  # type: ignore[arg-type]
            access_compartments=access_compartments,
            created_at=created_at,
            parent_transaction_hash=run.base_revision,
        )
        candidate_path = self.root / f"candidate-{self.route_counter}.json"
        candidate_path.write_bytes(transaction_bytes(transaction))
        paths: dict[str, Path] = {}
        for index, (registration, data) in enumerate(artifacts):
            path = self.root / f"artifact-{self.route_counter}-{index}.bin"
            path.write_bytes(data)
            paths[registration.artifact_id] = path
        digest = stage_candidate(
            self.layout, run.route_run_id, candidate_path, artifacts=paths
        )
        staged = read_staged_transaction(self.layout, run.route_run_id, digest)
        self.assertEqual(staged, transaction)
        prepared = preflight_candidate(
            self.layout,
            staged,
            tuple(
                StagedArtifact(
                    artifact_id=registration.artifact_id,
                    version=registration.version,
                    path=staged_artifact_path(
                        self.layout, run.route_run_id, registration.content_hash
                    ),
                )
                for registration, _ in artifacts
            ),
        )
        committed = commit_prepared(self.layout, prepared)
        self.assertEqual(committed.status, "committed")
        after = replay(self.layout)
        self.assertEqual(after.head, committed.head_after)
        for output in outputs:
            replayed = next(
                item
                for item in after.entity_versions
                if eref(item) == eref(output)
            )
            self.assertEqual(canonical_json_bytes(replayed), canonical_json_bytes(output))
        return after

    def _entity_at(self, snapshot: Snapshot, reference: EntityVersionRef) -> EntityVersion:
        return next(item for item in snapshot.entity_versions if eref(item) == reference)

    def _facet_ref(
        self,
        snapshot: Snapshot,
        reference: EntityVersionRef,
        *,
        field_path: str | None = None,
        facet: str | None = None,
    ) -> SemanticFacetRef:
        entity = self._entity_at(snapshot, reference)
        owner = facet
        if owner is None:
            owner = a.AUTHORING_PAYLOAD_OWNER_FACETS.get(entity.entity_type)
        if owner is None:
            owner = t.THEORY_PAYLOAD_OWNER_FACETS[entity.entity_type]
        semantic_hash = (
            authority_semantic_hash(
                entity, snapshot.decisions, snapshot.effective_decisions
            )
            if owner == "authority" and field_path is None
            else runtime_facet_semantic_hash(entity, owner, field_path)  # type: ignore[arg-type]
        )
        return SemanticFacetRef(
            entity_id=reference.entity_id,
            version=reference.version,
            facet=owner,  # type: ignore[arg-type]
            field_path=field_path,
            semantic_hash=semantic_hash,
        )

    def _relation(
        self,
        snapshot: Snapshot,
        *,
        relation_id: str,
        relation_type: str,
        source: EntityVersionRef,
        target: EntityVersionRef,
        created_at: str,
        source_field: SemanticFacetRef | None = None,
        target_path: str | None = None,
        target_facet: str | None = None,
        output_entities: Sequence[EntityVersion] = (),
        privacy: str = "project_private",
        access_compartments: tuple[str, ...] = ("project_research",),
    ) -> RelationVersion:
        source_entity = next(
            (
                item
                for item in (*snapshot.entity_versions, *output_entities)
                if eref(item) == source
            )
        )
        target_entity = next(
            (
                item
                for item in (*snapshot.entity_versions, *output_entities)
                if eref(item) == target
            )
        )
        source_owner = (
            a.AUTHORING_PAYLOAD_OWNER_FACETS.get(source_entity.entity_type)
            or t.THEORY_PAYLOAD_OWNER_FACETS[source_entity.entity_type]
        )
        target_owner = target_facet or (
            a.AUTHORING_PAYLOAD_OWNER_FACETS.get(target_entity.entity_type)
            or t.THEORY_PAYLOAD_OWNER_FACETS[target_entity.entity_type]
        )
        source_hash = (
            authority_semantic_hash(
                source_entity, snapshot.decisions, snapshot.effective_decisions
            )
            if source_owner == "authority"
            else runtime_facet_semantic_hash(source_entity, source_owner, None)  # type: ignore[arg-type]
        )
        upstream = source_field or SemanticFacetRef(
            entity_id=source.entity_id,
            version=source.version,
            facet=source_owner,
            field_path=None,
            semantic_hash=source_hash,
        )
        return RelationVersion(
            relation_id=relation_id,
            relation_type=relation_type,
            version=1,
            project_id=self.snapshot.project_id,
            source=source,
            target=target,
            dependency_mode="hard",
            upstream=upstream,
            downstream=FacetPathRef(
                entity_id=target.entity_id,
                version=target.version,
                facet=target_owner,  # type: ignore[arg-type]
                field_path=target_path,
            ),
            privacy=privacy,  # type: ignore[arg-type]
            access_compartments=access_compartments,
            created_at=created_at,
        )

    def _run_binding(self, route_run_id: str) -> a.RunProvenanceBinding:
        run = read_run(self.layout, route_run_id)
        context = read_context(self.layout, route_run_id)
        return a.RunProvenanceBinding(
            route_run_id=route_run_id,
            route_run_hash=sha256_digest(canonical_json_bytes(run)),
            context_manifest_hash=sha256_digest(canonical_json_bytes(context)),
            compiled_context_hash=run.context_hash,
        )

    def _producer_binding(
        self, snapshot: Snapshot, reference: EntityVersionRef
    ) -> a.RunProvenanceBinding:
        outcome = next(
            item
            for item in reversed(snapshot.route_outcomes)
            if reference in item.candidate_refs
        )
        return self._run_binding(outcome.route_run_id)

    def _context_parent_bindings(
        self,
        snapshot: Snapshot,
        route_run_id: str,
        *,
        excluded_run_ids: Iterable[str] = (),
    ) -> tuple[a.RunProvenanceBinding, ...]:
        excluded = set(excluded_run_ids)
        context = read_context(self.layout, route_run_id)
        by_id: dict[str, a.RunProvenanceBinding] = {}
        for reference in context.selected_entity_refs:
            try:
                binding = self._producer_binding(snapshot, reference)
            except StopIteration:
                continue
            if binding.route_run_id not in excluded:
                by_id[binding.route_run_id] = binding
        return tuple(by_id[key] for key in sorted(by_id))

    def _promote_production_package(
        self, handoff: Mapping[str, object]
    ) -> tuple[EntityVersion, EntityVersion, Decision]:
        old_package = handoff["argument_package"]
        old_dossier = handoff["g5_dossier"]
        old_g5 = handoff["g5"]
        assert isinstance(old_package, EntityVersion)
        assert isinstance(old_dossier, EntityVersion)
        assert isinstance(old_g5, Decision)
        package_payload = t.parse_theory_entity(old_package)
        dossier_payload = t.parse_theory_entity(old_dossier)
        assert isinstance(package_payload, t.ValidatedArgumentPackage)
        assert isinstance(dossier_payload, t.GateDossier)

        package_ref = EntityVersionRef(entity_id=old_package.entity_id, version=2)
        # Gate dossiers are immutable evidence packets.  Production promotion
        # therefore receives a new dossier identity and a distinct human G5
        # Decision, preserving the evaluation-only approval as audit history.
        dossier_ref = EntityVersionRef(
            entity_id=f"{old_dossier.entity_id}.production", version=1
        )
        package = self._entity(
            old_package.entity_id,
            package_payload.model_copy(
                update={
                    "g5_dossier_ref": dossier_ref,
                    "qualified_novelty": (
                        "Relative to the verified divisible-intensity comparator, the first mapping failure is the indivisible information-use margin; the claim is qualified to that exact scope."
                    ),
                    "unresolved_risks": (
                        "External literature coverage remains bounded by the verified comparator in this development fixture.",
                    ),
                    "release_mode": "production_candidate",
                    "novelty_claim_mode": "qualified",
                }
            ),
            title="Production-candidate validated argument package",
            summary="The exact verified argument chain with a qualified production claim.",
            created_at=_timestamp(0),
            version=2,
            supersedes=eref(old_package),
        )
        ordered = tuple(
            package_ref if item == eref(old_package) else item
            for item in dossier_payload.ordered_object_refs
        )
        requirements = tuple(
            (
                t.GateRequirement(
                    requirement_id=item.requirement_id,
                    description=(
                        "The production candidate makes only the exact qualified first-mapping-failure claim."
                        if item.requirement_id == "g5.no_external_claim"
                        else item.description
                    ),
                    evidence_refs=(
                        (package_ref,)
                        if item.requirement_id == "g5.no_external_claim"
                        else tuple(
                            package_ref if ref == eref(old_package) else ref
                            for ref in item.evidence_refs
                        )
                    ),
                    recorded_condition=item.recorded_condition,
                )
            )
            for item in dossier_payload.requirements
        )
        dossier = self._entity(
            dossier_ref.entity_id,
            dossier_payload.model_copy(
                update={
                    "ordered_object_refs": ordered,
                    "requirements": requirements,
                    "rationale": (
                        "The exact chain passes the production floors while limiting novelty to the verified first mapping failure."
                    ),
                    "prepared_at": _timestamp(0),
                }
            ),
            title="Production G5 argument-validation dossier",
            summary="Exact production qualification and G1--G4 authority evidence.",
            created_at=_timestamp(0),
        )

        validate_inputs = handoff["validate_inputs"]
        assert isinstance(validate_inputs, tuple)
        g1 = handoff["g1"]
        g2 = handoff["g2"]
        g3 = handoff["g3"]
        g4 = handoff["g4"]
        question = handoff["question"]
        assert all(isinstance(item, Decision) for item in (g1, g2, g3, g4))
        assert isinstance(question, EntityVersion)
        # The active-v3 registry deliberately preserves this mature route at
        # route_version=2.  Its larger active context is just above the Phase 2
        # helper's historical 32k budget, so begin it explicitly with the same
        # real boundary and a nonbinding 64k budget.
        self.route_counter += 1
        before = replay(self.layout)
        run = begin_run(
            self.layout,
            before,
            route_id="validate.argument_package",
            actor=AGENT,
            purpose="research_verification",
            compartments=("project_research",),
            focus_entity_ids=tuple(ref.entity_id for ref in validate_inputs),
            budget_units=64_000,
            route_run_id=f"run.gold.{self.route_counter}",
            context_manifest_id=f"context.gold.{self.route_counter}",
            created_at=_timestamp(0),
            route_registry_hash=ROUTE_REGISTRY_V3_HASH,
        )
        self.assertEqual(run.route_version, 2)
        self._commit_started_v3(
            before,
            run,
            outputs=(package, dossier),
            relations=(
                RelationVersion(
                    relation_id="relation.phase3.g5_governs_package",
                    relation_type="governs",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=dossier_ref,
                    target=package_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=_timestamp(0),
                ),
                RelationVersion(
                    relation_id="relation.phase3.package_includes_portfolio",
                    relation_type="includes",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=package_ref,
                    target=package_payload.result_portfolio_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=_timestamp(0),
                ),
                RelationVersion(
                    relation_id="relation.phase3.verification_validates_package",
                    relation_type="validates",
                    version=1,
                    project_id=self.snapshot.project_id,
                    source=package_payload.verification_bundle_ref,
                    target=package_ref,
                    dependency_mode="trace_only",
                    scope_ref=question.entity_id,
                    created_at=_timestamp(0),
                ),
            ),
            evidence_refs=validate_inputs,  # type: ignore[arg-type]
            authority_basis=tuple(
                item.decision_id for item in (g1, g2, g3, g4)  # type: ignore[union-attr]
            ),
            created_at=_timestamp(0),
        )
        promoted_snapshot = replay(self.layout)
        stale_ordered_refs = tuple(
            reference
            for reference in ordered
            if not _typed_reference_closure_is_current_and_fresh(
                promoted_snapshot, reference
            )
        )
        self.assertEqual(stale_ordered_refs, ())
        self.assertTrue(
            _typed_reference_closure_is_current_and_fresh(
                promoted_snapshot, dossier_ref
            )
        )
        production_g5 = Decision.model_validate(
            {
                **old_g5.model_dump(mode="python"),
                "decision_id": f"{old_g5.decision_id}.production",
                "version": 1,
                "question": "Approve this exact qualified production candidate?",
                "subject_ref": dossier_ref.entity_id,
                "evidence_refs": (dossier_ref.entity_id,),
                "recommendation": "Approve the qualified production-candidate handoff.",
                "rationale": (
                    "The exact argument and proof chain is unchanged; the package now limits its production claim to the verified first mapping failure."
                ),
                "unresolved_risks": (
                    "The production claim remains bounded by the fixture's verified literature control.",
                ),
                "decided_at": _timestamp(1),
                "supersedes": None,
            }
        )
        result = commit_decision(self.layout, production_g5)
        self.assertEqual(result.status, "committed")
        return package, dossier, production_g5

    def _make_rederivation(
        self,
        *,
        snapshot: Snapshot,
        package_ref: EntityVersionRef,
        claim_graph_ref: EntityVersionRef,
        obligation_ref: EntityVersionRef,
        verification_record_ref: EntityVersionRef,
        formal_model_ref: EntityVersionRef,
        assumption_map_ref: EntityVersionRef,
        g5_ref: DecisionVersionRef,
        rederiver: Actor,
        suffix: str,
        created_at: str,
    ) -> EntityVersion:
        before, run = self._begin_v3(
            route_id="verify.independent_rederivation",
            actor=rederiver,
            purpose="research_verification",
            focus_refs=(
                package_ref,
                claim_graph_ref,
                obligation_ref,
                formal_model_ref,
                assumption_map_ref,
            ),
            compartments=("blind_rederivation", "project_research"),
            created_at=created_at,
        )
        record_entity = self._entity_at(snapshot, verification_record_ref)
        verification = t.parse_theory_entity(record_entity)
        obligation = t.parse_theory_entity(self._entity_at(snapshot, obligation_ref))
        assert isinstance(verification, t.VerificationRecord)
        assert isinstance(obligation, t.ProofObligation)
        output_ref = EntityVersionRef(
            entity_id=f"rederivation.phase3.{suffix}", version=1
        )
        derivation_steps = (
            a.DerivationStep(
                step_id=f"step.{suffix}.factor",
                statement="Factor each precision-specific processing surplus into its precision and cost terms.",
                justification="The exact formal model and maintained assumptions define the receiver's net value.",
                source_refs=(formal_model_ref, assumption_map_ref),
            ),
            a.DerivationStep(
                step_id=f"step.{suffix}.threshold",
                statement="Solve the participation threshold and order the high- and low-precision thresholds.",
                justification="The obligation and claim graph fix the quantified threshold comparison.",
                dependency_step_ids=(f"step.{suffix}.factor",),
                source_refs=(claim_graph_ref, obligation_ref),
            ),
            a.DerivationStep(
                step_id=f"step.{suffix}.regimes",
                statement="Compare realized outcomes in every participation regime, including the tie boundary.",
                justification="The two earlier steps exhaust the maintained binary processing regimes.",
                dependency_step_ids=(f"step.{suffix}.threshold",),
                source_refs=(
                    claim_graph_ref,
                    obligation_ref,
                    formal_model_ref,
                    assumption_map_ref,
                ),
            ),
        )
        derived_conclusion = (
            "The exact threshold characterization in the obligation follows on the maintained binary-attention domain."
        )
        limitations = (
            "The result is re-derived only within the frozen model and stated quantifiers."
        )
        transcript = ReDerivationTranscript(
            record_ref=output_ref,
            package_ref=package_ref,
            claim_graph_ref=claim_graph_ref,
            claim_id=obligation.claim_id,
            obligation_ref=obligation_ref,
            formal_model_ref=formal_model_ref,
            assumption_map_ref=assumption_map_ref,
            rederiver=rederiver,
            steps=derivation_steps,
            derived_conclusion=derived_conclusion,
            comparison_to_claim="equivalent",
            outcome="agrees",
            limitations=limitations,
        )
        artifact_bytes = canonical_json_bytes(transcript)
        registration, artifact_ref, _ = self._registered_artifact(
            f"artifact.phase3.rederivation.{suffix}",
            artifact_bytes,
            logical_name=f"Blind re-derivation {suffix}",
            media_type="application/json",
            created_at=created_at,
        )
        originating = self._producer_binding(snapshot, verification_record_ref)
        proof_author = self._producer_binding(snapshot, obligation_ref)
        bindings = transaction_bindings(self.layout, run.route_run_id)
        payload = a.ReDerivationRecord(
            package_ref=package_ref,
            claim_graph_ref=claim_graph_ref,
            claim_id=obligation.claim_id,
            obligation_ref=obligation_ref,
            formal_model_ref=formal_model_ref,
            assumption_map_ref=assumption_map_ref,
            verification_record_ref=verification_record_ref,
            originating_verifier=verification.verifier,
            originating_verifier_run=originating,
            proof_author=AGENT,
            proof_author_output_ref=obligation_ref,
            proof_author_run=proof_author,
            rederiver=rederiver,
            route_run_id=run.route_run_id,
            route_run_hash=bindings["route_run_hash"],
            parent_runs=self._context_parent_bindings(
                before,
                run.route_run_id,
                excluded_run_ids=(originating.route_run_id,),
            ),
            derivation_artifact_ref=artifact_ref,
            derivation_steps=derivation_steps,
            derived_conclusion=derived_conclusion,
            comparison_to_claim="equivalent",
            context_manifest_hash=bindings["context_manifest_hash"],
            compiled_context_hash=bindings["compiled_context_hash"],
            excluded_proof_artifact_refs=verification.evidence_refs,
            outcome="agrees",
            limitations=limitations,
            performed_at=created_at,
        )
        entity = self._authoring_entity(
            f"rederivation.phase3.{suffix}",
            payload,
            title=f"Independent re-derivation of {obligation.obligation_id}",
            summary="Blind reconstruction agrees with the sealed verification record.",
            created_at=created_at,
            artifact_refs=(artifact_ref,),
        )
        self.assertEqual(eref(entity), output_ref)
        relations = tuple(
            self._relation(
                before,
                relation_id=f"relation.phase3.{suffix}.source.{index}",
                relation_type="depends_on",
                source=source,
                target=output_ref,
                created_at=created_at,
                source_field=(
                    self._facet_ref(before, source, field_path="/payload")
                    if source == package_ref
                    else None
                ),
                output_entities=(entity,),
            )
            for index, source in enumerate(
                (
                    package_ref,
                    claim_graph_ref,
                    obligation_ref,
                    formal_model_ref,
                    assumption_map_ref,
                    verification_record_ref,
                ),
                start=1,
            )
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=relations,
            artifacts=((registration, artifact_bytes),),
            evidence_refs=(
                package_ref,
                claim_graph_ref,
                obligation_ref,
                formal_model_ref,
                assumption_map_ref,
                g5_ref,
            ),
            authority_basis=(g5_ref.decision_id,),
            created_at=created_at,
        )
        return entity

    def _close_reviews(
        self,
        *,
        paper: EntityVersion,
        reader: EntityVersion,
        contracts: EntityVersion,
        assurance: EntityVersion,
        unit: EntityVersion,
        formal_review: EntityVersion,
        economic_review: EntityVersion,
        cold_review: EntityVersion,
        findings: tuple[EntityVersion, ...],
        generation: int,
        ready: bool,
        created_at: str,
    ) -> tuple[EntityVersion, EntityVersion | None]:
        unit_payload = a.parse_authoring_entity(unit)
        paper_payload = a.parse_authoring_entity(paper)
        assert isinstance(unit_payload, a.ManuscriptUnit)
        assert isinstance(paper_payload, a.PaperIR)
        closure_ref = EntityVersionRef(
            entity_id=f"closure.phase3.{generation}", version=1
        )
        brief_ref = (
            None
            if ready
            else EntityVersionRef(
                entity_id=f"revision_brief.phase3.{generation}", version=1
            )
        )
        actual = {
            "exact_g5_and_profile": True,
            "assurance_pass": True,
            "exact_span_trace": True,
            "layer_realization": True,
            "scope_and_assumptions": True,
            "bounded_evidentiary_language": True,
            "formal_fidelity": True,
            "economic_explanation": ready,
            "cold_reader_transfer": ready,
            "reader_dag_and_terminology": True,
            "no_governance_or_probe_leakage": True,
            "canonical_integration": True,
            "blocking_findings": ready,
        }
        check_evidence = {
            "assurance_pass": (eref(assurance),),
            "formal_fidelity": (eref(formal_review),),
            "economic_explanation": (eref(economic_review),),
            "cold_reader_transfer": (eref(cold_review),),
        }
        checks = tuple(
            a.AuthoringReadyCheck(
                check_id=check_id,  # type: ignore[arg-type]
                outcome="passed" if actual[check_id] else "failed",
                evidence_refs=check_evidence.get(check_id, (eref(unit),)),
                rationale=(
                    "The exact current inputs satisfy this noncompensatory requirement."
                    if actual[check_id]
                    else "An exact immutable review finding blocks this requirement."
                ),
            )
            for check_id in a.AUTHORING_READY_CHECK_ORDER
        )
        finding_payloads = [a.parse_authoring_entity(item) for item in findings]
        blocking_ids = tuple(
            sorted(
                item.finding_id
                for item in finding_payloads
                if isinstance(item, a.ReviewFinding) and item.blocking
            )
        )
        closure = a.ReviewClosure(
            compiler_mode=paper_payload.compiler_mode,
            paper_ir_ref=eref(paper),
            reader_path_ref=eref(reader),
            result_contract_set_ref=eref(contracts),
            assurance_bundle_ref=eref(assurance),
            manuscript_unit_ref=eref(unit),
            formal_fidelity_review_ref=eref(formal_review),
            economic_reader_review_ref=eref(economic_review),
            cold_reader_review_ref=eref(cold_review),
            closure_actor=CLOSURE_TOOL,
            checks=checks,
            blocking_finding_ids=blocking_ids,
            revision_brief_ref=brief_ref,
            status="authoring_ready" if ready else "blocked",
            evaluated_at=created_at,
        )
        output_compartments = tuple(
            sorted(
                {
                    *unit.access_compartments,
                    *cold_review.access_compartments,
                }
            )
        )
        closure_entity = self._authoring_entity(
            closure_ref.entity_id,
            closure,
            title=f"Deterministic review closure generation {generation}",
            summary=(
                "Every authoring-readiness dimension passes."
                if ready
                else "Economic explanation and transfer findings require revision."
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=output_compartments,
        )
        brief_entity: EntityVersion | None = None
        artifacts: tuple[tuple[ArtifactRegistration, bytes], ...] = ()
        if not ready:
            assert brief_ref is not None and findings
            brief_data = canonical_json_bytes(
                {
                    "protocol": "revision_brief_artifact.v1",
                    "closure_ref": closure_ref,
                    "finding_refs": tuple(eref(item) for item in findings),
                    "requirements": (
                        "Expand the force-margin-rival explanation and diagnostic ablation.",
                        "Explain the boundary and near-transfer prediction before re-review.",
                    ),
                }
            )
            registration, brief_artifact_ref, _ = self._registered_artifact(
                f"artifact.phase3.revision_brief.{generation}",
                brief_data,
                logical_name=f"Revision brief generation {generation}",
                media_type="application/json",
                created_at=created_at,
                privacy="restricted",
                access_compartments=output_compartments,
            )
            instructions = tuple(
                a.RevisionInstruction(
                    instruction_id=f"instruction.{generation}.{index}",
                    finding_ref=eref(finding_entity),
                    action=(
                        "add_boundary"
                        if isinstance(finding_payload, a.ReviewFinding)
                        and finding_payload.category == "boundary"
                        else "repair_explanation"
                    ),
                    requirement=(
                        finding_payload.recommended_repair
                        if isinstance(finding_payload, a.ReviewFinding)
                        else "Resolve the exact blocking finding."
                    ),
                    blocking=True,
                )
                for index, (finding_entity, finding_payload) in enumerate(
                    zip(findings, finding_payloads), start=1
                )
            )
            brief = a.RevisionBrief(
                manuscript_unit_ref=eref(unit),
                review_closure_ref=closure_ref,
                finding_refs=tuple(eref(item) for item in findings),
                instructions=instructions,
                brief_artifact_ref=brief_artifact_ref,
                prepared_by=CLOSURE_TOOL,
                prepared_at=created_at,
            )
            brief_entity = self._authoring_entity(
                brief_ref.entity_id,
                brief,
                title="Decision-complete manuscript revision brief",
                summary="Every blocking finding is mapped to one exact repair.",
                created_at=created_at,
                artifact_refs=(brief_artifact_ref,),
                privacy="restricted",
                access_compartments=output_compartments,
            )
            artifacts = ((registration, brief_data),)
        focus = (
            eref(assurance),
            eref(unit),
            eref(formal_review),
            eref(economic_review),
            eref(cold_review),
            *(eref(item) for item in findings),
        )
        before, run = self._begin_v3(
            route_id="close.manuscript_review",
            actor=CLOSURE_TOOL,
            purpose="research_review",
            focus_refs=focus,
            created_at=created_at,
            compartments=output_compartments,
            privacy_clearance="restricted",
        )
        outputs = (
            (closure_entity,)
            if brief_entity is None
            else (closure_entity, brief_entity)
        )
        relations: list[RelationVersion] = []
        for index, review in enumerate(
            (formal_review, economic_review, cold_review), start=1
        ):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase3.closure.{generation}.review.{index}",
                    relation_type="validates",
                    source=eref(review),
                    target=closure_ref,
                    created_at=created_at,
                    output_entities=outputs,
                    privacy="restricted",
                    access_compartments=output_compartments,
                )
            )
        relations.append(
            self._relation(
                before,
                relation_id=f"relation.phase3.closure.{generation}.assurance",
                relation_type="depends_on",
                source=eref(assurance),
                target=closure_ref,
                created_at=created_at,
                output_entities=outputs,
                privacy="restricted",
                access_compartments=output_compartments,
            )
        )
        if brief_entity is not None:
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase3.closure.{generation}.brief",
                    relation_type="depends_on",
                    source=closure_ref,
                    target=eref(brief_entity),
                    created_at=created_at,
                    output_entities=outputs,
                    privacy="restricted",
                    access_compartments=output_compartments,
                )
            )
        self._commit_started_v3(
            before,
            run,
            outputs=outputs,
            relations=tuple(relations),
            artifacts=artifacts,
            evidence_refs=focus,
            created_at=created_at,
            privacy="restricted",
            access_compartments=output_compartments,
        )
        return closure_entity, brief_entity

    def _record_human_effort(
        self,
        *,
        first_unit: EntityVersion,
        revised_unit: EntityVersion,
        created_at: str,
    ) -> EntityVersion:
        first = a.parse_authoring_entity(first_unit)
        revised = a.parse_authoring_entity(revised_unit)
        assert isinstance(first, a.ManuscriptUnit)
        assert isinstance(revised, a.ManuscriptUnit)
        before, run = self._begin_v3(
            route_id="record.human_effort",
            actor=HUMAN,
            purpose="human_effort_measurement",
            focus_refs=(eref(revised_unit),),
            created_at=created_at,
            compartments=revised_unit.access_compartments,
            privacy_clearance=revised_unit.privacy,
        )
        payload = a.HumanEffortRecord(
            manuscript_unit_ref=eref(revised_unit),
            human=HUMAN,
            events=(
                a.HumanEffortEvent(
                    event_id="effort.phase3.review_repairs",
                    occurred_at=created_at,
                    active_minutes=18,
                    affected_assertion_ids=(
                        "assertion.mechanism",
                        "assertion.example",
                        "assertion.boundary",
                    ),
                    disposition="light_edit",
                    severity="medium",
                    category="mechanism_intuition_repair",
                    before_artifact_ref=first.manuscript_artifact_ref,
                    after_artifact_ref=revised.manuscript_artifact_ref,
                    note="Expanded the competing forces, diagnostic ablation, boundary, and near-transfer explanation in response to exact review findings.",
                ),
            ),
            recorded_at=created_at,
        )
        entity = self._authoring_entity(
            "effort.phase3.main_result",
            payload,
            title="Human effort for the Phase 3 repair loop",
            summary="Active substantive intervention is recorded separately from compute time.",
            created_at=created_at,
            artifact_refs=(
                first.manuscript_artifact_ref,
                revised.manuscript_artifact_ref,
            ),
            privacy="restricted",
            access_compartments=revised_unit.access_compartments,
        )
        relation = self._relation(
            before,
            relation_id="relation.phase3.effort.unit",
            relation_type="reports_effort",
            source=eref(revised_unit),
            target=eref(entity),
            created_at=created_at,
            output_entities=(entity,),
            privacy="restricted",
            access_compartments=revised_unit.access_compartments,
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=(relation,),
            evidence_refs=(
                eref(revised_unit),
                first.manuscript_artifact_ref,
                revised.manuscript_artifact_ref,
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=revised_unit.access_compartments,
        )
        return entity

    def _adjudicate_reader_probe(
        self,
        *,
        assignment: EntityVersion,
        unit: EntityVersion,
        probe: EntityVersion,
        response: EntityVersion,
        generation: int,
        transfer_pass: bool,
        created_at: str,
    ) -> tuple[EntityVersion, tuple[EntityVersion, ...]]:
        unit_payload = a.parse_authoring_entity(unit)
        probe_payload = a.parse_authoring_entity(probe)
        response_payload = a.parse_authoring_entity(response)
        assert isinstance(unit_payload, a.ManuscriptUnit)
        assert isinstance(probe_payload, a.ReaderProbeSet)
        assert isinstance(response_payload, a.ReaderResponse)
        store = ObjectStore(self.layout)
        key = ReaderAnswerKeyArtifact.model_validate_json(
            store.read_bytes(
                "artifacts", probe_payload.answer_key_artifact_ref.content_hash
            ),
            strict=True,
        )
        response_artifact = ReaderResponseArtifact.model_validate_json(
            store.read_bytes(
                "artifacts", response_payload.response_artifact_ref.content_hash
            ),
            strict=True,
        )
        outcomes = {
            kind: (transfer_pass if kind == "near_transfer" else True)
            for kind in a.READER_PROBE_KIND_ORDER
        }
        results = tuple(
            a.ColdReaderProbeResult(
                probe_id=answer.probe_id,
                kind=answer.kind,
                outcome="passed" if outcomes[answer.kind] else "failed",
                response_excerpt_hash=answer.response_hash,
                answer_key_criterion_hash=criterion.criterion_hash,
                rationale=(
                    "The response reconstructs the exact requested distinction."
                    if outcomes[answer.kind]
                    else "The response does not make a determinate near-transfer prediction from the mechanism."
                ),
            )
            for answer, criterion in zip(response_artifact.answers, key.criteria)
        )
        assessment = a.ColdReaderAssessment(
            question_and_benchmark_retell_passed=True,
            exact_scope_recovery_passed=True,
            assumption_role_recovery_passed=True,
            boundary_discrimination_passed=True,
            near_transfer_passed=transfer_pass,
            response_artifact_ref=response_payload.response_artifact_ref,
            probe_results=results,
        )
        output_compartments = tuple(
            sorted(
                {
                    *probe.access_compartments,
                    "cold_reader_evaluation",
                }
            )
        )
        before, run = self._begin_v3(
            route_id="adjudicate.reader_probe",
            actor=PROBE_ADJUDICATOR,
            purpose="reader_evaluation_adjudication",
            focus_refs=(eref(assignment), eref(unit), eref(probe), eref(response)),
            created_at=created_at,
            compartments=output_compartments,
            privacy_clearance="restricted",
        )
        findings: list[EntityVersion] = []
        if not transfer_pass:
            finding = a.ReviewFinding(
                finding_id=f"finding.cold.transfer.{generation}",
                assignment_ref=eref(assignment),
                manuscript_unit_ref=eref(unit),
                reviewed_artifact_ref=unit_payload.manuscript_artifact_ref,
                role="cold_reader",
                critic=PROBE_ADJUDICATOR,
                category="transfer",
                severity="error",
                assertion_ids=("assertion.mechanism", "assertion.boundary"),
                evidence_refs=(
                    eref(unit),
                    response_payload.response_artifact_ref,
                    probe_payload.answer_key_artifact_ref,
                ),
                summary="The cold reader can retell the theorem but cannot transfer the mechanism to a weaker precision-linked cost.",
                recommended_repair="Explain how the cost perturbation changes the threshold gap and why equal uptake restores the conditional ranking.",
                blocking=True,
                reported_at=created_at,
            )
            findings.append(
                self._authoring_entity(
                    f"finding.phase3.cold.{generation}",
                    finding,
                    title="Blocking near-transfer finding",
                    summary="Cold-reader transfer fails on the frozen manuscript.",
                    created_at=created_at,
                    artifact_refs=(
                        unit_payload.manuscript_artifact_ref,
                        response_payload.response_artifact_ref,
                        probe_payload.answer_key_artifact_ref,
                    ),
                    privacy="restricted",
                    access_compartments=output_compartments,
                )
            )
        bindings = transaction_bindings(self.layout, run.route_run_id)
        review = a.ReviewRecord(
            assignment_ref=eref(assignment),
            manuscript_unit_ref=eref(unit),
            reviewed_artifact_ref=unit_payload.manuscript_artifact_ref,
            role="cold_reader",
            reviewer=PROBE_ADJUDICATOR,
            canonical_writer=WRITER,
            context_hash=bindings["compiled_context_hash"],
            assessment=assessment,
            finding_refs=tuple(eref(item) for item in findings),
            reader_response_ref=eref(response),
            answer_key_artifact_ref=probe_payload.answer_key_artifact_ref,
            adjudicator=PROBE_ADJUDICATOR,
            reviewed_at=created_at,
        )
        review_entity = self._authoring_entity(
            f"review.phase3.cold_reader.{generation}",
            review,
            title=f"Cold-reader adjudication generation {generation}",
            summary="Five probe outcomes bound to exact response and answer-key hashes.",
            created_at=created_at,
            artifact_refs=(
                unit_payload.manuscript_artifact_ref,
                response_payload.response_artifact_ref,
                probe_payload.answer_key_artifact_ref,
            ),
            privacy="restricted",
            access_compartments=output_compartments,
        )
        outputs = (*findings, review_entity)
        relations: list[RelationVersion] = []
        for index, finding in enumerate(findings):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase3.cold.{generation}.finding.{index}",
                    relation_type="reviews",
                    source=eref(unit),
                    target=eref(finding),
                    created_at=created_at,
                    output_entities=outputs,
                    privacy="restricted",
                    access_compartments=output_compartments,
                )
            )
        relations.extend(
            (
                self._relation(
                    before,
                    relation_id=f"relation.phase3.cold.{generation}.response",
                    relation_type="validates",
                    source=eref(response),
                    target=eref(review_entity),
                    created_at=created_at,
                    output_entities=outputs,
                    privacy="restricted",
                    access_compartments=output_compartments,
                ),
                self._relation(
                    before,
                    relation_id=f"relation.phase3.cold.{generation}.unit",
                    relation_type="reviews",
                    source=eref(unit),
                    target=eref(review_entity),
                    created_at=created_at,
                    output_entities=outputs,
                    privacy="restricted",
                    access_compartments=output_compartments,
                ),
            )
        )
        self._commit_started_v3(
            before,
            run,
            outputs=outputs,
            relations=tuple(relations),
            evidence_refs=(
                eref(assignment),
                eref(unit),
                eref(probe),
                eref(response),
                probe_payload.probe_artifact_ref,
                probe_payload.answer_key_artifact_ref,
                response_payload.response_artifact_ref,
                unit_payload.manuscript_artifact_ref,
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=output_compartments,
        )
        return review_entity, tuple(findings)

    def _make_assurance_bundle(
        self,
        *,
        snapshot: Snapshot,
        package_ref: EntityVersionRef,
        claim_graph_ref: EntityVersionRef,
        obligation_refs: tuple[EntityVersionRef, ...],
        verification_record_refs: tuple[EntityVersionRef, ...],
        verification_bundle_ref: EntityVersionRef,
        formal_model_ref: EntityVersionRef,
        assumption_map_ref: EntityVersionRef,
        rederivation_refs: tuple[EntityVersionRef, ...],
        g5_ref: DecisionVersionRef,
        created_at: str,
    ) -> EntityVersion:
        focus = (
            package_ref,
            claim_graph_ref,
            formal_model_ref,
            assumption_map_ref,
            verification_bundle_ref,
            *obligation_refs,
            *verification_record_refs,
            *rederivation_refs,
        )
        before, run = self._begin_v3(
            route_id="audit.argument_assurance",
            actor=ASSURANCE_AUDITOR,
            purpose="research_verification",
            focus_refs=focus,
            created_at=created_at,
        )
        registrations: list[tuple[ArtifactRegistration, bytes]] = []
        audits: list[a.ProofAudit] = []
        bundle_ref = EntityVersionRef(
            entity_id="assurance.bundle.phase3.attention_precision", version=1
        )
        for index, (obligation_ref, verification_ref, rederivation_ref) in enumerate(
            zip(obligation_refs, verification_record_refs, rederivation_refs), start=1
        ):
            obligation = t.parse_theory_entity(self._entity_at(snapshot, obligation_ref))
            verification = t.parse_theory_entity(
                self._entity_at(snapshot, verification_ref)
            )
            rederivation = a.parse_authoring_entity(
                self._entity_at(snapshot, rederivation_ref)
            )
            assert isinstance(obligation, t.ProofObligation)
            assert isinstance(verification, t.VerificationRecord)
            assert isinstance(rederivation, a.ReDerivationRecord)
            audit_id = f"audit.phase3.proof.{index}"
            limitations = (
                "The audit establishes fidelity within the exact frozen domain, not truth outside it."
            )
            report = ProofAuditReportArtifact(
                assurance_bundle_ref=bundle_ref,
                audit_id=audit_id,
                claim_graph_ref=claim_graph_ref,
                claim_id=obligation.claim_id,
                obligation_ref=obligation_ref,
                formal_model_ref=formal_model_ref,
                assumption_map_ref=assumption_map_ref,
                proof_artifact_ref=verification.evidence_refs[0],
                verification_record_ref=verification_ref,
                rederivation_ref=rederivation_ref,
                originating_verifier=verification.verifier,
                auditor=ASSURANCE_AUDITOR,
                outcome="passed",
                comparison_outcome=rederivation.outcome,
                limitations=limitations,
            )
            report_bytes = canonical_json_bytes(report)
            registration, report_ref, _ = self._registered_artifact(
                f"artifact.phase3.proof_audit.{index}",
                report_bytes,
                logical_name=f"Independent proof audit {index}",
                media_type="application/json",
                created_at=created_at,
            )
            registrations.append((registration, report_bytes))
            audits.append(
                a.ProofAudit(
                    audit_id=audit_id,
                    claim_graph_ref=claim_graph_ref,
                    claim_id=obligation.claim_id,
                    obligation_ref=obligation_ref,
                    formal_model_ref=formal_model_ref,
                    assumption_map_ref=assumption_map_ref,
                    proof_artifact_ref=verification.evidence_refs[0],
                    verification_record_ref=verification_ref,
                    rederivation_ref=rederivation_ref,
                    originating_verifier=verification.verifier,
                    auditor=ASSURANCE_AUDITOR,
                    audit_report_ref=report_ref,
                    outcome="passed",
                    comparison_outcome=rederivation.outcome,
                    limitations=limitations,
                    audited_at=created_at,
                )
            )
        headline_audits = [
            item for item in audits if item.claim_id == "claim.headline_reversal"
        ]
        self.assertTrue(headline_audits)
        headline_obligation = headline_audits[0].obligation_ref

        # Execute one exact finite diagnostic instead of allowing assurance to
        # self-exempt from every reproducible check.  This corroborates only a
        # normalized nonnegative-surplus relation at two declared cases; it is
        # explicitly not treated as proof of the universal theorem.
        protocol = "exact_polynomial_relation_scan.v1"
        code_bytes = harness_protocol_code_bytes(protocol)
        code_hash = harness_protocol_code_hash(protocol)
        left = ExactPolynomial.normalized(((Fraction(1), {"x": 1}),))
        right = ExactPolynomial()
        cases = (
            ExactAssignment(case_id="case.zero", values=(("x", Fraction(0)),)),
            ExactAssignment(case_id="case.one", values=(("x", Fraction(1)),)),
        )
        scan = run_exact_polynomial_relation_scan(
            ExactPolynomialRelation(left=left, operator="ge", right=right),
            cases,
            code_hash=code_hash,
        )
        harness_artifacts: list[tuple[ArtifactRegistration, ArtifactDependencyRef, bytes]] = []
        for suffix, data in (
            ("code", code_bytes),
            ("input", scan.input.canonical_bytes()),
            ("output", scan.output.canonical_bytes()),
            ("receipt", scan.receipt.canonical_bytes()),
        ):
            harness_artifacts.append(
                self._registered_artifact(
                    f"artifact.phase3.harness.{suffix}",
                    data,
                    logical_name=f"Exact finite harness {suffix}",
                    media_type="application/json",
                    created_at=created_at,
                )
            )
        registrations.extend((item[0], item[2]) for item in harness_artifacts)
        by_suffix = {
            item[0].artifact_id.rsplit(".", 1)[-1]: item[1]
            for item in harness_artifacts
        }
        polynomial_spec = a.ExactPolynomialSpec(
            terms=(
                a.ExactPolynomialTermSpec(
                    coefficient=a.ExactRationalValue(numerator=1, denominator=1),
                    powers=(a.PolynomialPowerSpec(variable="x", power=1),),
                ),
            )
        )
        case_specs = tuple(
            a.ExactAssignmentSpec(
                case_id=item.case_id,
                values=tuple(
                    a.ExactAssignmentValue(
                        variable=variable,
                        value=a.ExactRationalValue(
                            numerator=value.numerator,
                            denominator=value.denominator,
                        ),
                    )
                    for variable, value in item.values
                ),
            )
            for item in cases
        )
        scan_evidence = a.CounterexampleScanEvidence(
            predicate=a.PolynomialRelationPredicate(
                left=polynomial_spec,
                relation="ge",
                right=a.ExactPolynomialSpec(),
            ),
            cases=case_specs,
            code_hash=scan.input.code_hash,
            input_hash=scan.input.input_hash,
            output_hash=scan.output.output_hash,
            domain_hash=scan.output.domain_hash,
            relation_hash=scan.output.relation_hash,
            checked_count=scan.output.checked_count,
            outcome=scan.output.outcome,
            witness_case_id=None,
            witness_hash=None,
            receipt_hash=scan.receipt.receipt_hash,
        )
        tool_receipt = a.ToolHarnessReceipt(
            receipt_id="receipt.phase3.headline.finite",
            harness_kind="counterexample_search",
            claim_graph_ref=claim_graph_ref,
            claim_id="claim.headline_reversal",
            obligation_ref=headline_obligation,
            tool_name="econ_theorist.assurance",
            tool_version=protocol,
            code_ref=by_suffix["code"],
            input_ref=by_suffix["input"],
            output_ref=by_suffix["output"],
            receipt_ref=by_suffix["receipt"],
            domain="The exact normalized cases x=0 and x=1 for a nonnegative surplus diagnostic.",
            outcome="no_counterexample_found",
            evidentiary_role="corroboration_only",
            reproducible_evidence=scan_evidence,
            limitations="The finite diagnostic corroborates two cases and cannot prove the universal threshold theorem.",
            executed_at=created_at,
        )
        nonapplicability: list[a.HarnessNonApplicabilityRecord] = []
        for audit in headline_audits:
            nonapplicability.append(
                a.HarnessNonApplicabilityRecord(
                    record_id=f"harness.na.{audit.audit_id}.symbolic",
                    family="symbolic_identity",
                    claim_graph_ref=claim_graph_ref,
                    claim_id=audit.claim_id,
                    obligation_ref=audit.obligation_ref,
                    reason_code="no_algebraic_identity",
                    explanation="The audited result is a quantified regime characterization rather than a single normalized polynomial identity.",
                    evidence_refs=(audit.obligation_ref,),
                    determined_by=ASSURANCE_AUDITOR,
                )
            )
            if audit.obligation_ref != headline_obligation:
                nonapplicability.append(
                    a.HarnessNonApplicabilityRecord(
                        record_id=f"harness.na.{audit.audit_id}.finite",
                        family="counterexample_search",
                        claim_graph_ref=claim_graph_ref,
                        claim_id=audit.claim_id,
                        obligation_ref=audit.obligation_ref,
                        reason_code="covered_by_stronger_exact_argument",
                        explanation="This auxiliary headline obligation is covered by its passed exact proof audit; a separate finite grid would add no distinct diagnostic burden.",
                        evidence_refs=(audit.obligation_ref, audit.audit_report_ref),
                        determined_by=ASSURANCE_AUDITOR,
                    )
                )
        bindings = transaction_bindings(self.layout, run.route_run_id)
        payload = a.AssuranceBundle(
            package_ref=package_ref,
            g5_decision_ref=g5_ref,
            claim_graph_ref=claim_graph_ref,
            headline_claim_id="claim.headline_reversal",
            formal_model_ref=formal_model_ref,
            assumption_map_ref=assumption_map_ref,
            verification_bundle_ref=verification_bundle_ref,
            rederivation_refs=rederivation_refs,
            proof_audits=tuple(audits),
            tool_receipts=(tool_receipt,),
            tool_non_applicability=tuple(nonapplicability),
            assembled_by=ASSURANCE_AUDITOR,
            route_run_id=run.route_run_id,
            route_run_hash=bindings["route_run_hash"],
            context_manifest_hash=bindings["context_manifest_hash"],
            compiled_context_hash=bindings["compiled_context_hash"],
            assembled_at=created_at,
        )
        report_refs = tuple(item.audit_report_ref for item in audits)
        harness_refs = tuple(item[1] for item in harness_artifacts)
        proof_evidence = tuple(audit.proof_artifact_ref for audit in audits)
        assurance_artifact_refs = tuple(
            sorted(
                {*proof_evidence, *report_refs, *harness_refs},
                key=lambda item: (item.artifact_id, item.version, item.content_hash),
            )
        )
        entity = self._authoring_entity(
            "assurance.bundle.phase3.attention_precision",
            payload,
            title="Independent argument-assurance bundle",
            summary="Every proof revision is audited and the blind reconstructions agree.",
            created_at=created_at,
            artifact_refs=assurance_artifact_refs,
        )
        self.assertEqual(eref(entity), bundle_ref)
        required_sources = {
            package_ref,
            claim_graph_ref,
            formal_model_ref,
            assumption_map_ref,
            verification_bundle_ref,
            *rederivation_refs,
            *obligation_refs,
            *verification_record_refs,
        }
        relations = tuple(
            self._relation(
                before,
                relation_id=f"relation.phase3.assurance.source.{index}",
                relation_type="validates",
                source=source,
                target=bundle_ref,
                created_at=created_at,
                source_field=(
                    self._facet_ref(before, source, field_path="/payload")
                    if source == package_ref
                    else None
                ),
                output_entities=(entity,),
            )
            for index, source in enumerate(
                sorted(required_sources, key=lambda item: (item.entity_id, item.version)),
                start=1,
            )
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=relations,
            artifacts=tuple(registrations),
            evidence_refs=(*focus, g5_ref, *proof_evidence),
            authority_basis=(g5_ref.decision_id,),
            created_at=created_at,
        )
        return entity

    def _commit_profile_decisions(
        self,
        *,
        package: EntityVersion,
        question_ref: EntityVersionRef,
        created_at: str,
    ) -> tuple[Decision, Decision, Decision]:
        values = (
            (
                "decision.phase3.theory_mode",
                "theory_mode",
                "pure_theory",
                "Use a pure-theory authoring mode for this exact package?",
            ),
            (
                "decision.phase3.ambition",
                "ambition",
                "top_five",
                "Target a top-five general-interest theory presentation?",
            ),
            (
                "decision.phase3.audience",
                "audience",
                "general_economic_theorists",
                "Write first for general economic theorists?",
            ),
        )
        decisions: list[Decision] = []
        for index, (decision_id, kind, option, question) in enumerate(values):
            decision = Decision(
                decision_id=decision_id,
                version=1,
                project_id=self.snapshot.project_id,
                decision_kind=kind,  # type: ignore[arg-type]
                subject_ref=package.entity_id,
                scope_ref=question_ref.entity_id,
                question=question,
                options=(option, "revise"),
                selected_option=option,
                recommendation=f"Confirm {option} for the Phase 3 design.",
                rationale="The human owner fixes this profile dimension before prose is generated.",
                evidence_refs=(package.entity_id, question_ref.entity_id),
                unresolved_risks=(
                    "The profile controls presentation and does not certify publication quality.",
                ),
                required_authority="L2",
                decider=HUMAN,
                decided_at=_timestamp(6 + index),
                status="confirmed",
            )
            result = commit_decision(self.layout, decision)
            self.assertEqual(result.status, "committed")
            decisions.append(decision)
        return tuple(decisions)  # type: ignore[return-value]

    def _seal_assignment(self, assignment: a.CriticAssignment) -> a.CriticAssignment:
        return a.CriticAssignment.model_validate(
            {
                **assignment.model_dump(mode="python"),
                "sealed_context_hash": critic_assignment_contract_hash(assignment),
            }
        )

    def _make_authoring_design(
        self,
        *,
        package: EntityVersion,
        assurance: EntityVersion,
        production_g5: Decision,
        profile_decisions: tuple[Decision, Decision, Decision],
        g4_ref: DecisionVersionRef,
        created_at: str,
    ) -> tuple[
        EntityVersion,
        EntityVersion,
        EntityVersion,
        EntityVersion,
        tuple[EntityVersion, ...],
    ]:
        package_payload = t.parse_theory_entity(package)
        assert isinstance(package_payload, t.ValidatedArgumentPackage)
        claim_entity = self._entity_at(replay(self.layout), package_payload.claim_graph_ref)
        claim_graph = t.parse_theory_entity(claim_entity)
        assert isinstance(claim_graph, t.ClaimGraph)
        headline_index = next(
            index
            for index, claim in enumerate(claim_graph.claims)
            if claim.claim_id == "claim.headline_reversal"
        )
        headline = claim_graph.claims[headline_index]
        theory_decision, ambition_decision, audience_decision = profile_decisions
        decision_refs = tuple(
            DecisionVersionRef(decision_id=item.decision_id, version=item.version)
            for item in profile_decisions
        )
        g5_ref = DecisionVersionRef(
            decision_id=production_g5.decision_id, version=production_g5.version
        )

        profile_bytes = canonical_json_bytes(
            {
                "theory_mode": theory_decision.selected_option,
                "ambition": ambition_decision.selected_option,
                "audience": audience_decision.selected_option,
                "archetype": headline.archetype,
            }
        )
        profile_registration, profile_artifact_ref, _ = self._registered_artifact(
            "artifact.phase3.resolved_profile",
            profile_bytes,
            logical_name="Resolved Phase 3 authoring profile",
            media_type="application/json",
            created_at=created_at,
        )
        before, run = self._begin_v3(
            route_id="design.reader_path",
            actor=WRITER,
            purpose="research_authoring",
            focus_refs=(eref(package), eref(assurance)),
            created_at=created_at,
        )
        archetype_path = f"/payload/claims/{headline_index}/archetype"
        archetype_source = self._facet_ref(
            before,
            package_payload.claim_graph_ref,
            facet="formal",
            field_path=archetype_path,
        )
        profile = a.ResolvedProfileManifest(
            universal_floor_version="universal_floor.phase3.v1",
            theory_mode=theory_decision.selected_option,
            theory_mode_decision_ref=decision_refs[0],
            ambition=ambition_decision.selected_option,
            ambition_decision_ref=decision_refs[1],
            primary_result_archetype=headline.archetype,
            result_archetype_source=archetype_source,
            g4_decision_ref=g4_ref,
            primary_audience=audience_decision.selected_option,
            audience_decision_ref=decision_refs[2],
            source_state_revision=before.head,
            profile_artifact_ref=profile_artifact_ref,
            projection_hash="0" * 64,
            resolved_at=created_at,
        )
        profile = a.ResolvedProfileManifest.model_validate(
            {
                **profile.model_dump(mode="python"),
                "projection_hash": resolved_profile_projection_hash(profile),
            }
        )
        profile_entity = self._authoring_entity(
            "profile.phase3.attention_precision",
            profile,
            title="Resolved theory authoring profile",
            summary="Pure theory, top-five ambition, and general-theorist audience are human-fixed.",
            created_at=created_at,
            artifact_refs=(profile_artifact_ref,),
        )
        profile_ref = eref(profile_entity)

        def source(path: str, facet: str = "formal") -> SemanticFacetRef:
            return self._facet_ref(
                before,
                package_payload.claim_graph_ref,
                facet=facet,
                field_path=f"/payload/claims/{headline_index}/{path}",
            )

        projection = a.ClaimProjection(
            projection_id="projection.headline_reversal",
            claim_graph_ref=package_payload.claim_graph_ref,
            claim_id=headline.claim_id,
            formal_statement=headline.formal_statement,
            scope=headline.domain,
            assumption_ids=headline.assumption_ids,
            semantic_translation=headline.semantic_translation,
            formal_statement_source=source("formal_statement"),
            scope_source=source("domain"),
            assumption_source_refs=(source("assumption_ids"),),
            translation_source=source("semantic_translation"),
            allowed_wording_strength="entailed_equivalent",
            permitted_locations=("section.main_result",),
            prohibited_extensions=(
                "Do not equate accuracy with welfare.",
                "Do not claim that coarse information is always superior.",
                "Do not extend the result beyond indivisible processing.",
            ),
        )
        paper = a.PaperIR(
            compiler_mode="working",
            package_ref=eref(package),
            assurance_bundle_ref=eref(assurance),
            g5_decision_ref=g5_ref,
            source_state_revision=before.head,
            upstream_projection_hash="0" * 64,
            language="English",
            resolved_profile_manifest_ref=profile_ref,
            claim_projections=(projection,),
            ontology=(
                a.EconomicOntologyEntry(
                    object_id="object.processing_decision",
                    formal_symbol="d(x)",
                    preferred_economic_name="processing decision",
                    short_definition="Whether the receiver pays the precision-linked cost and uses the signal.",
                    economic_interpretation="The extensive information-use margin.",
                    mechanism_role="It lets precision change both conditional accuracy and whether information is used.",
                    allowed_aliases=("information-use decision",),
                    forbidden_names=("estimator", "algorithm"),
                    first_use_section_id="section.main_result",
                ),
            ),
            narrative_spine=a.NarrativeSpine(
                phenomenon_or_question="Can a more precise signal produce lower realized accuracy?",
                natural_benchmark="Conditional on processing, greater precision improves accuracy.",
                unresolved_benchmark_delta="The benchmark holds the processing decision fixed.",
                new_economic_or_conceptual_object="A precision-linked extensive information-use margin.",
                central_result="An exact cost interval makes the coarse signal used and the precise signal ignored.",
                why_not_immediate="Precision raises conditional value but also raises the processing cost more rapidly.",
                boundary_and_failure_conditions="Tie-breaking controls endpoint inclusion and a common cost removes the reversal.",
                economic_consequence_or_changed_practice="Information quality and information uptake must be evaluated jointly.",
                literature_update="The result qualifies the divisible-intensity comparator at the indivisible-use margin.",
                source_refs=(eref(package), package_payload.economic_argument_graph_ref),
            ),
            canonical_writer=WRITER,
            built_at=created_at,
        )
        paper = a.PaperIR.model_validate(
            {
                **paper.model_dump(mode="python"),
                "upstream_projection_hash": paper_ir_upstream_projection_hash(
                    paper, profile
                ),
            }
        )
        paper_entity = self._authoring_entity(
            "paper_ir.phase3.attention_precision",
            paper,
            title="Working Paper IR for the headline reversal",
            summary="Exact claim projection, economic ontology, and narrative spine.",
            created_at=created_at,
        )
        paper_ref = eref(paper_entity)

        knowledge = (
            a.ReaderKnowledgeItem(
                knowledge_id="knowledge.binary_choice",
                content="A receiver may process or ignore a binary signal.",
                origin="target_audience_background",
            ),
            a.ReaderKnowledgeItem(
                knowledge_id="knowledge.conditional_benchmark",
                content="Conditional accuracy increases with precision.",
                origin="delivered_update",
                producer_state_id="state.benchmark",
            ),
            a.ReaderKnowledgeItem(
                knowledge_id="knowledge.extensive_margin",
                content="Precision also changes the receiver's decision to use information.",
                origin="delivered_update",
                producer_state_id="state.mechanism",
            ),
        )
        states = (
            a.ReaderBeliefState(
                state_id="state.benchmark",
                known_on_entry=("knowledge.binary_choice",),
                default_expectation="More precise information improves realized accuracy.",
                live_question="What does that benchmark hold fixed?",
                update="It holds information use fixed.",
                delivered_knowledge_ids=("knowledge.conditional_benchmark",),
                support_refs=(package_payload.benchmark_set_ref,),
                transfer_objective="Separate conditional informativeness from uptake.",
                unresolved_on_exit="Whether precision changes information use.",
            ),
            a.ReaderBeliefState(
                state_id="state.mechanism",
                known_on_entry=(
                    "knowledge.binary_choice",
                    "knowledge.conditional_benchmark",
                ),
                default_expectation="The conditional comparison determines realized accuracy.",
                live_question="Can the precise signal be ignored while the coarse signal is used?",
                update="A precision-linked convex cost opens exactly that participation regime.",
                delivered_knowledge_ids=("knowledge.extensive_margin",),
                support_refs=(package_payload.economic_argument_graph_ref,),
                transfer_objective="Reconstruct the competing forces, threshold interval, and failure boundary.",
                unresolved_on_exit="How the two thresholds order.",
            ),
        )
        section = a.SectionContract(
            section_id="section.main_result",
            role="result_block",
            entry_state_id="state.benchmark",
            exit_state_id="state.mechanism",
            central_question="When does greater precision deter information use enough to reverse realized accuracy?",
            required_claim_projection_ids=(projection.projection_id,),
            claims_introduced=(headline.claim_id,),
            economic_object_ids_to_interpret=("object.processing_decision",),
            reader_update_on_exit="The reader can explain the reversal through the extensive margin and identify its boundary.",
            open_question_for_next_section="How does the proof isolate the exact interval?",
            reader_cost_constraint="Introduce the benchmark and two competing forces before the theorem.",
            appendix_boundary="main_text",
            forbidden_detours=("Do not lead with proof notation.",),
        )
        reader = a.ReaderPath(
            paper_ir_ref=paper_ref,
            knowledge_items=knowledge,
            reader_states=states,
            state_edges=(
                a.ReaderStateEdge(
                    source_state_id="state.benchmark",
                    target_state_id="state.mechanism",
                ),
            ),
            section_contracts=(section,),
            ordered_section_ids=(section.section_id,),
            built_at=created_at,
        )
        reader_entity = self._authoring_entity(
            "reader_path.phase3.attention_precision",
            reader,
            title="Reader path from benchmark to extensive-margin reversal",
            summary="A two-state DAG that foregrounds intuition before the theorem.",
            created_at=created_at,
        )
        reader_ref = eref(reader_entity)

        def layer(content: str, *refs: object) -> a.LayerContract:
            return a.LayerContract(
                applicability="applicable", content=content, source_refs=refs
            )

        def element(content: str, *refs: object) -> a.ContractElement:
            return a.ContractElement(content=content, source_refs=refs)

        packet = a.ResultPacket(
            packet_id="packet.headline_reversal",
            claim_projection_id=projection.projection_id,
            claim_graph_ref=package_payload.claim_graph_ref,
            claim_id=headline.claim_id,
            primary_archetype=headline.archetype,
            question=layer(
                "Can more precise information lower realized accuracy once its use is endogenous?",
                package_payload.question_ref,
            ),
            pre_result_expectation=a.LayerContract(
                applicability="not_applicable",
                not_applicable_reason="The benchmark layer already records the reader's prior expectation.",
            ),
            formal_statement_and_scope=layer(
                headline.formal_statement, package_payload.claim_graph_ref
            ),
            economic_translation=layer(
                headline.semantic_translation,
                package_payload.economic_argument_graph_ref,
            ),
            archetype_explanation=layer(
                "Direct precision gains compete with a precision-linked processing cost; their threshold ordering creates the reversal regime.",
                package_payload.economic_argument_graph_ref,
            ),
            boundary=layer(
                "Tie-breaking changes endpoint inclusion, while a common processing cost eliminates the strict reversal.",
                package_payload.example_suite_ref,
            ),
            proof_roadmap=layer(
                "Factor processing surplus, order the two thresholds, and compare realized outcomes across participation regimes.",
                package_payload.verification_bundle_ref,
            ),
            consequence=layer(
                "Signal quality cannot be ranked independently of information uptake.",
                package_payload.result_portfolio_ref,
            ),
            archetype_module=a.ComparativeStaticsThresholdModule(
                perturbation=element(
                    "Raise signal precision from ell to h.", package_payload.formal_model_ref
                ),
                competing_effects=element(
                    "Conditional accuracy rises, but processing becomes more costly.",
                    package_payload.economic_argument_graph_ref,
                ),
                monotonicity_domain=element(
                    headline.domain, package_payload.claim_graph_ref
                ),
                threshold_or_regime_logic=element(
                    "The high-precision processing threshold lies below the low-precision threshold.",
                    package_payload.verification_bundle_ref,
                ),
                reversal_or_boundary_witness=element(
                    "Only the coarse signal is processed inside the exact interval.",
                    package_payload.example_suite_ref,
                ),
            ),
        )
        assumption_map = t.parse_theory_entity(
            self._entity_at(before, package_payload.assumption_map_ref)
        )
        assert isinstance(assumption_map, t.AssumptionMap)
        assumption_by_id = {
            item.assumption_id: (index, item)
            for index, item in enumerate(assumption_map.assumptions)
        }
        assumption_contracts = tuple(
            a.AssumptionContract(
                assumption_id=assumption_id,
                formal_source=self._facet_ref(
                    before,
                    package_payload.assumption_map_ref,
                    facet="formal",
                    field_path=f"/payload/assumptions/{assumption_by_id[assumption_id][0]}/exact_content",
                ),
                economic_content=assumption_by_id[
                    assumption_id
                ][1].economic_interpretation,
                supported_claim_ids=(headline.claim_id,),
                proof_steps=(
                    "It enters the threshold factorization and the exhaustive participation-regime comparison.",
                ),
                foundation=assumption_by_id[assumption_id][1].foundation,
                satisfying_example_refs=(package_payload.example_suite_ref,),
                failure_without=assumption_by_id[assumption_id][1].scope_cost,
                weaker_condition_status="No weaker condition is asserted by the accepted package.",
                first_needed_section_id=section.section_id,
            )
            for assumption_id in headline.assumption_ids
        )
        contracts = a.ResultContractSet(
            paper_ir_ref=paper_ref,
            reader_path_ref=reader_ref,
            claim_graph_ref=package_payload.claim_graph_ref,
            assumption_map_ref=package_payload.assumption_map_ref,
            economic_argument_graph_ref=package_payload.economic_argument_graph_ref,
            example_suite_ref=package_payload.example_suite_ref,
            verification_bundle_ref=package_payload.verification_bundle_ref,
            result_packets=(packet,),
            assumption_contracts=assumption_contracts,
            proof_roadmaps=(
                a.ProofRoadmapContract(
                    roadmap_id="roadmap.headline_reversal",
                    claim_id=headline.claim_id,
                    object_constructed_or_compared="The processing decisions and realized accuracies at ell and h.",
                    key_decomposition_or_monotonicity_step="Write net value as x(1/2-kappa x) and order 1/(2h) below 1/(2ell).",
                    assumption_roles=(
                        "Indivisible processing creates the extensive margin.",
                        "Precision-linked cost makes the two thresholds differ.",
                    ),
                    main_technical_obstacle="Track endpoint inclusion under the exact tie rule.",
                    method_or_certificate="Analytic threshold factorization and exhaustive regime comparison.",
                    scope_not_established="No welfare ranking or divisible-attention extension is established.",
                    proof_refs=(package_payload.verification_bundle_ref,),
                ),
            ),
            built_at=created_at,
        )
        contracts_entity = self._authoring_entity(
            "contracts.phase3.attention_precision",
            contracts,
            title="Result and proof-roadmap contracts",
            summary="Every prose layer is bound to exact scientific evidence.",
            created_at=created_at,
        )
        contracts_ref = eref(contracts_entity)

        assignment_specs = (
            (
                "formal_fidelity",
                FORMAL_CRITIC,
                (
                    a.InformationGrant(
                        information_kind="formal_claim",
                        source_refs=(package_payload.claim_graph_ref,),
                        description="Exact theorem statement, scope, and assumptions.",
                    ),
                    a.InformationGrant(
                        information_kind="paper_ir_contract",
                        source_refs=(paper_ref,),
                        description="The exact wording-strength contract.",
                    ),
                ),
            ),
            (
                "economic_reader",
                ECONOMIC_CRITIC,
                (
                    a.InformationGrant(
                        information_kind="economic_argument",
                        source_refs=(package_payload.economic_argument_graph_ref,),
                        description="The causal economic argument and rival mechanism.",
                    ),
                    a.InformationGrant(
                        information_kind="examples",
                        source_refs=(package_payload.example_suite_ref,),
                        description="Diagnostic examples and ablation evidence.",
                    ),
                ),
            ),
            (
                "cold_reader",
                COLD_READER,
                (
                    a.InformationGrant(
                        information_kind="reader_background",
                        description="Only ordinary graduate microeconomic theory background.",
                    ),
                    a.InformationGrant(
                        information_kind="transfer_objective",
                        description="Apply the competing-forces logic to a nearby cost specification.",
                    ),
                ),
            ),
        )
        assignments: list[EntityVersion] = []
        for role, actor, grants in assignment_specs:
            draft = a.CriticAssignment(
                assignment_id=f"assignment.phase3.{role}",
                role=role,  # type: ignore[arg-type]
                paper_ir_ref=paper_ref,
                reader_path_ref=reader_ref,
                result_contract_set_ref=contracts_ref,
                assigned_actor=actor,
                canonical_writer=WRITER,
                probe_designer=PROBE_DESIGNER if role == "cold_reader" else None,
                adjudicator=PROBE_ADJUDICATOR if role == "cold_reader" else None,
                allowed_information=grants,
                forbidden_context=(
                    "No hidden probes or answer key; no other critic report or writer rationale."
                    if role == "cold_reader"
                    else "No other critic report and no hidden evaluation material."
                ,),
                transfer_objective=(
                    "Predict whether the reversal survives when the precision-linked cost is weakened."
                    if role == "cold_reader"
                    else None
                ),
                sealed_context_hash="0" * 64,
                sealed_at=created_at,
            )
            assignment = self._seal_assignment(draft)
            assignments.append(
                self._authoring_entity(
                    f"assignment.phase3.{role}",
                    assignment,
                    title=f"Isolated {role} critic assignment",
                    summary="A sealed role-specific information contract.",
                    created_at=created_at,
                )
            )

        outputs = (
            profile_entity,
            paper_entity,
            reader_entity,
            contracts_entity,
            *assignments,
        )
        relations = (
            self._relation(
                before,
                relation_id="relation.phase3.package.projects.paper",
                relation_type="projects",
                source=eref(package),
                target=paper_ref,
                created_at=created_at,
                output_entities=outputs,
            ),
            self._relation(
                before,
                relation_id="relation.phase3.profile.governs.paper",
                relation_type="governs",
                source=profile_ref,
                target=paper_ref,
                created_at=created_at,
                output_entities=outputs,
            ),
            self._relation(
                before,
                relation_id="relation.phase3.paper.projects.reader",
                relation_type="projects",
                source=paper_ref,
                target=reader_ref,
                created_at=created_at,
                output_entities=outputs,
            ),
            self._relation(
                before,
                relation_id="relation.phase3.paper.projects.contracts",
                relation_type="projects",
                source=paper_ref,
                target=contracts_ref,
                created_at=created_at,
                output_entities=outputs,
            ),
            self._relation(
                before,
                relation_id="relation.phase3.assurance.validates.paper",
                relation_type="validates",
                source=eref(assurance),
                target=paper_ref,
                created_at=created_at,
                output_entities=outputs,
            ),
            *(
                self._relation(
                    before,
                    relation_id=f"relation.phase3.paper.assigns.{index}",
                    relation_type="assigns",
                    source=paper_ref,
                    target=eref(assignment),
                    created_at=created_at,
                    output_entities=outputs,
                )
                for index, assignment in enumerate(assignments, start=1)
            ),
        )
        authority = (*decision_refs, g4_ref, g5_ref)
        self._commit_started_v3(
            before,
            run,
            outputs=outputs,
            relations=relations,
            artifacts=((profile_registration, profile_bytes),),
            evidence_refs=(eref(package), eref(assurance), *authority),
            authority_basis=tuple(item.decision_id for item in authority),
            created_at=created_at,
        )
        return (
            profile_entity,
            paper_entity,
            reader_entity,
            contracts_entity,
            tuple(assignments),
        )

    def _compose_unit(
        self,
        *,
        package: EntityVersion,
        assurance: EntityVersion,
        profile: EntityVersion,
        paper: EntityVersion,
        reader: EntityVersion,
        contracts: EntityVersion,
        generation: int,
        revised: bool,
        created_at: str,
        previous: EntityVersion | None = None,
        closure: EntityVersion | None = None,
        brief: EntityVersion | None = None,
    ) -> tuple[EntityVersion, str]:
        paper_payload = a.parse_authoring_entity(paper)
        contracts_payload = a.parse_authoring_entity(contracts)
        profile_payload = a.parse_authoring_entity(profile)
        assert isinstance(paper_payload, a.PaperIR)
        assert isinstance(contracts_payload, a.ResultContractSet)
        assert isinstance(profile_payload, a.ResolvedProfileManifest)
        projection = paper_payload.claim_projections[0]

        formal_text = projection.formal_statement
        translation_text = (
            "Economically, the comparison concerns realized accuracy after the receiver decides whether the signal is worth using."
        )
        if revised:
            mechanism_text = (
                "Two forces move in opposite directions. Greater precision improves accuracy conditional on processing, but it also raises the precision-linked processing cost. The affected margin is therefore the receiver's discrete decision to use information. The reversal appears only when the cost increase moves the precise signal below its participation threshold while the coarse signal remains above its own threshold."
            )
            example_text = (
                "The registered separating case places the cost strictly between the two participation thresholds: the receiver processes the coarse signal and ignores the precise signal. Holding the processing decision fixed removes this ranking, which identifies uptake rather than conditional informativeness as the operative channel."
            )
            boundary_text = (
                "The conclusion is local to that threshold interval. At an endpoint, the stated tie rule determines inclusion; with a common processing cost, the two thresholds no longer separate in the required direction and the strict reversal disappears."
            )
        else:
            mechanism_text = (
                "Precision changes both conditional accuracy and the processing decision. A threshold comparison creates a regime in which the two signals are treated differently, so realized accuracy need not inherit the conditional ranking."
            )
            example_text = (
                "One registered parameter case places the two signals in different processing regimes and displays the reversal in realized outcomes."
            )
            boundary_text = (
                "The endpoint depends on the tie convention, and changing the cost specification can eliminate the strict reversal."
            )
        assumption_text = (
            "Indivisible processing creates the extensive margin, and the precision-linked cost makes the two participation thresholds differ; these assumptions are used in the threshold factorization rather than added for notation."
        )
        proof_text = (
            "For the proof, factor net processing value, solve and order the two thresholds, and then compare realized outcomes in every participation regime, including the tie boundary."
        )
        consequence_text = (
            "The result changes the relevant comparison: information quality cannot be ranked independently of whether the receiver chooses to use the information."
        )
        rows = (
            ("assertion.formal", "formal_statement", formal_text),
            ("assertion.translation", "economic_translation", translation_text),
            (
                "assertion.mechanism",
                "mechanism_or_conceptual_explanation",
                mechanism_text,
            ),
            ("assertion.example", "example_or_witness", example_text),
            ("assertion.assumptions", "assumption_interpretation", assumption_text),
            ("assertion.boundary", "boundary", boundary_text),
            ("assertion.proof", "proof_roadmap", proof_text),
            ("assertion.consequence", "consequence", consequence_text),
        )
        text = "\n\n".join(item[2] for item in rows)
        data = text.encode("utf-8")
        superseded_artifact = None
        if previous is not None:
            previous_payload = a.parse_authoring_entity(previous)
            assert isinstance(previous_payload, a.ManuscriptUnit)
            superseded_artifact = ArtifactVersionRef(
                artifact_id=previous_payload.manuscript_artifact_ref.artifact_id,
                version=previous_payload.manuscript_artifact_ref.version,
            )
        registration, manuscript_ref, _ = self._registered_artifact(
            "artifact.phase3.manuscript.main_result",
            data,
            logical_name=f"Phase 3 manuscript generation {generation}",
            media_type="text/plain; charset=utf-8",
            created_at=created_at,
            privacy="restricted" if revised else "project_private",
            access_compartments=(
                "cold_reader",
                "cold_reader_evaluation",
                "project_research",
            )
            if revised
            else ("project_research",),
            version=generation,
            supersedes=superseded_artifact,
        )
        focus = [
            eref(package),
            eref(assurance),
            eref(profile),
            eref(paper),
            eref(reader),
            eref(contracts),
        ]
        if previous is not None:
            assert closure is not None and brief is not None
            focus.extend((eref(previous), eref(closure), eref(brief)))
        compartments = (
            (
                "cold_reader",
                "cold_reader_evaluation",
                "project_research",
            )
            if revised
            else ("project_research",)
        )
        privacy = "restricted" if revised else "project_private"
        before, run = self._begin_v3(
            route_id="compose.manuscript_unit",
            actor=WRITER,
            purpose="research_authoring",
            focus_refs=tuple(focus),
            created_at=created_at,
            compartments=compartments,
            privacy_clearance=privacy,
        )
        packet = read_compiled_context(self.layout, run.route_run_id)[
            "phase3_role_packet"
        ]
        source_map = {
            "formal_statement": (projection.formal_statement_source,),
            "economic_translation": (projection.translation_source,),
            "mechanism_or_conceptual_explanation": (projection.translation_source,),
            "example_or_witness": (projection.translation_source,),
            "assumption_interpretation": (projection.assumption_source_refs[0],),
            "boundary": (projection.scope_source,),
            "proof_roadmap": (projection.formal_statement_source,),
            "consequence": (projection.translation_source,),
        }
        support_map = {
            "formal_statement": (contracts_payload.verification_bundle_ref,),
            "economic_translation": (contracts_payload.economic_argument_graph_ref,),
            "mechanism_or_conceptual_explanation": (
                contracts_payload.economic_argument_graph_ref,
            ),
            "example_or_witness": (contracts_payload.example_suite_ref,),
            "assumption_interpretation": (contracts_payload.assumption_map_ref,),
            "boundary": (contracts_payload.example_suite_ref,),
            "proof_roadmap": (contracts_payload.verification_bundle_ref,),
            "consequence": (
                t.parse_theory_entity(package).result_portfolio_ref,
            ),
        }
        presentation_map = {
            "formal_statement": "theorem_statement",
            "economic_translation": "economic_interpretation",
            "mechanism_or_conceptual_explanation": "mechanism_explanation",
            "example_or_witness": "evidence_description",
            "assumption_interpretation": "economic_interpretation",
            "boundary": "evidence_description",
            "proof_roadmap": "evidence_description",
            "consequence": "consequence",
        }
        spans: list[a.ConsequentialSpan] = []
        cursor = 0
        for assertion_id, role, exact_text in rows:
            start = text.index(exact_text, cursor)
            end = start + len(exact_text)
            cursor = end
            spans.append(
                a.ConsequentialSpan(
                    assertion_id=assertion_id,
                    role=role,  # type: ignore[arg-type]
                    claim_projection_id=projection.projection_id,
                    claim_graph_ref=projection.claim_graph_ref,
                    claim_id=projection.claim_id,
                    source_fields=source_map[role],
                    scope=projection.scope,
                    assumption_ids=projection.assumption_ids,
                    support_refs=support_map[role],
                    location=a.ManuscriptLocation(start_offset=start, end_offset=end),
                    text_hash=sha256_digest(exact_text.encode("utf-8")),
                    wording_strength=(
                        "exact" if role == "formal_statement" else "entailed_weaker"
                    ),
                    presentation=presentation_map[role],  # type: ignore[arg-type]
                )
            )
        previous_payload = (
            a.parse_authoring_entity(previous) if previous is not None else None
        )
        payload = a.ManuscriptUnit(
            unit_id="unit.phase3.main_result",
            paper_ir_ref=eref(paper),
            reader_path_ref=eref(reader),
            result_contract_set_ref=eref(contracts),
            section_contract_id="section.main_result",
            manuscript_artifact_ref=manuscript_ref,
            source_state_revision=before.head,
            canonical_writer=WRITER,
            writer_role_packet_hash=sha256_digest(canonical_json_bytes(packet)),
            writer_output_hash=manuscript_ref.content_hash,
            integration_generation=generation,
            previous_manuscript_unit_ref=eref(previous) if previous is not None else None,
            previous_manuscript_artifact_ref=(
                previous_payload.manuscript_artifact_ref
                if isinstance(previous_payload, a.ManuscriptUnit)
                else None
            ),
            revision_brief_ref=eref(brief) if brief is not None else None,
            spans=tuple(spans),
            terminology=(
                a.TerminologyRealization(
                    object_id="object.processing_decision",
                    realized_name="processing decision",
                    formal_symbol="d(x)",
                    first_use_assertion_id="assertion.translation",
                ),
            ),
            composed_at=created_at,
        )
        entity = self._authoring_entity(
            "manuscript.phase3.attention_precision",
            payload,
            title="Integrated main-result manuscript unit",
            summary="A traced theorem, mechanism, diagnostic example, boundary, and proof roadmap.",
            created_at=created_at,
            artifact_refs=(
                manuscript_ref,
                *(
                    (previous_payload.manuscript_artifact_ref,)
                    if isinstance(previous_payload, a.ManuscriptUnit)
                    else ()
                ),
            ),
            version=generation,
            supersedes=eref(previous) if previous is not None else None,
            privacy=privacy,
            access_compartments=compartments,
        )
        unit_ref = eref(entity)
        relations: list[RelationVersion] = []
        for index, source_ref in enumerate((eref(paper), eref(reader), eref(contracts))):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase3.unit.{generation}.design.{index}",
                    relation_type="depends_on",
                    source=source_ref,
                    target=unit_ref,
                    created_at=created_at,
                    output_entities=(entity,),
                    privacy=privacy,
                    access_compartments=compartments,
                )
            )
        for span_index, span in enumerate(spans):
            for source_index, source_ref in enumerate(span.source_fields):
                relations.append(
                    self._relation(
                        before,
                        relation_id=f"relation.phase3.unit.{generation}.span.{span_index}.{source_index}",
                        relation_type="realizes",
                        source=EntityVersionRef(
                            entity_id=source_ref.entity_id,
                            version=source_ref.version,
                        ),
                        target=unit_ref,
                        created_at=created_at,
                        source_field=source_ref,
                        target_path=f"/payload/spans/{span_index}",
                        target_facet="terminology_presentation",
                        output_entities=(entity,),
                        privacy=privacy,
                        access_compartments=compartments,
                    )
                )
        authority_refs = (
            profile_payload.theory_mode_decision_ref,
            profile_payload.ambition_decision_ref,
            profile_payload.g4_decision_ref,
            profile_payload.audience_decision_ref,
            paper_payload.g5_decision_ref,
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=tuple(relations),
            artifacts=((registration, data),),
            evidence_refs=tuple(focus) + tuple(authority_refs),
            authority_basis=tuple(item.decision_id for item in authority_refs),
            created_at=created_at,
            privacy=privacy,
            access_compartments=compartments,
        )
        return entity, text

    def _review_unit(
        self,
        *,
        unit: EntityVersion,
        paper: EntityVersion,
        contracts: EntityVersion,
        assignment: EntityVersion,
        generation: int,
        economic_pass: bool,
        created_at: str,
    ) -> tuple[EntityVersion, tuple[EntityVersion, ...]]:
        unit_payload = a.parse_authoring_entity(unit)
        assignment_payload = a.parse_authoring_entity(assignment)
        contracts_payload = a.parse_authoring_entity(contracts)
        assert isinstance(unit_payload, a.ManuscriptUnit)
        assert isinstance(assignment_payload, a.CriticAssignment)
        assert isinstance(contracts_payload, a.ResultContractSet)
        role = assignment_payload.role
        self.assertIn(role, {"formal_fidelity", "economic_reader"})
        actor = assignment_payload.assigned_actor
        compartments = unit.access_compartments
        privacy = unit.privacy
        before, run = self._begin_v3(
            route_id="review.manuscript_unit",
            actor=actor,
            purpose="research_review",
            focus_refs=(eref(assignment), eref(unit), eref(paper), eref(contracts)),
            created_at=created_at,
            compartments=compartments,
            privacy_clearance=privacy,
        )
        bindings = transaction_bindings(self.layout, run.route_run_id)
        findings: list[EntityVersion] = []
        if role == "formal_fidelity":
            checks = tuple(
                a.EntailmentCheck(
                    assertion_id=span.assertion_id,
                    scope_relation="equal",
                    conclusion_relation=(
                        "equivalent"
                        if span.wording_strength == "exact"
                        else "weaker"
                    ),
                    assumptions_preserved=True,
                    source_refs=(span.claim_graph_ref,),
                    outcome="passed",
                    rationale="The exact span remains within the projected claim, scope, and assumptions.",
                )
                for span in unit_payload.spans
            )
            assessment: a.ReviewAssessment = a.FormalFidelityAssessment(
                theorem_statement_exact=True,
                scope_preserved=True,
                assumptions_preserved=True,
                proof_language_honest=True,
                numerical_evidence_bounded=True,
                entailment_checks=checks,
            )
        else:
            assessment = a.EconomicReaderAssessment(
                question_and_benchmark_reconstructible=True,
                explanation_is_not_restatement=True,
                mechanism_or_conceptual_logic_reconstructible=True,
                diagnostic_example_or_witness_present=True,
                boundary_is_economically_interpretable=economic_pass,
                reconstructions=(a.EconomicReconstruction(
                    claim_projection_id="projection.headline_reversal",
                    claim_id="claim.headline_reversal",
                    result_packet_id="packet.headline_reversal",
                    question_and_benchmark="The question is whether greater precision still improves realized accuracy once information use is endogenous; the fixed-use benchmark says yes.",
                    operative_force="A precision-linked processing cost rises against the conditional accuracy benefit created by greater signal precision.",
                    affected_margin="The affected margin is the receiver's discrete information-use decision, not accuracy conditional on already processing.",
                    serious_rival_and_separator="The serious rival is the direct conditional accuracy gain; the separating threshold case holds that gain but changes uptake across signals.",
                    mechanism_steps=(
                        "Greater precision first raises the receiver's accuracy conditional on processing the available signal.",
                        "The same precision change raises processing cost and shifts the receiver's discrete participation threshold.",
                        "When cost lies between thresholds, coarse information is used while precise information is ignored, reversing realized accuracy.",
                    ),
                    mechanism_assertion_ids=("assertion.mechanism",),
                    diagnostic_assertion_ids=("assertion.example",),
                    boundary_assertion_ids=("assertion.boundary",),
                    near_transfer_prediction="Weakening the precision-linked cost closes the threshold gap, so the reversal shrinks and disappears once uptake no longer differs.",
                    explanatory_delta_from_formal_statement="Precision-linked processing costs oppose conditional accuracy gains at the receiver's discrete information-use margin; their threshold ordering separates used coarse information from ignored precise information.",
                    evidence_refs=(eref(unit), unit_payload.manuscript_artifact_ref),
                ),),
            )
            if not economic_pass:
                finding_ref = EntityVersionRef(
                    entity_id=f"finding.phase3.economic.{generation}", version=1
                )
                finding = a.ReviewFinding(
                    finding_id=f"finding.economic.boundary.{generation}",
                    assignment_ref=eref(assignment),
                    manuscript_unit_ref=eref(unit),
                    reviewed_artifact_ref=unit_payload.manuscript_artifact_ref,
                    role="economic_reader",
                    critic=actor,
                    category="boundary",
                    severity="error",
                    assertion_ids=(
                        "assertion.mechanism",
                        "assertion.example",
                        "assertion.boundary",
                    ),
                    evidence_refs=(eref(unit), unit_payload.manuscript_artifact_ref),
                    summary="The first draft names the threshold channel but does not fully separate the rival conditional-accuracy force or show why the boundary kills the reversal.",
                    recommended_repair="Expand the competing forces, use the registered separating case as an ablation, and state the common-cost failure boundary explicitly.",
                    blocking=True,
                    reported_at=created_at,
                )
                findings.append(
                    self._authoring_entity(
                        finding_ref.entity_id,
                        finding,
                        title="Blocking economic-explanation finding",
                        summary="The mechanism and boundary require a decision-complete repair.",
                        created_at=created_at,
                        artifact_refs=(unit_payload.manuscript_artifact_ref,),
                        privacy=privacy,
                        access_compartments=compartments,
                    )
                )
        review_ref = EntityVersionRef(
            entity_id=f"review.phase3.{role}.{generation}", version=1
        )
        review = a.ReviewRecord(
            assignment_ref=eref(assignment),
            manuscript_unit_ref=eref(unit),
            reviewed_artifact_ref=unit_payload.manuscript_artifact_ref,
            role=role,
            reviewer=actor,
            canonical_writer=WRITER,
            context_hash=bindings["compiled_context_hash"],
            assessment=assessment,
            finding_refs=tuple(eref(item) for item in findings),
            reviewed_at=created_at,
        )
        review_entity = self._authoring_entity(
            review_ref.entity_id,
            review,
            title=f"Independent {role} review generation {generation}",
            summary="An immutable role-specific review of the exact manuscript bytes.",
            created_at=created_at,
            artifact_refs=(unit_payload.manuscript_artifact_ref,),
            privacy=privacy,
            access_compartments=compartments,
        )
        outputs = (*findings, review_entity)
        relations: list[RelationVersion] = []
        for index, finding in enumerate(findings):
            relations.append(
                self._relation(
                    before,
                    relation_id=f"relation.phase3.review.{role}.{generation}.finding.{index}",
                    relation_type="reviews",
                    source=eref(unit),
                    target=eref(finding),
                    created_at=created_at,
                    output_entities=outputs,
                    privacy=privacy,
                    access_compartments=compartments,
                )
            )
        relations.append(
            self._relation(
                before,
                relation_id=f"relation.phase3.review.{role}.{generation}.record",
                relation_type="reviews",
                source=eref(unit),
                target=eref(review_entity),
                created_at=created_at,
                output_entities=outputs,
                privacy=privacy,
                access_compartments=compartments,
            )
        )
        relations.append(
            self._relation(
                before,
                relation_id=f"relation.phase3.review.{role}.{generation}.assignment",
                relation_type="depends_on",
                source=eref(assignment),
                target=eref(review_entity),
                created_at=created_at,
                output_entities=outputs,
                privacy=privacy,
                access_compartments=compartments,
            )
        )
        self._commit_started_v3(
            before,
            run,
            outputs=outputs,
            relations=tuple(relations),
            evidence_refs=(
                eref(assignment),
                eref(unit),
                eref(paper),
                eref(contracts),
                unit_payload.manuscript_artifact_ref,
            ),
            created_at=created_at,
            privacy=privacy,
            access_compartments=compartments,
        )
        return review_entity, tuple(findings)

    def _prepare_reader_probe(
        self,
        *,
        assignment: EntityVersion,
        unit: EntityVersion,
        reader: EntityVersion,
        generation: int,
        created_at: str,
    ) -> EntityVersion:
        assignment_payload = a.parse_authoring_entity(assignment)
        unit_payload = a.parse_authoring_entity(unit)
        assert isinstance(assignment_payload, a.CriticAssignment)
        assert isinstance(unit_payload, a.ManuscriptUnit)
        output_compartments = tuple(
            sorted({*unit.access_compartments, "cold_reader"})
        )
        key_compartments = tuple(
            sorted({*output_compartments, "cold_reader_evaluation"})
        )
        probe_ref = EntityVersionRef(
            entity_id=f"probe_set.phase3.{generation}", version=1
        )
        prompt_texts = {
            "question_benchmark_retell": "State the paper's economic question and the fixed-processing benchmark in your own words.",
            "exact_scope_recovery": "Recover the exact maintained domain and say what conclusion the theorem does not establish.",
            "assumption_role_recovery": "Explain why indivisible processing and the precision-linked cost are operative rather than cosmetic.",
            "boundary_discrimination": "Distinguish the strict reversal interval from its tie endpoints and the common-cost failure case.",
            "near_transfer": "Predict what happens to the reversal when the precision-linked part of processing cost is weakened.",
        }
        prompts = tuple(
            ReaderProbePrompt(
                probe_id=f"probe.{generation}.{kind}",
                kind=kind,  # type: ignore[arg-type]
                prompt=prompt_texts[kind],
                prompt_hash=sha256_digest(prompt_texts[kind].encode("utf-8")),
                target_assertion_ids={
                    "question_benchmark_retell": ("assertion.translation",),
                    "exact_scope_recovery": ("assertion.formal", "assertion.boundary"),
                    "assumption_role_recovery": ("assertion.assumptions",),
                    "boundary_discrimination": ("assertion.boundary",),
                    "near_transfer": ("assertion.mechanism", "assertion.boundary"),
                }[kind],
                target_contract_ids=("packet.headline_reversal",),
            )
            for kind in a.READER_PROBE_KIND_ORDER
        )
        criteria = tuple(
            ReaderAnswerCriterion(
                probe_id=item.probe_id,
                kind=item.kind,
                criterion=(
                    f"A passing {item.kind} answer must recover the exact economic distinction requested without expanding the theorem's scope."
                ),
                criterion_hash=sha256_digest(
                    f"A passing {item.kind} answer must recover the exact economic distinction requested without expanding the theorem's scope.".encode(
                        "utf-8"
                    )
                ),
                required_content=(
                    "Name the relevant force, margin, scope, or boundary precisely.",
                    "Do not replace the economic comparison with a theorem paraphrase.",
                ),
                failure_signals=("Claims welfare or universal superiority.",),
            )
            for item in prompts
        )
        probe_artifact = ReaderProbeArtifact(
            assignment_ref=eref(assignment),
            manuscript_unit_ref=eref(unit),
            frozen_manuscript_artifact_ref=unit_payload.manuscript_artifact_ref,
            respondent=COLD_READER,
            transfer_objective=assignment_payload.transfer_objective,
            probes=prompts,
        )
        key_artifact = ReaderAnswerKeyArtifact(
            assignment_ref=eref(assignment),
            manuscript_unit_ref=eref(unit),
            frozen_manuscript_artifact_ref=unit_payload.manuscript_artifact_ref,
            adjudicator=PROBE_ADJUDICATOR,
            criteria=criteria,
        )
        probe_bytes = canonical_json_bytes(probe_artifact)
        key_bytes = canonical_json_bytes(key_artifact)
        probe_registration, probe_artifact_ref, _ = self._registered_artifact(
            f"artifact.phase3.probes.{generation}",
            probe_bytes,
            logical_name=f"Cold-reader probes generation {generation}",
            media_type="application/json",
            created_at=created_at,
            privacy="restricted",
            access_compartments=output_compartments,
        )
        key_registration, key_ref, _ = self._registered_artifact(
            f"artifact.phase3.answer_key.{generation}",
            key_bytes,
            logical_name=f"Sealed cold-reader answer key generation {generation}",
            media_type="application/json",
            created_at=created_at,
            privacy="restricted",
            access_compartments=key_compartments,
        )
        before, run = self._begin_v3(
            route_id="prepare.reader_probe",
            actor=PROBE_DESIGNER,
            purpose="reader_evaluation_preparation",
            focus_refs=(eref(assignment), eref(unit), eref(reader)),
            created_at=created_at,
            compartments=key_compartments,
            privacy_clearance=unit.privacy,
        )
        bindings = transaction_bindings(self.layout, run.route_run_id)
        payload = a.ReaderProbeSet(
            assignment_ref=eref(assignment),
            manuscript_unit_ref=eref(unit),
            frozen_manuscript_artifact_ref=unit_payload.manuscript_artifact_ref,
            probe_designer=PROBE_DESIGNER,
            respondent=COLD_READER,
            adjudicator=PROBE_ADJUDICATOR,
            canonical_writer=WRITER,
            transfer_objective=assignment_payload.transfer_objective,
            probes=tuple(
                a.ReaderProbeDescriptor(
                    probe_id=item.probe_id,
                    kind=item.kind,
                    prompt_hash=item.prompt_hash,
                    target_assertion_ids=item.target_assertion_ids,
                    target_contract_ids=item.target_contract_ids,
                )
                for item in prompts
            ),
            probe_artifact_ref=probe_artifact_ref,
            answer_key_artifact_ref=key_ref,
            route_run_id=run.route_run_id,
            context_manifest_hash=bindings["context_manifest_hash"],
            sealed_at=created_at,
        )
        entity = self._authoring_entity(
            probe_ref.entity_id,
            payload,
            title=f"Sealed reader probes generation {generation}",
            summary="Five post-freeze retell, scope, assumption, boundary, and transfer tests.",
            created_at=created_at,
            artifact_refs=(
                unit_payload.manuscript_artifact_ref,
                probe_artifact_ref,
                key_ref,
            ),
            privacy="restricted",
            access_compartments=key_compartments,
        )
        relations = (
            self._relation(
                before,
                relation_id=f"relation.phase3.probe.{generation}.unit",
                relation_type="tests",
                source=eref(unit),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=key_compartments,
            ),
            self._relation(
                before,
                relation_id=f"relation.phase3.probe.{generation}.assignment",
                relation_type="depends_on",
                source=eref(assignment),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=key_compartments,
            ),
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=relations,
            artifacts=(
                (probe_registration, probe_bytes),
                (key_registration, key_bytes),
            ),
            evidence_refs=(
                eref(assignment),
                eref(unit),
                eref(reader),
                unit_payload.manuscript_artifact_ref,
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=key_compartments,
        )
        return entity

    def _answer_reader_probe(
        self,
        *,
        assignment: EntityVersion,
        unit: EntityVersion,
        probe: EntityVersion,
        generation: int,
        created_at: str,
    ) -> EntityVersion:
        probe_payload = a.parse_authoring_entity(probe)
        unit_payload = a.parse_authoring_entity(unit)
        assert isinstance(probe_payload, a.ReaderProbeSet)
        assert isinstance(unit_payload, a.ManuscriptUnit)
        output_compartments = tuple(
            sorted({*probe.access_compartments, "cold_reader_evaluation"})
        )
        responses = {
            "question_benchmark_retell": "The paper asks whether more precise information can lower realized accuracy when use is endogenous; conditional on fixed processing, precision still improves accuracy.",
            "exact_scope_recovery": "The result is confined to the maintained binary-state, indivisible-processing model and does not establish welfare or universal superiority of coarse information.",
            "assumption_role_recovery": "Indivisibility creates the uptake margin, while precision-linked cost separates the participation thresholds; without them the stated reversal channel closes.",
            "boundary_discrimination": "The strict interval keeps coarse processing above threshold and precise processing below it; endpoints follow the tie rule, and common cost removes the required separation.",
            "near_transfer": (
                "I cannot tell from the first draft whether weakening the precision-linked cost changes only the interval or eliminates the mechanism."
                if generation == 1
                else "Weakening the precision-linked cost narrows the threshold gap and therefore the reversal interval; once uptake is the same for both signals, the direct accuracy gain restores the usual ranking."
            ),
        }
        answers = tuple(
            ReaderAnswer(
                probe_id=item.probe_id,
                kind=item.kind,
                response=responses[item.kind],
                response_hash=sha256_digest(responses[item.kind].encode("utf-8")),
            )
            for item in probe_payload.probes
        )
        response_ref = EntityVersionRef(
            entity_id=f"reader_response.phase3.{generation}", version=1
        )
        response_artifact = ReaderResponseArtifact(
            probe_set_ref=eref(probe),
            manuscript_unit_ref=eref(unit),
            respondent=COLD_READER,
            answers=answers,
        )
        response_bytes = canonical_json_bytes(response_artifact)
        registration, artifact_ref, _ = self._registered_artifact(
            f"artifact.phase3.reader_response.{generation}",
            response_bytes,
            logical_name=f"Cold-reader response generation {generation}",
            media_type="application/json",
            created_at=created_at,
            privacy="restricted",
            access_compartments=output_compartments,
        )
        before, run = self._begin_v3(
            route_id="answer.reader_probe",
            actor=COLD_READER,
            purpose="cold_reader_evaluation",
            focus_refs=(eref(assignment), eref(unit), eref(probe)),
            created_at=created_at,
            compartments=output_compartments,
            privacy_clearance="restricted",
        )
        bindings = transaction_bindings(self.layout, run.route_run_id)
        payload = a.ReaderResponse(
            probe_set_ref=eref(probe),
            manuscript_unit_ref=eref(unit),
            respondent=COLD_READER,
            answered_probe_ids=tuple(item.probe_id for item in probe_payload.probes),
            response_artifact_ref=artifact_ref,
            route_run_id=run.route_run_id,
            context_manifest_hash=bindings["context_manifest_hash"],
            submitted_at=created_at,
        )
        entity = self._authoring_entity(
            response_ref.entity_id,
            payload,
            title=f"Cold-reader response generation {generation}",
            summary="Five answers produced without the sealed key.",
            created_at=created_at,
            artifact_refs=(artifact_ref,),
            privacy="restricted",
            access_compartments=output_compartments,
        )
        relations = (
            self._relation(
                before,
                relation_id=f"relation.phase3.response.{generation}.probe",
                relation_type="tests",
                source=eref(probe),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=output_compartments,
            ),
            self._relation(
                before,
                relation_id=f"relation.phase3.response.{generation}.unit",
                relation_type="depends_on",
                source=eref(unit),
                target=eref(entity),
                created_at=created_at,
                output_entities=(entity,),
                privacy="restricted",
                access_compartments=output_compartments,
            ),
        )
        self._commit_started_v3(
            before,
            run,
            outputs=(entity,),
            relations=relations,
            artifacts=((registration, response_bytes),),
            evidence_refs=(
                eref(assignment),
                eref(unit),
                eref(probe),
                probe_payload.probe_artifact_ref,
                unit_payload.manuscript_artifact_ref,
            ),
            created_at=created_at,
            privacy="restricted",
            access_compartments=output_compartments,
        )
        return entity

    def _after_fresh_g5(self, handoff: Mapping[str, object]) -> bool:
        package, _dossier, production_g5 = self._promote_production_package(handoff)
        snapshot = replay(self.layout)
        package_payload = t.parse_theory_entity(package)
        assert isinstance(package_payload, t.ValidatedArgumentPackage)
        obligation_refs = handoff["obligation_refs"]
        verification_record_refs = handoff["verification_record_refs"]
        assert isinstance(obligation_refs, tuple)
        assert isinstance(verification_record_refs, tuple)
        rederivations: list[EntityVersion] = []
        for index, (obligation_ref, verification_ref) in enumerate(
            zip(obligation_refs, verification_record_refs), start=1
        ):
            assert isinstance(obligation_ref, EntityVersionRef)
            assert isinstance(verification_ref, EntityVersionRef)
            rederivations.append(
                self._make_rederivation(
                    snapshot=replay(self.layout),
                    package_ref=eref(package),
                    claim_graph_ref=package_payload.claim_graph_ref,
                    obligation_ref=obligation_ref,
                    verification_record_ref=verification_ref,
                    formal_model_ref=package_payload.formal_model_ref,
                    assumption_map_ref=package_payload.assumption_map_ref,
                    g5_ref=DecisionVersionRef(
                        decision_id=production_g5.decision_id,
                        version=production_g5.version,
                    ),
                    rederiver=Actor(
                        kind="agent", actor_id=f"gold.phase3.rederiver.{index}"
                    ),
                    suffix=str(index),
                    created_at=_timestamp(1 + index),
                )
            )
        assurance = self._make_assurance_bundle(
            snapshot=replay(self.layout),
            package_ref=eref(package),
            claim_graph_ref=package_payload.claim_graph_ref,
            obligation_refs=obligation_refs,  # type: ignore[arg-type]
            verification_record_refs=verification_record_refs,  # type: ignore[arg-type]
            verification_bundle_ref=package_payload.verification_bundle_ref,
            formal_model_ref=package_payload.formal_model_ref,
            assumption_map_ref=package_payload.assumption_map_ref,
            rederivation_refs=tuple(eref(item) for item in rederivations),
            g5_ref=DecisionVersionRef(
                decision_id=production_g5.decision_id,
                version=production_g5.version,
            ),
            created_at=_timestamp(5),
        )
        self.assertEqual(replay(self.layout).current_entities[assurance.entity_id], 1)
        question_ref = handoff["question_ref"]
        g4 = handoff["g4"]
        assert isinstance(question_ref, EntityVersionRef)
        assert isinstance(g4, Decision)
        profile_decisions = self._commit_profile_decisions(
            package=package,
            question_ref=question_ref,
            created_at=_timestamp(6),
        )
        profile, paper, reader, contracts, assignments = self._make_authoring_design(
            package=package,
            assurance=assurance,
            production_g5=production_g5,
            profile_decisions=profile_decisions,
            g4_ref=DecisionVersionRef(decision_id=g4.decision_id, version=g4.version),
            created_at=_timestamp(9),
        )
        assignment_by_role = {
            payload.role: entity
            for entity in assignments
            if isinstance((payload := a.parse_authoring_entity(entity)), a.CriticAssignment)
        }

        first_unit, _first_text = self._compose_unit(
            package=package,
            assurance=assurance,
            profile=profile,
            paper=paper,
            reader=reader,
            contracts=contracts,
            generation=1,
            revised=False,
            created_at=_timestamp(10),
        )
        first_formal, formal_findings = self._review_unit(
            unit=first_unit,
            paper=paper,
            contracts=contracts,
            assignment=assignment_by_role["formal_fidelity"],
            generation=1,
            economic_pass=True,
            created_at=_timestamp(11),
        )
        first_economic, economic_findings = self._review_unit(
            unit=first_unit,
            paper=paper,
            contracts=contracts,
            assignment=assignment_by_role["economic_reader"],
            generation=1,
            economic_pass=False,
            created_at=_timestamp(12),
        )
        first_probe = self._prepare_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=first_unit,
            reader=reader,
            generation=1,
            created_at=_timestamp(13),
        )
        first_response = self._answer_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=first_unit,
            probe=first_probe,
            generation=1,
            created_at=_timestamp(14),
        )
        first_cold, cold_findings = self._adjudicate_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=first_unit,
            probe=first_probe,
            response=first_response,
            generation=1,
            transfer_pass=False,
            created_at=_timestamp(15),
        )
        self.assertEqual(formal_findings, ())
        blocking_findings = (*economic_findings, *cold_findings)
        first_closure, brief = self._close_reviews(
            paper=paper,
            reader=reader,
            contracts=contracts,
            assurance=assurance,
            unit=first_unit,
            formal_review=first_formal,
            economic_review=first_economic,
            cold_review=first_cold,
            findings=blocking_findings,
            generation=1,
            ready=False,
            created_at=_timestamp(16),
        )
        self.assertIsNotNone(brief)
        assert brief is not None

        revised_unit, revised_text = self._compose_unit(
            package=package,
            assurance=assurance,
            profile=profile,
            paper=paper,
            reader=reader,
            contracts=contracts,
            generation=2,
            revised=True,
            previous=first_unit,
            closure=first_closure,
            brief=brief,
            created_at=_timestamp(17),
        )
        second_formal, second_formal_findings = self._review_unit(
            unit=revised_unit,
            paper=paper,
            contracts=contracts,
            assignment=assignment_by_role["formal_fidelity"],
            generation=2,
            economic_pass=True,
            created_at=_timestamp(18),
        )
        second_economic, second_economic_findings = self._review_unit(
            unit=revised_unit,
            paper=paper,
            contracts=contracts,
            assignment=assignment_by_role["economic_reader"],
            generation=2,
            economic_pass=True,
            created_at=_timestamp(19),
        )
        second_probe = self._prepare_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=revised_unit,
            reader=reader,
            generation=2,
            created_at=_timestamp(20),
        )
        second_response = self._answer_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=revised_unit,
            probe=second_probe,
            generation=2,
            created_at=_timestamp(21),
        )
        second_cold, second_cold_findings = self._adjudicate_reader_probe(
            assignment=assignment_by_role["cold_reader"],
            unit=revised_unit,
            probe=second_probe,
            response=second_response,
            generation=2,
            transfer_pass=True,
            created_at=_timestamp(22),
        )
        self.assertFalse(
            second_formal_findings
            or second_economic_findings
            or second_cold_findings
        )
        final_closure, final_brief = self._close_reviews(
            paper=paper,
            reader=reader,
            contracts=contracts,
            assurance=assurance,
            unit=revised_unit,
            formal_review=second_formal,
            economic_review=second_economic,
            cold_review=second_cold,
            findings=(),
            generation=2,
            ready=True,
            created_at=_timestamp(23),
        )
        self.assertIsNone(final_brief)
        current = replay(self.layout)
        validate_authoring_ready(
            current, eref(final_closure), manuscript_text=revised_text
        )
        effort = self._record_human_effort(
            first_unit=first_unit,
            revised_unit=revised_unit,
            created_at=_timestamp(24),
        )
        final = replay(self.layout)
        self.assertEqual(final.current_entities[effort.entity_id], 1)
        self.assertEqual(final.current_entities[revised_unit.entity_id], 2)
        self.assertEqual(
            canonical_json_bytes(replay_at(self.layout, final.head)),
            canonical_json_bytes(final),
        )
        return True
