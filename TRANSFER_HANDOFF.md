# Econ Theorist AI v2 transfer handoff

Updated: 2026-07-16

This file is the entry point for continuing the project on another computer or
in a new Codex conversation. Read it before changing code or rerunning pilots.

## Authoritative locations

- GitHub repository: `https://github.com/viplee110/econ-theorist-ai-v2`
- Active branch: `agent/research-first-audit-repair`
- Research-code checkpoint before this handoff: `cfcf2b8`
  (`Bind v2 packets to research inputs`); use the active remote branch tip as
  the authoritative handoff commit.
- Local repository under the shared Dropbox tree:
  `Search on Graphs/tmp/econ-theorist-ai-v2-architecture`
- Full V5.5 research run under the shared Dropbox tree:
  `Search on Graphs/.etai-v5_4d2-economy-tier-20260716-c8c539e`
- Compact V5.5 evidence:
  `review_outputs/phase5a2_v5_5_economy_tier_audit/`
- Detailed diagnosis preceding V5.5:
  `review_outputs/phase5a2_v5_4_codex_public_pilot/evaluation_report.md`
- Scholar/craft plan, including the unified micro/IO/search scholar pool:
  `docs/architecture/scientific_discovery_craft.md`

The Git author must remain:

`viplee110 <200110057+viplee110@users.noreply.github.com>`

## Current development position

The project is in the research-quality validation part of Phase 5, not Phase 6.
The core Phase 0--4 research substrate is implemented. Phase 5 is exercising
that substrate through real Codex research routes and reducing human effort.
Phase 6 remains the external/full-paper evaluation and eventual real-submission
gate; it has not been completed or removed.

The guiding product definition is an economic-theory research team, not merely
a paper generator. Priorities are economic question selection, mechanism and
model discovery, formal argument, intuition, and reader-facing exposition.
Software complexity is justified only when it protects or improves those
scientific functions. Local-user cybersecurity/attack hardening is out of
scope.

The scholar-distillation program is planned but not yet fully executed. Its
priority fields are IO theory, consumer/search theory, applied micro theory,
and adjacent modern micro theory. The existing curated pool in
`scientific_discovery_craft.md` is the starting population; distillation should
extract problem-finding, model-building, mechanism-testing, and exposition
patterns, not imitate scholars' prose or personalities.

## Completed repair and verification

On the active branch, WorkPacket compiler v2 now:

- exposes exact required input evidence refs;
- tells the model to copy them, in order, into `Transaction.evidence_refs`;
- exposes the required direction of the `decomposes` relation;
- gives more actionable validator messages;
- preserves compiler-v1 replay compatibility.

Verification completed on 2026-07-16:

- focused candidate-contract and Codex-bridge tests: 20 passed;
- schema plus related focused regression after regeneration: 23 passed;
- non-long suite: 583 tests run, 1 stale generated-schema failure found;
- both affected machine schemas were regenerated;
- the exact failed schema test and related suites then passed.

Commit `cfcf2b8` is pushed to the active remote branch. The untracked top-level
`tmp/` directory belongs to the user and must never be staged or deleted.
Two untracked V5.5 bootstrap scratch directories under `review_outputs` are
non-authoritative and should not be committed unless deliberately converted
into evidence:

- `review_outputs/phase5a2_v5_5_directed_bridge/`
- `review_outputs/phase5a2_v5_5_directed_pilot/`

## Latest scientific experiment

Read
`review_outputs/phase5a2_v5_5_economy_tier_audit/run_summary.md` and its five
adjacent evidence files.

Short conclusion:

- the economy-tier model committed `decompose.primitives` correctly;
- an independent high-intelligence audit found the model was not dynamically
  closed and should not pass G1;
- the economy-tier built-in `audit.framing_economics` independently found
  essentially all of those scientific defects;
- the audit candidate then failed to commit because a negative diagnosis could
  not satisfy an active-witness binding that the defective upstream graph made
  impossible;
- the canonical head did not move and G1 was not confirmed.

This is a narrow representation/control-flow defect, not a need to redesign the
whole architecture and not a failure of the audit's economic reasoning.

## Exact next task

Use a high-intelligence model for diagnosis/design. Before editing, reproduce
the archived audit candidate's exact validation failure against the current
branch and identify the smallest responsible validator/model condition.

Design goal:

1. A negative audit with `proposed_action == revise_framing` can canonically
   record that no legitimate payoff witness exists when it supplies typed gaps
   and exact upstream repair targets.
2. It must not fabricate or weaken a witness.
3. Any `ready_for_g1`, active-mechanism, distinctive-mechanism, or robustness
   claim retains the current strict witness requirements.
4. Navigation should expose an upstream repair route rather than turn a useful
   negative audit into an opaque terminal failure.
5. Keep the implementation small: prefer one conditional validation rule and
   focused tests over new schemas, workflow layers, or enterprise machinery.

After the design is settled, a lower-cost model may run the focused and full
software regression. Switch back to a high-intelligence model for the next
blind scientific comparison and system-level judgment.

After this defect is closed, resume the broader roadmap:

1. rerun the same economy-tier audit and compare its canonical memo against the
   independent audit;
2. test whether the revised pipeline routes cleanly back to repairing the
   ResearchQuestion, BenchmarkSet, or PrimitiveGraph;
3. continue the IO/search-first scholar distillation;
4. run additional held-out classic/problem-reconstruction pilots;
5. reserve Phase 6 for full-paper quality, human-effort, and submission-level
   validation.

## New-computer procedure

1. On the old computer, wait until Dropbox reports fully synced and close all
   Codex tasks, terminals, editors, and Python processes using this tree.
2. On the new computer, wait until Dropbox reports fully synced before opening
   the repository. Never let both computers write this Git worktree or the same
   `.econ-theorist` project concurrently.
3. Treat GitHub, not Dropbox's copy of `.git`, as the code authority. In the
   repository run:

   ```powershell
   git fetch origin
   git switch agent/research-first-audit-repair
   git pull --ff-only origin agent/research-first-audit-repair
   git status --short
   ```

4. Recreate the Python environment on the new computer; do not rely on the
   Dropbox-synchronised `.venv`:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -e .
   .\.venv\Scripts\etai.exe doctor
   ```

   `doctor` should report `"required_ok": true`.

5. Verify that the hidden directory
   `Search on Graphs/.etai-v5_4d2-economy-tier-20260716-c8c539e/.econ-theorist`
   exists. It contains the full canonical and operational run state. Do not
   initialize that project again and do not delete its recorded failed run.
6. Open the repository root in Codex. Start a new high-intelligence task with
   the prompt below.

## Prompt for the first task on the new computer

> Continue development of Econ Theorist AI v2 from `TRANSFER_HANDOFF.md` in
> this repository. Read that file completely, then inspect the compact V5.5
> evidence directory it names. Verify the active Git branch and commit before
> changing anything. Do not rerun completed decompose or audit generation.
> First reproduce and diagnose why the scientifically correct negative
> `audit.framing_economics` candidate could not commit. Propose and implement
> only the smallest research-first repair that permits a typed
> `revise_framing` diagnosis without weakening any readiness or active-mechanism
> gate. Preserve user Git identity, do not stage the user-owned `tmp/`, avoid
> enterprise/security expansion, run focused tests first, and report before a
> costly model-based rerun.

Once the new task has read this handoff and confirmed the exact evidence hashes,
the Codex conversation history is no longer needed to continue accurately.
