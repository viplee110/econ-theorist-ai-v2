# Phase 5A Host Bootstrap and Natural-Language Onboarding Contract

Status: Phase 5A.0 design accepted on `main` by `2192956`; active deployment
scope revised on 2026-07-13 to trusted local research use; the Phase 5A.1 local
machine facade and one Phase 5A.2 public Codex functional slice are complete in
the current tree. A later V8 public diagnostic committed framing and primitive
decomposition but not its framing-quality audit. The corrected-wheel R2
same-case run repeated those two commits without host interference, then
closed its audit as `failed_no_effect`. Independent adjudication returned
machine-mixed, `A-FAIL`, `REVISE`, and `R-FAIL`/H4. A later held-out authoring
pair found large structural and detailed reader-recovery gains from Semantic
V2 but no valid candidate in either three-attempt arm. The full host-native
research-ready gate remains open and no public-release claim is made.

Phase 5A.1 implementation branch (historical): `agent/phase5a-machine-facade`

Accepted Phase 4 base: `63d3393`, merged into `main` by `89d2152`

## 1. Outcome

Phase 5A must make the accepted v2 scientific core safely usable from a
capable coding-agent host without requiring an ordinary researcher to open a
shell or memorize an `etai` command. On first use, a researcher should be able
to say, in substance:

```text
Enable Econ Theorist AI v2 from
https://github.com/viplee110/econ-theorist-ai-v2 in this project.
```

The host then prepares a visible installation plan, requests any permission
that the host or operating system requires, installs an exact supported engine
release, binds the current project directory, initializes or validates the
project, inspects current scientific state, and either opens the uniquely
legal next run or reports the exact human choice or repair that is required.

If the project/question is public, or a verified pre-model/account-level
authorization already covers the provider and opened workspace, the same
sentence may also request "begin studying this question: ...". Otherwise the
first provider-backed-host message contains bootstrap information only; the
researcher supplies non-public research content after the local facade has
presented and obtained the required egress authorization. This remains a
natural-language experience, but privacy may require two messages rather than
pretending the first private message was never transmitted.

After successful onboarding, a researcher should be able to say:

```text
Continue this paper with v2.
Review the economic mechanism under the v2 workflow.
Start authoring under the top-general-interest theory profile.
```

The host may execute the machine interface in the background. Natural language
is a user interface over the canonical engine; it is not a second workflow,
scientific authority, or alternative state store.

Phase 5A establishes a single-agent, cross-host, installable execution shell.
It does not establish multi-agent scientific gains, complete-paper generation,
or comparative quality.

### 1.1 Active deployment profile and precedence

The implementation now distinguishes two acceptance profiles.

**Local research-ready** is the active profile. It trusts the researcher, the
local operating system, the user-selected IDE/account, and the ordinary package
manager. It protects the scientific state from model mistakes, stale or
repeated operations, ordinary crashes, wrong-project writes, accidental
context mixing, and unintended disclosure. It does not attempt to defeat an
attacker controlling the local account, IDE, provider, operating system, or
package infrastructure.

**Public-distribution-ready** is a later optional profile. It owns signed and
revocable releases, fully locked supply-chain evidence, hostile-host and
extreme filesystem-race defenses, and broad host/platform conformance claims.

Where later sections specify cryptographic-like approval receipts, per-delivery
provider attestations, signed bootstrap infrastructure, or exhaustive hostile
environment evidence, those requirements apply to the public-distribution
profile unless a local research-ready criterion explicitly names them. This
scope rule takes precedence over the older undifferentiated wording below.

The local profile still preserves four non-negotiable classes of control:

1. scientific integrity: one canonical core, exact validators, structural
   Decisions, deterministic WorkPackets, and sealed-context rules;
2. local reliability: candidate-first writing, atomic commit, idempotent exact
   retry, ordinary crash recovery, and protection of user-owned files;
3. privacy hygiene: one explicit project/session execution policy, exact packet
   allowlists, secret exclusion, and refusal of `local_only` or sealed work when
   the selected host lacks real isolation;
4. honest claims: capability and provenance records describe observations but
   are not presented as proof against a compromised host.

## 2. Two-layer experience

The user and machine layers are deliberately separate.

### 2.1 Researcher layer

- Ordinary onboarding and continuation use natural language.
- The researcher is not required to type or understand PowerShell, shell,
  Python, package-manager, or `etai` commands.
- A security-sensitive installation, network access, protected-directory
  write, or credential access may still require a host-native confirmation.
- Software-install permission never authorizes creation of a scientific
  project. A new genesis requires an explicit request to initialize/enable v2
  in one identified project root, plus a supplied or confirmed project name.
- Human L2 and L3 scientific/externally consequential decisions remain visible
  decisions. Frictionless onboarding cannot turn them into silent defaults.
- Errors are reported as research-relevant recovery choices, with technical
  details available on demand rather than imposed as the primary interface.

### 2.2 Machine layer

- Hosts call one versioned, provider-neutral `etai` machine interface.
- The engine remains operable directly from a terminal for tests, automation,
  recovery, and advanced users.
- Every state-changing operation continues through existing validated engine
  boundaries. A host adapter never edits canonical ObjectStore bytes directly.
- Machine responses use a versioned, machine-readable schema; adapters must not
  infer state or authority by scraping human Markdown or terminal prose.
- Responses are stable enough for a host to distinguish
  success, permission required, human decision required, ambiguous next route,
  stale base, recoverable installation failure, and corrupted state.

One-sentence use means no manual command burden. It does not mean invisible
installation, bypassed permissions, unpinned software, or autonomous science.

## 3. Terms and owners

- **Engine**: the installed `econ-theorist-ai` package, its CLI/application
  service, registries, schemas, validators, and packaged policy resources.
- **Theory project**: one exact directory containing paper artifacts and one
  `.econ-theorist` store rooted there.
- **Host**: a coding-agent environment capable of reading project files,
  invoking a local process, and presenting permission or decision requests.
- **Host adapter**: a thin host-specific bootstrap instruction or generated
  configuration that invokes the common engine protocol.
- **Host manifest**: the single authoritative packaged definition of host
  operations, safety rules, and supported capability levels from which thin
  host projections are derived. It is policy input, not canonical scientific
  state.
- **Capability receipt**: a non-scientific record of which required host
  capabilities were detected and which were unavailable.
- **Install plan**: a visible, version-pinned description of intended network,
  package, filesystem, and configuration changes before first-use mutation.
- **Work packet**: the exact route-bound context and candidate-workspace
  contract exposed to one host agent for a run.
- **Run input brief**: an immutable, content-addressed, host-neutral statement
  of the bounded user question/framing intent, requested scope, actor role,
  privacy, compartments, and optional profile request. It is noncanonical but
  is bound into the navigation candidate and work packet so a clean framing
  run can carry the user's actual question without changing `RouteRun` v1.
- **Delivery envelope**: the pre-delivery, host/session-specific operational
  record that binds one immutable work-packet hash to the resolved local paths,
  projection handshake, capability/egress authorization, and operation key.
- **Host receipt**: provenance for a completed host operation, including known
  host/model/tool identity, engine and adapter versions, input/output hashes,
  and completion status without private chain-of-thought.
- **Operation key**: a caller-supplied idempotency identifier bound to the exact
  operation kind, install scope or project, base head when one exists, and
  request digest. Reuse with different inputs is an error; exact replay returns
  the prior result rather than repeating a mutation.

Scientific route meanings remain owned by the versioned registry,
instructions, schemas, and validators. This contract owns only installation,
project binding, host projection, machine-facing navigation, and handoff.

## 4. Constitutional boundaries

### 4.1 One scientific core

`AGENTS.md`, `CLAUDE.md`, Cursor rules, editor settings, skills, and generated
host prompts must not each restate or reinterpret the research workflow. They
may teach a host how to locate the engine, request a work packet, execute an
allowed operation, return a candidate, and surface a blocker. Route-specific
scientific instructions are loaded from the exact engine release only when the
route is opened.

The following ordering is mandatory:

```text
natural-language request
-> thin host adapter
-> versioned machine operation
-> canonical route/context/validator
-> candidate workspace
-> validated stage and atomic commit
```

