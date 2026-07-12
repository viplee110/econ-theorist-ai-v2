# Econ Theorist AI v2

Econ Theorist AI v2 is a research operating system for developing frontier-level **economic theory** papers with human–AI collaboration.

The project is designed for pure and applied theory. It does not provide econometric, identification, estimation, data, or empirical-paper workflows. Symbolic computation, numerical examples, simulation, and formal tools are allowed only when they help discover, falsify, or verify theoretical claims.

## Current status

The repository contains **Architecture v0.1**, the accepted **Phase 1 walking substrate**, the accepted **Phase 2 theory-kernel vertical slice**, and the implemented **Phase 3 assurance and authoring vertical slice**. Phase 1 is a local, provider-neutral scientific state kernel: it initializes a theory project, preserves immutable transactions and Decisions, compiles bounded route contexts, commits under an exclusive lock, derives facet-level staleness, protects human-owned files, renders noncanonical views, and recovers from interrupted commits. Its acceptance suite includes real two-process head races, abrupt subprocess exits on both sides of the atomic-head boundary, adversarial authority/privacy tests, and Windows junction/reparse checks.

Frozen registry v2 contains 19 routes: 16 are enabled (13 theory routes, dependency repair, and two sealed blind-evaluation routes), while its three authoring placeholders remain `not_implemented`. Registry v3 adds ten native assurance, authoring, cold-reader, closure, and effort routes without changing historical v1/v2 meanings. Each native route validates the exact input IDs, revisions, and lineage in its immutable run focus; satisfying only entity types and counts is insufficient, and a same-type foreign Paper IR, contract, probe, review, or assurance object fails closed. For assurance, the VAP is the authority root: its internal ClaimGraph, FormalModel, AssumptionMap, and VerificationBundle refs must match exactly; every verified obligation/record pair must belong to that bundle and have exactly one same-package re-derivation. The provider-visible selected refs and blind packet are a separate projection and may exclude the VAP even though the immutable focus retains its authority binding. The real Phase 3 gold chain extends the accepted Phase 2 ObjectStore history through three obligation-scoped blind re-derivations, a multi-record assurance bundle, Paper IR and reader contracts, and an actual manuscript artifact. Its first manuscript fails the economic-reader and cold-reader transfer gates, receives a typed `RevisionBrief`, is superseded by the same canonical writer, and reaches `authoring_ready` only after fresh formal, economic, and cold-reader reviews pass.

Phase 3 validation reads and binds the immutable artifact bytes themselves--including re-derivation transcripts, proof-audit and harness records, manuscript text, and the separately sealed probe, answer key, and response--rather than trusting payload-declared hashes. Every non-whitespace manuscript-body character must belong to a typed prose span, and economic-reader and cold-reader coverage closes separately for every `ResultPacket`. `authoring_ready` requires the entire exact dependency chain to remain current and fresh, not merely the terminal review records. The writer cannot see cold probes or keys, the respondent cannot see the key, and append-only human-effort telemetry records active intervention separately from unattended compute. The comprehensive gold suffix currently has a noticeable replay and validation cost; reducing that cost without weakening byte, lineage, or isolation checks is a later optimization item.

The local `submission` compiler is implemented, but it is intentionally narrow: it may promote an exact current authoring-ready working unit only with the governing human Decision and may change formatting and span offsets, never wording, typed meaning, or scientific scope. It does not execute an external submission. Phase 3 also binds a harness's exact executable predicate and receipt to a declared obligation, but cannot by itself prove that the predicate is semantically equivalent to the obligation's natural-language meaning; that mapping is an explicit Phase 4 hardening boundary.

Phase 3 establishes a trustworthy one-result-block authoring core, not a complete-paper compiler or a publication guarantee. Phase 4's field/audience/venue profiles and theory craft-retrieval system remain to be implemented. No claim is made that the system can guarantee publication at Econometrica, a Top-5 journal, or a leading field journal. Those venues define an ambition and evaluation burden, not a style template or an acceptance promise.

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

Each detailed document owns one part of the design. `ARCHITECTURE.md` defines the cross-cutting constitution and points to those owners; it does not duplicate their full specifications.

## V1 inheritance

V2 is an architecture rewrite, not a rejection of v1. It preserves v1's strongest scientific assets—including human decision persistence, literature-evidence discipline, absorption tests, example-to-theory construction, counterexample search, proof audit, scientific-taste safeguards, isolated review lanes, and result-statement hygiene—while replacing fixed quotas, duplicated Markdown state, journal-bound naming, and late-stage intuition repair.

The migration rule is strict: every high-value v1 capability must have a v2 owner and a parity test, or an explicit retirement rationale.

## Phase 1 quick start

Python 3.11+ is required. The canonical validator is pinned to Pydantic 2.13.4 and pydantic-core 2.46.4 so replay acceptance does not drift across validator upgrades.

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
```

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
