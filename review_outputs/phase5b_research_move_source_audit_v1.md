# Phase 5B first ResearchMove source audit

## Authorization and disposition

On 2026-07-24 the researcher authorized source audit and
disabled-by-default development for exactly three candidates:

1. `Computational Structure Probe`;
2. `Representation Hunter`; and
3. `Analogical Structure Transfer — First Mapping Failure`.

The authorization does not cover runtime activation, an opt-in pilot,
automatic selection, a new research question, or reopening the parked
score-disclosure case.

All three candidates pass source audit with boundaries for a noncanonical
development release. They remain functional research operations, not scholar
personas, author-style imitations, route outcomes, novelty verdicts, or quality
claims.

## Audit method

The audit used eleven public primary sources from author, university,
professional-society, or official journal locations. Exact source snapshots
were retrieved on 2026-07-24 only to verify access and compute SHA-256. The
repository retains citations, hashes, byte lengths, functional derivations,
biases, and non-applicability; it does not retain source PDFs, reusable source
sentences, or hidden reasoning traces.

Published-paper evidence is labeled `inferred_reconstruction`: a final paper
can reveal a useful scientific transformation without revealing how its
authors historically discovered it. Only a method essay's express proposal is
labeled `explicitly_stated`.

## Source inventory

| ID | Primary source and exact snapshot | Type / relation | Bias and boundary | SHA-256 / bytes |
|---|---|---|---|---|
| `source.varian_model_building` | Hal R. Varian, [How to Build an Economic Model in Your Spare Time](https://people.ischool.berkeley.edu/~hal/Papers/how-OLD.pdf) (1997; public author revision) | `method_essay` / `explicitly_stated` | Retrospective, idealized, single-researcher, historical foundation. Supports simple cases and simplify-then-generalize, not numerical proof or universal minimalism. | `9035599e06746c9a2b929f9b6a3504b6a8ef6151d85eee27c486d9753745041c` / 123,374 |
| `source.liang_ml_models` | Annie Liang, [Using Machine Learning to Generate, Clarify, and Improve Economic Models](https://anniehliang.com/papers/JEL.pdf) ([author record](https://anniehliang.com/papers/pages/jel.html), accepted 2026) | `method_essay` / `explicitly_stated` | Method proposal in a fast-changing tool context; partially prediction-oriented. Supports adversarial model probes and human interpretation, not empirical workflow, proof, mechanism, or reliable LLM novelty. | `458fedd00d7f5fb5043d111914a481124e3cf076f5ad293836e6f38486ceebf6` / 1,492,432 |
| `source.moraga_sun_quality_search` | José L. Moraga-González and Yajie Sun, [Product Quality and Consumer Search](https://tinbergen.nl/media/news/moraga_sun_quality_and_search_aejmicro_final.pdf) ([AEA record](https://www.aeaweb.org/articles?id=10.1257/mic.20200300), 2023) | `published_paper` / `inferred_reconstruction` | Published-outcome and domain selection. Supports preserving sign reversals while seeking a general condition, not a claim that the authors used computation or that finite families prove universality. | `39df37f65a55bc6428171d0985fa2524eed31e42c798c12fef5e9c2da5b351c4` / 681,197 |
| `source.kamenica_gentzkow_persuasion` | Emir Kamenica and Matthew Gentzkow, [Bayesian Persuasion](https://web.stanford.edu/~gentzkow/research/BayesianPersuasion.pdf) ([AEA record](https://www.aeaweb.org/articles?id=10.1257/aer.101.6.2590), 2011) | `published_paper` / `inferred_reconstruction` | Successful canonical example and published-outcome selection. Supports posterior and concavification representations under their exact assumptions, not universal low-dimensionality or transfer to arbitrary communication environments. | `64ddd2908c8da90c8e7551ec1ad74b5c17bd10816f1773490835f07a63af8591` / 834,709 |
| `source.azevedo_leshno_matching` | Eduardo M. Azevedo and Jacob D. Leshno, [A Supply and Demand Framework for Two-Sided Matching Markets](https://eduardomazevedo.github.io/papers/Azevedo-Leshno-Supply-and-Demand-Matching.pdf) ([JPE record](https://www.journals.uchicago.edu/doi/10.1086/687476), 2016) | `published_paper` / `inferred_reconstruction` | Published-outcome and domain selection. Supports cutoff-price representation and transparent market clearing within the model, not universal cutoff sufficiency or finite-market uniqueness. | `cca02cf9462f390a31c38c12815f68fab101451999ba2c5ea2025c6c4c23d322` / 648,930 |
| `source.doval_skreta_limited_commitment` | Laura Doval and Vasiliki Skreta, [Mechanism Design With Limited Commitment](https://www.econometricsociety.org/publications/econometrica/2022/07/01/mechanism-design-limited-commitment/file/ecta200449.pdf) (Econometrica 2022) | `published_paper` / `inferred_reconstruction` | Published-outcome and domain selection. Supports canonical posterior-based representation for the paper's limited-commitment environment, not arbitrary dynamic games, low dimensionality, or novelty from representation alone. | `83a182e86134e914e0787fb941e9588674325a0b9d7f77776e55e9879edcf1d5` / 527,441 |
| `source.sannikov_continuation_value` | Yuliy Sannikov, [A Continuous-Time Version of the Principal-Agent Problem](https://www.gsb.stanford.edu/faculty-research/publications/continuous-time-version-principal-agent-problem) ([journal record](https://academic.oup.com/restud/article-abstract/75/3/957/1556636), 2008) | `published_paper` / `inferred_reconstruction` | Historical successful-case selection. Supports continuation value as a sufficient recursive state under the paper's conditions, not universal sufficiency or superiority of continuous time. The hash binds the official Stanford record page. | `a55d59ce528c31a1d5b3b74a3437dbe968a958714d727990e5c7d9229e3ee01c` / 184,200 |
| `source.full_substitutability` | John William Hatfield, Scott Duke Kominers, Alexandru Nichifor, Michael Ostrovsky, and Alexander Westkamp, [Full Substitutability](https://www.hbs.edu/ris/Publication%20Files/19-016_9d235843-80ce-4c8e-9938-4f0241379aab.pdf) ([journal record](https://onlinelibrary.wiley.com/doi/full/10.3982/TE3240), 2019) | `published_paper` / `inferred_reconstruction` | Published-outcome selection and author-version risk. Supports mapping several substitutability languages to a common structure and locating economically meaningful scope extensions, not value from every mismatch. | `47b7537b3ee55024eb65e6c2953461a4e813f9c0ab945a5b388012a3a82bc425` / 751,676 |
| `source.common_belief_global_games` | Stephen Morris, Hyun Song Shin, and Muhamet Yildiz, [Common Belief Foundations of Global Games](https://economics.mit.edu/sites/default/files/2022-10/common%20belief%20foundations.pdf) ([journal record](https://www.sciencedirect.com/science/article/pii/S0022053116000417), 2016) | `published_paper` / `inferred_reconstruction` | Published-outcome selection and domain restrictions. Supports mapping a special signal construction to a deeper belief primitive and recording where binary/symmetric scope stops transferring, not arbitrary-game portability. | `582081114b924786eff5b14c2ce4e5e5d4f4d74a05938f733523f56aa6efc626` / 404,671 |
| `source.x_games` | Kfir Eliaz and Ran Spiegler, [X-games](https://en-econ.tau.ac.il/sites/economy_en.tau.ac.il/files/media_server/Economics/foerder/papers/3-2014.pdf) ([TAU record](https://cris.tau.ac.il/en/publications/x-games/), 2015) | `published_paper` / `inferred_reconstruction` | Deliberate unification and published-outcome selection. Supports cross-application structural mapping plus explicit failure witnesses, not novelty from shared abstraction or from the first formal difference. | `e90dbbef5d81fe0ace08b01b5420e4e203718977d4ee32332c2448a64f6d07bd` / 205,490 |
| `source.rubinstein_dilemmas` | Ariel Rubinstein, [Dilemmas of an Economic Theorist](https://arielrubinstein.tau.ac.il/papers/74.pdf) (Econometrica 2006) | `method_essay` / `explicitly_stated` | Retrospective personal stance, historical foundation, and intellectual-lineage overlap with the X-games source. Preserves skepticism about elegant mappings, relevance, and model scope; it is a contrast, not a ban on analogy. | `ebafaccd40bc513ce76857498e7206143aea8d518421f3e5c48f21ffe4b8530b` / 200,033 |

## Move-level derivation

### Computational Structure Probe

Positive anchors are the Varian and Liang method essays plus the independent
Moraga-González--Sun paper family. The first two explicitly support small-case
iteration and computational/adversarial probing; the third is only an
inference from a published theory design that preserves sign reversals while
seeking more general conditions.

The derived move may search bounded cases for strict crossings, perturbation
margins, counterexamples, cutoffs, orderings, sufficient statistics,
equivalences, or functional forms. It must export the tested domain, solver
assumptions, failures, and a conjectured structure to normal proof and
interpretation work. Finite numerical evidence is never proof, a failed search
is not nonexistence, and the move is inapplicable when simplification removes
first-order institutional structure or changes the solution concept.

### Representation Hunter

The four positive anchors are independent published-paper families:
posterior/concavification, matching cutoffs, posterior-based limited-commitment
mechanisms, and continuation-value state compression. Each demonstrates a
paper-local representation change; none states a general discovery recipe.

The derived move must construct the map from the original formulation, state
its losslessness conditions, and record the first compression failure. It may
emit advisory evidence only when the representation reveals an ordering,
decomposition, comparative static, or transferable mechanism. Notation-only
compression, hidden institutional detail, or a merely renamed high-dimensional
object creates `application_only_risk`, not a promoted model or novelty claim.

### Analogical Structure Transfer — First Mapping Failure

Full Substitutability and Common Belief Foundations supply two independent
positive research lineages. X-games supplies the clearest application-spanning
mapping and failure witness but is not fully independent of the Rubinstein
skeptical lineage. Rubinstein is retained as a substantive contrast against
turning formal elegance, fables, or local mismatches into relevance or novelty.

The derived move maps primitives, information, timing, feasible actions,
strategic arrows, solution concept, and outcome object to a distant structure.
It marks each link exact, conditional, or failed and isolates the first
economically load-bearing failure. Exact mapping is absorption risk, not
novelty proof; failed mapping is a conjecture, not a contribution. A change of
research object requires separate human reframe authority. The move never
chooses a route or investment disposition.

## Independence and anti-echo audit

- Eleven sources cover eleven paper families.
- No positive move depends on only one author or coauthor cluster.
- The computational move has two independent explicit method sources and one
  independent published-paper instance.
- The representation move has four author-disjoint paper families and at
  least three distinct functional traditions even under conservative grouping.
- The analogical move has two independent positive traditions, one partially
  dependent failure-witness tradition, and one skeptical contrast.
- The source set is not a prestige ranking and no runtime projection exposes a
  scholar, institution, journal, recency weight, citation, or source identity.
- Sources before 2010 are retained only for a function unavailable from newer
  evidence and receive historical-foundation weight.

## Development and activation boundary

The development corpus must remain:

- noncanonical and outside evaluation holdouts;
- absent from packaged production resources;
- inaccessible through machine navigation, routes, WorkPackets, or the public
  bridge;
- disabled by default, with no selector, pilot, or automatic-selection
  authority;
- function-only in any offline projection; and
- unable to write canonical state or emit `continue`, `park`, `kill`, or
  `new_brief_required`.

An opt-in pilot requires a later, separate researcher authorization. Automatic
default activation additionally requires positive held-out paired replication
and experimental end-to-end evidence with no critical-error increase or
material collapse in idea diversity.
