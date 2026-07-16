# V8 public Codex pilot postflight manifest

Status: **recorded after the failed audit run; source evidence remains in the
isolated non-cloud pilot root**

The source root was
`C:\tmp\etai-v8-public-pilot-20260716-be4b192`. The files below were read
without resuming or mutating the route. Paths are relative to that root.

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| `run/codex-20260716T230126-agent-report.md` | 1,726 | `74795e5cd3ebbccdff9a7d6c3e621fce82caac8d88e0054ac4bd6d7cc5e88c13` |
| `run/codex-20260716T230126-continuation-stdout.json` | 121,258 | `4194db6366ddf67970c3a19f5e2417e3acbdc020b77956a865a8cc0dfc156a8d` |
| `run/codex-20260716T230126-audit-complete-stdout.json` | 1,384 | `02bac1874ed18c5606958b7015528348d242936705e501dd53454965fa19b474` |
| `run/codex-20260716T230126-audit-repair1-stdout.json` | 1,378 | `5ea0a63cb046381217d1e2bde8add4b2beb7de3ebd248ad7cf783532d9e133f5` |
| `run/codex-20260716T230126-audit-repair2-stdout.json` | 775 | `880bd7c1ede0b027e6f922845665c50feacc11e399cdabb084eea7dbc33294c3` |
| `run/codex-20260716T230126-audit-finish-stdout.json` | 676 | `dad696ca14ac7d98cae0562343c1d261ffb859ce20b33476baa18147ee5a29ad` |
| `run/codex-20260716T230126-audit-finish-retry-stdout.json` | 1,413 | `365c59a06ba1e6b2b31b40b7fedef142fce3240dde57e36d0ad3849c7f22f4e4` |
| initial archived candidate | 19,091 | `2b944a3902da18db5fe448046b0be217e8708c22cd8d803dd48827ac57585078` |
| final archived candidate | 19,032 | `3bcd35c30dff9742d50b80e0000ee6dd21d0642e2b766cc3d4f1ce6888c65643` |
| accepted `host.finish` operation record (`recorded_failure`) | 1,966 | `41b5099558d6b2c5072fc700018604805693364c15fa1d2524118a6240b485b1` |

The corresponding audit response metadata hashes are:

- initial completion: `f9013d8f8d70b415013a0ad48892dac63d9d5e467f94ea513e7c0ecf9f17cda9`;
- repair 1: `3e75a906785e3d09e9436c964e01884c0b2b2712fb0952a5236cb5224748e161`;
- repair 2: `bc9f29c9fdeb9bb857420f758ea4263c5c6c18ab08dceef17ee93f31597258c1`;
- first finish: `1aac6a3a6faea7989feb51f1192f7013b6ff31357646942970dd771abd4684db`;
- accepted finish retry recording `failed_terminal`:
  `6209d91fc3195f3e008fa0d00fb80df2d936adcaaa862a88679c676887065b5c`.

## Evidence limitations

- the repair-1 raw candidate was overwritten after its leading JSON parse
  failure and was not immutably captured;
- the source `audit-finish-request.json` was reused, so its current bytes are
  the corrected retry rather than the first rejected request;
- capture metadata preserves byte counts and digests for those invocations,
  but it does not reconstruct the missing raw sources;
- the post-pilot diagnosis and regressions are not model-run evidence.

The post-pilot capture-v2 candidate is designed to close these evidence gaps by
freezing the exact request bytes for every invocation and the pre-invocation
raw candidate bytes for every source-reading `complete` request. It also binds
that source to the exact route/WorkPacket path, invalidates a capture if the
source changes during execution, and compares any completion candidate digest
to the preflight canonical digest. Its own deterministic verification and a
later model run are separate evidence.
