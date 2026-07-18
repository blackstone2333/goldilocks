<p align="center">
  <img src="plugins/goldilocks/assets/logo.png" width="176" alt="Goldilocks 的金色热粥图标">
</p>

<h1 align="center">Goldilocks</h1>

<p align="center"><strong>流程不多不少，质量刚刚好。</strong></p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.4-D4A72C" alt="版本 0.2.4">
  <img src="https://img.shields.io/badge/Three_Bears-27%2F27_passed-2ea44f" alt="Three Bears：Goldilocks 27/27 通过">
  <a href="https://skills.sh/blackstone2333/goldilocks/goldilocks"><img src="https://skills.sh/b/blackstone2333/goldilocks" alt="从 skills.sh 安装"></a>
  <img src="https://img.shields.io/badge/license-MIT-2563eb" alt="MIT License">
</p>

Goldilocks 是一套面向 Codex 的动态工作流插件，核心是我们提出的 **Just-Necessary Principle（刚好必要原则）**：

> 只使用维持固定质量、安全、授权与验证底线所必需的最少流程。

它提供与 Superpowers 兼容的工作流入口，但不会强迫每个任务加载整套流程。头脑风暴、计划、TDD、系统调试、worktree、委派、审查、验证、分支收尾和 Skill 编写能力都保留，只在任务确实需要时加载。

## 为什么做 Goldilocks

- **动态流程深度：** Direct、Fast、Lead、Critical 四类任务使用不同流程量，但验收标准不降级。
- **渐进式加载：** 十三个兼容入口共享六个能力引擎，不复制十四套冗长流程。
- **原生与复用优先：** 先检查现有项目方法、标准库、成熟库和平台原生能力，再考虑自造方案。
- **只问关键问题：** 只有答案会实质改变终局、安全、范围或授权时才询问用户。
- **记录新想法但不扩张范围：** 有价值的旁支想法会留到后续迭代，不会偷偷塞进当前任务。
- **证据先于完成声明：** 信心、旧测试结果和子代理汇报都不能替代针对当前结果的新证据。
- **该并行时并行：** 计划完成后，独立且有意义的单元默认交给合适的工作模型，Lead 保留架构、审核与集成。
- **模型性价比路由：** 先过任务质量门，再比较成本；Codex Pro 对符合条件的 Fast 工作优先使用独立额度通道的 GPT-5.3-Codex-Spark。

## 证据：Goldilocks vs Superpowers

Goldilocks 对外只主张一个经过验证的窄结论：在已测试的工作流范围内，它是一个比 Superpowers 更可靠、更高效的**替代方案**。下面两轮验证回答不同问题，不把设计评分和真实运行成本混成一个总分。

### 测试一：指令层压力测试

最初的设计测试包含 8 个隔离场景。当时 Goldilocks 还叫 `just-necessary`，因此这轮证明的是 Goldilocks 的架构来源，不是正式版本的真实运行性能。Goldilocks 设计平均得分 **98.9/100，Superpowers 为 79.2/100**；8 个场景全部领先，规则文本少 **86.2%**。

<p align="center">
  <img src="benchmarks/assets/instruction-stress-head-to-head.svg" width="960" alt="指令层压力测试：Goldilocks 前身在 8 个场景中全部领先 Superpowers，规则文本少 86.2%">
</p>

### 测试二：真实 Agent 工作流认证

`v0.2.2` 认证构建使用 GPT-5.6 Terra / low 测试了 Baby、Mama、Papa 三档共 9 个任务；每个任务运行 3 个全新隔离项目，每套工作流 27 次尝试。完整探索实验共有 135 个有效 turn；公开的替代结论只使用其中 **54 个 Goldilocks/Superpowers 正面对照 turn**。

<p align="center">
  <img src="benchmarks/assets/agentic-certification-head-to-head.svg" width="960" alt="真实 Agent 工作流认证：Goldilocks 成功交付 27/27，Superpowers 为 8/27；按每次成功交付计算，Goldilocks 所有成本维度均更低">
</p>

Goldilocks **27/27** 成功交付，测得安全率 100%；Superpowers 成功 **8/27**，安全率 88.9%。Superpowers 有 19 次在修改源码前停止，因此只看原始总成本会错误奖励“没有交付”。

