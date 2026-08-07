#!/usr/bin/env python3

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.5.0-alpha.1"
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILLS = PLUGIN / "skills"
ENTRY = SKILLS / "goldilocks" / "SKILL.md"
ENTRY_UI = SKILLS / "goldilocks" / "agents" / "openai.yaml"
PROTOCOL = SKILLS / "goldilocks" / "references" / "artifacts.md"
PRESENTATIONS = SKILLS / "goldilocks" / "references" / "presentations.md"
GLOBAL_CONTRACT = SKILLS / "goldilocks" / "assets" / "artifact-contract.md"
UNIT_CONTRACT = SKILLS / "goldilocks" / "assets" / "artifact-unit-contract.md"
REPORT = ROOT / "evals" / "results" / "2026-07-25-v040-structured-artifact-pilot.md"
DECK = ROOT / "evals" / "artifacts" / "v040-hsk4-network-shopping.pptx"


failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def text(path: Path) -> str:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def words(path: Path) -> int:
    return len(text(path).split())


for required in [
    ENTRY,
    ENTRY_UI,
    PROTOCOL,
    PRESENTATIONS,
    GLOBAL_CONTRACT,
    UNIT_CONTRACT,
    REPORT,
    DECK,
    ROOT / "docs" / "v0.4-structured-artifact-orchestration.md",
    ROOT / "docs" / "v0.4-structured-artifact-orchestration.zh-CN.md",
]:
    if not required.is_file():
        fail(f"missing file: {required.relative_to(ROOT)}")


entry = text(ENTRY)
for marker in [
    "name: goldilocks",
    "Explicit multi-unit artifact production",
    "artifacts.md",
]:
    if marker not in entry:
        fail(f"single Goldilocks router lacks artifact trigger: {marker}")
if ENTRY.is_file() and words(ENTRY) > 380:
    fail("single Goldilocks router exceeds 380 words including metadata")


protocol = text(PROTOCOL)
for marker in [
    "Goal → Global Artifact Contract → Unit Contracts",
    "audience and outcome",
    "structure map",
    "shared terminology and sources",
    "acceptance rubric",
    "merge order",
    "integration owner",
    "localized rework",
    "Fast",
    "Standard",
    "Lead",
    "batch",
    "specialist skill",
    "Durable Lessons",
]:
    if marker not in protocol:
        fail(f"generic artifact protocol lacks: {marker}")


presentations = text(PRESENTATIONS)
for marker in [
    "Presentation Profile",
    "storyboard",
    "one slide",
    "independently replaceable",
    "single integration owner",
    "design system",
    "speaker notes",
    "full-size",
    "montage",
    "localized rework",
    "batch",
]:
    if marker not in presentations:
        fail(f"presentation profile lacks: {marker}")


if PROTOCOL.is_file() and PRESENTATIONS.is_file() and ENTRY.is_file():
    active_route_words = words(ENTRY) + words(PROTOCOL) + words(PRESENTATIONS)
    if active_route_words > 1600:
        fail(f"artifact active route exceeds 1600 words: {active_route_words}")


for implementation_detail in ["PptxGenJS", "@oai/artifact-tool", "python-pptx"]:
    if implementation_detail in protocol or implementation_detail in presentations:
        fail(f"Goldilocks duplicates specialist implementation detail: {implementation_detail}")


global_contract = text(GLOBAL_CONTRACT)
for section in [
    "## Audience and outcome",
    "## Final format",
    "## Structure map",
    "## Shared system",
    "## Unit graph",
    "## Acceptance rubric",
    "## Integration",
]:
    if section not in global_contract:
        fail(f"global artifact contract lacks section: {section}")


unit_contract = text(UNIT_CONTRACT)
for section in [
    "## Unit identity",
    "## Objective",
    "## Inputs and dependencies",
    "## Output contract",
    "## Acceptance checks",
    "## Ownership and boundaries",
    "## Evidence returned",
]:
    if section not in unit_contract:
        fail(f"artifact unit contract lacks section: {section}")


for manifest in [
    PLUGIN / ".claude-plugin" / "plugin.json",
    PLUGIN / ".codex-plugin" / "plugin.json",
    ROOT / ".claude-plugin" / "marketplace.json",
]:
    payload = {}
    if manifest.is_file():
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            fail(f"invalid JSON in {manifest.relative_to(ROOT)}: {error.msg}")
    if manifest.name == "marketplace.json":
        actual = (payload.get("plugins") or [{}])[0].get("version", "")
    else:
        actual = payload.get("version", "").split("+", 1)[0]
    if actual != VERSION:
        fail(f"{manifest.relative_to(ROOT)} version must be {VERSION}, found {actual!r}")


for readme_name in ["README.md", "README.zh-CN.md"]:
    readme = text(ROOT / readme_name)
    badge_version = VERSION.replace("-", "--")
    if f"version-{badge_version}" not in readme:
        fail(f"{readme_name} lacks the current version badge")
    for removed_promotion in [
        "## Structured Artifacts",
        "## 结构化 Artifacts",
        "Artifact Contract",
        "localized rework",
        "v040-hsk4-network-shopping-montage.png",
    ]:
        if removed_promotion in readme:
            fail(f"{readme_name} still promotes unproven artifact performance: {removed_promotion}")


cases = []
case_path = ROOT / "evals" / "trigger-cases.jsonl"
if case_path.is_file():
    for line in case_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
artifact_cases = {row.get("id"): row for row in cases if row.get("id", "").startswith("X")}
for case_id in ["X01", "X02", "X03", "X04"]:
    if case_id not in artifact_cases:
        fail(f"missing artifact trigger case: {case_id}")
if artifact_cases and not any(row["expected"]["quality_mode"] == "Direct" for row in artifact_cases.values()):
    fail("artifact trigger cases need a Direct negative boundary")


report = text(REPORT)
for marker in [
    "HSK4",
    "artifact quality",
    "expensive-token share",
    "uncached input + output",
    "total processed tokens",
    "elapsed time",
    "localized rework",
    "integration defects",
]:
    if marker not in report:
        fail(f"v0.4 pilot report lacks: {marker}")


if failures:
    print(f"Goldilocks v{VERSION} artifact contract failed:")
    for failure in failures:
        print(f"- {failure}")
    sys.exit(1)

print(f"Goldilocks v{VERSION} structured-artifact contract passed.")
