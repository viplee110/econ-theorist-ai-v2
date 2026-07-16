# V8 post-stabilization rerun preflight manifest

Status: **complete before generation; clean root contains no route request,
candidate, response, or canonical project state**

## Provenance

- source repository branch: `agent/research-first-audit-repair`;
- engine treatment commit:
  `4804323a84829247a88ae2f5e315538a331037fd`;
- clean non-cloud root:
  `C:\tmp\etai-v8-poststabilization-pilot-20260717-4804323`;
- Python: 3.12.13;
- wheel installation: offline, `--no-index --no-deps`, in a fresh
  `--system-site-packages` virtual environment.

The protocol source may later receive documentation-only commits. Those do not
change the executable treatment identified by the wheel digest and engine
commit above.

## Frozen generator-visible files

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `distribution/econ_theorist_ai-0.1.0-py3-none-any.whl` | 702,857 | `09c620566505acea8e5ab698fff32e56f9197b71d336abbed9c9a419769ce22b` |
| `.agents/skills/econ-theorist-v2/SKILL.md` | 4,938 | `4ee147e92abc591d4d22d1cd80aade47dbf34a9d0351d1ed4026c27f67a7c5a1` |
| `.agents/skills/econ-theorist-v2/agents/openai.yaml` | 296 | `d0db034c3c93616cb42390df90343f13a45f81af6cbe48d4b678fc54e0e09c17` |
| `CASE.md` | 2,992 | `0efac3ad9a3832726903a4ebdedd4a5dbbc3f0fd8da36af792d39011b88a8551` |
| `capture_codex_invocation.py` | 18,731 | `590ef3bdb4bb3e7ba80952108a4c98db8893f0bce3684e69372464967906291d` |

The generator-visible top level is exactly `.agents`, `.host-state`, `.venv`,
`distribution`, `run`, `capture_codex_invocation.py`, and `CASE.md`. Before
generation, `run/` and `.host-state/` are empty. There is no `.git`, source
tree, test tree, old candidate, prior report, protocol, or evaluation key in
the root.

## Frozen evaluator-only input

The unchanged same-case evaluation key remains outside the clean root:

- `frozen_evaluation_key.md`, 4,881 bytes;
- SHA-256:
  `96c506f89ce8da0a976b51408f774cebb305c32ad8d12413603453c633cfd22f`.

The generator may not read it. Its hash is recorded here only for later
adjudication provenance.

The exact user-visible rerun prompt is also frozen outside the clean root:

- `rerun_task_prompt.md`, 2,442 bytes;
- SHA-256:
  `d439f79ecc2b227fc73c18293fa09bc0f7271f6616ea913e83cb9d88b968d066`.

The prompt supplies only isolation, authorization, capture, and reporting
constraints. It does not contain the hidden evaluation key or a reference
candidate.

## Verification

- the treatment source passed 596 routine non-long tests with six declared
  optional/platform skips; the three hour-scale historical gold chains were
  intentionally excluded by the repository's routine command;
- the ten focused doctor/distribution tests and six focused framing-registry
  tests passed;
- all seven current exporters and compilation passed on the parent
  stabilization commit; this treatment changes no schema, registry, or
  instruction bytes;
- `git diff --check` and installed-wheel checks passed;
- the clean-root import path resolves inside its installed wheel environment;
- installed-wheel `doctor` reports `required_ok=true`, active registry v8, and
  35/35 routes enabled with verified instruction bundles;
- the installed active `repair.dependency.v5` bundle loads directly and is
  1,490 bytes;
- the read-only installed `etai codex invoke --schema bundle` preflight passed;
- `latexmk`, `pdflatex`, Lean, and Node are unavailable optional tools;
  WolframScript is available.

No ordinary-model generation or project-bound bridge request has occurred in
the clean rerun root. Any change to a generator-visible file invalidates this
manifest and requires a new root or an explicit amendment before generation.
