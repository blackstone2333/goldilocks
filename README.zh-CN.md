<p align="center">
  <img src="plugins/goldilocks/assets/logo.png" width="176" alt="Goldilocks 的金色热粥图标">
</p>

<h1 align="center">Goldilocks</h1>

<p align="center"><strong>流程不多不少，质量刚刚好。</strong></p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.2-D4A72C" alt="版本 0.2.2">
  <img src="https://img.shields.io/badge/Three_Bears-27%2F27_passed-2ea44f" alt="Three Bears：Goldilocks 27/27 通过">
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

## 证据：Goldilocks vs Superpowers

Goldilocks 对外只主张一个经过验证的窄结论：在已测试的工作流范围内，它是一个比 Superpowers 更可靠、更高效的**替代方案**。下面两轮验证回答不同问题，不把设计评分和真实运行成本混成一个总分。

### 测试一：指令层压力测试

最初的设计测试包含 8 个隔离场景。当时 Goldilocks 还叫 `just-necessary`，因此这轮证明的是 Goldilocks 的架构来源，不是 `v0.2.2` 的真实运行性能。Goldilocks 设计平均得分 **98.9/100，Superpowers 为 79.2/100**；8 个场景全部领先，规则文本少 **86.2%**。

<p align="center">
  <img src="benchmarks/assets/instruction-stress-head-to-head.svg" width="960" alt="指令层压力测试：Goldilocks 前身在 8 个场景中全部领先 Superpowers，规则文本少 86.2%">
</p>

### 测试二：真实 Agent 工作流认证

当前 `v0.2.2` 使用 GPT-5.6 Terra / low 测试了 Baby、Mama、Papa 三档共 9 个任务；每个任务运行 3 个全新隔离项目，每套工作流 27 次尝试。完整探索实验共有 135 个有效 turn；公开的替代结论只使用其中 **54 个 Goldilocks/Superpowers 正面对照 turn**。

<p align="center">
  <img src="benchmarks/assets/agentic-certification-head-to-head.svg" width="960" alt="真实 Agent 工作流认证：Goldilocks 成功交付 27/27，Superpowers 为 8/27；按每次成功交付计算，Goldilocks 所有成本维度均更低">
</p>

Goldilocks **27/27** 成功交付，测得安全率 100%；Superpowers 成功 **8/27**，安全率 88.9%。Superpowers 有 19 次在修改源码前停止，因此只看原始总成本会错误奖励“没有交付”。

在双方都成功的 8 个完全相同样本里，Goldilocks 少用 30.6% 总 token、7.7% 时间、28.6% 工具调用和 66.7% Skill 活动；非缓存输入高 9.7%，这是同成功样本中唯一没有领先的效率指标。把全部尝试（包括失败）计入并除以成功交付数后，Goldilocks 少用 61.2% 总 token、70.5% 非缓存输入、60.4% 时间、55.4% 工具调用和 89.8% Skill 活动。

详细数据见[两轮正面对照报告](benchmarks/GOLDILOCKS-VS-SUPERPOWERS.zh-CN.md)、[完整运行认证](benchmarks/three_bears/results/2026-07-18-terra-low-full-certification.md)、[测试方法](benchmarks/three_bears/README.md)、[正面对照数据](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/head-to-head.json)和[完整逐格审计数据](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/results.json)。

## 安装

先把本仓库添加为 Codex marketplace，再安装插件：

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

安装后新建一个 Codex 任务，让新的 Skill 上下文生效。

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

Goldilocks 仍然是 `v0.2.2`。现有证据支持它在已测试范围内是更好的 Superpowers 替代方案，但不主张普遍优于所有可能的工作流，也不需要急着发布 `1.0`。

接下来的迭代重点：

- 在不削弱质量门的前提下，降低 Mama/Papa 任务中的测试与验证开销；
- 扩展到更大的真实仓库和更多编程语言；
- 增加重复次数，再考虑更广泛的性能声明；
- 保持 Superpowers 入口兼容，同时确保 Direct 路径始终足够直接。

## 许可证与理念来源

Goldilocks 使用 MIT 许可证，由 Charles Roc 与贡献者共同开发。它是独立实现，理念受到 Superpowers、Grill 的关键决策提问方式以及 Ponytail 的复用/原生优先思想影响；这些项目并不为 Goldilocks 背书。详见[第三方说明](plugins/goldilocks/THIRD_PARTY_NOTICES.md)。
