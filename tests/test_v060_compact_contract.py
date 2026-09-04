#!/usr/bin/env python3
"""Contract for the compact Goldilocks 0.6.0 no-Hook package."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"

def main() -> None:
    skill_path = PLUGIN / "skills" / "goldilocks" / "SKILL.md"
    skill = skill_path.read_text(encoding="utf-8")
    kernel = (PLUGIN / "skills" / "goldilocks" / "references" / "kernel.md").read_text(encoding="utf-8")
    continuity = (PLUGIN / "skills" / "goldilocks" / "references" / "continuity.md").read_text(encoding="utf-8")
    lifecycle = (PLUGIN / "skills" / "goldilocks" / "references" / "task-lifecycle.md").read_text(encoding="utf-8")
    active_path = PLUGIN / "skills" / "goldilocks" / "assets" / "active-task.md"
    active = active_path.read_text(encoding="utf-8")
    frontmatter = skill.split("---", 2)[1]
    assert len(skill_path.read_bytes()) <= 5200
    assert "Clear routine Direct" in frontmatter
    assert "do not load this skill" in frontmatter
    assert "for executable work;" not in frontmatter
    assert "不提供或依赖 Hook" in skill
    assert "ROUTE=<direct|fast|standard|mixed>" in skill
    assert "minimum-sufficient" in skill
    assert "只有当前 tests 未覆盖" in skill
    assert "一个未覆盖 probe" not in skill
    assert "一个 focused uncovered-surface probe" not in kernel
    assert "产品修复后只重跑失败项与受影响项" in skill
    assert "不得重复已通过且未受影响的 tests 或重复 diff/status" in skill
    assert "不得重跑已通过 tests 或重复 diff/status" in kernel
    assert "safeguards" in kernel.lower()
    assert not (PLUGIN / "hooks" / "hooks.json").exists()
    assert not (PLUGIN / "skills" / "goldilocks" / "assets" / "codex-compact-prompt.md").exists()

    # ACTIVE is an event-triggered execution frontier, not an always-loaded
    # history file.  Keep the negative cases explicit now that no Hook/runtime
    # resolver exists to enforce them before the model sees a prompt.
    assert "Do not discover or read `ACTIVE.md` merely because it exists" in lifecycle
    assert "`status: active`" in lifecycle
    assert "host `session_id` match" in lifecycle
    assert "inspect frontmatter/size first" in lifecycle
    assert "Mere file existence is never a recovery signal" in continuity
    assert "Without an exact session match, do not recover" in continuity
    assert "a new task or ordinary prompt must not read stale ACTIVE" in continuity
    assert "文件仅存在不得触发读取" in kernel
    assert "`session_id` 精确匹配" in kernel

    assert len(active_path.read_bytes()) <= 4096
    assert len(active.splitlines()) <= 100
    for field in ("status:", "worktree:", "branch:", "session_id:"):
        assert field in active, field
    assert "Exact next action" in active
    assert "Do not repeat" in active
    print("Goldilocks compact no-Hook and ACTIVE continuity contract passed.")

if __name__ == "__main__":
    main()
