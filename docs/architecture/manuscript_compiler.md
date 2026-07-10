# Manuscript Compiler Architecture

## Purpose

The manuscript compiler turns current, route-admissible economic reasoning into a coherent theory paper without treating prose generation as an unconstrained final step. Its job is to preserve formal truth, expose the economic mechanism, manage the reader's sequence of questions, and produce a single authorial voice.

This is a theory-only component. It supports pure theory, applied theory, and theory papers with welfare or policy implications. It does not define empirical designs, data pipelines, identification strategies, or evidence claims based on estimated effects.

The compiler is not a guarantee of publication and is not a generic style improver. It is a semantic authoring layer between the research state and manuscript source.

```text
route-admissible research state
  -> Paper IR
  -> reader and result contracts
  -> route-scoped writing packets
  -> canonical writer
  -> fidelity and reader tests
  -> manuscript source
```

## Design commitments

1. Formal truth and economic explanation are distinct representations of the same result; neither may silently replace the other.
2. A manuscript is organized around reader updates, not around the chronology of the research process or the inventory of files produced.
3. The writer receives only the research material needed for the current section. Gate logs, Git instructions, obsolete drafts, agent transcripts, and unrelated referee reports are excluded.
4. One canonical writer owns voice and cross-section coherence. Specialist agents diagnose, verify, or propose local alternatives; they do not independently assemble the final manuscript.
5. Every consequential prose claim must resolve to a current result, economic argument, `LiteratureEvidence`-supported comparison, or explicitly labeled conjecture whose runtime status permits the selected compiler mode.
6. Target calibration may change emphasis, pacing, and reader assumptions. It may not change theorem scope, proof status, or the universal quality floor.
7. Generated prose remains a proposal until its formal and narrative contracts pass validation and, where required, human review.

## What the compiler does not store

Paper IR is a thin semantic intermediate representation. It must not duplicate the full manuscript, full proofs, all research notes, or every sentence in structured state. Those remain substantive artifacts. Paper IR stores the contracts, ordering, dependencies, and claim mappings required to compile and validate prose.

The compiler must not create a permanent Markdown file for every pass. Intermediate prompts, critic reports, and rejected paragraphs belong in a run directory. Material that had no effect on a committed transaction may be discarded under the retention policy; any consequential criticism must first be preserved as an immutable `ReviewFinding` with provenance before a raw report is discarded.

## Preconditions

The compiler may operate in three modes:

- `preview`: a bounded provisional package may be explored before G5. The output must be labeled preview and cannot be promoted as a working or submission draft.
- `working`: the compiler consumes the exact fresh `ValidatedArgumentPackage` revision promoted at `G5_argument_validation`; explicitly nonblocking proofs, positioning, or section decisions may remain open and must be labeled or omitted where they affect claims.
- `submission`: the same G5-approved package is current, all displayed formal claims satisfy the configured correctness floor, blocking freshness issues are resolved, and the manuscript-version promotion has the authority required by `state_runtime.md`.

At minimum, a working compilation requires:

- the G5-approved `ValidatedArgumentPackage` and economic argument spine;
- a selected model and explicit assumption set;
- at least one result with a stable statement and scope;
- a target configuration resolved from the profile stack;
- an artifact registry entry for the manuscript source;
- no unresolved hard-stale dependency on a displayed claim.

Missing inputs do not force the system to fabricate them. The compiler either routes back to the relevant research task or produces a clearly bounded preview.

## Paper IR

Paper IR is a versioned, typed projection artifact linked to exact revisions of upstream entities. The runtime stores a `PaperIRRef` with its identity, status, dependencies, and artifact version; it does not duplicate the IR inside the canonical snapshot. `ClaimGraph`, `AssumptionMap`, `ValidatedArgumentPackage`, verification records, literature objects, and effective decisions remain authoritative. Any statement, scope, assumption, interpretation, or status copied into Paper IR is a render cache whose source field and exact version are recorded; it cannot be independently edited or promoted. State dimensions and transition vocabulary are owned exclusively by `state_runtime.md`.

