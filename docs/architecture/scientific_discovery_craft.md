# Scientific Discovery and Research-Craft Extension

Status: evidence-informed design; scheduled after the first minimal
research-team pilot and inactive until incremental evaluation

Scope: pure and applied microeconomic theory, industrial-organization theory,
information economics, game theory, market and mechanism design, networks, and
formal political economy. This design does not add empirical, econometric, or
macro workflows.

## 1. Decision

V2 should add an evidence-backed **research-move library** for discovering
questions, constructing models, isolating mechanisms, forming conjectures, and
explaining results. It should not create named-economist personas, a journal
imitation engine, a top-100 prestige list, or another long sequence of
mandatory routes.

The existing theory route graph, canonical objects, promotion gates, and
profile/craft system remain the architecture. A research move is a small,
optional method card selected inside an existing route. Its scientific output
is stored in existing objects such as `ResearchQuestion`, `BenchmarkSet`,
`PrimitiveGraph`, `MechanismHypothesis`, `PredictionRegister`, `ExampleSuite`,
`FormalizationMap`, `ClaimGraph`, and `AssumptionMap`. The move itself does not
become a second research-state system.

`ResearchMove` is deliberately separate from the implemented Phase 4
`CraftMove`. The current `CraftMove` corpus repairs a diagnosed local
reader/exposition problem after the science exists; a `ResearchMove` helps
produce or challenge the upstream science. Overloading one schema would let a
writing repair masquerade as a solution to a question, mechanism, or model
defect.

The governing principle is:

> Keep exploration wide and promotion strict. Constrain claims, proof status,
> source fidelity, and canonical promotion; do not constrain imagination by
> forcing every project through the same recipe.

## 2. What the evidence says

The initial review covered 13 published pure-theory papers in the five
general-interest journals, including Econometrica, 12 published pure-theory papers in leading
field/theory journals, and public research-method material from classic and
contemporary theorists. Final papers do not reveal their authors' complete
historical discovery process, so paper-based conclusions below are explicitly
reconstructions of scientific design rather than biographical claims.

The most stable findings are:

1. Strong abstract theory normally rests on a retellable economic question,
   an exact benchmark, a small decisive example, and a named causal mechanism.
   Abstraction is valuable when it compresses or transfers an insight, not
   when it merely enlarges the state space.
2. The benchmark is the paper's coordinate system. A useful contribution can
   often be expressed as benchmark plus one economically meaningful change,
   followed by the first link in the benchmark reasoning that breaks.
3. Binary, two-agent, two-period, and other tiny cases are discovery
   laboratories. They expose signs, cutoffs, equivalences, counterexamples, and
   hidden feedback before they become exposition examples.
4. Many important advances are representation shifts: signals become
   posteriors, matching becomes cutoffs, histories become continuation values,
   or a complicated environment becomes a sufficient statistic or bound.
5. A mechanism should be recoverable as
   `primitive -> incentive/information change -> strategic response ->
   allocation -> consequence`. A proof citation is not a substitute for this
   economic chain.
6. Theorem order should follow economic understanding. The main text carries
   the theorem spine, decisive examples, mechanism, and boundaries; technical
   breadth that does not change the reader's update belongs in an appendix.
7. General-interest and field-frontier theory share the same correctness and
   intuition floor. Their main difference is intellectual radius: a Top-5
   paper more often supplies a portable principle, representation, equivalence,
   or tool; a field-top paper may answer one canonical institutional question
   more deeply.
8. Generality has a return on investment. A wider theorem is valuable only if
   it expands the audience, transfers the mechanism, supports another serious
   application, reveals a boundary, or creates a reusable tool.
9. Intuition is part of the scientific result. If a cold theorist cannot use
   the explanation to predict a nearby case, the paper has not yet recovered
   its mechanism, even if the formal statement is correct.
10. An out-of-corpus meta-evaluation of AI-generated game-theory questions
    motivates a useful but non-promoting **setup-burden diagnostic**: ask
    whether each additional primitive or modeling detail creates new economic
    reasoning, a boundary, or a transferable mechanism. Because that study is
    an empirical evaluation rather than a theory paper, it cannot support a
    `ResearchMove` or theoretical conclusion. The diagnostic is a blinded
    semantic judgment, not a ratio of words, tokens, symbols, equations, or
    theorem labels, and it must not penalize first-order institutional
    complexity.

## 3. Distill methods, not scholars

A scholar is a source-discovery node, not a runtime role. V2 must not instruct
an agent to "think like Acemoglu," "write like Armstrong," or imitate a named
author's voice. It may derive a functional move from public evidence while
retaining attribution, uncertainty, and non-applicability outside the writer's
context.

