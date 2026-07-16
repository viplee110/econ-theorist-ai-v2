# R2 cold-reader package manifest

Package root: `C:\tmp\etai-v8-r2-reader`

Status: **frozen before reader execution; `report/` initially empty**

## Allowlisted files

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `READER_PROMPT.md` | 1,415 | `28ad053e88c7f9ee87a1f5b59c21f13106f601d78ff9db5d21356e33c5948f2e` |
| `evidence/economist_memo.md` | 1,452 | `3f7ee3ef1111c20f999d5a47d889e3650db3998ea5bb8d880740aba4c0ad7f48` |

`MANIFEST.md` is this manifest's byte-for-byte package copy and is therefore
excluded from its own table. The repository postflight record binds its byte
count and digest.

The only allowlisted directory without an input file is `report/`. It must be
empty before execution and may receive only `cold_reader_retell.md`.

## Projection provenance

The memo is a field-preserving Markdown projection of `economist_memo` from
the final R2 audit candidate:

- generator source:
  `run/20260717-020-audit-repair2-metadata-captured-candidate.json`;
- source bytes: 41,447;
- source SHA-256:
  `405d0c38b658309cb2730deb3f8434558c6ce3629e7a84a31f61d26b0071b979`;
- source engine canonical candidate digest:
  `733319830ae7c3b2cc9336da37faddcbf8bd540615dcd425c176943ca05b5c6a`;
- canonical status: uncommitted after candidate validation failure.

The provenance above is not copied into the reader-facing memo. It is retained
here so that the projection is auditable without disclosing the evaluation key
or upstream evidence to the reader.

## Exclusions

The package contains no CASE, evaluation key, probes, WorkPacket, upstream
question/benchmark/primitive objects, candidate schema, validator diagnostic,
generator report, old pilot, source code, test, registry, wheel, `.git`,
`.agents`, `.venv`, operational state, host state, credential, email address,
or user-profile path. It is not an Econ Theorist project and must not be bound
or initialized as one.
