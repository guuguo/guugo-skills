---
name: gg-clean-mac
description: "Diagnose and safely clean macOS with Mole as the default scan, preview, execution, and audit layer. Use for low disk space, high swap, memory pressure, bloated caches, giant folders, AI/dev tool storage, app uninstall residue, or requests such as 清理电脑、空间不够、swap 高、快速扫描、磁盘分析、缓存太多、卸载软件、企业微信/微信/飞书/Claude/Codex/Gemini/Espressif 占用。"
---

# gg-clean-mac

## Core Rule

Use this skill to quickly explain macOS disk and swap pressure, then help the user make safe cleanup decisions. Use Mole (`mo`) as the default execution layer whenever it can preserve the user's confirmed scope.

Default to read-only scanning. Never delete, truncate, purge, reset, or move files until the user confirms concrete numbered items or concrete paths. Faster mode means faster evidence and clearer choices, not weaker confirmation.

Conversation-level confirmation outranks Mole's prompts. A confirmation inside Mole never authorizes a broader category than the user confirmed in chat. If Mole cannot target the confirmed scope exactly, abort or use the documented narrow fallback after explaining why.

Reply in Chinese by default.

## Required References

Load only what the task needs:

- `references/interaction-protocol.md`: always read before offering cleanup actions or handling multi-turn cleanup.
- `references/mole-execution-layer.md`: always read before scanning, previewing, executing, or verifying with Mole.
- `references/commands.md`: read before running scan or cleanup commands.
- `references/computer-impression-schema.md`: read before reading or updating `~/.agents/state/gg-clean-mac/computer-impression.json`.
- `references/mac-cleaning-targets.md`: read when interpreting known large macOS paths, app data, caches, SDKs, VM images, or AI/dev tool folders.
- `references/uninstall-mode.md`: read when the user asks to uninstall software, remove an app cleanly, find leftovers, or clean app residue.

## Workflow

1. Check the execution layer:
   - Run `command -v mo` and `mo --version` read-only.
   - If Mole exists, use the Mole-first routing in `references/mole-execution-layer.md`.
   - If Mole is missing or broken, continue read-only diagnosis with native commands and offer installation; do not install it unless the user asked or confirms installation.
2. Determine intent:
   - Space diagnosis: disk free space, large folders, caches.
   - Swap diagnosis: `vm.swapusage`, memory pressure, largest resident/swapped processes.
   - Cleanup: candidate actions plus confirmation flow.
   - Uninstall mode: identify app source, choose safe uninstall path, then scan residue separately.
   - Quick mode: prioritize known hotspots and shallow scans.
   - Deep mode: broader but still read-only scans after telling the user it may take longer.
3. Load computer impression if present:
   - Path: `~/.agents/state/gg-clean-mac/computer-impression.json`.
   - Use it only to prioritize checks and recall known risks.
   - Do not treat stale impressions as current facts; rescan important paths.
4. Run Mole-first read-only scans:
   - Use `mo status --json` for the system headline.
   - Use scoped `mo analyze --json <path>` for disk evidence; prefer known hotspots before the whole home directory.
   - Use the relevant Mole `--dry-run` before proposing cleanup, uninstall, purge, installer removal, or optimization.
   - Supplement with native read-only commands only when Mole lacks the metric, times out, or cannot explain the pressure.
5. Explain each candidate before asking for action:
   - What it is.
   - Where it comes from.
   - What it is used for.
   - Delete impact.
   - Rebuild path.
   - Network, external network, or VPN traffic cost.
   - Recommended action and confirmation phrase.
   - For uninstall residue, possible data types inside the path.
   - Include the planned execution route: exact Mole command, interactive Mole selection, App-internal action, or narrow fallback with reason.
6. Maintain a conversation-local cleanup board:
   - Candidate IDs.
   - Confirmed actions.
   - Cleaned items.
   - Skipped or deferred items.
   - Remaining next step.
7. Execute only confirmed actions:
   - Accept confirmations like `清理 1`, `清理 1 3`, `卸载 1`, `清理残留 2 3`, `跳过 2`, `暂缓 4`, `深扫 5`.
   - Generic replies like `可以`, `都清了`, `帮我清理`, `ok`, or `开始吧` are not cleanup authorization.
   - Before executing, repeat the Mole command/action, exact selection or path, expected reclaim, risk, and rebuild cost.
   - Prefer Mole execution. Use a fallback only when Mole cannot preserve exact scope, and state that reason before execution.
   - After executing, inspect `mo history --json` when applicable, then independently recheck target size and free space.
8. End by updating the computer impression:
   - Save only durable summary facts, preferences, hotspots, recent scan summaries, and known incidents.
   - Do not persist the per-turn board, partial task ledger, or unfinished candidate list.

## Classification

Use four groups in user output:

