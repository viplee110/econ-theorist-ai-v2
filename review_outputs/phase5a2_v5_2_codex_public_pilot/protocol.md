# V5.2 fresh public Codex pilot protocol

Status: **frozen before generation**
Protocol date: 2026-07-15 (Australia/Perth)
Case id: `consumable-quality-certificates-public-v5.2`
Engine/source commit: `cd018e54ffa8b8645058ff993562acec0fdf4807`
Execution branch: `agent/v5-real-codex-pilot`
Navigation policy: `navigation-registry.v4`
Navigation policy canonical digest: `4027c38ffbc43af55f2c8fc1fd6bdf634024e9b7a3cc1e88b426c20556634833`
Packaged navigation raw-file SHA-256: `fde0e81d9bc960ec7abd73433546e68a387817db5365ba8dac74551c16b41c47`
Wheel SHA-256: `d0e59192a629a6bc3dccd513e71d9cdeaa6de68d495f4d593e1b45c3ff54e317`

## 1. Purpose and claim boundary

This is a fresh, bounded regression pilot of the repaired pre-G1 framing
workflow. It asks whether an exact wheel built from the frozen source commit
can progress from question framing through primitive decomposition to the
engine-owned economics audit, without replaying framing inputs, forcing a
route, or overriding route-owned budgets.

The pilot may establish machine-path correctness for this case and may reveal
scientific or reader-facing weaknesses. It cannot establish that v2 is better
than v1, reduces human effort generally, produces Top-5 work, or is ready for
submission. Those remain Phase 6 claims.

The failed V5 and V5.1 runs, repository source, tests, and all prior outputs
are inaccessible to the generator until every V5.2 candidate and canonical
response has been frozen.

## 2. Frozen bindings

- The researcher-authored scientific seed is byte-for-byte identical to the
  prior seed: 1,237 UTF-8 bytes with SHA-256
  `7EBD071530BD591D7B689A5946132AAF2007F817632A65FC1CC8F3A2F46CD2CB`.
- The project name is `Consumable Quality Certificates`.
- The generator is a fresh Codex task with no inherited conversation history.
- The initial request supplies `requested_scope` and `framing_intent` once.
  Every ordinary continuation after a committed route omits both fields.
  Replaying them is an explicit reframe and is prohibited in this pilot.
- Every start/resume request omits `budget_units`. The installed v4 policy owns
  the expected defaults: 4,000 for framing, 8,000 for decomposition, and
  18,000 for the framing economics audit.
- The installed wheel is the exact distribution named above, built from the
  frozen source commit after that commit was created.
- Every engine invocation uses an isolated `LOCALAPPDATA` beneath the clean
  pilot root.

## 3. Generator isolation

The clean execution root is
`C:\tmp\etai-v5_2-public-pilot-20260715`. Before generation it may contain
only the installed wheel and isolated runtime, the local `econ-theorist-v2`
skill, `CASE.md`, and the empty isolated operational-home parent.

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
`committed` response authorizes another agent route. It must stop before G1
and must never fabricate or infer a human decision.

For each route, the generator may make at most three candidate attempts: the
initial candidate plus at most two sequential repairs based only on structured
bridge diagnostics. If a route does not commit after those attempts, the run
stops without bypassing validation. The generator must not force, skip,
reorder, or directly invoke a route.

## 5. Evidence retention

Retain without retrospective rewriting the exact wheel and hashes; every
bridge request and raw response; every WorkPacket, candidate attempt, and
repair diagnostic; canonical project state and run identifiers; generator
report, timestamps, and observable usage; and all post-freeze audits. Do not
retain secrets, credentials, the virtual environment, or unrelated host data.

## 6. Noncompensatory acceptance criteria

### Machine gate

- The engine commits each scientifically valid selected route, or honestly
  terminates/routes to revision when a scientific gate fails.
- The exact path advances through one framing and one decomposition run to the
  economics audit without repeated framing or decomposition.
- Omitted budgets resolve to 4,000, 8,000, and 18,000 on the expected path.
- No human-owned decision is manufactured.
- Completion, retry, and replay preserve exactly-once semantics and canonical
  state.
- Focused and complete regressions, exporters, and `etai doctor` pass on the
  frozen build.

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

## 7. Decision rule

- **Pass:** machine, economics, and reader-transfer gates pass.
- **Scientific revise:** machine behavior is correct but economics or reader
  transfer fails; make only a failure-driven scientific change.
- **Protocol/engine fail:** isolation, route ownership, canonical commit,
  budgeting, or exactly-once behavior fails; repair before interpreting prose.
