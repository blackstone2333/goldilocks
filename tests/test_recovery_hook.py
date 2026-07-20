#!/usr/bin/env python3

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins" / "goldilocks" / "scripts" / "recovery_reminder.py"


def run_hook(cwd: Path, event: str) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": "test-session",
        "cwd": str(cwd),
        "hook_event_name": event,
    }
    if event == "SessionStart":
        payload["source"] = "compact"
    elif event == "PostCompact":
        payload["trigger"] = "auto"
    elif event == "UserPromptSubmit":
        payload["prompt"] = "Also document the result."
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        parent = Path(temp_dir)
        outside_ledger = parent / ".goldilocks" / "ACTIVE.md"
        outside_ledger.parent.mkdir()
        outside_ledger.write_text("# Unrelated parent task\n", encoding="utf-8")

        repo = parent / "workspace"
        (repo / ".git").mkdir(parents=True)
        nested = repo / "src" / "nested"
        nested.mkdir(parents=True)

        quiet = run_hook(nested, "SessionStart")
        assert quiet.returncode == 0, quiet.stderr
        assert quiet.stdout == "", "hook must not cross the current Git boundary"

        ledger = repo / ".goldilocks" / "ACTIVE.md"
        ledger.parent.mkdir()
        ledger.write_text("# Active task\n", encoding="utf-8")

        session = run_hook(nested, "SessionStart")
        assert session.returncode == 0, session.stderr
        session_output = json.loads(session.stdout)
        context = session_output["hookSpecificOutput"]["additionalContext"]
        assert str(ledger) in context
        assert "Exact next action" in context
        assert "Do not repeat" in context

        steer = run_hook(nested, "UserPromptSubmit")
        steer_output = json.loads(steer.stdout)
        steer_context = steer_output["hookSpecificOutput"]["additionalContext"]
        assert "ADD, REPLACE, CANCEL, or QUESTION" in steer_context
        assert "applied" in steer_context

        compact = run_hook(nested, "PostCompact")
        compact_output = json.loads(compact.stdout)
        assert "systemMessage" in compact_output
        assert str(ledger) in compact_output["systemMessage"]

    print("Goldilocks recovery hook contract passed.")


if __name__ == "__main__":
    main()
