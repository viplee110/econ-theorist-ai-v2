# Implementation plan

Status: Architecture v0.1 with accepted Phase 1--4 implementations, the Phase
5A.0 host-bootstrap contract, and the Phase 5A.1 generic machine facade on
`main`; one Phase 5A.2 public Codex functional slice is recorded, and the
current tree contains a deterministically accepted additive registry-v8
framing-quality implementation candidate. V8 adds only a narrow, non-G1
negative-diagnosis exit for an upstream graph that cannot honestly support an
active-margin witness. R2 and the researcher-authorized R3 revision both
committed framing and decomposition but no audit. Locked R3 adjudication
classified the current failure `STRUCTURAL_TAX_PRIMARY` (0.86) and found no V8
validator defect. A noncanonical semantic-compiler prototype now validates the
locked R3 diagnosis under unchanged V8 semantics. The held-out paired shadow
is complete: neither arm reached V8, while Semantic V2 substantially reduced
structure and improved reader recovery without established material scientific
degradation. A fresh WorkPacket-only end-to-end route and the full local
research-ready gate remain open.

The first Phase 5B case has since completed its frozen noncanonical
nondegeneracy probe (`PARK`, 0.95), and the researcher selected Scheme B: a
score-blind final rule strictly increasing in the review signal, with
`phi(s,r)=r` as the minimal baseline. A developer-assisted, nonblind follow-up
canonically committed the PrimitiveGraph repair, dependent decomposition
refresh, and unchanged-V8 audit at checkpoint head
`aea3e7a77ab7a3dc0e4d0b334403eb6d9df38a69bf3ddbca730075e6728fd230`.
The researcher then authorized replacing the ResearchQuestion's unsupported
strict `frontier` with an outcome-vector comparison/locus without adding
capacity or optimization. A clean continuation under the restored strict
Phase-2 validator committed the dependency repair, decomposition refresh, and
fresh unchanged-V8 audit at
`bf4e7fdd49bcf089b18318e77075514cbaea027939049113d1d5840073b4800c`.
Exact replay passes and the audit proposes `ready_for_g1`; no human G1 decision
occurred. The recovery remains developer-assisted, nonblind evidence rather
than a fresh model or research-quality result.

Current implementation milestone: bounded authoring and diagnostic repair
implemented. Semantic V2 now compiles only explicitly located force margins
and deterministic witness mechanics while preserving model-authored force
source/target; no margin position defaults or topology inference are allowed.
Transaction detail is limited to a unique single-field near-match. The shadow
publisher accepts one strict duplicate-free JSON object and uses atomic no-
replace publication with an immutable completion receipt. Focused source-level
private-oracle and adversarial checks pass. Exact-wheel packaged-runtime
transport/oracle verification also passes: both surfaces validate under
unchanged V8, produce an identical scientific projection, and write no
canonical state; wrong-base rejection remains closed. This is deterministic
self-test evidence, not fresh model evidence. The 2026-07-22 researcher
priority decision stopped additional protocol-only paired runs. The minimal
researcher-facing Phase 5B framing team and its first real framing-only pilot
are now complete at the source-aware machine-path level: M passed, T was mixed,
U was not established, and a source-isolated candidate-only model cold read
rated Q mixed. The exact [pilot evidence summary](../../review_outputs/phase5b0_framing_team_public_pilot/evaluation_summary.md)
binds those claims to the engine commit, wheel digest, and observable model
labels. The probe and bounded Scheme-B follow-up are now recorded in the
[sibling evidence archive](../../review_outputs/phase5b0_framing_team_public_pilot_followup/FOLLOWUP_SUMMARY.md).
The next scientific step is an explicit researcher G1 review of the exact
ready proposal; do not activate a `ResearchMove` batch until that human choice.
A new held-out authoring pair may be resumed only when a concrete product
failure makes that comparison decision-relevant. V9 and an exploratory v1/v2
quality claim remain blocked. See
the exact [packaged-runtime verification](../../review_outputs/phase5a2_v8_authoring_pair_v2/packaged_runtime_verification.md).

## 1. Delivery strategy

Implementation should proceed by thin end-to-end slices. The project must demonstrate that a research object can be created, challenged, invalidated, explained, and recovered before it accumulates a large prompt library or dozens of schemas.

The first useful system is not a manuscript generator. It is a reliable theory-project substrate that can carry one small argument from benchmark to a verified, readable result block while preserving human authority and invalidating dependent work when an upstream object changes.

The first useful product is also not a protocol demonstration. A researcher
should be able to bring a question, discuss scientific choices with an AI
research team, and receive useful exploration and execution without
transcribing object ids, route names, or transaction structure. After the
bounded substrate exists, real research use takes priority over additional
host matrices, protocol-only blind pairs, or hostile-environment hardening.

