# Lean output hid defect causes

## Symptom

After a repair, users could receive only the changed result and verification. They could not tell what had been wrong or why the change fixed it.

## Root cause

The v0.4.1 lean communication contract required changed state and decisive evidence but did not preserve a causal-explanation exception. Diagnose required causal reporting only for diagnosis-only requests, while Fast and Standard completion contracts omitted a cause field. A model could therefore diagnose internally and still produce a compliant black-box handoff.

## Fix

For defect work, Lead, Diagnose, Fast, and Standard must report the evidence-backed cause, or explicitly mark it unknown rather than guessing, followed by the fix and verification. Mechanical and feature work keep the existing lean output.

## Verification

- `python3 tests/test_recovery_hook.py`
- `python3 tests/test_codex_worker.py`
- `python3 tests/test_v041_lean_contract.py`
- `python3 tests/test_v045_model_routing_contract.py`

## Prevention

Contract tests require causal transparency in the Hook, root Skill, Diagnose engine, Fast briefing, and Standard handoff.

## Status

Included in `v0.5.0-alpha.1` for opt-in field testing; the focused stable repair ships separately in `v0.4.2`.
