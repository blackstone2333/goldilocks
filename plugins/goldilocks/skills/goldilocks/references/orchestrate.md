# Orchestrate

Work inline unless coordination has positive net value:

`benefit = wall-clock saving + quality gain - setup - context transfer - review - integration risk`

Honor explicit delegation or isolation requests, but never lower safety or evidence standards.

## Choose isolation

Detect whether the host already provides an isolated workspace. Do not create nested or duplicate isolation. Inspect the current branch, dirty state, untracked files, repository instructions, and existing worktree conventions before changing workspace state.

Create a worktree when it protects unrelated user changes, separates concurrent branches, contains risky or long-running work, or preserves a stable baseline. Prefer host-native worktree support; otherwise use the repository's established worktree parent and verify a project-local parent is ignored. Record integration and cleanup ownership. Never move, overwrite, strand, or delete user changes, branches, or worktrees merely because implementation ended.

Skip a worktree when the current workspace is already isolated or setup and merge cost exceed its protection value.

## Split coherent workstreams

Parallelize only workstreams that are independent or have stable declared interfaces, can be reviewed as meaningful units, and will not edit the same fragile surface. Define shared decisions, ownership, integration order, and combined acceptance first. Keep overlapping work serial.

Every delegated brief states objective, non-goals, allowed scope, relevant project patterns, interfaces, acceptance checks, expected evidence, and forbidden external or destructive actions. Give agents only task-local context; the Lead owns architecture, shared interfaces, conflicts, integration, and final judgment.

## Route by capability

Use host-declared capability when available:

- Lead: ambiguity, architecture, Critical risk, integration, final judgment.
- Standard: bounded cross-file implementation with known patterns.
- Fast: mechanical, explicit, narrow, deterministically checked work.
- Unknown: treat as Standard.

A lower-capability worker receives a smaller scope, clearer brief, stronger deterministic checks, and review—not a lower quality target. Fast never owns Critical work, authority, architecture, or final integration.

Use subagent-driven development only when a plan contains multiple coherent units whose independent implementation and review save time or context. Do not create one agent per microstep. Review actual diffs and evidence, return bounded defects for correction, then re-review. After three repeated failures or requirement mismatches, stop the loop and reassess with Lead capability.

Agent success messages are not completion evidence. Run integration checks on the combined result.
