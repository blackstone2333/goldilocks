# Project Structure Contract

> Keep only sections that clarify durable boundaries. Update this document when the architecture changes, not after every edit.

## Purpose and boundaries

- What this project owns:
- What it explicitly does not own:
- External systems and trust boundaries:

## Target tree

```text
<show the meaningful directories and entry files>
```

## Responsibilities and dependencies

| Module or directory | Responsibility | May depend on | Must not depend on |
|---|---|---|---|
| | | | |

## Entry points and data flow

- Runtime entry points:
- Primary request/event/data flow:
- Persistence and external I/O:

## Tests

- Unit tests:
- Integration/contract tests:
- End-to-end or runtime checks:
- Fixtures and test helpers:

## Extension points

- Supported ways to add behavior:
- Stable interfaces or contracts:
- Decisions requiring an ADR:

## Structural guardrails

- Dependency direction:
- Ownership boundaries:
- Forbidden coupling:
- No generic `utils`/`helpers` dumping ground; shared code needs a named responsibility and owner.
