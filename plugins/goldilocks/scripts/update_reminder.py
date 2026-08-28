#!/usr/bin/env python3

"""Inject a durable final-answer update reminder for every root task."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

from update_checker import enabled, installed_version, parse_version


def pending_update(root: Path) -> tuple[str, str] | None:
    """Return the installed and pending versions only when the latter is newer."""

    current = installed_version()
    if current is None:
        return None
    try:
        with sqlite3.connect(root / "orchestration.db", timeout=3) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 3000")
            state = connection.execute(
                "SELECT latest_version FROM update_state WHERE singleton = 1"
            ).fetchone()
    except (OSError, sqlite3.Error):
        return None
    latest = parse_version(state["latest_version"] if state is not None else None)
    if latest is None or latest[0] <= current[0]:
        return None
    return current[1], latest[1]


def task_language(prompt: object) -> str:
    """Localize from this Hook's own prompt, independent of sibling Hook order."""

    text = str(prompt or "")
    return "zh" if len(re.findall(r"[\u3400-\u9fff]", text)) > len(re.findall(r"[A-Za-z]", text)) / 3 else "en"


def friendly_version(version: str) -> str:
    """Turn the common prerelease form into the short label users recognize."""

    parsed = parse_version(version)
    if parsed is None:
        return version
    prerelease = parsed[0].prerelease
    if len(prerelease) == 2 and prerelease[0].lower() == "beta" and prerelease[1].isdigit():
        return f"Beta{prerelease[1]}"
    return f"v{parsed[1]}"


def reminder(current: str, latest: str, language: str) -> str:
    installed, available = friendly_version(current), friendly_version(latest)
    if language == "zh":
        return (
            f"⚠️ **Goldilocks 可更新：{installed} → {available}**\n"
            f"回复“更新”即可升级；当前任务仍使用 {installed}。"
        )
    return (
        f"⚠️ **Goldilocks update available: {installed} → {available}**\n"
        f"Reply “update” to upgrade; this task is still using {installed}."
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if (
            payload.get("hook_event_name") != "UserPromptSubmit"
            or not enabled()
            or os.environ.get("GOLDILOCKS_WORKER") == "1"
        ):
            return
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return
        root = Path(configured).expanduser()
        language = task_language(payload.get("prompt"))
        update = pending_update(root)
        if update is None:
            return
        text = reminder(*update, language)
        instruction = (
            "A pending Goldilocks update was persisted locally. For this root task, append exactly "
            "the following two lines at the very end of the final user-facing answer, after any required "
            "Goldilocks route receipt. Do not claim it was installed, add commands, or mark the update handled:\n"
            f"{text}"
        )
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": instruction,
                    }
                },
                ensure_ascii=False,
            )
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError, sqlite3.Error):
        return


if __name__ == "__main__":
    main()
