---
name: gg-skills-governor
description: "Govern the full lifecycle of AI skills across ~/.agents/skills and installed clients such as Codex, Claude, OpenCode, Antigravity, Qoderwork, and Hermes: inventory, install from Git repositories, link, sync, audit, repair, update, replace, remove, and project setup. Also govern MCP servers through ~/.agents/mcp/registry.json and audit editor divergence. Use for global skill maintenance, broken or conflicting links, upstream skill repositories, cross-client consistency, skills.sh/Vercel CLI interoperability, MCP inventory, or MCP synchronization."
---

# Skills Governor

## Outcome Contract

Treat `~/.agents/skills/` as the canonical skill surface consumed by installed AI clients. Keep repository sources, canonical links, and client links explicit and independently verifiable.

For an unscoped global request, govern these consumers:

- `codex`
- `claude`
- `opencode`
- `antigravity`
- `qoderwork`
- `hermes`

If the user names a target or requests project-local setup, limit the scope accordingly. Detect each client before creating its directory or links; report unavailable clients as `skipped`.

A skill operation is complete only when:

- the source and canonical paths are known;
- every in-scope installed client has been verified;
- no unreported `missing`, `broken-link`, `wrong-link`, or `conflict` state remains;
- mutations and retained risks are summarized in a status matrix.

## Storage Model

Use these defaults unless the environment provides explicit overrides:

| Layer | Default |
|---|---|
| Canonical skills | `~/.agents/skills/` |
| Repository sources | `~/.agents/sources/skills/` |
| Codex | `~/.codex/skills/` |
| Claude | `~/.claude/skills/` |
| OpenCode | `~/.config/opencode/skills/` |
| Antigravity | `~/.gemini/antigravity/skills/` |
| Qoderwork | `~/.qoderworkcn/skills/` |
| Hermes | `~/.hermes/skills/` |

For a repository bundle, keep the full clone at `~/.agents/sources/skills/<repo-name>/` and expose each usable skill as a relative canonical symlink:

```text
~/.agents/skills/<skill-name>
  -> ../sources/skills/<repo-name>/<path-to-skill>
```

Do not flatten-copy bundle contents into `~/.agents/skills/`. Product-owned system skills may remain in their product-owned directories.

Hermes uses category directories. Default to:

- `devops`: `gg-skills-governor`, `gg-ai-native-startup-playbook`
- `software-development`: `gg-fact-driven-ai-methodology`, `gg-harness`
- `creative`: `gg-child-psychology-for-content`
- `imported`: unmapped skills

## Tool Boundaries

### Native default

Use Git for repository acquisition and updates, filesystem symlinks for the canonical layer, and `skills_doctor.py` for client audit and repair. This is the default lifecycle and has no third-party skill-manager dependency.

Use Git conservatively:

- verify the exact remote URL before cloning;
- inspect `git status` before updating;
- use fast-forward-only pulls for a clean repository;
- never reset, discard, or overwrite local changes;
- stop and report when the source is dirty, diverged, private, or ambiguous.

Do not treat the whole `~/.agents/` tree as one upstream repository by default. Resolve whether a push, pull, or update applies to a specific source repository or to an explicitly configured canonical meta-repository.

### Optional Vercel Labs skills CLI

Use the Vercel Labs `skills` CLI only when the user explicitly requests it, wants skills.sh discovery, wants a temporary `skills use` workflow, or chooses CLI-managed lock-based installation.

It is an acquisition adapter, not the source of truth for local governance:

- do not require it for normal install, update, link, repair, or removal;
- do not assume its fixed client paths cover Qoderwork or Hermes categories;
- do not edit `.skill-lock.json` manually when it exists;
- after every CLI mutation, run the governor audit for all in-scope consumers;
- if the CLI reports success but canonical or custom-client artifacts remain, finish cleanup through the canonical model and report the discrepancy.

Prefer explicit agent names over wildcard removal. Verify the installed CLI version and help output before constructing commands because its argument behavior may change.

### Discovery boundary

Use `find-repo` to discover and evaluate GitHub repositories when source selection, activity, documentation, license, or implementation quality matters. Use `skills find` only for direct skills.sh keyword lookup.

Discovery does not authorize installation. Inspect the selected repository and exact skill path before changing local state.

## Skill Doctor

Use the bundled doctor for read-only inventory:

```bash
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target codex
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target claude
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target opencode
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target antigravity
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target qoderwork
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target hermes
```

