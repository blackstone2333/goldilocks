# Route Card

Use this card for the first decision; load full orchestration only for actual delegation, worktrees, or layered integration.

Compare once:

`gain = Lead work avoided + parallel time + quota benefit - briefing - review - integration - retry risk`

- Direct when Lead finishes before briefing plus review, work is inseparable, or authority must remain local.
- Fast requires fixed objective, surface, interfaces, prohibitions, and acceptance.
- Standard owns one bounded domain with local judgment.
- Lead retains intent, shared decisions, authority, integration, and acceptance.

Emit one line only:

`ROUTE=<direct|fast|standard|mixed> | WRITE_READY=<n> | READ_READY=<n> | EXISTING=<n> | NEW_DISPATCH=<n> | LEAD=<nodes> | REASON=<code> | DETAIL=<sentence>`

`EXISTING` is user/other-workflow ownership; `NEW_DISPATCH` is workers started now. Use `lead_faster`, `shared_surface`, `critical_judgment`, `contract_not_ready`, `route_unavailable`, `review_cost`, `parallel_gain`, or `quota_gain`.

With an active project grant, verified route, and positive gain, dispatch the highest-value unit by default. Direct needs concrete evidence: Lead finishes first, startup failed, shared writes conflict, transfer costs more, or authority cannot move. The grant permits bounded Fast/Standard dispatch only; it adds no external or destructive authority.

Persist explicit user approval with `../../../scripts/project_delegation.py --grant --authority explicit-user --workdir <project>`; never infer approval.

If dispatching, read [orchestrate.md](orchestrate.md) and [model-routing.md](model-routing.md), then verify the route. Workers return `STATUS`, `CHANGES`, `VERIFIED`, `JUDGMENT CALLS`, and `GAPS`; Lead inspects evidence and integrates.
