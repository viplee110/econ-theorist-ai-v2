# Literature acquisition checkpoints

Status: additive trusted-local contract. This document defines evidence
acquisition around existing research routes; it does not create a scientific
stage, route, canonical payload, human gate, or novelty decision.

## Purpose

The system checks literature twice because the two decisions require different
evidence.

1. **Direction orientation, before the researcher chooses a framing.** A broad,
   shallow search asks whether either independently generated direction is
   obviously standard, already absorbed, or pointed at the wrong benchmark.
2. **Closest-theory audit, after claims are verified and before G4.** A narrow,
   full-text search tests the exact formal result, assumptions, economic lesson,
   and first substantive mapping failure against the closest theory.

The early check protects research time. The later check supports a bounded
contribution judgment. Neither search substitutes for economist judgment.

## Pre-choice direction orientation

The mentor and two collaborators first receive the unchanged framing
WorkPacket in sealed lanes. Only after the raw panel is immutable may the host
perform one source-aware coordinator review. The researcher sees the raw panel,
mentor screen, sources, coverage limits, and two complete comparison cards
before choosing a direction.

Legacy AI-agent runs retain `FramingDirectionCardV1` and
`FramingChoiceReviewV1` byte-for-byte. New topic-neutral activations explicitly
bind `source_aware_choice_profile=topic_neutral_v2` and require
`FramingDirectionCardV2` plus `FramingChoiceReviewV2`. A V2 card records:

- the exact question, benchmark, and benchmark delta;
- the economic significance and load-bearing economic force;
- inspected classic and recent sources, overlap risk, and closest overlap;
- the remaining theory delta and falsifiable increment; and
- the cheapest decisive pre-G1 probe and a kill-or-reframe condition.

The review remains noncanonical and immutable. It cannot mark literature
coverage current, establish novelty or non-absorption, approve G1, select a
direction, or create a worker. Exact retry returns the same digest; changing
the profile, panel, sources, cards, packet, head, project, or session is a
different operation and fails closed.

## Pre-G4 closest-theory acquisition

The formal checkpoint is not a new route. It is the host obligation that
applies when one delivered WorkPacket jointly requires `LiteratureEvidence`,
`ClosestTheoryMap`, and `AbsorptionAssessment`:

```text
verified claims
  -> fresh closest-theory acquisition
  -> existing absorption audit
  -> result portfolio
  -> G4 researcher decision
```

The host searches from the current question, exact benchmark, primitives,
timing, solution concept, assumptions, quantifiers, verified result, and
economic lesson. It should inspect classic anchors, recent candidates, the
closest paper, and useful backward or forward links until the existing
closest-theory comparison dimensions are covered or a precise coverage limit
is recorded. There is no mechanical paper-count target.

`full_text` means that the relevant text was actually inspected. Metadata,
abstracts, snippets, and model memory cannot be upgraded to full-text evidence.
The existing validator permits `proceed` only with source-verified full-text
assertions and prevents an unresolved or non-proceed assessment from supporting
a G4 approval proposal. Evidence belongs to the current packet and base head;
changing the formal claim or superseding the packet requires a fresh search.

## Acquisition, privacy, and failure

Two modes are admissible:

- `online_host_search`, when the host has search capability and the researcher’s
  privacy/egress policy separately permits sending the search query; and
- `offline_user_bundle`, using papers explicitly supplied for this project.

WorkPacket delivery permission is not automatically literature-search
permission. The host must not scan parent or sibling projects. It may register
project-owned evidence through the packet’s ordinary artifact path, but should
not copy copyrighted papers into the source repository.

If early access fails, the active source-aware team remains at the retryable
review stop; it must not silently downgrade to a source-blind choice. If the
formal audit has only metadata, abstracts, or incomplete coverage, it records
`unresolved_evidence` and cannot recommend `proceed`. If no citable source is
available, the host requests an offline bundle and keeps the same run open;
ordinary waiting is not a terminal failure.

## Host and evidence boundary

Codex exposes the versioned pre-choice sidecar and the formal WorkPacket
obligation. Claude Code and Cursor currently expose the formal obligation
through the host-neutral single-route protocol; they do not yet claim the
Codex framing-team sidecar. Deterministic tests establish binding, replay, and
fail-closed behavior. In the trusted-local profile, they do not independently
prove that a host searched the entire literature or that the resulting research
is novel, important, correct, or publication-ready.

