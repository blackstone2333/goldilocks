#!/usr/bin/env python3

"""Enforce and audit Goldilocks routing with concurrency-safe local state."""

from __future__ import annotations

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

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model_naming import model_name_suffix, visible_task_name
from native_terminal import TerminalState, read_terminal_state


POLICY_VERSION = "0.5.3-beta.9"
SPARK_MODEL = "gpt-5.3-codex-spark"
LUNA_MODEL = "gpt-5.6-luna"
TERRA_MODEL = "gpt-5.6-terra"
LEAD_MODEL = "gpt-5.6-sol"
FAST_LEAF_MODELS = {SPARK_MODEL, LUNA_MODEL}
MAX_FORK_TURNS = 4
ROUTE_PREFIXES = {
    "fast__": "fast",
    "standard__": "standard",
    "lead__": "lead",
}
SEMANTIC_NAME_PATTERN = re.compile(r"[a-z0-9](?:[a-z0-9_-]*[a-z0-9])?")
ROUTE_PROFILES_FILE = (
    Path(__file__).resolve().parent.parent
    / "skills"
    / "goldilocks"
    / "assets"
    / "codex-route-profiles.json"
)


def load_native_profiles() -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(ROUTE_PROFILES_FILE.read_text(encoding="utf-8"))
        return {
            name: profile
            for name, profile in payload["profiles"].items()
            if profile.get("transport") == "native"
        }
    except (OSError, KeyError, TypeError, ValueError):
        return {}


