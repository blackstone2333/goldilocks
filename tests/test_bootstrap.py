#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
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


def bootstrap_module():
    spec = importlib.util.spec_from_file_location("goldilocks_bootstrap_test", BOOTSTRAP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        assert plan["usage_visibility"]["mode"] == "on-demand"
        assert plan["usage_visibility"]["source"] == "default"
        assert plan["usage_visibility"]["choices"][0]["id"] == "on-demand"
        assert plan["approval_required"] is True
        assert set(plan["agents"].values()) == {"missing"}
        # Regression: byte-identical templates alone must never be reported as a
        # complete native role installation.  The temporary CODEX_HOME has no
        # config.toml declarations at this point.
        assert set(plan["registrations"].values()) == {"missing"}
        assert plan["experience"] == "partial"
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

        # The original defect: an installation with all four copied templates but
        # no [agents.*] declarations was previously indistinguishable from a full
        # native setup.  Keep this test before the successful apply below.
        template_only = root / "template-only-agents"
        template_only.mkdir()
        for template in ASSETS.glob("*.toml"):
            (template_only / template.name).write_bytes(template.read_bytes())
        template_only_plan = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(template_only),
                "--config-file", str(root / "template-only-config.toml"),
                "--state-dir", str(root / "template-only-state"), env=trusted_environment,
            )
        )
        assert set(template_only_plan["agents"].values()) == {"current"}
        assert set(template_only_plan["registrations"].values()) == {"missing"}
        assert template_only_plan["experience"] == "partial"
        template_only_check = command(
            "--check", "--json", "--host", "codex", "--target-dir", str(template_only),
            "--config-file", str(root / "template-only-config.toml"),
            "--state-dir", str(root / "template-only-state"), env=trusted_environment,
        )
        assert template_only_check.returncode != 0 and "roles are not registered" in template_only_check.stderr
        template_only_applied = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(template_only),
                "--config-file", str(root / "template-only-config.toml"),
                "--state-dir", str(root / "template-only-state"), env=trusted_environment,
            )
        )
        assert template_only_applied["status"] == "installed"
        assert not template_only_applied["installed"] and len(template_only_applied["registered"]) == 4
        assert template_only_applied["experience"] == "full"
        assert set(template_only_applied["registrations"].values()) == {"current"}

        applied = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), env=trusted_environment,
            )
        )
        assert applied["status"] == "installed" and len(applied["installed"]) == 4
        assert applied["experience"] == "full"
        assert set(applied["registrations"].values()) == {"current"}
        assert set(applied["registered"]) == {
            "goldilocks_spark_worker", "goldilocks_luna_economy",
            "goldilocks_terra_engineer", "goldilocks_sol_reviewer",
        }
        config = root / "config.toml"
        config_text = config.read_text(encoding="utf-8")
        assert "[agents.goldilocks_spark_worker]" in config_text
        assert 'config_file = "agents/goldilocks-spark-worker.toml"' in config_text
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
        assert not repeat["registered"]
        assert output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), env=trusted_environment,
            )
        )["approval_required"] is False

        automatic = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), "--usage-visibility", "automatic", env=trusted_environment,
            )
        )
        assert automatic["usage_visibility"]["mode"] == "automatic"
        automatic_applied = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), "--usage-visibility", "automatic", env=trusted_environment,
            )
        )
        assert automatic_applied["usage_visibility"]["mode"] == "automatic"
        assert json.loads((state / "usage-visibility.json").read_text()) == {"mode": "automatic"}
        assert output(
            command(
                "--check", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), "--usage-visibility", "automatic", env=trusted_environment,
            )
        )["status"] == "current"
        # A requested mode is a check target, not evidence that it is active.
        (state / "usage-visibility.json").unlink()
        absent_preference = command(
            "--check", "--json", "--host", "codex", "--target-dir", str(target),
            "--state-dir", str(state), "--usage-visibility", "automatic", env=trusted_environment,
        )
        assert absent_preference.returncode != 0 and "active on-demand (default)" in absent_preference.stderr
        default_visibility = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), env=trusted_environment,
            )
        )["usage_visibility"]
        assert default_visibility["mode"] == "on-demand" and default_visibility["source"] == "default"
        (state / "usage-visibility.json").write_text("{not json}\n", encoding="utf-8")
        corrupt_preference = command(
            "--check", "--json", "--host", "codex", "--target-dir", str(target),
            "--state-dir", str(state), "--usage-visibility", "automatic", env=trusted_environment,
        )
        assert corrupt_preference.returncode != 0 and "active on-demand (default)" in corrupt_preference.stderr
        environment_automatic = trusted_environment.copy()
        environment_automatic["GOLDILOCKS_USAGE_VISIBILITY"] = "automatic"
        assert output(
            command(
                "--check", "--json", "--host", "codex", "--target-dir", str(target),
                "--state-dir", str(state), "--usage-visibility", "automatic", env=environment_automatic,
            )
        )["usage_visibility"]["source"] == "environment"
        overridden_request = command(
            "--check", "--json", "--host", "codex", "--target-dir", str(target),
            "--state-dir", str(state), "--usage-visibility", "on-demand", env=environment_automatic,
        )
        assert overridden_request.returncode != 0 and "active automatic (environment)" in overridden_request.stderr

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
                "--config-file", str(root / "legacy-config.toml"), "--state-dir", str(state), env=trusted_environment,
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
        assert unapproved_check.returncode != 0 and "roles are not registered" in unapproved_check.stderr

        # Registration appends only missing owned tables.  Comments and unrelated
        # host settings survive byte-for-byte before the appended block.
        preserved_target = root / "preserved-agents"
        preserved_config = root / "preserved-config.toml"
        original_config = "# user comment\n[features.multi_agent_v2]\nenabled = true\ncustom_value = 7\n"
        preserved_config.write_text(original_config, encoding="utf-8")
        preserved = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(preserved_target),
                "--config-file", str(preserved_config), "--state-dir", str(root / "preserved-state"),
                env=trusted_environment,
            )
        )
        assert len(preserved["registered"]) == 4
        preserved_text = preserved_config.read_text(encoding="utf-8")
        assert preserved_text.startswith(original_config)
        assert output(
            command(
                "--check", "--json", "--host", "codex", "--target-dir", str(preserved_target),
                "--config-file", str(preserved_config), "--state-dir", str(root / "preserved-state"),
                env=trusted_environment,
            )
        )["experience"] == "full"

        # A normal user configuration may repeat an array-of-tables header.
        # That is valid TOML, not a duplicate table declaration.  Bootstrap must
        # preserve it byte-for-byte, recognize its four own registrations, and
        # behave the same through Python 3.9's bundled Tomli fallback.
        array_target, array_config = root / "array-agents", root / "array-config.toml"
        array_config_text = (
            'model = "gpt-5.6-sol"\n'
            "[features.multi_agent_v2]\n"
            "enabled = true\n\n"
            "[[skills.config]]\n"
            'name = "first-user-skill"\n'
            'enabled = true\n\n'
            'agents = ["x"]\n'
            "[skills.config.options]\n"
            'scope = "first"\n\n'
            "[[skills.config]]\n"
            'name = "second-user-skill"\n'
            'enabled = false\n'
            'agents = ["y"]\n'
            "[skills.config.options]\n"
            'scope = "second"\n\n'
        )
        declarations = bootstrap_module().role_declarations(array_target, array_config)
        for role, fields in declarations.items():
            array_config_text += (
                f"[agents.{role}]\n"
                f"description = {json.dumps(fields['description'])}\n"
                f"config_file = {json.dumps(fields['config_file'])}\n"
            )
        array_config.write_text(array_config_text, encoding="utf-8")
        for force_fallback in (False, True):
            array_module = bootstrap_module()
            saved_tomllib = array_module.tomllib
            if force_fallback:
                array_module.tomllib = None
            try:
                decoded, preserved_raw = array_module.read_config(array_config)
                states, _ = array_module.classify_registration_data(array_target, array_config, decoded)
                assert preserved_raw == array_config_text
                assert len(decoded["skills"]["config"]) == 2
                assert [entry["options"]["scope"] for entry in decoded["skills"]["config"]] == ["first", "second"]
                assert [entry["agents"] for entry in decoded["skills"]["config"]] == [["x"], ["y"]]
                assert set(states.values()) == {"current"}
            finally:
                array_module.tomllib = saved_tomllib
        array_plan = output(
            command(
                "--plan", "--json", "--host", "codex", "--target-dir", str(array_target),
                "--config-file", str(array_config), "--state-dir", str(root / "array-state"),
                env=trusted_environment,
            )
        )
        assert set(array_plan["registrations"].values()) == {"current"}

        # The same legal repeated array form must not interfere with bounded
        # append: retain all user TOML and add only missing owned role tables.
        bounded_target, bounded_config = root / "bounded-agents", root / "bounded-config.toml"
        one_role = "goldilocks_spark_worker"
        bounded_declarations = bootstrap_module().role_declarations(bounded_target, bounded_config)
        bounded_config_text = array_config_text.split(f"[agents.{one_role}]", 1)[0]
        bounded_config_text += (
            f"[agents.{one_role}]\n"
            f"description = {json.dumps(bounded_declarations[one_role]['description'])}\n"
            f"config_file = {json.dumps(bounded_declarations[one_role]['config_file'])}\n"
        )
        bounded_config.write_text(bounded_config_text, encoding="utf-8")
        bounded = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(bounded_target),
                "--config-file", str(bounded_config), "--state-dir", str(root / "bounded-state"),
                env=trusted_environment,
            )
        )
        assert set(bounded["registered"]) == {
            "goldilocks_luna_economy", "goldilocks_terra_engineer", "goldilocks_sol_reviewer",
        }
        bounded_text = bounded_config.read_text(encoding="utf-8")
        assert bounded_text.startswith(bounded_config_text)
        assert bounded_text.count("[[skills.config]]") == 2
        assert output(
            command(
                "--check", "--json", "--host", "codex", "--target-dir", str(bounded_target),
                "--config-file", str(bounded_config), "--state-dir", str(root / "bounded-state"),
                env=trusted_environment,
            )
        )["status"] == "current"

        # General TOML structure is owned by the actual decoder, so repeated
        # ordinary tables still fail closed without depending on scanner text.
        duplicate_normal_config = root / "duplicate-normal-table.toml"
        duplicate_normal_config.write_text(
            "[features.multi_agent_v2]\nenabled = true\n"
            "[features.multi_agent_v2]\nenabled = false\n",
            encoding="utf-8",
        )
        for force_fallback in (False, True):
            duplicate_module = bootstrap_module()
            saved_tomllib = duplicate_module.tomllib
            if force_fallback:
                duplicate_module.tomllib = None
            try:
                try:
                    duplicate_module.read_config(duplicate_normal_config)
                    raise AssertionError("duplicate normal table must fail closed")
                except ValueError as error:
                    assert "invalid TOML" in str(error)
            finally:
                duplicate_module.tomllib = saved_tomllib

        # Semantic TOML parsing recognizes a quoted role-table key, then preserves
        # that exact raw table while appending only the other declarations.
        quoted_target, quoted_config = root / "quoted-agents", root / "quoted-config.toml"
        quoted_config.write_text(
            '[agents."goldilocks_spark_worker"]\n'
            'description = "Goldilocks native Spark XHigh Fast leaf for deterministic coding and focused tests."\n'
            'config_file = "quoted-agents/goldilocks-spark-worker.toml"\n',
            encoding="utf-8",
        )
        quoted = output(
            command(
                "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(quoted_target),
                "--config-file", str(quoted_config), "--state-dir", str(root / "quoted-state"),
                env=trusted_environment,
            )
        )
        assert set(quoted["registered"]) == {
            "goldilocks_luna_economy", "goldilocks_terra_engineer", "goldilocks_sol_reviewer",
        }
        assert quoted_config.read_text(encoding="utf-8").count("goldilocks_spark_worker") == 1

        # Python 3.9 has no tomllib. The bundled fallback must still recognize
        # quoted semantic role tables instead of disabling Bootstrap.
        fallback_module = bootstrap_module()
        saved_tomllib = fallback_module.tomllib
        fallback_module.tomllib = None
        try:
            decoded, _ = fallback_module.read_config(quoted_config)
            fallback_states, _ = fallback_module.classify_registration_data(
                quoted_target, quoted_config, decoded
            )
            assert fallback_states["goldilocks_spark_worker"] == "current"
        finally:
            fallback_module.tomllib = saved_tomllib

        invalid_config = root / "invalid-config.toml"
        invalid_config.write_text('[agents."unterminated]\n', encoding="utf-8")
        try:
            bootstrap_module().read_config(invalid_config)
            raise AssertionError("invalid TOML must fail closed")
        except ValueError as error:
            assert "invalid TOML" in str(error)

        # Full TOML validation applies to unrelated settings too: a narrow
        # ownership scanner must never permit malformed host TOML to be appended.
        malformed_target, malformed_config = root / "malformed-agents", root / "malformed.toml"
        malformed_config.write_text("model = [\n", encoding="utf-8")
        for force_fallback in (False, True):
            parser_module = bootstrap_module()
            saved_tomllib = parser_module.tomllib
            if force_fallback:
                parser_module.tomllib = None
            try:
                try:
                    parser_module.read_config(malformed_config)
                    raise AssertionError("malformed unrelated TOML must fail closed")
                except ValueError as error:
                    assert "invalid TOML" in str(error)
            finally:
                parser_module.tomllib = saved_tomllib
        malformed_apply = command(
            "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(malformed_target),
            "--config-file", str(malformed_config), "--state-dir", str(root / "malformed-state"),
            env=trusted_environment,
        )
        assert malformed_apply.returncode != 0 and not malformed_target.exists()

        # Validate the raw Agent declaration structure before tomllib can turn a
        # supported-but-unowned form into a shape that looks current. The same
        # gate is used by Python 3.9 fallback and Python 3.11+ semantic parsing.
        unsupported_agent_forms = {
            "agents-table-inline": "[agents]\ngoldilocks_spark_worker = {}\n",
            "top-level-inline": "agents = { goldilocks_spark_worker = {} }\n",
            "top-level-dotted": "agents.goldilocks_spark_worker = {}\n",
            "agent-array": "[[agents.goldilocks_spark_worker]]\n",
            "dotted-role-field": (
                "[agents.goldilocks_spark_worker]\n"
                'description.extra = "not an owned scalar"\n'
            ),
            "nested-agent-table": "[agents.goldilocks_spark_worker.extra]\n",
        }
        structure_module = bootstrap_module()
        for name, raw_config in unsupported_agent_forms.items():
            structural_config = root / f"{name}.toml"
            structural_config.write_text(raw_config, encoding="utf-8")
            try:
                structure_module.read_config(structural_config)
                raise AssertionError(f"{name} must fail closed with tomllib available")
            except ValueError as error:
                assert "invalid TOML" in str(error)
            saved_tomllib = structure_module.tomllib
            structure_module.tomllib = None
            try:
                try:
                    structure_module.read_config(structural_config)
                    raise AssertionError(f"{name} must fail closed without tomllib")
                except ValueError as error:
                    assert "invalid TOML" in str(error)
            finally:
                structure_module.tomllib = saved_tomllib

        multiline_forms = {
            "basic": 'instructions = """\n[not a table]\n"""\n[features.multi_agent_v2]\nenabled = true\n',
            "literal": "instructions = '''\n[not a table]\n'''\n[features.multi_agent_v2]\nenabled = true\n",
        }
        for name, raw_config in multiline_forms.items():
            multiline_config = root / f"multiline-{name}.toml"
            multiline_config.write_text(raw_config, encoding="utf-8")
            decoded, preserved_raw = structure_module.read_config(multiline_config)
            assert preserved_raw == raw_config
            assert decoded["features"]["multi_agent_v2"]["enabled"] is True
            saved_tomllib = structure_module.tomllib
            structure_module.tomllib = None
            try:
                fallback_decoded, fallback_raw = structure_module.read_config(multiline_config)
                assert fallback_raw == raw_config
                assert fallback_decoded["features"]["multi_agent_v2"]["enabled"] is True
            finally:
                structure_module.tomllib = saved_tomllib
            multiline_target = root / f"multiline-{name}-agents"
            applied_multiline = output(
                command(
                    "--apply", "--yes", "--json", "--host", "codex",
                    "--target-dir", str(multiline_target), "--config-file", str(multiline_config),
                    "--state-dir", str(root / f"multiline-{name}-state"), env=trusted_environment,
                )
            )
            assert len(applied_multiline["registered"]) == 4
            assert multiline_config.read_text(encoding="utf-8").startswith(raw_config)

        duplicate_target, duplicate_config = root / "duplicate-agents", root / "duplicate-config.toml"
        duplicate_config.write_text(
            "[agents.goldilocks_spark_worker]\n"
            '[agents."goldilocks_spark_worker"]\n',
            encoding="utf-8",
        )
        duplicate = command(
            "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(duplicate_target),
            "--config-file", str(duplicate_config), "--state-dir", str(root / "duplicate-state"),
            env=trusted_environment,
        )
        assert duplicate.returncode != 0 and "role declarations" in duplicate.stderr
        assert not duplicate_target.exists()

        # A user-owned declaration that differs in either owned field is a hard
        # conflict: neither templates nor config are changed.
        role_conflict_target = root / "role-conflict-agents"
        role_conflict_config = root / "role-conflict.toml"
        role_conflict_config.write_text(
            "# preserve me\n[agents.goldilocks_spark_worker]\n"
            "description = \"user-owned Spark role\"\n"
            "config_file = \"agents/user-spark.toml\"\n",
            encoding="utf-8",
        )
        role_conflict = command(
            "--apply", "--yes", "--json", "--host", "codex", "--target-dir", str(role_conflict_target),
            "--config-file", str(role_conflict_config), "--state-dir", str(root / "role-conflict-state"),
            env=trusted_environment,
        )
        assert role_conflict.returncode != 0 and "role declarations" in role_conflict.stderr
        assert not role_conflict_target.exists()
        assert role_conflict_config.read_text(encoding="utf-8").startswith("# preserve me\n")

        # The in-process API is also safe when a caller retains a stale plan:
        # apply re-reads config before creating the first template.
        module = bootstrap_module()
        stale_target, stale_config, stale_state = (
            root / "stale-plan-agents", root / "stale-plan-config.toml", root / "stale-plan-state"
        )
        stale_plan = module.plan("codex", stale_target, stale_config, native, stale_state)
        stale_config.write_text(
            "[agents.goldilocks_luna_economy]\n"
            "description = \"new user role\"\n"
            "config_file = \"agents/user-luna.toml\"\n",
            encoding="utf-8",
        )
        try:
            module.apply(stale_plan, stale_state)
            raise AssertionError("stale plan must not install templates after a new role conflict")
        except ValueError as error:
            assert "role declarations" in str(error)
        assert not stale_target.exists()

        # If config changes after apply's first preflight, registration still
        # fails before a template can be created.
        between_target, between_config, between_state = (
            root / "between-preflight-agents", root / "between-preflight-config.toml", root / "between-preflight-state"
        )
        between_plan = module.plan("codex", between_target, between_config, native, between_state)
        original_append = module.append_registrations

        def introduce_conflict_before_registration(config_path: Path, target_path: Path) -> list[str]:
            config_path.write_text(
                "[agents.goldilocks_spark_worker]\n"
                "description = \"concurrent user role\"\n"
                "config_file = \"agents/concurrent-spark.toml\"\n",
                encoding="utf-8",
            )
            return original_append(config_path, target_path)

        module.append_registrations = introduce_conflict_before_registration
        try:
            try:
                module.apply(between_plan, between_state)
                raise AssertionError("late registration conflict must prevent template writes")
            except ValueError as error:
                assert "role declarations" in str(error)
        finally:
            module.append_registrations = original_append
        assert not between_target.exists()

        # A config mutation after append has read/staged the file is detected
        # immediately before replace, so the changed config is never overwritten.
        race_target, race_config = root / "race-agents", root / "race-config.toml"
        race_config.write_text("# baseline\n[features.multi_agent_v2]\nenabled = true\n", encoding="utf-8")
        original_fsync = module.os.fsync

        def mutate_config_after_stage(descriptor: int) -> None:
            original_fsync(descriptor)
            race_config.write_text("# concurrent user edit\n", encoding="utf-8")

        module.os.fsync = mutate_config_after_stage
        try:
            try:
                module.append_registrations(race_config, race_target)
                raise AssertionError("concurrent config mutation must prevent replace")
            except ValueError as error:
                assert "config changed during Bootstrap" in str(error)
        finally:
            module.os.fsync = original_fsync
        assert race_config.read_text(encoding="utf-8") == "# concurrent user edit\n"

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
            ["codex", "plugin", "marketplace", "add", "blackstone2333/goldilocks", "--ref", "v0.5.3-beta.6", "--json"],
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
        assert "plugin marketplace add blackstone2333/goldilocks --ref v0.5.3-beta.6 --json" in calls
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
