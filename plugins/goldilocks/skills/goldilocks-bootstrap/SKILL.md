---
name: goldilocks-bootstrap
description: Use only when installing, upgrading, or repairing the Goldilocks Skill and Codex native-host pack. Never invoke for ordinary task execution, routing, planning, or delivery.
---

# Goldilocks Bootstrap

Use this one-time Skill only when the user asks about installing, upgrading, or repairing
Goldilocks. Read [bootstrap.md](references/bootstrap.md), run `scripts/bootstrap.py`
for the read-only plan, and obtain the required explicit approval before applying it.
Do not invoke this Skill for ordinary tasks. Bootstrap only hands Hook trust back to the
Codex host review UI; it never writes host trust state or runs an aggressive bypass.
