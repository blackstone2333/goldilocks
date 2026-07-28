#!/usr/bin/env python3

"""Inject a tiny response contract and continuity guidance when needed."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


POLICY_VERSION = "0.4.3"
MICRO_STYLE = (
    "Lead with the result. Omit work preambles, repeated plans, status, recaps, tangents, "
    "and oversized logs. Report only changed state; expand for safety, ambiguity, or "
    "decisive evidence."
)
ROUTING_GATE = (
    "For executable work, silently apply the Goldilocks zero-cost gate before any specialist Skill. "
    "If material uncertainty, unknown cause, multi-stage continuity, or useful decomposition exists, "
    "read and use the goldilocks:goldilocks Skill; otherwise take its Direct exit. "
    "Skip the gate for pure conversation."
)


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def record_gate(payload: dict[str, object], cwd: Path, ledger: Path | None) -> None:
    """Record that the root gate was delivered without retaining prompt content."""

    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return
        root = Path(configured).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        session_id = str(payload.get("session_id") or "unknown-session")
        turn_id = str(payload.get("turn_id") or "unknown-turn")
        prompt = str(payload.get("prompt") or "")
        prompt_fingerprint = stable_hash(prompt)
        injection_id = stable_hash(f"{session_id}\n{turn_id}\n{prompt_fingerprint}")
        with sqlite3.connect(root / "orchestration.db", timeout=3) as connection:
            connection.execute("PRAGMA busy_timeout = 3000")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS gate_injections (
                    injection_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_id TEXT NOT NULL,
                    cwd_hash TEXT NOT NULL,
                    prompt_fingerprint TEXT NOT NULL,
                    ledger_present INTEGER NOT NULL,
                    injected_at TEXT NOT NULL,
                    policy_version TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT OR IGNORE INTO gate_injections (
                    injection_id, session_id, turn_id, cwd_hash, prompt_fingerprint,
                    ledger_present, injected_at, policy_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    injection_id,
                    session_id,
                    turn_id,
                    stable_hash(str(cwd)),
                    prompt_fingerprint,
                    int(ledger is not None),
                    datetime.now(timezone.utc).isoformat(),
                    POLICY_VERSION,
                ),
            )
    except (OSError, sqlite3.Error, TypeError, ValueError):
        # Auditability must never block or suppress the routing instruction.
        return


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
            record_gate(payload, cwd, ledger)
            message = f"{MICRO_STYLE} {ROUTING_GATE}"
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
