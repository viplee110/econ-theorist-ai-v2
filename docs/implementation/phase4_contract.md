# Phase 4 Profile and Craft Vertical Slice Contract

Status: implementation and semantic acceptance complete on
`agent/phase4-profile-craft`. An uninterrupted full-genesis Phase 1→4 gold run,
current focused/full non-gold suites, a fresh segmented continuation with
independent final-store verification, and an independent final adversarial
branch review with no blocking findings satisfy this contract on the branch.
Commit and merge remain pending. Full-history replay remains a performance
target, but the comprehensive acceptance command now passes.

Working branch: `agent/phase4-profile-craft`

Accepted Phase 3 base: `fb2c4f59665f0e7a9b223390442070463022bfed`

## 1. Outcome

The first Phase 4 slice is complete only when one exact Phase 3 theory result
can be calibrated to a human-authorized reader profile, diagnosed at the level
of a failed reader update, repaired with the smallest applicable set of
evidence-bearing functional craft moves, and re-evaluated without changing the
scientific claim or exposing anchor prose to the writer.

The slice targets the system's central authoring failure: prose that is
formally correct but remains abstract, theorem-shaped, and expensive for a
human economist to interpret. It does not treat fluency, additional intuition
paragraphs, or resemblance to a published paper as success. Success requires
that an isolated reader can recover the benchmark, operative economic force,
affected margin, boundary, and a nearby prediction from the revised text while
the Phase 3 formal-fidelity floor remains satisfied.

The accepted vertical chain is:

```text
exact Phase 3 scientific prefix and canonical working unit v2
-> an audited obligation-to-predicate mapping for the executed diagnostic check used by this slice
-> one human-authorized target configuration
-> deterministic profile-stack resolution
-> a fresh target-specific failed review, blocked ReviewClosure, and exact RevisionBrief over v2
-> exact reader-problem diagnosis
-> function-first retrieval from a theory-only craft release with internal source-risk controls
-> same canonical-writer identity supersedes that same ManuscriptUnit from v2 to v3
-> fresh Phase 3 formal/economic/cold-reader closure
-> independent craft-realization review
-> deterministic PROFILE-CRAFT-READY-0.1 closure
```

Phase 4 is still a one-result-block slice. It does not establish a complete
paper compiler, a general journal recommender, or publication readiness.

## 2. Compatibility before capability

- Phase 1, Phase 2, and Phase 3 payload bytes, schemas, route instructions,
  registry catalogs, policy hashes, frozen fixtures, and replay semantics remain
  unchanged.
- Phase 4 introduces `registry.v4.json`. It contains every v3 route entry with
  its exact v3 instruction and contract, then adds only the eight Phase 4-native
  routes in Section 9. Historical runs continue to resolve the registry hash
  with which they were created.
- Phase 4 payloads live in a separate `profile_craft` namespace and schema
  release. No field is added to a Phase 3 payload in order to make this slice
  work.
- The ordinary v3 `design.reader_path`, `compose.manuscript_unit`,
  `review.manuscript_unit`, reader-probe, and `close.manuscript_review` routes
  retain their accepted semantics. A Phase 4 closure is layered on top of a
  fresh Phase 3 `AUTHORING-READY-0.1` closure; it does not redefine that
  predicate retrospectively.
- A profile stack, source card, craft move, diagnosis, or target-fit review is
  never scientific support for a claim, proof, mechanism, assumption, example,
  or literature comparison.
- A venue or audience change cannot enter a discovery, mechanism,
  formalization, proof, or G1--G5 promotion context merely because it is present
  in project state.

The separate namespace is substantive, not cosmetic. It lets v3 projects
replay exactly while v4 can add new catalog provenance, conflict resolution,
craft selection, and reader-facing closure without widening the meaning of an
old entity.

## 3. Static catalogs versus project state

Profiles and craft evidence have two distinct homes.

### 3.1 Static, versioned catalog resources

Repository releases under `profiles/` and `craft/` contain:

- atomic profile-layer cards and one profile-catalog release manifest;
- release-cleared craft source cards subject to internal source-risk controls;
- functional craft-move cards;
- one craft-corpus release manifest with split, lineage, and active-status
  metadata.

These resources are versioned content and policy inputs. They are not copied
wholesale into every project snapshot. A run registers or otherwise resolves
their exact bytes and hashes, and project manifests retain only the exact
resource references needed for replay.

A catalog release is a software/content-governance product. Its human review
does not make it L2 scientific authority over a paper. It may describe a useful
reader-facing transformation; it may not assert that the project's theorem,
mechanism, or importance is correct.

### 3.2 Project-specific manifests

Project state stores exact decisions, resolved directives, diagnosed reader
problems, selected move references, bindings to the project's own economic
objects, and review outcomes. It does not store full anchor papers, reusable
sentences, or a second copy of the catalog.

The resolved profile stack is intentionally separate from craft selection.
Profile resolution occurs before a manuscript-specific reader failure is
known, whereas craft selection is conditional on that failure. Putting
selected move IDs inside the profile stack would create a circular dependency:

```text
profile -> Paper IR / reader path -> observed reader problem -> craft selection
```

Therefore `TargetProfile` pins the profile-catalog release,
`ResolvedProfileStack` pins the selected profile layers and resolved
directives, and `CraftSelectionManifest` pins the craft release, retriever,
index, selector, and selected moves. No selected craft move appears in the
profile stack.

