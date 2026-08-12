# Install Goldilocks

For Codex CLI and Desktop, Goldilocks is installed as a native Plugin by default. Portable Agent Skills are for other compatible hosts or a temporary Bootstrap source.

## Recommended: install stable v0.5.2 as a native Codex Plugin

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.5.2
codex plugin add goldilocks@goldilocks-local
```

The exact Git ref selects the stable release. The plugin manifest is already `0.5.2`, but a local plugin cache can be older and `~/.codex/agents` can still contain only earlier Terra/Sol templates.

For a first install, upgrade, or installation repair only, invoke the independent `$goldilocks-bootstrap` Skill. It is never part of ordinary task routing. From a repository checkout root, its script is:

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --plan --json
```

This first command is read-only. Inspect `approval_required` in its JSON result. If it is `true`, the Agent shows the plan and asks the user once; after approval, it runs:

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --apply --yes --json
```

If `approval_required` is `false`, run the apply step directly without `--yes`:

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --apply --json
```

Then verify:

```bash
python3 plugins/goldilocks/skills/goldilocks-bootstrap/scripts/bootstrap.py --check --json
```

Bootstrap automatically detects Codex and its native plugin, safely upgrades only byte-exact known legacy templates, adds the missing Spark/Luna/Terra/Sol companion templates, and refuses to overwrite a different user file. Its approval is global to the host and is reused until the capability or template hashes change; it is not project-local. From an installed source, its script is `goldilocks-bootstrap/scripts/bootstrap.py`; do not guess a cache path. Use `--native-plugin-dir` only when troubleshooting an automatic-discovery failure. If Codex began with Skills only, Bootstrap can install the native plugin and all four companion agents. After a successful check, the installing Agent follows its handoff to remove Codex's duplicate portable entry and starts a new task. Other hosts remain portable and mark unsupported capabilities as skipped.

## Choose an installation

- **Task router:** `goldilocks` contains the Just-Necessary routing logic and its internal workflow engines.
- **Setup helper:** `goldilocks-bootstrap` is installed alongside it but is invoked only for first install, upgrade, or installation repair.

The main `goldilocks` root router does not load Bootstrap during ordinary work. Avoid enabling Goldilocks and Superpowers at the same time; overlapping workflow rules can conflict.

## Portable Skills fallback

