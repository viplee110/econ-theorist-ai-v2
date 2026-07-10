# V1 capability migration ledger

Status: Architecture v0.1

V1 baseline: `viplee110/econ-theorist-ai` at `cc5f61254bb79e7436892e32ec88730ae14dd7f8`

## 1. Migration rule

V2 is an architecture rewrite and a capability migration. It does not copy v1's file topology or discard the research knowledge accumulated through repeated upgrades.

Every high-value v1 capability must receive:

1. a stable capability identifier;
2. its v1 evidence path and baseline revision;
3. a v2 owner;
4. one of five dispositions;
5. an observable parity or replacement test;
6. a recorded migration status.

The dispositions are:

- **preserve:** retain the principle and behavior with minimal semantic change;
- **refactor:** retain the scientific value through a different representation or control flow;
- **optional:** load only when risk or user choice warrants it;
- **fixture:** retain as historical evidence or a regression case, not as runtime guidance;
- **retire:** remove deliberately, with a stated reason and replacement if needed.

No capability is considered migrated merely because its wording appears in a prompt.

## 2. Capability ledger

All rows below have Architecture v0.1 migration status `mapped_design`: a v2 owner and parity test are specified, but no capability is yet `implemented` or `parity_verified`. Implementation must advance status explicitly rather than treating this design table as proof of migration.

