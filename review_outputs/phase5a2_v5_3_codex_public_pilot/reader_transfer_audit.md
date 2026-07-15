# Independent reader-transfer audit

## Status and scope

**Reader-transfer verdict: REVISE.**

This is a cold-reader assessment of the frozen V5.3 public pilot archive. The
assessment used the frozen protocol and the archived economist-facing
candidate material, memo, and dossiers. It did not use implementation source,
tests, old pilots, or a reference answer.

The `audit.framing_economics` candidate was **not canonically committed**. It
failed at the bridge's runtime semantic-hash boundary and is therefore
diagnostic material only. Its scientific observations do not replace the
canonical pre-audit dossier or constitute a G1 decision. The contract exposed
a callable derivation, but the generator used an all-zero hash and stopped
before retry exhaustion. The observed stop is therefore generator misuse plus
a protocol violation, alongside a separate product-UX defect: derived engine
metadata should not burden a research agent. The reader-transfer content can
still be assessed independently.

The content requires substantive scientific revision rather than copy-editing.
The underlying idea is intelligible and potentially useful, but the central
dynamic link and the benchmark interpretation are not yet sufficiently closed
for a general-interest theory reader.

## What a cold theory reader can recover

The economic puzzle is recoverable. A lower truthful-certification cost can
change selective issuance, the inventory and depletion of visible
certificates, the composition of sellers who remain uncertified, and hence the
value of inspecting an uncertified seller. The proposed outcome is a possible
non-monotonic response of inspection, successful allocation, or buyer surplus,
with no sign claimed in advance.

Across the ResearchQuestion and BenchmarkSet, the reader can also reconstruct
the actors and timing: two long-lived sellers privately observe capacity; a
short-lived buyer arrives each period; eligible high-capacity sellers may
issue a banked certificate; the buyer observes certificate stocks and then
inspects, buys, or exits; trade consumes a used certificate; and unused
certificates carry forward. This sequence is not, however, stated
self-containedly in the economist memo or replacement dossier. A reader using
only either nominally reader-facing object would have to infer or retrieve too
much of the model scene.

The memo's most effective intuition is that a consumable certificate can alter
the object over which a later buyer searches. The distinction between
certification take-up and the composition of the residual uncertified pool is
economically meaningful and easy to retell.

## The three-link mechanism

The proposed mechanism has two well-expressed endpoints and one unresolved
middle link.

1. **Cost to seller issuance.** The candidate gives a concrete eligible-seller
   state and compares issuance with non-issuance using the continuation-inclusive
   gap
   `D_S = gross issuance benefit - k`. It correctly explains that lowering
   `k` moves this gap one-for-one. The numerical illustration demonstrates two
   local action regions, but its trade-probability and continuation-value
   differences are posited rather than derived from a consistent equilibrium.

2. **Issuance and depletion to uncertified-pool composition.** This is the
   scientific bottleneck. The candidate says that selective issuance,
   carryover, and depletion *can* change the conditional high-capacity
   probability among uncertified sellers. It supplies no stock-balance or
   transition equation showing how the certification response changes that
   probability, no signed or threshold result, and no solved minimal state
   system. This leaves the central mechanism link open.

3. **Composition to buyer inspection.** In a no-certificate state the candidate
   compares inspection with the complete no-inspection deviation envelope and
   derives `D_B = p(1-p) - c`. This is concrete, economically interpretable,
   and correctly hump-shaped in the uncertified-pool belief `p`. It establishes
   a nonempty local inspection region, not the equilibrium map from `k` to `p`.

Consequently, the chain is graphically connected but not yet economically
closed. A theory reader can see what must be proved, but cannot yet verify that
the stated primitives generate the proposed stock-composition-search channel.

## Certified-option dominance

The audit correctly notices the key payoff comparison but does not carry its
implications far enough. Whenever a certificate is available, buying certified
service gives the buyer value one, whereas inspection yields at most one minus
the strictly positive search cost. Thus inspection is not an active competing
action in a certified state under the current payoff ledger.

This does not automatically eliminate every inventory effect because two
sellers can simultaneously display certificates and at most one is consumed
by the period's single buyer. It does sharply restrict the channel: a lone
certificate is bought and depleted immediately, persistence relies on excess
certified supply, and inspection can be active only after the public state has
no certificate. The current memo does not explain this state logic. It also
continues to speak loosely about buyer-controlled depletion even though the
depletion action is mechanical in the relevant certified states, apart from
the choice between payoff-equivalent certificates.

