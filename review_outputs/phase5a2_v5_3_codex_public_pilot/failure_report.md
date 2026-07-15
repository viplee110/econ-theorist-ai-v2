# V5.3 public Codex pilot failure report

Status: **generator/protocol failure; independent scientific and reader audits
also require substantive revision**

Pilot date: 2026-07-15 (Australia/Perth)

Frozen implementation commit:
`f7f34ef58dbe8af03592db02be617dfc9b403d40`

## Outcome

The fresh installed-wheel pilot traversed the intended research workflow
without route forcing:

1. `frame.question_and_benchmarks` committed on its first candidate;
2. `decompose.primitives` committed on its second candidate after one exact
   relation-direction diagnostic; and
3. `audit.framing_economics` produced one candidate but did not commit.

The canonical head stops after primitive decomposition at
`7575110612a3faff6d5784f1fb2bf34d1a31780d6b761d251a1c353460d7c789`.
No human G1 decision was created, inferred, or recorded.

The terminal generator report calls the audit stop an unavoidable engine
compatibility failure. The independent machine audit shows that attribution is
incorrect. The public contract named an installed callable for computing the
candidate-output facet hash. The generator instead wrote 64 zeroes and called
`finish` after one audit attempt, before the frozen retry allowance was
exhausted. The observed stop is therefore generator misuse plus a protocol
violation.

There is still a real product defect: deterministic engine metadata should not
consume language-model attention or scientific repair attempts. The bridge
should materialize it automatically. That usability repair does not turn the
archived audit candidate into a scientific pass.

## Route and attempt record

| Route | Default budget | Candidate attempts | Result |
|---|---:|---:|---|
| `frame.question_and_benchmarks` | 4,000 | 1 | committed |
| `decompose.primitives` | 8,000 | 2 | committed |
| `audit.framing_economics` | 18,000 | 1 | uncommitted; generator stopped early |

All ten generator-time bridge invocations produced complete, strict JSON
responses bound to the exact canonical request digest. Error responses were
nonmutating. The same open audit route re-delivered the same WorkPacket and
authoring-contract hashes. A post-freeze replay copied the exact terminal
request as invocation 015; both request bytes and response bytes are identical
to invocation 014. Terminal exactly-once behavior therefore passes even though
the generator used `finish` at the wrong time.

## Machine diagnosis

The correct runtime hash for the frozen candidate's complete
`FramingQualityBundle.economic_interpretation` facet is:

`5a0a8163e4f9cd9777da513359052bde50d8ac8e6d5261cf062571f8040f3d0f`

Correcting only that value in memory exposes further validator failures. In
order, the counterfactual candidate still lacks a required choice-dependent
active-margin witness, contains an incompatible semantic-ledger active node,
and records the wrong replacement-dossier condition. None of those
counterfactual adjustments was written, staged, or committed.

This establishes three boundaries:

- the hash was not publicly impossible to compute;
- the hash interface is still badly factored for a natural-language research
  workflow; and
- removing the hash obstruction would not make the candidate route-valid.

## Independent economics verdict

**Scientific revise; economics gate fail.** The audit candidate is
uncommitted and can supply diagnostic evidence only.

The candidate made real progress. It wrote explicit seller and buyer payoff
comparisons, correctly distinguished a fixed pointwise inspection rule from a
fixed aggregate inspection rate, identified missing off-support policy
semantics, treated a fixed selector as a convention rather than robustness,
and rejected a pure mechanical interpretation of the NX benchmark.

It nevertheless missed the central economic defect. Under the committed
ledger, an available certified purchase gives buyer value one, while
inspection can yield at most one and costs `c in (0,1)`. Inspection is thus
strictly dominated whenever a certificate is available. The audit demonstrated
an active inspection margin only in a no-certificate state, where no
certificate can be depleted. It neither added a buyer-facing tradeoff nor
deleted or downgraded the buyer-controlled depletion claim.

The proposed stock mechanism is also not closed. The F and N main paths are
identical:

`k -> certification -> uncertified pool -> inspection return -> inspection -> Q`

Neither path contains certificate stock, trade choice, or depletion. The
minimal example fixes the uncertified-pool belief and merely says that
issuance and depletion may move it. This gives two local payoff margins, not a
derived `k -> stock/depletion -> composition -> search` mechanism.

## Independent reader verdict

**Reader-transfer revise; high human revision burden.**

A cold theory reader can recover the puzzle and retell the two endpoint payoff
comparisons. The decisive middle stock-balance equation is absent, the
certificate-present dominance logic is not confronted, and the four-cell
benchmark differences are not yet causal components. The memo remains an
internal audit artifact rather than a self-contained theory-paper narrative.

The needed work is not copy-editing. It requires a substantive model choice:
either introduce a credible price, matching, or other buyer-facing tradeoff
that activates the relevant choice, or accept mechanical depletion and rewrite
the mechanism around stock occupancy, no-certificate states, and conditional
pool composition. It also requires a solved minimal transition system and a
more structured theorem target than an unrestricted three-point existence
search.

## Research-first repair boundary

This pilot does not justify more enterprise infrastructure, attack hardening,
authorization layers, broad retry machinery, or security work. V2 is a trusted
local research system. The repair budget is limited to work that improves the
economics or removes friction from the scholar's workflow:

1. let the bridge materialize exact runtime-derived hashes before canonical
   candidate identity is computed;
2. make a claimed distinctive mechanism path pass through its distinctive
   primitive or state transition, so a stock channel cannot reuse a flow path;
3. bind every payoff witness to the exact claimed link and relevant public
   state, and test the complete feasible-action envelope there;
4. return precise scientific diagnostics together when possible, rather than
   spending attempts on serial bookkeeping failures; and
5. rerun one fresh blind pilot before any claim that V5.3 lowers human effort
   or passes the framing audit.

After that bounded repair, development should move to question discovery,
model construction, theorem and boundary discovery, economic intuition,
reader-facing writing, and the planned IO/search scholar-distillation work.

## Claim boundary

This pilot shows that the route-based research process can execute through
framing, decomposition, and delivery of an economics audit, while preserving
state and human authority. It does not show that the complete scientific
workflow passes, that the current model has a valid consumable-stock
mechanism, that human revision effort is low, or that the system is ready for
Top-5-quality paper production.

The detailed findings are retained in `machine_protocol_audit.md`,
`economics_audit.md`, and `reader_transfer_audit.md`.
