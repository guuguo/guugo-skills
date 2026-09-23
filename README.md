<h1 align="center">guuguo-skills</h1>

<p align="center">
  A compact source repository for reusable AI agent skills, designed around
  governed local installs, symlink-based distribution, and fact-first workflows.
</p>

<p align="center">
  <a href="./README.zh-CN.md">中文版 README</a>
</p>

<p align="center">
  <a href="#skills"><img alt="skills" src="https://img.shields.io/badge/skills-16-2F6F5E"></a>
  <a href="#repository-model"><img alt="layout" src="https://img.shields.io/badge/layout-source%20repo%20%2B%20symlinks-3B82F6"></a>
  <a href="#validation"><img alt="validation" src="https://img.shields.io/badge/validation-quick_validate%20%2B%20doctor-64748B"></a>
</p>

## Why This Exists

`guuguo-skills` keeps a small set of high-leverage AI agent skills in one
versioned source repository. The repository is meant to be cloned under a local
skill source directory, then exposed to agent clients through a stable canonical
skill layer.

The key idea is:

```text
source repository -> canonical skill links -> agent-specific skill directories
```

This keeps updates centralized while letting Codex, Claude, Antigravity,
Qoderwork, and Hermes consume the same skill definitions.

## Skills

| Skill | Purpose | Notable resources |
| --- | --- | --- |
| `ai-drama-review` | Review dialogue, rhythm, and dramatic evidence in AI short dramas. | `SKILL.md` |
| `ai-video-director-prompt` | Compile locked scripts into directed video prompts. | `SKILL.md` |
| `gg-bilibili-publish` | Publish AI video or articles through the logged-in Bilibili creator center. | publishing references and scripts |
| `gg-character-card` | Create and verify character reference cards. | character asset references |
| `gg-douyin-ai-video` | Plan and review Douyin AI videos. | `SKILL.md` |
| `gg-drama-library` | Maintain source evidence and reusable short-drama cases. | library scripts and references |
| `gg-video-analysis` | Analyze video content and audience evidence. | analysis workflow and scripts |
| `huixiang-director` | Apply grounded, scene-led short-drama direction. | directing references |
| `video-prompt-compiler` | Compile video prompts and platform-specific generation lists. | `SKILL.md` |
| `gg-skills-governor` | Inspect, sync, repair, and govern skills across agent-specific directories. | `scripts/skills_doctor.py` |
| `gg-ai-native-startup-playbook` | Diagnose startup stage and produce practical AI-native startup artifacts. | `references/stage-cards.md`, `references/artifact-templates.md` |
| `gg-fact-driven-ai-methodology` | Rebuild AI workflow methodologies from confirmed facts and evidence instead of drift-prone self-optimization. | bilingual UI metadata |
| `gg-child-psychology-for-content` | Guide AI animation / short video / picture-book content creation with Piaget, Vygotsky, Erikson, Bowlby, and Montessori. | Chinese, child-development reference |
| `gg-harness` | Maintain a lightweight Harness layer: thin project maps, grilled requirements, and acceptance standards. | `references/*-template.md`, migration guide |
| `gg-clean-mac` | Diagnose macOS disk, cache, swap, large-folder pressure, and uninstall residue, then present risk-ranked cleanup choices that require explicit confirmation. | `references/interaction-protocol.md`, `references/mac-cleaning-targets.md`, `references/uninstall-mode.md`, computer-impression schema |
| `guuguo-image-gen` | Govern bitmap image generation and runtime asset processing; uses `$imagegen` inside Codex and `codex-guuguo` delegation from external clients. | `references/design-images.md`, `references/runtime-assets.md`, scripts |

## Repository Model

Use this repository as a bundle source:

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

Expose individual skills through `~/.agents/skills/`:

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

Then let agent clients point to `~/.agents/skills/`, not directly into this
repository. That middle layer is intentional: it gives each client a stable
consumer path while the source repository remains easy to update or replace.

## Quick Install

Install or update with `npx`:

```bash
npx --yes github:guuguo/guugo-skills
```

The installer will:

- sync this bundle into `~/.agents/sources/skills/guuguo-skills`,
- expose each skill through `~/.agents/skills/<skill-name>`,
- repair Codex, Claude, Antigravity, Qoderwork, and Hermes links for these skills only.
- skip a client when the corresponding application or known config marker is not detected.

For private repositories, make sure the local GitHub credentials used by npm/git
can access `guuguo/guugo-skills`.

Useful install options:

