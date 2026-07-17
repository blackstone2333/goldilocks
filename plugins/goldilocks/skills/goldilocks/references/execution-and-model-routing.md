# Execution and Model Routing

Work inline unless orchestration has positive net value.

## Net-benefit gate

Estimate:

`net benefit = wall-clock saving + quality gain - setup - context transfer - review - integration risk`

If the result is not clearly positive, keep the work with the current agent. User-requested delegation is still honored within safety and tool limits.

## Capability roles

Route by capability and task shape, never brand or version:

| Role | Suitable work |
|---|---|
| **Lead** | Architecture, high ambiguity, Critical risk, cross-workstream integration, final judgment |
| **Standard** | Ordinary cross-file implementation with known patterns and bounded decisions |
| **Fast** | Mechanical, explicit, easily checked work with narrow scope and stable interfaces |

Use a host-declared capability class when the environment provides one. If capability is unknown, treat the worker as **Standard** and keep Lead judgment with the current coordinating agent.

Fast must never own Critical work, architecture, authority decisions, cross-interface design, or final integration judgment. Standard may implement bounded cross-file work with established patterns. Lead owns ambiguity, Critical decisions, and final cross-workstream integration.

A lower-capability worker receives a smaller scope, a clearer brief, deterministic acceptance checks, and stronger review. Fast non-trivial output is reviewed by Standard or Lead before integration; Critical output receives Lead judgment plus an independent review. The worker does not receive a lower quality target. A capable Lead may use fewer process steps, but the same evidence gates apply.

## Split coherent workstreams

Delegate or parallelize only when workstreams:

- are independent or have a stable declared interface;
- can be reviewed as meaningful units;
- do not edit the same fragile surface concurrently;
- save elapsed time after integration cost.

Do not create one agent per tiny plan step. Keep setup with the deliverable that needs it. The Lead owns shared decisions, interface changes, integration, conflict resolution, and final verification.

Every delegated brief should contain:

- objective and explicit non-goals;
- allowed scope, files, and interfaces;
- project patterns and reuse constraints;
- acceptance checks and expected evidence;
- forbidden external, destructive, or out-of-scope actions.

When review finds a defect, send the bounded finding back for fix and re-review before integration. After three repeated failures or requirement mismatches, stop the loop and escalate to Lead reassessment instead of adding more agents or patches.

## Worktrees and isolation

Prefer an existing suitable or harness-owned workspace; do not duplicate isolation the host already provides. Before creating a worktree, inspect dirty or uncommitted state and never move, overwrite, or silently strand user changes. Verify the chosen local worktree parent is ignored when it lives inside a repository.

Create a new worktree when it materially protects a baseline, separates concurrent branches, prevents overlapping state, or contains a risky/long-running change. Record the integration owner and cleanup owner; do not delete a worktree or branch merely because implementation finished. Skip it for clear local work when setup and merge cost exceed the isolation benefit.

Before parallel execution, define integration order and shared ownership. Afterward, inspect actual diffs and run integration checks; subagent success messages are not completion evidence.