## 2. Phase 0 — freeze Architecture v0.1

### Deliverables

- architecture constitution and anti-goals;
- positive theory kernel specification;
- state, authority, dependency, context, and recovery model;
- manuscript compiler and reader-model specification;
- theory-only profile and craft-library design;
- v1 capability migration ledger;
- v1/v2 evaluation protocol;
- paper walkthroughs for four representative scenarios.

### Required walkthroughs

1. **Greenfield discovery:** rough theoretical question → benchmarks → competing mechanisms → micro-examples → formal implementation → central result → validated argument → introduction/result block.
2. **Existing theory manuscript:** ingest model, claims, proofs, and expert comments → reconstruct economic/formal objects → diagnose mechanism and exposition debt → revise without overstating scope.
3. **Foundational pure theory:** develop a representation, characterization, equivalence, or impossibility result without fabricating comparative-static, equilibrium-feedback, welfare, or policy fields.
4. **Upstream change:** alter a primitive or assumption after a result block exists → preview blast radius → supersede the decision → invalidate exact proof and prose dependencies → reverify and recompile.

### Exit criteria

- terminology and document ownership are consistent;
- the v1 ledger has no unclassified core capability;
- the evaluation protocol is frozen before generator optimization;
- the user confirms the structural decisions listed in Section 9;
- no production implementation is needed to resolve a known design contradiction.

## 3. Phase 1 — walking substrate

Build the smallest reliable runtime.

Implementation status: the walking substrate and its adversarial acceptance suite were reviewed and merged into `main` at `3ce5c6b8c92fbcbefb361b319a70894e173b119f`. Phase 1 is accepted; this does not imply that later theory, authoring, or release capabilities exist.

### Initial persistent objects

- project metadata and revision;
- artifact references and hashes;
- decisions and authority;
- immutable transaction events;
- run/context manifests;
- a minimal generic entity/relationship container sufficient for the first scenario.

### Initial commands

```text
etai init
etai validate
etai status
etai begin <route>
etai commit <run>
etai stale --why <entity>
etai recover
etai render
```

### Required behavior

```text
init
→ create valid state
→ begin isolated run
→ stage proposal
→ validate authority and hashes
→ commit atomically
→ mutate an upstream entity
→ derive downstream staleness
→ rebuild one compact status view
→ recover from an interrupted transaction
```

### Exit criteria

- schema, authority, dangling-reference, dependency-cycle, hash-conflict, and recovery tests pass;
- state is replayable from genesis committed transactions, or from a snapshot whose chain hash is verified plus later committed transactions;
- a human-owned artifact cannot be silently overwritten;
- generated Markdown is demonstrably non-canonical;
- architecture-budget tests enforce bounded always-on and route contexts.

## 4. Phase 2 — theory-kernel vertical slice

Implementation status: the vertical slice was reviewed and merged into `main`
at `6a14d52e4655dc8b7d5a42e43467f4c58faba510`. Phase 2 is accepted as a
semantic/runtime milestone, not as evidence that an AI generator has reached
publication quality.

Implement only the objects and routes needed for one complete theoretical argument:

- research question and benchmarks;
- primitive/economic argument graph;
- competing mechanism hypotheses;
- frozen prediction register;
- an archetype-sensitive example suite whose required functional roles are explicit rather than fixed to an E0–E3 count;
- formal model and formalization map;
- assumptions, claims, proof obligations, and closest-theory evidence;
- result portfolio and validated argument package.

The first case should be synthetic or based on public theory material and must be small enough to solve by hand. It must contain a rival mechanism and a boundary environment; a polished toy outline is insufficient.

### Exit criteria

- mechanism and implementation tournaments are operationally distinct;
- failed predictions remain visible;
- benchmark closure, mechanism ablation, rival separation, assumption distance, boundary witness, arrow coverage, and absorption translation tests run;
- numerical corroboration cannot certify a universal theorem;
- all applicable G1–G5 promotion decisions are recorded; reversible exploration may bundle decisions, but G3 formal-base and G5 argument-validation authority cannot be skipped before authoring-ready promotion.
- one real ObjectStore chain crosses G1 through G5, records the human G5
  Decision, derives a fresh validation closure, and replays exactly from
  genesis;
- a real absorption mutation makes the G4 dossier, argument package, and G5
  closure stale while preserving the exact bytes of the formal model, claim
  graph, verification records, and verification bundle, with only G1--G3
  remaining scientifically effective;
- one sealed confirmatory attempt executes `prepare.blind_case` and
  `evaluate.blind_argument_package` through begin, isolated context, stage,
  preflight, commit, and replay, ending in one terminal comparison;
- evaluator independence is enforced before any gold-bearing context is
  compiled, and historical v1 replay cannot be used as a live Phase 2 write
  downgrade;
