# D2 economy-tier diagnostic terminal note

The D2 generator was frozen after its legitimate terminal finish and before
post-run evaluation. The exact model slug was not observable; this run is an
economy-tier diagnostic selected by the researcher, not the official frozen
model treatment.

## Canonical outcome

- Clean root: `.etai-v5_4d2-economy-tier-20260716-c8c539e`
- Engine source: `c8c539e6b81404cfcd1eb247956b626f4b18ef2f`
- Framing commit/head:
  `b1debfed9b4eca68dc3b963586e74920e4caf995b61b63d90b49e9e2428c3147`
- Primitive-decomposition attempts: three
- Result of each attempt: `CandidateValidationError`, reporting zero
  BenchmarkSet route inputs
- Corrected finish result: `recorded_failure`
- Completion status: `failed_no_effect`
- Final host receipt:
  `6129a0cac426112104505fd2f3ece8965a10969941b113294d7030f6f59e220b`
- Head before and after finish: unchanged
- Human decisions recorded: none

The first finish request used free-text warnings and was rejected. The corrected
request used bounded opaque warning IDs and is the terminal request. The
byte-identical replay comparison applies to that corrected request, not to the
earlier invalid finish.

## Replay

The corrected terminal response and its post-freeze replay are byte-identical.
Both have SHA-256:

`FFBF2D59F5788C2DBB5C9C19542DC650DF34CA34E06E3FABB509DF035E2E4481`

## Frozen generator clarification

The generator reported no mismatch in root-local canonical state. It confirmed
that the first finish and its exact replay were errors, while the corrected
finish recorded failure without changing a route, candidate, decision, or
canonical head.

Post-freeze machine diagnosis is recorded separately in
`evaluation_report.md` and must not be attributed to the generator.
