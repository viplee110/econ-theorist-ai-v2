# Independent machine and protocol audit of the V5.3 public pilot

## Scope and evidence boundary

This is a read-only postmortem of the frozen V5.3 public Codex pilot, followed
by this report as the only file added by the reviewer. It checks the complete
route, attempt, request/response, commit, finish, and replay chain. It also
tests the failed audit candidate counterfactually in memory; none of those
counterfactual candidates was written, staged, or committed.

The central attribution is deliberately split three ways:

1. **Generator misuse caused the observed terminal stop.** The public contract
   did define a usable computation, the installed wheel exposed it, and the
   generator did not use it.
2. **The frozen retry protocol was violated.** The generator recorded `finish`
   after one audit attempt even though `finish` was reserved for retry
   exhaustion.
3. **A real product-UX defect remains.** A natural-language IDE agent should not
   have to manufacture deterministic engine metadata with a Python import.
   That burden belongs in the bridge, even though it was technically possible
   in this pilot.

Accordingly, this pilot is **not evidence of an unavoidable engine
compatibility failure**, and it is also **not a machine or scientific pass**.

## Overall verdict

| Dimension | Verdict |
|---|---|
| Route selection and budgets | Pass through the audit-route delivery |
| Framing commit | Pass, first attempt |
| Primitive-decomposition repair and commit | Pass, second attempt |
| Audit commit | Fail; no audit candidate committed |
| Request/response binding | Pass for every archived invocation |
| Canonical no-mutation on errors | Pass |
| `finish` exact replay | Pass: 014 and 015 are byte-identical |
| Generator use of the public contract | Fail |
| Frozen retry protocol | Fail |
| Scientific route acceptance | Not reached in the actual audit attempt; the candidate is invalid |
| Product usability of runtime-derived hashes | High-priority repair |

## Reconstructed execution chain

1. `001_start` opened `frame.question_and_benchmarks` with 4,000 lexical
   budget units.
2. `003_complete_attempt1` committed the framing transaction at
   `7ad23adbeba3d0bde9a8bfeca0944e2e08881309e3e75a8c322f92f0098187f6`.
3. `004_resume` selected `decompose.primitives` with 8,000 units.
4. `006_complete_attempt1` rejected a relation that did not target the
   `PrimitiveGraph`; the response was structured and nonmutating.
5. `008_complete_attempt2` committed the repaired decomposition at
   `7575110612a3faff6d5784f1fb2bf34d1a31780d6b761d251a1c353460d7c789`.
6. `009_resume` selected `audit.framing_economics` with 18,000 units and
   delivered four exact `audits` templates plus one runtime-bound `governs`
   template.
7. `011_complete_attempt1` rejected the all-zero upstream hash without
   canonical mutation.
8. `012_resume_current` re-delivered the same route run, WorkPacket hash,
   authoring-contract hash, base head, and candidate path under a fresh
   delivery envelope.
9. `013_finish_engine_compatibility` was itself rejected because the warning
   strings were free text rather than bounded tokens.
10. `014_finish_engine_compatibility` recorded a host failure while leaving the
    canonical head unchanged.
11. `015_postfreeze_finish_replay` replayed the exact 014 request. The 014 and
    015 request SHA-256 is
    `ED1BA3C2D68C08A9845469BFB1BC6CB5E0B81E76DF26467155AFE4FDBAF362CE`,
    and the 014 and 015 raw response SHA-256 is
    `924E1E42AC5E804D506543CCE93F1BF32EC5298D75053C4D496A5BBCF32C91D6`.
    This is a genuine exactly-once replay pass for `finish`.

Every capture metadata file reports a valid single JSON object, a valid strict
bridge response, the expected operation, the canonical request digest, an
unchanged source request, and empty stderr. Exit code 2 occurs only for
structured bridge errors. The only canonical head advances are the two
`committed` responses above.

## Findings by severity

### BLOCKING — the frozen pilot did not satisfy its machine gate