### Paper identity

```text
paper_ir_id
schema_version
project_id
mode
source_state_revision
resolved_profile_manifest
manuscript_artifact_ref
language
upstream_projection_manifest
projection_hash
```

### Claim registry

Each economically or formally consequential claim has a stable ID and records:

```text
claim_ref and exact version
claim type projection
source field refs and revisions
allowed wording strength
scope projection
assumption refs and exact versions
verification refs and exact versions
permitted manuscript locations
forbidden extensions or known overclaims
```

The claim registry is not a sentence bank or a second claim store. It is rebuilt when an upstream version changes. `allowed wording strength` is a projection of the authoritative allowed-claim envelope, while the canonical writer remains free to render it naturally for the local reader.

### Economic ontology and terminology

The ontology records the stable economic identity of core objects:

```text
object_id
formal symbol
preferred economic name
short definition
economic interpretation
role in the mechanism
allowed aliases
forbidden or misleading names
first required explanation point
```

This prevents the same object from drifting among labels such as regular price, stationary price, and equilibrium price without an explicit distinction.

### Narrative spine

The narrative spine has a shared core:

```text
phenomenon or question
reader's natural benchmark
unresolved benchmark delta
new economic or conceptual object
central result and why it is not immediate
boundary and failure conditions
economic consequence, application class, or changed modeling practice
literature update
```

The shared core is extended by the central result archetype. A mechanism paper may add wedge, decision margin, direct response, and equilibrium feedback. A characterization paper adds the object characterized, necessity/sufficiency logic, and tightness. An impossibility paper adds the conflicting desiderata and decisive relaxation. A representation paper adds the formal-economic mapping and changed conclusion. Pure theory must not invent direct/equilibrium effects, welfare, incidence, or policy language merely to populate a template. Every main-text section must serve an applicable reader update; a mathematically correct section with no such job is moved, merged, demoted, or removed.

### Section contracts

Each section contract contains:

```text
section_id and role
reader state on entry
central question
required inputs and result refs
claims introduced
economic objects that must be interpreted
reader update on exit
open question handed to the next section
reader-cost constraint (qualitative by default; measured reading time only in evaluation)
appendix boundary
forbidden detours
```

A section contract defines a function, not a fixed prose template. Multiple sections should not acquire identical openings or paragraph patterns merely because they share a schema.

### ResultPacket contracts

Every central claim receives one `ResultPacket` with a shared core and exactly one archetype module from `theory_kernel.md`. The shared core is:

```text
claim ref and exact upstream revision
primary archetype
economic or conceptual question answered
exact benchmark delta
formal statement/scope projection and source refs
semantic translation entailed by the claim
assumption refs and role projections
applicable example/witness refs
why the result is not immediate
boundary, limitation, and prohibited overclaims
proof idea and roadmap refs
reader update and economic consequence
downstream claim and section dependencies
```

Archetype modules add only relevant obligations:

- `mechanism_explanation`: initiating force, affected margin or distinction, direct response when applicable, strategic/equilibrium feedback when applicable, rival separation, ablation, and failure case;
- `comparative_statics_threshold`: perturbation, competing effects, exact monotonicity domain, threshold/regime logic, and reversal or boundary witness;
- `characterization_bounds`: object characterized, necessity witness, sufficiency witness, tightness/independence, and interpretation of the conditions;
- `robustness_invariance_equivalence`: environments mapped, preserved object/claim, mapping, economically meaningful variation, and failure boundary;
- `design_implementation_impossibility`: objective/desiderata, incentive-feasibility map, construction or minimal conflict, and decisive relaxation;
- `concept_representation_foundation`: concept/axioms/representation, economic identity, representation or independence burden, and a case in which the new lens changes a conclusion or modeling practice.

