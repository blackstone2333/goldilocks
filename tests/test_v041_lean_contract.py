#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
VERSION = "0.4.5"


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
    if visible_skills != ["goldilocks"]:
        failures.append(
            f"visible Skill set is {visible_skills}; thin core must expose only goldilocks"
        )
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

    for path in (ROOT / "README.md", ROOT / "README.zh-CN.md"):
        body = read(path)
        if f"version-{VERSION}" not in body:
            failures.append(f"{path.name} badge is not {VERSION}")
        if "Caveman" not in body or "ADHD" not in body:
            failures.append(f"{path.name} does not explain the lean-output influence")

    install_docs = {
        ROOT / "README.md": (
            "Ask an AI to install it",
            "Hook authorization is expected",
            "Goldilocks damaged the installation",
            "GOLDILOCKS_UPDATE_CHECK=0",
        ),
        ROOT / "README.zh-CN.md": (
            "让 AI 一键安装",
            "出现 Hook 授权是正常现象",
            "并不表示 Goldilocks 把安装环境弄坏了",
            "GOLDILOCKS_UPDATE_CHECK=0",
        ),
    }
    for path, markers in install_docs.items():
        body = read(path)
        for marker in markers:
            if marker not in body:
                failures.append(f"{path.name} lacks install trust guidance: {marker}")

    readme_order = {
        ROOT / "README.md": ("## Install", "## What it does"),
        ROOT / "README.zh-CN.md": ("## 安装", "## 它能做什么"),
    }
    for path, (install_heading, capability_heading) in readme_order.items():
        body = read(path)
        if body.find(install_heading) > body.find(capability_heading):
            failures.append(f"{path.name} must show installation before capabilities")

    discovery_markers = {
        ROOT / "README.md": (
            "replacement for Superpowers",
            "token-efficient AI agent workflow",
            "114/114 external checks",
            "11.5% fewer processing tokens",
            "10.9% less cumulative time",
        ),
        ROOT / "README.zh-CN.md": (
            "Superpowers 替代方案",
            "token-efficient AI Agent 工作流",
            "114/114 项外部检查",
            "处理 token 少 11.5%",
            "累计耗时少 10.9%",
        ),
    }
    for path, markers in discovery_markers.items():
        body = read(path)
        for marker in markers:
            if marker not in body:
                failures.append(f"{path.name} lacks searchable evidence marker: {marker}")

    codex_interface = codex_manifest["interface"]
    if codex_interface["shortDescription"] != "Adaptive workflow; Direct when enough":
        failures.append("Codex short description does not state the general adaptive default")
    if not codex_interface["defaultPrompt"][0].startswith("Default to Direct"):
        failures.append("Codex default prompt still biases every task toward workflow")

    guard = read(PLUGIN / "scripts" / "agent_routing_guard.py")
    if f'POLICY_VERSION = "{VERSION}-exp3.2"' not in guard:
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
    print("Goldilocks v0.4.5 lean-routing contract passed.")


if __name__ == "__main__":
    main()
