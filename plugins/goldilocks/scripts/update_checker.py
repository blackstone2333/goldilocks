#!/usr/bin/env python3

"""Silently check for a newer Goldilocks release at most once per day."""

from __future__ import annotations

import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


CHECK_INTERVAL_SECONDS = 24 * 60 * 60
DEFAULT_TIMEOUT_SECONDS = 2.0
DEFAULT_MANIFEST_URL = (
    "https://api.github.com/repos/blackstone2333/goldilocks/contents/"
    "plugins/goldilocks/.codex-plugin/plugin.json?ref=main"
)
DISABLED_VALUES = {"0", "false", "no", "off", "disabled"}
VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?$"
)
SELECTOR_COMPONENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
NETWORK_GIT_SOURCE = re.compile(
    r"^(?:https://|ssh://(?:[A-Za-z0-9][A-Za-z0-9._-]*@)?)"
    r"[A-Za-z0-9][A-Za-z0-9.-]*/[A-Za-z0-9][A-Za-z0-9._/-]*\.git$",
    re.ASCII,
)
SCP_GIT_SOURCE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9._-]*@[A-Za-z0-9][A-Za-z0-9.-]*:[A-Za-z0-9][A-Za-z0-9._/-]*\.git$",
    re.ASCII,
)


def enabled() -> bool:
    return (
        os.environ.get("GOLDILOCKS_WORKER") != "1"
        and os.environ.get("GOLDILOCKS_UPDATE_CHECK", "1").strip().lower() not in DISABLED_VALUES
    )


def plugin_root() -> Path:
    configured = os.environ.get("PLUGIN_ROOT")
    if configured:
        return Path(configured).expanduser()
    return Path(__file__).resolve().parents[1]


def plugin_data() -> Path | None:
    configured = os.environ.get("PLUGIN_DATA")
    if not configured:
        return None
    path = Path(configured).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def parse_version(raw: object) -> tuple[tuple[int, int, int, int, str], str] | None:
    public = str(raw or "").split("+", 1)[0]
    match = VERSION_PATTERN.fullmatch(public)
    if match is None:
        return None
    major, minor, patch = (int(match.group(index)) for index in range(1, 4))
    prerelease = match.group(4)
    stable_rank = 1 if prerelease is None else 0
    return (major, minor, patch, stable_rank, prerelease or ""), public


def installed_version() -> tuple[tuple[int, int, int, int, str], str] | None:
    manifest = plugin_root() / ".codex-plugin" / "plugin.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return parse_version(payload.get("version"))


def valid_git_source(value: object) -> str | None:
    """Accept only a single Git remote argument suitable for an explicit handoff."""

    if not isinstance(value, str) or not value or len(value) > 2048 or not value.isascii():
        return None
    if NETWORK_GIT_SOURCE.fullmatch(value):
        return value
    if SCP_GIT_SOURCE.fullmatch(value):
        return value
    return None


def installed_git_marketplace() -> tuple[str, str, str] | None:
    """Return the aligned Git selector and remote, never guessing installation provenance."""

    try:
        result = subprocess.run(
            ["codex", "plugin", "list", "--json"],
            capture_output=True,
            check=False,
            text=True,
            timeout=1,
        )
        if result.returncode != 0:
            return None
        payload = json.loads(result.stdout)
        installed = payload.get("installed")
        if not isinstance(installed, list):
            return None
        root = plugin_root().resolve()
        for item in installed:
            if not isinstance(item, dict) or item.get("name") != "goldilocks":
                continue
            marketplace = item.get("marketplaceName")
            source = item.get("source")
            marketplace_source = item.get("marketplaceSource")
            if not isinstance(marketplace, str) or not SELECTOR_COMPONENT.fullmatch(marketplace):
                continue
            if not isinstance(source, dict) or not isinstance(source.get("path"), str):
                continue
            if not isinstance(marketplace_source, dict):
                continue
            if marketplace_source.get("sourceType") != "git":
                continue
            remote = valid_git_source(marketplace_source.get("source"))
            if remote is None:
                continue
            if item.get("pluginId") != f"goldilocks@{marketplace}":
                continue
            try:
                source_path = Path(source["path"]).expanduser().resolve()
            except OSError:
                continue
            if source_path == root:
                return "goldilocks", marketplace, remote
    except (OSError, ValueError, TypeError, json.JSONDecodeError, subprocess.SubprocessError):
        return None
    return None


