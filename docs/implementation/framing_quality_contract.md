# Framing-quality preflight contract

Status: additive v5 implementation candidate; deterministic acceptance
complete, fresh real-Codex rerun pending

This contract owns the first pilot-driven scientific strengthening after the
Phase 5A.2 public Codex framing run. It addresses a narrow failure: a
`ResearchQuestion` and `BenchmarkSet` can be schema-valid while the proposed
controls do not isolate their advertised economic channels and the resulting
explanation remains too abstract for an economist to recover on a first read.

It does not define a second research workflow, certify a contribution, or
replace the human G1 question-and-benchmark decision.

## 1. Position in the research graph

The additive route is:

```text
frame.question_and_benchmarks
-> decompose.primitives
-> audit.framing_economics
-> human G1 decision
```

The audit occurs after primitive decomposition because channel reachability
cannot be checked reliably from prose alone. It occurs before G1 because an
economically meaningless control must not become an accepted dependency merely
because its formal description is precise.

The first run consumes the exact current `ResearchQuestion`, `BenchmarkSet`,
`PrimitiveGraph`, and pre-audit G1 `GateDossier`. It creates one
`FramingQualityBundle` and a new, version-1 replacement `GateDossier` whose
ordered evidence includes the bundle. It never mutates or supersedes the
source dossier because gate dossiers are immutable evidence packages. The
route proposes; it never records an effective L2 decision.

Only if an honest result is `continue_diagnostic`, a later run also consumes the
exact current bundle and supersedes only that bundle at the same four-object
upstream scope. It then creates another immutable replacement dossier for the
new exact bundle version. This permits scientific iteration without silently
changing the question, benchmark, primitive graph, or source dossier. A
`ready_for_g1` or `revise_framing` bundle is terminal for that exact scope and
cannot be continued in place.

If the audit discovers that the canonical question or benchmark is false or
misdescribed, its action is `revise_framing`. At least one disclosed gap must
name each proposed repair through an exact typed `ResearchQuestion`,
`BenchmarkSet`, or `PrimitiveGraph` ref. The v5 `repair.dependency` route may
then supersede exactly one such current target; it cannot use the bundle as
authority to switch to an unnamed object. Ordinary dependency invalidation
stales the primitive graph, quality bundle, and dossier before decomposition
and the audit are rerun. The bundle may disclose an error; it may not
reinterpret an incorrect benchmark into correctness.

## 2. Compatibility boundary

Registry v5 adds the audit route and advances `repair.dependency` to an explicit
v5 contract for gap-authorized proactive framing revision while retaining its
one-stale-root mode. Registry v1--v4 files, instruction bundles, payload
meanings, exported schemas, selectors, and frozen fixtures remain byte-for-byte
unchanged. Framing-quality records live in the independent
`framing_quality/v1` payload namespace.

Historical chains replay under the registry hash to which they were bound.
The current CLI and machine facade use v5 for new work. The v5 G1 user-action
preflight accepts only a current replacement dossier that includes a fresh
`FramingQualityBundle`; this current-action rule does not rewrite historical
Phase 2 transactions.

## 3. Canonical bundle

The bundle binds exact entity versions and records four scientific objects:

1. an archetype-sensitive economic tension;
2. an economist-facing memo specification;
3. one semantic audit for every exact benchmark record;
4. disclosed limitations and a non-upgrading proposed action.

The memo specification contains a one-sentence puzzle, the standard force, the
counterforce when the result archetype needs one, a closed three-link causal
chain, economic stakes, one explicitly illustrative minimal example, a
one-sentence takeaway, and the kill condition. The three links are an
exposition contract for this one-page projection, not a claim that every
paper's full mechanism has exactly three arrows.

Opposing forces are mandatory only for result archetypes whose claimed puzzle
depends on a reversal, threshold, nonmonotonicity, or tradeoff. A
one-direction `mechanism_explanation` uses `causal_channel`; it may use
`force_conflict` only when competing forces really generate its puzzle. A
representation, equivalence, existence-boundary, or impossibility framing uses
its appropriate tension rather than inventing two comparative-static effects.
Every declared force must appear in the three-link explanation. Each cited
step is a nonzero directed subpath of that force's source--operative-margin--
target path; a zero-length or merely named force is not an economic mechanism.

The canonical bundle is scientific state. Its rendered one-page Markdown memo
and compact benchmark table are derived views. A rendered view must not expose
entity IDs, schema terminology, validator findings, or orchestration language,
and it cannot become an independent source of scientific truth.

## 4. Benchmark semantics

Every benchmark is covered exactly once. Its audit distinguishes:

- objects changed by the comparison;
- objects held fixed and the level at which each is fixed;
- choices that reoptimize;
- distributions, transitions, choices, or equilibrium objects that remain
  endogenous;
- target outcomes;
- the active path from the changed object to each attributed outcome;
- the strength and limitation of the resulting attribution;
- how equilibrium-selection artifacts are handled.

