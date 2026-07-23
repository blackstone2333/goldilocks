# Changelog

[中文更新记录](CHANGELOG.zh-CN.md)

## 0.3.0 — 2026-07-23

### Added — Hierarchical Orchestration

- Added a constant-time make-or-delegate check before expensive implementation. Clear work may stay Direct or become one complete Fast contract; larger work can use Lead→Fast, Lead→Standard, or Lead→Standard→Fast.
- Added Standard domain ownership. Standard can resolve bounded local design, dispatch Fast execution contracts inside that boundary, review the domain result, and return one coherent evidence packet to Lead.
- Added selective execution memory. Projects may preserve a verified route, preconditions, invalidators, organization depth, quota mix, elapsed time, retries, and acceptance evidence without using the release changelog as an internal database.
- Added six v0.3 routing scenarios covering Direct dispatch, nested delegation, post-decomposition Fast eligibility, quota-weighted routing, execution-memory reuse, and full-context Lead handoff.

### Changed

- Fast now means low residual discretion after decomposition, not mechanical code, small file count, or a small original project. A large implementation may be Fast-ready after Lead or Standard freezes its decisions and acceptance.
- Model selection now minimizes quota-weighted expensive usage and critical-path time after the quality gate, while total raw tokens stay inside a reasonable evidence-based envelope.
- Useful concurrency is no longer described by a fixed two-or-three-worker default. It is bounded by the ready dependency graph, host capacity, isolation, integration risk, and reviewer throughput.
- Lead owns user intent, shared interfaces, conflicts, combined verification, and final judgment. Lead implementation now needs a Direct, Critical-core, unblocking, or failed-worker reason rather than being the silent default.
- Full-history context is allowed only for an explicit Lead handoff that inherits the parent Lead model. Fast and Standard continue to use task-local contracts or at most four relevant turns.

### Routing guard and evidence

- Replaced unlocked JSONL matching with a standard-library SQLite audit store. Concurrent writes are atomic, starts bind by a unique model match when possible, and ambiguous concurrent or nested starts are recorded as unverifiable instead of producing a false mismatch.
- Fast workers are enforced as leaf executors. Standard and Lead route choices remain explicit; Spark rewriting still uses the separate Codex usage channel when eligible.
- Plugin data records observed completions separately from verified passes. A normal child stop never becomes successful execution memory without Lead acceptance.
- Added [deterministic RED/GREEN coverage](evals/results/2026-07-23-v030-hierarchical-orchestration.md) for Fast recursion, Lead full-history inheritance, out-of-order unique-model starts, ambiguous same-model starts, SQLite decisions/executions, Stop correlation, and true mismatch handling.
- v0.3.0 makes no new runtime performance claim. The acceptance target is quality non-inferiority with lower Lead quota share, bounded total-token change, shorter critical path where parallelism exists, and no increase in integration defects.

## 0.2.6 — 2026-07-23

### Added

- Added a native Codex **Agent Routing Guard** that intercepts `spawn_agent` before execution without changing user-level model defaults.
- Added explicit `fast__`, `standard__`, and `lead__` dispatch contracts. Fast calls are rewritten to `gpt-5.3-codex-spark`; Standard and Lead calls require an explicit model.
- Added expected-versus-actual model auditing through `SubagentStart`, stored in plugin data rather than the project. A mismatched child is instructed not to execute the delegated task.
- Added a [deterministic hook contract test](evals/results/2026-07-23-v026-routing-guard.md) covering unclassified calls, implicit and explicit full-history forks, oversized context forks, Spark rewriting, explicit Standard/Lead routing, successful audit, and mismatch handling.

### Changed

- Full-history subagent forks are blocked. Delegated work receives a task-local packet with `fork_turns="none"` or at most four recent turns.
- Worker repair loops stop after a second failure or requirement mismatch. One cohesive worker normally implements a bounded unit and its focused tests instead of duplicating context across micro-agents.
- Native Codex hard enforcement is separated from portable Skill guidance: Skill-only installs remain cross-platform but cannot intercept Codex tools.

### Compatibility and evidence

- The routing hooks require Codex trust review after installation or hook changes. Direct tasks remain unaffected because the guard runs only around subagent activity.
- v0.2.6 closes the observed v0.2.5 failure where five child agents silently inherited `gpt-5.6-sol` and full parent history. It does not claim a new performance result until real projects measure Lead quota, total tokens, wall-clock time, retries, and integration defects.

