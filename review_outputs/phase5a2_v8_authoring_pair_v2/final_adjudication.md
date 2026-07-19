# Final adjudication: V8 authoring pair v2

Status: **`NO_CLEAR_SURFACE_SIGNAL`**: no clear end-to-end feasibility winner,
despite a clear directional structural-burden signal. Root-cause
classification: **`STRUCTURAL_TAX_PRIMARY`**, with model JSON/file-output
discipline contributory and no evidence of a registry-V8 scientific-acceptance
defect.

Neither arm reached unchanged V8 validity within three attempts. Semantic V2
therefore remains blocked from public-bridge integration. At the same time,
Semantic V2 removed more than half of the final authored structure, preserved
the core economics, and produced the stronger cold-reader memo. The experiment
supports continuing deterministic compilation, not returning to full
Transaction authorship and not weakening V8.

## Evidence and isolation

- Engine commit: `a03d1025ac9c9bcaefcd112de3e8c63694b97c8f`
- Wheel SHA-256:
  `061d505a5e0afa21604a52d7d1b298c92d852c24ca8f63d4bc45122a22dab01f`
- PRE manifest SHA-256:
  `6af4a71cb19f1da11d38eb710fc1d68debb4403946dc4d46c541c450d18137a3`
- Transaction manifest SHA-256:
  `ff154517e8890ab4aa2d4a536df97edfbd324756a4c12ec9a95a8bdd7941c375`
- Semantic V2 manifest SHA-256:
  `4c5104cf8c601e7b445d1352ae76a19abcc163ebf4f28fa2f97ba6cce123c067`
- Frozen generated-artifact aggregate:
  `11ac8cec806dfa9b78faa03d911eeb06cceba73d1b866593462033d3dda244e6`
- Scientific adjudication SHA-256:
  `bb14113daa0882558372cc2380e20940cd8094dc964888d867f6623c6fbf5ee4`
- Semantic reader free-retell / probe SHA-256:
  `5e090c2e6c20b9f33a26c470518b7880994e07a0903833feb6e68907d5ae41ba` /
  `278e7e26dad05d4f9ae5f4705652368fbf816fcb16b9f90dcf1d18f06c9eac45`
- Transaction reader free-retell / probe SHA-256:
  `2d69640ba4046889110b5ad570bc03c1a0157f8c34d462939ed9b0c7e1862832` /
  `239234ca3bef34db57aa16e4517e1852541fa7c305697b13f204dace71626426`

Both generator arms used separate new tasks in the frozen order. The requested
model class was ordinary/medium; actual provider/backend identity was not
independently observable. The scientific adjudicator and two cold readers used
three later isolated tasks. Reader A/B identity remained hidden until the
scientific ratings, free retells, and probe responses were all hashed.

Every attempt preserved canonical head
`dde1542e2916cce2a2a0c76dfbd14b4ea0b715c451c014727403390b2fe66d68`,
made zero canonical writes, and confirmed zero human gates.

## Machine validity and repair burden

| Measure | Semantic V2 | Transaction |
| --- | ---: | ---: |
| First-attempt final validation | fail | fail |
| Validation within three attempts | fail | fail |
| Experimental repairs submitted | 2 | 2 |
| Engine-route repair equivalent | 0 | 1 |
| Eligible for route-burden comparison | no | no |
| Source bytes by attempt | 16,556 / 13,604 / 10,922 | 22,381 / 22,435 / 22,391 |
| Total source bytes | 41,082 | 67,207 |
| Frozen harness elapsed total | 49 ms | 82 ms |
| Canonical writes / human gates | 0 / 0 | 0 / 0 |

Semantic V2 attempt 1 reached compiler preflight but failed
`compiler.margin.decision_missing` and one independent payload-schema check.
Attempt 2 replaced one witness with two intents on the same causal step and was
rejected by the semantic schema. Attempt 3 restored one intent but contained
one extra final `}`, so strict JSON parsing correctly failed.

Transaction attempt 1 failed one runtime relation-template topology. Attempt 2
contained a valid JSON body prefixed by `Exit code`, `Wall time`, and `Output`
lines, so strict JSON parsing correctly failed. Attempt 3 removed that prefix
but retained the unresolved topology mismatch.

