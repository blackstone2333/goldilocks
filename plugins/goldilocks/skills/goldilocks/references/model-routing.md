# Model Routing

Use this protocol after planning when multiple workers or model choices are available. Select the cheapest, fastest worker that clears the task's quality and safety floor—not the cheapest model overall and not the strongest model for every unit.

## Eligibility before ranking

Apply hard gates first: availability, tool access, context size, modality, language, data policy, task risk, and required authority. Critical judgment, architecture, shared-interface ownership, destructive actions, and final integration remain with Lead capability regardless of price.

Set a task-specific quality gate; a candidate below it is ineligible even when free. Prefer local evidence on the same repository and task shape, then comparable independent benchmarks, adjacent coding evidence, broad indices, and finally provider claims. Score repository fixes, mechanical edits, tests, exploration, terminal work, review, security, frontend, and multimodal work separately instead of averaging unrelated benchmarks.

## Capability and confidence

Normalize applicable benchmarks to `0..1` within the current candidates. Use a weighted geometric mean so one serious weakness cannot disappear inside an average:

`Q = 100 × product(score_i ^ weight_i)`

Weight by task relevance and local acceptance history. Discount confidence and recency for version or harness mismatch, missing cost, few samples, self-reporting, or single-benchmark evidence. Treat the dated [model registry](../assets/model-registry.json) as a seed, not truth.

## Cost, latency, and value

Compute direct cost from expected input, output, tools, and pricing, then add retry, review, and integration. For quotas, use opportunity cost: pressure, reset horizon, and separate billing channels.

`expected cost per successful delivery = (direct + retries + review + integration) / max(P(success), floor)`

Separate limits lower opportunity cost but never waive the quality gate. Count wall-clock latency and retries, not only tokens per second.

After the quality gate, remove candidates dominated on quality, cost, and latency using a Pareto frontier. For a portable tie-breaker, normalize within the eligible set:

`Value = Q^1.5 × reliability × confidence / ((1 + ln(1 + cost/Cref))^0.65 × (1 + ln(1 + latency/Lref))^0.35)`

This favors capability and prevents a near-free weak model winning by denominator collapse. Local success and user billing preferences override the seed.

## Assign execution roles

- Fast: deterministic mechanical edits, fixtures, formatting, code search, test authoring and focused test execution, log triage, and bounded documentation.
- Standard: known-pattern cross-file implementation with stable interfaces and executable acceptance.
- Lead: ambiguity, architecture, complex core logic, Critical work, cross-workstream interfaces, review, conflict resolution, and final judgment.

Delegate test authoring and focused test execution when independent, but the Lead reviews the tests and reruns combined verification in the integrated workspace. A worker summary is not completion evidence.

## Codex adapter

When Codex reports ChatGPT Pro access and `gpt-5.3-codex-spark` is available with separate usage limits, route eligible Fast, text-only work to it: mechanical code, test scaffolding, fixtures, narrow refactors, exploration summaries, and focused checks. This honors its low billing-channel opportunity cost and near-instant iteration.

Do not route architecture, ambiguous repository-wide changes, security decisions, Critical work, vision/browser tasks, or final integration to Spark. If Spark is unavailable or misses the quality gate, prefer an available efficient Codex worker such as Terra or Luna before consuming the Lead model for bounded work. Preserve the user's explicit model choice and actual host capability over this advisory order.

For every Codex spawn, encode the route in `task_name`: `fast__<name>`, `standard__<name>`, or `lead__<name>`. Set `fork_turns` explicitly to `none` or at most four recent turns; never use `all`. A Fast packet should normally use `none` and contain the objective, scope, stable interfaces, repository paths, acceptance, and prohibitions.

The Goldilocks Codex hook rewrites `fast__` calls to `gpt-5.3-codex-spark`, removes inherited effort or role overrides, and audits the actual started model. Standard and Lead subagents require an explicit model; inheriting Lead is an escalation, not a default. If Codex rejects the override, Spark is unavailable, or the actual model mismatches the route, do not retry without a model or full-fork the parent. Keep the work local or reclassify it. An explicit user model choice uses an explicit Standard or Lead route rather than bypassing the guard.

## Refresh discipline

Before making a consequential or repeated routing policy, refresh official pricing and availability, relevant independent leaderboards, and local success data. Record evidence date, harness, reasoning level, price channel, task profile, and uncertainty. Never claim a universal “best model”; publish role-specific tiers and the Pareto shortlist.
