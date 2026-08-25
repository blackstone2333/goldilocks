#!/usr/bin/env python3

"""Reserve and reconcile host-visible Sol-specialist work without creating threads.

This registry is deliberately caller-driven.  It records permission to create a
visible child and the child returned by the host, but it does not claim that a
Hook can intercept every host thread-creation route.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


POLICY_VERSION = "0.5.3-beta.6"
VISIBLE_SOL_ROLE = "visible_sol_specialist"
MODEL = "gpt-5.6-sol"
EFFORT = "high"
ACTIVE = ("reserved", "started")
TERMINAL = ("completed", "cancelled", "failed")
TASK_NAME = re.compile(r"lead__[a-z0-9](?:[a-z0-9_]*[a-z0-9])?_sol$")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--data-dir", type=Path)
    commands = value.add_subparsers(dest="command", required=True)

    reserve = commands.add_parser("reserve")
    reserve.add_argument("--origin-thread", required=True)
    reserve.add_argument("--parent-thread", required=True)
    reserve.add_argument("--request-key", required=True)
    reserve.add_argument("--task-name", required=True)
    reserve.add_argument("--kind", choices=("execution", "audit"), required=True)
    reserve.add_argument("--target-reservation")
    reserve.add_argument("--host-capability", choices=("visible-sol", "unavailable"), required=True)

    attach = commands.add_parser("attach")
    attach.add_argument("--reservation", required=True)
    attach.add_argument("--child-thread", required=True)
    attach.add_argument("--observed-parent-thread", required=True)
    attach.add_argument("--host-role", required=True)
    attach.add_argument("--model", required=True)
    attach.add_argument("--effort", required=True)

    for name in ("complete", "cancel", "fail"):
        terminal = commands.add_parser(name)
        terminal.add_argument("--reservation", required=True)
        if name == "complete":
            terminal.add_argument("--evidence", required=True)
        else:
            terminal.add_argument("--reason", required=True)
        terminal.add_argument(
            "--return-state", choices=("delivered",), required=name == "complete"
        )
        terminal.add_argument("--host-terminal", choices=("confirmed",))

    status = commands.add_parser("status")
    status.add_argument("--origin-thread", required=True)
    stored = commands.add_parser("receipt")
    stored.add_argument("--reservation", required=True)
    return value


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def data_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    configured = os.environ.get("PLUGIN_DATA")
    if configured:
        return Path(configured).expanduser().resolve()
    database_candidates = sorted(
        path.parent
        for path in (Path.home() / ".codex" / "plugins" / "data").glob(
            "goldilocks-*/orchestration.db"
        )
    )
    if len(database_candidates) == 1:
        return database_candidates[0]
    if database_candidates:
        raise ValueError("cannot identify one Goldilocks data directory; pass --data-dir")
    directory_candidates = sorted(
        path for path in (Path.home() / ".codex" / "plugins" / "data").glob("goldilocks-*") if path.is_dir()
    )
    if len(directory_candidates) == 1:
        return directory_candidates[0]
    raise ValueError("cannot identify one Goldilocks data directory; pass --data-dir")


def valid_id(value: str, label: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as error:
        raise ValueError(f"{label} must be a UUID") from error
    if str(parsed) != value or value != value.lower():
        raise ValueError(f"{label} must be a lowercase UUID")
    return value


def connect(root: Path) -> sqlite3.Connection:
    root.mkdir(parents=True, exist_ok=True)
    # First-use schema creation and WAL promotion can briefly contend between
    # independent callers.  Retry only that bounded local initialization;
    # later state transitions still use BEGIN IMMEDIATE as their authority.
    last_error: sqlite3.Error | None = None
    for attempt in range(40):
        connection = sqlite3.connect(root / "orchestration.db", timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA busy_timeout = 10000")
            connection.execute("PRAGMA journal_mode = WAL")
            ensure_schema(connection)
            return connection
        except sqlite3.OperationalError as error:
            connection.close()
            if "locked" not in str(error).lower() or attempt == 39:
                raise
            last_error = error
            time.sleep(0.025)
    raise last_error or sqlite3.OperationalError("database initialization failed")


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sol_specialist_tasks (
            reservation_id TEXT PRIMARY KEY,
            origin_thread_id TEXT NOT NULL,
            root_thread_id TEXT NOT NULL,
            parent_thread_id TEXT NOT NULL,
            child_thread_id TEXT UNIQUE,
            request_key TEXT NOT NULL,
            task_name TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('execution', 'audit')),
            target_reservation_id TEXT,
            state TEXT NOT NULL CHECK(state IN ('reserved', 'started', 'completed', 'cancelled', 'failed')),
            required_host_role TEXT NOT NULL,
            required_model TEXT NOT NULL,
            required_effort TEXT NOT NULL,
            observed_host_role TEXT,
            observed_model TEXT,
            observed_effort TEXT,
            reserved_at TEXT NOT NULL,
            started_at TEXT,
            terminal_at TEXT,
            return_state TEXT,
            terminal_detail_hash TEXT,
            receipt_json TEXT NOT NULL,
            policy_version TEXT NOT NULL,
            UNIQUE(root_thread_id, request_key),
            FOREIGN KEY(target_reservation_id) REFERENCES sol_specialist_tasks(reservation_id)
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS sol_specialist_active_by_root "
        "ON sol_specialist_tasks(root_thread_id, state, reserved_at)"
    )


def receipt(row: sqlite3.Row | dict[str, Any], *, idempotent: bool = False) -> dict[str, Any]:
    value = dict(row)
    return {
        "reservation_id": value["reservation_id"],
        "origin_thread_id": value["origin_thread_id"],
        "root_thread_id": value["root_thread_id"],
        "parent_thread_id": value["parent_thread_id"],
        "child_thread_id": value.get("child_thread_id"),
        "request_key": value["request_key"],
        "task_name": value["task_name"],
        "kind": value["kind"],
        "target_reservation_id": value.get("target_reservation_id"),
        "state": value["state"],
        "required_host_role": value["required_host_role"],
        "required_channel": VISIBLE_SOL_ROLE,
        "observed_host_role": value.get("observed_host_role"),
        "observed_model": value.get("observed_model"),
        "observed_effort": value.get("observed_effort"),
        "required_model": value["required_model"],
        "required_effort": value["required_effort"],
        "reserved_at": value["reserved_at"],
        "started_at": value.get("started_at"),
        "terminal_at": value.get("terminal_at"),
        "return_state": value.get("return_state"),
        "evidence_sha256": value.get("terminal_detail_hash"),
        "policy_version": value["policy_version"],
        "idempotent": idempotent,
    }


def persist_receipt(connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    value = receipt(row)
    connection.execute(
        "UPDATE sol_specialist_tasks SET receipt_json = ? WHERE reservation_id = ?",
        (json.dumps(value, sort_keys=True, separators=(",", ":")), row["reservation_id"]),
    )
    return value


def response(row: sqlite3.Row, *, idempotent: bool = False, slot: int | None = None) -> dict[str, Any]:
    """Return compact caller fields plus the persisted origin-return receipt."""
    saved = receipt(row, idempotent=idempotent)
    result: dict[str, Any] = {
        "reservation_id": saved["reservation_id"],
        "state": saved["state"],
        "kind": saved["kind"],
        "required_host_role": saved["required_host_role"],
        "required_model": saved["required_model"],
        "required_effort": saved["required_effort"],
        "idempotent": idempotent,
        "receipt": saved,
    }
    if slot is not None:
        result["slot"] = slot
    return result


def active_count(connection: sqlite3.Connection, root_thread: str) -> int:
    return int(connection.execute(
        "SELECT COUNT(*) FROM sol_specialist_tasks WHERE root_thread_id = ? AND state IN ('reserved', 'started')",
        (root_thread,),
    ).fetchone()[0])


def reserve(connection: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    origin = valid_id(args.origin_thread, "origin thread")
    parent = valid_id(args.parent_thread, "parent thread")
    if not args.request_key.strip():
        raise ValueError("request key cannot be empty")
    if TASK_NAME.fullmatch(args.task_name) is None:
        raise ValueError("task name must be lead__<semantic>_sol using lowercase letters, digits, and underscores")
    if args.host_capability == "unavailable":
        return {"state": "unavailable", "reservation_id": None, "origin_thread_id": origin,
                "reason": "visible Sol specialist is not available in this host"}

    connection.execute("BEGIN IMMEDIATE")
    existing = connection.execute(
        "SELECT * FROM sol_specialist_tasks WHERE root_thread_id = ? AND request_key = ?",
        (origin, args.request_key),
    ).fetchone()
    if existing is not None:
        expected = (
            parent,
            args.task_name,
            args.kind,
            args.target_reservation,
        )
        observed = (
            existing["parent_thread_id"],
            existing["task_name"],
            existing["kind"],
            existing["target_reservation_id"],
        )
        if observed != expected:
            raise ValueError("request key already belongs to a different Sol specialist contract")
        result = response(
            existing, idempotent=True,
            slot=None if existing["state"] in TERMINAL else active_count(connection, origin),
        )
        connection.commit()
        return result

    parent_is_sol = connection.execute(
        "SELECT 1 FROM sol_specialist_tasks WHERE child_thread_id = ? LIMIT 1", (parent,)
    ).fetchone()
    if parent_is_sol is not None:
        raise ValueError("a Sol specialist cannot create another Sol specialist")
    target = args.target_reservation
    if args.kind == "audit" and target:
        target_row = connection.execute(
            "SELECT * FROM sol_specialist_tasks WHERE reservation_id = ?", (target,)
        ).fetchone()
        if target_row is None or target_row["root_thread_id"] != origin:
            raise ValueError("audit target must belong to the same origin root")
    elif target:
        raise ValueError("execution cannot set --target-reservation")
    if active_count(connection, origin) >= 2:
        raise ValueError("origin root already has two active visible Sol specialists")

    row_data = {
        "reservation_id": str(uuid.uuid4()), "origin_thread_id": origin, "root_thread_id": origin,
        "parent_thread_id": parent, "child_thread_id": None, "request_key": args.request_key,
        "task_name": args.task_name, "kind": args.kind, "target_reservation_id": target,
        "state": "reserved", "required_host_role": VISIBLE_SOL_ROLE, "required_model": MODEL,
        "required_effort": EFFORT, "observed_host_role": None, "observed_model": None,
        "observed_effort": None, "reserved_at": timestamp(), "started_at": None,
        "terminal_at": None, "return_state": None, "terminal_detail_hash": None, "policy_version": POLICY_VERSION,
    }
    row_data["receipt_json"] = json.dumps(receipt(row_data), sort_keys=True, separators=(",", ":"))
    columns = ", ".join(row_data)
    placeholders = ", ".join("?" for _ in row_data)
    connection.execute(
        f"INSERT INTO sol_specialist_tasks ({columns}) VALUES ({placeholders})", tuple(row_data.values())
    )
    row = connection.execute("SELECT * FROM sol_specialist_tasks WHERE reservation_id = ?", (row_data["reservation_id"],)).fetchone()
    result = response(row, slot=active_count(connection, origin))
    connection.commit()
    return result


def attach(connection: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    child = valid_id(args.child_thread, "child thread")
    parent = valid_id(args.observed_parent_thread, "observed parent thread")
    connection.execute("BEGIN IMMEDIATE")
    row = connection.execute("SELECT * FROM sol_specialist_tasks WHERE reservation_id = ?", (args.reservation,)).fetchone()
    if row is None:
        raise ValueError("unknown Sol reservation")
    if parent != row["parent_thread_id"]:
        raise ValueError("observed parent thread does not match the reservation")
    if (args.host_role, args.model, args.effort) != (VISIBLE_SOL_ROLE, MODEL, EFFORT):
        raise ValueError("attached child is not the required visible Sol specialist identity")
    if row["state"] == "started" and row["child_thread_id"] == child:
        result = response(row, idempotent=True)
        connection.commit()
        return result
    if row["state"] != "reserved":
        raise ValueError("cannot attach a terminal Sol reservation")
    duplicate = connection.execute("SELECT reservation_id FROM sol_specialist_tasks WHERE child_thread_id = ?", (child,)).fetchone()
    if duplicate is not None:
        raise ValueError("visible child thread is already attached to another reservation")
    connection.execute(
        "UPDATE sol_specialist_tasks SET state = 'started', child_thread_id = ?, observed_host_role = ?, "
        "observed_model = ?, observed_effort = ?, started_at = ? WHERE reservation_id = ?",
        (child, args.host_role, args.model, args.effort, timestamp(), args.reservation),
    )
    row = connection.execute("SELECT * FROM sol_specialist_tasks WHERE reservation_id = ?", (args.reservation,)).fetchone()
    persist_receipt(connection, row)
    result = response(row)
    connection.commit()
    return result


def terminal(
    connection: sqlite3.Connection, args: argparse.Namespace, state: str, detail: str,
    return_state: str | None = None, host_terminal: str | None = None,
) -> dict[str, Any]:
    if not detail.strip():
        raise ValueError("terminal detail cannot be empty")
    detail_hash = hashlib.sha256(detail.encode("utf-8")).hexdigest()
    connection.execute("BEGIN IMMEDIATE")
    row = connection.execute("SELECT * FROM sol_specialist_tasks WHERE reservation_id = ?", (args.reservation,)).fetchone()
    if row is None:
        raise ValueError("unknown Sol reservation")
    if row["state"] in TERMINAL:
        if (
            row["state"] == state
            and row["terminal_detail_hash"] == detail_hash
            and row["return_state"] == return_state
        ):
            result = response(row, idempotent=True)
            connection.commit()
            return result
        raise ValueError("Sol reservation is terminal and its receipt is immutable")
    if state == "completed" and row["state"] != "started":
        raise ValueError("only an attached visible Sol specialist can complete")
    if row["state"] == "started" and host_terminal != "confirmed":
        raise ValueError("a started visible Sol specialist requires --host-terminal confirmed before terminal release")
    if row["state"] == "started" and return_state != "delivered":
        raise ValueError("a started visible Sol specialist requires --return-state delivered before terminal release")
    if row["state"] == "reserved" and return_state is not None:
        raise ValueError("an unstarted Sol reservation cannot claim an origin return")
    connection.execute(
        "UPDATE sol_specialist_tasks SET state = ?, terminal_at = ?, terminal_detail_hash = ?, return_state = ? WHERE reservation_id = ?",
        (state, timestamp(), detail_hash, return_state, args.reservation),
    )
    row = connection.execute("SELECT * FROM sol_specialist_tasks WHERE reservation_id = ?", (args.reservation,)).fetchone()
    persist_receipt(connection, row)
    result = response(row)
    connection.commit()
    return result


def status(connection: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    origin = valid_id(args.origin_thread, "origin thread")
    rows = connection.execute(
        "SELECT * FROM sol_specialist_tasks WHERE root_thread_id = ? ORDER BY reserved_at, rowid", (origin,)
    ).fetchall()
    return {"origin_thread_id": origin, "active_count": active_count(connection, origin),
            "capacity": 2, "receipts": [receipt(row) for row in rows]}


def stored_receipt(connection: sqlite3.Connection, args: argparse.Namespace) -> dict[str, Any]:
    row = connection.execute(
        "SELECT receipt_json FROM sol_specialist_tasks WHERE reservation_id = ?", (args.reservation,)
    ).fetchone()
    if row is None:
        raise ValueError("unknown Sol reservation")
    return json.loads(str(row["receipt_json"]))


def main() -> None:
    args = parser().parse_args()
    connection = connect(data_dir(args.data_dir))
    try:
        if args.command == "reserve":
            result = reserve(connection, args)
        elif args.command == "attach":
            result = attach(connection, args)
        elif args.command == "complete":
            result = terminal(connection, args, "completed", args.evidence, args.return_state, args.host_terminal)
        elif args.command == "cancel":
            result = terminal(
                connection, args, "cancelled", args.reason, args.return_state, args.host_terminal
            )
        elif args.command == "fail":
            result = terminal(
                connection, args, "failed", args.reason, args.return_state, args.host_terminal
            )
        elif args.command == "receipt":
            result = stored_receipt(connection, args)
        else:
            result = status(connection, args)
        print(json.dumps(result, sort_keys=True))
    finally:
        connection.close()


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error, TypeError, ValueError) as error:
        print(f"Goldilocks Sol registry failed: {error}", file=sys.stderr)
        raise SystemExit(2)
