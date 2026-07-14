# V5.1 fresh public Codex pilot protocol

Status: **frozen before generation**
Protocol date: 2026-07-14 (Australia/Perth)
Case id: `consumable-quality-certificates-public-v5.1`
Engine/source commit: `51789a55d5dcbdeb70455f2fcdd3a33502efae92`
Execution branch: `agent/v5-real-codex-pilot`
Navigation policy: `navigation-registry.v3`
Navigation policy canonical digest: `fe285a46a1da5e1dd0f9c2953d0c6a6cf7474ff39129d53c5be96548548bf594`
Navigation registry raw-file SHA-256: `95064b65fa53eadd5e9a77aa039f255df8a08e2c6b05c9769c77c1d7a670f226`
Wheel SHA-256: `0C16DAD616168C6781FBA28343CAEB9C2683B09118DA243A8589FAC8DC60D920`

## 1. Purpose and claim boundary

This is a fresh, bounded regression pilot of the repaired pre-G1 framing
workflow. It asks whether an exact wheel built from the frozen source commit
can progress from question framing through primitive decomposition to the
engine-owned economics audit without repeating a completed decomposition or
silently inheriting an inadequate host budget.

The pilot may establish machine-path correctness for this case and may reveal
scientific or reader-facing weaknesses. It cannot establish that v2 is better
than v1, reduces human effort generally, produces Top-5 work, or is ready for
submission. Those remain Phase 6 claims.

The failed V5 run and pre-V5 baseline are inaccessible to the generator until
all V5.1 candidates and canonical responses have been frozen.

## 2. Frozen bindings

- The researcher-authored scientific seed is byte-for-byte identical to the
  V5 seed; its 1,237-byte research block has SHA-256
  `7EBD071530BD591D7B689A5946132AAF2007F817632A65FC1CC8F3A2F46CD2CB`.
- The project name is `Consumable Quality Certificates`.
- The generator is a fresh Codex task with no inherited conversation history.
- Start/resume requests omit `budget_units`; the installed route registry owns
  the default budget. An explicit budget is permitted only for a separately
  labeled diagnostic and may not replace the canonical pilot path.
- The installed wheel is the exact distribution named above, built from the
  frozen source commit after that commit was created.
- Every engine invocation uses an isolated `LOCALAPPDATA` beneath the clean
  pilot root.

## 3. Generator isolation

The clean execution root is
`C:\tmp\etai-v5_1-public-pilot-20260714`. Before generation it may contain
only:

1. the installed v2 wheel and isolated runtime;
2. the local `econ-theorist-v2` skill;
3. `CASE.md`, containing the public seed and execution constraints; and
4. the empty isolated operational-home parent.

The generator may read only this clean root, the installed skill, public CLI
output, and WorkPackets returned by the bridge. It may not read or search the
source checkout, repository history, source files, tests, fixtures, old pilot
output, audit reports, reference candidates, gold cases, literature, the web,
parent or sibling directories, or another agent's context. It may not spawn
subagents.

The WorkPacket and its `candidate_authoring_contract` are the sole scientific
instruction, context, schema, and output contract for each candidate. Helper
code may be saved only beneath the packet's declared shadow root, and a
candidate may be saved only at its declared candidate path.

## 4. Execution path

The installed engine, not this protocol or the generator, selects every route.
The expected pre-G1 path is:

1. `frame.question_and_benchmarks`;
2. `decompose.primitives`;
3. `audit.framing_economics`; and then
4. a human-owned G1 decision or an engine-owned framing revision.

The generator starts or resumes through `etai codex invoke`, completes one
agent-authorized route at a time, and continues only after a canonical
`committed` response authorizes another agent route. It must stop before G1 and
must never fabricate or infer a human decision.

For each route, the generator may make at most three candidate attempts: the
initial candidate plus at most two sequential repairs based only on structured
bridge diagnostics. If a route does not commit after those attempts, the run
stops without bypassing validation.

The generator must not force, skip, reorder, or directly invoke a route. Any
engine-selected divergence from the expected path is retained as a finding.

## 5. Evidence retention

Retain without retrospective rewriting:

- exact wheel, source commit, hashes, and preflight inventory;
- every bridge request and raw canonical response;
- every WorkPacket, candidate attempt, repair diagnostic, and declared output;
- canonical project state, route/commit identifiers, and any G1 dossier;
- generator report, timestamps, wall time, and observable usage;
- focused tests, doctor/exporter/replay checks, and repository status; and
- post-freeze economics, reader-transfer, and protocol audits.

Do not retain secrets, credentials, or unrelated host data.

## 6. Noncompensatory acceptance criteria

### Machine gate

- The engine commits each scientifically valid selected route, or honestly
  terminates/routes to revision when a scientific gate fails.
- A fresh exact decomposition package suppresses automatic repeated
  decomposition while manual re-decomposition remains legal.
- Route-default budgeting admits the economics audit; an explicit 10,000-unit
  request remains a real hard cap.
- No human-owned decision is manufactured.
- Completion, retry, and replay preserve exactly-once semantics and canonical
  state.
- Focused regressions, exporters, and `etai doctor` pass on the frozen build.

### Economics gate

Fluent prose cannot compensate for a critical semantic error. The audit must
detect, repair, or block any instance of:

1. confusing a fixed conditional inspection rule with fixed aggregate
   inspection when equilibrium composition or choice probabilities change;
2. calling a benchmark a clean consumable-stock intervention when its cost or
   policy ledger makes it a placebo; or
3. treating a fixed lexicographic selector as proof of equilibrium-selection
   robustness.

Every benchmark must state its intervention, endogenous objects, fixed
objects, comparison object, and failure interpretation. If a clean framing is
not supported, `revise_framing` is the correct outcome.

### Reader-transfer gate

A cold theory reader, using only the economist-facing memo or dossier, must be
able to recover the puzzle, opposing forces, a three-link mechanism, a minimal
example or state comparison, a falsifiable kill condition, and the role of
every benchmark. The memo must avoid internal workflow jargon and the audit
must list concrete remaining edits.

## 7. Diagnostic comparison

Only after V5.1 output is frozen may independent auditors compare it with the
failed V5 run or pre-V5 baseline. Exploratory targets are holistic quality at
least 7.5/10, readability at least 7/10, abstraction severity at most 4/10,
and substantive human-editing burden at most 4/10. Zero critical economics
errors is mandatory regardless of aggregate scores.

## 8. Decision rule

- **Pass:** machine, economics, and reader-transfer gates pass.
- **Scientific revise:** machine behavior is correct but economics or reader
  transfer fails; make only a failure-driven scientific change.
- **Protocol/engine fail:** isolation, route ownership, canonical commit,
  budgeting, or exactly-once behavior fails; repair before interpreting prose.
