# Phase 5B first genuine framing-team pilot

You are already the one designated pilot task. Do not create, fork, hand off
to, or ask for another top-level Codex task. Work in exactly:

`C:\tmp\p5b1`

This is a source-code-isolated, researcher-in-the-loop exploratory use of Econ
Theorist AI v2, not a regression test and not evidence that multiple agents
outperform one model.

## Authority and permitted inputs

The researcher explicitly authorizes initialization of one new local v2
project in the selected root, the non-confidential provider exposures stated
in `CASE.md`, and the bounded framing-team flow for the frozen case. Read
completely:

1. `C:\tmp\p5b1\CASE.md`
2. `C:\tmp\p5b1\.agents\skills\econ-theorist-v2\SKILL.md`

Follow that skill exactly. The installed engine and its returned WorkPacket
own all scientific instructions, schemas, paths, validation, routing, and
repair limits. When an exact request shape is needed, inspect the installed
bridge schema rather than guessing it. The only direct bridge command allowed
is the read-only, non-project-bound schema query
`etai codex invoke --schema request` or `etai codex invoke --schema bundle`.
Every project-bound invocation must use the capture helper below.

Do not inspect source code, Git history, tests, fixtures, reference candidates,
old pilot folders, parent or sibling research directories, other conversations,
the repository at `C:\Projects\Econ Theorist AI v2`, or the other files in
`C:\tmp\p5b1-control`. Do not use the network or bring in outside literature.
Do not run unit tests, exporters, gold chains, or generic repository checks.

## Frozen runtime and evidence capture

Use only this installed launcher:

`C:\tmp\p5b1\.venv\Scripts\etai.exe`

Make every bridge invocation through:

`C:\tmp\p5b1\.venv\Scripts\python.exe C:\tmp\p5b1\capture_codex_invocation.py`

For every invocation, first save one strict request JSON under `run`, then use
unique `--stdout`, `--stderr`, and `--metadata` evidence paths under `run`.
Pass all of these fixed arguments to the capture helper:

- `--etai C:\tmp\p5b1\.venv\Scripts\etai.exe`
- `--project-root C:\tmp\p5b1`
- `--local-appdata C:\tmp\p5b1\.host-state`

For every `complete` invocation also pass the exact pre-invocation raw
candidate via `--candidate-source`. Except for the two read-only schema queries
allowed above, never call `etai codex invoke` directly. Never overwrite an
earlier capture and never edit canonical state directly; an engine-authorized
atomic commit is the intended terminal success.

Freeze one session object at the first request and reuse it exactly throughout
the run. Use the exact model label visible to this task if the host exposes it.
If no exact label is exposed, use
`user-selected-high-intelligence-unverified` consistently as both the selected
model and sole installed-model observation, and state in the report that this
is a user-selected/request label rather than independent provider/backend
proof. Do not silently change models. If capacity forces a model change, stop
and report without substituting another model.

## Authorized flow

1. Copy the exact `project_name`, `requested_scope`, and `framing_intent` from
   `CASE.md` into one `start_or_resume` request with `initialize: true`.
2. Follow the bridge response literally. Do not begin scientific generation
   until it delivers a WorkPacket. If `framing_team.open` returns
   `single_fallback`, stop and report `team surface not exercised`; this frozen
   team pilot does not authorize a fallback worker and the result must not be
   counted as team evidence. Follow every other bridge status literally.
3. When and only when the bridge returns `team_ready`, create exactly three
   advisory lanes: `mentor`, `collaborator_a`, and `collaborator_b`. Each lane
   receives only the exact immutable WorkPacket plus its own bridge-supplied
   role overlay and the minimum non-scientific permission boundary. Use
   context-free subagent creation with `fork_turns="none"` (or a strictly
   equivalent host mechanism); inherited conversation is forbidden. If that
   capability is unavailable, stop instead of weakening lane separation. Do
   not expose `CASE.md`, this task prompt, another lane's output, source, tests,
   or evaluator material. Do not allow a lane to delegate, write a candidate,
   or invoke the bridge.
