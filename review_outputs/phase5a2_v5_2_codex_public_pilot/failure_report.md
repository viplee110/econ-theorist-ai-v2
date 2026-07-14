# V5.2 public Codex pilot failure report

Status: **protocol/engine failure; post-freeze scientific diagnostic also
requires revision**

Pilot date: 2026-07-15 (Australia/Perth)

Frozen source commit: `cd018e54ffa8b8645058ff993562acec0fdf4807`

## Outcome

V5.2 repaired the exact no-progress failure observed in V5.1. With no route
forcing, framing replay, or caller-supplied budget, the engine selected:

1. `frame.question_and_benchmarks` at 4,000 units;
2. `decompose.primitives` at 8,000 units; and
3. `audit.framing_economics` at 18,000 units.

Framing and decomposition each committed on their second candidate. The
economics audit exhausted its initial candidate plus two permitted structured
repairs and remained uncommitted. The canonical head therefore stops after
decomposition at
`f7474b3bdf983d1033afbd38bdb24ca57cdbc9557deed0c9dbd378c28943b6f0`.
No human G1 decision was made, inferred, or recorded.

The strict protocol verdict is **protocol/engine fail**, not pass or scientific
revise. This is an end-to-end contract and harness failure, not canonical-store
corruption. Post-freeze inspection of the uncommitted audit candidate also
found a critical economic defect, recorded below only as redesign evidence.

## Exact route and repair sequence

| Route | Default budget | Candidate attempts | Terminal route result |
|---|---:|---:|---|
| `frame.question_and_benchmarks` | 4,000 | 2 | committed at `c7cb0241...` |
| `decompose.primitives` | 8,000 | 2 | committed at `f7474b3b...` |
| `audit.framing_economics` | 18,000 | 3 | uncommitted; repair limit exhausted |

The five rejected submissions all returned `mutated=false`:

1. framing cited a route name in `authority_basis`, which may cite only a
   previously effective Decision;
2. decomposition reversed the required target of `decomposes`;
3. the audit's baseline and countervailing forces used different targets;
4. after target repair, those forces did not have opposite directions; and
5. after direction repair, the audit failed the exact-input `audits`
   dependency rule.

The generator stopped immediately after the fifth rejection, as frozen by the
protocol. It did not submit a fourth audit candidate, continue navigation,
fabricate a gate decision, or modify the final candidate.

## What V5.2 established

The following machine claims passed for this case:

- ordinary continuation advanced rather than reopening framing;
- each scientific route had one immutable route run and failed candidates did
  not create duplicate canonical commits;
- registry-owned budgets resolved to 4,000, 8,000, and 18,000;
- route order and ownership remained engine-controlled;
- the successful framing and decomposition commits form one valid exact-head
  chain; and
- no Decision or effective human decision exists in the terminal store.

These results are a bounded regression success for the V5.1 navigation repair.
They do not compensate for the failures below.

## Contract-projection failure

All three audit candidates contained exactly four `audits` relations covering
the exact ResearchQuestion, BenchmarkSet, PrimitiveGraph, and source G1
GateDossier. The generator used the natural reading
`FramingQualityBundle -> audited input` with the relation schema's default
`trace_only` mode.

The exit validator instead requires each exact input to be the source of a
`hard` dependency into the FramingQualityBundle, with exact owner-facet and
semantic-hash bindings. It also requires a hard
`FramingQualityBundle -> replacement GateDossier` `governs` dependency. The
WorkPacket and candidate authoring contract projected relation types and
counts, but not these directions, modes, facets, or hashes. The first two audit
attempts were consumed by two separately emitted payload invariants before the
relation topology was diagnosed. A fourth attempt that merely reversed the
edges would still have failed on the undisclosed hard-dependency bindings.

This is primarily an incomplete contract projection plus serial diagnostic
ordering, not a reason to weaken validation or grant unlimited retries.

## Harness and evidence failures

