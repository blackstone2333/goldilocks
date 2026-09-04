#!/usr/bin/env python3
"""Small, deterministic regression for the capabilities retained in v0.6.0.

This is intentionally an offline contract test.  It does not start an agent,
touch a host, or pretend that an adapter run is model evidence.
"""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))

from native_terminal import exhausted_reset, terminal_state_from_records  # noqa: E402
from inspect_agent_runtime import canonical_native_name, verified_posthoc_fork_turns  # noqa: E402


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_trigger_cases() -> list[dict[str, object]]:
    rows = []
    for line_number, raw in enumerate(
        (ROOT / "evals" / "trigger-cases.jsonl").read_text(encoding="utf-8").splitlines(), 1
    ):
        if not raw.strip():
            continue
        value = json.loads(raw)
        assert isinstance(value, dict), line_number
        rows.append(value)
    return rows


def check_trigger_cases() -> None:
    rows = parse_trigger_cases()
    assert len(rows) >= 50, len(rows)
    ids = [row.get("id") for row in rows]
    assert all(isinstance(value, str) and value for value in ids)
    assert len(ids) == len(set(ids)), "duplicate trigger id"
    required = {"id", "category", "title", "prompt", "host_capability", "material_ambiguity", "expected"}
    for row in rows:
        assert required <= set(row), row.get("id")
        expected = row["expected"]
        assert isinstance(expected, dict)
        for field in ("quality_mode", "overlays", "engines", "max_user_rounds", "max_agent_calls", "required_evidence", "max_rule_words"):
            assert field in expected, (row["id"], field)
        assert isinstance(expected["engines"], list)
        assert isinstance(expected["max_agent_calls"], int)
        assert isinstance(expected["max_user_rounds"], int)
        if row["material_ambiguity"]:
            assert expected["max_user_rounds"] >= 1, row["id"]
    engines = {engine for row in rows for engine in row["expected"]["engines"]}
    assert {"align", "diagnose", "build", "orchestrate", "prove", "evolve"} <= engines
    direct = [row for row in rows if row["expected"]["quality_mode"] == "Direct"]
    assert direct and all(row["expected"]["max_agent_calls"] <= 1 for row in direct)
    # O13 is the deliberate exception: one Fast worker may win a constant-time
    # make-or-delegate check; Direct remains the fallback when it does not.
    o13 = next(row for row in rows if row["id"] == "O13")
    assert o13["expected"]["quality_mode"] == "Direct" and o13["expected"]["max_agent_calls"] == 1
    assert all(row["expected"]["max_rule_words"] <= 1100 for row in direct)


def parse_simple_toml(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in text(path).splitlines():
        match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*"([^"]*)"\s*$', raw)
        if match:
            result[match.group(1)] = match.group(2)
    return result