4. Use the same selected model observation for coordinator, all three advisors,
   and the later worker. Preserve each raw attributed lane output under `run`.
   If the collaborators are byte-identical or plainly the same proposal, ask
   only collaborator B for the single bounded diversity repair permitted by
   the skill. Do not create a fourth advisor or an extra panel.
5. Publish the three raw lane drafts through
   `framing_team.publish_panel`. Show the researcher all three raw outputs
   verbatim and with attribution before any optional coordinator orientation.
   Do not preselect a winner or silently synthesize a decision. Ask for one
   natural-language choice and then stop the turn. Wait for a genuinely new
   direct user reply in this same task.
6. On the next turn, preserve the exact user text before interpreting it. Send
   the exact current-user capture and an honest semantic interpretation through
   `framing_team.apply_user_turn`. Never invent, sharpen, or infer a structural
   choice. Follow `awaiting_clarification`, `new_brief_required`, `park`, and
   `kill` literally. None authorizes a worker. If the user asks for another
   panel, do not spawn unauthorized new lanes; follow the bridge/skill or stop
   and report the limitation.
7. Only `handoff_ready` authorizes exactly one `research_worker`. Give that
   worker the exact WorkPacket, authoring contract, preserved panel,
   researcher synthesis, and returned handoff, plus only the minimum
   non-scientific permission/capture boundary. Use `fork_turns="none"` or its
   strict equivalent; pass nothing from source, tests, fixtures, or evaluators.
8. The research worker itself—and only that worker—may write the declared
   candidate and execute every captured `complete` invocation. It must submit
   only `stage_and_commit`, with the exact handoff hash and its frozen
   agent/model observation. Use the schema-safe `research_worker` as the
   completion `agent_label`, not a slash-containing internal task path. The
   coordinator must not author, edit, repair, or submit the candidate on the
   worker's behalf. If validation returns an
   engine-authorized repair, resume the same worker identity and obey only the
   declared diagnostics and repair budget. Never use `stage_only`,
   `commit_staged`, or a substitute worker.
9. Stop after the framing route commits or reaches an honest terminal failure.
   Do not start decomposition, framing audit, G1, or any later route. Do not
   confirm or fabricate any human gate.

## Hard stops

Stop and surface the exact status on stale head or packet, binding/digest
mismatch, privacy/evidence failure, unexpected route, `single_fallback`,
`new_brief_required`, `park`, `kill`, model capacity or model change, repair
exhaustion, or any requested human gate. Do not use
`finish` for an ordinary user wait, clarification, or handoff. Use it only for
an otherwise-unrecorded real terminal stop allowed by the installed skill.

The current implementation has a known recovery gap after `kill` or
`new_brief_required`: stop and report it; do not improvise abandonment or
reframing.

## Terminal report

After a canonical framing commit or honest terminal failure, write
`C:\tmp\p5b1\run\agent-report.md`. Include:

- exact project root; observable model/session label and its limitations;
- chronological invocation/evidence paths and response statuses;
- packet, envelope, team-plan, panel, synthesis, handoff, candidate, receipt,
  and canonical-head identifiers or hashes only when actually exposed by the
  public bridge; never inspect source or guess hidden operational paths to
  obtain an unexposed worker-activation or completion-binding hash;
- the three lane labels and whether the one diversity repair was used;
- the exact researcher text, its recorded disposition, and whether a
  clarification was needed;
- researcher interventions counted separately as initial brief, direct choice,
  clarification turns, and any turn forced to handle a machine object, plus
  any mechanical friction;
- validation/repair outcomes, canonical writes, and human gates;
- explicit confirmation that no later route, network, external material,
  source/tests/fixtures, or unauthorized delegation was used.

Do not record private chain of thought or credentials. Distinguish what the
host observed from what it could not independently verify. Report useful or
unhelpful disagreement descriptively; do not claim research quality,
causality, model independence, or multi-agent superiority.

Hidden operational-sidecar integrity, if needed, belongs to a later frozen
controller/postflight inspection outside this generator task.
