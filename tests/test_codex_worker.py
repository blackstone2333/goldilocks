#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DISPATCHER = (
    ROOT
    / "plugins"
    / "goldilocks"
    / "skills"
    / "goldilocks"
    / "scripts"
    / "dispatch_codex_worker.py"
)
SPARK_MODEL = "gpt-5.3-codex-spark"
LUNA_MODEL = "gpt-5.6-luna"


def write_fake_codex(path: Path) -> None:
    path.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path

Path(os.environ["GOLDILOCKS_PROBE_FILE"]).write_text(
    json.dumps(
        {
            "argv": sys.argv[1:],
            "cwd": os.getcwd(),
            "stdin": sys.stdin.read(),
            "home": os.environ.get("HOME"),
            "codex_home": os.environ.get("CODEX_HOME"),
            "goldilocks_worker": os.environ.get("GOLDILOCKS_WORKER"),
            "config": (Path(os.environ["CODEX_HOME"]) / "config.toml").read_text(
                encoding="utf-8"
            ),
            "auth": (Path(os.environ["CODEX_HOME"]) / "auth.json").read_text(
                encoding="utf-8"
            ),
            "models": (Path(os.environ["CODEX_HOME"]) / "models_cache.json").read_text(
                encoding="utf-8"
            ),
            "runtime_cache_exists": (
                Path(os.environ["HOME"]) / ".cache" / "codex-runtimes"
            ).exists(),
        }
    ),
    encoding="utf-8",
)
print("FAKE_SPARK_OK")
raise SystemExit(int(os.environ.get("GOLDILOCKS_FAKE_EXIT", "0")))
""",
        encoding="utf-8",
    )
    path.chmod(0o755)


def run_dispatcher(
    worktree: Path,
    contract: Path,
    fake_codex: Path,
    probe: Path,
    source_home: Path,
    *extra: str,
    task_name: str = "fast__focused_implementation",
    fake_exit: int = 0,
    events_dir: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GOLDILOCKS_CODEX_BIN": str(fake_codex),
            "GOLDILOCKS_PROBE_FILE": str(probe),
            "GOLDILOCKS_FAKE_EXIT": str(fake_exit),
            "HOME": str(source_home),
            "CODEX_HOME": str(source_home / ".codex"),
        }
    )
    if events_dir is not None:
        env["GOLDILOCKS_WORKER_EVENTS_DIR"] = str(events_dir)
    return subprocess.run(
        [
            sys.executable,
            str(DISPATCHER),
            "--workdir",
            str(worktree),
            "--task-name",
            task_name,
            "--task-file",
            str(contract),
            *extra,
        ],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def write_source_home(path: Path) -> None:
    codex_home = path / ".codex"
    codex_home.mkdir(parents=True)
    (path / ".cache" / "codex-runtimes").mkdir(parents=True)
    (codex_home / "auth.json").write_text('{"token":"fake"}\n', encoding="utf-8")
    (codex_home / "models_cache.json").write_text(
        '{"models":[{"slug":"gpt-5.3-codex-spark"}]}\n', encoding="utf-8"
    )
    (codex_home / "config.toml").write_text(
        '''model_provider = "custom"
disable_response_storage = true
service_tier = "priority"
unrelated_top_level = "drop-me"

[model_providers.custom]
name = "Custom Provider"
base_url = "https://example.invalid/v1"
env_key = "TEST_API_KEY"

[mcp_servers.should_not_leak]
command = "unsafe-global-tool"

[features]
hooks = true
''',
        encoding="utf-8",
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        source_home = root / "user-home"
        write_source_home(source_home)
        worktree = root / "worker"
        worktree.mkdir()
        contract = root / "contract.md"
        contract.write_text(
            """# Objective
Implement the bounded parser change.

# Allowed scope
- parser.py
- tests/test_parser.py

