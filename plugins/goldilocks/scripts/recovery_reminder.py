#!/usr/bin/env python3

"""Inject a tiny response contract and continuity guidance when needed."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path


POLICY_VERSION = "0.5.0"
ROUTING_EXPERIMENT_ID = "routing-rationale-v3.2"
GLOBAL_GRANT_KEY = "__global__"
MICRO_STYLE = (
    "Lead with the result. Omit work preambles, repeated plans/status/recaps, tangents, and "
    "long logs. Report only changed state and decisive evidence; expand for safety/ambiguity. "
    "For defect work: evidence-backed cause—or explicitly unknown—then fix and verification."
)
ROUTING_GATE = (
    "For executable work, silently apply the Goldilocks zero-cost gate before any specialist Skill. "
    "If uncertainty, unknown cause, continuity, or useful decomposition exists, "
    "read and use goldilocks:goldilocks; otherwise take its Direct exit. "
    "Visible multi-unit implementation must run its make-or-delegate check before Lead edits; "
    "Direct remains valid when briefing and review cost more. "
    "Skip for pure conversation."
)
ROUTING_RATIONALE_GATE = (
    "Likely multi-unit work detected. Read route-card.md before implementation and write its canonical ROUTE line "
    "inside an HTML comment "
    "with WRITE_READY, READ_READY, EXISTING, PLANNED_DISPATCH, LEAD, REASON, and DETAIL. EXISTING is "
    "current host-confirmed running ownership—not UI labels, idle/completed handles, artifacts, or a "
    "historical task_started; collect finals via host wait/status. PLANNED_DISPATCH is intent; Hooks "
    "count starts. After attempts, show one primary-language receipt: TEAM/CONCURRENCY use host-confirmed "
    "starts/active workers, never planned; capacity is ? when unknown. Root Direct exit stays silent. "
    "Shared writes permit reads. Direct names transfer cost. Audit is silent; create no "
    "extra proof, probe, document, test, or model call. Name every child "
    "<tier>__<semantic>_<model>, where tier is fast, standard, or lead."
)
AUTHORIZED_DISPATCH_GATE = (
    "An explicit bounded-delegation grant applies. Compare current official input/cached/output rates, "
    "time, raw tokens, acceptance, and retry; cheaper may be slightly slower. Keep billing pools "
    "separate when remaining budgets are unknown. This is not a delegation quota. Evaluate every ready "
    "unit for Fast before Standard. Luna uses dispatch_codex_worker.py when native roles omit it; missing "
    "native role alone is not route_unavailable. If all delegated units use Terra, DETAIL states why Fast "
    "is ineligible: residual judgment, tools, authority, or acceptance. New-model discovery is read-only; "
    "first use requires persistent explicit-user authorization."
)
CONTINUITY_GATE = (
    "Repeated-failure continuity boundary detected. Before another fix, read the Goldilocks "
    "continuity.md reference; create or update one .goldilocks/ACTIVE.md frontier and the "
    "project's existing debug/validation record (or docs/debug/). Preserve symptom, evidence, "
    "disproven attempts, Do not repeat, exact next test, and related commits. "
    "Keep unverified work out of CHANGELOG; after fresh verification, record only user-visible "
    "release changes."
)
NEGATED_FAILURE_PATTERNS = (
    re.compile(r"(?:不用|不要|无需|不需要)(?:再)?(?:回退|撤回)"),
    re.compile(r"(?:没|没有|未|不会)(?:再)?(?:出现)?(?:问题|错误|异常|失败)"),
)
REPEAT_FAILURE_PATTERNS = (
    re.compile(
        r"(?:依旧|仍然|还是|又|再次|反复|重复).{0,16}"
        r"(?:不行|不能|无法|失败|没解决|没有解决|未解决|没修好|错误|报错|异常|"
        r"出问题|(?<!没)(?<!没有)有问题|无效|失效|坏了|又断了|再次出现)"
    ),
    re.compile(
        r"(?:没解决|没有解决|(?<!不用)(?<!不要)(?<!无需)回退|"
        r"(?<!不用)(?<!不要)(?<!无需)撤回|同样的问题|相同问题)"
    ),
    re.compile(r"(?:问题|错误|故障).{0,8}(?:又|再次).{0,8}(?:出现|发生)"),
    re.compile(
        r"\b(?:still (?:fail(?:s|ed|ing)?|broken|wrong|not fixed|not working|cannot|can't)|"
        r"still (?:doesn't|isn't) work(?:ing)?|"
        r"failed again|same (?:bug|issue|problem)|not fixed|didn't work|doesn't work|"
        r"keeps? (?:failing|breaking)|regression|revert(?:ed)?|roll(?:ed)? back)\b",
        re.IGNORECASE,
    ),
)
NUMBERED_UNIT_PATTERN = re.compile(
    r"(?m)^\s*(?:\d{1,2}[、.)）]|[-*]\s+(?:修复|修改|实现|完成|增加|添加|测试|"
    r"发布|部署|fix|change|implement|add|test|deploy|release)\b)",
    re.IGNORECASE,
)
MULTI_UNIT_PHRASE_PATTERN = re.compile(
    r"(?:以下|这些|多个|多项|逐项|一并|全部|所有).{0,12}"
    r"(?:问题|缺陷|任务|功能|改动|修复|完成)|"
    r"\b(?:multiple|several|all|each).{0,24}(?:bugs?|issues?|tasks?|features?|changes?)\b",
    re.IGNORECASE,
)
EXECUTION_PATTERN = re.compile(
    r"(?:修复|修改|实现|开发|完成|增加|添加|测试|构建|发布|部署)|"
    r"\b(?:fix|change|implement|develop|complete|add|test|build|release|deploy)\b",
    re.IGNORECASE,
)
SINGLE_UNIT_PATTERN = re.compile(
    r"(?:单一|单个|一个).{0,16}(?:实现|开发|任务|改动|单元)|"
    r"\b(?:single|one)\s+(?:local\s+)?(?:cohesive\s+)?"
    r"(?:implementation\s+)?(?:unit|task|change)\b",
    re.IGNORECASE,
)


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def workspace_root(cwd: Path) -> Path:
    for directory in (cwd, *cwd.parents):
        if (directory / ".git").exists():
            return directory
    return cwd


def repeat_failure_signal(prompt: str) -> bool:
    candidate = prompt
    for pattern in NEGATED_FAILURE_PATTERNS:
        candidate = pattern.sub("", candidate)
    return any(pattern.search(candidate) is not None for pattern in REPEAT_FAILURE_PATTERNS)


def routing_rationale_signal(prompt: str) -> bool:
    if len(NUMBERED_UNIT_PATTERN.findall(prompt)) >= 2:
        return True
    if EXECUTION_PATTERN.search(prompt) and MULTI_UNIT_PHRASE_PATTERN.search(prompt):
        return True
    if SINGLE_UNIT_PATTERN.search(prompt):
        return False
    return False


def ensure_gate_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS gate_injections (
            injection_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            turn_id TEXT NOT NULL,
            cwd_hash TEXT NOT NULL,
            prompt_fingerprint TEXT NOT NULL,
            ledger_present INTEGER NOT NULL,
            repeat_failure_signal INTEGER NOT NULL DEFAULT 0,
            continuity_required INTEGER NOT NULL DEFAULT 0,
            routing_rationale_candidate INTEGER NOT NULL DEFAULT 0,
            routing_experiment_id TEXT,
            delegation_grant_active INTEGER NOT NULL DEFAULT 0,
            injected_at TEXT NOT NULL,
            policy_version TEXT NOT NULL
        )
        """
    )
    columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(gate_injections)")
    }
    if "repeat_failure_signal" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN "
            "repeat_failure_signal INTEGER NOT NULL DEFAULT 0"
        )
    if "continuity_required" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN "
            "continuity_required INTEGER NOT NULL DEFAULT 0"
        )
    if "routing_rationale_candidate" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN "
            "routing_rationale_candidate INTEGER NOT NULL DEFAULT 0"
        )
    if "routing_experiment_id" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN routing_experiment_id TEXT"
        )
    if "delegation_grant_active" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN "
            "delegation_grant_active INTEGER NOT NULL DEFAULT 0"
        )


