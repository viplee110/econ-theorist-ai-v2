# Public evidence and redaction manifest

The unmodified private execution record remains under the isolated pilot root
recorded in `preflight_manifest.md`. The public archive copies the permitted
evidence bytes exactly; no retained file required redaction.

## Scan result

The retained set was scanned after the generator stopped for common OpenAI,
GitHub, and AWS key formats; private-key blocks; bearer tokens; cookies;
password, API-key, client-secret, and access-token assignments; email
addresses; Windows, macOS, and Linux user-profile paths; and the researcher's
known GitHub identity. The scan found zero matches in every category.

References to the clean `C:\tmp\etai-v5_3-public-pilot-20260715-f7f34ef`
root, its isolated `.host-state`, and its discarded virtual environment are
not user-profile disclosures. They are retained where needed to establish
isolation and exact capture paths.

## Exact public copies

- `generator_report.md` has original SHA-256
  `E70B97D41160F42D6670B87072E4B46EEC004C693AB7037C39E5C920BB4C1D41`.
- `run/` contains 49 exact files totaling 611,892 bytes. Files numbered
  001--014 are the frozen generator record. The four files numbered 015 are an
  explicitly post-freeze, byte-identical replay of the terminal request.
- `canonical_state/.econ-theorist/` contains 34 exact files totaling 492,478
  bytes from the permitted project, provenance, refs, runs, snapshots,
  staging, transactions, and views subtrees.
- All 84 copied generator, run, and canonical-state files were compared with
  their private originals by SHA-256; there were zero missing or mismatched
  files.

## Deliberate exclusions

The archive excludes the virtual environment, wheel bytes, installed local
skill copy, capture-helper copy, unrelated host files, `.host-state`, locks,
and the operational journal. Their relevant frozen hashes or exclusion rules
are recorded in `preflight_manifest.md` and `protocol.md`.

The post-freeze audits are new public analysis rather than copies of generator
output. They never overwrite or repair the frozen candidates.
