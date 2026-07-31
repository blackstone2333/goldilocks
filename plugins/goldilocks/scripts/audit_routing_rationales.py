#!/usr/bin/env python3

"""Audit the local routing-rationale experiment without reading prompt content."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Iterable


DEFAULT_EXPERIMENT = "routing-rationale-v2"
ROUTE_LINE = re.compile(
    r"^ROUTE=(direct|fast|standard|mixed)\s*\|\s*"
    r"WRITE_READY=(\d+)\s*\|\s*READ_READY=(\d+)\s*\|\s*"
    r"LEAD=(.*?)\s*\|\s*REASON=([a-z_]+)\s*\|\s*DETAIL=(.+?)\s*$",
    re.MULTILINE,
)
ANY_ROUTE_LINE = re.compile(r"^ROUTE=(?:direct|fast|standard|mixed)\b.*$", re.MULTILINE)


def default_database() -> Path:
    configured = os.environ.get("PLUGIN_DATA")
    if configured:
        return Path(configured).expanduser() / "orchestration.db"
    return (
        Path.home()
        / ".codex"
        / "plugins"
        / "data"
        / "goldilocks-goldilocks-local"
        / "orchestration.db"
    )


def default_log_roots() -> list[Path]:
    return [Path.home() / ".codex" / "sessions", Path.home() / ".codex" / "archived_sessions"]


def load_candidates(database: Path, experiment: str) -> dict[str, str]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT session_id, turn_id FROM gate_injections "
            "WHERE routing_rationale_candidate = 1 AND routing_experiment_id = ?",
            (experiment,),
        ).fetchall()
    return {str(turn_id): str(session_id) for session_id, turn_id in rows}


def matching_logs(roots: Iterable[Path], session_ids: set[str]) -> Iterable[Path]:
    seen: set[Path] = set()
    for root in roots:
        if root.is_file():
            paths = [root]
        elif root.is_dir():
            paths = root.rglob("*.jsonl")
        else:
            continue
        for path in paths:
            if path in seen or not any(session_id in path.name for session_id in session_ids):
                continue
            seen.add(path)
            yield path


def assistant_text(record: dict[str, object]) -> tuple[str | None, str]:
    if record.get("type") != "response_item":
        return None, ""
    payload = record.get("payload")
    if not isinstance(payload, dict) or payload.get("type") != "message":
        return None, ""
    if payload.get("role") != "assistant":
        return None, ""
    metadata = payload.get("internal_chat_message_metadata_passthrough")
    turn_id = metadata.get("turn_id") if isinstance(metadata, dict) else None
    content = payload.get("content")
    if not isinstance(content, list):
        return str(turn_id) if turn_id else None, ""
    text = "\n".join(
        str(item.get("text") or "")
        for item in content
        if isinstance(item, dict) and item.get("type") == "output_text"
    )
    return str(turn_id) if turn_id else None, text


def load_decisions(paths: Iterable[Path], candidate_ids: set[str]) -> dict[str, list[str]]:
    decisions: dict[str, list[str]] = {}
    for path in paths:
        try:
            with path.open(encoding="utf-8") as handle:
                for raw in handle:
                    try:
                        record = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    turn_id, message = assistant_text(record)
                    if turn_id not in candidate_ids:
                        continue
                    lines = ANY_ROUTE_LINE.findall(message)
                    if not lines:
                        continue
                    bucket = decisions.setdefault(turn_id, [])
                    for line in lines:
                        if line not in bucket:
                            bucket.append(line)
        except OSError:
            continue
    return decisions


def parse_decision(line: str) -> dict[str, object] | None:
    match = ROUTE_LINE.fullmatch(line.strip())
    if match is None:
        return None
    route, write_ready, read_ready, lead, reason, detail = match.groups()
    return {
        "route": route,
        "write_ready": int(write_ready),
        "read_ready": int(read_ready),
        "lead": lead.strip(),
        "reason": reason,
        "detail": detail.strip(),
    }


def build_report(candidates: dict[str, str], raw: dict[str, list[str]]) -> dict[str, object]:
    parsed: dict[str, dict[str, object]] = {}
    malformed: list[str] = []
    duplicate: list[str] = []
    for turn_id, lines in raw.items():
        if len(lines) > 1:
            duplicate.append(turn_id)
        decision = parse_decision(lines[-1])
        if decision is None:
            malformed.append(turn_id)
        else:
            parsed[turn_id] = decision

    flags: dict[str, list[str]] = {}
    for turn_id, decision in parsed.items():
        route = str(decision["route"])
        reason = str(decision["reason"])
        write_ready = int(decision["write_ready"])
        read_ready = int(decision["read_ready"])
        issues: list[str] = []
        if route == "direct" and (write_ready > 0 or read_ready > 0):
            issues.append("direct_declined_ready_work")
        if route == "direct" and reason in {"parallel_gain", "quota_gain"}:
            issues.append("direct_with_delegation_gain_reason")
        if route != "direct" and reason in {"lead_faster", "review_cost"}:
            issues.append("delegated_with_direct_reason")
        if reason == "route_unavailable":
            issues.append("manually_verify_named_route_or_probe")
        if reason == "shared_surface" and write_ready > 0:
            issues.append("manually_verify_independent_write_units")
        if issues:
            flags[turn_id] = issues

    routes = Counter(str(item["route"]) for item in parsed.values())
    reasons = Counter(str(item["reason"]) for item in parsed.values())
    candidate_ids = set(candidates)
    answered_ids = set(raw)
    return {
        "experiment": DEFAULT_EXPERIMENT,
        "candidate_count": len(candidate_ids),
        "answered_count": len(parsed),
        "compliance_rate": round(len(parsed) / len(candidate_ids), 4) if candidate_ids else 0.0,
        "missing_turn_ids": sorted(candidate_ids - answered_ids),
        "malformed_turn_ids": sorted(malformed),
        "duplicate_decision_turn_ids": sorted(duplicate),
        "route_distribution": dict(sorted(routes.items())),
        "reason_distribution": dict(sorted(reasons.items())),
        "write_ready_total": sum(int(item["write_ready"]) for item in parsed.values()),
        "read_ready_total": sum(int(item["read_ready"]) for item in parsed.values()),
        "review_flags": flags,
        "decisions": parsed,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=default_database())
    parser.add_argument("--experiment", default=DEFAULT_EXPERIMENT)
    parser.add_argument("--logs", type=Path, nargs="*", default=default_log_roots())
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    candidates = load_candidates(args.database.expanduser(), args.experiment)
    paths = matching_logs((path.expanduser() for path in args.logs), set(candidates.values()))
    report = build_report(candidates, load_decisions(paths, set(candidates)))
    report["experiment"] = args.experiment
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return

    print(
        f"{args.experiment}: {report['answered_count']}/{report['candidate_count']} compliant "
        f"({float(report['compliance_rate']):.0%})"
    )
    print(f"routes={report['route_distribution']} reasons={report['reason_distribution']}")
    print(
        f"WRITE_READY={report['write_ready_total']} READ_READY={report['read_ready_total']} "
        f"flags={len(report['review_flags'])}"
    )
    for turn_id, decision in report["decisions"].items():
        markers = ",".join(report["review_flags"].get(turn_id, []))
        suffix = f" FLAG={markers}" if markers else ""
        print(
            f"{turn_id} ROUTE={decision['route']} WRITE_READY={decision['write_ready']} "
            f"READ_READY={decision['read_ready']} REASON={decision['reason']} "
            f"DETAIL={decision['detail']}{suffix}"
        )
    if report["missing_turn_ids"]:
        print(f"missing={','.join(report['missing_turn_ids'])}")
    if report["malformed_turn_ids"]:
        print(f"malformed={','.join(report['malformed_turn_ids'])}")


if __name__ == "__main__":
    main()
