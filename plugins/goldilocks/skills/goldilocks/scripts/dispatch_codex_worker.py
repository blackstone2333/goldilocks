#!/usr/bin/env python3

"""Launch one contract-ready Goldilocks Fast task through the appropriate Codex model."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


SPARK_MODEL = "gpt-5.3-codex-spark"
LUNA_MODEL = "gpt-5.6-luna"
FAST_MODELS = {
    "luna": LUNA_MODEL,
    "spark-coding": SPARK_MODEL,
    # Backward-compatible aliases from Goldilocks <= 0.4.4.
    "general": LUNA_MODEL,
    "coding": SPARK_MODEL,
}
TASK_NAME_PATTERN = re.compile(r"^fast__[a-z0-9][a-z0-9_-]*$")
MACOS_APP_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
CAPABILITY_PROFILES = ("project", "minimal", "inherit")
POLICY_VERSION = "0.4.5-exp3"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description=(
            "Run a complete Fast execution contract with Luna by default, or use Spark's "
            "separate coding route for deterministic code batches."
        )
    )
    value.add_argument("--workdir", required=True, type=Path, help="Assigned repository or worktree.")
    value.add_argument("--task-name", required=True, help="A fast__-prefixed routing name.")
    value.add_argument("--task-file", required=True, type=Path, help="UTF-8 execution contract.")
    value.add_argument(
        "--work-type",
        choices=tuple(FAST_MODELS),
        default="luna",
        help=(
            "luna selects the universal Fast default; spark-coding selects the separately "
            "metered code specialist. general and coding remain compatibility aliases."
        ),
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
    value.add_argument(
        "--data-dir",
        type=Path,
        help="Optional Goldilocks audit directory; auto-detected when exactly one is installed.",
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


def resolve_audit_dir(explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit.expanduser().resolve()
    configured = os.environ.get("GOLDILOCKS_ROUTING_DATA_DIR") or os.environ.get("PLUGIN_DATA")
    if configured:
        return Path(configured).expanduser().resolve()
    candidates = sorted(
        path.parent
        for path in (Path.home() / ".codex" / "plugins" / "data").glob(
            "goldilocks-*/orchestration.db"
        )
    )
    return candidates[0] if len(candidates) == 1 else None


def route_role(work_type: str) -> str:
    return (
        "goldilocks_spark_coder"
        if work_type in {"spark-coding", "coding"}
        else "goldilocks_luna_worker"
    )


def start_external_audit(
    root: Path | None,
    *,
    task_name: str,
    workdir: Path,
    work_type: str,
    model: str,
    effort: str,
    sandbox: str,
    parent_session_id: str | None,
) -> str | None:
    if root is None:
        return None
    root.mkdir(parents=True, exist_ok=True)
    route_id = str(uuid.uuid4())
    with sqlite3.connect(root / "orchestration.db", timeout=10) as connection:
        connection.execute("PRAGMA busy_timeout = 10000")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS external_routes (
                route_id TEXT PRIMARY KEY,
                task_name TEXT NOT NULL,
                cwd_hash TEXT NOT NULL,
                expected_agent_type TEXT NOT NULL,
                expected_model TEXT NOT NULL,
                expected_effort TEXT NOT NULL,
                transport TEXT NOT NULL,
                requested_sandbox TEXT NOT NULL,
                status TEXT NOT NULL,
                actual_model TEXT,
                actual_effort TEXT,
                sandbox_policy_type TEXT,
                permission_profile_type TEXT,
                parent_session_id TEXT,
                started_at TEXT NOT NULL,
                stopped_at TEXT,
                elapsed_ms INTEGER,
                input_tokens INTEGER,
                cached_input_tokens INTEGER,
                output_tokens INTEGER,
                child_thread_id TEXT,
                rework_count INTEGER NOT NULL DEFAULT 0,
                lead_result TEXT,
                evidence_hash TEXT,
                verified_at TEXT,
                policy_version TEXT NOT NULL
            )
            """
        )
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(external_routes)")
        }
        if "parent_session_id" not in columns:
            connection.execute(
                "ALTER TABLE external_routes ADD COLUMN parent_session_id TEXT"
            )
        if "child_thread_id" not in columns:
            connection.execute(
                "ALTER TABLE external_routes ADD COLUMN child_thread_id TEXT"
            )
        connection.execute(
            """
            INSERT INTO external_routes (
                route_id, task_name, cwd_hash, expected_agent_type, expected_model,
                expected_effort, transport, requested_sandbox, status, started_at,
                parent_session_id, policy_version
            ) VALUES (?, ?, ?, ?, ?, ?, 'codex-exec', ?, 'started', ?, ?, ?)
            """,
            (
                route_id,
                task_name,
                hashlib.sha256(str(workdir).encode()).hexdigest(),
                route_role(work_type),
                model,
                effort,
                sandbox,
                datetime.now(timezone.utc).isoformat(),
                parent_session_id,
                POLICY_VERSION,
            ),
        )
    return route_id


def event_result(events_path: Path | None) -> tuple[str | None, str | None]:
    if events_path is None or not events_path.is_file():
        return None, None
    thread_id: str | None = None
    final_message: str | None = None
    try:
        with events_path.open(encoding="utf-8") as handle:
            for raw in handle:
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if record.get("type") == "thread.started":
                    value = record.get("thread_id")
                    if isinstance(value, str):
                        thread_id = value
                item = record.get("item")
                if (
                    record.get("type") == "item.completed"
                    and isinstance(item, dict)
                    and item.get("type") == "agent_message"
                    and isinstance(item.get("text"), str)
                ):
                    final_message = item["text"]
    except OSError:
        return None, None
    return thread_id, final_message


