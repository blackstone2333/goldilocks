#!/usr/bin/env python3

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
README = ROOT / "README.md"
README_ZH = ROOT / "README.zh-CN.md"
AGENT_GUIDE = ROOT / "docs" / "AGENT-GUIDE.md"
ROUTING = PLUGIN / "skills" / "goldilocks" / "references" / "model-routing.md"
SOL_SPECIALISTS = PLUGIN / "skills" / "goldilocks" / "references" / "sol-specialists.md"
ARTIFACTS = PLUGIN / "skills" / "goldilocks" / "references" / "artifacts.md"
PRESENTATIONS = PLUGIN / "skills" / "goldilocks" / "references" / "presentations.md"
REPORT = ROOT / "evals" / "results" / "2026-07-25-v040-structured-artifact-pilot.md"
REGISTRY = PLUGIN / "skills" / "goldilocks" / "assets" / "model-registry.json"


failures: list[str] = []


def require(path: Path, markers: list[str]) -> str:
    value = path.read_text(encoding="utf-8")
    for marker in markers:
        if marker not in value:
            failures.append(f"{path.relative_to(ROOT)} lacks: {marker}")
    return value


require(
    README,
    [
        "docs/AGENT-GUIDE.md",
        "Terra Medium",
        "Spark XHigh",
        "Luna Max",
    ],
)
require(
    README_ZH,
    [
        "docs/AGENT-GUIDE.md",
        "Terra Medium",
        "Spark XHigh",
        "Luna Max",
    ],
)
require(
    AGENT_GUIDE,
    [
        "Unit boundaries are the rework boundary",
        "The `project` worker profile",
        "Spark is not for document prose or continuity records",
        "Fast coding leaf",
        "Economy leaf",
    ],
)
require(
    ROUTING,
    [
        "`project`",
        "`minimal`",
        "`inherit`",
        "models_cache.json",
        "GOLDILOCKS_WORKER",
        "one coherent batch",
        "start with one Fast session",
        "gpt-5.3-codex-spark",
        "gpt-5.6-luna",
        "spark-coding",
        "luna",
    ],
)
require(
    SOL_SPECIALISTS,
    [
        "visible Codex task/thread",
        "a hidden native subagent",
        "permits two",
        "../../../scripts/sol_specialist_registry.py reserve",
        "Require explicit user authorization",
        "`create_thread`",
        "host `list_projects`",
        "same local/worktree",
        "lead__<semantic>_sol",
        "Goldilocks · Sol 专员 · <semantic>",
        "gpt-5.6-sol` with high reasoning",
        "read/list/send",
        "delivered origin return",
        "Never expire reservations",
        "independently audit the root project",
        "persistent receipt",
        "`execution`",
        "`audit`",
        "create another Sol specialist",
        "Require a concise result",
        "goldilocks_sol_reviewer",
    ],
)
require(
    ARTIFACTS,
    [
        "start with one worker session",
        "session count",
        "capability profile",
    ],
)
require(
    PRESENTATIONS,
    [
        "12-slide",
        "one worker session",
        "session boundary",
        "--work-type general",
    ],
)
require(
    REPORT,
    [
        "1,332,702",
        "1,190,016",
        "uncached input + output",
        "not raw total tokens",
    ],
)

registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
models = {model["id"]: model for model in registry["models"]}
spark_roles = models["gpt-5.3-codex-spark"]["recommended_roles"]
luna_roles = models["gpt-5.6-luna"]["recommended_roles"]
if "fast-default-programming" not in spark_roles or "general-content-production" not in models["gpt-5.3-codex-spark"]["excluded_roles"]:
    failures.append("Spark must be the programming Fast default without owning general content")
for role in ("economy-default", "latency-tolerant-general", "document-work", "night-shift"):
    if role not in luna_roles:
        failures.append(f"Luna seed lacks Economy role: {role}")
if "fast-default" in luna_roles or "default-fast-coding" not in models["gpt-5.6-luna"]["excluded_roles"]:
    failures.append("Luna must not remain the default Fast coding route")

profile = registry.get("production_profile", {})
expected_profile = {
    "lead": "gpt-5.6-sol",
    "standard": "gpt-5.6-terra",
    "fast": "gpt-5.3-codex-spark",
    "economy": "gpt-5.6-luna",
}
for role, model in expected_profile.items():
    if profile.get(role, {}).get("model") != model:
        failures.append(f"production profile {role} is not {model}")

if failures:
    print("Goldilocks context-lean worker contract failed:")
    for failure in failures:
        print(f"- {failure}")
    sys.exit(1)

print("Goldilocks context-lean worker contract passed.")
