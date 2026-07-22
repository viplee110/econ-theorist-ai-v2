# Source-Isolated Noncanonical Nondegeneracy Probe

## 1. Input integrity and isolation

The three authorized scientific inputs passed all pre-reading checks:

| File | Bytes | SHA-256 | Required lock field |
|---|---:|---|---|
| `input/FRAMING_INPUT.json` | 13113 | `43ea849be933a8528b357b3ba79c789587e1ecdad376d893382d750ac3820bb8` | matched `input_sha256` |
| `input/Q_LOCK.md` | 6842 | `c4915b9c646f6b3b57f0d2bdffd1bd401358c4bf5e029dad1b7835b11355f501` | matched `report_sha256` |
| `input/Q_LOCK.json` | 384 | `9767f7c214af1d163fdb44dfa619fe5bedd0ce0cfcae08aa7eb121a3ad26d8d1` | self-hash matched |

`Q_LOCK.json` also had `verdict = MIXED` and `confidence = 0.91`. No scientific input was read before these checks passed.

**Input-explicit assumptions.** The state is binary and full support; the score has ordered values `L,M,H`; `X` and fresh review signal `R` are binary and strictly informative; all relevant score-signal cells have positive probability; `S,X,R` are conditionally independent given qualification; the initial rule accepts `H` and rejects `D={L,M}`; only the information partition differs across regimes; value, cost, signal laws, initial/final rules, and review technology are fixed; non-appellants stay rejected; the final rule does not infer `X` from appeal; there is a positive constant per-appeal burden but no capacity, rationing, congestion, optimization, or endogenous review.

The analysis used no network, subagent, directory-external input, engine, canonical state, or canonical write. All writes are confined to `C:\tmp\nd1\report`.

## 2. Notation and maintained assumptions

Let qualification be `Q in {0,1}`, with `pi=Pr(Q=1) in (0,1)`. For `s in {L,M,H}`, `x in {0,1}`, and `r in {0,1}`, write

```text
p_q(s) = Pr(S=s | Q=q),
a_q(x) = Pr(X=x | Q=q),
rho_q(r) = Pr(R=r | Q=q).
```

Conditional independence gives joint mass

```text
w_q(s,x,r) = pi_q p_q(s) a_q(x) rho_q(r),
pi_1=pi, pi_0=1-pi,
```

and pre-review cell mass `w_q(s,x)=pi_q p_q(s)a_q(x)`. All these primitive probabilities relevant below are strictly positive. Score posterior ordering is equivalently the ordering of `lambda_s=p_1(s)/p_0(s)`; orienting the informative binary labels so that 1 is favorable gives `kappa_1>kappa_0`, where `kappa_x=a_1(x)/a_0(x)`, and `eta_1>eta_0`, where `eta_r=rho_1(r)/rho_0(r)`.

Let the general fixed final rule be `phi(s,r) in [0,1]`, the conditional probability of final acceptance following an appeal. This includes deterministic rules as the special case `{0,1}`. Define

```text
g_q(s) = sum_r phi(s,r) rho_q(r).
```

The applicant's value is `v>0`, cost is `c>0`, and `tau=c/v>0`; indifference is resolved in favor of appeal.

**Additional assumptions used only in the labelled example below.** The example takes `phi(s,r)=r`. This is not inferred from the input and is not used to resolve the final verdict.

## 3. Posterior and appeal formulas

Under score disclosure, the qualification posterior and appeal-success probability in cell `(s,x)`, `s in D`, are

```text
mu_sx = [pi p_1(s)a_1(x)] /
        [pi p_1(s)a_1(x)+(1-pi)p_0(s)a_0(x)]
      = [pi lambda_s kappa_x] /
        [1-pi+pi lambda_s kappa_x],

T_sx = [pi p_1(s)a_1(x)g_1(s)
        +(1-pi)p_0(s)a_0(x)g_0(s)] /
       [pi p_1(s)a_1(x)+(1-pi)p_0(s)a_0(x)]
     = g_0(s)+[g_1(s)-g_0(s)]mu_sx.
```

Thus `A^T_sx = 1{T_sx >= tau}`.

Under decision-only disclosure, a rejected applicant knows `D` and `x` but not `s`. The exact success probability is

```text
B_x = {sum_q pi_q a_q(x) sum_{s in D} p_q(s)g_q(s)} /
      {sum_q pi_q a_q(x) sum_{s in D} p_q(s)},
```

and `A^B_x=1{B_x >= tau}` applies to both hidden score cells. The two formulas correctly allow the fixed final rule to depend on the hidden institutional score.

Consequently, disclosure changes a positive-probability cell **if and only if**

```text
there exist s in {L,M}, x in {0,1} such that
(T_sx-tau)(B_x-tau) < 0,
```

