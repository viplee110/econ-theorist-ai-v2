# Phase 1 test fixtures

Phase 1 tests construct their smallest inputs in temporary directories. This
keeps object addresses, locks, and atomic-write races isolated and prevents a
checked-in generated snapshot or status page from becoming an accidental
source of truth.

Later slices may add the shared `R0` fixture here. Any such fixture must retain
the distinction between canonical inputs and rebuildable projections:

- immutable transaction and artifact bytes are canonical only when reachable
  from `refs/main`;
- snapshots and indexes are rebuildable caches;
- `views/status.md` is generated and noncanonical;
- human-owned files are never test outputs or in-place write targets.
