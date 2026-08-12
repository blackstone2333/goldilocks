# Portable Bootstrap

Run Bootstrap only after a user asks to install or upgrade this Skill. First run
`scripts/bootstrap.py --plan --json`; it is read-only. Show the plan, ask once, then
run `--apply --yes --json` only after explicit approval. Use `--check --json` to verify.

For Codex CLI and Desktop, the native Goldilocks plugin is preferred and portable Skills
are fallback only. Bootstrap installs the four byte-verified native templates and, after
approval, appends the four official Codex role declarations to `config.toml`:
`goldilocks_spark_worker`, `goldilocks_luna_economy`, `goldilocks_terra_engineer`, and
`goldilocks_sol_reviewer`. It preserves all existing settings and comments, appends only
missing `[agents.<name>]` tables, and never replaces a declaration whose `description`
or `config_file` differs. Such a conflict stops the operation with no template or config
write. Use `--config-file` only when the host config is intentionally outside the normal
parent of the `agents` directory.

Bootstrap does not rely on the earlier plan during apply: it re-reads role declarations
before any template write, completes safe registration before copying a template, reads
them once more immediately before staging config, and compares the original config
contents and file identity again before replacement. A concurrent config change aborts
rather than being overwritten.

`--plan`, `--apply`, and `--check` report `agents` (template state) separately from
`registrations` (live Codex role declarations). `experience=full` / `status=current`
requires a verified native plugin, all four exact templates, and all four exact role
registrations; template files alone are only a partial setup. A full pack reuses Hooks,
usage, and update facilities; `/hooks` remains user review required and Bootstrap never
invents a trusted hash. A portable-only Codex plan is `experience=partial`: its initial
plan visibly includes the locked v0.5.2
marketplace and plugin actions, which run only after the first `--yes`. Failure leaves
the portable Skill and installed agents intact as partial; Bootstrap never self-removes.
Apply returns a newly read final state, not its old plan: a registration-only repair is
reported as `status=installed`, and a plugin-install failure still reports the template
and role state that did land.

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
no nested UI, and never runs the bypass command or changes aliases. Its approved role
registration is limited to the four Goldilocks `[agents.*]` declarations described above;
Hook trust remains entirely with the host. Non-Codex or missing-hooks plans skip this
handoff.

After native plugin and four-agent `--check` succeed, Bootstrap emits a handoff for the
installing agent to remove Codex's duplicate portable entry and start a new task from
the plugin source. Non-Codex hosts prefer portable Skills with unsupported capabilities
skipped.
The global approval record contains only host identity, target, capability and template
hashes—never prompts, secrets, or project data—and is re-used until those change.

## Visible Usage preference

Bootstrap asks once through its `usage_visibility` JSON field: `on-demand` is the default
and recommended choice; `automatic` is an explicit opt-in. Select either with
`--usage-visibility on-demand|automatic` on plan/apply/check. A successful apply records
the selected mode in Bootstrap state; `GOLDILOCKS_USAGE_VISIBILITY` overrides it for a test
or host policy. The portable default is on-demand on every platform, so unreadable or absent
state never enables visible Usage. Automatic mode injects exactly one fail-silent pre-final
Usage instruction; it does not change host-side baseline recording or explicit on-demand
reads.

When a mode is supplied to `--check`, Bootstrap verifies that the actually active mode
matches it; the argument alone is never evidence of an active opt-in. A valid environment
override is authoritative, followed by the recorded preference, then the on-demand default.

The opt-in decision is diagnostic rather than a forecast. One frozen same-Direct ablation
observed +208,975 raw tokens, +50.258s, and +44.487% normalized cost; both diagnostic task
cells failed acceptance. It is evidence for keeping the default off, not a promised saving.
