#!/usr/bin/env python3

from __future__ import annotations

import json
import importlib.util
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
REMINDER = ROOT / "plugins" / "goldilocks" / "scripts" / "update_reminder.py"
HOOKS = ROOT / "plugins" / "goldilocks" / "hooks" / "hooks.json"


class ManifestHandler(BaseHTTPRequestHandler):
    version = "0.3.1"
    etag = '"release-031"'
    requests = 0
    payload: object | None = None
    if_none_match: list[str | None] = []

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        type(self).requests += 1
        type(self).if_none_match.append(self.headers.get("If-None-Match"))
        if self.headers.get("If-None-Match") == type(self).etag:
            self.send_response(304)
            self.end_headers()
            return

        payload = type(self).payload
        body = json.dumps({"version": type(self).version} if payload is None else payload).encode("utf-8")
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


def write_fake_codex(
    directory: Path,
    plugin_root: Path,
    *,
    marketplace: str = "goldilocks-release",
    source_type: str = "git",
    git_source: str = "https://github.com/blackstone2333/goldilocks.git",
    aligned: bool = True,
    source_path: Path | None = None,
    listed_version: str | None = None,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    source_root = source_path or (plugin_root if aligned else plugin_root.parent / "different-plugin")
    listing = {
        "installed": [
            {
                "pluginId": f"goldilocks@{marketplace}",
                "name": "goldilocks",
                "marketplaceName": marketplace,
                "version": listed_version,
                "source": {"source": "local", "path": str(source_root)},
                "marketplaceSource": {
                    "sourceType": source_type,
                    "source": git_source,
                },
            }
        ]
    }
    command = directory / "codex"
    command.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        f"print({json.dumps(json.dumps(listing))})\n",
        encoding="utf-8",
    )
    command.chmod(0o755)
    return directory


