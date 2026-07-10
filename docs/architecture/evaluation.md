# Evaluation Architecture

## Purpose

Evaluation determines whether v2 produces more correct, more economically intelligible, and less labor-intensive theory manuscripts than the frozen v1 baseline. It is not a marketing score and does not estimate the probability that a journal will accept a paper.

The evaluation system is theory-only. Numerical work appears only as theorem stress testing, counterexample search, symbolic support, or formal verification. No empirical-design, data-quality, identification, or treatment-effect metrics belong in this evaluation architecture.

The principal outcomes are:

1. formal and evidentiary correctness;
2. reader transfer of the archetype-appropriate economic or conceptual lesson;
3. quality of argument and exposition;
4. human effort required to reach an acceptable draft;
5. robustness of those gains across fields, archetypes, audiences, and targets.

No single aggregate score may substitute for these dimensions.

## Evaluation principles

1. Correctness is a floor, not a weighted stylistic feature. A severe formal error cannot be compensated by readable prose.
2. v1/v2 comparisons are paired, blind, and version-pinned.
3. Human effort is measured directly rather than inferred only from edit distance.
4. Reader understanding is tested by prediction and transfer, not only by ratings of clarity.
5. Development cases, style anchors, and confirmatory evaluation cases are separated.
6. Test procedures and decision thresholds are registered before examining confirmatory outcomes.
7. Component ablations identify which architectural changes cause gains.
8. Qualitative failure analysis remains first-class; a dashboard must not hide rare fatal errors.
9. System validation demonstrates state consistency, not scientific importance or publication readiness.

## Evaluation layers

### Layer A: executable architecture tests

These tests cover schemas, state transitions, claim references, dependency invalidation, context isolation, provenance, recovery, and migrations. They answer whether the system operates as specified, not whether the economics is good.

### Layer B: component-level scientific tests

Use bounded tasks with inspectable answers:

- recover the economic meaning of a formal object;
- distinguish a primitive assumption from a condition on an endogenous object;
- identify which assumption supports which result;
- detect an overclaim relative to a theorem;
- explain a decomposition;
- generate or interpret a micro-example;
- distinguish numerical corroboration from proof;
- diagnose why a result block fails to deliver intuition.

### Layer C: section-level authoring tests

Evaluate introductions, model exposition, assumption discussion, result blocks, proof roadmaps, literature positioning, and conclusions under matched inputs.

### Layer D: paired system evaluation

Run the three registered arms below. Do not collapse compiler quality, end-to-end discovery, and revision into one treatment label.

### Layer E: longitudinal human-AI collaboration

Measure how the systems perform over repeated revisions, upstream model changes, referee comments, and human overrides. This layer tests whether v2 reduces accumulated intervention rather than merely producing a better first sample.

## Frozen baselines and version pinning

Every comparison records:

```text
case_id
v1 commit or release
v2 commit or release
state/schema version
route, profile, and prompt hashes
model/provider/version when known
reasoning setting
agent topology, roles, and model lineage
allowed attempt/retry count
candidate-retention and output-selection rule
tool access and versions
input artifact hashes
literature bundle
profile, craft-corpus, split, retriever/index, and selected-move versions
token, time, and tool budgets
human decisions supplied
randomization seed when available
independent case-key id and hash
evaluator class and blinding manifest
```

Architecture v0.1 names v1 commit `cc5f61254bb79e7436892e32ec88730ae14dd7f8` as the initial comparator. Every actual case manifest pins the full hash. Fixes to v1 create a new named baseline rather than silently moving the comparator.

Because model outputs are stochastic, important cases should use multiple registered runs when budget permits. The number of attempts, retries, failures, discarded outputs, and selection rule are fixed before generation; best-of-N selection is prohibited unless it is the declared treatment and all N costs and outcomes are reported. Paired analysis remains at the case level so one prolific case cannot dominate the result.

## Three comparison arms

### `compiler_only`

Both systems receive one independently adjudicated, system-neutral validated research package. This arm tests Paper IR, reader modeling, craft selection, canonical writing, and fidelity without crediting either system for discovering the underlying economics.

### `end_to_end_discovery`

