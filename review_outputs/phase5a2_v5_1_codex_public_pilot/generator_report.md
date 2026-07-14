# Generator report — Consumable Quality Certificates

## Terminal outcome

The run stopped at a terminal protocol/navigation failure after the engine selected `frame.question_and_benchmarks` three consecutive times under three distinct immutable route-run identifiers. The first two runs committed; the third opened as `ready` even though two complete framing candidates were already canonical. No `decompose.primitives`, `audit.framing_economics`, human G1, or `revise_framing` route/boundary was reached.

The canonical third response itself was `ready` with no diagnostics. The terminal classification is therefore based on the observed no-progress navigation sequence and the supervisory stop instruction, not on an engine-emitted terminal outcome. No route was forced, named, skipped, or reordered.

## Exact route and outcome sequence

1. `frame.question_and_benchmarks`
   - Route run: `run_op_699125ff91cd4beae0569ca26f174e405d58ece6f531565a`
   - Triggering request: `run/007_start.request.json`; invocation `007` timed out with exact empty streams, then the identical request resumed in invocation `008`.
   - Ready response: `run/008_resume_same_start.stdout.json`
   - Work-packet hash: `63359441ef76dad877730598a1c0227029f46fe1d5cbfb04434c9853127c56bd`
   - Delivery-envelope hash: `1eefdfd6cabd37bd7dd68e4941a15849137567b1e4c58f079fdae9f03af6ffc6`
   - Scientific candidate/completion attempt 1: bridge `error`, `CandidateValidationError` because `authority_basis` cited a non-Decision (`run/010_complete_attempt1.stdout.json`).
   - Scientific candidate/completion attempt 2: `committed` (`run/012_complete_attempt2.stdout.json`).
   - Canonical transaction/candidate digest and head after: `f5bfa4ad81a61e3339e31b6b984a3f2130df89a93831a822b22fcf5078dc8f26`.

2. Continuation navigation check (no route opened)
   - Request: `run/013_start_next.request.json`.
   - Outcome: `blocked`, not mutated, because the minimal continuation omitted the immutable run-input brief.
   - This response also recorded `decompose.primitives` as requiring 4,407 `etai_lexical_v1` units while the registry default was 4,000, and `audit.framing_economics` as lacking a candidate focus satisfying registry cardinality.
   - The next request restored the original seed/scope, omitted `budget_units`, and named no route.

3. `frame.question_and_benchmarks` — first automatic repeat
   - Route run: `run_op_acaa89f3d3444b25d963ff8ec936917d6408083be4150a13`
   - Triggering request: `run/014_start_next_with_brief.request.json`
   - Ready response: `run/014_start_next_with_brief.stdout.json`
   - Work-packet hash: `d327256a8ec93c13f707346819cff0ec0b66619d2df63340b98574ee0bbfd79f`
   - Delivery-envelope hash: `dda18aa510aed98e1474875f1c8fb1f747ccbcdde041e50a06fef8e36a805d09`
   - Scientific candidate/completion attempts: 1.
   - Outcome: `committed` (`run/016_complete_repeat_attempt1.stdout.json`).
   - Canonical transaction/candidate digest and head after: `75563ecf65fb8943aaa9abf0f36becd089828d23ce8683136e585ef350cc2253`.

4. `frame.question_and_benchmarks` — second automatic repeat, terminal stop
   - Route run: `run_op_3e47218ad496305bffbd295213b0c3aed3294b553659b27f`
   - Triggering request: `run/017_start_next.request.json`
   - Ready response: `run/017_start_next.stdout.json`
   - Work-packet hash: `566a86097ccd158d8d61a1e0419024b136e942738c988f61a20056fe1dc78f17`
   - Delivery-envelope hash: `1ee0fd87352560a029ed914c74e341e4e14b39d7d12c0fc9109443421e84c0c2`
   - Submitted scientific candidate/completion attempts: 0.
   - Completion requests and completion bridge invocations: 0.
   - State at stop: `ready`; canonical head remained `75563ecf65fb8943aaa9abf0f36becd089828d23ce8683136e585ef350cc2253`.
   - Timing divergence preserved: before the supervisory stop instruction arrived, an unsubmitted draft had already been written at the declared candidate path and copied to `run/018_frame_question_and_benchmarks_repeat2.attempt1.candidate.json`. It was never submitted and is not counted as a scientific candidate/completion attempt. It was left untouched after the stop instruction.

