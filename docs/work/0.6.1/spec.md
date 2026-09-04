# Goldilocks 0.6.1 specification

```yaml
version: 0.6.1
status: confirmed
date: 2026-09-04
```

## Outcome

Make execution-time steering natural without weakening the existing Direct-first, no-Hook workflow.

- A new task enters alignment, then the minimum necessary route.
- A message received while work is in progress is not treated as a second new task.
- If it does not materially affect the current goal, scope, order, authority, or acceptance, answer or absorb it and resume the same execution point.
- If it does, interpret its meaning in context: pause, stop, change, strengthen, or re-plan. Ask only when a material ambiguity remains; update only records affected by that decision.

## Non-goals

- Do not restore Hook, global compaction prompts, automatic reminders, or a user-visible fixed message taxonomy.
- Do not change Direct's independent domain-Skill matching or the existing record-event boundaries.

## Acceptance

- Root workflow wording and both public diagrams express the two-entry model and the material-impact threshold.
- No public `NEW / QUESTION / ADD` formula remains as an operating requirement.
- Plugin, marketplace, Bootstrap, installation instructions, changelog, and release contract consistently identify `0.6.1`.