## 4. Static resource contracts

### 4.1 Profile-layer card

Every layer card records at least:

```text
layer id, version, and layer kind
canonical value and theory-only applicability
atomic directives with allowed effect domains
strength: invariant / required / soft preference
trigger and non-applicability conditions
compatible theory modes, archetypes, fields, and audiences
evidence refs, coverage, confidence, retrieval date, and review-after date
conflict keys and incompatibilities
artifact hash and release provenance
```

The allowed effect domains are closed. A field, audience, or venue layer may
adjust reader background, definition timing, example choice, pacing, emphasis,
appendix placement, or compression. It may not alter formal scope,
assumptions, proof status, evidentiary role, novelty evidence, or the human
authority registry.

Inactive provisional venue hypotheses cannot be emitted as active directives.
Submission constraints require an authoritative source and may affect only
rendering or packaging.

### 4.2 Craft source card

A source card records:

```text
source identity and lawful location
source kind: anchor / contrast / development / project_postmortem
theory mode, field, archetype, audience, and technical intensity
paper-family and author-team lineage
reader problem and source location
functional interpretation and competing interpretation
transferable semantic pattern
paper-specific material that must not transfer
access status, confidence, split, and review status
artifact hash and derivation provenance
```

The card is a derived analytical record, not a passage bank. Public resources
contain citations and internally reviewed functional notes rather than full
copyrighted or unpublished text.

These source-access, phrase, and voice rules are internal engineering controls.
They reduce transfer and imitation risk but do not prove copyright status,
authorship, plagiarism absence, or legal compliance.

### 4.3 Craft move card

A move card records:

```text
move id and version
controlled reader-problem kind
trigger conditions and forbidden conditions
required semantic-input slots
intended reader update and transfer objective
allowed placement and realization variants
anti-patterns and non-applicability rules
compatible modes, archetypes, fields, and audiences
matched anchor-card refs and contrast-card refs
independence groups and transfer confidence
release, split, artifact hash, and derivation provenance
```

For a working-draft selection in this slice, an active stable move requires at
least two genuinely independent matched anchor lineages and one functional
contrast card. A one-anchor move remains provisional and may be explored only
in preview. Two versions of one paper, common descendants, or the same author
team do not satisfy independence.

All active cards in the core release are theory-only. A mixed paper may support
a card only for an identified formal-theory function; empirical identification,
estimation, treatment effects, data templates, and causal-design moves are
inadmissible retrieval content.

## 5. Phase 4 project objects

Phase 4 adds the following strict payloads in `profile_craft`.

| Object | Function |
|---|---|
| `ObligationPredicateContract` | clause-level map from one exact proof obligation to one exact executable predicate and its bounded evidentiary role |
| `PredicateMappingAudit` | independent audit and adversarial mutation record for one exact mapping contract |
| `TargetProfile` | thin project selection bound to exact current Phase 3 package/Paper IR/reader-path/base-profile inputs, effective L2 Decisions, and one exact profile-catalog release |
| `ResolvedProfileStack` | deterministic project manifest over exact human decisions and static profile resources |
| `ReaderProblemDiagnosis` | exact typed projection of blocked closure, RevisionBrief instructions/findings, affected sections, causal class, and semantic source fields |
| `CraftSelectionManifest` | deterministic minimum-cardinality set cover v2 of exact revision requirements |
| `CraftRealizationAssessment` | independent requirement-, directive-, and target-reader assessment plus bounded phrase/voice/contamination controls |
| `ProfileCraftClosure` | derived `PROFILE-CRAFT-READY-0.1` result over the complete exact chain |

Profiled composition deliberately produces only an ordinary Phase 3
`ManuscriptUnit`; there is no `ProfiledManuscriptUnit` payload. The immutable
route focus and exact `ResolvedProfileStack -> ManuscriptUnit` (`governs`),
`CraftSelectionManifest -> ManuscriptUnit` (`realizes`), and
`ReaderProblemDiagnosis -> ManuscriptUnit` (`depends_on`) relations supply the
additional Phase 4 lineage without changing the frozen Phase 3 schema. The
manuscript artifact and all consequential semantic spans remain governed by
the Phase 3 `ManuscriptUnit` contract.

Phase 4 semantic-input provenance is recorded separately on
`CraftMoveRealization.realized_semantic_source_refs`, in the exact order of
`realized_semantic_input_ids`. It never expands the frozen Phase 3
`ConsequentialSpan.source_fields`, whose sources remain limited to the exact
Phase 3 scientific projections.

`TargetProfile` is not a second authority store. Its selected dimensions must
equal the exact effective Decisions it references; changing the manifest cannot
change the human choice. It additionally binds the exact current Phase 3
package, Paper IR, reader path, and base `ResolvedProfileManifest`, with payload
hashes and source-state revision. Those inputs must have mutually consistent
lineage and remain current and fresh. A foreign input, superseded version, or
upstream semantic change invalidates the target and every dependent stack,
diagnosis, selection, manuscript revision, assessment, and closure. It exists
so the resolver has one content-addressed target input rather than an informal
collection of target strings.

### 5.1 `ResolvedProfileStack`

The implemented manifest binds:

```text
profile-stack id and schema version
exact TargetProfile ref and payload hash
exact profile-catalog release ref
selected static layer refs, kinds, selection keys, and source statuses
every active or rejected directive, precedence, conflict outcome, and reason
the exact active-requirement and active-soft-preference projections
source-state revision, resolver version, resolver actor, and resolution time
```

The selected configuration and human Decision refs live in the exact
`TargetProfile` to which the stack binds. The craft release and retrieval
versions live in the later `CraftSelectionManifest`. The stack contains no
selected craft move and embeds no catalog card.

Phase 3's development fixture used the values `top_five` and
`general_economic_theorists`; the architecture's canonical Phase 4 values are
`frontier_general_interest` and `economic_theorist` or
`theory_and_field_bridge`. The resolver must not silently reinterpret an old
human decision. A working v4 stack needs an exact later L2 confirmation of the
canonical configuration or an explicit human-confirmed migration mapping.
Historical v3 manifests and Decisions remain unchanged.

### 5.2 `ReaderProblemDiagnosis`

Each diagnosis binds exact Paper IR, reader path, result contracts, resolved
profile, and—when a draft has been reviewed—the exact inspected manuscript,
diagnostic reviews/findings, blocked `ReviewClosure`, and `RevisionBrief`, all
with payload hashes. A post-manuscript diagnosis cannot become ready from a
self-reported reader problem or a review from a different draft. It records:

```text
exact blocking finding categories and affected section ids/roles
one typed causal class
one ResolutionRequirement for every blocking RevisionBrief instruction
exact instruction source, finding, repair action, assertion and section scope
four typed SemanticInputBindings with facet refs and semantic hashes
controlled reader-problem key and exact cached requirement/input projections
resolved or unresolved upstream-science status and craft eligibility/upstream route
exact evidence refs, diagnostician, and diagnosis time
```

The four seed semantic inputs are not interchangeable free-text slots. Their
typed selectors are `paper.narrative_spine.natural_benchmark`,
`result_packet.archetype.operative_force`,
`result_packet.archetype.affected_margin`, and `result_packet.boundary`.
Each selector has a fixed source kind and owning semantic facet. The two
archetype roles resolve through a closed deterministic table: a
`mechanism_explanation` packet uses `initiating_force` and `affected_margin`,
while a `comparative_statics_threshold` packet uses `competing_effects` and
`threshold_or_regime_logic`. Any other archetype fails closed; validation does
not try alternate paths or fall back to free text. Reusing the
benchmark field as a mechanism, supplying a derived diagnosis in place of an
accepted result field, or binding the right text from the wrong entity fails
validation. The payload does not duplicate review or manuscript bytes and
never exposes a hidden probe, answer key, or respondent answer.

The architecture distinguishes typed causal cases:

- `scientific_content`: the mechanism, boundary, assumption role, or evidence is not
  present in canonical research state;
- `reader_path_design`: a prerequisite, ordering, or section contract must change;
- `local_exposition`: accepted semantic inputs exist but the prose fails to
  deliver the intended update;
- `target_profile_mismatch`: the chosen audience or target configuration is itself the
  problem.

An initial-planning class is available only before a manuscript/review exists.
Only `local_exposition` is craft-retrieval eligible in the first slice.
`scientific_content` routes back to the owning theory route. A reader-path gap that
materially reorders the argument requires the existing L2
`narrative_material_order` authority and is deferred from the first runtime
case. `target_profile_mismatch` returns to the human profile decision rather
than being repaired rhetorically.

The writer may see the functional diagnosis and the already-authorized transfer
objective. The writer and retriever may not see a concrete hidden cold-reader
probe, answer key, respondent answer, or adjudication criterion. Fresh probes
are generated after revision.

### 5.3 `CraftSelectionManifest`

The implemented selection manifest records:

```text
exact diagnosis and resolved-profile refs and payload hashes
diagnosed problem, required resolutions, and upstream-science status
exact craft-corpus release ref
selection strategy plus retriever/index/selector versions
bounded ordered candidate audits, with each candidate's derived move card,
functional filters, covered requirements, and rejection reason
ordered selected move refs, outcome, and minimum-cardinality certificate
selector actor and selection time
```

It cannot cite a craft move as support for a scientific assertion. The writer
must bind every new consequential span to Phase 3 scientific sources exactly as
before. Static source-card lineage remains in the pinned corpus; it is not
copied into project state or exposed to the writer packet.

## 6. Profile resolver

`PROFILE-RESOLVER-0.1` is deterministic over exact inputs.

1. Resolve all effective Decision versions and require L2 human authority for
   the selected target configuration.
2. Pin the exact catalog release and select its one active universal floor.
3. Project the primary archetype from the current G4/G5 claim hierarchy rather
   than deciding it again.
4. Expand theory mode, ambition, field, audience, optional overlay, and verified
   submission constraints into atomic directives.
5. Evaluate typed applicability. Pure theory cannot acquire fabricated welfare,
   policy, incidence, direct-effect, or equilibrium-feedback obligations.
6. Build a conflict graph keyed by target scope, reader function, and effect
   domain.
7. Treat the universal floor as absolute: no other layer may defeat or weaken
   it, irrespective of ordinary numeric precedence. For all other conflicts,
   activate the highest applicable precedence and reject lower incompatible
   directives with an exact reason.
