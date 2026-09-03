#!/usr/bin/env python3

"""Explicit bootstrap for portable Goldilocks installation and native-host upgrades."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import re
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
try:
    import tomllib
except ImportError:
    tomllib = None  # type: ignore[assignment]
from _vendor import tomli
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "assets" / "bootstrap-agents"
TEMPLATE_FILES = (
    "goldilocks-spark-worker.toml",
    "goldilocks-luna-economy.toml",
    "goldilocks-terra-engineer.toml",
    "goldilocks-sol-reviewer.toml",
)
ROLE_SPECS = (
    (
        "goldilocks_spark_worker",
        "goldilocks-spark-worker.toml",
        "Goldilocks native Spark XHigh Fast leaf for deterministic coding and focused tests.",
    ),
    (
        "goldilocks_luna_economy",
        "goldilocks-luna-economy.toml",
        "Goldilocks native Luna Max Fast leaf for latency-tolerant economy work.",
    ),
    (
        "goldilocks_terra_engineer",
        "goldilocks-terra-engineer.toml",
        "Goldilocks Standard engineer for one bounded domain with material local judgment.",
    ),
    (
        "goldilocks_sol_reviewer",
        "goldilocks-sol-reviewer.toml",
        "Goldilocks fresh-context review-only specialist for high-risk integration.",
    ),
)
LEGACY_TEMPLATE_DIGESTS = {
    "goldilocks-terra-engineer.toml": {
        "7aa50cf57f7784bb9ad1093f5862dd019147b9f871dca9bcf19c5cafd7882f8c",
    },
    "goldilocks-sol-reviewer.toml": {
        "966d4258e284da8e3e00b12d2367fd98f84f3b45f4b33d61f2401ece7ad2fa62",
        # v0.5.2 official Sol template; retain only its exact shipped bytes.
        "ab7f7df4df07b83ea003781f960b4e5340812af122e835a52a49fc594e956e6e",
    },
}
USAGE_VISIBILITY_MODES = ("on-demand", "automatic")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    mode = value.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="Inspect only; writes nothing.")
    mode.add_argument("--apply", action="store_true", help="Apply the displayed plan.")
    mode.add_argument("--check", action="store_true", help="Verify the selected host setup.")
    value.add_argument("--yes", action="store_true", help="Explicit approval for this plan.")
    value.add_argument("--json", action="store_true", help="Emit a compact JSON result.")
    value.add_argument("--host", choices=("codex", "claude", "unknown"))
    value.add_argument("--target-dir", type=Path)
    value.add_argument("--config-file", type=Path, help="Codex config.toml to inspect or register safely.")
    value.add_argument("--native-plugin-dir", type=Path)
    value.add_argument("--state-dir", type=Path)
    value.add_argument(
        "--usage-visibility",
        choices=USAGE_VISIBILITY_MODES,
        help="Visible Usage policy: on-demand (default) or automatic.",
    )
    return value


def default_host() -> str:
    explicit = os.environ.get("GOLDILOCKS_BOOTSTRAP_HOST", "").strip().lower()
    if explicit in {"codex", "claude", "unknown"}:
        return explicit
    if os.environ.get("CODEX_HOME") or os.environ.get("CODEX_THREAD_ID"):
        return "codex"
    if os.environ.get("CLAUDE_CODE") or os.environ.get("CLAUDECODE"):
        return "claude"
    for root, host in (
        (Path.home() / ".codex", "codex"),
        (Path.home() / ".claude", "claude"),
    ):
        candidate = root / "skills" / "goldilocks-bootstrap"
        try:
            if candidate.exists() and candidate.resolve() == SKILL_DIR:
                return host
        except OSError:
            continue
    for root, host in (
        (Path.home() / ".codex" / "skills", "codex"),
        (Path.home() / ".codex" / "plugins", "codex"),
        (Path.home() / ".claude" / "skills", "claude"),
        (Path.home() / ".claude" / "plugins", "claude"),
    ):
        try:
            SKILL_DIR.relative_to(root)
            return host
        except ValueError:
            continue
    return "unknown"


def default_target(host: str) -> Path | None:
    if host != "codex":
        return None
    root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    return root / "agents"


def default_state_dir() -> Path:
    configured = os.environ.get("GOLDILOCKS_BOOTSTRAP_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "goldilocks-bootstrap"
    return Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "goldilocks-bootstrap"


def usage_preference_file(state_dir: Path) -> Path:
    return state_dir / "usage-visibility.json"


def read_usage_preference(state_dir: Path) -> str | None:
    path = usage_preference_file(state_dir)
    if not path.is_file() or path.is_symlink():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        mode = value.get("mode") if isinstance(value, dict) else None
        return mode if mode in USAGE_VISIBILITY_MODES else None
    except (OSError, ValueError, TypeError):
        return None


def usage_visibility(state_dir: Path, requested: str | None = None) -> dict[str, Any]:
    override = os.environ.get("GOLDILOCKS_USAGE_VISIBILITY", "").strip().lower()
    if override in USAGE_VISIBILITY_MODES:
        mode, source = override, "environment"
    elif requested in USAGE_VISIBILITY_MODES:
        mode, source = requested, "argument"
    elif (stored := read_usage_preference(state_dir)) is not None:
        mode, source = stored, "recorded"
    else:
        mode, source = "on-demand", "default"
    return {
        "mode": mode,
        "source": source,
        "automatic": mode == "automatic",
        "choices": [
            {"id": "on-demand", "label": "On-demand (default)", "recommended": True},
            {"id": "automatic", "label": "Automatic", "recommended": False},
        ],
    }


def write_usage_preference(state_dir: Path, mode: str) -> None:
    if mode not in USAGE_VISIBILITY_MODES:
        raise ValueError(f"unknown Usage visibility mode: {mode}")
    state_dir.mkdir(parents=True, exist_ok=True)
    if state_dir.is_symlink() or not state_dir.is_dir():
        raise ValueError(f"state directory is unsafe: {state_dir}")
    destination = usage_preference_file(state_dir)
    descriptor, raw_stage = tempfile.mkstemp(prefix=".goldilocks-usage-", dir=str(state_dir))
    stage = Path(raw_stage)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump({"mode": mode}, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(stage, destination)
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass


def canonical(path: Path) -> Path:
    expanded = path.expanduser()
    return Path(os.path.abspath(expanded if expanded.is_absolute() else Path.cwd() / expanded))


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def classify(template: Path, destination: Path) -> str:
    if not path_exists(destination):
        return "missing"
    if destination.is_symlink() or not destination.is_file():
        return "unsafe"
    try:
        content = destination.read_bytes()
    except OSError:
        return "unreadable"
    if content == template.read_bytes():
        return "current"
    if digest(content) in LEGACY_TEMPLATE_DIGESTS.get(template.name, set()):
        return "legacy"
    return "conflict"


def default_config(target: Path | None) -> Path | None:
    """The native-agent directory convention is <CODEX_HOME>/agents."""
    return target.parent / "config.toml" if target is not None else None


def role_declarations(target: Path, config: Path) -> dict[str, dict[str, str]]:
    """Return the exact two official fields Bootstrap owns for each role."""
    try:
        relative_target = target.relative_to(config.parent)
        prefix = relative_target.as_posix()
    except ValueError:
        prefix = str(target)
    return {
        role: {
            "description": description,
            "config_file": f"{prefix}/{filename}",
        }
        for role, filename, description in ROLE_SPECS
    }


BARE_TOML_KEY = re.compile(r"[A-Za-z0-9_-]+")


def parse_toml_string(value: str) -> str | None:
    """Read the basic/literal strings used by Codex role declarations.

    Bootstrap deliberately does not serialize or rewrite the user's TOML.  It only
    needs to recognize the two fields it owns, and treats an unrecognizable value as
    a conflict instead of guessing.
    """
    try:
        parsed = json.loads(value) if value.startswith('"') else ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return None
    return parsed if isinstance(parsed, str) else None


def strip_toml_comment(value: str) -> str:
    """Strip a TOML comment while preserving hashes inside quoted strings."""

    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if quote == '"':
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if quote == "'":
            if character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
        elif character == "#":
            return value[:index]
    return value


def parse_toml_key_path(value: str) -> list[str]:
    """Parse the TOML bare/basic/literal key grammar used by table paths."""

    parts: list[str] = []
    index = 0
    length = len(value)
    while True:
        while index < length and value[index].isspace():
            index += 1
        if index >= length:
            if parts:
                return parts
            raise ValueError("empty TOML key")
        if value[index] == '"':
            start = index
            index += 1
            escaped = False
            while index < length:
                character = value[index]
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == '"':
                    index += 1
                    break
                index += 1
            else:
                raise ValueError("unterminated TOML basic key")
            try:
                part = json.loads(value[start:index])
            except (TypeError, ValueError) as error:
                raise ValueError("invalid TOML basic key") from error
        elif value[index] == "'":
            end = value.find("'", index + 1)
            if end < 0:
                raise ValueError("unterminated TOML literal key")
            part = value[index + 1 : end]
            index = end + 1
        else:
            match = BARE_TOML_KEY.match(value, index)
            if match is None:
                raise ValueError("invalid TOML bare key")
            part = match.group(0)
            index = match.end()
        if not isinstance(part, str):
            raise ValueError("TOML key must be a string")
        parts.append(part)
        while index < length and value[index].isspace():
            index += 1
        if index == length:
            return parts
        if value[index] != ".":
            raise ValueError("invalid TOML dotted key")
        index += 1


def split_toml_assignment(line: str) -> tuple[str, str] | None:
    quote: str | None = None
    escaped = False
    for index, character in enumerate(line):
        if quote == '"':
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if quote == "'":
            if character == quote:
                quote = None
            continue
        if character in {'"', "'"}:
            quote = character
        elif character == "=":
            return line[:index], line[index + 1 :]
    return None


def parse_table_header(line: str) -> tuple[list[str], bool]:
    value = strip_toml_comment(line).strip()
    array = value.startswith("[[")
    opening, closing = ("[[", "]]" ) if array else ("[", "]")
    if not value.startswith(opening) or not value.endswith(closing):
        raise ValueError("invalid TOML table header")
    inner = value[len(opening) : -len(closing)]
    return parse_toml_key_path(inner), array


def multiline_toml_string_opener(line: str) -> str | None:
    """Return an unclosed TOML multiline delimiter outside strings/comments."""

    quote: str | None = None
    escaped = False
    index = 0
    while index < len(line):
        character = line[index]
        if quote == '"':
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if quote == "'":
            if character == quote:
                quote = None
            index += 1
            continue
        if character == "#":
            return None
        if line.startswith('"""', index) or line.startswith("'''", index):
            delimiter = line[index : index + 3]
            closing = line.find(delimiter, index + 3)
            if closing < 0:
                return delimiter
            index = closing + 3
            continue
        if character in {'"', "'"}:
            quote = character
        index += 1
    return None


