# Independent evaluation report

## 1. Integrity and independence

**Integrity result: PASS.** Before reading the evidence, I verified `MANIFEST.md`
at SHA-256
`a5c0cbd339fac2765cdffe65d8a087b715754063cd4eaaff054581938ed068b4`.
I then checked all 35 allowlisted inputs individually: every file was present,
every byte count and SHA-256 matched the manifest, and their byte total was
288,722. The package contained only those inputs, `MANIFEST.md`, and an empty
`report/` directory. No unexpected file or directory, reparse point, or
alternate data stream was found.

The only visible generator model label is `gpt-5`
(`CANONICAL_STATUS.json`, `$.model_observation.request_label`). The selected
tier is recorded only as `ordinary_or_medium`. The provider and actual backend
model were not independently confirmed
(`$.model_observation.provider_independently_confirmed = false` and
`$.model_observation.backend_model_independently_confirmed = false`). The
evaluation package supplies no independently observable backend identity for
this evaluator either.

This evaluation used only the allowlisted package. It did not use the web,
subagents, `etai`, the generator root, a source repository, or parent/sibling
directories. The following limitations bind every finding:

- The generator WorkPackets, candidate-authoring contracts, source, tests,
  registries, reference candidates, old evaluations, and generator report are
  absent. Their contents and the completeness or usability of a hidden
  WorkPacket cannot be inferred.
- The captures establish immutable request/candidate snapshots and valid bridge
  response envelopes, but they do not reveal the hidden validator predicate or
  intended authoring examples.
- There is no canonical audit transaction. The audit evidence consists of
  three rejected candidate snapshots plus a recorded-failure finish response;
  the canonical head remains the primitive-decomposition transaction.
- There is no solved equilibrium, payoff witness, transition matrix,
  comparative-static calculation, validation result, welfare result, or
  literature evidence. Distinctiveness below is about the proposed puzzle, not
  novelty.
- The cold reader saw only `evidence/economist_memo.md`; the frozen retell is an
  observation about that memo, not evidence that omitted upstream details were
  absent from every candidate.

## 2. Cold-reader adjudication

I apply the five frozen probes to the already frozen retell without rewriting
it.

1. **Certificate guarantee: not recovered.** The retell accurately reports
   that the memo does not say what the certificate certifies
   (`evidence/cold_reader_retell.md`, **§2 What a certificate appears to
   guarantee**). This is a faithful reading of the memo, but it means probe 1
   is unanswered. The memo's **Mechanism** section mentions only a conditional
   chain and an unresolved payoff comparison.
2. **Visible-certificate actions and payoff comparison: not recovered.** The
   retell's **§3 Buyer's apparent actions when a certificate is visible** says
   that no concrete action set, choice rule, or comparison can be recovered.
   Thus probe 2 fails as a reader-recovery test even though the retell correctly
   diagnoses the memo's omission.
3. **Failed link: partially recovered; zero-stock logic: not recovered.** The
   retell's **§4 Missing causal link and why it matters** correctly identifies
   the missing active choice tradeoff and refuses buyer-side attribution. It
   never explains why a search witness observed only when the certificate stock
   is zero cannot establish positive-stock trade and certificate depletion.
4. **Closed feedback versus reweighting: not recovered.** Section 4 says that
   behavior is not shown to respond to stock composition, but it does not
   distinguish a closed state/action/transition feedback from a change in the
   stationary weights on zero- and positive-certificate states. Probe 4 is
   therefore unanswered.
5. **Next object and kill observation: partially recovered.** The retell's
   **§5 What the researcher must do next, and what would kill the branch**
   points to the upstream PrimitiveGraph, an exact active-margin witness, and a
   failure condition. It does not recover the next high-value scientific
   choice—guaranteed-service versus information-only certificate semantics—or
   the guaranteed-service dominance derivation. Its **§6 Points not
   recoverable** confirms that the action, payoff, state, and transition graph
   would have to be reconstructed.

