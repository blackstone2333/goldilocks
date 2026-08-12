# Goldilocks v0.5.1 Release Evidence

[简体中文](V051-RELEASE-EVIDENCE.zh-CN.md)

## Result

This single frozen Direct comparison is valid: both the published v0.5.0 arm and the v0.5.1 candidate passed the same quality and infrastructure gates with one attempt, zero retries, and zero infrastructure failures. The result is a Pareto tradeoff, not a dominant win.

| Arm | Quality | Wall time | Input tokens | Cached input | Output tokens | Raw tokens | Official cost | Tool calls | Route |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| Published v0.5.0 | PASS; visible 5/5, hidden 8/8 | 219.150 s | 197,660 | 164,608 | 9,285 | 206,945 | $0.526114 | 9 | Direct |
| v0.5.1 candidate | PASS; visible 7/7, hidden 8/8 | 195.049 s | 281,242 | 230,656 | 8,020 | 289,262 | $0.608858 | 12 | Direct |

The candidate added two focused visible tests. Neither arm used a child agent. Spark did not participate.

## Comparison

Candidate minus published v0.5.0:

| Axis | Delta | Reading |
|---|---:|---|
| Wall time | -24.101 s (-10.997%) | improvement |
| Input tokens | +83,582 (+42.286%) | regression |
| Cached input tokens | +66,048 (+40.124%) | regression |
| Uncached input tokens | +17,534 (+53.050%) | regression |
| Output tokens | -1,265 (-13.624%) | improvement |
| Raw tokens | +82,317 (+39.777%) | regression |
| Official cost | +$0.082744 (+15.727%) | regression |
| Tool calls | +3 (+33.333%) | regression |

v0.5.1 is faster and emits fewer output tokens. Published v0.5.0 uses fewer tokens, costs less at official rates, and uses fewer tool calls. No candidate regression falls within the predefined 5% practical-parity band; therefore this sample does not select a forced winner.

## Cost boundary and limits

Only Sol participated, so the official cost is fully defined and the normalized comparison cost equals official cost in this sample. Spark did not participate. Where Spark is present in other comparisons, it has no official numeric USD price: its official USD value is N/A, never zero. Any normalized comparison proxy that values Spark tokens at frozen Luna rates is an analytical estimate, not a bill.

This is one frozen Direct sample on one deterministic artifact-manifest task. It does not establish performance for other task mixes, samples, hosts, models, providers, repositories, or routes.

## Public data

The sanitized machine-readable summary is [v051-final-candidate-comparison.json](data/v051-final-candidate-comparison.json). It intentionally excludes local paths, credentials, session data, and execution internals.