Both systems begin from the same raw question, source artifacts, literature access, and human constraints. Neither receives a v2-generated argument spine, ResultPacket, case key, or hidden reader probe. This arm measures the entire path from benchmark/mechanism discovery through manuscript production.

### `revision`

Both systems receive the same manuscript version, proofs, source evidence, and expert/referee comments. This arm measures reconstruction, diagnosis, selective invalidation, and revision. A human-corrected version is withheld unless the task explicitly tests comment-guided comparison against it.

Results are reported by arm and are never pooled into one headline score.

## v1/v2 blind comparison protocol

### 1. Prepare the arm-specific common input

Within an arm, both systems receive semantically identical research materials. For `compiler_only`, these may include:

- research question;
- model, primitives, timing, information, actions, payoffs, and equilibrium concept;
- accepted assumptions;
- theorem statements and proof status;
- economic argument materials available at the start of the test;
- literature evidence;
- target configuration;
- explicit human decisions.

For `end_to_end_discovery`, model, theorem, economic argument, and result contracts are outputs rather than supplied inputs. For `revision`, the shared input is the frozen manuscript/comment package. System-specific control files are not counted as research inputs. If one system receives an additional substantive economic insight, that condition is a separately named evaluation arm rather than a fair baseline comparison.

### 2. Match resources

Use the same model family and reasoning setting where technically possible, identical external tools and literature access, and comparable token and wall-time budgets. Resource deviations are recorded and analyzed rather than hidden.

Two complementary comparisons are useful:

- `equal-resource`: tests architectural efficiency under matched budgets;
- `best-system`: allows each system to use its intended workflow and measures end-product cost and quality.

They must not be pooled.

### 3. Anonymize outputs

Remove system names, file conventions, metadata, comments, and distinctive headers. Randomize output order separately for each evaluator. Use neutral labels that change across cases.

### 4. Use qualified readers

Panels should include, where relevant:

- a theorist capable of checking formal scope;
- a specialist in the paper's field;
- an economist outside the narrow field for reader-transfer testing;
- the human researcher for effort and acceptability measurements.

Confirmatory primary endpoints come from blinded human economists with the required competence. AI evaluators may supply diagnostics but cannot establish a confirmatory win; their model lineage and context are recorded separately. No evaluator sees other ratings before submitting an independent assessment.

### 5. Separate rating from editing

Readers first evaluate and complete comprehension tests on the untouched output. Human revision then begins in a separate phase. Otherwise edits contaminate the initial-quality comparison.

### 6. Reveal only after lock

System identity is revealed only after ratings, comprehension answers, critical-error adjudication, and human-effort logs for the round are locked.

## Correctness floors

An individual output is ineligible for manuscript promotion or a submission-quality win if it contains any known unresolved critical defect in the following areas. At system level, critical-error incidence and its uncertainty are reported across all registered outputs; a system comparison never converts a nonzero defect in a particular manuscript into permission to promote that manuscript.

### Formal fidelity

- theorem statement changed or strengthened;
- assumptions omitted, altered, or attached to the wrong result;
- local, conditional, or interior result presented as global or unconditional;
- existence, uniqueness, equilibrium, welfare, or comparative-static claim unsupported by the accepted result;
- proof roadmap materially misstates the proof;
- notation changes the mathematical object.
- a verbal translation or economic implication is not entailed by the scoped formal claim.

### Verification integrity

- numerical tests presented as proof;
- symbolic simplification presented as an economic argument or global certificate without justification;
- failed or stale verification omitted;
- counterexample ignored;
- tool output not reproducible from recorded inputs and versions when reproducibility is claimed.

### Literature integrity

- fabricated source or result;
- closest-paper claim unsupported by current `LiteratureEvidence`;
- prior paper described more strongly or narrowly than the source permits;
- novelty claim that ignores a known absorption threat in the supplied evidence.

### Internal consistency

- economic interpretation contradicts the formal object;
- the same object has incompatible identities in different sections;
- abstract, introduction, result section, and conclusion state different scopes;
- a displayed implication depends on a stale or rejected upstream decision.

Critical errors are adjudicated from exact locations and source contracts. Evaluators do not mark an output critical merely because they prefer another model or exposition.

Lesser errors are recorded by severity and repair cost. Correctness floors are reported separately from prose-quality scores.

## Reader-transfer evaluation

