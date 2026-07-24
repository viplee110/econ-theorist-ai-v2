---
name: econ-theorist-v2
description: Operate Econ Theorist AI v2 through its installed machine protocol in a local economic-theory paper project. Use when the user explicitly asks to initialize, inspect, continue, repair, or run Econ Theorist AI/v2, or when the selected root is already v2-bound and the user asks to continue the theory project. Do not use for empirical, econometric, data-analysis, or generic prose-only work.
---

# Econ Theorist AI v2

Use the installed engine as sole owner of workflow, state, instructions,
schemas, validation, and routing. Act as a thin host over its bridge.

## Operate the project

1. Use only the explicit project root; do not scan parent/sibling directories.
2. Verify that the installed `etai` exposes the `codex` bridge. Use its schema
   output when the exact request shape is not already known.
3. Invoke `etai codex invoke --request <path-or->`; let the bridge bind/inspect,
   select, open/resume, and deliver the exact WorkPacket.
4. Initialize only when explicitly asked. Inspection/discussion never implies
   permission to create genesis.
5. Send `requested_scope` and `framing_intent` only for an unframed project or explicit reframe. Omit both on every ordinary continuation. Freeze each
   intended field separately, write the request as UTF-8, re-read it, and
   require each decoded field and corresponding `WorkPacket.run_input` field
   to equal its intended string. Preserve the user's framing text; do not make
   the two fields identical when their intended meanings differ. Stop before
   lane exposure on mismatch. Use a user-supplied or neutral `project_name`;
   never add a capability, pilot/task label, expected result, or scientific
   primitive. Surface omitted-input diagnostics
   rather than replaying the old framing inputs. If a brief collides with a run,
   use `reframe.repair` only for a bridge-accepted untouched, empty-focus
   framing-v2 run with no active team. Bind delivery, capture, target, and new brief; exact retry preserves its noncanonical operational disposition.
6. Follow the bridge status exactly. Stop and surface the smallest necessary
   user choice for an ambiguous route, structural human gate, privacy blocker,
   incompatible root, or repair requirement. After the user chooses one route
   from `ambiguous_next`, relay only that existing route id through
   `requested_route_id`; never invent a route, combine it with a reframe brief,
   or treat the route choice as a human scientific gate. Handle an explicit
   `single_fallback` only as described below.
7. Treat the returned WorkPacket as the only scientific instruction, context,
   and output contract for the route. Do not supplement it with a remembered
   workflow, a journal stereotype, or instructions copied from another run.
8. Write helper code only under the packet's shadow root and the candidate only
   at its declared candidate path. Never edit canonical ObjectStore bytes or
   overwrite a human-owned paper or instruction file.
9. Use only the ready `candidate_authoring_contract` and exact WorkPacket.
   Copy its bindings/locations and obey its schemas/cardinalities.
   Do not read package source, tests, fixtures, or reference candidates; focus
   model judgment on the WorkPacket's economic content.
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

- Only when the bridge returns `team_ready`, start one mentor and two clean-context sealed lanes,
  each containing only the exact WorkPacket and its role overlay: no inherited
  coordinator/task turns, host path, pilot/session/capability/review metadata,
  or peer output. Capability labels authorize host operations only, never a
  research primitive. Lanes cannot write, complete, see peers, or delegate.
- If collaborator outputs are byte-identical or plainly the same proposal, ask
  collaborator B for one bounded diversity repair before publishing the panel.
- Publish the raw drafts without replacing them with titles or short summaries.
  If the bridge returns `awaiting_choice_review`, do not ask the user to choose.
- Claim source-aware choice available only when privacy/egress permits one
  bounded literature orientation. The coordinator performs it without recalling
  lanes or treating model memory as checked; submit sources, limits, and cards.
- Each collaborator card must state the concrete question, exact benchmark,
  economic value, ordinary-agent baseline, one operational AI primitive,
  mechanism-design delta, closest sources and overlap, remaining theory delta,
  falsifiable increment, and kill condition. Apply the mentor's critique as a
  screen; never relabel or select it as a third direction.
- Cards are an automatically compiled decision view, not a fixed research
  method. They are orientation, never novelty or absorption evidence.
- Only after `awaiting_user_choice`, put the attributed raw panel and, when
  present, mentor screen, every complete card, and source list/limits in the
  user-facing choice screen. Hashes, status, paths, or report links alone are
  not delivery. Ask one natural-language choice; relay the exact current user turn without sharpening or summarizing it.
- If source access fails, surface a retryable blocker; never invent citations
  or downgrade the active team to the legacy path.
- Follow `awaiting_clarification`, `new_brief_required`, and `single_fallback`
  literally. A fallback uses the existing Phase 5A path with one disclosed
  worker, the packet, and its authoring contract; never pretend it is three.
  Other stops create no worker; `reframe.repair` cannot recover an activated
  team's `new_brief_required` or terminal `kill`.
- Only `handoff_ready` permits exactly one research worker. Give it the packet,
  candidate authoring contract, panel, choice review when present, synthesis,
  and handoff; include the exact handoff hash and observable agent/model labels
  in one `stage_and_commit`; never use `stage_only` or `commit_staged`, and stop
  after framing.

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
- Do not rewrite `run.json` or treat a recorded host failure as abandonment.
- Do not use `reframe.repair` as generic abandonment, to replace an activated
  team run, or to infer a repair target or successor brief. An exact retry must
  recover the bridge-persisted disposition and successor rather than navigate
  afresh.
- Do not use `finish` as a generic pause or handoff marker.

When the bridge has not delivered a packet, do not begin scientific generation.
