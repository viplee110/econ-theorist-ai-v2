## Verdict

**Major revision / 暂不应通过 G1。**

该候选在结构上是一个清晰的概念清单，但尚不是闭合的动态博弈分解。它没有定义完整的公共状态、状态依赖行动集合、逐行动收益、Bayes 更新和 certificate-stock 转移核，因此目前无法判断策略最优性、稳态分布或任何真正的反馈。

尤其重要的是：在候选字面设定下，只要至少一个有效 certificate 可见且 \(c>0\)，inspection 就被直接购买 certified seller 严格支配。由此，图中声称的 inspection–trade–stock 闭环目前并不成立。候选选择 `proposed_action: revise` 是对的，但“机制和 separating benchmarks 已足够具体”的判断过于乐观。

## Adversarial audit

### 1. 公共状态、行动和收益没有闭合——致命

候选只有抽象节点，没有按公共状态定义博弈。至少应区分

\[
z_t=(z_{1t},z_{2t})\in\{00,10,01,11\},
\]

其中 \(z_{it}\) 表示 seller \(i\) 是否持有可见 certificate，并说明 certificate 的身份、年龄及其认证对象。

当前遗漏包括：

- seller 在 \(z_i=0,q_i=H\)、\(z_i=0,q_i=L\)、\(z_i=1\) 下分别有哪些行动；
- 已有 certificate 时是否能重复认证、撤销或弃置；
- buyer 在每个 \(z\) 下能否买任一 seller、inspect 哪一个 seller、exit；
- inspection 后看到 \(H/L\) 时能否改买另一 seller；
- 两个 certificate 同时可见时的 tie-breaking；
- 每个行动的当期收益和 continuation payoff。

候选甚至没有独立的 seller certification-choice 节点，只有 eligibility institution。[PrimitiveGraph 的行动与收益节点](<C:/Dropbox/Shufe/Research/Project/Search on Graphs/.etai-v5_4d2-economy-tier-20260716-c8c539e/.econ-theorist/staging/run_op_022ec3249664a8c635ac02d05e2b332095e28205828dc370/candidate.json:64>)

此外，把 buyer value、seller margin 和 discounting 一并称作“normalizations”不准确：只有价值单位可以正规化为一；margin、\(c\) 和 discount factor 决定策略和动态，属于实质性 primitives。

### 2. certificate 可见时 inspection 被支配——结构性结论

按当前字面模型：

- truthful certificate 保证成功服务；
- 成功服务给 buyer 最高值 \(1\)；
- 未声明购买价格、失败损失之外的额外收益或 certified seller 的溢价；
- inspection 成本为 \(c>0\)。

因此，只要 seller 1 有有效 certificate：

\[
U(\text{buy certified 1})=1,
\]

而任何先 inspection 的策略，即使之后仍可买 certified seller，其收益至多为 \(1-c<1\)。所以：

- \(z=10\) 或 \(01\)：inspection 严格被支配；
- \(z=11\)：没有 uncertified seller 可供 inspection；
- 只有 \(z=00\) 时 inspection 才可能活跃；
- 若 \(c=0\)，也至多是弱支配或无差异。

这不是可忽略的小细节，而是机制边界。若作者希望“certificate 可见时仍有 search”，必须引入价格差异、certificate 过时风险、容量匹配、配给或多维质量等新的实质性摩擦。

### 3. certificate-stock transition law 不存在——致命

候选只写了“发行形成 stock”和“交易消耗 certificate”两条箭头，[但没有状态方程](<C:/Dropbox/Shufe/Research/Project/Search on Graphs/.etai-v5_4d2-economy-tier-20260716-c8c539e/.econ-theorist/staging/run_op_022ec3249664a8c635ac02d05e2b332095e28205828dc370/candidate.json:77>)。

最严重的语义冲突是：seller 每期观察“current capacity”，但 certificate 可以跨期存续。如果 capacity 下一期重新抽取，那么昨天高容量时获得的 certificate 今天为什么仍然 truthful？必须二选一：

- certificate 锁定一单位高质量服务，直至该单位售出；或
- certificate 只认证当期 capacity，期末自动失效。

第二种选择基本消灭跨期 stock channel；若要保留该研究问题，最小选择通常是第一种。

### 4. 当前所谓 feedback 主要是状态分布效应，不是真正闭环——致命于当前机制表述

图中表面上存在

\[
stock\to posterior\to inspection\to trade\to stock.
\]

但在 inspection 活跃的 \(z=00\) 状态，没有 certificate 可以被交易消耗；在 certificate 被消耗的 \(z\neq00\) 状态，inspection 又被支配。因此，这条路径在同一状态下的边际作用为零。

