<p align="center">
  <img src="plugins/goldilocks/assets/logo.png" width="176" alt="A warm bowl of porridge, the Goldilocks logo">
</p>

<h1 align="center">Goldilocks</h1>

<p align="center"><strong>Not too much process. Not too little rigor. Just right.</strong></p>

<p align="center">
  <a href="README.md">English</a> · <a href="README.zh-CN.md">简体中文</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-0.2.2-D4A72C" alt="Version 0.2.2">
  <img src="https://img.shields.io/badge/Three_Bears-27%2F27_passed-2ea44f" alt="Three Bears: 27 of 27 Goldilocks cells passed">
  <img src="https://img.shields.io/badge/license-MIT-2563eb" alt="MIT License">
</p>

Goldilocks is a Codex workflow plugin built around the **Just-Necessary Principle**:

> Use the minimum process that preserves a constant quality, safety, authorization, and verification floor.

It provides a Superpowers-compatible workflow surface without requiring every task to pay for the entire workflow stack. Brainstorming, plans, TDD, debugging, worktrees, delegation, review, verification, branch finishing, and skill authoring remain available; each is loaded only when the task earns it.

## Why Goldilocks

- **Dynamic depth:** Direct, Fast, Lead, and Critical work receive different amounts of process while keeping the same acceptance standard.
- **Progressive disclosure:** thirteen compatibility entries route into six shared engines instead of duplicating fourteen long procedures.
- **Native and reuse first:** inspect the project, standard library, established helpers, and proven libraries before inventing new machinery.
- **Decision-frontier questions:** ask only when an answer can materially change the end state, safety, scope, or authorization.
- **Ideas without scope creep:** useful adjacent ideas are preserved for later rather than silently expanding the current task.
- **Evidence before completion:** confidence, old test output, and agent reports never replace fresh evidence for material claims.

## Current evidence

Goldilocks `v0.2.2` completed the full Three Bears matrix on GPT-5.6 Terra at low reasoning:

- 9 tasks across Baby, Mama, and Papa difficulty;
- Baseline, Goldilocks, Superpowers, Ponytail, and Grill arms;
- 3 fresh isolated runs per task/arm cell;
- 135 valid model turns, 0 infrastructure failures;
- 10,645,012 telemetry tokens across the complete matrix.

| Arm | Quality | Safety | Successful turns | Total tokens | Uncached input | Skill activity |
|---|---:|---:|---:|---:|---:|---:|
| **Goldilocks** | **27/27** | **100%** | **27** | 3,031,688 | 474,546 | 30 |
| Baseline | 27/27 | 100% | 27 | 1,629,610 | 326,595 | 0 |
| Grill | 27/27 | 100% | 27 | 1,653,856 | 262,677 | 3 |
| Ponytail | 26/27 | 100% | 26 | 2,015,197 | 305,021 | 27 |
| Superpowers | 8/27 | 88.9% | 8 | 2,314,661 | 476,286 | 87 |

The raw Superpowers totals look cheaper because 19 cells stopped before changing code, usually to request approval for an already specified implementation detail. On the eight cells both Goldilocks and Superpowers completed successfully, Goldilocks used 30.6% fewer total tokens, 7.7% less time, 28.6% fewer tool calls, and 66.7% less Skill activity, while using 9.7% more uncached input.

Goldilocks is not the cheapest arm in this suite. Against Baseline it used 86.0% more cumulative total tokens and 34.9% more time. Reducing that quality-preserving overhead is the main `v0.2.x` optimization target.

Read the [full certification report](benchmarks/three_bears/results/2026-07-18-terra-low-full-certification.md), the [benchmark methodology](benchmarks/three_bears/README.md), and the [per-cell published data](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/).

## Install

Add this repository as a Codex marketplace, then install the plugin:

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

Start a new Codex task after installation so the new Skill context is loaded.

## What ships

Goldilocks exposes the familiar workflow entry names needed to replace Superpowers:

| Need | Entry |
|---|---|
| Align on an uncertain end state | `brainstorming` |
| Produce or execute an implementation plan | `writing-plans`, `executing-plans` |
| Build with focused tests | `test-driven-development` |
| Diagnose before patching | `systematic-debugging` |
| Isolate or divide work | `using-git-worktrees`, `dispatching-parallel-agents`, `subagent-driven-development` |
| Request or process review | `requesting-code-review`, `receiving-code-review` |
| Prove completion and finish a branch | `verification-before-completion`, `finishing-a-development-branch` |
| Create or improve Skills | `writing-skills` |

The explicit `goldilocks` router replaces `using-superpowers`. It is intentionally not injected into every task, so trivial work can remain on the Direct path with zero workflow Skill reads.

The compatibility entries progressively disclose six shared engines:

1. **Align** — end state, material decisions, acceptance.
2. **Diagnose** — reproduction, trace, hypothesis, root cause.
3. **Build** — planning, focused TDD, coherent execution.
4. **Orchestrate** — worktrees, delegation, model routing, integration ownership.
5. **Prove** — review, verification, authorization, branch completion.
6. **Evolve** — idea capture, retrospection, and Skill improvement.

See [the v0.2 capability and trigger design](docs/v0.2-capability-trigger-engine.md).

## Validate locally

No model calls:

```bash
python3 tests/test_v02_contract.py
python3 tests/test_three_bears_contract.py
python3 benchmarks/three_bears/run.py --selftest
```

Low-cost live smoke test:

```bash
python3 benchmarks/three_bears/run.py \
  --task baby-docs \
  --arms baseline,goldilocks \
  --model gpt-5.6-terra \
  --reasoning low \
  --runs 1 \
  --workers 2
```

The full reproducible matrix is documented in [Three Bears](benchmarks/three_bears/README.md).

## Status and direction

Goldilocks remains `v0.2.2`. Passing this suite is evidence, not a claim of universal superiority or a reason to rush `1.0`.

Next iterations will focus on:

- lowering Mama/Papa test and verification overhead without weakening quality gates;
- expanding the benchmark into larger repositories and additional languages;
- adding more repetitions before making broad public performance claims;
- preserving Superpowers entry compatibility while keeping the Direct path truly direct.

## License and influences

Goldilocks is MIT licensed and developed by Charles Roc and contributors. It is an independent implementation influenced by Superpowers, Grill-style decision-frontier questioning, and Ponytail's reuse/native-first approach. Those projects do not endorse Goldilocks. See [Third-Party Notices](plugins/goldilocks/THIRD_PARTY_NOTICES.md).
