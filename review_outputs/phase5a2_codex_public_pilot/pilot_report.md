# Phase 5A.2 public Codex pilot report

## Scope and outcome

A fresh-context Codex task was given [`case.md`](case.md), the installed project
skill, and the bridge responses. Its instructions prohibited source, tests,
fixtures, gold answers, prior pilots, web access, literature targets, and
subagents; its run report recorded no read or use of them. The case was public
and stopped after the first canonical route commit.

The model completed `frame.question_and_benchmarks` in one scientific candidate
attempt with zero structured repair cycles. The bridge validated and committed
that candidate. This establishes one public Codex projection from natural
language through WorkPacket delivery, model authorship, validation, and commit;
it does not establish full-paper quality or the complete Phase 5A
research-ready gate.

## Reproducibility bindings

| Item | Exact value |
|---|---|
| Scientific-run engine commit | `528b943704466c7e7ab2ec39112e5195e01864ee` |
| Scientific-run wheel SHA-256 | `a30a881cb905f7c10c0ac1f3b9b66f9d25281bb6118544addd6011a301306586` |
| Host/model observation | OpenAI Codex, GPT-5 family; exact provider build unavailable |
| Project privacy | `public` |
| Route | `frame.question_and_benchmarks` |
| Route run | `run_op_357299f80dea59a15b799194f8727f32c500408d32bb117e` |
| WorkPacket | `f253bd89ffd59475395af795ea2a06ae19bffcc1a024a9f4405c1269c18c84eb` |
| Delivery envelope | `716908fcec6daa82c0ea1a14f0e0cd82c27bc84fda47825ef87757577f5f5c51` |
| Head before | `29deae00e48c5b36f83937daf4749590030b7939f7aacb57a00f5f03ba2525ac` |
| Candidate, transaction, and head after | `812f925afecb6bc262659ec377404f5ed48a1248167f7ee973e0fb7b8b3b9902` |
| Host receipt | `a830d993cd745f340b3b73c27e9564032be3bd516beaf6c6dc2ca352b85b273f` |

The local absolute root is replaced by `$PILOT_ROOT` in the saved request
projections. The permission-denied response is also a redacted projection; the
ready WorkPacket, reconstructed authoring contract, candidate, and completion
bindings retain their canonical engine hashes.

The original raw ready response was not retained intact and is not included as
accepted evidence. [`initial_work_packet.json`](initial_work_packet.json) is the
exact immutable packet record. The scientific-run wheel deterministically
recompiled [`initial_candidate_authoring_contract.json`](initial_candidate_authoring_contract.json)
at the historical base head; their canonical hashes reproduce the values in
[`initial_ready_summary.json`](initial_ready_summary.json).

## Observed execution

- Start request saved: `2026-07-13T20:04:10Z`.
- Ready state observed: `2026-07-13T20:06:06Z`.
- Candidate saved: `2026-07-13T20:11:58Z`.
- Committed response saved: `2026-07-13T20:12:59Z`.
- Agent report saved: `2026-07-13T20:14:02Z`.
- Scientific candidate attempts: one.
- Structured candidate repairs: zero.
- Human scientific decisions or edits: zero.
- Host permission events: one. The first start was non-mutating because the
  sandbox denied the engine's user-level operational directory; replaying the
  identical saved request with filesystem permission returned the WorkPacket.

The candidate is 18,512 bytes. Roughly six minutes elapsed between the ready
state and candidate creation. This is a diagnostic timing measurement, not a
provider-token measurement.

An exact replay of the completion request returned the same committed result:
the transaction count remained two, the completion-operation count remained
one, and the canonical head did not change.

## Post-commit continuation smoke

The navigation fix was packaged from commit
`56279a91c9599ef282ef23ddeef8dcf7a2367410` in a wheel with SHA-256
`9fffd76853021173e8c92409646990498d7ce7ed70329ef4067c09d61cae8b54`.
Using that wheel against the committed pilot selected the correct next route,
`decompose.primitives`, rather than aborting when an earlier repair probe was
inapplicable.

| Item | Exact value |
|---|---|
| Next run | `run_op_61fea7b6c4da60cd814028101cf17ac0c1997f80a3c631cc` |
| Next WorkPacket | `e6599433ad5f73b5ab2a197b0bef7a7e953490fded670b07bf6c35792f5f60a5` |
| Next authoring contract | `ca0c75dfd334fc20e0cde9b57e32f475362b87d54ec1febc2a2e3f8ba5cee833` |
| Canonical head after opening | `812f925afecb6bc262659ec377404f5ed48a1248167f7ee973e0fb7b8b3b9902` |

The continuation instruction explicitly prohibits confirming G1. No human
gate is pending yet because `decompose.primitives` must first produce the
PrimitiveGraph and decision dossier. A state-summary-backed replay of the exact
continuation request returned the same run; run and transaction counts stayed
at two and the head was unchanged. Opening and delivering this next run mutated
operational state only, not canonical scientific state. The bundle does not
claim byte-for-byte equality of two retained continuation responses.

## Defects exposed and repaired

1. An earlier blind pilot on commit `2b05b14` produced JSON-schema-valid
   relations whose `hard` dependency mode lacked exact facet endpoints. The
   domain model rejected them, but the bridge returned only a generic
   `CompletionError`. Commit `528b943` added typed relation invariants to the
   authoring contract and bounded structured repair diagnostics with code
   `codex_candidate_transaction_invalid`.
2. After the successful framing commit, generic navigation encountered an
   inapplicable `repair.dependency` probe and propagated its `RouteEntryError`
   instead of testing later candidates. Commit `56279a9` made candidate probing
   continue after an individual route rejection and added the continuation
   regression assertion.

## Claim boundary

This evidence covers one preinstalled, public-only Codex framing route. It does
not cover private, restricted, `local_only`, hidden, or sealed model handoff;
first-ever installation from an empty project; Claude Code or Cursor parity;
complete-paper generation; lower human effort; comparative v1/v2 superiority;
Top-5 quality; or publication readiness. The separate model-based diagnostic in
[`quality_audit.md`](quality_audit.md) identifies substantive problems even
though the transaction committed mechanically.
