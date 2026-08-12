---
name: goldilocks-bootstrap
description: Use only when installing, upgrading, or repairing the Goldilocks Skill and Codex native-host pack. Never invoke for ordinary task execution, routing, planning, or delivery.
---

# Goldilocks Bootstrap

Use only when installing, upgrading, or repairing Goldilocks. Read
[bootstrap.md](references/bootstrap.md), run `scripts/bootstrap.py --plan --json`, and
obtain explicit approval before apply. Never use for ordinary tasks. Hook trust remains
host-controlled.

Bootstrap JSON exposes `usage_visibility`. Choose `on-demand` (default) or `automatic`
with `--usage-visibility`; successful apply records it. Automatic adds one fail-silent
read per executable turn; on-demand reads only after an explicit request. The environment
override is `GOLDILOCKS_USAGE_VISIBILITY`.
