# Independent model-based scientific diagnostic

This is a model-based diagnostic audit of the model-produced candidate in
[`candidate_attempt_1.json`](candidate_attempt_1.json). The evaluator was not
given the engine source, tests, fixtures, or a gold answer. Scores are judgment
calls for development prioritization, not a journal forecast or formal
acceptance result and not human-expert review.

| Dimension | Score / 10 | Finding |
|---|---:|---|
| Falsifiability | 8 | The reversal question and kill condition are testable. |
| Economic consequence | 6 | The information-composition consequence is present but not yet sharply prioritized. |
| Benchmark delta | 5 | Two controls do not isolate their advertised objects cleanly. |
| Mechanism/result separation | 9 | No direction, proof, welfare, or novelty claim is smuggled into framing. |
| Kill condition | 6 | Useful, but partly depends on controls whose semantics need repair. |
| Intuition/readability | 5 | Dense state and control language obscures the two opposing economic forces. |
| Programmer/mathematical abstraction severity | 7 | The typed output is auditable but not yet an economist-facing explanation. |
| Expected expert editing burden | 7 | Substantive benchmark repair and substantial exposition work remain. |

The evaluator's separate holistic assessment was **6.3/10**; it was not the
arithmetic mean of the dimension scores. The output is an engine-accepted
framing transaction, not a Top-5-ready framing memo.

## Substantive defects

1. **The fixed-inspection control overstates what is fixed.** Freezing the
   state-contingent inspection rule does not fix the aggregate inspection rate
   `S(k)` when changing `k` also changes the stationary distribution of public
   states. The candidate's statement that `S(k)` is fixed by construction is
   therefore generally false.
2. **The frozen-stock cost ledger is close to a placebo.** It freezes the
   issuance rule and state-composition law and forbids seller reoptimization,
   so changing `k` is mainly a seller-accounting debit. Buyer inspection,
   allocation, and payoff are nearly constant by construction. That does not
   provide a meaningful direct-channel benchmark for the full equilibrium
   comparative static.
3. **The equilibrium-selection control is insufficient.** A fixed
   lexicographic selector does not rule out a reversal caused by jumps between
   equilibria. The design needs uniqueness, a continuous selected branch, or an
   all-equilibria robustness statement before assigning a reversal to the
   proposed mechanism.

## System implications

The next scientific improvements should be pilot-driven rather than another
generic safety layer:

- generate a canonical typed transaction and a separate one-page
  economist-facing framing memo containing one question, two opposing forces,
  a three-step mechanism, one minimal example, and a compact benchmark table;
- add a benchmark-semantic audit that marks, for every comparison, what changes,
  what is held fixed, what reoptimizes, and what remains endogenous;
- add logical checks for aggregate-versus-conditional claims, placebo controls,
  and equilibrium-selection artifacts;
- require a mechanism-robustness explanation before promoting a framing:
  identify the two opposing forces and state how selection artifacts are ruled
  out;
- measure one-sentence recoverability, reader burden, benchmark count, and
  expected expert editing time alongside schema validity.

The pilot therefore validates the handoff and also reproduces the user's core
complaint: mechanical correctness alone can still yield an abstract,
high-intervention economic-theory draft.
