#!/usr/bin/env python3

from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILL = PLUGIN / "skills" / "goldilocks"
CURRENT_VERSION = "0.5.1"
CORRECTED_RESULTS = (
    ROOT
    / "benchmarks"
    / "data"
    / "v050-release-matrix.json"
)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def signed_percent(baseline: float, control: float) -> str:
    change = (baseline - control) / control * 100
    return ("+" if change >= 0 else "−") + f"{abs(change):.2f}%"


def metric_pair(baseline: float, control: float, unit: str = "") -> str:
    suffix = f" {unit}" if unit else ""
    return f"{baseline:,.3f} / {control:,.3f}{suffix}; **{signed_percent(baseline, control)}**"


def cost_pair(baseline: float, control: float) -> str:
    return f"${baseline:.6f} / ${control:.6f}; **{signed_percent(baseline, control)}**"


def token_pair(baseline: int, control: int) -> str:
    return f"{baseline:,} / {control:,}; **{signed_percent(baseline, control)}**"


def chinese_metric(value: str) -> str:
    return value.replace("; **", "；**")


def assert_release_matrix_table() -> None:
    evidence = json.loads(read(CORRECTED_RESULTS))
    summaries = evidence["arm_summaries"]
    baseline_arm = "goldilocks-v050"
    controls = ("direct", "goldilocks-v042", "superpowers-assisted")
    tasks = ("direct_control", "doc_handoff", "parallel_units")
    corrected_arms = {item["arm"] for item in evidence["corrections"]}

    def aggregate(arm: str) -> dict[str, float | int]:
        records = summaries[arm]["tasks"]
        assert all(
            records[task]["quality_gate_passed"]
            and records[task]["completion_state"] == "completed"
            for task in tasks
        ), arm
        return {
            "quality": len(tasks),
            "duration_seconds": sum(records[task]["duration_seconds"] for task in tasks),
            "raw_total_tokens": sum(records[task]["raw_total_tokens"] for task in tasks),
            "normalized_usd": sum(records[task]["normalized_usd"] for task in tasks),
        }

    aggregates = {arm: aggregate(arm) for arm in (baseline_arm, *controls)}
    english = read(ROOT / "benchmarks" / "V050-RELEASE-EVIDENCE.md")
    chinese = read(ROOT / "benchmarks" / "V050-RELEASE-EVIDENCE.zh-CN.md")
    agent_guide = read(ROOT / "docs" / "AGENT-GUIDE.md")
    human_english = read(ROOT / "README.md")
    human_chinese = read(ROOT / "README.zh-CN.md")
    arm_labels = {
        "direct": "Direct",
        "goldilocks-v042": "Goldilocks 0.4.2",
        "superpowers-assisted": "Superpowers 6.1.1",
    }
    task_labels = {
        "direct_control": ("Compact control", "紧凑控制"),
        "doc_handoff": ("Document handoff", "文档交接"),
        "parallel_units": ("Parallel units", "并行单元"),
    }

    def quality(arm: str, *, aggregate_row: bool, chinese_row: bool) -> str:
        passed = str(aggregates[arm]["quality"]) + "/" + str(len(tasks)) if aggregate_row else ("通过" if chinese_row else "Pass")
        return passed + ("*" if arm in corrected_arms else "")

    base_aggregate = aggregates[baseline_arm]
    for control in controls:
        control_aggregate = aggregates[control]
        time = metric_pair(float(base_aggregate["duration_seconds"]), float(control_aggregate["duration_seconds"]), "s")
        tokens = token_pair(int(base_aggregate["raw_total_tokens"]), int(control_aggregate["raw_total_tokens"]))
        cost = cost_pair(float(base_aggregate["normalized_usd"]), float(control_aggregate["normalized_usd"]))
        english_line = (
            f"| **Aggregate (three tasks)** | **{arm_labels[control]}** | "
            f"**{quality(baseline_arm, aggregate_row=True, chinese_row=False)} / {quality(control, aggregate_row=True, chinese_row=False)}** | "
            f"{time} | {tokens} | {cost} |"
        )
        chinese_line = (
            f"| **综合（三项累计）** | **{arm_labels[control]}** | "
            f"**{quality(baseline_arm, aggregate_row=True, chinese_row=True)} / {quality(control, aggregate_row=True, chinese_row=True)}** | "
            f"{chinese_metric(time)} | {chinese_metric(tokens)} | {chinese_metric(cost)} |"
        )
        assert english_line in english, english_line
        assert chinese_line in chinese, chinese_line
        assert english_line.replace("**", "") in agent_guide, english_line
        assert english_line in human_english, english_line
        assert chinese_line in human_chinese, chinese_line

    for task in tasks:
        baseline = summaries[baseline_arm]["tasks"][task]
        for control in controls:
            comparator = summaries[control]["tasks"][task]
            assert baseline["quality_gate_passed"] and comparator["quality_gate_passed"]
            time = metric_pair(baseline["duration_seconds"], comparator["duration_seconds"], "s")
            tokens = token_pair(baseline["raw_total_tokens"], comparator["raw_total_tokens"])
            cost = cost_pair(baseline["normalized_usd"], comparator["normalized_usd"])
            english_line = (
                f"| {task_labels[task][0]} | {arm_labels[control]} | "
                f"{quality(baseline_arm, aggregate_row=False, chinese_row=False)} / {quality(control, aggregate_row=False, chinese_row=False)} | "
                f"{time} | {tokens} | {cost} |"
            )
            chinese_line = (
                f"| {task_labels[task][1]} | {arm_labels[control]} | "
                f"{quality(baseline_arm, aggregate_row=False, chinese_row=True)} / {quality(control, aggregate_row=False, chinese_row=True)} | "
                f"{chinese_metric(time)} | {chinese_metric(tokens)} | {chinese_metric(cost)} |"
            )
            assert english_line in english, english_line
            assert chinese_line in chinese, chinese_line
            assert english_line.replace("**", "") in agent_guide, english_line
            assert english_line in human_english, english_line
            assert chinese_line in human_chinese, chinese_line

    chart_specs = (
        (
            ROOT / "docs" / "assets" / "v050-release-comparison.svg",
            "value / column max",
        ),
        (
            ROOT / "docs" / "assets" / "v050-release-comparison.zh-CN.svg",
            "value / column max",
        ),
    )
    for chart_path, scale_marker in chart_specs:
        ET.parse(chart_path)
        chart = read(chart_path)
        assert "%" not in chart, chart_path
        for arm in (baseline_arm, *controls):
            aggregate = aggregates[arm]
            for expected in (
                f"{float(aggregate['duration_seconds']):,.3f} s",
                f"{int(aggregate['raw_total_tokens']):,}",
                f"${float(aggregate['normalized_usd']):.6f}",
            ):
                assert expected in chart, (chart_path, arm, expected)
        for marker in (
            "Goldilocks v0.5.0",
            "Goldilocks v0.4.2",
            "Direct",
            "Superpowers 6.1.1",
            "Luna-equivalent proxy",
            'class="surface"',
            scale_marker,
        ):
            assert marker in chart, (chart_path, marker)
        assert "log10(" not in chart, chart_path

    assert "docs/assets/v050-release-comparison.svg" in human_english
    assert "docs/assets/v050-release-comparison.zh-CN.svg" in human_chinese

    night_shift_markers = (
        "1,275.764",
        "249.043",
        "$0.122976",
        "$0.212937",
        "5.12",
        "42.25%",
        "official-price proxy",
        "benchmarks/TERRA-LUNA-EFFORT-EVIDENCE.md",
    )
    for document in (human_english, agent_guide):
        for marker in night_shift_markers:
            assert marker in document, marker
    for marker in (
        "1,275.764",
        "249.043",
        "$0.122976",
        "$0.212937",
        "5.12",
        "42.25%",
        "价格代理估算",
        "不是实际账单",
        "benchmarks/TERRA-LUNA-EFFORT-EVIDENCE.zh-CN.md",
    ):
        assert marker in human_chinese, marker

    for document, caveats in (
        (english, ("Spark has no public numeric price", "not an actual bill")),
        (chinese, ("Spark 没有公开的数值费率", "不是实际账单")),
        (agent_guide, ("Spark has no public numeric rate", "not an actual bill")),
    ):
        for caveat in caveats:
            assert caveat in document, caveat


