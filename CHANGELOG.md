# Changelog

[中文更新记录](CHANGELOG.zh-CN.md)

## 0.6.0 — 2026-09-04

### Lean no-Hook workflow with event-triggered project evidence

- Remove the Goldilocks lifecycle Hook product surface and its recurring prompt, session, compaction, stop, Usage, update, and audit work. Routing and recovery stay in the Skill; Usage, diagnostics, and route inspection remain available explicitly instead of running in the task hot path.
- Make the lifecycle order explicit: classify the incoming message, align the intended end state, choose the minimum project record, plan and route, execute with continuity, then accept and update. Direct means less orchestration after alignment; it does not suppress task-matching domain Skills.
- Treat Spec and Plan as work-unit evidence, keep ACTIVE as a compact execution frontier, and write PROJECT, handoff, debug, ideas, and CHANGELOG only when their real events occur. Completed work must not remain an active instruction or be reread merely because a file exists.
- Leave compaction to the host instead of installing a global Goldilocks `compact_prompt`. An explicit clean install removes only an exact recognized Goldilocks legacy prompt; custom and experimental prompt settings remain untouched.
- Preserve the native Spark/Luna/Terra/Sol roles, Night Shift, model fallback, user-selected host permissions, and minimum-sufficient verification. The short description handles selection for an unambiguous routine Direct task without loading the full root Skill or manufacturing activity/receipt for visibility; a real Goldilocks load still produces its factual route receipt.
- Promote the verified release candidate as the stable `v0.6.0` line. On its single frozen three-arm smoke task, all arms passed quality and the candidate observed 11.017% lower wall time and 23.740% fewer Raw Tokens than Direct; this remains task-specific evidence, not a universal performance promise.
- Keep the ACTIVE contract intentionally host-native: static, clean-install, and no-Hook boundaries passed. One additional live compaction/continuation probe was inconclusive because the host's first turn did not complete, so it is recorded as unknown rather than pass or fail and will be followed through normal field use.

## 0.5.3-beta.9 — 2026-09-03

### Domain Skills remain active on Direct

- Scope Direct precisely: it skips only the full Goldilocks orchestration path. Task-matching domain Skills—such as design, frontend, and document Skills—still load normally under the host's Skill-selection rules after routing.
- Add focused regression coverage for this compatibility boundary while retaining Beta8's lightweight Direct entry, visible activation and route receipt, on-demand Usage, fallback, continuity, and minimum-sufficient verification behavior.
- This is a focused compatibility fix from the clean `v0.5.3-beta.8` baseline; the existing Beta8 performance evidence remains the applicable benchmark boundary.

## 0.5.3-beta.8 — 2026-09-01

### Faster Direct entry with full orchestration on demand

- Keep routine bounded Direct work in the compact Hook instead of loading the root Skill merely to confirm Direct. Ambiguity, unknown cause, continuity, profitable delegation, cross-unit artifacts, and explicit Goldilocks requests still load the complete workflow.
- Make optional discovery fail soft and compose only applicable acceptance evidence. Python compilation is skipped when tests or CLI execution already imports every changed surface; failed or affected checks remain the only checks rerun.
- Keep visible activation, route receipts, Usage modes, Night Shift, Spark/Luna/Terra fallback, Owner routing, Sol specialists, continuity, and final acceptance. Zero child starts now report concurrency `0` rather than counting the main model.
- In one representative quality-passing confirmation versus released Beta7, the candidate observed wall time **−10.64%**, Raw Token **−1.36%**, and normalized comparison cost **−3.5%**, with zero root Skill reads. Wall time and cache behavior remain observational; this is not a general performance guarantee.
- In the final two-task comparison against Direct, all four cells passed quality and infrastructure with one attempt and zero retry. The Beta8 bug-fix cell observed wall **+3.727%**, Raw Token **−24.081%**, and two fewer tool calls; the bounded-feature cell observed wall **+12.963%**, Raw Token **−9.042%**, and one fewer tool call. These task-level observations define the prerelease evidence boundary, not a universal speed claim.

