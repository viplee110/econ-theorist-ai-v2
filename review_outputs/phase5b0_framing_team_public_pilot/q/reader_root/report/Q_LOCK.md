# Q-only Cold-Read Assessment

## 1. Research question

When does telling a rejected applicant whether the institutional score was low or middle, instead of revealing only that the applicant was rejected, change which rejected score–private-signal types appeal? Conditional on such a selection change, what happens to processing load and to the composition and classification consequences of reviewed cases when all decision and review rules remain fixed?

## 2. Exact benchmark and smallest departure

The exact benchmark is `decision_only`: the fixed initial rule accepts a high score and rejects low and middle scores; a rejected applicant observes only the pooled event `{low, middle}`, then observes the same binary private signal and decides whether to pay the same positive appeal cost under the same Bayesian threshold rule.

The smallest departure is `score_disclosure`: after the same rejection, the applicant additionally learns whether the rejected score was low or middle before observing the private signal and choosing whether to appeal. Nothing else changes—the prior and joint signal law, applicant value and cost, initial rule, review technology, final rule, institutional classification accounting, and per-appeal burden are held fixed.

## 3. Economic margin or force

The economic force is selection induced by a refinement of the applicant's information. Disclosure changes the posterior probability that an appeal will succeed in each score–private-signal cell; a common value-to-cost threshold can therefore split types that take the same action under the pooled rejection message. The nontrivial institutional margin is not information disclosure by itself but the resulting change in both appeal mass and appellant composition: additional or displaced appeals can alter total processing, qualified cases reaching review, corrected qualified rejections, and review-induced acceptances of unqualified applicants in different directions.

## 4. Central hidden assumption, degeneration risk, or failure condition

The central maintained assumption is a strict informational-separation experiment: disclosure affects only the rejected applicant's information and hence self-selection, while participation, signal laws, initial and final rules, review quality, processing technology, and institutional inference from appealing are all invariant. This excludes strategic signaling, endogenous review effort or standards, congestion, rationing, and feedback from the selected appeal pool. Those exclusions make the comparison clean, but they also carry much of its economic content.

The main degeneration risk is severe. With two rejected scores and a binary private signal, the exercise can collapse to ordering a small number of posterior review-success probabilities and listing the appeal-cost thresholds at which four finite cells switch actions. Full support, strict informativeness, positive costs, and a tie rule do not by themselves prevent that collapse; the tie rule matters only on threshold boundaries, not on nonempty open regions.

**Is the proposed contribution more than a mechanical finite-cell threshold exercise?** The framing alone does not yet establish that it is. It would become more than enumeration only if the primitive restrictions deliver an interpretable posterior ordering, a substantive selection decomposition, robust open-region comparative statics or bounds, or a low-dimensional sufficient statistic that explains the outcome-vector changes without merely tabulating cells. If disclosure changes no positive-probability cell on an open parameter region, or if the characterization is just those threshold crossings with unrestricted outcome weights, the frame degenerates on its own stated terms.

## 5. Bounded theoretical contribution if successful

The frame could support a deliberately narrow characterization: necessary and/or sufficient primitive signal and positive-cost conditions under which refining pooled rejection into low-versus-middle disclosure strictly changes the appeal set, together with an exact decomposition of the induced changes in appeal volume, qualified-appellant selection, corrected qualified rejections, unqualified review-induced acceptances, and processing burden. A useful result could identify when volume and composition move together or conflict and describe a classification–processing outcome locus under fixed rules. It could not, without additional structure, establish aggregate welfare, optimal disclosure, optimal capacity, or a general policy ranking.

## 6. Claims assumed without support

No definite result sign, welfare ranking, policy recommendation, empirical validation, formal validation, novelty claim, or venue claim is asserted. The text appropriately presents behavioral change and an economically meaningful characterization as questions or conditional possibilities rather than established findings.

Two phrases still require discipline in any later theorem. First, the existence of nonempty open parameter regions with changed appeal behavior is a required nondegeneracy condition, not something demonstrated here. Second, “classification-processing frontier” is presently only a proposed interpretation: with one fixed treatment comparison, fixed rules, and no capacity or optimization problem, the frame directly identifies an outcome-vector difference, not automatically a frontier or welfare tradeoff. Nor does the framing itself establish any monotone improvement in appellant quality or classification.

## 7. Cold-reader recoverability

Yes. A cold reader can recover the research question, the unique `decision_only` benchmark, the sole information-partition delta, the timing, the appeal-choice margin, the institutional outcome vector, and the exclusions without reconstructing missing context. The exact algebra of the final review-success probability and final decision rule is not supplied, so a theorem cannot yet be reconstructed, but that omission does not obscure the Q-level comparison or its bounded scope.

## 8. Q-only verdict

**Verdict: MIXED**  
**Confidence: 0.91**

The frame is unusually explicit about its benchmark, one-variable treatment, timing, maintained invariances, prohibited claims, and kill condition. It is scientifically recoverable and honestly scoped, and the selection-versus-volume distinction is economically intelligible. The reservation is substantive rather than presentational: in the stated smallest finite environment, the prospective characterization may be no more than posterior ordering plus cell-by-cell threshold arithmetic. Because the input identifies but does not resolve that nondegeneracy test, a cold reader cannot yet judge the bounded contribution as fully sharp enough for `PASS`; neither is the question missing or incoherent enough for `FAIL`.
