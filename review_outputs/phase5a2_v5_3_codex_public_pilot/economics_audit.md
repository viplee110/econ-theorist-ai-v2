# Independent Economics Audit of the V5.3 Public Pilot

## Scope and evidence boundary

This is a read-only, independent microeconomic-theory and industrial-organization review of the frozen V5.3 pilot. It uses only the evidence under this pilot directory. It does not use candidates, reports, or reference answers from another version.

The principal evidence is:

- [`protocol.md`](protocol.md), especially the noncompensatory economics gate;
- [`generator_case.md`](generator_case.md), containing the frozen research seed;
- [`run/002_candidate_attempt1.json`](run/002_candidate_attempt1.json), the committed framing candidate;
- [`run/007_candidate_attempt2.json`](run/007_candidate_attempt2.json), the committed primitive decomposition and pre-audit G1 dossier;
- [`run/010_candidate_attempt1.json`](run/010_candidate_attempt1.json), the **uncommitted** economics-audit candidate;
- [`run/011_complete_attempt1_stdout.json`](run/011_complete_attempt1_stdout.json), the audit completion diagnostic;
- [`run/014_finish_engine_compatibility_stdout.json`](run/014_finish_engine_compatibility_stdout.json), the terminal recorded-failure receipt; and
- [`generator_report.md`](generator_report.md), the execution summary.

## Overall judgment

**Decision: Scientific revise. The economics gate fails.**

The terminal route failure and the scientific judgment must be separated. The
public contract named an installed callable that could compute the runtime
semantic hash, but the generator submitted an all-zero value and then called
`finish` after only one audit attempt. The observed stop is therefore generator
misuse plus a retry-protocol violation, not proof that the hash was publicly
unavailable. Requiring a natural-language research agent to manufacture this
purely derived engine metadata remains a high-priority product-UX defect. None
of those machine facts is, by itself, a scientific failure.

The economics gate nevertheless fails on the frozen scientific content. The audit candidate did not confront the protocol's central dominance implication, did not repair the primitive ledger, and did not remove or downgrade the claimed buyer-controlled depletion channel. It also did not close a mechanism that is distinctive to consumable certificate stock.

The pilot contains genuine positive evidence: the audit candidate correctly diagnosed several benchmark and selection problems and proposed upstream revision. Those observations are useful, but they are diagnostic evidence only because the candidate was never committed.

## Canonical-status boundary

The framing transaction committed in [`run/003_complete_attempt1_stdout.json`](run/003_complete_attempt1_stdout.json), and the repaired primitive-decomposition transaction committed in [`run/008_complete_attempt2_stdout.json`](run/008_complete_attempt2_stdout.json).

The economics-audit candidate in `run/010_candidate_attempt1.json` did **not** commit. The bridge returned only:

> `relation rel_governs_fqb_replacement_gate@1 binds an incorrect upstream semantic hash`

The response reports `mutated: false`. The subsequent terminal receipt records a failure while leaving the canonical head unchanged. Accordingly:

- the proposed `FramingQualityBundle`, its `revise_framing` action, and the replacement G1 dossier are not canonical objects;
- the absence of another science diagnostic cannot be treated as an economics pass, because validator order and validator coverage are not an independent economic review; and
- statements below about the audit candidate are diagnostic observations, not claims that the system canonically accepted them.

## 1. The central dominance implication

The committed primitive ledger jointly imposes the following assumptions:

1. `n_certificate_semantics` gives a visible certificate one banked unit of successful service. A certified trade succeeds independently of current uncertified capacity.
2. `n_buyer_payoff` normalizes successful service to one, failure and exit to zero, and subtracts `c` when inspection occurs. Purchase transfers are fixed and absorbed into the normalization.
3. The research seed and protocol place `c` strictly between zero and one for the relevant dominance check.
4. `n_trade_exit_choice` and edge `e_trade_depletion` claim that the buyer's purchase choice determines whether a certificate is depleted.

Consider any public state in which at least one certificate is available. Buying a certified seller directly gives the buyer payoff one. Inspection can deliver service value no greater than one under any subsequent optimal purchase decision, but it also costs `c`. Its payoff is therefore at most

