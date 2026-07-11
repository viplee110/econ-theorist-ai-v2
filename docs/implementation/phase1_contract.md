# Phase 1 Walking Substrate Contract

Status: accepted Phase 1 executable contract

Accepted on `main`: `3ce5c6b8c92fbcbefb361b319a70894e173b119f`

Architecture base: `f30fd51bef78b0ee94f73e7c056c1b28e9789349`

## 1. Outcome

Phase 1 is complete only when a local theory project can traverse this loop without an LLM provider:

```text
initialize a valid project
→ begin an isolated route run at an exact head
→ stage entities, relations, decisions, and artifacts
→ validate hashes, authority, references, facets, and acyclicity
→ commit one immutable transaction atomically
→ supersede one upstream facet
→ derive the smallest stale downstream subgraph
→ rebuild a typed snapshot and a noncanonical status view
→ recover the same head after an injected interruption
```

This phase does not discover results, call model APIs, verify mathematics, or generate manuscript prose. It makes later scientific work inspectable and recoverable.

## 2. Locked implementation choices

- Python 3.11+ with a small `src/econ_theorist` package and an `etai` command.
- Pydantic 2.13.4 with pydantic-core 2.46.4 is the pinned canonical validator; the CLI otherwise uses the standard library.
- Canonical objects use deterministic UTF-8 JSON with sorted keys and no embedded digest field.
- One local `main` head, a mandatory OS-level exclusive commit lock, and atomic same-directory pointer replacement.
- Committed transaction objects and registered artifact bytes are content addressed by SHA-256.
- A typed JSON snapshot and Markdown status page are rebuildable projections. Neither is read as scientific truth.
- `begin_run` replays the canonical transaction chain and requires an exact snapshot projection; a cache with the right head but altered content is rejected.
- Entity payloads are divided into named semantic facets. Phase 1 keeps the container generic; Phase 2 adds theory-specific typed payloads.
- Invalidating dependencies bind exact entity ID, version, facet or field path, and semantic hash.
- Human-owned paths are read-only to the Phase 1 runtime. A proposed replacement is staged as a separate artifact and must carry an expected base hash.
- The complete route registry, allowed operation set, external instruction bundle, theory kernel, selector, decision registry, validator, and isolation policy are independently versioned and hash-bound in each ContextManifest.
- Context budgets record a deterministic estimator identifier and version. Required authority, quantifier, scope, dissent, and stale-blocker material fails closed rather than being silently truncated.

These choices implement the semantics already locked by Architecture v0.1. They do not activate optional multi-agent orchestration, databases, provider APIs, cross-project memory, git automation, or external release.

### 2.1 Resolutions needed to make the design executable

Architecture v0.1 intentionally deferred serialization details. Phase 1 resolves them as follows:

- A transaction revision is its SHA-256 digest. There is no parallel `rev_*` identity.
- Validator reports are immutable artifacts referenced by exact artifact ID, version, and content hash. A canonical `validated` RouteOutcome requires at least one such report; reports are not embedded in the transaction whose digest they validate.
- A dependency records an exact upstream version and semantic hash. Superseding an envelope without changing the bound facet hash does not invalidate that edge; changing the bound semantic hash does. RFC 6901 ancestor/descendant paths denote overlapping semantic regions for both propagation and DAG-cycle validation.
- A Decision's effective revision is derived during replay from the containing transaction digest. It is not stored inside that transaction.
- A new Decision cannot authorize another operation in the same transaction. Its authority can only govern a later transaction.
- For each decision kind, subject, and scope, human Decisions form one effective supersession chain. Unselected agent proposals may coexist outside that chain.
- Phase 1 records a local actor assertion and explicit confirmation as provenance; it does not pretend to provide cryptographic human identity. Strong identity is an adapter-level concern.
- Generic entity payloads are partitioned by the five architecture facets. A supersession's declared changed-facet set must exactly match the semantic diff.
- `scope_sensitive` invalidation initially supports exact `scope_ref` equality or an explicit overlap record. The engine never guesses semantic overlap.
- Pending RouteRuns and ContextManifests are immutable operational records. A committed transaction binds their hashes; a rejected run never becomes canonical scientific state.
- Route provenance is copied into a content-addressed canonical namespace before the head advances. Later replay does not depend on a mutable run workspace: it deterministically recompiles the context from the exact base snapshot and requires byte-for-byte agreement with the preserved context and manifest.
- `frame.question_and_benchmarks` and `repair.dependency` are the only enabled scientific routes in the first walking slice. The remaining Architecture v0.1 IDs are registered but return `not_implemented` until they have typed consumers.
- Phase 1 uses deterministic `etai_lexical_v1` budget units and records that identifier in every manifest. It does not claim equality with any provider's model tokens; a model adapter must recompile against its declared tokenizer.
- `project.json` contains non-scientific local configuration. The canonical `Project` entity is created by the genesis transaction.
- Artifact registration has one canonical representation in a transaction operation. The snapshot caches thin history plus current indexes.
- A human-owned v1 registration names the exact current working-file hash as H0. A replacement must bind the exact predecessor content hash and cannot silently change ownership or logical path; H0/H1/H2 conflicts are reconstructible after a post-head crash.
- Artifact dependencies bind exact artifact ID, version, and content hash. Bare artifact IDs do not establish freshness.
- Canonical entity, relation, Decision, artifact, and blocker IDs share one global namespace. RouteOutcome candidate/report refs, blocker affected refs, and transaction evidence refs are typed exact references; blocker `required_route` must be an exact pinned registry ID. Decision subjects/evidence must resolve; Phase 1 scope, dissent, and affected-scope refs resolve to current Entities.
- A privacy declassification Decision carries a typed exact subject and machine-readable approve/deny outcome. `deny` never authorizes a downgrade, and `local_only` cannot be declassified by project authority.
- Every transaction has a privacy label and compartment set at least as restrictive as its outputs, exact evidence and preconditions, superseded inputs, and actually cited authority basis. Authority preconditions hash the effective Decision projection, not merely the stored Entity fields. Decisions, outcomes, and blockers likewise inherit the privacy/compartment join of the canonical objects they reference; unrelated effective Decisions do not taint a transaction.
- Derived acceptance fields retain their exact Decision-version sources. Each stale reason carries a flattened, exact transitive evidence closure containing every dependency plus its bound and current upstream versions/hashes. If a superseding Entity version leaves the affected facet or JSON Pointer region semantically unchanged, that staleness carries forward to the current version; the corresponding cross-version semantic bridge also participates in invalidating-DAG cycle checks. Context compilation must include and authorize these sources or fail closed; an inaccessible optional neighbor is omitted as one dependency-closed group. Old Decisions and bare scope refs are rechecked against the privacy and compartments of their current referenced objects before entering a context.
- Entity/relation retirement and independent stored-status transition operations are unsupported in this candidate and fail closed. Agents cannot self-assert active, verified, validated, or literature-confirmed status through an EntityVersion write.
- An immutable `run.json` records run creation and therefore has exactly the status `running`; later lifecycle claims never rewrite it. Operational outcome sidecars, including lock-time `stale_base`, are noncanonical. Only an admissible committed `RouteOutcome` operation can become canonical research history, and `stale_base` is not a canonical RouteOutcome value. Candidate-bearing outcomes require exact candidate refs; a completed candidate must reference an output of its containing transaction; failed, interrupted, rejected, or superseded outcomes cannot co-commit scientific entity, relation, or Decision mutations.
- A corrupt or ambiguous head is reported and left untouched. Recovery may rebuild caches from one valid head; it never guesses a replacement canonical head.

### 2.2 Explicitly deferred boundaries

The walking candidate does not implement theory-specific payload schemas, artifact excerpts, verified snapshot checkpoints, public export/private-backup bundles, cryptographic human identity, or a complete retirement/status-transition policy. Export and external release remain disabled until the private/public split and cross-machine tests required by `state_runtime.md` are implemented. This is an explicit deferral, not evidence that those architecture requirements have passed.

## 3. Canonical boundary

The canonical chain owns:

- current and historical entity versions;
- versioned invalidating relations;
- immutable Decisions and their authority evidence;
- immutable artifact registrations;
- the exact parent of every committed transaction.

The following are deliberately noncanonical:

- run workspaces and rejected candidates;
- snapshots, indexes, and generated Markdown;
- console output;
- unregistered files in the researcher's working tree;
- agent conversation history.

A run may fail or lose a head race while its candidate remains inspectable. It becomes scientific state only if its transaction is reachable from `refs/main`.

### 3.1 Transaction-origin contract

The canonical `origin` field has exactly three values. It is not a descriptive label: validation uses it to select the actor, operation, and provenance rules below.

| Origin | Actor binding | Allowed operations | Route provenance |
|---|---|---|---|
| `genesis` | `actor.kind` must be `human` | exactly one `entity.create`, creating the canonical `Project` whose `entity_id` equals `project_id` | `route_id`, `route_run_hash`, `context_manifest_hash`, and `compiled_context_hash` must all be absent |
| `route_run` | the transaction actor must exactly equal the actor in both the immutable RouteRun and ContextManifest | every operation must be in the exact enabled route's versioned `allowed_operations`; Decision writes remain subject to that route's authority ceiling | exact `route_id` plus `route_run_hash`, `context_manifest_hash`, and `compiled_context_hash` are mandatory |
| `human_decision` | `actor.kind` must be `human`, and the transaction actor must exactly equal each Decision's declared decider | `decision.record` or `decision.supersede` only | `route_id`, `route_run_hash`, `context_manifest_hash`, and `compiled_context_hash` must all be absent |

