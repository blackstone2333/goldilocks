# Changelog

[中文更新记录](CHANGELOG.zh-CN.md)

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
