# Model Routing

Choose the cheapest capability and billing channel that clears the unit's quality, safety, authority, tool, context, language, and modality gates. Optimize after decomposition: a large implementation can become Fast when Lead or Standard has externalized its decisions into a complete contract.

## Gate quality before economics

Critical judgment, architecture, shared interfaces, destructive actions, permissions, external authority, and final integration remain Lead regardless of price. Fast is ineligible when it must infer product intent, change architecture, or decide a trust boundary.

Set a task-specific quality floor. Prefer verified local evidence for the same repository and task shape, then comparable independent agent results, adjacent coding evidence, broad indices, and provider claims. Discount stale versions, mismatched harnesses, small samples, missing domain evidence, unavailable tools, low confidence, and weak recency. Score implementation, test authoring, exploration, review/security, and multimodal work separately; never average unrelated benchmarks into a universal ranking.

## Optimize quota-weighted delivery

Raw tokens are a guardrail, not the primary subscription objective:

`QuotaBurn = sum(usage × account coefficient × channel scarcity) + retries + review + integration`

Account coefficient is the host's observed multiplier; channel scarcity reflects allowance, reset horizon, separate pools, and user preference. Unknown data stays unknown. Compare wall-clock critical path and a raw-token envelope against Direct or a verified similar route. Slightly more cheap worker tokens are acceptable only when they materially reduce expensive Lead usage or elapsed time without retry or review debt.

After the quality gate:

1. Remove routes outside the raw-token envelope or quality floor.
2. Keep the quality/quota/latency Pareto frontier.
3. Prefer the lowest expensive-token share and shortest useful critical path.
4. Choose the shallower organization when effectively tied.

For portable comparisons, expected cost per successful delivery remains useful:

`expected cost per successful delivery = (direct + retries + review + integration) / max(P(success), floor)`

Use local execution memory to improve estimates, never to bypass a hard gate. Record raw tokens, quota share, elapsed time, retries, and integrated defects when available.

## Assign organizational roles

- Fast: low residual discretion and deterministic acceptance; file count and original size are irrelevant.
- Standard: bounded domain ownership with local judgment; it may design and review Fast contracts.
- Lead: intent, architecture, Critical work, cross-domain interfaces, conflicts, combined verification, and final judgment.

Fast is a leaf. Standard delegates only within its domain and escalates shared decisions. Cheaper workers receive clearer contracts and checks, not a lower quality target.

## Codex adapter

When `gpt-5.3-codex-spark` has separate usage limits, prefer it for eligible Fast text-only contracts: fixed-decision implementation, tests, fixtures, deterministic migrations, focused checks, exploration, and bounded documentation. Exclude architecture, ambiguous repository-wide change, Critical work, browser/vision judgment, and integration. Use a verified domain-capable Standard model; the dated seed starts with Terra for general implementation and Luna for lower-risk volume, but current availability and local evidence win.

Codex has two worker routes: native subagents for models advertised by the native host, and the packaged external route when Spark is available to `codex exec` but absent natively. Host evidence belongs in the public design document, not a permanent rule here.

Every native Codex spawn encodes the route in `task_name`: `fast__<name>`, `standard__<name>`, or `lead__<name>`.

- Fast normally uses `fork_turns="none"` and a complete task-local contract.
- Standard uses a contract plus `none` or at most four relevant recent turns.
- Lead may use `all` only for a justified complex handoff that truly needs conversation history; it then inherits the parent Lead model and reasoning setting. Full history is not a cheaper-worker route.

Native Fast and Standard require explicit host-supported models. Fast normally uses `fork_turns="none"`; Standard uses none or at most four relevant turns. Only a justified full-history Lead handoff may use `all` and inherit Lead. Fast cannot delegate. The hook accepts `Agent`, `spawn_agent`, and `collaboration.spawn_agent`; if a specialized path bypasses `PreToolUse`, an unplanned Lead child gets a soft return check. Ambiguous concurrent or nested starts remain unverifiable rather than becoming false mismatches.

For an eligible Spark Fast contract when the native host does not advertise Spark, resolve `../scripts/dispatch_codex_worker.py` relative to this reference and run:

```bash
python3 <resolved-script> \
  --workdir <assigned-repository-or-worktree> \
  --task-name fast__<name> \
  --task-file <complete-contract.md> \
  --reasoning-effort medium
```

External startup/context is fixed raw-token overhead; use it only when avoided Lead work or parallel time pays back. Use isolated worktrees for parallel writers and unique result files. The adapter fixes Spark, sends the contract over stdin, disables plugins, apps, MCP, and further spawning, preserves provider and repository instructions, forbids danger-full-access, and propagates failure. It never performs a silent fallback. On failure, repair once, select another eligible worker, upgrade to Standard, or keep work local; never inherit Lead accidentally.

## Refresh discipline

Refresh consequential model, quota, and price assumptions. Record date, provider, harness, reasoning, billing channel, task profile, sample size, and uncertainty. The [model registry](../assets/model-registry.json) is a seed, not truth.

If a recurring route succeeds after combined verification, read [execution-memory.md](execution-memory.md) and preserve only the reusable pattern.
