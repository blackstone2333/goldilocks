# Goldilocks

Not too much process. Not too little rigor. Just right.

Goldilocks is a Codex workflow skill packaged as a plugin. It applies **The Just-Necessary Principle**: use the minimum process that preserves a constant quality, safety, authorization, and verification floor.

The project is intended to replace ceremony-heavy workflow stacks rather than sit beside them. Feature parity does not require ceremony parity.

## Current status

- `v0.1`: renamed, independently packaged baseline of the validated Just Necessary workflow.
- `v0.2`: Capability & Trigger Engine under RED evaluation before implementation.
- Public repository: https://github.com/blackstone2333/goldilocks
- A tagged release is intentionally deferred until the v0.2 trigger work reaches GREEN.

The plugin lives in `plugins/goldilocks/`. The trigger evaluation suite lives in `evals/` and defines expected mode, capability engines, user rounds, agent calls, evidence, and process-word budgets for 50 fresh-context scenarios.

## Install the plugin

Add the public repository as a Codex marketplace, then install Goldilocks:

```bash
codex plugin marketplace add blackstone2333/goldilocks
codex plugin add goldilocks@goldilocks-local
```

Start a new Codex thread after installation so the new skill context is loaded. During local development, this repository remains the source of truth; refresh the cachebuster and reinstall rather than editing a second plugin copy.

## Principle

**Minimum process. Constant quality.** A stronger worker may need fewer instructions; it does not get weaker acceptance criteria or evidence. Worktrees, plans, TDD, grilling, review, subagents, and parallelism are selected only when their expected value exceeds their coordination cost.

## v0.2 direction

Goldilocks compresses workflow coverage into six capability engines:

1. Align
2. Diagnose
3. Build
4. Orchestrate
5. Prove
6. Evolve

Thin explicit entry skills will preserve discoverability without loading an entire workflow stack. See `docs/v0.2-capability-trigger-engine.md`.

## Local validation

```bash
python3 tests/test_v02_contract.py
```

During the RED milestone this command is expected to fail on missing v0.2 engine and thin-entry files. The evaluation data and v0.1 plugin remain independently inspectable.

## License and influences

Goldilocks is MIT licensed. It is an independent implementation influenced by Superpowers, Grill-style decision-frontier questioning, and Ponytail's reuse/native-first approach. See `plugins/goldilocks/THIRD_PARTY_NOTICES.md`.
