# Repository instructions

## Current phase

This repository is implementing the Phase 1 walking substrate against Architecture v0.1. Keep changes inside the executable contract in `docs/implementation/phase1_contract.md` until the Phase 1 branch is reviewed. Do not add Phase 2 discovery prompts, model-provider calls, manuscript generation, multi-agent orchestration, databases, or UI scaffolding to solve a Phase 1 problem.

The canonical Phase 1 verification command is `python -m unittest discover -s tests -v`; committed JSON schemas must also match `python scripts/export_schemas.py --check`.

## Scope

- Serve economic theory papers only: pure theory and applied theory.
- Do not add econometric, identification, estimation, data, regression, experiment, or empirical-paper workflows.
- Symbolic and numerical tools may support theoretical exploration, equilibrium checks, counterexample search, or proof verification. Finite numerical evidence is never a proof of a universal claim.
- Venue names are target overlays, not architectural namespaces.

## Scientific invariants

- Begin from a question and an exact benchmark, not from a preferred technique.
- Separate a mechanism hypothesis from a formal implementation of that mechanism.
- Freeze predictions before seeing the full derivation; preserve failed predictions.
- Require a hand-solved benchmark and minimal mechanism example before a general model is promoted.
- Distinguish formal validity, economic-interpretation validity, literature/novelty status, human acceptance, and freshness.
- A theorem can be true while its proposed intuition is false; verify both.
- Do not force welfare or policy language onto pure conceptual theory. Require economic consequence, application class, or changed modeling practice instead.
- Do not use journal-like prose, theorem density, or mathematical abstraction as proxies for contribution quality.

## Human authority

Agents may explore reversible branches and propose decisions. Human confirmation is required before a core question, model primitive, equilibrium concept, central result scope, novelty claim, argument spine, or target/audience decision becomes a stable dependency. External release and submission always require explicit authorization.

## Architecture sources of truth

- `ARCHITECTURE.md`: constitution, boundaries, and system-level relationships.
- `docs/architecture/theory_kernel.md`: positive research process and scientific gates.
- `docs/architecture/state_runtime.md`: canonical state, transactions, dependencies, routing, and recovery.
- `docs/architecture/manuscript_compiler.md`: Paper IR and authoring contracts.
- `docs/architecture/profiles_and_craft.md`: theory-only craft learning and target calibration.
- `docs/architecture/evaluation.md`: readiness and v1/v2 evaluation.
- `docs/architecture/scenario_walkthroughs.md`: end-to-end integration tests on paper.
- `docs/architecture/v1_migration.md`: capability preservation and retirement decisions.
- `docs/architecture/implementation_plan.md`: phase order and exit criteria.

Do not define a second competing workflow in a README, prompt, example, or generated dashboard. Link to the owning specification.

## Design discipline

- Preserve v1 capabilities by function, not by copying its filenames or long prompts.
- Add canonical fields only when they affect routing, authority, dependency, claim scope, provenance, privacy, or evaluation.
- Treat generated Markdown as a view, never as canonical state.
- Keep the always-on control kernel small; load research, verification, authoring, and review instructions by route.
- Prefer a small end-to-end vertical slice to a broad but untested scaffold.
- Every normative rule should eventually have an executable validator, scenario test, or explicit human gate.
- Do not claim Top-5 readiness from bookkeeping, LLM consensus, or style similarity.
