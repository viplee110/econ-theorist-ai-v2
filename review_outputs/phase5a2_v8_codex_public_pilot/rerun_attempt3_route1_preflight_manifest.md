# V8 R3 guaranteed-service preflight manifest

Status: **complete before generation; no project-bound bridge invocation has
occurred in the clean R3 root**

## Provenance

- source repository branch: `agent/research-first-audit-repair`;
- executable engine commit:
  `462c15e698688e1db8b6b8ce86109ef9235a0073`;
- clean non-cloud root: `C:\tmp\etai-v8-r3`;
- Python: 3.12.13;
- wheel build: `pip wheel . --no-deps --no-build-isolation` from the clean
  executable commit;
- wheel installation: offline, `--no-index --no-deps`, in a fresh
  `--system-site-packages` virtual environment.

The later protocol/manifest documentation does not change the executable
treatment identified by the commit and wheel digest.

## Frozen generator-visible inputs

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `distribution/econ_theorist_ai-0.1.0-py3-none-any.whl` | 704,656 | `24edc0a9d9af69aece2d4e6414cbb401b2d4a109c26861f570fb4879cd9f7cfd` |
| `.agents/skills/econ-theorist-v2/SKILL.md` | 4,938 | `4ee147e92abc591d4d22d1cd80aade47dbf34a9d0351d1ed4026c27f67a7c5a1` |
| `.agents/skills/econ-theorist-v2/agents/openai.yaml` | 296 | `d0db034c3c93616cb42390df90343f13a45f81af6cbe48d4b678fc54e0e09c17` |
| `CASE.md` | 4,332 | `ed0e45072db305fcf0dc5f939fd9d04618cda87d5bfb80c8725dbd0449fa89f2` |
| `capture_codex_invocation.py` | 18,731 | `590ef3bdb4bb3e7ba80952108a4c98db8893f0bce3684e69372464967906291d` |

All five listed inputs are read-only.

The generator-visible top level is exactly `.agents`, `.host-state`, `.venv`,
`distribution`, `run`, `capture_codex_invocation.py`, and `CASE.md`. Before
generation, `run/` and `.host-state/` are empty. There is no `.git`, `.codex`,
`.econ-theorist`, source tree, test tree, old candidate, prior report,
protocol, evaluation key, or old operational state in the root.

The root `CASE.md` bytes exactly match
[`rerun_attempt3_generator_case.md`](rerun_attempt3_generator_case.md).

## Frozen external controls

The researcher branch decision remains outside the generator root:

- [`rerun_attempt3_route1_branch_decision.md`](rerun_attempt3_route1_branch_decision.md),
  2,152 bytes, SHA-256
  `9e81b06e043754eb56c6d232bc3dced5acfa32cc959d7f8928ae400f6e55d8d4`.

Its scientific content is represented in `CASE.md`; its metadata and prior-run
context are not generator inputs.

The unchanged evaluator-only key also remains outside the root:

- [`frozen_evaluation_key.md`](frozen_evaluation_key.md), 4,881 bytes,
  SHA-256
  `96c506f89ce8da0a976b51408f774cebb305c32ad8d12413603453c633cfd22f`.

The exact user-visible task prompt is frozen outside the root:

- [`rerun_attempt3_route1_task_prompt.md`](rerun_attempt3_route1_task_prompt.md),
  2,872 bytes, SHA-256
  `557fdb9a165dfbb617f340c88348695d2e05601b725e120daf1c4e3ba5baf11e`.

The prompt supplies isolation, initialization authority, capture discipline,
and the fact that the branch in `CASE.md` is already researcher-authored. It
contains no evaluation key, reference candidate, or old output.

## Installed-wheel verification

- the import path resolves to
  `C:\tmp\etai-v8-r3\.venv\Lib\site-packages\econ_theorist\__init__.py`;
- installed-wheel `doctor` reports `required_ok=true`, active registry v8,
  35/35 routes enabled, verified instruction bundles, and registry digest
  `5d2c2efdef205ee1ff188249dcb05cb5a4430d36ef754a93bde402a092aa40c1`;
- the installed `etai codex invoke --schema bundle` parses with the expected
  `request`, `response`, and `schema_bundle` members;
- Python, Pydantic, registry, Git, `latexmk`, `pdflatex`, and WolframScript are
  available; Lean and Node are unavailable optional tools and are not counted
  as passes;
- the exact executable source commit previously passed the 599-test routine
  non-long gate with six declared skips and all seven exporter checks; the
  three hour-scale historical gold chains were intentionally excluded;
- `git diff --check` passed before the wheel build, and the build left the
  executable source tree clean.

No ordinary-model generation, canonical initialization, project-bound bridge
request, WorkPacket delivery, or human gate has occurred in R3. Any change to
a generator-visible input invalidates this manifest and requires a new root or
an explicit pre-generation amendment.
