# Route-unavailable misreport and defensive over-verification

- Status: fixed and validated for prerelease `v0.5.3-beta.7` on one representative development fixture
- Affected version: Goldilocks 0.5.3-beta.6
- Date: 2026-08-28

## Symptom

- A field diagnostic found two canonical receipts with `PLANNED_DISPATCH=0` and
  `REASON=route_unavailable` even though no native or Adapter start failure was retained.
- Sol could interpret “fresh verification” as a requirement to repeat equivalent checks,
  switch interpreters, or run a full matrix after decisive low-risk evidence already existed.

## Root cause

- The route contract described `route_unavailable` as a missing or failed route but did not
  require a start attempt and observed failure in the current turn. The auditor compared soft
  route history but did not reconcile actual attempts and start failures.
- The minimum-sufficient principle existed, while completion wording still privileged a newly
  rerun check over current decisive evidence. That ambiguity rewarded defensive ceremony.

The report's missing employee, Night Shift, External Adapter, and update samples remain
**insufficient evidence**, not confirmed product failures; they are outside this repair.

## Fix

- `route_auditor.py` now counts retained native/Adapter attempts and observed start failures.
  It flags `route_unavailable` without an attempt or without an observed start failure; a real
  failed Adapter start remains legal.
- The multi-unit root Hook states the same evidence rule, so the correction does not depend on
  the model successfully opening `route-card.md` before it chooses the visible reason.
- Root, kernel, orchestration, route-card, build, diagnose, and prove contracts now stop after
  one authoritative decisive check. Ordinary low-risk work does not repeat equivalent tests,
  change interpreter for ceremony, or expand into a full matrix.
- Lead only runs combined acceptance when integration changed the tested surface or current
  integrated evidence is missing.
- A multi-file task no longer exits the root Direct gate merely because it has several ready
  units. When each unit is small and briefing/review/integration has no net benefit, the Hook's
  compact make-or-delegate check can select Direct without loading `route-card.md` or `kernel.md`.

## Verification

- `python3 tests/test_route_auditor.py` — passed after the affected change.
- `python3 tests/test_v053_compact_contract.py` — passed after the affected change.
- `python3 tests/test_recovery_hook.py` — passed after the final Hook wording.
- `python3 tests/test_beta7_release_contract.py` and `python3 tests/test_bootstrap.py` — passed
  after all Beta7 version surfaces were updated.
- Both Skill Creator quick validations and Plugin validation — passed on the final candidate.
- `git diff --check` — passed on the reconciled Beta6 worktree.
- One mature parallel-development fixture completed with one attempt per arm, zero retry, and one
  external quality gate; the results and stop boundary are recorded below and in the validation
  record. No continuity task or full matrix was added.

## Failed or excluded approaches

- One delegated static review failed before execution with upstream `503 auth_unavailable`.
  It was not retried and is not counted as a Goldilocks product failure.
- Historical benchmark results select the fixture only; no historical performance value is
  reused as a current Beta6 result.
- The first compact-contract trigger sentence did not match the multi-unit classifier; its test
  input was corrected and only that failed check was rerun.
- The first expanded Hook wording exceeded the existing 420-word ceiling. The rule was compressed
  instead of relaxing the limit; the final Hook contract passed.

## Performance observation

- The paired pre-thin Beta6/Direct attempts both passed. Beta6 used two extra instruction reads
  (`SKILL.md`, then `kernel.md`), wall `+37.572%` (observational), Raw `+77.980%`, and normalized
  cost `+92.258%`; both ran one test command and zero duplicate verification.
- After root thinning, a single Beta6 confirmation passed without reading `kernel.md`. Relative
  to pre-thin Beta6 it removed one tool round, reduced Raw `20.951%`, and reduced normalized cost
  `36.697%`. It remained Raw `40.691%` and cost `21.706%` above Direct because the required root
  Skill read remains.
- No rollout retained actual service tier. The post-thin sample also had an approximately
  90-second model-response gap, so wall-time changes are observational and were not rerun.

## Related evidence

- Regression tests: `tests/test_route_auditor.py`, `tests/test_v053_compact_contract.py`
- Benchmark record: `evals/beta6-route-speed-vs-direct-2026-08-28/VALIDATION.md`
- Field context: private deep diagnostic report generated 2026-08-28; raw report is not copied
  into the repository.

## Release continuation

- The accepted Beta7 baseline is the current post-thinning Beta6 worktree described above.
- Authoritative version surfaces now agree on `0.5.3-beta.7`; the version-affected contract,
  Bootstrap, route auditor, compact contract, recovery Hook, both Skill validations, Plugin
  validation, and diff whitespace check pass.
- The initial Beta7 publication completed at commit `e6ebd87`. The user-authorized same-tag
  refresh retains that commit as the rollback point and makes the refreshed `v0.5.3-beta.7` Tag
  the authoritative release source.
- The model fixture was not rerun. The later update-reminder UX change below does not alter the
  validated routing/verification result above.

## Persistent update-reminder follow-up

- Status: included in the refreshed Beta7 candidate and focused-test validated.
- Cause: `notified_version` correctly limited the SessionStart discovery notice to once, but that
  notice could be buried by an active task and no later root task was required to repeat it.
- Fix: the cached `latest_version` remains subject to the existing 24-hour network-check throttle,
  while a new root `UserPromptSubmit` Hook injects the exact localized two-line notice into every
  final answer until the installed version reaches the pending version. Worker tasks remain silent.
- The SessionStart block still carries verified tag, marketplace, install, Bootstrap, approval,
  and Hook-trust instructions for the installing agent, but is now explicitly internal so it does
  not duplicate the concise user notice. Stop Hook output is not used because Codex Desktop does
  not render it as normal assistant text.
- `python3 tests/test_update_checker.py` passed with two consecutive Beta5 root turns both showing
  `Beta5 → Beta7`, English localization, `notified_version` independence, and suppression after
  installing Beta7. `python3 tests/test_beta7_release_contract.py` and `git diff --check` also
  passed on the integrated candidate.
