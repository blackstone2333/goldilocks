# Three Bears — GPT-5.6 Terra reasoning sweep

This is an exploratory custom-provider run, not a universal performance claim. Quality gates are evaluated before efficiency.

## Setup

- Model: `gpt-5.6-terra`
- Provider: isolated OpenAI-compatible custom Responses provider; endpoint and credentials omitted
- Codex CLI: `0.145.0-alpha.18`
- Representative tasks: `baby-docs`, `mama-empty-query`, `papa-offline-design`
- Arms: Baseline, Goldilocks, Superpowers, Ponytail, Grill
- Reasoning: `low`, `high`, `xhigh`; one run per representative cell
- Direct regression: `baby-docs`, three runs per arm at `low`
- Goldilocks instruction-tree SHA-256: `08e32971632f6f58bc90d9a1cff0b028950f296f3c58dc038696ccd6651ce317`
- External sources: Superpowers `d884ae04`, Ponytail `16f29800`, Matt Pocock Skills `9603c1cc`

The provider-only temporary config copied no MCP servers, plugins, marketplaces, or unrelated user settings. Across the connectivity check and matrices covered by this report, 61 model turns completed using 4,075,498 telemetry tokens, including 918,466 uncached input and 67,624 output tokens.

## Direct-path regression

Goldilocks v0.2.2 prevents completion wording from implicitly loading the full proof engine. All 15 Baby cells passed.

| Arm | Quality | Median tokens | Median uncached | Median seconds | Median tools | Median Skill activity |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 3/3 | 31,636 | 11,167 | 66.5 | 1 | 0 |
| Goldilocks | 3/3 | 36,752 | 16,768 | 64.1 | 2 | 0 |
| Superpowers | 3/3 | 81,665 | 13,393 | 92.9 | 4 | 2 |
| Ponytail | 3/3 | 49,051 | 10,583 | 71.6 | 2 | 1 |
| Grill | 3/3 | 31,986 | 11,622 | 79.4 | 1 | 0 |

Against Superpowers, Goldilocks used 55.0% fewer median total tokens, finished 31.0% faster, made 50% fewer tool calls, and loaded no Skill. Its uncached input was 25.2% higher in this small sample, so cache-sensitive totals and uncached input should both remain visible.

## Representative reasoning sweep

Totals cover one Baby, one Mama, and one Papa cell per arm.

### Low

| Arm | Quality | Total tokens | Uncached input | Seconds | Tools | Skill activity |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 3/3 | 132,240 | 24,295 | 212.4 | 7 | 0 |
| Goldilocks | 3/3 | 271,238 | 27,651 | 286.1 | 15 | 3 |
| Superpowers | 3/3 | 405,873 | 72,580 | 349.2 | 20 | 8 |
| Ponytail | 3/3 | 191,209 | 32,915 | 235.2 | 10 | 3 |
| Grill | 3/3 | 135,899 | 30,219 | 196.8 | 7 | 1 |

Goldilocks versus Superpowers: 33.2% fewer total tokens, 61.9% less uncached input, 18.1% less time, 25.0% fewer tools, and 62.5% less Skill activity at the same quality.

### High

| Arm | Quality | Total tokens | Uncached input | Seconds | Tools | Skill activity |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 3/3 | 133,018 | 34,399 | 249.9 | 7 | 0 |
| Goldilocks | 3/3 | 265,597 | 56,581 | 305.8 | 17 | 3 |
| Superpowers | 3/3 | 432,478 | 75,003 | 361.1 | 18 | 9 |
| Ponytail | 3/3 | 188,941 | 43,086 | 216.4 | 10 | 2 |
| Grill | 3/3 | 148,094 | 41,006 | 227.5 | 8 | 1 |

Goldilocks versus Superpowers: 38.6% fewer total tokens, 24.6% less uncached input, 15.3% less time, 5.6% fewer tools, and 66.7% less Skill activity at the same quality.

### XHigh

| Arm | Quality | Total tokens | Uncached input | Seconds | Tools | Skill activity |
|---|---:|---:|---:|---:|---:|---:|
| Baseline | 3/3 | 146,509 | 21,955 | 211.9 | 8 | 0 |
| Goldilocks | 3/3 | 280,171 | 66,949 | 314.1 | 23 | 3 |
| Superpowers | **2/3** | 264,259 | 65,282 | 325.5 | 14 | 7 |
| Ponytail | 3/3 | 190,827 | 39,069 | 242.0 | 10 | 3 |
| Grill | 3/3 | 136,942 | 50,767 | 227.7 | 7 | 1 |

Superpowers failed the Mama task after loading `using-superpowers`, `systematic-debugging`, and `brainstorming`. It reproduced the shared `None.strip()` root cause, but the mandatory brainstorming approval gate forced it to ask whether `None` should match existing empty-string behavior instead of implementing the requested fix. It spent 132,687 tokens and made six tool calls without changing a file. Goldilocks completed the same task and preserved 3/3 quality.

Because Superpowers stopped early, its xhigh efficiency totals are not comparable as a successful result. On the two tasks both completed, Goldilocks used 24.6% fewer tokens and 21.6% less time.

## Reasoning-level conclusion

Goldilocks preserved 3/3 quality at every reasoning level. Relative to low, high used 104.6% more uncached input, took 6.9% longer, and made 13.3% more tool calls; xhigh used 142.1% more uncached input, took 9.8% longer, and made 53.3% more tool calls. Total tokens were distorted by cache distribution and moved only -2.1% and +3.3%.

For this suite, `low` is the best default. `high` and `xhigh` produced no measured quality gain, while xhigh exposed how a rigid mandatory workflow can become less reliable as the model follows its hard gates more literally. Higher reasoning remains appropriate when task-specific uncertainty or risk justifies it; it should not be a global process substitute.

## Limits

- The representative reasoning sweep is `n=1`; only the Baby Direct regression is `n=3`.
- Cache distribution varied heavily, so uncached input, elapsed time, and workflow activity matter alongside total tokens.
- A capable model solved every Baseline cell. This benchmark measures workflow overhead and failure modes, not whether a Skill is always necessary.
- The custom gateway may differ from the first ChatGPT-account round in caching, routing, or accounting. Cross-provider absolute-token comparisons are not valid.