8. If two non-equivalent directives at the same highest precedence share a
   conflict key, fail resolution. Stable sorting may order equivalent records;
   it may never lexically choose a scientific or authoring winner, and an LLM
   may not blend the conflict away.
9. Stale or insufficient field/venue evidence can only downgrade or deactivate
   that calibration. It cannot weaken the universal floor or create a new
   scientific requirement.
10. Canonicalize directives and rejected conflicts, bind every source hash, and
    derive the manifest hash.

A resolver does not estimate acceptance probability. A venue overlay is a
soft, evidence-dated reader calibration, not a label such as "Econometrica
style."

## 7. Craft diagnosis and retrieval

### 7.1 Diagnose before prescribing

Craft retrieval is forbidden until an exact reader problem exists. A theorem
that feels abstract because its economic mechanism is unresolved is a science
failure, not a prose problem. The diagnosis must show that the needed benchmark,
margin, rival, boundary, or assumption role already exists in exact accepted
state before a card may tell the writer how to expose it.

### 7.2 `CRAFT-RETRIEVER-0.1`

The first retriever is deterministic and function-first. It uses no source
passage embeddings, prose-similarity score, named-author style representation,
or hidden evaluation content.

1. Compile a controlled query from the diagnosis's problem kind, intended
   reader update, section role, result archetype, audience, and available
   semantic-input slots.
2. Hard-filter to the pinned active release and permitted splits.
3. Exclude empirical/mixed empirical cards, evaluation holdouts, unauthorized
   private sources, stale/retracted moves, the current evaluation paper family,
   cards whose required inputs are absent, and cards whose non-applicability
   condition fires.
4. Require compatible theory mode, archetype, audience, placement, evidence
   independence, and contrast support.
5. Rank lexicographically by exact reader-problem function, intended update,
   archetype, audience transition, placement, evidence class, and then lower
   intervention complexity. Stable move ID and version provide the final
   deterministic tie break.
6. Enumerate compatible covers and select a true minimum-cardinality set over
   the exact diagnosed `ResolutionRequirement` ids. Break ties only by the
   stable lexical tuple of move ids. Removing any selected move is not a
   sufficient certificate: a different smaller cover must also be ruled out.
   The seed corpus currently contains one supported move with exact extractors
   for `mechanism_explanation` and `comparative_statics_threshold`; it does not
   claim support for the other result archetypes or reader problems, and the
   schema uses no prose-length or paragraph-count quota.
7. Record every candidate and rejection, the minimum-cardinality certificate, all exact
   bindings, and the final manifest hash.

The canonical writer receives only selected functional cards rendered with the
project's own objects, plus the exact profile and revision packet. It never
receives anchor text or a phrase bank.

## 8. Obligation-to-predicate hardening

Phase 3 guarantees the bytes, execution, and declared scope of a harness, but
does not guarantee that an author-chosen executable predicate faithfully
represents the natural-language proof obligation. Phase 4 narrows that gap
without pretending that software can certify all semantic equivalence.

An `ObligationPredicateContract` binds one exact obligation, claim, model,
assumption set, harness entry point, code/input/domain artifacts, and declared
evidentiary role. It decomposes the obligation into stable clause IDs covering:

- quantifiers;
- domain and non-empty-domain conditions;
- antecedents and assumptions;
- conclusion, comparison, inequality direction, and tolerance;
- exclusions and scope boundaries.

Every clause maps to an exact predicate expression, code region, and executed
domain using JSON Pointer locators, or is explicitly recorded as uncovered. The
operational protocol reruns the exact Phase 3 executable receipt rather than
trusting a self-reported result. The declared role distinguishes
a falsification search from an identity certificate. Failure to find a finite
counterexample can never be upgraded to proof.

A distinct auditor creates `PredicateMappingAudit`. The audit recomputes all
hashes and checks:

- a witnessed non-empty domain and satisfiable antecedent;
- no constant-true, conclusion-copying, or empty-loop predicate;
- no dropped quantifier, assumption, exception, or conclusion component;
- no silent narrowing of bounds, grid, cases, or parameter domain;
- correct inequality direction and boundary treatment;
- clause-level adversarial mutations, with a justified result for any clause
  claimed redundant;
- exact limits of the resulting evidentiary role.

The five mandatory operational downgrade controls are empty domain, constant
true, conclusion flip, domain narrowing, and omitted assumption. The auditor
executes a typed domain-member witness and the first four controls against the
pinned predicate bytes. A bare finite scan cannot relabel that witness as
antecedent-satisfying when no executable antecedent exists. When the predicate has no assumption
component, omitted assumption retains the same predicate bytes and is registered
as a typed unexecutable control with
`execution_outcome=unencoded_assumption_not_executable`. It must force a warning
and prohibit `approved_exact`; it must not be reported as an executed or killed
mutant.

The mapper, harness author, and mapping auditor must satisfy the route's actor
and lineage-independence policy. A passing audit means "mapped and adversarially
audited for this declared role," not "the theorem is proved."

Approval is explicitly bounded. `approved_exact` requires exact contract
coverage, complete executable-control replay, no unexecutable mandatory control,
an antecedent-satisfying witness, and a predicate-falsifying witness.
`approved_partial` may approve an honestly partial or diagnostic contract only
when every registered executable control is replayed, each typed unexecutable
control is preserved with an explicit limitation/warning, a domain witness is
verified, and no error or critical finding remains. Every such limitation is a
typed, non-optional downstream projection: `ProfileCraftClosure` must carry it
and cannot issue a limitation-free readiness record.
It does not change the contract's coverage class or the Phase 3 receipt's
evidentiary role. In particular, a finite-sample `no_counterexample_found`
receipt remains diagnostic corroboration and cannot become a universal proof.