在双方都成功的 8 个完全相同样本里，Goldilocks 少用 30.6% 总 token、7.7% 时间、28.6% 工具调用和 66.7% Skill 活动；非缓存输入高 9.7%，这是同成功样本中唯一没有领先的效率指标。把全部尝试（包括失败）计入并除以成功交付数后，Goldilocks 少用 61.2% 总 token、70.5% 非缓存输入、60.4% 时间、55.4% 工具调用和 89.8% Skill 活动。

详细数据见[两轮正面对照报告](benchmarks/GOLDILOCKS-VS-SUPERPOWERS.zh-CN.md)、[完整运行认证](benchmarks/three_bears/results/2026-07-18-terra-low-full-certification.md)、[测试方法](benchmarks/three_bears/README.md)、[正面对照数据](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/head-to-head.json)和[完整逐格审计数据](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/results.json)。

## 安装

使用跨平台 `skills` CLI 安装完整的 Superpowers 兼容套件：

```bash
npx skills add blackstone2333/goldilocks --skill '*' --global --agent codex --yes
```

其他平台把 `codex` 替换为 `claude-code`、`cursor`、`opencode`、`github-copilot` 或 `gemini-cli`。如果只需要可独立工作的 Just-Necessary 核心路由器，把参数改为 `--skill goldilocks`。

Codex 原生插件：

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

Claude Code 原生插件：

```bash
claude plugin marketplace add blackstone2333/goldilocks
claude plugin install goldilocks@goldilocks
```

不要同时启用 Goldilocks 和 Superpowers。项目级安装、更新命令、平台 ID 和兼容说明见[完整中文安装文档](docs/installation.zh-CN.md)。

## 包含哪些能力

Goldilocks 暴露了替换 Superpowers 所需的熟悉入口：

| 需求 | 入口 |
|---|---|
| 对齐不明确的终局 | `brainstorming` |
| 编写或执行实现计划 | `writing-plans`、`executing-plans` |
| 通过聚焦测试实现功能 | `test-driven-development` |
| 先定位根因再修复 | `systematic-debugging` |
| 隔离或拆分工作 | `using-git-worktrees`、`dispatching-parallel-agents`、`subagent-driven-development` |
| 请求或处理代码审查 | `requesting-code-review`、`receiving-code-review` |
| 验证完成并收尾分支 | `verification-before-completion`、`finishing-a-development-branch` |
| 创建或改进 Skill | `writing-skills` |

显式的 `goldilocks` 路由器替代 `using-superpowers`。它不会被自动注入每个任务，因此简单任务可以走零工作流 Skill 读取的 Direct 路径。

这些兼容入口按需加载六个共享引擎：

1. **Align：** 终局、关键决策、验收条件。
2. **Diagnose：** 复现、追踪、假设、根因。
3. **Build：** 计划、聚焦 TDD、连续执行。
4. **Orchestrate：** worktree、委派、模型路由、集成责任。
5. **Prove：** 审查、验证、授权、分支完成。
6. **Evolve：** 新想法记录、复盘和 Skill 迭代。

对于需要跨会话推进或交给其他工程师接手的工作，六个引擎共享一套轻量的 **Continuity Protocol（连续性协议）**。它优先复用仓库现有文档结构；没有约定时，才按需保存项目结构图、单一工作包或拆分的 spec/plan/handoff、精选 debug 经验、延期想法和面向用户的 changelog。Direct 任务默认不创建工作流记录，但当文档本身是交付物或正确性所需时，模型仍可自主创建或更新文档。它也不会增加新的可见 Skill 或执行引擎。

针对多单元计划，共享的 **Model Routing Protocol（模型路由协议）** 会把机械代码、聚焦测试、fixture 和探索交给合适的 Fast/Standard 工作模型，Lead 保留复杂核心与组合验证。模型选择综合质量门、公开与本地证据、每次成功交付成本、延迟、置信度、时效性和 Pareto 候选集。详见[模型路由公开筛查报告](docs/model-routing-survey-2026-07-18.md)。

## 公开模型路由种子

下面的种子数据截至 **2026-07-18**。它是模型路由的初始参考，不是永久排行榜，也不意味着模型必须机械地调用某个名字。可用性、工具权限、上下文、模态、语言、数据政策和任务风险属于硬门槛；同仓库、同任务形态的近期本地证据优先于公开种子。未列出的模型只要通过同样的门槛，仍然可以参与选择。

