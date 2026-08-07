# Ghost subagent queue can distort routing

## Symptom

After completed child tasks were reconciled and Codex restarted, manually opening an old child could make the UI show it as processing again. The concern is not token use but a Lead incorrectly treating those handles as occupied capacity and avoiding delegation.

## Evidence

- Codex state contained zero open spawn edges after cleanup.
- Host agent status contained only the root agent.
- No native or external worker process was running.
- The reopened historical rollout could still end with `task_started` and no durable `task_complete`, allowing the UI to reconstruct a misleading spinner.

## Root cause

The UI label and the routing truth are separate state surfaces. Goldilocks runtime auditing already excludes unclosed observations older than the Fast 30-minute or other-tier 90-minute lifecycle, but the prompt did not explicitly forbid Lead from copying a stale UI count into `EXISTING`.

## Fix

Define active ownership from current host status or a fresh runtime observation. A UI label, idle/completed handle, unverified artifact, or lone historical `task_started` is not active. Stale records remain cleanup debt but do not consume routing capacity unless the host confirms they are running.

## Verification

- `python3 tests/test_recovery_hook.py` — passed.
- `python3 tests/test_route_auditor.py` — passed with stale unclosed native and external fixtures excluded from active count.
- Skill Creator `quick_validate.py` — source and installed local Skill both valid.
- Installed Hook smoke check — injected `host-confirmed`, `not UI labels`, and `historical task_started` rules.

## Failed approach

Directly closing Codex internal `thread_spawn_edges` removes current queue entries but does not change immutable rollout history; reopening an old child can therefore restore the visual spinner. Internal database mutation is not a durable portable plugin fix.

## Status

Included in `v0.5.0-alpha.1` for opt-in field testing. The host UI may still render a stale spinner, but Goldilocks no longer counts it as active without current host confirmation.
