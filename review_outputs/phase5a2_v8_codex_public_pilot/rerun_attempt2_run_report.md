# V8 post-stabilization rerun attempt 2 report

Status: **closed after a diagnosed `failed_no_effect`; framing and primitive
decomposition committed, the framing-economics audit did not commit, and no
human G1 decision occurred**

## Treatment identity

- engine commit:
  `4804323a84829247a88ae2f5e315538a331037fd`;
- wheel: `econ_theorist_ai-0.1.0-py3-none-any.whl`, 702,857 bytes;
- wheel SHA-256:
  `09c620566505acea8e5ab698fff32e56f9197b71d336abbed9c9a419769ce22b`;
- Route Registry V8 canonical digest:
  `5d2c2efdef205ee1ff188249dcb05cb5a4430d36ef754a93bde402a092aa40c1`;
- capture-v2 helper SHA-256:
  `590ef3bdb4bb3e7ba80952108a4c98db8893f0bce3684e69372464967906291d`;
- clean project root: `C:\tmp\etai-v8-r2`;
- model observation: the requests recorded `selected_model=gpt-5`, and the
  user selected an ordinary/medium tier; the actual provider and backend model
  identity were not independently observable.

The exact pre-generation bindings and isolation boundary are recorded in
[`rerun_preflight_manifest.md`](rerun_preflight_manifest.md). R2 used the same
wheel, skill, helper, and CASE bytes as attempt 1, while shortening the
isolated host-state path that caused the attempt-1 Windows path failure. See
[`rerun_attempt1_operational_failure.md`](rerun_attempt1_operational_failure.md).

## Correction and recovery lineage

The generator's first report incorrectly treated two stale blocked captures as
authoritative and omitted the later ready response. Read-only evidence review
identified the valid ready delivery, the preflight-valid candidate already at
the packet-declared path, and the existing completion request. The same blind
task then resumed the same immutable route; it did not send a replacement
`start` request or create a second project.

The authoritative generator record is the corrected report at
`C:\tmp\etai-v8-r2\run\20260717-consumable-quality-certificates-agent-report-corrected.md`,
8,286 bytes, SHA-256
`2e4c1f0fbf1842d24308b9c035fddf7d3fedde3dd2b3502aef96b674fd004a94`.
The earlier report remains preserved as negative reporting evidence and is not
used as the route chronology.

## Route outcomes

| Route | Host attempts | Machine result | Canonical result |
|---|---:|---|---|
| `frame.question_and_benchmarks` | one completion | `committed` | head `73fb8d5bc47f3c21d17228e76edb8300fbc537224bf896f2ebe01a52f57adf1c` |
| `decompose.primitives` | initial plus two repairs | `committed` | head `467a15616763fc5859ca7128893b187599a5e813d1dde8b5b5e968c3d2d60535` |
| `audit.framing_economics` | initial plus two repairs | rejected, then `failed_no_effect` recorded | no audit transaction; head remained `467a156...` |

The frame run was
`run_op_483cba782e815ef662cfc7a90d6127afa28dde3c5c3ac3c2`.
The decompose run was
`run_op_042c42e559702c4f53e3d5f283496220eb63ef0e31f9715e`.
The audit run was
`run_op_c8b18722063c1f734a48b9fd1503e6dd6d728c7fc81f4556`,
with WorkPacket digest
`77b1c685ea7f6ba2e6d1b65fa0e10728515b7d8e30b970d8fbe1e93fee1be81b`.
The WorkPacket remains in the isolated generator root and is not copied into
the independent evaluator package.

The committed head contains the project genesis, one `ResearchQuestion`, one
`BenchmarkSet`, one `PrimitiveGraph`, and one proposal-only `GateDossier`.
There are no effective Decisions and no registered artifacts.

## Audit repair evidence

| Attempt | Exact returned diagnostic | Canonical effect |
|---|---|---|
| initial | a held-fixed object used the unsupported `semantic_level=policy_rule` literal | none |
| repair 1 | the same `PrimitiveGraph` semantic object was both fixed and movable at the same level | none |
| repair 2 | a benchmark channel's declared endpoints did not match its changed and target objects | none |

The final audit source was 41,447 bytes with raw SHA-256
`405d0c38b658309cb2730deb3f8434558c6ce3629e7a84a31f61d26b0071b979`.
Its engine canonical candidate digest was
`733319830ae7c3b2cc9336da37faddcbf8bd540615dcd425c176943ca05b5c6a`.
It proposed `revise_framing`, did not claim a payoff witness or distinctive
mechanism, and did not claim G1 readiness. Because validation failed, neither
its `FramingQualityBundle` nor its replacement dossier became canonical.

## Capture, finish, and authority

Every source-reading completion capture reports a valid bridge response, exact
request binding, unchanged request bytes, unchanged candidate bytes, and no
capture error. The two successful completions also report that the engine
canonical candidate digest matches the committed response.

After the two declared audit repairs were exhausted, `finish` recorded
`failed_no_effect` with warnings `repair_budget_exhausted` and
`candidate_validation_error`. The response was `recorded_failure`, its
transaction digest was null, and
`head_before == head_after == 467a15616763fc5859ca7128893b187599a5e813d1dde8b5b5e968c3d2d60535`.
That mutation is an operational receipt, not a canonical scientific commit.

No packet delivered a pending human gate reference. No model or host confirmed
or fabricated a G1 decision.

## What this run establishes

- The corrected wheel traversed initialization, packet delivery, completion,
  exact continuation, candidate capture, two canonical commits, repair
  diagnostics, and protocol finish without the attempt-1 path failure or a
  new transport/encoding failure.
- The same-case half of the host-stabilization stop rule therefore ended in a
  genuine, specifically diagnosed model-content failure rather than another
  host-integration failure.
- The run does **not** establish a machine-pass audit, economic correctness,
  reader recovery, lower editing burden, research readiness, or permission to
  begin the exploratory v1/v2 comparison.
- The evidence alone does not decide whether the final rejection reflects a
  model mapping error, an unclear diagnostic/authoring surface, an
  overconstrained validator, or a mixture. That judgment is deliberately
  assigned to isolated post-generation evaluation.

The next work is not another regression cycle or an immediate V9. The isolated
cold-reader retell is now frozen with provisional burden H3. Next run the
separate high-intelligence economics adjudication against the unchanged
evaluation key. Only that adjudication may justify a bounded
contract/diagnostic change. The held-out ordinary-model framing run remains the
other half of the stabilization stage.
