#!/usr/bin/env python3

"""Show one compact per-turn model/token receipt without another model call."""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_naming import model_display_label


POLICY_VERSION = "0.5.1"
TRANSCRIPT_TAIL_BYTES = 8 * 1024 * 1024
TOKEN_KEYS = ("input_tokens", "cached_input_tokens", "output_tokens")
MODEL_ORDER = {label: index for index, label in enumerate(("Sol", "Terra", "Luna", "Spark"))}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def usage_from_record(record: object) -> dict[str, int] | None:
    if not isinstance(record, dict) or record.get("type") != "event_msg":
        return None
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return None
    info = payload.get("info")
    total = info.get("total_token_usage") if isinstance(info, dict) else None
    if not isinstance(total, dict):
        return None
    return {key: max(0, int(total.get(key) or 0)) for key in TOKEN_KEYS}


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
            usage = usage_from_record(record)
            if usage is not None:
                return usage
    except (OSError, TypeError, ValueError):
        return None
    return None


def completed_task_usage_since(path: object, started_at: str) -> dict[str, int] | None:
    """Sum completed child-task deltas after a Lead baseline.

    Reused Codex agents append new task segments to one cumulative rollout. Their
    lifetime total cannot be charged to the later Lead turn, so each completed
    segment is measured from its immediately preceding cumulative checkpoint.
    """

    if not isinstance(path, str) or not path:
        return None
    transcript = Path(path).expanduser()
    cutoff = parse_timestamp(started_at)
    if not transcript.is_file() or cutoff is None:
        return None
    totals = {key: 0 for key in TOKEN_KEYS}
    last_usage: dict[str, int] | None = None
    active: dict[str, dict[str, dict[str, int] | None]] = {}
    completed = 0
    try:
        with transcript.open(encoding="utf-8") as handle:
            for raw in handle:
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                usage = usage_from_record(record)
                if usage is not None:
                    last_usage = usage
                    for segment in active.values():
                        segment["latest"] = dict(usage)
                    continue
                if record.get("type") != "event_msg":
                    continue
                payload = record.get("payload")
                if not isinstance(payload, dict):
                    continue
                event = payload.get("type")
                turn_id = str(payload.get("turn_id") or "")
                timestamp = parse_timestamp(record.get("timestamp"))
                if event == "task_started":
                    if turn_id and timestamp is not None and timestamp >= cutoff:
                        active[turn_id] = {
                            "baseline": dict(last_usage) if last_usage is not None else None,
                            "latest": None,
                        }
                    continue
                if event != "task_complete" or turn_id not in active:
                    continue
                segment = active.pop(turn_id)
                baseline = segment["baseline"]
                latest = segment["latest"]
                if baseline is None or latest is None:
                    continue
                for key in TOKEN_KEYS:
                    totals[key] += delta(latest[key], baseline[key])
                completed += 1
    except (OSError, TypeError, ValueError):
        return None
    return totals if completed else None


