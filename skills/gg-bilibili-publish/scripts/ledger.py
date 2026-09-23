#!/usr/bin/env python3
"""B站发布台账：配置、校验、状态、待同步对账与异常记录。成功行由发布引擎追加。"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_CONFIG = Path.home() / ".config/gg-bilibili-publish/config.json"
VIDEO_MARKER = "## 已发布作品"
COLUMN_MARKER = "## 专栏发布记录"
EXCEPTION_MARKER = "## 删除/异常记录"
VIDEO_COLUMNS = [
    "published_at", "series", "work_label", "source_file", "sha256",
    "title", "aid", "bvid", "cid", "status",
]
IDENTITY_FIELDS = ("sha256", "aid", "bvid")
BACKTICK_FIELDS = {"source_file", "sha256", "aid", "bvid", "cid"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    with temporary.open("w", encoding="utf-8") as file_obj:
        file_obj.write(content)
        file_obj.flush()
        os.fsync(file_obj.fileno())
    temporary.replace(path)


def write_json(path: Path, data: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def absolute(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("必须指定绝对路径")
    if sys.platform == "darwin" and len(path.parts) > 2 and path.parts[1] == "Volumes":
        volume = Path(*path.parts[:3])
        if not volume.is_mount():
            raise ValueError(f"外置卷未挂载: {volume}")
    return path.resolve()


def resolve_ref(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path)


@dataclass(frozen=True)
class Workspace:
    config_path: Path
    project_root: Path
    ledger_path: Path
    log_root: Path
    staging_root: Path
    upload_copy_dir: Path


def load_workspace(config_path: Path = DEFAULT_CONFIG) -> Workspace:
    path = config_path.expanduser()
    if not path.is_file():
        raise ValueError(f"尚未配置 B站发布工作区: {path}；先运行 configure --project-root")
    data = read_json(path)
    if data.get("schema_version") != 1:
        raise ValueError("schema_version 必须为 1")
    root = absolute(data["project_root"])
    return Workspace(
        config_path=path.resolve(),
        project_root=root,
        ledger_path=resolve_ref(root, data.get("ledger_path", "docs/harness/notes/bilibili-publish-record.md")),
        log_root=resolve_ref(root, data.get("log_root", "logs/bilibili-publish")),
        staging_root=resolve_ref(root, data.get("staging_root", "tmp/publish-staging/bilibili")),
        upload_copy_dir=absolute(data.get("upload_copy_dir", str(Path.home() / "Downloads/platform-publish"))),
    )


def configure(config_path: Path, project_root: Path, **overrides: str) -> dict[str, Any]:
    root = absolute(project_root)
    data = read_json(config_path) if config_path.is_file() else {"schema_version": 1}
    data["schema_version"] = 1
    data["project_root"] = str(root)
    defaults = {
        "ledger_path": "docs/harness/notes/bilibili-publish-record.md",
        "log_root": "logs/bilibili-publish",
        "staging_root": "tmp/publish-staging/bilibili",
        "upload_copy_dir": str(Path.home() / "Downloads/platform-publish"),
    }
    for key, default in defaults.items():
        data[key] = overrides.get(key) or data.get(key) or default
    write_json(config_path, data)
    workspace = load_workspace(config_path)
    return {
        "config": str(workspace.config_path),
        "project_root": str(workspace.project_root),
        "ledger_path": str(workspace.ledger_path),
        "log_root": str(workspace.log_root),
        "staging_root": str(workspace.staging_root),
        "upload_copy_dir": str(workspace.upload_copy_dir),
    }


def strip_cell(value: str) -> str:
    text = value.strip()
    if text.startswith("`") and text.endswith("`") and len(text) >= 2:
        return text[1:-1]
    return text


def parse_row(line: str) -> dict[str, str] | None:
    if not line.startswith("|") or re.match(r"^\|\s*:?-{3,}", line):
        return None
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    if len(cells) != len(VIDEO_COLUMNS):
        return None
    if cells[0] in {"发布时间", "时间"}:
        return None
    return {key: strip_cell(value) for key, value in zip(VIDEO_COLUMNS, cells)}


def video_section(content: str) -> str:
    if VIDEO_MARKER not in content or COLUMN_MARKER not in content:
        raise ValueError("台账缺少视频或专栏分隔标题")
    return content.split(VIDEO_MARKER, 1)[1].split(COLUMN_MARKER, 1)[0]


def parse_video_rows(content: str) -> list[dict[str, str]]:
    rows = []
    for line in video_section(content).splitlines():
        row = parse_row(line)
        if row:
            rows.append(row)
    return rows


def is_deleted(row: dict[str, str]) -> bool:
    blob = " ".join(row.values())
    return "已删除" in blob


def escape_markdown_cell(value: Any) -> str:
    return str(value if value is not None else "待同步").replace("|", "\\|").replace("\n", " ")


def format_video_row(record: dict[str, Any]) -> str:
    values = []
    for key in VIDEO_COLUMNS:
        value = escape_markdown_cell(record.get(key))
        if key in BACKTICK_FIELDS:
            value = f"`{value}`"
        values.append(value)
    return "| " + " | ".join(values) + " |"


def identities_of(record: dict[str, Any]) -> list[str]:
    values = []
    for key in IDENTITY_FIELDS:
        value = str(record.get(key) or "").strip()
        if value and value != "待同步":
            values.append(value)
    return values


def detect_local_duplicate(manifest: dict[str, Any], ledger_path: Path) -> None:
    if not ledger_path.exists():
        raise ValueError(f"B站发布台账不存在：{ledger_path}")
    ledger = ledger_path.read_text(encoding="utf-8")
    matches = []
    if manifest["sha256"] in ledger:
        matches.append("sha256")
    if manifest["video"] in ledger:
        matches.append("source_path")
    if matches:
        raise DuplicateDetected("本地台账已存在目标视频", {"matched_by": matches})


class DuplicateDetected(RuntimeError):
    def __init__(self, message: str, evidence: dict[str, Any] | None = None):
        super().__init__(message)
        self.evidence = evidence or {}


def append_video_ledger(record: dict[str, Any], ledger_path: Path) -> dict[str, Any]:
    if not ledger_path.exists():
        raise ValueError(f"B站发布台账不存在：{ledger_path}")
    lock_path = ledger_path.with_name(f".{ledger_path.name}.lock")
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        content = ledger_path.read_text(encoding="utf-8")
        matched = [value for value in identities_of(record) if f"`{value}`" in content]
        if matched:
            return {"written": False, "already_present": True, "matched": matched, "path": str(ledger_path)}
        if COLUMN_MARKER not in content:
            raise ValueError("B站台账缺少专栏分隔标题，拒绝猜测追加位置")
        before, after = content.split(COLUMN_MARKER, 1)
        atomic_write(ledger_path, before.rstrip() + "\n" + format_video_row(record) + "\n" + COLUMN_MARKER + after)
        return {"written": True, "already_present": False, "path": str(ledger_path)}


def _locked_content(ledger_path: Path):
    if not ledger_path.exists():
        raise ValueError(f"B站发布台账不存在：{ledger_path}")
    lock_path = ledger_path.with_name(f".{ledger_path.name}.lock")
    lock_file = lock_path.open("a+", encoding="utf-8")
    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
    return lock_file, ledger_path.read_text(encoding="utf-8")


def row_matches(row: dict[str, str], identity: dict[str, str]) -> bool:
    for key in IDENTITY_FIELDS:
        wanted = (identity.get(key) or "").strip()
        if wanted and wanted != "待同步" and row.get(key) == wanted:
            return True
    return False


def reconcile_video_row(ledger_path: Path, identity: dict[str, str], fields: dict[str, str]) -> dict[str, Any]:
    allowed = {"cid", "status", "aid", "bvid", "title"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"reconcile 不允许改这些字段: {sorted(unknown)}")
    if not any((identity.get(key) or "").strip() not in {"", "待同步"} for key in IDENTITY_FIELDS):
        raise ValueError("reconcile 需要 sha256、aid 或 bvid")
    lock_file, content = _locked_content(ledger_path)
    try:
        video_section(content)
        matches = []
        lines = content.splitlines(keepends=True)
        for index, line in enumerate(lines):
            if not line.startswith("|"):
                continue
            row = parse_row(line)
            if row and row_matches(row, identity) and not is_deleted(row):
                matches.append((index, row))
        if len(matches) != 1:
            raise ValueError(f"reconcile 必须命中唯一成功行，实际 {len(matches)}")
        index, row = matches[0]
        updated = dict(row)
        updated.update({key: value for key, value in fields.items() if value})
        newline = "\n" if lines[index].endswith("\n") else ""
        lines[index] = format_video_row(updated) + newline
        atomic_write(ledger_path, "".join(lines))
        return {"written": True, "path": str(ledger_path), "row": updated}
    finally:
        lock_file.close()


def record_exception(ledger_path: Path, record: dict[str, str]) -> dict[str, Any]:
    required = ("time", "series", "title", "phenomenon", "handling")
    missing = [key for key in required if not str(record.get(key) or "").strip()]
    if missing:
        raise ValueError(f"异常记录缺字段: {missing}")
    lock_file, content = _locked_content(ledger_path)
    try:
        if EXCEPTION_MARKER not in content:
            raise ValueError("台账缺少删除/异常记录标题")
        row = "| " + " | ".join(escape_markdown_cell(record[key]) for key in required) + " |"
        if not content.endswith("\n"):
            content += "\n"
        atomic_write(ledger_path, content + row + "\n")
        return {"written": True, "path": str(ledger_path)}
    finally:
        lock_file.close()


def validate_ledger(ledger_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    if not ledger_path.is_file():
        return {"valid": False, "errors": [f"台账不存在: {ledger_path}"]}
    content = ledger_path.read_text(encoding="utf-8")
    for marker in (VIDEO_MARKER, COLUMN_MARKER, EXCEPTION_MARKER):
        if marker not in content:
            errors.append(f"缺少 {marker}")
    if errors:
        return {"valid": False, "errors": errors, "warnings": [], "videos": 0, "pending": 0}
    seen: dict[str, str] = {}
    warnings: list[str] = []
    rows = parse_video_rows(content)
    pending = 0
    for row in rows:
        if is_deleted(row):
            continue
        for key in IDENTITY_FIELDS:
            value = row.get(key) or ""
            if not value or value == "待同步":
                continue
            owner = f"{key}:{value}"
            if owner in seen:
                message = f"重复 {key} `{value}`"
                if key == "sha256":
                    warnings.append(message)
                else:
                    errors.append(message)
            seen[owner] = row["title"]
        if any("待同步" in (row.get(key) or "") for key in ("aid", "bvid", "cid", "status")):
            pending += 1
    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "videos": len(rows),
        "pending": pending,
        "path": str(ledger_path),
    }


def status_report(ledger_path: Path) -> dict[str, Any]:
    report = validate_ledger(ledger_path)
    if not ledger_path.is_file():
        return report
    rows = parse_video_rows(ledger_path.read_text(encoding="utf-8"))
    pending_rows = [
        {
            "published_at": row["published_at"],
            "title": row["title"],
            "sha256": row["sha256"],
            "aid": row["aid"],
            "bvid": row["bvid"],
            "cid": row["cid"],
            "status": row["status"],
        }
        for row in rows
        if "待同步" in row.get("cid", "") or "待同步" in row.get("aid", "") or "待同步" in row.get("status", "")
    ]
    report["latest"] = rows[-1]["title"] if rows else None
    report["pending_rows"] = pending_rows
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)
    configure_cmd = sub.add_parser("configure")
    configure_cmd.add_argument("--project-root", required=True)
    configure_cmd.add_argument("--ledger-path")
    configure_cmd.add_argument("--log-root")
    configure_cmd.add_argument("--staging-root")
    configure_cmd.add_argument("--upload-copy-dir")
    sub.add_parser("status")
    sub.add_parser("validate")
    reconcile_cmd = sub.add_parser("reconcile")
    reconcile_cmd.add_argument("--sha256")
    reconcile_cmd.add_argument("--aid")
    reconcile_cmd.add_argument("--bvid")
    reconcile_cmd.add_argument("--cid")
    reconcile_cmd.add_argument("--status")
    reconcile_cmd.add_argument("--title")
    exception_cmd = sub.add_parser("record-exception")
    exception_cmd.add_argument("--time", required=True)
    exception_cmd.add_argument("--series", required=True)
    exception_cmd.add_argument("--title", required=True)
    exception_cmd.add_argument("--phenomenon", required=True)
    exception_cmd.add_argument("--handling", required=True)
    args = parser.parse_args(argv)
    config = args.config.expanduser()
    if args.command == "configure":
        result = configure(
            config,
            Path(args.project_root),
            ledger_path=args.ledger_path,
            log_root=args.log_root,
            staging_root=args.staging_root,
            upload_copy_dir=args.upload_copy_dir,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    workspace = load_workspace(config)
    if args.command == "validate":
        report = validate_ledger(workspace.ledger_path)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["valid"] else 2
    if args.command == "status":
        report = status_report(workspace.ledger_path)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report.get("valid", True) else 2
    if args.command == "reconcile":
        identity = {"sha256": args.sha256, "aid": args.aid, "bvid": args.bvid}
        fields = {key: getattr(args, key) for key in ("cid", "status", "aid", "bvid", "title") if getattr(args, key)}
        result = reconcile_video_row(workspace.ledger_path, identity, fields)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if args.command == "record-exception":
        result = record_exception(
            workspace.ledger_path,
            {
                "time": args.time,
                "series": args.series,
                "title": args.title,
                "phenomenon": args.phenomenon,
                "handling": args.handling,
            },
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    raise ValueError(f"未知命令: {args.command}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, KeyError, TypeError, DuplicateDetected) as exc:
        print(f"台账操作失败: {exc}", file=sys.stderr)
        raise SystemExit(2)
