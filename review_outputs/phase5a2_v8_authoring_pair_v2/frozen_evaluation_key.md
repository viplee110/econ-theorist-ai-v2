# Frozen evaluator-only key: accident-liability authoring pair v2

This file is evaluator-only.  It must never be copied into either generator
arm, named in a generator prompt, summarized to a generator, or opened until
both independent arms have stopped.

## Frozen economic facts

- Fixed routine action: payoff is 3 at `L=0` and 1 at `L=4`; accident
  probability is 1/2 under both rules.
- Reoptimization: routine is the strict choice at `L=0`; preventive is the
  strict choice at `L=4`.
- Reoptimized accident probability changes from 1/2 to 0.
- Liability does not mechanically change accident risk under a fixed action.
- The only active decision margin is `maintenance_choice`.
- `maintenance_payoff_basis` is payoff evidence for the two-action comparison,
  not a choice margin.
- The fixed primitives are returns 3 and 2, accident risks 1/2 and 0, the
  binary action set, risk neutrality, accident-contingency, payment timing,
  and enforceability.  The changed primitive is the payment level `L: 0 -> 4`.
- No welfare, optimal-policy, legal, empirical, or novelty conclusion follows.

## Separate scores

Record each dimension separately; do not collapse them into a pass/fail:

1. Machine validity: first-pass validation, final validation, submitted
   repairs, issue taxonomy, source bytes, elapsed time, and zero writes.
2. Structural burden: model-authored wrappers, bindings, identifiers, hashes,
   relations, paths, and active-margin graph bindings.
3. Economics: the four payoff/risk comparisons above, fixed-versus-active
   distinction, exact active margin, and causal spine.
4. Claim discipline: no prohibited extension and no fabricated human G1
   decision.
5. Reader recovery: a cold reader can state the question, both benchmarks,
   the strict switch, the accident consequence, and the scope boundary.

`ready_for_g1` is valid when the exact benchmark separation, strict active
margin, selection statement, and boundaries are complete.  A
`revise_framing` answer is economically honest only if it identifies a
specific real defect, binds it to an exact upstream repair target, and
downgrades the affected claim.  Generic caution is not a substitute for the
available exact comparison.

## Material errors

- claiming the fixed-action accident probability falls;
- reporting the high-liability routine payoff as -1 rather than 1;
- treating liability itself as an endogenous maintenance response;
- holding `maintenance_choice` fixed and reoptimizing it in the same row;
- claiming preventive maintenance has positive residual accident risk;
- using payoff-ledger entries as an active choice witness;
- inferring welfare or optimal liability from private payoff and accident risk;
- treating machine validity as research quality.

## Pair integrity

Compare only outputs generated from the same frozen WorkPacket, Snapshot,
engine wheel, ordinary/medium model class, attempt cap, and scientific case.
The transaction arm and `semantic_v2` arm must run in separate new tasks.  Do
not reveal one arm's output or receipt to the other.  Score both only after
both have naturally stopped.
