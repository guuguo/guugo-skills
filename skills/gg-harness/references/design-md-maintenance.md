# 视觉文件维护方案（DESIGN.md）

本文件定义 `gg-harness` 下视觉规范文件的独立维护方案。视觉规范采用
[DESIGN.md 开放格式](https://github.com/google-labs-code/design.md)（Google Labs，Apache-2.0），
它是给编码 agent 用的「视觉身份」描述：让同一套外观在不同会话、不同工具、不同 agent 之间保持一致。

## 为什么单独维护

视觉规范是**跨周期的长期事实**，不是某一个需求的产物：

- 它随品牌/视觉身份变化而更新，节奏和功能需求完全不同。
- 多个 UI 需求共享同一份视觉源；复制进每个 `plan.md` 会立刻发散。
- 它需要被外部工具链（linter、Stitch、Figma/Tailwind 互转）直接发现。

因此视觉文件**不走需求周期**（不写 `plan.md` / `grill.md` / `acceptance.md`），而是作为
`_stable/` 级别的事实独立维护，由触达 UI 的需求引用并遵守。

## 权威源与位置

- 唯一权威源：**项目根目录 `DESIGN.md`**。遵循开放格式惯例，外部工具/其它 agent/linter 默认按根目录查找。
- `docs/harness/specs/_stable/design-guidelines.md` 退化为**指针**：一句话指向根 `DESIGN.md`，不复制内容。
- `_stable/index.md` 与 `AGENTS.md` 各登记一行索引，写明「何时读取」。
- 子品牌/多主题时，可加 `DESIGN.<变体>.md`（如 `DESIGN.dark.md`），同样登记索引；不要把变体内容塞进主文件。

## DESIGN.md 格式速记

一个 `DESIGN.md` = 可选 YAML frontmatter（机器读的 design tokens）+ Markdown 正文（人读的设计理由）。
**Token 是规范值，正文解释怎么用。Token 是上下文，不是渲染指令。**

固定章节顺序（不相关可省略，出现的需按此序、用 `##`）：

1. **Overview**（Brand & Style）— 品牌性格、受众、想唤起的情绪
2. **Colors** — 至少 `primary`；常用 `primary/secondary/tertiary/neutral`
3. **Typography** — 一般 9–15 级，语义命名 `headline/display/body/label/caption` + `sm/md/lg`
4. **Layout**（Layout & Spacing）— 栅格/间距策略
5. **Elevation & Depth** — 层级如何表达（阴影 or 边框/色彩对比）
6. **Shapes** — 圆角/形状语言
7. **Components** — 按钮/输入框等原子组件，含状态变体
8. **Do's and Don'ts** — 护栏

Token schema（embed 在 frontmatter，跨引用用 `{path.to.token}`）：

```yaml
---
version: alpha
name: <设计系统名>
description: <可选>
colors:        # map<string, Color>，Color = 任意合法 CSS 颜色，推荐 #RRGGBB
  primary: "#1A1C1E"
typography:    # map<string, Typography>
  h1: { fontFamily: Public Sans, fontSize: 48px, fontWeight: 600, lineHeight: 1.1, letterSpacing: -0.02em }
rounded:       # map<string, Dimension(px/em/rem)>
  md: 8px
spacing:       # map<string, Dimension | number>
  md: 16px
components:    # map<string, map<string, string>>，值可引用其它 token
  button-primary: { backgroundColor: "{colors.primary}", rounded: "{rounded.md}", padding: 12px }
  button-primary-hover: { backgroundColor: "{colors.primary-70}" }
---
```

可自由扩展 spec 未定义的 key/章节（如 `motion`、`iconography`）；linter 接受，agent 读正文。
重复 `## Colors` 这类同名章节是错误，应拒绝。

## 编写理念（最重要，源自 DESIGN.md PHILOSOPHY）

1. **正文 > Token**：生成质量取决于意图描述得多清楚，而非数值多精确。
2. **具体参照 > 一堆形容词**：「1970 年代老牌大学的研究生讲义」唤起一整个世界；「现代、干净、可信、高级」什么都没说清，只会产出平庸的「正中间」。形容词描述一片区域，具体参照描述一个点。
3. **负向约束自带在参照里**：说出对象名就排除了它不是什么；Do/Don't 清单太长往往说明前面描述太含糊。

## 维护生命周期

- **创建**：先写一句具体的 Overview 参照，再补 Colors/Typography 等章节，最后才填 token。先正文后数值。
- **变更**：视觉身份变化时直接改根 `DESIGN.md`；在 `_stable/index.md` 或变更说明里注明受影响的 UI 需求。
- **校验**：可选跑 DESIGN.md linter（`bunx` / 仓库 `design.md` 工具）做 token 合法性与 WCAG 对比度检查；无工具时人工对照章节顺序与 token schema。
- **与需求周期的关系**：触达 UI 的需求，其 `plan.md` 必须在「做」里链接根 `DESIGN.md`，`acceptance.md` 把「符合 DESIGN.md 视觉规范」列为验收项。需求**不得**擅自改写 `DESIGN.md`；如确需调整视觉源，先单独走视觉文件变更并经用户确认。

## AGENTS.md 索引约定

`AGENTS.md` 只登记指针，不嵌内容。建议在「关键目录」加一行、「规则索引」加一行：

```md
## 关键目录
- `DESIGN.md`：项目视觉规范权威源（DESIGN.md 开放格式），UI 工作的单一事实来源。

## 规则索引
- `DESIGN.md`：当需求涉及 UI/视觉/品牌时必读，并在验收中核对一致性。
```
