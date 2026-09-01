#!/usr/bin/env python3

"""Inject a tiny response contract and continuity guidance when needed."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from native_terminal import read_terminal_state


POLICY_VERSION = "0.5.3-beta.8"
ROUTING_EXPERIMENT_ID = "routing-rationale-v3.2"
GLOBAL_GRANT_KEY = "__global__"
HOOK_HEALTH_TTL_DAYS = 30
HOOK_HEALTH_TABLE = "hook_health"
MICRO_STYLE = (
    "Lead with the result. Omit work preambles, repeated plans/status/recaps, tangents, and "
    "long logs. Report only changed state and decisive evidence; expand for safety/ambiguity. "
    "For defects: evidence-backed cause—or explicitly unknown—fix and verification; expand when asked."
)
ROUTING_GATE = (
    "For executable work, silently apply the Goldilocks zero-cost gate before specialist Skills. "
    "Clear bounded work takes Direct without loading goldilocks:goldilocks or its references. "
    "Load it only for unresolved ambiguity/cause, required continuity, or delegation/artifact "
    "decomposition whose implementation gain clearly exceeds briefing, review, and integration. "
    "Visible multi-unit implementation runs make-or-delegate before Lead edits; Direct remains valid "
    "when transfer cost is higher. Skip pure conversation."
)
MINIMUM_SUFFICIENT_VERIFICATION = (
    "Minimum-sufficient verification: in one first call, guard optional files (`[ -f \"$f\" ]`) while reading existing "
    "instructions/relevant source/tests and metadata or `python3 --version`; no second discovery. Treat that runtime as "
    "the syntax floor (Python <3.10: no `X | None`). One fail-propagating evidence call: applicable tests, one "
    "uncovered probe, diff/status; derive expectations first. Skip compile when tests/CLI import changes. Reuse checks; "
    "no new hash/freeze/baseline/gate without a named escaping failure. After product repair rerun only failed/affected "
    "checks; fix faulty probes without product changes "
    "or equivalent checks. Recurring unknowns mean "
    "diagnose, not retry. Preserve safeguards; auth/data/irreversible/release remain risk-based."
)
VISIBLE_RESPONSE_CONTRACT_EN = (
    "Every executable task, Direct included (`ROUTE=direct`), shows once in its first work update: "
    "`Goldilocks | Active: <selected or observed action>`. Merge restore/route/delegation/fallback, "
    "Night Shift, Usage/update, or acceptance events into updates; no audit dump. Without intermediate updates, "
    "put the action in final DETAIL. End with exactly one localized receipt in this exact field order: "
    "`ROUTE=<direct|fast|standard|mixed> | TEAM=<main model and actually started roles> | "
    "CONCURRENCY=<host-confirmed starts/host limit or ?> | DELEGATED=<actual delegated work or none> | "
    "REASON=<short reason> | DETAIL=<one factual sentence>`. DETAIL reports only Goldilocks actions that affected work. "
    "TEAM root is `main model`, never Codex/primary agent; list only actual started roles. CONCURRENCY counts host-confirmed child starts: "
    "none is 0, never 1 for the main model. Usage is host-side and fail-silent: on-demand by default; "
    "Bootstrap automatic opt-in runs once per executable task. Pure conversation has no persistent activity cue, receipt, or Usage."
)
VISIBLE_RESPONSE_CONTRACT_ZH = (
    "每个可执行任务（包括直接路径 `路由=直接`）在第一次工作更新显示一次本地化活动行："
    "`Goldilocks｜已启用：<一个已经选定或观察到、与本任务有关的真实动作>`。只写真实发生的 Direct 门、连续性恢复、"
    "路由/委派/回退、Night Shift、用量/更新提醒或终验；后续事件合并进正常更新，不倾倒原始审计日志。若不需要中间更新，"
    "只在最终详情承载该动作。最终必须有且仅有一次本地化、用户可见的 Goldilocks 路由回执，字段顺序固定："
    "`路由=<直接|快速|标准|混合>｜团队=<主模型及实际启动角色>｜并发=<宿主确认启动数/宿主上限或?>｜"
    "委派=<实际委派任务或无>｜理由=<简短理由>｜详情=<一句事实>`。详情必须说明实际发生的 Goldilocks 动作，不写未调用能力。"
    "团队根身份只写 `主模型`，不得写 Codex/主代理；并发只数宿主确认启动的子智能体，未启动子智能体就是 0，绝不把主模型计为 1。"
    "用量由宿主侧静默处理：默认按需；Bootstrap 启用自动模式后，"
    "每个可执行任务自动读取一次；按需模式只在用户明确索要时读取。纯对话不显示持久活动行、回执或用量。"
)
USAGE_VISIBILITY_MODES = {"on-demand", "automatic"}


def usage_visibility_mode() -> str:
    """Resolve Bootstrap's portable preference without making hook delivery depend on it."""

    override = os.environ.get("GOLDILOCKS_USAGE_VISIBILITY", "").strip().lower()
    if override in USAGE_VISIBILITY_MODES:
        return override
    configured = os.environ.get("GOLDILOCKS_BOOTSTRAP_STATE_DIR")
    if configured:
        state_dir = Path(configured).expanduser()
    elif os.name == "nt":
        state_dir = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "goldilocks-bootstrap"
    else:
        state_dir = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "goldilocks-bootstrap"
    preference = state_dir / "usage-visibility.json"
    try:
        if preference.is_symlink() or not preference.is_file():
            return "on-demand"
        value = json.loads(preference.read_text(encoding="utf-8"))
        mode = value.get("mode") if isinstance(value, dict) else None
        return mode if mode in USAGE_VISIBILITY_MODES else "on-demand"
    except (OSError, ValueError, TypeError):
        return "on-demand"


DIRECT_USAGE_QUERY_PATTERN = re.compile(
    r"(?:\b(?:show|display|report|check|give|current|how many|what(?:'s| is))\b.{0,32}"
    r"\b(?:usage|tokens?|token count)\b|\b(?:usage|tokens?|token count)\b.{0,24}"
    r"\b(?:now|current|please)\b|(?:显示|查看|报告|告诉|当前|本次|多少).{0,16}"
    r"(?:用量|token|令牌)|(?:用量|token|令牌).{0,8}(?:多少|是多少|情况|统计))",
    re.IGNORECASE,
)
USAGE_FEATURE_DISCUSSION_PATTERN = re.compile(
    r"(?:\b(?:usage|tokens?)\b.{0,32}\b(?:feature|automatic|on[ -]?demand|bootstrap|"
    r"enable|setting|preference|design|work)\b|\b(?:how does|should (?:we|i)|"
    r"discuss)\b.{0,32}\b(?:usage|tokens?)\b|(?:用量|token|令牌).{0,24}"
    r"(?:功能|自动|按需|Bootstrap|启用|设置|偏好|设计|讨论))",
    re.IGNORECASE,
)


