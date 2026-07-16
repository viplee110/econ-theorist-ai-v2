# V8 public Codex pilot preflight manifest

Status: **complete before generation; no generator or bridge invocation has occurred**

## Scope and provenance

This manifest freezes the distribution and generator-visible inputs for the
V8 public negative-diagnosis pilot. The engine-code baseline is commit
`45a540ba06591055fef4f7e543f1a8eafdf4681e`; the protocol source checkout was
commit `179cd6f`, whose changes are pilot documentation and inputs rather than
engine implementation. The exact installed wheel, rather than either commit
label alone, is the executable treatment.

The final clean generator root is deliberately not created from this source
checkout. It will be a new, non-cloud directory outside the repository and
will contain only the generator-visible inventory named below. The protocol
and evaluation key remain outside that root.

## Frozen distribution and active resources

- wheel: `econ_theorist_ai-0.1.0-py3-none-any.whl`;
- wheel bytes: 699,569;
- wheel SHA-256:
  `dad56a86b8863ca63cf7bae3b37da5bcacabeee66cf99c1ea5ad71f7a9f3854d`;
- Route Registry V8 canonical digest:
  `5d2c2efdef205ee1ff188249dcb05cb5a4430d36ef754a93bde402a092aa40c1`;
- Route Registry V8 raw-file SHA-256:
  `77c9ea3a50eb6cc0e5c87072168ebb7db39eb031fe5a96cc484b6ea0dba74409`;
- Navigation Registry V7 canonical digest:
  `ea133669cd85c073b6352744f2d1b5413dfe33d738752ad17769637acfd9e510`;
- Navigation Registry V7 raw-file SHA-256:
  `2fcb7d84691f65b7f8dfcffb42ad71aff0469df184380bb0bd5ca926b4cfdb00`;
- `audit.framing_economics.v8` SHA-256:
  `1f5dd361a0d8ac0c117cc587c541d5dc3e750c38ed0ba1d7e172432b10b971f0`.

## Frozen pilot materials

| File | Bytes | SHA-256 | Generator-visible |
|---|---:|---|---|
| `protocol.md` | 6,051 | `274547b757f54af2ebe19cb54dad57119f93371ca1f51bef94b70380a006fa94` | no |
| `frozen_evaluation_key.md` | 4,881 | `96c506f89ce8da0a976b51408f774cebb305c32ad8d12413603453c633cfd22f` | no |
| `generator_case.md` / clean-root `CASE.md` | 2,992 | `0efac3ad9a3832726903a4ebdedd4a5dbbc3f0fd8da36af792d39011b88a8551` | yes |
| `.agents/skills/econ-theorist-v2/SKILL.md` | 4,938 | `4ee147e92abc591d4d22d1cd80aade47dbf34a9d0351d1ed4026c27f67a7c5a1` | yes |
| `scripts/capture_codex_invocation.py` | 10,910 | `017d941665d3220c3f50885f08ae4d4af38979f67c8267c0b9cf3c64ce40d519` | yes |

The generator-visible root must otherwise contain only its virtual environment,
the wheel, empty `.host-state`, and empty `run` directories. It must not expose
the source checkout, Git data, test suite, historic pilot outputs, protocol,
evaluation key, or reference candidates.

## Verification before generation

- the complete code baseline at `45a540b` previously passed the 584-test
  routine non-long regression, with six declared platform/optional skips;
  the three hour-scale historical gold chains were intentionally excluded;
- the V8 focused framing/registry/model/distribution group previously passed
  69 tests, and the affected Windows operational-journal group passed 25;
- `git diff --check` passed for the pilot-freeze changes;
- all seven current schema/resource exporter checks passed in this freeze;
- source-checkout `doctor` reported `required_ok=true`, Python 3.12.13,
  Pydantic 2.13.4, and active V8 with 35/35 routes enabled;
- a fresh `--system-site-packages` wheel-smoke virtual environment installed
  the wheel offline with `--no-index --no-deps`; its import path was the wheel
  environment, and its `doctor` also reported `required_ok=true`, active V8,
  and 35/35 routes enabled;
- `latexmk`, `pdflatex`, Lean, and Node are unavailable optional tools; they
  do not block the local theory core. WolframScript is available.

No real model generation, `etai codex invoke` request, candidate, canonical
project state, or bridge response exists under this V8 pilot record. Any
generator-visible input or wheel change requires a new manifest and a new
blind task.
