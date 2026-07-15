# V5.3 pilot preflight manifest

Captured: 2026-07-15, before the first bridge invocation

Clean root: `C:\tmp\etai-v5_3-public-pilot-20260715-f7f34ef`

Python: `3.12.10`

Environment construction: `venv --system-site-packages`, followed by an
offline wheel installation with `--no-index --no-deps`

## Frozen source and distribution

- source commit:
  `f7f34ef58dbe8af03592db02be617dfc9b403d40`
- distribution: `econ_theorist_ai-0.1.0-py3-none-any.whl`
- wheel bytes: `666145`
- wheel SHA-256:
  `8E2397055208AEB6424A6FF93E6B6476584D0E6A0437194B6FC7ACAA2D78CC0A`
- offline build backend: `setuptools 83.0.0`, `wheel 0.47.0`
- route registry v6 canonical digest:
  `532329cad6ce302f9f390f1d726fceee94560114c7fb9b3f6d5e2968486bcdde`
- navigation registry v5 canonical digest:
  `50b3943aa43aa989e33a27bef48eb6de66e41cf8048ff856fa2183397caa9a4c`
- packaged navigation v5 raw-file SHA-256:
  `7E3C47455D1FD951B81922D65FAB47587A6F0BC91941FF3A5CFADF4EADE7B2F7`
- audit instruction v6 SHA-256:
  `9BFC49B724B3AA0914D66431C37E988C0C67B3EFDEFFCA4003D5D81A4F9BC893`

Installed-wheel `doctor` reported `required_ok: true`, Python 3.12.10,
Pydantic 2.13.4, pydantic-core 2.46.4, and active route registry v6 with all
35 routes enabled. Missing Lean and Node adapters were optional and did not
block the theory core.

## Verification completed before the pilot

- complete routine non-long regression: 560 passed, 6 skipped, 0 failed;
- final affected contract/bridge/capture/skill suite: 28 passed;
- focused framing/model/registry/distribution suite: 59 passed;
- seven schema/resource exporter checks: passed;
- Python compilation and `git diff --check`: passed;
- archived V5.2 ready response: strict parse and byte-for-byte canonical
  reserialization passed;
- independent final reviews: no high or blocking finding.

The three hour-scale Phase 2--4 historical gold chains were not rerun. Their
frozen route, instruction, and navigation resources are byte-identical to
`main`; the additive current regression covered historical addressability and
the V5 golden response.

## Clean-root inventory before generation

Top-level entries were exactly `.agents/`, `.host-state/`, `.venv/`,
`distribution/`, `capture_codex_invocation.py`, and `CASE.md`.

The virtual environment contained 1,157 files totaling 17,900,453 bytes. Its
scientific/runtime inputs outside `.venv` were exactly:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `.agents/skills/econ-theorist-v2/SKILL.md` | 4,938 | `4EE147E92ABC591D4D22D1CD80AADE47DBF34A9D0351D1ED4026C27F67A7C5A1` |
| `.agents/skills/econ-theorist-v2/agents/openai.yaml` | 296 | `D0DB034C3C93616CB42390DF90343F13A45F81AF6CBE48D4B678FC54E0E09C17` |
| `capture_codex_invocation.py` | 10,910 | `017D941665D3220C3F50885F08AE4D4AF38979F67C8267C0B9CF3C64CE40D519` |
| `CASE.md` | 2,994 | `C26BE82FA643D702F13DE113847B2CD93D4E5C57B54DF8D72B09A6470AFFAB75` |
| `distribution/econ_theorist_ai-0.1.0-py3-none-any.whl` | 666,145 | `8E2397055208AEB6424A6FF93E6B6476584D0E6A0437194B6FC7ACAA2D78CC0A` |

The `Research seed` block is 1,237 UTF-8 bytes with SHA-256
`7EBD071530BD591D7B689A5946132AAF2007F817632A65FC1CC8F3A2F46CD2CB`.
No source checkout, repository history, test, fixture, gold case, prior output,
audit, reference candidate, literature file, or web material was copied into
the clean root.
