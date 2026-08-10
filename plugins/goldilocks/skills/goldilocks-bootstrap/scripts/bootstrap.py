#!/usr/bin/env python3

"""Explicit bootstrap for portable Goldilocks installation and native-host upgrades."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Any


SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "assets" / "bootstrap-agents"
TEMPLATE_FILES = (
    "goldilocks-spark-worker.toml",
    "goldilocks-luna-economy.toml",
    "goldilocks-terra-engineer.toml",
    "goldilocks-sol-reviewer.toml",
)
LEGACY_TEMPLATE_DIGESTS = {
    "goldilocks-terra-engineer.toml": {
        "7aa50cf57f7784bb9ad1093f5862dd019147b9f871dca9bcf19c5cafd7882f8c",
    },
    "goldilocks-sol-reviewer.toml": {
        "966d4258e284da8e3e00b12d2367fd98f84f3b45f4b33d61f2401ece7ad2fa62",
    },
}


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
    value.add_argument("--native-plugin-dir", type=Path)
    value.add_argument("--state-dir", type=Path)
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
    return Path.home() / ".local" / "state" / "goldilocks-bootstrap"


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
            "--ref", "v0.5.0", "--json",
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


def plan(host: str, target: Path | None, plugin_dir: Path | None, state_dir: Path) -> dict[str, Any]:
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
    hashes = {template.name: digest(template.read_bytes()) for template in templates}
    actions = plugin_actions(host, verified_plugin)
    experience = "full" if verified_plugin else (
        "partial" if host == "codex" else "portable"
    )
    cleanup = portable_cleanup(host)
    hook_handoff = hook_trust_handoff(host, plugin_dir, verified_plugin)
    preferred_experience = "native_plugin" if host == "codex" else "portable_skills"
    fingerprint_input = {
        "host": host,
        "target": str(target) if target is not None else None,
        "capabilities": caps,
        "template_hashes": hashes,
        "experience": experience,
        "preferred_experience": preferred_experience,
        "portable_skills_role": "fallback" if host == "codex" else "preferred",
        "plugin_actions": actions,
        "portable_cleanup": cleanup,
        "hook_trust_handoff": hook_handoff,
    }
    fingerprint = digest(json.dumps(fingerprint_input, sort_keys=True).encode("utf-8"))
    approvals = read_approvals(state_dir)
    approved = approvals["approvals"].get(host_key(host), {}).get("fingerprint") == fingerprint
    return {
        "status": "planned",
        "host": host,
        "target": str(target) if target is not None else None,
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
        "template_hashes": hashes,
        "plugin_actions": actions,
        "portable_cleanup": cleanup,
        "hook_trust_handoff": hook_handoff,
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


def apply(value: dict[str, Any], state_dir: Path) -> dict[str, Any]:
    if value["capabilities"]["agent_templates"] != "supported":
        return {**value, "status": "skipped", "installed": [], "migrated": []}
    target = Path(str(value["target"]))
    if target == Path(target.anchor):
        raise ValueError("refusing to use the filesystem root as the agent target")
    if path_exists(target) and (target.is_symlink() or not target.is_dir()):
        raise ValueError(f"agent target is not a real directory: {target}")
    unsafe = {name: state for name, state in value["agents"].items() if state not in {"missing", "legacy", "current"}}
    if unsafe:
        details = ", ".join(f"{name}={state}" for name, state in sorted(unsafe.items()))
        raise ValueError(f"refusing to overwrite or follow existing agent files: {details}")
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
    record_approval(value, state_dir)
    actions = value["plugin_actions"]
    if not actions:
        return {
            **value,
            "status": "installed" if installed or migrated else "current",
            "installed": installed,
            "migrated": migrated,
        }
    success, action_results, error = install_plugin(actions)
    if not success:
        return {
            **value,
            "status": "partial",
            "installed": installed,
            "migrated": migrated,
            "plugin_action_results": action_results,
            "plugin_error": error,
        }
    full_plugin = discover_registry_native_plugin()
    completed = plan(str(value["host"]), target, full_plugin, state_dir)
    record_approval(completed, state_dir)
    return {
        **completed,
        "status": "installed" if installed or migrated else "current",
        "installed": installed,
        "migrated": migrated,
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
    state_dir = canonical(args.state_dir or default_state_dir())
    plugin_dir = (
        canonical(args.native_plugin_dir)
        if args.native_plugin_dir
        else discover_native_plugin(host)
    )
    value = plan(host, target, plugin_dir, state_dir)
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
        if value["approval_required"]:
            raise ValueError("Bootstrap plan is not globally approved for this target")
        if value["experience"] != "full":
            raise ValueError("Bootstrap remains portable/partial: an enabled, valid native Goldilocks plugin is required for full experience")
        emit({**value, "status": "current"}, args.json)
        return
    if value["approval_required"] and not args.yes:
        raise ValueError("Bootstrap requires explicit confirmation: run --plan, then --apply --yes")
    emit(apply(value, state_dir), args.json)


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError) as error:
        raise SystemExit(f"Goldilocks Bootstrap failed: {error}")
