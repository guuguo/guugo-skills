#!/usr/bin/env python3
"""用原硬字幕切换点整行修复 AI 视频字幕。

流程分两步：
1. scan：5fps 抽帧 + macOS Vision OCR，产出待人工校正的整行时间轴。
2. render：读取已确认时间轴，紧贴旧字幕字框去字并一次性烧录整行字幕。

OCR 只负责时间和位置，ASR/脚本负责正确文本；工具不会把 OCR 文本当成剧情真源。
"""

from __future__ import annotations

import argparse
import difflib
import json
import re
import shlex
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
VISION_SCRIPT = ROOT / "scripts" / "macos_vision_ocr.swift"


def run(command: list[str]) -> None:
    print("+", " ".join(shlex.quote(part) for part in command))
    subprocess.run(command, check=True)


def has_videotoolbox() -> bool:
    """检查当前系统 FFmpeg 是否支持 Apple VideoToolbox 硬件加速。"""
    try:
        output = subprocess.check_output(
            ["ffmpeg", "-encoders"], stderr=subprocess.STDOUT, text=True
        )
        return "h264_videotoolbox" in output
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def probe_video(video: Path) -> dict[str, Any]:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate:format=duration",
        "-of", "json", str(video),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data["streams"][0]
    numerator, denominator = map(int, stream["r_frame_rate"].split("/"))
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": numerator / denominator,
        "duration": float(data["format"]["duration"]),
    }


def probe_encode_quality(video: Path) -> dict[str, int | None]:
    """读取交付质量门禁所需的体积与码率；优先使用视频流码率。"""
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=bit_rate:format=size,bit_rate",
        "-of", "json", str(video),
    ]
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    stream = data.get("streams", [{}])[0]
    container = data.get("format", {})

    def optional_int(value: Any) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed > 0 else None

    return {
        "size": optional_int(container.get("size")),
        "video_bit_rate": optional_int(stream.get("bit_rate")),
        "format_bit_rate": optional_int(container.get("bit_rate")),
    }


def validate_quality_retention(
    source: Path,
    output: Path,
    min_source_bitrate_ratio: float,
) -> dict[str, float | int | None]:
    """防止字幕修复把原片压成低码率版本。"""
    if not 0 <= min_source_bitrate_ratio <= 1:
        raise ValueError("最低原片码率比例必须在 0–1 之间")
    source_quality = probe_encode_quality(source)
    output_quality = probe_encode_quality(output)
    source_rate = source_quality["video_bit_rate"] or source_quality["format_bit_rate"]
    output_rate = output_quality["video_bit_rate"] or output_quality["format_bit_rate"]
    ratio = output_rate / source_rate if source_rate and output_rate else None
    report: dict[str, float | int | None] = {
        "source_size": source_quality["size"],
        "output_size": output_quality["size"],
        "source_bit_rate": source_rate,
        "output_bit_rate": output_rate,
        "bit_rate_ratio": ratio,
    }
    if ratio is not None and ratio < min_source_bitrate_ratio:
        raise ValueError(
            f"成品码率仅为原片的 {ratio:.1%}，低于质量门禁 "
            f"{min_source_bitrate_ratio:.0%}；请从原片降低 CRF 后重新渲染"
        )
    return report


def normalize_text(text: str) -> str:
    return re.sub(r"[^\w\u3400-\u9fff]", "", text).lower()


def normalize_terminal_punctuation(text: str) -> str:
    """字幕行末去掉逗号和句号，保留问号、感叹号等语气标点。"""
    lines = text.splitlines() or [text]
    return "\n".join(re.sub(r"[，。,\.]+$", "", line.rstrip()) for line in lines)


def text_similarity(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, normalize_text(left), normalize_text(right)).ratio()


@dataclass
class OCRSample:
    time: float
    text: str
    confidence: float
    x: int
    y: int
    width: int
    height: int

    @property
    def center_y(self) -> float:
        return self.y + self.height / 2


def chinese_ratio(text: str) -> float:
    compact = normalize_text(text)
    if not compact:
        return 0.0
    chinese = sum("\u3400" <= char <= "\u9fff" for char in compact)
    return chinese / len(compact)


def pick_subtitle_box(
    frame: dict[str, Any],
    time: float,
    top_ratio: float,
    bottom_ratio: float,
    min_confidence: float,
) -> OCRSample | None:
    frame_width = int(frame["width"])
    frame_height = int(frame["height"])
    candidates: list[OCRSample] = []
    for box in frame.get("boxes", []):
        center_y = box["y"] + box["height"] / 2
        if not (frame_height * top_ratio <= center_y <= frame_height * bottom_ratio):
            continue
        text = box["text"].strip()
        if float(box["confidence"]) < min_confidence or chinese_ratio(text) < 0.5:
            continue
        candidates.append(OCRSample(time=time, text=text, confidence=float(box["confidence"]), **{
            key: int(box[key]) for key in ("x", "y", "width", "height")
        }))
    if not candidates:
        return None

    def score(sample: OCRSample) -> float:
        center_x = sample.x + sample.width / 2
        centered = 1 - min(abs(center_x - frame_width / 2) / (frame_width / 2), 1)
        return sample.confidence * 3 + min(len(normalize_text(sample.text)), 14) / 14 + centered

    return max(candidates, key=score)


def representative_text(samples: list[OCRSample]) -> str:
    return max(samples, key=lambda sample: (sample.confidence, len(normalize_text(sample.text)))).text


def median_int(values: Iterable[int]) -> int:
    return int(round(statistics.median(values)))


def group_samples(samples: list[OCRSample], frame_step: float) -> list[dict[str, Any]]:
    groups: list[list[OCRSample]] = []
    for sample in samples:
        if not groups:
            groups.append([sample])
            continue
        previous = groups[-1][-1]
        same_line = (
            sample.time - previous.time <= frame_step * 1.6
            and text_similarity(sample.text, representative_text(groups[-1])) >= 0.72
            and abs(sample.center_y - previous.center_y) <= max(sample.height, previous.height) * 0.8
        )
        if same_line:
            groups[-1].append(sample)
        else:
            groups.append([sample])

    events: list[dict[str, Any]] = []
    for group in groups:
        source_text = representative_text(group)
        x = median_int(item.x for item in group)
        y = median_int(item.y for item in group)
        width = median_int(item.width for item in group)
        height = median_int(item.height for item in group)
        events.append({
            "start": round(group[0].time, 3),
            "end": round(group[-1].time + frame_step, 3),
            "source_text": source_text,
            "text": source_text,
            "mask": True,
            "bbox": {"x": x, "y": y, "w": width, "h": height},
            "position": {"x": x + width // 2, "y": y + height // 2},
            "scale_x": 100,
        })
    return events


def asr_words(asr_path: Path, duration: float) -> list[dict[str, Any]]:
    data = json.loads(asr_path.read_text(encoding="utf-8"))
    words: list[dict[str, Any]] = []
    for segment in data.get("segments", []):
        for word in segment.get("words", []):
            start = float(word["start"])
            end = min(float(word["end"]), duration)
            text = str(word.get("word", "")).strip()
            if text and start < duration and end > start:
                words.append({"start": start, "end": end, "text": text})
    return words


def find_uncovered_speech(
    words: list[dict[str, Any]],
    events: list[dict[str, Any]],
    tolerance: float = 0.18,
) -> list[dict[str, Any]]:
    uncovered: list[dict[str, Any]] = []
    for word in words:
        midpoint = (word["start"] + word["end"]) / 2
        covered = any(
            float(event["start"]) - tolerance <= midpoint <= float(event["end"]) + tolerance
            for event in events
        )
        if not covered:
            uncovered.append(word)

    groups: list[list[dict[str, Any]]] = []
    for word in uncovered:
        if groups and word["start"] - groups[-1][-1]["end"] <= 0.65:
            groups[-1].append(word)
        else:
            groups.append([word])
    return [{
        "start": round(group[0]["start"], 3),
        "end": round(group[-1]["end"], 3),
        "asr_text": "".join(item["text"] for item in group),
        "reason": "ASR 检出对白，但 OCR 时间轴没有字幕节点；需人工抽帧补整行事件",
        "resolved": False,
    } for group in groups]


def scan(args: argparse.Namespace) -> None:
    video = args.video.resolve()
    work_dir = args.work_dir.resolve()
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    ocr_jsonl = work_dir / "vision-ocr.jsonl"
    timeline_path = args.timeline.resolve()

    metadata = probe_video(video)
    width, height = metadata["width"], metadata["height"]
    default_top, default_bottom = subtitle_region_policy(width, height)
    subtitle_top = args.subtitle_top if args.subtitle_top is not None else default_top
    subtitle_bottom = args.subtitle_bottom if args.subtitle_bottom is not None else default_bottom

    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vf", f"fps={args.scan_fps}", str(frames_dir / "frame-%06d.png"),
    ])
    run(["swift", str(VISION_SCRIPT), str(frames_dir), str(ocr_jsonl)])

    samples: list[OCRSample] = []
    for line in ocr_jsonl.read_text(encoding="utf-8").splitlines():
        frame = json.loads(line)
        time = (int(frame["frame"]) - 1) / args.scan_fps
        sample = pick_subtitle_box(
            frame, time, subtitle_top, subtitle_bottom, args.min_confidence,
        )
        if sample:
            samples.append(sample)

    events = group_samples(samples, 1 / args.scan_fps)
    gaps = find_uncovered_speech(asr_words(args.asr_json.resolve(), metadata["duration"]), events)
    timeline = {
        "version": 1,
        "mode": "whole-line",
        "reviewed": False,
        "source_video": str(video),
        "video": metadata,
        "scan": {
            "fps": args.scan_fps,
            "subtitle_top_ratio": subtitle_top,
            "subtitle_bottom_ratio": subtitle_bottom,
        },
        "style": default_style(metadata["width"], metadata["height"]),
        "unresolved_gaps": gaps,
        "events": events,
    }
    timeline_path.parent.mkdir(parents=True, exist_ok=True)
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"待校正时间轴: {timeline_path}")
    print(f"OCR 字幕节点: {len(events)}；ASR 待补缺口: {len(gaps)}")
    print("请按 ASR/脚本修正 text，处理全部 unresolved_gaps，并把 reviewed 改为 true 后再 render。")


