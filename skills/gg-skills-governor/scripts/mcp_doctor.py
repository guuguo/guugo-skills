#!/usr/bin/env python3
"""mcp_doctor.py — read-only MCP inventory & drift auditor for gg-skills-governor.

Reads the canonical registry (~/.agents/mcp/registry.json) and each editor's MCP
config, then reports, per editor, which registered servers are present / MISSING
(targeted but absent) / drift (present but not targeted), plus unmanaged servers
(present in an editor but not in the registry).

READ-ONLY by design. It NEVER edits any editor config. 补齐/同步 is performed by the
AGENT per the gg-skills-governor SKILL.md, because each editor uses a different
config format (TOML / JSON / YAML) and that translation is an agent judgement call.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path

DEFAULT_REGISTRY = os.environ.get("MCP_REGISTRY", "~/.agents/mcp/registry.json")
ROOT_KEY = {"toml": "mcp_servers", "yaml": "mcp_servers", "json": "mcpServers"}


def _expand(p: str) -> Path:
    return Path(os.path.expanduser(p))


def read_servers(cfg: dict) -> set | None:
    """Set of server names configured in one editor, or None if missing/unreadable."""
    path = _expand(cfg.get("config", ""))
    fmt = cfg.get("format")
    if not path.exists() or path.is_dir():
        return None
    try:
        text = path.read_text(encoding="utf-8")
        if fmt == "json":
            data = json.loads(text)
        elif fmt == "toml":
            try:
                import tomllib
            except ModuleNotFoundError:
                import tomli as tomllib  # py<3.11
            data = tomllib.loads(text)
        elif fmt == "yaml":
            try:
                import yaml
            except ModuleNotFoundError:
                return None
            data = yaml.safe_load(text) or {}
        else:
            return None
    except Exception:
        return None
    section = data.get(ROOT_KEY.get(fmt, "mcpServers")) or {}
    return set(section.keys()) if isinstance(section, dict) else set()


def audit(registry, only_editor=None, only_server=None):
    editors = {e: c for e, c in registry["editors"].items()
               if not only_editor or e == only_editor}
    servers = registry["servers"]
    actual = {e: read_servers(c) for e, c in editors.items()}
    rows = []
    for name, meta in servers.items():
        if only_server and name != only_server:
            continue
        targets = set(meta.get("targets", []))
        cells = {}
        for e in editors:
            present = actual[e] is not None and name in actual[e]
            targeted = e in targets
            cells[e] = ("ok" if present and targeted else
                        "MISSING" if targeted and not present else
                        "drift" if present and not targeted else "-")
        rows.append((name, cells))
    known = set(servers.keys())
    unmanaged = {e: sorted(s - known) for e, s in actual.items()
                 if s is not None and (s - known)}
    return editors, actual, rows, unmanaged


def main():
    ap = argparse.ArgumentParser(description="Read-only MCP registry / drift auditor.")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    ap.add_argument("--editor", help="audit a single editor")
    ap.add_argument("--server", help="audit a single server")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    reg_path = _expand(args.registry)
    if not reg_path.exists():
        print(f"registry not found: {reg_path}", file=sys.stderr)
        return 2
    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    editors, actual, rows, unmanaged = audit(registry, args.editor, args.server)
    missing = [(n, e) for n, c in rows for e, v in c.items() if v == "MISSING"]
    drift = [(n, e) for n, c in rows for e, v in c.items() if v == "drift"]

    if args.json:
        print(json.dumps({
            "registry": str(reg_path),
            "editors": {e: (None if actual[e] is None else sorted(actual[e])) for e in editors},
            "matrix": [{"server": n, **c} for n, c in rows],
            "missing": [{"server": n, "editor": e} for n, e in missing],
            "unmanaged": unmanaged,
            "drift": [{"server": n, "editor": e} for n, e in drift],
        }, ensure_ascii=False, indent=2))
        return 0

    elist = list(editors)
    print(f"MCP doctor · registry {reg_path}")
    print("editors: " + "  ".join(
        f"{e}({'unreadable/none' if actual[e] is None else str(len(actual[e]))+' servers'})"
        for e in elist))
    print()
    w = max([len(n) for n, _ in rows] + [12])
    print("server".ljust(w) + "  " + "  ".join(e[:11].ljust(11) for e in elist))
    for name, cells in rows:
        print(name.ljust(w) + "  " + "  ".join(cells[e].ljust(11) for e in elist))
    print()
    print("MISSING (targeted but absent) — agent should add per SKILL.md:")
    print("\n".join(f"  - {n}  ->  {e}" for n, e in missing) or "  none")
    if unmanaged:
        print("\nUnmanaged (present but not in registry — consider registering):")
        for e, lst in unmanaged.items():
            print(f"  - {e}: {', '.join(lst)}")
    if drift:
        print("\nDrift (present but not in targets):")
        print("\n".join(f"  - {n}  in {e}" for n, e in drift))
    return 0


if __name__ == "__main__":
    sys.exit(main())
