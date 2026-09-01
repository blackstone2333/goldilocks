#!/usr/bin/env python3

"""Store or inspect an explicit Goldilocks delegation grant."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


POLICY_VERSION = "0.5.3-beta.8"
GLOBAL_GRANT_KEY = "__global__"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    action = value.add_mutually_exclusive_group()
    action.add_argument("--grant", action="store_true")
    action.add_argument("--revoke", action="store_true")
    action.add_argument("--status", action="store_true")
    value.add_argument("--authority", choices=("explicit-user",))
    value.add_argument(
        "--global",
        dest="global_scope",
        action="store_true",
        help="Apply the bounded delegation preference to future projects until revoked.",
    )
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
    grant_key = GLOBAL_GRANT_KEY if args.global_scope else project
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
                (grant_key, timestamp, POLICY_VERSION),
            )
        elif args.revoke:
            connection.execute(
                """
                INSERT INTO project_grants (
                    cwd_hash, active, granted_at, revoked_at, policy_version
                ) VALUES (?, 0, ?, ?, ?)
                ON CONFLICT(cwd_hash) DO UPDATE SET
                    active = 0, revoked_at = excluded.revoked_at,
                    policy_version = excluded.policy_version
                """,
                (grant_key, timestamp, timestamp, POLICY_VERSION),
            )
        row = connection.execute(
            "SELECT active, granted_at, revoked_at, policy_version FROM project_grants "
            "WHERE cwd_hash = ?",
            (grant_key,),
        ).fetchone()
        effective_source = "global" if args.global_scope else "project"
        if not args.global_scope and row is None:
            row = connection.execute(
                "SELECT active, granted_at, revoked_at, policy_version FROM project_grants "
                "WHERE cwd_hash = ?",
                (GLOBAL_GRANT_KEY,),
            ).fetchone()
            if row is not None:
                effective_source = "global"

    print(
        json.dumps(
            {
                "status": "active" if row and row[0] else "inactive",
                "project_hash": None if args.global_scope else project,
                "requested_scope": "global" if args.global_scope else "project",
                "effective_source": effective_source if row is not None else None,
                "granted_at": row[1] if row else None,
                "revoked_at": row[2] if row else None,
                "policy_version": row[3] if row else POLICY_VERSION,
                "scope": (
                    "global bounded Fast/Standard dispatch preference; per-project opt-out; "
                    "no additional external authority"
                    if args.global_scope
                    else "bounded Fast/Standard dispatch only; no additional external authority"
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error, TypeError, ValueError) as error:
        raise SystemExit(f"Goldilocks project delegation failed: {error}")
