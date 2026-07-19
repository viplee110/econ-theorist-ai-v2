# Framing-quality preflight contract

Status: additive v8 negative-diagnosis revision candidate; pre-pilot scientific
and post-pilot host-stabilization deterministic verification passed. R2 and R3
both committed framing and decomposition but no audit or G1 decision. The
locked R3 adjudication classified the current failure
`STRUCTURAL_TAX_PRIMARY` with confidence 0.86 and found no V8 acceptance defect.
A noncanonical semantic-compiler prototype validates the locked negative
diagnosis under unchanged V8 semantics with zero canonical writes. Its held-out
ordinary-model pair is complete: neither arm reached the scientific validator,
but the semantic surface substantially reduced structure and improved detailed
reader recovery without established material scientific degradation. Public
integration remains blocked. The bounded authoring/diagnostic candidate is now
implemented and source-level private-oracle/adversarial checks pass; packaged-
runtime verification remains next, not V9 or another blind pair.

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

Registry v5 added the audit route and advanced `repair.dependency` to an
explicit v5 contract for gap-authorized proactive framing revision while
retaining its one-stale-root mode. Registry v6 preserves that complete catalog
and advances only `audit.framing_economics` to its active-margin instruction.
Registry v1--v5 files, instruction bundles, payload meanings, exported schemas,
selectors, and frozen fixtures remain byte-for-byte unchanged. Framing-quality
records live in the independent `framing_quality/v1` payload namespace.

Registry v8 preserves every v1--v7 route and instruction binding and advances
only `audit.framing_economics` to `framing_quality_route_exit.v2`. Its narrow
diagnostic exception permits all payoff witnesses to be absent only for a fully
downgraded `revise_framing` bundle: it must disclose a causal-attribution or
reoptimization gap with an exact current upstream repair target, make no
active-response, clean-attribution, aggregate-fixed, or distinctive-mechanism
claim, and cannot support `ready_for_g1`. It forbids fabricated payoff
evidence; any supplied witness remains subject to every ordinary strict check.

Historical chains replay under the registry hash to which they were bound.
The current CLI and machine facade use route registry v8 and navigation
registry v7 for new work. The current G1 user-action preflight accepts only a
current replacement dossier that includes a fresh `FramingQualityBundle`; this
current-action rule does not rewrite historical Phase 2 transactions.

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

A choice-dependent mechanism step also carries an `ActiveMarginWitness`. In
one concrete state it names the exact decision and payoff objects and compares
the claimed response with an economically exhaustive deviation under the same
timing, information, beliefs, and continuation convention. A binary comparison
states why its two actions exhaust the feasible set. A multi-action or
continuous choice instead uses the best feasible deviation, a deviation payoff
envelope, or the appropriate local variation rather than a convenient single
alternative. The witness states continuation-inclusive payoffs and the
necessary best-response, mixing, or local optimality condition. Its
`status_basis` also explains how the upstream source changes the payoff gap,
deviation envelope, or local incentive; without that comparative response the
margin remains unresolved. It classifies the margin as active, inactive, or
unresolved and gives a link-specific kill condition.

A downstream technological transition that introduces no new choice does not
repeat an upstream action comparison. But every choice margin on which a
declared force operates must be witnessed somewhere in the chain, regardless
of the paper's result archetype. These comparisons are diagnostic economic
evidence, not proofs of existence or global comparative statics.

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

The v6 core exit checks retain exact bindings, complete benchmark coverage,
primitive-node closure, causal-chain closure, channel reachability, and the
consistency of the proposed attribution. V8 retains those checks and admits an
unwitnessed route exit only for the fully downgraded `revise_framing` case
described in section 2: no active-response or distinctive-mechanism claim, no
aggregate-fixed claim, weak or unresolved attribution, an exact upstream
repair target, and no possible G1 readiness. It must emit stable diagnostic
codes for at least these blockers:

- `aggregate_invariance_unsupported`: a pointwise or state-contingent policy is
  fixed but an aggregate is claimed fixed while its weighting distribution or
  transition law remains endogenous, changed, or unresolved;
- `placebo_control`: a changed parameter reaches no target outcome through a
  reoptimizing choice, endogenous transition, or other active response margin,
  so a frozen ledger or accounting debit is being presented as a mechanism
  control;
