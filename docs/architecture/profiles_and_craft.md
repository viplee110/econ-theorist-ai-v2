# Profiles and Theory-Paper Craft

## Purpose

Profiles calibrate a theory paper to its scientific ambition, contribution type, field, and reader without making the core system journal-specific. The craft library supplies reusable exposition moves learned from excellent theory papers without copying their language or turning a journal's past publications into a rigid style template.

The system is limited to pure and applied economic theory. Profiles may cover welfare and policy theory, market design, mechanism design, information economics, industrial organization theory, political economy theory, behavioral theory, macro theory, finance theory, and other fields only when the project is a formal economic-theory paper. They do not activate econometrics, empirical design, data analysis, identification, or causal-estimation workflows.

## Profile stack

Every authoring and review run resolves one ordered stack:

```text
universal quality floor
  + theory mode
  + ambition mode
  + paper archetype
  + field calibration
  + target audience
  + soft journal overlay
  + submission constraints
  = resolved profile manifest
```

The layers are orthogonal wherever possible. A profile must not be a long combined prompt such as "Econometrica network-search theory paper." The resolved manifest records the source version of every layer, conflicts, and final decisions.

## Layer 1: universal frontier-theory quality floor

The universal floor applies to Econometrica, general-interest Top-5, and top-field targets. A different target may alter emphasis and fit, but never lowers:

- truthfulness and exact theorem scope;
- proof discipline and transparent verification status;
- economic importance relative to the stated audience;
- novelty scrutiny and closest-paper honesty;
- mechanism clarity;
- assumption necessity and economic naturalness;
- model economy and resistance to decorative complexity;
- result hierarchy;
- boundary and failure analysis;
- distinction between analytic proof, formal certificate, symbolic support, numerical stress testing, and conjecture;
- reproducibility of computational verification;
- readable economic interpretation;
- preservation of uncertainty and unresolved risks.

The universal floor is an invariant set. Lower-level profiles cannot override it. Passing it means that no known blocking defect remains; it does not certify publication probability.

## Layer 2: theory mode

Theory mode determines which economic obligations are relevant without creating an empirical branch.

### `pure_theory`

The primary contribution is a concept, representation, characterization, bound, equivalence, robustness result, implementation result, or impossibility theorem. The paper must explain the economic consequence, application class, or change in modeling practice. It must not invent welfare or policy language merely to appear applied.

### `applied_theory`

The formal contribution is tied to an institution, market, strategic environment, or policy/design question. The paper must map institutional features to primitives and, when relevant to its own claims, account for welfare, incidence, rents, transfers, resource costs, or design constraints. This remains a theoretical mode: it does not add data, estimation, identification, or empirical-validation workflows.

Theory mode changes relevant obligations, not the correctness or novelty floor. A paper may contain both abstract and institutional sections, but the resolved profile records the dominant mode and any explicitly justified secondary mode.

## Layer 3: ambition mode

Ambition mode states the paper's intended scientific reach rather than naming a journal.

### `frontier_general_interest`

The paper seeks a broad update for economists beyond its originating field. Calibration emphasizes:

- a question legible to a general economist;
- a mechanism with consequences beyond one special environment;
- clear economic stakes before technical detail;
- aggressive result hierarchy and compression of field-specific infrastructure;
- explicit transfer of the insight to adjacent settings;
- a credible answer to "why should economists outside this field care?"

### `frontier_theory`

The paper seeks a foundational theoretical contribution. Calibration emphasizes:

- a sharp new object, primitive, theorem, impossibility, or unifying argument;
- transparent relation between economic intuition and formal architecture;
- broad theorem scope or a compelling explanation of why a narrow scope is fundamental;
- economical assumptions and proof structure;
- conceptual reuse by theorists in other domains.

### `field_frontier`

The paper seeks to change how a mature field understands a central question. Calibration emphasizes:

- command of field benchmarks and closest substitutes;
- a mechanism or theorem that resolves a recognized field tension;
- sufficient institutional or modeling specificity for field readers;
- implications and boundaries that matter within the field;
- direct comparison with the strongest field alternatives.

Developmental states such as preview, working draft, and submission draft are compiler modes, not ambition modes. A preview may aim at frontier quality while remaining incomplete.

## Layer 4: paper archetype

