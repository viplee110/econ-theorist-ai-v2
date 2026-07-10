# Architecture scenario walkthroughs

Status: Architecture v0.1 integration tests on paper

These scenarios test whether the architecture connects across research, state, verification, authoring, and human authority. They are not claims of research novelty and are not evaluation cases.

## Scenario A — greenfield theoretical discovery

### Starting instruction

“Develop a theory of disclosure when a receiver must pay attention to process a signal.”

This is a synthetic fixture. The system must not assume that the topic, mechanism, or result is novel.

### Question and benchmarks

The question route creates a provisional `ResearchQuestion`: when can a less informative disclosure policy induce more effective information use because attention is endogenous?

The `BenchmarkSet` contains:

- costless-attention benchmark: attention is costless and therefore exogenous;
- no-disclosure and full-disclosure policy benchmarks;
- the closest-theory benchmark to be populated only from verified literature evidence.

`G1_question_benchmark` asks whether the endogenous-attention margin creates an unresolved theoretical prediction, rather than approving the topic because it sounds relevant.

### Competing mechanisms

The mechanism tournament holds the question and benchmark fixed.

- M1, **posterior-shaping force:** coarser disclosure changes receiver actions through the posterior distribution, taking attention as given.
- M2, **attention-response force:** simpler disclosure raises the probability or intensity with which the receiver processes the signal.
- M3, **strategic dilution rival:** the apparent gain is driven only by the sender suppressing unfavorable states, not by endogenous attention.

Each mechanism records its affected decision margin, predicted outcome, boundary, rival, and kill counterfactual. No utility function or equilibrium technique wins this tournament merely because it is easy to solve.

### Prediction freeze and example suite

Before full derivation, the `PredictionRegister` stores `FrozenPrediction` entries:

- M2 predicts that some reduction in informativeness can increase action responsiveness when attention cost is intermediate;
- the net welfare or sender-payoff effect is unresolved because information loss and attention gain oppose each other;
- the effect should disappear when attention is costless and may disappear when attention is prohibitively costly.

The example lab assigns functional roles rather than fixed slots:

- `benchmark_costless`: two states and two actions with costless attention;
- `mechanism_on`: the smallest hand-solvable costly-attention environment exhibiting the proposed margin;
- `rival_separator`: a parameter pair where M2 and M3 make different predictions;
- `cost_boundary`: a zero-cost or high-cost case in which the force disappears or reverses.

One case may fill multiple roles. If no minimal mechanism-on case exists, M2 is falsified or the environment is too complicated to isolate it; the system may not substitute a general fixed-point model and post-hoc intuition.

### Formal implementation tournament

Only after `G2_mechanism` does the system compare implementations, for example:

- binary attention choice versus continuous attention;
- direct signal design versus a reduced-form informativeness order;
- single receiver versus a strategic receiver population.

The judge evaluates benchmark closure, mechanism fidelity, assumption debt, theorem bite, boundary visibility, tractability, and reader legibility. It does not reward maximal generality by default.

`G3_formal_base` then locks the selected primitives, timing, information structure, and solution concept before a central claim becomes a stable dependency.

### Claim and assurance path

The result portfolio may discover that a global sign is false. The failure route can reframe the contribution as:

- a threshold characterization;
- a possibility frontier;
- an invariance result over attention technologies;
- an impossibility of obtaining both maximal information and maximal attention.

`G4_result_investment` compares the candidate nugget, primary archetype, surprise and importance, reader-belief update, economic consequence, proof and absorption risks, and expected return. If the human invests, each claim is linked to assumptions, proof obligations, example witnesses, and the closest-theory mapping. Numerical scans can locate a counterexample or conjectured region; they cannot certify the theorem.

### Authoring path

After G4, formal verification, semantic entailment, mechanism validation, and absorption remain separate. Only `G5_argument_validation` may approve the fresh `ValidatedArgumentPackage` and hand its result contract to authoring:

```text
reader question
→ costless-attention benchmark
→ endogenous-attention prediction
→ exact theorem or characterization
→ direct information loss
→ attention response
→ net-effect condition
→ zero/high-cost boundaries
→ proof roadmap
→ economic consequence
```