def direct_usage_query(prompt: str) -> bool:
    return bool(DIRECT_USAGE_QUERY_PATTERN.search(prompt)) and not bool(
        USAGE_FEATURE_DISCUSSION_PATTERN.search(prompt)
    )


USAGE_EXECUTABLE_REQUEST_PATTERN = re.compile(
    r"(?:翻译|翻成|撰写|写(?:一|个|份)?|审查|评审|分析|诊断|总结|概括|摘要|搜索|查找|检索|"
    r"比较|对比|构建|编译|编辑|修改|修复|实现|开发|创建|测试|部署|发布|安装|升级)|"
    r"\b(?:translate|write|draft|review|audit|analy[sz]e|diagnose|summari[sz]e|search|compare|"
    r"build|compile|edit|change|fix|implement|develop|create|test|deploy|release|install|upgrade)\b|"
    r"\b(?:provide|give|need|want|request|help(?:\s+me)?\s+with)"
    r"\s+(?:(?:a|an)\s+)?(?:translation|writing|analysis|review|summary|search|comparison)\b",
    re.IGNORECASE,
)
PURE_USAGE_DISCUSSION_PATTERN = re.compile(
    r"(?:\bwhat do you think about\b|\bjust discuss(?:\s+(?:this|it|that))?\b|"
    r"\blet'?s discuss\b|\b(?:can|could|should)\s+(?:we|i)\s+discuss\b|"
    r"\bdiscuss(?:ing)?\s+(?:how|whether|the (?:feature|setting|idea|practice))\b|"
    r"\b(?:explain|describe|clarify|introduce|teach|what is|how (?:does|do|is))\b|"
    r"\bwhat are (?:the )?(?:benefits|advantages|pros) of\b|\bi (?:think|believe|feel)\b|"
    r"\b(?:is|are)\s+(?:code\s+)?review\b.{0,48}\b(?:good|useful|worth|best practice)\b|"
    r"(?:你觉得|你怎么看).{0,48}(?:讨论|聊聊)|(?:只|先).{0,6}(?:讨论|聊聊)|"
    r"(?:讨论|聊聊).{0,32}(?:如何|怎么|是否|要不要|功能|设置|实践)|"
    r"(?:解释|说明|介绍).{0,48}|(?:我觉得|我认为|我想).{0,48}(?:审查|评审)|"
    r"(?:代码|同行|同伴)审查.{0,24}(?:好处|优点|益处|好吗|好不好|是否值得))",
    re.IGNORECASE,
)
USAGE_FOLLOW_ON_WORK_PATTERN = re.compile(
    r"(?:[,，;；.!?。]\s*(?:then\s+)?|\b(?:and|then)\s+)(?:please\s+)?(?:translate|write|draft|review|audit|"
    r"analy[sz]e|diagnose|summari[sz]e|search|compare|build|compile|edit|change|fix|"
    r"implement|develop|create|test|deploy|release|install|upgrade)\b|"
    r"(?:[,，;；。]\s*|并|然后|再).{0,16}(?:翻译|撰写|审查|分析|诊断|总结|搜索|查找|检索|比较|对比|"
    r"构建|编译|编辑|修改|修复|实现|开发|创建|测试|部署|发布|安装|升级)",
    re.IGNORECASE,
)


def usage_reporter_command(turn_id: str | None, zh: bool) -> str:
    """Build one shell-portable Python command with no versioned cache path."""

    safe_turn = turn_id if re.fullmatch(r"[A-Za-z0-9_.:-]+", turn_id or "") else ""
    launcher = "py -3" if os.name == "nt" else "python3"
    arguments = f"'--current','--turn-id','{safe_turn}'"
    if zh:
        arguments += ",'--language','zh'"
    program = (
        "import json,runpy,subprocess,sys; from pathlib import Path; "
        "p=json.loads(subprocess.check_output(['codex','plugin','list','--json'])); "
        "r=Path(next(x for x in p.get('installed',[]) if x.get('enabled') and "
        "(str(x.get('name') or '').lower()=='goldilocks' or "
        "str(x.get('pluginId') or '').lower().startswith('goldilocks@')))['source']['path'])/"
        "'scripts'/'usage_reporter.py'; "
        f"sys.argv=[str(r),{arguments}]; runpy.run_path(str(r),run_name='__main__')"
    )
    return f'{launcher} -c "{program}"'


def usage_requirements(prompt: str) -> tuple[bool, bool, bool]:
    """Classify visible Usage without treating an opinion prompt as executable work."""

    requested = direct_usage_query(prompt)
    automatic = (
        usage_visibility_mode() == "automatic"
        and USAGE_EXECUTABLE_REQUEST_PATTERN.search(prompt) is not None
        and not USAGE_FEATURE_DISCUSSION_PATTERN.search(prompt)
        and (
            not PURE_USAGE_DISCUSSION_PATTERN.search(prompt)
            or USAGE_FOLLOW_ON_WORK_PATTERN.search(prompt) is not None
        )
    )
    return requested, automatic, primary_language_is_zh(prompt)


def usage_instruction_for(
    turn_id: str | None, requested: bool, automatic: bool, zh: bool
) -> str:
    """Return one runnable, fail-silent current-Usage instruction for a recorded turn."""

    if not requested and not automatic:
        return ""
    command = usage_reporter_command(turn_id, zh)
    trigger = "Automatic visible Usage is enabled" if automatic and not requested else "Current Usage was requested"
    return (
        f"{trigger}: resolve the enabled plugin with `codex plugin list --json`, then immediately "
        f"before the final response run `{command}` exactly once; "
        "append nonempty output, and on empty output or failure omit Usage without retrying or debugging."
    )


def usage_instruction(prompt: str, turn_id: str | None) -> str:
    """Return one runnable, fail-silent current-Usage request when it was requested."""

    return usage_instruction_for(turn_id, *usage_requirements(prompt))
