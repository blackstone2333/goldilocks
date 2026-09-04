#!/usr/bin/env python3

"""Emit allowlisted routing metadata from one exact Codex child rollout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_naming import model_name_suffix

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
PROFILES = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "goldilocks"
    / "assets"
    / "codex-route-profiles.json"
)
ROUTE_PREFIXES = {"fast__": "fast", "standard__": "standard", "lead__": "lead"}
SEMANTIC_NAME = re.compile(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?$")
POLICY_VERSION = "0.6.1"


def canonical_native_name(agent_path: object, profile: dict[str, object]) -> str:
    """Return a rollout's independently visible canonical native task name.

    Native ``SubagentStart`` can arrive before the host has supplied its path.
    This deliberately accepts the later rollout only when it contains the exact
    route name implied by the native profile; it never guesses a name from role.
    """
    name = str(agent_path or "").rsplit("/", 1)[-1].strip().lower()
    tier = str(profile.get("tier") or "")
    model = str(profile.get("model") or "")
    prefix = next((value for value, value_tier in ROUTE_PREFIXES.items() if value_tier == tier), "")
    suffix = model_name_suffix(model)
    ending = f"_{suffix}"
    if not name or not prefix or not suffix or not name.startswith(prefix) or not name.endswith(ending):
        raise ValueError("rollout agent_path is not a canonical native task name")
    semantic = name[len(prefix) : -len(ending)]
    if not semantic or SEMANTIC_NAME.fullmatch(semantic) is None:
        raise ValueError("rollout agent_path is not a canonical native task name")
    return name


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("thread_id")
    value.add_argument("--sessions-dir", type=Path)
    value.add_argument("--record", action="store_true", help="Update the correlated audit row.")
    value.add_argument("--data-dir", type=Path)
    return value


def sessions_root(explicit: Path | None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    configured = os.environ.get("CODEX_HOME")
    root = Path(configured).expanduser() if configured else Path.home() / ".codex"
    return root / "sessions"


def data_root(explicit: Path | None) -> Path:
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


def one(values: list[object], label: str, *, required: bool = True) -> object | None:
    normalized = {json.dumps(value, sort_keys=True) for value in values if value is not None}
    if not normalized:
        if required:
            raise ValueError(f"missing {label}")
        return None
    if len(normalized) != 1:
        raise ValueError(f"conflicting {label}")
    return json.loads(next(iter(normalized)))


def task_complete_time(records: list[dict[str, object]]) -> str | None:
    """Return the last rollout completion timestamp, if the child reached one.

    Some hosts omit ``SubagentStop`` after interrupts.  A child rollout's own
    terminal event is direct lifecycle evidence, so use it to close an already
    observed execution without inferring success or route availability.
    """
    latest: str | None = None
    for record in records:
        payload = record.get("payload")
        if record.get("type") != "event_msg" or not isinstance(payload, dict):
            continue
        if payload.get("type") != "task_complete":
            continue
        timestamp = record.get("timestamp")
        if isinstance(timestamp, str) and timestamp and (latest is None or timestamp > latest):
            latest = timestamp
    return latest


def verified_posthoc_fork_turns(role: object, profile: dict[str, object], observed: object) -> str:
    """Return a reusable native fork contract only when rollout evidence proves it.

    A posthoc native correlation has no PreToolUse decision to establish an
    explicit Lead handoff.  It therefore accepts only the fixed-role contracts
    that the rollout itself can prove, and never promotes an arbitrary non-null
    value (particularly ``all``) into reusable route evidence.
    """
    if not isinstance(observed, str):
        raise ValueError("rollout fork_turns must be an explicit string contract")
    value = observed.strip().lower()
    if not value:
        raise ValueError("rollout lacks observed fork_turns; native runtime evidence cannot synthesize a reusable routing decision")

    role_name = str(role)
    tier = str(profile.get("tier") or "")
    if role_name in {"goldilocks_spark_worker", "goldilocks_luna_economy"}:
        allowed = {"none"}
    elif role_name == "goldilocks_sol_reviewer":
        allowed = {"none"}
    elif role_name == "goldilocks_terra_engineer" and tier == "standard":
        allowed = {"none", "1", "2", "3", "4"}
    else:
        raise ValueError("child is not a recognized fixed native Goldilocks role")
    if value not in allowed:
        expected = "none" if allowed == {"none"} else "none or one to four"
        raise ValueError(
            f"rollout fork_turns={value!r} violates {role_name}'s fixed contract: {expected}. "
            "Only an explicitly planned Lead handoff may use all; posthoc runtime evidence cannot infer one."
        )
    return value


def main() -> None:
    args = parser().parse_args()
    if UUID.fullmatch(args.thread_id) is None:
        raise ValueError("thread_id must be a lowercase UUID")
    root = sessions_root(args.sessions_dir)
    if not root.is_dir():
        raise ValueError(f"sessions directory is unavailable: {root}")
    matches = list(root.rglob(f"rollout-*-{args.thread_id}.jsonl"))
    if len(matches) != 1:
        raise ValueError(f"expected one exact rollout, found {len(matches)}")

    session_meta: list[dict[str, object]] = []
    contexts: list[dict[str, object]] = []
    rollout_records: list[dict[str, object]] = []
    usage: dict[str, int] = {}
    with matches[0].open(encoding="utf-8") as handle:
        for raw in handle:
            try:
                record = json.loads(raw)
            except json.JSONDecodeError:
                continue
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            rollout_records.append(record)
            if record.get("type") == "session_meta":
                session_meta.append(payload)
            elif record.get("type") == "turn_context":
                contexts.append(payload)
            elif record.get("type") == "event_msg":
                info = payload.get("info")
                total = info.get("total_token_usage") if isinstance(info, dict) else None
                if isinstance(total, dict):
                    for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
                        if isinstance(total.get(key), int):
                            usage[key] = total[key]
    if len(session_meta) != 1 or not contexts:
        raise ValueError("rollout lacks one session_meta or any turn_context")

    session = session_meta[0]
    if session.get("id") != args.thread_id:
        raise ValueError("rollout metadata does not identify the requested thread")
    role = one([session.get("agent_role")], "agent role")
    model = one([item.get("model") for item in contexts], "model")
    effort = one([item.get("effort") for item in contexts], "reasoning effort")
    sandbox = one(
        [
            item.get("sandbox_policy", {}).get("type")
            if isinstance(item.get("sandbox_policy"), dict)
            else None
            for item in contexts
        ],
        "sandbox policy",
        required=False,
    )
    permission = one(
        [
            item.get("permission_profile", {}).get("type")
            if isinstance(item.get("permission_profile"), dict)
            else None
            for item in contexts
        ],
        "permission profile",
        required=False,
    )

    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"]
    expected = profiles.get(str(role))
    if expected is not None:
        if model != expected["model"] or effort != expected["reasoning_effort"]:
            raise ValueError(
                f"route mismatch for {role}: observed {model}/{effort}, expected "
                f"{expected['model']}/{expected['reasoning_effort']}"
            )

    result = {
        "thread_id": args.thread_id,
        "parent_thread_id": session.get("parent_thread_id"),
        "agent_role": role,
        "agent_path": session.get("agent_path"),
        "task_name": str(session.get("agent_path") or "").rsplit("/", 1)[-1] or None,
        "model_provider": session.get("model_provider"),
        "model": model,
        "effort": effort,
        "sandbox_policy_type": sandbox,
        "permission_profile_type": permission,
        "cwd": one([item.get("cwd") for item in contexts], "working directory"),
        "input_tokens": usage.get("input_tokens"),
        "cached_input_tokens": usage.get("cached_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "recorded": False,
    }
    if args.record:
        database = data_root(args.data_dir) / "orchestration.db"
        with sqlite3.connect(database, timeout=10) as connection:
            connection.row_factory = sqlite3.Row
            execution = connection.execute(
                """
                SELECT execution.*, decision.status
                FROM executions AS execution
                LEFT JOIN decisions AS decision
                    ON decision.decision_id = execution.decision_id
                WHERE execution.agent_id = ?
                """,
                (args.thread_id,),
            ).fetchone()
            if execution is None:
                raise ValueError(
                    f"no SubagentStart audit row exists for child {args.thread_id}"
                )
            if str(execution["status"] or "").startswith("verified_"):
                raise ValueError(
                    f"child {args.thread_id} is already {execution['status']}; "
                    "runtime evidence is immutable after Lead verification"
                )
            completed_at = task_complete_time(rollout_records)
            if execution["decision_id"]:
                connection.execute(
                    """
                    UPDATE executions SET actual_agent_type = ?, actual_model = ?,
                        actual_effort = ?, sandbox_policy_type = ?,
                        permission_profile_type = ?, input_tokens = ?,
                        cached_input_tokens = ?, output_tokens = ? WHERE agent_id = ?
                    """,
                    (
                        role, model, effort, sandbox, permission,
                        usage.get("input_tokens"), usage.get("cached_input_tokens"),
                        usage.get("output_tokens"), args.thread_id,
                    ),
                )
                connection.execute(
                    """
                    UPDATE decisions SET actual_model = ? WHERE decision_id = ?
                    """,
                    (
                        model,
                        execution["decision_id"],
                    ),
                )
            else:
                # A native start may be observed before Codex includes its path
                # and effort.  It is not reusable then.  A later rollout can
                # repair that one narrow state only when it independently proves
                # role, exact canonical name, parent session and native profile.
                if expected is None:
                    raise ValueError("child is not a recognized native Goldilocks role")
                task_name = canonical_native_name(session.get("agent_path"), expected)
                observed_fork = one(
                    [item.get("fork_turns") for item in contexts],
                    "fork_turns",
                    required=False,
                )
                observed_fork = verified_posthoc_fork_turns(role, expected, observed_fork)
                if execution["correlation_confidence"] not in {
                    "name_unverified", "name_mismatch"
                }:
                    raise ValueError(
                        f"child {args.thread_id} is not eligible for posthoc native correlation"
                    )
                if str(execution["session_id"] or "") != str(session.get("parent_thread_id") or ""):
                    raise ValueError("rollout parent_thread_id does not match the observed parent session")
                for field, observed in {
                    "actual_agent_type": role,
                    "actual_model": model,
                    "actual_effort": effort,
                }.items():
                    recorded = execution[field]
                    if recorded is not None and str(recorded) != str(observed):
                        raise ValueError(f"observed {field} conflicts with the original child start")
                existing = connection.execute(
                    "SELECT decision_id FROM decisions WHERE agent_id = ?", (args.thread_id,)
                ).fetchone()
                if existing is not None:
                    raise ValueError("child already has a different routing decision")

                observed_cwd = str(result["cwd"] or "")
                decision_id = f"posthoc:{args.thread_id}"
                started_at = str(execution["started_at"] or "")
                if not started_at:
                    raise ValueError("observed child has no start time for posthoc correlation")
                stopped_at = execution["stopped_at"]
                status = "stopped" if stopped_at else "started"
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    """
                    INSERT INTO decisions (
                        decision_id, session_id, turn_id, tool_use_id, cwd_hash,
                        task_fingerprint, task_name, tier, parent_model, expected_model,
                        expected_agent_type, expected_effort, expected_sandbox, billing_channel,
                        transport, fork_turns, status, prior_observations, planned_at, started_at,
                        stopped_at, actual_model, agent_id, correlation_confidence, policy_version
                    ) VALUES (?, ?, '', ?, ?, ?, ?, ?, '', ?, ?, ?, ?, NULL,
                        'native', ?, ?, 0, ?, ?, ?, ?, ?, 'posthoc_role_observed', ?)
                    """,
                    (
                        decision_id, session.get("parent_thread_id"), f"posthoc:{args.thread_id}",
                        hashlib.sha256(observed_cwd.encode()).hexdigest(),
                        hashlib.sha256(task_name.lower().encode()).hexdigest(), task_name,
                        expected["tier"], model, role, effort,
                        expected.get("sandbox"), str(observed_fork), status, started_at,
                        started_at, stopped_at, model, args.thread_id, POLICY_VERSION,
                    ),
                )
                updated = connection.execute(
                    """
                    UPDATE executions SET decision_id = ?, expected_model = ?,
                        actual_model = ?, expected_agent_type = ?, actual_agent_type = ?,
                        expected_effort = ?, actual_effort = ?, expected_sandbox = ?,
                        sandbox_policy_type = ?, permission_profile_type = ?, input_tokens = ?,
                        cached_input_tokens = ?, output_tokens = ?, correlation_confidence = ?
                    WHERE agent_id = ? AND decision_id IS NULL
                        AND correlation_confidence IN ('name_unverified', 'name_mismatch')
                    """,
                    (
                        decision_id, model, model, role, role, effort, effort,
                        expected.get("sandbox"), sandbox, permission,
                        usage.get("input_tokens"), usage.get("cached_input_tokens"),
                        usage.get("output_tokens"), "posthoc_role_observed", args.thread_id,
                    ),
                )
                if updated.rowcount != 1:
                    raise ValueError("child changed during posthoc native correlation")
            if completed_at and execution["stopped_at"] is None:
                connection.execute(
                    "UPDATE executions SET stopped_at = ? WHERE agent_id = ? AND stopped_at IS NULL",
                    (completed_at, args.thread_id),
                )
                connection.execute(
                    """
                    UPDATE decisions SET status = 'stopped', stopped_at = ?
                    WHERE agent_id = ? AND status IN ('planned', 'started')
                    """,
                    (completed_at, args.thread_id),
                )
        result["recorded"] = True
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError) as error:
        raise SystemExit(f"Goldilocks runtime inspection failed: {error}")
