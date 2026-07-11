# Implementation plan

Status: Architecture v0.1 with accepted Phase 1 implementation

Current phase: Phase 2 — theory-kernel vertical slice

## 1. Delivery strategy

Implementation should proceed by thin end-to-end slices. The project must demonstrate that a research object can be created, challenged, invalidated, explained, and recovered before it accumulates a large prompt library or dozens of schemas.

The first useful system is not a manuscript generator. It is a reliable theory-project substrate that can carry one small argument from benchmark to a verified, readable result block while preserving human authority and invalidating dependent work when an upstream object changes.

## 2. Phase 0 — freeze Architecture v0.1

### Deliverables

- architecture constitution and anti-goals;
- positive theory kernel specification;
- state, authority, dependency, context, and recovery model;
- manuscript compiler and reader-model specification;
- theory-only profile and craft-library design;
- v1 capability migration ledger;
- v1/v2 evaluation protocol;
- paper walkthroughs for four representative scenarios.

### Required walkthroughs

1. **Greenfield discovery:** rough theoretical question → benchmarks → competing mechanisms → micro-examples → formal implementation → central result → validated argument → introduction/result block.
2. **Existing theory manuscript:** ingest model, claims, proofs, and expert comments → reconstruct economic/formal objects → diagnose mechanism and exposition debt → revise without overstating scope.
3. **Foundational pure theory:** develop a representation, characterization, equivalence, or impossibility result without fabricating comparative-static, equilibrium-feedback, welfare, or policy fields.
4. **Upstream change:** alter a primitive or assumption after a result block exists → preview blast radius → supersede the decision → invalidate exact proof and prose dependencies → reverify and recompile.

### Exit criteria

- terminology and document ownership are consistent;
- the v1 ledger has no unclassified core capability;
- the evaluation protocol is frozen before generator optimization;
- the user confirms the structural decisions listed in Section 9;
- no production implementation is needed to resolve a known design contradiction.

## 3. Phase 1 — walking substrate

Build the smallest reliable runtime.

Implementation status: the walking substrate and its adversarial acceptance suite were reviewed and merged into `main` at `3ce5c6b8c92fbcbefb361b319a70894e173b119f`. Phase 1 is accepted; this does not imply that later theory, authoring, or release capabilities exist.

### Initial persistent objects

- project metadata and revision;
- artifact references and hashes;
- decisions and authority;
- immutable transaction events;
- run/context manifests;
- a minimal generic entity/relationship container sufficient for the first scenario.

### Initial commands

```text
etai init
etai validate
etai status
etai begin <route>
etai commit <run>
etai stale --why <entity>
etai recover
etai render
```

### Required behavior

```text
init
→ create valid state
→ begin isolated run
→ stage proposal
→ validate authority and hashes
→ commit atomically
→ mutate an upstream entity
→ derive downstream staleness
→ rebuild one compact status view
→ recover from an interrupted transaction
```

### Exit criteria

- schema, authority, dangling-reference, dependency-cycle, hash-conflict, and recovery tests pass;
- state is replayable from genesis committed transactions, or from a snapshot whose chain hash is verified plus later committed transactions;
- a human-owned artifact cannot be silently overwritten;
- generated Markdown is demonstrably non-canonical;
- architecture-budget tests enforce bounded always-on and route contexts.

## 4. Phase 2 — theory-kernel vertical slice

Implementation status: the vertical-slice candidate is implemented on
`agent/phase2-theory-kernel-slice` and has passed its local acceptance suite;
branch review and merge remain pending. This is a semantic/runtime milestone,
not evidence that an AI generator has reached publication quality.

Implement only the objects and routes needed for one complete theoretical argument:

- research question and benchmarks;
- primitive/economic argument graph;
- competing mechanism hypotheses;
- frozen prediction register;
- an archetype-sensitive example suite whose required functional roles are explicit rather than fixed to an E0–E3 count;
- formal model and formalization map;
- assumptions, claims, proof obligations, and closest-theory evidence;
- result portfolio and validated argument package.

The first case should be synthetic or based on public theory material and must be small enough to solve by hand. It must contain a rival mechanism and a boundary environment; a polished toy outline is insufficient.

### Exit criteria

- mechanism and implementation tournaments are operationally distinct;
- failed predictions remain visible;
- benchmark closure, mechanism ablation, rival separation, assumption distance, boundary witness, arrow coverage, and absorption translation tests run;
- numerical corroboration cannot certify a universal theorem;
- all applicable G1–G5 promotion decisions are recorded; reversible exploration may bundle decisions, but G3 formal-base and G5 argument-validation authority cannot be skipped before authoring-ready promotion.
- one real ObjectStore chain crosses G1 through G5, records the human G5
  Decision, derives a fresh validation closure, and replays exactly from
  genesis;
- a real absorption mutation makes the G4 dossier, argument package, and G5
  closure stale while preserving the exact bytes of the formal model, claim
  graph, verification records, and verification bundle, with only G1--G3
  remaining scientifically effective;
- one sealed confirmatory attempt executes `prepare.blind_case` and
  `evaluate.blind_argument_package` through begin, isolated context, stage,
  preflight, commit, and replay, ending in one terminal comparison;
- evaluator independence is enforced before any gold-bearing context is
  compiled, and historical v1 replay cannot be used as a live Phase 2 write
  downgrade;
