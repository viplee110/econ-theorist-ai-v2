# Positive Theory Research Kernel

Status: Architecture v0.1 specification

Owner: positive economic reasoning and scientific promotion gates

Scope: pure and applied economic theory only

## 1. Contract

The kernel turns a `ResearchQuestion` into a `ValidatedArgumentPackage`. It
prevents a convenient formal model from being mistaken for an economic
mechanism and prevents intuition from being written after the result without a
test of the proposed economic force.

The kernel MUST establish:

1. an important unresolved delta from exact benchmarks;
2. a discriminated economic mechanism, conflict, or foundational force;
3. a minimal credible formal implementation;
4. claims true at their stated assumptions, domain, and quantifiers;
5. transparent assumption roles and boundaries;
6. nonabsorption by the closest theory;
7. an economic argument reconstructible without reverse-engineering the proof.

Formal truth, interpretation validity, literature status, human acceptance, and
freshness are non-compensatory and independent.

Included: theory discovery, analytical derivation, symbolic checks, finite
numerical exploration, simulation, counterexample search, and optional formal
methods used to discover or verify theory.

Excluded: econometrics, identification, estimation, calibration to data,
regression, experiments, empirical robustness, and manuscript prose. Finite
numerical evidence may falsify a universal claim but MUST NOT prove one.

"Mechanism" is archetype-sensitive. It may be an equilibrium feedback, the role
of an axiom, a minimal conflict behind an impossibility, or a representation that
changes an economic conclusion. The kernel MUST NOT force conceptual theory
into comparative-statics, welfare, policy, or empirical templates.

## 2. Result archetypes

Every central claim declares one primary archetype. The declaration selects its
required examples, proof obligations, and boundary tests.

| Archetype | Contribution contract | Decisive evidence |
| --- | --- | --- |
| `mechanism_explanation` | A new force resolves a pattern, puzzle, or benchmark failure. | Mechanism-on case, ablation, serious rival, and formal witness for the decisive arrow. |
| `comparative_statics_threshold` | A change produces a sign, ordering, threshold, or regime shift. | Direct/equilibrium decomposition, exact monotonicity scope, and boundary or reversal case. |
| `characterization_bounds` | Necessary/sufficient conditions or tight bounds describe the object. | Separate necessity and sufficiency witnesses; tightness or independence examples. |
| `robustness_invariance_equivalence` | A result survives meaningful changes or environments map to one object. | Explicit mapping, preserved claim, relevant variants, and failure boundary. |
| `design_implementation_impossibility` | An institution implements an objective or desiderata conflict. | Incentive/feasibility map, construction or minimal conflict, and decisive relaxation. |
| `concept_representation_foundation` | A concept, axiom, or representation changes conclusions or modeling practice. | Economic interpretation, representation/independence evidence, and a changed-conclusion case. |

## 3. Ownership and scientific predicates

This document owns theory semantics, route preconditions, and scientific gates.
`state_runtime.md` owns schemas, versions, transactions, status vocabularies,
authority storage, dependency propagation, and recovery. The manuscript compiler
owns reader-facing prose.

Sets, graphs, maps, suites, and packages below are domain aggregates. The runtime
may normalize them into entities, typed relations, and referenced artifacts but
MUST preserve these domain contracts as the authoritative theory semantics;
project-state truth remains governed by `state_runtime.md`.

The runtime derives, rather than lets an agent assert, these predicates:

- `question_is_investable`;
- `mechanism_is_discriminated`;
- `formal_implementation_is_admissible`;
- `formal_claim_is_verified`;
- `semantic_translation_is_entailed`;
- `mechanism_interpretation_is_validated`;
- `contribution_is_nonabsorbed`;
- `argument_is_validated`.

## 4. Canonical theory objects

### 4.1 ResearchQuestion and benchmark set

`ResearchQuestion` records the phenomenon, logical puzzle, design problem, or
conceptual gap; the object to explain; why an answer matters; optional candidate
archetypes that do not constrain discovery; a kill condition; and human-approved
scope. The primary archetype is locked only with the central result at G4.

Each benchmark records exact primitives, timing, solution concept, prediction,
and why it does not settle the question. A named "standard model" is not an exact
benchmark. Advance requires a reader to state the unresolved delta without
seeing the proposed model.

### 4.2 PrimitiveGraph and MechanismHypothesis

