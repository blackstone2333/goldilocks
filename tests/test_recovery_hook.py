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
HOOK = ROOT / "plugins" / "goldilocks" / "scripts" / "recovery_reminder.py"


def run_hook(
    cwd: Path,
    event: str,
    *,
    worker: bool = False,
    data_dir: Path | None = None,
    prompt: str = "Build and test the full-stack feature with the specialist Skill.",
    turn_id: str = "test-turn",
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

        no_ledger_steer = run_hook(nested, "UserPromptSubmit", data_dir=data_dir)
        assert no_ledger_steer.returncode == 0, no_ledger_steer.stderr
        style_output = json.loads(no_ledger_steer.stdout)
        style_context = style_output["hookSpecificOutput"]["additionalContext"]
        assert len(style_context.split()) <= 90
        assert "Lead with the result" in style_context
        assert "Omit work preambles" in style_context
        assert "Report only changed state" in style_context
        assert "decisive evidence" in style_context
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
                "routing_experiment_id "
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
            "read orchestrate.md",
            "compact ROUTE line",
            "WRITE_READY",
            "READ_READY",
            "project-level organization",
            "active threads",
            "shared write surface",
            "read-only diagnosis",
            "Existing parallel ownership means mixed",
            "route_unavailable must name",
            "one-sentence DETAIL",
            "not default to doing worker-ready work",
            "advisory; do not force delegation",
        ):
            assert phrase in rationale_context, phrase
        with sqlite3.connect(data_dir / "orchestration.db") as connection:
            connection.row_factory = sqlite3.Row
            rationale_row = connection.execute(
                "SELECT routing_rationale_candidate, routing_experiment_id "
                "FROM gate_injections WHERE turn_id = 'rationale-turn'"
            ).fetchone()
        assert rationale_row["routing_rationale_candidate"] == 1
        assert rationale_row["routing_experiment_id"] == "routing-rationale-v2"
        assert multi_unit_prompt.encode() not in (
            data_dir / "orchestration.db"
        ).read_bytes(), "routing audit must not retain candidate prompt text"

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

        ledger = repo / ".goldilocks" / "ACTIVE.md"
        ledger.parent.mkdir()
        ledger.write_text("# Active task\n", encoding="utf-8")

        for event in ("SessionStart", "UserPromptSubmit", "PostCompact"):
            worker = run_hook(nested, event, worker=True, data_dir=data_dir)
            assert worker.returncode == 0, worker.stderr
            assert worker.stdout == "", f"Fast worker hook must stay silent for {event}"

        with sqlite3.connect(data_dir / "orchestration.db") as connection:
            count = connection.execute("SELECT COUNT(*) FROM gate_injections").fetchone()[0]
        assert count == 6, "Fast workers must not inject or audit the root gate"

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

    print("Goldilocks recovery hook contract passed.")


if __name__ == "__main__":
    main()
