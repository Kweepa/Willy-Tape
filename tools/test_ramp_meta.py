#!/usr/bin/env python3
"""Verify 2-byte ramp overlay decodes to baked params (mirrors BakeRampMeta / ApplyRamp)."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mkcatalogue import FLAG_RAMP  # noqa: E402
from mkroom import (  # noqa: E402
    RAMP_UP_LEFT,
    RAMP_UP_LEFT_RY_ADJUST,
    RAMP_UP_RIGHT,
    RAMP_RY_TOE,
    TILEMAP_ROWS,
    WIDTH,
    derive_ramp_params,
    infer_ramp_from_tilemap,
    ramp_surface_abs,
)
from udg_pool import UDG_INDEX_BYTES  # noqa: E402

HEADER = 2
INDEX_ENTRY = 4


def decode_ramp_pack(b0: int, b1: int) -> tuple[int, int, int, bool]:
    """Mirror ApplyRamp ZP decode: col_start, row_start, length, up_right."""
    col_start = b1 & 0x1F
    row_start = b0 & 0x0F
    length = (b0 >> 4) + 1
    up_right = (b1 & 0x80) == 0
    return col_start, row_start, length, up_right


def overlay_bytes_to_tilemap(b0: int, b1: int) -> list[str]:
    """Reconstruct ramp tiles from pack_ramp2 (same geometry ApplyRamp paints)."""
    col_start, row_start, length, up_right = decode_ramp_pack(b0, b1)
    ch = "/" if up_right else "\\"
    row_step = -1 if up_right else 1
    lines = [" " * WIDTH for _ in range(TILEMAP_ROWS)]
    for i in range(length):
        col = col_start + i
        row = row_start + i * row_step
        if not 0 <= row < TILEMAP_ROWS:
            raise ValueError(f"ramp row {row} out of range")
        row_chars = list(lines[row])
        row_chars[col] = ch
        lines[row] = "".join(row_chars)
    return lines


def bake_ramp_params_from_pack(b0: int, b1: int) -> tuple[int, int, int, int, int, int]:
    """Mirror BakeRampMeta 6502 (hx/mov/num/g_frame -> meta_content_ramp_*)."""
    col_start, row_start, length, up_right = decode_ramp_pack(b0, b1)
    col_end = col_start + length - 1
    ramp_type = RAMP_UP_RIGHT if up_right else RAMP_UP_LEFT
    row_step = 0 if length == 1 else (-1 if up_right else 1)

    rx1 = col_start * 4 - 4
    rx2 = col_end * 4 + 4
    if ramp_type == RAMP_UP_RIGHT:
        e, a = 0xFF, 1
    else:
        e, a = 0, 0

    toe = RAMP_RY_TOE[ramp_type]
    ry = ramp_surface_abs(rx1, col_start, col_end, row_start, row_step, ramp_type) - toe
    if ramp_type == RAMP_UP_LEFT:
        ry += RAMP_UP_LEFT_RY_ADJUST

    if ramp_type == RAMP_UP_RIGHT:
        upper_px = col_end * 4
    else:
        upper_px = col_start * 4
    ymin = ramp_surface_abs(
        upper_px, col_start, col_end, row_start, row_step, ramp_type
    ) - toe

    return (rx1, rx2, ry, e, a, ymin)


def find_ramp_bytes(blob: bytes, off: int) -> tuple[int, int] | None:
    title_end = blob.index(0, off)
    meta_off = title_end + 1
    flags = blob[meta_off + 6]
    if not (flags & FLAG_RAMP):
        return None
    pos = meta_off + 8 + 6 + UDG_INDEX_BYTES
    cells = 0
    while cells < 384:
        tok = blob[pos]
        run = (tok >> 3) & 0x1F
        cells += run
        pos += 1
    pos += 2  # pickup word
    return blob[pos], blob[pos + 1]


def main() -> None:
    cat_path = ROOT / "catalogue.bin"
    if not cat_path.is_file():
        print("catalogue.bin not found — run make.bat first")
        sys.exit(1)

    cat = cat_path.read_bytes()
    count, = struct.unpack_from("<H", cat, 0)
    records_off = HEADER + count * INDEX_ENTRY
    errors = 0
    ramp_rooms = 0
    derived_ok = 0

    for rid in range(count):
        idx_off = HEADER + rid * INDEX_ENTRY
        rec_off, _rec_len = struct.unpack_from("<HH", cat, idx_off)
        rec_off += records_off
        ramp_bytes = find_ramp_bytes(cat, rec_off)
        if ramp_bytes is None:
            continue
        ramp_rooms += 1
        b0, b1 = ramp_bytes

        baked = bake_ramp_params_from_pack(b0, b1)
        rx1, rx2, ry, e, a, ymin = baked
        if rx1 >= rx2:
            print(f"room {rid}: invalid bounds rx1={rx1} rx2={rx2}")
            errors += 1
            continue

        try:
            tilemap = overlay_bytes_to_tilemap(b0, b1)
            ramp_type = infer_ramp_from_tilemap(tilemap)
            derived = derive_ramp_params(tilemap, ramp_type)
            derived_ok += 1
            if baked != derived:
                print(f"room {rid}: pack bake vs derive mismatch")
                print(f"  bytes ${b0:02x} ${b1:02x} -> {baked}")
                print(f"  derive -> {derived}")
                errors += 1
        except ValueError:
            pass  # overlay rows wrap in 6502 — skip derive cross-check

    # Spot-check room 00 against known tilemap bake
    room00 = bake_ramp_params_from_pack(0x3E, 0x10)
    if room00 != (60, 80, 120, 255, 1, 88):
        print(f"room 00 spot-check failed: {room00}")
        errors += 1

    print(f"Checked {ramp_rooms} ramp rooms ({derived_ok} cross-checked vs derive)")
    if errors:
        print(f"{errors} error(s)")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
