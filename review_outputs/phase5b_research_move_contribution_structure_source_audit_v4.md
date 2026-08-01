# Contribution-Structure ResearchMove Source Audit v4

Date: 2026-08-01

Status: `passed_with_boundaries`

Authority: researcher-authorized, disabled development only

## Scope and decision

This additive audit covers exactly two function-only research moves:

- `Question Reframer`; and
- `Near-Optimal Structure Pivot`.

The batch responds to two scientific gaps in the existing nine-move corpus. A
candidate may preserve a real mechanism but remain trapped in an
application-level question, and an exact optimization problem may conceal the
small structure that would make a result understandable and reusable. These
moves add bounded branch operations for those gaps. They do not score journal
fit, predict publication, certify novelty or importance, replace human question
authority, or reward abstraction, theorem count, or approximation for its own
sake.

The v4 release preserves every v1--v3 source card and move exactly. It adds four
public primary-source cards. Published papers support only inferred
reconstructions of scientific design; none is evidence that an author privately
used the move as a general research habit. Only source-isolated functional
properties enter the corpus. No source prose, persona, author voice, or hidden
reasoning trace is retained.

## Additive admitted sources

### Simone Galperti, Aleksandr Levkun, and Jacopo Perego, The Value of Data Records

- Source snapshot:
  [Review of Economic Studies manuscript PDF](https://www.restud.com/wp-content/uploads/2023/04/MS31202manuscript.pdf).
- Publication:
  [Review of Economic Studies article record](https://academic.oup.com/restud/article/91/2/1007/7115889).
- Access: verified public journal-hosted manuscript PDF on 2026-08-01.
- Captured bytes: `387363`.
- Captured SHA-256:
  `2706a8b614b2fa0e6ec3127b7fb9757174eb1adf707c6a326dc5960cfff8f80a`.
- Evidence relation: inferred reconstruction from a published applied-theory
  design.
- Supported transfer: keep the information-intermediation problem fixed but
  change the unit of analysis from an undifferentiated dataset to the marginal
  value of one record. That reframe reveals a pooling externality across records
  and creates a portable valuation object with implications for acquisition and
  compensation.
- Does not support: treating every smaller unit as insightful, assuming that a
  marginal-value object always exists, or claiming that a reframed object is
  novel, important, welfare improving, or empirically measurable.
- Bias and boundary: published-outcome selection, one coauthor cluster,
  information-design specificity, and a journal-manuscript version difference.
  The move is inapplicable when the proposed unit erases the original strategic
  interaction or changes the researcher-owned economic tension.

### Xavier Gabaix, A Sparsity-Based Model of Bounded Rationality

- Source snapshot:
  [NBER working-paper PDF](https://www.nber.org/system/files/working_papers/w16911/w16911.pdf).
- Publication:
  [Quarterly Journal of Economics article record](https://academic.oup.com/qje/article-abstract/129/4/1661/1854039).
- Access: verified public institution PDF on 2026-08-01.
- Captured bytes: `763110`.
- Captured SHA-256:
  `bfb848161c9ecf406a34687cd274b4f724e34e8df7c2b0c42b634beefc8db74f`.
- Evidence relation: inferred reconstruction from a published pure-theory
  design.
- Supported transfer: preserve the economic problem of bounded choice while
  moving from separate anomaly-specific adjustments to one sparse decision
  operator that can be applied to demand and equilibrium. The useful reframe
  changes the object being explained and earns breadth through nearby-case
  transfer rather than through additional primitives.
- Does not support: universal sparsity, a claim that one operator explains all
  bounded rationality, or permission to replace a faithful institution with a
  mathematically convenient behavioral object.
- Bias and boundary: published-outcome selection, successful-case selection,
  behavioral-domain specificity, and an author-version difference. The reframe
  must preserve an exact benchmark and identify the first benchmark reasoning
  link that changes.

### Jason D. Hartline and Tim Roughgarden, Simple versus Optimal Mechanisms

- Source snapshot:
  [author-hosted conference-paper PDF](https://www.timroughgarden.org/papers/bk.pdf).
- Publication:
  [ACM article record](https://dl.acm.org/doi/10.1145/1566374.1566407).
- Access: verified public author PDF on 2026-08-01.
- Captured bytes: `223395`.
- Captured SHA-256:
  `9dd9fe2c5022b7309a82be5207e53e57fb3ca955758df30447c0134e9e1c28c3`.
- Evidence relation: inferred reconstruction from a published pure-theory
  design.
- Supported transfer: when the distribution-sensitive optimum is opaque,
  restrict attention to a transparent mechanism class and prove an explicit
  approximation guarantee under stated distribution and feasibility
  conditions. The guarantee identifies which assumptions allow simplicity to
  retain most of the objective.
- Does not support: arbitrary constant-factor approximation, treating
  computational convenience as economic value, or transferring auction
  regularity and downward-closed feasibility conditions to unrelated models.
- Bias and boundary: published-outcome selection, algorithmic-mechanism-design
  specificity, one coauthor cluster, and historical-foundation bias. A formal
  bound is required; numerical closeness or a short mechanism description is
  insufficient.

### Itai Ashlagi, Faidra Monachou, and Afshin Nikzad, Optimal Allocation via Waitlists: Simplicity through Information Design

- Source snapshot:
  [Review of Economic Studies manuscript PDF](https://www.restud.com/wp-content/uploads/2024/01/MS30810manuscript.pdf).
- Publication:
  [Review of Economic Studies article record](https://academic.oup.com/restud/article/92/1/40/7603125).
- Access: verified public journal-hosted manuscript PDF on 2026-08-01.
- Captured bytes: `1426123`.
- Captured SHA-256:
  `7805829af19344a0071dfb40cdb4ae990e7a8b9b3ae9c0817f0058062e8659f1`.
- Evidence relation: inferred reconstruction from a published applied-theory
  design.
- Supported transfer: solve the unrestricted direct-mechanism benchmark, then
  search for a familiar institution and information policy that implements the
  same objective transparently. Exact simple implementation is the zero-loss
  boundary of a structure pivot and shows how the unrestricted optimum can
  reveal the cutoff or partition a useful theorem should explain.
- Does not support: universal optimality of waitlists, free addition of an
  information-design instrument, or the claim that familiar institutions are
  always simple for participants or administrators.
- Bias and boundary: published-outcome selection, one coauthor cluster,
  dynamic-allocation specificity, and a journal-manuscript version difference.
  The information instrument, supermodularity, arrival process, waiting cost,
  and objective weights are load-bearing and cannot be silently transferred.

## Contextual chain and contradiction checks

The following primary sources were inspected as contextual checks. They are not
additional hash-bound cards and do not count as independent positive evidence.

- Bulow and Klemperer,
  [Auctions versus Negotiations](https://www.gsb.stanford.edu/faculty-research/publications/auctions-vs-negotiations),
  provides a transparent comparison in which additional competition dominates
  optimal negotiation under explicit assumptions. It is a useful boundary:
  changing the bidder set is resource augmentation, not a same-environment
  approximation guarantee.
- Shengwu Li,
  [Designing Simple Mechanisms](https://www.aeaweb.org/articles?id=10.1257%2Fjep.38.4.175),
  distinguishes several participant-facing meanings of simplicity. It warns
  against using description length or mathematical tractability as the sole
  simplicity criterion.
- The existing source card for Carroll's `Robustness and Linear Contracts`
  shows that a simple institution can become exactly optimal after changing the
  knowledge benchmark. That is a robustness-axis result, not an approximation
  result, so v4 does not reuse it as evidence for the new move.

These checks preserve conflicting routes to simplicity: a bounded-loss rule in
the maintained environment, a zero-loss implementation using an explicitly
available design instrument, a resource-augmentation comparison, and robust
optimality under a changed uncertainty model are different scientific claims.
The move may not merge them.

## Move-level adjudication

### Question Reframer

Admitted for disabled development as `paper-chain-derived`. The move freezes the
current economic tension, exact benchmark, and decisive outcome, then generates
alternative units or objects of explanation. Each branch must state what remains
fixed, the first benchmark reasoning link that changes, the new economic object,
and the resulting consequence or transfer class. It retains a branch only when
the reframe increases intellectual radius or reveals a different mechanism
without changing the underlying tension.

The move returns candidate research branches, not an accepted ResearchQuestion.
Any change to a human-approved question requires a fresh human decision. It is
inapplicable when the proposed branch merely changes nouns, adds a fashionable
application, introduces a different research objective, or seeks a Top-5 label
without a scientific change.

### Near-Optimal Structure Pivot

Admitted for disabled development as `paper-chain-derived`. The move fixes the
environment, objective, feasible set, and exact optimum benchmark, then searches
for the smallest economically interpretable restricted class. It must prove an
explicit multiplicative or additive loss bound, or an exact zero-loss
implementation, and preserve the assumptions supporting that statement. It then
extracts the cutoff, monotonicity, partition, sufficient statistic, or other
load-bearing structure that an exact theorem or implementation should explain.

The move is not a license to abandon the exact problem. Approximation is useful
only when the simple class exposes economic structure, changes practical
implementability, or yields a transferable theorem. It is inapplicable when the
loss cannot be defined, the bound is vacuous, the exact solution is already
transparent, or omitted institutional detail is first-order. Finite computation
is not a proof of a guarantee.

## Release boundaries

- All eleven inherited and additive moves remain `development_disabled`.
- The release is checkout-only and excluded from packaging.
- There is no retrieval, ranking, selector, automatic activation, WorkPacket
  exposure, route disposition, canonical write, pilot, novelty, importance,
  welfare, venue, or human-gate authority.
- The audit supports two functional search transformations, not named-scholar
  replicas, personalities, writing styles, or comprehensive intellectual
  biographies.
- Source identities and source phrases remain unavailable to a future
  generator.
- Source snapshots are not retained in the repository; only hashes, byte
  counts, citations, derived functions, and limitations remain.
- A separate researcher authorization is required before any opt-in runtime
  pilot.
- Automatic activation remains contingent on positive held-out replication and
  one positive end-to-end pilot with no critical-error or idea-diversity harm.
