#!/usr/bin/env python3

"""Emit a small routing reminder plus continuity guidance when a ledger exists."""

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
        event = payload.get("hook_event_name")
        if event == "SessionStart":
            routing = (
                "Goldilocks routing: make one quick Direct-versus-delegate check before implementation. "
                "Lead owns intent, architecture, integration, and final acceptance. Send a complete "
                "execution contract to Fast; give bounded unresolved domain judgment to Standard, which "
                "may contract Fast. Fast is a leaf. Use an explicit host-supported native model, or the "
                "packaged Spark codex-exec adapter when native Spark is unavailable."
            )
            if ledger is not None:
                routing += (
                    f" Recovery state exists at {ledger}; read it, reconcile repository evidence, honor "
                    "applied steering and Do not repeat, then continue from Exact next action."
                )
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": routing,
                }
            }
        elif event == "UserPromptSubmit":
            if ledger is None:
                return
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