The first operational slice requires one unambiguous executed receipt for each
mapped obligation and an exact bijection between executable tool receipts in the
governing `AssuranceBundle` and approved bounded mapping audits supplied to the
Phase 4 chain. `resolve.profile_stack` and `close.profile_craft_review` recompute
that binding; missing, duplicate, or foreign receipts/audits fail closed. Typed
Phase 3 harness non-applicability records do not need fabricated mappings. A
rejected supplied mapping blocks Phase 4 readiness; it reopens G5 only when the
failure reveals a substantive proof or scope gap rather than a harness-only
weakness.

## 9. Route catalog v4

`registry.v4.json` adds exactly these eight native routes in the first slice.
The existing v3 design, ordinary compose/review/reader, closure, and effort
routes remain available with their original instructions.

### `map.obligation_predicate`

Consumes exactly one `AssuranceBundle`, `AssumptionMap`, `ClaimGraph`,
`FormalModel`, and `ProofObligation`. The validator requires the scientific
refs to be the assurance bundle's exact lineage and the obligation to be
covered by that bundle. It produces one `ObligationPredicateContract` whose
code, input, predicate, clause, witness, and mutation refs bind the executed
receipt. Mapping is a proposal and cannot improve the receipt's evidentiary
role. The route registers the exact witness, mutated-predicate, and
mutation-result artifacts created by the mapping transaction; unregistered,
missing, noncanonical, or hash-mismatched operational bytes fail staging and
replay.

### `audit.obligation_predicate`

Consumes the same five exact scientific/assurance inputs plus one exact mapping
contract. A lineage-independent human or agent exactly reruns the mapped
receipt, verifies the declared witness at its typed strength, and replays every mutation artifact
already registered by the mapping, producing one `PredicateMappingAudit`
bound to the route run and context hashes. It preserves failures and uncovered
clauses rather than editing the mapping into a pass.

### `resolve.profile_stack`

Consumes one exact `ValidatedArgumentPackage`, `AssuranceBundle`, `PaperIR`,
`ReaderPath`, Phase 3 `ResolvedProfileManifest`, and one or more approved
bounded `PredicateMappingAudit`s. The deterministic route produces one
`TargetProfile` and one conflict-free `ResolvedProfileStack` in the same
transaction. The target carries the exact effective human L2 Decision refs as
transaction evidence/authority, and both outputs pin the packaged profile
catalog by exact static-resource ref. An unresolved conflict or inactive
requested layer blocks resolution rather than becoming a partially active
stack.

### `diagnose.reader_problem`

Consumes exact `PaperIR`, `ReaderPath`, `ResultContractSet`, and
`ResolvedProfileStack` inputs. A post-manuscript diagnosis additionally requires
the exact inspected `ManuscriptUnit`, current diagnostic `ReviewRecord`s and
blocking `ReviewFinding`s, blocked `ReviewClosure`, and its exact
`RevisionBrief`. It produces one `ReaderProblemDiagnosis` whose requirements
are a lossless typed projection of the brief instructions and findings. Only a
pre-manuscript planning diagnosis may use the typed no-prior-unit/review path.
It receives no cold-reader probe/key bytes. Formal or scientific gaps cannot be
labeled craft-eligible.

### `retrieve.craft_moves`

Consumes one exact craft-eligible diagnosis, resolved profile, `PaperIR`,
`ReaderPath`, and `ResultContractSet`. A deterministic actor resolves the pinned
packaged corpus and runs the function-first retriever under the
`research_authoring` purpose, producing one `CraftSelectionManifest`. The
context exposes only release-cleared internal derived cards; it does not expose excluded
empirical material, full source prose, citations, locators, or hidden
evaluation content.

### `compose.profiled_manuscript_unit`

Consumes exact profile stack, diagnosis, selection, Paper IR, reader path,
result contracts, Phase 3 minimal profile, and validated package inputs; the
governing assurance is included when the Paper IR names one. When revising a
prior unit, the exact blocked `ReviewClosure` and `RevisionBrief` over that same
unit are mandatory inputs, and the output must supersede the same
`ManuscriptUnit` entity at its next generation. The actor must be the exact Paper
IR canonical writer.
The route produces exactly one ordinary Phase 3 `ManuscriptUnit` and no
Phase-4-specific manuscript wrapper. The writer may change exposition but may
not change scientific scope, assumptions, result hierarchy, or a material
argument order without the existing effective L2 Decision.

The provider-visible writer packet contains the functional move cards and
project bindings, not anchor text, raw reviews, hidden probes/keys, or corpus
search results. Every new consequential span still needs only the exact Phase 3
scientific source fields admitted by the frozen authoring contract. Phase 4
diagnosis sources are bound separately by the later realization assessment.

### `review.craft_realization`

