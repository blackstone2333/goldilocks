# Goldilocks 0.6.0-beta.1 发布前三臂测试

```yaml
date: 2026-09-04
candidate: 0.6.0-beta.1
final_source_sha256: 2e634e395fbfafdedf3f061d52a75ba02afea8571240d14bb4e8a016131ec0c0
model: gpt-5.6-sol
reasoning: high
service_tier: standard_requested_host_omitted
sandbox: danger-full-access
approval_policy: never
formal_model_calls_per_candidate: 3
final_result: PASS
release_eligible: true
```

## 最终结论

最终候选通过发布前 smoke gate。Beta9、Beta1 和原生 Direct 均完成同一固定小题并通过质量、完成度、基础设施与协议检查；每臂一次有效样本，均无宿主重试。

Beta1 在清晰任务中选择 Direct，根 Goldilocks Skill 正文未加载；零子 Agent、零多余状态、零流程文档、零后台动作、零真正重复验证。领域 Skill 发现、四个原生 Agent、Night Shift、回退、显式 Usage/诊断、安全与宿主权限边界未因本次减重而删除。

这是一次固定小题的发布前 smoke gate，只证明该候选满足当前发布门，不外推为版本在所有项目中普遍快于原生 Direct。

## 最终候选结果

| 臂 | 质量 | 耗时 | Raw Token | 账面归一成本 | Cache-neutral 成本 | 工具/步骤 | 真正重复验证 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `0.5.3-beta.9` | PASS | 100.888 s | 76,343 | $0.140375 | $0.422615 | 5 / 5 | 1 |
| `0.6.0-beta.1` | PASS | 110.169 s | 77,193 | $0.206398 | $0.432190 | 5 / 5 | 0 |
| 原生 Direct | PASS | 123.809 s | 101,224 | $0.202656 | $0.556320 | 7 / 7 | 0 |

### Beta1 相对 Beta9

- 耗时：`+9.199%`
- Raw Token：`+1.113%`
- 工具/步骤：均为 `0` 差异
- 缓存命中率相差 `17.359` 个百分点，账面成本不可直接硬比；按统一 uncached 输入费率计算的 cache-neutral 成本为 `+2.266%`
- 三项中 Raw Token 与门禁成本均在 `+3%` 等效带内，耗时未超过 `+10%` 上限，因此通过

### Beta1 相对原生 Direct

- 耗时：`-11.017%`
- Raw Token：`-23.740%`
- 工具/步骤：各少 `2`
- 缓存命中率相差 `12.617` 个百分点，账面成本不可直接硬比；cache-neutral 成本为 `-22.313%`
- 耗时与门禁成本均未超过 `+15%` 上限，因此通过

## 行为与输入证据

- Beta1 路线：Direct
- 子 Agent 启动：0
- 用户往返：0
- 多余状态写入：0
- 流程文档创建：0
- 后台动作：0
- 验证恢复：1；这是同一验证先因不可用 runner 未启动、随后成功运行，不计作重复产品验证
- 真正重复验证：0
- Beta1 可见目录描述：1 次
- Beta1 根 Skill 正文标记：0 次
- 原生 Direct 中 Goldilocks 目录描述与正文标记：均为 0

## 保留的 HOLD 历史

首轮候选 source hash 为 `8b5dcc4fd8479eabf756e33092c5fe7812a3110368144c057acbe28f51d88ff4`。三臂质量均通过，但 Beta1 相对 Beta9 的耗时、Raw Token、账面归一成本分别为 `+48.783%`、`+13.582%`、`+73.667%`；相对原生 Direct 分别为 `+70.677%`、`+46.653%`、`+189.073%`，因此正确判为 HOLD。

定位出的产品问题是：清晰 Direct 仍加载约 6.5 KB 根 Skill，并在 runner 修复后重复执行等价检查。随后只收紧清晰 Direct 的入口、最小充分验证停止条件与活动/回执文案，没有降低质量、权限、安全或验收要求。

中间候选 source hash 为 `2fd1f68ae5efdd95b3e8c47fdde79e23018312736815e59d7311700bb7a637ce`，产品面已减重，但 harness 仍把一次 runner recovery 误记为重复验证，因此保持 HOLD。修复统计口径后只重跑受影响的冻结三臂，没有重刷同一候选或挑选较好样本。

## 门禁与证据

- PASS：三臂质量、完成度、基础设施和协议均通过。
- PASS：最终结果来自 3 次正式模型调用，不是离线或合成 fixture。
- PASS：Beta1 的 Direct 行为与保留能力合同通过。
- PASS：Beta1 相对 Beta9 和原生 Direct 均通过冻结效率门。
- 最终聚合报告：`/private/tmp/goldilocks-v060-beta1-runnerhint-20260904/report.json`
- 最终运行目录：`/private/tmp/goldilocks-v060-beta1-runnerhint-20260904`
- 首轮 HOLD：`/private/tmp/goldilocks-v060-beta1-formal-20260904/report.json`
- 中间 HOLD：`/private/tmp/goldilocks-v060-beta1-final-20260904/report.json`
- 可复现 harness：`evals/v060-beta1-three-arm-2026-09-04/`
- 发布判定：`release_eligible=true`

本记录不构成发布动作授权：提交、Tag、推送和发布仍作为下一独立步骤执行。