\[
1-c < 1.
\]

Thus inspection is strictly dominated by direct certified purchase whenever a certificate is available. With one available certificate, its depletion is effectively mechanical under the stated ledger. With two available certificates, the buyer may select which identical certified option is used, but this does not create the claimed responsive search-versus-depletion margin under the symmetric fixed-transfer environment.

This result does not prove that certificate stock is economically irrelevant. Stock occupancy can still affect how often the economy reaches a no-certificate state and can affect beliefs conditional on that state. It does prove that the current ledger does not support a buyer-controlled depletion channel interacting with inspection in certificate-present states.

## 2. The audit checked the wrong buyer state

The buyer active-margin witness in `run/010_candidate_attempt1.json` explicitly uses the state:

> `No seller displays a certificate`

It sets independent high-capacity probability `p = 1/3` for each uncertified seller and `c = 1/9`. The candidate correctly computes

\[
V_I=-c+p+(1-p)p=4/9,
\qquad
V_0=p=1/3,
\]

and correctly derives the inspection condition `p(1-p) >= c`. This is a valid demonstration that inspection can be active in a no-certificate state.

It is not a test of the disputed margin. In that witness state, no action can deplete a certificate because no certificate exists. The witness therefore establishes a generic information-acquisition margin while bypassing the certificate-present state required by the protocol.

The witness's link-specific kill condition mentions that a certified outside option may dominate inspection, but the audit never substitutes the candidate's own payoff ledger into that condition. Had it done so, it would have found strict dominance in every certificate-present state. The four disclosed gaps are instead limited to:

- aggregate endogeneity under the frozen inspection kernel;
- incomplete off-support definition of that kernel;
- selector-only equilibrium assurance; and
- unresolved intertemporal certificate semantics.

There is no disclosed dominance or buyer-controlled-depletion defect. No certified price premium, horizontal match value, product differentiation, quantity constraint, or other buyer-facing tradeoff is introduced. Nor is the buyer-controlled depletion claim removed or downgraded. The protocol-specific repair therefore did not occur.

## 3. The stock-and-depletion mechanism is not closed

The full-model F assessment and the flow-model N assessment use the same exact principal channel path:

> `n_cost_k -> n_certification_choice -> n_uncertified_pool -> n_inspection_return -> n_inspection_choice -> n_outcome_Q`

That path contains neither `n_certificate_stock`, `n_trade_exit_choice`, nor the trade-depletion edge. It can describe current selective certification changing the uncertified pool in either a stock or a flow model. It cannot, by itself, identify the distinctive effect of certificate carryover or depletion.

The primitive graph does contain separate stock and depletion nodes and edges. The problem is not that the vocabulary is missing; the audit's operative three-link mechanism does not traverse it. Prose in the middle causal step says that carryover and trade depletion affect the stationary conditional distribution, but the exact chain bypasses those objects.

The minimal example also stops short of closure. It holds the buyer-side belief at `p = 1/3`, while the seller illustration independently varies `k`. It then says that buyer inspection can respond *if* equilibrium issuance and depletion move the belief through the inspection threshold. That is a useful conjecture, but it does not establish the required map

\[
k \longrightarrow \text{issuance}
\longrightarrow \text{stock/depletion transition}
\longrightarrow p
\longrightarrow \text{inspection}.
\]

The two local payoff comparisons are therefore not yet one closed economic mechanism.

## 4. Assessment of the seller active-margin witness

The seller witness is an improvement over unsupported verbal mechanism prose. It writes a continuation-inclusive issue-versus-not payoff gap and observes that a reduction in `k` raises that gap one-for-one.

However, the illustration assigns a current trade-success-probability difference of `1/2` and a continuation-value difference of `1/4` without deriving them from a fully specified common public state, buyer strategy, transition, and stationary continuation problem. The candidate itself properly labels the numbers illustrative and states that they do not establish a stationary equilibrium.

The correct diagnostic conclusion is therefore that a seller threshold is algebraically plausible, not that an equilibrium-reachable active seller link has been established. For a G1-quality mechanism, the witness must either be derived from an admissible reachable state or be classified as unresolved pending that derivation.

