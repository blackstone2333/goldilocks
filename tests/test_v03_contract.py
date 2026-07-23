#!/usr/bin/env python3

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "0.3.0"
PLUGIN = ROOT / "plugins" / "goldilocks"
SKILLS = PLUGIN / "skills"
MAIN = SKILLS / "goldilocks" / "SKILL.md"
CONTINUITY = SKILLS / "goldilocks" / "references" / "continuity.md"
MODEL_ROUTING = SKILLS / "goldilocks" / "references" / "model-routing.md"
EXECUTION_MEMORY = SKILLS / "goldilocks" / "references" / "execution-memory.md"
MODEL_REGISTRY = SKILLS / "goldilocks" / "assets" / "model-registry.json"
MODEL_SURVEY = ROOT / "docs" / "model-routing-survey-2026-07-18.md"
ACTIVE_TASK = SKILLS / "goldilocks" / "assets" / "active-task.md"
COMPACT_PROMPT = SKILLS / "goldilocks" / "assets" / "codex-compact-prompt.md"
HOOK_CONFIG = PLUGIN / "hooks" / "hooks.json"
HOOK_SCRIPT = PLUGIN / "scripts" / "recovery_reminder.py"
ROUTING_HOOK_SCRIPT = PLUGIN / "scripts" / "agent_routing_guard.py"
TEMPLATE_ASSETS = {
    "active-task.md",
    "codex-compact-prompt.md",
    "project-map.md",
    "work-packet.md",
    "debug-note.md",
    "execution-pattern.md",
}
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
CLAUDE_PLUGIN = PLUGIN / ".claude-plugin" / "plugin.json"
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


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        fail(f"{path.relative_to(ROOT)}: invalid JSON: {error.msg}")
        return {}


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
        orchestrated = "Orchestrated" in expected["overlays"]
        allowed_calls = 1 if orchestrated else 0
        if expected["max_agent_calls"] > allowed_calls:
            fail(f"{label}: Direct work exceeds its make-or-delegate agent bound")
        if expected["max_rule_words"] > (1100 if orchestrated else 650):
            fail(f"{label}: Direct path exceeds its rule budget")
    if expected["quality_mode"] == "Guarded" and "Orchestrated" not in expected["overlays"]:
        if expected["max_rule_words"] > 1500:
            fail(f"{label}: ordinary Guarded path exceeds 1500 rule words")


for required in [
    ROOT / ".agents" / "plugins" / "marketplace.json",
    CLAUDE_MARKETPLACE,
    PLUGIN / ".codex-plugin" / "plugin.json",
    CLAUDE_PLUGIN,
    MAIN,
    CONTINUITY,
    MODEL_ROUTING,
    EXECUTION_MEMORY,
    MODEL_REGISTRY,
    MODEL_SURVEY,
    ACTIVE_TASK,
    COMPACT_PROMPT,
    HOOK_CONFIG,
    HOOK_SCRIPT,
    ROUTING_HOOK_SCRIPT,
    CASES,
    RESULTS,
    ROOT / "docs" / "installation.md",
    ROOT / "docs" / "installation.zh-CN.md",
    ROOT / "CHANGELOG.md",
    ROOT / "CHANGELOG.zh-CN.md",
]:
    require_file(required)

claude_marketplace = load_json(CLAUDE_MARKETPLACE)
if claude_marketplace:
    if claude_marketplace.get("name") != "goldilocks":
        fail("Claude marketplace name must be goldilocks")
    plugins = claude_marketplace.get("plugins", [])
    if len(plugins) != 1 or plugins[0].get("name") != "goldilocks":
        fail("Claude marketplace must expose exactly one goldilocks plugin")
    elif plugins[0].get("source") != "./plugins/goldilocks":
        fail("Claude marketplace source must point to ./plugins/goldilocks")

claude_plugin = load_json(CLAUDE_PLUGIN)
if claude_plugin:
    if claude_plugin.get("name") != "goldilocks":
        fail("Claude plugin name must be goldilocks")
    if claude_plugin.get("version") != RELEASE_VERSION:
        fail(f"Claude plugin version must be {RELEASE_VERSION}")

codex_plugin = load_json(PLUGIN / ".codex-plugin" / "plugin.json")
if codex_plugin:
    codex_version = codex_plugin.get("version", "").split("+", 1)[0]
    if codex_version != RELEASE_VERSION:
        fail(f"Codex plugin base version must be {RELEASE_VERSION}")

if claude_marketplace:
    marketplace_plugins = claude_marketplace.get("plugins", [])
    if marketplace_plugins and marketplace_plugins[0].get("version") != RELEASE_VERSION:
        fail(f"Claude marketplace version must be {RELEASE_VERSION}")

for readme_name in ["README.md", "README.zh-CN.md"]:
    readme_path = ROOT / readme_name
    require_file(readme_path)
    if readme_path.is_file():
        readme = readme_path.read_text(encoding="utf-8")
        for command in [
            "npx skills add blackstone2333/goldilocks",
            "codex plugin marketplace add blackstone2333/goldilocks",
            "claude plugin marketplace add blackstone2333/goldilocks",
        ]:
            if command not in readme:
                fail(f"{readme_name} lacks installation command: {command}")
        if f"version-{RELEASE_VERSION}" not in readme:
            fail(f"{readme_name} lacks the {RELEASE_VERSION} version badge")

