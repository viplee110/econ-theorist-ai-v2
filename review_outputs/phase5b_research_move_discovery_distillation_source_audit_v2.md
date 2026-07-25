# Discovery-Distillation ResearchMove Source Audit v2

Date: 2026-07-25

Status: `passed_with_boundaries`

Authority: researcher-authorized, disabled development only

## Scope and decision

This additive audit covers three function-only research moves intended to
address the observed failure of topic-level prompts to produce economically
meaningful questions:

- `Market-Operation Primitive`;
- `Different-Implementation Question`; and
- `Ground-Up Constraint Rebuild`.

The release preserves the v1 corpus byte-for-byte as its inherited base and
adds four public primary-source cards. It does not create a scholar persona,
runtime selector, route, WorkPacket field, pilot authorization, canonical
writer, or human-decision authority. Source identities and source phrasing
remain unavailable to a future generator.

## Additive source audit

### Daron Acemoglu, Nobel Prize interview transcript

- Locator:
  [official transcript](https://www.nobelprize.org/prizes/economic-sciences/2024/acemoglu/1722488-interview-transcript/)
- Access: verified public official-institution page on 2026-07-25.
- Captured bytes: `179138`.
- Captured SHA-256:
  `b2a6732d81f2484ad5990299bfd1684238389ed645cbf7dab8b71e336e7953d8`.
- Evidence relation: explicit interview statement.
- Supported transfer: promising questions may arise while reading an existing
  paper or encountering a real social problem and asking how one would treat
  it differently; ambition remains incremental and repeated error checking is
  necessary.
- Does not support: novelty, correctness, importance, or general applicability
  of every alternative implementation.
- Bias and boundary: retrospective narration, successful-case selection, and a
  single researcher's method. The move must stop when the alternative is merely
  relabeling or changes a human-owned question without approval.

### Mark Armstrong and Jidong Zhou, Consumer Information and the Limits to Competition

- Locator:
  [official AEA article page](https://www.aeaweb.org/articles?id=10.1257%2Faer.20210083).
- Access: verified public official-publisher abstract and metadata page on
  2026-07-25; the captured page is not represented as full-text access.
- Captured bytes: `30023`.
- Captured SHA-256:
  `1a75a11c2d06084235ef533f9fc41649092a9de64550018188c3b71cd64aa897`.
- Evidence relation: inferred reconstruction from a published pure-theory
  design.
- Supported transfer: an apparently background market operation--what private
  preference information consumers receive--can be made the exact design
  variable, with explicit consequences for product differentiation,
  competition, purchase allocation, and welfare.
- Does not support: a general recipe, an AI-specific primitive, or the claim
  that every information refinement is economically important.
- Bias and boundary: published-outcome selection, one coauthor cluster, and IO
  domain specificity. A market-operation move is inapplicable when the changed
  detail alters no feasible action, information, transfer, strategic response,
  or payoff.

### Alvin E. Roth, The Economist as Engineer

- Locator:
  [author-hosted published paper](https://web.stanford.edu/~alroth/papers/engineer.pdf).
- Access: verified public author/institution PDF on 2026-07-25.
- Captured bytes: `423368`.
- Captured SHA-256:
  `f3a0d982030940a5650d9ecb25ef462358fbd6ada238c169e248e52b7adccaaf`.
- Evidence relation: inferred reconstruction from a published methodology and
  market-design paper.
- Supported transfer: real market design requires responsibility for
  institution-level details, and complications encountered in implementation
  can generate new theoretical questions rather than merely decorate a simple
  model.
- Does not support: importing every real-world detail, replacing theory with
  engineering, or treating implementation success as proof of generality.
- Bias and boundary: historical foundation, successful-design selection, and
  market-design domain transfer. The operative detail must change a strategic
  or feasible object and remain separable enough for theory.

### Elon Musk, The Henry Ford video oral-history interview

- Locator:
  [museum-issued transcript](https://www.thehenryford.org/docs/thehenryfordlibraries/innovator-transcripts/transcript_musk_full-length5a30f6547bde445e8119d53fb454b300.pdf?sfvrsn=f4eeb20a_1).
- Interview: 2008; transcript copyright: 2009.
- Access: verified public institution PDF on 2026-07-25.
- Captured bytes: `93856`.
- Captured SHA-256:
  `c442cc17b06ffa29192fcecb98efbbbb3be2b5aab0e841ce1e1f65b5b8c8ebe1`.
- Evidence relation: explicit interview statement.
- Supported transfer: question inherited conventions, reconstruct conclusions
  from the most defensible fundamentals, locate the binding system bottleneck,
  and reject a different design unless it is actually better. The transcript
  also cautions that major innovations often combine several changes rather
  than one slogan.
- Does not support: economic equilibrium, welfare, novelty, optimality,
  scientific validity, a universal deletion rule, or imitation of a founder's
  personality and management style.
- Bias and boundary: retrospective narration, successful-case selection,
  commercial self-presentation, and hardware-to-economics domain transfer. The
  source may not independently support a ResearchMove. Its function is
  admitted only when two independent economic sources support and bound the
  same transformation.

## Move-level adjudication

### Market-Operation Primitive

Admitted for disabled development. It reconstructs what participants actually
observe, search, remember, can commit to, can enter or exit, and how they pay;
then it replaces one inherited convention and traces the strategic consequence.
It must not become an institution-detail checklist. Its positive evidence is
the independent Roth and Armstrong-Zhou paper families.

### Different-Implementation Question

Admitted for disabled development. It takes one established result or
institutional tension, changes one substantive primitive, timing, information,
commitment, or implementation rule, and asks which mechanism and prediction
change. Its positive evidence combines Acemoglu's explicit method observation
with the independent Doval-Skreta limited-commitment theory instance already
audited in v1. It must stop at cosmetic changes or a different human-owned
question.

### Ground-Up Constraint Rebuild

Admitted for disabled development with a cross-domain warning. It preserves
the economic puzzle and outcome, separates hard feasibility from information,
incentives, commitment, institutional rules, and conventions, and reconstructs
the smallest model that still carries the mechanism. Its first-principles
source is the Musk interview, but admission also requires the independent
economic anchors from Varian and Roth. It must not delete a load-bearing
institution, replace incentives with physical feasibility, or treat elegance
as contribution quality.

## Release boundaries

- All moves remain `development_disabled`.
- The release is checkout-only and excluded from packaging.
- There is no retrieval, ranking, selector, automatic activation, route
  disposition, canonical write, pilot, novelty, welfare, or human-gate
  authority.
- Source snapshots are not retained in the repository; only hashes, byte
  counts, citations, derived functions, and limitations remain.
- A separate researcher authorization is required before any opt-in runtime
  pilot.
- Automatic activation remains contingent on held-out replication and one
  positive end-to-end pilot.
