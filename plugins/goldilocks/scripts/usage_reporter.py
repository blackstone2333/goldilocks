#!/usr/bin/env python3

"""Show one compact per-turn model/token receipt without another model call."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


POLICY_VERSION = "0.4.5-exp3.1"
TRANSCRIPT_TAIL_BYTES = 8 * 1024 * 1024
TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def latest_usage(path: object) -> dict[str, int] | None:
    if not isinstance(path, str) or not path:
        return None
    transcript = Path(path).expanduser()
    if not transcript.is_file():
        return None
    try:
        with transcript.open("rb") as handle:
            size = handle.seek(0, os.SEEK_END)
            handle.seek(max(0, size - TRANSCRIPT_TAIL_BYTES))
            data = handle.read()
        for raw in reversed(data.splitlines()):
            try:
                record = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            payload = record.get("payload")
            if record.get("type") != "event_msg" or not isinstance(payload, dict):
                continue
            info = payload.get("info")
            total = info.get("total_token_usage") if isinstance(info, dict) else None
            if not isinstance(total, dict):
                continue
            return {
                key: max(0, int(total.get(key) or 0))
                for key in TOKEN_KEYS
            }
    except (OSError, TypeError, ValueError):
        return None
    return None


def connect(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(root / "orchestration.db", timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS task_usage_baselines (
            session_id TEXT NOT NULL,
            turn_id TEXT NOT NULL,
            root_model TEXT,
            baseline_input_tokens INTEGER NOT NULL DEFAULT 0,
            baseline_cached_input_tokens INTEGER NOT NULL DEFAULT 0,
            baseline_output_tokens INTEGER NOT NULL DEFAULT 0,
            baseline_available INTEGER NOT NULL DEFAULT 0,
            started_at TEXT NOT NULL,
            last_receipt_hash TEXT,
            last_reported_at TEXT,
            policy_version TEXT NOT NULL,
            PRIMARY KEY(session_id, turn_id)
        )
        """
    )
    connection.execute(
        "DELETE FROM task_usage_baselines WHERE julianday('now') - julianday(started_at) > 30"
    )
    return connection


