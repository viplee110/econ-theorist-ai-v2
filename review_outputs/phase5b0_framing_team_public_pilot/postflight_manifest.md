# Postflight evidence manifest

## Frozen identities

- Engine commit: `cb2abb97e94086e940bb1a84c95eb054cd4eca2c`
- Wheel SHA-256:
  `f94f62ecfbc11bcdf7ad52b5cadd4ed127de0006309a54daf025e1bea7670064`
- Pilot observable model label: `user-selected-high-intelligence-unverified`
- Q-reader observable model label: `high-intelligence-model-unverified`
- Project id: `prj_8d76c7f0fe786f8a6abf8b49f38807ac47380cdd3681e3a0`
- Route run id:
  `run_op_aa380ca47c2adbc16bd7a4643e20123e7472b410b06132a2`
- Canonical head:
  `50fa98f65c974269044331d023eb06cf6071a6207df27ab3f5c71e8a5771fcfd`

`evidence_manifest.json` is the complete byte/hash inventory for the compact
archive. It includes the exact canonical transaction, final completion bundle,
team plan/panel/synthesis/handoff/worker binding, host-receipt preimage, and
candidate-only Q lock.

The original pilot control inputs retain their exact names under `control/`, so
the preflight SHA sidecar resolves on case-sensitive systems. The exact pre-Q
source-aware audit and matching sidecar are retained under `historical_pre_q/`;
its Q `PENDING` line is a historical state, not the final Q verdict. The final
verdicts live in `evaluation_summary.md` and the Q lock. Its old U rationale is
likewise superseded by the final evaluation summary and is retained only to
preserve the pre-Q audit bytes.

The cold-reader package retains its original input names and preflight verifier
under `q/reader_root/`. Because this is the after-run archive, `report/` now
contains the locked output; the verifier's intentional initial-empty-report
check must not be rerun in place. `q/controller/Q_MANIFEST.sha256` and the
top-level evidence manifest verify the preserved bytes without rewriting the
reader package.

## Deliberately retained only in the local pilot root

The following remain at `C:\tmp\p5b1` and are not duplicated in Git:

- 001--006 request/captured-request/stdout/stderr/metadata bundles;
- the 001--004 large bridge responses and WorkPacket;
- rejected and raw candidate attempts;
- the 81 KB worker-delivery file;
- unrelated operational/canonical projections and host state;
- the wheel and virtual environment.

Their relevant identifiers, statuses, diagnostic text, bytes, and hashes are
recorded in `agent-report.md`, `historical_pre_q/POSTFLIGHT_AUDIT.md`, and
`machine_audit.md`. This keeps the committed evidence compact while preserving
the exact local audit root. No failed attempt is represented as a canonical
commit.

## Verdict anchors

- M: `PASS`
- T: `MIXED`
- U: `NOT ESTABLISHED`
- Q: `MIXED`, confidence `0.91`
- Q input SHA-256:
  `43ea849be933a8528b357b3ba79c789587e1ecdad376d893382d750ac3820bb8`
- Q report SHA-256:
  `c4915b9c646f6b3b57f0d2bdffd1bd401358c4bf5e029dad1b7835b11355f501`

The Q task saw only the mechanical scientific projection and its task materials
in `q/reader_root/`, and none of the team, user, repair, pilot-model, machine,
or source evidence before locking its report. The Q reader's observable model
label is distinct from the pilot label; neither verifies a backend identity.
