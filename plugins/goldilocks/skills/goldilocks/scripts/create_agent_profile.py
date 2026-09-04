#!/usr/bin/env python3

"""Discover and create consent-gated dynamic Goldilocks worker profiles."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PLUGIN_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PLUGIN_ROOT / "scripts"))

import model_economics as economics  # noqa: E402
import dispatch_codex_worker as dispatcher  # noqa: E402


POLICY_VERSION = "0.6.0"
NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
EFFORTS = ("low", "medium", "high", "xhigh", "max")
SAFE_SANDBOXES = ("read-only", "workspace-write")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--economics", type=Path, default=economics.DEFAULT_ECONOMICS)
    common.add_argument(
        "--models-cache",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
        / "models_cache.json",
    )
    common.add_argument("--data-dir", type=Path)
    commands = value.add_subparsers(dest="command", required=True)

    discover = commands.add_parser("discover", parents=[common])
    discover.add_argument("--billing-channel")
    discover.add_argument("--require-capability", action="append", default=[])

    authorize = commands.add_parser("authorize", parents=[common])
    authorize.add_argument("--model", required=True)
    authorize.add_argument("--billing-channel", required=True)
    authorize.add_argument("--authority", required=True, choices=("explicit-user",))

    revoke = commands.add_parser("revoke", parents=[common])
    revoke.add_argument("--model", required=True)
    revoke.add_argument("--billing-channel", required=True)
    revoke.add_argument("--authority", required=True, choices=("explicit-user",))

    commands.add_parser("list", parents=[common])

    create = commands.add_parser("create", parents=[common])
    create.add_argument("--model", required=True)
    create.add_argument("--billing-channel", required=True)
    create.add_argument("--name")
    create.add_argument("--reasoning-effort", choices=EFFORTS, default="medium")
    create.add_argument("--sandbox", choices=SAFE_SANDBOXES, default="workspace-write")
    create.add_argument(
        "--capabilities",
        choices=dispatcher.CAPABILITY_PROFILES,
        default="project",
    )
    create.add_argument("--require-capability", action="append", default=[])
    create.add_argument("--output-dir", type=Path)
    return value


def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_data_dir(explicit: Path | None) -> Path:
    resolved = dispatcher.resolve_audit_dir(explicit)
    if resolved is None:
        raise ValueError(
            "Cannot identify one Goldilocks data directory; pass --data-dir explicitly."
        )
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def connect_authorizations(root: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(root / "orchestration.db", timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_authorizations (
            model TEXT NOT NULL,
            billing_channel TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('active', 'revoked')),
            authority TEXT NOT NULL,
            authorized_at TEXT NOT NULL,
            revoked_at TEXT,
            policy_version TEXT NOT NULL,
            PRIMARY KEY(model, billing_channel)
        )
        """
    )
    return connection


def visible_models(args: argparse.Namespace) -> set[str]:
    return economics.model_ids_from_cache(args.models_cache.expanduser().resolve())


def require_visible(args: argparse.Namespace, model: str) -> None:
    if model not in visible_models(args):
        raise ValueError(f"model {model} is not advertised by the current host")