for changelog_name, marker in [
    ("CHANGELOG.md", "Hierarchical Orchestration"),
    ("CHANGELOG.zh-CN.md", "分层动态编排"),
]:
    changelog_path = ROOT / changelog_name
    if changelog_path.is_file():
        changelog = changelog_path.read_text(encoding="utf-8")
        if RELEASE_VERSION not in changelog or marker not in changelog:
            fail(f"{changelog_name} lacks the {RELEASE_VERSION} orchestration release notes")

for engine in sorted(ENGINES):
    require_file(SKILLS / "goldilocks" / "references" / f"{engine}.md")

for template in sorted(TEMPLATE_ASSETS):
    require_file(SKILLS / "goldilocks" / "assets" / template)

markdown_assets = {
    path.name
    for path in (SKILLS / "goldilocks" / "assets").glob("*.md")
}
if markdown_assets != TEMPLATE_ASSETS:
    fail(
        "continuity template set mismatch: "
        f"expected {sorted(TEMPLATE_ASSETS)}, found {sorted(markdown_assets)}"
    )

if MAIN.is_file():
    main_text = MAIN.read_text(encoding="utf-8")
    if "Direct: do not create workflow continuity documents by default" not in main_text:
        fail("main router must keep Direct work free of default continuity overhead")
    if "documentation is the deliverable" not in main_text:
        fail("main router must preserve Direct documentation autonomy")
    if "continuity.md" not in main_text:
        fail("main router lacks conditional continuity routing")
    if ".goldilocks/ACTIVE.md" not in main_text:
        fail("main router lacks deterministic recovery routing")

for engine in sorted(ENGINES):
    engine_path = SKILLS / "goldilocks" / "references" / f"{engine}.md"
    if engine_path.is_file() and "continuity.md" not in engine_path.read_text(encoding="utf-8"):
        fail(f"{engine} engine lacks conditional continuity routing")

if CONTINUITY.is_file():
    continuity_text = CONTINUITY.read_text(encoding="utf-8")
    for required_text in [
        "docs/PROJECT.md",
        "docs/work/",
        "docs/debug/",
        "docs/ideas.md",
        "CHANGELOG.md",
        "Direct",
        "Guarded",
        "Critical",
        "regression test",
        "Do not create a debug note",
        ".goldilocks/ACTIVE.md",
        "ADD / REPLACE / CANCEL / QUESTION",
        "pending, applied, or superseded",
        "Exact next action",
        "Do not repeat",
        "repository state wins",
    ]:
        if required_text not in continuity_text:
            fail(f"continuity protocol lacks required contract: {required_text}")

if ACTIVE_TASK.is_file():
    active_text = ACTIVE_TASK.read_text(encoding="utf-8")
    for required_text in [
        "## Objective",
        "## Steering ledger",
        "### Done",
        "### In progress",
        "### Remaining",
        "### Exact next action",
        "## Repository state",
        "## Verification",
        "## Do not repeat",
        "## Terminal condition",
    ]:
        if required_text not in active_text:
            fail(f"active-task template lacks required section: {required_text}")
    if len(active_text.splitlines()) > 100:
        fail("active-task template exceeds 100 lines")

if COMPACT_PROMPT.is_file():
    compact_text = COMPACT_PROMPT.read_text(encoding="utf-8")
    for required_text in [
        "Steering ledger",
        "Exact next action",
        "Do not repeat",
        ".goldilocks/ACTIVE.md",
        "complete override",
    ]:
        if required_text not in compact_text:
            fail(f"Codex compact prompt lacks required contract: {required_text}")

hook_config = load_json(HOOK_CONFIG)
if hook_config:
    hook_events = set(hook_config.get("hooks", {}))
    for event in [
        "PreToolUse",
        "SubagentStart",
        "SubagentStop",
        "SessionStart",
        "PostCompact",
        "UserPromptSubmit",
    ]:
        if event not in hook_events:
            fail(f"hook config lacks event: {event}")
    routing_hook_config = json.dumps(hook_config.get("hooks", {}), ensure_ascii=False)
    if "agent_routing_guard.py" not in routing_hook_config:
        fail("hook config does not register the agent routing guard")
    pre_tool_groups = hook_config.get("hooks", {}).get("PreToolUse", [])
    if not any("Agent" in str(group.get("matcher", "")) for group in pre_tool_groups):
        fail("routing guard does not match the Agent alias")

