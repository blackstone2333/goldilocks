#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
BOOTSTRAP_SKILL = PLUGIN / "skills" / "goldilocks-bootstrap"
BOOTSTRAP = BOOTSTRAP_SKILL / "scripts" / "bootstrap.py"
AGENTS = PLUGIN / "agents"
ASSETS = BOOTSTRAP_SKILL / "assets" / "bootstrap-agents"


def command(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BOOTSTRAP), *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def output(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def make_native_plugin(root: Path) -> Path:
    native = root / "native-plugin"
    (native / "hooks").mkdir(parents=True)
    (native / "hooks" / "hooks.json").write_text("{}\n")
    (native / ".codex-plugin").mkdir()
    (native / ".codex-plugin" / "plugin.json").write_text('{"name":"goldilocks"}\n')
    (native / "skills" / "goldilocks").mkdir(parents=True)
    (native / "skills" / "goldilocks" / "SKILL.md").write_text("# Goldilocks\n")
    (native / "scripts").mkdir()
    (native / "scripts" / "usage_reporter.py").write_text("# usage\n")
    (native / "scripts" / "update_checker.py").write_text("# update\n")
    return native


def fake_codex(root: Path, native: Path, *, fail_marketplace: bool = False) -> dict[str, str]:
    bin_dir = root / "bin"
    bin_dir.mkdir()
    marker, log = root / "installed", root / "codex.log"
    executable = bin_dir / "codex"
    executable.write_text(
        "#!/bin/sh\n"
        f"printf '%s\\n' \"$*\" >> '{log}'\n"
        "if [ \"$1 $2 $3\" = \"plugin list --json\" ]; then\n"
        f"  if [ -f '{marker}' ]; then printf '%s\\n' '{{\"installed\":[{{\"name\":\"goldilocks\",\"enabled\":true,\"source\":{{\"path\":\"{native}\"}}}}]}}'; else printf '%s\\n' '{{\"installed\":[]}}'; fi\n"
        "  exit 0\n"
        "fi\n"
        + ("if [ \"$1 $2 $3\" = \"plugin marketplace add\" ]; then exit 7; fi\n" if fail_marketplace else "")
        + "if [ \"$1 $2 $3\" = \"plugin add goldilocks@goldilocks-local\" ]; then : > '"
        + str(marker)
        + "'; fi\nexit 0\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    environment = os.environ.copy()
    environment["PATH"] = str(bin_dir)
    return environment


def main() -> None:
    for template in sorted(AGENTS.glob("*.toml")):
        assert template.read_bytes() == (ASSETS / template.name).read_bytes(), template.name
    terra = (AGENTS / "goldilocks-terra-engineer.toml").read_text(encoding="utf-8")
    assert "Spark XHigh is the deterministic coding Fast specialist" in terra
    assert "Luna Max is the Economy Fast" in terra
    assert "Luna is the general Fast baseline" not in terra

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        target, state = root / "agents", root / "state"
        native = make_native_plugin(root)
        trusted_environment = os.environ.copy()
        trusted_environment["PLUGIN_ROOT"] = str(native)
        trusted_environment["CODEX_HOME"] = str(root / "codex-home")
        plan = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), env=trusted_environment,
            )
        )
        assert plan["status"] == "planned"
        assert plan["approval_required"] is True
        assert set(plan["agents"].values()) == {"missing"}
        assert plan["experience"] == "full"
        assert plan["preferred_experience"] == "native_plugin"
        assert plan["portable_skills_role"] == "fallback"
        assert plan["portable_cleanup"]["status"] == "not-needed"
        trust = plan["hook_trust_handoff"]
        assert trust["status"] == "host-review-required"
        assert trust["selection_required"] is True
        assert "choose exactly one" in trust["confirmation"]
        assert trust["fallback"] == "/hooks" and trust["executed_by_bootstrap"] is False
        assert trust["choices"] == [
            {
                "id": "persistent_goldilocks", "label": "Persist Goldilocks trust", "recommended": True,
                "action": "In Codex's startup hook-review UI, select Trust all and continue.",
                "scope": "current Goldilocks hooks definition only",
                "persistence": "persistent until the hooks definition changes",
            },
            {
                "id": "bypass_once_all_hooks", "label": "Bypass all hooks once", "recommended": False,
                "next_launch_command": ["codex", "--dangerously-bypass-hook-trust"],
                "scope": "all enabled hooks", "persistence": "single invocation",
            },
            {"id": "skip", "label": "Skip Hook trust", "recommended": False, "scope": "no Hook trust change", "persistence": "none"},
        ]
        assert not target.exists() and not state.exists(), "plan must be zero-write"

        no_approval = command(
            "--apply", "--json", "--host", "codex", "--target-dir", str(target),
            "--state-dir", str(state), env=trusted_environment,
        )
        assert no_approval.returncode != 0 and not target.exists() and not state.exists()

        applied = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), env=trusted_environment,
            )
        )
        assert applied["status"] == "installed" and len(applied["installed"]) == 4
        assert output(
            command(
                "--check", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), env=trusted_environment,
            )
        )["status"] == "current"
        repeat = output(
            command(
                "--apply", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), env=trusted_environment,
            )
        )
        assert repeat["status"] == "current" and not repeat["installed"]
        assert output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), env=trusted_environment,
            )
        )["approval_required"] is False

        legacy = root / "legacy"
        legacy.mkdir()
        for name in ("goldilocks-terra-engineer.toml", "goldilocks-sol-reviewer.toml"):
            old = subprocess.run(
                ["git", "show", f"v0.5.0-alpha.2:plugins/goldilocks/agents/{name}"],
                cwd=ROOT,
                capture_output=True,
                check=True,
            ).stdout
            (legacy / name).write_bytes(old)
        migrated = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(legacy),
                "--state-dir", str(state), env=trusted_environment,
            )
        )
        assert set(migrated["migrated"]) == {
            "goldilocks-terra-engineer.toml", "goldilocks-sol-reviewer.toml"
        }

        manual = root / "manual"
        manual.mkdir()
        for template in ASSETS.glob("*.toml"):
            (manual / template.name).write_bytes(template.read_bytes())
        unapproved_check = command(
            "--check", "--json", "--host", "codex", "--target-dir", str(manual),
            "--state-dir", str(state), env=trusted_environment,
        )
        assert unapproved_check.returncode != 0 and "not globally approved" in unapproved_check.stderr

        conflict = root / "conflict"
        conflict.mkdir()
        (conflict / "goldilocks-terra-engineer.toml").write_text("user-owned = true\n")
        refused = command(
            "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(conflict),
            "--state-dir", str(state), env=trusted_environment,
        )
        assert refused.returncode != 0 and "refusing to overwrite" in refused.stderr
        assert len(list(conflict.iterdir())) == 1

        unsupported_target, unsupported_state = root / "claude-agents", root / "claude-state"
        unsupported = output(
            command(
                "--apply", "--yes", "--json", "--host", "claude", "--target-dir", str(unsupported_target),
                "--state-dir", str(unsupported_state),
            )
        )
        assert unsupported["status"] == "skipped"
        assert unsupported["approval_required"] is False
        assert unsupported["preferred_experience"] == "portable_skills"
        assert unsupported["portable_skills_role"] == "preferred"
        assert unsupported["hook_trust_handoff"]["status"] == "skipped"
        assert not unsupported_target.exists() and not unsupported_state.exists()
        unknown = output(command("--plan", "--json", "--host", "unknown"))
        assert unknown["capabilities"]["agent_templates"] == "unsupported"

        reused = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(root / "reuse"),
                "--state-dir", str(state), "--native-plugin-dir", str(native), env=trusted_environment,
            )
        )
        assert reused["native_plugin"] == "detected"
        assert reused["hooks_review"] == "required"
        assert reused["capabilities"]["usage"] == "reused"
        assert reused["capabilities"]["update"] == "reused"

        loose_hooks = root / "loose-hooks"
        (loose_hooks / "hooks").mkdir(parents=True)
        (loose_hooks / "hooks" / "hooks.json").write_text("{}\n")
        not_plugin = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(root / "loose"),
                "--state-dir", str(state), "--native-plugin-dir", str(loose_hooks),
            )
        )
        assert not_plugin["native_plugin"] == "absent"
        assert not_plugin["capabilities"]["hooks"] == "unsupported"

        incomplete = root / "incomplete-plugin"
        (incomplete / ".codex-plugin").mkdir(parents=True)
        (incomplete / ".codex-plugin" / "plugin.json").write_text('{"name":"goldilocks"}\n')
        repair = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(root / "repair"),
                "--state-dir", str(state), "--native-plugin-dir", str(incomplete),
            )
        )
        assert repair["experience"] == "partial"
        assert repair["plugin_repair"] == "handoff-required"
        assert repair["plugin_actions"]
        assert repair["native_components"] == {
            "core_skill": False, "hooks": False, "usage": False, "update": False
        }

        fake_bin = root / "bin"
        fake_bin.mkdir()
        fake = fake_bin / "codex"
        fake.write_text(
            "#!/bin/sh\nprintf '%s\\n' '{\"installed\":[{\"name\":\"goldilocks\",\"enabled\":true,\"source\":{\"path\":\"'"
            + str(native)
            + "'\"}}]}'\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
        environment = os.environ.copy()
        environment["PATH"] = str(fake_bin)
        probe = """
import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('bootstrap', sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.SKILL_DIR = Path(sys.argv[2])
print(module.discover_native_plugin('codex') or '')
"""
        discovered = subprocess.run(
            [sys.executable, "-c", probe, str(BOOTSTRAP), str(root / "portable-skill")],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        assert discovered.returncode == 0 and discovered.stdout.strip() == str(native)
        default_environment = environment.copy()
        for key in ("GOLDILOCKS_BOOTSTRAP_HOST", "CODEX_HOME", "CODEX_THREAD_ID", "CLAUDE_CODE", "CLAUDECODE", "PLUGIN_ROOT"):
            default_environment.pop(key, None)
        default_unknown = output(
            command(
                "--plan", "--json", "--target-dir", str(root / "default"),
                "--state-dir", str(state), env=default_environment,
            )
        )
        assert default_unknown["host"] == "unknown"
        shared_home = root / "shared-home"
        shared_skill = shared_home / ".agents" / "skills" / "goldilocks-bootstrap"
        shared_skill.parent.mkdir(parents=True)
        shared_skill.symlink_to(BOOTSTRAP_SKILL, target_is_directory=True)
        codex_mapping = shared_home / ".codex" / "skills" / "goldilocks-bootstrap"
        codex_mapping.parent.mkdir(parents=True)
        codex_mapping.symlink_to(shared_skill, target_is_directory=True)
        mapped_environment = default_environment.copy()
        mapped_environment["HOME"] = str(shared_home)
        mapped = output(
            command(
                "--plan", "--json", "--target-dir", str(root / "mapped"),
                "--state-dir", str(state), env=mapped_environment,
            )
        )
        assert mapped["host"] == "codex"
        default_environment["CODEX_THREAD_ID"] = "thread-evidence"
        default_detected = output(
            command(
                "--plan", "--json", "--target-dir", str(root / "default-codex"),
                "--state-dir", str(state), env=default_environment,
            )
        )
        assert default_detected["host"] == "codex"
        assert default_detected["native_plugin"] == "detected"
        fake.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        absent = subprocess.run(
            [sys.executable, "-c", probe, str(BOOTSTRAP), str(root / "portable-skill")],
            text=True,
            capture_output=True,
            check=False,
            env=environment,
        )
        assert absent.returncode == 0 and absent.stdout.strip() == ""

    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        native = make_native_plugin(root)
        loose = root / "portable-only"
        loose.mkdir()
        environment = fake_codex(root, native)
        environment["CODEX_HOME"] = str(root / "codex-home")
        for name in ("goldilocks", "goldilocks-bootstrap"):
            (Path(environment["CODEX_HOME"]) / "skills" / name).mkdir(parents=True)
        target, state = root / "agents", root / "state"
        partial_plan = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), "--native-plugin-dir", str(loose), env=environment,
            )
        )
        assert partial_plan["experience"] == "partial"
        assert partial_plan["native_plugin"] == "absent"
        assert partial_plan["hook_trust_handoff"]["status"] == "skipped"
        assert partial_plan["plugin_actions"] == [
            ["codex", "plugin", "marketplace", "add", "blackstone2333/goldilocks", "--ref", "v0.5.0", "--json"],
            ["codex", "plugin", "add", "goldilocks@goldilocks-local", "--json"],
        ]
        assert partial_plan["portable_cleanup"]["executed_by_bootstrap"] is False
        assert partial_plan["portable_cleanup"]["commands"] == [
            ["npx", "skills", "remove", "--global", "--agent", "codex", "--skill", "goldilocks", "--yes"],
            ["npx", "skills", "remove", "--global", "--agent", "codex", "--skill", "goldilocks-bootstrap", "--yes"],
        ]
        first_refusal = command(
            "--apply", "--json", "--host", "codex", "--target-dir", str(target),
            "--state-dir", str(state), "--native-plugin-dir", str(loose), env=environment,
        )
        assert first_refusal.returncode != 0 and not (root / "codex.log").exists()
        upgraded = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), "--native-plugin-dir", str(loose), env=environment,
            )
        )
        assert upgraded["experience"] == "full" and upgraded["status"] == "installed"
        assert [row["command"] for row in upgraded["plugin_action_results"]] == partial_plan["plugin_actions"]
        calls = (root / "codex.log").read_text(encoding="utf-8")
        assert "plugin marketplace add blackstone2333/goldilocks --ref v0.5.0 --json" in calls
        assert "plugin add goldilocks@goldilocks-local --json" in calls
        assert "npx" not in calls
        assert output(
            command(
                "--check", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), "--native-plugin-dir", str(native), env=environment,
            )
        )["experience"] == "full"

        failed_root = root / "failed"
        failed_native = make_native_plugin(failed_root)
        failed_loose = failed_root / "portable-only"
        failed_loose.mkdir()
        failing_environment = fake_codex(failed_root, failed_native, fail_marketplace=True)
        failed = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(failed_root / "agents"),
                "--state-dir", str(failed_root / "state"), "--native-plugin-dir", str(failed_loose), env=failing_environment,
            )
        )
        assert failed["status"] == "partial" and "plugin command failed" in failed["plugin_error"]
        assert len(list((failed_root / "agents").glob("*.toml"))) == 4
        assert "npx" not in (failed_root / "codex.log").read_text(encoding="utf-8")
        partial_check = command(
            "--check", "--json", "--host", "codex", "--target-dir", str(failed_root / "agents"),
            "--state-dir", str(failed_root / "state"), "--native-plugin-dir", str(failed_loose), env=failing_environment,
        )
        assert partial_check.returncode != 0 and "portable/partial" in partial_check.stderr

        before_unknown = (root / "codex.log").read_text(encoding="utf-8")
        unknown = output(command("--apply", "--json", "--host", "unknown", env=environment))
        assert unknown["status"] == "skipped"
        assert (root / "codex.log").read_text(encoding="utf-8") == before_unknown

    print("Goldilocks portable Bootstrap contract passed.")


if __name__ == "__main__":
    main()
