# 验收标准

## 状态

- 状态：implemented
- P0 是否已由用户确认：是
- 最近确认时间：2026-07-06

## 验收表

| 编号 | 对应来源 | 验收条件 | 重要性 | 证据要求 | 状态 |
| --- | --- | --- | --- | --- | --- |
| A1 | `plan.md#范围` | 项目新增 `skills/gg-clean-mac/SKILL.md`，技能名、描述、触发条件和使用边界清晰。 | P0 | `quick_validate.py skills/gg-clean-mac` 通过；人工检查 `SKILL.md`。 | passed |
| A2 | `plan.md#范围` | `SKILL.md` 明确默认只读扫描，不默认删除文件，不默认清理聊天/办公 App 数据。 | P0 | 人工检查“默认只读”“删除前确认”“App 内清理”相关段落。 | passed |
| A3 | `plan.md#范围` | 快速模式被明确定义：优先系统指标、电脑印象路径和本机高频大户，避免默认全盘慢扫。 | P0 | 人工检查快速模式步骤；可用模拟请求验证 agent 会先走快速路径。 | passed |
| A4 | `plan.md#范围` | 电脑印象机制被明确定义：保存路径为 `~/.agents/state/gg-clean-mac/computer-impression.json`，JSON 为唯一长期源文件，字段包含 `machine_summary`、`hotspots`、`preferences`、`recent_scans`、`known_incidents`，并说明更新时机、隐私边界、后续加速方式。 | P0 | 人工检查参考文件或 `SKILL.md`；确认不会把个人画像写进仓库，且不会维护 Markdown/JSON 双状态。 | passed |
| A5 | `plan.md#范围` | 企业微信、微信、飞书/Lark、Claude/ChatGPT 等 App 数据被归入“解释并建议 App 内清理/谨慎处理”，不得作为普通缓存直接删除。 | P0 | 人工检查风险分级表；示例输出包含企业微信处理说明。 | passed |
| A6 | `plan.md#范围` | 所有实际清理行为都必须要求用户确认；快速模式只能加速证据收集与候选项表达，不得跳过确认。 | P0 | 人工检查 `SKILL.md`；模拟“快速清理”请求时仍要求用户确认具体清理项。 | passed |
| A7 | `plan.md#范围` | 技能提供清理建议分级：可直接清、建议 App 内清理、谨慎处理、不建议动。 | P1 | 人工检查输出格式或参考说明。 | passed |
| A8 | `plan.md#范围` | 每个清理候选项必须尽量说明来源、用途、删除影响、重建方式、是否联网、是否可能访问外网、是否可能消耗 VPN 流量。 | P0 | 人工检查输出模板；模拟 `~/.cache/uv`、`.espressif`、Claude `vm_bundles`、企业微信四类候选。 | passed |
| A9 | `plan.md#范围` | 多轮清理看板只在对话内维护；结束后只将摘要写入电脑印象，不把运行过程态或未完成任务流水账持久化。 | P0 | 人工检查 `SKILL.md` 中的多轮清理流程；模拟多轮对话时能输出看板并最终更新摘要。 | passed |
| A10 | `plan.md#范围` | 首版包含 `references/interaction-protocol.md`，明确多轮对话看板、候选编号、确认语法、泛泛确认不授权、执行前复述和执行后复查。 | P0 | 人工检查协议文件；模拟“可以”“都清了”“清理 1”“深扫 5”等输入。 | passed |
| A11 | `plan.md#范围` | 首版包含 `references/computer-impression-schema.md`，定义电脑印象 JSON schema、字段说明、更新/裁剪规则、示例和隐私边界。 | P0 | 人工检查 schema 文件；确认 JSON 是唯一长期源文件，Markdown 仅展示。 | passed |
| A12 | `plan.md#范围` | 首版包含 `references/mac-cleaning-targets.md`，覆盖常见 macOS 大户路径的来源、用途、风险、重建方式和网络/VPN 成本。 | P0 | 人工检查知识库；至少覆盖 uv、Homebrew、go-build、Playwright、JetBrains、Codex、Antigravity、Gemini、Espressif、Claude vm_bundles、企业微信、微信、LarkShell。 | passed |
| A13 | `plan.md#现有系统事实` | 技能首版参考材料包含本机已知高频大户路径，用于未来快速扫描。 | P1 | 检查 `references/` 或 `SKILL.md` 是否列出重点路径。 | passed |
| A14 | `plan.md#约束与风险` | 对 `.codex`、`.antigravity_cockpit`、`.gemini`、`.espressif`、Claude `vm_bundles` 等开发/AI 工具目录给出风险解释。 | P1 | 人工检查参考材料；示例输出能解释这些目录是什么。 | passed |
| A15 | `README.zh-CN.md` | 仓库技能列表更新，加入 `gg-clean-mac` 的一句话用途和主要资源。 | P1 | `README.zh-CN.md`/`README.md` diff。 | passed |
| A16 | `scripts/install.js` / `package.json` | 安装/同步逻辑包含 `gg-clean-mac`，不会遗漏 canonical links 和客户端链接修复。 | P0 | 运行或静态检查安装脚本中的技能清单。 | passed |

