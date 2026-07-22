# Independent cold read of one proposed economic-theory frame

You are already the designated independent reader. Do not create another
top-level task, use subagents, or consult any prior conversation.

Work only in `C:\tmp\qf1`. The launch turn supplies the expected SHA-256 of
`Q_MANIFEST.json`. First run the local verifier with that expected hash. Stop
on any mismatch.

Read only these files:

- `TASK_PROMPT.md`
- `Q_MANIFEST.json`
- `VERIFY_MANIFEST.ps1`
- `FRAMING_INPUT.json`

Do not inspect parent or sibling directories, hidden host state, the originating
project, source code, tests, cases, instructions, process evidence, other
reports, other conversations, or the network. Do not infer who or what produced
the frame. Do not search literature and do not assess novelty.

## Assignment

Read `FRAMING_INPUT.json` as a cold reader. Assess only the scientific framing
that appears in that file. Produce `report\Q_LOCK.md` containing:

1. A one- or two-sentence retelling of the research question.
2. The exact benchmark and the smallest departure from it.
3. The economic margin or force that could make the comparison nontrivial.
4. The central hidden assumption, degeneration risk, or failure condition.
5. The bounded theoretical contribution the frame could support if successful.
6. Any result, sign, welfare ranking, policy recommendation, validation,
   novelty, or venue claim that the frame appears to assume without support.
7. Whether a cold reader can recover the question, benchmark, delta, and scope
   without reconstructing missing context.
8. A Q-only verdict of `PASS`, `MIXED`, `FAIL`, or `NOT OBSERVABLE`, plus a
   confidence from 0 to 1 and concise reasons.

Judge economic sharpness, recoverability, nondegeneracy, and honest scope. Do
not reward length, schema density, mathematical notation, confidence, or
theorem-like prose. Explicitly ask whether the proposed contribution is more
than a mechanical finite-cell threshold exercise.

After writing `Q_LOCK.md`, compute its raw SHA-256 and write
`report\Q_LOCK.json` with these exact fields:

- `lock_schema`: `economic-theory-frame/q-lock/v1`
- `input_sha256`: copied from the verified manifest
- `report_sha256`: the raw SHA-256 of `Q_LOCK.md`
- `verdict`: the same Q-only verdict
- `confidence`: the same numeric confidence
- `model_observation`: the exact visible model label, or
  `high-intelligence-model-unverified` if unavailable
- `locked_at_utc`: the actual UTC timestamp

Do not alter any input file after verification. Do not record private chain of
thought. Stop immediately after the two lock files are written; do not ask for
or inspect any unblinding material.
