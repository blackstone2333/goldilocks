# Goldilocks v0.5.0 Release Evidence

[简体中文](V050-RELEASE-EVIDENCE.zh-CN.md)

## Frozen release matrix

The v0.5.0 release matrix ran the same three frozen tasks—compact control, document handoff, and parallel units—against Direct, Superpowers 6.1.1, Goldilocks 0.4.2, and Goldilocks 0.5.0. Quality is the first gate.

| Arm | Aligned quality | Time | Raw Token | Authorization-normalized cost |
|---|---:|---:|---:|---:|
| Goldilocks 0.5.0 | 3/3 | 1,223.291 s | 1,593,503 | $2.949584 |
| Direct | 3/3 | 894.252 s | 1,629,009 | $3.416688 |
| Goldilocks 0.4.2 | 3/3 | 1,399.565 s | 3,367,113 | $4.427797 |
| Superpowers 6.1.1 assisted | 3/3 | 7,402.714 s | 29,059,764 | $25.360443 |

The table uses 0.5.0 as its baseline: first the three aggregates, then each task comparison. `Δ = (0.5.0 − control) / control`; a negative value means 0.5.0 is lower.

| Task | Control | Quality (0.5 / control) | Time (0.5 / control; Δ) | Raw Token (0.5 / control; Δ) | Authorization-normalized cost (0.5 / control; Δ) |
|---|---|---:|---:|---:|---:|
| **Aggregate (three tasks)** | **Direct** | **3/3 / 3/3** | 1,223.291 / 894.252 s; **+36.79%** | 1,593,503 / 1,629,009; **−2.18%** | $2.949584 / $3.416688; **−13.67%** |
| **Aggregate (three tasks)** | **Goldilocks 0.4.2** | **3/3 / 3/3** | 1,223.291 / 1,399.565 s; **−12.59%** | 1,593,503 / 3,367,113; **−52.67%** | $2.949584 / $4.427797; **−33.38%** |
| **Aggregate (three tasks)** | **Superpowers 6.1.1** | **3/3 / 3/3*** | 1,223.291 / 7,402.714 s; **−83.48%** | 1,593,503 / 29,059,764; **−94.52%** | $2.949584 / $25.360443; **−88.37%** |
| Compact control | Direct | Pass / Pass | 146.947 / 137.376 s; **+6.97%** | 132,621 / 114,351; **+15.98%** | $0.422859 / $0.309312; **+36.71%** |
| Compact control | Goldilocks 0.4.2 | Pass / Pass | 146.947 / 233.905 s; **−37.18%** | 132,621 / 332,205; **−60.08%** | $0.422859 / $0.630806; **−32.97%** |
| Compact control | Superpowers 6.1.1 | Pass / Pass* | 146.947 / 2,448.273 s; **−94.00%** | 132,621 / 10,080,790; **−98.68%** | $0.422859 / $8.214185; **−94.85%** |
| Document handoff | Direct | Pass / Pass | 752.209 / 500.055 s; **+50.43%** | 944,632 / 460,093; **+105.31%** | $1.851148 / $1.148769; **+61.14%** |
| Document handoff | Goldilocks 0.4.2 | Pass / Pass | 752.209 / 822.632 s; **−8.56%** | 944,632 / 1,383,659; **−31.73%** | $1.851148 / $2.106448; **−12.12%** |
| Document handoff | Superpowers 6.1.1 | Pass / Pass* | 752.209 / 3,601.023 s; **−79.11%** | 944,632 / 12,843,017; **−92.64%** | $1.851148 / $11.966323; **−84.53%** |
| Parallel units | Direct | Pass / Pass | 324.135 / 256.821 s; **+26.21%** | 516,250 / 1,054,565; **−51.05%** | $0.675578 / $1.958607; **−65.51%** |
| Parallel units | Goldilocks 0.4.2 | Pass / Pass | 324.135 / 343.028 s; **−5.51%** | 516,250 / 1,651,249; **−68.74%** | $0.675578 / $1.690543; **−60.04%** |
| Parallel units | Superpowers 6.1.1 | Pass / Pass* | 324.135 / 1,353.418 s; **−76.05%** | 516,250 / 6,135,957; **−91.59%** | $0.675578 / $5.179935; **−86.96%** |

All three aggregates passed the 3/3 quality gate. 0.5.0's aggregate time is **36.79% higher (slower)** than Direct; its Raw Token and authorization-normalized cost are **2.18%** and **13.67%** lower. Against 0.4.2, time, Raw Token, and cost are lower by **12.59%**, **52.67%**, and **33.38%**; against Superpowers, by **83.48%**, **94.52%**, and **88.37%**.

## How the acceptance floor was aligned

The frozen raw harness initially reported three Superpowers cells as incomplete even though each repository had completed the implementation and passed behavior, hidden acceptance, compilation, product diff, and corrected scope checks. An offline, zero-model correction repaired two fixed harness rules: semantic completion recognition and the Superpowers-owned scope allowlist. The corrected classification gives Superpowers 3/3; table cells marked `*` use that correction. Its original time and raw-Token telemetry is unchanged.

Goldilocks 0.4.2's document-handoff result was also classified by semantic meaning rather than a required literal word. No model cell was rerun to obtain those classifications.

## Cost boundary

Spark has no public numeric price. The authorization-normalized cost in this report is the official known-model subtotal plus a user-authorized Luna-equivalent proxy for Spark usage. It is a comparison estimate, not an actual bill, and it keeps the Spark allowance distinct from publicly priced model usage.

These results describe only this frozen three-task matrix. They do not establish a result for other task mixes, hosts, providers, or repositories.

## Provenance

- Sanitized machine-readable result: [`benchmarks/data/v050-release-matrix.json`](data/v050-release-matrix.json)
- Frozen corrected manifest SHA-256: `4aa73e315c1d5b576c5ca5f49dba858d728d3eb5362157c918c80849a4bde415`
- Corrected source result SHA-256: `fb32db2799efe4c7759cadd3a7e338c00ce23bf49dc59968efc098da8c19d93c`
- Reusable method notes: [`docs/benchmarking-lessons.md`](../docs/benchmarking-lessons.md)

Raw evaluation workspaces, credentials, caches, local paths, and session state are intentionally excluded from the public repository.
