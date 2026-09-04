#!/usr/bin/env python3
"""Contract for v0.6.1's natural in-flight steering behavior."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "plugins" / "goldilocks" / "skills" / "goldilocks"


def main() -> None:
    root_skill = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    lifecycle = (SKILL / "references" / "task-lifecycle.md").read_text(encoding="utf-8")
    continuity = (SKILL / "references" / "continuity.md").read_text(encoding="utf-8")
    kernel = (SKILL / "references" / "kernel.md").read_text(encoding="utf-8")
    active_template = (SKILL / "assets" / "active-task.md").read_text(encoding="utf-8")

    # New work aligns before routing; it does not share the in-flight path.
    assert "新任务先完成需求对齐，再选择记录、计划和路由" in root_skill
    assert "执行中的插话与新任务分开" in root_skill
    assert "Routing never precedes alignment" in lifecycle

    # In-flight text receives one semantic materiality judgment, not a keyword
    # protocol.  A harmless interruption returns to the exact current frontier.
    assert "只判断一次是否实质影响当前目标、范围、顺序、权限、验收或返回点" in root_skill
    assert "does **not** pass through a fixed keyword taxonomy" in lifecycle
    assert "answer the simple question or absorb the useful information, then return to the exact prior execution position" in lifecycle
    assert "pause, stop, change, strengthen, or re-plan" in lifecycle
    assert "ask one focused question with a recommended interpretation" in lifecycle
    assert "not a required vocabulary list" in lifecycle
    assert "ADD / REPLACE / CANCEL / QUESTION" not in active_template
    assert "Material steering ledger" in active_template

    # Only material steering that has to survive a boundary enters ACTIVE.
    assert "simple in-flight answer" in continuity
    assert "Record only a material effect that must survive a boundary" in continuity
    assert "实质插话的返回点否则会丢失时" in kernel
    assert "简单插话或短 Direct 不建" in kernel

    print("Goldilocks v0.6.1 runtime steering contract passed.")


if __name__ == "__main__":
    main()
