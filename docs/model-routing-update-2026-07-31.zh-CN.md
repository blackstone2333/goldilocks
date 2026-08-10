# 模型路由更新 — 2026-07-31

本文记录 Goldilocks v0.4.5 的证据和决策。它只更新当前路由，不会用新价格改写旧基准测试当时的成本。

> 历史快照：v0.5.0 已用新的生产角色取代下述路由——Terra Medium 是 Standard 主负责人，Spark XHigh 是确定性编程 Fast 叶子，Luna Max 是 Economy。下方带日期的价格仍作为原始证据保留。

## 当前 OpenAI 成本关系

官方标准短上下文 API 价格，单位为美元 / 100 万 token：

| 模型 | 输入 | 缓存输入 | 输出 | Goldilocks 起始角色 |
|---|---:|---:|---:|---|
| GPT-5.6 Sol | $5.00 | $0.50 | $30.00 | Lead / Critical / 最终整合 |
| GPT-5.6 Terra | $2.00 | $0.20 | $12.00 | Standard |
| GPT-5.6 Luna | $0.20 | $0.02 | $1.20 | Fast |

三项价格中，Luna 都只有 Terra 的十分之一、Sol 的 4%。Codex 套餐估算中，Luna 可用消息数也约为 Terra 的十倍。GPT-5.3-Codex-Spark 的 Pro 编程额度池仍有独立计量优势，但这不代表它应当成为所有 Fast 工作的默认模型。

来源：[OpenAI API 价格](https://developers.openai.com/api/docs/pricing)、[Codex 套餐估算](https://learn.chatgpt.com/docs/pricing)和 [OpenAI 工作负载选型指南](https://developers.openai.com/tracks/building-agents#how-to-choose)。

## v0.4.5 起始路由

- **Luna 是通用 Fast 基线**：focused coding、测试、探索、提取、路由、自动化和边界明确的内容生产都先考虑它。
- **Spark 是可选的编程额度专才**：用于纯文本、确定性代码批次，且独立额度收益必须足以抵消外部启动成本。
- **Terra 是 Standard 基线**：适合仍需实质领域判断、跨文件协调或局部整合的有界任务。低风险、接口稳定、可决定性验收的 Standard 边界任务可先试一次 Luna；质量未过线就升级 Terra。
- **Sol 继续担任 Lead**：负责意图、架构、信任边界、Critical 工作、共享决策、最终整合和组合验收。

模型可用性、工具、模态、隐私、权限和任务质量底线永远先于价格。角色在拆解后判定：Fast 指剩余裁量低，不代表原任务小。

## 本地调用审计

对近期 Codex 项目会话进行保护隐私的审计后发现，Goldilocks 的“触发”和“真正编排”已经脱节：

- 根 Hook 在 7 月 28 日注入 10 次、7 月 29 日 25 次、7 月 30 日 45 次；
- 最近三个主要开发项目虽然大量并行调用本地工具，但没有派发 Goldilocks Luna、Terra 或 Spark 子任务；
- 后续一项任务确实创建了两个子智能体，但两者都继承 Sol，没有走显式 Fast 或 Standard 路由；
- 历史路由库中存在已停止的 Spark、Luna 和 Terra worker，证明这些通道以前调用成功；但所有 `verified_passes` 都是 0。

这是一项运行审计，不是模型质量基准。它说明模型可以调用，但 Lead 经常只读完精简根 Skill 就自己做到底，没有进入 `orchestrate.md`；同时系统把 worker 停止当成审计终点，没有记录最终验收。

因此 v0.4.5 增加两项控制，但不会把所有任务强制编排：

1. 明显包含多个独立单元的实现任务，Lead 动手前必须做一次常数时间的 make-or-delegate 比较；当交代和审核成本更高时，仍可选择 Direct；
2. 原生 worker 停止只算观察，Lead 重跑组合验收并记录 `verified_pass` 或 `verified_fail` 后才闭环；只有 verified pass 可以进入可复用执行记忆。

系统不会保存私有提示词、源码或验收原文。门禁记录使用哈希，新验收记录器也只保存证据哈希。
