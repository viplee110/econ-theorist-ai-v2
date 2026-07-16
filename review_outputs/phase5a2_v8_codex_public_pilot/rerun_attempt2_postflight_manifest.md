# V8 post-stabilization rerun attempt 2 postflight manifest

Status: **generator evidence frozen; cold-reader package frozen and unrun;
economics-evaluator package waits for the reader retell**

## Treatment and state

The treatment remains the exact commit, wheel, registry, skill, CASE, and
capture helper bound in [`rerun_preflight_manifest.md`](rerun_preflight_manifest.md).
No engine or scientific-contract bytes changed during this run.

- generator root: `C:\tmp\etai-v8-r2`;
- engine commit:
  `4804323a84829247a88ae2f5e315538a331037fd`;
- wheel SHA-256:
  `09c620566505acea8e5ab698fff32e56f9197b71d336abbed9c9a419769ce22b`;
- final canonical head:
  `467a15616763fc5859ca7128893b187599a5e813d1dde8b5b5e968c3d2d60535`;
- canonical transactions: three, including genesis;
- effective Decisions: zero;
- audit transaction: none;
- audit finish: operational `recorded_failure` with
  `completion_status=failed_no_effect`.

## Compact source-evidence bindings

All paths in this table are relative to `C:\tmp\etai-v8-r2`. SHA-256 values
bind file bytes, not the engine's canonical JSON identity unless explicitly
identified as a transaction digest.

| Evidence | Bytes | File SHA-256 |
|---|---:|---|
| `CASE.md` | 2,992 | `0efac3ad9a3832726903a4ebdedd4a5dbbc3f0fd8da36af792d39011b88a8551` |
| `run/20260717-consumable-quality-certificates-agent-report-corrected.md` | 8,286 | `2e4c1f0fbf1842d24308b9c035fddf7d3fedde3dd2b3502aef96b674fd004a94` |
| `run/20260717-004-complete-metadata-captured-candidate.json` | 17,945 | `cab8722e588377d97449d97a0cabb0dbd13d96910aa45fb7fe2dca30046513f2` |
| `run/20260717-004-complete-stdout.json` | 1,463 | `a6ee0f8c1383a70fcdcfd4ac0f373a65988d7763f44698a4141127b60c6f8055` |
| `run/20260717-004-complete-metadata.json` | 3,101 | `a041c04c3b8c6f3ce9cac41dafa3593c5702c9872ca3b8bb6aeb6de9fa7a3324` |
| `run/20260717-008-decompose-complete-metadata-captured-candidate.json` | 20,175 | `0452e0be1e9c233e21f7f9771f477913a2fd71e3e007f19297719dcd28c0c8a6` |
| `run/20260717-008-decompose-complete-stdout.json` | 1,353 | `547af369af5d8c2db96594680ce29d66a959b52e0672f77aad3ba31e5bc475ae` |
| `run/20260717-010-decompose-repair1-metadata-captured-candidate.json` | 20,056 | `6c7bf4991e6eec2534b964d6890ba934cda6d2be499b5d489a5e1f167160a7c0` |
| `run/20260717-010-decompose-repair1-stdout.json` | 726 | `98a60a731238adbfc34603f47e863a4a7bc9a9baad04bd2e7584cfd57ed267e0` |
| `run/20260717-012-decompose-repair2-metadata-captured-candidate.json` | 20,141 | `d8352327650c6040bf5487667d87440d372a09620dc5a39897c11a8fb1883e01` |
| `run/20260717-012-decompose-repair2-stdout.json` | 1,463 | `a84688d0fba6dd6fafb74a957963a0d9db28ea80a6d9253c0b0c77c6a76cd66e` |
| `run/20260717-012-decompose-repair2-metadata.json` | 3,173 | `020c844b7219d3635442412e78a937044ef123d97e568ce119600795e80e0769` |
| `run/20260717-016-audit-complete-metadata-captured-candidate.json` | 41,423 | `3c0cc4cd7e5749983a132bab9488d91298c245258cab01ddd0b67c3718fac44d` |
| `run/20260717-016-audit-complete-stdout.json` | 1,269 | `e990bedb0f27761ab01537ffcba84cf794f87bf24ee4180fd3588f0cfad15ec5` |
| `run/20260717-016-audit-complete-metadata.json` | 2,981 | `86ed61992e9d60c7e1694081ec7d8935ffab08454b72dc634c1fad3bdfe61e18` |
| `run/20260717-018-audit-repair1-metadata-captured-candidate.json` | 41,431 | `c64de6b3e30a7d2db6e414d7e4b8791e3dc4697b7f7abbcc2e7f9d0ca2577b58` |
| `run/20260717-018-audit-repair1-stdout.json` | 785 | `3958b9288431d8c8a6c4f56e6af52fcd5f590d78e29943aa55596022405c52f2` |
| `run/20260717-018-audit-repair1-metadata.json` | 2,972 | `d4601ed8979c34ba041b5b5f9cd21c1b787ba286d1e4bbbd657f1fefbbd69b14` |
| `run/20260717-020-audit-repair2-metadata-captured-candidate.json` | 41,447 | `405d0c38b658309cb2730deb3f8434558c6ce3629e7a84a31f61d26b0071b979` |
| `run/20260717-020-audit-repair2-stdout.json` | 747 | `d257220da1d40c6fc725da3fc115b4eaa2744f985ab7bb10309eaf36c3905929` |
| `run/20260717-020-audit-repair2-metadata.json` | 2,972 | `4dd2a43202ff3ed55b90ea31654a92601de2340eb5202a0fa19c6545028dd850` |
| `run/20260717-021-audit-finish-request.json` | 576 | `efdc398c892365716201d230eff05c947b4e54ce22606abbcdf7a288404bfeed` |
| `run/20260717-022-audit-finish-stdout.json` | 1,413 | `a0fe4cf272a20fdae2d39a548f5269cec2a2922c722c50ebf4ec9b3e115c0f40` |
| `run/20260717-022-audit-finish-metadata.json` | 2,691 | `5d9c8fc0a7a71ce92632793bf664b64b2e1118f750e5144467ff8b1066e750c4` |
| `.econ-theorist/refs/main` | 64 | `b68b0367d4225204256ebe4c7c740804a800ed960e37b734a3ad3a9d36c00068` |
| genesis transaction bytes | 1,500 | `2f6ae15bbf9c71825ea2b848c884b1139c9c1cca94a63fad9b35d5aa83799c5f` |
| frame transaction bytes | 14,596 | `73fb8d5bc47f3c21d17228e76edb8300fbc537224bf896f2ebe01a52f57adf1c` |
| decompose transaction bytes | 14,636 | `467a15616763fc5859ca7128893b187599a5e813d1dde8b5b5e968c3d2d60535` |

