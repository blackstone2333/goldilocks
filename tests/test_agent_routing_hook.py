#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins" / "goldilocks" / "scripts" / "agent_routing_guard.py"


def run_hook(
    data_dir: Path,
    event: str,
    *,
    tool_input: dict | None = None,
    tool_name: str = "spawn_agent",
    model: str = "gpt-5.6-sol",
    agent_id: str = "agent-1",
    turn_id: str = "test-turn",
) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": "test-session",
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
                "tool_use_id": f"call-{agent_id}",
                "tool_input": tool_input or {},
            }
        )
    elif event in {"SubagentStart", "SubagentStop"}:
        payload.update(
            {
                "agent_id": agent_id,
                "agent_type": "default",
            }
        )

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


def denial_reason(result: subprocess.CompletedProcess[str]) -> str:
    output = output_json(result)
    hook_output = output["hookSpecificOutput"]
    assert hook_output["permissionDecision"] == "deny"
    return hook_output["permissionDecisionReason"]


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir)

        unrelated = run_hook(
            data_dir,
            "PreToolUse",
            tool_name="Bash",
            tool_input={"command": "git status --short"},
        )
        assert unrelated.returncode == 0, unrelated.stderr
        assert unrelated.stdout == "", "non-agent tools must stay untouched"

        unclassified = run_hook(
            data_dir,
            "PreToolUse",
            tool_input={
                "task_name": "inspect_logs",
                "fork_turns": "none",
                "message": "Inspect the bounded log set.",
            },
        )
        assert "fast__" in denial_reason(unclassified)

        full_history = run_hook(
            data_dir,
            "PreToolUse",
            tool_input={
                "task_name": "fast__inspect_logs",
                "fork_turns": "all",
                "message": "Inspect the bounded log set.",
            },
        )
        assert "full-history" in denial_reason(full_history)

        implicit_full_history = run_hook(
            data_dir,
            "PreToolUse",
            tool_input={
                "task_name": "fast__inspect_logs",
                "message": "Inspect the bounded log set.",
            },
        )
        assert "fork_turns" in denial_reason(implicit_full_history)

        oversized_fork = run_hook(
            data_dir,
            "PreToolUse",
            tool_input={
                "task_name": "fast__inspect_logs",
                "fork_turns": "5",
                "message": "Inspect the bounded log set.",
            },
        )
        assert "four" in denial_reason(oversized_fork)

        fast = run_hook(
            data_dir,
            "PreToolUse",
            tool_input={
                "task_name": "fast__inspect_logs",
                "fork_turns": "none",
                "model": "gpt-5.6-sol",
                "reasoning_effort": "xhigh",
                "message": "Inspect the bounded log set and report file evidence.",
            },
            agent_id="fast-1",
        )
        fast_output = output_json(fast)["hookSpecificOutput"]
        assert fast_output["permissionDecision"] == "allow"
        rewritten = fast_output["updatedInput"]
        assert rewritten["model"] == "gpt-5.3-codex-spark"
        assert rewritten["fork_turns"] == "none"
        assert "reasoning_effort" not in rewritten
        assert rewritten["task_name"] == "fast__inspect_logs"

        standard_without_model = run_hook(
            data_dir,
            "PreToolUse",
            tool_input={
                "task_name": "standard__known_pattern_change",
                "fork_turns": "2",
                "message": "Implement the bounded known-pattern change.",
            },
        )
        assert "explicit model" in denial_reason(standard_without_model)

        standard = run_hook(
            data_dir,
            "PreToolUse",
            tool_input={
                "task_name": "standard__known_pattern_change",
                "fork_turns": "2",
                "model": "gpt-5.6-terra",
                "message": "Implement the bounded known-pattern change.",
            },
            agent_id="standard-1",
        )
        assert standard.returncode == 0, standard.stderr
        assert standard.stdout == "", "valid explicit Standard routing should pass through"

        lead = run_hook(
            data_dir,
            "PreToolUse",
            tool_input={
                "task_name": "lead__independent_security_review",
                "fork_turns": "1",
                "model": "gpt-5.6-sol",
                "message": "Independently review the supplied diff and threat boundary.",
            },
            agent_id="lead-1",
        )
        assert lead.returncode == 0, lead.stderr
        assert lead.stdout == "", "justified explicit Lead routing should pass through"

    with tempfile.TemporaryDirectory() as temp_dir:
        matched_data = Path(temp_dir)
        planned = run_hook(
            matched_data,
            "PreToolUse",
            tool_input={
                "task_name": "fast__focused_tests",
                "fork_turns": "none",
                "message": "Write and run the focused deterministic tests.",
            },
            agent_id="match-plan",
        )
        output_json(planned)
        matched = run_hook(
            matched_data,
            "SubagentStart",
            model="gpt-5.3-codex-spark",
            agent_id="match-agent",
            turn_id="child-turn",
        )
        assert matched.returncode == 0, matched.stderr
        assert matched.stdout == "", "matching routes must not add context or UI noise"

    with tempfile.TemporaryDirectory() as temp_dir:
        mismatch_data = Path(temp_dir)
        planned = run_hook(
            mismatch_data,
            "PreToolUse",
            tool_input={
                "task_name": "fast__focused_tests",
                "fork_turns": "none",
                "message": "Write and run the focused deterministic tests.",
            },
            agent_id="mismatch-plan",
        )
        output_json(planned)
        mismatch = run_hook(
            mismatch_data,
            "SubagentStart",
            model="gpt-5.6-sol",
            agent_id="mismatch-agent",
            turn_id="other-child-turn",
        )
        mismatch_output = output_json(mismatch)
        assert "routing mismatch" in mismatch_output["systemMessage"].lower()
        context = mismatch_output["hookSpecificOutput"]["additionalContext"]
        assert "do not execute" in context.lower()
        assert "gpt-5.3-codex-spark" in context
        assert "gpt-5.6-sol" in context

    print("Goldilocks agent routing hook contract passed.")


if __name__ == "__main__":
    main()
