#!/usr/bin/env python3

"""Keep Beta6 identity, bootstrap intent, and stable install guidance coherent."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
BETA = "0.5.3-beta.6"
STABLE_REF = "v0.5.2"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    manifests = (
        PLUGIN / ".codex-plugin" / "plugin.json",
        PLUGIN / ".claude-plugin" / "plugin.json",
    )
    for manifest in manifests:
        assert json.loads(read(manifest))["version"] == BETA, manifest
    marketplace = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
    assert marketplace["plugins"][0]["version"] == BETA

    policy_files = (
        "agent_routing_guard.py",
        "inspect_agent_runtime.py",
        "project_delegation.py",
        "record_routing_outcome.py",
        "recovery_reminder.py",
        "route_auditor.py",
        "sol_specialist_registry.py",
        "usage_reporter.py",
    )
    for name in policy_files:
        assert f'POLICY_VERSION = "{BETA}"' in read(PLUGIN / "scripts" / name), name
    for name in ("create_agent_profile.py", "dispatch_codex_worker.py"):
        assert f'POLICY_VERSION = "{BETA}"' in read(
            PLUGIN / "skills" / "goldilocks" / "scripts" / name
        ), name

    profiles = json.loads(read(PLUGIN / "skills" / "goldilocks" / "assets" / "codex-route-profiles.json"))
    assert profiles["experiment"] == f"v{BETA}-hybrid-routing"
    registry = read(PLUGIN / "skills" / "goldilocks" / "assets" / "model-registry.json")
    assert f"v{BETA}" in registry
    assert f"{BETA} host contract" in read(
        PLUGIN / "skills" / "goldilocks" / "references" / "sol-specialists.md"
    )

    root_skill = read(PLUGIN / "skills" / "goldilocks" / "SKILL.md")
    hygiene = read(PLUGIN / "skills" / "goldilocks" / "references" / "final-output-hygiene.md")
    notices = read(PLUGIN / "THIRD_PARTY_NOTICES.md")
    assert "[final-output-hygiene.md](references/final-output-hygiene.md)" in root_skill
    assert "accepted, verified current state" in hygiene
    assert "Do not add a freeze, scanner, automatic agent" in hygiene
    assert "https://github.com/LB623/no-negative-echo" in notices
    assert "independent, narrowed rewrite" in notices

    stable_install_files = (
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        ROOT / "docs" / "installation.md",
        ROOT / "docs" / "installation.zh-CN.md",
    )
    for path in stable_install_files:
        body = read(path)
        assert STABLE_REF in body, path
    for path in stable_install_files[:2]:
        assert BETA not in read(path), path

    bootstrap = read(PLUGIN / "skills" / "goldilocks-bootstrap" / "scripts" / "bootstrap.py")
    bootstrap_reference = read(PLUGIN / "skills" / "goldilocks-bootstrap" / "references" / "bootstrap.md")
    assert f'"--ref", "v{BETA}", "--json"' in bootstrap
    assert f"v{BETA} Beta marketplace" in bootstrap_reference
    assert "v0.5.2 official Sol template" in bootstrap

    for path in (ROOT / "CHANGELOG.md", ROOT / "CHANGELOG.zh-CN.md"):
        body = read(path)
        assert f"## {BETA} — 2026-08-25" in body, path
        assert "usage_limit" in body and "worktree" in body and "Goldilocks" in body, path

    print("Goldilocks 0.5.3-beta.6 release contract passed; stable installs remain v0.5.2.")


if __name__ == "__main__":
    main()
