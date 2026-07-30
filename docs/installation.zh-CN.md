# 安装 Goldilocks

Goldilocks 既可以作为跨平台 Agent Skills 安装，也可以作为 Codex 或 Claude Code 原生插件安装。

## 选择安装方式

- **核心路由器：** 只安装 `goldilocks`，获得 Just-Necessary 动态流程判断，体积和上下文开销最小，可独立工作。
- **唯一 Skill：** 安装 `goldilocks`；它的内部引擎继续提供头脑风暴、计划、TDD、调试、worktree、委派、审查、验证、分支收尾和 Skill 编写。

现在不需要安装任何额外工作流 Skill。同时也不建议并行启用 Goldilocks 与 Superpowers，两套重叠的工作流规则可能发生冲突。

## 跨平台 Skills 安装

开源的 [`skills` CLI](https://github.com/vercel-labs/skills) 支持 Codex、Claude Code、Cursor、OpenCode、GitHub Copilot、Gemini CLI 等大量 Agent。

交互式安装：

```bash
npx skills add blackstone2333/goldilocks
```

只全局安装核心路由器：

```bash
npx skills add blackstone2333/goldilocks \
  --skill goldilocks \
  --global \
  --agent <agent> \
  --yes
```

全局安装完整套件：

```bash
npx skills add blackstone2333/goldilocks \
  --skill goldilocks \
  --global \
  --agent <agent> \
  --yes
```

常用平台 ID：

| 平台 | `<agent>` |
|---|---|
| Codex | `codex` |
| Claude Code | `claude-code` |
| Cursor | `cursor` |
| OpenCode | `opencode` |
| GitHub Copilot | `github-copilot` |
| Gemini CLI | `gemini-cli` |

去掉 `--global` 即安装到当前项目。只查看仓库中可安装的 Skill，不执行安装：

```bash
npx skills add blackstone2333/goldilocks --list
```

更新已安装的 Skill：

```bash
npx skills update --global --yes
```

纯 Skill 安装不会在后台检查更新，因此启用过程保持离线、跨平台，也不会持续增加模型或网络开销。需要主动获知更新时，请定期执行更新命令或订阅 GitHub Releases。

## Codex 原生插件

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

安装后新建一个 Codex 任务，让新的 Skill 上下文生效。

### 安静的更新感知

原生插件会在 `SessionStart` 时检查 GitHub 上的 Goldilocks 公共清单，但 24 小时内最多请求一次。检查使用短超时、GitHub ETag 和插件数据目录中的 SQLite 状态。已经是最新版、重复启动、响应格式错误、超时或离线时完全无输出；发现更高的语义版本时，每个版本只提醒一次，并显示当前版本、最新版本和更新命令。

检查器不会下载或执行远端代码，也不会自行安装更新。当前任务始终继续使用已经加载的版本；阅读 changelog 并确认更新后，再运行：

```bash
codex plugin marketplace upgrade goldilocks-local
codex plugin add goldilocks@goldilocks-local
```

更新后新建任务生效。如需完全关闭联网检查，可在 Codex 环境中设置 `GOLDILOCKS_UPDATE_CHECK=0`。

### Codex 连续性恢复

原生插件为 `SessionStart`、`PostCompact` 和 `UserPromptSubmit` 附带恢复 Hook。只有当前工作区存在 `.goldilocks/ACTIVE.md` 时才会输出提醒，否则完全静默。它还为 `PreToolUse`、`SubagentStart` 和 `SubagentStop` 附带路由守卫。守卫只在子智能体活动时运行：阻止未分级派发，要求 Fast 与 Standard 显式选择宿主支持的模型，禁止 Fast 继续创建子智能体，并且只允许明确的 Lead 交接继承完整历史。并发路由观察写入本地 SQLite；宿主关联不唯一时只记录歧义，不会误停子任务。子任务停止仍只是观察，Lead 重跑组合验收并记录 `verified_pass` 或 `verified_fail` 后才算闭环；验收证据只保存哈希，不保留原文。它不会修改用户级 `config.toml`，也不会给 Direct 任务增加流程。

当所选 Fast 模型可由 `codex exec` 使用、但原生子智能体通道没有提供时，打包的适配器会把 `luna` 交给通用 Fast 默认模型，把 `spark-coding` 交给独立计量的确定性编程专才；旧的 `general` 和 `coding` 名称继续兼容。默认 `project` 能力档位会隔离无关的全局插件、App、MCP、Skill 和 Hook，同时保留项目规则及运行所需的认证/供应商信息；只有完整合同明确需要已安装的用户能力时才使用 `inherit`。

Codex 会要求用户审核非托管插件 Hook；安装后可用 `/hooks` 查看并信任 Goldilocks 定义，插件更新导致 Hook 哈希变化时需要重新审核。恢复 Hook 被禁用时，连续性账本仍是唯一事实源；路由 Hook 未获信任或平台只安装了跨平台 Skill 时，模型路由只保留指导作用，无法强制执行。

如需额外加强压缩摘要，可从仓库复制 `plugins/goldilocks/skills/goldilocks/assets/codex-compact-prompt.md` 到稳定的本地路径，并在用户级 `~/.codex/config.toml` 中指向该副本：

```toml
experimental_compact_prompt_file = "/绝对路径/goldilocks-compact-prompt.md"
```

这个设置可选且全局生效。Codex 会把它视为内置压缩提示词的完整覆盖，而不是追加片段；Execution Frontier 不依赖它也能工作。

## Claude Code 原生插件

```bash
claude plugin marketplace add blackstone2333/goldilocks
claude plugin install goldilocks@goldilocks
```

也可以在 Claude Code 内使用交互命令：

```text
/plugin marketplace add blackstone2333/goldilocks
/plugin install goldilocks@goldilocks
```

如果当前会话没有显示新 Skill，重启 Claude Code。

## 其他 Agent

Cursor、OpenCode、GitHub Copilot、Gemini CLI 以及其他受支持平台，使用上面的跨平台安装命令并替换对应的 Agent ID 即可。CLI 会写入各平台原生的 Skill 目录，不需要手工复制。

如果某个平台尚未支持 Agent Skills，可以把 `plugins/goldilocks/skills/goldilocks` 复制到该平台的 Skill 目录来安装核心路由器；需要完整套件时，复制 `plugins/goldilocks/skills/` 下的全部目录。