The introduction is compiled after this economic core exists. A cold reader must be able to predict what happens in an unshown nearby attention-cost environment. Failure reopens the mechanism or reader path, not merely the prose style.

### Architecture properties exercised

- mechanism/implementation separation;
- prediction integrity;
- archetype-sensitive functional example roles;
- plural result archetypes;
- proof versus numerical evidence;
- human G1 question, G2 mechanism, G3 formal-base, G4 investment, and G5 argument gates;
- result packet to manuscript traceability.

## Scenario B — revision of an existing theory manuscript

### Inputs

The user provides a LaTeX manuscript, appendix proofs, references, and expert comments. The material is private unless the user authorizes release. It is not placed in a public craft corpus or hidden benchmark automatically.

### Reconstruction

The intake route does not trust the manuscript's own labels as canonical truth. It proposes:

- economic objects and their formal symbols;
- agents, timing, information, actions, payoffs, and solution concept;
- assumptions and where each enters;
- formal claims and proof dependencies;
- the claimed mechanism and benchmark;
- literature and novelty claims with evidence status;
- current section and result hierarchy.

The human confirms only the structural reconstruction that will become a stable dependency. The original files remain substantive artifacts protected by hashes.

### Expert-comment translation

Suppose the comments identify four problems:

1. an object changes economic name across sections;
2. an auxiliary function is defined formally but never interpreted;
3. a primitive-looking assumption has no familiar sufficient conditions;
4. the result may need fewer assumptions than the proposition states.

The system translates these into object-level proposals:

- update the economic ontology and terminology constraints;
- add the auxiliary function to the mechanism/formalization map or remove it from the main exposition;
- reopen the relevant `AssumptionMap` entry for primitive interpretation, examples, and boundary witnesses;
- run assumption ablations and re-derive the exact claim;
- invalidate affected verbal translations, assumption discussions, proof roadmaps, and summary claims.

The comments do not become generic style instructions. They are linked to exact objects and dependencies.

### Revision routes

The router chooses registered routes with explicit parameters:

- `repair.dependency` with `target=claim` if the formal scope is wrong;
- `audit.assumptions_generality_and_absorption` with an assumption focus if naturalness or necessity is unresolved;
- `repair.dependency` with `target=mechanism`, followed by the applicable mechanism/example routes, if the proposed intuition does not survive ablation;
- `compose.manuscript_unit` with `unit=result_block` if the research state is sound but the reader path is weak;
- `design.reader_path` with a manuscript-architecture scope if proof order and reader order are confused.

A proof critic sees the model, assumptions, claim, and proof. A cold reader sees the manuscript but not author rationalizations. The canonical writer receives the accepted revision brief and relevant Paper IR only.

If reconstruction changes the formal base, central result, or argument spine, the corresponding G3, G4, or G5 Decision is reopened. A revision that is purely expository may reuse fresh upstream Decisions, but manuscript promotion still requires the effective runtime authority for that version.

### Promotion test

The revised section is not promoted merely because it is smoother. It must:

- preserve exact claim scope;
- give every core object a stable economic identity;
- explain assumption roles without equating an analogy with a proof;
- make the benchmark, mechanism, result, and boundary recoverable;
- reduce economic-semantic repair in expert review.

### Architecture properties exercised

- private artifact policy;
- manuscript-to-state reconstruction;
- expert-feedback ingestion;
- assumption and terminology dependencies;
- isolated critics and canonical writer;
- substantive human-effort evaluation.

## Scenario C — upstream assumption change

### Initial accepted state

Assumption A4 provides a shape restriction used by Lemma L2. L2 supports central Result R1, its proof verification V1, the introduction claim C-intro, Result Block RB1, and a welfare implication W1. The proposed mechanism also uses A4 only for the net ordering, not for the direct behavioral response.

The materialized snapshot renders separate dimensions; `human_acceptance` and `freshness` are projections from effective Decisions and dependencies rather than agent-authored fields:

```text
R1.human_acceptance = human_confirmed
R1.formal_validity = verified_in_scope
R1.interpretation_validity = validated
R1.freshness = fresh
```

### Proposed change

