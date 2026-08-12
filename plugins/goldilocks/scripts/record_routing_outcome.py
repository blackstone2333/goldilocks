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


POLICY_VERSION = "0.5.1"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description="Close a stopped native worker route after Lead verification."
    )
    route = value.add_mutually_exclusive_group(required=True)
    route.add_argument("--agent-id")
    route.add_argument("--route-id", help="External codex-exec route id.")
    value.add_argument("--result", required=True, choices=("pass", "fail"))
    value.add_argument(
        "--evidence",
        required=True,
        help="Concise acceptance command/result; only its SHA-256 hash is stored.",
    )
    value.add_argument("--data-dir", type=Path)
    value.add_argument(
        "--rework-count",
        type=int,
        default=0,
        help="Number of worker correction rounds required before Lead acceptance.",
    )
    return value


def require_observed(route: sqlite3.Row, column: str, route_name: str, label: str) -> None:
    if not route[column]:
        raise ValueError(f"{route_name} lacks an observed {label}.")


def validate_external_pass(route: sqlite3.Row, route_id: str) -> None:
    route_name = f"External route {route_id}"
    if route["status"] != "succeeded" or not route["stopped_at"]:
        raise ValueError(f"{route_name} did not complete successfully.")
    require_observed(route, "actual_model", route_name, "model")
    require_observed(route, "actual_effort", route_name, "reasoning effort")
    require_observed(route, "sandbox_policy_type", route_name, "sandbox policy")
    require_observed(route, "permission_profile_type", route_name, "permission profile")
    if route["expected_model"] and route["actual_model"] != route["expected_model"]:
        raise ValueError(
            f"{route_name} observed {route['actual_model']}, expected "
            f"{route['expected_model']}."
        )
    if route["expected_effort"] and route["actual_effort"] != route["expected_effort"]:
        raise ValueError(
            f"{route_name} observed effort {route['actual_effort']}, expected "
            f"{route['expected_effort']}."
        )
    if route["requested_sandbox"] and (
        route["sandbox_policy_type"] != route["requested_sandbox"]
    ):
        raise ValueError(
            f"{route_name} observed sandbox {route['sandbox_policy_type']}, expected "
            f"{route['requested_sandbox']}."
        )


def validate_native_pass(route: sqlite3.Row, agent_id: str) -> None:
    route_name = f"Agent {agent_id}"
    require_observed(route, "actual_model", route_name, "model")
    require_observed(route, "actual_effort", route_name, "reasoning effort")
    require_observed(route, "sandbox_policy_type", route_name, "sandbox policy")
    require_observed(route, "permission_profile_type", route_name, "permission profile")
    if route["expected_model"] and route["actual_model"] != route["expected_model"]:
        raise ValueError(
            f"{route_name} ran {route['actual_model']}, expected {route['expected_model']}; "
            "mismatched routes cannot become verified passes."
        )
    if route["expected_agent_type"] and (
        route["expected_agent_type"] != route["actual_agent_type"]
    ):
        raise ValueError(
            f"{route_name} ran role {route['actual_agent_type'] or 'unknown'}, expected "
            f"{route['expected_agent_type']}."
        )
    if route["expected_effort"] and route["actual_effort"] != route["expected_effort"]:
        raise ValueError(
            f"{route_name} ran effort {route['actual_effort']}, expected "
            f"{route['expected_effort']}."
        )
    if route["expected_sandbox"] and (
        route["sandbox_policy_type"] != route["expected_sandbox"]
    ):
        raise ValueError(
            f"{route_name} ran sandbox {route['sandbox_policy_type']}, expected "
            f"{route['expected_sandbox']}."
        )