**R diagnostic: R-FAIL for cold-reader recovery.** The retell is an accurate
diagnosis of a thin memo, but accuracy about missing information is not the same
as passing the probes. It fully recovers neither the certificate payoff
envelope nor the zero-stock/reweighting distinction; probes 1, 2, and 4 fail,
and probes 3 and 5 are only partial.

**Human burden: H4.** The retell provisionally labels itself H3 in **§7**, but
the frozen burden rule places an output that hides certificate dominance or
requires reconstruction of the state/payoff graph in H3--H4. Here the human
must first discover the central guaranteed-service contradiction, choose a
certificate ledger, and then remodel several payoff, state, transition, and
attribution links. That is more than several local rewrites; it is the H4
case.

## 3. Economics rubric

| Frozen-key item | Score | Evidence and adjudication |
|---|---:|---|
| 1. Certificate payoff envelope | **0** | The committed guaranteed-opportunity branch is visible in `evidence/frame/attempt1.candidate.json`, `$.operations[0].entity.facets.economic_interpretation.payload.proposed_scope`, and in the full benchmark at `$.operations[1].entity.facets.economic_interpretation.payload.benchmarks[0].exact_primitives[1]`. Buyer actions and service payoffs appear at `...benchmarks[0].exact_primitives[0]`, `...exact_primitives[2]`, and `...timing[2]`. Yet the final audit candidate says only that no same-state ledger is available (`evidence/audit/attempt3.candidate.json`, `$.operations[0].entity.facets.economic_interpretation.payload.disclosed_gaps[0]`) and never performs the already available dominance comparison. This misses the decisive envelope rather than merely disclosing an unresolved term. |
| 2. State and transition closure | **1** | The audit records carryover and consumption conditionally (`evidence/audit/attempt3.candidate.json`, `$.operations[0].entity.facets.economic_interpretation.payload.causal_chain[1]` and `[2]`) and explicitly withholds an active witness. Its full-row path is at `...payload.benchmark_assessments[0].channel_path`. But it neither supports selection of the certified seller in a positive-stock state nor separates that trade from mechanical consumption and later zero-stock inspection. No complete issuance/stock/composition law is supplied. The gap is disclosed with `REVISE`, so this is unresolved rather than concealed. |
| 3. Causal attribution | **1** | The final candidate refuses a distinctive mechanism, labels attribution unresolved, and records endogenous weighting (`evidence/audit/attempt3.candidate.json`, `$.operations[0].entity.facets.economic_interpretation.payload.benchmark_assessments[0].aggregate_invariance`, `...attribution_strength`, and `...disclosed_gaps[1]`). This avoids inferring a same-state response from disjoint witnesses. It does not, however, state whether the remaining effect is merely stationary-distribution reweighting or close an action-to-transition feedback. Accurate non-claim plus an exact gap earns 1. |
| 4. Benchmark meaning | **2** | The audit distinguishes frozen policy/state accounting, transition-kernel deletion, and inspection disabling; it also calls the selection rule a selector rather than robustness. Exact paths are `evidence/audit/attempt3.candidate.json`, `$.operations[0].entity.facets.economic_interpretation.payload.benchmark_assessments[1]`, `[2]`, and `[3]`, especially each row's `held_fixed`, `reoptimizing`, `aggregate_invariance`, and `selection_assurance`. The canonical definitions are bound at `evidence/canonical/frame.transaction.json`, `$.operations[1].entity.facets.economic_interpretation.payload.benchmarks[1:4]`. The expiry row is treated only diagnostically, not as proof of a pure depletion channel. |
| 5. Disposition and repair | **2** | The rejected audit content nevertheless gives `revise_framing`, no readiness claim, typed causal-attribution and reoptimization gaps, and exact upstream refs (`evidence/audit/attempt3.candidate.json`, `$.operations[0].entity.facets.economic_interpretation.payload.proposed_action`, `...disclosed_gaps[0].repair_target_refs`, and `...disclosed_gaps[1].repair_target_refs`). The replacement dossier also proposes `revise` and preserves the human boundary at `$.operations[1].entity.facets.authority.payload.proposed_action` and `...requirements[3]`. Its repair diagnosis is incomplete about dominance, but the disposition itself satisfies this item. |

