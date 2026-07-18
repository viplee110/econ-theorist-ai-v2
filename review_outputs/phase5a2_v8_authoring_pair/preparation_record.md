# Held-out V8 authoring pair preparation record

Status: frozen and ready for two generator tasks; no model generation or
scientific adjudication has been performed.

## Exact evidence bindings

- Pair root: `C:\tmp\etai-v8-pair-ecc1853`
- Engine commit: `ecc18534be7083a2a061121dc36044a0fe240104`
- Wheel SHA-256: `a20d874b528698d5359e30c167e98e0cff179f0202fe98bfd826cfb7bb5b718c`
- PRE manifest SHA-256 (external root anchor):
  `96dae6d531db549679dbbcdd6a78641fb7b7730c34054d3644cc032f3b79b5de`
- Transaction arm manifest SHA-256:
  `7621de81635a0390f63a6b62a80c5645a0447a3c287b04a18b3923417a3793b8`
- Semantic arm manifest SHA-256:
  `9381ee4c8349513e4ef717806c94f3e397cb1a96e69a8da56e239ad28f4ddb15`
- Runtime manifest SHA-256:
  `a411e50b824c4542451bf8df613cb1065fbceef4cbd233500b562184f0bdd809`
- WorkPacket SHA-256:
  `7991cea0354ccca8129ffac90bc904ad75db03f300976309f5c94ed09ae060cc`
- Candidate authoring contract SHA-256:
  `6e61dd5cb11a70d4181a1e89ccc459c6473627dafdb38793ec0b78c2b30cc1f5`
- Frozen snapshot SHA-256:
  `cc7b8196bed5607bc57478f5898e5c9374f678d938cc49f7a1eb2001a37f456a`
- Base head:
  `827c7232cfc0ea00389aeafc036f5ae76c3e37da7448ec9d9e0b5db81e36e907`
- Frozen execution order: `arm-transaction`, then `arm-semantic`.

The exact PRE verifier and both arm verifiers passed against the hashes above.
The runtime omits only the unused pip-generated `bin/etai.exe` console
launcher; the omission is recorded in both runtime and PRE manifests. Every
installed Python module byte matches the clean checkout, and the frozen wheel
matches the WorkPacket engine semantics and registry-v8 binding.

## Private preparation checks

The evaluator-side oracle compiled through both surfaces and reached the same
scientific projection SHA-256:
`802671110e48fd2dbd0bc2d4fef247b40c82edcda000f27d016737d3662d8948`.
Both oracle candidates passed the unchanged V8 validator with zero canonical
writes. A deliberately wrong base revision produced an immutable failed
receipt classified as `wrapper_or_binding`, rather than a harness crash.

No bridge call, candidate completion, canonical commit, human gate, network,
subagent generator, or provider claim occurred during preparation.

## Verification scope

- 13 focused semantic-compiler and shadow-harness tests passed on the exact
  engine commit.
- `scripts/export_framing_quality_schemas.py --check` passed, confirming no
  canonical framing schema drift.
- `git diff --check` passed before the preparation record was added.
- The 594-test non-long suite and the seven-exporter sweep were not rerun for
  this bounded experiment-preparation slice.

The two generator tasks must use the same ordinary/medium model and the pair
root as their workspace root, while working only in their assigned arm. High
intelligence is reserved for the later blinded economics and cold-reader
adjudication after both generator reports are frozen.
