#!/usr/bin/env python3

"""Silently compare one Goldilocks route line with existing runtime evidence."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


POLICY_VERSION = "0.5.0-alpha.1-exp3.2"
ROUTING_EXPERIMENT_ID = "routing-rationale-v3.2"
TRANSCRIPT_TAIL_BYTES = 16 * 1024 * 1024
ROUTE_LINE = re.compile(
    r"^ROUTE=(direct|fast|standard|mixed)\s*\|\s*"
    r"WRITE_READY=(\d+)\s*\|\s*READ_READY=(\d+)\s*\|\s*"
    r"EXISTING=(\d+)\s*\|\s*"
    r"(?:PLANNED_DISPATCH|NEW_DISPATCH)=(\d+)\s*\|\s*"
    r"LEAD=(.*?)\s*\|\s*REASON=([a-z_]+)\s*\|\s*DETAIL=(.+?)\s*$",
    re.MULTILINE,
)
DIRTY_TREE = re.compile(
    r"(?:脏工作树|未提交(?:改动|修改)|dirty\s+(?:worktree|tree)|uncommitted\s+changes)",
    re.IGNORECASE,
)
MODEL_NAMES = {
    "luna": "gpt-5.6-luna",
    "spark": "gpt-5.3-codex-spark",
    "codex-spark": "gpt-5.3-codex-spark",
    "terra": "gpt-5.6-terra",
    "sol": "gpt-5.6-sol",
}


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def read_tail(path: object) -> list[dict[str, Any]]:
    if not isinstance(path, str) or not path:
        return []
    transcript = Path(path).expanduser()
    if not transcript.is_file():
        return []
    records: list[dict[str, Any]] = []
    try:
        with transcript.open("rb") as handle:
            size = handle.seek(0, os.SEEK_END)
            offset = max(0, size - TRANSCRIPT_TAIL_BYTES)
            handle.seek(offset)
            data = handle.read()
        lines = data.splitlines()
        if offset and lines:
            lines = lines[1:]
        for raw in lines:
            try:
                record = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if isinstance(record, dict):
                records.append(record)
    except OSError:
        return []
    return records


def assistant_message(record: dict[str, Any]) -> tuple[str | None, str]:
    if record.get("type") != "response_item":
        return None, ""
    payload = record.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "message":
        return None, ""
    if payload.get("role") != "assistant":
        return None, ""
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    turn_id = metadata.get("turn_id") if isinstance(metadata, dict) else None
    content = payload.get("content")
    if not isinstance(content, list):
        return str(turn_id) if turn_id else None, ""
    text = "\n".join(
        str(item.get("text") or "")
        for item in content
        if isinstance(item, dict) and item.get("type") in {"output_text", "input_text"}
    )
    return str(turn_id) if turn_id else None, text


def latest_route(
    records: list[dict[str, Any]], turn_id: str
) -> tuple[str, datetime] | None:
    found: tuple[str, datetime] | None = None
    for record in records:
        record_turn, text = assistant_message(record)
        if record_turn != turn_id:
            continue
        timestamp = parse_timestamp(record.get("timestamp"))
        for match in ROUTE_LINE.finditer(text):
            found = (match.group(0), timestamp or datetime.now(timezone.utc))
    return found


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS route_audits (
            audit_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            turn_id TEXT NOT NULL,
            cwd_hash TEXT NOT NULL,
            route_fingerprint TEXT NOT NULL,
            route TEXT NOT NULL,
            write_ready INTEGER NOT NULL,
            read_ready INTEGER NOT NULL,
            claimed_existing INTEGER NOT NULL,
            planned_dispatch INTEGER NOT NULL,
            observed_active_agents INTEGER NOT NULL,
            observed_dispatch INTEGER NOT NULL,
            available_route_count INTEGER NOT NULL,
            delegation_grant_active INTEGER NOT NULL,
            reason_code TEXT NOT NULL,
            review_flags TEXT NOT NULL,
            route_at TEXT NOT NULL,
            audited_at TEXT NOT NULL,
            routing_experiment_id TEXT NOT NULL,
            policy_version TEXT NOT NULL,
            UNIQUE(session_id, turn_id)
        )
        """
    )


def tables(connection: sqlite3.Connection) -> set[str]:
    return {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }


def columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {str(row[1]) for row in connection.execute(f"PRAGMA table_info({table})")}


def candidate(
    connection: sqlite3.Connection, session_id: str, turn_id: str
) -> sqlite3.Row | None:
    if "gate_injections" not in tables(connection):
        return None
    required = {
        "session_id",
        "turn_id",
        "cwd_hash",
        "routing_rationale_candidate",
        "routing_experiment_id",
        "delegation_grant_active",
        "injected_at",
    }
    if not required.issubset(columns(connection, "gate_injections")):
        return None
    return connection.execute(
        """
        SELECT cwd_hash, delegation_grant_active, injected_at
        FROM gate_injections
        WHERE session_id = ? AND turn_id = ?
          AND routing_rationale_candidate = 1 AND routing_experiment_id = ?
        ORDER BY injected_at DESC LIMIT 1
        """,
        (session_id, turn_id, ROUTING_EXPERIMENT_ID),
    ).fetchone()


