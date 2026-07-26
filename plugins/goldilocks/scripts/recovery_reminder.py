#!/usr/bin/env python3

"""Inject a tiny response contract and continuity guidance when needed."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


MICRO_STYLE = (
    "Lead with the result. Omit work preambles, repeated plans, status, recaps, tangents, "
    "and oversized logs. Report only changed state; expand for safety, ambiguity, or "
    "decisive evidence."
)


def find_ledger(cwd: Path) -> Path | None:
    for directory in (cwd, *cwd.parents):
        candidate = directory / ".goldilocks" / "ACTIVE.md"
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None


def main() -> None:
    try:
        if os.environ.get("GOLDILOCKS_WORKER") == "1":
            return
        payload = json.load(sys.stdin)
        cwd = Path(payload.get("cwd") or os.getcwd()).expanduser().resolve()
        ledger = find_ledger(cwd)
        event = payload.get("hook_event_name")
        if event == "SessionStart":
            if ledger is None:
                return
            routing = (
                f"Recovery state exists at {ledger}; read it, reconcile repository evidence, honor "
                "applied steering and Do not repeat, then continue from Exact next action."
            )
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": routing,
                }
            }
        elif event == "UserPromptSubmit":
            message = MICRO_STYLE
            if ledger is not None:
                message += (
                    f" An active Goldilocks task ledger exists at {ledger}. Interpret this prompt "
                    "against its stable Objective as ADD, REPLACE, CANCEL, or QUESTION; after "
                    "handling it, mark the steering entry applied before continuing."
                )
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": message,
                }
            }
        elif event == "PostCompact":
            if ledger is None:
                return
            output = {
                "continue": True,
                "systemMessage": (
                    f"Goldilocks recovery required: read {ledger}, reconcile repository state, "
                    "and resume from Exact next action."
                ),
            }
        else:
            return

        print(json.dumps(output, ensure_ascii=False))
    except (OSError, ValueError, TypeError):
        # Continuity reminders are a guardrail; a broken hook must not block work.
        return


if __name__ == "__main__":
    main()
