#!/usr/bin/env python3

"""Focused lifecycle regression for direct runtime completion reconciliation."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "plugins" / "goldilocks" / "scripts" / "inspect_agent_runtime.py"
THREAD = "11111111-2222-4333-8444-555555555555"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], text=True, capture_output=True, check=False
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        sessions = root / "sessions"
        sessions.mkdir()
        rollout = sessions / f"rollout-fixture-{THREAD}.jsonl"
        records = [
            {
                "type": "session_meta",
                "payload": {
                    "id": THREAD,
                    "parent_thread_id": "parent-session",
                    "agent_role": "goldilocks_terra_engineer",
                    "agent_path": "/root/standard__runtime_audit_terra",
                },
            },
            {
                "type": "turn_context",
                "payload": {
                    "model": "gpt-5.6-terra",
                    "effort": "medium",
                    "sandbox_policy": {"type": "danger-full-access"},
                    "permission_profile": {"type": "disabled"},
                    "cwd": "/fixture",
                    "fork_turns": "none",
                },
            },
            {
                "timestamp": "2026-08-20T01:02:03+00:00",
                "type": "event_msg",
                "payload": {"type": "task_complete"},
            },
        ]
        rollout.write_text("\n".join(json.dumps(record) for record in records) + "\n")
        data = root / "data"
        data.mkdir()
        with sqlite3.connect(data / "orchestration.db") as connection:
            connection.executescript(
                """
                CREATE TABLE decisions (
                    decision_id TEXT PRIMARY KEY, status TEXT, actual_model TEXT,
                    agent_id TEXT, stopped_at TEXT
                );
                CREATE TABLE executions (
                    agent_id TEXT PRIMARY KEY, decision_id TEXT, actual_agent_type TEXT,
                    actual_model TEXT, actual_effort TEXT, sandbox_policy_type TEXT,
                    permission_profile_type TEXT, input_tokens INTEGER,
                    cached_input_tokens INTEGER, output_tokens INTEGER, stopped_at TEXT
                );
                """
            )
            connection.execute(
                "INSERT INTO decisions VALUES ('decision-1', 'started', NULL, ?, NULL)",
                (THREAD,),
            )
            connection.execute(
                "INSERT INTO executions VALUES (?, 'decision-1', NULL, '', NULL, NULL, NULL, NULL, NULL, NULL, NULL)",
                (THREAD,),
            )
        result = run(
            str(INSPECTOR), THREAD, "--sessions-dir", str(sessions), "--data-dir", str(data), "--record"
        )
        assert result.returncode == 0, result.stderr
        with sqlite3.connect(data / "orchestration.db") as connection:
            execution = connection.execute("SELECT stopped_at FROM executions").fetchone()
            decision = connection.execute("SELECT status, stopped_at FROM decisions").fetchone()
        assert execution == ("2026-08-20T01:02:03+00:00",)
        assert decision == ("stopped", "2026-08-20T01:02:03+00:00")
    print("Goldilocks native runtime completion reconciliation passed.")


if __name__ == "__main__":
    main()
