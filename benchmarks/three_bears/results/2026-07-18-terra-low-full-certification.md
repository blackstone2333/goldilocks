# Three Bears — Goldilocks v0.2.2 full workflow certification

This run is the first complete three-repetition matrix for Goldilocks. It is evidence for the `v0.2.2` workflow design, not a universal model or workflow ranking and not a `1.0` release gate.

## Setup

- Date: 2026-07-18
- Model: `gpt-5.6-terra`
- Reasoning: `low`
- Provider: isolated OpenAI-compatible custom Responses provider; endpoint and credentials omitted
- Tasks: all 9 Three Bears tasks
- Arms: Baseline, Goldilocks, Superpowers, Ponytail, Grill
- Runs: 3 per task/arm cell
- Workers: 3
- Timeout: 1,200 seconds per cell
- Seed: `1729`
- Valid turns: 135/135
- Infrastructure failures: 0
- Telemetry tokens: 10,645,012 total, 1,845,125 uncached input, 181,903 output
- Goldilocks: `386cb4b`
- Superpowers: `d884ae04`
- Ponytail: `16f29800`
- Matt Pocock Skills / Grill: `9603c1cc`

Each cell ran in a freshly generated git repository with isolated Skill sources and a reduced provider-only Codex configuration. The deterministic graders were validated against good and bad references before model calls, then rerun offline after the matrix completed.

## Result

Quality gates are read before efficiency. A cell that stops early, asks an unnecessary approval question, or fails to change the requested code is not an efficiency win.

| Arm | Quality | Safety | Scope | Successful turns | Total tokens | Uncached input | Cumulative seconds | Tools | Skill activity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Goldilocks** | **27/27** | **100%** | **100%** | **27** | 3,031,688 | 474,546 | 3,866.3 | 161 | 30 |
| Baseline | 27/27 | 100% | 100% | 27 | 1,629,610 | 326,595 | 2,865.2 | 94 | 0 |
| Grill | 27/27 | 100% | 100% | 27 | 1,653,856 | 262,677 | 2,724.5 | 94 | 3 |
| Ponytail | 26/27 | 100% | 100% | 26 | 2,015,197 | 305,021 | 2,865.9 | 103 | 27 |
| Superpowers | 8/27 | 88.9% | 100% | 8 | 2,314,661 | 476,286 | 2,890.3 | 107 | 87 |

Goldilocks passed every Baby, Mama, and Papa cell. It preserved the Direct path on all three trivial documentation samples, reused existing helpers and standard-library mechanisms, repaired shared causes, stopped at material design decisions, and maintained the path-traversal and immediate-revocation safety boundaries.

## Goldilocks versus Superpowers

Superpowers passed 8 of 27 cells. Nineteen failures ended before a source change. The repeated pattern was an approval or clarification question for behavior already constrained by the task and repository:

- `baby-uuid`: 0/3, asking which UUID form or requesting approval for UUID v4;
- `baby-reuse`: 0/3, asking about an irrelevant empty-input edge case or requesting design approval;
- `mama-csv-headers`: 0/3, asking about case sensitivity, message wording, or design approval;
- `mama-cache`: 0/3, asking what the existing `calls()` contract should mean;
- `papa-safe-path`: 0/3, asking whether unsafe paths should raise or sanitize;
- `papa-revocation`: 0/3, requesting approval after identifying the stale cache;
- `mama-empty-query`: 2/3, with one approval question and two unusually expensive successes;
- `baby-docs` and `papa-offline-design`: 3/3 each.

Raw Superpowers totals are therefore not comparable as successful delivery cost. Two additional views are useful:

### Same successful cells

On the eight exact task/run cells both arms completed:

| Metric | Goldilocks | Superpowers | Goldilocks delta |
|---|---:|---:|---:|
| Total tokens | 617,818 | 890,007 | -30.6% |
| Uncached input | 139,058 | 126,782 | +9.7% |
| Cumulative seconds | 819.9 | 888.0 | -7.7% |
| Tool calls | 30 | 42 | -28.6% |
| Skill activity | 7 | 21 | -66.7% |

### Quality-adjusted across all attempts

Counting the cost of failed attempts and dividing by successful deliveries, Goldilocks used 61.2% fewer total tokens, 70.5% less uncached input, 60.4% less time, 55.2% fewer tool calls, and 89.9% less Skill activity per successful cell than Superpowers.

## The uncomfortable result

Goldilocks was not the lowest-cost arm. Relative to Baseline across the full matrix, it used 86.0% more cumulative total tokens, 45.3% more uncached input, 34.9% more time, and 71.3% more tool calls. Relative to Ponytail, Goldilocks delivered one additional passing cell but also used materially more work.

The main source is visible in the median behavior: Goldilocks added tests on Mama and Papa tasks and used six median tool calls, while the no-workflow arms often solved the seeded repositories directly. This is the clearest optimization target for a future `v0.2.x`: retain the 27/27 quality floor while reducing test and proof expansion when deterministic acceptance can be established more cheaply.

## Certification conclusion

For this nine-task suite, model, provider, and Codex build:

1. Goldilocks preserved full measured quality and safety across all 27 cells.
2. Goldilocks was substantially more reliable than Superpowers and used less workflow activity on comparable successes.
3. Goldilocks can serve as the Superpowers replacement target for this tested surface.
4. The run does not prove universal superiority over Baseline, Ponytail, Grill, other models, or real production repositories.
5. `v0.2.2` should remain the current version while overhead reduction and broader external validation continue.

## Published artifacts

- [Generated report](data/2026-07-18-terra-low-full/REPORT.md)
- [Run metadata](data/2026-07-18-terra-low-full/metadata.json)
- [Per-cell results](data/2026-07-18-terra-low-full/results.json)
- [Aggregated summary](data/2026-07-18-terra-low-full/summary.json)

The full local run also retains cell workspaces, raw event streams, and stderr for audit. Those generated workspaces are intentionally excluded from git; the published data above contains every scored cell, final response, telemetry measurement, changed-file summary, and grader result.