The level vocabulary distinguishes at least primitives, pointwise or
state-contingent policies, conditional distributions, transition kernels,
stationary distributions, aggregates, choices, payoff ledgers, and equilibrium
correspondences. Holding one level fixed never silently fixes another.
Reoptimizing objects bind exact `choice` nodes. A non-choice active response
may instead bind an endogenous conditional distribution, transition kernel,
stationary distribution, equilibrium object, or equilibrium correspondence to
a compatible graph node. An outcome label by itself is not an active margin.
Two differently named ledger objects cannot use the same graph node to claim
that the same semantic level is both fixed and movable.

Selection assurance is one of `unique_equilibrium`, `continuous_branch`,
`all_equilibria`, `selector_only`, `unresolved`, or `not_applicable`. A fixed
selector is a reproducible convention, not evidence that a comparative static
is robust to equilibrium selection.

## 5. Noncompensatory automatic checks

The v5 exit validator checks exact bindings, complete benchmark coverage,
primitive-node closure, causal-chain closure, channel reachability, and the
consistency of the proposed attribution. It must emit stable diagnostic codes
for at least these three blockers:

- `aggregate_invariance_unsupported`: a pointwise or state-contingent policy is
  fixed but an aggregate is claimed fixed while its weighting distribution or
  transition law remains endogenous, changed, or unresolved;
- `placebo_control`: a changed parameter reaches no target outcome through a
  reoptimizing choice, endogenous transition, or other active response margin,
  so a frozen ledger or accounting debit is being presented as a mechanism
  control;
- `selection_robustness_unsupported`: `selector_only` or unresolved selection
  is used to claim that an equilibrium-selection artifact has been ruled out.

These checks are noncompensatory. Good prose, formal precision, or another
clean benchmark cannot offset one blocker. An honest bundle may retain an
unresolved issue only by downgrading its attribution and proposing
`continue_diagnostic` or `revise_framing`; it may not propose `ready_for_g1`.
Every `DisclosedFramingGap` is unresolved by construction, regardless of its
category, so any disclosed gap blocks readiness. Conversely, a known
endogenous or changed weighting distribution is not automatically a gap when
the bundle does not claim the aggregate fixed and traces composition as the
active mechanism. A fully explained `qualified` attribution records a known
limitation and may be ready; `weak` or `unresolved` attribution may not.

Automatic validation establishes internal consistency and declared channel
identification, not the truth of a model-produced economic classification.

## 6. Human G1 authority

Only the human researcher decides whether:

- the question and consequence are important;
- the stated forces are real economic mechanisms rather than renamed algebra;
- each benchmark is economically informative rather than an artificial freeze;
- the minimal example clarifies the operative tradeoff;
- any disclosed equilibrium-selection limitation is acceptable;
- an economist can accurately retell the puzzle, mechanism, boundary, and
  nearby case with an acceptable editing burden.

Model scores and reader probes are diagnostic evidence. They cannot confirm
G1 or turn an unresolved scientific gap into an approval.

## 7. Acceptance evidence

The implementation slice is not accepted until it demonstrates:

- unchanged v1--v4 registry and instruction identities;
- strict payload/schema round trips and candidate-contract exposure;
- rejection of each of the three defects found in the Phase 5A.2 pilot;
- rejection of every gap category at `ready_for_g1`;
- rejection of unused, zero-length, or path-detached economic forces;
- rejection of self-declared reoptimization on outcome nodes and of same-level
  fixed/movable aliases;
- acceptance of a typed endogenous transition as the active response margin;
- acceptance of known endogenous composition when no aggregate invariance is
  claimed, and of a fully explained qualified attribution;
- acceptance of a one-direction `causal_channel` without an invented
  counterforce;
- acceptance of an honestly downgraded unresolved-selection case without
  promoting it to G1-ready;
- rejection of a current G1 action against the immutable pre-audit dossier;
- staleness of the bundle and strengthened dossier after an upstream question,
  benchmark, or primitive change;
- exact retry and replay behavior for the new route;
- all seven current schema/resource exporter checks, including
  `python scripts/export_framing_quality_schemas.py --check`;
- a derived memo with one puzzle, the relevant tension, a closed three-link
  explanation, one illustrative example, a compact benchmark table, and no
  system vocabulary;
- a fresh Codex rerun on the same public pilot before any claim about improved
  readability or lower human intervention.

The rerun is exploratory evidence. Confirmatory v1/v2 quality, editing-time,
and human-effort claims remain owned by Phase 6.

The deterministic portion of this predicate passed on the implementation
branch: 522 routine non-long tests passed with six reported platform/optional
skips; all seven schema/resource exporters, compilation of 144 Python files,
`doctor` with `required_ok=true`, local Markdown-link validation, and
`git diff --check` passed. Registry v5 is pinned at
`91ef2dcf75bcc4bce22241466477a99f9e34cbd8ac537974e1017a2e1fe92195`
and navigation v2 at
`262140bc73fb2b0a14c0d7ea884b36d07997aae4c63403f9091bb28ad2fccf81`.
The fresh Codex rerun bullet remains open, so this checkpoint is not evidence
that readability, paper quality, or human effort has improved.
