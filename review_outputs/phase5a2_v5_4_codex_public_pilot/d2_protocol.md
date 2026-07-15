# V5.4-D2 economy-tier blind replication

Status: frozen before the first D2 bridge invocation.

## Purpose

After V5.4-D1 reached a terminal bridge outcome, the user changed the Codex
task to a lower-cost model configuration. D2 tests whether the same frozen V2
workflow can be operated by a fresh blind current-Codex Generator under that
user-selected economy-tier configuration.

The runtime does not expose an exact underlying model identifier. Therefore
D2 is a separately labelled feasibility replication, not a controlled D1/D2
model comparison and not evidence of a causal model effect, general quality
effect, lower human burden, or publication readiness.

## Frozen treatment

- engine source commit: `c8c539e6b81404cfcd1eb247956b626f4b18ef2f`;
- wheel: 687,580 bytes, SHA-256
  `DB549E9F0203885B7A13ACE59A9D2A2D855167A9A257B90AEE99B0DEF5CAB7B2`;
- unchanged public CASE: 2,994 bytes, SHA-256
  `C26BE82FA643D702F13DE113847B2CD93D4E5C57B54DF8D72B09A6470AFFAB75`;
- unchanged seed block: 1,237 UTF-8 bytes, SHA-256
  `7EBD071530BD591D7B689A5946132AAF2007F817632A65FC1CC8F3A2F46CD2CB`;
- unchanged installed skill: 4,938 bytes, SHA-256
  `4EE147E92ABC591D4D22D1CD80AADE47DBF34A9D0351D1ED4026C27F67A7C5A1`;
- unchanged capture helper: 10,910 bytes, SHA-256
  `017D941665D3220C3F50885F08AE4D4AF38979F67C8267C0B9CF3C64CE40D519`;
- selected root:
  `C:\Dropbox\Shufe\Research\Project\Search on Graphs\.etai-v5_4d2-economy-tier-20260716-c8c539e`.

The only changed condition is the user-selected current Codex configuration.
Record it as `economy-tier user-selected; exact underlying model identifier not
exposed`. Do not infer or claim a model slug.

## Blind execution

Use one fresh Generator with no inherited conversation. It may read only the
selected root's CASE, installed skill, and returned WorkPackets. It must not
read D1, the source repository, parent or sibling directories, evaluation
keys, prior outputs, tests, web material, or subagents.

Use the installed capture bridge for every call. Follow engine-selected routes
one canonical commit at a time. Preserve every request, response, metadata and
candidate attempt. A route receives at most an initial candidate plus two
repairs after repairable candidate diagnostics. Do not create or infer a human
decision. Stop at a human gate, a genuine terminal failure, or the bounded
repair limit; use `finish` only for a true otherwise-unrecorded termination.

## Evaluation boundary

After terminal output is frozen, apply the already frozen V5.4 E1--E6,
M/A/O/R and H0--H4 diagnostics separately. An audit that accurately identifies
an unresolved framing problem may be scientifically successful even though the
research object is `REVISE` or `KILL`. D2 may not reclassify the official
model-gated V5.4 run or D1.
