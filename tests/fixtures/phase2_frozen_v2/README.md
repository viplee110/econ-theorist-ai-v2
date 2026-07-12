# Frozen Phase 2 semantic oracle

`canonical_semantics.v2.json` pins the accepted Phase 2 model schemas, exported
schemas, v2 instruction corpus, registry file, and gold case independently of
the active Phase 3 catalog. A deliberate Phase 2 migration must create a new
oracle version; Phase 3 may not update these values to make a regression pass.
