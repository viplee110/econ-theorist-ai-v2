# V8 public Codex negative-diagnosis pilot protocol

Status: **frozen before generation; no generator or bridge invocation has occurred**

## Purpose and claim boundary

This is a bounded, fresh, public diagnostic of the V8 framing-quality exit.
V8 preserves every positive active-margin, consequence-binding, and human-G1
requirement. It adds only one narrow exit: when the exact upstream
`PrimitiveGraph` makes a connected payoff comparison unavailable, a fully
downgraded `revise_framing` bundle may commit without inventing a witness.

The pilot uses the same public consumable-quality-certificates seed as the
recorded V5.3--V5.5 diagnostics. It asks whether a fresh generator can either
produce a supported framing path or honestly record the failed causal link and
route an exact upstream repair. It is not a comparison of model tiers, a claim
that V8 improves on V5.x, proof of lower human effort, a G1 decision, or a
claim of paper readiness.

## Frozen implementation treatment

- engine commit: `45a540ba06591055fef4f7e543f1a8eafdf4681e`;
- execution branch: `agent/research-first-audit-repair`;
- active Route Registry V8 canonical digest:
  `5d2c2efdef205ee1ff188249dcb05cb5a4430d36ef754a93bde402a092aa40c1`;
- active Navigation Registry V7 canonical digest:
  `ea133669cd85c073b6352744f2d1b5413dfe33d738752ad17769637acfd9e510`;
- `audit.framing_economics.v8` instruction SHA-256:
  `1f5dd361a0d8ac0c117cc587c541d5dc3e750c38ed0ba1d7e172432b10b971f0`.

The preflight manifest will add the wheel digest, clean-root inventory, exact
generator-case digest, skill digest, capture-helper digest, Python version,
and installed-wheel `doctor` output. Any change to the engine bytes, wheel,
generator case, or clean-root inputs invalidates this protocol freeze.

## Generator isolation

The generator runs in a new Codex task with no inherited conversation history.
Its selected root is a newly created, non-cloud test directory outside this
source checkout. The generator may see only:

- the installed wheel and its virtual environment;
- the project skill;
- `CASE.md`, copied byte-for-byte from `generator_case.md`;
- `capture_codex_invocation.py`;
- an empty `.host-state` parent and an empty `run` directory.

It may not read the source checkout, repository history, tests, fixtures, old
pilots, audit reports, candidates, this protocol, the evaluation key,
literature, the web, parent or sibling directories, or another agent's
context. It may not spawn subagents. The protocol, evaluation key, and later
audits remain outside the clean root until generation has frozen.

## Generator and route discipline

Use the researcher-selected ordinary/economy-tier model. Record the exact
observable model identity and reasoning setting when the host exposes them. If
the identity cannot be observed, record `user-selected ordinary/economy-tier;
exact model identity unavailable`; the run is then an independent diagnostic,
not a controlled cross-model comparison.

The initial bridge request supplies `requested_scope` and `framing_intent`
once. Every later continuation omits them. The engine alone selects routes.
The expected pre-G1 sequence is:

```text
frame.question_and_benchmarks
-> decompose.primitives
-> audit.framing_economics
-> one ordinary continuation, only after an audit commit
```

The generator completes only the currently authorized route. It may submit an
initial candidate and at most two sequential repairs when the bridge returns
structured validation diagnostics. It must invoke every request through
`capture_codex_invocation.py`, retain request/response/candidate/timing files,
and stop before a human G1 decision. It may use `finish` only after exhausted
declared retries, explicit cancellation, or an abnormal host/model abort.

After generation freezes, replay the final successful completion request (or a
legitimate terminal finish request) with the exact original bytes. The replay
must not create another transaction, operation, or head advance.

## Directed V8 checks

The machine audit records these separately from economics quality:

1. If the audit's exact upstream graph cannot legally support a connected
   payoff witness, the candidate may leave all witnesses absent only with
   `proposed_action=revise_framing`, a causal-attribution or reoptimization
   gap, and exact current `ResearchQuestion`, `BenchmarkSet`, or
   `PrimitiveGraph` repair targets.
2. That bundle must make no active-response, aggregate-fixed, clean
   attribution, or distinctive-mechanism claim; it must not become
   `ready_for_g1`, and no G1 action may be recorded.
3. Any witness that the generator does supply remains subject to the ordinary
   payoff and consequence-binding checks. V8 must not validate fabricated,
   zero-state, off-path, or payoff-detached evidence.
4. A successful negative audit must canonical-commit, and the ordinary
   continuation must expose the engine-selected upstream repair or a human
   wait. A normal pause is not a terminal `finish` event.

If the fresh generator instead derives and binds a genuine active margin, the
run can still be a valid framing pilot but the V8-specific unwitnessed exit is
reported as **not exercised**, not as passed.

## Evidence and outcome separation

Retain the protocol, manifest, frozen evaluation key, generator input and
input hashes, exact bridge captures, WorkPackets, candidate contracts, raw
candidates, diagnostics, canonical heads, exact replay, and observable host
facts. Do not retain credentials, unrelated host state, or private material.

The final evidence records four independent conclusions:

- **M:** machine protocol and canonical commit/replay behavior;
- **A:** economic diagnosis quality under the frozen key;
- **O:** current object disposition (`REVISE`, `KILL`, or exceptionally
  `READY`); and
- **R/H:** whether a cold reader can recover the failed link and the remaining
  human reconstruction burden.

An M-pass negative commit is not an economics pass by itself, and an
economically useful `REVISE` result is not G1 readiness.
