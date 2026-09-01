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
from typing import Any, Iterator


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import model_economics as economics  # noqa: E402
from model_naming import model_name_suffix, visible_task_name  # noqa: E402


SPARK_MODEL = "gpt-5.3-codex-spark"
LUNA_MODEL = "gpt-5.6-luna"
TERRA_MODEL = "gpt-5.6-terra"
FAST_MODELS = {
    "luna": LUNA_MODEL,
    "terra-standard": TERRA_MODEL,
    "spark-coding": SPARK_MODEL,
    # Backward-compatible aliases from Goldilocks <= 0.4.4.
    "general": LUNA_MODEL,
    "coding": SPARK_MODEL,
}
TASK_NAME_PATTERN = re.compile(r"^(?:fast|standard)__[a-z0-9][a-z0-9_-]*$")
MACOS_APP_CODEX = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
CAPABILITY_PROFILES = ("project", "minimal", "inherit")
POLICY_VERSION = "0.5.3-beta.8"


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        description=(
            "Run one complete Goldilocks worker contract with Luna, Terra, or Spark."
        )
    )
    value.add_argument("--workdir", required=True, type=Path, help="Assigned repository or worktree.")
    value.add_argument("--task-name", required=True, help="A fast__- or standard__-prefixed routing name.")
    value.add_argument("--task-file", required=True, type=Path, help="UTF-8 execution contract.")
    value.add_argument(
        "--work-type",
        choices=tuple(FAST_MODELS),
        default=None,
        help=(
            "luna selects Economy/Fast, terra-standard selects bounded Standard, and "
            "spark-coding selects the separate-pool coding specialist."
        ),
    )
    value.add_argument(
        "--reasoning-effort",
        choices=("low", "medium", "high", "xhigh", "max"),
        default=None,
        help="Use low for mechanical work; raise only when the contract needs it.",
    )
    value.add_argument(
        "--sandbox",
        choices=("read-only", "workspace-write"),
        default=None,
        help="Fast never receives danger-full-access through this adapter.",
    )
    value.add_argument(
        "--capabilities",
        choices=CAPABILITY_PROFILES,
        default=None,
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
    value.add_argument(
        "--agent-profile",
        type=Path,
        help=(
            "Consent-gated profile created by create_agent_profile.py. Profile values are "
            "pinned and cannot be silently overridden."
        ),
    )
    value.add_argument(
        "--billing-channel",
        help=(
            "Explicit active billing pool for official cost accounting. A dynamic profile "
            "already pins this value."
        ),
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
    return f"""You are a contracted Goldilocks worker. The owner fixed the material decisions.

Implement and verify only the contract below in the assigned workspace.

- Do not delegate, reroute, broaden scope, change shared interfaces, or take unapproved external/destructive actions.
- Do not rerun Goldilocks routing, continuity, update checks, or task ledgers.
- Treat listed units as one coherent batch; keep each independently checkable.
- Preserve unrelated work and repository rules. Stop rather than guess when a material decision is missing.
- At completion, report changed files, focused checks and results, then unresolved blockers or risks. Defects add an evidence-backed CAUSE or explicitly unknown, then fix and verification; expand when asked. No preamble or repeated recap.

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
    if len(candidates) == 1:
        return candidates[0]
    data_root = Path.home() / ".codex" / "plugins" / "data"
    directories = sorted(path for path in data_root.glob("goldilocks-*") if path.is_dir())
    if len(directories) == 1:
        return directories[0]
    codex = shutil.which("codex")
    if codex:
        try:
            installed = json.loads(
                subprocess.check_output(
                    [codex, "plugin", "list", "--json"],
                    text=True,
                    timeout=5,
                )
            ).get("installed", [])
            matches = [
                item
                for item in installed
                if item.get("name") == "goldilocks" and item.get("installed") is True
            ]
            if len(matches) == 1 and matches[0].get("marketplaceName"):
                return data_root / f"goldilocks-{matches[0]['marketplaceName']}"
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, AttributeError):
            pass
    return None


def route_role(work_type: str, profile_name: str | None = None) -> str:
    if profile_name:
        return profile_name
    if work_type == "terra-standard":
        return "goldilocks_terra_engineer"
    if work_type in {"spark-coding", "coding"}:
        return "goldilocks_spark_coder"
    return "goldilocks_luna_worker"


def authorization_active(root: Path | None, model: str, billing_channel: str) -> bool:
    if root is None or not (root / "orchestration.db").is_file():
        return False
    try:
        with sqlite3.connect(root / "orchestration.db", timeout=3) as connection:
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            if "agent_authorizations" not in tables:
                return False
            row = connection.execute(
                """
                SELECT status FROM agent_authorizations
                WHERE model = ? AND billing_channel = ?
                """,
                (model, billing_channel),
            ).fetchone()
            return row is not None and row[0] == "active"
    except sqlite3.Error:
        return False


def load_agent_profile(
    arguments: argparse.ArgumentParser,
    path: Path,
    audit_dir: Path | None,
) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    try:
        profile = economics.load_json(resolved)
        economics.verify_profile(profile)
    except economics.EconomicsError as error:
        fail(arguments, str(error))
    if profile.get("tier") != "fast":
        fail(arguments, "dynamic codex-exec profiles must remain Fast leaves")
    model = str(profile.get("model") or "")
    billing_channel = str(profile.get("billing_channel") or "")
    if not model or not billing_channel:
        fail(arguments, "dynamic agent profile lacks model or billing channel")
    try:
        visible = economics.model_ids_from_cache(source_codex_home() / "models_cache.json")
    except economics.EconomicsError as error:
        fail(arguments, str(error))
    if model not in visible:
        fail(arguments, f"profile model {model} is no longer advertised by the current host")
    authorization_root = audit_dir
    if authorization_root is None and resolved.parent.name == "agent-profiles":
        authorization_root = resolved.parent.parent
    if not authorization_active(authorization_root, model, billing_channel):
        fail(
            arguments,
            f"authorization for {model}/{billing_channel} is absent or revoked",
        )
    return profile


def fixed_pricing_snapshot(
    model: str, billing_channel: str | None = None
) -> dict[str, Any] | None:
    billing_channel = billing_channel or os.environ.get("GOLDILOCKS_BILLING_CHANNEL")
    if not billing_channel:
        return None
    try:
        registry = economics.load_economics()
        return economics.pricing_snapshot(
            registry,
            model,
            billing_channel,
            require_current=False,
            require_rankable=False,
        )
    except economics.EconomicsError:
        return None


def contract_fingerprint(task_name: str, contract: str) -> str:
    normalized = re.sub(r"\d+", "#", f"{task_name}\n{contract}".lower())
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def ensure_experiences_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
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
        )
        """
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
    task_fingerprint: str,
    agent_role: str,
    agent_profile: str | None,
    billing_channel: str | None,
    pricing_snapshot: dict[str, Any] | None,
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
                task_fingerprint TEXT,
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
                agent_profile TEXT,
                billing_channel TEXT,
                pricing_snapshot TEXT,
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
        if "task_fingerprint" not in columns:
            connection.execute(
                "ALTER TABLE external_routes ADD COLUMN task_fingerprint TEXT"
            )
        for name in ("agent_profile", "billing_channel", "pricing_snapshot"):
            if name not in columns:
                connection.execute(f"ALTER TABLE external_routes ADD COLUMN {name} TEXT")
        ensure_experiences_schema(connection)
        connection.execute(
            """
            INSERT INTO external_routes (
                route_id, task_name, cwd_hash, task_fingerprint,
                expected_agent_type, expected_model,
                expected_effort, transport, requested_sandbox, status, started_at,
                parent_session_id, agent_profile, billing_channel, pricing_snapshot,
                policy_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'codex-exec', ?, 'started', ?, ?, ?, ?, ?, ?)
            """,
            (
                route_id,
                task_name,
                hashlib.sha256(str(workdir).encode()).hexdigest(),
                task_fingerprint,
                agent_role,
                model,
                effort,
                sandbox,
                datetime.now(timezone.utc).isoformat(),
                parent_session_id,
                agent_profile,
                billing_channel,
                (
                    json.dumps(pricing_snapshot, ensure_ascii=False, sort_keys=True)
                    if pricing_snapshot is not None
                    else None
                ),
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
            "SELECT * FROM external_routes WHERE route_id = ?", (route_id,)
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
        actual_model = str(observed.get("actual_model") or "")
        if (
            row is not None
            and thread_id
            and actual_model
            and actual_model == row["expected_model"]
            and row["task_fingerprint"]
        ):
            ensure_experiences_schema(connection)
            connection.execute(
                """
                INSERT INTO experiences (
                    cwd_hash, task_fingerprint, tier, model, observed_completions,
                    verified_passes, verified_failures, last_seen_at, policy_version
                ) VALUES (?, ?, 'fast', ?, 1, 0, 0, ?, ?)
                ON CONFLICT(cwd_hash, task_fingerprint, tier, model, policy_version)
                DO UPDATE SET
                    observed_completions = observed_completions + 1,
                    last_seen_at = excluded.last_seen_at
                """,
                (
                    row["cwd_hash"],
                    row["task_fingerprint"],
                    actual_model,
                    stopped.isoformat(),
                    row["policy_version"],
                ),
            )


def main() -> int:
    arguments = parser()
    args = arguments.parse_args()

    requested_task_name = args.task_name.strip().lower()
    if not TASK_NAME_PATTERN.fullmatch(requested_task_name):
        fail(arguments, "task-name must start with fast__ or standard__ and contain only letters, digits, _ or -")

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

    audit_dir = resolve_audit_dir(args.data_dir)
    profile: dict[str, Any] | None = None
    if args.agent_profile is not None:
        profile = load_agent_profile(arguments, args.agent_profile, audit_dir)
        selected_model = str(profile["model"])
        selected_work_type = f"profile:{profile['name']}"
        selected_effort = str(profile["reasoning_effort"])
        selected_sandbox = str(profile["sandbox"])
        selected_capabilities = str(profile["capabilities_profile"])
        for label, explicit, pinned in (
            ("work-type", args.work_type, None),
            ("reasoning-effort", args.reasoning_effort, selected_effort),
            ("sandbox", args.sandbox, selected_sandbox),
            ("capabilities", args.capabilities, selected_capabilities),
        ):
            if explicit is not None and (pinned is None or explicit != pinned):
                fail(arguments, f"--{label} conflicts with the consent-gated agent profile")
        selected_role = str(profile["name"])
        profile_path = str(args.agent_profile.expanduser().resolve())
        billing_channel = str(profile["billing_channel"])
        if args.billing_channel is not None and args.billing_channel != billing_channel:
            fail(arguments, "--billing-channel conflicts with the consent-gated agent profile")
        pricing = profile.get("pricing_snapshot")
    else:
        selected_work_type = args.work_type or "luna"
        selected_model = FAST_MODELS[selected_work_type]
        selected_effort = args.reasoning_effort or "medium"
        selected_sandbox = args.sandbox or "workspace-write"
        selected_capabilities = args.capabilities or "project"
        selected_role = route_role(selected_work_type)
        profile_path = None
        requested_channel = args.billing_channel or os.environ.get(
            "GOLDILOCKS_BILLING_CHANNEL"
        )
        pricing = fixed_pricing_snapshot(selected_model, requested_channel)
        billing_channel = requested_channel
    task_name = visible_task_name(requested_task_name, selected_model)
    codex_binary = find_codex(arguments)
    route_id = start_external_audit(
        audit_dir,
        task_name=task_name,
        workdir=workdir,
        work_type=selected_work_type,
        model=selected_model,
        effort=selected_effort,
        sandbox=selected_sandbox,
        parent_session_id=os.environ.get("CODEX_THREAD_ID"),
        task_fingerprint=contract_fingerprint(task_name, contract),
        agent_role=selected_role,
        agent_profile=profile_path,
        billing_channel=billing_channel,
        pricing_snapshot=pricing if isinstance(pricing, dict) else None,
    )
    command = [
        codex_binary,
        "exec",
        "--disable",
        "multi_agent",
        "-c",
        f'model_reasoning_effort="{selected_effort}"',
        "--sandbox",
        selected_sandbox,
        "--color",
        "never",
        "-m",
        selected_model,
        "-C",
        str(workdir),
    ]
    if selected_capabilities == "minimal":
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

    prompt = build_prompt(task_name, selected_work_type, workdir, contract)
    try:
        with worker_environment(selected_capabilities) as environment:
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
                            "model": selected_model,
                            "agent_profile": profile_path,
                            "billing_channel": billing_channel,
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
