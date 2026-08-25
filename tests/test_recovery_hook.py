#!/usr/bin/env python3

from __future__ import annotations

import json
import hashlib
import os
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
HOOK = ROOT / "plugins" / "goldilocks" / "scripts" / "recovery_reminder.py"


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


@contextmanager
def database(path: Path):
    """Match sqlite3's transaction context while closing fixture connections."""

    connection = sqlite3.connect(path)
    try:
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def run_hook(
    cwd: Path,
    event: str,
    *,
    worker: bool = False,
    data_dir: Path | None = None,
    prompt: str = "Build and test the full-stack feature with the specialist Skill.",
    turn_id: str = "test-turn",
    session_roots: Path | None = None,
    usage_visibility: str | None = None,
    session_id: str = "test-session",
) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": session_id,
        "turn_id": turn_id,
        "cwd": str(cwd),
        "hook_event_name": event,
    }
    if event == "SessionStart":
        payload["source"] = "startup"
    elif event == "PostCompact":
        payload["trigger"] = "auto"
    elif event == "UserPromptSubmit":
        payload["prompt"] = prompt
    env = os.environ.copy()
    if worker:
        env["GOLDILOCKS_WORKER"] = "1"
    if data_dir is not None:
        env["PLUGIN_DATA"] = str(data_dir)
    else:
        env.pop("PLUGIN_DATA", None)
    if session_roots is not None:
        env["GOLDILOCKS_SESSION_ROOTS"] = str(session_roots)
    if usage_visibility is not None:
        env["GOLDILOCKS_USAGE_VISIBILITY"] = usage_visibility
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        parent = Path(temp_dir)
        outside_ledger = parent / ".goldilocks" / "ACTIVE.md"
        outside_ledger.parent.mkdir()
        outside_ledger.write_text("# Unrelated parent task\n", encoding="utf-8")

        repo = parent / "workspace"
        (repo / ".git").mkdir(parents=True)
        nested = repo / "src" / "nested"
        nested.mkdir(parents=True)
        data_dir = parent / "plugin-data"
        data_dir.mkdir()

        # A host may stay in one registered worktree while the active frontier
        # lives in another. Recovery must use the host session id and Git's
        # registry, never a recursive "first ACTIVE wins" scan.
        registered_container = parent / "registered-container"
        registered_work = registered_container / "work"
        registered_work.mkdir(parents=True)
        registered_main = registered_work / "registered-main"
        subprocess.run(["git", "init", "-q", str(registered_main)], check=True)
        subprocess.run(
            [
                "git", "-C", str(registered_main), "-c", "user.name=Goldilocks Test",
                "-c", "user.email=goldilocks@example.invalid", "commit", "--allow-empty",
                "-q", "-m", "fixture",
            ],
            check=True,
        )
        registered_a = registered_work / "registered-a"
        registered_b = registered_work / "registered-b"
        subprocess.run(
            ["git", "-C", str(registered_main), "worktree", "add", "-q", "-b", "ledger-a", str(registered_a)],
            check=True,
        )
        subprocess.run(
            ["git", "-C", str(registered_main), "worktree", "add", "-q", "-b", "ledger-b", str(registered_b)],
            check=True,
        )

        ledger_a = registered_a / ".goldilocks" / "ACTIVE.md"
        ledger_a.parent.mkdir()
        ledger_a.write_text(
            "---\nstatus: active\nsession_id: matching-session\n---\n# Active A\n",
            encoding="utf-8",
        )
        # A valid registered backlink may itself use a relative path.
        linked_gitdir = Path(
            (registered_a / ".git")
            .read_text(encoding="utf-8")
            .split(":", 1)[1]
            .strip()
        )
        (linked_gitdir / "gitdir").write_text(
            os.path.relpath(registered_a / ".git", linked_gitdir) + "\n",
            encoding="utf-8",
        )

        symlink_target = parent / "symlink-frontier"
        symlink_target.mkdir()
        (symlink_target / "ACTIVE.md").write_text(
            "---\nstatus: active\nsession_id: matching-session\n---\n# Do not follow\n",
            encoding="utf-8",
        )
        symlinked_goldilocks = registered_b / ".goldilocks"
        symlinked_goldilocks.symlink_to(symlink_target, target_is_directory=True)
        registered_session = run_hook(
            registered_container, "SessionStart", session_id="matching-session"
        )
        assert registered_session.returncode == 0, registered_session.stderr
        registered_context = json.loads(registered_session.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert str(ledger_a) in registered_context
        assert "Goldilocks | Active: continuity restored from ACTIVE" in registered_context

        registered_compact = run_hook(
            registered_container, "PostCompact", session_id="matching-session"
        )
        compact_message = json.loads(registered_compact.stdout)["systemMessage"]
        assert str(ledger_a) in compact_message
        assert "Goldilocks | Active: continuity restored from ACTIVE" in compact_message

        wrong_session = run_hook(
            registered_container, "SessionStart", session_id="different-session"
        )
        assert wrong_session.returncode == 0, wrong_session.stderr
        assert wrong_session.stdout == ""

        unregistered = registered_container / "unregistered-child" / ".goldilocks" / "ACTIVE.md"
        unregistered.parent.mkdir(parents=True)
        unregistered.write_text(
            "---\nstatus: active\nsession_id: unregistered-session\n---\n# Ignore me\n",
            encoding="utf-8",
        )
        unregistered_session = run_hook(
            registered_container, "SessionStart", session_id="unregistered-session"
        )
        assert unregistered_session.stdout == ""

        forged_target = parent / "forged-worktree"
        forged_target.mkdir()
        (forged_target / ".git").write_text("gitdir: /not/the/registered/entry\n", encoding="utf-8")
        forged_ledger = forged_target / ".goldilocks" / "ACTIVE.md"
        forged_ledger.parent.mkdir()
        forged_ledger.write_text(
            "---\nstatus: active\nsession_id: forged-session\n---\n# Forged\n",
            encoding="utf-8",
        )
        forged_entry = registered_main / ".git" / "worktrees" / "forged"
        forged_entry.mkdir()
        (forged_entry / "gitdir").write_text(
            str(forged_target / ".git") + "\n", encoding="utf-8"
        )
        forged_session = run_hook(
            registered_container, "SessionStart", session_id="forged-session"
        )
        assert forged_session.stdout == "", "one-way registry entries must not be trusted"

        symlinked_goldilocks.unlink()
        ledger_b = registered_b / ".goldilocks" / "ACTIVE.md"
        ledger_b.parent.mkdir()
        ledger_b.write_text(
            "---\nstatus: active\nsession_id: matching-session\n---\n# Active B\n",
            encoding="utf-8",
        )
        ambiguous = run_hook(
            registered_container, "SessionStart", session_id="matching-session"
        )
        assert ambiguous.returncode == 0, ambiguous.stderr
        assert ambiguous.stdout == "", "multiple matching frontiers must never be guessed"
        with database(data_dir / "orchestration.db") as connection:
            connection.execute(
                """
                CREATE TABLE gate_injections (
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

        startup = run_hook(nested, "SessionStart")
        assert startup.returncode == 0, startup.stderr
        assert startup.stdout == "", "startup stays silent without recovery state"

        compact_without_recovery = run_hook(nested, "PostCompact")
        assert compact_without_recovery.returncode == 0, compact_without_recovery.stderr
        compact_contract = json.loads(compact_without_recovery.stdout)["systemMessage"]
        assert "visible response and verification contracts survived compaction" in compact_contract
        assert "Minimum-sufficient verification" in compact_contract
        assert "diagnose, not retry" in compact_contract
        assert "Usage is host-side and fail-silent" in compact_contract

        no_ledger_steer = run_hook(nested, "UserPromptSubmit", data_dir=data_dir)
        assert no_ledger_steer.returncode == 0, no_ledger_steer.stderr
        style_output = json.loads(no_ledger_steer.stdout)
        style_context = style_output["hookSpecificOutput"]["additionalContext"]
        assert len(style_context.split()) <= 350
        assert "Lead with the result" in style_context
        assert "Omit work preambles" in style_context
        assert "Report only changed state" in style_context
        assert "decisive evidence" in style_context
        assert "For defects" in style_context
        assert "expand when asked" in style_context
        assert "evidence-backed cause" in style_context
        assert "explicitly unknown" in style_context
        assert "fix and verification" in style_context
        assert "Every executable" in style_context
        assert "exactly one localized visible Goldilocks route receipt" in style_context
        assert "in this exact field order" in style_context
        assert "ROUTE=<direct|fast|standard|mixed>" in style_context
        assert "TEAM=<main model and actually started roles>" in style_context
        assert "CONCURRENCY=<host-confirmed starts/host limit or ?>" in style_context
        assert "DELEGATED=<actual delegated work or none>" in style_context
        assert "REASON=<short reason>" in style_context
        assert "DETAIL=<one factual sentence>" in style_context
        assert "never Codex/primary agent" in style_context
        assert "Usage is host-side and fail-silent" in style_context
        assert "on-demand is the default" in style_context
        assert "Bootstrap automatic opt-in" in style_context
        assert "usage_reporter.py" not in style_context
        assert "codex plugin list" not in style_context
        assert "fast__<semantic>_<model>" in style_context
        assert "standard__<semantic>_<model>" in style_context
        assert "lead__<semantic>_<model>" in style_context
        assert "Luna/Spark" in style_context
        assert "fork_turns=none" in style_context
        assert "none/1-4" in style_context
        assert "fresh review-only/no write/repair/delegate" in style_context
        assert "never changes user-selected host permissions" in style_context
        assert "only explicit Lead handoff permits `all`" in style_context
        assert "native hosts may bypass PreToolUse" in style_context
        assert "silently apply the Goldilocks zero-cost gate" in style_context
        assert "before any specialist Skill" in style_context
        assert "goldilocks:goldilocks" in style_context
        assert "otherwise take its Direct exit" in style_context
        assert "pure conversation" in style_context
        assert "Minimum-sufficient verification" in style_context
        assert "Add no hash/frozen contract/baseline/gate" in style_context
        assert "Without relevant change, do not rerun a pass" in style_context
        assert "after repair run only failed/affected checks" in style_context
        assert "diagnose, not retry" in style_context
        assert "Preserve safeguards" in style_context
        assert "Likely multi-unit work detected" not in style_context

        health_session_start = run_hook(nested, "SessionStart", data_dir=data_dir)
        assert health_session_start.returncode == 0, health_session_start.stderr
        assert health_session_start.stdout == ""
        health_prompt = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="Track hook health without saving sensitive content.",
            turn_id="health-turn",
        )
        assert health_prompt.returncode == 0, health_prompt.stderr
        health_compact = run_hook(nested, "PostCompact", data_dir=data_dir)
        assert health_compact.returncode == 0, health_compact.stderr
        assert "systemMessage" in json.loads(health_compact.stdout)

        with database(data_dir / "orchestration.db") as connection:
            connection.row_factory = sqlite3.Row
            health_rows = connection.execute(
                "SELECT event_name, session_id_hash, turn_id_hash, status, started_at, finished_at "
                ", elapsed_ms, policy_version "
                "FROM hook_health ORDER BY event_name, session_id_hash, turn_id_hash"
            ).fetchall()
        assert len(health_rows) >= 4
        for row in health_rows:
            assert row["status"] == "ok"
            assert row["session_id_hash"] == stable_hash("test-session")
            assert len(row["session_id_hash"]) == 64
            assert len(row["turn_id_hash"]) == 64
            assert row["started_at"]
            assert row["finished_at"]
            assert row["elapsed_ms"] >= 0
            assert row["policy_version"]
        with database(data_dir / "orchestration.db") as connection:
            session_hash = stable_hash("test-session")
            assert connection.execute(
                "SELECT COUNT(*) FROM hook_health WHERE session_id_hash = ? AND event_name = 'SessionStart' "
                "AND turn_id_hash = ?",
                (session_hash, stable_hash("test-turn")),
            ).fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(*) FROM hook_health WHERE session_id_hash = ? AND event_name = 'UserPromptSubmit' "
                "AND turn_id_hash = ?",
                (session_hash, stable_hash("health-turn")),
            ).fetchone()[0] == 1
            assert connection.execute(
                "SELECT COUNT(*) FROM hook_health WHERE session_id_hash = ? AND event_name = 'PostCompact' "
                "AND turn_id_hash = ?",
                (session_hash, stable_hash("test-turn")),
            ).fetchone()[0] == 1
        assert b"Track hook health without saving sensitive content." not in (
            data_dir / "orchestration.db"
        ).read_bytes()

        duplicate_health_prompt = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="This prompt duplicates the previous turn_id.",
            turn_id="health-turn",
        )
        assert duplicate_health_prompt.returncode == 0, duplicate_health_prompt.stderr
        with database(data_dir / "orchestration.db") as connection:
            count = connection.execute(
                "SELECT COUNT(*) FROM hook_health WHERE event_name = 'UserPromptSubmit' "
                "AND turn_id_hash = ?",
                (stable_hash("health-turn"),),
            ).fetchone()[0]
        assert count == 1

        with database(data_dir / "orchestration.db") as connection:
            connection.execute(
                "INSERT INTO hook_health ("
                "event_name, session_id_hash, turn_id_hash, event_id, started_at, finished_at, "
                "elapsed_ms, status, policy_version"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    "SessionStart",
                    "stale_session",
                    "stale_turn",
                    "stale",
                    (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(),
                    (datetime.now(timezone.utc) - timedelta(days=40)).isoformat(),
                    0,
                    "ok",
                    "0.5.3-beta.5",
                ),
            )
        stale_cleanup = run_hook(
            nested, "SessionStart", data_dir=data_dir, turn_id="stale-turn"
        )
        assert stale_cleanup.returncode == 0, stale_cleanup.stderr
        with database(data_dir / "orchestration.db") as connection:
            stale_remaining = connection.execute(
                "SELECT COUNT(*) FROM hook_health WHERE event_id = 'stale'"
            ).fetchone()[0]
        assert stale_remaining == 0

        cohesive_prompt = (
            "Implement this single local implementation unit. Update the code, focused tests, "
            "and concise README contract; make no architectural changes."
        )
        cohesive = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt=cohesive_prompt,
            turn_id="cohesive-direct-turn",
        )
        cohesive_context = json.loads(cohesive.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "Likely multi-unit work detected" not in cohesive_context

        night_shift_discussion = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="我们讨论一下 Night Shift 夜班模式是否适合文档任务？",
            turn_id="night-shift-discussion",
        )
        discussion_context = json.loads(night_shift_discussion.stdout)[
            "hookSpecificOutput"
        ]["additionalContext"]
        assert "Night Shift 已选择" not in discussion_context
        assert "Night Shift 建议" not in discussion_context

        zh_mode_question = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="讨论怎么用 Night Shift；是否启用夜班来完成这份文档更合适？",
            turn_id="night-shift-zh-question",
        )
        zh_question_context = json.loads(zh_mode_question.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "Night Shift 已选择" not in zh_question_context
        assert "Night Shift 建议" not in zh_question_context

        en_mode_question = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="What is Night Shift for, and should we enable Night Shift to complete the document?",
            turn_id="night-shift-en-question",
        )
        en_question_context = json.loads(en_mode_question.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "Night Shift selected" not in en_question_context
        assert "Night Shift suggestion" not in en_question_context

        night_shift_luna = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="请用夜班/成本优先模式完成这份文档和调研，我可以等到明天。",
            turn_id="night-shift-luna",
        )
        luna_context = json.loads(night_shift_luna.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        for phrase in (
            "Night Shift 已选择",
            "Luna Max",
            "原生不可见时先用 Adapter",
            "实际启动失败后才可标记 route_unavailable",
        ):
            assert phrase in luna_context, phrase

        night_shift_spark = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="Please use Night Shift to fix this urgent deterministic coding bug before the deadline.",
            turn_id="night-shift-spark",
        )
        spark_context = json.loads(night_shift_spark.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        for phrase in (
            "Night Shift selected",
            "Spark XHigh",
            "Try the native employee first",
            "try the adapter",
            "observed start failure",
        ):
            assert phrase in spark_context, phrase

        suggested = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="请完成这份文档；不着急，可以等，成本优先。",
            turn_id="night-shift-suggestion",
        )
        suggested_context = json.loads(suggested.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "Night Shift 建议" in suggested_context
        assert "不切换模型" in suggested_context
        repeated_suggestion = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="请继续完成这份文档；不着急，可以等，成本优先。",
            turn_id="night-shift-suggestion-repeat",
        )
        repeated_suggestion_context = json.loads(repeated_suggestion.stdout)[
            "hookSpecificOutput"
        ]["additionalContext"]
        assert "Night Shift 建议" not in repeated_suggestion_context

        no_database_night_shift = run_hook(
            nested,
            "UserPromptSubmit",
            prompt="Please use Night Shift to complete this ordinary document task; it can wait.",
            turn_id="night-shift-no-database",
        )
        assert no_database_night_shift.returncode == 0, no_database_night_shift.stderr
        assert "Luna Max" in json.loads(no_database_night_shift.stdout)[
            "hookSpecificOutput"
        ]["additionalContext"]

        with database(data_dir / "orchestration.db") as connection:
            reminders = connection.execute(
                "SELECT kind FROM night_shift_reminders ORDER BY kind"
            ).fetchall()
        assert [row[0] for row in reminders] == [
            "explicit_luna",
            "explicit_spark",
            "suggestion",
        ]

        with database(data_dir / "orchestration.db") as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT session_id, turn_id, cwd_hash, prompt_fingerprint, ledger_present, "
                "repeat_failure_signal, continuity_required, routing_rationale_candidate, "
                "routing_experiment_id, delegation_grant_active "
                "FROM gate_injections WHERE turn_id = 'test-turn'"
            ).fetchall()
        assert len(rows) == 1
        assert rows[0]["session_id"] == "test-session"
        assert rows[0]["turn_id"] == "test-turn"
        assert len(rows[0]["cwd_hash"]) == 64
        assert len(rows[0]["prompt_fingerprint"]) == 64
        assert rows[0]["ledger_present"] == 0
        assert rows[0]["repeat_failure_signal"] == 0
        assert rows[0]["continuity_required"] == 0
        assert rows[0]["routing_rationale_candidate"] == 0
        assert rows[0]["routing_experiment_id"] is None
        assert rows[0]["delegation_grant_active"] == 0
        assert b"Build and test the full-stack feature" not in (
            data_dir / "orchestration.db"
        ).read_bytes(), "audit storage must not retain prompt text"

        with database(data_dir / "orchestration.db") as connection:
            audit_count_before_repeat = connection.execute(
                "SELECT COUNT(*) FROM gate_injections"
            ).fetchone()[0]
        repeated = run_hook(nested, "UserPromptSubmit", data_dir=data_dir)
        assert repeated.returncode == 0, repeated.stderr
        with database(data_dir / "orchestration.db") as connection:
            count = connection.execute("SELECT COUNT(*) FROM gate_injections").fetchone()[0]
        assert count == audit_count_before_repeat, "the same prompt turn must not add another audit record"

        multi_unit_prompt = (
            "请完成以下开发任务：\n"
            "1、修复画布上下文记忆。\n"
            "2、实现 Agent 连接。\n"
            "3、补齐测试、文档和发布检查。"
        )
        with database(data_dir / "orchestration.db") as connection:
            connection.execute(
                "CREATE TABLE project_grants (cwd_hash TEXT PRIMARY KEY, active INTEGER, "
                "granted_at TEXT, revoked_at TEXT, policy_version TEXT)"
            )
            connection.execute(
                "INSERT INTO project_grants VALUES (?, 1, 'now', NULL, '0.5.0')",
                ("__global__",),
            )
        rationale = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt=multi_unit_prompt,
            turn_id="rationale-turn",
        )
        assert rationale.returncode == 0, rationale.stderr
        rationale_context = json.loads(rationale.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        for phrase in (
            "Likely multi-unit work detected",
            "Read route-card.md",
            "canonical ROUTE line",
            "inside an HTML comment",
            "WRITE_READY",
            "READ_READY",
            "EXISTING",
            "PLANNED_DISPATCH",
            "current host-confirmed running ownership",
            "not UI labels",
            "historical task_started",
            "Audit is silent",
            "create no extra proof, probe, document, test, or model call",
            "EXISTING is current host-confirmed running ownership",
            "collect finals via host wait/status",
            "TEAM/CONCURRENCY use host-confirmed starts/active workers",
            "never planned",
            "capacity is ? when unknown",
            "Root Direct uses the compact visible response contract",
            "Shared writes",
            "explicit bounded-delegation grant",
            "current official input/cached/output rates",
            "persistent explicit-user authorization",
            "<tier>__<semantic>_<model>",
            "Evaluate every ready unit for Fast before Standard",
            "missing native role alone is not route_unavailable",
            "all delegated units use Terra",
            "why Fast is ineligible",
        ):
            assert phrase in rationale_context, phrase
        assert len(rationale_context.split()) <= 420
        with database(data_dir / "orchestration.db") as connection:
            connection.row_factory = sqlite3.Row
            rationale_row = connection.execute(
                "SELECT routing_rationale_candidate, routing_experiment_id "
                "FROM gate_injections WHERE turn_id = 'rationale-turn'"
            ).fetchone()
        assert rationale_row["routing_rationale_candidate"] == 1
        assert rationale_row["routing_experiment_id"] == "routing-rationale-v3.2"
        assert multi_unit_prompt.encode() not in (
            data_dir / "orchestration.db"
        ).read_bytes(), "routing audit must not retain candidate prompt text"

        lifecycle_data = parent / "lifecycle-data"
        lifecycle_data.mkdir()
        lifecycle_sessions = parent / "lifecycle-sessions"
        lifecycle_sessions.mkdir()
        started = datetime.now(timezone.utc) - timedelta(minutes=2)
        completed = started + timedelta(minutes=1)
        running = datetime.now(timezone.utc) - timedelta(seconds=10)
        with database(lifecycle_data / "orchestration.db") as connection:
            connection.execute(
                "CREATE TABLE decisions (decision_id TEXT PRIMARY KEY, session_id TEXT, "
                "tier TEXT, status TEXT)"
            )
            connection.execute(
                "CREATE TABLE executions (agent_id TEXT PRIMARY KEY, session_id TEXT, "
                "decision_id TEXT, started_at TEXT, stopped_at TEXT, elapsed_ms INTEGER)"
            )
            connection.executemany(
                "INSERT INTO decisions VALUES (?, 'test-session', 'fast', 'started')",
                [("completed-decision",), ("running-decision",)],
            )
            connection.executemany(
                "INSERT INTO executions VALUES (?, 'test-session', ?, ?, NULL, NULL)",
                [
                    ("completed-agent", "completed-decision", started.isoformat()),
                    ("running-agent", "running-decision", running.isoformat()),
                ],
            )
        completed_rollout = lifecycle_sessions / "rollout-test-completed-agent.jsonl"
        completed_rollout.write_text(
            "\n".join(
                json.dumps(
                    {
                        "timestamp": stamp.isoformat().replace("+00:00", "Z"),
                        "type": "event_msg",
                        "payload": {"type": event},
                    }
                )
                for stamp, event in (
                    (started, "task_started"),
                    (completed, "task_complete"),
                )
            )
            + "\n",
            encoding="utf-8",
        )
        running_rollout = lifecycle_sessions / "rollout-test-running-agent.jsonl"
        running_rollout.write_text(
            "\n".join(
                json.dumps(
                    {
                        "timestamp": stamp.isoformat().replace("+00:00", "Z"),
                        "type": "event_msg",
                        "payload": {"type": event},
                    }
                )
                for stamp, event in (
                    (started, "task_complete"),
                    (running, "task_started"),
                )
            )
            + "\n",
            encoding="utf-8",
        )
        lifecycle = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=lifecycle_data,
            prompt="继续当前实现。",
            turn_id="lifecycle-turn",
            session_roots=lifecycle_sessions,
        )
        assert lifecycle.returncode == 0, lifecycle.stderr
        lifecycle_context = json.loads(lifecycle.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "1 completed worker outcome(s) remain unverified" in lifecycle_context
        with database(lifecycle_data / "orchestration.db") as connection:
            completed_row = connection.execute(
                "SELECT stopped_at, elapsed_ms FROM executions "
                "WHERE agent_id = 'completed-agent'"
            ).fetchone()
            running_row = connection.execute(
                "SELECT stopped_at FROM executions WHERE agent_id = 'running-agent'"
            ).fetchone()
            statuses = dict(
                connection.execute("SELECT decision_id, status FROM decisions").fetchall()
            )
        assert completed_row[0] == completed.isoformat().replace("+00:00", "Z")
        assert completed_row[1] == 60_000
        assert running_row[0] is None
        assert statuses == {
            "completed-decision": "stopped",
            "running-decision": "started",
        }

        quota_data = parent / "quota-recovery-data"
        quota_data.mkdir()
        quota_sessions = parent / "quota-recovery-sessions"
        quota_sessions.mkdir()
        quota_agent = "11111111-2222-4333-8444-777777777777"
        quota_reset = int(datetime.now(timezone.utc).timestamp()) + 3600
        with database(quota_data / "orchestration.db") as connection:
            connection.execute(
                "CREATE TABLE decisions (decision_id TEXT PRIMARY KEY, session_id TEXT, "
                "status TEXT, stopped_at TEXT)"
            )
            connection.execute(
                "CREATE TABLE executions (agent_id TEXT PRIMARY KEY, session_id TEXT, "
                "decision_id TEXT, actual_model TEXT, started_at TEXT, stopped_at TEXT, "
                "elapsed_ms INTEGER, terminal_outcome TEXT NOT NULL DEFAULT 'unknown', "
                "quota_reset_at INTEGER)"
            )
            connection.execute(
                "INSERT INTO decisions VALUES ('quota-decision', 'test-session', 'started', NULL)"
            )
            connection.execute(
                "INSERT INTO executions VALUES (?, 'test-session', 'quota-decision', "
                "'gpt-5.3-codex-spark', ?, NULL, NULL, 'unknown', NULL)",
                (quota_agent, started.isoformat()),
            )
        quota_rollout = quota_sessions / f"rollout-test-{quota_agent}.jsonl"
        quota_rollout.write_text(
            "\n".join(
                json.dumps(record)
                for record in (
                    {
                        "timestamp": completed.isoformat().replace("+00:00", "Z"),
                        "type": "event_msg",
                        "payload": {
                            "type": "token_count",
                            "rate_limits": {
                                "limit_name": "GPT-5.3-Codex-Spark",
                                "primary": {
                                    "used_percent": 100.0,
                                    "resets_at": quota_reset,
                                },
                            },
                        },
                    },
                    {
                        "timestamp": completed.isoformat().replace("+00:00", "Z"),
                        "type": "event_msg",
                        "payload": {
                            "type": "task_complete",
                            "error": {
                                "message": "do not persist this fixture text",
                                "codex_error_info": "usage_limit_exceeded",
                            },
                        },
                    },
                )
            )
            + "\n",
            encoding="utf-8",
        )
        quota_recovery = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=quota_data,
            prompt="继续当前实现。",
            turn_id="quota-recovery-turn",
            session_roots=quota_sessions,
        )
        assert quota_recovery.returncode == 0, quota_recovery.stderr
        with database(quota_data / "orchestration.db") as connection:
            quota_row = connection.execute(
                "SELECT stopped_at, terminal_outcome, quota_reset_at FROM executions "
                "WHERE agent_id = ?",
                (quota_agent,),
            ).fetchone()
        assert quota_row[0] is not None
        assert quota_row[1:] == ("usage_limit", quota_reset)
        assert b"do not persist this fixture text" not in (
            quota_data / "orchestration.db"
        ).read_bytes()

        simple_change = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="把按钮颜色改成蓝色。",
            turn_id="simple-change",
        )
        simple_context = json.loads(simple_change.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "Likely multi-unit work detected" not in simple_context
        with database(data_dir / "orchestration.db") as connection:
            simple_candidate = connection.execute(
                "SELECT routing_rationale_candidate FROM gate_injections "
                "WHERE turn_id = 'simple-change'"
            ).fetchone()[0]
        assert simple_candidate == 0

        with database(data_dir / "orchestration.db") as connection:
            connection.execute(
                "CREATE TABLE decisions (decision_id TEXT, session_id TEXT, tier TEXT, status TEXT)"
            )
            connection.execute(
                "CREATE TABLE executions (session_id TEXT, decision_id TEXT, "
                "started_at TEXT, stopped_at TEXT)"
            )
            connection.execute(
                "CREATE TABLE external_routes (parent_session_id TEXT, status TEXT, "
                "lead_result TEXT)"
            )
            connection.executemany(
                "INSERT INTO decisions VALUES (?, 'test-session', ?, ?)",
                [("stopped-native", "fast", "stopped"), ("stale-fast", "fast", "started")],
            )
            connection.execute(
                "INSERT INTO executions VALUES "
                "('test-session', 'stale-fast', '2020-01-01T00:00:00+00:00', NULL)"
            )
            connection.execute(
                "INSERT INTO external_routes VALUES ('test-session', 'succeeded', NULL)"
            )
        debt_prompt = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="继续完成当前实现。",
            turn_id="routing-debt-turn",
        )
        debt_context = json.loads(debt_prompt.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "2 completed worker outcome(s) remain unverified" in debt_context
        assert "1 worker(s) exceed the lifecycle warning" in debt_context
        assert "Stale records do not count as EXISTING" in debt_context
        assert "current host status confirms they are running" in debt_context

        first_recurrence_without_history = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=parent / "fresh-plugin-data",
            prompt="这个修复仍然失败。",
            turn_id="first-recurrence",
        )
        assert first_recurrence_without_history.returncode == 0
        first_context = json.loads(first_recurrence_without_history.stdout)[
            "hookSpecificOutput"
        ]["additionalContext"]
        assert "Repeated-failure continuity boundary" not in first_context

        benign_prompt = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="还是不用回退，这次没有问题。",
            turn_id="benign-turn",
        )
        assert benign_prompt.returncode == 0
        benign_context = json.loads(benign_prompt.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "Repeated-failure continuity boundary" not in benign_context

        benign_variant = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="还是选择原方案，目前没有异常。",
            turn_id="benign-turn-2",
        )
        assert benign_variant.returncode == 0
        benign_variant_context = json.loads(benign_variant.stdout)[
            "hookSpecificOutput"
        ]["additionalContext"]
        assert "Repeated-failure continuity boundary" not in benign_variant_context

        repeated_failure = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="画圈依旧不能识别，还是不行，不要再重复上次的方案。",
            turn_id="test-turn-2",
        )
        assert repeated_failure.returncode == 0, repeated_failure.stderr
        repeated_context = json.loads(repeated_failure.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        for phrase in (
            "Repeated-failure continuity boundary",
            "continuity.md",
            ".goldilocks/ACTIVE.md",
            "debug/validation record",
            "Do not repeat",
            "exact next test",
            "Keep unverified work out of CHANGELOG",
        ):
            assert phrase in repeated_context, phrase

        with database(data_dir / "orchestration.db") as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT turn_id, repeat_failure_signal, continuity_required "
                "FROM gate_injections WHERE repeat_failure_signal = 1 ORDER BY injected_at"
            ).fetchall()
        assert len(rows) == 1
        assert rows[0]["turn_id"] == "test-turn-2"
        assert rows[0]["repeat_failure_signal"] == 1
        assert rows[0]["continuity_required"] == 1

        root_session = run_hook(repo, "SessionStart", data_dir=data_dir)
        assert root_session.returncode == 0, root_session.stderr
        root_debt = json.loads(root_session.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "continuity debt" in root_debt

        no_ledger_session = run_hook(nested, "SessionStart", data_dir=data_dir)
        assert no_ledger_session.returncode == 0, no_ledger_session.stderr
        session_debt = json.loads(no_ledger_session.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "continuity debt" in session_debt
        assert ".goldilocks/ACTIVE.md" in session_debt
        assert "repository evidence" in session_debt

        no_ledger_compact = run_hook(nested, "PostCompact", data_dir=data_dir)
        assert no_ledger_compact.returncode == 0, no_ledger_compact.stderr
        compact_debt = json.loads(no_ledger_compact.stdout)["systemMessage"]
        assert "continuity debt" in compact_debt
        assert ".goldilocks/ACTIVE.md" in compact_debt
        assert "repository evidence" in compact_debt
        assert "Minimum-sufficient verification" in compact_debt
        assert "Usage is host-side and fail-silent" in compact_debt

        usage_turn = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="Show my current token usage, please.",
            turn_id="usage-survives-compact",
        )
        assert usage_turn.returncode == 0, usage_turn.stderr
        assert usage_turn.stdout.count("usage_reporter.py") == 1
        usage_compact = run_hook(
            nested, "PostCompact", data_dir=data_dir, turn_id="usage-survives-compact"
        )
        usage_compact_message = json.loads(usage_compact.stdout)["systemMessage"]
        assert usage_compact_message.count("usage_reporter.py") == 1
        assert "'--current','--turn-id','usage-survives-compact'" in usage_compact_message

        automatic_turn = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="Translate this paragraph into French.",
            turn_id="automatic-survives-compact",
            usage_visibility="automatic",
        )
        assert automatic_turn.returncode == 0, automatic_turn.stderr
        automatic_compact = run_hook(
            nested, "PostCompact", data_dir=data_dir, turn_id="automatic-survives-compact"
        )
        automatic_compact_message = json.loads(automatic_compact.stdout)["systemMessage"]
        assert automatic_compact_message.count("usage_reporter.py") == 1
        assert "Automatic visible Usage is enabled" in automatic_compact_message
        assert "'--current','--turn-id','automatic-survives-compact'" in automatic_compact_message

        discussion_turn = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="What do you think about code review as a practice? Just discuss it.",
            turn_id="discussion-does-not-survive-compact",
            usage_visibility="automatic",
        )
        assert discussion_turn.returncode == 0, discussion_turn.stderr
        discussion_compact = run_hook(
            nested,
            "PostCompact",
            data_dir=data_dir,
            turn_id="discussion-does-not-survive-compact",
        )
        assert "usage_reporter.py" not in json.loads(discussion_compact.stdout)["systemMessage"]

        chinese_turn = run_hook(
            nested,
            "UserPromptSubmit",
            data_dir=data_dir,
            prompt="请修复这个解析器并运行聚焦测试。",
            turn_id="chinese-survives-compact",
        )
        assert chinese_turn.returncode == 0, chinese_turn.stderr
        chinese_compact = run_hook(
            nested,
            "PostCompact",
            data_dir=data_dir,
            turn_id="chinese-survives-compact",
        )
        chinese_compact_message = json.loads(chinese_compact.stdout)["systemMessage"]
        assert "Goldilocks｜已启用：" in chinese_compact_message
        assert "路由=<直接|快速|标准|混合>" in chinese_compact_message
        assert "Goldilocks | Active:" not in chinese_compact_message

        ledger = repo / ".goldilocks" / "ACTIVE.md"
        ledger.parent.mkdir()
        ledger.write_text("# Active task\n", encoding="utf-8")

        with database(data_dir / "orchestration.db") as connection:
            audit_count_before_worker_events = connection.execute(
                "SELECT COUNT(*) FROM gate_injections"
            ).fetchone()[0]
        for event in ("SessionStart", "UserPromptSubmit", "PostCompact"):
            worker = run_hook(nested, event, worker=True, data_dir=data_dir)
            assert worker.returncode == 0, worker.stderr
            assert worker.stdout == "", f"Fast worker hook must stay silent for {event}"

        with database(data_dir / "orchestration.db") as connection:
            count = connection.execute("SELECT COUNT(*) FROM gate_injections").fetchone()[0]
        assert count == audit_count_before_worker_events, "Fast workers must not inject or audit the root gate"

        session = run_hook(nested, "SessionStart")
        assert session.returncode == 0, session.stderr
        session_output = json.loads(session.stdout)
        context = session_output["hookSpecificOutput"]["additionalContext"]
        assert str(ledger) in context
        assert "Exact next action" in context
        assert "Do not repeat" in context
        assert len(context.split()) <= 120

        steer = run_hook(nested, "UserPromptSubmit")
        steer_output = json.loads(steer.stdout)
        steer_context = steer_output["hookSpecificOutput"]["additionalContext"]
        assert "ADD, REPLACE, CANCEL, or QUESTION" in steer_context
        assert "applied" in steer_context
        assert "Lead with the result" in steer_context

        compact = run_hook(nested, "PostCompact")
        compact_output = json.loads(compact.stdout)
        assert "systemMessage" in compact_output
        assert str(ledger) in compact_output["systemMessage"]
        assert "Minimum-sufficient verification" in compact_output["systemMessage"]
        assert "Usage is host-side and fail-silent" in compact_output["systemMessage"]

        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        stable_command = next(
            hook["command"]
            for hook in hooks["hooks"]["UserPromptSubmit"][0]["hooks"]
            if "recovery_reminder.py" in hook["command"]
        )
        fake_bin = parent / "fake-bin"
        fake_bin.mkdir()
        fake_codex = fake_bin / "codex"
        fake_codex.write_text(
            "#!/usr/bin/env python3\n"
            "import json, os\n"
            f"print(json.dumps({{'installed':[{{'pluginId':'goldilocks@goldilocks-local',"
            "'enabled':True,'source':{'path':os.environ['FAKE_PLUGIN_ROOT']}}]}))\n",
            encoding="utf-8",
        )
        fake_codex.chmod(0o755)
        fallback_env = os.environ.copy()
        fallback_env.update(
            {
                "PATH": f"{fake_bin}{os.pathsep}{fallback_env.get('PATH', '')}",
                "PLUGIN_ROOT": str(parent / "deleted-versioned-cache"),
                "PLUGIN_DATA": str(parent / "stable-hook-data"),
                "FAKE_PLUGIN_ROOT": str(PLUGIN),
            }
        )
        stable = subprocess.run(
            stable_command,
            input=json.dumps(
                {
                    "session_id": "stable-session",
                    "turn_id": "stable-turn",
                    "cwd": str(repo),
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": "把按钮颜色改成蓝色。",
                }
            ),
            text=True,
            capture_output=True,
            check=False,
            shell=True,
            env=fallback_env,
        )
        assert stable.returncode == 0, stable.stderr
        stable_context = json.loads(stable.stdout)["hookSpecificOutput"][
            "additionalContext"
        ]
        assert "Goldilocks zero-cost gate" in stable_context
        assert "confirmed Spark quota failure" in stable_context

        assert "用量由宿主侧静默处理" in stable_context
        assert "usage_reporter.py" not in stable_context
        assert "codex plugin list" not in stable_context
        assert "路由=直接" in stable_context

    print("Goldilocks recovery hook contract passed.")


if __name__ == "__main__":
    main()
