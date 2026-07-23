# Goldilocks v0.2.6 routing-guard contract test

- Date: 2026-07-23
- Scope: native Codex hook behavior, Skill contract, plugin structure
- Runtime certification: not claimed

## Observed RED baseline

A real v0.2.5 project spawned five children without `model` or `reasoning_effort`. Four used `fork_turns="all"`; the fifth used four turns. Every child actually started as `gpt-5.6-sol` at `xhigh`, so Spark's separate limit was untouched. The previous routing prose said to prefer Spark but did not affect the tool input.

Before implementation, `tests/test_agent_routing_hook.py` failed because no routing guard existed.

## Implemented contract

- `fast__` + bounded context rewrites the call to `gpt-5.3-codex-spark` and clears inherited effort, service tier, and role overrides.
- `standard__` and `lead__` require an explicit model.
- Missing tiers, omitted or full-history forks, and forks above four turns are denied before execution.
- `SubagentStart` compares the actual model with the latest unmatched planned route. A mismatch instructs the child not to execute.
- Routing records contain task names and model metadata, not prompts, and live in plugin data rather than the repository.

## Fresh checks

```text
Goldilocks agent routing hook contract passed.
Goldilocks recovery hook contract passed.
Goldilocks v0.2 contract passed with 60 trigger cases.
Three Bears contract passed: 9 tasks, 5 arms, all reference instruments valid.
14/14 Skills valid.
Plugin validation passed.
```

## Boundary

These deterministic checks prove blocking, rewriting, audit, mismatch handling, existing contracts, and package structure. They do not yet prove real-project token or wall-clock savings, Spark availability on every account, or unchanged integration-defect rates. Those require a new trusted-hook task and measured runtime traces.
