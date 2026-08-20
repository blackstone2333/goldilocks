# Model Routing

Choose the cheapest capability and billing channel that clears the unit's quality, safety, authority, tool, context, language, and modality gates. Classify after decomposition: a large unit can become Fast when its residual discretion has been externalized into a complete contract.

## Apply the quality gate before economics

Architecture, shared interfaces, destructive actions, permissions, external authority, trust boundaries, Critical judgment, and final integration remain Lead regardless of price. Fast is ineligible when it must infer product intent or architecture.

Set a task-specific quality floor. Prefer verified local evidence for the same repository and task shape, then comparable agent results, adjacent coding evidence, broad indices, and provider claims. Treat implementation, test authoring, exploration, review/security, and multimodal work separately. Penalize missing domain evidence, mismatched tools, small samples, low confidence, stale versions, and weak recency; never average unrelated benchmarks into one universal score.

## Optimize cost-weighted delivery

Resolve `../assets/model-economics.json`. It stores dated official input, cached-input, and output rates separately by model, billing channel, currency, service tier, region, and cache condition. Unknown stays unknown.

For the same token mix on ChatGPT Standard credits, Terra costs 40% and Luna 4% of Sol; current OpenAI Standard API prices have the same ratios. Spark uses a separate Pro usage pool with no public numeric rate, so it is never assigned a fake zero cost.

After equal quality and authority:

`DeliveryCost = token spend + scarce-budget share + time + briefing/review/integration + P(failure) × retry cost`

Within one pool, compute the official token charge. Across currencies or allowance pools, compare `estimated spend / remaining budget`; if budgets are unknown, preserve a cost/time/raw-token Pareto frontier instead of adding dollars, yuan, credits, and separate allowances. `QuotaBurn` is the spend-to-remaining-budget fraction for a known quota pool, not a universal cross-provider scalar.

Use elapsed critical path and a raw-token envelope as guardrails. A slightly slower cheap worker may win when expensive-token share falls materially without excessive review or retry. Remove routes below the quality floor or outside the guardrails, choose the useful Pareto frontier, then prefer the shallower organization when effectively tied.

Portable fallback:

`expected cost per successful delivery = (direct + retries + review + integration) / max(P(success), floor)`

Execution memory may refine time, failure, review, and retry estimates but never bypass a hard gate. Record uncached input, cached input, output, billing pool, price snapshot, elapsed time, retries, and integrated defects when available.

## Transfer the whole mutable chain

Evaluate delegation across every known stage that can still change the deliverable, not only the first ready unit. A spec, plan, debug note, or handoff is useful evidence, but durable documentation alone does not repay worker startup and Lead review.

Delegate staged mixed work only when one worker contract can own the complete known mutable execution chain through decisive acceptance. If Lead must implement a later known stage, repeat substantial exploration, or reconstruct worker context, include that work in the route comparison and default to Direct. Do not split one tightly coupled chain merely to create a cheaper first phase.

## Assign roles

- Fast: fixed decisions, low residual discretion, deterministic acceptance; it remains a leaf.
- Standard: bounded domain judgment and the narrow primary owner of its complete known
  mutable execution chain. It may contract a non-conflicting Fast leaf, then integrates
  it, performs one ordinary repair, and re-verifies before escalation.
- Lead: intent, architecture, Critical work, shared interfaces, authority/safety
  boundaries, conflicts, one proportional acceptance pass, and final judgment. It does
  not repeat owner exploration, and takes the chain back only for those boundaries or a
  repeated acceptance failure after the owner's repair.

Cheaper workers receive clearer contracts and checks, not a lower quality target. Standard escalates shared decisions.

## Fixed Codex employees

Resolve `../assets/codex-route-profiles.json`:

- `goldilocks_spark_worker`: native Spark XHigh Fast for deterministic coding/tests.
- `goldilocks_luna_economy`: native Luna Max Fast for latency-tolerant low-discretion
  general or document work.
- `goldilocks_terra_engineer`: native Terra Medium Standard for mixed implementation, durable documentation, and bounded judgment; it may contract Fast.
- `goldilocks_sol_reviewer`: fresh native Sol/High review-only task; inherits user-selected host permissions.

`goldilocks_spark_coder` and `goldilocks_luna_worker` remain packaged external-adapter
fallback profiles for non-native hosts.

Install native templates with `../../../scripts/install_agents.py`, then start a new task. The installer never edits `config.toml`, host permissions, or a differing file; use `../../../scripts/inspect_agent_runtime.py --record` when runtime evidence is incomplete.

