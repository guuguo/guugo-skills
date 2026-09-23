#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import uuid
from collections import deque
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw

ALPHA_THRESHOLD = 16


def parse_size(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    raw = value.lower().replace(",", "x")
    parts = [p for p in raw.split("x") if p]
    if len(parts) == 1:
        n = int(parts[0])
        return n, n
    if len(parts) != 2:
        raise argparse.ArgumentTypeError(f"Invalid size: {value}")
    return int(parts[0]), int(parts[1])


def choose_key(image: Image.Image) -> str:
    rgba = image.convert("RGBA")
    samples = []
    for x, y in [(0, 0), (rgba.width - 1, 0), (0, rgba.height - 1), (rgba.width - 1, rgba.height - 1)]:
        samples.append(rgba.getpixel((x, y))[:3])
    r = sum(c[0] for c in samples) / len(samples)
    g = sum(c[1] for c in samples) / len(samples)
    b = sum(c[2] for c in samples) / len(samples)
    if g > 160 and g - max(r, b) > 70:
        return "green"
    if r > 160 and b > 160 and min(r, b) - g > 70:
        return "magenta"
    if min(r, g, b) > 220:
        return "white"
    return "none"


def remove_key(image: Image.Image, key: str, aggressive: bool) -> Image.Image:
    if key == "auto":
        key = choose_key(image)
    if key == "none":
        return image.convert("RGBA")
    if key == "white":
        return remove_edge_white(image, aggressive)

    rgba = image.convert("RGBA")
    pixels = rgba.load()
    for y in range(rgba.height):
        for x in range(rgba.width):
            r, g, b, a = pixels[x, y]
            if key == "green":
                dominant = g - max(r, b)
                hard = g > 205 and r < 95 and b < 95 and dominant > 110
                soft = aggressive and g > 120 and dominant > 22 and g > r * 1.12 and g > b * 1.12
                if hard or soft:
                    strength = min(1.0, max(0.0, dominant / 180.0))
                    alpha = 0 if strength > 0.78 else int(a * (1.0 - strength))
                    pixels[x, y] = (r, min(g, max(r, b) + 8), b, alpha)
            elif key == "magenta":
                dominant = min(r, b) - g
                hard = r > 190 and b > 190 and g < 100 and dominant > 90
                soft = aggressive and r > 120 and b > 120 and dominant > 20
                if hard or soft:
                    strength = min(1.0, max(0.0, dominant / 170.0))
                    alpha = 0 if strength > 0.76 else int(a * (1.0 - strength))
                    base = max(g, min(r, b) - 16)
                    pixels[x, y] = (base, g, base, alpha)
    return rgba


def remove_edge_white(image: Image.Image, aggressive: bool) -> Image.Image:
    rgba = image.convert("RGBA")
    pixels = rgba.load()
    width, height = rgba.size
    queue = deque()
    visited = set()
    for x in range(width):
        queue.append((x, 0))
        queue.append((x, height - 1))
    for y in range(height):
        queue.append((0, y))
        queue.append((width - 1, y))
    threshold = 232 if aggressive else 244
    while queue:
        x, y = queue.popleft()
        if (x, y) in visited:
            continue
        visited.add((x, y))
        r, g, b, a = pixels[x, y]
        if min(r, g, b) < threshold:
            continue
        pixels[x, y] = (255, 255, 255, 0)
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                queue.append((nx, ny))
    return rgba


def pad_box(box: tuple[int, int, int, int], size: tuple[int, int], padding: int) -> tuple[int, int, int, int]:
    left, top, right, bottom = box
    width, height = size
    return max(0, left - padding), max(0, top - padding), min(width, right + padding), min(height, bottom + padding)


def trim_alpha(image: Image.Image, padding: int) -> Image.Image:
    bbox = image.getchannel("A").getbbox()
    if not bbox:
        return image
    return image.crop(pad_box(bbox, image.size, padding))


def fit_canvas(image: Image.Image, target_size: tuple[int, int] | None) -> Image.Image:
    if not target_size:
        return image
    image = trim_alpha(image, 0)
    max_w = int(target_size[0] * 0.94)
    max_h = int(target_size[1] * 0.94)
    sprite = image.copy()
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    sprite.thumbnail((max_w, max_h), resampling)
    canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
    canvas.alpha_composite(sprite, ((target_size[0] - sprite.width) // 2, (target_size[1] - sprite.height) // 2))
    return canvas


def connected_components(image: Image.Image, min_area: int) -> list[dict]:
    alpha = image.getchannel("A")
    width, height = image.size
    data = alpha.tobytes()
    mask = [bytearray(1 if data[y * width + x] > ALPHA_THRESHOLD else 0 for x in range(width)) for y in range(height)]
    components: list[dict] = []
    for y in range(height):
        for x in range(width):
            if mask[y][x] == 0:
                continue
            mask[y][x] = 0
            queue = deque([(x, y)])
            pixels = []
            left = right = x
            top = bottom = y
            while queue:
                cx, cy = queue.popleft()
                pixels.append((cx, cy))
                left, right = min(left, cx), max(right, cx)
                top, bottom = min(top, cy), max(bottom, cy)
                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if nx == cx and ny == cy:
                            continue
                        if 0 <= nx < width and 0 <= ny < height and mask[ny][nx]:
                            mask[ny][nx] = 0
                            queue.append((nx, ny))
            if len(pixels) >= min_area:
                components.append({
                    "bbox": (left, top, right + 1, bottom + 1),
                    "area": len(pixels),
                    "pixels": pixels,
                    "center": ((left + right) / 2, (top + bottom) / 2),
                })
    return sort_components(components)


def sort_components(components: list[dict]) -> list[dict]:
    if not components:
        return []
    heights = [c["bbox"][3] - c["bbox"][1] for c in components]
    threshold = max(16, sum(heights) / len(heights) * 0.65)
    rows: list[list[dict]] = []
    for component in sorted(components, key=lambda c: c["center"][1]):
        for row in rows:
            avg_y = sum(c["center"][1] for c in row) / len(row)
            if abs(component["center"][1] - avg_y) <= threshold:
                row.append(component)
                break
        else:
            rows.append([component])
    return [c for row in rows for c in sorted(row, key=lambda item: item["center"][0])]


def crop_component(source: Image.Image, component: dict, padding: int) -> Image.Image:
    box = pad_box(component["bbox"], source.size, padding)
    crop = Image.new("RGBA", (box[2] - box[0], box[3] - box[1]), (0, 0, 0, 0))
    source_pixels = source.load()
    out_pixels = crop.load()
    for x, y in component["pixels"]:
        if box[0] <= x < box[2] and box[1] <= y < box[3]:
            out_pixels[x - box[0], y - box[1]] = source_pixels[x, y]
    return crop


def sprite_vertices(width: int, height: int) -> dict:
    hw, hh = width / 2, height / 2
    return {
        "rawPosition": [-hw, -hh, 0, hw, -hh, 0, -hw, hh, 0, hw, hh, 0],
        "indexes": [0, 1, 2, 2, 1, 3],
        "uv": [0, height, width, height, 0, 0, width, 0],
        "nuv": [0, 0, 1, 0, 0, 1, 1, 1],
        "minPos": [-hw, -hh, 0],
        "maxPos": [hw, hh, 0],
    }


def write_cocos_meta(path: Path, border: tuple[int, int, int, int] | None = None) -> None:
    meta_path = path.with_suffix(path.suffix + ".meta")
    width, height = Image.open(path).size
    asset_uuid = str(uuid.uuid4())
    if meta_path.exists():
        try:
            asset_uuid = json.loads(meta_path.read_text(encoding="utf8")).get("uuid") or asset_uuid
        except json.JSONDecodeError:
            pass
    left, right, top, bottom = border or (0, 0, 0, 0)
    meta = {
        "ver": "1.0.27",
        "importer": "image",
        "imported": True,
        "uuid": asset_uuid,
        "files": [".json", ".png"],
        "subMetas": {
            "6c48a": {
                "importer": "texture",
                "uuid": f"{asset_uuid}@6c48a",
                "displayName": path.stem,
                "id": "6c48a",
                "name": "texture",
                "userData": {
                    "wrapModeS": "clamp-to-edge",
                    "wrapModeT": "clamp-to-edge",
                    "minfilter": "linear",
                    "magfilter": "linear",
                    "mipfilter": "none",
                    "anisotropy": 0,
                    "isUuid": True,
                    "imageUuidOrDatabaseUri": asset_uuid,
                    "visible": False,
                },
                "ver": "1.0.22",
                "imported": True,
                "files": [".json"],
                "subMetas": {},
            },
            "f9941": {
                "importer": "sprite-frame",
                "uuid": f"{asset_uuid}@f9941",
                "displayName": path.stem,
                "id": "f9941",
                "name": "spriteFrame",
                "userData": {
                    "trimType": "auto",
                    "trimThreshold": 1,
                    "rotated": False,
                    "offsetX": 0,
                    "offsetY": 0,
                    "trimX": 0,
                    "trimY": 0,
                    "width": width,
                    "height": height,
                    "rawWidth": width,
                    "rawHeight": height,
                    "borderTop": top,
                    "borderBottom": bottom,
                    "borderLeft": left,
                    "borderRight": right,
                    "packable": True,
                    "pixelsToUnit": 100,
                    "pivotX": 0.5,
                    "pivotY": 0.5,
                    "meshType": 0,
                    "isUuid": True,
                    "imageUuidOrDatabaseUri": f"{asset_uuid}@6c48a",
                    "atlasUuid": "",
                    "vertices": sprite_vertices(width, height),
                },
                "ver": "1.0.12",
                "imported": True,
                "files": [".json"],
                "subMetas": {},
            },
        },
        "userData": {
            "type": "sprite-frame",
            "fixAlphaTransparencyArtifacts": False,
            "hasAlpha": True,
            "redirect": f"{asset_uuid}@6c48a",
        },
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def write_contact_sheet(paths: Iterable[Path], out: Path) -> None:
    paths = list(paths)
    if not paths:
        return
    cell_w, cell_h, label_h = 220, 200, 28
    cols = min(5, max(1, math.ceil(math.sqrt(len(paths)))))
    rows = math.ceil(len(paths) / cols)
    canvas = Image.new("RGB", (cols * cell_w, rows * cell_h), (238, 242, 246))
    draw = ImageDraw.Draw(canvas)
    resampling = getattr(Image, "Resampling", Image).LANCZOS
    for index, path in enumerate(paths):
        x, y = (index % cols) * cell_w, (index // cols) * cell_h
        draw.rounded_rectangle((x + 8, y + 8, x + cell_w - 8, y + cell_h - 8), radius=8, fill=(255, 255, 255), outline=(190, 204, 218))
        image = Image.open(path).convert("RGBA")
        image.thumbnail((cell_w - 28, cell_h - label_h - 22), resampling)
        px = x + (cell_w - image.width) // 2
        py = y + 14 + (cell_h - label_h - 22 - image.height) // 2
        canvas.paste(Image.new("RGB", image.size, (250, 250, 250)), (px, py))
        canvas.paste(image, (px, py), image)
        draw.text((x + 12, y + cell_h - label_h + 4), path.name[:28], fill=(40, 56, 70))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out)


def parse_border(value: str | None) -> tuple[int, int, int, int] | None:
    if not value:
        return None
    parts = [int(p) for p in value.replace(",", " ").split()]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("--border expects left,right,top,bottom")
    return parts[0], parts[1], parts[2], parts[3]


def main() -> None:
    parser = argparse.ArgumentParser(description="Generic AI image cutout and component splitter.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--split", choices=["none", "components"], default="none")
    parser.add_argument("--key", choices=["auto", "green", "magenta", "white", "none"], default="auto")
    parser.add_argument("--aggressive", action="store_true")
    parser.add_argument("--trim", action="store_true")
    parser.add_argument("--padding", type=int, default=8)
    parser.add_argument("--min-area", type=int, default=80)
    parser.add_argument("--prefix", default="asset")
    parser.add_argument("--target-size", type=parse_size)
    parser.add_argument("--contact-sheet", type=Path)
    parser.add_argument("--meta", choices=["none", "cocos"], default="none")
    parser.add_argument("--border", type=parse_border, help="Cocos nine-slice border: left,right,top,bottom")
    args = parser.parse_args()

    if not args.input.exists():
        raise SystemExit(f"Input not found: {args.input}")
    source = remove_key(Image.open(args.input), args.key, args.aggressive)
    written: list[Path] = []

    if args.split == "components":
        if not args.output_dir:
            raise SystemExit("--output-dir is required when --split components")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        components = connected_components(source, args.min_area)
        for index, component in enumerate(components, start=1):
            image = crop_component(source, component, args.padding)
            image = fit_canvas(image, args.target_size)
            output = args.output_dir / f"{args.prefix}_{index:02d}.png"
            image.save(output)
            if args.meta == "cocos":
                write_cocos_meta(output, args.border)
            written.append(output)
    else:
        if not args.output:
            raise SystemExit("--output is required for single output mode")
        image = trim_alpha(source, args.padding) if args.trim else source
        image = fit_canvas(image, args.target_size)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        image.save(args.output)
        if args.meta == "cocos":
            write_cocos_meta(args.output, args.border)
        written.append(args.output)

    if args.contact_sheet:
        write_contact_sheet(written, args.contact_sheet)
    print(json.dumps({"written": [str(path) for path in written]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
