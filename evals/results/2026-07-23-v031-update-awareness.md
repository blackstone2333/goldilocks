# Goldilocks v0.3.1 quiet-update-awareness contract test

- Date: 2026-07-23
- Scope: native Codex update check, throttling, notification, failure behavior, Hook registration
- Automatic installation: intentionally not implemented

## RED baseline

`tests/test_update_checker.py` initially failed because `plugins/goldilocks/scripts/update_checker.py` did not exist. A second RED case showed that an HTTP 304 response lost the cached latest version after a local downgrade.

## Implemented contract

- Run only for native Codex `SessionStart` and at most once every 24 hours.
- Compare the installed semantic version with the public repository manifest.
- Use a short network timeout and ETag, with concurrency-safe state in plugin-data SQLite.
- Stay silent when current, throttled, disabled, malformed, timed out, or offline.
- Notify once for each newer version and include exact Codex update commands.
- Keep the active task on its loaded version and require explicit user approval before installation.
- Let portable Skill installs retain zero default network and startup-hook cost.

## Fresh deterministic checks

```text
Goldilocks update checker contract passed.
Goldilocks v0.3 contract passed with 66 trigger cases.
Goldilocks v0.3.0 agent routing hook contract passed.
Goldilocks recovery hook contract passed.
Python compilation and Git whitespace checks passed.
```

The update-checker suite uses a local HTTP server and covers a newer release, daily throttling, unchanged ETag, a second newer release, current installation, cached comparison after downgrade, explicit opt-out, offline failure, and silent Hook registration.

## Boundary

These checks prove deterministic client behavior without relying on GitHub availability. They do not prove that every host permits outbound GitHub access, that Codex will auto-install an update, or that portable Skill-only platforms can run a startup check. Network failure is an expected silent state; users can still update explicitly through their installation channel.