## 0.5.3-beta.7 — 2026-08-28

### Evidence-grounded routing and minimum-sufficient verification

- Make `route_unavailable` evidence-based: it now requires a retained native or Adapter start attempt and an observed start failure in the current turn. A zero-attempt or plan-only Direct decision reports its actual reason instead, while genuine Adapter start failures remain valid and auditable.
- Stop Sol verification after one authoritative check provides decisive evidence. Ordinary low-risk work does not repeat equivalent tests, switch interpreters for ceremony, or expand into a full matrix; after a repair it reruns only failed and affected checks, and Lead repeats acceptance only when integration changed the tested surface or integrated evidence is missing.
- Let several small ready units stay Direct when briefing, review, and integration would add no net value. In one representative quality-passing fixture, the thinned path removed the extra `kernel.md` read and reduced raw tokens by 20.951% and normalized cost by 36.697% versus the pre-thinning Beta6 sample; wall time remains observational because the run contained an unclassified provider/host delay.
- Keep newer-version reminders visible after discovery: every root task appends one concise localized notice until the installed version catches up. Per-task reminders read only local cached state, preserve the 24-hour remote-check interval, and never bypass explicit approval, Tag verification, reinstall, Bootstrap, or Hook-trust review.

## 0.5.3-beta.6 — 2026-08-25

### Spark quota fallback, visible activity, and session-bound continuity

- Recover a native Spark `usage_limit` terminal result even when the host omits `SubagentStop`. The same parent session will not launch Spark again before the observed reset; it must freshly compare Terra, Luna, and Direct. Only an allowlisted outcome and reset time are retained, never raw error text.
- Give all nine Goldilocks Hook paths a localized transient activity status. Executable work also receives one compact `Goldilocks | Active` cue and a truthful final route detail for observed routing, recovery, fallback, Night Shift, Usage/update, or acceptance activity. Pure conversation receives no persistent activity line, and Usage remains on-demand by default.
- Restore continuity only from exactly one same-session ACTIVE frontier in a Git-registered worktree. Wrong-session, ambiguous, forged one-way registry, and symlinked candidates fail silent; Chinese tasks remain Chinese after `PostCompact` recovery.

## 0.5.3-beta.5 — 2026-08-22

### Final-output hygiene and update awareness repair

- Added an on-demand final-output hygiene reference: durable delivery surfaces now describe only the accepted, verified current state while preserving real removals, migrations, compatibility, safety, audit facts, external actions, and pre-existing user work. This adds no scanner, extra Agent, freeze, or default verification loop.
- Repaired quiet update awareness to read the GitHub Releases API: successful checks remain 24-hour quiet checks, failures retry after 15 minutes, stable installs ignore prereleases, and prerelease installs can discover newer prereleases or stable releases. Each newer version is still noticed once.
- The checker never downloads, executes, or silently upgrades code. Hook-definition changes remain subject to user review; after an approved update, verify the Tag, reinstall, run Bootstrap plan/apply/check, and start a new task.

## 0.5.3-beta.4 — 2026-08-20

### Compact execution and local diagnostics

- Added minimum-sufficient verification guidance: reuse focused evidence, preserve existing safeguards, and after one ordinary repair rerun only failed or affected checks.
- Made the Direct route receipt explicit for every executable task while keeping Usage on-demand by default; Bootstrap `automatic` remains an explicit opt-in.
- Preserved user-selected host permissions across native routing, strengthened route and native-role identity audits, and record only privacy-preserving local Hook-health metadata for aggregate export.
- Added a seven-day, read-only diagnostics Skill for Beta feedback. It excludes prompts, project contents, secrets, and transcript text; unavailable or old local evidence is reported as insufficient rather than a failure.

## 0.5.2 — 2026-08-12

### Bootstrap compatibility patch

