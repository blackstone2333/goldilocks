# Testing and Verification

Choose the smallest evidence set that would fail if the requested behavior were wrong. Evidence depth follows the claim and risk, not worker seniority.

## Evidence by mode

| Mode | Minimum evidence |
|---|---|
| **Direct** | Inspect the diff or output and run one targeted check; trivial prose-only edits need no invented test |
| **Guarded** | Focused behavior test or runnable check plus relevant static/build checks |
| **Orchestrated overlay** | Add per-workstream checks, actual diff review, and integration verification to the applicable Guarded or Critical evidence |
| **Critical** | Risk-specific negative tests, rollback/recovery evidence, full relevant suite, and independent review |

For a behavior bug, capture a regression that fails before the fix when practical, then verify it passes. For an obvious root cause, keep the cycle focused; do not expand into a broad testing campaign without evidence of wider risk.

For new non-trivial behavior, define the smallest acceptance check and see it fail first when practical and cheap, then implement only enough to pass. If fail-first evidence is impossible or prohibited, state why and do not overclaim what the resulting test proves.

After three failed fix attempts or disproven hypotheses, stop patching. Reassess the root cause, assumptions, and architecture, and escalate the stage or capability level when needed.

## Constant quality gates

Apply every gate relevant to the task:

- **Acceptance:** each requested outcome has observable evidence.
- **Tests:** non-trivial branches, parsers, concurrency, and behavior changes have a runnable check.
- **Security and trust boundaries:** validate hostile or malformed input and preserve authentication/authorization invariants.
- **High-risk paths:** money, permissions, migrations, data loss, production, and public contracts receive strict targeted and negative tests.
- **Integration:** coordinated changes work together, not only in isolation.
- **Real runtime:** UI, browser, deployment, device, hardware, network, or external-service claims are checked on the actual relevant surface when available.
- **Authorization:** external writes, messages, pushes, releases, deployments, account changes, and destructive actions have authority. Tool access, credentials, or technical ability are not authorization.
- **Destructive action:** for high-impact or irreversible deletion, cleanup, overwrite, migration, or branch removal, confirmation names the action, target, environment, exact scope and blast radius, plus recovery or acknowledged irreversibility. A vague delegation is insufficient.
- **Fresh verification:** completion claims cite a current relevant command, runtime observation, or artifact inspection.

Review is proportional: self-review for Direct work, a focused independent pass when Standard/Orchestrated integration or judgment benefits, and independent review for Critical work.

When authorization details are incomplete, limit work to safe read-only inventory, preview, dry-run, draft, or recovery planning. Clearly authorized, low-impact, reversible external actions may remain Guarded; verify their result after execution.

If a required check cannot run, state what ran, what did not, why, and which claim remains unverified. Never replace fresh evidence with confidence, an old test result, or another agent's report.
