# Route Card

Use once before multi-unit implementation; load orchestration only for delegation.

`DirectCost = Lead budget share + time + failure risk`

`DelegateCost = worker budget share + time + briefing + review + integration + failure × retry`

Use official active-channel rates. Compare separate pools by remaining-budget share; otherwise keep a Pareto result.

- Direct: weighted cost wins, work is inseparable, or authority stays local.
- Fast: fixed scope, interfaces, prohibitions, and acceptance.
- Standard: bounded domain judgment.
- Lead: intent, authority, integration, and acceptance.

Emit one line:

`ROUTE=<direct|fast|standard|mixed> | WRITE_READY=<n> | READ_READY=<n> | EXISTING=<n> | PLANNED_DISPATCH=<n> | LEAD=<nodes> | REASON=<code> | DETAIL=<sentence>`

`EXISTING` is host-confirmed running ownership, not completed artifacts, idle/UI handles, or historical `task_started`. Resolve conflicts with host status/list. `PLANNED_DISPATCH` is intended starts. Use `lead_faster`, `shared_surface`, `critical_judgment`, `contract_not_ready`, `route_unavailable`, `review_cost`, `parallel_gain`, or `quota_gain`.

Collect terminal children with host wait/status; never make the user open them. Stale records count only when host-confirmed running.

Silently check run data without creating probes or narration. Recheck preconditions; one useful contract may validate a route, while startup failure returns Direct.

With an active grant, verified route, equal acceptance, and lower scarce-quota cost, dispatch the highest-value ready unit even when slightly slower, while keeping time and raw tokens proportionate. Direct needs concrete cost, quality, shared-surface, route-failure, or authority evidence.

Evaluate every ready unit for Fast before Standard. If all workers are Terra, `DETAIL` states why residual judgment, tools, authority, or acceptance make Fast ineligible. Missing native Luna visibility is not `route_unavailable` while the verified adapter works. Name children `<tier>__<semantic>_<model>`.

Persist approval with `../../../scripts/project_delegation.py --grant --global --authority explicit-user`; use project `--revoke` for opt-out. The grant adds no external or destructive authority.

If dispatching, read [orchestrate.md](orchestrate.md) and [model-routing.md](model-routing.md). Workers return `STATUS`, `CHANGES`, `VERIFIED`, `JUDGMENT CALLS`, and `GAPS`; Lead inspects and accepts.
