# Task Lifecycle

Use this reference for non-simple executable work, mid-flight steering, persistence, or durable project evidence. A clear simple Direct request aligns its outcome inline, then acts without loading this file or creating workflow records.

## Ordered lifecycle

The invariant is:

`new task: align outcome → choose records → plan and route → execute and preserve continuity → accept, update, hand off, and archive`

During execution, an inserted message takes a separate, lighter path: make one semantic impact judgment, answer or absorb it and return when it is non-material, and only then steer the affected work when it is material.

Routing never precedes alignment. `Direct` is an orchestration decision after alignment, not permission to assume an unresolved outcome. Alignment is complete without asking when the request plus inspected facts already determine the end state, constraints, authority, and acceptance.

| Stage | Capability / reference | Required result | Record interaction |
|---|---|---|---|
| 1. Establish the entry and restore only when needed | Root rules; [continuity.md](continuity.md) only for a real recovery boundary | For a new task, retain enough current conversation to align its outcome. During execution, retain the active objective and return point while making one semantic impact judgment about an inserted message | Use current conversation first. Do not discover or read `ACTIVE.md` merely because it exists. On a verified recovery, read only the matching active frontier. An explicitly deferred adjacent idea goes to Ideas; a material applied steer is persisted only when it must survive a boundary. |
| 2. Align requirements | [align.md](align.md), plus the task-matching domain or brainstorming skill when available | A settled end-state contract: observable result, scope/non-goals, constraints, authority, and acceptance | For non-simple project work, create or update the work-unit Spec after alignment. Update `PROJECT.md` only for durable project structure/boundary changes. |
| 3. Determine project records | [continuity.md](continuity.md) | Choose no workflow record, one compact work packet, or split Spec/Plan/Handoff based on actual persistence, ownership, and risk | Reuse project conventions. Do not create empty files or a hierarchy just because this stage exists. |
| 4. Plan and route | Build for an executable plan; [kernel.md](kernel.md), [orchestrate.md](orchestrate.md), and model routing only when delegation may pay | Coherent work units, dependencies, one owner per mutable surface, acceptance method, then Direct/Fast/Standard/mixed | Non-simple project work gets explicit Plan semantics; a medium work packet may contain both Spec and Plan. Create `ACTIVE.md` only when a real continuity boundary is expected or reached. |
| 5. Execute and maintain continuity | Build/TDD, diagnose, evolve, domain skill, and [continuity.md](continuity.md) as facts require | Implement the aligned outcome, process steering, keep one current owner/frontier, and run minimum-sufficient checks | Read the Plan and only relevant Debug notes. Update Plan at coherent milestones; write ACTIVE, Debug, or Ideas only on their events below. |
| 6. Accept, update, and hand off | Prove, continuity, and final-output hygiene when applicable | Compare fresh evidence with Spec acceptance, integrate once, report verified result, and leave the project truthful | Mark Spec/Plan status and update `PROJECT.md`, Debug, or verified user-visible `CHANGELOG` only when each record's event trigger fired; create Handoff only for a real receiver; transfer durable outcomes and remove/close ACTIVE. |

## New-task entry and in-flight steering

A new task normally enters through outcome alignment. It is not treated as a continuation merely because an older objective exists in the conversation; an unfinished objective remains visible until it is completed, explicitly superseded, or stopped.

An inserted message while work is underway does **not** pass through a fixed keyword taxonomy. Make one semantic judgment: does it materially affect the current objective, scope, order, authority, safety, acceptance, or the return point?

- If no, answer the simple question or absorb the useful information, then return to the exact prior execution position. Do not create a Plan, change routing, or write continuity state for the interruption.
- If yes, interpret its actual intent and apply only the needed steering: pause, stop, change, strengthen, or re-plan the affected work. Update the affected Spec before Plan when the outcome contract changes; update only Plan when method or order changes. Preserve the return point when it would otherwise be lost.
- If the impact or intended steering would materially change work but remains ambiguous, ask one focused question with a recommended interpretation. Do not invent a rigid label just to proceed.