`PrimitiveGraph` distinguishes actors, choices, constraints, information,
timing, institutions, preferences/technology, interactions, equilibrium
objects, perturbations, and outcomes. Every edge has economic meaning. A
reduced-form condition is linked to primitive sufficient conditions or marked
as an unresolved scope cost.

Each `MechanismHypothesis` states:

- the decision margin or foundational distinction;
- the initiating wedge, constraint, axiom, or information change;
- the applicable response/feedback chain or foundational transformation/conflict;
- predicted consequence and boundary;
- expected load-bearing conditions;
- a signature distinct from a serious rival;
- a killer test that would count against it.

Hypotheses with identical arrows and signatures are one candidate, not two.

### 4.3 PredictionRegister, FrozenPrediction, and ExampleSuite

`PredictionRegister` is the aggregate whose entries are `FrozenPrediction`
objects. Each entry is recorded before the full derivation or computation is
observed and contains the predicted result, proposed economic chain, expected
conditions, ablation outcome, rival difference, and surprise/falsifier. Its
original content is immutable; later reconciliation is append-only.

An `ExampleSuite` contains, as the archetype requires:

1. an exact benchmark;
2. a transparent, hand-solved minimal mechanism/axiom/constraint-on case;
3. an ablation or relaxation removing the proposed force while preserving
   unrelated structure;
4. a rival-separating case;
5. a boundary, failure, tightness, or independence case.

These are functional roles, not fixed E0--E3 labels or a required cardinality.
One transparent case may fill several roles; additional cases are required only
when the archetype needs them for discrimination, necessity, or scope.

Every case traces primitive/axiom/constraint -> choice or admissible set ->
interaction/representation -> equilibrium/logical consequence -> outcome.
Black-box computation is not hand-solving. Examples support discrimination and
can falsify conjectures; they do not prove universal theorems.

### 4.4 EconomicArgumentGraph

`EconomicArgumentGraph` refines the selected hypothesis. Every load-bearing
economic arrow links to a primitive or assumption, a response or constraint, a
formal witness, a supporting/separating/boundary case, and the exact conclusion
it supports. It distinguishes direct effects from equilibrium feedback.

A theorem may be true while this graph is false. Formal verification therefore
MUST NOT automatically validate interpretation.

### 4.5 FormalModel and FormalizationMap

`FormalModel` declares formal objects, timing, choice/strategy spaces,
information and beliefs where relevant, feasibility, solution concept, and
outcomes.

`FormalizationMap` is bidirectional:

- every load-bearing economic node/edge maps to a formal object, restriction,
  or derived relation;
- every central formal object states its economic identity and research job.

An unwitnessed economic arrow and unexplained central mathematical structure
both block implementation promotion.

### 4.6 AssumptionMap

For each assumption, `AssumptionMap` records exact content and quantifiers;
economic interpretation; primitive or reduced-form status; role (definition,
mechanism, existence, uniqueness, selection, tractability, regularity, sign, or
domain); dependent claims, proof steps, and argument arrows; satisfying cases;
weakening/violation attempts; primitive sufficient conditions; and scope cost.

The map MUST distinguish "the result is false without it" from "the current
proof uses it." A tractability condition MUST NOT be called economically
necessary without necessity evidence.

### 4.7 ClaimGraph, ProofObligation, and VerificationRecord

Each `ClaimGraph` node records archetype, scientific job, formal statement,
domain, quantifiers, assumptions, semantic translation, dependencies,
mechanism link, proof obligations, verification records, and closest-theory
comparator. Jobs include headline, enabling, decomposition, necessity,
converse, boundary, robustness, negative result, and application.

The graph identifies one contribution spine. Additional results need a distinct
job; theorem density is never a promotion criterion.

A `ProofObligation` is the smallest auditable burden needed by a claim. A
`VerificationRecord` says what was checked, by which valid method, against which
revisions, and with what limitations. Formal truth, semantic entailment, and
mechanism validity are checked separately.

### 4.8 LiteratureEvidence and ClosestTheoryMap

`LiteratureEvidence` grounds assertions about prior theory. `ClosestTheoryMap`
compares the exact benchmark, primitives, solution concept, assumptions,
quantifiers, result, and economic lesson. It classifies the project as duplicate,
direct corollary, special case, generalization, converse, different mechanism,
different boundary, application, or non-comparable.

Absorption asks: does the closest verified result plus a standard argument
available to the intended audience already deliver the central claim or its
economic lesson? Notation or prose differences do not establish novelty.

