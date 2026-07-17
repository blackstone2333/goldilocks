# Goldilocks

Not too much process. Not too little rigor. Just right.

Goldilocks is a Codex workflow suite packaged as a plugin. It applies **The Just-Necessary Principle**: use the minimum process that preserves a constant quality, safety, authorization, and verification floor.

The project is intended to replace ceremony-heavy workflow stacks rather than sit beside them. Feature parity does not require ceremony parity.

## Current status

- `v0.2.1`: complete Superpowers-compatible entry surface, conditional idea capture across every execution engine, and the Three Bears agentic benchmark.
- Public repository: https://github.com/blackstone2333/goldilocks

The plugin lives in `plugins/goldilocks/`. The trigger evaluation suite lives in `evals/` and defines expected mode, capability engines, user rounds, agent calls, evidence, and process-word budgets for 52 scenarios.

## Install the plugin

Add the public repository as a Codex marketplace, then install Goldilocks:

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

Start a new Codex thread after installation so the new skill context is loaded. During local development, this repository remains the source of truth; refresh the cachebuster and reinstall rather than editing a second plugin copy.

## Principle

**Minimum process. Constant quality.** A stronger worker may need fewer instructions; it does not get weaker acceptance criteria or evidence. Worktrees, plans, TDD, grilling, review, subagents, and parallelism are selected only when their expected value exceeds their coordination cost.

## Compatibility surface

Goldilocks exposes the familiar workflow entry names so it can replace Superpowers without copying fourteen long procedures:

- `brainstorming`
- `writing-plans`
- `executing-plans`
- `test-driven-development`
- `systematic-debugging`
- `using-git-worktrees`
- `dispatching-parallel-agents`
- `subagent-driven-development`
- `requesting-code-review`
- `receiving-code-review`
- `verification-before-completion`
- `finishing-a-development-branch`
- `writing-skills`

The explicit `goldilocks` router replaces `using-superpowers`. It is not implicitly injected, so trivial tasks pay no router cost. The thirteen compatibility entries route into six capability engines:

1. Align
2. Diagnose
3. Build
4. Orchestrate
5. Prove
6. Evolve

Each entry contains no more than 80 body words and loads only the engine needed for that task. See `docs/v0.2-capability-trigger-engine.md`.

Every execution engine also contains a lightweight idea-capture condition: adjacent ideas do not expand current scope, are preserved for the final handoff, and load Evolve only when classification or durable recording is actually needed.

## Local validation

```bash
python3 tests/test_v02_contract.py
```

The contract validates the exact 14-Skill surface, trigger scenarios, progressive-disclosure engines, and token budgets.

## Three Bears Benchmark

`benchmarks/three_bears/` generates fresh isolated repositories and compares baseline, Goldilocks, Superpowers, Ponytail, and Grill across Baby, Mama, and Papa difficulty levels. It gates correctness, safety, scope, reuse, and decision quality before comparing tokens, time, tool calls, and diff size.

```bash
python3 benchmarks/three_bears/run.py --selftest
python3 benchmarks/three_bears/run.py --task baby-docs --arms baseline,goldilocks --runs 1
```

See `benchmarks/three_bears/README.md` for the full reproducible matrix.

## License and influences

Goldilocks is MIT licensed. It is an independent implementation influenced by Superpowers, Grill-style decision-frontier questioning, and Ponytail's reuse/native-first approach. See `plugins/goldilocks/THIRD_PARTY_NOTICES.md`.
