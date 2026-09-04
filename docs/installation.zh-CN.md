# 安装 Goldilocks

对 Codex CLI 和 Desktop，Goldilocks 默认以原生 Plugin 安装。portable Agent Skills 用于其他兼容宿主，或作为临时 Bootstrap 来源。

## 推荐正式版：在 Codex 中以原生 Plugin 安装 v0.6.0

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.6.0
codex plugin add goldilocks@goldilocks-local
```

该命令锁定 `0.6.0` 正式版 Git ref。本地插件缓存仍可能保留旧构建，`~/.codex/agents` 也可能仍是较早的伴随 Agent 模板，因此升级后应运行一次 Bootstrap，再新建任务。

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

[skills.sh 页面](https://skills.sh/blackstone2333/goldilocks/goldilocks)默认跟随仓库主分支作为稳定通道。只安装一个通道。下方不锁版本的命令跟随稳定 `main`；历史 Tag 可用于复现。若要精确锁定 portable `v0.6.0`，分别从 Tag 路径安装两个 Skill：

```bash
npx skills add https://github.com/blackstone2333/goldilocks/tree/v0.6.0/plugins/goldilocks/skills/goldilocks --skill goldilocks
npx skills add https://github.com/blackstone2333/goldilocks/tree/v0.6.0/plugins/goldilocks/skills/goldilocks-bootstrap --skill goldilocks-bootstrap
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
codex plugin marketplace add blackstone2333/goldilocks@v0.6.0
codex plugin add goldilocks@goldilocks-local
```

这是 Codex CLI/Desktop 的默认路径。安装后新建一个 Codex 任务，让新的 Skill 上下文生效。

### 伴随 Agent 与可见名称

升级时调用 `$goldilocks-bootstrap`，按其计划、授权分支、应用、检查和 handoff 执行，再新建任务。原生子 Agent 的名称规范为 `<tier>__<semantic>_<model>`，例如 `fast__focused_checks_spark` 或 `standard__draft_contract_terra`；父模型必须在 spawn 前就提供这个名称。有些 Codex 原生路径只暴露启动后的 `SubagentStart`；名称必须在启动前提供，启动后无法补救。

### 手动更新

更新需要手动执行。查看 changelog，选择并验证目标 Git release tag，然后按该 tag
重新安装 Plugin 或 Skills，并运行 Bootstrap plan/apply/check 完成一次性升级；普通任务
不会执行更新操作。

### Codex 连续性恢复

路由和连续性由 Skill 与事件触发的 ACTIVE 账本承载。得到批准后，Bootstrap 可以向用户 `config.toml` 追加缺失的四个官方 `[agents.*]` 注册；Goldilocks 不再安装或覆盖全局 `compact_prompt`。只有显式执行清洁安装，且顶层 prompt 与已知 Goldilocks 遗留内容精确匹配时，Bootstrap 才会将其删除；用户自定义 prompt 和 `experimental_compact_prompt_file` 保持不变。只有实际加载 Goldilocks 的任务才显示短回执，清晰例行 Direct 保持安静；Usage 始终按需。

最终角色结构为 Lead/Sol、作为主负责人的 Standard/Terra Medium、确定性编程叶子的 Fast/Spark XHigh，以及负责对时延不敏感的成本优先通用或文档工作的 Economy/Luna Max。Spark 不负责文档正文或连续性，Goldilocks 也不为 Spark 预留额度。默认 `project` 能力档位会隔离无关的全局插件、App、MCP 和 Skill，同时保留项目规则及运行所需的认证/供应商信息；只有完整合同明确需要已安装的用户能力时才使用 `inherit`。

Skill 始终可正常使用；经验证匹配的 ACTIVE 账本是 Goldilocks 唯一的执行状态事实源，Codex 继续使用自身原生压缩行为。

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
