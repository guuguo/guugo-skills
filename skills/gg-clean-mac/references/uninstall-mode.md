# Uninstall Mode

## Contents

- [Core Rule](#core-rule)
- [Identify First](#identify-first)
- [Preferred Uninstall Path](#preferred-uninstall-path)
- [Residue Candidate Categories](#residue-candidate-categories)
- [Residue Output Template](#residue-output-template)
- [Risk Defaults](#risk-defaults)
- [Example Wording](#example-wording)

Use this reference when the user asks to uninstall software, clean uninstall residue, or make an app removal "clean".

## Core Rule

Uninstall mode has three phases:

1. Identify the app and installation source.
2. Propose the safest main uninstall path.
3. Scan and explain residue candidates, then request a second confirmation for selected residue cleanup.

Do not collapse these phases into one "uninstall cleanly" action.

Use Mole as the default uninstall discovery and preview layer when it recognizes the app. Run `mo uninstall --list`, then `mo uninstall --dry-run <exact-name>`. Execute with Mole only when the app and every leftover it will remove map to separately confirmed IDs. If Mole bundles unconfirmed leftovers and cannot deselect them, use the safest narrow main-uninstall fallback and keep residue as phase 3. Never add `--permanent` by default.

## Identify First

Collect read-only evidence:

- App bundle path: `/Applications/<App>.app` or `~/Applications/<App>.app`.
- Bundle ID: `mdls` or `osascript -e 'id of app "App Name"'`.
- Install source:
  - App Store.
  - Homebrew Cask.
  - `.pkg` installer receipt.
  - Drag-and-drop app bundle.
  - Vendor installer or updater.
- Background components:
  - `~/Library/LaunchAgents`.
  - `/Library/LaunchAgents`.
  - `/Library/LaunchDaemons`.
  - `/Library/PrivilegedHelperTools`.
  - Login Items, menu bar helpers, auto updaters.

If source is unclear, say so and keep actions conservative.

## Preferred Uninstall Path

| Source | Preferred action | Notes |
| --- | --- | --- |
| Official uninstaller exists | Use official uninstaller first. | Best for drivers, VPNs, security tools, virtualization, sync clients, and apps with privileged helpers. |
| Mole recognizes the app and scope is selectable | `mo uninstall --dry-run <exact-name>`, then `mo uninstall <exact-name>` after separate app/residue confirmations. | Preferred general-app route; sends removals to Trash and records history. |
| Mole bundles unconfirmed leftovers | Use the safest narrow main-uninstall fallback. | Do not let Mole collapse the two confirmation stages; scan residue afterward. |
| Homebrew Cask not recognized by Mole | `brew uninstall --cask <name>` after confirmation. | Native fallback. Consider `--zap` only in the separate residue phase after explaining exact scope. |
| App Store | Use Finder/Launchpad/App Store guidance. | Receipts and sandbox data may remain; explain residue separately. |
| `.pkg` installer | Prefer vendor uninstall docs. | Receipts do not list every live file safely; `pkgutil --forget` is not uninstall. |
| Drag-and-drop `.app` not recognized by Mole | Move the app bundle to Trash after confirmation. | Native fallback; then scan residue separately. |

The skill never merges the main uninstall and residue cleanup stages. Mole may bundle them technically, so execute it only when the user's separate confirmations cover the exact combined selection.

## Residue Candidate Categories

Every residue item must state possible data types, not just "leftover file".

| Location pattern | Possible data | Default stance |
| --- | --- | --- |
| `~/Library/Application Support/<App or Vendor>` | User data, local databases, workspace state, plugins, downloaded runtimes, indexes, account state. | Cautious; default do not delete unless user wants full removal. |
| `~/Library/Caches/<bundle-id>` | Cache, thumbnails, temporary downloads, search or browser cache, update cache. | Usually safe after confirmation. |
| `~/Library/Preferences/<bundle-id>.plist` | Settings, window layout, feature flags, login preference, license toggles. | Low space value; delete only for reset/clean uninstall. |
| `~/Library/Containers/<bundle-id>` | Sandboxed app data, documents, databases, downloads, chat/media data. | High risk; default preserve. |
| `~/Library/Group Containers/<team-or-vendor>` | Shared account state, sync databases, extensions, shared caches, office/chat data. | High risk; default preserve unless ownership is strong. |
| `~/Library/Logs` and crash reports | Logs and crash reports. | Usually safe, low value unless debugging. |
| `~/Library/Saved Application State/<bundle-id>.savedState` | Window/session restore state. | Usually safe, tiny. |
| `~/Library/LaunchAgents/<bundle-or-vendor>.plist` | User-level background updater, sync helper, menu helper. | Can remove after verifying ownership and stopping service. |
| `/Library/LaunchAgents` and `/Library/LaunchDaemons` | System or all-user background services. | High risk; prefer official uninstaller. |
| `/Library/PrivilegedHelperTools` | Admin helper for VPN, driver, virtualization, security, updater. | High risk; prefer official uninstaller. |
| Keychain items | Tokens, credentials, licenses. | Never delete automatically; only mention possible manual review. |
| Browser profiles/extensions | Cookies, local storage, extensions, user profile state. | High risk; default preserve. |

## Residue Output Template

For every residue candidate:

```text
残留编号:
路径:
当前大小:
归属证据:
可能包含的数据:
- 用户数据:
- 账号/登录态:
- 缓存/索引:
- 插件/扩展:
- 后台服务:
- 许可证/Keychain:
- 可重建性:
删除影响:
重建方式:
网络/VPN 成本:
建议动作:
确认方式:
```

## Risk Defaults

- Cache-only residue can be recommended for cleanup after confirmation.
- Preferences and saved state are usually small; do not present them as space-saving wins.
- Application Support, Containers, Group Containers, Keychain, LaunchDaemons, and PrivilegedHelperTools need stronger evidence and clearer warnings.
- Developer and AI apps may store models, sessions, project state, browser profiles, credentials, and local VMs. Do not assume residue is disposable.
- Chat and office apps may store original media, documents, message databases, search indexes, and corporate account state. Prefer app-internal cleanup or preserve.

## Example Wording

```text
残留 3
路径: ~/Library/Application Support/JetBrains
可能包含的数据:
- 用户数据: IDE 配置、项目历史、插件配置
- 账号/登录态: 可能有账号状态或授权状态
- 缓存/索引: 有项目索引和本地缓存
- 插件/扩展: 可能有已安装插件
- 可重建性: 索引可重建；配置、插件选择和历史不一定值得丢
建议动作: 如果只是省空间，暂缓；如果目标是彻底卸载 JetBrains，再单独确认。
确认方式: 清理残留 3
```
