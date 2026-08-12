#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTER = ROOT / "plugins" / "goldilocks" / "scripts" / "usage_reporter.py"
HOOKS = ROOT / "plugins" / "goldilocks" / "hooks" / "hooks.json"


def append_usage(
    path: Path,
    input_tokens: int,
    cached: int,
    output: int,
    *,
    timestamp: str | None = None,
) -> None:
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
    if timestamp is not None:
        record["timestamp"] = timestamp
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def append_task_event(path: Path, event: str, turn_id: str, timestamp: str) -> None:
    record = {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {"type": event, "turn_id": turn_id},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record) + "\n")


def append_fork_meta(path: Path, session_id: str, parent_thread_id: str) -> None:
    record = {
        "timestamp": datetime.now().isoformat(),
        "type": "session_meta",
        "payload": {
            "id": session_id,
            "parent_thread_id": parent_thread_id,
            "source": {
                "subagent": {
                    "thread_spawn": {"parent_thread_id": parent_thread_id}
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


def run_current(
    data: Path,
    session_id: str = "session-1",
    language: str | None = None,
    turn_id: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(REPORTER), "--current"]
    if turn_id is not None:
        command.extend(("--turn-id", turn_id))
    if language is not None:
        command.extend(("--language", language))
    return subprocess.run(
        command,
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


def without_wall(value: str) -> str:
    return value.strip().split(" · wall ", 1)[0].split(" · 用时 ", 1)[0]


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
        reused_transcript = root / "rollout-reused-agent.jsonl"
        forked_transcript = root / "rollout-forked-agent.jsonl"
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
                    decision_id TEXT, session_id TEXT, turn_id TEXT,
                    fork_turns TEXT, status TEXT
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE executions (
                    agent_id TEXT, session_id TEXT, decision_id TEXT, actual_model TEXT,
                    started_at TEXT, stopped_at TEXT,
                    input_tokens INTEGER, cached_input_tokens INTEGER,
                    output_tokens INTEGER
                )
                """
            )
            connection.execute(
                "INSERT INTO decisions VALUES "
                "('native-1', 'session-1', 'turn-1', 'none', 'verified_pass'), "
                "('native-2', 'session-1', 'terra-child-turn', 'none', 'verified_pass'), "
                "('native-3', 'session-1', 'historical-child-turn', 'none', 'verified_pass'), "
                "('native-4', 'session-1', 'forked-child-turn', 'none', 'verified_pass')"
            )
            baseline_time = datetime.fromisoformat(task["started_at"])
            historical = (baseline_time - timedelta(minutes=5)).isoformat()
            followup_started = (baseline_time + timedelta(seconds=1)).isoformat()
            followup_checkpoint = (baseline_time + timedelta(seconds=2)).isoformat()
            followup_stopped = (baseline_time + timedelta(seconds=3)).isoformat()
            inherited_early = (baseline_time - timedelta(seconds=2)).isoformat()
            inherited_latest = (baseline_time - timedelta(seconds=1)).isoformat()
            forked_final = (baseline_time + timedelta(seconds=2)).isoformat()
            connection.execute(
                "INSERT INTO executions VALUES "
                "('luna-agent', 'session-1', 'native-1', 'gpt-5.6-luna', ?, 'done', 50, 40, 5), "
                "('terra-agent', 'session-1', 'native-2', 'gpt-5.6-terra', ?, 'done', NULL, NULL, NULL), "
                "('reused-agent', 'session-1', 'native-3', 'gpt-5.6-terra', ?, ?, 1120, 1000, 112), "
                "('forked-agent', 'session-1', 'native-4', 'gpt-5.6-terra', ?, 'done', "
                "2000500, 1800400, 10050)",
                (
                    task["started_at"],
                    task["started_at"],
                    historical,
                    followup_stopped,
                    task["started_at"],
                ),
            )
            append_usage(
                reused_transcript,
                1000,
                900,
                100,
                timestamp=historical,
            )
            append_task_event(
                reused_transcript,
                "task_started",
                "followup-turn",
                followup_started,
            )
            append_usage(
                reused_transcript,
                1120,
                1000,
                112,
                timestamp=followup_checkpoint,
            )
            append_task_event(
                reused_transcript,
                "task_complete",
                "followup-turn",
                followup_stopped,
            )
            # A native fork copies earlier cumulative checkpoints into the new
            # rollout.  The child owns only the delta from the final inherited
            # checkpoint before SubagentStart, not its lifetime-looking Stop
            # total and not the first copied checkpoint.
            append_fork_meta(forked_transcript, "forked-agent", "session-1")
            append_usage(
                forked_transcript,
                1_000_000,
                900_000,
                5_000,
                timestamp=inherited_early,
            )
            append_usage(
                forked_transcript,
                2_000_000,
                1_800_000,
                10_000,
                timestamp=inherited_latest,
            )
            append_usage(
                forked_transcript,
                2_000_500,
                1_800_400,
                10_050,
                timestamp=forked_final,
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
        visible = run_current(data, turn_id="turn-1")
        assert visible.returncode == 0, visible.stderr
        expected_visible = (
            "Usage: Sol 220 (in 200 / cached 140 / out 20) | "
            "Terra 770 (in 700 / cached 570 / out 70) | "
            "Luna 88 (in 80 / cached 60 / out 8) | "
            "Spark 77 (in 70 / cached 60 / out 7) | "
            "DeepSeek V4 Flash 44 (in 40 / cached 30 / out 4) | total 1,199 tokens"
        )
        assert without_wall(visible.stdout) == expected_visible, visible.stdout
        assert " · wall " in visible.stdout

        chinese_visible = run_current(data, language="zh", turn_id="turn-1")
        assert chinese_visible.returncode == 0, chinese_visible.stderr
        assert chinese_visible.stdout.startswith("用量：Sol 220（输入 200 / 缓存 140 / 输出 20）")
        assert "Terra 770（输入 700 / 缓存 570 / 输出 70）" in chinese_visible.stdout
        assert "总计 1,199 tokens" in chinese_visible.stdout
        assert " · 用时 " in chinese_visible.stdout

        # `--current` is used by the response contract immediately before the
        # model's final answer.  It must only inspect the existing ledger: a
        # read path must still work when neither the database nor its parent
        # directory accepts a journal, schema migration, or receipt update.
        database = data / "orchestration.db"
        directory_mode = data.stat().st_mode & 0o777
        database_mode = database.stat().st_mode & 0o777
        try:
            os.chmod(database, 0o444)
            os.chmod(data, 0o555)
            readonly_visible = run_current(data, turn_id="turn-1")
            assert readonly_visible.returncode == 0, readonly_visible.stderr
            assert without_wall(readonly_visible.stdout) == without_wall(visible.stdout)
        finally:
            os.chmod(data, directory_mode)
            os.chmod(database, database_mode)

        with sqlite3.connect(data / "orchestration.db") as connection:
            recovered = connection.execute(
                "SELECT input_tokens, cached_input_tokens, output_tokens "
                "FROM executions WHERE agent_id = 'terra-agent'"
            ).fetchone()
        assert recovered == (None, None, None), "visible Usage reads must not backfill execution rows"
        stopped = run_hook(data, transcript, "Stop")
        assert stopped.returncode == 0, stopped.stderr
        assert json.loads(stopped.stdout) == {}, "Usage reporter is not a second Stop receipt"

        missing_start = run_hook(data, None, "UserPromptSubmit", turn_id="turn-2")
        assert missing_start.returncode == 0 and missing_start.stdout == ""
        with sqlite3.connect(data / "orchestration.db") as connection:
            turn_two = (baseline_time + timedelta(seconds=10)).isoformat()
            connection.execute(
                "UPDATE task_usage_baselines SET started_at = ? WHERE turn_id = 'turn-2'",
                (turn_two,),
            )
            connection.execute(
                "INSERT INTO decisions VALUES "
                "('native-5', 'session-1', 'missing-worker-turn', 'none', 'verified_pass')"
            )
            connection.execute(
                "INSERT INTO executions VALUES "
                "('missing-agent', 'session-1', 'native-5', 'gpt-5.6-terra', ?, 'done', "
                "NULL, NULL, NULL)",
                (turn_two,),
            )
            connection.execute(
                "INSERT INTO external_routes VALUES "
                "('session-1', ?, 'done', 'gpt-5.3-codex-spark', "
                "'gpt-5.3-codex-spark', 10, 8, 1)",
                (turn_two,),
            )
        partial = run_current(data, turn_id="turn-2")
        assert partial.returncode == 0, partial.stderr
        assert "Spark 11 (in 10 / cached 8 / out 1)" in partial.stdout
        assert "Sol unavailable" in partial.stdout
        assert "usage unavailable for 1 worker" in partial.stdout
        assert "known total 11 tokens" in partial.stdout, partial.stdout
        stale = run_current(data, turn_id="missing-turn")
        assert stale.returncode == 0 and stale.stdout == "" and stale.stderr == ""
        missing_stop = run_hook(data, None, "Stop", turn_id="turn-2")
        assert json.loads(missing_stop.stdout) == {}

        # A new native fork may lack a transcript checkpoint even though the
        # posthoc inspector recorded its child-only Usage.  Accept that DB
        # record only for an explicit fresh (`none`) dispatch verified as pass;
        # inherited and unlinked forks remain unavailable.
        fresh_fork = root / "fresh-fork-agent.jsonl"
        inherited_fork = root / "inherited-fork-agent.jsonl"
        unlinked_fork = root / "unlinked-fork-agent.jsonl"
        malformed_fork = root / "malformed-fork-agent.jsonl"
        append_fork_meta(fresh_fork, "fresh-fork-agent", "session-1")
        append_fork_meta(inherited_fork, "inherited-fork-agent", "session-1")
        append_fork_meta(unlinked_fork, "unlinked-fork-agent", "session-1")
        fork_start = run_hook(data, None, "UserPromptSubmit", turn_id="turn-3")
        assert fork_start.returncode == 0 and fork_start.stdout == ""
        turn_three = (baseline_time + timedelta(seconds=20)).isoformat()
        with sqlite3.connect(data / "orchestration.db") as connection:
            connection.execute(
                "UPDATE task_usage_baselines SET started_at = ? WHERE turn_id = 'turn-3'",
                (turn_three,),
            )
            connection.execute(
                "INSERT INTO decisions VALUES "
                "('native-6', 'session-1', 'fresh-fork-turn', 'none', 'verified_pass'), "
                "('native-7', 'session-1', 'inherited-fork-turn', '2', 'verified_pass'), "
                "('native-8', 'session-1', 'no-transcript-inherited-turn', '2', 'verified_pass'), "
                "('native-9', 'session-1', 'no-transcript-failed-turn', 'none', 'verified_fail'), "
                "('native-10', 'session-1', 'malformed-inherited-turn', '2', 'verified_pass')"
            )
            connection.execute(
                "INSERT INTO executions VALUES "
                "('fresh-fork-agent', 'session-1', 'native-6', 'gpt-5.6-luna', ?, 'done', 300, 250, 30), "
                "('inherited-fork-agent', 'session-1', 'native-7', 'gpt-5.6-terra', ?, 'done', 500, 400, 50), "
                "('unlinked-fork-agent', 'session-1', 'missing-decision', 'gpt-5.6-terra', ?, 'done', 700, 600, 70), "
                "('no-transcript-inherited-agent', 'session-1', 'native-8', 'gpt-5.6-terra', ?, 'done', 800, 700, 80), "
                "('no-transcript-failed-agent', 'session-1', 'native-9', 'gpt-5.6-terra', ?, 'done', 900, 800, 90), "
                "('no-transcript-unlinked-agent', 'session-1', 'missing-decision-2', 'gpt-5.6-terra', ?, 'done', 1000, 900, 100), "
                "('malformed-fork-agent', 'session-1', 'native-10', 'gpt-5.6-terra', ?, 'done', 1100, 1000, 110)",
                (turn_three,) * 7,
            )
        # This rollout has a usage checkpoint but no valid thread_spawn
        # metadata.  It must not bypass the inherited-fork decision guard.
        append_usage(
            malformed_fork,
            1_100,
            1_000,
            110,
            timestamp=(baseline_time + timedelta(seconds=21)).isoformat(),
        )
        fresh = run_current(data, turn_id="turn-3")
        assert fresh.returncode == 0, fresh.stderr
        assert "Luna 330 (in 300 / cached 250 / out 30)" in fresh.stdout
        assert "Terra" not in fresh.stdout
        assert "usage unavailable for 6 workers" in fresh.stdout, fresh.stdout
        assert "known total 330 tokens" in fresh.stdout, fresh.stdout

        # Older ledgers without fork_turns/status cannot prove that a DB total
        # belongs to a fresh accepted worker.  Keep it unavailable instead of
        # treating a legacy non-null number as current-turn Usage.
        legacy_data = root / "legacy-data"
        legacy_start = run_hook(
            legacy_data, None, "UserPromptSubmit", turn_id="legacy-turn"
        )
        assert legacy_start.returncode == 0 and legacy_start.stdout == ""
        with sqlite3.connect(legacy_data / "orchestration.db") as connection:
            legacy_started = connection.execute(
                "SELECT started_at FROM task_usage_baselines "
                "WHERE turn_id = 'legacy-turn'"
            ).fetchone()[0]
            connection.execute(
                "CREATE TABLE decisions (decision_id TEXT, session_id TEXT, turn_id TEXT)"
            )
            connection.execute(
                "CREATE TABLE executions ("
                "agent_id TEXT, session_id TEXT, decision_id TEXT, actual_model TEXT, "
                "started_at TEXT, stopped_at TEXT, input_tokens INTEGER, "
                "cached_input_tokens INTEGER, output_tokens INTEGER)"
            )
            connection.execute(
                "INSERT INTO decisions VALUES "
                "('legacy-decision', 'session-1', 'legacy-worker-turn')"
            )
            connection.execute(
                "INSERT INTO executions VALUES "
                "('legacy-agent', 'session-1', 'legacy-decision', 'gpt-5.6-terra', "
                "?, 'done', 1200, 1000, 120)",
                (legacy_started,),
            )
        legacy = run_current(legacy_data, turn_id="legacy-turn")
        assert legacy.returncode == 0, legacy.stderr
        assert "Terra" not in legacy.stdout
        assert "usage unavailable for 1 worker" in legacy.stdout, legacy.stdout

        worker_start = run_hook(
            data, transcript, "UserPromptSubmit", turn_id="worker-turn", worker=True
        )
        worker_stop = run_hook(data, transcript, "Stop", turn_id="worker-turn", worker=True)
        assert worker_start.stdout == ""
        assert json.loads(worker_stop.stdout) == {}

        assert b"secret implementation prompt" not in (data / "orchestration.db").read_bytes()

        corrupt = root / "corrupt-data"
        corrupt.mkdir()
        (corrupt / "orchestration.db").write_bytes(b"not a sqlite database")
        failed_current = run_current(corrupt)
        assert failed_current.returncode == 0
        assert failed_current.stdout == ""
        assert failed_current.stderr == "", "--current must fail silently for invalid ledgers"

    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]
    assert "Stop" in hooks
    user_commands = json.dumps(hooks["UserPromptSubmit"], ensure_ascii=False)
    stop_commands = json.dumps(hooks["Stop"], ensure_ascii=False)
    assert "usage_reporter.py" in user_commands
    assert "codex','plugin','list','--json" in user_commands
    assert "usage_reporter.py" not in stop_commands
    assert "route_auditor.py" in stop_commands
    print("Goldilocks host-side live usage receipt contract passed.")


if __name__ == "__main__":
    main()