All origins bind `base_revision` exactly to `parent_transaction_hash`; genesis uses `null`, can occur only in an empty store, and cannot recur. Every transaction carries a `route_run_id` as a stable correlation identifier, but only `route_run` origin binds that identifier to canonical route provenance. For `route_run`, the three mandatory hashes address canonical UTF-8 JSON bytes for the RouteRun, ContextManifest, and compiled context. Commit and replay verify those objects, replay the exact base, deterministically recompile the route context, and require byte agreement plus agreement on project, base revision, route/run identity, actor, context, registry and policy versions, instruction bundle, isolation policy, and write allowlist. Genesis and human-Decision transactions cannot borrow route provenance hashes. The transaction digest itself remains outside the canonical transaction body.

## 4. First fixture

The shared `R0` fixture contains:

```text
Assumption A
  └─formal/hard→ Claim C
                    └─formal/hard→ Verification V
                    └─presentation→ ManuscriptUnit M

Independent Result U
Human confirmation Decision D
Human-owned paper.tex at content hash H0
Generated views/status.md
```

The fixture is intentionally smaller than a paper. It is large enough to distinguish a precise facet invalidation from an indiscriminate project-wide stale flag.

## 5. Acceptance matrix

### P1-01 — content integrity

Reject a declared digest mismatch, a simulated digest collision, or a corrupted existing content-addressed object. Keep the canonical head unchanged, never overwrite the older object, and leave an auditable quarantine report.

### P1-02 — competing commits

Let two candidates validate from the same head. After the first advances `main`, the second must re-read the head inside the lock and return `stale_base`. It is preserved as a proposal; it is never rebased or partially committed automatically.

### P1-03 — crash recovery

Expose named fault points after staging, artifact installation, transaction installation, temporary-head write, head replacement, snapshot write, and view write. Before head replacement, recovery yields the old head; after replacement, it yields the new head. Repeated recovery is idempotent.

### P1-04 — human-owned file protection

Begin from `paper.tex@H0`, edit the working file to `H1`, and stage an agent proposal `H2`. The runtime must preserve the working bytes at `H1`, retain all three hashes, and report a reconciliation conflict. It never writes a human-owned path.

### P1-05 — dependency cycles

Allow descriptive non-invalidating feedback relations. Reject a cycle in the invalidating dependency projection as one whole transaction, with no partial relation visible in canonical state.

### P1-06 — facet-level freshness

A terminology-only change stales only presentation dependents. A formal change stales the exact dependent claim, verification, interpretation mapping, and manuscript unit, while independent result `U` stays fresh. A false or incomplete `changed_facets` declaration rejects the whole transaction.

### P1-07 — generated-view nonauthority

Editing `views/status.md` to claim false confirmation or verification must not affect the head, replay, or snapshot. `recover` and `render` restore a view bearing `GENERATED`, `NONCANONICAL`, and `source_head` markers.

### P1-08 — bounded context

For a fixed head, route, focus, privacy grant, and budget, context compilation is deterministic. It retains required authority, exact scope, dissent, quantifiers, and stale blockers; records every privacy or budget omission; and fails before a run starts if required material cannot fit.

## 6. Consistency oracle

Every negative test finishes by checking the same oracle:

1. `refs/main` contains one valid SHA-256 digest.
2. The reachable parent chain is continuous and every transaction filename matches its canonical bytes.
3. Every reachable artifact matches its registered digest.
4. Replaying twice yields the same canonical snapshot hash.
5. A regenerated view reports the same source head as the snapshot and `refs/main`.
6. A rejected or interrupted transaction changed no canonical entity, relation, Decision, or artifact registration.
7. No historical object, generated view, or human-owned working file was used as an in-place write target.

## 7. Delivery slices

Implementation proceeds in four reviewable slices:

1. strict models, canonical serialization, store layout, initialization, and replay;
2. transactions, lock, atomic commit, authority, hash, reference, facet, and DAG validators;
3. route runs, bounded contexts, derived freshness, status explanations, rendering, and recovery;
4. fault-injection subprocess tests, portability checks, schema export, documentation, and v1 parity updates.

No later slice may weaken an earlier oracle to make a scenario pass.

## 8. V1 capability inheritance in this slice

The frozen v1 baseline contributes behavioral contracts, not files to copy:

- its compact `active_context` idea becomes a generated, budgeted context whose source revisions are explicit;
- Auto, Checkpoint, Gate, and Human-only distinctions become route ceilings and immutable Decision authority;
- a human gate proposal retains the reason for stopping, evidence, recommendation, alternatives, consequences, affected objects, and next route;
- failed checks, counterexamples, reversals, and minority findings remain addressable instead of disappearing from a polished dashboard;
- tool discovery becomes an idempotent `doctor` command with structured capability impact; a missing optional tool degrades a route but does not block ordinary theory work;
- pre-edit hashes and expected-base checks protect human changes, while git remains an optional file-level adapter rather than the scientific state machine.

Phase 1 does not copy v1's large `ECONOMETRICA_*` instruction files, free-form duplicated state notes, linear stage number, ignored canonical state, hard-coded Windows tool paths, or empirical/mixed-paper initialization paths.
