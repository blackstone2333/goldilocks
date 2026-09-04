#!/usr/bin/env python3
"""Focused offline contract for the 0.6.0 three-arm harness."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "v060-beta1-three-arm-2026-09-04"
RUNNER = EVAL / "run.py"


def load_harness():
    spec = importlib.util.spec_from_file_location("beta1_three_arm", RUNNER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = load_harness()


def complete_protocol(arm: str) -> dict:
    protocol = {
        "source_frozen": True,
        **H.expected_protocol_hashes(),
        "runtime_identity_verified": True,
        "root_session_count": 1,
        "child_session_count": 0,
        "usage_deduplicated": True,
        "same_host": True,
        "same_toolset": True,
        "cold_context": True,
        "approval_policy": "never",
        "sandbox": "danger-full-access",
        "full_access": True,
    }
    if arm == "direct":
        protocol.update({
            "direct_pure": True,
            "plugin_identity_verified": False,
            "plugin_list_root_key": "installed",
            "goldilocks_plugin_ids": [],
            "isolated_skills_entries": [],
            "isolated_marketplace_entries": [],
            "compact_prompt_present": False,
            "prompt_input_goldilocks_mentions": 0,
        })
    else:
        protocol.update(
            {
                "direct_pure": False,
                "plugin_identity_verified": True,
                "source_sha256": f"frozen-{arm}",
            }
        )
    return protocol


def valid_cell(arm: str = "direct") -> dict:
    return {
        "schema_version": 1,
        "cell_id": f"cell-{arm}",
        "arm": arm,
        "version": H.EXPECTED_VERSIONS[arm],
        "runtime": {
            "model": "gpt-5.6-sol",
            "effort": "high",
            "service_tier": "standard",
        },
        "attempts": 1,
        "host_retries": 0,
        "returncode": 0,
        "wall_time_ms": 100,
        "completion": {"turn_completed": True},
        "quality": {
            "passed": True,
            "checks": [
                {
                    "kind": "hidden_acceptance",
                    "grader_sha256": H.expected_protocol_hashes()["grader_sha256"],
                    "passed": True,
                }
            ],
        },
        "telemetry": {
            "input_tokens": 100,
            "cached_input_tokens": 50,
            "cache_write_input_tokens": 10,
            "output_tokens": 10,
            "tool_calls": 1,
            "process_steps": 1,
            "verification_calls": 1,
            "duplicate_verification_calls": 0,
            "normalized_cost_usd": 999,
        },
        "route": {
            "selected": "direct",
            "child_starts": 0,
            "user_roundtrips": 0,
            "unnecessary_state_writes": 0,
            "workflow_documents_created": 0,
            "background_actions": 0,
        },
        "measurement": {
            "cost_comparable": True,
            "contamination": [],
            "pricing_provenance": H.PRICING_PROVENANCE,
        },
        "protocol": complete_protocol(arm),
        "errors": [],
        "synthetic": False,
    }


def normalized(raw: dict, root: Path):
    path = root / f"{raw['cell_id']}.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return H.load_cell(path, arm_hint=raw["arm"])


def test_classification_and_cost(root: Path) -> None:
    base = valid_cell()
    cell = normalized(base, root)
    row = H.classify_cell(cell)
    assert row["status"] == "eligible"
    # 40 uncached * 5 + 50 cached * .5 + 10 write * 6.25 + 10 output * 30.
    assert cell["telemetry"]["normalized_cost_usd"] == 0.0005875
    assert cell["telemetry"]["normalized_cost_usd"] != 999
    assert cell["telemetry"]["raw_tokens"] == 110

    no_write_partition = copy.deepcopy(base)
    no_write_partition["cell_id"] = "no-cache-write-partition"
    no_write_partition["telemetry"]["cache_write_input_tokens"] = None
    no_write_cell = normalized(no_write_partition, root)
    assert no_write_cell["telemetry"]["cache_write_input_tokens"] is None
    assert no_write_cell["telemetry"]["normalized_cost_usd"] is not None
    assert H.classify_cell(no_write_cell)["status"] == "eligible"

    missing = copy.deepcopy(base)
    missing["cell_id"] = "missing-telemetry"
    missing["telemetry"] = {}
    missing_row = H.classify_cell(normalized(missing, root))
    assert missing_row["status"] == "measurement_partial"
    assert missing_row["metrics"]["input_tokens"] is None
    assert missing_row["metrics"]["raw_tokens"] is None

    no_grader = copy.deepcopy(base)
    no_grader["cell_id"] = "no-grader"
    no_grader["quality"]["checks"] = []
    assert H.classify_cell(normalized(no_grader, root))["status"] == "evidence_gap"

    bad_quality = copy.deepcopy(base)
    bad_quality["cell_id"] = "quality-fail"
    bad_quality["quality"] = {"passed": False, "checks": []}
    bad_quality["telemetry"] = {}
    assert H.classify_cell(normalized(bad_quality, root))["status"] == "quality_failure"

    bad_protocol = copy.deepcopy(bad_quality)
    bad_protocol["cell_id"] = "protocol-first"
    bad_protocol["protocol"]["same_host"] = False
    assert H.classify_cell(normalized(bad_protocol, root))["status"] == "protocol_failure"

    infra = copy.deepcopy(bad_protocol)
    infra["cell_id"] = "infra-first"
    infra["failure_class"] = "infrastructure_invalid"
    infra["infrastructure_reason"] = "timeout"
    infra["completion"] = {"turn_completed": False}
    infra["returncode"] = 1
    infra["errors"] = ["runner timed out"]
    assert H.classify_cell(normalized(infra, root))["status"] == "infrastructure_failure"

    unclassified = copy.deepcopy(base)
    unclassified["cell_id"] = "unclassified"
    unclassified["completion"] = {"turn_completed": False}
    unclassified["returncode"] = 1
    unclassified["errors"] = ["a free-form timeout-looking message"]
    assert H.classify_cell(normalized(unclassified, root))["status"] == "evidence_gap"

    overlap = copy.deepcopy(base)
    overlap["cell_id"] = "overlapping-token-partitions"
    overlap["telemetry"]["cached_input_tokens"] = 90
    overlap["telemetry"]["cache_write_input_tokens"] = 20
    overlap_cell = normalized(overlap, root)
    assert overlap_cell["telemetry"]["token_partition_valid"] is False
    assert overlap_cell["telemetry"]["normalized_cost_usd"] is None
    assert H.classify_cell(overlap_cell)["status"] == "measurement_partial"

    contaminated = copy.deepcopy(base)
    contaminated["cell_id"] = "contaminated"
    contaminated["measurement"]["contamination"] = ["provider tier changed"]
    contaminated_cell = normalized(contaminated, root)
    assert contaminated_cell["telemetry"]["normalized_cost_usd"] is None
    assert H.classify_cell(contaminated_cell)["status"] == "measurement_partial"

    invalid_enum = copy.deepcopy(base)
    invalid_enum["cell_id"] = "invalid-enum"
    invalid_enum["failure_class"] = "transport"
    try:
        normalized(invalid_enum, root)
    except H.CellFormatError:
        pass
    else:
        raise AssertionError("unstructured/synonym failure_class was accepted")


def test_replacement_contract(root: Path) -> None:
    original_raw = valid_cell("v060_beta1")
    original_raw.update(
        {
            "cell_id": "original-infra",
            "failure_class": "infrastructure_invalid",
            "infrastructure_reason": "auth",
            "returncode": 1,
            "completion": {"turn_completed": False},
            "errors": ["auth pool unavailable"],
        }
    )
    replacement_raw = valid_cell("v060_beta1")
    replacement_raw.update(
        {
            "cell_id": "replacement-one",
            "retry_of": "original-infra",
            "replacement_index": 1,
            "replacement_authorized": True,
            "replacement_reason": "authorized replacement for structured auth failure",
        }
    )
    original = normalized(original_raw, root)
    replacement = normalized(replacement_raw, root)
    original["history_label"] = "original"
    replacement["history_label"] = "replacement"
    assert H.validate_replacement_chain([original, replacement])["valid"] is True

    same_id = copy.deepcopy(replacement)
    same_id["cell_id"] = original["cell_id"]
    assert H.validate_replacement_chain([original, same_id])["valid"] is False
    no_auth = copy.deepcopy(replacement)
    no_auth["replacement_authorized"] = False
    assert H.validate_replacement_chain([original, no_auth])["valid"] is False
    not_infra = copy.deepcopy(original)
    not_infra["failure_class"] = None
    not_infra["infrastructure_reason"] = None
    assert H.validate_replacement_chain([not_infra, replacement])["valid"] is False


def test_raw_events_cannot_be_overwritten(root: Path) -> None:
    cell_root = root / "raw-event-merge"
    cell_root.mkdir()
    events = cell_root / "events.jsonl"
    records = [
        {"type": "thread.started", "thread_id": "root-a"},
        {"type": "thread.started", "thread_id": "root-b"},
        {"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m unittest"}},
        {"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m unittest"}},
        {"type": "item.completed", "item": {"id": "edit-1", "type": "file_change", "changes": ["src/tag_index.py"]}},
        {"type": "item.completed", "item": {"id": "agent-1", "type": "collab_tool_call", "name": "spawn_agent", "arguments": {"task": "x"}}},
        {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 4, "output_tokens": 2}},
    ]
    events.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
    producer = valid_cell("direct")
    producer["cell_id"] = "raw-event-conflict"
    producer["events_file"] = "events.jsonl"
    producer["protocol"]["root_session_count"] = 1
    producer["telemetry"]["input_tokens"] = 999
    (cell_root / "cell.json").write_text(json.dumps(producer), encoding="utf-8")

    cell = H.load_cell(cell_root, arm_hint="direct")
    row = H.classify_cell(cell)
    assert cell["telemetry"]["input_tokens"] == 10
    assert cell["telemetry"]["tool_calls"] == 3
    assert cell["protocol"]["root_session_count"] == 2
    assert cell["protocol"]["valid"] is False
    assert cell["measurement"]["contamination"]
    assert row["status"] == "protocol_failure"
    assert row["quality_passed"] is None
    assert row["metrics"]["input_tokens"] is None
    assert row["observed"]["metrics"]["input_tokens"] == 10


def test_semantic_duplicate_verification(root: Path) -> None:
    events = root / "semantic-verification.jsonl"
    probe = """python3 - <<'PY'
