#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
INSTALLER = PLUGIN / "scripts" / "install_agents.py"
GRANT = PLUGIN / "scripts" / "project_delegation.py"
INSPECTOR = PLUGIN / "scripts" / "inspect_agent_runtime.py"
GUARD = PLUGIN / "scripts" / "agent_routing_guard.py"
RECORDER = PLUGIN / "scripts" / "record_routing_outcome.py"
DISPATCHER = PLUGIN / "skills" / "goldilocks" / "scripts" / "dispatch_codex_worker.py"
PROFILES = PLUGIN / "skills" / "goldilocks" / "assets" / "codex-route-profiles.json"
TERRA = "gpt-5.6-terra"


def command(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


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
    profiles = json.loads(PROFILES.read_text(encoding="utf-8"))["profiles"]
    assert profiles["goldilocks_spark_coder"]["transport"] == "codex-exec"
    assert profiles["goldilocks_spark_coder"]["model"] == "gpt-5.3-codex-spark"
    assert profiles["goldilocks_luna_worker"]["transport"] == "codex-exec"
    assert profiles["goldilocks_terra_engineer"]["transport"] == "native"
    assert profiles["goldilocks_terra_engineer"]["may_delegate"] is True
    assert profiles["goldilocks_sol_reviewer"]["sandbox"] == "read-only"

    target = root / "agents"
    missing = command(str(INSTALLER), "--target-dir", str(target), "--check")
    assert missing.returncode != 0
    installed = command(str(INSTALLER), "--target-dir", str(target), "--json")
    assert installed.returncode == 0, installed.stderr
    result = json.loads(installed.stdout)
    assert result["status"] == "installed"
    assert len(result["installed"]) == 2
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
                "effort": "high",
                "sandbox_policy": {"type": "danger-full-access"},
                "permission_profile": {"type": "disabled"},
                "cwd": "/fixture",
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
    assert result["model"] == TERRA and result["effort"] == "high"
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
                "reasoning_effort": "high",
                "message": "Implement the bounded domain and report evidence.",
            },
        },
    )
    assert planned.returncode == 0, planned.stderr
    update = json.loads(planned.stdout)["hookSpecificOutput"]["updatedInput"]
    assert update["agent_type"] == "goldilocks_terra_engineer"
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
            "reasoning_effort": "high",
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
    assert decision["expected_effort"] == "high"
    assert execution["actual_agent_type"] == "goldilocks_terra_engineer"
    assert execution["actual_effort"] == "high"
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
            "UPDATE executions SET actual_effort = 'high', permission_profile_type = NULL "
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
            "agent_path": "/root/standard__observed_route",
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
    assert observed_decision["task_name"] == "standard__observed_route"
    assert observed_decision["expected_agent_type"] == "goldilocks_terra_engineer"
    assert observed_decision["expected_effort"] == "high"
    assert observed_execution["correlation_confidence"] == "role_observed"


def test_external_route_audit(root: Path) -> None:
    source_home = root / "source-home"
    codex_home = source_home / ".codex"
    codex_home.mkdir(parents=True)
    (codex_home / "auth.json").write_text("{}\n", encoding="utf-8")
    (codex_home / "models_cache.json").write_text('{"models":[]}\n', encoding="utf-8")
    (codex_home / "config.toml").write_text("", encoding="utf-8")
    fake = root / "fake-codex"
    fake.write_text(
        """#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
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
print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'ROUTE_OK_SPARK'}}))
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
    assert route["expected_model"] == "gpt-5.3-codex-spark"
    assert route["actual_model"] == route["expected_model"]
    assert route["actual_effort"] == "medium"
    assert route["status"] == "succeeded"
    assert route["route_id"] == summary["route_id"]
    assert route["child_thread_id"] == summary["thread_id"]
    assert route["parent_session_id"] == "parent-experiment-thread"
    assert route["input_tokens"] == 30 and route["output_tokens"] == 5
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
