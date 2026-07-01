#!/usr/bin/env python3
"""Estimate tilemap compression sizes for JSW room data."""

from __future__ import annotations

import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mkroom import (  # noqa: E402
    GUARDIAN_RECORD_BYTES,
    MAX_GUARDIANS,
    RAMP_NONE,
    RAMP_UP_LEFT,
    RAMP_UP_RIGHT,
    TILEMAP_ROWS,
    TILE_CHAR_MAP,
    TILE_CONVEYOR,
    TILE_EMPTY,
    TILE_HAZARD,
    TILE_PLATFORM,
    TILE_RAMP,
    TILE_SOLID,
    WIDTH,
    derive_ramp_bounds,
    parse_room,
    parse_tile_char,
)

ROOT = Path(__file__).resolve().parent.parent
ROOMS = sorted(ROOT.glob("rooms/room*.txt"))
CELLS = TILEMAP_ROWS * WIDTH  # 384 gameplay cells


@dataclass
class RoomStats:
    rid: int
    title_len: int
    guardians: int
    has_pickup: bool
    has_ramp: bool
    has_conveyor: bool
    belt: int
    tile_types_used: set[int]
    custom_udg_bytes: int


def tile_grid(tilemap: list[str]) -> list[int]:
    """Return 384 cell types 0-6 (+ pickup as 6)."""
    out: list[int] = []
    for row in range(TILEMAP_ROWS):
        line = tilemap[row]
        for col in range(WIDTH):
            ch = line[col] if col < len(line) else " "
            if ch == "+":
                out.append(6)
            else:
                out.append(parse_tile_char(ch))
    return out