**Total: 6/10. Economics result: A-FAIL.** The frozen rule makes any score of
0 an A-FAIL; the stronger scores on benchmark meaning and disposition cannot
compensate for item 1.

### 3.1 Certificate payoff envelope

The committed framing chooses, provisionally, a guaranteed-service ledger: an
eligible high-capacity seller certifies a particular high opportunity, that
opportunity remains the certified opportunity while carried, and service
succeeds exactly for a high current opportunity. Under the stated normalized
buyer payoff and common terms, a visible certificate therefore yields 1. An
inspection of an uncertified seller yields at most `1 - c`, exit yields 0, and
buying an uncertified seller without inspection yields a belief-weighted value
no greater than 1. For `c > 0`, inspection is strictly dominated whenever a
certificate is available; for `c = 0`, it is at best weakly dominated absent
another buyer-facing force. The audit's assertion that the comparison is wholly
unavailable is too strong. What remains unavailable is the complete common-
state comparison among certified purchase, uncertified purchase, and any terms
or tie-breaking when their values tie.

An information-only ledger would be a different upstream model: the
certificate's signal persistence, current-capacity belief, buyer payoff,
timing, and transition would all have to be rederived. The guaranteed-service
inequality cannot simply be imported into that branch.

### 3.2 Positive-stock trade support

Technological consumption is not enough: the buyer must choose the certified
seller in a positive-stock state. The guaranteed payoff makes certified trade
strictly preferable to exit and to costly inspection, but selection against an
uncertified purchase still requires the common-state belief/terms and the
fixed tie-breaking rule. Those objects are proposed but not specified. Thus
the evidence supports inspection dominance, but not a complete positive-stock
certified-trade witness for every relevant state. A zero-certificate search
observation cannot fill this gap because there is then no certificate to trade
against or consume.

### 3.3 State and transition closure

A closed ledger must separately encode: issuance after a private high draw;
the public number and identity of carried certificates; beliefs about each
uncertified seller; selection and trade in positive-stock states; mechanical
consumption only after certified trade; the fresh draw/re-certification timing;
and search/purchase behavior in zero-stock states. The committed objects give
a verbal carry/consume/fresh-draw order but no state law or transition
probabilities that connect seller choices, buyer choices, certificate stock,
and the later uncertified composition. The audit correctly refuses closure,
but its generic missing-ledger diagnosis does not identify these distinct
links.

### 3.4 Causal attribution

With guaranteed service, inspection can occur only in a zero-certificate
state. A change in `k` may still change aggregate `S(k)` by changing the
stationary weight placed on zero-stock states, or by changing beliefs within a
zero-stock state. That is not by itself a same-state positive-stock inspection
response, and it is not yet a closed depletion feedback. A closed feedback
would need supported certified purchase, resulting consumption, subsequent
issuance/composition dynamics, and a later state-contingent buyer response.
The audit avoids an affirmative claim but never tells the reader whether only
one-way reweighting remains.

### 3.5 Benchmark meaning

- **Full model:** seller and buyer behavior, transitions, beliefs, and the
  stationary distribution are re-solved at each `k`; this is the target, not a
  control.
- **Policy-frozen accounting:** both policies and the reference stationary
  distribution are fixed at `k0`; only seller certification expense changes.
  Therefore `S`, `A`, and buyer surplus are constant by construction. This is
  stronger than fixing a pointwise rule alone, but it is only an accounting
  boundary and cannot witness a mechanism.
