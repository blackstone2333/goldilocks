# Debug Note: Spark quota exhaustion and worker fallback

- Status: fixed and verified for prerelease `v0.5.3-beta.6`
- Affected versions/environment: Goldilocks `v0.5.3-beta.5`, Codex Desktop/CLI native Spark role
- Date: 2026-08-24

## Symptom

- A Spark task appeared to exhaust a newly reset five-hour pool after the UI was interpreted as showing two Spark workers.
- After the host reported Spark usage unavailable/exhausted, the main model continued the work instead of visibly selecting a new eligible worker.
- Impact: scarce Spark quota may be consumed too aggressively, and the documented fallback may not preserve delegated execution.

## Current evidence

- `model-registry.json` describes Spark as a separate pool with no public numeric rate and says to fall back when unavailable or exhausted.
- `kernel.md` currently allows Spark fallback to Terra, Luna, or Direct. Therefore main-model takeover is not automatically a policy violation; the missing evidence is whether another route was eligible and available, and whether the takeover reason was surfaced.
- The prior Beta5 release tests covered role identity and unavailable-route wording, but are not a runtime proof for mid-task quota exhaustion.
- The task actually started one Spark and one Luna. The Spark child performed real repository reads/searches and one patch before `task_complete.error.codex_error_info=usage_limit_exceeded`; exact account telemetry is not retained in this public record.
- The first visible five-hour snapshot was already exhausted and close to its reset. It was therefore the end of the prior rolling window, not proof that one child exhausted a fresh pool.
- A later ordinary host snapshot confirmed that the rolling window had reset; no Spark probe was launched.
- The real errored child produced no recorded `SubagentStop`; its `executions.stopped_at` remains null. Official Codex Hook documentation lists `agent_transcript_path` on `SubagentStop`, but no terminal-error field. The child's own rollout does contain the structured terminal error.

## Disposition of hypotheses

1. **Disproved as stated:** there were not two Spark workers; one Spark and one Luna were started.
2. **Supported boundary:** the old five-hour pool was already at its end and the public token-to-quota conversion is unknown, so this task's raw tokens cannot explain the whole pool.
3. **Confirmed product defect:** Goldilocks has no same-task Spark quota circuit breaker.
4. **Confirmed lifecycle gap:** an errored native Spark child may bypass `SubagentStop`; rollout recovery closes lifecycle only and discards the structured failure reason. Direct is allowed by policy, but Beta5 does not require a visible Terra/Luna/Direct re-comparison after quota exhaustion.

## Regression result

Both distinguishing fixtures pass. A second Spark plan is denied while Terra remains eligible and reset expiry restores Spark. A new parent prompt after a quota error that omitted `SubagentStop` closes the execution and preserves `terminal_outcome=usage_limit` plus `quota_reset_at`.

## Do not repeat

- Do not estimate remaining Spark quota from raw token totals; the public conversion is unknown.
- Do not launch another Spark worker to test an already exhausted pool.
- Do not add a general delegation limit before confirming whether the failure is quota-specific.
- Do not call Direct takeover defective without checking eligibility, availability, and the recorded reason for the next route.

## Root cause

- The quota interpretation combined a UI role-count mistake with a rolling-window boundary: the observed Spark run occurred just before the old five-hour window reset, not immediately after a fresh reset.
- Beta5 records native starts and stops but not privacy-safe terminal outcomes. On this host the usage-limit error skipped `SubagentStop`, and the fallback recovery path recognizes only that `task_complete` exists. Consequently the parent receives the error text, but Goldilocks neither latches Spark as unavailable for the root task nor forces an explicit comparison of Terra, Luna, and Direct.

## Fix

- Add an allowlisted terminal outcome (`completed`, `usage_limit`, `other_error`, `unknown`) to native execution state without storing raw error text.
- Parse `task_complete.error.codex_error_info` from the one exact child rollout, using `agent_transcript_path` when `SubagentStop` exists and the existing session-root lookup when it does not.
- Before another native Spark plan, reconcile unresolved Spark executions in that session; after confirmed `usage_limit`, deny repeat Spark use in that root task and require a fresh Terra/Luna/Direct comparison. Terra is preferred for remaining transferable code; Direct remains valid only when takeover is cheaper or the remainder is no longer transferable, and the visible receipt must say why.
- Recovery now commits authoritative lifecycle reconciliation before optional debt statistics, makes the `decisions.tier` query schema-aware, and reuses the same allowlisted terminal parser.

## Verification and prevention

