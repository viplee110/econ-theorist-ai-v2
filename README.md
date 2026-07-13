# Econ Theorist AI v2

Econ Theorist AI v2 is a research operating system for developing frontier-level **economic theory** papers with human–AI collaboration.

The project is designed for pure and applied theory. It does not provide econometric, identification, estimation, data, or empirical-paper workflows. Symbolic computation, numerical examples, simulation, and formal tools are allowed only when they help discover, falsify, or verify theoretical claims.

## Current status

The repository contains **Architecture v0.1** and accepted **Phase 1--4 implementations on `main`**. Phase 4 implementation `63d3393` was merged by `89d2152` after its uninterrupted full-genesis acceptance run and independent adversarial review found no blocking findings. The **Phase 5A.0** design slice has now completed independent adversarial review on `agent/phase5a-host-bootstrap-contract`; it freezes safe natural-language onboarding and thin Codex, Claude Code, and Cursor host-adapter semantics, but implements no Phase 5A runtime capability. Phase 1 is a local, provider-neutral scientific state kernel: it initializes a theory project, preserves immutable transactions and Decisions, compiles bounded route contexts, commits under an exclusive lock, derives facet-level staleness, protects human-owned files, renders noncanonical views, and recovers from interrupted commits. Its acceptance suite includes real two-process head races, abrupt subprocess exits on both sides of the atomic-head boundary, adversarial authority/privacy tests, and Windows junction/reparse checks.

Frozen registry v2 contains 19 routes: 16 are enabled (13 theory routes, dependency repair, and two sealed blind-evaluation routes), while its three authoring placeholders remain `not_implemented`. Registry v3 adds ten native assurance, authoring, cold-reader, closure, and effort routes without changing historical v1/v2 meanings. Each native route validates the exact input IDs, revisions, and lineage in its immutable run focus; satisfying only entity types and counts is insufficient, and a same-type foreign Paper IR, contract, probe, review, or assurance object fails closed. For assurance, the VAP is the authority root: its internal ClaimGraph, FormalModel, AssumptionMap, and VerificationBundle refs must match exactly; every verified obligation/record pair must belong to that bundle and have exactly one same-package re-derivation. The provider-visible selected refs and blind packet are a separate projection and may exclude the VAP even though the immutable focus retains its authority binding. The real Phase 3 gold chain extends the accepted Phase 2 ObjectStore history through three obligation-scoped blind re-derivations, a multi-record assurance bundle, Paper IR and reader contracts, and an actual manuscript artifact. Its first manuscript fails the economic-reader and cold-reader transfer gates, receives a typed `RevisionBrief`, is superseded by the same canonical writer, and reaches `authoring_ready` only after fresh formal, economic, and cold-reader reviews pass.

Phase 3 validation reads and binds the immutable artifact bytes themselves--including re-derivation transcripts, proof-audit and harness records, manuscript text, and the separately sealed probe, answer key, and response--rather than trusting payload-declared hashes. Every non-whitespace manuscript-body character must belong to a typed prose span, and economic-reader and cold-reader coverage closes separately for every `ResultPacket`. `authoring_ready` requires the entire exact dependency chain to remain current and fresh, not merely the terminal review records. The writer cannot see cold probes or keys, the respondent cannot see the key, and append-only human-effort telemetry records active intervention separately from unattended compute. The comprehensive gold suffix currently has a noticeable replay and validation cost; reducing that cost without weakening byte, lineage, or isolation checks is a later optimization item.

The local `submission` compiler is implemented, but it is intentionally narrow: it may promote an exact current authoring-ready working unit only with the governing human Decision and may change formatting and span offsets, never wording, typed meaning, or scientific scope. It does not execute an external submission. Phase 3 also binds a harness's exact executable predicate and receipt to a declared obligation, but cannot by itself prove that the predicate is semantically equivalent to the obligation's natural-language meaning.

Phase 4 hardens that boundary with an additive `registry.v4.json` and exactly eight native routes: obligation mapping and audit, profile resolution, reader-problem diagnosis, function-first craft retrieval, profiled composition, independent craft-realization review, and profile/craft closure. All Phase 4 payloads live in an independent `profile_craft` namespace; copied v1--v3 routes retain their historical route versions, instructions, validators, and replay meanings. A `TargetProfile` pins the exact current Phase 3 package, Paper IR, reader path, and base profile manifest as well as effective human Decisions; a changed or foreign dependency fails freshness and invalidates its Phase 4 descendants. The pinned seed profile catalog and craft corpus are packaged policy resources rather than project entities. The corpus contains internal functional cards, not source prose, and the profiled writer receives selected functions and four typed project-semantic source fields without anchor identities, passages, or hidden reader material. These access and voice controls reduce leakage and imitation risk; they are not copyright or legal proof.

