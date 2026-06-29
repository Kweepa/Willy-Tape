#!/usr/bin/env python3
"""Verify catalogue room RLE decode matches mkroom tile grid."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_room_compress import rle_pack, rle_unpack, strip_overlays, tile_grid  # noqa: E402
from mkcatalogue import (  # noqa: E402
    FLAG_ARROW,
    FLAG_CONVEYOR,
    FLAG_NASTY,
    FLAG_RAMP,
)
from udg_pool import UDG_INDEX_BYTES  # noqa: E402
from mkroom import TILE_CHR_BASE, TILEMAP_ROWS, WIDTH, parse_room  # noqa: E402

HEADER = 2
INDEX_ENTRY = 4


def parse_record(blob: bytes, off: int) -> dict:
    title_end = blob.index(0, off)
    meta_off = title_end + 1
    meta = blob[meta_off : meta_off + 8]
    flags = meta[6]
    pos = meta_off + 8 + 6  # meta8 + tile_colors
    pos += UDG_INDEX_BYTES
    rle_start = pos
    pos = rle_start
    cells: list[int] = []
    while len(cells) < 384:
        tok = blob[pos]
        run = (tok >> 3) & 0x1F
        val = tok & 7
        cells.extend([val] * run)
        pos += 1
    pos += 2  # pickup screen offset word ($ffff = none)
    if flags & FLAG_RAMP:
        pos += 2
    if flags & FLAG_CONVEYOR:
        pos += 2
    if flags & FLAG_ARROW:
        pos += 5
    pos += 1  # guardian count
    return {
        "meta": meta,
        "tile_colors": blob[meta_off + 8 : meta_off + 14],
        "title": blob[off:title_end].decode("ascii"),
        "types": cells,
        "next": pos,
    }


def main() -> None:
    cat = (ROOT / "catalogue.bin").read_bytes()
    rooms_dir = ROOT / "rooms"
    count, = struct.unpack_from("<H", cat, 0)
    records_off = HEADER + count * INDEX_ENTRY
    errors = 0
    for rid in range(count):
        idx_off = HEADER + rid * INDEX_ENTRY
        rec_off, rec_len = struct.unpack_from("<HH", cat, idx_off)
        rec = parse_record(cat, records_off + rec_off)
        room_path = rooms_dir / f"room{rid:02d}.txt"
        if not room_path.is_file():
            continue
        room = parse_room(room_path.read_text(encoding="utf-8"), source=room_path)
        grid, _, _, _ = strip_overlays(tile_grid(room["tilemap"]))
        if grid != rec["types"]:
            print(f"room {rid}: RLE mismatch")
            errors += 1
        else:
            print(f"room {rid}: OK ({rec['title']})")
    if errors:
        raise SystemExit(errors)


if __name__ == "__main__":
    main()