def check_roles_and_permissions() -> None:
    expected = {
        "goldilocks-sol-reviewer.toml": ("gpt-5.6-sol", "high", "lead__", "none"),
        "goldilocks-terra-engineer.toml": ("gpt-5.6-terra", "medium", "standard__", "none"),
        "goldilocks-spark-worker.toml": ("gpt-5.3-codex-spark", "xhigh", "fast__", "none"),
        "goldilocks-luna-economy.toml": ("gpt-5.6-luna", "max", "fast__", "none"),
    }
    for filename, (model, effort, prefix, fork) in expected.items():
        body = text(PLUGIN / "agents" / filename)
        assert f'model = "{model}"' in body
        assert f'model_reasoning_effort = "{effort}"' in body
        assert prefix in text(PLUGIN / "skills" / "goldilocks" / "references" / "kernel.md")
        assert f'fork_turns`={fork}' in text(PLUGIN / "skills" / "goldilocks" / "references" / "kernel.md") or fork == "none"
    profiles = json.loads(text(PLUGIN / "skills" / "goldilocks" / "assets" / "codex-route-profiles.json"))
    for key in ("goldilocks_spark_worker", "goldilocks_luna_economy", "goldilocks_terra_engineer", "goldilocks_sol_reviewer"):
        assert profiles["profiles"][key]["may_delegate"] is False or key == "goldilocks_terra_engineer"
    assert profiles["profiles"]["goldilocks_sol_reviewer"]["host_permissions"] == "inherit-user-selection"
    kernel = text(PLUGIN / "skills" / "goldilocks" / "references" / "kernel.md")
    assert "do not reduce, override" not in kernel  # permission contract lives in role instructions
    assert "用户可见性不反向塑造路线" in kernel

    profiles = json.loads(text(PLUGIN / "skills" / "goldilocks" / "assets" / "codex-route-profiles.json"))["profiles"]
    for role in ("goldilocks_spark_worker", "goldilocks_luna_economy", "goldilocks_sol_reviewer"):
        assert verified_posthoc_fork_turns(role, profiles[role], "none") == "none"
        for bad in ("all", "1", ""):
            try:
                verified_posthoc_fork_turns(role, profiles[role], bad)
            except ValueError:
                pass
            else:
                raise AssertionError((role, bad))
    terra = profiles["goldilocks_terra_engineer"]
    for value in ("none", "1", "2", "3", "4"):
        assert verified_posthoc_fork_turns("goldilocks_terra_engineer", terra, value) == value
    for bad in ("all", "5"):
        try:
            verified_posthoc_fork_turns("goldilocks_terra_engineer", terra, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(bad)
    assert canonical_native_name("/root/fast__fixtures_spark", profiles["goldilocks_spark_worker"]) == "fast__fixtures_spark"
    for bad_name in ("/root/spark__fixtures_spark", "/root/fast__fixtures_terra", "/root/fast___spark"):
        try:
            canonical_native_name(bad_name, profiles["goldilocks_spark_worker"])
        except ValueError:
            pass
        else:
            raise AssertionError(bad_name)


def check_runtime_mismatch_and_permission_metadata() -> None:
    inspector = PLUGIN / "scripts" / "inspect_agent_runtime.py"
    thread = "22222222-3333-4444-8555-666666666666"
    with tempfile.TemporaryDirectory() as temporary:
        sessions = Path(temporary)
        rollout = sessions / f"rollout-fixture-{thread}.jsonl"
        base = {"type": "session_meta", "payload": {"id": thread, "agent_role": "goldilocks_spark_worker", "agent_path": "/root/fast__fixtures_spark", "parent_thread_id": "parent"}}
        context = {"type": "turn_context", "payload": {"model": "wrong-model", "effort": "xhigh", "cwd": "/fixture", "permission_profile": {"type": "disabled"}}}
        rollout.write_text("\n".join(json.dumps(item) for item in (base, context)) + "\n", encoding="utf-8")
        mismatch = subprocess.run([sys.executable, str(inspector), thread, "--sessions-dir", str(sessions)], text=True, capture_output=True)
        assert mismatch.returncode != 0 and "route mismatch" in mismatch.stderr
        context["payload"]["model"] = "gpt-5.3-codex-spark"
        context["payload"]["permission_profile"] = {"type": "user-selected-full"}
        rollout.write_text("\n".join(json.dumps(item) for item in (base, context)) + "\n", encoding="utf-8")
        valid = subprocess.run([sys.executable, str(inspector), thread, "--sessions-dir", str(sessions)], text=True, capture_output=True)
        assert valid.returncode == 0, valid.stderr
        observed = json.loads(valid.stdout)
        assert observed["model"] == "gpt-5.3-codex-spark"
        assert observed["permission_profile_type"] == "user-selected-full"


def check_quota_fallback_and_night_shift() -> None:
    # Exhaustion is terminal evidence, not a reason to retry Spark.
    reset = exhausted_reset({"limit_name": "spark", "primary": {"used_percent": 100, "resets_at": 123}})
    assert reset == 123
    assert exhausted_reset({"limit_name": "codex", "primary": {"used_percent": 100, "resets_at": 123}}) is None
    records = [
        {"type": "event_msg", "timestamp": "2026-09-04T00:00:00Z", "payload": {"type": "token_count", "rate_limits": {"limit_name": "spark", "primary": {"used_percent": 100, "resets_at": 123}}}},
        {"type": "event_msg", "timestamp": "2026-09-04T00:00:01Z", "payload": {"type": "task_complete"}},
    ]
    state = terminal_state_from_records(records)
    assert state is not None and state.outcome == "completed" and state.quota_reset_at == 123
    kernel = text(PLUGIN / "skills" / "goldilocks" / "references" / "kernel.md")
    assert "不重试 Spark" in kernel
    assert "fallback" in kernel and "Terra/Luna/Direct" in kernel
    assert "economy→Luna" in kernel and "urgent deterministic code→Spark" in kernel
    assert "minimum-sufficient" in kernel
    root_skill = text(PLUGIN / "skills" / "goldilocks" / "SKILL.md")
    assert "按任务匹配加载 domain Skill" in root_skill
    assert "Direct" in root_skill


def main() -> None:
    check_trigger_cases()
    check_roles_and_permissions()
    check_runtime_mismatch_and_permission_metadata()
    check_quota_fallback_and_night_shift()
    print("Goldilocks v0.6.0 retained-capabilities contract passed.")


if __name__ == "__main__":
    main()
