#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
VERSION = "0.5.0"
README = ROOT / "README.md"
README_ZH = ROOT / "README.zh-CN.md"
AGENT_GUIDE = ROOT / "docs" / "AGENT-GUIDE.md"
INSTALL = ROOT / "docs" / "installation.md"
INSTALL_ZH = ROOT / "docs" / "installation.zh-CN.md"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    failures: list[str] = []

    codex_manifest = json.loads(read(PLUGIN / ".codex-plugin" / "plugin.json"))
    claude_manifest = json.loads(read(PLUGIN / ".claude-plugin" / "plugin.json"))
    marketplace = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
    for name, actual in (
        ("Codex manifest", codex_manifest["version"].split("+", 1)[0]),
        ("Claude manifest", claude_manifest["version"]),
        ("marketplace", marketplace["plugins"][0]["version"]),
    ):
        if actual != VERSION:
            failures.append(f"{name} version is {actual}, expected {VERSION}")

    root_skill = read(PLUGIN / "skills" / "goldilocks" / "SKILL.md")
    required_root_phrases = (
        "Decision-first communication",
        "Do not narrate planned work",
        "delta only",
        "shortest decisive evidence",
        "evidence-backed cause",
        "explicitly unknown",
    )
    for phrase in required_root_phrases:
        if phrase not in root_skill:
            failures.append(f"Goldilocks root is missing lean-output rule: {phrase}")

    root_body = root_skill.split("---", 2)[-1]
    if len(root_body.split()) > 300:
        failures.append(
            f"Goldilocks root is {len(root_body.split())} words; the thin router budget is 300"
        )
    for phrase in (
        "Direct exit",
        "Do not read any Goldilocks reference",
        "Do not invoke another Goldilocks skill",
        "Do not announce the route",
    ):
        if phrase not in root_skill:
            failures.append(f"Goldilocks root is missing zero-cost Direct rule: {phrase}")
    for phrase in ("any executable work", "documents", "presentations", "spreadsheets"):
        if phrase not in root_skill:
            failures.append(f"Goldilocks root is missing general-work trigger: {phrase}")
    if "## Minimum complete loop" in root_skill:
        failures.append("Goldilocks root still embeds a universal execution loop")

    visible_skills = sorted(
        path.parent.name for path in (PLUGIN / "skills").glob("*/SKILL.md")
    )
    if visible_skills != ["goldilocks", "goldilocks-bootstrap"]:
        failures.append(
            f"visible Skill set is {visible_skills}; release must expose the thin router and one-time Bootstrap only"
        )
    bootstrap_skill = read(PLUGIN / "skills" / "goldilocks-bootstrap" / "SKILL.md")
    if "installing, upgrading, or repairing" not in bootstrap_skill or "ordinary tasks" not in bootstrap_skill:
        failures.append("one-time Bootstrap Skill lacks its narrow install/upgrade trigger")
    if "bootstrap" in root_skill.lower():
        failures.append("main Goldilocks router must not mention or trigger Bootstrap")
    for engine in (
        "align.md",
        "diagnose.md",
        "build.md",
        "orchestrate.md",
        "prove.md",
        "evolve.md",
        "artifacts.md",
    ):
        if engine not in root_skill:
            failures.append(f"Goldilocks root does not route the internal engine: {engine}")

    orchestrate = read(PLUGIN / "skills" / "goldilocks" / "references" / "orchestrate.md")
    required_route_phrases = (
        "Route readiness is a prerequisite",
        "Do not debug worker transport inside a product task",
        "fall back to Direct",
        "cached route evidence",
    )
    for phrase in required_route_phrases:
        if phrase not in orchestrate:
            failures.append(f"orchestration is missing failure-economy rule: {phrase}")

    route_card = read(
        PLUGIN / "skills" / "goldilocks" / "references" / "route-card.md"
    )
    for phrase in (
        "Luna = `0.04 × Sol`",
        "Terra = `0.40 × Sol`",
        "Spark remains a separate unpriced pool",
        "Price every independent ready unit before Direct",
        "Shared writes block conflicting writers, not read-only work",
        "`shared_surface` alone cannot justify `PLANNED_DISPATCH=0`",
        "generic “extra tokens” or Lead convenience is insufficient",
    ):
        if phrase not in route_card:
            failures.append(f"route card is missing weighted-cost guard: {phrase}")

    diagnose = read(PLUGIN / "skills" / "goldilocks" / "references" / "diagnose.md")
    continuity = read(PLUGIN / "skills" / "goldilocks" / "references" / "continuity.md")
    retention_text = f"{diagnose}\n{continuity}"
    for phrase in (
        "second user-confirmed recurrence",
        "before another patch",
        ".goldilocks/ACTIVE.md",
        "Do not repeat",
    ):
        if phrase.lower() not in retention_text.lower():
            failures.append(f"repeated-failure retention lacks: {phrase}")
    for phrase in (
        "unverified fixes out of the changelog",
        "confirmed user-visible release changes",
    ):
        if phrase not in continuity:
            failures.append(f"continuity changelog boundary lacks: {phrase}")

    dispatcher = read(
        PLUGIN
        / "skills"
        / "goldilocks"
        / "scripts"
        / "dispatch_codex_worker.py"
    )
    if "agents.enabled=false" in dispatcher:
        failures.append("dispatcher still uses the CLI-version-specific agents.enabled override")
    if '"--disable",\n        "multi_agent"' not in dispatcher:
        failures.append("dispatcher does not use the cross-version multi_agent feature switch")
    for phrase in ("GOLDILOCKS_WORKER_EVENTS_DIR", 'command.append("--json")'):
        if phrase not in dispatcher:
            failures.append(f"dispatcher is missing context-lean worker evidence handling: {phrase}")

    notices = read(PLUGIN / "THIRD_PARTY_NOTICES.md")
    for source, commit in (
        ("JuliusBrussee/caveman", "0d95a81d35a9f2d123a5e9430d1cfc43d55f1bb0"),
        ("ayghri/i-have-adhd", "16a42a01f7783e29db8557dfc46226baf8015618"),
    ):
        if source not in notices or commit not in notices:
            failures.append(f"third-party notice is missing {source} provenance")

    for path in (ROOT / "CHANGELOG.md", ROOT / "CHANGELOG.zh-CN.md"):
        if f"## {VERSION}" not in read(path):
            failures.append(f"{path.name} is missing the {VERSION} entry")

    for path in (README, README_ZH):
        body = read(path)
        badge_version = VERSION.replace("-", "--")
        if f"version-{badge_version}" not in body:
            failures.append(f"{path.name} badge is not {VERSION}")
        if "Caveman" not in body or "ADHD" not in body:
            failures.append(f"{path.name} does not explain the lean-output influence")
        if "docs/AGENT-GUIDE.md" not in body:
            failures.append(f"{path.name} does not link the Agent-facing project guide")
        if len(body.splitlines()) > 340:
            failures.append(f"{path.name} exceeds the 340-line professional-homepage budget")
        for marker in ("```mermaid", "PROJECT.md", ".goldilocks/", "ACTIVE.md"):
            if marker not in body:
                failures.append(f"{path.name} lacks professional architecture content: {marker}")

    feature_markers = {
        README: (
            "> [!CAUTION]",
            "Do not enable Goldilocks and Superpowers together",
            "> [!IMPORTANT]",
            "6 (recommended starting value)",
            "## Reading the route receipt",
            "## Usage",
            "## Night Shift",
            "docs/assets/v050-release-comparison.svg",
        ),
        README_ZH: (
            "> [!CAUTION]",
            "不要同时启用 Goldilocks 和 Superpowers",
            "> [!IMPORTANT]",
            "6（建议起始值）",
            "## 看懂路由回执",
            "## Usage 用量统计",
            "## Night Shift 夜班模式",
            "docs/assets/v050-release-comparison.zh-CN.svg",
        ),
    }
    for path, markers in feature_markers.items():
        body = read(path)
        for marker in markers:
            if marker not in body:
                failures.append(f"{path.name} lacks v0.5.0 feature visibility: {marker}")

    install_docs = {
        INSTALL: (
            "Trust all and continue",
            "--dangerously-bypass-hook-trust",
            "GOLDILOCKS_UPDATE_CHECK=0",
        ),
        INSTALL_ZH: (
            "信任全部并继续",
            "--dangerously-bypass-hook-trust",
            "GOLDILOCKS_UPDATE_CHECK=0",
        ),
        AGENT_GUIDE: (
            "[features.multi_agent_v2]",
            "max_concurrent_threads_per_session = 6",
        ),
    }
    for path, markers in install_docs.items():
        body = read(path)
        for marker in markers:
            if marker not in body:
                failures.append(f"{path.name} lacks install trust guidance: {marker}")

    readme_order = {
        README: (
            "## Install",
            "### Ask an AI to install it",
            "### Codex CLI or Desktop",
            "### Claude Code",
            "### Other Skills-compatible hosts",
            "## What it does",
            "## Evidence",
        ),
        README_ZH: (
            "## 安装",
            "### 让 AI 帮你安装",
            "### Codex CLI 或 Desktop",
            "### Claude Code",
            "### 其他兼容 Skills 的宿主",
            "## 它能做什么",
            "## 证据",
        ),
    }
    for path, headings in readme_order.items():
        body = read(path)
        positions = [body.find(heading) for heading in headings]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            failures.append(
                f"{path.name} must order AI install, Codex, Claude, portable hosts, capabilities, then evidence"
            )

    feature_order = {
        README: (
            "## Reading the route receipt",
            "## Usage",
            "## Night Shift",
            "## Codex model routes",
            "## Evidence",
        ),
        README_ZH: (
            "## 看懂路由回执",
            "## Usage 用量统计",
            "## Night Shift 夜班模式",
            "## Codex 模型路由",
            "## 证据",
        ),
    }
    for path, headings in feature_order.items():
        body = read(path)
        positions = [body.find(heading) for heading in headings]
        if any(position < 0 for position in positions) or positions != sorted(positions):
            failures.append(
                f"{path.name} must expose receipt, Usage, Night Shift, model routes, then evidence"
            )

    discovery_markers = {
        README: (
            "lean, adaptive replacement for Superpowers",
            "v0.5.0 release matrix",
            "took 36.79% longer",
            "−13.67%",
            "Superpowers",
        ),
        README_ZH: (
            "精简、动态的 Superpowers 替代方案",
            "v0.5.0 发布矩阵",
            "累计耗时高 36.79%",
            "−13.67%",
            "Superpowers",
        ),
        AGENT_GUIDE: (
            "replacement for Superpowers",
            "v0.4.1 Direct A/B passed 114/114",
            "11.5% fewer processing tokens",
            "10.9% less cumulative time",
            "not `AGENTS.md`",
        ),
    }
    for path, markers in discovery_markers.items():
        body = read(path)
        for marker in markers:
            if marker not in body:
                failures.append(f"{path.name} lacks searchable evidence marker: {marker}")

    if (ROOT / "docs" / "AGENTS.md").exists():
        failures.append("Agent-facing project documentation must not be an auto-loaded docs/AGENTS.md")

    codex_interface = codex_manifest["interface"]
    if codex_interface["shortDescription"] != "Adaptive workflow; Direct when enough":
        failures.append("Codex short description does not state the general adaptive default")
    if not codex_interface["defaultPrompt"][0].startswith("Default to Direct"):
        failures.append("Codex default prompt still biases every task toward workflow")

    guard = read(PLUGIN / "scripts" / "agent_routing_guard.py")
    if f'POLICY_VERSION = "{VERSION}"' not in guard:
        failures.append("routing guard policy version was not advanced")

    recovery = read(PLUGIN / "scripts" / "recovery_reminder.py")
    for phrase in (
        "MICRO_STYLE",
        "ROUTING_GATE",
        "CONTINUITY_GATE",
        "Lead with the result",
        "Omit work preambles",
        "Report only changed state",
        "decisive evidence",
        "For defects",
        "expand when asked",
        "evidence-backed cause",
        "explicitly unknown",
        "fix and verification",
        "goldilocks:goldilocks",
        "gate_injections",
        "prompt_fingerprint",
        "repeat_failure_signal",
        "continuity_required",
        "Keep unverified work out of CHANGELOG",
    ):
        if phrase not in recovery:
            failures.append(f"recovery hook lacks micro-style contract: {phrase}")

    if failures:
        raise AssertionError("\n".join(failures))
    print(f"Goldilocks v{VERSION} lean-routing contract passed.")


if __name__ == "__main__":
    main()
