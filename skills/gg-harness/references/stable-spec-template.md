# Stable Specs

Use `docs/harness/specs/_stable/` for cross-cycle facts that stay current across many requirements.

Recommended files:

```text
docs/harness/specs/_stable/
  index.md
  goals.md
  design-guidelines.md
  acceptance-baseline.md
  terms.md
```

## `index.md`

```md
# Stable Spec Index

| 文件 | 用途 | 何时读取 |
| --- | --- | --- |
| `goals.md` | 长期产品/项目目标 | 当需求影响长期方向时 |
| `design-guidelines.md` | 指向根 `DESIGN.md` 的视觉规范指针（不复制内容） | 当需求涉及 UI/UX/品牌时 |
| `acceptance-baseline.md` | 通用验收基线 | 当需求需要默认质量底线时 |
| `terms.md` | 术语表 | 当需求含领域词时 |
```

Rules:

- Put only long-lived facts here.
- Do not copy stable content into every `plan.md`; reference it.
- If a stable fact changes, update `_stable/` and note affected requirements.
- Keep requirement-specific tradeoffs inside that requirement directory.
- 视觉规范的权威源是项目根 `DESIGN.md`，按 `references/design-md-maintenance.md` 独立维护；`design-guidelines.md` 只做指针，不复制内容。
