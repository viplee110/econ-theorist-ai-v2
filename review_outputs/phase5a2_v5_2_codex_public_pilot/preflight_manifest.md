# V5.2 pilot preflight manifest

Captured: 2026-07-15, before the first `etai` invocation
Clean root: `C:\tmp\etai-v5_2-public-pilot-20260715`
Python: `3.12.10`
Environment construction: `venv --system-site-packages`, followed by an
offline wheel installation with `--no-index --no-deps`

## Frozen source and distribution

- source commit: `cd018e54ffa8b8645058ff993562acec0fdf4807`
- distribution: `econ_theorist_ai-0.1.0-py3-none-any.whl`
- wheel bytes: `651448`
- wheel SHA-256:
  `D0E59192A629A6BC3DCCD513E71D9CDEAA6DE68D495F4D593E1B45C3FF54E317`
- offline build backend: `setuptools 83.0.0`, `wheel 0.47.0`
- active navigation policy canonical digest:
  `4027c38ffbc43af55f2c8fc1fd6bdf634024e9b7a3cc1e88b426c20556634833`
- packaged navigation v4 raw-file SHA-256:
  `FDE0E81D9BC960EC7ABD73433546E68A387817DB5365BA8DAC74551C16B41C47`

## Clean-root inventory before first invocation

The only top-level entries were `.agents/`, `.host-localappdata/` (empty),
`.venv/`, `distribution/`, and `CASE.md`. The virtual environment contained
1,154 files totaling 17,765,830 bytes. Its scientific/runtime inputs outside
`.venv` were exactly:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `.agents/skills/econ-theorist-v2/agents/openai.yaml` | 296 | `D0DB034C3C93616CB42390DF90343F13A45F81AF6CBE48D4B678FC54E0E09C17` |
| `.agents/skills/econ-theorist-v2/SKILL.md` | 4,399 | `77C5B53B5247E503DCB1F3D1AC7954EACCC1F107FB193173C005118AC296B731` |
| `CASE.md` | 2,798 | `F61EE776FBB1FCAAC2A28EF53ED3B903433378D74AAD522E1F5C5045DFBE38FD` |
| `distribution/econ_theorist_ai-0.1.0-py3-none-any.whl` | 651,448 | `D0E59192A629A6BC3DCCD513E71D9CDEAA6DE68D495F4D593E1B45C3FF54E317` |

No source checkout, test, fixture, gold case, prior output, audit, reference
candidate, or literature file was copied into the clean root. The `Research
seed` block is 1,237 UTF-8 bytes with SHA-256
`7EBD071530BD591D7B689A5946132AAF2007F817632A65FC1CC8F3A2F46CD2CB`.

## Verification completed before the clean pilot

- focused navigation/bridge/skill checks: 26 passing;
- independent fix review: 15 passing and no material finding;
- complete routine non-long regression: 530 passing, 6 skipped, 0 failed;
- seven schema/resource exporter checks: passing;
- source-checkout doctor: `required_ok: true`;
- v3 raw SHA-256 remained
  `95064B65FA53EADD5E9A77AA039F255DF8A08E2C6B05C9769C77C1D7A670F226`;
  v4 differs semantically only in registry version and the decomposition
  default budget from 4,000 to 8,000.
