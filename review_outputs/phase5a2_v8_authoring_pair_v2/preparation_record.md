# Held-out V8 semantic-authoring V2 pair preparation record

Status: frozen and ready for two independent generator tasks. No model
generation, bridge call, candidate completion, canonical candidate commit, or
human gate occurred during preparation.

## Exact evidence bindings

- Pair root: `C:\tmp\etai-v8-liability-pair-a03d102-c4e91b72`
- Engine commit: `a03d1025ac9c9bcaefcd112de3e8c63694b97c8f`
- Wheel SHA-256:
  `061d505a5e0afa21604a52d7d1b298c92d852c24ca8f63d4bc45122a22dab01f`
- PRE manifest SHA-256:
  `6af4a71cb19f1da11d38eb710fc1d68debb4403946dc4d46c541c450d18137a3`
- Transaction arm manifest SHA-256:
  `ff154517e8890ab4aa2d4a536df97edfbd324756a4c12ec9a95a8bdd7941c375`
- Semantic V2 arm manifest SHA-256:
  `4c5104cf8c601e7b445d1352ae76a19abcc163ebf4f28fa2f97ba6cce123c067`
- Runtime manifest SHA-256:
  `adf910c7b3fa57b2cc77e46f4751dddd76b003ff2d778c178e6f3f35d9ef351b`
- WorkPacket SHA-256:
  `040a11df181e705d6d46e822f4d82c2ce44cdeefb02dfa3c3255e9659fe9dfec`
- Candidate authoring contract SHA-256:
  `cfdfab5deb6fdc71335a33a1da14c8cd0e5f9675ac1077c4c020af307b16b755`
- Frozen Snapshot SHA-256:
  `27833c22751cca10cef81e2c4f12f08a47221fbda1580bd9605d1bf510a0cedc`
- Base head:
  `dde1542e2916cce2a2a0c76dfbd14b4ea0b715c451c014727403390b2fe66d68`
- Evaluator-key SHA-256:
  `3ee1ac219d518ddb2905fe84c590bec65f0d0f3e87ea90dbd2193506a37cedcd`
- Shared CASE SHA-256:
  `c1d5beb75af55615108092cda2db472e2c62b8d419b234b46352ea744a6ea358`
- Oracle scientific-projection SHA-256:
  `714b5654f18400cc53d12b67afaae6d1a59d0e4f1b455fc2a62b70b7cef7fa9b`
- Frozen order: `arm-transaction`, then `arm-semantic` (`semantic_v2`).

## Preparation checks

The external PRE verifier and both arm verifiers passed. The two arms have
byte-identical CASE and WorkPacket files, and the semantic surface is exactly
`econ-theorist/framing-audit-semantic-authoring-surface/v2`. The evaluator
key remains only in this exact repository commit and is bound by its hash; it
is not present anywhere in the pair workspace.

The private Transaction and Semantic V2 oracles both passed the unchanged
registry-V8 validator and produced the same scientific projection. Canonical
writes were zero, the canonical head was unchanged, and a deliberately wrong
base revision failed closed as `wrapper_or_binding` with zero writes.

Twenty-six focused semantic-authoring, harness, and new-case oracle tests
passed. The framing-quality schema exporter and `git diff --check` passed.
The routine non-long suite and the other six exporters were not rerun for this
noncanonical preparation-only slice; the slice changes no canonical schema,
registry, instruction, route validator, or public bridge path.

## Next execution

Use the same ordinary/medium model class in two genuinely independent new
tasks and follow the exact `OPERATOR_HANDOFF.md` under the pair root. Open
both tasks before reading either result, execute them in the frozen order, and
return only after both reports are immutable. High intelligence is reserved
for the later blinded economics and cold-reader adjudication.

Older `C:\tmp\etai-v8-*` directories remain unchanged. They are prior raw
evidence and are not an input to this pair; a fresh root and manifests provide
the required isolation without deleting them.
