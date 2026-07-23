#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "plugins" / "goldilocks" / "scripts" / "update_checker.py"
HOOKS = ROOT / "plugins" / "goldilocks" / "hooks" / "hooks.json"


class ManifestHandler(BaseHTTPRequestHandler):
    version = "0.3.1"
    etag = '"release-031"'
    requests = 0

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        type(self).requests += 1
        if self.headers.get("If-None-Match") == type(self).etag:
            self.send_response(304)
            self.end_headers()
            return

        body = json.dumps({"version": type(self).version}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("ETag", type(self).etag)
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args: object) -> None:
        return


def write_manifest(plugin_root: Path, version: str) -> None:
    manifest = plugin_root / ".codex-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps({"name": "goldilocks", "version": version}), encoding="utf-8")


def run_checker(
    plugin_root: Path,
    data_dir: Path,
    url: str,
    *,
    enabled: str = "1",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "PLUGIN_ROOT": str(plugin_root),
            "PLUGIN_DATA": str(data_dir),
            "GOLDILOCKS_UPDATE_CHECK": enabled,
            "GOLDILOCKS_UPDATE_URL": url,
            "GOLDILOCKS_UPDATE_TIMEOUT_SECONDS": "0.5",
        }
    )
    return subprocess.run(
        [sys.executable, str(CHECKER)],
        input=json.dumps({"hook_event_name": "SessionStart", "cwd": str(ROOT)}),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def expire_check(data_dir: Path) -> None:
    with sqlite3.connect(data_dir / "orchestration.db") as connection:
        connection.execute("UPDATE update_state SET checked_at = 0 WHERE singleton = 1")


def main() -> None:
    ManifestHandler.requests = 0
    server = ThreadingHTTPServer(("127.0.0.1", 0), ManifestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/plugin.json"

    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin_root = root / "plugin"
            data_dir = root / "data"
            write_manifest(plugin_root, "0.3.0+codex.local")

            available = run_checker(plugin_root, data_dir, url)
            assert available.returncode == 0, available.stderr
            notice = json.loads(available.stdout)
            message = notice["systemMessage"]
            context = notice["hookSpecificOutput"]["additionalContext"]
            assert "0.3.0" in message and "0.3.1" in message
            assert "codex plugin marketplace upgrade goldilocks-local" in message
            assert "codex plugin add goldilocks@goldilocks-local" in message
            assert "explicit user approval" in context
            assert ManifestHandler.requests == 1

            throttled = run_checker(plugin_root, data_dir, url)
            assert throttled.returncode == 0, throttled.stderr
            assert throttled.stdout == "", "checks inside 24 hours must stay silent and skip network"
            assert ManifestHandler.requests == 1

            expire_check(data_dir)
            unchanged = run_checker(plugin_root, data_dir, url)
            assert unchanged.returncode == 0, unchanged.stderr
            assert unchanged.stdout == "", "an unchanged ETag must stay silent"
            assert ManifestHandler.requests == 2

            ManifestHandler.version = "0.3.2"
            ManifestHandler.etag = '"release-032"'
            expire_check(data_dir)
            next_release = run_checker(plugin_root, data_dir, url)
            assert next_release.returncode == 0, next_release.stderr
            assert "0.3.2" in json.loads(next_release.stdout)["systemMessage"]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin_root = root / "plugin"
            data_dir = root / "data"
            write_manifest(plugin_root, "0.3.2+codex.current")
            current = run_checker(plugin_root, data_dir, url)
            assert current.returncode == 0, current.stderr
            assert current.stdout == "", "current installations must stay silent"

            write_manifest(plugin_root, "0.3.1+codex.downgraded")
            expire_check(data_dir)
            cached_notice = run_checker(plugin_root, data_dir, url)
            assert cached_notice.returncode == 0, cached_notice.stderr
            assert "0.3.2" in json.loads(cached_notice.stdout)["systemMessage"], (
                "a 304 response must still compare cached latest version after a downgrade"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            before = ManifestHandler.requests
            disabled = run_checker(root / "plugin", root / "data", url, enabled="0")
            assert disabled.returncode == 0, disabled.stderr
            assert disabled.stdout == ""
            assert ManifestHandler.requests == before, "opt-out must not contact GitHub"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_manifest(root / "plugin", "0.3.0")
            ManifestHandler.version = "not-semver"
            ManifestHandler.etag = '"malformed-version"'
            malformed = run_checker(root / "plugin", root / "data", url)
            assert malformed.returncode == 0, malformed.stderr
            assert malformed.stdout == "", "malformed remote versions must stay silent"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_manifest(root / "plugin", "0.3.0")
            offline = run_checker(root / "plugin", root / "data", "http://127.0.0.1:9/plugin.json")
            assert offline.returncode == 0, offline.stderr
            assert offline.stdout == "", "network failures must never delay or pollute the task"

        hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
        commands = [hook for group in hooks for hook in group.get("hooks", [])]
        update_hooks = [hook for hook in commands if "update_checker.py" in hook.get("command", "")]
        assert len(update_hooks) == 1, "SessionStart must register one update checker"
        assert update_hooks[0]["timeout"] <= 4
        assert "statusMessage" not in update_hooks[0], "normal checks must have no visible startup status"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print("Goldilocks update checker contract passed.")


if __name__ == "__main__":
    main()
