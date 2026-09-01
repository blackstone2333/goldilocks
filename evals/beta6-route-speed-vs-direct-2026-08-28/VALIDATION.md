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
Authoritative version surfaces agree and the version-affected packaging checks pass. The initial
Beta7 release was commit `e6ebd87`; the user-authorized same-tag refresh adds only the persistent
update-reminder UX and bilingual release surfaces. These benchmark results were not rerun or
reframed as a broader claim.

## 2026-09-01 Beta7 speed candidate

One fresh Beta7-versus-Direct pair and one candidate-only confirmation were run with the same
bounded fixture and external quality gate. All three arms passed with one attempt and zero retry.

| Arm | Quality | Wall* | Raw | Normalized USD | Tools | Root Skill reads |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Direct | PASS | 88.240 s | 93,198 | $0.230323 | 5 | 0 |
| Released Beta7 | PASS | 135.400 s | 148,870 | $0.332128 | 7 | 1 |
| Speed candidate | PASS | 84.953 s | 90,507 | $0.314607 | 4 | 0 |

The candidate keeps routine bounded Direct work in the compact Hook instead of loading the root
Skill merely to confirm Direct. It lazy-loads worker naming, fallback, and delegation-only rules;
full routing still loads for unresolved ambiguity or cause, continuity, profitable delegation,
cross-unit artifacts, or explicit Goldilocks use. It also composes safely compatible validation
targets into one evidence bundle and reruns only failed or affected checks.

Relative to released Beta7, the candidate observed wall `-37.3%`, Raw `-39.2%`, normalized cost
`-5.3%`, and three fewer tool calls. Relative to Direct it observed wall `-3.7%` and Raw `-2.9%`.
Its normalized cost remained `+36.6%` because cache hit was `55.4%` versus Direct's `77.0%`;
therefore no guaranteed cost advantage is claimed. Wall and cost percentages are directional from
one representative sample, not a general benchmark.

The CLI/render check remains because it covered a changed surface not proven by the visible unit
tests. Visible activation, route receipt, Usage modes, Night Shift, fallback, continuity, Owner
routing, delegation, and final acceptance remain contracted. A candidate trace exposed a receipt
count bug (`CONCURRENCY=1/4` with zero child starts); the compact Hook now excludes the main model
from child concurrency, and the focused recovery/compact contract checks passed after that fix.

Stop boundary: do not rerun this speed fixture. If publication is authorized, use a new prerelease
version and run only the focused version/packaging and contract checks required by that change.

## User-authorized candidate repeat

The user authorized one additional candidate-only attempt as a conditional Beta8 release gate.
It ran in the existing dedicated test conversation with zero host retry and did not rerun Direct.

| Arm | Quality | Wall* | Raw | Normalized USD | Tools | Verification | Root Skill reads |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Beta8 candidate repeat | PASS | 213.546 s | 126,656 | $0.384183 | 6 | 2 | 0 |

Relative to the retained released-Beta7 arm, Raw remained `-14.9%`, one tool call and the root Skill
read remained removed, and quality passed. Wall was `+57.7%` and normalized cost `+15.7%`, so the
previous speed/cost direction did not repeat and the conditional publication gate did not open.

The trace gives concrete causes for the extra rounds: an optional `AGENTS.md` lookup was chained so
no match aborted the first inspection; a malformed quoted follow-up lost command resolution; and
the first compile check used the isolated HOME's unwritable Python cache before rerunning only the
affected compile/CLI evidence with a `/tmp` cache. There were no duplicate verification calls and
the complete root Skill still was not read. These are real attempt costs, not grounds to erase or
retry the result.

Stop boundary: do not publish Beta8 and do not run another attempt without a new user decision.

## Refined candidate confirmation

After the user authorized the bounded fail-soft discovery, nonredundant compile, and writable-cache
changes, one new candidate-only confirmation ran in the same dedicated test conversation. Direct
was not rerun and the host made zero retry.

| Arm | Quality | Wall* | Raw | Normalized USD | Tools | Root Skill reads |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Refined Beta8 candidate | PASS | 121.000 s | 146,841 | $0.320499 | 7 | 0 |

Relative to the retained released-Beta7 arm, the refined candidate observed wall `-10.64%`, Raw
`-1.36%`, and normalized cost `-3.5%`, with equal quality and no root Skill read. The isolated
Python cache caused no repair round. The first inspection still attempted target files before they
existed, but the prior malformed command-resolution failure did not recur. The remaining ordinary
repair corrected Python 3.9 annotation compatibility, and the final CLI probe corrected its own
expected word total; the external visible, hidden, compile, diff, scope, and frozen quality gate
passed.

This one-task evidence supports the release decision but is not a general performance guarantee.
The successful direction satisfies the user's conditional Beta8 publication gate; no additional
behavioral run is authorized or needed.
