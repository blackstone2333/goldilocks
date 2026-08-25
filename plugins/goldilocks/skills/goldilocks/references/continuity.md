# Continuity

Preserve the minimum durable context another competent human or agent needs to continue correctly. Use the project's existing documentation convention first. Do not create a parallel Goldilocks hierarchy when the repository already has suitable specs, ADRs, plans, issue notes, or changelogs.

## Choose the persistence depth

| Work shape | Durable record |
|---|---|
| Direct | No workflow continuity record by default. Create or update normal project documentation when it is the deliverable or necessary for correctness. |
| Guarded | One compact work packet only when work spans stages or sessions, carries meaningful decisions, or needs handoff. |
| Critical, Orchestrated, or cross-session handoff | Separate current spec, plan, and handoff when one packet would obscure ownership, risk, or status. |
| New project or architecture-level change | Create or update a project structure contract before implementation. |

Direct work may autonomously create or update documentation when documentation is the requested artifact, an established project convention requires it, or omission would leave behavior, operation, or ownership misleading. It should not create speculative spec/plan/handoff files, empty folders, placeholders, or paperwork that merely repeats the conversation.

When no local convention exists, use:

```text
docs/
├── PROJECT.md
├── work/
│   ├── YYYY-MM-DD-<topic>.md
│   └── execution-patterns.md
├── decisions/
│   └── ADR-0001-<decision>.md
├── debug/
│   ├── README.md
│   └── YYYY-MM-DD-<problem>.md
└── ideas.md

CHANGELOG.md
```

Large work may replace the single packet with:

```text
docs/work/YYYY-MM-DD-<topic>/
├── spec.md
├── plan.md
└── handoff.md
```

Use [project-map.md](../assets/project-map.md), [work-packet.md](../assets/work-packet.md), [debug-note.md](../assets/debug-note.md), and [execution-pattern.md](../assets/execution-pattern.md) as section menus, not forms that must be filled completely. Delete irrelevant headings.

## Keep the project legible

Before coding a new project or costly structural change, record the target directory tree, module responsibilities, allowed dependency direction, entry points and data flow, test layout, extension points, and forbidden coupling. Explicitly prevent generic `utils` or `helpers` dumping grounds. Prefer an established framework layout when it already communicates these facts.

Update `docs/PROJECT.md` only when the durable structure or boundaries change. It describes the current system, not the history of every edit. Use an ADR only for a costly-to-reverse decision whose rationale would otherwise be lost.

## Keep work state current

A work packet contains only the end state, scope and non-goals, decisions and assumptions, relevant code map, ordered work, acceptance evidence, current status, and deferred ideas needed for continuation. Mark units pending, active, blocked, or complete; update the packet at coherent milestones, not after every command.

For handoff, remove stale speculation and name:

- what is complete and what remains;
- changed files or commits and important interfaces;
- commands run and their fresh results;
- unresolved risks, blockers, and required authority;
- the next smallest coherent action.

Never treat a stale plan as truth. The receiver checks it against the current code and repository state before execution.

## Survive steering and compaction

When work is likely to cross a context boundary, receives mid-flight steering, or must resume after waiting or delegation, keep one live execution frontier. Reuse a predictable existing state file when it carries the same contract; otherwise copy [active-task.md](../assets/active-task.md) to `.goldilocks/ACTIVE.md`. This is a short-lived pointer and ledger, not a second documentation hierarchy. Link to the real spec or plan instead of duplicating it, keep it under 100 lines and about 4 KB, and remove it after durable outcomes are transferred at completion. Keep `.goldilocks/ACTIVE.md` out of version control; add it to the project's ignore mechanism when safe, and warn instead of rewriting an established ignore policy without authority.

Record the current host `session_id` in the frontier frontmatter. Recovery prefers a frontier in the current cwd or its repository ancestors. If work continues from a sibling worktree, it may inspect only Git's registered worktree entries and select the single `status: active` frontier whose `session_id` exactly matches the host session. Never recursively scan arbitrary children, choose an unrelated active frontier, or guess when more than one match exists.

Keep the original objective stable. Classify each later user message as `ADD / REPLACE / CANCEL / QUESTION`; record its effect and mark it `pending, applied, or superseded`. A recent message does not replace the objective unless the user explicitly changes or cancels it. After handling a steer, mark it applied before doing more work.

The frontier names only the current objective, boundaries, current work, remaining work, one **Exact next action**, repository and verification state, blockers or authority, a **Do not repeat** boundary, and the terminal condition. Move completed detail and reusable evidence to the existing work/debug record or archive; do not keep growing the live prompt. Update it after a steer is consumed, at coherent milestones, before long waits or delegation, and before handoff or known compaction—not after every command.

Treat a second user-confirmed recurrence, a reverted fix, or a third disproven hypothesis as a hard continuity boundary. Before another patch, create or refresh the frontier and the project's existing debug or validation record. Preserve failed approaches and their evidence once, name the exact next distinguishing test, and do not force the next agent to reconstruct them from chat.

On startup, resume, or compaction recovery, read the frontier first; inspect `git status`, relevant diffs, commits, and files; then reconcile it. The repository state wins when they disagree. Continue from the Exact next action and do not reopen completed work unless its evidence is stale or contradicted. Codex users may optionally use [codex-compact-prompt.md](../assets/codex-compact-prompt.md); bundled hooks are reminders only, never the source of truth.

## Preserve ideas without expanding scope

Keep required work in the current packet. Put valuable but unnecessary ideas in the project's existing backlog or `docs/ideas.md`, with the value, revisit trigger, and dependency in a few lines. Do not pre-design or scaffold deferred work.

## Build a debug memory selectively

Before diagnosing a recurring-looking problem, search `docs/debug/` by error text, module, dependency, environment, and symptom. Revalidate any old explanation or workaround against current code and versions.

After a fix, add a focused regression test when practical. Create or update a debug note only when the root cause was non-obvious, the failure is likely to recur, an environment or integration trap is reusable, failed approaches would otherwise be repeated, or security/data integrity was involved.

Do not create a debug note for obvious typos, routine dependency drift, transient noise, or a failure already explained by a clear regression test and commit. A useful note records symptom, reproduction, root cause, fix, verification commands, failed attempts, related regression test or commit, prevention, and current status. Link rather than paste large logs. Never store credentials, tokens, private user data, or production secrets.

Keep `CHANGELOG.md` separate: it records user-visible release changes, not internal debugging history. Keep unverified fixes out of the changelog; after fresh verification, record only confirmed user-visible release changes in the repository's existing format. Internal routing history remains in the plugin audit database.

## Reuse execution routes selectively

Before repeating orchestration analysis for a familiar task shape, search the project's execution patterns. Reuse a route only after checking its preconditions and invalidators against current code, risk, authority, tools, models, billing channels, and acceptance. After combined verification, record only routes likely to recur; read [execution-memory.md](execution-memory.md). A worker stop is not proof that a route succeeded, and internal routing history never belongs in `CHANGELOG.md`.

## Completion check

Before handoff or completion, verify that durable records are still accurate, links resolve, completed work is marked, deferred ideas are separated from acceptance, and no secret or raw-log dump was added. Documentation is evidence of continuity, not a substitute for tests or runtime verification.
