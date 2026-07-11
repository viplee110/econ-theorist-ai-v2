# State and Runtime Architecture v0.1

Status: design specification, not an implementation claim

Scope: economic theory only

Owner: canonical state, transactions, dependencies, routing, provenance, and recovery

## 1. Purpose and boundary

The runtime exists to preserve scientific meaning while humans and multiple agents explore, formalize, verify, explain, and revise an economic theory project. It must answer five questions reliably:

1. What is currently claimed, and at what exact scope?
2. Which artifacts and decisions support that claim?
3. Which conclusions became stale after an upstream change?
4. Who had authority to make each consequential decision?
5. Can another machine reconstruct the same project state and route context?

The runtime is not a substitute for economic judgment. It does not define the positive research process, decide whether a mechanism is interesting, write the paper, or certify publication readiness. Those responsibilities belong to the theory kernel, manuscript compiler, target profiles, and evaluation specifications.

This document deliberately specifies a thin substrate. A larger state machine, a general agent platform, and a database-first implementation are anti-goals for Architecture v0.1.

## 2. Five runtime planes

The system is divided into five logical planes. They may initially share one process and one file store; the separation is semantic, not a microservice requirement.

| Plane | Owns | Must not become |
|---|---|---|
| **1. Constitution and authority** | scientific invariants, privacy rules, authority levels, confirmed decisions, release permission | a long route prompt or an automated taste function |
| **2. Canonical research state** | typed entities, typed relations, orthogonal statuses, current versions, canonical head | a manuscript store, notebook dump, or prose dashboard |
| **3. Control and context** | route contracts, entry predicates, dependency selection, context compilation, write scopes, validators | a fixed irreversible stage pipeline |
| **4. Execution and provenance** | isolated human/agent/tool runs, candidate transactions, tool evidence, conflicts, run lineage | an untraceable chat history or agent-vote truth machine |
| **5. Artifacts and views** | proofs, examples, scripts, literature notes, Paper IR, manuscript files, generated status views, export bundles | a second source of project status |

The normal flow is:

```text
constitution + authority
          ↓
materialized snapshot at revision R
          ↓
route contract → context manifest → isolated run
          ↓
candidate artifacts + candidate transaction
          ↓
validation + authority check + atomic commit at R+1
          ↓
dependency invalidation → regenerated views
```

Only a committed transaction changes canonical state. Chat messages, agent conclusions, tool output, edited Markdown views, and the mere existence of an artifact do not.

## 3. The small always-on kernel

Every route receives a small, versioned control kernel. It contains only information that is both cross-cutting and unsafe to omit:

- project identity, schema version, canonical head, and active route/run identifiers;
- the theory-only scope and hard scientific invariants;
- authority and privacy rules;
- the active human-confirmed decisions relevant to the route;
- the focused entity identifiers, freshness summary, unresolved blockers, and allowed write set;
- the context manifest identifier and instructions for producing transaction candidates.

The kernel must not contain the full manuscript, proof archive, literature archive, old discussions, all agent instructions, or every project entity. Architecture v0.1 targets approximately **1,500–2,000 tokens** for the ordinary always-on kernel. Normative rules may be compressed by reference to versioned rule identifiers, but they may not be silently truncated.

The kernel is compiled, not hand-maintained. A budget test fails if it grows beyond its configured envelope. Route-specific scientific instructions and project content are loaded after the kernel and are separately versioned.

## 4. Canonical state model

### 4.1 Event history and snapshot

The canonical source of truth is the chain of committed, immutable transactions plus registered immutable artifact versions. A materialized snapshot is a rebuildable cache for fast reads. Generated Markdown is a view of that snapshot.

```text
committed transactions + immutable artifact versions
                         ↓ replay
              materialized typed snapshot
                         ↓ render
           status page / tables / human views
```

Direct edits to a snapshot or generated view are invalid. A meaningful correction is expressed as a new transaction that supersedes an earlier version while preserving history.

### 4.2 Thin entity envelope

Every canonical entity has a common envelope. The example is illustrative; the exact serialization is an implementation choice constrained by the semantics below.

```yaml
entity_id: ent_...
entity_type: mechanism_hypothesis
version: 4
project_id: prj_...
title: "Congestion redirects sequential search"
summary: "One decision-complete paragraph, not the underlying note"
scope_ref: scope_...
status:
  lifecycle: active
  formal_validity: not_applicable
  interpretation_validity: stress_tested
  literature:
    coverage: current
    novelty: unresolved
derived_status:                 # snapshot projection, never agent-authored
  human_acceptance: human_provisional
  freshness: fresh
artifact_refs: [art_...]
relation_refs: [rel_...]
decision_refs: [dec_...]
provenance_ref: txn_...
privacy: project_private
access_compartments: [project_research]
created_at: "..."
supersedes: ent_...@3
```