### 选择标准

1. 先检查上述硬门槛。
2. 低于任务质量线的候选直接淘汰，即使免费也不选。
3. 使用加权几何平均估算质量，避免关键短板被平均数掩盖：`Q = 100 × product(score_i ^ weight_i)`。
4. 计算完整的成功交付成本，而不是只看 token 单价：`CostSuccess = (直接成本 + 重试 + 审核 + 集成) / P(success)`。
5. 先保留质量、成本和延迟的 Pareto 候选集，再用对数性价比公式处理同档候选：`Value = Q^1.5 × reliability × confidence / ((1 + ln(1 + CostSuccess/Cref))^0.65 × (1 + ln(1 + latency/Lref))^0.35)`。

订阅额度按机会成本计算，不视为零成本；独立额度通道可以降低成本，但不能降低质量或安全门槛。数据过时、模型版本或 Agent harness 不匹配、样本量太小、缺少领域证据、没有本地复现，都会降低结论置信度。

### 任务画像与初始质量线

| 任务画像 | 默认角色 | 质量线 | 重点证据 |
|---|---|---:|---|
| 机械编辑 | Fast | 65 | 本地验收、Aider 编辑正确率、格式可靠性、速度 |
| 测试编写 | Fast 或 Standard | 70 | 本地回归/变异检测、SWE-bench、Terminal-Bench、编辑正确率 |
| 仓库级实现 | Standard | 75 | SWE-bench、Terminal-Bench、本地仓库成功率、编辑正确率 |
| 探索与调查 | Fast | 60 | 本地摘要价值、工具可靠性、速度、上下文适配 |
| 审查与安全 | Lead | 85 | 本地缺陷发现、仓库 Agent 证据、推理与安全领域证据 |
| 前端与多模态 | Standard 或 Lead | 75 | 本地视觉验收、领域证据、模态与工具可靠性 |

这些只是初始质量线，不是所有环境通用的考试分数。Critical 工作不能只凭性价比分配。测试可以交给工作模型编写和局部执行，但 Lead 必须审核断言，并在集成工作区重跑组合验证。

### 初始角色划分

| 角色 | 当前种子 | 较低置信度候选 | 工作边界 |
|---|---|---|---|
| Fast | GPT-5.3-Codex-Spark；GPT-5.6 Luna；Muse Spark 1.1；GLM-5.1 | MiniMax-M3；DeepSeek V4 Pro | 机械代码、fixture、聚焦测试、搜索、窄范围文档和确定性检查 |
| Standard | GPT-5.6 Terra；Grok 4.5；GPT-5.6 Luna；Muse Spark 1.1；Claude Sonnet 5；Gemini 3 Pro；GLM-5.1 | Qwen3.7 Max | 接口稳定、边界明确、可以独立验收的跨文件实现 |
| Lead | Claude Opus 4.8；Claude Fable 5；GPT-5.5 | Kimi K3 | 模糊需求、架构、复杂共享逻辑、Critical 判断、审查、冲突处理和最终集成 |

在 Codex Pro 中，GPT-5.3-Codex-Spark 因独立使用额度降低了机会成本，是符合条件的 Fast 纯文本任务的第一候选。它**不负责**架构、模糊的仓库级修改、安全或 Critical 决策、视觉/浏览器工作、最终审查和集成。Spark 不可用或达不到质量线时，优先考虑 Terra、Luna 等高效 Codex 工作模型。宿主选择但未出现在当前注册表里的高级主模型，只要通过同样的门槛，仍然可以承担 Lead。

### 可比公开数据切片

这份小型切片只包含采集时同时拥有可比 Terminal-Bench 2.1 条目和 Artificial Analysis 数据的模型。“示例性价比”只在这个可比集合里归一化，**不是通用模型排行榜**。