## 5. Positive scientific findings in the uncommitted audit

The audit candidate makes several correct and valuable diagnoses.

### Pointwise policy is not aggregate invariance

It correctly observes that fixing a state-contingent inspection kernel `q_bar(s)` does not fix the aggregate inspection rate when the stationary state distribution changes with `k`:

\[
Q_X(k)=\sum_s \mu_X(s;k)q_{\mathrm{bar}}(s).
\]

Seller issuance, trade, depletion, and carryover can all change `mu_X(s;k)`. The upstream statement that `Q_X` is mechanically fixed is therefore false.

### Off-support benchmark semantics are incomplete

The anchor equilibrium may not visit every public state reached under another value of `k` or in the flow intervention. The candidate correctly requires `q_bar` to be defined on the union of relevant public states before X and NX can be exact policy interventions.

### A selector is not selection robustness

The common selection rule makes the exercise reproducible. It does not establish uniqueness, continuity of an equilibrium branch, or invariance across all equilibria. The candidate correctly downgrades attribution on this ground.

### NX is not a purely mechanical baseline

Even with flow expiration and pointwise inspection fixed, sellers still reoptimize certification and current public-state weights still respond to `k`. The candidate correctly rejects the description of NX as a purely mechanical cheaper-certification response.

These are substantive economic improvements. They also show why requiring explicit payoff and benchmark ledgers is useful: the system produced objects that can be inspected and falsified rather than relying only on polished prose.

## 6. Research-question assessment

The central intuition is promising: a persistent, exhaustible certification stock may change the residual population over which buyers search. The audit memo's headline—“A consumable certificate can alter the object a buyer is searching over”—is economical and memorable.

The present question is nevertheless too permissive for a general-interest theory contribution. It asks whether there exists some admissible primitive vector, some outcome among `Q`, `A`, and `U`, and some ordered triple of certification costs producing a sign reversal. With a flexible admissible domain and a selected equilibrium, that can become a parameter-search existence exercise rather than a robust economic theorem.

Further, under the current fixed-transfer normalization,

\[
U(k)=A(k)-cQ(k),
\]

so `U` is not an independent economic object. The paper would need to identify the primary comparative-static object and derive a sharper threshold, characterization, impossibility boundary, or robust sufficient condition rather than treating any reversal in any of three outcomes as success.

The “banked successful service” certificate is also a substantive institution, not a harmless interpretation. It resembles a reserve, warranty, or service entitlement more than a conventional signal of current quality. A strong paper could study that object, but it must explain why it is economically natural and where it exists, or choose a different certificate technology.

## 7. Benchmark assessment

The four-cell stock/flow by endogenous/frozen-inspection design is a useful organizing idea. Its accounting identity is exact:

- `M = Delta Y_NX`;
- `S = Delta Y_X - Delta Y_NX`;
- `I = Delta Y_N - Delta Y_NX`; and
- `R = Delta Y_F - Delta Y_X - Delta Y_N + Delta Y_NX`.

Exact algebra does not make the labels causal. The cells change equilibrium behavior, public-state domains, state weights, and potentially the selected equilibrium branch. A nonzero `S` or `R` can therefore be a cross-model equilibrium contrast rather than evidence that the named economic channel is necessary.

At minimum, the eventual design should distinguish:

1. a state-contingent inspection-policy effect;
2. a public-state weighting or composition effect;
3. a stock-versus-flow institutional contrast; and
4. equilibrium-selection sensitivity.

The stock-versus-flow comparison may remain economically useful even when it is not called a “pure component.” The labels should match the intervention that is actually held fixed.

## 8. Kill-condition assessment

The framing supplies a falsifiable computational condition: reject the proposed stock attribution when no strict reversal requires a nonzero stock-dependent term. This is better than an unfalsifiable mechanism story.

It is still broad and partly ex post because the admissible parameter domain, equilibrium mapping, and causal interpretation of the algebraic residuals remain unresolved. More importantly, it omits the immediate link-level kill condition implied by the existing payoff ledger:

> If certified purchase gives one, inspection can deliver at most one, and `c > 0`, then inspection is strictly dominated whenever a certificate is available; the buyer-controlled depletion margin must be removed or the primitive ledger must change.

