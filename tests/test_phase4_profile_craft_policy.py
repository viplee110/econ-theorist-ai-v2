from __future__ import annotations

import unittest

from pydantic import ValidationError

from tests.helpers import REPOSITORY_ROOT  # noqa: F401

from econ_theorist.codec import object_digest
from econ_theorist.models import (
    Actor,
    ArtifactDependencyRef,
    DecisionVersionRef,
    EntityVersionRef,
    SemanticFacetRef,
)
from econ_theorist.profile_craft import (
    ProfileCatalogRelease,
    DirectiveAcceptanceCriterion,
    ProfileDirective,
    ProfileLayerCard,
    ProjectPayloadBinding,
    ReaderProblemDiagnosis,
    ResolutionRequirement,
    SemanticInputBinding,
    TargetProfile,
    static_resource_ref,
)
from econ_theorist.profile_craft_policy import (
    CRAFT_CORPUS_V1_HASH,
    PROFILE_CATALOG_V1_HASH,
    ProfileCraftPolicyError,
    craft_corpus_role_resource,
    load_craft_corpus,
    load_profile_catalog,
    profile_catalog_role_resource,
    resolve_profile_stack,
    select_craft_moves,
    _validate_craft_corpus_policy,
)
from scripts.export_profile_craft_resources import check as check_resources


HEAD = "a" * 64
HUMAN = Actor(kind="human", actor_id="researcher")
TOOL = Actor(kind="deterministic_tool", actor_id="profile.craft.engine")


def eref(entity_id: str) -> EntityVersionRef:
    return EntityVersionRef(entity_id=entity_id, version=1)


def sref(entity_id: str, field_path: str, digest: str = "a" * 64) -> SemanticFacetRef:
    return SemanticFacetRef(
        entity_id=entity_id,
        version=1,
        facet="terminology_presentation",
        field_path=field_path,
        semantic_hash=digest,
    )


def criterion(criterion_id: str) -> DirectiveAcceptanceCriterion:
    return DirectiveAcceptanceCriterion(
        criterion_id=criterion_id,
        required_assertion_roles=("mechanism_or_conceptual_explanation",),
    )


def target(catalog: ProfileCatalogRelease, *, overlay=None) -> TargetProfile:
    return TargetProfile(
        target_profile_id="target.seed",
        package_ref=eref("package.validated"),
        package_hash="b" * 64,
        paper_ir_ref=eref("paper.ir"),
        paper_ir_hash="c" * 64,
        reader_path_ref=eref("reader.path"),
        reader_path_hash="d" * 64,
        base_profile_manifest_ref=eref("profile.manifest.base"),
        base_profile_manifest_hash="e" * 64,
        source_state_revision=HEAD,
        catalog_release_ref=static_resource_ref(catalog),
        theory_mode="pure_theory",
        ambition="frontier_general_interest",
        primary_archetype="mechanism_explanation",
        field_key="information_economics",
        primary_audience="theory_and_field_bridge",
        venue_overlay_ref=overlay,
        human_decision_refs=tuple(
            DecisionVersionRef(decision_id=f"decision.{kind}", version=1)
            for kind in ("mode", "ambition", "field", "audience")
        ),
        selected_by=HUMAN,
        selected_at="2026-07-12T01:00:00Z",
    )