The open-source [`skills` CLI](https://github.com/vercel-labs/skills) supports Claude Code, Cursor, OpenCode, GitHub Copilot, Gemini CLI, and other compatible hosts. On Codex, use it only when the native Plugin is not yet available or as a temporary Bootstrap source.

The [skills.sh listing](https://skills.sh/blackstone2333/goldilocks/goldilocks) follows the repository's default branch as its stable channel and does not expose a separate prerelease channel. Install only one channel. The unpinned commands below follow stable `main`; historical Alpha Tags remain available only for reproduction. For an exact portable `v0.5.2` pin, install both Skills from their tagged paths:

```bash
npx skills add https://github.com/blackstone2333/goldilocks/tree/v0.5.2/plugins/goldilocks/skills/goldilocks --skill goldilocks
npx skills add https://github.com/blackstone2333/goldilocks/tree/v0.5.2/plugins/goldilocks/skills/goldilocks-bootstrap --skill goldilocks-bootstrap
```

Interactive installation:

```bash
npx skills add blackstone2333/goldilocks --skill goldilocks goldilocks-bootstrap
```

Install both Goldilocks Skills globally:

```bash
npx skills add blackstone2333/goldilocks \
  --skill goldilocks goldilocks-bootstrap \
  --global \
  --agent <agent> \
  --yes
```

Common agent IDs:

| Platform | `<agent>` |
|---|---|
| Codex (fallback only) | `codex` |
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

Portable Skills do not run a background update check. This keeps activation offline, cross-platform, and free of recurring model or network overhead. Run the update command explicitly or watch GitHub releases when proactive notification is important. Codex CLI and Desktop users should return to the native Plugin after Bootstrap has completed its handoff.

The Skills installer intentionally does not execute arbitrary post-install code. “Automatic” Bootstrap means the installing Agent invokes `$goldilocks-bootstrap` only for the setup cases above and follows its plan, approval, apply, check, and handoff; `npx` does not run it by itself. On portable or other hosts, Bootstrap reports only capabilities it can prove supported and marks the rest as `skipped`; it does not present a uniform native-plugin setup.

## Codex native Plugin details

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.5.2
codex plugin add goldilocks@goldilocks-local
```

This is the default Codex CLI/Desktop path. Start a new Codex task after installation so the new Skill context is loaded.

### Companion agents and visible names

For an upgrade, invoke `$goldilocks-bootstrap` and follow its plan, approval branch, apply, check, and handoff, then start a new task. Native child-agent names follow `<tier>__<semantic>_<model>`—for example `fast__focused_checks_spark` or `standard__draft_contract_terra`. The parent must supply that form before spawn. Some native Codex paths expose only `SubagentStart`, which is too late for a Hook to rename the child; a missing prefix therefore means the visible naming contract was not followed, not by itself that the Plugin failed to load.

### Quiet update awareness

The native plugin checks the public Goldilocks manifest on GitHub at most once every 24 hours during `SessionStart`. It uses a short timeout, GitHub ETags, and a small state row in plugin-data SQLite. Current versions, repeated sessions, malformed responses, timeouts, and offline use produce no output. A newer semantic version produces one notice per release with the installed version, latest version, and update commands.

The checker never downloads or executes remote code and never installs an update. The active task remains on its installed version. Because a Goldilocks marketplace is pinned to an immutable release Tag, `marketplace upgrade` alone cannot move it to a later version. After reviewing the changelog and explicitly approving the update, follow the exact safe-source sequence shown by the notice: verify the new Tag with `git ls-remote`, remove the old marketplace, re-add the same validated Git source at `--ref v<latest>`, reinstall the plugin, run Bootstrap plan/apply/check, and start a new task. Unsafe, local, or unverifiable provenance produces no update command. Set `GOLDILOCKS_UPDATE_CHECK=0` in the Codex environment to disable the network check completely.

### Codex continuity recovery

The native plugin bundles recovery hooks for `SessionStart`, `PostCompact`, and `UserPromptSubmit`. `SessionStart` stays silent without continuity debt; `UserPromptSubmit` injects the constant-size route response contract and adds an exact-turn Usage instruction only for an explicit request or Bootstrap's `automatic` opt-in; `PostCompact` restores the selected contract. It also bundles a routing guard for `PreToolUse`, `SubagentStart`, and `SubagentStop`. Where the host exposes PreToolUse, the guard blocks unclassified calls, pins supported roles, prevents Fast from spawning, and permits full history only for an explicit Lead handoff. SubagentStart-only native paths are audited after launch and cannot be renamed retroactively. Concurrent route observations use a local SQLite database; ambiguous host correlation is recorded without stopping a child. A stop remains an observation until Lead reruns combined acceptance and records `verified_pass` or `verified_fail`; evidence text is hashed rather than retained. Approved Bootstrap setup may append only the four missing official `[agents.*]` registrations to user `config.toml`, preserving other settings/comments and aborting on conflicts. Direct always adds the compact visible receipt; Usage stays on-demand unless the user opted into automatic mode.

The final role structure is Lead/Sol, Standard/Terra Medium as the primary owner, Fast/Spark XHigh as the deterministic coding leaf, and Economy/Luna Max for latency-tolerant cost-first general or document work. Spark does not own document prose or continuity, and Goldilocks does not reserve Spark capacity. Its default `project` capability profile isolates unrelated global plugins, Apps, MCP, Skills, and Hooks while retaining repository rules and the credentials/provider metadata needed to run. Use `inherit` only when a complete contract explicitly requires an installed user capability.

Bootstrap carries Hook setup into the first new task after installation or upgrade. Choose one:

- **A — Persistently trust Goldilocks (recommended):** at the startup review, verify the Goldilocks source and choose “Trust all and continue” or its persistent equivalent. Review again when the Hook definition changes.
- **B — Bypass all enabled Hooks for one launch:** start the next task with `codex --dangerously-bypass-hook-trust`. This affects every enabled Hook, not only Goldilocks, lasts for that launch only, and does not set permanent trust.
- **C — Do not trust yet:** decline the review. The written Skill remains available, while Hook-dependent automation does not run.

Filesystem or full-access permission and Hook trust are separate boundaries, so choose them independently. Bootstrap never writes `hooks.state` or a trusted hash, changes no alias, Hook trust, or concurrency setting, and never represents bypass as permanent; its only approved user-config edit is the bounded four-role registration described above. Codex records the final trust click. Use `/hooks` only when the startup review did not appear or for later verification. The continuity ledger remains the source of truth if a recovery hook is disabled; routing becomes advisory rather than enforced when the routing hook is not trusted or the platform only installed portable Skills.

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