def inspect_worker_rollout(
    environment: dict[str, str], thread_id: str | None
) -> dict[str, object]:
    if thread_id is None:
        return {}
    codex_home = Path(environment.get("CODEX_HOME") or "")
    sessions = codex_home / "sessions"
    if not sessions.is_dir():
        return {}
    paths = list(sessions.rglob(f"rollout-*-{thread_id}.jsonl"))
    if len(paths) != 1:
        return {}
    contexts: list[dict[str, object]] = []
    usage: dict[str, int] = {}
    try:
        with paths[0].open(encoding="utf-8") as handle:
            for raw in handle:
                try:
                    record = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                payload = record.get("payload")
                if record.get("type") == "turn_context" and isinstance(payload, dict):
                    contexts.append(payload)
                if record.get("type") == "event_msg" and isinstance(payload, dict):
                    info = payload.get("info")
                    total = info.get("total_token_usage") if isinstance(info, dict) else None
                    if isinstance(total, dict):
                        for key in ("input_tokens", "cached_input_tokens", "output_tokens"):
                            if isinstance(total.get(key), int):
                                usage[key] = total[key]
    except OSError:
        return {}
    if not contexts:
        return usage
    latest = contexts[-1]
    sandbox = latest.get("sandbox_policy")
    permission = latest.get("permission_profile")
    return {
        **usage,
        "actual_model": latest.get("model"),
        "actual_effort": latest.get("effort"),
        "sandbox_policy_type": sandbox.get("type") if isinstance(sandbox, dict) else None,
        "permission_profile_type": (
            permission.get("type") if isinstance(permission, dict) else None
        ),
    }


def finish_external_audit(
    root: Path | None,
    route_id: str | None,
    returncode: int,
    observed: dict[str, object],
    thread_id: str | None = None,
) -> None:
    if root is None or route_id is None:
        return
    stopped = datetime.now(timezone.utc)
    with sqlite3.connect(root / "orchestration.db", timeout=10) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            "SELECT started_at FROM external_routes WHERE route_id = ?", (route_id,)
        ).fetchone()
        elapsed_ms = None
        if row is not None:
            try:
                started = datetime.fromisoformat(str(row["started_at"]))
                elapsed_ms = max(0, int((stopped - started).total_seconds() * 1000))
            except ValueError:
                pass
        connection.execute(
            """
            UPDATE external_routes SET status = ?, actual_model = ?, actual_effort = ?,
                sandbox_policy_type = ?, permission_profile_type = ?, stopped_at = ?,
                elapsed_ms = ?, input_tokens = ?, cached_input_tokens = ?, output_tokens = ?,
                child_thread_id = ?
            WHERE route_id = ?
            """,
            (
                "succeeded" if returncode == 0 else "failed",
                observed.get("actual_model"),
                observed.get("actual_effort"),
                observed.get("sandbox_policy_type"),
                observed.get("permission_profile_type"),
                stopped.isoformat(),
                elapsed_ms,
                observed.get("input_tokens"),
                observed.get("cached_input_tokens"),
                observed.get("output_tokens"),
                thread_id,
                route_id,
            ),
        )


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

    codex_binary = find_codex(arguments)
    selected_model = FAST_MODELS[args.work_type]
    audit_dir = resolve_audit_dir(args.data_dir)
    route_id = start_external_audit(
        audit_dir,
        task_name=task_name,
        workdir=workdir,
        work_type=args.work_type,
        model=selected_model,
        effort=args.reasoning_effort,
        sandbox=args.sandbox,
        parent_session_id=os.environ.get("CODEX_THREAD_ID"),
    )
    command = [
        codex_binary,
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
        selected_model,
        "-C",
        str(workdir),
    ]
    if args.capabilities == "minimal":
        command.append("--ignore-rules")
    if args.result_file is not None:
        command.extend(["--output-last-message", str(args.result_file.expanduser().resolve())])
    events_path = worker_events_path(task_name)
    persistent_events = events_path is not None
    temporary_events: tempfile.TemporaryDirectory[str] | None = None
    if events_path is None and audit_dir is not None:
        temporary_events = tempfile.TemporaryDirectory(prefix="goldilocks-worker-events-")
        events_path = Path(temporary_events.name) / f"{task_name}.events.jsonl"
    if events_path is not None:
        command.append("--json")
    command.append("-")

    prompt = build_prompt(task_name, args.work_type, workdir, contract)
    try:
        with worker_environment(args.capabilities) as environment:
            thread_id: str | None = None
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
                thread_id, final_message = event_result(events_path)
                print(
                    json.dumps(
                        {
                            "task_name": task_name,
                            "model": FAST_MODELS[args.work_type],
                            "returncode": completed.returncode,
                            "events": str(events_path) if persistent_events else None,
                            "thread_id": thread_id,
                            "route_id": route_id,
                        }
                    )
                )
                if args.result_file is not None:
                    result_path = args.result_file.expanduser().resolve()
                    if result_path.is_file():
                        print(result_path.read_text(encoding="utf-8").strip())
                elif final_message:
                    print(final_message.strip())
            observed = inspect_worker_rollout(environment, thread_id)
            finish_external_audit(
                audit_dir, route_id, completed.returncode, observed, thread_id
            )
    except KeyboardInterrupt:
        finish_external_audit(audit_dir, route_id, 130, {})
        return 130
    except OSError as error:
        finish_external_audit(audit_dir, route_id, 127, {})
        print(f"Goldilocks could not start the Fast worker: {error}", file=sys.stderr)
        return 127
    finally:
        if temporary_events is not None:
            temporary_events.cleanup()
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
