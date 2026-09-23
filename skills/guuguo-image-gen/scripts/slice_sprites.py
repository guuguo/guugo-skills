#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent


def parse_box(value: str) -> tuple[int, int, int, int]:
    parts = [int(p) for p in value.replace(",", " ").split()]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("box must be x1,y1,x2,y2")
    return parts[0], parts[1], parts[2], parts[3]


def parse_size(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    raw = str(value).lower().replace(",", "x")
    parts = [p for p in raw.split("x") if p]
    if len(parts) == 1:
        n = int(parts[0])
        return n, n
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"Invalid size: {value}")
    return int(parts[0]), int(parts[1])


def trim_alpha(image: Image.Image, padding: int) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        return image
    left, top, right, bottom = bbox
    return image.crop((
        max(0, left - padding),
        max(0, top - padding),
        min(image.width, right + padding),
        min(image.height, bottom + padding),
    ))


def fit_canvas(image: Image.Image, target_size: tuple[int, int] | None) -> Image.Image:
    if not target_size:
        return image
    image = trim_alpha(image, 0)
    sprite = image.copy()
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    sprite.thumbnail((int(target_size[0] * 0.94), int(target_size[1] * 0.94)), resampling)
    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    canvas.alpha_composite(sprite, ((target_size[0] - sprite.width) // 2, (target_size[1] - sprite.height) // 2))
    return canvas


def write_meta(path: Path, border: str | None) -> None:
    cmd = [sys.executable, str(HERE / "cutout_assets.py"), "--input", str(path), "--output", str(path), "--key", "none", "--meta", "cocos"]
    if border:
        cmd.extend(["--border", border])
    subprocess.run(cmd, check=True)


def process_one(input_path: Path, output_path: Path, box: tuple[int, int, int, int], target_size: tuple[int, int] | None, padding: int, should_trim: bool, meta: str, border: str | None) -> Path:
    source = Image.open(input_path).convert("RGBA")
    image = source.crop(box)
    if should_trim:
        image = trim_alpha(image, padding)
    image = fit_canvas(image, target_size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    if meta == "cocos":
        write_meta(output_path, border)
    return output_path


def run_spec(spec_path: Path, base_dir: Path, meta: str, border: str | None) -> list[Path]:
    specs = json.loads(spec_path.read_text(encoding="utf8"))
    if not isinstance(specs, list):
        raise SystemExit("Spec JSON must be a list.")
    written = []
    for item in specs:
        input_path = (base_dir / item["input"]).resolve()
        output_path = (base_dir / item["output"]).resolve()
        box = tuple(item["box"])
        if len(box) != 4:
            raise SystemExit(f"Invalid box in {item}")
        target_size = parse_size(item.get("target_size") or item.get("size"))
        padding = int(item.get("padding", 8))
        should_trim = bool(item.get("trim", True))
        written.append(process_one(input_path, output_path, box, target_size, padding, should_trim, meta, item.get("border") or border))
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop known sprite boxes from sheets.")
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--base-dir", type=Path, default=Path("."))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--box", type=parse_box)
    parser.add_argument("--target-size", type=parse_size)
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--no-trim", action="store_true")
    parser.add_argument("--meta", choices=["none", "cocos"], default="none")
    parser.add_argument("--border", help="Cocos nine-slice border: left,right,top,bottom")
    args = parser.parse_args()

    if args.spec:
        written = run_spec(args.spec, args.base_dir.resolve(), args.meta, args.border)
    else:
        if not args.input or not args.output or not args.box:
            raise SystemExit("Single mode requires --input, --output and --box.")
        written = [process_one(args.input, args.output, args.box, args.target_size, args.padding, not args.no_trim, args.meta, args.border)]
    print(json.dumps({"written": [str(path) for path in written]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
