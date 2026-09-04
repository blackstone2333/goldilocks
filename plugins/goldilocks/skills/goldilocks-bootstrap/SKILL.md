---
name: goldilocks-bootstrap
description: Use only when installing, upgrading, or repairing the Goldilocks Skill and Codex native-host pack. Never invoke for ordinary task execution, routing, planning, or delivery.
---

# Goldilocks Bootstrap

Use only when installing, upgrading, or repairing Goldilocks. Read
[bootstrap.md](references/bootstrap.md), run `scripts/bootstrap.py --plan --json`, and
obtain explicit approval before apply. Never use for ordinary tasks. Routing and
continuity remain carried by the Skill and `ACTIVE.md`; Goldilocks ships no Hook feature,
compact prompt, source, or trust path. Bootstrap is
an explicit, one-time install/upgrade/repair operation; it is not a runtime service and
does not run on ordinary turns.

Bootstrap never injects or changes a user compact prompt during ordinary installation.
