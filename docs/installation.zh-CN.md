# 安装 Goldilocks

Goldilocks 既可以作为跨平台 Agent Skills 安装，也可以作为 Codex 或 Claude Code 原生插件安装。

## 选择安装方式

- **核心路由器：** 只安装 `goldilocks`，获得 Just-Necessary 动态流程判断，体积和上下文开销最小，可独立工作。
- **完整套件：** 安装全部 14 个 Skill，获得完整的 Superpowers 兼容入口，包括头脑风暴、计划、TDD、调试、worktree、委派、审查、验证、分支收尾和 Skill 编写。

不要单独安装 `brainstorming` 等兼容入口。这些薄入口会调用核心 `goldilocks` Skill 内的共享引擎。同时也不建议并行启用 Goldilocks 与 Superpowers，两套重叠的工作流规则可能发生冲突。

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
  --skill '*' \
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

## Codex 原生插件

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

安装后新建一个 Codex 任务，让新的 Skill 上下文生效。Goldilocks 发布新版本后，可通过 Codex 的插件管理器更新 marketplace 和插件。

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
