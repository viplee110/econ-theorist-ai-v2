# Phase 2 Theory-Kernel Vertical Slice Contract

Status: accepted and merged into `main`

Branch: `agent/phase2-theory-kernel-slice`

Accepted commit: `6a14d52e4655dc8b7d5a42e43467f4c58faba510`

Accepted Phase 1 base: `3ce5c6b8c92fbcbefb361b319a70894e173b119f`

## 1. Outcome

Phase 2 is complete only when one small, hand-solvable `mechanism_explanation`
case can traverse the complete theory route graph and produce a fresh semantic
argument package without using manuscript prose as scientific evidence:

```text
question and exact benchmarks
-> primitives
-> competing mechanisms
-> frozen predictions
-> hand-solved examples, ablation, rival separator, and boundary
-> mechanism promotion
-> competing formal implementations
-> formal-base promotion
-> claims, assumptions, proof obligations, and counterexamples
-> proof, interpretation, generality, and absorption audits
-> minimal result portfolio
-> argument-package candidate and immutable G5 dossier
-> human-confirmed G5 Decision
-> fresh derived validation closure
-> exact replay from genesis
```

The evaluation side closes a second executable path:

```text
two shared-attempt pre-result briefs plus sealed gold package
-> human implementation freeze
-> immutable blind case and transformed-variant manifests
-> independently generated, canonically locked candidate package
-> independent 17-dimension evaluator comparison
-> one terminal comparison record for the attempt
```

The executable cases are evaluation fixtures, not originality or publication
claims. Phase 2 validates the research semantics that an AI executor must obey.
It does not call a provider, show that an AI can recover the gold result, or
compile a manuscript.

## 2. Compatibility before capability

Phase 1 canonical history must remain byte-for-byte replayable. Phase 2 may not
replace a policy resource in place merely because the newest run needs a richer
contract.

- `registry.v1.json`, its instruction bundles, and its hash remain frozen.
- Phase 2 introduces a v2 policy catalog and selects policy by exact manifest
  bindings during replay.
- Historical provenance resolves route contracts by registry hash, route ID,
  and route version; it is never checked only against a current global hash.
- Historical v1 chains remain replayable, but v1 is not a live-write escape
  hatch. A live v1 transaction cannot create or mutate a packed Phase 2 entity
  or register anything recognizable as a candidate lock, and no new v1 run may
  begin after Phase 2 material has entered the project. Preflight and lock-time
  commit both enforce this boundary; pure historical replay does not.
- New contexts record the active registry and selector bindings. Historical
  contexts are deterministically recompiled under their historical bindings.
- The generic `EntityVersion` envelope remains canonical. Registered Phase 2
  entity types are validated through an exact `entity_type -> payload model`
  registry, so old generic entities do not acquire new meanings retroactively.
- The blind implementation freeze does not add a `DecisionKind` or change the
  v1 Decision schema. It reuses one effective human L2 `theory_mode` Decision
  with `status=confirmed`, `selected_option=freeze`, the transformed
  `PreResultBrief` stable ID as subject, the attempt ID as scope, and a decision
  time later than the brief. Both v1 and v2 decision-registry versions remain
  version 1; the transformed manifest stores the exact Decision version.

## 3. Phase 2 canonical theory objects

Phase 2 normalizes the following theory aggregates into typed canonical
entities. Rich algebra, full proofs, large comparison tables, and source text
remain immutable artifacts referenced by exact hash.

| Family | Initial typed entities |
|---|---|
| question | `ResearchQuestion`, `BenchmarkSet`, `PrimitiveGraph` |
| mechanism | `MechanismHypothesis`, `MechanismTournament`, `PredictionRegister`, `ExampleSuite`, `EconomicArgumentGraph` |
| formal | `ImplementationTournament`, `FormalModel`, `FormalizationMap`, `AssumptionMap`, `ClaimGraph`, `ProofObligation`, `VerificationRecord`, `VerificationBundle` |
| literature and contribution | `LiteratureEvidence`, `ClosestTheoryMap`, `AbsorptionAssessment`, `ResultPortfolio` |
| authority and handoff | `GateDossier`, `ValidatedArgumentPackage` |
| evaluation | `PreResultBrief`, `BlindCaseManifest`, `TransformedVariantManifest`, `VAPComparisonRecord` |

