<h1 align="center">guugo-skills</h1>

<p align="center">
  A compact source repository for reusable AI agent skills, designed around
  governed local installs, symlink-based distribution, and fact-first workflows.
</p>

<p align="center">
  <a href="./README.zh-CN.md">中文版 README</a>
</p>

<p align="center">
  <a href="#skills"><img alt="skills" src="https://img.shields.io/badge/skills-3-2F6F5E"></a>
  <a href="#repository-model"><img alt="layout" src="https://img.shields.io/badge/layout-source%20repo%20%2B%20symlinks-3B82F6"></a>
  <a href="#validation"><img alt="validation" src="https://img.shields.io/badge/validation-quick_validate%20%2B%20doctor-64748B"></a>
</p>

## Why This Exists

`guugo-skills` keeps a small set of high-leverage AI agent skills in one
versioned source repository. The repository is meant to be cloned under a local
skill source directory, then exposed to agent clients through a stable canonical
skill layer.

The key idea is:

```text
source repository -> canonical skill links -> agent-specific skill directories
```

This keeps updates centralized while letting Codex, Claude, Antigravity, and
Qoderwork consume the same skill definitions.

## Skills

| Skill | Purpose | Notable resources |
| --- | --- | --- |
| `skills-governor` | Inspect, sync, repair, and govern skills across agent-specific directories. | `scripts/skills_doctor.py` |
| `ai-native-startup-playbook` | Diagnose startup stage and produce practical AI-native startup artifacts. | `references/stage-cards.md`, `references/artifact-templates.md` |
| `fact-driven-ai-methodology` | Rebuild AI workflow methodologies from confirmed facts and evidence instead of drift-prone self-optimization. | bilingual UI metadata |
| `child-psychology-for-content` | Guide AI animation / short video / picture-book content creation with Piaget, Vygotsky, Erikson, Bowlby, and Montessori. | Chinese, child-development reference |

## Repository Model

Use this repository as a bundle source:

```text
~/.agents/sources/skills/guugo-skills/
  skills/
    skills-governor/
    ai-native-startup-playbook/
    fact-driven-ai-methodology/
```

Expose individual skills through `~/.agents/skills/`:

```text
~/.agents/skills/skills-governor
  -> ../sources/skills/guugo-skills/skills/skills-governor
~/.agents/skills/ai-native-startup-playbook
  -> ../sources/skills/guugo-skills/skills/ai-native-startup-playbook
~/.agents/skills/fact-driven-ai-methodology
  -> ../sources/skills/guugo-skills/skills/fact-driven-ai-methodology
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

- sync this bundle into `~/.agents/sources/skills/guugo-skills`,
- expose each skill through `~/.agents/skills/<skill-name>`,
- repair Codex, Claude, Antigravity, and Qoderwork links for these skills only.

For private repositories, make sure the local GitHub credentials used by npm/git
can access `guuguo/guugo-skills`.

Useful install options:

```bash
# Install into a custom source location
GUUGO_SKILLS_SOURCE_DIR=/path/to/guugo-skills npx --yes github:guuguo/guugo-skills

# Use a custom canonical skills directory
GUUGO_SKILLS_CANONICAL_DIR=/path/to/skills npx --yes github:guuguo/guugo-skills

# Repair only selected clients
GUUGO_SKILLS_TARGETS=codex,claude npx --yes github:guuguo/guugo-skills

# Skip client repair and only create canonical links
GUUGO_SKILLS_SKIP_CLIENTS=1 npx --yes github:guuguo/guugo-skills
```

### Manual Fallback

If `npx` is unavailable, clone the repository and run the installer directly:

```bash
mkdir -p ~/.agents/sources/skills
git clone https://github.com/guuguo/guugo-skills.git ~/.agents/sources/skills/guugo-skills
node ~/.agents/sources/skills/guugo-skills/scripts/install.js
```

## Custom Paths

The default profile assumes:

```text
canonical skills: ~/.agents/skills/
Codex skills:     ~/.codex/skills/
Claude skills:    ~/.claude/skills/
Antigravity:      ~/.gemini/antigravity/skills/
Qoderwork:        ~/.qoderworkcn/skills/
```

`skills_doctor.py` can run against other layouts:

```bash
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py \
  --source /path/to/canonical/skills \
  --target codex \
  --target-dir /path/to/codex/skills
```

Environment overrides are also supported:

```bash
SKILLS_GOVERNOR_SOURCE=/path/to/canonical/skills \
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target codex
```

You can also inspect or repair a specific skill:

```bash
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py \
  --target codex \
  --skill fact-driven-ai-methodology \
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
for target in codex claude antigravity qoderwork; do
  python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py \
    --target "$target" \
    --skill skills-governor \
    --skill ai-native-startup-playbook \
    --skill fact-driven-ai-methodology \
    --only-problems
done
```

A healthy setup should report no problems for these three managed skills.

## Design Rules

- Keep each skill self-contained: `SKILL.md`, optional `agents/openai.yaml`, and only necessary bundled resources.
- Keep detailed references under `references/` so agents load them only when needed.
- Keep deterministic maintenance scripts under `scripts/`.
- Do not flatten-copy bundle skills into `~/.agents/skills/`; expose them with symlinks.
- Treat local paths in `skills-governor` as defaults, not universal constants.

## Current Status

This repository currently focuses on personal-to-general reusable workflows:

- governing multi-agent skill installs,
- applying an AI-native startup operating playbook,
- rebuilding AI workflow methodologies from confirmed facts.

It is intentionally small. New skills should be added only when they have a
clear trigger, repeatable workflow, and enough reusable material to justify a
dedicated skill folder.
