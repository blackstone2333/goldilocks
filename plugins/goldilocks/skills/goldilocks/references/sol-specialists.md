# Sol Specialists (0.5.1 host contract)

Require explicit user authorization. It is a visible Codex task/thread at Sol/high—not
a hidden native subagent, external worker,
`goldilocks_sol_reviewer`, or Project Hub member. Root Sol keeps authority and
integration.

## Lifecycle

1. Fix mode, contract, and root/origin. Run
   `python3 ../../../scripts/sol_specialist_registry.py reserve`; each root permits two
   active/reserved specialists.
2. Call host `list_projects`, then host `create_thread` in the same local/worktree
   project at `gpt-5.6-sol` with high reasoning. Use `lead__<semantic>_sol`, title it
   `Goldilocks · Sol 专员 · <semantic>`, then `attach` its actual ID. Never generic-spawn.
3. Follow with host read/list/send. Require a concise result, changed files, evidence,
   and blockers returned to origin.
4. After delivered origin return and terminal host status, record `complete`, `fail`,
   or `cancel`. Before start, `fail` records launch failure and `cancel` drops an unused
   reservation without claiming return. Never expire reservations by time or idleness.
   `status` shows capacity; `receipt` reads the
   persistent receipt.

## Modes and limits

- `execution` owns one bounded chain and may delegate ready, non-conflicting
  Terra/Spark/Luna work, integrate it, and verify acceptance.
- `audit` may independently audit the root project or primary task. It is read-only,
  delegates nothing, and never repairs; an execution target is optional.
- Neither mode may create another Sol specialist, expand authority, or hide a Sol
  fallback. If visible threads are unavailable, record failure and use an ordinary
  verified route.

Contracts state mode, paths/tools, non-goals, interfaces, acceptance/audit question,
and return format. Names and reservations do not prove starts.
`goldilocks_sol_reviewer` remains only the native requested-read-only reviewer. This
preview adds no Project Hub, cross-project event bus, automatic synchronization, or
autonomous follow-up.
