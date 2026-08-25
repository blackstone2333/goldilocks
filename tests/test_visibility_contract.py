#!/usr/bin/env python3

"""Regression contract for visible Goldilocks activation, events, and receipt."""

from __future__ import annotations

import json
import os
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
HOOK = PLUGIN / "scripts" / "recovery_reminder.py"
HOOKS = PLUGIN / "hooks" / "hooks.json"


def context(prompt: str, turn_id: str, *, usage_visibility: str | None = None) -> str:
    with tempfile.TemporaryDirectory() as temporary:
        data = Path(temporary) / "plugin-data"
        payload = {
            "session_id": "visibility-session",
            "turn_id": turn_id,
            "cwd": str(ROOT),
            "hook_event_name": "UserPromptSubmit",
            "prompt": prompt,
        }
        result = subprocess.run(
            [sys.executable, str(HOOK)],
            input=json.dumps(payload),
            text=True,
            capture_output=True,
            check=False,
            env={
                **os.environ,
                "PLUGIN_DATA": str(data),
                "GOLDILOCKS_USAGE_VISIBILITY": usage_visibility or "on-demand",
            },
        )
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def main() -> None:
    # A compact receipt is mandatory even for a Direct executable task.  The
    # user should not need to infer activation from whether a worker happened
    # to be dispatched.
    english = context("Implement the small parser fix and run its focused test.", "en-direct")
    for marker in (
        "Every executable",
        "Direct",
        "first work update",
        "Goldilocks | Active:",
        "already selected or observed",
        "exactly one localized visible Goldilocks route receipt",
        "ROUTE=direct",
        "DETAIL names the actual Goldilocks action",
        "host-side and fail-silent",
        "on-demand is the default",
        "Bootstrap automatic opt-in",
        "each executable task",
        "fast__<semantic>_<model>",
        "standard__<semantic>_<model>",
        "lead__<semantic>_<model>",
    ):
        assert marker in english, marker

    # The receipt and the unavailable fallback follow the user's language;
    # internal reason codes may remain machine-oriented elsewhere.
    chinese = context("修复这个小解析器问题，并运行对应的聚焦测试。", "zh-direct")
    for marker in (
        "每个可执行", "第一次工作更新", "Goldilocks｜已启用：", "已经选定或观察到", "有且仅有一次",
        "本地化", "用户可见", "回执", "路由=直接", "详情必须说明实际发生的 Goldilocks 动作", "用量",
        "默认按需", "明确索要", "Bootstrap 启用自动模式", "每个可执行任务自动读取一次",
    ):
        assert marker in chinese, marker

    # Conversation is explicitly exempt, rather than relying on the model to
    # guess whether the mandatory executable receipt should be omitted.
    conversation = context("你觉得这个架构思路怎么样？先讨论一下，不要修改。", "zh-chat")
    assert "纯对话不显示持久活动行、回执或用量" in conversation

    for model_instruction in ("usage_reporter.py", "codex plugin list"):
        assert model_instruction not in english
        assert model_instruction not in chinese

    explicit = context("Show my current token usage, please.", "usage-direct")
    assert explicit.count("usage_reporter.py") == 1
    assert explicit.count("codex plugin list --json") == 1
    assert "'--current','--turn-id','usage-direct'" in explicit
    assert "runpy.run_path" in explicit
    assert "plugin_root=" not in explicit
    assert "without retrying or debugging" in explicit

    explicit_chinese = context("请显示我本次的用量。", "usage-zh")
    assert explicit_chinese.count("usage_reporter.py") == 1
    assert explicit_chinese.count("codex plugin list --json") == 1
    assert "'--current','--turn-id','usage-zh','--language','zh'" in explicit_chinese

    terse_chinese = context("用量多少？", "usage-zh-terse")
    assert "'--current','--turn-id','usage-zh-terse','--language','zh'" in terse_chinese

    automatic = context(
        "Implement the small parser fix and run its focused test.", "auto-direct",
        usage_visibility="automatic",
    )
    assert automatic.count("Automatic visible Usage is enabled") == 1
    assert automatic.count("usage_reporter.py") == 1
    assert automatic.count("codex plugin list --json") == 1
    assert "'--current','--turn-id','auto-direct'" in automatic
    assert "without retrying or debugging" in automatic

    automatic_review = context(
        "Review the parser implementation and report any defects.", "auto-review",
        usage_visibility="automatic",
    )
    assert "'--current','--turn-id','auto-review'" in automatic_review

    automatic_translation = context(
        "Translate this paragraph into French.", "auto-translate",
        usage_visibility="automatic",
    )
    assert "'--current','--turn-id','auto-translate'" in automatic_translation

    on_demand_translation = context(
        "Please provide a translation of this paragraph.", "on-demand-translation"
    )
    assert "usage_reporter.py" not in on_demand_translation

    for prompt, turn_id in (
        ("Please provide a translation of this paragraph.", "auto-provide-translation"),
        ("Can you help with writing a customer email?", "auto-help-writing"),
        ("Please provide an analysis of these results.", "auto-provide-analysis"),
        ("请提供这段话的翻译。", "auto-zh-translation"),
        ("请帮我写一封客户邮件。", "auto-zh-writing"),
        ("请提供这组结果的分析。", "auto-zh-analysis"),
    ):
        automatic_request = context(prompt, turn_id, usage_visibility="automatic")
        assert f"'--current','--turn-id','{turn_id}'" in automatic_request

    # Representative executable-versus-conversation boundary: automatic mode
    # follows requested work families in both languages, not explanatory shape.
    for prompt, turn_id, expects_usage in (
        ("Summarize this report.", "auto-summarize", True),
        ("Search for the current API documentation.", "auto-search", True),
        ("Compare these two proposals.", "auto-compare", True),
        ("请总结这份报告。", "auto-zh-summarize", True),
        ("请搜索当前 API 文档。", "auto-zh-search", True),
        ("请比较这两个方案。", "auto-zh-compare", True),
        ("Review this patch.", "auto-review-patch", True),
        ("Explain how code review works.", "auto-explain-review", False),
        ("What are the benefits of code review?", "auto-review-benefits", False),
        ("I think peer review improves quality.", "auto-review-opinion", False),
        ("请解释代码审查如何工作。", "auto-zh-explain-review", False),
        ("代码审查有什么好处？", "auto-zh-review-benefits", False),
        ("我认为同行评审能提升质量。", "auto-zh-review-opinion", False),
        ("Explain this stack trace and fix the bug.", "auto-explain-fix", True),
        ("Explain this stack trace, fix the bug.", "auto-explain-comma-fix", True),
        ("Could you explain this stack trace, then fix the bug?", "auto-explain-then-fix", True),
        ("Describe the current config and compare it to the target.", "auto-describe-compare", True),
        ("请解释这个堆栈跟踪并修复该 bug。", "auto-zh-explain-fix", True),
        ("请解释这个堆栈跟踪，修复该 bug。", "auto-zh-explain-comma-fix", True),
        ("请解释这个堆栈跟踪；然后修复该 bug。", "auto-zh-explain-then-fix", True),
        ("请说明当前配置并与目标比较。", "auto-zh-describe-compare", True),
    ):
        automatic_request = context(prompt, turn_id, usage_visibility="automatic")
        assert ("usage_reporter.py" in automatic_request) is expects_usage

    automatic_chinese_writing = context(
        "请撰写一封简短的客户邮件。", "auto-zh-write",
        usage_visibility="automatic",
    )
    assert "'--current','--turn-id','auto-zh-write','--language','zh'" in automatic_chinese_writing

    # Execute the generated Unix command against an isolated fake plugin
    # registry. This catches quoting, dynamic source resolution, and argv drift
    # without consulting the user's real Codex installation.
    command_builder = runpy.run_path(str(HOOK))["usage_reporter_command"]
    if os.name != "nt":
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            fake_bin = root / "bin"
            fake_scripts = root / "plugin" / "scripts"
            fake_bin.mkdir()
            fake_scripts.mkdir(parents=True)
            codex = fake_bin / "codex"
            codex.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                f"print(json.dumps({{'installed':[{{'enabled':True,'name':'goldilocks','pluginId':'goldilocks@test','source':{{'path':{str(root / 'plugin')!r}}}}}]}}))\n",
                encoding="utf-8",
            )
            codex.chmod(0o755)
            (fake_scripts / "usage_reporter.py").write_text(
                "import json,sys\nprint(json.dumps(sys.argv[1:]))\n",
                encoding="utf-8",
            )
            executed = subprocess.run(
                command_builder("turn-123", True),
                shell=True,
                text=True,
                capture_output=True,
                check=False,
                env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}"},
            )
            assert executed.returncode == 0, executed.stderr
            assert json.loads(executed.stdout) == [
                "--current", "--turn-id", "turn-123", "--language", "zh"
            ]
    else:
        assert command_builder("turn-123", False).startswith('py -3 -c "')

    feature_discussion = context(
        "Should we enable automatic Usage in Bootstrap? Let's discuss the setting.",
        "auto-feature", usage_visibility="automatic",
    )
    assert "usage_reporter.py" not in feature_discussion
    assert "codex plugin list" not in feature_discussion

    automatic_chat = context(
        "What do you think about this architecture? Let's discuss it first.",
        "auto-chat", usage_visibility="automatic",
    )
    assert "usage_reporter.py" not in automatic_chat
    assert "codex plugin list" not in automatic_chat

    discussion_only = context(
        "What do you think about code review as a practice? Just discuss it.",
        "auto-discussion-only", usage_visibility="automatic",
    )
    assert "usage_reporter.py" not in discussion_only

    opinion_only = context(
        "Is code review a good practice?", "auto-opinion-only",
        usage_visibility="automatic",
    )
    assert "usage_reporter.py" not in opinion_only

    chinese_discussion_only = context(
        "你觉得代码审查这种实践怎么样？只讨论一下。", "auto-zh-discussion",
        usage_visibility="automatic",
    )
    assert "usage_reporter.py" not in chinese_discussion_only

    hooks = json.loads(HOOKS.read_text(encoding="utf-8"))["hooks"]
    submit = json.dumps(hooks["UserPromptSubmit"], ensure_ascii=False)
    assert "usage_reporter.py" in submit
    visible_hook_count = 0
    statuses: list[str] = []
    for event, groups in hooks.items():
        for group in groups:
            for hook in group.get("hooks", []):
                status = hook.get("statusMessage")
                assert status, f"{event} hook must visibly identify its Goldilocks activity"
                assert "Goldilocks" in status, f"{event} status must identify Goldilocks"
                statuses.append(status)
                visible_hook_count += 1
    assert visible_hook_count == 9
    assert any("Usage baseline" in status for status in statuses)
    assert any("Route candidate audit" in status for status in statuses)
    assert not any("Receipt audit" in status or "Acceptance" in status for status in statuses)

    print("Goldilocks visible Direct receipt and live Usage contract passed.")


if __name__ == "__main__":
    main()
