<h1 align="center">guuguo-skills</h1>

<p align="center">
  面向 AI Agent 的可复用技能仓库：统一来源、软链接分发、跨客户端修复、事实驱动工作流。
</p>

<p align="center">
  <a href="./README.md">English README</a>
</p>

<p align="center">
  <a href="#技能列表"><img alt="skills" src="https://img.shields.io/badge/skills-16-2F6F5E"></a>
  <a href="#仓库模型"><img alt="layout" src="https://img.shields.io/badge/layout-source%20repo%20%2B%20symlinks-3B82F6"></a>
  <a href="#校验"><img alt="validation" src="https://img.shields.io/badge/validation-quick_validate%20%2B%20doctor-64748B"></a>
</p>

## 这个仓库解决什么

`guuguo-skills` 用一个版本化仓库维护一组高价值 AI 技能，并通过稳定的本地中转层分发给 Codex、Claude、Antigravity、Qoderwork、Hermes 等客户端。

核心模型：

```text
来源仓库 -> ~/.agents/skills 中转链接 -> 各客户端技能目录
```

这样做的好处是：技能只在一个地方维护，客户端只消费稳定路径；以后更新、替换、迁移来源仓库都不会牵动每个客户端。

## 技能列表

| 技能 | 用途 | 主要资源 |
| --- | --- | --- |
| `ai-drama-review` | 评审 AI 短剧对白、节奏和关系证据。 | `SKILL.md` |
| `ai-video-director-prompt` | 将已锁定脚本编译为导演式视频提示词。 | `SKILL.md` |
| `gg-bilibili-publish` | 通过已登录的 B 站创作中心发布视频或专栏。 | 发布参考与脚本 |
| `gg-character-card` | 制作与验收角色参考卡。 | 角色资产参考 |
| `gg-douyin-ai-video` | 策划和评审抖音 AI 视频。 | `SKILL.md` |
| `gg-drama-library` | 保存短剧原片证据与可复用案例。 | 素材库脚本与参考 |
| `gg-video-analysis` | 分析视频内容和受众证据。 | 分析流程与脚本 |
| `huixiang-director` | 应用生活流短剧导演方法。 | 导演参考 |
| `video-prompt-compiler` | 编译视频提示词和平台生成清单。 | `SKILL.md` |
| `gg-skills-governor` | 巡检、同步、修复和治理多客户端技能链接。 | `scripts/skills_doctor.py` |
| `gg-ai-native-startup-playbook` | 诊断创业阶段，产出 AI 原生创业执行产物。 | `references/stage-cards.md`、`references/artifact-templates.md` |
| `gg-child-psychology-for-content` | 用儿童心理学指导儿童内容、动画、绘本和教育产品创作。 | 中文儿童发展参考 |
| `gg-fact-driven-ai-methodology` | 基于确认事实和证据重建 AI 工作流方法论，避免规则漂移和自我优化失控。 | 双语 UI 元数据 |
| `gg-harness` | 维护轻量 Harness：薄项目地图、需求拷问、验收标准。 | `references/*-template.md`、迁移指南 |
| `gg-clean-mac` | 快速诊断 macOS 磁盘、缓存、swap、大文件夹和卸载残留，并按风险分级给出清理确认建议。 | `references/interaction-protocol.md`、`references/mac-cleaning-targets.md`、`references/uninstall-mode.md`、电脑印象 schema |
| `guuguo-image-gen` | 维护位图生图与运行时素材处理规则；Codex 内使用 `$imagegen`，外部客户端通过 `codex-guuguo` 委托生成。 | `references/design-images.md`、`references/runtime-assets.md`、脚本 |

## 一行安装

使用 `npx` 安装或更新：

```bash
npx --yes github:guuguo/guugo-skills
```

安装器会自动完成：

- 同步仓库到 `~/.agents/sources/skills/guuguo-skills`
- 在 `~/.agents/skills/<skill-name>` 创建 16 个技能的中转链接
- 只针对这 16 个技能修复 Codex、Claude、Antigravity、Qoderwork、Hermes 的客户端链接
- 如果对应客户端不存在，自动跳过，不会为了链接任务创建目标技能目录

如果仓库是 private，需要确保本机 npm/git 使用的 GitHub 凭据能访问 `guuguo/guugo-skills`。

常用安装参数：

```bash
# 安装到自定义来源目录
GUUGO_SKILLS_SOURCE_DIR=/path/to/guuguo-skills npx --yes github:guuguo/guugo-skills

# 使用自定义 canonical skills 目录
GUUGO_SKILLS_CANONICAL_DIR=/path/to/skills npx --yes github:guuguo/guugo-skills

# 只修复指定客户端
GUUGO_SKILLS_TARGETS=codex,claude,hermes npx --yes github:guuguo/guugo-skills

# 只创建 ~/.agents/skills 中转链接，不修复客户端
GUUGO_SKILLS_SKIP_CLIENTS=1 npx --yes github:guuguo/guugo-skills
```

## 手动安装备用方案

没有 `npx` 时，可以手动 clone 后运行安装器：

```bash
mkdir -p ~/.agents/sources/skills
git clone https://github.com/guuguo/guugo-skills.git ~/.agents/sources/skills/guuguo-skills
node ~/.agents/sources/skills/guuguo-skills/scripts/install.js
```

## 仓库模型

推荐来源仓库结构：

```text
~/.agents/sources/skills/guuguo-skills/
  skills/
    gg-skills-governor/
    gg-ai-native-startup-playbook/
    gg-fact-driven-ai-methodology/
    gg-harness/
    gg-clean-mac/
    guuguo-image-gen/
```

对外暴露的 canonical skills 层：