NATIVE_PROFILES = load_native_profiles()
FIXED_NATIVE_ROLE_BY_MODEL = {
    str(profile["model"]): name for name, profile in NATIVE_PROFILES.items()
}
FIXED_NATIVE_ROLE_BY_SUFFIX = {
    model_name_suffix(model): role for model, role in FIXED_NATIVE_ROLE_BY_MODEL.items()
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


def rewrite_visible_task_name(tool_input: dict[str, Any], model: str) -> dict[str, Any]:
    rewritten = dict(tool_input)
    rewritten["task_name"] = visible_task_name(
        str(tool_input.get("task_name") or ""), model
    )
    return rewritten


def has_strict_visible_task_name(task_name: str, model: str) -> bool:
    """Require `<tier>__<semantic>_<actual-model-suffix>` after normalization."""
    normalized = task_name.strip().lower()
    tier = classify(normalized)
    if tier is None:
        return False
    prefix = next(prefix for prefix, value in ROUTE_PREFIXES.items() if value == tier)
    suffix = model_name_suffix(model)
    ending = f"_{suffix}"
    if not suffix or not normalized.endswith(ending):
        return False
    semantic = normalized[len(prefix) : -len(ending)]
    return bool(semantic and SEMANTIC_NAME_PATTERN.fullmatch(semantic))


def canonical_visible_task_name(
    tool_input: dict[str, Any], model: str
) -> dict[str, Any] | None:
    rewritten = rewrite_visible_task_name(tool_input, model)
    if not has_strict_visible_task_name(str(rewritten.get("task_name") or ""), model):
        return None
    return rewritten


def native_observed_name_confidence(
    payload: dict[str, Any], profile: dict[str, Any]
) -> tuple[str, str]:
    """Classify an unplanned native start without inventing a trusted route.

    ``SubagentStart`` is observational: a host can expose the native role and
    model while omitting the user-visible task name.  That is useful identity
    evidence, but it is not enough to turn the run into a reusable
    ``role_observed`` route.  Only a visible name that independently agrees
    with the role's tier and model suffix earns that confidence.
    """
    expected_tier = str(profile.get("tier") or "")
    expected_model = str(profile.get("model") or "")
    actual_model = str(payload.get("model") or "")
    if actual_model != expected_model:
        return "", "fixed_identity_mismatch"

    observed_name = str(payload.get("agent_path") or "").rsplit("/", 1)[-1]
    if not observed_name:
        return "", "name_unverified"
    if (
        classify(observed_name) != expected_tier
        or not has_strict_visible_task_name(observed_name, expected_model)
    ):
        return observed_name, "name_mismatch"
    return observed_name, "role_observed"


def deny_invalid_visible_name() -> None:
    deny(
        "Goldilocks requires every visible child name to be exactly "
        "<tier>__<semantic>_<model>. Use a nonempty lowercase semantic name; "
        "the Hook derives the actual model suffix."
    )


def fixed_role_requested_by(task_name: str, model: str) -> str | None:
    """Identify a fixed native role from an explicit model or visible suffix."""
    if model in FIXED_NATIVE_ROLE_BY_MODEL:
        return FIXED_NATIVE_ROLE_BY_MODEL[model]
    normalized = task_name.strip().lower()
    for suffix, role in FIXED_NATIVE_ROLE_BY_SUFFIX.items():
        if suffix and normalized.endswith(f"_{suffix}"):
            return role
    return None


def require_fixed_native_role(task_name: str, model: str, agent_type: str) -> str | None:
    role = fixed_role_requested_by(task_name, model)
    if role is None or agent_type == role:
        return None
    return (
        f"Goldilocks fixed native routing requires agent_type={role}. "
        "A task_name suffix never selects a model or role; retry with that explicit agent_type, "
        "or use the packaged adapter/keep the work local when the native role is unavailable."
    )


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
            expected_agent_type TEXT,
            expected_effort TEXT,
            expected_sandbox TEXT,
            billing_channel TEXT,
            transport TEXT NOT NULL DEFAULT 'native',
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
            expected_agent_type TEXT,
            actual_agent_type TEXT,
            expected_effort TEXT,
            actual_effort TEXT,
            expected_sandbox TEXT,
            sandbox_policy_type TEXT,
            permission_profile_type TEXT,
            correlation_confidence TEXT NOT NULL,
            started_at TEXT NOT NULL,
            stopped_at TEXT,
            elapsed_ms INTEGER,
            input_tokens INTEGER,
            cached_input_tokens INTEGER,
            output_tokens INTEGER,
            rework_count INTEGER NOT NULL DEFAULT 0,
            terminal_outcome TEXT NOT NULL DEFAULT 'unknown',
            quota_reset_at INTEGER,
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
    decision_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(decisions)")
    }
    execution_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(executions)")
    }
    for name, definition in {
        "expected_agent_type": "TEXT",
        "expected_effort": "TEXT",
        "expected_sandbox": "TEXT",
        "billing_channel": "TEXT",
        "transport": "TEXT NOT NULL DEFAULT 'native'",
    }.items():
        if name not in decision_columns:
            connection.execute(f"ALTER TABLE decisions ADD COLUMN {name} {definition}")
    for name, definition in {
        "expected_agent_type": "TEXT",
        "actual_agent_type": "TEXT",
        "expected_effort": "TEXT",
        "actual_effort": "TEXT",
        "expected_sandbox": "TEXT",
        "sandbox_policy_type": "TEXT",
        "permission_profile_type": "TEXT",
        "elapsed_ms": "INTEGER",
        "input_tokens": "INTEGER",
        "cached_input_tokens": "INTEGER",
        "output_tokens": "INTEGER",
        "rework_count": "INTEGER NOT NULL DEFAULT 0",
        "terminal_outcome": "TEXT NOT NULL DEFAULT 'unknown'",
        "quota_reset_at": "INTEGER",
    }.items():
        if name not in execution_columns:
            connection.execute(f"ALTER TABLE executions ADD COLUMN {name} {definition}")
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
    *,
    expected_agent_type: str | None = None,
    expected_effort: str | None = None,
    expected_sandbox: str | None = None,
    transport: str = "native",
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
            task_name, tier, parent_model, expected_model, expected_agent_type,
            expected_effort, expected_sandbox, billing_channel, transport, fork_turns, status,
            prior_observations, planned_at, policy_version
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'planned', ?, ?, ?)
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
            expected_agent_type,
            expected_effort,
            expected_sandbox,
            os.environ.get("GOLDILOCKS_BILLING_CHANNEL"),
            transport,
            str(tool_input.get("fork_turns") or ""),
            int(prior),
            now(),
            POLICY_VERSION,
        ),
    )
    connection.commit()
    connection.close()


