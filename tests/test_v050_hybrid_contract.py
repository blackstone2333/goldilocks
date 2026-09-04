#!/usr/bin/env python3

"""Retained routing/bootstrap contract after the retired Hook product surface."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILL = PLUGIN / "skills" / "goldilocks"

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def main() -> None:
    root = read(SKILL / "SKILL.md")
    routing = read(SKILL / "references" / "model-routing.md")
    bootstrap = read(PLUGIN / "skills" / "goldilocks-bootstrap" / "SKILL.md")
    profiles = json.loads(read(SKILL / "assets" / "codex-route-profiles.json"))["profiles"]
    assert "不提供或依赖 Hook" in root
    assert "ships no Hook feature, source, or trust path" in bootstrap
    assert not (PLUGIN / "hooks" / "hooks.json").exists()
    for marker in ("Spark XHigh Fast", "native Luna Max Fast", "Terra Medium Standard", "default to Direct", "complete known mutable execution chain"):
        assert marker in routing, marker
    assert profiles["goldilocks_spark_worker"]["reasoning_effort"] == "xhigh"
    assert profiles["goldilocks_luna_economy"]["reasoning_effort"] == "max"
    assert profiles["goldilocks_terra_engineer"]["reasoning_effort"] == "medium"
    result = subprocess.run([sys.executable, str(SKILL / "scripts" / "dispatch_codex_worker.py"), "--help"], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    for marker in ("terra-standard", "spark-coding", "max"):
        assert marker in result.stdout, marker
    print("Goldilocks retained routing/bootstrap no-Hook contract passed.")

if __name__ == "__main__":
    main()
