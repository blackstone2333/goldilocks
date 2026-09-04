# Install Goldilocks

For Codex CLI and Desktop, Goldilocks is installed as a native Plugin by default. Portable Agent Skills are for other compatible hosts or a temporary Bootstrap source.

## Recommended stable release: install v0.6.0 as a native Codex Plugin

```bash
codex plugin marketplace add blackstone2333/goldilocks@v0.6.0
codex plugin add goldilocks@goldilocks-local
```

The exact Git ref selects the stable `0.6.0` release. A local plugin cache can still contain an older build and `~/.codex/agents` can still contain earlier companion templates, so upgrades should run Bootstrap once and then start a new task.

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

The [skills.sh listing](https://skills.sh/blackstone2333/goldilocks/goldilocks) follows the repository's default branch as its stable channel. Install only one channel. The unpinned commands below follow stable `main`; historical tags remain available for reproduction. For an exact portable `v0.6.0` pin, install both Skills from their tagged paths:

```bash
npx skills add https://github.com/blackstone2333/goldilocks/tree/v0.6.0/plugins/goldilocks/skills/goldilocks --skill goldilocks
npx skills add https://github.com/blackstone2333/goldilocks/tree/v0.6.0/plugins/goldilocks/skills/goldilocks-bootstrap --skill goldilocks-bootstrap
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
codex plugin marketplace add blackstone2333/goldilocks@v0.6.0
codex plugin add goldilocks@goldilocks-local
```

This is the default Codex CLI/Desktop path. Start a new Codex task after installation so the new Skill context is loaded.

### Companion agents and visible names

For an upgrade, invoke `$goldilocks-bootstrap` and follow its plan, approval branch, apply, check, and handoff, then start a new task. Native child-agent names follow `<tier>__<semantic>_<model>`—for example `fast__focused_checks_spark` or `standard__draft_contract_terra`. The parent must supply that form before spawn. Some native Codex paths expose only `SubagentStart`; names must therefore be supplied before spawn and cannot be repaired after launch.

### Manual updates

Updates are manual. Review the changelog, select and verify the desired Git release tag,
then reinstall the plugin or Skills at that tag and run Bootstrap plan/apply/check as a
one-time upgrade. Ordinary tasks do not perform update work.

### Codex continuity recovery

Routing and continuity use the Skill and the event-triggered ACTIVE ledger. Approved Bootstrap setup may append the four missing official `[agents.*]` registrations to user `config.toml`; Goldilocks does not install or override a global `compact_prompt`. During an explicit clean install, Bootstrap may remove a top-level prompt only when it exactly matches a recognized Goldilocks legacy prompt. Custom prompts and `experimental_compact_prompt_file` remain untouched. Only work that actually loads Goldilocks emits its compact receipt; clear routine Direct work stays silent. Usage stays on-demand.

The final role structure is Lead/Sol, Standard/Terra Medium as the primary owner, Fast/Spark XHigh as the deterministic coding leaf, and Economy/Luna Max for latency-tolerant cost-first general or document work. Spark does not own document prose or continuity, and Goldilocks does not reserve Spark capacity. Its default `project` capability profile isolates unrelated global plugins, Apps, MCP, and Skills while retaining repository rules and the credentials/provider metadata needed to run. Use `inherit` only when a complete contract explicitly requires an installed user capability.

Skills remain available normally, and a verified matching ACTIVE ledger is the sole Goldilocks execution-state source of truth. Codex retains its native compaction behavior.

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
