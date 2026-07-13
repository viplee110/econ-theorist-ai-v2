"""Pinned Phase 4 catalogs plus deterministic resolution and retrieval."""

from __future__ import annotations

from functools import lru_cache
from itertools import combinations
from pathlib import Path
from typing import Any

from .codec import canonical_json_bytes, object_digest, sha256_digest
from .distribution_resources import (
    DistributionResourceError,
    installed_resource_root,
)
from .models import Actor, EntityVersionRef
from .profile_craft import (
    CraftCandidateAudit,
    CraftCorpusRelease,
    MoveRequirementCoverage,
    CraftSelectionManifest,
    ARCHETYPE_DEPENDENT_SEMANTIC_INPUT_SELECTORS,
    ProfileCatalogRelease,
    ReaderProblemDiagnosis,
    ResolvedDirective,
    ResolvedProfileStack,
    SelectedProfileLayerBinding,
    StaticResourceRef,
    TYPED_EXTRACTOR_ARCHETYPES,
    TargetProfile,
    static_resource_ref,
)


PROFILE_CATALOG_V1_HASH = (
    "f5959f8ba50f3ef2e8fac52d0af3465a361778fb1a79f6c83e5af91ce8e48158"
)
CRAFT_CORPUS_V1_HASH = (
    "468571238038771dfd84ccc27fc9efcb9b562bdf887a49592701e3c33b8f813b"
)
PROFILE_RESOLVER_VERSION = "profile.resolver.precedence.v2"
CRAFT_SELECTOR_VERSION = "craft.selector.semantic_set_cover.v2"


_SCIENTIFIC_EFFECT_SCOPES = {
    "formal_truth",
    "scientific_claim",
    "discovery",
    "economic_interpretation",
}
_THEORY_RESEARCH_MODES = {
    "pure_theory",
    "applied_theory",
    "theory_methodology",
}
_ADMISSIBLE_SOURCE_ACCESS = {
    "verified_public",
    "verified_licensed",
    "project_owned",
    "restricted_private",
}


class ProfileCraftPolicyError(ValueError):
    """A static catalog or deterministic projection violates Phase 4 policy."""


def _directive_semantics(directive) -> bytes:
    """Canonical directive meaning, excluding its bookkeeping identity."""

    return canonical_json_bytes(
        directive.model_dump(
            mode="json",
            exclude={"directive_id", "conflict_key"},
        )
    )


def _validate_profile_catalog_policy(catalog: ProfileCatalogRelease) -> None:
    """Fail closed on catalog shapes not guaranteed by the payload schema."""

    selection_keys: set[tuple[str, str]] = set()
    for card in catalog.cards:
        key = (card.layer_kind, card.selection_key)
        if key in selection_keys:
            raise ProfileCraftPolicyError(
                "profile catalog has an ambiguous layer selection: "
                f"{card.layer_kind}/{card.selection_key}"
            )
        selection_keys.add(key)
        if card.layer_kind == "universal_floor":
            for directive in card.directives:
                if (
                    directive.effect_scope in _SCIENTIFIC_EFFECT_SCOPES
                    and directive.directive_kind != "preserve_floor"
                ):
                    raise ProfileCraftPolicyError(
                        "a universal-floor scientific directive must preserve, "
                        "not create or alter, canonical science"
                    )


