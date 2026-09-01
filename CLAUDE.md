# Econ Theorist AI v2 — Claude Code host adapter

<!-- econ-theorist-v2:managed-projection:v1 -->

This is a thin Claude Code projection over the engine-owned, IDE-neutral
machine protocol. It does not define a second research workflow. The engine,
the returned WorkPacket, and the route's authoring contract are authoritative.

## When to use it

Use this adapter only when the researcher explicitly asks to initialize,
inspect, continue, repair, or run an Econ Theorist AI v2 pure/applied theory
project. Ordinary explanation, coding, or empirical/econometric work does not
activate v2.

## Operating contract

1. Work only in the exact project root named by the researcher. Do not scan
   parent or sibling directories, and preserve user-owned files and unrelated
   working-tree changes.
2. Use the installed host-neutral protocol, not legacy route commands:

   ```text
   etai machine invoke --request REQUEST.json
   ```

   The request must conform to
   `schemas/machine/v1/machine-request.schema.json`. Standard output is one
   canonical `MachineResponseV1` JSON object. If the executable is not
   installed, stop and report the installation/doctor requirement.
3. Let the engine bind or inspect the project, choose the next legal bounded
   route, open/resume the run, deliver the exact WorkPacket, and validate the
   candidate. Do not choose or reorder routes, infer a theorem, or create a
   human decision from chat convenience.
4. Treat the returned WorkPacket and `candidate_authoring_contract` as the only
   scientific context and output contract for that run. Do not add remembered
   journal rules, source cards, prompts, or content from another run.
5. If the required outputs jointly name `LiteratureEvidence`,
   `ClosestTheoryMap`, and `AbsorptionAssessment`, acquire fresh closest-theory
   evidence before authoring. Use online search only with separate
   privacy/egress permission, or an explicit project-local offline bundle.
   Bind it to the current packet and head; metadata, abstracts, snippets, and
   model memory are not full-text evidence and cannot support `proceed`.
6. Write only to the packet-declared shadow/candidate paths. Never write
   canonical ObjectStore bytes directly. Complete through
   `candidate.complete` and report success only when the engine response is
   `committed`.
7. Surface `blocked`, `repair_required`, `human_decision_required`,
   `ambiguous_next`, privacy failures, and other non-success outcomes exactly;
   stop when the researcher must decide. Retry the same operation key after an
   interruption rather than opening a replacement run.
8. The generic machine protocol is currently a single-route host surface. Do
   not simulate the Codex-specific framing or theorem team bridge, claim
   multiple agents, or expose a sealed packet to another model unless a future
   Claude projection explicitly declares that engine surface and its isolation.

For the full scientific boundaries and recovery rules, read the engine-owned
`.agents/skills/econ-theorist-v2/SKILL.md` and
`docs/implementation/machine_protocol_v1.md`; do not copy their route-specific
instructions into this file.

<!-- /econ-theorist-v2:managed-projection:v1 -->
