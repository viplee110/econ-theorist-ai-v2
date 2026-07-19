# Held-out case: accident liability and preventive maintenance

This frozen case asks only whether a change in accident liability changes an
operator's maintenance choice and therefore the accident probability.  It is a
small applied-theory mechanism example.  It makes no welfare, optimal-policy,
empirical, legal, or literature-novelty claim.

## Exact environment

One risk-neutral operator chooses one of two actions after observing the
liability rule:

- `routine`: operating return 3 and accident probability 1/2;
- `preventive`: operating return 2 and accident probability 0.

An accident, when it occurs, makes the operator pay liability `L`.  Compare
`L=0` with `L=4`.  Liability is paid only after an accident.  The returns,
accident technology, action set, timing, and risk neutrality are held fixed.
The operator maximizes expected private payoff.

## Exact benchmarks

### `b_routine_fixed_accounting`

Hold the operator's action fixed at `routine` and change only `L` from 0 to 4.
Expected private payoff changes from

`3 - (1/2)(0) = 3`

to

`3 - (1/2)(4) = 1`.

The accident probability remains 1/2.  This is a payoff-mapping comparison,
not evidence of an active maintenance response.

### `b_maintenance_reoptimization`

Allow the operator to choose again after the liability rule is set.

- At `L=0`, routine pays 3 and preventive pays 2, so routine is the strict
  optimum and the accident probability is 1/2.
- At `L=4`, routine pays 1 and preventive pays 2, so preventive is the strict
  optimum and the accident probability is 0.

The exact active channel is:

`liability_rule -> maintenance_payoff_basis -> maintenance_choice -> accident_probability`

The three-step economic spine is: liability changes the expected payoff of
routine maintenance; the strict payoff ranking reverses the maintenance
choice; the changed choice lowers accident probability from 1/2 to zero.

## Research boundary

The target is the operator's maintenance choice and the accident probability.
Victim loss, transfers, enforcement cost, legal feasibility, heterogeneous
operators, social welfare, policy optimality, empirical relevance, and
literature novelty are outside this case.  A correct framing must not infer
any of them from the stated comparison.
