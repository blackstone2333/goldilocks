# Three Bears — Goldilocks v0.2.2 versus Superpowers certification

This report certifies one product claim: Goldilocks is a better Superpowers replacement on the tested workflow surface. It is not a universal model or workflow ranking and not a `1.0` release gate.

## Setup

- Date: 2026-07-18
- Model: `gpt-5.6-terra`
- Reasoning: `low`
- Provider: isolated OpenAI-compatible custom Responses provider; endpoint and credentials omitted
- Tasks: all 9 Three Bears tasks
- Compared workflows: Goldilocks and Superpowers
- Runs: 3 per task/workflow cell
- Workers: 3
- Timeout: 1,200 seconds per cell
- Seed: `1729`
- Published head-to-head turns: 54/54
- Source exploratory experiment: 135/135 valid turns
- Infrastructure failures: 0
- Published comparison telemetry: 5,346,349 total tokens, 950,832 uncached input
- Goldilocks: `386cb4b`
- Superpowers: `d884ae04`

Each cell ran in a freshly generated git repository with isolated Skill sources and a reduced provider-only Codex configuration. The deterministic graders were validated against good and bad references before model calls, then rerun offline after the matrix completed. The retained artifacts contain the complete exploratory experiment; all product conclusions and tables below use only the 54 Goldilocks/Superpowers turns.

## Result

Quality gates are read before efficiency. A cell that stops early, asks an unnecessary approval question, or fails to change the requested code is not an efficiency win.

| Arm | Quality | Safety | Scope | Successful turns | Total tokens | Uncached input | Cumulative seconds | Tools | Skill activity |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Goldilocks** | **27/27** | **100%** | **100%** | **27** | 3,031,688 | 474,546 | 3,866.3 | 161 | 30 |
| Superpowers | 8/27 | 88.9% | 100% | 8 | 2,314,661 | 476,286 | 2,890.3 | 107 | 87 |

Goldilocks passed every Baby, Mama, and Papa cell. It preserved the Direct path on all three trivial documentation samples, reused existing helpers and standard-library mechanisms, repaired shared causes, stopped at material design decisions, and maintained the path-traversal and immediate-revocation safety boundaries.

![Goldilocks versus Superpowers real agentic certification](../../assets/agentic-certification-head-to-head.svg)

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

Counting failed attempts and dividing all cost by successful deliveries:

| Metric per successful delivery | Goldilocks | Superpowers | Goldilocks delta |
|---|---:|---:|---:|
| Total tokens | **112,285** | 289,333 | **−61.2%** |
| Uncached input | **17,576** | 59,536 | **−70.5%** |
| Seconds | **143.2** | 361.3 | **−60.4%** |
| Tool calls | **6.0** | 13.4 | **−55.4%** |
| Skill activity | **1.1** | 10.9 | **−89.8%** |

## Scope of claim

This report ranks Goldilocks only against Superpowers. It does not claim universal superiority over workflow-free execution, unrelated workflow systems, other models, or real production repositories. The harness retains additional exploratory arms so readers can run broader comparisons themselves; those arms are not part of the Goldilocks product claim.

One limitation remains visible in the direct comparison: on the eight exact cells both workflows successfully completed, Goldilocks used 9.7% more uncached input. It still used fewer total tokens, less time, fewer tools, and less Skill activity on that slice. Future `v0.2.x` work should preserve the 27/27 quality floor while reducing uncached context and proof overhead further.

## Certification conclusion

For this nine-task suite, model, provider, and Codex build:

1. Goldilocks preserved full measured quality and safety across all 27 cells.
2. Goldilocks was substantially more reliable than Superpowers and used less workflow activity on comparable successes.
3. Goldilocks can serve as the Superpowers replacement target for this tested surface.
4. The run does not prove universal superiority beyond this specific replacement claim, model, provider, task suite, and benchmark revision.
5. `v0.2.2` should remain the current version while overhead reduction and broader external validation continue.

## Published artifacts

- [Goldilocks/Superpowers head-to-head data](data/2026-07-18-terra-low-full/head-to-head.json)
- [Run metadata](data/2026-07-18-terra-low-full/metadata.json)
- [Complete per-cell audit results](data/2026-07-18-terra-low-full/results.json)

The artifacts retain the full 135-turn exploratory experiment for audit. Filter `arm` to `goldilocks` and `superpowers` to reproduce the 54-turn published comparison. The full local run also retains cell workspaces, raw event streams, and stderr; generated workspaces are intentionally excluded from git.
