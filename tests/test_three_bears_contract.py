#!/usr/bin/env python3

import importlib.util
import os
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "benchmarks" / "three_bears"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


for required in [
    BENCH / "README.md",
    BENCH / "__init__.py",
    BENCH / "tasks.py",
    BENCH / "run.py",
]:
    assert required.is_file(), f"missing {required.relative_to(ROOT)}"

tasks = load_module("three_bears_tasks", BENCH / "tasks.py")
runner = load_module("three_bears_run", BENCH / "run.py")

assert set(runner.ARMS) == {"baseline", "goldilocks", "superpowers", "ponytail", "grill"}
assert len(tasks.TASKS) == 9
assert Counter(task["level"] for task in tasks.TASKS.values()) == {
    "baby": 3,
    "mama": 3,
    "papa": 3,
}

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    source = root / "source.toml"
    source.write_text(
        'model_provider = "custom"\n'
        'service_tier = "priority"\n'
        '[model_providers.custom]\n'
        'name = "example"\n'
        'wire_api = "responses"\n'
        'requires_openai_auth = true\n'
        'base_url = "https://example.invalid/v1"\n'
        'experimental_bearer_token = "secret-value"\n'
        '[mcp_servers.should_not_copy]\n'
        'url = "https://example.invalid/mcp"\n',
        encoding="utf-8",
    )
    old_config = os.environ.get("THREE_BEARS_CODEX_CONFIG")
    os.environ["THREE_BEARS_CODEX_CONFIG"] = str(source)
    try:
        codex_home = runner.prepare_codex_home("baseline", root / "home")
    finally:
        if old_config is None:
            os.environ.pop("THREE_BEARS_CODEX_CONFIG", None)
        else:
            os.environ["THREE_BEARS_CODEX_CONFIG"] = old_config
    copied = (codex_home / "config.toml").read_text(encoding="utf-8")
    assert 'model_provider = "custom"' in copied
    assert '[model_providers.custom]' in copied
    assert 'experimental_bearer_token = "secret-value"' in copied
    assert "mcp_servers" not in copied
    assert oct((codex_home / "config.toml").stat().st_mode & 0o777) == "0o600"

required_fields = {
    "level",
    "track",
    "prompt",
    "seed",
    "allowed_changes",
    "axis",
    "good",
    "bad",
    "score",
}

for task_id, task in tasks.TASKS.items():
    assert task_id.startswith(("baby-", "mama-", "papa-"))
    assert required_fields <= task.keys(), f"{task_id} missing {required_fields - task.keys()}"
    assert task["track"] in {"build", "align"}
    assert task["axis"] in {"correct", "safe", "scope", "reuse", "process"}

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tasks.materialize(task_id, root)
        tasks.snapshot_repo(root)
        tasks.apply_reference(task_id, root, "good")
        good = tasks.score_task(task_id, root, task.get("good_final", ""))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        tasks.materialize(task_id, root)
        tasks.snapshot_repo(root)
        tasks.apply_reference(task_id, root, "bad")
        bad = tasks.score_task(task_id, root, task.get("bad_final", ""))

    for result in (good, bad):
        assert {"correct", "safe", "scope", "reuse", "process", "quality", "reason"} <= result.keys()

    assert good["quality"] == 1, f"{task_id} good reference failed: {good}"
    assert good[task["axis"]] == 1, f"{task_id} good reference missed axis"
    assert bad[task["axis"]] == 0, f"{task_id} bad reference escaped axis: {bad}"

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    tasks.materialize("papa-offline-design", root)
    tasks.snapshot_repo(root)
    conflict_frontier = (
        "The highest-impact unresolved decision is conflict ownership and the source of truth. "
        "I recommend keeping the server authoritative while preserving conflicting offline edits for explicit review. "
        "Should conflicts require explicit review, or should one side automatically win?"
    )
    assert tasks.score_task("papa-offline-design", root, conflict_frontier)["process"] == 1

    terse_default = (
        "The highest-impact decision is conflict ownership and the source of truth. "
        "Default: keep the server authoritative and hold overlapping offline edits for explicit review. "
        "Should conflicts require reviewer resolution, or should one side automatically win?"
    )
    assert tasks.score_task("papa-offline-design", root, terse_default)["process"] == 1

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    events = root / "events.jsonl"
    stderr = root / "stderr.txt"
    events.write_text(
        '{"type":"thread.started","thread_id":"t1"}\n'
        '{"type":"item.completed","item":{"type":"error","message":"unsupported model"}}\n'
        '{"type":"turn.failed","error":{"message":"HTTP 400"}}\n',
        encoding="utf-8",
    )
    stderr.write_text("", encoding="utf-8")
    failed = runner.parse_events(events, stderr)
    assert failed["turn_completed"] is False
    assert failed["tool_calls"] == 0
    assert any("unsupported model" in error for error in failed["errors"])

valid_record = {
    "level": "baby",
    "arm": "goldilocks",
    "turn_completed": True,
    "returncode": 0,
    "quality": 1,
    "safe": 1,
    "scope": 1,
    "reuse": 1,
    "process": 1,
    "total_tokens": 10,
}
invalid_record = {
    **valid_record,
    "turn_completed": False,
    "returncode": 1,
    "quality": 0,
    "total_tokens": 0,
    "errors": ["usage limit"],
}
row = next(
    row
    for row in runner.aggregate([valid_record, invalid_record])
    if row["level"] == "baby" and row["arm"] == "goldilocks"
)
assert row["n"] == 1
assert row["attempted"] == 2
assert row["infrastructure_failures"] == 1
assert row["quality_rate"] == 1
assert row["tokens_median"] == 10

print("Three Bears contract passed: 9 tasks, 5 arms, all reference instruments valid.")
