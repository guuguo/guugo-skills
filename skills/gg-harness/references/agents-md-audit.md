# AGENTS.md Audit Workflow

Use this when a project already has a messy, oversized, or old `AGENTS.md`.

## Audit Without Editing

First read the existing file and classify each section:

| Class | Meaning | Target |
| --- | --- | --- |
| Map | project goal, directories, entrypoints | keep in thin `AGENTS.md` |
| Hard boundary | user-change safety, validation rule, release boundary | keep or index |
| Long rule | Java rules, QA runner, style guide, role manuals | move/index under `docs/harness/rules/` |
| Requirement fact | feature goal, scope, non-goal, user path | move/index under `docs/harness/specs/<需求>/plan.md` |
| Stable fact | cross-cycle goal, design guideline, terminology | move/index under `docs/harness/specs/_stable/` |
| Runtime detail | task switch, session close, route JSON, `.harness/runs` | do not migrate into gg-harness |
| Unknown | unclear current value | ask or mark pending |

Also check whether `AGENTS.md` has a short execution evidence contract. If missing, recommend adding a concise rule: executing a confirmed requirement plan must verify against `acceptance.md` and write final evidence to `acceptance.md` or same-directory `result.md` before claiming completion.

Also check whether the project has `docs/harness/version.md`. If missing, recommend creating it from `references/project-version-template.md`; if present, use it to decide which `gg-harness` migrations still apply.

## Recommendation Before Patch

Before applying edits, show the user:

- candidate thin `AGENTS.md`
- whether to create or update `docs/harness/version.md`
- content to move into `docs/harness/rules/`
- content to move into `docs/harness/specs/` or `_stable/`
- content to leave untouched or archive
- content recommended for removal
- P0 questions that must be confirmed

Do not apply key changes until the user confirms. If the user says "按推荐继续", proceed and record which choices were recommended assumptions.

## Question Budget

Ask at most 8 user questions:

- P0: up to 3, one at a time.
- P1: up to 5, can be batched.
- P2: do not ask; record recommended assumptions.

If project goal, main directories, or hard boundaries remain unclear after P0 budget, stop and mark the audit blocked.

## Audit Report Shape

Write either `docs/harness/rules/agents-map-maintenance.md` or a section in the active `plan.md`:

```md
# AGENTS.md 整理记录

## 已确认

- {fact}

## 推荐假设

- {assumption}

## 迁移/索引

| 原位置 | 新位置 | 处理 | 理由 |
| --- | --- | --- | --- |

## 未决问题

| 问题 | 影响 | 推荐答案 | 状态 |
| --- | --- | --- | --- |
```