Use `--skill <name>` for a focused operation, `--fix` to create or replace missing/broken managed symlinks, and `--prune` only after the user explicitly requests stale-link cleanup or approves the reported prune set.

Path overrides remain available:

```bash
python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py \
  --source /path/to/skills \
  --target codex \
  --target-dir /path/to/codex/skills
```

For an unscoped global audit or repair, run every target:

```bash
for target in codex claude opencode antigravity qoderwork hermes; do
  python3 ~/.agents/skills/gg-skills-governor/scripts/skills_doctor.py --target "$target"
done
```

Add `--fix` only when repair is authorized. For Antigravity, also verify that `chat.useClaudeSkills` is enabled.

## Lifecycle Rules

### Install

1. Resolve and inspect the exact repository and skill path.
2. Clone the repository under `~/.agents/sources/skills/` or reuse the verified existing clone.
3. Confirm the skill contains a valid `SKILL.md`.
4. Create a relative canonical symlink under `~/.agents/skills/`.
5. Audit, repair, and re-audit every in-scope consumer.

If the source is a single standalone skill rather than a bundle, preserve its repository identity instead of copying only `SKILL.md`.

### Update

1. Resolve the canonical link to its source repository.
2. Inspect the remote, branch, working tree, and incoming changes.
3. Update only when the repository can be fast-forwarded without losing local work.
4. Revalidate `SKILL.md` and any changed scripts.
5. Re-audit client links and report material upstream changes.

### Replace

Inspect the current source and all consumers before switching the canonical link. Do not overwrite a real directory or silently replace a differently sourced skill. Preserve a recoverable rollback path until verification succeeds.

### Remove

1. Audit the named skill across canonical and client paths.
2. Remove only links that resolve to the named canonical skill.
3. Remove the canonical symlink after consumer links are cleared.
4. Keep the source repository by default; delete or trash it only when the user explicitly requests source removal and no other skills depend on it.
5. Re-audit all in-scope consumers. For removal, `missing` is the expected final doctor state.

Never interpret removal of one skill as permission to remove its containing bundle.

### Project setup

Keep project-local skills inside the project and scope links only to requested project clients. Prefer copies only when the user requires a self-contained project or the client cannot consume symlinks.

## Skill Guardrails

- Never overwrite a real client directory without explicit approval.
- Never delete user-authored skills while repairing links.
- Prefer relative symlinks for global canonical and consumer links.
- Treat same-name real directories and differently sourced links as conflicts.
- Validate exact destructive targets; prefer recoverable trashing for material sources.
- Do not create client directories for unavailable clients.
- Do not claim success from a package-manager exit code alone.

## MCP Governance

Treat `~/.agents/mcp/registry.json` as the canonical MCP registry. MCP configurations are translated per editor rather than symlinked.

`scripts/mcp_doctor.py` is read-only. It reports:

- `ok`
- `MISSING`
- `drift`
- `unmanaged`

Audit with:

```bash
python3 ~/.agents/skills/gg-skills-governor/scripts/mcp_doctor.py
python3 ~/.agents/skills/gg-skills-governor/scripts/mcp_doctor.py --json
python3 ~/.agents/skills/gg-skills-governor/scripts/mcp_doctor.py --server <name>
```

For a targeted missing server, translate the registry entry into the editor's native format:

| Editor | Config |
|---|---|
| Codex | `~/.codex/config.toml` or active `$CODEX_HOME/config.toml` |
| Claude | `~/.claude.json`; prefer `claude mcp add` |
| Antigravity | `~/.gemini/antigravity/mcp_config.json` |
| Gemini | `~/.gemini/settings.json` |
| Hermes | `~/.hermes/config.yaml` |
| OpenCode | `~/.config/opencode/opencode.json` |
| Qoderwork | Resolve the actual config path before use |

Copy commands, arguments, URLs, and environment keys from the registry or a verified working editor. Never fabricate secrets or echo secret values. Do not distribute editor-built-in servers such as `node_repl`.

After changes, re-run `mcp_doctor.py` and tell the user to restart or reconnect affected editors.

## Final Report

For skill operations, report:

- source repository and skill path;
- canonical path;
- in-scope consumers;
- per-consumer `linked` / `missing` / `conflict` / `skipped` status;
- changes made and anything deliberately retained.

For MCP operations, report:

- registry path;
- in-scope editors;
- server-by-editor status;
- translated changes;
- restart or reconnect requirement.
