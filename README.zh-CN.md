<p align="center">
  <img src="plugins/goldilocks/assets/logo.png" width="176" alt="Goldilocks 图标：一碗温热的粥">
</p>

<h1 align="center">Goldilocks</h1>

<p align="center"><strong>流程不过量，严谨不缺席，一切刚刚好。</strong></p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.5.0--alpha.1-D4A72C" alt="版本 0.5.0-alpha.1">
  <img src="https://img.shields.io/badge/Direct_AB-114%2F114_passed-2ea44f" alt="Direct 对照：114 项检查全部通过">
  <a href="https://skills.sh/blackstone2333/goldilocks/goldilocks"><img src="https://skills.sh/b/blackstone2333/goldilocks" alt="从 skills.sh 安装"></a>
  <img src="https://img.shields.io/badge/license-MIT-2563eb" alt="MIT 许可证">
</p>

Goldilocks 是一个精简、动态的 Superpowers 替代方案，也是适用于 Codex、Claude Code 及其他兼容 Agent 的 token-efficient AI Agent 工作流。头脑风暴、spec、plan、TDD、debug、连续性、委派、审查、验收和新想法留存等质量保障能力都还在，但只对外显示一个 Skill。

在 v0.4.1 认证的 Direct A/B 对照中，两条路径均通过 114/114 项外部检查；Goldilocks 的处理 token 少 11.5%、累计耗时少 10.9%，按 GPT-5.6 Sol Standard 官方 token 价格计算的成本低 6.3%。这些是已测试编程任务上的实测结果，并非对所有场景都绝对领先的声明。

> 只使用足以维持质量、安全、授权和验收底线的流程。

清晰任务保持 Direct；只有出现具体触发条件才增加结构。Lead 模型把稀缺上下文用在理解意图、架构、整合和最终验收上，把完整、可独立验证的执行合同交给更便宜的工作模型。

Goldilocks 不限定工作领域：软件、研究、分析、文档、演示文稿、表格以及其他结构化交付物，都可以进入同一个路由器。它只决定任务值得使用多少流程和协作；具体领域的制作能力仍由专业 Skill 负责。值得拆分时，单元边界让返工保持局部。因此，短任务或不可拆分的整体创作仍可能全程保持 Direct。

## 安装

不要同时启用 Goldilocks 和 Superpowers。

> **Alpha 实地测试：** 本标签包含仍在观察的成本感知路由、模型命名、路由审查和递归 Usage 回执。只需要稳定的故障解释修复时，请从默认分支安装 `v0.4.2`；两个版本不要同时安装。

### 在 Codex 中直接安装本 Alpha

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.5.0-alpha.1
codex plugin add goldilocks@goldilocks-local
```

安装后新建任务，在 `/hooks` 中核对命令确实来自 Goldilocks，再决定是否持久信任。有效反馈包括：任务类型、可见 `ROUTE` 行、子智能体名称与模型、耗时、最终的原因/修复/验证、Usage 行或未出现的情况，以及相对 Direct 是否更清晰、更快或更省。

### 让 AI 一键安装

把下面整段提示词复制给能够管理自身 Skill 或插件的 Codex、Claude Code、Cursor 等 Agent：

```text
请从 https://github.com/blackstone2333/goldilocks 安装 Goldilocks v0.5.0-alpha.1 预发布版，必须锁定 Git ref v0.5.0-alpha.1；Codex 依次运行 `codex plugin marketplace add blackstone2333/goldilocks@v0.5.0-alpha.1` 和安装 `goldilocks@goldilocks-local`。不要与 Superpowers 或其他 Goldilocks 版本同时启用。先说明这是实验版，只问我一次是否愿意在 /hooks 中持久信任其 Hooks，最后验证安装版本、Hook 状态和可用性，不要修改无关配置。
```

### 任意兼容 Skills 的 Agent

```bash
npx skills add blackstone2333/goldilocks
```

全局安装为 Codex Skill：

```bash
npx skills add blackstone2333/goldilocks --skill goldilocks --global --agent codex --yes
```

安装器支持时，可把 `codex` 换成 `claude-code`、`cursor`、`opencode`、`github-copilot` 或 `gemini-cli`。

### Codex 原生插件

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.5.0-alpha.1
codex plugin add goldilocks@goldilocks-local
```

