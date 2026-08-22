#!/usr/bin/env python3

"""Silently discover a newer Goldilocks release; never install it."""

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
from functools import total_ordering
from pathlib import Path
from typing import Any


CHECK_INTERVAL_SECONDS = 24 * 60 * 60
FAILURE_BACKOFF_SECONDS = 15 * 60
RESERVATION_SECONDS = 10
DEFAULT_TIMEOUT_SECONDS = 2.0
DEFAULT_RELEASES_URL = "https://api.github.com/repos/blackstone2333/goldilocks/releases?per_page=100"
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


@total_ordering
class SemanticVersion:
    """A small SemVer comparator, including numeric prerelease identifiers."""

    def __init__(self, major: int, minor: int, patch: int, prerelease: str | None) -> None:
        self.major, self.minor, self.patch = major, minor, patch
        self.prerelease = tuple(prerelease.split(".")) if prerelease else ()

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.prerelease) == (
            other.major, other.minor, other.patch, other.prerelease
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if core != other_core:
            return core < other_core
        if not self.prerelease or not other.prerelease:
            return bool(self.prerelease) and not bool(other.prerelease)
        for left, right in zip(self.prerelease, other.prerelease):
            if left == right:
                continue
            left_numeric, right_numeric = left.isdigit(), right.isdigit()
            if left_numeric and right_numeric:
                return int(left) < int(right)
            if left_numeric != right_numeric:
                return left_numeric
            return left < right
        return len(self.prerelease) < len(other.prerelease)
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


def parse_version(raw: object) -> tuple[SemanticVersion, str] | None:
    public = str(raw or "").split("+", 1)[0]
    if public.startswith("v"):
        public = public[1:]
    match = VERSION_PATTERN.fullmatch(public)
    if match is None:
        return None
    major, minor, patch = (int(match.group(index)) for index in range(1, 4))
    prerelease = match.group(4)
    if prerelease:
        identifiers = prerelease.split(".")
        if any(not part or (part.isdigit() and len(part) > 1 and part.startswith("0")) for part in identifiers):
            return None
    return SemanticVersion(major, minor, patch, prerelease), public


def installed_version() -> tuple[SemanticVersion, str] | None:
    manifest = plugin_root() / ".codex-plugin" / "plugin.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return parse_version(payload.get("version"))


def installed_manifest_version() -> str | None:
    try:
        payload = json.loads((plugin_root() / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    except (OSError, TypeError, json.JSONDecodeError):
        return None
    return payload.get("version") if isinstance(payload.get("version"), str) else None


def valid_git_source(value: object) -> str | None:
    """Accept only a single Git remote argument suitable for an explicit handoff."""

    if not isinstance(value, str) or not value or len(value) > 2048 or not value.isascii():
        return None
    if NETWORK_GIT_SOURCE.fullmatch(value):
        return value
    if SCP_GIT_SOURCE.fullmatch(value):
        return value
    return None


def cache_matches_marketplace_snapshot(
    root: Path, source_path: Path, marketplace: str, listed_version: object
) -> bool:
    """Match Codex's Git snapshot listing to the versioned cache running this Hook."""

    manifest_version = installed_manifest_version()
    if listed_version is not None and listed_version != manifest_version:
        return False
    if source_path == root:
        return True  # Deterministic local-test and older-host shape.
    home = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser().resolve()
    expected_snapshot = home / ".tmp" / "marketplaces" / marketplace / "plugins" / "goldilocks"
    expected_cache_parent = home / "plugins" / "cache" / marketplace / "goldilocks"
    return (
        source_path == expected_snapshot
        and root.parent == expected_cache_parent
        and root.name == manifest_version
    )


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
            if cache_matches_marketplace_snapshot(root, source_path, marketplace, item.get("version")):
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
            checked_installed_version TEXT,
            retry_after REAL NOT NULL DEFAULT 0,
            reservation_id INTEGER NOT NULL DEFAULT 0,
            reserved_until REAL NOT NULL DEFAULT 0,
            etag TEXT,
            latest_version TEXT,
            latest_is_prerelease INTEGER NOT NULL DEFAULT 0,
            notified_version TEXT
        )
        """
    )
    # Existing installations have the earlier, smaller schema.
    existing = {row[1] for row in connection.execute("PRAGMA table_info(update_state)")}
    for name, definition in (
        ("retry_after", "REAL NOT NULL DEFAULT 0"),
        ("checked_installed_version", "TEXT"),
        ("reservation_id", "INTEGER NOT NULL DEFAULT 0"),
        ("reserved_until", "REAL NOT NULL DEFAULT 0"),
        ("latest_is_prerelease", "INTEGER NOT NULL DEFAULT 0"),
    ):
        if name not in existing:
            connection.execute(f"ALTER TABLE update_state ADD COLUMN {name} {definition}")
    connection.execute("INSERT OR IGNORE INTO update_state(singleton) VALUES (1)")
    connection.commit()
    return connection


def reserve_check(root: Path, now: float, current_version: str) -> dict[str, Any] | None:
    connection = connect_state(root)
    try:
        connection.execute("BEGIN IMMEDIATE")
        state = connection.execute(
            "SELECT checked_at, checked_installed_version, retry_after, reservation_id, reserved_until, etag, latest_version, "
            "latest_is_prerelease, notified_version "
            "FROM update_state WHERE singleton = 1"
        ).fetchone()
        if state is None:
            return None
        version_changed = state["checked_installed_version"] != current_version
        if version_changed:
            connection.execute(
                """
                UPDATE update_state
                SET checked_at = 0, retry_after = 0, reserved_until = 0, etag = NULL,
                    latest_version = NULL, latest_is_prerelease = 0, notified_version = NULL,
                    checked_installed_version = ?
                WHERE singleton = 1
                """,
                (current_version,),
            )
            state = dict(state)
            state.update(
                checked_at=0, retry_after=0, reserved_until=0, etag=None, latest_version=None,
                latest_is_prerelease=0, notified_version=None, checked_installed_version=current_version,
            )
        if now - float(state["checked_at"]) < CHECK_INTERVAL_SECONDS:
            connection.commit()
            return None
        if now < float(state["retry_after"]) or now < float(state["reserved_until"]):
            connection.commit()
            return None
        reservation_id = int(state["reservation_id"]) + 1
        connection.execute(
            "UPDATE update_state SET reservation_id = ?, reserved_until = ?, checked_installed_version = ? WHERE singleton = 1",
            (reservation_id, now + RESERVATION_SECONDS, current_version),
        )
        connection.commit()
        reserved = dict(state)
        reserved["reservation_id"] = reservation_id
        return reserved
    finally:
        connection.close()


def request_timeout() -> float:
    try:
        value = float(os.environ.get("GOLDILOCKS_UPDATE_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS
    return min(max(value, 0.1), 3.0)


def fetch_releases(etag: str | None) -> tuple[Any | None, str | None]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "goldilocks-update-checker",
    }
    if etag:
        headers["If-None-Match"] = etag
    request = urllib.request.Request(
        os.environ.get("GOLDILOCKS_UPDATE_URL", DEFAULT_RELEASES_URL),
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=request_timeout()) as response:
            body = response.read(65_537)
            if len(body) > 65_536:
                raise ValueError("remote manifest exceeds 64 KiB")
            payload = json.loads(body.decode("utf-8"))
            if not isinstance(payload, (dict, list)):
                raise ValueError("remote release response is not an object or list")
            return payload, response.headers.get("ETag")
    except urllib.error.HTTPError as error:
        if error.code == 304:
            return None, etag
        raise


def select_latest_release(
    payload: Any,
    current: tuple[SemanticVersion, str],
) -> tuple[SemanticVersion, str, bool] | None:
    """Choose an eligible published release for this installation channel."""

    # A one-object manifest remains supported only as a deterministic local override.
    if isinstance(payload, dict):
        parsed = parse_version(payload.get("version"))
        if parsed is None:
            return None
        return parsed[0], parsed[1], bool(parsed[0].prerelease)
    if not isinstance(payload, list):
        return None
    allow_prereleases = bool(current[0].prerelease)
    candidates: list[tuple[SemanticVersion, str, bool]] = []
    for release in payload:
        if not isinstance(release, dict) or release.get("draft") is True:
            continue
        is_prerelease = release.get("prerelease") is True
        if is_prerelease and not allow_prereleases:
            continue
        parsed = parse_version(release.get("tag_name"))
        if parsed is None:
            continue
        if not is_prerelease and parsed[0].prerelease:
            continue
        candidates.append((parsed[0], parsed[1], is_prerelease))
    return max(candidates, default=None, key=lambda item: item[0])


def record_remote(
    root: Path,
    reservation_id: int,
    checked_at: float,
    remote_version: str,
    etag: str | None,
    is_prerelease: bool,
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
        updated = connection.execute(
            """
            UPDATE update_state
            SET checked_at = ?, retry_after = 0, reserved_until = 0, etag = ?, latest_version = ?,
                latest_is_prerelease = ?,
                notified_version = CASE WHEN ? THEN ? ELSE notified_version END
            WHERE singleton = 1 AND reservation_id = ?
            """,
            (checked_at, etag, remote_version, int(is_prerelease), int(notify), remote_version, reservation_id),
        )
        if updated.rowcount != 1:
            connection.commit()
            return False
        connection.commit()
        return notify
    finally:
        connection.close()


def record_failure(root: Path, reservation_id: int, now: float) -> None:
    """Short retry after failures; an obsolete request cannot erase newer state."""

    connection = connect_state(root)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute(
            """
            UPDATE update_state
            SET retry_after = ?, reserved_until = 0
            WHERE singleton = 1 AND reservation_id = ?
            """,
            (now + FAILURE_BACKOFF_SECONDS, reservation_id),
        )
        connection.commit()
    finally:
        connection.close()


def emit_notice(current: str, latest: str, plugin: str, marketplace: str, remote: str) -> None:
    selector = f"{plugin}@{marketplace}"
    tag = f"v{latest}"
    message = (
        f"Goldilocks update available: installed {current}, latest {latest}. "
        f"Detected Git marketplace `{marketplace}`, plugin `{selector}`, and source `{remote}`. "
        "This check only discovered the update: no files were changed, and this task "
        "continues with the installed version. Reply that you approve the update; then the "
        f"installing agent must own the complete verification and upgrade, first verifying `{tag}` "
        "before mutation with `git ls-remote "
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
                        "automatic update, retain approval, or trust changed Hooks."
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
        state = reserve_check(data, time.time(), current[1])
        if state is None:
            return
        payload, etag = fetch_releases(state.get("etag"))
        if payload is None:
            cached = parse_version(state.get("latest_version"))
            if cached is None:
                record_failure(data, state["reservation_id"], time.time())
                return
            latest = (cached[0], cached[1], bool(state.get("latest_is_prerelease")))
        else:
            latest = select_latest_release(payload, current)
            if latest is None:
                record_failure(data, state["reservation_id"], time.time())
                return
        notify = record_remote(
            data,
            state["reservation_id"],
            time.time(),
            latest[1],
            etag,
            latest[2],
            should_notify=latest[0] > current[0]
            and (bool(current[0].prerelease) or not latest[2]),
        )
        if notify:
            emit_notice(current[1], latest[1], *selector)
    except (OSError, ValueError, TypeError, json.JSONDecodeError, sqlite3.Error, urllib.error.URLError):
        try:
            if "data" in locals() and data is not None and "state" in locals() and state is not None:
                record_failure(data, state["reservation_id"], time.time())
        except (OSError, sqlite3.Error, KeyError):
            pass
        return


if __name__ == "__main__":
    main()
