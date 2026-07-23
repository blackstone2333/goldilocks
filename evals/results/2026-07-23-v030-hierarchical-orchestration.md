# Goldilocks v0.3.0 hierarchical-orchestration contract test

- Date: 2026-07-23
- Scope: routing contract, native Codex guard, concurrency-safe audit, recovery compatibility, package structure
- Runtime performance certification: not claimed

## Target contract

v0.3.0 changes delegation from a flat task-size rule into a dynamic hierarchy:

- Lead keeps intent, architecture, shared interfaces, resource allocation, integration, and final quality.
- Standard owns one bounded domain and may delegate complete execution contracts inside it.
- Fast accepts low-discretion implementation contracts and remains a leaf.
- Routing minimizes quota-weighted expensive usage and critical-path time after quality and safety gates, while raw-token growth remains bounded.
- A previously verified execution pattern may bypass repeated planning only after a short invalidation check.

## Deterministic checks

Fresh checks passed for:

```text
Goldilocks v0.3 contract passed with 66 trigger cases.
Goldilocks v0.3.0 agent routing hook contract passed.
Goldilocks recovery hook contract passed.
Three Bears contract passed: 9 tasks, 5 arms, all reference instruments valid.
Three Bears instruments: valid; all five benchmark arms discoverable.
14/14 Skills valid.
Plugin validation passed.
Python compilation and Git whitespace checks passed.
```

The routing-hook suite covers Fast model rewriting, Fast leaf enforcement, explicit Standard routing, explicit full-history Lead handoff, out-of-order unique-model starts, ambiguous same-model starts, true mismatch handling, SQLite decision/execution correlation, Stop correlation, and the distinction between observed completion and verified success.

## Fixed regression

The v0.2.6 audit associated a child start with the latest unmatched plan. Concurrent or nested starts could therefore bind to the wrong decision and report a false model mismatch. v0.3.0 uses SQLite and binds automatically only when model correlation is unique. Ambiguous starts are preserved as observations without stopping or accusing a specific child.

## Boundary

These checks prove the declared files, routing rules, hook transformations, audit behavior, backward-compatible contracts, and package validity. They do not prove lower real-project quota burn, shorter elapsed time, bounded total tokens, or unchanged integration-defect rates. Those claims require repeated fresh-project comparisons with actual model usage and equivalent acceptance tests.
