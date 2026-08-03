#!/usr/bin/env python3

"""Store or inspect one explicit project-level Goldilocks delegation grant."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


POLICY_VERSION = "0.4.5-exp3"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    action = value.add_mutually_exclusive_group()
    action.add_argument("--grant", action="store_true")
    action.add_argument("--revoke", action="store_true")
    action.add_argument("--status", action="store_true")
    value.add_argument("--authority", choices=("explicit-user",))
    value.add_argument("--workdir", type=Path, default=Path.cwd())
    value.add_argument("--data-dir", type=Path)
    return value


def workspace_root(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    for directory in (resolved, *resolved.parents):
        if (directory / ".git").exists():
            return directory
    return resolved


def cwd_hash(path: Path) -> str:
    return hashlib.sha256(str(workspace_root(path)).encode()).hexdigest()


def resolve_data_dir(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    configured = os.environ.get("PLUGIN_DATA")
    if configured:
        return Path(configured).expanduser().resolve()
    candidates = sorted(
        path.parent
        for path in (Path.home() / ".codex" / "plugins" / "data").glob(
            "goldilocks-*/orchestration.db"
        )
    )
    if len(candidates) == 1:
        return candidates[0]
    raise ValueError("cannot identify one Goldilocks data directory; pass --data-dir")


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS project_grants (
            cwd_hash TEXT PRIMARY KEY,
            active INTEGER NOT NULL,
            granted_at TEXT NOT NULL,
            revoked_at TEXT,
            policy_version TEXT NOT NULL
        )
        """
    )


def main() -> None:
    args = parser().parse_args()
    if args.grant and args.authority != "explicit-user":
        raise ValueError("--grant requires --authority explicit-user")
    root = resolve_data_dir(args.data_dir)
    root.mkdir(parents=True, exist_ok=True)
    database = root / "orchestration.db"
    project = cwd_hash(args.workdir)
    timestamp = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(database, timeout=10) as connection:
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        ensure_schema(connection)
        if args.grant:
            connection.execute(
                """
                INSERT INTO project_grants (
                    cwd_hash, active, granted_at, revoked_at, policy_version
                ) VALUES (?, 1, ?, NULL, ?)
                ON CONFLICT(cwd_hash) DO UPDATE SET
                    active = 1, granted_at = excluded.granted_at,
                    revoked_at = NULL, policy_version = excluded.policy_version
                """,
                (project, timestamp, POLICY_VERSION),
            )
        elif args.revoke:
            connection.execute(
                """
                UPDATE project_grants SET active = 0, revoked_at = ?, policy_version = ?
                WHERE cwd_hash = ?
                """,
                (timestamp, POLICY_VERSION, project),
            )
        row = connection.execute(
            "SELECT active, granted_at, revoked_at, policy_version FROM project_grants "
            "WHERE cwd_hash = ?",
            (project,),
        ).fetchone()

    print(
        json.dumps(
            {
                "status": "active" if row and row[0] else "inactive",
                "project_hash": project,
                "granted_at": row[1] if row else None,
                "revoked_at": row[2] if row else None,
                "policy_version": row[3] if row else POLICY_VERSION,
                "scope": "bounded Fast/Standard dispatch only; no additional external authority",
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error, TypeError, ValueError) as error:
        raise SystemExit(f"Goldilocks project delegation failed: {error}")
