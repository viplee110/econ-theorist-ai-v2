# V5.1 public Codex pilot failure report

Status: **protocol/engine failure; scientific output not interpreted**  
Pilot date: 2026-07-14 to 2026-07-15 (Australia/Perth)  
Frozen source commit: `51789a55d5dcbdeb70455f2fcdd3a33502efae92`

## Outcome

The frozen pilot did not reach `decompose.primitives`,
`audit.framing_economics`, a human G1 decision, or `revise_framing`.
Instead, the engine opened `frame.question_and_benchmarks` three times under
three distinct immutable route-run identifiers. The first two route runs
committed. The third returned `ready` and was stopped before any candidate was
submitted.

This is a navigation and default-budget failure. The framing candidates are
retained only as execution evidence. They were not compared, scored, or
interpreted for economics, novelty, readability, or publication quality.

## Observed causal sequence

1. The first `frame.question_and_benchmarks` route opened as
   `run_op_699125ff91cd4beae0569ca26f174e405d58ece6f531565a`. Candidate attempt
   1 failed structured validation because `authority_basis` cited an object
   that was not a Decision. Candidate attempt 2 repaired that diagnostic and
   committed. The resulting head was
   `f5bfa4ad81a61e3339e31b6b984a3f2130df89a93831a822b22fcf5078dc8f26`.
2. The minimal continuation request in `run/013_start_next.request.json`
   intentionally omitted the run-input brief. It returned `blocked` without
   mutation. In the same response:
   - framing was unavailable because it required an immutable run-input brief;
   - `decompose.primitives` required exactly 4,407 `etai_lexical_v1` units,
     while the registry-owned default budget was 4,000; and
   - `audit.framing_economics` had no candidate focus satisfying registry
     cardinality.
3. The continuation in `run/014_start_next_with_brief.request.json` restored
   the original seed and requested scope while still omitting `budget_units`.
   This made framing eligible again. The engine opened a second
   `frame.question_and_benchmarks` route,
   `run_op_acaa89f3d3444b25d963ff8ec936917d6408083be4150a13`, which committed
   on its first candidate attempt. The resulting and final canonical head was
   `75563ecf65fb8943aaa9abf0f36becd089828d23ce8683136e585ef350cc2253`.
4. The next request again supplied the original brief and omitted
   `budget_units`. The engine opened a third
   `frame.question_and_benchmarks` route,
   `run_op_3e47218ad496305bffbd295213b0c3aed3294b553659b27f`, with a canonical
   `ready` response and no diagnostic. The supervisor stopped the pilot before
   submission because the automatic route sequence was making no stage
   progress.

The immediate failure mechanism is therefore exact and bounded: without the
brief, the 4,000-unit default could not admit the 4,407-unit decomposition;
restoring the brief reopened framing instead of advancing beyond the already
committed framing work; the third framing-ready response was stopped before
submission. This report does not infer a deeper code-level cause beyond that
preserved request/response evidence.

## Exact counts

| Measure | Count |
|---|---:|
| Distinct framing route runs opened | 3 |
| Scientific candidate/completion attempts by route run | 2, 1, 0 |
| Completion submissions | 3 |
| Structured validation errors | 1 |
| Canonical commits | 2 |
| Third-route completion requests or invocations | 0 |
| Unsubmitted third-route drafts | 1 |
| `etai` process invocations | 12 |
| Public `codex invoke` process invocations | 10 |
| Request-bearing bridge invocations | 8 |
| Distinct request JSON files used by those invocations | 7 |
| Host-capture failures before process creation | 2 |

The unsubmitted draft was written before the supervisory stop instruction
arrived. It was copied into the evidence directory but never sent to the
completion bridge, never committed, and is not counted as a scientific
candidate/completion attempt.

## Boundaries not reached

- Automatic repeated **decomposition** did not occur; decomposition never
  opened. The observed repetition was framing.
- `audit.framing_economics` did not open.
- No human-owned decision was created, inferred, or recorded.
- No G1 dossier or `revise_framing` outcome was produced.
- Every `start_or_resume` request omitted `budget_units`, as frozen by the
  protocol.

## Archived evidence and exclusions

The repository archive contains:

- `generator_case.md`, a byte-for-byte copy of the generator's `CASE.md`
  (`SHA-256 9B67D683141675F794292A6CF3F046E624E469F17860E0253F6185CD3C864FF2`);
  this name avoids a case-insensitive collision with the distinct pre-existing
  `case.md` protocol input;
- `generator_report.md` and `evidence_inventory.md` copied byte-for-byte;
- all 53 files in `run/` (464,803 bytes), including requests, raw responses,
  empty streams, candidates, and invocation metadata; and
- 32 files (208,875 bytes) under
  `canonical_store/.econ-theorist/`: project metadata, provenance, refs,
  canonical runs, snapshot, staging evidence, transactions, and status view.

Before copying, retained inputs were scanned for common API-key, GitHub-token,
AWS-key, bearer-token, private-key, password, credential, cookie, personal
email, username, and user-profile path signatures. No such signatures were
found in the retained set.

The following were deliberately excluded:

- `.venv/`, `distribution/`, and `.agents/` because the preflight manifest
  already freezes their hashes and they are not run-state evidence;
- `.host-localappdata/` because it is isolated host-operational state;
- `.econ-theorist/operational/` (88 files, 156,314 bytes) because it contains
  host capability/egress bookkeeping rather than canonical scientific state;
  sensitive-field terms found by the scan were confined to this excluded
  operational subtree; and
- `.econ-theorist/locks/`, which contains transient one-byte lock files.

No secret, credential, host environment, or virtual environment was copied.
