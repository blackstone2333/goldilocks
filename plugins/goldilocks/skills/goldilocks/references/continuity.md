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
│   └── YYYY-MM-DD-<topic>.md
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

Use [project-map.md](../assets/project-map.md), [work-packet.md](../assets/work-packet.md), and [debug-note.md](../assets/debug-note.md) as section menus, not forms that must be filled completely. Delete irrelevant headings.

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

## Preserve ideas without expanding scope

Keep required work in the current packet. Put valuable but unnecessary ideas in the project's existing backlog or `docs/ideas.md`, with the value, revisit trigger, and dependency in a few lines. Do not pre-design or scaffold deferred work.

## Build a debug memory selectively

Before diagnosing a recurring-looking problem, search `docs/debug/` by error text, module, dependency, environment, and symptom. Revalidate any old explanation or workaround against current code and versions.

After a fix, add a focused regression test when practical. Create or update a debug note only when the root cause was non-obvious, the failure is likely to recur, an environment or integration trap is reusable, failed approaches would otherwise be repeated, or security/data integrity was involved.

Do not create a debug note for obvious typos, routine dependency drift, transient noise, or a failure already explained by a clear regression test and commit. A useful note records symptom, reproduction, root cause, fix, verification commands, failed attempts, related regression test or commit, prevention, and current status. Link rather than paste large logs. Never store credentials, tokens, private user data, or production secrets.

Keep `CHANGELOG.md` separate: it records user-visible release changes, not internal debugging history. Follow the repository's existing changelog format and update it only when the task includes a release-worthy external change.

## Completion check

Before handoff or completion, verify that durable records are still accurate, links resolve, completed work is marked, deferred ideas are separated from acceptance, and no secret or raw-log dump was added. Documentation is evidence of continuity, not a substitute for tests or runtime verification.
