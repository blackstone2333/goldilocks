# Beta6 route speed versus Direct

One mature, independent-parallel development fixture is compared once per arm:
`patched-beta6` and `direct`. Both request `gpt-5.6-sol` at high reasoning effort
and standard service tier, with workspace-write and approval never.

The runner creates separate repo, HOME/CODEX_HOME, audit, and event directories per
arm. It copies no host trust, permission, or concurrency configuration; it only links
the authentication and model-cache files needed to execute. `patched-beta6` installs
the frozen local marketplace fixture; `direct` has no Goldilocks or Superpowers
installation. Each arm is exactly one attempt and has zero retries.

The frozen fixture is `tasks/parallel/`, copied from the mature 2026-08-12 parallel
task solely as source material. The plugin and marketplace fixture snapshot the current
Beta6 worktree. The runner aggregates every root and child rollout found under the
isolated CODEX_HOME. It records wall time, input/cached/output/raw tokens, tool calls,
verification tool calls, exact duplicate verification calls, actual service tier, and
cost. Sol/Terra/Luna use 5/0.5/6.25/30, 2/0.2/2.5/12, and
0.2/0.02/0.25/1.2 USD per million uncached input/cached input/cache write/output
tokens. Spark's official USD result is N/A and the separate normalized number uses
the Luna proxy. Raw Token is input plus output; cached input is a subset of input and
is not added again.

After each arm, the external quality gate runs exactly once: visible tests, hidden
tests, compile, diff whitespace, and scope/frozen-file check. If no actual service tier
is retained in rollout metadata, the elapsed time is marked observational. This is one
representative scenario, not a general benchmark claim.

Run only with explicit authority:

```sh
RUN_BETA6_FORMAL=1 python3 run.py --execute
```
