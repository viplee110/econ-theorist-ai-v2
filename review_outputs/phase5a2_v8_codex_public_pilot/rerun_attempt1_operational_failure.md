# V8 post-stabilization rerun attempt 1 operational failure

Status: **frozen pre-WorkPacket host-path failure; not scientific evidence**

## Claim boundary

The first corrected-wheel rerun attempt used
`C:\tmp\etai-v8-poststabilization-pilot-20260717-4804323`. It did not create a
canonical project, deliver a WorkPacket, open a route, produce a candidate,
commit a transaction, or reach a human gate. The bridge response reported
`mutated=false`, `project_id=null`, `head=null`, and `route_run_id=null`.

The agent report's phrase "terminal operational error" describes the valid
bridge error response, not a persisted terminal journal record. The isolated
operational journal contains a reservation, a one-byte lock carrier, and an
empty events directory; it contains no `terminal.json`. The canonical root has
no `.econ-theorist` store.

## Captured evidence

The full source evidence remains in the isolated root. Its compact inventory
is:

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `run/001-start-request.json` | 1,794 | `c5d12978a2c942385b14ae9e3c87a8ae07234ceade4bd0db2a7b4a8a489a92be` |
| `run/002-start-metadata-captured-request.json` | 1,794 | `c5d12978a2c942385b14ae9e3c87a8ae07234ceade4bd0db2a7b4a8a489a92be` |
| `run/002-start-stdout.json` | 948 | `7cd21ae3afdc4d3f973ec1a77a8bf4d5dcefee1c5794ef81493e4370efe915f6` |
| `run/002-start-stderr.txt` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `run/002-start-metadata.json` | 2,793 | `bf868f359d13f1b86c14dc3327ce811588a3ed56bf8b2dc94bad6b6463114483` |
| `run/003-agent-report.md` | 2,544 | `584777b40a94142cdbd826a1b92f6cf3a7f2eba6ec8cdecf2cc28fb3201aaa37` |
| preproject `reservation.json` | 316 | `cd2318f012d85de59fb35087bad02dff5480b0e8a42594526e895f1252350607` |
| preproject lock carrier | 1 | `6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d` |

Attempt 001 failed before child launch and left no metadata, stderr, captured
request, or state directory. Its reported `PermissionError` therefore cannot
be independently classified from surviving evidence. Attempt 002 has a valid
capture-v2 envelope: source and captured request hashes match, the source did
not change, stdout is valid bridge JSON, response binding passed, and stderr is
empty.

## Diagnosis

Attempt 002 wrote the 212-character reservation path and then failed while
publishing the first immutable reserved-event path, which was 269 characters.
This Windows host reports `LongPathsEnabled=0`. The engine call chain reached
the same-directory `os.link` no-replace publication and returned
`OperationalError` when the final event did not exist after the underlying
`OSError`. The exact Win32 code was not projected into the bridge response, so
`WinError 206` is a strongly supported inference rather than a directly
captured fact.

The long path came from placing isolated `LOCALAPPDATA` beneath the verbose
pilot root. It is not a framing route, V8 validator, candidate, or economics
failure. The duplicate `run/bridge-venv` used the same wheel but was unnecessary
and was not causal.

## Disposition

Preserve the failed root unchanged. Do not retry there while the same long
operational path remains. R2 uses the short root `C:\tmp\etai-v8-r2`, the same
engine commit, wheel, skill, capture helper, and CASE bytes, plus the
preinstalled launcher. Its corresponding event-path projection is 231
characters. No engine or scientific-policy bytes changed between attempts.
