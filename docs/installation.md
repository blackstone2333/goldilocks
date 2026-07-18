# Install Goldilocks

Goldilocks can be installed as portable Agent Skills or as a native Codex or Claude Code plugin.

## Choose an installation

- **Core router:** install only `goldilocks` for the Just-Necessary routing logic. It is self-contained and has the smallest footprint.
- **Complete suite:** install all 14 Skills for the full Superpowers-compatible surface: brainstorming, planning, TDD, debugging, worktrees, delegation, review, verification, branch finishing, and Skill authoring.

Do not install a compatibility entry such as `brainstorming` by itself. Those thin entries share engines bundled with the core `goldilocks` Skill. Also avoid enabling Goldilocks and Superpowers at the same time; overlapping workflow rules can conflict.

## Portable Skills installation

The open-source [`skills` CLI](https://github.com/vercel-labs/skills) supports Codex, Claude Code, Cursor, OpenCode, GitHub Copilot, Gemini CLI, and many other agents.

Interactive installation:

```bash
npx skills add blackstone2333/goldilocks
```

Install only the core router globally:

```bash
npx skills add blackstone2333/goldilocks \
  --skill goldilocks \
  --global \
  --agent <agent> \
  --yes
```

Install the complete suite globally:

```bash
npx skills add blackstone2333/goldilocks \
  --skill '*' \
  --global \
  --agent <agent> \
  --yes
```

Common agent IDs:

| Platform | `<agent>` |
|---|---|
| Codex | `codex` |
| Claude Code | `claude-code` |
| Cursor | `cursor` |
| OpenCode | `opencode` |
| GitHub Copilot | `github-copilot` |
| Gemini CLI | `gemini-cli` |

Omit `--global` to install into the current project. To see every detected Skill without installing anything:

```bash
npx skills add blackstone2333/goldilocks --list
```

Update installed Skills:

```bash
npx skills update --global --yes
```

## Codex native plugin

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

Start a new Codex task after installation so the new Skill context is loaded. Update the marketplace and plugin through Codex's plugin manager when a newer Goldilocks version is published.

## Claude Code native plugin

```bash
claude plugin marketplace add blackstone2333/goldilocks
claude plugin install goldilocks@goldilocks
```

The equivalent interactive commands inside Claude Code are:

```text
/plugin marketplace add blackstone2333/goldilocks
/plugin install goldilocks@goldilocks
```

Restart Claude Code after installation if the Skills do not appear in the current session.

## Other agents

For Cursor, OpenCode, GitHub Copilot, Gemini CLI, and other supported agents, use the portable installation above with the corresponding agent ID. The CLI writes to each platform's native Skill directory; no manual copying is required.

If a platform does not yet support Agent Skills, copy `plugins/goldilocks/skills/goldilocks` for the core router or every directory under `plugins/goldilocks/skills/` for the complete suite into that platform's Skill directory.
