#!/usr/bin/env python3
"""Run five workflow arms against fresh agentic benchmark repositories."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import os
import random
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from tasks import TASKS, diff_stats, materialize, score_task, selftest as task_selftest, snapshot_repo


RUNS_DIR = HERE / "runs"
ARM_ORDER = ["baseline", "goldilocks", "superpowers", "ponytail", "grill"]
ARMS = {
    "baseline": "No non-system workflow Skill.",
    "goldilocks": "Goldilocks v0.2 compatibility suite; entries trigger as needed.",
    "superpowers": "Original Superpowers suite with using-superpowers bootstrap.",
    "ponytail": "Original Ponytail full mode on coding tasks.",
    "grill": "Original Matt Pocock grilling primitive on alignment tasks.",
}
DEFAULT_MODEL = "gpt-5.6-terra"
CELL_TIMEOUT = 420


def _env_path(name: str, fallback: Path) -> Path:
    return Path(os.environ.get(name, str(fallback))).expanduser().resolve()


def arm_skill_dirs(arm: str) -> list[Path]:
    siblings = ROOT.parent
    if arm == "baseline":
        return []
    if arm == "goldilocks":
        base = _env_path("GOLDILOCKS_SKILLS", ROOT / "plugins" / "goldilocks" / "skills")
        return sorted(path for path in base.iterdir() if (path / "SKILL.md").is_file()) if base.is_dir() else []
    if arm == "superpowers":
        base = _env_path("SUPERPOWERS_SKILLS", siblings / "superpowers-clean-baseline" / "skills")
        return sorted(path for path in base.iterdir() if (path / "SKILL.md").is_file()) if base.is_dir() else []
    if arm == "ponytail":
        path = _env_path("PONYTAIL_SKILL", siblings / "ponytail" / "skills" / "ponytail")
        return [path] if (path / "SKILL.md").is_file() else []
    if arm == "grill":
        path = _env_path(
            "GRILL_SKILL",
            siblings / "mattpocock-skills" / "skills" / "productivity" / "grilling",
        )
        return [path] if (path / "SKILL.md").is_file() else []
    raise KeyError(arm)


def arm_prefix(arm: str, task: dict[str, Any]) -> str:
    if arm == "superpowers":
        return "Use $using-superpowers and every applicable Superpowers workflow for this task."
    if arm == "ponytail" and task["track"] == "build":
        return "Use $ponytail full for this coding task."
    if arm == "grill" and task["track"] == "align":
        return "Use $grilling for this design decision."
    return ""


def codex_binary() -> str:
    override = os.environ.get("CODEX_BIN")
    if override:
        return override
    bundled = Path("/Applications/ChatGPT.app/Contents/Resources/codex")
    if bundled.is_file():
        return str(bundled)
    found = shutil.which("codex")
    if found:
        return found
    raise RuntimeError("Codex CLI not found; set CODEX_BIN")


def auth_home() -> Path:
    override = os.environ.get("THREE_BEARS_AUTH_HOME")
    if override:
        return Path(override).expanduser().resolve()
    configured = os.environ.get("CODEX_HOME")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / ".codex"


def prepare_codex_home(arm: str, home: Path) -> Path:
    codex_home = home / ".codex"
    skills_home = codex_home / "skills"
    skills_home.mkdir(parents=True, exist_ok=True)

    source_auth = auth_home()
    for filename in ("auth.json", "auth.chatgpt.json"):
        source = source_auth / filename
        target = codex_home / filename
        if source.is_file():
            try:
                target.symlink_to(source)
            except OSError:
                shutil.copy2(source, target)

    for source in arm_skill_dirs(arm):
        target = skills_home / source.name
        try:
            target.symlink_to(source, target_is_directory=True)
        except OSError:
            shutil.copytree(source, target)
    return codex_home


def discover_arm_skills(arm: str) -> tuple[bool, list[str]]:
    paths = arm_skill_dirs(arm)
    if arm == "baseline":
        return True, []
    expected = []
    for path in paths:
        metadata = path / "agents" / "openai.yaml"
        if metadata.is_file() and "allow_implicit_invocation: false" in metadata.read_text(encoding="utf-8"):
            continue
        expected.append(path.name)
    with tempfile.TemporaryDirectory(prefix=f"three-bears-discovery-{arm}-") as tmp_home:
        home = Path(tmp_home)
        codex_home = prepare_codex_home(arm, home)
        environment = os.environ.copy()
        environment.update({"HOME": str(home), "CODEX_HOME": str(codex_home), "NO_COLOR": "1"})
        try:
            result = subprocess.run(
                [codex_binary(), "debug", "prompt-input", "Three Bears skill discovery check."],
                capture_output=True,
                text=True,
                env=environment,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False, ["prompt-input timed out after 60s"]
    if result.returncode:
        return False, [f"prompt-input failed: {result.stderr.strip()[:160]}"]
    missing = [name for name in expected if name not in result.stdout]
    return not missing, missing


def _kill_tree(process: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except ProcessLookupError:
        pass


def parse_events(events_path: Path, stderr_path: Path) -> dict[str, Any]:
    final = ""
    thread_id = None
    usage: dict[str, int] = {}
    tool_calls = 0
    command_calls = 0
    skill_reads: set[str] = set()
    commands: list[str] = []

    if events_path.is_file():
        for raw in events_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "thread.started":
                thread_id = event.get("thread_id")
            item = event.get("item") or {}
            if event.get("type") == "item.completed":
                item_type = item.get("type")
                if item_type == "agent_message":
                    final = item.get("text", "")
                elif item_type == "command_execution":
                    tool_calls += 1
                    command_calls += 1
                    command = item.get("command", "")
                    commands.append(command)
                    for match in re.findall(r"/skills/([^/]+)/SKILL\.md", command):
                        skill_reads.add(match)
                elif item_type:
                    tool_calls += 1
            if event.get("type") == "turn.completed":
                usage = event.get("usage") or {}

    injected: set[str] = set()
    if stderr_path.is_file():
        stderr = stderr_path.read_text(encoding="utf-8", errors="ignore")
        for line in stderr.splitlines():
            if "codex.skill.injected" in line:
                match = re.search(r"invalid characters:\s*([a-z0-9-]+:[a-z0-9-]+)", line.lower())
                if match:
                    injected.add(match.group(1))

    input_tokens = int(usage.get("input_tokens") or 0)
    cached_tokens = int(usage.get("cached_input_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or 0)
    return {
        "thread_id": thread_id,
        "final": final,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "uncached_input_tokens": max(0, input_tokens - cached_tokens),
        "output_tokens": output_tokens,
        "reasoning_output_tokens": int(usage.get("reasoning_output_tokens") or 0),
        "total_tokens": input_tokens + output_tokens,
        "tool_calls": tool_calls,
        "command_calls": command_calls,
        "skill_reads": sorted(skill_reads),
        "skill_injections": sorted(injected),
        "skill_activity_count": len(skill_reads | {name.split(":")[-1] for name in injected}),
        "commands": commands,
        "question_marks": final.count("?") + final.count("？"),
        "final_words": len(final.split()),
    }


def shared_prompt(task_prompt: str, arm: str, task: dict[str, Any]) -> str:
    parts = [
        "You are working in a disposable local benchmark repository.",
        "Complete only the requested task. Inspect the repository before deciding.",
        "You may edit files and run local checks unless the task explicitly says not to edit.",
        "Do not use the network, install dependencies, commit, push, open a PR, or change external systems.",
    ]
    prefix = arm_prefix(arm, task)
    if prefix:
        parts.append(prefix)
    parts.append(task_prompt)
    return "\n\n".join(parts)


def run_cell(
    task_id: str,
    arm: str,
    model: str,
    reasoning: str,
    run_number: int,
    cell_dir: Path,
    timeout: int,
) -> dict[str, Any]:
    task = TASKS[task_id]
    repo = cell_dir / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    materialize(task_id, repo)
    snapshot_repo(repo)

    events_path = cell_dir / "events.jsonl"
    stderr_path = cell_dir / "stderr.txt"
    started = time.monotonic()
    timed_out = False
    returncode = None

    with tempfile.TemporaryDirectory(prefix=f"three-bears-{arm}-") as tmp_home:
        home = Path(tmp_home)
        codex_home = prepare_codex_home(arm, home)
        prompt = shared_prompt(task["prompt"], arm, task)
        command = [
            codex_binary(),
            "exec",
            "--ephemeral",
            "--ignore-rules",
            "--disable",
            "multi_agent",
            "-s",
            "workspace-write",
            "-c",
            'approval_policy="never"',
            "-c",
            f'model_reasoning_effort="{reasoning}"',
            "-m",
            model,
            "-C",
            str(repo),
            "--json",
            prompt,
        ]
        environment = os.environ.copy()
        environment.update(
            {
                "HOME": str(home),
                "CODEX_HOME": str(codex_home),
                "NO_COLOR": "1",
            }
        )
        with events_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                env=environment,
                start_new_session=(os.name != "nt"),
            )
            try:
                returncode = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                _kill_tree(process)
                try:
                    returncode = process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    returncode = -9

    duration = round(time.monotonic() - started, 3)
    telemetry = parse_events(events_path, stderr_path)
    score = score_task(task_id, repo, telemetry["final"])
    stats = diff_stats(repo)
    result = {
        "task": task_id,
        "level": task["level"],
        "track": task["track"],
        "arm": arm,
        "model": model,
        "reasoning": reasoning,
        "run": run_number,
        "returncode": returncode,
        "timed_out": timed_out,
        "duration_seconds": duration,
        **score,
        **stats,
        **telemetry,
    }
    (cell_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _median(records: list[dict[str, Any]], key: str):
    values = [record.get(key) for record in records if isinstance(record.get(key), (int, float))]
    return round(statistics.median(values), 3) if values else None


def aggregate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record.get("level", "unknown"), record.get("arm", "unknown"))].append(record)
        groups[("all", record.get("arm", "unknown"))].append(record)
    rows = []
    for (level, arm), cells in sorted(groups.items()):
        n = len(cells)
        rows.append(
            {
                "level": level,
                "arm": arm,
                "n": n,
                "quality_rate": round(sum(int(cell.get("quality", 0)) for cell in cells) / n, 3),
                "safe_rate": round(sum(int(cell.get("safe", 0)) for cell in cells) / n, 3),
                "scope_rate": round(sum(int(cell.get("scope", 0)) for cell in cells) / n, 3),
                "reuse_rate": round(sum(int(cell.get("reuse", 0)) for cell in cells) / n, 3),
                "process_rate": round(sum(int(cell.get("process", 0)) for cell in cells) / n, 3),
                "tokens_median": _median(cells, "total_tokens"),
                "uncached_tokens_median": _median(cells, "uncached_input_tokens"),
                "cached_tokens_median": _median(cells, "cached_input_tokens"),
                "duration_median": _median(cells, "duration_seconds"),
                "source_added_lines_median": _median(cells, "source_added_lines"),
                "test_added_lines_median": _median(cells, "test_added_lines"),
                "tool_calls_median": _median(cells, "tool_calls"),
                "skill_activity_median": _median(cells, "skill_activity_count"),
            }
        )
    return rows


def _format(value: Any, digits: int = 1) -> str:
    if value is None:
        return "-"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def print_summary(rows: list[dict[str, Any]]) -> None:
    for level in ("baby", "mama", "papa", "all"):
        selected = [row for row in rows if row["level"] == level]
        if not selected:
            continue
        print(f"\n=== {level.upper()} ===")
        print("  arm           n  quality safe reuse process tokens uncached  sec  +src tools skills")
        for row in sorted(selected, key=lambda item: ARM_ORDER.index(item["arm"])):
            print(
                f"  {row['arm']:<13} {row['n']:>2}  {row['quality_rate']:>7.3f} "
                f"{row['safe_rate']:>4.2f} {row['reuse_rate']:>5.2f} {row['process_rate']:>7.2f} "
                f"{_format(row['tokens_median'], 0):>6} {_format(row['uncached_tokens_median'], 0):>8} "
                f"{_format(row['duration_median']):>5} "
                f"{_format(row['source_added_lines_median'], 0):>5} {_format(row['tool_calls_median'], 0):>5} "
                f"{_format(row['skill_activity_median'], 0):>6}"
            )


def write_report(run_dir: Path, rows: list[dict[str, Any]], metadata: dict[str, Any]) -> None:
    lines = [
        "# Three Bears Benchmark Report",
        "",
        f"Run: `{metadata['date']}`  ",
        f"Model: `{metadata['model']}`  ",
        f"Reasoning: `{metadata['reasoning']}`  ",
        "",
        "Quality gates must be read before efficiency. Fewer tokens or lines do not count as a win when quality, safety, scope, reuse, or decision process drops.",
        "",
    ]
    for level in ("baby", "mama", "papa", "all"):
        selected = [row for row in rows if row["level"] == level]
        if not selected:
            continue
        lines.extend(
            [
                f"## {level.title()}",
                "",
                "| Arm | n | Quality | Safe | Scope | Reuse | Process | Median tokens | Median uncached input | Median cached input | Median seconds | Median source +LOC | Median test +LOC | Median tools | Median skills |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for row in sorted(selected, key=lambda item: ARM_ORDER.index(item["arm"])):
            lines.append(
                "| {arm} | {n} | {quality_rate:.3f} | {safe_rate:.3f} | {scope_rate:.3f} | "
                "{reuse_rate:.3f} | {process_rate:.3f} | {tokens} | {uncached} | {cached} | {seconds} | {loc} | {test_loc} | {tools} | {skills} |".format(
                    arm=row["arm"],
                    n=row["n"],
                    quality_rate=row["quality_rate"],
                    safe_rate=row["safe_rate"],
                    scope_rate=row["scope_rate"],
                    reuse_rate=row["reuse_rate"],
                    process_rate=row["process_rate"],
                    tokens=_format(row["tokens_median"], 0),
                    uncached=_format(row["uncached_tokens_median"], 0),
                    cached=_format(row["cached_tokens_median"], 0),
                    seconds=_format(row["duration_median"]),
                    loc=_format(row["source_added_lines_median"], 0),
                    test_loc=_format(row["test_added_lines_median"], 0),
                    tools=_format(row["tool_calls_median"], 0),
                    skills=_format(row["skill_activity_median"], 0),
                )
            )
        lines.append("")
    (run_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def git_sha(path: Path) -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=path, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def source_manifest(arms: list[str]) -> dict[str, Any]:
    manifest = {"goldilocks_repo": git_sha(ROOT), "arms": {}}
    for arm in arms:
        paths = arm_skill_dirs(arm)
        manifest["arms"][arm] = [{"path": str(path), "sha": git_sha(path)} for path in paths]
    return manifest


def validate_environment(arms: list[str], require_auth: bool) -> int:
    failures = task_selftest()
    try:
        binary = codex_binary()
        print(f"ok  codex                  {binary}")
    except RuntimeError as error:
        print(f"XX  codex                  {error}")
        failures += 1
    for arm in arms:
        paths = arm_skill_dirs(arm)
        okay = arm == "baseline" or bool(paths)
        print(f"{'ok ' if okay else 'XX '} arm source             {arm}: {len(paths)} skill dir(s)")
        failures += 0 if okay else 1
        if okay:
            discovered, missing = discover_arm_skills(arm)
            detail = "discoverable" if discovered else f"missing {missing}"
            print(f"{'ok ' if discovered else 'XX '} arm discovery          {arm}: {detail}")
            failures += 0 if discovered else 1
    if require_auth:
        present = any((auth_home() / name).is_file() for name in ("auth.json", "auth.chatgpt.json"))
        print(f"{'ok ' if present else 'XX '} auth                   {auth_home()}")
        failures += 0 if present else 1
    return failures


def rescore(run_dir: Path) -> None:
    run_dir = run_dir.resolve()
    records = []
    for cell in sorted(path for path in run_dir.iterdir() if path.is_dir()):
        parts = cell.name.split("__")
        if len(parts) != 4 or parts[0] not in TASKS:
            continue
        task_id, arm, model, raw_run = parts
        repo = cell / "repo"
        telemetry = parse_events(cell / "events.jsonl", cell / "stderr.txt")
        score = score_task(task_id, repo, telemetry["final"])
        stats = diff_stats(repo)
        old = {}
        if (cell / "result.json").is_file():
            old = json.loads((cell / "result.json").read_text(encoding="utf-8"))
        record = {
            **old,
            "task": task_id,
            "level": TASKS[task_id]["level"],
            "track": TASKS[task_id]["track"],
            "arm": arm,
            "model": model,
            "run": int(raw_run),
            **score,
            **stats,
            **telemetry,
        }
        (cell / "result.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        records.append(record)
    rows = aggregate(records)
    metadata_path = run_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.is_file() else {
        "date": run_dir.name,
        "model": records[0].get("model", "unknown") if records else "unknown",
        "reasoning": records[0].get("reasoning", "unknown") if records else "unknown",
    }
    (run_dir / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(run_dir, rows, metadata)
    print_summary(rows)
    print(f"\nrescored {len(records)} cells in {run_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Three Bears agentic workflow benchmark")
    parser.add_argument("--selftest", action="store_true", help="validate graders and available arm sources; no model calls")
    parser.add_argument("--dry-run", action="store_true", help="print the selected matrix; no model calls")
    parser.add_argument("--rescore", type=Path, help="recompute a kept run offline")
    parser.add_argument("--task", help="comma-separated task ids")
    parser.add_argument("--level", choices=["baby", "mama", "papa", "all"])
    parser.add_argument("--arms", default=",".join(ARM_ORDER), help="comma-separated workflow arms")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--reasoning", default="low")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=CELL_TIMEOUT)
    parser.add_argument("--seed", type=int, default=1729, help="deterministically randomize cell order")
    args = parser.parse_args()

    if args.rescore:
        return rescore(args.rescore)

    arms = [arm.strip() for arm in args.arms.split(",") if arm.strip()]
    unknown_arms = set(arms) - set(ARMS)
    if unknown_arms:
        parser.error(f"unknown arms: {sorted(unknown_arms)}")

    if args.selftest:
        raise SystemExit(1 if validate_environment(arms, require_auth=False) else 0)

    if args.task:
        task_ids = [task.strip() for task in args.task.split(",") if task.strip()]
    elif args.level:
        task_ids = [task_id for task_id, task in TASKS.items() if args.level == "all" or task["level"] == args.level]
    else:
        parser.error("select --task <ids> or --level baby|mama|papa|all")
    unknown_tasks = set(task_ids) - set(TASKS)
    if unknown_tasks:
        parser.error(f"unknown tasks: {sorted(unknown_tasks)}")

    cells = [
        (task_id, arm, run_number)
        for task_id in task_ids
        for arm in arms
        for run_number in range(args.runs)
    ]
    random.Random(args.seed).shuffle(cells)
    if args.dry_run:
        print(f"model={args.model} reasoning={args.reasoning} cells={len(cells)}")
        for task_id, arm, run_number in cells:
            active = bool(arm_prefix(arm, TASKS[task_id])) or arm == "goldilocks"
            print(f"  {task_id:24} {arm:13} run={run_number} available={str(active).lower()}")
        raise SystemExit(1 if validate_environment(arms, require_auth=False) else 0)

    if validate_environment(arms, require_auth=True):
        raise SystemExit("environment invalid; refusing to spend model calls")

    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / stamp
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {
        "date": stamp,
        "model": args.model,
        "reasoning": args.reasoning,
        "runs": args.runs,
        "workers": args.workers,
        "timeout": args.timeout,
        "seed": args.seed,
        "tasks": task_ids,
        "arms": arms,
        "sources": source_manifest(arms),
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"running {len(cells)} isolated cells with {args.workers} worker(s) -> {run_dir}", flush=True)
    records: list[dict[str, Any]] = []

    def execute(spec: tuple[str, str, int]) -> dict[str, Any]:
        task_id, arm, run_number = spec
        safe_model = re.sub(r"[^a-zA-Z0-9_.-]+", "-", args.model)
        cell = run_dir / f"{task_id}__{arm}__{safe_model}__{run_number}"
        cell.mkdir(parents=True, exist_ok=False)
        return run_cell(task_id, arm, args.model, args.reasoning, run_number, cell, args.timeout)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {pool.submit(execute, cell): cell for cell in cells}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            task_id, arm, run_number = futures[future]
            try:
                record = future.result()
            except Exception as error:
                record = {
                    "task": task_id,
                    "level": TASKS[task_id]["level"],
                    "track": TASKS[task_id]["track"],
                    "arm": arm,
                    "model": args.model,
                    "reasoning": args.reasoning,
                    "run": run_number,
                    "quality": 0,
                    "correct": 0,
                    "safe": 0,
                    "scope": 0,
                    "reuse": 0,
                    "process": 0,
                    "error": str(error),
                }
            records.append(record)
            print(
                f"  [{index}/{len(cells)}] {task_id} / {arm} "
                f"quality={record.get('quality')} tokens={record.get('total_tokens', 0)} "
                f"time={record.get('duration_seconds', 0)}s +src={record.get('source_added_lines', 0)}",
                flush=True,
            )
            (run_dir / "results.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    rows = aggregate(records)
    (run_dir / "summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(run_dir, rows, metadata)
    print_summary(rows)
    print(f"\nwrote {run_dir / 'results.json'}, summary.json, and REPORT.md")


if __name__ == "__main__":
    main()
