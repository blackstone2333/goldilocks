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
REPORTER = ROOT / "plugins" / "goldilocks" / "scripts" / "usage_reporter.py"
HOOKS = ROOT / "plugins" / "goldilocks" / "hooks" / "hooks.json"


def append_usage(path: Path, input_tokens: int, cached: int, output: int) -> None:
    record = {
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": input_tokens,
                    "cached_input_tokens": cached,
                    "output_tokens": output,
                }
            },
        },
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def run_hook(
    data: Path,
    transcript: Path | None,
    event: str,
    *,
    turn_id: str = "turn-1",
    worker: bool = False,
) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": "session-1",
        "turn_id": turn_id,
        "cwd": str(ROOT),
        "hook_event_name": event,
        "model": "gpt-5.6-sol",
        "prompt": "secret implementation prompt",
    }
    if transcript is not None:
        payload["transcript_path"] = str(transcript)
    if event == "Stop":
        payload["last_assistant_message"] = "done"
        payload["stop_hook_active"] = False
    env = {
        **os.environ,
        "PLUGIN_DATA": str(data),
        "GOLDILOCKS_SESSION_ROOTS": str(data.parent),
    }
    if worker:
        env["GOLDILOCKS_WORKER"] = "1"
    return subprocess.run(
        [sys.executable, str(REPORTER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def run_current(data: Path, session_id: str = "session-1") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPORTER), "--current"],
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "PLUGIN_DATA": str(data),
            "CODEX_THREAD_ID": session_id,
            "GOLDILOCKS_SESSION_ROOTS": str(data.parent),
        },
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        data = root / "data"
        transcript = root / "rollout.jsonl"
        append_usage(transcript, 100, 60, 10)

        baseline = run_hook(data, transcript, "UserPromptSubmit")
        assert baseline.returncode == 0 and baseline.stdout == "", baseline.stderr
        stale_snapshot = run_current(data)
        assert stale_snapshot.returncode == 0, stale_snapshot.stderr
        assert stale_snapshot.stdout == "", stale_snapshot.stdout
        terra_transcript = root / "rollout-terra-agent.jsonl"
        append_usage(terra_transcript, 80, 70, 8)
        with sqlite3.connect(data / "orchestration.db") as connection:
            connection.row_factory = sqlite3.Row
            task = connection.execute("SELECT * FROM task_usage_baselines").fetchone()
            assert task["baseline_input_tokens"] == 100
            assert task["baseline_cached_input_tokens"] == 60
            assert task["baseline_output_tokens"] == 10
            assert task["baseline_available"] == 1
            assert task["transcript_path"] == str(transcript)
            connection.execute(
                """
                CREATE TABLE decisions (
                    decision_id TEXT, session_id TEXT, turn_id TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE executions (
                    agent_id TEXT, decision_id TEXT, actual_model TEXT,
                    started_at TEXT, stopped_at TEXT,
                    input_tokens INTEGER, cached_input_tokens INTEGER,
                    output_tokens INTEGER
                )
                """
            )
            connection.execute(
                "INSERT INTO decisions VALUES ('native-1', 'session-1', 'turn-1'), "
                "('native-2', 'session-1', 'terra-child-turn')"
            )
            connection.execute(
                "INSERT INTO executions VALUES "
                "('luna-agent', 'native-1', 'gpt-5.6-luna', ?, 'done', 50, 40, 5), "
                "('terra-agent', 'native-2', 'gpt-5.6-terra', ?, 'done', NULL, NULL, NULL)",
                (task["started_at"], task["started_at"]),
            )
            connection.execute(
                """
                CREATE TABLE external_routes (
                    parent_session_id TEXT, started_at TEXT, stopped_at TEXT,
                    actual_model TEXT, expected_model TEXT, input_tokens INTEGER,
                    cached_input_tokens INTEGER, output_tokens INTEGER
                )
                """
            )
            connection.execute(
                "INSERT INTO external_routes VALUES "
                "('session-1', ?, 'done', 'gpt-5.3-codex-spark', "
                "'gpt-5.3-codex-spark', 70, 60, 7)",
                (task["started_at"],),
            )
            connection.execute(
                "INSERT INTO external_routes VALUES "
                "('terra-agent', ?, 'done', 'gpt-5.6-luna', "
                "'gpt-5.6-luna', 30, 20, 3), "
                "('session-1', ?, 'done', 'deepseek-ai/DeepSeek-V4-Flash', "
                "'deepseek-ai/DeepSeek-V4-Flash', 40, 30, 4)",
                (task["started_at"], task["started_at"]),
            )

        append_usage(transcript, 300, 200, 30)
        visible = run_current(data)
        assert visible.returncode == 0, visible.stderr
        assert visible.stdout.strip() == (
            "Usage: Sol 220 (in 200 / cached 140 / out 20) | "
            "Terra 88 (in 80 / cached 70 / out 8) | "
            "Luna 88 (in 80 / cached 60 / out 8) | "
            "Spark 77 (in 70 / cached 60 / out 7) | "
            "DeepSeek V4 Flash 44 (in 40 / cached 30 / out 4) | total 517 tokens"
        )
        with sqlite3.connect(data / "orchestration.db") as connection:
            recovered = connection.execute(
                "SELECT input_tokens, cached_input_tokens, output_tokens "
                "FROM executions WHERE agent_id = 'terra-agent'"
            ).fetchone()
        assert recovered == (80, 70, 8)
        stopped = run_hook(data, transcript, "Stop")
        assert stopped.returncode == 0, stopped.stderr
        message = json.loads(stopped.stdout)["systemMessage"]
        assert "gpt-5.6-sol: in 200 (140 cached) + out 20 = 220" in message
        assert "gpt-5.6-terra: in 80 (70 cached) + out 8 = 88" in message
        assert "gpt-5.6-luna: in 80 (60 cached) + out 8 = 88" in message
        assert "gpt-5.3-codex-spark: in 70 (60 cached) + out 7 = 77" in message
        assert "deepseek-ai/DeepSeek-V4-Flash: in 40 (30 cached) + out 4 = 44" in message
        assert "total 517 tokens" in message

        duplicate = run_hook(data, transcript, "Stop")
        assert duplicate.returncode == 0 and json.loads(duplicate.stdout) == {}

        append_usage(transcript, 310, 205, 32)
        updated = run_hook(data, transcript, "Stop")
        updated_message = json.loads(updated.stdout)["systemMessage"]
        assert "gpt-5.6-sol: in 210 (145 cached) + out 22 = 232" in updated_message
        assert "total 529 tokens" in updated_message

        missing_start = run_hook(data, None, "UserPromptSubmit", turn_id="turn-2")
        assert missing_start.returncode == 0 and missing_start.stdout == ""
        missing_stop = run_hook(data, None, "Stop", turn_id="turn-2")
        assert "root: token telemetry unavailable" in json.loads(missing_stop.stdout)[
            "systemMessage"
        ]

        worker_start = run_hook(
            data, transcript, "UserPromptSubmit", turn_id="worker-turn", worker=True
        )
        worker_stop = run_hook(data, transcript, "Stop", turn_id="worker-turn", worker=True)
        assert worker_start.stdout == ""
        assert json.loads(worker_stop.stdout) == {}

        assert b"secret implementation prompt" not in (data / "orchestration.db").read_bytes()

    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]
    assert "Stop" in hooks
    user_commands = json.dumps(hooks["UserPromptSubmit"], ensure_ascii=False)
    stop_commands = json.dumps(hooks["Stop"], ensure_ascii=False)
    assert "usage_reporter.py" in user_commands
    assert "usage_reporter.py" in stop_commands
    print("Goldilocks per-turn usage receipt contract passed.")


if __name__ == "__main__":
    main()