# Acceptance
- Run the focused parser test.
""",
            encoding="utf-8",
        )
        fake_codex = root / "codex"
        write_fake_codex(fake_codex)
        probe = root / "probe.json"

        result = run_dispatcher(worktree, contract, fake_codex, probe, source_home)
        assert result.returncode == 0, result.stderr
        assert "FAKE_SPARK_OK" in result.stdout
        invocation = json.loads(probe.read_text(encoding="utf-8"))
        argv = invocation["argv"]
        assert argv[0] == "exec"
        assert ["-m", SPARK_MODEL] == argv[argv.index("-m") : argv.index("-m") + 2]
        assert ["--sandbox", "workspace-write"] == argv[
            argv.index("--sandbox") : argv.index("--sandbox") + 2
        ]
        assert "agents.enabled=false" not in argv
        assert ["--disable", "multi_agent"] == argv[
            argv.index("--disable") : argv.index("--disable") + 2
        ]
        assert "plugins" not in argv
        assert "apps" not in argv
        assert "mcp_servers={}" not in argv
        for phrase in (
            "Defects add",
            "evidence-backed CAUSE",
            "explicitly unknown",
            "fix and verification",
            "expand when asked",
        ):
            assert phrase in invocation["stdin"]
        assert 'model_reasoning_effort="medium"' in argv
        assert argv[-1] == "-", "the contract must travel over stdin, not shell interpolation"
        assert Path(invocation["cwd"]).samefile(worktree)
        assert Path(invocation["home"]) != source_home
        assert Path(invocation["codex_home"]) != source_home / ".codex"
        assert invocation["goldilocks_worker"] == "1"
        assert invocation["auth"] == '{"token":"fake"}\n'
        assert "gpt-5.3-codex-spark" in invocation["models"]
        assert invocation["runtime_cache_exists"] is True
        minimal_config = invocation["config"]
        assert 'model_provider = "custom"' in minimal_config
        assert "[model_providers.custom]" in minimal_config
        assert "disable_response_storage = true" in minimal_config
        assert 'service_tier = "priority"' in minimal_config
        assert "unrelated_top_level" not in minimal_config
        assert "mcp_servers" not in minimal_config
        assert "[features]" not in minimal_config
        assert "--ignore-rules" not in argv, "project profile must preserve repository rules"
        prompt = invocation["stdin"]
        assert "Goldilocks Fast leaf" in prompt
        assert "Do not delegate" in prompt
        assert "Do not delegate, reroute, broaden scope" in prompt
        assert "fast__focused_implementation" in prompt
        assert "Implement the bounded parser change" in prompt
        assert "changed files" in prompt and "checks" in prompt
        assert "Do not rerun Goldilocks routing" in prompt
        assert "one coherent batch" in prompt
        worker_header = prompt.split("--- execution contract ---", 1)[0]
        assert len(worker_header.split()) <= 125, "leaf briefing must stay context-lean"
        assert "company-style" not in worker_header
        assert "report changed files" in worker_header.lower()

        probe.unlink()
        events_dir = root / "worker-events"
        captured = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            probe,
            source_home,
            events_dir=events_dir,
        )
        assert captured.returncode == 0, captured.stderr
        assert "FAKE_SPARK_OK" not in captured.stdout
        summary = json.loads(captured.stdout.strip())
        assert summary["model"] == SPARK_MODEL
        event_path = Path(summary["events"])
        assert event_path.parent.samefile(events_dir)
        assert event_path.read_text(encoding="utf-8").strip() == "FAKE_SPARK_OK"
        captured_argv = json.loads(probe.read_text(encoding="utf-8"))["argv"]
        assert "--json" in captured_argv

        probe.unlink()
        general = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            probe,
            source_home,
            "--work-type",
            "general",
        )
        assert general.returncode == 0, general.stderr
        general_argv = json.loads(probe.read_text(encoding="utf-8"))["argv"]
        assert ["-m", LUNA_MODEL] == general_argv[
            general_argv.index("-m") : general_argv.index("-m") + 2
        ]

        probe.unlink()
        minimal = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            probe,
            source_home,
            "--capabilities",
            "minimal",
        )
        assert minimal.returncode == 0, minimal.stderr
        minimal_invocation = json.loads(probe.read_text(encoding="utf-8"))
        assert "--ignore-rules" in minimal_invocation["argv"]
        assert Path(minimal_invocation["codex_home"]) != source_home / ".codex"

        probe.unlink()
        inherited = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            probe,
            source_home,
            "--capabilities",
            "inherit",
        )
        assert inherited.returncode == 0, inherited.stderr
        inherited_invocation = json.loads(probe.read_text(encoding="utf-8"))
        assert Path(inherited_invocation["home"]) == source_home
        assert Path(inherited_invocation["codex_home"]) == source_home / ".codex"
        assert inherited_invocation["goldilocks_worker"] == "1"
        assert "mcp_servers.should_not_leak" in inherited_invocation["config"]
        assert "--ignore-rules" not in inherited_invocation["argv"]

        custom_result = root / "last-message.txt"
        probe.unlink()
        tuned = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            probe,
            source_home,
            "--reasoning-effort",
            "low",
            "--sandbox",
            "read-only",
            "--result-file",
            str(custom_result),
        )
        assert tuned.returncode == 0, tuned.stderr
        tuned_argv = json.loads(probe.read_text(encoding="utf-8"))["argv"]
        assert 'model_reasoning_effort="low"' in tuned_argv
        assert ["--sandbox", "read-only"] == tuned_argv[
            tuned_argv.index("--sandbox") : tuned_argv.index("--sandbox") + 2
        ]
        assert ["--output-last-message", str(custom_result.resolve())] == tuned_argv[
            tuned_argv.index("--output-last-message") : tuned_argv.index("--output-last-message") + 2
        ]

        invalid = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            root / "invalid-probe.json",
            source_home,
            task_name="standard__wrong_channel",
        )
        assert invalid.returncode == 2
        assert "fast__" in invalid.stderr

        empty = root / "empty.md"
        empty.write_text("\n", encoding="utf-8")
        empty_result = run_dispatcher(
            worktree,
            empty,
            fake_codex,
            root / "empty-probe.json",
            source_home,
        )
        assert empty_result.returncode == 2
        assert "empty" in empty_result.stderr.lower()

        failed = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            root / "failed-probe.json",
            source_home,
            fake_exit=7,
        )
        assert failed.returncode == 7, "worker failures must propagate without silent fallback"

    print("Goldilocks external Codex Fast worker contract passed.")


if __name__ == "__main__":
    main()
