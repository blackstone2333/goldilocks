# Beta6 route speed versus Direct — validation

Date: 2026-08-28

## Decision

The `route_unavailable` evidence contract and minimum-sufficient verification policy are
validated. The first paired representative task showed Direct faster and cheaper, but also
isolated the remaining Goldilocks overhead to two instruction reads. The root gate was then
thinned so small multi-file work can select Direct without loading `kernel.md`; one candidate-only
confirmation proved that structural and token/cost reduction. No further sample was run.

This is one mature independent-parallel development fixture, not a general benchmark claim.
Every model attempt used `gpt-5.6-sol` at high effort, requested standard service tier, ran in an
isolated repository/HOME/CODEX_HOME, and received zero retry.

## Results

| Arm | Quality | Wall* | Input | Cached | Output | Raw | Normalized USD | Tools | Internal verification | Exact duplicates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Patched Beta6 before root thinning | PASS | 112.812 s | 132,206 | 87,808 | 3,564 | 135,770 | $0.372814 | 6 | 1 | 0 |
| Direct | PASS | 82.002 s | 73,831 | 55,296 | 2,453 | 76,284 | $0.193913 | 4 | 1 | 0 |
| Beta6 after root thinning | PASS | 210.657 s | 104,466 | 82,688 | 2,859 | 107,325 | $0.236004 | 5 | 1 | 0 |

Raw is input plus output; cached input is a subset of input and is not added twice. No arm used a
child model, so the normalized cost equals the Sol API-price estimate and no Spark proxy affects
these rows.

*No rollout retained an actual service-tier value. Wall time is therefore observational. The
post-thin run contained an approximately 90-second model-response gap between two ordinary
inspection calls; it cannot distinguish provider/host latency from reasoning variance and is not
used to claim a speed regression or gain.

## Decisive deltas

- Initial paired signal, Beta6 versus Direct: wall `+37.572%` (observational), Raw `+77.980%`,
  normalized cost `+92.258%`, and two additional tool calls.
- Tool-trace cause: both arms used two project-inspection calls, one edit call, and one test call.
  Beta6 alone read `SKILL.md` and then `kernel.md`; there was no delegation or extra test loop.
- Post-thin versus pre-thin Beta6: one fewer tool call, Raw `-20.951%`, normalized cost
  `-36.697%`, input `-20.982%`, and output `-19.781%`.
- Post-thin versus Direct: Raw `+40.691%` and normalized cost `+21.706%`. The remaining structural
  tax is the single required root Skill read; `kernel.md` was not read.
- All three attempts passed visible, hidden, compile, diff-whitespace, scope, and frozen-file
  acceptance. Each model ran exactly one internal verification command; exact duplicate
  verification calls were zero.

## Route-unavailable and verification evidence

- `python3 tests/test_route_auditor.py` — passed after attempt/failure reconciliation was added.
- `python3 tests/test_v053_compact_contract.py` — passed after the final root-thinning wording.
- `python3 tests/test_recovery_hook.py` — passed after the final Hook wording and remained within
  its 420-word ceiling.
- Both Skill quick validations and Plugin validation passed on the final `0.5.3-beta.7`
  candidate, after the wording and version surfaces were complete.
- `python3 tests/test_beta7_release_contract.py` and `python3 tests/test_bootstrap.py` passed after
  the Beta7 manifest, policy, Bootstrap, profile, and changelog surfaces were updated.

`route_unavailable` now requires retained native/Adapter start-failure evidence in the current
turn. Zero-attempt and plan-only Direct decisions use their actual transfer, review, authority, or
coupling reason. The auditor independently flags missing attempt/failure evidence.

## Stop boundary

Do not rerun this fixture to obtain a nicer wall time. A second Direct arm, continuity task, or
full matrix would test stochastic/provider variance rather than the repaired contracts. Revisit
only if field diagnostics show another false `route_unavailable`, equivalent verification repeats,
or a real task still loads `kernel.md` solely because it touches several tiny files.

## Release continuation

The current post-thinning Beta6 implementation is the accepted source for `0.5.3-beta.7`.
Authoritative version surfaces agree and the version-affected packaging checks pass. Release now
proceeds directly to exact safe staging and remote publication; these results are not rerun or
reframed as a broader benchmark.