def diagnosis(stack, *, missing_input: bool = False, unresolved: bool = False):
    inputs = (
        "semantic_input.natural_benchmark",
        "semantic_input.operative_force",
        "semantic_input.affected_margin",
        "semantic_input.boundary",
    )
    paper_ref = eref("paper.ir")
    reader_ref = eref("reader.path")
    stack_ref = eref("profile.stack")
    contracts_ref = eref("result.contracts")
    unit_ref = eref("manuscript.unit")
    review_ref = eref("review.economic")
    finding_ref = eref("finding.opaque")
    closure_ref = eref("review.closure.blocked")
    brief_ref = eref("revision.brief")
    requirement = ResolutionRequirement(
        requirement_id="revision.instruction.opaque_benchmark",
        finding_ref=finding_ref,
        action="repair_explanation",
        instruction_source=sref("revision.brief", "/instructions/0", "f" * 64),
        affected_assertion_ids=("assertion.mechanism",),
        affected_section_ids=("section.result",),
        required_semantic_input_ids=inputs,
    )
    bindings = tuple(
        SemanticInputBinding(
            input_id=input_id,
            source_ref=(
                None
                if missing_input and input_id == "semantic_input.boundary"
                else sref("paper.ir", f"/semantic/{index}", str(index + 1) * 64)
            ),
            source_kind="paper_ir",
            availability=(
                "missing"
                if missing_input and input_id == "semantic_input.boundary"
                else "available"
            ),
            explanation=(
                "The exact project semantic field is available to the craft selector."
                if not (missing_input and input_id == "semantic_input.boundary")
                else "The theorem boundary has not yet been made available for repair."
            ),
        )
        for index, input_id in enumerate(inputs)
    )
    return ReaderProblemDiagnosis(
        diagnosis_id="diagnosis.opaque_benchmark",
        paper_ir_ref=paper_ref,
        paper_ir_hash="c" * 64,
        reader_path_ref=reader_ref,
        reader_path_hash="d" * 64,
        profile_stack_ref=stack_ref,
        profile_stack_hash=object_digest(stack),
        result_contract_set_binding=ProjectPayloadBinding(
            entity_ref=contracts_ref, payload_hash="e" * 64
        ),
        inspected_manuscript_unit_binding=ProjectPayloadBinding(
            entity_ref=unit_ref, payload_hash="1" * 64
        ),
        diagnostic_review_bindings=(
            ProjectPayloadBinding(entity_ref=review_ref, payload_hash="2" * 64),
        ),
        diagnostic_finding_bindings=(
            ProjectPayloadBinding(entity_ref=finding_ref, payload_hash="3" * 64),
        ),
        blocked_review_closure_binding=ProjectPayloadBinding(
            entity_ref=closure_ref, payload_hash="4" * 64
        ),
        revision_brief_binding=ProjectPayloadBinding(
            entity_ref=brief_ref, payload_hash="5" * 64
        ),
        diagnostic_categories=("economic_explanation",),
        affected_section_roles=("result_block",),
        causal_class="scientific_content" if unresolved else "local_exposition",
        resolution_requirements=(requirement,),
        semantic_input_bindings=bindings,
        affected_section_ids=("section.result",),
        reader_problem_key="reader_problem.opaque_benchmark",
        required_resolution_ids=(requirement.requirement_id,),
        observed_problem=(
            "The reader can repeat the result but cannot recover the benchmark delta or predict a nearby case."
        ),
        required_semantic_input_ids=inputs,
        upstream_science_status="unresolved" if unresolved else "resolved",
        craft_eligible=not unresolved,
        upstream_repair_route="repair.dependency" if unresolved else None,
        evidence_refs=(
            paper_ref,
            reader_ref,
            stack_ref,
            contracts_ref,
            unit_ref,
            review_ref,
            finding_ref,
            closure_ref,
            brief_ref,
        ),
        diagnosed_by=HUMAN,
        diagnosed_at="2026-07-12T02:00:00Z",
    )