- Fixed the Python 3.9 Bootstrap TOML validation path to accept a valid repeated `[[skills.config]]` array-of-tables while preserving fail-closed, zero-write behavior for duplicate ordinary tables, nonstandard agent declarations, and conflicting configuration.
- Bootstrap still does not modify Hook trust automatically; that decision remains with the host and user.

## 0.5.1 — 2026-08-12

### Native visibility, safe setup, and measured defaults

- Added one compact visible Direct receipt and made Usage on-demand by default; `automatic` is an explicit Bootstrap opt-in. The default avoids a mandatory pre-final read on ordinary work, while both modes remain one local read with no second model call.
- Registered and identity-checked native Spark, Luna, Terra, and Sol roles, with the packaged adapter as the fallback when the host cannot expose the required native route. Night Shift is now an active delivery mode under the same route and ownership gates.
- Bounded visible Sol specialists to two concurrent slots per root, with host-confirmed terminal return before capacity is recycled.
- Made Bootstrap validate complete TOML safely on Python 3.9 with bundled, MIT-licensed Tomli. After approval it can append only the four missing official `[agents.*]` registrations; Hook trust remains a host decision.
- Clarified that immutable Tag updates require Tag verification, marketplace removal, re-add at the verified ref, plugin reinstall, Bootstrap plan/apply/check, and a new task; Goldilocks never self-updates.
- Refined complete-chain ownership: one owner carries the known mutable chain, receives one ordinary focused repair when needed, and returns evidence for proportional Lead acceptance.
- Made Direct a progressive cold start: it preloads no Route Card, orchestration, or continuity reference, but upgrades on demand when execution reveals independent units, an unknown cause, or a persistence boundary. The root-localized route receipt remains visible.

### Evidence limits

The [final frozen Direct sample](benchmarks/V051-RELEASE-EVIDENCE.md) was quality-valid for both arms. Relative to published v0.5.0, the candidate measured wall **−10.997%** and output **−13.624%**, but raw tokens **+39.777%**, official USD **+15.727%**, and tool calls **+33.333%**. This is a Pareto tradeoff, not a dominant efficiency result; it covers only the recorded task and does not claim automatic Hook trust or automatic self-update.

## 0.5.0 — 2026-08-11

### Stable release

- Promoted the cost-aware routing and companion-agent support from the 0.5.0 prerelease series to stable `v0.5.0`.
- Finalized the public ownership structure: Sol is Lead; Terra Medium is the primary Standard owner; Spark XHigh is a deterministic coding-only Fast leaf that does not own documents or continuity; Luna Max is the latency-tolerant Economy route. Spark capacity is not reserved.
- Clarified chain ownership: one owner carries a complete known mutable chain, Lead performs one proportional final acceptance, and a fresh handoff continues from its durable boundary rather than rebuilding prior work.
- Published the frozen three-task release evidence as three aggregate plus nine task-level comparisons. Under aligned semantic acceptance, Goldilocks 0.5.0, Direct, Goldilocks 0.4.2, and Superpowers 6.1.1 each passed 3/3; the table also reports 0.5.0's measured 36.79% aggregate time cost versus Direct instead of hiding the slower result.
- Split setup into the independent, one-time `goldilocks-bootstrap` Skill. Codex CLI and Desktop prefer the native Plugin; portable Skills are fallback. The main router never invokes Bootstrap during ordinary work. Bootstrap can complete a Skills-only Codex install with the native plugin and four companion agents, then hand off duplicate portable-entry cleanup, one explicit Hook-trust choice, and a new task after a successful check.
- Localized the user-visible route receipt to the user's current language. It now reports host-confirmed team/concurrency, delegated work, retained Lead work, reason, detail, and fallback; fixed English readiness fields and reason codes remain in a hidden canonical audit record.
- Standardized defect reporting across the root gate, Diagnose, delegated handoffs, and the packaged worker: state the evidence-backed cause or explicitly unknown, then the fix and fresh verification, with more causal detail on request.
- Moved Usage reporting entirely out of Lead acceptance. A five-second, fail-silent `Stop` Hook emits available per-model totals; missing or read-only telemetry is omitted without retries, reporter diagnosis, or delaying delivery.
- Split the public documentation by audience: professional English and Chinese product pages retain the decision flow, durable-document structure, model guidance, and full release matrix; a comprehensive, evidence-dense `docs/AGENT-GUIDE.md` supports AI evaluation. The guide is deliberately not an auto-loaded `AGENTS.md`, so it adds no routine repository-instruction tax.
- Documented reusable benchmarking lessons on harness classification, host-side telemetry, semantic acceptance, interactive workflow handling, cost accounting, and non-rerun discipline.

