# gg-harness Version

Use this file as the skill-side source of truth for project harness upgrades.

## Current Version

- Current version: `0.7.0`
- Release date: `2026-08-06`

## Version History

| Version | Date | Change | Project migration |
| --- | --- | --- | --- |
| `0.7.0` | `2026-08-06` | Adds conditional reference-implementation inheritance: pin immutable sources, classify business invariants and proven advantages separately from ordinary choices and legacy baggage, require evidence for P0 deviations, and define parity acceptance without forcing structural copying. | Add one project-map trigger when the project repeatedly replicates mature capabilities. Apply the inheritance and parity sections only to new, reopened, or currently active reference-implementation requirements; do not bulk-rewrite unrelated or historical specs. |
| `0.1.0` | `2026-06-19` | Initial lightweight harness shape: thin `AGENTS.md`, confirmed `plan.md`, `grill.md`, `acceptance.md`, optional `_stable/`, rare persistent `sub-*.md`, no execution layer ownership. | Create `docs/harness/specs/`, slim or index `AGENTS.md`, and migrate only long-term facts from old harness materials after user confirmation. |
| `0.2.0` | `2026-06-20` | Adds the execution evidence contract and project harness version tracking. Completion claims now require final evidence in `acceptance.md` or same-directory `result.md`. | Add or update `docs/harness/version.md`; add a short execution evidence contract to `AGENTS.md`; add execution handoff/acceptance-record sections to new templates and update active requirement docs only when relevant. |
| `0.3.0` | `2026-06-20` | Absorbs the useful part of spec-driven development: `plan.md` states `做 / 不做`, while `acceptance.md` owns `验证`. | Update active requirement docs when touched; do not bulk rewrite historical specs. Remove `spec-driven-development` routing from agent environments if `gg-harness` is the project standard. |
| `0.4.0` | `2026-06-25` | Adds a separate visual-identity maintenance scheme: root `DESIGN.md` (DESIGN.md open format) as the authoritative source, maintained outside the requirement cycle and indexed in `AGENTS.md` + `_stable/`. | If the project has a visual identity, create/relocate root `DESIGN.md`, make `_stable/design-guidelines.md` a pointer, add one DESIGN.md line to `AGENTS.md` key-dirs + rule-index; require UI requirements to reference it. No-op for projects without a UI. |
| `0.5.0` | `2026-07-21` | Adds evidence-backed minimal-change planning: write invariants first, map first-release mechanisms to confirmed failures, prefer wrappers over rewrites, separate must-fix from could-optimize, and enforce a complexity budget. | Update active requirements when touched: add invariants, evidence mapping, a minimum closed loop, deferred observations, and complexity-budget exceptions. Do not bulk-rewrite historical specs. If an active draft mostly loses mechanisms during review, rewrite its scope from the minimum loop instead of preserving the oversized draft. |
| `0.6.0` | `2026-07-21` | Adds a conditional product-decision addendum: problem evidence before solution, a concise user-value release narrative, baseline/target/window, explicit options and confidence, controlled rollout/rollback, and separate post-launch outcome observation. | Apply only to new or reopened product/user-behavior requirements. Add the relevant product sections when touched; keep routine engineering work unchanged, do not bulk-rewrite historical specs, and do not let pending 30/60/90-day outcome observations block delivery completion unless they are explicit rollout gates. |

## Upgrade Rules

- Compare the project-local `docs/harness/version.md` version to `Current version`.
- Apply only migrations newer than the project-local version and up to the target version.
- If the project has no local version file, treat it as `unknown`; audit before migration.
- Do not assume every old project must receive every template change. Prefer active requirements and project-wide rules first.
- Always show the migration plan and wait for user confirmation before durable edits.
- After confirmed migration, update project-local `docs/harness/version.md` with version, date, summary, and migration notes.