## Attempt and invocation counts

- Scientific candidate/completion attempts by immutable route run: `2`, `1`, `0`.
- Total scientific completion submissions: `3` (one structured validation error, two commits).
- Canonical commits: `2`.
- Unsubmitted drafts outside those attempt counts: `1` on the third route.
- Host capture setup failures before any etai process: `2` (`001`, `002`).
- Total etai process invocations: `12` (`003`, `004`, `005`, `006`, `007`, `008`, `010`, `012`, `013`, `014`, `016`, `017`).
- Public `codex invoke` process invocations, including help/schema: `10` (`003`, `004`, `007`, `008`, `010`, `012`, `013`, `014`, `016`, `017`).
- Request-bearing bridge process invocations: `8` (`007`, `008`, `010`, `012`, `013`, `014`, `016`, `017`). `007` and `008` used the same immutable request file, so there were `7` distinct request JSON files.
- Non-bridge etai diagnostics/help: `2` (`005`, `006`).

## Canonical identifiers

- Project id: `prj_06882e8f7deec6ff5aed75ceb5f04c85f634cab23acdb087`.
- Genesis/base head after initialization: `8ced7fcbb6118559d2c33fde5a334fb358c394731aef035ccd51fa7ceef4cc5e`.
- First committed head: `f5bfa4ad81a61e3339e31b6b984a3f2130df89a93831a822b22fcf5078dc8f26`.
- Second and final canonical head: `75563ecf65fb8943aaa9abf0f36becd089828d23ce8683136e585ef350cc2253`.

## Repetition, budget, and boundaries

- Automatic repeated decomposition: **No.** `decompose.primitives` never opened. The observed divergence was automatic repeated **framing**: the same framing route was selected three times total, twice after a prior framing commit.
- Route-default budgeting: every `start_or_resume` request omitted `budget_units`; ready packets reported the registry-owned 4,000-unit default.
- `audit.framing_economics` admission: **No.** The blocked navigation response reported no candidate focus satisfying registry cardinality. Separately, `decompose.primitives` required 4,407 units and was not enterable at the 4,000-unit default.
- Human G1 boundary: **Not reached.** Ready packets had no pending human gate references; no human decision was made or inferred.
- `revise_framing` boundary: **Not reached.** No such canonical route or outcome occurred.

## Timing

- Sum of captured etai invocation wall times, including the 10.691-second timed-out initialization call: `56,161 ms`.
- Sum for request-bearing bridge calls: `45,485 ms`.
- Clock interval from the first successful etai capture start (`2026-07-14T23:47:33.5169266+08:00`) through the final ready response (`2026-07-15T00:07:43.0617048+08:00`): approximately `1,209,545 ms` (20 minutes 9.545 seconds).
- Each invocation's exact timestamps, exit code, and wall time are in its numbered metadata file. The interrupted `007` call could not emit its internal end timestamp; its exact zero-byte streams, host timeout, and resume are preserved.

## Evidence and limitations

- Exact inventory: `evidence_inventory.md`.
- All requests are ordinary strict JSON created in the selected root; all start requests omit `budget_units`.
- Every raw stdout/stderr stream is preserved with its numbered invocation. Empty stderr files are evidence of empty streams, not missing captures.
- The two initial capture failures occurred before process creation and are preserved separately.
- The terminal navigation classification is supervisory because the third canonical response said `ready`; the engine did not itself emit a terminal failure or human-gate response.
- The unsubmitted third-route draft is a timing divergence, not a committed or submitted scientific attempt.
- No source, tests, fixtures, prior runs, literature, web material, baseline, or reference output was used or compared. No claim of scientific superiority is made.