A field belongs in canonical state only if at least one route, validator, authority rule, dependency rule, privacy rule, scope check, provenance query, or evaluation consumes it. Rich derivations, prose, code, diagrams, referee reports, and paper text remain artifacts.

Canonical summaries are decision-complete but short. They identify the economic content and exact scope; they do not reproduce the artifact.

### 4.3 Orthogonal status dimensions

There is no single `verified`, `approved`, or `done` flag. At minimum, relevant entities expose the following independent dimensions:

| Dimension | Initial vocabulary | Meaning |
|---|---|---|
| `lifecycle` | `proposed`, `active`, `superseded`, `retired` | administrative existence, not truth |
| `formal_validity` | `not_applicable`, `unassessed`, `exploratory_only`, `partially_checked`, `verified_in_scope`, `failed`, `disputed` | mathematical support for the exact formal scope |
| `interpretation_validity` | `not_applicable`, `unassessed`, `hypothesized`, `example_supported`, `stress_tested`, `validated`, `failed`, `disputed` | support for the proposed economic mechanism or interpretation |
| `literature.coverage` | `not_started`, `partial`, `current`, `needs_refresh` | adequacy and freshness of the closest-theory search |
| `literature.novelty` | `unassessed`, `unresolved`, `differentiated`, `absorbed`, `disputed` | relationship of the contribution claim to prior theory |
| `human_acceptance` | `agent_proposed`, `human_provisional`, `human_confirmed`, `human_rejected`, `superseded` | projection of effective Decision events, not scientific truth |
| `freshness` | `fresh`, `stale`, `revalidating`, `blocked_by_stale_input` | projection of committed dependencies and version refs |

Applicability is declared by entity schema. A required dimension uses one value from its vocabulary; a dimension declared inapplicable is omitted from stored status and rendered as `not_applicable` in views. Formal verification does not promote interpretation validity. Human confirmation does not promote formal validity or novelty. Strong prose does not change any dimension.

Stored scientific-status transitions require a transaction, an allowed actor, and supporting references. `human_acceptance` is derived exclusively from effective, immutable Decision events. `freshness` is derived exclusively from the committed dependency graph and exact version/facet refs. Both appear in materialized snapshots and views, but neither may be asserted by an agent or written by an independent status-transition operation.

### 4.4 Core entity families

The initial schema should support only entities needed by the end-to-end theory route.

Aggregate names used by `theory_kernel.md`—including `BenchmarkSet`, `PrimitiveGraph`, `EconomicArgumentGraph`, `PredictionRegister`, `ExampleSuite`, `FormalizationMap`, `AssumptionMap`, `ClaimGraph`, `ClosestTheoryMap`, and `ValidatedArgumentPackage`—are **derived manifests over granular canonical entities**. A manifest contains ordered member refs, a source revision, and a manifest hash; it never duplicates member content or status. Rebuildable manifests may be registered as artifacts, but the granular entities below remain the only canonical research truth.

**Research identity and scope**

- `Project`, `ResearchQuestion`, `Benchmark`, `ScopeDefinition`, `TargetProfileRef`, `ResolvedProfileManifestRef`, `CraftMoveRef`.

**Economic reasoning**

- `Primitive`, `MechanismHypothesis`, `FrozenPrediction`, `MicroExample`, `MechanismTest` (including ablation and rival separation), `EconomicInterpretation`, `EconomicArgument`.

**Formal theory**

- `FormalModel`, `Assumption`, `SolutionConcept`;
- `Claim`, storing independent `formal_kind` (theorem, lemma, proposition, corollary) and `economic_result_archetype` (`mechanism_explanation`, `comparative_statics_threshold`, `characterization_bounds`, `robustness_invariance_equivalence`, `design_implementation_impossibility`, or `concept_representation_foundation`);
- `ProofObligation`, `VerificationRecord`, `Counterexample`, `ResultPortfolio`.

**Literature and contribution**

- `LiteratureEvidence`, `ClosestTheoryEntry` (a member of the derived `ClosestTheoryMap` manifest), `ContributionClaim`, `AbsorptionAssessment`.

**Authoring and review references**

- `ArgumentSpineRef`, `PaperIRRef`, `ManuscriptContractRef`, `ReviewFinding`, `EvaluationRecord`.

The manuscript compiler owns the internal schema of Paper IR and manuscript contracts. The runtime stores only their identity, version, scope, status, dependencies, and artifact references.

