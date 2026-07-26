#!/usr/bin/env python3

"""Launch one contract-ready Goldilocks Fast task through the appropriate Codex model."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


SPARK_MODEL = "gpt-5.3-codex-spark"
LUNA_MODEL = "gpt-5.6-luna"
FAST_MODELS = {"coding": SPARK_MODEL, "general": LUNA_MODEL}
TASK_NAME_PATTERN = re.compile(r"^fast__[a-z0-9][a-z0-9_-]*$")
MACOS_APP_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
CAPABILITY_PROFILES = ("project", "minimal", "inherit")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description=(
            "Run a complete Fast execution contract with Spark for coding work or Luna for "
            "general non-coding production."
        )
    )
    value.add_argument("--workdir", required=True, type=Path, help="Assigned repository or worktree.")
    value.add_argument("--task-name", required=True, help="A fast__-prefixed routing name.")
    value.add_argument("--task-file", required=True, type=Path, help="UTF-8 execution contract.")
    value.add_argument(
        "--work-type",
        choices=tuple(FAST_MODELS),
        default="coding",
        help="coding selects gpt-5.3-codex-spark; general selects gpt-5.6-luna.",
    )
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
        "--capabilities",
        choices=CAPABILITY_PROFILES,
        default="project",
        help=(
            "project uses an isolated global context while preserving repository rules; "
            "minimal also ignores user/project execpolicy rules; inherit keeps all user "
            "plugins, Apps, MCP, Skills, and Hooks when the contract explicitly needs them."
        ),
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


def source_codex_home() -> Path:
    configured = os.environ.get("GOLDILOCKS_SOURCE_CODEX_HOME") or os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def toml_string(raw: str) -> str:
    raw = raw.strip()
    if raw.startswith('"'):
        return str(json.loads(raw))
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    return raw.split("#", 1)[0].strip()


def toml_key(value: str) -> str:
    return value if re.fullmatch(r"[A-Za-z0-9_-]+", value) else json.dumps(value)


def selected_provider(source: Path) -> tuple[str, list[str], list[str]] | None:
    config = source / "config.toml"
    if not config.is_file():
        return None
    lines = config.read_text(encoding="utf-8").splitlines()
    name = os.environ.get("GOLDILOCKS_MODEL_PROVIDER")
    top_level: list[str] = []
    for line in lines:
        if line.lstrip().startswith("["):
            break
        match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=\s*(.+?)\s*$", line)
        if not match:
            continue
        key, value = match.groups()
        if key == "model_provider" and not name:
            name = toml_string(value)
        elif key in {"disable_response_storage", "service_tier"}:
            top_level.append(line)
    if not name:
        return None

    provider_lines: list[str] = []
    inside = False
    header = re.compile(r"^\s*\[model_providers\.([^]]+)\]\s*$")
    for line in lines:
        match = header.match(line)
        if match:
            inside = toml_string(match.group(1)) == name
            continue
        if inside and line.lstrip().startswith("["):
            break
        if inside:
            provider_lines.append(line)
    if not any(line.strip() for line in provider_lines):
        return None
    return name, top_level, provider_lines


def link_or_copy(source: Path, target: Path) -> None:
    try:
        target.symlink_to(source, target_is_directory=source.is_dir())
    except OSError:
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)


def write_minimal_config(source: Path, target: Path) -> None:
    provider = selected_provider(source)
    lines: list[str] = []
    if provider is not None:
        name, top_level, provider_lines = provider
        lines = [f"model_provider = {json.dumps(name)}", *top_level]
        lines.extend(["", f"[model_providers.{toml_key(name)}]", *provider_lines])
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + ("\n" if lines else ""))


def prepare_isolated_home(root: Path, source: Path) -> Path:
    codex_home = root / ".codex"
    codex_home.mkdir(parents=True)
    for filename in ("auth.json", "auth.chatgpt.json", "models_cache.json"):
        candidate = source / filename
        if candidate.is_file():
            link_or_copy(candidate, codex_home / filename)
    write_minimal_config(source, codex_home / "config.toml")

    runtime = source.parent / ".cache" / "codex-runtimes"
    if runtime.is_dir():
        runtime_target = root / ".cache" / "codex-runtimes"
        runtime_target.parent.mkdir(parents=True)
        link_or_copy(runtime, runtime_target)
    return codex_home


@contextmanager
def worker_environment(capabilities: str) -> Iterator[dict[str, str]]:
    environment = os.environ.copy()
    environment["GOLDILOCKS_WORKER"] = "1"
    if capabilities == "inherit":
        yield environment
        return

    source = source_codex_home()
    with tempfile.TemporaryDirectory(prefix="goldilocks-worker-") as raw_home:
        home = Path(raw_home)
        codex_home = prepare_isolated_home(home, source)
        environment.update({"HOME": str(home), "CODEX_HOME": str(codex_home)})
        yield environment


def build_prompt(task_name: str, work_type: str, workdir: Path, contract: str) -> str:
    return f"""You are a Goldilocks Fast leaf. The owner fixed the material decisions.

Implement and verify only the contract below in the assigned workspace.

- Do not delegate, reroute, broaden scope, change shared interfaces, or take unapproved external/destructive actions.
- Do not rerun Goldilocks routing, continuity, update checks, or task ledgers.
- Treat listed units as one coherent batch; keep each independently checkable.
- Preserve unrelated work and repository rules. Stop rather than guess when a material decision is missing.
- At completion, report changed files, focused checks and results, then unresolved blockers or risks. No preamble or repeated recap.

Task name: {task_name}
Work type: {work_type}
Assigned workspace: {workdir}

--- execution contract ---

{contract.rstrip()}
"""


def worker_events_path(task_name: str) -> Path | None:
    raw = os.environ.get("GOLDILOCKS_WORKER_EVENTS_DIR")
    if not raw:
        return None
    root = Path(raw).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{task_name}.{os.getpid()}.events.jsonl"


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
        "--disable",
        "multi_agent",
        "-c",
        f'model_reasoning_effort="{args.reasoning_effort}"',
        "--sandbox",
        args.sandbox,
        "--color",
        "never",
        "-m",
        FAST_MODELS[args.work_type],
        "-C",
        str(workdir),
    ]
    if args.capabilities == "minimal":
        command.append("--ignore-rules")
    if args.result_file is not None:
        command.extend(["--output-last-message", str(args.result_file.expanduser().resolve())])
    events_path = worker_events_path(task_name)
    if events_path is not None:
        command.append("--json")
    command.append("-")

    prompt = build_prompt(task_name, args.work_type, workdir, contract)
    try:
        with worker_environment(args.capabilities) as environment:
            if events_path is None:
                completed = subprocess.run(
                    command,
                    input=prompt,
                    text=True,
                    cwd=workdir,
                    check=False,
                    env=environment,
                )
            else:
                with events_path.open("x", encoding="utf-8") as stream:
                    completed = subprocess.run(
                        command,
                        input=prompt,
                        text=True,
                        cwd=workdir,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                        check=False,
                        env=environment,
                    )
                print(
                    json.dumps(
                        {
                            "task_name": task_name,
                            "model": FAST_MODELS[args.work_type],
                            "returncode": completed.returncode,
                            "events": str(events_path),
                        }
                    )
                )
                if args.result_file is not None:
                    result_path = args.result_file.expanduser().resolve()
                    if result_path.is_file():
                        print(result_path.read_text(encoding="utf-8").strip())
    except KeyboardInterrupt:
        return 130
    except OSError as error:
        print(f"Goldilocks could not start the Fast worker: {error}", file=sys.stderr)
        return 127
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
