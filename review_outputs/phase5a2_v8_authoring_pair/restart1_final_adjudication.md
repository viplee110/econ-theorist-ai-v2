# Restart 1 final paired-authoring adjudication

Status: **`NO_CLEAR_SURFACE_SIGNAL`**. The semantic compiler prototype shows a
large directional reduction in manual structure, with no scientific or reader
degradation, but it did not reach unchanged V8 validity within three attempts.
The preregistered `COMPILER_FEASIBILITY_SIGNAL` is therefore not met.

This pair does not justify V9, does not weaken V8, and does not yet justify
making the semantic surface the public bridge authoring path.

## Evidence binding and isolation

- Engine commit: `1d9a2e9e2c086a821e168ba50a235459d121734b`
- Wheel SHA-256:
  `5db9c8975bff320ee4be0797b3727f13e1637b063e24b4761b9005161d2f09db`
- PRE manifest SHA-256:
  `df63df0ad255eb0b149e1008ccc5d0d6dd2c45ab4e36e13f3cac5ce3ef64974a`
- Semantic arm manifest SHA-256:
  `952b994104acbe00f5d688d1faef6ebc776e278733016c13a84bc86c098c52f7`
- Transaction arm manifest SHA-256:
  `75a20c9a083a8649553e189a36c9a21c30a4c8588575c552f25ca10a0dd77fa4`
- Semantic report SHA-256:
  `01a4b583d8d8c34150ed759c19f1a56fe6d69d5be47909b001202fc0463fe67c`
- Transaction report SHA-256:
  `5bcde091edef2a57d65bfa22f85ba7a7e18cfda76dbff0b4cf32558b998db5e7`
- Phase-1 lock SHA-256:
  `c13bfdf4a4f1ee460869a9925615a33d169a4865afcb817b7fa7a12421496327`
- Cold-reader evidence SHA-256:
  `e02982165b52e5aca08ca96902473730a2ffd623f7fb9d6d330addfbc61b0163`

The original pair under `etai-v8-pair-ecc1853` remains ineligible because one
Codex task executed both arms. Restart 1 used two independent user-created
tasks in the frozen order. Both requested the same ordinary/medium model; the
actual backend/provider was not independently observable. Every frozen input
hash remained intact. Canonical head was unchanged, canonical writes were
zero, and no human gate was confirmed.

## Preregistered measures

| Measure | Semantic | Transaction |
| --- | ---: | ---: |
| Strict parse on attempts 1/2/3 | yes / yes / yes | yes / yes / yes |
| Surface compile/preflight | fail / fail / fail | not applicable |
| Unchanged V8 pass | no / no / no | no / no / no |
| Experimental repairs submitted | 2 | 2 |
| Runner source bytes by attempt | 14,201 / 10,801 / 10,803 | 21,496 / 21,488 / 23,187 |
| Runner source bytes, total | 35,805 | 66,171 |
| Canonicalized source bytes, total | 34,210 | 56,539 |
| Final JSON leaf fields | 187 | 422 |
| Frozen harness elapsed time, total | 85 ms | 527 ms |
| Final economics rubric | 9/10 | 9/10 |
| Submitted action | `REVISE` | `READY` |
| Adjudicated artifact action | `REVISE` | `REVISE` |
| Underlying scientific-content disposition | `READY` | `REVISE` |
| Cold-reader result | `R-PARTIAL` / H2 | `R-PARTIAL` / H2 |
| Canonical writes / human gates | 0 / 0 | 0 / 0 |

Relative to Transaction, Semantic reduced total runner source bytes by 45.89%,
total canonicalized source bytes by 39.49%, final source bytes by 53.42%, and
final leaf fields by 55.69%. These are real structural-burden signals. The
elapsed values measure frozen harness execution only, not model thinking time
or human effort, and must not be treated as latency evidence.

Repair diffs also show different burdens. Semantic changed 78 leaf pointers
after its first diagnostic and only two after its second. Transaction changed
two status pointers after its first diagnostic, then added 25 active-witness
leaf fields after its second. Neither arm reached a passing candidate.

## Locked scientific result

The phase-1 lock scores both arms `9/10` with no zero item. Both recover
`-1/3`, `+1/3`, fixed-strategy provision `1/3`, and equilibrium provision `0`
versus `1/3`; both identify the initiator's initial participation as the true
response and keep the follower strategy unchanged.

Semantic does not enumerate every held-fixed assumption and its final
`revise_framing` action treats an intentionally excluded welfare boundary as
though it were an unresolved repairable gap. Its substantive economics is
ready, but the submitted action must be repaired.

Transaction explicitly misclassifies the fixed follower type weights as
`endogenous`. The endogenous object is campaign reachability through initial
participation, not the `1/3, 2/3` type distribution. This is a local scientific
error requiring revision, not a kill condition.

## Validator and interface attribution

### Semantic arm

1. Attempt 1 failed semantic preflight because two active distinctive claims
   lacked a complete public-state binding. The receipt exposed three related
   schema errors.
2. Attempt 2 repaired that structure but kept a scope limitation in
   `disclosed_gaps` while proposing `ready_for_g1`.