| ID | V1 evidence | Valuable capability | Disposition | V2 owner | Parity or replacement test |
|---|---|---|---|---|---|
| `V1-TASTE` | `AGENTS.md`, “Scientific Taste & Anti-Complexity”; `ECONOMETRICA_PANEL_PROTOCOL.md`, Nugget/Occam tests | Detect defensive complexity, weak nuggets, ornamental generality, and technique-first modeling | Refactor | Architecture constitution plus theory-kernel validators | A deliberately ornate but absorbed model is rejected or simplified even when formally correct |
| `V1-RESULT-HYGIENE` | `AGENTS.md` result-statement rules; latest v1 commit | Keep formal statements minimal and move interpretation, caveats, and proof intuition to appropriate prose | Preserve | Claim schema and manuscript result-block contract | A bloated proposition is separated into truth-critical conditions, exact statement, interpretation, boundary, and proof roadmap without scope drift |
| `V1-HUMAN-GATES` | `AGENTS.md` Human Gates; `ECONOMETRICA_AI_HUMAN_WORKFLOW.md` Human Decision Persistence | Human ownership of structural choices, append-only reversals, consequences, and rechecks | Refactor | Typed `Decision` entities, immutable events, authority levels, dependency invalidation | Reverse an accepted primitive: the old decision remains, a superseding decision is added, and dependent results/prose become stale |
| `V1-PROVISIONAL-AUTO` | Orchestrator guarded full-auto mode; `auto_decisions.md` and ratification design | Permit autonomous exploration without falsely recording human confirmation | Preserve | Provisional branches and promotion boundaries | An agent can complete a reversible exploration, but cannot promote its central result or release a manuscript without the required authority |
| `V1-EVIDENCE-LEDGER` | Discovery D3; `literature_evidence_ledger.md` | Separate source facts, AI inferences, access status, closest papers, anchors, and absorption threats | Refactor | `LiteratureEvidence` and `ClosestTheoryMap` | Every novelty or absorption claim resolves to verified literature evidence or is visibly provisional |
| `V1-FIELD-PROFILE` | `field_profile.md` protocols | Route literature and specialist criticism by the actual theoretical field and adjacent theory families | Refactor | Versioned field profile | Changing the field profile changes literature/referee contexts without invalidating formal proofs |
| `V1-TARGET-PROFILE` | `target_journal_profile.md`; “target changes calibration, not quality” | Separate quality floor from venue fit, reader breadth, and presentation calibration | Refactor | `TargetProfileRef` plus versioned `ResolvedProfileManifestRef` and soft venue overlays | A target change reopens authoring/review contracts but does not mark a theorem false or reduce the universal quality floor |
| `V1-ECON-LOGIC` | Discovery “Economic Logic Map Discipline”; `economic_logic_map.md` | Track phenomenon, tension, minimal example, prediction, sharpness, absorption threat, blocker, and next question | Refactor and strengthen | Canonical economic argument plus generated compact view | The system can answer the current economic question and next discriminating test from structured state without consulting competing dashboards |
| `V1-PRIMITIVE-HUNTER` | Discovery D4; `primitive_hunter_report.md` | Audit primitives, reduced-form objects, endogenization, and nonlocal mutations | Refactor | Primitive decomposition, mechanism hypotheses, and optional escape operators | The system distinguishes primitive, institutional constraint, derived object, normalization, and regularity; it does not demand endogenization when robustness to microfoundations is the contribution |
| `V1-NONCONVEX-SEARCH` | Discovery Nonconvex Branch Generation | Escape a local model/theorem optimum by changing primitive, timing, information, objective, solution concept, boundary, or representation | Optional | Risk-triggered discovery operators | After repeated local repair fails, the router proposes structurally different branches and preserves their provenance; it does not run a standing quota |
| `V1-MICRO-EXAMPLE` | Discovery D4.5; `micro_example_note.md`; model-craft funnel | Build theory from a hand-solved benchmark, minimal mechanism example, failure condition, and failed simpler alternatives | Preserve and strengthen | `PredictionRegister` and archetype-sensitive `ExampleSuite` | Required functional roles—benchmark, mechanism/constraint-on, ablation or relaxation, rival separation, and boundary/tightness/independence—are covered explicitly; applicable core cases are hand-solvable without the main theorem |
| `V1-MODEL-TOURNAMENT` | Discovery D4; `model_tournament.md`; lane-aware judge | Compare alternatives before committing to a canonical model | Refactor | Separate mechanism tournament and formal-implementation tournament | Formal tractability cannot make a mechanism win; implementation candidates are compared only after the mechanism question is fixed |
| `V1-HEURISTIC-DERIVATION` | Discovery D4.5–D5; `heuristic_derivation.md` | Replay the small example, derive from economic tradeoffs, expose assumptions, record failed derivations, and search counterexamples | Refactor | `FormalizationMap` and `ClaimGraph` | Each load-bearing mechanism arrow maps to a formal object or lemma, and failed predictions/derivations remain recorded |
| `V1-ABSORPTION` | Discovery D6; `absorption_tests.md`; name-swap and complexity-shield tests | Test whether known theory obtains the result under relabeling, extra assumptions, or defensive complexity | Preserve and strengthen | Closest-theory translation and absorption audit | Map agents, primitives, constraints, equilibrium concept, and results to the closest theory; identify the first mapping failure or mark the contribution absorbed/provisional |
| `V1-CONTRIBUTION-LOCK` | Human Workflow Stages 1–2; `contribution_lock.md` | Lock the question, central result, non-substitutable insight, and reader belief update before large manuscript investment | Refactor | G4 Result Investment Gate, `ClaimGraph`, `ResultPortfolio`, and argument spine | Promotion requires a non-substitutable nugget, allowed-claim envelope, boundary, proof status, economic consequence, reader update, and explicit invest/refine/pivot/park/kill decision |
| `V1-GENERALITY` | `generality_ledger.md` | Record assumption additions, domain restrictions, special cases, and theorem drift | Refactor | Generality frontier | The system compares result sharpness, naturalness, novelty, scope, tractability, and legibility rather than treating maximum generality as monotone progress |
| `V1-PRE-PAPER-NOTE` | Discovery D7; `pre_paper_model_note.md` | Require a short model/theorem package before drafting the full paper | Refactor | `ValidatedArgumentPackage` plus generated model-note view | Full authoring cannot be promoted until the central mechanism, claims, assumptions, boundaries, evidence, and proof obligations form a coherent package |
| `V1-CLAIM-EXTRACTION` | Verification V1 | Extract exact claims, quantifiers, assumptions, dependencies, and proof locations | Preserve | canonical `Claim` entities, derived `ClaimGraph`, and `ProofObligation` schema | A theorem's exact domain and dependency set can be reconstructed mechanically from its registered claim |
| `V1-ASSUMPTION-LEDGER` | Human Workflow Stage 3; Verification V1–V5; `assumption_ledger.md` | Track exact assumptions, economic meaning, proof use, naturalness, drift, and whether each condition is genuinely load-bearing | Refactor and strengthen | `AssumptionMap` | Each central assumption records formal/economic roles, primitive sufficient conditions or an explicit gap, satisfying environments, dependent claims/arrows, ablation evidence, violation witness, and result-versus-proof necessity |
| `V1-REDERIVATION` | Verification V2 | Re-derive from primitives instead of trusting manuscript algebra | Preserve | Verification routes | An independent verifier receives model/assumptions/claim but not the author's explanatory narrative and reports agreement or a precise gap |
| `V1-SYMBOLIC-NUMERIC` | Verification V3–V4 | Use exact algebra and numerical boundary/counterexample search without confusing corroboration with proof | Preserve | Verification adapters and evidence types | A planted finite-grid “proof” remains unverified; a discovered counterexample refutes or challenges the exact bound claim |
| `V1-PROOF-AUDIT` | Verification V5 | Classify proof gaps, hidden assumptions, direction errors, and unproved existence/uniqueness steps | Preserve | Proof obligations and verification records | Each proof obligation binds to exact revisions of the claim, assumptions, model, and solution concept |
| `V1-FORMAL-TRIAGE` | Verification V6–V7; `SimpleLemma.lean` | Apply formal proof selectively to compact, high-value lemmas | Optional | Formal-proof adapter | Lean or another prover is suggested only when formalization value exceeds translation cost; the smoke lemma remains a toolchain fixture |
| `V1-COUNTEREXAMPLE-HARNESS` | `verification_templates/counterexample_search.py` | Reproducible seeds, boundary search, and explicit “no counterexample is not proof” discipline | Refactor | Generic theory counterexample harness | Structured output records claim ID, admissible domain, seed, environment, witness, and evidence status |
| `V1-DYNAMIC-PANEL` | Panel Protocol dynamic configuration | Choose critics from field, contribution type, method, target reader, and live risk | Refactor | Targeted critic router | A low-risk local question receives one relevant critic; a high-stakes investment decision receives independent roles justified by specific risks |
| `V1-INFO-ISOLATION` | Panel Blind, Context, and Literature modes | Prevent later agents from inheriting author rationalizations or previous referee anchoring | Preserve | Route-specific context manifests | A blind reader's manifest proves it did not receive decisions, old reports, or hidden argument notes |
| `V1-LANE-JUDGE` | `agent_runs/`, `cross_agent_model_audit.md` | Isolated proposals, provenance, judge synthesis, and no direct canonical overwrite | Optional, high value | Multi-agent run substrate | Multiple lanes remain inspectable; correlated outputs are not counted as independent evidence; a judge proposes rather than confirms |
| `V1-ADVOCATE` | Panel Advocate/Best-Case Reader | Construct the strongest defensible case for why a question matters before killing it | Preserve as targeted critic | G1 Question and Benchmark Gate | A candidate cannot be killed solely by a hostile reading until its strongest evidence-bounded value case is represented |
| `V1-MANUSCRIPT-ARCH` | Human Workflow Stage 5.5; `manuscript_architecture_plan.md` | Give each section a job and choose the appendix boundary deliberately | Refactor and move earlier | Paper IR and section contracts | Every section has reader-before/after states, a closed question, allowed claims, formal objects, and an appendix decision |
| `V1-STYLE-ANCHORS` | Human Workflow Stage 6.5; style-anchor notes/matrix/plan | Learn exposition architecture from field- and genre-matched papers without copying prose | Refactor and move earlier | Theory craft library, voice charter, and reader model | The system retrieves functional moves with provenance and non-applicability conditions; text similarity is not an objective |
| `V1-WORKING-PREVIEW` | Working preview protocol | Give the human a readable provisional snapshot before all gates are final | Preserve | Preview route with visible provisional status | A preview may be read and edited but cannot silently confirm primitives, novelty, results, or target fit |
| `V1-REVIEW-REVISION` | Panel Review/Revision; revision tree | Separate defensive patching, mechanism simplification, and pivot/reframe | Refactor | Failure-sensitive revision router | A contribution objection reopens discovery/investment instead of triggering endless sentence polishing |
| `V1-EXTERNAL-REALITY` | Human Workflow Stage 9 | Break correlated AI author/reviewer/editor errors with expert feedback | Preserve | External reality-check gate and evaluation case ingestion | Expert feedback is linked to affected objects and creates proposed revisions without being overwritten by an AI consensus |
| `V1-LOW-TOKEN` | Orchestrator active-context and artifact-budget rules | Reduce reconstruction and top-level artifact proliferation | Refactor | Context compiler, thin state, and architecture-budget tests | Ordinary routes read bounded context; one generated status view replaces manually synchronized dashboards |
| `V1-VERSION-CONTROL` | `ECONOMETRICA_VERSION_CONTROL.md` | Protect dirty human work, inspect diffs, checkpoint, branch, and recover | Optional infrastructure | Version-control adapter and human-owned artifact conflict checks | A run based on an old hash cannot overwrite a human edit; both variants survive for merge |
| `V1-TOOLCHAIN` | `verify_toolchain.ps1`, `TOOLCHAIN_README.md` | Diagnose tool availability and never claim a check that did not execute | Refactor | Portable `doctor` command and verification provenance | Missing tools yield an honest unavailable status; successful checks record tool/version/output identity |
| `V1-RESEARCHER-MEMORY` | README optional cross-project memory | Retain methods, negative knowledge, proof techniques, and postmortems as priors | Optional and private | Local researcher-memory adapter | Project evidence and current human decisions override memory; an outside-view route can challenge the profile |
| `V1-EXAMPLES` | `examples/full_walkthrough_toy_project/`, model-base and kill/pivot examples | Demonstrate v1 artifact shapes and negative routing | Fixture | Migration and regression cases | Existing examples are never used as Top-5 prose anchors; model examples are replaced before claiming micro-example parity |
| `V1-LEGAL` | `LICENSE`, `NOTICE`, `CITATION.cff` | Apache-2.0 licensing and attribution | Preserve | Repository root metadata | License remains Apache-2.0; project/version metadata is updated without weakening notices |

