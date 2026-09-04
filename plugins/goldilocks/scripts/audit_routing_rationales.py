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

import model_economics as economics


DEFAULT_EXPERIMENT = "routing-rationale-v3.2"
ROUTE_FIELDS = (
    r"ROUTE=(direct|fast|standard|mixed)\s*\|\s*"
    r"WRITE_READY=(\d+)\s*\|\s*READ_READY=(\d+)\s*\|\s*"
    r"EXISTING=(\d+)\s*\|\s*"
    r"(?:PLANNED_DISPATCH|NEW_DISPATCH)=(\d+)\s*\|\s*"
    r"LEAD=(.*?)\s*\|\s*REASON=([a-z_]+)\s*\|\s*DETAIL=(.+?)"
)
ROUTE_LINE = re.compile(rf"^{ROUTE_FIELDS}$")
CANONICAL_ROUTE_COMMENT = re.compile(rf"<!--\s*({ROUTE_FIELDS})\s*-->", re.DOTALL)


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


def load_silent_audits(database: Path, experiment: str) -> dict[str, object]:
    with sqlite3.connect(database) as connection:
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'route_audits'"
        ).fetchone()
        if table is None:
            return {
                "audit_count": 0,
                "flagged_audit_count": 0,
                "flag_distribution": {},
                "planned_dispatch_total": 0,
                "observed_dispatch_total": 0,
            }
        rows = connection.execute(
            "SELECT planned_dispatch, observed_dispatch, review_flags "
            "FROM route_audits WHERE routing_experiment_id = ?",
            (experiment,),
        ).fetchall()
    flags: Counter[str] = Counter()
    flagged = 0
    for _planned, _observed, raw_flags in rows:
        try:
            parsed = json.loads(str(raw_flags or "[]"))
        except json.JSONDecodeError:
            parsed = []
        values = [str(value) for value in parsed if isinstance(value, str)]
        if values:
            flagged += 1
            flags.update(values)
    return {
        "audit_count": len(rows),
        "flagged_audit_count": flagged,
        "flag_distribution": dict(sorted(flags.items())),
        "planned_dispatch_total": sum(int(row[0] or 0) for row in rows),
        "observed_dispatch_total": sum(int(row[1] or 0) for row in rows),
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


def parse_mapping(values: list[str], *, numeric: bool = False) -> dict[str, object]:
    result: dict[str, object] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected KEY=VALUE, received {value}")
        key, raw = value.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if not key or not raw:
            raise ValueError(f"expected KEY=VALUE, received {value}")
        if numeric:
            amount = float(raw)
            if amount <= 0:
                raise ValueError(f"budget must be positive: {value}")
            result[key] = amount
        else:
            result[key] = raw
    return result


def row_value(row: sqlite3.Row, key: str) -> object | None:
    return row[key] if key in row.keys() else None


def frozen_snapshot_current_at_route(
    snapshot: dict[str, object], model: str, channel: str, started_at: object
) -> bool:
    """Accept a recorded official snapshot only if it covered the route's start.

    A current registry is preferred for live reporting.  When that registry has
    since expired, an external route's recorded price evidence remains usable
    for historical cost reporting, but only for its original model/channel and
    only through the source's recorded expiry.
    """

    if snapshot.get("model") != model or snapshot.get("billing_channel") != channel:
        return False
    source = snapshot.get("source")
    if not isinstance(source, dict) or source.get("kind") != "official":
        return False
    try:
        route_started = economics.parse_timestamp(started_at)
        expires_at = economics.parse_timestamp(source.get("expires_at"))
    except economics.EconomicsError:
        return False
    return route_started <= expires_at


def load_usage_economics(
    database: Path,
    registry_path: Path,
    channel_overrides: dict[str, object],
    remaining_budgets: dict[str, object],
) -> dict[str, object]:
    registry = economics.load_economics(registry_path)
    routes: list[dict[str, object]] = []
    with sqlite3.connect(database) as connection:
        connection.row_factory = sqlite3.Row
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if "executions" in tables:
            decision_columns = (
                {
                    str(row[1])
                    for row in connection.execute("PRAGMA table_info(decisions)")
                }
                if "decisions" in tables
                else set()
            )
            billing_select = (
                "decision.billing_channel AS decision_billing_channel"
                if "billing_channel" in decision_columns
                else "NULL AS decision_billing_channel"
            )
            if "decisions" in tables:
                rows = connection.execute(
                    f"""
                    SELECT execution.*, decision.status AS decision_status,
                           decision.tier AS decision_tier, {billing_select}
                    FROM executions AS execution
                    LEFT JOIN decisions AS decision
                        ON decision.decision_id = execution.decision_id
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT execution.*, NULL AS decision_status, NULL AS decision_tier, "
                    "NULL AS decision_billing_channel FROM executions AS execution"
                ).fetchall()
            for row in rows:
                model = str(row_value(row, "actual_model") or "")
                routes.append(
                    {
                        "kind": "native",
                        "model": model,
                        "started_at": row_value(row, "started_at"),
                        "input_tokens": row_value(row, "input_tokens"),
                        "cached_input_tokens": row_value(row, "cached_input_tokens"),
                        "output_tokens": row_value(row, "output_tokens"),
                        "elapsed_ms": row_value(row, "elapsed_ms"),
                        "verified": str(row_value(row, "decision_status") or "")
                        in {"verified_pass", "verified_fail"},
                        "unplanned_sol": model == "gpt-5.6-sol"
                        and (
                            not row_value(row, "decision_id")
                            or row_value(row, "correlation_confidence") == "unplanned"
                        ),
                        "billing_channel": row_value(row, "decision_billing_channel")
                        or channel_overrides.get(model),
                        "pricing_snapshot": None,
                    }
                )
        if "external_routes" in tables:
            rows = connection.execute("SELECT * FROM external_routes").fetchall()
            for row in rows:
                model = str(
                    row_value(row, "actual_model")
                    or row_value(row, "expected_model")
                    or ""
                )
                stored_snapshot: dict[str, object] | None = None
                raw_snapshot = row_value(row, "pricing_snapshot")
                if isinstance(raw_snapshot, str) and raw_snapshot:
                    try:
                        parsed = json.loads(raw_snapshot)
                        if isinstance(parsed, dict):
                            stored_snapshot = parsed
                    except json.JSONDecodeError:
                        pass
                routes.append(
                    {
                        "kind": "external",
                        "model": model,
                        "started_at": row_value(row, "started_at"),
                        "input_tokens": row_value(row, "input_tokens"),
                        "cached_input_tokens": row_value(row, "cached_input_tokens"),
                        "output_tokens": row_value(row, "output_tokens"),
                        "elapsed_ms": row_value(row, "elapsed_ms"),
                        "verified": row_value(row, "lead_result") in {"pass", "fail"},
                        "unplanned_sol": False,
                        "billing_channel": row_value(row, "billing_channel")
                        or channel_overrides.get(model),
                        "pricing_snapshot": stored_snapshot,
                    }
                )

    totals = {
        "routes": len(routes),
        "verified_routes": sum(bool(route["verified"]) for route in routes),
        "unverified_routes": sum(not bool(route["verified"]) for route in routes),
        "unplanned_sol_workers": sum(bool(route["unplanned_sol"]) for route in routes),
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "uncached_input_tokens": 0,
        "output_tokens": 0,
        "processing_tokens": 0,
        "elapsed_ms": 0,
    }
    by_model: dict[str, dict[str, object]] = {}
    pool_costs: dict[str, dict[str, object]] = {}
    unknown_cost_routes = 0
    for route in routes:
        model = str(route["model"] or "unknown")
        input_tokens = max(0, int(route["input_tokens"] or 0))
        cached_tokens = min(input_tokens, max(0, int(route["cached_input_tokens"] or 0)))
        output_tokens = max(0, int(route["output_tokens"] or 0))
        elapsed_ms = max(0, int(route["elapsed_ms"] or 0))
        uncached_tokens = input_tokens - cached_tokens
        totals["input_tokens"] += input_tokens
        totals["cached_input_tokens"] += cached_tokens
        totals["uncached_input_tokens"] += uncached_tokens
        totals["output_tokens"] += output_tokens
        totals["processing_tokens"] += input_tokens + output_tokens
        totals["elapsed_ms"] += elapsed_ms
        model_row = by_model.setdefault(
            model,
            {
                "routes": 0,
                "verified_routes": 0,
                "input_tokens": 0,
                "cached_input_tokens": 0,
                "uncached_input_tokens": 0,
                "output_tokens": 0,
                "processing_tokens": 0,
                "elapsed_ms": 0,
            },
        )
        model_row["routes"] += 1
        model_row["verified_routes"] += int(bool(route["verified"]))
        model_row["input_tokens"] += input_tokens
        model_row["cached_input_tokens"] += cached_tokens
        model_row["uncached_input_tokens"] += uncached_tokens
        model_row["output_tokens"] += output_tokens
        model_row["processing_tokens"] += input_tokens + output_tokens
        model_row["elapsed_ms"] += elapsed_ms

        channel = route.get("billing_channel")
        snapshot = route.get("pricing_snapshot")
        if channel:
            try:
                snapshot = economics.pricing_snapshot(
                    registry,
                    model,
                    str(channel),
                    require_current=True,
                    require_rankable=False,
                )
            except economics.EconomicsError:
                if isinstance(snapshot, dict):
                    current = frozen_snapshot_current_at_route(
                        snapshot,
                        model,
                        str(channel),
                        route.get("started_at"),
                    )
                    snapshot = {**snapshot, "price_current": current}
                else:
                    snapshot = None
        if not isinstance(snapshot, dict):
            unknown_cost_routes += 1
            continue
        estimate = economics.estimate_cost(
            snapshot, input_tokens, cached_tokens, output_tokens
        )
        if estimate["status"] != "estimated":
            unknown_cost_routes += 1
            continue
        pool = str(estimate["billing_channel"])
        currency = str(estimate["currency"])
        bucket = pool_costs.setdefault(
            pool,
            {"currency": currency, "estimated_amount": 0.0, "routes": 0},
        )
        if bucket["currency"] != currency:
            raise ValueError(f"billing channel {pool} contains mixed currencies")
        bucket["estimated_amount"] += float(estimate["amount"])
        bucket["routes"] += 1

    for pool, bucket in pool_costs.items():
        bucket["estimated_amount"] = round(float(bucket["estimated_amount"]), 12)
        budget = remaining_budgets.get(pool)
        if isinstance(budget, (int, float)):
            bucket["remaining_budget"] = float(budget)
            bucket["estimated_budget_fraction"] = round(
                float(bucket["estimated_amount"]) / float(budget), 12
            )
    sol = by_model.get("gpt-5.6-sol", {})
    sol_share = {
        key: round(float(sol.get(key, 0)) / float(totals[key]), 6)
        if totals[key]
        else 0.0
        for key in ("uncached_input_tokens", "output_tokens", "processing_tokens")
    }
    return {
        "raw": totals,
        "by_model": dict(sorted(by_model.items())),
        "sol_share": sol_share,
        "cost_by_billing_channel": dict(sorted(pool_costs.items())),
        "unknown_cost_routes": unknown_cost_routes,
        "cross_pool_rule": (
            "Compare estimated_budget_fraction when provided; otherwise preserve separate "
            "currency/allowance totals and a Pareto frontier."
        ),
    }


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
                    lines = [match.group(1) for match in CANONICAL_ROUTE_COMMENT.finditer(message)]
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
    route, write_ready, read_ready, existing, planned_dispatch, lead, reason, detail = match.groups()
    return {
        "route": route,
        "write_ready": int(write_ready),
        "read_ready": int(read_ready),
        "existing": int(existing),
        "planned_dispatch": int(planned_dispatch),
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
        planned_dispatch = int(decision["planned_dispatch"])
        observed_dispatch = int(observed_dispatches.get(turn_id, 0))
        decision["observed_dispatch"] = observed_dispatch
        grant_active = bool(candidates.get(turn_id, {}).get("delegation_grant_active"))
        issues: list[str] = []
        if route == "direct" and (write_ready > 0 or read_ready > 0):
            issues.append("direct_declined_ready_work")
        if route == "direct" and reason in {"parallel_gain", "quota_gain"}:
            issues.append("direct_with_delegation_gain_reason")
        if route != "direct" and reason in {"lead_faster", "review_cost"}:
            issues.append("delegated_with_direct_reason")
        if reason == "shared_surface" and write_ready > 0:
            issues.append("manually_verify_independent_write_units")
        if route == "direct" and planned_dispatch > 0:
            issues.append("direct_plans_dispatch")
        if route == "mixed" and existing == 0 and planned_dispatch == 0:
            issues.append("mixed_without_parallel_ownership")
        if planned_dispatch > write_ready + read_ready:
            issues.append("planned_dispatch_exceeds_ready_units")
        if planned_dispatch != observed_dispatch:
            issues.append("planned_dispatch_mismatch")
        if grant_active and write_ready + read_ready > 0 and observed_dispatch == 0:
            issues.append("authorized_ready_without_observed_dispatch")
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
        if int(decision["observed_dispatch"]) > 0
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
        "planned_dispatch_total": sum(
            int(item["planned_dispatch"]) for item in parsed.values()
        ),
        "observed_dispatch_total": sum(
            int(item["observed_dispatch"]) for item in parsed.values()
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
    parser.add_argument(
        "--economics",
        type=Path,
        default=economics.DEFAULT_ECONOMICS,
        help="Official model-economics registry.",
    )
    parser.add_argument(
        "--billing-channel",
        action="append",
        default=[],
        metavar="MODEL=CHANNEL",
        help="Explicit active billing channel for native routes lacking one.",
    )
    parser.add_argument(
        "--remaining-budget",
        action="append",
        default=[],
        metavar="CHANNEL=AMOUNT",
        help="Optional remaining pool budget for cross-pool normalization.",
    )
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
    report["silent_audits"] = load_silent_audits(
        args.database.expanduser(), args.experiment
    )
    report["usage_economics"] = load_usage_economics(
        args.database.expanduser(),
        args.economics.expanduser(),
        parse_mapping(args.billing_channel),
        parse_mapping(args.remaining_budget, numeric=True),
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        return

    print(
        f"{args.experiment}: {report['answered_count']}/{report['candidate_count']} compliant "
        f"({float(report['compliance_rate']):.0%})"
    )
    usage = report["usage_economics"]
    print(
        f"workers={usage['raw']['routes']} verified={usage['raw']['verified_routes']} "
        f"unverified={usage['raw']['unverified_routes']} "
        f"unplanned_sol={usage['raw']['unplanned_sol_workers']} "
        f"processing_tokens={usage['raw']['processing_tokens']} "
        f"unknown_cost_routes={usage['unknown_cost_routes']}"
    )
    print(f"routes={report['route_distribution']} reasons={report['reason_distribution']}")
    print(
        f"WRITE_READY={report['write_ready_total']} READ_READY={report['read_ready_total']} "
        f"EXISTING={report['existing_parallel_total']} "
        f"PLANNED_DISPATCH={report['planned_dispatch_total']} "
        f"OBSERVED_DISPATCH={report['observed_dispatch_total']} "
        f"authorized_dispatch_rate={float(report['authorized_active_dispatch_rate']):.0%} "
        f"flags={len(report['review_flags'])}"
    )
    for turn_id, decision in report["decisions"].items():
        markers = ",".join(report["review_flags"].get(turn_id, []))
        suffix = f" FLAG={markers}" if markers else ""
        print(
            f"{turn_id} ROUTE={decision['route']} WRITE_READY={decision['write_ready']} "
            f"READ_READY={decision['read_ready']} EXISTING={decision['existing']} "
            f"PLANNED_DISPATCH={decision['planned_dispatch']} "
            f"OBSERVED_DISPATCH={decision['observed_dispatch']} "
            f"REASON={decision['reason']} "
            f"DETAIL={decision['detail']}{suffix}"
        )
    if report["missing_turn_ids"]:
        print(f"missing={','.join(report['missing_turn_ids'])}")
    if report["malformed_turn_ids"]:
        print(f"malformed={','.join(report['malformed_turn_ids'])}")


if __name__ == "__main__":
    main()