3. Attempt 3 changed only the action and rationale to `revise_framing`, but
   supplied no exact typed upstream repair target. The claimed scope boundary
   was not a real upstream defect, so no honest target existed.

An evaluator-only posthoc diagnostic removed the non-gap and restored the
scientifically supported ready action. It passed semantic preflight and
compiled a 21,145-byte Transaction, proving that the compiler-owned wrappers,
refs, paths, relations, hashes, dossier, and outcome were feasible. The
unchanged V8 validator then exposed the next latent issue:
`active_margin_witness_missing`. The model had described the payoff comparison
in prose but had not supplied the exact typed same-state witness. This posthoc
run had zero canonical writes and is diagnostic only; it does not change the
experimental failure.

### Transaction arm

1. Attempt 1 used `interpretation_validity=example_supported` on new entities
   and was correctly rejected for self-asserting validated interpretation.
2. Attempts 2 and 3 changed that status to `hypothesized`, but the bundle facet
   retained the wrong schema ID:
   `econ_theorist.theory/FramingQualityBundle/v1` instead of the exact frozen
   `econ_theorist.framing_quality/FramingQualityBundle/v1`.
3. The frozen surface did explicitly supply the correct ID, so this is a model
   authoring error and the acceptance decision is correct. The validator,
   however, returned only `not a canonical framing-quality envelope`; it did
   not report the failing path or expected and observed IDs. Attempt 3 therefore
   added an unrelated 25-field active witness and repeated the envelope error.

An evaluator-only schema-ID correction exposed eight typed payload errors,
including the wrong `minimal_example.role`, string values where typed `changed`
objects were required in both benchmarks, an empty required
`still_endogenous` ledger, and a `not_claimed` distinctive row that retained a
contrast binding. Aggregate tuple errors were cascading consequences. Again,
this was a zero-write posthoc diagnostic and is not an experimental repair.

### Root-cause classification

The primary cause is **layered structural authoring tax plus non-actionable
diagnostic sequencing**, not weak economics and not an erroneous V8 acceptance
rule.

- The strict scientific gates are defensible: no false candidate should have
  passed.
- The Transaction task was asked to hand-author 422 final leaf fields even
  though more than half were deterministic wrappers or bindings.
- The Semantic compiler successfully removed those deterministic fields, but
  its remaining scientific contract still required a highly structured payoff
  witness that the memo-level reasoning did not automatically populate.
- Both surfaces exposed one layer at a time. Relevant independent errors were
  hidden until earlier wrappers or model validators succeeded, exhausting the
  symmetric two-repair budget.
- The harness classified generic route exceptions as `scientific_validator`
  even when adjudication proved an envelope or payload-schema cause. That
  taxonomy is conservative but misleading for product diagnosis.

## Cold-reader result

Both independent readers recovered the central payment-to-participation-to-
provision mechanism and the no-refund/refund result. Semantic's memo preserved
the exact accounting but did not identify the follower's high/low strategy or
enumerate the fixed assumptions. Transaction's memo preserved the actor and
strategy distinction but did not explain that `1/3` is the fixed high-type
probability or give the fixed-strategy quantities. Each needs one local memo
rewrite, so both receive `R-PARTIAL` / H2. Neither surface is reader-dominated.

## Preregistered conclusion

- `INVALID_SETUP`: **no**. All bindings and private oracle checks passed.
- `COMPILER_FEASIBILITY_SIGNAL`: **no**. Semantic did not pass V8 within three
  attempts.
- `MIXED`: **no**. The mechanical reduction did not degrade economics or
  reader burden.
- `NO_CLEAR_SURFACE_SIGNAL`: **yes**. Neither arm passed, and reader/scientific
  quality is tied, although Semantic has a strong directional burden advantage.

One pair cannot establish research readiness, general quality improvement, or
v2 superiority. It does establish that deterministic compilation is the right
direction, while the current semantic authoring contract and diagnostic stack
are not yet integration-ready.

## Next bounded implementation

Do not create V9 and do not rerun this case. Preserve every V8 acceptance gate.
The next slice is an authoring/diagnostic revision only:

1. Validate the typed payload before route validation on both surfaces and
   return exact JSON pointers, rule IDs, expected values, observed values, and
   the complete set of independent errors in one receipt.
2. Replace the generic canonical-envelope boolean failure with the existing
   precise parser diagnostics, including the exact schema-ID mismatch.
3. Classify envelope, payload schema, wrapper, and scientific failures
   separately instead of treating every route exception as scientific.
4. Make non-blocking scope limits visibly distinct from unresolved
   `disclosed_gaps` in the authoring projection and repair hints; do not relax
   the rule that a genuinely unresolved gap blocks readiness.
5. Keep payoffs and feasible actions model-authored, but let the compiler bind
   their exact graph nodes, edge path, consequence, and public-state structure
   wherever those bindings are deterministic and unambiguous.
6. Add focused diagnostic-aggregation and compiler tests, then use one new
   held-out ordinary-model pair. Integration into the public bridge remains
   blocked until that fresh semantic arm reaches unchanged V8 validity without
   worse economics or reader burden.
