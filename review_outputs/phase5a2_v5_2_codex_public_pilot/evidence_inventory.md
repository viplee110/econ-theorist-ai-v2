# V5.2 public evidence inventory

## Frozen inputs

- `protocol.md` — protocol frozen before generation.
- `preflight_manifest.md` — exact source, wheel, navigation, skill, CASE, and
  verification hashes.
- `generator_case.md` — byte-for-byte copy of the isolated generator's
  `CASE.md`, SHA-256
  `F61EE776FBB1FCAAC2A28EF53ED3B903433378D74AAD522E1F5C5045DFBE38FD`.

## Generator record

- `generator_report.md` — public-redacted copy of the terminal generator
  report; the original hash is recorded in `public_redaction_manifest.md`.
- `evidence_inventory.json` — original generator inventory, SHA-256
  `4B8C383FDABD13F90E59DC68A5B41C121B57A49B3DFB817332010F589AD62AB5`.
- `failure_report.md` — post-freeze causal and decision-rule audit.
- `public_redaction_manifest.md` — exact scope and original hashes for the two
  bounded public path redactions.

## Numbered bridge evidence

`run/` contains 53 files for invocations 001--014: available request JSON,
raw stdout and stderr, wrapper failure evidence, and invocation metadata. The
successful invocation 004 raw stdout was not captured; its metadata records
the gap, and invocation 005 captures the same still-open route packet without
claiming byte identity.

## Canonical store

`canonical_store/.econ-theorist/` contains 37 files (517,341 bytes):

- project metadata;
- provenance objects and main ref;
- the three route-run directories and two committed outcomes;
- latest snapshot and status view;
- every staged framing, decomposition, and audit candidate retained by the
  canonical store;
- the three canonical transaction files.

The copied file count and byte count exactly match the corresponding permitted
source subtrees. Operational host state, locks, the environment, distribution,
and unrelated host files are excluded.