## 不作为通过依据

- 只创建空目录或空 `SKILL.md`。
- 只写扫描命令，但没有安全边界和电脑印象更新规则。
- 快速模式直接执行清理，或把“帮我清理”理解成对所有低风险项的授权。
- 只输出“可以删除缓存”，没有说明来源、用途、删除影响和重建成本。
- 只写“可重建”，但不说明是否要联网、是否是外网资源、是否可能消耗 VPN 流量。
- 没有区分聊天数据、开发工具链、会话数据库、模型/虚拟机镜像、包管理器缓存的风险。
- 缺少交互协议，导致“可以”“都清了”“帮我清理”这类泛泛确认触发删除。
- 缺少常见目录知识库，导致无法解释目录来源、用途和恢复成本。
- 将本轮清理看板、运行过程态或未完成任务流水账写入电脑印象。
- 同时维护 Markdown 和 JSON 两份长期电脑印象状态，导致状态不一致。
- 实现者自称完成，但没有运行技能结构校验。
- 未检查安装脚本和 README 是否纳入新技能。

## 待确认验收

| 编号 | 问题 | 推荐答案 | 风险 | 状态 |
| --- | --- | --- | --- | --- |
| QA1 | P0 验收是否需要用户确认后才能从 draft 改为 confirmed？ | 是。 | 中高风险清理技能不应由实现者单方面定义通过。 | confirmed |
| QA2 | 是否要求实现阶段实际运行一次本机快速扫描作为验收？ | 本次未要求；后续第一次用 `$gg-clean-mac` 清理时执行只读快速扫描。 | 没有实测可能无法发现输出是否足够快、是否命中重点。 | deferred |

## 执行验收记录

> 执行完成后必须回填。本节记录最终证据，不记录运行过程态。证据较多时，创建同目录 `result.md` 并在此链接。

- 执行状态：completed
- 执行方式：normal agent + skill-creator + gg-harness acceptance record
- 执行时间：2026-07-06
- 执行者/会话：Codex 当前会话
- 关联提交/PR/变更摘要：未提交；新增 `skills/gg-clean-mac/`，更新 README、安装脚本，修复 `gg-skills-governor` frontmatter YAML 引号问题。
- 详细结果文件：无

### 验收项结果

| 编号 | 状态 | 实际证据 | 说明 |
| --- | --- | --- | --- |
| A1-A16 | passed | `quick_validate.py skills/gg-clean-mac` 通过；全量 `for skill in skills/*; do quick_validate.py "$skill"; done` 通过；`node --check scripts/install.js` 通过；`node scripts/install.js` 成功链接 `gg-clean-mac`；`skills_doctor.py --target <target> --skill gg-clean-mac --only-problems` 显示 codex/claude/antigravity/qoderwork/hermes 均 linked。 | 未执行任何删除或清理命令。 |

### 验证命令与结果

| 命令/检查 | 结果 | 关键输出或证据位置 |
| --- | --- | --- |
| `python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/gg-clean-mac` | passed | `Skill is valid!` |
| `for skill in skills/*; do python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill"; done` | passed | 七个技能均输出 `Skill is valid!` |
| `node --check scripts/install.js` | passed | 无语法错误输出 |
| `node scripts/install.js` | passed | 已链接 `~/.agents/skills/gg-clean-mac`，并修复 codex/claude/antigravity/qoderwork/hermes links |
| `for target in codex claude antigravity qoderwork hermes; do python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target "$target" --skill gg-clean-mac --only-problems; done` | passed | 每个目标 `counts.linked = 1`，问题列表为空 |

### 独立审查

- Spec review：自查完成，验收项 A1-A16 对应实现均已核对。
- Code review：未做独立代码评审。
- 人工验收：待用户确认。

### 未验证项与风险

- 本次没有执行真实清理，也没有删除任何用户文件。
- 本次没有运行完整本机快速扫描；第一次实际调用 `$gg-clean-mac` 时应按技能做只读快速扫描，并在用户确认后才允许清理。
- 电脑印象文件最终保存路径已实现为规范说明：`~/.agents/state/gg-clean-mac/computer-impression.json`。
- 电脑印象格式已实现为 JSON 唯一长期源文件，Markdown 只用于展示。
- 多轮清理状态策略已实现为对话内看板 + 结束后摘要入印象。
- 逐项确认格式已实现为编号/路径语法；泛泛确认不能触发清理。
