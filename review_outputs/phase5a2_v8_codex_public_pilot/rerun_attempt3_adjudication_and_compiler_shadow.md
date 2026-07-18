# R3 adjudication and semantic-compiler shadow record

Status: **independent adjudication complete; `STRUCTURAL_TAX_PRIMARY` (0.86);
noncanonical compiler replay valid; no canonical audit or human gate recorded**

Date: 2026-07-19

## Evidence boundary

The independent task verified its frozen 42-file, 594,079-byte manifest and did
not use network access, subagents, source code, or unlisted inputs. Its locked
reports remain outside the repository and are identified here rather than
copied into the pilot record:

| Report | Bytes | SHA-256 |
| --- | ---: | --- |
| `phase1_scientific_adjudication.md` | 31,513 | `ab3e56eb3df62c7603faa2c2ecea160fd81f7f3d92e5a4d2f0cdc2a000a50f33` |
| `PHASE1_LOCK.json` | 214 | `864a72d497018855cd7ab5704d43672079937131206e1f10a194daac40c619d2` |
| `phase2_architecture_adjudication.md` | 29,188 | `bd6bc8d3d91ebef4b40425113f3c4ed026e91deca039e7c8076e0b4b0d78f77c` |
| `final_decision.md` | 8,406 | `43baf46a1f543947e2b67e9c77313843b2c3c7463908785673f0431344cdb2f8` |

Phase 1 was locked before the architecture material was opened. The reported
scientific result was machine failure, economics success on eight of ten
items, `REVISE`, no memo-based reader verdict, and provisional editing burden
H3. The economics diagnosis correctly recovered the guaranteed-service
dominance, positive-stock trade/depletion comparison, zero-state inspection,
reweighting-versus-feedback distinction, benchmarks, and exact gaps. It also
identified missing seller continuation payoffs, a complete zero-state payoff
ledger, and timing/selection detail; therefore this is not a research-quality
pass.

Phase 2 estimated mechanical structural work at 40--65 percent of the whole run
and 75--95 percent of the audit-repair stage. It found no evidence that the V8
negative-diagnosis acceptance rule was defective. The final classification was
`STRUCTURAL_TAX_PRIMARY`, confidence 0.86, with the prescribed next step being
a noncanonical semantic compiler and batch structural preflight rather than
V9, relaxed validation, or another same-case generation attempt.

## Locked R3 replay

The locked final candidate was 41,610 bytes, SHA-256
`569fde15a8e13c90eae55d6d63a4f41e4641a2773d0ccb7461e829963918f679`.
Its exact audit ready response was 131,698 bytes, SHA-256
`b82373b20535b9ac399ddb53d8efb6e974195dcd529feb11bcad0bc046ff8c19`.
The replay base remained canonical head
`5ef5dbda951645b41e3a900e740ac97c060fcbda483da0641dc7d9ced90bae83`.

The locked candidate exposed one bounded semantic representation conflict:
`endo_zero_response_full` declared `behavioral_response` while binding
`zero_state_response`, an `equilibrium_object` node. The buyer's actual choice
was already represented separately by `reopt_buyer_action_full` bound to the
choice node `buyer_action_set`; changing only the former semantic level to
`equilibrium_object` therefore preserves rather than invents the economics.
The fixed-policy/fixed-law accounting row remains `payoff_ledger` and is not
classified as an active margin.

The original candidate also required two mechanical derivations that should
not consume scientific repairs:

- a revise-framing replacement dossier records `risk_disclosed`, not
  `gap_disclosed`, for `g1.framing_quality`;
- the compiler instantiates four exact input-to-bundle `audits` relations and
  one bundle-to-dossier `governs` relation as whole-facet `hard` dependencies,
  including the authority-aware contract hash and the runtime bundle hash.

The new compiler performed those derivations in memory, resolved every channel
from changed and target objects plus declared waypoints, wrapped both output
entities, generated the five relations and exact route outcome, and submitted
the resulting `Transaction` only to the unchanged V8 candidate validator. The
result was:

```text
status: SHADOW_VALID
preflight issues: 0
compiled transaction/projected digest:
  82382b45acffc5573eb5beef1ac439ad722a0c85fafb5ad94951d042f592c275
projection delta: +2 entities, +5 relations, +1 route outcome
canonical writes: 0
human decisions: 0
```

The compiler digest differs from a hand-repaired candidate identity because
the compiler owns retry-stable wrapper and relation IDs. It is not a claim that
the original ordinary-model run exercised this compiler.

## Prototype boundary

The implementation lives in
`src/econ_theorist/framing_quality_authoring.py`. It is deliberately outside
the canonical payload, route registry, frozen instruction resources, and V8
validator. It accepts only a fresh audit under the exact V8 compiler-v2
authoring contract and base snapshot, fills absent exact input refs, rejects
mismatched refs, returns multiple location-specific channel/ledger issues, and
compiles a candidate `Transaction`. A continuation contract fails closed until
exact bundle supersession is implemented. It does not stage, commit, repair,
confirm G1, or change scientific content.

Focused verification covered:

- deterministic compilation of two entity wrappers, five template-exact hard
  relations, runtime hash, evidence refs, and route outcome;
- one preflight returning path, node-kind, and fixed/movable issues together;
- a fixed-policy/fixed-law diagnostic accounting row remaining outside active
  margin classification;
- the pre-existing V8 negative-diagnosis and structured force-path checks;
- the pre-existing exact runtime-hash materialization boundary.

## Next test

Do not create V9 and do not rerun R3 generation as if it were new blind
evidence. Freeze one held-out economic-theory framing case and run a paired
shadow comparison with the same ordinary model and scientific brief:

1. the existing free-form Transaction authoring surface;
2. the semantic draft plus compiler surface.

Compare first-pass structural validity, scientific diagnostics, model repairs,
authoring bytes/tokens, elapsed time, and human editing burden. Keep blinded
economics and reader scoring separate from machine validity. Only after that
paired result should the prototype be considered for bridge integration and a
canonical end-to-end run.