def parse_agent_tables(raw: str) -> dict[str, dict[str, str | None]]:
    """Validate the Agent-table subset Bootstrap owns.

    Unknown general TOML remains byte-preserved. Any syntax that could define or
    alias ``agents`` outside the official table form fails closed.
    """

    tables: dict[str, dict[str, str | None]] = {}
    # ``current`` is the complete current TOML context, including array-table
    # elements.  It is only used to protect Bootstrap's top-level ``agents``
    # namespace; general TOML validity belongs to tomllib/Tomli below.
    current: list[str] | None = None
    seen_agent_roles: set[str] = set()
    multiline: str | None = None
    for line_number, line in enumerate(raw.splitlines(), 1):
        if multiline is not None:
            closing = line.find(multiline)
            if closing < 0:
                continue
            line = line[closing + len(multiline) :]
            multiline = None
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        multiline = multiline_toml_string_opener(line)
        if stripped.startswith("["):
            try:
                path, array = parse_table_header(line)
            except ValueError as error:
                raise ValueError(f"invalid TOML table header on line {line_number}") from error
            if path and path[0] == "agents":
                if array:
                    raise ValueError("unsupported TOML agents array table")
                if len(path) != 2:
                    raise ValueError("unsupported TOML agents table declaration")
                role = path[1]
                if role in seen_agent_roles:
                    raise ValueError(f"duplicate TOML agents table on line {line_number}")
                seen_agent_roles.add(role)
            current = path
            if not array and len(path) == 2 and path[0] == "agents":
                role = path[1]
                tables[role] = {}
            continue
        assignment = split_toml_assignment(line)
        if assignment is None:
            if current and current[0] == "agents":
                raise ValueError(f"invalid TOML agents assignment on line {line_number}")
            continue
        lhs, rhs = assignment
        try:
            key_path = parse_toml_key_path(lhs.strip())
        except ValueError as error:
            if current and current[0] == "agents":
                raise ValueError(f"invalid TOML agents key on line {line_number}") from error
            continue
        if current is None:
            if key_path and key_path[0] == "agents":
                raise ValueError("unsupported dotted or inline TOML agents declaration")
            continue
        if len(current) < 2 or current[0] != "agents":
            continue
        role = current[1]
        if len(current) != 2 or len(key_path) != 1:
            raise ValueError("unsupported dotted TOML agents declaration")
        field = key_path[0]
        if field not in {"description", "config_file"}:
            continue
        if field in tables[role]:
            raise ValueError(f"duplicate TOML agents field on line {line_number}")
        tables[role][field] = parse_toml_string(strip_toml_comment(rhs).strip())
    return tables


