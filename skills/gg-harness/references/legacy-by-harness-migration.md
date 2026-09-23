# Old `by-harness` Migration

Read this only when the user explicitly wants to migrate an old `by-harness` project into `gg-harness`.

Migration is not script-driven. Do not run old `by-harness` `update_runtime.py`, `scaffold.py`, or automatic upgrade scripts. The agent performs audit, recommendation, user confirmation, and manual fact migration.

## Principles

- Do not delete old directories automatically.
- Do not overwrite `AGENTS.md` without confirmation.
- Migrate long-term facts, not execution state.
- Treat `.harness/task-harness/runs`, `progress`, `route`, and `evidence` as history, not new specs.
- Do not convert all old task JSON files into `sub-*.md`.
- Do not preserve the old execution state machine as `gg-harness`.

## Classify Old Artifacts

| Old artifact | Action | Target |
| --- | --- | --- |
| `AGENTS.md` / `CLAUDE.md` managed block | Extract map, boundaries, indexes; propose thin map | `AGENTS.md` |
| `docs/agent-context/agent-rules/` | Keep active long rules by index | `docs/harness/rules/` or `_stable/` |
| `.harness/docs/specs/` | Migrate only durable requirement facts | `docs/harness/specs/<需求>/plan.md` |
| `.harness/docs/contracts/` | Extract checkable acceptance | `docs/harness/specs/<需求>/acceptance.md` |
| `docs/agent-context/<需求>/` | Migrate if it is requirement/tech fact | `docs/harness/specs/<需求>/` or `_stable/` |
| `.harness/task-harness/tasks/` | Use as historical reference only | migration report |
| `.harness/task-harness/runs/` | Runtime history | keep or archive |
| `.harness/task-harness/progress/` | Runtime history | keep or archive |
| `.harness/docs/qa/` | Extract only durable acceptance evidence if useful | `acceptance.md` or report |
| `.harness/config/`, `.harness/scripts/` | Runtime | do not migrate |

## Migration Steps

1. Audit without editing:
   - locate `AGENTS.md`, `BY-HARNESS MANAGED BLOCK`, `.harness/`, old specs/contracts/rules, `docs/agent-context/`, `docs/tech-plan/`
   - list what should be kept, migrated, archived, or confirmed

2. Recommend a migration plan:
   - candidate thin `AGENTS.md`
   - new requirement directory list
   - source files for each new `plan.md` and `acceptance.md`
   - `_stable/` and `docs/harness/rules/` updates
   - old runtime directories to preserve
   - P0 questions for the user

3. Wait for user confirmation:
   - whether to rewrite `AGENTS.md`
   - which old requirements become durable `plan.md`
   - which old contracts/QA become `acceptance.md`
   - which old rules are still hard boundaries
   - whether to keep `.harness/` in place

4. Rewrite thin `AGENTS.md` after confirmation:
   - keep goal, directories, entrypoints, hard boundaries, indexes
   - remove or index runtime upgrade, auto route, session close, task switch, feature list, QA runner, long Java rules

5. Migrate confirmed requirements:
   - create `docs/harness/specs/YYYYMMDD[-版本]-中文短名/`
   - write `plan.md` from durable facts
   - write `acceptance.md` from checkable conditions
   - write `grill.md` or migration notes with confirmed facts and assumptions
   - create `sub-*.md` only for independent long-term fact value

6. Preserve runtime history:
   - keep `runs`, `progress`, `evidence`, config, scripts unless the user explicitly asks to clean them
   - if cleanup is requested, recommend backup first and ask for explicit confirmation

7. Generate migration report:

```text
docs/harness/rules/legacy-by-harness-migration-report.md
```

Report:

- migration date
- migrated files
- skipped files and reasons
- `AGENTS.md` changes
- new requirement directories
- assumptions and open questions
- old `.harness/` preservation policy

## Completion Criteria

- `AGENTS.md` is a confirmed thin map.
- Durable requirements are in `plan.md`.
- Durable acceptance is in `acceptance.md`.
- Stable rules/specs are indexed, not pasted into `AGENTS.md`.
- Runtime history was not mistaken for requirement fact.
- Migration report exists.
