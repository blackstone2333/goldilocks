#!/usr/bin/env python3
"""Offline contract for the authorized v0.6.0 CLI producer."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL = ROOT / "evals" / "v060-beta1-three-arm-2026-09-04"
RUNNER = EVAL / "execute.py"


spec = importlib.util.spec_from_file_location("beta1_cli_runner", RUNNER)
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="goldilocks-beta1-runner-") as raw:
        root = Path(raw)
        home, codex_home = root / "home", root / "codex_home"
        home.mkdir()
        codex_home.mkdir()
        # This is deliberately fake test material; cleanup must erase both the
        # auth-shaped file and provider config without reading their contents.
        (codex_home / "auth.json").write_text('{"token":"fake"}', encoding="utf-8")
        (codex_home / "config.toml").write_text('experimental_bearer_token="fake"', encoding="utf-8")
        M._cleanup_sensitive_home(codex_home)
        assert codex_home.is_dir() and list(codex_home.iterdir()) == []

        text = M._as_text(b"timeout bytes")
        assert text == "timeout bytes"
        events = root / "events.jsonl"
        events.write_text(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 4}}) + "\n", encoding="utf-8")
        observed = M._event_summary(events)
        assert observed["usage"]["input_tokens"] == 4
        assert "cache_write_input_tokens" not in observed["usage"]
        # Ordinary model prose must not become a false delegation/background
        # receipt merely because it mentions those words.
        events.write_text(
            "\n".join(
                [
                    json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "a subagent can run in background"}}),
                    json.dumps({"type": "item.completed", "item": {"type": "collab_tool_call"}}),
                    json.dumps({"type": "background_action"}),
                ]
            ) + "\n",
            encoding="utf-8",
        )
        assert M._structured_route_actions(events) == (1, 1)
        command = M._command_for(root, "task")
        assert "--ephemeral" in command
        assert "danger-full-access" in command
        assert 'approval_policy="never"' in command
        assert 'model_reasoning_effort="high"' in command
        assert "gpt-5.6-sol" in command

        # A path named goldilocks and Codex's host-owned .system bundle are
        # not workflow evidence.  A semantic $goldilocks instruction is.
        audit = root / "audit"
        audit.mkdir()
        (codex_home / "skills").mkdir()
        (codex_home / "skills" / ".system").mkdir()
        original_run = M._run
        prompt = json.dumps([{"content": [{"text": f"skill root: {root}/goldilocks/skills/.system"}]}])
        def fake_run(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, '{"installed": []}', "") if "plugin" in command else subprocess.CompletedProcess(command, 0, prompt, "")
        M._run = fake_run
        try:
            purity = M._direct_purity(env={}, cwd=root, codex_home=codex_home, audit=audit)
        finally:
            M._run = original_run
        assert purity["direct_pure"] is True
        summary = (audit / "prompt-structure.json").read_text(encoding="utf-8")
        assert "goldilocks/skills/.system" not in summary
        assert json.loads(summary)["total_text_chars"] > 0
        # Both released catalog descriptions count by their structured Skill
        # list entry; a filesystem path does not.
        beta1 = M._prompt_structure(json.dumps([{"content": [{"text": "- goldilocks:goldilocks: Use for material ambiguity."}]}]))
        beta9 = M._prompt_structure(json.dumps([{"content": [{"text": "- goldilocks:goldilocks: Adaptive orchestration and continuity."}]}]))
        path_only = M._prompt_structure(json.dumps([{"content": [{"text": "/tmp/goldilocks/skills/goldilocks/SKILL.md"}]}]))
        assert beta1["goldilocks_catalog_description_count"] == 1
        assert beta9["goldilocks_catalog_description_count"] == 1
        assert path_only["goldilocks_catalog_description_count"] == 0

        for arm in ("v053_beta9", "v060_beta1", "direct"):
            (root / "cells" / arm).mkdir(parents=True, exist_ok=True)
        for arm in ("v053_beta9", "v060_beta1"):
            (root / "cells" / arm / "cell.json").write_text("{}", encoding="utf-8")
        direct = root / "cells" / "direct"
        (direct / "events").mkdir()
        (direct / "audit").mkdir()
        original = {"cell_id": "direct:setup-failure", "attempts": 0, "failure_class": "infrastructure_invalid", "runner": {"model_request_started": False}}
        (direct / "cell.json").write_text(json.dumps(original), encoding="utf-8")
        assert M._prepare_direct_replacement({}, root) == "direct:setup-failure"
        assert (direct / "original" / "cell.json").is_file()
        assert (direct / "events").is_dir() and (direct / "audit").is_dir()
        chain = [
            {"history_label": "original", "failure_class": "infrastructure_invalid", "attempts": 0, "host_retries": 0, "protocol": {}, "replacement_of": None, "retry_of": None, "replacement_index": None, "replacement_authorized": None, "replacement_reason": None, "infrastructure_reason": "host", "cell_id": "direct:setup-failure", "cell_id_supplied": True},
            {"history_label": "replacement", "failure_class": None, "attempts": 1, "host_retries": 0, "replacement_of": "direct:setup-failure", "retry_of": "direct:setup-failure", "replacement_index": 1, "replacement_authorized": True, "replacement_reason": "authorized replacement", "cell_id": "direct:replacement-1", "cell_id_supplied": True},
        ]
        assert M.H.validate_replacement_chain(chain)["valid"] is True

    source = RUNNER.read_text(encoding="utf-8")
    assert "goldilocks@goldilocks-local" in source
    assert "request_max_retries = 0" in source
    assert "stream_max_retries = 0" in source
    assert "unbounded_connection_retries = false" in source
    assert "goldilocks@goldilocks-local" in source
    assert 'audit / "plugin-list.json"' in source
    assert 'audit / "prompt-structure.json"' in source
    # A command returning rc=0 with no installed Goldilocks record is not
    # identity evidence and must stop before any model request.
    try:
        M._verify_installed_plugin(
            "v060_beta1", {"source": "/not-used-before-empty-check", "source_sha256": "x"},
            {"installed": []},
        )
    except M.RunnerError:
        pass
    else:
        raise AssertionError("empty successful plugin list was accepted as identity evidence")
    print("Goldilocks beta1 three-arm CLI runner contract passed.")


if __name__ == "__main__":
    main()