- the frozen Phase 1 byte oracle remains unchanged and passes byte-for-byte.

## 5. Phase 3 — assurance and authoring vertical slice

Implementation status: the executable vertical slice in
`docs/implementation/phase3_contract.md` is implemented. Registry v3 preserves
the frozen v1/v2 policy meanings while enabling the assurance, authoring,
cold-reader, closure, and effort routes required by this slice.

All ten Phase 3-native routes validate exact input IDs, revisions, and lineage
in their immutable run focus in addition to registry type/cardinality. That
focus's current `EntityVersion` set equals all `EntityVersion` evidence in the
transaction; same-type objects from a foreign authoring chain fail closed. The
provider-visible refs are a narrower privacy projection and may exclude the VAP
for blind re-derivation. Assurance nevertheless treats the VAP as authority:
its `ClaimGraph`, `FormalModel`, `AssumptionMap`, and `VerificationBundle` refs
must match exactly. Each re-derivation selects one obligation/verification pair
from that bundle, the assurance audit forms a same-package bijection over all
bundle `VerificationRecord`s, and review closure explicitly selects the exact
current `AssuranceBundle` governing its manuscript.

Implemented:

- independent re-derivation;
- symbolic checks and counterexample harness;
- proof audit bound to exact revisions;
- Paper IR and reader-belief states;
- section and result-block contracts;
- layered claim expressions and entailment checks;
- one canonical writer plus isolated fidelity/economic-reader critics.

The real gold chain continues the accepted Phase 2 ObjectStore history. It
performs three obligation-scoped blind re-derivations and a multi-record
assurance audit, then composes a first manuscript that fails the economic and
cold-reader gates. A typed revision brief returns only the unresolved work to
the same canonical writer; the superseding manuscript reaches
`authoring_ready` only after fresh formal, economic, and cold-reader review.
Re-derivation, audit, harness, manuscript, probe, sealed-key, response, and
revision-brief claims are checked against their actual immutable artifact
bytes. Cold-reader contexts enforce writer/probe/key separation, and
append-only telemetry records active human minutes and semantic edit category.
Every non-whitespace manuscript-body character is covered by a typed span;
economic-reader and cold-reader acceptance is closed per `ResultPacket`; and
readiness requires every upstream scientific, assurance, authoring, artifact,
and review dependency to remain current and fresh.

The long Phase 3 gold suffix has a visible performance cost from repeated
replay plus operational lineage and artifact-byte validation. Safe incremental
or cached validation is a later optimization task, not a reason to weaken the
acceptance predicate.

Working and submission compilation consume the exact G5-approved `ValidatedArgumentPackage` revision. Preview compilation may consume a bounded provisional package but cannot promote it.

The local submission compiler consumes an exact authoring-ready working unit
and its effective human promotion Decision. It permits formatting and derived
offset changes only; wording, typed assertions, source bindings, and scientific
content must remain unchanged. External submission execution remains an L3
deferral.

This milestone establishes a trustworthy one-result-block authoring core. It
does not establish complete-paper capability, held-out superiority to v1, or
acceptance probability at Econometrica, a Top-5, or a leading field journal.

### Exit criteria

- a central result can be traced from reader-facing prose to claim, assumptions, mechanism, example, proof status, and evidence revisions;
- a theorem statement remains formal while nearby prose supplies benchmark, translation, mechanism, boundary, and proof roadmap as needed;
- every non-whitespace manuscript-body character has one typed span, and every
  ResultPacket independently receives economic-reader and cold-reader coverage;
- authoring readiness fails when any member of its exact dependency chain is
  superseded or stale;
- all native routes reject same-type foreign inputs; re-derivation accepts one
  exact `ProofObligation` and closure explicitly consumes its exact
  `AssuranceBundle`;
- immutable focus equals complete transaction EntityVersion evidence, while
  blind provider visibility may omit VAP prose; assurance binds the VAP's exact
  internal refs and a re-derivation bijection over its `VerificationRecord`s;
- changing the theorem scope invalidates all stronger prose but not unrelated sections;
- cold-reader retell and prediction-transfer tests are executable;
- substantive human-edit categories and time can be recorded.

## 6. Phase 4 — profile and craft system

Implementation status: accepted Phase 4 implementation `63d3393` was merged
into `main` by `89d2152` against the frozen Phase 3 base after an independent
final adversarial branch review found no blocking findings. `registry.v4.json`
is an additive catalog: every v3 route
entry and instruction remains byte-identical, and only these eight native v4
routes are added:

```text
map.obligation_predicate
audit.obligation_predicate
resolve.profile_stack
diagnose.reader_problem
retrieve.craft_moves
compose.profiled_manuscript_unit
review.craft_realization
close.profile_craft_review
```