## 3. Deliberate retirements

| V1 behavior | Decision | Reason or replacement |
|---|---|---|
| `ECONOMETRICA_*` architectural filenames | Retire | Venue calibration belongs in profiles, not system identity |
| Empirical/mixed orientations, identification objects, data and experiment referee paths | Retire from v2 core | V2 is theory-only; theoretical numerical work remains in verification |
| Fixed quotas such as 30–80 topics and 20–40 model skeletons | Retire | Search breadth should stop by disagreement, information value, coverage, and budget |
| A single 1–5 aggregate research score | Retire as a decision rule | Use non-compensatory floors and diagnostic vectors |
| “Deepest primitive is always best” | Retire | Purpose-fit reduced forms can express invariance or robustness |
| “The theorem sentence must appear verbatim throughout the paper” | Retire | Use entailment-consistent layered explanations |
| Default full referee board for ordinary tasks | Retire | Use the smallest targeted independent critique that addresses the live risk |
| Linear stage number as canonical project state | Retire | Maturity is derived from capabilities; focus is a route |
| Multiple hand-maintained Markdown truth sources | Retire | Typed snapshot, immutable events, dependency graph, and generated views replace them |
| Late style pass as the main intuition repair mechanism | Retire | Reader modeling and mechanism packets enter before drafting |
| Welfare as a universal requirement | Retire | Require welfare/incidence when economically relevant; pure theory requires an honest economic consequence or modeling implication |

## 4. Migration completion criteria

A capability changes from `planned` to `migrated` only when:

- its v2 owner exists;
- its relevant scenario or validator passes;
- its context and authority boundary are defined;
- it does not require a second competing source of truth;
- its v1 baseline behavior and intended v2 improvement are documented.

Architecture review may intentionally postpone optional adapters. It may not mark a core scientific discipline migrated solely because the implementation plan mentions it.