Later text must never silently erase an uncompleted objective. Explicit language is strong evidence, but semantic intent and the settled contract—not a required vocabulary list—determine whether work pauses, stops, changes, or continues.

## Record event contract

The trigger is a real state event, not a keyword. When an event applies, update the project's existing record; when it does not, do not create or read a file for ceremony. Link evidence instead of copying conversations or logs.

| Record | Unit and purpose | Read trigger | Write trigger | Completion behavior |
|---|---|---|---|---|
| `docs/PROJECT.md` or existing equivalent | Project-level current map and stable boundaries | New project orientation, structural planning, or a task touching architecture/boundaries | Project creation or verified change to structure, entry points, ownership, dependency direction, or trust boundary | Keep current; replace stale facts rather than append history |
| Work-unit Spec | What one version, feature, fix, or other acceptance unit must become | Before planning, scope-changing work, and final acceptance | After alignment for non-simple project work; update when requested behavior, scope, constraints, authority, or acceptance changes | Mark accepted/superseded; retain as the outcome contract |
| Work-unit Plan | How that same unit will be delivered: steps, dependencies, owners, checks | Before execution or real resume of non-simple work | After Spec is settled and before multi-step execution; update when method, order, ownership, status, or verification changes | Mark complete/blocked/superseded; never treat a completed Plan as an active instruction |
| `.goldilocks/ACTIVE.md` | Ephemeral pointer to the one live execution frontier | Only an explicit continuation startup/resume, compaction, wait-return, delegation, or handoff recovery with `status: active` and exact objective, repository, and host `session_id` match; inspect frontmatter/size first and read the body only after it matches | When work must survive compaction, a session boundary, a real pause/resume, long wait, delegation/handoff, or a material steer whose return point would otherwise be lost | Transfer durable facts to Spec/Plan/Debug/Handoff, then remove or mark inactive; never accumulate history |
| Work-unit Handoff | Package for a named next owner/session | The named receiver starts or reconciles the transfer | Only when ownership, session, environment, or execution boundary is actually transferred | Receiver reconciles evidence; retain with the work unit or fold into a compact packet |
| `docs/debug/` or existing equivalent | Reusable failure memory | Before diagnosing a genuinely recurring/similar symptom | After evidence establishes a non-obvious or reusable cause/fix, recurring integration trap, important failed approach, or security/data issue | Mark fixed/obsolete and link regression evidence; no raw-log archive |
| `docs/ideas.md` or existing backlog | Valuable idea intentionally outside current acceptance | Planning/review when that deferred scope may now be relevant | When a useful adjacent idea is explicitly deferred; do not put accepted current requirements here | Keep a terse value, revisit trigger, and dependency; remove/promote when scheduled |
| `CHANGELOG.md` or existing equivalent | Verified user-visible change history | Release/version questions and release preparation | Only after a user-visible change has fresh verification, in the repository's existing format | Append/prepare the appropriate release entry; exclude internal routing and unverified claims |

Spec and Plan are scoped to an acceptance-bearing work unit, not every message and not one immortal project file. A project or release may have a parent Spec/Plan; executable child units may have their own records. Reuse the same records across conversations while the unit remains the same. For medium single-owner work, one `docs/work/<topic>.md` may contain `Spec`, `Plan`, and `Status` sections; add a Handoff section only when a real transfer occurs. Split files only when size, stages, owners, or risk make the packet unclear: semantic completeness is mandatory; physical separation is not.

## Plan change rules

- Implementation method, tool, or order changes while the agreed outcome remains stable: update Plan with the reason and proceed.
- Requested outcome, scope, constraint, authority, or acceptance changes: update Spec first, then re-plan the affected work.
- Multiple owners: one integration owner writes the authoritative Plan; other owners return evidence and proposed changes rather than overwriting it.
- Completed work: close the Plan and preserve concise evidence; a later independent outcome gets a new work unit rather than extending the old Plan forever.

## Lightweight boundary

Do not write after every command, read every record on every prompt, create a Plan only to choose Direct, or make documentation substitute for tests. One coherent milestone update beats a command diary. The lifecycle should leave enough evidence to resume and audit the project while staying off the simple-task hot path.