The implementation adds a separate strict `profile_craft` payload/schema
namespace instead of changing Phase 1--3 objects. A pinned 18-card seed profile
catalog supplies the universal floor, two theory modes, three ambition levels,
six result archetypes, one provisional information-economics field calibration,
and five audiences; no named-journal overlay is active. A separately pinned
theory-only seed craft corpus supplies one supported functional move, two
independent matched source lineages, one project-owned contrast, and an
explicitly excluded empirical decoy. The writer sees only release-cleared
internal functional projections and project semantic inputs, not source prose, anchor
identity, corpus search results, or hidden reader probes and keys.

Obligation mapping now exactly reruns the Phase 3 executable receipt and binds
real immutable clause locators, witness, mutated-predicate, and mutation-result
bytes. Clause locators are JSON Pointers into the executed predicate. Five
mandatory downgrade controls are evaluated: empty domain, constant true,
conclusion flip, and domain narrowing execute as recomputations; omitted
assumption retains the same predicate bytes and becomes a typed unexecutable
control with
`execution_outcome=unencoded_assumption_not_executable` when the bare predicate
has no assumption component. That outcome forces a warning and prohibits exact
approval; it is not reported as an executed or killed mutant. The independent
audit has two non-upgrading approval lanes: `approved_exact` is available only
to exact coverage with the stronger nonvacuity evidence, while
`approved_partial` may approve an honestly bounded partial or diagnostic
mapping only after all executable controls are replayed and every unexecutable
control is represented by a typed limitation. Those limitations are preserved
in the audit and projected into Phase 4 closure; partial never becomes exact by
omission downstream. In the real gold chain, the inherited finite
counterexample scan therefore stays `diagnostic`/`approved_partial`; it is never
promoted to a universal proof.

The target profile binds four exact current human L2 Decisions together with
the exact current Phase 3 package, Paper IR, reader path, and base profile
manifest. Foreign, superseded, or stale bindings invalidate the stack and all
dependent Phase 4 work. A fresh target-specific review fails the same canonical
Phase 3 `ManuscriptUnit` v2 and produces a blocked `ReviewClosure` plus exact
`RevisionBrief`. The diagnosis must project the exact blocking findings and
instructions, typed causal class, affected section roles, resolution
requirements, and four non-interchangeable semantic source selectors. Only a
local-exposition failure enters retrieval. The function-first selector then
computes a deterministic minimum-cardinality set cover v2 over those exact
requirements, with a stable lexical tie break. The seed release currently
contains one move with exact typed extractors for `mechanism_explanation` and
`comparative_statics_threshold`; it is not evidence of broad archetype or
craft coverage.
The same canonical-writer identity then supersedes that same entity from v2 to
v3; there is no `ProfiledManuscriptUnit` payload or alternative manuscript
entity. Exact `governs`, `realizes`, `depends_on`, and historical trace relations
carry the Phase 4 lineage. Fresh Phase 3 formal, economic, and cold-reader
reviews, an internal derived-field n-gram phrase scan, and an independent
`CraftRealizationAssessment` must then verify every requirement's assertion,
section, and ordered Phase 4 semantic-source realization; every active directive's observable
acceptance criterion; and target-reader recovery of the benchmark, operative
force, boundary, and nearby case. Only a deterministic noncompensatory
`ProfileCraftClosure` may then establish `PROFILE-CRAFT-READY-0.1`. Phrase,
source-access, and voice controls are bounded internal safeguards, not
plagiarism, copyright, authorship, or legal certification.

Phase 4 semantic-input evidence is recorded independently on each
`CraftMoveRealization` as an ordered input-to-`SemanticFacetRef` projection.
It is deliberately not inserted into the frozen Phase 3
`ConsequentialSpan.source_fields`: those fields continue to contain only the
exact Phase 3 scientific projection sources allowed by the v1--v3 authoring
contract.

The current writer is a deterministic fixture. The checkpoint therefore tests
the real ObjectStore, transaction, validation, failure-repair, review,
freshness, and replay protocol without calling an external LLM, autonomously
generating a paper, or establishing writing quality, Top-5 performance, legal
compliance, or reduced human effort. Current acceptance evidence is an
independent final adversarial branch review with no blocking findings; 82/82
focused Phase 4 non-gold checks; 403 complete non-gold tests passing with five
skips; an uninterrupted full-genesis Phase 1→4 gold test passing in 6156.901
seconds; five exporter checks; `doctor` with
`required_ok=true`; registry v4's 34 routes at
`d81276ed9b7482768840ef89980d6cbb81361ca2ff84acee3ab7da7bb67eae7e`;
compilation of 98 Python files; and `git diff --check`.

