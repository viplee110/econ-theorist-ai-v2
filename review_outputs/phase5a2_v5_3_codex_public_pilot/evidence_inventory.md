# V5.3 public pilot evidence inventory

## Frozen pre-generation inputs

- `protocol.md` -- protocol frozen before generation.
- `preflight_manifest.md` -- implementation, wheel, registry, instruction,
  skill, case, environment, and verification hashes.
- `generator_case.md` -- exact clean-root `CASE.md` copy.

## Frozen generator record

- `generator_report.md` -- exact terminal report, preserved even where the
  postmortem later disproves its compatibility attribution; SHA-256
  `E70B97D41160F42D6670B87072E4B46EEC004C693AB7037C39E5C920BB4C1D41`.
- `run/` -- 49 files totaling 611,892 bytes.
  - Invocations 001--014 contain every request, raw stdout, raw stderr, capture
    metadata, and each saved candidate attempt produced during generation.
  - Invocation 015 is explicitly post-freeze: an exact replay of request 014
    used only to test terminal exactly-once behavior.
- `canonical_state/.econ-theorist/` -- 34 files totaling 492,478 bytes from
  the permitted project, provenance, refs, runs, snapshots, staging,
  transactions, and views subtrees.

All 84 copied generator, run, and canonical-state files were compared with
their private clean-root originals by SHA-256. There were no missing or
mismatched files.

## Post-freeze independent analysis

- `machine_protocol_audit.md` -- route, attempt, binding, finish, replay,
  generator-use, latent-validator, and interface postmortem.
- `economics_audit.md` -- independent IO/micro-theory dominance, mechanism,
  benchmark, Top-5-potential, and human-burden assessment.
- `reader_transfer_audit.md` -- cold-reader reconstruction, intuition,
  mechanism-closure, benchmark, prose, and revision-burden assessment.
- `failure_report.md` -- integrated decision-rule report.
- `public_redaction_manifest.md` -- exclusions, exact-copy counts, scan scope,
  and the zero-redaction result.

## Exclusions

The archive excludes the virtual environment, distribution bytes, installed
skill copy, capture-helper copy, isolated host state, locks, operational
journals, and unrelated host files. Frozen input hashes and the exclusion
boundary are recorded in the protocol and preflight manifest.
