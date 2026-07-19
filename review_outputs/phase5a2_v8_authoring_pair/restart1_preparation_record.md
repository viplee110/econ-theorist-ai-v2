# Held-out V8 authoring pair restart 1

Status: frozen and ready for two genuinely independent generator tasks; no
model generation or scientific adjudication has been performed on this restart.

## Why the prior pair is not evidence

Both arms under `C:\tmp\etai-v8-pair-ecc1853` were executed in one Codex task.
That permits cross-arm conversational context even if the filesystem arms were
separate. The two reports are therefore classified as
`INVALID_SINGLE_TASK_CONTEXT` and must not be compared or scientifically
adjudicated. The old directory remains unchanged as process-failure evidence;
its candidate and report contents were not inspected during this restart.

## Fresh evidence bindings

- Pair root: `C:\tmp\etai-v8-pair-restart1-1d9a2e9`
- Engine commit: `1d9a2e9e2c086a821e168ba50a235459d121734b`
- Wheel SHA-256:
  `5db9c8975bff320ee4be0797b3727f13e1637b063e24b4761b9005161d2f09db`
- PRE manifest SHA-256:
  `df63df0ad255eb0b149e1008ccc5d0d6dd2c45ab4e36e13f3cac5ce3ef64974a`
- Semantic arm manifest SHA-256:
  `952b994104acbe00f5d688d1faef6ebc776e278733016c13a84bc86c098c52f7`
- Transaction arm manifest SHA-256:
  `75a20c9a083a8649553e189a36c9a21c30a4c8588575c552f25ca10a0dd77fa4`
- Runtime manifest SHA-256:
  `2c5746e5a663cb06cab246c7b94886af7d2b6375f7b1449568a798fe24ec6a7b`
- WorkPacket SHA-256:
  `7991cea0354ccca8129ffac90bc904ad75db03f300976309f5c94ed09ae060cc`
- Candidate authoring contract SHA-256:
  `6e61dd5cb11a70d4181a1e89ccc459c6473627dafdb38793ec0b78c2b30cc1f5`
- Frozen snapshot SHA-256:
  `cc7b8196bed5607bc57478f5898e5c9374f678d938cc49f7a1eb2001a37f456a`
- Base head:
  `827c7232cfc0ea00389aeafc036f5ae76c3e37da7448ec9d9e0b5db81e36e907`
- Frozen execution order: `arm-semantic`, then `arm-transaction`.

The PRE verifier and both arm verifiers passed against these external hashes.
The private preparation oracle passed the unchanged V8 validator through both
interfaces with the same scientific projection and zero canonical writes. The
base-mismatch self-test also failed closed with zero canonical writes.

## Required launch isolation

The operator must manually create two separate Codex tasks before either task
opens an arm. One task receives only `launch/arm-semantic.md`; the other receives
only `launch/arm-transaction.md`. A task must not create, fork, delegate, or
execute the sibling arm, and neither result may be relayed to the other task.
Both tasks use the same ordinary/medium model and use the fresh pair root as
their workspace root.

High intelligence is not required for the two generator runs. It is reserved
for the independent blinded economics and cold-reader adjudication after both
reports are frozen.
