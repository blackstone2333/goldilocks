#!/usr/bin/env python3

"""Guard the compact always-loaded contract and its compaction recovery."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "plugins" / "goldilocks" / "scripts" / "recovery_reminder.py"
SKILL = ROOT / "plugins" / "goldilocks" / "skills" / "goldilocks" / "SKILL.md"
KERNEL = ROOT / "plugins" / "goldilocks" / "skills" / "goldilocks" / "references" / "kernel.md"


RECEIPT_EN = (
    "ROUTE=<direct|fast|standard|mixed> | TEAM=<main model and actually started roles> | "
    "CONCURRENCY=<host-confirmed starts/host limit or ?> | DELEGATED=<actual delegated work or none> | "
    "REASON=<short reason> | DETAIL=<one factual sentence>"
)
RECEIPT_ZH = (
    "路由=<直接|快速|标准|混合>｜团队=<主模型及实际启动角色>｜并发=<宿主确认启动数/宿主上限或?>｜"
    "委派=<实际委派任务或无>｜理由=<简短理由>｜详情=<一句事实>"
)


def hook(event: str, prompt: str = "Build the feature.") -> str:
    payload = {
        "session_id": "compact-contract",
        "turn_id": "compact-turn",
        "cwd": str(ROOT),
        "hook_event_name": event,
    }
    if event == "UserPromptSubmit":
        payload["prompt"] = prompt
    result = subprocess.run(
        [sys.executable, str(HOOK)], input=json.dumps(payload), text=True, capture_output=True, check=False
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    return output.get("systemMessage") or output["hookSpecificOutput"]["additionalContext"]


def main() -> None:
    skill = SKILL.read_text(encoding="utf-8")
    kernel = KERNEL.read_text(encoding="utf-8")
    assert "[kernel.md](references/kernel.md)" in skill
    assert RECEIPT_EN in skill
    assert RECEIPT_ZH in skill
    for required in (
        "minimum-sufficient",
        "不新增 hash/contract freeze/baseline/gate",
        "无相关变更不重跑已通过项",
        "修复后只重跑失败项与受影响项",
        "原因不明的连续失败转 diagnose",
        "既有 safeguards 不删",
    ):
        assert required in skill, required
    for required in (
        "Verification 用 minimum-sufficient",
        "不新增 hash、contract freeze、baseline 或 gate",
        "无相关变更不重跑已通过项",
        "repair 后仅重跑失败项与受影响项",
        "原因不明的连续失败转 diagnose",
        "已有 safeguards 不删",
    ):
        assert required in kernel, required
    for required in (
        "Luna/Spark=`fast__<semantic>_<model>`",
        "Terra=`standard__<semantic>_<model>`",
        "Sol reviewer=`lead__<semantic>_<model>`",
        "Luna/Spark 固定 `fork_turns=none`",
        "Terra 仅 `none` 或 `1`–`4`",
        "Sol reviewer 固定 `none`、fresh review-only、不得 write/repair/delegate",
        "不修改或降低用户选择的宿主权限",
        "仅显式 Lead handoff 可用 `all`",
        "原生宿主可能绕过 PreToolUse，主模型每次 spawn 前自检",
    ):
        assert required in kernel, required

    english = hook("UserPromptSubmit")
    chinese = hook("UserPromptSubmit", "请修复这个功能。")
    compact = hook("PostCompact")
    for message, receipt in ((english, RECEIPT_EN), (chinese, RECEIPT_ZH), (compact, RECEIPT_EN)):
        assert receipt in message
        assert "Pure conversation has no receipt or Usage" in message or "纯对话不显示回执或用量" in message
        for required in (
            "Minimum-sufficient verification",
            "Add no hash/frozen contract/baseline/gate",
            "Without relevant change, do not rerun a pass",
            "after repair run only failed/affected checks",
            "diagnose, not retry",
            "Preserve safeguards",
        ):
            assert required in message, required
    for required in (
        "fast__<semantic>_<model>",
        "fork_turns=none",
        "standard__<semantic>_<model>",
        "none/1-4",
        "lead__<semantic>_<model>",
        "fresh review-only/no write/repair/delegate",
        "never changes user-selected host permissions",
        "only explicit Lead handoff permits `all`",
        "native hosts may bypass PreToolUse",
    ):
        assert required in english, required

    print("Goldilocks 0.5.3-beta.4 compact contract passed.")


if __name__ == "__main__":
    main()
