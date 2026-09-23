# Cleanup Interaction Protocol

## Contents

- [Principle](#principle)
- [Conversation Board](#conversation-board)
- [Candidate IDs](#candidate-ids)
- [Confirmation Grammar](#confirmation-grammar)
- [Pre-Execution Restatement](#pre-execution-restatement)
- [Mole Scope Gate](#mole-scope-gate)
- [App-Internal Cleanup Items](#app-internal-cleanup-items)
- [Uninstall Mode Confirmation](#uninstall-mode-confirmation)
- [Execution Evidence](#execution-evidence)
- [End-of-Session Summary](#end-of-session-summary)

## Principle

The skill may speed up scanning and explanation, but never speeds past user confirmation. Every destructive or state-changing action needs a concrete confirmation that names a candidate ID or path.

## Conversation Board

Maintain this board in the conversation, not in the computer-impression JSON:

```text
本轮目标:
候选项:
已确认:
已执行:
已跳过:
暂缓:
执行层:
下一步:
```

Refresh the board after each scan, confirmation, cleanup, skip, or deferral.

## Candidate IDs

- Assign stable numeric IDs per board: `1`, `2`, `3`.
- Do not reuse an ID for a different path in the same board.
- If a path is rescanned and size changes, keep the same ID and update size.
- If the board is reset, say so explicitly.

## Confirmation Grammar

Accepted action confirmations:

- `清理 1`
- `清理 1 3`
- `卸载 1`
- `清理残留 2 3`
- `保留用户数据`
- `只删缓存`
- `清理 /Users/name/path`
- `跳过 2`
- `暂缓 4`
- `深扫 5`
- `只扫描`

Not accepted as cleanup authorization:

- `可以`
- `ok`
- `开始吧`
- `都清了`
- `帮我清理`
- `清理一下`
- `按你说的来`
- `卸载干净`

For generic replies, ask the user to choose specific IDs. Keep the question short and include the safest recommended IDs if there are any.

## Pre-Execution Restatement

Before any cleanup command, restate:

- Candidate ID and path.
- Exact Mole command and interactive selection, or App-internal/narrow fallback action with the reason Mole cannot preserve scope.
- Estimated reclaim.
- Risk and data impact.
- Rebuild path.
- Whether rebuild needs network, external network, or VPN traffic.

If the user confirmed multiple IDs, execute one risk group at a time. Start with lower-risk cache commands.

## Mole Scope Gate

- Chat confirmation is the authority; Mole's own prompt is only an execution safeguard.
- Run the matching Mole `--dry-run` before proposing or executing a destructive workflow.
- Map every Mole row/category selected during execution to a confirmed candidate ID. Deselect unconfirmed items.
- Abort when Mole exposes only a broader category than the confirmed target. Offer a narrow fallback instead of expanding scope.
- Keep uninstall recoverable. Do not add `mo uninstall --permanent` unless the user explicitly confirms permanent deletion.
- Treat `mo optimize` as a separate state-changing action even when it appears next to cleanup commands.

## App-Internal Cleanup Items

For WeCom, WeChat, Lark, and similar app-owned data:

- Explain where the data lives and why it is large.
- Tell the user to clean inside the app where possible.
- Do not convert App-internal cleanup into `rm -rf`.
- If the user insists on command-line deletion, warn that it may destroy chat files, indexes, account state, or local work state; ask for explicit path-level confirmation and prefer not to proceed.

## Uninstall Mode Confirmation

Split uninstall into two separate confirmation stages:

1. Main uninstall: remove the app through the safest identified path, such as a scope-safe Mole selection, official uninstaller, Homebrew Cask, App Store guidance, package receipt plan, or moving the app bundle to Trash.
2. Residue cleanup: remove selected leftover files only after the main uninstall is complete or intentionally skipped.

Do not accept `卸载干净`, `都删了`, or `按你说的来` as permission for both stages. Ask for exact actions:

- `卸载 1`
- `清理残留 2 3`
- `只删缓存`
- `保留用户数据`

If `mo uninstall` bundles the app and leftovers and does not allow deselecting unconfirmed residue, do not execute it after a main-uninstall-only confirmation. Use a narrow main-uninstall fallback, then rescan residue.

Residue candidates must explain possible data types before confirmation. If possible data includes user data, account state, Keychain/license, container data, group container data, or privileged helper tools, default to `暂缓` unless the user explicitly asks for a clean uninstall and confirms the path.

## Execution Evidence

After each confirmed action:

1. Read `mo history --json` when Mole performed the action.
2. Recheck target size and disk free space independently.
3. Report reclaimed space as measured, not only estimated.
4. State whether Mole or a documented fallback performed the action.
5. Update board status.
6. Record durable conclusions for the final computer-impression update.

## End-of-Session Summary

At the end, summarize:

- Initial free space and swap.
- Actions executed.
- Execution layer used and any fallback reason.
- Measured reclaim.
- Deferred or skipped candidates.
- New hotspots or preferences to write to computer impression.

Do not persist the board itself.
