<h1 align="center">guugo-skills</h1>

<p align="center">
  面向 AI Agent 的可复用技能仓库：统一来源、软链接分发、跨客户端修复、事实驱动工作流。
</p>

<p align="center">
  <a href="./README.md">English README</a>
</p>

<p align="center">
  <a href="#技能列表"><img alt="skills" src="https://img.shields.io/badge/skills-3-2F6F5E"></a>
  <a href="#仓库模型"><img alt="layout" src="https://img.shields.io/badge/layout-source%20repo%20%2B%20symlinks-3B82F6"></a>
  <a href="#校验"><img alt="validation" src="https://img.shields.io/badge/validation-quick_validate%20%2B%20doctor-64748B"></a>
</p>

## 这个仓库解决什么

`guugo-skills` 用一个版本化仓库维护一组高价值 AI 技能，并通过稳定的本地中转层分发给 Codex、Claude、Antigravity、Qoderwork 等客户端。

核心模型：

```text
来源仓库 -> ~/.agents/skills 中转链接 -> 各客户端技能目录
```

这样做的好处是：技能只在一个地方维护，客户端只消费稳定路径；以后更新、替换、迁移来源仓库都不会牵动每个客户端。

## 技能列表

| 技能 | 用途 | 主要资源 |
| --- | --- | --- |
| `skills-governor` | 巡检、同步、修复和治理多客户端技能链接。 | `scripts/skills_doctor.py` |
| `ai-native-startup-playbook` | 诊断创业阶段，产出 AI 原生创业执行产物。 | `references/stage-cards.md`、`references/artifact-templates.md` |
| `fact-driven-ai-methodology` | 基于确认事实和证据重建 AI 工作流方法论，避免规则漂移和自我优化失控。 | 双语 UI 元数据 |

## 一行安装

使用 `npx` 安装或更新：

```bash
npx --yes github:guuguo/guugo-skills
```

安装器会自动完成：

- 同步仓库到 `~/.agents/sources/skills/guugo-skills`
- 在 `~/.agents/skills/<skill-name>` 创建三个技能的中转链接
- 只针对这三个技能修复 Codex、Claude、Antigravity、Qoderwork 的客户端链接

如果仓库是 private，需要确保本机 npm/git 使用的 GitHub 凭据能访问 `guuguo/guugo-skills`。

常用安装参数：

```bash
# 安装到自定义来源目录
GUUGO_SKILLS_SOURCE_DIR=/path/to/guugo-skills npx --yes github:guuguo/guugo-skills

# 使用自定义 canonical skills 目录
GUUGO_SKILLS_CANONICAL_DIR=/path/to/skills npx --yes github:guuguo/guugo-skills

# 只修复指定客户端
GUUGO_SKILLS_TARGETS=codex,claude npx --yes github:guuguo/guugo-skills

# 只创建 ~/.agents/skills 中转链接，不修复客户端
GUUGO_SKILLS_SKIP_CLIENTS=1 npx --yes github:guuguo/guugo-skills
```

## 手动安装备用方案

没有 `npx` 时，可以手动 clone 后运行安装器：

```bash
mkdir -p ~/.agents/sources/skills
git clone https://github.com/guuguo/guugo-skills.git ~/.agents/sources/skills/guugo-skills
node ~/.agents/sources/skills/guugo-skills/scripts/install.js
```

## 仓库模型

推荐来源仓库结构：

```text
~/.agents/sources/skills/guugo-skills/
  skills/
    skills-governor/
    ai-native-startup-playbook/
    fact-driven-ai-methodology/
```

对外暴露的 canonical skills 层：

```text
~/.agents/skills/skills-governor
  -> ../sources/skills/guugo-skills/skills/skills-governor
~/.agents/skills/ai-native-startup-playbook
  -> ../sources/skills/guugo-skills/skills/ai-native-startup-playbook
~/.agents/skills/fact-driven-ai-methodology
  -> ../sources/skills/guugo-skills/skills/fact-driven-ai-methodology
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
```

`skills_doctor.py` 支持自定义来源和目标：

```bash
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py \
  --source /path/to/canonical/skills \
  --target codex \
  --target-dir /path/to/codex/skills
```

也可以只修复某个技能：

```bash
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py \
  --target codex \
  --skill fact-driven-ai-methodology \
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
for target in codex claude antigravity qoderwork; do
  python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py \
    --target "$target" \
    --skill skills-governor \
    --skill ai-native-startup-playbook \
    --skill fact-driven-ai-methodology \
    --only-problems
done
```

健康状态下，这三个技能不应出现在问题列表中。

## 设计规则

- 每个技能保持自包含：`SKILL.md`、可选 `agents/openai.yaml`、必要的 `scripts/` 或 `references/`。
- 详细材料放进 `references/`，让 Agent 按需加载。
- 确定性维护逻辑放进 `scripts/`。
- 不要把 bundle 技能平铺复制到 `~/.agents/skills/`，使用 symlink 暴露。
- `skills-governor` 中的本地路径都是默认值，不是不可更改的硬编码。

## 当前状态

这个仓库目前聚焦三类可复用工作流：

- 多客户端 AI 技能治理
- AI 原生创业阶段诊断与执行产物
- 基于事实的 AI 方法论重建

仓库刻意保持小而清晰。新增技能前，需要先确认它有清楚的触发场景、可重复执行的工作流，以及足够值得沉淀的资源。