def is_recorded_fast_agent(payload: dict[str, Any]) -> bool:
    agent_id = str(payload.get("agent_id") or "")
    if not agent_id:
        return False
    connection = connect_state()
    if connection is None:
        return False
    row = connection.execute(
        """
        SELECT 1
        FROM executions AS execution
        JOIN decisions AS decision ON decision.decision_id = execution.decision_id
        WHERE execution.agent_id = ? AND decision.tier = 'fast'
        LIMIT 1
        """,
        (agent_id,),
    ).fetchone()
    connection.close()
    return row is not None


def terminal_elapsed_ms(started_at: object, stopped_at: str) -> int | None:
    try:
        started = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        stopped = datetime.fromisoformat(stopped_at.replace("Z", "+00:00"))
        return max(0, int((stopped - started).total_seconds() * 1000))
    except (TypeError, ValueError):
        return None


def persist_terminal_state(
    connection: sqlite3.Connection,
    execution: sqlite3.Row,
    state: TerminalState,
) -> None:
    elapsed_ms = terminal_elapsed_ms(execution["started_at"], state.completed_at)
    connection.execute(
        "UPDATE executions SET stopped_at = ?, elapsed_ms = ?, terminal_outcome = ?, "
        "quota_reset_at = ? WHERE agent_id = ?",
        (
            state.completed_at,
            elapsed_ms,
            state.outcome,
            state.quota_reset_at,
            execution["agent_id"],
        ),
    )
    if execution["decision_id"]:
        connection.execute(
            "UPDATE decisions SET status = 'stopped', stopped_at = ? "
            "WHERE decision_id = ? AND status IN ('planned', 'started')",
            (state.completed_at, execution["decision_id"]),
        )


def reconcile_native_terminals(
    connection: sqlite3.Connection, session_id: str
) -> None:
    executions = connection.execute(
        "SELECT * FROM executions WHERE session_id = ? "
        "AND actual_model = ? AND terminal_outcome = 'unknown'",
        (session_id, SPARK_MODEL),
    ).fetchall()
    for execution in executions:
        state = read_terminal_state(str(execution["agent_id"] or ""))
        if state is not None:
            persist_terminal_state(connection, execution, state)


def active_spark_quota_latch(session_id: object) -> int | None:
    if not session_id:
        return None
    connection = connect_state()
    if connection is None:
        return None
    try:
        connection.execute("BEGIN IMMEDIATE")
        reconcile_native_terminals(connection, str(session_id))
        rows = connection.execute(
            "SELECT stopped_at, quota_reset_at FROM executions "
            "WHERE session_id = ? AND actual_model = ? "
            "AND terminal_outcome = 'usage_limit' ORDER BY stopped_at DESC",
            (str(session_id), SPARK_MODEL),
        ).fetchall()
        current = int(time.time())
        for row in rows:
            reset_at = row["quota_reset_at"]
            if isinstance(reset_at, int):
                if reset_at > current:
                    connection.commit()
                    return reset_at
                continue
            try:
                stopped = datetime.fromisoformat(
                    str(row["stopped_at"]).replace("Z", "+00:00")
                )
                conservative_reset = int(stopped.timestamp()) + 5 * 60 * 60
            except (TypeError, ValueError):
                continue
            if conservative_reset > current:
                connection.commit()
                return conservative_reset
        connection.commit()
        return None
    finally:
        connection.close()


def deny_active_spark_quota(reset_at: int) -> None:
    reset = datetime.fromtimestamp(reset_at, timezone.utc).isoformat()
    deny(
        "Goldilocks confirmed a Spark usage limit for this parent session until "
        f"{reset}. Do not retry Spark before that reset. Re-evaluate the unfinished "
        "contract now: prefer Terra for transferable coding with residual judgment, "
        "Luna for eligible economy/document work, or Direct only when takeover is "
        "cheaper or the remainder is no longer transferable; surface the chosen fallback reason."
    )


