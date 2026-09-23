---
name: gg-harness
description: "Use when maintaining a lightweight Harness Engineering layer: slimming AGENTS.md into a project map, grilling requirements, creating plan.md/grill.md/acceptance.md, maintaining stable specs, reference-implementation parity, root DESIGN.md, execution evidence, docs/harness/version.md, and migration from by-harness. 中文触发：gg-harness、轻量 harness、项目地图、AGENTS.md 瘦身、需求拷问、验收标准、执行证据契约、功能复刻、对等验收、视觉规范、DESIGN.md、harness 版本升级、迁移 by-harness。"
---

# gg-harness

## Core Model

Use `gg-harness` as a lightweight Harness Engineering front layer:

```text
thin AGENTS.md map
  -> docs/harness/version.md local harness version
  -> grilled and confirmed requirement facts
  -> invariants + confirmed failure evidence
  -> conditional reference implementation + capability inheritance contract
  -> minimal closed loop + complexity budget
  -> 做 / 不做 in plan.md
  -> plan.md + acceptance.md + grill.md
  -> 验证 in acceptance.md
  -> optional _stable/ and rare sub-*.md
  -> user-chosen execution layer
  -> final evidence written back to acceptance.md or result.md
```

Do not turn this skill into an executor. It does not implement features, split runtime tasks, manage sessions, keep `.harness/runs`, or bind to any specific execution plugin. The requirement directory itself is the handoff material and the final acceptance record.

## Required Behavior

Write user-facing responses in Chinese by default.

Before changing project facts, separate:

- confirmed facts
- recommended assumptions
- unresolved questions

Default to the smallest evidence-backed change. Preserve confirmed business semantics, transaction boundaries, scheduling, data ownership, and core data structures unless changing one is itself required by the user or proven necessary. Put plausible but unproven risks and optional optimizations under later observation; do not silently promote them into first-release scope.

For important project-map or requirement changes, give the user a recommendation and wait for confirmation before applying durable edits.

## Workflow

### 1. Resolve the Project and Existing Materials

Work inside a concrete project repository. Inspect existing `AGENTS.md`, `docs/`, prior plans, specs, rules, and any user-provided PRD or discussion.

Do not index or rewrite broad multi-project roots. If the current directory is not the target project, ask for or infer the specific project path first.

### 2. Check or Initialize Harness Version

Read `references/harness-version.md` to know the current `gg-harness` version and migration notes.

Project-local version file:

```text
docs/harness/version.md
```

If the file is missing, recommend creating it from `references/project-version-template.md`. Treat the project as `unknown` or pre-versioned, audit existing harness files, then propose a migration plan before durable edits.

When the user asks to initialize, upgrade, update, or sync harness:

- compare project-local version with the current skill version
- list only migrations newer than the project-local version and up to the target version
- inspect whether each migration already appears to be applied
- show a short migration plan and ask for confirmation before editing project files
- after applying confirmed migrations, update `docs/harness/version.md` with the new version, date, summary, and migration notes

Migration notes must stay short: one or two sentences per version. Do not invent automated scripts unless a future migration explicitly requires deterministic tooling.

### 3. Maintain Thin `AGENTS.md`

Use `AGENTS.md` only as a project map:

- one-sentence project goal
- key directories
- work entrypoints
- hard boundaries
- rule/spec indexes

`AGENTS.md` must include or index the execution evidence contract: when an agent executes a confirmed requirement plan, it must verify against `acceptance.md` and write final evidence back to the requirement directory before claiming completion. Keep this rule short in `AGENTS.md`; put long details in the requirement `acceptance.md` or an indexed rule file.

When auditing an existing messy `AGENTS.md`, read `references/agents-md-audit.md`.

Important: audit and recommend automatically, but do not overwrite key `AGENTS.md` content before user confirmation. A candidate patch or candidate replacement is allowed; silent replacement is not.

For a clean target shape, use `references/agents-template.md`.

### 4. Grill Requirements Before Writing Durable Specs

