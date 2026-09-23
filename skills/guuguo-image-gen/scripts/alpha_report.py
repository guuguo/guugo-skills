#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image


def iter_images(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*.png") if p.is_file())


def key_pixel_count(image: Image.Image, key: str) -> int:
    if key == "none":
        return 0
    rgba = image.convert("RGBA")
    count = 0
    for r, g, b, a in rgba.getdata():
        if a <= 0:
            continue
        if key == "green" and g > 120 and g - max(r, b) > 24:
            count += 1
        elif key == "magenta" and r > 120 and b > 120 and min(r, b) - g > 24:
            count += 1
    return count


def report_one(path: Path, key: str) -> dict:
    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A")
    bbox = alpha.getbbox()
    corners = [
        alpha.getpixel((0, 0)),
        alpha.getpixel((image.width - 1, 0)),
        alpha.getpixel((0, image.height - 1)),
        alpha.getpixel((image.width - 1, image.height - 1)),
    ]
    alpha_data = list(alpha.getdata())
    opaque = sum(1 for a in alpha_data if a >= 250)
    transparent = sum(1 for a in alpha_data if a <= 5)
    partial = len(alpha_data) - opaque - transparent
    return {
        "file": str(path),
        "size": [image.width, image.height],
        "has_alpha_bbox": bbox is not None,
        "alpha_bbox": list(bbox) if bbox else None,
        "corner_alpha": corners,
        "corner_alpha_ok": all(a <= 5 for a in corners),
        "opaque_pixels": opaque,
        "partial_alpha_pixels": partial,
        "transparent_pixels": transparent,
        "possible_key_pixels": key_pixel_count(image, key),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Report alpha and possible chroma-key residue for PNG assets.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--key", choices=["green", "magenta", "none"], default="none")
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    reports = [report_one(path, args.key) for path in iter_images(args.path)]
    payload = {"count": len(reports), "reports": reports}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + "\n", encoding="utf8")
    print(text)


if __name__ == "__main__":
    main()