Consumes one exact ordinary `ManuscriptUnit`, profile stack, diagnosis,
selection manifest, Paper IR, reader path, result contracts, fresh
`AUTHORING-READY-0.1` `ReviewClosure`, and exactly three fresh `ReviewRecord`s:
formal, economic-reader, and cold-reader.
A human or agent critic distinct from the writer produces one
`CraftRealizationAssessment`. The assessment checks every exact revision
requirement against its realizing selected move, affected assertion ids,
affected section ids, and the ordered independent Phase 4 semantic source refs
bound by that realization. It separately checks
each active profile directive against its observable assertion-role/review-signal
criterion and records a noncompensatory target-reader outcome for benchmark,
operative force, boundary, and nearby-case prediction. It also checks that
anti-patterns, anchor language, and unsupported scientific content did not
enter. It does not rewrite prose and cannot substitute for formal,
economic-reader, or cold-reader review.
The phrase-overlap check is a typed immutable artifact registered by this route.
It scans n-grams only across pinned internal derived fields and must bind its
exact manuscript, selected moves, comparison set, and pass/fail result. It is not
a plagiarism detector or a copyright/legal certification. The analogous named-
voice control is likewise an internal policy check, not proof about authorship,
copyright, or legal compliance.

### `close.profile_craft_review`

A deterministic actor consumes the exact ordinary manuscript unit, profile
stack, diagnosis, selection, `CraftRealizationAssessment`, fresh Phase 3
`AUTHORING-READY-0.1` `ReviewClosure` over that same unit, and one or more
approved bounded mapping audits. The governing `AssuranceBundle` is resolved
through the base Phase 3 closure rather than supplied as a second direct input.
The route produces one `ProfileCraftClosure`. Missing or foreign inputs, an old
authoring closure, favorable craft self-report without fresh cold-reader
transfer, a failed directive/requirement/target-reader check, or omission of a
typed `approved_partial` predicate limitation fails closed.

## 10. Authority

No new paper-level Decision kind is required for this slice.

- Theory mode, ambition, field, audience, venue overlay, submission
  constraints, target profile, voice charter, narrative material order, and
  manuscript promotion use their existing L2 Decision kinds.
- Related choices should be presented in one decision packet, but the resolver
  records the exact effective Decision refs rather than inventing authority in
  its own payload.
- Profile resolution, conflict detection, filtering, ranking, hashing, and
  closure are L0 deterministic derivations.
- Diagnosis, provisional craft application, and prose revision are reversible
  L1 work.
- A move that materially changes argument order cannot be applied in working
  mode without the exact effective `narrative_material_order` L2 Decision.
- A craft card cannot choose a theorem, suppress a genuine boundary, expand
  scope, or create novelty.
- Manuscript-version promotion remains L2. External communication, release,
  and submission handoff remain L3.

Catalog review is content governance, not a shortcut around these levels.

## 11. Dependency and freshness rules

All Phase 4 relations bind exact versions, facets/paths, semantic hashes, and
artifact bytes.

- Superseding a target/profile Decision makes the `TargetProfile` no longer
  current/effective and therefore blocks readiness through the resolved stack,
  diagnosis, selection, profiled `ManuscriptUnit`, craft assessment, and Phase
  4 closure. It does not rewrite or stale G1--G5 science, proofs, or unchanged
  Phase 3 assurance.
- A venue overlay or submission constraint may create presentation or
  packaging invalidation only. Any edge from it to a formal claim or proof is a
  schema error.
- Publishing a new catalog release does not retroactively stale a project that
  pinned an older valid release. Retraction of a selected move, revoked source
  access, or materially weakened evidence evidentiary-stales the selection and
  craft review and requires reassessment of the prose; it does not invalidate
  the theorem.
- Adding an unrelated source card or move leaves existing selections fresh.
- A diagnosis and selection remain valid historical revision bases after the
  exact diagnosed manuscript version is intentionally superseded, provided the
  Phase 4 transaction relations preserve that dependency and none of their
  semantic, profile, or evidence inputs changed. They are not required to
  pretend that the superseded draft is current.
- A new manuscript revision hard-stales reviews and closure over the old bytes.
  Fresh probes must be generated for the new unit.
- A change to an accepted benchmark, mechanism, assumption, claim scope,
  ResultPacket, or reader contract propagates through the existing Phase 3
  edges and also stales every dependent Phase 4 diagnosis, selection,
  manuscript, assessment, and closure.
- A mapping contract depends hard on the exact obligation, formal inputs,
  harness code, domain, and receipt. Any changed byte requires a new audit.
- A failed predicate mapping blocks the receipt's use in Phase 4 closure. It
  does not automatically declare the analytical proof false; a substantive gap
  is recorded separately and routed to proof/G5 repair.

Provider-visible context isolation is tested independently of transaction-head
metadata. Changing only a venue overlay must leave the compiled scientific
payload of discovery and proof routes unchanged because those resources are not
permitted inputs to those routes.

## 12. `PROFILE-CRAFT-READY-0.1`

A profiled working manuscript is ready under the first Phase 4 predicate only
when all of these hold:

1. the exact underlying Phase 3 manuscript unit has a fresh
   `AUTHORING-READY-0.1` closure;
2. every executable tool receipt in the governing assurance chain has exactly
   one approved bounded `PredicateMappingAudit`, every audit binds its exact
   receipt without duplication, neither coverage nor evidentiary role is
   upgraded, and every `approved_partial` typed limitation is projected into
   closure;