These 26 registered payloads each have a versioned schema. References are exact entity or
artifact versions. A payload cannot assert a derived scientific predicate such
as `formal_claim_is_verified` or `argument_is_validated`; validators derive
those predicates from fresh exact evidence.

All exact numerical fixture values use reduced rational numbers. JSON floats
remain forbidden.

## 4. Route contract

The Phase 2 registry registers 19 routes and enables 16: all thirteen theory
routes, dependency repair, and two sealed evaluation routes. The three
authoring routes -- `design.reader_path`, `compose.manuscript_unit`, and
`review.manuscript_unit` -- remain `not_implemented`.

| Route | Required exit |
|---|---|
| `frame.question_and_benchmarks` | typed question and exact benchmark set |
| `prepare.blind_case` | exactly two shared-attempt briefs and one sealed gold package, governed by one unique effective human freeze, produce immutable blind-case and transformed-variant manifests plus exact `seals` and `transforms` links |
| `evaluate.blind_argument_package` | exact manifest, variant, transformed brief, candidate, gold, and prior candidate lock produce one immutable independent comparison and exact `compares_to` link; the attempt becomes terminal |
| `decompose.primitives` | primitive graph and immutable G1 dossier |
| `tournament.mechanisms` | economically distinct hypotheses and serious rival or explicit waiver |
| `freeze.predictions` | immutable pre-result brief and frozen prediction register |
| `lab.micro_examples_and_ablations` | transparent functional-role coverage and append-only reconciliation |
| `promote.mechanism` | economic argument graph and immutable G2 dossier |
| `tournament.implementations` | selected and contrast formal implementations |
| `promote.formal_base` | bidirectional formalization coverage and immutable G3 dossier |
| `discover.claims_and_boundaries` | scoped claims, assumptions, obligations, and boundary objects |
| `verify.claims_proofs_and_interpretation` | independent exact verification without numerical-proof substitution |
| `audit.assumptions_generality_and_absorption` | assumption roles, closest-theory translation, and absorption outcome |
| `curate.result_portfolio` | smallest result set with distinct scientific jobs and immutable G4 dossier |
| `validate.argument_package` | deterministic package candidate and immutable G5 dossier |
| `repair.dependency` | smallest exact repair candidate for one stale root |

Routes restrict operation families, output entity and relation types, required
input evidence, purpose, compartments, and entry/exit validators. `begin` and
commit both check entry predicates. An operation allowlist alone is not a
scientific route contract.

## 5. Promotion gates

Agents may prepare dossiers and proposed Decisions. They may not confirm any
G1--G5 choice.

- A `GateDossier` is immutable, binds one exact `research_question_ref`, and
  includes that same ref among its exact ordered object refs.
- Its gate kind must equal the associated Decision kind.
- The associated Decision names the dossier as its subject and the dossier's
  ResearchQuestion stable ID as its scope.
- A dossier is committed before the human Decision that cites it.
- A later gate requires the prior effective human-confirmed gate and fresh
  governed inputs.
- Every gated route cites the exact ResearchQuestion version as evidence. All
  of its scientific outputs and relation endpoints must recursively resolve to
  that one question root; zero, mixed, foreign, or stale-version roots fail
  closed.
- Superseding an upstream gate stales every governed downstream package without
  deleting the old decision or scientific objects.

The minimum dossiers are:

- G1: question, exact benchmark delta, primitive scope, importance, kill
  condition, and risks;
- G2: serious rival, frozen predictions, reconciliations, examples, ablation,
  separation, boundary, and assumption risks;
- G3: implementation comparison, mapping coverage, primitives, timing,
  solution concept, and selected formal base;
- G4: headline claim, archetype, nugget, supported importance, reader update,
  economic consequence, proof/boundary/closest-theory risks, portfolio, and
  research-return decision;
- G5: exact argument package, qualified novelty, unresolved risks, prohibited
  overclaims, and every non-compensatory scientific floor.

`argument_is_validated` requires fresh exact evidence and effective human G1--G5
Decisions. Formal validity, semantic entailment, mechanism validity, literature
status, human acceptance, and freshness never compensate for one another.

## 6. Golden case: precision, complexity, and indivisible attention

The development fixture asks when more precise information can reduce realized
decision accuracy because it deters attention.

