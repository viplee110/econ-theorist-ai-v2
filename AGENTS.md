# Repository instructions

## Current phase

Phases 1--4 are accepted on `main`; Phase 4 implementation `63d3393` was merged
by `89d2152`. Phase 5A.0, the design contract and status repair for safe
natural-language onboarding and thin Codex, Claude Code, and Cursor host
projections, is complete on `agent/phase5a-host-bootstrap-contract` after
independent adversarial review found no remaining blocker. Its normative owner
is `docs/implementation/phase5a_contract.md`.

Phase 5A.0 changes documentation and freezes acceptance semantics only. Do not
claim that a host installer, generic facade, work packet, cross-host handoff,
or one-sentence onboarding exists until its later executable slice and tests
pass. Do not add host runtime code on the Phase 5A.0 branch; Phase 5A.1 begins
as a separate executable slice after this contract is merged.

Do not modify Phase 1--4 payload meanings, committed schemas, registry or
instruction bytes, packaged profile/craft resources, frozen fixtures, or
historical selector behavior to solve a host-integration problem. Host
projections remain thin: they invoke one engine-owned machine protocol and may
not duplicate route instructions, scientific gates, profiles, or validators.
No host writes canonical ObjectStore bytes directly or confirms an L2/L3 human
decision.

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

For the Phase 5A.0 documentation-only slice, also run `git diff --check`, verify
every new local Markdown link, and search for stale Phase 4 branch/merge status.
Later executable Phase 5A slices must add their focused contract, install,
idempotence, root-binding, cross-host, privacy, recovery, and adversarial tests
before requesting review. Report optional-tool skips separately; they are not
passes.

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

## Host integration invariants

- Natural language is a user interface over the canonical engine, not a second
  research workflow.
- The first installation or protected action may require a bounded host/OS
  approval; never promise to bypass it.
- Bind one exact project root and reject ambiguous, nested, escaped, or foreign
  stores.
- Repeated onboarding and host switching must preserve project id, head,
  derived run view, Decisions, blockers, and work-packet hashes.
- Do not expose non-public content to a provider-backed host without the
  contract's EgressPlan, authorization, and technical secret/compartment
  isolation. Install permission is not egress consent.
- Exclude unrestricted human-decision actions from model tools. A conforming
  host requires the exact trusted-human approval receipt; Phase 1's local
  `kind=human` assertion is not cryptographic identity.
- Preserve user-owned `AGENTS.md`, `CLAUDE.md`, Cursor rules, and unrelated
  working-tree changes. Modify only an engine-owned projection or stop with a
  manual merge proposal.
- IDE memory, chat transcripts, generated status, and Git state are
  noncanonical. Keep the CLI/machine path usable without any host adapter.

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
- `docs/implementation/phase5a_contract.md`: host/bootstrap, natural-language
  onboarding, machine navigation, and cross-host acceptance semantics.

Do not define a second competing workflow in a README, prompt, example, or generated dashboard. Link to the owning specification.

## Design discipline

- Preserve v1 capabilities by function, not by copying its filenames or long prompts.
- Add canonical fields only when they affect routing, authority, dependency, claim scope, provenance, privacy, or evaluation.
- Treat generated Markdown as a view, never as canonical state.
- Keep the always-on control kernel small; load research, verification, authoring, and review instructions by route.
- Prefer a small end-to-end vertical slice to a broad but untested scaffold.
- Every normative rule should eventually have an executable validator, scenario test, or explicit human gate.
- Do not claim Top-5 readiness from bookkeeping, LLM consensus, or style similarity.