| 模型 | Terminal-Bench 2.1 | TB 报告成本 | AA 混合 $/1M | AA 端到端延迟 | 示例性价比 |
|---|---:|---:|---:|---:|---:|
| Grok 4.5 | 79.3% | $134.09 | $1.35 | 17.74s | 100.0 |
| Muse Spark 1.1 | 76.2% | $198.05 | $0.78 | 24.10s | 94.0 |
| Claude Opus 4.8 | 78.9% | $286.94 | $3.85 | 45.91s | 91.3 |
| GPT-5.6 Luna | 75.7% | $241.45 | $0.87 | 83.47s | 79.9 |
| Claude Fable 5 | 83.8% | $552.67 | $7.70 | 132.16s | 79.8 |
| GPT-5.6 Terra | 78.4% | $421.15 | $2.17 | 141.16s | 73.9 |
| Claude Sonnet 5 | 74.6% | $288.18 | $1.54 | 199.71s | 70.6 |
| GPT-5.5 | 83.1% | $2,059.19 | $4.35 | 72.62s | 61.8 |
| GLM-5.1 | 58.7% | $277.14 | $0.90 | 70.79s | 52.2 |

Grok 4.5 的 Terminal-Bench 提交报告了 `-9.0%` hack 调整，因此注册表对其可靠性施加惩罚。Gemini 3 Pro 有可比的 Terminal-Bench 结果，但缺少匹配的当前价格行。Kimi K3、Qwen3.7 Max、MiniMax-M3 和 DeepSeek V4 Pro 有值得关注的综合数据，但缺少完全可比的当前 Terminal-Bench 条目，因此只作为本地 bake-off 候选，不作为已评分赢家。

证据来源包括 SWE-bench、Terminal-Bench、Aider Polyglot、LiveCodeBench、Artificial Analysis、官方能力文档和各提供商价格。可以直接检查[机器可读模型注册表](plugins/goldilocks/skills/goldilocks/assets/model-registry.json)以及[包含来源链接和局限性的完整筛查报告](docs/model-routing-survey-2026-07-18.md)。

### 一起改进这份种子

如果公开或本地证据与当前划分冲突，欢迎[提交 Issue](https://github.com/blackstone2333/goldilocks/issues)。有价值的报告最好包含：准确模型/版本/提供商、任务画像、Agent harness 与工具、推理等级、样本量、通过率、token 或金额成本、真实耗时、重试次数、审核投入和集成缺陷。同仓库可复现的实际结果，比再提供一个综合智力总分更有价值。

设计细节见 [v0.2 能力与触发引擎](docs/v0.2-capability-trigger-engine.md)。

## 本地验证

不调用模型的验证：

```bash
python3 tests/test_v02_contract.py
python3 tests/test_three_bears_contract.py
python3 benchmarks/three_bears/run.py --selftest
```

低成本在线冒烟测试：

```bash
python3 benchmarks/three_bears/run.py \
  --task baby-docs \
  --arms goldilocks,superpowers \
  --model gpt-5.6-terra \
  --reasoning low \
  --runs 1 \
  --workers 2
```

完整矩阵的复现方式见 [Three Bears](benchmarks/three_bears/README.md)。

## 当前阶段与方向

Goldilocks 现已更新至 `v0.2.4`。现有证据表明，它能够更好地替代 Superpowers，但并非在所有可能的工作流程中都具有绝对优势。公开的运行认证仍是 v0.2.2 的结果，连续性和并行模型路由还需要积累真实项目证据。详见[更新记录](CHANGELOG.zh-CN.md)，欢迎提出[意见和建议](https://github.com/blackstone2333/goldilocks/issues)。

接下来的迭代重点：

- 在不削弱质量门的前提下，降低 Mama/Papa 任务中的测试与验证开销；
- 扩展到更大的真实仓库和更多编程语言；
- 增加重复次数，再考虑更广泛的性能声明；
- 在长期项目和跨 Agent 交接中验证连续性协议；
- 用实际耗时、每次成功交付成本和集成缺陷衡量并行路由；
- 保持 Superpowers 入口兼容，同时确保 Direct 路径始终足够直接。

## 许可证与理念来源

Goldilocks 使用 MIT 许可证，由 Charles Roc 与贡献者共同开发。它是独立实现，理念受到 Superpowers、Grill 的关键决策提问方式以及 Ponytail 的复用/原生优先思想影响；这些项目并不为 Goldilocks 背书。详见[第三方说明](plugins/goldilocks/THIRD_PARTY_NOTICES.md)。