away from boundary equalities. With the stated tie rule, the exact weak-boundary version is `1{T_sx>=tau} != 1{B_x>=tau}`. This is a proved necessary-and-sufficient behavioral characterization, not a claim that the input pins down which side obtains.

## 4. Open-region proof or obstruction

For any fixed admissible `phi` and full-support primitive point at which one of the strict crossing inequalities above holds, the same crossing persists on a nonempty open neighborhood. The reason is analytic: `T_sx` and `B_x` are continuous rational functions of the interior primitive probabilities and `tau`, and their denominators are strictly positive. Strict score and signal likelihood-ratio orderings are themselves open restrictions. Hence strict crossings, not equality surfaces, generate open regions.

There is nevertheless a decisive obstruction in the supplied frame: `phi` is not specified or restricted enough to establish that the actual fixed rule admits such a crossing. Two admissible cases demonstrate identification failure.

1. If `phi(s,r)=0` for every `(s,r)`, then every success probability is zero. Since `tau>0`, nobody appeals in either regime, so no selection-change region exists.
2. Under the **additional illustrative assumption** `phi(s,r)=r`, take `pi=0.5`; score probabilities `(p_1(L),p_1(M),p_1(H))=(0.2,0.3,0.5)` and `(p_0(L),p_0(M),p_0(H))=(0.5,0.3,0.2)`; `Pr(X=1|Q=1)=0.8`, `Pr(X=1|Q=0)=0.2`; `Pr(R=1|Q=1)=0.8`, `Pr(R=1|Q=0)=0.2`; and `tau=0.30`. All probabilities are interior, the score likelihood ratios are `0.4<1<2.5`, and both binary signals are strictly informative. The relevant success probabilities are

```text
T_L0 = 0.254545...,  T_M0 = 0.320000...,  B_0 = 0.281081...,
T_L1 = 0.569231...,  T_M1 = 0.680000...,  B_1 = 0.628571....
```

Only `(M,0)` changes, entering appeal under disclosure. Strict-inequality margins are

```text
tau-B_0 = 0.0189189...,
T_M0-tau = 0.0200000...,
tau-T_L0 = 0.0454545...,
min(T_L1,T_M1,B_1)-tau = 0.2692307....
```

Their positive minimum, approximately `0.0189189`, plus continuity proves that this illustrative point lies inside a nonempty open selection-change region. This witness proves possibility for that added rule, not existence for the unspecified rule in the input.

**Proved conclusion.** The maintained class contains both robust degeneracy and robust selection change. The missing final-rule choice prevents a rule-uniform answer and cannot be filled in without a researcher choice.

## 5. Beyond-enumeration test

The primitive reduction is low-dimensional. Treatment beliefs depend on the signal laws through the product `lambda_s kappa_x` and the rule through the two numbers `g_0(s),g_1(s)`. The pooled benchmark depends on the two score aggregates

```text
d_q = sum_{s in D} p_q(s),
h_q = sum_{s in D} p_q(s)g_q(s),
```

because `B_x=[pi a_1(x)h_1+(1-pi)a_0(x)h_0]/[pi a_1(x)d_1+(1-pi)a_0(x)d_0]`. Thus the sufficient statistics are `{lambda_s kappa_x,g_0(s),g_1(s)}` for disclosed cells and `{d_q,h_q}` for pooling, rather than an unexplained four-cell table.

If the extra restriction `g_1(s)>g_0(s)` holds, `T_sx` is increasing in posterior odds `lambda_s kappa_x`; if `g_1(s)<g_0(s)`, the ordering reverses; and if equality holds, qualification beliefs do not affect success at score `s`. These are genuine posterior-ordering statements, but the input does not impose the sign or score invariance of `g_1(s)-g_0(s)`. Strict informativeness of `R` alone is insufficient because an unrestricted fixed `phi` may ignore or reverse `R`.

This reduction and the exact selection decomposition below go beyond bare enumeration. Still, without a final-rule restriction they characterize a family rather than settle which economic ordering governs the proposed object. The economic mechanism is information-refinement-induced self-selection; the possible theoretical contribution would be a theorem under an approved rule restriction. Those are distinct from the mathematical fact that a finite set of indicators changes at thresholds.

## 6. Outcome-vector decomposition

Let `Delta A_sx=A^T_sx-A^B_x` and sum only over `s in D`, `x in {0,1}`. Exact treatment-minus-benchmark deltas are

```text
Delta V   = sum_{q,s,x} w_q(s,x) Delta A_sx                 (appeal volume),
Delta K   = sum_{s,x} w_1(s,x) Delta A_sx                   (qualified appellants),
Delta C   = sum_{s,x} w_1(s,x) g_1(s) Delta A_sx            (corrected qualified rejections),
Delta U   = sum_{s,x} w_0(s,x) g_0(s) Delta A_sx            (review-induced unqualified acceptances),
Delta PB  = b Delta V, b>0                                  (total processing burden).
```

