# Requirement `plan.md` Template

Create under:

```text
docs/harness/specs/YYYYMMDD-中文短名/plan.md
docs/harness/specs/YYYYMMDD-版本-中文短名/plan.md
```

Use this as a fact document, not an engineering management template. Do not add people-days, staffing plans, release plans, or implementation tasks unless the requirement fact itself needs them.

```md
# {需求名}

## 状态

- 状态：draft / confirmed / blocked
- 版本归属：{无明确版本 / v1.4 / 2026q3 / r2 / ...}
- 最近确认人：{用户/角色}
- 最近确认时间：{YYYY-MM-DD}

## 目标

{说明要解决什么问题，为什么现在要做，成功后外部可观察结果是什么。}

## 用户与场景

- 目标用户：
- 主要场景：
- 关键用户路径：

## 产品决策补充（适用时）

{仅当需求涉及用户可见行为、产品投入、受控发布或上线效果时，按 `product-decision-template.md` 写入适用的“用户价值发布稿 / 目标与观测 / 决策与取舍 / 发布与回滚”；普通工程任务删除本节。}

## 不变项

- 业务语义：{必须保持的口径和外部行为}
- 事务边界：{继续复用的提交/回滚边界}
- 调度与并发：{保持不变的触发、顺序和并发模型}
- 数据与事实源：{保持不变的数据结构、主事实源和兼容语义}
- 核心实现：{优先复用、不在本期重写的业务逻辑}

## 参考实现与能力继承（适用时）

{仅当需求明确复刻、迁移、替换、对齐或参考成熟实现时保留；普通需求删除本节。参考对象必须固定到仓库和不可变 commit/tag，不能只写分支名。}

- 参考实现：{仓库、commit/tag、相关路径}
- 选择依据：{生产表现、测试、压测、故障历史或其他直接证据}
- 允许偏离边界：{已确认的差异；没有则写“无”}

| 源能力 | 分类 | 源实现机制 | 已验证价值/基线 | 目标实现 | 继承状态 | 偏离证据与替代机制 |
| --- | --- | --- | --- | --- | --- | --- |
| {capability} | 业务不变项 / 成熟优势 / 普通选择 / 历史或平台包袱 | {mechanism} | {evidence/baseline/unknown} | {reuse/adapter/equivalent/redesign} | inherited / deviated / not-applicable | {required for P0 deviation} |

## 证据与故障映射

只有用户事实、日志、Heap/Profile、代码路径、测试、压测或强制稳定规范支持的问题才能进入首期。无直接证据的风险进入“后续观察/可选优化”。

| 已确认问题 | 证据 | 最小修复机制 | 为什么不能更简单 |
| --- | --- | --- | --- |
| {failure} | {fact/log/code/test/constraint} | {smallest guard/bound/checkpoint/adapter} | {reason} |

## 范围

### 必须修复

- {由证据证明、阻塞目标或 P0 验收的问题}

### 本期最小闭环

- {优先包裹现有边界、复用内部逻辑的最小改动}

### 后续观察 / 可选优化

- {可能有价值但没有证据证明为首期必要的优化，以及触发升级的量化条件}

### 不做

- {非目标}

## 复杂度预算

首期默认不新增业务表、第二事实源、并发维度、线程/连接池规模、核心业务重写或非必要状态。若突破默认值，逐项填写；没有则明确写“无”。

| 新增机制 | 对应的已确认问题/约束 | 更简单替代为何不足 | 是否首期必要 |
| --- | --- | --- | --- |
| {table/state/queue/worker/concurrency/rewrite} | {evidence mapping} | {reason} | 是 / 否，移至后续 |

## 已确认事实

- {fact}

## 推荐假设

- {assumption and risk}

## 待确认问题

| 优先级 | 问题 | 推荐答案 | 不确认的影响 | 状态 |
| --- | --- | --- | --- | --- |
| P0 | {question} | {recommendation} | {impact} | open |

## 现有系统事实

- {来自代码、文档、接口、历史实现的事实}

## 约束与风险

- {接口/数据/权限/兼容/安全/并发/跨系统/体验风险}

## 稳定规范引用

- `{path}`：{为什么要读}

## 持久子需求判断

- 是否需要 `sub-*.md`：否 / 是
- 判断理由：
- 如果需要，子需求文件：

## 验收标准引用

- `acceptance.md`

## 执行交接

- 执行层由用户运行时指定；本需求文档不绑定 Superpowers、普通 agent 或其他执行技能。
- 执行前必须读取 `acceptance.md`。
- 执行完成声明必须回填 `acceptance.md#执行验收记录`，或创建并链接同目录 `result.md`。
- 执行层不得擅自改写本文件的需求事实；如发现事实变化，先记录建议并等待用户确认。

## 变更记录

| 日期 | 变更 | 来源 |
| --- | --- | --- |
```

Rules:

- P0 unresolved means `blocked/draft`.
- P1/P2 may continue as recommended assumptions if clearly labeled.
- Do not copy acceptance tables into `plan.md`; use `acceptance.md`.
- Do not write execution-layer task breakdowns here.
- Do not record runtime progress here; final evidence belongs in `acceptance.md` or `result.md`.
- Write `不变项` and evidence mapping before proposing architecture.
- Prefer a bounded wrapper around the current implementation over an internal rewrite.
- Keep unproven risks and useful-but-nonessential optimizations out of first-release scope.
- If review mostly removes mechanisms, rewrite the scope from the minimum closed loop instead of preserving the oversized draft incrementally.
- For product decisions, read `product-decision-template.md` and include only sections justified by user impact, decision uncertainty, or rollout risk.
- For reference-implementation requirements, pin an immutable source and classify capabilities before solution design. Preserve business invariants and evidence-backed advantages; do not require structural copying of ordinary choices or legacy baggage.