A host-specific prompt is never allowed between the canonical validator and
the canonical store as an unrecorded policy override.

### 4.2 Canonical-state boundary

- `.econ-theorist` committed history remains the scientific source of truth.
- Host chat history, task state, IDE memory, Git branches, generated Markdown,
  and adapter files are noncanonical.
- A host writes only to engine-declared candidate workspaces and explicitly
  engine-owned noncanonical projection paths. A proposed change to a
  human-owned artifact is written to a candidate/shadow path and reconciled by
  the existing expected-base-hash boundary; the host never overwrites the
  human-owned working file directly. It must not synthesize, replace, or repair
  transaction, head, provenance, artifact-store, or snapshot bytes itself.
- `stage`, validation, and commit semantics remain authoritative.
- Switching hosts cannot silently reinitialize, fork, migrate, or reinterpret
  the project.

### 4.3 Authority boundary

- Installation approval is not scientific approval.
- A supported host facade or judge cannot confirm an L2 Decision for the
  researcher or invoke an unrestricted human-decision path from model-callable
  tools.
- A missing, rejected, mixed, stale, or ambiguous Decision stops promotion.
- External communication, publication, submission, destructive migration, and
  credential disclosure remain L3 actions with explicit authorization.
- Natural-language wording such as "continue automatically" does not waive
  these boundaries.

The accepted Phase 1 `Actor(kind="human")` is an explicit local provenance
assertion, not cryptographic proof of identity. Phase 5A must not redescribe it
as strong authentication. Host-mediated confirmation therefore uses a separate
trusted local approval channel outside the model context. It presents the exact
project/head, Decision bytes/digest, options, selected option, authority level,
and blast-radius summary, then issues a single-use, expiring, project/head- and
Decision-bound `HumanApprovalReceipt`. The host-facing decision operation
validates and consumes that receipt; the acting model cannot mint, edit, or
reuse it.

If a host cannot distinguish a direct user gesture from model-produced text or
cannot exclude the raw decision-confirmation operation from model tools, it may
prepare the Decision proposal but must stop for a separate trusted/manual human
path. Prompt text such as "the user approves" is never a receipt.

The generic machine protocol defines the trusted-channel interface and tests
it with an injected reference implementation. Receipt/authorization issuance,
revocation, and unrestricted raw decision actions are absent from the ordinary
model-callable request union. A generic CLI invocation cannot prove a direct
human gesture or host/provider isolation merely by supplying a boolean. Until
a host-native adapter supplies those controls in 5A.2--5A.4, the facade may
return a proposal or egress plan but must report
`trusted_human_channel_required`/`unsupported_host` at the protected boundary.

This is an adapter/approval-channel assurance claim, not resistance to a fully
compromised host or local account with arbitrary filesystem/process control.
Phase 5A documentation and receipts state that threat-model limit. Strong
cross-machine legal identity, hardware attestation, and cryptographic authorship
remain deferred unless a later reviewed identity architecture adds them.

Approval use is concurrency-safe, not a boolean file check. An engine-owned
append-only approval ledger and project-local approval lock derive
`issued`, `reserved(operation_key)`, `consumed`, `expired`, `revoked`, and
terminal no-effect/failure states. Under the lock, the facade validates the
receipt, exact project/head/action/Decision digest, selected option, expiry,
revocation, prior use, and operation key immediately before reservation. Only
the reserving operation may proceed. It rechecks the head at the canonical
commit boundary; success appends `consumed`, while stale-head or uncertain
failure becomes terminal and requires a fresh human approval. A crashed
reservation may be recovered only by the same operation key after proving that
no effect occurred. A second host cannot double-spend the receipt.

### 4.4 Privacy and reasoning boundary

- Project discovery is limited to the exact user-selected root and explicitly
  granted additional directories.
- One project must not contribute context, memory, artifacts, or decisions to
  another without a separately authorized adapter and recorded provenance.
- Install and host receipts record concise rationale and observable actions,
  not hidden reasoning traces.
- Secrets never enter canonical scientific state, generated host instructions,
  logs, work packets, or public diagnostics.

### 4.5 Provider egress, retention, and host memory

A coding-agent host may transmit prompts, file content, tool output, logs, or
chat state to an external model provider. Giving the host filesystem access is
therefore a potential egress grant; a work-packet allowlist in prompt text is
not an enforcement boundary when the host can independently read more files.

The local v2 facade cannot retroactively protect text already sent as the first
message to a remote model or workspace context already exposed before the
facade starts. One-message onboarding with non-public content is supported only
when (a) a trusted local pre-model extension intercepts the request and obtains
authorization before transmission, or (b) a verified pre-existing
host/account/project authorization already covers the exact provider and
technically accessible workspace. Otherwise the safe first message contains
only public bootstrap/source information in a neutral or already authorized
workspace; non-public project binding and the research question follow after
authorization. If the host exposes the private workspace before either control
exists, private onboarding is unsupported.

Before any non-public project byte is delivered to a provider-backed model,
the local facade produces an `EgressPlan` that declares:

- host product/version, adapter, model/provider, account or execution class
  when known, and whether execution is local or remote;
- the exact filesystem/tool scope the host can technically access, not only
  the smaller context the adapter intends to send;
- project, privacy labels, compartments, purpose, and data classes selected;
- known retention, training, logging, region, deletion, and human-review
  settings, with unknown values explicit;
- host memory/session persistence and whether it can cross projects;
- required isolation controls and the authorization being requested;
- authorization id, exact project/head/work-packet or bounded install scope,
  provider/purpose, allowed data classes, expiry, reuse rule, and revocation
  state.

Package-install/network permission is not consent to disclose research
content. `local_only` content never enters a provider-backed host. `restricted`
content requires exact affirmative egress authorization plus enforceable
filesystem/tool isolation. `project_private` content requires a bounded
project/provider authorization; if the host can access the whole project, the
authorization must disclose that whole accessible scope. Unknown provider
handling or unenforceable isolation fails closed for `restricted` and blind
compartments.

An `EgressAuthorization` is a separate, trusted-human operational approval. It
permits only the declared processing scope and does not change a canonical
privacy label, declassify an artifact, certify provider deletion, or authorize
public/external release. Any declassification or L3 release still requires its
own canonical human Decision/handoff. Revocation stops future deliveries under
the authorization; every delivery has an append-only outcome receipt.

Reusable egress authorization also uses an engine-owned append-only ledger and
project-local egress lock. Its signed bytes include an exact positive maximum
delivery count; `single_delivery` has bound one and `bounded_reuse` has an
explicit bound greater than one. Each delivery has a unique operation/delivery key.
The facade checks scope, head/packet, provider, purpose, expiry, revocation,
memory setting, and technical isolation under the lock, then rechecks and
records `delivery_started` immediately before releasing bytes. Revocation is
serialized against that transition: it blocks deliveries not yet started but
cannot undo one already transmitted. A crash after possible transmission is
`unknown_possible_egress` and is never retried automatically.

Blind probes, answer keys, sealed evaluation cases, and mutually isolated
roles require host-enforced allowlists, separate sandboxes/workspaces, or an
equivalent technical boundary. Instructions such as "do not read this file"
are not sufficient. A host that cannot enforce the required compartment is
unsupported for that route even if it can run ordinary project-private work.

Host automatic memory must be disabled or technically scoped to the exact
project and authorized purpose. If that cannot be verified, non-public
cross-session memory is disabled and the limitation appears in the capability
receipt. Revocation stops future delivery but cannot be represented as deletion
of provider-held copies unless the provider supplies verifiable deletion
evidence. Egress plans and delivery outcomes are privacy-governed operational
receipts; they contain hashes and metadata rather than duplicating disclosed
content.

Credentials and unrelated secrets are never included even when the researcher
authorizes whole-project research-content access. Provider-backed execution
uses a redacted environment and an allowlisted shadow workspace or equivalent
technical deny boundary. If the host can still read secret-bearing files,
parent directories, environment variables, or credential stores, the external
run is unsupported rather than relying on a prompt not to inspect them.

