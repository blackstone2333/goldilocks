# Diagnose

Find the root cause before changing behavior. Diagnosis requests authorize evidence gathering, not automatically a fix.

## Evidence loop

1. Read the complete error, stack, logs, failing assertion, and nearby warnings. If the project has a debug knowledge base, search it by error, module, environment, and symptom.
2. Reproduce the symptom consistently, or characterize exactly when it occurs.
3. Inspect recent changes and trace the real call, data, state, and configuration flow end to end.
4. At each component boundary, compare expected input/output with observed evidence.
5. Form one falsifiable root-cause hypothesis and run the smallest experiment that distinguishes it from alternatives.
6. Record disproven hypotheses so they are not repeated.

Prefer existing logs, tests, traces, debuggers, profilers, and read-only queries. Add temporary instrumentation only where a boundary is otherwise opaque, and remove it unless it has lasting operational value.

## Fix the common cause

Locate all callers and affected paths before patching. Repair the earliest shared incorrect assumption or contract that explains the evidence. Avoid per-caller guards, broad rewrites, longer sleeps, retry inflation, or dependency upgrades unless the root cause specifically requires them.

For asynchronous failures, wait on the observable condition rather than elapsed time. For environment-only failures, compare versions, inputs, permissions, configuration, and runtime boundaries before changing code.

Capture a focused regression that fails for the observed reason when practical, then make the smallest fix and prove the regression passes. Read [build.md](build.md) for implementation choices and [prove.md](prove.md) for evidence depth.

When the root cause or failed attempts contain reusable, non-obvious knowledge, read [continuity.md](continuity.md) and update the existing debug record or create one after the fix. Revalidate old workarounds against current code; routine failures need no note.

After three failed fixes or disproven hypotheses, stop patching. Reassess the reproduction, assumptions, architecture, and worker capability; escalate to Lead judgment instead of trying a fourth speculative change or multiplying agents.

If the user asked only for diagnosis, stop with the causal chain, evidence, impact, and bounded fix options. Do not mutate source, configuration, production, or external systems.

If a useful adjacent idea appears but is not required for current acceptance, do not follow it. Preserve it for final handoff; read [evolve.md](evolve.md) only when classification or durable capture is needed.