Let the equally likely state be `theta in {0,1}`. A signal with precision
`x in {ell,h}`, where `0 < ell < h <= 1`, is correct with probability
`(1+x)/2`. Before seeing it, the receiver chooses indivisible processing
`d in {0,1}`. Processing costs `kappa*x^2`; not processing yields accuracy
`1/2`; ties are processed.

Processing surplus and realized accuracy are

```text
Delta(x) = x/2 - kappa*x^2
d(x) = 1 iff kappa <= 1/(2*x)
Y(x;kappa) = 1/2 + d(x)*x/2.
```

The frozen headline conjecture is

```text
Y(ell;kappa) > Y(h;kappa)
iff 1/(2*h) < kappa <= 1/(2*ell).
```

The direct-information rival predicts that higher precision wins conditional
on processing. The selected mechanism is the extensive attention margin: the
gross value rises linearly while processing cost rises quadratically. A
constant-cost ablation removes the reversal. A contrast implementation with
continuous attention intensity has

```text
e*(x) = min{1, 1/(2*kappa*x)}
Y2(x;kappa) = 1/2 + min{x/2, 1/(4*kappa)},
```

which is weakly increasing in precision. Indivisible attention is therefore a
load-bearing mechanism condition, not a harmless tractability assumption.

The exact example suite covers benchmark, mechanism-on, constant-cost
ablation, rival separation, both threshold endpoints, and the region in which
neither signal is processed. The proof is split into separately auditable
obligations for signal value, processing threshold, threshold order, interval
partition, reversal, ablation, and continuous-attention monotonicity.

The fixture prohibits claims that coarse information is always better, that
endogenous attention alone suffices, that the result is robust to continuous
attention, that indivisibility is merely technical, or that accuracy is welfare
without an explicit social objective.

## 7. Absorption branch

After the control argument is assembled, the fixture injects a sealed verified
adoption-threshold comparator with the exact translation

```text
benefit -> x/2
cost -> kappa*x^2
adoption -> signal processing
output gain -> x/2
baseline output -> 1/2.
```

The accepted mutation has no first mapping failure. All eight comparison
dimensions -- benchmark, primitives, timing, solution concept, assumptions,
quantifiers, formal result, and economic lesson -- are `exact` or
`standard_argument`, so the headline result is classified as a
`direct_corollary`, absorption is `absorbed`, and the recommended route is
`mutate`. The correct response is:

- preserve the formal theorem and its verification;
- preserve any independently validated mechanism interpretation;
- set absorption to `absorbed`;
- stale the G4 investment dossier, argument package, and G5 closure while
  leaving only G1--G3 scientifically effective;
- route to mutate, demote, pivot, park, or kill;
- forbid renaming objects or adding decorative generality as a repair.

The mutation acceptance test requires the exact bytes and versions of the
promoted `FormalModel`, `ClaimGraph`, every `VerificationRecord`, and the
`VerificationBundle` to remain unchanged. Absorption changes investment and
novelty authority, not whether a proved theorem suddenly became false.

The control fixture may create an evaluation-only package marked
`publication_eligible=false` and `external_novelty_not_claimed=true`. It never
creates a production publication claim.

## 8. Blind reconstruction benchmark

Blind reconstruction evaluates scientific recovery rather than textual
imitation.

1. The case builder holds the source paper, gold semantic package, transforms,
   hidden probes, and answer key.
2. The generator receives only a pre-result brief: the question, primitives,
   institution, exact allowed benchmarks, tools, and budget.
3. Titles, authors, theorem statements, proofs, original intuition, and gold
   examples are excluded from generator contexts.
4. The candidate package hash is fixed before an evaluator may access gold.
5. The evaluator is read-only and cannot modify generator research state.
6. Feedback contaminates that attempt; any repair evaluation uses a fresh case
   or seed.

The candidate lock is an immutable `ArtifactRegistration`, not a new entity.
Its ID is `candidate.lock.<attempt_id>`, its version is 1, it has no
`supersedes`, and its media type is
`application/vnd.econ-theorist.candidate-lock+json`. Its stored bytes are the
canonical JSON bytes of the exact candidate `EntityVersion`; content hash and
byte size must agree exactly. `validate.argument_package` emits the blind
candidate and lock in the same transaction, and evaluation requires that lock
to be current before its run begins. The comparison's candidate hash, lock
hash, and canonical candidate bytes must all agree.

