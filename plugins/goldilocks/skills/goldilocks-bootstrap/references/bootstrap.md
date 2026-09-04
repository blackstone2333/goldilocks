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
write. Bootstrap never injects a `compact_prompt`. During explicit `--clean-install`, it
may remove only an exact known Goldilocks current or legacy top-level prompt; custom or
experimental prompt configuration is preserved and reported as unprocessed. The
compare-and-replace write preserves
comments, settings, permissions, and file mode. Use `--config-file` only when the host config is intentionally outside the normal
parent of the `agents` directory.

For a one-time clean install, add `--clean-install` to both the read-only plan and the
approved apply. The preview lists only exact Goldilocks portable mappings,
manifest-proven plugin caches, duplicate entries, and Goldilocks-named hook residue,
along with protected repository, backup, project-document, and `.goldilocks/ACTIVE.md`
boundaries. Unknown trust/UI state and unrelated host settings are reported as
unprocessed (unrecognized state) and are never edited.
When the enabled plugin comes from the local Goldilocks marketplace, clean install uses
that existing marketplace entry: it unregisters the entry, clears the identified old
Goldilocks cache/state, then adds the same marketplace entry again and independently
checks Codex's enabled-plugin registry. A published Git install instead remains locked
to stable `v0.6.1`; Bootstrap never assumes an unreleased remote tag exists.

Bootstrap does not rely on the earlier plan during apply: it re-reads role declarations
before any template write, completes safe registration before copying a template, reads
them once more immediately before staging config, and compares the original config
contents and file identity again before replacement. A concurrent config change aborts
rather than being overwritten.

`--plan`, `--apply`, and `--check` report `agents` (template state) separately from
`registrations` (live Codex role declarations). `experience=full` / `status=current`
requires a verified native plugin, all four exact templates, and all four exact role
registrations; template files alone are only a partial setup. A verified native pack
provides the Skill, companion agents, and usage reporter; Goldilocks ships no Hook
feature or source. Routing and continuity remain in the Skill and `ACTIVE.md`. A
portable-only Codex plan is
`experience=partial`: its initial
plan visibly includes the stable v0.6.1 marketplace and plugin actions, which run
only after the first `--yes`. Failure leaves
the portable Skill and installed agents intact as partial; Bootstrap never self-removes.
Apply returns a newly read final state, not its old plan: a registration-only repair is
reported as `status=installed`, and a plugin-install failure still reports the template
and role state that did land.

During ordinary/default Bootstrap, no Hook state is written. Only an explicit
`--clean-install` may atomically remove exact Goldilocks legacy
`[hooks.state."goldilocks@…:hooks/…"]` tables; unknown or other-plugin state is retained
and reported as unprocessed. Bootstrap has no Hook trust handoff, review choices, or
bypass command. Its approved role registration is limited to the four Goldilocks
`[agents.*]` declarations described above.

After native plugin and four-agent `--check` succeed, Bootstrap emits a handoff for the
installing agent to remove Codex's duplicate portable entry and start a new task from
the plugin source. Non-Codex hosts prefer portable Skills with unsupported capabilities
skipped.
The global approval record contains only host identity, target, capability and template
hashes—never prompts, secrets, or project data—and is re-used until those change.

## Lifecycle boundary

Bootstrap performs only the approved install, upgrade, or repair transaction and then
exits. It has no update checker, recurring watcher, automatic usage mode, or other
runtime/background behavior. Usage reporting, when available, belongs to the installed
Skill and is invoked explicitly by that Skill; it is not configured by Bootstrap.
