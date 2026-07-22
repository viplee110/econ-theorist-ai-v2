# Source-aware controller machine audit

This is a postflight audit of the recorded public transport and canonical
state. It is not a scientific-quality judgment and is not provider-independent
attestation.

Evidence is bound to engine
`cb2abb97e94086e940bb1a84c95eb054cd4eca2c`, wheel
`f94f62ecfbc11bcdf7ad52b5cadd4ed127de0006309a54daf025e1bea7670064`,
and observable model label `user-selected-high-intelligence-unverified`.

## Verdict: PASS

- The preflight manifest and anchor match every declared static input. The
  installed distribution points to the same wheel.
- Captured invocations 001--007 had byte-identical source and captured
  requests, matching request/stdout/stderr hashes, valid response schemas, and
  no binding error.
- The recorded calls 001--004 retained one session, WorkPacket
  `b15db115d1803573cd2e492af3af81339d32ca93064530b4f200f8d12114607a`,
  and envelope
  `2e399d7a0ced6e3f37b4304ee94171d7578e28cd72ffa7e258d28354f4caae70`.
- The operational store contains exactly the attributed mentor, collaborator A,
  and collaborator B outputs in the panel and one recorded worker activation
  for handoff
  `89ff1c396ba22b9d591ac4e6e6edfe221a1871cd0279c2df20e9d21a5b5716a4`.
- Candidate digests progressed from `77be5ddd...` to `649c1ff4...` to
  `50fa98f6...`. The first two attempts recorded only their exact
  `CandidateValidationError` and operational provenance. They created no host
  receipt, transaction, or canonical-head advance.
- The third attempt has the sole recorded receipt
  `3a2abf14797dd98351df17fb132916aa6aa23cf4089de3a9d7c521c6e52d4211`.
  Its candidate, transaction, and head-after all equal
  `50fa98f65c974269044331d023eb06cf6071a6207df27ab3f5c71e8a5771fcfd`.
- Canonical state contains genesis plus this framing transaction, one completed
  route outcome, no Decision or approval, and no decomposition, audit, G1, or
  later route.
- All 22 inspected content-addressed team/completion sidecars matched their
  addresses.
- The compact archive includes the exact team-plan and host-receipt preimages;
  their SHA-256 values equal the plan and receipt hashes used by the recorded
  chain.

Two empty `.git` and `.codex` marker directories appeared after preflight and
before engine initialization. They contained no files, did not form a Git
repository, and changed no manifest-bound bytes; they are host-created state,
not scientific-input contamination.

The generator's `agent-report.md` is retained as a self-report. This controller
audit independently checked its machine claims against the capture metadata,
operational sidecars, canonical transaction, ref, and outcome, but it cannot
prove the actual model backend, provider-level delivery, worker identity, or
cryptographic lane independence.