The human asks whether A4 can be weakened to A4'. The agent opens a provisional route and cannot overwrite A4 or mark the weaker claim `human_confirmed` or `verified_in_scope`.

Before promotion, the dependency engine displays a blast-radius preview:

- A4 and its naturalness explanation: superseded if approved;
- L2, R1, V1, and W1: hard stale;
- C-intro and RB1: hard stale because they state R1;
- the scope-sensitive `ClosestTheoryMap`, `ResultPortfolio`, and `ValidatedArgumentPackage`: stale;
- the direct-effect mechanism arrow: remains fresh if independent of A4;
- the net-effect arrow and boundary explanation: stale;
- unrelated results and the target profile: remain fresh.

### Re-derivation outcomes

There are four legitimate outcomes:

1. R1 holds under A4', and a new proof/verification restores formal freshness; semantic and interpretation predicates are rechecked separately.
2. Only a weaker R1' holds; the claim graph and every stronger prose surface are revised.
3. A threshold or bound replaces the global result; the result archetype and narrative spine reopen.
4. A counterexample refutes the proposed weakening; A4 remains load-bearing and the failure witness is retained.

The system cannot silently add a different shape restriction, change the domain, or rewrite the intuition to make the attempted weakening look successful.

### Transaction and recovery

If the human accepts the change, a superseding decision event records alternatives, rationale, evidence revisions, and blast radius. Canonical promotion is atomic. If the process fails between prepare and finalize, recovery uses before/after state hashes and the immutable transaction record; it never resolves the conflict by last-write-wins.

### Recompilation

Only stale manuscript units are recompiled. The canonical writer receives the revised claim, assumption role, boundary, and neighboring context. The introduction and conclusion are checked for stronger legacy wording. The target overlay cannot preserve a broad claim that the new result no longer supports.

### Architecture properties exercised

- field-level dependency invalidation;
- separation of `human_acceptance`, `formal_validity`, `interpretation_validity`, and `freshness`;
- blast-radius preview;
- superseding human decisions;
- partial mechanism validity;
- atomic promotion and recovery;
- selective manuscript recompilation.

## Scenario D — foundational pure-theory characterization

The synthetic question is when menu-dependent choice correspondences admit a representation by one stable ordering. `G1_question_benchmark` fixes the unrestricted-correspondence benchmark and records candidate, nonbinding archetypes.

Before proof, the `PredictionRegister` stores conjectured sufficiency, necessity, uniqueness limits, and what should fail when each consistency axiom is removed. The `ExampleSuite` uses functional roles: a representable benchmark, an axiom-independence witness, a nonrepresentable cycle, and a uniqueness boundary. No fixed number is imposed.

`G2_mechanism` promotes the foundational force only after discriminating the representation from rival axiom systems. `G3_formal_base` locks the domain, axioms, and representation map. `G4_result_investment` selects `concept_representation_foundation` as primary only after reviewing the characterization, nugget, importance, reader update, boundaries, and proof risk.

The claim graph separates sufficiency, necessity, uniqueness, and independence obligations. A valid proof can retain `formal_validity: verified_in_scope` even if its proposed economic interpretation fails. `G5_argument_validation` requires formal verification, semantic entailment, interpretation validation, nonabsorption, and human approval as separate checks.

The archetype-specific result contract records:

```text
direct_effect: not_applicable
strategic_or_equilibrium_feedback: not_applicable
welfare_or_policy: not_applicable
economic_consequence: identifies when many menu problems share one stable economic ordering
```

Reader transfer asks whether a nearby axiom system admits the representation and which necessity step fails. It does not invent a comparative static, strategic feedback, empirical claim, or welfare conclusion.

## Integration findings

The walkthroughs impose five requirements on implementation:

1. dependencies must resolve below whole-file granularity;
2. mechanism arrows and formal claims need separate identities and mappings;
3. provisional exploration must be able to continue without promotion;
4. critic contexts must be independently reproducible;
5. authoring outputs must point back to exact research-state revisions.

If an implementation cannot satisfy these requirements with a small vertical slice, the architecture should be simplified before adding prompts, profiles, or multi-agent panels.