- The first three start attempts failed with `PermissionError` and
  `mutated=false`. The first attempted a non-isolated user state directory
  because the wrapper did not successfully propagate its environment before
  process creation. This violates the frozen requirement that every engine
  invocation use the isolated `LOCALAPPDATA`.
- The fourth start successfully opened framing, but its large raw stdout was
  truncated by the host transport before archival. The next resume recovered
  the same still-open route and full packet, but it is not claimed to be the
  missing raw response.
- After the permitted audit attempts were exhausted, the generator recorded a
  terminal stop but the canonical audit `run.json` remained `running`; the
  protocol has no committed abandonment record for this condition.
- This pilot observed packet replay and non-mutating candidate retry, but did
  not directly replay an already successful completion request. Full
  completion exactly-once evidence therefore remains incomplete at the pilot
  level.

## Post-freeze economics and reader diagnostic

The uncommitted candidate is not a canonical audit and cannot change the
overall verdict. It nevertheless provides useful blinded failure evidence.

It correctly distinguished a fixed state-contingent inspection rule from a
fixed aggregate inspection rate, rejected the matched-expiry benchmark as a
clean depletion control because it also changes certificate reuse, and kept
cross-model equilibrium-branch pairing unresolved.

It missed a more basic payoff-ledger contradiction. In the committed pre-G1
PrimitiveGraph's proposed, not human-approved, ledger, a certified seller gives
the buyer service payoff 1 with no purchase price. Any inspection costs `c` in
`(0,1)` and can deliver service payoff at most 1, so inspection yields at most
`1-c < 1` whenever a certificate is available. Conditional on that proposed
ledger:

- with a certificate present, inspection is strictly dominated;
- with one certificate, it is purchased and consumed without inspection;
- with two certificates, one is consumed and only its identity is selected;
  and
- in the no-certificate state where inspection may occur, there is no
  certificate to deplete.

The advertised `inspection -> allocation -> certificate depletion` path is
therefore inactive under the proposed ledger. Treating the missing
buyer-facing price or tradeoff as merely a later scope choice is insufficient.
The illustrative one-certificate example is not a valid best-response witness,
so the opposing-force, three-link mechanism, concrete-example, and benchmark
role parts of the reader-transfer gate fail even though the prose is fluent.

## Bounded repair implications

The next candidate should make only failure-driven changes:

1. project route-specific relation templates and force-conflict invariants in
   the machine-readable authoring contract, including exact endpoints,
   dependency modes, facets, and engine-computed semantic bindings;
2. return independent structured violations together, or preflight mechanical
   topology before consuming a scientific repair attempt;
3. make the first invocation genuinely isolated, retain every raw response,
   and record an explicit terminal abandonment when the frozen retry budget is
   exhausted;
4. require an active-margin witness for every claimed mechanism link: one
   concrete state, feasible alternative actions, payoff comparison, and the
   inequality under which the response is nontrivial;
5. either introduce a buyer-facing tradeoff that can make inspection optimal
   while a certificate is outstanding, or delete the buyer-controlled
   depletion claim and reframe around mechanically induced stock composition;
   and
6. preserve one-use certificate technology in the depletion control and state
   an operational branch correspondence before making causal benchmark claims.

No new route, gate, scholar persona, general retry expansion, or broad security
layer is justified by this run.

## Evidence retention and privacy

The public archive retains 53 numbered invocation files and 37 canonical-store
files from the permitted project, provenance, refs, runs, snapshots, staging,
transactions, and views subtrees. It excludes the virtual environment,
distribution copy, local skill copy, host-local application state, locks, and
engine operational state. Their frozen hashes or exclusions are already
recorded by the preflight and generator inventories.

The retained set was scanned for common API-key, GitHub-token, AWS-key,
bearer-token, private-key, password, cookie, credential, email, and user-profile
signatures. No secret or email signature was found. One Windows user-profile
component appeared in two otherwise retained files and was replaced by
`<USERPROFILE>` in the public copies. Exact original hashes and the bounded
redaction are disclosed in `public_redaction_manifest.md`; the original bytes
remain only in the private frozen execution root.
