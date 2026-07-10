# Econ Theorist AI v2

Econ Theorist AI v2 is a research operating system for developing frontier-level **economic theory** papers with human–AI collaboration.

The project is designed for pure and applied theory. It does not provide econometric, identification, estimation, data, or empirical-paper workflows. Symbolic computation, numerical examples, simulation, and formal tools are allowed only when they help discover, falsify, or verify theoretical claims.

## Current status

The repository is in **Architecture v0.1**. The current work records and tests a scientific and systems design to be reviewed before implementation begins. No claim is made that the system can guarantee publication at Econometrica, a Top-5 journal, or a leading field journal. Those venues define an ambition and evaluation burden, not a style template or an acceptance promise.

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

Each detailed document owns one part of the design. `ARCHITECTURE.md` defines the cross-cutting constitution and points to those owners; it does not duplicate their full specifications.

## V1 inheritance

V2 is an architecture rewrite, not a rejection of v1. It preserves v1's strongest scientific assets—including human decision persistence, literature-evidence discipline, absorption tests, example-to-theory construction, counterexample search, proof audit, scientific-taste safeguards, isolated review lanes, and result-statement hygiene—while replacing fixed quotas, duplicated Markdown state, journal-bound naming, and late-stage intuition repair.

The migration rule is strict: every high-value v1 capability must have a v2 owner and a parity test, or an explicit retirement rationale.

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
