# Build

Inspect before inventing, reuse before adding, and plan only to the depth that reduces execution uncertainty.

## Reuse ladder

Stop at the first rung that fully satisfies acceptance and safety:

1. Remove work that is not needed now.
2. Reuse an existing project helper, component, script, test utility, asset, API, or configuration.
3. Extend the established project pattern or extension point.
4. Use the language or framework standard library.
5. Use native browser, OS, database, cloud, or hardware capability.
6. Use a suitable already-installed library, component system, animation library, or asset source.
7. Write the minimum custom implementation.

Before adding a dependency, verify fit, maintenance, compatibility, licensing, bundle/runtime cost, and whether it removes more ownership than it creates. Do not turn a trivial change into a research project.

## Plan to useful depth

- Direct: no separate plan.
- Guarded: short ordered units naming touched flow and focused checks.
- Orchestrated: add ownership, stable interfaces, integration order, and combined acceptance.
- Critical: durable design/plan with authority, rollback, risk controls, and approval.

Keep each unit coherent and independently checkable. Fold setup, documentation, and configuration into the deliverable that needs them. Avoid implementation transcripts, artificial two-minute microsteps, and mandatory plan files. For handoff, long-running work, auditability, costly decisions, or new-project structure, read [continuity.md](continuity.md) and create only the durable record earned by the work.

When executing an existing plan, inspect it against current code first. Resolve genuine blockers, then execute coherent units continuously. Pause only for missing authority, material ambiguity, an unsafe plan, or an external dependency; do not ask “continue?” after every unit.

Before the Lead starts implementing a multi-unit plan, route each unit by independence, capability, model value, acceptance, and integration order through [orchestrate.md](orchestrate.md). The plan should expose parallel waves rather than silently assigning every unit to the main model.

## Test-first proportionally

For bugs and non-trivial behavior, define the smallest acceptance or regression check and observe it fail for the expected reason when practical and cheap. Implement only enough to pass, then refactor while keeping it green.

Fail-first is optional for prose-only edits, mechanical configuration, generated artifacts, exploratory prototypes, or cases where no meaningful pre-implementation signal exists. State why when skipping it. If implementation already exists, do not delete correct work merely to reenact TDD; add the missing regression and verify the behavior honestly.

Trace the touched flow end to end, preserve security and accessibility invariants, follow project conventions, and prefer the fewest files that keep responsibilities clear. Give a coherent unit at most one focused check when current evidence is absent; use [prove.md](prove.md) to reuse that result rather than rerun it at completion.

If a useful adjacent idea appears but is not required for current acceptance, do not follow it. Preserve it for final handoff; read [evolve.md](evolve.md) only when classification or durable capture is needed.
