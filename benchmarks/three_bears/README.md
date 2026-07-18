# Three Bears Benchmark

An agentic benchmark for the public Goldilocks claim: can it replace Superpowers with more reliable delivery and less quality-adjusted workflow cost?

Every cell starts a real headless Codex session in a newly generated git repository. No task reuses a previous project's history, conversation, dependencies, working tree, or plugin cache. Workspaces and raw event streams are retained under `runs/` for audit and offline rescoring.

The randomized first cell doubles as a live model/account preflight. If it cannot complete a model turn, the matrix stops before launching the remaining cells. After preflight, only `--workers` cells remain in flight; an incomplete model turn stops new scheduling. Infrastructure failures are reported separately and excluded from quality and efficiency aggregates.

## Bears

| Level | What it tests | Tasks |
|---|---|---|
| Baby | Clear, local, reversible work where ceremony should disappear | README punctuation, standard-library UUID, existing-helper reuse |
| Mama | Ordinary implementation and debugging where focused process should pay for itself | shared empty-query bug, duplicate CSV headers, standard-library caching |
| Papa | Trust boundaries, authorization, and material design ambiguity | path traversal, immediate role revocation, offline-mode decision frontier |

Each task ships a good and bad reference. `--selftest` proves the good reference passes and the bad reference is caught before any model call.

## Arms

| Arm | Activation |
|---|---|
| `baseline` | No non-system workflow Skill |
| `goldilocks` | Current repository's 14 Skill directories; entries trigger only when applicable |
| `superpowers` | Original Superpowers directories plus explicit `using-superpowers` bootstrap |
| `ponytail` | Original Ponytail full mode on coding tasks; inactive on the design task |
| `grill` | Original Matt Pocock `grilling` primitive on the design task; inactive on coding tasks |

The conditional activation avoids pretending Ponytail is a general design interview or Grill is a coding workflow. All five arms remain available in one matrix.

The official product comparison is intentionally limited to `goldilocks` versus `superpowers`. The other arms remain available for independent exploration and are not ranked in the Goldilocks product claim.

By default the external source paths are sibling repositories already used during Goldilocks development:

- `../superpowers-clean-baseline/skills`
- `../ponytail/skills/ponytail`
- `../mattpocock-skills/skills/productivity/grilling`

Override them with `SUPERPOWERS_SKILLS`, `PONYTAIL_SKILL`, and `GRILL_SKILL`. Override Goldilocks with `GOLDILOCKS_SKILLS`.

## Metrics

Quality is read before efficiency:

- `quality`: deterministic correctness, safety, and allowed-scope gate;
- `safe`: adversarial trust-boundary or authorization behavior;
- `reuse`: existing helper or standard-library mechanism selected where required;
- `process`: the design task surfaces one material decision, recommends a default, and asks before architecture;
- `scope`: no unrelated file changes;
- input, cached, uncached, output, and total tokens from Codex telemetry;
- wall time, tool calls, Skill reads/injections, final questions, changed files, and added/deleted LOC.

Fewer tokens, seconds, or lines do not count as a win when any applicable quality gate falls. Tests written by the agent are tracked separately in `test_added_lines` and are not treated as source bloat.

## Run

The harness uses the bundled Codex CLI when available. Authentication is linked into a temporary home and never copied into a kept run. The selected provider from `$CODEX_HOME/config.toml` is reduced to a temporary provider-only config with mode `0600`; MCP servers, plugins, marketplaces, and unrelated user settings are not copied. Set `CODEX_BIN`, `THREE_BEARS_AUTH_HOME`, `THREE_BEARS_CODEX_CONFIG`, or `THREE_BEARS_MODEL_PROVIDER` when discovery differs on your machine.

Validate everything without a model call:

```bash
python3 benchmarks/three_bears/run.py --selftest
python3 tests/test_three_bears_contract.py
```

Preview a matrix without spending tokens:

```bash
python3 benchmarks/three_bears/run.py \
  --level all \
  --arms baseline,goldilocks,superpowers,ponytail,grill \
  --dry-run
```

Low-cost smoke comparison:

```bash
python3 benchmarks/three_bears/run.py \
  --task baby-docs \
  --arms goldilocks,superpowers \
  --model gpt-5.6-terra \
  --reasoning low \
  --runs 1 \
  --workers 2
```

Full Goldilocks/Superpowers certification:

```bash
python3 benchmarks/three_bears/run.py \
  --level all \
  --arms goldilocks,superpowers \
  --model gpt-5.6-terra \
  --reasoning low \
  --runs 3 \
  --workers 3
```

That command runs 54 isolated cells. Cell order is deterministically randomized (`--seed 1729`) to reduce warm-cache and ordering bias. Start with one run per cell before paying for repetitions. Report medians only after at least three runs; use five or more when making broad public performance claims. Always publish cached and uncached input separately: a single warm-cache imbalance can dominate both latency and apparent cost.

Optional exploratory five-arm matrix:

```bash
python3 benchmarks/three_bears/run.py \
  --level all \
  --arms baseline,goldilocks,superpowers,ponytail,grill \
  --model gpt-5.6-terra \
  --reasoning low \
  --runs 3 \
  --workers 3
```

That optional command runs 135 isolated cells. Its additional arms are available for readers to evaluate themselves; they are not part of the official Goldilocks-versus-Superpowers claim.

Recompute graders and summary tables without another model call:

```bash
python3 benchmarks/three_bears/run.py --rescore benchmarks/three_bears/runs/<timestamp>
```

Each run retains `metadata.json`, cell repositories, raw `events.jsonl`, stderr, per-cell results, `results.json`, `summary.json`, and `REPORT.md`.

Published head-to-head evidence:

- [Two-test Goldilocks versus Superpowers report](../GOLDILOCKS-VS-SUPERPOWERS.md)
- [2026-07-18 — Terra low runtime certification, 54-turn published head-to-head slice](results/2026-07-18-terra-low-full-certification.md)

## Interpretation limits

Nine tasks are a regression suite, not proof of universal superiority. The alignment task uses a deterministic behavioral rubric rather than a live multi-turn human conversation. Token figures include the Codex session context and should be compared only between cells using the same model, CLI build, machine, and benchmark revision. A public claim should publish the raw run directory, source commits, repetitions, failures, and variance—not only the winning median.