def forked_task_usage_since(
    path: object, started_at: str
) -> tuple[dict[str, int] | None, bool]:
    """Measure a fresh native fork from its last inherited checkpoint.

    Codex may copy the parent rollout history into a child and keep the copied
    cumulative token totals.  SubagentStop can therefore report a lifetime-like
    value.  The SubagentStart timestamp falls after the copied history and before
    the child's first model response, so the last checkpoint before that boundary
    is the correct baseline.
    """

    if not isinstance(path, str) or not path:
        return None, False
    transcript = Path(path).expanduser()
    cutoff = parse_timestamp(started_at)
    if not transcript.is_file() or cutoff is None:
        return None, False
    forked = False
    baseline: dict[str, int] | None = None
    current: dict[str, int] | None = None
    try:
        with transcript.open(encoding="utf-8") as handle:
            for raw in handle:
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if record.get("type") == "session_meta":
                    payload = record.get("payload")
                    source = payload.get("source") if isinstance(payload, dict) else None
                    subagent = source.get("subagent") if isinstance(source, dict) else None
                    spawn = subagent.get("thread_spawn") if isinstance(subagent, dict) else None
                    if isinstance(spawn, dict):
                        forked = True
                usage = usage_from_record(record)
                if usage is None:
                    continue
                timestamp = parse_timestamp(record.get("timestamp"))
                if timestamp is None:
                    continue
                if timestamp < cutoff:
                    baseline = usage
                else:
                    current = usage
    except (OSError, TypeError, ValueError):
        return None, forked
    if not forked or baseline is None or current is None:
        return None, forked
    return ({key: delta(current[key], baseline[key]) for key in TOKEN_KEYS}, True)


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
            transcript_path TEXT,
            started_at TEXT NOT NULL,
            last_receipt_hash TEXT,
            last_reported_at TEXT,
            policy_version TEXT NOT NULL,
            PRIMARY KEY(session_id, turn_id)
        )
        """
    )
    columns = {
        str(row[1])
        for row in connection.execute("PRAGMA table_info(task_usage_baselines)")
    }
    if "transcript_path" not in columns:
        connection.execute(
            "ALTER TABLE task_usage_baselines ADD COLUMN transcript_path TEXT"
        )
    connection.execute(
        "DELETE FROM task_usage_baselines WHERE julianday('now') - julianday(started_at) > 30"
    )
    return connection


def connect_readonly(database: Path) -> sqlite3.Connection:
    """Open the existing ledger without migrations, journals, or backfills."""

    uri = f"file:{quote(str(database.resolve()), safe='/')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA query_only = ON")
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
            baseline_available, transcript_path, started_at, policy_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            turn_id,
            str(payload.get("model") or "unknown"),
            values["input_tokens"],
            values["cached_input_tokens"],
            values["output_tokens"],
            int(usage is not None),
            str(payload.get("transcript_path") or "") or None,
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


def is_verified_fresh_fork(row: sqlite3.Row) -> bool:
    """Whether a completed execution is an accepted fresh-context dispatch."""

    return (
        row["decision_fork_turns"] == "none"
        and row["decision_status"] == "verified_pass"
        and row["stopped_at"] is not None
    )


def verified_fresh_fork_db_usage(row: sqlite3.Row) -> dict[str, object] | None:
    """Return complete posthoc usage only for an explicit fresh verified fork.

    A forked transcript can begin without the inherited checkpoint required to
    calculate a transcript delta.  The runtime inspector may nevertheless have
    recorded complete child-only usage.  That record is safe for this turn only
    when the original dispatch explicitly started a fresh context and the
    completed execution has subsequently passed verification.
    """

    if (
        not is_verified_fresh_fork(row)
        or any(row[key] is None for key in TOKEN_KEYS)
    ):
        return None
    return {key: row[key] for key in TOKEN_KEYS}


def worker_usage(
    connection: sqlite3.Connection,
    session_id: str,
    turn_id: str,
    started_at: str,
) -> tuple[dict[str, dict[str, int]], int]:
    models: dict[str, dict[str, int]] = {}
    missing = 0
    owner_sessions = {session_id}
    pending_sessions = [session_id]
    seen_agents: set[str] = set()
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if "executions" in tables:
        decision_columns = (
            table_columns(connection, "decisions") if "decisions" in tables else set()
        )
        execution_columns = table_columns(connection, "executions")
        required_executions = {
            "agent_id",
            "started_at",
            "stopped_at",
            "actual_model",
            *TOKEN_KEYS,
        }
        can_join_decisions = {
            "decision_id",
            "session_id",
        }.issubset(decision_columns) and "decision_id" in execution_columns
        can_read_fork_proof = {
            "decision_id",
            "fork_turns",
            "status",
        }.issubset(decision_columns) and "decision_id" in execution_columns
        has_execution_owner = "session_id" in execution_columns
        if required_executions.issubset(execution_columns) and (
            has_execution_owner or can_join_decisions
        ):
            while pending_sessions:
                owner_session = pending_sessions.pop()
                if has_execution_owner:
                    source = "FROM executions AS execution"
                    owner_clause = "execution.session_id = ?"
                else:
                    source = (
                        "FROM executions AS execution JOIN decisions AS decision "
                        "ON decision.decision_id = execution.decision_id"
                    )
                    owner_clause = "decision.session_id = ?"
                decision_projection = (
                    ", decision.fork_turns AS decision_fork_turns, "
                    "decision.status AS decision_status"
                    if can_read_fork_proof
                    else ", NULL AS decision_fork_turns, NULL AS decision_status"
                )
                decision_join = (
                    " LEFT JOIN decisions AS decision "
                    "ON decision.decision_id = execution.decision_id"
                    if can_read_fork_proof and has_execution_owner
                    else ""
                )
                rows = connection.execute(
                    f"""
                    SELECT execution.agent_id, execution.actual_model,
                           execution.started_at, execution.stopped_at,
                           execution.input_tokens, execution.cached_input_tokens,
                           execution.output_tokens {decision_projection}
                    {source}{decision_join}
                    WHERE {owner_clause} AND execution.stopped_at IS NOT NULL
                      AND (
                          julianday(execution.stopped_at) >= julianday(?)
                          OR julianday(execution.started_at) >= julianday(?)
                      )
                    """,
                    (owner_session, started_at, started_at),
                ).fetchall()
                for row in rows:
                    agent_id = str(row["agent_id"] or "")
                    if agent_id and agent_id in seen_agents:
                        continue
                    if agent_id:
                        seen_agents.add(agent_id)
                        owner_sessions.add(agent_id)
                        pending_sessions.append(agent_id)
                    transcript = find_transcript(agent_id, None)
                    execution_started = parse_timestamp(row["started_at"])
                    cutoff = parse_timestamp(started_at)
                    reused = (
                        execution_started is not None
                        and cutoff is not None
                        and execution_started < cutoff
                    )
                    if reused:
                        values = completed_task_usage_since(
                            str(transcript) if transcript is not None else None,
                            started_at,
                        )
                        if values is None:
                            missing += 1
                            continue
                    else:
                        values = None
                        if transcript is not None:
                            values, _forked = forked_task_usage_since(
                                str(transcript), str(row["started_at"])
                            )
                        if values is None:
                            # A missing, unreadable, or malformed transcript is
                            # not permission to trust lifetime-looking DB totals.
                            # Use the posthoc record only when the dispatch is
                            # provably fresh, complete, and accepted.
                            values = verified_fresh_fork_db_usage(row)
                            if (
                                values is None
                                and is_verified_fresh_fork(row)
                                and transcript is not None
                            ):
                                values = latest_usage(str(transcript))
                            if values is None:
                                missing += 1
                                continue
                    add_usage(
                        models,
                        row["actual_model"],
                        *(values[key] for key in TOKEN_KEYS),
                    )

    if "external_routes" in tables:
        columns = table_columns(connection, "external_routes")
        required = {"parent_session_id", "started_at", "actual_model", "expected_model", *TOKEN_KEYS}
        if required.issubset(columns):
            stopped_filter = "AND stopped_at IS NOT NULL" if "stopped_at" in columns else ""
            for owner_session in owner_sessions:
                rows = connection.execute(
                    f"""
                    SELECT actual_model, expected_model, input_tokens,
                           cached_input_tokens, output_tokens
                    FROM external_routes
                    WHERE parent_session_id = ? AND started_at >= ? {stopped_filter}
                    """,
                    (owner_session, started_at),
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


def resolve_data_root() -> Path:
    configured = os.environ.get("PLUGIN_DATA")
    if configured:
        return Path(configured).expanduser()
    candidates = sorted(
        path.parent
        for path in (Path.home() / ".codex" / "plugins" / "data").glob(
            "goldilocks-*/orchestration.db"
        )
    )
    if len(candidates) == 1:
        return candidates[0]
    return (
        Path.home()
        / ".codex"
        / "plugins"
        / "data"
        / "goldilocks-goldilocks-local"
    )


def find_transcript(session_id: str, stored: object) -> Path | None:
    if isinstance(stored, str) and stored:
        path = Path(stored).expanduser()
        if path.is_file():
            return path
    configured = os.environ.get("GOLDILOCKS_SESSION_ROOTS")
    roots = (
        [Path(value).expanduser() for value in configured.split(os.pathsep) if value]
        if configured
        else [
            Path.home() / ".codex" / "sessions",
            Path.home() / ".codex" / "archived_sessions",
        ]
    )
    matches: list[Path] = []
    for root in roots:
        if root.is_dir():
            matches.extend(root.rglob(f"*{session_id}.jsonl"))
    return max(matches, key=lambda path: path.stat().st_mtime) if matches else None


def format_current(
    models: dict[str, dict[str, int]],
    language: str = "en",
    started_at: str | None = None,
    *,
    unavailable_root: str | None = None,
    missing_workers: int = 0,
) -> str | None:
    if not models and unavailable_root is None and not missing_workers:
        return None
    rows: list[tuple[int, str, dict[str, int]]] = []
    for model, usage in models.items():
        label = model_display_label(model)
        rows.append((MODEL_ORDER.get(label, len(MODEL_ORDER)), label, usage))
    parts: list[str] = []
    total = 0
    for _order, label, usage in sorted(rows, key=lambda row: (row[0], row[1])):
        processing = usage["input_tokens"] + usage["output_tokens"]
        if processing == 0:
            continue
        total += processing
        if language == "zh":
            parts.append(
                f"{label} {processing:,}（输入 {usage['input_tokens']:,} / "
                f"缓存 {usage['cached_input_tokens']:,} / 输出 {usage['output_tokens']:,}）"
            )
        else:
            parts.append(
                f"{label} {processing:,} (in {usage['input_tokens']:,} / "
                f"cached {usage['cached_input_tokens']:,} / out {usage['output_tokens']:,})"
            )
    unavailable = unavailable_root is not None or missing_workers > 0
    if unavailable_root is not None:
        if language == "zh":
            parts.append(f"主模型 {unavailable_root} 暂不可用")
        else:
            parts.append(f"root {unavailable_root} unavailable")
    if missing_workers:
        if language == "zh":
            parts.append(f"{missing_workers} 个子智能体用量暂不可用")
        else:
            noun = "worker" if missing_workers == 1 else "workers"
            parts.append(f"usage unavailable for {missing_workers} {noun}")
    if not parts:
        return None
    duration = format_duration(started_at) if started_at is not None else "unknown"
    if language == "zh":
        total_text = (
            f"已知合计 {total:,} tokens"
            if unavailable and total
            else "总计暂不可用"
            if unavailable
            else f"总计 {total:,} tokens"
        )
        return (
            "用量：" + " | ".join(parts) + f" | {total_text} · 用时 {duration}"
        )
    total_text = (
        f"known total {total:,} tokens"
        if unavailable and total
        else "total unavailable"
        if unavailable
        else f"total {total:,} tokens"
    )
    return (
        "Usage: " + " | ".join(parts) + f" | {total_text} · wall {duration}"
    )


def current_receipt(
    session_id: str, language: str = "en", turn_id: str | None = None
) -> str | None:
    root = resolve_data_root()
    database = root / "orchestration.db"
    if not database.is_file() or not session_id:
        return None
    with connect_readonly(database) as connection:
        if turn_id:
            baseline = connection.execute(
                "SELECT * FROM task_usage_baselines WHERE session_id = ? AND turn_id = ?",
                (session_id, turn_id),
            ).fetchone()
        else:
            baseline = connection.execute(
                "SELECT * FROM task_usage_baselines WHERE session_id = ? "
                "ORDER BY started_at DESC LIMIT 1",
                (session_id,),
            ).fetchone()
        if baseline is None:
            return None
        models, missing_workers = worker_usage(
            connection,
            session_id,
            str(baseline["turn_id"]),
            str(baseline["started_at"]),
        )
        transcript = find_transcript(session_id, baseline["transcript_path"])
        current = latest_usage(str(transcript)) if transcript is not None else None
        root_available = bool(baseline["baseline_available"]) and current is not None
        if root_available and current is not None:
            add_usage(
                models,
                str(baseline["root_model"] or "unknown"),
                delta(current["input_tokens"], baseline["baseline_input_tokens"]),
                delta(
                    current["cached_input_tokens"],
                    baseline["baseline_cached_input_tokens"],
                ),
                delta(current["output_tokens"], baseline["baseline_output_tokens"]),
            )
        unavailable_root = None
        if not root_available:
            unavailable_root = model_display_label(
                str(baseline["root_model"] or "root")
            )
        return format_current(
            models,
            language,
            str(baseline["started_at"]),
            unavailable_root=unavailable_root,
            missing_workers=missing_workers,
        )


def requested_language(arguments: list[str]) -> str:
    for index, argument in enumerate(arguments):
        if argument.startswith("--language="):
            value = argument.split("=", 1)[1]
        elif argument == "--language" and index + 1 < len(arguments):
            value = arguments[index + 1]
        else:
            continue
        return "zh" if value.lower().startswith("zh") else "en"
    return "en"


def requested_turn_id(arguments: list[str]) -> str | None:
    for index, argument in enumerate(arguments):
        if argument.startswith("--turn-id="):
            value = argument.split("=", 1)[1]
        elif argument == "--turn-id" and index + 1 < len(arguments):
            value = arguments[index + 1]
        else:
            continue
        return value.strip() or None
    return None


def main() -> None:
    if "--current" in sys.argv[1:]:
        try:
            receipt = current_receipt(
                os.environ.get("CODEX_THREAD_ID", ""),
                requested_language(sys.argv[1:]),
                requested_turn_id(sys.argv[1:]),
            )
            if receipt:
                print(receipt)
        except (
            OSError,
            sqlite3.Error,
            TypeError,
            ValueError,
            KeyError,
            json.JSONDecodeError,
        ):
            pass
        return
    event = ""
    try:
        payload = json.load(sys.stdin)
        event = str(payload.get("hook_event_name") or "")
        if os.environ.get("GOLDILOCKS_WORKER") == "1":
            if event == "Stop":
                print("{}")
            return
        if event == "Stop":
            print("{}")
            return
        if event != "UserPromptSubmit":
            return
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return
        with connect(Path(configured).expanduser()) as connection:
            record_baseline(connection, payload)
    except (OSError, sqlite3.Error, TypeError, ValueError, json.JSONDecodeError):
        if event == "Stop":
            print("{}")


if __name__ == "__main__":
    main()