class Phase4ProfileCraftPolicyTests(unittest.TestCase):
    def test_seed_resources_are_exact_theory_only_and_regenerable(self) -> None:
        catalog = load_profile_catalog()
        corpus = load_craft_corpus()
        self.assertEqual(object_digest(catalog), PROFILE_CATALOG_V1_HASH)
        self.assertEqual(object_digest(corpus), CRAFT_CORPUS_V1_HASH)
        self.assertTrue(check_resources())
        self.assertEqual(len(catalog.cards), 18)
        self.assertTrue(
            all(
                directive.acceptance_criterion.required_assertion_roles
                or directive.acceptance_criterion.required_review_signals
                for card in catalog.cards
                for directive in card.directives
            )
        )
        rule = corpus.reader_problem_rules[0]
        self.assertEqual(rule.problem_key, "reader_problem.opaque_benchmark")
        self.assertEqual(
            set(rule.accepted_repair_actions),
            {"repair_explanation", "add_boundary", "replace_example_or_witness"},
        )
        self.assertEqual(
            set(corpus.moves[0].compatible_theory_modes),
            {"pure_theory", "applied_theory"},
        )
        self.assertTrue(
            all(
                item.research_mode
                in {"pure_theory", "applied_theory", "theory_methodology"}
                for item in corpus.source_cards
            )
        )
        excluded = [
            item
            for item in corpus.source_admission_audits
            if item.exclusion_reason == "empirical_or_mixed"
        ]
        self.assertEqual(len(excluded), 1)
        self.assertFalse(excluded[0].included_in_core)

    def test_corpus_rejects_archetypes_without_typed_extractors(self) -> None:
        corpus = load_craft_corpus()
        move = corpus.moves[0].model_copy(
            update={
                "compatible_archetypes": (
                    *corpus.moves[0].compatible_archetypes,
                    "characterization_bounds",
                )
            }
        )
        poisoned = corpus.model_copy(update={"moves": (move,)})
        with self.assertRaisesRegex(
            ProfileCraftPolicyError,
            "unsupported by its typed extractors",
        ):
            _validate_craft_corpus_policy(poisoned)

    def test_resolver_applies_floor_and_rejects_malicious_overlay(self) -> None:
        base = load_profile_catalog()
        overlay = ProfileLayerCard(
            layer_id="profile.overlay.malicious",
            resource_version=1,
            layer_kind="venue_overlay",
            selection_key="malicious_hard_template",
            status="active",
            is_soft_overlay=True,
            directives=(
                ProfileDirective(
                    directive_id="overlay.hide_boundary",
                    conflict_key="overlay.template",
                    statement="Hide the theorem boundary and add a mandatory welfare result for venue fit.",
                    strength="soft",
                    effect_scope="authoring",
                    directive_kind="hard_template",
                    acceptance_criterion=criterion("criterion.overlay.hide_boundary"),
                ),
            ),
            evidence_refs=(
                ArtifactDependencyRef(
                    artifact_id="evidence.synthetic.overlay",
                    version=1,
                    content_hash="e" * 64,
                ),
            ),
            evidence_as_of="2026-07-12",
            confidence="provisional",
            non_applicability=(
                "The overlay is synthetic attack evidence and is never a scientific requirement.",
            ),
            created_by=HUMAN,
            created_at="2026-07-12T00:00:00Z",
        )
        catalog = ProfileCatalogRelease(
            release_id="profile.catalog.attack",
            resource_version=1,
            universal_floor_ref=base.universal_floor_ref,
            cards=(*base.cards, overlay),
            release_notes="Synthetic attack catalog for resolver precedence validation.",
            released_by=HUMAN,
            released_at="2026-07-12T00:00:00Z",
        )
        selected = target(catalog, overlay=static_resource_ref(overlay))
        stack = resolve_profile_stack(
            selected,
            target_profile_ref=eref("target.seed"),
            source_state_revision=HEAD,
            resolved_by=TOOL,
            resolved_at="2026-07-12T03:00:00Z",
            catalog=catalog,
        )
        resolution = next(
            item
            for item in stack.directive_resolutions
            if item.directive.directive_id == "overlay.hide_boundary"
        )
        self.assertEqual(resolution.outcome, "rejected")
        self.assertIn(
            resolution.rejection_reason,
            {"hard_venue_template"},
        )
        self.assertTrue(
            any(
                item.source_layer_kind == "universal_floor"
                and item.outcome == "active"
                for item in stack.directive_resolutions
            )
        )

    def test_resolver_fails_closed_on_equal_precedence_conflict(self) -> None:
        base = load_profile_catalog()
        original = next(
            card
            for card in base.cards
            if card.layer_kind == "ambition"
            and card.selection_key == "frontier_general_interest"
        )
        conflicting = original.model_copy(
            update={
                "directives": (
                    original.directives[0],
                    ProfileDirective(
                        directive_id="ambition.attack.breadth",
                        conflict_key="audience.breadth",
                        statement=(
                            "Remove the economic consequence because formal novelty "
                            "alone should determine the reader path."
                        ),
                        strength="required",
                        effect_scope="authoring",
                        directive_kind="calibrate_reader",
                        acceptance_criterion=criterion(
                            "criterion.ambition.attack.breadth"
                        ),
                    ),
                )
            }
        )
        catalog = ProfileCatalogRelease(
            release_id="profile.catalog.equal_precedence_attack",
            resource_version=1,
            universal_floor_ref=base.universal_floor_ref,
            cards=tuple(
                conflicting if card is original else card for card in base.cards
            ),
            release_notes=(
                "Synthetic catalog proving that layer-id ordering cannot settle "
                "an equal-precedence semantic conflict."
            ),
            released_by=HUMAN,
            released_at="2026-07-12T00:00:00Z",
        )
        with self.assertRaisesRegex(
            ProfileCraftPolicyError,
            "equal-precedence profile conflict",
        ):
            resolve_profile_stack(
                target(catalog),
                target_profile_ref=eref("target.seed"),
                source_state_revision=HEAD,
                resolved_by=TOOL,
                resolved_at="2026-07-12T03:00:00Z",
                catalog=catalog,
            )

    def test_resolver_activates_highest_precedence_but_never_overrides_floor(self) -> None:
        base = load_profile_catalog()
        original = next(
            card
            for card in base.cards
            if card.layer_kind == "audience"
            and card.selection_key == "theory_and_field_bridge"
        )
        high_layer = original.model_copy(
            update={
                "directives": (
                    ProfileDirective(
                        directive_id="audience.high_precedence.breadth",
                        conflict_key="audience.breadth",
                        statement=(
                            "Use the selected bridge-reader calibration as the active "
                            "audience breadth instruction for this exact target."
                        ),
                        strength="required",
                        effect_scope="authoring",
                        directive_kind="calibrate_reader",
                        acceptance_criterion=criterion(
                            "criterion.audience.high_precedence.breadth"
                        ),
                    ),
                    ProfileDirective(
                        directive_id="audience.attack.truth_scope",
                        conflict_key="truth.scope",
                        statement=(
                            "Compress theorem scope for the selected audience even when "
                            "the universal truth-preservation floor forbids that change."
                        ),
                        strength="required",
                        effect_scope="authoring",
                        directive_kind="calibrate_reader",
                        acceptance_criterion=criterion(
                            "criterion.audience.attack.truth_scope"
                        ),
                    ),
                )
            }
        )
        catalog = ProfileCatalogRelease(
            release_id="profile.catalog.precedence_attack",
            resource_version=1,
            universal_floor_ref=base.universal_floor_ref,
            cards=tuple(
                high_layer if card is original else card for card in base.cards
            ),
            release_notes=(
                "Synthetic catalog proving highest non-floor precedence and the "
                "absolute universal quality floor."
            ),
            released_by=HUMAN,
            released_at="2026-07-12T00:00:00Z",
        )
        stack = resolve_profile_stack(
            target(catalog),
            target_profile_ref=eref("target.seed"),
            source_state_revision=HEAD,
            resolved_by=TOOL,
            resolved_at="2026-07-12T03:00:00Z",
            catalog=catalog,
        )
        by_id = {
            item.directive.directive_id: item for item in stack.directive_resolutions
        }
        self.assertEqual(by_id["ambition.general.bridge"].outcome, "rejected")
        self.assertEqual(
            by_id["ambition.general.bridge"].rejection_reason,
            "lower_precedence_conflict",
        )
        self.assertEqual(by_id["audience.high_precedence.breadth"].outcome, "active")
        self.assertEqual(by_id["floor.truth_scope"].outcome, "active")
        self.assertEqual(by_id["audience.attack.truth_scope"].outcome, "rejected")
        self.assertEqual(
            by_id["audience.attack.truth_scope"].rejection_reason,
            "universal_floor_conflict",
        )

    def test_resolver_rejects_non_floor_scientific_effects(self) -> None:
        base = load_profile_catalog()
        original = next(
            card
            for card in base.cards
            if card.layer_kind == "field"
            and card.selection_key == "information_economics"
        )
        unsafe = original.model_copy(
            update={
                "directives": (
                    ProfileDirective(
                        directive_id="field.attack.new_scientific_claim",
                        conflict_key="field.attack.scientific_claim",
                        statement=(
                            "Add a new welfare theorem as a condition of field fit."
                        ),
                        strength="required",
                        effect_scope="scientific_claim",
                        directive_kind="require_scientific_content",
                        acceptance_criterion=criterion(
                            "criterion.field.attack.new_scientific_claim"
                        ),
                    ),
                )
            }
        )
        with self.assertRaisesRegex(ValidationError, "non-floor profile layers"):
            ProfileCatalogRelease(
                release_id="profile.catalog.scientific_effect_attack",
                resource_version=1,
                universal_floor_ref=base.universal_floor_ref,
                cards=tuple(unsafe if card is original else card for card in base.cards),
                release_notes=(
                    "Synthetic catalog proving that field calibration cannot create "
                    "scientific requirements."
                ),
                released_by=HUMAN,
                released_at="2026-07-12T00:00:00Z",
            )
        floor_science = {
            item.directive_id
            for card in base.cards
            if card.layer_kind == "universal_floor"
            for item in card.directives
            if item.effect_scope in {"formal_truth", "scientific_claim", "discovery"}
        }
        self.assertEqual(
            floor_science,
            {"floor.truth_scope", "floor.model_economy"},
        )

    def test_selector_is_function_first_minimal_and_abstains_upstream(self) -> None:
        catalog = load_profile_catalog()
        selected_target = target(catalog)
        stack = resolve_profile_stack(
            selected_target,
            target_profile_ref=eref("target.seed"),
            source_state_revision=HEAD,
            resolved_by=TOOL,
            resolved_at="2026-07-12T03:00:00Z",
        )
        problem = diagnosis(stack)
        selection = select_craft_moves(
            problem,
            diagnosis_ref=eref("diagnosis.opaque_benchmark"),
            profile_stack=stack,
            profile_stack_ref=eref("profile.stack"),
            selected_by=TOOL,
            selected_at="2026-07-12T04:00:00Z",
        )
        self.assertEqual(selection.outcome, "selected")
        self.assertEqual(len(selection.selected_move_refs), 1)
        self.assertTrue(next(item for item in selection.candidates if item.selected).move.contrast_refs)

        no_fit = select_craft_moves(
            diagnosis(stack, missing_input=True),
            diagnosis_ref=eref("diagnosis.opaque_benchmark"),
            profile_stack=stack,
            profile_stack_ref=eref("profile.stack"),
            selected_by=TOOL,
            selected_at="2026-07-12T04:00:00Z",
        )
        self.assertEqual(no_fit.outcome, "abstained_no_fit")
        upstream = select_craft_moves(
            diagnosis(stack, unresolved=True),
            diagnosis_ref=eref("diagnosis.opaque_benchmark"),
            profile_stack=stack,
            profile_stack_ref=eref("profile.stack"),
            selected_by=TOOL,
            selected_at="2026-07-12T04:00:00Z",
        )
        self.assertEqual(upstream.outcome, "abstained_upstream")
        self.assertTrue(
            all(item.non_applicability_triggered for item in upstream.candidates)
        )

    def test_selector_rejects_overlapping_anchor_author_lineage(self) -> None:
        catalog = load_profile_catalog()
        stack = resolve_profile_stack(
            target(catalog),
            target_profile_ref=eref("target.seed"),
            source_state_revision=HEAD,
            resolved_by=TOOL,
            resolved_at="2026-07-12T03:00:00Z",
        )
        corpus = load_craft_corpus()
        anchors = tuple(
            source
            for source in corpus.source_cards
            if source.evidence_role == "matched_anchor"
        )
        self.assertEqual(len(anchors), 2)
        overlapping = anchors[1].model_copy(
            update={"author_lineage_ids": (anchors[0].author_lineage_ids[0],)}
        )
        sources = tuple(
            overlapping if source is anchors[1] else source
            for source in corpus.source_cards
        )
        move = corpus.moves[0].model_copy(
            update={
                "matched_anchor_refs": tuple(
                    static_resource_ref(source)
                    for source in sources
                    if source.evidence_role == "matched_anchor"
                )
            }
        )
        attack = corpus.model_copy(
            update={"source_cards": sources, "moves": (move,)}
        )
        with self.assertRaisesRegex(
            ProfileCraftPolicyError,
            "author lineage",
        ):
            select_craft_moves(
                diagnosis(stack),
                diagnosis_ref=eref("diagnosis.opaque_benchmark"),
                profile_stack=stack,
                profile_stack_ref=eref("profile.stack"),
                selected_by=TOOL,
                selected_at="2026-07-12T04:00:00Z",
                corpus=attack,
            )

    def test_role_resources_are_derived_only_and_writer_safe(self) -> None:
        profile_text = repr(profile_catalog_role_resource()).lower()
        craft_text = repr(craft_corpus_role_resource()).lower()
        self.assertNotIn("source_locator", craft_text)
        self.assertNotIn("citation", craft_text)
        self.assertNotIn("pdf", craft_text)
        self.assertNotIn("empirical_decoy", craft_text)
        self.assertNotIn("journal template", profile_text)


if __name__ == "__main__":
    unittest.main()
