# Goldilocks versus Superpowers

[English](GOLDILOCKS-VS-SUPERPOWERS.md) · [简体中文](GOLDILOCKS-VS-SUPERPOWERS.zh-CN.md)

Goldilocks makes one public product claim: it is a more reliable and more efficient **Superpowers replacement** on the tested workflow surface. It does not claim to be universally superior to every possible workflow or to using no workflow at all.

Two evaluations support that claim. They answer different questions and must not be blended into one score.

## Test 1 — instruction-level stress test

This was the original five-arm design evaluation, filtered here to the requested Goldilocks/Superpowers head-to-head. Goldilocks was still named `just-necessary`; the result supports the architecture that became Goldilocks, not release runtime performance.

![Instruction-level head-to-head: Goldilocks predecessor versus Superpowers](assets/instruction-stress-head-to-head.svg)

Eight scenarios covered a trivial edit, a clear feature, a shared-root bug, ambiguous SSO, native reuse, parallel work, idea capture, and a destructive production action. Each workflow ran in an isolated instruction context and was scored with the bundled rubric. This was a behavioral rule-set stress test, not a real repository execution benchmark.

| Metric | Goldilocks predecessor | Superpowers 6.1.1 | Result |
|---|---:|---:|---:|
| Average scenario score | **98.9/100** | 79.2/100 | Goldilocks +19.7 points |
| Scenario wins/ties/losses | **8 / 0 / 0** | 0 / 0 / 8 | Goldilocks led all 8 |
| Rule text | **2,552 words** | 18,516 words | Goldilocks 86.2% smaller |

The full scenario scores used in the chart were:

The original report published scenario rows as whole points while preserving full-precision rubric averages. Recomputing an average from the rounded rows can therefore differ by 0.1.

| Scenario | Goldilocks predecessor | Superpowers |
|---|---:|---:|
| One-word documentation fix | **100** | 89 |
| Clear two-file feature | **99** | 79 |
| Shared-root bug | **99** | 89 |
| Ambiguous enterprise SSO | **96** | 77 |
| Native component opportunity | **100** | 79 |
| Three independent workstreams | **99** | 79 |
| Mid-flight non-essential idea | **100** | 82 |
| Destructive production action and external message | **99** | 60 |

## Test 2 — real agentic workflow certification

This is the published `v0.2.2` runtime evidence: GPT-5.6 Terra at low reasoning, nine Baby/Mama/Papa tasks, three fresh isolated repositories per task, and 27 attempts for each workflow. The published head-to-head slice contains 54 valid model turns with zero infrastructure failures.

![Real agentic head-to-head: Goldilocks versus Superpowers](assets/agentic-certification-head-to-head.svg)

### Delivery result

| Workflow | Successful delivery | Safety | Total attempts |
|---|---:|---:|---:|
| **Goldilocks** | **27/27 (100%)** | **100%** | 27 |
| Superpowers | 8/27 (29.6%) | 88.9% | 27 |

Superpowers stopped before changing source code in 19 attempts, usually to request approval or clarification for behavior already constrained by the task and repository. Those early stops make its raw totals look cheaper without producing a delivery.

### Like-for-like efficiency

On the eight exact task/run cells both workflows completed successfully:

| Metric | Goldilocks | Superpowers | Goldilocks delta |
|---|---:|---:|---:|
| Total tokens | **617,818** | 890,007 | **−30.6%** |
| Uncached input | 139,058 | **126,782** | +9.7% |
| Cumulative seconds | **819.9** | 888.0 | **−7.7%** |
| Tool calls | **30** | 42 | **−28.6%** |
| Skill activity | **7** | 21 | **−66.7%** |

Goldilocks led four of five comparable efficiency measures. Superpowers used 9.7% less uncached input on this eight-cell slice; that exception is shown explicitly rather than hidden inside total-token figures.

### Cost per successful delivery

Charging every attempt—including failures—and dividing by successful deliveries:

| Metric per successful delivery | Goldilocks | Superpowers | Goldilocks delta |
|---|---:|---:|---:|
| Total tokens | **112,285** | 289,333 | **−61.2%** |
| Uncached input | **17,576** | 59,536 | **−70.5%** |
| Seconds | **143.2** | 361.3 | **−60.4%** |
| Tool calls | **6.0** | 13.4 | **−55.4%** |
| Skill activity | **1.1** | 10.9 | **−89.8%** |

## What the two tests prove

- The instruction design covered the tested workflow and safety scenarios with much less rule text than Superpowers.
- The current plugin delivered every tested task while Superpowers delivered fewer than one third.
- On identical successful cells, Goldilocks was leaner on total tokens, time, tools, and Skill activity.
- After failed attempts are charged to delivery, Goldilocks was cheaper on every measured cost dimension.

The defensible conclusion is narrow: **Goldilocks is the better Superpowers replacement on these tested scenarios, tasks, model, provider, and benchmark revision.** Broader comparisons remain available through the harness for readers to run themselves.

## Sources

- [Instruction-stress chart data](data/instruction-stress-head-to-head.json)
- [Full `v0.2.2` workflow certification](three_bears/results/2026-07-18-terra-low-full-certification.md)
- [Three Bears methodology and runner](three_bears/README.md)
- [Head-to-head calculation data](three_bears/results/data/2026-07-18-terra-low-full/head-to-head.json)
- [Complete per-cell audit data](three_bears/results/data/2026-07-18-terra-low-full/results.json)