def _validate_craft_corpus_policy(corpus: CraftCorpusRelease) -> None:
    """Apply static theory, provenance, and evidence-independence gates."""

    anchor_lineages: set[str] = set()
    for source in corpus.source_cards:
        if source.research_mode not in _THEORY_RESEARCH_MODES:
            raise ProfileCraftPolicyError(
                "empirical or mixed-empirical sources cannot enter the core craft corpus"
            )
        if source.access_status not in _ADMISSIBLE_SOURCE_ACCESS:
            raise ProfileCraftPolicyError(
                "unverified or revoked sources cannot enter the core craft corpus"
            )
        if source.corpus_split == "evaluation_holdout":
            raise ProfileCraftPolicyError(
                "evaluation holdouts cannot enter the core craft corpus"
            )
        if source.evidence_role == "matched_anchor":
            lineages = set(source.author_lineage_ids)
            if anchor_lineages.intersection(lineages):
                raise ProfileCraftPolicyError(
                    "core matched anchors must not overlap in author lineage"
                )
            anchor_lineages.update(lineages)

    by_ref = {static_resource_ref(source): source for source in corpus.source_cards}
    rules = {item.problem_key: item for item in corpus.reader_problem_rules}
    if len(rules) != len(corpus.reader_problem_rules):
        raise ProfileCraftPolicyError("reader-problem rules must be unique")
    for move in corpus.moves:
        rule = rules.get(move.reader_problem_key)
        if rule is None:
            raise ProfileCraftPolicyError(
                "each craft move requires one exact reader-problem rule"
            )
        if not set(move.supported_repair_actions).issubset(
            rule.accepted_repair_actions
        ) or not set(move.required_semantic_inputs).issubset(
            rule.required_semantic_input_ids
        ):
            raise ProfileCraftPolicyError(
                "craft move semantics exceed its exact reader-problem rule"
            )
        typed_archetype_selectors = {
            source_rule.selector
            for source_rule in rule.semantic_input_source_rules
            if source_rule.selector
            in ARCHETYPE_DEPENDENT_SEMANTIC_INPUT_SELECTORS
        }
        if typed_archetype_selectors and not set(
            move.compatible_archetypes
        ).issubset(TYPED_EXTRACTOR_ARCHETYPES):
            raise ProfileCraftPolicyError(
                "craft move declares an archetype unsupported by its typed extractors"
            )
        try:
            anchors = tuple(by_ref[ref] for ref in move.matched_anchor_refs)
            contrasts = tuple(by_ref[ref] for ref in move.contrast_refs)
        except KeyError as exc:
            raise ProfileCraftPolicyError(
                "craft move cites evidence outside its pinned core release"
            ) from exc
        if any(source.evidence_role != "matched_anchor" for source in anchors):
            raise ProfileCraftPolicyError(
                "matched-anchor refs must resolve to matched-anchor sources"
            )
        if any(source.evidence_role != "contrast" for source in contrasts):
            raise ProfileCraftPolicyError(
                "contrast refs must resolve to contrast sources"
            )
        if any(
            source.function_key != move.function_key
            or source.reader_problem_key != move.reader_problem_key
            for source in (*anchors, *contrasts)
        ):
            raise ProfileCraftPolicyError(
                "craft evidence must match the move's reader problem and function"
            )
        if move.confidence not in {"supported", "strong"}:
            continue
        if len(anchors) < 2 or not contrasts:
            raise ProfileCraftPolicyError(
                "supported craft moves require two independent anchors and a contrast"
            )
        families = tuple(source.paper_family_id for source in anchors)
        if len(set(families)) != len(families):
            raise ProfileCraftPolicyError(
                "matched anchors must come from distinct paper families"
            )
        seen_lineages: set[str] = set()
        for source in anchors:
            lineages = set(source.author_lineage_ids)
            if seen_lineages.intersection(lineages):
                raise ProfileCraftPolicyError(
                    "matched anchors must not overlap in author lineage"
                )
            seen_lineages.update(lineages)


def _source_resource(path: str) -> Path:
    root = Path(__file__).resolve().parents[2]
    candidate = root / path
    if candidate.is_file():
        return candidate
    try:
        installed = installed_resource_root() / Path(path)
    except DistributionResourceError as exc:
        raise ProfileCraftPolicyError(
            f"cannot locate Phase 4 static resource: {path}"
        ) from exc
    if not installed.is_file():
        raise ProfileCraftPolicyError(
            f"installed Phase 4 static resource is missing: {installed}"
        )
    return installed


def _load_exact(path: str, model, expected_hash: str):
    source = _source_resource(path)
    try:
        data = source.read_bytes()
        value = model.model_validate_json(data, strict=True)
    except (OSError, ValueError) as exc:
        raise ProfileCraftPolicyError(f"invalid Phase 4 resource: {source}") from exc
    if canonical_json_bytes(value) != data:
        raise ProfileCraftPolicyError(f"Phase 4 resource is not canonical JSON: {source}")
    if sha256_digest(data) != expected_hash or object_digest(value) != expected_hash:
        raise ProfileCraftPolicyError(f"Phase 4 resource hash mismatch: {source}")
    return value


@lru_cache(maxsize=1)
def load_profile_catalog() -> ProfileCatalogRelease:
    catalog = _load_exact(
        "profiles/catalog.v1.json",
        ProfileCatalogRelease,
        PROFILE_CATALOG_V1_HASH,
    )
    _validate_profile_catalog_policy(catalog)
    return catalog


