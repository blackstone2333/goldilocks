#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Produce a privacy-first, read-only Goldilocks diagnostic report."""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
EN_RECEIPT = re.compile(
    r"(?mi)^ROUTE=(direct|fast|standard|mixed)\s*\|\s*TEAM=.+\|\s*"
    r"CONCURRENCY=.+\|\s*DELEGATED=.+\|\s*REASON=.+\|\s*DETAIL=.+$"
)
ZH_RECEIPT = re.compile(
    r"(?m)^路由=(直接|快速|标准|混合)｜团队=.+｜并发=.+｜委派=.+｜理由=.+｜详情=.+$"
)
OFFICIAL = {"goldilocks_luna_economy", "goldilocks_spark_worker", "goldilocks_terra_engineer", "goldilocks_sol_reviewer"}
ROUTE_NAMES = {"直接": "direct", "快速": "fast", "标准": "standard", "混合": "mixed"}

def parse_time(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

def cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data-dir", type=Path)
    p.add_argument("--sessions-dir", type=Path)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--output", type=Path)
    p.add_argument("--lang", choices=("zh", "en"), default="zh")
    return p

def data_root(explicit: Path | None, gaps: list[str]) -> Path | None:
    if explicit: return explicit.expanduser()
    if os.environ.get("PLUGIN_DATA"): return Path(os.environ["PLUGIN_DATA"]).expanduser()
    base = Path.home()/".codex/plugins/data"
    found = sorted(p.parent for p in base.glob("goldilocks-*/orchestration.db"))
    if len(found) == 1: return found[0]
    if len(found) > 1:
        try:
            result = subprocess.run(
                ["codex", "plugin", "list", "--json"], text=True,
                capture_output=True, timeout=3, check=False,
            )
            installed = json.loads(result.stdout).get("installed", []) if result.returncode == 0 else []
            active = [
                row for row in installed
                if row.get("enabled") and str(row.get("name") or "").lower() == "goldilocks"
            ]
            if len(active) == 1:
                candidate = base / f"goldilocks-{active[0].get('marketplaceName')}"
                if (candidate / "orchestration.db").is_file(): return candidate
        except (OSError, subprocess.SubprocessError, ValueError, TypeError, json.JSONDecodeError):
            pass
    gaps.append("未发现 Goldilocks SQLite 数据库" if not found else "发现多个 Goldilocks 数据目录；请用 --data-dir 指定")
    return None

def ro(path: Path) -> sqlite3.Connection:
    c = sqlite3.connect(f"file:{quote(str(path.resolve()), safe='/')}?mode=ro", uri=True, timeout=3)
    c.row_factory = sqlite3.Row
    return c

def cols(c: sqlite3.Connection, table: str) -> set[str]:
    return {str(r[1]) for r in c.execute(f"PRAGMA table_info({table})")}

def window(c: sqlite3.Connection, table: str, cutoff: str, gaps: list[str]) -> tuple[str, tuple[str, ...]] | None:
    preferred = {
        "decisions": ("planned_at", "started_at"),
        "executions": ("started_at",),
        "external_routes": ("started_at",),
        "task_usage_baselines": ("started_at",),
        "night_shift_reminders": ("reminded_at",),
        "hook_health": ("finished_at", "started_at"),
        "gate_injections": ("injected_at",),
    }.get(table, ("started_at", "finished_at"))
    name = next((x for x in preferred if x in cols(c, table)), None)
    if not name:
        gaps.append(f"表 {table} 缺少时间列，不能安全纳入最近窗口")
        return None
    return f" WHERE {name} >= ?", (cutoff,)

def n(c: sqlite3.Connection, table: str, where: str, args: tuple[Any, ...]) -> int:
    return int(c.execute(f"SELECT COUNT(*) FROM {table}{where}", args).fetchone()[0])

def local_version(gaps: list[str]) -> str | None:
    try:
        version = json.loads((ROOT/".codex-plugin/plugin.json").read_text(encoding="utf-8")).get("version")
        return str(version) if version else None
    except (OSError, ValueError, json.JSONDecodeError):
        gaps.append("无法从同一插件根 manifest 读取安装版本")
        return None

def safe_roles(values: list[object]) -> dict[str, int]:
    result = Counter()
    for value in values:
        text = str(value or "")
        result[text if text in OFFICIAL else "custom/unknown"] += 1
    return dict(result)

def db_summary(root: Path | None, cutoff: str, gaps: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {"version": local_version(gaps) or "证据不足", "gates": 0, "decisions": 0, "starts": 0, "attempts": [0,0,0], "routes": Counter(), "roles": {}, "failed": 0, "usage": [0,"证据不足","证据不足"], "night": {}, "update": "无记录", "hook": [0,0,"证据不足",{},[]], "errors": 0, "tables": False}
    if not root or not (root/"orchestration.db").is_file():
        gaps.append("指定的数据目录中没有 orchestration.db")
        return out
    try:
        with ro(root/"orchestration.db") as c:
            table_set = {str(r[0]) for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}; out["tables"] = True
            for table in ("gate_injections","decisions","executions","external_routes","task_usage_baselines","night_shift_reminders","update_state","hook_health"):
                if table not in table_set: gaps.append(f"缺少表 {table}（可能是旧版 schema）")
            if "gate_injections" in table_set and (w := window(c,"gate_injections",cutoff,gaps)):
                out["gates"] = n(c,"gate_injections",*w)
            if "decisions" in table_set and (w := window(c,"decisions",cutoff,gaps)):
                out["decisions"] = n(c,"decisions",*w); cs=cols(c,"decisions")
                if "tier" in cs: out["routes"].update(str(r[0]).lower() for r in c.execute(f"SELECT tier FROM decisions{w[0]} AND tier IS NOT NULL",w[1]))
            if "executions" in table_set and (w := window(c,"executions",cutoff,gaps)):
                out["starts"] = n(c,"executions",*w); cs=cols(c,"executions")
                if "actual_agent_type" in cs: out["roles"] = safe_roles([r[0] for r in c.execute(f"SELECT actual_agent_type FROM executions{w[0]}",w[1])])
            if "external_routes" in table_set and (w := window(c,"external_routes",cutoff,gaps)):
                total=n(c,"external_routes",*w); cs=cols(c,"external_routes")
                completed=n(c,"external_routes",w[0]+" AND stopped_at IS NOT NULL",w[1]) if "stopped_at" in cs else 0
                child=n(c,"external_routes",w[0]+" AND child_thread_id IS NOT NULL",w[1]) if "child_thread_id" in cs else 0
                out["attempts"]=[total,completed,child]
                if "status" in cs: out["failed"] += n(c,"external_routes",w[0]+" AND status IN ('failed','route_unavailable')",w[1])
            if "task_usage_baselines" in table_set and (w := window(c,"task_usage_baselines",cutoff,gaps)):
                cs=cols(c,"task_usage_baselines"); total=n(c,"task_usage_baselines",*w)
                if "baseline_available" in cs:
                    out["usage"] = [total, n(c,"task_usage_baselines",w[0]+" AND baseline_available=1",w[1]), n(c,"task_usage_baselines",w[0]+" AND baseline_available=0",w[1])]
                else:
                    out["usage"] = [total,"证据不足","证据不足"]
            if "night_shift_reminders" in table_set and (w := window(c,"night_shift_reminders",cutoff,gaps)):
                cs=cols(c,"night_shift_reminders")
                if "kind" in cs: out["night"] = dict(c.execute(f"SELECT kind,COUNT(*) FROM night_shift_reminders{w[0]} GROUP BY kind",w[1]))
            if "update_state" in table_set:
                cs=cols(c,"update_state")
                if {"singleton","checked_at","latest_version"}.issubset(cs):
                    row=c.execute("SELECT checked_at,latest_version FROM update_state WHERE singleton=1").fetchone()
                    if row and row[0]: out["update"] = f"检查尝试已记录；远端版本证据：{str(row[1]) if row[1] else '无'}"
                else: gaps.append("表 update_state 缺少诊断列")
            if "hook_health" in table_set and (w := window(c,"hook_health",cutoff,gaps)):
                cs=cols(c,"hook_health"); total=n(c,"hook_health",*w); fail=n(c,"hook_health",w[0]+" AND status!='ok'",w[1]) if "status" in cs else 0
                elapsed="证据不足"
                if "elapsed_ms" in cs:
                    row=c.execute(f"SELECT AVG(elapsed_ms) FROM hook_health{w[0]}",w[1]).fetchone(); elapsed=f"{float(row[0]):.1f}ms" if row and row[0] is not None else "无样本"
                events=dict(c.execute(f"SELECT event_name||'/'||status,COUNT(*) FROM hook_health{w[0]} GROUP BY event_name,status",w[1])) if {"event_name","status"}.issubset(cs) else {}
                versions=[str(r[0]) for r in c.execute(f"SELECT DISTINCT policy_version FROM hook_health{w[0]} AND policy_version IS NOT NULL",w[1])] if "policy_version" in cs else []
                out["hook"]=[total,fail,elapsed,events,versions]
    except (OSError,sqlite3.Error,ValueError) as e: gaps.append(f"无法只读打开 SQLite 数据：{type(e).__name__}")
    return out

def assistant_final(record: dict[str, Any]) -> tuple[str, str] | None:
    p=record.get("payload")
    if record.get("type")!="response_item" or not isinstance(p,dict) or p.get("type")!="message" or p.get("role")!="assistant" or p.get("phase")!="final_answer": return None
    content=p.get("content")
    metadata=p.get("internal_chat_message_metadata_passthrough")
    turn=str(metadata.get("turn_id") or "") if isinstance(metadata,dict) else ""
    if not turn or not isinstance(content,list): return None
    return turn, "\n".join(str(x.get("text") or "") for x in content if isinstance(x,dict) and x.get("type")=="output_text")

def rollout_summary(explicit: Path|None, cutoff: datetime, gaps: list[str]) -> dict[str,Any]:
    root=explicit.expanduser() if explicit else Path(os.environ.get("CODEX_HOME",Path.home()/".codex"))/"sessions"
    out={"files":0,"turns":0,"receipt_turns":0,"receipts":0,"duplicates":0,"routes":Counter(),"errors":0}
    if not root.is_dir(): gaps.append("未发现本地宿主 rollout；无法核对回执"); return out
    try: paths=list(root.rglob("*.jsonl"))
    except OSError: gaps.append("本地宿主 rollout 不可读取"); return out
    for path in paths:
        try:
            if path.stat().st_mtime < cutoff.timestamp(): continue
        except OSError:
            out["errors"]+=1; continue
        out["files"]+=1; turns=set(); receipts=Counter()
        try:
            for raw in path.open(encoding="utf-8",errors="replace"):
                try: r=json.loads(raw)
                except json.JSONDecodeError: out["errors"]+=1; continue
                p=r.get("payload")
                if r.get("type")=="event_msg" and isinstance(p,dict) and p.get("type")=="task_started":
                    turn=str(p.get("turn_id") or "")
                    if turn and (ts:=parse_time(r.get("timestamp"))) and ts>=cutoff: turns.add(turn)
                    continue
                final=assistant_final(r)
                if final is None: continue
                turn,text=final
                if turn not in turns: continue
                matches=EN_RECEIPT.findall(text)+ZH_RECEIPT.findall(text)
                if matches: receipts[turn]+=len(matches); out["routes"].update(ROUTE_NAMES.get(x.lower(), x.lower()) for x in matches)
        except OSError: out["errors"]+=1
        out["turns"]+=len(turns); out["receipt_turns"]+=len(receipts); out["receipts"]+=sum(receipts.values()); out["duplicates"]+=sum(max(0,x-1) for x in receipts.values())
    return out

def render(d:dict[str,Any],r:dict[str,Any],gaps:list[str],days:int,en:bool)->str:
    title="# Goldilocks local diagnostic report" if en else "# Goldilocks 本地诊断报告"
    privacy = (
        "Privacy: counts only; no prompts, content, secrets, complete IDs, paths, or transcript text."
        if en else "隐私：仅输出计数；不输出 prompt、内容、密钥、完整 ID、路径或完整 transcript。"
    )
    labels = {
        "window": "Window" if en else "覆盖窗口",
        "activity": "## Activity" if en else "## 活动统计",
        "version": "Installed version" if en else "本地安装版本",
        "gate": "Root-gate deliveries / host task_started turns (includes subagents and root tasks)" if en else "根门禁记录 / 宿主 task_started turn（含 subagent 与主任务）",
        "receipt": "Turns with final-answer receipt / receipts / duplicates" if en else "含 final-answer 回执 turn / 回执数 / 重复",
        "visible": "Visible receipt routes" if en else "可见回执路线",
        "decision": "Native route decisions / tiers" if en else "原生委派决策 / tier",
        "start": "Native employee starts / actual identities" if en else "原生 employee 启动 / 实际 identity",
        "external": "External attempts / completed / child-thread confirmed (not native starts)" if en else "external 尝试 / 已完成 / child-thread 已确认（不计入原生启动）",
        "failed": "Failed external records" if en else "失败 external 记录",
        "usage": "requests / available / unavailable" if en else "请求 / 可用 / 不可用",
        "update": "Update check attempt / remote-version evidence" if en else "更新检查尝试 / 远端版本证据",
        "health": "Hook health: rows / failures / average elapsed" if en else "Hook 健康：记录 / 失败 / 平均耗时",
        "errors": "Read errors" if en else "读取错误",
        "gaps": "## Evidence gaps" if en else "## 证据缺口",
    }
    rows = [
        title, "", privacy,
        f"{labels['window']}：{'recent ' if en else '最近 '}{days}{' days' if en else ' 天'}。",
        "", labels["activity"],
        f"- {labels['version']}：{d['version']}",
        f"- {labels['gate']}：{d['gates']} / {r['turns']}",
        f"- {labels['receipt']}：{r['receipt_turns']} / {r['receipts']} / {r['duplicates']}",
        f"- {labels['visible']}：{dict(r['routes']) or '证据不足'}",
        f"- {labels['decision']}：{d['decisions']} / {dict(d['routes']) or '证据不足'}",
        f"- {labels['start']}：{d['starts']} / {d['roles'] or '证据不足'}",
        f"- {labels['external']}：{' / '.join(map(str,d['attempts']))}",
        f"- {labels['failed']}：{d['failed']}",
        f"- Usage baseline {labels['usage']}：{' / '.join(map(str,d['usage']))}",
        f"- Night Shift：{d['night'] or '证据不足'}",
        f"- {labels['update']}：{d['update']}",
        f"- {labels['health']}：{' / '.join(map(str,d['hook'][:3]))}",
        f"- Hook event/status：{d['hook'][3] or '证据不足'}",
        f"- Hook policy version：{', '.join(d['hook'][4]) or '证据不足'}",
        f"- {labels['errors']}：{d['errors']+r['errors']}",
        "", labels["gaps"],
    ]
    return "\n".join(rows+([f"- {x}" for x in gaps] or ["- None detected" if en else "- 未发现"]))+"\n"

def main()->int:
    p=cli(); a=p.parse_args()
    if a.days<1: p.error("--days must be at least 1")
    gaps=[]; cutoff=datetime.now(timezone.utc)-timedelta(days=a.days); d=db_summary(data_root(a.data_dir,gaps),cutoff.isoformat(),gaps); r=rollout_summary(a.sessions_dir,cutoff,gaps); report=render(d,r,gaps,a.days,a.lang=="en")
    if a.output: a.output.expanduser().write_text(report,encoding="utf-8")
    else: sys.stdout.write(report)
    return 0
if __name__=="__main__": raise SystemExit(main())