Before creating or finalizing `plan.md`, perform bounded `grill-me` style calibration:

- AGENTS initialization/upgrade: at most 8 user questions.
- Requirement `plan.md`: at most 12 user questions.
- Acceptance standards: at most 6 user questions.

Ask P0 blockers one at a time. Batch P1 questions when useful. Do not ask P2 questions; record recommended assumptions.

If a P0 remains unresolved after the budget, mark the document `blocked/draft` instead of inventing certainty.

Use `references/grill-template.md` for `grill.md`.

Before solution expansion, complete the minimum-change calibration:

1. Write the invariants first: what business behavior, transaction boundary, scheduling mode, source of truth, and data structure must remain unchanged.
2. Map every first-release problem to direct evidence: user fact, log, heap/profile, code path, test, benchmark, or mandatory stable constraint.
3. Prefer wrapping the failing boundary over rewriting its internals. Reuse current business logic and add the smallest guard, bound, checkpoint, timeout, or adapter that closes the proven failure.
4. Separate **must fix** from **could optimize**. An improvement that may be useful is not first-release scope unless the minimum loop cannot pass acceptance without it.
5. Apply a complexity budget. By default, do not add a business table, second source of truth, new concurrency dimension, larger thread/connection pool, core business rewrite, or extra states. Every exception must name the confirmed failure it solves and why a lower-complexity alternative is insufficient.
6. Make the first draft a minimal closed loop. Reviews should mainly find missing evidence or correctness gaps. If later reviews mostly delete mechanisms, stop patching the oversized design and rewrite its scope from the invariants and failure evidence.

When a requirement explicitly replicates, migrates, replaces, aligns with, or references a mature implementation, also complete a conditional capability-inheritance calibration:

1. Pin the reference implementation to repository plus immutable commit/tag and relevant paths. A mutable branch name alone is insufficient.
2. Classify referenced behavior as **business invariant**, **evidence-backed mature advantage**, **ordinary implementation choice**, or **legacy/platform-specific baggage**. Do not inherit all source code indiscriminately.
3. Preserve business invariants and mature advantages, either by direct reuse, a thin adapter, or an equivalent mechanism. A P0 deviation requires direct evidence, an explicit replacement, and user confirmation.
4. Prefer, in order: direct reuse, adapter reuse, equivalent reuse of the proven mechanism, then evidence-backed redesign. Code structure may differ; confirmed capability may not silently regress.
5. Mark unknown source baselines as `unknown`. Measure them before inventing quantitative parity targets.
6. Define parity acceptance with the same fixture and comparable conditions across business output, state/cursor semantics, failure recovery, latency, database/network work, and peak resources, selecting only dimensions relevant to the inherited capability.

Ask only P0 inheritance questions: the pinned source, must-preserve capabilities, and material allowed deviations. Batch P1 details and record P2 assumptions. Do not apply this calibration to unrelated greenfield features or routine fixes.

This discipline does not prohibit preventive work required by an explicit user constraint, security/compliance rule, or stable project standard; record that mandate as evidence. Do not use speculative completeness as evidence.

For a user-facing feature, product-behavior change, roadmap/investment decision, staged launch, or post-launch outcome claim, also read `references/product-decision-template.md` before finalizing `plan.md` and `acceptance.md`. Apply only its relevant sections:

- state the user problem and evidence before describing the solution
- write a short user-value release narrative before solution detail
- record baseline, target, observation window, data source, and confidence without inventing missing values
- make material options, trade-offs, confidence, and revisit conditions explicit
- define rollout gates and rollback conditions when production, data, permissions, or user behavior creates rollout risk
- separate delivery acceptance from 30/60/90-day or domain-appropriate outcome observation

Do not treat `grill-me` as a substitute for external product evidence. Interviews, behavior data, support signals, revenue/retention, experiments, and usability observations validate reality; self-questioning only tests the coherence of current assumptions.

### 5. Create Requirement Directory

Default location:

```text
docs/harness/specs/YYYYMMDD-中文短名/
  plan.md
  grill.md
  acceptance.md
```