```text
~/.agents/skills/gg-skills-governor
  -> ../sources/skills/guuguo-skills/skills/gg-skills-governor
~/.agents/skills/gg-ai-native-startup-playbook
  -> ../sources/skills/guuguo-skills/skills/gg-ai-native-startup-playbook
~/.agents/skills/gg-child-psychology-for-content
  -> ../sources/skills/guuguo-skills/skills/gg-child-psychology-for-content
~/.agents/skills/gg-fact-driven-ai-methodology
  -> ../sources/skills/guuguo-skills/skills/gg-fact-driven-ai-methodology
~/.agents/skills/gg-harness
  -> ../sources/skills/guuguo-skills/skills/gg-harness
~/.agents/skills/gg-clean-mac
  -> ../sources/skills/guuguo-skills/skills/gg-clean-mac
~/.agents/skills/guuguo-image-gen
  -> ../sources/skills/guuguo-skills/skills/guuguo-image-gen
```

各客户端继续链接 `~/.agents/skills/`，不要直接链接到本仓库内部。中转层是刻意保留的稳定接口。

## 自定义路径

默认路径配置：

```text
canonical skills: ~/.agents/skills/
Codex skills:     ~/.codex/skills/
Claude skills:    ~/.claude/skills/
Antigravity:      ~/.gemini/antigravity/skills/
Qoderwork:        ~/.qoderworkcn/skills/
Hermes:           ~/.hermes/skills/
```

Hermes 的技能目录按品类组织。默认情况下，`gg-skills-governor` 和 `gg-ai-native-startup-playbook` 会链接到 `devops`，`gg-fact-driven-ai-methodology` 和 `gg-harness` 会链接到 `software-development`，`gg-child-psychology-for-content` 会链接到 `creative`，未配置映射的技能会链接到 `imported`。

`skills_doctor.py` 支持自定义来源和目标：

```bash
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py \
  --source /path/to/canonical/skills \
  --target codex \
  --target-dir /path/to/codex/skills
```

也可以只修复某个技能：

```bash
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py \
  --target codex \
  --skill gg-fact-driven-ai-methodology \
  --fix
```

## 校验

校验技能结构：

```bash
for skill in skills/*; do
  python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill"
done
```

检查客户端链接：

```bash
for target in codex claude antigravity qoderwork hermes; do
  python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py \
    --target "$target" \
    --skill ai-drama-review \
    --skill ai-video-director-prompt \
    --skill gg-bilibili-publish \
    --skill gg-character-card \
    --skill gg-douyin-ai-video \
    --skill gg-drama-library \
    --skill gg-video-analysis \
    --skill huixiang-director \
    --skill video-prompt-compiler \
    --skill gg-skills-governor \
    --skill gg-ai-native-startup-playbook \
    --skill gg-child-psychology-for-content \
    --skill gg-fact-driven-ai-methodology \
    --skill gg-harness \
    --skill gg-clean-mac \
    --skill guuguo-image-gen \
    --only-problems
done
```

健康状态下，这 16 个技能不应出现在问题列表中。

## 设计规则

- 每个技能保持自包含：`SKILL.md`、可选 `agents/openai.yaml`、必要的 `scripts/` 或 `references/`。
- 详细材料放进 `references/`，让 Agent 按需加载。
- 确定性维护逻辑放进 `scripts/`。
- 不要把 bundle 技能平铺复制到 `~/.agents/skills/`，使用 symlink 暴露。
- `gg-skills-governor` 中的本地路径都是默认值，不是不可更改的硬编码。

## 当前状态

这个仓库目前聚焦几类可复用工作流：

- 多客户端 AI 技能治理
- AI 原生创业阶段诊断与执行产物
- 基于事实的 AI 方法论重建
- 轻量 Harness 项目地图、需求事实和验收标准维护
- macOS 磁盘、缓存、swap 与本机清理印象诊断

仓库刻意保持小而清晰。新增技能前，需要先确认它有清楚的触发场景、可重复执行的工作流，以及足够值得沉淀的资源。

## AI 视频创作技能统一维护

四个技能统一以本仓库 `skills/` 下的文件为维护真源：

- [gg-douyin-ai-video](skills/gg-douyin-ai-video/SKILL.md)
- [ai-drama-review](skills/ai-drama-review/SKILL.md)
- [ai-video-director-prompt](skills/ai-video-director-prompt/SKILL.md)
- [gg-character-card](skills/gg-character-card/SKILL.md)

全局入口 `~/.agents/skills/<技能名>` 和客户端均通过软链接读取同一份内容。旧来源路径仅保留兼容链接，迁移前原件（含导演技能 Git 历史）保存在 `.migration-backup/`，不再作为维护入口。安装器已包含以上四个技能。

## 短剧素材与视听分析

- [gg-drama-library](skills/gg-drama-library/SKILL.md)：完整桥段、单集情绪、全剧递进与人物适配检索。本机素材目录由 `~/.config/gg-drama-library/config.json` 的 `library_root` 维护。
- [gg-video-analysis](skills/gg-video-analysis/SKILL.md)：通用抽帧、分页接触表、本地 ASR 与视听观察证据。配置位于 `~/.config/gg-video-analysis/config.json`；复用已安装的 video-subtitle-workflow 资源预检脚本，缺失依赖时明确报告。
- [gg-bilibili-publish](skills/gg-bilibili-publish/SKILL.md)：B站视频/专栏发布与台账。配置位于 `~/.config/gg-bilibili-publish/config.json`；台账和成片留在项目目录，不进技能仓库。

由本仓库统一维护、安装器分发，原始素材、发布记录和运行配置保存在仓库外。
