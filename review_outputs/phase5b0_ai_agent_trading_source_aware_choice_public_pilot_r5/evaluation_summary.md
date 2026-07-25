# Phase 5B AI-agent-trading neutral-root pilot R5 evaluation

## Archive role

This is an additive postflight evaluation of:

`C:\tmp\etai-at-r5-291cd02`

Freeze the run at `awaiting_user_choice`. Do not apply a choice, create its
worker, call `finish`, or use the run as clean first-use or research-quality
evidence.

## Exact evidence

- engine commit:
  `291cd0266c3afeb45dd10cb2f22388f0d5a756d5`
- wheel SHA-256:
  `eb90de7f022bca22e6b7fa7c9a4e01160b55c2b56650558ea5bd532e71ed14f2`
- task prompt SHA-256:
  `8e1298c7ad70aeca8e166a5a18914ab61b80e6fae7a909ccbf4d9fcecd9df333`
- agent report SHA-256:
  `bdb64851fa6a377d495452c9be921a95be9be9569aa36a0e7020f97059472a85`
- project id:
  `prj_fe2a92e067daf577a88aacdd78f903da2eb461c1c98c979f`
- route run:
  `run_op_05fed0b76245ffc3a3f9bdeb69ef67fd57233e056e3326a1`
- WorkPacket:
  `09757a800d80a64469a4bcc063272a4a1855c763101d0f276c4f820633e11313`
- delivery envelope:
  `14402015767806cd0b93a7b83215f0aff15f62e10671503c6ba648214bc6ab60`
- team plan:
  `45eef28ee8112d4272fd3daa6b929e9bee81fe7cba3bb4a1e48e84c49cbd69d0`
- panel:
  `755179c52dd356407215f708de9bd30caa77c2e0834d7f13dc4d5a25ac9bf1d5`
- choice review:
  `bf8e616f9cdedd582427540fef672685eec5d6a165a7c23cf5b85a17fd7cf72b`
- unchanged canonical head:
  `95d0642d047a93da05a910b542ffa060d3ffa664ce151bd20d7fa22327fdc256`
- observable lane/coordinator model label: `gpt-5.6-sol`; provider/backend
  identity was not independently established.

## Separate verdicts

| Dimension | Verdict | Bound conclusion |
|---|---|---|
| Machine/protocol | **PASS — bounded stop only** | The bridge reached `awaiting_user_choice`; no worker, candidate, handoff, human gate, or `finish` occurred and the head did not change. |
| Initial research input | **PASS** | The separately intended `requested_scope` and `framing_intent` strings survived request serialization and exactly matched `WorkPacket.run_input`. |
| Panel diversity | **PASS — content only** | A studies machine-verifiable policy commitment in repeated bilateral trade; B studies coordinated pseudonymous replication in a repeated double auction. They are materially different proposals. Logical isolation remains a host claim. |
| Choice-review fidelity | **FAIL** | The coordinator's correct UTF-8 review content was transcoded while constructing the bridge request. The engine bound the changed strings, while the final researcher display used the different correct helper content. |
| Choice UX | **MIXED** | The complete panel and cards repair the prior hash/title-only failure, but the output is very long, source links are malformed by nested Markdown, and the displayed view is not the bound view. |
| Scientific orientation | **MIXED** | Both cards contain a concrete question, benchmarks, ordinary-agent comparison, operational primitive, overlap warning, and kill condition, but both have high absorption risk and the dynamic false-name search omitted direct neighbors. |
| Research quality / novelty | **NOT ESTABLISHED** | No theorem, formal validity result, novelty audit, G1 decision, or worker candidate exists. |

## Fidelity failure

`choice-review-content.json` is valid UTF-8 and contains the intended Greek
symbols and Unicode punctuation. Its SHA-256 is:

`0af7e7f9b3e8be626b7bb60cefb198b8178e5f98b238c5da91ffeaa2d8313c8c`

The submitted `choice-review-request.json` has SHA-256:

`245fbaa44a28bb03be94f975e33f7f3134952c7788de7c5e1b00fdeb5ca7ae2a`

Across the structured review, 27 string leaves differ. Examples include:

- `δ` becoming `未`;
- `ε` becoming `蔚`;
- the Unicode punctuation in author names becoming mojibake.

The bridge correctly bound what the host submitted. The final report then
displayed the correct local helper content rather than the changed content
returned by the bridge. This is a host file/shell and display-binding failure,
not a canonical engine mutation or a scientific-validator defect.

The bounded correction is operational only:

1. preserve every draft, screen, source, and card as decoded UTF-8 across host
   file and shell boundaries;
2. compare decoded strings before publication; and
3. render the researcher choice screen from the exact bound bridge response,
   never from a different helper file.

No new schema, route, gate, validator, or generic security layer is warranted.

## Scientific postflight

### Direction A — park the AI framing

Machine-readable, executable commitment is already a general program or
contract technology rather than an AI-specific primitive. Repeated bilateral
trade and conditional commitment/disclosure also have close existing
characterizations. A should not be selected unless a minimal model first
identifies a capability that an ordinary mediator, contract, or precommitted
strategy cannot reproduce. The more honest fallback is a general
commitment-equivalence probe, not an AI-agent-trading paper.

### Direction B — revise before selection

Cheap coordinated pseudonymous copies are economically relevant, but
“stateful” or “learning” copies may be only one principal's joint
history-contingent strategy. The missing first step is a two-period
separation-or-reduction test. Identity age, exit/re-entry, persistent types,
cross-period budgets, reputation, or history-contingent forfeiture must
strictly change implementability relative to static or online false-name
baselines. A completely refundable deposit with no capital or opportunity cost
cannot supply the result.

The source review omitted especially close dynamic references:

- Todo et al., *False-name-proofness in Online Mechanisms* (AAMAS 2012);
- Bredin, Parkes, and Duong, *Chain: A Dynamic Double Auction Framework for
  Matching Patient Agents*;
- Friedman and Resnick, *The Social Cost of Cheap Pseudonyms*.

Therefore B is `REVISE`, not a direct positive-mechanism selection. Continue
only if a finite two-period model yields a strict dynamic separation; accept a
reduction theorem and park the AI-specific claim otherwise.

## Disposition

Record R5 as **protocol stop PASS, initial input PASS, choice-review fidelity
FAIL, researcher UX/scientific orientation MIXED, and research quality NOT
ESTABLISHED**. Preserve its research reasoning as advisory evidence only.

The next check should be one short neutral-root run after the narrow UTF-8 and
bound-display host correction. It should not rerun the whole regression suite,
change V8, activate ResearchMoves, or extend the workflow.