- Passed: `python3 tests/test_agent_routing_hook.py` covers quota failure, no second Spark dispatch, eligible Terra fallback, reset expiry, and no raw-error persistence.
- Passed: `python3 tests/test_recovery_hook.py` covers omitted-`SubagentStop` recovery, terminal outcome/reset persistence, last-lifecycle-event handling, and reduced-schema compatibility.
- Passed: `git diff --check`.
- Independent `goldilocks_sol_reviewer / gpt-5.6-sol / high` review: PASS, with no blocking or medium/high findings. It separately checked session isolation, reset expiry, privacy, schema compatibility, and Terra/Luna/Direct eligibility.
- Runtime constraint observed: no new Spark was launched; verification reused existing host evidence.

## Current behavior

- A confirmed native Spark quota failure is latched for that parent session until the observed reset; when reset metadata is absent, the fallback is a conservative five-hour window from failure.
- A repeated native Spark dispatch is denied during the latch. Terra and Luna remain eligible; Direct remains eligible only when takeover is cheaper or the remainder is no longer transferable, and its reason must be visible.
- Other sessions are not mechanically locked by this parent-session guard. External adapters receive the policy instruction but are outside the native spawn guard.
- A later ordinary host snapshot confirmed the rolling-window reset without launching another Spark probe. Exact account usage values are intentionally omitted; there is still no public token-to-quota conversion.

## Continuity visibility audit (2026-08-25)

