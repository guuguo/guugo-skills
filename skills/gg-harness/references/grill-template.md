# `grill.md` Template

Use this beside `plan.md` to record target calibration. The point is to prevent wrong goals from becoming durable project facts.

```md
# 目标校准记录

## 背景

- 需求目录：
- 输入材料：
- 校准时间：

## 当前理解

- 需求目标：
- 本期成功标准：
- 不变项：
- 已确认故障证据：
- 最小闭环：
- 主要非目标：

## 问题预算

- AGENTS 初始化/升级：最多 8 问
- 需求 plan.md：最多 12 问
- 验收 acceptance.md：最多 6 问

## 问题记录

| 编号 | 优先级 | 问题 | 推荐答案 | 判断依据 | 如果错了的影响 | 用户答复 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Q1 | P0 | {question} | {recommendation} | {basis} | {impact} | {answer} | confirmed/open |

## 已确认结论

- {confirmed fact}

## 第一性原理与复杂度审查

| 检查项 | 结论 | 依据/处理 |
| --- | --- | --- |
| 是否先写清业务语义、事务、调度、事实源和核心实现的不变项？ | 是 / 否 | {detail} |
| 首期每个问题是否都有直接证据或强制约束？ | 是 / 否 | {mapping} |
| 是否优先包裹故障边界，而不是重写内部？ | 是 / 否 | {lower-complexity alternative} |
| “能优化”和“必须修复”是否已经分开？ | 是 / 否 | {deferred items} |
| 是否新增表、第二事实源、状态、队列、并发、线程/连接或核心重写？ | 是 / 否 | {each mechanism and evidence} |
| 删除任一新增机制后，最小闭环是否仍能通过 P0 验收？ | 是 / 否 | {remove/defer decision} |
| 本轮评审主要是在补缺口，还是持续删除过度设计？ | 补缺口 / 删除设计 | 若主要删除，回到不变项和证据重写范围 |

## 参考实现继承校准（适用时）

仅当需求明确复刻、迁移、替换、对齐或参考成熟实现时保留。

| 检查项 | 结论 | 依据/处理 |
| --- | --- | --- |
| 参考实现是否已固定到仓库和不可变 commit/tag，而非只有分支名？ | 是 / 否 | {source and paths} |
| 哪些业务不变项和已有成熟优势必须继承？ | {list} | {evidence} |
| 哪些内容只是普通实现选择或历史/平台包袱，不应机械复制？ | {list} | {reason} |
| 是否存在 P0 能力偏离；偏离是否有证据、替代机制和用户确认？ | 是 / 否 | {deviation decision} |

## 产品决策校准（适用时）

仅在需求涉及用户问题、产品投入、发布策略或效果声明时，按 `product-decision-template.md` 记录必要结论：问题是否有外部证据、价值发布稿能否脱离方案成立、基线/目标/窗口是否可信、主要取舍和置信度是否透明、发布门槛与回滚是否可观察。内部 `grill-me` 不能替代用户访谈、行为数据或其他外部证据。

## 推荐假设

- {assumption}

## 阻塞项

- {P0 blocker, if any}
```

Use these priorities:

- P0: blocks direction, scope, hard boundary, or P0 acceptance.
- P1: important, but can proceed with a labeled recommendation.
- P2: useful detail; record assumption instead of asking.