def main() -> None:
    codex_manifest = json.loads(read(PLUGIN / ".codex-plugin" / "plugin.json"))
    claude_manifest = json.loads(read(PLUGIN / ".claude-plugin" / "plugin.json"))
    assert codex_manifest["version"] == CURRENT_VERSION
    assert claude_manifest["version"] == CURRENT_VERSION

    root = read(SKILL / "SKILL.md")
    for marker in (
        "Standard owns one complete mutable chain",
        "Fast receives a complete fixed leaf contract",
        "one ordinary repair plus re-verification",
        "one proportional final acceptance",
        "does not duplicate owner exploration",
        "model-routing.md",
    ):
        assert marker in root, marker
    assert "bootstrap" not in root.lower()

    bootstrap = read(PLUGIN / "skills" / "goldilocks-bootstrap" / "SKILL.md")
    for marker in ("installing, upgrading, or repairing", "ordinary tasks", "scripts/bootstrap.py"):
        assert marker in bootstrap, marker

    routing = read(SKILL / "references" / "model-routing.md")
    for marker in (
        "Spark XHigh Fast",
        "native Luna Max Fast",
        "Terra Medium Standard",
        "Spark is ineligible for pure documents",
        "Night Shift is a delivery mode",
        "Transfer the whole mutable chain",
        "complete known mutable execution chain",
        "durable documentation alone does not repay worker startup",
        "default to Direct",
        "--work-type spark-coding --reasoning-effort xhigh",
        "--work-type luna --reasoning-effort max",
    ):
        assert marker in routing, marker

    profiles = json.loads(read(SKILL / "assets" / "codex-route-profiles.json"))["profiles"]
    assert profiles["goldilocks_spark_coder"]["reasoning_effort"] == "xhigh"
    assert profiles["goldilocks_luna_worker"]["reasoning_effort"] == "max"
    assert profiles["goldilocks_terra_engineer"]["reasoning_effort"] == "medium"
    assert 'model_reasoning_effort = "medium"' in read(
        PLUGIN / "agents" / "goldilocks-terra-engineer.toml"
    )

    dispatcher = SKILL / "scripts" / "dispatch_codex_worker.py"
    help_result = subprocess.run(
        [sys.executable, str(dispatcher), "--help"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert help_result.returncode == 0, help_result.stderr
    for marker in ("terra-standard", "spark-coding", "max"):
        assert marker in help_result.stdout, marker

    policy_files = [
        PLUGIN / "scripts" / name
        for name in (
            "agent_routing_guard.py",
            "project_delegation.py",
            "record_routing_outcome.py",
            "recovery_reminder.py",
            "route_auditor.py",
            "usage_reporter.py",
        )
    ] + [
        SKILL / "scripts" / "create_agent_profile.py",
        SKILL / "scripts" / "dispatch_codex_worker.py",
    ]
    for path in policy_files:
        assert f'POLICY_VERSION = "{CURRENT_VERSION}"' in read(path), path

    assert_release_matrix_table()

    print(f"Goldilocks v{CURRENT_VERSION} hybrid contract passed; v0.5.0 matrix preserved.")


if __name__ == "__main__":
    main()