- `selection_robustness_unsupported`: `selector_only` or unresolved selection
  is used to claim that an equilibrium-selection artifact has been ruled out.
- `active_margin_witness_missing`: a choice-dependent mechanism step, or a
  force's operative choice margin, has no exact payoff comparison;
- `active_margin_witness_binding`: the purported decision is not a choice on
  the claimed PrimitiveGraph subpath;
- `active_margin_payoff_binding`: cited payoff or continuation objects do not
  bind a connected payoff basis for that decision;
- `inactive_mechanism_link`: a payoff comparison kills a claimed active link,
  but the bundle does not propose an exact causal-attribution revision.

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
It can require a complete, graph-bound comparison and prevent an honestly
inactive or unresolved margin from being promoted. It does not symbolically
solve arbitrary payoff expressions. Semantic acceptance therefore also
requires a blinded rerun to perform the stated dominance and best-response
check rather than merely fill the fields.

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

- unchanged v1--v5 registry and instruction identities;
- strict payload/schema round trips and candidate-contract exposure;
- rejection of each of the three defects found in the Phase 5A.2 pilot;
- rejection of every gap category at `ready_for_g1`;
- rejection of unused, zero-length, or path-detached economic forces;
- rejection of missing, non-choice, off-path, or payoff-detached active-margin
  witnesses for choice-dependent mechanism links;
- acceptance of an unwitnessed downstream mechanical step that introduces no
  new choice when its operative upstream choice is witnessed elsewhere;
- rejection of a declared operative choice margin that tries to bypass the
  witness by changing the result archetype, while non-choice forces remain
  free of invented action comparisons;
- binary exhaustiveness or an appropriate best-deviation, envelope, or local
  variation basis, plus an upstream payoff-sensitivity explanation;
- acceptance of an honestly inactive link only as `revise_framing` with an
  exact causal-attribution repair target, and rejection of inactive or
  unresolved margins at `ready_for_g1`;
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
  explanation, plain-language state/action/payoff/inequality/kill checks for
  its choice margins, one illustrative example, a compact benchmark table,
  and no system vocabulary;
- a fresh Codex rerun on the same public pilot before any claim about improved
  readability or lower human intervention.

The rerun is exploratory evidence. Confirmatory v1/v2 quality, editing-time,
and human-effort claims remain owned by Phase 6.

The earlier v5/v6 deterministic checkpoints do not establish acceptance of
this v8 negative-diagnosis revision. Against the final current pins, 69 focused
framing, registry, model, and distribution tests passed. Route registry v8 is
pinned at `5d2c2efdef205ee1ff188249dcb05cb5a4430d36ef754a93bde402a092aa40c1`
and navigation registry v7 at
`ea133669cd85c073b6352744f2d1b5413dfe33d738752ad17769637acfd9e510`.
The pre-pilot V8 tree passed 584 routine non-long tests with six declared
platform/optional skips, Python compilation, and diff checks. The seven
current schema/resource exporters and an installed-wheel `doctor` check passed
during the v8 pilot freeze; its exact wheel and input hashes are recorded in
`../../review_outputs/phase5a2_v8_codex_public_pilot/preflight_manifest.md`.
The three hour-scale historical gold chains were not rerun because this
additive change preserves their frozen resources. A successful Codex audit
rerun remains open, so this checkpoint is not evidence that readability, paper
quality, or human effort has improved.

The frozen first V8 run has now occurred. Engine baseline `45a540b` and wheel
`dad56a86b8863ca63cf7bae3b37da5bcacabeee66cf99c1ea5ad71f7a9f3854d`
committed framing at `a1970a85...` and decomposition at `8a7e73a...`. Audit run
`run_op_29e4aa557e4823cded54a6c32ef447aaef93376147ad78cb` produced an honest
unwitnessed `revise_framing` candidate but did not pass the exact primitive-path
contract after its two declared repairs. No FramingQualityBundle, replacement
GateDossier, or G1 decision entered the canonical head. Its final
`failed_terminal` receipt left the head unchanged and the RouteRun resumable.
See the exact [run report](../../review_outputs/phase5a2_v8_codex_public_pilot/run_report.md).

