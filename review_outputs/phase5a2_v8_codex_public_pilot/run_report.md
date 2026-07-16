# V8 public Codex pilot run report

Status: **closed after the audit route exhausted its declared repairs; no G1
decision occurred**

## Treatment identity

- engine baseline: `45a540ba06591055fef4f7e543f1a8eafdf4681e`;
- wheel SHA-256:
  `dad56a86b8863ca63cf7bae3b37da5bcacabeee66cf99c1ea5ad71f7a9f3854d`;
- Route Registry V8:
  `5d2c2efdef205ee1ff188249dcb05cb5a4430d36ef754a93bde402a092aa40c1`;
- `audit.framing_economics.v8` instruction SHA-256:
  `1f5dd361a0d8ac0c117cc587c541d5dc3e750c38ed0ba1d7e172432b10b971f0`;
- model observation: the host request recorded `selected_model=gpt-5`, and the
  user described the selected tier as ordinary/medium; the actual provider and
  backend model identity were not independently observable.

The frozen inputs and visibility boundary remain in
[`preflight_manifest.md`](preflight_manifest.md). This report records later
execution and does not alter that pre-generation manifest.

## Route outcomes

| Route | Machine result | Canonical result |
|---|---|---|
| `frame.question_and_benchmarks` | completed | committed as `a1970a85024b26b3776d91a3c554d19faa9e4accd9ea1a69c2a1f6d6a8ec0769` |
| `decompose.primitives` | completed | committed as `8a7e73a78794e6c729d105f41639ac4038ad283e66d38d89dfd34301f3aeaa16` |
| `audit.framing_economics` | repair budget exhausted | no audit transaction committed; head remained `8a7e73a...` |

The audit run was
`run_op_29e4aa557e4823cded54a6c32ef447aaef93376147ad78cb`, with WorkPacket
`2cf95a3439d4104784985c4549392580bd807889096f6441fcab1908e4878a72`
and delivery envelope
`b924f54af536fe820147f06bb1f81739ccfbfa3eac7bd389be6e59b6f2973ed3`.
The candidate honestly proposed `revise_framing` and disclosed that the exact
PrimitiveGraph lacked a connected payoff comparison. No payoff witness, human
G1 approval, or G1-ready claim was fabricated.

## Candidate attempts

1. Initial engine-normalized archived candidate
   `2b944a3902da18db5fe448046b0be217e8708c22cd8d803dd48827ac57585078`
   was rejected for two model-level fields: a `causal_channel` retained
   `countervailing_logic`, and one unresolved distinctive-mechanism row omitted
   its exact contrast benchmark.
2. The next source failed strict JSON parsing at line 1, column 1. The agent
   reported a UTF-8 BOM, but that raw source was overwritten and was not frozen;
   the preserved evidence proves a leading parse failure, not the exact bytes.
3. Final engine-normalized archived candidate
   `3bcd35c30dff9742d50b80e0000ee6dd21d0642e2b766cc3d4f1ce6888c65643`
   repaired the two first-attempt fields but was rejected by
   `causal_force_binding`.

Post-pilot read-only replay against the exact final candidate localizes three
primitive-path defects that the original response did not enumerate:

- step 1, `n_k -> n_certification_policy`, cites `force_stock`, whose declared
  source-margin-target geometry is
  `n_consumable_stock -> n_inspection -> n_outcomes`;
- step 1 ends at `n_certification_policy`, while step 2 starts at
  `n_consumable_stock`;
- step 2 ends at `n_uncertified_pool`, while step 3 starts at `n_inspection`.

The validator therefore rejected a real semantic inconsistency. The contract
usability defect was that it returned only the first generic rule message with
empty `details`, after the source-encoding failure had consumed one of the two
declared repair opportunities.

## Finish semantics

The first `finish` request used a warning value outside the bounded opaque-token
grammar and was rejected without a head change. The corrected request used
`candidate_repair_exhausted` and recorded `failed_terminal` as an operational
host receipt. Its completion result was `recorded_failure`, its transaction
digest was null, and `head_before == head_after == 8a7e73a...`.

This is durable operational evidence of a host-session termination. It is not
a canonical scientific transaction, does not rewrite the immutable RouteRun,
and must not be described as a canonical route termination or audit commit.

## Evaluation conclusion

- machine completion: frame pass; decomposition pass; audit fail;
- scientific disposition: the negative diagnosis is inspectable candidate
  evidence only, not an accepted FramingQualityBundle or replacement dossier;
- human authority: no G1 decision was requested, triggered, or confirmed;
- research-quality and effort claims: not established.

The host-stabilization changes described in
[`stabilization_gate.md`](stabilization_gate.md) were written after this run.
The original pilot did not exercise them.
