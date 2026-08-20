#!/usr/bin/env python3

"""Install Goldilocks native companion-agent templates without overwriting user files."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "agents"
TEMPLATE_FILES = (
    "goldilocks-spark-worker.toml",
    "goldilocks-luna-economy.toml",
    "goldilocks-terra-engineer.toml",
    "goldilocks-sol-reviewer.toml",
)

# Only these byte-exact, previously shipped templates may be replaced during an
# upgrade.  A user edit, even one with the same semantic TOML meaning, is a conflict.
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


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--target-dir", type=Path)
    value.add_argument("--check", action="store_true", help="Verify only; change nothing.")
    value.add_argument("--json", action="store_true", help="Emit one compact JSON result.")
    return value


def default_target() -> Path:
    configured = os.environ.get("CODEX_HOME")
    root = Path(configured).expanduser() if configured else Path.home() / ".codex"
    return root / "agents"


def path_exists(path: Path) -> bool:
    return path.exists() or path.is_symlink()


def classify(template: Path, destination: Path) -> str:
    if not path_exists(destination):
        return "missing"
    if destination.is_symlink() or not destination.is_file():
        return "unsafe"
    try:
        content = destination.read_bytes()
        if content == template.read_bytes():
            return "current"
        digest = hashlib.sha256(content).hexdigest()
        if digest in LEGACY_TEMPLATE_DIGESTS.get(template.name, set()):
            return "legacy"
        return "conflict"
    except OSError:
        return "unreadable"


def install_missing(template: Path, destination: Path) -> None:
    descriptor, raw_stage = tempfile.mkstemp(
        prefix=".goldilocks-agent-", dir=str(destination.parent)
    )
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
    """Atomically replace a preflighted byte-exact legacy template."""
    descriptor, raw_stage = tempfile.mkstemp(
        prefix=".goldilocks-agent-", dir=str(destination.parent)
    )
    stage = Path(raw_stage)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(template.read_bytes())
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(stage, 0o644)
        # Re-check immediately before replacement so a user edit observed during
        # installation remains protected rather than being silently overwritten.
        if classify(template, destination) != "legacy":
            raise ValueError(f"agent destination changed during migration: {destination}")
        os.replace(stage, destination)
    finally:
        try:
            stage.unlink()
        except FileNotFoundError:
            pass


def run(target: Path, check_only: bool) -> dict[str, object]:
    expanded = target.expanduser()
    target = Path(os.path.abspath(expanded if expanded.is_absolute() else Path.cwd() / expanded))
    if target == Path(target.anchor):
        raise ValueError("refusing to use the filesystem root as the agent target")
    if path_exists(target) and (target.is_symlink() or not target.is_dir()):
        raise ValueError(f"agent target is not a real directory: {target}")

    templates = [TEMPLATE_DIR / name for name in TEMPLATE_FILES]
    for template in templates:
        if template.is_symlink() or not template.is_file():
            raise ValueError(f"missing or unsafe shipped template: {template}")

    states = {
        template.name: classify(template, target / template.name) for template in templates
    }
    invalid = {
        name: state
        for name, state in states.items()
        if state not in {"current", "missing", "legacy"}
    }
    if invalid:
        details = ", ".join(f"{name}={state}" for name, state in sorted(invalid.items()))
        raise ValueError(f"refusing to overwrite or follow existing agent files: {details}")

    if check_only:
        outdated = [name for name, state in states.items() if state != "current"]
        if outdated:
            raise ValueError("companion agents are not installed exactly: " + ", ".join(outdated))
        return {"status": "current", "target": str(target), "agents": states}

    target.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or not target.is_dir():
        raise ValueError(f"agent target changed during preflight: {target}")

    installed: list[str] = []
    migrated: list[str] = []
    for template in templates:
        destination = target / template.name
        current_state = classify(template, destination)
        if current_state == "current":
            continue
        if current_state == "legacy":
            replace_legacy(template, destination)
            migrated.append(template.name)
            continue
        if current_state != "missing":
            raise ValueError(f"agent destination changed during preflight: {destination}")
        try:
            install_missing(template, destination)
        except FileExistsError as error:
            raise ValueError(f"agent destination appeared during install: {destination}") from error
        installed.append(template.name)

    final = {
        template.name: classify(template, target / template.name) for template in templates
    }
    if any(state != "current" for state in final.values()):
        raise ValueError("post-install exactness check failed")
    return {
        "status": "installed" if installed or migrated else "current",
        "target": str(target),
        "installed": installed,
        "migrated": migrated,
        "agents": final,
    }


def main() -> None:
    args = parser().parse_args()
    result = run(args.target_dir or default_target(), args.check)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(f"AGENT {result['status'].upper()}: {result['target']}")
        for name, state in result["agents"].items():
            print(f"- {name}: {state}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, TypeError, ValueError) as error:
        raise SystemExit(f"Goldilocks companion-agent install failed: {error}")