ROUTING_RATIONALE_GATE = (
    "Multi-unit work: before Lead edits, run one make-or-delegate check; write one canonical ROUTE HTML comment "
    "with WRITE_READY, READ_READY, EXISTING, PLANNED_DISPATCH, LEAD, REASON, and DETAIL. EXISTING is "
    "current host-confirmed running ownership—not UI labels, idle/completed handles, artifacts, or a "
    "historical task_started; collect finals via host wait/status. PLANNED_DISPATCH is intent; Hooks "
    "count starts. After attempts, show one primary-language receipt: TEAM/CONCURRENCY use host-confirmed "
    "starts/active workers, never planned; capacity is ? when unknown. Root Direct uses the compact "
    "visible response contract without loading orchestration references. Small files need no route-card/kernel; "
    "load only if delegation may pay or compact fields fail. route_unavailable needs retained native/Adapter "
    "start-failure evidence; zero-attempt/plan-only uses "
    "the actual Direct reason. Shared writes permit "
    "reads. Direct names transfer cost. Audit is silent; create no "
    "extra proof, probe, document, test, or model call. Spawn self-check—native hosts may bypass PreToolUse: "
    "Luna/Spark=`fast__<semantic>_<model>`,fork_turns=none; Terra=`standard__<semantic>_<model>`,none/1-4; "
    "SolReviewer=`lead__<semantic>_<model>`,none,fresh review-only/no write/repair/delegate. Host permissions "
    "stay unchanged; only explicit Lead handoff permits `all`. Spark-quota-failed: no retry until observed "
    "reset; compare Terra/Luna/Direct; explain main-model takeover."
)
AUTHORIZED_DISPATCH_GATE = (
    "Bounded-delegation grant active, not quota. Compare official input/cached/output rates, time/raw, "
    "acceptance, retry; cheaper may be slower; unknown pools stay separate. Fast-check ready "
    "unit before Standard. Luna uses dispatch_codex_worker.py if native omits it; absence alone ≠ "
    "route_unavailable. All-Terra DETAIL names Fast blocker: judgment/tools/authority/acceptance. "
    "New-model discovery is read-only; first use needs persistent explicit authorization."
)
CONTINUITY_GATE = (
    "Repeated-failure continuity boundary detected. Before another fix, read the Goldilocks "
    "continuity.md reference; create or update one .goldilocks/ACTIVE.md frontier and the "
    "project's existing debug/validation record (or docs/debug/). Preserve symptom, evidence, "
    "disproven attempts, Do not repeat, exact next test, and related commits. "
    "Keep unverified work out of CHANGELOG; after fresh verification, record only user-visible "
    "release changes."
)
NEGATED_FAILURE_PATTERNS = (
    re.compile(r"(?:不用|不要|无需|不需要)(?:再)?(?:回退|撤回)"),
    re.compile(r"(?:没|没有|未|不会)(?:再)?(?:出现)?(?:问题|错误|异常|失败)"),
)
REPEAT_FAILURE_PATTERNS = (
    re.compile(
        r"(?:依旧|仍然|还是|又|再次|反复|重复).{0,16}"
        r"(?:不行|不能|无法|失败|没解决|没有解决|未解决|没修好|错误|报错|异常|"
        r"出问题|(?<!没)(?<!没有)有问题|无效|失效|坏了|又断了|再次出现)"
    ),
    re.compile(
        r"(?:没解决|没有解决|(?<!不用)(?<!不要)(?<!无需)回退|"
        r"(?<!不用)(?<!不要)(?<!无需)撤回|同样的问题|相同问题)"
    ),
    re.compile(r"(?:问题|错误|故障).{0,8}(?:又|再次).{0,8}(?:出现|发生)"),
    re.compile(
        r"\b(?:still (?:fail(?:s|ed|ing)?|broken|wrong|not fixed|not working|cannot|can't)|"
        r"still (?:doesn't|isn't) work(?:ing)?|"
        r"failed again|same (?:bug|issue|problem)|not fixed|didn't work|doesn't work|"
        r"keeps? (?:failing|breaking)|regression|revert(?:ed)?|roll(?:ed)? back)\b",
        re.IGNORECASE,
    ),
)
NUMBERED_UNIT_PATTERN = re.compile(
    r"(?m)^\s*(?:\d{1,2}[、.)）]|[-*]\s+(?:修复|修改|实现|完成|增加|添加|测试|"
    r"发布|部署|fix|change|implement|add|test|deploy|release)\b)",
    re.IGNORECASE,
)
MULTI_UNIT_PHRASE_PATTERN = re.compile(
    r"(?:以下|这些|多个|多项|逐项|一并|全部|所有).{0,12}"
    r"(?:问题|缺陷|任务|功能|改动|修复|完成)|"
    r"\b(?:multiple|several|all|each).{0,24}(?:bugs?|issues?|tasks?|features?|changes?)\b",
    re.IGNORECASE,
)
EXECUTION_PATTERN = re.compile(
    r"(?:修复|修改|实现|开发|完成|增加|添加|测试|构建|发布|部署)|"
    r"\b(?:fix|change|implement|develop|complete|add|test|build|release|deploy)\b",
    re.IGNORECASE,
)
SINGLE_UNIT_PATTERN = re.compile(
    r"(?:单一|单个|一个).{0,16}(?:实现|开发|任务|改动|单元)|"
    r"\b(?:single|one)\s+(?:local\s+)?(?:cohesive\s+)?"
    r"(?:implementation\s+)?(?:unit|task|change)\b",
    re.IGNORECASE,
)
NIGHT_SHIFT_COMMAND_PATTERN = re.compile(
    r"(?:(?:请|这次|就)?\s*(?:用|使用|启用|选择|按)\s*(?:night\s*shift|夜班|挂机班))|"
    r"(?:(?:night\s*shift|夜班|挂机班)(?:模式)?\s*(?:跑|运行|执行|处理))|"
    r"\b(?:use|enable|choose|run)\s+(?:the\s+)?night\s*shift\b",
    re.IGNORECASE,
)
WAITABLE_PATTERN = re.compile(
    r"(?:可以等|不着急|明天|过夜|晚点|can\s+wait|not\s+urgent|overnight|"
    r"latency[ -]?tolerant)",
    re.IGNORECASE,
)
COST_PRIORITY_PATTERN = re.compile(
    r"(?:成本优先|省钱|预算|cost\s*(?:first|priority)|budget|cheaper|economy)",
    re.IGNORECASE,
)
URGENT_PATTERN = re.compile(r"(?:紧急|马上|立刻|截止|urgent|asap|deadline)", re.IGNORECASE)
CODING_PATTERN = re.compile(
    r"(?:代码|编码|开发|实现|修复|bug|测试|code|coding|implement|fix|build|test)",
    re.IGNORECASE,
)
DOCUMENT_PATTERN = re.compile(
    r"(?:文档|方案|报告|总结|调研|写作|document|proposal|report|research|writing)",
    re.IGNORECASE,
)
CONVERSATION_PATTERN = re.compile(
    r"(?:聊聊|讨论|解释|介绍|怎么看|什么是|是否可行|是否启用|要不要启用|想问|"
    r"talk about|discuss|explain|what is|how does|should\s+(?:we|i)\s+enable|"
    r"whether\s+to\s+enable)",
    re.IGNORECASE,
)


def stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def workspace_root(cwd: Path) -> Path:
    for directory in (cwd, *cwd.parents):
        if (directory / ".git").exists():
            return directory
    return cwd


def _now_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_identity(payload: dict[str, object], key: str, fallback: str) -> str:
    return stable_hash(str(payload.get(key, fallback)))


