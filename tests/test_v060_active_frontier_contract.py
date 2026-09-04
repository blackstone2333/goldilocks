#!/usr/bin/env python3
"""Contract for ACTIVE-only continuity with no Goldilocks compact prompt."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILL = PLUGIN / "skills" / "goldilocks"
BOOTSTRAP = PLUGIN / "skills" / "goldilocks-bootstrap"


def main() -> None:
    assert not (SKILL / "assets" / "codex-compact-prompt.md").exists()

    root_skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    continuity = (SKILL / "references" / "continuity.md").read_text(encoding="utf-8")
    lifecycle = (SKILL / "references" / "task-lifecycle.md").read_text(encoding="utf-8")
    bootstrap_skill = (BOOTSTRAP / "SKILL.md").read_text(encoding="utf-8")
    bootstrap_source = (BOOTSTRAP / "scripts" / "bootstrap.py").read_text(encoding="utf-8")

    assert "不覆盖宿主的 `compact_prompt`；ACTIVE 是唯一执行前沿" in root_skill
    assert "does not override the host's compaction prompt" in continuity
    assert "sole execution-state source of truth" in continuity
    assert "status: active" in lifecycle
    assert "session_id" in lifecycle
    assert "Mere file existence is never a recovery signal" in continuity

    assert "--context-lean" not in bootstrap_skill
    assert "--context-lean" not in bootstrap_source
    assert "compact_prompt_installed" not in bootstrap_source
    assert "never injects or changes a user compact prompt" in bootstrap_skill

    docs = (
        ROOT / "docs" / "installation.md",
        ROOT / "docs" / "installation.zh-CN.md",
        ROOT / "docs" / "AGENT-GUIDE.md",
    )
    for document in docs:
        content = document.read_text(encoding="utf-8")
        assert "--context-lean" not in content, document
    assert "does not install or override a global `compact_prompt`" in docs[0].read_text(encoding="utf-8")
    assert "不再安装或覆盖全局 `compact_prompt`" in docs[1].read_text(encoding="utf-8")

    print("Goldilocks 0.6.0 ACTIVE-only continuity contract passed.")


if __name__ == "__main__":
    main()