def record_baseline(connection: sqlite3.Connection, payload: dict[str, Any]) -> None:
    session_id = str(payload.get("session_id") or "")
    turn_id = str(payload.get("turn_id") or "")
    if not session_id or not turn_id:
        return
    usage = latest_usage(payload.get("transcript_path"))
    values = usage or {key: 0 for key in TOKEN_KEYS}
    connection.execute(
        """
        INSERT OR IGNORE INTO task_usage_baselines (
            session_id, turn_id, root_model, baseline_input_tokens,
            baseline_cached_input_tokens, baseline_output_tokens,
            baseline_available, started_at, policy_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            turn_id,
            str(payload.get("model") or "unknown"),
            values["input_tokens"],
            values["cached_input_tokens"],
            values["output_tokens"],
            int(usage is not None),
            now(),
            POLICY_VERSION,
        ),
    )


def table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {
        str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")
    }


def add_usage(
    models: dict[str, dict[str, int]],
    model: object,
    input_tokens: object,
    cached_input_tokens: object,
    output_tokens: object,
) -> None:
    name = str(model or "unknown")
    row = models.setdefault(name, {key: 0 for key in TOKEN_KEYS})
    row["input_tokens"] += max(0, int(input_tokens or 0))
    row["cached_input_tokens"] += max(0, int(cached_input_tokens or 0))
    row["output_tokens"] += max(0, int(output_tokens or 0))
    row["cached_input_tokens"] = min(
        row["input_tokens"], row["cached_input_tokens"]
    )


def worker_usage(
    connection: sqlite3.Connection,
    session_id: str,
    turn_id: str,
    started_at: str,
) -> tuple[dict[str, dict[str, int]], int]:
    models: dict[str, dict[str, int]] = {}
    missing = 0
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if {"decisions", "executions"}.issubset(tables):
        decision_columns = table_columns(connection, "decisions")
        execution_columns = table_columns(connection, "executions")
        required_decisions = {"decision_id", "session_id", "turn_id"}
        required_executions = {"decision_id", "actual_model", "stopped_at", *TOKEN_KEYS}
        if required_decisions.issubset(decision_columns) and required_executions.issubset(
            execution_columns
        ):
            rows = connection.execute(
                """
                SELECT execution.actual_model, execution.input_tokens,
                       execution.cached_input_tokens, execution.output_tokens
                FROM executions AS execution
                JOIN decisions AS decision
                    ON decision.decision_id = execution.decision_id
                WHERE decision.session_id = ? AND decision.turn_id = ?
                  AND execution.stopped_at IS NOT NULL
                """,
                (session_id, turn_id),
            ).fetchall()
            for row in rows:
                if all(row[key] is None for key in TOKEN_KEYS):
                    missing += 1
                else:
                    add_usage(models, row["actual_model"], *(row[key] for key in TOKEN_KEYS))

    if "external_routes" in tables:
        columns = table_columns(connection, "external_routes")
        required = {"parent_session_id", "started_at", "actual_model", "expected_model", *TOKEN_KEYS}
        if required.issubset(columns):
            stopped_filter = "AND stopped_at IS NOT NULL" if "stopped_at" in columns else ""
            rows = connection.execute(
                f"""
                SELECT actual_model, expected_model, input_tokens,
                       cached_input_tokens, output_tokens
                FROM external_routes
                WHERE parent_session_id = ? AND started_at >= ? {stopped_filter}
                """,
                (session_id, started_at),
            ).fetchall()
            for row in rows:
                if all(row[key] is None for key in TOKEN_KEYS):
                    missing += 1
                else:
                    add_usage(
                        models,
                        row["actual_model"] or row["expected_model"],
                        *(row[key] for key in TOKEN_KEYS),
                    )
    return models, missing


def delta(current: int, baseline: int) -> int:
    return current - baseline if current >= baseline else current


def format_duration(started_at: str) -> str:
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        elapsed = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
    except (TypeError, ValueError):
        return "unknown"
    minutes, seconds = divmod(elapsed, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m{seconds:02d}s"
    return f"{seconds}s"


def format_receipt(
    models: dict[str, dict[str, int]],
    *,
    root_unknown: bool,
    missing_workers: int,
    started_at: str,
) -> tuple[str, str]:
    ranked = sorted(
        models.items(),
        key=lambda item: item[1]["input_tokens"] + item[1]["output_tokens"],
        reverse=True,
    )
    parts: list[str] = []
    total = 0
    for model, usage in ranked:
        processing = usage["input_tokens"] + usage["output_tokens"]
        total += processing
        parts.append(
            f"{model}: in {usage['input_tokens']:,} "
            f"({usage['cached_input_tokens']:,} cached) + out "
            f"{usage['output_tokens']:,} = {processing:,}"
        )
    if root_unknown:
        parts.append("root: token telemetry unavailable")
    if missing_workers:
        parts.append(f"{missing_workers} worker(s): token telemetry unavailable")
    if not parts:
        parts.append("token telemetry unavailable")
    message = (
        "Goldilocks usage | "
        + "; ".join(parts)
        + f" | total {total:,} tokens · wall {format_duration(started_at)}"
    )
    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "models": models,
                "root_unknown": root_unknown,
                "missing_workers": missing_workers,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return message, fingerprint


def build_receipt(
    connection: sqlite3.Connection, payload: dict[str, Any]
) -> str | None:
    session_id = str(payload.get("session_id") or "")
    turn_id = str(payload.get("turn_id") or "")
    if not session_id or not turn_id:
        return None
    baseline = connection.execute(
        "SELECT * FROM task_usage_baselines WHERE session_id = ? AND turn_id = ?",
        (session_id, turn_id),
    ).fetchone()
    if baseline is None:
        return None
    models, missing_workers = worker_usage(
        connection, session_id, turn_id, str(baseline["started_at"])
    )
    current = latest_usage(payload.get("transcript_path"))
    root_unknown = not bool(baseline["baseline_available"]) or current is None
    if not root_unknown and current is not None:
        add_usage(
            models,
            str(payload.get("model") or baseline["root_model"] or "unknown"),
            delta(current["input_tokens"], baseline["baseline_input_tokens"]),
            delta(
                current["cached_input_tokens"],
                baseline["baseline_cached_input_tokens"],
            ),
            delta(current["output_tokens"], baseline["baseline_output_tokens"]),
        )
    message, fingerprint = format_receipt(
        models,
        root_unknown=root_unknown,
        missing_workers=missing_workers,
        started_at=str(baseline["started_at"]),
    )
    if baseline["last_receipt_hash"] == fingerprint:
        return None
    connection.execute(
        """
        UPDATE task_usage_baselines
        SET last_receipt_hash = ?, last_reported_at = ?
        WHERE session_id = ? AND turn_id = ?
        """,
        (fingerprint, now(), session_id, turn_id),
    )
    return message


def main() -> None:
    event = ""
    try:
        payload = json.load(sys.stdin)
        event = str(payload.get("hook_event_name") or "")
        if os.environ.get("GOLDILOCKS_WORKER") == "1":
            if event == "Stop":
                print("{}")
            return
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            if event == "Stop":
                print("{}")
            return
        with connect(Path(configured).expanduser()) as connection:
            if event == "UserPromptSubmit":
                record_baseline(connection, payload)
                return
            if event == "Stop":
                message = build_receipt(connection, payload)
                print(json.dumps({"systemMessage": message} if message else {}, ensure_ascii=False))
    except (OSError, sqlite3.Error, TypeError, ValueError, json.JSONDecodeError):
        if event == "Stop":
            print("{}")


if __name__ == "__main__":
    main()