def validate_agent_declaration_structure(raw: str) -> dict[str, dict[str, str | None]]:
    """Reject TOML Agent shapes that Bootstrap cannot safely own or append to."""

    return parse_agent_tables(raw)


def read_config(path: Path) -> tuple[dict[str, Any], str]:
    if not path_exists(path):
        return {}, ""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Codex config is unsafe: {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ValueError(f"Codex config is unreadable: {path}: {error}") from error
    try:
        fallback_agents = validate_agent_declaration_structure(raw)
    except ValueError as error:
        raise ValueError(f"Codex config is invalid TOML: {path}: {error}") from error
    decoder = tomllib or tomli
    try:
        decoded = decoder.loads(raw)
    except decoder.TOMLDecodeError as error:
        # Bootstrap preserves raw TOML on append, so reject partial parses
        # instead of guessing about tables or their ownership.
        raise ValueError(f"Codex config is invalid TOML: {path}: {error}") from error
    return decoded, raw


def classify_registration_data(
    target: Path, config: Path, decoded: dict[str, Any]
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Classify role registrations from one already-read config snapshot."""
    wanted = role_declarations(target, config)
    agents = decoded.get("agents", {})
    if not isinstance(agents, dict):
        return {role: "conflict" for role in wanted}, wanted
    states: dict[str, str] = {}
    for role, desired in wanted.items():
        existing = agents.get(role)
        if existing is None:
            states[role] = "missing"
        elif not isinstance(existing, dict):
            states[role] = "conflict"
        elif all(existing.get(key) == expected for key, expected in desired.items()):
            states[role] = "current"
        else:
            states[role] = "conflict"
    return states, wanted


def classify_registrations(target: Path | None, config: Path | None) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    if target is None or config is None:
        return {}, {}
    try:
        decoded, _ = read_config(config)
    except ValueError:
        wanted = role_declarations(target, config)
        return {role: "unsafe" for role in wanted}, wanted
    return classify_registration_data(target, config, decoded)


def config_snapshot(path: Path, raw: str) -> tuple[int, int, int, int] | None:
    if not path_exists(path):
        return None
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Codex config is unsafe: {path}")
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def assert_config_unchanged(
    path: Path, raw: str, snapshot: tuple[int, int, int, int] | None
) -> None:
    """Make a compare-and-replace decision without ever overwriting a new config."""
    if config_snapshot(path, raw) != snapshot:
        raise ValueError(f"Codex config changed during Bootstrap: {path}")
    if snapshot is not None:
        _, live_raw = read_config(path)
        if live_raw != raw:
            raise ValueError(f"Codex config changed during Bootstrap: {path}")


def append_registrations(config: Path, target: Path) -> list[str]:
    """Append only absent role tables; never rewrite user TOML or trust state."""
    # Re-read immediately before staging, rather than trusting an earlier --plan
    # result or the pre-template apply preflight.
    decoded, raw = read_config(config)
    states, _ = classify_registration_data(target, config, decoded)
    unsafe = {role: state for role, state in states.items() if state not in {"missing", "current"}}
    if unsafe:
        details = ", ".join(f"{role}={state}" for role, state in sorted(unsafe.items()))
        raise ValueError(f"refusing to overwrite or follow existing role declarations: {details}")
    missing = [role for role, state in states.items() if state == "missing"]
    if not missing:
        return []
    desired = role_declarations(target, config)
    snapshot = config_snapshot(config, raw)
    suffix = "" if not raw or raw.endswith("\n") else "\n"
    if raw:
        suffix += "\n"
    for role in missing:
        fields = desired[role]
        suffix += (
            f"[agents.{role}]\n"
            f"description = {json.dumps(fields['description'])}\n"
            f"config_file = {json.dumps(fields['config_file'])}\n"
        )
    config.parent.mkdir(parents=True, exist_ok=True)
    if config.parent.is_symlink() or not config.parent.is_dir():
        raise ValueError(f"Codex config directory is unsafe: {config.parent}")
    mode = config.stat().st_mode & 0o777 if path_exists(config) else 0o600
    descriptor, raw_stage = tempfile.mkstemp(prefix=".goldilocks-config-", dir=str(config.parent))
    stage = Path(raw_stage)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(raw)
            handle.write(suffix)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(stage, mode)
        assert_config_unchanged(config, raw, snapshot)
        os.replace(stage, config)
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass
    return missing


def native_plugin(path: Path | None) -> bool:
    """Accept only a real Goldilocks Codex manifest, never a loose hooks directory."""
    if path is None or path.is_symlink() or not path.is_dir():
        return False
    manifest = path / ".codex-plugin" / "plugin.json"
    if manifest.is_symlink() or not manifest.is_file():
        return False
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, TypeError, ValueError):
        return False
    return isinstance(payload, dict) and str(payload.get("name") or "").lower() == "goldilocks"


def native_components(path: Path | None) -> dict[str, bool]:
    if not native_plugin(path):
        return {"core_skill": False, "hooks": False, "usage": False, "update": False}
    assert path is not None
    required = {
        "core_skill": path / "skills" / "goldilocks" / "SKILL.md",
        "hooks": path / "hooks" / "hooks.json",
        "usage": path / "scripts" / "usage_reporter.py",
        "update": path / "scripts" / "update_checker.py",
    }
    return {
        name: candidate.is_file() and not candidate.is_symlink()
        for name, candidate in required.items()
    }


def native_pack(path: Path | None) -> bool:
    return native_plugin(path) and all(native_components(path).values())


def configured_plugin_root() -> Path | None:
    raw = os.environ.get("PLUGIN_ROOT")
    if not raw:
        return None
    candidate = canonical(Path(raw))
    return candidate if native_pack(candidate) else None


def installed_plugin_cache(path: Path | None) -> bool:
    if path is None or not native_pack(path):
        return False
    raw_home = os.environ.get("CODEX_HOME")
    if not raw_home:
        return False
    try:
        relative = canonical(path).relative_to(canonical(Path(raw_home)))
    except ValueError:
        return False
    return "plugins" in relative.parts


def ancestor_native_plugin() -> Path | None:
    """Use an ancestor only with explicit runtime/plugin-cache evidence."""
    configured = configured_plugin_root()
    for parent in (SKILL_DIR, *SKILL_DIR.parents):
        if configured is not None and canonical(parent) == configured:
            return parent
        if installed_plugin_cache(parent):
            return parent
    return None


def discover_registry_native_plugin() -> Path | None:
    """Inspect the enabled Codex registry; do not treat a bundled source as installed."""
    executable = shutil.which("codex")
    if not executable:
        return None
    try:
        result = subprocess.run(
            [executable, "plugin", "list", "--json"],
            text=True,
            capture_output=True,
            check=False,
            timeout=3,
        )
        payload = json.loads(result.stdout) if result.returncode == 0 else {}
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None
    installed = payload.get("installed", []) if isinstance(payload, dict) else []
    for item in installed if isinstance(installed, list) else []:
        if not isinstance(item, dict) or not item.get("enabled"):
            continue
        name = str(item.get("name") or "").lower()
        plugin_id = str(item.get("pluginId") or "").lower()
        source = item.get("source")
        if name != "goldilocks" and not plugin_id.startswith("goldilocks@"):
            continue
        if not isinstance(source, dict) or not isinstance(source.get("path"), str):
            continue
        candidate = canonical(Path(source["path"]))
        if native_pack(candidate):
            return candidate
    return None


def discover_native_plugin(host: str) -> Path | None:
    """Read Codex's local plugin registry; never install, trust, or download anything."""
    if host != "codex":
        return None
    configured = configured_plugin_root()
    if configured is not None:
        return configured
    bundled = ancestor_native_plugin()
    if bundled is not None:
        return bundled
    return discover_registry_native_plugin()


def native_install_evidence(path: Path | None) -> bool:
    if path is None or not native_pack(path):
        return False
    configured = configured_plugin_root()
    if configured is not None and canonical(path) == configured:
        return True
    if installed_plugin_cache(path):
        return True
    registry = discover_registry_native_plugin()
    return registry is not None and canonical(path) == canonical(registry)


def capabilities(host: str, plugin_dir: Path | None, verified: bool) -> dict[str, Any]:
    components = native_components(plugin_dir)
    if host != "codex":
        return {
            "agent_templates": "unsupported",
            "naming_contract": "unsupported",
            "hooks": "unsupported",
            "usage": "unsupported",
            "update": "unsupported",
        }
    return {
        "agent_templates": "supported",
        "naming_contract": "supported",
        "hooks": "review-required" if verified and components["hooks"] else "unsupported",
        "usage": "reused" if verified and components["usage"] else "unsupported",
        "update": "reused" if verified and components["update"] else "unsupported",
    }


def plugin_actions(host: str, verified_plugin: bool) -> list[list[str]]:
    if host != "codex" or verified_plugin:
        return []
    return [
        [
            "codex", "plugin", "marketplace", "add", "blackstone2333/goldilocks",
            "--ref", "v0.5.3-beta.9", "--json",
        ],
        ["codex", "plugin", "add", "goldilocks@goldilocks-local", "--json"],
    ]


def portable_cleanup(host: str) -> dict[str, Any]:
    if host != "codex":
        return {"status": "skipped", "reason": "Codex-only handoff"}
    root = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")).expanduser()
    present = [
        name
        for name in ("goldilocks", "goldilocks-bootstrap")
        if (root / "skills" / name).exists()
    ]
    if not present:
        return {"status": "not-needed", "reason": "no Codex portable Skill mapping detected"}
    return {
        "status": "handoff-required",
        "commands": [
            ["npx", "skills", "remove", "--global", "--agent", "codex", "--skill", name, "--yes"]
            for name in present
        ],
        "only_after": "native plugin and all four native agents pass --check; then start a new task from the plugin source",
        "executed_by_bootstrap": False,
    }


def hook_trust_handoff(host: str, plugin_dir: Path | None, verified: bool) -> dict[str, Any]:
    if host != "codex" or not verified or not native_components(plugin_dir)["hooks"]:
        return {"status": "skipped", "reason": "requires a verified Codex Goldilocks hooks pack"}
    return {
        "status": "host-review-required",
        "selection_required": True,
        "confirmation": "Ask the installing user to choose exactly one Hook trust option; Bootstrap will not execute it.",
        "choices": [
            {
                "id": "persistent_goldilocks",
                "label": "Persist Goldilocks trust",
                "recommended": True,
                "action": "In Codex's startup hook-review UI, select Trust all and continue.",
                "scope": "current Goldilocks hooks definition only",
                "persistence": "persistent until the hooks definition changes",
            },
            {
                "id": "bypass_once_all_hooks",
                "label": "Bypass all hooks once",
                "recommended": False,
                "next_launch_command": ["codex", "--dangerously-bypass-hook-trust"],
                "scope": "all enabled hooks",
                "persistence": "single invocation",
            },
            {
                "id": "skip",
                "label": "Skip Hook trust",
                "recommended": False,
                "scope": "no Hook trust change",
                "persistence": "none",
            },
        ],
        "fallback": "/hooks",
        "executed_by_bootstrap": False,
    }


def host_key(host: str) -> str:
    identity = f"{host}|{os.getuid() if hasattr(os, 'getuid') else ''}|{socket.gethostname()}|{platform.system()}"
    return digest(identity.encode("utf-8"))


def approval_file(state_dir: Path) -> Path:
    return state_dir / "approvals.json"


def read_approvals(state_dir: Path) -> dict[str, Any]:
    path = approval_file(state_dir)
    if not path.is_file() or path.is_symlink():
        return {"schema_version": 1, "approvals": {}}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and isinstance(value.get("approvals"), dict):
            return value
    except (OSError, ValueError, TypeError):
        pass
    return {"schema_version": 1, "approvals": {}}


def write_approvals(state_dir: Path, value: dict[str, Any]) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    if state_dir.is_symlink() or not state_dir.is_dir():
        raise ValueError(f"state directory is unsafe: {state_dir}")
    destination = approval_file(state_dir)
    descriptor, raw_stage = tempfile.mkstemp(prefix=".goldilocks-approval-", dir=str(state_dir))
    stage = Path(raw_stage)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, sort_keys=True, separators=(",", ":"))
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(stage, destination)
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass


def install_missing(template: Path, destination: Path) -> None:
    descriptor, raw_stage = tempfile.mkstemp(prefix=".goldilocks-agent-", dir=str(destination.parent))
    stage = Path(raw_stage)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(template.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(stage, 0o644)
        os.link(stage, destination)
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass


def replace_legacy(template: Path, destination: Path) -> None:
    descriptor, raw_stage = tempfile.mkstemp(prefix=".goldilocks-agent-", dir=str(destination.parent))
    stage = Path(raw_stage)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(template.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(stage, 0o644)
        if classify(template, destination) != "legacy":
            raise ValueError(f"agent destination changed during migration: {destination}")
        os.replace(stage, destination)
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass


def plan(
    host: str,
    target: Path | None,
    config: Path | None,
    plugin_dir: Path | None,
    state_dir: Path,
    requested_usage_visibility: str | None = None,
) -> dict[str, Any]:
    templates = [TEMPLATE_DIR / name for name in TEMPLATE_FILES]
    if any(template.is_symlink() or not template.is_file() for template in templates):
        raise ValueError("shipped Bootstrap templates are missing or unsafe")
    verified_plugin = host == "codex" and native_install_evidence(plugin_dir)
    caps = capabilities(host, plugin_dir, verified_plugin)
    states = (
        {template.name: classify(template, target / template.name) for template in templates}
        if target is not None and caps["agent_templates"] == "supported"
        else {}
    )
    registrations, registration_definitions = (
        classify_registrations(target, config)
        if caps["agent_templates"] == "supported"
        else ({}, {})
    )
    hashes = {template.name: digest(template.read_bytes()) for template in templates}
    actions = plugin_actions(host, verified_plugin)
    agents_ready = bool(states) and all(state == "current" for state in states.values())
    registrations_ready = bool(registrations) and all(
        state == "current" for state in registrations.values()
    )
    experience = "full" if verified_plugin and agents_ready and registrations_ready else (
        "partial" if host == "codex" else "portable"
    )
    cleanup = portable_cleanup(host)
    hook_handoff = hook_trust_handoff(host, plugin_dir, verified_plugin)
    visibility = usage_visibility(state_dir, requested_usage_visibility)
    preferred_experience = "native_plugin" if host == "codex" else "portable_skills"
    fingerprint_input = {
        "host": host,
        "target": str(target) if target is not None else None,
        "config_file": str(config) if config is not None else None,
        "native_plugin_dir": str(plugin_dir) if plugin_dir is not None else None,
        "capabilities": caps,
        "template_hashes": hashes,
        "role_definitions": registration_definitions,
        "preferred_experience": preferred_experience,
        "portable_skills_role": "fallback" if host == "codex" else "preferred",
        "plugin_actions": actions,
        "portable_cleanup": cleanup,
        "hook_trust_handoff": hook_handoff,
        "usage_visibility": {"mode": visibility["mode"]},
    }
    fingerprint = digest(json.dumps(fingerprint_input, sort_keys=True).encode("utf-8"))
    approvals = read_approvals(state_dir)
    approved = approvals["approvals"].get(host_key(host), {}).get("fingerprint") == fingerprint
    return {
        "status": "planned",
        "host": host,
        "target": str(target) if target is not None else None,
        "config_file": str(config) if config is not None else None,
        "native_plugin_dir": str(plugin_dir) if plugin_dir is not None else None,
        "capabilities": caps,
        "experience": experience,
        "preferred_experience": preferred_experience,
        "portable_skills_role": "fallback" if host == "codex" else "preferred",
        "native_plugin": "detected" if native_plugin(plugin_dir) else "absent",
        "native_components": native_components(plugin_dir),
        "plugin_repair": (
            "handoff-required" if host == "codex" and native_plugin(plugin_dir) and not verified_plugin else "not-needed"
        ),
        "hooks_review": "required" if caps["hooks"] == "review-required" else caps["hooks"],
        "agents": states,
        "registrations": registrations,
        "role_definitions": registration_definitions,
        "template_hashes": hashes,
        "plugin_actions": actions,
        "portable_cleanup": cleanup,
        "hook_trust_handoff": hook_handoff,
        "usage_visibility": visibility,
        "fingerprint": fingerprint,
        "approval_required": caps["agent_templates"] == "supported" and not approved,
    }


def install_plugin(actions: list[list[str]]) -> tuple[bool, list[dict[str, Any]], str | None]:
    executable = shutil.which("codex")
    if not executable:
        return False, [], "Codex CLI is unavailable; portable agents remain installed."
    results: list[dict[str, Any]] = []
    for action in actions:
        command = [executable, *action[1:]]
        try:
            result = subprocess.run(
                command, text=True, capture_output=True, check=False, timeout=60
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return False, results, f"plugin command failed to start: {error}"
        results.append({"command": action, "returncode": result.returncode})
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()[:500]
            return False, results, f"plugin command failed ({' '.join(action)}): {detail or 'no diagnostic'}"
    installed = discover_registry_native_plugin()
    if installed is None:
        return False, results, "plugin commands returned successfully but no enabled, valid Goldilocks source was verified."
    return True, results, None


def record_approval(value: dict[str, Any], state_dir: Path) -> None:
    approvals = read_approvals(state_dir)
    approvals["approvals"][host_key(str(value["host"]))] = {
        "fingerprint": value["fingerprint"],
        "template_hashes": value["template_hashes"],
    }
    write_approvals(state_dir, approvals)


def completed_plan(
    value: dict[str, Any], target: Path, config: Path, state_dir: Path,
    requested_usage_visibility: str | None = None,
) -> dict[str, Any]:
    raw_plugin = value.get("native_plugin_dir")
    plugin_dir = Path(str(raw_plugin)) if raw_plugin else None
    return plan(
        str(value["host"]), target, config, plugin_dir, state_dir,
        requested_usage_visibility,
    )


def with_apply_changes(
    value: dict[str, Any], *, installed: list[str], migrated: list[str], registered: list[str]
) -> dict[str, Any]:
    return {
        **value,
        "status": "installed" if installed or migrated or registered else "current",
        "installed": installed,
        "migrated": migrated,
        "registered": registered,
    }


def apply(value: dict[str, Any], state_dir: Path) -> dict[str, Any]:
    if value["capabilities"]["agent_templates"] != "supported":
        return {**value, "status": "skipped", "installed": [], "migrated": []}
    target = Path(str(value["target"]))
    config = Path(str(value["config_file"]))
    if target == Path(target.anchor):
        raise ValueError("refusing to use the filesystem root as the agent target")
    if path_exists(target) and (target.is_symlink() or not target.is_dir()):
        raise ValueError(f"agent target is not a real directory: {target}")
    # The plan can also be stale with respect to template files.  Verify all
    # no-write preconditions before registering anything.
    live_agents = {
        name: classify(TEMPLATE_DIR / name, target / name)
        for name in TEMPLATE_FILES
    }
    unsafe = {name: state for name, state in live_agents.items() if state not in {"missing", "legacy", "current"}}
    if unsafe:
        details = ", ".join(f"{name}={state}" for name, state in sorted(unsafe.items()))
        raise ValueError(f"refusing to overwrite or follow existing agent files: {details}")
    # The plan can be stale.  Refuse a newly introduced role conflict before
    # creating or replacing even one template file.
    live_registrations, _ = classify_registrations(target, config)
    registration_unsafe = {
        name: state for name, state in live_registrations.items()
        if state not in {"missing", "current"}
    }
    if registration_unsafe:
        details = ", ".join(f"{name}={state}" for name, state in sorted(registration_unsafe.items()))
        raise ValueError(f"refusing to overwrite or follow existing role declarations: {details}")
    # Register before copying a template.  If a concurrent edit makes the
    # registration unsafe, no template has been created yet.
    registered = append_registrations(config, target)
    target.mkdir(parents=True, exist_ok=True)
    installed: list[str] = []
    migrated: list[str] = []
    for name in TEMPLATE_FILES:
        template = TEMPLATE_DIR / name
        destination = target / name
        state = classify(template, destination)
        if state == "current":
            continue
        if state == "missing":
            install_missing(template, destination)
            installed.append(name)
            continue
        if state == "legacy":
            replace_legacy(template, destination)
            migrated.append(name)
            continue
        raise ValueError(f"agent destination changed during Bootstrap: {destination}")
    if any(classify(TEMPLATE_DIR / name, target / name) != "current" for name in TEMPLATE_FILES):
        raise ValueError("Bootstrap post-install exactness check failed")
    current_registrations, _ = classify_registrations(target, config)
    if any(state != "current" for state in current_registrations.values()):
        raise ValueError("Bootstrap post-registration exactness check failed")
    selected_mode = str(value["usage_visibility"]["mode"])
    completed = completed_plan(value, target, config, state_dir, selected_mode)
    actions = value["plugin_actions"]
    if not actions:
        if value["usage_visibility"]["source"] != "environment":
            write_usage_preference(state_dir, selected_mode)
        record_approval(completed, state_dir)
        final = completed_plan(completed, target, config, state_dir)
        return with_apply_changes(final, installed=installed, migrated=migrated, registered=registered)
    success, action_results, error = install_plugin(actions)
    if not success:
        final = completed_plan(value, target, config, state_dir)
        record_approval(final, state_dir)
        final = completed_plan(final, target, config, state_dir)
        return {
            **with_apply_changes(final, installed=installed, migrated=migrated, registered=registered),
            "status": "partial",
            "plugin_action_results": action_results,
            "plugin_error": error,
        }
    full_plugin = discover_registry_native_plugin()
    completed = plan(str(value["host"]), target, config, full_plugin, state_dir, selected_mode)
    if value["usage_visibility"]["source"] != "environment":
        write_usage_preference(state_dir, selected_mode)
    record_approval(completed, state_dir)
    final = plan(str(value["host"]), target, config, full_plugin, state_dir)
    return {
        **with_apply_changes(final, installed=installed, migrated=migrated, registered=registered),
        "plugin_action_results": action_results,
    }


def emit(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, sort_keys=True))
    else:
        print(f"BOOTSTRAP {value['status'].upper()}: {value['host']}")


def main() -> None:
    args = parser().parse_args()
    host = args.host or default_host()
    target = canonical(args.target_dir) if args.target_dir else default_target(host)
    config = canonical(args.config_file) if args.config_file else default_config(target)
    state_dir = canonical(args.state_dir or default_state_dir())
    plugin_dir = (
        canonical(args.native_plugin_dir)
        if args.native_plugin_dir
        else discover_native_plugin(host)
    )
    value = plan(host, target, config, plugin_dir, state_dir, args.usage_visibility)
    if args.plan:
        emit(value, args.json)
        return
    if args.check:
        if value["capabilities"]["agent_templates"] != "supported":
            emit({**value, "status": "skipped"}, args.json)
            return
        incomplete = [name for name, state in value["agents"].items() if state != "current"]
        if incomplete:
            raise ValueError("Bootstrap agents are not installed exactly: " + ", ".join(incomplete))
        registrations = [name for name, state in value["registrations"].items() if state != "current"]
        if registrations:
            raise ValueError("Bootstrap roles are not registered exactly: " + ", ".join(registrations))
        if value["approval_required"]:
            raise ValueError("Bootstrap plan is not globally approved for this target")
        if value["experience"] != "full":
            raise ValueError("Bootstrap remains portable/partial: an enabled, valid native Goldilocks plugin is required for full experience")
        active_visibility = usage_visibility(state_dir)
        if args.usage_visibility:
            if active_visibility["mode"] != args.usage_visibility:
                raise ValueError(
                    "Bootstrap Usage visibility is not active as requested: "
                    f"requested {args.usage_visibility}, active {active_visibility['mode']} "
                    f"({active_visibility['source']})"
                )
        emit(
            {**value, "usage_visibility": active_visibility, "status": "current"},
            args.json,
        )
        return
    if value["approval_required"] and not args.yes:
        raise ValueError("Bootstrap requires explicit confirmation: run --plan, then --apply --yes")
    emit(apply(value, state_dir), args.json)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError) as error:
        raise SystemExit(f"Goldilocks Bootstrap failed: {error}")
