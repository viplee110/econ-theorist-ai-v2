# Exact evidence inventory

All paths are relative to `C:\tmp\etai-v5_1-public-pilot-20260714` unless shown otherwise.

## Controlling inputs

- `CASE.md`
- `.agents/skills/econ-theorist-v2/SKILL.md`

## Host-capture setup evidence

- `run/001_host_capture_failure.md` — `Start-Process` failed before etai process creation because the environment contained duplicate case variants of `Path`.
- `run/002_host_capture_failure.md` — sandbox redirection failed before etai process creation.

## Public help, schema, and doctor

- `run/003_help.meta.json`
- `run/003_help.stdout.txt`
- `run/003_help.stderr.txt`
- `run/004_request_schema.meta.json`
- `run/004_request_schema.stdout.json`
- `run/004_request_schema.stderr.txt`
- `run/005_etai_help.meta.json`
- `run/005_etai_help.stdout.txt`
- `run/005_etai_help.stderr.txt`
- `run/006_doctor.meta.json`
- `run/006_doctor.stdout.txt`
- `run/006_doctor.stderr.txt`

## Initialization and first framing route

- `run/007_start.request.json`
- `run/007_start.meta.json`
- `run/007_start.stdout.json` — exact zero-byte stream from host timeout.
- `run/007_start.stderr.txt` — exact zero-byte stream from host timeout.
- `run/008_resume_same_start.meta.json`
- `run/008_resume_same_start.stdout.json` — full ready response, WorkPacket, and candidate authoring contract.
- `run/008_resume_same_start.stderr.txt`
- `run/009_frame_question_and_benchmarks.attempt1.candidate.json`
- `run/009_frame_question_and_benchmarks.attempt1.meta.json`
- `run/010_complete_attempt1.request.json`
- `run/010_complete_attempt1.meta.json`
- `run/010_complete_attempt1.stdout.json` — structured validation diagnostic.
- `run/010_complete_attempt1.stderr.txt`
- `run/011_frame_question_and_benchmarks.attempt2.candidate.json`
- `run/011_frame_question_and_benchmarks.attempt2.meta.json`
- `run/012_complete_attempt2.request.json`
- `run/012_complete_attempt2.meta.json`
- `run/012_complete_attempt2.stdout.json` — first canonical commit response.
- `run/012_complete_attempt2.stderr.txt`

## Blocked continuation navigation

- `run/013_start_next.request.json`
- `run/013_start_next.meta.json`
- `run/013_start_next.stdout.json` — exact blocked response and registry diagnostics.
- `run/013_start_next.stderr.txt`

## First repeated framing route

- `run/014_start_next_with_brief.request.json`
- `run/014_start_next_with_brief.meta.json`
- `run/014_start_next_with_brief.stdout.json` — full ready response, WorkPacket, and candidate authoring contract.
- `run/014_start_next_with_brief.stderr.txt`
- `run/015_frame_question_and_benchmarks_repeat.attempt1.candidate.json`
- `run/015_frame_question_and_benchmarks_repeat.attempt1.meta.json`
- `run/016_complete_repeat_attempt1.request.json`
- `run/016_complete_repeat_attempt1.meta.json`
- `run/016_complete_repeat_attempt1.stdout.json` — second canonical commit response.
- `run/016_complete_repeat_attempt1.stderr.txt`

## Second repeated framing route and terminal stop

- `run/017_start_next.request.json`
- `run/017_start_next.meta.json`
- `run/017_start_next.stdout.json` — full third ready response, WorkPacket, and candidate authoring contract.
- `run/017_start_next.stderr.txt`
- `run/018_frame_question_and_benchmarks_repeat2.attempt1.candidate.json` — unsubmitted draft snapshot created before the stop instruction; no completion request exists.
- `run/018_unsubmitted_third_route_draft.meta.json`

## Declared candidate locations

- `.econ-theorist/staging/run_op_699125ff91cd4beae0569ca26f174e405d58ece6f531565a/candidate.json` — final submitted source for first route run; exact attempts are preserved separately under `run/009...` and `run/011...`.
- `.econ-theorist/staging/run_op_acaa89f3d3444b25d963ff8ec936917d6408083be4150a13/candidate.json` — submitted source for first repeated route run.
- `.econ-theorist/staging/run_op_3e47218ad496305bffbd295213b0c3aed3294b553659b27f/candidate.json` — unsubmitted draft; left untouched at stop.

## Reports

- `generator_report.md`
- `evidence_inventory.md`
