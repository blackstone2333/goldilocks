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
HOOK = ROOT / "plugins" / "goldilocks" / "scripts" / "agent_routing_guard.py"
SPARK_MODEL = "gpt-5.3-codex-spark"
LEAD_MODEL = "gpt-5.6-sol"
TERRA_MODEL = "gpt-5.6-terra"


def run_hook(
    data_dir: Path,
    event: str,
    *,
    tool_input: dict | None = None,
    tool_name: str = "spawn_agent",
    model: str = LEAD_MODEL,
    agent_id: str = "agent-1",
    session_id: str = "test-session",
    turn_id: str = "test-turn",
    tool_use_id: str | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": session_id,
        "turn_id": turn_id,
        "cwd": str(ROOT),
        "hook_event_name": event,
        "model": model,
        "permission_mode": "default",
    }
    if event == "PreToolUse":
        payload.update(
            {
                "tool_name": tool_name,
                "tool_use_id": tool_use_id or f"call-{agent_id}",
                "tool_input": tool_input or {},
            }
        )
    elif event in {"SubagentStart", "SubagentStop"}:
        payload.update({"agent_id": agent_id, "agent_type": "default"})

    env = os.environ.copy()
    env["PLUGIN_DATA"] = str(data_dir)
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def output_json(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode == 0, result.stderr
    assert result.stdout, "expected JSON hook output"
    return json.loads(result.stdout)


def hook_output(result: subprocess.CompletedProcess[str]) -> dict:
    return output_json(result)["hookSpecificOutput"]


def denial_reason(result: subprocess.CompletedProcess[str]) -> str:
    output = hook_output(result)
    assert output["permissionDecision"] == "deny"
    return output["permissionDecisionReason"]


def assert_silent(result: subprocess.CompletedProcess[str], reason: str) -> None:
    assert result.returncode == 0, result.stderr
    assert result.stdout == "", reason


def rows(data_dir: Path, table: str) -> list[sqlite3.Row]:
    database = data_dir / "orchestration.db"
    assert database.is_file(), "routing state must use PLUGIN_DATA/orchestration.db"
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(f"SELECT * FROM {table}").fetchall()


def spawn_input(
    task_name: str,
    *,
    fork_turns: str,
    model: str | None = None,
    reasoning_effort: str | None = None,
) -> dict:
    value = {
        "task_name": task_name,
        "fork_turns": fork_turns,
        "message": f"Execute the bounded task {task_name} and report evidence.",
    }
    if model is not None:
        value["model"] = model
    if reasoning_effort is not None:
        value["reasoning_effort"] = reasoning_effort
    return value


def test_pre_tool_contract(data_dir: Path) -> None:
    unrelated = run_hook(
        data_dir,
        "PreToolUse",
        tool_name="Bash",
        tool_input={"command": "git status --short"},
    )
    assert_silent(unrelated, "non-agent tools must stay untouched")

    unclassified = run_hook(
        data_dir,
        "PreToolUse",
        tool_input=spawn_input("inspect_logs", fork_turns="none"),
    )
    assert "fast__" in denial_reason(unclassified)

    implicit_full_history = run_hook(
        data_dir,
        "PreToolUse",
        tool_input={"task_name": "fast__inspect_logs", "message": "Inspect logs."},
    )
    assert "fork_turns" in denial_reason(implicit_full_history)

    oversized_fork = run_hook(
        data_dir,
        "PreToolUse",
        tool_input=spawn_input("fast__inspect_logs", fork_turns="5"),
    )
    assert "four" in denial_reason(oversized_fork)

    for tier in ("fast", "standard"):
        full_history = run_hook(
            data_dir,
            "PreToolUse",
            tool_input=spawn_input(
                f"{tier}__inspect_logs",
                fork_turns="all",
                model=TERRA_MODEL if tier == "standard" else None,
            ),
        )
        assert "full-history" in denial_reason(full_history)

    fast_without_model = run_hook(
        data_dir,
        "PreToolUse",
        tool_input=spawn_input(
            "fast__inspect_logs",
            fork_turns="none",
        ),
    )
    assert "explicit model" in denial_reason(fast_without_model)

    fast_terra_input = spawn_input(
        "fast__inspect_logs",
        fork_turns="none",
        model=TERRA_MODEL,
        reasoning_effort="low",
    )
    fast_terra = run_hook(
        data_dir,
        "PreToolUse",
        tool_name="collaboration.spawn_agent",
        tool_input=fast_terra_input,
        tool_use_id="fast-terra-explicit",
    )
    assert_silent(fast_terra, "explicit Terra Fast routing should pass through unchanged")
    recorded_fast = next(
        row for row in rows(data_dir, "decisions") if row["tool_use_id"] == "fast-terra-explicit"
    )
    assert recorded_fast["expected_model"] == TERRA_MODEL
    assert recorded_fast["fork_turns"] == "none"

    fast_spark_input = spawn_input(
        "fast__spark_when_available",
        fork_turns="none",
        model=SPARK_MODEL,
        reasoning_effort="low",
    )
    fast_spark = run_hook(
        data_dir,
        "PreToolUse",
        tool_input=fast_spark_input,
        tool_use_id="fast-spark-explicit",
    )
    assert_silent(fast_spark, "an explicitly selected available Spark Fast route should pass through unchanged")

    recursive_fast = run_hook(
        data_dir,
        "PreToolUse",
        model=SPARK_MODEL,
        tool_input=spawn_input("fast__recursive", fork_turns="none"),
    )
    assert "spawn" in denial_reason(recursive_fast).lower()

    standard_without_model = run_hook(
        data_dir,
        "PreToolUse",
        tool_input=spawn_input("standard__known_pattern", fork_turns="2"),
    )
    assert "explicit model" in denial_reason(standard_without_model)

    standard = run_hook(
        data_dir,
        "PreToolUse",
        tool_input=spawn_input(
            "standard__known_pattern",
            fork_turns="2",
            model=TERRA_MODEL,
            reasoning_effort="medium",
        ),
        tool_use_id="standard-explicit",
    )
    assert_silent(standard, "valid explicit Standard routing should pass through")

    lead = run_hook(
        data_dir,
        "PreToolUse",
        model=LEAD_MODEL,
        tool_input=spawn_input(
            "lead__security_review",
            fork_turns="1",
            model=LEAD_MODEL,
            reasoning_effort="high",
        ),
        tool_use_id="lead-explicit",
    )
    assert_silent(lead, "bounded explicit Lead routing should pass through")

    lead_full_history = run_hook(
        data_dir,
        "PreToolUse",
        model=LEAD_MODEL,
        tool_input=spawn_input(
            "lead__architecture_owner",
            fork_turns="all",
            model=TERRA_MODEL,
            reasoning_effort="xhigh",
        ),
        tool_use_id="lead-full-history",
    )
    rewritten_lead = hook_output(lead_full_history)["updatedInput"]
    assert rewritten_lead["fork_turns"] == "all"
    assert "model" not in rewritten_lead
    assert "reasoning_effort" not in rewritten_lead


def test_unique_model_correlation(data_dir: Path) -> None:
    session = "unique-model-session"
    fast = run_hook(
        data_dir,
        "PreToolUse",
        session_id=session,
        tool_use_id="decision-a",
        tool_input=spawn_input("fast__spark_a", fork_turns="none", model=SPARK_MODEL),
    )
    assert_silent(fast, "explicit Spark Fast plan should be recorded")
    standard = run_hook(
        data_dir,
        "PreToolUse",
        session_id=session,
        tool_use_id="decision-b",
        tool_input=spawn_input(
            "standard__terra_b", fork_turns="2", model=TERRA_MODEL
        ),
    )
    assert_silent(standard, "Terra plan should be recorded")

    spark_start = run_hook(
        data_dir,
        "SubagentStart",
        session_id=session,
        agent_id="spark-agent",
        model=SPARK_MODEL,
        turn_id="spark-child-turn",
    )
    assert_silent(spark_start, "Spark Start must uniquely match the Fast Spark decision A")
    terra_start = run_hook(
        data_dir,
        "SubagentStart",
        session_id=session,
        agent_id="terra-agent",
        model=TERRA_MODEL,
        turn_id="terra-child-turn",
    )
    assert_silent(terra_start, "Terra Start must uniquely match Terra decision B")

    executions = [row for row in rows(data_dir, "executions") if row["session_id"] == session]
    assert len(executions) == 2
    by_agent = {row["agent_id"]: row for row in executions}
    assert by_agent["spark-agent"]["expected_model"] == SPARK_MODEL
    assert by_agent["spark-agent"]["actual_model"] == SPARK_MODEL
    assert by_agent["spark-agent"]["decision_id"] is not None
    assert by_agent["terra-agent"]["expected_model"] == TERRA_MODEL
    assert by_agent["terra-agent"]["actual_model"] == TERRA_MODEL
    assert by_agent["terra-agent"]["decision_id"] is not None
    assert by_agent["spark-agent"]["decision_id"] != by_agent["terra-agent"]["decision_id"]


def test_ambiguous_same_model_correlation(data_dir: Path) -> None:
    session = "ambiguous-model-session"
    for suffix in ("a", "b"):
        planned = run_hook(
            data_dir,
            "PreToolUse",
            session_id=session,
            tool_use_id=f"same-model-{suffix}",
            tool_input=spawn_input(
                f"standard__same_model_{suffix}", fork_turns="1", model=TERRA_MODEL
            ),
        )
        assert_silent(planned, "same-model plans should be accepted")

    started = run_hook(
        data_dir,
        "SubagentStart",
        session_id=session,
        agent_id="ambiguous-agent",
        model=TERRA_MODEL,
        turn_id="ambiguous-child-turn",
    )
    assert_silent(started, "ambiguous correlation must not emit a concrete mismatch")
    execution = next(
        row
        for row in rows(data_dir, "executions")
        if row["session_id"] == session and row["agent_id"] == "ambiguous-agent"
    )
    assert execution["correlation_confidence"] == "ambiguous"
    assert execution["decision_id"] is None


def test_stop_reconnects_by_agent_id(data_dir: Path) -> None:
    session = "stop-session"
    planned = run_hook(
        data_dir,
        "PreToolUse",
        session_id=session,
        tool_use_id="stop-decision",
        tool_input=spawn_input("fast__stop_target", fork_turns="none", model=TERRA_MODEL),
    )
    assert_silent(planned, "explicit Terra Fast plan should be recorded")
    started = run_hook(
        data_dir,
        "SubagentStart",
        session_id=session,
        agent_id="stopped-agent",
        model=TERRA_MODEL,
    )
    assert_silent(started, "matching start should stay silent")
    stopped = run_hook(
        data_dir,
        "SubagentStop",
        session_id=session,
        agent_id="stopped-agent",
        model=TERRA_MODEL,
        turn_id="stop-turn",
    )
    assert_silent(stopped, "SubagentStop should stay silent")
    execution = next(
        row
        for row in rows(data_dir, "executions")
        if row["session_id"] == session and row["agent_id"] == "stopped-agent"
    )
    assert execution["stopped_at"] is not None
    experience = rows(data_dir, "experiences")[-1]
    assert experience["observed_completions"] == 1
    assert experience["verified_passes"] == 0
    assert experience["verified_failures"] == 0


def test_real_mismatch(data_dir: Path) -> None:
    session = "mismatch-session"
    planned = run_hook(
        data_dir,
        "PreToolUse",
        session_id=session,
        tool_use_id="mismatch-decision",
        tool_input=spawn_input("fast__focused_tests", fork_turns="none", model=TERRA_MODEL),
    )
    assert_silent(planned, "explicit Terra Fast plan should be recorded")
    mismatch = run_hook(
        data_dir,
        "SubagentStart",
        session_id=session,
        model=LEAD_MODEL,
        agent_id="mismatch-agent",
        turn_id="mismatch-child-turn",
    )
    output = output_json(mismatch)
    assert "routing mismatch" in output["systemMessage"].lower()
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "do not execute" in context.lower()
    assert TERRA_MODEL in context
    assert LEAD_MODEL in context


def test_unplanned_sol_soft_return(data_dir: Path) -> None:
    unplanned_sol = run_hook(
        data_dir,
        "SubagentStart",
        session_id="unplanned-sol-session",
        model=LEAD_MODEL,
        agent_id="unplanned-sol-agent",
    )
    output = output_json(unplanned_sol)
    assert "systemMessage" not in output
    context = output["hookSpecificOutput"]["additionalContext"]
    assert "Lead" in context
    assert "Fast/Standard" in context
    assert "return" in context.lower()

    unplanned_terra = run_hook(
        data_dir,
        "SubagentStart",
        session_id="unplanned-terra-session",
        model=TERRA_MODEL,
        agent_id="unplanned-terra-agent",
    )
    assert_silent(unplanned_terra, "unplanned Terra starts remain silent")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)
        test_pre_tool_contract(data_dir)
        assert rows(data_dir, "decisions"), "accepted routes must create decisions"
        test_unique_model_correlation(data_dir)
        test_ambiguous_same_model_correlation(data_dir)
        test_stop_reconnects_by_agent_id(data_dir)
        test_real_mismatch(data_dir)
        test_unplanned_sol_soft_return(data_dir)

    print("Goldilocks v0.4.4 agent routing hook contract passed.")


if __name__ == "__main__":
    main()
