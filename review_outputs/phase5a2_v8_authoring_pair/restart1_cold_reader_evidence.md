# Restart 1 isolated cold-reader evidence

Status: **FROZEN**. Two fresh readers received only one final
`economist_memo` each. They had no filesystem or network access and did not see
the CASE, evaluator key, interface name, sibling memo, reports, receipts, or
candidate structure. Each free retell was frozen before the common five probes
were supplied.

The reader labels were revealed only after both probe responses returned:

- Reader A = semantic final memo.
- Reader B = transaction final memo.

## Reader A free retell

> 这份 memo 研究的是：失败后退还出资，什么时候会真正改变公共品是否被提供，而不只是改变既定行为下的收益记账。基准对比中，如果把策略固定不变，退款只会把收益从负三分之一变为正三分之一，提供水平仍是三分之一；但一旦允许参与决策内生化，退款会改变失败状态下的收益，从而改变发起人在最初是否参与时的严格比较。发生行为变化的是发起人的初始参与选择；其他参与者的具体行为如何变化，无法从 memo 确定。逆向归纳的核心结果是：不退款规则下提供为零，退款规则下提供为三分之一。因此，直接机制是“支付规则改变失败收益—初始参与改变—最终提供改变”，而不是退款直接改变已经固定的后续行为。结论仅适用于所述的两人序贯门槛博弈及其既定假设；这些具体假设是什么，无法从 memo 确定。

### Reader A probe response

1. 研究问题是：失败出资被退还何时会改变实际提供，而不只是改变收益记账？第一个基准固定策略，退款使收益从 −1/3 变为 +1/3、提供仍为 1/3；第二个基准允许初始参与内生化，逆向归纳下不退款与退款的提供分别为 0 和 1/3。
2. 退款直接改变失败状态下的收益，并因此改变发起人最初参与时的严格收益比较。它不是直接改变最终提供。
3. 改变的是发起人的初始参与选择；既定的后续条件策略不改变。后续行动者的具体身份与策略内容无法从 memo 确定。
4. 不退款时，发起人的初始严格比较导致不参与，因此提供为 0；退款改变失败收益和这项比较，使参与发生，随后既定后续行为产生 1/3 的提供。更细的策略路径无法从 memo 确定。
5. 结论仅限于这一个两人序贯门槛博弈及其未在 memo 中展开的假设。不能据此推出退款一般都会提高提供，也不能把结果归因于后续条件策略发生变化。

Keyed result: `R-PARTIAL`, burden `H2`. The reader recovered the exact
accounting, both provision comparisons, the initiator margin, and the scope.
One local memo rewrite must identify the follower's high/low conditional rule
and enumerate the fixed assumptions.

## Reader B free retell

> 这份 memo 研究的是：即使后行动者的反应完全不变，只在项目失败时发生的退款，是否仍能改变门槛项目最终能否被启动和供给。它比较无退款与有退款两种情形，同时区分两层分析：固定策略下的核算只展示退款如何改变各结果对应的收益；顺序博弈中的逆向归纳则允许参与者据此重新选择，从而决定实际是否发起项目。直接机制不是退款改变了后行动者的高、低状态反应，而是失败状态下的支付进入了先行动者“严格选择发起还是放弃”的收益比较。因此，发生变化的是先行动者的初始参与行为，后行动者的后续行为保持不变。核心数值结果是：逆向归纳下，无退款时供给为 0，有退款时为 1/3；这个 1/3 究竟表示供给概率、状态占比还是其他量，无法从 memo 确定。结论只覆盖所指定的两人顺序门槛博弈；退款大小、完整收益结构、状态分布以及结论能否推广到其他博弈，均无法从 memo 确定。

### Reader B probe response

1. 精确问题是：当退款只影响失败状态、后行动者的行为不变时，它能否改变项目供给？两个分析基准是固定策略核算与顺序重新优化：前者隔离收益映射，后者用逆向归纳确定实际发起；两者都涉及无退款与有退款的对比。
2. 退款直接改变失败状态下的支付，从而改变发起者“发起还是放弃”的严格收益比较。它不直接改变后行动者的反应。
3. 改变的是先行动者的初始参与选择。后行动者在高、低情形下的条件策略不变。
4. 逆向归纳时，失败状态支付的变化使先行动者在一个原本不会参与的早期内生边际上选择发起，因此 memo 报告供给由无退款时的 0 变为有退款时的 1/3。1/3 的具体计算过程及其量纲无法从 memo 确定。
5. 结论仅适用于指定的两人顺序门槛博弈，不能据此推出其他博弈或一般退款制度中的普遍结论。也不能推出退款改变了后行动者策略，或确定 1/3 在模型中的具体含义。

Keyed result: `R-PARTIAL`, burden `H2`. The reader recovered the actor split,
no-start logic, causal direction, and scope. One local memo rewrite must state
the fixed-strategy quantities and explain that `1/3` is the fixed high-type
probability and hence the provision probability conditional on initiation.

## Reader comparison

Neither memo is reader-dominated. A preserves exact accounting but omits actor
and assumption detail; B preserves the actor/strategy distinction but omits
the exact accounting and probability basis. Both require one local rewrite,
so the preregistered reader-burden comparison is a tie at `H2`.