Neither arm reached the scientific validator. A machine failure in this pair
is therefore not evidence that the unchanged V8 scientific gate is too strict.
The repair-equivalent counts are harness annotations only: every attempt was
marked ineligible for engine-route burden comparison, so they do not establish
a public-route repair saving.

## Structural burden

| Final-source measure | Semantic V2 | Transaction | Semantic reduction |
| --- | ---: | ---: | ---: |
| Source bytes | 10,922 | 22,391 | 51.22% |
| JSON leaf fields | 210 | 454 | 53.74% |
| Transaction operations | 0 | 8 | 100% |
| Entity wrappers | 0 | 2 | 100% |
| Relation wrappers | 0 | 5 | 100% |
| Authored `semantic_hash` fields | 0 | 10 | 100% |

Across all three attempts, Semantic V2 reduced authored source bytes by 38.87%.
This is a genuine structural-burden signal. It is not a machine-validity signal
because neither arm passed.

The remaining V2 surface still makes the model author `force_id`, force source,
margin and target nodes, causal-step numbers and node IDs, benchmark channel
waypoints, `decision_force_id`, payoff-node disambiguators, consequence-step
bindings, payload graph declarations such as distinctive-mechanism edge IDs,
and public-state object IDs. Active-witness consequence edge paths remain
compiler-owned. The residual declarations caused the observed preflight
failure despite correct memo-level economics.

## Locked scientific adjudication

The anonymous mapping was revealed only after every rating and reader response
was frozen:

- Candidate/Reader A = Semantic V2.
- Candidate/Reader B = Transaction.

Both candidates received **`REVISE`**, not `KILL`. Both correctly state:

- fixed routine payoff `3 -> 1` and fixed accident probability `1/2`;
- strict reoptimization from routine at `L=0` to preventive at `L=4`;
- reoptimized accident probability `1/2 -> 0`;
- the active spine
  `liability_rule -> maintenance_payoff_basis -> maintenance_choice -> accident_probability`;
- no welfare, optimal-law, legal-feasibility, empirical, victim, enforcement-
  cost, heterogeneity, or novelty conclusion; and
- no human G1 approval.

Semantic V2 has three localized defects:

1. its fixed-action `channel_intent` incorrectly targets accident probability
   through maintenance choice instead of ending at the payoff basis;
2. its force labels `maintenance_payoff_basis` as the active margin even though
   the true decision margin is `maintenance_choice`; and
3. enforceability is implicit rather than explicitly held fixed.

Transaction has three localized defects:

1. the active benchmark says maintenance reoptimizes while also setting
   `pointwise_policy_fixed=true`;
2. its force likewise labels the payoff basis rather than maintenance choice as
   the margin; and
3. enforceability is implicit rather than explicitly held fixed.

These defects independently block a scientific `READY` disposition and expose
cross-field preflight gaps, although they did not cause the observed machine
rejections because neither arm reached V8. They are small enough to repair and
do not show weak economic reasoning or a need for V9.

## Isolated reader result

Both readers met the frozen key's basic recovery requirements. Semantic V2
additionally achieved full detailed recovery in both the free retell and common
probes. Its reader recovered the question, both benchmarks, fixed payoff `3 -> 1`, the
strict `3 > 2` and `2 > 1` choice comparisons, preventive payoff 2, accident
risk `1/2 -> 0`, the exact active decision margin, the distinction between
payoff evidence and behavior, and the scope boundary.

Transaction achieved strong but partial detailed recovery. Its reader recovered the
question, both benchmarks, fixed payoff and risk, strict maintenance switch,
active margin, and causal consequence. The reader correctly reported that the
memo did not state preventive payoff 2 and could not recover the same detailed
claim boundary from the memo alone.

Semantic V2 is therefore **not reader-degraded and is directionally better**
on this held-out case. This does not compensate for its machine failure.

## Locked source attribution

Source inspection occurred only after the scientific and reader locks.

### Transaction

