#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILL = PLUGIN / "skills" / "goldilocks"
VERSION = "0.5.2"
EXPERIMENT_POLICY = "0.5.2"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    failures: list[str] = []

    root = read(SKILL / "SKILL.md")
    for marker in (
        "Visible multi-unit implementation",
        "orchestrate.md",
        "constant-time comparison",
    ):
        if marker not in root:
            failures.append(f"root make-or-delegate gate lacks: {marker}")

    recovery = read(PLUGIN / "scripts" / "recovery_reminder.py")
    for marker in (
        f'POLICY_VERSION = "{EXPERIMENT_POLICY}"',
        "Visible multi-unit implementation",
        "make-or-delegate check before Lead edits",
        "Direct remains valid",
    ):
        if marker not in recovery:
            failures.append(f"recovery route gate lacks: {marker}")

    diagnose = read(SKILL / "references" / "diagnose.md")
    for marker in (
        "evidence-backed cause",
        "explicitly unknown",
        "cause, fix, and verification",
    ):
        if marker not in diagnose:
            failures.append(f"diagnostic handoff lacks: {marker}")

    standard_agent = read(PLUGIN / "agents" / "goldilocks-terra-engineer.toml")
    for marker in (
        "CAUSE",
        "evidence-backed",
        "explicitly unknown",
        "Fast before Standard",
        "Luna",
        "Spark",
        "why Fast is ineligible",
    ):
        if marker not in standard_agent:
            failures.append(f"Standard worker handoff lacks: {marker}")

    routing = read(SKILL / "references" / "model-routing.md")
    for marker in (
        "gpt-5.3-codex-spark` at XHigh",
        "gpt-5.6-terra` at Medium",
        "gpt-5.6-luna` at Max",
        "Spark is ineligible for pure documents",
        "Night Shift is a delivery mode",
        "record_routing_outcome.py",
        "verified_pass",
        "verified_fail",
    ):
        if marker not in routing:
            failures.append(f"model routing lacks: {marker}")

    orchestrate = read(SKILL / "references" / "orchestrate.md")
    for marker in (
        "Explain the route briefly",
        "ROUTE=<direct|fast|standard|mixed>",
        "WRITE_READY=<count>",
        "READ_READY=<count>",
        "EXISTING=<count>",
        "PLANNED_DISPATCH=<count>",
        "DETAIL=<one concise sentence>",
        "lead_faster",
        "parallel_gain",
        "quota_gain",
        "not a delegation quota",
        "worker-ready implementation",
        "project-level organization",
        "shared mutable surface",
        "blocks concurrent writers only",
        "ROUTE=mixed",
        "first bounded, useful real contract",
        "silently compared",
        "Do not create proof, probes, documents, tests, model calls",
        "host wait/status mechanism",
        "Never make the user open a finished child",
        "default to actually dispatching",
        "<tier>__<semantic>_<model>",
        "why Fast is ineligible",
        "missing native Luna role",
        "inside an HTML comment",
        "host-confirmed successful starts/active workers",
        "at most three delegated items plus `+N`",
    ):
        if marker not in orchestrate:
            failures.append(f"routing-rationale experiment lacks: {marker}")

    route_card = read(SKILL / "references" / "route-card.md")
    for marker in (
        "user's primary language",
        "canonical comment or both languages",
        "ROUTE=mixed | TEAM=Lead+3 workers",
        "路由=混合｜团队=主模型+3 个子智能体",
        "主模型更快",
        "共享写入面",
        "审核成本",
        "并行收益",
        "额度收益",
        "host-confirmed successful starts",
        "never `PLANNED_DISPATCH`",
    ):
        if marker not in route_card:
            failures.append(f"localized route receipt lacks: {marker}")

    dispatcher = read(SKILL / "scripts" / "dispatch_codex_worker.py")
    for marker in (
        '"luna": LUNA_MODEL',
        '"spark-coding": SPARK_MODEL',
        'selected_work_type = args.work_type or "luna"',
        '"general": LUNA_MODEL',
        '"coding": SPARK_MODEL',
    ):
        if marker not in dispatcher:
            failures.append(f"dispatcher route lacks: {marker}")

    guard = read(PLUGIN / "scripts" / "agent_routing_guard.py")
    recorder = read(PLUGIN / "scripts" / "record_routing_outcome.py")
    for marker in ("FAST_LEAF_MODELS", "is_recorded_fast_agent", "gpt-5.6-luna"):
        if marker not in guard:
            failures.append(f"Fast leaf guard lacks: {marker}")
    for marker in (
        f'POLICY_VERSION = "{EXPERIMENT_POLICY}"',
        "verified_passes",
        "verified_failures",
        "evidence_hash",
        "already-recorded",
    ):
        if marker not in recorder:
            failures.append(f"outcome recorder lacks: {marker}")

    registry = json.loads(read(SKILL / "assets" / "model-registry.json"))
    if registry["as_of"] != "2026-08-10":
        failures.append("model registry date was not refreshed")
    current = registry.get("current_openai_pricing", {})
    expected_prices = {
        "gpt-5.6-sol": (5.0, 0.5, 30.0),
        "gpt-5.6-terra": (2.0, 0.2, 12.0),
        "gpt-5.6-luna": (0.2, 0.02, 1.2),
    }
    for model, expected in expected_prices.items():
        row = current.get(model, {})
        actual = (row.get("input"), row.get("cached_input"), row.get("output"))
        if actual != expected:
            failures.append(f"{model} current price is {actual}, expected {expected}")

    for path in (
        ROOT / "docs" / "model-routing-update-2026-07-31.md",
        ROOT / "docs" / "model-routing-update-2026-07-31.zh-CN.md",
    ):
        body = read(path)
        for marker in ("Luna", "Terra", "Spark", "verified_pass"):
            if marker not in body:
                failures.append(f"{path.name} lacks {marker}")

    if failures:
        raise AssertionError("\n".join(failures))
    print(f"Goldilocks v{VERSION} model-routing contract passed.")


if __name__ == "__main__":
    main()
