#!/usr/bin/env python3

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILLS = PLUGIN / "skills"
MAIN = SKILLS / "goldilocks" / "SKILL.md"
CASES = ROOT / "evals" / "trigger-cases.jsonl"
RESULTS = ROOT / "evals" / "results" / "red-baseline.jsonl"

ENGINES = {"align", "diagnose", "build", "orchestrate", "prove", "evolve"}
ENTRIES = {
    "brainstorming",
    "writing-plans",
    "executing-plans",
    "test-driven-development",
    "systematic-debugging",
    "using-git-worktrees",
    "dispatching-parallel-agents",
    "subagent-driven-development",
    "requesting-code-review",
    "receiving-code-review",
    "verification-before-completion",
    "finishing-a-development-branch",
    "writing-skills",
}
MODES = {"Direct", "Guarded", "Critical"}
CAPABILITIES = {"Lead", "Standard", "Fast", "Unknown"}


failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def require_file(path: Path) -> None:
    if not path.is_file():
        fail(f"missing file: {path.relative_to(ROOT)}")


def word_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").split())


def body_word_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    body = parts[2] if len(parts) == 3 else text
    return len(body.split())


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    if not path.is_file():
        return rows
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            rows.append(json.loads(raw))
        except json.JSONDecodeError as error:
            fail(f"{path.relative_to(ROOT)}:{line_number}: invalid JSON: {error.msg}")
    return rows


def validate_case(case: dict, index: int) -> None:
    label = case.get("id", f"row-{index}")
    required = {"id", "category", "title", "prompt", "host_capability", "material_ambiguity", "expected"}
    missing = required - case.keys()
    if missing:
        fail(f"{label}: missing fields: {sorted(missing)}")
        return

    if case["host_capability"] not in CAPABILITIES:
        fail(f"{label}: invalid host_capability")

    expected = case["expected"]
    expected_fields = {
        "quality_mode",
        "overlays",
        "engines",
        "entry",
        "max_user_rounds",
        "max_agent_calls",
        "required_evidence",
        "max_rule_words",
        "forbidden_actions",
    }
    missing_expected = expected_fields - expected.keys()
    if missing_expected:
        fail(f"{label}: missing expected fields: {sorted(missing_expected)}")
        return

    if expected["quality_mode"] not in MODES:
        fail(f"{label}: invalid quality_mode")
    if set(expected["overlays"]) - {"Orchestrated"}:
        fail(f"{label}: invalid overlay")
    if set(expected["engines"]) - ENGINES:
        fail(f"{label}: invalid engine")
    if expected["entry"] is not None and expected["entry"] not in ENTRIES:
        fail(f"{label}: invalid thin entry")
    if not case["material_ambiguity"] and expected["max_user_rounds"] != 0:
        fail(f"{label}: non-ambiguous work must allow zero extra user rounds")
    if expected["quality_mode"] == "Direct":
        if expected["max_agent_calls"] != 0:
            fail(f"{label}: Direct work must default to zero agent calls")
        if expected["max_rule_words"] > 650:
            fail(f"{label}: Direct path exceeds 650 rule words")
    if expected["quality_mode"] == "Guarded" and "Orchestrated" not in expected["overlays"]:
        if expected["max_rule_words"] > 1500:
            fail(f"{label}: ordinary Guarded path exceeds 1500 rule words")


for required in [
    ROOT / ".agents" / "plugins" / "marketplace.json",
    PLUGIN / ".codex-plugin" / "plugin.json",
    MAIN,
    CASES,
    RESULTS,
]:
    require_file(required)

for engine in sorted(ENGINES):
    require_file(SKILLS / "goldilocks" / "references" / f"{engine}.md")

for entry in sorted(ENTRIES):
    path = SKILLS / entry / "SKILL.md"
    require_file(path)
    if path.is_file() and body_word_count(path) > 80:
        fail(f"thin entry exceeds 80 body words: {entry}")

skill_docs = sorted(SKILLS.glob("*/SKILL.md")) if SKILLS.is_dir() else []
skill_names = {path.parent.name for path in skill_docs}
expected_skill_names = ENTRIES | {"goldilocks"}
if skill_names != expected_skill_names:
    fail(
        "visible skill set mismatch: "
        f"expected {sorted(expected_skill_names)}, found {sorted(skill_names)}"
    )

main_metadata = SKILLS / "goldilocks" / "agents" / "openai.yaml"
require_file(main_metadata)
if main_metadata.is_file() and "allow_implicit_invocation: false" not in main_metadata.read_text(encoding="utf-8"):
    fail("goldilocks router must disable implicit invocation")

if MAIN.is_file() and word_count(MAIN) > 650:
    fail(f"main router exceeds 650 words: {word_count(MAIN)}")

docs = skill_docs + list((SKILLS / "goldilocks" / "references").glob("*.md"))
if docs:
    total_words = sum(word_count(path) for path in docs)
    if total_words > 6000:
        fail(f"capability documentation exceeds 6000 words: {total_words}")

cases = load_jsonl(CASES)
if not 40 <= len(cases) <= 60:
    fail(f"trigger suite must contain 40-60 cases, found {len(cases)}")

ids = [case.get("id") for case in cases]
if len(ids) != len(set(ids)):
    fail("trigger case ids must be unique")

for index, case in enumerate(cases, 1):
    validate_case(case, index)

covered_engines = {
    engine
    for case in cases
    for engine in case.get("expected", {}).get("engines", [])
}
if cases and covered_engines != ENGINES:
    fail(f"engine coverage mismatch: {sorted(covered_engines)}")

results = load_jsonl(RESULTS)
if RESULTS.is_file():
    if not results:
        fail("RED baseline results are empty")
    elif not any(result.get("valid") is True and result.get("status") == "FAIL" for result in results):
        fail("RED baseline must contain at least one valid observed failure")

    for engine in sorted(ENGINES):
        engine_path = SKILLS / "goldilocks" / "references" / f"{engine}.md"
        if engine_path.is_file() and not any(
            result.get("valid") is True
            and result.get("status") == "FAIL"
            and engine in result.get("gap_engines", [])
            for result in results
        ):
            fail(f"implemented engine lacks reproducible RED evidence: {engine}")

    for entry in sorted(ENTRIES):
        entry_path = SKILLS / entry / "SKILL.md"
        if entry_path.is_file() and not any(
            result.get("valid") is True
            and result.get("status") == "FAIL"
            and entry in result.get("gap_entries", [])
            for result in results
        ):
            fail(f"implemented thin entry lacks reproducible RED evidence: {entry}")

if failures:
    for message in failures:
        print(f"FAIL: {message}", file=sys.stderr)
    print(f"\n{len(failures)} Goldilocks v0.2 contract failure(s).", file=sys.stderr)
    raise SystemExit(1)

print(f"Goldilocks v0.2 contract passed with {len(cases)} trigger cases.")