## 5. Host capability contract

Phase 5A officially targets Codex, Claude Code, and Cursor, plus a generic CLI
fallback. A future host is supportable only if it satisfies the same contract;
the project must not claim universal IDE support merely because files can be
opened there.

A full Phase 5A host requires:

1. read access to the selected project root;
2. controlled write access to declared project and candidate paths;
3. the ability to invoke the installed engine and capture structured output;
4. a way to present installation and protected-action approvals;
5. stable project-root identification;
6. preservation of exact files and UTF-8 content;
7. the ability to report a blocker and wait for human input;
8. sufficient process isolation to avoid leaking another project's context.
9. accurate disclosure of remote-provider egress, technically accessible file
   scope, retention/memory settings, and enforceable compartment controls for
   every privacy level the adapter claims to support.

The capability receipt records the host product/version and adapter version so
support is an evidence-backed statement about a tested surface, not a timeless
claim about a product name.

Useful but nonessential capabilities, such as background agents, worktrees,
hooks, model selection, or MCP tools, must be declared separately. Their
absence cannot change route semantics. Phase 5A uses one acting agent; broader
parallel-agent capabilities belong to Phase 5B.

An official Phase 5A projection disables autonomous scientific delegation or
records that the host cannot do so and is unsupported for the single-agent
claim. Tool subprocesses are allowed; a second model context that proposes,
reviews, judges, or writes scientific content is a Phase 5B agent lane, not a
Phase 5A implementation detail.

Capability negotiation fails closed. If a required capability is missing, the
adapter reports the unsupported operation and offers the canonical CLI/manual
fallback. It does not emulate a missing safety or authority capability with a
prompt promise.

## 6. Distribution and first-use bootstrap

### 6.1 Trusted discovery

The official repository and release channel must publish one short,
agent-readable onboarding document that identifies:

- the canonical project and publisher;
- supported platforms and Python/runtime requirements;
- the exact stable release or allowed release channel;
- artifact hashes or an equivalent package-integrity mechanism;
- the safe installation operation;
- the expected permission boundary;
- the post-install verification operation;
- recovery and uninstall instructions.

A bare host cannot securely derive publisher identity from the product name
alone. First-use bootstrap therefore requires one of three explicit trust
roots: a canonical repository/package identifier included in the user's
natural-language request, a previously installed signed/verified host catalog
entry, or a publisher identity verified through a separately trusted package
index. If none is available, the host asks the user to confirm the canonical
source before any download. This may still be one natural-language request;
it is not permission to search for a similarly named repository and execute
it.

Search-engine ranking or a host's recollection of an old command is not a trust
root. An adapter must not execute a downloaded opaque script, `curl | shell`,
or an unpinned branch as the ordinary installation path.

The pre-install trust object and post-install engine inventory are distinct:

- a small signed bootstrap descriptor, verified against the selected publisher
  identity before execution, binds the release/version, supported platforms,
  exact wheel hashes, Python constraints, fully hashed transitive dependency
  lock, build provenance/attestation, host-manifest hash, revocation/expiry
  metadata, and post-install engine-manifest hash;
- an installed engine manifest records the absolute interpreter, isolated
  environment, package/entry-point location, exact installed distribution
  graph and hashes, registries, schemas, instructions, profiles, craft
  resources, validators, and host manifest, and must match the signed
  descriptor.

An installed `etai` process cannot establish the trustworthiness of the code
that installed that same process. Phase 5A.1 therefore owns the versioned
descriptor/install-plan/engine-manifest schemas, pure validation logic, and
deterministic development fixtures. A separately trusted pre-install verifier
or host-native installer executes the descriptor protocol before `etai`
exists. Real publisher signing keys, revocation publication, locked release
artifacts, and fresh-environment installation evidence remain Phase 5A.5 exit
work; a source checkout is always reported as `development_only`.

Ordinary installation uses a prebuilt verified wheel plus the fully hashed
dependency set in an isolated environment. It does not build an sdist or run an
unlocked build backend. A missing platform wheel stops with an unsupported
platform/build-review result. Release construction itself uses a locked build
environment and records its provenance. The current source checkout's
`setuptools>=68` build requirement and editable install are development paths,
not Phase 5A release-integrity evidence.

The adapter invokes the absolute verified launcher/interpreter from the
managed environment and checks its engine-manifest digest; it does not trust
the first executable named `etai` on `PATH`. Dependency substitution, extra or
missing installed distributions, signed-descriptor mismatch, package-resource
drift, revoked releases, and launcher/path shadowing all fail before project
state is read or mutated. Key rotation and revocation require a separately
versioned publisher policy rather than an adapter-local exception.

### 6.2 Install plan

Before first-use software or configuration mutation, the host presents or makes inspectable a plan that
states the selected release, source, integrity evidence, installation scope,
target project root, files it may add or modify, and commands or equivalent
operations it will perform. Permission may cover the bounded plan; Phase 5A
does not require repetitive confirmation of deterministic substeps already
within that grant.

The install plan separately states whether project initialization was
requested. Package installation and host-projection approval cannot be reused
as implicit permission to create `.econ-theorist` genesis state. Initialization
requires the exact root, project name, and an explicit user intent such as
"enable v2 in this project"; it receives its own operation key and receipt even
when one natural-language sentence requested both actions.

Denial, cancellation, network failure, unavailable runtime, or package-integrity
failure leaves the project scientifically unchanged and returns a structured
recovery response.

### 6.3 Version discipline

- The engine, host-manifest, and host-projection versions are explicit.
- A project records which engine/schema/registry versions govern its current
  state using existing versioned mechanisms or a tested additive extension.
- An adapter refuses an incompatible engine rather than silently upgrading or
  downgrading state.
- Upgrades are planned, versioned, idempotent, and independently reversible
  until a separately authorized canonical migration commits.
- Uninstalling a host adapter or engine never deletes a theory project.

### 6.4 Post-install verification

First use is not successful until the installed engine passes the applicable
`doctor`, package-resource, registry-hash, schema, and project validation
checks. A host may hide routine command output, but it must preserve an
inspectable receipt and surface every warning or failed required check.

## 7. Project-root binding and idempotence

The host binds one explicit absolute project root for the operation. It must
detect and reject ambiguous nested `.econ-theorist` stores, a root outside
granted access, a reparse/symlink escape, or a mismatch between the selected
project and canonical project identity. It may detect sibling candidates only
inside an explicitly granted discovery scope; it must not scan parent or
sibling directories merely to prove that no other project exists.

Every root-aware machine request carries a versioned `DiscoveryGrant` naming
the exact selected root, stable workspace root, allowed discovery roots, and
ancestor-check boundary. The facade checks ancestors only up to that granted
boundary and descendants only under the selected root. If the grant is too
narrow to rule out an outer project store, it returns `root_scope_incomplete`;
it never scans an ungranted parent or sibling as a convenience.

Required behavior is:

- no existing store plus explicit project-initialization intent, exact root,
  and supplied/confirmed name: initialize exactly one genesis;
- no existing store without that intent or identity: report
  `project_initialization_required` without canonical mutation;
- valid existing store: validate and reuse it without a new genesis;
- incomplete noncanonical setup: repair only generated configuration that the
  engine owns, then validate;
- interrupted canonical operation: invoke canonical recovery semantics before
  offering new work;
- invalid or corrupted canonical state: stop without canonical mutation and
  present exact diagnostics;
- incompatible version: stop and propose a versioned migration or compatible
  engine selection;
- repeated natural-language request: converge to the same initialized state
  and active run rather than duplicating either.

Existing-project recognition begins with a strictly read-only compatibility
probe over safe store metadata, project identity/version hints, head, and
reachable format/schema identifiers. It selects a compatible engine before
calling replay, recovery, render, `ensure`, or any configuration writer. In
particular, the current legacy `init_project` path rewrites generated
`project.json` when a head already exists; Phase 5A must not call it to
"recognize" an existing project. Existing stores use the new read-only bind
path. Any generated-config repair is a separately planned, authorized,
idempotent operation after compatibility and canonical validation succeed.