Clarity ratings alone are vulnerable to fluent but empty prose. Readers therefore complete structured tests after reading the relevant section or manuscript without consulting source contracts.

### Shared recovery core

Ask the reader to state, in their own words:

- the economic or conceptual question;
- the natural benchmark and unresolved delta;
- the main result and its exact scope;
- the role of the central assumptions;
- the main boundary or failure case;
- what an economist learns relative to the closest theory.

### Archetype-specific reasoning

Select exactly one module matching the claim's registered archetype:

- `mechanism_explanation`: recover the initiating force, affected margin or distinction, response/feedback where applicable, rival, and ablation;
- `comparative_statics_threshold`: predict a nearby perturbation, explain competing effects, and locate the monotonicity or regime boundary;
- `characterization_bounds`: distinguish necessity from sufficiency and apply the conditions to a new candidate object;
- `robustness_invariance_equivalence`: map a nearby environment, identify what is preserved, and locate where the mapping fails;
- `design_implementation_impossibility`: identify the binding incentive/feasibility conflict and predict the effect of relaxing one requirement;
- `concept_representation_foundation`: use the concept or representation to classify a new case and explain which conclusion or modeling practice changes.

Non-applicable mechanism, feedback, welfare, policy, or comparative-static questions are omitted with a recorded reason. They are not scored as missing.

### Near transfer

Give a hidden nearby environment or conceptual case appropriate to the archetype. Ask which result logic survives, which conclusion may change, and what would need to be re-proved or re-established.

### Boundary discrimination

Present one valid application and one tempting but invalid extension. Ask the reader to identify which is supported and why.

### Delayed retention

For selected cases, repeat a compact recovery test after a delay. A manuscript whose mechanism is understood should leave more than remembered terminology.

Before any system output is generated, independent subject-matter experts build and lock a system-neutral case key from source research materials. The key records shared-core answers, archetype-specific obligations, acceptable alternatives, forbidden extensions, and probe hashes. It cannot be generated from v2 Paper IR, ResultPackets, either system's prose, or an evaluator that saw those outputs. Concrete probes and answer keys are hidden from writers and generation routes. Evaluators may record reasonable alternative interpretations for blinded adjudication.

## Human-effort measurement

The central efficiency question is how much high-intensity researcher labor remains before the text reaches a common, blinded acceptance endpoint. Before revision begins, the case protocol defines the minimum correctness, completeness, reader-transfer, and deliverable scope required. Lower time caused by abandonment, omitted sections, or acceptance of a worse endpoint is not an efficiency gain.

Record:

- active human minutes, excluding unattended computation;
- number of human-AI clarification rounds;
- number of structural decisions the human must reconstruct because the system did not surface them;
- paragraphs accepted unchanged, lightly edited, substantially rewritten, and deleted;
- words retained, but only as a secondary measure;
- formal-error corrections;
- mechanism or intuition repairs;
- assumption-interpretation repairs;
- result-hierarchy and reader-path changes;
- literature-positioning repairs;
- voice and language edits;
- regressions introduced by later rounds;
- subjective cognitive load, recorded immediately using a simple ordinal scale;
- whether the human would trust the draft as the starting point for the next round.
- manuscript length and delivered-scope coverage;
- reader time to the comprehension endpoint;
- abandonment, timeout, and reason for stopping.

Edit distance alone is inadequate: changing a theorem qualifier may be small in characters but high in importance, while rewriting a transition may be large but cheap. Every edit is therefore assigned a semantic class and severity.

Revision order is randomized and counterbalanced. The same researcher should not revise both paired outputs sequentially when insights from the first can repair the second; use independent editors, matched cases, or a preregistered crossover design with carryover analysis. Initial quality is rated before any editing.

The primary effort outcome is active substantive revision time to the common endpoint, reported with final quality, delivered scope, manuscript length, and reader time. Secondary outcomes include time per accepted manuscript unit, direct-retention rate, and high-severity interventions. Abandoned or timed-out revisions remain outcomes and are not dropped or coded as fast completion.

## Argument and craft assessment

After correctness adjudication, evaluators assess:

