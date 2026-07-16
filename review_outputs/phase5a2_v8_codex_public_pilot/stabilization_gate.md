# V8 post-pilot host-stabilization gate

Status: **deterministic acceptance passed; the same-case rerun exposed a
diagnosed model-content failure, while the held-out run remains open**

This gate prevents the V8 pilot from turning into an unbounded sequence of
scientific route versions. It changes host interoperability, diagnostics, and
evidence capture only. It does not change the V8 route registry, route
instruction, schemas, scientific acceptance conditions, or human G1 authority.

## Frozen scope

The stabilization candidate may do only the following:

1. accept one leading UTF-8 BOM at the noncanonical host candidate-source
   boundary, then derive the same strict BOM-free canonical Transaction bytes;
2. return all observed primitive-path binding and adjacent-chain closure issues
   in one bounded structured diagnostic, with exact candidate-relative
   locations and node/force identifiers already present in the WorkPacket;
3. expose the existing bounded opaque warning-token grammar in the Codex finish
   request schema before a machine operation is reserved;
4. capture immutable per-invocation request bytes and, for source-reading
   completion, immutable pre-invocation candidate bytes.

No new scientific rule may be added in this slice. A model content error after
an exact, complete diagnostic is evaluation evidence, not automatically an
engine defect.

## Deterministic acceptance

- a BOM-bearing and BOM-free representation of the same candidate produce the
  same canonical candidate/transaction identity;
- two leading BOMs, malformed JSON, duplicate keys, invalid models, and
  scientifically invalid candidates remain rejected;
- the exact failed pilot candidate remains rejected, but one response reports
  its force misbinding and both chain gaps;
- the V8 unwitnessed negative exception still cannot bypass any force-path,
  positive-readiness, or human-G1 condition;
- invalid free-text finish warnings fail at the public Codex request boundary;
- capture schema v2 never overwrites an existing evidence file and preserves
  exact pre-invocation request/candidate bytes, binds the candidate to the
  route/WorkPacket path and completion digest, and rejects evidence validity if
  that source changes during execution;
- focused tests, all seven exporters, the routine non-long suite, `doctor`,
  compilation, and `git diff --check` pass.

## Real-pilot stop rule

After deterministic acceptance, freeze a new commit, wheel digest, clean
non-cloud root, skill, case, capture helper, and evaluation key. Then run:

1. one fresh ordinary-model blind rerun of the same public case;
2. one fresh ordinary-model blind run of a held-out framing case.

Close this stabilization stage when both runs have no transport/encoding
interference, return complete repair diagnostics when rejected, preserve human
authority, and either commit an honest route-valid output or expose a genuine
model-content failure. Do not create V9 merely because an ordinary model makes
a clearly diagnosed content error. A new scientific route version is warranted
only if acceptance semantics themselves must change.

This stop rule closes only the host-stabilization stage. It does not close the
V8 scientific pilot gate or authorize the v1/v2 comparison. The same public
case must still produce a canonical audit commit and undergo independent
economics inspection before that scientific follow-up begins; a clearly
diagnosed model-content failure in either run remains evaluation evidence, not
a reason to keep changing the host or scientific contract.

For a source-reading completion capture, invoke the helper with the exact
candidate path as well as the usual request and output paths:

```text
python capture_codex_invocation.py ... --request REQUEST.json \
  --candidate-source .econ-theorist/staging/RUN_ID/candidate.json \
  --stdout OUT.json --stderr ERR.txt --metadata META.json
```

Use an ordinary/medium model for the two generator runs. After each output is
frozen, use a separate high-intelligence task for independent economics and
reader-burden adjudication.

## Attempt-2 checkpoint

The corrected-wheel same-case rerun at `C:\tmp\etai-v8-r2` completed under
engine commit `4804323a84829247a88ae2f5e315538a331037fd` and wheel SHA-256
`09c620566505acea8e5ab698fff32e56f9197b71d336abbed9c9a419769ce22b`.
It committed framing and primitive decomposition, then returned three specific
candidate diagnostics before recording `failed_no_effect` with no audit
transaction and no G1 decision. Capture binding and integrity checks passed.

This satisfies the same-case host-stability branch by exposing a genuine,
bounded model-content failure without transport or encoding interference. It
does not satisfy the separate scientific requirement for a canonical audit
commit. Independent cold-reader and economics adjudication are pending, and
the held-out ordinary-model run remains required. See
[`rerun_attempt2_run_report.md`](rerun_attempt2_run_report.md) and
[`rerun_attempt2_postflight_manifest.md`](rerun_attempt2_postflight_manifest.md).