Blind metadata on a `ValidatedArgumentPackage` is an all-or-none triple:
`evaluation_attempt_id`, exact `pre_result_brief_ref`, and `generator_actor`.
Only an `evaluation_only` package may carry it. The evaluator must be a
different actor from the generator, must compare all 17 signature dimensions,
and may create at most one terminal `VAPComparisonRecord` for an attempt. Actor
independence is checked before context compilation or run-workspace creation,
so the generator cannot read gold and merely accept a later commit rejection.
A public classic cannot receive the `confirmatory_clean` disposition.

Both evaluation routes use exact-focus contexts with no optional neighbors and
no privacy omissions. Only `confirmatory_case_preparation` and
`confirmatory_evaluation` purposes may read `confirmatory_holdout`. Evaluation
contexts bind exact artifact registrations, canonical base64 artifact bytes,
and the exact implementation-freeze Decision; those bytes participate in the
compiled-context hash. `trace_only` links are protected pointers rather than
source-to-target data dependencies: both endpoints must safely flow into the
relation envelope, while the link cannot itself declassify either endpoint.

Three layers are reported separately:

- public classic reconstruction, useful but exposed to training-memory risk;
- semantics-preserving renaming, label permutation, timing/information changes,
  and exact parameter transforms with a hidden inverse map;
- synthetic confirmatory holdouts generated only after implementation is
  frozen.

The primary comparison is between normalized semantic package signatures:
question delta, benchmarks, mechanism graph, rivals, frozen predictions,
functional examples, selected/rejected implementations, formalization, claim
scope, assumptions, proof obligations, boundaries, absorption, portfolio,
gates, prohibited overclaims, and exact dependency traces. Text similarity,
BLEU, ROUGE, embeddings, and imitation of the original author's wording are
not success criteria.

Public reconstruction begins with an anonymized classic search-price problem.
The generator receives primitives and the zero-versus-positive search-cost
question, but never the paper name or paradox label. Transformed and synthetic
cases carry more evidentiary weight than the unmodified public case.

## 9. Required acceptance failures

The acceptance suite must reject at least the following:

- altering a frozen prediction after any result or example is observed;
- promoting a mechanism without a serious rival, ablation, and separator;
- selecting a tractable formal model whose mapping does not implement the
  promoted economic force;
- using finite examples, enumeration, simulation, or numerical agreement to
  verify a universal theorem;
- treating a proof-only assumption as economically necessary;
- validating semantic language stronger than the exact theorem scope;
- allowing an in-domain counterexample while retaining a universal claim;
- promoting a package with missing proof, boundary, mapping, or absorption
  floors;
- letting an absorber make a true theorem formally false;
- letting a true theorem compensate for absorbed novelty;
- disclosing a gold seal, inverse transform, or hidden transfer probe to a
  generator context;
- reading holdout bytes under any purpose other than the two exact
  confirmatory-evaluation purposes;
- evaluating without a prior exact candidate lock, with tampered candidate or
  lock bytes, or with a lock produced after evaluation begins;
- assigning the generator as evaluator, omitting any of the 17 semantic
  dimensions, or reporting an exposed public classic as `confirmatory_clean`;
- creating a second terminal comparison for the same attempt;
- using evaluator feedback inside the same confirmatory attempt;
- reusing a gate from another ResearchQuestion, another exact question
  version, or a mixed-scope authority basis, even within the same project;
- breaking byte-level replay of a Phase 1 transaction or context.

## 10. Explicit deferrals

Phase 2 does not implement Paper IR, manuscript prose, canonical writing,
cold-reader prose tests, target profiles, craft retrieval, venue overlays,
general multi-agent orchestration, agent voting, external release, or a claim
that the fixture is original or publishable. The first slice covers the
`mechanism_explanation` archetype; the other five archetypes remain specified
but not yet executable.

The Phase 2 exit is one replayable transformed blind case whose real v2
`prepare` and `evaluate` runs end in one terminal `VAPComparisonRecord`, plus an
absorption mutation that blocks production handoff without corrupting the
underlying formal record. The runtime fixture installs a deterministic,
content-addressed historical seed and immediately replay-validates its gold,
candidate, and lock before the real v2 runs; it does not use a live v1 write.
The separate contract suite enforces that a real blind candidate and its lock
must be emitted together by `validate.argument_package`. Neither test claims
that an AI has independently recovered a classic paper or reached Top-5
quality.
