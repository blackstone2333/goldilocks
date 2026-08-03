#!/usr/bin/env python3

"""Audit the local routing-rationale experiment without reading prompt content."""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


DEFAULT_EXPERIMENT = "routing-rationale-v3"
ROUTE_LINE = re.compile(
    r"^ROUTE=(direct|fast|standard|mixed)\s*\|\s*"
    r"WRITE_READY=(\d+)\s*\|\s*READ_READY=(\d+)\s*\|\s*"
    r"EXISTING=(\d+)\s*\|\s*NEW_DISPATCH=(\d+)\s*\|\s*"
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


def load_candidates(database: Path, experiment: str) -> dict[str, dict[str, object]]:
    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT session_id, turn_id, cwd_hash, injected_at, "
            "delegation_grant_active FROM gate_injections "
            "WHERE routing_rationale_candidate = 1 AND routing_experiment_id = ?",
            (experiment,),
        ).fetchall()
    return {
        str(turn_id): {
            "session_id": str(session_id),
            "cwd_hash": str(cwd_hash),
            "injected_at": str(injected_at),
            "delegation_grant_active": bool(grant_active),
        }
        for session_id, turn_id, cwd_hash, injected_at, grant_active in rows
    }


def load_observed_dispatches(
    database: Path, candidates: dict[str, dict[str, object]]
) -> dict[str, int]:
    observed = {turn_id: 0 for turn_id in candidates}
    candidate_windows: dict[str, list[tuple[str, str]]] = {}
    for turn_id, candidate in candidates.items():
        candidate_windows.setdefault(str(candidate["session_id"]), []).append(
            (str(candidate["injected_at"]), turn_id)
        )
    with sqlite3.connect(database) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        decision_columns = (
            {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(decisions)")
            }
            if "decisions" in tables
            else set()
        )
        external_columns = (
            {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(external_routes)")
            }
            if "external_routes" in tables
            else set()
        )
        native_ready = {
            "session_id",
            "started_at",
            "agent_id",
            "status",
            "expected_model",
            "actual_model",
        }.issubset(decision_columns)
        external_ready = {
            "parent_session_id",
            "started_at",
            "route_id",
            "status",
            "child_thread_id",
        }.issubset(external_columns)
        all_boundaries: dict[str, list[str]] = {}
        if "gate_injections" in tables:
            gate_columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(gate_injections)")
            }
            if {"session_id", "injected_at"}.issubset(gate_columns):
                for session_id, injected_at in connection.execute(
                    "SELECT session_id, injected_at FROM gate_injections"
                ):
                    all_boundaries.setdefault(str(session_id), []).append(
                        str(injected_at)
                    )
        for session_id, windows in candidate_windows.items():
            boundaries = sorted(all_boundaries.get(session_id, []))
            for started_at, turn_id in sorted(windows):
                deadline = (
                    datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                    + timedelta(minutes=30)
                ).isoformat()
                later_boundaries = [value for value in boundaries if value > started_at]
                before = min(
                    later_boundaries[0] if later_boundaries else deadline,
                    deadline,
                )
                count = 0
                if native_ready:
                    count += int(
                        connection.execute(
                            """
                            SELECT COUNT(DISTINCT agent_id) FROM decisions
                            WHERE session_id = ? AND started_at >= ? AND started_at < ?
                                AND agent_id IS NOT NULL
                                AND status IN (
                                    'started', 'stopped', 'verified_pass', 'verified_fail'
                                )
                                AND expected_model = actual_model
                            """,
                            (session_id, started_at, before),
                        ).fetchone()[0]
                    )
                if external_ready:
                    count += int(
                        connection.execute(
                            """
                            SELECT COUNT(DISTINCT route_id) FROM external_routes
                            WHERE parent_session_id = ? AND started_at >= ? AND started_at < ?
                                AND status IN ('started', 'succeeded', 'failed')
                                AND child_thread_id IS NOT NULL AND child_thread_id != ''
                            """,
                            (session_id, started_at, before),
                        ).fetchone()[0]
                    )
                observed[turn_id] = count
    return observed


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
    route, write_ready, read_ready, existing, new_dispatch, lead, reason, detail = match.groups()
    return {
        "route": route,
        "write_ready": int(write_ready),
        "read_ready": int(read_ready),
        "existing": int(existing),
        "new_dispatch": int(new_dispatch),
        "lead": lead.strip(),
        "reason": reason,
        "detail": detail.strip(),
    }


