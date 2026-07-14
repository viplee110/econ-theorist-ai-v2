# V5 public Codex pilot failure report

Status: **engine/protocol failure; scientific comparison not reached**  
Case: `consumable-quality-certificates-public-v5`  
Frozen wheel SHA-256: `8CA2E91911EA8A42C956B6FF4C12595C81C13A932D964855FCD9996D888E0004`

## Observed route sequence

The fresh, isolated generator committed:

1. `frame.question_and_benchmarks` on candidate attempt 2;
2. `decompose.primitives` on candidate attempt 2; and
3. a second, distinct `decompose.primitives` refinement on candidate attempt 3.

The engine then opened a third `decompose.primitives` run. The generator was
stopped before authoring it. That run has zero candidate attempts and zero
completion requests. No human decision or effective G1 approval was created.

## Root cause

Two independent machine defects combined into one deterministic loop:

- the Codex bridge always forwarded its 10,000-unit request default, thereby
  overriding the framing-audit route's configured 18,000-unit default; and
- automatic navigation treated an already completed exact decomposition scope
  as eligible again.

At the terminal canonical head, the lineage-valid audit context required
10,226 `etai_lexical_v1` units. The frozen 10,000-unit override therefore
excluded it. The old dossier/current graph pairing was correctly rejected as a
lineage mismatch, leaving repeated decomposition as the only candidate. A
read-only 18,000-unit probe admitted both audit and decomposition, confirming
that raising the budget alone would have produced ambiguity rather than the
intended route sequence.

## Correct stop and claim boundary

The correct response was to stop before the third candidate. Another
decomposition could append graph and immutable dossier versions but could not
perform the economics audit or authorize G1. The run therefore provides no
valid evidence that V5 improves economic quality, readability, or human effort.
Those questions remain open for a fresh rerun after the engine repair.

The exact requests, responses, candidate attempts, canonical store, generator
report, and terminal diagnostic are retained in this directory without
retrospective rewriting.

## Repair implemented for the fresh rerun

- Navigation policy v3 gives automatic decomposition a versioned
  `uncompleted_decomposition_scope.v1` selector. It suppresses a focus only
  when every selected exact question/benchmark pair already has a current,
  fresh PrimitiveGraph and matching pre-audit G1 dossier. Explicit scientific
  re-decomposition remains legal, and an authorized upstream repair reopens
  automatic eligibility.
- A Codex start request now leaves `budget_units` absent by default. Navigation
  therefore uses each route's own configured budget; an explicit budget remains
  a hard cap.
- When budget insufficiency and a gate-shaped diagnostic coexist, navigation
  reports `repair_required` before `human_decision_required`.
- An unfinished run bound to an inactive navigation-policy hash is not silently
  resumed after upgrade; it enters inspection/repair.

The frozen route registries and historical navigation-policy v1/v2 bytes remain
addressable and unchanged. The changed automatic candidate semantics are bound
to a new navigation-policy v3 hash.

## Verification before rerun

- four directly modified modules: 34 tests passed in 267.695 seconds;
- complete routine non-long regression selection: 530 tests passed with six
  platform/optional skips in 553.387 seconds;
- focused bridge, exact 10,000-unit cap, multi-benchmark, post-audit-dossier,
  upgrade-resume, Python compilation, and `git diff --check` checks passed.

A new clean root, frozen wheel, and protocol are required for V5.1. The failed
V5 root and evidence must not be reused as generator context.