def connect_state(root: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(root / "orchestration.db", timeout=3)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 3000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS update_state (
            singleton INTEGER PRIMARY KEY CHECK(singleton = 1),
            checked_at REAL NOT NULL DEFAULT 0,
            etag TEXT,
            latest_version TEXT,
            notified_version TEXT
        )
        """
    )
    connection.execute("INSERT OR IGNORE INTO update_state(singleton) VALUES (1)")
    connection.commit()
    return connection


def reserve_check(root: Path, checked_at: float) -> dict[str, Any] | None:
    connection = connect_state(root)
    try:
        connection.execute("BEGIN IMMEDIATE")
        state = connection.execute(
            "SELECT checked_at, etag, latest_version, notified_version "
            "FROM update_state WHERE singleton = 1"
        ).fetchone()
        if state is None:
            return None
        elapsed = checked_at - float(state["checked_at"])
        if elapsed < CHECK_INTERVAL_SECONDS:
            connection.commit()
            return None
        connection.execute(
            "UPDATE update_state SET checked_at = ? WHERE singleton = 1",
            (checked_at,),
        )
        connection.commit()
        return dict(state)
    finally:
        connection.close()


def request_timeout() -> float:
    try:
        value = float(os.environ.get("GOLDILOCKS_UPDATE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return min(max(value, 0.1), 3.0)


def fetch_manifest(etag: str | None) -> tuple[dict[str, Any] | None, str | None]:
    headers = {
        "Accept": "application/vnd.github.raw+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "goldilocks-update-checker",
    }
    if etag:
        headers["If-None-Match"] = etag
    request = urllib.request.Request(
        os.environ.get("GOLDILOCKS_UPDATE_URL", DEFAULT_MANIFEST_URL),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=request_timeout()) as response:
            body = response.read(65_537)
            if len(body) > 65_536:
                raise ValueError("remote manifest exceeds 64 KiB")
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("remote manifest is not an object")
            return payload, response.headers.get("ETag")
    except urllib.error.HTTPError as error:
        if error.code == 304:
            return None, etag
        raise


def record_remote(
    root: Path,
    remote_version: str,
    etag: str | None,
    *,
    should_notify: bool,
) -> bool:
    connection = connect_state(root)
    try:
        connection.execute("BEGIN IMMEDIATE")
        state = connection.execute(
            "SELECT notified_version FROM update_state WHERE singleton = 1"
        ).fetchone()
        notify = bool(
            should_notify
            and state is not None
            and state["notified_version"] != remote_version
        )
        connection.execute(
            """
            UPDATE update_state
            SET etag = ?, latest_version = ?,
                notified_version = CASE WHEN ? THEN ? ELSE notified_version END
            WHERE singleton = 1
            """,
            (etag, remote_version, int(notify), remote_version),
        )
        connection.commit()
        return notify
    finally:
        connection.close()


def emit_notice(current: str, latest: str, plugin: str, marketplace: str, remote: str) -> None:
    selector = f"{plugin}@{marketplace}"
    tag = f"v{latest}"
    message = (
        f"Goldilocks update available: installed {current}, latest {latest}. "
        f"Detected Git marketplace `{marketplace}`, plugin `{selector}`, and source `{remote}`. "
        "This check only discovered the update: no files were changed, and this task "
        "continues with the installed version. Reply that you approve the update; the "
        f"installing agent must first verify `{tag}` before mutation with `git ls-remote "
        f"--exit-code --refs {remote} refs/tags/{tag}`, then run `codex plugin marketplace "
        f"remove {marketplace} --json`, `codex plugin marketplace add {remote} --ref {tag} "
        f"--json`, and `codex plugin add {selector} --json`; then run Bootstrap "
        "plan/apply/check and start a new task. This checker never automatically upgrades, "
        "retains approval, or trusts changed Hooks."
    )
    print(
        json.dumps(
            {
                "systemMessage": message,
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": (
                        f"{message} Inform the user once. After explicit approval, verify {tag} "
                        "before removal, then use the displayed remove/add/add sequence and "
                        "$goldilocks-bootstrap for Bootstrap plan/apply/check; do not run an "
                        "automatic update or trust changed Hooks."
                    ),
                },
            },
            ensure_ascii=False,
        )
    )


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if payload.get("hook_event_name") != "SessionStart" or not enabled():
            return
        selector = installed_git_marketplace()
        if selector is None:
            return
        data = plugin_data()
        current = installed_version()
        if data is None or current is None:
            return
        state = reserve_check(data, time.time())
        if state is None:
            return
        manifest, etag = fetch_manifest(state.get("etag"))
        latest = parse_version(
            state.get("latest_version") if manifest is None else manifest.get("version")
        )
        if latest is None:
            return
        notify = record_remote(
            data,
            latest[1],
            etag,
            should_notify=latest[0] > current[0],
        )
        if notify:
            emit_notice(current[1], latest[1], *selector)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, sqlite3.Error, urllib.error.URLError):
        return


if __name__ == "__main__":
    main()
