# 更新记录

[English changelog](CHANGELOG.md)

## 0.2.3 — 2026-07-18

### 新增

- 新增按需加载的 **Continuity Protocol（连续性协议）**，用于需要跨会话推进或在人类工程师与 Agent 之间交接的工作。
- 新增按复杂度持久化：普通多阶段工作使用一个精简 work packet；Critical、Orchestrated 或重要跨会话工作才拆分为 `spec.md`、`plan.md` 和 `handoff.md`。
- 为新项目和架构级变更新增项目结构契约，覆盖目录结构、模块职责、依赖方向、入口、数据流、测试布局、扩展点和禁止耦合。
- 新增精选 debug memory：优先搜索既有经验，记录可复用的根因、无效尝试、回归测试与预防措施，并禁止保存密钥和大段原始日志。
- 新增三个可选模板：project map、work packet 和 debug note。

### 调整

- Direct 工作不再默认承担流程文档成本，但模型仍可在文档本身是交付物、项目规范要求或正确性需要时自主创建和更新普通文档。
- Align、Build、Diagnose、Orchestrate、Prove 和 Evolve 只在持久化确有价值时加载连续性协议。
- Prove 在完成前会检查已使用的 spec、plan、项目结构、debug 链接、想法清单和 handoff 是否仍然准确。
- Codex、Claude Code 和跨平台 Skill 元数据统一更新为 `0.2.3`。

### 兼容性与证据

- 对外仍为 14 个 Skill 和 6 个共享引擎；连续性协议不是新的可见 Skill，而是渐进加载的共享协议。
- 当前公开的完整 Agent 工作流认证仍是 v0.2.2 的结果。在连续性协议完成长期项目和跨 Agent 交接验证前，v0.2.3 不冒充新的在线基准测试结果。
