# `acceptance.md` Template

Acceptance is a first-class document. AI drafts it, but humans must confirm P0 items for medium/high-risk work.

```md
# 验收标准

## 状态

- 状态：draft / confirmed / blocked
- P0 是否已由用户确认：是 / 否
- 最近确认时间：{YYYY-MM-DD}

## 验收表

用本节承接 `plan.md` 的“验证”。每条验收条件都必须可观察、可复核，并说明证据要求。

| 编号 | 对应来源 | 验收条件 | 重要性 | 证据要求 | 状态 |
| --- | --- | --- | --- | --- | --- |
| A1 | `plan.md` | {总体可交付条件} | P0 | {测试/截图/日志/人工确认/执行层审查} | pending |
| A2 | `plan.md#范围` | {范围条件} | P1 | {验证方式} | pending |
| A3 | `plan.md#不变项` | {旧新业务语义、事务、调度和事实源保持一致} | P0 | {黄金样例/对照测试/调用与事务边界证据} | pending |
| A4 | `plan.md#复杂度预算` | {所有首期新增机制均可追溯到已确认问题，后续优化未混入首期} | P0 | {代码与文档 diff、机制到证据映射} | pending |

## 参考实现对等验收（适用时）

仅当 `plan.md` 包含“参考实现与能力继承”时保留。使用同一夹具和可比较条件；只选择与继承能力相关的维度。源基线未知时先测量并记录 `unknown`，不得编造目标。

| 编号 | 继承能力 | 源基线 | 目标通过条件 | 对比方法与允许差异 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| P1 | {business/state/recovery/performance/resource capability} | {measured value/behavior/unknown} | {no-regression or confirmed target} | {same fixture, environment differences, tolerance} | {test/log/profile/diff} | pending |

## 效果观测（适用时）

本节只用于无法在交付时立即证明的用户/业务结果。交付验收与效果观测是两个状态；效果观测 `pending` 不阻塞交付完成，除非该指标被用户明确设为扩量门槛。

| 编号 | 目标 | 基线 | 目标值 | 观测时间点 | 数据来源 | 状态 | 实际证据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| O1 | {outcome} | {baseline/unknown} | {target} | {30/60/90 天或领域周期} | {source} | pending / passed / failed / not-verified / n/a | {evidence} |

## 不作为通过依据

- {例如：只看到代码改了、执行层自称完成、旧 passes=true、未验证截图等}

## 待确认验收

| 编号 | 问题 | 推荐答案 | 风险 | 状态 |
| --- | --- | --- | --- | --- |

## 执行验收记录

> 执行完成后必须回填。本节记录最终证据，不记录运行过程态。证据较多时，创建同目录 `result.md` 并在此链接。

- 执行状态：not-started / in-progress / passed / failed / partially-passed / blocked
- 执行方式：{普通 agent / Superpowers / 其他技能或插件}
- 执行时间：{YYYY-MM-DD HH:mm}
- 执行者/会话：{agent / thread / reviewer，如适用}
- 关联提交/PR/变更摘要：{commit / PR / changed files}
- 详细结果文件：{无 / `result.md`}

### 验收项结果

| 编号 | 状态 | 实际证据 | 说明 |
| --- | --- | --- | --- |
| A1 | passed / failed / not-verified / n/a | {命令、截图、日志、人工确认、review 结论} | {说明} |

### 验证命令与结果

| 命令/检查 | 结果 | 关键输出或证据位置 |
| --- | --- | --- |
| `{command}` | pass / fail / not-run | {摘要} |

### 独立审查

- Spec review：{未做 / 通过 / 未通过 / 不适用；证据}
- Code review：{未做 / 通过 / 未通过 / 不适用；证据}
- 人工验收：{未做 / 通过 / 未通过 / 不适用；证据}

### 未验证项与风险

- {未验证项、失败项、风险、后续动作}
```

Rules:

- Quantify what can be quantified.
- For fuzzy quality, define a comparison method.
- Mark draft when P0 acceptance is not confirmed.
- Do not let the implementer redefine P0 pass conditions.
- Do not claim completion when any P0 item is failed or not verified, unless the user explicitly accepts the exception.
- Keep runtime progress outside specs; only final evidence belongs here.
- Require old/new behavior comparison for every declared invariant that the implementation touches.
- Do not make deferred observations or optional optimizations block the minimum release unless new evidence and user confirmation move them into scope.
- Reject a mechanism that has no mapping to a confirmed failure, explicit user constraint, or stable mandatory rule.
- Treat execution `passed` as delivery acceptance only; do not imply that pending post-launch outcomes were achieved.
- Do not mark an outcome passed before its observation window closes or without the declared evidence source.
- For reference-implementation requirements, do not accept “the feature works” as parity evidence. Verify every P0 inherited capability or record a user-confirmed deviation with replacement evidence.
