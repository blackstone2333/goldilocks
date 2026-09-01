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
isolated repository/HOME/CODEX_HOME, and received zero retry. Later Beta7/Beta8 candidate sections
record their own frozen runtime settings and release gates.

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
It became the first member of a stricter consecutive-stability gate; publication remained paused
until a second candidate-only run met the predeclared bounds below.

## Consecutive Beta8 stability gate

The user required two consecutive quality-passing candidate runs before publication. A unique
candidate-only stability mode then ran once in the existing dedicated test conversation. Direct
was not rerun, there was no host retry, and the root Skill remained unread on both candidate runs.

| Candidate run | Quality | Wall* | Raw | Normalized USD | Tools | Verification | Root Skill reads |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Refined confirmation | PASS | 121.000 s | 146,841 | $0.320499 | 7 | 0 | 0 |
| Stability confirmation | PASS | 125.804 s | 151,256 | $0.351791 | 7 | 1 | 0 |

The frozen acceptance bounds were wall difference at most `15%`, Raw difference at most `10%`,
normalized-cost difference at most `10%`, equal passing quality, zero retry, and zero root Skill
reads. The observed consecutive differences were wall `+3.970%`, Raw `+3.007%`, and normalized
cost `+9.764%`; every bound passed.

Historical release action: this evidence was used to publish `0.5.3-beta.8`, which was later
explicitly withdrawn. The GitHub prerelease and local/remote tags were removed; the candidate
branch remains. This section no longer authorizes publication.

## Withdrawn Beta8 reoptimization

The withdrawn candidate was reworked against one fresh Direct arm. Three avoidable model rounds
were isolated rather than attributed to complete orchestration: fail-hard optional-path discovery,
Python syntax newer than the active 3.9 runtime, and incorrect self-authored probe expectations.
The compact Hook now performs guarded discovery, relevant reads, and runtime detection in one
first call; it treats the declared/current runtime as the syntax floor and requires one
fail-propagating evidence call with expectations derived first.

Two consecutive runs of the final contract used one attempt, zero host retry, no child, and no
root-Skill read. All external visible, hidden, compile, diff, scope, and frozen-file gates passed.

| Arm | Quality | Wall* | Raw | Normalized USD | Tools | Evidence calls | Root Skill reads |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fresh Direct | PASS | 96.213 s | 78,332 | $0.254610 | 4 | 1 | 0 |
| Final candidate A | PASS | 94.182 s | 70,245 | $0.302006 | 3 | 1* | 0 |
| Final candidate B | PASS | 94.593 s | 69,699 | $0.231591 | 3 | 1* | 0 |

Candidate A versus Direct observed wall `-2.1%`, Raw `-10.3%`, and one fewer tool call. Candidate B
observed wall `-1.7%`, Raw `-11.0%`, normalized cost `-9.0%`, and one fewer tool call. Between the
two candidates, wall differed by `0.4%` and Raw by `0.8%`; both traces contained exactly one
guarded inspection, one implementation patch, and one combined evidence call, with none of the
three avoidable repair rounds.

Normalized cost was not stable between the candidates: A was `+18.6%` versus Direct while B was
`-9.0%`. A cached `46.9%` of input versus `68.6%` for Direct; B cached `68.4%`. This is retained as
cache variance, not reframed as workflow work or a universal cost claim. `*` The current telemetry
regex reports these combined calls as zero because their command is stored with escaped newlines;
the raw traces show one `set -e` evidence call in each run.

Decision: the final candidate restores the first speed candidate's Direct-level wall/Raw behavior
without removing Goldilocks capabilities. Publication and local installation remain paused; no
additional rollout is justified solely to obtain a more favorable cache sample.

## Beta8 two-task release gate — frozen before execution

The user authorized two different fresh tests followed by publication only if both remain stable.
The gate uses one existing-code bug fix (`beta8-bugfix`) and one new bounded feature
(`beta8-feature`). Each task runs one Direct cell and one current-candidate cell with Sol/xhigh,
requested standard service, one attempt, and zero host retry. Execution is counterbalanced:
bugfix Direct → bugfix candidate → feature candidate → feature Direct.

The release gate was fixed before model calls:

- all four infrastructure and external quality results pass;
- each candidate emits a Direct receipt, reads no root Skill, and starts no child;
- per task, candidate wall and Raw are no more than `10%` above same-task Direct;
- per task, candidate tool calls do not exceed same-task Direct; and
- normalized cost is reported but not gated because cached input depends on provider state.

Any failed criterion stops publication without retrying a cell. Passing both tasks authorizes only
focused version/packaging checks, remote publication verification, and local installation; it does
not authorize another performance rollout.

### Final-gate result

All four cells completed with one attempt, zero retry, valid identity, and passing external quality.
Both candidate cells selected Direct, emitted the canonical receipt, read no root Skill, started no
child, and avoided second discovery, runtime-compatibility repair, and probe-expectation repair.

| Task / arm | Quality | Wall* | Raw | Normalized USD | Tools | Root Skill reads |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Bugfix Direct | PASS | 58.574 s | 86,924 | $0.121724 | 5 | 0 |
| Bugfix candidate | PASS | 60.757 s | 65,992 | $0.171664 | 3 | 0 |
| Feature candidate | PASS | 56.557 s | 65,501 | $0.170967 | 3 | 0 |
| Feature Direct | PASS | 50.067 s | 72,012 | $0.152919 | 4 | 0 |

The bugfix gate passed: candidate wall `+3.727%`, Raw `-24.081%`, and two fewer tool calls. The
feature gate failed only the predeclared wall bound: candidate wall `+12.963%` exceeded the `10%`
limit, while Raw was `-9.042%`, tool calls were one lower, and every structural/quality condition
passed. The trace contains no workflow repair round that explains the extra 6.490 seconds; the
remaining wall cause is unknown/model-provider variance, not evidence for another product repair.

Release decision: `release_eligible=false`. Do not publish, tag, package, install, or rerun a cell
under this frozen gate. Changing the wall tolerance after observing the result requires a new user
decision rather than a retrospective benchmark rewrite.

### User-authorized prerelease decision

On 2026-09-01, after reviewing the frozen result, the user explicitly accepted a `15%` wall
tolerance for this prerelease and authorized publication without another performance rerun. The
original `10%` gate and its failed feature-wall result above remain unchanged. Under the newly
authorized boundary, both task cells are within tolerance, all quality/structure conditions remain
passing, and the release chain is eligible. This decision authorizes only focused packaging checks,
GitHub prerelease publication, and local installation; it does not turn either task observation
into a general performance guarantee.