def lifecycle_minutes(model: object, tier: object = None) -> int:
    if str(tier or "") == "fast" or str(model or "") in {
        "gpt-5.6-luna",
        "gpt-5.3-codex-spark",
    }:
        return 30
    return 90


def active_agents(
    connection: sqlite3.Connection, cwd_hash: str, route_at: datetime
) -> int:
    observed: set[str] = set()
    available = tables(connection)
    if {"decisions", "executions"}.issubset(available):
        required_decision = {"decision_id", "cwd_hash", "tier", "expected_model"}
        required_execution = {"agent_id", "decision_id", "started_at", "stopped_at"}
        if required_decision.issubset(columns(connection, "decisions")) and required_execution.issubset(
            columns(connection, "executions")
        ):
            rows = connection.execute(
                """
                SELECT execution.agent_id, execution.started_at, execution.stopped_at,
                       decision.tier, decision.expected_model
                FROM executions AS execution
                JOIN decisions AS decision ON decision.decision_id = execution.decision_id
                WHERE decision.cwd_hash = ? AND execution.started_at <= ?
                  AND (execution.stopped_at IS NULL OR execution.stopped_at > ?)
                """,
                (cwd_hash, route_at.isoformat(), route_at.isoformat()),
            ).fetchall()
            for row in rows:
                started = parse_timestamp(row["started_at"])
                if started is None:
                    continue
                age = (route_at - started).total_seconds() / 60
                if age <= lifecycle_minutes(row["expected_model"], row["tier"]):
                    observed.add(f"native:{row['agent_id']}")
    if "external_routes" in available:
        required = {
            "route_id",
            "cwd_hash",
            "expected_model",
            "started_at",
            "stopped_at",
        }
        if required.issubset(columns(connection, "external_routes")):
            rows = connection.execute(
                """
                SELECT route_id, expected_model, started_at, stopped_at
                FROM external_routes
                WHERE cwd_hash = ? AND started_at <= ?
                  AND (stopped_at IS NULL OR stopped_at > ?)
                """,
                (cwd_hash, route_at.isoformat(), route_at.isoformat()),
            ).fetchall()
            for row in rows:
                started = parse_timestamp(row["started_at"])
                if started is None:
                    continue
                age = (route_at - started).total_seconds() / 60
                if age <= lifecycle_minutes(row["expected_model"]):
                    observed.add(f"external:{row['route_id']}")
    return len(observed)


def observed_dispatches(
    connection: sqlite3.Connection,
    session_id: str,
    route_at: datetime,
    audited_at: datetime,
) -> int:
    observed: set[str] = set()
    available = tables(connection)
    if {"decisions", "executions"}.issubset(available):
        required_decision = {"decision_id", "session_id"}
        required_execution = {"agent_id", "decision_id", "started_at"}
        if required_decision.issubset(columns(connection, "decisions")) and required_execution.issubset(
            columns(connection, "executions")
        ):
            rows = connection.execute(
                """
                SELECT DISTINCT execution.agent_id
                FROM executions AS execution
                JOIN decisions AS decision ON decision.decision_id = execution.decision_id
                WHERE decision.session_id = ? AND execution.started_at > ?
                  AND execution.started_at <= ?
                """,
                (session_id, route_at.isoformat(), audited_at.isoformat()),
            ).fetchall()
            observed.update(f"native:{row[0]}" for row in rows if row[0])
    if "external_routes" in available:
        required = {"route_id", "parent_session_id", "started_at"}
        if required.issubset(columns(connection, "external_routes")):
            rows = connection.execute(
                """
                SELECT DISTINCT route_id FROM external_routes
                WHERE parent_session_id = ? AND started_at > ? AND started_at <= ?
                """,
                (session_id, route_at.isoformat(), audited_at.isoformat()),
            ).fetchall()
            observed.update(f"external:{row[0]}" for row in rows if row[0])
    return len(observed)


def available_route_models(
    connection: sqlite3.Connection, cwd_hash: str, route_at: datetime
) -> set[str]:
    models: set[str] = set()
    available = tables(connection)
    if {"decisions", "executions"}.issubset(available):
        required_decision = {"decision_id", "cwd_hash", "expected_model"}
        required_execution = {
            "decision_id",
            "actual_model",
            "started_at",
            "stopped_at",
        }
        if required_decision.issubset(columns(connection, "decisions")) and required_execution.issubset(
            columns(connection, "executions")
        ):
            rows = connection.execute(
                """
                SELECT DISTINCT execution.actual_model
                FROM executions AS execution
                JOIN decisions AS decision ON decision.decision_id = execution.decision_id
                WHERE execution.started_at < ?
                  AND execution.stopped_at IS NOT NULL
                  AND execution.actual_model = decision.expected_model
                """,
                (route_at.isoformat(),),
            ).fetchall()
            models.update(str(row[0]) for row in rows if row[0])
    if "external_routes" in available:
        required = {
            "cwd_hash",
            "expected_model",
            "actual_model",
            "status",
            "started_at",
        }
        if required.issubset(columns(connection, "external_routes")):
            rows = connection.execute(
                """
                SELECT DISTINCT COALESCE(actual_model, expected_model)
                FROM external_routes
                WHERE started_at < ? AND status = 'succeeded'
                  AND COALESCE(actual_model, '') != ''
                """,
                (route_at.isoformat(),),
            ).fetchall()
            models.update(str(row[0]) for row in rows if row[0])
    return models