If `V^j>0`, qualified-appellant composition is `theta^j=K^j/V^j`, with exact difference

```text
theta^T-theta^B = [Delta K-theta^B Delta V]/V^T.
```

The per-appeal burden itself remains exactly `b` in both regimes; only its total changes.

There is non-arbitrary content without welfare weights. If `Delta A_sx>=0` in every cell (disclosure only adds appeals), then `Delta V,Delta K,Delta C,Delta U,Delta PB` are all weakly nonnegative; the reverse holds if disclosure only removes appeals. With positive cell masses, any changed cell makes `Delta V` and `Delta PB` strict; classification components are strict when the corresponding `g_q(s)>0`. This exposes a classification conflict: added appeals can simultaneously increase corrected qualified rejections and unqualified acceptances. Composition has no general sign because its numerator is `Delta K-theta^B Delta V`.

When some cells enter and others leave, unrestricted admissible cell masses and `g_q(s)` can reverse the signs of every aggregate above except the accounting identity `Delta PB=b Delta V`; no welfare weighting repairs a primitive sign theorem. Thus the robust results are the exact weighted decomposition, the burden identity, the one-sided-selection monotonicity, and the correction/error conflict—not an aggregate welfare ranking.

## 7. Resource/frontier interpretation

With fixed `b`, no hard capacity, no rationing, no congestion, no optimization, and no endogenous review, the direct object is an **outcome-vector difference** between two fixed information regimes. As `tau` or primitives vary, these vectors trace a piecewise-defined **locus** whose jumps occur at the success thresholds. It is not a frontier in the strict feasible-set/optimization sense. Calling the two-regime comparison a classification-processing frontier would overstate the model.

At most two minimal researcher-approved reframes are available; neither is implemented here:

1. Specify a nontrivial final rule, minimally `phi(s,r)=r`, and present the result as an information-selection characterization and outcome locus.
2. If a true frontier is essential, add an explicit capacity allocation or review-optimization mechanism; that is a new model, not part of this probe.

## 8. Answers to Q1-Q4

**Q1 — open-region existence.** Conditional on a specified fixed final rule, a strict crossing `1{T_sx>=tau} != 1{B_x>=tau}` is necessary and sufficient and automatically defines an open primitive region; the example proves such a region can exist. Under the current rule-unspecified input, however, existence for the actual model cannot be proved because admissible rules also imply no appeals and no crossing.

**Q2 — beyond finite-cell enumeration.** Yes at the level of a family characterization: likelihood-ratio products, the aggregates `(d_q,h_q)`, posterior ordering conditional on the sign of `g_1-g_0`, and the exact selection decomposition explain the cells. No unconditional economic ordering is identified until the final rule is chosen or restricted.

**Q3 — non-arbitrary outcome content.** Yes conditionally: one-sided entry or exit gives joint weak monotonicity of volume, qualified-appellant mass, both classification counts, and burden, while added review can create a correction/error conflict; `Delta PB=b Delta V` always. General mixed entry/exit and appellant quality have no sign under the maintained unrestricted primitives.

**Q4 — resources and frontier.** The present object is an outcome-vector difference and, under parameter variation, a locus. Positive per-appeal burden alone does not create a strict frontier.

## 9. Verdict: PARK

`PARK` is required. Selection change is possible on a nonempty open region and the analysis has structure beyond a threshold table, so `KILL` is not justified. But the supplied input omits the decisive fixed final rule (or a restriction on it); admissible choices yield opposite nondegeneracy answers. Selecting a favorable rule here would violate the instruction not to make a new researcher choice. The missing human choice is: approve a specific nontrivial final rule, or approve a primitive restriction on `phi` strong enough to sign and separate the review-success probabilities.

## 10. Confidence and minimal next scientific action

**Confidence: 0.95.**

Minimal next scientific action: the researcher should approve exactly one final-rule specification/restriction. The smallest is `phi(s,r)=r` (accept exactly on favorable fresh review), after which the displayed open-region witness and likelihood-ratio characterization can be promoted from an illustrative conditional result to the maintained model. No capacity mechanism is needed unless the intended object is genuinely a frontier.

## 11. Tool-use and limitation declaration

Tools used were local PowerShell shell commands for exact reads, byte counts, hashes, JSON-field verification, and timestamping, plus `apply_patch` for report-only writes. Python was attempted only as a local standard-library calculator but was unavailable and read no scientific content; no package was installed. No numerical result is offered as a universal proof: the witness is paired with strict margins and continuity only to prove a nonempty open region under its explicitly added final-rule assumption. Universal and impossibility claims above are analytic. Network used: no. Subagents used: no. Outside-input reads: no. Econ Theorist engine invoked: no. Canonical writes: zero.
