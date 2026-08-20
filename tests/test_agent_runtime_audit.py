#!/usr/bin/env python3

"""Focused lifecycle regression for native rollouts missing SubagentStop."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INSPECTOR = ROOT / "plugins" / "goldilocks" / "scripts" / "inspect_agent_runtime.py"
GUARD = ROOT / "plugins" / "goldilocks" / "scripts" / "agent_routing_guard.py"
THREAD = "11111111-2222-4333-8444-555555555555"


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args], text=True, capture_output=True, check=False, env=env
    )


def start_unplanned_native(data: Path, thread: str, role: str, model: str, effort: str) -> None:
    env = os.environ.copy()
    env["PLUGIN_DATA"] = str(data)
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(
            {
                "hook_event_name": "SubagentStart",
                "session_id": "posthoc-parent",
                "turn_id": "posthoc-turn",
                "agent_id": thread,
                "agent_type": role,
                "model": model,
                "reasoning_effort": effort,
                "cwd": "/fixture",
                "sandbox_policy": {"type": "danger-full-access"},
                "permission_profile": {"type": "disabled"},
            }
        ),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr


def write_posthoc_rollout(
    sessions: Path, thread: str, role: str, model: str, effort: str, task_name: str, fork_turns: str
) -> None:
    records = (
        {
            "type": "session_meta",
            "payload": {
                "id": thread,
                "parent_thread_id": "posthoc-parent",
                "agent_role": role,
                "agent_path": f"/root/{task_name}",
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": model,
                "effort": effort,
                "sandbox_policy": {"type": "danger-full-access"},
                "permission_profile": {"type": "disabled"},
                "cwd": "/fixture",
                "fork_turns": fork_turns,
            },
        },
    )
    (sessions / f"rollout-posthoc-{thread}.jsonl").write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )


def test_posthoc_fork_contract(root: Path) -> None:
    sessions = root / "posthoc-sessions"
    sessions.mkdir()
    data = root / "posthoc-data"
    data.mkdir()
    roles = {
        "spark": ("goldilocks_spark_worker", "gpt-5.3-codex-spark", "xhigh", "fast"),
        "luna": ("goldilocks_luna_economy", "gpt-5.6-luna", "max", "fast"),
        "terra": ("goldilocks_terra_engineer", "gpt-5.6-terra", "medium", "standard"),
        "sol": ("goldilocks_sol_reviewer", "gpt-5.6-sol", "high", "lead"),
    }
    cases = (
        ("11111111-2222-4333-8444-000000000001", "spark", "none", True),
        ("11111111-2222-4333-8444-000000000002", "luna", "none", True),
        ("11111111-2222-4333-8444-000000000003", "terra", "none", True),
        ("11111111-2222-4333-8444-000000000004", "terra", "1", True),
        ("11111111-2222-4333-8444-000000000005", "terra", "4", True),
        ("11111111-2222-4333-8444-000000000006", "sol", "none", True),
        ("11111111-2222-4333-8444-000000000007", "spark", "1", False),
        ("11111111-2222-4333-8444-000000000008", "luna", "all", False),
        ("11111111-2222-4333-8444-000000000009", "terra", "5", False),
        ("11111111-2222-4333-8444-000000000010", "terra", "all", False),
        ("11111111-2222-4333-8444-000000000011", "sol", "1", False),
    )
    for thread, name, fork_turns, valid in cases:
        role, model, effort, tier = roles[name]
        start_unplanned_native(data, thread, role, model, effort)
        write_posthoc_rollout(
            sessions, thread, role, model, effort, f"{tier}__posthoc_{name}_{thread[-1]}_{name}", fork_turns
        )
        result = run(
            str(INSPECTOR), thread, "--sessions-dir", str(sessions), "--data-dir", str(data), "--record"
        )
        with sqlite3.connect(data / "orchestration.db") as connection:
            decisions = connection.execute(
                "SELECT COUNT(*) FROM decisions WHERE agent_id = ?", (thread,)
            ).fetchone()[0]
            execution = connection.execute(
                "SELECT decision_id, correlation_confidence, sandbox_policy_type, permission_profile_type "
                "FROM executions WHERE agent_id = ?",
                (thread,),
            ).fetchone()
        if valid:
            assert result.returncode == 0, result.stderr
            assert decisions == 1
            assert execution[0] is not None and execution[1] == "posthoc_role_observed"
            assert execution[2:] == ("danger-full-access", "disabled")
        else:
            assert result.returncode != 0
            assert "fork_turns" in result.stderr and decisions == 0
            assert execution[:2] == (None, "name_unverified")


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
        test_posthoc_fork_contract(root)
    print("Goldilocks native runtime completion reconciliation passed.")


if __name__ == "__main__":
    main()
