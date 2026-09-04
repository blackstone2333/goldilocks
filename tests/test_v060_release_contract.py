#!/usr/bin/env python3

"""Keep the 0.6.0 identity and no-Hook guidance coherent."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
RELEASE = "0.6.0"
RELEASE_REF = f"v{RELEASE}"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def main() -> None:
    manifests = (
        PLUGIN / ".codex-plugin" / "plugin.json",
        PLUGIN / ".claude-plugin" / "plugin.json",
    )
    for manifest in manifests:
        version = json.loads(read(manifest))["version"]
        assert version.split("+", 1)[0] == RELEASE, manifest
    marketplace = json.loads(read(ROOT / ".claude-plugin" / "marketplace.json"))
    assert marketplace["plugins"][0]["version"] == RELEASE

    policy_files = (
        "inspect_agent_runtime.py",
        "project_delegation.py",
        "record_routing_outcome.py",
        "sol_specialist_registry.py",
        "usage_reporter.py",
    )
    for name in policy_files:
        assert f'POLICY_VERSION = "{RELEASE}"' in read(PLUGIN / "scripts" / name), name
    for name in ("create_agent_profile.py", "dispatch_codex_worker.py"):
        assert f'POLICY_VERSION = "{RELEASE}"' in read(
            PLUGIN / "skills" / "goldilocks" / "scripts" / name
        ), name

    profiles = json.loads(read(PLUGIN / "skills" / "goldilocks" / "assets" / "codex-route-profiles.json"))
    assert profiles["experiment"] == f"v{RELEASE}-hybrid-routing"
    registry = read(PLUGIN / "skills" / "goldilocks" / "assets" / "model-registry.json")
    assert f"v{RELEASE}" in registry
    assert f"{RELEASE} host contract" in read(
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
    assert "按任务匹配加载 domain Skill" in root_skill
    assert "Direct" in root_skill and "Goldilocks orchestration" in root_skill
    assert "不提供或依赖 Hook" in root_skill
    assert "Usage 仅 on-demand，无 automatic 模式" in root_skill
    assert "explicit automatic" not in root_skill
    assert not (PLUGIN / "hooks" / "hooks.json").exists()

    readme = read(ROOT / "README.md")
    readme_zh = read(ROOT / "README.zh-CN.md")
    guide = read(ROOT / "docs" / "AGENT-GUIDE.md")
    assert "explicitly established earlier" in readme
    assert "no Hook or background process records one automatically" in readme
    assert "does not load the Goldilocks root Skill" in readme
    assert "Every executable turn now shows" not in readme
    assert "先前已经显式建立可用基线" in readme_zh
    assert "没有 Hook 或后台流程自动记录基线" in readme_zh
    assert "不加载 Goldilocks 根 Skill" in readme_zh
    assert "每个可执行任务都会" not in readme_zh
    assert "has no automatic mode, Hook, or background recorder" in guide
    assert "no Goldilocks root load" in guide

    current_install_files = (
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        ROOT / "docs" / "installation.md",
        ROOT / "docs" / "installation.zh-CN.md",
    )
    for path in current_install_files:
        body = read(path)
        assert RELEASE_REF in body or RELEASE in body, path
        assert "v0.6.0-beta.1" not in body, path

    bootstrap = read(PLUGIN / "skills" / "goldilocks-bootstrap" / "scripts" / "bootstrap.py")
    bootstrap_reference = read(PLUGIN / "skills" / "goldilocks-bootstrap" / "references" / "bootstrap.md")
    assert f'"--ref", "v{RELEASE}", "--json"' in bootstrap
    assert f"stable v{RELEASE} marketplace" in bootstrap_reference
    assert "v0.5.2 official Sol template" in bootstrap

    for path in (ROOT / "CHANGELOG.md", ROOT / "CHANGELOG.zh-CN.md"):
        body = read(path)
        assert f"## {RELEASE} — 2026-09-04" in body, path
        assert "Direct" in body and "Skill" in body, path

    print("Goldilocks 0.6.0 release contract passed; stable identity is coherent.")


if __name__ == "__main__":
    main()