#### 出现 Hook 授权是正常现象

Codex 原生插件包含本地命令 Hook，因此首次安装时会要求授权；升级、重新安装或刷新插件缓存后，也可能再次询问。这是 Codex 对新的可执行插件副本重新建立信任，并不表示 Goldilocks 把安装环境弄坏了。

**推荐完全信任 Goldilocks 自带的全部 Hook。** 安装完成后，在 Codex CLI 的交互界面中输入 `/hooks`（不是在普通 shell 中执行），检查命令来源确实属于 Goldilocks，然后选择持久的“信任全部”或“始终允许”（具体文字随 Codex 版本而异），不要选择“仅本次允许”。该信任会绑定当前 Hook 定义并供后续任务复用；定义不变时只需完成一次，不应每个任务重复询问。插件更新改变 Hook 哈希后，Codex 出于安全原因可能要求重新审核。

- `recovery_reminder.py`：在专业 Skill 之前注入极小门禁，把重复失败升级为持久连续性，恢复压缩后的任务状态，并加入精简沟通约束。本地审计只保存哈希、有限的复发标志和时间，不保存提示词原文。
- `agent_routing_guard.py`：检查子智能体路由，并把路由元数据保存在插件本地数据目录。Worker 停止后不会被直接记为成功；Lead 重跑验收并由 `record_routing_outcome.py` 记为 verified pass 或 fail 后才闭环，系统只保留证据哈希。
- `update_checker.py`：每天最多访问一次 GitHub，只检查 Goldilocks 清单版本；不会自动安装更新，也不会修改项目文件。设置 `GOLDILOCKS_UPDATE_CHECK=0` 可以关闭这项联网检查。
- `usage_reporter.py`：无需额外调用模型即可汇总本轮各模型的 token 和耗时。Goldilocks 会在最终回答前读取 `--current` 单行回执；若 Codex 尚未写入本轮首个统计检查点则保持静默，不会误报 0。

如果拒绝 Hook 授权，Skill 的文字工作流仍可使用，但自动连续性提醒、路由约束、更新提醒和 token 回执不会运行。授权前也可以直接查看 [`hooks/hooks.json`](plugins/goldilocks/hooks/hooks.json) 中的准确命令。

如果每个任务仍反复弹出授权，先用 `/hooks` 确认选择的是持久信任而非仅允许一次，并检查启动脚本是否在每次运行时重新安装插件或刷新插件缓存。

### Claude Code 原生插件

```bash
claude plugin marketplace add blackstone2333/goldilocks
claude plugin install goldilocks@goldilocks
```

项目级安装、更新和卸载方法见[完整安装说明](docs/installation.zh-CN.md)。

### 更新

仓库和 skills.sh 安装都以 GitHub 为源，但不会静默改写本地正在使用的副本；发布新版本后，需要重新运行对应安装或升级命令。Codex 原生插件每天最多静默检查一次 GitHub：已是最新版或离线时不提示；发现新版本时只提醒一次；未经同意不会自动更新。设置 `GOLDILOCKS_UPDATE_CHECK=0` 可关闭检查。

## 它能做什么

| 内部引擎 | 何时启用 | 结果 |
|---|---|---|
| **Align** | 终局、产品选择、权限或验收存在实质不确定性 | 开工前形成紧凑决策或 spec |
| **Diagnose** | 已知有故障，但原因未知 | 复现、定位根因、聚焦修复、回归证据 |
| **Build** | 需要复用判断、持久计划、分阶段执行或有意识的 TDD | 最小必要计划和连贯执行单元 |
| **Orchestrate** | worktree、独立单元、委派、并行或模型路由能改善交付 | 就绪依赖图和边界清晰的工作合同 |
| **Prove** | 审查、发布、安全、集成或多个重要声明需要证据 | 与风险相称的新鲜检查和 Lead 验收 |
| **Evolve** | 出现有价值的新想法、可复用路径或 Skill 改进 | 留存后续方向或已验证经验，不扩大当前范围 |

