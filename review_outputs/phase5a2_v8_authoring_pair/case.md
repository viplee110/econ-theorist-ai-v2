# Held-out case: failure refunds and threshold provision

Status: frozen generator-visible scientific brief for one noncanonical paired
authoring test.

This case is distinct from the certification/service-guarantee pilot.  It is a
two-person sequential threshold-contribution game.

## Environment

1. An initiator first chooses whether to contribute 1.  If the initiator does
   not contribute, the campaign closes and the follower never moves.
2. After an initial contribution, the follower observes her own value and
   chooses whether to contribute 1.  The project is provided only if both
   contribute.
3. The initiator values provision at 2.  The follower's value is 2 with
   probability 1/3 and 0 with probability 2/3.  Values, probabilities, costs,
   threshold, timing, and information are common knowledge.
4. Under `no_refund`, a failed campaign keeps the initiator's contribution.
   Under `failure_refund`, a failed-campaign contribution is returned.  A
   successful contribution still costs 1 under both rules.
5. The target is provision probability and the initiator-participation
   mechanism.  Welfare, optimal mechanism design, platform revenue, empirical
   validity, and literature novelty are outside scope.

## Exact benchmarks

`b_fixed_strategy_accounting` holds fixed initial contribution and the
follower strategy "contribute if high, decline if low."  The initiator's
expected payoff is -1/3 without a refund and +1/3 with a failure refund, while
provision probability remains 1/3.  This benchmark separates a payoff mapping
from a behavioral response.

`b_sequential_reoptimization` uses backward induction.  The high follower
type contributes and the low type declines under both rules.  Without a
refund the initiator compares -1/3 with 0 and does not start, so provision
probability is 0.  With a failure refund the initiator compares +1/3 with 0
and starts, so provision probability is 1/3.

The canonical WorkPacket is the source of truth for exact object IDs,
PrimitiveGraph nodes and edges, route instructions, privacy, provenance, and
the pre-G1 dossier.  A generator must neither confirm a human G1 decision nor
extend the stated claim scope.
