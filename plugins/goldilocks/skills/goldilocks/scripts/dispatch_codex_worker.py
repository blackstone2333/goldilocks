#!/usr/bin/env python3

"""Launch one contract-ready Goldilocks Fast task through Codex Spark."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


SPARK_MODEL = "gpt-5.3-codex-spark"
TASK_NAME_PATTERN = re.compile(r"^fast__[a-z0-9][a-z0-9_-]*$")
MACOS_APP_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description=(
            "Run a complete Fast execution contract with gpt-5.3-codex-spark. "
            "This is the fallback when the native subagent host does not advertise Spark."
        )
    )
    value.add_argument("--workdir", required=True, type=Path, help="Assigned repository or worktree.")
    value.add_argument("--task-name", required=True, help="A fast__-prefixed routing name.")
    value.add_argument("--task-file", required=True, type=Path, help="UTF-8 execution contract.")
    value.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high", "xhigh"),
        default="medium",
        help="Use low for mechanical work; raise only when the contract needs it.",
    )
    value.add_argument(
        "--sandbox",
        choices=("read-only", "workspace-write"),
        default="workspace-write",
        help="Fast never receives danger-full-access through this adapter.",
    )
    value.add_argument(
        "--result-file",
        type=Path,
        help="Optional path for Codex's last response, useful for parallel result collection.",
    )
    return value


def fail(arguments: argparse.ArgumentParser, message: str) -> None:
    arguments.error(message)


def find_codex(arguments: argparse.ArgumentParser) -> str:
    configured = os.environ.get("GOLDILOCKS_CODEX_BIN")
    candidates = [configured, shutil.which("codex"), str(MACOS_APP_CODEX)]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    fail(
        arguments,
        "Codex CLI not found. Set GOLDILOCKS_CODEX_BIN or install the Codex CLI/desktop app.",
    )
    raise AssertionError("argparse.error always exits")


def build_prompt(task_name: str, workdir: Path, contract: str) -> str:
    return f"""You are a Goldilocks Fast worker in a company-style agent hierarchy.

Your owner has already made the material product and architecture decisions. You are a leaf executor: implement and verify only the bounded contract below inside the assigned workspace.

- Do not delegate or create subagents.
- Do not broaden scope, revise product intent, change shared interfaces, or perform external/destructive actions unless the contract explicitly authorizes them.
- If a missing decision affects intent, architecture, authority, or a shared boundary, stop and report the blocker instead of guessing.
- Preserve unrelated user work. Follow repository instructions and established patterns.
- At completion, report changed files, focused checks and their results, and unresolved risks or blockers.

Task name: {task_name}
Assigned workspace: {workdir}

--- execution contract ---

{contract.rstrip()}
"""


def main() -> int:
    arguments = parser()
    args = arguments.parse_args()

    task_name = args.task_name.strip().lower()
    if not TASK_NAME_PATTERN.fullmatch(task_name):
        fail(arguments, "task-name must start with fast__ and contain only letters, digits, _ or -")

    workdir = args.workdir.expanduser().resolve()
    if not workdir.is_dir():
        fail(arguments, f"workdir is not a directory: {workdir}")

    task_file = args.task_file.expanduser().resolve()
    if not task_file.is_file():
        fail(arguments, f"task-file does not exist: {task_file}")
    try:
        contract = task_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        fail(arguments, f"could not read task-file as UTF-8: {error}")
    if not contract.strip():
        fail(arguments, "task-file is empty")

    command = [
        find_codex(arguments),
        "exec",
        "-c",
        "agents.enabled=false",
        "-c",
        f'model_reasoning_effort="{args.reasoning_effort}"',
        "--sandbox",
        args.sandbox,
        "--color",
        "never",
        "-m",
        SPARK_MODEL,
        "-C",
        str(workdir),
    ]
    if args.result_file is not None:
        command.extend(["--output-last-message", str(args.result_file.expanduser().resolve())])
    command.append("-")

    prompt = build_prompt(task_name, workdir, contract)
    try:
        completed = subprocess.run(command, input=prompt, text=True, cwd=workdir, check=False)
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        print(f"Goldilocks could not start the Spark worker: {error}", file=sys.stderr)
        return 127
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
