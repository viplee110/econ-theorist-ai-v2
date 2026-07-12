# Architecture v0.1

Status: design baseline, not an implementation claim

Scope: economic theory only

Baseline date: 2026-07-11

## 1. Mission

Econ Theorist AI v2 should help a researcher discover, formalize, verify, explain, and revise economic theory at a frontier-research standard while reducing avoidable human reconstruction and rewriting.

The system optimizes a vector, not a single score:

1. formal truth and claim discipline;
2. importance and non-absorption of the contribution;
3. visibility and validity of the economic mechanism;
4. naturalness, necessity, and transparency of assumptions;
5. reader comprehension and manuscript coherence;
6. substantive human time required to reach a research-faithful draft.

No system state, checklist, panel vote, or language-model score can certify journal acceptance. Econometrica, Top-5, and leading field journals describe ambition, audience burden, and comparison sets.

## 2. Scope and anti-goals

### Included

- pure and applied microeconomic theory;
- information economics, game theory, mechanism and market design, contracts, industrial organization theory, social choice, networks, and related theoretical fields;
- theoretical work in macroeconomics, finance, labor, public economics, political economy, and other fields when the research object is a formal economic model;
- symbolic algebra, numerical stress tests, simulations, and formal proof tools used for theoretical discovery or verification.

### Excluded from the core

- econometrics, causal identification, estimation, calibration to data, data cleaning, regressions, experiments, and empirical robustness workflows;
- generation of empirical findings or claims from numerical model exploration;
- journal-style imitation, author imitation, or text-similarity optimization;
- fully autonomous confirmation of high-stakes scientific or external decisions;
- a promise that more agents, longer prompts, or more formalism implies better economics.

Empirical facts may motivate a theoretical question when properly sourced, but v2 does not conduct or write the empirical analysis.

## 3. Architectural constitution

The following rules are cross-cutting and normative.

### Economic reasoning before formal convenience

1. A project begins from an unresolved question and explicit benchmark set.
2. Mechanism hypotheses compete before formal model implementations compete.
3. A hand-solved benchmark and minimal mechanism example precede promotion of a general model.
4. Predictions are recorded before full derivation; disagreement with the derivation is evidence, not prose to be erased.
5. Each load-bearing economic arrow must have a formal witness, and each central formal object must have an economic identity.
6. Formal truth and mechanism truth are evaluated separately.

### Abstraction must pay rent

Abstraction is justified only when it buys at least one of the following: a sharper result, a wider economically meaningful domain, a unifying representation, a robustness guarantee, a possibility or impossibility frontier, or a simpler statement of the essential force. Otherwise it is a cost.

### Result architecture is plural

The system must support mechanism explanations, comparative statics and thresholds, characterizations and bounds, robustness/invariance/equivalence, design/implementation/impossibility, and concepts/representations/foundations. It must not force every project into a comparative-statics-plus-welfare template.

### Human taste remains an authority boundary

AI may search, derive, criticize, and prepare decision-complete proposals. A human controls promotion of the research question, central primitives, equilibrium concept, main result scope, novelty claim, economic argument spine, target audience, investment decision, and external release.

### State discipline serves research

Canonical state is a thin, typed spine. It contains only information needed for routing, authority, dependencies, claim scope, provenance, privacy, and evaluation. Rich prose, proofs, scripts, and papers remain substantive artifacts referenced by the state.

### Writing is reader belief engineering

The manuscript is compiled from a validated economic argument and an explicit reader path. A theorem does not substitute for intuition, and an intuition paragraph does not substitute for a tested mechanism. The same result may be expressed at different resolutions, but every expression must remain within the formal claim's scope.

### Evaluation is non-compensatory

Formal correctness, assumption completeness, claim entailment, and citation/contribution integrity are floors. Strong prose cannot compensate for failure on them. After those floors, evaluation remains a readiness vector rather than a single scalar score.

## 4. System map

