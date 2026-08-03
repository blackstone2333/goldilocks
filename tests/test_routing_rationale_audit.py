#!/usr/bin/env python3

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "plugins" / "goldilocks" / "scripts" / "audit_routing_rationales.py"


def response(turn_id: str, text: str) -> str:
    return json.dumps(
        {
            "type": "response_item",
            "payload": {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": text}],
                "internal_chat_message_metadata_passthrough": {"turn_id": turn_id},
            },
        },
        ensure_ascii=False,
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        database = root / "orchestration.db"
        with sqlite3.connect(database) as connection:
            connection.execute(
                "CREATE TABLE gate_injections (session_id TEXT, turn_id TEXT, "
                "routing_rationale_candidate INTEGER, routing_experiment_id TEXT, "
                "delegation_grant_active INTEGER, cwd_hash TEXT, injected_at TEXT)"
            )
            connection.executemany(
                "INSERT INTO gate_injections VALUES "
                "(?, ?, 1, 'routing-rationale-v3', ?, 'cwd-a', ?)",
                [
                    ("session-a", "turn-a", 1, "2026-08-03T00:00:00+00:00"),
                    ("session-a", "turn-b", 1, "2026-08-03T00:01:00+00:00"),
                    ("session-a", "turn-c", 0, "2026-08-03T00:02:00+00:00"),
                ],
            )
            connection.execute(
                "CREATE TABLE decisions (session_id TEXT, started_at TEXT, agent_id TEXT, "
                "status TEXT, expected_model TEXT, actual_model TEXT)"
            )
            connection.execute(
                "INSERT INTO decisions VALUES "
                "('session-a', '2026-08-03T00:01:30+00:00', 'actual-worker-b', "
                "'stopped', 'worker-model', 'worker-model')"
            )
            connection.execute(
                "CREATE TABLE external_routes (parent_session_id TEXT, started_at TEXT, "
                "route_id TEXT, status TEXT, expected_model TEXT, actual_model TEXT, "
                "child_thread_id TEXT)"
            )
            connection.executemany(
                "INSERT INTO external_routes VALUES "
                "(?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        "session-a",
                        "2026-08-03T00:01:40+00:00",
                        "external-worker-b",
                        "failed",
                        "external-model",
                        "external-model",
                        "child-thread-b",
                    ),
                    (
                        "session-a",
                        "2026-08-03T00:02:10+00:00",
                        "next-prompt-decoy",
                        "succeeded",
                        "external-model",
                        "external-model",
                        "child-thread-c",
                    ),
                ],
            )

        log = root / "rollout-session-a.jsonl"
        log.write_text(
            "\n".join(
                [
                    response(
                        "turn-a",
                        "ROUTE=direct | WRITE_READY=0 | READ_READY=1 | EXISTING=0 | "
                        "NEW_DISPATCH=0 | LEAD=接口与验收 | "
                        "REASON=review_cost | DETAIL=交接和复核比本地诊断更慢。",
                    ),
                    response(
                        "turn-b",
                        "ROUTE=mixed | WRITE_READY=1 | READ_READY=2 | EXISTING=1 | "
                        "NEW_DISPATCH=2 | LEAD=集成 | "
                        "REASON=parallel_gain | DETAIL=独立工作可并行。",
                    ),
                    json.dumps(
                        {"type": "event_msg", "payload": {"type": "user_message", "message": "secret prompt"}},
                        ensure_ascii=False,
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--database",
                str(database),
                "--logs",
                str(log),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
        assert "secret prompt" not in result.stdout
        report = json.loads(result.stdout)
        assert report["candidate_count"] == 3
        assert report["answered_count"] == 2
        assert report["compliance_rate"] == 0.6667
        assert report["missing_turn_ids"] == ["turn-c"]
        assert report["route_distribution"] == {"direct": 1, "mixed": 1}
        assert report["write_ready_total"] == 1
        assert report["read_ready_total"] == 3
        assert report["existing_parallel_total"] == 1
        assert report["claimed_new_dispatch_total"] == 2
        assert report["new_dispatch_total"] == 2
        assert report["active_dispatch_turns"] == 1
        assert report["authorized_ready_count"] == 2
        assert report["authorized_active_dispatch_rate"] == 0.5
        assert report["review_flags"]["turn-a"] == [
            "direct_declined_ready_work",
            "authorized_ready_without_new_dispatch",
        ]

        with sqlite3.connect(database) as connection:
            connection.execute("DELETE FROM decisions")
            connection.execute("DELETE FROM external_routes")
        unobserved = subprocess.run(
            [
                sys.executable,
                str(AUDIT),
                "--database",
                str(database),
                "--logs",
                str(log),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        assert unobserved.returncode == 0, unobserved.stderr
        unobserved_report = json.loads(unobserved.stdout)
        assert unobserved_report["claimed_new_dispatch_total"] == 2
        assert unobserved_report["new_dispatch_total"] == 0
        assert "claimed_dispatch_without_observed_start" in unobserved_report[
            "review_flags"
        ]["turn-b"]

    print("Goldilocks routing-rationale audit passed.")


if __name__ == "__main__":
    main()
