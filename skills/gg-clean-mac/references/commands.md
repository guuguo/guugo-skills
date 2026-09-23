# Commands

## Contents

- [Mole Preflight](#mole-preflight)
- [Mole Read-Only Baseline](#mole-read-only-baseline)
- [Mole Workflow Commands](#mole-workflow-commands)
- [Native Read-Only Fallback](#native-read-only-fallback)
- [Computer Impression](#computer-impression)
- [Native Uninstall Discovery Fallback](#native-uninstall-discovery-fallback)
- [Narrow Cleanup Fallbacks](#narrow-cleanup-fallbacks)
- [Native Uninstall Fallbacks](#native-uninstall-fallbacks)
- [App-Internal Cleanup Guidance](#app-internal-cleanup-guidance)
- [Post-Cleanup Verification](#post-cleanup-verification)

Use Mole first. Native commands are evidence or narrow fallbacks, not the default execution layer. Run state-changing commands only after explicit ID/path confirmation and the scope gate in `mole-execution-layer.md`.

## Mole Preflight

```bash
command -v mo
mo --version
```

Do not silently install or update Mole. If it is missing, continue read-only with native commands and offer installation separately.

## Mole Read-Only Baseline

```bash
mo status --json
mo analyze --json ~/Library/Caches
mo clean --dry-run
mo history --json --limit 20
```

Prefer scoped analysis paths selected from current evidence or computer-impression hotspots. `mo clean --dry-run` may be slow and interactive-looking even though it is read-only; report partial scans honestly if interrupted.

## Mole Workflow Commands

```bash
mo uninstall --list
mo uninstall --dry-run "App Name"
mo purge --dry-run
mo installer --dry-run
mo optimize --dry-run
```

After explicit confirmation, execute the corresponding command without `--dry-run`, selecting only confirmed rows/categories. Use `mo uninstall "App Name"` without `--permanent` so removal stays recoverable through Trash.

## Native Read-Only Fallback

```bash
df -h /
df -h /System/Volumes/Data
sysctl vm.swapusage
memory_pressure
```

### Process Snapshot

```bash
ps -axo pid,ppid,comm,rss,vsz -r | head -30
top -l 1 -o mem -n 20 -stats pid,command,mem,rsize,vsize
```

For richer process interpretation, use Python to parse `ps` output, but keep it read-only.

### Size Checks

Use `du -sh` for known paths:

```bash
du -sh ~/.cache/uv 2>/dev/null
du -sh ~/Library/Caches 2>/dev/null
du -sh ~/Library/Application\ Support/Claude/vm_bundles 2>/dev/null
```

Use shallow scans before broad scans:

```bash
du -d 1 -h ~ 2>/dev/null | sort -h | tail -30
du -d 1 -h ~/Library 2>/dev/null | sort -h | tail -30
du -d 1 -h ~/Library/Caches 2>/dev/null | sort -h | tail -30
du -d 1 -h ~/Library/Application\ Support 2>/dev/null | sort -h | tail -30
du -d 1 -h ~/.cache 2>/dev/null | sort -h | tail -30
```

Find large files only in scoped locations unless the user asks for deep mode:

```bash
find ~ -xdev -type f -size +1G -print 2>/dev/null
```

## Computer Impression

Read:

```bash
test -f ~/.agents/state/gg-clean-mac/computer-impression.json && \
  python3 -m json.tool ~/.agents/state/gg-clean-mac/computer-impression.json
```

Create or update with a JSON-aware tool. Do not append ad-hoc text. Keep summaries short.

## Native Uninstall Discovery Fallback

Use these to identify an app before proposing uninstall actions:

```bash
mdfind "kMDItemContentType == 'com.apple.application-bundle' && kMDItemDisplayName == 'App Name'"
mdls -name kMDItemCFBundleIdentifier -name kMDItemDisplayName -name kMDItemPath /Applications/App.app
osascript -e 'id of app "App Name"'
brew list --cask --versions
pkgutil --pkgs | sort
launchctl list | grep -i appname
```

Use scoped residue scans after identifying a bundle ID or vendor token:

```bash
find ~/Library -iname '*bundle.or.vendor.token*' -maxdepth 4 -print 2>/dev/null
find /Library/LaunchAgents /Library/LaunchDaemons /Library/PrivilegedHelperTools -iname '*bundle.or.vendor.token*' -print 2>/dev/null
du -sh <candidate-path> 2>/dev/null
```

Do not delete based only on name matching. Treat the result as evidence to explain, not proof to remove.

## Narrow Cleanup Fallbacks

Use only after explicit confirmation when Mole cannot preserve exact path-level scope. State the Mole limitation before execution.

```bash
uv cache clean
brew cleanup
go clean -cache
```

Playwright browser cache cleanup is medium risk. Prefer explaining first. Do not use this fallback if a confirmed Mole selection can target it safely:

```bash
rm -rf ~/Library/Caches/ms-playwright
```

Use only after confirming browser redownload cost.

For generic cache directories, prefer a recoverable move or scoped deletion of the exact confirmed candidate after checking that it is unchanged, unused, and not an app-data root. Avoid broad patterns and broad cache-root commands.

## Native Uninstall Fallbacks

Use these only when Mole does not recognize the app or the vendor's official uninstaller is safer:

```bash
brew uninstall --cask <cask>
brew uninstall --cask --zap <cask>
```

Use `--zap` only after explaining the exact zap list or residue categories and after the user confirms. Do not use it as a substitute for Mole's separate main-uninstall and residue stages. For `.pkg` installs, prefer official uninstallers or vendor docs; `pkgutil --forget` only forgets receipts and does not remove files.

## App-Internal Cleanup Guidance

For WeCom, WeChat, Lark, Claude, ChatGPT, and similar app data:

- Prefer in-app storage/cache management.
- Ask the user to close the app before any file-level operation.
- Do not run deletion commands against entire container or application support roots.

## Post-Cleanup Verification

Check Mole history first when Mole executed the action, then independently recheck:

```bash
mo history --json --limit 20
df -h /System/Volumes/Data
du -sh <path> 2>/dev/null
sysctl vm.swapusage
```

Report measured change. If free space did not improve, say so and inspect whether files moved to Trash, APFS accounting changed, the path was recreated, or Mole skipped the item. Do not treat history or exit status alone as proof of reclaim.
