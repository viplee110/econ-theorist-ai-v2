"""Render the small, copyright-safe Phase 4 seed catalogs deterministically."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from econ_theorist.codec import canonical_json_bytes  # noqa: E402
from econ_theorist.models import Actor, ArtifactDependencyRef  # noqa: E402
from econ_theorist.profile_craft import (  # noqa: E402
    CraftCorpusRelease,
    CraftMove,
    CraftSourceCard,
    DirectiveAcceptanceCriterion,
    ProfileCatalogRelease,
    ProfileDirective,
    ProfileLayerCard,
    ReaderProblemRule,
    SemanticInputSourceRule,
    SourceAdmissionAudit,
    static_resource_ref,
)


STAMP = "2026-07-12T00:00:00Z"
CURATOR = Actor(kind="human", actor_id="catalog.curator.viplee110")


def artifact(artifact_id: str, digest: str) -> ArtifactDependencyRef:
    return ArtifactDependencyRef(
        artifact_id=artifact_id,
        version=1,
        content_hash=digest,
    )


def directive(
    directive_id: str,
    conflict_key: str,
    statement: str,
    *,
    strength: str,
    effect_scope: str,
    directive_kind: str,
    non_applicability: str | None = None,
) -> ProfileDirective:
    assertion_roles: tuple[str, ...] = ()
    review_signals: tuple[str, ...] = ()
    if effect_scope == "formal_truth":
        review_signals = ("formal_fidelity",)
    elif effect_scope == "scientific_claim":
        review_signals = ("scope_and_assumptions",)
    elif effect_scope == "economic_interpretation":
        assertion_roles = ("mechanism_or_conceptual_explanation",)
    elif effect_scope == "review":
        review_signals = ("bounded_evidentiary_language",)
    elif "audience." in directive_id or "general." in directive_id:
        review_signals = ("cold_reader_transfer",)
    elif "mechanism" in directive_id or "reader_path" in directive_id:
        assertion_roles = ("mechanism_or_conceptual_explanation",)
    elif "boundary" in directive_id or "scope" in directive_id:
        assertion_roles = ("boundary",)
    elif "institution" in directive_id or "objects" in directive_id:
        assertion_roles = ("economic_translation",)
    else:
        assertion_roles = ("consequence",)
    return ProfileDirective(
        directive_id=directive_id,
        conflict_key=conflict_key,
        statement=statement,
        strength=strength,
        effect_scope=effect_scope,
        directive_kind=directive_kind,
        acceptance_criterion=DirectiveAcceptanceCriterion(
            criterion_id=f"criterion.{directive_id}",
            required_assertion_roles=assertion_roles,
            required_review_signals=review_signals,
        ),
        non_applicability=non_applicability,
    )


def layer(
    layer_id: str,
    layer_kind: str,
    selection_key: str,
    directives: tuple[ProfileDirective, ...],
) -> ProfileLayerCard:
    return ProfileLayerCard(
        layer_id=layer_id,
        resource_version=1,
        layer_kind=layer_kind,
        selection_key=selection_key,
        status="active",
        directives=directives,
        confidence="provisional",
        non_applicability=(
            "Do not apply any reader-facing calibration that changes accepted scientific content.",
        ),
        created_by=CURATOR,
        created_at=STAMP,
    )


def profile_catalog() -> ProfileCatalogRelease:
    floor = layer(
        "profile.floor.theory.v1",
        "universal_floor",
        "universal_quality_floor",
        (
            directive(
                "floor.truth_scope",
                "truth.scope",
                "Preserve exact theorem scope, assumptions, boundaries, and proof status everywhere.",
                strength="invariant",
                effect_scope="formal_truth",
                directive_kind="preserve_floor",
            ),
            directive(
                "floor.mechanism",
                "economic.mechanism",
                "Make the operative economic or conceptual force reconstructible rather than restating mathematics.",
                strength="invariant",
                effect_scope="economic_interpretation",
                directive_kind="preserve_floor",
            ),
            directive(
                "floor.model_economy",
                "scientific.model_economy",
                "Keep assumptions natural and the model no larger than the accepted contribution requires.",
                strength="invariant",
                effect_scope="scientific_claim",
                directive_kind="preserve_floor",
            ),
            directive(
                "floor.result_hierarchy",
                "authoring.result_hierarchy",
                "Expose one central result hierarchy with diagnostic examples, boundaries, and honest evidence roles.",
                strength="invariant",
                effect_scope="authoring",
                directive_kind="preserve_floor",
            ),
            directive(
                "floor.uncertainty",
                "review.uncertainty",
                "Record uncertainty, non-applicability, provenance, and reproducibility without rhetorical upgrading.",
                strength="invariant",
                effect_scope="review",
                directive_kind="preserve_floor",
            ),
        ),
    )
    pure = layer(
        "profile.mode.pure_theory.v1",
        "theory_mode",
        "pure_theory",
        (
            directive(
                "mode.pure.consequence",
                "mode.economic_consequence",
                "Explain the economic consequence, application class, or changed modeling practice without inventing welfare or policy claims.",
                strength="required",
                effect_scope="authoring",
                directive_kind="calibrate_reader",
            ),
        ),
    )
    applied = layer(
        "profile.mode.applied_theory.v1",
        "theory_mode",
        "applied_theory",
        (
            directive(
                "mode.applied.institution",
                "mode.institution_mapping",
                "Map primitives and results to the institution or design problem while excluding empirical workflow templates.",
                strength="required",
                effect_scope="authoring",
                directive_kind="calibrate_reader",
            ),
        ),
    )
    ambitions = (
        layer(
            "profile.ambition.general_interest.v1",
            "ambition",
            "frontier_general_interest",
            (
                directive(
                    "ambition.general.bridge",
                    "audience.breadth",
                    "Build a disciplined bridge from the precise theoretical advance to a broad economic question without inflating relevance.",
                    strength="required",
                    effect_scope="authoring",
                    directive_kind="calibrate_reader",
                ),
            ),
        ),
        layer(
            "profile.ambition.theory.v1",
            "ambition",
            "frontier_theory",
            (
                directive(
                    "ambition.theory.object",
                    "audience.breadth",
                    "Foreground the new theoretical object and what it changes for economic modeling practice.",
                    strength="required",
                    effect_scope="authoring",
                    directive_kind="calibrate_reader",
                ),
            ),
        ),
        layer(
            "profile.ambition.field.v1",
            "ambition",
            "field_frontier",
            (
                directive(
                    "ambition.field.delta",
                    "audience.breadth",
                    "State the exact field benchmark delta and mechanism without lowering the universal quality floor.",
                    strength="required",
                    effect_scope="authoring",
                    directive_kind="calibrate_reader",
                ),
            ),
        ),
    )
    archetype_cards = tuple(
        layer(
            f"profile.archetype.{key}.v1",
            "archetype",
            key,
            (
                directive(
                    f"archetype.{key}.reader_path",
                    "authoring.result_function",
                    f"Organize exposition around the reader function of the {key.replace('_', ' ')} result rather than a generic theorem template.",
                    strength="required",
                    effect_scope="authoring",
                    directive_kind="calibrate_reader",
                ),
            ),
        )
        for key in (
            "mechanism_explanation",
            "comparative_statics_threshold",
            "characterization_bounds",
            "robustness_invariance_equivalence",
            "design_implementation_impossibility",
            "concept_representation_foundation",
        )
    )
    field = layer(
        "profile.field.information_economics.v1",
        "field",
        "information_economics",
        (
            directive(
                "field.information.objects",
                "field.canonical_objects",
                "Define how information, beliefs, actions, and incentives interact before asking readers to parse the general result.",
                strength="required",
                effect_scope="authoring",
                directive_kind="calibrate_reader",
            ),
        ),
    )
    audience_cards = tuple(
        layer(
            f"profile.audience.{key}.v1",
            "audience",
            key,
            (
                directive(
                    f"audience.{key}.timing",
                    "audience.explanation_timing",
                    f"Calibrate definitions, intuition, examples, and proof roadmap for the declared {key.replace('_', ' ')} reader.",
                    strength="required",
                    effect_scope="authoring",
                    directive_kind="calibrate_reader",
                ),
            ),
        )
        for key in (
            "general_economist",
            "economic_theorist",
            "field_specialist",
            "theory_and_field_bridge",
            "policy_or_design_literate_economist",
        )
    )
    cards = (floor, pure, applied, *ambitions, *archetype_cards, field, *audience_cards)
    return ProfileCatalogRelease(
        release_id="profile.catalog.theory_seed",
        resource_version=1,
        universal_floor_ref=static_resource_ref(floor),
        cards=cards,
        release_notes=(
            "Initial theory-only seed: universal floor plus schema-complete modes, ambitions, archetypes, one provisional field calibration, and audiences; no real venue overlay is active."
        ),
        released_by=CURATOR,
        released_at=STAMP,
    )


def source_card(
    source_id: str,
    *,
    citation: str,
    locator: str,
    source_hash: str,
    evidence_hash: str,
    research_mode: str,
    evidence_role: str,
    split: str,
    family: str,
    lineage: tuple[str, ...],
    summary: str,
    transferable: str,
) -> CraftSourceCard:
    return CraftSourceCard(
        source_card_id=source_id,
        resource_version=1,
        citation=citation,
        source_locator=locator,
        source_content_hash=source_hash,
        access_status="project_owned" if locator.startswith("repo:") else "verified_public",
        access_evidence_ref=artifact(f"access.{source_id}", evidence_hash),
        access_verified_at="2026-07-12",
        research_mode=research_mode,
        evidence_role=evidence_role,
        corpus_split=split,
        paper_family_id=family,
        author_lineage_ids=lineage,
        reader_problem_key="reader_problem.opaque_benchmark",
        function_key="craft_function.benchmark_before_mechanism",
        functional_summary=summary,
        transferable_content=transferable,
        paper_specific_nontransferable=(
            "Do not transfer wording, cadence, notation, examples, applications, or any author-specific voice."
        ),
        confidence="supported" if evidence_role != "provisional" else "provisional",
        non_applicability=(
            "Do not use when the benchmark or operative economic force remains scientifically unresolved.",
        ),
        phrase_audit_ref=artifact(f"phrase.audit.{source_id}", evidence_hash),
        derived_by=CURATOR,
        derived_at=STAMP,
    )


def craft_corpus() -> CraftCorpusRelease:
    kg = source_card(
        "craft.source.kamenica_gentzkow_2011.benchmark",
        citation=(
            "Emir Kamenica and Matthew Gentzkow (2011), Bayesian Persuasion, American Economic Review 101(6):2590-2615, doi:10.1257/aer.101.6.2590"
        ),
        locator="https://www.aeaweb.org/articles?id=10.1257/aer.101.6.2590",
        source_hash="6ba7e6bedca9b98e5749c1d26f33d1d4971a2b54b3b3fbca6f7b845a4d06a65b",
        evidence_hash="9130d0d98500a087cbd0c9caa1cbfd1af6760cf5d652fed426e996049aa3087c",
        research_mode="applied_theory",
        evidence_role="matched_anchor",
        split="anchor",
        family="paper_family.kamenica_gentzkow_bayesian_persuasion",
        lineage=("author.kamenica", "author.gentzkow"),
        summary=(
            "The derived card tracks how a precise persuasion question and benchmark make the later information-design result economically legible."
        ),
        transferable=(
            "State the natural benchmark and operative choice before asking the reader to absorb the general characterization."
        ),
    )
    varian = source_card(
        "craft.source.varian_1997.benchmark",
        citation=(
            "Hal R. Varian (1997), How to Build an Economic Model in Your Spare Time, The American Economist 41(2):3-10"
        ),
        locator="https://people.ischool.berkeley.edu/~hal/Papers/how-OLD.pdf",
        source_hash="9035599e06746c9a2b929f9b6a3504b6a8ef6151d85eee27c486d9753745041c",
        evidence_hash="1885326bfa1dbb765ab25550a6e4184355dc790838f1d37240f12ea09afee37d",
        research_mode="theory_methodology",
        evidence_role="matched_anchor",
        split="anchor",
        family="paper_family.varian_model_building",
        lineage=("author.varian",),
        summary=(
            "The derived card records the function of beginning from a concrete economic question and simple benchmark before generalization."
        ),
        transferable=(
            "Use the simplest benchmark that exposes the economic delta, then let the general model answer the already-understood question."
        ),
    )
    contrast = source_card(
        "craft.source.synthetic_formal_first_contrast",
        citation="Econ Theorist AI v2 project-owned formal-first contrast fixture (2026)",
        locator="repo:craft/evidence/synthetic_formal_first_contrast.md",
        source_hash="e541e710aa79623bf636438783d22fdc2ec7fab1dd4baebaa950df4bf37946d4",
        evidence_hash="e541e710aa79623bf636438783d22fdc2ec7fab1dd4baebaa950df4bf37946d4",
        research_mode="pure_theory",
        evidence_role="contrast",
        split="contrast",
        family="paper_family.synthetic_formal_first",
        lineage=("project.econ_theorist_ai_v2",),
        summary=(
            "The project-owned contrast is formally correct but withholds the benchmark and mechanism until after the proposition."
        ),
        transferable=(
            "Use this card only to recognize the failure mode in which theorem comprehension does not yield a nearby economic prediction."
        ),
    )
    empirical = source_card(
        "craft.source.synthetic_empirical_decoy",
        citation="Econ Theorist AI v2 project-owned empirical-template decoy (2026)",
        locator="repo:craft/evidence/synthetic_empirical_decoy.md",
        source_hash="cc8e97ff8b6b562d6a73c8da2aab5bc323645ebd028ba415785acd8520b4ec8d",
        evidence_hash="cc8e97ff8b6b562d6a73c8da2aab5bc323645ebd028ba415785acd8520b4ec8d",
        research_mode="empirical",
        evidence_role="provisional",
        split="development",
        family="paper_family.synthetic_empirical_decoy",
        lineage=("project.econ_theorist_ai_v2",),
        summary=(
            "The decoy overlaps lexically with the theory problem but organizes evidence around identification and regression reporting."
        ),
        transferable=(
            "No content is transferable into the theory core; the card exists to test explicit empirical exclusion."
        ),
    )
    move = CraftMove(
        move_id="craft.move.benchmark_before_mechanism",
        resource_version=1,
        functional_name="Expose the fixed benchmark before the operative economic force",
        reader_problem_key="reader_problem.opaque_benchmark",
        function_key="craft_function.benchmark_before_mechanism",
        trigger_conditions=(
            "The reader encounters a result before being able to state what the natural benchmark holds fixed.",
            "A formally correct retell does not support a prediction for a nearby environment.",
        ),
        required_semantic_inputs=(
            "semantic_input.natural_benchmark",
            "semantic_input.operative_force",
            "semantic_input.affected_margin",
            "semantic_input.boundary",
        ),
        supported_repair_actions=(
            "repair_explanation",
            "add_boundary",
            "replace_example_or_witness",
        ),
        intended_reader_update=(
            "The reader can distinguish the natural benchmark from the new force and use that distinction to predict the affected margin."
        ),
        typical_placements=("introduction", "result_block"),
        valid_variants=(
            "A hand-solvable example may reveal the same benchmark-to-force contrast before the general statement.",
            "A short benchmark paragraph may precede a theorem when the example would add notation rather than insight.",
        ),
        failure_modes=(
            "Do not turn the move into a fixed journal paragraph template or repeat the theorem in looser words.",
            "Do not use exposition to conceal an unresolved mechanism, assumption, or boundary.",
        ),
        compatible_archetypes=(
            "mechanism_explanation",
            "comparative_statics_threshold",
        ),
        compatible_audiences=(
            "general_economist",
            "economic_theorist",
            "field_specialist",
            "theory_and_field_bridge",
        ),
        compatible_theory_modes=("pure_theory", "applied_theory"),
        compatible_field_keys=("information_economics",),
        eligible_section_roles=("introduction", "result_block"),
        compatible_causal_classes=("local_exposition",),
        non_applicability_rule_ids=(
            "upstream_science_unresolved",
            "nonlocal_causal_class",
            "semantic_inputs_unavailable",
            "theory_mode_incompatible",
            "field_incompatible",
            "section_role_incompatible",
        ),
        matched_anchor_refs=(static_resource_ref(kg), static_resource_ref(varian)),
        contrast_refs=(static_resource_ref(contrast),),
        confidence="supported",
        non_applicability=(
            "Do not apply before the benchmark and mechanism are current, accepted, and economically interpretable.",
        ),
        created_by=CURATOR,
        created_at=STAMP,
    )
    audits = (
        SourceAdmissionAudit(source=kg, included_in_core=True),
        SourceAdmissionAudit(source=varian, included_in_core=True),
        SourceAdmissionAudit(source=contrast, included_in_core=True),
        SourceAdmissionAudit(
            source=empirical,
            included_in_core=False,
            exclusion_reason="empirical_or_mixed",
        ),
    )
    return CraftCorpusRelease(
        release_id="craft.corpus.theory_seed",
        resource_version=1,
        split_id="craft.split.seed_v1",
        source_admission_audits=audits,
        source_cards=(kg, varian, contrast),
        reader_problem_rules=(
            ReaderProblemRule(
                problem_key="reader_problem.opaque_benchmark",
                accepted_finding_categories=(
                    "economic_explanation",
                    "boundary",
                    "transfer",
                ),
                accepted_repair_actions=(
                    "repair_explanation",
                    "add_boundary",
                    "replace_example_or_witness",
                ),
                required_semantic_input_ids=(
                    "semantic_input.natural_benchmark",
                    "semantic_input.operative_force",
                    "semantic_input.affected_margin",
                    "semantic_input.boundary",
                ),
                semantic_input_source_rules=(
                    SemanticInputSourceRule(
                        input_id="semantic_input.natural_benchmark",
                        source_kind="paper_ir",
                        owner_facet="terminology_presentation",
                        selector="paper.narrative_spine.natural_benchmark",
                    ),
                    SemanticInputSourceRule(
                        input_id="semantic_input.operative_force",
                        source_kind="result_contract",
                        owner_facet="terminology_presentation",
                        selector="result_packet.archetype.operative_force",
                    ),
                    SemanticInputSourceRule(
                        input_id="semantic_input.affected_margin",
                        source_kind="result_contract",
                        owner_facet="terminology_presentation",
                        selector="result_packet.archetype.affected_margin",
                    ),
                    SemanticInputSourceRule(
                        input_id="semantic_input.boundary",
                        source_kind="result_contract",
                        owner_facet="terminology_presentation",
                        selector="result_packet.boundary",
                    ),
                ),
                allowed_causal_classes=("local_exposition",),
            ),
        ),
        moves=(move,),
        index_version="craft.index.function_first.v1",
        retriever_version="craft.retriever.matched_contrast.v1",
        released_by=CURATOR,
        released_at=STAMP,
    )


def rendered_resources() -> dict[Path, bytes]:
    return {
        ROOT / "profiles" / "catalog.v1.json": canonical_json_bytes(profile_catalog()),
        ROOT / "craft" / "corpus.v1.json": canonical_json_bytes(craft_corpus()),
    }


def write() -> None:
    for path, data in rendered_resources().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


def check() -> bool:
    return all(path.is_file() and path.read_bytes() == data for path, data in rendered_resources().items())


if __name__ == "__main__":
    if sys.argv[1:] == ["--check"]:
        raise SystemExit(0 if check() else 1)
    if sys.argv[1:]:
        raise SystemExit("usage: export_profile_craft_resources.py [--check]")
    write()