def project_grant_active(connection: sqlite3.Connection, cwd_hash: str) -> bool:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'project_grants'"
    ).fetchone()
    if table is None:
        return False
    row = connection.execute(
        "SELECT active FROM project_grants WHERE cwd_hash = ?", (cwd_hash,)
    ).fetchone()
    if row is not None:
        return bool(row[0])
    row = connection.execute(
        "SELECT active FROM project_grants WHERE cwd_hash = ?", (GLOBAL_GRANT_KEY,)
    ).fetchone()
    return bool(row and row[0])


def record_gate(
    payload: dict[str, object], cwd: Path, ledger: Path | None
) -> dict[str, bool]:
    """Record that the root gate was delivered without retaining prompt content."""

    prompt = str(payload.get("prompt") or "")
    repeat_signal = repeat_failure_signal(prompt)
    rationale_candidate = routing_rationale_signal(prompt)
    state = {
        "repeat_failure_signal": repeat_signal,
        "continuity_required": False,
        "routing_rationale_candidate": rationale_candidate,
        "delegation_grant_active": False,
    }
    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return state
        root = Path(configured).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        session_id = str(payload.get("session_id") or "unknown-session")
        turn_id = str(payload.get("turn_id") or "unknown-turn")
        prompt_fingerprint = stable_hash(prompt)
        injection_id = stable_hash(f"{session_id}\n{turn_id}\n{prompt_fingerprint}")
        cwd_hash = stable_hash(str(workspace_root(cwd)))
        with sqlite3.connect(root / "orchestration.db", timeout=3) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 3000")
            connection.execute("PRAGMA journal_mode = WAL")
            ensure_gate_schema(connection)
            existing = connection.execute(
                "SELECT repeat_failure_signal, continuity_required, "
                "routing_rationale_candidate, delegation_grant_active "
                "FROM gate_injections WHERE injection_id = ?",
                (injection_id,),
            ).fetchone()
            if existing is not None:
                return {
                    "repeat_failure_signal": bool(existing["repeat_failure_signal"]),
                    "continuity_required": bool(existing["continuity_required"]),
                    "routing_rationale_candidate": bool(
                        existing["routing_rationale_candidate"]
                    ),
                    "delegation_grant_active": bool(existing["delegation_grant_active"]),
                }
            prior_prompts = int(
                connection.execute(
                    "SELECT COUNT(*) FROM gate_injections "
                    "WHERE session_id = ? AND cwd_hash = ?",
                    (session_id, cwd_hash),
                ).fetchone()[0]
            )
            continuity_required = bool(
                ledger is None and repeat_signal and prior_prompts >= 1
            )
            grant_active = project_grant_active(connection, cwd_hash)
            if grant_active and ledger is not None and EXECUTION_PATTERN.search(prompt):
                rationale_candidate = True
            connection.execute(
                """
                INSERT OR IGNORE INTO gate_injections (
                    injection_id, session_id, turn_id, cwd_hash, prompt_fingerprint,
                    ledger_present, repeat_failure_signal, continuity_required,
                    routing_rationale_candidate, routing_experiment_id,
                    delegation_grant_active, injected_at, policy_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    injection_id,
                    session_id,
                    turn_id,
                    cwd_hash,
                    prompt_fingerprint,
                    int(ledger is not None),
                    int(repeat_signal),
                    int(continuity_required),
                    int(rationale_candidate),
                    ROUTING_EXPERIMENT_ID if rationale_candidate else None,
                    int(grant_active),
                    datetime.now(timezone.utc).isoformat(),
                    POLICY_VERSION,
                ),
            )
            return {
                "repeat_failure_signal": repeat_signal,
                "continuity_required": continuity_required,
                "routing_rationale_candidate": rationale_candidate,
                "delegation_grant_active": grant_active,
            }
    except (OSError, sqlite3.Error, TypeError, ValueError):
        # Auditability must never block or suppress the routing instruction.
        return state


def routing_debt_context(payload: dict[str, object]) -> str:
    """Return one compact close-or-renew reminder without retaining task content."""

    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return ""
        database = Path(configured).expanduser() / "orchestration.db"
        if not database.is_file():
            return ""
        session_id = str(payload.get("session_id") or "unknown-session")
        with sqlite3.connect(database, timeout=3) as connection:
            connection.row_factory = sqlite3.Row
            reconcile_native_completions(connection, session_id)
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            native_debt = 0
            external_debt = 0
            stale = 0
            if "decisions" in tables:
                native_debt = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM decisions WHERE session_id = ? "
                        "AND status = 'stopped'",
                        (session_id,),
                    ).fetchone()[0]
                )
            if "external_routes" in tables:
                external_debt = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM external_routes WHERE parent_session_id = ? "
                        "AND status IN ('succeeded', 'failed') AND lead_result IS NULL",
                        (session_id,),
                    ).fetchone()[0]
                )
            if "executions" in tables:
                stale = int(
                    connection.execute(
                        """
                        SELECT COUNT(*) FROM executions AS execution
                        LEFT JOIN decisions AS decision
                            ON decision.decision_id = execution.decision_id
                        WHERE execution.session_id = ? AND execution.stopped_at IS NULL
                          AND (julianday('now') - julianday(execution.started_at)) * 1440
                              > CASE WHEN decision.tier = 'fast' THEN 30 ELSE 90 END
                        """,
                        (session_id,),
                    ).fetchone()[0]
                )
        parts: list[str] = []
        unverified = native_debt + external_debt
        if unverified:
            parts.append(f"{unverified} completed worker outcome(s) remain unverified")
        if stale:
            parts.append(f"{stale} worker(s) exceed the lifecycle warning")
        if not parts:
            return ""
        return (
            "Goldilocks routing debt: "
            + "; ".join(parts)
            + ". Stale records do not count as EXISTING unless current host status confirms they are "
            "running; close outcomes and stop or explicitly renew them before reuse."
        )
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return ""


def session_roots() -> list[Path]:
    configured = os.environ.get("GOLDILOCKS_SESSION_ROOTS")
    if configured:
        return [
            Path(value).expanduser()
            for value in configured.split(os.pathsep)
            if value.strip()
        ]
    codex_home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")
    return [codex_home / "sessions", codex_home / "archived_sessions"]


def rollout_terminal_time(agent_id: str) -> str | None:
    latest: tuple[str, str] | None = None
    for root in session_roots():
        if not root.is_dir():
            continue
        try:
            paths = root.rglob(f"rollout-*-{agent_id}.jsonl")
            for path in paths:
                with path.open("rb") as handle:
                    size = handle.seek(0, os.SEEK_END)
                    offset = max(0, size - 512 * 1024)
                    handle.seek(offset)
                    lines = handle.read().splitlines()
                if offset and lines:
                    lines = lines[1:]
                for raw in lines:
                    try:
                        record = json.loads(raw)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    payload = record.get("payload")
                    if record.get("type") != "event_msg" or not isinstance(payload, dict):
                        continue
                    event = str(payload.get("type") or "")
                    timestamp = str(record.get("timestamp") or "")
                    if event in {"task_started", "task_complete"} and timestamp:
                        if latest is None or timestamp > latest[1]:
                            latest = (event, timestamp)
        except OSError:
            continue
    return latest[1] if latest and latest[0] == "task_complete" else None


def reconcile_native_completions(
    connection: sqlite3.Connection, session_id: str
) -> int:
    available = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if not {"decisions", "executions"}.issubset(available):
        return 0
    decision_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(decisions)")
    }
    execution_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(executions)")
    }
    if not {"decision_id", "status"}.issubset(decision_columns) or not {
        "agent_id",
        "session_id",
        "decision_id",
        "started_at",
        "stopped_at",
    }.issubset(execution_columns):
        return 0
    rows = connection.execute(
        "SELECT agent_id, decision_id, started_at FROM executions "
        "WHERE session_id = ? AND stopped_at IS NULL",
        (session_id,),
    ).fetchall()
    reconciled = 0
    for row in rows:
        completed_at = rollout_terminal_time(str(row["agent_id"] or ""))
        if completed_at is None:
            continue
        elapsed_ms: int | None = None
        try:
            started = datetime.fromisoformat(str(row["started_at"]).replace("Z", "+00:00"))
            stopped = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            elapsed_ms = max(0, int((stopped - started).total_seconds() * 1000))
        except (TypeError, ValueError):
            pass
        if "elapsed_ms" in execution_columns:
            connection.execute(
                "UPDATE executions SET stopped_at = ?, elapsed_ms = ? WHERE agent_id = ?",
                (completed_at, elapsed_ms, row["agent_id"]),
            )
        else:
            connection.execute(
                "UPDATE executions SET stopped_at = ? WHERE agent_id = ?",
                (completed_at, row["agent_id"]),
            )
        if row["decision_id"]:
            connection.execute(
                "UPDATE decisions SET status = 'stopped' WHERE decision_id = ? "
                "AND status IN ('planned', 'started')",
                (row["decision_id"],),
            )
        reconciled += 1
    return reconciled


def has_continuity_debt(payload: dict[str, object], cwd: Path) -> bool:
    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return False
        database = Path(configured).expanduser() / "orchestration.db"
        if not database.is_file():
            return False
        session_id = str(payload.get("session_id") or "unknown-session")
        with sqlite3.connect(database, timeout=3) as connection:
            connection.row_factory = sqlite3.Row
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(gate_injections)")
            }
            if "continuity_required" not in columns:
                return False
            row = connection.execute(
                "SELECT 1 FROM gate_injections WHERE session_id = ? AND cwd_hash = ? "
                "AND continuity_required = 1 LIMIT 1",
                (session_id, stable_hash(str(workspace_root(cwd)))),
            ).fetchone()
            return row is not None
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return False


def find_ledger(cwd: Path) -> Path | None:
    for directory in (cwd, *cwd.parents):
        candidate = directory / ".goldilocks" / "ACTIVE.md"
        if candidate.is_file():
            return candidate
        if (directory / ".git").exists():
            break
    return None


def main() -> None:
    try:
        if os.environ.get("GOLDILOCKS_WORKER") == "1":
            return
        payload = json.load(sys.stdin)
        cwd = Path(payload.get("cwd") or os.getcwd()).expanduser().resolve()
        ledger = find_ledger(cwd)
        event = payload.get("hook_event_name")
        if event == "SessionStart":
            if ledger is None:
                if not has_continuity_debt(payload, cwd):
                    return
                routing = (
                    "Goldilocks continuity debt exists for this session and workspace. Before "
                    "continuing, read continuity.md, reconcile repository evidence, create or "
                    "update .goldilocks/ACTIVE.md and the existing debug/validation record, then "
                    "resume from the exact next test."
                )
            else:
                routing = (
                    f"Recovery state exists at {ledger}; read it, reconcile repository evidence, "
                    "honor applied steering and Do not repeat, then continue from Exact next action."
                )
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": routing,
                }
            }
        elif event == "UserPromptSubmit":
            gate_state = record_gate(payload, cwd, ledger)
            message = f"{MICRO_STYLE} {ROUTING_GATE}"
            if gate_state["routing_rationale_candidate"]:
                message += f" {ROUTING_RATIONALE_GATE}"
                if gate_state["delegation_grant_active"]:
                    message += f" {AUTHORIZED_DISPATCH_GATE}"
            if ledger is not None:
                message += (
                    f" An active Goldilocks task ledger exists at {ledger}. Interpret this prompt "
                    "against its stable Objective as ADD, REPLACE, CANCEL, or QUESTION; after "
                    "handling it, mark the steering entry applied before continuing."
                )
            elif gate_state["continuity_required"]:
                message += f" {CONTINUITY_GATE}"
            debt = routing_debt_context(payload)
            if debt:
                message += f" {debt}"
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": message,
                }
            }
        elif event == "PostCompact":
            if ledger is None:
                if not has_continuity_debt(payload, cwd):
                    return
                else:
                    system_message = (
                        "Goldilocks continuity debt survived compaction without a task frontier. Read "
                        "continuity.md, reconcile repository evidence, create or update "
                        ".goldilocks/ACTIVE.md and the existing debug/validation record, then resume "
                        "from the exact next test."
                    )
            else:
                system_message = (
                    f"Goldilocks recovery required: read {ledger}, reconcile repository state, "
                    "and resume from Exact next action."
                )
            output = {
                "continue": True,
                "systemMessage": system_message,
            }
        else:
            return

        print(json.dumps(output, ensure_ascii=False))
    except (OSError, ValueError, TypeError):
        # Continuity reminders are a guardrail; a broken hook must not block work.
        return


if __name__ == "__main__":
    main()