The release evidence is limited to its frozen tasks. Spark has no public numeric rate: the published comparison cost is an authorization-normalized estimate, not an actual bill. Bootstrap never writes Hook-trust state or bypasses it; Codex records the final choice. `/hooks` is a fallback when startup review did not appear or for later verification.

The prerelease entries below preserve the routing decisions made at the time; the stable v0.5.0 role structure above supersedes them.

## 0.5.0-alpha.2 — 2026-08-07

### Weighted-Cost Routing and Reused-Agent Usage

- Moved the current Codex same-mix cost seed into the always-read Route Card: Luna is 4% and Terra 40% of Sol; Spark remains a separate unpriced allowance pool.
- Required every independent ready unit to be priced before Direct. Shared writes no longer justify withholding read-only work, and generic “extra tokens” or Lead convenience no longer qualifies as `review_cost` evidence.
- Preserved Lead ownership of intent, authority, shared writes, integration, and final acceptance while making inexpensive read-only or bounded Fast work easier to dispatch.
- Fixed Usage receipts for `followup_task` reactivations. Reused completed agents now contribute only their new completed task-segment deltas instead of disappearing or charging lifetime totals.
- Added regression coverage for weighted Direct decisions and reused-agent accounting while keeping the capability-documentation budget below its existing limit.

This prerelease changes no Hook permissions. Codex may still request renewed Hook trust after installing a new plugin version or cache copy.

## 0.5.0-alpha.1 — 2026-08-07

### Cost-aware field-test routing

- Added opt-in global authorization for bounded Fast and Standard delegation; new model/profile creation still requires explicit user consent.
- Added a visible, fixed-category route rationale and a zero-burden audit so Direct decisions can be reviewed without creating extra probes, documents, tests, or model calls.
- Required every ready unit to be evaluated for Fast before Standard. Codex uses Luna for general Fast work, Spark for deterministic coding batches, Terra for bounded judgment, and Sol for Lead authority and integration when those routes are available.
- Standardized child names as `<tier>__<task>_<model>` and added dynamic suffixes for other providers such as DeepSeek, Kimi, and Qwen.
- Added recursive per-model Usage receipts for Lead, native children, and external Fast workers. Missing host usage stays unavailable rather than being estimated or reported as zero.
- Preserved the pre-final Usage instruction after automatic or manual context compaction, including turns without a continuity ledger.
- Resolved the active plugin at receipt time so a mid-task cache/version replacement cannot invalidate an already-injected Usage command.
- Added causal transparency for defect work: cause—or explicitly unknown—fix, and verification remain visible despite lean output, with more detail on request.

This prerelease is intended for real-project feedback. Routing and Usage behavior may vary with host model availability, billing pools, transcript events, and Hook trust; use `v0.4.2` when only the stable defect-explanation fix is wanted.

## 0.4.5 — 2026-07-31

### Cheaper Fast and Standard Routing That Actually Closes