def named_models(detail: str) -> set[str]:
    lowered = detail.lower()
    result = {model for alias, model in MODEL_NAMES.items() if alias in lowered}
    result.update(
        model
        for model in set(MODEL_NAMES.values())
        if model.lower() in lowered
    )
    return result


def audit(payload: dict[str, Any], connection: sqlite3.Connection) -> None:
    session_id = str(payload.get("session_id") or "")
    turn_id = str(payload.get("turn_id") or "")
    if not session_id or not turn_id:
        return
    row = candidate(connection, session_id, turn_id)
    if row is None:
        return
    route_record = latest_route(read_tail(payload.get("transcript_path")), turn_id)
    if route_record is None:
        return
    line, route_at = route_record
    match = ROUTE_LINE.fullmatch(line.strip())
    if match is None:
        return
    route, write_ready, read_ready, existing, planned, _lead, reason, detail = match.groups()
    write_count = int(write_ready)
    read_count = int(read_ready)
    existing_count = int(existing)
    planned_count = int(planned)
    audited_at = datetime.now(timezone.utc)
    cwd_hash = str(row["cwd_hash"])
    active_count = active_agents(connection, cwd_hash, route_at)
    observed_count = observed_dispatches(connection, session_id, route_at, audited_at)
    route_models = available_route_models(connection, cwd_hash, route_at)
    mentioned = named_models(detail)
    history_conflict = bool(route_models & mentioned) if mentioned else bool(route_models)

    flags: list[str] = []
    if existing_count > active_count:
        flags.append("existing_above_observed_agents")
    if planned_count != observed_count:
        flags.append("planned_dispatch_mismatch")
    if reason == "route_unavailable" and history_conflict:
        flags.append("route_unavailable_conflicts_with_history")
    if route == "direct" and read_count > 0 and DIRTY_TREE.search(detail):
        flags.append("dirty_tree_rejected_read_only")
    if (
        route == "direct"
        and bool(row["delegation_grant_active"])
        and write_count + read_count > 0
        and bool(route_models)
    ):
        flags.append("authorized_ready_direct_with_available_route")

    ensure_schema(connection)
    audit_id = stable_hash(f"{session_id}\n{turn_id}")
    connection.execute(
        """
        INSERT INTO route_audits (
            audit_id, session_id, turn_id, cwd_hash, route_fingerprint, route,
            write_ready, read_ready, claimed_existing, planned_dispatch,
            observed_active_agents, observed_dispatch, available_route_count,
            delegation_grant_active, reason_code, review_flags, route_at,
            audited_at, routing_experiment_id, policy_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id, turn_id) DO UPDATE SET
            route_fingerprint = excluded.route_fingerprint,
            route = excluded.route,
            write_ready = excluded.write_ready,
            read_ready = excluded.read_ready,
            claimed_existing = excluded.claimed_existing,
            planned_dispatch = excluded.planned_dispatch,
            observed_active_agents = excluded.observed_active_agents,
            observed_dispatch = excluded.observed_dispatch,
            available_route_count = excluded.available_route_count,
            delegation_grant_active = excluded.delegation_grant_active,
            reason_code = excluded.reason_code,
            review_flags = excluded.review_flags,
            route_at = excluded.route_at,
            audited_at = excluded.audited_at,
            routing_experiment_id = excluded.routing_experiment_id,
            policy_version = excluded.policy_version
        """,
        (
            audit_id,
            session_id,
            turn_id,
            cwd_hash,
            stable_hash(line),
            route,
            write_count,
            read_count,
            existing_count,
            planned_count,
            active_count,
            observed_count,
            len(route_models),
            int(bool(row["delegation_grant_active"])),
            reason,
            json.dumps(sorted(flags), separators=(",", ":")),
            route_at.isoformat(),
            audited_at.isoformat(),
            ROUTING_EXPERIMENT_ID,
            POLICY_VERSION,
        ),
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if payload.get("hook_event_name") != "Stop":
            return
        if os.environ.get("GOLDILOCKS_WORKER") == "1":
            print("{}")
            return
        configured = os.environ.get("PLUGIN_DATA")
        if configured:
            root = Path(configured).expanduser()
            root.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(root / "orchestration.db", timeout=5) as connection:
                connection.row_factory = sqlite3.Row
                connection.execute("PRAGMA busy_timeout = 5000")
                connection.execute("PRAGMA journal_mode = WAL")
                audit(payload, connection)
        print("{}")
    except (OSError, sqlite3.Error, TypeError, ValueError, json.JSONDecodeError):
        print("{}")


if __name__ == "__main__":
    main()