from src.tag_index import merge_tags
result = merge_tags((" One ",), iter(["one", " TWO ", ""]))
assert result == ["One", "TWO"], result
print("iterator probe: ok")
PY"""
    records = [
        {"type": "item.completed", "item": {"id": "pre", "type": "command_execution", "command": "python3 -m unittest tests/test_tag_index.py && git status --short", "exit_code": 1}},
        {"type": "item.completed", "item": {"id": "edit", "type": "file_change", "changes": [{"path": "src/tag_index.py", "kind": "update"}]}},
        {"type": "item.completed", "item": {"id": "test-failed", "type": "command_execution", "command": "python -m unittest -v tests/test_tag_index.py", "exit_code": 127}},
        {"type": "item.completed", "item": {"id": "test-retry", "type": "command_execution", "command": "python3 -m unittest tests/test_tag_index.py", "exit_code": 0}},
        {"type": "item.completed", "item": {"id": "check-one", "type": "command_execution", "command": probe + "\ngit diff --check && git diff -- src/tag_index.py tests/test_tag_index.py && git status --short", "exit_code": 0}},
        {"type": "item.completed", "item": {"id": "check-two", "type": "command_execution", "command": "set -e\n" + probe + "\ngit diff --check\ngit diff -- src/tag_index.py tests/test_tag_index.py\ngit status --short", "exit_code": 0}},
    ]
    events.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")
    parsed = H.parse_events(events, arm="v060_beta1")
    # The pre-edit test/status are a different generation.  Within the final
    # generation the Python 127 -> python3 success is visible as one runner
    # recovery, not a duplicate. The second compound check repeats probe,
    # diff-check, diff, and status.
    assert parsed["telemetry"]["verification_calls"] == 12
    assert parsed["telemetry"]["verification_recovery_calls"] == 1
    assert parsed["telemetry"]["duplicate_verification_calls"] == 4


def test_offline_entrypoints(root: Path) -> None:
    check = H.preflight()
    assert check["passed"] is True
    assert check["formal_model_calls"] == 0
    assert check["host_credentials_read"] is False

    prepared = H.prepare_run(root / "prepared")
    assert prepared["passed"] is True
    assert prepared["formal_model_calls"] == 0
    lock = prepared["lock"]
    assert lock["runtime"]["model"] == "gpt-5.6-sol"
    assert lock["runtime"]["reasoning_effort"] == "high"
    assert lock["runtime"]["requested_service_tier"] == "standard"
    assert lock["control_fingerprint"]["sandbox"] == "danger-full-access"
    assert lock["control_fingerprint"]["approval_policy"] == "never"
    assert lock["control_fingerprint"]["automatic_host_retries"] == 0
    for arm in H.ARMS:
        roots = lock["cell_roots"][arm]
        assert Path(roots["repo"]).is_dir()
        assert Path(roots["codex_home"]).is_dir()
        assert not (Path(roots["codex_home"]) / "auth.json").exists()

    cli = subprocess.run(
        [sys.executable, str(RUNNER), "--preflight"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert cli.returncode == 0, cli.stderr
    assert json.loads(cli.stdout)["formal_model_calls"] == 0

    cli_prepare = subprocess.run(
        [sys.executable, str(RUNNER), "--prepare-run", str(root / "cli-prepared")],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert cli_prepare.returncode == 0, cli_prepare.stderr
    assert json.loads(cli_prepare.stdout)["formal_model_calls"] == 0


def main() -> None:
    fixture_rows = H.load_cells(EVAL / "fixtures")
    assert all(row["status"] == "eligible" for row in fixture_rows)
    fixture_report = H.build_report(
        fixture_rows, source="bundled synthetic fixtures", formal_model_calls=0
    )
    assert fixture_report["release_eligible"] is False
    assert fixture_report["evidence_grade"] == "offline-contract-fixture"

    with tempfile.TemporaryDirectory(prefix="goldilocks-beta1-contract-") as raw:
        root = Path(raw)
        test_classification_and_cost(root)
        test_replacement_contract(root)
        test_raw_events_cannot_be_overwritten(root)
        test_semantic_duplicate_verification(root)
        test_offline_entrypoints(root)
    print("Goldilocks 0.6.0 three-arm offline comparison contract passed.")


if __name__ == "__main__":
    main()