The uninterrupted final-code gold test is the primary end-to-end acceptance
evidence. A fresh segmented real-ObjectStore continuation remains additional
historical-integrity evidence: it ran from frozen Phase 3 head
`dfb04a...` through run 52. Independent verification at final head `88b656...`
found 87 entities, all 67 historical entities byte-identical, all 182
historical transaction/artifact/provenance files unchanged,
`replay_at(final.head) == replay(final)`, exactly one current ready
`ProfileCraftClosure`, and diagnostic coverage with all eight typed limitations
preserved. The 6156.901-second uninterrupted runtime leaves full-history replay
as a performance target, but the comprehensive acceptance command now passes.
Performance work must preserve the validation predicate.

### Exit criteria

- discovery behavior does not change merely because a venue overlay changes;
- a target change affects only justified authoring/review dependencies;
- craft retrieval uses matched and contrast anchors by function, not prose similarity;
- source provenance, access status, confidence, non-applicability, and internal copyright-risk controls are recorded without claiming legal certification;
- empirical-paper templates cannot enter the core retrieval set.

The accepted checkpoint additionally verifies real operational-artifact
bytes, exact receipt replay, JSON Pointer clause binding, witness execution, four
executable downgrade recomputations plus the typed omitted-assumption
unexecutable control, writer/retriever context isolation, frozen catalog
compatibility, historical replay, bounded partial-audit semantics, and
target-only selective invalidation. Together with the fresh segmented chain and
current regression evidence above, these establish the revised repair loop.
They do not establish complete-paper coverage, a broad production craft corpus,
held-out quality superiority, lower human effort, external-LLM performance, or
publication readiness.

The evidence-informed discovery extension in
`scientific_discovery_craft.md` is deliberately outside the accepted Phase 4
behavior. It proposes a separate, noncanonical `ResearchMove` library for
question, benchmark, model, mechanism, and theorem discovery; it does not
overload the implemented local-exposition `CraftMove`, add a route or gate, or
change default live WorkPackets before source audit, held-out paired
replication, and an experimental end-to-end pilot justify activation. A
source-audited, disabled-by-default projection may be used earlier in an
explicitly authorized research-team pilot without making a quality claim.

## 7. Phase 5 -- host adaptation and controlled multi-agent execution

Phase 5 is split into two capability groups with a bounded exploratory overlap.
Phase 5A makes the accepted single-agent core safely installable and operable
from supported coding-agent hosts. Once its bounded exploratory floor is
demonstrated, Phase 5B adds the researcher-facing AI team and optional
research-tool adapters while the complete 5A release gate remains open. This
split does not add a seventh implementation phase or move comparative claims
out of Phase 6.

The active target is trusted local self-use. Two gates are distinct:

- **research-ready:** one selected local host can execute the scientific core
  reliably enough to run real theory work and diagnostic quality pilots;
- **public-distribution-ready:** broad host/platform support, signed release
  infrastructure, and hostile-environment hardening.

The bounded exploratory floor is the prerequisite for product learning; the
complete research-ready gate is the prerequisite for formal Phase 5B
acceptance and a local release claim. Public-release hardening must not postpone
the first real paper route.

### 7.1 Phase 5A -- host bootstrap and natural-language onboarding

The normative design and acceptance owner is
`../implementation/phase5a_contract.md`.

Required thin slices are:

1. **5A.0 -- contract and status repair:** freeze the two-layer user/machine
   experience, host trust boundary, capability contract, cross-host parity,
   installation safety, and acceptance matrix without runtime claims;
2. **5A.1 -- generic machine facade:** add structured, idempotent bootstrap,
   read-only existing-project compatibility, derived run lifecycle, compact
   inspection, sound navigation probes, safe open/resume, trusted-human and
   egress approvals, host-neutral work packets, delivery envelopes, and host
   receipts;
3. **5A.2 -- Codex research-ready slice:** pass natural-language onboarding or
   continuation and one real theory route through the common protocol, ending
   in a validated committed candidate;
4. **5A.3 -- portable-host smoke tests:** add Claude Code and Cursor thin
   projections when useful, without blocking Codex-based scientific work;
5. **5A.4 -- local release usability:** package a pinned local release and
   verify ordinary install, update, recovery, and generic CLI use;
6. **5A.5 -- optional public-distribution hardening:** only before making broad
   security/support claims, add signing, revocation, locked supply-chain,
   hostile-host, full platform, and expanded conformance evidence.

The public part of 5A.2 is recorded in
`../../review_outputs/phase5a2_codex_public_pilot/`: a prepared Codex checkout
completed one public `frame.question_and_benchmarks` route and exact completion
retry. A final-wheel continuation smoke selected `decompose.primitives`. This
does not close the research-ready criteria below because positive non-public
execution, clean first-use activation, and a broader real-workflow diagnostic
remain unproved. A separate model-based diagnostic also found material
benchmark and readability defects, so the next slices are selected by those
failures rather than by generic infrastructure expansion.