Cache visibility is not route readiness. Confirm the model on the native host. Name
spawns exactly `fast__<name>_<model>`, `standard__<name>_<model>`, or
`lead__<name>_<model>`; do not add an `owner` name prefix. Set `fork_turns` explicitly.
The Hook fails closed for a missing tier/semantic prefix and derives `_luna`, `_spark`,
`_terra`, or `_sol` from the selected model:

- Fast: normally `none` plus a task-local contract.
- Standard: `none` or at most four relevant turns.
- Only a justified full-history Lead handoff may use `all`; it inherits Lead model and reasoning.

Fixed employees require explicit `agent_type`: `goldilocks_spark_worker`,
`goldilocks_luna_economy`, `goldilocks_terra_engineer`, or
`goldilocks_sol_reviewer`. Model overrides and suffixes never select them; generic fixed
model starts fail closed. Use the Adapter or keep work local when a role is invisible.
Only a justified Lead handoff may inherit Lead, and Fast cannot delegate. The Hook
accepts `Agent`, `spawn_agent`, and `collaboration.spawn_agent`; unplanned Sol returns
immediately, and a Fast/Standard disguise is unusable. Ambiguous concurrent or nested starts stay unverifiable.

## Host-visible Sol specialists (prototype)

After authorization, read [Sol Specialists](sol-specialists.md). Its visible Sol/high
path is separate from the native reviewer and hidden subagents: two slots, no nested
Sol, and mandatory origin return. Execution may delegate Terra/Spark/Luna; audit stays
read-only. Capability failure falls back openly. This is not Project Hub.

## External Fast adapter

Use `gpt-5.3-codex-spark` at XHigh for deterministic coding-only batches with decisive automated acceptance when its separate pool is available and startup cost is repaid. Spark is ineligible for pure documents, human-facing prose, or continuity records. Use `gpt-5.6-terra` at Medium for mixed implementation plus substantive spec, plan, debug, or handoff writing, and for bounded domain judgment or cross-file coordination. Use `gpt-5.6-luna` at Max for latency-tolerant, cost-first general or document work. Exclude architecture, Critical work, trust boundaries, final visual judgment, and final integration from Fast or Economy.

Night Shift is a delivery mode. Ordinary economy Night Shift uses Luna Max; urgent deterministic coding may use Spark XHigh. Spark has no reserve floor: use it when task-feasible, then fall back to Terra Medium, Luna Max, or Direct according to the work shape when unavailable or exhausted.

For an eligible external contract, resolve `../scripts/dispatch_codex_worker.py`:

```bash
python3 <dispatch-script> \
  --workdir <repository-or-worktree> \
  --task-name fast__<name> \
  --task-file <complete-contract.md> \
  --work-type luna \
  --capabilities project \
  --reasoning-effort medium
```

Use `--work-type spark-coding --reasoning-effort xhigh` only for a qualifying coding-only batch. Use `--work-type luna --reasoning-effort max` for Economy/Night Shift general work. `general` and `coding` remain compatibility aliases. The adapter calls `codex exec`, pins model/effort/sandbox, forbids danger-full-access, sends the contract on stdin, disables further delegation, and propagates failure without silent fallback.

The adapter derives the visible model suffix; callers may pass only the semantic base name.

`project` isolates global plugins, Apps, MCP, Skills, and Hooks while preserving repository rules. `minimal` also ignores execpolicy rules. `inherit` keeps the full environment only when the contract names a required installed capability. Clean profiles preserve authentication, provider, `models_cache.json`, and runtime.

Startup/context is fixed overhead. Always start with one Fast session and one coherent batch; add sessions only for measured parallel savings. Keep implementation and focused checks together. Do not debug transport inside product work.

If `GOLDILOCKS_WORKER_EVENTS_DIR` is set, the adapter retains child JSONL and returns its path; otherwise temporary events are deleted. Lead receives only the short result while usage remains auditable.

## Dynamic employee fallback

When no fixed employee fits but the host advertises a potentially cheaper model, read [agent-factory.md](agent-factory.md). Discovery is read-only. First preflight/create/use requires explicit user authorization for that model and billing channel; authorization is global until revoked. Visibility never proves sufficient allowance.

## Close and reuse routes

Native stop or external exit is only an observation. After Lead inspects the diff and reruns combined acceptance, resolve `../../../scripts/record_routing_outcome.py` and record `--agent-id` or `--route-id`, `--result pass|fail`, and fresh evidence. The recorder hashes evidence and rejects incomplete, mismatched, contradictory, or failed passes. Only `verified_pass` is reusable; failed acceptance is `verified_fail`.

Refresh consequential model, quota, price, and capability evidence. Record date, provider, model, reasoning, billing channel, task profile, sample size, and uncertainty. The [model registry](../assets/model-registry.json) is a seed, not truth. For recurring verified routes, read [execution-memory.md](execution-memory.md).
