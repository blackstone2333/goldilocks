#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "plugins" / "goldilocks" / "scripts" / "sol_specialist_registry.py"
ROOT_THREAD = "00000000-0000-4000-8000-000000000001"


def run(data_dir: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REGISTRY), "--data-dir", str(data_dir), *args],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PLUGIN_DATA": str(data_dir)},
    )


def output(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def reserve(data_dir: Path, key: str, *, kind: str = "execution", target: str | None = None) -> dict[str, object]:
    command = [
        "reserve", "--origin-thread", ROOT_THREAD, "--parent-thread", ROOT_THREAD,
        "--request-key", key, "--task-name", f"lead__{key.replace('-', '_')}_sol", "--kind", kind,
        "--host-capability", "visible-sol",
    ]
    if target:
        command.extend(("--target-reservation", target))
    return output(run(data_dir, *command))


def test_registry_lifecycle_slots_receipts_and_idempotency(data_dir: Path) -> None:
    first = reserve(data_dir, "implementation")
    assert first["state"] == "reserved"
    assert first["slot"] == 1
    assert first["required_host_role"] == "visible_sol_specialist"
    assert first["required_model"] == "gpt-5.6-sol"
    assert first["required_effort"] == "high"
    assert first["receipt"]["origin_thread_id"] == ROOT_THREAD
    assert first["receipt"]["task_name"] == "lead__implementation_sol"

    replay = reserve(data_dir, "implementation")
    assert replay["reservation_id"] == first["reservation_id"]
    assert replay["idempotent"] is True
    conflicting_replay = run(
        data_dir, "reserve", "--origin-thread", ROOT_THREAD, "--parent-thread", ROOT_THREAD,
        "--request-key", "implementation", "--task-name", "lead__different_sol", "--kind", "execution",
        "--host-capability", "visible-sol",
    )
    assert conflicting_replay.returncode == 2
    assert "different Sol specialist contract" in conflicting_replay.stderr

    second = reserve(data_dir, "review", kind="audit", target=str(first["reservation_id"]))
    assert second["slot"] == 2
    assert second["kind"] == "audit"
    blocked = run(
        data_dir, "reserve", "--origin-thread", ROOT_THREAD, "--parent-thread", ROOT_THREAD,
        "--request-key", "third", "--task-name", "lead__third_sol", "--kind", "execution",
        "--host-capability", "visible-sol",
    )
    assert blocked.returncode == 2
    assert "two active" in blocked.stderr

    child = "00000000-0000-4000-8000-000000000101"
    attached = output(run(
        data_dir, "attach", "--reservation", str(first["reservation_id"]), "--child-thread", child,
        "--observed-parent-thread", ROOT_THREAD, "--host-role", "visible_sol_specialist",
        "--model", "gpt-5.6-sol", "--effort", "high",
    ))
    assert attached["state"] == "started"
    assert attached["receipt"]["child_thread_id"] == child
    wrong_identity_replay = run(
        data_dir, "attach", "--reservation", str(first["reservation_id"]), "--child-thread", child,
        "--observed-parent-thread", ROOT_THREAD, "--host-role", "goldilocks_sol_reviewer",
        "--model", "gpt-5.6-sol", "--effort", "high",
    )
    assert wrong_identity_replay.returncode == 2
    assert "required visible Sol specialist identity" in wrong_identity_replay.stderr
    terminal = output(run(
        data_dir, "complete", "--reservation", str(first["reservation_id"]), "--evidence", "focused test passed", "--return-state", "delivered", "--host-terminal", "confirmed",
    ))
    assert terminal["state"] == "completed"
    assert len(str(terminal["receipt"]["evidence_sha256"])) == 64

    released = reserve(data_dir, "replacement")
    assert released["slot"] == 2, "the terminal execution releases its original slot"
    repeat_complete = output(run(
        data_dir, "complete", "--reservation", str(first["reservation_id"]), "--evidence", "focused test passed", "--return-state", "delivered", "--host-terminal", "confirmed",
    ))
    assert repeat_complete["idempotent"] is True
    conflict = run(data_dir, "cancel", "--reservation", str(first["reservation_id"]), "--reason", "conflict")
    assert conflict.returncode == 2
    assert "terminal" in conflict.stderr


def test_capability_nesting_and_no_automatic_stale_release(data_dir: Path) -> None:
    unavailable = output(run(
        data_dir, "reserve", "--origin-thread", ROOT_THREAD, "--parent-thread", ROOT_THREAD,
        "--request-key", "unavailable", "--task-name", "lead__unavailable_sol", "--kind", "execution",
        "--host-capability", "unavailable",
    ))
    assert unavailable["state"] == "unavailable"
    assert unavailable["reservation_id"] is None

    parent = reserve(data_dir, "parent")
    sol_child = "00000000-0000-4000-8000-000000000201"
    output(run(
        data_dir, "attach", "--reservation", str(parent["reservation_id"]), "--child-thread", sol_child,
        "--observed-parent-thread", ROOT_THREAD, "--host-role", "visible_sol_specialist",
        "--model", "gpt-5.6-sol", "--effort", "high",
    ))
    nested = run(
        data_dir, "reserve", "--origin-thread", ROOT_THREAD, "--parent-thread", sol_child,
        "--request-key", "nested", "--task-name", "lead__nested_sol", "--kind", "execution",
        "--host-capability", "visible-sol",
    )
    assert nested.returncode == 2
    assert "cannot create another Sol" in nested.stderr

    status = output(run(data_dir, "status", "--origin-thread", ROOT_THREAD))
    assert status["active_count"] == 1, "started/idle work stays active without explicit terminal evidence"
    premature = run(data_dir, "cancel", "--reservation", str(parent["reservation_id"]), "--reason", "operator confirmed stale")
    assert premature.returncode == 2
    assert "host-terminal" in premature.stderr
    still_active = output(run(data_dir, "status", "--origin-thread", ROOT_THREAD))
    assert still_active["active_count"] == 1
    missing_return = run(
        data_dir, "cancel", "--reservation", str(parent["reservation_id"]),
        "--reason", "operator confirmed stale", "--host-terminal", "confirmed",
    )
    assert missing_return.returncode == 2
    assert "return-state delivered" in missing_return.stderr
    still_active = output(run(data_dir, "status", "--origin-thread", ROOT_THREAD))
    assert still_active["active_count"] == 1
    abandoned = output(run(
        data_dir, "cancel", "--reservation", str(parent["reservation_id"]), "--reason", "operator confirmed stale",
        "--host-terminal", "confirmed", "--return-state", "delivered",
    ))
    assert abandoned["state"] == "cancelled"
    replacement = reserve(data_dir, "after-cancel")
    assert replacement["slot"] == 1


def test_create_failure_and_audit_independence(data_dir: Path) -> None:
    execution = reserve(data_dir, "target")
    create_failed = output(run(
        data_dir, "fail", "--reservation", str(execution["reservation_id"]),
        "--reason", "host create failed",
    ))
    assert create_failed["state"] == "failed"
    assert create_failed["receipt"]["child_thread_id"] is None
    replacement = reserve(data_dir, "new-target")
    target_child = "00000000-0000-4000-8000-000000000301"
    output(run(
        data_dir, "attach", "--reservation", str(replacement["reservation_id"]), "--child-thread", target_child,
        "--observed-parent-thread", ROOT_THREAD, "--host-role", "visible_sol_specialist",
        "--model", "gpt-5.6-sol", "--effort", "high",
    ))
    audit_from_target = run(
        data_dir, "reserve", "--origin-thread", ROOT_THREAD, "--parent-thread", target_child,
        "--request-key", "bad-audit", "--task-name", "lead__bad_audit_sol", "--kind", "audit",
        "--target-reservation", str(replacement["reservation_id"]), "--host-capability", "visible-sol",
    )
    assert audit_from_target.returncode == 2
    assert "cannot create another Sol" in audit_from_target.stderr


def test_concurrent_reserves_never_exceed_two_slots(data_dir: Path) -> None:
    commands = []
    for number in range(3):
        commands.append(subprocess.Popen(
            [
                sys.executable, str(REGISTRY), "--data-dir", str(data_dir), "reserve",
                "--origin-thread", ROOT_THREAD, "--parent-thread", ROOT_THREAD,
                "--request-key", f"concurrent-{number}", "--task-name", f"lead__concurrent_{number}_sol",
                "--kind", "execution", "--host-capability", "visible-sol",
            ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env={**os.environ, "PLUGIN_DATA": str(data_dir)},
        ))
    results = [process.communicate() for process in commands]
    assert sum(1 for process in commands if process.returncode == 0) == 2, results
    assert sum(1 for stdout, stderr in results if "two active" in stderr) == 1, results
    current = output(run(data_dir, "status", "--origin-thread", ROOT_THREAD))
    assert current["active_count"] == 2


def test_root_audit_task_names_receipt_and_completion_return_gate(data_dir: Path) -> None:
    root_audit = reserve(data_dir, "root_audit", kind="audit")
    assert root_audit["receipt"]["target_reservation_id"] is None
    invalid_name = run(
        data_dir, "reserve", "--origin-thread", ROOT_THREAD, "--parent-thread", ROOT_THREAD,
        "--request-key", "invalid-name", "--task-name", "standard__not_sol_terra", "--kind", "execution",
        "--host-capability", "visible-sol",
    )
    assert invalid_name.returncode == 2
    assert "task name must" in invalid_name.stderr
    child = "00000000-0000-4000-8000-000000000401"
    output(run(
        data_dir, "attach", "--reservation", str(root_audit["reservation_id"]), "--child-thread", child,
        "--observed-parent-thread", ROOT_THREAD, "--host-role", "visible_sol_specialist",
        "--model", "gpt-5.6-sol", "--effort", "high",
    ))
    missing_return = run(
        data_dir, "complete", "--reservation", str(root_audit["reservation_id"]), "--evidence", "acceptance passed",
    )
    assert missing_return.returncode == 2
    complete = output(run(
        data_dir, "complete", "--reservation", str(root_audit["reservation_id"]), "--evidence", "acceptance passed",
        "--return-state", "delivered", "--host-terminal", "confirmed",
    ))
    assert complete["receipt"]["return_state"] == "delivered"
    stored = output(run(data_dir, "receipt", "--reservation", str(root_audit["reservation_id"])))
    assert stored == complete["receipt"]


def test_data_dir_fallback_requires_exactly_one_registry(data_dir: Path) -> None:
    home = data_dir / "home"
    absent = subprocess.run(
        [sys.executable, str(REGISTRY), "status", "--origin-thread", ROOT_THREAD],
        text=True, capture_output=True, check=False,
        env={**os.environ, "HOME": str(home), "PLUGIN_DATA": ""},
    )
    assert absent.returncode == 2
    fallback = home / ".codex" / "plugins" / "data" / "goldilocks-only"
    fallback.mkdir(parents=True)
    fresh = subprocess.run(
        [sys.executable, str(REGISTRY), "status", "--origin-thread", ROOT_THREAD],
        text=True, capture_output=True, check=False,
        env={**os.environ, "HOME": str(home), "PLUGIN_DATA": ""},
    )
    assert fresh.returncode == 0, fresh.stderr
    assert (fallback / "orchestration.db").is_file()


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        test_registry_lifecycle_slots_receipts_and_idempotency(Path(temporary) / "lifecycle")
    with tempfile.TemporaryDirectory() as temporary:
        test_capability_nesting_and_no_automatic_stale_release(Path(temporary) / "stale")
    with tempfile.TemporaryDirectory() as temporary:
        test_create_failure_and_audit_independence(Path(temporary) / "audit")
    with tempfile.TemporaryDirectory() as temporary:
        test_concurrent_reserves_never_exceed_two_slots(Path(temporary) / "concurrent")
    with tempfile.TemporaryDirectory() as temporary:
        test_root_audit_task_names_receipt_and_completion_return_gate(Path(temporary) / "contract")
    with tempfile.TemporaryDirectory() as temporary:
        test_data_dir_fallback_requires_exactly_one_registry(Path(temporary) / "fallback")


if __name__ == "__main__":
    main()
