# V5.4 research-quality diagnostic

Status: **scientific revise; no architecture rewrite required**

This report evaluates the two frozen off-protocol diagnostics that followed the
official model-identity gate:

- D1: one fresh run by the then-current Codex session;
- D2: one fresh replication with the researcher-selected economy-tier model.

Neither run identifies an exact public model slug, so neither is the official
`gpt-5.3-codex` treatment contemplated by the primary protocol. D1 is used for
economics diagnosis. D2 is used only for model-tier and contract-usability
diagnosis. No cross-model quality ranking is claimed.

## Bottom line

D1 made real progress and the engine did not canonically accept its invalid
audit. The generated economics nevertheless missed the decisive statewise
dominance result: under its own locked-service interpretation, a visible
certificate yields buyer payoff one, whereas inspecting an uncertified seller
yields at most `1-c`. Inspection is therefore strictly dominated whenever any
certificate is visible. The zero-certificate inspection witness is valid, but
there is then no certificate to deplete.

The object can be revised rather than killed. A narrower mechanism may run from
issuance and mechanically forced depletion to the frequency and composition of
future zero-certificate states, and from those states to inspection. That is a
one-way state-distribution channel unless an additional strategic link is
derived. It is not the direct inspection-to-depletion feedback stated in parts
of the primitive graph and audit draft.

D2 failed much earlier for a different reason. Its economic content repeatedly
used the exact ResearchQuestion and BenchmarkSet, but the candidate contract did
not tell the model that WorkPacket focus refs must be copied to top-level
`Transaction.evidence_refs`. The model placed them in fields that the route
entry validator does not read. This is a small contract-usability defect, not a
reason to add another workflow or security layer.

## Independent dimensions

### M — machine execution and protocol

**D1 adjudication: M-PASS, with an inconclusive runtime-materialization
subcheck.** Route selection, budgets, isolation, retry counting, human
authority, terminal finish, unchanged canonical head, and exact terminal replay
behaved as frozen. Three audit candidates were rejected and no invalid bundle
became canonical. Because no audit candidate committed, the intended live
runtime-null materialization path was not exercised.

An independent economics evaluator used the stricter label M-FAIL because no
canonical audit was produced. This report preserves that dissent but applies the
frozen protocol's machine rule: honest terminal rejection after the declared
repair budget is machine-correct; the scientific content remains diagnostic.

**D2 diagnostic: contract-usability failure.** Navigation and validation were
correct, but the public sole-authority contract omitted a critical mechanical
mapping and returned an empty structured diagnostic detail object. That defect
made a cheaper model spend all repairs moving the same exact refs among the
wrong fields.

### A — quality of the economics audit

**A-FAIL.** The audit correctly identified several important issues:

- local activity does not establish equilibrium-path reachability;
- a fixed pointwise inspection rule does not fix aggregate inspection when
  state weights change;
- a fixed selector is a convention, not selection robustness;
- the frozen-policy row is an accounting placebo, not a mechanism control;
- certificate semantics, invariant-distribution treatment, and the no-price
  scope remain human-owned or unresolved.

It did not identify the sharper dominance and state-compatibility defect. It
called a positive-stock-to-belief-to-inspection path active even though
inspection is inactive whenever positive locked-service stock is visible. Its
two valid local witnesses live in disjoint post-issuance states and do not by
themselves close a feedback loop.

Frozen-key scores for D1 are:

| Item | Score | Reason |
|---|---:|---|
| E1 certificate semantics and payoff envelope | 0 | Semantics are explicit, but one- and two-certificate action envelopes are omitted, hiding dominance. |
| E2 nature of depletion | 1 | Mechanical depletion is partly recognized, but positive-stock trade is not derived as forced and is mixed with buyer feedback language. |
| E3 real stock/depletion spine | 1 | Useful local transitions exist, but no closed common-path stock law links them to the claimed inspection response. |
| E4 benchmark meaning | 2 | Pointwise/aggregate, selector/robustness, flow/full, and accounting-placebo distinctions are handled well. |
| E5 falsification and disposition | 1 | Revision is honest, but dominance and failure of the conditional composition link are missing from the kill/rewrite conditions. |
| E6 intuition and naturalness | 1 | The memo is clear and retellable, but transfers an overstated mechanism. |

### O — current research-object status

**O-REVISE.** The intended question still has credible branches:

1. retain guaranteed service and rewrite around forced depletion plus the
   frequency/composition of reachable zero-stock states;
2. define certification as information rather than a locked service, then
   rederive every certified-option payoff and transition;
3. add an economically natural buyer-facing tradeoff upstream and prove a
   nonempty positive-stock inspection region.

The audit may not add branch 2 or 3 in one sentence merely to save a failed
downstream mechanism. The human should choose the institution first.

### R/H — reader transfer and human burden

**R-FAIL; H3 for the guaranteed-service revision, H4 if the literal feedback
loop is indispensable.** A cold reader initially found D1 persuasive and rated
it H2. Only after an explicit positive-stock action-envelope probe did the
reader recover the dominance result and recognize that the two local witnesses
occupy disjoint states. That miss is direct evidence that fluent structure and
internal terminology can conceal the central economic defect.

The guaranteed-service branch is not a total restart: the seller threshold,
zero-stock inspection inequality, benchmark ledger, and aggregate-weighting
distinction remain useful. But the researcher must still discover dominance,
replace the false feedback edge, supply the stock/state law, and re-audit the
mechanism narrative. A branch that insists on buyer-choice-mediated depletion
requires a new primitive and a deeper remodel.

## D2 exact mechanical diagnosis

All three primitive-decomposition candidates had empty top-level
`evidence_refs`. Attempts two and three copied the exact inputs into
`preconditions`, and attempt three also put them in route-outcome
`candidate_refs`; neither field supplies route-entry evidence. The next latent
errors were also mechanical:

- route-outcome `candidate_refs` included pre-existing inputs instead of only
  transaction-produced objects;
- `decomposes` was reversed, with the PrimitiveGraph as source rather than
  target.

The canonical head did not change, the three candidate attempts were preserved,
the corrected terminal finish recorded `failed_no_effect`, and the terminal
replay was byte-identical. The validator was right to reject the transactions;
the authoring interface was wrong to leave these deterministic bindings for a
language model to infer.

## Minimal repair decision

No Phase 0-4 rewrite and no new enterprise control layer is warranted.

The next research-first iteration should do only three things:

1. **Economics:** require the audit to compare the complete action envelope in
   every public-state class used by the claimed downstream path; distinguish a
   mechanical transition, one-way distributional reweighting, and a closed
   behavioral feedback; require an explicit stock/state law at framing
   precision.
2. **Mechanical authoring:** bind exact route inputs to `evidence_refs`, project
   non-ambiguous relation endpoints, and return JSON-path-specific repair
   diagnostics. The model should spend tokens on economics, not copying refs.
3. **Reader transfer:** surface a short economist-facing diagnostic that states
   the mechanism, the failed link, the surviving branch, and the next human
   choice. Internal route and schema vocabulary should remain behind it.

The first two are required before another blind research-quality pilot. The
third should be implemented at the smallest existing rendering/integration
point; it may be deferred if it would create a new subsystem.

## Claim boundary

This one case establishes neither Top-5 readiness nor a causal ranking of model
tiers. It does establish two actionable facts: the current audit can still hide
a central economic contradiction behind plausible structure, and the current
candidate contract spends too much weaker-model capacity on deterministic
serialization details. Both defects can be addressed locally.
