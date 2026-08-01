# Phase 5B.1 Theorem Challenge-Team Contract

## Status and purpose

Phase 5B.1 adds one bounded, optional research team around an immutable
`verify.claims_proofs_and_interpretation` WorkPacket. It improves the chance
that a formally correct-looking result is challenged before the coordinator
authors the route candidate. It does not add a canonical route, schema, gate,
scientific standard, or second workflow.

The existing route instruction, `ClaimGraph`, `ProofObligation`,
`VerificationRecord`, `VerificationBundle`, validators, and G4 human decision
remain authoritative. This slice only makes two separable advisory tasks
explicit:

1. one proof worker attempts every exact `ProofObligation` in the packet; and
2. one counterexample/economics challenger attacks the same obligations for
   boundary failures, missing assumptions, false interpretation, and weak
   economic content.

The coordinator receives both raw reports and the unchanged WorkPacket, then
authors at most one candidate through the existing completion path. Advisory
workers never write canonical state or decide G4.

## Activation boundary

The team may open only when all of the following hold:

- the bridge has delivered a current public WorkPacket for exactly
  `verify.claims_proofs_and_interpretation`;
- the packet contains the complete, nonempty tuple of exact
  `ProofObligation` revisions selected by the existing route;
- the host can expose the same packet to two logically sealed lanes; and
- no candidate has already been staged for the run.

Activation is optional. If the host cannot provide the declared lanes, the
unchanged single-agent route remains available. Once activated, the run must
complete through the exact published theorem-team review; it cannot silently
downgrade to an unbound single-agent candidate.

## Lane inputs and outputs

Each lane receives only:

- the exact WorkPacket already delivered to the coordinator;
- its exact role overlay; and
- its lane-input hash.

It receives no peer output, coordinator conversation, remembered project
context, candidate draft, or authority to delegate. Both lane records bind the
complete ordered tuple of `ProofObligation` refs extracted from the packet.

The proof worker must distinguish derivation, assumptions used, unresolved
steps, and finite checks. A numerical example or enumeration may falsify or
corroborate, but cannot certify a universal claim.

The challenger must search for counterexamples, boundary cases, omitted
assumptions, semantic overreach, and a theorem whose stated economic mechanism
is false or unimportant. It does not need to manufacture a criticism when the
claim survives; a clean challenge report is still useful evidence.

The published review preserves both attributed raw reports. Agreement is
correlated advice, not proof. Disagreement must remain visible in the
coordinator's `VerificationRecord`/`VerificationBundle` candidate rather than
being averaged away.

## Canonical completion and authority

The coordinator is the sole candidate author and the existing engine is the
sole canonical writer. A declared theorem team requires:

- one exact immutable review hash;
- `stage_and_commit` through the existing bridge completion operation; and
- an operational completion binding between that review, candidate digest,
  delivery envelope, coordinator model observation, and completion operation.

The sidecar records are operational and noncanonical. They do not establish
formal validity, economic interpretation, novelty, contribution, or G4
approval. The unchanged route validator decides whether the candidate is
admissible; the researcher alone decides whether the useful result portfolio
deserves further investment at G4.

## Recovery and compatibility

Plan, review, and completion publication are immutable and exactly retryable.
A stale base, changed delivery, changed obligation tuple, mismatched review, or
candidate staged before team activation fails closed. After activation, a
validator-rejected candidate may be repaired and resubmitted under the same
immutable review; its new candidate digest receives a new completion binding.
Historical packets and ordinary single-agent completion bytes remain valid
when theorem-team fields are absent.

Focused Phase 5B.1 tests cover route restriction, exact obligation binding,
lane isolation records, immutable retry, stale/wrong review rejection, no
canonical write before completion, and completion binding. This slice does not
claim that multiple agents improve research quality until a later real project
comparison supplies that evidence.
