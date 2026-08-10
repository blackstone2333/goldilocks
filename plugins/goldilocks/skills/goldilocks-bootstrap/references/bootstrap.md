# Portable Bootstrap

Run Bootstrap only after a user asks to install or upgrade this Skill. First run
`scripts/bootstrap.py --plan --json`; it is read-only. Show the plan, ask once, then
run `--apply --yes --json` only after explicit approval. Use `--check --json` to verify.

For Codex CLI and Desktop, the native Goldilocks plugin is preferred and portable Skills
are fallback only. Bootstrap installs the four byte-verified native templates and naming
contract without touching `config.toml`. A detected enabled Goldilocks plugin gives
`experience=full` and reuses its Hooks, usage, and update facilities; `/hooks` remains
user review required and Bootstrap never invents a trusted hash. A portable-only Codex
plan is `experience=partial`: its initial plan visibly includes the locked v0.5.0
marketplace and plugin actions, which run only after the first `--yes`. Failure leaves
the portable Skill and installed agents intact as partial; Bootstrap never self-removes.

For a full Codex pack, `hook_trust_handoff` is `host-review-required` and the installing
agent asks once which option to use:

- `persistent_goldilocks` (recommended): in Codex's startup hook-review UI, choose
  **Trust all and continue** for the current Goldilocks hooks definition. It persists
  until that definition changes.
- `bypass_once_all_hooks`: launch exactly `codex --dangerously-bypass-hook-trust` next.
  Its scope is all enabled hooks and it lasts one invocation only; it is not persistent
  trust.
- `skip`: make no Hook trust change.

`/hooks` is the fallback. Bootstrap never writes `hooks.state` or a trusted hash, starts
no nested UI, and never runs the bypass command, changes aliases, or edits configuration;
the host remains the final authority. Non-Codex or missing-hooks plans skip this handoff.

After native plugin and four-agent `--check` succeed, Bootstrap emits a handoff for the
installing agent to remove Codex's duplicate portable entry and start a new task from
the plugin source. Non-Codex hosts prefer portable Skills with unsupported capabilities
skipped.
The global approval record contains only host identity, target, capability and template
hashes—never prompts, secrets, or project data—and is re-used until those change.