- Made GPT-5.6 Luna the universal Codex Fast baseline for focused coding, tests, exploration, extraction, routing, automation, and bounded content production after its July 31 price and allowance change.
- Kept GPT-5.3-Codex-Spark as the separately metered text-code specialist for deterministic coding batches, rather than treating it as the default for every coding task.
- Made GPT-5.6 Terra the Standard baseline for bounded domain judgment and local integration. Low-risk, objectively checkable Standard-boundary work may probe Luna once before upgrading.
- Preserved GPT-5.6 Sol for Lead, architecture, Critical work, shared decisions, final integration, and combined acceptance. Price still cannot bypass capability, tool, modality, authority, privacy, or quality gates.
- Strengthened the zero-cost gate: visibly multi-unit implementation now performs one constant-time make-or-delegate comparison before Lead edits. Direct remains valid when briefing and review cost more.
- Audited recent local project sessions. The root Hook was active, but recent development work did not dispatch Luna, Terra, or Spark; later children still inherited Sol. Historical records proved all three routes had worked earlier, while no worker had a Lead-verified pass recorded.
- Added `record_routing_outcome.py` so worker stops remain observations until Lead reruns combined acceptance and closes them as `verified_pass` or `verified_fail`. The recorder is idempotent, rejects mismatched or contradictory routes, and stores only an evidence hash.
- Extended Fast leaf enforcement to Luna and any native worker recorded as Fast, while preserving normal tools and Standard's bounded delegation role.
- Updated the adapter to use explicit `luna` and `spark-coding` work types, with `general` and `coding` retained as compatibility aliases.
- Refreshed the machine-readable model registry, bilingual routing note, installation guidance, and regression coverage. Older benchmark prices remain historically unchanged.

## 0.4.4 — 2026-07-29

### Earned Continuity for Repeated Failures

- Added a hard persistence boundary on the second user-confirmed recurrence in the same session and workspace. Before another patch, Goldilocks requires one live `.goldilocks/ACTIVE.md` frontier and the project's existing debug or validation record.
- Preserved symptom, evidence, disproven attempts, **Do not repeat**, exact next test, and related commits so compaction or handoff does not force another agent to reconstruct failed work from chat.
- Kept documentation selective: routine Direct work still creates no workflow files, and obvious or transient failures still need no debug note.
- Separated release history from debugging memory. Unverified fixes remain out of Changelog; freshly verified user-visible release changes may enter the repository's established Changelog, while failed attempts stay in the debug record.
- Added privacy-preserving recurrence flags and continuity-debt state to the existing hashed gate audit, including an in-place migration from v0.4.3 databases. Prompt text is still never stored.
- Added resume and post-compaction recovery when continuity debt exists but a previous turn failed to create the frontier.
- Added regression coverage for Chinese repeated-failure detection, audit migration and idempotency, worker silence, continuity-debt recovery, Changelog boundaries, and no prompt retention.

## 0.4.3 — 2026-07-28

### Reliable Root Invocation

- Fixed a real activation gap: specialist Skills could previously be selected without Goldilocks ever running its root decision gate.
- Added a compact `UserPromptSubmit` gate before specialist Skills. Pure conversation skips it, clear work stays Direct without loading the full router, and material uncertainty, unknown cause, multi-stage continuity, or useful decomposition explicitly loads `goldilocks:goldilocks`.
- Added a privacy-preserving local audit of gate delivery. It stores session/turn identifiers, timestamps, and prompt/workspace hashes in the existing plugin database; prompt text is never retained.
- Added unknown causality to the root gate so focused debugging cannot incorrectly fall through as clear Direct work.
- Added regression coverage for gate injection, specialist-Skill precedence, audit idempotency, worker silence, prompt privacy, and the existing sub-300-word router budget.

## 0.4.2 — 2026-07-26

### General Adaptive Invocation

