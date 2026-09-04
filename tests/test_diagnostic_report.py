from __future__ import annotations
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "plugins/goldilocks/scripts/diagnostic_report.py"

def test_recent_assistant_only_and_readonly(tmp_path: Path) -> None:
    now=datetime.now(timezone.utc).isoformat(); old=(datetime.now(timezone.utc)-timedelta(days=9)).isoformat()
    data=tmp_path/"data"; data.mkdir()
    with sqlite3.connect(data/"orchestration.db") as db:
        db.execute("CREATE TABLE decisions (tier TEXT, policy_version TEXT, status TEXT, turn_id TEXT, planned_at TEXT)")
        db.execute("INSERT INTO decisions VALUES ('fast','0.5.3-beta','started','secret-turn-12345678',?)",(now,))
        db.execute("CREATE TABLE gate_injections (injected_at TEXT)")
        db.execute("INSERT INTO gate_injections VALUES (?)",(now,))
    sessions=tmp_path/"sessions"; sessions.mkdir()
    (sessions/"rollout.jsonl").write_text("\n".join((
        '{"timestamp":"'+now+'","type":"event_msg","payload":{"type":"task_started","turn_id":"x"}}',
        '{"type":"response_item","payload":{"type":"message","role":"user","content":[{"type":"output_text","text":"路由=快速｜团队=主模型｜并发=0/6｜委派=无｜理由=例子｜详情=不应计数"}]}}',
        '{"type":"response_item","payload":{"type":"message","role":"assistant","phase":"commentary","internal_chat_message_metadata_passthrough":{"turn_id":"x"},"content":[{"type":"output_text","text":"路由=快速｜团队=主模型｜并发=0/6｜委派=无｜理由=进度｜详情=不应计数"}]}}',
        '{"type":"response_item","payload":{"type":"message","role":"assistant","phase":"final_answer","internal_chat_message_metadata_passthrough":{"turn_id":"x"},"content":[{"type":"output_text","text":"路由=标准｜团队=主模型｜并发=0/6｜委派=无｜理由=完成｜详情=已验证"}]}}',
    ))+"\n",encoding="utf-8")
    before=(data/"orchestration.db").read_bytes()
    result=subprocess.run([sys.executable,str(REPORT),"--data-dir",str(data),"--sessions-dir",str(sessions),"--days","7"],text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    assert "含 final-answer 回执 turn / 回执数 / 重复：1 / 1 / 0" in result.stdout
    assert "可见回执路线：{'standard': 1}" in result.stdout
    assert "原生委派决策 / tier：1 / {'fast': 1}" in result.stdout
    assert "Hook" not in result.stdout
    assert "secret-turn" not in result.stdout
    assert (data/"orchestration.db").read_bytes()==before

def test_no_data_is_readable(tmp_path: Path) -> None:
    result=subprocess.run([sys.executable,str(REPORT),"--data-dir",str(tmp_path/"none"),"--sessions-dir",str(tmp_path/"sessions")],text=True,capture_output=True)
    assert result.returncode==0 and "证据不足" in result.stdout

def main() -> None:
    with tempfile.TemporaryDirectory() as raw:
        root=Path(raw); test_recent_assistant_only_and_readonly(root)
    with tempfile.TemporaryDirectory() as raw:
        root=Path(raw); test_no_data_is_readable(root)

if __name__ == "__main__":
    main()