That run attempted but did not demonstrate the V8 negative-diagnosis exit. It
also exposed a leading candidate-source parse failure, incomplete path-error
diagnostics, a hidden finish-warning grammar, and mutable evidence-source
paths. The bounded post-pilot stabilization candidate addresses those host
surfaces without changing this contract's scientific conditions. Those fixes
were not exercised by the original run. The post-pilot source candidate passed
594 routine non-long tests with six declared skips, all seven exporters, and
required `doctor` checks. The corrected committed wheel then ran the same-case
R2 blind test without transport or encoding interference. It committed framing
at `73fb8d5b...` and decomposition at `467a1561...`, but the audit exhausted
two repairs on an unsupported semantic-level literal, a fixed/movable semantic
conflict, and a channel-endpoint mismatch. Its `failed_no_effect` finish left
the canonical head unchanged and did not create a FramingQualityBundle,
replacement GateDossier, or G1 decision. This is host-stability evidence and
diagnosed model-output evidence, not acceptance of the V8 negative-diagnosis
exit. See the [R2 report](../../review_outputs/phase5a2_v8_codex_public_pilot/rerun_attempt2_run_report.md).

The isolated cold-reader retell remains frozen with its original provisional
burden H3: it recovered the missing active-margin diagnosis but could not
recover the certificate guarantee, buyer actions, or operative payoff
comparison from the memo. The independent keyed adjudication separately
assigned H4 and `R-FAIL`, because repairing the memo requires an upstream
state/payoff graph and ledger choice rather than several local rewrites. Its
economics scores were `0, 1, 1, 2, 2`, hence `A-FAIL`, with disposition
`REVISE`; machine execution was mixed because framing and decomposition
committed while the audit did not. See the exact
[independent evaluation](../../review_outputs/phase5a2_v8_codex_public_pilot/rerun_attempt2_independent_evaluation_report.md),
30,626 bytes, SHA-256
`23cd4e7ed76c967f2e14f373ace6331a72748e7db0f18f70f1b9e8879c6a7d50`.

The adjudicator classified model-content/mapping error as primary (confidence
0.80), diagnostic/authoring-surface ambiguity as secondary (0.70), and found
only 0.35 confidence that validator overconstraint contributed. It therefore
does not justify V9, a relaxed endpoint or semantic-ledger predicate,
`policy_rule` in the semantic-level enum, or an engine-added scientific
primitive. The only justified engine follow-up is a diagnostic-only surface
improvement that reports benchmark/object IDs, conflicting values, expected
endpoints, and exact payload-relative paths for fixed/endogenous and endpoint
failures. That source change postdates R2 and cannot be treated as part of its
treatment.

The researcher selected the guaranteed-service ledger on 2026-07-18. That
choice killed the unsupported positive-stock inspection margin and limited R3
to an honest zero-certificate-state/reweighting question without a newly
invented buyer-facing force. The ordinary-model task followed the frozen
[R3 protocol](../../review_outputs/phase5a2_v8_codex_public_pilot/rerun_attempt3_route1_protocol.md):
it committed the revised ResearchQuestion/BenchmarkSet and PrimitiveGraph/
proposal-only GateDossier, then exhausted two audit repairs and recorded
`failed_no_effect`; no FramingQualityBundle, replacement dossier, or human G1
decision was committed.

The locked two-phase adjudication then recovered eight of ten economics items
but found that mechanical authoring dominated the failure. Its final decision
was `STRUCTURAL_TAX_PRIMARY` (0.86), not an acceptance-semantics defect. A
noncanonical semantic compiler subsequently reproduced the exact V8 contract,
corrected only the bounded `behavioral_response`/`equilibrium_object`
representation choice, derived the replacement-dossier condition and five
hard relations, and passed the unchanged candidate validator in memory. See
the exact [adjudication and compiler shadow record](../../review_outputs/phase5a2_v8_codex_public_pilot/rerun_attempt3_adjudication_and_compiler_shadow.md).

This shadow replay is not a canonical audit and not new model-generation
evidence. The held-out paired ordinary-model shadow comparing the free-form
Transaction authoring surface with the semantic compiler is now complete. It
provides a clear directional structural-burden signal but no end-to-end
feasibility winner because neither arm passed. Result solving, public bridge
integration, and an exploratory v1/v2 quality comparison remain premature.

