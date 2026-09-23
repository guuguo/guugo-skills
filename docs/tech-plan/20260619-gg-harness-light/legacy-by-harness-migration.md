# 旧 by-harness 项目迁移指南

本文是 `gg-harness` 的按需子文档。只有当用户明确希望把旧 `by-harness` 项目迁移到 `gg-harness` 轻方案时才读取。

迁移目标不是把旧 runtime 升级成新 runtime，也不是把 `.harness/` 过程态搬到新结构里；目标是把仍然有长期价值的项目地图、需求事实、验收标准和稳定规则迁移到 `gg-harness` 的轻结构中。

## 一、迁移原则

- 不做脚本化迁移，不运行旧 `by-harness` 的 `update_runtime.py`、`scaffold.py` 或自动升级脚本。
- 不自动删除旧目录，不覆盖已有 `AGENTS.md`，不静默丢弃任何无法判断价值的内容。
- 先审计，后给推荐迁移方案；用户确认后，agent 才能逐步落盘。
- 只迁移长期事实，不迁移执行过程态。
- 旧任务拆分、运行记录、progress、runs、route、evidence 只作为历史参考或归档线索，不进入 `docs/harness/specs/`。
- 迁移后的 `AGENTS.md` 仍必须是薄地图，只写项目目标、目录入口、硬边界和规则索引。

## 二、旧产物分类

| 旧 by-harness 产物 | 处理建议 | 目标位置 |
| --- | --- | --- |
| `AGENTS.md` / `CLAUDE.md` 托管块 | 提取项目地图、硬边界、规则索引；生成候选薄 `AGENTS.md`，用户确认后落盘 | `AGENTS.md` |
| `docs/agent-context/agent-rules/` | 审计后保留仍有效的稳定规则；过长规则索引化 | `docs/harness/rules/` 或 `docs/harness/specs/_stable/` |
| `.harness/docs/specs/` | 只迁移仍代表需求事实的内容；不要照搬任务执行拆分 | `docs/harness/specs/<日期[-版本]-中文短名>/plan.md` |
| `.harness/docs/contracts/` | 提取可检查验收条件；去掉执行过程字段 | `docs/harness/specs/<日期[-版本]-中文短名>/acceptance.md` |
| `docs/agent-context/<需求目录>/` | 如果是需求/技术事实文档，按新目录命名规则迁移 | `docs/harness/specs/<日期[-版本]-中文短名>/plan.md` 或 `_stable/` |
| `docs/tech-plan/` | 可建立索引引用；需要纳入 harness 时按单需求迁移 | `docs/harness/specs/<日期[-版本]-中文短名>/` |
| `.harness/task-harness/tasks/` | 不作为新 specs 默认迁移；只作为识别历史需求、验收和 owner 的参考 | 迁移报告 |
| `.harness/task-harness/runs/` | 运行态，不迁移到 specs | 保留原地或按用户要求归档 |
| `.harness/task-harness/progress/` | 历史过程态，不迁移到 specs | 保留原地或按用户要求归档 |
| `.harness/docs/qa/` | 若包含长期验收结论，可摘录到 `acceptance.md`；否则作为历史证据保留 | 迁移报告或原地保留 |
| `docs/harness/contracts/` | 旧验收契约目录。迁移时合并进需求目录内的 `acceptance.md` | `docs/harness/specs/<需求>/acceptance.md` |
| `.harness/config/`、`.harness/scripts/` | runtime 和脚本，不迁移 | 保留原地，后续由用户决定是否清理 |

## 三、迁移步骤

### 1. 建立迁移审计清单

agent 先读取项目根目录，不修改文件，列出旧 `by-harness` 相关入口：

- 是否存在 `AGENTS.md`、`CLAUDE.md`、`<!-- BEGIN BY-HARNESS MANAGED BLOCK -->`。
- 是否存在 `.harness/`、`.harness/task-harness/`、`.harness/docs/`。
- 是否存在 `docs/harness/specs/`、`docs/harness/contracts/`、`docs/harness/rules/`。
- 是否存在 `docs/agent-context/`、`docs/tech-plan/`。
- 是否存在旧 Java 规则、分布式规则或项目专用硬门禁。

输出迁移审计清单，标明每类内容建议为：

- 保留为薄地图。
- 迁移为需求事实。
- 迁移为验收标准。
- 迁移为稳定规则或稳定规范。
- 仅归档，不迁移。
- 待用户确认。

### 2. 给出推荐迁移方案

在用户确认前，不改写 `AGENTS.md`，不移动旧目录。

推荐方案至少包含：

- 新 `AGENTS.md` 候选结构。
- 需要创建的 `docs/harness/specs/<日期[-版本]-中文短名>/` 目录清单。
- 每个需求目录的来源文件、迁移理由和风险。
- 需要创建或更新的 `_stable/` 文件。
- 需要创建或更新的 `docs/harness/rules/` 文件。
- 不迁移的运行态目录和原因。
- 需要用户确认的问题。