def handle_pre_tool_use(payload: dict[str, Any]) -> None:
    tool_name = str(payload.get("tool_name") or "")
    normalized_tool_name = tool_name.rsplit(".", 1)[-1]
    if normalized_tool_name not in {"spawn_agent", "Agent"}:
        return

    if (
        str(payload.get("model") or "") in FAST_LEAF_MODELS
        or is_recorded_fast_agent(payload)
    ):
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
    requested_agent_type = str(tool_input.get("agent_type") or "").strip()
    profile = NATIVE_PROFILES.get(requested_agent_type)
    if profile is not None and not (tier == "lead" and fork_value == "all"):
        expected_tier = str(profile["tier"])
        expected_model = str(profile["model"])
        expected_effort = str(profile["reasoning_effort"])
        if tier != expected_tier:
            deny(
                f"Goldilocks role {requested_agent_type} is {expected_tier}, but task_name "
                f"declares {tier}. Use the matching routing prefix."
            )
            return
        if expected_model == SPARK_MODEL:
            reset_at = active_spark_quota_latch(payload.get("session_id"))
            if reset_at is not None:
                deny_active_spark_quota(reset_at)
                return
        if requested_agent_type == "goldilocks_sol_reviewer" and fork_value != "none":
            deny("Goldilocks fresh Sol review requires fork_turns=none.")
            return
        requested_model = str(tool_input.get("model") or "").strip()
        requested_effort = str(tool_input.get("reasoning_effort") or "").strip()
        if requested_model and requested_model != expected_model:
            deny(
                f"Goldilocks role {requested_agent_type} pins {expected_model}; "
                f"remove the conflicting {requested_model} override."
            )
            return
        if requested_effort and requested_effort != expected_effort:
            deny(
                f"Goldilocks role {requested_agent_type} pins {expected_effort} reasoning; "
                f"remove the conflicting {requested_effort} override."
            )
            return
        rewritten = canonical_visible_task_name(tool_input, expected_model)
        if rewritten is None:
            deny_invalid_visible_name()
            return
        rewritten.pop("model", None)
        rewritten.pop("reasoning_effort", None)
        rewritten.pop("service_tier", None)
        record_plan(
            payload,
            rewritten,
            tier,
            expected_model,
            expected_agent_type=requested_agent_type,
            expected_effort=expected_effort,
            expected_sandbox=(
                str(profile.get("sandbox")) if profile.get("sandbox") else None
            ),
        )
        if rewritten != tool_input:
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

    if tier == "lead" and fork_value == "all":
        inherited_model = str(payload.get("model") or "")
        if not inherited_model:
            deny("Goldilocks could not identify the parent Lead model for the full-history handoff.")
            return
        rewritten = canonical_visible_task_name(tool_input, inherited_model)
        if rewritten is None:
            deny_invalid_visible_name()
            return
        rewritten.pop("model", None)
        rewritten.pop("reasoning_effort", None)
        rewritten.pop("service_tier", None)
        rewritten.pop("agent_type", None)
        record_plan(payload, rewritten, tier, inherited_model)
        emit({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "allow", "updatedInput": rewritten}})
        return

    requested_model = str(tool_input.get("model") or "").strip()
    if requested_model == SPARK_MODEL:
        reset_at = active_spark_quota_latch(payload.get("session_id"))
        if reset_at is not None:
            deny_active_spark_quota(reset_at)
            return
    fixed_role_error = require_fixed_native_role(task_name, requested_model, requested_agent_type)
    if fixed_role_error:
        deny(fixed_role_error)
        return

    if tier == "fast":
        if not requested_model:
            deny(
                "Goldilocks requires an explicit model for native Fast subagents so they cannot "
                "silently inherit Lead. Choose a model advertised by the host; when native Luna "
                "or Spark is unavailable, use the packaged dispatch_codex_worker.py adapter."
            )
            return
        rewritten = canonical_visible_task_name(tool_input, requested_model)
        if rewritten is None:
            deny_invalid_visible_name()
            return
        record_plan(
            payload,
            rewritten,
            tier,
            requested_model,
            expected_effort=str(tool_input.get("reasoning_effort") or "") or None,
        )
        if rewritten != tool_input:
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

    if not requested_model:
        deny(
            f"Goldilocks requires an explicit model for {tier.title()} subagents. "
            "Choose a model that clears the quality gate, or keep the work with the current owner."
        )
        return

    rewritten = canonical_visible_task_name(tool_input, requested_model)
    if rewritten is None:
        deny_invalid_visible_name()
        return
    record_plan(
        payload,
        rewritten,
        tier,
        requested_model,
        expected_effort=str(tool_input.get("reasoning_effort") or "") or None,
    )
    if rewritten != tool_input:
        emit(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                    "updatedInput": rewritten,
                }
            }
        )