The operational checkpoint continues the real Phase 3 ObjectStore chain through actual immutable transactions, route validation, review closure, staleness, and replay. Its finite counterexample receipt is exactly rerun, decomposed with JSON Pointer clause locators, and exercised with a typed domain witness and five mandatory downgrade controls. Empty domain, constant true, conclusion flip, and domain narrowing are executable recomputations. Because the bare finite-scan predicate has no assumption component, omitted assumption instead retains the same predicate bytes and is recorded as a typed unexecutable control; it forces an explicit limitation and prohibits exact approval rather than being claimed as an executed or killed mutant. An `approved_partial` mapping must preserve every typed limitation downstream and project it into closure; neither mapper, auditor, resolver, nor closure may upgrade it to exact theorem evidence.

After human-confirmed L2 target Decisions resolve a profile stack, a post-manuscript diagnosis must bind the exact blocked `ReviewClosure`, exact `RevisionBrief`, every blocking instruction and finding, affected section roles, and four non-interchangeable semantic source selectors. Only a typed local-exposition failure is craft-eligible. Retrieval recomputes a deterministic **minimum-cardinality set cover v2**, with a stable lexical tie break, over the exact revision requirements; the seed release contains one functional move with exact extractors for `mechanism_explanation` and `comparative_statics_threshold`, not broad archetype or craft coverage. Profile precedence is non-blending: the universal floor is absolute, otherwise the highest applicable layer wins, and a conflicting equal-precedence pair fails resolution. Independent assessment then checks each revision requirement's assertion, section, and ordered Phase 4 realization-source binding, every active directive's observable acceptance criterion, and the target reader's benchmark, mechanism, boundary, and nearby-case recovery before closure may pass. These Phase 4 source bindings live in `CraftMoveRealization`; they do not broaden the frozen Phase 3 `ConsequentialSpan.source_fields`, which remains reserved for exact Phase 3 scientific projection sources.

This checkpoint uses a deterministic writer fixture: it validates orchestration and scientific-state protocol, but it does not call an external LLM, generate a complete paper autonomously, or demonstrate paper quality, Top-5 performance, legal compliance, or reduced human effort. Current acceptance evidence comprises an independent final adversarial branch review with no blocking findings; 82/82 focused Phase 4 non-gold checks; the complete non-gold suite with 403 tests passing and five skips; an uninterrupted full-genesis Phase 1→4 gold test passing in 6156.901 seconds; all five exporter checks; `doctor` with `required_ok=true`; registry v4 with 34 routes and hash `d81276ed9b7482768840ef89980d6cbb81361ca2ff84acee3ab7da7bb67eae7e`; compilation of 98 Python files; and `git diff --check`.

The uninterrupted final-code gold run is the primary end-to-end acceptance evidence. The earlier fresh segmented real-ObjectStore continuation remains additional historical-integrity evidence: it ran from frozen Phase 3 head `dfb04a...` through run 52, and independent verification at head `88b656...` found 87 entities, all 67 historical entities byte-identical, all 182 historical transaction/artifact/provenance files unchanged, `replay_at(final.head) == replay(final)`, exactly one current ready `ProfileCraftClosure`, and diagnostic coverage with all eight typed limitations preserved. The 6156.901-second runtime still identifies full-history replay as a performance target; it is no longer an uncompleted acceptance command. The internal phrase and voice checks are bounded controls over pinned internal derived fields; they are not plagiarism, copyright, authorship, or legal certification.

Phase 4 establishes one trustworthy one-result-block repair loop, not a complete-paper compiler or a publication guarantee. Phase 5A first adds safe package distribution, natural-language onboarding, a generic machine facade, and thin host projections while preserving the single-writer core; Phase 5B then adds controlled multi-agent lanes and optional research adapters. Phase 5A owns functional and safety parity across supported hosts; Phase 6 owns held-out v1/v2 and research-quality, efficiency, and human-effort outcome comparisons across systems, models, or hosts after the relevant evaluation arms are preregistered. No phase guarantees publication at Econometrica, a Top-5 journal, or a leading field journal; those venues define an ambition and evaluation burden, not a style template or acceptance promise.

## Design thesis

The main failure mode of an AI-written theory paper is rarely a missing style instruction. It is usually a missing economic argument: the system formalizes too early, confuses a solvable model with a good mechanism, and later adds generic intuition around a theorem.

V2 therefore requires this order:

```text
question and benchmark
→ mechanism hypotheses
→ prediction freeze and hand-solved micro-examples
→ mechanism stress tests and ablations
→ formal implementations and theorem discovery
→ proof, boundary, and closest-theory verification
→ validated economic argument
→ theory manuscript compiler
→ cold-reader and referee evaluation
```