### 3. 用户确认迁移范围

用户至少确认下面几项后才能落盘：

- 是否改写 `AGENTS.md`。
- 哪些旧需求值得迁移为长期 `plan.md`。
- 哪些旧 contract/QA 结论值得迁移为 `acceptance.md`。
- 哪些规则是项目长期硬边界，哪些只是旧执行层细节。
- 是否保留旧 `.harness/` 目录原样。

如果用户只说“按推荐继续”，agent 可以按推荐方案落盘，但必须在迁移报告中记录哪些是推荐假设。

### 4. 改写薄 `AGENTS.md`

用户确认后，改写 `AGENTS.md`：

- 只保留项目一句话目标、关键目录、工作入口、硬边界和规则索引。
- 删除或迁出旧 by-harness 的 runtime 升级、自动路由、session_close、task_switch、feature_list、QA runner、Java 长规则全文。
- 对旧 `BY-HARNESS MANAGED BLOCK` 的处理必须在迁移报告中说明：保留、替换或移除。
- 不能把旧执行闭环 `read task -> plan -> build -> qa -> fix -> mark_pass` 写成 `gg-harness` 默认流程。

### 5. 迁移需求事实

对每个确认迁移的旧需求：

1. 按 `YYYYMMDD-中文短名` 或 `YYYYMMDD-版本-中文短名` 创建新需求目录。
2. 从旧 spec、tech-plan、task JSON 中提取目标事实，写入 `plan.md`。
3. 明确哪些事实来自旧文档，哪些是推荐假设，哪些待确认。
4. 不复制旧执行步骤、任务状态、passes、owner、run-id 等过程字段。
5. 如果旧任务只是前端/后端/测试/DDL 这种执行拆分，不创建 `sub-*.md`。
6. 只有旧子块具备独立长期事实价值时，才创建 `sub-<中文短名>.md`。

### 6. 迁移验收标准

对每个确认迁移的旧需求：

1. 从旧 contract、QA 结论、任务验收字段中提取可检查验收条件。
2. 写入同一需求目录的 `acceptance.md`。
3. 区分 P0/P1/P2。
4. 标明证据要求：测试、截图、日志、人工确认或执行层审查。
5. 如果旧验收只是“已完成”“QA pass”“passes=true”，不能直接作为 P0 验收；必须改写成可观察条件。

### 7. 迁移稳定规则和稳定规范

稳定规则迁移要克制：

- 项目长期目标、长期 UX/设计规范、通用验收基线、术语表进入 `docs/harness/specs/_stable/`。
- agent 工作规则、目录索引、硬边界进入 `docs/harness/rules/`。
- Java 或分布式规则如果确实仍是项目硬边界，可以索引化保留；不要把全文塞进 `AGENTS.md`。
- 旧执行层规则、runtime 升级规则、自动路由脚本规则不迁移为 `gg-harness` 规则。

### 8. 保留旧运行态

默认不删除：

- `.harness/task-harness/runs/`
- `.harness/task-harness/progress/`
- `.harness/docs/qa/`
- `.harness/config/`
- `.harness/scripts/`

如果用户要求清理，只给出清理建议和备份建议，不直接删除。删除必须由用户再次明确确认。

### 9. 生成迁移报告

迁移完成后，在当前迁移需求目录或 `docs/harness/rules/` 中生成迁移报告，至少包含：

- 迁移日期。
- 已迁移文件清单。
- 未迁移文件清单和原因。
- `AGENTS.md` 变更摘要。
- 新需求目录清单。
- 待确认问题。
- 旧 `.harness/` 保留策略。

推荐文件名：

```text
docs/harness/rules/legacy-by-harness-migration-report.md
```

## 四、完成判定

迁移完成不等于旧任务完成。完成判定只看长期事实是否被安全搬迁：

- `AGENTS.md` 已变成薄地图，且用户确认过关键改写。
- 需要迁移的需求已进入 `docs/harness/specs/<日期[-版本]-中文短名>/plan.md`。
- 需要迁移的验收已进入同目录 `acceptance.md`。
- 稳定规则和规范已索引化，不塞满 `AGENTS.md`。
- 旧运行态没有被误迁移为长期事实。
- 迁移报告记录了保留、迁移、废弃和待确认项。

## 五、禁止事项

- 禁止运行旧 `by-harness` 自动升级脚本来完成迁移。
- 禁止把 `.harness/task-harness/tasks/` 全量转成 `sub-*.md`。
- 禁止把 `runs/progress/evidence` 写入新 specs。
- 禁止直接覆盖 `AGENTS.md`。
- 禁止为了“迁移完整”保留旧执行状态机。
- 禁止把旧 `passes=true` 当成新验收通过。
