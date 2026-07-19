# Frozen generator evidence: V8 authoring pair v2

Frozen at `2026-07-19T10:57:31.6397090Z`, after both independent generator
arms had stopped and before either report, receipt, attempt, or the
evaluator-only key was opened for substantive adjudication.

## Integrity checks

- PRE manifest: `6af4a71cb19f1da11d38eb710fc1d68debb4403946dc4d46c541c450d18137a3`
- Transaction manifest: `ff154517e8890ab4aa2d4a536df97edfbd324756a4c12ec9a95a8bdd7941c375`
- Semantic V2 manifest: `4c5104cf8c601e7b445d1352ae76a19abcc163ebf4f28fa2f97ba6cce123c067`
- Every file listed by the PRE and arm manifests was independently rehashed
  and matched its frozen byte count and SHA-256.
- The repository evaluator-key digest still matched
  `3ee1ac219d518ddb2905fe84c590bec65f0d0f3e87ea90dbd2193506a37cedcd`.
- No exact copy of that evaluator-key digest appeared on the mutable pair
  surface (top level, arms, launch, private evaluator, task metadata, or Git
  metadata). The frozen runtime was covered by the PRE-manifest recheck.
- The original PRE/arm verifiers intentionally reject post-run unlisted
  outputs. Therefore the post-run check reapplied their byte/hash checks to
  every listed frozen input without applying the pre-run no-extra-output rule.

## Frozen output artifacts

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `arm-semantic/report/agent_report.md` | 1236 | `8c70d7564be88c313a6ef57a2125e3d4e87bc1958f4e0fd9812eb09e0ea8ca82` |
| `arm-semantic/work/attempt_01.json` | 16556 | `ef5577b90ab179670d0d0e8e77f4c5b90eba23a34622871dc0485e51aaaaccb4` |
| `arm-semantic/work/attempt_01.receipt.json` | 1905 | `5568926ae2ae44acbb673e2f55fecc4c46fe0bc5ab2cd393ca608e1644053ef4` |
| `arm-semantic/work/attempt_02.json` | 13604 | `7b968b9ed32d2b2a6972026a2a367212c540a60aa0ebbcc0a0aff051e7fa44fd` |
| `arm-semantic/work/attempt_02.receipt.json` | 1373 | `64cc61e5d0160577536e9014f9b6a5771bcdc56b9606f3c9d24bcce9e4a988a4` |
| `arm-semantic/work/attempt_03.json` | 10922 | `8545c31863bbb6b995971e6f8cc1f2014a6d853db71b7ff34730d7d7a2629bfe` |
| `arm-semantic/work/attempt_03.receipt.json` | 1351 | `a685b73c74b844be569a63a2cb4b40fe79e7b5a5a046d96fa3a46b1aee7286e4` |
| `arm-transaction/report/agent_report.md` | 1387 | `9a92fface6f99d81a4580133eede6cb9e8c94c89802f8a719c26aa6babfc003e` |
| `arm-transaction/work/attempt_01.json` | 22381 | `e9929dedced6f3aa6e6bfb1c73f5c57875d4142cba46fd2a804a7396fe2dfe3b` |
| `arm-transaction/work/attempt_01.receipt.json` | 1409 | `c7b449ac75795fd09e041d152a7770509a5c1754241480de0dc3c447b2a0f834` |
| `arm-transaction/work/attempt_02.json` | 22435 | `4c9f9bb8b49f7a54417cd8cfcf341d7c7cda0918359a1e3d15356c36516de430` |
| `arm-transaction/work/attempt_02.receipt.json` | 1348 | `af41d718948b50615f316dd6ba96b23828de1efb10724d87713f20bfe60e1663` |
| `arm-transaction/work/attempt_03.json` | 22391 | `ee6a52c56e036c82f75ee26c80517c6c0f913cbd72acea7932358d876c046d08` |
| `arm-transaction/work/attempt_03.receipt.json` | 1471 | `491dcca7260fd0b1483f4c9305d334c0148e753c2c5ac30f0f7773900699df18` |

The aggregate is SHA-256 over sorted lines of
`relative_path<TAB>byte_count<TAB>sha256`, joined with LF and encoded as UTF-8
without a BOM.

- All 14 generated artifacts: `11ac8cec806dfa9b78faa03d911eeb06cceba73d1b866593462033d3dda244e6`
- Transaction generated artifacts: `79a1f0916a1809982149c08fe44abf7336bcda9942c5e696c996a7a872fb6dc5`
- Semantic V2 generated artifacts: `1d52439a826cec3809a5206ea7b7469504cba0af52922ba49e0093be3457f5ec`
- All 30 files under both arms: `8c4db00efec416dd8e28399bb6864b68b04640331589e00e266183816c894eb1`

No canonical write or human gate is authorized by this evidence freeze.
