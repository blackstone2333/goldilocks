# Three Bears — GPT-5.6 high model sweep

This exploratory run compares Terra, Luna, and Sol while holding the provider, reasoning level, tasks, arms, concurrency, and benchmark revision constant. It is not a statistical model ranking.

## Setup

- Models: `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.6-sol`
- Reasoning: `high`
- Provider: isolated OpenAI-compatible custom Responses provider; endpoint and credentials omitted
- Tasks: `baby-docs`, `mama-empty-query`, `papa-offline-design`
- Arms: Baseline, Goldilocks, Superpowers, Ponytail, Grill
- Runs: one per model/task/arm cell; 45 completed turns
- Workers: 3
- Goldilocks: v0.2.2 instruction tree

All 45 cells passed their quality gates.

## Whole-matrix model cost

Totals include all five arms and all three tasks.

| Model | Quality | Total tokens | Uncached input | Output | Cumulative seconds | Tools | Skill activity |
|---|---:|---:|---:|---:|---:|---:|---:|
| Terra | 15/15 | 1,168,128 | 250,075 | 20,005 | 1,360.8 | 60 | 15 |
| Luna | 15/15 | 1,605,091 | 303,315 | 32,528 | 1,825.9 | 105 | 16 |
| Sol | 15/15 | 1,443,268 | 395,242 | 28,122 | 2,161.5 | 88 | 19 |

Relative to Terra, Luna used 37.4% more total tokens, 21.3% more uncached input, 34.2% more time, and 75.0% more tools. Sol used 23.6% more total tokens, 58.0% more uncached input, 58.8% more time, and 46.7% more tools. No measured quality gain accompanied the extra work.

## Goldilocks across models

| Model | Quality | Total tokens | Uncached input | Cumulative seconds | Tools | Skill activity |
|---|---:|---:|---:|---:|---:|---:|
| Terra | 3/3 | 265,597 | 56,581 | 305.8 | 17 | 3 |
| Luna | 3/3 | 499,210 | 80,402 | 415.3 | 32 | 3 |
| Sol | 3/3 | 342,776 | 98,702 | 468.5 | 22 | 3 |

Goldilocks selected exactly the same workflow depth on every model: zero Skills for Baby, debugging plus TDD for Mama, and brainstorming for Papa. The model changed execution behavior after routing, not the route itself.

Compared with Terra, Luna used 88.0% more total tokens, 42.1% more uncached input, 35.8% more time, and 88.2% more tools. Sol used 29.1% more total tokens, 74.4% more uncached input, 53.2% more time, and 29.4% more tools.

Task-level Goldilocks results:

| Task | Terra tokens / sec / tools | Luna tokens / sec / tools | Sol tokens / sec / tools |
|---|---:|---:|---:|
| Baby | 60,557 / 90.7 / 3 | 43,206 / 91.3 / 2 | 60,399 / 96.2 / 3 |
| Mama | 155,395 / 126.8 / 11 | 330,316 / 185.5 / 20 | 172,787 / 191.7 / 8 |
| Papa | 49,645 / 88.4 / 3 | 125,688 / 138.5 / 10 | 109,590 / 180.7 / 11 |

Luna was lean on the trivial Baby edit but expanded heavily on Mama and Papa. Sol used fewer tools than Terra on Mama, yet much more uncached input and time; on Papa it made almost four times as many tool calls as Terra.

## Goldilocks versus Superpowers

| Model | Quality | Token delta | Uncached delta | Time delta | Tool delta | Skill-activity delta |
|---|---:|---:|---:|---:|---:|---:|
| Terra | 3/3 vs 3/3 | -38.6% | -24.6% | -15.3% | -5.6% | -66.7% |
| Luna | 3/3 vs 3/3 | -7.8% | -14.1% | -22.4% | -20.0% | -66.7% |
| Sol | 3/3 vs 3/3 | -41.4% | -10.9% | -33.4% | -24.1% | -75.0% |

Superpowers loaded nine Skill activities on Terra and Luna, then twelve on Sol. On Sol, even the Baby punctuation edit loaded systematic debugging and TDD in addition to bootstrap and verification; the Mama fix also loaded brainstorming. Goldilocks remained at three total Skill activities across all three models.

## Interpretation

For this suite and provider, Terra high was the best high-reasoning balance: lowest whole-matrix tokens, uncached input, elapsed time, and tool count while matching Luna and Sol at 15/15 quality.

The Baseline differences were comparatively small: Luna used 11.1% more total tokens and 1.7% more time than Terra; Sol used 9.0% more tokens and 22.6% more time. Workflow-guided arms widened the gaps substantially. This indicates a model-workflow interaction rather than a simple fixed model-speed multiplier.

The evidence supports capability-sensitive workflow selection:

1. Keep workflow routing stable and minimal; Goldilocks did this across all models.
2. Do not assume a stronger or lighter model automatically needs more process.
3. Treat model choice and workflow choice as separate controls. Terra high performed best here, while Terra low remained the best result in the separate reasoning sweep.
4. Avoid universal bootstrap rules: more literal Skill compliance can increase work without improving the delivered result.

## Limits

- Each model/task/arm cell is `n=1`; cache distribution and gateway scheduling can dominate individual cells.
- The suite is deliberately small and does not test domains where Sol's deeper reasoning or Luna's usage profile may pay off.
- Cumulative seconds measure total cell wall time, not end-to-end matrix latency under three-way concurrency.
- Results apply to this custom gateway and Codex build; they should not be generalized to every provider or account surface.