A successful revision must either make this restricted stock logic the center
of the mechanism or add an explicit buyer-facing tradeoff, such as price or
match value, that can make certified purchase and inspection genuinely compete.

## Benchmarks and falsification

The four cells are easy to remember: full consumable stock with endogenous
inspection (`F`), flow certification with endogenous inspection (`N`),
consumable stock with a frozen pointwise inspection rule (`X`), and flow
certification with that rule (`NX`). The factorial identity is arithmetically
valid.

Its causal labels are not valid as written. Fixing the state-contingent rule
`q_bar(s)` does not fix aggregate inspection when certification, depletion, and
trade change the stationary weights on public states. The rule is also not
defined on the union of states that may be reached across stock and flow
environments. Finally, a common selector is a reproducibility convention, not
evidence that comparisons survive equilibrium multiplicity. The uncommitted
audit candidate identifies these defects correctly and appropriately proposes
revision.

The current flow benchmark removes carryover and trade-triggered depletion at
the same time. It is a meaningful boundary model, but it does not separately
identify inventory persistence from endogenous depletion. A matched
exogenous-expiration benchmark would be more informative about whether trade
triggering, rather than the mere existence of persistence, does the economic
work.

The archive includes useful local kill conditions for the seller and buyer
margins. The top-level kill condition is less informative because it largely
says to abandon the mechanism if an exhaustive parameter and equilibrium
search finds no required reversal. The missing central falsifiers should be
stated directly: the mechanism dies if certificates cannot persist on the
equilibrium path, if issuance and depletion leave the uncertified conditional
distribution invariant, or if the full and appropriately matched no-stock or
exogenous-depletion models coincide for the claimed outcome.

## Readability and expected human effort

The economist memo is clearer than the surrounding structured transaction,
but it remains a compact audit summary rather than paper prose. Phrases such
as “active local margins,” “aggregate attribution,” “selector-only,” “frozen
pointwise policy,” and “ready for G1” foreground the system's checking process
instead of the market's economic logic. The dossier is necessarily even more
checklist-like. Neither object opens with a vivid model scene or walks the
reader through one certificate's economic life.

The required human intervention is **high** for a paper-quality framing. A
theorist would need to derive the missing transition link, redesign or relabel
the benchmark decomposition, resolve certificate semantics, and write a new
standalone narrative. The existing material is useful as an internal research
diagnostic and as a map of unresolved issues; it is not close to an
introduction or model-motivation section that can be polished into place.

## Five priority improvements

1. **Close the middle mechanism link.** Write the smallest stock-transition
   system and derive how `k` changes issuance, certificate inventory and
   depletion, and the conditional belief `p` among uncertified sellers. State
   exactly when this mapping is zero, changes sign, or crosses the buyer's
   inspection threshold.

2. **Resolve certified-option dominance and persistence.** Analyze the zero-,
   one-, and two-certificate public states explicitly. Show why inventory can
   survive despite immediate purchase of a lone certificate and why search is
   active only in no-certificate states, or introduce a genuine buyer-facing
   tradeoff if endogenous depletion choice is essential.

3. **Repair the benchmark architecture.** Define `q_bar` on a common complete
   state domain; distinguish a fixed pointwise policy from fixed state weights;
   use conditional outcomes or an explicit reweighting decomposition; and add
   a matched exogenous-expiration comparison if trade-triggered depletion is a
   separate claimed force. Treat equilibrium selection as conditional unless
   uniqueness or branch robustness is established.

4. **Write a standalone economist narrative.** Begin with the actors and
   within-period timing, then present the three-link intuition, the two payoff
   inequalities, the role of each benchmark, and the mechanism's falsifiers.
   Remove object identifiers, G1 terminology, and process-audit vocabulary
   from the reader-facing memo.

5. **Sharpen the theoretical target.** Replace the broad search for any
   three-cost reversal with a structured proposition or threshold result in a
   solved minimal example. Promote direct mechanism-death statements—such as
   no persistent stock, invariant uncertified composition, or equality with a
   matched benchmark—over an exhaustive-search kill condition.
