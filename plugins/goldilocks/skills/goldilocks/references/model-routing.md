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

Use `gpt-5.6-luna` as the universal Fast baseline for focused coding, tests, exploration, extraction, routing, automation, and bounded content production. Its July 31, 2026 pricing and Codex allowance make it the first probe when the contract is low-discretion and objectively checkable. Use `gpt-5.3-codex-spark` instead for text-only deterministic coding batches when its separate Pro usage pool is available and the batch repays external startup cost. Spark is quota arbitrage plus coding specialization, not the universal Fast default.

Use `gpt-5.6-terra` as the OpenAI Standard baseline when bounded work still needs material domain judgment, cross-file coordination, or local integration. Luna may cross the Standard boundary only for low-risk work with stable interfaces and decisive acceptance; one quality miss or unresolved judgment upgrades the unit to Terra instead of starting a cheap retry loop. Exclude architecture, ambiguous repository-wide change, Critical work, trust boundaries, final visual judgment, and final integration from both Fast models. Classify by the work actually produced, not the file extension: formula or code automation is coding, while a focused code edit may still be Luna-eligible.

Codex has two worker routes: native subagents for models advertised by the native host, and the packaged external route when the selected Fast model is available to `codex exec` but absent natively. Host evidence belongs in the public design document, not a permanent rule here.

Every native Codex spawn encodes the route in `task_name`: `fast__<name>`, `standard__<name>`, or `lead__<name>`.

- Fast normally uses `fork_turns="none"` and a complete task-local contract.
- Standard uses a contract plus `none` or at most four relevant recent turns.
- Lead may use `all` only for a justified complex handoff that truly needs conversation history; it then inherits the parent Lead model and reasoning setting. Full history is not a cheaper-worker route.

Native Fast and Standard require explicit host-supported models. Fast normally uses `fork_turns="none"`; Standard uses none or at most four relevant turns. Only a justified full-history Lead handoff may use `all` and inherit Lead. Fast cannot delegate. The hook accepts `Agent`, `spawn_agent`, and `collaboration.spawn_agent`; if a specialized path bypasses `PreToolUse`, an unplanned Lead child gets a soft return check. Ambiguous concurrent or nested starts remain unverifiable rather than becoming false mismatches.

For an eligible external Fast contract, resolve `../scripts/dispatch_codex_worker.py` relative to this reference. Luna is the default:

```bash
python3 <resolved-script> \
  --workdir <assigned-repository-or-worktree> \
  --task-name fast__<name> \
  --task-file <complete-contract.md> \
  --work-type luna \
  --capabilities project \
  --reasoning-effort medium
```

Use `--work-type spark-coding` only for a qualifying Spark batch. The legacy `general` and `coding` names remain compatibility aliases for Luna and Spark respectively.

External startup/context is fixed overhead; require Lead or parallel savings. When no verified route memory exists, **start with one Fast session** and give it **one coherent batch** whose units remain separately checkable. Increase the session count only when measured useful work or critical-path savings repay another startup. Do not split implementation from its focused checks or turn every replaceable unit into a session.

The adapter offers three explicit capability profiles:

- `project` is the default: isolate global plugins, Apps, MCP, Skills, and Hooks while preserving repository instructions and rules.
- `minimal` uses the same clean worker home and also ignores user/project execpolicy rules for contracts that need only built-in execution tools.
- `inherit` keeps the user's full environment only when the contract names an installed external capability it actually needs.

Clean profiles preserve authentication, provider, `models_cache.json`, and bundled runtime. Every profile sets `GOLDILOCKS_WORKER=1`, silencing inherited continuity/update Hooks without weakening leaf enforcement. The adapter fixes the model (`luna` → Luna, `spark-coding` → Spark), sends the contract over stdin, forbids danger-full-access, and propagates failure without silent fallback. Startup failure invalidates the route; repair it separately rather than inside product work.

For measured or long-running work, set `GOLDILOCKS_WORKER_EVENTS_DIR` to a persistent directory. The adapter writes child JSONL there and returns only its path, exit code, and short final result to Lead, preventing raw worker transcripts from re-entering expensive context while keeping usage auditable. Without the variable, output behavior remains unchanged.

Native `SubagentStop` records only an observed completion. After Lead inspects the actual diff and reruns the relevant combined acceptance, resolve the plugin's `scripts/record_routing_outcome.py` and close the route explicitly:

```bash
python3 <resolved-script> \
  --agent-id <completed-agent-id> \
  --result pass \
  --evidence "<fresh command and concise result>"
```

Use `--result fail` when integration or acceptance rejects the worker result; the status becomes `verified_fail`. The recorder stores only an evidence hash, is idempotent, and refuses unstopped, uncorrelated, model-mismatched, or contradictory outcomes. Only `verified_pass` routes may become reusable execution memory.

## Refresh discipline

Refresh consequential model, quota, and price assumptions. Record date, provider, harness, reasoning, billing channel, task profile, sample size, and uncertainty. The [model registry](../assets/model-registry.json) is a seed, not truth.

If a recurring route succeeds after combined verification, read [execution-memory.md](execution-memory.md) and preserve only the reusable pattern.