这些是内部工作流引擎，不是六个独立公开 Skill。唯一的 `goldilocks` 路由器只加载当前需要的引擎；事实跨越边界时才增加第二个。

## 它如何判断

```mermaid
flowchart TD
    A["收到任务"] --> B{"存在实质不确定性、连续性、风险或值得拆分的就绪工作吗？"}
    B -- "没有" --> C["Direct 退出<br/>最小完整改动 + 决定性检查"]
    B -- "终局不清楚" --> D["Align"]
    B -- "根因未知" --> E["Diagnose"]
    B -- "多阶段工作" --> F["Build"]
    B -- "存在独立就绪单元" --> G["Orchestrate"]
    B -- "发布或较高风险" --> H["Prove"]
    D --> F
    E --> F
    F --> J{"由谁完成最划算且可靠？"}
    G --> J
    J -- "直接做更快" --> K["Lead 实现"]
    J -- "完整、低裁量合同" --> L["Fast 工作成员"]
    J -- "仍有局部专业判断" --> M["Standard 负责人 → 可再派 Fast"]
    C --> N["新鲜验收证据"]
    K --> N
    L --> N
    M --> N
    H --> N
    N --> O["Lead 整合并最终验收"]
    O --> P{"这些知识以后还会有用吗？"}
    P -- "会" --> Q["只保留有用的 spec、plan、handoff、debug 经验、idea 或执行路径"]
    P -- "不会" --> R["完成，不留下流程垃圾"]
    Q --> R
```

不变的是最终质量，而不是流程数量，也不是谁亲手写代码。Goldilocks 不会因为工具箱里有 spec、plan、worktree、子智能体或连续性文档，就强行创建它们。

## 默认 Direct

根路由器不到 300 词。如果没有实质决策、未知根因、连续性需求、外部风险或值得委派的就绪工作，Goldilocks 会在加载任何工作流参考前直接退出。它只检查任务本地事实，完成最小完整改动，并运行一项“结果有错就会失败”的最小检查。

现有 Hook 会加入一条紧凑沟通约束，理念来自 Caveman 和 i-have-adhd（ADHD）：结果先行、省略开工前言、只报告状态变化、日志只留决定性片段；涉及安全或歧义时恢复完整说明。故障任务仍必须交代有证据支持的原因（或明确说明尚未确认）、修复方式和验证结果，避免为了简洁把调试变成黑盒。

同一个 Hook 现在会在专业 Skill 之前加入紧凑的零成本门禁：纯对话跳过；清晰的可执行任务保持 Direct，不加载完整路由器；出现实质不确定性、未知根因、多阶段连续性或有效拆分空间时，明确加载 `goldilocks:goldilocks`。本地审计只记录提示词与工作区哈希、会话/回合标识和时间，因此能够验证门禁是否生效，又不保留提示词内容。

重复失败会获得必要留存，但不会让每个任务都制造文档：同一会话和工作区中，用户第二次确认问题复发时，Goldilocks 强制维护一个 `.goldilocks/ACTIVE.md` 执行前沿，并复用项目现有的 debug 或 validation 记录。症状、证据、已排除方案、**Do not repeat**、精确下一项测试和相关提交都能跨上下文压缩保留。未经验证的修复不进入 Changelog；只有新鲜验收通过的用户可见发布变化才进入。即使上一回合没有及时创建前沿，恢复和压缩 Hook 也会继续提示尚未偿还的连续性债务。

## 连续性，但不滥造文档

Direct 默认不创建流程文档，但当文档本身是交付物或正确性确实需要时，模型仍可自主建文档。只有任务需要跨越上下文压缩、多阶段、等待、用户中途引导、委派或交接时，才启用持久状态。

需要时，Goldilocks 使用清爽、方便人类和其他 Agent 接手的项目记忆：

