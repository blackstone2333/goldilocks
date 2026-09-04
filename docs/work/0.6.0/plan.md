# Goldilocks 0.6.0 实施计划

```yaml
version: 0.6.0
status: active
current_phase: 7
overall_owner: main_model
integration_owner: main_model
updated: 2026-09-04
```

本 Plan 对应同目录的 [spec.md](spec.md)。它管理 `0.6.0` 这一可验收版本工作单元，不为每轮对话或每个小命令创建新 Plan。

## Owner 规则

- 主模型是唯一整合 owner：维护已确认终态、共享接口、权限、安全、最终差异、组合验收和发布决策。
- 某一阶段只有在宿主确认实际委派后，才把执行 owner 更新为对应 Agent；不得把计划中的角色写成已经启动的团队事实。
- 每个可变文件域只有一个 writer。并行只用于互不冲突且可独立验收的工作单元。
- 文档、代码或测试 worker 返回的结果必须由整合 owner 对照 Spec 和实际 diff 接收；不得仅凭完成消息宣布通过。
- Plan 只在阶段开始、阶段完成、真实阻塞、owner/依赖变化或验收结果出现时更新，不记录命令流水账。

## 阶段总览

| 阶段 | 负责 owner | 状态 | 交付物 | 阶段验收 |
|---|---|---|---|---|
| 1. 冻结 Spec/Plan 与基线 | 主模型（文档可由一个独立 writer 起草） | complete | 本目录 `spec.md`、`plan.md`；Beta9 可复现基线定位 | 范围、非目标、六步流程、记录触发器、清洁安装和三臂门完整；Beta9 源/版本可在清理后隔离运行 |
| 2. 六步主流程与记录协议 | 主模型或一个确认启动的实现 owner | complete | 根 Skill、按需 references、ACTIVE 恢复合同及对应聚焦测试 | 对齐先于路由；插话能返回主线；文件只按事件触发；旧 ACTIVE 不被新任务读取 |
| 3. 版本身份、无 Hook 与保留能力 | 主模型或一个确认启动的元数据 owner | complete | 所有 manifest/展示统一为 v0.6.0；废弃 Hook 入口和引用清除；四 Agent/显式工具保持 | 静态合同通过；零 Hook 注册；四 Agent 身份、Usage/诊断/路由回执可用 |
| 4. Bootstrap 清洁安装 | 主模型或一个确认启动的 Bootstrap owner | complete | 可预览的 Goldilocks-only 清理和唯一安装路径；聚焦测试 | 不触碰项目文件、历史、备份、其他插件或无关配置；安装后唯一版本、零 Hook、权限不降级 |
| 5. 一次最小充分组合验收 | 主模型 | complete | 受影响测试结果、最终 diff/status、未验收缺口 | 一次权威组合检查证明 7.1；只修失败项并重验受影响面，不跑等价测试循环 |
| 6. 本机清洁安装与简单三臂测试 | 主模型；受影响安装面由 Bootstrap owner 修改 | complete_with_runtime_unknown | 已通过的三臂证据；移除全局 prompt；ACTIVE 静态/清洁安装证据 | 三臂与受影响合同通过；一次真实续接探针未进入压缩事件，按授权转为发布后实机观察 |
| 7. 发布 v0.6.0 | 主模型 | active | README/CHANGELOG、发布提交/标签、远端正式版 | 不重跑完整三臂或 ACTIVE 探针；完成版本一致性、发布与远端复核 |

## 阶段 1：冻结工作合同与可复现基线

**Owner：主模型。**

- [x] 建立工作单元级 Spec，固定 `0.6.0` 的包含项与非目标。
- [x] 建立阶段 Plan，明确 owner、依赖、验收和发布门。
- [x] 记录 Beta9 的不可变来源（commit/tag/安装包或字节可核对快照），避免清洁安装后无法运行基线。
- [x] 记录纯 Direct 的隔离条件：不加载 Goldilocks Plugin、portable Skill、Hook、compact prompt 或全局 Goldilocks 规则。
- [x] 核对当前 dirty worktree，按文件域分配唯一 writer；保留既有用户改动。

**完成条件：** 文档与仓库事实一致，三臂都有可隔离复现的来源，实施不依赖将要被清理的缓存。

## 阶段 2：实现六步主流程与事件触发记录

**Owner：主模型；若委派，必须把实际 owner 和文件域写回本 Plan。依赖：阶段 1。**

