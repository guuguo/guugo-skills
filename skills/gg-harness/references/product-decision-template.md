# Product Decision Addendum

Use this reference only when a requirement changes user-visible product behavior, commits meaningful product investment, needs controlled rollout, or claims a measurable post-launch outcome. Do not use it for routine bugs, internal refactors, documentation, or configuration unless user impact or rollout risk makes the fields material.

Copy only the applicable sections into the existing `plan.md`, `grill.md`, and `acceptance.md`. Do not create another project file.

## Evidence rule

- State the problem and supporting evidence before proposing a solution.
- Separate confirmed facts, recommended assumptions, and unresolved questions.
- Use external evidence appropriate to the claim: behavior data, support or sales signals, revenue/retention, experiments, usability observations, or target-user interviews.
- `grill-me` tests internal coherence; it does not validate external reality.
- If interviews are the main available discovery evidence, treat five target-user interviews as a recommended starting point, not statistical proof or a universal gate. Continue or segment research when signals conflict or the decision has high cost or blast radius.
- Write an unknown baseline as `unknown` and define how to measure it. Never invent a baseline, target, confidence, or customer finding to complete the template.

## `plan.md` sections

### 用户价值发布稿

Write one short paragraph before solution detail:

> 面向 `{目标用户}`，他们当前因为 `{已证实的问题}` 而无法 `{期望结果}`。本次变化将让他们 `{可观察的新结果}`，现在值得解决是因为 `{时机与证据}`。我们将通过 `{指标与观测窗口}` 判断它是否真正产生价值。

If this paragraph cannot be written without unsupported claims, keep the requirement `draft` and return to problem evidence, or redefine the work as a bounded evidence-gathering experiment with explicit acceptance. Do not present an experiment as a validated product plan.

### 目标与观测

| 目标 | 当前基线 | 目标值 | 观测窗口 | 数据来源 | 置信度 |
| --- | --- | --- | --- | --- | --- |
| {user/business outcome} | {value/unknown} | {target/unknown} | {7/30/60/90 days or domain cadence} | {analytics/log/support/interview} | high/medium/low + reason |

Use the shortest window that can observe the claimed effect. Do not default to 30/60/90 days when the signal appears immediately or requires a longer cycle.

### 决策与取舍

Record only choices that materially affect scope, user behavior, architecture, cost, risk, or reversibility.

| 决策 | 候选方案 | 当前选择 | 主要取舍 | 置信度 | 重新评估条件 |
| --- | --- | --- | --- | --- | --- |
| {decision} | {A/B/defer} | {choice} | {benefit given up / risk accepted} | {high/medium/low + evidence} | {new evidence or threshold} |

### 发布与回滚

Use this section only when staged exposure or rollback materially reduces risk.

| 阶段 | 范围/人群 | 进入门槛 | 成功门槛 | 停止扩量/回滚条件 |
| --- | --- | --- | --- | --- |
| {internal/beta/percentage/GA} | {cohort} | {precondition} | {observable gate} | {threshold or failure class} |

- Rollback method and owner/authority:
- Data or side-effect compensation when rollback is incomplete:
- User/stakeholder communication required on rollback:

## `grill.md` checks

Record only decision-relevant findings:

- Does the value narrative describe a verified problem rather than marketing a preferred solution?
- Is the external evidence proportionate to uncertainty, cost, reversibility, and blast radius?
- Are missing baselines and weak-confidence assumptions visible rather than filled with invented precision?
- Would a smaller option test the same value hypothesis with less irreversible investment?
- Are rollout gates and revisit conditions tied to observable evidence?

## `acceptance.md` outcome observation

Use the effect-observation table in `acceptance-template.md` and keep delivery acceptance and outcome observation separate.

- `passed` delivery means the confirmed capability was shipped and its immediate P0 checks passed.
- `pending` outcome observation does not block delivery completion unless it is an explicit rollout gate.
- Do not mark an outcome `passed` before the observation time or without the stated evidence.
- When a metric misses, record the disproven assumption and the decision it changes; do not rewrite the original target after seeing results.