def build_report(
    candidates: dict[str, dict[str, object]],
    raw: dict[str, list[str]],
    observed_dispatches: dict[str, int] | None = None,
) -> dict[str, object]:
    observed_dispatches = observed_dispatches or {}
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
        existing = int(decision["existing"])
        new_dispatch = int(decision["new_dispatch"])
        observed_dispatch = int(observed_dispatches.get(turn_id, 0))
        decision["observed_new_dispatch"] = observed_dispatch
        grant_active = bool(candidates.get(turn_id, {}).get("delegation_grant_active"))
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
        if route == "direct" and new_dispatch > 0:
            issues.append("direct_claims_new_dispatch")
        if route == "mixed" and existing == 0 and new_dispatch == 0:
            issues.append("mixed_without_parallel_ownership")
        if new_dispatch > write_ready + read_ready:
            issues.append("dispatch_exceeds_ready_units")
        if new_dispatch > observed_dispatch:
            issues.append("claimed_dispatch_without_observed_start")
        if grant_active and write_ready + read_ready > 0 and observed_dispatch == 0:
            issues.append("authorized_ready_without_new_dispatch")
        if issues:
            flags[turn_id] = issues

    routes = Counter(str(item["route"]) for item in parsed.values())
    reasons = Counter(str(item["reason"]) for item in parsed.values())
    candidate_ids = set(candidates)
    answered_ids = set(raw)
    authorized_ready = [
        turn_id
        for turn_id, decision in parsed.items()
        if candidates.get(turn_id, {}).get("delegation_grant_active")
        and int(decision["write_ready"]) + int(decision["read_ready"]) > 0
    ]
    active_dispatch = [
        turn_id
        for turn_id, decision in parsed.items()
        if int(decision["observed_new_dispatch"]) > 0
    ]
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
        "existing_parallel_total": sum(int(item["existing"]) for item in parsed.values()),
        "claimed_new_dispatch_total": sum(
            int(item["new_dispatch"]) for item in parsed.values()
        ),
        "new_dispatch_total": sum(
            int(item["observed_new_dispatch"]) for item in parsed.values()
        ),
        "active_dispatch_turns": len(active_dispatch),
        "authorized_candidate_count": sum(
            bool(item.get("delegation_grant_active")) for item in candidates.values()
        ),
        "authorized_ready_count": len(authorized_ready),
        "authorized_active_dispatch_rate": round(
            sum(turn_id in active_dispatch for turn_id in authorized_ready)
            / len(authorized_ready),
            4,
        )
        if authorized_ready
        else 0.0,
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
    session_ids = {str(item["session_id"]) for item in candidates.values()}
    paths = matching_logs((path.expanduser() for path in args.logs), session_ids)
    raw_decisions = load_decisions(paths, set(candidates))
    report = build_report(
        candidates,
        raw_decisions,
        load_observed_dispatches(args.database.expanduser(), candidates),
    )
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
        f"EXISTING={report['existing_parallel_total']} "
        f"CLAIMED_NEW_DISPATCH={report['claimed_new_dispatch_total']} "
        f"OBSERVED_NEW_DISPATCH={report['new_dispatch_total']} "
        f"authorized_dispatch_rate={float(report['authorized_active_dispatch_rate']):.0%} "
        f"flags={len(report['review_flags'])}"
    )
    for turn_id, decision in report["decisions"].items():
        markers = ",".join(report["review_flags"].get(turn_id, []))
        suffix = f" FLAG={markers}" if markers else ""
        print(
            f"{turn_id} ROUTE={decision['route']} WRITE_READY={decision['write_ready']} "
            f"READ_READY={decision['read_ready']} EXISTING={decision['existing']} "
            f"CLAIMED_NEW_DISPATCH={decision['new_dispatch']} "
            f"OBSERVED_NEW_DISPATCH={decision['observed_new_dispatch']} "
            f"REASON={decision['reason']} "
            f"DETAIL={decision['detail']}{suffix}"
        )
    if report["missing_turn_ids"]:
        print(f"missing={','.join(report['missing_turn_ids'])}")
    if report["malformed_turn_ids"]:
        print(f"malformed={','.join(report['malformed_turn_ids'])}")


if __name__ == "__main__":
    main()
