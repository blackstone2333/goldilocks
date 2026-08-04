# Route Card

Use this card for the first decision; load full orchestration only for actual delegation, worktrees, or layered integration.

Compare once. Speed alone does not decide:

`DirectCost = Lead token spend/budget share + Direct time + failure risk`

`DelegateCost = worker token spend/budget share + elapsed time + briefing + review + integration + failure × retry`

Use official channel-specific input/cached/output rates. Compare different currencies or allowance pools by their remaining-budget fractions, or keep a Pareto comparison when budgets are unknown. Never invent one blended number.

- Direct when its weighted cost wins, work is inseparable, or authority must remain local. A slightly faster Lead is not cheaper by definition.
- Fast requires fixed objective, surface, interfaces, prohibitions, and acceptance.
- Standard owns one bounded domain with local judgment.
- Lead retains intent, shared decisions, authority, integration, and acceptance.

Emit one line only:

`ROUTE=<direct|fast|standard|mixed> | WRITE_READY=<n> | READ_READY=<n> | EXISTING=<n> | NEW_DISPATCH=<n> | LEAD=<nodes> | REASON=<code> | DETAIL=<sentence>`

`EXISTING` is user/other-workflow ownership; `NEW_DISPATCH` is workers started now. Use `lead_faster`, `shared_surface`, `critical_judgment`, `contract_not_ready`, `route_unavailable`, `review_cost`, `parallel_gain`, or `quota_gain`.

With an active project grant, verified route, equal acceptance, and lower scarce-quota cost, dispatch the highest-value unit by default even when it is slightly slower. Raw-token or elapsed growth must remain proportionate. Direct needs concrete weighted-cost, quality, shared-surface, failed-route, or authority evidence. The grant permits bounded Fast/Standard dispatch only; it adds no external or destructive authority.

Persist explicit user approval with `../../../scripts/project_delegation.py --grant --authority explicit-user --workdir <project>`; never infer approval.

If dispatching, read [orchestrate.md](orchestrate.md) and [model-routing.md](model-routing.md), then verify the route. Workers return `STATUS`, `CHANGES`, `VERIFIED`, `JUDGMENT CALLS`, and `GAPS`; Lead inspects evidence and integrates.