The audit route never committed, so the expected pre-G1 path did not complete.
The `recorded_failure` receipt accurately records an operational event, but it
does not convert the uncommitted audit candidate into canonical evidence and
does not establish that the engine could not complete the route.

The branch should not be described as having passed the V5.3 pilot. A fresh
blind run is required after the minimal interface repair.

### BLOCKING — generator misuse and retry-protocol violation

The delivered authoring contract explicitly says:

> For `runtime_facet_semantic_hash_v1`, compute
> `econ_theorist.runtime.freshness.facet_semantic_hash` over the complete
> candidate source `EntityVersion` and the declared whole facet.

That instruction is present in
[`run/009_resume_stdout.json`](run/009_resume_stdout.json). The same rule is
defined in
[`candidate_contract.py`](../../src/econ_theorist/candidate_contract.py#L232).
The installed pilot wheel can import the named function. Applying it to the
archived candidate's complete `FramingQualityBundle.economic_interpretation`
facet returns:

`5a0a8163e4f9cd9777da513359052bde50d8ac8e6d5261cf062571f8040f3d0f`

The generator instead wrote 64 zeroes at
[`run/010_candidate_attempt1.json`](run/010_candidate_attempt1.json#L1206).
Importing a named public function from the installed wheel is not source
inspection and was not prohibited by the frozen isolation rule. The statement
in [`generator_report.md`](generator_report.md#L20) that the contract supplied
“no contract-defined derivation” is therefore false.

The frozen protocol permits an initial candidate and two diagnostic repairs,
then permits `finish` only for an otherwise unrecorded retry-exhaustion
termination ([`protocol.md`](protocol.md#L97)). The terminal request instead
records `candidate_attempts.one`
([`run/014_finish_engine_compatibility_request.json`](run/014_finish_engine_compatibility_request.json#L13)).
The generator neither exhausted the permitted attempts nor encountered an
abnormal host/model abort. Calling `finish` was a protocol violation.

This is the primary cause of the observed terminal stop.

### BLOCKING — the audit candidate had latent scientific-validator failures

Correcting only the semantic hash in memory does not make the candidate valid.
It exposes the next route diagnostic:

`active_margin_witness_missing: every choice-dependent mechanism step requires a concrete payoff comparison`

The actual bridge attempt never reached the Phase 5 route validator. Generic
relation referential integrity runs first
([`replay.py`](../../src/econ_theorist/runtime/replay.py#L2205)); the Phase 5
route validator runs later
([`replay.py`](../../src/econ_theorist/runtime/replay.py#L2478)). Thus the claim
in [`generator_report.md`](generator_report.md#L16) must not be read as a
scientific-route pass.

To determine whether the hash was masking other defects, the reviewer applied
minimal in-memory adjustments solely to expose the next gate, not as endorsed
scientific repairs:

1. correct runtime hash only -> `active_margin_witness_missing`;
2. add a concrete witness to the second choice-dependent chain step ->
   `placebo_control: an endogenous active margin is incompatible with its PrimitiveGraph node kind`;
3. remove that semantic-ledger type mismatch ->
   `replacement dossier lacks the exact framing-quality requirement`;
4. change the appended revise requirement from `gap_disclosed` to the required
   `risk_disclosed` -> the counterfactual transaction validates in memory.

The relevant validators are at
[`framing_quality_validation.py`](../../src/econ_theorist/framing_quality_validation.py#L721),
[`framing_quality_validation.py`](../../src/econ_theorist/framing_quality_validation.py#L878),
and
[`framing_quality_validation.py`](../../src/econ_theorist/framing_quality_validation.py#L1250).
The original candidate's `g1.framing_quality` row uses `gap_disclosed` at
[`run/010_candidate_attempt1.json`](run/010_candidate_attempt1.json#L1010).

This counterfactual result proves two narrow points only: the runtime hash was
not the sole candidate defect, and the scientific validator would have blocked
the archived candidate. It does not approve the economics, the reader-facing
memo, or the in-memory adjustments.

### HIGH — the public authoring interface is executable but poorly factored

The interface is not literally incomplete:

- the contract names the exact callable;
- the wheel exposes it; and
- the correct value is reproducible without repository source.

It is nevertheless a product-UX defect for the intended one-sentence IDE
experience. The template deliberately carries `upstream_semantic_hash: null`
for a candidate-output source
([`candidate_contract.py`](../../src/econ_theorist/candidate_contract.py#L612)),
while canonical `SemanticFacetRef` requires a 64-hex digest
([`models.py`](../../src/econ_theorist/models.py#L258)). The bridge strictly
parses a complete canonical `Transaction` before scientific validation
([`completion.py`](../../src/econ_theorist/machine/completion.py#L489)). No
candidate-draft representation lets the generator declare “engine-derived.”

This forces the language model to perform deterministic bookkeeping that
contains no economic judgment. It wastes an attempt, masks scientific
diagnostics, creates IDE/provider variance, and competes with the limited
repair budget. Those are research-productivity costs, not merely enterprise
hardening concerns.

The correct classification is therefore:

- **observed failure:** generator misuse;
- **underlying product debt:** engine authoring-UX defect;
- **not supported by the evidence:** unavoidable engine incompatibility.

### MEDIUM — `finish.warnings` has a public-schema/runtime mismatch

`CodexFinishRequestV1` exposes `warnings` as arbitrary nonempty strings
([`codex_bridge.py`](../../src/econ_theorist/codex_bridge.py#L167)). The runtime
silently imposes a 128-character safe-token grammar
([`completion.py`](../../src/econ_theorist/machine/completion.py#L65) and
[`completion.py`](../../src/econ_theorist/machine/completion.py#L734)). The
free-text 013 request therefore passed bridge parsing and failed only inside
completion. The 014 bounded identifiers repaired it.

This did not corrupt state and is not a scientific blocker, but the
authoritative request schema should express the rule directly so one bridge
call is sufficient.

### MEDIUM — fail-fast diagnostics and a three-attempt cap can hide multiple visible defects

The authoring contract already exposed the active-margin and semantic-ledger
invariants, yet the generator did not satisfy them. The route then reports one
validator failure at a time. In this candidate, the hash plus three latent
validator failures would exceed the frozen three-attempt budget if repaired
naively in sequence.

Do not respond with a broad enterprise workflow. The focused repair is to
remove engine-derived metadata from the attempt budget and return precise,
object-addressed science diagnostics (step number, object ID, node kind, and
expected dossier condition) so one scientific repair can address all disclosed
issues.

### LOW — error evidence does not expose the engine-computed candidate digest

`006` and `008` have byte-identical complete requests because
`expected_candidate_digest` is null and the same candidate path was reused,
although the candidate contents differ. Internally, the bridge computes the
candidate digest and includes it in the operation key
([`codex_bridge.py`](../../src/econ_theorist/codex_bridge.py#L888)), so engine
exactly-once semantics remain sound. The error response does not expose that
effective digest, however, so the public archive cannot cryptographically bind
an error diagnostic to its saved candidate using the response alone.

This is an evidence-quality improvement, not a priority over the scientific
and UX repairs above.

## Minimal repair choice

### Option A — one-liner or CLI helper

A helper can parse the complete candidate `Transaction`, select the
candidate-output `FramingQualityBundle`, call the named installed function,
and print or insert the hash. This is enough to show that the frozen interface
was publicly evaluable. A small public command such as
`etai candidate materialize <candidate-path>` would be less brittle than a
route-specific Python one-liner.

Advantages:

- smallest immediate implementation change;
- preserves the canonical schema; and
- useful as an explicit debugging tool.

Disadvantages:

- the IDE agent must remember and invoke an extra mechanical step;
- a skipped helper still consumes a scientific attempt;
- it remains provider- and host-behavior dependent; and
- it exposes storage bookkeeping in the user workflow.

This is acceptable only as a temporary reproduction/debugging aid.

### Option B — bridge auto-materialization (recommended)

The bridge should own every `runtime_facet_semantic_hash_v1` value. The
candidate draft may use `null` only at the exact runtime-bound template. Before
strict canonical validation and before computing the candidate digest or
operation key, the bridge should:

1. load the exact delivered authoring contract;
2. match each runtime template to exactly one candidate relation;
3. verify the exact output ordinal, entity type, source/target IDs, facets,
   dependency mode, and relation type;
4. construct the complete candidate source `EntityVersion`;
5. compute and inject the whole-facet semantic hash in memory;
6. strict-validate the resulting canonical `Transaction`; and
7. compute identity and exactly-once keys from the materialized canonical
   bytes.

The bridge must not globally make canonical semantic hashes optional and need
not rewrite the readable candidate source. A correct explicit hash may remain
acceptable; an incorrect explicit hash must still fail. Null materialization
must be available only for a uniquely matched exact runtime template.

This option is recommended because the derived hash is engine truth, not
scientific content. It simplifies every IDE, saves attempts and tokens, and
lets the economics validator become the first meaningful diagnostic.

## Required focused tests

1. **Cold serialized public path.** Using only an installed wheel, a serialized
   WorkPacket/authoring contract, and a draft with the runtime hash null,
   complete and commit a candidate. Assert that the canonical relation hash is
   exactly `facet_semantic_hash(complete_source_entity, declared_facet)`.
2. **Pilot regression.** Feed the archived audit candidate through
   materialization. Assert that the hash boundary disappears and the first
   diagnostic is `active_margin_witness_missing`, with no canonical mutation.
3. **Exact-template fail closed.** Reject null materialization for a wrong or
   duplicate relation, wrong source/target, wrong output ordinal, wrong facet,
   wrong dependency mode, or any non-runtime template.
4. **Explicit-hash behavior.** Accept the correct explicit digest and reject an
   incorrect explicit digest without silently replacing it.
5. **Identity and replay.** Assert that identical drafts materialize to
   identical canonical bytes, candidate digests, operation keys, and replay
   responses; changing the FQB facet must change both derived hash and
   candidate digest.
6. **Legacy boundary.** Keep frozen v1-v5 contract bytes unchanged. If the
   serialized v6 authoring contract changes, bind it through a new exact
   semantics/version boundary rather than retrospectively rewriting evidence.
7. **Diagnostic precision.** Return the exact causal step for a missing witness,
   the object and actual/allowed node kind for a semantic-ledger mismatch, and
   the required `recorded_condition` for the replacement dossier.
8. **Finish schema.** Make free-text warnings fail `CodexFinishRequestV1`
   validation itself and bounded unique warning identifiers pass.
9. **Generator protocol.** Add a skill/integration test that a repairable
   candidate error cannot trigger `finish` before retry exhaustion; host abort,
   explicit cancellation, and true retry exhaustion remain allowed.
10. **Retain the existing finish replay proof.** Preserve the 014/015
    byte-identical request and response evidence as an exactly-once fixture.

## Evidence and claim boundary after repair

Auto-materialization plus these tests would establish a reliable public
mechanical interface. It would not establish that the candidate has good
economics, that the V5.3 audit passes, that human burden is lower, or that the
system approaches Top-5 quality. Those claims require a new fresh blind pilot
and the independent economics and reader-transfer gates.

The current sibling audits describe the terminal event as an engine or
engine/protocol compatibility failure in
[`economics_audit.md`](economics_audit.md#L22) and
[`reader_transfer_audit.md`](reader_transfer_audit.md#L16). That attribution
should be corrected during integration: the observed terminal stop was
generator misuse plus a retry-protocol violation, while the interface still
has the separate high-priority UX defect described here.

## Final decision

**Protocol/engine pilot result: FAIL, but not for the reason stated in the
generator report.** Route ownership, budgets, request binding, nonmutation,
commits, and exact finish replay behaved correctly. The generator ignored a
publicly executable contract instruction, stopped before retry exhaustion,
and misclassified the stop. The engine should nevertheless absorb the
runtime-derived hash because doing so is the smallest high-leverage change for
the intended natural-language research workflow. After that change, rerun the
same fresh blind pilot and let the scientific validators, not bookkeeping,
determine the outcome.