The captured frame and decompose source-file hashes differ from their
transaction digests because the engine computes canonical identity from strict
JSON. Their capture metadata record the canonical digest before invocation and
`candidate_digest_matches_response=true`.

Every listed capture metadata object reports `response_valid=true`, no capture
error, no response-binding error, and unchanged request/candidate bytes for
the invocation. The final audit metadata has no commit digest match because
the candidate was rejected.

## Frozen evaluator-only key

The unchanged key remains:

- repository path: `frozen_evaluation_key.md`;
- bytes: 4,881;
- SHA-256:
  `96c506f89ce8da0a976b51408f774cebb305c32ad8d12413603453c633cfd22f`.

It was unavailable to the generator. It is also absent from the cold-reader
package.

## Cold-reader package

Root: `C:\tmp\etai-v8-r2-reader`

| File | Bytes | SHA-256 |
|---|---:|---|
| `MANIFEST.md` | 1,886 | `4158405c21f0d40c9d22c73ae0c6f78ce02edd0019e98d1f4e625387287eca09` |
| `READER_PROMPT.md` | 1,415 | `28ad053e88c7f9ee87a1f5b59c21f13106f601d78ff9db5d21356e33c5948f2e` |
| `evidence/economist_memo.md` | 1,452 | `3f7ee3ef1111c20f999d5a47d889e3650db3998ea5bb8d880740aba4c0ad7f48` |

The memo preserves all nine source `economist_memo` fields under whitespace
normalization. The package inventory contains only those three read-only files
and an empty writable `report/` directory. It contains no key, probe, CASE,
upstream object, candidate, diagnostic, generator report, source, test,
registry, wheel, `.git`, `.agents`, `.venv`, or operational/host state.

The economics-evaluator package is intentionally not final until the reader
retell exists and its bytes are frozen. This prevents a task that already has
the answer key from manufacturing the purported cold-reader evidence.

## Claim boundary

This compact repository record does not copy the raw R2 operational store or
WorkPackets into Git. The exact local evidence remains in the isolated root.
The record establishes treatment identity, two canonical commits, capture
integrity, a diagnosed uncommitted audit failure, unchanged human authority,
and the inputs for independent evaluation. It does not establish A-SUCCESS,
R-PASS, low human burden, research readiness, a validator defect, or v1/v2
superiority.
