#!/usr/bin/env python3

"""Enforce and audit Goldilocks routing with concurrency-safe local state."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


POLICY_VERSION = "0.3.2"
SPARK_MODEL = "gpt-5.3-codex-spark"
LEAD_MODEL = "gpt-5.6-sol"
MAX_FORK_TURNS = 4
ROUTE_PREFIXES = {
    "fast__": "fast",
    "standard__": "standard",
    "lead__": "lead",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def valid_fork_turns(tier: str, raw_value: object) -> tuple[bool, str]:
    if raw_value is None or not str(raw_value).strip():
        return False, (
            "Goldilocks blocks implicit context inheritance. Set fork_turns explicitly: "
            'normally "none", one to four recent turns, or "all" only for a justified Lead handoff.'
        )

    value = str(raw_value).strip().lower()
    if value == "all":
        if tier == "lead":
            return True, ""
        return False, (
            "Goldilocks reserves full-history forks for explicit Lead handoffs because they inherit "
            "the parent model and duplicate the complete conversation. Distill a task-local contract."
        )
    if value == "none":
        return True, ""

    try:
        turns = int(value)
    except ValueError:
        return False, 'fork_turns must be "none", a positive integer no greater than four, or Lead-only "all".'
    if turns < 1 or turns > MAX_FORK_TURNS:
        return False, "Goldilocks allows one to four recent turns; use a task contract or an explicit Lead handoff."
    return True, ""


def data_dir() -> Path | None:
    raw = os.environ.get("PLUGIN_DATA")
    if not raw:
        return None
    path = Path(raw).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def connect_state() -> sqlite3.Connection | None:
    root = data_dir()
    if root is None:
        return None
    connection = sqlite3.connect(root / "orchestration.db", timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS decisions (
            decision_id TEXT PRIMARY KEY,
            session_id TEXT,
            turn_id TEXT,
            tool_use_id TEXT UNIQUE,
            cwd_hash TEXT NOT NULL,
            task_fingerprint TEXT NOT NULL,
            task_name TEXT NOT NULL,
            tier TEXT NOT NULL,
            parent_model TEXT NOT NULL,
            expected_model TEXT NOT NULL,
            fork_turns TEXT NOT NULL,
            status TEXT NOT NULL,
            prior_observations INTEGER NOT NULL DEFAULT 0,
            planned_at TEXT NOT NULL,
            started_at TEXT,
            stopped_at TEXT,
            actual_model TEXT,
            agent_id TEXT,
            correlation_confidence TEXT,
            policy_version TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS decisions_ready
            ON decisions(session_id, status, expected_model, planned_at);

        CREATE TABLE IF NOT EXISTS executions (
            agent_id TEXT PRIMARY KEY,
            session_id TEXT,
            decision_id TEXT,
            expected_model TEXT,
            actual_model TEXT NOT NULL,
            correlation_confidence TEXT NOT NULL,
            started_at TEXT NOT NULL,
            stopped_at TEXT,
            FOREIGN KEY(decision_id) REFERENCES decisions(decision_id)
        );

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
        );
        """
    )
    return connection


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def task_fingerprint(payload: dict[str, Any], tool_input: dict[str, Any]) -> tuple[str, str]:
    cwd = str(payload.get("cwd") or "")
    task_name = str(tool_input.get("task_name") or "")
    message = str(tool_input.get("message") or "")
    normalized = re.sub(r"\d+", "#", f"{task_name}\n{message}".lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return stable_hash(cwd), stable_hash(normalized)


def record_plan(
    payload: dict[str, Any],
    tool_input: dict[str, Any],
    tier: str,
    expected_model: str,
) -> None:
    connection = connect_state()
    if connection is None:
        return
    cwd_hash, fingerprint = task_fingerprint(payload, tool_input)
    prior = connection.execute(
        """
        SELECT COALESCE(SUM(observed_completions), 0)
        FROM experiences
        WHERE cwd_hash = ? AND task_fingerprint = ? AND tier = ? AND model = ?
        """,
        (cwd_hash, fingerprint, tier, expected_model),
    ).fetchone()[0]
    connection.execute(
        """
        INSERT OR REPLACE INTO decisions (
            decision_id, session_id, turn_id, tool_use_id, cwd_hash, task_fingerprint,
            task_name, tier, parent_model, expected_model, fork_turns, status,
            prior_observations, planned_at, policy_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            payload.get("session_id"),
            payload.get("turn_id"),
            payload.get("tool_use_id"),
            cwd_hash,
            fingerprint,
            str(tool_input.get("task_name") or ""),
            tier,
            str(payload.get("model") or ""),
            expected_model,
            str(tool_input.get("fork_turns") or ""),
            int(prior),
            now(),
            POLICY_VERSION,
        ),
    )
    connection.commit()
    connection.close()


def handle_pre_tool_use(payload: dict[str, Any]) -> None:
    tool_name = str(payload.get("tool_name") or "")
    normalized_tool_name = tool_name.rsplit(".", 1)[-1]
    if normalized_tool_name not in {"spawn_agent", "Agent"}:
        return

    if str(payload.get("model") or "") == SPARK_MODEL:
        deny("Goldilocks Fast workers are leaf executors and cannot spawn more subagents. Return to the owner.")
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
            "or lead__. Classify the execution contract and retry."
        )
        return

    fork_valid, fork_reason = valid_fork_turns(tier, tool_input.get("fork_turns"))
    if not fork_valid:
        deny(fork_reason)
        return

    fork_value = str(tool_input.get("fork_turns") or "").strip().lower()
    if tier == "fast":
        requested_model = str(tool_input.get("model") or "").strip()
        if not requested_model:
            deny(
                "Goldilocks requires an explicit model for native Fast subagents so they cannot "
                "silently inherit Lead. Choose a model advertised by the host; when native Spark "
                "is unavailable, use the packaged dispatch_codex_worker.py adapter."
            )
            return
        record_plan(payload, tool_input, tier, requested_model)
        return

    if tier == "lead" and fork_value == "all":
        inherited_model = str(payload.get("model") or "")
        if not inherited_model:
            deny("Goldilocks could not identify the parent Lead model for the full-history handoff.")
            return
        rewritten = dict(tool_input)
        rewritten.pop("model", None)
        rewritten.pop("reasoning_effort", None)
        rewritten.pop("service_tier", None)
        rewritten.pop("agent_type", None)
        record_plan(payload, rewritten, tier, inherited_model)
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
            "Choose a model that clears the quality gate, or keep the work with the current owner."
        )
        return

    record_plan(payload, tool_input, tier, requested_model)


def claim_plan(payload: dict[str, Any]) -> tuple[sqlite3.Row | None, str]:
    connection = connect_state()
    if connection is None:
        return None, "unavailable"
    session_id = payload.get("session_id")
    actual_model = str(payload.get("model") or "")
    agent_id = str(payload.get("agent_id") or "")
    started_at = now()
    connection.execute("BEGIN IMMEDIATE")
    candidates = connection.execute(
        """
        SELECT * FROM decisions
        WHERE session_id = ? AND status = 'planned'
        ORDER BY planned_at, rowid
        """,
        (session_id,),
    ).fetchall()
    matching = [row for row in candidates if row["expected_model"] == actual_model]

    selected: sqlite3.Row | None = None
    if len(candidates) == 1:
        selected = candidates[0]
        confidence = "single"
    elif len(matching) == 1:
        selected = matching[0]
        confidence = "model_unique"
    elif candidates:
        confidence = "ambiguous"
    else:
        confidence = "unplanned"

    decision_id = selected["decision_id"] if selected is not None else None
    connection.execute(
        """
        INSERT OR REPLACE INTO executions (
            agent_id, session_id, decision_id, expected_model, actual_model,
            correlation_confidence, started_at, stopped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            agent_id,
            session_id,
            decision_id,
            selected["expected_model"] if selected is not None else None,
            actual_model,
            confidence,
            started_at,
        ),
    )
    if selected is not None:
        connection.execute(
            """
            UPDATE decisions
            SET status = 'started', started_at = ?, actual_model = ?, agent_id = ?,
                correlation_confidence = ?
            WHERE decision_id = ? AND status = 'planned'
            """,
            (started_at, actual_model, agent_id, confidence, decision_id),
        )
    connection.commit()
    connection.close()
    return selected, confidence


def handle_subagent_start(payload: dict[str, Any]) -> None:
    decision, confidence = claim_plan(payload)
    if decision is None and confidence == "unplanned":
        actual_model = str(payload.get("model") or "")
        if actual_model == LEAD_MODEL:
            emit(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "SubagentStart",
                        "additionalContext": (
                            "You started as an unplanned Lead-model subagent. Before implementing, "
                            "check whether the task is ready for Fast/Standard. If it is, return to "
                            "the parent for explicit lower-cost dispatch. Continue only when this "
                            "subtask genuinely needs Lead judgment or owns an inseparable critical boundary."
                        ),
                    }
                }
            )
        return
    if decision is None or confidence in {"ambiguous", "unavailable"}:
        return

    expected_model = str(decision["expected_model"] or "")
    actual_model = str(payload.get("model") or "")
    if expected_model and actual_model == expected_model:
        return

    message = (
        "Goldilocks routing mismatch: "
        f"{decision['task_name']} expected {expected_model}, but Codex started {actual_model or 'an unknown model'}."
    )
    emit(
        {
            "systemMessage": message,
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": (
                    f"{message} Do not execute the delegated task. Report the mismatch immediately "
                    "so the owner can keep the work local or choose a verified route."
                ),
            },
        }
    )