@lru_cache(maxsize=1)
def load_craft_corpus() -> CraftCorpusRelease:
    corpus = _load_exact(
        "craft/corpus.v1.json",
        CraftCorpusRelease,
        CRAFT_CORPUS_V1_HASH,
    )
    _validate_craft_corpus_policy(corpus)
    evidence_files = {
        "craft.source.kamenica_gentzkow_2011.benchmark": (
            "craft/evidence/kamenica_gentzkow_2011.metadata.json"
        ),
        "craft.source.varian_1997.benchmark": (
            "craft/evidence/varian_1997_model_building.metadata.json"
        ),
        "craft.source.synthetic_formal_first_contrast": (
            "craft/evidence/synthetic_formal_first_contrast.md"
        ),
        "craft.source.synthetic_empirical_decoy": (
            "craft/evidence/synthetic_empirical_decoy.md"
        ),
    }
    for admission in corpus.source_admission_audits:
        source = admission.source
        path = evidence_files.get(source.source_card_id)
        if path is None:
            raise ProfileCraftPolicyError(
                f"core craft source lacks packaged evidence: {source.source_card_id}"
            )
        digest = sha256_digest(_source_resource(path).read_bytes())
        if (
            source.access_evidence_ref.content_hash != digest
            or source.phrase_audit_ref.content_hash != digest
        ):
            raise ProfileCraftPolicyError(
                f"craft source evidence hash mismatch: {source.source_card_id}"
            )
        if source.source_locator.startswith("repo:") and source.source_content_hash != digest:
            raise ProfileCraftPolicyError(
                f"project-owned source content hash mismatch: {source.source_card_id}"
            )
    return corpus


_PRECEDENCE = {
    "universal_floor": 2,
    "theory_mode": 4,
    "ambition": 4,
    "archetype": 5,
    "field": 6,
    "audience": 7,
    "venue_overlay": 8,
    "submission_constraint": 9,
}


def _intrinsic_directive_rejection(
    card,
    directive,
    *,
    floor_conflicts: set[str],
) -> str | None:
    """Return a rejection that does not depend on another non-floor claim."""

    if card.status != "active":
        return "inactive_or_provisional_source"
    if card.layer_kind == "venue_overlay":
        if directive.conflict_key in floor_conflicts:
            return "universal_floor_conflict"
        if directive.directive_kind == "hard_template":
            return "hard_venue_template"
        if directive.directive_kind == "imitate_voice":
            return "named_voice_imitation"
        if directive.directive_kind == "suppress_boundary":
            return "boundary_suppression"
        if directive.effect_scope in {
            *_SCIENTIFIC_EFFECT_SCOPES,
            "economic_interpretation",
        } or directive.strength != "soft":
            return "forbidden_scientific_effect"
        if card.confidence == "provisional":
            return "inactive_or_provisional_source"
        return None
    if (
        directive.effect_scope in _SCIENTIFIC_EFFECT_SCOPES
        and not (
            card.layer_kind == "universal_floor"
            and directive.directive_kind == "preserve_floor"
        )
    ):
        return "forbidden_scientific_effect"
    return None