### 4.9 ResultPortfolio and ValidatedArgumentPackage

`ResultPortfolio` selects the smallest results needed for the contribution
spine: headline, enabling, mechanism/necessity, boundary/negative, and valuable
robustness results. It records each result's job and marginal value; results with
no distinct job are removed or demoted.

`ValidatedArgumentPackage` is the normal authoring handoff. It references the
approved question/benchmarks; one-sentence economic nugget; selected mechanism
and serious rejected rivals; `PredictionRegister` and honest reconciliation;
`ExampleSuite`; graphs, model, and formalization; assumptions, claims, proofs,
and verification; closest-theory map and qualified novelty; result portfolio;
derived generality frontier; unresolved risks; and prohibited overclaims.

It is a semantic package, not prose. Authoring may change resolution but MUST
NOT invent a mechanism, widen a claim, hide a boundary, or upgrade novelty.

## 5. Route graph

```text
frame.question_and_benchmarks
-> decompose.primitives
-> tournament.mechanisms
-> freeze.predictions
-> lab.micro_examples_and_ablations
-> promote.mechanism
-> tournament.implementations
-> promote.formal_base
-> discover.claims_and_boundaries
-> verify.claims_proofs_and_interpretation
-> audit.assumptions_generality_and_absorption
-> curate.result_portfolio
-> validate.argument_package
```

Routes are revisitable capabilities, not irreversible stages. Every route MUST
declare preconditions, context, outputs, validators, human authority, and named
failure routes. Maturity is derived from fresh accepted capabilities.

An existing model/theorem enters through normalization and reverse
`FormalizationMap`; known results are prior evidence, never retroactive frozen
predictions. Revision comments reopen the smallest sound upstream dependency: a
false intuition reopens the argument/mechanism, an assumption objection reopens
the map/model, and absorption reopens the claim/question. Prose cannot close a
scientific objection.

## 6. Two tournaments and the example laboratory

### 6.1 Mechanism tournament

This tournament asks which economic force could answer the question. Candidates
must differ in primitive arrows, margins, feedbacks, axiom conflicts, or
representations. Compare them without a synthetic score on benchmark resolution,
discriminability, explanatory compression, portability, importance/surprise,
assumption burden, and killer-test quality.

At least one serious rival is required unless an archetype-specific waiver
explains the alternative rivalry test. Selection requires frozen-prediction and
example evidence plus human confirmation; an agent vote is not evidence.

### 6.2 Implementation tournament

This tournament asks for the smallest credible formal environment that
faithfully implements the selected force and yields a valuable theorem frontier.
Compare fidelity, minimality, tractability/proof risk, mapping transparency,
rival separation, meaningful reach, closest-theory differentiation, and theorem
leverage.

There is no fixed candidate quota. At least one contrast implementation or a
reasoned human waiver is required. A feature is admitted only if it changes a
central claim, makes the mechanism valid, reveals a meaningful boundary, covers
a new economic class, or reduces proof risk without obscuring the argument.

The tournaments MUST NOT collapse: models can share a mechanism, and one model
can host several mechanisms. A failed model does not falsify a mechanism; a
solved model does not validate its advertised mechanism.

### 6.3 Prediction reconciliation and ablation

After solution, every frozen prediction is reconciled as confirmed,
right-result/wrong-reason, informative failure, non-discriminating,
implementation failure, or unresolved.

If an ablation leaves the result unchanged, diagnose: false advertised
mechanism, hidden substitute channel, failed ablation, or genuine invariance.
Only the last supports promotion without mechanism revision, and it requires a
proof and failure boundary.

Generalize a solved example by removing details one at a time and opening the
corresponding conjecture/proof obligation. Stop when added abstraction no longer
changes the economic lesson or destroys transparent interpretation.

## 7. Scientific audits

### 7.1 Claim and assumption floors

`formal_claim_is_verified=true` requires explicit objects, domain, quantifiers,
and assumptions; validly discharged proof obligations; relevant edge/off-path
checks; fresh inputs; and no in-domain unresolved counterexample.

`semantic_translation_is_entailed=true` requires the economic-language
translation to stay within that exact formal statement and scope.
`mechanism_interpretation_is_validated=true` separately requires evidence for
the proposed economic chain, representation, or conflict. Either may fail while
the formal claim remains verified. `argument_is_validated` composes the fresh
applicable predicates, nonabsorption, and G5 human authorization; it never
back-propagates interpretation failure into formal validity.

