#!/usr/bin/env python3

"""Emit small Codex hook reminders only when an active Goldilocks ledger exists."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


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
        payload = json.load(sys.stdin)
        cwd = Path(payload.get("cwd") or os.getcwd()).expanduser().resolve()
        ledger = find_ledger(cwd)
        if ledger is None:
            return

        event = payload.get("hook_event_name")
        if event == "SessionStart":
            message = (
                f"Goldilocks recovery state exists at {ledger}. Before acting, read it, "
                "reconcile it with repository evidence, honor applied steering and Do not "
                "repeat, then continue from Exact next action."
            )
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": message,
                }
            }
        elif event == "UserPromptSubmit":
            message = (
                f"An active Goldilocks task ledger exists at {ledger}. Interpret this prompt "
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