Each project selects one dominant paper archetype and at most one secondary archetype from the result-archetype vocabulary owned by `theory_kernel.md`. At paper level, this means the archetype of the central reader update; individual claims retain their own kernel contracts. Selecting many archetypes is a warning that the paper lacks a contribution hierarchy.

The shared archetypes are:

- `mechanism_explanation`;
- `comparative_statics_threshold`;
- `characterization_bounds`;
- `robustness_invariance_equivalence`;
- `design_implementation_impossibility`;
- `concept_representation_foundation`.

New primitives, benchmark reversals, decompositions, sufficient statistics, and unifications are recorded as the economic content of the appropriate shared archetype rather than creating a competing classification. For example, a new primitive that exposes a hidden feedback normally serves `mechanism_explanation`; a sufficient statistic that organizes several environments may serve `concept_representation_foundation` or `robustness_invariance_equivalence`, depending on the actual claim.

The archetype controls what the manuscript must make visible. For example, a `mechanism_explanation` paper must expose the economic chain and failure cases; a `characterization_bounds` paper must explain what the characterization organizes and why its conditions are natural; a `design_implementation_impossibility` paper must identify the conflicting economic requirements rather than presenting only a contradiction proof.

## Layer 5: field calibration

Field profiles contain only information that is stable enough and sufficiently supported to improve reasoning or communication:

- standard benchmark environments;
- accepted meanings of technical terms;
- common equilibrium concepts and where variants matter;
- canonical reader priors and likely misconceptions;
- field-specific assumption naturalness questions;
- expected welfare, incidence, policy, or design implications when relevant;
- normal proof and robustness burdens;
- closest-literature search vocabulary;
- notation conventions when they reduce friction.

Field profiles must not contain fixed referee personas, caricatures of a field, or a generic checklist copied into every paper. A project may override a field convention when the economic reason is explicit.

Field profiles are evidence-bearing and versioned. Claims such as "readers in this field always expect X" require multiple relevant anchors or must be labeled provisional.

## Layer 6: target audience

Audience is represented separately from field and journal. Common audiences are:

- `general_economist`;
- `economic_theorist`;
- `field_specialist`;
- `theory_and_field_bridge`;
- `policy_or_design_literate_economist` for theory papers with direct institutional consequences.

An audience profile controls assumed knowledge, definition timing, example choice, notation density, proof-roadmap depth, and literature explanation. It does not control whether a theorem is true.

Paper IR records a primary audience and optional secondary audience. If the two require incompatible exposition, the compiler presents the tradeoff rather than averaging them into vague prose.

## Layer 7: soft journal overlay

A journal overlay is the final and weakest layer. It is a probabilistic reader-and-fit calibration, not a rulebook and not an imitation target.

A soft overlay may adjust:

- likely breadth of the opening question;
- pace at which formal detail enters;
- main-text versus appendix emphasis;
- expected relation between theorem and application;
- amount of field background needed;
- likely editor/referee fit questions;
- abstract and introduction compression;
- salience of generality, method, welfare, or field consequences.

It may not:

- relax the universal quality floor;
- alter claims, assumptions, or proof status;
- require a result merely because recent papers display it;
- prescribe sentence patterns or a named author's voice;
- convert a field contribution into a general-interest contribution through rhetoric;
- treat historical acceptance patterns as deterministic editorial policy.

Overlays are soft because journals are heterogeneous and editorial standards change. Each overlay therefore records evidence coverage, date, uncertainty, and conditions under which it should be reviewed. Econometrica is one optional overlay, not a filename prefix or the identity of the system.

## Layer 8: submission constraints

Submission constraints are externally checkable requirements such as length limits, anonymization, file composition, appendix/supplement rules, abstract limits, and disclosure statements. They may change rendering and packaging but not the research claim, proof status, economic argument, or universal floor. Each constraint records its source, retrieval date, target, applicability, and verification status. A journal stereotype is not a submission constraint.

### Initial profile presets

Architecture v0.1 defines three reusable presets. A preset expands into selections from the layers above; it is not an additional precedence layer and cannot override them:

- `frontier_theory_universal`: selects the universal floor without a venue overlay and leaves mode, archetype, field, and audience explicit;
- `top_general_interest_theory`: adds a broad-reader burden, a consequential belief update beyond the narrow field, early economic stakes, and strong result compression;
- `top_field_theory`: adds a precise field-frontier delta, command of closest substitutes, specialist naturalness standards, and a clear reason the result changes field practice.

