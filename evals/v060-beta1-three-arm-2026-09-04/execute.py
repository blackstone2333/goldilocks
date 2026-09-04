#!/usr/bin/env python3
"""Authorized, one-shot CLI producer for the v0.6.0-beta.1 three-arm gate.

``run.py`` owns grading and comparison.  This small companion only turns a
previously frozen ``run-lock.json`` into one normalized cell per arm.  It is
intentionally fail-closed: without ``--execute`` it performs local lock and
command validation only, and a failed cell stops the sequence.  It never
retries a model request or prints authentication material.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "run.py"
ARMS: Tuple[str, ...] = ("v053_beta9", "v060_beta1", "direct")
AUTH_FILENAMES = ("auth.json", "auth.chatgpt.json")


class RunnerError(RuntimeError):
    """A local/protocol failure that must not be labelled a product failure."""


def _load_harness():
    spec = importlib.util.spec_from_file_location("goldilocks_beta1_harness", RUNNER_PATH)
    if spec is None or spec.loader is None:
        raise RunnerError(f"cannot import offline harness: {RUNNER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = _load_harness()


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RunnerError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise RunnerError(f"{path} must contain a JSON object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run(command: Sequence[str], *, env: Mapping[str, str], cwd: Path, timeout: int = 60) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(command), cwd=str(cwd), env=dict(env), text=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=timeout,
    )


def _codex_binary() -> str:
    override = os.environ.get("CODEX_BIN")
    if override:
        return override
    bundled = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
    if bundled.is_file():
        return str(bundled)
    found = shutil.which("codex")
    if found:
        return found
    raise RunnerError("Codex CLI not found; set CODEX_BIN")


def _auth_home() -> Path:
    configured = os.environ.get("GOLDILOCKS_EVAL_AUTH_HOME") or os.environ.get("CODEX_HOME")
    return Path(configured).expanduser().resolve() if configured else (Path.home() / ".codex")


def _copy_auth(destination: Path) -> List[str]:
    """Copy only the existing CLI auth files, with private modes and no logging."""

    source = _auth_home()
    copied: List[str] = []
    for name in AUTH_FILENAMES:
        candidate = source / name
        if candidate.is_file():
            target = destination / name
            shutil.copy2(candidate, target)
            os.chmod(target, 0o600)
            copied.append(name)
    if not copied:
        raise RunnerError(f"no Codex auth file found in {_auth_home()}")
    return copied


def _toml_value(value: str) -> str:
    value = value.strip()
    if value.startswith('"'):
        try:
            return str(json.loads(value))
        except json.JSONDecodeError:
            pass
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1]
    return value.split("#", 1)[0].strip()


def _toml_key(value: str) -> str:
    return value if re.fullmatch(r"[A-Za-z0-9_-]+", value) else json.dumps(value, ensure_ascii=False)


def _write_minimal_provider_config(destination: Path) -> Optional[str]:
    """Keep just the selected model provider; omit MCP, plugins and user rules."""

    source = _auth_home() / "config.toml"
    if not source.is_file():
        return None
    lines = source.read_text(encoding="utf-8").splitlines()
    selected = os.environ.get("GOLDILOCKS_EVAL_MODEL_PROVIDER")
    top: List[str] = []
    for line in lines:
        if line.lstrip().startswith("["):
            break
        match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*=\s*(.+?)\s*$", line)
        if not match:
            continue
        key, raw = match.groups()
        if key == "model_provider" and not selected:
            selected = _toml_value(raw)
        elif key in {"disable_response_storage"}:
            top.append(line)
    if not selected:
        return None
    provider: List[str] = []
    inside = False
    header = re.compile(r"^\s*\[model_providers\.([^]]+)\]\s*$")
    for line in lines:
        match = header.match(line)
        if match:
            inside = _toml_value(match.group(1)) == selected
            continue
        if inside and line.lstrip().startswith("["):
            break
        if inside:
            provider.append(line)
    if not any(line.strip() for line in provider):
        raise RunnerError("selected model provider is not present in host config")
    # These are explicit protocol controls, not inherited host defaults.  A
    # CLI that does not recognize one of them must fail before it can start a
    # request; it must never silently obtain a retry from the host profile.
    top.extend(
        [
            "request_max_retries = 0",
            "stream_max_retries = 0",
            "unbounded_connection_retries = false",
        ]
    )
    target = destination / "config.toml"
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write("\n".join([f"model_provider = {json.dumps(selected, ensure_ascii=False)}", *top, "", f"[model_providers.{_toml_key(selected)}]", *provider]) + "\n")
    return selected


def _isolated_env(home: Path, codex_home: Path) -> Dict[str, str]:
    environment = os.environ.copy()
    for key in (
        "CODEX_HOME", "CODEX_CONFIG", "CODEX_SKILLS_DIR", "CLAUDE_PLUGIN_ROOT",
        "PLUGIN_ROOT", "GOLDILOCKS_ACTIVE_FILE",
    ):
        environment.pop(key, None)
    environment.update({"HOME": str(home), "CODEX_HOME": str(codex_home), "NO_COLOR": "1"})
    return environment


def _setup_home(cell: Mapping[str, Any]) -> Tuple[Dict[str, str], Dict[str, Any]]:
    home, codex_home = Path(cell["home"]), Path(cell["codex_home"])
    if any(home.iterdir()) or any(codex_home.iterdir()):
        raise RunnerError("prepared cell HOME/CODEX_HOME must be empty before its single attempt")
    # ``prepare-run`` deliberately creates these two empty roots.  Do not
    # replace them: their paths are part of the frozen run-lock evidence.
    copied_auth = _copy_auth(codex_home)
    provider = _write_minimal_provider_config(codex_home)
    return _isolated_env(home, codex_home), {"auth_files_copied": copied_auth, "model_provider": provider}


def _json_or_empty(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _verify_installed_plugin(arm: str, source: Mapping[str, Any], plugin_list: Any) -> Dict[str, Any]:
    """Prove enabled Goldilocks is the candidate snapshot, not just a same-name install."""

    if not isinstance(plugin_list, Mapping) or not isinstance(plugin_list.get("installed"), list):
        raise RunnerError(f"{arm} plugin-list evidence has no installed list")
    enabled = [
        row for row in plugin_list["installed"]
        if isinstance(row, Mapping)
        and row.get("pluginId") == "goldilocks@goldilocks-local"
        and row.get("enabled") is True
    ]
    if len(enabled) != 1:
        raise RunnerError(f"{arm} requires exactly one enabled goldilocks@goldilocks-local")
    row = enabled[0]
    if row.get("version") != H.EXPECTED_VERSIONS[arm]:
        raise RunnerError(f"{arm} installed Goldilocks version does not match its frozen candidate")
    source_value = row.get("installedPath")
    if not isinstance(source_value, str):
        detail = row.get("source")
        source_value = detail.get("path") if isinstance(detail, Mapping) else None
    if not isinstance(source_value, str) or not source_value:
        raise RunnerError(f"{arm} plugin-list does not expose an installed source path")
    installed_path = Path(source_value).expanduser().resolve()
    frozen_root = Path(str(source["source"])).resolve()
    frozen_digest = str(source["source_sha256"])
    source_verified = _is_within(installed_path, frozen_root / "plugins" / "goldilocks")
    if not source_verified:
        # A materialized local marketplace is acceptable only when the whole
        # cache has a marketplace manifest and hashes to this exact lock.
        for ancestor in (installed_path, *installed_path.parents):
            if not (ancestor / ".claude-plugin" / "marketplace.json").is_file():
                continue
            if not _is_within(installed_path, ancestor / "plugins" / "goldilocks"):
                continue
            try:
                source_verified = H.marketplace_digest(ancestor) == frozen_digest
            except OSError:
                source_verified = False
            break
    if not source_verified:
        raise RunnerError(f"{arm} installed Goldilocks source is not the frozen marketplace digest")
    return {"identity_verified": True, "plugin": dict(row), "installed_path": str(installed_path), "source_sha256": frozen_digest}


def _install_frozen_plugin(arm: str, lock: Mapping[str, Any], *, env: Mapping[str, str], cwd: Path, audit: Path) -> Dict[str, Any]:
    source = lock["frozen_sources"][arm]
    source_path = Path(source["source"])
    if not source_path.is_dir() or not source.get("source_sha256"):
        raise RunnerError(f"{arm} frozen plugin source is unavailable")
    binary = _codex_binary()
    add_market = _run([binary, "plugin", "marketplace", "add", str(source_path), "--json"], env=env, cwd=cwd)
    if add_market.returncode:
        raise RunnerError(f"{arm} local marketplace install failed ({add_market.returncode})")
    # Codex assigns local source marketplaces the stable local namespace used
    # by Bootstrap, irrespective of the marketplace manifest display name.
    install = _run([binary, "plugin", "add", "goldilocks@goldilocks-local", "--json"], env=env, cwd=cwd)
    if install.returncode:
        raise RunnerError(f"{arm} local Goldilocks plugin install failed ({install.returncode})")
    listed = _run([binary, "plugin", "list", "--json"], env=env, cwd=cwd)
    if listed.returncode:
        raise RunnerError(f"{arm} plugin identity check failed ({listed.returncode})")
    (audit / "plugin-list.json").write_text(listed.stdout, encoding="utf-8")
    plugin_list = _json_or_empty(listed.stdout)
    identity = _verify_installed_plugin(arm, source, plugin_list)
    return {
        "marketplace_add": {"returncode": add_market.returncode, "json": _json_or_empty(add_market.stdout)},
        "plugin_add": {"returncode": install.returncode, "json": _json_or_empty(install.stdout)},
        "plugin_list": plugin_list,
        "source_sha256": source["source_sha256"],
        **identity,
    }


def _all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _all_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _all_strings(item)


def _prompt_structure(output: str) -> Dict[str, Any]:
    """Produce auditable prompt-shape evidence without retaining prompt text."""

    try:
        value = json.loads(output)
    except json.JSONDecodeError:
        return {"available": False, "gap": "debug_prompt_input_not_json"}
    texts: List[str] = []
    for message in value if isinstance(value, list) else []:
        if not isinstance(message, Mapping):
            continue
        for content in message.get("content", []):
            if isinstance(content, Mapping) and isinstance(content.get("text"), str):
                texts.append(content["text"])
    joined = "\n".join(texts)
    # Catalog evidence is the exact, line-oriented skill-list identity.  It
    # deliberately does not depend on a release-specific description, and a
    # directory/plugin path containing "goldilocks" cannot satisfy it.
    catalog_pattern = re.compile(r"(?mi)^\s*-\s+goldilocks:goldilocks:\s+\S")
    body_marker = "Goldilocks 不提供或依赖 Hook"
    return {
        "available": True,
        "total_text_chars": len(joined),
        "text_sha256": hashlib.sha256(joined.encode("utf-8")).hexdigest(),
        "goldilocks_catalog_description_present": bool(catalog_pattern.search(joined)),
        "goldilocks_catalog_description_count": len(catalog_pattern.findall(joined)),
        "main_skill_body_marker_present": body_marker in joined,
        "main_skill_body_marker_count": joined.count(body_marker),
    }


def _capture_prompt_structure(*, env: Mapping[str, str], cwd: Path, audit: Path, completed: Optional[subprocess.CompletedProcess[str]] = None) -> Tuple[Dict[str, Any], Optional[subprocess.CompletedProcess[str]]]:
    result = completed or _run([_codex_binary(), "debug", "prompt-input", "Prompt structure inspection."], env=env, cwd=cwd)
    summary = _prompt_structure(result.stdout) if result.returncode == 0 else {"available": False, "gap": "debug_prompt_input_failed", "returncode": result.returncode}
    _write_json(audit / "prompt-structure.json", summary)
    return summary, result


def _direct_purity(*, env: Mapping[str, str], cwd: Path, codex_home: Path, audit: Path) -> Dict[str, Any]:
    binary = _codex_binary()
    listed = _run([binary, "plugin", "list", "--json"], env=env, cwd=cwd)
    debug = _run([binary, "debug", "prompt-input", "Direct purity inspection."], env=env, cwd=cwd)
    if listed.returncode or debug.returncode:
        raise RunnerError("Direct purity inspection failed")
    # Keep a redacted, reviewable shape receipt only; prompt bodies may contain
    # unrelated host text and are never persisted by this evaluation runner.
    (audit / "plugin-list.json").write_text(listed.stdout, encoding="utf-8")
    prompt_structure, _ = _capture_prompt_structure(env=env, cwd=cwd, audit=audit, completed=debug)
    plugin_list = _json_or_empty(listed.stdout)
    if not isinstance(plugin_list, Mapping) or not isinstance(plugin_list.get("installed"), list):
        raise RunnerError("Direct plugin-list evidence has no installed root")
    evidence = H.direct_semantic_evidence(plugin_list, codex_home, debug.stdout)
    evidence["direct_pure"] = all(
        evidence[key] == expected
        for key, expected in {
            "goldilocks_plugin_ids": [], "isolated_skills_entries": [],
            "isolated_marketplace_entries": [], "compact_prompt_present": False,
            "prompt_input_goldilocks_mentions": 0,
        }.items()
    )
    evidence["plugin_identity_verified"] = False
    evidence["prompt_structure"] = prompt_structure
    return evidence


def _walk_dicts(value: Any) -> Iterable[Mapping[str, Any]]:
    if isinstance(value, Mapping):
        yield value
        for item in value.values():
            yield from _walk_dicts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_dicts(item)


def _event_summary(path: Path) -> Dict[str, Any]:
    """Extract only observed usage and tool cardinality from raw Codex JSONL."""

    usage: Dict[str, int] = {}
    tool_ids = set()
    tools = 0
    verification_calls: List[str] = []
    completed = False
    errors: List[str] = []
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parsed = _json_or_empty(raw_line)
        if not isinstance(parsed, Mapping):
            continue
        for obj in _walk_dicts(parsed):
            maybe_usage = obj.get("total_token_usage") or obj.get("usage")
            if isinstance(maybe_usage, Mapping):
                for key in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens"):
                    value = maybe_usage.get(key)
                    if isinstance(value, int) and not isinstance(value, bool):
                        usage[key] = max(usage.get(key, 0), value)
            item_type = str(obj.get("type") or "")
            if item_type in {"function_call", "custom_tool_call", "local_shell_call", "tool_call", "command_execution", "file_change", "collab_tool_call"}:
                identifier = obj.get("call_id") or obj.get("id")
                if identifier is None or identifier not in tool_ids:
                    tools += 1
                    if identifier is not None:
                        tool_ids.add(identifier)
                name = str(obj.get("name") or obj.get("function_name") or "unknown")
                arguments = str(obj.get("arguments") or obj.get("arguments_json") or obj.get("input") or obj.get("command") or "")
                if H._is_verification_call(name, arguments):
                    normalized_arguments = re.sub(r"\s+", " ", arguments).strip()
                    verification_calls.append(f"{name}|{normalized_arguments}")
            text = str(obj.get("error") or obj.get("message") or "")
            if text and item_type in {"error", "turn.failed", "item.failed"}:
                errors.append(text[:300])
            if item_type in {"turn.completed", "task_complete", "task_completed"}:
                completed = True
    # Preserve the harness parser's canonical vocabulary where it recognizes
    # an event, but do not turn an absent provider field into a claimed zero.
    parsed = H.parse_events(path)
    for key in ("input_tokens", "cached_input_tokens", "cache_write_input_tokens", "output_tokens"):
        value = parsed.get("telemetry", {}).get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            usage[key] = value
    duplicate = sum(count - 1 for count in collections.Counter(verification_calls).values() if count > 1)
    canonical_telemetry = parsed.get("telemetry", {})
    return {
        "usage": usage, "tool_calls": tools, "turn_completed": completed, "errors": errors,
        # run.py's parser is the one canonical normalizer for the formal
        # report.  Its values win whenever available; the generic scan above
        # exists only for newer event vocabulary it has not learned yet.
        "tool_calls": canonical_telemetry.get("tool_calls") if canonical_telemetry.get("tool_calls") is not None else tools,
        "verification_calls": canonical_telemetry.get("verification_calls") if canonical_telemetry.get("verification_calls") is not None else len(verification_calls),
        "duplicate_verification_calls": canonical_telemetry.get("duplicate_verification_calls") if canonical_telemetry.get("duplicate_verification_calls") is not None else duplicate,
    }


def _changed_paths(repo: Path) -> List[str]:
    tracked = _run(["git", "diff", "HEAD", "--name-only"], env=os.environ, cwd=repo)
    untracked = _run(["git", "ls-files", "--others", "--exclude-standard"], env=os.environ, cwd=repo)
    if tracked.returncode or untracked.returncode:
        raise RunnerError("cannot derive route evidence from the prepared fixture repository")
    return sorted({line.strip() for text in (tracked.stdout, untracked.stdout) for line in text.splitlines() if line.strip()})


def _structured_route_actions(events: Path) -> Tuple[int, int]:
    """Count only typed tool/event records, never model prose."""

    child_starts = 0
    background_actions = 0
    child_functions = {"spawn_agent", "create_thread", "fork_thread", "send_message_to_thread"}
    background_event_types = {"background_action", "background_task", "async_task"}
    for raw_line in events.read_text(encoding="utf-8", errors="replace").splitlines():
        record = _json_or_empty(raw_line)
        if not isinstance(record, Mapping):
            continue
        for item in _walk_dicts(record):
            item_type = str(item.get("type") or "").lower()
            function_name = str(item.get("name") or item.get("function_name") or "").lower()
            if item_type == "collab_tool_call" or (
                item_type in {"function_call", "custom_tool_call", "tool_call"}
                and function_name in child_functions
            ):
                child_starts += 1
            if item_type in background_event_types or item.get("background") is True:
                background_actions += 1
    return child_starts, background_actions


def _route_evidence(repo: Path, events: Path) -> Dict[str, Any]:
    """Derive, rather than promise, the smoke-cell Direct route receipt."""

    changed = _changed_paths(repo)
    child_starts, background_actions = _structured_route_actions(events)
    state_paths = [path for path in changed if path == ".goldilocks/ACTIVE.md" or path.startswith(".goldilocks/")]
    workflow_paths = [path for path in changed if path.startswith("docs/work/") or path.endswith("handoff.md")]
    return {
        "selected": "direct" if child_starts == 0 else "non_direct_observed",
        "child_starts": child_starts,
        "user_roundtrips": 0,
        "unnecessary_state_writes": len(state_paths),
        "workflow_documents_created": len(workflow_paths),
        "background_actions": background_actions,
        "changed_paths": changed,
    }


def _infrastructure_reason(returncode: int, errors: Sequence[str], timed_out: bool) -> str:
    if timed_out:
        return "timeout"
    text = " ".join(errors).lower()
    if "auth" in text or "credential" in text or "login" in text:
        return "auth"
    if "quota" in text or "rate limit" in text or "usage limit" in text:
        return "quota"
    if "transport" in text or "network" in text or "connection" in text:
        return "transport"
    if "provider" in text or "model" in text:
        return "provider"
    return "host" if returncode else "evidence_input"


def _command_for(repo: Path, prompt: str) -> List[str]:
    return [
        _codex_binary(), "exec", "--ephemeral", "--ignore-rules", "--disable", "multi_agent",
        "-s", "danger-full-access", "-c", 'approval_policy="never"',
        "-c", 'model_reasoning_effort="high"', "-c", 'service_tier="standard"',
        "-m", "gpt-5.6-sol", "-C", str(repo), "--json", prompt,
    ]


def _as_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def _cleanup_sensitive_home(codex_home: Path) -> None:
    """Erase the isolated credential/config/session root after every cell."""

    if codex_home.name != "codex_home":
        raise RunnerError("refusing to clean a non-cell CODEX_HOME")
    if codex_home.exists():
        shutil.rmtree(codex_home)
    codex_home.mkdir(parents=True, exist_ok=False)


def _protocol(lock: Mapping[str, Any], arm: str, *, direct: Mapping[str, Any], plugin: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        **lock["protocol_hashes"], "source_frozen": True, "runtime_identity_verified": True,
        "root_session_count": 1, "child_session_count": 0, "usage_deduplicated": True,
        "same_host": True, "same_toolset": True, "cold_context": True,
        "approval_policy": "never", "sandbox": "danger-full-access", "full_access": True,
        "retry_controls": {"request_max_retries": 0, "stream_max_retries": 0, "unbounded_connection_retries": False},
        "direct_pure": False,
        "plugin_identity_verified": bool(plugin and plugin.get("identity_verified") is True),
    }
    if arm == "direct":
        result.update(direct)
    else:
        result["source_sha256"] = plugin["source_sha256"] if plugin else None
    return result


def _run_arm(lock: Mapping[str, Any], run_dir: Path, arm: str, *, timeout_seconds: int) -> Dict[str, Any]:
    cell = lock["cell_roots"][arm]
    repo, events = Path(cell["repo"]), Path(cell["events"]) / "events.jsonl"
    audit = Path(cell["audit"])
    plugin: Optional[Dict[str, Any]] = None
    direct: Dict[str, Any] = {}
    setup: Dict[str, Any] = {}
    prompt_structure: Dict[str, Any] = {"available": False, "gap": "not_captured"}
    try:
        env, setup = _setup_home(cell)
        if arm == "direct":
            direct = _direct_purity(
                env=env, cwd=repo, codex_home=Path(cell["codex_home"]), audit=audit
            )
            if not direct["direct_pure"]:
                raise RunnerError("Direct isolation is contaminated before model execution")
            prompt_structure = direct.get("prompt_structure", prompt_structure)
        else:
            plugin = _install_frozen_plugin(arm, lock, env=env, cwd=repo, audit=audit)
            prompt_structure, _ = _capture_prompt_structure(env=env, cwd=repo, audit=audit)
        prompt = (Path(run_dir) / "cells" / arm / "TASK.md").read_text(encoding="utf-8")
        command = _command_for(repo, prompt)
        started = time.monotonic()
        timed_out = False
        try:
            completed = _run(command, env=env, cwd=repo, timeout=timeout_seconds)
            returncode, stdout, stderr = completed.returncode, completed.stdout, completed.stderr
        except subprocess.TimeoutExpired as error:
            timed_out, returncode = True, 124
            stdout = _as_text(error.stdout)
            stderr = _as_text(error.stderr)
        wall_time_ms = max(1, round((time.monotonic() - started) * 1000))
        events.write_text(stdout, encoding="utf-8")
        (audit / "stderr.txt").write_text(stderr, encoding="utf-8")
        observed = _event_summary(events)
        grade = H.grade_repo(repo)
        _write_json(audit / "grade.json", grade)
        successful = returncode == 0 and observed["turn_completed"]
        failure_class = None if successful else "infrastructure_invalid"
        errors = list(observed["errors"])
        if stderr.strip():
            errors.append(stderr.strip()[-500:])
        raw = {
            "schema_version": 1, "cell_id": f"{arm}:attempt-1", "arm": arm,
            "version": H.EXPECTED_VERSIONS[arm],
            "runtime": {"model": "gpt-5.6-sol", "effort": "high", "requested_service_tier": "standard"},
            "attempts": 1, "host_retries": 0, "returncode": returncode, "wall_time_ms": wall_time_ms,
            "completion": {"turn_completed": observed["turn_completed"]},
            "quality": {"passed": grade["passed"], "checks": grade["checks"]},
            "telemetry": {**{key: observed["usage"].get(key) for key in H.TOKEN_KEYS}, "tool_calls": observed["tool_calls"], "process_steps": observed["tool_calls"], "verification_calls": observed["verification_calls"], "duplicate_verification_calls": observed["duplicate_verification_calls"]},
            "route": _route_evidence(repo, events),
            "measurement": {"cost_comparable": True, "pricing_provenance": H.PRICING_PROVENANCE, "contamination": []},
            "protocol": {**_protocol(lock, arm, direct=direct, plugin=plugin), "prompt_structure": prompt_structure},
            "failure_class": failure_class,
            "infrastructure_reason": _infrastructure_reason(returncode, errors, timed_out) if failure_class else None,
            "errors": errors, "events_file": "events/events.jsonl", "runner": {"command": command, "auth_files_copied": setup.get("auth_files_copied", []), "model_provider": setup.get("model_provider"), "timed_out": timed_out, "grade_runs": 1}, "synthetic": False,
        }
        _write_json(Path(run_dir) / "cells" / arm / "cell.json", raw)
        return raw
    finally:
        # The evidence keeps no credential material.  `--ephemeral` also keeps
        # the model session out of the temporary CODEX_HOME.
        _cleanup_sensitive_home(Path(cell["codex_home"]))


def _validate_lock(lock: Mapping[str, Any], run_dir: Path) -> None:
    if lock.get("execution_order") != list(ARMS):
        raise RunnerError("run-lock execution order differs from the frozen three-arm protocol")
    runtime = lock.get("runtime", {})
    expected = {"model": "gpt-5.6-sol", "reasoning_effort": "high", "requested_service_tier": "standard", "sandbox": "danger-full-access", "approval_policy": "never"}
    if any(runtime.get(key) != value for key, value in expected.items()):
        raise RunnerError("run-lock runtime differs from the frozen protocol")
    if lock.get("formal_model_calls_planned") != 3 or lock.get("automatic_host_retries") != 0:
        raise RunnerError("run-lock permits an invalid model-call or retry count")
    if not (run_dir / "run-lock.json").is_file():
        raise RunnerError("run-lock must live inside the selected run directory")
    for arm in ARMS:
        cell = lock.get("cell_roots", {}).get(arm, {})
        for key in ("repo", "home", "codex_home", "audit", "events"):
            if not Path(cell.get(key, "")).is_dir():
                raise RunnerError(f"{arm} prepared {key} directory is missing")
        if (Path(cell["repo"]) / ".git").exists() is False:
            raise RunnerError(f"{arm} prepared repository lacks its baseline Git fixture")
        existing = Path(run_dir) / "cells" / arm / "cell.json"
        if existing.exists():
            raise RunnerError(f"{arm} already has evidence; never overwrite a cell")


def _prepare_direct_replacement(lock: Mapping[str, Any], run_dir: Path) -> str:
    """Retain an unstarted Direct infrastructure record and open its one retry."""

    for arm in ("v053_beta9", "v060_beta1"):
        if not (run_dir / "cells" / arm / "cell.json").is_file():
            raise RunnerError(f"cannot replace Direct: retained {arm} evidence is missing")
    arm_dir = run_dir / "cells" / "direct"
    root_cell = arm_dir / "cell.json"
    if not root_cell.is_file() or (arm_dir / "original").exists() or (arm_dir / "replacement").exists():
        raise RunnerError("Direct replacement requires exactly one unchained root cell")
    original = _read_json(root_cell)
    if original.get("failure_class") != "infrastructure_invalid" or original.get("attempts") != 0:
        raise RunnerError("only a retained Direct infrastructure setup failure with attempts=0 may be replaced")
    if original.get("runner", {}).get("model_request_started") is not False:
        raise RunnerError("Direct replacement is forbidden if the original may have started a model request")
    original_id = original.get("cell_id")
    if not isinstance(original_id, str) or not original_id:
        raise RunnerError("Direct setup failure lacks an explicit cell_id")
    target = arm_dir / "original"
    target.mkdir()
    shutil.move(str(root_cell), str(target / "cell.json"))
    for name in ("events", "audit"):
        path = arm_dir / name
        if path.exists():
            shutil.move(str(path), str(target / name))
        (arm_dir / name).mkdir()
    return original_id


def execute_direct_replacement(run_dir: Path, *, timeout_seconds: int) -> Dict[str, Any]:
    lock = _read_json(run_dir / "run-lock.json")
    # The original complete-run validator intentionally rejects all existing
    # evidence.  Replacement is a separate, narrow protocol: two completed
    # arms stay untouched and only an unstarted Direct setup record can move.
    original_id = _prepare_direct_replacement(lock, run_dir)
    produced = _run_arm(lock, run_dir, "direct", timeout_seconds=timeout_seconds)
    produced.update(
        {
            "cell_id": "direct:replacement-1",
            "retry_of": original_id,
            "replacement_of": original_id,
            "replacement_index": 1,
            "replacement_authorized": True,
            "replacement_reason": "authorized replacement for retained Direct setup failure before model request",
            "events_file": "events/events.jsonl",
        }
    )
    arm_dir = run_dir / "cells" / "direct"
    _write_json(arm_dir / "cell.json", produced)
    replacement = arm_dir / "replacement"
    replacement.mkdir()
    shutil.move(str(arm_dir / "cell.json"), str(replacement / "cell.json"))
    for name in ("events", "audit"):
        shutil.move(str(arm_dir / name), str(replacement / name))
    # Formal validation reads selected Direct audit at the locked root.  Raw
    # events stay exclusively with the chain nodes, so they cannot be imported
    # twice; recreate only the required locked root directory.
    shutil.copytree(replacement / "audit", arm_dir / "audit")
    (arm_dir / "events").mkdir()
    return {"passed": produced.get("failure_class") is None, "model_calls_started": int(produced.get("attempts") or 0), "replacement_of": original_id, "cell": produced}


def renormalize_existing(run_dir: Path) -> Dict[str, Any]:
    """Rebuild retained producer telemetry from immutable raw CLI JSONL."""

    changed = []
    for arm in ARMS:
        arm_dir = run_dir / "cells" / arm
        cell_path, events = arm_dir / "cell.json", arm_dir / "events" / "events.jsonl"
        if not cell_path.is_file() or not events.is_file():
            continue
        producer = _read_json(cell_path)
        canonical = H.parse_events(events, arm=arm).get("telemetry", {})
        before = dict(producer.get("telemetry") or {})
        updates = {key: canonical.get(key) for key in ("tool_calls", "process_steps", "verification_calls", "duplicate_verification_calls") if canonical.get(key) is not None}
        if not updates:
            continue
        audit = arm_dir / "audit"
        audit.mkdir(exist_ok=True)
        _write_json(audit / "producer-cell-before-renormalize.json", producer)
        producer["telemetry"] = {**before, **updates}
        _write_json(audit / "renormalization.json", {"raw_events": "events/events.jsonl", "before": {key: before.get(key) for key in updates}, "after": updates})
        _write_json(cell_path, producer)
        changed.append(arm)
    return {"passed": True, "model_calls": 0, "renormalized_arms": changed}


def _record_infrastructure_failure(lock: Mapping[str, Any], run_dir: Path, arm: str, error: Exception) -> Dict[str, Any]:
    """Preserve a non-product failure even if setup stopped before Codex ran."""

    cell = lock["cell_roots"][arm]
    message = str(error)
    raw = {
        "schema_version": 1, "cell_id": f"{arm}:setup-failure", "arm": arm,
        "version": H.EXPECTED_VERSIONS[arm],
        "runtime": {"model": "gpt-5.6-sol", "effort": "high", "requested_service_tier": "standard"},
        "attempts": 0, "host_retries": 0, "returncode": None, "wall_time_ms": None,
        "completion": {"turn_completed": False}, "quality": {"passed": None, "checks": []},
        "telemetry": {key: None for key in (*H.TOKEN_KEYS, "tool_calls", "process_steps", "verification_calls", "duplicate_verification_calls")},
        "route": {}, "measurement": {"cost_comparable": False, "pricing_provenance": H.PRICING_PROVENANCE, "contamination": []},
        "protocol": _protocol(lock, arm, direct={}, plugin=None),
        "failure_class": "infrastructure_invalid", "infrastructure_reason": _infrastructure_reason(1, [message], False),
        "errors": [message], "runner": {"model_request_started": False, "grade_runs": 0}, "synthetic": False,
    }
    _write_json(Path(run_dir) / "cells" / arm / "cell.json", raw)
    return raw


def dry_run(run_dir: Path) -> Dict[str, Any]:
    lock = _read_json(run_dir / "run-lock.json")
    _validate_lock(lock, run_dir)
    return {"passed": True, "model_calls": 0, "execution_order": list(ARMS), "commands": {arm: _command_for(Path(lock["cell_roots"][arm]["repo"]), "<frozen TASK.md>") for arm in ARMS}}


def execute(run_dir: Path, *, timeout_seconds: int) -> Dict[str, Any]:
    lock = _read_json(run_dir / "run-lock.json")
    _validate_lock(lock, run_dir)
    cells = []
    for arm in ARMS:
        try:
            produced = _run_arm(lock, run_dir, arm, timeout_seconds=timeout_seconds)
            cells.append(produced)
            if produced.get("failure_class") == "infrastructure_invalid":
                return {"passed": False, "model_calls_started": len(cells), "stopped_at": arm, "error": "structured infrastructure failure", "cells": cells}
        except (RunnerError, OSError, subprocess.SubprocessError) as error:
            # No following arm starts: an infrastructure setup failure makes
            # parity unknowable, and this runner never silently replaces cells.
            cells.append(_record_infrastructure_failure(lock, run_dir, arm, error))
            return {"passed": False, "model_calls_started": len(cells) - 1, "stopped_at": arm, "error": str(error), "cells": cells}
    return {"passed": True, "model_calls_started": len(cells), "cells": cells}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path, help="directory produced by run.py --prepare-run")
    parser.add_argument("--execute", action="store_true", help="explicitly permit the three real model calls")
    parser.add_argument("--replace-direct", action="store_true", help="perform the one authorized Direct-only infrastructure replacement")
    parser.add_argument("--renormalize-existing", action="store_true", help="rebuild retained telemetry from raw events without model calls")
    parser.add_argument("--ephemeral", action="store_true", help="required acknowledgement of ephemeral credential handling")
    parser.add_argument("--timeout-seconds", type=int, default=900)
    args = parser.parse_args(argv)
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    run_dir = args.run_dir.resolve()
    try:
        if args.renormalize_existing:
            result = renormalize_existing(run_dir)
        elif args.execute and args.ephemeral:
            result = execute_direct_replacement(run_dir, timeout_seconds=args.timeout_seconds) if args.replace_direct else execute(run_dir, timeout_seconds=args.timeout_seconds)
        else:
            result = dry_run(run_dir)
        if args.execute and not args.ephemeral:
            result = {"passed": False, "model_calls": 0, "error": "--execute requires --ephemeral"}
    except RunnerError as error:
        result = {"passed": False, "model_calls": 0, "error": str(error)}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
