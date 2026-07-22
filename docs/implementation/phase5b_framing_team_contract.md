# Phase 5B.0 Framing Research-Team Contract

Status: researcher-authorized contract with an implemented noncanonical
binding/persistence slice; host orchestration and a real-model pilot remain
open, and no research-quality or multi-agent-benefit claim is made

Scope: `frame.question_and_benchmarks` only

Priority amendment date: 2026-07-22

## 1. Outcome

Phase 5B.0 adds one small research team around an immutable, engine-produced
`frame.question_and_benchmarks` WorkPacket. A mentor challenges the frame, two
sealed collaborators propose genuinely different directions, the researcher
selects or rewrites the direction in natural language, and one research worker
authors the candidate through the existing Phase 5A completion path.

This slice tests whether role-separated AI collaboration makes the research
conversation more useful. It does not create a general agent platform, a
second scientific workflow, a new route, a new scientific schema, V9, a new
validator, or a new human Decision kind.

## 2. Product boundary

The researcher discusses the question, benchmarks, contribution, risks, and
preferred direction. The engine or host projection owns ids, hashes, lane
bindings, storage, retries, and handoff mechanics.

The slice ends after the existing framing route commits, requests repair, or
fails. It does not automatically start primitive decomposition, a framing
audit, G1, or any later route. No output establishes research quality or a
causal advantage over one capable model.

When the team surface, required isolation, or privacy clearance is unavailable,
the system exposes an honest `single_fallback` and preserves the existing
single-worker path. It never fabricates independent opinions.

## 3. One immutable scientific base

The existing engine first legally opens or resumes one framing route and
produces WorkPacket `P`. Every team record binds the same:

- project id;
- route id and route-run id;
- base head;
- WorkPacket hash;
- context-manifest hash;
- compiled-context hash; and
- run-input-brief hash, including an explicit null value when absent.

All advisory lanes receive the exact scientific bytes of `P` plus one small
role overlay. The overlay assigns a research responsibility and free-text
output shape; it does not copy, weaken, or extend the route instructions,
validator, allowed operations, privacy clearance, or output contract.

A changed head, superseded packet, mismatched binding, or changed input brief
makes the whole team session stale. The host stops and obtains a fresh engine
packet. It does not automatically rebase advice, substitute a packet, or carry
the old researcher selection forward.

## 4. Sealed advisory lanes

The first slice has exactly three advisory outputs:

1. **mentor** -- challenges question sharpness, benchmark choice, importance,
   contribution radius, hidden assumptions, and continue/simplify/pivot/park/
   kill conditions;
2. **collaborator A** -- proposes one defensible question-and-benchmark frame;
3. **collaborator B** -- proposes a materially different defensible frame.

Collaborators do not see each other's output, the mentor's completed output,
the eventual researcher selection, or worker output while authoring. The
mentor does not see collaborator output. Logical sealing is sufficient for the
trusted-local exploratory profile when recorded honestly; it is not described
as cryptographic or cross-provider independence.

An advisory lane may reason, criticize, and write free-form Markdown. It may
not write the candidate path, call `candidate.complete`, write canonical
ObjectStore bytes, confirm a human gate, expand filesystem or source scope, or
delegate again. Agreement is correlated advice, not scientific evidence.

## 5. Noncanonical operational records

Team records are immutable, content-addressed operational sidecars under the
route run. They inherit the packet's privacy and retention boundaries and are
never canonical research objects.

The minimum records are:

- `FramingTeamPlanV1`: the exact packet binding, declared execution/isolation
  mode, three role overlays, and the single-writer constraint;
- `FramingLaneOutputV1`: lane id, role, observable agent/model label when
  available, common packet binding, and free-form Markdown;
- `FramingTeamPanelV1`: one mentor output and exactly two collaborator outputs,
  preserving all three by digest;
- `FramingResearcherSynthesisV1`: exact common binding, panel hash, researcher
  id, natural-language synthesis, selected lane ids, and a non-gate
  disposition; and
- `FramingWorkerHandoffV1`: panel and synthesis hashes, the existing candidate
  path and completion operation, and one bounded worker brief.

The sidecars record model/provider facts only when observable. They do not
store private chain of thought. Selecting one proposal never deletes or
overwrites the mentor critique or the other proposal.

## 6. Researcher choice and authority

The researcher may select A, select B, combine them, rewrite them, reject all,
or request another bounded panel. Ambiguous natural language remains
`awaiting_clarification`; the system does not infer a structural choice.

`continue`, `simplify`, and `pivot` require a worker brief. `park` and `kill`
produce no worker handoff. This disposition directs the current framing
candidate only. It is not G1, does not create a canonical `Decision`, and does
not authorize a later route or external action.

If the researcher materially changes the question, requested scope, privacy
policy, or framing intent beyond `P`, the team session returns
`new_brief_required`. The existing engine must then create a newly bound input
brief and WorkPacket.

## 7. Single worker and existing completion

Only one `research_worker` receives the original WorkPacket, preserved panel,
researcher synthesis, and bounded handoff. The WorkPacket remains the sole
scientific instruction and output contract; the sidecars are attributed advice
within that contract.

Only the worker may write the packet-declared candidate/shadow paths and call
the existing `candidate.complete`. Existing validators, repair budgets,
candidate capture, atomic commit, exact retry, stale-base behavior, and human
gates remain unchanged. A team sidecar cannot make an invalid candidate valid.

## 8. Minimal state and failure behavior

```text
eligible_packet
  -> advisory_lanes_open
  -> advice_ready
  -> awaiting_user_choice
  -> handoff_ready
  -> worker_running
  -> existing_completion_result
```

Bounded branches are:

- duplicate collaborator proposals -> one diversity repair -> advice or a
  visibly degraded offer;
- ambiguous user text -> `awaiting_clarification`;
- material scope change -> `new_brief_required`;
- changed head or packet -> `stale_team_session`;
- unavailable team capability or isolation -> `single_fallback`; and
- `park`, `kill`, or user cancellation -> no worker handoff and no canonical
  write.

## 9. First implementation and acceptance

The first implementation adds only a noncanonical framing-team module and
focused tests. It must not modify frozen Phase 1--4 payloads, WorkPacket v1,
CapabilityReceipt v1, route registries, route instructions, framing schemas,
V8 validators, or the canonical commit path.

This first module trusts a future local host to supply the direct-user capture
and the semantic classification `clear_within_packet`. It records those claims
but does not itself observe UI gestures, classify ambiguity or material scope
change, dispatch models, or implement fallback. Until the thin host projection
provides and tests those controls, the module is a binding/persistence slice
and must not be exposed as a complete research-team pilot.

Focused acceptance demonstrates:

1. one mentor and two distinct collaborators share an exact packet binding;
2. wrong route, packet, run, project, base, context, or input binding fails
   closed;
3. sealed lane outputs remain separately inspectable after selection;
4. ambiguous selection, `park`, and `kill` cannot create a worker handoff;
5. one synthesis produces exactly one worker handoff and no human Decision;
6. content-addressed publication is idempotent and tampering is detected;
7. creating or reading team records does not move the canonical head;
8. `single_fallback` leaves the existing Phase 5A route usable; and
9. a later real framing pilot records user interventions, useful disagreement,
   and friction without claiming multi-agent superiority.

Only the focused Phase 5B.0 tests are required during implementation. Run the
complete non-long suite and exporters once before declaring the slice stable,
not after every small edit.
