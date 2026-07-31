#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILL = PLUGIN / "skills" / "goldilocks"
VERSION = "0.4.5"


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
        f'POLICY_VERSION = "{VERSION}"',
        "Visible multi-unit implementation",
        "make-or-delegate check before Lead edits",
        "Direct remains valid",
    ):
        if marker not in recovery:
            failures.append(f"recovery route gate lacks: {marker}")

    routing = read(SKILL / "references" / "model-routing.md")
    for marker in (
        "gpt-5.6-luna` as the universal Fast baseline",
        "gpt-5.3-codex-spark` instead",
        "gpt-5.6-terra` as the OpenAI Standard baseline",
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
        "failed minimal probe",
    ):
        if marker not in orchestrate:
            failures.append(f"routing-rationale experiment lacks: {marker}")

    dispatcher = read(SKILL / "scripts" / "dispatch_codex_worker.py")
    for marker in (
        '"luna": LUNA_MODEL',
        '"spark-coding": SPARK_MODEL',
        'default="luna"',
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
        f'POLICY_VERSION = "{VERSION}"',
        "verified_passes",
        "verified_failures",
        "evidence_hash",
        "already-recorded",
    ):
        if marker not in recorder:
            failures.append(f"outcome recorder lacks: {marker}")

    registry = json.loads(read(SKILL / "assets" / "model-registry.json"))
    if registry["as_of"] != "2026-07-31":
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
    print("Goldilocks v0.4.5 model-routing contract passed.")


if __name__ == "__main__":
    main()
