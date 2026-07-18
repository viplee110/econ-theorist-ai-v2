# Frozen evaluator key: failure-refund pair

This file is evaluator-only.  It must not be copied into either generator arm
or opened before both arm artifacts are frozen.

## Economics rubric

Score each item 0 (wrong/absent), 1 (partial or ambiguous), or 2 (correct,
explicit, and scoped).

1. **Exact accounting:** recovers -1/3 and +1/3 for the initiator and 0 and 1/3
   for equilibrium provision under no-refund and refund.
2. **Mapping versus behavior:** states that fixed-strategy provision stays 1/3
   and does not use the payoff-ledger change itself as active causal evidence.
3. **True response margin:** identifies the initiator's contribution as the
   rule-responsive choice; does not invent a change in the follower's
   high/low-type strategy.
4. **Held-fixed boundary:** keeps type probabilities, values, contribution
   cost, threshold, timing, information, and campaign-close rule fixed.
5. **Causal/claim discipline:** connects refund, failed-state loss, initial
   contribution, conditional follower action, and provision; handles the
   no-start branch without an arbitrary selector and avoids welfare,
   optimality, universality, novelty, or human-approval overclaims.

Record separately whether the proposed action is `READY`, `REVISE`, or `KILL`.
A complete and restrained answer may be ready for proposed human G1 review.
An honest revise outcome must name a real, exact scope-blocking gap and narrow
its claims.  If welfare is introduced, missing platform disposition of failed
contributions is a real gap.

## Reader probes

Without seeing this key or the case, ask a fresh reader to retell:

1. the question and exact comparison;
2. what the refund directly changes;
3. whose choice changes and whose conditional strategy does not;
4. why provision changes from 0 to 1/3;
5. the main limitation or prohibited claim.

Assign H1--H4 editing burden independently of machine validity.  Preserve the
free retell before showing any probe or the other arm.

## Mechanical traps (not substitutes for the rubric)

- fixed strategy incorrectly raises provision probability;
- provision is reported as 1 rather than 1/3;
- follower behavior is claimed to change with refund;
- initiator choice is simultaneously held fixed and reoptimizing;
- type weights are treated as endogenous;
- successful contributions are treated as refunded;
- failed-state payoff 0 is confused with expected payoff +1/3;
- a proposed G1 dossier is represented as a confirmed human decision.