Another necessary kill condition is whether the stock model produces a mechanism path not reproduced by the flow model. If the exact operative F and N paths remain identical, a consumable-stock attribution has not been established.

## 9. Reader transfer and expected human burden

The economist-facing memo is materially clearer than the surrounding transaction representation. A cold reader can recover the broad question, the seller threshold idea, the hump-shaped information value `p(1-p)`, and the frozen-kernel problem.

The reader cannot recover a valid closed stock/depletion mechanism because the memo joins two local comparisons with an unresolved “if.” Its claim that both local margins are active can also give false confidence: the relevant certificate-present buyer margin is dominated.

Human intervention therefore remains high. Advancing this project would require the researcher to:

1. decide what the certificate economically represents;
2. add a genuine buyer-facing tradeoff or explicitly make depletion mechanical;
3. rebuild the benchmark semantics and outcome decomposition;
4. derive equilibrium-reachable seller and buyer margins;
5. establish how `k` changes the relevant conditional belief; and
6. sharpen the broad existence question into a theorem with robust economic content.

The system has reduced burden on aggregate-invariance, off-support, and selection diagnostics. It has not yet reduced the most important burden: detecting and repairing the primitive-level contradiction that collapses the advertised buyer channel.

## 10. Top-5 readiness

**Current readiness: not close to a Top-5 submission.**

This is not primarily a writing problem. The economic hook is potentially valuable, but the current primitive ledger makes the proposed interactive buyer-depletion channel inactive, the distinctive stock path is absent from the operative chain, and the headline result is a broad existence search rather than a robust characterization.

A Top-5-level development would need a natural institution, a mechanism that survives a complete payoff ledger, an exact and defensible benchmark, general comparative statics or characterization results, and robustness beyond an arbitrary equilibrium selector. The present artifacts are useful pre-model diagnostics, not a paper-ready foundation.

## 11. Minimal high-leverage repairs

These are scientific safeguards, not additional enterprise workflow.

### A. Bind each witness to the claimed link and relevant state

An active-margin witness must use a state in which the disputed action can affect the claimed downstream object. A no-certificate inspection witness cannot validate buyer-controlled certificate depletion.

### B. Require the distinctive path to traverse the distinctive primitive

Any stock attribution must have an exact F path that traverses certificate stock and the relevant transition or depletion edge. If the F and N channel paths are identical, the system should classify the stock attribution as unresolved or unsupported.

### C. Run the complete action envelope by public-state class

For every public state used by a mechanism, compare the focal action with all feasible deviations. When the ledger supplies a known payoff upper bound, dominance should be resolved directly rather than deferred to prose.

### D. Choose one of two economic repair branches

1. **Activate buyer-controlled depletion.** Add a natural certified-price, match, fit, quality, congestion, or other tradeoff so that direct certified purchase and inspection of an uncertified seller can each be optimal in a nonempty parameter region. Then derive the same-state payoff threshold.
2. **Make depletion mechanical.** Retain the current value normalization, acknowledge that a visible certificate is purchased without inspection, and remove buyer-controlled depletion language. The mechanism should then be written as seller issuance, stock occupancy and mechanical transition, the distribution of no-certificate states and their conditional quality, and inspection only in those states.

### E. Decompose aggregate inspection honestly

Separate changes in the inspection policy from changes in public-state weights. Treat F versus N as an institutional equilibrium contrast unless stronger invariance conditions support a causal component label.

## Final decision

| Dimension | Judgment |
|---|---|
| Protocol termination | Engine-compatibility failure; not itself a scientific failure |
| Audit canonical status | Uncommitted; diagnostic observations only |
| Dominance detection | Failed on the protocol-specified certificate-present state |
| Buyer-controlled depletion repair | Neither repaired nor downgraded |
| Stock mechanism closure | Failed; F and N use the same principal path and bypass stock/depletion |
| Benchmark diagnosis | Substantively improved and largely correct |
| Reader transfer | Clearer prose, but the central mechanism remains incomplete |
| Top-5 readiness | Not ready; major economic redesign required |
| Overall | **Scientific revise / economics gate fail** |