A later frozen V8 blind pilot is recorded in
`../../review_outputs/phase5a2_v8_codex_public_pilot/`. It canonically committed
`frame.question_and_benchmarks` and `decompose.primitives`, then exhausted the
declared repairs on `audit.framing_economics`. Its honest `revise_framing`
candidate remained noncanonical, no replacement dossier or G1 decision was
committed, and the final `failed_terminal` value is an operational host receipt
rather than a canonical route disposition.

The additive v8 implementation candidate is specified in
`../implementation/framing_quality_contract.md`. It inserts
`audit.framing_economics` after primitive decomposition and before the human G1
decision, preserving the frozen v1--v4 route meanings. It must pass its
deterministic acceptance predicate and a successful fresh real-Codex v8 rerun before any
claim about improved readability or lower human intervention. The
deterministic predicate passed. The first real-model attempt did not commit the
audit and exposed post-pilot host/diagnostic defects. Those later fixes passed
their deterministic stabilization gate. The corrected-wheel R2 same-case run
then traversed the host path cleanly and committed framing and decomposition,
but its audit exhausted two repairs and recorded `failed_no_effect` without a
canonical audit transaction. Independent adjudication subsequently returned
machine-mixed, `A-FAIL` (`0, 1, 1, 2, 2`), `REVISE`, and `R-FAIL`/H4. It found
a primary model-content/mapping error and secondary diagnostic ambiguity, not
an established acceptance-semantics defect. A post-evaluation diagnostic-only
patch adds exact paths for fixed/endogenous and endpoint failures without
changing V8. The human-authorized guaranteed-service R3 sequence and the later
held-out accident-liability pair are now complete. Neither pair arm reached
unchanged V8 within three attempts, but Semantic V2 reduced final source bytes
by 51.22% and leaf fields by 53.74%, preserved the core economics, and improved
detailed reader recovery. Locked source inspection identified residual
deterministic graph binding and nonlocal diagnostics as the next boundary,
without finding a V8 defect. The bounded noncanonical repair now requires an
explicit cited-step margin position, provides only unique single-field
Transaction near-matches, and has passed focused source-level private-oracle/
adversarial checks under unchanged V8. Exact-wheel packaged-runtime transport/
oracle verification also passes with byte-identical scientific projections and
zero canonical writes. The 2026-07-22 priority amendment supersedes a new
protocol-only held-out pair as the default next slice; resume such a pair only
when a concrete researcher-facing failure makes it decision-relevant. See the
[final pair adjudication](../../review_outputs/phase5a2_v8_authoring_pair_v2/final_adjudication.md)
and [packaged-runtime verification](../../review_outputs/phase5a2_v8_authoring_pair_v2/packaged_runtime_verification.md).

The ordinary researcher-facing interface is natural language. The machine
layer remains a versioned `etai` protocol, and the terminal path remains
available for automation, recovery, tests, and advanced users. A first-use
host/OS permission may be required; one-sentence onboarding never means
silently bypassing installation security or L2/L3 human authority.

#### Phase 5A research-ready exit criteria

- Codex can initialize or continue the selected project from a natural-language
  request without command transcription;
- one real theory route completes `packet -> model candidate -> validate ->
  stage/commit`; a deterministic writer fixture is insufficient;
- exact retries do not duplicate genesis, runs, delivery, or commits, and an
  ordinary interruption is recoverable;
- the host does not overwrite user-owned paper or instruction files and never
  writes canonical ObjectStore bytes directly;
- unresolved structural Decisions stop promotion;
- the exact private packet is inspectable, and `local_only` or sealed/blind
  routes stop when real isolation is unavailable;
- the focused suite, non-long regression suite, exporters, and `doctor` pass.

This gate permits exploratory v1/v2 pilots and the minimal Phase 5B lanes
motivated by their failures. It does not establish cross-host parity, public
release security, or comparative superiority.

A bounded public diagnostic may run before the full gate only to expose
scientific or interface failures. It does not authorize Phase 5B acceptance or
Phase 6 comparative claims.

#### Phase 5A public-distribution exit criteria

- Codex, Claude Code, and Cursor can each perform the documented clean
  onboarding request without requiring the researcher to transcribe a shell
  command;
- all hosts use one engine-owned host manifest and the same exact
  route/context/validator semantics;
- repeat onboarding and cross-host continuation preserve one project id, one
  canonical head, derived run view, Decisions, blockers, and work-packet hashes;
- host projections preserve user-owned instructions/files and never overwrite
  human-owned working artifacts or canonical ObjectStore bytes directly;
- non-public provider egress, host memory, secrets, blind compartments, and
  human approvals are enforced by technical scopes/receipts rather than prompt
  promises;
