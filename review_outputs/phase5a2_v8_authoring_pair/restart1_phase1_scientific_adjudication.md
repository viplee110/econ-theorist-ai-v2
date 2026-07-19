# Restart 1 phase-1 scientific adjudication

Status: **SCIENTIFIC_CONTENT_LOCKED** before implementation-source, test, or
reference-candidate inspection. This phase scores the two frozen final
FramingQualityBundle payloads only. Machine validity, wrapper correctness,
authored bytes, and interface burden are ineligible here.

This is a scientific-only lock, not a claim of arm-identity blinding: the
evaluator had already seen the surface labels and receipt outcomes. Each item
was nevertheless scored independently against the frozen key, without using a
machine pass or failure as evidence for economic quality.

## Frozen inputs

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| Held-out `CASE.md` | 2,184 | `432e28158c7867a9f2e56ce13c028929d57225511b9edfa03f8889c3a9c63bea` |
| Frozen evaluator key | 2,487 | `c8f1d3c537536db3b42b543ca49a571f242145624879311c0d7c490e6533da5b` |
| Semantic final attempt | 10,803 | `3fdf80fd375de22a3425344981a9468116c864bf672072ec36fb7dcc8aeb2334` |
| Transaction final attempt | 23,190 | `d9dc9780a1b26e076fc79c540d668c6a204d7d051b98a990252e69fa0bd01aca` |

## Locked rubric scores

| Frozen-key item | Semantic | Transaction |
| --- | ---: | ---: |
| 1. Exact accounting | 2 | 2 |
| 2. Mapping versus behavior | 2 | 2 |
| 3. True response margin | 2 | 2 |
| 4. Held-fixed boundary | 1 | 1 |
| 5. Causal and claim discipline | 2 | 2 |
| **Total** | **9/10** | **9/10** |

### Semantic arm

- It states the exact initiator comparisons `-1/3` and `+1/3`, fixed-strategy
  provision `1/3`, and reoptimized provision `0` versus `1/3`.
- It cleanly separates the failed-state payoff mapping from the initiator's
  initial participation response, keeps the follower's high/low rule and type
  weighting fixed, and does not introduce welfare, optimality, novelty, or a
  human G1 decision. It explicitly fixes the follower action, cost, threshold,
  and type distribution, but leaves values, information, timing, and the
  campaign-close rule inside a generic reference to the stated assumptions
  rather than enumerating the full boundary. This reduces item 4 to 1.
- Its final `revise_framing` action is not an honest scientific disposition.
  The only named gap is an intentionally excluded welfare/scope boundary; it
  is neither an unresolved defect in the claimed result nor an exact upstream
  repair target. Earlier attempts had classified the same substantive content
  as ready. The frozen key records action separately, so this mismatch is not
  double-counted against an otherwise complete causal and claim-discipline
  score.

Submitted action: `REVISE`. Scientific-content disposition: `READY`, but the
submitted artifact itself requires revision to restore the supported action.

### Transaction arm

- It also recovers all four exact quantities, identifies the initiator as the
  rule-responsive decision maker, preserves the follower's conditional
  strategy, handles the no-start branch without an arbitrary selector, and
  avoids prohibited claims or fabricated human approval.
- Its sequential assessment incorrectly labels
  `weighting_distribution_status` as `endogenous`. The follower's type weights
  remain fixed at `1/3` and `2/3`; reachability changes because the initiator
  starts, not because the type distribution changes. This exact frozen-key
  trap reduces item 4 to 1.
- The surrounding causal explanation correctly attributes the aggregate
  change to initial participation, so the localized weighting-field error is
  not double-counted under item 5.

Submitted action: `READY`. Scientific-content disposition: `REVISE` to change
the weighting status to fixed and distinguish fixed type weights from
endogenous reachability. It is not a `KILL` result.

## Phase-1 conclusion

Both arms contain strong and substantially correct economics; neither has a
zero rubric item. Their machine failures therefore cannot be interpreted as
evidence that the model failed to understand the case. Scientific score is a
tie, with different localized defects. The interface conclusion remains
unlocked pending validator-envelope attribution, burden measures, and isolated
cold-reader evidence.

An independent read-only scorer restricted to the CASE, frozen key, and two
final candidates returned the same item scores, `9/10` totals, and adjudicated
actions. It did not inspect reports, receipts, interfaces, source, or tests.
