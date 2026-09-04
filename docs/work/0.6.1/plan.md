# Goldilocks 0.6.1 执行计划

```yaml
version: 0.6.1
status: complete
owner: main_model
updated: 2026-09-04
```

1. [x] 在根工作流、ACTIVE 模板与相关参考中，用双入口和“实质影响”规则替换固定的插入消息标签。**Owner：** implementation chain。
2. [x] 更新中英文流程图、发布文档、版本元数据与 Bootstrap 稳定版本行为。**Owner：** documentation/release chain。
3. [x] 为项目记录增加语言策略：人类可读内容跟随用户工作语言，稳定技术/机器标识保留英文，内部记录不自动双语重复。**Owner：** main model。
4. [x] 整合后运行聚焦的 steering、release、Bootstrap、ACTIVE/compact、Skill、Plugin、JSON 与 diff 合同。**Owner：** main model。**Evidence：** 2026-09-04 全部通过。
5. [x] 提交并推送 `release/v0.6.1` 与 `main`，按用户明确授权覆盖 `v0.6.1` Tag，发布非 prerelease 的 Latest Release，并核对远端结果。**Owner：** main model。**Evidence：** GitHub 于 2026-09-04 返回 `draft=false`、`prerelease=false`，Latest API 指向 `v0.6.1`。