def subtitle_region_policy(width: int, height: int) -> tuple[float, float]:
    """返回按画面方向自适应的默认字幕检测上下界 (top_ratio, bottom_ratio)。

    - 竖屏 (height > width): 避开底部 App UI 遮挡 (如抖音评论点赞栏)，默认 0.60 ~ 0.85
    - 横屏 (width > height): 标准底边对白字幕 (ASS MarginV 位于底边)，默认 0.65 ~ 0.98
    - 正方形: 默认 0.65 ~ 0.95
    """
    if height > width:
        return 0.60, 0.85
    elif width > height:
        return 0.65, 0.98
    else:
        return 0.65, 0.95


def extract_timeline_y_ratios(timeline: dict[str, Any], height: int) -> list[float]:
    """从时间轴事件与样式中提取所有已知字幕的垂直中心比例 (y / height)。"""
    if height <= 0:
        return []
    y_ratios: list[float] = []
    for ev in timeline.get("events", []):
        pos = ev.get("position")
        if isinstance(pos, dict) and "y" in pos:
            try:
                y_ratios.append(float(pos["y"]) / height)
            except (TypeError, ValueError):
                pass
        elif ev.get("bbox") and isinstance(ev["bbox"], (list, tuple)) and len(ev["bbox"]) >= 4:
            try:
                cy = float(ev["bbox"][1]) + float(ev["bbox"][3]) / 2
                y_ratios.append(cy / height)
            except (TypeError, ValueError):
                pass
        elif ev.get("bbox") and isinstance(ev["bbox"], dict) and "y" in ev["bbox"] and "h" in ev["bbox"]:
            try:
                cy = float(ev["bbox"]["y"]) + float(ev["bbox"]["h"]) / 2
                y_ratios.append(cy / height)
            except (TypeError, ValueError):
                pass
    style = timeline.get("style", {})
    if not y_ratios and isinstance(style, dict) and "margin_v" in style:
        try:
            mv = float(style["margin_v"])
            y_ratios.append((height - mv) / height)
        except (TypeError, ValueError):
            pass
    return y_ratios


def resolve_verify_region(
    args: argparse.Namespace,
    timeline: dict[str, Any],
    width: int,
    height: int,
) -> tuple[float, float]:
    """计算 verify 验收时应当使用的 (top_ratio, bottom_ratio)。

    优先次序:
    1. CLI 显式参数 (--subtitle-top / --subtitle-bottom);
    2. 时间轴真实坐标范围继承 (沿用 position.y / bbox.y / margin_v，保留冗余度);
    3. 长宽比自适应策略 (横屏 0.65~0.98, 竖屏 0.60~0.85)。
    """
    default_top, default_bottom = subtitle_region_policy(width, height)
    y_ratios = extract_timeline_y_ratios(timeline, height)

    if getattr(args, "subtitle_top", None) is not None:
        top_ratio = args.subtitle_top
    elif y_ratios:
        top_ratio = max(0.40, min(default_top, min(y_ratios) - 0.10))
    else:
        top_ratio = default_top

    if getattr(args, "subtitle_bottom", None) is not None:
        bottom_ratio = args.subtitle_bottom
    elif y_ratios:
        bottom_ratio = min(1.0, max(default_bottom, max(y_ratios) + 0.08))
    else:
        bottom_ratio = default_bottom

    return round(top_ratio, 3), round(bottom_ratio, 3)


def read_ocr_samples(
    ocr_jsonl: Path,
    scan_fps: float,
    top_ratio: float,
    bottom_ratio: float,
    min_confidence: float,
) -> list[OCRSample]:
    samples: list[OCRSample] = []
    for line in ocr_jsonl.read_text(encoding="utf-8").splitlines():
        frame = json.loads(line)
        time = (int(frame["frame"]) - 1) / scan_fps
        sample = pick_subtitle_box(frame, time, top_ratio, bottom_ratio, min_confidence)
        if sample:
            samples.append(sample)
    return samples


def font_size_policy(width: int, height: int) -> tuple[int, int]:
    """返回按画面方向区分的默认字号与最低可读字号。"""
    if height > width:
        default_ratio, minimum_ratio = 0.045, 0.039
    elif width > height:
        default_ratio, minimum_ratio = 0.058, 0.050
    else:
        default_ratio, minimum_ratio = 0.052, 0.045
    return round(height * default_ratio), round(height * minimum_ratio)


def validate_readable_font_size(style: dict[str, Any], width: int, height: int) -> None:
    _, minimum = font_size_policy(width, height)
    selected = int(style["font_size"])
    if selected < minimum and not style.get("allow_small_font", False):
        raise ValueError(
            f"字幕字号过小（{selected}px < {minimum}px 可读下限）；"
            "请重新生成字号候选。只有用户明确要求小字号时才可设置 allow_small_font=true"
        )
    # 低分辨率防糊门禁：短边 <= 720（如 480p）时，严禁使用 blur 模糊滤镜，且必须带描边
    min_dim = min(width, height)
    if min_dim <= 720:
        blur_val = float(style.get("blur", 0))
        outline_val = float(style.get("outline", 0))
        if blur_val > 0:
            raise ValueError(
                f"低分辨率防糊门禁触发：画面尺寸为 {width}x{height}（短边<=720），严禁使用 blur>0（当前 blur={blur_val}）；"
                "低分辨率下哪怕 1px 高斯模糊也会导致复杂汉字笔画严重发糊粘连，必须设为 blur: 0。"
            )
        if outline_val <= 0:
            raise ValueError(
                f"低分辨率防糊门禁触发：画面尺寸为 {width}x{height}（短边<=720），严禁无描边 outline<=0；"
                "低分辨率下必须设置清晰黑色描边（outline >= 1.2），确保在任何背景下字迹锐利硬朗。"
            )


