---
name: goldilocks
description: Use when explicitly asked to apply Goldilocks, choose a project workflow, replace Superpowers, or decide how much brainstorming, planning, testing, isolation, delegation, review, and verification a task actually needs.
---

# Goldilocks

Use the minimum process that preserves the same high quality, safety, authorization, and evidence floor.

A capable worker may need fewer instructions. A simple task may need fewer stages. Neither gets weaker acceptance criteria.

## Route the current stage

Re-evaluate as facts change; do not assign one workflow depth to an entire project.

| Mode | Observable condition | Default shape |
|---|---|---|
| Direct | Clear, local, reversible, low-risk | Act inline; inspect output and run one relevant check |
| Guarded | Behavior change, bug, multi-file work, or limited ambiguity | State assumptions; use a short plan and focused evidence |
| Critical | Security, permissions, money, production, migration, data loss, public contract, or costly architecture | Resolve authority/design; add risk-specific tests and independent review |

Before an expensive model starts implementation, make a constant-time Direct-versus-delegate check. If a verified route for the same task shape still applies, reuse it after checking invalidators. Add orchestration only when delegation, hierarchy, isolation, or parallelism has positive net value after briefing, review, integration, retry risk, quota-channel cost, and raw-token growth.

After a Guarded or Critical plan exposes meaningful units, run the orchestration routing pass before the Lead starts implementing everything. A ready execution contract can go directly to Fast; a bounded domain can go to Standard, which may split it into Fast contracts. Lead owns direction and final quality rather than defaulting to high-cost implementation.

Direct: do not create workflow continuity documents by default. Creating or updating documentation is still appropriate when documentation is the deliverable, project conventions require it, or omission would make the change misleading. For Guarded work that genuinely spans stages, Critical or Orchestrated work, cross-session handoff, or new-project architecture, read [continuity.md](references/continuity.md) and persist only the minimum useful state.

If `.goldilocks/ACTIVE.md` exists, continuity recovery takes precedence over reconstructing the task from chat: read it, reconcile it with repository evidence, classify the current user message, and continue from its exact frontier. Create it only when continuity risk appears, such as likely compaction, a long-running multi-stage task, mid-flight steering, waiting, delegation, or handoff.

## Load only the needed engine

- Material product, design, architecture, scope, or authority decisions: read [align.md](references/align.md).
- Bugs, failures, unexpected behavior, or unclear causality: read [diagnose.md](references/diagnose.md).
- Reuse, planning, implementation, or test-first development: read [build.md](references/build.md).
- Worktrees, parallel work, subagents, or capability routing: read [orchestrate.md](references/orchestrate.md).
- Review, runtime evidence, completion claims, or branch integration: read [prove.md](references/prove.md).
- Mid-flight ideas, skill authoring, or workflow improvement: read [evolve.md](references/evolve.md).

Load multiple engines only when the stage genuinely crosses their boundaries. Explicit compatibility skills route directly to the same engines.

## Minimum complete loop

1. Define the requested end state, constraints, non-goals, and acceptance evidence.
2. Inspect the real project flow, structure, documentation, and existing solutions before inventing.
3. Choose the smallest safe execution and organizational shape.
4. Implement the smallest coherent change.
5. Obtain fresh evidence for every completion claim.
6. Separate useful follow-up ideas from delivered scope.

Ask only when the answer changes the end state, authority, external effect, safety boundary, or a costly-to-reverse choice. Investigate project facts yourself. Honor explicit scope and tool constraints; when a necessary check is forbidden or unavailable, report the exact unverified claim.

Never optimize away acceptance, regression evidence, security, accessibility, trust-boundary validation, data-loss prevention, integration checks, real-runtime evidence, destructive-action confirmation, or explicit authority for external effects.
