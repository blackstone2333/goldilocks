# Reuse and Planning

Understand the touched flow end to end before minimizing it. The shortest change in the wrong place is not efficient.

## Reuse ladder

Stop at the first rung that fully satisfies acceptance and safety:

1. **Need:** Does this need to exist now? Remove speculative work.
2. **Project existing:** Reuse an existing helper, component, script, test utility, asset, API, or configuration.
3. **Project pattern:** Extend the established pattern or extension point instead of creating a parallel system.
4. **Standard library:** Prefer maintained language or framework primitives.
5. **Native platform:** Prefer browser, OS, database, cloud, or hardware-platform capabilities.
6. **Installed ecosystem:** Use an already-installed dependency, animation library, component library, standard library package, or asset library when it fits.
7. **Minimum custom:** Write the smallest custom implementation that preserves the quality floor.

Before adding a dependency, check whether it is already installed, fits the current stack, is maintained enough for the risk, and avoids more ownership than it removes. Do not turn reuse selection into a research project for a trivial change.

For bugs, find the shared root cause and callers before patching symptoms. One correct fix at the common path is usually smaller and safer than repeated guards.

## Plan only to the useful depth

| Mode | Planning artifact |
|---|---|
| **Direct** | No separate plan; state a key assumption only if useful |
| **Guarded** | Short ordered plan with touched areas and focused checks |
| **Orchestrated overlay** | Add ownership, interfaces, integration order, and acceptance to the Guarded or Critical plan; never replace its quality requirements |
| **Critical** | Durable design/plan with authority, rollback, risk controls, and explicit approval |

A plan should reduce execution uncertainty. Do not repeat full implementation code, restate known context, or split setup/documentation into artificial microtasks. Create a durable document only when it supports handoff, long-running work, auditability, or costly decisions.

Prefer deletion over addition, boring over clever, and the fewest files that match project conventions. Never simplify away a trust-boundary check, accessibility requirement, security control, calibration needed by real hardware, or error handling that prevents data loss.
