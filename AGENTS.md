# Repository instructions

## Current phase

Phases 1--3 are accepted on `main`. This repository is implementing the first
Phase 4 profile-and-craft vertical slice against
`docs/implementation/phase4_contract.md`. The slice adds a separate
`profile_craft` payload namespace, a frozen-superset `registry.v4.json`, typed
obligation-to-predicate audits, deterministic profile resolution, reader-problem
diagnosis, function-first craft retrieval, canonical-writer repair, and a
Phase-4-specific closure layered on the existing Phase 3 authoring closure.

Do not modify Phase 1--3 payload meanings, committed schemas, registry or
instruction bytes, frozen fixtures, or historical selector behavior to solve a
Phase 4 problem. The ordinary v3 design, compose, review, reader-probe, and
closure routes remain intact. Phase 4 adds only the native routes named in its
contract. Static profile/craft catalogs stay separate from project manifests,
and selected craft moves belong in `CraftSelectionManifest`, never in the
resolved profile stack.

The canonical repository verification command remains
`python -m unittest discover -s tests -v`. Schema and pinned-resource
verification requires all five accepted exporters:

```text
python scripts/export_schemas.py --check
python scripts/export_theory_schemas.py --check
python scripts/export_authoring_schemas.py --check
python scripts/export_profile_craft_schemas.py --check
python scripts/export_profile_craft_resources.py --check
```

Run `etai doctor` and the focused Phase 4 contract, downgrade,
selective-invalidation, context-isolation, replay, and gold tests before
requesting review. Report optional-tool skips separately; they are not passes.

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
