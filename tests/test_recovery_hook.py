#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
HOOK = ROOT / "plugins" / "goldilocks" / "scripts" / "recovery_reminder.py"


def run_hook(
    cwd: Path,
    event: str,
    *,
    worker: bool = False,
    data_dir: Path | None = None,
    prompt: str = "Build and test the full-stack feature with the specialist Skill.",
    turn_id: str = "test-turn",
    session_roots: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": "test-session",
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
        with sqlite3.connect(data_dir / "orchestration.db") as connection:
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
        compact_usage_context = json.loads(compact_without_recovery.stdout)["systemMessage"]
        assert "Before final" in compact_usage_context
        assert "usage_reporter.py" in compact_usage_context
        assert "--current" in compact_usage_context
        assert "append nonempty Usage" in compact_usage_context

        no_ledger_steer = run_hook(nested, "UserPromptSubmit", data_dir=data_dir)
        assert no_ledger_steer.returncode == 0, no_ledger_steer.stderr
        style_output = json.loads(no_ledger_steer.stdout)
        style_context = style_output["hookSpecificOutput"]["additionalContext"]
        assert len(style_context.split()) <= 105
        assert "Lead with the result" in style_context
        assert "Omit work preambles" in style_context
        assert "Report only changed state" in style_context
        assert "decisive evidence" in style_context
        assert "For defect work" in style_context
        assert "evidence-backed cause" in style_context
        assert "explicitly unknown" in style_context
        assert "fix and verification" in style_context
        assert "Before final" in style_context
        assert "usage_reporter.py" in style_context
        assert "--current" in style_context
        assert "append nonempty Usage" in style_context
        assert "never estimate" in style_context
        assert "silently apply the Goldilocks zero-cost gate" in style_context
        assert "before any specialist Skill" in style_context
        assert "goldilocks:goldilocks" in style_context
        assert "otherwise take its Direct exit" in style_context
        assert "pure conversation" in style_context
        assert "Likely multi-unit work detected" not in style_context

        with sqlite3.connect(data_dir / "orchestration.db") as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT session_id, turn_id, cwd_hash, prompt_fingerprint, ledger_present, "
                "repeat_failure_signal, continuity_required, routing_rationale_candidate, "
                "routing_experiment_id, delegation_grant_active "
                "FROM gate_injections"
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

        repeated = run_hook(nested, "UserPromptSubmit", data_dir=data_dir)
        assert repeated.returncode == 0, repeated.stderr
        with sqlite3.connect(data_dir / "orchestration.db") as connection:
            count = connection.execute("SELECT COUNT(*) FROM gate_injections").fetchone()[0]
        assert count == 1, "the same prompt turn must produce one audit record"

        multi_unit_prompt = (
            "请完成以下开发任务：\n"
            "1、修复画布上下文记忆。\n"
            "2、实现 Agent 连接。\n"
            "3、补齐测试、文档和发布检查。"
        )
        with sqlite3.connect(data_dir / "orchestration.db") as connection:
            connection.execute(
                "CREATE TABLE project_grants (cwd_hash TEXT PRIMARY KEY, active INTEGER, "
                "granted_at TEXT, revoked_at TEXT, policy_version TEXT)"
            )
            connection.execute(
                "INSERT INTO project_grants VALUES (?, 1, 'now', NULL, '0.5.0-alpha.1-exp3.2')",
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
            "ROUTE line",
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
        assert len(rationale_context.split()) <= 285
        with sqlite3.connect(data_dir / "orchestration.db") as connection:
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
        with sqlite3.connect(lifecycle_data / "orchestration.db") as connection:
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
        with sqlite3.connect(lifecycle_data / "orchestration.db") as connection:
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
        with sqlite3.connect(data_dir / "orchestration.db") as connection:
            simple_candidate = connection.execute(
                "SELECT routing_rationale_candidate FROM gate_injections "
                "WHERE turn_id = 'simple-change'"
            ).fetchone()[0]
        assert simple_candidate == 0

        with sqlite3.connect(data_dir / "orchestration.db") as connection:
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

        with sqlite3.connect(data_dir / "orchestration.db") as connection:
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
        assert "usage_reporter.py" in compact_debt

        ledger = repo / ".goldilocks" / "ACTIVE.md"
        ledger.parent.mkdir()
        ledger.write_text("# Active task\n", encoding="utf-8")

        for event in ("SessionStart", "UserPromptSubmit", "PostCompact"):
            worker = run_hook(nested, event, worker=True, data_dir=data_dir)
            assert worker.returncode == 0, worker.stderr
            assert worker.stdout == "", f"Fast worker hook must stay silent for {event}"

        with sqlite3.connect(data_dir / "orchestration.db") as connection:
            count = connection.execute("SELECT COUNT(*) FROM gate_injections").fetchone()[0]
        assert count == 7, "Fast workers must not inject or audit the root gate"

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
        assert "usage_reporter.py" in compact_output["systemMessage"]

        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        stable_command = hooks["hooks"]["UserPromptSubmit"][0]["hooks"][0]["command"]
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

        live_plugin = parent / "live-plugin"
        live_scripts = live_plugin / "scripts"
        live_scripts.mkdir(parents=True)
        (live_scripts / "usage_reporter.py").write_text(
            'print("Usage: dynamically resolved")\n', encoding="utf-8"
        )
        usage_command = stable_context.split("Before final: run `", 1)[1].split("`;", 1)[0]
        assert str(PLUGIN) not in usage_command
        assert "codex" in usage_command and "plugin" in usage_command
        current_env = fallback_env.copy()
        current_env["FAKE_PLUGIN_ROOT"] = str(live_plugin)
        current = subprocess.run(
            usage_command,
            text=True,
            capture_output=True,
            check=False,
            shell=True,
            env=current_env,
        )
        assert current.returncode == 0, current.stderr
        assert current.stdout.strip() == "Usage: dynamically resolved"

    print("Goldilocks recovery hook contract passed.")


if __name__ == "__main__":
    main()
