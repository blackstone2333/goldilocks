#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
README = ROOT / "README.md"
README_ZH = ROOT / "README.zh-CN.md"
ROUTING = PLUGIN / "skills" / "goldilocks" / "references" / "model-routing.md"
ARTIFACTS = PLUGIN / "skills" / "goldilocks" / "references" / "artifacts.md"
PRESENTATIONS = PLUGIN / "skills" / "goldilocks" / "references" / "presentations.md"
REPORT = ROOT / "evals" / "results" / "2026-07-25-v040-structured-artifact-pilot.md"
HOOKS = PLUGIN / "hooks" / "hooks.json"
REGISTRY = PLUGIN / "skills" / "goldilocks" / "assets" / "model-registry.json"
EXPECTED_HOOK_HASH = "816f58dd24bebf9b76e18d8abbe63332dde319b08228abe4f2f101f97c411f15"


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
        "Coding → Spark · General → Luna",
        "`project` profile",
        "unit boundaries keep rework local",
        "Fast **coding**",
        "Fast **general non-coding**",
    ],
)
require(
    README_ZH,
    [
        "编程 → Spark · 通用非编程 → Luna",
        "默认 `project` 档位",
        "单元边界让返工保持局部",
        "Fast **编程**",
        "Fast **通用非编程**",
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
        "coding",
        "general",
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

actual_hook_hash = hashlib.sha256(HOOKS.read_bytes()).hexdigest()
if actual_hook_hash != EXPECTED_HOOK_HASH:
    failures.append("hooks/hooks.json changed; this experiment must not trigger a new trust hash")

registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
models = {model["id"]: model for model in registry["models"]}
spark_roles = models["gpt-5.3-codex-spark"]["recommended_roles"]
luna_roles = models["gpt-5.6-luna"]["recommended_roles"]
if "fast-coding" not in spark_roles or "fast-general" in spark_roles:
    failures.append("Spark seed must prefer coding Fast work, not general content production")
for role in ("fast-general", "presentation-content", "document-sections", "report-drafting"):
    if role not in luna_roles:
        failures.append(f"Luna seed lacks non-coding role: {role}")

if failures:
    print("Goldilocks context-lean worker contract failed:")
    for failure in failures:
        print(f"- {failure}")
    sys.exit(1)

print("Goldilocks context-lean worker contract passed.")