- Status: implementation authorized; activity visibility and nested-worktree discovery repair in progress.
- Question: recent work did not visibly show a context handoff, so distinguish durable parent continuity from worker conversation inheritance and determine whether either path was omitted.
- Parent evidence: the root task compacted at 2026-08-24 15:01:00Z and 15:19:28Z. The repair resumed from the exact failed recovery test, reconciled the branch/diff, and updated `.goldilocks/ACTIVE.md`; no objective or work state was lost.
- Worker evidence: the recent Explorer, Terra audit, and Sol review all started with `fork_turns=none`. Terra and Sol received bounded contracts containing the worktree, scope, prohibitions, and acceptance, so copying the full parent conversation was neither required nor desirable.
- Owner-handoff disposition: no mutable worker chain changed owners. The main model implemented; Terra diagnosed read-only; Sol reviewed read-only. Therefore a separate Owner-to-Owner handoff was not triggered and should not have been.
- Confirmed visibility/discovery gap: the active frontier lives in the nested implementation worktree, but the root task's host cwd is the outer repository. Installed Beta5 `find_ledger()` searches only cwd and ancestors. The worktree session recorded `ledger_present=1`, while the outer root session recorded `ledger_present=0`. Continuity still succeeded because the compaction reminder and explicit reconciliation forced the frontier read, but the Hook could not advertise the ledger automatically.
- Recommended repair boundary: persist an audited `session_id → active worktree/frontier` pointer when the Lead first adopts a worktree, then resolve only that exact path on recovery. Do not recursively search arbitrary children. Surface a compact `DETAIL=restored from ACTIVE` fact only on actual restore, avoiding a permanent per-turn token tax.
- User-visible product decision: a small output-token tax is acceptable when it proves Goldilocks is actively routing, restoring continuity, delegating, falling back, accepting work, reminding Night Shift, reporting requested Usage, or detecting updates. Visibility must describe only observed actions, remain localized, and coalesce duplicates rather than exposing internal audit logs.
- Exact next test: inventory current Hook outputs, then add behavioral coverage for an executable activation cue, event facts carried into the final receipt, and a registered nested-worktree continuity restore. Pure internal no-op checks may remain silent only when no Goldilocks behavior affected the task.
- Reconciled implementation contract (2026-08-25): routine Hook checks use localized host `statusMessage` so they remain visible without adding model-context/output tax; events that actually affect execution are coalesced into one localized `Goldilocks｜已启用` / `Goldilocks | Active` fact and the existing final receipt `DETAIL`. The nested-worktree fallback must select only a Git-registered worktree whose active frontier has the current host `session_id`; it must not recursively scan arbitrary children or guess between unrelated active ledgers.
- Current exact next test: add failing assertions for the localized executable activation cue, event-bearing final receipt, pure-conversation silence, and `session_id`-matched registered-worktree recovery cue before changing runtime code.
- Implemented result: all nine Hook commands now carry a branded host `statusMessage`; executable work receives one localized first-update activity cue, later real events are coalesced, and the existing final `DETAIL/详情` must state the actual Goldilocks action. Pure conversation keeps only transient host status and gets no persistent activity line, route receipt, or automatic Usage.
- Worktree result: ACTIVE frontmatter now records `session_id`. Recovery first preserves local behavior, then checks only conventional Git registries and their registered worktree entries; it accepts exactly one `status: active` + exact-session match. Wrong-session, unregistered, malformed, and ambiguous candidates are not selected.
- Fresh affected verification passed: `test_visibility_contract.py`, `test_recovery_hook.py`, `test_context_lean_worker_contract.py`, `test_final_output_hygiene_contract.py`, `test_v053_compact_contract.py`, `test_update_checker.py`, `test_agent_routing_hook.py`, `test_usage_reporter.py`, `test_route_auditor.py`, Skill Creator `quick_validate.py`, `py_compile`, and `git diff --check`.
- Measured visibility cost versus published Beta5's injected response contract: approximately +90 English or +137 Chinese input tokens before caching; one persistent activity line is typically only a few dozen output tokens. Static Hook statuses add zero model calls and zero model tokens.
- Historical `test_v03_contract.py` was intentionally not used as acceptance: it has 22 pre-existing expectations for 0.3/0.5.2 topology/version surfaces and fails on the Beta5 baseline independently of this repair.
- Exact next acceptance: independent Sol read-only review of truthful event semantics, session isolation, fail-silent behavior, and the combined Spark fallback + visibility diff; repair only a blocking finding.
- First independent review result: fix-first. It identified a one-way/stale Git registry or symlinked `.goldilocks` path that could redirect ACTIVE, two status labels that overstated the underlying Hook (`Usage preference`, visible receipt audit), and PostCompact's empty-prompt language fallback to English.
- Review repairs: require registry `gitdir` and worktree `.git` to point to each other; reject symlinked registry entries, gitdir markers, worktree roots, ACTIVE files, and `.goldilocks` parents; retain valid relative backlinks. Rename the statuses to `Usage baseline` and `Route candidate audit`. Restore response language from the latest session/workspace gate row during PostCompact.
- Added behavior coverage for valid relative backlink, forged one-way entry, symlinked frontier parent, Chinese turn→PostCompact localization, and truthful status labels. The affected focused suite, quick validation, compilation, and diff check pass after repair.
- Current exact acceptance: same Sol reviewer performs one bounded read-only re-review of those three closures; no full-suite rerun or publication.
- Final acceptance: the same `goldilocks_sol_reviewer / gpt-5.6-sol / high` re-reviewed only the three repairs and returned `ship`, with no remaining realistic failure scenario. Four affected tests and `git diff --check` were independently fresh.
- Real workspace probe: resolving from the host's non-Git outer cwd for the current session selected exactly the intended registered worktree frontier at `work/goldilocks-final-output-hygiene/.goldilocks/ACTIVE.md`.
- Pre-release repair checkpoint: Spark quota fallback, activity visibility, truthful Hook labels, localized compact recovery, and registered-worktree continuity selection were fixed and verified on `fix/spark-quota-fallback-v053-beta5`. At that checkpoint no publication, installation, host-permission change, or automatic Usage opt-in had been performed.
- Release continuation (2026-08-25): user authorized publishing the verified state as the next GitHub Beta, expected `v0.5.3-beta.6`. Release preparation is limited to authoritative version surfaces, one affected packaging check, commit/tag/branch push, prerelease creation, and remote convergence verification; stable/SkillHub/local install/permission changes remain out of scope.
- Beta6 release inventory (2026-08-25): a read-only comparison with the Beta5 release commit confirmed that the three plugin/marketplace manifests, policy/data identities, Bootstrap Beta reference, bilingual changelogs, and release contract are the current-version surfaces. README and public installation documents remain on stable `v0.5.2`; historical Beta5 evidence is not rewritten. Exact next test after the version patch is the renamed Beta6 release contract followed by the affected Bootstrap, routing, recovery, visibility, compact, hash, JSON, compilation, and diff checks once.
- Beta6 packaging verification (2026-08-25): the release contract, Bootstrap, routing, recovery, visibility, compact, context-hash, update-checker, both Skill validators, JSON parsing, Python compilation, and diff checks passed. Two earlier local HTTP fixture attempts produced empty output before the full update-checker contract completed without a product-code change; no functional assertion failed. A final independent Terra read-only packaging review returned PASS.

## Links

- Related policy: `plugins/goldilocks/skills/goldilocks/references/kernel.md`
- Related registry: `plugins/goldilocks/skills/goldilocks/assets/model-registry.json`
- Related tests: `tests/test_agent_routing_hook.py`, `tests/test_recovery_hook.py`
