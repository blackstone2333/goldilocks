# Model Routing

Use this protocol after planning when multiple workers or model choices are available. Select the cheapest, fastest worker that clears the task's quality and safety floor—not the cheapest model overall and not the strongest model for every unit.

## Eligibility before ranking

Apply hard gates first: availability, tool access, context size, modality, language, data policy, task risk, and required authority. Critical judgment, architecture, shared-interface ownership, destructive actions, and final integration remain with Lead capability regardless of price.

Set a task-specific quality gate. A candidate below it is ineligible even when free. Prefer evidence in this order:

1. local evidence on the same repository and task shape;
2. relevant independent benchmark under a comparable agent harness;
3. adjacent coding or tool-use benchmarks;
4. broad intelligence indices;
5. provider claims only when nothing stronger exists.

Do not average unrelated benchmarks blindly. Score repository fixes, mechanical edits, test authoring, exploration, terminal work, review, security, frontend work, and multimodal work separately.

## Capability and confidence

Normalize each applicable benchmark to `0..1` within a current candidate set. Use a weighted geometric mean so one serious weakness cannot disappear inside a high average:

`Q = 100 × product(score_i ^ weight_i)`

Weight evidence by relevance to the current unit. Repository implementation should emphasize SWE-bench and terminal-agent evidence; explicit edits can emphasize edit correctness; exploration emphasizes context, speed, and tool reliability. Use local acceptance history whenever available.

Multiply conclusions by confidence and recency. Confidence falls when a result uses another model version, a different harness, missing cost data, few samples, self-reported results, or only one benchmark. Treat the dated [model registry](../assets/model-registry.json) as a seed, not truth.

## Cost, latency, and value

Compute direct cost from expected uncached input, cached input, output, tool charges, and provider pricing. Add expected retry, review, and integration work. For subscriptions or quotas, replace dollar price with opportunity cost: quota pressure, reset horizon, and whether the worker uses a separate billing channel.

`expected cost per successful delivery = (direct + retries + review + integration) / max(P(success), floor)`

Separate usage limits lower opportunity cost but do not waive the quality gate. Include expected wall-clock latency, not only tokens per second; long first-token delay and retries matter.

After the quality gate, remove candidates dominated on quality, cost, and latency using a Pareto frontier. For a portable tie-breaker, normalize within the eligible set:

`Value = Q^1.5 × reliability × confidence / ((1 + ln(1 + cost/Cref))^0.65 × (1 + ln(1 + latency/Lref))^0.35)`

This deliberately rewards capability more than price and uses logarithms so a near-free weak model cannot win by denominator collapse. Local measured success and user billing preferences override the public seed.

## Assign execution roles

- Fast: deterministic mechanical edits, fixtures, formatting, code search, test authoring and focused test execution, log triage, and bounded documentation.
- Standard: known-pattern cross-file implementation with stable interfaces and executable acceptance.
- Lead: ambiguity, architecture, complex core logic, Critical work, cross-workstream interfaces, review, conflict resolution, and final judgment.

Delegate test authoring and focused test execution when independent, but the Lead reviews the tests and reruns combined verification in the integrated workspace. A worker summary is not completion evidence.

## Codex adapter

When Codex reports ChatGPT Pro access and `gpt-5.3-codex-spark` is available with separate usage limits, prefer it for eligible Fast, text-only work: mechanical code, test scaffolding, fixtures, narrow refactors, exploration summaries, and focused checks. This honors its low billing-channel opportunity cost and near-instant iteration.

Do not route architecture, ambiguous repository-wide changes, security decisions, Critical work, vision/browser tasks, or final integration to Spark. If Spark is unavailable or misses the quality gate, prefer an available efficient Codex worker such as Terra or Luna before consuming the Lead model for bounded work. Preserve the user's explicit model choice and actual host capability over this advisory order.

## Refresh discipline

Before making a consequential or repeated routing policy, refresh official pricing and availability, relevant independent leaderboards, and local success data. Record evidence date, harness, reasoning level, price channel, task profile, and uncertainty. Never claim a universal “best model”; publish role-specific tiers and the Pareto shortlist.
