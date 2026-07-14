# Generator report

## Actual route and outcome sequence

1. `001_start_request.json` -> pre-route `PermissionError`, `mutated: false`, no WorkPacket.
2. `002_start_request.json` -> pre-route `PermissionError`, `mutated: false`, no WorkPacket.
3. `003_start_request.json` with minimum escalation -> `ready`, `mutated: true`; engine selected `frame.question_and_benchmarks` (`run_op_a97cf34e8051072040e29a4dfaefa823b9e2cf4feb6a181f`).
4. Incidental `004_resume_request.json` replay occurred while the same route was open; its evidence patch failed atomically and its response was not retained. `005_resume_request.json` was authored but never invoked.
5. `006_complete_request_attempt_01.json` -> `CandidateValidationError`, `mutated: false`.
6. `007_complete_request_attempt_02.json` -> `committed`, `mutated: true`; head and transaction digest `6b18331c84b54476d9dbdaa4043f46cfb90617a7a27386f3bfb387f49cddbeeb`.
7. `008_continuation_request.json` -> `invalid_codex_bridge_request (start_or_resume:value_error)`, `mutated: false`, no WorkPacket; the host request incorrectly supplied `requested_scope` without `framing_intent`.
8. `009_continuation_request.json` corrected that host-only pairing error -> `ready`, `mutated: true`; engine selected `decompose.primitives` (`run_op_68423a4d7024d0ee62098c0c00c7129d9453797ccea331d8`).
9. `010_complete_request_route02_attempt_01.json` -> `CandidateValidationError`, `mutated: false`.
10. `011_complete_request_route02_attempt_02.json` -> `committed`, `mutated: true`; head and transaction digest `0304ecab3bb55c37c709fa4b2cc6ef9f311b67e8640fd175af7ec304dda8185c`.
11. `012_continuation_request.json` -> `ready`, `mutated: true`; engine selected a distinct `decompose.primitives` refinement run (`run_op_1a10179e2cef7787f88aa597c2be167adcee26514fbbaad5`).
12. `013_complete_request_route03_attempt_01.json` -> strict `changed_facets` validation error, `mutated: false`.
13. `014_complete_request_route03_attempt_02.json` -> `ChangedFacetError`, `mutated: false`.
14. `015_complete_request_route03_attempt_03.json` -> `committed`, `mutated: true`; head and transaction digest `d2af9d75342625ac8cc9cb2c0844e35d23679b4a2eb8c7fad48a94a1fec3b514`.
15. `016_continuation_request.json` -> `ready`, `mutated: true`; engine opened a third `decompose.primitives` run (`run_op_27eae34430c5945ec59642c3a9a4b3561ae135412ae692e3`). No candidate or completion request followed.

## Attempts per route

- `frame.question_and_benchmarks`: 2 candidate attempts. Attempt 1 was rejected because one relation endpoint did not resolve to the exact ResearchQuestion. Repair 1 changed only the `frames` endpoint/reference; attempt 2 committed. No second repair was used.
- `decompose.primitives` run `run_op_68423a4d7024d0ee62098c0c00c7129d9453797ccea331d8`: 2 candidate attempts. Attempt 1 had the `decomposes` relation reversed; repair 1 changed only its direction/reference and attempt 2 committed.
- `decompose.primitives` run `run_op_1a10179e2cef7787f88aa597c2be167adcee26514fbbaad5`: 3 candidate attempts. Attempt 1 omitted the required superseding-entity facet declaration; repair 1 declared `economic_interpretation`; attempt 2 identified the additional exact `terminology_presentation` diff; repair 2 added it and attempt 3 committed.
- Repeated `decompose.primitives` run `run_op_27eae34430c5945ec59642c3a9a4b3561ae135412ae692e3`: 0 candidate attempts and 0 completion requests.

## Terminal condition