- **One-buyer expiry:** the model is re-solved after all unused certificates
  are forced to expire. This changes persistence, the transition kernel, the
  state distribution, and potentially behavior. It is a bundled removal of
  cross-buyer carryover, not a pure control for the mechanical act of
  consumption after trade.
- **Inspection disabled:** setting `c = 2` changes a primitive and removes
  inspection as an effective action, while seller behavior and the certificate
  stock remain endogenous after re-solution. Differences relative to the full
  model identify dependence on the inspection institution only conditionally;
  they are not a held-stock causal effect.

## 4. Committed upstream quality

Canonical commitment proves only that a transaction passed the mechanical
route checks. All four current research objects remain `agent_proposed`
(`evidence/canonical/status.md`, **Current entities**) and no human G1 decision
exists.

| Object | Mechanical validity | Economic-interpretation validity | Coherence | Distinctiveness | Readability | Required expert editing |
|---|---|---|---|---|---|---|
| **ResearchQuestion** (`evidence/canonical/frame.transaction.json`, `$.operations[0].entity`) | Accepted and canonical in the frame transaction; the exact three-cost inequality and kill condition are typed. | **Material defect.** It provisionally locks a certified high opportunity across buyers, which implies visible-certificate inspection dominance, while its `phenomenon` says stock composition therefore changes the private return to inspection. The claimed link is not derived. | The question, outcomes, and no-direction boundary fit together, but the intended active search channel conflicts with the guaranteed-service branch. | The consumable public-information-stock puzzle is potentially distinctive; no mechanism contribution or literature novelty is established. | Precise but overly dense; the long `object_to_explain`, scope, and kill condition combine model choice, estimand, and attribution. | **Major.** Choose the certificate ledger, expose the payoff envelope, and either kill/narrow positive-stock search or redesign the upstream model honestly. |
| **BenchmarkSet** (`evidence/canonical/frame.transaction.json`, `$.operations[1].entity`) | Accepted and canonical; four environments have explicit primitives, timing, solution concepts, and predictions. | The frozen accounting benchmark is well defined. The expiry benchmark removes a broad persistence institution, not depletion alone; the `c=2` benchmark reoptimizes a different economy. Neither repairs the missing positive-stock payoff/trade witness. | Mostly aligned with the ResearchQuestion, but the promised three-way attribution is stronger than the supplied state/action closure permits. | A useful diagnostic ledger, not yet a distinctive mechanism design. | Long but comparatively clear; row-by-row labels help. | **Major.** Correct the attribution language, state what each row changes and reoptimizes, and align every row with the selected certificate ledger. |
| **PrimitiveGraph** (`evidence/canonical/decompose.transaction.json`, `$.operations[1].entity`) | Accepted and canonical after repair. Nodes and edges are schema-valid. | **Insufficient.** It lacks public-state/payoff/deviation objects, seller certification alternatives, beliefs, certified-seller selection, and a closed transition law. `pool_to_buyer_choice` states relevance, not an active response; `timing_to_pool` states an accounting relation, not a solved law. | The arrows retell the intended narrative but skip the very links required to make it causal. | No established distinctive mechanism; the graph is a proposal map. | Node labels are readable, but broad nodes such as `service_payoff_technology` hide the operative inequalities. | **Major/H4.** Add or rewrite exact economic nodes and links after the ledger choice; do not merely add decorative arrows. |
| **Proposal-only GateDossier** (`evidence/canonical/decompose.transaction.json`, `$.operations[0].entity`) | Accepted and canonical after correcting enum literals and including the PrimitiveGraph in `ordered_object_refs`. `proposed_action = park`; it does not confirm G1. | Appropriately cautious about scope and selection, but it records importance and benchmark separation as supplied evidence without surfacing the certificate-dominance contradiction. | Coherent as a governance wrapper around the committed objects, not as proof that those objects are research-ready. | No independent distinctiveness or novelty evidence. | Clear about authority, but form-heavy and less useful than an economist-facing branch decision. | **Substantial after upstream repair.** Replace generic requirements with the guaranteed/information-only branch choice, payoff test, transition test, and branch-specific kill condition. |

