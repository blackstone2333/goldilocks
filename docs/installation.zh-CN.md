# 安装 Goldilocks

对 Codex CLI 和 Desktop，Goldilocks 默认以原生 Plugin 安装。portable Agent Skills 用于其他兼容宿主，或作为临时 Bootstrap 来源。

## 推荐：在 Codex 中以原生 Plugin 安装稳定版 v0.5.1

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.5.1
codex plugin add goldilocks@goldilocks-local
```

该命令锁定稳定版 Git ref。插件 manifest 已是 `0.5.1`，但本地插件缓存可能仍较旧，`~/.codex/agents` 也可能只保留旧的 Terra/Sol 模板。

仅在首次安装、升级或安装修复时调用独立的 `$goldilocks-bootstrap` Skill；它绝不进入普通任务路由。在仓库 checkout 根目录中，它的脚本是：

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --plan --json
```

这条命令只读。检查 JSON 结果中的 `approval_required`。如果它为 `true`，Agent 展示计划后只向用户确认一次；获得同意后运行：

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --apply --yes --json
```

如果 `approval_required` 为 `false`，直接运行不带 `--yes` 的 apply：

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

[skills.sh 页面](https://skills.sh/blackstone2333/goldilocks/goldilocks)默认跟随仓库主分支作为稳定通道，目前没有单独的预发布通道。只安装一个通道。下方不锁版本的命令跟随稳定 `main`；历史 Alpha Tag 仅用于复现。若要精确锁定 portable `v0.5.1`，分别从 Tag 路径安装两个 Skill：

```bash
npx skills add https://github.com/blackstone2333/goldilocks/tree/v0.5.1/plugins/goldilocks/skills/goldilocks --skill goldilocks
npx skills add https://github.com/blackstone2333/goldilocks/tree/v0.5.1/plugins/goldilocks/skills/goldilocks-bootstrap --skill goldilocks-bootstrap
```

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
codex plugin marketplace add blackstone2333/goldilocks@v0.5.1
codex plugin add goldilocks@goldilocks-local
```

这是 Codex CLI/Desktop 的默认路径。安装后新建一个 Codex 任务，让新的 Skill 上下文生效。

### 伴随 Agent 与可见名称

升级时调用 `$goldilocks-bootstrap`，按其计划、授权分支、应用、检查和 handoff 执行，再新建任务。原生子 Agent 的名称规范为 `<tier>__<semantic>_<model>`，例如 `fast__focused_checks_spark` 或 `standard__draft_contract_terra`；父模型必须在 spawn 前就提供这个名称。有些 Codex 原生路径只暴露启动后的 `SubagentStart`，Hook 此时已经无法改名；因此缺少前缀代表可见命名合同没有被遵守，不能仅凭这一点断定 Plugin 没有加载。

### 安静的更新感知

原生插件会在 `SessionStart` 时检查 GitHub 上的 Goldilocks 公共清单，但 24 小时内最多请求一次。检查使用短超时、GitHub ETag 和插件数据目录中的 SQLite 状态。已经是最新版、重复启动、响应格式错误、超时或离线时完全无输出；发现更高的语义版本时，每个版本只提醒一次，并显示当前版本、最新版本和更新命令。

检查器不会下载或执行远端代码，也不会自行安装更新；当前任务始终继续使用已经加载的版本。Goldilocks marketplace 固定到不可变的 release Tag，因此只运行 `marketplace upgrade` 不能升级到新版本。阅读 changelog 并明确批准更新后，按提醒中基于真实安全来源生成的顺序执行：先用 `git ls-remote` 验证新 Tag，再移除旧 marketplace，以同一已验证 Git 来源和 `--ref v<latest>` 重新添加，重新安装 Plugin，运行 Bootstrap plan/apply/check，最后新建任务。来源不安全、属于本地开发或无法核实时，不会给出更新命令。如需完全关闭联网检查，可在 Codex 环境中设置 `GOLDILOCKS_UPDATE_CHECK=0`。

### Codex 连续性恢复

原生插件为 `SessionStart`、`PostCompact` 和 `UserPromptSubmit` 附带恢复 Hook。没有连续性债务时 `SessionStart` 保持静默；`UserPromptSubmit` 注入常量级路由回执合同，只有用户明确索要或 Bootstrap 已启用 `automatic` 时才加入绑定当前轮次的 Usage 指令；`PostCompact` 恢复本轮选中的合同。插件还为 `PreToolUse`、`SubagentStart` 和 `SubagentStop` 附带路由守卫：宿主暴露 PreToolUse 时，它会阻止未分级派发、锁定受支持角色、禁止 Fast 继续创建子智能体，并且只允许明确的 Lead 交接继承完整历史；只暴露 SubagentStart 的原生路径只能在启动后审计，无法事后改名。并发路由观察写入本地 SQLite；宿主关联不唯一时只记录歧义，不会误停子任务。子任务停止仍只是观察，Lead 重跑组合验收并记录 `verified_pass` 或 `verified_fail` 后才算闭环；验收证据只保存哈希，不保留原文。得到批准后，Bootstrap 只会向用户 `config.toml` 追加缺失的四个官方 `[agents.*]` 注册，保留其他设置和注释，发现冲突则终止。Direct 始终增加一条短回执；Usage 默认按需，只有用户选择自动模式后才逐轮读取。

最终角色结构为 Lead/Sol、作为主负责人的 Standard/Terra Medium、确定性编程叶子的 Fast/Spark XHigh，以及负责对时延不敏感的成本优先通用或文档工作的 Economy/Luna Max。Spark 不负责文档正文或连续性，Goldilocks 也不为 Spark 预留额度。默认 `project` 能力档位会隔离无关的全局插件、App、MCP、Skill 和 Hook，同时保留项目规则及运行所需的认证/供应商信息；只有完整合同明确需要已安装的用户能力时才使用 `inherit`。

Bootstrap 会把 Hook setup 带入安装或升级后的第一个新任务。请选择其一：

- **A — 持久信任 Goldilocks（推荐）：** 启动审核出现时核对 Goldilocks 来源，选择“信任全部并继续”或等效的持久选项。Hook 定义变化时再次审核。
- **B — 仅本次绕过全部已启用 Hook：** 下一次任务以 `codex --dangerously-bypass-hook-trust` 启动。它影响所有已启用 Hook，不只 Goldilocks，只对该次启动有效，且不会设为永久信任。
- **C — 暂不信任：** 拒绝审核。文字 Skill 仍可使用，但依赖 Hook 的自动化不会运行。

文件系统/完全访问权限和 Hook 信任是两套边界，应分别选择。Bootstrap 绝不会写入 `hooks.state` 或 trusted hash，不修改 alias、Hook 信任或并发配置，也不把 bypass 说成永久设置；唯一获批的用户配置写入，是上面限定的四个角色注册。最终信任点击由 Codex 记录。只有启动审核未出现或需要事后复核时，才使用 `/hooks`。恢复 Hook 被禁用时，连续性账本仍是唯一事实源；路由 Hook 未获信任或平台只安装了跨平台 Skill 时，模型路由只保留指导作用，无法强制执行。

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