Fields outside the selected archetype may be `not_applicable` only with a short reason. `not_applicable` is preferable to fabricated direct effects, equilibrium feedback, welfare, policy, examples, or signs. A ResultPacket is a projection/contract artifact, not an authoritative result entity, and not every applicable field must become a separate paragraph.

### Assumption contracts

For each assumption used in the main text:

```text
formal content
economic content
which proof step or result it supports
whether it is primitive or imposed on an endogenous/reduced-form object
familiar sufficient primitive conditions, when known
examples satisfying it
what fails without it
whether a weaker condition is known
where it is first needed
```

Calling an assumption "primitive" because it is written in terms of model inputs is not enough. The contract must distinguish mathematical primitiveness from economic naturalness.

Assumption-contract content is projected from exact `AssumptionMap` versions. The compiler may choose explanation and placement, but it cannot independently change an assumption's content, necessity status, primitive foundation, or scope cost.

### Proof-roadmap contracts

A proof roadmap explains the economic and mathematical architecture without reproducing the proof:

```text
object being constructed or compared
key decomposition or monotonicity step
where each central assumption enters
main technical obstacle
certificate, fixed-point, envelope, or local argument used
scope that the proof does not establish
appendix or verification refs
```

Numerical or symbolic checks must be labeled by their actual evidentiary role. A numerical stress test cannot be rendered as an analytic proof.

### LiteraturePositioningContract

Each consequential literature contrast is compiled from exact `LiteratureEvidence`, `ClosestTheoryMap`, contribution-claim, and absorption-assessment revisions:

```text
positioning_claim_id
prior-theory refs and source locations
object-by-object comparator mapping
shared benchmark and exact delta
mechanism/result/boundary relationship
allowed novelty wording
known absorption threat and uncertainty
required citation locations
forbidden stronger contrast
```

The contract supplies evidence-bounded comparisons to the writer. It is rebuilt when the central claim or closest-theory evidence changes and never upgrades partial literature coverage into a universal literature claim.

## Reader-belief model

The reader-belief model is a planning device, not a claim to predict an individual reader psychologically. It makes the intended cognitive updates explicit.

For each section and main result, Paper IR records:

- `known_on_entry`: facts and definitions the text may assume;
- `default_expectation`: the conclusion a competent reader might predict from the benchmark;
- `live_question`: the uncertainty currently motivating attention;
- `misconception_risk`: a plausible but incorrect inference;
- `update`: what the reader should understand after the block;
- `support_path`: example, equation, decomposition, theorem, or contrast that earns the update;
- `transfer_objective`: the kind of nearby environment, distinction, or inference to which understanding should transfer;
- `unresolved_on_exit`: the question intentionally carried forward.

Reader states are ordered by dependency. A block cannot assume an update that no earlier block delivered. The compiler flags such gaps and circular motivation.

The reader-belief model should be sparse. It is required for the introduction, model motivation, every central result, major extension, and conclusion. It is not required for routine algebra or every appendix lemma. Concrete cold-reader probes are generated after drafting by an isolated evaluator and are excluded from the writer's context; the writer sees only the transfer objective.

## Layered explanation

Important results normally require several layers of explanation. These layers may be interleaved or compressed, but must remain distinguishable:

1. **Question layer**: what economic question or benchmark tension is being resolved?
2. **Pre-result expectation layer**: when applicable, what sign, characterization, invariant, conflict, implementation, or representation should the reader conjecture before the theorem, and why is the answer not immediate? If no honest pre-result expectation exists, record a reasoned `not_applicable` rather than inventing one.
3. **Formal layer**: what exactly is true, under which assumptions and scope?
4. **Translation layer**: what does the formal statement say in the economic language of the paper?
5. **Archetype layer**: what mechanism, characterization logic, invariance map, conflict, implementation argument, or representation generates the result's economic content?
6. **Boundary layer**: where does the result, mapping, condition, bound, implementation, or interpretation fail, loosen, or reverse?
7. **Proof layer**: what is the proof strategy and where is the technical difficulty?
8. **Consequence layer**: why should the reader update their view of the phenomenon, literature, design problem, application class, or modeling practice?

