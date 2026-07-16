# V5.5 economy-tier decompose and audit summary

Date: 2026-07-16

## Exact project

The full Dropbox-synchronised research project is:

`C:\Dropbox\Shufe\Research\Project\Search on Graphs\.etai-v5_4d2-economy-tier-20260716-c8c539e`

The files in this directory are compact copies of the evidence needed to
continue development without depending on Codex conversation history.

## Decompose result

- Route: `decompose.primitives`
- Run: `run_op_022ec3249664a8c635ac02d05e2b332095e28205828dc370`
- Outcome: `committed`
- Candidate and canonical head after:
  `90a35ee9c6af65467e6d6209723597c502b1eb9b0f77fe7fe08a0226c3aefcd5`
- Structured diagnostics: none
- Evidence: `decompose_candidate.committed.json`

The packet-v2 input evidence binding and the direction of the `decomposes`
relation were both authored correctly. Scientifically, the output was a useful
concept map but not a closed dynamic game.

## Independent adversarial audit

Evidence: `independent_adversarial_audit.md`

Verdict: major revision; do not pass G1. It identified:

1. missing public state, state-contingent actions, payoffs, Bayes updating, and
   transition kernel;
2. strict dominance of inspection whenever a valid certificate is visible and
   `c > 0` under the literal payoff ledger;
3. an unresolved conflict between persistent certificates and period-specific
   capacity;
4. state-distribution reweighting rather than the claimed same-state closed
   feedback;
5. benchmark rows that do not yet isolate one mechanism under a common game.

## Built-in economics audit

- Route: `audit.framing_economics`
- Run: `run_op_af8c18585b55048abd4f4c78154ec6526bdd209fb5b64d58`
- WorkPacket:
  `64636e00ebffc1c3350ab181e965b1f69de781a16c41cf70723f85572826dec1`
- Candidate digest recorded by finish:
  `185c9a7d116858b62f1d3737ef7c939b42c73bd774eabdf95a355287be1d7dce`
- Outcome: `recorded_failure` / `failed_no_effect`
- Canonical head before and after:
  `90a35ee9c6af65467e6d6209723597c502b1eb9b0f77fe7fe08a0226c3aefcd5`
- Warnings: `repair_exhausted`, `upstream_payoff_path_missing`,
  `human_g1_not_confirmed`
- Evidence: `audit_candidate.uncommitted.json`, `audit_work_packet.json`, and
  `audit_terminal_completion_record.json`

The economy-tier model successfully diagnosed essentially every independent
audit finding: certificate semantics, the visible-certificate dominance
boundary, missing state/action/payoff/transition closure, invalid benchmark
attribution, aggregate endogeneity, and absent selection assurance. It also
proposed `revise_framing` and did not confirm G1.

The candidate could not commit because the immutable upstream PrimitiveGraph
does not connect `n_payoffs` to a choice in the stock cycle. The route contract
requires an active-margin witness that cannot be legally bound to that graph.
Changing the archetype would contradict the exact ResearchQuestion. The
scientific diagnosis therefore succeeded, while the representation of a
negative audit failed.

## Development conclusion

This is not evidence for weakening readiness gates. A readiness or mechanism
claim must still require exact payoff witnesses. The minimal repair to study is
a committable negative-audit path:

- when `proposed_action == revise_framing`;
- when no readiness, mechanism activity, or G1 confirmation is claimed;
- when the missing witness is itself disclosed as a typed gap with exact
  upstream repair targets;
- permit the audit bundle and replacement revise dossier to commit without
  fabricating an active witness;
- route the project back to upstream framing/decomposition repair.

Do not add enterprise security, a new workflow engine, or a broad schema layer.
First reproduce the exact validator failure from the archived candidate, then
make the smallest scientific-contract change and test both the negative path
and the unchanged readiness path.