### 2.1 消息分类与对齐

- [x] 在最小入口中固定 `NEW / QUESTION / ADD / REPLACE / PAUSE / CANCEL / CONFIRM / RESUME` 的判断。
- [x] 明确 `QUESTION` 回答后恢复原主线；只有显式 `REPLACE / PAUSE / CANCEL` 改变主线。
- [x] 实现 `ADD-accepted / ADD-pending / ADD-blocking` 三档处理。
- [x] 保证需求对齐发生在 Plan 和路由之前；清晰 Direct 只做常量时间判断，不强制访谈。
- [x] align 只询问会改变终态的决策，先查事实，并在提问时给出建议和主要取舍。

### 2.2 记录选择与计划

- [x] 落实“语义必须存在，物理文件可以合并”：简单 Direct 无流程文档；中等工作允许单工作包；大型/跨会话工作才拆分 spec/plan。
- [x] 为 PROJECT、spec、plan、ACTIVE、handoff、debug、ideas、CHANGELOG 编码准确的读写触发条件。
- [x] 规定 Plan 以可验收工作单元为边界；同一任务跨对话复用，任务结束标记完成，不维护永久追加的总 Plan。
- [x] 规定 ACTIVE 只在压缩、等待、steering、委派、交接、跨会话等持久化边界出现，约 4 KB/100 行上限，完成后关闭或移除。
- [x] 新任务不得因 `.goldilocks/ACTIVE.md` 仅仅存在而读取；恢复须匹配 active 状态、当前任务和 session。
- [x] ACTIVE 只保留当前消息分类、主线、对齐/授权状态、未处理要求、返回点与已触发记录；Goldilocks 不覆盖宿主压缩 prompt，也不建立第二摘要层。

### 2.3 路由、执行和验收

- [x] Plan 形成后再比较 Direct/Fast/Standard/Mixed；不因“展示 Skill 有用”而制造委派。
- [x] 执行中按需调用 build、diagnose、evolve、continuity 和领域 Skill；Direct 不得抑制任务匹配的领域 Skill。
- [x] 验收将每个完成声明映射到当前证据，复用有效 focused evidence，只在集成改变表面时做一次组合验收。
- [x] 完成时更新持久记录并关闭 ACTIVE；已完成 Plan 不再作为活动指令。

**聚焦验收：** 用静态合同和最少行为用例覆盖阶段顺序、消息分类、文件触发正/反例、ACTIVE 匹配/拒绝和最小验证停止条件。测试本身不得重新引入 Hook。

## 阶段 3：统一 v0.6.0 身份并确认减重没有阉割核心能力

**Owner：主模型；若委派，元数据/文档与运行实现应避免重叠 writer。依赖：阶段 2 的接口已稳定。**

- [x] 将原生 Plugin、portable Skill、marketplace、README、Agent Guide 和安装材料的当前开发身份统一为 `0.6.0`。
- [x] 删除已废弃 Hook 文件、Hook manifest 入口、安装/信任文案和不再被引用的 Hook 专属兼容分支或测试。
- [x] 保留并检查四个原生 Agent：Spark Fast、Luna Economy、Terra Standard、Sol Reviewer。
- [x] 保留并检查显式 Usage、显式诊断、运行时/路由证据工具和最终路由回执。
- [x] 保留 Direct 运行中升级路线、模型回退、Night Shift、权限和不可逆操作边界。
- [x] 全仓搜索旧版本身份和 Hook 声明；历史基准、CHANGELOG 历史、调试证据中的版本事实不得机械改写。

**完成条件：** 活动安装面只有 v0.6.0 身份且没有 Hook；历史资料仍保持历史真实性；核心能力清单逐项有静态或聚焦证据。

## 阶段 4：实现清洁安装

**Owner：主模型或确认启动的单一 Bootstrap owner。依赖：阶段 3 已生成可安装版本。**

- [x] 为清洁安装提供只读计划/预览，列出每个 Goldilocks 自有待删除目标和保留目标。
- [x] 删除范围仅包含旧活动安装、缓存、旧入口、旧 Hook 显示/信任残留和重复 portable/native 入口。
- [x] 显式保护仓库、历史版本、备份、项目文档、`.goldilocks/ACTIVE.md`、用户修改文件、其他插件和无关宿主配置。
- [x] 安装唯一候选版本，并验证版本、零 Hook、四 Agent、显式 Usage/诊断和现有权限。
- [x] 输出需要重启/新任务的 handoff，不把会话或 UI 快照缓存误判为安装失败。