Each observation records orthogonal evidence fields:

- `source_type`: interview, autobiography, method essay, research statement,
  retrospective, published paper, working paper, or conference material;
- `claim_relation`: `explicitly_stated` by the researcher or
  `inferred_reconstruction` from the final scientific design; and
- `bias_flags`: retrospective narration, published-outcome selection,
  coauthor-cluster dependence, or other limits on transfer.

The display shorthands `DIRECT`, `METHOD`, and `INFERRED` may summarize these
fields in a report, but they are not mutually exclusive storage categories.
An inferred reconstruction is never reported as the author's own stated
process.

Conflicting methods are preserved rather than averaged away. Examples include
large-question search versus one precise market friction, maximal
simplification versus retaining first-order complexity, Bayesian versus robust
design, and exact characterization versus useful near-optimal structure. A
move card states when each side is appropriate.

## 4. Contemporary microeconomic-theory evidence policy

The long-run production-quality research corpus should explore roughly 40--60
methodologically diverse active scholars and 100--200 public primary sources,
not the top 100 of a ranking. This coverage target is not a prerequisite for
the first useful research-team pilot: the first source-audited batch may use
about eight scholars or twenty primary sources and should expand only when it
adds a genuine move or boundary. A 48-scholar, roughly 132--138-source first pass
is one planning midpoint, not an acceptance target. The initial weighting is:

| Source date | Curation weight |
|---|---:|
| 2022--2026 | 1.0 |
| 2015--2021 | 0.8 |
| 2010--2014 | 0.5 |
| 2005--2009 | 0.3 |
| Before 2005 | 0.1, historical foundation only |

Recency affects which evidence is sampled first; it does not make a new claim
truer than an old one. Entry into the high-weight scholar pool normally
requires relevant theory activity in 2021--2026. Macro, empirical, and
econometric outputs are excluded even when produced by an admitted scholar.

Daron Acemoglu and Mark Armstrong are high-priority seeds for different
reasons. Acemoglu's public interview explicitly supports question generation,
ambition built on incremental science, and repeated checking. Separate
`inferred_reconstruction` cards from his micro theory may study endogenous
institutions, networks, and feedbacks. Armstrong's IO record, including recent
and continuing work, contributes inferred market-operation candidates
involving search order, consideration sets, captive buyers, information,
multibrand pricing, and platforms. Their coauthors help discover adjacent
active theorists, but collaboration is not itself evidence of a distinct
method.

The anti-echo audit asks whether:

- either seed's one- and two-hop network approaches 15% of the core;
- the two seed networks together approach 30%;
- the share outside both two-hop networks falls below roughly 40%;
- one coauthored paper or one paper family counts as one evidence lineage;
- one institution approaches 12.5% of the scholar sample;
- a supported general move normally needs two independent research circles,
  or one explicit method source plus one independent paper instance; and
- journals and conferences are sampled independently of the coauthor graph,
  including Econometrica, Theoretical Economics, JET, GEB, AEJ Micro, RAND,
  JPE Micro, ACM EC, SAET, and EARIE.

These percentages are curation warnings, not runtime quotas or scientific
truth. A curator may depart from them with a short coverage rationale;
lifecycle, field, method, and contradiction coverage plus marginal saturation
control when sampling stops.

### Contemporary microeconomic-theory discovery and monitoring pool

This is a discovery pool, not a ranking, prestige list, or invitation to
imitate a scholar's personality or prose. Scholars are entry points to public
evidence. Only paper-level, claim-level research moves may be extracted.

An `active_node` has at least one qualifying public theory output in
2021--2026. A `current_theory_edge` is a publicly verifiable coauthored
microeconomic, IO, game-theoretic, mechanism-design, market-design, or formal
political-economy output dated 2005--2026. Macroeconomic, empirical,
econometric, and policy-only outputs do not create theory edges. Neither do
acknowledgements, advising, institutional proximity, or conference
participation. Older collaborations are stored as `historical_edge`.

`outside_checked` means that no qualifying path of length at most two has been
verified in the bounded graph. It is not a claim that no lifetime intellectual
or collaboration path exists.

The active 55-scholar pool is organized by research function:

- institutions, networks, formal political economy, and data-market
  mechanisms: Daron Acemoglu [A0], Asuman Ozdaglar [A1], Alexander Wolitzky
  [A1], Georgy Egorov [A1], Matthew O. Jackson [A1], Ali Makhdoumi [A1],
  Benjamin Golub [A2 via Jackson], Mohammad Akbarpour [A2 via Jackson], and
  Gabriel Carroll [A2 via Egorov];