def resolve_profile_stack(
    target: TargetProfile,
    *,
    target_profile_ref: EntityVersionRef,
    source_state_revision: str,
    resolved_by: Actor,
    resolved_at: str,
    catalog: ProfileCatalogRelease | None = None,
) -> ResolvedProfileStack:
    """Resolve one human target with explicit precedence and rejection records."""

    active_catalog = catalog or load_profile_catalog()
    _validate_profile_catalog_policy(active_catalog)
    catalog_ref = static_resource_ref(active_catalog)
    if target.catalog_release_ref != catalog_ref:
        raise ProfileCraftPolicyError("target binds another profile catalog release")
    cards = active_catalog.cards
    by_key = {(card.layer_kind, card.selection_key): card for card in cards}
    floors = [card for card in cards if card.layer_kind == "universal_floor"]
    if len(floors) != 1:
        raise ProfileCraftPolicyError("profile catalog has no unique universal floor")
    selected = [floors[0]]
    for layer_kind, selection_key in (
        ("theory_mode", target.theory_mode),
        ("ambition", target.ambition),
        ("archetype", target.primary_archetype),
        ("field", target.field_key),
        ("audience", target.primary_audience),
    ):
        card = by_key.get((layer_kind, selection_key))
        if card is None:
            raise ProfileCraftPolicyError(
                f"catalog lacks selected {layer_kind}: {selection_key}"
            )
        selected.append(card)
    if target.venue_overlay_ref is not None:
        matches = [
            card
            for card in cards
            if static_resource_ref(card) == target.venue_overlay_ref
            and card.layer_kind == "venue_overlay"
        ]
        if len(matches) != 1:
            raise ProfileCraftPolicyError("selected venue overlay is not in the catalog")
        selected.extend(matches)
    for constraint_ref in target.submission_constraint_refs:
        matches = [
            card
            for card in cards
            if static_resource_ref(card) == constraint_ref
            and card.layer_kind == "submission_constraint"
        ]
        if len(matches) != 1:
            raise ProfileCraftPolicyError(
                "selected submission constraint is not in the catalog"
            )
        selected.extend(matches)

    floor_conflicts = {
        directive.conflict_key for directive in floors[0].directives
    }
    ordered_directives = tuple(
        (card, item, _PRECEDENCE[card.layer_kind])
        for card in sorted(
            selected,
            key=lambda item: (_PRECEDENCE[item.layer_kind], item.layer_id),
        )
        for item in card.directives
    )
    reasons: list[str | None] = [
        _intrinsic_directive_rejection(
            card,
            item,
            floor_conflicts=floor_conflicts,
        )
        for card, item, _ in ordered_directives
    ]
    by_conflict: dict[str, list[int]] = {}
    for index, (_, item, _) in enumerate(ordered_directives):
        if reasons[index] is None:
            by_conflict.setdefault(item.conflict_key, []).append(index)

    for conflict_key, indices in by_conflict.items():
        floor_indices = [
            index
            for index in indices
            if ordered_directives[index][0].layer_kind == "universal_floor"
        ]
        if floor_indices:
            floor_semantics = {
                _directive_semantics(ordered_directives[index][1])
                for index in floor_indices
            }
            if len(floor_semantics) != 1:
                raise ProfileCraftPolicyError(
                    "unresolved equal-precedence profile conflict for "
                    f"{conflict_key}"
                )
            for index in indices:
                if index not in floor_indices:
                    reasons[index] = "universal_floor_conflict"
            continue

        winning_precedence = max(
            ordered_directives[index][2] for index in indices
        )
        winning_indices = [
            index
            for index in indices
            if ordered_directives[index][2] == winning_precedence
        ]
        winning_semantics = {
            _directive_semantics(ordered_directives[index][1])
            for index in winning_indices
        }
        if len(winning_semantics) != 1:
            raise ProfileCraftPolicyError(
                "unresolved equal-precedence profile conflict for "
                f"{conflict_key}"
            )
        for index in indices:
            if index not in winning_indices:
                reasons[index] = "lower_precedence_conflict"

    resolutions: list[ResolvedDirective] = []
    for (card, item, precedence), reason in zip(ordered_directives, reasons):
        outcome = "rejected" if reason is not None else "active"
        resolutions.append(
            ResolvedDirective(
                source_card_ref=static_resource_ref(card),
                source_layer_kind=card.layer_kind,
                directive=item,
                precedence=precedence,
                outcome=outcome,
                rejection_reason=reason,
            )
        )
    requirements = tuple(
        item.directive.directive_id
        for item in resolutions
        if item.outcome == "active" and item.directive.strength != "soft"
    )
    preferences = tuple(
        item.directive.directive_id
        for item in resolutions
        if item.outcome == "active" and item.directive.strength == "soft"
    )
    return ResolvedProfileStack(
        stack_id=f"profile.stack.{target.target_profile_id}",
        target_profile_ref=target_profile_ref,
        target_profile_hash=object_digest(target),
        catalog_release_ref=catalog_ref,
        selected_layers=tuple(
            SelectedProfileLayerBinding(
                layer_ref=static_resource_ref(card),
                layer_kind=card.layer_kind,
                selection_key=card.selection_key,
                source_status=card.status,
            )
            for card in selected
        ),
        directive_resolutions=tuple(resolutions),
        active_requirements=requirements,
        active_soft_preferences=preferences,
        source_state_revision=source_state_revision,
        resolver_version=PROFILE_RESOLVER_VERSION,
        resolved_by=resolved_by,
        resolved_at=resolved_at,
    )