```text
docs/
├── PROJECT.md          # 项目地图和稳定结构
├── work/               # 当前 spec、plan、工作包和 handoff
├── debug/              # 可复发 bug、根因、解法和回归链接
├── ideas.md            # 当前范围之外的好想法
└── CHANGELOG.md        # 用户可见变化
.goldilocks/
└── ACTIVE.md           # 上下文恢复用的紧凑执行前沿
```

`ACTIVE.md` 记录已完成工作、精确下一步、待处理或已消费的用户引导、仓库证据、验收情况和“不要重复”边界。上下文压缩后，以仓库状态为准，不以过期记忆为准。相似任务可以复用已验证执行路径，但必须先检查失效条件。

## 公司式动态编排

Goldilocks 把委派视为经济决策和组织决策：

- **Lead** 负责用户意图、架构、共享决策、冲突处理、整合和最终验收。
- **Standard** 负责仍需判断的有界领域，并可把判断转化成 Fast 合同。
- **Fast** 接收包含范围、权限、输入、接口、验收和返回证据的完整合同；Fast 是叶子成员。

Fast 指拆解后剩余裁量低，不代表原任务很小。多个独立就绪单元可以并行；不可分割的核心仍由 Lead 处理。并发数量取决于依赖、宿主容量、隔离条件、集成风险和审核吞吐，而不是僵硬的项目规模分级。

### Codex 模型路由

**Fast 基线 → Luna · 编程额度专才 → Spark · Standard → Terra**

- Fast 默认先考虑 `gpt-5.6-luna`，覆盖 focused coding、测试、探索、路由、提取、自动化和边界明确的内容生产。
- `gpt-5.3-codex-spark` 继续作为纯文本编程专才：仅在 Pro 独立额度池可用，且确定性代码批次足以抵消启动成本时优先。
- Standard 在仍需实质领域判断或局部整合时默认使用 `gpt-5.6-terra`；低风险、可客观验收的 Standard 边界任务可以先试一次 Luna，未过质量门槛就升级 Terra。
- Lead 继续负责架构、Critical 工作、共享决策和最终整合；同项目同任务形态的本地证据优先于种子表。

OpenAI 2026 年 7 月 31 日调价后，标准短上下文 token 价格中 Luna 只有 Terra 的十分之一、Sol 的 4%；Codex 套餐估算的 Luna 消息数也约为 Terra 的十倍。价格不能绕过质量、权限、模态和工具门槛。参见[带日期的路由更新](docs/model-routing-update-2026-07-31.zh-CN.md)。

Goldilocks 优先使用宿主明确支持的原生模型。当原生协作接口没有 Spark 或 Luna、但本地 Codex CLI 可以调用时，`dispatch_codex_worker.py` 会通过 `codex exec` 使用指定模型和完整合同。默认 `project` 档位保留仓库规则，同时隔离无关的全局插件、App、MCP、Skill 和 Hook；合同明确需要用户能力时可以选择 `inherit`。Fast 被关闭的是继续分派权，不是普通执行工具。

只有验证过的路由才会开始委派。路由启动失败时，立即回到 Direct 或另一条已验证路径，不在产品任务中消耗 Lead 回合调试工作模型的传输层。子任务事件流可留在 Lead 上下文之外，只向上汇报简洁证据。

目标不是不惜代价压低原始 token。质量和权限是硬门槛，总 token 必须受控；在合格路径之间，再尽量降低高倍率模型额度和关键路径时间。

初始模型种子只供参考，不是永久排行榜：

| 角色 | 起始候选 | 边界 |
|---|---|---|
| Fast 基线 | GPT-5.6 Luna 及其他已验证低成本生产模型 | 完整合同、低剩余裁量、决定性验收 |
| Fast 编程专才 | GPT-5.3-Codex-Spark、Muse Spark 及其他已验证编程模型 | 纯文本确定性批次，独立额度收益足以抵消启动成本 |
| Standard | GPT-5.6 Terra；Luna 低风险首轮；Grok、Claude Sonnet、Gemini Pro、GLM/Qwen 候选 | 有界领域判断和局部整合 |
| Lead | 当前宿主 Lead 模型，如 GPT-5.6 Sol、Claude Opus/Fable 及其他已验证前沿模型 | 意图、架构、关键决策和组合验收 |