**Operational records**

- `Decision`, `Artifact`, `RouteRun`, `ContextManifest`, `Transaction`, `RiskOrBlocker`.

New entity types require an owning route, a validator, a dependency policy, and a demonstrated inability to represent the content with an existing entity plus artifact.

The canonical cross-document vocabulary is `LiteratureEvidence`, the derived `ClosestTheoryMap` manifest, and `TargetProfileRef`; aliases such as `EvidenceRecord`, `LiteratureClaim`, `ClosestTheoryComparison`, `TargetSpec`, or `target journal profile` are import labels only and must normalize to these objects.

### 4.5 Typed relations

Relations are first-class and versioned. Important initial relation types include:

```text
defines / refines / supersedes
depends_on / assumes / uses_solution_concept
implements / formalizes / maps_to
predicts / tests / ablates / distinguishes_from
supports / contradicts / limits / is_counterexample_to
proves / discharges / interprets
compares_with / is_absorbed_by / differentiates_from
belongs_to_result / realizes_argument_step
renders / reviews / addresses
derived_from / produced_by / governed_by_decision
```

Each invalidating relation declares both a `dependency_mode` and an exact endpoint:

```text
(upstream entity id, version, facet or field path, semantic hash)
-> (downstream entity id, version, facet or field path)
```

Initial upstream facets are `formal`, `economic_interpretation`, `literature_novelty`, `terminology_presentation`, and `authority`. A type may refine these into field paths but may not replace them with an untyped "meaning changed" assertion. Each relation also declares a `dependency_mode`:

- `hard`: a change to the bound facet/path stales the downstream facet;
- `scope_sensitive`: propagation occurs when the changed scope overlaps the downstream scope;
- `evidentiary`: removal or weakening of support requires reassessment;
- `presentation`: the rendered downstream artifact becomes stale, not the upstream science;
- `trace_only`: provenance with no invalidation effect.

The descriptive relation graph may contain economically meaningful feedback. The invalidating `depends_on` projection must be a directed acyclic graph. Cycles in the dependency projection are a schema error and usually reveal that two objects need a shared upstream object or a single composite object.

## 5. Immutable transactions and events

### 5.1 Transaction envelope

A route produces a candidate transaction rather than directly editing canonical state.

```yaml
transaction_id: txn_...
transaction_schema: 1
project_id: prj_...
base_revision: rev_...
route_run_id: run_...
actor:
  kind: agent       # human | agent | deterministic_tool
  actor_id: ...
intent: "Register a tested mechanism candidate"
preconditions:
  - entity: ent_...
    expected_version: 3
changed_facets:
  - entity: ent_...
    facets: [economic_interpretation]
operations:
  - entity.create: ...
  - relation.create: ...
  - status.transition: ...
artifact_additions:
  - artifact_id: art_...
    content_hash: sha256:...
evidence_refs: [art_..., run_...]
authority_basis: [dec_...]
validator_results: [...]
created_at: "..."
parent_transaction_hash: sha256:...
```

`changed_facets` is mandatory for a superseding entity version and is validated against the actual field diff. The transaction digest is computed over canonical serialized bytes and stored as the content-addressed filename/head value; it is **not** a field inside those bytes.

Initial operations remain limited to creating/superseding/retiring entity versions or relations, requesting stored scientific-status transitions, recording/superseding Decisions, registering immutable artifact versions, and recording route outcomes or blockers.

An apparent in-place patch is serialized as a new entity version. Deletion from history is not an ordinary operation. Privacy-driven erasure, if legally required, is an exceptional administrative procedure that leaves a non-sensitive tombstone and audit record where permitted.

### 5.2 Commit rules

A transaction can commit only when:

1. its base revision is still the relevant head;
2. schemas and references validate;
3. relation and dependency invariants validate;
4. status transitions are legal and cite sufficient evidence;
5. its actor has the necessary authority or a confirmed decision delegates it;
6. every referenced new artifact exists at the declared content hash;
7. privacy flow rules permit all new relations and exports;
8. the resulting dependency graph remains acyclic.

Validators establish structural admissibility, not economic merit. A schema-valid mechanism can still be wrong or uninteresting.

### 5.3 Corrections and disagreement

History is never rewritten to make the research path look cleaner. Failed frozen predictions, rejected mechanisms, counterexamples, negative referee findings, and superseded decisions remain addressable. A correction creates a new version and states what it supersedes and why.

Disagreement between agents is represented by separate findings or candidate entities connected to the same object. It is resolved by evidence or an authorized decision, not by overwriting the minority finding or counting votes.

