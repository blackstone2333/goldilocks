# Kernel

## Route / Owner

进入 kernel 后、Lead 实现前算一次 `gain = Lead saved - worker - briefing - review - integration - failure×retry`。完整可转交、可与 Lead 终验分离且实施明显重于 briefing+review 的单一 mutable chain 也参选，即使内部紧耦合；shared surface 只限 one writer，不等于 Lead 必须自做。仅比较 Direct 与一个 Owner；gain 不足、transfer loss、authority、route unavailable 或 review cost 更高则 Direct；不制造 unit/plan/probe。单链转交胜出时只给一个 Owner。

微小/局部、只读、尚无可转交 fix 的诊断、contract 不完整/不安全，或转交成本未明显低于 Lead execution，不触发此门。

先评估 Fast：contract 固定 objective、non-goals、scope/tools、interfaces、dependencies、acceptance、evidence、prohibitions；有 residual judgment 即 Standard。Standard 可派 non-conflicting Fast 并 integrate；首失败仅 ordinary repair 一次。同一 acceptance 再失败即升级，不循环。

dispatch 前定 dependency、单 writer、interface、integration order、combined acceptance；保留 dirty work；未经授权不得 overwrite/delete/publish/deploy/contact/cross authority。child 名：Luna/Spark=`fast__<semantic>_<model>`，Terra=`standard__<semantic>_<model>`，Sol reviewer=`lead__<semantic>_<model>`。Luna/Spark 固定 `fork_turns=none`；Terra 仅 `none` 或 `1`–`4`；Sol reviewer 固定 `none`、fresh review-only、不得 write/repair/delegate；这是任务行为合同，不修改或降低用户选择的宿主权限。仅显式 Lead handoff 可用 `all`。原生宿主可能绕过 PreToolUse，主模型每次 spawn 前自检这些条件。Fast 不 delegate。worker 返回 `STATUS, CAUSE, CHANGES, VERIFIED, JUDGMENT CALLS, GAPS`；CAUSE 有证据或 unknown。

Fast 完成 fixed implementation 并执行一次 contract-scoped focused acceptance 后立即返回，不追加等价验证。Lead 不重新探索或重做 worker 已完成内容。全部 worker 返回后只执行一次 combined authoritative acceptance；组合验收失败最多一次 ordinary repair + re-verification，随后返回或升级，禁止循环。

orchestration 内部 comment 固定：`ROUTE, WRITE_READY, READ_READY, EXISTING, PLANNED_DISPATCH, LEAD, REASON, DETAIL`；reason codes=`lead_faster, shared_surface, critical_judgment, contract_not_ready, route_unavailable, review_cost, parallel_gain, quota_gain`。最终只按 root SKILL 的 protocol island 输出一次用户语言 receipt；不让回执格式反向决定路线。

## Models / fallback / Night Shift

核对 native role 与 actual model；cache≠readiness。固定 role 显式 `agent_type`：`goldilocks_spark_worker`=Spark XHigh code/tests；`goldilocks_luna_economy`=Luna Max economy/doc；`goldilocks_terra_engineer`=Terra Medium judgment；`goldilocks_sol_reviewer`=Sol High review-only。suffix 不选 role；不可见则 verified fallback，绝不 silent inherit Lead。visible Sol=`gpt-5.6-sol`。

Night Shift：economy→Luna；urgent deterministic code→Spark；不可用时公开 fallback 至 Terra/Luna/Direct。Spark official USD=N/A；quality/authority/safety 先于 economics。visible Sol 需 authorization；每 root 最多 two active/reserved、无 nested、须 origin return。audit read-only、no delegate/repair。

## Engines

**align** 定 end state。**diagnose** full evidence→reproduce/trace→falsifiable cause→earliest shared fix；第二次 recurrence 写 continuity，三次失败即 escalate。**build** inspect/reuse→最小 fail-first acceptance→最小实现。**prove** fresh evidence + final diff/status；integrated work 要 owner evidence + combined acceptance。**evolve** 只凭 reproducible behavior。**artifact** 定 unit/interface/assembly/acceptance。

Verification 用 minimum-sufficient：默认复用已有 evidence、runner 与验证设施；不新增 hash、contract freeze、baseline 或 gate，除非能指出具体事故，并说明 Git/version/PK/transaction/unique/type/ordinary tests 为何不足。已有 safeguards 不删；auth/data/irreversible/release 按项目风险。

工具保持自由选择，但禁止逻辑重复：先选项目声明或 host 提供的 authoritative runner。若仅 runner/dependency 不可用，执行一次 logically complete direct bundle，合并 supplied tests、focused edge、compile 与 diff。命令未启动或路径错误可修正并重启同一 bundle；这不增加逻辑验证次数。无相关变更不重跑已通过项；repair 后仅重跑失败项与受影响项。原因不明的连续失败转 diagnose，不靠重复运行碰运气。一旦取得 decisive evidence，立即停止，不再运行等价 tests/checks，不搜索多个 interpreter，不安装测试依赖。功能失败走 ordinary repair/escalation，不冒充环境 fallback。

编码 contract 边界只按当前 API 实际涉及的事实检查，包括 exact exception type、string/container 歧义、bool/int、空值/重复值、defensive copy 或 mutable return；这不是通用死清单，未涉及者不测。边界检查并入 worker 的一次 focused acceptance 或唯一 combined acceptance，不另开验证轮次。

## Continuity / completion — protocol island

compaction、stage、steering、waiting、delegation、handoff、persistence 时建立/更新 `.goldilocks/ACTIVE.md`。机器字段固定且逐项一次；值可自由表达：

`当前 Owner/Current Owner` · `状态/State` · `证据/Evidence` · `决策/Decision` · `下一步/Next action` · `阻塞/Blocker` · `验收/Acceptance` · `交接/Handoff`。

机器只固定字段标签，不固定值中的动词或同义词；按事实、语义完整性与 Owner 唯一性验收，不用词汇白名单反向塑造工作流。

fresh session 读文档继续；Direct 默认无状态。遵循仓库惯例。仅在用户要求、惯例要求或不更新会使 operation/ownership 失真时修改既有文件；不为导航、润色或“顺手完整”而扩大范围。新项目/architecture change 可写 `docs/PROJECT.md`；ACTIVE 可安全 ignore。完成前 fresh acceptance + full result + actual diff/status；old pass/report/stopped worker 不是 proof。