def handle_subagent_stop(payload: dict[str, Any]) -> None:
    connection = connect_state()
    if connection is None:
        return
    agent_id = str(payload.get("agent_id") or "")
    stopped_at = now()
    connection.execute("BEGIN IMMEDIATE")
    execution = connection.execute(
        "SELECT * FROM executions WHERE agent_id = ?",
        (agent_id,),
    ).fetchone()
    connection.execute(
        "UPDATE executions SET stopped_at = ? WHERE agent_id = ?",
        (stopped_at, agent_id),
    )
    if execution is not None and execution["decision_id"]:
        decision = connection.execute(
            "SELECT * FROM decisions WHERE decision_id = ?",
            (execution["decision_id"],),
        ).fetchone()
        if decision is not None:
            connection.execute(
                "UPDATE decisions SET status = 'stopped', stopped_at = ? WHERE decision_id = ?",
                (stopped_at, decision["decision_id"]),
            )
        if decision is not None and decision["expected_model"] == execution["actual_model"]:
            connection.execute(
                """
                INSERT INTO experiences (
                    cwd_hash, task_fingerprint, tier, model, observed_completions,
                    verified_passes, verified_failures, last_seen_at, policy_version
                ) VALUES (?, ?, ?, ?, 1, 0, 0, ?, ?)
                ON CONFLICT(cwd_hash, task_fingerprint, tier, model, policy_version)
                DO UPDATE SET
                    observed_completions = observed_completions + 1,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    decision["cwd_hash"],
                    decision["task_fingerprint"],
                    decision["tier"],
                    execution["actual_model"],
                    stopped_at,
                    POLICY_VERSION,
                ),
            )
    connection.commit()
    connection.close()


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
    except (OSError, sqlite3.Error, TypeError, ValueError) as error:
        if "payload" in locals() and payload.get("hook_event_name") == "PreToolUse":
            deny(f"Goldilocks routing guard failed closed: {error}")


if __name__ == "__main__":
    main()