If the requirement belongs to an explicit version:

```text
docs/harness/specs/YYYYMMDD-版本-中文短名/
```

Use Chinese short names by default. Do not invent a version segment.

Use:

- `references/plan-template.md` for requirement facts.
- `references/acceptance-template.md` for acceptance standards.
- `references/stable-spec-template.md` for cross-cycle facts under `docs/harness/specs/_stable/`.

For every active requirement `plan.md`, write these sections before implementation detail:

- `不变项`
- `证据与故障映射`
- `范围`, separating `必须修复`, `本期最小闭环`, `后续观察/可选优化`, and `不做`
- `复杂度预算`, including an explicit justification for every exceeded default

For a reference-implementation requirement, also write the conditional `参考实现与能力继承` section from `references/plan-template.md`, and add the matching parity table from `references/acceptance-template.md`. Omit both sections when no mature implementation is being referenced.

For product-decision requirements, add only the applicable sections from `references/product-decision-template.md`. Omit the addendum for small bug fixes, internal refactors, documentation, and routine configuration unless they change user outcomes or require a controlled rollout.

Keep `做 / 不做 / 验证` split across files:

- `plan.md`: what to do and what not to do.
- `acceptance.md`: how to verify completion.
- `AGENTS.md`: only says execution must read `plan.md` and `acceptance.md`; do not duplicate requirement details there.

### 6. Avoid Persistent Sub-Specs by Default

Do not create `sub-*.md` for execution steps, frontend/backend splits, testing chunks, or token-control decomposition.

Create `sub-<中文短名>.md` only when the sub-block has long-term fact value, such as independent version, independent acceptance, independent owner, independent user path, external contract, risk decision, or future reuse across requirements.

Before creating `sub-*.md`, explain why runtime decomposition is insufficient and get user confirmation or record the assumption. Use `references/sub-spec-template.md`.

### 7. Maintain Visual Design Files Separately

Treat the project's visual identity as a cross-cycle stable fact, not a per-requirement output. Use the [DESIGN.md open format](https://github.com/google-labs-code/design.md) (Apache-2.0): a self-contained spec that keeps the same look-and-feel consistent across sessions, tools, and agents.

Visual design files do **not** go through the requirement cycle. Do not write `plan.md` / `grill.md` / `acceptance.md` for them. They are maintained on their own visual-change cadence and referenced by UI-touching requirements.

- Canonical source is project-root `DESIGN.md`, so external tooling, linters, and other agents discover it by convention.
- `docs/harness/specs/_stable/design-guidelines.md` becomes a one-line pointer to root `DESIGN.md`; do not duplicate its content.
- Register one index line in `_stable/index.md` and one in `AGENTS.md` (key directories + rule index), stating "read when a requirement touches UI/visual/brand".
- A UI-touching requirement must link root `DESIGN.md` in `plan.md` 做 and list "conforms to DESIGN.md" in `acceptance.md`. Requirements may not rewrite `DESIGN.md`; a visual-source change is a separate, user-confirmed edit.
- Prose is primary: a specific reference ("a 1970s university lecture handout") carries more than a list of adjectives. Tokens are context, not rendering instructions.

Use `references/design-md-maintenance.md` for the full scheme, format digest, and authoring philosophy.

### 8. Keep Execution Layer Separate

After `plan.md` and P0 acceptance are confirmed, provide handoff by listing:

- requirement directory path
- read order: `plan.md`, `acceptance.md`, then `grill.md` and rare `sub-*.md`
- unresolved P0/P1/P2 items
- referenced `_stable/` files
- hard boundaries
- rule that execution layers may not rewrite requirement facts without user confirmation
- rule that execution completion claims require a final evidence record in `acceptance.md` or `result.md`

Do not create a separate handoff template file. The requirement directory is the handoff source.

### 9. Require Final Execution Evidence

`gg-harness` does not maintain runtime progress files, but every execution layer must leave final, reviewable evidence.