if MODEL_ROUTING.is_file():
    routing_text = MODEL_ROUTING.read_text(encoding="utf-8")
    for required_text in [
        "quality gate",
        "Pareto",
        "expected cost per successful delivery",
        "confidence",
        "recency",
        "local evidence",
        "billing channel",
        "gpt-5.3-codex-spark",
        "separate usage limits",
        "test authoring",
        "combined verification",
        "fast__<name>",
        "fork_turns",
        "QuotaBurn",
        "raw-token envelope",
        "residual discretion",
        "full-history Lead handoff",
        "Ambiguous concurrent or nested starts",
    ]:
        if required_text not in routing_text:
            fail(f"model routing lacks required contract: {required_text}")

if EXECUTION_MEMORY.is_file():
    memory_text = EXECUTION_MEMORY.read_text(encoding="utf-8")
    for required_text in [
        "verified execution pattern",
        "invalidation check",
        "normal worker stop is an observation, not a verified success",
        "Keep `CHANGELOG.md` separate",
    ]:
        if required_text not in memory_text:
            fail(f"execution memory lacks required contract: {required_text}")

if ROUTING_HOOK_SCRIPT.is_file():
    guard_text = ROUTING_HOOK_SCRIPT.read_text(encoding="utf-8")
    for required_text in [
        "orchestration.db",
        "sqlite3",
        "Fast workers are leaf executors",
        'tier == "lead" and fork_value == "all"',
        'confidence = "ambiguous"',
        "verified_passes",
    ]:
        if required_text not in guard_text:
            fail(f"routing guard lacks v0.3 contract: {required_text}")

registry = load_json(MODEL_REGISTRY)
if registry:
    if registry.get("as_of") != "2026-07-18":
        fail("model registry must carry its evidence date")
    if len(registry.get("sources", [])) < 8:
        fail("model registry needs broad public benchmark and pricing sources")
    model_ids = {model.get("id") for model in registry.get("models", [])}
    for model_id in [
        "gpt-5.3-codex-spark",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
        "claude-fable-5",
        "grok-4.5",
        "muse-spark-1.1",
    ]:
        if model_id not in model_ids:
            fail(f"model registry lacks representative model: {model_id}")
    task_profiles = registry.get("task_profiles", {})
    for profile in [
        "mechanical_edit",
        "test_authoring",
        "repo_implementation",
        "exploration",
        "review_security",
        "frontend_multimodal",
    ]:
        if profile not in task_profiles:
            fail(f"model registry lacks task-specific scoring profile: {profile}")

orchestrate_path = SKILLS / "goldilocks" / "references" / "orchestrate.md"
if orchestrate_path.is_file():
    orchestrate_text = orchestrate_path.read_text(encoding="utf-8")
    for required_text in [
        "routing pass after planning",
        "make-or-delegate check",
        "Lead → Standard → Fast",
        "Fast is a leaf",
        "Do not impose a fixed worker count",
        "model-routing.md",
    ]:
        if required_text not in orchestrate_text:
            fail(f"orchestrate engine lacks parallel-first contract: {required_text}")

for engine in sorted(ENGINES - {"evolve"}):
    engine_path = SKILLS / "goldilocks" / "references" / f"{engine}.md"
    if engine_path.is_file() and "evolve.md" not in engine_path.read_text(encoding="utf-8"):
        fail(f"{engine} engine lacks conditional idea-capture routing")

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

verification_entry = SKILLS / "verification-before-completion" / "SKILL.md"
if verification_entry.is_file():
    verification_text = verification_entry.read_text(encoding="utf-8")
    if "Do not invoke for a clear Direct edit" not in verification_text:
        fail("verification entry must exclude clear Direct edits from implicit triggering")
    if "For clear Direct work, do not load another engine" not in verification_text:
        fail("verification entry must degrade safely when Direct work invokes it explicitly")

executing_entry = SKILLS / "executing-plans" / "SKILL.md"
if executing_entry.is_file():
    executing_text = executing_entry.read_text(encoding="utf-8")
    if "orchestrate.md" not in executing_text:
        fail("executing-plans must route multi-unit plans through orchestration")
    if "eligible independent units default to workers" not in executing_text:
        fail("executing-plans must not silently assign every unit to Lead")
    if "delegate by default" in executing_text:
        fail("executing-plans retains the v0.2.3 anti-delegation bias")

writing_entry = SKILLS / "writing-plans" / "SKILL.md"
if writing_entry.is_file() and "parallel waves" not in writing_entry.read_text(encoding="utf-8"):
    fail("writing-plans must expose routing-ready parallel waves")

if MAIN.is_file() and word_count(MAIN) > 650:
    fail(f"main router exceeds 650 words: {word_count(MAIN)}")

docs = skill_docs + list((SKILLS / "goldilocks" / "references").glob("*.md"))
if docs:
    total_words = sum(word_count(path) for path in docs)
    if total_words > 6800:
        fail(f"capability documentation exceeds 6800 words: {total_words}")

cases = load_jsonl(CASES)
if not 40 <= len(cases) <= 70:
    fail(f"trigger suite must contain 40-70 cases, found {len(cases)}")

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
    print(f"\n{len(failures)} Goldilocks v0.3 contract failure(s).", file=sys.stderr)
    raise SystemExit(1)

print(f"Goldilocks v0.3 contract passed with {len(cases)} trigger cases.")
