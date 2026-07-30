#!/usr/bin/env python3

"""Record Lead-verified Goldilocks worker outcomes without retaining evidence text."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


POLICY_VERSION = "0.4.5"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Close a stopped native worker route after Lead verification."
    )
    value.add_argument("--agent-id", required=True)
    value.add_argument("--result", required=True, choices=("pass", "fail"))
    value.add_argument(
        "--evidence",
        required=True,
        help="Concise acceptance command/result; only its SHA-256 hash is stored.",
    )
    value.add_argument("--data-dir", type=Path)
    return value


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
    raise ValueError(
        "Cannot identify one Goldilocks plugin data directory; pass --data-dir explicitly."
    )


def main() -> None:
    args = parser().parse_args()
    if not args.evidence.strip():
        raise ValueError("--evidence must name the fresh acceptance evidence.")
    root = resolve_data_dir(args.data_dir)
    database = root / "orchestration.db"
    if not database.is_file():
        raise ValueError(f"Goldilocks routing database not found: {database}")

    verified_at = datetime.now(timezone.utc).isoformat()
    evidence_hash = hashlib.sha256(args.evidence.encode("utf-8")).hexdigest()
    with sqlite3.connect(database, timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS verifications (
                verification_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL UNIQUE,
                decision_id TEXT NOT NULL,
                result TEXT NOT NULL CHECK(result IN ('pass', 'fail')),
                evidence_hash TEXT NOT NULL,
                verified_at TEXT NOT NULL,
                policy_version TEXT NOT NULL
            )
            """
        )
        prior = connection.execute(
            "SELECT * FROM verifications WHERE agent_id = ?", (args.agent_id,)
        ).fetchone()
        if prior is not None:
            if prior["result"] != args.result:
                raise ValueError(
                    f"Agent {args.agent_id} is already verified as {prior['result']}; "
                    "do not overwrite routing evidence."
                )
            print(
                json.dumps(
                    {
                        "agent_id": args.agent_id,
                        "result": args.result,
                        "status": "already-recorded",
                        "evidence_sha256": prior["evidence_hash"],
                    }
                )
            )
            return

        route = connection.execute(
            """
            SELECT execution.*, decision.cwd_hash, decision.task_fingerprint,
                   decision.tier, decision.policy_version AS decision_policy
            FROM executions AS execution
            JOIN decisions AS decision ON decision.decision_id = execution.decision_id
            WHERE execution.agent_id = ?
            """,
            (args.agent_id,),
        ).fetchone()
        if route is None:
            raise ValueError(f"No uniquely correlated Goldilocks route for agent {args.agent_id}.")
        if route["stopped_at"] is None:
            raise ValueError(f"Agent {args.agent_id} has not stopped; verify only completed work.")
        if route["expected_model"] != route["actual_model"]:
            raise ValueError(
                f"Agent {args.agent_id} ran {route['actual_model']}, expected "
                f"{route['expected_model']}; mismatched routes cannot become verified passes."
            )

        connection.execute(
            """
            INSERT INTO verifications (
                verification_id, agent_id, decision_id, result, evidence_hash,
                verified_at, policy_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                args.agent_id,
                route["decision_id"],
                args.result,
                evidence_hash,
                verified_at,
                POLICY_VERSION,
            ),
        )
        column = "verified_passes" if args.result == "pass" else "verified_failures"
        connection.execute(
            f"""
            INSERT INTO experiences (
                cwd_hash, task_fingerprint, tier, model, observed_completions,
                verified_passes, verified_failures, last_seen_at, policy_version
            ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)
            ON CONFLICT(cwd_hash, task_fingerprint, tier, model, policy_version)
            DO UPDATE SET {column} = {column} + 1, last_seen_at = excluded.last_seen_at
            """,
            (
                route["cwd_hash"],
                route["task_fingerprint"],
                route["tier"],
                route["actual_model"],
                int(args.result == "pass"),
                int(args.result == "fail"),
                verified_at,
                route["decision_policy"],
            ),
        )
        connection.execute(
            "UPDATE decisions SET status = ? WHERE decision_id = ?",
            (f"verified_{args.result}", route["decision_id"]),
        )

    print(
        json.dumps(
            {
                "agent_id": args.agent_id,
                "result": args.result,
                "status": "recorded",
                "evidence_sha256": evidence_hash,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error, TypeError, ValueError) as error:
        print(f"Goldilocks verification failed: {error}", file=sys.stderr)
        raise SystemExit(2)