A typed canonical state, dependency graph, decision history, and route-specific context compiler support this research process without becoming substitutes for economic judgment.

## Architecture documents

- [Architecture and constitution](ARCHITECTURE.md)
- [Positive theory research kernel](docs/architecture/theory_kernel.md)
- [State and runtime architecture](docs/architecture/state_runtime.md)
- [Theory manuscript compiler](docs/architecture/manuscript_compiler.md)
- [Target profiles and craft library](docs/architecture/profiles_and_craft.md)
- [Evaluation protocol](docs/architecture/evaluation.md)
- [Architecture scenario walkthroughs](docs/architecture/scenario_walkthroughs.md)
- [V1 capability migration](docs/architecture/v1_migration.md)
- [Implementation plan](docs/architecture/implementation_plan.md)
- [Phase 1 executable contract](docs/implementation/phase1_contract.md)
- [Phase 2 executable contract](docs/implementation/phase2_contract.md)
- [Phase 3 executable contract](docs/implementation/phase3_contract.md)
- [Phase 4 executable contract](docs/implementation/phase4_contract.md)
- [Phase 5A host bootstrap and onboarding contract](docs/implementation/phase5a_contract.md)

Each detailed document owns one part of the design. `ARCHITECTURE.md` defines the cross-cutting constitution and points to those owners; it does not duplicate their full specifications.

## V1 inheritance

V2 is an architecture rewrite, not a rejection of v1. It preserves v1's strongest scientific assets—including human decision persistence, literature-evidence discipline, absorption tests, example-to-theory construction, counterexample search, proof audit, scientific-taste safeguards, isolated review lanes, and result-statement hygiene—while replacing fixed quotas, duplicated Markdown state, journal-bound naming, and late-stage intuition repair.

The migration rule is strict: every high-value v1 capability must have a v2 owner and a parity test, or an explicit retirement rationale.

## Current source-checkout quick start

Python 3.11+ is required. The canonical validator is pinned to Pydantic 2.13.4 and pydantic-core 2.46.4 so replay acceptance does not drift across validator upgrades.

This is the current machine/developer path, not the intended ordinary
researcher experience. Phase 5A targets natural-language onboarding from a
supported host so the researcher does not have to open a shell or memorize
these commands. That host bootstrap is specified but not yet implemented; the
commands below remain the honest current interface.

For a provider-backed host, one-message onboarding may include a research
question only when that content is public or a verified pre-model/account-level
egress authorization already covers the provider and workspace. Otherwise the
safe experience uses one natural-language bootstrap request and a second
message with the private question after authorization--still no manual shell
commands, but no retroactive privacy claim.

```text
pip install -e .
etai doctor
etai --project /path/to/theory-project init --name "My theory project"
etai --project /path/to/theory-project validate
etai --project /path/to/theory-project status
```

A minimal framing run can then be opened at an exact canonical head:

```text
etai --project /path/to/theory-project begin frame.question_and_benchmarks
```

`begin` creates an immutable run/context manifest and a noncanonical candidate workspace. `stage` preserves a strict transaction candidate, `commit` validates and atomically advances the head, `stale --why` explains derived invalidation, and `recover` rebuilds disposable snapshots and views. Structural human choices are recorded through `decide` using the versioned Decision JSON schema in `schemas/v1/decision.schema.json`.

Phase 1 deliberately fails closed on entity/relation retirement and independent stored-status transitions. It does not yet implement provider calls, theory-specific object schemas, artifact excerpts, checkpoint compaction, public export/private-backup bundles, cryptographic human identity, or external release. No external-release route is enabled.

Run the deterministic test suite from a source checkout with:

```text
python -m unittest discover -s tests -v
python scripts/export_schemas.py --check
python scripts/export_theory_schemas.py --check
python scripts/export_authoring_schemas.py --check
python scripts/export_profile_craft_schemas.py --check
python scripts/export_profile_craft_resources.py --check
```

## Resume on another computer

The Git repository, not an IDE conversation, is the durable development
handoff. Before moving machines, commit and push the current branch;
uncommitted files do not follow a clone. On the new computer, clone the
repository and use `main` as the accepted Phase 1--4 base:

```text
git clone https://github.com/viplee110/econ-theorist-ai-v2.git
cd econ-theorist-ai-v2
git fetch origin
git switch main
git pull --ff-only
```

Install Python 3.11+ dependencies with `pip install -e .`, run `etai doctor`,
then run the five exporter checks above and
`python -m unittest discover -s tests -v`. Read `AGENTS.md`, the implementation
plan, and `docs/implementation/phase5a_contract.md` before Phase 5A changes;
together they replace the missing chat history. A clean `git status` and exact
exporter checks establish that the new machine has the same versioned source
and policy resources.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
