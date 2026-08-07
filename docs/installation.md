# Install Goldilocks

Goldilocks can be installed as portable Agent Skills or as a native Codex or Claude Code plugin.

## Install the v0.5.0 Alpha in Codex

The Alpha and stable plugin share one marketplace name, so choose one rather than installing both:

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.5.0-alpha.1
codex plugin add goldilocks@goldilocks-local
```

Start a new task and verify `v0.5.0-alpha.1` before testing. The exact Git ref keeps this install on the prerelease instead of the default stable branch.

## Choose an installation

- **Core router:** install only `goldilocks` for the Just-Necessary routing logic. It is self-contained and has the smallest footprint.
- **Single Skill:** install `goldilocks`; its internal engines retain brainstorming, planning, TDD, debugging, worktrees, delegation, review, verification, branch finishing, and Skill authoring.

There are no extra workflow Skills to install. Avoid enabling Goldilocks and Superpowers at the same time; overlapping workflow rules can conflict.

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
  --skill goldilocks \
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

Portable Skills do not run a background update check. This keeps activation offline, cross-platform, and free of recurring model or network overhead. Run the update command explicitly or watch GitHub releases when proactive notification is important.

## Codex native plugin

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

Start a new Codex task after installation so the new Skill context is loaded.

### Quiet update awareness

The native plugin checks the public Goldilocks manifest on GitHub at most once every 24 hours during `SessionStart`. It uses a short timeout, GitHub ETags, and a small state row in plugin-data SQLite. Current versions, repeated sessions, malformed responses, timeouts, and offline use produce no output. A newer semantic version produces one notice per release with the installed version, latest version, and update commands.

The checker never downloads or executes remote code and never installs an update. The active task remains on its installed version; review the changelog and approve the update before running:

```bash
codex plugin marketplace upgrade goldilocks-local
codex plugin add goldilocks@goldilocks-local
```

Start a new task after updating. Set `GOLDILOCKS_UPDATE_CHECK=0` in the Codex environment to disable the network check completely.

### Codex continuity recovery

The native plugin bundles recovery hooks for `SessionStart`, `PostCompact`, and `UserPromptSubmit`. They emit nothing unless the current workspace contains `.goldilocks/ACTIVE.md`. It also bundles a routing guard for `PreToolUse`, `SubagentStart`, and `SubagentStop`. The guard only runs around subagent activity: it blocks unclassified calls, requires an explicit host-supported model for Fast and Standard, prevents Fast from spawning, and permits full history only for an explicit Lead handoff. Concurrent route observations use a local SQLite database; ambiguous host correlation is recorded without stopping a child. A stop remains an observation until Lead reruns combined acceptance and records `verified_pass` or `verified_fail`; evidence text is hashed rather than retained. It does not edit user `config.toml` or add work to Direct tasks.

When the selected Fast model is available through `codex exec` but not through native subagents, the bundled adapter routes `luna` to the universal Fast default and `spark-coding` to the separately metered deterministic code specialist. Legacy `general` and `coding` names remain compatible. Its default `project` capability profile isolates unrelated global plugins, Apps, MCP, Skills, and Hooks while retaining repository rules and the credentials/provider metadata needed to run. Use `inherit` only when a complete contract explicitly requires an installed user capability.

Codex requires review before non-managed plugin hooks run. Use `/hooks` to inspect and trust the Goldilocks definition after installation, and review it again after an update changes the hook hash. The continuity ledger remains the source of truth if a recovery hook is disabled; routing becomes advisory rather than enforced when the routing hook is not trusted or the platform only installed portable Skills.

For an additional compaction layer, copy `plugins/goldilocks/skills/goldilocks/assets/codex-compact-prompt.md` from this repository to a stable local path and point user-level `~/.codex/config.toml` at that copy:

```toml
experimental_compact_prompt_file = "/absolute/path/to/goldilocks-compact-prompt.md"
```

This setting is optional and global. Codex treats it as a complete override of the built-in compaction prompt, not an additive fragment. The Execution Frontier works without it.

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