Individual venues remain soft overlays on these presets. The following are inactive provisional hypotheses for corpus design, not active profile requirements:

- Econometrica theory places especially high pressure on the two-way map between economic content and formal contribution, meaningful generality, robustness, and constructive rigor;
- general-interest Top-5 theory places especially high pressure on question breadth, early reader access, and economic consequence without sacrificing formal self-containment;
- JET and Theoretical Economics can permit faster entry into the formal problem, but the theory-frontier delta and economic interpretation must remain explicit;
- RAND theory should make the institutional environment, strategic mechanism, and relevant welfare/design implications auditable;
- GEB should expose the general game-theoretic advance or transferable application insight rather than merely solve one named game.

No hypothesis in this list may enter a resolved manifest until a versioned corpus audit supplies evidence, uncertainty, a non-applicability rule, and human authorization through the runtime authority registry. The hypotheses must be revised when the craft corpus or official venue guidance changes. They must not be converted into claims such as “QJE introductions always do X” or “Econometrica requires maximum abstraction.”

## Profile resolution

The resolver applies the following precedence:

1. formal truth and route-admissible canonical research state;
2. universal quality floor;
3. explicit human decisions about theory mode, ambition, contribution, and audience;
4. theory mode;
5. primary archetype;
6. field calibration;
7. audience needs;
8. soft journal overlay;
9. verified submission constraints;
10. local craft preferences.

When two layers conflict, the higher layer controls and the conflict is reported. The resolver must not silently blend incompatible instructions.

A resolved manifest contains:

```text
profile_manifest_id
state revision
quality-floor version
theory mode
ambition mode
primary and secondary archetype
field profile and confidence
primary and secondary audience
journal overlay and evidence date
submission-constraint refs and source dates
active requirements
soft preferences
rejected conflicts
human decision refs
profile schema and resolver versions
source profile/overlay hashes
craft corpus release and split id
retriever/index and selector versions
selected CraftMove ids, versions, and evidence refs
route, prompt, and context-manifest refs
```

The resolved manifest is a versioned artifact referenced by the runtime's `ResolvedProfileManifestRef` and the applicable `PaperIRRef`; `TargetProfileRef` records the project choices from which resolution begins. Neither is a second target-state store. The manifest is pinned for a writing run. Updating a profile later creates scoped `ReviewFinding` records and, when material, `RiskOrBlocker` records for affected exposition or review products. Only `state_runtime.md` determines freshness transitions, and unchanged mathematics is not invalidated.

## Functional craft library

The craft library learns what excellent theory papers accomplish for readers, not how particular authors sound. A craft move is a functional transformation from a reader problem to an exposition solution.

Core move families include:

### Problem and puzzle moves

- begin from an economically recognizable decision, institution, or tension;
- state the benchmark intuition before introducing the new force;
- convert a broad topic into one answerable question;
- show why the sign, ranking, existence, or welfare conclusion is not obvious;
- distinguish a genuine puzzle from a claim that is merely technically difficult.

### Example-to-theory moves

- use a hand-solvable example to expose the operative margin;
- vary one primitive while holding the benchmark fixed;
- ask for an ex ante prediction before displaying the theorem;
- use a counterexample to kill an attractive but false generalization;
- abstract only the feature that survives the example comparison.

### Model-exposition moves

- introduce agents, timing, information, and payoffs in the order needed to answer the live question;
- give each formal object a stable economic identity;
- separate economically meaningful primitives from normalization and technical regularity;
- explain an equilibrium concept through the strategic problem it closes;
- defer machinery until the reader understands why it is needed.

### Result moves

- motivate a theorem with a benchmark prediction;
- state the exact result before broad interpretation;
- translate symbols into economically meaningful comparisons;
- decompose direct and equilibrium effects;
- explain the role of central assumptions at the point where they matter;
- locate reversal, threshold, and failure boundaries;
- distinguish the main result from robustness, extension, and illustration;
- use a proof roadmap to expose structure without forcing the proof into the main text.

### Literature moves

- compare mechanisms and economic objects, not keyword overlap;
- identify the nearest result that could absorb the paper;
- state what the earlier framework cannot express or what conclusion changes;
- avoid declaring a literature universally believes a benchmark when signs are mixed;
- make novelty proportional to verified evidence.