3. the exact L2 profile Decisions and exact Phase 3 package, Paper IR, reader
   path, and base profile manifest remain current/fresh; the resolved stack is
   current, conflict-free, and contains the absolute universal floor;
4. no inactive provisional venue hypothesis or unverified submission constraint
   entered the active stack;
5. the reader diagnosis exactly binds the blocked closure and RevisionBrief,
   projects every blocking instruction/finding and typed semantic source, reveals
   no unresolved scientific input gap, and is eligible for local exposition repair;
6. the retriever used the pinned theory-only release, excluded holdouts and
   source prose, and selected the deterministic minimum-cardinality compatible
   set cover v2;
7. every selected move has exact required-input bindings and active independent
   matched/contrast evidence;
8. neither a craft resource nor a profile directive is cited as scientific
   support for a manuscript assertion;
9. the craft critic confirms assertion/section/independent Phase 4 source-binding coverage for every
   revision requirement, observable acceptance for every active directive, and
   a passing target-reader outcome; no unresolved blocking anti-pattern,
   provenance, target-fit, or imitation finding remains;
10. the fresh Phase 3 economic-reader reconstruction and cold-reader probes for
    the revised unit pass, including boundary and near transfer; merely applying
    a named move is insufficient;
11. formal fidelity, exact scope, assumptions, evidentiary language, and
    canonical-writer ownership remain unchanged or freshly revalidated;
12. the complete chain and every catalog/artifact byte replay exactly.

`ProfileCraftClosure` is a derived authoring record. It is not a publication
score, journal acceptance prediction, human promotion, or permission to submit.

## 13. First gold scenario

The first gold chain continues the real Phase 3 attention/precision case and
uses the existing headline reversal:

```text
fixed-processing benchmark:
greater signal precision improves conditional accuracy

endogenous-use force:
precision also raises a precision-linked processing cost and can change uptake

boundary/near transfer:
weakening that cost narrows the threshold gap; once uptake no longer differs,
the usual accuracy ranking returns
```

The scenario must perform, rather than self-report, the following sequence:

1. Preserve the exact Phase 3 G5 package, proof evidence, and assurance chain.
2. Create and independently audit mappings for every executed harness receipt.
3. Evaluate all five mandatory downgrade controls. Execute and reject empty
   domain, constant true, conclusion flip, and domain narrowing. Record omitted
   assumption as the typed `unencoded_assumption_not_executable` control because
   the bare predicate contains no assumption component; preserve its warning and
   prohibit exact approval.
4. Obtain an exact L2 canonical target choice for `pure_theory`,
   `frontier_general_interest`, `information_economics`, and
   `theory_and_field_bridge`, with no active venue overlay in the first release.
5. Resolve one conflict-free profile stack while preserving the G4/G5
   `comparative_statics_threshold` archetype.
6. Use a deterministic, correct but abstract writer fixture that states the
   threshold result yet does not let an isolated reader use the mechanism in the
   nearby weaker-cost case. Run a fresh target-specific review over the canonical
   `ManuscriptUnit` v2; formal review passes while economic/cold-reader review
   blocks, producing a blocked closure and exact revision brief.
7. Diagnose the exact failure as a local exposition gap, not a missing theorem
   or missing mechanism.
8. Retrieve the seed release's one supported benchmark-to-force move for the
   exact `comparative_statics_threshold` packet using
   two independent matched anchor lineages and a contrast card. The
   minimum-cardinality selection binds the existing benchmark,
   extensive information-use margin, competing forces, ablation, and boundary;
   no source sentence reaches the writer.
9. Have the same canonical-writer identity supersede that same unit from v2 to
   v3 using the exact blocked closure, revision brief, diagnosis, and selection.
10. Run fresh formal, economic, cold-reader, and craft reviews. Verify every
    brief requirement's assertion/section/independent Phase 4 source binding, every active
    directive criterion, and the target-reader outcome. The cold reader
    must now predict that weakening the precision-linked cost shrinks and then
    eliminates the reversal region for the stated reason.
11. Produce a passing `PROFILE-CRAFT-READY-0.1` closure and an exact human-effort
    record, then replay the final head byte-for-byte.

The gold suite also forks a target-only mutation. Changing only a soft overlay
must alter the resolved profile and justified presentation descendants while
leaving the question, model, assumptions, claims, proofs, G1--G5 Decisions, and
assurance current. Discovery-route provider payloads must not contain the
overlay or craft catalog. An empirical craft card and a confirmatory-holdout
card must both be rejected even if their text is superficially similar to the
manuscript.

The scenario demonstrates a functioning repair mechanism. It does not show
that the craft component caused a general quality improvement; that comparison
belongs to Phase 6.

The fixture is deterministic and makes no external LLM call; it is not an
autonomous paper generator and supplies no paper-quality, Top-5, legal, or
human-effort-efficacy evidence. Current acceptance evidence is an independent
final adversarial branch review with no blocking findings; 82/82 focused Phase
4 non-gold checks; the complete non-gold suite with 403 tests passing and five
skips; an uninterrupted full-genesis Phase 1→4 gold test passing in 6156.901
seconds; all five exporter checks; `doctor` with `required_ok=true`; registry v4 with 34
routes and hash
`d81276ed9b7482768840ef89980d6cbb81361ca2ff84acee3ab7da7bb67eae7e`;
compilation of 98 Python files; and `git diff --check`.