def _plugin_data() -> Path | None:
    configured = os.environ.get("PLUGIN_DATA")
    if not configured:
        return None
    root = Path(configured).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _ensure_health_schema(connection: sqlite3.Connection) -> None:
    table_exists = (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?",
            (HOOK_HEALTH_TABLE,),
        ).fetchone()
        is not None
    )
    if not table_exists:
        connection.execute(
            f"""
            CREATE TABLE {HOOK_HEALTH_TABLE} (
                event_name TEXT NOT NULL,
                session_id_hash TEXT NOT NULL,
                turn_id_hash TEXT NOT NULL,
                event_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                elapsed_ms INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL,
                policy_version TEXT NOT NULL DEFAULT '{POLICY_VERSION}'
            )
            """
        )
    columns = {
        str(row[1]) for row in connection.execute(f"PRAGMA table_info({HOOK_HEALTH_TABLE})")
    }
    if "elapsed_ms" not in columns:
        connection.execute(f"ALTER TABLE {HOOK_HEALTH_TABLE} ADD COLUMN elapsed_ms INTEGER NOT NULL DEFAULT 0")
    if "policy_version" not in columns:
        connection.execute(
            f"ALTER TABLE {HOOK_HEALTH_TABLE} "
            f"ADD COLUMN policy_version TEXT NOT NULL DEFAULT '{POLICY_VERSION}'"
        )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS hook_health_cleanup_idx ON "
        f"{HOOK_HEALTH_TABLE} (finished_at)"
    )


def _elapsed_ms(started_at: str, finished_at: str) -> int:
    try:
        started = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
        finished = datetime.fromisoformat(finished_at.replace("Z", "+00:00"))
        return max(0, int((finished - started).total_seconds() * 1000))
    except (TypeError, ValueError, ArithmeticError):
        return 0


def _prune_hook_health(connection: sqlite3.Connection, cutoff: str) -> None:
    connection.execute(
        f"DELETE FROM {HOOK_HEALTH_TABLE} WHERE finished_at < ?",
        (cutoff,),
    )


def _record_hook_health(
    payload: dict[str, object],
    event: str,
    status: str,
    started_at: str,
) -> None:
    if status not in {"ok", "error"}:
        return
    try:
        root = _plugin_data()
        if root is None:
            return
        connection = sqlite3.connect(root / "orchestration.db", timeout=3)
        try:
            connection.execute("PRAGMA busy_timeout = 3000")
            connection.execute("PRAGMA journal_mode = WAL")
            _ensure_health_schema(connection)
            session_id_hash = _hash_identity(payload, "session_id", "unknown-session")
            turn_id_hash = _hash_identity(payload, "turn_id", "unknown-turn")
            event_id = stable_hash(f"{event}\n{session_id_hash}\n{turn_id_hash}")
            now = _now_isoformat()
            connection.execute(
                f"""
                INSERT INTO {HOOK_HEALTH_TABLE} (
                    event_name, session_id_hash, turn_id_hash, event_id,
                    started_at, finished_at, elapsed_ms, status, policy_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET
                    elapsed_ms = excluded.elapsed_ms,
                    finished_at = excluded.finished_at,
                    status = excluded.status,
                    policy_version = excluded.policy_version
                """,
                (
                    event,
                    session_id_hash,
                    turn_id_hash,
                    event_id,
                    started_at,
                    now,
                    _elapsed_ms(started_at, now),
                    status,
                    POLICY_VERSION,
                ),
            )
            cutoff = (
                datetime.now(timezone.utc) - timedelta(days=HOOK_HEALTH_TTL_DAYS)
            ).isoformat()
            _prune_hook_health(connection, cutoff)
            connection.commit()
        finally:
            connection.close()
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return


def repeat_failure_signal(prompt: str) -> bool:
    candidate = prompt
    for pattern in NEGATED_FAILURE_PATTERNS:
        candidate = pattern.sub("", candidate)
    return any(pattern.search(candidate) is not None for pattern in REPEAT_FAILURE_PATTERNS)


def routing_rationale_signal(prompt: str) -> bool:
    if len(NUMBERED_UNIT_PATTERN.findall(prompt)) >= 2:
        return True
    if EXECUTION_PATTERN.search(prompt) and MULTI_UNIT_PHRASE_PATTERN.search(prompt):
        return True
    if SINGLE_UNIT_PATTERN.search(prompt):
        return False
    return False


def primary_language_is_zh(prompt: str) -> bool:
    return len(re.findall(r"[\u3400-\u9fff]", prompt)) > len(re.findall(r"[A-Za-z]", prompt)) / 3


def night_shift_kind(prompt: str) -> str | None:
    """Classify an observable Night Shift intent; never select a model automatically."""

    if not EXECUTION_PATTERN.search(prompt):
        return None
    # A discussion or a question about the mode is never consent to use it.
    if CONVERSATION_PATTERN.search(prompt):
        return None
    explicit = NIGHT_SHIFT_COMMAND_PATTERN.search(prompt) is not None
    waitable = WAITABLE_PATTERN.search(prompt) is not None
    if explicit:
        return "explicit_spark" if URGENT_PATTERN.search(prompt) and CODING_PATTERN.search(prompt) else "explicit_luna"
    if (
        waitable
        and COST_PRIORITY_PATTERN.search(prompt)
        and (DOCUMENT_PATTERN.search(prompt) or CODING_PATTERN.search(prompt))
    ):
        return "suggestion"
    return None


def night_shift_message(kind: str, zh: bool) -> str:
    if zh:
        if kind == "suggestion":
            return (
                "Night Shift 建议：此任务看起来可无人值守且成本优先；如你同意，可选夜班模式。"
                "这是建议，不切换模型、不阻塞当前执行，也不会在本会话/工作区重复提示。"
            )
        if kind == "explicit_spark":
            return (
                "Night Shift 已选择：这是紧急且确定性的编码工作，优先 Spark XHigh。先尝试原生员工；"
                "原生不可见时先用 Adapter；仅在实际启动失败后才可标记 route_unavailable 并回退。"
            )
        return (
            "Night Shift 已选择：普通经济型通用/文档工作优先 Luna Max。先尝试原生员工；"
            "原生不可见时先用 Adapter；仅在实际启动失败后才可标记 route_unavailable 并回退。"
        )
    if kind == "suggestion":
        return (
            "Night Shift suggestion: this looks unattended and cost-first; offer the mode if useful. "
            "This is non-blocking, does not switch models, and is not repeated for this session/workspace."
        )
    if kind == "explicit_spark":
        return (
            "Night Shift selected: urgent deterministic coding prefers Spark XHigh. Try the native employee first; "
            "if it is not visible, try the adapter; only an observed start failure may become route_unavailable and fall back."
        )
    return (
        "Night Shift selected: ordinary economy general/document work prefers Luna Max. Try the native employee first; "
        "if it is not visible, try the adapter; only an observed start failure may become route_unavailable and fall back."
    )


