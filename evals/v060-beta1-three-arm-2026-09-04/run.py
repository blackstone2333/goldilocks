#!/usr/bin/env python3
"""Offline three-arm comparison harness for the 0.6.0-beta.1 smoke test.

This module deliberately does not start Codex, contact a provider, install a
plugin, or read host credentials.  It consumes a small, normalized cell file
produced by an separately-authorized runner and keeps execution failures out
of the product-quality denominator.  ``--self-test`` only exercises local
fixtures and temporary JSON/JSONL data.
"""

from __future__ import annotations

import argparse
import ast
import collections
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
MANIFEST = HERE / "manifest.json"
ARMS: Tuple[str, ...] = ("v053_beta9", "v060_beta1", "direct")
EXPECTED_VERSIONS = {
    "v053_beta9": "0.5.3-beta.9",
    "v060_beta1": "0.6.0-beta.1",
    "direct": None,
}
TOKEN_KEYS: Tuple[str, ...] = (
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
)
METRIC_KEYS: Tuple[str, ...] = (
    "wall_time_ms",
    "tool_calls",
    "process_steps",
    "verification_calls",
    "verification_recovery_calls",
    "duplicate_verification_calls",
    "input_tokens",
    "cached_input_tokens",
    "cache_write_input_tokens",
    "output_tokens",
    "raw_tokens",
    "normalized_cost_usd",
    "cache_neutral_cost_usd",
)
NORMALIZED_RATES = {
    "gpt-5.6-sol": {"input": 5.0, "cached": 0.5, "cache_write": 6.25, "output": 30.0},
    "gpt-5.6-terra": {"input": 2.0, "cached": 0.2, "cache_write": 2.5, "output": 12.0},
    "gpt-5.6-luna": {"input": 0.2, "cached": 0.02, "cache_write": 0.25, "output": 1.2},
    # Explicit comparison proxy only; it is never presented as Spark official pricing.
    "gpt-5.3-codex-spark": {"input": 0.2, "cached": 0.02, "cache_write": 0.25, "output": 1.2},
}
PRICING_PROVENANCE = "goldilocks-normalized-rates-2026-09-04"
CACHE_RATE_COMPARABLE_BASIS_POINTS = 500
SINGLE_SAMPLE_EQUIVALENCE_PERCENT = 3.0
FAILURE_CLASSES = ("infrastructure_invalid", "protocol_invalid", "quality_failure")
INFRASTRUCTURE_REASONS = (
    "auth",
    "quota",
    "provider",
    "transport",
    "timeout",
    "host",
    "root_identity",
    "evidence_input",
)
CELL_STATUSES = (
    "infrastructure_failure",
    "protocol_failure",
    "evidence_gap",
    "quality_failure",
    "measurement_partial",
    "eligible",
)