The additive semantic-authoring V2 revision is a noncanonical preparation
surface only. It preserves the V1 surface and every V8 scientific predicate.
The semantic-authoring and frozen shadow surfaces report a bounded aggregate
of exact envelope and typed-payload failures, including JSON pointers and
expected/observed schema values; this reporting is not wired into the public
bridge. For an active margin, the model still authors the actions, payoff
comparison, feasibility basis, inequality, activity judgment, and kill
condition. V2 forbids every hand-authored `active_margin_witness`, including
one on a step without a margin intent, and rejects a V1 draft at a V2 entry
point. V2 requires an intent for every V8-required payoff witness, except for
the exact fully-downgraded unwitnessed-negative predicate already defined by
V8. The compiler binds a graph decision, unique payoff basis, consequence
path, and public-state object only when each binding is deterministic;
otherwise it fails closed with alternatives rather than inventing a scientific
link. The bounded revision also projects away only
`forces[*].margin_node_id`. Force source and target remain model-authored.
Every margin intent and residual force locator must explicitly select
`source`, `target`, or `unique_interior` on one force-cited causal step; there
is no default. A margin intent locates a force only when it names that force or
its step names exactly one force, and `unique_interior` succeeds only for one
path with exactly one interior node. The model still authors causal node IDs,
any necessary channel waypoints, force selection when a step is not unique,
payoff disambiguators, public-state object IDs, and payload graph declarations
such as `distinctive_mechanism.distinctive_edge_ids`. Active-witness
consequence edge paths remain compiler-owned. An intentional scope limitation
remains in the memo's scope condition; `disclosed_gaps` remains reserved for an
unresolved defect and therefore still
blocks `ready_for_g1`. This revision is not public bridge integration or
evidence of a fresh model pass.

The accident-liability authoring pair frozen at engine commit
`a03d1025ac9c9bcaefcd112de3e8c63694b97c8f` is complete. Neither independent
ordinary-model arm reached unchanged V8 validity within three attempts; both
stopped before the scientific validator, wrote no canonical state, and
confirmed no human gate. Semantic V2 nevertheless reduced final source bytes
by 51.22% and final leaf fields by 53.74%. Blinded economics assigned both
candidates `REVISE` with no established material scientific degradation. Both
met the frozen basic-recovery key; the Semantic reader additionally completed
every common probe, while the Transaction reader could not recover preventive
payoff 2 or the same detailed claim boundary from its memo alone.

Locked source inspection found residual deterministic graph binding on both
surfaces. The implemented Transaction near-match reports
`operations/<index>/relation/downstream/semantic_hash` with bounded canonical-
safe expected/observed fields only when one unique candidate differs in one
field; ties and multi-field differences retain the generic failure. Semantic
binding diagnostics return the observed node and kind plus every compatible
choice on the selected causal step. Deterministic preflight rejects a fixed
row whose channel traverses an exactly bound held-fixed choice to an outcome,
and rejects a witnessed force whose margin is not the exact decision choice.
It deliberately does not treat aggregate `pointwise_policy_fixed=true` as a
generic contradiction merely because a different object reoptimizes: that
boolean has no object binding, so such a rule would reject valid economics. A
future blocker requires an explicit policy-object binding. V8 remains the
unchanged scientific authority. Future case briefs and evaluation keys must
align explicitly on held-fixed primitives such as enforceability.

The shadow transport now rejects malformed UTF-8, duplicate JSON keys,
wrappers, arrays, prefixes, and suffixes; it never trims, extracts,
reserializes, or repairs model bytes. Same-directory no-replace publication is
atomic, exact source replay is idempotent, the scientific projection is
published before its receipt, and a receipt is the completion marker. This is
still noncanonical. Do not start another blind pair or public integration
until packaged-runtime transport/oracle verification passes. See the exact
[preparation record](../../review_outputs/phase5a2_v8_authoring_pair_v2/preparation_record.md),
[final adjudication](../../review_outputs/phase5a2_v8_authoring_pair_v2/final_adjudication.md),
and [machine decision](../../review_outputs/phase5a2_v8_authoring_pair_v2/FINAL_DECISION.json).