`project.json.engine_version` is a generated local diagnostic hint, not
canonical governing authority and never the sole compatibility signal. A
`virgin` classification requires no head, project identity, transaction,
provenance, artifact, run, staging, or orphan bytes; precreated empty
engine-owned directories alone may be virgin. Any other headless residue is
`recovery_required`, not permission to create a new genesis.

For Section 8.2 only, a root classified `virgin`--including one containing only
those empty engine-owned directories--is equivalent to "no existing store".
It is not treated as an existing project and may initialize only under the
explicit intent/name requirements above.

Initialization must not require the engine source repository to be copied into
the paper directory. Source-checkout installation remains a developer path;
the ordinary project contains its own artifacts and `.econ-theorist` state,
not a private copy of the framework implementation.

### 7.1 Derived run lifecycle

The accepted `RouteRun` v1 record is immutable and its stored status is always
`running`. Phase 5A must not append to it, rewrite it, or pretend that it already
contains a completed/abandoned lifecycle. Inspection instead derives a
versioned `RunExecutionView` with orthogonal facets from existing immutable and
noncanonical evidence:

- `integrity`: `valid` or `invalid` for required operational bytes, hashes, and
  bindings;
- `base_freshness`: `current`, `stale`, `unknown`, or `not_applicable` after a
  matching transaction has committed;
- `lifecycle`: exactly one of `opened`, `candidate_present`, `staged`,
  `commit_conflict`, `committed`, or `unknown` when integrity prevents safe
  classification.

For valid evidence, lifecycle is mutually exclusive under this precedence:

1. `committed` when replay finds a reachable committed transaction with the
   exact `route_run_id` and provenance bindings;
2. `commit_conflict` when no such transaction is reachable and an immutable
   outcome records a failed/conflicting commit;
3. `staged` when `active-candidate` resolves to one valid immutable staged
   digest;
4. `candidate_present` when the declared workspace contains a materially
   populated candidate but no active staged digest exists;
5. `opened` when the valid initial candidate workspace is otherwise unfilled.

Thus `staged` may correctly coexist with `base_freshness=stale`, while
`opened` and `candidate_present` cannot both hold. `integrity=invalid` forces
`lifecycle=unknown` and `base_freshness=unknown` for planning.

Run outcomes and staging files help derive operational state but never override
canonical replay. Phase 5A defines no automatic `abandoned` state. If several
uncommitted compatible runs exist, or lifecycle evidence conflicts, planning
returns `repair_required`/`ambiguous_next` and asks for an explicit recovery or
future disposition mechanism; it does not select the newest run or delete the
others.

### 7.2 Duplicate prevention

The Phase 5A facade serializes inspect-plus-resume/open under an engine-owned
project-local navigation lock, replays the head inside that lock, and binds the
operation key before creating a run. An exact retry returns the existing run.
A changed head restarts inspection. The navigation lock is operational and
does not replace the existing canonical commit lock.

Legacy/direct run creation may reveal pre-existing duplicates. The facade must
detect them and fail closed; it cannot retroactively infer which chat or run the
researcher intended. Last-writer-wins, newest-run-wins, and silent deletion are
forbidden.

## 8. Required machine operations

Phase 5A must expose the following behaviors through one structured interface.
Exact public CLI spellings are chosen during implementation and documented in
one place; host adapters consume the behavior contract, not hard-coded prose
recipes.

Every state-changing host operation carries an operation key. The engine binds
that key to the exact request and persists enough non-secret receipt state to
make retries idempotent across host restarts. A reused key with a different
request fails closed. Existing transaction hashes and route-run identities
remain the canonical scientific deduplication anchors.

### 8.1 Install and verify engine

1. identify host capabilities and installation scope;
2. resolve and verify the supported engine;
3. produce/execute the bounded install plan when necessary;
4. run environment diagnostics;
5. install or reconcile the thin host projection safely when requested;
6. return engine/adapter versions, capability receipt, warnings, and blockers.

This operation creates no theory-project genesis. It may be used before a
project exists.

### 8.2 Bind or initialize project

1. bind one exact granted project root;
2. reject ambiguous, nested, escaped, corrupt, or foreign stores;
3. if store entries exist, run the read-only compatibility probe, select the
   compatible engine, and validate without invoking legacy `init_project`,
   `ensure`, recovery, rendering, or a config writer; or
4. only when no store exists and explicit project-initialization intent, exact
   root, and a
   supplied/confirmed project name are all present, initialize exactly one
   genesis under a distinct operation key;
5. return project id, exact head, validation status, and a read-only inspection
   result.

Project initialization is a canonical setup action but not an L2 promotion of
a research question, mechanism, model, claim, novelty position, argument spine,
or target. Installation permission alone never invokes it.

### 8.3 Inspect

Return a compact machine view containing at least:

- project identity and exact canonical head;
- engine, schema, registry, profile, and craft versions when applicable;
- active or incomplete runs and candidate status;
- current readiness/blocker summary;
- stale or invalid dependencies that preclude progress;
- pending human Decisions;
- legal next-route candidates, each with why it is or is not available;
- recovery advice that does not itself mutate state.

This is not a dump of the entire Snapshot into the host context.

### 8.4 Plan next

Planning is read-only. It may identify a unique next operation but cannot open
a run. It returns one of:

- `unique_next`: exactly one route/focus is legal;
- `resume_required`: an incomplete run or staged candidate already owns the
  next action;
- `human_decision_required`: an L2/L3 or other explicit human choice blocks
  progress;
- `ambiguous_next`: multiple legal research paths require a choice;
- `repair_required`: validation, recovery, stale dependency, or version repair
  precedes new work;
- `complete_for_requested_scope`: no further route is required for the user's
  bounded request;
- `navigation_unsupported`: the engine lacks a sound, complete-enough probe for
  at least one enabled route/focus class, so uniqueness cannot be claimed;
- `unsupported_host`: the host cannot safely perform the operation.

No score, model preference, or adapter-local heuristic may collapse a real
scientific ambiguity into `unique_next`.

The accepted route registry and entry validators authorize an already
specified route/focus; they do not enumerate all legal route/focus pairs.
Phase 5A.1 must therefore add a separate versioned navigation-probe registry,
packaged as noncanonical engine policy. For each supported route version it
names a deterministic candidate-focus selector, prerequisite/blocker probe,
and the existing authoritative entry validator used for final dry-run
authorization. It contains no route prompt or scientific acceptance rule.

A navigation candidate key includes the exact base head, route id/version,
purpose, actor kind/role, ordered compartments, privacy clearance, focus
ids/revisions, context budget, and exact `RunInputBrief` hash when one is
required--not only route/focus. If purpose or another field is not derivable
from versioned engine policy and the bounded user request, planning reports the
missing input. In particular, the adapter cannot invent purpose defaults for
routes that the current CLI does not define. Changing the brief produces a new
candidate/run/packet; it cannot silently replace an opened run's input.

Every proposed candidate is checked by the exact current route authorization
and entry validator without mutation. Tests establish probe soundness and
fixture-bounded completeness. If any enabled route lacks a tested navigation
probe, focus enumeration is incomplete, or a probe and entry validator
disagree, planning returns `repair_required`/`navigation_unsupported`; it may
not report `unique_next`. Route ordering may help presentation but never erase
multiple genuinely legal candidates.

### 8.5 Open or resume

- Resume an existing compatible run before creating another only when its
  exact full navigation candidate key matches: base head, route id/version,
  purpose, actor kind/role, ordered compartments, privacy clearance, focus
  ids/revisions, and context budget, together with exact registry,
  instruction, selector, context, and applicable profile/policy hashes.
- A new genesis project may open the unique framing route when the user's
  request provides the required research question or explicitly requests
  framing.
- `requested_scope` plus `framing_intent` means **frame or explicitly
  reframe**. A host includes them for the first framing request, or for a later
  reframe the user actually requested. After a committed route, an ordinary
  continuation omits both fields so navigation can advance from current
  scientific state. A host must surface a blocked no-brief continuation; it
  must not replay the prior brief merely to make framing enterable again.
- Open a new run only from an exact current head and exact legal route/focus.
- Return a work packet and candidate workspace; do not return write access to
  canonical storage.
