# 安装 Goldilocks

对 Codex CLI 和 Desktop，Goldilocks 默认以原生 Plugin 安装。portable Agent Skills 用于其他兼容宿主，或作为临时 Bootstrap 来源。

## 推荐：在 Codex 中以原生 Plugin 安装稳定版 v0.5.0

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.5.0
codex plugin add goldilocks@goldilocks-local
```

该命令锁定稳定版 Git ref。插件 manifest 已是 `0.5.0`，但本地插件缓存可能仍较旧，`~/.codex/agents` 也可能只保留旧的 Terra/Sol 模板。

仅在首次安装、升级或安装修复时调用独立的 `$goldilocks-bootstrap` Skill；它绝不进入普通任务路由。在仓库 checkout 根目录中，它的脚本是：

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --plan --json
```

这条命令只读。检查 JSON 结果中的 `approval_required`。如果它为 `true`，Agent 展示计划后只向用户确认一次；获得同意后运行：

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --apply --yes --json
```

如果 `approval_required` 为 `false`，直接运行下面的命令。无论哪种情况，随后都验证：

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --apply --json
```

随后验证：

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --check --json
```

Bootstrap 会自动识别 Codex 及其原生插件，只会安全升级字节完全匹配的已知旧模板，补齐 Spark/Luna/Terra/Sol 伴随 Agent 模板；遇到不同的用户文件会拒绝覆盖。它的授权记录是宿主级全局复用，直到能力或模板哈希变化才失效，不是项目级记录。在已安装 source 中，脚本为 `goldilocks-bootstrap/scripts/bootstrap.py`，不要猜测缓存路径。仅在自动识别失败的故障排查中使用 `--native-plugin-dir`。若 Codex 最初只安装了 Skill，Bootstrap 可以补装原生插件和全部四个伴随 Agent。检查成功后，安装 Agent 按 handoff 清理 Codex 的重复 portable entry 并新建任务。其他宿主保持 portable，未支持能力标记为 skipped。

## 选择安装方式

- **任务路由器：** `goldilocks` 提供 Just-Necessary 动态流程判断及其内部工作流引擎。
- **安装助手：** `goldilocks-bootstrap` 与它一起安装，但只在首次安装、升级或安装修复时调用。

主 `goldilocks` 根路由不会在普通工作中加载 Bootstrap。同时也不建议并行启用 Goldilocks 与 Superpowers，两套重叠的工作流规则可能发生冲突。

## Portable Skills fallback

开源的 [`skills` CLI](https://github.com/vercel-labs/skills) 支持 Claude Code、Cursor、OpenCode、GitHub Copilot、Gemini CLI 等兼容宿主。在 Codex 上，仅当原生 Plugin 尚不可用或需要临时 Bootstrap 来源时使用它。

交互式安装：

```bash
npx skills add blackstone2333/goldilocks --skill goldilocks goldilocks-bootstrap
```

全局安装两个 Goldilocks Skill：

```bash
npx skills add blackstone2333/goldilocks \
  --skill goldilocks goldilocks-bootstrap \
  --global \
  --agent <agent> \
  --yes
```

常用平台 ID：

| 平台 | `<agent>` |
|---|---|
| Codex（仅 fallback） | `codex` |
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

纯 Skill 安装不会在后台检查更新，因此启用过程保持离线、跨平台，也不会持续增加模型或网络开销。需要主动获知更新时，请定期执行更新命令或订阅 GitHub Releases。Codex CLI 和 Desktop 用户在 Bootstrap handoff 完成后应回到原生 Plugin。

出于安全考虑，Skills 安装器不会自行执行任意 postinstall 代码。“自动” Bootstrap 指安装 Agent 仅在上述安装场景调用 `$goldilocks-bootstrap`，并完成它的计划、授权、应用、检查和 handoff；`npx` 本身不会执行它。在 portable 或其他宿主上，Bootstrap 只报告它能够证明支持的能力，其余能力明确标为 `skipped`，不会伪装成统一的原生插件配置。

## Codex 原生 Plugin 说明

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.5.0
codex plugin add goldilocks@goldilocks-local
```

这是 Codex CLI/Desktop 的默认路径。安装后新建一个 Codex 任务，让新的 Skill 上下文生效。

### 伴随 Agent 与可见名称

升级时调用 `$goldilocks-bootstrap`，按其计划、授权分支、应用、检查和 handoff 执行，再新建任务。原生子 Agent 的名称规范为 `<tier>__<semantic>_<model>`，例如 `fast__focused_checks_spark` 或 `standard__draft_contract_terra`。如果名称缺少路由层级前缀，说明该任务的 Goldilocks Hook 或 Skill 没有加载；先检查已安装 source 并新建任务，再把它当作路由结果。

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

最终角色结构为 Lead/Sol、作为主负责人的 Standard/Terra Medium、确定性编程叶子的 Fast/Spark XHigh，以及负责对时延不敏感的成本优先通用或文档工作的 Economy/Luna Max。Spark 不负责文档正文或连续性，Goldilocks 也不为 Spark 预留额度。默认 `project` 能力档位会隔离无关的全局插件、App、MCP、Skill 和 Hook，同时保留项目规则及运行所需的认证/供应商信息；只有完整合同明确需要已安装的用户能力时才使用 `inherit`。

Bootstrap 会把 Hook setup 带入安装或升级后的第一个新任务。请选择其一：

- **A — 持久信任 Goldilocks（推荐）：** 启动审核出现时核对 Goldilocks 来源，选择“信任全部并继续”或等效的持久选项。Hook 定义变化时再次审核。
- **B — 仅本次绕过全部已启用 Hook：** 下一次任务以 `codex --dangerously-bypass-hook-trust` 启动。它影响所有已启用 Hook，不只 Goldilocks，只对该次启动有效，且不会设为永久信任。
- **C — 暂不信任：** 拒绝审核。文字 Skill 仍可使用，但依赖 Hook 的自动化不会运行。

文件系统/完全访问权限和 Hook 信任是两套边界，应分别选择。Bootstrap 绝不会写入 `hooks.state` 或 trusted hash、不改 alias 或配置，也不把 bypass 说成永久设置；最终点击由 Codex 记录。只有启动审核未出现或需要事后复核时，才使用 `/hooks`。恢复 Hook 被禁用时，连续性账本仍是唯一事实源；路由 Hook 未获信任或平台只安装了跨平台 Skill 时，模型路由只保留指导作用，无法强制执行。

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
