# V8 authoring pair v2 adjudication stage-1 freeze

Frozen at `2026-07-19T11:45:27.8604880Z`, after the independent scientific
adjudicator and both isolated cold readers had stopped, and before the
development task opened any of their generated outputs.

## Input integrity

- Scientific package: `MANIFEST_OK`, SHA-256
  `38d9fbea9346f932001bcef275e6e2fcaead941775f69b049e5a90ed51a4c974`
  over five listed inputs.
- Reader A package: `MANIFEST_OK`, SHA-256
  `1257975a9219ae948e096a34246a29d9ce005f86a3a34a423f72def09597c72e`
  over two listed inputs.
- Reader B package: `MANIFEST_OK`, SHA-256
  `3f26cc3247497630249c38e16f76aa8dabaa5bbb23cc2f8fb57459b14886ad09`
  over two listed inputs.

## Frozen outputs

| Anonymous task output | Bytes | SHA-256 |
| --- | ---: | --- |
| `scientific/phase1_scientific_adjudication.md` | 25,866 | `bb14113daa0882558372cc2380e20940cd8094dc964888d867f6623c6fbf5ee4` |
| `reader-a/free_retell.md` | 1,498 | `5e090c2e6c20b9f33a26c470518b7880994e07a0903833feb6e68907d5ae41ba` |
| `reader-b/free_retell.md` | 1,336 | `2d69640ba4046889110b5ad570bc03c1a0157f8c34d462939ed9b0c7e1862832` |

The anonymous A/B mapping remains outside all three task workspaces and is not
revealed by this freeze. No candidate was executed, no canonical state was
written, and no human gate was confirmed.

The two frozen free retells may now receive the common stage-2 probes. They
must not be edited after this point.
