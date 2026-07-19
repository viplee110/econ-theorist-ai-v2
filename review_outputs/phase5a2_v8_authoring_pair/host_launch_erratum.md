# Held-out pair host-launch erratum

Status: host-only correction recorded before either generator opened an arm
file or authored attempt 1.

## Observation

Both designated generator tasks verified their exact arm manifests and
reported `MANIFEST_OK`. The frozen launch message then told the already-created
task to open a new Codex task. Codex rejected that recursive task-creation
request. Neither task opened its arm files, invoked `RUN_ATTEMPT.ps1`, produced
an artifact or receipt, consumed a repair, or observed the sibling arm.

This is `HOST_LAUNCH_PROMPT_DEFECT`, not a machine, compiler, V8 scientific,
or model-generation failure. The pair remains at attempt 1 in both arms.

## Symmetric recovery

Resume the same two tasks; do not create replacements. Each receives only the
same host-level correction plus its already assigned arm path:

1. You are already the designated generator task. Do not create, fork,
   delegate, or hand off another task.
2. The exact manifest verification already succeeded and no arm file has been
   opened. Keep attempt number 1 and consume no repair.
3. Set the shell working directory to the assigned arm, read only
   `TASK_PROMPT.md` and the manifest-listed files it permits, and follow that
   prompt through the frozen runner.

This correction contains no economic content, candidate hint, diagnostic, or
cross-arm observation. It is applied identically before scientific generation
in both arms, so it does not alter the paired treatment. The frozen package at
`C:\tmp\etai-v8-pair-ecc1853` and its external PRE-manifest SHA-256
`96dae6d531db549679dbbcdd6a78641fb7b7730c34054d3644cc032f3b79b5de`
remain unchanged.

The launch-prompt generator was separately corrected for future packages so a
message pasted into an existing task states the workspace setup as an operator
precondition instead of instructing the task to create another task.
