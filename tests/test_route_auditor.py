#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDITOR = ROOT / "plugins" / "goldilocks" / "scripts" / "route_auditor.py"
HOOKS = ROOT / "plugins" / "goldilocks" / "hooks" / "hooks.json"


def append_route(path: Path, turn_id: str, timestamp: str, line: str) -> None:
    record = {
        "timestamp": timestamp,
        "type": "response_item",
        "payload": {
            "type": "message",
            "role": "assistant",
            "content": [{"type": "output_text", "text": line}],
            "internal_chat_message_metadata_passthrough": {"turn_id": turn_id},
        },
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def run(data: Path, transcript: Path, turn_id: str) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": "session-1",
        "turn_id": turn_id,
        "cwd": str(ROOT),
        "hook_event_name": "Stop",
        "transcript_path": str(transcript),
        "last_assistant_message": "done",
    }
    return subprocess.run(
        [sys.executable, str(AUDITOR)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PLUGIN_DATA": str(data)},
    )


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE gate_injections (
            injection_id TEXT PRIMARY KEY,
            session_id TEXT,
            turn_id TEXT,
            cwd_hash TEXT,
            routing_rationale_candidate INTEGER,
            routing_experiment_id TEXT,
            delegation_grant_active INTEGER,
            injected_at TEXT
        );
        CREATE TABLE decisions (
            decision_id TEXT PRIMARY KEY,
            session_id TEXT,
            cwd_hash TEXT,
            tier TEXT,
            expected_model TEXT
        );
        CREATE TABLE executions (
            agent_id TEXT PRIMARY KEY,
            decision_id TEXT,
            actual_model TEXT,
            started_at TEXT,
            stopped_at TEXT
        );
        CREATE TABLE external_routes (
            route_id TEXT PRIMARY KEY,
            parent_session_id TEXT,
            cwd_hash TEXT,
            expected_model TEXT,
            actual_model TEXT,
            status TEXT,
            started_at TEXT,
            stopped_at TEXT
        );
        """
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        data = root / "data"
        data.mkdir()
        database = data / "orchestration.db"
        transcript = root / "rollout.jsonl"
        cwd_hash = "a" * 64
        with sqlite3.connect(database) as connection:
            create_schema(connection)
            connection.execute(
                "INSERT INTO gate_injections VALUES "
                "('gate-a', 'session-1', 'turn-a', ?, 1, "
                "'routing-rationale-v3.2', 1, '2026-08-05T07:22:00+00:00')",
                (cwd_hash,),
            )
            connection.execute(
                "INSERT INTO external_routes VALUES "
                "('old-luna', 'old-session', ?, 'gpt-5.6-luna', 'gpt-5.6-luna', "
                "'succeeded', '2026-08-05T07:00:00+00:00', "
                "'2026-08-05T07:05:00+00:00')",
                ("other-project-route",),
            )
            connection.execute(
                "INSERT INTO decisions VALUES "
                "('stale-native', 'old-session', ?, 'standard', 'gpt-5.6-terra')",
                (cwd_hash,),
            )
            connection.execute(
                "INSERT INTO executions VALUES "
                "('stale-terra', 'stale-native', 'gpt-5.6-terra', "
                "'2026-08-05T05:00:00+00:00', NULL)"
            )
            connection.execute(
                "INSERT INTO external_routes VALUES "
                "('stale-spark', 'old-session', ?, 'gpt-5.3-codex-spark', '', "
                "'started', '2026-08-05T06:00:00+00:00', NULL)",
                (cwd_hash,),
            )

        bad_detail = (
            "Luna 和 Spark 当前不可调度，四个未验收结果与脏工作树共享接口面。"
        )
        append_route(
            transcript,
            "turn-a",
            "2026-08-05T07:23:00Z",
            "ROUTE=direct | WRITE_READY=5 | READ_READY=2 | EXISTING=4 | "
            "PLANNED_DISPATCH=0 | LEAD=M3集成与验收 | REASON=route_unavailable | "
            f"DETAIL={bad_detail}",
        )
        first = run(data, transcript, "turn-a")
        assert first.returncode == 0, first.stderr
        assert json.loads(first.stdout) == {}, "the audit must remain silent"
        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM route_audits WHERE turn_id = 'turn-a'"
            ).fetchone()
        assert row is not None
        assert row["claimed_existing"] == 4
        assert row["observed_active_agents"] == 0
        assert row["planned_dispatch"] == 0
        assert row["observed_dispatch"] == 0
        assert row["available_route_count"] == 1
        assert json.loads(row["review_flags"]) == [
            "authorized_ready_direct_with_available_route",
            "dirty_tree_rejected_read_only",
            "existing_above_observed_agents",
            "route_unavailable_conflicts_with_history",
        ]
        raw_database = database.read_bytes()
        assert bad_detail.encode() not in raw_database
        assert "M3集成与验收".encode() not in raw_database

        with sqlite3.connect(database) as connection:
            connection.execute(
                "INSERT INTO gate_injections VALUES "
                "('gate-b', 'session-1', 'turn-b', ?, 1, "
                "'routing-rationale-v3.2', 1, '2026-08-05T07:39:00+00:00')",
                (cwd_hash,),
            )
            connection.execute(
                "INSERT INTO external_routes VALUES "
                "('already-active', 'other-session', ?, 'gpt-5.6-luna', '', "
                "'started', '2026-08-05T07:35:00+00:00', NULL)",
                (cwd_hash,),
            )
            connection.execute(
                "INSERT INTO decisions VALUES "
                "('new-native', 'session-1', ?, 'standard', 'gpt-5.6-terra')",
                (cwd_hash,),
            )
            connection.execute(
                "INSERT INTO executions VALUES "
                "('agent-terra', 'new-native', 'gpt-5.6-terra', "
                "'2026-08-05T07:41:00+00:00', NULL)"
            )
            connection.execute(
                "INSERT INTO external_routes VALUES "
                "('new-luna', 'session-1', ?, 'gpt-5.6-luna', '', "
                "'started', '2026-08-05T07:42:00+00:00', NULL)",
                (cwd_hash,),
            )
        append_route(
            transcript,
            "turn-b",
            "2026-08-05T07:40:00Z",
            "ROUTE=mixed | WRITE_READY=1 | READ_READY=1 | EXISTING=1 | "
            "PLANNED_DISPATCH=2 | LEAD=接口与验收 | REASON=parallel_gain | "
            "DETAIL=两个独立单元并行，Lead 负责集成。",
        )
        second = run(data, transcript, "turn-b")
        assert second.returncode == 0, second.stderr
        assert json.loads(second.stdout) == {}
        with sqlite3.connect(database) as connection:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT * FROM route_audits WHERE turn_id = 'turn-b'"
            ).fetchone()
            count = connection.execute("SELECT COUNT(*) FROM route_audits").fetchone()[0]
        assert count == 2
        assert row["observed_active_agents"] == 1
        assert row["planned_dispatch"] == 2
        assert row["observed_dispatch"] == 2
        assert json.loads(row["review_flags"]) == []

        repeated = run(data, transcript, "turn-b")
        assert repeated.returncode == 0 and json.loads(repeated.stdout) == {}
        with sqlite3.connect(database) as connection:
            assert connection.execute("SELECT COUNT(*) FROM route_audits").fetchone()[0] == 2

    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]
    assert "route_auditor.py" not in json.dumps(hooks)
    reporter = (ROOT / "plugins" / "goldilocks" / "scripts" / "usage_reporter.py").read_text(
        encoding="utf-8"
    )
    assert "route_auditor.audit(payload, connection)" in reporter
    print("Goldilocks silent route auditor passed.")


if __name__ == "__main__":
    main()
