# Frozen protocol: V8 authoring pair v2

## Purpose

Measure whether the V2 semantic authoring surface reduces low-level authoring
tax without weakening the unchanged registry-V8 scientific validator.  This
is noncanonical compiler evidence, not a public-bridge integration test and
not evidence of research quality by itself.

## Frozen arms

- `transaction`: the model authors the complete existing Transaction surface.
- `semantic_v2`: the model authors `FramingAuditSemanticDraftV2`, including
  scientific `channel_intents` and `margin_intents`; the compiler owns exact
  input refs, channel paths, choice/payoff node bindings, consequence edge
  paths, wrappers, relations, IDs, hashes, and route outcome.

Both arms receive the same generator-visible case, WorkPacket, and
FramingQualityBundle payload contract.  Only the surface contract differs.

## Execution

1. Prepare into a new output root with
   `scripts/prepare_framing_authoring_pair_v2.py` and an exact clean engine
   commit plus its exact wheel.
2. Verify the externally anchored pre-manifest before opening either arm.
3. Create two independent new Codex tasks using the same ordinary/medium model
   class.  Open both before reading either result.
4. Give each task only its frozen launch prompt.  No task may read the
   repository, parent, sibling arm, evaluator directory, old conversation,
   network, source, tests, or fixtures.
   This is local-use instruction isolation, not an attacker-resistant
   filesystem or operating-system claim.
5. Each arm gets at most three immutable attempts and stops at first validator
   pass.  Receipt diagnostics are its only repair feedback.
6. The harness validates in memory.  Every attempt must report identical
   canonical head before and after and zero canonical writes.
7. Do not invoke the bridge, commit a candidate, confirm a human gate, or run a
   formal generator while preparing the pair.
8. After both arms stop, freeze their reports and receipts before exposing the
   evaluator-only key to an independent adjudicator.  The key remains in the
   exact engine commit and is bound by hash in the pre-manifest; it is not
   copied into the pair workspace.

## Comparison

Report machine validity, repair burden, source size, structural authoring,
economics, claim discipline, and cold-reader recovery separately.  A V2
machine pass does not establish better economics, and a scientifically good
draft that fails wrappers is not a machine pass.  Integration into the public
bridge remains a later decision based on the paired evidence.