- the frozen Phase 1 byte oracle remains unchanged and passes byte-for-byte.

## 5. Phase 3 — assurance and authoring vertical slice

Add:

- independent re-derivation;
- symbolic checks and counterexample harness;
- proof audit bound to exact revisions;
- Paper IR and reader-belief states;
- section and result-block contracts;
- layered claim expressions and entailment checks;
- one canonical writer plus isolated fidelity/economic-reader critics.

Working and submission compilation consume the exact G5-approved `ValidatedArgumentPackage` revision. Preview compilation may consume a bounded provisional package but cannot promote it.

### Exit criteria

- a central result can be traced from reader-facing prose to claim, assumptions, mechanism, example, proof status, and evidence revisions;
- a theorem statement remains formal while nearby prose supplies benchmark, translation, mechanism, boundary, and proof roadmap as needed;
- changing the theorem scope invalidates all stronger prose but not unrelated sections;
- cold-reader retell and prediction-transfer tests are executable;
- substantive human-edit categories and time can be recorded.

## 6. Phase 4 — profile and craft system

Add the versioned universal quality floor, theory modes, result archetypes, fields, audience breadth, and soft venue overlays. Populate a theory-only craft library with structural cards derived from permitted sources.

### Exit criteria

- discovery behavior does not change merely because a venue overlay changes;
- a target change affects only justified authoring/review dependencies;
- craft retrieval uses matched and contrast anchors by function, not prose similarity;
- source provenance, access status, confidence, non-applicability, and copyright-safe derived notes are recorded;
- empirical-paper templates cannot enter the core retrieval set.

## 7. Phase 5 — controlled multi-agent and optional adapters

Add only after the single-agent vertical slice is stable:

- isolated mechanism/model lanes;
- general multi-agent lanes beyond Phase 2's sealed confirmatory-evaluation
  contexts, including broader blind, context, and literature-review panels;
- judge synthesis with minority preservation;
- version-control adapter;
- Lean or other formal-proof adapter;
- private researcher-memory adapter;
- advanced symbolic/numerical tools.

### Exit criteria

- multi-agent agreement is recorded as correlated evidence rather than proof;
- raw lanes and context manifests remain inspectable;
- a judge cannot confirm a human-owned decision;
- optional adapters cannot weaken privacy, authority, or evidence semantics;
- the core remains usable without any optional adapter.

## 8. Phase 6 — comparative evaluation and hardening

Run the preregistered compiler-only, end-to-end discovery, and revision comparisons on held-out theory cases under the full protocol in `evaluation.md`. Perform v2 ablations for the economic argument representation, reader contracts, mechanism/result packets, dependency invalidation, and craft retrieval.

Phase 2's sealed blind routes establish the protocol and runtime slice only.
Phase 6 supplies the held-out comparative evidence about whether an isolated AI
generator can actually recover high-quality theory more efficiently than the
frozen baselines.

Before any external-release route is enabled, add and verify replayable private backups plus redacted public bundles/receipts on a different machine path. The Phase 1 walking candidate performs no export or external action.

### Exit criteria

- the complete versioned predicate `EV-PROMOTION-0.1` in `evaluation.md` is satisfied; this plan does not define a weaker local substitute;
- failure cases become regression scenarios or explicit architecture revisions rather than reasons to move the predicate after seeing results.

## 9. Structural decisions for human review

The following decisions should be confirmed at the end of Phase 0 because they shape implementation substantially:

1. use an immutable transaction chain plus atomic head as the portable source of truth, with a thin typed JSON snapshot as a rebuildable materialized view and no database in the initial core;
2. use route-based control and derived readiness rather than a canonical linear stage number;
3. separate mechanism competition from formal-implementation competition;
4. use a universal frontier-theory floor plus composable soft target overlays;
5. use one canonical manuscript writer and independent critics rather than multi-agent prose assembly;
6. require human promotion of structural scientific decisions while permitting autonomous provisional exploration;
7. keep multi-agent panels, formal proof, version control automation, and cross-project memory optional;
8. preserve Apache License 2.0.

## 10. Proposed repository shape

The implementation layout is a proposal, not a commitment to populate every directory immediately:

```text
econ-theorist-ai-v2/
├─ AGENTS.md
├─ ARCHITECTURE.md
├─ README.md
├─ LICENSE
├─ docs/architecture/
├─ src/econ_theorist/
├─ schemas/
├─ routes/
│  ├─ discovery/
│  ├─ mechanism/
│  ├─ formalization/
│  ├─ verification/
│  ├─ authoring/
│  ├─ review/
│  └─ revision/
├─ profiles/
├─ craft/
├─ templates/
├─ migrations/
├─ tests/
└─ evals/
```

`routes/` is the executable workflow source. Documentation explains it; a second `workflows/` tree must not duplicate it. Directories are created only when their first tested consumer exists.

## 11. Release discipline

- Architecture, schema, engine, route/prompt, profile, and verification-toolchain versions are independent.
- A profile update is not a schema migration.
- Schema migrations are sequential, dry-runnable, checkpointed, and non-destructive on failure.
- V1 remains a frozen comparison baseline; migration imports proposed facts rather than copying all legacy files into canonical state.
- The user's unpublished manuscripts and expert comments stay local unless explicit publication authorization is given. They may be diagnostic cases but never public fixtures by default.
