# Project `docs/harness/version.md` Template

Create or update this file in the target project, not inside the skill.

```md
# Harness 版本

## 当前状态

- gg-harness 本地版本：{0.3.0 / unknown}
- 最近检查时间：{YYYY-MM-DD}
- 最近迁移人：{用户/agent}
- 状态：current / needs-upgrade / unknown / blocked

## 版本记录

| 日期 | 版本 | 变更摘要 | 迁移行为 |
| --- | --- | --- | --- |
| {YYYY-MM-DD} | `{version}` | {一两句话说明本次 gg-harness 规则变化} | {一两句话说明项目做了什么迁移；没有则写“无需迁移”} |

## 本地偏差

- {项目选择保留的例外、未迁移项、原因和风险}

## 下次升级检查

- 对照当前技能 `references/harness-version.md`。
- 只处理高于本地版本的迁移项。
- 迁移 `AGENTS.md`、`docs/harness/specs/`、`acceptance.md`、`_stable/` 前必须先给出建议并获得用户确认。
```

Rules:

- Keep each version record short.
- Do not store runtime progress here.
- Do not overwrite user-specific local deviations; document them.
