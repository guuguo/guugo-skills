# Thin AGENTS.md Template

Use this as a candidate shape. Do not overwrite an existing `AGENTS.md` before user confirmation.

```md
# AGENTS.md

## 项目目标

{一句话说明项目做什么、服务谁、核心结果是什么。}

## 关键目录

- `{path}`：{用途}
- `{path}`：{用途}
- `DESIGN.md`：项目视觉规范权威源（DESIGN.md 开放格式），UI 工作的单一事实来源。{无视觉规范可删此行}
- `docs/harness/version.md`：本项目已应用的 gg-harness 版本、升级记录和本地偏差。
- `docs/harness/specs/`：需求事实、目标校准和验收标准。
- `docs/harness/specs/_stable/`：跨需求长期目标、设计规范、通用验收基线和术语。
- `docs/harness/rules/`：较长的 agent 工作规则和项目硬边界索引。

## 工作入口

- 开始工作前先读本文件。
- 初始化或升级 harness 时，先对照 `docs/harness/version.md` 和当前 gg-harness 技能版本。
- 处理需求时读取对应 `docs/harness/specs/<日期[-版本]-中文短名>/plan.md`。
- 验收以同目录 `acceptance.md` 为准。
- 如需求引用 `_stable/`，按 `plan.md` 中的链接读取。
- 只有存在长期事实价值的例外子需求时，才读取同目录 `sub-*.md`。

## 执行证据契约

- 按需求 `plan.md` 执行时，完成声明必须以同目录 `acceptance.md` 为准。
- 执行完成前，必须在 `acceptance.md` 底部回填验收记录；中高风险或证据较多时，写入同目录 `result.md` 并在 `acceptance.md` 链接。
- 验收记录必须包含执行方式、测试/检查证据、每条验收项状态、未验证项、遗留风险和关联提交/变更摘要。
- P0 验收项失败或未验证时，不能声称需求完成，除非用户明确接受例外。
- 执行层可以生成自己的计划、review 或测试输出，但不能擅自改写 `plan.md` 的需求事实或 `acceptance.md` 的通过条件。

## 硬边界

- 不破坏用户已有改动。
- 不做无关重构。
- 不越过已确认的 P0 验收标准。
- 不让实现者自判通过；验收必须对照 `acceptance.md`。
- 不把执行层运行过程态写回 `docs/harness/specs/`；只允许写入最终验收证据，或在用户确认后同步需求事实变更。

## 规则索引

- `DESIGN.md`：当需求涉及 UI/视觉/品牌时必读，并在验收中核对一致性。{无视觉规范可删此行}
- `{rule-file}`：{何时读取}
- `{stable-file}`：{何时读取}
```

Checklist:

- Keep the file short.
- Link long rules instead of embedding them.
- Label recommended assumptions if the user has not confirmed them.
- Record the confirmation in the audit report or `grill.md`.
