#!/usr/bin/env python3

"""Retained core package contract; Hook-era v0.3 checks are intentionally retired."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILLS = PLUGIN / "skills"

def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")

def main() -> None:
    codex = json.loads(read(PLUGIN / ".codex-plugin" / "plugin.json"))
    claude = json.loads(read(PLUGIN / ".claude-plugin" / "plugin.json"))
    assert codex["name"] == claude["name"] == "goldilocks"
    visible_skills = {path.parent.name for path in SKILLS.glob("*/SKILL.md")}
    assert {"goldilocks", "goldilocks-bootstrap", "goldilocks-diagnostics"} <= visible_skills
    root = read(SKILLS / "goldilocks" / "SKILL.md")
    bootstrap = read(SKILLS / "goldilocks-bootstrap" / "SKILL.md")
    assert "不提供或依赖 Hook" in root
    assert "ships no Hook feature, source, or trust path" in bootstrap
    assert not (PLUGIN / "hooks" / "hooks.json").exists()
    print("Goldilocks core no-Hook package contract passed.")

if __name__ == "__main__":
    main()
