# V5.4 pilot preflight manifest

Captured: 2026-07-15, before the first generator or bridge invocation

Clean root:
C:\tmp\etai-v5_4-public-pilot-20260715-c8c539e

Environment construction: Python 3.12.10 venv with
system-site-packages, followed by offline wheel installation with
no-index and no-deps.

## Frozen protocol and generator input

- protocol: 15,043 bytes; SHA-256
  F2FE184C84D931624E3C3927C504A7866B16C1A5C09B12557B58B099E3C75403
- independent evaluation key: 8,264 bytes; SHA-256
  BACF343F919DC2BCEFCFE132F180D81A2ABD6AAEC6C6251711CD22F0825E283F
- complete generator CASE: 2,994 bytes; SHA-256
  C26BE82FA643D702F13DE113847B2CD93D4E5C57B54DF8D72B09A6470AFFAB75
- Research seed block: 1,237 UTF-8 bytes; SHA-256
  7EBD071530BD591D7B689A5946132AAF2007F817632A65FC1CC8F3A2F46CD2CB

The protocol and evaluation key are outside the clean root. The generator
receives only the unchanged CASE and cannot access either evaluator document.

## Frozen implementation and distribution

- implementation commit:
  c8c539e6b81404cfcd1eb247956b626f4b18ef2f
- implementation branch: agent/research-first-audit-repair
- distribution: econ_theorist_ai-0.1.0-py3-none-any.whl
- wheel bytes: 687,580
- wheel SHA-256:
  DB549E9F0203885B7A13ACE59A9D2A2D855167A9A257B90AEE99B0DEF5CAB7B2
- offline build backend: setuptools 83.0.0 and wheel 0.47.0 from the
  existing local build-deps directory
- wheel archive entries: 231
- wheel uncompressed bytes: 3,590,982

The wheel contains no tests, review_outputs, old pilot candidates, failure
reports, economics audits, or reader audits. It contains the unchanged core
module econ_theorist/gold_cases.py, 15,873 bytes with SHA-256
E7ED53D57ECBABFE03CEEA37ADCD3117F5E7183CEC8B400E90043DF10C67CDD7.
That module has no certificate, consumable, depletion, inspection, buyer,
seller, or search match, has no diff from main commit 674ef0e, and is installed
source that the generator is explicitly prohibited from reading.

## Frozen active resources

- Route Registry R7 canonical digest:
  a8b50155a4a9f2656b8890f6f6cc7c2ce4085a49bb52086f19c11cb0b1e12f50
- Route Registry R7 raw-file SHA-256:
  BBC6A03FA93970DD6D7C90491511A287C9FFEEFAC1F036E893C70503AE07A84A
- Navigation N6 canonical digest:
  94520d9626e702fde479be0184bbc5baa3cc25dce9c8f65e1d935064923f826f
- Navigation N6 raw-file SHA-256:
  702E51A3EC01B4A1DD343467D0819DF9AD1AB011994E872546A6DE9E9A4F920F
- audit.framing_economics.v7 instruction SHA-256:
  E57A770DB8F111DD51B8B752DB521F19602221BA60CF03D31F3065134820DF1C

Installed-wheel doctor reported required_ok true, Python 3.12.10, Pydantic
2.13.4, pydantic-core 2.46.4, and active Route Registry R7 with 35 of 35
routes enabled. Lean and Node are optional and unavailable; they do not block
the theory core.

## Verification completed before distribution freeze

- final cross-module joint regression: 119 of 119 passed;
- post-review research-flexibility regression: 22 of 22 passed;
- candidate contract, archive, and bridge focused suite: 17 of 17 passed;
- complete framing real-store route regression: 29 of 29 passed;
- cross-phase frozen compatibility checks: 31 of 31 passed;
- broad routine non-long regression: 581 tests passed, 6 skipped, 0 failed,
  with the Phase 2, Phase 3, and Phase 4 hour-scale gold chains excluded;
- all seven schema and resource exporter checks passed;
- doctor unit tests: 3 of 3 passed;
- installed-wheel doctor required_ok: true;
- Python compilation and git diff --check passed; and
- independent final integration review found no remaining P0, P1, or P2 issue.

The excluded long gold chains were not rerun. Historical resources remain
addressable and the non-long compatibility suites passed, but this manifest
does not substitute those checks for a fresh hour-scale gold-chain claim.

## Clean-root inventory before generation

Top-level entries are exactly:

- .agents/
- .host-state/
- .venv/
- distribution/
- run/ (empty)
- capture_codex_invocation.py
- CASE.md

The virtual environment contains 1,162 files totaling 18,095,562 bytes. The
scientific and runtime inputs outside .venv are exactly:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| .agents/skills/econ-theorist-v2/SKILL.md | 4,938 | 4EE147E92ABC591D4D22D1CD80AADE47DBF34A9D0351D1ED4026C27F67A7C5A1 |
| .agents/skills/econ-theorist-v2/agents/openai.yaml | 296 | D0DB034C3C93616CB42390DF90343F13A45F81AF6CBE48D4B678FC54E0E09C17 |
| capture_codex_invocation.py | 10,910 | 017D941665D3220C3F50885F08AE4D4AF38979F67C8267C0B9CF3C64CE40D519 |
| CASE.md | 2,994 | C26BE82FA643D702F13DE113847B2CD93D4E5C57B54DF8D72B09A6470AFFAB75 |
| distribution/econ_theorist_ai-0.1.0-py3-none-any.whl | 687,580 | DB549E9F0203885B7A13ACE59A9D2A2D855167A9A257B90AEE99B0DEF5CAB7B2 |

The skill, capture helper, CASE, and seed hashes are identical to V5.3. A
corrected pre-generation credential-signature scan over all non-venv,
non-wheel clean-root files found zero matches. The initial broad scan produced
one false positive from the substring in an SPDX license identifier inside
the venv; the boundary-corrected scan excluded the venv and returned no match.

No repository source checkout, tests, prior pilot output, evaluation key,
literature file, reference answer, or audit report was copied to the clean
root. No generator invocation has occurred at the time of this manifest.

## Go decision

The frozen implementation, distribution, protocol, evaluator key, generator
input, and clean root satisfy the pre-generation conditions. Any subsequent
implementation or generator-input change invalidates this freeze and requires
a new wheel, hashes, and protocol identity.
