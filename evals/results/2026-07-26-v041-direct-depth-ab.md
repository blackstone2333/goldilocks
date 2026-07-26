# v0.4.1 Direct-depth A/B — 2026-07-26

## Verdict

Across clear single-agent coding fixtures at simple, moderate, and complex depth, the current one-Skill Goldilocks build preserved external acceptance and improved the median elapsed time, official GPT-5.6 Sol Standard API cost, and total processing tokens in every scenario.

Across all eleven measured runs per arm, Goldilocks used 10.9% less elapsed time, 6.3% less official token cost, 11.5% fewer total processing tokens, 28.4% fewer shell commands, and 46.9% fewer visible response words. Both arms passed 114/114 external checks.

This certifies the Direct branch plus the 26-word communication contract on these fixtures. It does not certify ambiguous discovery, unknown-cause debugging, long-task continuity, or multi-agent delegation.

## Official cost method

The calculation uses the [OpenAI GPT-5.6 Sol Standard API price](https://developers.openai.com/api/docs/pricing), per one million tokens:

- uncached input: $5.00;
- cached input: $0.50;
- cache write: $6.25;
- output: $30.00.

`cost = (uncached_input × 5 + cached_input × 0.5 + cache_write × 6.25 + output × 30) / 1,000,000`

All measured events reported zero cache-write tokens. The equivalent [official ChatGPT credit card](https://learn.chatgpt.com/docs/pricing#what-are-tokens-and-credits) is 125 input, 12.5 cached input, and 750 output credits per one million tokens, so it has the same relative deltas.

## Controlled setup

- Model: `gpt-5.6-sol`, high reasoning.
- Agents disabled in both arms so every model token remained measurable in the parent event stream.
- Same neutral task prompt, fresh Git fixture, repository scope, tools, and external acceptance per scenario.
- Direct and Goldilocks started simultaneously in each wave.
- One warm-up per arm and scenario was excluded.
- Three measured runs for simple and complex; moderate was extended from three to a pre-fixed five after its first three cost samples disagreed between median and cumulative results.
- Hidden acceptance tests were outside the model workspace and ran only after the model returned.

## Fixtures

- **Simple:** one `clamp` implementation, one README sentence, three checks.
- **Moderate:** a TTL-aware LRU cache with expiry, replacement, recency, eviction, and boundary semantics; four public plus eight hidden checks per run.
- **Complex:** a multi-file persistent dependency job queue with versioned atomic JSON, leases, retries, failure propagation, immutable snapshots, and recovery; four public plus eleven hidden checks per run.

## Median results

| Scenario | Runs / arm | Acceptance / arm | Direct time | Gold time | Time | Direct cost | Gold cost | Cost | Processing tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Simple | 3 | 9/9 | 68.291 s | 66.510 s | **−2.6%** | $0.194540 | $0.147344 | **−24.3%** | **−13.8%** |
| Moderate | 5 | 60/60 | 200.959 s | 140.454 s | **−30.1%** | $0.434383 | $0.375291 | **−13.6%** | **−20.4%** |
| Complex | 3 | 45/45 | 637.670 s | 610.982 s | **−4.2%** | $1.182287 | $1.124906 | **−4.9%** | **−14.5%** |

## Aggregate measured total

| Metric | Bare Direct | Goldilocks | Change |
|---|---:|---:|---:|
| External checks | 114/114 | 114/114 | Equal |
| Elapsed time | 3,179.888 s | 2,834.277 s | **−10.9%** |
| Official Standard API cost | $6.227343 | $5.833429 | **−6.3%** |
| Equivalent ChatGPT credits | 155.684 | 145.836 | **−6.3%** |
| Total processing tokens | 3,133,099 | 2,773,485 | **−11.5%** |
| Uncached input tokens | 421,555 | 406,937 | **−3.5%** |
| Cached input tokens | 2,617,856 | 2,277,888 | **−13.0%** |
| Output tokens | 93,688 | 88,660 | **−5.4%** |
| Reasoning-output tokens | 44,276 | 41,773 | **−5.7%** |
| Shell commands | 88 | 63 | **−28.4%** |
| Visible response words | 2,223 | 1,181 | **−46.9%** |

## Variance and negative evidence

- Simple Goldilocks output and reasoning-output medians were higher even though official cost fell; fewer turns reduced the larger input component.
- The first three moderate runs had a lower Goldilocks cumulative cost but a higher Goldilocks cost median. Two pre-fixed additional waves resolved the five-run median to −13.6% and the mean to −14.7%.
- Complex results were volatile: Goldilocks won two paired waves and lost one. Its median cost improved 4.9%, but its mean cost improved only 0.5%. This is a narrow advantage, not evidence of deterministic per-run savings.
- Goldilocks made two failed shell attempts across all eleven runs versus none for Direct, then repaired them before final acceptance.
- No Goldilocks workflow file was read in any scored run. The fixtures had settled end states, no unknown root cause, no continuity requirement, and agents disabled, so the correct path was Direct. The measured effect is therefore the prompt-level communication contract, not hidden workflow ceremony.

During complex warm-up, both implementations failed one hidden assertion because the test required `TypeError` for a non-JSON payload while the specification did not define the exception type. Before measured runs, the assertion was corrected to accept `TypeError` or `ValueError` and revalidated against the oracle plus both warm-up implementations. No measured result was removed or rerun.

## Data

The cleaned per-run metrics, summaries, price card, and aggregate are in [the machine-readable result](data/2026-07-26-v041-direct-depth-ab.json).
