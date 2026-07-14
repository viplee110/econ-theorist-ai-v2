# Public evidence redaction manifest

The private frozen execution root retains the exact original bytes. Two public
copies replace one Windows user-profile component with `<USERPROFILE>` before
GitHub archival:

- `generator_report.md`: original SHA-256
  `6b3f4730125a6b0cc42d76b4da05dd01c50cbdcf132937ff36fa842d33b774f3`;
- `run/001_start_stdout.jsonl`: original SHA-256
  `a3636a1f710b35afa9e7fc3c92c444ed42e540b5cc73518fd76b4b0291fbeb56`.

No diagnostic code, outcome, mutation status, request digest, route state, or
scientific content was changed. The unredacted originals remain only under the
private frozen root recorded in the preflight manifest. The public
`evidence_inventory.json` intentionally records their original hashes so the
redaction is explicit rather than silently rewriting provenance.