### Architecture moves

- make each section answer a question created earlier;
- close a section by stating the update and opening the next question;
- move technical breadth out of the main text when it does not change the cognitive update;
- place definitions, examples, and assumptions before their first inferential use;
- repeat a core idea only when the repetition performs a new function.

### Conclusion moves

- recover the question, mechanism, and boundary rather than inventorying sections;
- identify where the argument transfers and where it should not;
- separate established implications from open theoretical conjectures.

## Craft-move representation

Each move is stored as a compact, versioned craft artifact:

```text
move_id
functional name
reader problem addressed
trigger conditions
required semantic inputs
intended reader update
typical placement
valid variants
failure modes and anti-patterns
compatible archetypes and audiences
anchor evidence refs
transfer confidence
corpus release and source-card versions
artifact hash and derivation provenance
```

The object must not store reusable sentences from anchors. Short quotations, when legally and analytically necessary, belong in sourced `LiteratureEvidence` artifacts and are not supplied to the writer as a phrase bank.

## Learning from high-quality theory papers

Craft evidence is restricted to relevant, high-quality theory papers from general-interest Top-5 journals, Econometrica, leading theory journals, and field-top journals. Inclusion is based on functional relevance, not journal label alone.

Anchor selection should be diverse across:

- fields;
- paper archetypes;
- technical intensity;
- broad and specialist audiences;
- authors and time periods.

An anchor note records:

```text
paper identity and lawful source
field and archetype
reader problem
location of the move
what function the passage performs
what semantic inputs make it work
what is transferable
what is paper-specific and must not be copied
confidence and competing interpretation
```

At least two genuinely independent anchors should normally support a claimed general craft principle. Independence is assessed across author teams, paper/working-paper lineage, shared templates, and the specific research tradition that could generate the same move; two versions or close descendants of one paper count once. A single paper may inspire a provisional move but not a universal rule.

The system learns moves such as benchmark-before-result, example-to-abstraction, mechanism decomposition, and boundary clarification. It must not learn signature diction, sentence cadence, metaphor, paragraph rhythm, or rhetorical mannerisms associated with identifiable authors.

### Corpus lifecycle and selection bias

Published papers are selected outcomes. Their common features are useful hypotheses about craft, not causal proof that copying those features produces publication. The library therefore separates:

- `anchor`: high-quality theory papers used to derive candidate functional moves;
- `contrast`: papers or passages that are correct but expose a known reader problem;
- `development`: cases used while designing prompts and contracts;
- `evaluation_holdout`: paper families and projects inaccessible to craft retrieval;
- `project_postmortem`: local lessons from accepted, rejected, simplified, or abandoned system outputs.

Where lawfully available, earlier drafts, public referee/editor materials, author discussions, and expert comments can help distinguish an initial research problem from the polished equilibrium outcome. They remain evidence, not universal instructions. Accepted final papers alone must not teach the system that every extension, long introduction, or notation choice was causally valuable.

The corpus is stratified by theory mode, field, archetype, audience breadth, technical intensity, author, year, and working-paper lineage. A new paper cannot change a stable profile by itself. Candidate moves require human/AI dual review, provenance, a confidence label, a non-applicability note, and a change log. Incremental scans may occur regularly, while formal profile releases occur only after cross-paper review.

Public repositories store citations and copyright-safe derived cards, not full copyrighted or unpublished paper text. Local private source access is governed by the runtime privacy policy. A source used as a craft anchor cannot remain a confirmatory evaluation target in the same paper family.

### Architecture v0.1 seed evidence

The initial design was informed by methodological notes and representative theory papers, including:

- Hal Varian, [How to Build an Economic Model in Your Spare Time](https://people.ischool.berkeley.edu/~hal/Papers/how-OLD.pdf): begin with phenomena and simple examples, subtract until the essential mechanism is visible, and make the paper's point accessible early;
- Avinash Dixit, [Some Notes on the Art of Theoretical Modeling in Economics](https://www.princeton.edu/~dixitak/Teaching/ArtOfModeling.pdf): modeling is disciplined inclusion and exclusion around a consequential puzzle;
- Kamenica and Gentzkow, [Bayesian Persuasion](https://web.stanford.edu/~gentzkow/research/BayesianPersuasion.pdf): use a transparent example to discover the general object and then characterize the design problem;
- Carroll, [Robustness and Linear Contracts](https://www.bu.edu/econ/files/2013/03/May-4-Caroll.pdf): change one primitive, expose the guarantee mechanism, and expand only after the minimal result is clear;
- Bergemann, Brooks, and Morris, [The Limits of Price Discrimination](https://www.aeaweb.org/articles?id=10.1257%2Faer.20130848): use a possibility frontier when opposing forces do not support a universal sign;
- Bergemann and Morris, [Bayes Correlated Equilibrium](https://www.econtheory.org/ojs/index.php/te/article/viewFile/20160487/15457/452): separate basic game from information structure and use representation/equivalence to organize robustness;
- Monderer and Shapley, [Potential Games](https://www.sciencedirect.com/science/article/pii/S0899825696900445): move from an example to a concept, representation, characterization, and applications.

These are seed anchors for functional analysis, not prose templates or a closed canon. The versioned corpus must broaden across Top-5 and field-top theory, including recent papers and different result archetypes.

## Craft selection for a writing run

The compiler selects only moves that address an observed reader problem in the current Paper IR. It does not dump the craft library into the writer's context.

Selection order:

1. identify the reader update that is failing;
2. identify the result or section contract involved;
3. retrieve compatible moves by function, archetype, field, and audience;
4. exclude moves whose required semantic inputs are absent;
5. choose the smallest set that resolves the problem;
6. render the move using the project's own economic objects and voice;
7. test reader transfer and formal fidelity.

Craft should be diagnosed before it is prescribed. For example, if a theorem feels unmotivated because the mechanism itself is unresolved, no stylistic move can repair it; the route returns to mechanism work.

## Voice policy

The desired voice is generated from the project's argument, audience, and canonical writer sample. It is not an average of anchor prose.

Voice constraints may include:

- precision without legalistic qualification overload;
- confidence proportional to evidence;
- concrete economic nouns and active causal verbs;
- definitions near inferential use;
- restrained signposting;
- variation in paragraph structure when function permits;
- explicit boundaries without defensive rhetoric.

Named-author imitation is prohibited. Requests for "write like author X" are translated into allowed functional properties, such as concise theorem setup or clear benchmark contrast, while excluding identifiable expression.

## Human decisions

This document does not define authority levels or confirmation states. The resolver may produce typed proposals for theory mode, ambition, dominant archetype, target audience, venue overlay, voice charter, submission constraints, or a craft move that materially changes argument order. `state_runtime.md` is the sole authority registry and determines which proposal requires an L2/L3 human transaction and which selection may remain an L1 provisional branch. Related choices should be bundled into one decision packet.

## Validation and invalidation

Required checks include:

- every resolved profile includes the universal floor;
- no lower profile layer overrides a formal invariant;
- exactly one dominant theory mode and one primary ambition mode, archetype, and audience are selected;
- journal overlays are marked soft and evidence-dated;
- inactive provisional venue hypotheses cannot enter a resolved manifest;
- submission constraints have authoritative source refs and cannot change scientific content;
- craft moves have functional triggers and evidence refs;
- anchor-derived material contains no stored phrase bank;
- profile requirements are traceable to Paper IR contracts;
- target changes do not invalidate unchanged proofs;
- stale field or journal evidence downgrades calibration confidence;
- the writer receives selected moves, not full anchor texts;
- every resolved manifest pins corpus, retriever, selected-move, profile, overlay, route, prompt, and submission-constraint provenance.

## Anti-patterns

- Treating "Econometrica style" as one stable voice.
- Lowering rigor for a field journal.
- Inflating broad relevance to satisfy a general-interest profile.
- Counting intuition paragraphs, examples, or citations as quality metrics.
- Applying every high-quality-paper move to every manuscript.
- Using a famous paper as both training anchor and blind evaluation target.
- Inferring field conventions from one recent article.
- Encoding journal names in core workflow or schema filenames.
- Copying anchor syntax while replacing nouns.
- Allowing a target overlay to choose the theorem or suppress a genuine boundary.

## Acceptance criterion

The profile and craft system succeeds when it helps the canonical writer perform the same kinds of reader-facing functions found in excellent theory papers, using the current project's own economics and voice, while formal truth, scientific ambition, and uncertainty remain controlled by the universal state rather than by journal mimicry.