def safe_name(model: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", model.lower()).strip("_")
    return f"dynamic_{normalized}"[:64]


def load_authorization(
    root: Path, model: str, billing_channel: str
) -> sqlite3.Row | None:
    with connect_authorizations(root) as connection:
        return connection.execute(
            "SELECT * FROM agent_authorizations WHERE model = ? AND billing_channel = ?",
            (model, billing_channel),
        ).fetchone()


def discover(args: argparse.Namespace) -> dict[str, Any]:
    registry = economics.load_economics(args.economics)
    visible = visible_models(args)
    required = set(args.require_capability)
    candidates: list[dict[str, Any]] = []
    for model in sorted(visible & set(registry["models"])):
        entry = registry["models"][model]
        capabilities = set(entry.get("capabilities") or [])
        if not required.issubset(capabilities):
            continue
        for channel in economics.available_channels(registry, model):
            if args.billing_channel and channel != args.billing_channel:
                continue
            try:
                snapshot = economics.pricing_snapshot(
                    registry,
                    model,
                    channel,
                    require_current=False,
                    require_rankable=False,
                )
                candidates.append(
                    {
                        "model": model,
                        "provider": snapshot["provider"],
                        "billing_channel": channel,
                        "currency": snapshot["currency"],
                        "input": snapshot["input"],
                        "cached_input": snapshot["cached_input"],
                        "output": snapshot["output"],
                        "price_current": snapshot["price_current"],
                        "rankable": snapshot["rankable"],
                        "capabilities": snapshot["capabilities"],
                        "source": snapshot["source"],
                    }
                )
            except economics.EconomicsError as error:
                candidates.append(
                    {
                        "model": model,
                        "billing_channel": channel,
                        "rankable": False,
                        "error": str(error),
                    }
                )
    return {
        "status": "discovered",
        "consumed_model_quota": False,
        "candidates": candidates,
    }


def authorize(args: argparse.Namespace) -> dict[str, Any]:
    require_visible(args, args.model)
    registry = economics.load_economics(args.economics)
    economics.pricing_snapshot(
        registry,
        args.model,
        args.billing_channel,
        require_current=False,
        require_rankable=False,
    )
    root = resolve_data_dir(args.data_dir)
    authorized_at = iso_now()
    with connect_authorizations(root) as connection:
        connection.execute(
            """
            INSERT INTO agent_authorizations (
                model, billing_channel, status, authority, authorized_at,
                revoked_at, policy_version
            ) VALUES (?, ?, 'active', ?, ?, NULL, ?)
            ON CONFLICT(model, billing_channel) DO UPDATE SET
                status = 'active', authority = excluded.authority,
                authorized_at = excluded.authorized_at, revoked_at = NULL,
                policy_version = excluded.policy_version
            """,
            (
                args.model,
                args.billing_channel,
                args.authority,
                authorized_at,
                POLICY_VERSION,
            ),
        )
    return {
        "status": "authorized",
        "scope": "global-model-and-billing-channel-until-revoked",
        "model": args.model,
        "billing_channel": args.billing_channel,
        "authorized_at": authorized_at,
    }


def revoke(args: argparse.Namespace) -> dict[str, Any]:
    root = resolve_data_dir(args.data_dir)
    revoked_at = iso_now()
    with connect_authorizations(root) as connection:
        row = connection.execute(
            "SELECT * FROM agent_authorizations WHERE model = ? AND billing_channel = ?",
            (args.model, args.billing_channel),
        ).fetchone()
        if row is None:
            raise ValueError("no matching dynamic-agent authorization exists")
        connection.execute(
            """
            UPDATE agent_authorizations
            SET status = 'revoked', revoked_at = ?, authority = ?, policy_version = ?
            WHERE model = ? AND billing_channel = ?
            """,
            (
                revoked_at,
                args.authority,
                POLICY_VERSION,
                args.model,
                args.billing_channel,
            ),
        )
    return {
        "status": "revoked",
        "model": args.model,
        "billing_channel": args.billing_channel,
        "revoked_at": revoked_at,
    }


def list_authorizations(args: argparse.Namespace) -> dict[str, Any]:
    root = resolve_data_dir(args.data_dir)
    with connect_authorizations(root) as connection:
        rows = connection.execute(
            """
            SELECT model, billing_channel, status, authority, authorized_at, revoked_at
            FROM agent_authorizations ORDER BY model, billing_channel
            """
        ).fetchall()
    return {"authorizations": [dict(row) for row in rows]}


def find_codex() -> str:
    configured = os.environ.get("GOLDILOCKS_CODEX_BIN")
    candidates = [configured, shutil.which("codex"), str(dispatcher.MACOS_APP_CODEX)]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
    raise ValueError("Codex CLI not found for dynamic-agent preflight")


def run_preflight(model: str) -> dict[str, Any]:
    codex = find_codex()
    with tempfile.TemporaryDirectory(prefix="goldilocks-agent-preflight-") as temporary:
        workdir = Path(temporary)
        events = workdir / "events.jsonl"
        command = [
            codex,
            "exec",
            "--disable",
            "multi_agent",
            "-c",
            'model_reasoning_effort="low"',
            "--sandbox",
            "read-only",
            "--color",
            "never",
            "--ignore-rules",
            "-m",
            model,
            "-C",
            str(workdir),
            "--json",
            "-",
        ]
        prompt = (
            "Goldilocks read-only route preflight. Do not call tools or modify files. "
            "Reply with exactly GOLDILOCKS_PREFLIGHT_OK."
        )
        with dispatcher.worker_environment("project") as environment:
            with events.open("x", encoding="utf-8") as stream:
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
            thread_id, final_message = dispatcher.event_result(events)
            observed = dispatcher.inspect_worker_rollout(environment, thread_id)
    if completed.returncode != 0:
        raise ValueError(f"read-only preflight failed with exit {completed.returncode}")
    if observed.get("actual_model") != model:
        raise ValueError(
            f"preflight requested {model}, observed {observed.get('actual_model') or 'unknown'}"
        )
    if observed.get("sandbox_policy_type") != "read-only":
        raise ValueError("preflight did not run in the read-only sandbox")
    if (final_message or "").strip() != "GOLDILOCKS_PREFLIGHT_OK":
        raise ValueError("preflight did not return the required completion marker")
    return {
        "status": "passed",
        "checked_at": iso_now(),
        "actual_model": observed.get("actual_model"),
        "actual_effort": observed.get("actual_effort"),
        "sandbox_policy_type": observed.get("sandbox_policy_type"),
        "permission_profile_type": observed.get("permission_profile_type"),
        "input_tokens": observed.get("input_tokens"),
        "cached_input_tokens": observed.get("cached_input_tokens"),
        "output_tokens": observed.get("output_tokens"),
    }


def create_profile(args: argparse.Namespace) -> dict[str, Any]:
    require_visible(args, args.model)
    root = resolve_data_dir(args.data_dir)
    authorization = load_authorization(root, args.model, args.billing_channel)
    if authorization is None or authorization["status"] != "active":
        raise ValueError(
            "dynamic-agent use is not authorized; ask the user, then run the authorize command"
        )
    registry = economics.load_economics(args.economics)
    snapshot = economics.pricing_snapshot(
        registry,
        args.model,
        args.billing_channel,
        require_current=True,
        require_rankable=True,
    )
    required = set(args.require_capability)
    available = set(snapshot.get("capabilities") or [])
    missing = sorted(required - available)
    if missing:
        raise ValueError(f"model {args.model} lacks required capabilities: {', '.join(missing)}")
    name = (args.name or safe_name(args.model)).strip().lower()
    if not NAME_PATTERN.fullmatch(name):
        raise ValueError("profile name must be 1-64 lowercase letters, digits, _ or -")
    output_dir = (args.output_dir or (root / "agent-profiles")).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{name}.json"
    if target.exists():
        raise ValueError(f"refusing to overwrite existing profile: {target}")
    preflight = run_preflight(args.model)
    profile = economics.sign_profile(
        {
            "schema_version": economics.PROFILE_SCHEMA_VERSION,
            "name": name,
            "source": "goldilocks-agent-factory",
            "tier": "fast",
            "model": args.model,
            "reasoning_effort": args.reasoning_effort,
            "sandbox": args.sandbox,
            "capabilities_profile": args.capabilities,
            "model_capabilities": snapshot["capabilities"],
            "may_delegate": False,
            "billing_channel": args.billing_channel,
            "pricing_snapshot": snapshot,
            "authorization": {
                "status": "active",
                "scope": "global-model-and-billing-channel-until-revoked",
                "authority": authorization["authority"],
                "authorized_at": authorization["authorized_at"],
            },
            "preflight": preflight,
            "created_at": iso_now(),
            "policy_version": POLICY_VERSION,
        }
    )
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(profile, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    return {
        "status": "created",
        "profile": str(target),
        "name": name,
        "model": args.model,
        "billing_channel": args.billing_channel,
        "authorization_scope": "global-model-and-billing-channel-until-revoked",
        "preflight": preflight,
    }


def main() -> None:
    args = parser().parse_args()
    if args.command == "discover":
        result = discover(args)
    elif args.command == "authorize":
        result = authorize(args)
    elif args.command == "revoke":
        result = revoke(args)
    elif args.command == "list":
        result = list_authorizations(args)
    else:
        result = create_profile(args)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, sqlite3.Error, TypeError, ValueError, economics.EconomicsError) as error:
        print(f"Goldilocks Agent Factory failed: {error}", file=sys.stderr)
        raise SystemExit(2)