## 5. Audit-attempt diagnosis

### 5.1 Unsupported `semantic_level` literal

`evidence/audit/attempt1.response.json`, `$.diagnostics[0].message`, rejects
`policy_rule` at
`evidence/audit/attempt1.candidate.json`,
`$.operations[0].entity.facets.economic_interpretation.payload.benchmark_assessments[1].held_fixed[0].semantic_level`.
The diagnostic supplies the exact path and allowed literals. Attempt 2 changes
only that leaf from `policy_rule` to `behavioral_response` at the same path.

**Diagnosis:** a mechanical model-to-schema mapping error, not a demonstrated
validator false positive. Calling the object a frozen policy is economically
reasonable, but the candidate put a fixing concept into a field whose enum
describes semantic object level; `fixing_level = policy_rule` was already
available. The repair is schema-compliant in spirit, though
`behavioral_response` is a less exact name for a policy rule.

### 5.2 Fixed/movable semantic conflict

`evidence/audit/attempt2.response.json`, `$.diagnostics[0].message`, reports
that one PrimitiveGraph object is held fixed and movable at the same semantic
level. In the mechanical benchmark, attempt 2 places
`stationary_certificate_pool`/`stationary_distribution` both in
`...benchmark_assessments[1].held_fixed[1]` and in
`...benchmark_assessments[1].still_endogenous[0]`; the latter's own label says
it is a fixed evaluation input and not reoptimized.

Attempt 3 repairs three leaves under
`$.operations[0].entity.facets.economic_interpretation.payload.benchmark_assessments[1].still_endogenous[0]`:

- `label`: from “stock object carried as a fixed evaluation input, not
  reoptimized” to “seller expense ledger changes mechanically while the policy
  and state weighting remain frozen”;
- `semantic_level`: from `stationary_distribution` to `payoff_ledger`;
- `primitive_node_id`: from `stationary_certificate_pool` to
  `service_payoff_technology`.

**Diagnosis:** the attempt-2 candidate is substantively inconsistent at those
fields; the validator's conflict is economically plausible. The diagnostic
surface is nevertheless insufficient because it gives no benchmark id,
object id, or JSON paths. Moreover, attempt 3 moves the changed expense ledger
into `still_endogenous`, although this benchmark has no endogenous
reoptimization; an empty `still_endogenous` list would be the economically
cleaner representation if the contract permits it.

### 5.3 Channel endpoint mismatch

`evidence/audit/attempt3.response.json`, `$.diagnostics[0].message`, rejects
the final repair because channel endpoints do not match changed and target
objects. No further candidate was allowed. The preceding repair did not alter
any `channel_path`. A visible mismatch exists in the mechanical row:
`...benchmark_assessments[1].changed[0].primitive_node_id` is
`certification_cost_perturbation`, its target nodes are the three buyer outcomes
at `...targets[*].primitive_node_id`, but `...channel_path` ends at
`stationary_certificate_pool`. In the inspection-disabled row, changed objects
map to `buyer_action_choice` at `...benchmark_assessments[3].changed[*]`, while
its path begins at `certificate_timing_depletion`.

**Diagnosis:** there is enough visible evidence for a candidate mapping error,
so a false positive is not the leading explanation. But the error surface is
again insufficient: it identifies neither the failing benchmark nor the
expected start/end ids, and the absent authoring contract prevents a decision
about whether a `diagnostic_only` or `boundary_or_mapping` row may use a
representative truncated path. The claim that the validator is overconstrained
is therefore **inconclusive**, not established.

### 5.4 Earlier decomposition repairs

