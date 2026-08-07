# Changelog

[中文更新记录](CHANGELOG.zh-CN.md)

## 0.5.0-alpha.1 — 2026-08-07

### Cost-aware field-test routing

- Added opt-in global authorization for bounded Fast and Standard delegation; new model/profile creation still requires explicit user consent.
- Added a visible, fixed-category route rationale and a zero-burden audit so Direct decisions can be reviewed without creating extra probes, documents, tests, or model calls.
- Required every ready unit to be evaluated for Fast before Standard. Codex uses Luna for general Fast work, Spark for deterministic coding batches, Terra for bounded judgment, and Sol for Lead authority and integration when those routes are available.
- Standardized child names as `<tier>__<task>_<model>` and added dynamic suffixes for other providers such as DeepSeek, Kimi, and Qwen.
- Added recursive per-model Usage receipts for Lead, native children, and external Fast workers. Missing host usage stays unavailable rather than being estimated or reported as zero.
- Preserved the pre-final Usage instruction after automatic or manual context compaction, including turns without a continuity ledger.
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
