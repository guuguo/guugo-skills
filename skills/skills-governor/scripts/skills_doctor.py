#!/usr/bin/env python3
"""Inspect and optionally repair skill symlinks from a canonical skill source."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


HOME = Path.home()
DEFAULT_SOURCE = Path(os.environ.get("SKILLS_GOVERNOR_SOURCE", HOME / ".agents" / "skills")).expanduser()
DEFAULT_TARGETS = {
    "antigravity": Path(
        os.environ.get(
            "SKILLS_GOVERNOR_ANTIGRAVITY_DIR",
            HOME / ".gemini" / "antigravity" / "skills",
        )
    ).expanduser(),
    "codex": Path(os.environ.get("SKILLS_GOVERNOR_CODEX_DIR", HOME / ".codex" / "skills")).expanduser(),
    "claude": Path(os.environ.get("SKILLS_GOVERNOR_CLAUDE_DIR", HOME / ".claude" / "skills")).expanduser(),
    "qoderwork": Path(
        os.environ.get("SKILLS_GOVERNOR_QODERWORK_DIR", HOME / ".qoderworkcn" / "skills")
    ).expanduser(),
}


def is_skill_dir(path: Path) -> bool:
    return path.is_dir() and (path / "SKILL.md").is_file()


def rel_target(src: Path, dst_parent: Path) -> str:
    return os.path.relpath(src, dst_parent)


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def inspect_target(name: str, target: Path, source: Path, selected_skills: set[str] | None = None) -> dict:
    all_skills = sorted(p for p in source.iterdir() if is_skill_dir(p))
    managed_names = {p.name for p in all_skills}
    skills = [p for p in all_skills if selected_skills is None or p.name in selected_skills]
    source_resolved = source.resolve(strict=False)
    rows = []
    for src in skills:
        dst = target / src.name
        row = {
            "skill": src.name,
            "source": str(src),
            "target": str(dst),
            "status": "missing",
        }
        if dst.is_symlink():
            resolved = dst.resolve(strict=False)
            if resolved == src.resolve(strict=False):
                row["status"] = "linked"
            elif not dst.exists():
                row["status"] = "broken-link"
                row["points_to"] = os.readlink(dst)
            else:
                row["status"] = "wrong-link"
                row["points_to"] = os.readlink(dst)
        elif dst.exists():
            row["status"] = "conflict"
        rows.append(row)

    if target.exists() and selected_skills is None:
        for entry in sorted(target.iterdir()):
            if entry.name in managed_names:
                continue
            if not entry.is_symlink():
                continue
            points_to = os.readlink(entry)
            resolved = entry.resolve(strict=False)
            if is_under(resolved, source_resolved) or not entry.exists():
                rows.append(
                    {
                        "skill": entry.name,
                        "source": None,
                        "target": str(entry),
                        "status": "orphan-link" if entry.exists() else "broken-orphan-link",
                        "points_to": points_to,
                    }
                )

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1

    return {
        "target_name": name,
        "target_dir": str(target),
        "source_dir": str(source),
        "selected_skills": sorted(selected_skills) if selected_skills else None,
        "counts": counts,
        "skills": rows,
    }


def fix_target(report: dict) -> list[dict]:
    target = Path(report["target_dir"])
    target.mkdir(parents=True, exist_ok=True)
    changes = []
    for row in report["skills"]:
        status = row["status"]
        if row["source"] is None:
            continue
        dst = Path(row["target"])
        src = Path(row["source"])
        if status == "linked" or status == "conflict" or status == "wrong-link":
            continue
        if status == "broken-link":
            dst.unlink()
        if status in {"missing", "broken-link"}:
            dst.symlink_to(rel_target(src, target))
            changes.append({"skill": src.name, "action": "linked", "target": str(dst)})
    return changes


def prune_target(report: dict) -> list[dict]:
    changes = []
    for row in report["skills"]:
        if row["status"] not in {"orphan-link", "broken-orphan-link"}:
            continue
        dst = Path(row["target"])
        if dst.is_symlink():
            dst.unlink()
            changes.append({"skill": row["skill"], "action": "pruned", "target": str(dst)})
    return changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Canonical skill source directory.")
    parser.add_argument("--target", choices=sorted(DEFAULT_TARGETS), default="codex")
    parser.add_argument("--target-dir", type=Path, help="Override the selected target directory.")
    parser.add_argument("--skill", action="append", help="Limit inspection or repair to one skill. Repeatable.")
    parser.add_argument("--fix", action="store_true", help="Create missing symlinks and replace broken symlinks.")
    parser.add_argument("--prune", action="store_true", help="Remove stale or orphaned symlinks from the target.")
    parser.add_argument("--only-problems", action="store_true", help="Only print non-linked rows.")
    args = parser.parse_args()

    source = args.source.expanduser()
    target = args.target_dir.expanduser() if args.target_dir else DEFAULT_TARGETS[args.target]

    if not source.exists():
        raise SystemExit(f"Missing source directory: {source}")

    selected_skills = set(args.skill) if args.skill else None
    missing_selected = []
    if selected_skills:
        missing_selected = [
            skill
            for skill in sorted(selected_skills)
            if not is_skill_dir(source / skill)
        ]
        if missing_selected:
            raise SystemExit(f"Missing selected skills in {source}: {', '.join(missing_selected)}")

    report = inspect_target(args.target, target, source, selected_skills)
    changes = fix_target(report) if args.fix else []
    prune_changes = prune_target(report) if args.prune else []
    if args.fix or args.prune:
        report = inspect_target(args.target, target, source, selected_skills)
        report["changes"] = changes + prune_changes

    if args.only_problems:
        report["skills"] = [row for row in report["skills"] if row["status"] != "linked"]

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