def strip_overlays(grid: list[int]) -> tuple[list[int], dict | None, dict | None]:
    """Remove ramp/conveyor tiles; pickup becomes empty. Return base grid + overlays."""
    base = list(grid)
    pickup: tuple[int, int] | None = None

    for i, t in enumerate(base):
        if t == 6:
            base[i] = TILE_EMPTY
            pickup = (i % WIDTH, i // WIDTH)
        elif t == TILE_RAMP:
            base[i] = TILE_EMPTY
        elif t == TILE_CONVEYOR:
            base[i] = TILE_EMPTY

    ramp_info = extract_ramp_overlay(grid)
    conv_info = extract_conveyor_overlay(grid)
    return base, ramp_info, conv_info, pickup


def _ramp_tilemap_from_cells(cells: list[tuple[int, int]], ramp_type: int) -> list[str]:
    """Build minimal tilemap with / or \\ at ramp cells for derive_ramp_bounds."""
    ch = "/" if ramp_type == RAMP_UP_RIGHT else "\\"
    lines = [" " * WIDTH for _ in range(TILEMAP_ROWS)]
    for col, row in cells:
        row_chars = list(lines[row])
        row_chars[col] = ch
        lines[row] = "".join(row_chars)
    return lines


def extract_ramp_overlay(grid: list[int]) -> dict | None:
    cells: list[tuple[int, int]] = []
    for i, t in enumerate(grid):
        if t != TILE_RAMP:
            continue
        col, row = i % WIDTH, i // WIDTH
        cells.append((col, row))
    if not cells:
        return None

    by_col = {col: row for col, row in cells}
    col_start = min(by_col)
    col_end = max(by_col)
    row_start = by_col[col_start]
    if col_end == col_start:
        ramp_type = RAMP_UP_RIGHT
    else:
        row_step_geom = by_col[col_start + 1] - row_start
        if row_step_geom == -1:
            ramp_type = RAMP_UP_RIGHT
        elif row_step_geom == 1:
            ramp_type = RAMP_UP_LEFT
        else:
            raise ValueError(
                f"invalid ramp row step {row_step_geom} at col {col_start}"
            )

    tilemap = _ramp_tilemap_from_cells(cells, ramp_type)
    col_start, col_end, row_start, row_step = derive_ramp_bounds(tilemap, ramp_type)
    length = col_end - col_start + 1
    direction = 0 if ramp_type == RAMP_UP_RIGHT else 1
    return {
        "x": col_start,
        "y": row_start,
        "length": length,
        "direction": direction,
        "row_step": row_step,
    }


def extract_conveyor_overlay(grid: list[int]) -> dict | None:
    runs: list[tuple[int, int, int]] = []  # row, col_start, length
    for row in range(TILEMAP_ROWS):
        col = 0
        while col < WIDTH:
            i = row * WIDTH + col
            if grid[i] != TILE_CONVEYOR:
                col += 1
                continue
            start = col
            while col < WIDTH and grid[row * WIDTH + col] == TILE_CONVEYOR:
                col += 1
            runs.append((row, start, col - start))
    if not runs:
        return None
    if len(runs) > 1:
        # JSW rooms typically have one belt row; keep longest run
        runs.sort(key=lambda r: -r[2])
    row, x, length = runs[0]
    return {"x": x, "y": row, "length": length}


def grid_to_tilemap(grid: list[int]) -> list[str]:
    rev = {
        TILE_EMPTY: " ",
        TILE_PLATFORM: "F",
        TILE_SOLID: "W",
        TILE_HAZARD: "*",
        TILE_RAMP: "/",
        TILE_CONVEYOR: ">",
    }
    lines: list[str] = []
    for row in range(TILEMAP_ROWS):
        chars = []
        for col in range(WIDTH):
            t = grid[row * WIDTH + col]
            if t == 6:
                chars.append("+")
            elif t == TILE_RAMP:
                chars.append("/")
            else:
                chars.append(rev.get(t, " "))
        lines.append("".join(chars))
    return lines


def rle_unpack(tokens: list[int], nbytes: int = CELLS) -> list[int]:
    """Inverse of rle_pack — expand tokens to cell types."""
    out: list[int] = []
    for tok in tokens:
        run = (tok >> 3) & 0x1F
        val = tok & 7
        out.extend([val] * run)
    if len(out) != nbytes:
        raise ValueError(f"rle_unpack: got {len(out)} cells, expected {nbytes}")
    return out


def rle_pack(values: list[int], order: str = "row") -> list[int]:
    """8-bit tokens: 5-bit run length (1-31), 3-bit value (0-7)."""
    if order == "col":
        seq = []
        for col in range(WIDTH):
            for row in range(TILEMAP_ROWS):
                seq.append(values[row * WIDTH + col])
        values = seq
    out: list[int] = []
    i = 0
    n = len(values)
    while i < n:
        val = values[i] & 7
        run = 1
        while run < 31 and i + run < n and values[i + run] == val:
            run += 1
        out.append((run << 3) | val)
        i += run
    return out


def raw_bits(values: list[int], bits: int) -> int:
    """Pack values using `bits` per cell."""
    total_bits = len(values) * bits
    return (total_bits + 7) // 8


def pack_ramp2(info: dict) -> bytes:
    """2-byte ramp: byte0 (len-1)<<4|y, byte1 (dir<<7)|x."""
    x = info["x"] & 0x1F
    y = info["y"] & 0x0F
    length = info["length"]
    if not 1 <= length <= 16:
        raise ValueError(f"ramp length {length} out of range 1-16")
    length_n = (length - 1) & 0x0F
    direction = info["direction"] & 1
    b0 = (length_n << 4) | y
    b1 = (direction << 7) | x
    return bytes([b0, b1])


def pack_conveyor2(info: dict, velocity: int) -> bytes:
    """2-byte conveyor: byte0 (len-1)<<4|y, byte1 (vel<<6)|x.

    vel is belt+1 so runtime can decode with ``dex`` after extracting bits 6-7:
    packed 0 -> belt $ff (-1), packed 1 -> belt $00, packed 2 -> belt $01.
    """
    vel_map = {-1: 0, 0: 1, 1: 2}
    vel = vel_map.get(velocity, 1) & 3
    x = info["x"] & 0x1F
    y = info["y"] & 0x0F
    length = info["length"]
    if not 1 <= length <= 16:
        raise ValueError(f"conveyor length {length} out of range 1-16")
    length_n = (length - 1) & 0x0F
    b0 = (length_n << 4) | y
    b1 = (vel << 6) | x
    return bytes([b0, b1])


# Legacy names used by mkcatalogue imports.
pack_ramp3 = pack_ramp2
pack_conveyor3 = pack_conveyor2


def count_custom_udg(room: dict) -> int:
    total = 0
    for i, udg in enumerate(room["tileudg"]):
        if any(udg):
            total += 8
    if room.get("itemudg_defined"):
        total += 8
    return total


def meta_fixed_bytes(room: dict, pickup: tuple[int, int] | None) -> int:
    """Minimal per-room metadata excluding tilemap, UDGs, guardians, sprites."""
    # conn(4) + spawn(2) + border/bg(1) + tile_colors(6) + guardian_count(1)
    # + flags(1) + pickup(1 if present) + title index would be 1 byte in shared table
    n = 4 + 2 + 1 + 6 + 1 + 1
    if pickup:
        n += 1
    if room.get("rope"):
        n += 1  # rope params elsewhere
    if room.get("arrow"):
        n += 5  # y, x, v, sound approx
    return n


def guardian_data_bytes(room: dict) -> int:
    return len(room["guardians"]) * GUARDIAN_RECORD_BYTES


def analyze_room(path: Path) -> dict:
    room = parse_room(path.read_text(encoding="utf-8"), source=path)
    grid = tile_grid(room["tilemap"])
    base, ramp, conv, pickup = strip_overlays(grid)

    schemes = {
        "raw384_full": len(grid),  # one byte per cell, types 0-6
        "raw96_base2bit": raw_bits(base, 2),  # types 0-3 only
        "raw144_base3bit": raw_bits(base, 3),  # if we kept 0-7
        "rle_full_row": len(rle_pack(grid, "row")),
        "rle_full_col": len(rle_pack(grid, "col")),
        "rle_base_row": len(rle_pack(base, "row")),
        "rle_base_col": len(rle_pack(base, "col")),
    }

    overlays = 0
    if ramp:
        overlays += 3
    if conv:
        overlays += 3

    meta = meta_fixed_bytes(room, pickup)
    udg = count_custom_udg(room)
    gdata = guardian_data_bytes(room)

    return {
        "id": room["id"],
        "schemes": schemes,
        "overlays": overlays,
        "meta": meta,
        "udg": udg,
        "gdata": gdata,
        "guardians": len(room["guardians"]),
        "title_len": len(room["title"]),
        "has_ramp": ramp is not None,
        "has_conv": conv is not None,
        "has_pickup": pickup is not None,
    }


def summarize(values: list[int]) -> str:
    return (
        f"min={min(values)} avg={statistics.mean(values):.1f} "
        f"med={statistics.median(values):.0f} max={max(values)} "
        f"total={sum(values)}"
    )


def main() -> None:
    rows = [analyze_room(p) for p in ROOMS if p.name != "room62.txt"]
    n = len(rows)

    print("=== JSW room tilemap compression audit ===")
    print(f"Rooms analysed: {n} (excluding room62 logo stub)")
    print(f"Gameplay cells per room: {CELLS} ({WIDTH}x{TILEMAP_ROWS})")
    print()

    print("Overlay prevalence:")
    print(f"  ramp:     {sum(r['has_ramp'] for r in rows)}/{n} rooms (+3 B when present)")
    print(f"  conveyor: {sum(r['has_conv'] for r in rows)}/{n} rooms (+3 B when present)")
    print(f"  pickup:   {sum(r['has_pickup'] for r in rows)}/{n} rooms (+1 B in meta)")
    print()

    print("Tilemap encoding sizes (bytes per room):")
    for key in rows[0]["schemes"]:
        vals = [r["schemes"][key] for r in rows]
        print(f"  {key:18s}: {summarize(vals)}")
    print()

    overlay_vals = [r["overlays"] for r in rows]
    print(f"Ramp+conveyor overlays: {summarize(overlay_vals)}")
    print()

    # Combined schemes user asked about
    combos = {
        "A: RLE full map (row)": lambda r: r["schemes"]["rle_full_row"],
        "B: RLE base 0-3 (row) + overlays": lambda r: r["schemes"]["rle_base_row"] + r["overlays"],
        "C: RLE base 0-3 (col) + overlays": lambda r: r["schemes"]["rle_base_col"] + r["overlays"],
        "D: raw 2-bit base + overlays": lambda r: r["schemes"]["raw96_base2bit"] + r["overlays"],
        "E: RLE full (col)": lambda r: r["schemes"]["rle_full_col"],
    }
    print("Combined tilemap schemes:")
    for name, fn in combos.items():
        vals = [fn(r) for r in rows]
        print(f"  {name:36s}: {summarize(vals)}")
    print()

    meta_vals = [r["meta"] for r in rows]
    udg_vals = [r["udg"] for r in rows]
    gdata_vals = [r["gdata"] for r in rows]
    print("Other per-room data (current text-derived):")
    print(f"  minimal meta (no title):  {summarize(meta_vals)}")
    print(f"  custom UDG bytes:         {summarize(udg_vals)}")
    print(f"  guardian AoS data:        {summarize(gdata_vals)}")
    print()

    # Title table: 61 unique titles
    titles = sorted({parse_room(p.read_text(), p)["title"] for p in ROOMS if p.name != "room62.txt"})
    title_table = sum(len(t) + 1 for t in titles)  # null-terminated
    print(f"Shared title string table: {title_table} bytes ({len(titles)} titles)")
    print()

    # Full tape block estimates
    print("=== Estimated per-room tape block (excl. guardian sprites) ===")
    print("Assumes: 1-byte title index, global 4KB guardian frame pool loaded once")
    print()

    for scheme_name, tile_fn in [
        ("B: RLE base row + overlays", lambda r: r["schemes"]["rle_base_row"] + r["overlays"]),
        ("D: 2-bit raw base + overlays", lambda r: r["schemes"]["raw96_base2bit"] + r["overlays"]),
        ("A: RLE full row (no split)", lambda r: r["schemes"]["rle_full_row"]),
    ]:
        totals = []
        for r in rows:
            block = (
                1  # title index
                + r["meta"]
                + tile_fn(r)
                + r["gdata"]
                + r["udg"]
            )
            totals.append(block)
        print(f"  {scheme_name}:")
        print(f"    per room: {summarize(totals)}")
        print(f"    all {n} rooms: {sum(totals)} bytes ({sum(totals)/1024:.1f} KB)")

    print()
    print("=== Compare to current in-RAM room image ===")
    print("  screen tilemap only (16 rows baked): 384 B")
    print("  meta tail header: 38 B (+ guardian AoS 60 B, flags)")
    print("  tile colours in image: 6 B")
    print("  per-room UDGs in image: up to 56 B (+ item 8)")
    print("  (full PRG also carries 288 B guardian sprites + 256 B Willy + code prefix)")


if __name__ == "__main__":
    main()
