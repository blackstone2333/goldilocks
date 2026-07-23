# Model Routing

Choose the cheapest capability and billing channel that clears the unit's quality, safety, authority, tool, context, language, and modality gates. Optimize after decomposition: a large implementation can become Fast when Lead or Standard has externalized its decisions into a complete contract.

## Gate quality before economics

Critical judgment, architecture, shared-interface ownership, destructive actions, permissions, external authority, and final integration remain Lead regardless of price. Fast is ineligible when the worker must infer product intent, change architecture, or decide a trust boundary.

Set a task-specific quality floor. Prefer evidence in this order: verified local work on the same repository and task shape; comparable independent agent benchmarks; adjacent coding evidence; broad indices; provider claims. Discount stale versions, different harnesses, small samples, missing domain evidence, self-reporting, and unavailable tools. Do not average unrelated benchmarks into one universal model ranking.

Track confidence and recency explicitly. Score implementation, test authoring, exploration, review, security, frontend, and multimodal work by the evidence relevant to that profile.

## Optimize quota-weighted delivery

Raw token count is a guardrail, not the primary subscription objective. Estimate:

`QuotaBurn = sum(usage × account coefficient × channel scarcity) + retries + review + integration`

Account coefficient represents the host's real model multiplier or observed credit consumption. Channel scarcity reflects remaining allowance, reset horizon, a separate usage pool, and user preference. Unknown or stale quota data stays unknown; never invent a free channel or assume availability.

Also estimate wall-clock critical path and a raw-token envelope relative to the likely Direct route or a verified similar task. A route may use slightly more total tokens when cheap parallel workers substantially reduce expensive Lead usage or elapsed time. Reject orchestration that causes uncontrolled raw-token growth, repeated retries, or review debt.

After the quality gate:

1. remove routes outside the raw-token envelope;
2. remove candidates dominated on quota burn, quality, and latency;
3. prefer the Pareto route with the lowest expensive-token share and shortest useful critical path;
4. choose the shallower organization when results are effectively tied.

For portable public-price comparisons, expected cost per successful delivery remains useful:

`expected cost per successful delivery = (direct + retries + review + integration) / max(P(success), floor)`

Use local execution memory to improve estimates, never to bypass a hard gate. Record raw tokens, quota-weighted share, elapsed time, retries, and integrated defects when available.

## Assign organizational roles

- Fast: an execution contract with low residual discretion and deterministic acceptance. File count and original project size do not decide the role.
- Standard: bounded domain ownership or implementation with remaining local judgment. Standard may design several Fast contracts and review their domain result.
- Lead: user intent, product and architecture decisions, Critical work, cross-domain interfaces, conflict resolution, combined verification, and final judgment.

Fast is a leaf. Standard delegates only within its domain and escalates shared decisions. A lower-cost worker receives a clearer contract and stronger checks, not a lower quality target.

## Codex adapter

When ChatGPT Pro exposes `gpt-5.3-codex-spark` with separate usage limits, use it for eligible Fast text-only contracts: implementation whose decisions are already fixed, tests, fixtures, migrations with deterministic mappings, focused checks, exploration, and bounded documentation. Spark does not own architecture, ambiguous repository-wide changes, Critical work, vision/browser judgment, or integration.

For Standard Codex work, prefer a verified capable model for the domain. The dated seed starts with Terra for general repository implementation and Luna for lower-risk high-volume work, but availability and local evidence override that order. Lead uses the host's strongest suitable model.

Every Codex spawn encodes the route in `task_name`: `fast__<name>`, `standard__<name>`, or `lead__<name>`.

- Fast normally uses `fork_turns="none"` and a complete task-local contract.
- Standard uses a contract plus `none` or at most four relevant recent turns.
- Lead may use `all` only for a justified complex handoff that truly needs conversation history; it then inherits the parent Lead model and reasoning setting. Full history is not a cheaper-worker route.

The native hook rewrites `fast__` to `gpt-5.3-codex-spark`, removes inherited effort overrides, requires explicit Standard models, and prevents Fast workers from spawning. It permits explicit full-history Lead handoff, stores routing observations in a concurrency-safe local database, and audits actual models only when the host correlation is unique. Ambiguous concurrent or nested starts are marked unverifiable rather than assigned a false mismatch.

If a model override is rejected, a required worker is unavailable, or the actual model uniquely mismatches the route, do not retry by silently inheriting Lead. Keep the work local or deliberately reclassify it.

## Refresh discipline

Refresh consequential model, quota, and pricing assumptions. Record evidence date, provider, harness, reasoning level, billing channel, task profile, sample size, and uncertainty. The [model registry](../assets/model-registry.json) is a seed, not truth; never claim a universal best model.

If a recurring route succeeds after combined verification, read [execution-memory.md](execution-memory.md) and preserve only the reusable pattern.
