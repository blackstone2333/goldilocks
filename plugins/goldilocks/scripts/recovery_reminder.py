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


POLICY_VERSION = "0.4.5"
MICRO_STYLE = (
    "Lead with the result. Omit work preambles, repeated plans, status, recaps, tangents, "
    "and oversized logs. Report only changed state; expand for safety, ambiguity, or "
    "decisive evidence."
)
ROUTING_GATE = (
    "For executable work, silently apply the Goldilocks zero-cost gate before any specialist Skill. "
    "If material uncertainty, unknown cause, multi-stage continuity, or useful decomposition exists, "
    "read and use the goldilocks:goldilocks Skill; otherwise take its Direct exit. "
    "Visible multi-unit implementation must run its make-or-delegate check before Lead edits; "
    "Direct remains valid when briefing and review cost more. "
    "Skip the gate for pure conversation."
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


def record_gate(
    payload: dict[str, object], cwd: Path, ledger: Path | None
) -> dict[str, bool]:
    """Record that the root gate was delivered without retaining prompt content."""

    prompt = str(payload.get("prompt") or "")
    repeat_signal = repeat_failure_signal(prompt)
    state = {
        "repeat_failure_signal": repeat_signal,
        "continuity_required": False,
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
                "SELECT repeat_failure_signal, continuity_required "
                "FROM gate_injections WHERE injection_id = ?",
                (injection_id,),
            ).fetchone()
            if existing is not None:
                return {
                    "repeat_failure_signal": bool(existing["repeat_failure_signal"]),
                    "continuity_required": bool(existing["continuity_required"]),
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
            connection.execute(
                """
                INSERT OR IGNORE INTO gate_injections (
                    injection_id, session_id, turn_id, cwd_hash, prompt_fingerprint,
                    ledger_present, repeat_failure_signal, continuity_required,
                    injected_at, policy_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    datetime.now(timezone.utc).isoformat(),
                    POLICY_VERSION,
                ),
            )
            return {
                "repeat_failure_signal": repeat_signal,
                "continuity_required": continuity_required,
            }
    except (OSError, sqlite3.Error, TypeError, ValueError):
        # Auditability must never block or suppress the routing instruction.
        return state


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
            if ledger is not None:
                message += (
                    f" An active Goldilocks task ledger exists at {ledger}. Interpret this prompt "
                    "against its stable Objective as ADD, REPLACE, CANCEL, or QUESTION; after "
                    "handling it, mark the steering entry applied before continuing."
                )
            elif gate_state["continuity_required"]:
                message += f" {CONTINUITY_GATE}"
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
