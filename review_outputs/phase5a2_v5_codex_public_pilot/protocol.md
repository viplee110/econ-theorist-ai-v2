# V5 fresh public Codex pilot protocol

Status: **frozen before generation**  
Protocol date: 2026-07-14 (Australia/Perth)  
Case id: `consumable-quality-certificates-public-v5`  
Engine/source commit: `de9de84db486975ffc63d2e51adcd1ca8dbd3a05`  
Execution branch: `agent/v5-real-codex-pilot`

## 1. Purpose and claim boundary

This is a bounded, diagnostic regression pilot. It asks whether the V5
pre-G1 framing workflow changes real-model behavior on the same synthetic
public research seed used in the pre-V5 pilot.

The pilot may establish that the installed engine can execute the V5 framing
path and may reveal concrete scientific or reader-facing failures. It cannot
establish that v2 is better than v1, reduces human effort in general, produces
Top-5 work, or is publication-ready. Those claims remain Phase 6 questions.

The pre-V5 pilot is a development baseline only. Its output and audits are
inaccessible to the generator until every V5 candidate and canonical response
has been frozen.

## 2. Frozen bindings

- The researcher-authored scientific seed is reproduced verbatim from
  `case.md` in `generator_case.md`.
- The project name is `Consumable Quality Certificates`.
- The generator is a fresh Codex task with no inherited conversation history.
- The selected model is recorded as the available GPT-5 family Codex model;
  any more specific provider build is recorded only if the host exposes it.
- Each bridge request uses `budget_units: 10000`, matching the earlier pilot's
  deterministic bridge budget field. Actual host usage and wall time are
  recorded separately when observable.
- The installed wheel is built from the frozen engine/source commit above;
  its filename and SHA-256 digest are recorded in the final manifest.
- The operational home is isolated beneath the clean pilot root by setting
  `LOCALAPPDATA` for every engine invocation.

## 3. Generator isolation

The clean execution root is
`C:\tmp\etai-v5-public-pilot-20260714`. Before generation it may contain only:

1. the installed v2 wheel and its isolated runtime;
2. the local `econ-theorist-v2` skill;
3. `CASE.md`, containing the public seed and execution constraints;
4. request files and artifacts created by this run; and
5. the isolated operational home used by the installed engine.

The generator may read only the clean root, the installed skill, the installed
engine's public CLI output, and WorkPackets returned by the bridge. It may not
read or search the source checkout, repository history, source files, tests,
fixtures, old pilot output, audit reports, reference candidates, gold cases,
literature, the web, parent or sibling directories, or another agent's context.
It may not spawn subagents.

The WorkPacket and its `candidate_authoring_contract` are the sole scientific
instruction, context, schema, and output contract for each candidate. Helper
code may be saved only under the packet's declared shadow root, and a candidate
may be saved only at the path declared by that packet.

## 4. Execution path

The installed engine, not this protocol or the generator, selects each next
route. The expected V5 pre-G1 path is:

1. `frame.question_and_benchmarks`;
2. `decompose.primitives`;
3. `audit.framing_economics`; and then
4. a human-owned G1 decision.

The generator starts or resumes through `etai codex invoke`, completes one
agent-authorized route at a time, submits its candidate through the same
bridge, and proceeds only when the canonical response says `committed` and
authorizes another agent route. It must stop before G1 and must never fabricate
or infer a human confirmation.

For each route, the generator may make at most three candidate attempts: the
initial candidate plus at most two sequential repairs based only on structured
bridge diagnostics. If the route is not committed after those attempts, the
run stops and records the terminal failure without bypassing validation.

The generator must not force, skip, reorder, or directly invoke a route. If the
engine-selected sequence differs from the expected path, the actual sequence
is retained and treated as a protocol finding.

## 5. Evidence retention

The run retains, without retrospective rewriting:

- the exact installed wheel and SHA-256 digest;
- the exact clean-root inventory before first invocation;
- every start/continuation/completion request and raw canonical response;
- every WorkPacket, candidate attempt, and structured repair diagnostic;
- canonical project state, route/commit identifiers, and the G1 dossier;
- generator report, invocation timestamps, wall time, and observable usage;
- evidence of the isolated operational home and absence of forbidden inputs;
- focused engine tests, exporters, doctor output, replay/retry checks, and
  repository status after evidence is imported; and
- post-freeze independent economics, reader-transfer, and protocol audits.

Secrets, credentials, and unrelated host data must not be retained.

## 6. Noncompensatory acceptance criteria

### 6.1 Machine gate

- All three engine-selected pre-G1 routes commit canonically, unless the engine
  honestly terminates or routes to revision because a scientific gate fails.
- No human-owned decision is manufactured.
- Candidate submission, retry, replay, and idempotence preserve exactly-once
  semantics and canonical state.
- Focused regressions, exporters, and `etai doctor` pass on the frozen build.

### 6.2 Economics gate

No critical semantic error may be offset by fluent prose or a high aggregate
score. In particular, the V5 workflow must detect, repair, or explicitly block
each of these failure classes if it appears:

1. treating a fixed conditional inspection rule as fixed aggregate inspection
   when equilibrium composition or choice probabilities can change;
2. labeling a benchmark as isolating the consumable-stock channel when its
   cost or policy ledger makes the intervention economically placebo; and
3. treating a fixed lexicographic selector as sufficient evidence that a
   result is robust to equilibrium selection.

Every benchmark must state the intervention, what remains endogenous, what is
held fixed, the comparison object, and the interpretation of a failure. If the
evidence does not support a clean pre-G1 framing, the correct outcome is an
honest `revise_framing`-type disposition, not a false `ready_for_g1`.

### 6.3 Reader-transfer gate

An economist-facing one-page memo or equivalent G1-facing artifact must avoid
workflow jargon such as schema, route, entity, packet, and system internals.
Without consulting machine artifacts, a cold theory reader must be able to
recover accurately:

- the economic puzzle and why it matters;
- the opposing economic forces or mechanism archetypes;
- a three-link causal explanation;
- a minimal example or state comparison;
- a falsifiable kill condition; and
- the economic role of every benchmark.

The audit records concrete substantive edits still required, rather than only
assigning a style score.

## 7. Diagnostic comparison targets

After the V5 output is frozen, an independent paired audit may compare it with
the pre-V5 pilot. The following are exploratory targets, not promotion claims:

- holistic quality at least 7.5/10;
- economist-facing readability at least 7/10;
- abstraction severity at most 4/10; and
- expert substantive-editing burden at most 4/10.

Zero critical economics errors is mandatory regardless of these scores. The
paired audit must distinguish improvements caused by V5 workflow artifacts
from mere wording variation or evaluator preference.

## 8. Decision rule

- **Pass:** the machine, economics, and reader-transfer gates all pass. Proceed
  to close the remaining local Phase 5A research-ready evidence gap.
- **Scientific revise:** the engine behaves safely but one or more economics or
  reader-transfer criteria fail. Make only the smallest failure-driven V5
  change, then rerun this frozen case in a new clean root.
- **Protocol/engine fail:** isolation, route ownership, canonical commit, or
  exactly-once behavior fails. Repair that defect before interpreting prose or
  economics scores.