- Broadened the single `goldilocks` trigger from explicit project-workflow requests to any executable work, including software, research, analysis, documents, presentations, spreadsheets, and other structured deliverables.
- Enabled implicit invocation while preserving the zero-cost Direct gate: clear work still loads no internal engine, creates no workflow residue, and announces no route.
- Clarified that Goldilocks coordinates workflow and acceptance across domains; specialist Skills remain responsible for domain-specific production.
- Kept non-coding orchestration experimental. The router may choose Direct for short, inseparable, or holistic creative work instead of forcing delegation.
- Added a copy-paste AI installation prompt and documented why Codex may request Hook approval again after install or update, what each Hook does, its network boundary, and the effect of declining it.
- Moved installation ahead of the capability tour so new users can act before reading the implementation details.
- Clarified the searchable project summary with the bounded v0.4.1 Direct A/B result: 114/114 checks on both paths, 11.5% fewer processing tokens, 10.9% less cumulative time, and 6.3% lower official GPT-5.6 Sol Standard token cost.

No new domain-production engine was added; this release broadens eligibility, not mandatory process.

## 0.4.1 — 2026-07-26

### Thin Adaptive Superpowers Replacement

- Consolidated the complete workflow surface into one visible `goldilocks` Skill. Align, Diagnose, Build, Orchestrate, Prove, Evolve, and the explicit Artifacts profile remain progressively disclosed internal engines.
- Made Direct a hard, silent exit for clear work. No workflow reference, continuity state, delegation ceremony, or route announcement is loaded unless a concrete trigger earns it.
- Added a 26-word decision-first communication contract influenced by Caveman and i-have-adhd (ADHD): result first, no work preambles or repeated state, concise decisive logs, and full wording for safety or ambiguity.
- Preserved deliberate brainstorming, compact specs and plans, TDD, root-cause debugging, worktrees, review, verification, idea capture, and safe branch completion without requiring them on every task.
- Kept durable project memory conditional: `docs/PROJECT.md`, `docs/work/`, `docs/debug/`, `docs/ideas.md`, `CHANGELOG.md`, and `.goldilocks/ACTIVE.md` appear only when continuity or correctness justifies them.
- Retained dynamic Lead → Standard → Fast orchestration. Lead owns intent, architecture, integration, and final acceptance; Standard owns bounded domain judgment; Fast receives a complete low-discretion contract and remains a leaf.
- Added work-type-aware Codex routing: Fast coding prefers `gpt-5.3-codex-spark`; Fast general non-coding prefers `gpt-5.6-luna`. Native supported models are preferred, with `dispatch_codex_worker.py` and `codex exec` as the packaged fallback.
- Added ready-route failure economy and context-lean worker evidence. Delegation starts only on a verified route; transport startup failures return to Direct or another proven route instead of consuming the product task on adapter repair.
- Retained explicit structured-artifact orchestration through one global Artifact Contract, replaceable unit contracts, localized rework, one integration owner, and global QA. Specialist production Skills remain responsible for authoring quality.
- Kept quiet update awareness for native Codex installs: at most one GitHub check per day, silence when current or offline, one reminder per newer release, and no automatic update without approval.

### Verification

- Added deterministic contracts for the single-Skill surface, sub-300-word router, Direct exit, lean communication, cross-version worker leaf switch, Spark/Luna routing, context-lean evidence, route-failure behavior, continuity, Artifacts, manifests, bilingual documentation, and third-party attribution.
- Certified the Direct branch on simple, moderate, and complex coding fixtures with GPT-5.6 Sol at high reasoning, fresh repositories, hidden deterministic acceptance, simultaneous Direct/Goldilocks waves, and excluded warm-ups.
- Both arms passed all 114/114 external checks. Across eleven runs per arm, Goldilocks used 10.9% less cumulative time, 6.3% less official GPT-5.6 Sol Standard token cost, and 11.5% fewer processing tokens.
- Retained the published Goldilocks/Superpowers evidence: 27/27 versus 8/27 successful Three Bears deliveries, plus the eight-scenario instruction stress test.

Goldilocks can better replace Superpowers on the tested workflow surface, but this release does not claim an absolute advantage across every possible workflow. More project tests and feedback are welcome.
