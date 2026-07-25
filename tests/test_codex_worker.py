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
    *extra: str,
    task_name: str = "fast__focused_implementation",
    fake_exit: int = 0,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GOLDILOCKS_CODEX_BIN": str(fake_codex),
            "GOLDILOCKS_PROBE_FILE": str(probe),
            "GOLDILOCKS_FAKE_EXIT": str(fake_exit),
        }
    )
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


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
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

        result = run_dispatcher(worktree, contract, fake_codex, probe)
        assert result.returncode == 0, result.stderr
        assert "FAKE_SPARK_OK" in result.stdout
        invocation = json.loads(probe.read_text(encoding="utf-8"))
        argv = invocation["argv"]
        assert argv[0] == "exec"
        assert ["-m", SPARK_MODEL] == argv[argv.index("-m") : argv.index("-m") + 2]
        assert ["--sandbox", "workspace-write"] == argv[
            argv.index("--sandbox") : argv.index("--sandbox") + 2
        ]
        assert "--disable" in argv and "plugins" in argv
        assert "agents.enabled=false" in argv
        assert "mcp_servers={}" in argv
        assert 'model_reasoning_effort="medium"' in argv
        assert argv[-1] == "-", "the contract must travel over stdin, not shell interpolation"
        assert Path(invocation["cwd"]).samefile(worktree)
        prompt = invocation["stdin"]
        assert "Fast worker" in prompt
        assert "leaf executor" in prompt
        assert "Do not delegate" in prompt
        assert "Do not broaden scope" in prompt
        assert "fast__focused_implementation" in prompt
        assert "Implement the bounded parser change" in prompt
        assert "changed files" in prompt and "checks" in prompt

        custom_result = root / "last-message.txt"
        probe.unlink()
        tuned = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            probe,
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
        )
        assert empty_result.returncode == 2
        assert "empty" in empty_result.stderr.lower()

        failed = run_dispatcher(
            worktree,
            contract,
            fake_codex,
            root / "failed-probe.json",
            fake_exit=7,
        )
        assert failed.returncode == 7, "worker failures must propagate without silent fallback"

    print("Goldilocks external Codex Fast worker contract passed.")


if __name__ == "__main__":
    main()