For completeness, the decomposition route also had two mechanical repairs.
`evidence/decompose/attempt1.response.json` rejected `gate_kind = G1` and a
free-text `proposed_action`; attempt 2 changed the exact authority-payload
paths to `G1_question_benchmark` and `park`. Attempt 2 then omitted a required
primitive object; attempt 3 added
`primitive_graph_decompose_primitives@1` to
`$.operations[0].entity.facets.authority.payload.ordered_object_refs[2]` and
committed. These are authoring/mapping errors; the first diagnostic is
path-specific, while the second is materially less actionable.

## 6. Root-cause classification

**Primary cause: model-content/mapping error — confidence 0.80.** The economic
output misses the guaranteed-service dominance implication, and the typed audit
candidate contains visible category and endpoint inconsistencies. These facts
do not depend on hidden source or tests.

**Secondary cause: diagnostic/authoring-surface ambiguity — confidence 0.70.**
The latter two audit diagnostics omit benchmark ids, object ids, JSON paths,
and expected endpoint values. The repair sequence shows the author moving an
object from a fixed distribution to a supposedly endogenous payoff ledger
without resolving the underlying category question. Because the authoring
contract is absent, no claim is made that the hidden WorkPacket itself was
incomplete.

**Validator false positive or overconstraint: not established — confidence
0.35 that it contributed.** The final error could be overstrict for a negative,
unwitnessed diagnostic row, but the visible paths also fail ordinary endpoint
semantics. The evidence is mixed and insufficient to assign primary blame to
the validator.

The smallest evidence that could falsify this classification is the omitted
audit candidate-authoring contract together with a path-level validator trace
for attempt 3. If that contract explicitly permits the supplied negative-row
paths and a replay shows that the unchanged candidate should validate, the
primary mechanical cause would shift to validator defect/overconstraint. If it
instead gives the required endpoint/category mapping and attempt 3 violates
it, the present classification is strengthened. Separately, an explicit
upstream information-only certificate ledger with supported current beliefs
and payoffs would falsify the guaranteed-service dominance reading; no such
object is in the frozen package.

## 7. Disposition

The categories are independent; none compensates for another.

- **M (machine): mixed, with two upstream commits and an audit failure.**
  `frame.question_and_benchmarks` committed at
  `73fb8d5bc47f3c21d17228e76edb8300fbc537224bf896f2ebe01a52f57adf1c`;
  `decompose.primitives` committed at
  `467a15616763fc5859ca7128893b187599a5e813d1dde8b5b5e968c3d2d60535`.
  All three audit completion attempts were rejected. The finish response
  recorded `failed_no_effect`, created no audit transaction, and left the head
  unchanged (`evidence/audit/finish.response.json`, `$.completion`). The V8
  unwitnessed-negative M-PASS condition was exercised and failed because the
  audit bundle and replacement dossier were not canonically committed.
- **A: A-FAIL.** Scores are `0, 1, 1, 2, 2`; item 1's zero triggers the frozen
  rule exactly.
- **O: REVISE.** The broad research puzzle remains viable, but the current
  positive-stock inspection/depletion story is not. `READY` is prohibited.
  Under the committed guaranteed-service ledger, the active positive-stock
  inspection branch should be killed or narrowed; an information-only branch
  would require an honest upstream remodel.
- **R/H: R-FAIL; H4.** The reader recovers a generic missing margin and a
  PrimitiveGraph repair target, but not the certificate guarantee, visible-
  state payoff comparison, zero-stock limitation, or feedback/reweighting
  distinction.

No human G1 decision has been made or may be inferred.

## 8. Minimal next action

The smallest upstream scientific action is a branch decision followed by a
ledger rewrite; no result solving is yet warranted.

1. **Choose and state the operative certificate ledger in the
   ResearchQuestion.**
   - If the certified high opportunity is guaranteed while carried, write the
     public-state buyer payoff envelope explicitly and record that inspection
     is dominated whenever a certificate is visible. Kill the positive-stock
     search margin, and narrow the question to zero-stock reweighting,
     allocation, or surplus only if those channels can be stated without
     overclaiming depletion.
   - If the certificate is information-only, rewrite its signal content,
     capacity-redraw timing, beliefs, certified and uncertified payoffs, and
     transition law. Do not import the guaranteed-service inequality.
   - If positive-stock inspection is essential, a price, match value,
     congestion, rationing, or comparable supported buyer-facing force must be
     added upstream by an authorized scientific choice. It cannot be smuggled
     into the audit or represented as an engine repair.