def select_craft_moves(
    diagnosis: ReaderProblemDiagnosis,
    *,
    diagnosis_ref: EntityVersionRef,
    profile_stack: ResolvedProfileStack,
    profile_stack_ref: EntityVersionRef,
    selected_by: Actor,
    selected_at: str,
    corpus: CraftCorpusRelease | None = None,
) -> CraftSelectionManifest:
    """Recompute typed eligibility and the deterministic minimum set cover."""

    active_corpus = corpus or load_craft_corpus()
    _validate_craft_corpus_policy(active_corpus)
    if diagnosis.profile_stack_ref != profile_stack_ref:
        raise ProfileCraftPolicyError(
            "diagnosis is bound to another resolved profile stack"
        )
    if diagnosis.profile_stack_hash != object_digest(profile_stack):
        raise ProfileCraftPolicyError(
            "diagnosis profile-stack hash does not match the selected stack"
        )
    layer_values = {
        item.layer_kind: item.selection_key for item in profile_stack.selected_layers
    }
    theory_mode = layer_values["theory_mode"]
    archetype = layer_values["archetype"]
    field_key = layer_values["field"]
    audience = layer_values["audience"]
    matching_rules = tuple(
        item
        for item in active_corpus.reader_problem_rules
        if item.problem_key == diagnosis.reader_problem_key
    )
    if len(matching_rules) != 1:
        raise ProfileCraftPolicyError(
            "diagnosis requires one exact reader-problem rule in the pinned corpus"
        )
    problem_rule = matching_rules[0]
    if not set(diagnosis.diagnostic_categories).issubset(
        problem_rule.accepted_finding_categories
    ):
        raise ProfileCraftPolicyError(
            "diagnosis includes a finding category outside its exact problem rule"
        )
    diagnosis_actions = {
        item.action for item in diagnosis.resolution_requirements
    }
    if not diagnosis_actions.issubset(problem_rule.accepted_repair_actions):
        raise ProfileCraftPolicyError(
            "diagnosis includes a repair action outside its exact problem rule"
        )
    if set(diagnosis.required_semantic_input_ids) != set(
        problem_rule.required_semantic_input_ids
    ):
        raise ProfileCraftPolicyError(
            "diagnosis semantic inputs do not equal its exact problem-rule contract"
        )
    diagnosis_nonapplicable = (
        diagnosis.upstream_science_status == "unresolved"
        or not diagnosis.craft_eligible
    )
    available_inputs = {
        item.input_id
        for item in diagnosis.semantic_input_bindings
        if item.availability == "available"
    }
    provisional: list[dict[str, Any]] = []
    core_refs = {static_resource_ref(move) for move in active_corpus.moves}
    for index, move in enumerate(active_corpus.moves, start=1):
        move_ref = static_resource_ref(move)
        functional = (
            "exact"
            if move.reader_problem_key == diagnosis.reader_problem_key
            else "mismatch"
        )
        semantic = set(move.required_semantic_inputs).issubset(available_inputs)
        archetype_ok = archetype in move.compatible_archetypes
        audience_ok = audience in move.compatible_audiences
        theory_ok = theory_mode in move.compatible_theory_modes
        field_ok = field_key in move.compatible_field_keys
        placement_ok = bool(
            set(diagnosis.affected_section_roles).intersection(
                move.eligible_section_roles
            )
        )
        causal_ok = (
            diagnosis.causal_class in move.compatible_causal_classes
            and diagnosis.causal_class in problem_rule.allowed_causal_classes
        )
        triggered: list[str] = []
        rule_ids = set(move.non_applicability_rule_ids)
        for condition, rule_id in (
            (
                diagnosis.upstream_science_status == "unresolved",
                "upstream_science_unresolved",
            ),
            (not causal_ok, "nonlocal_causal_class"),
            (not semantic, "semantic_inputs_unavailable"),
            (not theory_ok, "theory_mode_incompatible"),
            (not field_ok, "field_incompatible"),
            (not placement_ok, "section_role_incompatible"),
        ):
            if condition and rule_id in rule_ids:
                triggered.append(rule_id)
        nonapplicable = bool(triggered)
        corpus_ok = move_ref in core_refs
        confidence_ok = move.confidence in {"supported", "strong"}
        coverages = []
        for requirement in diagnosis.resolution_requirements:
            required = set(requirement.required_semantic_input_ids)
            usable = required.intersection(available_inputs).intersection(
                move.required_semantic_inputs
            )
            missing = required - usable
            action_supported = requirement.action in move.supported_repair_actions
            coverages.append(
                MoveRequirementCoverage(
                    requirement_id=requirement.requirement_id,
                    repair_action=requirement.action,
                    required_semantic_input_ids=requirement.required_semantic_input_ids,
                    available_semantic_input_ids=tuple(
                        item
                        for item in requirement.required_semantic_input_ids
                        if item in usable
                    ),
                    missing_semantic_input_ids=tuple(
                        item
                        for item in requirement.required_semantic_input_ids
                        if item in missing
                    ),
                    action_supported=action_supported,
                    semantic_inputs_available=not missing,
                    covered=action_supported and not missing,
                )
            )
        covered_ids = tuple(
            item.requirement_id for item in coverages if item.covered
        )
        eligible = all(
            (
                functional == "exact",
                semantic,
                archetype_ok,
                audience_ok,
                theory_ok,
                field_ok,
                placement_ok,
                causal_ok,
                not nonapplicable,
                corpus_ok,
                confidence_ok,
                bool(move.contrast_refs),
                bool(covered_ids),
            )
        )
        provisional.append(
            {
                "move_ref": move_ref,
                "move": move,
                "functional_match": functional,
                "semantic_inputs_present": semantic,
                "archetype_compatible": archetype_ok,
                "audience_compatible": audience_ok,
                "theory_mode_compatible": theory_ok,
                "field_compatible": field_ok,
                "placement_compatible": placement_ok,
                "causal_class_compatible": causal_ok,
                "non_applicability_triggered": nonapplicable,
                "triggered_non_applicability_rule_ids": tuple(triggered),
                "corpus_admissible": corpus_ok,
                "confidence_admissible": confidence_ok,
                "lexical_similarity_rank": index,
                "requirement_coverages": tuple(coverages),
                "covered_requirement_ids": covered_ids,
                "eligible": eligible,
            }
        )
    required_resolutions = set(diagnosis.required_resolution_ids)
    eligible_indices = tuple(
        index for index, values in enumerate(provisional) if values["eligible"]
    )
    selected_indices: set[int] = set()
    if not diagnosis_nonapplicable:
        winning: tuple[tuple[str, ...], tuple[int, ...]] | None = None
        for cardinality in range(1, len(eligible_indices) + 1):
            options = []
            for group in combinations(eligible_indices, cardinality):
                coverage = set().union(
                    *(set(provisional[index]["covered_requirement_ids"]) for index in group)
                )
                if coverage == required_resolutions:
                    move_ids = tuple(
                        sorted(provisional[index]["move"].move_id for index in group)
                    )
                    options.append((move_ids, group))
            if options:
                winning = min(options, key=lambda item: item[0])
                break
        if winning is not None:
            selected_indices = set(winning[1])
    candidates: list[CraftCandidateAudit] = []
    for index, values in enumerate(provisional):
        eligible = values.pop("eligible")
        selected = index in selected_indices
        if selected:
            reason = None
        elif diagnosis_nonapplicable:
            reason = "non_applicable"
        elif values["functional_match"] != "exact":
            reason = "function_mismatch"
        elif not values["semantic_inputs_present"]:
            reason = "missing_semantic_inputs"
        elif not values["archetype_compatible"]:
            reason = "archetype_mismatch"
        elif not values["audience_compatible"]:
            reason = "audience_mismatch"
        elif not values["theory_mode_compatible"]:
            reason = "theory_mode_mismatch"
        elif not values["field_compatible"]:
            reason = "field_mismatch"
        elif not values["placement_compatible"]:
            reason = "placement_mismatch"
        elif not values["causal_class_compatible"]:
            reason = "causal_class_mismatch"
        elif values["non_applicability_triggered"]:
            reason = "non_applicable"
        elif not values["corpus_admissible"]:
            reason = "corpus_excluded"
        elif not values["confidence_admissible"]:
            reason = "insufficient_confidence"
        else:
            reason = "redundant_not_minimal"
        candidates.append(
            CraftCandidateAudit(
                **values,
                selected=selected,
                exclusion_reason=reason,
            )
        )
    if diagnosis_nonapplicable:
        outcome = "abstained_upstream"
    elif not selected_indices:
        outcome = "abstained_no_fit"
    else:
        outcome = "selected"
    selected_refs = tuple(item.move_ref for item in candidates if item.selected)
    return CraftSelectionManifest(
        selection_id=f"craft.selection.{diagnosis.diagnosis_id}",
        diagnosis_ref=diagnosis_ref,
        diagnosis_hash=object_digest(diagnosis),
        diagnosed_reader_problem_key=diagnosis.reader_problem_key,
        diagnosed_required_resolution_ids=diagnosis.required_resolution_ids,
        diagnosed_upstream_science_status=diagnosis.upstream_science_status,
        profile_stack_ref=profile_stack_ref,
        profile_stack_hash=object_digest(profile_stack),
        corpus_release_ref=static_resource_ref(active_corpus),
        selection_strategy="function_first_semantic_set_cover_v2",
        index_version=active_corpus.index_version,
        retriever_version=active_corpus.retriever_version,
        selector_version=CRAFT_SELECTOR_VERSION,
        candidates=tuple(candidates),
        selected_move_refs=selected_refs,
        outcome=outcome,
        selected_by=selected_by,
        selected_at=selected_at,
    )


