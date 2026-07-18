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
  <a href="https://skills.sh/blackstone2333/goldilocks"><img src="https://skills.sh/b/blackstone2333/goldilocks" alt="Install from skills.sh"></a>
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

## Evidence: Goldilocks vs Superpowers

Goldilocks makes one deliberately narrow public claim: it is a more reliable and more efficient **Superpowers replacement** on the tested workflow surface. Two evaluations support that claim without mixing design scores with runtime measurements.

### Test 1 — instruction-level stress test

The original design evaluation ran eight isolated scenarios. Goldilocks was still named `just-necessary`, so this is architectural lineage evidence rather than `v0.2.2` runtime evidence. The Goldilocks design averaged **98.9/100 versus 79.2/100**, led all eight scenarios, and used **86.2% less rule text**.

<p align="center">
  <img src="benchmarks/assets/instruction-stress-head-to-head.svg" width="960" alt="Instruction-level stress test: the Goldilocks predecessor leads Superpowers in all eight scenarios and uses 86.2 percent less rule text">
</p>

### Test 2 — real agentic certification

The current `v0.2.2` plugin was tested on GPT-5.6 Terra at low reasoning across nine Baby/Mama/Papa tasks, three fresh isolated runs per task, and 27 attempts per workflow. The complete exploratory experiment contained 135 valid turns; the published replacement claim uses only the **54 Goldilocks/Superpowers head-to-head turns**.

<p align="center">
  <img src="benchmarks/assets/agentic-certification-head-to-head.svg" width="960" alt="Real agentic certification: Goldilocks delivered 27 of 27 attempts versus 8 of 27 for Superpowers and used less cost per successful delivery on every measured dimension">
</p>

Goldilocks delivered **27/27** attempts with 100% measured safety; Superpowers delivered **8/27** with 88.9% safety. Nineteen Superpowers attempts stopped before changing source code, so raw totals alone would reward non-delivery.

On the eight exact cells both workflows completed, Goldilocks used 30.6% fewer total tokens, 7.7% less time, 28.6% fewer tool calls, and 66.7% less Skill activity. It used 9.7% more uncached input on that slice—the one comparable efficiency measure it did not win. Charging every attempt and dividing by successful deliveries, Goldilocks used 61.2% fewer total tokens, 70.5% less uncached input, 60.4% less time, 55.4% fewer tool calls, and 89.8% less Skill activity.

Read the [two-test head-to-head report](benchmarks/GOLDILOCKS-VS-SUPERPOWERS.md), the [full runtime certification](benchmarks/three_bears/results/2026-07-18-terra-low-full-certification.md), the [benchmark methodology](benchmarks/three_bears/README.md), the [head-to-head data](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/head-to-head.json), and the [complete per-cell audit data](benchmarks/three_bears/results/data/2026-07-18-terra-low-full/results.json).

## Install

Install the complete Superpowers-compatible suite with the cross-platform `skills` CLI:

```bash
npx skills add blackstone2333/goldilocks --skill '*' --global --agent codex --yes
```

Replace `codex` with `claude-code`, `cursor`, `opencode`, `github-copilot`, or `gemini-cli` for another agent. To install only the self-contained Just-Necessary router, use `--skill goldilocks` instead.

Native Codex plugin:

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

Native Claude Code plugin:

```bash
claude plugin marketplace add blackstone2333/goldilocks
claude plugin install goldilocks@goldilocks
```

Do not enable Goldilocks and Superpowers together. See the [complete installation guide](docs/installation.md) for project-local installs, updates, platform IDs, and compatibility details.

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
  --arms goldilocks,superpowers \
  --model gpt-5.6-terra \
  --reasoning low \
  --runs 1 \
  --workers 2
```

The full reproducible matrix is documented in [Three Bears](benchmarks/three_bears/README.md).

## Status and direction

Goldilocks remains at `v0.2.2`. Current evidence shows that it is a better replacement for Superpowers, but it does not have an absolute advantage across every possible workflow. We still need testing and feedback from more real projects; [issues and suggestions are welcome](https://github.com/blackstone2333/goldilocks/issues).

Next iterations will focus on:

- lowering Mama/Papa test and verification overhead without weakening quality gates;
- expanding the benchmark into larger repositories and additional languages;
- adding more repetitions before making broad public performance claims;
- preserving Superpowers entry compatibility while keeping the Direct path truly direct.

## License and influences

Goldilocks is MIT licensed and developed by Charles Roc and contributors. It is an independent implementation influenced by Superpowers, Grill-style decision-frontier questioning, and Ponytail's reuse/native-first approach. Those projects do not endorse Goldilocks. See [Third-Party Notices](plugins/goldilocks/THIRD_PARTY_NOTICES.md).