2. **Repair the PrimitiveGraph economically.** Add exact public states,
   buyer payoff/deviation comparisons, seller certification alternatives,
   certified-seller selection, the action-to-consumption link, fresh draw and
   issuance timing, and the stock/composition law. Label separately
   positive-stock trade, mechanical depletion, and zero-stock inspection.
3. **Tighten the BenchmarkSet.** Keep the frozen accounting row's policies and
   distribution fixed with no `still_endogenous` object; describe expiry as a
   broad carryover/transition intervention; and state that the `c=2` economy is
   re-solved with endogenous stock. Any claimed channel path must run from an
   actually changed object to the stated target, or be explicitly absent when
   the contract permits only a negative diagnosis.
4. **Replace the GateDossier and memo only after those edits.** The new memo
   must expose the certificate guarantee, the visible-state action comparison,
   the exact failed link, the reweighting-versus-feedback status, and the next
   branch choice. It must remain proposal-only and `REVISE` unless a later
   human decision says otherwise.

The only engine change justified by the frozen evidence is a **diagnostic
surface improvement**: for fixed/endogenous and endpoint failures, report the
benchmark id, object id, exact JSON paths, conflicting values, and expected
endpoint set. The evidence does **not** justify relaxing the validator, adding
`policy_rule` to the semantic-level enum, or adding a scientific primitive.

**Another same-case generator run is warranted before any held-out run.** It
should occur only after the upstream economics edits (and, if adopted, the
path-aware diagnostic improvement). The same case should demonstrate a
canonical audit bundle and replacement dossier plus a memo that passes the
five reader probes. A held-out run before that would confound unresolved
economics with the authoring/validator sequence.

## Decision table

| finding | evidence | confidence | authorized next step | prohibited inference |
|---|---|---:|---|---|
| Package integrity passed | 35/35 hashes and byte counts; manifest digest matched; no extras | 1.00 | Use this frozen package as the sole evaluation record | No inference about omitted files or backend identity |
| Guaranteed-service branch implies visible-state inspection dominance | Canonical frame RQ scope and full benchmark payoff/timing paths | 0.95 | Make the payoff envelope explicit; kill/narrow or honestly change ledger | No positive-stock search claim from composition alone |
| State/transition and causal attribution remain open | Audit attempt 3 causal chain, benchmark rows, and disclosed gaps | 0.90 | Close positive trade, consumption, issuance, stock, belief, and later-action links | No depletion claim from a zero-stock search witness |
| Benchmark ledger is useful but conditional | Canonical four-row BenchmarkSet and audit row assessments | 0.85 | Correct expiry and reoptimization meanings | No “pure depletion” or selector-robustness claim |
| Audit rejection sequence is led by mapping errors with weak diagnostics | Three audit responses and exact attempt-to-attempt leaf changes | 0.80 | Improve candidate mapping and path-level diagnostics | No demonstrated validator false positive |
| Machine run is only partially successful | Two canonical upstream transactions; no audit transaction; recorded failure | 1.00 | Rerun the same case after upstream repair | No M-PASS for the audit and no G1 confirmation |
| Economics disposition is A-FAIL / REVISE | Rubric `0,1,1,2,2` | 0.95 | Perform the minimum upstream branch and ledger edits | No readiness, result, welfare, proof, or novelty claim |
| Reader burden is R-FAIL / H4 | Frozen memo and retell §§2--7 against five probes | 0.90 | Rewrite the memo only after the model branch is repaired | Do not treat an accurate report of omissions as probe recovery |