def profile_catalog_role_resource() -> dict[str, Any]:
    """Copyright-neutral catalog projection for the resolver role packet."""

    catalog = load_profile_catalog()
    return {
        "release": static_resource_ref(catalog).model_dump(mode="json"),
        "cards": tuple(
            {
                "layer_kind": card.layer_kind,
                "selection_key": card.selection_key,
                "status": card.status,
                "confidence": card.confidence,
                "directives": tuple(
                    {
                        "statement": item.statement,
                        "strength": item.strength,
                        "effect_scope": item.effect_scope,
                        "directive_kind": item.directive_kind,
                        "acceptance_criterion": item.acceptance_criterion.model_dump(
                            mode="json"
                        ),
                        "non_applicability": item.non_applicability,
                    }
                    for item in card.directives
                ),
            }
            for card in catalog.cards
        ),
    }


def craft_corpus_role_resource() -> dict[str, Any]:
    """Derived-only functional corpus projection for the retriever, not writer."""

    corpus = load_craft_corpus()
    return {
        "release": static_resource_ref(corpus).model_dump(mode="json"),
        "split": corpus.split_id,
        "index_version": corpus.index_version,
        "retriever_version": corpus.retriever_version,
        "reader_problem_rules": tuple(
            item.model_dump(mode="json") for item in corpus.reader_problem_rules
        ),
        "source_evidence": tuple(
            {
                "source_card": source.source_card_id,
                "research_mode": source.research_mode,
                "evidence_role": source.evidence_role,
                "paper_family": source.paper_family_id,
                "reader_problem": source.reader_problem_key,
                "function": source.function_key,
                "access_status": source.access_status,
                "confidence": source.confidence,
                "functional_summary": source.functional_summary,
                "transferable_content": source.transferable_content,
                "non_applicability": source.non_applicability,
            }
            for source in corpus.source_cards
        ),
        "moves": tuple(
            {
                "move": move.move_id,
                "functional_name": move.functional_name,
                "reader_problem": move.reader_problem_key,
                "function": move.function_key,
                "triggers": move.trigger_conditions,
                "required_semantic_inputs": move.required_semantic_inputs,
                "supported_repair_actions": move.supported_repair_actions,
                "intended_reader_update": move.intended_reader_update,
                "placements": move.typical_placements,
                "variants": move.valid_variants,
                "failure_modes": move.failure_modes,
                "compatible_archetypes": move.compatible_archetypes,
                "compatible_audiences": move.compatible_audiences,
                "compatible_theory_modes": move.compatible_theory_modes,
                "compatible_field_keys": move.compatible_field_keys,
                "eligible_section_roles": move.eligible_section_roles,
                "compatible_causal_classes": move.compatible_causal_classes,
                "non_applicability_rule_ids": move.non_applicability_rule_ids,
                "confidence": move.confidence,
                "non_applicability": move.non_applicability,
            }
            for move in corpus.moves
        ),
    }


__all__ = [
    "CRAFT_CORPUS_V1_HASH",
    "CRAFT_SELECTOR_VERSION",
    "PROFILE_CATALOG_V1_HASH",
    "PROFILE_RESOLVER_VERSION",
    "ProfileCraftPolicyError",
    "craft_corpus_role_resource",
    "load_craft_corpus",
    "load_profile_catalog",
    "profile_catalog_role_resource",
    "resolve_profile_stack",
    "select_craft_moves",
]