- Stopped on a protocol/engine navigation failure before `audit.framing_economics`. At head `d2af9d75...`, the audit route had a valid lineage candidate but required 10,226 `etai_lexical_v1` context units, above the frozen 10,000-unit request. The alternative old-dossier focus failed exact lineage matching, so navigation excluded the audit and left `decompose.primitives` as the sole repeating route.
- The frozen budget was not raised. Route run `run_op_27eae34430c5945ec59642c3a9a4b3561ae135412ae692e3` was preserved as opened by 016, but no candidate or completion followed. No human G1 decision was fabricated or inferred.

## Preserved evidence

- Request schema: `000_request_schema.json`.
- Start evidence: `001_start_request.json`, `001_start_response.raw.json`, `002_start_request.json`, `002_start_response.raw.json`, `003_start_request.json`, `003_start_response.raw.json`.
- Incidental/unused replay requests: `004_resume_request.json`, `005_resume_request.json`.
- Route 1 completion evidence: `006_complete_request_attempt_01.json`, `006_complete_response_attempt_01.raw.json`, `006_complete_timing_attempt_01.json`, `007_complete_request_attempt_02.json`, `007_complete_response_attempt_02.raw.json`, `007_complete_timing_attempt_02.json`.
- Continuation evidence: `008_continuation_request.json` plus response/capture/timing; `009_continuation_request.json` plus response/capture/timing; `012_continuation_request.json` plus response/capture/timing; and `016_continuation_request.json` plus response/capture/timing.
- Route 2 completion evidence: `010_complete_request_route02_attempt_01.json` plus response/timing and `011_complete_request_route02_attempt_02.json` plus response/timing.
- Route 3 completion evidence: `013_complete_request_route03_attempt_01.json`, `014_complete_request_route03_attempt_02.json`, and `015_complete_request_route03_attempt_03.json`, each with its raw response and timing file.
- Structured repair diagnostics: `route01_attempt01_repair_diagnostics.json`, `route02_attempt01_repair_diagnostics.json`, `route03_attempt01_repair_diagnostics.json`, and `route03_attempt02_repair_diagnostics.json`.
- Route 1 candidate attempts: `.econ-theorist/operational/v1/runs/run_op_a97cf34e8051072040e29a4dfaefa823b9e2cf4feb6a181f/shadow/evidence/attempt_01_candidate.json` and `attempt_02_candidate.json`; declared candidate under that run's staging path.
- Route 2 candidate attempts: `.econ-theorist/operational/v1/runs/run_op_68423a4d7024d0ee62098c0c00c7129d9453797ccea331d8/shadow/evidence/attempt_01_candidate.json` and `attempt_02_candidate.json`; declared candidate under that run's staging path.
- Route 3 candidate attempts: `.econ-theorist/operational/v1/runs/run_op_1a10179e2cef7787f88aa597c2be167adcee26514fbbaad5/shadow/evidence/attempt_01_candidate.json`, `attempt_02_candidate.json`, and `attempt_03_candidate.json`; declared candidate under that run's staging path.
- Terminal host audit note: `terminal_navigation_diagnostic.json`.
- Observable timing: `timing_log.md` and the invocation-specific timing files above.

## Limitations

- The host tool inserted a middle-truncation marker into `003_start_response.raw.json`; the file therefore is not byte-exact even though the canonical ready response and WorkPacket were delivered and the packet-bound candidate was accepted by the engine.
- The 004 replay response was lost when its evidence patch failed atomically; no project mutation was inferred from it.
- `005_resume_request.json` is preserved but was never sent.
- Two initial non-state CLI discovery calls (`--help` and the first `--schema request`) occurred before the mandated `LOCALAPPDATA` assignment; the schema was then rerun with the exact assignment. Every project workflow request used the exact isolated `LOCALAPPDATA`; all workflow invocations from 003 onward used `require_escalated`.
- The terminal 10,226-versus-10,000 navigation diagnosis came from a read-only host enumeration, not from a new canonical `codex invoke` response; `terminal_navigation_diagnostic.json` labels that provenance. The exact 016 response independently preserves the repeated route that triggered the audit.
- No baseline, reference answer, web source, repository source, test, fixture, sibling, parent scientific context, or literature material was read. The host supplied only mechanical request/navigation facts.