Layering is not repetition. Each layer performs a different function. The compiler should remove paraphrases that merely restate the theorem without adding interpretation, mechanism, scope, or consequence.

## Canonical writer

The canonical writer is a role, not necessarily a fixed model instance. Within a manuscript version, it owns:

- voice and terminology;
- paragraph rhythm and transitions;
- section openings and exits;
- result hierarchy;
- integration of accepted specialist feedback;
- conformity with claim and result contracts.

The canonical writer receives a clean writing packet produced by the runtime context compiler containing only:

```text
current user instruction
mode and resolved profile
relevant reader states
section contracts and archetype-specific ResultPackets
accepted argument and result excerpts
formal invariants and forbidden claims
local manuscript context
approved terminology
selected craft moves
applicable LiteraturePositioningContracts
```

It does not receive full workflow documents, decision history, unrelated proofs, all style anchors, prior failed drafts, full referee panels, or raw multi-agent transcripts.

Specialist agents produce structured outputs:

- formal-fidelity critic: mismatches and exact affected claim IDs;
- economic-intuition critic: missing mechanism links or misleading interpretations;
- cold-reader critic: unexplained prerequisites and failed reader updates;
- assumption critic: naturalness, necessity, and primitive mappings;
- craft critic: functional exposition failures;
- copy editor: local language and consistency issues.

Their comments are merged into a revision brief. Any finding that changes committed prose or state is referenced by the transaction. The canonical writer performs the prose revision. Direct patching by many independent writers is permitted only for mechanically isolated changes and must be followed by a canonical integration pass.

## Compilation pipeline

### 1. Resolve inputs

Load exact route-admissible revisions, resolve the profile stack, check privacy policy, and identify stale inputs or entities whose derived `human_acceptance` is insufficient for the requested compiler mode. `preview` may use `agent_proposed` inputs when visibly labeled. `working` requires the effective `human_confirmed` G5 handoff decision; any remaining `human_provisional` input must be explicitly nonblocking and cannot support a displayed stable claim. `submission` additionally requires the applicable manuscript-promotion decision and fresh validity records.

### 2. Build or update Paper IR

Construct the claim registry, ontology, reader states, narrative spine, section contracts, and result contracts. Reuse fresh objects; do not rebuild the entire IR for a local revision.

### 3. Validate the plan

Check referential integrity, reader-state prerequisites, result coverage, claim strength, theorem ordering, and appendix boundaries. Present high-impact narrative choices for human authorization.

### 4. Compile writing packets

Create one route-scoped packet at a time. Include neighboring section context so local prose connects to the manuscript, but exclude unrelated system state.

### 5. Draft in dependency order

Draft the economic core before summary surfaces that depend on it. A normal order is result blocks and model exposition, then introduction and conclusion, followed by abstract and title. This is a dependency order, not a mandatory user-facing section order.

### 6. Integrate with the canonical writer

Resolve terminology, transitions, emphasis, repetition, and voice across sections. Preserve human-authored text unless a revision is authorized and based on its current hash.

### 7. Run fidelity validators

Compare prose claims with the claim registry, theorem scope, assumptions, proof status, literature evidence, and artifact revisions.

### 8. Run reader tests

An isolated cold-reader evaluator generates probes after the manuscript unit is frozen. Tests cover question and benchmark recovery, archetype-appropriate reasoning, exact result scope, boundary recognition, and transfer to a nearby environment or conceptual case. Probe content and answer keys are not included in the canonical writer's context.

### 9. Run target and craft calibration

Apply the resolved profile and functional craft moves without changing scientific content or imitating anchor language.

### 10. Build and register

Compile the manuscript where applicable, scan references and warnings, register hashes and provenance, and emit a concise status view. Promotion to a new manuscript version is an explicit transaction.

## Dependency and invalidation rules

Compiler objects depend on fields, not merely files.