当前能够成立的最多是：

\[
k\to certification\to \Pr(z=00)\to aggregate\ inspection,
\]

即 \(k\) 改变公共状态的占用分布，从而改变 buyer 遇到可搜索状态的频率。

要构成真正战略反馈，还需明确：

\[
inspection/trade\ allocation
\to seller\ continuation\ value
\to future\ certification
\to stock\ transition
\to future\ inspection.
\]

候选没有 buyer allocation 到 seller continuation value、再到 certification choice 的边。[现有边集合](<C:/Dropbox/Shufe/Research/Project/Search on Graphs/.etai-v5_4d2-economy-tier-20260716-c8c539e/.econ-theorist/staging/run_op_022ec3249664a8c635ac02d05e2b332095e28205828dc370/candidate.json:75>)

### 5. benchmarks 没有在共同状态和行动集合下隔离机制——致命

- **Non-consumable certificate benchmark**：可以只改 depletion 参数，但必须先解决永久 certificate 与每期 capacity 重抽之间的 truthfulness 冲突。
- **Fixed uncertified composition**：直接把 posterior 固定为 \(k\)-invariant 通常违反 Bayes consistency。必须把它明确标为 partial-equilibrium accounting exercise，或提供一个可实现该 posterior 的外生 replacement/garbling process。
- **Exogenous inspection**：候选自己承认它改变了 action rule；这不是同一行动集合下的均衡比较。[“Common action set apart from…”](<C:/Dropbox/Shufe/Research/Project/Search on Graphs/.etai-v5_4d2-economy-tier-20260716-c8c539e/.econ-theorist/staging/run_op_022ec3249664a8c635ac02d05e2b332095e28205828dc370/candidate.json:69>)
- **Mechanical cheaper-certification benchmark**：当前 decomposition 中没有“固定 certification、inspection、trade policies 和状态分布，只改变 seller 的 \(k\) 支出”的 accounting placebo，因此没有真正隔离机械成本效应。

GateDossier 把 belief updating 和 fixed-composition implementation 归为普通 scope risk；实际上它们是模型存在性与 benchmark 可解释性的前置条件。[当前风险表述](<C:/Dropbox/Shufe/Research/Project/Search on Graphs/.etai-v5_4d2-economy-tier-20260716-c8c539e/.econ-theorist/staging/run_op_022ec3249664a8c635ac02d05e2b332095e28205828dc370/candidate.json:119>)

## 最小修复方案

1. **锁定 certificate 语义。**  
   规定 certificate 对应一单位已确认的高容量服务；该单位在售出前保持有效。持有未售 certificate 的 seller 不重新抽取该单位的 capacity。

2. **写出最小状态、时序、行动和收益。**  
   采用 \(z\in\{00,10,01,11\}\)，逐状态列出 seller 和 buyer 行动。最低限度写明

   \[
   u_B=q_j-c\,1\{\text{inspect}\},\qquad
   u_i=mq_ix_i-ka_i+\delta E[V_i(z')].
   \]

   同时规定 inspection 后的完整 contingent action set。

3. **加入闭合转移律。**  
   若 \(a_{it}\) 是新发行、\(x_{it}\) 是向 seller \(i\) 的交易：

   \[
   \tilde z_{it}=\max\{z_{it},a_{it}\},\qquad
   z_{i,t+1}=\tilde z_{it}(1-x_{it}),
   \]

   并规定容量重抽、Bayes posterior、同时认证和双 certificate 时的处理。

4. **明确记录 dominance。**  
   写入一个正式边界：\(c>0\) 且 certificate 有效时 inspection 严格被支配。因此

   \[
   I(k)=\pi_k(00)\,I_k(00).
   \]

   这会把研究问题精确分解为“零-certificate 状态占用效应”和“该状态内的 conditional inspection effect”。

5. **对 feedback 做非零检验。**  
   检查 inspection 是否真的改变 seller-specific trade probability、continuation value 和下一期 certification。若其中任一链接恒为零，就把贡献改称“endogenous state-distribution channel”，不要称 closed-loop feedback。

6. **重做 benchmark ledger。**  
   每一行保持同一 \(z\)、同一物理行动集合和同一收益定义，只改变一个对象：

   - depletion parameter；
   - posterior/transition kernel；
   - buyer strategy 是否冻结；
   - 全部 policies 与状态分布冻结、仅改变 \(k\) 的 accounting placebo。

修复后再讨论 equilibrium selection、稳态唯一性和 welfare 定义。当前最先要解决的不是 selection，而是模型是否已经定义成一个一致的动态博弈。本次审查未修改文件或系统状态。