```bash
# Install into a custom source location
GUUGO_SKILLS_SOURCE_DIR=/path/to/guuguo-skills npx --yes github:guuguo/guugo-skills

# Use a custom canonical skills directory
GUUGO_SKILLS_CANONICAL_DIR=/path/to/skills npx --yes github:guuguo/guugo-skills

# Repair only selected clients
GUUGO_SKILLS_TARGETS=codex,claude,hermes npx --yes github:guuguo/guugo-skills

# Skip client repair and only create canonical links
GUUGO_SKILLS_SKIP_CLIENTS=1 npx --yes github:guuguo/guugo-skills
```

### Manual Fallback

If `npx` is unavailable, clone the repository and run the installer directly:

```bash
mkdir -p ~/.agents/sources/skills
git clone https://github.com/guuguo/guugo-skills.git ~/.agents/sources/skills/guuguo-skills
node ~/.agents/sources/skills/guuguo-skills/scripts/install.js
```

## Custom Paths

The default profile assumes:

```text
canonical skills: ~/.agents/skills/
Codex skills:     ~/.codex/skills/
Claude skills:    ~/.claude/skills/
Antigravity:      ~/.gemini/antigravity/skills/
Qoderwork:        ~/.qoderworkcn/skills/
Hermes:           ~/.hermes/skills/
```

Hermes skills are category-based. By default this repository links
`gg-skills-governor` and `gg-ai-native-startup-playbook` under `devops`,
`gg-fact-driven-ai-methodology` and `gg-harness` under `software-development`,
`gg-child-psychology-for-content` under `creative`, and unmapped skills under
`imported`.

`skills_doctor.py` can run against other layouts:

```bash
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py \
  --source /path/to/canonical/skills \
  --target codex \
  --target-dir /path/to/codex/skills
```

Environment overrides are also supported:

```bash
SKILLS_GOVERNOR_SOURCE=/path/to/canonical/skills \
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target codex
```

You can also inspect or repair a specific skill:

```bash
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py \
  --target codex \
  --skill gg-fact-driven-ai-methodology \
  --fix
```

## Validation

Validate the skill folders:

```bash
for skill in skills/*; do
  python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py "$skill"
done
```

Check consumer links:

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

A healthy setup should report no problems for these 16 managed skills.

## Design Rules

- Keep each skill self-contained: `SKILL.md`, optional `agents/openai.yaml`, and only necessary bundled resources.
- Keep detailed references under `references/` so agents load them only when needed.
- Keep deterministic maintenance scripts under `scripts/`.
- Do not flatten-copy bundle skills into `~/.agents/skills/`; expose them with symlinks.
- Treat local paths in `gg-skills-governor` as defaults, not universal constants.

## Current Status

This repository currently focuses on personal-to-general reusable workflows:

- governing multi-agent skill installs,
- applying an AI-native startup operating playbook,
- rebuilding AI workflow methodologies from confirmed facts,
- maintaining lightweight Harness project maps, requirement facts, and acceptance standards,
- diagnosing macOS disk, cache, swap, and cleanup hotspots with local computer impressions,
- generating bitmap design images and runtime assets with Codex-backed image generation.

It is intentionally small. New skills should be added only when they have a
clear trigger, repeatable workflow, and enough reusable material to justify a
dedicated skill folder.

## Unified AI video skill maintenance

These four skills are maintained together under this repository’s `skills/` directory:

- [gg-douyin-ai-video](skills/gg-douyin-ai-video/SKILL.md)
- [ai-drama-review](skills/ai-drama-review/SKILL.md)
- [ai-video-director-prompt](skills/ai-video-director-prompt/SKILL.md)
- [gg-character-card](skills/gg-character-card/SKILL.md)

Canonical and client symlinks consume these same files. Former source paths are compatibility links; pre-migration originals, including the director skill Git history, are retained in `.migration-backup/`. The installer includes all four skills.

## Drama reference and video evidence skills

- [gg-drama-library](skills/gg-drama-library/SKILL.md): evidence-backed story beats, episode tracks, series arcs, and character-aware reference retrieval. Local storage is configured by `library_root` in `~/.config/gg-drama-library/config.json`.
- [gg-video-analysis](skills/gg-video-analysis/SKILL.md): timestamped frames, paginated contact sheets, local ASR, and audiovisual evidence. Runtime configuration lives in `~/.config/gg-video-analysis/config.json`. Reuses the installed video-subtitle-workflow resource preflight; missing dependencies are reported explicitly.
- [gg-bilibili-publish](skills/gg-bilibili-publish/SKILL.md): Bilibili video/column publishing and the publish ledger. Runtime configuration lives in `~/.config/gg-bilibili-publish/config.json`. Ledgers and media stay in the project.

These skills are maintained here and distributed by the installer. Media, publish records, and machine-specific configuration stay outside the repository.
