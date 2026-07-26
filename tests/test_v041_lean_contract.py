#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
VERSION = "0.4.1"


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

    codex_interface = codex_manifest["interface"]
    if codex_interface["shortDescription"] != "Direct by default; structure only when earned":
        failures.append("Codex short description does not state the thin-kernel default")
    if not codex_interface["defaultPrompt"][0].startswith("Default to Direct"):
        failures.append("Codex default prompt still biases every task toward workflow")

    guard = read(PLUGIN / "scripts" / "agent_routing_guard.py")
    if f'POLICY_VERSION = "{VERSION}"' not in guard:
        failures.append("routing guard policy version was not advanced")

    recovery = read(PLUGIN / "scripts" / "recovery_reminder.py")
    for phrase in (
        "MICRO_STYLE",
        "Lead with the result",
        "Omit work preambles",
        "Report only changed state",
        "decisive evidence",
    ):
        if phrase not in recovery:
            failures.append(f"recovery hook lacks micro-style contract: {phrase}")

    if failures:
        raise AssertionError("\n".join(failures))
    print("Goldilocks v0.4.1 lean-routing contract passed.")


if __name__ == "__main__":
    main()
