#!/usr/bin/env python3

"""Read only allowlisted lifecycle facts from one exact native child rollout."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


TAIL_BYTES = 1024 * 1024
USAGE_LIMIT_CODES = {"usage_limit_exceeded", "usage_limit_reached"}


@dataclass(frozen=True)
class TerminalState:
    completed_at: str
    outcome: str
    quota_reset_at: int | None


def session_roots() -> list[Path]:
    configured = os.environ.get("GOLDILOCKS_SESSION_ROOTS")
    if configured:
        return [
            Path(value).expanduser()
            for value in configured.split(os.pathsep)
            if value.strip()
        ]
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return [codex_home / "sessions", codex_home / "archived_sessions"]


def valid_transcript(path: Path, agent_id: str) -> bool:
    return (
        bool(agent_id)
        and path.name.startswith("rollout-")
        and path.name.endswith(f"-{agent_id}.jsonl")
        and path.is_file()
    )


def rollout_paths(agent_id: str, explicit: object = None) -> list[Path]:
    paths: dict[str, Path] = {}
    if isinstance(explicit, str) and explicit.strip():
        candidate = Path(explicit).expanduser()
        if valid_transcript(candidate, agent_id):
            resolved = candidate.resolve()
            paths[str(resolved)] = resolved
    for root in session_roots():
        if not root.is_dir():
            continue
        try:
            for candidate in root.rglob(f"rollout-*-{agent_id}.jsonl"):
                if valid_transcript(candidate, agent_id):
                    resolved = candidate.resolve()
                    paths[str(resolved)] = resolved
        except OSError:
            continue
    return list(paths.values())


def tail_records(path: Path) -> list[dict[str, object]]:
    with path.open("rb") as handle:
        size = handle.seek(0, os.SEEK_END)
        offset = max(0, size - TAIL_BYTES)
        handle.seek(offset)
        lines = handle.read().splitlines()
    if offset and lines:
        lines = lines[1:]
    records: list[dict[str, object]] = []
    for raw in lines:
        try:
            value = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def exhausted_reset(rate_limits: object) -> int | None:
    if not isinstance(rate_limits, dict):
        return None
    name = str(rate_limits.get("limit_name") or "").lower()
    if name and "spark" not in name:
        return None
    resets: list[int] = []
    for key in ("primary", "secondary"):
        window = rate_limits.get(key)
        if not isinstance(window, dict):
            continue
        used = window.get("used_percent")
        reset = window.get("resets_at")
        if isinstance(used, (int, float)) and used >= 100 and isinstance(reset, int):
            resets.append(reset)
    return max(resets) if resets else None


def terminal_state_from_records(records: list[dict[str, object]]) -> TerminalState | None:
    quota_reset_at: int | None = None
    terminal: TerminalState | None = None
    latest_lifecycle: tuple[str, str] | None = None
    for record in records:
        payload = record.get("payload")
        if record.get("type") != "event_msg" or not isinstance(payload, dict):
            continue
        event = str(payload.get("type") or "")
        timestamp = record.get("timestamp")
        if event in {"task_started", "task_complete"} and isinstance(timestamp, str):
            if latest_lifecycle is None or timestamp > latest_lifecycle[0]:
                latest_lifecycle = (timestamp, event)
        if event == "token_count":
            observed_reset = exhausted_reset(payload.get("rate_limits"))
            if observed_reset is not None:
                quota_reset_at = max(quota_reset_at or observed_reset, observed_reset)
            continue
        if event != "task_complete":
            continue
        if not isinstance(timestamp, str) or not timestamp:
            continue
        error = payload.get("error")
        if error is None:
            outcome = "completed"
        elif isinstance(error, dict) and str(error.get("codex_error_info") or "") in USAGE_LIMIT_CODES:
            outcome = "usage_limit"
        else:
            outcome = "other_error"
        terminal = TerminalState(timestamp, outcome, quota_reset_at)
    if latest_lifecycle is None or latest_lifecycle[1] != "task_complete":
        return None
    return terminal


def read_terminal_state(agent_id: str, explicit: object = None) -> TerminalState | None:
    latest: TerminalState | None = None
    for path in rollout_paths(agent_id, explicit):
        try:
            state = terminal_state_from_records(tail_records(path))
        except OSError:
            continue
        if state is not None and (
            latest is None or state.completed_at > latest.completed_at
        ):
            latest = state
    return latest