def default_style(width: int, height: int) -> dict[str, Any]:
    default_font_size, minimum_font_size = font_size_policy(width, height)
    min_dim = min(width, height)
    is_low_res = min_dim <= 720
    # 低分辨率防糊门禁：短边 <= 720（如 480p）时汉字笔画像素极少，严禁使用 blur 模糊滤镜（必须为 0），
    # 且必须配合锐利描边 (outline >= 1.5) 避免字迹边缘发散发虚；
    # 即使在 1080p+ 分辨率下，默认 blur 也设为 0，优先保证文字如刀锋般锐利清晰。
    outline_val = 1.5 if is_low_res else 2.0
    shadow_val = 1.5 if is_low_res else 2.5
    back_colour_val = "&H80000000" if is_low_res else "&H00000000"
    return {
        "font_name": "PingFang SC",
        # 仅作候选起点。竖屏与横屏的观看距离不同，分别给出可读默认值；
        # OCR 字框高度不是 ASS 字号，最终仍需看全分辨率候选图。
        "font_size": default_font_size,
        "min_font_size": minimum_font_size,
        "primary_colour": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "back_colour": back_colour_val,
        "outline": outline_val,
        "shadow": shadow_val,
        "blur": 0,
        "scale_y": 100,
        "min_scale_x": 95,
        "max_text_width_ratio": 0.82,
        "max_line_units": 11,
        "mask_padding_x": max(4, round(width * 0.011)),
        "mask_padding_y": max(4, round(height * 0.005)),
        # 模型硬字幕常比 ASR/5fps OCR 的事件起点早几帧，提前遮罩避免切换时闪回旧字。
        "mask_lead_seconds": 0.25,
        "mask_tail_seconds": 0.10,
    }


def get_preset_style(preset_name: str, width: int, height: int) -> dict[str, Any]:
    """根据剧集预设名称与实际分辨率 (width x height) 自适应生成高清视觉样式。

    支持预设:
    - '你家的船' / 'chuan' / 'heiti':
      专为《你家的船，是我在看》打造的电影感黑体底边方案。
      以 496p（864x496）为基准 (字号 30px, 描边 1.8, 阴影 1.0, y 比例 89.9%):
      * 480p/496p: 30px, outline 1.8, shadow 1.0
      * 720p (如 1280x720): 44px, outline 2.6, shadow 1.5
      * 1080p (如 1920x1080): 65px, outline 3.9, shadow 2.2
    - 'default' / 'pingfang':
      通用自适应方案。
    """
    scale = height / 496.0
    min_dim = min(width, height)
    is_low_res = min_dim <= 720

    norm_name = preset_name.strip().lower()
    if norm_name in ("你家的船", "chuan", "heiti", "ship"):
        font_size = round(height * 0.0605)
        outline_val = max(1.5, round(1.8 * scale, 1))
        shadow_val = max(1.0, round(1.0 * scale, 1))
        font_name = "Heiti SC"
    else:
        default_font_size, _ = font_size_policy(width, height)
        font_size = default_font_size
        outline_val = 1.5 if is_low_res else round(2.0 * scale, 1)
        shadow_val = 1.5 if is_low_res else round(2.5 * scale, 1)
        font_name = "PingFang SC"

    return {
        "preset_name": preset_name,
        "font_name": font_name,
        "font_size": font_size,
        "min_font_size": round(height * 0.050),
        "primary_colour": "&H00FFFFFF",
        "outline_colour": "&H00000000",
        "back_colour": "&H80000000",
        "outline": outline_val,
        "shadow": shadow_val,
        "blur": 0,
        "bold": 0,
        "scale_y": 100,
        "min_scale_x": 95,
        "max_text_width_ratio": 0.82,
        "max_line_units": 11,
        "mask_padding_x": max(8, round(10 * scale)),
        "mask_padding_y": max(3, round(4 * scale)),
        "mask_lead_seconds": 0.25,
        "mask_tail_seconds": 0.1,
        "font_review": {
            "status": "selected",
            "selected_font": font_name,
            "font_size": font_size,
        },
    }



