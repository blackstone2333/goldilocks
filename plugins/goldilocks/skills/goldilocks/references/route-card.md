# Route Card

Use once before multi-unit implementation; load orchestration only when dispatching.

`DirectCost = Lead budget share + time + failure risk`

`DelegateCost = worker budget share + time + briefing + review + integration + failure × retry`

Use official active-channel rates; keep separate pools on a cost/time/token Pareto frontier when remaining budgets are unknown.

Codex same-mix seed: Luna = `0.04 × Sol`; Terra = `0.40 × Sol`; Spark remains a separate unpriced pool. Token-charge break-even is about `25×` and `2.5×` Sol raw tokens before other costs.

Fast gets fixed scope and acceptance; Standard gets bounded judgment; Lead keeps intent, authority, integration, and acceptance.

Before implementation or dispatch, write the canonical audit record only inside an HTML
comment. Keep its field names and reason code in English exactly as shown:

`<!-- ROUTE=<direct|fast|standard|mixed> | WRITE_READY=<n> | READ_READY=<n> | EXISTING=<n> | PLANNED_DISPATCH=<n> | LEAD=<nodes> | REASON=<code> | DETAIL=<sentence> -->`

`EXISTING` means host-confirmed running ownership, never UI labels, completed/idle handles, artifacts, or historical `task_started`. `PLANNED_DISPATCH` means intended starts. Use `lead_faster`, `shared_surface`, `critical_judgment`, `contract_not_ready`, `route_unavailable`, `review_cost`, `parallel_gain`, or `quota_gain`.

After dispatch attempts return—or immediately for a Direct choice made inside
orchestration—show exactly one short receipt in the user's primary language. Do not show
the canonical comment or both languages. The root Direct exit shows the same compact
receipt through the always-loaded response contract without reading this card.

- English: `ROUTE=mixed | TEAM=Lead+3 workers | CONCURRENCY=3/6 | DELEGATED=tests, parser, +1 | LEAD=integration | REASON=parallel gain | DETAIL=...`
- 中文：`路由=混合｜团队=主模型+3 个子智能体｜并发=3/6｜委派=测试、解析、+1｜主模型=整合｜理由=并行收益｜详情=…`

`TEAM` and the numerator of `CONCURRENCY` are host-confirmed successful starts or
currently active workers, never `PLANNED_DISPATCH`; write `?` when the host limit is
unknown. If a start fails, show the actual count and name the fallback in `DETAIL`.
List at most three delegated items, then `+N`. Translate only the receipt reason:
`lead_faster` → `lead faster` / `主模型更快`; `shared_surface` → `shared surface` /
`共享写入面`; `critical_judgment` → `critical judgment` / `关键判断`;
`contract_not_ready` → `contract not ready` / `合同未就绪`; `route_unavailable` →
`route unavailable` / `路由不可用`; `review_cost` → `review cost` / `审核成本`;
`parallel_gain` → `parallel gain` / `并行收益`; `quota_gain` → `quota gain` /
`额度收益`.

Price every independent ready unit before Direct. Shared writes block conflicting writers, not read-only work. With `READ_READY > 0`, `shared_surface` alone cannot justify `PLANNED_DISPATCH=0`. `review_cost` must name concrete transfer, acceptance, retry, or time evidence; generic “extra tokens” or Lead convenience is insufficient.

Silently reuse run data; create no probe. Direct needs concrete weighted-cost, quality, authority, route-failure, or inseparability evidence. With an active grant, verified route, equal acceptance, and lower scarce-quota cost, dispatch the highest-value ready unit within time and raw-token bounds.

Evaluate Fast before Standard. If all workers are Terra, `DETAIL` explains why judgment, tools, authority, or acceptance exclude Fast. Missing native Luna visibility is not `route_unavailable` while the adapter works. Name children `<tier>__<semantic>_<model>` before native spawn; `SubagentStart` is too late to rename.

Collect terminal children with host wait/status; never make the user open one. Persist approval with `../../../scripts/project_delegation.py --grant --global --authority explicit-user`; use project `--revoke` for opt-out.

If dispatching, read [orchestrate.md](orchestrate.md) and [model-routing.md](model-routing.md). Workers return `STATUS`, `CHANGES`, `VERIFIED`, `JUDGMENT CALLS`, and `GAPS`; Lead accepts the result.
