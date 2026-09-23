# macOS Cleaning Targets

Use this reference to explain common large folders. Always rescan before reporting a size.

| Path | What it is | Source and use | Cleanup guidance | Rebuild/network cost |
| --- | --- | --- | --- | --- |
| `~/.cache/uv` | uv/Python package and interpreter cache. | Created by uv and Python tooling while resolving packages, wheels, sdists, and interpreters. | Low to medium risk. Prefer `uv cache clean` after confirmation. | Rebuilt by future uv/Python operations. Usually needs network; may access PyPI, mirrors, GitHub, or external resources; may use VPN traffic. |
| `~/Library/Caches/Homebrew` | Homebrew downloads, metadata, bottles, and API cache. | Created by `brew install`, `brew update`, and formula metadata fetches. | Low risk. Prefer `brew cleanup` and targeted cache cleanup after confirmation. | Rebuilt by Homebrew. Needs network; may access GitHub, Homebrew API, bottle CDN; may use VPN. |
| `~/Library/Caches/go-build` | Go build cache. | Created by `go build`, `go test`, and Go tools. | Low risk. Prefer `go clean -cache` after confirmation. | Rebuilt by compiling. Usually no network for cache itself, but builds may later fetch modules if module cache is missing. CPU/time cost. |
| `~/Library/Caches/ms-playwright` | Playwright browser binaries. | Created by Playwright installs or tests needing Chromium/Firefox/WebKit. | Medium risk. Remove only if user accepts browser redownload. | Tests will redownload large browser bundles, often from external CDN. Can consume hundreds of MB to multiple GB and VPN traffic. |
| `~/Library/Caches/JetBrains` | JetBrains IDE caches, indexes, local history-like caches, and Toolbox cache. | Created by IntelliJ/PyCharm/WebStorm/Toolbox. | Medium risk. Prefer closing IDE first; avoid deleting settings. | IDE rebuilds indexes with CPU/disk time. Some components may redownload over network. |
| `~/Library/Caches/semble` | Semble MCP or tool cache. | Created by `semble`/MCP processes and related Python/uv environments. | Medium risk. Stop runaway processes first; clean only scoped cache paths after confirmation. | May rebuild dependencies or indexes; may need Python package downloads and network/VPN. |
| `~/.codex` | Codex config, sessions, archived sessions, backups, logs, generated images, temp files. | Created by Codex app/CLI and Codex sessions. | High nuance. Consider old backups, archived sessions, logs, generated images, and tmp only. Never delete auth/config/current DB wholesale. | Some files are not meaningfully rebuildable. Logs/backups may be disposable; sessions/history may be valuable. |
| `~/.antigravity_cockpit` | Antigravity/Codex cockpit instances, sessions, backups, archived sessions, runtime state. | Created by Antigravity or related cockpit runtime. | High nuance. Consider old backups/archives only. Do not delete instance configs or active sessions blindly. | Runtime may recreate some state, but history and account/session data may be lost. |
| `~/.gemini` | Gemini and Antigravity data, browser profiles, recordings, backups, OAuth/account state. | Created by Gemini CLI/IDE and Antigravity integration. | High nuance. Browser recordings and old backups can be candidates; OAuth/profile/config should not be touched. | Some data can regenerate; profiles and auth may require login; recordings may be user data. |
| `~/.espressif` | ESP-IDF/ESP32 tools, toolchain downloads, Python envs, and dist cache. | Created by Espressif install scripts and ESP-IDF tooling. | Medium to high risk. `dist` download cache is more disposable; `tools` is the installed compiler/toolchain and should not be removed casually. | Reinstalling tools requires large downloads, often external resources, and may consume VPN traffic; also takes setup time. |
| `~/Library/Application Support/Claude/vm_bundles` | Claude local VM/rootfs bundle and session data. | Created by Claude/Claude Code local VM features. | High risk. Do not delete wholesale without explicit understanding. | May redownload or rebuild multi-GB rootfs images; likely external network and VPN traffic; local VM state may be lost. |
| `~/Library/Containers/com.tencent.WeWorkMac` | Enterprise WeChat/WeCom sandbox data: chat files, databases, profiles, local app data. | Created by WeCom while syncing messages, files, images, videos, and document previews. | App-internal cleanup only by default. Do not command-line delete. | Chat/file data may not be reliably rebuildable; redownload may require corporate network/login and can consume bandwidth. |
| `~/Library/Containers/com.tencent.xinWeChat` | WeChat sandbox data: chat files, xwechat files, mini programs, databases. | Created by WeChat while syncing messages, files, images, videos, and mini program data. | App-internal cleanup only by default. Do not command-line delete. | Chat/file data may not be reliably rebuildable; redownload may consume network and may be impossible for old media. |
| `~/Library/Application Support/LarkShell` | Feishu/Lark shell data, caches, search DBs, local resources, mini app/page assets. | Created by Lark/Feishu desktop app. | Prefer App-internal cleanup. Some caches/search DBs may be candidates only after app is closed and path is understood. | App may rebuild indexes and redownload resources; may need corporate/external network and bandwidth. |

## Risk Labels

- Low: cache can usually be rebuilt; still ask for confirmation.
- Medium: rebuild cost or temporary productivity hit is meaningful.
- High nuance: contains mixed cache, history, auth, profile, or app state; only scoped cleanup.
- App-internal: explain and route the user to app settings/storage management.

## Local Hotspots From This Machine

Known historical large items on this Mac:

- WeCom container around 50G.
- WeChat container around 19G.
- `~/.cache/uv` around 21G.
- `~/.codex` around 21G.
- `~/.antigravity_cockpit` around 16G.
- `~/.gemini` around 8.9G.
- `~/.espressif` around 6.3G.
- Claude `vm_bundles` around 6.3G.
- JetBrains caches around 5.3G.

Use these as scan priorities, not as current facts.

## Execution-Layer Notes

- Let Mole detect and preview generic macOS caches, logs, installer files, app bundles, and project artifacts.
- Keep package-manager caches (`uv`, Homebrew, Go) on their native narrow commands when `mo clean` cannot select the exact confirmed cache.
- Keep WeChat, WeCom, and Lark on App-internal cleanup even when Mole reports their paths.
- Keep mixed AI-agent homes, SDKs, browser profiles, VM bundles, and active indexes out of broad Mole cleanup. Use scoped analysis and candidate-level confirmation.
- Respect Mole whitelist results as protection signals. Do not remove a whitelist entry merely to increase reclaim without separate user confirmation.
