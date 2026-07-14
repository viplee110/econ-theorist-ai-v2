# Isolated generator report

- Root: `C:\tmp\etai-v5_2-public-pilot-20260715`
- Project: `Consumable Quality Certificates`
- Project ID: `prj_38d64a879d712f6c43bafcf31c88eb223048e36e2c6c8ff2`
- Session: `etai-v5-2-public-pilot-20260715-isolated-generator` / `gpt-5.2`
- Terminal status: stopped on the third candidate for `audit.framing_economics`, after the allowed initial candidate plus two structured repairs. No later bridge invocation, continuation, or human-owned decision was made.

## Route sequence

1. `frame.question_and_benchmarks`
   - Route run: `run_op_df6e11c9049ea9a746a2467c04a4774ecf22f65dfc4c11b2`
   - WorkPacket: `c72ffc7ad547fc0e83e068dc4c4e25de7ad9c1ac7395aa65e329ca61dbbf947f`
   - Candidate attempts: 2
   - Attempt 1: rejected, `mutated=false` — `authority_basis may cite only previously effective Decisions; invalid: frame.question_and_benchmarks`
   - Attempt 2: committed, no diagnostics
   - Head before: `089c1b2fca9c33cfe0bc4370b0290a744a43136cabe632e49c6b3a17b2960229`
   - Head after / candidate digest / transaction digest: `c7cb02412367f82dcfa41ef67da853688353ba0e1aab9a0f13a47188a2743ee7`
   - Host receipt: `87d75d4499a74ba8fb67dcadef048d83f00468d3a013819ec9e361d6106189cf`

2. `decompose.primitives`
   - Route run: `run_op_94a0530b42e272a8d384e92a4d9e88f9aaabe3d150605895`
   - WorkPacket: `3317739c5e03714c8ea50e5fae4e8ef229f095fdb2ff676723a1cd7ba9d87764`
   - Candidate attempts: 2
   - Attempt 1: rejected, `mutated=false` — `Phase 2 route contract rejected the transaction: decomposes relation does not target PrimitiveGraph`
   - Attempt 2: committed, no diagnostics
   - Head before: `c7cb02412367f82dcfa41ef67da853688353ba0e1aab9a0f13a47188a2743ee7`
   - Head after / candidate digest / transaction digest: `f7474b3bdf983d1033afbd38bdb24ca57cdbc9557deed0c9dbd378c28943b6f0`
   - Host receipt: `f13351ec9870f35c4617c6f1058c192135adf90edba0e76817b5c9cef4db555f`

3. `audit.framing_economics`
   - Route run: `run_op_10750bc4052cfad55c10259f2bd109fb941dabcc725eb49f`
   - WorkPacket: `ebe8fa5207f5168d7f08a623e0bf825459aa88f249db3dd1af9e048868539aca`
   - Base head: `f7474b3bdf983d1033afbd38bdb24ca57cdbc9557deed0c9dbd378c28943b6f0`
   - Candidate attempts: 3
   - Attempt 1: rejected, `mutated=false` — `baseline and countervailing forces must act on the same target`
   - Attempt 2: rejected, `mutated=false` — `baseline and countervailing forces must have opposite directions`
   - Attempt 3: rejected, `mutated=false` — `framing bundle requires one audits dependency from every exact input`
   - Terminal disposition: uncommitted route failure; repair limit exhausted.

## Invocation ledger

- Public bridge request invocations: 14, from `2026-07-15T04:03:39.8210792+08:00` through `2026-07-15T04:53:41.0009879+08:00`.
- Interface discovery before requests: `etai codex invoke --help` and `etai codex invoke --schema request`.
- Start invocations 1–3 returned host `PermissionError` diagnostics with `mutated=false`, in order:
  1. `<USERPROFILE>\\.local\\state` after the wrapper's attempted environment assignment failed.
  2. `C:\\tmp\\etai-v5_2-public-pilot-20260715\\.host-localappdata\\EconTheoristAI`.
  3. `C:\\tmp\\etai-v5_2-public-pilot-20260715\\.host-localappdata\\EconTheoristAI\\operational`.
- The required `LOCALAPPDATA=C:\tmp\etai-v5_2-public-pilot-20260715\.host-localappdata` was then propagated successfully; subsequent bridge requests used it.
- Ordinary continuations after committed routes omitted `requested_scope`, `framing_intent`, and `budget_units`.

## Audit preservation note

Exact JSON requests, captured raw stdout/stderr, invocation metadata, full candidate attempts, and structured repair diagnostics are inventoried in `generator_artifacts/evidence_inventory.json`. The successful initial ready response at invocation 4 was transported through a host output channel that truncated its large base64 rendering before it could be archived as raw stdout. That omission is preserved explicitly in `004_start_invocation_meta.json`; the authoritative still-open route packet was captured in full by the immediately following ordinary no-framing resume (`005_resume_stdout.jsonl`). No raw-stdout claim is made for invocation 4.

## Explicit exclusions

- No web, literature, repository checkout, history, tests, fixtures, reference answers, prior outputs, parent/sibling directories, or other-agent scientific context were read or used.
- No subagent was spawned.
- No direct canonical-store write, human-owned artifact overwrite, human G1 decision, approval, or confirmation was made.
- No bridge call or candidate modification occurred after the terminal third audit attempt.
- This report records protocol facts only and does not interpret scientific quality.
