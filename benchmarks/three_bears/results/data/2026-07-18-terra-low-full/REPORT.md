# Three Bears Benchmark Report

Run: `20260718-033829`
Model: `gpt-5.6-terra`
Reasoning: `low`

Quality gates must be read before efficiency. Fewer tokens or lines do not count as a win when quality, safety, scope, reuse, or decision process drops.

## Baby

| Arm | Valid / attempted | Infra failures | Quality | Safe | Scope | Reuse | Process | Median tokens | Median uncached input | Median cached input | Median seconds | Median source +LOC | Median test +LOC | Median tools | Median skills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 66077 | 11267 | 46592 | 93.2 | 4 | 0 | 4 | 0 |
| goldilocks | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 73925 | 12943 | 57344 | 119.5 | 4 | 0 | 4 | 0 |
| superpowers | 9 / 9 | 0 | 0.333 | 1.000 | 1.000 | 0.333 | 1.000 | 65891 | 12351 | 51200 | 88.3 | 0 | 0 | 3 | 3 |
| ponytail | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 76183 | 7540 | 62976 | 107.7 | 4 | 0 | 4 | 1 |
| grill | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 66866 | 8643 | 47616 | 103.5 | 4 | 0 | 4 | 0 |

## Mama

| Arm | Valid / attempted | Infra failures | Quality | Safe | Scope | Reuse | Process | Median tokens | Median uncached input | Median cached input | Median seconds | Median source +LOC | Median test +LOC | Median tools | Median skills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 0.778 | 1.000 | 68092 | 9027 | 56320 | 101.9 | 5 | 0 | 4 | 0 |
| goldilocks | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 0.778 | 1.000 | 123989 | 14167 | 107520 | 125.5 | 5 | 21 | 6 | 2 |
| superpowers | 9 / 9 | 0 | 0.222 | 1.000 | 1.000 | 0.667 | 1.000 | 88367 | 20538 | 57344 | 106.7 | 0 | 0 | 4 | 4 |
| ponytail | 9 / 9 | 0 | 0.889 | 1.000 | 1.000 | 0.889 | 1.000 | 77573 | 12290 | 64512 | 113.4 | 3 | 0 | 4 | 1 |
| grill | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 0.778 | 1.000 | 68636 | 8589 | 58880 | 105.5 | 5 | 0 | 4 | 0 |

## Papa

| Arm | Valid / attempted | Infra failures | Quality | Safe | Scope | Reuse | Process | Median tokens | Median uncached input | Median cached input | Median seconds | Median source +LOC | Median test +LOC | Median tools | Median skills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 67807 | 11796 | 54272 | 109.7 | 3 | 0 | 4 | 0 |
| goldilocks | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 131691 | 18061 | 110592 | 156.9 | 1 | 31 | 6 | 1 |
| superpowers | 9 / 9 | 0 | 0.333 | 0.667 | 1.000 | 1.000 | 1.000 | 71571 | 19585 | 55808 | 101.2 | 0 | 0 | 3 | 3 |
| ponytail | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 64844 | 7951 | 56320 | 81.2 | 1 | 0 | 3 | 1 |
| grill | 9 / 9 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 69423 | 7004 | 45056 | 94.3 | 1 | 0 | 4 | 0 |

## All

| Arm | Valid / attempted | Infra failures | Quality | Safe | Scope | Reuse | Process | Median tokens | Median uncached input | Median cached input | Median seconds | Median source +LOC | Median test +LOC | Median tools | Median skills |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 27 / 27 | 0 | 1.000 | 1.000 | 1.000 | 0.926 | 1.000 | 67266 | 10240 | 49664 | 96.0 | 4 | 0 | 4 | 0 |
| goldilocks | 27 / 27 | 0 | 1.000 | 1.000 | 1.000 | 0.926 | 1.000 | 111886 | 14649 | 96768 | 133.7 | 4 | 19 | 6 | 1 |
| superpowers | 27 / 27 | 0 | 0.296 | 0.889 | 1.000 | 0.667 | 1.000 | 70594 | 13606 | 56320 | 100.7 | 0 | 0 | 3 | 3 |
| ponytail | 27 / 27 | 0 | 0.963 | 1.000 | 1.000 | 0.963 | 1.000 | 76671 | 10247 | 63488 | 107.7 | 3 | 0 | 4 | 1 |
| grill | 27 / 27 | 0 | 1.000 | 1.000 | 1.000 | 0.926 | 1.000 | 68009 | 8589 | 57344 | 102.6 | 4 | 0 | 4 | 0 |