- If the head changes, invalidate the packet and require reinspection.

### 8.6 Complete candidate

The host returns declared artifacts and a candidate transaction through the
existing staging boundary. The engine validates exact hashes, schema,
authority, lineage, context, base revision, privacy, and route outcome before
atomic commit. A host cannot reinterpret a rejected candidate as success.

## 9. Work-packet, delivery-envelope, and receipt minimums

Phase 5A uses three separate immutable operational objects. They use
deterministic canonical-JSON encoding for hashing; "canonical JSON" here is a
serialization rule and does not make them canonical scientific state.

### 9.1 Scientific work packet

The engine deterministically compiles one host-neutral work packet from the
exact immutable `RouteRun`, `ContextManifest`, compiled-context bytes,
content-addressed `RunInputBrief` when present, and packaged policy versions.
No other chat or host memory is an implicit packet input. It binds:

- packet schema/version and exact hashes of those three existing run objects;
- project id and exact base head;
- route id/version, purpose, actor role, and focus ids/revisions;
- registry, instruction, schema, profile, selector, and context hashes;
- privacy compartment and clearance;
- selected canonical references and permitted artifact excerpts;
- explicit omissions and hidden compartments;
- relative logical candidate/shadow paths and allowed operation classes;
- required outputs and validation endpoint;
- pending human gates, forbidden actions, and stale-base behavior.

The packet contains no host/model id, absolute machine path, operation key,
delivery time, candidate/outcome, or mutable completion state. Its id is the
SHA-256 digest of its exact canonical-JSON bytes. Regeneration from the same
run/context/policy bytes must produce the same digest across supported hosts.
The packet is never updated in place. Candidate progress and completion affect
only `RunExecutionView` and the post-run receipt. A changed base/context creates
a new run and packet. A packet-compiler/schema or host-neutral policy change
must never overwrite an existing packet. Phase 5A.1 stops rather than rebinding
an incomplete run to new policy bytes. Phase 5A.4 update usability must
implement and test creation of a new immutable packet naming the prior packet
hash and a typed supersession reason before such updates are supported; the
schema field alone is not an implementation claim. Cross-host hash parity is
asserted only under the same exact engine, packet compiler, schema, and
host-neutral policy versions.

### 9.2 Delivery envelope

Before exposing packet content to one host session, the facade writes a
separate content-addressed delivery envelope that references the work-packet
hash and records the operation key, host/projection handshake, resolved
absolute project/candidate roots, capability receipt, EgressPlan/authorization,
delivery time, agent topology, and pre-delivery status such as
`authorized_to_deliver` or `blocked_before_delivery`. Later delivery/result
state belongs only in the host-operation receipt. A new host/session gets a new
envelope but should receive the same host-neutral packet when the exact run is
resumed.

### 9.3 Host operation receipt

After delivery/agent work, the facade writes a new content-addressed receipt
that references the delivery-envelope and work-packet hashes and records known
host/model/provider/reasoning/tool identities, candidate/artifact digests,
stage/commit outcome, head before/after, warnings, and completion/failure state.
It never mutates the pre-run packet or delivery envelope. An exact operation-key
retry returns the prior envelope/receipt, except that a delivery operation that
may already have returned packet bytes must return
`unknown_possible_egress` without the packet on retry. A materially different
attempt uses a new key and append-only receipt.

A missing optional identity is recorded as unknown; it is never fabricated.
Private reasoning text is neither required nor stored.

### 9.4 Storage and authority

Pre-project installation and capability receipts are local operational records,
not scientific entities. They live in an engine-owned local operational area,
use an explicit retention/version policy, contain no credentials or project
content beyond the minimum root/project binding, and remain inspectable and
deletable without changing scientific history. They do not travel in a theory
project backup or cross-host handoff unless a human explicitly includes them in
a privacy-governed support bundle.

The accepted `RouteRun` v1, `ContextManifest`, transaction provenance hashes,
and historical route validators have no append slot for these Phase 5A
objects. Phase 5A must not rewrite them or claim otherwise. Work packets,
delivery envelopes, and receipts live in an engine-owned run-operational area
and cannot influence replay, route entry, validation, authority, freshness, or
commit acceptance. They reference existing hashes in the forward direction;
the historical transaction does not bidirectionally bind them.

Scientific-run sidecars inherit the run/project privacy label, retention,
private-backup, and release restrictions. Absence or loss is reported as
missing host evidence rather than corruption of canonical scientific history.
A host summary never becomes evidence for a claim merely because it is
retained.

If later evaluation or assurance requires canonical bidirectional binding of
host/model provenance, that requires an explicit additive schema/transaction
or run-provenance version and migration with frozen-history tests. It cannot be
smuggled into `RouteRun` v1, appended after its hash is committed, or forced
through historical route outputs that reject an extra artifact. Until such a
binding is accepted, Phase 5A sidecars can support operational conformance but
not a confirmatory causal claim about model or host quality.

Two hosts receiving the same work-packet hash must face the same scientific
preconditions and validator; their delivery envelopes and receipts are
expected to differ. Their prose or candidate quality may differ, but the
adapter may not change the evidence, authority, or acceptance predicate.

## 10. Host projections

The engine-owned host manifest is the source from which supported projections
are generated or checked.

- Codex currently uses `.agents/skills/econ-theorist-v2/SKILL.md` over the
  installed `etai codex invoke` bridge. This prepared-checkout projection is
  public-only and does not establish cold installation or an activation
  handshake in an arbitrary paper directory.
- Claude Code may receive a bounded `CLAUDE.md` integration and, when needed,
  project agent definitions.
- Cursor may receive bounded project rules in its supported project-rule
  location.
- A generic host receives the documented CLI/manual fallback.

Projection installation is conservative:

1. discover an existing user-owned instruction file;
2. prefer a dedicated generated file plus a supported reference/import;
3. otherwise add only a clearly delimited, versioned managed block after
   showing the planned change;
4. never replace unrelated user instructions;
5. on update, change only the engine-owned projection;
6. on uninstall, remove only the engine-owned projection;
7. if safe composition cannot be proved, stop and provide a manual merge
   proposal without modifying the file.

Host projections state that canonical machine output and work packets outrank
adapter summaries on scientific state. They must not embed route prompts,
private project content, journal-imitation instructions, or credentials.

### 10.1 Projection activation handshake

File presence is not evidence that a host loaded or applied a projection.
Supported projections carry a projection id/version and authoritative
host-manifest hash plus a minimal instruction to perform a machine handshake.
At the start of a fresh host session, the handshake returns and records
`projection_loaded`, the exact projection/manifest hashes, host product/version,
project root, and known instruction-source/precedence information. A missing or
mismatched handshake is `projection_inactive`, not success.

Installation during an already-running host session must not assume that new
project instructions are reloaded. If the host cannot activate them
dynamically, bootstrap returns `host_session_restart_required`; it may finish
the explicitly requested first-use operation using the verified onboarding
document and engine facade, but cross-session support is claimed only after a
fresh-session handshake passes. Starting/reloading that session should be
host-automated when the host safely supports it; it never requires the
researcher to transcribe a shell command.

Host-native tests must exercise the product's actual instruction discovery and
precedence behavior, including higher-priority override files, excluded
instruction sources, nested project roots, size/truncation limits, wrong rule
types or path scopes, stale projections, and session-start caching. A rendered
file, template snapshot, or agent assertion that it "read the rules" is
insufficient. The handshake proves loading, not obedience; engine validation
and permission controls remain the enforcement boundary.

## 11. Natural-language navigation rules

The host translates intent into a bounded requested operation, not directly
into a scientific result.

- "Install v2" requests software installation and diagnostics only; it does
  not create a project.
- "Enable v2 in this project" may additionally request project binding or
  initialization, but only when the exact root and project name are supplied
  or confirmed. That explicit request, not the package-install approval,
  authorizes genesis.
- "Continue with v2" requests inspect, plan-next, and then resume or open only
  if the next action is unique and within the user's authority.
- "Review the mechanism" narrows eligible routes to mechanism-relevant review
  or repair, but exact state and route preconditions remain controlling.
