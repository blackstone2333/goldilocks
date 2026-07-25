# Goldilocks v0.3.3 Capability-Preserving Spark Evidence

Date: 2026-07-25  
Scope: external Fast worker capability regression

## Problem

v0.3.2 correctly made Spark a leaf but also disabled plugins, apps, and MCP. That conflated organizational authority with tool capability. A bounded Fast task may legitimately need GitHub, browser, documentation, or project-specific tools even though it must not delegate or change shared decisions.

The two existing real probes also showed weak economic justification for the restriction: the capability-disabled adapter reported 8,417 tokens, while the earlier ordinary Spark CLI probe reported 8,897. Roughly 480 reported tokens did not justify removing whole tool classes.

## RED

`tests/test_codex_worker.py` was changed to require:

- `agents.enabled=false` remains in the generated command;
- no `--disable` feature flags are injected;
- `plugins`, `apps`, and `mcp_servers={}` are absent from adapter overrides.

The test failed against v0.3.2 because the command still included those restrictions.

## GREEN

The adapter now emits only the organizational override:

```text
-c agents.enabled=false
```

It preserves the user's normal plugin, App, and MCP configuration. Existing sandbox choices, explicit Spark model selection, safe stdin contract transfer, result-file support, failure propagation, and no-silent-fallback behavior remain unchanged.

## Boundary

Capability is not authority. Fast still receives a complete bounded contract, cannot create subagents, cannot broaden scope or change architecture/shared interfaces, and remains subject to the host's normal tool availability, sandbox, and permission gates.
