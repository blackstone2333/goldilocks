# Execution Memory

Reuse a verified execution pattern when doing so avoids repeating orchestration judgment. This is a selective project playbook, not a transcript, release changelog, or excuse to preserve every task.

## Look up before routing again

Search the repository's existing work notes first. If none exist and recurring routes have durable value, use `docs/work/execution-patterns.md` or the project's equivalent. Match task shape, subsystem, risk, tools, acceptance, and dependency pattern—not wording alone.

Treat a prior route as:

- reusable when the task shape and preconditions match, the prior result passed combined verification, and no invalidator changed;
- a candidate when only the subsystem or implementation pattern matches;
- stale when interfaces, dependencies, risk, authority, model availability, billing channel, or acceptance changed.

A cache hit removes repeated planning, not the short invalidation check. Critical, security, permission, production, financial, destructive, architecture, and final-integration work never downgrades solely because history says a cheaper route once worked.

## Record only useful evidence

After Lead accepts the combined result, update one compact pattern only when recurrence is plausible. Use [execution-pattern.md](../assets/execution-pattern.md) as a section menu and delete irrelevant fields. Record:

- recognizable task shape and project area;
- preconditions and invalidators;
- successful organization depth and role ownership;
- models or capability classes used;
- concurrency shape and isolation needs;
- acceptance evidence, retries, escalation, and observed defects;
- raw-token change when known, quota-weighted expensive share when known, elapsed time, evidence date, and confidence.

Do not store prompts, source code, credentials, private user data, account identifiers, raw logs, or invented quota numbers. Link to an existing test or commit instead of pasting evidence. A normal worker stop is an observation, not a verified success.

The native Codex plugin keeps concurrency-safe anonymous route observations in plugin data. These observations can inform later estimates, but only Lead-verified project patterns may be reused as successful playbooks.

Keep `CHANGELOG.md` separate. It remains user-facing release history, never an internal routing database.
