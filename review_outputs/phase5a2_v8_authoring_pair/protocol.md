# Registry-V8 paired authoring shadow protocol

Status: preregistered; generation not yet executed.

## Question

Does a model-facing semantic draft plus deterministic compiler reduce the
structural authoring tax observed in R3 without weakening the unchanged V8
validator or degrading the economics?

This is an authoring-interface experiment, not another full research run.  It
uses one fresh held-out audit base and never stages, commits, finishes a run,
or records a human gate.

## Frozen pair

Both arms receive byte-identical `CASE.md`, `COMMON_WORK_PACKET.json`, and
`FRAMING_PAYLOAD_CONTRACT.json`, derived from one exact fresh registry-V8 audit
run and base `Snapshot`.

- Transaction arm: authors one complete Transaction under the existing
  `CandidateAuthoringContractV1` surface.  Runtime facet hashes may be
  materialized only by the existing draft boundary.
- Semantic arm: authors one `FramingAuditSemanticDraftV1`.  The compiler binds
  the four exact inputs, resolves declared paths, creates wrappers, the
  replacement dossier, five exact hard relations and the route outcome.

Both arms end at the same unchanged call to `validate_candidate` with the same
Snapshot, V8 registry hash, and live-policy enforcement.  Canonical head before
and after must be identical.

## Isolation and execution

Use the same ordinary/medium model and settings in two new tasks.  Each task is
opened with the pair directory as its workspace root only so the frozen runner
can read the shared runtime, then restricted by protocol to its own arm
directory and the single frozen harness command.  The model may not inspect
the parent/shared runtime directly or use network access, subagents,
repository source, tests or fixtures, earlier pilots, old conversations, the
sibling arm, or the evaluator key.  This is local-use protocol isolation, not
an attacker-resistant filesystem claim.  The visible model label is recorded;
provider/backend identity is not invented when it cannot be independently
observed.

The arm order is fixed from a deterministic seed over the frozen scientific
and engine bindings, then recorded in and bound by the pre-manifest before
either model runs.  Start both tasks before inspecting either answer.  Do not
feed observations from the first arm to the second.

The development task supplies the exact `PRE_MANIFEST.json` SHA-256 as the
external root of trust.  That pre-manifest binds two launch prompts, and each
launch prompt supplies the exact SHA-256 expected by its arm verifier.  A
compiler contract, generated-ID, runtime, or frozen-hash failure is
`INVALID_SETUP`; it is not charged to either model.  Each runner derives the
only permitted source path from the attempt number and cannot accept an
arbitrary source file.  Preparation reads the selected wheel once, installs
only that frozen copy, verifies every installed Python module byte against the
exact clean checkout, and separately verifies the WorkPacket engine semantics
and registry hash.  It omits the unused pip-generated `etai` console launcher
from the isolated module-only runtime and records that omission; neither arm
uses the CLI or bridge.  The wheel digest remains an explicit evidence
binding, not a supply-chain signing claim.

## Attempts and stop rule

Each arm gets an initial artifact and at most two revisions.  Every model
artifact after a harness rejection counts as one experimental repair,
including a semantic preflight rejection.  Return the complete immutable
harness receipt verbatim; do not hand-edit, summarize, or add hints.  Stop at
the first V8 pass or after attempt three.  A setup/hash/harness mismatch makes
the pair `INVALID_SETUP`, not an arm failure.  One exhausted arm does not cancel
the other.

## Measures

Machine and burden measures are preregistered separately from scientific
quality:

- strict parse/preflight and V8 validity on first attempt;
- V8 validity within three attempts, attempts and diagnostic taxonomy;
- raw and canonicalized authored JSON bytes, diagnostic bytes, JSON-pointer
  revisions, harness calls, and elapsed time; model self-reported token counts
  are not treated as telemetry;
- frozen economics rubric, outcome class, omitted or invented primitives;
- separate cold-reader retell and H1--H4 editing burden.

Every rejection sets the symmetric experimental-repair-required measure,
regardless of arm or rejection layer.  A separately reported engine-route
repair equivalent describes how the current canonical engine would behave,
but is explicitly ineligible for the cross-arm burden comparison.

Machine validity cannot compensate for an economics or reader failure.

## Conclusion boundary

`COMPILER_FEASIBILITY_SIGNAL` requires semantic-arm V8 validity within three
attempts, zero writes, lower structural rejection/attempt or authored-byte
burden than the Transaction arm, no economics rubric item falling to zero, and
no worse reader burden.  Similar arms are `NO_CLEAR_SURFACE_SIGNAL`; mechanical
improvement with scientific degradation is `MIXED`; any frozen-boundary
mismatch is `INVALID_SETUP`.

One pair cannot establish research readiness, general quality improvement, or
v2 superiority.  It decides only whether bridge integration of the prototype
is the next justified small step.
