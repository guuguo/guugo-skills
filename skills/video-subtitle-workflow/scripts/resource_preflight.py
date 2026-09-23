#!/usr/bin/env python3
"""在字幕重任务前检查内存压力、并发进程和临时磁盘容量。"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


GIB = 1024 ** 3


def run_text(command: list[str]) -> str:
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


def probe_video(video: Path) -> dict[str, float | int]:
    output = run_text([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height:format=duration,size",
        "-of", "json", str(video),
    ])
    data = json.loads(output)
    stream = data["streams"][0]
    container = data["format"]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration": float(container["duration"]),
        "size": int(container.get("size") or video.stat().st_size),
    }


def memory_snapshot() -> dict[str, int | float | None]:
    if sys.platform == "darwin":
        total = int(run_text(["sysctl", "-n", "hw.memsize"]).strip())
        pressure = run_text(["memory_pressure", "-Q"])
        match = re.search(r"free percentage:\s*(\d+)%", pressure)
        free_percent = float(match.group(1)) if match else None
        available = int(total * free_percent / 100) if free_percent is not None else None
        return {"total_bytes": total, "available_bytes": available, "free_percent": free_percent}

    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        values: dict[str, int] = {}
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            key, value = line.split(":", 1)
            values[key] = int(value.strip().split()[0]) * 1024
        total = values.get("MemTotal")
        available = values.get("MemAvailable")
        free_percent = available / total * 100 if total and available is not None else None
        return {"total_bytes": total, "available_bytes": available, "free_percent": free_percent}

    return {"total_bytes": None, "available_bytes": None, "free_percent": None}


def existing_heavy_workers() -> list[dict[str, Any]]:
    try:
        output = run_text(["ps", "-axo", "pid=,rss=,command="])
    except (OSError, subprocess.CalledProcessError):
        return []
    pattern = re.compile(r"(?:^|[/\s])(ffmpeg|macos_vision_ocr\.swift|mlx_whisper)(?:\s|$)")
    workers = []
    for line in output.splitlines():
        parts = line.strip().split(maxsplit=2)
        if len(parts) != 3:
            continue
        pid, rss_kib, command = parts
        if int(pid) == os.getpid() or not pattern.search(command):
            continue
        workers.append({"pid": int(pid), "rss_bytes": int(rss_kib) * 1024, "command": command})
    return workers


def nearest_existing_directory(path: Path) -> Path:
    candidate = path.resolve()
    while not candidate.exists():
        if candidate.parent == candidate:
            raise FileNotFoundError(f"找不到可检查磁盘的父目录: {path}")
        candidate = candidate.parent
    return candidate if candidate.is_dir() else candidate.parent


def gib(value: int | float | None) -> float | None:
    return round(value / GIB, 2) if value is not None else None


def assess(video: Path, work_dir: Path, scan_fps: float, parallel_jobs: int) -> dict[str, Any]:
    if scan_fps <= 0:
        raise ValueError("scan-fps 必须大于 0")
    if parallel_jobs <= 0:
        raise ValueError("parallel-jobs 必须大于 0")

    metadata = probe_video(video)
    memory = memory_snapshot()
    workers = existing_heavy_workers()
    disk_path = nearest_existing_directory(work_dir)
    disk_free = shutil.disk_usage(disk_path).free

    width = int(metadata["width"])
    height = int(metadata["height"])
    duration = float(metadata["duration"])
    source_size = int(metadata["size"])
    frame_count = math.ceil(duration * scan_fps)
    raw_frame_bytes = width * height * 4

    # PNG 大小依画面内容而变；用未压缩 RGBA 上界做保守磁盘预算。
    frame_disk_budget = int(frame_count * raw_frame_bytes * 1.05)
    disk_required = frame_disk_budget + int(source_size * 1.5) + 512 * 1024 ** 2

    # 各阶段串行执行。估算只用于阻止明显危险的启动，不作为精确 RSS 承诺。
    asr_peak = 3 * GIB
    ocr_peak = max(1 * GIB, raw_frame_bytes * 32)
    render_peak = max(1 * GIB, raw_frame_bytes * 24)
    stage_peak = max(asr_peak, ocr_peak, render_peak) * parallel_jobs
    total_memory = memory["total_bytes"]
    reserve = max(2 * GIB, int(total_memory * 0.10)) if total_memory else 4 * GIB
    memory_required = stage_peak + reserve

    blockers: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []
    available = memory["available_bytes"]
    free_percent = memory["free_percent"]

    if available is None or free_percent is None:
        blockers.append("无法读取系统可用内存和内存压力")
    else:
        if free_percent < 15:
            blockers.append(f"系统可用内存仅 {free_percent:.0f}%，低于 15% 启动门禁")
        if available < memory_required:
            blockers.append(
                f"可用内存约 {gib(available)} GiB，低于估算峰值加系统保留量 {gib(memory_required)} GiB"
            )
        elif free_percent < 30 or available < memory_required * 1.35:
            warnings.append("内存余量有限，必须保持单任务串行并在每个重阶段前重新预检")

    if disk_free < disk_required:
        blockers.append(
            f"工作盘可用空间约 {gib(disk_free)} GiB，低于保守临时空间预算 {gib(disk_required)} GiB"
        )

    cpu_count = os.cpu_count() or 1
    try:
        load_1m = os.getloadavg()[0]
    except OSError:
        load_1m = None
    if load_1m is not None and load_1m > cpu_count * 1.25:
        warnings.append(f"1 分钟负载 {load_1m:.1f} 高于 {cpu_count} 核的 125%")

    if workers:
        blockers.append(f"检测到 {len(workers)} 个 ffmpeg、Vision OCR 或 MLX Whisper 重任务仍在运行")
        recommendations.append("等待现有重任务结束后重新预检，不并行跑多个字幕任务")

    if parallel_jobs > 1:
        warnings.append(f"parallel-jobs={parallel_jobs} 会按任务数放大峰值内存")
        recommendations.append("字幕 ASR、OCR、渲染和验收默认 parallel-jobs=1")

    if blockers:
        status = "block"
        recommendations.append("先释放内存、结束重任务或换到空间更充足的工作盘，然后重新运行预检")
    elif warnings:
        status = "caution"
        recommendations.append("一次只处理一个视频；进入 ASR、scan、render、verify 前分别重新预检")
    else:
        status = "ok"
        recommendations.append("资源余量允许启动一个字幕重阶段；阶段之间仍保持串行")

    return {
        "status": status,
        "video": str(video),
        "work_dir_disk": str(disk_path),
        "video_metadata": {
            **metadata,
            "scan_fps": scan_fps,
            "estimated_scan_frames": frame_count,
            "raw_rgba_frame_mib": round(raw_frame_bytes / 1024 ** 2, 2),
        },
        "memory": {
            "total_gib": gib(total_memory),
            "available_gib": gib(available),
            "free_percent": free_percent,
            "estimated_stage_peak_gib": gib(stage_peak),
            "system_reserve_gib": gib(reserve),
            "required_before_start_gib": gib(memory_required),
        },
        "disk": {
            "free_gib": gib(disk_free),
            "estimated_png_budget_gib": gib(frame_disk_budget),
            "required_gib": gib(disk_required),
        },
        "cpu": {"logical_cores": cpu_count, "load_1m": load_1m},
        "existing_heavy_workers": workers,
        "blockers": blockers,
        "warnings": warnings,
        "recommendations": recommendations,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--scan-fps", type=float, default=5.0)
    parser.add_argument("--parallel-jobs", type=int, default=1)
    parser.add_argument("--json", action="store_true", help="输出完整 JSON 报告")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        report = assess(args.video.resolve(), args.work_dir, args.scan_fps, args.parallel_jobs)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"资源预检失败: {error}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"资源预检: {report['status']}")
        memory = report["memory"]
        disk = report["disk"]
        print(
            f"内存: 可用 {memory['available_gib']} GiB / {memory['total_gib']} GiB；"
            f"启动要求 {memory['required_before_start_gib']} GiB"
        )
        print(f"磁盘: 可用 {disk['free_gib']} GiB；保守要求 {disk['required_gib']} GiB")
        for label in ("blockers", "warnings", "recommendations"):
            for item in report[label]:
                print(f"{label}: {item}")
    return 2 if report["status"] == "block" else 0


if __name__ == "__main__":
    raise SystemExit(main())