- "Write for Econometrica/Top-5/general-interest theory" selects or proposes a
  supported ambition/audience profile; it cannot activate an unsupported named
  journal overlay, change the science, or certify journal quality.
- A request spanning installation, project initialization, and research uses
  distinct operation keys and receipts: first install/verify, then explicitly
  bind/initialize, then inspect, and only then open a separately receipted
  scientific run.

If required information is missing, the host asks the smallest decision-complete
question. It does not infer a central mechanism, solution concept, theorem
scope, novelty claim, target profile, or external action from conversational
convenience.

## 12. Acceptance scenarios

Every implemented host projection must pass a shared conformance suite plus a
host-native end-to-end check. Fixture-only host rendering is insufficient for
the final Phase 5A claim.

### 12.1 Clean first use

For Codex, Claude Code, and Cursor, begin in a clean theory-paper directory
without an installed project. Give the same natural-language onboarding
request, including the canonical source identifier unless a tested trusted
catalog already supplies it, the exact current root, and a project name. The
request explicitly authorizes initialization in that root. In the public-data
case it may include the public research question. In the non-public case, use a
verified pre-model/account authorization or send the question only after the
EgressPlan is approved. After the minimum host/OS-mandated approvals--with one
bounded installation-plan approval as the target--each host must:

- install the same supported engine release;
- pass required diagnostics;
- initialize exactly one project and genesis;
- validate the exact head;
- install a non-destructive thin projection;
- inspect state;
- open the unique framing run when the request supplies the question;
- return an inspectable receipt and candidate workspace.

Differences in host-native approval UI are allowed. Differences in scientific
state, route meaning, or validator are not.

Also test the unsafe ordering: put an unapproved private question in the first
message to a provider-backed host with no pre-model or account authorization.
The local test harness must prevent transmission before model invocation; if
the real host cannot do so, that private first-message mode is explicitly
unsupported and cannot be counted as successful one-message onboarding.

### 12.2 Repeated onboarding

Repeat the same request in the same host and then in a different host. No
second genesis, duplicate equivalent active run, head change, scientific-state
rewrite, or duplicated managed block may occur.

### 12.3 Cross-host handoff

Create or resume work in one host, stop at a safe boundary, and continue from
each other supported host. Every host must report the same project id, head,
active run, work-packet hashes, blockers, and human Decisions. Host identity is
additional provenance, not a new project identity.

### 12.4 Existing project and instructions

Onboard an existing valid project containing user-owned `AGENTS.md`,
`CLAUDE.md`, Cursor rules, paper artifacts, uncommitted Git changes, and no v2
managed block. The adapter must preserve every unrelated byte or stop with a
manual merge proposal. It must not require a clean Git tree to read or validate
scientific state.

Repeat with an older compatible project, an incompatible future version, a
head plus missing/stale/corrupt generated `project.json`, and a project whose
recorded engine differs from the currently installed launcher. Hash all
pre-existing store bytes before recognition. The compatibility probe must be
read-only, must select or reject the engine before replay/mutation, and must not
silently invoke legacy `init_project` or rewrite configuration.

### 12.5 Active and staged work

Test an open run, a completed but unstaged candidate, a staged candidate, a
stale-base candidate, and an interrupted commit. The host must resume or invoke
canonical recovery as appropriate. It must never create a competing duplicate
run merely because the chat is new.

### 12.6 Ambiguity and authority

Test multiple legal routes, missing focus, missing L2 Decision, rejected/mixed
Decision, unsupported target overlay, and an L3 release request. Also test a
model-authored "user approved" statement, direct/raw `decide` invocation from
the model tool set, forged receipt, receipt replay, wrong project/head/Decision
binding, expiration, and changed selected option. The host must surface the
exact choice or denial and leave canonical state unchanged unless the trusted
human channel supplies the exact valid receipt.

Race two hosts against the same approval receipt, change the head between
reservation and commit, crash before/after reservation, and attempt recovery
under a different operation key. At most the exact reserving operation may
commit, and any ambiguous/stale outcome requires fresh approval.

### 12.7 Installation and integrity failures

Test denied permission, offline network, unavailable runtime, untrusted or
expired/revoked publisher descriptor, wheel or transitive-dependency hash
mismatch, unlocked/sdist build attempt, `PATH`-shadowed launcher, incompatible
engine, unexpected installed distribution, engine-manifest mismatch, missing
packaged resources, damaged adapter, and interrupted installation. Every case
must fail without canonical scientific mutation and provide a bounded recovery
path.

### 12.8 Root and privacy attacks

Test nested stores, wrong project root, sibling-project confusion inside a
granted discovery scope, attempted out-of-scope parent/sibling scanning,
directory traversal, symlink/junction/reparse escape, private-compartment
request, secret in environment output, and attempted cross-project memory.
Every attack must fail closed without leaking content.

Also race egress delivery against revocation/expiry/head change, crash before
and after `delivery_started`, retry an `unknown_possible_egress`, and attempt a
second host delivery under the same delivery key. No bytes may leave before the
serialized start transition, and an uncertain transmission is never
automatically repeated.

### 12.9 CLI independence

Run the same initialization, validation, inspection, and route-opening flow
without an IDE adapter. The core must remain usable and semantically identical
through its documented machine/CLI interface.

### 12.10 Single-agent boundary

Run each host-native Phase 5A scenario with background-agent or agent-team
features disabled. Receipts must declare `agent_topology=single`, and run
provenance must contain no undeclared scientific child-agent lane. Attempted
automatic delegation to a second model context must be rejected or move the
test to a future Phase 5B contract; it cannot be hidden behind the host adapter
and counted as Phase 5A success.

### 12.11 Projection discovery and activation

Install each projection, begin a fresh host-native session, and require a
successful exact-hash activation handshake. Repeat with a higher-priority
override, excluded instruction source, nested root, over-limit/truncated
instruction chain, wrong Cursor rule kind/scope, stale manifest hash, and a
projection installed after session start. Each unsupported or inactive case
must be detected rather than counted as loaded merely because a file exists.

## 13. Evidence and test matrix

### 13.1 Local research-ready evidence

The active profile requires:

- deterministic tests for root binding, navigation, WorkPacket construction,
  candidate validation/completion, exact retry, and ordinary recovery;
- preservation of accepted Phase 1--4 schema, registry, instruction, replay,
  authority, privacy, and gold oracles;
- one recorded Codex natural-language initialization or continuation flow;
- one real theory route whose model-produced candidate passes through the
  engine validator and atomic commit boundary;
- a negative route showing that an unresolved structural Decision stops
  promotion;
- a negative privacy case showing that `local_only` or sealed/blind work is not
  delivered when the selected host cannot provide its required isolation;
- `doctor`, exporters, the focused suite, and the complete non-long regression
  suite, with skips reported honestly.

A deterministic writer fixture is architecture evidence but cannot satisfy the
real-route item.

### 13.2 Public-distribution-ready evidence

Phase 5A implementation evidence must include:

- deterministic unit tests for install-plan, capability, root-binding,
  projection-merge, idempotence, navigation, work-packet, and receipt logic;
- adversarial tests for every failure in Section 12;
- frozen Phase 1--4 registry, schema, instruction, resource, replay, privacy,
  authority, and gold oracles;
- signed-bootstrap, locked-build, wheel, fully hashed transitive-dependency,
  absolute-launcher, and post-install engine-manifest tests from a release
  artifact rather than only `pip install -e .`;
- fresh-environment tests on every supported operating-system class claimed by
  the release;
- a shared host-conformance fixture for Codex, Claude Code, and Cursor;
- one recorded host-native onboarding and cross-host handoff per supported
  host, with private data redacted;
- explicit single-agent topology checks for every Phase 5A host-native run;
- fresh-session projection activation/precedence checks rather than only file
  rendering snapshots;
- a versioned support matrix pinning host product/build, operating system,
  adapter/projection, instruction/rule mode, sandbox/permission configuration,
  provider/privacy configuration, and tested model class, with repeated
  independent clean-start and resume trials for every combination claimed;