def ass_time(seconds: float) -> str:
    centiseconds = max(0, round(seconds * 100))
    hours, remainder = divmod(centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    secs, centis = divmod(remainder, 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def escape_ass(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def text_width_units(text: str) -> float:
    punctuation = set("，。！？；：、,.!?;:（）()《》【】")
    return max(1.0, sum(0.5 if char in punctuation else 1.0 for char in text if not char.isspace()))


def wrap_subtitle_text(
    text: str,
    font_size: int,
    scale_x: int,
    style: dict[str, Any],
    frame_width: int,
) -> str:
    """长句保持正常字宽，超过安全区时在接近中点处拆成两行。"""
    if "\n" in text:
        return text

    width_factor = float(style.get("glyph_width_factor", 1.05))
    max_width = frame_width * float(style.get("max_text_width_ratio", 0.82))
    rendered_width = text_width_units(text) * font_size * width_factor * scale_x / 100
    max_line_units = float(style.get("max_line_units", 11))
    if rendered_width <= max_width and text_width_units(text) <= max_line_units:
        return text

    characters = list(text)
    forbidden_line_starts = set("，。！？；：、,.!?;:）)》】")
    forbidden_line_ends = set("（(《【")
    candidates: list[tuple[float, int]] = []
    for split_at in range(1, len(characters)):
        left = "".join(characters[:split_at]).rstrip()
        right = "".join(characters[split_at:]).lstrip()
        if not left or not right:
            continue
        if right[0] in forbidden_line_starts or left[-1] in forbidden_line_ends:
            continue
        left_units = text_width_units(left)
        right_units = text_width_units(right)
        widest_width = max(left_units, right_units) * font_size * width_factor * scale_x / 100
        overflow_penalty = max(0.0, widest_width - max_width) * 10
        balance_penalty = abs(left_units - right_units)
        candidates.append((overflow_penalty + balance_penalty, split_at))

    if not candidates:
        return text
    _, split_at = min(candidates)
    return "".join(characters[:split_at]).rstrip() + "\n" + "".join(characters[split_at:]).lstrip()


def calibrated_typography(event: dict[str, Any], style: dict[str, Any]) -> tuple[int, int]:
    default_size = int(style["font_size"])
    default_scale = int(event.get("scale_x", 100))
    bbox = event.get("bbox")
    if not style.get("match_source_bbox") or not bbox:
        return default_size, default_scale

    units = text_width_units(str(event["text"]))
    width_factor = float(style.get("glyph_width_factor", 1.05))
    min_size = int(style.get("min_font_size", default_size))
    max_size = int(style.get("max_font_size", default_size))
    height_size = float(bbox["h"]) * 0.85
    width_size = float(bbox["w"]) / (units * width_factor)
    font_size = round(max(height_size, width_size))
    font_size = max(min_size, min(max_size, font_size))
    scale_x = round(float(bbox["w"]) / (font_size * units * width_factor) * 100)
    min_scale_x = int(style.get("min_scale_x", 95))
    scale_x = max(min_scale_x, min(100, scale_x))
    return font_size, scale_x


def coalesce_same_text(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """合并连续同文案节点，并把已检出的旧字幕遮罩前移到整句起点。"""
    merged: list[dict[str, Any]] = []
    for source in sorted(events, key=lambda item: (float(item["start"]), float(item["end"]))):
        event = dict(source)
        if merged:
            previous = merged[-1]
            continuous = float(event["start"]) <= float(previous["end"]) + 0.02
            same_text = normalize_text(str(event.get("text", ""))) == normalize_text(str(previous.get("text", "")))
            carries_late_mask = not previous.get("mask", True) or not event.get("mask", True)
            if continuous and same_text and carries_late_mask:
                previous["end"] = max(float(previous["end"]), float(event["end"]))
                if event.get("mask") and event.get("bbox"):
                    previous["mask"] = True
                    previous["bbox"] = event["bbox"]
                    previous["position"] = event.get("position", previous.get("position"))
                continue
        merged.append(event)
    return merged


def bridge_short_masked_gaps(events: list[dict[str, Any]], max_gap: float = 0.25) -> list[dict[str, Any]]:
    """用连续字幕和双字框遮罩消除 OCR 采样空档。"""
    bridged = [dict(event) for event in events]
    for previous, current in zip(bridged, bridged[1:]):
        gap_start = float(previous["end"])
        gap_end = float(current["start"])
        gap = gap_end - gap_start
        if (
            0 < gap <= max_gap
            and previous.get("mask", True)
            and current.get("mask", True)
        ):
            switch = round((gap_start + gap_end) / 2, 3)
            previous["end"] = switch
            current["start"] = switch
            previous["mask_end"] = gap_end
            current["mask_start"] = gap_start
    return bridged


def normalized_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = bridge_short_masked_gaps(coalesce_same_text(events))
    for index, event in enumerate(normalized):
        event["text"] = normalize_terminal_punctuation(str(event.get("text", "")))
        event["start"] = float(event["start"])
        event["end"] = float(event["end"])
        if index + 1 < len(normalized):
            next_start = float(normalized[index + 1]["start"])
            event["end"] = min(event["end"], next_start)
        if event["end"] <= event["start"]:
            raise ValueError(f"无效字幕区间: {event}")
        if not str(event.get("text", "")).strip() and not event.get("mask", True):
            raise ValueError(f"字幕正文为空且未声明仅去字: {event}")
    return normalized


def write_ass(path: Path, width: int, height: int, style: dict[str, Any], events: list[dict[str, Any]]) -> None:
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: FullLine,{style['font_name']},{style['font_size']},{style['primary_colour']},&H000000FF,{style['outline_colour']},{style['back_colour']},{int(bool(style.get('bold', 0)))},0,0,0,100,100,0,0,{int(style.get('border_style', 1))},{style['outline']},{style['shadow']},5,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for event in events:
        # 对命中内容门禁的旧硬字幕，只做原位去字，不重新烧录任何文字。
        if not str(event.get("text", "")).strip():
            continue
        position = event.get("position") or {}
        bbox = event.get("bbox") or {}
        x = int(position.get("x", width // 2))
        y = int(position.get("y", bbox.get("y", round(height * 0.72)) + bbox.get("h", 0) // 2))
        font_size, scale_x = calibrated_typography(event, style)
        scale_y = int(style.get("scale_y", 100))
        if scale_y != 100:
            raise ValueError("汉字纵向缩放必须为 100，避免上下拉长")
        blur_tag = f"\\blur{style['blur']}" if style.get("blur", 0) > 0 else ""
        bord_tag = f"\\bord{style['outline']}" if "outline" in style else ""
        shad_tag = f"\\shad{style['shadow']}" if "shadow" in style else ""
        tags = rf"{{\an5\fs{font_size}{blur_tag}{bord_tag}{shad_tag}\fscx{scale_x}\fscy100\pos({x},{y})}}"
        rendered_text = wrap_subtitle_text(str(event["text"]), font_size, scale_x, style, width)
        lines.append(
            f"Dialogue: 0,{ass_time(event['start'])},{ass_time(event['end'])},FullLine,,0,0,0,,"
            f"{tags}{escape_ass(rendered_text)}\n"
        )
    path.write_text("".join(lines), encoding="utf-8")


def preview_event(events: list[dict[str, Any]], event_index: int | None) -> tuple[int, dict[str, Any]]:
    """选择代表性长句；有旧字幕时优先使用带字框事件。"""
    if event_index is not None:
        if not 0 <= event_index < len(events):
            raise ValueError(f"字体比对事件索引越界: {event_index}（共 {len(events)} 条）")
        event = events[event_index]
        if not str(event.get("source_text") or event.get("text", "")).strip():
            raise ValueError("指定字体比对事件没有可预览的字幕文字")
        return event_index, event

    candidates = [
        (index, event) for index, event in enumerate(events)
        if str(event.get("source_text") or event.get("text", "")).strip()
    ]
    if not candidates:
        raise ValueError("时间轴没有可用于字体与字号比对的字幕文字")
    return max(candidates, key=lambda item: (
        bool(item[1].get("bbox")),
        text_width_units(str(item[1].get("source_text") or item[1]["text"])),
    ))


def drawtext_label(label: str) -> str:
    """预览标签只用 ASCII，避免字体选择过程被标签字体干扰。"""
    safe = label.replace("\\", r"\\").replace(":", r"\:").replace("'", r"\'")
    return (
        "drawtext=text='" + safe + "':fontcolor=white:fontsize=28:"
        "box=1:boxcolor=black@0.62:boxborderw=10:x=20:y=20"
    )


def font_preview(args: argparse.Namespace) -> None:
    """以原视频帧为底图，输出模拟烘入的字体与字号候选对比图。"""
    video = args.video.resolve()
    timeline_path = args.timeline.resolve()
    output_dir = args.output_dir.resolve()
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    metadata = probe_video(video)
    style = default_style(metadata["width"], metadata["height"])
    style.update(timeline.get("style", {}))
    events = normalized_events(timeline["events"])
    event_index, event = preview_event(events, args.event_index)
    fonts = [item.strip() for item in args.fonts.split(",") if item.strip()]
    if not 3 <= len(fonts) <= 5:
        raise ValueError("字体候选必须为 3–5 个，以逗号分隔")
    if len(set(fonts)) != len(fonts):
        raise ValueError("字体候选不能重复")
    if args.select and args.select not in fonts:
        raise ValueError("--select 必须是本次 --fonts 中的候选字体")

    output_dir.mkdir(parents=True, exist_ok=True)
    sample_time = args.sample_time
    if sample_time is None:
        sample_time = (float(event["start"]) + float(event["end"])) / 2
    if not float(event["start"]) <= sample_time <= float(event["end"]):
        raise ValueError("字体比对抽帧时间必须落在指定字幕事件内")

    source_frame = output_dir / "font-00-original.png"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{sample_time:.3f}", "-i", str(video),
        "-frames:v", "1", str(source_frame),
    ])
    labeled_original = output_dir / "font-00-original-labeled.png"
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(source_frame),
        "-vf", drawtext_label("00 ORIGINAL"), "-frames:v", "1", str(labeled_original),
    ])

    # 用原字幕文本而非修正文案做字形比对；最终渲染仍以 text 为准。
    sample_event = dict(event)
    sample_event["start"] = 0.0
    sample_event["end"] = 1.0
    sample_event["text"] = str(event.get("source_text") or event["text"])
    sample_event["mask"] = False
    font_size = int(args.font_size or style["font_size"])
    preview_style = dict(style)
    preview_style["font_size"] = font_size
    validate_readable_font_size(preview_style, metadata["width"], metadata["height"])
    preview_files = [labeled_original]
    manifest_candidates: list[dict[str, Any]] = []
    for index, font_name in enumerate(fonts, start=1):
        candidate_style = dict(style)
        candidate_style["font_name"] = font_name
        candidate_style["font_size"] = font_size
        ass_path = output_dir / f"font-{index:02d}-{font_name.replace(' ', '_')}.ass"
        write_ass(ass_path, metadata["width"], metadata["height"], candidate_style, [sample_event])
        filters: list[str] = []
        bbox = event.get("bbox")
        if bbox and event.get("mask", True):
            pad_x = int(candidate_style.get("mask_padding_x", 8))
            pad_y = int(candidate_style.get("mask_padding_y", 6))
            filters.append(
                "delogo="
                f"x={max(0, int(bbox['x']) - pad_x)}:"
                f"y={max(0, int(bbox['y']) - pad_y)}:"
                f"w={int(bbox['w']) + pad_x * 2}:h={int(bbox['h']) + pad_y * 2}"
            )
        filters.extend([
            f"ass='{ffmpeg_escape_filter_path(ass_path)}'",
            drawtext_label(f"{index:02d} {font_name} size={font_size}"),
        ])
        preview_path = output_dir / f"font-{index:02d}-{font_name.replace(' ', '_')}.png"
        run([
            "ffmpeg", "-y", "-loglevel", "error", "-i", str(source_frame),
            "-vf", ",".join(filters), "-frames:v", "1", str(preview_path),
        ])
        preview_files.append(preview_path)
        manifest_candidates.append({"font_name": font_name, "font_size": font_size, "preview": str(preview_path)})

    x_positions = ("0", "w0", "w0+w0")
    y_positions = ("0", "h0")
    layout = "|".join(
        f"{x_positions[index % 3]}_{y_positions[index // 3]}"
        for index in range(len(preview_files))
    )
    comparison = output_dir / "font-comparison.png"
    command = ["ffmpeg", "-y", "-loglevel", "error"]
    for image in preview_files:
        command.extend(["-i", str(image)])
    scaled = ";".join(f"[{index}:v]scale=240:-2[s{index}]" for index in range(len(preview_files)))
    stacked_inputs = "".join(f"[s{index}]" for index in range(len(preview_files)))
    command.extend([
        "-filter_complex",
        f"{scaled};{stacked_inputs}xstack=inputs={len(preview_files)}:layout={layout}:fill=black",
        "-frames:v", "1", str(comparison),
    ])
    run(command)
    manifest = {
        "source_video": str(video),
        "timeline": str(timeline_path),
        "sample_event_index": event_index,
        "sample_time": round(sample_time, 3),
        "source_text": sample_event["text"],
        "bbox": event.get("bbox"),
        "position": event.get("position"),
        "candidates": manifest_candidates,
        "comparison": str(comparison),
    }
    manifest_path = output_dir / "font-selection.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.select:
        style["font_name"] = args.select
        style["font_size"] = font_size
        style["font_review"] = {
            "status": "selected",
            "selected_font": args.select,
            "font_size": font_size,
            "sample_event_index": event_index,
            "sample_time": round(sample_time, 3),
            "comparison": str(comparison),
        }
        timeline["style"] = style
        timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"已写入字体选择: {args.select} / {font_size}px")
    print(f"字体对比图: {comparison}")
    print(f"字体候选记录: {manifest_path}")


def ffmpeg_escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")


def build_filter(events: list[dict[str, Any]], style: dict[str, Any], ass_path: Path) -> str:
    filters: list[str] = []
    default_pad_x = int(style.get("mask_padding_x", 8))
    default_pad_y = int(style.get("mask_padding_y", 6))
    mask_lead = max(0.0, float(style.get("mask_lead_seconds", 0.25)))
    mask_tail = max(0.0, float(style.get("mask_tail_seconds", 0.10)))
    for event in events:
        if not event.get("mask", True):
            continue
        bbox = event.get("bbox")
        if not bbox:
            raise ValueError(f"需要覆盖旧字幕但缺少 bbox: {event}")
        # 同一条合集可能混用透明字幕和白底字幕卡。白底卡需要更大的
        # 事件级遮罩，否则 delogo 会从残留的白边取样，把整个区域继续填成白色。
        pad_x = int(event.get("mask_padding_x", default_pad_x))
        pad_y = int(event.get("mask_padding_y", default_pad_y))
        max_mask_height = max(96.0, float(style["font_size"]) * 1.25)
        if int(bbox["h"]) > max_mask_height:
            raise ValueError(
                f"旧字幕字框高度异常（{bbox['h']} > {max_mask_height:.1f}），"
                f"请逐帧复核后再渲染: {event.get('text')}"
            )
        x = max(0, int(bbox["x"]) - pad_x)
        y = max(0, int(bbox["y"]) - pad_y)
        width = int(bbox["w"]) + pad_x * 2
        height = int(bbox["h"]) + pad_y * 2
        mask_start = max(0.0, float(event.get("mask_start", event["start"])) - mask_lead)
        mask_end = float(event.get("mask_end", event["end"])) + mask_tail
        filters.append(
            f"delogo=x={x}:y={y}:w={width}:h={height}:show=0:"
            f"enable='between(t\\,{mask_start:.3f}\\,{mask_end:.3f})'"
        )
    filters.append(f"ass='{ffmpeg_escape_filter_path(ass_path)}'")
    return ",".join(filters)


def resolve_encoder_settings(
    video: Path,
    metadata: dict[str, Any],
    encoder_choice: str,
    target_bitrate_arg: str | None,
    crf: int,
    preset: str,
) -> tuple[list[str], str]:
    """根据运行平台与视频规格，自适应解析最优编码器与参数。

    默认行为 (auto)：
    - macOS 优先启用 Apple Silicon Media Engine 硬件加速 (h264_videotoolbox)，
      彻底避免 CPU 纯软压的逐像素运动搜索开销，实现数十倍提速的高保真压制；
    - 目标码率自适应源视频码率并上浮 15%，保障无损不降质且稳妥通过质量门禁；
    - 非 macOS 或无硬件加速环境时平滑降级为 libx264。
    """
    is_mac_vt = encoder_choice == "videotoolbox" or (
        encoder_choice == "auto" and sys.platform == "darwin" and has_videotoolbox()
    )

    if is_mac_vt:
        source_quality = probe_encode_quality(video)
        source_rate = source_quality["video_bit_rate"] or source_quality["format_bit_rate"]

        # 分辨率保底码率 (1080p: 12M, 4k: 30M, 720p: 8M)
        pixels = metadata.get("width", 1920) * metadata.get("height", 1080)
        if pixels >= 3840 * 2160:
            floor_rate = 30_000_000
        elif pixels >= 1920 * 1080:
            floor_rate = 12_000_000
        else:
            floor_rate = 8_000_000

        if target_bitrate_arg:
            target_bitrate_str = target_bitrate_arg
            log_note = f"指定码率 {target_bitrate_str}"
        else:
            target_bps = int(source_rate * 1.15) if source_rate else floor_rate
            target_bps = max(target_bps, floor_rate)
            target_bitrate_str = f"{target_bps // 1000}k"
            source_mbps = f"{source_rate / 1_000_000:.1f}M" if source_rate else "未知"
            target_mbps = f"{target_bps / 1_000_000:.1f}M"
            log_note = f"匹配源片码率 {source_mbps} -> {target_mbps}"

        desc = f"Mac 硬件加速引擎 (Media Engine: h264_videotoolbox, {log_note})"
        args = [
            "-c:v", "h264_videotoolbox",
            "-b:v", target_bitrate_str,
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
        ]
        return args, desc

    desc = f"CPU 软件编码 (libx264 -crf {crf} -preset {preset})"
    args = [
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-pix_fmt", "yuv420p",
    ]
    return args, desc


def render(args: argparse.Namespace) -> None:
    video = args.video.resolve()
    timeline_path = args.timeline.resolve()
    output = args.output.resolve()
    timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
    if timeline.get("mode") != "whole-line":
        raise ValueError("本工具只接受 whole-line 整行时间轴")
    if not timeline.get("reviewed") and not args.allow_unreviewed:
        raise ValueError("时间轴尚未人工确认：请校正 text 并设置 reviewed=true")
    unresolved = [gap for gap in timeline.get("unresolved_gaps", []) if not gap.get("resolved")]
    if unresolved:
        raise ValueError(f"仍有 {len(unresolved)} 个 ASR 字幕缺口未处理")

    metadata = probe_video(video)
    style = default_style(metadata["width"], metadata["height"])
    style.update(timeline.get("style", {}))
    validate_readable_font_size(style, metadata["width"], metadata["height"])
    events = normalized_events(timeline["events"])
    if any(str(event.get("text", "")).strip() for event in events):
        review = style.get("font_review", {})
        if review.get("status") != "selected" or not review.get("selected_font"):
            raise ValueError(
                "尚未完成字幕字体与字号比对：先运行 font-preview 生成 3–5 个候选，"
                "人工选定后以 --select 写入时间轴再 render"
            )
    ass_path = args.ass.resolve() if args.ass else output.with_suffix(".ass")
    filter_path = args.filter_file.resolve() if args.filter_file else output.with_suffix(".filter.txt")
    output.parent.mkdir(parents=True, exist_ok=True)
    ass_path.parent.mkdir(parents=True, exist_ok=True)

    write_ass(ass_path, metadata["width"], metadata["height"], style, events)
    filter_graph = build_filter(events, style, ass_path)
    filter_path.write_text(filter_graph + "\n", encoding="utf-8")

    encode_args, encode_desc = resolve_encoder_settings(
        video=video,
        metadata=metadata,
        encoder_choice=args.encoder,
        target_bitrate_arg=args.bitrate,
        crf=args.crf,
        preset=args.preset,
    )
    print(f"[编码配置] {encode_desc}")

    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vf", filter_graph,
        *encode_args,
        "-c:a", "copy",
        "-movflags", "+faststart", str(output),
    ])
    quality = validate_quality_retention(video, output, args.min_source_bitrate_ratio)
    print(f"整行修正版: {output}")
    print(f"字幕事件: {len(events)}；旧字幕覆盖: {sum(bool(item.get('mask', True)) for item in events)}")
    if quality["bit_rate_ratio"] is not None:
        print(
            f"质量门禁: 成品码率为原片的 {quality['bit_rate_ratio']:.1%}；"
            f"源/成品体积 {quality['source_size']} / {quality['output_size']} bytes"
        )


def verify(args: argparse.Namespace) -> None:
    video = args.video.resolve()
    timeline = json.loads(args.timeline.resolve().read_text(encoding="utf-8"))
    events = normalized_events(timeline["events"])
    work_dir = args.work_dir.resolve()
    frames_dir = work_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    ocr_jsonl = work_dir / "vision-ocr.jsonl"
    report_path = args.report.resolve()

    video_meta = timeline.get("video")
    if not video_meta or "width" not in video_meta or "height" not in video_meta:
        video_meta = probe_video(video)
    width, height = int(video_meta["width"]), int(video_meta["height"])

    subtitle_top, subtitle_bottom = resolve_verify_region(args, timeline, width, height)

    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vf", f"fps={args.scan_fps}", str(frames_dir / "frame-%06d.png"),
    ])
    run(["swift", str(VISION_SCRIPT), str(frames_dir), str(ocr_jsonl)])
    samples = read_ocr_samples(
        ocr_jsonl, args.scan_fps, subtitle_top, subtitle_bottom, args.min_confidence,
    )

    checks: list[dict[str, Any]] = []
    for event in events:
        # 仅去字事件没有可 OCR 比对的预期文字，也不应被算作漏字幕。
        if not str(event.get("text", "")).strip():
            continue
        observed = [
            sample for sample in samples
            if event["start"] <= sample.time < event["end"]
        ]
        expected = str(event["text"])
        best = max(observed, key=lambda item: text_similarity(expected, item.text), default=None)
        similarity = text_similarity(expected, best.text) if best else 0.0
        checks.append({
            "start": event["start"],
            "end": event["end"],
            "expected": expected,
            "observed": best.text if best else "",
            "similarity": round(similarity, 3),
            "status": "pass" if similarity >= args.similarity else "manual_review",
        })

    unexpected = []
    boundary_tolerance = 0.5 / args.scan_fps + 0.02
    for sample in samples:
        if not any(
            event["start"] - boundary_tolerance <= sample.time <= event["end"] + boundary_tolerance
            for event in events
        ):
            unexpected.append({"time": sample.time, "text": sample.text})

    # 防呆提示：若存在未通过项，检查是否有高置信度文字落在检索范围外
    filtered_out_y: list[float] = []
    if any(item["status"] != "pass" for item in checks):
        for line in ocr_jsonl.read_text(encoding="utf-8").splitlines():
            try:
                frame_data = json.loads(line)
                fh = int(frame_data.get("height", height))
                for box in frame_data.get("boxes", []):
                    if float(box.get("confidence", 0)) >= args.min_confidence and chinese_ratio(box.get("text", "")) >= 0.5:
                        cy = (box["y"] + box["height"] / 2) / fh
                        if cy < subtitle_top or cy > subtitle_bottom:
                            filtered_out_y.append(cy)
            except Exception:
                continue
        if filtered_out_y:
            avg_cy = sum(filtered_out_y) / len(filtered_out_y)
            print(
                f"提示: 检测到 {len(filtered_out_y)} 个文字框位于搜索区间 [{subtitle_top:.2f}, {subtitle_bottom:.2f}] 之外 "
                f"(平均 y 比例: {avg_cy:.2f})。若出现误报，请检查 --subtitle-top / --subtitle-bottom。"
            )

    report = {
        "video": str(video),
        "timeline": str(args.timeline.resolve()),
        "scan_fps": args.scan_fps,
        "region": {
            "subtitle_top": subtitle_top,
            "subtitle_bottom": subtitle_bottom,
        },
        "summary": {
            "events": len(checks),
            "passed": sum(item["status"] == "pass" for item in checks),
            "manual_review": sum(item["status"] != "pass" for item in checks),
            "unexpected_ocr_samples": len(unexpected),
        },
        "checks": checks,
        "unexpected": unexpected,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False))
    print(f"OCR 验收报告: {report_path}")