def night_shift_context(payload: dict[str, object], cwd: Path, prompt: str) -> str:
    """Persist a once-only Night Shift hint without storing prompt text or blocking delivery."""

    kind = night_shift_kind(prompt)
    if kind is None:
        return ""
    zh = primary_language_is_zh(prompt)
    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return night_shift_message(kind, zh)
        root = Path(configured).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(root / "orchestration.db", timeout=3) as connection:
            connection.execute("PRAGMA busy_timeout = 3000")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS night_shift_reminders (
                    session_id TEXT NOT NULL,
                    cwd_hash TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    reminded_at TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    PRIMARY KEY (session_id, cwd_hash, kind)
                )
                """
            )
            cursor = connection.execute(
                "INSERT OR IGNORE INTO night_shift_reminders "
                "(session_id, cwd_hash, kind, reminded_at, policy_version) VALUES (?, ?, ?, ?, ?)",
                (
                    str(payload.get("session_id") or "unknown-session"),
                    stable_hash(str(workspace_root(cwd))),
                    kind,
                    datetime.now(timezone.utc).isoformat(),
                    POLICY_VERSION,
                ),
            )
            if cursor.rowcount == 0:
                return ""
    except (OSError, sqlite3.Error, TypeError, ValueError):
        # Auditing is advisory only. Preserve the intent even when persistence is unavailable.
        return night_shift_message(kind, zh)
    return night_shift_message(kind, zh)


def visible_response_contract(
    prompt: str, turn_id: str | None, language: str | None = None
) -> str:
    zh = language == "zh" if language in {"en", "zh"} else primary_language_is_zh(prompt)
    value = VISIBLE_RESPONSE_CONTRACT_ZH if zh else VISIBLE_RESPONSE_CONTRACT_EN
    turn_arg = f"--turn-id {turn_id}" if turn_id else ""
    return value.replace("{turn_arg}", turn_arg).replace("  ", " ")


def latest_turn_id(payload: dict[str, object], cwd: Path) -> str | None:
    explicit = str(payload.get("turn_id") or "").strip()
    if explicit:
        return explicit
    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return None
        database = Path(configured).expanduser() / "orchestration.db"
        if not database.is_file():
            return None
        uri = f"{database.resolve().as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=3) as connection:
            row = connection.execute(
                "SELECT turn_id FROM gate_injections WHERE session_id = ? AND cwd_hash = ? "
                "ORDER BY injected_at DESC LIMIT 1",
                (
                    str(payload.get("session_id") or "unknown-session"),
                    stable_hash(str(workspace_root(cwd))),
                ),
            ).fetchone()
        return str(row[0]) if row and row[0] else None
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return None


def latest_usage_instruction(payload: dict[str, object], cwd: Path) -> str:
    """Restore Usage only when the most recent recorded root turn required it."""

    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return ""
        database = Path(configured).expanduser() / "orchestration.db"
        if not database.is_file():
            return ""
        uri = f"{database.resolve().as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=3) as connection:
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(gate_injections)")
            }
            if not {"usage_requested", "usage_automatic", "usage_language"}.issubset(columns):
                return ""
            session_id = str(payload.get("session_id") or "unknown-session")
            cwd_hash = stable_hash(str(workspace_root(cwd)))
            explicit_turn_id = str(payload.get("turn_id") or "").strip()
            if explicit_turn_id:
                row = connection.execute(
                    "SELECT turn_id, usage_requested, usage_automatic, usage_language "
                    "FROM gate_injections WHERE session_id = ? AND cwd_hash = ? AND turn_id = ? "
                    "ORDER BY injected_at DESC LIMIT 1",
                    (session_id, cwd_hash, explicit_turn_id),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT turn_id, usage_requested, usage_automatic, usage_language "
                    "FROM gate_injections WHERE session_id = ? AND cwd_hash = ? "
                    "ORDER BY injected_at DESC LIMIT 1",
                    (session_id, cwd_hash),
                ).fetchone()
        if row is None:
            return ""
        return usage_instruction_for(
            str(row[0]) or None, bool(row[1]), bool(row[2]), row[3] == "zh"
        )
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return ""


def latest_response_language(payload: dict[str, object], cwd: Path) -> str:
    """Restore the latest root-turn language after compaction; English is the safe fallback."""

    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return "en"
        database = Path(configured).expanduser() / "orchestration.db"
        if not database.is_file():
            return "en"
        uri = f"{database.resolve().as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=3) as connection:
            columns = {
                str(row[1]) for row in connection.execute("PRAGMA table_info(gate_injections)")
            }
            if "usage_language" not in columns:
                return "en"
            session_id = str(payload.get("session_id") or "unknown-session")
            cwd_hash = stable_hash(str(workspace_root(cwd)))
            explicit_turn_id = str(payload.get("turn_id") or "").strip()
            if explicit_turn_id:
                row = connection.execute(
                    "SELECT usage_language FROM gate_injections "
                    "WHERE session_id = ? AND cwd_hash = ? AND turn_id = ? "
                    "ORDER BY injected_at DESC LIMIT 1",
                    (session_id, cwd_hash, explicit_turn_id),
                ).fetchone()
            else:
                row = connection.execute(
                    "SELECT usage_language FROM gate_injections "
                    "WHERE session_id = ? AND cwd_hash = ? "
                    "ORDER BY injected_at DESC LIMIT 1",
                    (session_id, cwd_hash),
                ).fetchone()
        return "zh" if row and row[0] == "zh" else "en"
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return "en"


def ensure_gate_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS gate_injections (
            injection_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            turn_id TEXT NOT NULL,
            cwd_hash TEXT NOT NULL,
            prompt_fingerprint TEXT NOT NULL,
            ledger_present INTEGER NOT NULL,
            repeat_failure_signal INTEGER NOT NULL DEFAULT 0,
            continuity_required INTEGER NOT NULL DEFAULT 0,
            routing_rationale_candidate INTEGER NOT NULL DEFAULT 0,
            routing_experiment_id TEXT,
            delegation_grant_active INTEGER NOT NULL DEFAULT 0,
            usage_requested INTEGER NOT NULL DEFAULT 0,
            usage_automatic INTEGER NOT NULL DEFAULT 0,
            usage_language TEXT,
            injected_at TEXT NOT NULL,
            policy_version TEXT NOT NULL
        )
        """
    )
    columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(gate_injections)")
    }
    if "repeat_failure_signal" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN "
            "repeat_failure_signal INTEGER NOT NULL DEFAULT 0"
        )
    if "continuity_required" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN "
            "continuity_required INTEGER NOT NULL DEFAULT 0"
        )
    if "routing_rationale_candidate" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN "
            "routing_rationale_candidate INTEGER NOT NULL DEFAULT 0"
        )
    if "routing_experiment_id" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN routing_experiment_id TEXT"
        )
    if "delegation_grant_active" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN "
            "delegation_grant_active INTEGER NOT NULL DEFAULT 0"
        )
    if "usage_requested" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN usage_requested INTEGER NOT NULL DEFAULT 0"
        )
    if "usage_automatic" not in columns:
        connection.execute(
            "ALTER TABLE gate_injections ADD COLUMN usage_automatic INTEGER NOT NULL DEFAULT 0"
        )
    if "usage_language" not in columns:
        connection.execute("ALTER TABLE gate_injections ADD COLUMN usage_language TEXT")