模型可用性、工具、隐私、语言、模态和任务质量底线都是硬门槛；同项目同任务形态的近期结果优先于公开排名。参见[机器可读种子表](plugins/goldilocks/skills/goldilocks/assets/model-registry.json)、[当前路由更新](docs/model-routing-update-2026-07-31.zh-CN.md)和[原始方法说明](docs/model-routing-survey-2026-07-18.md)。

## 证据

### v0.4.1 Direct 路径认证

测试使用全新仓库、模型不可见的固定外部验收、Direct/Goldilocks 同波并行、排除预热，并由 GPT-5.6 Sol high 完成简单、中度、复杂三种编程任务。

| 场景 | 每组次数 | 每组验收 | 中位耗时 | 中位官方 API 成本 | 中位处理 token |
|---|---:|---:|---:|---:|---:|
| 简单 | 3 | 9/9 | **−2.6%** | **−24.3%** | **−13.8%** |
| 中度 | 5 | 60/60 | **−30.1%** | **−13.6%** | **−20.4%** |
| 复杂 | 3 | 45/45 | **−4.2%** | **−4.9%** | **−14.5%** |

每组共 11 次运行，两条路径都通过 **114/114** 项外部检查。Goldilocks 累计耗时低 10.9%，按 GPT-5.6 Sol Standard 官方 token 价格计算的成本低 6.3%，处理 token 低 11.5%。这证明当前 Direct 分支在这些任务上有效；发现需求、debug、长期连续性和委派仍需要更多真实项目反馈。参见[报告和机器可读数据](evals/results/2026-07-26-v041-direct-depth-ab.md)。

### Goldilocks 对 Superpowers

Goldilocks 只提出一个克制的公开结论：在已测试工作流表面上，它是更好的 Superpowers 替代方案。

| 测试 | Goldilocks | Superpowers | 结果 |
|---|---:|---:|---|
| 8 场景指令压力测试 | **98.9/100** | 79.2/100 | Goldilocks 领先 8/8，规则文本少 86.2% |
| Three Bears 成功交付 | **27/27** | 8/27 | Goldilocks 保持 100% 实测安全 |
| 每次成功交付总 token | **112,285** | 289,333 | Goldilocks −61.2% |
| 每次成功交付耗时 | **143.2 秒** | 361.3 秒 | Goldilocks −60.4% |
| 每次成功交付 Skill 活动 | **1.1** | 10.9 | Goldilocks −89.8% |

在双方都成功的 8 个完全相同单元里，Goldilocks 总 token 少 30.6%、耗时少 7.7%、工具调用少 28.6%、Skill 活动少 66.7%。参见[完整正面对照报告](benchmarks/GOLDILOCKS-VS-SUPERPOWERS.zh-CN.md)和[公开数据](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/head-to-head.json)。

这些结果支持用 Goldilocks 替换 Superpowers，但不能证明它在所有工作流、模型、仓库或供应商上都绝对领先。欢迎继续做项目测试并反馈。

## 当前状态

Goldilocks `v0.5.0-alpha.1` 是自愿安装的实地测试版本。它在已测试工作流表面上能够更好地替代 Superpowers，但新增路由和 Usage 行为仍需更多真实项目反馈，再决定是否发布稳定 `v0.5.0`。[欢迎提出意见](https://github.com/blackstone2333/goldilocks/issues)。

Goldilocks 采用 MIT 许可证，由 Charles Roc 和贡献者开发。它是独立实现，受到 Superpowers、Grill 式决策前沿提问、Ponytail 原生/复用优先理念、Caveman 和 ADHD 的启发；这些项目并未为 Goldilocks 背书。详见[第三方声明](plugins/goldilocks/THIRD_PARTY_NOTICES.md)。
