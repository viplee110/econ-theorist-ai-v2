---
name: econ-theorist-v2
description: Operate Econ Theorist AI v2 through its installed machine protocol in a local economic-theory paper project. Use when the user explicitly asks to initialize, inspect, continue, repair, or run Econ Theorist AI/v2, or when the selected root is already v2-bound and the user asks to continue the theory project. Do not use for empirical, econometric, data-analysis, or generic prose-only work.
---

# Econ Theorist AI v2

Use the installed engine as the sole owner of scientific workflow, state,
instructions, schemas, validation, and route selection. Act only as a thin
Codex host over the engine-owned bridge.

## Operate the project

1. Identify the one project root explicitly selected by the user. Do not scan
   parent, sibling, or unrelated research directories.
2. Verify that the installed `etai` exposes the `codex` bridge. Use its schema
   output when the exact request shape is not already known.
3. Invoke `etai codex invoke --request <path-or->`. Let the bridge bind or
   inspect the project, select the legal next route, open or resume it, and
   deliver the exact WorkPacket.
4. Set initialization intent only when the user explicitly asked to enable or
   initialize v2 in that root. Never infer permission to create genesis from a
   request merely to inspect or discuss a paper.
5. Send `requested_scope` and `framing_intent` only to start an unframed
   project or when the user explicitly requests a new frame/reframe. Omit both
   on every ordinary continuation after a committed route; their presence is
   an explicit reframe request. If an omitted-input continuation is blocked,
   surface its diagnostic rather than replaying the old framing inputs.
6. Follow the bridge status exactly. Stop and surface the smallest necessary
   user choice for an ambiguous route, structural human gate, privacy blocker,
   incompatible root, or repair requirement. Handle an explicit
   `single_fallback` only as described below.
7. Treat the returned WorkPacket as the only scientific instruction, context,
   and output contract for the route. Do not supplement it with a remembered
   workflow, a journal stereotype, or instructions copied from another run.
8. Write helper code only under the packet's shadow root and the candidate only
   at its declared candidate path. Never edit canonical ObjectStore bytes or
   overwrite a human-owned paper or instruction file.
9. Construct the candidate only from the ready response's
   `candidate_authoring_contract` and exact WorkPacket. Copy its same-named
   `transaction_bindings`, use only its `output_locations`, and follow its
   transaction/payload/relation schemas and output cardinalities. The bridge
   computes canonical identity from ordinary strict JSON. Do not read package source, tests,
   fixtures, or reference candidates to guess the Transaction shape. Concentrate
   model judgment on the economic content requested by the WorkPacket.
10. Submit the candidate through the bridge's completion request. Report success
   only when the canonical response says the candidate was committed; a file
   write, plausible draft, or staged candidate is not completion.
11. After interruption, invoke the same bridge request or inspect its recorded
    operation state. Preserve exact operation keys and bindings; do not create a
    replacement run merely because chat history is missing.
12. Submit a bridge `finish` request only after an otherwise-unrecorded real
    termination following packet delivery: exhausted declared retries,
    explicit user cancellation, or an abnormal host/model abort. Use the exact
    packet and envelope bindings. Do not finish an ordinary human wait,
    clarification, handoff, or intentional pause; resume the same immutable run.

## Use the bounded framing team

- Only when the bridge returns `team_ready`, start exactly one mentor and two
  sealed collaborator advisory lanes. Give each the exact delivered WorkPacket
  plus only its bridge-supplied role overlay. Advisory lanes cannot write the
  candidate, call completion, see another lane's output, or delegate again.
- If collaborator outputs are byte-identical or plainly the same proposal, ask
  collaborator B for one bounded diversity repair before publishing the panel.
- Publish raw lane drafts through the bridge, show the attributed panel, and ask
  the researcher one natural-language choice. Send the exact current user turn;
  never manufacture or silently sharpen the researcher's direction.
- Follow `awaiting_clarification`, `new_brief_required`, and `single_fallback`
  literally. For `single_fallback`, disclose that the team is unavailable and
  use exactly one worker with the packet and authoring contract; never pretend
  that one model supplied three independent opinions. The other two statuses
  create no worker.
- Only `handoff_ready` permits exactly one research worker to author the declared
  candidate. Give it the returned packet, candidate authoring contract, panel,
  synthesis, and handoff; include the exact handoff hash plus the worker's
  observable agent/model labels in one `stage_and_commit`; never use `stage_only` or
  `commit_staged` for the team. Stop after the framing result.

## Preserve boundaries

- Keep Phase 5A execution single-agent outside the bridge-declared framing-team
  exception. Do not otherwise delegate a route or expose its packet elsewhere.
- Do not choose or reorder routes yourself.
- Do not restate theory-kernel, profile, craft, Top-5, or route-specific rules
  in this skill; the pinned WorkPacket owns them.
- Do not imitate Transaction, entity, relation, or theory schemas from memory.
  If a ready response lacks a complete authoring contract, stop as an engine
  compatibility error instead of inspecting implementation source to fill gaps.
- Do not confirm L2/L3 Decisions, fabricate human approval, relax privacy, or
  bypass a blocked delivery.
- Do not use legacy `etai begin`, `stage`, or `commit` commands as a substitute
  for the bridge and machine protocol.
- Do not read test fixtures, gold candidates, or reference answers while
  producing a real evaluation candidate.
- Do not rewrite `run.json` or claim that a recorded host failure canonically
  abandoned a route.
- Do not use `finish` as a generic pause or handoff marker.

When the bridge has not delivered a packet, do not begin scientific generation.