- economic importance as actually supported;
- visibility of the benchmark and puzzle;
- mechanism completeness;
- quality and diagnostic value of examples;
- theorem motivation;
- exactness of verbal translations;
- assumption naturalness and necessity discussion;
- result hierarchy;
- proof-roadmap usefulness;
- reader path and cognitive load;
- literature contrast;
- boundary honesty;
- coherence of voice;
- fit with the resolved ambition, archetype, field, and audience profiles.

Ratings require a short reason and an exact passage or omission. Pure numerical impressions are not sufficient for confirmatory analysis.

## The expert-annotated appendix case

An AI-generated appendix with expert comments but no completed revision is a diagnostic case, not a gold rewrite benchmark.

It can evaluate whether the system detects:

- unstable economic identity and terminology;
- formal objects lacking interpretation;
- assumptions described as primitive but not economically natural;
- missing primitive sufficient conditions;
- assumption redundancy or lack of ablation;
- definitions introduced after their inferential use;
- mismatch between proof organization and reader needs.

Because no expert-approved final text exists, the case must not score prose similarity to an imagined solution. Valid outcomes are diagnostic recall/precision, quality of proposed repair contracts, correctness of any rewrite, and expert assessment of whether the proposal addresses the actual comments.

If the human later supplies a completed revision, it becomes a three-part case:

```text
AI original -> expert comments -> human revision
```

The human revision remains evidence of one successful solution, not a phrase-level target to imitate.

## Leakage prevention

Evaluation materials are divided into:

- `development`: visible during architecture and prompt design;
- `pilot`: used to estimate variance and set feasible thresholds;
- `confirmatory holdout`: inaccessible to authoring routes and craft retrieval;
- `external replication`: maintained by a separate evaluator when possible.

Controls include:

- content hashes for case inputs and outputs;
- separate storage and access policies for holdouts;
- context manifests proving which files and anchor records a run received;
- disjoint craft anchors and evaluation targets for confirmatory cases;
- no expert comments in the generation context unless the tested task is comment-guided revision;
- no human revision in the model context when evaluating independent rewriting;
- no concrete cold-reader probe or answer key in writer, critic, craft-retrieval, or profile contexts;
- audit for distinctive phrases shared with hidden targets;
- no tuning on evaluator rationales from the confirmatory set;
- fresh cases from fields and archetypes not represented in development.

If leakage is discovered, the affected result is invalidated rather than adjusted statistically.

## Anti-Goodhart safeguards

The evaluation system must resist optimizing visible proxies while losing scientific quality.

1. Do not publish one headline score. Report correctness floors, transfer, craft, and effort separately.
2. Apply correctness gates before style comparisons.
3. Use hidden transfer questions and rotating cases.
4. Require passage-level reasons for ratings.
5. Track output length, number of examples, intuition paragraphs, citations, and theorem restatements as diagnostics, never as success targets.
6. Penalize unsupported breadth and rhetorical importance claims.
7. Include adversarial cases where the correct action is to narrow, say "unknown," or refuse to draft a final claim.
8. Include cases where a simple model and short explanation dominate a technically richer alternative.
9. Test for formulaic result blocks and repeated exposition templates.
10. Preserve qualitative fatal-error reports even when aggregate means improve.
11. Freeze scoring rules before confirmatory evaluation.
12. Audit whether evaluators can infer system identity from formatting or characteristic rhetoric.
13. Register every attempt, retry, rejection, and selection decision so best-of-N cherry-picking cannot masquerade as architecture quality.
14. Compare reader transfer jointly with manuscript length and reading time so repetition cannot purchase an unqualified clarity win.

The system should not be trained to maximize evaluator preference directly. It should improve the upstream economic contracts and let preference be an external consequence.

## Ablation program

Ablations isolate the effect of the architectural components. Each removes one component while holding the model, research inputs, budget, and remaining system fixed.

Required ablations include:

- no economic argument spine;
- no reader-belief model;
- no micro-example requirement;
- no result-block contracts;
- no layered explanation contract;
- no economic ontology/terminology contract;
- no canonical writer, allowing independent section writers;
- no writer context isolation, exposing full governance and logs;
- no functional craft retrieval;
- no target profile beyond the universal floor;
- journal overlay replaced by a hard journal template;
- no dependency invalidation after an upstream assumption or theorem change;
- no human promotion gate for structural decisions.

