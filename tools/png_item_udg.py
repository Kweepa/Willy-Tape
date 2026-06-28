#!/usr/bin/env python3
"""Extract @itemudg lines from a palette PNG of 8x8 item sprites."""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

# Default names for bake/newitems.png (row, col) -> description
NEWITEMS_NAMES: dict[tuple[int, int], str] = {
    (0, 0): "medicine bottle",
    (0, 2): "warning triangle",
    (0, 4): "three bars",
    (0, 6): "steaming mug",
    (0, 8): "teapot",
    (0, 10): "flame / steam",
    (1, 1): "leaf",
    (1, 3): "crown",
    (1, 5): "bicycle",
    (1, 7): "snail",
    (1, 9): "heart",
    (2, 0): "wrench",
    (2, 2): "skull",
    (2, 4): "space invader",
    (2, 6): "padlock",
    (2, 8): "wine glass",
    (2, 10): "bomb",
}


def find_red_index(im: Image.Image) -> int:
    """Palette index with the strongest red channel (R - max(G,B))."""
    palette = im.getpalette()
    if not palette:
        raise ValueError("image has no palette")
    best_index = 0
    best_score = -1
    for i in range(len(palette) // 3):
        r, g, b = palette[i * 3 : i * 3 + 3]
        score = r - max(g, b)
        if score > best_score:
            best_score = score
            best_index = i
    if best_score < 1:
        raise ValueError("no red ink colour found in palette")
    return best_index


def tile_to_udg_bytes(im: Image.Image, tx: int, ty: int, ink_idx: int) -> bytes:
    px = im.load()
    x0, y0 = tx * 8, ty * 8
    out = bytearray(8)
    for y in range(8):
        byte = 0
        for x in range(8):
            if px[x0 + x, y0 + y] == ink_idx:
                byte |= 1 << (7 - x)
        out[y] = byte
    return bytes(out)


def load_names(path: Path | None) -> dict[tuple[int, int], str]:
    if path is None:
        return {}
    names: dict[tuple[int, int], str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        parts = line.split(None, 2)
        if len(parts) < 3:
            raise ValueError(f"names line needs 'row col description': {line!r}")
        row, col = int(parts[0]), int(parts[1])
        names[(row, col)] = parts[2]
    return names


def format_itemudg_line(bs: bytes, description: str | None) -> str:
    parts = ",".join(str(b) for b in bs)
    if description:
        return f"@itemudg {parts} ; {description}"
    return f"@itemudg {parts}"


def extract_item_udgs(
    path: Path,
    ink_idx: int | None = None,
    names: dict[tuple[int, int], str] | None = None,
) -> list[str]:
    if Image is None:
        raise RuntimeError("Pillow required (pip install pillow)")
    im = Image.open(path)
    if im.mode != "P":
        raise ValueError(f"{path}: expected palette PNG (P mode), got {im.mode}")
    if im.width % 8 or im.height % 8:
        raise ValueError(f"{path}: size must be a multiple of 8 pixels")

    ink = ink_idx if ink_idx is not None else find_red_index(im)
    cols, rows = im.width // 8, im.height // 8
    if names is None:
        names = {}

    lines: list[str] = []
    for ty in range(rows):
        for tx in range(cols):
            bs = tile_to_udg_bytes(im, tx, ty, ink)
            if not any(bs):
                continue
            desc = names.get((ty, tx))
            lines.append(format_itemudg_line(bs, desc))
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", type=Path, help="palette PNG of 8x8 item sprites")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="write lines to this file (default: stdout)",
    )
    parser.add_argument(
        "--ink-index",
        type=int,
        default=None,
        help="palette index for ink pixels (default: auto-detect red)",
    )
    parser.add_argument(
        "--names",
        type=Path,
        help="optional names file: 'row col description' per line",
    )
    parser.add_argument(
        "--newitems",
        action="store_true",
        help="use built-in names for bake/newitems.png",
    )
    args = parser.parse_args()

    names = load_names(args.names)
    if args.newitems:
        names = {**NEWITEMS_NAMES, **names}

    lines = extract_item_udgs(args.png, ink_idx=args.ink_index, names=names)
    text = "\n".join(lines) + ("\n" if lines else "")
    if args.output:
        args.output.write_text(text, encoding="utf-8")
        print(f"wrote {len(lines)} @itemudg lines to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
