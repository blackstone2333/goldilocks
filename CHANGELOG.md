# Changelog

[中文更新记录](CHANGELOG.zh-CN.md)

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
