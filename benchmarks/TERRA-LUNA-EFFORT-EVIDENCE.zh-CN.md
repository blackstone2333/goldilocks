# Terra / Luna 思考等级证据

[English](TERRA-LUNA-EFFORT-EVIDENCE.md)

这是 Goldilocks Standard 与 Night Shift 默认路线背后的脱敏公开记录。四个独立 Owner 在同一项冻结复杂编程任务、种子仓库、隐藏裁判、宿主 Harness 和遥测口径下运行。四组都通过了可见测试、11 项隐藏验收、编译、diff、范围以及模型与思考等级身份门禁。

| 方案 | 质量 | 观察耗时 | Raw Token | 官方费率代理估算 |
|---|---:|---:|---:|---:|
| Terra Medium | 通过 | 249.043 秒 | 241,689 | $0.212937 |
| Terra XHigh | 通过 | 560.981 秒 | 525,706 | $0.523867 |
| Terra Max | 通过 | 695.082 秒 | 428,766 | $0.602954 |
| Luna Max | 通过 | 1,275.764 秒 | 1,449,579 | $0.122976 |

在这项任务中，Luna Max 的观察耗时约为 Terra Medium 的 **5.12 倍**，官方费率代理估算则低 **42.25%**。Luna 使用的 Raw Token 约为 6 倍。因此 Night Shift 是“用等待换低价”，不是 Token 效率更高。

由于各组共享服务商，耗时只作为观察值。美元数字按冻结 Harness 使用的公开标准 Token 费率折算，只是比较估算，不是实际账单。这一项任务不能证明普遍的模型排行榜。

同一协议还把 Spark 作为无公开价格的能力参照单独测试。Spark Medium 漏掉一项隐藏的持久化不变量；预先约定的 Spark XHigh 追加单元通过全部 11 项隐藏验收，用时 137.458 秒，Raw Token 为 600,737。Spark 没有公开数值费率，因此美元值是 `N/A`，绝不是零。

## 来源校验

- 冻结四组 Manifest SHA-256：`ecaef6cd769e0cf59bcb7a7d4844d9714ce8891e17ebd815c1594a106d98d2cc`
- Host Harness SHA-256：`efa343fcc4293046f363b3e132c99f60aae444f0bf598af1b771ffb1a755e41f`
- 封闭四组结果 SHA-256：`0eb3485150b1106c3e272f10098196fa3e65785e2bdf96af9792c8e7cee17dc0`
- Spark 参照摘要 SHA-256：`fd021ceb8cdcaff05c7ab1cb13c9c0d399eed60014eb15d291320036b2766e15`

原始评测工作区、凭据、缓存和本机会话状态不会进入公开仓库。