def claim_plan(payload: dict[str, Any]) -> tuple[sqlite3.Row | None, str]:
    connection = connect_state()
    if connection is None:
        return None, "unavailable"
    session_id = payload.get("session_id")
    actual_model = str(payload.get("model") or "")
    actual_agent_type = str(payload.get("agent_type") or "") or None
    actual_effort = str(payload.get("reasoning_effort") or payload.get("effort") or "") or None
    sandbox = payload.get("sandbox_policy")
    permission = payload.get("permission_profile")
    sandbox_type = (
        str(sandbox.get("type") or "") or None if isinstance(sandbox, dict) else None
    )
    permission_type = (
        str(permission.get("type") or "") or None
        if isinstance(permission, dict)
        else None
    )
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
    matching = [
        row
        for row in candidates
        if row["expected_model"] == actual_model
        and (
            not row["expected_agent_type"]
            or not actual_agent_type
            or row["expected_agent_type"] == actual_agent_type
        )
    ]

    selected: sqlite3.Row | None = None
    if len(candidates) == 1:
        selected = candidates[0]
        confidence = "single"
    elif len(matching) == 1:
        selected = matching[0]
        confidence = "route_unique"
    elif candidates:
        confidence = "ambiguous"
    elif actual_agent_type in NATIVE_PROFILES:
        profile = NATIVE_PROFILES[actual_agent_type]
        task_name, native_confidence = native_observed_name_confidence(payload, profile)
        if native_confidence != "role_observed":
            # Keep actual role/model/effort facts in ``executions`` below, but
            # do not synthesize a decision that later verification could reuse
            # as a successful native route.
            confidence = native_confidence
        else:
            cwd_hash = stable_hash(str(payload.get("cwd") or ""))
            fingerprint = stable_hash(re.sub(r"\s+", " ", task_name.lower()).strip())
            decision_id = str(uuid.uuid4())
            connection.execute(
                """
                INSERT INTO decisions (
                    decision_id, session_id, turn_id, tool_use_id, cwd_hash,
                    task_fingerprint, task_name, tier, parent_model, expected_model,
                    expected_agent_type, expected_effort, expected_sandbox, transport,
                    billing_channel, fork_turns, status, prior_observations, planned_at, started_at,
                    actual_model, agent_id, correlation_confidence, policy_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, '', ?, ?, ?, ?, 'native', ?, 'none',
                    'started', 0, ?, ?, ?, ?, 'role_observed', ?)
                """,
                (
                    decision_id,
                    session_id,
                    payload.get("turn_id"),
                    f"observed:{agent_id}",
                    cwd_hash,
                    fingerprint,
                    task_name,
                    str(profile["tier"]),
                    str(profile["model"]),
                    actual_agent_type,
                    str(profile["reasoning_effort"]),
                    str(profile.get("sandbox")) if profile.get("sandbox") else None,
                    os.environ.get("GOLDILOCKS_BILLING_CHANNEL"),
                    started_at,
                    started_at,
                    actual_model,
                    agent_id,
                    POLICY_VERSION,
                ),
            )
            selected = connection.execute(
                "SELECT * FROM decisions WHERE decision_id = ?", (decision_id,)
            ).fetchone()
            confidence = "role_observed"
    else:
        confidence = "unplanned"

    decision_id = selected["decision_id"] if selected is not None else None
    connection.execute(
        """
        INSERT OR REPLACE INTO executions (
            agent_id, session_id, decision_id, expected_model, actual_model,
            expected_agent_type, actual_agent_type, expected_effort, actual_effort,
            expected_sandbox, sandbox_policy_type, permission_profile_type,
            correlation_confidence, started_at, stopped_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
        """,
        (
            agent_id,
            session_id,
            decision_id,
            selected["expected_model"] if selected is not None else None,
            actual_model,
            selected["expected_agent_type"] if selected is not None else None,
            actual_agent_type,
            selected["expected_effort"] if selected is not None else None,
            actual_effort,
            selected["expected_sandbox"] if selected is not None else None,
            sandbox_type,
            permission_type,
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
    if decision is None and confidence == "fixed_identity_mismatch":
        actual_agent_type = str(payload.get("agent_type") or "")
        actual_model = str(payload.get("model") or "")
        expected_model = str(
            NATIVE_PROFILES.get(actual_agent_type, {}).get("model") or ""
        )
        warning = (
            "Goldilocks identity violation: an unplanned fixed native role started "
            f"agent_type={actual_agent_type or 'unknown'} on {actual_model or 'an unknown model'} "
            f"instead of {expected_model or 'its fixed model'}. SubagentStart cannot cancel a "
            "child after launch, so return immediately without reading files, calling tools, or "
            "implementing. This result cannot be used. Ask the parent to retry with the exact "
            "role/model pair, use the packaged adapter, or keep the work local."
        )
        emit(
            {
                "systemMessage": warning,
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": warning,
                },
            }
        )
        return
    if decision is None and confidence in {"name_unverified", "name_mismatch"}:
        actual_agent_type = str(payload.get("agent_type") or "")
        observed_name = str(payload.get("agent_path") or "").rsplit("/", 1)[-1]
        detail = (
            "the host did not expose a visible child name"
            if confidence == "name_unverified"
            else f"visible name {observed_name or 'unknown'} does not match this role"
        )
        warning = (
            "Goldilocks native-route audit: "
            f"{detail}. This already-started {actual_agent_type or 'native'} child remains "
            "observable, but will not be recorded as a reusable role_observed route. "
            "Report the actual role/model/effort; use <tier>__<semantic>_<model> on the next spawn."
        )
        emit(
            {
                "systemMessage": warning,
                "hookSpecificOutput": {
                    "hookEventName": "SubagentStart",
                    "additionalContext": warning,
                },
            }
        )
        return
    if decision is None and confidence == "unplanned":
        actual_model = str(payload.get("model") or "")
        if actual_model == LEAD_MODEL:
            observed_name = str(payload.get("agent_path") or "").rsplit("/", 1)[-1]
            explicit_lead = has_strict_visible_task_name(observed_name, LEAD_MODEL)
            if explicit_lead:
                return
            spoofed_role = fixed_role_requested_by(observed_name, "")
            spoofed_tier = classify(observed_name)
            retry = (
                f" Retry with agent_type={spoofed_role}."
                if spoofed_tier in {"fast", "standard"} and spoofed_role
                else ""
            )
            warning = (
                "Goldilocks quota violation: an unplanned Lead-model subagent inherited Sol. "
                "SubagentStart cannot cancel a child after launch, so return immediately without "
                "reading files, calling tools, or implementing. Ask the parent to retry with a "
                "fixed Fast/Standard employee or an explicit lead__ contract."
                + (
                    " This Fast/Standard-looking result cannot be used." + retry
                    if spoofed_tier in {"fast", "standard"}
                    else ""
                )
            )
            emit(
                {
                    "systemMessage": warning,
                    "hookSpecificOutput": {
                        "hookEventName": "SubagentStart",
                        "additionalContext": warning,
                    }
                }
            )
            return

        fixed_role = FIXED_NATIVE_ROLE_BY_MODEL.get(actual_model)
        actual_agent_type = str(payload.get("agent_type") or "")
        if fixed_role and actual_agent_type != fixed_role:
            warning = (
                "Goldilocks identity violation: an unplanned fixed-model subagent started "
                f"{actual_model} as {actual_agent_type or 'a generic agent'} instead of "
                f"agent_type={fixed_role}. SubagentStart cannot cancel a child after launch, "
                "so return immediately without reading files, calling tools, or implementing. "
                "This result cannot be used. Ask the parent to retry with the exact agent_type, "
                "use the packaged adapter, or keep the work local."
            )
            emit(
                {
                    "systemMessage": warning,
                    "hookSpecificOutput": {
                        "hookEventName": "SubagentStart",
                        "additionalContext": warning,
                    },
                }
            )
        return
    if decision is None and confidence == "ambiguous":
        actual_model = str(payload.get("model") or "")
        fixed_role = FIXED_NATIVE_ROLE_BY_MODEL.get(actual_model)
        actual_agent_type = str(payload.get("agent_type") or "")
        if fixed_role and actual_agent_type != fixed_role:
            warning = (
                "Goldilocks identity/correlation violation: this fixed-model subagent could not "
                "be matched to one explicit routing contract. SubagentStart cannot cancel a child "
                "after launch, so return immediately without reading files, calling tools, or "
                "implementing. This result cannot be used. Ask the parent to retry serially or "
                f"with an unambiguous agent_type={fixed_role} contract."
            )
            emit(
                {
                    "systemMessage": warning,
                    "hookSpecificOutput": {
                        "hookEventName": "SubagentStart",
                        "additionalContext": warning,
                    },
                }
            )
        return
    if decision is None or confidence in {"ambiguous", "unavailable"}:
        return

    expected_model = str(decision["expected_model"] or "")
    actual_model = str(payload.get("model") or "")
    expected_agent_type = str(decision["expected_agent_type"] or "")
    actual_agent_type = str(payload.get("agent_type") or "")
    expected_effort = str(decision["expected_effort"] or "")
    actual_effort = str(payload.get("reasoning_effort") or payload.get("effort") or "")
    mismatches: list[str] = []
    if expected_model and actual_model != expected_model:
        mismatches.append(f"model expected {expected_model}, observed {actual_model or 'unknown'}")
    if expected_agent_type and actual_agent_type != expected_agent_type:
        mismatches.append(
            f"agent type expected {expected_agent_type}, observed {actual_agent_type or 'unknown'}"
        )
    if expected_effort and actual_effort and actual_effort != expected_effort:
        mismatches.append(
            f"reasoning expected {expected_effort}, observed {actual_effort}"
        )
    if not mismatches:
        return

    message = (
        "Goldilocks routing mismatch: "
        f"{decision['task_name']} " + "; ".join(mismatches) + "."
    )
    emit(
        {
            "systemMessage": message,
            "hookSpecificOutput": {
                "hookEventName": "SubagentStart",
                "additionalContext": (
                    f"{message} Do not execute the delegated task. Return immediately without "
                    "reading files, calling tools, or implementing. This result cannot be used. "
                    "Report the mismatch so the owner can keep the work local or choose a verified route."
                ),
            },
        }
    )


def usage_values(payload: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    usage = payload.get("usage") or payload.get("token_usage")
    if not isinstance(usage, dict):
        return None, None, None

    def value(*keys: str) -> int | None:
        for key in keys:
            raw = usage.get(key)
            if isinstance(raw, int) and raw >= 0:
                return raw
        return None

    return (
        value("input_tokens", "input"),
        value("cached_input_tokens", "cached_input"),
        value("output_tokens", "output"),
    )


def handle_subagent_stop(payload: dict[str, Any]) -> None:
    connection = connect_state()
    if connection is None:
        return
    agent_id = str(payload.get("agent_id") or "")
    connection.execute("BEGIN IMMEDIATE")
    execution = connection.execute(
        "SELECT * FROM executions WHERE agent_id = ?",
        (agent_id,),
    ).fetchone()
    terminal = read_terminal_state(agent_id, payload.get("agent_transcript_path"))
    stopped_at = terminal.completed_at if terminal is not None else now()
    input_tokens, cached_input_tokens, output_tokens = usage_values(payload)
    elapsed_ms = (
        terminal_elapsed_ms(execution["started_at"], stopped_at)
        if execution is not None
        else None
    )
    connection.execute(
        """
        UPDATE executions SET stopped_at = ?, elapsed_ms = ?, input_tokens = ?,
            cached_input_tokens = ?, output_tokens = ?, terminal_outcome = ?,
            quota_reset_at = ? WHERE agent_id = ?
        """,
        (
            stopped_at,
            elapsed_ms,
            input_tokens,
            cached_input_tokens,
            output_tokens,
            terminal.outcome if terminal is not None else "unknown",
            terminal.quota_reset_at if terminal is not None else None,
            agent_id,
        ),
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
