# Machine protocol v1

Status: Phase 5A.1 local machine facade implemented and verified; a thin
public-only Codex projection and one real framing-route pilot are recorded in
the current tree. The full local research-ready gate remains open, while
signed/public-distribution hardening is optional 5A.5

## Host-neutral transport and Codex projection

The canonical host-neutral structured transport is:

```text
etai machine invoke --request -
etai machine invoke --request REQUEST.json
```

Input is one `MachineRequestV1` JSON object. Standard output is exactly one
canonical `MachineResponseV1` JSON object followed by one newline. A valid
blocked operation is represented by `outcome`, not inferred from prose or
standard error. The request is limited to 16 MiB. Ordinary terminal commands
remain available as an advanced/manual compatibility surface, but official
host projections use this protocol.

The prepared-checkout Codex projection is:

```text
etai codex invoke --request -
etai codex invoke --request REQUEST.json
etai codex invoke --schema bundle
```

This is a thin engine-owned projection over the same machine operations. Its
v1 requests start or resume work, complete one exact candidate, or record an
honest host-session finish. The start request binds one Codex session, exact
root, optional public project initialization, and bounded research brief. It
currently accepts public work only and fails closed before packet delivery for
unsupported privacy. A ready response includes the exact WorkPacket plus a
mechanical candidate-authoring contract: transaction bindings, output
cardinalities, JSON Schemas, and typed cross-field model invariants. An invalid
candidate returns bounded structured repair diagnostics rather than exposing a
traceback or accepting direct canonical edits. A finish response reuses the
host-neutral `host.finish` receipt. The Codex projection uses it only for an
otherwise-unrecorded real termination after delivery: exhausted declared
retries, explicit user cancellation, or an abnormal host/model abort. Ordinary
human waits, clarifications, handoffs, and intentional pauses are not finishes.
A recorded finish does not rewrite the immutable `RouteRun` or prevent a later
exact resume.

The repository's pilot capture helper is evaluation tooling, not another
machine or Codex interface. It pre-reads and strictly validates one bridge
request, binds its selected root, sends those exact bytes over standard input,
and streams raw stdout and stderr directly to local evidence files. It records
JSON-object validity separately from strict `CodexBridgeResponseV1` validity;
a successful child process that emits arbitrary JSON still makes the capture
command fail. Those captures can contain local paths or research content: they
must be frozen, hashed, secret-scanned, and, where necessary, redacted with an
explicit manifest before any public archive is created.

The exported schemas are in [`schemas/machine/v1`](../../schemas/machine/v1/).
The packaged [`host-manifest.v1.json`](../../machine/host-manifest.v1.json)
defines which operations are model-callable, adapter-internal,
trusted-human-only, or excluded.

## Envelope

Every request contains:

```json
{
  "request_schema": "econ-theorist/machine-request/v1",
  "operation": "project.inspect",
  "operation_key": null,
  "project_root": "C:/absolute/paper/root",
  "discovery_grant": {
    "grant_schema": "econ-theorist/discovery-grant/v1",
    "selected_root": "C:/absolute/paper/root",
    "allowed_discovery_roots": ["C:/absolute/paper/root"],
    "ancestor_check_boundary": "C:/absolute/paper/root",
    "stable_workspace_root": "C:/absolute/paper/root"
  },
  "parameters": {}
}
```

All root-aware operations require an absolute root and exact
`DiscoveryGrantV1`. The engine does not scan an ungranted parent or sibling.
Every state-changing operation requires an operation key; read-only operations
forbid one. The same key plus the same canonical request recovers or replays
the operation. Reusing a key for different bytes is `conflict`.

## Operations

