# V8 authoring pair v2 adjudication stage-2 freeze

Frozen at `2026-07-19T11:50:38.9422671Z`, after both isolated readers had
answered the common probes and before the development task opened either
response or revealed the anonymous A/B mapping.

## Preserved stage-1 evidence

- Reader A input manifest remained `MANIFEST_OK` at
  `1257975a9219ae948e096a34246a29d9ce005f86a3a34a423f72def09597c72e`.
- Reader B input manifest remained `MANIFEST_OK` at
  `3f26cc3247497630249c38e16f76aa8dabaa5bbb23cc2f8fb57459b14886ad09`.
- Reader A `free_retell.md` remained byte-identical at 1,498 bytes and
  `5e090c2e6c20b9f33a26c470518b7880994e07a0903833feb6e68907d5ae41ba`.
- Reader B `free_retell.md` remained byte-identical at 1,336 bytes and
  `2d69640ba4046889110b5ad570bc03c1a0157f8c34d462939ed9b0c7e1862832`.

## Frozen stage-2 outputs

| Anonymous task output | Bytes | SHA-256 |
| --- | ---: | --- |
| `reader-a/probe_response.md` | 2,430 | `278e7e26dad05d4f9ae5f4705652368fbf816fcb16b9f90dcf1d18f06c9eac45` |
| `reader-b/probe_response.md` | 2,447 | `239234ca3bef34db57aa16e4517e1852541fa7c305697b13f204dace71626426` |

The mapping may now be revealed for final comparison. No candidate was run,
no canonical state was written, and no human gate was confirmed.