def record_external(
    connection: sqlite3.Connection,
    args: argparse.Namespace,
    evidence_hash: str,
    verified_at: str,
) -> dict[str, object]:
    route = connection.execute(
        "SELECT * FROM external_routes WHERE route_id = ?", (args.route_id,)
    ).fetchone()
    if route is None:
        raise ValueError(f"No Goldilocks external route {args.route_id}.")
    if route["lead_result"] is not None:
        if route["lead_result"] != args.result:
            raise ValueError(
                f"External route {args.route_id} is already verified as "
                f"{route['lead_result']}."
            )
        if args.result == "pass":
            validate_external_pass(route, args.route_id)
        return {
            "route_id": args.route_id,
            "result": args.result,
            "status": "already-recorded",
            "evidence_sha256": route["evidence_hash"],
            "rework_count": route["rework_count"],
        }
    if route["status"] not in {"succeeded", "failed"} or not route["stopped_at"]:
        raise ValueError(
            f"External route {args.route_id} has status {route['status']}; "
            "only completed routes can be verified."
        )
    if args.result == "pass":
        validate_external_pass(route, args.route_id)
    connection.execute(
        """
        UPDATE external_routes SET lead_result = ?, evidence_hash = ?, verified_at = ?,
            rework_count = ? WHERE route_id = ?
        """,
        (args.result, evidence_hash, verified_at, args.rework_count, args.route_id),
    )
    if route["task_fingerprint"]:
        model = str(route["actual_model"] or route["expected_model"] or "")
        if model:
            column = "verified_passes" if args.result == "pass" else "verified_failures"
            connection.execute(
                f"""
                INSERT INTO experiences (
                    cwd_hash, task_fingerprint, tier, model, observed_completions,
                    verified_passes, verified_failures, last_seen_at, policy_version
                ) VALUES (?, ?, 'fast', ?, 0, ?, ?, ?, ?)
                ON CONFLICT(cwd_hash, task_fingerprint, tier, model, policy_version)
                DO UPDATE SET {column} = {column} + 1,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    route["cwd_hash"],
                    route["task_fingerprint"],
                    model,
                    int(args.result == "pass"),
                    int(args.result == "fail"),
                    verified_at,
                    route["policy_version"],
                ),
            )
    return {
        "route_id": args.route_id,
        "result": args.result,
        "status": "recorded",
        "evidence_sha256": evidence_hash,
        "rework_count": args.rework_count,
    }


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


def ensure_experiment_columns(connection: sqlite3.Connection) -> None:
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if "decisions" in tables:
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(decisions)")
        }
        if "expected_sandbox" not in columns:
            connection.execute("ALTER TABLE decisions ADD COLUMN expected_sandbox TEXT")
    if "executions" in tables:
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(executions)")
        }
        if "expected_sandbox" not in columns:
            connection.execute("ALTER TABLE executions ADD COLUMN expected_sandbox TEXT")
    if "external_routes" in tables:
        columns = {
            str(row[1]) for row in connection.execute("PRAGMA table_info(external_routes)")
        }
        if "task_fingerprint" not in columns:
            connection.execute("ALTER TABLE external_routes ADD COLUMN task_fingerprint TEXT")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS experiences (
            cwd_hash TEXT NOT NULL,
            task_fingerprint TEXT NOT NULL,
            tier TEXT NOT NULL,
            model TEXT NOT NULL,
            observed_completions INTEGER NOT NULL DEFAULT 0,
            verified_passes INTEGER NOT NULL DEFAULT 0,
            verified_failures INTEGER NOT NULL DEFAULT 0,
            last_seen_at TEXT NOT NULL,
            policy_version TEXT NOT NULL,
            PRIMARY KEY(cwd_hash, task_fingerprint, tier, model, policy_version)
        )
        """
    )


def main() -> None:
    args = parser().parse_args()
    if not args.evidence.strip():
        raise ValueError("--evidence must name the fresh acceptance evidence.")
    if args.rework_count < 0:
        raise ValueError("--rework-count cannot be negative.")
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
        ensure_experiment_columns(connection)
        if args.route_id:
            result = record_external(connection, args, evidence_hash, verified_at)
            print(json.dumps(result))
            return
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
        if prior is not None and prior["result"] != args.result:
            raise ValueError(
                f"Agent {args.agent_id} is already verified as {prior['result']}; "
                "do not overwrite routing evidence."
            )

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
        if args.result == "pass":
            validate_native_pass(route, args.agent_id)

        if prior is not None:
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
        connection.execute(
            "UPDATE executions SET rework_count = ? WHERE agent_id = ?",
            (args.rework_count, args.agent_id),
        )

    print(
        json.dumps(
            {
                "agent_id": args.agent_id,
                "result": args.result,
                "status": "recorded",
                "evidence_sha256": evidence_hash,
                "rework_count": args.rework_count,
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error, TypeError, ValueError) as error:
        print(f"Goldilocks verification failed: {error}", file=sys.stderr)
        raise SystemExit(2)