- `doctor`, exporters, full non-gold regression, and proportionate gold replay;
- explicit reporting of skipped optional tools and untested host/platform
  combinations.

Passing a rendered-template snapshot does not prove a host can install or
operate the engine. Passing one recording proves only that exact
host/version/platform/configuration trial; it does not prove parity for another
host or a later product release.

## 14. Implementation slices

Implementation proceeds in this order:

1. **5A.0 -- contract and status repair:** freeze this contract, update the
   Phase 4 merged status, architecture trust boundary, roadmap, and repository
   instructions without adding runtime behavior.
2. **5A.1 -- local machine facade:** implement compatibility recognition,
   project binding, derived lifecycle, sound navigation, host-neutral work
   packets, reliable candidate completion, exact retry, and ordinary recovery
   with no host-specific scientific rules. Bootstrap, capability, egress, and
   receipt objects may remain descriptive or optional outside sealed work.
3. **5A.2 -- Codex research-ready vertical slice:** implement natural-language
   initialization/continuation and run one real theory route from packet to
   model candidate, validation, and commit.
4. **5A.3 -- portable-host smoke tests:** add Claude Code and Cursor thin
   projections when useful; their parity does not block Codex scientific work.
5. **5A.4 -- local release usability:** verify pinned local installation,
   update, recovery, uninstall, and generic CLI operation.
6. **5A.5 -- optional public-distribution hardening:** before broad public
   security/support claims, add signing, revocation, fully locked dependency
   evidence, hostile-environment review, and expanded platform conformance.

The current tree completes the prepared-checkout, public first-route subset of
5A.2. Positive non-public execution, clean first-use activation, and the full
gate below remain open.

Each slice is independently reviewable. No host-specific shortcut may be
promoted into the engine before a generic invariant and test justify it.

## 15. Exit criteria

### 15.1 Local research-ready gate

The local profile is accepted when:

1. Codex can initialize or continue the exact selected project from natural
   language without asking the researcher to transcribe commands;
2. a real theory route completes `WorkPacket -> model-produced candidate ->
   validate -> stage/commit` through the canonical engine;
3. exact retries do not duplicate genesis, runs, delivery, or commits, and an
   ordinary interrupted operation has a tested recovery path;
4. the host never overwrites user-owned paper/instruction files or writes
   canonical ObjectStore bytes directly;
5. unresolved structural Decisions stop promotion;
6. only the exact declared private packet is exposed, and `local_only` or
   sealed/blind work stops without real isolation;
7. focused tests, the complete non-long regression suite, exporters, and
   `doctor` pass.

Passing this gate permits controlled Phase 5B work and exploratory quality
pilots. It does not claim v2 superiority, lower human effort, broad host parity,
or public-release security.

This gate is not yet accepted. The recorded public functional slice satisfies
the real-model first-route subset but not all privacy and first-use criteria.

### 15.2 Public-distribution-ready gate

The public-distribution profile is accepted only when:

1. an ordinary researcher can issue the documented natural-language request
   in each supported host without manually invoking a shell command;
2. unavoidable first-use interactions are limited to bounded trusted-source,
   host/OS installation, non-public egress, required session activation, or
   actual human-decision approvals--never command transcription;
3. clean install, existing-project onboarding, repeat use, update, recovery,
   uninstall, and cross-host continuation are idempotent and fail closed;
4. all supported hosts use one engine-owned manifest and the same exact
   scientific route/context/validator semantics;
5. adapters preserve user-owned instructions/files and never write
   human-owned working artifacts or canonical store bytes directly;
6. project identity, head, derived active-run state, Decisions, blockers, and
   work-packet hashes agree across hosts under the same pinned engine/policy;
7. ambiguous routes, missing Decisions, unsupported profiles, permission
   denial, integrity failure, and corrupt state cannot be converted into
   progress by adapter heuristics;
8. official adapter tool surfaces exclude unrestricted human-decision actions,
   and forged, missing, stale, replayed, or mismatched human-approval receipts
   cannot confirm an L2/L3 action within the documented threat model;
9. EgressPlans, authorizations, technical secret/compartment isolation, host
   memory scope, and delivery receipts enforce every claimed privacy level;
10. host/model/tool identity is captured when available without requiring or
   storing private reasoning;
11. the full CLI path remains documented, tested, and usable without an IDE;
12. Phase 1--4 frozen semantics and accepted regression evidence remain green;
13. an independent adversarial review finds no unresolved blocking violation
    of supply-chain, privacy, authority, project-root, idempotence, or canonical
    state boundaries.

Passing the public-distribution gate supports broader natural-language
onboarding and single-agent host-portability claims. It still does not prove
autonomous research quality or reduced human effort.

## 16. Explicit deferrals to Phase 5B or Phase 6

Phase 5A does not implement or validate:

- parallel mechanism/model discovery lanes;
- general multi-agent panels, agent teams, judge synthesis, or minority
  preservation;
- prose assembly by committee or replacement of the canonical writer;
- provider ranking, model selection policy, credentials for autonomous API
  generation, or comparative model claims;
- Git, Lean, private cross-project memory, or advanced symbolic/numerical
  adapters beyond what installation itself requires;
- complete-paper autonomous generation or broad craft/profile coverage;
- claims that v2 beats v1, that one supported model/host produces better or
  more efficient research outcomes than another, that v2 reduces substantive
  human effort, or that it approaches Econometrica/Top-5 quality;
- external communication, release of a manuscript, or submission execution.

Controlled multi-agent scientific execution and optional research-tool
adapters belong to Phase 5B after the local research-ready gate; they need not
wait for public-distribution hardening. Held-out v1/v2 and outcome comparisons across
models or hosts, plus ablation, quality, and human-effort comparisons, belong
to Phase 6. `evaluation.md` must be extended and preregistered before it is used
for a model- or host-outcome comparison not already present in its frozen arms.

## 17. Completion evidence for this design slice

The 5A.0 design slice is complete when:

- this contract is internally consistent with `ARCHITECTURE.md`,
  `state_runtime.md`, and the accepted Phase 1--4 contracts;
- the implementation plan distinguishes 5A from 5B without renumbering the
  six implementation phases;
- README and repository instructions accurately state the current boundary;
- Phase 4 historical documents record their merge without rewriting accepted
  predicates or evidence;
- `git diff --check` and documentation-link checks pass;
- an independent review finds no blocking design contradiction.

No Phase 5A runtime capability may be claimed from completion of 5A.0 alone.

Recorded Phase 5A.0 acceptance evidence is:

- independent roadmap and adversarial boundary reviews, with all blocking
  findings resolved and the final adversarial review reporting no remaining
  blocker;
- the complete non-long-gold regression selection: 403 tests passing with five
  platform/optional skips in 152.763 seconds;
- `doctor` and all five accepted schema/resource exporter checks passing from
  the source checkout;
- `git diff --check`, local Markdown-link validation, and the stale Phase 4
  status search passing;
- accepted Phase 4 main-history evidence retained rather than misreported as a
  new run: the uninterrupted Phase 1--4 full-genesis gold completed in
  6156.901 seconds before merge. The three hour-scale Phase 2/3/4 gold-runtime
  modules were intentionally not rerun for this documentation-only slice.

## 18. Phase 5A.1 local-machine-facade evidence

Recorded Phase 5A.1 acceptance evidence is:

- 60 focused `test_phase5a_*` tests passing, including root compatibility,
  navigation, strict transport, authority/egress, concurrency, candidate
  completion, schema/resource integrity, and atomic operational publication;
- one public-process deterministic route completing initialization,
  navigation, run opening, WorkPacket creation and delivery, fixture candidate
  writing, exact scientific validation, canonical commit, and a fresh-process
  idempotent retry;
- explicit fault tests showing that a fresh session receives a complete
  validated resume descriptor, a crash after durable `delivery_started`
  returns the original envelope and can close through `host.finish`, and a
  crash between immutable candidate capture and completion-start publication
  recovers even when the disposable candidate source is gone;
- the complete routine non-long regression selection: 472 tests passing with
  six platform/optional skips in 250.820 seconds. The three hour-scale Phase
  2/3/4 gold-runtime modules were intentionally excluded; their previously
  accepted full-chain evidence was not rewritten as a new run;
