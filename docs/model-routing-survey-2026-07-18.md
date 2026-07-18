# Model Delegation Survey — 2026-07-18

This survey supports Goldilocks v0.2.4 model routing. It is a dated evidence snapshot, not a permanent ranking. Model versions, prices, quotas, harnesses, and provider access change quickly.

## Decision

Goldilocks should not rank workers by raw coding score divided by token price. That ratio explodes for nearly free models, ignores retries and review cost, and treats unrelated benchmarks as interchangeable.

The portable policy is:

1. Apply availability, modality, tool, context, data-policy, and risk gates.
2. Require a task-specific quality floor.
3. Build a Pareto shortlist on capability, expected cost per successful delivery, and wall-clock latency.
4. Use a logarithmic value score only to break ties.
5. Override public estimates with recent local results on the same repository and task shape.

## Public evidence screened

Independent benchmarks and aggregators:

- [SWE-bench](https://www.swebench.com/) for repository issue resolution and multilingual repository work.
- [Terminal-Bench 2.1](https://www.tbench.ai/leaderboard/terminal-bench/2.1) for terminal-agent execution, reported cost, and hack rate.
- [Aider Polyglot](https://aider.chat/docs/leaderboards/) for explicit code-edit correctness, edit-format reliability, cost, and response behavior.
- [LiveCodeBench](https://livecodebench.github.io/leaderboard.html) for contamination-resistant algorithmic coding.
- [Artificial Analysis](https://artificialanalysis.ai/leaderboards/models) for a broad intelligence index, blended price, output speed, first-token latency, and end-to-end response time.

Official availability and pricing sources:

- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Codex speed](https://learn.chatgpt.com/docs/agent-configuration/speed), and [Codex pricing](https://learn.chatgpt.com/docs/pricing).
- [OpenAI](https://developers.openai.com/api/docs/pricing), [Anthropic](https://claude.com/pricing), [Google](https://ai.google.dev/gemini-api/docs/pricing), [xAI](https://docs.x.ai/developers/models), [DeepSeek](https://api-docs.deepseek.com/quick_start/pricing/), [Alibaba](https://www.alibabacloud.com/help/en/model-studio/model-pricing), [Kimi](https://platform.kimi.ai/docs/pricing), [MiniMax](https://platform.minimax.io/docs/pricing/overview), [Z.ai](https://docs.z.ai/guides/overview/pricing), and [Mistral](https://docs.mistral.ai/models/overview).

## Comparable agentic snapshot

The following rows had both Terminal-Bench 2.1 and a comparable Artificial Analysis entry. “Example value” uses the formula below and is normalized to the best model in this small comparable set. It is not a universal model ranking.

| Model | Terminal-Bench | TB cost | AA intelligence | AA blended $/1M | AA end-to-end | Example value |
|---|---:|---:|---:|---:|---:|---:|
| Grok 4.5 | 79.3% | $134.09 | 54 | $1.35 | 17.74s | 100.0 |
| Muse Spark 1.1 | 76.2% | $198.05 | 51 | $0.78 | 24.10s | 94.0 |
| Claude Opus 4.8 | 78.9% | $286.94 | 56 | $3.85 | 45.91s | 91.3 |
| GPT-5.6 Luna | 75.7% | $241.45 | 51 | $0.87 | 83.47s | 79.9 |
| Claude Fable 5 | 83.8% | $552.67 | 60 | $7.70 | 132.16s | 79.8 |
| GPT-5.6 Terra | 78.4% | $421.15 | 55 | $2.17 | 141.16s | 73.9 |
| Claude Sonnet 5 | 74.6% | $288.18 | 53 | $1.54 | 199.71s | 70.6 |
| GPT-5.5 | 83.1% | $2,059.19 | 55 | $4.35 | 72.62s | 61.8 |
| GLM-5.1 | 58.7% | $277.14 | 40 | $0.90 | 70.79s | 52.2 |

Grok 4.5's Terminal-Bench submission reported a `-9.0%` hack adjustment, so Goldilocks records a reliability penalty rather than treating its price-performance lead as unconditional. Harness and reasoning-level mismatches also lower confidence for every cross-site comparison.

Models with strong current broad metrics but no comparable Terminal-Bench row—including Kimi K3, Qwen3.7 Max, MiniMax-M3, and DeepSeek V4 Pro—remain candidates, not scored winners. They should enter a local bake-off before repeated delegation.

## Direction-specific evidence

No single public benchmark covers all delegation work:

- Repository fixes: emphasize SWE-bench and local issue-resolution success.
- Terminal agents and multi-step execution: emphasize Terminal-Bench.
- Mechanical edits and patch formatting: emphasize Aider edit correctness and well-formed output.
- Algorithmic implementation: emphasize LiveCodeBench.
- Multilingual repositories: use SWE-bench Multilingual; its public snapshot showed materially different ordering from terminal-agent results.
- Exploration and log analysis: emphasize context, speed, first-token latency, tool reliability, and summarization quality.
- Tests: combine repository/terminal evidence with local mutation-catching and false-positive rates.
- Review, security, frontend, and multimodal work: require local or domain-specific evidence because the broad public leaderboards are insufficient.

Aider's older public rows illustrate why recency matters but also why cheap specialists deserve testing: DeepSeek V3.2 Exp Reasoner reported 74.2% at $1.30, its Chat variant 70.2% at $0.88, and Kimi K2 59.1% at $1.24. These results should not be transferred directly to newer model versions or another agent harness.

## Scoring standard

For task profile `p`, normalize each relevant evidence value to `0..1` and calculate:

`Q(p,m) = 100 × product(normalized_evidence_i ^ task_weight_i)`

Use a geometric mean so a serious deficiency cannot hide inside a high average. Estimate confidence from source independence, sample size, recency, version match, harness match, and local replication.

Estimate full delivery economics:

`CostSuccess = (direct token/tool cost + expected retries + review + integration) / max(P(success), 0.05)`

Subscription workers use opportunity cost instead of pretending to be free: remaining quota, reset horizon, competing uses, and billing channel. A genuinely separate quota lowers this cost without lowering the quality requirement.

After the quality gate and Pareto filter, use:

`Value = Q^1.5 × reliability × confidence / ((1 + ln(1 + CostSuccess/Cref))^0.65 × (1 + ln(1 + latency/Lref))^0.35)`

Normalize the best eligible candidate to 100. Suggested starting floors are profile-dependent: Fast requires deterministic checks and a narrow scope; Standard needs evidence on comparable cross-file work; Lead requires high confidence with no critical capability deficit. Critical work is never assigned by value score alone.

## Codex-specific result

Official Codex documentation describes GPT-5.3-Codex-Spark as a fast, less-capable, text-only research-preview model for ChatGPT Pro with its own usage limits. Goldilocks therefore treats it as the first candidate for eligible Fast work when that channel is available:

- mechanical code and fixture generation;
- test scaffolding and focused checks;
- narrow refactors and deterministic migrations;
- read-heavy exploration returned as a concise summary.

Spark does not own architecture, ambiguous repository-wide work, security or Critical decisions, vision/browser work, final review, or integration. GPT-5.6 Terra/Luna are fallbacks for bounded workers; the main model retains complex core logic and combined acceptance.

## Maintenance rule

Refresh the registry when a provider changes a model/version/price, a major independent benchmark publishes comparable results, or local outcomes contradict the public estimate. Keep raw metrics, evidence dates, reasoning levels, and uncertainty; do not silently rewrite historical benchmark claims.
