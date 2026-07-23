# Orchestrate

Orchestration allocates decision work, implementation work, and review to the cheapest capable layer. Run a routing pass after planning, or a constant-time check before clear Direct work. It is not a ceremony and not a task-size label. The Lead owns the outcome; Standard owns a bounded domain; Fast executes contracts whose material decisions have already been made.

## Run the make-or-delegate check

Before an expensive model starts implementation, make one quick comparison:

`delegation gain = Lead work avoided + parallel time saved + quota-channel benefit - briefing - review - integration - retry risk`

Search a verified execution pattern first when the repository contains one. Reuse its route after a short invalidation check; read [execution-memory.md](execution-memory.md) only when a task shape is recurring or the route will likely be reused.

- Keep Direct when the Lead can implement and verify before a worker can be briefed and reviewed.
- Delegate directly to Fast when the objective, scope, interfaces, acceptance, and prohibitions form a complete execution contract.
- Delegate a bounded domain to Standard when domain planning or local judgment remains. Standard may then convert its design into Fast contracts.
- Keep Critical judgment, cross-domain interfaces, authority, and final integration with Lead.

This check is constant-time for clear work. Do not write a plan merely to decide that a two-minute task is Direct.

## Choose only the useful depth

Use the shallowest organization that shortens the critical path or reduces quota-weighted expensive work:

- Lead → Direct for tiny or inseparable work.
- Lead → Fast for a ready execution contract.
- Lead → Standard for one bounded expert task.
- Lead → Standard → Fast when a domain contains several contractible units.
- Multiple Standard advisers may investigate a hard decision independently, but one named owner decides and integrates. Do not create a committee of overlapping writers.

Fast is a leaf executor and does not delegate. Standard may delegate Fast only inside its assigned domain and may not expand scope, change shared interfaces, cross an authority boundary, or claim final integration. Each additional management layer must earn itself; remove it when transfer and review cost exceed the saving.

The Lead should not implement merely because it can produce the highest-quality code. Lead implementation needs a reason: faster Direct delivery, inseparable Critical core, shared-interface ownership, emergency unblocking, or worker failure after one bounded repair.

## Split into execution contracts

Classify after decomposition, not before it. A large cross-file unit can be Fast when its remaining discretion is low; a ten-line security decision can remain Lead.

Every delegated contract states objective, non-goals, allowed files or domain, stable interfaces, dependencies, acceptance checks, expected evidence, and forbidden external or destructive actions. Give task-local repository paths and decisions instead of copying the conversation. If a competent worker still has to infer product intent or architecture, the contract is not Fast-ready.

Prefer one worker implementing a coherent unit and its focused checks. Do not split implementation and tests when that duplicates the same context. Workers escalate ambiguity instead of guessing. After one failed repair or requirement mismatch, reconsider the contract or capability; after a second, stop the worker loop and upgrade or keep the work local.

## Parallelize the ready graph

Define dependencies, shared interfaces, ownership, integration order, and combined acceptance before dispatch. Only ready units run. Keep overlapping edits to one fragile surface serial and give every shared interface one owner.

Do not impose a fixed worker count. Useful concurrency is bounded by independent ready units, host capacity, isolated workspaces, integration risk, and reviewer throughput. Fill available capacity when it shortens the critical path; use waves when the host limit or dependency graph requires them.

Detect existing isolation before creating worktrees. Inspect branch, dirty state, untracked files, repository instructions, and conventions. Create a worktree when it protects user changes or separates concurrent writers; skip it when the host already isolates work or setup costs more than it protects. Never move, overwrite, strand, or delete user work to simplify orchestration.

## Route capability and quota

Read [model-routing.md](model-routing.md) when multiple models, billing channels, or capability levels are available. Apply the quality and authority gates first. Then prefer the route that lowers quota-weighted expensive usage and wall-clock time while keeping total raw tokens inside a reasonable envelope.

Fast describes low remaining discretion, not small original scope. Standard describes bounded residual judgment, not medium file count. Lead describes authority and integration responsibility, not a requirement to type every line.

## Integrate upward

Fast returns the changed files and focused evidence to its Standard or Lead owner. Standard reviews actual diffs, resolves domain-local issues, runs domain checks, and returns one coherent domain result. Lead reviews integrated diffs and shared boundaries, resolves conflicts, and reruns the combined acceptance gate.

Agent completion messages are not evidence. If useful adjacent ideas appear, preserve them without following them; read [evolve.md](evolve.md) only when durable capture is warranted. When sessions or layers need durable coordination, read [continuity.md](continuity.md) and keep one authoritative execution frontier.