## 6. Decisions and authority

### 6.1 Decision record

A Decision event is the sole authority truth. Entity `human_acceptance` is a deterministic projection of the effective Decision events that govern it. A decision is immutable and scoped, with at least:

```text
decision id and version
question being decided
available options
selected option, if any
recommendation and concise rationale
evidence, dissent, and unresolved risks
required authority level
decider and timestamp
effective revision and affected scopes
status: proposed / provisional / confirmed / rejected / superseded
decision_kind
superseded-by reference
```

The record stores a concise, inspectable rationale, not hidden chain-of-thought.

`decision_kind` and its minimum authority come from one versioned registry. Initial kinds include the theory-kernel promotions `G1_question_benchmark`, `G2_mechanism`, `G3_formal_base`, `G4_result_investment`, and `G5_argument_validation`, plus primitive promotion; novelty/contribution; argument/narrative spine and material ordering; theory mode, ambition, field, audience, venue overlay, and submission constraints; voice charter; manuscript-version promotion; privacy declassification; external release; and destructive cleanup. A kind may require a higher level under a project policy, never a lower one. Decision status is not duplicated in the entity's stored scientific status.

### 6.2 Authority levels

The runtime enforces the levels defined in `ARCHITECTURE.md`:

| Level | Examples | Who may commit |
|---|---|---|
| `L0 deterministic` | hash, validate, render, replay, derive snapshot projections | deterministic tooling under a versioned rule |
| `L1 reversible exploration` | provisional mechanisms, examples, model variants, derivations, critiques, prose previews | agents or humans through isolated provisional runs |
| `L2 structural science` | promote question, primitive, solution concept, main result/scope, novelty, argument/narrative spine, target profile, or voice charter | a human confirmation transaction |
| `L3 external/destructive` | authorize a release bundle, submission handoff, external communication, or destructive cleanup | explicit human authorization for the named action |

Agents may prepare decision-complete proposals and continue reversible exploration from them. A provisional decision may support a labeled provisional run, but it cannot become a stable dependency of the confirmed central argument. Structural delegation debt is surfaced as a blocker before promotion.

Human confirmation means “accepted as the current project choice,” not “proved true.” A confirmed decision may later be superseded by another human decision; downstream freshness is then recomputed.

## 7. Dependency DAG and staleness

### 7.1 Dependency identity

Every dependency edge binds to an exact upstream entity/version/facet-or-path/semantic-hash endpoint and, where relevant, an exact scope or artifact hash. A downstream facet is fresh only if:

- all required upstream versions are current at the pinned canonical head;
- all required authority decisions remain effective;
- all required evidence exists and retains sufficient status;
- no invalidation predicate attached to the edge has fired.

Freshness is therefore a reproducible snapshot projection. It is not a canonical event, an agent assertion, or an inference from file modification time.

### 7.2 Propagation semantics

When a committed transaction declares and validates `changed_facets`, the runtime computes affected descendant facets before rendering the next snapshot/view. A terminology-only change cannot stale a proof edge bound to `formal`; a changed formal assumption cannot be hidden as presentation. Classification that requires scientific judgment is part of the candidate transaction and promotion dossier, not guessed by the dependency engine.

| Upstream event | Required effect |
|---|---|
| an assumption changes meaning or scope | stale dependent claims, proof obligations, verifications, interpretations, argument steps, and manuscript units |
| a solution concept changes | stale affected model solutions and everything derived from them |
| a frozen prediction is replaced after derivation | preserve the original prediction; mark the new one post-derivation and reopen the relevant mechanism test |
| a mechanism is rejected | preserve any independently valid formal theorem; stale the mechanism mapping, interpretation, argument step, and dependent prose |
| a counterexample defeats a universal claim | set the claim's formal status to failed or disputed in scope and stale all stronger dependent claims and prose |
| closest theory absorbs a contribution claim | stale novelty, contribution framing, argument spine, target assessment, and manuscript claims; do not stale an otherwise valid proof |
| a human-confirmed structural decision is superseded | stale all descendants governed by the prior decision |
| a manuscript paragraph is edited | stale only derived renderings/reviews unless the edit is ingested as a changed scientific claim |

Staleness does not erase prior validation. It says that validation was performed against an older dependency set. Revalidation creates a new verification or interpretation record bound to the new versions.

### 7.3 Blocking and repair

A stale entity may be inspected and used as historical evidence. It may not be promoted as current support for a central claim. If a route requires a stale input, the route either:

- switches to an explicit repair/revalidation route;
- operates in a labeled provisional run without canonical promotion; or
- stops with `blocked_by_stale_input` and names the minimal repair set.

The dependency engine should compute the smallest affected subgraph. It must not invalidate the entire project by default.

## 8. Routes and the context compiler

### 8.1 Authoritative route registry and contract

The runtime owns one versioned route registry and exact executable route IDs. Scientific documents own route semantics and instruction bundles, but their diagrams are conceptual unless their labels resolve to a registry ID. Aliases normalize at intake and never become a second route catalog. Every registered route declares a machine-checkable contract:

```yaml
route_id: verify.claims_proofs_and_interpretation
route_version: 1
purpose: "Independently verify one scoped formal claim"
entry_predicates: [...]
focus_types: [Claim]
required_statuses: [...]
instruction_bundles: [...]
read_selector: ...
artifact_excerpt_policy: ...
allowed_tools: [...]
allowed_entity_operations: [...]
output_schema: ...
validators: [...]
authority_ceiling: L1
success_outcomes: [...]
failure_and_reroute: [...]
staleness_policy: ...
privacy_clearance: project_private
allowed_purposes: [research_verification]
required_compartments: [project_research]
```

Routes are capabilities, not maturity labels. A project can revisit a route whenever dependencies change. Writing `Stage 7` into a view never advances the project.

Architecture v0.1 reserves these exact core IDs:

```text
frame.question_and_benchmarks; decompose.primitives; tournament.mechanisms; freeze.predictions; lab.micro_examples_and_ablations; promote.mechanism
tournament.implementations; promote.formal_base; discover.claims_and_boundaries; verify.claims_proofs_and_interpretation; audit.assumptions_generality_and_absorption
curate.result_portfolio; validate.argument_package; design.reader_path; compose.manuscript_unit; review.manuscript_unit; repair.dependency
```

More specific operations such as `revise.claim` or `compose.result_block` are route parameters or registered child IDs, not implicit aliases. `route_id`, not prose order or a stage number, is the executable identity.

### 8.2 Route-run lifecycle

An isolated run follows this lifecycle:

```text
planned
→ context_compiled at revision R
→ running
→ completed_with_candidate | failed | interrupted
→ validated
→ committed | rejected | superseded | stale_base
```

Completion does not imply commitment. A run may produce useful artifacts while its candidate state transition is rejected.

The lifecycle above is logical, not permission to rewrite one creation record. In the Phase 1 local substrate, immutable `run.json` records only the transition into `running`; later operational outcomes live in noncanonical sidecars, while admissible scientific outcomes require a committed `RouteOutcome`. A lock-time `stale_base` result is operational and can never be asserted as a canonical RouteOutcome.

### 8.3 Context compilation

The compiler takes:

```text
snapshot revision
+ route and role versions
+ focus entity ids
+ `ResolvedProfileManifestRef`, only if the route permits target calibration
+ privacy clearance
+ declared purpose and compartment grants
+ token budget
+ isolation/blinding policy
```

It selects, in order:

1. the small kernel;
2. the route's versioned scientific instructions;
3. focused entities at exact versions;
4. the minimal required ancestor and neighbor slice from the dependency graph;
5. effective decisions and unresolved dissent in that slice;
6. declared artifact excerpts, with provenance and scope;
7. relevant stale/blocker notices;
8. an explicit list of important omissions caused by budget, privacy, or blinding.

The output is both compiled context and an immutable `ContextManifest` containing all entity versions, artifact hashes/excerpt boundaries, rule/profile versions, selector version, budget, redactions, exclusions, and final context hash. Given the same inputs and available artifacts, deterministic selection must reproduce the same manifest.

Budget pressure is handled by graph relevance and declared compression rules, not silent truncation. Required invariants, claim quantifiers, assumption scope, dissent, and authority constraints are never summarized away.

### 8.4 Isolation policies

Different roles receive deliberately different contexts:

- an explorer may see open alternatives and failure history;
- an independent proof verifier does not see the originating proof's persuasive commentary unless required after a blind attempt;
- an economic-interpretation critic sees the formal statement and examples but does not inherit the proposed intuition as fact;
- a cold reader sees the intended manuscript unit and only the background a real target reader would have;
- the canonical writer sees validated content and critique records but does not acquire authority to change scientific scope.

No route relies on hidden chat memory. If information affects an output, it must appear in the manifest or be recorded as a tool result during the run.

### 8.5 Write discipline

Each run has an entity and artifact write allowlist. Agents write to a staging area and return:

- candidate artifacts;
- a candidate transaction;
- concise rationale and uncertainty;
- unresolved conflicts and recommended next route.

