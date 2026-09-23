# Computer Impression Schema

## Contents

- [Location](#location)
- [Source of Truth](#source-of-truth)
- [Top-Level Shape](#top-level-shape)
- [Hotspot Item](#hotspot-item)
- [Known Incident Item](#known-incident-item)
- [Recent Scan Item](#recent-scan-item)
- [Update Rules](#update-rules)

## Location

The long-term computer impression lives outside the skill repository:

```text
~/.agents/state/gg-clean-mac/computer-impression.json
```

Create parent directories if needed. Treat this file as private local machine state. Do not commit it.

## Source of Truth

JSON is the only long-term source of truth. Markdown reports may be generated for display, but do not maintain a second Markdown state file.

## Top-Level Shape

```json
{
  "schema_version": 1,
  "updated_at": "2026-07-06T18:00:00+08:00",
  "machine_summary": {
    "hostname": "optional",
    "os": "macOS",
    "disk_profile": "Data volume often low on free space",
    "common_pressure": ["disk", "swap"],
    "developer_stack": ["python", "node", "ai-agents"],
    "notes": []
  },
  "preferences": {
    "language": "zh-CN",
    "cleanup_confirmation": "explicit-id-required",
    "app_data_policy": {
      "wechat": "app-internal-only",
      "wecom": "app-internal-only",
      "lark": "prefer-app-internal"
    },
    "never_touch_patterns": [
      "auth",
      "credentials",
      "current sessions"
    ]
  },
  "hotspots": [],
  "known_incidents": [],
  "recent_scans": []
}
```

## Hotspot Item

```json
{
  "path": "~/.cache/uv",
  "label": "uv Python package cache",
  "category": "package-cache",
  "risk": "low",
  "recommended_action": "use tool cleanup command after confirmation",
  "last_seen_at": "2026-07-06T18:00:00+08:00",
  "last_size_bytes": 22548578304,
  "max_seen_bytes": 22548578304,
  "recurs": true,
  "confidence": 0.9,
  "rebuild": {
    "method": "uv or Python tools redownload packages",
    "needs_network": true,
    "may_need_external_network": true,
    "may_use_vpn": true,
    "cost_note": "Can redownload many Python wheels from PyPI or configured mirrors."
  },
  "notes": []
}
```

## Known Incident Item

Use for process or event memories, not just paths:

```json
{
  "id": "chatgpt-large-swap-20260706",
  "seen_at": "2026-07-06T17:03:00+08:00",
  "summary": "ChatGPT.app had about 29G footprint and about 28G swapped.",
  "category": "swap",
  "evidence": {
    "process": "ChatGPT.app",
    "swap_used": "about 28G"
  },
  "recommended_future_check": "Check ChatGPT.app among top memory processes when swap is high."
}
```

## Recent Scan Item

Keep only 5-10 summaries:

```json
{
  "scanned_at": "2026-07-06T18:00:00+08:00",
  "mode": "quick",
  "disk_free": "2.5Gi",
  "swap_used": "41Gi",
  "top_findings": [
    "WeCom container about 50G",
    "uv cache about 21G"
  ],
  "actions_taken": [
    "scan only"
  ],
  "measured_reclaim": "0B",
  "notes": []
}
```

## Update Rules

- Always rescan a hotspot before presenting it as current.
- If a path disappears or shrinks, lower confidence or mark stale; do not delete the record immediately.
- Update `max_seen_bytes` only when current size is larger.
- Store durable preferences, not one-turn instructions.
- Store summaries, not raw command output.
- Trim `recent_scans` to the newest 10 items.
- Avoid secrets, tokens, full chat filenames, or private document titles in notes.
- Summarize whether Mole or a narrow fallback executed cleanup. Record the fallback reason, not raw command output.
- When Mole executes, store its version only when relevant to a compatibility or behavior incident; do not duplicate it in every scan.