- A primitive, timing, information, payoff, or equilibrium-concept change hard-invalidates affected results, result contracts, claims, and prose blocks.
- A theorem statement or assumption-set change hard-invalidates its proof roadmap, verbal translation, introduction claim, and displayed implications.
- A proof-only change invalidates proof descriptions and verification status as appropriate, but need not invalidate an unchanged economic mechanism.
- An argument-spine change invalidates narrative and reader contracts, not an otherwise unchanged theorem.
- A target or audience change creates a scoped `ReviewFinding` and, when material, a `RiskOrBlocker` attached to affected authoring references; the dependency engine applies only runtime-defined freshness transitions. It does not invalidate mathematics.
- A terminology change invalidates affected rendered prose and ontology views, not results.
- A closer-paper discovery downgrades affected novelty and positioning claims; it does not change formal truth.
- A manuscript file changed outside the compiler creates an artifact-hash mismatch `ReviewFinding` and, when unresolved, a `RiskOrBlocker`. The system requests classification as semantic, expository, or formatting change before proposing dependency changes; it does not invent a new runtime status.

Before accepting a high-impact change, the compiler must display its manuscript blast radius.

## Validators

Structural validation can be executable; scientific quality remains a human and evaluative judgment. Required validators include:

- every consequential prose claim maps to a current claim ID;
- every cached claim, assumption, verification, and literature field identifies its exact authoritative source version;
- no Paper IR projection can be edited as a scientific source;
- every formal claim uses the route-admissible statement, scope, and assumption revisions;
- no stale hard dependency is presented as current;
- every central result has a reader update and an archetype-specific `ResultPacket` contract;
- every core symbol has a stable economic identity and first-use explanation;
- assumption descriptions distinguish economic role from proof role;
- numerical checks are not presented as proofs;
- introduction and conclusion do not strengthen the body result;
- literature contrasts have current `LiteratureEvidence` refs;
- every consequential literature contrast satisfies a current LiteraturePositioningContract;
- section entry states are delivered by prior sections;
- deleted or demoted results are removed from summaries and transitions;
- the resolved profile never overrides formal invariants.

Validation failure blocks promotion but does not delete the draft. The run remains available for diagnosis and revision.

## Human decisions

The compiler does not define authority levels or confirmation states. It emits typed decision proposals for structural choices such as the central reader update, main-result designation, claim boundary, audience/target selection, material argument reordering, main-text inclusion, voice charter, and manuscript-version promotion. `state_runtime.md` is the sole authority registry and decides which proposal requires an L2 or L3 human transaction and which local operation is permitted at L1. Related proposals should be bundled into one decision packet rather than interrupting after every section.

## Failure modes to reject

- Writing an introduction directly from a theorem sentence without a narrative spine.
- Treating more intuition paragraphs as evidence of better intuition.
- Repeating the theorem in progressively vaguer language.
- Introducing notation before the reader has a question that needs it.
- Explaining assumptions only as mathematical regularity conditions.
- Allowing every specialist agent to rewrite prose in a different voice.
- Copying characteristic wording, cadence, or rhetorical signatures from named papers.
- Moving technical material to an appendix while leaving main-text claims that depend on unexplained objects.
- Treating a polished preview as submission-ready because it reads smoothly.
- Passing schema validation and inferring that the paper is economically important.

## Minimal persistent outputs

For one manuscript version, the compiler needs only:

```text
versioned Paper IR artifact plus canonical PaperIRRef
manuscript source and compiled output
accepted run provenance
one generated status view
```

Critic reports, context packs, intermediate paragraphs, and rejected variants remain run artifacts. They are not promoted into permanent project bureaucracy unless they contain non-reproducible substantive research that the user explicitly accepts.

## Acceptance criterion

The compiler succeeds only when a formally competent reader can recover the paper's question, benchmark, mechanism, main result, assumption roles, and boundary from the manuscript, and can use that understanding to reason about a nearby case, while every displayed claim remains faithful to the accepted theory state.
