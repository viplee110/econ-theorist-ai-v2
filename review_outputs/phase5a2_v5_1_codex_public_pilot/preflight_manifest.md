# V5.1 pilot preflight manifest

Captured: 2026-07-14, before the first `etai` invocation
Clean root: `C:\tmp\etai-v5_1-public-pilot-20260714`
Python: `3.12.10`
Environment construction: `venv --system-site-packages`, followed by an
offline wheel installation with `--no-index --no-deps`

## Frozen source and distribution

- source commit: `51789a55d5dcbdeb70455f2fcdd3a33502efae92`
- distribution: `econ_theorist_ai-0.1.0-py3-none-any.whl`
- wheel bytes: `649898`
- wheel SHA-256:
  `0C16DAD616168C6781FBA28343CAEB9C2683B09118DA243A8589FAC8DC60D920`
- offline build backend: `setuptools 83.0.0`, `wheel 0.47.0`
- active navigation policy canonical digest:
  `fe285a46a1da5e1dd0f9c2953d0c6a6cf7474ff39129d53c5be96548548bf594`
- navigation registry v3 raw-file SHA-256:
  `95064B65FA53EADD5E9A77AA039F255DF8A08E2C6B05C9769C77C1D7A670F226`

## Clean-root inventory before first invocation

The only top-level entries were:

- `.agents/`
- `.host-localappdata/` (empty isolated operational-home parent)
- `.venv/`
- `CASE.md`
- `distribution/`

The virtual environment contained 1,153 files totaling 17,749,601 bytes. Its
scientific/runtime inputs outside `.venv` were exactly:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `.agents/skills/econ-theorist-v2/agents/openai.yaml` | 296 | `D0DB034C3C93616CB42390DF90343F13A45F81AF6CBE48D4B678FC54E0E09C17` |
| `.agents/skills/econ-theorist-v2/SKILL.md` | 3,976 | `4238AA882B5A82E38B979EBC6B0787A4EBBA6DA2673DBA132CDC3292898665F4` |
| `CASE.md` | 2,797 | `9B67D683141675F794292A6CF3F046E624E469F17860E0253F6185CD3C864FF2` |
| `distribution/econ_theorist_ai-0.1.0-py3-none-any.whl` | 649,898 | `0C16DAD616168C6781FBA28343CAEB9C2683B09118DA243A8589FAC8DC60D920` |

No source checkout, test, fixture, gold case, prior output, audit, reference
candidate, or literature file was copied into the clean root.

The `Research seed` block is byte-for-byte identical to the previous frozen
seed: 1,237 UTF-8 bytes, SHA-256
`7EBD071530BD591D7B689A5946132AAF2007F817632A65FC1CC8F3A2F46CD2CB`.

## Installed package snapshot

The engine's direct runtime set was:

- `econ-theorist-ai==0.1.0`
- `pydantic==2.13.4`
- `pydantic_core==2.46.4`
- `annotated-types==0.7.0`
- `typing_extensions==4.15.0`
- `typing-inspection==0.4.2`

The environment inherited other read-only packages from the verification
Python through `--system-site-packages`. They were not supplied as scientific
context. A console-encoding warning occurred while printing package metadata;
it did not alter the environment or invoke the engine.