The final governs relation had the correct source, target, relation type,
facets, dependency mode, and explicit runtime upstream hash placeholder. It
also added `semantic_hash: null` to the non-semantic `downstream` facet ref.
The exact contract permits no such downstream field, so the topology matcher
correctly found zero matches.

The receipt exposed only an operation-level message that template
`framing.governs.replacement_g1_dossier` matched zero topologies. It supplied no
JSON pointer, expected/observed topology, or near-match field difference. The
model consequently changed the relation ID, which the topology matcher does
not use, and exhausted the repair budget without seeing the actual extra
field. This is structural authoring and diagnostic tax, not economics.

### Semantic V2

The V2 compiler searches each named force's `margin_node_id` for a unique
PrimitiveGraph node of kind `choice` on the declared causal step. The candidate
instead supplied `maintenance_payoff_basis`, whose kind is payoff technology.
The compiler correctly refused to materialize a choice witness.

The receipt reported `expected:null`, `observed:null`, and `options:[]`. It did
not expose the observed node kind or the unique choice node
`maintenance_choice` already present on the causal step. The model responded by
adding a second intent for the same step rather than correcting the force
binding.

More importantly, the task prompt says exact graph bindings are compiler-owned
while the semantic payload still requires model-authored force node bindings,
channel waypoints, causal node IDs, force selection, payoff disambiguators, and
public-state object IDs. The private oracle uses
`margin_node_id=maintenance_choice` and
`target_node_id=accident_probability`; the generator never received that
evaluator-only answer. The observed failure is therefore direct evidence that
V2 has not yet moved enough deterministic graph structure out of the model
surface.

## Final decision

- `INVALID_SETUP`: **no**.
- Semantic V2 unchanged-V8 validity within three attempts: **no**.
- Established material scientific degradation relative to Transaction:
  **no**; the anonymous adjudication did not rank the two, both require local
  revision, and neither has a material numerical or claim-boundary failure.
- Reader degradation: **no**; Semantic V2 is better on the frozen reader task.
- Structural reduction: **yes**, large and directionally useful.
- Public-bridge integration now: **blocked**.
- V9 or weaker acceptance semantics: **not justified**.
- Final pair class: **`NO_CLEAR_SURFACE_SIGNAL`**, with
  **`STRUCTURAL_TAX_PRIMARY`** diagnosis.

## Next bounded implementation

Do not rerun this case and do not begin another blind pair yet.

1. Preserve every registry-V8 scientific acceptance rule.
2. Make Transaction topology diagnostics report the closest relation, exact
   JSON pointer, and expected/observed extra or missing fields; the present
   governs failure should identify
   `operations/<index>/relation/downstream/semantic_hash` directly.
3. Reduce the semantic surface rather than merely expanding its prose prompt.
   The compiler should own deterministic force/channel graph bindings whenever
   the PrimitiveGraph and declared scientific intent identify one unique path.
   It must still fail closed on ambiguity and must not invent payoffs, actions,
   inequalities, activity, consequences, or scope claims.
4. When a semantic binding is invalid, expose the observed node and kind plus
   all compatible choice-node options on the causal step. Batch independent
   payload and binding errors in one receipt where possible.
5. Add deterministic cross-field preflight for the locked scientific defects:
   reject a fixed/boundary channel that traverses a held-fixed decision and
   ends at the outcome, an active row that both reoptimizes a decision and sets
   `pointwise_policy_fixed=true`, and a witnessed force whose margin node is not
   the exact choice node. Align future briefs and evaluator keys explicitly on
   held-fixed primitives such as enforceability.
6. Keep strict JSON parsing. Improve the host/file-writing path so command
   summaries or extra braces cannot be mixed into the candidate; do not accept
   prose-wrapped or ambiguously repaired JSON as canonical evidence.
7. Add focused diagnostic/compiler tests and rerun only the affected focused
   suite, schema exporter, and `git diff --check` for this noncanonical slice.
8. Only after the private oracle and adversarial diagnostics pass should one
   final fresh held-out ordinary-model pair be prepared. Public integration is
   justified only if Semantic reaches unchanged V8 validity without worse
   economics or reader recovery.

No merge to `main` should be based on this pair alone. The current audit branch
remains the appropriate location for the bounded authoring/diagnostic repair.