- all six then-current schema/resource exporter checks, Python compilation,
  `doctor` with `required_ok=true`, Markdown-link validation, and
  `git diff --check` passing. Lean and Node remain optional and unavailable on
  the verification machine;
- a final independent trusted-local audit reporting no Phase 5A.1 blocker.

This evidence establishes the generic local machine facade only. It does not
establish natural-language Codex activation, a model-produced candidate, the
local research-ready gate, v2 quality gains, or public-distribution readiness;
those claims remain owned by Phase 5A.2 or later slices.

## 19. Phase 5A.2 public Codex functional-slice evidence

The recorded evidence is in
[`../../review_outputs/phase5a2_codex_public_pilot`](../../review_outputs/phase5a2_codex_public_pilot/).
It establishes a bounded public slice, not the complete gate in section 15.1:

- a fresh-context Codex task in a prepared checkout was given one public
  synthetic theory seed, the project skill, and bridge responses. Its
  instructions prohibited source, tests, fixtures, gold answers, web access,
  prior pilots, literature targets, and subagents, and its run report recorded
  no read or use of them;
- engine commit `528b943704466c7e7ab2ec39112e5195e01864ee` and wheel SHA-256
  `a30a881cb905f7c10c0ac1f3b9b66f9d25281bb6118544addd6011a301306586`
  completed `frame.question_and_benchmarks` from natural language through
  WorkPacket delivery, one model-produced candidate, validation, and canonical
  commit with zero scientific repairs or human scientific decisions;
- replaying the exact completion request produced no duplicate transaction,
  completion operation, or head advance;
- the post-pilot navigation fix at
  `56279a91c9599ef282ef23ddeef8dcf7a2367410`, packaged with wheel SHA-256
  `9fffd76853021173e8c92409646990498d7ce7ed70329ef4067c09d61cae8b54`,
  selected `decompose.primitives` on continuation, and a state-summary-backed
  exact retry preserved the same operational run and canonical head;
- an earlier blind failure exposed a JSON-Schema/domain-model gap and generic
  completion error; the current bridge publishes typed relation invariants and
  bounded `codex_candidate_transaction_invalid` repair diagnostics;
- a separate model-based diagnostic gave the committed framing a holistic
  6.3/10 assessment and found substantive fixed-inspection, frozen-ledger,
  equilibrium-selection, and readability problems. Mechanical commit therefore
  is not evidence of Top-5 quality or reduced expert intervention;
- the recorded public-slice checkpoint completed a 74-test focused Phase 5A suite with
  one Windows symlink skip and a 486-test routine non-long suite with six
  platform/optional skips, plus all six then-current exporters, compilation of 138 Python
  files, `doctor` with
  `required_ok=true`, skill/YAML validation, Markdown-link validation, and
  `git diff --check`.

This slice does not demonstrate positive private, restricted, `local_only`,
hidden, or sealed Codex execution; first-ever installation from an empty
project; Claude Code or Cursor parity; a complete paper route; comparative
v1/v2 superiority; lower human effort; publication readiness; or the complete
local research-ready gate. The deterministic acceptance predicate for the
additive v8 work specified in
[`framing_quality_contract.md`](framing_quality_contract.md) now passes. Its
first frozen public rerun and its post-pilot status are recorded separately in
section 20; the earlier slice and hashes above remain historical evidence.

## 20. V8 public negative-diagnosis pilot and post-pilot stabilization

The later evidence is recorded in
[`../../review_outputs/phase5a2_v8_codex_public_pilot`](../../review_outputs/phase5a2_v8_codex_public_pilot/).
It separates four conclusions:

- **machine path:** `frame.question_and_benchmarks` and
  `decompose.primitives` canonically committed; `audit.framing_economics` did
  not commit after the initial candidate and two declared repairs;
- **candidate economics:** the audit honestly proposed `revise_framing` and did
  not fabricate a payoff witness, but its final force binding and two adjacent
  chain joins violated the exact PrimitiveGraph path contract;
- **disposition and authority:** `failed_terminal` is a durable operational
  host receipt, not a canonical scientific disposition. No FramingQualityBundle,
  replacement GateDossier, or human G1 Decision was committed;
- **quality and effort:** the noncanonical candidate can support later blind
  adjudication, but this run establishes neither research quality, readability,
  nor reduced human editing burden.

One repair opportunity was consumed by a leading JSON parse failure reported
by the agent as a UTF-8 BOM, and the final domain diagnostic returned a generic
message with empty details rather than all three path defects. The first finish
request also revealed an undiscoverable opaque-warning grammar, and the pilot
capture did not freeze overwritten request/candidate sources.

The post-pilot host-stabilization candidate normalizes one leading UTF-8 BOM at
the noncanonical source boundary, aggregates exact path diagnostics, exposes
the existing finish-token grammar in the Codex schema, and adds immutable
request/candidate capture. It changes no route registry, instruction, schema,
scientific acceptance condition, or human gate. The failed pilot did not
exercise these later fixes. The post-pilot source candidate passed its
deterministic gate.

The corrected-wheel R2 same-case task then traversed the stabilized host path,
committed framing and primitive decomposition, and exhausted two audit repairs
before recording operational `failed_no_effect`; no audit transaction or G1
decision occurred. Independent keyed evaluation classified the primary cause
as model-content/mapping error, diagnostic/authoring ambiguity as secondary,
and did not establish validator overconstraint. Its final disposition was
machine-mixed, `A-FAIL` (`0, 1, 1, 2, 2`), `REVISE`, and `R-FAIL`/H4. The
post-evaluation fixed/endogenous and endpoint diagnostic improvement is a
separate, semantics-preserving source change and was not exercised by R2.

The researcher selected the guaranteed-service certificate ledger on
2026-07-18. The R3 ordinary-model run then committed the frozen upstream
reframe and decomposition but exhausted both audit repairs without a canonical
audit. Locked independent adjudication classified the failure
`STRUCTURAL_TAX_PRIMARY` (0.86), not a V8 acceptance-semantics defect. A
noncanonical semantic compiler now reproduces the five exact relation
templates, derives the replacement dossier, batches channel and semantic-ledger
structural issues, and validates the locked negative diagnosis under the
unchanged V8 validator with zero canonical writes.

This prototype is not yet part of the public transport and the prior R3 run did
not exercise it. The held-out paired ordinary-model shadow is now complete.
Neither free-form Transaction nor Semantic V2 reached the unchanged V8
scientific validator in three attempts, and neither wrote canonical state or
confirmed a human gate. Transaction stopped on a relation-topology extra field
whose receipt exposed no near-match; Semantic V2 stopped on an incorrect force
margin binding whose receipt exposed neither the observed payoff-node kind nor
the unique compatible choice node. Strict JSON/file-output errors were also
contributory. Semantic V2 nevertheless reduced final source bytes by 51.22%
and leaf fields by 53.74%; blinded economics found no established material
scientific degradation, and its reader recovered more detail.

Public integration remains blocked. The bounded noncanonical slice now binds
only an explicitly selected force-margin position, reports Transaction detail
only for a unique single-field near-match, and atomically isolates one strict
duplicate-free JSON object. Force source/target and all economic comparisons
remain model-authored; every V8 predicate is unchanged. Focused source-level
private-oracle/adversarial checks pass, while packaged-runtime transport/oracle
verification remains required before a final fresh held-out pair. See the
[R2 report](../../review_outputs/phase5a2_v8_codex_public_pilot/rerun_attempt2_run_report.md),
[R3 protocol](../../review_outputs/phase5a2_v8_codex_public_pilot/rerun_attempt3_route1_protocol.md),
[adjudication/compiler shadow](../../review_outputs/phase5a2_v8_codex_public_pilot/rerun_attempt3_adjudication_and_compiler_shadow.md),
[held-out pair adjudication](../../review_outputs/phase5a2_v8_authoring_pair_v2/final_adjudication.md),
and [machine decision](../../review_outputs/phase5a2_v8_authoring_pair_v2/FINAL_DECISION.json).