class CellFormatError(ValueError):
    """A malformed cell is an evidence/infrastructure problem, not quality."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_tree(path: Path) -> str:
    digest = hashlib.sha256()
    for child in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
        if ".git" in child.parts or "__pycache__" in child.parts or child.suffix == ".pyc":
            continue
        digest.update(child.relative_to(path).as_posix().encode("utf-8") + b"\0")
        digest.update(child.read_bytes() + b"\0")
    return digest.hexdigest()


def expected_protocol_hashes() -> Dict[str, str]:
    return {
        "prompt_sha256": sha256_file(HERE / "task" / "TASK.md"),
        "fixture_sha256": sha256_tree(HERE / "task" / "template"),
        "grader_sha256": sha256_tree(HERE / "task" / "hidden"),
    }


def _as_int(value: Any, field: str, *, optional: bool = True) -> Optional[int]:
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise CellFormatError(f"{field} must be a JSON integer")
    number = value
    if number < 0:
        raise CellFormatError(f"{field} must be non-negative")
    return number


def _bool_or_none(value: Any, field: str) -> Optional[bool]:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise CellFormatError(f"{field} must be a boolean")


def _first_dict(*values: Any) -> Dict[str, Any]:
    for value in values:
        if isinstance(value, dict):
            return value
    return {}


def _extract_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return " ".join(_extract_text(item) for item in value)
    if isinstance(value, dict):
        return " ".join(_extract_text(item) for item in value.values())
    return str(value)


def _normalize_verification_tail(value: str) -> str:
    """Ignore presentation-only flags while retaining the tested target."""

    value = re.sub(
        r"(?<!\S)--?(?:q|quiet|v|verbose|failfast|buffer|catch)(?=\s|$)",
        "",
        value,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", value.strip().rstrip("'\"\\"))


def _python_probe_fingerprint(source: str) -> Optional[str]:
    """Fingerprint one assertion probe independent of shell/interpreter spelling."""

    if not re.search(r"(?m)^\s*assert\b", source):
        return None
    try:
        normalized = ast.dump(ast.parse(source), annotate_fields=True, include_attributes=False)
    except SyntaxError:
        normalized = re.sub(r"\s+", " ", source).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def _verification_semantic_keys(name: str, arguments: str) -> List[str]:
    """Return each verification action embedded in one completed tool call.

    Keys intentionally describe the operation rather than the complete shell
    string.  This recognizes interpreter fallback and repeated compound checks;
    the caller separately distinguishes failed runner recovery and adds a
    code-generation prefix so a rerun after a product edit is not redundant.
    """

    text = f"{name} {arguments}"
    keys: List[str] = []
    python_module = re.compile(
        r"\bpython(?:\d+(?:\.\d+)*)?\s+-m\s+"
        r"(?P<module>pytest|unittest|compileall)\b(?P<tail>[^\n;&|]*)",
        re.IGNORECASE,
    )
    for match in python_module.finditer(text):
        module = match.group("module").lower()
        tail = _normalize_verification_tail(match.group("tail"))
        keys.append(f"python-module:{module}:{tail}")

    for match in re.finditer(
        r"\bnpm\s+(?:run\s+)?test\b(?P<tail>[^\n;&|]*)",
        text,
        re.IGNORECASE,
    ):
        keys.append(f"npm-test:{_normalize_verification_tail(match.group('tail'))}")
    for tool in ("cargo", "go"):
        for match in re.finditer(
            rf"\b{tool}\s+test\b(?P<tail>[^\n;&|]*)",
            text,
            re.IGNORECASE,
        ):
            keys.append(f"{tool}-test:{_normalize_verification_tail(match.group('tail'))}")

    for match in re.finditer(r"\bgit\s+diff\b(?P<tail>[^\n;&|]*)", text, re.IGNORECASE):
        tail = match.group("tail")
        keys.append("git:diff-check" if re.search(r"(?:^|\s)--check(?:\s|$)", tail) else "git:diff")
    keys.extend("git:status" for _ in re.finditer(r"\bgit\s+status\b", text, re.IGNORECASE))

    heredoc = re.compile(
        r"\bpython(?:\d+(?:\.\d+)*)?\s+-\s*<<\s*['\"]?"
        r"(?P<marker>[A-Za-z_][A-Za-z0-9_]*)['\"]?[^\n]*\n"
        r"(?P<body>.*?)\n(?P=marker)\b",
        re.IGNORECASE | re.DOTALL,
    )
    for match in heredoc.finditer(text):
        fingerprint = _python_probe_fingerprint(match.group("body"))
        if fingerprint is not None:
            keys.append(f"python-assert-probe:{fingerprint}")
    return keys


def _is_verification_call(name: str, arguments: str) -> bool:
    return bool(_verification_semantic_keys(name, arguments))


def _event_records(path: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as error:
            raise CellFormatError(f"{path.name}:{line_number} is not JSON") from error
        if not isinstance(item, dict):
            raise CellFormatError(f"{path.name}:{line_number} is not an object")
        records.append(item)
    return records


def parse_events(path: Path, *, arm: Optional[str] = None) -> Dict[str, Any]:
    """Convert a Codex-like JSONL trace into the normalized cell schema.

    The adapter accepts the small event vocabulary already used by the project
    (`session_meta`, `turn_context`, `event_msg`, and `response_item`) plus
    explicit `cell`, `quality`, and `run` records.  Unknown records are ignored
    so a provider adding an informational event cannot become a product fail.
    """

    session: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    usage: Dict[str, Any] = {}
    usage_records: Dict[str, List[Dict[str, Any]]] = collections.defaultdict(list)
    calls: List[Dict[str, Any]] = []
    call_keys = set()
    completed_items: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []
    quality_passed: Optional[bool] = None
    quality_checks: List[Dict[str, Any]] = []
    completed: Optional[bool] = None
    returncode: Optional[int] = None
    attempts: Optional[int] = None
    host_retries: Optional[int] = None
    wall_time_ms: Optional[int] = None
    process_steps: Optional[int] = None
    explicit_arm = arm
    explicit_version: Optional[str] = None
    route: Dict[str, Any] = {}
    measurement: Dict[str, Any] = {}
    protocol: Dict[str, Any] = {}
    failure_class: Optional[str] = None
    infrastructure_reason: Optional[str] = None
    cell_id: Optional[str] = None
    replacement_of: Optional[str] = None
    retry_of: Optional[str] = None
    replacement_index: Optional[int] = None
    replacement_authorized: Optional[bool] = None
    replacement_reason: Optional[str] = None
    thread_ids: set[str] = set()
    session_ids: set[str] = set()
    parser_violations: List[str] = []
    parser_contamination: List[str] = []

    def record_conflict(message: str) -> None:
        if message not in parser_violations:
            parser_violations.append(message)
        if message not in parser_contamination:
            parser_contamination.append(message)

    def merge_without_overwrite(target: Dict[str, Any], incoming: Any, label: str) -> None:
        """Merge evidence while retaining the first value and any contradiction."""

        if not isinstance(incoming, dict):
            return
        for key, value in incoming.items():
            if key not in target:
                target[key] = value
                continue
            if target[key] == value:
                continue
            if key in {"contamination", "violations"} and isinstance(target[key], list) and isinstance(value, list):
                target[key] = list(dict.fromkeys([*target[key], *value]))
                continue
            record_conflict(f"conflicting {label}.{key} evidence")

    def usage_snapshot(value: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(value, dict):
            return None
        keys = (*TOKEN_KEYS, "reasoning_output_tokens")
        snapshot = {key: value.get(key) for key in keys if value.get(key) is not None}
        return snapshot or None

    def record_usage(kind: str, value: Any) -> None:
        snapshot = usage_snapshot(value)
        if snapshot is not None:
            usage_records[kind].append(snapshot)

    def completed_item_call(response: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        response_type = str(response.get("type") or "")
        if response_type not in {"command_execution", "file_change", "collab_tool_call"}:
            return None
        if response_type == "command_execution":
            name = "command_execution"
            arguments = _extract_text(response.get("command") or "")
        elif response_type == "file_change":
            name = "file_change"
            arguments = _extract_text(
                response.get("changes")
                or response.get("patch")
                or response.get("path")
                or ""
            )
        else:
            name = str(
                response.get("name")
                or response.get("tool_name")
                or response.get("tool")
                or "collab_tool_call"
            )
            arguments = _extract_text(
                response.get("arguments")
                or response.get("input")
                or response.get("prompt")
                or ""
            )
        # Preserve command newlines: compound verification and heredoc probes
        # cannot be segmented correctly after whitespace flattening.
        exit_code = response.get("exit_code") if response_type == "command_execution" else None
        if isinstance(exit_code, bool) or not isinstance(exit_code, int):
            exit_code = None
        return {"name": name, "arguments": arguments.strip(), "exit_code": exit_code}

    for item in _event_records(path):
        item_type = str(item.get("type") or item.get("event") or "")
        payload = item.get("payload")
        if not isinstance(payload, dict):
            payload = item

        if item_type in {"cell", "run", "metadata"}:
            explicit_arm = payload.get("arm") or explicit_arm
            explicit_version = payload.get("version") or explicit_version
            if payload.get("returncode") is not None:
                returncode = payload.get("returncode")
            attempts = payload.get("attempts", attempts)
            host_retries = payload.get("host_retries", host_retries)
            wall_time_ms = payload.get("wall_time_ms", wall_time_ms)
            process_steps = payload.get("process_steps", process_steps)
            merge_without_overwrite(route, payload.get("route"), "route")
            merge_without_overwrite(measurement, payload.get("measurement"), "measurement")
            merge_without_overwrite(protocol, payload.get("protocol"), "protocol")
            failure_class = payload.get("failure_class") or failure_class
            infrastructure_reason = payload.get("infrastructure_reason") or infrastructure_reason
            cell_id = payload.get("cell_id") or cell_id
            replacement_of = payload.get("replacement_of") or replacement_of
            retry_of = payload.get("retry_of") or retry_of
            replacement_index = payload.get("replacement_index", replacement_index)
            replacement_authorized = payload.get("replacement_authorized", replacement_authorized)
            replacement_reason = payload.get("replacement_reason") or replacement_reason

        if item_type == "thread.started":
            thread_id = payload.get("thread_id") or payload.get("id")
            if thread_id is None:
                record_conflict("thread.started is missing thread_id")
            else:
                thread_ids.add(str(thread_id))
        elif item_type == "session_meta":
            merge_without_overwrite(session, payload, "session_meta")
            session_id = payload.get("session_id") or payload.get("thread_id") or payload.get("id")
            if session_id is not None:
                session_ids.add(str(session_id))
            explicit_arm = payload.get("arm") or explicit_arm
            explicit_version = payload.get("version") or explicit_version
        elif item_type == "turn_context":
            merge_without_overwrite(context, payload, "turn_context")
        elif item_type in {"quality", "quality_gate"}:
            if payload.get("passed") is not None:
                quality_passed = _bool_or_none(payload.get("passed"), "quality.passed")
            checks = payload.get("checks")
            if isinstance(checks, list):
                quality_checks.extend(item for item in checks if isinstance(item, dict))
        elif item_type in {"run.completed", "turn.completed", "task_complete", "task_completed"}:
            completed = True
            if payload.get("returncode") is not None:
                returncode = payload.get("returncode")
            if item_type == "turn.completed":
                record_usage("turn.completed", item.get("usage") or payload.get("usage"))
        elif item_type in {"run.failed", "turn.failed", "task_failed", "error"}:
            completed = False
            message = payload.get("message") or payload.get("error") or payload.get("reason")
            if message:
                errors.append(_extract_text(message))
        elif item_type == "event_msg":
            event_kind = str(payload.get("type") or "")
            if event_kind in {"task_complete", "turn_completed", "run_completed"}:
                completed = True
            elif event_kind in {"task_failed", "turn_failed", "error"}:
                completed = False
                message = payload.get("message") or payload.get("error")
                if message:
                    errors.append(_extract_text(message))
            info = payload.get("info")
            if isinstance(info, dict) and isinstance(info.get("total_token_usage"), dict):
                record_usage("event_msg", info["total_token_usage"])
            if isinstance(payload.get("total_token_usage"), dict):
                record_usage("event_msg", payload["total_token_usage"])
        elif item_type in {"usage", "token_usage"}:
            source = payload.get("usage") if isinstance(payload.get("usage"), dict) else payload
            record_usage("explicit", source)
        elif item_type == "item.completed":
            response = item.get("item")
            if not isinstance(response, dict):
                record_conflict("item.completed is missing item object")
                continue
            response_id = response.get("id")
            if response_id is None:
                # Real CLI completed items carry an id.  Count a malformed item
                # once by content, but make the evidence ineligible.
                response_key = "missing:" + hashlib.sha256(
                    json.dumps(response, sort_keys=True, default=str).encode("utf-8")
                ).hexdigest()
                record_conflict("item.completed is missing item.id")
            else:
                response_key = str(response_id)
            prior = completed_items.get(response_key)
            if prior is not None:
                if prior != response:
                    record_conflict(f"conflicting item.completed payload for item.id={response_key}")
                continue
            completed_items[response_key] = response
            call = completed_item_call(response)
            if call is not None:
                calls.append(call)
            if response.get("type") == "error":
                message = response.get("message") or response.get("error") or response.get("reason")
                if message:
                    errors.append(_extract_text(message))
        elif item_type in {"response_item", "tool_call", "tool.completed"}:
            response = payload
            response_type = str(response.get("type") or item_type)
            if response_type in {"function_call", "custom_tool_call", "local_shell_call", "tool_call", "tool.started", "tool.completed"}:
                name = str(response.get("name") or response.get("function_name") or "unknown")
                arguments = _extract_text(
                    response.get("arguments")
                    or response.get("arguments_json")
                    or response.get("input")
                    or response.get("command")
                    or ""
                )
                normalized_arguments = arguments.strip()
                call_id = response.get("call_id") or response.get("id") or response.get("tool_call_id")
                if call_id is not None:
                    key = f"id:{call_id}"
                    if key in call_keys:
                        continue
                    call_keys.add(key)
                # Generic response/tool-call records do not prove a process
                # outcome.  Treat their verification as having entered the
                # verifier, so missing evidence can never excuse a duplicate.
                calls.append({"name": name, "arguments": normalized_arguments, "exit_code": None})
        elif item_type in {"process_step", "step"}:
            process_steps = (process_steps or 0) + 1

        if item.get("returncode") is not None:
            returncode = item.get("returncode")
        if item.get("attempts") is not None:
            attempts = item.get("attempts")
        if item.get("host_retries") is not None:
            host_retries = item.get("host_retries")
        if item.get("wall_time_ms") is not None:
            wall_time_ms = item.get("wall_time_ms")
        if item.get("process_steps") is not None:
            process_steps = item.get("process_steps")
        if isinstance(item.get("quality"), dict):
            quality = item["quality"]
            if quality.get("passed") is not None:
                quality_passed = _bool_or_none(quality.get("passed"), "quality.passed")
        if isinstance(item.get("route"), dict):
            merge_without_overwrite(route, item["route"], "route")
        if isinstance(item.get("measurement"), dict):
            merge_without_overwrite(measurement, item["measurement"], "measurement")
        if isinstance(item.get("protocol"), dict):
            merge_without_overwrite(protocol, item["protocol"], "protocol")
        failure_class = item.get("failure_class") or failure_class
        infrastructure_reason = item.get("infrastructure_reason") or infrastructure_reason
        cell_id = item.get("cell_id") or cell_id
        replacement_of = item.get("replacement_of") or replacement_of
        retry_of = item.get("retry_of") or retry_of
        replacement_index = item.get("replacement_index", replacement_index)
        replacement_authorized = item.get("replacement_authorized", replacement_authorized)
        replacement_reason = item.get("replacement_reason") or replacement_reason

    # Resolve usage by source rather than allowing the last record to silently
    # overwrite earlier evidence.  event_msg totals are cumulative, so only a
    # decrease is contradictory; terminal/explicit records must agree exactly.
    resolved_usage: Dict[str, Dict[str, Any]] = {}
    for kind, records in usage_records.items():
        if kind == "event_msg":
            for earlier, later in zip(records, records[1:]):
                for key in set(earlier) & set(later):
                    if isinstance(earlier[key], int) and isinstance(later[key], int) and later[key] < earlier[key]:
                        record_conflict(f"non-monotonic {kind} usage for {key}")
            resolved_usage[kind] = records[-1]
        else:
            resolved_usage[kind] = records[0]
            if any(record != records[0] for record in records[1:]):
                record_conflict(f"conflicting {kind} usage records")
    for kind in ("turn.completed", "explicit", "event_msg"):
        if kind in resolved_usage:
            usage = dict(resolved_usage[kind])
            primary_kind = kind
            break
    else:
        primary_kind = None
    if primary_kind is not None:
        for kind, candidate in resolved_usage.items():
            if kind == primary_kind:
                continue
            for key in set(usage) & set(candidate):
                if usage[key] != candidate[key]:
                    record_conflict(
                        f"usage mismatch between {primary_kind} and {kind} for {key}"
                    )

    observed_ids = thread_ids or session_ids
    if observed_ids:
        observed_count = len(observed_ids)
        protocol["observed_root_session_count"] = observed_count
        protocol["root_session_fingerprints"] = sorted(
            hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
            for value in observed_ids
        )
        declared_count = protocol.get("root_session_count")
        if declared_count is not None and declared_count != observed_count:
            protocol["declared_root_session_count"] = declared_count
            record_conflict(
                f"declared root_session_count={declared_count} contradicts observed count={observed_count}"
            )
        protocol["root_session_count"] = observed_count
        if observed_count != 1:
            record_conflict(f"multiple root thread/session identities observed: {observed_count}")
    if thread_ids and session_ids and thread_ids != session_ids:
        # Do not add the sets together (the two event surfaces can name the
        # same root differently), but retain their separate cardinalities.
        protocol["observed_thread_count"] = len(thread_ids)
        protocol["observed_session_meta_count"] = len(session_ids)
        if len(thread_ids) != 1 or len(session_ids) != 1:
            record_conflict("thread.started and session_meta identity evidence disagree")

    if parser_contamination:
        existing_contamination = measurement.get("contamination")
        if isinstance(existing_contamination, list):
            measurement["contamination"] = list(
                dict.fromkeys([*existing_contamination, *parser_contamination])
            )
        else:
            measurement["contamination"] = list(parser_contamination)
    if parser_violations:
        existing_violations = protocol.get("violations")
        if not isinstance(existing_violations, list):
            existing_violations = []
        protocol["violations"] = list(dict.fromkeys([*existing_violations, *parser_violations]))
        protocol["valid"] = False

    if explicit_arm is None:
        explicit_arm = "unknown"
    normalized_usage = {key: usage.get(key) for key in TOKEN_KEYS}
    verification_canonicals: List[str] = []
    verification_outcomes: Dict[str, List[Tuple[Optional[int], bool]]] = collections.defaultdict(list)
    code_generation = 0
    for call in calls:
        if call["name"] == "file_change":
            code_generation += 1
            continue
        semantic_keys = _verification_semantic_keys(call["name"], call["arguments"])
        recovery_eligible = (
            call["name"] == "command_execution"
            and len(semantic_keys) == 1
            and re.search(r"&&|\|\||;|\n", call["arguments"]) is None
        )
        for key in semantic_keys:
            canonical = f"generation:{code_generation}|{key}"
            verification_canonicals.append(canonical)
            verification_outcomes[canonical].append(
                (call.get("exit_code"), recovery_eligible)
            )

    duplicate_verification_calls = sum(
        max(0, len(outcomes) - 1) for outcomes in verification_outcomes.values()
    )
    verification_recovery_calls = 0
    for outcomes in verification_outcomes.values():
        # A recovery is one immediately paired 126/127 -> 0 substitution for a
        # single verification command.  It removes exactly one semantic repeat.
        # Repeating the broken command twice, crossing a product edit, or using
        # a compound command remains visible and cannot be washed away.
        for earlier, later in zip(outcomes, outcomes[1:]):
            earlier_exit, earlier_eligible = earlier
            later_exit, later_eligible = later
            if (
                earlier_exit in {126, 127}
                and later_exit == 0
                and earlier_eligible
                and later_eligible
            ):
                verification_recovery_calls += 1
                duplicate_verification_calls -= 1
    if calls and process_steps is None:
        # Tool calls are observable process steps only as a fallback when the
        # producer has no richer step count; the report labels both separately.
        process_steps = len(calls)
    return {
        "schema_version": 1,
        "cell_id": cell_id,
        "cell_id_supplied": cell_id is not None,
        "replacement_of": replacement_of,
        "retry_of": retry_of or replacement_of,
        "replacement_index": replacement_index,
        "replacement_authorized": replacement_authorized,
        "replacement_reason": replacement_reason,
        "arm": explicit_arm,
        "version": explicit_version,
        "runtime": {
            "model": context.get("model") or session.get("model"),
            "effort": context.get("effort") or session.get("effort"),
            "requested_service_tier": (
                context.get("requested_service_tier")
                or context.get("service_tier")
                or session.get("requested_service_tier")
                or session.get("service_tier")
            ),
        },
        "attempts": attempts,
        "host_retries": host_retries,
        "returncode": returncode,
        "wall_time_ms": wall_time_ms,
        "completion": {"turn_completed": completed},
        "quality": {"passed": quality_passed, "checks": quality_checks},
        "telemetry": {
            **normalized_usage,
            "tool_calls": len(calls) if calls else None,
            "process_steps": process_steps,
            "verification_calls": len(verification_canonicals) if calls else None,
            "verification_recovery_calls": verification_recovery_calls if calls else None,
            "duplicate_verification_calls": duplicate_verification_calls if calls else None,
        },
        "route": route,
        "measurement": measurement,
        "protocol": protocol,
        "failure_class": failure_class,
        "infrastructure_reason": infrastructure_reason,
        "errors": errors,
        "synthetic": False,
    }


def _load_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise CellFormatError(f"cannot read JSON cell {path}: {error}") from error
    if not isinstance(value, dict):
        raise CellFormatError(f"JSON cell {path} must be an object")
    return value


def _find_cell(path: Path) -> Path:
    if path.is_file():
        return path
    for name in ("cell.json", "result.json", "events.jsonl"):
        candidate = path / name
        if candidate.is_file():
            return candidate
    raise CellFormatError(f"no cell.json, result.json, or events.jsonl under {path}")


def _merge_event_evidence(
    event_data: Dict[str, Any], producer: Dict[str, Any], *, source: Path
) -> Dict[str, Any]:
    """Merge a producer envelope without allowing it to erase raw evidence."""

    merged = {**event_data, **producer}
    protocol = {**_first_dict(producer.get("protocol"))}
    measurement = {**_first_dict(producer.get("measurement"))}
    violations = list(protocol.get("violations") or [])
    contamination = list(measurement.get("contamination") or [])

    def conflict(message: str) -> None:
        if message not in violations:
            violations.append(message)
        if message not in contamination:
            contamination.append(message)

    event_protocol = _first_dict(event_data.get("protocol"))
    for key, value in event_protocol.items():
        if key in protocol and protocol[key] != value and key not in {"violations", "valid"}:
            conflict(f"producer protocol.{key} contradicts raw events")
        protocol[key] = value
    for message in event_protocol.get("violations") or []:
        if message not in violations:
            violations.append(str(message))
    if event_protocol.get("valid") is False:
        protocol["valid"] = False

    event_measurement = _first_dict(event_data.get("measurement"))
    for message in event_measurement.get("contamination") or []:
        if message not in contamination:
            contamination.append(str(message))

    producer_completion = _first_dict(producer.get("completion"))
    event_completion = _first_dict(event_data.get("completion"))
    event_completed = event_completion.get("turn_completed")
    producer_completed = producer_completion.get("turn_completed")
    if event_completed is not None:
        if producer_completed is not None and producer_completed != event_completed:
            conflict("producer completion contradicts raw events")
        merged["completion"] = event_completion

    producer_telemetry = _first_dict(producer.get("telemetry"), producer.get("usage"))
    event_telemetry = _first_dict(event_data.get("telemetry"))
    telemetry = dict(producer_telemetry)
    event_derived_metrics = {
        "tool_calls",
        "process_steps",
        "verification_calls",
        "verification_recovery_calls",
        "duplicate_verification_calls",
    }
    for key, value in event_telemetry.items():
        if value is None:
            continue
        if (
            key not in event_derived_metrics
            and key in telemetry
            and telemetry[key] is not None
            and telemetry[key] != value
        ):
            conflict(f"producer telemetry.{key} contradicts raw events")
        telemetry[key] = value
    merged["telemetry"] = telemetry

    event_route = _first_dict(event_data.get("route"))
    route = dict(_first_dict(producer.get("route")))
    for key, value in event_route.items():
        if key in route and route[key] != value:
            conflict(f"producer route.{key} contradicts raw events")
        route[key] = value
    merged["route"] = route

    if violations:
        protocol["valid"] = False
        protocol["violations"] = violations
    if contamination:
        measurement["contamination"] = contamination
    merged["protocol"] = protocol
    merged["measurement"] = measurement
    merged["errors"] = list(
        dict.fromkeys(
            [str(item) for item in (event_data.get("errors") or [])]
            + [str(item) for item in (producer.get("errors") or [])]
        )
    )
    return merged


def load_cell(path: Path, *, arm_hint: Optional[str] = None) -> Dict[str, Any]:
    source = _find_cell(path)
    if source.suffix == ".jsonl":
        raw = parse_events(source, arm=arm_hint)
    else:
        raw = _load_json(source)
        if isinstance(raw.get("result"), dict):
            raw = {**raw, **raw["result"]}
        if raw.get("events_file"):
            event_path = (source.parent / str(raw["events_file"])).resolve()
            event_data = parse_events(event_path, arm=arm_hint)
            raw = _merge_event_evidence(event_data, raw, source=source)
        raw.setdefault("arm", arm_hint or raw.get("candidate") or source.parent.name)
        raw.setdefault("version", raw.get("plugin_version"))
        raw.setdefault("runtime", _first_dict(raw.get("runtime"), raw.get("identity")))
        raw.setdefault("completion", _first_dict(raw.get("completion"), raw.get("observed")))
        raw.setdefault("quality", _first_dict(raw.get("quality"), raw.get("grading")))
        raw.setdefault("telemetry", _first_dict(raw.get("telemetry"), raw.get("usage")))
        raw.setdefault("measurement", _first_dict(raw.get("measurement")))
        raw.setdefault("errors", [])
    return normalize_cell(raw, source=source, arm_hint=arm_hint)


def normalize_cell(raw: Dict[str, Any], *, source: Path, arm_hint: Optional[str] = None) -> Dict[str, Any]:
    arm = str(raw.get("arm") or arm_hint or "unknown")
    if arm not in ARMS:
        raise CellFormatError(f"{source}: unknown arm {arm!r}")
    version = raw.get("version")
    expected_version = EXPECTED_VERSIONS[arm]
    if expected_version is not None and version != expected_version:
        raise CellFormatError(f"{source}: {arm} expected version {expected_version!r}, got {version!r}")
    if arm == "direct" and version not in (None, "direct"):
        raise CellFormatError(f"{source}: Direct arm must not carry a Goldilocks version")

    runtime = _first_dict(raw.get("runtime"), raw.get("identity"))
    completion = _first_dict(raw.get("completion"), raw.get("observed"))
    quality = _first_dict(raw.get("quality"), raw.get("grading"))
    telemetry = _first_dict(raw.get("telemetry"), raw.get("usage"))
    errors = raw.get("errors") or []
    if not isinstance(errors, list):
        raise CellFormatError(f"{source}: errors must be a list")

    attempts = _as_int(raw.get("attempts"), "attempts")
    host_retries = _as_int(raw.get("host_retries"), "host_retries")
    returncode = _as_int(raw.get("returncode"), "returncode")
    wall_time_ms = _as_int(raw.get("wall_time_ms"), "wall_time_ms")
    turn_completed = _bool_or_none(
        completion.get("turn_completed", completion.get("completed")),
        "completion.turn_completed",
    )
    quality_passed = _bool_or_none(quality.get("passed", quality.get("quality_passed")), "quality.passed")
    checks = quality.get("checks") or []
    if not isinstance(checks, list):
        raise CellFormatError(f"{source}: quality.checks must be a list")

    failure_class = raw.get("failure_class")
    if failure_class is not None:
        failure_class = str(failure_class)
        if failure_class not in FAILURE_CLASSES:
            raise CellFormatError(
                f"{source}: failure_class must be one of {list(FAILURE_CLASSES)!r}"
            )
    infrastructure_reason = raw.get("infrastructure_reason")
    if infrastructure_reason is not None:
        infrastructure_reason = str(infrastructure_reason)
        if infrastructure_reason not in INFRASTRUCTURE_REASONS:
            raise CellFormatError(
                f"{source}: infrastructure_reason must be one of "
                f"{list(INFRASTRUCTURE_REASONS)!r}"
            )
    if failure_class == "infrastructure_invalid" and infrastructure_reason is None:
        raise CellFormatError(
            f"{source}: infrastructure_invalid requires a whitelisted infrastructure_reason"
        )
    if failure_class != "infrastructure_invalid" and infrastructure_reason is not None:
        raise CellFormatError(
            f"{source}: infrastructure_reason is only valid with infrastructure_invalid"
        )
    replacement_index = _as_int(raw.get("replacement_index"), "replacement_index")
    replacement_authorized = _bool_or_none(
        raw.get("replacement_authorized"), "replacement_authorized"
    )
    retry_of = raw.get("retry_of") or raw.get("replacement_of")
    if retry_of is not None and not str(retry_of).strip():
        raise CellFormatError(f"{source}: retry_of must be a non-empty cell id")
    replacement_reason = raw.get("replacement_reason")
    if replacement_reason is not None and not isinstance(replacement_reason, str):
        raise CellFormatError(f"{source}: replacement_reason must be a string")

    measurement = _first_dict(raw.get("measurement"))
    if "contamination" in measurement and not isinstance(measurement["contamination"], list):
        raise CellFormatError(f"{source}: measurement.contamination must be a list")

    normalized: Dict[str, Any] = {
        "schema_version": raw.get("schema_version", 1),
        "source": str(source),
        "cell_id": str(
            raw.get("cell_id")
            or f"{arm}:{hashlib.sha256(str(source.resolve()).encode('utf-8')).hexdigest()[:12]}"
        ),
        "cell_id_supplied": bool(raw.get("cell_id")),
        "replacement_of": raw.get("replacement_of"),
        "retry_of": str(retry_of) if retry_of is not None else None,
        "replacement_index": replacement_index,
        "replacement_authorized": replacement_authorized,
        "replacement_reason": replacement_reason,
        "arm": arm,
        "version": version,
        "runtime": {
            "model": runtime.get("model"),
            "effort": runtime.get("effort"),
            "requested_service_tier": (
                runtime.get("requested_service_tier") or runtime.get("service_tier")
            ),
        },
        "attempts": attempts,
        "host_retries": host_retries,
        "returncode": returncode,
        "wall_time_ms": wall_time_ms,
        "completion": {"turn_completed": turn_completed},
        "quality": {"passed": quality_passed, "checks": checks},
        "telemetry": {},
        "route": _first_dict(raw.get("route")),
        "measurement": measurement,
        "errors": [str(error) for error in errors],
        "synthetic": bool(raw.get("synthetic", False)),
        "protocol": _first_dict(raw.get("protocol")),
        "failure_class": failure_class,
        "infrastructure_reason": infrastructure_reason,
    }
    for key in TOKEN_KEYS + (
        "tool_calls",
        "process_steps",
        "verification_calls",
        "verification_recovery_calls",
        "duplicate_verification_calls",
    ):
        normalized["telemetry"][key] = _as_int(telemetry.get(key), f"telemetry.{key}")
    input_tokens = normalized["telemetry"]["input_tokens"]
    cached_tokens = normalized["telemetry"]["cached_input_tokens"]
    cache_write_tokens = normalized["telemetry"]["cache_write_input_tokens"]
    token_partition_valid = not (
        input_tokens is not None
        and cached_tokens is not None
        and cache_write_tokens is not None
        and cached_tokens + cache_write_tokens > input_tokens
    ) and not (
        input_tokens is not None
        and cached_tokens is not None
        and cached_tokens > input_tokens
    )
    normalized["telemetry"]["token_partition_valid"] = token_partition_valid
    normalized["telemetry"]["raw_tokens"] = (
        input_tokens + normalized["telemetry"]["output_tokens"]
        if input_tokens is not None and normalized["telemetry"]["output_tokens"] is not None
        else None
    )
    normalized["telemetry"]["cache_hit_rate"] = (
        round(cached_tokens / input_tokens, 6)
        if token_partition_valid and input_tokens not in (None, 0) and cached_tokens is not None
        else None
    )
    # Never trust or mix a producer-supplied cost.  Recompute every comparable
    # cell from the same frozen rate table so all three arms share one basis.
    normalized["telemetry"]["normalized_cost_usd"] = _normalized_cost(normalized)
    normalized["telemetry"]["cache_neutral_cost_usd"] = _cache_neutral_cost(normalized)
    return normalized


def _normalized_cost(cell: Dict[str, Any]) -> Optional[float]:
    telemetry = cell["telemetry"]
    measurement = cell.get("measurement", {})
    if measurement.get("cost_comparable") is not True:
        return None
    if measurement.get("pricing_provenance") != PRICING_PROVENANCE:
        return None
    contamination = measurement.get("contamination")
    if contamination != []:
        return None
    # The smoke task must remain single-root Direct. Mixed-model totals need
    # per-model attribution and therefore stay N/A in this minimal harness.
    if cell.get("route", {}).get("child_starts") != 0:
        return None
    model = cell.get("runtime", {}).get("model")
    rate = NORMALIZED_RATES.get(model)
    if rate is None:
        return None
    input_tokens = telemetry.get("input_tokens")
    cached_tokens = telemetry.get("cached_input_tokens")
    output_tokens = telemetry.get("output_tokens")
    cache_write_observed = telemetry.get("cache_write_input_tokens")
    if input_tokens is None or cached_tokens is None or output_tokens is None:
        return None
    # Codex's public turn.completed usage does not always expose a distinct
    # cache-write partition.  Preserve that field as N/A in telemetry, while
    # charging all non-cached input at the regular input rate.  When a producer
    # does expose a write partition, use the frozen comparison proxy for it.
    cache_write = cache_write_observed if cache_write_observed is not None else 0
    # Token partitions were validated during normalization.  Silently clipping
    # an impossible producer record would turn corrupt telemetry into a cheap
    # looking result, so cost calculation deliberately performs no clamping.
    if cached_tokens + cache_write > input_tokens:
        return None
    uncached = input_tokens - cached_tokens - cache_write
    value = (
        uncached * rate["input"]
        + cached_tokens * rate["cached"]
        + cache_write * rate["cache_write"]
        + output_tokens * rate["output"]
    ) / 1_000_000
    return round(value, 9)


def _cache_neutral_cost(cell: Dict[str, Any]) -> Optional[float]:
    """Price all input at one uncached rate while preserving output cost."""

    telemetry = cell["telemetry"]
    measurement = cell.get("measurement", {})
    if measurement.get("cost_comparable") is not True:
        return None
    if measurement.get("pricing_provenance") != PRICING_PROVENANCE:
        return None
    if measurement.get("contamination") != []:
        return None
    if cell.get("route", {}).get("child_starts") != 0:
        return None
    rate = NORMALIZED_RATES.get(cell.get("runtime", {}).get("model"))
    input_tokens = telemetry.get("input_tokens")
    output_tokens = telemetry.get("output_tokens")
    if rate is None or input_tokens is None or output_tokens is None:
        return None
    value = (input_tokens * rate["input"] + output_tokens * rate["output"]) / 1_000_000
    return round(value, 9)


def invalid_cell(arm: str, error: str) -> Dict[str, Any]:
    return {
        "schema_version": 1,
        "source": None,
        "cell_id": None,
        "cell_id_supplied": False,
        "replacement_of": None,
        "retry_of": None,
        "replacement_index": None,
        "replacement_authorized": None,
        "replacement_reason": None,
        "arm": arm,
        "version": EXPECTED_VERSIONS[arm],
        "runtime": {},
        "attempts": None,
        "host_retries": None,
        "returncode": None,
        "wall_time_ms": None,
        "completion": {"turn_completed": None},
        "quality": {"passed": None, "checks": []},
        "telemetry": {key: None for key in METRIC_KEYS},
        "route": {},
        "measurement": {},
        "protocol": {},
        "failure_class": "infrastructure_invalid",
        "infrastructure_reason": "evidence_input",
        "errors": [error],
        "synthetic": False,
    }


def _protocol_violations(cell: Dict[str, Any]) -> List[str]:
    violations: List[str] = []
    protocol = cell.get("protocol", {})
    runtime = cell.get("runtime", {})
    hashes = expected_protocol_hashes()
    if runtime.get("model") != "gpt-5.6-sol":
        violations.append("root model identity is not gpt-5.6-sol")
    if runtime.get("effort") != "high":
        violations.append("root reasoning effort is not high")
    if runtime.get("requested_service_tier") != "standard":
        violations.append("requested service tier is not standard")
    for key, expected in hashes.items():
        if protocol.get(key) != expected:
            violations.append(f"{key} does not match the frozen task")
    if protocol.get("source_frozen") is not True:
        violations.append("arm source was not frozen before execution")
    if protocol.get("runtime_identity_verified") is not True:
        violations.append("runtime identity was not independently verified")
    if protocol.get("root_session_count") != 1:
        violations.append("exactly one root session is required")
    child_count = protocol.get("child_session_count")
    if not isinstance(child_count, int) or isinstance(child_count, bool) or child_count < 0:
        violations.append("child session count is not proven")
    elif child_count != 0:
        # This deliberately small smoke task is expected to stay Direct in all
        # three arms.  Requiring a single root session keeps token attribution
        # and normalized cost comparable without guessing child-model prices.
        violations.append(f"{cell['arm']} smoke cell must not start a child session")
    if protocol.get("usage_deduplicated") is not True:
        violations.append("root/child usage was not de-duplicated")
    for key in ("same_host", "same_toolset", "cold_context"):
        if protocol.get(key) is not True:
            violations.append(f"control parity {key} is not proven")
    if protocol.get("approval_policy") != "never":
        violations.append("approval policy parity is not proven")
    if protocol.get("sandbox") != "danger-full-access":
        violations.append("sandbox permission parity is not full-access")
    if protocol.get("full_access") is not True:
        violations.append("full-access permission parity is not proven")
    if cell["arm"] == "direct":
        if protocol.get("direct_pure") is not True:
            violations.append("Direct purity is not proven")
        if protocol.get("plugin_identity_verified") not in (None, False):
            violations.append("Direct must not report an installed workflow plugin")
        direct_evidence = {
            "plugin_list_root_key": "installed",
            "goldilocks_plugin_ids": [],
            "isolated_skills_entries": [],
            "isolated_marketplace_entries": [],
            "compact_prompt_present": False,
            "prompt_input_goldilocks_mentions": 0,
        }
        for key, expected in direct_evidence.items():
            if protocol.get(key) != expected:
                violations.append(f"Direct isolation evidence {key} is not {expected!r}")
    else:
        if protocol.get("plugin_identity_verified") is not True:
            violations.append("installed plugin identity is not proven")
        if not protocol.get("source_sha256"):
            violations.append("frozen plugin source digest is missing")
    return violations


def _measurement_gaps(cell: Dict[str, Any]) -> List[str]:
    gaps: List[str] = []
    telemetry = cell.get("telemetry", {})
    route = cell.get("route", {})
    if cell.get("wall_time_ms") is None:
        gaps.append("wall_time_ms")
    elif cell.get("wall_time_ms") <= 0:
        gaps.append("wall_time_ms.must_be_positive")
    for key in (
        "input_tokens",
        "cached_input_tokens",
        "output_tokens",
        "raw_tokens",
        "normalized_cost_usd",
        "cache_neutral_cost_usd",
        "tool_calls",
        "process_steps",
        "verification_calls",
        "duplicate_verification_calls",
    ):
        if telemetry.get(key) is None:
            gaps.append(f"telemetry.{key}")
    if cell.get("arm") == "v060_beta1":
        for key in (
            "selected",
            "child_starts",
            "user_roundtrips",
            "unnecessary_state_writes",
            "workflow_documents_created",
            "background_actions",
        ):
            if route.get(key) is None:
                gaps.append(f"route.{key}")
    if cell.get("measurement", {}).get("cost_comparable") is not True:
        gaps.append("measurement.cost_comparable")
    if cell.get("measurement", {}).get("pricing_provenance") != PRICING_PROVENANCE:
        gaps.append("measurement.pricing_provenance")
    if cell.get("measurement", {}).get("contamination") != []:
        gaps.append("measurement.contamination")
    if telemetry.get("token_partition_valid") is False:
        gaps.append("telemetry.token_partition_valid")
    return gaps


def _hidden_acceptance_records(cell: Dict[str, Any]) -> List[Dict[str, Any]]:
    expected = expected_protocol_hashes()["grader_sha256"]
    records: List[Dict[str, Any]] = []
    for check in cell.get("quality", {}).get("checks", []):
        if not isinstance(check, dict):
            continue
        if (
            check.get("kind") == "hidden_acceptance"
            and check.get("grader_sha256") == expected
        ):
            records.append(check)
    return records


def _hidden_acceptance_outcome(cell: Dict[str, Any]) -> Optional[bool]:
    records = _hidden_acceptance_records(cell)
    if len(records) != 1:
        return None
    check = records[0]
    passed = check.get("passed")
    returncode = check.get("returncode")
    if passed is not None and not isinstance(passed, bool):
        return None
    if returncode is not None and (isinstance(returncode, bool) or not isinstance(returncode, int)):
        return None
    by_returncode = returncode == 0 if returncode is not None else None
    if passed is not None and by_returncode is not None and passed != by_returncode:
        return None
    return passed if passed is not None else by_returncode


def _hidden_acceptance_proven(cell: Dict[str, Any]) -> bool:
    outcome = _hidden_acceptance_outcome(cell)
    return outcome is not None and outcome == cell.get("quality", {}).get("passed")


def classify_cell(cell: Dict[str, Any]) -> Dict[str, Any]:
    completion = cell["completion"].get("turn_completed")
    quality = cell["quality"].get("passed")
    infra_reasons: List[str] = []
    protocol_reasons: List[str] = []
    evidence_gaps: List[str] = []
    explicit_failure = cell.get("failure_class")

    # Infrastructure is never guessed from free-form error text.  A producer
    # must use the single structured enum plus a whitelisted reason; malformed
    # local evidence is normalized through invalid_cell() to the same shape.
    if explicit_failure == "infrastructure_invalid":
        reason = cell.get("infrastructure_reason")
        infra_reasons.append(f"structured infrastructure failure: {reason}")
        infra_reasons.extend(cell.get("errors") or [])

    if cell.get("attempts") is None:
        evidence_gaps.append("attempt count evidence missing")
    elif cell.get("attempts") != 1:
        protocol_reasons.append("protocol requires exactly one attempt")
    if cell.get("host_retries") is None:
        evidence_gaps.append("host retry evidence missing")
    elif cell.get("host_retries") != 0:
        protocol_reasons.append("automatic/host retry occurred")

    if cell.get("returncode") is None:
        evidence_gaps.append("returncode evidence missing")
    if completion is None:
        evidence_gaps.append("turn completion evidence missing")
    # A failed root process/turn without a structured infrastructure reason is
    # inconclusive, not permission to call a product-quality failure "infra".
    if explicit_failure != "infrastructure_invalid":
        if cell.get("returncode") not in (None, 0):
            evidence_gaps.append(
                f"unclassified root execution failure: returncode={cell.get('returncode')}"
            )
        if completion is False:
            evidence_gaps.append("unclassified incomplete root turn")

    protocol = cell.get("protocol", {})
    if isinstance(protocol, dict) and protocol.get("valid") is False:
        protocol_reasons.extend(str(item) for item in (protocol.get("violations") or ["producer marked protocol invalid"]))
    protocol_reasons.extend(_protocol_violations(cell))
    if explicit_failure == "protocol_invalid":
        protocol_reasons.extend(cell.get("errors") or ["producer marked protocol invalid"])

    if explicit_failure == "quality_failure" and quality is not False:
        protocol_reasons.append("quality_failure requires quality.passed=false")
    hidden_acceptance_count = len(_hidden_acceptance_records(cell))
    if hidden_acceptance_count > 1:
        protocol_reasons.append("hidden acceptance must be recorded exactly once")
    elif hidden_acceptance_count == 1:
        hidden_outcome = _hidden_acceptance_outcome(cell)
        if hidden_outcome is None:
            protocol_reasons.append("hidden acceptance result is missing or contradictory")
        elif quality is not None and hidden_outcome != quality:
            protocol_reasons.append("quality.passed contradicts hidden acceptance")

    # Deliberate precedence: infrastructure -> protocol -> quality evidence ->
    # quality result -> measurement.  A later layer can never relabel an
    # earlier failure or make it comparison-eligible.
    if infra_reasons:
        status = "infrastructure_failure"
        infrastructure_passed = False
        protocol_passed = False
    elif protocol_reasons:
        status = "protocol_failure"
        infrastructure_passed = True
        protocol_passed = False
    elif evidence_gaps:
        status = "evidence_gap"
        infrastructure_passed = True
        protocol_passed = True
    elif quality is None:
        status = "evidence_gap"
        infrastructure_passed = True
        protocol_passed = True
    elif quality is False or explicit_failure == "quality_failure":
        # A producer cannot turn an explicit failed external grade into an
        # evidence gap merely by omitting the corresponding hidden check.
        status = "quality_failure"
        infrastructure_passed = True
        protocol_passed = True
    elif not _hidden_acceptance_proven(cell):
        status = "evidence_gap"
        infrastructure_passed = True
        protocol_passed = True
    elif _measurement_gaps(cell):
        status = "measurement_partial"
        infrastructure_passed = True
        protocol_passed = True
    else:
        status = "eligible"
        infrastructure_passed = True
        protocol_passed = True
    eligible_measurement = status == "eligible"
    # Keep producer observations available for audit, but never expose them as
    # comparison metrics when infrastructure/protocol/evidence is invalid.
    observed = {
        "quality_passed": quality,
        "completion_passed": completion,
        "wall_time_ms": cell.get("wall_time_ms"),
        "metrics": cell.get("telemetry", {}),
    }
    public_quality = quality if status in {"eligible", "quality_failure", "measurement_partial"} else None
    public_completion = completion if status in {"eligible", "quality_failure", "measurement_partial"} else None
    public_wall = cell.get("wall_time_ms") if eligible_measurement else None
    public_metrics = cell.get("telemetry", {}) if eligible_measurement else {
        key: None for key in METRIC_KEYS
    }
    return {
        "arm": cell["arm"],
        "version": cell.get("version"),
        "status": status,
        "comparison_eligible": status == "eligible",
        "infrastructure_passed": infrastructure_passed,
        "protocol_passed": protocol_passed,
        "quality_passed": public_quality,
        "completion_passed": public_completion,
        "attempts": cell.get("attempts"),
        "host_retries": cell.get("host_retries"),
        "wall_time_ms": public_wall,
        "metrics": public_metrics,
        "observed": observed,
        "route": cell.get("route", {}),
        "measurement": cell.get("measurement", {}),
        "measurement_gaps": _measurement_gaps(cell),
        "protocol": cell.get("protocol", {}),
        "errors": list(infra_reasons),
        "evidence_gaps": list(evidence_gaps),
        "reported_errors": list(cell.get("errors") or []),
        "protocol_reasons": list(protocol_reasons),
        "quality_evidence_proven": _hidden_acceptance_proven(cell),
        "quality_checks": cell.get("quality", {}).get("checks", []),
        "synthetic": bool(cell.get("synthetic", False)),
    }


def _invalidate_row_protocol(row: Dict[str, Any], reason: str) -> None:
    """Apply a late chain/cross-arm protocol failure without leaking metrics."""

    row["status"] = "protocol_failure"
    row["comparison_eligible"] = False
    row["infrastructure_passed"] = True
    row["protocol_passed"] = False
    row["protocol_reasons"] = list(row.get("protocol_reasons") or []) + [reason]
    row["quality_passed"] = None
    row["completion_passed"] = None
    row["wall_time_ms"] = None
    row["metrics"] = {key: None for key in METRIC_KEYS}


def load_cells(input_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    seen_cell_ids: Dict[str, str] = {}
    for arm in ARMS:
        history = load_arm_history(input_dir, arm)
        chain = validate_replacement_chain(history)
        # The last retained record is the one eligible for comparison.  The
        # original remains attached as audit evidence and is never discarded.
        cell = history[-1]
        row = classify_cell(cell)
        cell_id = cell.get("cell_id")
        if cell_id and cell.get("cell_id_supplied"):
            previous_arm = seen_cell_ids.get(str(cell_id))
            if previous_arm is not None:
                _invalidate_row_protocol(row, f"cell_id duplicates {previous_arm}")
            else:
                seen_cell_ids[str(cell_id)] = arm
        if not chain["valid"]:
            # Replacement protocol is an evidence-layer failure even if the
            # selected record itself also failed to execute.  Never let an
            # invalid chain masquerade as an authorized infrastructure sample.
            _invalidate_row_protocol(row, chain["reason"])
        row["replacement_chain"] = chain
        row["retained_history"] = [
            {
                "cell_id": item.get("cell_id"),
                "history_label": item.get("history_label"),
                "status": classify_cell(item)["status"],
                "source": item.get("source"),
                "attempts": item.get("attempts"),
            }
            for item in history
        ]
        rows.append(row)
    return rows


def _arm_sources(input_dir: Path, arm: str) -> List[Tuple[str, Path]]:
    """Return original then at most one explicitly retained replacement."""

    arm_dir = input_dir / arm
    if not arm_dir.is_dir():
        raise CellFormatError(f"arm directory missing: {arm_dir}")
    evidence_names = ("cell.json", "result.json", "events.jsonl")
    evidence_like = sorted(
        path.relative_to(arm_dir).as_posix()
        for path in arm_dir.rglob("*")
        if path.is_file() and path.name in evidence_names
    )
    root_evidence = [arm_dir / name for name in evidence_names if (arm_dir / name).is_file()]
    original = arm_dir / "original"
    replacement = arm_dir / "replacement"
    chain_like = sorted(
        child.name
        for child in arm_dir.iterdir()
        if child.is_dir() and (child.name == "original" or child.name.startswith("replacement"))
    )
    if original.exists() or replacement.exists() or chain_like:
        if root_evidence:
            raise CellFormatError("replacement chain cannot coexist with root cell evidence")
        if chain_like != ["original", "replacement"]:
            raise CellFormatError(
                "replacement chain requires exactly original/ and replacement/"
            )
        sources: List[Tuple[str, Path]] = []
        for label, directory in (("original", original), ("replacement", replacement)):
            evidence = [directory / name for name in evidence_names if (directory / name).is_file()]
            if len(evidence) != 1:
                raise CellFormatError(
                    f"{label} must contain exactly one normalized evidence file"
                )
            sources.append((label, evidence[0]))
        allowed = {
            f"original/{sources[0][1].name}",
            f"replacement/{sources[1][1].name}",
            "original/events/events.jsonl",
            "replacement/events/events.jsonl",
        }
        extras = sorted(set(evidence_like) - allowed)
        if extras:
            raise CellFormatError(f"unexpected extra evidence records: {extras}")
        return sources
    if len(root_evidence) != 1:
        raise CellFormatError("arm must contain exactly one normalized evidence file")
    # The execution runner retains the raw CLI stream under events/ while the
    # normalized, externally graded record stays at the arm root.
    allowed = {root_evidence[0].name, "events/events.jsonl"}
    extras = sorted(set(evidence_like) - allowed)
    if extras:
        raise CellFormatError(f"unexpected extra evidence records: {extras}")
    return [("primary", root_evidence[0])]


def load_arm_history(input_dir: Path, arm: str) -> List[Dict[str, Any]]:
    """Load an arm's original/replacement chain while retaining both records."""

    records: List[Dict[str, Any]] = []
    try:
        sources = _arm_sources(input_dir, arm)
    except (OSError, CellFormatError) as error:
        return [invalid_cell(arm, str(error))]
    for label, source in sources:
        try:
            cell = load_cell(source, arm_hint=arm)
            cell["history_label"] = label
            records.append(cell)
        except (OSError, CellFormatError) as error:
            records.append(invalid_cell(arm, str(error)))
            records[-1]["history_label"] = label
    return records


