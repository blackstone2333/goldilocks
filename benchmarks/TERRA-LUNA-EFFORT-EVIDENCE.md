# Terra/Luna effort evidence

[简体中文](TERRA-LUNA-EFFORT-EVIDENCE.zh-CN.md)

This is the sanitized public record behind Goldilocks' Standard and Night Shift defaults. Four sole-owner arms ran the same frozen complex coding task, seed repository, hidden grader, host harness, and telemetry contract. Every arm passed visible tests, all 11 hidden checks, compilation, diff, scope, and exact model/effort identity.

| Arm | Quality | Observational time | Raw Token | Official-price proxy |
|---|---:|---:|---:|---:|
| Terra Medium | pass | 249.043 s | 241,689 | $0.212937 |
| Terra XHigh | pass | 560.981 s | 525,706 | $0.523867 |
| Terra Max | pass | 695.082 s | 428,766 | $0.602954 |
| Luna Max | pass | 1,275.764 s | 1,449,579 | $0.122976 |

On this task, Luna Max took about **5.12×** Terra Medium's observed wall time while its official-price proxy was **42.25% lower**. Luna used about 6× the Raw Tokens. Night Shift is therefore a latency-for-price choice, not a claim of higher token efficiency.

Timing is observational because the arms shared a provider. The dollar figures apply the public standard token rates used by the frozen harness and are comparison estimates, not actual bills. This one task does not establish a universal model ranking.

The same protocol separately tested Spark as an unpriced capability reference. Spark Medium failed one hidden persistence invariant; the predeclared Spark XHigh follow-up passed all 11 hidden checks in 137.458 s with 600,737 Raw Tokens. Spark has no public numeric rate, so its USD value remains `N/A`, never zero.

## Provenance

- Frozen four-arm manifest SHA-256: `ecaef6cd769e0cf59bcb7a7d4844d9714ce8891e17ebd815c1594a106d98d2cc`
- Host harness SHA-256: `efa343fcc4293046f363b3e132c99f60aae444f0bf598af1b771ffb1a755e41f`
- Closed four-arm result SHA-256: `0eb3485150b1106c3e272f10098196fa3e65785e2bdf96af9792c8e7cee17dc0`
- Spark reference summary SHA-256: `fd021ceb8cdcaff05c7ab1cb13c9c0d399eed60014eb15d291320036b2766e15`

Raw evaluation workspaces, credentials, caches, and local session state are intentionally excluded from the public repository.