```text
QUALITY AND AUTHORITY PLANE
  constitution · theory profiles · human decision rights · privacy
                         │
                         ▼
POSITIVE THEORY RESEARCH KERNEL
  question/benchmarks
    → primitive decomposition
    → mechanism tournament
    → prediction freeze + micro-example lab
    → mechanism stress tests
    → implementation tournament
    → theorem and boundary discovery
    → assumption/generality/absorption audit
                         │
                         ▼
FORMAL ASSURANCE
  re-derivation · symbolic checks · counterexamples · proof audit
  optional formal certificates · claim/evidence binding
                         │
                         ▼
VALIDATED ECONOMIC ARGUMENT
  economic argument graph · claim graph · result portfolio
                         │
                         ▼
THEORY MANUSCRIPT COMPILER
  Paper IR · reader-belief graph · section/result contracts
  layered explanation · canonical writer · fidelity critics
                         │
                         ▼
EVALUATION AND REVISION
  cold economist · field reader · formal reader · target referee
  human-effort measurement · reopen/pivot/repair routes

All layers use:
  typed canonical state · immutable events · dependency DAG
  route-specific contexts · isolated runs · provenance · recovery
```

The detailed owners are:

- positive research: `docs/architecture/theory_kernel.md`;
- Phase 3 formal-assurance execution semantics: `docs/implementation/phase3_contract.md`;
- state and execution substrate: `docs/architecture/state_runtime.md`;
- authoring: `docs/architecture/manuscript_compiler.md`;
- craft and target calibration: `docs/architecture/profiles_and_craft.md`;
- evaluation: `docs/architecture/evaluation.md`.
- integration walkthroughs: `docs/architecture/scenario_walkthroughs.md`.

## 5. Research control flow

V2 is route-based, not a single irreversible stage sequence. The following is a conceptual capability flow, not a second executable route registry. Exact route IDs and versions are owned by the registry specified in `docs/architecture/state_runtime.md`.

```text
discover.question
→ establish.benchmarks
→ hypothesize.mechanisms
→ freeze.predictions
→ construct.micro_examples
→ stress_test.mechanism
→ choose.formal_implementation
→ derive.claims
→ verify.claims_and_proofs
→ audit.assumptions_generality_absorption
→ validate.argument
→ design.reader_path
→ compose.manuscript_unit
→ review_and_revise
```

Failure routes are first-class. A failed global sign may become a threshold, bound, possibility set, or impossibility result. A theorem whose proposed mechanism fails must reopen the mechanism rather than receive a new post-hoc intuition. A closest-paper absorption may trigger mutation, demotion to an application, pivot, park, or kill.

Project maturity is derived from accepted and fresh capabilities. It is never advanced by writing “Stage 6” into a dashboard.

## 6. Core representations

The research layer uses typed, linked representations rather than a collection of competing status notes:

- question and benchmark set;
- primitives and economic argument graph;
- mechanism hypotheses, frozen predictions, and example suite;
- formal models and the economic-to-formal mapping;
- assumptions, claims, proof obligations, and verification records;
- literature evidence and closest-theory mappings;
- result portfolio and validated argument package;
- Paper IR, reader states, and manuscript contracts;
- decisions, risks, artifacts, and dependency edges.

The state architecture defines exact identity, status, transaction, and invalidation semantics. Detailed theory content remains in the relevant research objects and artifacts; the canonical snapshot does not become a manuscript database.

### Canonical vocabulary boundary

Cross-document names have one owner and one meaning:

- `PredictionRegister` is the aggregate manifest; `FrozenPrediction` is an immutable entry.
- `Claim.formal_kind` records theorem, lemma, proposition, corollary, and related formal labels; `Claim.economic_result_archetype` records one of the six economic contribution archetypes.
- `LiteratureEvidence` is a sourced record; `ClosestTheoryMap` is the structured comparison and absorption mapping.
- `TargetProfileRef` points to project target choices; `ResolvedProfileManifestRef` points to the exact composed theory/ambition/archetype/field/audience/overlay configuration used by a run.
- `CraftMoveRef` identifies a versioned, provenance-bearing functional craft card.
- `PaperIRRef` points to an immutable projection built from exact upstream research revisions; it is never a competing scientific state.

