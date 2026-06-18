---
name: skills-governor
description: Use when installing, linking, syncing, auditing, repairing, replacing, or removing AI skills across ~/.agents/skills and agent-specific skill directories such as Codex, Claude, Gemini, Antigravity IDE, Qoderwork, or Hermes.
---

# Skills Governor

## Core Rule

Treat `~/.agents/skills/` as the default canonical skill source unless the user or environment provides a different source directory. Agent-specific skill directories such as `~/.codex/skills/`, `~/.claude/skills/`, `~/.gemini/antigravity/skills/`, `~/.qoderworkcn/skills/`, and `~/.hermes/skills/` consume that source through symlinks unless the user explicitly asks for a copy or a product-owned system skill.

Default to global maintenance. If the user asks to install, link, sync, repair, replace, or make a skill available and does not explicitly restrict the target, audit and repair all global skill consumers:

- `codex`
- `claude`
- `antigravity`
- `qoderwork`
- `hermes`

Do not stop after the first mentioned or currently active agent. A task is complete only after the requested skill or skill set is verified across every in-scope consumer, with a short status matrix in the final response.

Before creating links for any target, detect whether that client exists. If the client is not installed or no known client marker exists, skip that target and report it as `skipped`; do not create the target skill directory merely because a link task was requested.

Use this skill for requests like:
- "install this skill", "sync skills", "push/pull skills"
- "link these skills to Codex", "link these skills to Claude"
- "link these skills to Antigravity IDE"
- "link these skills to Qoderwork"
- "link these skills to Hermes"
- "repair broken skill links", "remove old skills", "replace this skill"
- "show me unmanaged skills", "doctor my skill setup", "clean stale links"
- "set up project skills"
- "make this skill available everywhere"
- "install mcp", "add mcp", "sync mcp", "manage mcp"
- "configure Codex/Claude/Gemini/Antigravity/Qoder MCP"
- "make MCP available everywhere"

This skill should trigger for the full lifecycle of skill management:
- install
- link
- sync
- inspect
- repair
- replace
- remove
- project-level setup

This skill should also trigger for the full lifecycle of MCP management:
- register
- install
- sync
- inspect
- repair
- profile
- project-level setup

## Default Path Profile

- Canonical repo root: `~/.agents/`
- Canonical skills: `~/.agents/skills/`
- Canonical external skill sources: `~/.agents/sources/skills/`
- Codex global skills: `~/.codex/skills/`
- Claude global skills: `~/.claude/skills/`
- Antigravity IDE global skills: `~/.gemini/antigravity/skills/`
- Qoderwork global skills: `~/.qoderworkcn/skills/`
- Hermes global skills: `~/.hermes/skills/`
- Hermes category defaults: `devops` for `skills-governor` and `ai-native-startup-playbook`; `software-development` for `fact-driven-ai-methodology`; `imported` for unmapped skills
- Existing lock file: `~/.agents/.skill-lock.json`
- Canonical MCP config repo: `~/mcp-config/`
- Canonical MCP server manifests: `~/mcp-config/servers/`
- Canonical MCP profiles: `~/mcp-config/profiles/`
- Gemini MCP config target: `~/.gemini/config/mcp_config.json`
- Qoder MCP config target: `~/Library/Application Support/Qoder/SharedClientCache/mcp.json`
- Project MCP config targets: `./.mcp.json`, `./.antigravity/mcp.json`, `.cursor/mcp.json` when supported

Treat these paths as defaults, not universal constants. If the user has a different home layout, a project-local skill source, or client-specific skill directories, resolve and use those paths explicitly.

Never edit `.skill-lock.json` by hand. It is owned by the skills-manager CLI.

Never duplicate MCP server definitions across agents by hand when they can be generated from `~/mcp-config/`.

For repository-level skill bundles, clone the full upstream project under
`~/.agents/sources/skills/<repo-name>/`. Expose individual usable skills from
`~/.agents/skills/` as symlinks into the cloned repository, for example
`~/.agents/skills/<skill-name> -> ../sources/skills/<repo-name>/skills/<skill-name>`.
Do not flatten-copy bundle subdirectories into `~/.agents/skills/`; this keeps
updates centralized through the source clone.

## Preferred Tools

Use the existing skills-manager wrapper first:

```bash
SM="$HOME/.agents/skills/skills-manager/scripts/sm.sh"
"$SM" --version
```

Common operations:

```bash
"$SM" pull
"$SM" push -m "update skills"
"$SM" link --agents codex
"$SM" link --agents claude-code
"$SM" link --project --agents codex --mode copy
```

When a client target is not yet exposed by `skills-manager` (for example Antigravity IDE, Qoderwork, or Hermes global skills), use `skills_doctor.py` directly.

For Antigravity IDE, also verify that the client-side compatibility switch `chat.useClaudeSkills` is enabled in the user's IDE settings.

If the request is inspection or repair-oriented, use the bundled doctor:

```bash
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target antigravity --fix
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target codex --fix
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target claude --fix --prune
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target qoderwork --fix
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target hermes --fix
```

The doctor defaults to `~/.agents/skills/`, but supports path overrides:

```bash
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --source /path/to/skills --target codex
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target codex --target-dir /path/to/codex/skills
python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target codex --skill my-skill --fix
SKILLS_GOVERNOR_HERMES_CATEGORY_MY_SKILL=devops python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target hermes --skill my-skill --fix
SKILLS_GOVERNOR_SOURCE=/path/to/skills python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py
```

For global skill sync or repair, run the full target loop unless the user explicitly scopes the request:

```bash
for target in codex claude antigravity qoderwork hermes; do
  python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target "$target"
done
```

When fixing missing or broken links globally, run:

```bash
for target in codex claude antigravity qoderwork hermes; do
  python3 ~/.agents/skills/skills-governor/scripts/skills_doctor.py --target "$target" --fix
done
```

Use `--prune` only when the user explicitly asks to clean stale links or when you have already reported what will be pruned.

For MCP management, prefer a single source of truth under `~/mcp-config/` and a sync step that materializes client-specific configs:

```bash
~/mcp-config/sync.sh
```

Expected outputs include:

- `~/.codex/config.toml`
- `~/.gemini/config/mcp_config.json`
- `~/Library/Application Support/Qoder/SharedClientCache/mcp.json`
- `~/.claude/` client config files
- `./.mcp.json`
- `./.antigravity/mcp.json`

Use profile selection to keep the same server inventory but vary trust level:

- `coding.json` for normal coding work
- `safe-readonly.json` for inspection-only work
- `project-full.json` for project-specific high-trust setups

## Workflow

1. Identify whether the user wants installation, inventory, sync, link, repair, replacement, removal, or project setup.
2. Resolve scope:
   - If the user names one target, such as "Codex only" or "link to Claude", operate only on that target.
   - If the user says "everywhere", "global", "sync skills", "manage this skill", or does not name a target, scope is `codex`, `claude`, `antigravity`, `qoderwork`, and `hermes`.
   - If the user asks for project setup, scope is only the current project targets.
3. Inspect all in-scope targets before changing state. Prefer `skills_doctor.py` for link status and conflict detection.
4. Use `skills-manager` for GitHub-backed `pull`, `push`, and standard targets it supports.
5. Use `skills_doctor.py --fix` for deterministic symlink creation or broken symlink replacement, especially for Antigravity IDE, Qoderwork, and Hermes.
6. Use `skills_doctor.py --prune` when stale or orphaned links should be removed from Codex, Claude, Antigravity IDE, Qoderwork, or Hermes.
7. Report the changed paths and any conflicts that were skipped.
8. Verify all in-scope targets after fixes. For a named skill, confirm that exact skill is `linked` in every target. For a broad sync, confirm no `missing`, `broken`, or `conflict` statuses remain unless explicitly reported.
9. For repository-level skill bundles, clone or update the upstream repository in `~/.agents/sources/skills/<repo-name>/`, then create or repair `~/.agents/skills/<skill-name>` symlinks to the real skill directories inside that clone.
10. For MCP requests, resolve the desired profile first, then sync `~/mcp-config/` into the target agents and project files.
11. When a user asks to "install mcp" or "add mcp", treat it as: install the server once, add it to the canonical MCP repo, then sync all selected agent targets.

## Completion Criteria

For skill management, final output must include:

- The canonical source path.
- The in-scope target list.
- A status matrix with each target and `linked` / `missing` / `conflict` / `skipped`.
- Any changes made.
- Any client-specific follow-up, such as enabling Antigravity IDE's `chat.useClaudeSkills`.

Do not answer "done" after verifying only Codex or Claude when the request was global or unscoped.

## MCP Operating Model

### Canonical Source

Maintain all MCP server definitions in `~/mcp-config/servers/` and all reusable trust bundles in `~/mcp-config/profiles/`.

### Sync Rule

Do not manually maintain per-agent MCP JSON/TOML unless a target cannot be generated. Prefer one repo, one sync script, many generated targets.

Qoder uses a JSON object with an `mcpServers` map at
`~/Library/Application Support/Qoder/SharedClientCache/mcp.json`. Generate this
file from `~/mcp-config/` during sync. For stdio servers, write `command`,
`args`, and `env` entries. For SSE or Streamable HTTP servers, write
`"type": "sse"` and `url` entries; if the canonical server manifest uses
`serverUrl`, map it to Qoder's `url` field or add a `qoder` override in the
server manifest. Qoder blocks shell control syntax such as `&&`, `||`, pipes,
semicolons, redirects, backticks, and `$()` in MCP args. When setup requires
shell logic, create an executable wrapper under `~/mcp-config/bin/` and point
the `qoder.command` override at that wrapper with plain args.

For Gemini, Antigravity, Qoder, and other stdio MCP clients, watch for clients
that launch servers with cwd set to `/`, `$HOME`, or another unsuitable
directory. If an MCP server is cwd-sensitive or auto-initializes per-repo state,
add a client-specific manifest override under `~/mcp-config/servers/<name>.json`
and start it from a dedicated writable client context directory such as
`~/.gemini/<server>-mcp-context` or `~/.qoder/<server>-mcp-context`. Do not use
`$HOME` itself for per-repo tools whose local context directory may collide with
global config directories.

### Client Compatibility Rule

Treat Codex success as a smoke test, not proof that the same MCP config will run
unchanged in every client. Before syncing a new stdio MCP server broadly:

1. Use absolute paths for `command` when the client may be launched from a GUI.
2. Pin language runtimes explicitly when dependencies require a minimum version,
   for example `uvx --python ~/.local/bin/python3 ...`.
3. Keep `args` as literal argv values, not shell snippets. Put shell setup,
   `cd`, `mkdir`, env bootstrapping, and command chaining in a wrapper script.
4. Add client-specific overrides for Qoder, Gemini, or Antigravity when cwd,
   PATH, env, or security policy differs from Codex.
5. Smoke-test from a hostile cwd such as `/` with a minimal environment before
   declaring the MCP available everywhere.

### Installation Rule

When the user asks to install a new MCP server:

1. Add the server manifest to `~/mcp-config/servers/<name>.json`.
2. Add or update any profile entries that should include it.
3. Add client-specific overrides or wrapper scripts when the server depends on
   cwd, PATH, Python/Node versions, shell features, or local writable state.
4. Run `~/mcp-config/sync.sh` to update agent configs and project configs.
5. Verify each selected target agent can see the server and list its tools.

### Project Rule

If the request is project-scoped, sync only the current project targets and add a short repo note in `AGENTS.md` or `CLAUDE.md` that tells AI to prefer CodeGraph for cross-file analysis, refactors, and call-chain tracing.

### Auto-Trigger Rule

If the user says any of these, switch into MCP management mode automatically:

- install mcp
- add mcp
- configure mcp
- sync mcp
- repair mcp
- manage mcp
- mcp for codex/claude/gemini/antigravity/qoder

## Guardrails

- Do not overwrite a real directory in an agent-specific skills folder without explicit user approval.
- Do not delete user skills while repairing links.
- Do not create links for a target until the corresponding client is detected. Report unavailable targets as `skipped`.
- Prefer relative symlinks for global links.
- When a skill exists in `~/.agents/skills/` but not in Codex, Claude, Antigravity IDE, Qoderwork, or Hermes, link it rather than copying it.
- When a target has a real directory with the same name, report it as a conflict.
- When pruning, remove only symlinks that are stale, broken, or no longer managed by `~/.agents/skills/`.
- Do not hardcode server definitions in multiple agent configs when they can be generated from `~/mcp-config/`.
