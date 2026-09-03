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
PROVE = ROOT / "plugins" / "goldilocks" / "skills" / "goldilocks" / "references" / "prove.md"
BUILD = ROOT / "plugins" / "goldilocks" / "skills" / "goldilocks" / "references" / "build.md"
DIAGNOSE = ROOT / "plugins" / "goldilocks" / "skills" / "goldilocks" / "references" / "diagnose.md"
ORCHESTRATE = ROOT / "plugins" / "goldilocks" / "skills" / "goldilocks" / "references" / "orchestrate.md"
ROUTE_CARD = ROOT / "plugins" / "goldilocks" / "skills" / "goldilocks" / "references" / "route-card.md"


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
    prove = PROVE.read_text(encoding="utf-8")
    build = BUILD.read_text(encoding="utf-8")
    diagnose = DIAGNOSE.read_text(encoding="utf-8")
    orchestrate = ORCHESTRATE.read_text(encoding="utf-8")
    route_card = ROUTE_CARD.read_text(encoding="utf-8")
    assert "[kernel.md](references/kernel.md)" in skill
    assert RECEIPT_EN in skill
    assert RECEIPT_ZH in skill
    for required in (
        "minimum-sufficient",
        "多个 ready units 但各自很小",
        "不只因多文件读 reference",
        "至少一条完整可转交",
        "不新增 hash/contract freeze/baseline/gate",
        "无相关变更不重跑已通过项",
        "产品修复后只重跑失败项与受影响项",
        "普通低风险改动不新增 hash/contract freeze/baseline/gate",
        "首次检查在一个工具调用内用存在性守卫",
        "`[ -f \"$f\" ]`",
        "读取现有 instructions/相关 source/tests",
        "读取项目元数据或 `python3 --version`",
        "不二次探测",
        "以声明或当前运行时为语法下限",
        "Python <3.10 禁止 `X | None`",
        "一个能传递失败状态的 evidence call",
        "probe 预期先推导",
        "tests/CLI 已导入变更时不再 compile",
        "错误 probe 只修 probe，不改产品、不追加等价 check",
        "一次权威 check 已给 decisive evidence 即停止",
        "不因谨慎重复等价 tests、换 interpreter 或跑 full matrix",
        "原因不明的连续失败转 diagnose",
        "既有 safeguards 不删",
    ):
        assert required in skill, required
    for required in (
        "Verification 用 minimum-sufficient",
        "不新增 hash、contract freeze、baseline 或 gate",
        "无相关变更不重跑已通过项",
        "产品 repair 后仅重跑失败项与受影响项",
        "普通 low-risk change 不新增 hash、contract freeze、baseline 或 gate",
        "首次检查在一个工具调用内用存在性守卫",
        "`[ -f \"$f\" ]`",
        "读取现有 instructions/相关 source/tests",
        "读取项目元数据或 `python3 --version`",
        "不二次 discovery",
        "以声明或当前运行时为语法下限",
        "Python <3.10 禁止 `X | None`",
        "一个能传递失败状态的 evidence call",
        "probe 预期先推导",
        "tests/CLI 已导入变更时不再 compile",
        "错误 probe 只修 probe，不改产品、不追加等价 check",
        "一次 authoritative check 已给 decisive evidence 即停止",
        "普通 low-risk change 不因谨慎重复等价 tests/checks、换 interpreter 或跑 full matrix",
        "原因不明的连续失败转 diagnose",
        "已有 safeguards 不删",
    ):
        assert required in kernel, required
    for text, required in (
        (kernel, "route_unavailable` 仅在本 turn 已保留 native/Adapter 实际启动失败证据时合法"),
        (orchestrate, "zero attempts or an unexecuted plan cannot use it"),
        (route_card, "zero attempts or an unexecuted plan must use the actual Direct reason instead"),
        (prove, "not rerunning an equivalent passing check for ceremony"),
        (prove, "otherwise it does not repeat an equivalent worker check"),
        (build, "at most one focused check when current evidence is absent"),
        (diagnose, "reused rather than repeated for “freshness”"),
    ):
        assert required in text, required
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
    routed = hook(
        "UserPromptSubmit",
        "请完成以下开发任务：\n1、实现 parser。\n2、实现 renderer。\n3、补齐 tests 并集成。",
    )
    compact = hook("PostCompact")
    for message, receipt in ((english, RECEIPT_EN), (chinese, RECEIPT_ZH), (compact, RECEIPT_EN)):
        assert receipt in message
        assert (
            "Pure conversation has no persistent activity cue, receipt, or Usage" in message
            or "纯对话不显示持久活动行、回执或用量" in message
        )
        for required in (
            "Minimum-sufficient verification",
            "in one first call",
            "`[ -f \"$f\" ]`",
            "instructions/relevant source/tests",
            "`python3 --version`",
            "no second discovery",
            "syntax floor",
            "Python <3.10: no `X | None`",
            "One fail-propagating evidence call",
            "one uncovered probe",
            "derive expectations first",
            "Skip compile when tests/CLI import changes",
            "no new hash/freeze/baseline/gate",
            "After product repair rerun only failed/affected checks",
            "fix faulty probes without product changes or equivalent checks",
            "Recurring unknowns mean diagnose, not retry",
            "Preserve safeguards",
        ):
            assert required in message, required
    assert "route_unavailable needs retained native/Adapter start-failure evidence" in routed
    assert "zero-attempt/plan-only uses the actual Direct reason" in routed
    assert "run one make-or-delegate check" in routed
    assert "Small files need no route-card/kernel" in routed
    assert "only if delegation may pay" in routed
    assert "Direct skips only goldilocks:goldilocks and its references" in english
    assert "task-matching domain Skills load normally" in english
    assert "implementation gain clearly exceeds briefing, review, and integration" in english
    assert "CONCURRENCY counts host-confirmed child starts" in english
    assert "none is 0, never 1 for the main model" in english
    assert "未启动子智能体就是 0" in chinese
    assert "绝不把主模型计为 1" in chinese
    for required in (
        "fast__<semantic>_<model>",
        "fork_turns=none",
        "standard__<semantic>_<model>",
        "none/1-4",
        "lead__<semantic>_<model>",
        "fresh review-only/no write/repair/delegate",
        "Host permissions stay unchanged",
        "only explicit Lead handoff permits `all`",
        "native hosts may bypass PreToolUse",
    ):
        assert required in routed, required

    print("Goldilocks 0.5.3-beta.9 compact contract passed.")


if __name__ == "__main__":
    main()