Aggregate theory graphs and packages are derived manifests over addressable canonical entities unless a later schema decision explicitly chooses a canonical root representation. Their payloads must not duplicate live claim, assumption, status, or authority fields.

## 7. Target calibration

Scientific discovery is governed first by a universal frontier-theory floor. Calibration is then composed from:

```text
theory mode
+ ambition mode
+ contribution archetype
+ field
+ target audience
+ soft journal overlay
+ submission constraints
```

Initial strong profiles are deliberately few:

- `frontier_theory_universal`;
- `top_general_interest_theory`;
- `top_field_theory`.

Venue overlays may adjust audience breadth, motivation burden, formal density, proof placement, and application expectations. They may not lower correctness, novelty, mechanism, or evidence standards, and they do not define the discovery search space before a central result exists.

## 8. V1 inheritance

The v1 baseline is commit `cc5f61254bb79e7436892e32ec88730ae14dd7f8` of `viplee110/econ-theorist-ai`.

V2 preserves v1's scientific disciplines by assigning each capability a typed owner and a parity test. It does not copy v1's long, overlapping workflow documents into new filenames. The authoritative migration ledger is `docs/architecture/v1_migration.md`.

The intended pattern is:

```text
v1 research discipline
→ explicit v2 object, route, validator, critic, or optional adapter
→ scenario-level parity test
```

Existing v1 examples remain historical or regression fixtures until they are replaced by complete theory cases with hand-solved examples, ablations, rival separation, formal claims, and reader tests.

## 9. Architecture budgets

To prevent the control system from overwhelming the research:

- the always-on kernel should remain approximately 1,500–2,000 tokens;
- ordinary routes must not read the whole project by default;
- generated state views should default to one compact status page;
- a new canonical field requires a route or validator that consumes it;
- a new persistent artifact requires non-reproducible substantive content;
- a new panel requires a stated risk that a cheaper targeted critic cannot resolve;
- schemas, prompts, and profiles have independent versions and change logs.

These budgets should become regression tests, not aspirational prose.

## 10. Human authority levels

- **L0 — deterministic operations:** validate, hash, render, compile, and rebuild derived views automatically.
- **L1 — reversible exploration:** agents may create provisional mechanisms, examples, models, proofs, prose previews, and critiques.
- **L2 — structural scientific decisions:** human confirmation is required before promotion of core questions, primitives, solution concepts, central claims, novelty, argument spine, and target/audience choices.
- **L3 — external or destructive actions:** submission, publication, external messages, and destructive operations require explicit authorization.

Provisional exploration may continue without interrupting the human at every local choice. It cannot cross a promotion boundary while carrying unresolved structural delegation debt.

## 11. Readiness to implement

Architecture v0.1 is ready for implementation review only when:

1. every high-value v1 capability has a v2 owner, parity test, or retirement rationale;
2. core entities, status dimensions, dependencies, authority, and transaction semantics are internally consistent;
3. each critical route has preconditions, context selectors, outputs, validators, failure routes, and promotion authority;
4. the manuscript compiler can trace every reader-facing central claim to a fresh result and mechanism packet;
5. the evaluation protocol freezes correctness floors, reader tests, human-effort measures, leakage rules, and v1/v2 comparison budgets;
6. four paper scenarios have been walked through on paper: greenfield discovery, foundational pure theory, revision of an existing theory manuscript, and an upstream assumption change that invalidates proofs and prose;
7. the user has reviewed the small number of structural choices with irreversible implementation consequences.

Implementation then begins with the smallest end-to-end vertical slice described in `docs/architecture/implementation_plan.md`.