def validate_replacement_chain(records: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate the one-replacement rule without hiding the original evidence."""

    if not records:
        return {"valid": False, "reason": "no arm record"}
    if len(records) == 1:
        if records[0].get("history_label") == "replacement":
            return {"valid": False, "reason": "replacement exists without its retained original"}
        if any(
            records[0].get(key) is not None
            for key in (
                "replacement_of",
                "retry_of",
                "replacement_index",
                "replacement_authorized",
                "replacement_reason",
            )
        ):
            return {"valid": False, "reason": "primary cell carries replacement metadata"}
        return {"valid": True, "replacement_used": False, "retained_original": True}
    if len(records) != 2:
        return {"valid": False, "reason": "more than one replacement is not authorized"}
    original, replacement = records
    if original.get("history_label") != "original" or replacement.get("history_label") != "replacement":
        return {"valid": False, "reason": "replacement chain must retain original then replacement"}
    if original.get("failure_class") != "infrastructure_invalid":
        # A completed clean original, or an unstructured execution error,
        # cannot be replaced merely to select a nicer sample.
        return {
            "valid": False,
            "reason": "original must be structured infrastructure_invalid",
        }
    if original.get("attempts") not in (None, 0, 1):
        return {"valid": False, "reason": "original violated the one-attempt protocol"}
    if original.get("host_retries") not in (None, 0):
        return {"valid": False, "reason": "original includes an unauthorized host retry"}
    original_protocol = original.get("protocol", {})
    for key, expected in expected_protocol_hashes().items():
        observed = original_protocol.get(key)
        if observed is not None and observed != expected:
            return {"valid": False, "reason": f"original contradicts frozen {key}"}
    if original_protocol.get("root_session_count") not in (None, 1):
        return {"valid": False, "reason": "original contradicts the single-root protocol"}
    if original_protocol.get("child_session_count") not in (None, 0):
        return {"valid": False, "reason": "original started a child session"}
    if any(
        original.get(key) is not None
        for key in (
            "replacement_of",
            "retry_of",
            "replacement_index",
            "replacement_authorized",
            "replacement_reason",
        )
    ):
        return {"valid": False, "reason": "original carries replacement metadata"}
    if original.get("infrastructure_reason") not in INFRASTRUCTURE_REASONS:
        return {
            "valid": False,
            "reason": "original infrastructure_invalid lacks a whitelisted reason",
        }
    if not original.get("cell_id_supplied") or not replacement.get("cell_id_supplied"):
        return {"valid": False, "reason": "replacement chain requires explicit unique cell_id values"}
    if original.get("cell_id") == replacement.get("cell_id"):
        return {"valid": False, "reason": "replacement cell_id must differ from original"}
    if replacement.get("retry_of") != original.get("cell_id"):
        return {"valid": False, "reason": "retry_of does not point to retained original cell_id"}
    if replacement.get("replacement_of") not in (None, original.get("cell_id")):
        return {"valid": False, "reason": "replacement_of contradicts retry_of"}
    if replacement.get("replacement_index") != 1:
        return {"valid": False, "reason": "replacement_index must be 1"}
    if replacement.get("replacement_authorized") is not True:
        return {"valid": False, "reason": "replacement lacks explicit authorization"}
    if not str(replacement.get("replacement_reason") or "").strip():
        return {"valid": False, "reason": "replacement lacks an infrastructure reason"}
    if replacement.get("failure_class") in {"quality_failure", "protocol_invalid"}:
        return {"valid": False, "reason": "quality/protocol failure cannot be replacement-selected"}
    return {
        "valid": True,
        "replacement_used": True,
        "retained_original": True,
        "original_cell_id": original.get("cell_id"),
        "replacement_cell_id": replacement.get("cell_id"),
    }


def _percent(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return 0.0 if numerator == 0 else None
    return round((numerator / denominator - 1.0) * 100.0, 3)


def _cache_rate_delta(
    candidate_metrics: Dict[str, Any], baseline_metrics: Dict[str, Any], key: str
) -> Optional[float]:
    """Return an exact-input cache-rate delta; round only the display value."""

    candidate_input = candidate_metrics.get("input_tokens")
    baseline_input = baseline_metrics.get("input_tokens")
    candidate_value = candidate_metrics.get(key)
    baseline_value = baseline_metrics.get(key)
    if None in (candidate_input, baseline_input, candidate_value, baseline_value):
        return None
    if candidate_input == 0 or baseline_input == 0:
        if candidate_input == baseline_input == 0 and candidate_value == baseline_value == 0:
            return 0.0
        return None
    return candidate_value / candidate_input - baseline_value / baseline_input


def _cache_comparison(
    candidate_metrics: Dict[str, Any], baseline_metrics: Dict[str, Any]
) -> Dict[str, Any]:
    """Decide whether observed cache-priced cost is controlled for this pair."""

    result: Dict[str, Any] = {
        "status": "cache-not-comparable",
        "hit_rate_delta_points": None,
        "write_rate_delta_points": None,
        "reason": "cache telemetry is missing or invalid",
    }
    if (
        candidate_metrics.get("token_partition_valid") is not True
        or baseline_metrics.get("token_partition_valid") is not True
    ):
        return result

    hit_delta = _cache_rate_delta(
        candidate_metrics, baseline_metrics, "cached_input_tokens"
    )
    if hit_delta is None:
        return result
    result["hit_rate_delta_points"] = round(hit_delta * 100.0, 3)

    candidate_write = candidate_metrics.get("cache_write_input_tokens")
    baseline_write = baseline_metrics.get("cache_write_input_tokens")
    if (candidate_write is None) != (baseline_write is None):
        result["reason"] = "cache-write telemetry uses different observation coverage"
        return result
    write_delta = 0.0
    if candidate_write is not None:
        write_delta_value = _cache_rate_delta(
            candidate_metrics, baseline_metrics, "cache_write_input_tokens"
        )
        if write_delta_value is None:
            return result
        write_delta = write_delta_value
        result["write_rate_delta_points"] = round(write_delta * 100.0, 3)

    candidate_input = candidate_metrics["input_tokens"]
    baseline_input = baseline_metrics["input_tokens"]
    if candidate_input == baseline_input == 0:
        hit_within_bound = True
        write_within_bound = True
    else:
        # Compare the unrounded token ratios, not their presentation values.
        denominator = candidate_input * baseline_input
        hit_numerator = abs(
            candidate_metrics["cached_input_tokens"] * baseline_input
            - baseline_metrics["cached_input_tokens"] * candidate_input
        )
        hit_within_bound = (
            hit_numerator * 10_000
            <= CACHE_RATE_COMPARABLE_BASIS_POINTS * denominator
        )
        if candidate_write is None:
            write_within_bound = True
        else:
            write_numerator = abs(
                candidate_write * baseline_input - baseline_write * candidate_input
            )
            write_within_bound = (
                write_numerator * 10_000
                <= CACHE_RATE_COMPARABLE_BASIS_POINTS * denominator
            )
    if hit_within_bound and write_within_bound:
        result["status"] = "comparable"
        result["reason"] = "cache hit/write exposure differs by no more than 5 percentage points"
    else:
        result["reason"] = "cache hit/write exposure differs by more than 5 percentage points"
    return result


def _pair_delta(candidate: Dict[str, Any], baseline: Dict[str, Any]) -> Dict[str, Any]:
    if candidate["status"] != "eligible" or baseline["status"] != "eligible":
        return {
            "comparison_status": "inconclusive",
            "reason": "at least one arm has an infrastructure failure or missing/failed quality evidence",
            "wall_percent": None,
            "tool_call_delta": None,
            "process_step_delta": None,
            "input_percent": None,
            "cached_input_percent": None,
            "output_percent": None,
            "raw_percent": None,
            "normalized_cost_percent": None,
            "cache_neutral_cost_percent": None,
            "cache_comparison_status": "inconclusive",
            "cache_hit_rate_delta_points": None,
            "cache_write_rate_delta_points": None,
            "cost_gate_basis": None,
            "cost_gate_percent": None,
        }
    cm = candidate["metrics"]
    bm = baseline["metrics"]
    cache = _cache_comparison(cm, bm)
    observed_cost_percent = _percent(
        cm.get("normalized_cost_usd"), bm.get("normalized_cost_usd")
    )
    neutral_cost_percent = _percent(
        cm.get("cache_neutral_cost_usd"), bm.get("cache_neutral_cost_usd")
    )
    if cache["status"] == "comparable":
        cost_gate_basis = "observed_normalized_cost"
        cost_gate_percent = observed_cost_percent
    else:
        cost_gate_basis = "cache_neutral_cost"
        cost_gate_percent = neutral_cost_percent
    return {
        "comparison_status": "observed",
        "reason": (
            "same-task fixture metrics; one sample is directional; "
            f"{cache['reason']}"
        ),
        "wall_percent": _percent(candidate.get("wall_time_ms"), baseline.get("wall_time_ms")),
        "tool_call_delta": (
            cm.get("tool_calls") - bm.get("tool_calls")
            if cm.get("tool_calls") is not None and bm.get("tool_calls") is not None
            else None
        ),
        "process_step_delta": (
            cm.get("process_steps") - bm.get("process_steps")
            if cm.get("process_steps") is not None and bm.get("process_steps") is not None
            else None
        ),
        "input_percent": _percent(cm.get("input_tokens"), bm.get("input_tokens")),
        "cached_input_percent": _percent(cm.get("cached_input_tokens"), bm.get("cached_input_tokens")),
        "output_percent": _percent(cm.get("output_tokens"), bm.get("output_tokens")),
        "raw_percent": _percent(cm.get("raw_tokens"), bm.get("raw_tokens")),
        "normalized_cost_percent": observed_cost_percent,
        "cache_neutral_cost_percent": neutral_cost_percent,
        "cache_comparison_status": cache["status"],
        "cache_hit_rate_delta_points": cache["hit_rate_delta_points"],
        "cache_write_rate_delta_points": cache["write_rate_delta_points"],
        "cost_gate_basis": cost_gate_basis,
        "cost_gate_percent": cost_gate_percent,
    }


def _beta1_direct_behavior(beta1: Dict[str, Any]) -> Dict[str, Any]:
    route = beta1.get("route", {})
    metrics = beta1.get("metrics", {})
    conditions = {
        "selected_direct": route.get("selected") == "direct",
        "zero_child_starts": route.get("child_starts") == 0,
        "zero_unnecessary_state": route.get("unnecessary_state_writes") == 0,
        "zero_workflow_documents": route.get("workflow_documents_created") == 0,
        "zero_background_actions": route.get("background_actions") == 0,
        "zero_duplicate_verification": metrics.get("duplicate_verification_calls") == 0,
    }
    return {"passed": all(conditions.values()), "conditions": conditions}


def _release_gate(by_arm: Dict[str, Dict[str, Any]], comparisons: Dict[str, Dict[str, Any]], synthetic: bool) -> Dict[str, Any]:
    beta1 = by_arm.get("v060_beta1") or classify_cell(invalid_cell("v060_beta1", "0.6 arm missing"))
    all_eligible = all(by_arm.get(arm, {}).get("status") == "eligible" for arm in ARMS)
    direct_behavior = _beta1_direct_behavior(beta1)
    # comparisons are baseline-vs-Direct, so calculate Beta1-vs-Beta9 explicitly.
    beta9 = by_arm.get("v053_beta9") or classify_cell(invalid_cell("v053_beta9", "Beta9 arm missing"))
    beta1_vs_beta9 = _pair_delta(beta1, beta9)
    beta9_values = [
        beta1_vs_beta9.get("wall_percent"),
        beta1_vs_beta9.get("raw_percent"),
        beta1_vs_beta9.get("cost_gate_percent"),
    ]
    known_beta9_values = [value for value in beta9_values if value is not None]
    beta9_efficiency_passed = (
        beta1_vs_beta9.get("comparison_status") == "observed"
        and len(known_beta9_values) == 3
        and sum(value <= SINGLE_SAMPLE_EQUIVALENCE_PERCENT for value in known_beta9_values) >= 2
        and all(value <= 10 for value in known_beta9_values)
    )
    beta1_vs_direct = comparisons["v060_beta1"]
    direct_efficiency_passed = (
        beta1_vs_direct.get("comparison_status") == "observed"
        and beta1_vs_direct.get("wall_percent") is not None
        and beta1_vs_direct["wall_percent"] <= 15
        and beta1_vs_direct.get("cost_gate_percent") is not None
        and beta1_vs_direct["cost_gate_percent"] <= 15
        # Raw tokens remain visible evidence but are not an additional hidden
        # hard gate beyond the Spec's wall/cost Direct thresholds.
        and beta1_vs_direct.get("raw_percent") is not None
    )
    conditions = {
        "all_arms_quality_and_infrastructure_pass": all_eligible,
        "beta1_direct_behavior": direct_behavior["passed"],
        "beta1_vs_beta9_efficiency": beta9_efficiency_passed,
        "beta1_vs_direct_efficiency": direct_efficiency_passed,
        "non_synthetic_evidence": not synthetic,
    }
    return {
        "passed": all(conditions.values()),
        "conditions": conditions,
        "beta1_direct_behavior": direct_behavior,
        "beta1_vs_beta9": beta1_vs_beta9,
        "beta1_vs_direct": beta1_vs_direct,
        "note": "A one-task PASS is a prerelease smoke gate, not a general superiority claim.",
    }


def build_report(rows: Sequence[Dict[str, Any]], *, source: str, formal_model_calls: Optional[int] = None) -> Dict[str, Any]:
    by_arm = {row["arm"]: row for row in rows}
    direct = by_arm.get("direct") or classify_cell(invalid_cell("direct", "Direct arm missing"))
    comparisons = {
        arm: _pair_delta(by_arm.get(arm) or classify_cell(invalid_cell(arm, "arm missing")), direct)
        for arm in ("v053_beta9", "v060_beta1")
    }
    synthetic = any(bool(row.get("synthetic")) for row in rows)
    if formal_model_calls is None:
        formal_model_calls = 0 if synthetic else sum(
            int(item.get("attempts") or 0)
            for row in rows for item in (row.get("retained_history") or [])
        )
    gate = _release_gate(by_arm, comparisons, synthetic)
    quality_denominator = sum(
        1 for row in rows
        if row.get("status") in {"eligible", "quality_failure", "measurement_partial"}
        and row.get("quality_evidence_proven") is True
    )
    quality_numerator = sum(
        1 for row in rows
        if row.get("status") in {"eligible", "measurement_partial"}
        and row.get("quality_evidence_proven") is True
        and row.get("quality_passed") is True
    )
    return {
        "schema_version": 1,
        "experiment": "v060-beta1-three-arm-2026-09-04",
        "source": source,
        "evidence_grade": "offline-contract-fixture" if synthetic else "normalized-run-input",
        "formal_model_calls": formal_model_calls,
        "claim_boundary": "A single bounded comparison is directional; infrastructure failures are not product failures.",
        "release_eligible": gate["passed"],
        "release_smoke_gate": gate,
        "quality_completion": {
            "passed": quality_numerator,
            "eligible_completed": quality_denominator,
            "rate": round(quality_numerator / quality_denominator, 6) if quality_denominator else None,
        },
        "rows": list(rows),
        "comparisons_vs_direct": comparisons,
    }


def _display(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def render_report(report: Dict[str, Any]) -> str:
    lines = [
        "Experiment: v060-beta1-three-arm-2026-09-04",
        f"Evidence: {report['evidence_grade']} · formal model calls: {report['formal_model_calls']}",
        "Quality/infrastructure are separated; no infrastructure failure is a product-quality result.",
        "",
        "| Arm | Status | Complete | Quality | Wall ms | Tools | Steps | Input | Cached | Output | Raw | Norm. USD | Neutral USD |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in report["rows"]:
        metrics = row["metrics"]
        lines.append(
            "| {arm} | {status} | {complete} | {quality} | {wall} | {tools} | {steps} | {input} | {cached} | {output} | {raw} | {cost} | {neutral} |".format(
                arm=row["arm"],
                status=row["status"],
                complete=_display(row["completion_passed"]),
                quality=_display(row["quality_passed"]),
                wall=_display(row["wall_time_ms"]),
                tools=_display(metrics.get("tool_calls")),
                steps=_display(metrics.get("process_steps")),
                input=_display(metrics.get("input_tokens")),
                cached=_display(metrics.get("cached_input_tokens")),
                output=_display(metrics.get("output_tokens")),
                raw=_display(metrics.get("raw_tokens")),
                cost=_display(metrics.get("normalized_cost_usd")),
                neutral=_display(metrics.get("cache_neutral_cost_usd")),
            )
        )
    lines.append("")
    for arm, delta in report["comparisons_vs_direct"].items():
        lines.append(
            "{arm} vs Direct: {status}; wall={wall}%, raw={raw}%, observed normalized cost={cost}%, "
            "cache-neutral cost={neutral}%, gate cost={gate_cost}% ({basis}; {cache_status}), "
            "tools={tools}, steps={steps}. {reason}".format(
                arm=arm,
                status=delta["comparison_status"],
                wall=_display(delta["wall_percent"]),
                raw=_display(delta["raw_percent"]),
                cost=_display(delta["normalized_cost_percent"]),
                neutral=_display(delta["cache_neutral_cost_percent"]),
                gate_cost=_display(delta["cost_gate_percent"]),
                basis=_display(delta["cost_gate_basis"]),
                cache_status=_display(delta["cache_comparison_status"]),
                tools=_display(delta["tool_call_delta"]),
                steps=_display(delta["process_step_delta"]),
                reason=delta["reason"],
            )
        )
    lines.append(f"Release eligible: {report['release_eligible']} (offline fixture never authorizes publication).")
    return "\n".join(lines)


def _command(args: Sequence[str], *, cwd: Path, env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    completed = subprocess.run(
        list(args),
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    return {
        "command": list(args),
        "returncode": completed.returncode,
        "output_tail": "\n".join(completed.stdout.splitlines()[-12:]),
    }


def grade_repo(repo: Path, *, require_prepared: bool = False) -> Dict[str, Any]:
    """Run the one authoritative external fixture gate without a model call."""

    repo = repo.resolve()
    if not repo.is_dir():
        raise CellFormatError(f"fixture repository does not exist: {repo}")
    git_check = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=str(repo),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if git_check.returncode != 0:
        raise CellFormatError("result repository must be the prepared Git fixture with a baseline HEAD")
    if require_prepared:
        cell_root = repo.parent
        cells_root = cell_root.parent
        run_root = cells_root.parent
        if (
            cell_root.name not in ARMS
            or cells_root.name != "cells"
            or not (run_root / "run-lock.json").is_file()
        ):
            raise CellFormatError("--grade-repo accepts only a repository from --prepare-run")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repo)
    with tempfile.TemporaryDirectory(prefix="goldilocks-beta1-pycache-") as pycache:
        env["PYTHONPYCACHEPREFIX"] = pycache
        hidden = _command([sys.executable, str(HERE / "task" / "hidden" / "test_acceptance.py")], cwd=repo, env=env)
        hidden.update(
            {
                "kind": "hidden_acceptance",
                "grader_sha256": expected_protocol_hashes()["grader_sha256"],
                "passed": hidden["returncode"] == 0,
            }
        )
        checks = [
            _command([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=repo, env=env),
            hidden,
            _command([sys.executable, "-m", "compileall", "-q", "src", "tests"], cwd=repo, env=env),
        ]
    if (repo / ".git").exists():
        checks.append(_command(["git", "diff", "HEAD", "--check"], cwd=repo, env=env))
        tracked = subprocess.run(
            ["git", "diff", "HEAD", "--name-only"],
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        ).stdout.splitlines()
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(repo),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        ).stdout.splitlines()
        changed = sorted({path.strip() for path in tracked + untracked if path.strip()})
        allowed = {"src/tag_index.py", "tests/test_tag_index.py"}
        outside = [path for path in changed if path not in allowed]
        checks.append(
            {
                "command": ["scope-check", *sorted(allowed)],
                "returncode": 1 if outside else 0,
                "output_tail": "out-of-scope: " + ", ".join(outside) if outside else "",
            }
        )
    frozen_matches = (
        (repo / "README.md").is_file()
        and (repo / "README.md").read_bytes() == (HERE / "task" / "template" / "README.md").read_bytes()
    )
    checks.append(
        {
            "command": ["frozen-file-check", "README.md"],
            "returncode": 0 if frozen_matches else 1,
            "output_tail": "" if frozen_matches else "README.md changed or missing",
        }
    )
    return {"passed": all(check["returncode"] == 0 for check in checks), "checks": checks}


def _seed_repo(repo: Path) -> None:
    fixed_env = os.environ.copy()
    fixed_env.update(
        {
            "GIT_AUTHOR_DATE": "2026-09-04T00:00:00+00:00",
            "GIT_COMMITTER_DATE": "2026-09-04T00:00:00+00:00",
        }
    )
    for args in (
        ["git", "init", "-q"],
        ["git", "add", "-A"],
        ["git", "-c", "user.name=eval", "-c", "user.email=eval@invalid", "commit", "-qm", "seed"],
    ):
        result = subprocess.run(args, cwd=str(repo), env=fixed_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
        if result.returncode:
            raise CellFormatError(f"cannot seed fixture repo: {result.stdout[-400:]}")


def fixture_self_test() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="goldilocks-beta1-task-") as raw_dir:
        root = Path(raw_dir)
        bad_repo = root / "bad"
        shutil.copytree(HERE / "task" / "template", bad_repo)
        _seed_repo(bad_repo)
        bad = grade_repo(bad_repo)
        if bad["passed"]:
            raise AssertionError("broken template unexpectedly passed hidden acceptance")

        good_repo = root / "good"
        shutil.copytree(HERE / "task" / "template", good_repo)
        _seed_repo(good_repo)
        shutil.copy2(HERE / "task" / "oracle" / "src" / "tag_index.py", good_repo / "src" / "tag_index.py")
        good = grade_repo(good_repo)
        if not good["passed"]:
            raise AssertionError(f"oracle failed external acceptance: {good}")
    return {"broken_template_rejected": True, "oracle_passed": True}


def load_manifest() -> Dict[str, Any]:
    value = _load_json(MANIFEST)
    if tuple(value.get("execution_order") or ()) != ARMS:
        raise CellFormatError(f"manifest execution_order must be {list(ARMS)}")
    if value.get("automatic_host_retries") != 0:
        raise CellFormatError("automatic_host_retries must remain zero")
    if value.get("authorized_infrastructure_replacements_max") != 1:
        raise CellFormatError("exactly one authorized infrastructure replacement must be retained")
    runtime = _first_dict(value.get("runtime"))
    expected_runtime = {
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "requested_service_tier": "standard",
        "sandbox": "danger-full-access",
        "approval_policy": "never",
    }
    for key, expected in expected_runtime.items():
        if runtime.get(key) != expected:
            raise CellFormatError(f"manifest runtime.{key} must be {expected!r}")
    return value


def resolve_arm_source(manifest: Dict[str, Any], arm: str) -> Optional[Path]:
    raw = manifest["arms"][arm].get("source")
    return (HERE / str(raw)).resolve() if raw is not None else None


def marketplace_digest(source: Path) -> str:
    digest = hashlib.sha256()
    required = (
        source / ".agents" / "plugins" / "marketplace.json",
        source / ".claude-plugin" / "marketplace.json",
    )
    for path in required:
        digest.update(path.relative_to(source).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    plugin = source / "plugins" / "goldilocks"
    digest.update(sha256_tree(plugin).encode("ascii"))
    return digest.hexdigest()


def inspect_arm_source(manifest: Dict[str, Any], arm: str) -> Dict[str, Any]:
    definition = manifest["arms"][arm]
    source = resolve_arm_source(manifest, arm)
    if arm == "direct":
        return {
            "arm": arm,
            "passed": source is None,
            "source": None,
            "version": None,
            "source_sha256": None,
            "zero_hooks": True,
        }
    failures: List[str] = []
    if source is None or not source.is_dir():
        return {"arm": arm, "passed": False, "source": str(source), "failures": ["source missing"]}
    plugin_manifest = source / "plugins" / "goldilocks" / ".codex-plugin" / "plugin.json"
    marketplace = source / ".agents" / "plugins" / "marketplace.json"
    if not plugin_manifest.is_file():
        failures.append("Codex plugin manifest missing")
        version = None
    else:
        version = _load_json(plugin_manifest).get("version")
        version = str(version).split("+", 1)[0] if version is not None else None
        if version != definition.get("expected_version"):
            failures.append(f"expected version {definition.get('expected_version')}, got {version}")
    if not marketplace.is_file():
        failures.append("marketplace manifest missing")
    hooks = source / "plugins" / "goldilocks" / "hooks" / "hooks.json"
    if arm == "v060_beta1" and hooks.exists():
        failures.append("0.6 candidate still registers hooks")
    try:
        source_digest = marketplace_digest(source)
    except OSError as error:
        failures.append(f"source digest failed: {error}")
        source_digest = None
    return {
        "arm": arm,
        "passed": not failures,
        "source": str(source),
        "version": version,
        "source_sha256": source_digest,
        "zero_hooks": not hooks.exists(),
        "failures": failures,
    }


def preflight() -> Dict[str, Any]:
    manifest = load_manifest()
    sources = [inspect_arm_source(manifest, arm) for arm in ARMS]
    task = fixture_self_test()
    return {
        "passed": all(source["passed"] for source in sources) and all(task.values()),
        "formal_model_calls": 0,
        "host_credentials_read": False,
        "runtime": manifest["runtime"],
        "protocol_hashes": expected_protocol_hashes(),
        "manifest_sha256": sha256_file(MANIFEST),
        "sources": sources,
        "task_fixture": task,
    }


def _copy_marketplace(source: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    shutil.copytree(source / ".agents", destination / ".agents")
    shutil.copytree(source / ".claude-plugin", destination / ".claude-plugin")
    shutil.copytree(
        source / "plugins" / "goldilocks",
        destination / "plugins" / "goldilocks",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
    )


def prepare_run(run_dir: Path) -> Dict[str, Any]:
    """Freeze sources and identical task repos without contacting a model."""

    check = preflight()
    if not check["passed"]:
        raise CellFormatError(f"preflight failed: {check}")
    run_dir = run_dir.resolve()
    if run_dir.exists():
        raise CellFormatError(f"refusing to overwrite existing run directory: {run_dir}")
    run_dir.mkdir(parents=True)
    manifest = load_manifest()
    frozen_sources: Dict[str, Any] = {}
    for source_row in check["sources"]:
        arm = source_row["arm"]
        source = resolve_arm_source(manifest, arm)
        if source is None:
            frozen_sources[arm] = {"source": None, "source_sha256": None, "version": None}
            continue
        destination = run_dir / "frozen-sources" / arm
        _copy_marketplace(source, destination)
        frozen_sources[arm] = {
            "source": str(destination),
            "source_sha256": marketplace_digest(destination),
            "version": source_row["version"],
        }
        if frozen_sources[arm]["source_sha256"] != source_row["source_sha256"]:
            raise CellFormatError(f"{arm} changed while its source snapshot was being frozen")
    cell_roots: Dict[str, Any] = {}
    for arm in ARMS:
        cell = run_dir / "cells" / arm
        repo = cell / "repo"
        shutil.copytree(HERE / "task" / "template", repo)
        _seed_repo(repo)
        shutil.copy2(HERE / "task" / "TASK.md", cell / "TASK.md")
        for name in ("home", "codex_home", "audit", "events", "pycache", "results"):
            (cell / name).mkdir(parents=True)
        cell_roots[arm] = {
            "repo": str(repo),
            "home": str(cell / "home"),
            "codex_home": str(cell / "codex_home"),
            "audit": str(cell / "audit"),
            "events": str(cell / "events"),
            "pycache": str(cell / "pycache"),
            "results": str(cell / "results"),
        }
    lock = {
        "experiment": manifest["experiment"],
        "formal_model_calls_planned": 3,
        "automatic_host_retries": 0,
        "authorized_infrastructure_replacements_max": 1,
        "execution_order": list(ARMS),
        "runtime": manifest["runtime"],
        "manifest_sha256": sha256_file(MANIFEST),
        "protocol_hashes": expected_protocol_hashes(),
        "frozen_sources": frozen_sources,
        "cell_roots": cell_roots,
        "control_fingerprint": {
            "same_host": True,
            "same_toolset": True,
            "cold_context": True,
            "sandbox": "danger-full-access",
            "approval_policy": "never",
            "auth_files": "not copied by offline harness",
            "automatic_host_retries": 0,
        },
    }
    (run_dir / "run-lock.json").write_text(json.dumps(lock, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"passed": True, "formal_model_calls": 0, "run_dir": str(run_dir), "lock": lock}


def direct_semantic_evidence(inventory: Any, codex_home: Path, prompt_text: str) -> Dict[str, Any]:
    """Shared Direct evidence rule: workflow identities, never incidental paths."""

    installed = inventory.get("installed")
    if not isinstance(installed, list):
        raise CellFormatError("Direct plugin-list.json must have an installed list at its root")
    goldilocks_ids: List[str] = []
    for item in installed:
        if not isinstance(item, dict):
            raise CellFormatError("Direct plugin-list installed entries must be objects")
        plugin_id = str(item.get("pluginId") or "")
        name = str(item.get("name") or "")
        if plugin_id == "goldilocks@goldilocks-local" or name == "goldilocks":
            goldilocks_ids.append(plugin_id or name)

    skills = codex_home / "skills"
    # Codex injects the host-owned `.system` bundle into an otherwise fresh
    # home; it is not a portable workflow Skill.
    skills_entries = sorted(path.name for path in skills.iterdir() if path.name != ".system") if skills.is_dir() else []
    marketplace_entries: List[str] = []
    for relative in (Path("marketplaces"), Path("plugins") / "marketplaces"):
        root = codex_home / relative
        if root.is_dir():
            marketplace_entries.extend(
                f"{relative.as_posix()}/{path.name}" for path in root.iterdir()
            )
    config = codex_home / "config.toml"
    config_text = config.read_text(encoding="utf-8", errors="replace") if config.is_file() else ""
    compact_present = bool(
        re.search(
            r"(?m)^\s*(?:compact_prompt|experimental_compact_prompt_file)\s*=",
            config_text,
        )
    )
    parsed_prompt = None
    try:
        parsed_prompt = json.loads(prompt_text)
    except json.JSONDecodeError:
        pass
    prompt_parts = []
    if isinstance(parsed_prompt, list):
        for message in parsed_prompt:
            if not isinstance(message, dict):
                continue
            for content in message.get("content", []):
                if isinstance(content, dict) and isinstance(content.get("text"), str):
                    prompt_parts.append(content["text"])
    semantic_prompt = "\n".join(prompt_parts)
    return {
        "plugin_list_root_key": "installed",
        "goldilocks_plugin_ids": sorted(goldilocks_ids),
        "isolated_skills_entries": skills_entries,
        "isolated_marketplace_entries": sorted(marketplace_entries),
        "compact_prompt_present": compact_present,
        "prompt_input_goldilocks_mentions": len(re.findall(r"(?im)(?:^|\n)\s*(?:\$goldilocks|<goldilocks|use\s+goldilocks\b|load\s+goldilocks\b)", semantic_prompt)),
    }


def _direct_filesystem_evidence(run_dir: Path) -> Dict[str, Any]:
    """Derive Direct purity from retained redacted files, never prompt text."""

    direct_root = run_dir / "cells" / "direct"
    codex_home = direct_root / "codex_home"
    audit = direct_root / "audit"
    inventory = _load_json(audit / "plugin-list.json")
    prompt_structure_path = audit / "prompt-structure.json"
    if not prompt_structure_path.is_file():
        raise CellFormatError("Direct redacted prompt structure evidence is missing")
    prompt_structure = _load_json(prompt_structure_path)
    if prompt_structure.get("available") is not True:
        raise CellFormatError("Direct redacted prompt structure is unavailable")
    total_chars = prompt_structure.get("total_text_chars")
    text_sha256 = prompt_structure.get("text_sha256")
    if (
        isinstance(total_chars, bool)
        or not isinstance(total_chars, int)
        or total_chars <= 0
        or not isinstance(text_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", text_sha256) is None
    ):
        raise CellFormatError("Direct redacted prompt structure is malformed")
    clean_markers = {
        "goldilocks_catalog_description_present": False,
        "goldilocks_catalog_description_count": 0,
        "main_skill_body_marker_present": False,
        "main_skill_body_marker_count": 0,
    }
    for key, expected in clean_markers.items():
        if prompt_structure.get(key) != expected:
            raise CellFormatError(f"Direct prompt structure is contaminated: {key}")

    # The execution runner computed semantic activation mentions from the raw
    # prompt before discarding it.  Retain only the zero-valued result while
    # independently binding the redacted shape, plugin list, and isolated home.
    evidence = direct_semantic_evidence(inventory, codex_home, "[]")
    evidence["prompt_structure"] = prompt_structure
    return evidence


def validate_formal_run(input_dir: Path, rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Bind imported evidence to one prepared run-lock and its isolated roots."""

    input_dir = input_dir.resolve()
    run_dir = input_dir.parent if input_dir.name == "cells" else input_dir
    cells_dir = run_dir / "cells"
    if input_dir != cells_dir.resolve():
        raise CellFormatError("formal --input-dir must be the prepared run's cells/ directory")
    lock_path = run_dir / "run-lock.json"
    lock = _load_json(lock_path)
    manifest = load_manifest()
    required = {
        "experiment": manifest["experiment"],
        "formal_model_calls_planned": 3,
        "automatic_host_retries": 0,
        "execution_order": list(ARMS),
        "manifest_sha256": sha256_file(MANIFEST),
        "protocol_hashes": expected_protocol_hashes(),
    }
    for key, expected in required.items():
        if lock.get(key) != expected:
            raise CellFormatError(f"run-lock {key} does not match the frozen experiment")
    if lock.get("runtime") != manifest.get("runtime"):
        raise CellFormatError("run-lock runtime does not match the frozen manifest")
    locked_roots = _first_dict(lock.get("cell_roots"))
    locked_sources = _first_dict(lock.get("frozen_sources"))
    by_arm = {row["arm"]: row for row in rows}
    for arm in ARMS:
        arm_root = cells_dir / arm
        roots = _first_dict(locked_roots.get(arm))
        for name in ("repo", "home", "codex_home", "audit", "events", "results"):
            expected_path = (arm_root / name).resolve()
            observed = roots.get(name)
            if not observed or Path(str(observed)).resolve() != expected_path:
                raise CellFormatError(f"run-lock cell root mismatch for {arm}.{name}")
        source = _first_dict(locked_sources.get(arm))
        protocol = by_arm[arm].get("protocol", {})
        if arm == "direct":
            if source.get("source") is not None or source.get("source_sha256") is not None:
                raise CellFormatError("Direct run-lock unexpectedly carries a plugin source")
        else:
            frozen = Path(str(source.get("source") or "")).resolve()
            if not frozen.is_dir() or marketplace_digest(frozen) != source.get("source_sha256"):
                raise CellFormatError(f"frozen source digest mismatch for {arm}")
            if protocol.get("source_sha256") != source.get("source_sha256"):
                _invalidate_row_protocol(by_arm[arm], "cell source digest does not match run-lock")

    direct_evidence = _direct_filesystem_evidence(run_dir)
    direct = by_arm["direct"]
    for key, observed in direct_evidence.items():
        if direct.get("protocol", {}).get(key) != observed:
            _invalidate_row_protocol(direct, f"Direct retained evidence contradicts {key}")
    return {"run_dir": str(run_dir), "run_lock": str(lock_path), "direct_evidence": direct_evidence}


def self_test() -> Dict[str, Any]:
    """Run all checks without a model call and return a machine-readable result."""

    rows = load_cells(FIXTURES)
    assert [row["arm"] for row in rows] == list(ARMS)
    assert all(row["status"] == "eligible" for row in rows), rows
    report = build_report(rows, source="bundled synthetic fixtures", formal_model_calls=0)
    assert report["evidence_grade"] == "offline-contract-fixture"
    assert report["release_eligible"] is False
    assert report["comparisons_vs_direct"]["v060_beta1"]["comparison_status"] == "observed"

    # A cost comparison only uses observed cache pricing when cache exposure is
    # close enough to be a controlled input.  Otherwise the observed cost stays
    # reportable while the gate uses a cache-neutral cost basis.
    comparable = _pair_delta(
        {
            "status": "eligible",
            "wall_time_ms": 103,
            "metrics": {
                "input_tokens": 10_000,
                "cached_input_tokens": 6_400,
                "cache_write_input_tokens": None,
                "token_partition_valid": True,
                "normalized_cost_usd": 1.03,
                "cache_neutral_cost_usd": 1.05,
            },
        },
        {
            "status": "eligible",
            "wall_time_ms": 100,
            "metrics": {
                "input_tokens": 10_000,
                "cached_input_tokens": 5_900,
                "cache_write_input_tokens": None,
                "token_partition_valid": True,
                "normalized_cost_usd": 1.0,
                "cache_neutral_cost_usd": 1.0,
            },
        },
    )
    assert comparable["cache_comparison_status"] == "comparable"
    assert comparable["cost_gate_basis"] == "observed_normalized_cost"
    assert comparable["cost_gate_percent"] == 3.0
    cache_skewed = _pair_delta(
        {
            "status": "eligible",
            "wall_time_ms": 103,
            "metrics": {
                "input_tokens": 10_000,
                "cached_input_tokens": 6_400,
                "cache_write_input_tokens": None,
                "token_partition_valid": True,
                "normalized_cost_usd": 1.30,
                "cache_neutral_cost_usd": 1.05,
            },
        },
        {
            "status": "eligible",
            "wall_time_ms": 100,
            "metrics": {
                "input_tokens": 10_000,
                "cached_input_tokens": 8_400,
                "cache_write_input_tokens": None,
                "token_partition_valid": True,
                "normalized_cost_usd": 1.0,
                "cache_neutral_cost_usd": 1.0,
            },
        },
    )
    assert cache_skewed["cache_comparison_status"] == "cache-not-comparable"
    assert cache_skewed["normalized_cost_percent"] == 30.0
    assert cache_skewed["cost_gate_basis"] == "cache_neutral_cost"
    assert cache_skewed["cost_gate_percent"] == 5.0
    just_over_cache_bound = _pair_delta(
        {
            "status": "eligible",
            "wall_time_ms": 100,
            "metrics": {
                "input_tokens": 10_000,
                "cached_input_tokens": 6_401,
                "cache_write_input_tokens": None,
                "token_partition_valid": True,
                "normalized_cost_usd": 1.0,
                "cache_neutral_cost_usd": 1.0,
            },
        },
        {
            "status": "eligible",
            "wall_time_ms": 100,
            "metrics": {
                "input_tokens": 10_000,
                "cached_input_tokens": 5_900,
                "cache_write_input_tokens": None,
                "token_partition_valid": True,
                "normalized_cost_usd": 1.0,
                "cache_neutral_cost_usd": 1.0,
            },
        },
    )
    assert just_over_cache_bound["cache_comparison_status"] == "cache-not-comparable"
    assert _cache_comparison(
        {
            "input_tokens": 100,
            "cached_input_tokens": 60,
            "cache_write_input_tokens": 0,
            "token_partition_valid": True,
        },
        {
            "input_tokens": 100,
            "cached_input_tokens": 60,
            "cache_write_input_tokens": None,
            "token_partition_valid": True,
        },
    )["status"] == "cache-not-comparable"
    assert _cache_comparison(
        {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": None,
            "token_partition_valid": True,
        },
        {
            "input_tokens": 0,
            "cached_input_tokens": 0,
            "cache_write_input_tokens": None,
            "token_partition_valid": True,
        },
    )["status"] == "comparable"
    assert _percent(0, 0) == 0.0
    assert _percent(1, 0) is None

    # In a one-sample smoke comparison, <=3% is an equivalence band rather
    # than evidence of a real regression.  Raw tokens versus Direct remain a
    # reported diagnostic and do not silently become a stricter hard gate.
    def eligible_gate_row(
        arm: str,
        *,
        wall: int,
        raw: int,
        observed_cost: float,
        neutral_cost: float,
        cache_hit_rate: float,
    ) -> Dict[str, Any]:
        return {
            "arm": arm,
            "status": "eligible",
            "wall_time_ms": wall,
            "metrics": {
                "raw_tokens": raw,
                "input_tokens": 100,
                "cached_input_tokens": round(cache_hit_rate * 100),
                "cache_write_input_tokens": None,
                "token_partition_valid": True,
                "normalized_cost_usd": observed_cost,
                "cache_neutral_cost_usd": neutral_cost,
                "duplicate_verification_calls": 0,
            },
            "route": {
                "selected": "direct",
                "child_starts": 0,
                "unnecessary_state_writes": 0,
                "workflow_documents_created": 0,
                "background_actions": 0,
            },
        }

    beta9_gate_row = eligible_gate_row(
        "v053_beta9", wall=100, raw=100, observed_cost=1.0, neutral_cost=1.0, cache_hit_rate=0.60
    )
    beta1_gate_row = eligible_gate_row(
        "v060_beta1", wall=108, raw=103, observed_cost=1.03, neutral_cost=1.10, cache_hit_rate=0.61
    )
    direct_gate_row = eligible_gate_row(
        "direct", wall=100, raw=90, observed_cost=0.80, neutral_cost=1.0, cache_hit_rate=0.85
    )
    gate_rows = {
        row["arm"]: row for row in (beta9_gate_row, beta1_gate_row, direct_gate_row)
    }
    gate_comparisons = {
        arm: _pair_delta(gate_rows[arm], direct_gate_row)
        for arm in ("v053_beta9", "v060_beta1")
    }
    boundary_gate = _release_gate(gate_rows, gate_comparisons, synthetic=False)
    assert boundary_gate["conditions"]["beta1_vs_beta9_efficiency"] is True
    assert boundary_gate["conditions"]["beta1_vs_direct_efficiency"] is True
    assert boundary_gate["beta1_vs_direct"]["raw_percent"] > 0
    beta1_gate_row["wall_time_ms"] = 111
    above_regression_cap = _release_gate(
        gate_rows,
        {
            arm: _pair_delta(gate_rows[arm], direct_gate_row)
            for arm in ("v053_beta9", "v060_beta1")
        },
        synthetic=False,
    )
    assert above_regression_cap["conditions"]["beta1_vs_beta9_efficiency"] is False
    fixture_status = fixture_self_test()

    with tempfile.TemporaryDirectory(prefix="goldilocks-beta1-eval-") as raw_dir:
        root = Path(raw_dir)
        retained_run = root / "retained-run"
        retained_audit = retained_run / "cells" / "direct" / "audit"
        retained_home = retained_run / "cells" / "direct" / "codex_home"
        retained_audit.mkdir(parents=True)
        retained_home.mkdir(parents=True)
        (retained_audit / "plugin-list.json").write_text(
            json.dumps({"installed": []}), encoding="utf-8"
        )
        clean_prompt_structure = {
            "available": True,
            "total_text_chars": 100,
            "text_sha256": "a" * 64,
            "goldilocks_catalog_description_present": False,
            "goldilocks_catalog_description_count": 0,
            "main_skill_body_marker_present": False,
            "main_skill_body_marker_count": 0,
        }
        (retained_audit / "prompt-structure.json").write_text(
            json.dumps(clean_prompt_structure), encoding="utf-8"
        )
        retained = _direct_filesystem_evidence(retained_run)
        assert retained["prompt_input_goldilocks_mentions"] == 0
        assert retained["prompt_structure"] == clean_prompt_structure

        def retained_prompt_rejected(update: Dict[str, Any]) -> bool:
            candidate = {**clean_prompt_structure, **update}
            (retained_audit / "prompt-structure.json").write_text(
                json.dumps(candidate), encoding="utf-8"
            )
            try:
                _direct_filesystem_evidence(retained_run)
            except CellFormatError:
                return True
            return False

        assert retained_prompt_rejected({"available": False})
        assert retained_prompt_rejected(
            {
                "goldilocks_catalog_description_present": True,
                "goldilocks_catalog_description_count": 1,
            }
        )
        assert retained_prompt_rejected(
            {"main_skill_body_marker_present": True, "main_skill_body_marker_count": 1}
        )
        (retained_audit / "prompt-structure.json").unlink()
        try:
            _direct_filesystem_evidence(retained_run)
        except CellFormatError:
            pass
        else:
            raise AssertionError("missing Direct prompt structure must fail closed")

        missing = {
            "arm": "direct",
            "version": None,
            "runtime": {"model": "gpt-5.6-sol", "effort": "high", "service_tier": "standard"},
            "attempts": 1,
            "host_retries": 0,
            "returncode": 0,
            "completion": {"turn_completed": True},
            "quality": {"passed": True},
            "telemetry": {"tool_calls": 1},
            "protocol": {
                "source_frozen": True,
                "prompt_sha256": expected_protocol_hashes()["prompt_sha256"],
                "fixture_sha256": expected_protocol_hashes()["fixture_sha256"],
                "grader_sha256": expected_protocol_hashes()["grader_sha256"],
                "runtime_identity_verified": True,
                "root_session_count": 1,
                "child_session_count": 0,
                "usage_deduplicated": True,
                "same_host": True,
                "same_toolset": True,
                "cold_context": True,
                "approval_policy": "never",
                "sandbox": "danger-full-access",
                "full_access": True,
                "direct_pure": True,
                "plugin_identity_verified": False,
                "plugin_list_root_key": "installed",
                "goldilocks_plugin_ids": [],
                "isolated_skills_entries": [],
                "isolated_marketplace_entries": [],
                "compact_prompt_present": False,
                "prompt_input_goldilocks_mentions": 0,
            },
            "synthetic": False,
        }
        (root / "cell.json").write_text(json.dumps(missing), encoding="utf-8")
        missing_cell = load_cell(root, arm_hint="direct")
        missing_row = classify_cell(missing_cell)
        assert missing_row["status"] == "evidence_gap"
        assert missing_row["metrics"]["input_tokens"] is None
        assert missing_row["metrics"]["raw_tokens"] is None

        failed = dict(missing)
        failed["completion"] = {"turn_completed": False}
        failed["failure_class"] = "infrastructure_invalid"
        failed["infrastructure_reason"] = "timeout"
        failed["errors"] = ["provider timeout"]
        (root / "cell.json").write_text(json.dumps(failed), encoding="utf-8")
        failed_row = classify_cell(load_cell(root, arm_hint="direct"))
        assert failed_row["status"] == "infrastructure_failure"
        assert failed_row["quality_passed"] is None
        assert failed_row["observed"]["quality_passed"] is True
        assert "provider timeout" in failed_row["errors"]

        events = root / "events.jsonl"
        events.write_text(
            "\n".join(
                [
                    json.dumps({"type": "session_meta", "payload": {"arm": "direct", "id": "s1"}}),
                    json.dumps({"type": "turn_context", "payload": {"model": "gpt-5.6-sol", "effort": "high", "service_tier": "standard"}}),
                    json.dumps({"type": "metadata", "payload": {"attempts": 1, "host_retries": 0, "returncode": 0, "wall_time_ms": 10, "protocol": {"source_frozen": True, "prompt_sha256": expected_protocol_hashes()["prompt_sha256"], "fixture_sha256": expected_protocol_hashes()["fixture_sha256"], "grader_sha256": expected_protocol_hashes()["grader_sha256"], "runtime_identity_verified": True, "root_session_count": 1, "full_access": True, "direct_pure": True, "plugin_identity_verified": False}}}),
                    json.dumps({"type": "response_item", "payload": {"type": "function_call", "name": "shell", "arguments": "python3 -m pytest"}}),
                    json.dumps({"type": "event_msg", "payload": {"info": {"total_token_usage": {"input_tokens": 10, "cached_input_tokens": 4, "output_tokens": 2}}}}),
                    json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}),
                    json.dumps({"type": "quality", "payload": {"passed": True}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        parsed = normalize_cell(parse_events(events), source=events, arm_hint="direct")
        assert parsed["telemetry"]["tool_calls"] == 1
        assert parsed["telemetry"]["verification_calls"] == 1
        assert parsed["telemetry"]["duplicate_verification_calls"] == 0
        assert parsed["telemetry"]["raw_tokens"] == 12

        # Real ``codex exec --json`` records wrap completed work in ``item``
        # and put terminal usage at the top level.  Started records and an
        # exact repeated completion must not double count.
        events.write_text(
            "\n".join(
                [
                    json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                    json.dumps({"type": "item.started", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m pytest"}}),
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m pytest", "status": "completed", "exit_code": 0}}),
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m pytest", "status": "completed", "exit_code": 0}}),
                    json.dumps({"type": "item.completed", "item": {"id": "edit-1", "type": "file_change", "changes": [{"path": "src/tag_index.py", "kind": "update"}]}}),
                    json.dumps({"type": "item.completed", "item": {"id": "agent-1", "type": "collab_tool_call", "tool_name": "spawn_agent", "arguments": {"task": "review"}}}),
                    json.dumps({"type": "item.completed", "item": {"id": "msg-1", "type": "agent_message", "text": "done"}}),
                    json.dumps({"type": "turn.completed", "usage": {"input_tokens": 20, "cached_input_tokens": 8, "cache_write_input_tokens": 0, "output_tokens": 3, "reasoning_output_tokens": 1}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        real_cli = parse_events(events, arm="direct")
        assert real_cli["completion"]["turn_completed"] is True
        assert real_cli["telemetry"]["tool_calls"] == 3
        assert real_cli["telemetry"]["verification_calls"] == 1
        assert real_cli["telemetry"]["input_tokens"] == 20
        assert real_cli["telemetry"]["output_tokens"] == 3
        assert real_cli["protocol"]["root_session_count"] == 1
        assert real_cli["protocol"].get("valid") is not False

        # A missing interpreter/runner never entered product verification.
        # Its successful same-generation fallback is visible as recovery, not
        # penalized as unnecessary duplicate verification.
        events.write_text(
            "\n".join(
                [
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python -m unittest tests/test_tag_index.py", "status": "failed", "exit_code": 127}}),
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-2", "type": "command_execution", "command": "python3 -m unittest tests/test_tag_index.py", "status": "completed", "exit_code": 0}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        recovered = parse_events(events, arm="direct")
        assert recovered["telemetry"]["verification_calls"] == 2
        assert recovered["telemetry"]["verification_recovery_calls"] == 1
        assert recovered["telemetry"]["duplicate_verification_calls"] == 0

        def recovery_counts(exit_codes: Sequence[int], *, compound: bool = False) -> Tuple[int, int]:
            records = []
            for index, exit_code in enumerate(exit_codes):
                command = "python3 -m unittest tests/test_tag_index.py"
                if index == 0:
                    command = "python -m unittest tests/test_tag_index.py"
                if compound:
                    command += " && git status --short"
                records.append(
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {
                                "id": f"cmd-{index}",
                                "type": "command_execution",
                                "command": command,
                                "status": "completed" if exit_code == 0 else "failed",
                                "exit_code": exit_code,
                            },
                        }
                    )
                )
            events.write_text("\n".join(records) + "\n", encoding="utf-8")
            parsed_counts = parse_events(events, arm="direct")["telemetry"]
            return (
                parsed_counts["verification_recovery_calls"],
                parsed_counts["duplicate_verification_calls"],
            )

        assert recovery_counts([126, 0]) == (1, 0)
        assert recovery_counts([0, 127, 0]) == (1, 1)
        assert recovery_counts([127, 127, 0]) == (1, 1)
        assert recovery_counts([127, 0], compound=True) == (0, 2)

        # Once a verification actually ran, another same-generation call is a
        # duplicate even when the first result failed.  A product edit starts a
        # new generation and makes the targeted rerun legitimate.
        events.write_text(
            "\n".join(
                [
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m unittest tests/test_tag_index.py", "status": "failed", "exit_code": 1}}),
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-2", "type": "command_execution", "command": "python3 -m unittest tests/test_tag_index.py", "status": "completed", "exit_code": 0}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        repeated = parse_events(events, arm="direct")
        assert repeated["telemetry"]["verification_recovery_calls"] == 0
        assert repeated["telemetry"]["duplicate_verification_calls"] == 1
        events.write_text(
            "\n".join(
                [
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m unittest tests/test_tag_index.py", "status": "failed", "exit_code": 1}}),
                    json.dumps({"type": "item.completed", "item": {"id": "edit-1", "type": "file_change", "changes": [{"path": "src/tag_index.py", "kind": "update"}]}}),
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-2", "type": "command_execution", "command": "python3 -m unittest tests/test_tag_index.py", "status": "completed", "exit_code": 0}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        post_edit = parse_events(events, arm="direct")
        assert post_edit["telemetry"]["verification_recovery_calls"] == 0
        assert post_edit["telemetry"]["duplicate_verification_calls"] == 0

        # Contradictory roots, duplicate completed payloads, and terminal
        # usage are retained as protocol/contamination evidence.  The first
        # completed item and usage snapshot remain canonical rather than being
        # silently overwritten by the later record.
        events.write_text(
            "\n".join(
                [
                    json.dumps({"type": "thread.started", "thread_id": "thread-1"}),
                    json.dumps({"type": "thread.started", "thread_id": "thread-2"}),
                    json.dumps({"type": "session_meta", "payload": {"session_id": "session-1"}}),
                    json.dumps({"type": "session_meta", "payload": {"session_id": "session-2"}}),
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m pytest"}}),
                    json.dumps({"type": "item.completed", "item": {"id": "cmd-1", "type": "command_execution", "command": "python3 -m unittest"}}),
                    json.dumps({"type": "turn.completed", "usage": {"input_tokens": 20, "cached_input_tokens": 8, "cache_write_input_tokens": 0, "output_tokens": 3}}),
                    json.dumps({"type": "turn.completed", "usage": {"input_tokens": 21, "cached_input_tokens": 8, "cache_write_input_tokens": 0, "output_tokens": 3}}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        conflicted = parse_events(events, arm="direct")
        assert conflicted["telemetry"]["tool_calls"] == 1
        assert conflicted["telemetry"]["input_tokens"] == 20
        assert conflicted["protocol"]["root_session_count"] == 2
        assert conflicted["protocol"]["valid"] is False
        assert any("multiple root" in item for item in conflicted["protocol"]["violations"])
        assert any("conflicting turn.completed usage" in item for item in conflicted["measurement"]["contamination"])

    return {
        "passed": True,
        "formal_model_calls": 0,
        "arms": list(ARMS),
        "fixture_rows": len(rows),
        "release_eligible": False,
        "task_fixture": fixture_status,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run offline parser/contract checks")
    parser.add_argument("--preflight", action="store_true", help="verify frozen sources and task locally")
    parser.add_argument(
        "--prepare-run",
        type=Path,
        metavar="PATH",
        help="create isolated frozen cell roots without starting a model",
    )
    parser.add_argument("--report", action="store_true", help="render the bundled synthetic report")
    parser.add_argument("--input-dir", type=Path, help="directory containing v053_beta9/, v060_beta1/, direct/")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of the human report")
    parser.add_argument("--output", type=Path, help="optional JSON report destination")
    parser.add_argument("--formal-model-calls", type=int, help="override retained cell count when importing a run")
    parser.add_argument("--grade-repo", type=Path, help="run the local external quality gate for one result repo")
    parser.add_argument("--execute", action="store_true", help="rejected: this harness never starts model calls")
    args = parser.parse_args(argv)

    if args.execute:
        parser.error("offline harness refuses --execute; use a separately authorized runner to produce normalized cells")
    if args.formal_model_calls is not None and args.formal_model_calls < 0:
        parser.error("--formal-model-calls must be non-negative")
    if args.self_test:
        result = self_test()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.preflight:
        result = preflight()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1

    if args.prepare_run:
        result = prepare_run(args.prepare_run)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    if args.grade_repo:
        result = grade_repo(args.grade_repo, require_prepared=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result["passed"] else 1

    input_dir = args.input_dir or FIXTURES
    if not args.report and args.input_dir is None:
        parser.error("choose --self-test, --preflight, --prepare-run, --grade-repo, --report, or --input-dir")
    rows = load_cells(input_dir)
    formal_validation = None
    is_fixture_report = input_dir.resolve() == FIXTURES.resolve()
    if not is_fixture_report:
        try:
            formal_validation = validate_formal_run(input_dir, rows)
        except CellFormatError as error:
            parser.error(str(error))
    derived_model_calls = 0 if is_fixture_report else sum(
        int(item.get("attempts") or 0)
        for row in rows for item in (row.get("retained_history") or [])
    )
    if args.formal_model_calls is not None and args.formal_model_calls != derived_model_calls:
        parser.error(
            "--formal-model-calls must equal retained actual model attempts "
            f"({derived_model_calls})"
        )
    report = build_report(
        rows,
        source=str(input_dir),
        formal_model_calls=derived_model_calls,
    )
    if formal_validation is not None:
        report["formal_validation"] = formal_validation
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else render_report(report))
    return 0 if is_fixture_report or report["release_eligible"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
