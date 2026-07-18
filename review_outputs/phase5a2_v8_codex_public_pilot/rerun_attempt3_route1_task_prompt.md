# Prompt for the R3 guaranteed-service ordinary-model task

Open a new Codex task with `C:\tmp\etai-v8-r3` as its selected working
directory, then paste the text below exactly.

> 这是 Econ Theorist AI v2 的一次公开、单 agent、真实同案修订盲测。当前工作
> 目录是 `C:\tmp\etai-v8-r3`。我明确授权你仅在这个目录中初始化并执行
> `CASE.md` 所描述的新公开测试项目。`CASE.md` 中的 guaranteed-service 路线是
> 研究者已经作出的本案例 reframe 输入；它不是 G1 决定，也不授权你确认任何
> 人类 gate。
>
> 先完整读取 `CASE.md` 和
> `.agents/skills/econ-theorist-v2/SKILL.md`，严格按已安装 skill 与 engine
> bridge 执行。使用当前普通/中等模型完成生成，不要切换高智力模型，不要生成
> 或调用任何 subagent。
>
> 已安装 launcher 是 `.venv\Scripts\etai.exe`。每次调用 helper 时把这个精确
> 路径传给 `--etai`；不要创建新的 virtual environment，不要在 `run/` 中重新
> 安装 wheel。
>
> 这是盲测，不是代码开发。不要读取父目录、兄弟目录、源码仓库、Git 历史、
> tests、fixtures、R2 或其他旧 pilot、旧候选、评价标准、其他对话或网络；不要
> clone、pull 或修改 engine。只允许使用本目录中的已安装 wheel、skill、
> `CASE.md`、`capture_codex_invocation.py`，以及 engine 返回的 CLI 响应和
> WorkPacket。
>
> 每次 bridge 调用都使用 `capture_codex_invocation.py`，并在 `run/` 下使用全新、
> 不重复的 request/stdout/stderr/metadata 文件名。凡是从候选源完成的
> `complete` 调用，必须把 WorkPacket 声明的精确 candidate path 同时传给
> `--candidate-source`。如果 capture 返回证据绑定错误、候选在调用中变化或
> digest 不匹配，立即停止并如实报告，不能把它算作有效路线结果。
>
> 让 engine 单独选择和排序路线；不要从记忆补充工作流，不要直接写 canonical
> ObjectStore，不要重新决定 CASE 中已经给定的 guaranteed-service 分支，也
> 不要添加价格、匹配、拥堵、配给等新经济力量。严格遵循每个 WorkPacket 的
> candidate authoring contract、声明的候选路径和修复预算。只有 bridge 明确
> 返回 canonical commit 才能报告提交成功。
>
> 到达人类决策边界、协议自然停止点，或确实耗尽 engine 声明的修复预算时停止。
> 不要继续替人做决定。最后在 `run/` 下写一份新的 `*-agent-report.md`，列出每次
> 调用的 request、stdout、stderr、metadata、captured request/candidate 路径，
> 以及 route outcome、canonical head、是否发生 commit、是否触发人类 gate。
> 明确记录可观察的模型标签；如果无法独立确认实际 provider/backend 模型，就
> 如实写明不可确认。