- IO, search, platforms, data, and competition: Mark Armstrong [M0], John
  Vickers [M1], Jidong Zhou [M1], Julian Wright [M1], Andrew Rhodes [M2 via
  Zhou], Andrei Hagiu [M2 via Wright], Bruno Jullien [M2 via Wright], Chengsi
  Wang [M2 via Wright], Ran Spiegler, Dirk Bergemann, Alessandro Bonatti,
  Volker Nocke [M3/topic], Heski Bar-Isaac, Alexandre de Cornière, Özlem
  Bedre-Defolie, Nicolas Schutz, Greg Taylor,
  [Yongmin Chen](https://www.colorado.edu/faculty/chen-yongmin/),
  [Michael D. Whinston](https://economics.mit.edu/people/faculty/michael-whinston),
  [Simon P. Anderson](https://economics.virginia.edu/people/simon-anderson),
  [Luís Cabral](https://www.stern.nyu.edu/faculty/bio/luis-cabral), and
  [Patrick Rey](https://www.tse-fr.eu/people/patrick-rey?tab=bio-and-research-interests);
- information, mechanisms, learning, and communication: Annie Liang, Laura
  Doval, Vasiliki Skreta, Shengwu Li, Alessandro Pavan, Navin Kartik, Elliot
  Lipnowski, Xiaosheng Mu, Emir Kamenica, Stephen Morris, Benjamin Brooks,
  Piotr Dworczak, and Alex Smolin;
- dynamic games, contracts, and reputation: Takuo Sugaya [A2 via Wolitzky],
  Marina Halac, Johannes Hörner, Harry Pei, Doron Ravid, and Mira Frick; and
- matching, market design, and implementation: Itai Ashlagi, Yeon-Koo Che,
  Fuhito Kojima, Eduardo Azevedo, and M. Bumin Yenmez.

These five lanes are the general theory-scholar pool: 9 nodes in institutions,
networks, and formal political economy; 22 in IO, search, platforms, and
competition; 13 in information, mechanisms, learning, and communication; 6 in
dynamic games, contracts, and reputation; and 5 in matching, market design,
and implementation. Within the IO lane, Anderson covers product
differentiation and price dispersion; Cabral covers firm and industry
dynamics; Chen covers switching, search, and dynamic pricing; and Whinston
and Rey deepen vertical-contract and exclusion coverage. They sit inside the
same pool as the original search, platform, data, and competition scholars.

In the original 50-node graph audit, names without an A/M path tag are
`outside_checked`. Thirty-two nodes are outside both seeds' verified two-hop
networks or are explicit third-hop/topic nodes. Sixteen are qualifying
non-seed one/two-hop nodes. The five later IO nodes await the next graph-label
and provenance refresh and are not included in these path statistics.
The latter concentration deliberately triggers the seed-network curation
warning above even though 64% of the original pool lies outside the verified
two-hop graphs. These are pool-coverage statistics, not runtime quotas;
corpus curation and runtime sampling should rotate and downweight seed-network
scholars rather than treating all 55 names as equally frequent inputs.

Monitoring priority is scholar-owned paper and CV pages, then official
department and working-paper feeds, then official journal or conference pages
for version confirmation. Search indexes are discovery aids, not canonical
evidence. Every graph edge stores `(source_a, source_b, title, year,
theory_scope, edge_type, evidence_url, checked_at)`. Policy, empirical, macro,
and econometric connections are retained as non-counting edge types rather
than silently converted into theory edges. For example, a public Bonatti--Zhou
policy connection is a `policy_edge`, not a theory coauthorship edge; Volker
Nocke is M3/topic rather than M2; and Annie Liang remains `outside_checked`
rather than being pulled inward by an unverified Acemoglu--Fudenberg edge.

### Foundational anchors

Two foundation-role anchors preserve intellectual ancestry without,
in that role, receiving the recency or collaboration-network weight of active
discovery nodes:

- [Jean Tirole](https://www.tse-fr.eu/people/jean-tirole), for the integrated
  IO language connecting market power, dynamic competition, vertical
  relations, regulation, and two-sided markets; and
- [Paul Klemperer](https://www.nuffield.ox.ac.uk/people/profiles/paul-klemperer/),
  for switching costs, dynamic competition, auctions, and the discipline of
  moving between simple theory and institutional design.

Thus the curation structure is **55 active contemporary nodes + 2
foundation-role anchors**, not 57 equally weighted scholar personas. The
foundation layer is used to recover canonical benchmarks, mechanism ancestry,
and known failure modes, helping
the system avoid rediscovering an old result under new notation. It is not a
style-transfer library. Xavier Vives is the first reserve if later coverage
audits find product-market rivalry or strategic complementarities too thin;
reserve status is a curation note, not a lower assessment of the scholar.

## 5. Research-move representation

Each candidate move is a compact, versioned, copyright-safe derived card:

```text
move_id and version
lifecycle stage and compatible existing routes
functional name
trigger: the observable research problem that makes the move useful
operation: what to vary, compare, construct, or test
required current semantic inputs
expected existing-object output
success diagnostic
failure modes and anti-patterns
non-applicability and conflicting moves
semantic-input requirements and explicit non-applicability
source_type, claim_relation, and bias-flagged evidence refs
paper-family and coauthor-cluster independence ids
recency tier, transfer confidence, and curator decision
```

Before G4, theory mode, field, candidate archetype, and ambition may rank or
annotate otherwise applicable moves but may not exclude them. Eligibility is
limited to current semantic inputs and explicit non-applicability. After G4,
an actually locked archetype may filter incompatible moves. Journal overlays
never enter the discovery selector.

Cards store citations, structured functional summaries, source hashes when
lawful, and short compliant excerpts only when indispensable. They do not
store full copyrighted papers, reusable source sentences, signature diction,
or hidden reasoning traces. The generator sees the function-only projection;
source identities and evaluation holdouts remain outside its writing context.

## 6. Initial move library

These are candidate moves for evaluation, not mandatory requirements.

A candidate enters `ResearchMove` only if it adds a triggered search
transformation or branch operation that the existing route contract does not
already require. Restating an acceptance criterion as a card is rejected: it
adds prompt burden without adding discovery capacity.

The exact wedge and benchmark, formulation completeness, primitive
classification, rival mechanisms, prediction freeze, tiny examples,
ablations, boundary and counterexample work, mechanism-chain recovery,
claim/proof/interpretation separation, G1--G5 investment decisions, and
reader-facing theorem/appendix design are already owned by routes, validators,
gates, or the Phase 4 `CraftMove` system. They remain scientific floors or
writing craft, not `ResearchMove` entries. The semantic setup-burden check is
an evaluator diagnostic, not a move or promotion rule.

The initial genuine search-expander candidates are:

- **Different-Implementation Question:** while reading an existing result, ask
  what changes under a substantively different primitive, representation,
  timing, or institution rather than a cosmetic extension.
- **Question Reframer:** change the unit of analysis or the object being
  explained--for example action to information, prediction to welfare, or
  individual behavior to system outcome--while preserving the original
  economic tension.
- **Tractable Proxy Pivot:** move to a nearby environment that retains the
  target tension when the inherited problem is intractable; record what the
  proxy no longer represents.
- **Market-Operation Primitive:** reconstruct what participants actually see,
  remember, search, consider, contract on, and can commit to, then replace one
  unrealistic background convention with the smallest operative friction.
- **Institutional Feedback Deepener:** move one layer below a policy or rule by
  endogenizing who enforces it, who constrains the enforcer, or how today's
  rule changes future power, information, or participation.
- **Residual-Case Hunter:** use numerical or flexible predictive tools to find
  synthetic cases where a simple model fails, then search for a portable
  economic mechanism explaining the residual. The pattern remains a
  conjecture until proved.
- **Representation Hunter:** restate the problem through beliefs, cutoffs,
  continuation values, sufficient statistics, dual variables, or another
  natural representation; retain the change only when it reveals or compresses
  the economics.
- **Robustness-Axis Switch:** replace an arbitrarily fixed information,
  action-set, preference, or environment specification with a clearly defined
  class and ask which prediction survives across that uncertainty.
- **Near-Optimal Structure Pivot:** when exact optimization preserves opaque
  higher-order detail, characterize a transparent near-optimal solution first
  and use it to identify the structure an exact theorem would need. This is
  also the exception to automatic minimalism when first-order complexity is
  economically load-bearing.
- **Computational Structure Probe:** solve small finite or numerical versions
  to conjecture a cutoff, dual object, equivalence, or functional form; export
  only the conjectured structure and its tested domain to proof routes.
- **Analogical Structure Transfer:** map primitives and strategic arrows from
  a distant setting, then make the first mapping failure--not shared
  vocabulary--the candidate source of a new model or boundary.
- **Nonconvex Branch Mutation:** after repeated local repair, change one deep
  dimension--primitive, timing, information, objective, solution concept,
  boundary, or representation--and preserve the abandoned branch rather than
  blending incompatible repairs.

## 7. Integration with the existing route graph

No new route is required for the first release. A route-aware selector offers
two to four applicable moves; the generator may use zero to two and records a
short decision rationale rather than a private chain of thought.
Each runtime projection should remain about 80--120 words and contain no
scholar name, paper prose, prestige signal, or source-ranking score.

| Existing capability | Candidate search-expander moves |
|---|---|
| `frame.question_and_benchmarks` | Different-Implementation Question; Question Reframer; Tractable Proxy; Market-Operation Primitive |
| `decompose.primitives` | Market-Operation Primitive; Institutional Feedback Deepener; Robustness-Axis Switch |
| `tournament.mechanisms` | Representation Hunter; Analogical Structure Transfer; Institutional Feedback Deepener |
| `lab.micro_examples_and_ablations` | Residual-Case Hunter; Computational Structure Probe; Nonconvex Branch Mutation |
| `tournament.implementations` | Representation Hunter; Tractable Proxy; Near-Optimal Structure Pivot |
| `discover.claims_and_boundaries` | Computational Structure Probe; Robustness-Axis Switch; Nonconvex Branch Mutation |
| `audit.assumptions_generality_and_absorption` | Robustness-Axis Switch; Analogical Structure Transfer; Near-Optimal Structure Pivot |

The engine remains the sole route and WorkPacket owner. The local IDE skill
does not contain this library. When activated later, the selected move ids,
versions, and source release belong in the route context/provenance; scientific
claims continue to live only in the normal canonical entities. Evaluators
judge whether the resulting object is sharper, more correct, and more
transferable, not whether an agent mechanically followed a named move.

### V1 inheritance

This is not a clean-slate replacement for v1. It uses the most useful v1
research disciplines while retaining their current v2 typed owners:
Scientific Taste and Nugget, Primitive Hunter, Nonconvex Branch Generation,
Micro-Example and Example-to-Theory, Model Tournament, Heuristic Derivation,
Generality/Occam, Absorption, and Style Anchors. Only an unimplemented search
operation becomes a new optional card; existing route disciplines and Phase 4
Style Anchors remain where they are. In particular,
`V1-NONCONVEX-SEARCH` remains `optional_not_migrated` in the migration ledger;
route-local Question Reframer, Representation Hunter, Tractable Proxy, and
Nonconvex Branch Mutation moves provide a lightweight way to recover that
search capacity without reviving v1's long prompts, fixed quotas, or duplicate
workflow state. V1 disciplines already enforced by current routes remain route
contracts rather than duplicated move cards.

## 8. Top-5 and field-frontier control

Target control is a soft assessment profile over the same discovery space. It
must not make a journal overlay silently change the model or suppress ideas.
Before G4, move eligibility depends only on current semantic inputs and an
explicit non-applicability rule. Theory mode, field, candidate archetype, and
ambition may reorder or annotate candidates and evaluate their eventual
radius, but cannot filter a move out. A locked post-G4 archetype may filter
incompatible moves; a journal overlay has no discovery-selector authority.

| Dimension | General-interest / Top-5 theory | Field-frontier theory |
|---|---|---|
| audience radius | consequential to economists beyond the origin field | decisive for a mature field's central question |
| benchmark breadth | often connects two or more canonical conversations | one canonical benchmark plus closest substitutes may suffice |
| preferred result shape | portable principle, representation, equivalence, tool, or exceptionally compressed theorem | deep characterization, comparative statics, design, welfare, or policy for the field |
| applications | demonstrate transfer across settings when that is the contribution | one institution may be treated deeply |
| abstraction budget | spend only to obtain portability or conceptual reuse | spend only to solve the field problem faithfully |
| generalization threshold | must enlarge intellectual radius | must improve completeness, robustness, or field relevance |

Both profiles retain the same noncompensatory floor: exact question and
benchmark, correct model and solution concept, real proof status, honest
novelty and scope, naturalness scrutiny, mechanism recovery, decisive examples
or counterexamples, and a reader-transferable explanation. A strong
field-frontier result must not be rhetorically relabeled as general interest;
the system should instead report the current radius and the smallest genuine
scientific change that could enlarge it.

## 9. Incremental validation plan

This extension does not justify rerunning Phase 1--4 merely because a design
document or source card changes. Validation scales with the behavior changed.

1. **Source and derivation audit.** Check source type, claim relation, bias
   flags, paper-family and coauthor independence, dates, theory-only admission,
   copyright-safe projection, attribution, contradictions, and
   non-applicability.
2. **Micro A/B screening.** Begin with six high-leverage moves on five to ten
   short research situations each. Preregister one primary scientific outcome
   and a small set of harm checks per move. Hold the generator model, budget,
   and paired seed state fixed; compare no move, optional route-selected move,
   and forced move. The forced arm diagnoses harm and is not the intended
   product.
3. **Output measures.** Blindly assess the preregistered outcome plus relevant
   harms such as critical semantic error, lost idea diversity, or added expert
   editing time. Supporting measures may include question sharpness, distinct
   useful mechanisms, decisive examples, primitive/endogenous distinctions,
   counterexample survival, nearby-case transfer, and the semantic setup-burden
   diagnostic. Length, token count, theorem count, notation count, and
   confidence are never success measures.
4. **Held-out paired replication.** Screening can reject a move but cannot
   justify default activation or a quality claim. Replicate the preregistered
   primary outcome and harm checks on inaccessible paired seeds. If forced use
   performs worse, the result supports optional routing rather than deletion.
5. **Source-isolated cases.** Include two or three classic mechanisms plus one
   genuinely new project question. Hiding papers and answer keys does not erase
   pretraining knowledge, so this is not called knowledge-blind. Use renamed
   primitives, parameter/timing counterfactuals, synthetic isomorphs, and
   contamination probes; classic cases mainly test mechanism reconstruction,
   while new cases test discovery.
6. **Experimental end-to-end pilot.** After source audit, an explicitly
   researcher-authorized, non-default move set may enter a declared pilot
   WorkPacket before held-out replication so that real product use can expose
   missing triggers and harms. It carries no quality claim and must not expand
   the whole corpus and run a full-paper experiment simultaneously.
7. **Activation rule.** A move becomes eligible for automatic default
   selection only after the held-out paired replication and experimental
   end-to-end pilot support its primary outcome with no critical-error increase
   or material collapse in idea diversity. Source-audited opt-in experimental
   use is not default activation.
8. **Regression scope.** Corpus/data-only changes receive schema, hash,
   isolation, retrieval, and focused scientific tests. WorkPacket selection or
   evaluator changes receive affected-route and bridge tests. Only changes to
   canonical schemas, navigation, gates, or state invalidation require the
   corresponding full-history regression.

## 10. Delivery sequence

The first real research-team pilot should precede corpus expansion so that
observed question, model, proof, and editing failures determine which methods
deserve early retrieval. The smallest sound implementation is:

1. freeze this design and the evidence taxonomy;
2. curate one small versioned development batch in
   `craft/research_corpus.v1.json`, outside evaluation holdouts;
3. source-audit the batch and expose a small set only in an explicit opt-in
   research-team pilot;
4. run offline micro A/B screening on the moves that address observed pilot
   failures;
5. replicate promising effects on held-out paired, source-isolated, and
   genuinely new cases;
6. promote only the supported two-to-four-move menus to automatic selection in
   existing WorkPackets; and
7. expand coverage only when the marginal source adds a new move, a real
   boundary, a contradictory method, or a previously uncovered field.

After source audit, a disabled-by-default experimental selector and compact
projection may be added to support the opt-in pilot. Automatic route selection
and production package-resource wiring require positive held-out replication
and the experimental end-to-end evidence. Neither mode adds a canonical
entity, schema, Decision, gate, route, or navigation state; the WorkPacket's
existing compiled-context hash supplies run provenance.

One practical exploration cadence uses batches of about eight scholars or
twenty sources. An initial saturation signal is two consecutive batches with
fewer than two genuine new moves per batch, no material lifecycle or intended
micro/IO field gap, and mostly repeated triggers and boundaries. This is a
curation judgment, not a sample-size acceptance quota. A genuine move must
specify a trigger, an output, a success test, and a non-applicability condition.
If the project chooses active maintenance, an optional quarterly scan can
check public work from the previous 24 months and an annual release can
rebalance institutions, geography, career stage, fields, and research styles.

## 11. Initial primary-source anchors

The first evidence pass includes:

- [Daron Acemoglu's Nobel interview](https://www.nobelprize.org/prizes/economic-sciences/2024/acemoglu/1722488-interview-transcript/), which directly discusses idea byproducts, ambition built on incremental science, failure, and repeated checking;
- [Mark Armstrong's research record](https://sites.google.com/view/mark-armstrong/research), including continuing work on search, information, captive buyers, multibrand pricing, and platforms;
- [Armstrong and Zhou, Consumer Information and the Limits to Competition](https://www.aeaweb.org/articles?id=10.1257/aer.20210083), an inferred example of making consumer information an endogenous design object;
- [Armstrong and Vickers, Multibrand Price Dispersion](https://discovery.ucl.ac.uk/id/eprint/10221547/), a 2026 example built around consideration sets and discrete market-design counterfactuals;
- [Annie Liang, Using Machine Learning to Generate, Clarify, and Improve Economic Models](https://anniehliang.com/papers/pages/jel.html), which proposes predictive benchmarks, adversarial model probes, and interpretable hybrid models;
- [Golub, Liang, and Siniscalchi, Human or Machine?](https://anniehliang.com/papers/pages/turing-test.html), retained only as out-of-corpus meta-evaluation evidence for the non-promoting semantic setup-burden diagnostic, not as a theory or `ResearchMove` source;
- [Hal Varian, How to Build an Economic Model in Your Spare Time](https://people.ischool.berkeley.edu/~hal/Papers/how-OLD.pdf), a classic source for concrete questions, simple cases, and example-to-theory iteration;
- [Avinash Dixit, My System of Work (Not!)](https://www.princeton.edu/~dixitak/home/dixitwrk.pdf) and [The Art of Modeling](https://www.princeton.edu/~dixitak/Teaching/ArtOfModeling.pdf), which support incubation, plural methods, restart, and mechanism-preserving simplification;
- [Jean Tirole's Nobel biography](https://www.nobelprize.org/prizes/economic-sciences/2014/tirole/biographical/) and [Bengt Holmstrom's Nobel biography](https://www.nobelprize.org/prizes/economic-sciences/2016/holmstrom/biographical/), which provide direct retrospective evidence on formulation and separating essential forces from detail;
- [Dani Rodrik's Richmond Fed interview](https://www.richmondfed.org/publications/research/econ_focus/2014/q3/interview.cfm), [Ariel Rubinstein's Dilemmas of an Economic Theorist](https://arielrubinstein.tau.ac.il/papers/74.pdf), and [Alvin Roth's The Economist as Engineer](https://web.stanford.edu/~alroth/papers/engineer.pdf), which preserve important disagreements about model pluralism, fables, mapping, and implementation; and
- representative paper anchors already used by v2, including [Bayesian Persuasion](https://www.aeaweb.org/articles?id=10.1257/aer.101.6.2590), while further published-paper cards remain development evidence until independent corpus and holdout audits are complete.

## 12. Initial published-paper evidence set

The following table freezes the 25-paper theory sample behind the design
findings. Every move in the final column is inferred from the published
scientific architecture; it is not a claim about the authors' private research
history.

| Paper | Venue | Inferred scientific-design move |
|---|---|---|
| Kamenica and Gentzkow, [Bayesian Persuasion](https://www.aeaweb.org/articles?id=10.1257/aer.101.6.2590) | AER 2011 | Represent signal design as a distribution over posteriors; discover with a tiny application, then generalize geometrically. |
| Carroll, [Robustness and Linear Contracts](https://www.aeaweb.org/articles?id=10.1257/aer.20131159) | AER 2015 | Explain a widespread simple institution by removing one strong knowledge assumption from the canonical benchmark. |
| Haghpanah, Kuvalekar, and Lipnowski, [Buying from a Group](https://www.aeaweb.org/articles?id=10.1257/aer.20230914) | AER 2024 | Extract a small shared institutional structure from group-sale settings and let it determine the mechanism. |
| Esponda and Pouzo, [Berk–Nash Equilibrium: A Framework for Modeling Agents With Misspecified Models](https://onlinelibrary.wiley.com/doi/10.3982/ECTA12609) | Econometrica 2016 | Turn a conceptual inconsistency about misspecification into a formal distinction between objective environment and subjective model. |
| Doval and Skreta, [Mechanism Design with Limited Commitment](https://onlinelibrary.wiley.com/doi/10.3982/ECTA16846) | Econometrica 2022 | Find why a canonical revelation principle fails and change representation so the missing commitment problem becomes tractable. |
| Pycia and Troyan, [A Theory of Simplicity in Games and Mechanism Design](https://onlinelibrary.wiley.com/doi/10.3982/ECTA16310) | Econometrica 2023 | Replace vague cognitive cost with one measurable contingent-planning operation and use extreme horizons to expose it. |
| Azevedo and Leshno, [A Supply and Demand Framework for Two-Sided Matching Markets](https://www.journals.uchicago.edu/doi/10.1086/687476) | JPE 2016 | Use a continuum and cutoff-price representation to unify heterogeneity, market clearing, and comparative statics. |
| Lipnowski, Ravid, and Shishkin, [Persuasion via Weak Institutions](https://www.journals.uchicago.edu/doi/full/10.1086/720462) | JPE 2022 | Introduce one credibility primitive connecting persuasion and cheap talk, then test whether natural monotonicity survives. |
| Koszegi and Szeidl, [A Model of Focusing in Economic Choice](https://academic.oup.com/qje/article-abstract/128/1/53/1840038) | QJE 2013 | Seek one transferable force that organizes several apparently conflicting choice patterns. |
| Gabaix, [A Sparsity-Based Model of Bounded Rationality](https://academic.oup.com/qje/article-abstract/129/4/1661/1854039) | QJE 2014 | Modify a foundational operator instead of building separate models for each anomaly, producing a reusable tool. |
| Galperti, Levkun, and Perego, [The Value of Data Records](https://academic.oup.com/restud/article-abstract/91/2/1007/7115889) | ReStud 2024 | Ask for the marginal value of one record and use dual prices to reveal direct value and a pooling externality. |
| Ashlagi, Monachou, and Nikzad, [Optimal Allocation via Waitlists: Simplicity Through Information Design](https://academic.oup.com/restud/advance-article-abstract/doi/10.1093/restud/rdae013/7603125) | ReStud 2025 | Solve the unrestricted allocation first, then show how a simple familiar institution plus information design implements it. |
| Sannikov, [A Continuous-Time Version of the Principal-Agent Problem](https://academic.oup.com/restud/article-abstract/75/3/957/1556636) | ReStud 2008 | Change time representation to expose continuation utility as the sufficient state and simplify dynamic incentives. |
| [Long Information Design](https://www.econtheory.org/ojs/index.php/te/article/viewArticle/20220883) | Theoretical Economics 2022 | Change the timing/deadline primitive and compare restricted with unrestricted information technologies before applying the result. |
| [Full Substitutability](https://onlinelibrary.wiley.com/doi/full/10.3982/TE3240) | Theoretical Economics 2019 | Map several literatures' definitions to one common object; technical abstraction earns its place through unification. |
| [Optimal Mechanism for the Sale of a Durable Good](https://www.econtheory.org/ojs/index.php/te/article/viewArticle/20240865) | Theoretical Economics 2024 | Pursue one sharp implementation equivalence and stop generalizing where the transparent result ends. |
| [Dynamic Benchmark Targeting](https://www.sciencedirect.com/science/article/pii/S0022053117300212) | JET 2017 | Import a tool only after adding economically meaningful patience, commitment, and memory primitives that change its conclusion. |
| [Common Belief Foundations of Global Games](https://www.sciencedirect.com/science/article/pii/S0022053116000417) | JET 2016 | Strip a result away from a special signal construction and identify the belief primitive that actually supports it. |
| [Selecting a Winner with External Referees](https://www.sciencedirect.com/science/article/pii/S0022053123000832) | JET 2023 | Move from institution to minimal model, derive the mechanism's recognizable shape, then compare alternative evaluation systems. |
| [Hybrid Platform Model: Monopolistic Competition and a Dominant Firm](https://onlinelibrary.wiley.com/doi/full/10.1111/1756-2171.12478) | RAND 2024 | Build a benchmark ladder from marketplace to hybrid platform and use it to organize entry, pricing, and welfare. |
| [Content-Hosting Platforms: Discovery, Membership, or Both?](https://onlinelibrary.wiley.com/doi/10.1111/1756-2171.70029) | RAND 2025 | Begin with an economically recognizable business-model taxonomy, then show how competition can reverse the monopoly tradeoff. |
| [X-games](https://www.sciencedirect.com/science/article/pii/S0899825614001717) | GEB 2015 | Compress several applications into a minimal externality formalism; portability, not theorem count, supplies breadth. |
| [Screening for Experiments](https://www.sciencedirect.com/science/article/pii/S0899825623001021) | GEB 2023 | Organize results around a clean tradeoff between experiment quality and ex-post decision quality. |
| [Product Quality and Consumer Search](https://www.aeaweb.org/articles?id=10.1257/mic.20200300) | AEJ Micro 2023 | Add endogenous quality to a canonical search model and actively seek failures of intuitive monotonicity. |
| [Dynamic Information Design under Constrained Communication Rules](https://www.aeaweb.org/articles?id=10.1257/mic.20200356) | AEJ Micro 2023 | Add a concrete communication constraint only because it yields a named belief-spread mechanism and welfare comparison. |

This list is a starting evidence set, not a canon and not a publication
guarantee. The objective is to raise the probability of finding a good
question, a small faithful model, a sharp mechanism, a credible theorem, and a
clear economic explanation while reducing low-value human repair.
