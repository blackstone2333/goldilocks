---
name: goldilocks
description: Use when Codex must plan or execute project or coding work while minimizing unnecessary process, tokens, latency, or orchestration without reducing final quality. Applies when deciding whether to brainstorm, grill decisions, reuse existing solutions, plan, test, create a worktree, delegate, parallelize, review, verify, or record follow-up ideas.
---

# Goldilocks

**Minimum process. Constant quality.** Use the smallest workflow that can still produce the same high-standard result.

Process may shrink when the task or model is capable enough; required evidence cannot. A stronger worker may need fewer instructions, but it does not get weaker acceptance, safety, authorization, or verification standards.

## Route each stage, not the whole project

Inspect enough of the request and touched project flow to avoid guessing. At each stage, assess:

- **Ambiguity:** Are unresolved decisions likely to change the result?
- **Risk:** Could this affect security, permissions, money, production, data, public contracts, accessibility, or irreversible/external actions?
- **Coordination:** Would isolation, delegation, or parallel work save more than it costs?

Choose a quality mode for the current stage and re-evaluate when facts change. When multiple modes match, apply the strongest applicable risk gate. Add Orchestrated as an execution shape when coordination has positive net value; it can combine with Guarded or Critical and never weakens them.

| Mode | Observable shape | Default response |
|---|---|---|
| **Direct** | Clear, local, reversible, low-risk | Act directly; run one relevant check |
| **Guarded** | Non-trivial behavior, bug, limited ambiguity, or a clearly authorized low-impact reversible external action | State assumptions; use a short plan and focused tests |
| **Orchestrated** | Multiple coherent workstreams or meaningful integration | Overlay the applicable quality mode; define interfaces and isolate/delegate/parallelize only for net benefit |
| **Critical** | Security, permissions, money, migrations, production, data loss, high-impact or irreversible destructive/external action, or costly architecture | Resolve authority and design; use strict risk-specific tests and independent review |

Do not automatically chain brainstorming, a written plan, worktrees, TDD, subagents, review, and branch finishing. Load the next process only when its trigger becomes observable.

## Execute the minimum complete loop

1. **Define the end state.** Extract acceptance criteria, constraints, evidence needed, and non-goals. If material decisions remain, read [alignment-and-grilling.md](references/alignment-and-grilling.md).
2. **Inspect before inventing.** Trace the real flow and search existing project mechanisms. Before choosing architecture or adding code, read [reuse-and-planning.md](references/reuse-and-planning.md).
3. **Choose execution shape.** Work inline by default. For worktrees, delegation, parallelism, and capability routing, read [execution-and-model-routing.md](references/execution-and-model-routing.md).
4. **Preserve the quality floor.** Direct trivial prose/config work may inspect the output or diff and run one targeted check without loading another reference. For behavior changes, bugs, Orchestrated/Critical work, or runtime claims, read [testing-and-verification.md](references/testing-and-verification.md).
5. **Protect scope without losing ideas.** When a new idea appears during execution, classify it using [idea-ledger.md](references/idea-ledger.md).

## Interaction rules

- Investigate facts that tools or the project can answer; ask the user for decisions or authority.
- Ask only when an answer changes the end state, safety boundary, external effect, or a costly-to-reverse choice. Otherwise state a safe assumption and continue.
- Honor explicit user choices about scope, tools, delegation, testing, and delivery unless they conflict with safety, authorization, or applicable quality gates. If the user forbids necessary verification, respect the constraint, state the result is unverified, and do not claim completion.
- Keep updates proportional. Do not spend more words narrating the process than the task needs.

## Constant gates

Never optimize away applicable acceptance checks, regression evidence, trust-boundary validation, security, accessibility, data-loss prevention, integration checks, real-runtime validation, external authorization, destructive-action confirmation, or fresh verification.

If evidence cannot be obtained, report the exact unverified claim. Do not substitute confidence, model capability, review prose, or an old passing result.