For small work, update the bottom of `acceptance.md`. For medium/high-risk work or noisy evidence, create `result.md` in the same requirement directory and link it from `acceptance.md`.

The final evidence record must include:

- execution method, such as normal agent, Superpowers, or another user-chosen skill
- execution time and actor/session if known
- related commits, PRs, or changed-file summary
- test commands, manual checks, screenshots, logs, or review outputs actually used
- per-acceptance status: passed / failed / not verified / not applicable
- unresolved gaps, risks, and follow-up items
- whether independent review happened, such as spec review, code review, or human review
- for reference-implementation requirements, the pinned source version and actual parity/deviation evidence

An agent must not claim the requirement is complete if any P0 acceptance item is failed or not verified, unless the user explicitly accepts that exception. Do not let execution reports redefine acceptance conditions.

Delivery completion and product-outcome confirmation are separate states. A requirement may pass delivery acceptance while later outcome observations remain pending. Do not claim that a product outcome was achieved before its observation window closes; do not make a future observation block delivery completion unless the user explicitly defines it as a rollout gate.

### 10. Migrate Old `by-harness` Only on Request

If the user explicitly wants to migrate an old `by-harness` project, read `references/legacy-by-harness-migration.md`.

Migration is manual and confirmation-driven:

- do not run old `by-harness` upgrade/scaffold scripts
- do not migrate `.harness/task-harness/runs` or progress as specs
- do not convert all old task JSON files into `sub-*.md`
- do not overwrite `AGENTS.md` without confirmation

## Reference Routing

- `references/harness-version.md`: use for current skill version and migration notes.
- `references/project-version-template.md`: use when creating or updating `docs/harness/version.md`.
- `references/agents-md-audit.md`: use for messy `AGENTS.md` audit and confirmation workflow.
- `references/agents-template.md`: use when drafting thin `AGENTS.md`.
- `references/plan-template.md`: use when creating requirement facts.
- `references/grill-template.md`: use when recording requirement calibration.
- `references/acceptance-template.md`: use when creating acceptance standards and final execution evidence records.
- `references/product-decision-template.md`: use only for user-facing/product decisions that need problem evidence, a value narrative, measurable outcomes, explicit trade-offs, controlled rollout, or post-launch observation.
- `references/sub-spec-template.md`: use only for rare persistent sub-specs.
- `references/stable-spec-template.md`: use for `_stable/` goals, design guidelines, baselines, terms.
- `references/design-md-maintenance.md`: use when creating or maintaining the project visual identity (root `DESIGN.md`), separate from the requirement cycle.
- `references/legacy-by-harness-migration.md`: use only for explicit old `by-harness` migration.

## Guardrails

- Do not preserve heavy `by-harness` runtime behavior in `gg-harness`.
- Do not maintain `.harness/runs`, session ledgers, runtime manifests, task switches, route JSON, or live execution progress.
- Do require final execution evidence before completion claims; this is an acceptance record, not a runtime system.
- Do not put Java rule books, QA runner details, or long process docs into `AGENTS.md`.
- Do not run the visual identity (`DESIGN.md`) through the requirement cycle, and do not let a requirement rewrite it without a separate user-confirmed visual change.
- Do not let AI-only acceptance replace human confirmation for P0 outcomes.
- Do not treat execution plans as durable requirement facts.
- Do not force all historical requirement docs to match the latest templates; migrate active or project-wide rules first.
- Do not broaden first-release scope for architectural completeness, hypothetical scale, or an unproven future failure.
- Do not replace a working business core when a bounded wrapper can close the confirmed failure.
- Do not silently drop an evidence-backed capability when replicating or migrating a mature implementation. Preserve it or record the confirmed deviation and replacement evidence; do not copy legacy baggage merely for structural similarity.
- Do not treat added tables, states, queues, workers, concurrency, retries, or abstraction layers as free; charge each one to a confirmed requirement or failure.
- Do not force product-decision sections onto routine engineering work, fabricate baselines or targets, or use internal grilling as evidence that users have a problem.