def run_checker(
    plugin_root: Path,
    data_dir: Path,
    url: str,
    *,
    enabled: str = "1",
    worker: bool = False,
    marketplace: str = "goldilocks-release",
    source_type: str = "git",
    git_source: str = "https://github.com/blackstone2333/goldilocks.git",
    aligned: bool = True,
    source_path: Path | None = None,
    listed_version: str | None = None,
    codex_home: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    fake_bin = write_fake_codex(
        plugin_root.parent / "fake-bin",
        plugin_root,
        marketplace=marketplace,
        source_type=source_type,
        git_source=git_source,
        aligned=aligned,
        source_path=source_path,
        listed_version=listed_version,
    )
    env = os.environ.copy()
    env.update(
        {
            "PLUGIN_ROOT": str(plugin_root),
            "PLUGIN_DATA": str(data_dir),
            "GOLDILOCKS_UPDATE_CHECK": enabled,
            "GOLDILOCKS_UPDATE_URL": url,
            "GOLDILOCKS_UPDATE_TIMEOUT_SECONDS": "0.5",
            "GOLDILOCKS_WORKER": "1" if worker else "0",
            "NO_PROXY": "127.0.0.1,localhost",
            "no_proxy": "127.0.0.1,localhost",
            "PATH": f"{fake_bin}{os.pathsep}{env.get('PATH', '')}",
        }
    )
    if codex_home is not None:
        env["CODEX_HOME"] = str(codex_home)
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


def clear_retry(data_dir: Path) -> None:
    with sqlite3.connect(data_dir / "orchestration.db") as connection:
        connection.execute("UPDATE update_state SET retry_after = 0, reserved_until = 0 WHERE singleton = 1")


def run_reminder(
    plugin_root: Path, data_dir: Path, *, language: str = "zh", turn_id: str = "turn-1"
) -> subprocess.CompletedProcess[str]:
    prompt = "请修复这个功能。" if language == "zh" else "Please fix this feature."
    return subprocess.run(
        [sys.executable, str(REMINDER)],
        input=json.dumps({"hook_event_name": "UserPromptSubmit", "session_id": "session-1", "turn_id": turn_id, "prompt": prompt}),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PLUGIN_ROOT": str(plugin_root), "PLUGIN_DATA": str(data_dir)},
    )


def main() -> None:
    spec = importlib.util.spec_from_file_location("update_checker", CHECKER)
    assert spec is not None and spec.loader is not None
    checker = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = checker
    spec.loader.exec_module(checker)
    assert checker.parse_version("0.5.3-beta.10")[0] > checker.parse_version("0.5.3-beta.9")[0]
    assert checker.parse_version("0.5.3")[0] > checker.parse_version("0.5.3-beta.99")[0]
    assert checker.parse_version("0.5.3-beta.01") is None
    assert checker.parse_version("0.5.3-beta..1") is None

    with tempfile.TemporaryDirectory() as temp_dir:
        data = Path(temp_dir)
        data.mkdir(exist_ok=True)
        old = checker.reserve_check(data, 100_000.0, "0.5.1")
        assert old is not None
        with sqlite3.connect(data / "orchestration.db") as connection:
            connection.execute("UPDATE update_state SET reserved_until = 0")
        new = checker.reserve_check(data, 100_001.0, "0.5.1")
        assert new is not None
        assert checker.record_remote(data, new["reservation_id"], 100_002.0, "0.5.2", '"new"', False,
                                     should_notify=False) is False
        checker.record_failure(data, old["reservation_id"], 101_000.0)
        with sqlite3.connect(data / "orchestration.db") as connection:
            state = connection.execute("SELECT latest_version, retry_after FROM update_state").fetchone()
        assert state == ("0.5.2", 0), "a late failed request must not overwrite a newer success"

    ManifestHandler.requests = 0
    ManifestHandler.payload = None
    ManifestHandler.if_none_match = []
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
            assert "goldilocks@goldilocks-release" in message
            assert "goldilocks-release" in message
            assert "https://github.com/blackstone2333/goldilocks.git" in message
            assert "INTERNAL Goldilocks update handoff" in message
            assert "do not separately narrate this block" in message
            assert "per-root update_reminder owns the only user-visible update notice" in message
            assert "Reply that you approve the update" not in message
            assert "codex plugin marketplace upgrade" not in message
            assert (
                "git ls-remote --exit-code --refs https://github.com/blackstone2333/goldilocks.git "
                "refs/tags/v0.3.1"
            ) in message
            assert "codex plugin marketplace remove goldilocks-release --json" in message
            assert (
                "codex plugin marketplace add https://github.com/blackstone2333/goldilocks.git "
                "--ref v0.3.1 --json"
            ) in message
            assert "codex plugin add goldilocks@goldilocks-release --json" in message
            assert message.index("git ls-remote") < message.index("codex plugin marketplace remove")
            assert "Bootstrap plan/apply/check" in context
            assert ManifestHandler.requests == 1

            zh_reminder = run_reminder(plugin_root, data_dir)
            assert zh_reminder.returncode == 0, zh_reminder.stderr
            zh_context = json.loads(zh_reminder.stdout)["hookSpecificOutput"]["additionalContext"]
            assert "⚠️ **Goldilocks 可更新：v0.3.0 → v0.3.1**" in zh_context
            assert "回复“更新”即可升级；当前任务仍使用 v0.3.0。" in zh_context
            en_reminder = run_reminder(plugin_root, data_dir, language="en")
            assert "⚠️ **Goldilocks update available: v0.3.0 → v0.3.1**" in en_reminder.stdout

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
            ManifestHandler.payload = [
                {"tag_name": "v0.5.3-beta.10", "prerelease": True, "draft": False},
                {"tag_name": "v0.5.2", "prerelease": False, "draft": False},
            ]
            ManifestHandler.etag = '"release-api-stable"'
            write_manifest(root / "plugin", "0.5.1")
            stable = run_checker(root / "plugin", root / "data", url)
            assert "0.5.2" in json.loads(stable.stdout)["systemMessage"]
            assert "beta.10" not in stable.stdout, "stable channels must ignore prereleases"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ManifestHandler.payload = [
                {"tag_name": "v0.5.3-beta.10", "prerelease": True, "draft": False},
                {"tag_name": "v0.5.3-beta.9", "prerelease": True, "draft": False},
                {"tag_name": "v0.5.4-draft", "prerelease": True, "draft": True},
            ]
            ManifestHandler.etag = '"release-api-beta"'
            write_manifest(root / "plugin", "0.5.3-beta.9")
            beta = run_checker(root / "plugin", root / "data", url)
            assert "0.5.3-beta.10" in json.loads(beta.stdout)["systemMessage"]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ManifestHandler.payload = [
                {"tag_name": "v0.5.3-beta.10", "prerelease": True, "draft": False},
                {"tag_name": "v0.5.3", "prerelease": False, "draft": False},
            ]
            ManifestHandler.etag = '"release-api-beta-to-stable"'
            write_manifest(root / "plugin", "0.5.3-beta.9")
            beta_to_stable = run_checker(root / "plugin", root / "data", url)
            assert "latest `0.5.3`" in json.loads(beta_to_stable.stdout)["systemMessage"]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ManifestHandler.payload = [
                {"tag_name": "v0.5.3-beta.10", "prerelease": True, "draft": False},
                {"tag_name": "v0.5.2", "prerelease": False, "draft": False},
            ]
            ManifestHandler.etag = '"switch-channel"'
            write_manifest(root / "plugin", "0.5.1")
            stable_first = run_checker(root / "plugin", root / "data", url)
            assert "latest `0.5.2`" in json.loads(stable_first.stdout)["systemMessage"]
            write_manifest(root / "plugin", "0.5.3-beta.9")
            before_headers = len(ManifestHandler.if_none_match)
            beta_after_switch = run_checker(root / "plugin", root / "data", url)
            assert "0.5.3-beta.10" in json.loads(beta_after_switch.stdout)["systemMessage"]
            assert ManifestHandler.if_none_match[before_headers] is None, (
                "a changed installed channel must invalidate the old ETag and fetch the full release list"
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ManifestHandler.payload = {"unexpected": "shape"}
            write_manifest(root / "plugin", "0.5.1")
            before = ManifestHandler.requests
            malformed_release = run_checker(root / "plugin", root / "data", url)
            assert malformed_release.stdout == ""
            retry_suppressed = run_checker(root / "plugin", root / "data", url)
            assert retry_suppressed.stdout == ""
            assert ManifestHandler.requests == before + 1, "a failure must back off briefly, not poll again"
            clear_retry(root / "data")
            ManifestHandler.payload = [{"tag_name": "v0.5.2", "prerelease": False, "draft": False}]
            recovered = run_checker(root / "plugin", root / "data", url)
            assert "0.5.2" in json.loads(recovered.stdout)["systemMessage"]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            marketplace = "goldilocks-release"
            codex_home = root / "codex-home"
            cache_root = codex_home / "plugins" / "cache" / marketplace / "goldilocks" / "0.5.1"
            snapshot = codex_home / ".tmp" / "marketplaces" / marketplace / "plugins" / "goldilocks"
            snapshot.mkdir(parents=True)
            write_manifest(cache_root, "0.5.1")
            ManifestHandler.payload = [{"tag_name": "v0.5.2", "prerelease": False, "draft": False}]
            cache_install = run_checker(
                cache_root, root / "data", url, marketplace=marketplace,
                source_path=snapshot, listed_version="0.5.1", codex_home=codex_home,
            )
            assert "0.5.2" in json.loads(cache_install.stdout)["systemMessage"], (
                "Git marketplace snapshots and executing cache paths must align by identity/version"
            )

        ManifestHandler.payload = None
        ManifestHandler.version = "0.3.2"
        ManifestHandler.etag = '"release-032"'

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
            write_manifest(root / "plugin", "0.3.0")
            before = ManifestHandler.requests
            worker = run_checker(root / "plugin", root / "data", url, worker=True)
            assert worker.returncode == 0, worker.stderr
            assert worker.stdout == ""
            assert ManifestHandler.requests == before, "workers must never perform update checks"

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
            ManifestHandler.payload = None
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

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_manifest(root / "plugin", "0.3.0")
            before = ManifestHandler.requests
            local = run_checker(
                root / "plugin",
                root / "data",
                url,
                source_type="local",
            )
            assert local.returncode == 0, local.stderr
            assert local.stdout == ""
            assert ManifestHandler.requests == before, "local development sources must not contact GitHub"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_manifest(root / "plugin", "0.3.0")
            before = ManifestHandler.requests
            unknown = run_checker(
                root / "plugin",
                root / "data",
                url,
                source_type="registry",
            )
            assert unknown.returncode == 0, unknown.stderr
            assert unknown.stdout == ""
            assert ManifestHandler.requests == before, "unknown marketplaces must fail silent"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for index, unsafe_git_source in enumerate(
                (
                    "https://example.invalid/goldilocks.git;rm -rf /",
                    "https://example.invalid/goldilocks.git?ref=other",
                    "https://example.invalid/goldilocks.git#other",
                    "https://example.invalid/goldilocks*.git",
                    "https://example.invalid/(goldilocks).git",
                    "https://example.invalid/[goldilocks].git",
                    "https://example.invalid/goldilocks.git\nnext",
                    "https://example.invalid/goldilócks.git",
                )
            ):
                plugin = root / f"plugin-{index}"
                data = root / f"data-{index}"
                write_manifest(plugin, "0.3.0")
                before = ManifestHandler.requests
                unsafe_source = run_checker(
                    plugin,
                    data,
                    url,
                    git_source=unsafe_git_source,
                )
                assert unsafe_source.returncode == 0, unsafe_source.stderr
                assert unsafe_source.stdout == "", unsafe_git_source
                assert ManifestHandler.requests == before, unsafe_git_source

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ManifestHandler.payload = None
            ManifestHandler.version = "0.3.2"
            ManifestHandler.etag = '"release-032-safe-source"'
            for index, git_source in enumerate(
                (
                    "ssh://git@github.com/blackstone2333/goldilocks.git",
                    "git@github.com:blackstone2333/goldilocks.git",
                )
            ):
                plugin = root / f"plugin-{index}"
                write_manifest(plugin, "0.3.0")
                valid_source = run_checker(plugin, root / f"data-{index}", url, git_source=git_source)
                assert valid_source.returncode == 0, valid_source.stderr
                assert git_source in json.loads(valid_source.stdout)["systemMessage"]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_manifest(root / "plugin", "0.3.0")
            before = ManifestHandler.requests
            unsafe_selector = run_checker(
                root / "plugin",
                root / "data",
                url,
                marketplace="goldilocks-release;echo unsafe",
            )
            assert unsafe_selector.returncode == 0, unsafe_selector.stderr
            assert unsafe_selector.stdout == ""
            assert ManifestHandler.requests == before, "unsafe selectors must fail silent"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_manifest(root / "plugin", "0.3.0")
            before = ManifestHandler.requests
            unaligned = run_checker(
                root / "plugin",
                root / "data",
                url,
                aligned=False,
            )
            assert unaligned.returncode == 0, unaligned.stderr
            assert unaligned.stdout == ""
            assert ManifestHandler.requests == before, "mismatched plugin roots must fail silent"

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            plugin_root = root / "plugin"
            data_dir = root / "data"
            write_manifest(plugin_root, "0.5.3-beta.5")
            data_dir.mkdir()
            connection = checker.connect_state(data_dir)
            try:
                connection.execute(
                    "UPDATE update_state SET latest_version = ?, notified_version = ? WHERE singleton = 1",
                    ("0.5.3-beta.8", "0.5.3-beta.8"),
                )
                connection.commit()
            finally:
                connection.close()
            first = run_reminder(plugin_root, data_dir)
            second = run_reminder(plugin_root, data_dir, turn_id="turn-2")
            assert first.returncode == 0 and second.returncode == 0
            assert "⚠️ **Goldilocks 可更新：Beta5 → Beta8**" in first.stdout
            assert "回复“更新”即可升级；当前任务仍使用 Beta5。" in first.stdout
            assert first.stdout == second.stdout, "notified_version must not suppress later task reminders"
            assert "⚠️ **Goldilocks update available: Beta5 → Beta8**" in (
                run_reminder(plugin_root, data_dir, language="en").stdout
            )
            write_manifest(plugin_root, "0.5.3-beta.8")
            assert run_reminder(plugin_root, data_dir).stdout == "", "installing the target clears the reminder"

        hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
        commands = [hook for group in hooks for hook in group.get("hooks", [])]
        update_hooks = [hook for hook in commands if "update_checker.py" in hook.get("command", "")]
        assert len(update_hooks) == 1, "SessionStart must register one update checker"
        assert update_hooks[0]["timeout"] <= 4
        assert "Goldilocks" in update_hooks[0]["statusMessage"]
        assert "Updates" in update_hooks[0]["statusMessage"]
        prompt_hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]["UserPromptSubmit"]
        prompt_commands = [hook for group in prompt_hooks for hook in group.get("hooks", [])]
        reminders = [hook for hook in prompt_commands if "update_reminder.py" in hook.get("command", "")]
        assert len(reminders) == 1, "every root prompt must receive the pending-update contract"
        assert reminders[0]["timeout"] <= 3

        checker_source = CHECKER.read_text(encoding="utf-8")
        assert "api.github.com/repos/blackstone2333/goldilocks/releases" in checker_source, (
            "the default check must use GitHub Releases, including published prereleases"
        )
        assert "codex plugin marketplace upgrade" not in checker_source
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    print("Goldilocks update checker contract passed.")


if __name__ == "__main__":
    main()