For each load-bearing assumption, audit its exact job, result-versus-proof
necessity, primitive foundation, nonempty natural class, plausible violation,
surviving conclusion, and permitted descriptive language. Unknown necessity
remains unknown.

### 7.2 Generality frontier

Generality is a derived view over verified model variants, assumptions, claims,
and the result portfolio, not another canonical object. It marks economically
meaningful dimensions as verified, false, or open. Broader scope is preferred
only when its economic value justifies assumption, proof, and exposition costs.
A clean boundary or tight result may dominate ornamental generality.

### 7.3 Absorption

Run absorption after a central claim exists and rerun it whenever claim scope,
model base, assumptions, or economic lesson changes. Outcomes are nonabsorbed,
partially absorbed, application-only, unresolved evidence, or absorbed. Valid
routes are substantive mutation, converse/boundary search, demotion, pivot,
park, or kill--never renaming or decorative generality.

## 8. Human promotion gates

Gates are decision boundaries, not mandatory interruptions during reversible
search. Agent approvals remain provisional.

| Gate | Required dossier | Human decision |
| --- | --- | --- |
| `G1_question_benchmark` | Question, exact delta, primitive scope, importance, kill condition, risks. | Approve/revise/pivot/park/kill the problem. |
| `G2_mechanism` | Serious rivals, `PredictionRegister`, examples, ablations, separation, assumption risks. | Promote a force or reopen the tournament. |
| `G3_formal_base` | Implementation comparison, mapping, primitives, timing, solution concept. | Lock the model base or reopen search. |
| `G4_result_investment` | Headline claim; proposed primary archetype; nugget; surprise/importance; reader-belief update; economic consequence; proof/boundary/closest-theory risks; portfolio; expected research return. | Lock primary archetype and central scope; invest/narrow/mutate/pivot/park/kill. |
| `G5_argument_validation` | Complete package, qualified novelty, risks, prohibited overclaims. | Approve argument spine/handoff or reopen a named dependency. |

## 9. Named failure routes

| Signal | Required route | Forbidden repair |
| --- | --- | --- |
| Benchmark settles the question. | Sharpen the delta, change question, or stop. | Add complexity to manufacture novelty. |
| Hypotheses are synonyms. | Merge and rebuild from distinct arrows/conflicts. | Vote over renamed copies. |
| Frozen prediction fails. | Preserve; inspect feedback/hidden conditions; revise hypothesis. | Rewrite prediction or add post-hoc intuition. |
| Example is opaque. | Simplify agents/actions/states/timing/values. | Substitute a large black-box simulation. |
| Ablation has no effect. | Diagnose false force, hidden channel, failed ablation, or invariance. | Declare robustness without proof. |
| Rivals do not separate. | Find a separator, merge, or test equivalence. | Select rhetorically or by agent majority. |
| Solved model does not map to force. | Reject/demote model; repair mapping. | Treat tractability as mechanism evidence. |
| Mechanism survives but model fails. | Try another implementation or revise feasibility. | Abandon force because one model is hard. |
| Main conjecture is false. | Classify counterexample; seek meaningful threshold/bound/impossibility or stop. | Add assumptions until old sentence is true. |
| Proof fails. | Localize obligation; seek independent proof/counterexample. | Promote from examples or confidence. |
| Theorem true, intuition false. | Reopen argument graph and mechanism gate. | Preserve intuition because proof passed. |
| Assumption unnatural/load-bearing. | Primitive-hunt, weaken, bound, narrow, or reconsider. | Call it mild/standard/technical. |
| Generality hides economics. | Roll back; demote wider result. | Maximize scope mechanically. |
| Closest theory absorbs claim. | Mutate/demote/pivot/park/kill. | Hide comparator or rename objects. |
| Formal and numerical checks disagree. | Reproduce and localize as falsification signal. | Let simulation override universal proof. |
| Argument cannot be reconstructed. | Rebuild examples/arrows before authoring. | Send to a style pass. |

## 10. Compact v1 inheritance