An agent cannot promote its own authority, edit an upstream confirmed decision, or mark its own output human-confirmed.

A critic output that affects a candidate transaction, revision brief, gate, or committed prose is consequential and must be retained as an immutable `ReviewFinding` with the critic run, exact target refs, finding, evidence, severity, and disposition. Raw non-consequential alternatives may follow the run-retention policy; deletion may never break committed provenance.

## 9. Multi-agent provenance

Every human, agent, and deterministic-tool run records enough provenance to reproduce the evidentiary path without preserving private reasoning traces:

- run, parent-run, route, role, provisional-workspace, and base-revision identifiers;
- actor class and stable actor identifier;
- model/tool/provider identifier where applicable;
- instruction, schema, profile, selector, and validator versions;
- context manifest and input artifact hashes;
- tool invocations and returned artifact references;
- output artifact hashes and candidate transaction identifier;
- timestamps, completion state, declared uncertainty, and concise rationale;
- reviewer findings, conflicts, and eventual disposition.

Private chain-of-thought is neither required nor stored. Provenance records claims, evidence, assumptions, transformations, and decisions that another researcher can inspect.

Agent agreement is not scientific evidence. Multiple agents using substantially identical context and models are correlated reviewers, not independent replications. The runtime records role, context, model family, and parentage so evaluation can detect false independence.

Only one designated canonical writer commits reader-facing prose for a manuscript unit. Other agents submit findings or proposed patches. This preserves a coherent voice while keeping criticism independent.

## 10. Atomic commit, concurrency, and recovery

### 10.1 Minimal commit protocol

Phase 1 uses one canonical `main` head and a **mandatory exclusive commit lock**; it does not assume that a portable file system supplies compare-and-swap:

1. pin base head `R`; write candidate artifacts and canonical transaction bytes to staging;
2. compute artifact digests and the transaction digest outside the canonical transaction bytes, then run validators;
3. acquire the exclusive commit lock and re-read `main` inside the lock;
4. if `main != R`, release the lock and return `stale_base` without rewriting the candidate;
5. move immutable artifacts and transaction bytes into content-addressed locations;
6. atomically replace the `main` pointer with the transaction digest, then release the lock;
7. rebuild/invalidate the snapshot and regenerate views.

Steps 6 and 7 are caches and may safely occur after the atomic head update. A transaction object not reachable from `main` is not committed canonical history.

### 10.2 Concurrent proposals

Runs may execute concurrently against a pinned revision, but Phase 1 serializes commits. A changed head returns `stale_base`; the route must recompile context and explicitly resubmit or preserve the candidate as a conflicting proposal. Automatic rebase, branch heads, and merge semantics are deferred until controlled multi-agent work demonstrates the need. Last-writer-wins is always forbidden for research entities and decisions.

### 10.3 Recovery matrix

| Failure point | Recovery |
|---|---|
| crash while staging | remove or quarantine staging; canonical head is unchanged |
| immutable artifact written but transaction not reachable | retain temporarily as an orphan, then garbage-collect or quarantine after audit |
| transaction object written but head not advanced | treat as uncommitted proposal; retry only after base and validators are checked |
| head advanced but snapshot/view missing | replay from head and regenerate caches/views |
| corrupted snapshot | discard and replay committed transactions |
| artifact hash mismatch | quarantine artifact, mark dependent objects blocked, never substitute silently |
| competing head update | keep losing candidate, return `stale_base`, preserve both run records |
| external human edit of a tracked manuscript | never overwrite; register the new file version or present a three-way reconciliation proposal |

Recovery is idempotent. Phase 1 executes no external action and produces only local candidate transactions plus registered local artifacts. It neither constructs a release bundle nor submits a bundle checksum for `L3` handoff authorization. Private-backup/public-release bundle construction, cross-machine validation, checksum-bound authorization, and external handoff are deferred until the release capabilities in Section 12 are implemented and enabled.

## 11. Physical layout and portability

The logical store should remain inspectable and usable without a hosted service. An illustrative initial layout is:

```text
.econ-theorist/
  project.yaml                 # project id, schema versions, non-secret config
  refs/
    main                       # atomic pointer to committed transaction hash
  locks/commit                 # mandatory Phase 1 exclusive commit lock
  transactions/sha256/...      # immutable transaction objects
  artifacts/sha256/...         # immutable registered artifact versions
  runs/...                     # run and context manifests
  snapshots/latest.json        # rebuildable cache
  views/status.md              # generated, non-canonical
  staging/...                  # disposable, never canonical
```

Exact filenames are not frozen, but the following portability rules are:

- UTF-8, documented schemas, stable identifiers, and content hashes;
- relative logical references rather than machine-specific absolute paths;
- no provider-specific identifiers as the sole identity of an entity or artifact;
- explicit schema and route migrations with before/after validation;
- deterministic replay from genesis committed transactions, or from a verified snapshot checkpoint plus its subsequent committed transactions;
- git compatibility without treating git commits as canonical scientific transactions;
- a full private backup includes schemas, all reachable transactions, permitted referenced artifacts, manifests, and checksums.

Here `checkpoint` means only a rebuildable snapshot cache whose state hash and transaction head have been verified; it never replaces committed history as authority. `Accepted events` is not a separate category: only transactions reachable from `main` are committed.

A local file implementation is sufficient for the first vertical slice. An index or database may later accelerate queries, but it remains a rebuildable projection unless a reviewed architecture revision says otherwise.

## 12. Privacy and release

Every entity and artifact has one privacy label plus zero or more purpose/compartment grants:

- `public`: safe for a public repository or release bundle;
- `project_private`: ordinary unpublished research material;
- `restricted`: sensitive referee, coauthor, licensed, or third-party material with named access rules;
- `local_only`: secrets, credentials, or material prohibited from export.

The default for new research content is `project_private` in `project_research`. Purpose/compartment ACLs are independent of the privacy lattice: `confirmatory_holdout`, for example, denies authoring and craft-retrieval purposes even to an actor otherwise cleared for project-private material. Route authorization requires privacy clearance, an allowed purpose, every required compartment, and role/isolation rules.

Privacy propagates conservatively: a derived artifact cannot receive a more permissive label without a registered declassification Decision of the required kind and authority. Legal or license restrictions cannot be waived by project authority. Credentials and secrets are never stored in canonical state, transactions, prompts, or provenance logs.

Privacy joins are persistent across bare current references: if a Decision subject/evidence or an Entity/Relation scope later becomes more restrictive, an older referencing record cannot enter a lower-clearance context merely because it was admissible when first written. Derived stale notices carry their complete exact source-evidence closure, so privacy and compartment checks reach the root change even across historical entity versions. If a superseding Entity version leaves an affected facet or JSON Pointer region semantically unchanged, its inherited staleness remains visible on the current version, and that cross-version semantic bridge participates in invalidating-DAG cycle checks. JSON Pointer ancestor and descendant paths count as overlapping regions in both freshness propagation and invalidating-cycle checks.

Public craft resources store citations and derived functional patterns, not copied copyrighted papers or unpublished manuscripts. Export must eventually produce either a **full private backup** with replayable authorized history or a **redacted public release bundle** with permitted artifacts and a non-replayable receipt that records omissions without exposing private transaction payloads, hashes, paths, or summaries. Mixed-private transactions are never copied wholesale into a public bundle. The Phase 1 walking candidate does not implement export and enables no external-release route. Bundle construction and cross-machine validation are required before such a route can be enabled; external handoff remains outside the replayable core and requires an `L3` Decision naming its exact checksum.

## 13. Runtime invariants

The following are hard commit-time or scenario-test invariants:

1. Canonical state changes only through a committed transaction.
2. Every entity version and artifact version is immutable and provenance-linked.
3. Generated Markdown, dashboards, and snapshots are rebuildable views.
4. The dependency projection is acyclic and every edge binds exact versions/scopes.
5. Freshness is derived; stale support cannot promote a current central claim.
6. Formal validity, interpretation validity, literature/novelty, human acceptance, and freshness never imply one another.
7. A finite numerical or symbolic sample cannot verify a universal claim without a valid formal argument or certificate covering that scope.
8. A theorem may remain formally valid when its proposed intuition fails; the statuses and dependencies must represent that case.
9. Failed predictions, counterexamples, dissent, and superseded decisions remain traceable.
10. Structural scientific promotion and release cannot be self-authorized by an agent.
11. A route reads and writes only what its contract, declared purpose, privacy clearance, compartments, and role policy allow.
12. Every consequential run has a reproducible context manifest and output provenance.
13. Human-edited substantive files are never silently overwritten.
14. Replay and recovery are idempotent; the Phase 1 runtime performs no external actions.
15. No core schema or route introduces econometric, identification, estimation, regression, experimental, or empirical-paper entities.

## 14. Minimal tooling surface

Architecture v0.1 needs a small substrate, not a large platform. The first vertical slice requires only these capabilities; command names are illustrative:

- `validate`: schemas, references, authority, privacy, status transitions, and dependency acyclicity;
- `context`: compile a route context and immutable manifest from a pinned revision;
- `commit`: validate and atomically commit one candidate transaction under the exclusive lock;
- `status`: replay/materialize state and render one compact human view;
- `recover`: inspect heads, replay history, repair caches, and quarantine incomplete work;
- `export` (deferred until before external release is enabled): create either a replayable private backup or a redacted release bundle/receipt with checksums.

Route execution can initially be a thin wrapper around these primitives. Search indexes, queues, dashboards, vector databases, distributed locks, and general workflow engines are deferred until an observed bottleneck justifies them.

## 15. Required tests before enabling or promoting the corresponding capabilities

This section is the cumulative architecture-level verification matrix. A delivery slice must pass the tests applicable to the capabilities it implements. Tests for explicitly deferred capabilities—such as export, cross-machine backup replay, proof-verifier or cold-reader isolation, multi-agent lineage, and later scientific-state scenarios—become mandatory before those capabilities are enabled or promoted; their presence below does not claim that the Phase 1 walking candidate implements or has passed them. The walking candidate's implemented boundary and executable acceptance matrix are recorded in `../implementation/phase1_contract.md`.

### 15.1 Structural tests

- schema round-trip and unknown-field rejection;
- stable identifier, referential-integrity, and content-hash checks;
- legal scientific-status transitions plus rejection of direct `human_acceptance`/`freshness` writes;
- Decision-to-authority and dependency-to-freshness projection tests;
- changed-facet validation, dependency-cycle rejection, and minimal stale-subgraph propagation;
- exact route-ID registry and alias-normalization tests;
- authority negative tests for every registered Decision kind at `L2`/`L3`;
- privacy non-downgrade, purpose/compartment denial, holdout isolation, and export-redaction tests;
- theory-only schema lint preventing excluded workflow objects.

### 15.2 Transaction and recovery tests

- exclusive-lock atomic commit under a head race;
- stale-base rejection without automatic rebase;
- canonical transaction-digest test proving the digest is outside hashed bytes;
- idempotent replay and recovery;
- fault injection after every commit step;
- orphan artifact and transaction handling;
- corrupted snapshot rebuild;
- human external-edit protection;
- full-private-backup replay on a different machine path and non-replayable redacted receipt validation.

### 15.3 Context and provenance tests

- golden context manifests for fixed snapshots and routes;
- kernel token-budget regression;
- required quantifier, assumption, dissent, and authority retention under budget pressure;
- privacy, purpose/compartment, and role-isolation tests;
- proof-verifier and cold-reader blinding tests;
- provenance completeness from output claim back to context, artifacts, run, transaction, and actor;
- detection of nominally multiple agents sharing the same parent/context/model lineage.

### 15.4 Scientific state scenarios

At minimum, walk through and automate these cases:

1. **Assumption revision:** changing one load-bearing assumption stales exactly the dependent claims, proof records, interpretations, argument steps, and manuscript units; unrelated results stay fresh.
2. **True theorem, false intuition:** a theorem remains `verified_in_scope` while a mechanism ablation sets its proposed interpretation to `failed` and reopens the economic argument.
3. **Absorbed contribution:** a closest-theory finding invalidates novelty and framing without falsely invalidating the proof.
4. **Counterexample repair:** a failed universal claim is narrowed to a threshold or bound while the original claim and counterexample remain traceable.
5. **Competing agents:** two candidates from the same base survive as explicit proposals; neither wins through last-writer-wins or vote count.
6. **Authority boundary:** an agent can explore from an unconfirmed primitive but cannot promote the central argument or release a manuscript.
7. **Crash recovery:** a failure at each commit boundary reconstructs one unambiguous canonical head; no external action exists to repeat.
8. **Private/export split:** a private backup replays fully, while a public bundle excludes restricted source and validates a redacted provenance receipt without leaking mixed-private transactions.

## 16. Architecture locks and deferred choices

Architecture v0.1 locks the following semantics:

- five-plane separation;
- a small compiled kernel;
- thin typed canonical state backed by immutable transactions;
- orthogonal validity, novelty, authority, and freshness dimensions;
- version/facet-bound dependency invalidation;
- one authoritative exact-ID route registry;
- route-specific, manifest-backed contexts;
- provenance-preserving multi-agent proposals;
- single-head locked atomic commits, replayable recovery, and generated views;
- privacy-labeled, portable, provider-neutral storage.

It intentionally defers serialization details, CLI spelling, user-interface design, indexing technology, orchestration framework, database choice, model provider, and distributed execution. Those choices should be made only after the smallest end-to-end theory case passes the tests above.