**聚焦验收：** 临时 HOME/CODEX_HOME fixture 同时覆盖预览、同意应用、冲突时无写入、用户文件保留、重复入口收敛和检查结果。不得直接拿真实用户目录做破坏性测试。

## 阶段 5：一次最小充分组合验收

**Owner：主模型。依赖：阶段 2–4。**

在一个能传递失败状态的 evidence call 中完成：

1. 运行受本次改动直接影响的聚焦测试；
2. 运行仍适用的既有核心合同测试；
3. 检查最终 diff 和 status；
4. 做一个未被测试覆盖、但会推翻关键声明的 focused probe（若所有关键声明已被现有测试覆盖，则不另造 probe）。

修复规则：

- 产品失败：只修失败原因，重跑失败项及受影响项。
- 测试夹具/路径错误：只修测试基础设施，再启动同一逻辑 bundle。
- 原因不明的重复失败：停止重跑，转 diagnose，选择下一项有区分度的检查。
- 已获得决定性证据后停止，不换解释器、不跑无关 full matrix、不追加等价 gate。

**完成条件：** Spec 7.1 每项都映射到当前证据；未验证项明确记录，不以“应该可以”通过。

**结果：complete。** 20 个活动合同脚本、3 个 Skill 校验、Plugin 校验、三臂 runner self-test/preflight 与 diff check 均通过；没有为已删除 Hook 行为恢复旧测试。

## 阶段 6：本机清洁安装与三臂简单测试

**Owner：主模型。依赖：阶段 5。**

### 6.1 本机清洁安装

- [x] 先运行预览并保存脱敏清单。
- [x] 确认范围只包含 Goldilocks 自有目标后应用。
- [x] 重启 Codex 或新开任务，检查唯一 `0.6.0`、零 Hook、四 Agent 和权限。
- [x] 不删除测试所需的不可变 Beta9 基线；Beta9 通过隔离环境运行，不重新污染主安装。

### 6.2 三臂协议

- [x] 冻结一个边界清晰、预期 Direct、带确定性验收的小型代码修复题和 fixture。
- [x] 随机化或预先固定三臂顺序，避免根据中途结果换题。
- [x] 每臂在同一宿主、同一主模型/思考等级、同一权限和等价新任务中运行一次有效样本。
- [x] Beta9 与 v0.6.0 候选使用各自隔离安装；纯 Direct 确认没有 Goldilocks Skill/Plugin/Hook/compact prompt/规则。
- [x] 记录质量、wall、Raw Token、normalized cost（可比时）、工具/Agent/往返/文档/测试次数和路线。
- [x] 基础设施失败只替换该臂一次，同时保留被判污染的原始记录和理由。
- [x] 按 Spec 7.2 的阈值作出 `PASS / HOLD`，不以主观体感替代数据。

**结果：complete。** 首轮结果因输入膨胀与效率差距保持 HOLD；修复后最终候选三臂同质量通过，v0.6.0 候选没有功能阉割、无关文档或真正重复验证，并通过相对 Beta9 与原生 Direct 的冻结效率门。决定性证据见 `evals/results/2026-09-04-v060-beta1-release-smoke.md`。

### 6.3 有界效率修复与新候选复验

- [x] 收紧 frontmatter：清晰例行 Direct 在短描述中完成终态清晰度判断，不加载完整 Goldilocks；仅 material ambiguity、unknown cause、persistence/recovery、净收益委派、跨单元 artifact 或显式请求触发。
- [x] 保持零 Hook、领域 Skill 发现、权限、安全、四 Agent 和升级路线不变。
- [x] 将额外 probe 改为“只有当前 tests 留下重要证据缺口时最多一个”；检查脚本失败后只补缺失证据，不重复已通过 tests/diff/status。
- [x] 缩短只在 Goldilocks 实际加载时出现的活动提示与最终 receipt，不让可见性反向触发 Skill。
- [x] 修复三臂 harness 的语义重复验证识别，保留首轮证据不改写。
- [x] 运行受影响合同、Skill/Plugin validation 与一次清洁重装；通过后以新 source hash 按冻结协议运行一次新三臂，不复用或挑选首轮成绩。

