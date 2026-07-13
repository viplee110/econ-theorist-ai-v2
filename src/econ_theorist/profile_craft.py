"""Strict, independently namespaced Phase 4 profile and craft contracts.

This module is deliberately detached from the Phase 1--3 policy, route, and
runtime registries.  It describes admissible profile/craft resources and
project records without changing any earlier payload bytes.  The contracts
are fail-closed about profile precedence, theory-only craft evidence,
function-first retrieval, copyright-safe realization, and executable-
predicate mapping.  They do not certify publication quality, legal copyright
compliance, or mathematical truth.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from types import MappingProxyType
from typing import Annotated, Literal, Mapping, TypeAlias

from pydantic import Field, field_validator, model_validator

from .codec import canonical_json_bytes, object_digest
from .models import (
    Actor,
    ArtifactDependencyRef,
    DecisionVersionRef,
    Digest,
    EntityVersion,
    EntityVersionRef,
    Facet,
    FacetPayloads,
    NonEmptyString,
    SemanticFacetRef,
    StableId,
    StrictModel,
)
from .theory import ExactEvidenceRef, ResultArchetype


PositiveInt: TypeAlias = Annotated[int, Field(ge=1)]
ExplanatoryText: TypeAlias = Annotated[str, Field(min_length=24)]

ProfileLayerKind: TypeAlias = Literal[
    "universal_floor",
    "theory_mode",
    "ambition",
    "archetype",
    "field",
    "audience",
    "venue_overlay",
    "submission_constraint",
]
TheoryMode: TypeAlias = Literal["pure_theory", "applied_theory"]
AmbitionMode: TypeAlias = Literal[
    "frontier_general_interest", "frontier_theory", "field_frontier"
]
AudienceKind: TypeAlias = Literal[
    "general_economist",
    "economic_theorist",
    "field_specialist",
    "theory_and_field_bridge",
    "policy_or_design_literate_economist",
]
RepairAction: TypeAlias = Literal[
    "correct_formal_expression",
    "narrow_scope",
    "restore_assumption",
    "repair_explanation",
    "replace_example_or_witness",
    "repair_reader_path",
    "stabilize_terminology",
    "add_boundary",
    "remove_governance_language",
    "request_human_decision",
]
FindingCategory: TypeAlias = Literal[
    "formal_fidelity",
    "scope",
    "assumption",
    "proof_language",
    "economic_explanation",
    "example_or_witness",
    "reader_prerequisite",
    "terminology",
    "boundary",
    "transfer",
    "governance_leakage",
    "other",
]
SectionRole: TypeAlias = Literal[
    "introduction",
    "model_motivation",
    "model",
    "result_block",
    "extension",
    "conclusion",
    "appendix",
]
CausalClass: TypeAlias = Literal[
    "initial_planning",
    "local_exposition",
    "reader_path_design",
    "target_profile_mismatch",
    "scientific_content",
]
PredicateLimitationKind: TypeAlias = Literal[
    "nonexact_clause_mapping",
    "domain_not_equal",
    "quantifier_not_equivalent",
    "assumption_mapping_nonexact",
    "bounded_execution_scope",
    "coverage_below_exact",
    "loose_tolerance",
    "nonvacuity_unverified",
    "unexecutable_control",
]
PREDICATE_LIMITATION_KIND_ORDER: tuple[PredicateLimitationKind, ...] = (
    "nonexact_clause_mapping",
    "domain_not_equal",
    "quantifier_not_equivalent",
    "assumption_mapping_nonexact",
    "bounded_execution_scope",
    "coverage_below_exact",
    "loose_tolerance",
    "nonvacuity_unverified",
    "unexecutable_control",
)
NonApplicabilityRuleId: TypeAlias = Literal[
    "upstream_science_unresolved",
    "nonlocal_causal_class",
    "semantic_inputs_unavailable",
    "theory_mode_incompatible",
    "field_incompatible",
    "section_role_incompatible",
]
SemanticInputSourceKind: TypeAlias = Literal["paper_ir", "result_contract"]
SemanticInputSelector: TypeAlias = Literal[
    "paper.narrative_spine.natural_benchmark",
    "result_packet.archetype.operative_force",
    "result_packet.archetype.affected_margin",
    "result_packet.boundary",
]
TypedExtractorArchetype: TypeAlias = Literal[
    "mechanism_explanation",
    "comparative_statics_threshold",
]
TYPED_EXTRACTOR_ARCHETYPES: tuple[TypedExtractorArchetype, ...] = (
    "mechanism_explanation",
    "comparative_statics_threshold",
)
ARCHETYPE_DEPENDENT_SEMANTIC_INPUT_SELECTORS: tuple[
    SemanticInputSelector, ...
] = (
    "result_packet.archetype.operative_force",
    "result_packet.archetype.affected_margin",
)
_ARCHETYPE_SELECTOR_SUFFIXES: Mapping[
    TypedExtractorArchetype, Mapping[SemanticInputSelector, str]
] = MappingProxyType(
    {
        "mechanism_explanation": MappingProxyType(
            {
                "result_packet.archetype.operative_force": (
                    "/archetype_module/initiating_force/content"
                ),
                "result_packet.archetype.affected_margin": (
                    "/archetype_module/affected_margin/content"
                ),
            }
        ),
        "comparative_statics_threshold": MappingProxyType(
            {
                "result_packet.archetype.operative_force": (
                    "/archetype_module/competing_effects/content"
                ),
                "result_packet.archetype.affected_margin": (
                    "/archetype_module/threshold_or_regime_logic/content"
                ),
            }
        ),
    }
)


def semantic_input_selector_path(
    selector: SemanticInputSelector,
    *,
    primary_archetype: ResultArchetype,
    packet_index: int,
) -> str:
    """Resolve one typed selector without guessing or cross-archetype fallback."""

    if selector == "paper.narrative_spine.natural_benchmark":
        return "/payload/narrative_spine/natural_benchmark"
    if primary_archetype not in _ARCHETYPE_SELECTOR_SUFFIXES:
        raise ValueError(
            f"unsupported typed semantic extractor archetype: {primary_archetype}"
        )
    packet_root = f"/payload/result_packets/{packet_index}"
    if selector == "result_packet.boundary":
        return f"{packet_root}/boundary/content"
    try:
        suffix = _ARCHETYPE_SELECTOR_SUFFIXES[primary_archetype][selector]
    except KeyError as exc:
        raise ValueError(
            f"unsupported typed semantic selector for {primary_archetype}: {selector}"
        ) from exc
    return f"{packet_root}{suffix}"


def _actor_key(actor: Actor) -> tuple[str, str]:
    return actor.kind, actor.actor_id


def _ref_key(reference: object) -> tuple[object, ...]:
    if isinstance(reference, EntityVersionRef):
        return ("entity", reference.entity_id, reference.version)
    if isinstance(reference, ArtifactDependencyRef):
        return (
            "artifact",
            reference.artifact_id,
            reference.version,
            reference.content_hash,
        )
    if isinstance(reference, DecisionVersionRef):
        return ("decision", reference.decision_id, reference.version)
    if isinstance(reference, SemanticFacetRef):
        return (
            "semantic_facet",
            reference.entity_id,
            reference.version,
            reference.facet,
            reference.field_path,
            reference.semantic_hash,
        )
    raise TypeError(f"unsupported exact reference: {type(reference).__name__}")


def _unique(values: tuple[object, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _unique_refs(values: tuple[object, ...], label: str) -> None:
    _unique(tuple(_ref_key(item) for item in values), label)


def _ordered_union(groups: tuple[tuple[str, ...], ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item for group in groups for item in group))


class ProfileCraftPayload(StrictModel):
    """Base model for the independent Phase 4 namespace."""

    schema_version: Literal[1] = 1


class StaticResourceRef(StrictModel):
    resource_kind: Literal[
        "profile_layer",
        "profile_catalog",
        "craft_source",
        "craft_move",
        "craft_corpus",
    ]
    resource_id: StableId
    version: PositiveInt
    content_hash: Digest


def static_resource_ref(resource: object) -> StaticResourceRef:
    """Return a content-addressed reference to one registered static resource."""

    if isinstance(resource, ProfileLayerCard):
        kind, identity, version = (
            "profile_layer",
            resource.layer_id,
            resource.resource_version,
        )
    elif isinstance(resource, ProfileCatalogRelease):
        kind, identity, version = (
            "profile_catalog",
            resource.release_id,
            resource.resource_version,
        )
    elif isinstance(resource, CraftSourceCard):
        kind, identity, version = (
            "craft_source",
            resource.source_card_id,
            resource.resource_version,
        )
    elif isinstance(resource, CraftMove):
        kind, identity, version = (
            "craft_move",
            resource.move_id,
            resource.resource_version,
        )
    elif isinstance(resource, CraftCorpusRelease):
        kind, identity, version = (
            "craft_corpus",
            resource.release_id,
            resource.resource_version,
        )
    else:
        raise TypeError(f"not a Phase 4 static resource: {type(resource).__name__}")
    return StaticResourceRef(
        resource_kind=kind,
        resource_id=identity,
        version=version,
        content_hash=object_digest(resource),
    )


# ---------------------------------------------------------------------------
# Static profile resources


class DirectiveAcceptanceCriterion(StrictModel):
    criterion_id: StableId
    required_assertion_roles: tuple[StableId, ...] = ()
    required_review_signals: tuple[StableId, ...] = ()

    @model_validator(mode="after")
    def _criterion_is_observable(self) -> "DirectiveAcceptanceCriterion":
        _unique(self.required_assertion_roles, "criterion assertion roles")
        _unique(self.required_review_signals, "criterion review signals")
        if not self.required_assertion_roles and not self.required_review_signals:
            raise ValueError(
                "a directive acceptance criterion requires an assertion role or review signal"
            )
        return self


class ProfileDirective(StrictModel):
    directive_id: StableId
    conflict_key: StableId
    statement: ExplanatoryText
    strength: Literal["invariant", "required", "soft"]
    effect_scope: Literal[
        "formal_truth",
        "scientific_claim",
        "discovery",
        "economic_interpretation",
        "authoring",
        "review",
        "submission_rendering",
    ]
    directive_kind: Literal[
        "preserve_floor",
        "calibrate_reader",
        "adjust_presentation",
        "submission_rule",
        "require_scientific_content",
        "hard_template",
        "imitate_voice",
        "suppress_boundary",
    ]
    acceptance_criterion: DirectiveAcceptanceCriterion
    non_applicability: ExplanatoryText | None = None


class ProfileLayerCard(ProfileCraftPayload):
    layer_id: StableId
    resource_version: PositiveInt
    layer_kind: ProfileLayerKind
    selection_key: StableId
    status: Literal["active", "provisional", "inactive"]
    theory_only: Literal[True] = True
    is_soft_overlay: bool = False
    directives: Annotated[tuple[ProfileDirective, ...], Field(min_length=1)]
    evidence_refs: tuple[ArtifactDependencyRef, ...] = ()
    evidence_as_of: NonEmptyString | None = None
    confidence: Literal["provisional", "supported", "strong"]
    non_applicability: tuple[ExplanatoryText, ...] = ()
    created_by: Actor
    created_at: NonEmptyString

    @model_validator(mode="after")
    def _layer_invariants(self) -> "ProfileLayerCard":
        _unique(tuple(item.directive_id for item in self.directives), "profile directive IDs")
        _unique(
            tuple(item.acceptance_criterion.criterion_id for item in self.directives),
            "profile directive acceptance criteria",
        )
        if self.layer_kind == "universal_floor":
            if self.status != "active":
                raise ValueError("the universal floor must be active")
            if any(item.strength != "invariant" for item in self.directives):
                raise ValueError("every universal-floor directive must be invariant")
            if self.is_soft_overlay:
                raise ValueError("the universal floor is not an overlay")
            if any(
                item.effect_scope
                in {
                    "formal_truth",
                    "scientific_claim",
                    "discovery",
                    "economic_interpretation",
                }
                and item.directive_kind != "preserve_floor"
                for item in self.directives
            ):
                raise ValueError(
                    "universal-floor scientific effects must preserve accepted science"
                )
        elif self.layer_kind == "venue_overlay":
            if not self.is_soft_overlay:
                raise ValueError("a venue overlay must declare soft-overlay status")
            if not self.evidence_refs or self.evidence_as_of is None:
                raise ValueError("a venue overlay requires dated exact evidence")
        elif self.is_soft_overlay:
            raise ValueError("only venue-overlay cards may be soft overlays")
        if self.layer_kind != "universal_floor" and any(
            item.effect_scope
            in {
                "formal_truth",
                "scientific_claim",
                "discovery",
                "economic_interpretation",
            }
            for item in self.directives
        ):
            raise ValueError(
                "non-floor profile layers cannot alter formal, scientific, discovery, "
                "or economic-interpretation content"
            )
        if self.layer_kind == "submission_constraint" and any(
            item.effect_scope != "submission_rendering" for item in self.directives
        ):
            raise ValueError("submission constraints may affect only rendering")
        if self.confidence in {"supported", "strong"} and not self.evidence_refs:
            raise ValueError("supported profile cards require exact evidence")
        _unique_refs(self.evidence_refs, "profile evidence refs")
        return self


class ProfileCatalogRelease(ProfileCraftPayload):
    release_id: StableId
    resource_version: PositiveInt
    universal_floor_ref: StaticResourceRef
    cards: Annotated[tuple[ProfileLayerCard, ...], Field(min_length=1)]
    release_notes: ExplanatoryText
    released_by: Actor
    released_at: NonEmptyString

    @model_validator(mode="after")
    def _catalog_has_one_floor(self) -> "ProfileCatalogRelease":
        identities = tuple((item.layer_id, item.resource_version) for item in self.cards)
        _unique(identities, "profile catalog card revisions")
        floors = tuple(item for item in self.cards if item.layer_kind == "universal_floor")
        if len(floors) != 1:
            raise ValueError("a profile catalog requires exactly one universal floor")
        expected = static_resource_ref(floors[0])
        if self.universal_floor_ref != expected:
            raise ValueError("universal_floor_ref does not bind the exact floor card")
        return self


# ---------------------------------------------------------------------------
# Static craft resources


class CraftSourceCard(ProfileCraftPayload):
    source_card_id: StableId
    resource_version: PositiveInt
    citation: NonEmptyString
    source_locator: NonEmptyString
    source_content_hash: Digest
    source_artifact_ref: ArtifactDependencyRef | None = None
    access_status: Literal[
        "verified_public",
        "verified_licensed",
        "project_owned",
        "restricted_private",
        "unverified",
        "revoked",
    ]
    access_evidence_ref: ArtifactDependencyRef
    access_verified_at: NonEmptyString
    research_mode: Literal[
        "pure_theory",
        "applied_theory",
        "theory_methodology",
        "empirical",
        "mixed_empirical",
    ]
    evidence_role: Literal["matched_anchor", "contrast", "provisional"]
    corpus_split: Literal[
        "anchor",
        "contrast",
        "development",
        "evaluation_holdout",
        "project_postmortem",
    ]
    paper_family_id: StableId
    author_lineage_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    reader_problem_key: StableId
    function_key: StableId
    functional_summary: ExplanatoryText
    transferable_content: ExplanatoryText
    paper_specific_nontransferable: ExplanatoryText
    confidence: Literal["provisional", "supported", "strong"]
    non_applicability: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    contains_reusable_prose: Literal[False] = False
    writer_visibility: Literal["derived_card_only"] = "derived_card_only"
    phrase_audit_status: Literal["passed"] = "passed"
    phrase_audit_ref: ArtifactDependencyRef
    derived_by: Actor
    derived_at: NonEmptyString

    @field_validator("author_lineage_ids")
    @classmethod
    def _lineages_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "source author lineages")
        return value

    @model_validator(mode="after")
    def _source_provenance_is_coherent(self) -> "CraftSourceCard":
        if self.evidence_role == "matched_anchor" and self.corpus_split not in {
            "anchor",
            "development",
        }:
            raise ValueError("matched anchors require an anchor/development split")
        if self.evidence_role == "contrast" and self.corpus_split not in {
            "contrast",
            "development",
        }:
            raise ValueError("contrast evidence requires a contrast/development split")
        if self.access_status == "restricted_private" and self.source_artifact_ref is None:
            raise ValueError("restricted sources require an exact private artifact ref")
        return self


class CraftMove(ProfileCraftPayload):
    move_id: StableId
    resource_version: PositiveInt
    functional_name: NonEmptyString
    reader_problem_key: StableId
    function_key: StableId
    trigger_conditions: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    required_semantic_inputs: Annotated[tuple[StableId, ...], Field(min_length=1)]
    supported_repair_actions: Annotated[tuple[RepairAction, ...], Field(min_length=1)]
    intended_reader_update: ExplanatoryText
    typical_placements: Annotated[tuple[StableId, ...], Field(min_length=1)]
    valid_variants: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    failure_modes: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    compatible_archetypes: Annotated[tuple[ResultArchetype, ...], Field(min_length=1)]
    compatible_audiences: Annotated[tuple[AudienceKind, ...], Field(min_length=1)]
    compatible_theory_modes: Annotated[tuple[TheoryMode, ...], Field(min_length=1)]
    compatible_field_keys: Annotated[tuple[StableId, ...], Field(min_length=1)]
    eligible_section_roles: Annotated[tuple[SectionRole, ...], Field(min_length=1)]
    compatible_causal_classes: Annotated[tuple[CausalClass, ...], Field(min_length=1)]
    non_applicability_rule_ids: Annotated[
        tuple[NonApplicabilityRuleId, ...], Field(min_length=1)
    ]
    matched_anchor_refs: Annotated[tuple[StaticResourceRef, ...], Field(min_length=1)]
    contrast_refs: tuple[StaticResourceRef, ...] = ()
    confidence: Literal["provisional", "supported", "strong"]
    non_applicability: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    source_phrase_material_included: Literal[False] = False
    voice_policy: Literal["functional_properties_only"] = "functional_properties_only"
    created_by: Actor
    created_at: NonEmptyString

    @model_validator(mode="after")
    def _move_has_independent_evidence_shape(self) -> "CraftMove":
        _unique(
            tuple((item.resource_id, item.version) for item in self.matched_anchor_refs),
            "matched anchor refs",
        )
        _unique(
            tuple((item.resource_id, item.version) for item in self.contrast_refs),
            "contrast refs",
        )
        if any(item.resource_kind != "craft_source" for item in (*self.matched_anchor_refs, *self.contrast_refs)):
            raise ValueError("craft moves may cite only craft-source resources")
        if self.confidence in {"supported", "strong"} and (
            len(self.matched_anchor_refs) < 2 or not self.contrast_refs
        ):
            raise ValueError(
                "supported craft moves require two matched anchors and contrast evidence"
            )
        _unique(self.required_semantic_inputs, "required semantic inputs")
        _unique(self.supported_repair_actions, "supported repair actions")
        _unique(self.compatible_archetypes, "compatible archetypes")
        _unique(self.compatible_audiences, "compatible audiences")
        _unique(self.compatible_theory_modes, "compatible theory modes")
        _unique(self.compatible_field_keys, "compatible field keys")
        _unique(self.eligible_section_roles, "eligible section roles")
        _unique(self.compatible_causal_classes, "compatible causal classes")
        _unique(self.non_applicability_rule_ids, "non-applicability rule IDs")
        return self


class SemanticInputSourceRule(StrictModel):
    """Typed, non-regex source contract for one semantic craft input."""

    input_id: StableId
    source_kind: SemanticInputSourceKind
    owner_facet: Facet
    selector: SemanticInputSelector

    @model_validator(mode="after")
    def _selector_has_the_declared_owner(self) -> "SemanticInputSourceRule":
        expected = {
            "paper.narrative_spine.natural_benchmark": (
                "paper_ir",
                "terminology_presentation",
            ),
            "result_packet.archetype.operative_force": (
                "result_contract",
                "terminology_presentation",
            ),
            "result_packet.archetype.affected_margin": (
                "result_contract",
                "terminology_presentation",
            ),
            "result_packet.boundary": (
                "result_contract",
                "terminology_presentation",
            ),
        }[self.selector]
        if (self.source_kind, self.owner_facet) != expected:
            raise ValueError(
                "semantic-input selector has the wrong source kind or owner facet"
            )
        return self


class ReaderProblemRule(StrictModel):
    problem_key: StableId
    accepted_finding_categories: Annotated[
        tuple[FindingCategory, ...], Field(min_length=1)
    ]
    accepted_repair_actions: Annotated[tuple[RepairAction, ...], Field(min_length=1)]
    required_semantic_input_ids: Annotated[
        tuple[StableId, ...], Field(min_length=1)
    ]
    semantic_input_source_rules: Annotated[
        tuple[SemanticInputSourceRule, ...], Field(min_length=1)
    ]
    allowed_causal_classes: Annotated[tuple[CausalClass, ...], Field(min_length=1)]

    @model_validator(mode="after")
    def _rule_vocabularies_are_unique(self) -> "ReaderProblemRule":
        _unique(self.accepted_finding_categories, "accepted finding categories")
        _unique(self.accepted_repair_actions, "accepted repair actions")
        _unique(self.required_semantic_input_ids, "problem-rule semantic inputs")
        _unique(
            tuple(item.input_id for item in self.semantic_input_source_rules),
            "problem-rule semantic input source IDs",
        )
        if tuple(item.input_id for item in self.semantic_input_source_rules) != (
            self.required_semantic_input_ids
        ):
            raise ValueError(
                "semantic input source rules must exactly follow required input order"
            )
        _unique(self.allowed_causal_classes, "allowed causal classes")
        return self


class SourceAdmissionAudit(StrictModel):
    source: CraftSourceCard
    included_in_core: bool
    exclusion_reason: Literal[
        "empirical_or_mixed",
        "unverified_or_revoked_access",
        "evaluation_holdout",
        "duplicate_lineage",
        "copyright_audit_failed",
        "not_applicable",
    ] | None = None

    @model_validator(mode="after")
    def _admission_has_a_reason(self) -> "SourceAdmissionAudit":
        if self.included_in_core and self.exclusion_reason is not None:
            raise ValueError("included craft sources cannot carry an exclusion reason")
        if not self.included_in_core and self.exclusion_reason is None:
            raise ValueError("excluded craft sources require an exact reason")
        if self.source.research_mode in {"empirical", "mixed_empirical"} and (
            self.included_in_core or self.exclusion_reason != "empirical_or_mixed"
        ):
            raise ValueError("empirical craft sources must be excluded explicitly")
        return self


class CraftCorpusRelease(ProfileCraftPayload):
    release_id: StableId
    resource_version: PositiveInt
    split_id: StableId
    core_theory_only: Literal[True] = True
    copyright_safe_derived_only: Literal[True] = True
    source_admission_audits: Annotated[
        tuple[SourceAdmissionAudit, ...], Field(min_length=1)
    ]
    source_cards: Annotated[tuple[CraftSourceCard, ...], Field(min_length=1)]
    reader_problem_rules: Annotated[tuple[ReaderProblemRule, ...], Field(min_length=1)]
    moves: Annotated[tuple[CraftMove, ...], Field(min_length=1)]
    index_version: StableId
    retriever_version: StableId
    released_by: Actor
    released_at: NonEmptyString

    @model_validator(mode="after")
    def _corpus_is_theory_only_and_traceable(self) -> "CraftCorpusRelease":
        source_ids = tuple(
            (item.source_card_id, item.resource_version) for item in self.source_cards
        )
        _unique(source_ids, "core craft-source revisions")
        _unique(
            tuple((item.move_id, item.resource_version) for item in self.moves),
            "craft-move revisions",
        )
        _unique(
            tuple(item.problem_key for item in self.reader_problem_rules),
            "reader-problem rules",
        )
        audits = {
            (item.source.source_card_id, item.source.resource_version): item
            for item in self.source_admission_audits
        }
        if len(audits) != len(self.source_admission_audits):
            raise ValueError("source admission audits must be unique")
        if set(source_ids) != {
            key for key, audit in audits.items() if audit.included_in_core
        }:
            raise ValueError("core source_cards must equal admitted source audits")
        allowed_modes = {"pure_theory", "applied_theory", "theory_methodology"}
        allowed_access = {
            "verified_public",
            "verified_licensed",
            "project_owned",
            "restricted_private",
        }
        for source in self.source_cards:
            if source.research_mode not in allowed_modes:
                raise ValueError("empirical-paper templates cannot enter the core corpus")
            if source.access_status not in allowed_access:
                raise ValueError("unverified or revoked sources cannot enter the core corpus")
            if source.corpus_split == "evaluation_holdout":
                raise ValueError("evaluation holdouts cannot enter the craft corpus")

        corpus_anchor_lineages: set[str] = set()
        for source in self.source_cards:
            if source.evidence_role != "matched_anchor":
                continue
            lineages = set(source.author_lineage_ids)
            if corpus_anchor_lineages.intersection(lineages):
                raise ValueError(
                    "core matched anchors must have disjoint author lineages"
                )
            corpus_anchor_lineages.update(lineages)

        by_ref = {static_resource_ref(item): item for item in self.source_cards}
        rules_by_key = {item.problem_key: item for item in self.reader_problem_rules}
        for move in self.moves:
            rule = rules_by_key.get(move.reader_problem_key)
            if rule is None:
                raise ValueError("every craft move requires one exact reader-problem rule")
            if not set(move.supported_repair_actions).issubset(
                rule.accepted_repair_actions
            ):
                raise ValueError("craft move supports an action outside its problem rule")
            if not set(move.required_semantic_inputs).issubset(
                rule.required_semantic_input_ids
            ):
                raise ValueError("craft move requires inputs outside its problem rule")
            if not set(move.compatible_causal_classes).issubset(
                rule.allowed_causal_classes
            ):
                raise ValueError("craft move accepts a causal class outside its problem rule")
            if any(
                item.selector in ARCHETYPE_DEPENDENT_SEMANTIC_INPUT_SELECTORS
                for item in rule.semantic_input_source_rules
            ) and not set(move.compatible_archetypes).issubset(
                TYPED_EXTRACTOR_ARCHETYPES
            ):
                raise ValueError(
                    "craft move declares an archetype unsupported by its typed extractors"
                )
            try:
                anchors = tuple(by_ref[item] for item in move.matched_anchor_refs)
                contrasts = tuple(by_ref[item] for item in move.contrast_refs)
            except KeyError as exc:
                raise ValueError("craft move cites a source outside the release") from exc
            if any(item.evidence_role != "matched_anchor" for item in anchors):
                raise ValueError("matched refs must resolve to matched anchors")
            if any(item.evidence_role != "contrast" for item in contrasts):
                raise ValueError("contrast refs must resolve to contrast sources")
            if any(
                item.function_key != move.function_key
                or item.reader_problem_key != move.reader_problem_key
                for item in (*anchors, *contrasts)
            ):
                raise ValueError("craft evidence must match the move by function")
            independent_families = {item.paper_family_id for item in anchors}
            if move.confidence in {"supported", "strong"} and len(independent_families) < 2:
                raise ValueError("two versions of one paper do not provide independence")
            seen_lineages: set[str] = set()
            for anchor in anchors:
                lineages = set(anchor.author_lineage_ids)
                if seen_lineages.intersection(lineages):
                    raise ValueError(
                        "matched anchors must have disjoint author lineages"
                    )
                seen_lineages.update(lineages)
        return self


# ---------------------------------------------------------------------------
# Project profile resolution and function-first craft selection


class TargetProfile(ProfileCraftPayload):
    target_profile_id: StableId
    package_ref: EntityVersionRef
    package_hash: Digest
    paper_ir_ref: EntityVersionRef
    paper_ir_hash: Digest
    reader_path_ref: EntityVersionRef
    reader_path_hash: Digest
    base_profile_manifest_ref: EntityVersionRef
    base_profile_manifest_hash: Digest
    source_state_revision: Digest
    catalog_release_ref: StaticResourceRef
    theory_mode: TheoryMode
    ambition: AmbitionMode
    primary_archetype: ResultArchetype
    field_key: StableId
    primary_audience: AudienceKind
    secondary_audience: AudienceKind | None = None
    venue_overlay_ref: StaticResourceRef | None = None
    submission_constraint_refs: tuple[StaticResourceRef, ...] = ()
    human_decision_refs: Annotated[
        tuple[DecisionVersionRef, ...], Field(min_length=4)
    ]
    selected_by: Actor
    selected_at: NonEmptyString

    @model_validator(mode="after")
    def _target_refs_have_expected_kinds(self) -> "TargetProfile":
        if self.catalog_release_ref.resource_kind != "profile_catalog":
            raise ValueError("TargetProfile requires an exact profile catalog")
        if self.venue_overlay_ref is not None and (
            self.venue_overlay_ref.resource_kind != "profile_layer"
        ):
            raise ValueError("venue_overlay_ref must reference a profile layer")
        if any(
            item.resource_kind != "profile_layer"
            for item in self.submission_constraint_refs
        ):
            raise ValueError("submission constraints must reference profile layers")
        if self.secondary_audience == self.primary_audience:
            raise ValueError("secondary audience must add a distinct reader")
        _unique_refs(
            (
                self.package_ref,
                self.paper_ir_ref,
                self.reader_path_ref,
                self.base_profile_manifest_ref,
            ),
            "target-profile exact project refs",
        )
        _unique_refs(self.human_decision_refs, "target-profile Decision refs")
        _unique(
            tuple((item.resource_id, item.version) for item in self.submission_constraint_refs),
            "submission-constraint refs",
        )
        return self


class ResolvedDirective(StrictModel):
    source_card_ref: StaticResourceRef
    source_layer_kind: ProfileLayerKind
    directive: ProfileDirective
    precedence: Annotated[int, Field(ge=1, le=10)]
    outcome: Literal["active", "rejected"]
    rejection_reason: Literal[
        "universal_floor_conflict",
        "forbidden_scientific_effect",
        "hard_venue_template",
        "named_voice_imitation",
        "boundary_suppression",
        "inactive_or_provisional_source",
        "lower_precedence_conflict",
        "not_applicable",
    ] | None = None

    @model_validator(mode="after")
    def _resolution_records_rejection(self) -> "ResolvedDirective":
        if self.outcome == "active" and self.rejection_reason is not None:
            raise ValueError("active directives cannot carry rejection reasons")
        if self.outcome == "rejected" and self.rejection_reason is None:
            raise ValueError("rejected directives require an exact reason")
        return self


class SelectedProfileLayerBinding(StrictModel):
    """Thin binding to a selected static layer; no catalog/card embedding."""

    layer_ref: StaticResourceRef
    layer_kind: ProfileLayerKind
    selection_key: StableId
    source_status: Literal["active", "provisional", "inactive"]

    @model_validator(mode="after")
    def _binding_is_a_profile_layer(self) -> "SelectedProfileLayerBinding":
        if self.layer_ref.resource_kind != "profile_layer":
            raise ValueError("selected layer bindings require profile-layer refs")
        return self


class ResolvedProfileStack(ProfileCraftPayload):
    stack_id: StableId
    target_profile_ref: EntityVersionRef
    target_profile_hash: Digest
    catalog_release_ref: StaticResourceRef
    selected_layers: Annotated[
        tuple[SelectedProfileLayerBinding, ...], Field(min_length=6)
    ]
    directive_resolutions: Annotated[
        tuple[ResolvedDirective, ...], Field(min_length=1)
    ]
    active_requirements: tuple[StableId, ...]
    active_soft_preferences: tuple[StableId, ...]
    source_state_revision: Digest
    resolver_version: StableId
    resolved_by: Actor
    resolved_at: NonEmptyString

    @model_validator(mode="after")
    def _universal_floor_wins(self) -> "ResolvedProfileStack":
        if self.catalog_release_ref.resource_kind != "profile_catalog":
            raise ValueError("profile stack requires an exact profile-catalog ref")
        layers_by_ref = {item.layer_ref: item for item in self.selected_layers}
        if len(layers_by_ref) != len(self.selected_layers):
            raise ValueError("selected profile layers must be unique")
        counts = Counter(item.layer_kind for item in self.selected_layers)
        for required in (
            "universal_floor",
            "theory_mode",
            "ambition",
            "archetype",
            "field",
            "audience",
        ):
            if counts[required] != 1:
                raise ValueError(f"profile stack requires exactly one {required} layer")
        if counts["venue_overlay"] > 1:
            raise ValueError("profile stack permits at most one venue overlay")
        observed: dict[tuple[StaticResourceRef, str], ResolvedDirective] = {}
        _unique(
            tuple(item.directive.directive_id for item in self.directive_resolutions),
            "resolved directive IDs",
        )
        for resolution in self.directive_resolutions:
            key = (resolution.source_card_ref, resolution.directive.directive_id)
            if key in observed:
                raise ValueError("each selected directive must be resolved exactly once")
            source = layers_by_ref.get(resolution.source_card_ref)
            if source is None:
                raise ValueError("directive resolution does not bind a selected layer")
            if source.layer_kind != resolution.source_layer_kind:
                raise ValueError("directive resolution has the wrong source layer")
            observed[key] = resolution

        floor_keys = {
            item.directive.conflict_key
            for item in self.directive_resolutions
            if item.source_layer_kind == "universal_floor"
        }
        for resolution in self.directive_resolutions:
            directive = resolution.directive
            if resolution.source_layer_kind == "universal_floor":
                if resolution.outcome != "active":
                    raise ValueError("universal-floor directives cannot be rejected")
            if resolution.source_layer_kind == "venue_overlay":
                unsafe_scope = directive.effect_scope in {
                    "formal_truth",
                    "scientific_claim",
                    "discovery",
                    "economic_interpretation",
                }
                unsafe_kind = directive.directive_kind in {
                    "require_scientific_content",
                    "hard_template",
                    "imitate_voice",
                    "suppress_boundary",
                }
                hard = directive.strength != "soft"
                if resolution.outcome == "active" and (unsafe_scope or unsafe_kind or hard):
                    raise ValueError("venue overlays may activate only soft authoring/review calibration")
                if resolution.outcome == "active" and directive.effect_scope not in {
                    "authoring",
                    "review",
                }:
                    raise ValueError("active venue overlays cannot affect science or discovery")
                if directive.conflict_key in floor_keys and resolution.outcome == "active":
                    raise ValueError("a venue overlay cannot override the universal floor")
            source_layer = layers_by_ref[resolution.source_card_ref]
            if source_layer.source_status != "active" and resolution.outcome == "active":
                raise ValueError("inactive or provisional profile cards cannot activate directives")

        active = tuple(
            item.directive.directive_id
            for item in self.directive_resolutions
            if item.outcome == "active" and item.directive.strength != "soft"
        )
        soft = tuple(
            item.directive.directive_id
            for item in self.directive_resolutions
            if item.outcome == "active" and item.directive.strength == "soft"
        )
        if set(active) != set(self.active_requirements):
            raise ValueError("active_requirements is not the exact resolved projection")
        if set(soft) != set(self.active_soft_preferences):
            raise ValueError("active_soft_preferences is not the exact resolved projection")
        _unique(self.active_requirements, "active requirements")
        _unique(self.active_soft_preferences, "active soft preferences")
        return self


class ProjectPayloadBinding(StrictModel):
    """Content-addressed binding to one exact project entity payload."""

    entity_ref: EntityVersionRef
    payload_hash: Digest


NoPriorManuscriptUnitReason: TypeAlias = Literal[
    "initial_composition_not_yet_realized"
]
NoPriorReviewReason: TypeAlias = Literal[
    "initial_composition_not_yet_reviewable"
]


class SemanticInputBinding(StrictModel):
    input_id: StableId
    source_ref: SemanticFacetRef | None = None
    source_kind: Literal[
        "paper_ir",
        "reader_path",
        "result_contract",
        "manuscript_unit",
        "review_finding",
        "human_decision",
        "derived_diagnosis",
    ]
    availability: Literal["available", "missing", "scientifically_unresolved"]
    explanation: ExplanatoryText

    @model_validator(mode="after")
    def _availability_binds_an_exact_source(self) -> "SemanticInputBinding":
        if (self.source_ref is not None) != (self.availability == "available"):
            raise ValueError(
                "available semantic inputs require an exact facet; unavailable inputs forbid one"
            )
        return self


class ResolutionRequirement(StrictModel):
    requirement_id: StableId
    finding_ref: EntityVersionRef
    action: RepairAction
    instruction_source: SemanticFacetRef
    affected_assertion_ids: tuple[StableId, ...] = ()
    affected_section_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    required_semantic_input_ids: Annotated[
        tuple[StableId, ...], Field(min_length=1)
    ]

    @model_validator(mode="after")
    def _requirement_projections_are_unique(self) -> "ResolutionRequirement":
        _unique(self.affected_assertion_ids, "resolution affected assertion IDs")
        _unique(self.affected_section_ids, "resolution affected section IDs")
        _unique(
            self.required_semantic_input_ids,
            "resolution required semantic input IDs",
        )
        return self


class ReaderProblemDiagnosis(ProfileCraftPayload):
    diagnosis_id: StableId
    paper_ir_ref: EntityVersionRef
    paper_ir_hash: Digest
    reader_path_ref: EntityVersionRef
    reader_path_hash: Digest
    profile_stack_ref: EntityVersionRef
    profile_stack_hash: Digest
    result_contract_set_binding: ProjectPayloadBinding
    inspected_manuscript_unit_binding: ProjectPayloadBinding | None = None
    no_prior_manuscript_unit_reason: NoPriorManuscriptUnitReason | None = None
    diagnostic_review_bindings: tuple[ProjectPayloadBinding, ...] = ()
    diagnostic_finding_bindings: tuple[ProjectPayloadBinding, ...] = ()
    blocked_review_closure_binding: ProjectPayloadBinding | None = None
    revision_brief_binding: ProjectPayloadBinding | None = None
    no_prior_review_reason: NoPriorReviewReason | None = None
    diagnostic_categories: tuple[FindingCategory, ...] = ()
    affected_section_roles: Annotated[tuple[SectionRole, ...], Field(min_length=1)]
    causal_class: CausalClass
    resolution_requirements: tuple[ResolutionRequirement, ...] = ()
    semantic_input_bindings: tuple[SemanticInputBinding, ...] = ()
    affected_section_ids: tuple[StableId, ...] = ()
    reader_problem_key: StableId
    required_resolution_ids: tuple[StableId, ...] = ()
    observed_problem: ExplanatoryText
    required_semantic_input_ids: tuple[StableId, ...] = ()
    upstream_science_status: Literal["resolved", "unresolved"]
    craft_eligible: bool
    upstream_repair_route: StableId | None = None
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    diagnosed_by: Actor
    diagnosed_at: NonEmptyString

    @model_validator(mode="after")
    def _craft_follows_scientific_diagnosis(self) -> "ReaderProblemDiagnosis":
        _unique(self.affected_section_ids, "affected section IDs")
        _unique(self.required_resolution_ids, "diagnosis resolution IDs")
        _unique(self.required_semantic_input_ids, "diagnosis semantic inputs")
        _unique(self.diagnostic_categories, "diagnostic finding categories")
        _unique(self.affected_section_roles, "affected section roles")
        _unique(
            tuple(item.requirement_id for item in self.resolution_requirements),
            "resolution requirements",
        )
        _unique(
            tuple(item.input_id for item in self.semantic_input_bindings),
            "semantic input bindings",
        )
        _unique_refs(self.evidence_refs, "diagnosis evidence refs")

        expected_resolution_ids = tuple(
            item.requirement_id for item in self.resolution_requirements
        )
        expected_section_ids = _ordered_union(
            tuple(item.affected_section_ids for item in self.resolution_requirements)
        )
        expected_input_ids = _ordered_union(
            tuple(
                item.required_semantic_input_ids
                for item in self.resolution_requirements
            )
        )
        if self.required_resolution_ids != expected_resolution_ids:
            raise ValueError(
                "required_resolution_ids must be the exact requirement projection"
            )
        if self.affected_section_ids != expected_section_ids:
            raise ValueError(
                "affected_section_ids must be the exact requirement projection"
            )
        if self.required_semantic_input_ids != expected_input_ids:
            raise ValueError(
                "required_semantic_input_ids must be the exact requirement projection"
            )
        if tuple(item.input_id for item in self.semantic_input_bindings) != (
            self.required_semantic_input_ids
        ):
            raise ValueError(
                "semantic input bindings must cover the required input projection in order"
            )

        has_unit = self.inspected_manuscript_unit_binding is not None
        has_no_unit_reason = self.no_prior_manuscript_unit_reason is not None
        if has_unit == has_no_unit_reason:
            raise ValueError(
                "diagnosis requires exactly one inspected manuscript unit or "
                "typed no-prior-unit reason"
            )

        has_reviews = bool(self.diagnostic_review_bindings)
        has_findings = bool(self.diagnostic_finding_bindings)
        has_no_review_reason = self.no_prior_review_reason is not None
        if has_reviews != has_findings:
            raise ValueError(
                "diagnostic review records and findings must be bound together"
            )
        if has_reviews == has_no_review_reason:
            raise ValueError(
                "diagnosis requires exactly one review/finding evidence set or "
                "typed no-prior-review reason"
            )
        if has_unit and not has_reviews:
            raise ValueError(
                "an inspected manuscript unit requires diagnostic reviews and findings"
            )
        if not has_unit and has_reviews:
            raise ValueError(
                "pre-manuscript diagnosis cannot claim review or finding evidence"
            )

        has_closure = self.blocked_review_closure_binding is not None
        has_brief = self.revision_brief_binding is not None
        if has_closure != has_brief:
            raise ValueError(
                "blocked review closure and RevisionBrief must be bound together"
            )
        initial = self.causal_class == "initial_planning"
        if initial:
            if has_unit or has_reviews or has_closure:
                raise ValueError(
                    "initial planning cannot claim a manuscript failure bundle"
                )
            if self.resolution_requirements or self.semantic_input_bindings:
                raise ValueError(
                    "initial planning cannot claim RevisionBrief-derived requirements"
                )
            if self.diagnostic_categories:
                raise ValueError("initial planning cannot claim review finding categories")
        elif not (has_unit and has_reviews and has_closure):
            raise ValueError(
                "post-manuscript diagnosis requires one complete failure/closure/brief bundle"
            )
        elif not self.resolution_requirements or not self.diagnostic_categories:
            raise ValueError(
                "post-manuscript diagnosis requires typed findings and resolution requirements"
            )

        review_refs = tuple(
            item.entity_ref for item in self.diagnostic_review_bindings
        )
        review_hashes = tuple(
            item.payload_hash for item in self.diagnostic_review_bindings
        )
        finding_refs = tuple(
            item.entity_ref for item in self.diagnostic_finding_bindings
        )
        finding_hashes = tuple(
            item.payload_hash for item in self.diagnostic_finding_bindings
        )
        _unique_refs(review_refs, "diagnostic review refs")
        _unique(review_hashes, "diagnostic review hashes")
        _unique_refs(finding_refs, "diagnostic finding refs")
        _unique(finding_hashes, "diagnostic finding hashes")

        required_evidence_refs = {
            _ref_key(self.paper_ir_ref),
            _ref_key(self.reader_path_ref),
            _ref_key(self.profile_stack_ref),
            _ref_key(self.result_contract_set_binding.entity_ref),
            *(
                ()
                if self.inspected_manuscript_unit_binding is None
                else (_ref_key(self.inspected_manuscript_unit_binding.entity_ref),)
            ),
            *(_ref_key(item) for item in review_refs),
            *(_ref_key(item) for item in finding_refs),
            *(
                ()
                if self.blocked_review_closure_binding is None
                else (
                    _ref_key(self.blocked_review_closure_binding.entity_ref),
                    _ref_key(self.revision_brief_binding.entity_ref),  # type: ignore[union-attr]
                )
            ),
        }
        observed_evidence_refs = {_ref_key(item) for item in self.evidence_refs}
        if not required_evidence_refs.issubset(observed_evidence_refs):
            raise ValueError(
                "diagnosis evidence refs must cover every exact diagnosis binding"
            )
        if not initial:
            known_findings = {
                item.entity_ref for item in self.diagnostic_finding_bindings
            }
            if any(
                item.finding_ref not in known_findings
                for item in self.resolution_requirements
            ):
                raise ValueError(
                    "resolution requirements must bind findings in the failure bundle"
                )
        if self.causal_class == "scientific_content":
            if self.upstream_science_status != "unresolved":
                raise ValueError("scientific-content diagnoses must remain unresolved")
        elif self.upstream_science_status != "resolved":
            raise ValueError("only scientific-content diagnoses may be science-unresolved")
        expected_craft_eligible = self.causal_class == "local_exposition"
        if self.craft_eligible != expected_craft_eligible:
            raise ValueError("only local-exposition diagnoses are craft-eligible")
        if self.craft_eligible:
            if self.upstream_repair_route is not None:
                raise ValueError("craft-eligible local repairs cannot route upstream")
        elif self.upstream_repair_route is None:
            raise ValueError("nonlocal diagnoses require an exact upstream repair route")
        return self


class MoveRequirementCoverage(StrictModel):
    requirement_id: StableId
    repair_action: RepairAction
    required_semantic_input_ids: Annotated[
        tuple[StableId, ...], Field(min_length=1)
    ]
    available_semantic_input_ids: tuple[StableId, ...]
    missing_semantic_input_ids: tuple[StableId, ...]
    action_supported: bool
    semantic_inputs_available: bool
    covered: bool

    @model_validator(mode="after")
    def _coverage_is_an_exact_projection(self) -> "MoveRequirementCoverage":
        _unique(self.required_semantic_input_ids, "coverage required semantic inputs")
        _unique(self.available_semantic_input_ids, "coverage available semantic inputs")
        _unique(self.missing_semantic_input_ids, "coverage missing semantic inputs")
        required = set(self.required_semantic_input_ids)
        available = set(self.available_semantic_input_ids)
        missing = set(self.missing_semantic_input_ids)
        if available.intersection(missing) or available.union(missing) != required:
            raise ValueError(
                "available and missing semantic inputs must partition the requirement"
            )
        if self.semantic_inputs_available != (not missing):
            raise ValueError("semantic_inputs_available is not the exact projection")
        if self.covered != (self.action_supported and self.semantic_inputs_available):
            raise ValueError("covered is not the exact action/input projection")
        return self


class CraftCandidateAudit(StrictModel):
    move_ref: StaticResourceRef
    move: CraftMove
    functional_match: Literal["exact", "compatible", "mismatch"]
    semantic_inputs_present: bool
    archetype_compatible: bool
    audience_compatible: bool
    theory_mode_compatible: bool
    field_compatible: bool
    placement_compatible: bool
    causal_class_compatible: bool
    non_applicability_triggered: bool
    triggered_non_applicability_rule_ids: tuple[NonApplicabilityRuleId, ...] = ()
    corpus_admissible: bool
    confidence_admissible: bool
    lexical_similarity_rank: PositiveInt | None = None
    requirement_coverages: tuple[MoveRequirementCoverage, ...] = ()
    covered_requirement_ids: tuple[StableId, ...] = ()
    selected: bool
    exclusion_reason: Literal[
        "function_mismatch",
        "missing_semantic_inputs",
        "archetype_mismatch",
        "audience_mismatch",
        "theory_mode_mismatch",
        "field_mismatch",
        "placement_mismatch",
        "causal_class_mismatch",
        "non_applicable",
        "corpus_excluded",
        "insufficient_confidence",
        "redundant_not_minimal",
    ] | None = None

    @model_validator(mode="after")
    def _candidate_is_function_first(self) -> "CraftCandidateAudit":
        if self.move_ref != static_resource_ref(self.move):
            raise ValueError("candidate audit does not bind the exact craft move")
        _unique(
            self.triggered_non_applicability_rule_ids,
            "triggered non-applicability rule IDs",
        )
        _unique(
            tuple(item.requirement_id for item in self.requirement_coverages),
            "candidate requirement coverage records",
        )
        projected = tuple(
            item.requirement_id for item in self.requirement_coverages if item.covered
        )
        if self.covered_requirement_ids != projected:
            raise ValueError(
                "covered_requirement_ids must be the exact coverage projection"
            )
        if self.non_applicability_triggered != bool(
            self.triggered_non_applicability_rule_ids
        ):
            raise ValueError(
                "non_applicability_triggered must project triggered rule IDs"
            )
        if not set(self.triggered_non_applicability_rule_ids).issubset(
            self.move.non_applicability_rule_ids
        ):
            raise ValueError("candidate triggered a rule not declared by its craft move")
        eligible = (
            self.functional_match == "exact"
            and self.semantic_inputs_present
            and self.archetype_compatible
            and self.audience_compatible
            and self.theory_mode_compatible
            and self.field_compatible
            and self.placement_compatible
            and self.causal_class_compatible
            and not self.non_applicability_triggered
            and self.corpus_admissible
            and self.confidence_admissible
            and self.move.confidence in {"supported", "strong"}
            and bool(self.move.contrast_refs)
        )
        if self.selected and not eligible:
            raise ValueError("selected craft moves must pass every functional hard filter")
        if self.selected and (not self.covered_requirement_ids or self.exclusion_reason is not None):
            raise ValueError("selected candidates require coverage and no exclusion")
        if not self.selected and self.exclusion_reason is None:
            raise ValueError("every rejected candidate requires an auditable reason")
        _unique(self.covered_requirement_ids, "candidate requirement coverage")
        return self


class CraftSelectionManifest(ProfileCraftPayload):
    selection_id: StableId
    diagnosis_ref: EntityVersionRef
    diagnosis_hash: Digest
    diagnosed_reader_problem_key: StableId
    diagnosed_required_resolution_ids: Annotated[
        tuple[StableId, ...], Field(min_length=1)
    ]
    diagnosed_upstream_science_status: Literal["resolved", "unresolved"]
    profile_stack_ref: EntityVersionRef
    profile_stack_hash: Digest
    corpus_release_ref: StaticResourceRef
    selection_strategy: Literal["function_first_semantic_set_cover_v2"]
    index_version: StableId
    retriever_version: StableId
    selector_version: StableId
    candidates: Annotated[tuple[CraftCandidateAudit, ...], Field(min_length=1, max_length=64)]
    selected_move_refs: tuple[StaticResourceRef, ...]
    outcome: Literal["selected", "abstained_upstream", "abstained_no_fit"]
    minimality_kind: Literal["minimum_cardinality"] = "minimum_cardinality"
    selected_by: Actor
    selected_at: NonEmptyString

    @model_validator(mode="after")
    def _selection_is_matched_contrast_and_minimal(self) -> "CraftSelectionManifest":
        if self.corpus_release_ref.resource_kind != "craft_corpus":
            raise ValueError("selection requires an exact craft corpus release")
        _unique(
            self.diagnosed_required_resolution_ids,
            "diagnosed resolution IDs",
        )
        refs = tuple(item.move_ref for item in self.candidates)
        _unique(tuple((item.resource_id, item.version) for item in refs), "candidate moves")
        selected = tuple(item for item in self.candidates if item.selected)
        if tuple(item.move_ref for item in selected) != self.selected_move_refs:
            raise ValueError("selected_move_refs must preserve the selected candidate order")
        if self.diagnosed_upstream_science_status == "unresolved":
            if self.outcome != "abstained_upstream" or selected:
                raise ValueError("unresolved economics requires upstream abstention")
            return self
        if self.outcome == "selected":
            if not selected:
                raise ValueError("selected outcome requires at least one move")
            if any(
                item.move.reader_problem_key != self.diagnosed_reader_problem_key
                for item in selected
            ):
                raise ValueError("selected moves must match the diagnosed reader problem")
            required = set(self.diagnosed_required_resolution_ids)
            coverage = [set(item.covered_requirement_ids) for item in selected]
            if set().union(*coverage) != required:
                raise ValueError("selected moves must cover the exact diagnosed requirements")
            admissible = tuple(
                item
                for item in self.candidates
                if item.functional_match == "exact"
                and item.semantic_inputs_present
                and item.archetype_compatible
                and item.audience_compatible
                and item.theory_mode_compatible
                and item.field_compatible
                and item.placement_compatible
                and item.causal_class_compatible
                and not item.non_applicability_triggered
                and item.corpus_admissible
                and item.confidence_admissible
                and item.move.confidence in {"supported", "strong"}
                and bool(item.move.contrast_refs)
                and item.covered_requirement_ids
            )
            winning_ids: tuple[str, ...] | None = None
            for cardinality in range(1, len(admissible) + 1):
                covers: list[tuple[str, ...]] = []
                for group in combinations(admissible, cardinality):
                    group_coverage = set().union(
                        *(set(item.covered_requirement_ids) for item in group)
                    )
                    if group_coverage == required:
                        covers.append(tuple(sorted(item.move.move_id for item in group)))
                if covers:
                    winning_ids = min(covers)
                    break
            if winning_ids is None:
                raise ValueError("selected outcome has no admissible set cover")
            if tuple(sorted(item.move.move_id for item in selected)) != winning_ids:
                raise ValueError(
                    "craft selection is not the deterministic minimum-cardinality cover"
                )
        elif selected:
            raise ValueError("abstention outcomes cannot select craft moves")
        return self


# ---------------------------------------------------------------------------
# Obligation-to-predicate semantic hardening


class PredicateClauseMapping(StrictModel):
    obligation_clause_id: StableId
    clause_kind: Literal[
        "domain", "quantifier", "assumption", "antecedent", "conclusion", "boundary"
    ]
    relation: Literal["exact", "partial", "omitted", "narrowed", "broadened"]
    predicate_json_pointers: tuple[NonEmptyString, ...]
    predicate_fragment_hash: Digest
    explanation: ExplanatoryText

    @model_validator(mode="after")
    def _mapping_has_executable_locators(self) -> "PredicateClauseMapping":
        _unique(self.predicate_json_pointers, "predicate JSON pointers")
        if self.relation == "omitted" and self.predicate_json_pointers:
            raise ValueError("omitted clauses cannot claim predicate locators")
        if self.relation != "omitted" and not self.predicate_json_pointers:
            raise ValueError("non-omitted clauses require executable predicate locators")
        if any(not item.startswith("/") for item in self.predicate_json_pointers):
            raise ValueError("predicate locators must be canonical JSON Pointers")
        return self


class PredicateWitness(StrictModel):
    witness_id: StableId
    case_id: StableId
    witness_kind: Literal[
        "domain_member", "antecedent_satisfying", "predicate_falsifying", "boundary"
    ]
    artifact_ref: ArtifactDependencyRef
    explanation: ExplanatoryText


class PredicateMutationTest(StrictModel):
    mutation_id: StableId
    mutation_kind: Literal[
        "empty_domain",
        "constant_true",
        "conclusion_flip",
        "domain_narrowing",
        "omitted_assumption",
        "quantifier_flip",
        "extra_assumption",
        "boundary_omission",
        "loose_tolerance",
    ]
    mutated_predicate_ref: ArtifactDependencyRef
    result_ref: ArtifactDependencyRef
    expected_to_fail: Literal[True] = True
    detected: bool


class ObligationPredicateContract(ProfileCraftPayload):
    contract_id: StableId
    assurance_bundle_ref: EntityVersionRef
    assurance_bundle_hash: Digest
    receipt_id: StableId
    receipt_hash: Digest
    obligation_ref: EntityVersionRef
    obligation_hash: Digest
    claim_graph_ref: EntityVersionRef
    claim_graph_hash: Digest
    formal_model_ref: EntityVersionRef
    formal_model_hash: Digest
    assumption_map_ref: EntityVersionRef
    assumption_map_hash: Digest
    obligation_clause_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    obligation_assumption_ids: tuple[StableId, ...]
    mapped_assumption_ids: tuple[StableId, ...]
    added_assumption_ids: tuple[StableId, ...] = ()
    clause_mappings: Annotated[
        tuple[PredicateClauseMapping, ...], Field(min_length=1)
    ]
    domain_relation: Literal["equal", "narrowed", "broadened", "incomparable"]
    quantifier_relation: Literal["equivalent", "weakened", "strengthened", "incomparable"]
    execution_scope: Literal[
        "symbolic_exact", "exhaustive_finite", "finite_sample", "diagnostic"
    ]
    coverage_class: Literal["exact", "partial", "diagnostic", "falsification_only"]
    predicate_artifact_ref: ArtifactDependencyRef
    code_ref: ArtifactDependencyRef
    antecedent_satisfiable: bool
    predicate_can_return_false: bool
    witnesses: Annotated[tuple[PredicateWitness, ...], Field(min_length=1)]
    mutation_tests: Annotated[tuple[PredicateMutationTest, ...], Field(min_length=1)]
    tolerance_policy: Literal["exact", "obligation_authorized", "loose"]
    tolerance_evidence_ref: ExactEvidenceRef | None = None
    mapper: Actor
    mapped_at: NonEmptyString
    limitations: ExplanatoryText

    @model_validator(mode="after")
    def _exact_coverage_is_nonvacuous(self) -> "ObligationPredicateContract":
        _unique(self.obligation_clause_ids, "obligation clause IDs")
        _unique(self.obligation_assumption_ids, "obligation assumption IDs")
        _unique(self.mapped_assumption_ids, "mapped assumption IDs")
        _unique(self.added_assumption_ids, "added assumption IDs")
        _unique(tuple(item.witness_id for item in self.witnesses), "predicate witnesses")
        _unique(
            tuple(item.mutation_id for item in self.mutation_tests),
            "predicate mutation tests",
        )
        mapped_clause_ids = tuple(item.obligation_clause_id for item in self.clause_mappings)
        _unique(mapped_clause_ids, "predicate clause mappings")
        if set(mapped_clause_ids) != set(self.obligation_clause_ids):
            raise ValueError("every obligation clause must have exactly one mapping")
        if self.mapper.kind == "deterministic_tool":
            raise ValueError("semantic predicate mapping requires a human or agent")
        witness_kinds = {item.witness_kind for item in self.witnesses}
        if "domain_member" not in witness_kinds:
            raise ValueError(
                "every predicate mapping requires an executable domain-member witness"
            )
        if self.antecedent_satisfiable != (
            "antecedent_satisfying" in witness_kinds
        ):
            raise ValueError(
                "antecedent_satisfiable requires a distinct executable antecedent witness"
            )
        if self.predicate_can_return_false != (
            "predicate_falsifying" in witness_kinds
        ):
            raise ValueError(
                "predicate_can_return_false requires an executable falsifying witness"
            )
        mandatory_mutations = {
            "empty_domain",
            "constant_true",
            "conclusion_flip",
            "domain_narrowing",
            "omitted_assumption",
        }
        observed_mutations = {item.mutation_kind for item in self.mutation_tests}
        if not mandatory_mutations.issubset(observed_mutations):
            raise ValueError(
                "predicate mapping omits a mandatory executable downgrade attack"
            )
        undetected_executable_controls = tuple(
            item.mutation_id
            for item in self.mutation_tests
            if not item.detected and item.mutation_kind != "omitted_assumption"
        )
        if undetected_executable_controls:
            raise ValueError(
                "every executable predicate downgrade control must be detected"
            )
        if self.tolerance_policy == "obligation_authorized" and self.tolerance_evidence_ref is None:
            raise ValueError("authorized tolerance requires exact obligation evidence")
        if self.tolerance_policy != "obligation_authorized" and self.tolerance_evidence_ref is not None:
            raise ValueError("tolerance evidence is allowed only for authorized tolerance")
        if self.coverage_class == "exact":
            if not all(item.detected for item in self.mutation_tests):
                raise ValueError(
                    "exact predicate coverage cannot rely on an unexecutable control"
                )
            if self.domain_relation != "equal":
                raise ValueError("exact predicate coverage cannot narrow the obligation domain")
            if self.quantifier_relation != "equivalent":
                raise ValueError("exact predicate coverage requires equivalent quantifiers")
            if set(self.mapped_assumption_ids) != set(self.obligation_assumption_ids):
                raise ValueError("exact predicate coverage requires every exact assumption")
            if self.added_assumption_ids:
                raise ValueError("exact predicate coverage cannot add assumptions")
            if any(item.relation != "exact" for item in self.clause_mappings):
                raise ValueError("exact coverage requires exact mapping of every clause")
            if self.execution_scope in {"finite_sample", "diagnostic"}:
                raise ValueError("sampled or diagnostic execution cannot claim exact coverage")
            if not self.antecedent_satisfiable or not self.predicate_can_return_false:
                raise ValueError("exact predicate mapping must be demonstrably nonvacuous")
            if not {"antecedent_satisfying", "predicate_falsifying"}.issubset(witness_kinds):
                raise ValueError("exact mapping requires satisfying and falsifying witnesses")
            mutation_kinds = {item.mutation_kind for item in self.mutation_tests if item.detected}
            if not {"constant_true", "conclusion_flip"}.issubset(mutation_kinds):
                raise ValueError("exact mapping must kill constant-true and conclusion-flip mutants")
            if self.tolerance_policy == "loose":
                raise ValueError("loose tolerance cannot support exact mapping")
        return self


class PredicateMappingFinding(StrictModel):
    finding_id: StableId
    severity: Literal["info", "warning", "error", "critical"]
    summary: ExplanatoryText
    affected_clause_ids: tuple[StableId, ...] = ()
    limitation_kinds: tuple[PredicateLimitationKind, ...] = ()

    @model_validator(mode="after")
    def _limitation_kinds_are_unique_and_ordered(self) -> "PredicateMappingFinding":
        _unique(self.limitation_kinds, "predicate limitation kinds")
        expected = tuple(
            kind
            for kind in PREDICATE_LIMITATION_KIND_ORDER
            if kind in self.limitation_kinds
        )
        if self.limitation_kinds != expected:
            raise ValueError("predicate limitation kinds must use canonical order")
        return self


class PredicateMappingAudit(ProfileCraftPayload):
    audit_id: StableId
    contract_ref: EntityVersionRef
    contract_hash: Digest
    contract_coverage_class: Literal["exact", "partial", "diagnostic", "falsification_only"]
    contract_mapper: Actor
    registered_mutation_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    auditor: Actor
    mutation_executor: Actor
    mutation_replay_ref: ArtifactDependencyRef
    route_run_id: StableId
    route_run_hash: Digest
    context_manifest_hash: Digest
    compiled_context_hash: Digest
    replayed_mutation_ids: tuple[StableId, ...]
    mutation_replay_passed: bool
    unexecutable_mutation_ids: tuple[StableId, ...]
    domain_witness_verified: bool
    antecedent_witness_verified: bool
    falsifying_witness_verified: bool
    findings: tuple[PredicateMappingFinding, ...] = ()
    verdict: Literal["approved_exact", "approved_partial", "rejected"]
    audited_at: NonEmptyString

    @model_validator(mode="after")
    def _audit_is_independent_and_noncompensatory(self) -> "PredicateMappingAudit":
        if _actor_key(self.auditor) == _actor_key(self.contract_mapper):
            raise ValueError("predicate mapping auditor must be independent of mapper")
        if self.auditor.kind == "deterministic_tool":
            raise ValueError("semantic mapping audit requires a human or agent")
        if self.mutation_executor.kind != "deterministic_tool":
            raise ValueError("predicate mutation replay requires a deterministic tool")
        _unique(self.registered_mutation_ids, "registered predicate mutants")
        if set(self.replayed_mutation_ids) != set(self.registered_mutation_ids):
            raise ValueError("mapping audit must replay every registered mutant")
        _unique(self.replayed_mutation_ids, "replayed predicate mutants")
        _unique(self.unexecutable_mutation_ids, "unexecutable predicate controls")
        if not set(self.unexecutable_mutation_ids).issubset(
            self.registered_mutation_ids
        ):
            raise ValueError("unexecutable controls must be registered and replayed")
        blocking = any(item.severity in {"error", "critical"} for item in self.findings)
        warning = any(item.severity == "warning" for item in self.findings)
        if self.verdict in {"approved_exact", "approved_partial"} and not (
            self.mutation_replay_passed and self.domain_witness_verified
        ):
            raise ValueError(
                "predicate approval requires passed executable controls and a domain witness"
            )
        if (
            self.verdict == "approved_partial"
            and self.unexecutable_mutation_ids
            and not warning
        ):
            raise ValueError(
                "partial approval must warn about every typed unexecutable-control gap"
            )
        if self.verdict == "approved_exact":
            if self.contract_coverage_class != "exact":
                raise ValueError("only exact contracts may receive exact approval")
            if not (
                self.mutation_replay_passed
                and self.antecedent_witness_verified
                and self.falsifying_witness_verified
            ):
                raise ValueError("exact approval requires replayed nonvacuity evidence")
            if self.unexecutable_mutation_ids:
                raise ValueError(
                    "exact approval forbids typed unexecutable predicate controls"
                )
            if blocking:
                raise ValueError("blocking semantic findings cannot be compensated")
            if any(item.limitation_kinds for item in self.findings):
                raise ValueError("exact approval cannot declare a predicate limitation")
        if self.verdict == "rejected" and not blocking:
            raise ValueError("rejected mapping audits require a blocking finding")
        return self


# ---------------------------------------------------------------------------
# Craft realization and noncompensatory closure


class CraftMoveRealization(StrictModel):
    move_ref: StaticResourceRef
    realized_assertion_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    realized_semantic_input_ids: Annotated[
        tuple[StableId, ...], Field(min_length=1)
    ]
    realized_semantic_source_refs: Annotated[
        tuple[SemanticFacetRef, ...], Field(min_length=1)
    ]
    realized_function: bool
    intended_reader_update_delivered: bool
    formal_fidelity_preserved: bool
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    explanation: ExplanatoryText

    @field_validator("evidence_refs")
    @classmethod
    def _realization_evidence_is_unique(
        cls, value: tuple[ExactEvidenceRef, ...]
    ) -> tuple[ExactEvidenceRef, ...]:
        _unique_refs(value, "craft realization evidence")
        return value

    @field_validator("realized_assertion_ids", "realized_semantic_input_ids")
    @classmethod
    def _realized_ids_are_unique(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        _unique(value, "craft realization IDs")
        return value

    @field_validator("realized_semantic_source_refs")
    @classmethod
    def _realized_semantic_sources_are_unique(
        cls, value: tuple[SemanticFacetRef, ...]
    ) -> tuple[SemanticFacetRef, ...]:
        _unique_refs(value, "craft realization semantic sources")
        return value


class DirectiveAcceptanceCheck(StrictModel):
    directive_id: StableId
    criterion_id: StableId
    required_assertion_roles: tuple[StableId, ...] = ()
    realized_assertion_roles: tuple[StableId, ...] = ()
    required_review_signals: tuple[StableId, ...] = ()
    observed_review_signals: tuple[StableId, ...] = ()
    outcome: Literal["pass", "fail"]
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    explanation: ExplanatoryText

    @model_validator(mode="after")
    def _directive_check_is_noncompensatory(self) -> "DirectiveAcceptanceCheck":
        for values, label in (
            (self.required_assertion_roles, "required directive assertion roles"),
            (self.realized_assertion_roles, "realized directive assertion roles"),
            (self.required_review_signals, "required directive review signals"),
            (self.observed_review_signals, "observed directive review signals"),
        ):
            _unique(values, label)
        _unique_refs(self.evidence_refs, "directive acceptance evidence")
        if not self.required_assertion_roles and not self.required_review_signals:
            raise ValueError("directive checks require an observable acceptance criterion")
        passed = set(self.required_assertion_roles).issubset(
            self.realized_assertion_roles
        ) and set(self.required_review_signals).issubset(
            self.observed_review_signals
        )
        if (self.outcome == "pass") != passed:
            raise ValueError("directive check outcome is not the exact coverage result")
        return self


class ResolutionRequirementCheck(StrictModel):
    requirement_id: StableId
    repair_action: RepairAction
    realizing_move_refs: Annotated[tuple[StaticResourceRef, ...], Field(min_length=1)]
    affected_assertion_ids: tuple[StableId, ...] = ()
    affected_section_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    required_semantic_input_ids: Annotated[
        tuple[StableId, ...], Field(min_length=1)
    ]
    realized_semantic_input_ids: tuple[StableId, ...]
    outcome: Literal["pass", "fail"]
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    explanation: ExplanatoryText

    @model_validator(mode="after")
    def _resolution_check_is_noncompensatory(self) -> "ResolutionRequirementCheck":
        _unique(
            tuple((item.resource_id, item.version) for item in self.realizing_move_refs),
            "resolution realizing move refs",
        )
        if any(item.resource_kind != "craft_move" for item in self.realizing_move_refs):
            raise ValueError("resolution checks may bind only selected craft moves")
        for values, label in (
            (self.affected_assertion_ids, "checked affected assertion IDs"),
            (self.affected_section_ids, "checked affected section IDs"),
            (self.required_semantic_input_ids, "checked required semantic input IDs"),
            (self.realized_semantic_input_ids, "checked realized semantic input IDs"),
        ):
            _unique(values, label)
        _unique_refs(self.evidence_refs, "resolution requirement evidence")
        passed = set(self.required_semantic_input_ids).issubset(
            self.realized_semantic_input_ids
        )
        if (self.outcome == "pass") != passed:
            raise ValueError("resolution check outcome is not the exact semantic coverage")
        return self


class TargetReaderOutcome(StrictModel):
    primary_audience: AudienceKind
    benchmark_delta_reconstructible: bool
    operative_force_reconstructible: bool
    boundary_reconstructible: bool
    nearby_case_predictable: bool
    outcome: Literal["pass", "fail"]
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    explanation: ExplanatoryText

    @model_validator(mode="after")
    def _reader_outcome_is_noncompensatory(self) -> "TargetReaderOutcome":
        _unique_refs(self.evidence_refs, "target-reader outcome evidence")
        passed = all(
            (
                self.benchmark_delta_reconstructible,
                self.operative_force_reconstructible,
                self.boundary_reconstructible,
                self.nearby_case_predictable,
            )
        )
        if (self.outcome == "pass") != passed:
            raise ValueError("target-reader outcome is not the exact reader-test projection")
        return self


class CraftRealizationAssessment(ProfileCraftPayload):
    assessment_id: StableId
    selection_manifest_ref: EntityVersionRef
    selection_manifest_hash: Digest
    profile_stack_ref: EntityVersionRef
    profile_stack_hash: Digest
    reader_problem_diagnosis_ref: EntityVersionRef
    reader_problem_diagnosis_hash: Digest
    reader_path_ref: EntityVersionRef
    reader_path_hash: Digest
    result_contract_set_ref: EntityVersionRef
    result_contract_set_hash: Digest
    primary_audience: AudienceKind
    selected_move_refs: Annotated[
        tuple[StaticResourceRef, ...], Field(min_length=1)
    ]
    manuscript_unit_ref: EntityVersionRef
    manuscript_unit_hash: Digest
    manuscript_artifact_ref: ArtifactDependencyRef
    base_authoring_closure_ref: EntityVersionRef
    base_authoring_closure_hash: Digest
    formal_fidelity_review_ref: EntityVersionRef
    formal_fidelity_review_hash: Digest
    economic_reader_review_ref: EntityVersionRef
    economic_reader_review_hash: Digest
    cold_reader_review_ref: EntityVersionRef
    cold_reader_review_hash: Digest
    writer: Actor
    assessor: Actor
    move_realizations: Annotated[
        tuple[CraftMoveRealization, ...], Field(min_length=1)
    ]
    required_directive_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    directive_acceptance_checks: Annotated[
        tuple[DirectiveAcceptanceCheck, ...], Field(min_length=1)
    ]
    required_resolution_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    resolution_requirement_checks: Annotated[
        tuple[ResolutionRequirementCheck, ...], Field(min_length=1)
    ]
    target_reader_outcome: TargetReaderOutcome
    formal_fidelity_outcome: Literal["pass", "fail"]
    phrase_leak_audit_outcome: Literal["pass", "fail"]
    phrase_leak_audit_ref: ArtifactDependencyRef
    named_voice_imitation_outcome: Literal["pass", "fail"]
    empirical_template_contamination_outcome: Literal["pass", "fail"]
    outcome: Literal["pass", "revise", "reject"]
    assessed_at: NonEmptyString

    @model_validator(mode="after")
    def _realization_cannot_compensate_for_a_floor_failure(
        self,
    ) -> "CraftRealizationAssessment":
        if _actor_key(self.writer) == _actor_key(self.assessor):
            raise ValueError("craft realization requires an independent assessor")
        refs = tuple(item.move_ref for item in self.move_realizations)
        _unique(tuple((item.resource_id, item.version) for item in refs), "realized craft moves")
        if refs != self.selected_move_refs:
            raise ValueError("realization must assess every selected move in exact order")
        _unique(self.required_directive_ids, "assessment required directive IDs")
        _unique(self.required_resolution_ids, "assessment required resolution IDs")
        directive_ids = tuple(
            item.directive_id for item in self.directive_acceptance_checks
        )
        resolution_ids = tuple(
            item.requirement_id for item in self.resolution_requirement_checks
        )
        _unique(directive_ids, "assessment directive checks")
        _unique(resolution_ids, "assessment resolution checks")
        if directive_ids != self.required_directive_ids:
            raise ValueError("directive checks must cover every required directive in order")
        if resolution_ids != self.required_resolution_ids:
            raise ValueError("resolution checks must cover every diagnosis requirement in order")
        if self.target_reader_outcome.primary_audience != self.primary_audience:
            raise ValueError("target-reader outcome must use the exact primary audience")
        floors_pass = all(
            item == "pass"
            for item in (
                self.formal_fidelity_outcome,
                self.phrase_leak_audit_outcome,
                self.named_voice_imitation_outcome,
                self.empirical_template_contamination_outcome,
            )
        )
        moves_pass = all(
            item.realized_function
            and item.intended_reader_update_delivered
            and item.formal_fidelity_preserved
            for item in self.move_realizations
        )
        semantic_checks_pass = all(
            item.outcome == "pass" for item in self.directive_acceptance_checks
        ) and all(
            item.outcome == "pass" for item in self.resolution_requirement_checks
        )
        reader_pass = self.target_reader_outcome.outcome == "pass"
        if self.outcome == "pass" and not (
            floors_pass and moves_pass and semantic_checks_pass and reader_pass
        ):
            raise ValueError("craft success cannot compensate for a floor or fidelity failure")
        return self


PROFILE_CRAFT_READY_CHECK_ORDER: tuple[str, ...] = (
    "universal_floor",
    "overlay_conflicts",
    "theory_only_corpus",
    "functional_matched_contrast",
    "provenance_access_confidence",
    "copyright_and_voice",
    "predicate_mapping",
    "craft_realization",
    "target_reader_fit",
)


class ProfileCraftClosureCheck(StrictModel):
    check_id: StableId
    check_kind: Literal[
        "universal_floor",
        "overlay_conflicts",
        "theory_only_corpus",
        "functional_matched_contrast",
        "provenance_access_confidence",
        "copyright_and_voice",
        "predicate_mapping",
        "craft_realization",
        "target_reader_fit",
    ]
    outcome: Literal["pass", "fail"]
    evidence_refs: Annotated[tuple[ExactEvidenceRef, ...], Field(min_length=1)]
    explanation: ExplanatoryText


class ProfileCraftClosure(ProfileCraftPayload):
    closure_id: StableId
    base_authoring_closure_ref: EntityVersionRef
    base_authoring_closure_hash: Digest
    base_authoring_closure_outcome: Literal["authoring_ready"]
    manuscript_unit_ref: EntityVersionRef
    manuscript_unit_hash: Digest
    reader_problem_diagnosis_ref: EntityVersionRef
    reader_problem_diagnosis_hash: Digest
    profile_stack: ProjectPayloadBinding
    craft_selection: ProjectPayloadBinding
    predicate_mapping_audits: Annotated[
        tuple[ProjectPayloadBinding, ...], Field(min_length=1)
    ]
    predicate_mapping_coverage_classes: Annotated[
        tuple[Literal["exact", "partial", "diagnostic", "falsification_only"], ...],
        Field(min_length=1),
    ]
    predicate_limitation_kinds: tuple[PredicateLimitationKind, ...]
    realization_assessment: ProjectPayloadBinding
    source_state_revision: Digest
    all_dependencies_current_and_fresh: Literal[True]
    checks: Annotated[tuple[ProfileCraftClosureCheck, ...], Field(min_length=1)]
    outcome: Literal["ready", "blocked"]
    blocking_reasons: tuple[ExplanatoryText, ...] = ()
    determined_by: Actor
    determined_at: NonEmptyString

    @model_validator(mode="after")
    def _closure_is_noncompensatory(self) -> "ProfileCraftClosure":
        kinds = tuple(item.check_kind for item in self.checks)
        if kinds != PROFILE_CRAFT_READY_CHECK_ORDER:
            raise ValueError("profile/craft closure checks must be complete and ordered")
        _unique(tuple(item.check_id for item in self.checks), "profile/craft closure check IDs")
        _unique_refs(
            tuple(item.entity_ref for item in self.predicate_mapping_audits),
            "predicate mapping audit refs",
        )
        if len(self.predicate_mapping_coverage_classes) != len(
            self.predicate_mapping_audits
        ):
            raise ValueError(
                "predicate coverage classes must project every audit in audit order"
            )
        _unique(self.predicate_limitation_kinds, "closure predicate limitations")
        all_pass = all(item.outcome == "pass" for item in self.checks)
        if self.outcome == "ready" and (not all_pass or self.blocking_reasons):
            raise ValueError("a ready closure cannot compensate for any failed check")
        if self.outcome == "blocked" and (all_pass or not self.blocking_reasons):
            raise ValueError("a blocked closure requires a failed check and exact reason")
        return self


# ---------------------------------------------------------------------------
# Independent payload registry and envelope helpers


_FORMAL_TYPES = (ObligationPredicateContract, PredicateMappingAudit)
_EVIDENCE_TYPES = (CraftSourceCard, CraftMove, CraftCorpusRelease)
_PRESENTATION_TYPES = (
    ProfileLayerCard,
    ProfileCatalogRelease,
    TargetProfile,
    ResolvedProfileStack,
    ReaderProblemDiagnosis,
    CraftSelectionManifest,
    CraftRealizationAssessment,
)
_AUTHORITY_TYPES = (ProfileCraftClosure,)
_ALL_PAYLOAD_TYPES = (
    *_FORMAL_TYPES,
    *_EVIDENCE_TYPES,
    *_PRESENTATION_TYPES,
    *_AUTHORITY_TYPES,
)

PROFILE_CRAFT_PAYLOAD_MODELS: Mapping[str, type[ProfileCraftPayload]] = MappingProxyType(
    {model.__name__: model for model in _ALL_PAYLOAD_TYPES}
)
PROFILE_CRAFT_PAYLOAD_OWNER_FACETS: Mapping[str, Facet] = MappingProxyType(
    {
        **{model.__name__: "formal" for model in _FORMAL_TYPES},
        **{model.__name__: "literature_novelty" for model in _EVIDENCE_TYPES},
        **{
            model.__name__: "terminology_presentation"
            for model in _PRESENTATION_TYPES
        },
        **{model.__name__: "authority" for model in _AUTHORITY_TYPES},
    }
)


def profile_craft_schema_id(entity_type: str) -> str:
    if entity_type not in PROFILE_CRAFT_PAYLOAD_MODELS:
        raise ValueError(f"unregistered Phase 4 entity_type: {entity_type}")
    return f"econ_theorist.profile_craft/{entity_type}/v1"


def profile_craft_payload_entity_type(payload: ProfileCraftPayload) -> str:
    entity_type = type(payload).__name__
    if PROFILE_CRAFT_PAYLOAD_MODELS.get(entity_type) is not type(payload):
        raise ValueError(f"unregistered Phase 4 payload model: {entity_type}")
    return entity_type


def pack_profile_craft_payload(payload: ProfileCraftPayload) -> FacetPayloads:
    """Pack a registered Phase 4 payload without touching earlier registries."""

    entity_type = profile_craft_payload_entity_type(payload)
    owner = PROFILE_CRAFT_PAYLOAD_OWNER_FACETS[entity_type]
    facets: dict[str, object] = {
        "formal": {},
        "economic_interpretation": {},
        "literature_novelty": {},
        "terminology_presentation": {},
        "authority": {},
    }
    facets[owner] = {
        "schema": profile_craft_schema_id(entity_type),
        "payload": payload.model_dump(mode="json", exclude_none=False),
    }
    return FacetPayloads.model_validate(facets)


def parse_profile_craft_payload(
    entity_type: str, facets: FacetPayloads | Mapping[str, object]
) -> ProfileCraftPayload:
    """Parse only the independent Phase 4 profile/craft namespace."""

    model = PROFILE_CRAFT_PAYLOAD_MODELS.get(entity_type)
    if model is None:
        raise ValueError(f"unregistered Phase 4 entity_type: {entity_type}")
    if not isinstance(facets, FacetPayloads):
        facets = FacetPayloads.model_validate(facets)
    owner = PROFILE_CRAFT_PAYLOAD_OWNER_FACETS[entity_type]
    dumped = facets.model_dump(mode="python")
    for facet, value in dumped.items():
        if facet != owner and value != {}:
            raise ValueError(
                f"{entity_type} payload is owned by {owner}; facet {facet} must be empty"
            )
    wrapper = dumped[owner]
    if set(wrapper) != {"schema", "payload"}:
        raise ValueError("typed profile/craft facet must contain exactly schema and payload")
    expected_schema = profile_craft_schema_id(entity_type)
    if wrapper["schema"] != expected_schema:
        raise ValueError(f"typed profile/craft schema mismatch: expected {expected_schema}")
    payload_data = wrapper["payload"]
    if not isinstance(payload_data, dict):
        raise ValueError("typed profile/craft payload must be a JSON object")
    return model.model_validate_json(canonical_json_bytes(payload_data), strict=True)


def parse_profile_craft_entity(entity: EntityVersion) -> ProfileCraftPayload:
    return parse_profile_craft_payload(entity.entity_type, entity.facets)


def is_packed_profile_craft_entity(entity: EntityVersion) -> bool:
    owner = PROFILE_CRAFT_PAYLOAD_OWNER_FACETS.get(entity.entity_type)
    if owner is None:
        return False
    value = getattr(entity.facets, owner)
    return (
        isinstance(value, dict)
        and set(value) == {"schema", "payload"}
        and value.get("schema") == profile_craft_schema_id(entity.entity_type)
        and isinstance(value.get("payload"), dict)
    )


__all__ = [
    "PROFILE_CRAFT_PAYLOAD_MODELS",
    "PROFILE_CRAFT_PAYLOAD_OWNER_FACETS",
    "PROFILE_CRAFT_READY_CHECK_ORDER",
    "ARCHETYPE_DEPENDENT_SEMANTIC_INPUT_SELECTORS",
    "CraftCandidateAudit",
    "CraftCorpusRelease",
    "CraftMove",
    "CraftMoveRealization",
    "CraftRealizationAssessment",
    "CraftSelectionManifest",
    "CraftSourceCard",
    "DirectiveAcceptanceCheck",
    "DirectiveAcceptanceCriterion",
    "FindingCategory",
    "MoveRequirementCoverage",
    "ObligationPredicateContract",
    "PredicateClauseMapping",
    "PredicateMappingAudit",
    "PredicateMappingFinding",
    "PredicateMutationTest",
    "PredicateWitness",
    "ProfileCatalogRelease",
    "ProfileCraftClosure",
    "ProfileCraftClosureCheck",
    "ProfileCraftPayload",
    "ProfileDirective",
    "ProfileLayerCard",
    "ProjectPayloadBinding",
    "ReaderProblemDiagnosis",
    "ReaderProblemRule",
    "RepairAction",
    "ResolutionRequirement",
    "ResolutionRequirementCheck",
    "ResolvedDirective",
    "ResolvedProfileStack",
    "SelectedProfileLayerBinding",
    "SourceAdmissionAudit",
    "StaticResourceRef",
    "SemanticInputBinding",
    "SemanticInputSelector",
    "SemanticInputSourceKind",
    "SemanticInputSourceRule",
    "TYPED_EXTRACTOR_ARCHETYPES",
    "TypedExtractorArchetype",
    "SectionRole",
    "CausalClass",
    "TargetProfile",
    "TargetReaderOutcome",
    "is_packed_profile_craft_entity",
    "pack_profile_craft_payload",
    "parse_profile_craft_entity",
    "parse_profile_craft_payload",
    "profile_craft_payload_entity_type",
    "profile_craft_schema_id",
    "static_resource_ref",
    "semantic_input_selector_path",
]