| Operation | State effect | Required parameter payload |
|---|---|---|
| `bootstrap.plan` | none | descriptor, bounded HTTPS origins, environment and launcher paths; external trust evidence is adapter-injected |
| `bootstrap.verify` | local operation receipt | no model parameters; a public-release verifier may inject exact evidence |
| `project.bind_or_initialize` | conditional genesis | `initialize`, exact project name, optional requested project id, and optional `project_privacy`; local operational home/actor are host configuration |
| `project.inspect` | none | compartments, clearance, budget/scope and optional `RunInputBriefV1`; the Phase 5A actor is engine-owned |
| `navigation.plan_next` | none | same navigation inputs as inspection |
| `run.open_or_resume` | run-operational files | exact `NavigationCandidateV1` and its optional exact input brief |
| `egress.plan` | none | run/packet hashes, capability receipt, host/provider/model and handling declarations |
| `packet.deliver` | delivery ledger/envelope | exact plan and optional local capability receipt; provider/public-release paths use injected session and authorization evidence |
| `candidate.complete` | stage and optional canonical commit | action, run/packet/envelope bindings, candidate path/artifact map, and bounded reasoning/tool/warning labels |
| `host.finish` | host receipt | run/packet/envelope bindings, bounded reasoning/tool/warning labels, and one failure/cancel/uncertainty status |
| `decision.confirm` | canonical Decision commit | exact Decision, challenge, receipt and injected trusted channel |
| `operation.inspect` | none | operation key and `project` or `preproject` scope |

Operation-specific payloads are validated strictly: unknown fields, wrong
scalar types, missing bindings, unsafe paths, or unbounded receipt text fail.
Tuple fields are JSON arrays. `candidate.complete.action` is one of
`stage_only`, `commit_staged`, or `stage_and_commit`. Host receipts accept only
opaque bounded tool/warning codes and one reasoning-exposure class; they never
accept chain-of-thought.

## Local research profile and privacy surfaces

The active profile trusts the local researcher, operating system, selected IDE
and account, and ordinary package manager. The protocol protects against model
mistakes, wrong-root writes, stale/repeated operations, ordinary interruption,
and accidental context mixing. It does not treat model-reported host settings
as proof against a compromised IDE, provider, or operating system.

For an ordinary nonsealed `local` plan, `packet.deliver` may accept the exact
capability receipt in the request and generate its own timestamp and session
identifier. `candidate.complete` and `host.finish` can then derive the host
identity from the immutable local delivery envelope and plan. This keeps the
full local CLI usable without a host-native attestation service. Hidden or
sealed packets never use this fallback.

The ordinary request union deliberately excludes approval issuance,
revocation, egress authorization issuance, and unrestricted raw decisions.
The generic CLI cannot turn a model-supplied assertion into a trusted human
gesture. `decision.confirm` succeeds only when a host adapter injects the
matching non-model-callable channel. The optional provider/public-distribution
path similarly retains an injected channel and authorization ledger.

`local_only` work never receives a provider-backed plan. Restricted provider
work requires verified isolation and known handling. Every authorization has
an exact positive delivery bound. The engine records `delivery_started` before
returning packet bytes. A delivery retry or inspection after bytes may have
crossed the boundary returns `unknown_possible_egress` with no packet.

## Host-neutral handoff

`RunInputBriefV1` carries the user's bounded research question without changing
the frozen `RouteRun` schema. Its hash is part of the complete navigation key.
The deterministic `WorkPacketV1` is compiled only from the immutable run,
context manifest, compiled context, input brief, and packaged policy bytes. It
contains no host/model/session, absolute path, operation key, or time. Those
belong to a separate delivery envelope and host receipt. Consequently two
supported hosts using the same engine/policy bytes resume the same run and
obtain the same work-packet hash.

## First local executable sequence

1. Install a pinned commit or local wheel from the user-selected repository and
   run `doctor`. A source checkout remains a development path; the optional
   inventory verifier, rather than `doctor` alone, can classify it as
   `development_only`. Signed bootstrap evidence belongs to the optional
   public-release profile.
2. `project.bind_or_initialize` performs a zero-write compatibility probe and
   creates genesis only after explicit initialization intent and identity.
3. `project.inspect` or `navigation.plan_next` reports one exact next route,
   ambiguity, a human gate, repair, or completion.
4. `run.open_or_resume` creates one run and deterministic packet; concurrent
   hosts converge under the navigation/canonical lock order.
5. `egress.plan` and `packet.deliver` record the selected local execution and
   return the exact nonsealed packet.
6. The host writes only the packet's candidate/shadow paths, then calls
   `candidate.complete` or `host.finish`.

This sequence remains the engine contract for Codex, Claude Code, Cursor, and
other thin projections. The recorded Codex slice demonstrates one-sentence
activation only in a prepared checkout and only for a public framing route. It
does not establish cold installation, positive private execution, a signed
production release, multi-agent execution, host parity, or improved research
quality.