- permission denial, integrity/version failure, ambiguous route, missing human
  Decision, corrupt state, wrong root, and privacy attacks fail without
  canonical scientific mutation;
- signed/locked installation from a release artifact, absolute launcher and
  projection-activation handshakes, `doctor`, CLI independence, recovery,
  update, and uninstall are tested rather than inferred from templates;
- the accepted Phase 1--4 semantics and regression evidence remain green;
- an independent adversarial review finds no blocking supply-chain, privacy,
  authority, project-root, idempotence, or canonical-state violation.

The public-distribution gate proves bounded host portability for one acting
agent. Neither gate proves multi-agent benefit, complete-paper generation,
lower human effort, or Top-5 readiness.

### 7.2 Phase 5B -- researcher-facing AI team and optional research adapters

The normative owner for the first framing-only slice is
[`../implementation/phase5b_framing_team_contract.md`](../implementation/phase5b_framing_team_contract.md).

The current tree implements its noncanonical binding/persistence layer and one
thin public Codex projection over the existing bridge. An exact framing
WorkPacket can declare one mentor and two sealed collaborators, preserve all
advice, record a direct-user synthesis or a typed no-handoff stop, expose an
honest single-worker fallback, explicitly authorize three advisory exposures
plus one terminal-handoff-conditional worker exposure after the original
single-coordinator delivery, and bind at most one terminal worker handoff
without moving canonical state. Worker and handoff provenance is kept in an
additive completion-binding sidecar rather than repurposing the frozen host
receipt's tool identities. One immutable activation fixes the worker per
handoff, and the initial team slice uses only atomic `stage_and_commit` so it
cannot take ownership of a previously staged candidate. Focused tests cover
wrong/stale bindings, idempotence, tampering, minority preservation,
ambiguity, changed briefs, `park`/`kill`, delivery/capture session mismatch,
terminal conflicts, and forged handoffs. Actual model dispatch and semantic
classification remain host responsibilities. One real public framing-only
pilot has now provided [source-aware evidence](../../review_outputs/phase5b0_framing_team_public_pilot/evaluation_summary.md)
for the machine surface and a recorded single-worker completion binding, but
not provider-independent model delivery, strong collaborator diversity,
unscripted user value, or scientific quality. The later frozen probe returned
`PARK` (0.95), and the researcher selected the Scheme-B rule class and baseline,
then separately authorized outcome-vector/locus terminology without capacity or
optimization. The strict-replay recovery committed the dependency repair,
decomposition, and unchanged-V8 audit; the audit proposes `ready_for_g1`, but
no human G1 occurred. A narrow bridge-level `reframe.repair`
composite now handles only an untouched, empty-focus framing-v2 run: it records
a noncanonical operational disposition bound to the exact target, successor
brief, and navigation candidate, then opens that exact dependency repair with
recoverable exact retry. It does not apply to an activated team, so general
recovery after team `kill` or `new_brief_required` remains open and those
statuses still stop an exploratory pilot. The original `p5b1` experimental
lineage after `ed2371...` is negative evidence only because it contains a
failed-route transaction admitted by a reverted validator relaxation; the
separate clean continuation is the replay-valid result.

Begin the exploratory product slice after the bounded Phase 5A substrate has
demonstrated one real route commit, exact retry/recovery, and engine-owned
canonical writes. The still-open full local research-ready gate remains a
release claim, not a blocker on product learning; do not wait for the optional
public-distribution gate.

The minimum slice organizes three functional responsibilities behind one
natural-language research conversation:

- a mentor lane challenges the question, benchmark, assumptions, taste, and
  continue/simplify/pivot/park/kill choice;
- one or more collaborator lanes generate genuinely different mechanisms,
  examples, formalizations, conjectures, and objections; and
- a research-worker lane carries out bounded literature work, derivations,
  proof or counterexample checks, drafting, and revisions after the relevant
  human choice.

Roles are not personas and do not imply three standing agents on every task.
The orchestrator uses the smallest useful team, preserves isolated proposals
and minority objections when independence matters, and gives one canonical
writer the selected work. No lane writes canonical state directly or confirms
a human-owned Decision.

The first implementation order is:

1. expose one natural-language team entry point that hides machine bookkeeping;
2. support mentor advice, rival collaborator proposals, and one worker handoff
   on existing routes without adding a second workflow or new scientific
   schema;
3. run one genuine theory project from question and benchmarks through a
   verified, readable result block while recording researcher interventions;
4. use the observed scientific and usability failures to select the first
   small `ResearchMove` batch from
   [`scientific_discovery_craft.md`](scientific_discovery_craft.md); and
5. keep version control, formal proof, private cross-project memory, and
   advanced symbolic/numerical adapters optional.

#### Phase 5B exit criteria

