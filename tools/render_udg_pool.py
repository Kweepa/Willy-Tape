#!/usr/bin/env python3
"""Render canonical UDG pools to a single preview PNG."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_room_compress import strip_overlays, tile_grid  # noqa: E402
from mkcatalogue import FLAG_CONVEYOR, FLAG_NASTY, FLAG_RAMP, gameplay_room_paths  # noqa: E402
from mkroom import TILE_HAZARD, parse_room  # noqa: E402
from udg_pool import (  # noqa: E402
    TILE_BELT,
    TILE_FLOOR,
    TILE_NASTY,
    TILE_PICKUP,
    TILE_RAMP,
    TILE_WALL,
    UDG_POOL_LIMITS,
    UdgPool,
    _pixel,
    audit_unused_udg_definitions,
    format_assignment_report,
    pairwise_spread_score,
)

try:
    from PIL import Image, ImageDraw
except ImportError:
    Image = None  # type: ignore

TYPE_LABELS = {
    TILE_FLOOR: "floor",
    TILE_WALL: "wall",
    TILE_NASTY: "nasty",
    TILE_RAMP: "ramp",
    TILE_BELT: "conveyor",
    TILE_PICKUP: "pickup",
}

GROUP_ORDER = (
    TILE_FLOOR,
    TILE_WALL,
    TILE_NASTY,
    TILE_RAMP,
    TILE_BELT,
    TILE_PICKUP,
)

DEFAULT_OVERRIDES = (
    Path(__file__).resolve().parent.parent / "bake" / "udg_canonical_overrides.json"
)


def room_flags(room: dict) -> int:
    grid = tile_grid(room["tilemap"])
    base, ramp, conv, _pickup = strip_overlays(grid)
    flags = 0
    if TILE_HAZARD in base:
        flags |= FLAG_NASTY
    if ramp:
        flags |= FLAG_RAMP
    if conv:
        flags |= FLAG_CONVEYOR
    return flags


def load_rooms(rooms_dir: Path) -> list[dict]:
    rooms: list[dict] = []
    for p in gameplay_room_paths(rooms_dir):
        rooms.append(parse_room(p.read_text(encoding="utf-8"), source=p))
    rooms.sort(key=lambda r: r["id"])
    return rooms


def blit_udg(
    img: Image.Image,
    chunk: bytes,
    x0: int,
    y0: int,
    *,
    scale: int,
    ink: tuple[int, int, int],
    paper: tuple[int, int, int],
) -> None:
    chunk = bytes(chunk[:8].ljust(8, b"\x00"))
    for row in range(8):
        for col in range(8):
            colour = ink if _pixel(chunk, row, col) else paper
            for dy in range(scale):
                for dx in range(scale):
                    img.putpixel((x0 + col * scale + dx, y0 + row * scale + dy), colour)


def render_preview(
    pool: UdgPool,
    *,
    scale: int = 8,
    item_gap: int = 20,
    group_gap: int = 16,
    margin: int = 12,
    label_h: int = 18,
    caption_h: int = 28,
) -> Image.Image:
    if Image is None:
        raise RuntimeError("Pillow required (pip install pillow)")

    ink = (240, 240, 240)
    paper = (32, 32, 48)
    label_bg = (20, 20, 28)
    group_bg = (28, 28, 40)

    sprite_px = 8 * scale
    cell_w = sprite_px + item_gap
    groups: list[tuple[int, str, list[bytes], list[int]]] = []
    max_row_w = 0
    for tile_type in GROUP_ORDER:
        chunks = pool.canonical.get(tile_type, [])
        sources = pool.canonical_source.get(tile_type, [])
        cap = pool.selection_limit(tile_type)
        pool_cap = pool.pool_limit(tile_type)
        row: list[bytes] = []
        row_sources: list[int] = []
        for i in range(cap):
            if i < len(chunks):
                row.append(chunks[i])
                row_sources.append(sources[i] if i < len(sources) else -1)
            else:
                row.append(b"\x00" * 8)
                row_sources.append(-1)
        spread = pairwise_spread_score([c for c in row if c != b"\x00" * 8])
        default = UDG_POOL_LIMITS[tile_type]
        cap_label = f"{cap}/{pool_cap}" if pool_cap > default else str(cap)
        label = f"{TYPE_LABELS[tile_type]} ({cap_label})  spread={spread}"
        row_w = len(row) * cell_w - item_gap
        max_row_w = max(max_row_w, row_w)
        groups.append((tile_type, label, row, row_sources))

    width = margin * 2 + max_row_w
    group_h = label_h + sprite_px + caption_h
    height = margin * 2 + len(groups) * group_h + (len(groups) - 1) * group_gap

    img = Image.new("RGB", (width, height), label_bg)
    draw = ImageDraw.Draw(img)

    y = margin
    for _tile_type, label, row, row_sources in groups:
        x0 = margin
        draw.rectangle(
            (margin - 4, y - 2, width - margin + 4, y + group_h - 4),
            fill=group_bg,
        )
        draw.text((x0, y), label, fill=(180, 200, 255))
        y += label_h
        for i, (chunk, src) in enumerate(zip(row, row_sources)):
            x = x0 + i * cell_w
            blit_udg(img, chunk, x, y, scale=scale, ink=ink, paper=paper)
            draw.text((x, y + sprite_px + 2), f"[{i}]", fill=(140, 140, 160))
            if src >= 0:
                draw.text((x, y + sprite_px + 14), f"r{src}", fill=(200, 180, 120))
        y += sprite_px + caption_h + group_gap

    return img


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rooms",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "rooms",
    )
    parser.add_argument(
        "-o",
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "bake" / "udg_canonical_preview.png",
    )
    parser.add_argument(
        "--assignments",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "bake" / "udg_canonical_assignments.txt",
    )
    parser.add_argument(
        "--overrides",
        type=Path,
        default=DEFAULT_OVERRIDES,
        help="JSON with per-type include_rooms / exclude_rooms (optional)",
    )
    parser.add_argument("--scale", type=int, default=8)
    parser.add_argument("--gap", type=int, default=20, help="Horizontal space between UDGs")
    args = parser.parse_args()

    rooms = load_rooms(args.rooms)
    flags_by_rid = {r["id"]: room_flags(r) for r in rooms}
    overrides_path = args.overrides if args.overrides.is_file() else None
    pool = UdgPool()
    pool.build(rooms, flags_by_rid=flags_by_rid, overrides_path=overrides_path)

    unused_udg = audit_unused_udg_definitions(rooms)
    if unused_udg:
        pool.warnings.extend(unused_udg)

    img = render_preview(pool, scale=args.scale, item_gap=args.gap)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out)
    print(f"Wrote {args.out} ({img.width}x{img.height})")

    report = format_assignment_report(pool)
    args.assignments.write_text(report, encoding="utf-8")
    print(f"Wrote {args.assignments}")
    print()
    print(report, end="")

    if overrides_path:
        print(f"(applied overrides from {overrides_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
