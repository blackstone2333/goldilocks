#!/usr/bin/env python3

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins" / "goldilocks" / "scripts" / "recovery_reminder.py"


def run_hook(cwd: Path, event: str, *, worker: bool = False) -> subprocess.CompletedProcess[str]:
    payload = {
        "session_id": "test-session",
        "cwd": str(cwd),
        "hook_event_name": event,
    }
    if event == "SessionStart":
        payload["source"] = "startup"
    elif event == "PostCompact":
        payload["trigger"] = "auto"
    elif event == "UserPromptSubmit":
        payload["prompt"] = "Also document the result."
    env = os.environ.copy()
    if worker:
        env["GOLDILOCKS_WORKER"] = "1"
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
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

        startup = run_hook(nested, "SessionStart")
        assert startup.returncode == 0, startup.stderr
        assert startup.stdout == "", "startup stays silent without recovery state"

        no_ledger_steer = run_hook(nested, "UserPromptSubmit")
        assert no_ledger_steer.returncode == 0, no_ledger_steer.stderr
        style_output = json.loads(no_ledger_steer.stdout)
        style_context = style_output["hookSpecificOutput"]["additionalContext"]
        assert len(style_context.split()) <= 35
        assert "Lead with the result" in style_context
        assert "Omit work preambles" in style_context
        assert "Report only changed state" in style_context
        assert "decisive evidence" in style_context

        no_ledger_compact = run_hook(nested, "PostCompact")
        assert no_ledger_compact.returncode == 0, no_ledger_compact.stderr
        assert no_ledger_compact.stdout == "", "compaction recovery remains ledger-gated"

        ledger = repo / ".goldilocks" / "ACTIVE.md"
        ledger.parent.mkdir()
        ledger.write_text("# Active task\n", encoding="utf-8")

        for event in ("SessionStart", "UserPromptSubmit", "PostCompact"):
            worker = run_hook(nested, event, worker=True)
            assert worker.returncode == 0, worker.stderr
            assert worker.stdout == "", f"Fast worker hook must stay silent for {event}"

        session = run_hook(nested, "SessionStart")
        assert session.returncode == 0, session.stderr
        session_output = json.loads(session.stdout)
        context = session_output["hookSpecificOutput"]["additionalContext"]
        assert str(ledger) in context
        assert "Exact next action" in context
        assert "Do not repeat" in context
        assert len(context.split()) <= 120

        steer = run_hook(nested, "UserPromptSubmit")
        steer_output = json.loads(steer.stdout)
        steer_context = steer_output["hookSpecificOutput"]["additionalContext"]
        assert "ADD, REPLACE, CANCEL, or QUESTION" in steer_context
        assert "applied" in steer_context
        assert "Lead with the result" in steer_context

        compact = run_hook(nested, "PostCompact")
        compact_output = json.loads(compact.stdout)
        assert "systemMessage" in compact_output
        assert str(ledger) in compact_output["systemMessage"]

    print("Goldilocks recovery hook contract passed.")


if __name__ == "__main__":
    main()