- 可直接清理: build caches, package caches, download caches, temporary files, old backups, stale logs.
- 建议 App 内清理: WeCom/企业微信, WeChat/微信, Lark/飞书, app-managed chat or document stores.
- 谨慎处理: session databases, account state, VM/rootfs images, SDK toolchains, browser profiles, AI agent history.
- 不建议动: auth tokens, config, active databases, original chat data, current work sessions.

## Mole Execution Routing

- Status and health: `mo status --json`.
- Scoped disk analysis: `mo analyze --json <path>`.
- General cache cleanup: `mo clean --dry-run`, then `mo clean` only when its interactive selections map exactly to confirmed IDs.
- App uninstall: `mo uninstall --list` and `mo uninstall --dry-run <app>` first. Execute with Mole only when its app and leftover selections match separately confirmed uninstall/residue IDs; otherwise use the safest narrow main-uninstall fallback and keep residue cleanup separate.
- Project artifacts: `mo purge --dry-run`, then `mo purge` only for confirmed projects/artifact categories.
- Installer files: `mo installer --dry-run`, then `mo installer` only for confirmed files.
- Maintenance: `mo optimize --dry-run`, then `mo optimize` only after separately confirming the listed system changes.
- Audit: `mo history --json`; treat it as execution evidence, not a substitute for `df`/`du` verification.

Never use `mo uninstall --permanent` by default. Never run a broad Mole action merely because its dry-run total looks attractive.

## Quick Mode

Quick mode should usually complete in tens of seconds. Prefer:

- `mo status --json` for disk, memory, swap, health, and uptime.
- Scoped `mo analyze --json` for current hotspots.
- `mo clean --dry-run` when the user intends cleanup; stop a slow read-only traversal after sufficient evidence and report it as incomplete.
- Computer-impression hotspots.
- Known high-impact paths:
  - `~/Library/Containers/com.tencent.WeWorkMac`
  - `~/Library/Containers/com.tencent.xinWeChat`
  - `~/.cache/uv`
  - `~/.codex`
  - `~/.antigravity_cockpit`
  - `~/.gemini`
  - `~/.espressif`
  - `~/Library/Application Support/Claude/vm_bundles`
  - `~/Library/Caches`
  - `~/Library/Application Support/LarkShell`

Use native `df`, `sysctl`, `ps`, `du`, or `find` only to fill gaps or validate Mole. If quick mode cannot explain the pressure, offer deep mode instead of silently starting a slow full-disk scan.

## Hard Boundaries

- Do not run `rm -rf` against app data, chat data, SDKs, VM images, or unknown paths.
- Do not treat app uninstall as ordinary cache cleanup.
- Do not delete uninstall residue just because the path name resembles the app name; explain the evidence and possible data first.
- Do not combine app removal and residue cleanup into one implicit action. Ask separately.
- Do not remove LaunchDaemons, PrivilegedHelperTools, Group Containers, Keychain items, browser profiles, or sandbox Containers without explicit path-level confirmation.
- Do not delete WeCom/WeChat/Lark data from the command line; explain and guide App-internal cleanup.
- Do not delete `~/.codex`, `~/.antigravity_cockpit`, `~/.gemini`, `.espressif`, or Claude `vm_bundles` wholesale.
- Do not clean "all caches" as one action. Present scoped numbered candidates.
- Do not launch `mo clean`, `mo purge`, `mo installer`, or `mo optimize` unless the interactive scope can be constrained to confirmed IDs.
- Do not treat a Mole in-terminal confirmation as replacement for explicit chat confirmation.
- Do not use `mo uninstall --permanent` unless the user explicitly confirms permanent deletion after the recoverable default is explained.
- Do not let `mo uninstall` collapse main-app removal and unconfirmed residue cleanup; abort or fall back when leftovers cannot be deselected.
- Do not bypass App-internal-only rules merely because Mole detects the path.
- Do not write personal computer impressions into the skill repository.
- Do not claim cleanup succeeded without rechecking size/free-space evidence.

## Output Shape

For diagnosis, output:

1. Current headline: disk, swap, memory pressure, most suspicious process/path.
2. Super-heavy items: largest few paths/processes with size.
3. Cleanup candidates by risk group.
4. Recommended first actions.
5. Exact confirmation phrases for allowed next steps.
6. What will be written to computer impression.

For each cleanup candidate, include:

```text
编号:
路径:
当前大小:
这是什么:
从哪来:
干嘛用:
删除影响:
重建方式:
网络/VPN 成本:
建议动作:
执行方式:
确认方式:
```

For each uninstall residue candidate, also include:

```text
可能包含的数据:
- 用户数据:
- 账号/登录态:
- 缓存/索引:
- 插件/扩展:
- 后台服务:
- 许可证/Keychain:
- 可重建性:
归属证据:
```