The most informative ablations are mechanism tests, not feature-count contests. Examples:

- If removing the reader model reduces transfer but not formal fidelity, it is performing its intended function.
- If removing context isolation worsens voice and increases governance language, the hypothesized contamination channel is supported.
- If removing result contracts improves fluency but increases overclaims, contracts are protecting correctness at a possible prose cost.
- If journal overlays do not improve target-reader ratings, they should be simplified or removed rather than retained ceremonially.

Interactions should be tested selectively, especially argument spine × result contract and reader model × canonical writer. Full factorial experiments are unnecessary unless pilot evidence justifies the cost.

## System-reliability evaluation

Scientific evaluation is invalid if the runtime loses state or silently uses stale inputs. Required scenario tests include:

- changing a primitive and confirming the correct theorems, proofs, explanations, and summaries become stale;
- changing only the target overlay and confirming formal results remain fresh;
- finding a counterexample and confirming the affected claim cannot retain `formal_validity: verified_in_scope`;
- reversing a human decision and confirming dependent working products reopen;
- running blind agents and verifying forbidden context is absent;
- verifying that writers receive transfer objectives but not concrete cold-reader probes or case keys;
- crashing before, during, and after transaction commit and recovering deterministically;
- detecting simultaneous edits without overwriting human text;
- moving the project folder across machines without absolute-path failure;
- migrating schemas without rewriting history or losing decisions.

## Statistical analysis

Confirmatory reporting uses paired case-level differences. Recommended outputs include:

- distributions and confidence intervals, not only means;
- critical-error incidence;
- paired reader-transfer differences;
- paired active-human-time differences;
- inter-rater agreement and adjudication rates;
- results by field, archetype, audience, and manuscript component;
- sensitivity to evaluator group;
- run-to-run variance for stochastic generation;
- qualitative taxonomy of regressions and wins.

Pilot data may be used to choose feasible sample sizes and thresholds. Those choices must be locked before confirmatory outcomes are inspected. A small number of papers should be described as case evidence, not population-level proof.

## Promotion criteria

The versioned architecture-promotion predicate is `EV-PROMOTION-0.1`. Phase 6 and later release plans should reference this predicate rather than restating a weaker subset. Exact numerical thresholds are set after the pilot and preregistered before the confirmatory evaluation. At minimum, v2 cannot be promoted as an improvement unless:

1. every manuscript proposed for promotion has zero known unresolved critical errors, while system-level critical-error incidence satisfies the preregistered non-inferiority rule;
2. it improves shared-core and archetype-appropriate reader transfer, not merely clarity ratings;
3. it reduces active substantive human effort to the common endpoint or materially improves endpoint quality at the same effort;
4. gains meet preregistered minimum case counts and field/archetype strata rather than an ambiguous "more than one" rule;
5. no leakage or material protocol violation affects the comparison;
6. ablations provide evidence that the intended architectural components, rather than uncontrolled extra information or budget, cause the gains;
7. blinded human preference is locked before system identity is revealed; post-reveal explanations are reported only as qualitative follow-up;
8. attempt counts, agent topology, selection rules, corpus/retriever versions, and evaluator lineage show no uncontrolled best-of-N or correlated-self-evaluation advantage;
9. the result is reported separately for `compiler_only`, `end_to_end_discovery`, and `revision` arms.

Failure on one confirmatory round is information for redesign, not a reason to move thresholds.

## Minimal evaluation artifacts

To avoid a new evaluation bureaucracy, retain only:

```text
preregistered protocol
case manifests and input hashes
anonymized outputs
raw locked ratings and comprehension answers
human-effort event log
critical-error adjudications
analysis code and version manifest
concise results report
```

Exploratory notes, evaluator chat, and intermediate charts remain run artifacts unless needed to reproduce a decision. Public repositories must exclude unpublished manuscripts, confidential expert comments, and proprietary or unauthorized paper texts.

## Acceptance criterion

The evaluation architecture succeeds when it can distinguish four outcomes that a single style score would conflate:

- fluent but formally wrong;
- correct but economically opaque;
- clear first draft that still consumes heavy human repair;
- correct, transferable, coherent theory writing that materially reduces high-intensity human intervention.

Only the fourth outcome supports the central v2 claim.
