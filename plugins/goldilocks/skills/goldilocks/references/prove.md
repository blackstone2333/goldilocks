# Prove

Choose the smallest evidence set that would fail if the claim were wrong. Evidence follows claim and risk, not worker seniority.

## Evidence depth

- Direct: inspect the output or diff and run one targeted check; do not invent tests for punctuation.
- Guarded: focused behavior or runnable acceptance check plus relevant static/build checks.
- Orchestrated: add per-workstream evidence, actual diff review, and combined integration verification.
- Critical: risk-specific negative tests, rollback or recovery evidence, full relevant suite, real-runtime checks, and independent review.

Verify UI, browser, device, deployment, network, hardware, and external-service claims on the actual relevant surface when available. Tests around a simulation do not prove a runtime claim.

## Review work

When requesting review, give the reviewer the end state, constraints, acceptance, relevant diff or commit range, and checks run—not the session's conclusions. Ask for prioritized correctness, regression, security, data-loss, and maintainability findings with file evidence. Use self-review for Direct work, focused independent review when major or orchestrated work benefits, and independent review for Critical changes.

When receiving feedback:

1. Restate the technical claim.
2. Inspect the cited code and reproduce or reason from evidence.
3. Ask only if the feedback is materially ambiguous.
4. Implement supported findings one coherent group at a time and rerun relevant checks.
5. Explain evidence when rejecting or narrowing a suggestion.

Avoid performative agreement, blind implementation, and reflexive dismissal. Review comments are hypotheses until verified.

## Completion gate

Immediately before claiming complete, map each claim to current decisive evidence and inspect the final diff and repository status. Run a check only when no evidence after the last relevant change proves that claim. “Fresh” means current-target evidence produced after the affected change—not rerunning an equivalent passing check for ceremony. Another agent's summary alone or confidence is not evidence; its inspectable result may be reused when integration did not invalidate it.

Workers may write tests and run independent focused checks in parallel. Require concise evidence summaries and inspect their actual diffs/results. Lead runs one combined acceptance only when integration changed the tested surface or no current integrated evidence exists; otherwise it does not repeat an equivalent worker check.

If the work used durable records, read [continuity.md](continuity.md) and verify the spec, plan status, project map, idea separation, debug links, and handoff are current. Stale documentation is an incomplete handoff, but documentation never substitutes for runtime evidence.

If a check cannot run or is forbidden, state what ran, what did not, why, and the exact claim that remains unverified. Do not claim completion.

## Finish a branch safely

After sufficient current verification, inspect branch/worktree state and present only applicable integration choices: keep for handoff, push the current branch, open a PR, merge locally, or clean up. Execute only the user's authorized choice. A request to push is not authority to open a PR, merge, release, or deploy.

Before destructive cleanup, name the branch/worktree and confirm changes are integrated or intentionally discarded. Never automatically delete a branch or worktree. Verify the remote or local result after the chosen action.

If a useful adjacent idea appears but is not required for current acceptance, do not follow it. Preserve it for final handoff; read [evolve.md](evolve.md) only when classification or durable capture is needed.