| V1 discipline | V2 owner here |
| --- | --- |
| Scientific Taste, Nugget, Occam, Complexity Shield | Question dossier, economic nugget, implementation comparison, generality stop rule. |
| Primitive Hunter, Economic Logic Map | `PrimitiveGraph`, `EconomicArgumentGraph`, primitive-foundation search. |
| Model Tournament | Separate mechanism and implementation tournaments; no fixed quota. |
| Micro-Example Gate, Example-to-Theory | Freeze, hand-solved suite, ablation, rival separation, proof obligations. |
| Main-Theorem Gate, Contribution Lock | `ClaimGraph`, `ResultPortfolio`, G4 and G5. |
| Assumption/Generality Ledgers | `AssumptionMap` and derived frontier. |
| Counterexample Search, Proof Audit | Obligations, verification records, boundary cases, failure routes. |
| Evidence Ledger, Absorption Test | `LiteratureEvidence`, `ClosestTheoryMap`, nonabsorption predicate. |

This migrates research discipline, not v1 stage numbers, fixed quotas, long
prompts, duplicated Markdown state, or journal-bound filenames. Full parity and
retirement decisions belong to `v1_migration.md`.

## 11. Executable acceptance tests

Every normative promotion rule MUST have a deterministic validator, binary
scenario assertion, or machine-checkable human dossier. A fixture declares
input, attempted route, expected predicates/next routes/gate, forbidden
promotions, and required diagnostics.

| ID | Binary assertion |
| --- | --- |
| `TK-001` | Empirical estimation output is rejected as out of scope. |
| `TK-002` | Missing exact benchmark prediction/delta blocks `question_is_investable`. |
| `TK-003` | Missing applicable force chain/signature/killer test blocks mechanism entry. |
| `TK-004` | Identical arrows/signatures merge rather than inflate rival count. |
| `TK-005` | Post-solution edit to a frozen prediction is rejected; reconciliation is allowed. |
| `TK-006` | Imported known result is prior evidence, not a retroactive prediction. |
| `TK-007` | Missing hand-solved case or applicable ablation blocks mechanism promotion. |
| `TK-008` | Finite examples/simulation cannot verify a universal claim. |
| `TK-009` | Unexplained no-effect ablation blocks promotion. |
| `TK-010` | Nonseparated rivals require separator/merge/equivalence/waiver, not a winner. |
| `TK-011` | Formal-base promotion before mechanism/example evidence is rejected. |
| `TK-012` | Unmapped economic arrow or central formal object blocks implementation. |
| `TK-013` | An example violating a cited claim assumption cannot support that claim. |
| `TK-014` | Missing domain/quantifier/assumption/proof link blocks formal verification; bad translation blocks semantic entailment only. |
| `TK-015` | A formal claim may pass while contradicted interpretation keeps the argument invalid. |
| `TK-016` | Proof-only regularity cannot be labeled economically necessary. |
| `TK-017` | Upstream assumption change stales dependent claims, proofs, arrows, comparisons, and packages. |
| `TK-018` | Unsupported generality/robustness language blocks package validation. |
| `TK-019` | Changed central claim invalidates the prior absorption audit. |
| `TK-020` | Direct corollary of closest verified theory is classified absorbed. |
| `TK-021` | Result with no distinct scientific job is excluded absent explicit exception. |
| `TK-022` | Agent-authored structural approval cannot create stable promotion. |
| `TK-023` | Any missing correctness/nonabsorption/human floor blocks package emission. |
| `TK-024` | Each central lesson must trace to claim, assumptions, arrows, and verification. |

Detailed integration narratives for the core routes are owned by
`scenario_walkthroughs.md`; this kernel retains six binary coverage cases:

| Scenario | Required assertion |
| --- | --- |
| Greenfield competing mechanisms | Functional example roles, preserved prediction, G1--G5 in order, proof/absorption before handoff. |
| Existing theorem reconstruction | Preserve prior result, reverse-map model, no fabricated prediction, withhold argument until upstream contracts pass. |
| False global sign | Keep counterexample; route to threshold/bound/regime/stop without silent restriction. |
| True theorem, wrong mechanism | Formal validity may pass; interpretation and package fail; reopen mechanism. |
| Foundational theory | Use archetype-appropriate consequence/independence tests; invent no welfare or empirical claim. |
| Upstream revision | Invalidate dependent science and handoffs while preserving unrelated branches. |

## 12. Exit criterion

The kernel exits only with a fresh `ValidatedArgumentPackage`, all applicable
correctness floors, and required human decisions. Otherwise it returns a named
failure route, bounded provisional package, pivot/park/kill recommendation, or
request for scientific judgment. Polished prose is not a fallback and package
validation is not a claim of journal acceptance.