- the researcher can operate the team by discussing scientific content and
  decisions, without manually authoring machine-protocol objects;
- mentor, collaborator, and worker contributions remain attributable and do
  not collapse disagreement into one unexplained answer;
- multi-agent agreement is recorded as correlated evidence rather than proof;
- raw lanes and exact context manifests remain inspectable;
- a judge cannot confirm a human-owned decision;
- minority evidence cannot disappear merely because a judge selects another
  proposal;
- concurrent proposals preserve exact base heads and never use
  last-writer-wins scientific commits;
- optional adapters cannot weaken privacy, authority, or evidence semantics;
- the core remains usable without any optional adapter; and
- one real end-to-end theory-project pilot records scientific usefulness,
  failure points, and substantive researcher effort before broader panels or
  scholar-corpus expansion.

Phase 5B scales controlled search, criticism, and optional tooling. It does
not replace the canonical writer with prose assembly by committee, turn
agreement into proof, or establish Top-5 quality. Phase 4's single-writer
repair and noncompensatory closure remain the floor.

## 8. Phase 6 — comparative evaluation and hardening

Run the preregistered compiler-only, end-to-end discovery, and revision comparisons on held-out theory cases under the full protocol in `evaluation.md`. Perform v2 ablations for the economic argument representation, reader contracts, mechanism/result packets, dependency invalidation, and craft retrieval.

Phase 5A owns functional, safety, state, and semantic conformance across
supported hosts. A claim that one model or host produces better research,
requires less human effort, or reaches the endpoint more efficiently is a Phase
6 outcome comparison. Because the frozen evaluation protocol initially defines
v1/v2 arms rather than a general model-by-host experiment, any additional
model/host arms and budgets must be added and preregistered before confirmatory
outcomes are inspected.

Phase 2's sealed blind routes establish the protocol and runtime slice only.
Phase 6 supplies the held-out comparative evidence about whether an isolated AI
generator can actually recover high-quality theory more efficiently than the
frozen baselines.

Before any external-release route is enabled, add and verify replayable private backups plus redacted public bundles/receipts on a different machine path. The Phase 1 walking candidate performs no export or external action.

Phase 6 is the first phase allowed to support comparative claims such as
"better than v1," "less human intervention," or "closer to frontier-journal
standards." It still does not submit a paper automatically. A real external
communication or submission remains an L3 human-authorized action after the
evaluation, backup, privacy, and release predicates pass.

### Exit criteria

- the complete versioned predicate `EV-PROMOTION-0.1` in `evaluation.md` is satisfied; this plan does not define a weaker local substitute;
- failure cases become regression scenarios or explicit architecture revisions rather than reasons to move the predicate after seeing results.

## 9. Structural decisions for human review

The following decisions should be confirmed at the end of Phase 0 because they shape implementation substantially:

1. use an immutable transaction chain plus atomic head as the portable source of truth, with a thin typed JSON snapshot as a rebuildable materialized view and no database in the initial core;
2. use route-based control and derived readiness rather than a canonical linear stage number;
3. separate mechanism competition from formal-implementation competition;
4. use a universal frontier-theory floor plus composable soft target overlays;
5. use one canonical manuscript writer and independent critics rather than multi-agent prose assembly;
6. require human promotion of structural scientific decisions while permitting autonomous provisional exploration;
7. make the minimal mentor/collaborator/research-worker team a core
   researcher-facing capability after the local substrate, while keeping
   broader panels, formal proof, version-control automation, and cross-project
   memory optional;
8. preserve Apache License 2.0.

## 10. Proposed repository shape

The implementation layout is a proposal, not a commitment to populate every directory immediately:

```text
econ-theorist-ai-v2/
├─ AGENTS.md
├─ ARCHITECTURE.md
├─ README.md
├─ LICENSE
├─ docs/architecture/
├─ src/econ_theorist/
├─ schemas/
├─ routes/
│  ├─ discovery/
│  ├─ mechanism/
│  ├─ formalization/
│  ├─ verification/
│  ├─ authoring/
│  ├─ review/
│  └─ revision/
├─ profiles/
├─ craft/
├─ templates/
├─ migrations/
├─ tests/
└─ evals/
```

`routes/` is the executable workflow source. Documentation explains it; a second `workflows/` tree must not duplicate it. Directories are created only when their first tested consumer exists.

## 11. Release discipline

- Architecture, schema, engine, route/prompt, profile, and verification-toolchain versions are independent.
- A profile update is not a schema migration.
- Schema migrations are sequential, dry-runnable, checkpointed, and non-destructive on failure.
- V1 remains a frozen comparison baseline; migration imports proposed facts rather than copying all legacy files into canonical state.
- The user's unpublished manuscripts and expert comments stay local unless explicit publication authorization is given. They may be diagnostic cases but never public fixtures by default.
