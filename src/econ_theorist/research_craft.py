"""Disabled development contracts for scholar-audited research moves.

This namespace is deliberately noncanonical and independent of Phase 4
``CraftMove`` resources.  It describes a source-audited development corpus and
function-only projections without registering a route, payload, WorkPacket,
selector, canonical entity, or package resource.
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Annotated, Literal, Mapping, TypeAlias

from pydantic import Field, field_validator, model_validator

from .codec import object_digest
from .models import Actor, Digest, NonEmptyString, StableId, StrictModel


PositiveInt: TypeAlias = Annotated[int, Field(ge=1)]
ExplanatoryText: TypeAlias = Annotated[str, Field(min_length=24)]
AuditDate: TypeAlias = Annotated[
    str, Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
]

SourceType: TypeAlias = Literal["method_essay", "published_paper"]
ClaimRelation: TypeAlias = Literal[
    "explicitly_stated",
    "inferred_reconstruction",
]
ResearchMode: TypeAlias = Literal[
    "pure_theory",
    "applied_theory",
    "theory_methodology",
    "empirical",
    "mixed_empirical",
]
EvidenceRole: TypeAlias = Literal["positive_anchor", "skeptical_contrast"]
CorpusSplit: TypeAlias = Literal["development", "evaluation_holdout"]
SourceSnapshotKind: TypeAlias = Literal[
    "author_or_institution_pdf",
    "official_publisher_pdf",
    "official_institution_page",
]
BiasFlag: TypeAlias = Literal[
    "retrospective_narration",
    "published_outcome_selection",
    "coauthor_cluster_dependence",
    "successful_case_selection",
    "single_source_method",
    "method_proposal_not_outcome_evidence",
    "rapidly_changing_tool_context",
    "historical_foundation",
    "domain_specific_transfer",
    "author_version_difference_possible",
    "intellectual_lineage_overlap",
]
RecencyTier: TypeAlias = Literal[
    "2022_2026",
    "2015_2021",
    "2010_2014",
    "2005_2009",
    "before_2005",
]
TransferConfidence: TypeAlias = Literal["low", "moderate", "high"]
SourceCuratorDecision: TypeAlias = Literal[
    "admit_disabled_development",
    "admit_contrast_disabled_development",
    "exclude",
]
SourceExclusionReason: TypeAlias = Literal[
    "empirical_or_mixed",
    "unverified_or_revoked_access",
    "evaluation_holdout",
    "duplicate_lineage",
    "copyright_audit_failed",
    "not_applicable",
]

ResearchRouteId: TypeAlias = Literal[
    "frame.question_and_benchmarks",
    "decompose.primitives",
    "tournament.mechanisms",
    "lab.micro_examples_and_ablations",
    "tournament.implementations",
    "discover.claims_and_boundaries",
    "audit.assumptions_generality_and_absorption",
]
LifecycleStage: TypeAlias = Literal[
    "framing",
    "primitive_decomposition",
    "mechanism_tournament",
    "micro_examples",
    "implementation_tournament",
    "claim_discovery",
    "absorption_audit",
]
ExistingOutputType: TypeAlias = Literal[
    "MechanismHypothesis",
    "PredictionRegister",
    "ExampleSuite",
    "FormalizationMap",
    "AssumptionMap",
    "ClaimGraph",
    "ProofObligation",
    "ClosestTheoryMap",
    "AbsorptionAssessment",
]
AdvisoryEvidenceKind: TypeAlias = Literal[
    "supports_continuation",
    "application_only_risk",
    "requires_human_approved_reframe",
    "unresolved_dependency",
]


_ROUTING_OUTCOMES = {
    "continue",
    "park",
    "kill",
    "new_brief_required",
}
_RECENCY_BY_YEAR: tuple[tuple[range, RecencyTier, int], ...] = (
    (range(2022, 10_000), "2022_2026", 1000),
    (range(2015, 2022), "2015_2021", 800),
    (range(2010, 2015), "2010_2014", 500),
    (range(2005, 2010), "2005_2009", 300),
    (range(0, 2005), "before_2005", 100),
)


def _unique(values: tuple[object, ...], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{label} must be unique")


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\w'-]+\b", value, flags=re.UNICODE))


def _expected_recency(year: int) -> tuple[RecencyTier, int]:
    for years, tier, weight in _RECENCY_BY_YEAR:
        if year in years:
            return tier, weight
    raise ValueError(f"unsupported publication year: {year}")


class ResearchCraftResource(StrictModel):
    """Base for static, noncanonical research-craft development resources."""

    schema_version: Literal[1] = 1


class ResearchSourceCard(ResearchCraftResource):
    source_id: StableId
    resource_version: PositiveInt
    title: NonEmptyString
    authors: Annotated[tuple[NonEmptyString, ...], Field(min_length=1)]
    publication_year: Annotated[int, Field(ge=1900, le=2100)]
    citation: NonEmptyString
    source_locator: NonEmptyString
    publication_locator: NonEmptyString | None = None
    source_snapshot_kind: SourceSnapshotKind
    source_snapshot_sha256: Digest
    source_snapshot_bytes: PositiveInt
    access_status: Literal["verified_public"] = "verified_public"
    accessed_at: AuditDate
    source_type: SourceType
    claim_relation: ClaimRelation
    research_mode: ResearchMode
    evidence_role: EvidenceRole
    corpus_split: CorpusSplit
    paper_family_id: StableId
    coauthor_cluster_id: StableId
    author_lineage_ids: Annotated[tuple[StableId, ...], Field(min_length=1)]
    recency_tier: RecencyTier
    recency_weight_milli: Literal[1000, 800, 500, 300, 100]
    bias_flags: Annotated[tuple[BiasFlag, ...], Field(min_length=1)]
    functional_summary: ExplanatoryText
    transferable_content: ExplanatoryText
    does_not_support: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    non_applicability: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    transfer_confidence: TransferConfidence
    curator_decision: SourceCuratorDecision
    contains_reusable_prose: Literal[False] = False
    writer_visibility: Literal["source_isolated"] = "source_isolated"
    voice_policy: Literal["functional_properties_only"] = (
        "functional_properties_only"
    )
    copyright_policy: Literal["hash_and_derived_function_only"] = (
        "hash_and_derived_function_only"
    )
    audited_by: Actor
    audited_at: NonEmptyString

    @field_validator(
        "authors",
        "author_lineage_ids",
        "bias_flags",
        "does_not_support",
        "non_applicability",
    )
    @classmethod
    def _tuple_values_are_unique(cls, value: tuple[object, ...]) -> tuple[object, ...]:
        _unique(value, "source tuple values")
        return value

    @model_validator(mode="after")
    def _source_semantics_are_bounded(self) -> "ResearchSourceCard":
        if not self.source_locator.startswith("https://"):
            raise ValueError("research source locator must use HTTPS")
        if (
            self.publication_locator is not None
            and not self.publication_locator.startswith("https://")
        ):
            raise ValueError("research publication locator must use HTTPS")
        expected_tier, expected_weight = _expected_recency(self.publication_year)
        if (
            self.recency_tier != expected_tier
            or self.recency_weight_milli != expected_weight
        ):
            raise ValueError("source recency tier does not match publication year")
        if self.publication_year > int(self.accessed_at[:4]):
            raise ValueError("research source publication year cannot be in the future")
        if self.source_type == "published_paper":
            if self.claim_relation != "inferred_reconstruction":
                raise ValueError(
                    "published-paper research moves are inferred reconstructions"
                )
            if "published_outcome_selection" not in self.bias_flags:
                raise ValueError(
                    "published-paper reconstructions require outcome-selection bias"
                )
        elif self.claim_relation != "explicitly_stated":
            raise ValueError("method essays must bind an explicitly stated method")
        if self.curator_decision == "exclude":
            return self
        if self.evidence_role == "skeptical_contrast" and self.curator_decision != (
            "admit_contrast_disabled_development"
        ):
            raise ValueError(
                "skeptical contrasts require the contrast curator decision"
            )
        if self.evidence_role == "positive_anchor" and self.curator_decision != (
            "admit_disabled_development"
        ):
            raise ValueError(
                "positive anchors require the development curator decision"
            )
        return self


class ResearchSourceRef(StrictModel):
    source_id: StableId
    version: PositiveInt
    content_hash: Digest


def research_source_ref(source: ResearchSourceCard) -> ResearchSourceRef:
    """Return an exact content-addressed reference to one source card."""

    return ResearchSourceRef(
        source_id=source.source_id,
        version=source.resource_version,
        content_hash=object_digest(source),
    )


class SourceAdmissionAudit(StrictModel):
    source_ref: ResearchSourceRef
    included_in_development: bool
    exclusion_reason: SourceExclusionReason | None = None

    @model_validator(mode="after")
    def _admission_is_coherent(self) -> "SourceAdmissionAudit":
        if self.included_in_development and self.exclusion_reason is not None:
            raise ValueError(
                "included research sources cannot have an exclusion reason"
            )
        if not self.included_in_development and self.exclusion_reason is None:
            raise ValueError("excluded research sources require an exclusion reason")
        return self


class ResearchEvidenceBinding(StrictModel):
    source_ref: ResearchSourceRef
    use_role: Literal["positive_anchor", "boundary", "skeptical_contrast"]


class ResearchMove(ResearchCraftResource):
    move_id: StableId
    resource_version: PositiveInt
    variant_id: StableId | None = None
    functional_name: NonEmptyString
    lifecycle_stages: Annotated[tuple[LifecycleStage, ...], Field(min_length=1)]
    compatible_route_ids: Annotated[
        tuple[ResearchRouteId, ...], Field(min_length=1)
    ]
    trigger_keys: Annotated[tuple[StableId, ...], Field(min_length=1)]
    trigger_conditions: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    operation_steps: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    required_semantic_inputs: Annotated[
        tuple[StableId, ...], Field(min_length=1)
    ]
    expected_existing_output_types: Annotated[
        tuple[ExistingOutputType, ...], Field(min_length=1)
    ]
    success_diagnostics: Annotated[
        tuple[ExplanatoryText, ...], Field(min_length=1)
    ]
    failure_modes: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    anti_patterns: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    non_applicability_keys: Annotated[
        tuple[StableId, ...], Field(min_length=1)
    ]
    non_applicability: Annotated[tuple[ExplanatoryText, ...], Field(min_length=1)]
    conflicting_move_ids: tuple[StableId, ...] = ()
    advisory_evidence_kinds: Annotated[
        tuple[AdvisoryEvidenceKind, ...], Field(min_length=1)
    ]
    evidence_bindings: Annotated[
        tuple[ResearchEvidenceBinding, ...], Field(min_length=2)
    ]
    transfer_confidence: TransferConfidence
    curator_decision: Literal["disabled_development_only"] = (
        "disabled_development_only"
    )
    runtime_projection: ExplanatoryText
    activation_status: Literal["development_disabled"] = "development_disabled"
    pilot_authorized: Literal[False] = False
    automatic_selection_authorized: Literal[False] = False
    canonical_write_authorized: Literal[False] = False
    source_identities_visible_to_generator: Literal[False] = False
    source_phrase_material_included: Literal[False] = False
    route_disposition_authority: Literal[False] = False
    created_by: Actor
    created_at: NonEmptyString

    @field_validator(
        "lifecycle_stages",
        "compatible_route_ids",
        "trigger_keys",
        "trigger_conditions",
        "operation_steps",
        "required_semantic_inputs",
        "expected_existing_output_types",
        "success_diagnostics",
        "failure_modes",
        "anti_patterns",
        "non_applicability_keys",
        "non_applicability",
        "conflicting_move_ids",
        "advisory_evidence_kinds",
    )
    @classmethod
    def _move_tuple_values_are_unique(
        cls, value: tuple[object, ...]
    ) -> tuple[object, ...]:
        _unique(value, "research move tuple values")
        return value

    @field_validator("evidence_bindings")
    @classmethod
    def _evidence_bindings_are_unique(
        cls, value: tuple[ResearchEvidenceBinding, ...]
    ) -> tuple[ResearchEvidenceBinding, ...]:
        keys = tuple(
            (
                item.source_ref.source_id,
                item.source_ref.version,
                item.source_ref.content_hash,
                item.use_role,
            )
            for item in value
        )
        _unique(keys, "research move evidence bindings")
        return value

    @field_validator("runtime_projection")
    @classmethod
    def _runtime_projection_is_compact_and_advisory(cls, value: str) -> str:
        words = _word_count(value)
        if words < 80 or words > 120:
            raise ValueError("runtime research-move projection must be 80--120 words")
        lowered = value.casefold()
        if "http://" in lowered or "https://" in lowered or "doi:" in lowered:
            raise ValueError("runtime projection cannot expose source locators")
        tokens = set(re.findall(r"[a-z_]+", lowered))
        if tokens.intersection(_ROUTING_OUTCOMES):
            raise ValueError("runtime projection cannot emit route outcomes")
        return value


class ResearchCorpusRelease(ResearchCraftResource):
    release_id: StableId
    resource_version: PositiveInt
    release_status: Literal["development_disabled"] = "development_disabled"
    source_audit_status: Literal["passed_with_boundaries"] = (
        "passed_with_boundaries"
    )
    source_audit_report_path: NonEmptyString
    source_audit_report_sha256: Digest
    source_cards: Annotated[
        tuple[ResearchSourceCard, ...], Field(min_length=1)
    ]
    source_admission_audits: Annotated[
        tuple[SourceAdmissionAudit, ...], Field(min_length=1)
    ]
    moves: Annotated[tuple[ResearchMove, ...], Field(min_length=1)]
    evaluation_holdouts_included: Literal[False] = False
    production_package_resource: Literal[False] = False
    runtime_selector_present: Literal[False] = False
    pilot_authorized: Literal[False] = False
    automatic_selection_authorized: Literal[False] = False
    canonical_write_authorized: Literal[False] = False
    source_snapshot_retention: Literal[
        "hash_only_no_copyrighted_source_bytes"
    ] = "hash_only_no_copyrighted_source_bytes"
    runtime_projection_policy: Literal[
        "function_only_80_120_words_source_isolated"
    ] = "function_only_80_120_words_source_isolated"
    opt_in_pilot_requires_separate_human_authorization: Literal[True] = True
    default_activation_requires_held_out_replication: Literal[True] = True
    default_activation_requires_end_to_end_pilot: Literal[True] = True
    development_authorized_by: Actor
    curated_by: Actor
    released_at: NonEmptyString

    @model_validator(mode="after")
    def _release_is_source_bound_and_disabled(self) -> "ResearchCorpusRelease":
        source_ids = tuple(
            (item.source_id, item.resource_version) for item in self.source_cards
        )
        _unique(source_ids, "research source revisions")
        move_ids = tuple((item.move_id, item.resource_version) for item in self.moves)
        _unique(move_ids, "research move revisions")

        source_by_ref = {
            (
                ref.source_id,
                ref.version,
                ref.content_hash,
            ): source
            for source in self.source_cards
            for ref in (research_source_ref(source),)
        }
        audit_keys = tuple(
            (
                item.source_ref.source_id,
                item.source_ref.version,
                item.source_ref.content_hash,
            )
            for item in self.source_admission_audits
        )
        _unique(audit_keys, "research source admission audits")
        if set(audit_keys) != set(source_by_ref):
            raise ValueError("every research source requires one exact admission audit")

        included_refs = {
            (
                item.source_ref.source_id,
                item.source_ref.version,
                item.source_ref.content_hash,
            )
            for item in self.source_admission_audits
            if item.included_in_development
        }
        for key in included_refs:
            source = source_by_ref[key]
            if source.research_mode in {"empirical", "mixed_empirical"}:
                raise ValueError(
                    "empirical or mixed sources cannot enter research-move development"
                )
            if source.corpus_split == "evaluation_holdout":
                raise ValueError(
                    "evaluation holdouts cannot enter research-move development"
                )
            if source.curator_decision == "exclude":
                raise ValueError("excluded sources cannot enter development")

        referenced: set[tuple[str, int, str]] = set()
        author_tokens = {
            token.casefold()
            for source in self.source_cards
            for author in source.authors
            for token in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+", author)
            if len(token) >= 3
        }
        for move in self.moves:
            positive_sources: list[ResearchSourceCard] = []
            for binding in move.evidence_bindings:
                key = (
                    binding.source_ref.source_id,
                    binding.source_ref.version,
                    binding.source_ref.content_hash,
                )
                source = source_by_ref.get(key)
                if source is None or key not in included_refs:
                    raise ValueError(
                        "research move evidence must bind an admitted exact source"
                    )
                referenced.add(key)
                if binding.use_role == "positive_anchor":
                    if source.evidence_role != "positive_anchor":
                        raise ValueError(
                            "positive evidence must bind a positive source card"
                        )
                    positive_sources.append(source)
                elif binding.use_role == "skeptical_contrast":
                    if source.evidence_role != "skeptical_contrast":
                        raise ValueError(
                            "skeptical evidence must bind a contrast source card"
                        )

            positive_families = {
                source.paper_family_id for source in positive_sources
            }
            positive_clusters = {
                source.coauthor_cluster_id for source in positive_sources
            }
            positive_lineages: set[str] = set()
            for source in positive_sources:
                overlap = positive_lineages.intersection(source.author_lineage_ids)
                if overlap:
                    raise ValueError(
                        "positive research sources cannot reuse an author lineage"
                    )
                positive_lineages.update(source.author_lineage_ids)
            if (
                len(positive_sources) < 2
                or len(positive_families) < 2
                or len(positive_clusters) < 2
            ):
                raise ValueError(
                    "each research move requires two independent positive "
                    "paper families and coauthor clusters"
                )
            has_explicit_method = any(
                source.source_type == "method_essay"
                and source.claim_relation == "explicitly_stated"
                for source in positive_sources
            )
            inferred_paper_groups = {
                (source.paper_family_id, source.coauthor_cluster_id)
                for source in positive_sources
                if source.source_type == "published_paper"
                and source.claim_relation == "inferred_reconstruction"
            }
            if not (
                (has_explicit_method and inferred_paper_groups)
                or len(inferred_paper_groups) >= 2
            ):
                raise ValueError(
                    "research move evidence requires method-plus-paper or two "
                    "independent paper reconstructions"
                )

            projection_tokens = {
                token.casefold()
                for token in re.findall(
                    r"[A-Za-zÀ-ÖØ-öø-ÿ'-]+",
                    move.runtime_projection,
                )
            }
            leaked = sorted(author_tokens.intersection(projection_tokens))
            if leaked:
                raise ValueError(
                    "function-only projection leaks source identity: "
                    + ", ".join(leaked)
                )

        if referenced != included_refs:
            raise ValueError(
                "every admitted development source must support or bound a move"
            )
        return self


RESEARCH_CRAFT_RESOURCE_MODELS: Mapping[str, type[StrictModel]] = MappingProxyType(
    {
        "ResearchSourceCard": ResearchSourceCard,
        "ResearchMove": ResearchMove,
        "ResearchCorpusRelease": ResearchCorpusRelease,
    }
)


__all__ = [
    "RESEARCH_CRAFT_RESOURCE_MODELS",
    "ResearchCorpusRelease",
    "ResearchEvidenceBinding",
    "ResearchMove",
    "ResearchSourceCard",
    "ResearchSourceRef",
    "SourceAdmissionAudit",
    "research_source_ref",
]
