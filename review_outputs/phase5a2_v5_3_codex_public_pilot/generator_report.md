# Generator report

## Terminal outcome

- Outcome: `recorded_failure` (`failed_terminal`) on route `audit.framing_economics`.
- Project: `prj_daca32112d999b9a185964e29f75ba728ec66da721dd331b`.
- Final canonical head: `7575110612a3faff6d5784f1fb2bf34d1a31780d6b761d251a1c353460d7c789`.
- Terminal route run: `run_op_9303bc77ae7a5282451f0c40ee1dfe31bf670fa4fa36e038`.
- Terminal record interval: `2026-07-15T12:44:48.997806Z` to `2026-07-15T12:44:52.052575Z`.
- No human G1 decision was created, inferred, or recorded.

## Canonical progress

1. `frame.question_and_benchmarks` committed on the first candidate attempt at digest `7ad23adbeba3d0bde9a8bfeca0944e2e08881309e3e75a8c322f92f0098187f6`.
2. `decompose.primitives` committed on the second candidate attempt after the structured diagnostic `decomposes relation does not target PrimitiveGraph`; committed digest `7575110612a3faff6d5784f1fb2bf34d1a31780d6b761d251a1c353460d7c789`.
3. `audit.framing_economics` candidate attempt 1 passed the scientific/route checks reached before referential integrity, then failed without canonical mutation because `rel_governs_fqb_replacement_gate@1` bound an incorrect upstream semantic hash.

## Terminal compatibility defect

The audit contract requires a hard `governs` relation whose upstream is the candidate-output `FramingQualityBundle.economic_interpretation` facet. Its relation template gives `upstream_semantic_hash: null` with binding `runtime_facet_semantic_hash_v1`. The strict Transaction schema nevertheless requires a concrete 64-hex semantic hash. The bridge rejected an incorrect placeholder with `ReferentialIntegrityError`, did not disclose the expected runtime value, and re-delivered the same contract without a concrete value or contract-defined derivation. Continuing would require guessing or inspecting prohibited implementation source, so the route was recorded as a terminal engine-compatibility failure after one candidate attempt.

## Evidence index

- Initialization: `run/001_start_request.json`, `run/001_start_stdout.json`, `run/001_start_stderr.txt`, `run/001_start_metadata.json`.
- Framing candidate and commit: `run/002_candidate_attempt1.json`, `run/003_complete_attempt1_request.json`, `run/003_complete_attempt1_stdout.json`, `run/003_complete_attempt1_stderr.txt`, `run/003_complete_attempt1_metadata.json`.
- First continuation: `run/004_resume_request.json`, `run/004_resume_stdout.json`, `run/004_resume_stderr.txt`, `run/004_resume_metadata.json`.
- Primitive candidate attempt 1 and diagnostic: `run/005_candidate_attempt1.json`, `run/006_complete_attempt1_request.json`, `run/006_complete_attempt1_stdout.json`, `run/006_complete_attempt1_stderr.txt`, `run/006_complete_attempt1_metadata.json`.
- Primitive diagnostic repair and commit: `run/007_candidate_attempt2.json`, `run/008_complete_attempt2_request.json`, `run/008_complete_attempt2_stdout.json`, `run/008_complete_attempt2_stderr.txt`, `run/008_complete_attempt2_metadata.json`.
- Audit route delivery: `run/009_resume_request.json`, `run/009_resume_stdout.json`, `run/009_resume_stderr.txt`, `run/009_resume_metadata.json`.
- Audit candidate and diagnostic: `run/010_candidate_attempt1.json`, `run/011_complete_attempt1_request.json`, `run/011_complete_attempt1_stdout.json`, `run/011_complete_attempt1_stderr.txt`, `run/011_complete_attempt1_metadata.json`.
- Same-route re-delivery: `run/012_resume_current_request.json`, `run/012_resume_current_stdout.json`, `run/012_resume_current_stderr.txt`, `run/012_resume_current_metadata.json`.
- First finish-format diagnostic: `run/013_finish_engine_compatibility_request.json`, `run/013_finish_engine_compatibility_stdout.json`, `run/013_finish_engine_compatibility_stderr.txt`, `run/013_finish_engine_compatibility_metadata.json`.
- Terminal record: `run/014_finish_engine_compatibility_request.json`, `run/014_finish_engine_compatibility_stdout.json`, `run/014_finish_engine_compatibility_stderr.txt`, `run/014_finish_engine_compatibility_metadata.json`.
