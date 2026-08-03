#!/usr/bin/env python3

"""Emit allowlisted routing metadata from one exact Codex child rollout."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sqlite3
from pathlib import Path


UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
PROFILES = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "goldilocks"
    / "assets"
    / "codex-route-profiles.json"
)


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
                SELECT execution.decision_id, decision.status
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
            if not execution["decision_id"]:
                raise ValueError(
                    f"child {args.thread_id} is not correlated to a routing decision"
                )
            if str(execution["status"] or "").startswith("verified_"):
                raise ValueError(
                    f"child {args.thread_id} is already {execution['status']}; "
                    "runtime evidence is immutable after Lead verification"
                )
            connection.execute(
                """
                UPDATE executions SET actual_agent_type = ?, actual_model = ?,
                    actual_effort = ?, sandbox_policy_type = ?,
                    permission_profile_type = ?, input_tokens = ?,
                    cached_input_tokens = ?, output_tokens = ? WHERE agent_id = ?
                """,
                (
                    role,
                    model,
                    effort,
                    sandbox,
                    permission,
                    usage.get("input_tokens"),
                    usage.get("cached_input_tokens"),
                    usage.get("output_tokens"),
                    args.thread_id,
                ),
            )
            if execution["decision_id"]:
                task_name = str(session.get("agent_path") or role).rsplit("/", 1)[-1]
                observed_cwd = str(result["cwd"] or "")
                connection.execute(
                    """
                    UPDATE decisions SET actual_model = ?, task_name = ?, cwd_hash = ?,
                        task_fingerprint = ? WHERE decision_id = ?
                    """,
                    (
                        model,
                        task_name,
                        hashlib.sha256(observed_cwd.encode()).hexdigest(),
                        hashlib.sha256(task_name.lower().encode()).hexdigest(),
                        execution["decision_id"],
                    ),
                )
        result["recorded"] = True
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError) as error:
        raise SystemExit(f"Goldilocks runtime inspection failed: {error}")