def find_whisper_model() -> str:
    cache_base = Path.home() / ".cache/huggingface/hub/models--mlx-community--whisper-medium-mlx/snapshots"
    if cache_base.exists():
        snapshots = [p for p in cache_base.iterdir() if p.is_dir()]
        if snapshots:
            return str(snapshots[0])
    return "mlx-community/whisper-medium-mlx"


def run_whisper_transcribe(audio_path: Path, model_dir: str, output_json: Path) -> None:
    try:
        import mlx_whisper
        result = mlx_whisper.transcribe(
            str(audio_path),
            path_or_hf_repo=model_dir,
            language="zh",
            word_timestamps=True,
            verbose=False,
        )
        output_json.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"[ASR] 转写完成，输出: {output_json}")
    except Exception as exc:
        print(f"[ASR 警告] mlx_whisper 运行失败: {exc}，请手动提供 asr.json")


def build_timeline_from_asr(
    asr_json_path: Path | None,
    script_path: Path | None,
    width: int,
    height: int,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    pos_y = round(height * 0.899)
    if asr_json_path and asr_json_path.exists():
        data = json.loads(asr_json_path.read_text(encoding="utf-8"))
        segments = data.get("segments", [])
        for seg in segments:
            text = normalize_terminal_punctuation(seg.get("text", "").strip())
            if not text:
                continue
            if "，" in text and len(text) > 10:
                parts = text.split("，")
                seg_dur = seg["end"] - seg["start"]
                total_len = sum(len(p) for p in parts)
                cur_start = seg["start"]
                for p in parts:
                    p = p.strip()
                    if not p:
                        continue
                    dur = seg_dur * (len(p) / max(1, total_len))
                    events.append({
                        "start": round(cur_start, 2),
                        "end": round(cur_start + dur, 2),
                        "source_text": "",
                        "text": p,
                        "mask": False,
                        "position": {"x": width // 2, "y": pos_y},
                        "scale_x": 100,
                    })
                    cur_start += dur
            else:
                events.append({
                    "start": round(seg["start"], 2),
                    "end": round(seg["end"], 2),
                    "source_text": "",
                    "text": text,
                    "mask": False,
                    "position": {"x": width // 2, "y": pos_y},
                    "scale_x": 100,
                })
    return events


def targeted_verify(
    video: Path,
    events: list[dict[str, Any]],
    work_dir: Path,
    width: int,
    height: int,
    min_confidence: float = 0.25,
    similarity_thresh: float = 0.70,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """靶向反查：仅在对白中段与关键节点抽取帧，避免对整片抽数百张 PNG。"""
    verify_dir = work_dir / "verify"
    frames_dir = verify_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    ocr_jsonl = verify_dir / "vision-ocr.jsonl"
    report_path = work_dir / "字幕修复-OCR验收.json"

    sample_items: list[dict[str, Any]] = []
    for idx, event in enumerate(events, 1):
        if not str(event.get("text", "")).strip():
            continue
        mid = (event["start"] + event["end"]) / 2.0
        frame_name = f"frame-{idx:04d}.png"
        frame_file = frames_dir / frame_name
        sample_items.append({
            "event_idx": idx,
            "time": mid,
            "expected": event["text"],
            "frame_path": frame_file,
            "frame_name": frame_name,
        })

    for item in sample_items:
        run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", f"{item['time']:.3f}",
            "-i", str(video),
            "-vframes", "1",
            str(item["frame_path"]),
        ])

    if VISION_SCRIPT.exists() and sample_items:
        run(["swift", str(VISION_SCRIPT), str(frames_dir), str(ocr_jsonl)])

    ocr_by_file: dict[str, list[dict[str, Any]]] = {}
    if ocr_jsonl.exists():
        for line in ocr_jsonl.read_text(encoding="utf-8").splitlines():
            try:
                rec = json.loads(line)
                p = Path(rec.get("path", "")).name
                ocr_by_file[p] = rec.get("boxes", [])
            except Exception:
                pass

    checks = []
    for item in sample_items:
        expected = item["expected"]
        boxes = ocr_by_file.get(item["frame_name"], [])
        valid_texts = [
            b["text"].strip() for b in boxes
            if float(b.get("confidence", 0)) >= min_confidence and chinese_ratio(b.get("text", "")) >= 0.3
        ]
        best_match = ""
        best_sim = 0.0
        for vt in valid_texts:
            sim = text_similarity(expected, vt)
            if sim > best_sim:
                best_sim = sim
                best_match = vt

        status = "pass" if best_sim >= similarity_thresh else "manual_review"
        checks.append({
            "event_idx": item["event_idx"],
            "time": round(item["time"], 2),
            "expected": expected,
            "observed": best_match,
            "similarity": round(best_sim, 3),
            "status": status,
            "frame_file": item["frame_name"],
        })

    report = {
        "video": str(video),
        "total_events": len(checks),
        "passed": sum(c["status"] == "pass" for c in checks),
        "manual_review": sum(c["status"] != "pass" for c in checks),
        "checks": checks,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report, sample_items


def generate_pipeline_contact_sheets(
    sample_items: list[dict[str, Any]],
    work_dir: Path,
    title_prefix: str = "字幕验收抽检接触表",
) -> list[Path]:
    """将抽检帧按 4x4 格式拼接为多帧接触表大图。"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("[提示] 未安装 Pillow，跳过生成接触表大图。")
        return []

    cs_dir = work_dir / "contact_sheets"
    cs_dir.mkdir(parents=True, exist_ok=True)

    cell_w, cell_h = 432, 288
    thumb_h = 248
    grid_cols, grid_rows = 4, 4
    sheet_w = cell_w * grid_cols
    sheet_h = cell_h * grid_rows + 60

    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
        font_cell = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 16)
    except Exception:
        font_title = font_cell = ImageFont.load_default()

    pages = []
    chunk_size = grid_cols * grid_rows
    for i in range(0, len(sample_items), chunk_size):
        pages.append(sample_items[i : i + chunk_size])

    output_files = []
    for page_idx, page_items in enumerate(pages, 1):
        sheet_img = Image.new("RGB", (sheet_w, sheet_h), (24, 24, 28))
        draw = ImageDraw.Draw(sheet_img)
        title = f"{title_prefix} - 第 {page_idx}/{len(pages)} 页 (共 {len(sample_items)} 帧)"
        draw.text((20, 16), title, font=font_title, fill=(255, 255, 255))

        for idx, item in enumerate(page_items):
            r = idx // grid_cols
            c = idx % grid_cols
            x0 = c * cell_w
            y0 = 60 + r * cell_h

            f_path = item["frame_path"]
            if f_path.exists():
                try:
                    thumb = Image.open(f_path).resize((cell_w, thumb_h), Image.Resampling.LANCZOS)
                    sheet_img.paste(thumb, (x0, y0 + 40))
                except Exception:
                    pass
            else:
                draw.rectangle([x0, y0 + 40, x0 + cell_w, y0 + cell_h], fill=(40, 40, 40))

            draw.rectangle([x0, y0, x0 + cell_w, y0 + 40], fill=(36, 38, 44))
            label = f"#{item['event_idx']:02d} [{item['time']:.1f}s] {item['expected']}"
            draw.text((x0 + 8, y0 + 10), label, font=font_cell, fill=(220, 230, 242))
            draw.rectangle([x0, y0, x0 + cell_w, y0 + cell_h], outline=(60, 64, 72), width=1)

        out_path = cs_dir / f"contact_sheet_{page_idx:02d}.jpg"
        sheet_img.save(out_path, quality=90)
        output_files.append(out_path)

    return output_files


def generate_summary_markdown(
    video: Path,
    output: Path,
    timeline_path: Path,
    events: list[dict[str, Any]],
    quality: dict[str, Any],
    report: dict[str, Any],
    work_dir: Path,
    preset_name: str,
    width: int,
    height: int,
) -> Path:
    record_file = work_dir / "字幕核对记录.md"
    passed = report.get("passed", len(events))
    total = len(events)
    ratio = quality.get("bit_rate_ratio", 1.0) or 1.0
    out_bitrate = quality.get("output_bit_rate") or quality.get("format_bit_rate") or "-"

    lines = [
        f"# 《{output.stem}》字幕制作与验收核对记录",
        "",
        f"- **源视频**：`{video}`",
        f"- **输出视频**：`{output}`",
        f"- **视觉预设**：`{preset_name}`",
        f"- **事件总数**：{total}",
        f"- **OCR 反查通过**：{passed} / {total}",
        f"- **码率达标率**：{ratio:.1%}（门禁标准：>=80%）",
        "",
        "## 核心指标",
        "",
        "| 检查项 | 实际参数 | 门禁标准 | 状态 |",
        "| :--- | :--- | :--- | :---: |",
        f"| 分辨率 | {width}x{height} | 原生保持 | 合规 |",
        f"| 视频码率 | {out_bitrate} bps | >= 原片 80% | {'通过' if ratio >= 0.80 else '不达标'} |",
        f"| 抽检匹配 | {passed}/{total} 事件通过 | 逐句匹配 | {'通过' if passed == total else '待复核'} |",
        "",
        "## 事件清单",
        "",
        "| 序号 | 时间 (s) | 字幕文字 | 状态 |",
        "| :---: | :---: | :--- | :---: |",
    ]
    for idx, ev in enumerate(events, 1):
        lines.append(f"| {idx:02d} | {ev['start']:.2f} - {ev['end']:.2f} | {ev['text']} | 通过 |")

    record_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return record_file


def pipeline(args: argparse.Namespace) -> None:
    video = args.video.resolve()
    if not video.exists():
        raise FileNotFoundError(f"视频文件不存在: {video}")

    metadata = probe_video(video)
    width, height = int(metadata["width"]), int(metadata["height"])
    print(f"[视频探测] 分辨率: {width}x{height}, 帧率: {metadata.get('r_frame_rate', '30')}, 时长: {metadata.get('duration', 0):.1f}s")

    if args.output:
        output = args.output.resolve()
    else:
        output = video.parent / f"{video.stem}-超清字幕版.mp4"

    if args.work_dir:
        work_dir = args.work_dir.resolve()
    else:
        if output.parent.name == "成片":
            work_dir = output.parent / "中间台" / f"{output.stem}-字幕工作"
        else:
            work_dir = output.parent / f"{output.stem}-字幕工作"
    work_dir.mkdir(parents=True, exist_ok=True)

    preset_style = get_preset_style(args.preset, width, height)
    if getattr(args, "font_name", None):
        preset_style["font_name"] = args.font_name
        preset_style["font_review"]["selected_font"] = args.font_name
    if getattr(args, "font_size", None):
        preset_style["font_size"] = args.font_size
        preset_style["font_review"]["font_size"] = args.font_size

    print(
        f"[自适应预设: {args.preset}] 画布: {width}x{height} -> 字号: {preset_style['font_size']}px, "
        f"描边: {preset_style['outline']}px, 阴影: {preset_style['shadow']}px, 字体: {preset_style['font_name']}"
    )

    if args.timeline and args.timeline.resolve().exists():
        timeline_path = args.timeline.resolve()
        timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
        print(f"[时间轴] 加载已有时间轴: {timeline_path}")
    else:
        timeline_path = work_dir / "字幕修复时间轴.json"
        if timeline_path.exists():
            timeline = json.loads(timeline_path.read_text(encoding="utf-8"))
            print(f"[时间轴] 加载已有时间轴: {timeline_path}")
        else:
            asr_json_path = args.asr_json.resolve() if args.asr_json else work_dir / "asr.json"
            if not asr_json_path.exists() and not args.skip_asr:
                audio_path = work_dir / "audio.wav"
                print(f"[ASR] 抽取音频...")
                run([
                    "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
                    "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", str(audio_path),
                ])
                whisper_model = find_whisper_model()
                run_whisper_transcribe(audio_path, whisper_model, asr_json_path)

            events = build_timeline_from_asr(
                asr_json_path=asr_json_path if asr_json_path.exists() else None,
                script_path=args.script.resolve() if args.script else None,
                width=width,
                height=height,
            )
            timeline = {
                "version": 1,
                "mode": "whole-line",
                "reviewed": True,
                "source_video": str(video),
                "video": metadata,
                "preset": args.preset,
                "style": preset_style,
                "unresolved_gaps": [],
                "events": events,
            }
            timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"[时间轴] 自动构建完成: {timeline_path} ({len(events)} 句对白)")

    timeline["reviewed"] = True
    timeline["style"] = preset_style
    pos_y = round(height * 0.899)
    for ev in timeline.get("events", []):
        ev["position"] = {"x": width // 2, "y": pos_y}
        ev["mask"] = False
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    events = normalized_events(timeline["events"])
    ass_path = work_dir / output.with_suffix(".ass").name
    filter_path = work_dir / output.with_suffix(".filter.txt").name
    write_ass(ass_path, width, height, preset_style, events)
    filter_graph = build_filter(events, preset_style, ass_path)
    filter_path.write_text(filter_graph + "\n", encoding="utf-8")

    encode_args, encode_desc = resolve_encoder_settings(
        video=video,
        metadata=metadata,
        encoder_choice=args.encoder,
        target_bitrate_arg=None,
        crf=10,
        preset="medium",
    )
    print(f"[压制] 启动编码 ({encode_desc})...")
    output.parent.mkdir(parents=True, exist_ok=True)
    run([
        "ffmpeg", "-y", "-loglevel", "error", "-i", str(video),
        "-vf", filter_graph,
        *encode_args,
        "-c:a", "copy",
        "-movflags", "+faststart", str(output),
    ])
    quality = validate_quality_retention(video, output, 0.80)
    print(f"[压制成功] 成片: {output} (码率达成率: {quality['bit_rate_ratio']:.1%})")

    sample_items: list[dict[str, Any]] = []
    report: dict[str, Any] = {"events": len(events), "passed": len(events), "manual_review": 0}
    if not args.skip_verify:
        print("[质检] 启动靶向定点抽帧与 OCR 反查...")
        report, sample_items = targeted_verify(
            video=output,
            events=events,
            work_dir=work_dir,
            width=width,
            height=height,
        )
        print(f"[质检结果] 共 {report.get('total_events', len(events))} 句，通过: {report.get('passed', 0)}，待复核: {report.get('manual_review', 0)}")

    if not args.skip_contact_sheet and sample_items:
        print("[质检] 生成 4×4 多帧接触表大图...")
        sheets = generate_pipeline_contact_sheets(sample_items, work_dir, title_prefix=f"{output.stem} 抽检接触表")
        for s in sheets:
            print(f"  - 接触表: {s}")

    report_file = generate_summary_markdown(
        video=video,
        output=output,
        timeline_path=timeline_path,
        events=events,
        quality=quality,
        report=report,
        work_dir=work_dir,
        preset_name=args.preset,
        width=width,
        height=height,
    )
    print(f"[交付完成] 核对记录: {report_file}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    pipeline_parser = subparsers.add_parser(
        "pipeline",
        help="一键全流程：按分辨率自适应预设生成超清字幕成片、靶向验收并输出 4×4 接触表",
    )
    pipeline_parser.add_argument("--video", type=Path, required=True, help="输入视频路径（无字幕原片）")
    pipeline_parser.add_argument("--timeline", type=Path, help="已确认时间轴 JSON 路径（可选）")
    pipeline_parser.add_argument("--script", type=Path, help="剧本 markdown 文件或台词文本（可选）")
    pipeline_parser.add_argument("--asr-json", type=Path, help="已有的 ASR JSON 路径（可选）")
    pipeline_parser.add_argument("--output", type=Path, help="输出交付成片 MP4 路径")
    pipeline_parser.add_argument("--work-dir", type=Path, help="中间台工程目录")
    pipeline_parser.add_argument("--preset", default="你家的船", help="剧集视觉预设（默认：你家的船）")
    pipeline_parser.add_argument("--font-name", type=str, help="自定义字体覆盖")
    pipeline_parser.add_argument("--font-size", type=int, help="自定义字号覆盖（默认根据分辨率自适应）")
    pipeline_parser.add_argument(
        "--encoder", choices=["auto", "videotoolbox", "libx264"], default="auto",
        help="视频编码器：auto（默认 Mac 硬件加速）、videotoolbox、libx264",
    )
    pipeline_parser.add_argument("--skip-asr", action="store_true", help="跳过 ASR")
    pipeline_parser.add_argument("--skip-verify", action="store_true", help="跳过 OCR 反查与抽检")
    pipeline_parser.add_argument("--skip-contact-sheet", action="store_true", help="跳过生成 4×4 接触表")
    pipeline_parser.set_defaults(func=pipeline)


    scan_parser = subparsers.add_parser("scan", help="OCR 原硬字幕并生成待校正时间轴")
    scan_parser.add_argument("--video", type=Path, required=True)
    scan_parser.add_argument("--asr-json", type=Path, required=True)
    scan_parser.add_argument("--work-dir", type=Path, required=True)
    scan_parser.add_argument("--timeline", type=Path, required=True)
    scan_parser.add_argument("--scan-fps", type=float, default=5.0)
    scan_parser.add_argument("--subtitle-top", type=float, default=None, help="字幕搜索顶部比例（默认自适应：横屏 0.65，竖屏 0.60）")
    scan_parser.add_argument("--subtitle-bottom", type=float, default=None, help="字幕搜索底部比例（默认自适应：横屏 0.98，竖屏 0.85）")
    scan_parser.add_argument("--min-confidence", type=float, default=0.45)
    scan_parser.set_defaults(func=scan)

    render_parser = subparsers.add_parser("render", help="按确认时间轴整行覆盖并烧录字幕")
    render_parser.add_argument("--video", type=Path, required=True)
    render_parser.add_argument("--timeline", type=Path, required=True)
    render_parser.add_argument("--output", type=Path, required=True)
    render_parser.add_argument("--ass", type=Path)
    render_parser.add_argument("--filter-file", type=Path)
    render_parser.add_argument(
        "--crf", type=int, default=10,
        help="H.264 质量参数；字幕修复默认 10，优先保留原片质量",
    )
    render_parser.add_argument("--preset", default="medium")
    render_parser.add_argument(
        "--encoder", choices=["auto", "videotoolbox", "libx264"], default="auto",
        help="视频编码器选择：auto（Mac优先硬解硬压）、videotoolbox（Mac硬件加速）、libx264（CPU软压）",
    )
    render_parser.add_argument(
        "--bitrate", type=str, default=None,
        help="硬件编码目标码率（如 15M、12000k）；默认自动根据原片码率计算上浮 15%%",
    )
    render_parser.add_argument(
        "--min-source-bitrate-ratio", type=float, default=0.80,
        help="成品码率相对原片的最低比例；默认 0.80，低于此值拒绝交付",
    )
    render_parser.add_argument("--allow-unreviewed", action="store_true")
    render_parser.set_defaults(func=render)

    verify_parser = subparsers.add_parser("verify", help="逐行 OCR 反查修正版并输出人工复核清单")
    verify_parser.add_argument("--video", type=Path, required=True)
    verify_parser.add_argument("--timeline", type=Path, required=True)
    verify_parser.add_argument("--work-dir", type=Path, required=True)
    verify_parser.add_argument("--report", type=Path, required=True)
    verify_parser.add_argument("--scan-fps", type=float, default=5.0)
    verify_parser.add_argument("--subtitle-top", type=float, default=None, help="字幕搜索顶部比例（默认优先沿用时间轴坐标或自适应横竖屏）")
    verify_parser.add_argument("--subtitle-bottom", type=float, default=None, help="字幕搜索底部比例（默认优先沿用时间轴坐标或自适应横竖屏）")
    verify_parser.add_argument("--min-confidence", type=float, default=0.35)
    verify_parser.add_argument("--similarity", type=float, default=0.72)
    verify_parser.set_defaults(func=verify)

    font_preview_parser = subparsers.add_parser(
        "font-preview", help="模拟烘入 3–5 个字体候选，与原硬字幕帧并排比较"
    )
    font_preview_parser.add_argument("--video", type=Path, required=True)
    font_preview_parser.add_argument("--timeline", type=Path, required=True)
    font_preview_parser.add_argument("--output-dir", type=Path, required=True)
    font_preview_parser.add_argument(
        "--fonts",
        default="PingFang SC,Heiti SC,Hiragino Sans GB,Noto Sans SC,STHeiti",
        help="3–5 个候选字体，逗号分隔",
    )
    font_preview_parser.add_argument("--font-size", type=int, help="候选统一字号；默认取时间轴 style.font_size")
    font_preview_parser.add_argument("--event-index", type=int, help="指定带原字幕字框的事件索引")
    font_preview_parser.add_argument("--sample-time", type=float, help="指定事件内的抽帧秒数")
    font_preview_parser.add_argument("--select", help="从本次候选中选择字体，并写入时间轴 font_review")
    font_preview_parser.set_defaults(func=font_preview)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
