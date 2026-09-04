---
name: goldilocks
description: Use for material ambiguity, unknown cause, persistence/recovery, useful delegation, cross-unit artifacts, or explicit Goldilocks requests. Clear routine Direct tasks do not load this skill; matching domain skills remain available, and Direct uses the project's evident runner first.
---

# Goldilocks

默认 Direct。只在上述边界成立时加载本 Skill；清晰例行任务由 frontmatter 的短门完成终态检查，不为证明 Direct 读取本文件。

新任务先完成需求对齐，再选择记录、计划和路由。选择未解才读 [align.md](references/align.md)。执行中的插话与新任务分开：只判断一次是否实质影响当前目标、范围、顺序、权限、验收或返回点；无影响则答复/吸收并返回，有影响才按语义调整。不得把固定分类词当协议；有会改变工作的歧义才问一个带建议的问题。非简单执行、实质 steering、跨阶段/会话或需持久证据时读 [task-lifecycle.md](references/task-lifecycle.md)。

Goldilocks 不提供或依赖 Hook，也不覆盖宿主的 `compact_prompt`；ACTIVE 是唯一执行前沿。它不因 `.goldilocks/ACTIVE.md` 仅仅存在就读取；只有宿主明确为 startup/resume/compaction/wait/delegation/handoff 的同任务恢复，且状态、任务和 session 匹配时才读。Direct 只跳过 Goldilocks orchestration；对齐后仍按任务匹配加载 domain Skill，绝不得因 Direct 抑制它。

## Direct gate

对齐后检查 architecture、authority、safety、irreversibility、causality、continuity 与 ready units。tiny/inseparable，或委派净收益不足，即 **Direct**：不建 state，做最小改动与决定性检查。发现 unknown cause、persistence，或完整可转交工作明显重于 briefing+review 时，读 [kernel.md](references/kernel.md) 比较路线，不预设委派。

验证遵循 minimum-sufficient：首次合并读现有 instructions、相关 source/tests 与运行时，不二次 discovery；复用 checks，受影响 tests 只跑一次，并同一 evidence call 检查 diff/status。产品修复后只重跑失败项与受影响项，不重跑已经通过且未受影响的 tests。只有当前 tests 未覆盖会推翻完成声明的重要表面，才加一个预先推导的 probe。脚本、路径或 runner 在触及产品前失败，只修并重跑缺失证据；不得重复已通过且未受影响的 tests 或重复 diff/status。一次权威证据足够即停止，不跑无关矩阵；原因不明的连续失败转 diagnose。普通低风险改动不新增无法说明具体事故的 hash、freeze、baseline 或 gate；既有 safeguards 不删，认证、数据安全、不可逆操作与正式发布仍按风险执行。细节按需读 [prove.md](references/prove.md)。

## One engine

align=终态不明；diagnose=unknown cause；build=durable execution/TDD；orchestrate=delegation；prove=acceptance；evolve=skill experiment；artifact=multi-unit；continuity=persistence/handoff。仅事实跨界才加读。

## Completion contract — protocol island

Standard owns one mutable chain + one ordinary repair；Fast 接 fixed leaf；Lead 留 intent、shared interfaces、authority/safety 与 final acceptance，不重复 Owner exploration。

本 Skill 实际加载并影响执行时，首次工作更新最多显示一条真实活动行：中文 `Goldilocks｜已启用：<动作>`，英文 `Goldilocks | Active: <action>`。后续只在恢复、委派、回退、Night Shift 或终验真实发生时合并更新；不为清晰 Direct 加载 Skill、展示活动或倾倒审计。

本 Skill 实际加载的可执行任务在最终回答末尾追加且仅追加一条用户语言 receipt；纯对话或未加载的清晰 Direct 省略。`详情/DETAIL` 只写真实动作。

中文固定：`路由=<直接|快速|标准|混合>｜团队=<主模型及实际启动角色>｜并发=<宿主确认启动数/宿主上限或?>｜委派=<实际委派任务或无>｜理由=<简短理由>｜详情=<一句事实>`。

English fixed: `ROUTE=<direct|fast|standard|mixed> | TEAM=<main model and actually started roles> | CONCURRENCY=<host-confirmed starts/host limit or ?> | DELEGATED=<actual delegated work or none> | REASON=<short reason> | DETAIL=<one factual sentence>`.

根身份只写 `主模型/main model`；worker 写实际 role，数量与 starts 一致。路线是决策，团队/并发/委派是事实，格式不反向决定 dispatch。Usage 仅 on-demand，无 automatic 模式；用户明确索要才调用。无此前显式基线时报告 unavailable 或省略，不补造基线。

报告 delta 与最短 decisive evidence。Defect 报 CAUSE（或 unknown）、fix 与当前证据，不为“fresh”重复验证。

最终交付只陈述已验收、已验证的当前状态；会话中未采用方案与用户纠正只作控制信息，不回显为交付内容。仅在方案被否或纠正、会话很长/compact/delegated、多交付表面、用户已见负向回声，或要写 commit、PR、release、README、log、handoff 等 durable surface 时，按需读 [final-output-hygiene.md](references/final-output-hygiene.md)。