The uninterrupted final-code gold test is the primary end-to-end acceptance
evidence. The fresh segmented real-ObjectStore continuation remains additional
historical-integrity evidence: it began at frozen Phase 3 head
`dfb04a...` and completed through run 52. Independent final-store verification
at head `88b656...` found 87 entities, all 67 historical entities byte-identical,
all 182 historical transaction/artifact/provenance files unchanged,
`replay_at(final.head) == replay(final)`, exactly one current ready
`ProfileCraftClosure`, and diagnostic coverage with all eight typed limitations
preserved. The 6156.901-second uninterrupted runtime leaves full-history replay
as a performance target, but the comprehensive acceptance command now passes.
Commit and merge remain pending.

## 14. Required adversarial tests

- any mutation of v1--v3 registry or instruction bytes fails frozen oracles;
- a v4 route using a v3 registry hash, or a historical route using v4 semantics,
  fails;
- profile resolution without the universal floor or exact effective L2
  Decisions fails;
- legacy profile values cannot be silently mapped to canonical v4 values;
- equal-precedence conflicts, hard journal templates, and overlays that change
  science fail;
- stale, unsupported, or inactive venue evidence cannot become an active
  requirement;
- target-only changes do not stale claims, proofs, or assurance;
- selected moves inside the profile stack fail schema validation;
- craft retrieval without a diagnosis, for a science gap, or with missing
  semantic inputs fails;
- retrieval by source prose similarity, named-author style, or hidden target
  text fails;
- empirical, unauthorized, retracted, same-lineage duplicate, and holdout cards
  are excluded;
- a stable working move without two independent matched anchors and one contrast
  fails;
- a nonminimal incompatible move dump fails its selection certificate;
- a writer packet containing anchor text, probe/key material, or full search
  results fails context validation;
- craft/profile refs used as scientific assertion support fail;
- a different writer, foreign diagnosis, foreign selection, or stale prior unit
  fails profiled composition;
- a craft critic cannot compensate for failed formal, economic, or cold-reader
  review;
- counting moves, examples, paragraphs, or explanation length cannot satisfy
  closure;
- theorem restatement without a recoverable mechanism and transfer prediction
  fails;
- constant-true, empty-domain, weakened, narrowed, and wrong-inequality harness
  mappings fail independent audit; a typed unexecutable omitted-assumption
  control forces a warning and prevents exact approval rather than pretending
  that it was executed;
- finite failure to find a counterexample cannot receive a universal-proof
  evidentiary role;
- missing or foreign mapping audits fail Phase 4 closure;
- a revised unit requires fresh reader probes and reviews;
- exact replay, Phase 1 frozen bytes, Phase 2 frozen semantics, and Phase 3
  schemas/gold behavior remain green.

## 15. Explicit deferrals

The first Phase 4 slice does not implement:

- a complete-paper profile/craft compiler;
- runtime cases for all six result archetypes;
- a broad production catalog across all theory fields;
- an active named-journal overlay, including an Econometrica overlay, before a
  separate evidence-dated corpus release and human authorization exist;
- automated journal choice, acceptance probabilities, or prose imitation;
- material reader-path or whole-paper reordering beyond the existing L2
  authority and the one local repair case;
- online learning from the user's draft, automatic global profile updates, or
  cross-project private memory;
- large-scale paper ingestion or storage of copyrighted full text;
- provider ranking, credentials, general multi-agent orchestration, or formal
  proof adapters;
- external release, communication, submission execution, or L3 handoff;
- empirical, econometric, identification, estimation, experimental, causal, or
  data workflows;
- evidence that v2 beats v1, improves held-out papers, reduces human effort, or
  reaches Econometrica/Top-5 quality. Those are Phase 6 evaluation claims.

The initial active catalog may contain only the universal floor, the gold
case's theory mode/ambition/field/audience resources, a no-overlay configuration,
and the small number of independently supported craft moves required by the
gold. Schema support for other layers is not permission to activate unsupported
content.

## 16. Exit criteria

The first Phase 4 slice is accepted only when:

- registry v4 adds the eight routes above while preserving every v1--v3 byte
  and selector result;
- strict `profile_craft` schemas are exported and reproduce exactly;
- static profile/craft resources are separate from project manifests and every
  selected resource is hash-pinned;
- the resolver is deterministic, conflict-reporting, and authority-complete;
- the retriever is function-first, minimum-cardinality, theory-only,
  holdout-safe, and subject to bounded internal source/voice controls that make
  no legal-certification claim;
- one uninterrupted full-genesis real-ObjectStore chain completes the gold
  failure-diagnosis-retrieval-revision-review-closure sequence, with segmented
  continuation retained as independent historical-integrity evidence;
- every executed harness receipt in that chain has a passing independent
  clause-level mapping audit;
- the revised unit passes fresh Phase 3 formal/economic/cold-reader review and
  the independent craft review without changing the theorem;
- target-only selective invalidation and all downgrade attacks pass;
- doctor, schema checks, exact replay, the complete Phase 1--4 regression suite,
  and frozen Phase 1--3 oracles pass before branch acceptance.

Passing this contract establishes one trustworthy profile-and-craft repair
loop. It does not establish general Top-5 writing quality or comparative
efficiency; those claims remain governed by the preregistered Phase 6 protocol.
