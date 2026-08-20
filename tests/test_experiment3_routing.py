#!/usr/bin/env python3

from __future__ import annotations

import json
import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
INSTALLER = PLUGIN / "scripts" / "install_agents.py"
BOOTSTRAP = PLUGIN / "skills" / "goldilocks-bootstrap" / "scripts" / "bootstrap.py"
GRANT = PLUGIN / "scripts" / "project_delegation.py"
INSPECTOR = PLUGIN / "scripts" / "inspect_agent_runtime.py"
GUARD = PLUGIN / "scripts" / "agent_routing_guard.py"
RECORDER = PLUGIN / "scripts" / "record_routing_outcome.py"
DISPATCHER = PLUGIN / "skills" / "goldilocks" / "scripts" / "dispatch_codex_worker.py"
FACTORY = PLUGIN / "skills" / "goldilocks" / "scripts" / "create_agent_profile.py"
PROFILES = PLUGIN / "skills" / "goldilocks" / "assets" / "codex-route-profiles.json"
ECONOMICS = PLUGIN / "skills" / "goldilocks" / "assets" / "model-economics.json"
TERRA = "gpt-5.6-terra"


def command(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def bootstrap_module():
    spec = importlib.util.spec_from_file_location("goldilocks_bootstrap_migration", BOOTSTRAP)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def hook(data_dir: Path, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PLUGIN_DATA"] = str(data_dir)
    return subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def test_profiles_and_installer(root: Path) -> None:
    route_registry = json.loads(PROFILES.read_text(encoding="utf-8"))
    profiles = route_registry["profiles"]
    assert profiles["goldilocks_spark_coder"]["transport"] == "codex-exec"
    assert profiles["goldilocks_spark_coder"]["model"] == "gpt-5.3-codex-spark"
    assert profiles["goldilocks_luna_worker"]["transport"] == "codex-exec"
    assert profiles["goldilocks_spark_worker"] == {
        "tier": "fast",
        "model": "gpt-5.3-codex-spark",
        "reasoning_effort": "xhigh",
        "transport": "native",
        "agent_type": "goldilocks_spark_worker",
        "may_delegate": False,
    }
    assert profiles["goldilocks_luna_economy"] == {
        "tier": "fast",
        "model": "gpt-5.6-luna",
        "reasoning_effort": "max",
        "transport": "native",
        "agent_type": "goldilocks_luna_economy",
        "may_delegate": False,
    }
    assert profiles["goldilocks_terra_engineer"]["transport"] == "native"
    assert profiles["goldilocks_terra_engineer"]["may_delegate"] is True
    # Native roles inherit the user's host access.  Sol's review restriction is
    # behavioral only; it must not turn a danger-full-access host into a
    # read-only child sandbox.
    assert profiles["goldilocks_sol_reviewer"]["review_mode"] == "no-write-by-contract"
    assert profiles["goldilocks_sol_reviewer"]["host_permissions"] == "inherit-user-selection"
    sol_agent = (PLUGIN / "agents" / "goldilocks-sol-reviewer.toml").read_text(
        encoding="utf-8"
    )
    bootstrap_sol_agent = (
        PLUGIN
        / "skills"
        / "goldilocks-bootstrap"
        / "assets"
        / "bootstrap-agents"
        / "goldilocks-sol-reviewer.toml"
    ).read_text(encoding="utf-8")
    for source in (sol_agent, bootstrap_sol_agent):
        assert "sandbox" not in source
        assert "requested-read-only" not in source
        assert "host\npermission request" in source
    ratios = route_registry["economics"]["chatgpt_standard_same_mix_ratios_to_sol"]
    assert ratios["gpt-5.6-terra"] == 0.4
    assert ratios["gpt-5.6-luna"] == 0.04
    assert ratios["gpt-5.3-codex-spark"] is None

    model_economics = json.loads(ECONOMICS.read_text(encoding="utf-8"))
    sol_rate = next(
        row
        for row in model_economics["models"]["gpt-5.6-sol"]["rates"]
        if row["billing_channel"] == "openai-chatgpt-credits-standard"
    )
    luna_rate = next(
        row
        for row in model_economics["models"]["gpt-5.6-luna"]["rates"]
        if row["billing_channel"] == "openai-chatgpt-credits-standard"
    )
    assert sol_rate == {
        "billing_channel": "openai-chatgpt-credits-standard",
        "currency": "CHATGPT_CREDIT",
        "unit": "per_1m_tokens",
        "input": 125.0,
        "cached_input": 12.5,
        "output": 750.0,
        "source_id": "openai-codex-pricing",
        "conditions": {"service_tier": "standard"},
    }
    assert luna_rate["input"] / sol_rate["input"] == 0.04
    assert luna_rate["cached_input"] / sol_rate["cached_input"] == 0.04
    assert luna_rate["output"] / sol_rate["output"] == 0.04

    target = root / "agents"
    missing = command(str(INSTALLER), "--target-dir", str(target), "--check")
    assert missing.returncode != 0
    installed = command(str(INSTALLER), "--target-dir", str(target), "--json")
    assert installed.returncode == 0, installed.stderr
    result = json.loads(installed.stdout)
    assert result["status"] == "installed"
    assert len(result["installed"]) == 4
    checked = command(
        str(INSTALLER), "--target-dir", str(target), "--check", "--json"
    )
    assert checked.returncode == 0, checked.stderr
    assert json.loads(checked.stdout)["status"] == "current"
    before = {path.name: path.read_bytes() for path in target.iterdir()}
    repeated = command(str(INSTALLER), "--target-dir", str(target), "--json")
    assert repeated.returncode == 0, repeated.stderr
    assert json.loads(repeated.stdout)["status"] == "current"
    assert before == {path.name: path.read_bytes() for path in target.iterdir()}

    migration = root / "legacy-agents"
    migration.mkdir()
    legacy_terra = (ROOT / ".git").exists()
    assert legacy_terra, "fixture requires the shipped template in repository history"
    old_terra = subprocess.run(
        ["git", "show", "v0.5.0-alpha.2:plugins/goldilocks/agents/goldilocks-terra-engineer.toml"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    old_sol = subprocess.run(
        ["git", "show", "v0.5.0-alpha.2:plugins/goldilocks/agents/goldilocks-sol-reviewer.toml"],
        cwd=ROOT,
        capture_output=True,
        check=True,
    ).stdout
    (migration / "goldilocks-terra-engineer.toml").write_bytes(old_terra)
    (migration / "goldilocks-sol-reviewer.toml").write_bytes(old_sol)
    migrated = command(str(INSTALLER), "--target-dir", str(migration), "--json")
    assert migrated.returncode == 0, migrated.stderr
    migration_result = json.loads(migrated.stdout)
    assert set(migration_result["migrated"]) == {
        "goldilocks-terra-engineer.toml",
        "goldilocks-sol-reviewer.toml",
    }
    assert len(migration_result["installed"]) == 2
    assert command(str(INSTALLER), "--target-dir", str(migration), "--check").returncode == 0

    conflict = root / "conflict-agents"
    conflict.mkdir()
    (conflict / "goldilocks-terra-engineer.toml").write_text(
        "user-owned = true\n", encoding="utf-8"
    )
    refused = command(str(INSTALLER), "--target-dir", str(conflict))
    assert refused.returncode != 0
    assert "refusing to overwrite" in refused.stderr
    assert not (conflict / "goldilocks-sol-reviewer.toml").exists()

    real_target = root / "real-agents"
    real_target.mkdir()
    linked_target = root / "linked-agents"
    linked_target.symlink_to(real_target, target_is_directory=True)
    symlink_refused = command(str(INSTALLER), "--target-dir", str(linked_target))
    assert symlink_refused.returncode != 0
    assert "not a real directory" in symlink_refused.stderr
    assert not any(real_target.iterdir())


def test_v052_sol_template_migrates_only_when_byte_exact(root: Path) -> None:
    old = subprocess.run(
        ["git", "show", "v0.5.2:plugins/goldilocks/agents/goldilocks-sol-reviewer.toml"],
        cwd=ROOT, capture_output=True, check=True,
    ).stdout
    target = root / "v052-sol"
    target.mkdir()
    destination = target / "goldilocks-sol-reviewer.toml"
    destination.write_bytes(old)

    installed = command(str(INSTALLER), "--target-dir", str(target), "--json")
    assert installed.returncode == 0, installed.stderr
    assert "goldilocks-sol-reviewer.toml" in json.loads(installed.stdout)["migrated"]
    assert destination.read_bytes() == (PLUGIN / "agents" / destination.name).read_bytes()

    bootstrap = bootstrap_module()
    bootstrap_destination = root / "bootstrap-v052-sol" / "goldilocks-sol-reviewer.toml"
    bootstrap_destination.parent.mkdir()
    bootstrap_destination.write_bytes(old)
    bootstrap_template = bootstrap.TEMPLATE_DIR / bootstrap_destination.name
    assert bootstrap.classify(bootstrap_template, bootstrap_destination) == "legacy"
    bootstrap.replace_legacy(bootstrap_template, bootstrap_destination)
    assert bootstrap_destination.read_bytes() == bootstrap_template.read_bytes()
    bootstrap_destination.write_bytes(old + b"# user edit\n")
    assert bootstrap.classify(bootstrap_template, bootstrap_destination) == "conflict"

    conflict = root / "v052-sol-conflict"
    conflict.mkdir()
    (conflict / "goldilocks-sol-reviewer.toml").write_bytes(old + b"# user edit\n")
    refused = command(str(INSTALLER), "--target-dir", str(conflict))
    assert refused.returncode != 0
    assert "goldilocks-sol-reviewer.toml=conflict" in refused.stderr


def test_project_grant(root: Path) -> None:
    project = root / "project"
    (project / ".git").mkdir(parents=True)
    data = root / "grant-data"
    refused = command(
        str(GRANT), "--grant", "--workdir", str(project), "--data-dir", str(data)
    )
    assert refused.returncode != 0
    granted = command(
        str(GRANT),
        "--grant",
        "--authority",
        "explicit-user",
        "--workdir",
        str(project),
        "--data-dir",
        str(data),
    )
    assert granted.returncode == 0, granted.stderr
    assert json.loads(granted.stdout)["status"] == "active"
    assert str(project).encode() not in (data / "orchestration.db").read_bytes()
    status = command(
        str(GRANT), "--status", "--workdir", str(project), "--data-dir", str(data)
    )
    assert json.loads(status.stdout)["status"] == "active"
    revoked = command(
        str(GRANT), "--revoke", "--workdir", str(project), "--data-dir", str(data)
    )
    assert revoked.returncode == 0, revoked.stderr
    assert json.loads(revoked.stdout)["status"] == "inactive"

    global_grant = command(
        str(GRANT),
        "--grant",
        "--global",
        "--authority",
        "explicit-user",
        "--data-dir",
        str(data),
    )
    assert global_grant.returncode == 0, global_grant.stderr
    global_result = json.loads(global_grant.stdout)
    assert global_result["status"] == "active"
    assert global_result["requested_scope"] == "global"

    inherited_project = root / "inherited-project"
    inherited_project.mkdir()
    inherited = command(
        str(GRANT),
        "--status",
        "--workdir",
        str(inherited_project),
        "--data-dir",
        str(data),
    )
    inherited_result = json.loads(inherited.stdout)
    assert inherited_result["status"] == "active"
    assert inherited_result["effective_source"] == "global"

    project_opt_out = command(
        str(GRANT),
        "--revoke",
        "--workdir",
        str(inherited_project),
        "--data-dir",
        str(data),
    )
    assert json.loads(project_opt_out.stdout)["status"] == "inactive"
    global_status = command(
        str(GRANT), "--status", "--global", "--data-dir", str(data)
    )
    assert json.loads(global_status.stdout)["status"] == "active"


def test_runtime_inspector(root: Path) -> None:
    thread = "11111111-2222-4333-8444-555555555555"
    sessions = root / "sessions" / "2026" / "08" / "03"
    sessions.mkdir(parents=True)
    rollout = sessions / f"rollout-2026-08-03T00-00-00-{thread}.jsonl"
    records = [
        {
            "type": "session_meta",
            "payload": {
                "id": thread,
                "parent_thread_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                "agent_role": "goldilocks_terra_engineer",
                "agent_path": "/fixture/agent.toml",
                "model_provider": "fixture",
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": TERRA,
                "effort": "medium",
                "sandbox_policy": {"type": "danger-full-access"},
                "permission_profile": {"type": "disabled"},
                "cwd": "/fixture",
                "fork_turns": "none",
            },
        },
        {
            "type": "event_msg",
            "payload": {
                "info": {
                    "total_token_usage": {
                        "input_tokens": 45,
                        "cached_input_tokens": 12,
                        "output_tokens": 7,
                    }
                }
            },
        },
    ]
    rollout.write_text(
        "\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8"
    )
    inspected = command(
        str(INSPECTOR), thread, "--sessions-dir", str(root / "sessions")
    )
    assert inspected.returncode == 0, inspected.stderr
    result = json.loads(inspected.stdout)
    assert result["agent_role"] == "goldilocks_terra_engineer"
    assert result["model"] == TERRA and result["effort"] == "medium"
    assert result["sandbox_policy_type"] == "danger-full-access"
    assert result["permission_profile_type"] == "disabled"
    assert result["input_tokens"] == 45
    assert result["cached_input_tokens"] == 12
    assert result["output_tokens"] == 7

    audit = root / "inspector-audit"
    audit.mkdir()
    with sqlite3.connect(audit / "orchestration.db") as connection:
        connection.execute(
            "CREATE TABLE decisions (decision_id TEXT PRIMARY KEY, status TEXT, "
            "actual_model TEXT, task_name TEXT, cwd_hash TEXT, task_fingerprint TEXT)"
        )
        connection.execute(
            "CREATE TABLE executions (agent_id TEXT PRIMARY KEY, decision_id TEXT, "
            "actual_agent_type TEXT, actual_model TEXT, actual_effort TEXT, "
            "sandbox_policy_type TEXT, permission_profile_type TEXT, input_tokens INTEGER, "
            "cached_input_tokens INTEGER, output_tokens INTEGER)"
        )
        connection.execute(
            "INSERT INTO decisions VALUES "
            "('decision-1', 'verified_pass', ?, 'old', 'old', 'old')",
            (TERRA,),
        )
        connection.execute(
            "INSERT INTO executions VALUES (?, 'decision-1', ?, ?, 'high', "
            "'read-only', 'disabled', 1, 1, 1)",
            (thread, "goldilocks_terra_engineer", TERRA),
        )
    immutable = command(
        str(INSPECTOR),
        thread,
        "--sessions-dir",
        str(root / "sessions"),
        "--data-dir",
        str(audit),
        "--record",
    )
    assert immutable.returncode != 0
    assert "immutable after Lead verification" in immutable.stderr

    # Runtime metadata enriches an already planned route but must never replace
    # its canonical contract identity when the rollout omits agent_path.
    mutable_thread = "22222222-3333-4444-8555-666666666666"
    mutable_records = [
        {
            "type": "session_meta",
            "payload": {
                "id": mutable_thread,
                "parent_thread_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                "agent_role": "goldilocks_terra_engineer",
                "model_provider": "fixture",
            },
        },
        records[1],
        records[2],
    ]
    (sessions / f"rollout-2026-08-03T00-30-00-{mutable_thread}.jsonl").write_text(
        "\n".join(json.dumps(item) for item in mutable_records) + "\n",
        encoding="utf-8",
    )
    planned_name = "standard__planned_identity_terra"
    planned_cwd_hash = "planned-cwd-hash"
    planned_fingerprint = "planned-task-fingerprint"
    with sqlite3.connect(audit / "orchestration.db") as connection:
        connection.execute(
            "INSERT INTO decisions VALUES (?, 'started', NULL, ?, ?, ?)",
            ("decision-2", planned_name, planned_cwd_hash, planned_fingerprint),
        )
        connection.execute(
            "INSERT INTO executions VALUES (?, 'decision-2', ?, ?, NULL, NULL, NULL, NULL, NULL, NULL)",
            (mutable_thread, "goldilocks_terra_engineer", TERRA),
        )
    mutable = command(
        str(INSPECTOR),
        mutable_thread,
        "--sessions-dir",
        str(root / "sessions"),
        "--data-dir",
        str(audit),
        "--record",
    )
    assert mutable.returncode == 0, mutable.stderr
    assert json.loads(mutable.stdout)["recorded"] is True
    with sqlite3.connect(audit / "orchestration.db") as connection:
        preserved = connection.execute(
            "SELECT actual_model, task_name, cwd_hash, task_fingerprint "
            "FROM decisions WHERE decision_id = 'decision-2'"
        ).fetchone()
    assert preserved == (TERRA, planned_name, planned_cwd_hash, planned_fingerprint)

    # Codex native starts can precede the rollout metadata that contains the
    # canonical child path and effort.  The inspector may repair precisely that
    # observed-only state, but not infer any broader route.
    posthoc_data = root / "posthoc-audit"
    parent = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
    posthoc_thread = "66666666-7777-4888-8999-aaaaaaaaaaaa"
    posthoc_start = hook(
        posthoc_data,
        {
            "hook_event_name": "SubagentStart",
            "session_id": parent,
            "turn_id": "native-child-turn",
            "agent_id": posthoc_thread,
            "agent_type": "goldilocks_terra_engineer",
            "model": TERRA,
            "cwd": "/fixture",
        },
    )
    assert posthoc_start.returncode == 0, posthoc_start.stderr
    posthoc_rollout = sessions / f"rollout-2026-08-03T01-00-00-{posthoc_thread}.jsonl"
    posthoc_records = [
        {
            "type": "session_meta",
            "payload": {
                "id": posthoc_thread,
                "parent_thread_id": parent,
                "agent_role": "goldilocks_terra_engineer",
                "agent_path": "/root/standard__posthoc_runtime_terra",
            },
        },
        {
            "type": "turn_context",
            "payload": {
                "model": TERRA,
                "effort": "medium",
                "sandbox_policy": {"type": "danger-full-access"},
                "permission_profile": {"type": "disabled"},
                "cwd": "/fixture",
                "fork_turns": "none",
            },
        },
        {
            "type": "event_msg",
            "payload": {"info": {"total_token_usage": {"input_tokens": 13, "cached_input_tokens": 5, "output_tokens": 3}}},
        },
    ]
    posthoc_rollout.write_text(
        "\n".join(json.dumps(item) for item in posthoc_records) + "\n", encoding="utf-8"
    )
    posthoc_stop = hook(
        posthoc_data,
        {
            "hook_event_name": "SubagentStop",
            "session_id": parent,
            "agent_id": posthoc_thread,
            "agent_type": "goldilocks_terra_engineer",
            "model": TERRA,
        },
    )
    assert posthoc_stop.returncode == 0, posthoc_stop.stderr
    posthoc = command(
        str(INSPECTOR), posthoc_thread, "--sessions-dir", str(root / "sessions"),
        "--data-dir", str(posthoc_data), "--record",
    )
    assert posthoc.returncode == 0, posthoc.stderr
    assert json.loads(posthoc.stdout)["recorded"] is True
    with sqlite3.connect(posthoc_data / "orchestration.db") as connection:
        connection.row_factory = sqlite3.Row
        decision = connection.execute(
            "SELECT * FROM decisions WHERE agent_id = ?", (posthoc_thread,)
        ).fetchone()
        execution = connection.execute(
            "SELECT * FROM executions WHERE agent_id = ?", (posthoc_thread,)
        ).fetchone()
    assert decision["task_name"] == "standard__posthoc_runtime_terra"
    assert decision["correlation_confidence"] == "posthoc_role_observed"
    assert decision["status"] == "stopped"
    assert decision["planned_at"] == execution["started_at"]
    assert decision["started_at"] == execution["started_at"]
    assert decision["stopped_at"] == execution["stopped_at"]
    assert execution["decision_id"] == decision["decision_id"]
    assert execution["actual_effort"] == "medium"
    assert execution["input_tokens"] == 13 and execution["output_tokens"] == 3
    repeated = command(
        str(INSPECTOR), posthoc_thread, "--sessions-dir", str(root / "sessions"),
        "--data-dir", str(posthoc_data), "--record",
    )
    assert repeated.returncode == 0, repeated.stderr
    with sqlite3.connect(posthoc_data / "orchestration.db") as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM decisions WHERE agent_id = ?", (posthoc_thread,)
        ).fetchone()[0] == 1

    # The posthoc bridge rejects all material ambiguities rather than converting
    # them into a reusable native decision.
    bad_parent_thread = "77777777-8888-4999-8aaa-bbbbbbbbbbbb"
    bad_parent = [dict(item) for item in posthoc_records]
    bad_parent[0] = {**bad_parent[0], "payload": {**posthoc_records[0]["payload"], "id": bad_parent_thread, "parent_thread_id": "wrong-parent"}}
    (sessions / f"rollout-2026-08-03T02-00-00-{bad_parent_thread}.jsonl").write_text(
        "\n".join(json.dumps(item) for item in bad_parent) + "\n", encoding="utf-8"
    )
    hook(posthoc_data, {"hook_event_name": "SubagentStart", "session_id": parent, "agent_id": bad_parent_thread, "agent_type": "goldilocks_terra_engineer", "model": TERRA, "cwd": "/fixture"})
    rejected_parent = command(str(INSPECTOR), bad_parent_thread, "--sessions-dir", str(root / "sessions"), "--data-dir", str(posthoc_data), "--record")
    assert rejected_parent.returncode != 0 and "parent_thread_id" in rejected_parent.stderr

    bad_name_thread = "88888888-9999-4aaa-8bbb-cccccccccccc"
    bad_name = [dict(item) for item in posthoc_records]
    bad_name[0] = {**bad_name[0], "payload": {**posthoc_records[0]["payload"], "id": bad_name_thread, "agent_path": "/root/not-a-route"}}
    (sessions / f"rollout-2026-08-03T03-00-00-{bad_name_thread}.jsonl").write_text("\n".join(json.dumps(item) for item in bad_name) + "\n", encoding="utf-8")
    hook(posthoc_data, {"hook_event_name": "SubagentStart", "session_id": parent, "agent_id": bad_name_thread, "agent_type": "goldilocks_terra_engineer", "model": TERRA, "cwd": "/fixture"})
    rejected_name = command(str(INSPECTOR), bad_name_thread, "--sessions-dir", str(root / "sessions"), "--data-dir", str(posthoc_data), "--record")
    assert rejected_name.returncode != 0 and "canonical native task name" in rejected_name.stderr

    bad_profile_thread = "99999999-aaaa-4bbb-8ccc-dddddddddddd"
    bad_profile = [dict(item) for item in posthoc_records]
    bad_profile[0] = {
        **bad_profile[0],
        "payload": {**posthoc_records[0]["payload"], "id": bad_profile_thread},
    }
    bad_profile[1] = {
        **bad_profile[1],
        "payload": {**posthoc_records[1]["payload"], "model": "gpt-5.6-sol"},
    }
    (sessions / f"rollout-2026-08-03T04-00-00-{bad_profile_thread}.jsonl").write_text(
        "\n".join(json.dumps(item) for item in bad_profile) + "\n", encoding="utf-8"
    )
    hook(posthoc_data, {"hook_event_name": "SubagentStart", "session_id": parent, "agent_id": bad_profile_thread, "agent_type": "goldilocks_terra_engineer", "model": TERRA, "cwd": "/fixture"})
    rejected_profile = command(str(INSPECTOR), bad_profile_thread, "--sessions-dir", str(root / "sessions"), "--data-dir", str(posthoc_data), "--record")
    assert rejected_profile.returncode != 0 and "route mismatch" in rejected_profile.stderr

    unplanned_thread = "aaaaaaaa-bbbb-4ccc-8ddd-ffffffffffff"
    unplanned = [dict(item) for item in posthoc_records]
    unplanned[0] = {**unplanned[0], "payload": {**posthoc_records[0]["payload"], "id": unplanned_thread}}
    (sessions / f"rollout-2026-08-03T05-00-00-{unplanned_thread}.jsonl").write_text(
        "\n".join(json.dumps(item) for item in unplanned) + "\n", encoding="utf-8"
    )
    hook(posthoc_data, {"hook_event_name": "SubagentStart", "session_id": parent, "agent_id": unplanned_thread, "agent_type": "goldilocks_terra_engineer", "model": TERRA, "cwd": "/fixture"})
    with sqlite3.connect(posthoc_data / "orchestration.db") as connection:
        connection.execute("UPDATE executions SET correlation_confidence = 'unplanned' WHERE agent_id = ?", (unplanned_thread,))
    rejected_unplanned = command(str(INSPECTOR), unplanned_thread, "--sessions-dir", str(root / "sessions"), "--data-dir", str(posthoc_data), "--record")
    assert rejected_unplanned.returncode != 0 and "not eligible" in rejected_unplanned.stderr
    with sqlite3.connect(posthoc_data / "orchestration.db") as connection:
        connection.execute("UPDATE executions SET correlation_confidence = 'ambiguous' WHERE agent_id = ?", (unplanned_thread,))
    rejected_ambiguous = command(str(INSPECTOR), unplanned_thread, "--sessions-dir", str(root / "sessions"), "--data-dir", str(posthoc_data), "--record")
    assert rejected_ambiguous.returncode != 0 and "not eligible" in rejected_ambiguous.stderr

    different_thread = "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"
    different = [dict(item) for item in posthoc_records]
    different[0] = {**different[0], "payload": {**posthoc_records[0]["payload"], "id": different_thread}}
    (sessions / f"rollout-2026-08-03T06-00-00-{different_thread}.jsonl").write_text(
        "\n".join(json.dumps(item) for item in different) + "\n", encoding="utf-8"
    )
    hook(posthoc_data, {"hook_event_name": "SubagentStart", "session_id": parent, "agent_id": different_thread, "agent_type": "goldilocks_terra_engineer", "model": TERRA, "cwd": "/fixture"})
    with sqlite3.connect(posthoc_data / "orchestration.db") as connection:
        connection.execute(
            "INSERT INTO decisions SELECT ?, session_id, turn_id, ?, cwd_hash, task_fingerprint, "
            "task_name, tier, parent_model, expected_model, expected_agent_type, expected_effort, "
            "expected_sandbox, billing_channel, transport, fork_turns, status, prior_observations, "
            "planned_at, started_at, stopped_at, actual_model, ?, correlation_confidence, policy_version "
            "FROM decisions WHERE decision_id = ?",
            ("different-decision", "different-tool", different_thread, decision["decision_id"]),
        )
    rejected_different = command(str(INSPECTOR), different_thread, "--sessions-dir", str(root / "sessions"), "--data-dir", str(posthoc_data), "--record")
    assert rejected_different.returncode != 0 and "different routing decision" in rejected_different.stderr


def test_native_role_audit(root: Path) -> None:
    data = root / "routing-data"
    base = {
        "session_id": "experiment-3-session",
        "turn_id": "parent-turn",
        "agent_id": "lead-agent",
        "cwd": str(ROOT),
        "model": "gpt-5.6-sol",
        "permission_mode": "default",
    }
    planned = hook(
        data,
        {
            **base,
            "hook_event_name": "PreToolUse",
            "tool_name": "spawn_agent",
            "tool_use_id": "terra-route",
            "tool_input": {
                "task_name": "standard__bounded_domain",
                "fork_turns": "none",
                "agent_type": "goldilocks_terra_engineer",
                "model": TERRA,
                "reasoning_effort": "medium",
                "message": "Implement the bounded domain and report evidence.",
            },
        },
    )
    assert planned.returncode == 0, planned.stderr
    update = json.loads(planned.stdout)["hookSpecificOutput"]["updatedInput"]
    assert update["agent_type"] == "goldilocks_terra_engineer"
    assert update["task_name"] == "standard__bounded_domain_terra"
    assert "model" not in update and "reasoning_effort" not in update

    started = hook(
        data,
        {
            **base,
            "hook_event_name": "SubagentStart",
            "turn_id": "child-turn",
            "agent_id": "terra-child",
            "agent_type": "goldilocks_terra_engineer",
            "model": TERRA,
            "reasoning_effort": "medium",
            "sandbox_policy": {"type": "danger-full-access"},
            "permission_profile": {"type": "disabled"},
        },
    )
    assert started.returncode == 0 and started.stdout == "", started.stdout
    stopped = hook(
        data,
        {
            **base,
            "hook_event_name": "SubagentStop",
            "turn_id": "child-turn",
            "agent_id": "terra-child",
            "agent_type": "goldilocks_terra_engineer",
            "model": TERRA,
            "usage": {
                "input_tokens": 100,
                "cached_input_tokens": 60,
                "output_tokens": 20,
            },
        },
    )
    assert stopped.returncode == 0 and stopped.stdout == ""

    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.row_factory = sqlite3.Row
        decision = connection.execute(
            "SELECT * FROM decisions WHERE tool_use_id = 'terra-route'"
        ).fetchone()
        execution = connection.execute(
            "SELECT * FROM executions WHERE agent_id = 'terra-child'"
        ).fetchone()
    assert decision["expected_agent_type"] == "goldilocks_terra_engineer"
    assert decision["expected_model"] == TERRA
    assert decision["expected_effort"] == "medium"
    assert execution["actual_agent_type"] == "goldilocks_terra_engineer"
    assert execution["actual_effort"] == "medium"
    assert execution["sandbox_policy_type"] == "danger-full-access"
    assert execution["input_tokens"] == 100
    assert execution["cached_input_tokens"] == 60
    assert execution["output_tokens"] == 20
    assert execution["elapsed_ms"] is not None

    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.execute(
            "UPDATE executions SET actual_effort = NULL WHERE agent_id = 'terra-child'"
        )
    missing_effort = command(
        str(RECORDER),
        "--data-dir",
        str(data),
        "--agent-id",
        "terra-child",
        "--result",
        "pass",
        "--evidence",
        "must fail without effort",
    )
    assert missing_effort.returncode != 0 and "reasoning effort" in missing_effort.stderr
    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.execute(
            "UPDATE executions SET actual_effort = 'medium', permission_profile_type = NULL "
            "WHERE agent_id = 'terra-child'"
        )
    missing_permission = command(
        str(RECORDER),
        "--data-dir",
        str(data),
        "--agent-id",
        "terra-child",
        "--result",
        "pass",
        "--evidence",
        "must fail without permission metadata",
    )
    assert missing_permission.returncode != 0
    assert "permission profile" in missing_permission.stderr
    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.execute(
            "UPDATE executions SET permission_profile_type = 'disabled' "
            "WHERE agent_id = 'terra-child'"
        )

    verified = command(
        str(RECORDER),
        "--data-dir",
        str(data),
        "--agent-id",
        "terra-child",
        "--result",
        "pass",
        "--evidence",
        "focused checks passed",
        "--rework-count",
        "1",
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["rework_count"] == 1
    with sqlite3.connect(data / "orchestration.db") as connection:
        rework = connection.execute(
            "SELECT rework_count FROM executions WHERE agent_id = 'terra-child'"
        ).fetchone()[0]
    assert rework == 1

    stale_review = hook(
        data,
        {
            **base,
            "hook_event_name": "PreToolUse",
            "tool_name": "spawn_agent",
            "tool_use_id": "bad-review",
            "tool_input": {
                "task_name": "lead__final_review",
                "fork_turns": "1",
                "agent_type": "goldilocks_sol_reviewer",
                "message": "Review only.",
            },
        },
    )
    denial = json.loads(stale_review.stdout)["hookSpecificOutput"]
    assert denial["permissionDecision"] == "deny"
    assert "fork_turns=none" in denial["permissionDecisionReason"]

    observed_data = root / "observed-routing-data"
    observed_start = hook(
        observed_data,
        {
            **base,
            "session_id": "observed-session",
            "hook_event_name": "SubagentStart",
            "turn_id": "observed-child-turn",
            "agent_id": "observed-terra-child",
            "agent_type": "goldilocks_terra_engineer",
            "agent_path": "/root/standard__observed_route_terra",
            "model": TERRA,
        },
    )
    assert observed_start.returncode == 0 and observed_start.stdout == ""
    with sqlite3.connect(observed_data / "orchestration.db") as connection:
        connection.row_factory = sqlite3.Row
        observed_decision = connection.execute(
            "SELECT * FROM decisions WHERE agent_id = 'observed-terra-child'"
        ).fetchone()
        observed_execution = connection.execute(
            "SELECT * FROM executions WHERE agent_id = 'observed-terra-child'"
        ).fetchone()
    assert observed_decision["task_name"] == "standard__observed_route_terra"
    assert observed_decision["expected_agent_type"] == "goldilocks_terra_engineer"
    assert observed_decision["expected_effort"] == "medium"
    assert observed_execution["correlation_confidence"] == "role_observed"


def test_external_route_audit(root: Path) -> None:
    source_home = root / "source-home"
    codex_home = source_home / ".codex"
    codex_home.mkdir(parents=True)
    (codex_home / "auth.json").write_text("{}\n", encoding="utf-8")
    (codex_home / "models_cache.json").write_text(
        json.dumps(
            {
                "models": [
                    {"slug": "gpt-5.3-codex-spark"},
                    {"slug": "gpt-5.6-luna"},
                    {"slug": "kimi-k2.7-code"},
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (codex_home / "config.toml").write_text("", encoding="utf-8")
    fake = root / "fake-codex"
    fake.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
prompt = sys.stdin.read()
model = args[args.index('-m') + 1]
effort_arg = next(value for value in args if value.startswith('model_reasoning_effort='))
effort = effort_arg.split('=', 1)[1].strip('\\"')
thread = os.environ.get('FAKE_THREAD_ID', '22222222-3333-4444-8555-666666666666')
root = Path(os.environ['CODEX_HOME']) / 'sessions' / '2026' / '08' / '03'
root.mkdir(parents=True)
rollout = root / f'rollout-test-{thread}.jsonl'
records = [
  {'type':'session_meta','payload':{'id':thread}},
  {'type':'turn_context','payload':{'model':model,'effort':effort,'sandbox_policy':{'type':'read-only'},'permission_profile':{'type':'disabled'},'cwd':os.getcwd()}},
  {'type':'event_msg','payload':{'info':{'total_token_usage':{'input_tokens':30,'cached_input_tokens':10,'output_tokens':5}}}},
]
rollout.write_text('\\n'.join(json.dumps(item) for item in records) + '\\n')
decoy = root / 'rollout-newer-33333333-4444-4555-8666-777777777777.jsonl'
decoy.write_text(json.dumps({'type':'turn_context','payload':{'model':'wrong-model','effort':'low','cwd':os.getcwd()}}) + '\\n')
print(json.dumps({'type':'thread.started','thread_id':thread}))
message = 'GOLDILOCKS_PREFLIGHT_OK' if 'Goldilocks read-only route preflight' in prompt else 'ROUTE_OK_SPARK'
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':message}}))
print(json.dumps({'type':'turn.completed','usage':{'input_tokens':30,'output_tokens':5}}))
raise SystemExit(int(os.environ.get('FAKE_EXIT_CODE', '0')))
""",
        encoding="utf-8",
    )
    fake.chmod(0o755)
    contract = root / "external-contract.md"
    contract.write_text(
        "Reply with the completion marker only. Do not modify files.\n", encoding="utf-8"
    )
    workdir = root / "external-workdir"
    workdir.mkdir()
    data = root / "external-data"
    env = os.environ.copy()
    env.update(
        {
            "GOLDILOCKS_CODEX_BIN": str(fake),
            "GOLDILOCKS_SOURCE_CODEX_HOME": str(codex_home),
            "HOME": str(source_home),
            "CODEX_HOME": str(codex_home),
            "CODEX_THREAD_ID": "parent-experiment-thread",
        }
    )
    dispatched = command(
        str(DISPATCHER),
        "--workdir",
        str(workdir),
        "--task-name",
        "fast__external_probe",
        "--task-file",
        str(contract),
        "--work-type",
        "spark-coding",
        "--sandbox",
        "read-only",
        "--data-dir",
        str(data),
        env=env,
    )
    assert dispatched.returncode == 0, dispatched.stderr
    output_lines = dispatched.stdout.strip().splitlines()
    summary = json.loads(output_lines[0])
    assert summary["model"] == "gpt-5.3-codex-spark"
    assert summary["thread_id"] == "22222222-3333-4444-8555-666666666666"
    assert summary["route_id"]
    assert output_lines[1] == "ROUTE_OK_SPARK"
    assert summary["events"] is None, "automatic audits must not retain raw worker events"
    assert not (data / "worker-events").exists()
    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.row_factory = sqlite3.Row
        route = connection.execute("SELECT * FROM external_routes").fetchone()
    assert route["expected_agent_type"] == "goldilocks_spark_coder"
    assert route["task_name"] == "fast__external_probe_spark"
    assert route["expected_model"] == "gpt-5.3-codex-spark"
    assert route["actual_model"] == route["expected_model"]
    assert route["actual_effort"] == "medium"
    assert route["status"] == "succeeded"
    assert route["route_id"] == summary["route_id"]
    assert route["child_thread_id"] == summary["thread_id"]
    assert route["parent_session_id"] == "parent-experiment-thread"
    assert route["input_tokens"] == 30 and route["output_tokens"] == 5
    with sqlite3.connect(data / "orchestration.db") as connection:
        observed_experience = connection.execute(
            """
            SELECT observed_completions, verified_passes, verified_failures
            FROM experiences
            WHERE task_fingerprint = ? AND model = ?
            """,
            (route["task_fingerprint"], route["actual_model"]),
        ).fetchone()
    assert observed_experience == (1, 0, 0)
    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.execute(
            "UPDATE external_routes SET actual_effort = NULL WHERE route_id = ?",
            (route["route_id"],),
        )
    missing_effort = command(
        str(RECORDER),
        "--data-dir",
        str(data),
        "--route-id",
        route["route_id"],
        "--result",
        "pass",
        "--evidence",
        "must fail without effort",
    )
    assert missing_effort.returncode != 0 and "reasoning effort" in missing_effort.stderr
    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.execute(
            "UPDATE external_routes SET actual_effort = 'medium', "
            "sandbox_policy_type = 'workspace-write' WHERE route_id = ?",
            (route["route_id"],),
        )
    wrong_sandbox = command(
        str(RECORDER),
        "--data-dir",
        str(data),
        "--route-id",
        route["route_id"],
        "--result",
        "pass",
        "--evidence",
        "must fail on sandbox mismatch",
    )
    assert wrong_sandbox.returncode != 0 and "observed sandbox" in wrong_sandbox.stderr
    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.execute(
            "UPDATE external_routes SET sandbox_policy_type = 'read-only', "
            "permission_profile_type = 'disabled' WHERE route_id = ?",
            (route["route_id"],),
        )
    verified = command(
        str(RECORDER),
        "--data-dir",
        str(data),
        "--route-id",
        route["route_id"],
        "--result",
        "pass",
        "--evidence",
        "external probe returned zero",
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["status"] == "recorded"
    with sqlite3.connect(data / "orchestration.db") as connection:
        verified_experience = connection.execute(
            """
            SELECT observed_completions, verified_passes, verified_failures
            FROM experiences
            WHERE task_fingerprint = ? AND model = ?
            """,
            (route["task_fingerprint"], route["actual_model"]),
        ).fetchone()
    assert verified_experience == (1, 1, 0)

    failed_env = {
        **env,
        "FAKE_EXIT_CODE": "3",
        "FAKE_THREAD_ID": "44444444-5555-4666-8777-888888888888",
    }
    failed_dispatch = command(
        str(DISPATCHER),
        "--workdir",
        str(workdir),
        "--task-name",
        "fast__external_failure",
        "--task-file",
        str(contract),
        "--work-type",
        "spark-coding",
        "--sandbox",
        "read-only",
        "--data-dir",
        str(data),
        env=failed_env,
    )
    assert failed_dispatch.returncode == 3
    failed_summary = json.loads(failed_dispatch.stdout.strip().splitlines()[0])
    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.row_factory = sqlite3.Row
        failed_route = connection.execute(
            "SELECT * FROM external_routes WHERE route_id = ?",
            (failed_summary["route_id"],),
        ).fetchone()
    assert failed_route["status"] == "failed"
    assert failed_route["task_name"] == "fast__external_failure_spark"
    assert failed_route["stopped_at"]
    assert failed_route["child_thread_id"] == failed_summary["thread_id"]

    failed_cannot_pass = command(
        str(RECORDER),
        "--data-dir",
        str(data),
        "--route-id",
        failed_route["route_id"],
        "--result",
        "pass",
        "--evidence",
        "failed route cannot pass",
    )
    assert failed_cannot_pass.returncode != 0
    assert "did not complete successfully" in failed_cannot_pass.stderr
    recorded_failure = command(
        str(RECORDER),
        "--data-dir",
        str(data),
        "--route-id",
        failed_route["route_id"],
        "--result",
        "fail",
        "--evidence",
        "worker exited 3",
    )
    assert recorded_failure.returncode == 0, recorded_failure.stderr
    assert json.loads(recorded_failure.stdout)["status"] == "recorded"
    with sqlite3.connect(data / "orchestration.db") as connection:
        failed_experience = connection.execute(
            """
            SELECT observed_completions, verified_passes, verified_failures
            FROM experiences
            WHERE task_fingerprint = ? AND model = ?
            """,
            (failed_route["task_fingerprint"], failed_route["actual_model"]),
        ).fetchone()
    assert failed_experience == (1, 0, 1)

    discovered = command(
        str(FACTORY),
        "discover",
        "--models-cache",
        str(codex_home / "models_cache.json"),
        "--data-dir",
        str(data),
        "--require-capability",
        "coding",
        env=env,
    )
    assert discovered.returncode == 0, discovered.stderr
    discovery = json.loads(discovered.stdout)
    assert discovery["consumed_model_quota"] is False
    assert any(
        row["model"] == "kimi-k2.7-code"
        and row["billing_channel"] == "kimi-api-standard"
        and row["rankable"] is True
        for row in discovery["candidates"]
    )

    unauthorized = command(
        str(FACTORY),
        "create",
        "--model",
        "kimi-k2.7-code",
        "--billing-channel",
        "kimi-api-standard",
        "--models-cache",
        str(codex_home / "models_cache.json"),
        "--data-dir",
        str(data),
        "--sandbox",
        "read-only",
        env=env,
    )
    assert unauthorized.returncode != 0
    assert "ask the user" in unauthorized.stderr

    invisible = command(
        str(FACTORY),
        "authorize",
        "--model",
        "deepseek-v4-flash",
        "--billing-channel",
        "deepseek-api-standard",
        "--authority",
        "explicit-user",
        "--models-cache",
        str(codex_home / "models_cache.json"),
        "--data-dir",
        str(data),
        env=env,
    )
    assert invisible.returncode != 0 and "not advertised" in invisible.stderr

    authorized = command(
        str(FACTORY),
        "authorize",
        "--model",
        "kimi-k2.7-code",
        "--billing-channel",
        "kimi-api-standard",
        "--authority",
        "explicit-user",
        "--models-cache",
        str(codex_home / "models_cache.json"),
        "--data-dir",
        str(data),
        env=env,
    )
    assert authorized.returncode == 0, authorized.stderr
    authorization = json.loads(authorized.stdout)
    assert authorization["scope"] == "global-model-and-billing-channel-until-revoked"

    stale_registry = root / "stale-economics.json"
    stale_payload = json.loads(ECONOMICS.read_text(encoding="utf-8"))
    stale_payload["sources"]["kimi-k27-code-pricing"]["expires_at"] = (
        "2020-01-01T00:00:00+00:00"
    )
    stale_registry.write_text(json.dumps(stale_payload), encoding="utf-8")
    stale_create = command(
        str(FACTORY),
        "create",
        "--model",
        "kimi-k2.7-code",
        "--billing-channel",
        "kimi-api-standard",
        "--name",
        "stale_kimi",
        "--economics",
        str(stale_registry),
        "--models-cache",
        str(codex_home / "models_cache.json"),
        "--data-dir",
        str(data),
        "--sandbox",
        "read-only",
        env=env,
    )
    assert stale_create.returncode != 0 and "expired" in stale_create.stderr

    unofficial_registry = root / "unofficial-economics.json"
    unofficial_payload = json.loads(ECONOMICS.read_text(encoding="utf-8"))
    unofficial_payload["sources"]["kimi-k27-code-pricing"]["kind"] = "aggregator"
    unofficial_registry.write_text(json.dumps(unofficial_payload), encoding="utf-8")
    unofficial_authorize = command(
        str(FACTORY),
        "authorize",
        "--model",
        "kimi-k2.7-code",
        "--billing-channel",
        "kimi-api-standard",
        "--authority",
        "explicit-user",
        "--economics",
        str(unofficial_registry),
        "--models-cache",
        str(codex_home / "models_cache.json"),
        "--data-dir",
        str(root / "unofficial-data"),
        env=env,
    )
    assert unofficial_authorize.returncode != 0
    assert "official source" in unofficial_authorize.stderr

    created = command(
        str(FACTORY),
        "create",
        "--model",
        "kimi-k2.7-code",
        "--billing-channel",
        "kimi-api-standard",
        "--models-cache",
        str(codex_home / "models_cache.json"),
        "--data-dir",
        str(data),
        "--require-capability",
        "coding",
        "--sandbox",
        "read-only",
        env=env,
    )
    assert created.returncode == 0, created.stderr
    created_result = json.loads(created.stdout)
    profile_path = Path(created_result["profile"])
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    assert profile["model"] == "kimi-k2.7-code"
    assert profile["may_delegate"] is False
    assert profile["authorization"]["scope"] == (
        "global-model-and-billing-channel-until-revoked"
    )
    assert profile["preflight"]["status"] == "passed"
    assert profile["integrity_sha256"]

    repeated_profile = command(
        str(FACTORY),
        "create",
        "--model",
        "kimi-k2.7-code",
        "--billing-channel",
        "kimi-api-standard",
        "--models-cache",
        str(codex_home / "models_cache.json"),
        "--data-dir",
        str(data),
        "--sandbox",
        "read-only",
        env=env,
    )
    assert repeated_profile.returncode != 0
    assert "refusing to overwrite" in repeated_profile.stderr

    another_project = root / "another-project"
    another_project.mkdir()
    dynamic_dispatch = command(
        str(DISPATCHER),
        "--workdir",
        str(another_project),
        "--task-name",
        "fast__authorized_kimi",
        "--task-file",
        str(contract),
        "--agent-profile",
        str(profile_path),
        "--data-dir",
        str(data),
        env=env,
    )
    assert dynamic_dispatch.returncode == 0, dynamic_dispatch.stderr
    dynamic_summary = json.loads(dynamic_dispatch.stdout.strip().splitlines()[0])
    assert dynamic_summary["model"] == "kimi-k2.7-code"
    assert dynamic_summary["billing_channel"] == "kimi-api-standard"
    with sqlite3.connect(data / "orchestration.db") as connection:
        connection.row_factory = sqlite3.Row
        dynamic_route = connection.execute(
            "SELECT * FROM external_routes WHERE route_id = ?",
            (dynamic_summary["route_id"],),
        ).fetchone()
    assert dynamic_route["expected_agent_type"] == profile["name"]
    assert dynamic_route["task_name"] == "fast__authorized_kimi-k2-7-code"
    assert dynamic_route["agent_profile"] == str(profile_path)
    assert json.loads(dynamic_route["pricing_snapshot"])["currency"] == "CNY"

    revoked = command(
        str(FACTORY),
        "revoke",
        "--model",
        "kimi-k2.7-code",
        "--billing-channel",
        "kimi-api-standard",
        "--authority",
        "explicit-user",
        "--data-dir",
        str(data),
        env=env,
    )
    assert revoked.returncode == 0, revoked.stderr
    denied_after_revoke = command(
        str(DISPATCHER),
        "--workdir",
        str(another_project),
        "--task-name",
        "fast__revoked_kimi",
        "--task-file",
        str(contract),
        "--agent-profile",
        str(profile_path),
        "--data-dir",
        str(data),
        env=env,
    )
    assert denied_after_revoke.returncode != 0
    assert "absent or revoked" in denied_after_revoke.stderr


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        test_profiles_and_installer(root)
        test_project_grant(root)
        test_runtime_inspector(root)
        test_native_role_audit(root)
        test_external_route_audit(root)
    print("Goldilocks experiment 3 routing contract passed.")


if __name__ == "__main__":
    main()
