# Mole Execution Layer

Use Mole (`mo`) as the default scanner, previewer, executor, and audit source. Keep the skill's explicit-ID confirmation protocol as the authority for scope.

## Preflight

Run read-only:

```bash
command -v mo
mo --version
```

If Mole is unavailable or broken, continue read-only diagnosis with native commands. Offer installation separately; do not silently install or repair Mole.

## Capability Matrix

| Intent | Preview / evidence | Execution after confirmation | Verification |
| --- | --- | --- | --- |
| System health | `mo status --json` | None | Repeat `mo status --json` |
| Disk analysis | `mo analyze --json <path>` | `mo analyze <path>` for user-controlled Trash selection | Rescan the path and check Trash/free space |
| Cache/log cleanup | `mo clean --dry-run` | `mo clean` with only confirmed selections | `mo history --json`, `df`, scoped `du` |
| App uninstall | `mo uninstall --list`; `mo uninstall --dry-run <app>` | `mo uninstall <app>` only when app and residue selections match separately confirmed IDs | `mo history --json`; verify bundle and residues |
| Project artifacts | `mo purge --dry-run` | `mo purge` with only confirmed projects/categories | `mo history --json`; rescan targets |
| Installer files | `mo installer --dry-run` | `mo installer` with only confirmed files | `mo history --json`; verify paths/free space |
| Maintenance | `mo optimize --dry-run` | `mo optimize` after separate confirmation | `mo history --json`; repeat relevant status checks |

`mo status --json`, `mo analyze --json`, and `mo history --json` are machine-readable. Other workflows may be interactive and must not be treated as precisely targetable unless the visible selection can be mapped to confirmed candidate IDs.

## Scope Gate

Choose exactly one route per candidate:

1. **Exact Mole command**: Use when Mole accepts an exact app name or explicit path and dry-run matches the candidate.
2. **Interactive Mole selection**: Use when every selected row/category is visible and maps one-to-one to confirmed IDs. Deselect everything else.
3. **App-internal action**: Use for WeChat, WeCom, Lark, and other app-managed stores.
4. **Narrow fallback**: Use only when Mole cannot preserve the confirmed scope. State why Mole is unsuitable, show the exact native/tool command or path action, and retain the same confirmation requirement.

Abort if the mapping becomes ambiguous, the target changes materially after confirmation, or an app/process starts using the target.

## Execution Rules

- Run the matching `--dry-run` before every destructive Mole workflow.
- Restate the exact Mole command and selected rows/categories before execution.
- Preserve Mole's recoverable defaults. For uninstall, use Trash behavior; do not add `--permanent` by default.
- Mole can include app leftovers in uninstall. If those leftovers cannot be deselected, a main-uninstall confirmation alone is insufficient; abort or use a narrow fallback for the app bundle, then handle residue as a second stage.
- Treat `mo optimize` as state-changing maintenance, not harmless cleanup. Confirm its proposed changes separately.
- Do not pass sudo merely to broaden a scan or cleanup. Explain why elevated system scope is needed and obtain explicit confirmation first.
- Do not execute a broad `mo clean` for a small path-level confirmation. Use a narrow fallback instead.

## Slow or Partial Scans

Mole dry-runs may traverse thousands of files. During a read-only scan:

- Report progress if it exceeds a normal quick scan.
- Interrupt safely after sufficient evidence when the remaining traversal is low value.
- Label the result partial; do not present Mole's interim total as a complete candidate list.
- Prefer scoped `mo analyze --json <path>` over repeating a slow whole-user scan.

## Verification

After execution:

```bash
mo history --json --limit 20
df -h /System/Volumes/Data
du -sh <confirmed-target> 2>/dev/null
```

Use history to establish what Mole attempted. Use filesystem evidence to establish what changed. Report measured reclaim from before/after evidence, account for Trash and APFS purgeable-space behavior, and never infer success from an exit code alone.

## Fallback Reporting

When a fallback is necessary, record:

- Mole limitation encountered.
- Exact fallback action and target.
- Whether the action is recoverable.
- Before/after size and free-space evidence.
- That confirmation scope was unchanged.