**6.3 三臂门禁：PASS。** 受测 source hash 为 `2e634e395fbfafdedf3f061d52a75ba02afea8571240d14bb4e8a016131ec0c0`；三臂 `release_eligible=true`。后续 6.4 仅删除三臂中未触发的全局压缩配置面，按受影响证据继承规则处理。

### 6.4 移除全局 compact prompt

用户确认 ACTIVE 是唯一执行前沿，v0.6.0 不再向 Codex 全局 `config.toml` 注入或维护 `compact_prompt`。

- [x] 删除 Bootstrap 的 `--context-lean` 写入能力和随包 prompt asset；普通安装不读取或写入压缩配置。
- [x] 清洁安装只删除精确匹配已知 Goldilocks 内容的顶层 `compact_prompt`；用户自定义与 experimental 配置保持原样并报告未处理。
- [x] 更新中英文安装说明、Agent Guide、Spec 与运行记录，避免继续宣称全局 prompt 是连续性组成部分。
- [x] 先预览、再清理本机已确认的 Goldilocks 遗留 prompt，并验证其他配置、Agent 注册和权限未改变。
- [x] 运行受影响 Bootstrap、ACTIVE 静态和旧任务拒绝合同。
- [ ] 一次真实 ACTIVE 压缩续接探针在宿主首轮未结束时达到单次尝试上限，尚未进入 compact/follow-up；结论为 unknown。用户明确同意不重试，将其转为发布后的实机观察。

**证据继承边界：** 6.3 的三臂任务没有发生上下文压缩；本次只删除未被该任务触发的 Bootstrap/宿主压缩配置面，因此保留其路由、质量和效率证据。发布前只重验本次受影响面，不重跑三臂碰运气。

## 阶段 7：发布 `0.6.0`

**Owner：主模型。依赖：阶段 1–6 的决定性检查已通过；真实 ACTIVE 续接保留上述已授权的宿主证据缺口。当前状态：active。**

- [ ] 将已验证的用户可见变化写入中英文 CHANGELOG 和 README；不写未实现方案。
- [ ] 检查发布 diff 不含临时 fixture、凭据、缓存、原始日志或用户项目文件。
- [ ] 创建版本提交和 `0.6.0` 标签，并推送至已授权的 Goldilocks 仓库。
- [ ] 发布非 prerelease 的正式版，随后从远端/安装入口复核版本和安装结果。
- [ ] 将本 Plan 标记 `complete`，关闭对应 ACTIVE；留下决定性测试记录的链接。

## 验收证据索引

| 声明 | 证据路径/结果 | 状态 |
|---|---|---|
| 六步顺序与消息分类 | `tests/test_v060_release_contract.py`、`tests/test_v060_active_frontier_contract.py` | pass |
| 事件触发记录与 ACTIVE 恢复 | `task-lifecycle.md`、compact contract 与 ACTIVE-only contract | pass |
| 统一 v0.6.0 身份、零 Hook | Plugin/Skill validation 与 retained-capabilities contract | pass |
| 四 Agent 与显式能力保留 | `tests/test_v060_retained_capabilities.py` 与运行时检查 | pass |
| 清洁安装保留边界 | `tests/test_bootstrap.py`；本机唯一候选、零 Hook、权限未改 | pass |
| 聚焦组合验收 | 20 个活动合同脚本、3 个 Skill 校验、Plugin 校验、runner self-test/preflight、diff check | pass |
| Beta9/v0.6.0 候选/纯 Direct 对照 | `evals/results/2026-09-04-v060-beta1-release-smoke.md` | pass |
| 全局 prompt 移除与 ACTIVE 恢复 | 静态/清洁安装合同 pass；真实续接探针因宿主首轮未结束为 unknown，已授权转实机观察 | accepted_unknown |
| 远端发布与安装复核 | 尚未执行 | active |

## Plan 变更规则

- 实现方法、顺序或工具变化但终态不变：直接更新本 Plan，并简述原因。
- 目标、范围、非目标、权限或验收变化：先更新 Spec；存在实质选择时先与用户重新对齐。
- 明显相关且无冲突的新要求：更新真正受影响的 Spec/Plan/ACTIVE 后继续。
- 有疑问但不阻塞的新要求：记为 pending，在自然节点给出建议；不默认为已接受。
- 范围外想法：写入项目 ideas（若需要跨会话保存），不塞进本 Plan，也不展开实现。
- 阶段完成后标记 complete；旧阶段不再被任何恢复上下文当作当前动作。