## 0.2.5 — 2026-07-20

### Added

- Extended the **Continuity Protocol** with a temporary, under-100-line `.goldilocks/ACTIVE.md` Execution Frontier for long tasks exposed to compaction, steering, waiting, delegation, or handoff.
- Added explicit `ADD`, `REPLACE`, `CANCEL`, and `QUESTION` steering semantics with `pending`, `applied`, and `superseded` lifecycle states.
- Added an exact-next-action and do-not-repeat recovery boundary, repository reconciliation, verification state, authority blockers, and terminal conditions.
- Added silent-by-default Codex recovery hooks plus an optional complete compaction-prompt asset.

### Changed

- Recovery now reads durable state first, checks Git and current files, and resumes from the first unfinished action instead of reconstructing work from chat salience.
- Direct work still creates no workflow state by default; the live ledger is activated only by observable continuity risk and is removed after useful outcomes are transferred.

### Compatibility and evidence

- Hooks are optional reminders and require Codex trust review; the ledger remains authoritative when hooks are delayed or unavailable.
- v0.2.5 is an experimental continuity release. One [fresh-context smoke test](evals/results/2026-07-20-v025-continuity-smoke.md) passed; the published runtime certification remains v0.2.2 while real projects test actual compaction recovery and non-repetition behavior.

## 0.2.4 — 2026-07-18

### Added

- Added a parallel-first routing pass after multi-unit plans: eligible independent work defaults to workers instead of silently accumulating on the Lead.
- Added task-specific model scoring based on a quality gate, public and local evidence, confidence, recency, expected cost per successful delivery, latency, and a Pareto shortlist.
- Added a Codex adapter that prefers `gpt-5.3-codex-spark` for eligible Fast text-only work when its separate usage limits are available.
- Added a dated public model registry and research survey covering independent coding benchmarks and official pricing sources across major providers.

### Changed

- Fast workers now preferentially receive mechanical implementation, test authoring, focused test execution, fixtures, and read-heavy exploration.
- Lead retains architecture, complex shared logic, Critical work, diff review, conflict resolution, combined verification, and final integration.
- Serial execution of an otherwise eligible multi-unit plan must state why coordination cost exceeds the saving.
- Public model rankings are advisory; local repository evidence and current host availability override the dated seed.

### Compatibility and evidence

- The visible surface remains fourteen Skills and six engines. Model routing is a shared protocol and zero-default-context registry asset.
- Existing published runtime certification remains the v0.2.2 result; v0.2.4 requires new real-project evidence before performance claims are expanded.

## 0.2.3 — 2026-07-18

### Added

- Added an on-demand **Continuity Protocol** for work that must survive sessions or transfer between humans and agents.
- Added proportional persistence: one compact work packet for ordinary multi-stage work, or split `spec.md`, `plan.md`, and `handoff.md` for Critical, Orchestrated, or substantial cross-session work.
- Added a project structure contract for new projects and architecture-level changes, covering directory layout, module ownership, dependency direction, entry points, data flow, test layout, extension points, and forbidden coupling.
- Added selective debug memory under the project's existing convention or `docs/debug/`, with search-before-debugging, root-cause notes, failed-attempt capture, regression-test links, and secret-safe recording rules.
- Added three optional templates: project map, work packet, and debug note.

### Changed

- Direct work no longer pays a default workflow-documentation cost. It still retains full autonomy to create or update normal documentation when documentation is the deliverable, project conventions require it, or correctness would otherwise suffer.
- Align, Build, Diagnose, Orchestrate, Prove, and Evolve now route to continuity only when durable state has positive value.
- Prove now checks that used specs, plans, project maps, debug links, idea ledgers, and handoffs remain current before completion.
- Codex, Claude Code, and cross-platform Skill metadata now report version `0.2.3`.

### Compatibility and evidence

- The public surface remains fourteen Skills backed by six engines; Continuity is a shared progressive-disclosure protocol, not another visible Skill.
- Existing published agentic certification remains the v0.2.2 result. v0.2.3 does not claim a new live benchmark result until the continuity behavior is tested on long-running projects and cross-agent handoffs.
