# Frozen Phase 1 v1 byte oracle

`canonical_bytes.v1.json` is an archival container. Its five base64 values
decode to the exact canonical bytes below; the base64 envelope is used so that
Git, editors, and patch tooling cannot add an end-of-file newline to a
canonical JSON payload.

| payload | bytes | SHA-256 |
|---|---:|---|
| `genesis_transaction` | 1362 | `717c037bbc9fa38e403b4de4c59790898fb58eaa1b0a6760066ad0f721ee037e` |
| `framing_run` | 616 | `60b0fd7c0f4641837406fb4a0d700285d8655fa4322c25844485f2d993b1f73e` |
| `framing_manifest` | 1356 | `358d85b700895b43958701d346919b19324401ba0cdba3d606a567a5d170a1b6` |
| `framing_compiled_context` | 2762 | `fa1e3dc8acba5e40228e9430cb0df5ea802116196f24c75dbdcc27b2c66c6c1a` |
| `framing_transaction` | 1679 | `bc39706b06541436b0bc75dcd09933e3f1e423717a92e4e1d98f2501dcd52900` |

The source is a one-time deterministic construction under frozen registry v1
hash `d9c84001420bd63a82418ee3cfe1776895be69936e921aa8c4790a8966aa6913`
and the pinned Pydantic 2.13.4 / pydantic-core 2.46.4 validator:

1. A literal genesis transaction creates
   `project.phase1.frozen.bytes@1` at `2026-07-11T00:00:00Z`.
2. `compile_context` compiles the v1
   `frame.question_and_benchmarks` route at that exact genesis revision with
   literal run/manifest IDs, timestamp, actor, compartments, and a 4000-unit
   budget.
3. A literal v1 route transaction creates the generic, deliberately untyped
   `question.phase1.frozen@1` envelope and binds the three exact provenance
   hashes.
4. `transaction_bytes` serialized the two transactions;
   `canonical_json_bytes` serialized the run and manifest; the compiled
   context is the exact `CompiledContext.encoded` value.

No temporary directory, absolute path, generated ID, current clock value, or
machine-specific field appears in the decoded bytes. The temporary directory
used during construction only hosted the content-addressed store.

These bytes are a compatibility oracle, not a regeneratable snapshot. Do not
replace them or their expected hashes to accommodate a code change. If a
future implementation cannot read, hash, reproduce, and replay them exactly,
the implementation needs a versioned historical reader or an explicit
migration design while these bytes remain unchanged.
