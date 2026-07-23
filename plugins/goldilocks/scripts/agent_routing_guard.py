#!/usr/bin/env python3

"""Enforce and audit Goldilocks subagent routing without global Codex config."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SPARK_MODEL = "gpt-5.3-codex-spark"
MAX_FORK_TURNS = 4
ROUTE_PREFIXES = {
    "fast__": "fast",
    "standard__": "standard",
    "lead__": "lead",
}


def emit(output: dict[str, Any]) -> None:
    print(json.dumps(output, ensure_ascii=False))


def deny(reason: str) -> None:
    emit(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
    )


def classify(task_name: str) -> str | None:
    normalized = task_name.strip().lower()
    for prefix, tier in ROUTE_PREFIXES.items():
        if normalized.startswith(prefix):
            return tier
    return None


def valid_fork_turns(raw_value: object) -> tuple[bool, str]:
    if raw_value is None or not str(raw_value).strip():
        return False, (
            "Goldilocks blocks the implicit full-history fork. Retry with explicit "
            "fork_turns=\"none\" and a task-local brief, or a positive integer no greater than four."
        )

    value = str(raw_value).strip().lower()
    if value == "all":
        return False, (
            "Goldilocks blocks full-history subagent forks because they inherit the Lead model "
            "and duplicate unrelated context. Distill a task-local brief and retry without full-history."
        )
    if value == "none":
        return True, ""

    try:
        turns = int(value)
    except ValueError:
        return False, "fork_turns must be \"none\" or a positive integer no greater than four."
    if turns < 1 or turns > MAX_FORK_TURNS:
        return False, "Goldilocks allows at most four recent turns; otherwise keep the work local."
    return True, ""


def state_path() -> Path | None:
    raw = os.environ.get("PLUGIN_DATA")
    if not raw:
        return None
    path = Path(raw).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path / "agent-routing.jsonl"


def append_event(event: dict[str, Any]) -> None:
    path = state_path()
    if path is None:
        return
    event = {
        "at": datetime.now(timezone.utc).isoformat(),
        **event,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        handle.write("\n")


def read_events() -> list[dict[str, Any]]:
    path = state_path()
    if path is None or not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def record_plan(payload: dict[str, Any], tool_input: dict[str, Any], tier: str, model: str) -> None:
    append_event(
        {
            "event": "planned",
            "session_id": payload.get("session_id"),
            "turn_id": payload.get("turn_id"),
            "tool_use_id": payload.get("tool_use_id"),
            "task_name": tool_input.get("task_name"),
            "tier": tier,
            "expected_model": model,
            "fork_turns": tool_input.get("fork_turns"),
        }
    )


def handle_pre_tool_use(payload: dict[str, Any]) -> None:
    tool_name = str(payload.get("tool_name") or "")
    if tool_name not in {"spawn_agent", "Agent"}:
        return

    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        deny("Goldilocks could not inspect the subagent arguments, so the spawn was blocked.")
        return

    task_name = str(tool_input.get("task_name") or "")
    tier = classify(task_name)
    if tier is None:
        deny(
            "Goldilocks requires an explicit routing tier in task_name: fast__, standard__, "
            "or lead__. Classify the task and retry; do not silently inherit the Lead model."
        )
        return

    fork_valid, fork_reason = valid_fork_turns(tool_input.get("fork_turns"))
    if not fork_valid:
        deny(fork_reason)
        return

    if tier == "fast":
        rewritten = dict(tool_input)
        rewritten["model"] = SPARK_MODEL
        rewritten.pop("reasoning_effort", None)
        rewritten.pop("service_tier", None)
        rewritten.pop("agent_type", None)
        record_plan(payload, rewritten, tier, SPARK_MODEL)
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "updatedInput": rewritten,
                }
            }
        )
        return

    requested_model = str(tool_input.get("model") or "").strip()
    if not requested_model:
        deny(
            f"Goldilocks requires an explicit model for {tier.title()} subagents. "
            "Choose a model that clears the task quality gate, or keep the work with the Lead."
        )
        return

    record_plan(payload, tool_input, tier, requested_model)


def next_plan(payload: dict[str, Any]) -> dict[str, Any] | None:
    session_id = payload.get("session_id")
    events = [
        event
        for event in read_events()
        if event.get("session_id") == session_id
    ]
    used_ids = {
        event.get("plan_tool_use_id")
        for event in events
        if event.get("event") == "started"
    }
    # SubagentStart carries the child's turn id, not the parent's spawn turn id.
    # The latest unmatched plan is the safe correlation for sequential native spawns
    # and avoids reusing an older plan left behind by a failed spawn.
    for event in reversed(events):
        if event.get("event") == "planned" and event.get("tool_use_id") not in used_ids:
            return event
    return None


def handle_subagent_start(payload: dict[str, Any]) -> None:
    plan = next_plan(payload)
    if plan is None:
        return

    expected_model = str(plan.get("expected_model") or "")
    actual_model = str(payload.get("model") or "")
    matches = bool(expected_model and actual_model == expected_model)
    append_event(
        {
            "event": "started",
            "session_id": payload.get("session_id"),
            "turn_id": payload.get("turn_id"),
            "agent_id": payload.get("agent_id"),
            "agent_type": payload.get("agent_type"),
            "plan_tool_use_id": plan.get("tool_use_id"),
            "task_name": plan.get("task_name"),
            "tier": plan.get("tier"),
            "expected_model": expected_model,
            "actual_model": actual_model,
            "matches": matches,
        }
    )
    if matches:
        return

    message = (
        "Goldilocks routing mismatch: "
        f"{plan.get('task_name')} expected {expected_model}, but Codex started {actual_model or 'an unknown model'}."
    )
    emit(
        {
            "systemMessage": message,
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": (
                    f"{message} Do not execute the delegated task. Report the mismatch immediately "
                    "so the Lead can keep the work local or choose a verified route."
                ),
            },
        }
    )


def handle_subagent_stop(payload: dict[str, Any]) -> None:
    append_event(
        {
            "event": "stopped",
            "session_id": payload.get("session_id"),
            "turn_id": payload.get("turn_id"),
            "agent_id": payload.get("agent_id"),
            "agent_type": payload.get("agent_type"),
            "model": payload.get("model"),
        }
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        event = payload.get("hook_event_name")
        if event == "PreToolUse":
            handle_pre_tool_use(payload)
        elif event == "SubagentStart":
            handle_subagent_start(payload)
        elif event == "SubagentStop":
            handle_subagent_stop(payload)
    except (OSError, TypeError, ValueError) as error:
        if "payload" in locals() and payload.get("hook_event_name") == "PreToolUse":
            deny(f"Goldilocks routing guard failed closed: {error}")


if __name__ == "__main__":
    main()