def project_grant_active(connection: sqlite3.Connection, cwd_hash: str) -> bool:
    table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'project_grants'"
    ).fetchone()
    if table is None:
        return False
    row = connection.execute(
        "SELECT active FROM project_grants WHERE cwd_hash = ?", (cwd_hash,)
    ).fetchone()
    if row is not None:
        return bool(row[0])
    row = connection.execute(
        "SELECT active FROM project_grants WHERE cwd_hash = ?", (GLOBAL_GRANT_KEY,)
    ).fetchone()
    return bool(row and row[0])


def record_gate(
    payload: dict[str, object], cwd: Path, ledger: Path | None
) -> dict[str, bool]:
    """Record that the root gate was delivered without retaining prompt content."""

    prompt = str(payload.get("prompt") or "")
    repeat_signal = repeat_failure_signal(prompt)
    rationale_candidate = routing_rationale_signal(prompt)
    usage_requested, usage_automatic, usage_zh = usage_requirements(prompt)
    state = {
        "repeat_failure_signal": repeat_signal,
        "continuity_required": False,
        "routing_rationale_candidate": rationale_candidate,
        "delegation_grant_active": False,
        "usage_requested": usage_requested,
        "usage_automatic": usage_automatic,
        "usage_zh": usage_zh,
    }
    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return state
        root = Path(configured).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        session_id = str(payload.get("session_id") or "unknown-session")
        turn_id = str(payload.get("turn_id") or "unknown-turn")
        prompt_fingerprint = stable_hash(prompt)
        injection_id = stable_hash(f"{session_id}\n{turn_id}\n{prompt_fingerprint}")
        cwd_hash = stable_hash(str(workspace_root(cwd)))
        with sqlite3.connect(root / "orchestration.db", timeout=3) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout = 3000")
            connection.execute("PRAGMA journal_mode = WAL")
            ensure_gate_schema(connection)
            existing = connection.execute(
                "SELECT repeat_failure_signal, continuity_required, "
                "routing_rationale_candidate, delegation_grant_active, "
                "usage_requested, usage_automatic, usage_language "
                "FROM gate_injections WHERE injection_id = ?",
                (injection_id,),
            ).fetchone()
            if existing is not None:
                return {
                    "repeat_failure_signal": bool(existing["repeat_failure_signal"]),
                    "continuity_required": bool(existing["continuity_required"]),
                    "routing_rationale_candidate": bool(
                        existing["routing_rationale_candidate"]
                    ),
                    "delegation_grant_active": bool(existing["delegation_grant_active"]),
                    "usage_requested": bool(existing["usage_requested"]),
                    "usage_automatic": bool(existing["usage_automatic"]),
                    "usage_zh": existing["usage_language"] == "zh",
                }
            prior_prompts = int(
                connection.execute(
                    "SELECT COUNT(*) FROM gate_injections "
                    "WHERE session_id = ? AND cwd_hash = ?",
                    (session_id, cwd_hash),
                ).fetchone()[0]
            )
            continuity_required = bool(
                ledger is None and repeat_signal and prior_prompts >= 1
            )
            grant_active = project_grant_active(connection, cwd_hash)
            if grant_active and ledger is not None and EXECUTION_PATTERN.search(prompt):
                rationale_candidate = True
            connection.execute(
                """
                INSERT OR IGNORE INTO gate_injections (
                    injection_id, session_id, turn_id, cwd_hash, prompt_fingerprint,
                    ledger_present, repeat_failure_signal, continuity_required,
                    routing_rationale_candidate, routing_experiment_id,
                    delegation_grant_active, usage_requested, usage_automatic,
                    usage_language, injected_at, policy_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    injection_id,
                    session_id,
                    turn_id,
                    cwd_hash,
                    prompt_fingerprint,
                    int(ledger is not None),
                    int(repeat_signal),
                    int(continuity_required),
                    int(rationale_candidate),
                    ROUTING_EXPERIMENT_ID if rationale_candidate else None,
                    int(grant_active),
                    int(usage_requested),
                    int(usage_automatic),
                    "zh" if usage_zh else "en",
                    datetime.now(timezone.utc).isoformat(),
                    POLICY_VERSION,
                ),
            )
            return {
                "repeat_failure_signal": repeat_signal,
                "continuity_required": continuity_required,
                "routing_rationale_candidate": rationale_candidate,
                "delegation_grant_active": grant_active,
                "usage_requested": usage_requested,
                "usage_automatic": usage_automatic,
                "usage_zh": usage_zh,
            }
    except (OSError, sqlite3.Error, TypeError, ValueError):
        # Auditability must never block or suppress the routing instruction.
        return state


def routing_debt_context(payload: dict[str, object]) -> str:
    """Return one compact close-or-renew reminder without retaining task content."""

    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return ""
        database = Path(configured).expanduser() / "orchestration.db"
        if not database.is_file():
            return ""
        session_id = str(payload.get("session_id") or "unknown-session")
        with sqlite3.connect(database, timeout=3) as connection:
            connection.row_factory = sqlite3.Row
            reconcile_native_completions(connection, session_id)
            # Lifecycle recovery is authoritative; optional debt statistics must not
            # roll it back when an older or reduced audit schema lacks a column.
            connection.commit()
            tables = {
                str(row[0])
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            native_debt = 0
            external_debt = 0
            stale = 0
            if "decisions" in tables:
                native_debt = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM decisions WHERE session_id = ? "
                        "AND status = 'stopped'",
                        (session_id,),
                    ).fetchone()[0]
                )
            if "external_routes" in tables:
                external_debt = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM external_routes WHERE parent_session_id = ? "
                        "AND status IN ('succeeded', 'failed') AND lead_result IS NULL",
                        (session_id,),
                    ).fetchone()[0]
                )
            if "executions" in tables:
                execution_columns = {
                    str(row[1])
                    for row in connection.execute("PRAGMA table_info(executions)")
                }
                if {"session_id", "started_at", "stopped_at"}.issubset(
                    execution_columns
                ):
                    decision_columns = (
                        {
                            str(row[1])
                            for row in connection.execute("PRAGMA table_info(decisions)")
                        }
                        if "decisions" in tables
                        else set()
                    )
                    can_join_tier = (
                        "decision_id" in execution_columns
                        and {"decision_id", "tier"}.issubset(decision_columns)
                    )
                    join = (
                        "LEFT JOIN decisions AS decision "
                        "ON decision.decision_id = execution.decision_id"
                        if can_join_tier
                        else ""
                    )
                    threshold = (
                        "CASE WHEN decision.tier = 'fast' THEN 30 ELSE 90 END"
                        if can_join_tier
                        else "90"
                    )
                    stale = int(
                        connection.execute(
                            "SELECT COUNT(*) FROM executions AS execution "
                            f"{join} WHERE execution.session_id = ? "
                            "AND execution.stopped_at IS NULL "
                            "AND (julianday('now') - julianday(execution.started_at)) * 1440 "
                            f"> {threshold}",
                            (session_id,),
                        ).fetchone()[0]
                    )
        parts: list[str] = []
        unverified = native_debt + external_debt
        if unverified:
            parts.append(f"{unverified} completed worker outcome(s) remain unverified")
        if stale:
            parts.append(f"{stale} worker(s) exceed the lifecycle warning")
        if not parts:
            return ""
        return (
            "Goldilocks routing debt: "
            + "; ".join(parts)
            + ". Stale records do not count as EXISTING unless current host status confirms they are "
            "running; close outcomes and stop or explicitly renew them before reuse."
        )
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return ""


def reconcile_native_completions(
    connection: sqlite3.Connection, session_id: str
) -> int:
    available = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        )
    }
    if not {"decisions", "executions"}.issubset(available):
        return 0
    decision_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(decisions)")
    }
    execution_columns = {
        str(row[1]) for row in connection.execute("PRAGMA table_info(executions)")
    }
    if not {"decision_id", "status"}.issubset(decision_columns) or not {
        "agent_id",
        "session_id",
        "decision_id",
        "started_at",
        "stopped_at",
    }.issubset(execution_columns):
        return 0
    rows = connection.execute(
        "SELECT agent_id, decision_id, started_at FROM executions "
        "WHERE session_id = ? AND stopped_at IS NULL",
        (session_id,),
    ).fetchall()
    reconciled = 0
    for row in rows:
        terminal = read_terminal_state(str(row["agent_id"] or ""))
        if terminal is None:
            continue
        completed_at = terminal.completed_at
        elapsed_ms: int | None = None
        try:
            started = datetime.fromisoformat(str(row["started_at"]).replace("Z", "+00:00"))
            stopped = datetime.fromisoformat(completed_at.replace("Z", "+00:00"))
            elapsed_ms = max(0, int((stopped - started).total_seconds() * 1000))
        except (TypeError, ValueError):
            pass
        updates = ["stopped_at = ?"]
        values: list[object] = [completed_at]
        if "elapsed_ms" in execution_columns:
            updates.append("elapsed_ms = ?")
            values.append(elapsed_ms)
        if "terminal_outcome" in execution_columns:
            updates.append("terminal_outcome = ?")
            values.append(terminal.outcome)
        if "quota_reset_at" in execution_columns:
            updates.append("quota_reset_at = ?")
            values.append(terminal.quota_reset_at)
        values.append(row["agent_id"])
        connection.execute(
            f"UPDATE executions SET {', '.join(updates)} WHERE agent_id = ?",
            values,
        )
        if row["decision_id"]:
            if "stopped_at" in decision_columns:
                connection.execute(
                    "UPDATE decisions SET status = 'stopped', stopped_at = ? "
                    "WHERE decision_id = ? AND status IN ('planned', 'started')",
                    (completed_at, row["decision_id"]),
                )
            else:
                connection.execute(
                    "UPDATE decisions SET status = 'stopped' WHERE decision_id = ? "
                    "AND status IN ('planned', 'started')",
                    (row["decision_id"],),
                )
        reconciled += 1
    return reconciled


def has_continuity_debt(payload: dict[str, object], cwd: Path) -> bool:
    try:
        configured = os.environ.get("PLUGIN_DATA")
        if not configured:
            return False
        database = Path(configured).expanduser() / "orchestration.db"
        if not database.is_file():
            return False
        session_id = str(payload.get("session_id") or "unknown-session")
        with sqlite3.connect(database, timeout=3) as connection:
            connection.row_factory = sqlite3.Row
            columns = {
                str(row[1])
                for row in connection.execute("PRAGMA table_info(gate_injections)")
            }
            if "continuity_required" not in columns:
                return False
            row = connection.execute(
                "SELECT 1 FROM gate_injections WHERE session_id = ? AND cwd_hash = ? "
                "AND continuity_required = 1 LIMIT 1",
                (session_id, stable_hash(str(workspace_root(cwd)))),
            ).fetchone()
            return row is not None
    except (OSError, sqlite3.Error, TypeError, ValueError):
        return False


def _git_common_dir(directory: Path) -> Path | None:
    marker = directory / ".git"
    try:
        if marker.is_symlink():
            return None
        if marker.is_dir():
            return marker.resolve()
        if not marker.is_file():
            return None
        first_line = marker.read_text(encoding="utf-8", errors="replace").splitlines()[0]
        if not first_line.lower().startswith("gitdir:"):
            return None
        gitdir = Path(first_line.split(":", 1)[1].strip()).expanduser()
        if not gitdir.is_absolute():
            gitdir = (directory / gitdir).resolve()
        if gitdir.parent.name == "worktrees":
            return gitdir.parent.parent.resolve()
        return gitdir.resolve()
    except (IndexError, OSError, ValueError):
        return None


def _candidate_common_git_dirs(cwd: Path) -> list[Path]:
    """Find trusted Git registries without recursively scanning the workspace."""

    found: list[Path] = []
    for directory in (cwd, *cwd.parents):
        common = _git_common_dir(directory)
        if common is not None:
            found.append(common)
            break
    if not found:
        # Codex workspaces may be a non-Git container whose registered worktrees
        # live one level below a conventional worktree directory.
        for container_name in (".worktrees", "worktrees", "work"):
            container = cwd / container_name
            try:
                children = list(container.iterdir()) if container.is_dir() else []
            except OSError:
                children = []
            for child in children:
                if child.is_symlink() or not child.is_dir():
                    continue
                common = _git_common_dir(child)
                if common is not None:
                    found.append(common)
    unique: list[Path] = []
    seen: set[str] = set()
    for path in found:
        key = str(path)
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def _registered_worktrees(common_git_dir: Path) -> list[Path]:
    worktrees: list[Path] = []
    if common_git_dir.name == ".git" and not common_git_dir.is_symlink():
        worktrees.append(common_git_dir.parent)
    registry = common_git_dir / "worktrees"
    try:
        entries = list(registry.iterdir()) if registry.is_dir() else []
    except OSError:
        entries = []
    for entry in entries:
        gitdir_file = entry / "gitdir"
        try:
            if entry.is_symlink() or gitdir_file.is_symlink() or not gitdir_file.is_file():
                continue
            git_marker = Path(gitdir_file.read_text(encoding="utf-8").strip()).expanduser()
            if not git_marker.is_absolute():
                git_marker = entry / git_marker
            if git_marker.name != ".git" or git_marker.is_symlink() or not git_marker.is_file():
                continue
            worktree = git_marker.parent
            if worktree.is_symlink() or not worktree.is_dir():
                continue
            first_line = git_marker.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()[0]
            if not first_line.lower().startswith("gitdir:"):
                continue
            backlink = Path(first_line.split(":", 1)[1].strip()).expanduser()
            if not backlink.is_absolute():
                backlink = worktree / backlink
            if backlink.resolve() != entry.resolve():
                continue
            worktrees.append(worktree.resolve())
        except (IndexError, OSError, ValueError):
            continue
    return worktrees


def _frontier_matches(ledger: Path, session_id: str) -> bool:
    try:
        if (
            ledger.is_symlink()
            or ledger.parent.is_symlink()
            or not ledger.parent.is_dir()
            or not ledger.is_file()
        ):
            return False
        text = ledger.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---", 4)
    if end < 0:
        return False
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, separator, value = line.partition(":")
        if separator:
            fields[key.strip()] = value.strip().strip("'\"")
    return fields.get("status") == "active" and fields.get("session_id") == session_id


def _trusted_local_ledger(ledger: Path) -> bool:
    try:
        return bool(
            not ledger.is_symlink()
            and not ledger.parent.is_symlink()
            and ledger.parent.is_dir()
            and ledger.is_file()
        )
    except OSError:
        return False


def find_ledger(cwd: Path, session_id: str | None = None) -> Path | None:
    local_candidate = cwd / ".goldilocks" / "ACTIVE.md"
    if _trusted_local_ledger(local_candidate):
        return local_candidate
    boundary = next(
        (directory for directory in (cwd, *cwd.parents) if (directory / ".git").exists()),
        None,
    )
    if boundary is not None and boundary != cwd:
        for directory in cwd.parents:
            candidate = directory / ".goldilocks" / "ACTIVE.md"
            if _trusted_local_ledger(candidate):
                return candidate
            if directory == boundary:
                break
    if not session_id:
        return None
    matches: list[Path] = []
    seen: set[str] = set()
    for common in _candidate_common_git_dirs(cwd):
        for worktree in _registered_worktrees(common):
            candidate = worktree / ".goldilocks" / "ACTIVE.md"
            key = str(candidate)
            if key in seen:
                continue
            seen.add(key)
            if _frontier_matches(candidate, session_id):
                matches.append(candidate)
    if len(matches) == 1:
        return matches[0]
    return None


def main() -> None:
    if os.environ.get("GOLDILOCKS_WORKER") == "1":
        return
    try:
        payload = json.load(sys.stdin)
        event = str(payload.get("hook_event_name") or "")
        if event not in {"SessionStart", "UserPromptSubmit", "PostCompact"}:
            return
        started_at = _now_isoformat()
        cwd = Path(payload.get("cwd") or os.getcwd()).expanduser().resolve()
        session_id = str(payload.get("session_id") or "")
        ledger = find_ledger(cwd, session_id)
        output = None
        if event == "SessionStart":
            if ledger is None:
                if not has_continuity_debt(payload, cwd):
                    output = None
                else:
                    output = {
                        "hookSpecificOutput": {
                            "hookEventName": "SessionStart",
                            "additionalContext": (
                                "Goldilocks continuity debt exists for this session and workspace. "
                                "Before continuing, read continuity.md, reconcile repository evidence, "
                                "create or update .goldilocks/ACTIVE.md and the existing debug/validation "
                                "record, then resume from the exact next test."
                            ),
                        }
                    }
            else:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": (
                            "Show one localized first-work-update cue (`Goldilocks | Active: continuity restored from ACTIVE` / "
                            "`Goldilocks｜已启用：已从 ACTIVE 恢复任务`) and do not repeat it. "
                            f"Recovery state exists at {ledger}; read it, reconcile repository evidence, "
                            "honor applied steering and Do not repeat, then continue from Exact next action."
                        ),
                    }
                }
        elif event == "UserPromptSubmit":
            gate_state = record_gate(payload, cwd, ledger)
            prompt = str(payload.get("prompt") or "")
            message = (
                f"{MICRO_STYLE} {ROUTING_GATE} {MINIMUM_SUFFICIENT_VERIFICATION} "
                f"{visible_response_contract(prompt, str(payload.get('turn_id') or '') or None)}"
            )
            if usage := usage_instruction_for(
                str(payload.get("turn_id") or "") or None,
                gate_state["usage_requested"],
                gate_state["usage_automatic"],
                gate_state["usage_zh"],
            ):
                message += f" {usage}"
            if gate_state["routing_rationale_candidate"]:
                message += f" {ROUTING_RATIONALE_GATE}"
                if gate_state["delegation_grant_active"]:
                    message += f" {AUTHORIZED_DISPATCH_GATE}"
            if ledger is not None:
                message += (
                    f" An active Goldilocks task ledger exists at {ledger}. Interpret this prompt "
                    "against its stable Objective as ADD, REPLACE, CANCEL, or QUESTION; after "
                    "handling it, mark the steering entry applied before continuing."
                )
            elif gate_state["continuity_required"]:
                message += f" {CONTINUITY_GATE}"
            night_shift = night_shift_context(payload, cwd, prompt)
            if night_shift:
                message += f" {night_shift}"
            debt = routing_debt_context(payload)
            if debt:
                message += f" {debt}"
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": message,
                }
            }
        else:
            response_recovery = (
                "Goldilocks visible response and verification contracts survived compaction. "
                + MINIMUM_SUFFICIENT_VERIFICATION
                + " "
                + visible_response_contract(
                    "",
                    latest_turn_id(payload, cwd),
                    latest_response_language(payload, cwd),
                )
            )
            if usage := latest_usage_instruction(payload, cwd):
                response_recovery += f" {usage}"
            if ledger is None:
                if not has_continuity_debt(payload, cwd):
                    system_message = response_recovery
                else:
                    system_message = (
                        "Goldilocks continuity debt survived compaction without a task frontier. Read "
                        "continuity.md, reconcile repository evidence, create or update "
                        ".goldilocks/ACTIVE.md and the existing debug/validation record, then resume "
                        f"from the exact next test. {response_recovery}"
                    )
            else:
                system_message = (
                    "Show one localized first-work-update cue (`Goldilocks | Active: continuity restored from ACTIVE` / "
                    "`Goldilocks｜已启用：已从 ACTIVE 恢复任务`) and do not repeat it. "
                    f"Goldilocks recovery required: read {ledger}, reconcile repository state, "
                    f"and resume from Exact next action. {response_recovery}"
                )
            output = {
                "continue": True,
                "systemMessage": system_message,
            }

        if output is not None:
            print(json.dumps(output, ensure_ascii=False))
        _record_hook_health(payload, event, "ok", started_at)
    except Exception:
        if "event" in locals():
            _record_hook_health(payload, event, "error", started_at)
        return


if __name__ == "__main__":
    main()
