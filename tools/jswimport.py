#!/usr/bin/env python3
"""Import JSW SkoolKit room data into VIC-20 roomNN.txt files."""

from __future__ import annotations

import argparse
import random
import re
import sys
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = Path(__file__).resolve().parent / "jswcache"
ROOMS_DIR = ROOT / "rooms"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mkroom import tile_types_in_tilemap  # noqa: E402

SRC_W = 32
SRC_H = 16
DST_W = 24
DROP_COLS = SRC_W - DST_W

EXISTING = {21, 27, 28, 29, 30, 33, 34, 35}
ROOM_BASE = 49152
ENTITY_BASE = 40960
ITEM_BASE = 41984
ITEM_BASE2 = 42240
GUARDIAN_GFX = 43776
GUARDIAN_GFX_BYTES = 49152 - GUARDIAN_GFX  # through byte before room data at 49152
ATTR_BASE = 24064
GFX_PAGE_BASE = 171

# Tile importance when choosing columns to drop (lower = drop first).
TILE_DROP_WEIGHT = (0, 1, 8, 4)  # empty, floor, wall, nasty
INK_NAMES = ("BLK", "BLU", "RED", "PUR", "GRN", "CYN", "YEL", "WHT")
ITEM_INK_COLORS = ("BLU", "RED", "PUR", "GRN", "CYN", "YEL")
TILE_CHARS = (" ", "F", "W", "*")

FRAME_MASK_COUNT = {0: 1, 1: 2, 3: 4, 7: 8}

DEFB_RE = re.compile(
    r"DEFB\s+((?:%[01]+|\$[0-9A-Fa-f]+|\d+)(?:\s*,\s*(?:%[01]+|\$[0-9A-Fa-f]+|\d+))*)",
    re.I,
)
SKOOL_ROW_RE = re.compile(
    r'<td class="address-1"><span id="(\d+)"></span>\d+</td>\s*'
    r'<td class="instruction">(DEFB|DEFM|DEFW)\s+([^<]+)</td>',
    re.I,
)


def parse_byte(tok: str) -> int:
    tok = tok.strip()
    if tok.startswith("%"):
        return int(tok[1:], 2) & 0xFF
    if tok.startswith("$"):
        return int(tok[1:], 16) & 0xFF
    return int(tok) & 0xFF


def parse_defb_line(line: str) -> list[int]:
    m = DEFB_RE.search(line)
    if not m:
        return []
    return [parse_byte(p) for p in m.group(1).split(",")]


def fetch_html(addr: int) -> str:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{addr}.html"
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    url = f"https://skoolkit.ca/disassemblies/jet_set_willy/asm/{addr}.html"
    print(f"fetch {url}")
    with urllib.request.urlopen(url, timeout=60) as resp:
        text = resp.read().decode("utf-8", errors="replace")
    path.write_text(text, encoding="utf-8")
    return text


def instruction_to_bytes(kind: str, args: str) -> bytes:
    kind = kind.upper()
    if kind == "DEFB":
        return bytes(parse_defb_line(f"DEFB {args}"))
    if kind == "DEFM":
        m = re.search(r'"([^"]*)"', args)
        return m.group(1).encode("ascii", errors="replace") if m else b""
    if kind == "DEFW":
        return (int(args.strip()) & 0xFFFF).to_bytes(2, "little")
    return b""


def extract_bytes_from_html(html: str, start: int, count: int) -> bytes:
    """Parse DEFB/DEFM/DEFW bytes from a SkoolKit HTML page by address."""
    mem = bytearray(count)
    end = start + count
    for m in SKOOL_ROW_RE.finditer(html):
        addr = int(m.group(1))
        data = instruction_to_bytes(m.group(2), m.group(3))
        for i, b in enumerate(data):
            off = addr + i
            if start <= off < end:
                mem[off - start] = b
    return bytes(mem)


def load_blob(addr: int, size: int) -> bytes:
    html = fetch_html(addr)
    return extract_bytes_from_html(html, addr, size)


def decode_layout(data: bytes) -> list[list[int]]:
    """128 bytes -> 32x16 grid, values 0-3 (2 bits per cell)."""
    grid = [[0] * SRC_W for _ in range(SRC_H)]
    for row in range(SRC_H):
        for byte_i in range(8):
            b = data[row * 8 + byte_i] if row * 8 + byte_i < len(data) else 0
            for pair in range(4):
                col = byte_i * 4 + pair
                shift = 6 - pair * 2
                grid[row][col] = (b >> shift) & 3
    return grid


def attr_addr_to_cell(addr: int) -> tuple[int, int]:
    off = addr - ATTR_BASE
    return off % SRC_W, off // SRC_W


def parse_room_block(data: bytes) -> dict:
    layout = data[0:128]
    title = data[128:160].split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
    tiles = [data[160 + i * 9 : 160 + (i + 1) * 9] for i in range(6)]
    item_udg = data[225:233]
    exits = list(data[233:237])
    entities: list[tuple[int, int]] = []
    off = 240
    while off + 1 < len(data):
        a, b = data[off], data[off + 1]
        if a == 255 and b == 0:
            break
        entities.append((a, b))
        off += 2

    conv_dir = data[214]
    conv_addr = data[215] | (data[216] << 8)
    conv_len = data[217]
    ramp_dir = data[218]
    ramp_addr = data[219] | (data[220] << 8)
    ramp_len = data[221]
    border = data[222]

    return {
        "layout": layout,
        "title": title or "Untitled",
        "tiles": tiles,
        "item_udg": item_udg,
        "exits": exits,
        "entities": entities,
        "conv_dir": conv_dir,
        "conv_addr": conv_addr,
        "conv_len": conv_len,
        "ramp_dir": ramp_dir,
        "ramp_addr": ramp_addr,
        "ramp_len": ramp_len,
        "border": border,
    }


def load_entities() -> dict[int, bytes]:
    blob = load_blob(ENTITY_BASE, 1024)
    return {i: blob[i * 8 : (i + 1) * 8] for i in range(128)}


def load_guardian_gfx() -> bytes:
    return load_blob(GUARDIAN_GFX, GUARDIAN_GFX_BYTES)


def decode_item_word(low: int, high: int) -> tuple[int, int, int]:
    """Decode item position from the two item-table bytes (see SkoolKit 41984)."""
    word = high | (low << 8)
    x = word & 31
    y = ((word >> 5) & 7) | (((word >> 15) & 1) << 3)
    room = (word >> 8) & 63
    return x, y, room


def load_items_by_room() -> dict[int, list[tuple[int, int, int]]]:
    html = fetch_html(ITEM_BASE)
    lows = extract_bytes_from_html(html, ITEM_BASE, 256)
    highs = extract_bytes_from_html(html, ITEM_BASE2, 256)
    by_room: dict[int, list[tuple[int, int, int]]] = {}
    for iid in range(173, 256):
        x, y, rid = decode_item_word(lows[iid], highs[iid])
        if rid <= 60:
            by_room.setdefault(rid, []).append((x, y, iid))
    return by_room


def load_room_names() -> dict[int, str]:
    names: dict[int, str] = {}
    for rid in range(61):
        try:
            data = load_room_blob(rid)
            t = data[128:160].split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
            if t:
                names[rid] = t
        except Exception:
            pass
    return names


def load_room_blob(rid: int) -> bytes:
    addr = ROOM_BASE + rid * 256
    return load_blob(addr, 256)


def entity_type(ent: bytes) -> int:
    return ent[0] & 7


def is_vertical(ent: bytes) -> bool:
    return entity_type(ent) == 2


def is_horizontal(ent: bytes) -> bool:
    return entity_type(ent) == 1


def ink_name(attr: int) -> str:
    return INK_NAMES[attr & 7]


def frame_range(ent: bytes) -> tuple[int, int]:
    mask = (ent[1] >> 5) & 7
    count = FRAME_MASK_COUNT.get(mask, 1)
    if is_horizontal(ent):
        return 0, count - 1
    if count > 4:
        count = 4
    fmin = (ent[0] >> 5) & 3
    return fmin, fmin + count - 1


def horiz_velocity(ent: bytes) -> int:
    return 1 if (ent[0] & 0x80) else -1


def signed_byte(b: int) -> int:
    return b if b < 128 else b - 256


def guardian_y(b: int) -> int:
    """JSW stores guardian y at 2x VIC pixel resolution."""
    return b // 2


def vertical_velocity(b: int) -> int:
    return signed_byte(b) // 2


def sprite_bytes(gfx: bytes, page: int, sprite_index: int, fmin: int, count: int) -> bytes:
    base = (page - GFX_PAGE_BASE) * 256 + sprite_index * 32
    need = count * 32
    if base < 0 or base + need > len(gfx):
        return bytes(need)
    return gfx[base + fmin * 32 : base + fmin * 32 + need]


def feature_columns(room: dict) -> set[int]:
    """Columns used by ramp or conveyor overlays — must not be dropped."""
    cols: set[int] = set()
    if room["ramp_len"]:
        c, _ = attr_addr_to_cell(room["ramp_addr"])
        for i in range(room["ramp_len"]):
            sc = c + i
            if 0 <= sc < SRC_W:
                cols.add(sc)
    if room["conv_len"]:
        c, _ = attr_addr_to_cell(room["conv_addr"])
        for i in range(room["conv_len"]):
            sc = c + i
            if 0 <= sc < SRC_W:
                cols.add(sc)
    return cols


def boundary_wall_columns(grid: list[list[int]]) -> tuple[int | None, int | None]:
    """Left/right room boundary walls that must survive column cropping."""
    WALL = 2
    left_cands: list[int] = []
    right_cands: list[int] = []
    for r in range(SRC_H):
        walls = [c for c in range(SRC_W) if grid[r][c] == WALL]
        if len(walls) < 2:
            continue
        left, right = min(walls), max(walls)
        span = right - left
        if span >= 28:
            continue
        if r == SRC_H - 1 and span >= 24:
            continue
        if span >= 8:
            left_cands.append(left)
            right_cands.append(right)

    left: int | None = None
    right: int | None = None
    if left_cands:
        lc = Counter(left_cands)
        rc = Counter(right_cands)
        lv, ln = lc.most_common(1)[0]
        rv, rn = rc.most_common(1)[0]
        left = lv if ln >= 2 else min(left_cands)
        right = rv if rn >= 2 else max(right_cands)

    for col, is_left in ((0, True), (SRC_W - 1, False)):
        n = sum(1 for r in range(SRC_H - 1) if grid[r][col] == WALL)
        if n >= 3:
            if is_left:
                left = col if left is None else min(left, col)
            else:
                right = col if right is None else max(right, col)
    return left, right


def choose_drop_columns(grid: list[list[int]], protected: set[int]) -> list[int]:
    """Pick 8 columns to drop (32→24). Columns 0 and 31 are always kept."""
    protected = set(protected) | {0, SRC_W - 1}
    left_wall, right_wall = boundary_wall_columns(grid)

    def col_weight(c: int) -> float:
        return sum(TILE_DROP_WEIGHT[grid[r][c]] for r in range(SRC_H))

    def drop_priority(c: int) -> float:
        """Lower = drop first. Boundary walls are a very soft keep preference."""
        w = col_weight(c)
        if left_wall is not None and c == left_wall:
            w += 0.25
        if right_wall is not None and c == right_wall:
            w += 0.25
        return w

    def pick_balanced_drops(droppable: list[int]) -> list[int]:
        """Drop lowest-weight columns, alternating left/right halves of the screen."""
        mid = SRC_W // 2
        left = sorted([c for c in droppable if c < mid], key=drop_priority)
        right = sorted([c for c in droppable if c >= mid], key=drop_priority)
        drop: list[int] = []
        li = ri = 0
        pick_left = True
        while len(drop) < DROP_COLS:
            if pick_left and li < len(left):
                drop.append(left[li])
                li += 1
            elif ri < len(right):
                drop.append(right[ri])
                ri += 1
            elif li < len(left):
                drop.append(left[li])
                li += 1
            else:
                break
            pick_left = not pick_left
        return sorted(drop)

    droppable = [c for c in range(SRC_W) if c not in protected]
    if len(droppable) >= DROP_COLS:
        return pick_balanced_drops(droppable)

    # Too much protected: still keep 0/31, drop the 8 lowest-priority other columns.
    candidates = [c for c in range(SRC_W) if c not in {0, SRC_W - 1}]
    return sorted(candidates, key=drop_priority)[:DROP_COLS]


def remap_col(c: int, drop: list[int]) -> int:
    return c - sum(1 for d in drop if d < c)


def overlay_line(cells: list[str], col: int, length: int, ch: str) -> None:
    for i in range(length):
        c = col + i
        if 0 <= c < len(cells):
            cells[c] = ch


def apply_ramp(
    lines: list[str], drop: list[int], col: int, row: int, length: int, direction: int
) -> None:
    ch = "/" if direction == 1 else "\\"
    for i in range(length):
        sc = col + i
        sr = row - i if direction == 1 else row + i
        if sc in drop or not (0 <= sr < SRC_H):
            continue
        ncol = remap_col(sc, drop)
        if 0 <= ncol < DST_W:
            cells = list(lines[sr].ljust(DST_W)[:DST_W])
            cells[ncol] = ch
            lines[sr] = "".join(cells)


def apply_conveyor(
    lines: list[str], drop: list[int], col: int, row: int, length: int, direction: int
) -> None:
    if row < 0 or row >= SRC_H:
        return
    ch = ">" if direction else "<"
    ncol = remap_col(col, drop)
    if ncol < 0:
        return
    cells = list(lines[row].ljust(DST_W)[:DST_W])
    for i in range(length):
        c = ncol + i
        if 0 <= c < DST_W:
            cells[c] = ch
    lines[row] = "".join(cells)


def grid_to_tilemap(
    grid: list[list[int]],
    drop: list[int],
    room: dict,
    item_xy: tuple[int, int],
) -> list[str]:
    drop_set = set(drop)
    lines: list[str] = []
    for row in range(SRC_H):
        cells: list[str] = []
        for col in range(SRC_W):
            if col in drop_set:
                continue
            t = grid[row][col]
            cells.append(TILE_CHARS[t] if t < len(TILE_CHARS) else " ")
        if len(cells) < DST_W:
            cells.extend([" "] * (DST_W - len(cells)))
        lines.append("".join(cells)[:DST_W].ljust(DST_W))

    if room["conv_len"]:
        c, r = attr_addr_to_cell(room["conv_addr"])
        apply_conveyor(lines, drop, c, r, room["conv_len"], room["conv_dir"])

    if room["ramp_len"]:
        c, r = attr_addr_to_cell(room["ramp_addr"])
        apply_ramp(lines, drop, c, r, room["ramp_len"], room["ramp_dir"])

    if item_xy:
        x, y = item_xy
        if 0 <= y < SRC_H and 0 <= x < DST_W:
            cells = list(lines[y].ljust(DST_W)[:DST_W])
            cells[x] = "+"
            lines[y] = "".join(cells)[:DST_W].ljust(DST_W)
    return lines


def pick_item(
    items: list[tuple[int, int, int]], drop: list[int]
) -> tuple[int, int]:
    drop_set = set(drop)
    playable = [(x, y) for x, y, _ in items if x not in drop_set and y < SRC_H]
    if playable:
        # Prefer highest items (smallest y — e.g. bottles hanging from ceiling).
        playable.sort(key=lambda p: (p[1], abs(p[0] - 16)))
        x, y = playable[0]
        return remap_col(x, drop), y
    return DST_W // 2, SRC_H - 1


def room_has_item(items: list[tuple[int, int, int]], drop: list[int]) -> bool:
    drop_set = set(drop)
    return any(x not in drop_set and y < SRC_H for x, y, _ in items)


def pick_item_color(rid: int) -> str:
    return random.Random(rid).choice(ITEM_INK_COLORS)


def guardian_sprite_key(ent: bytes, spec: int) -> tuple[int, int, int, int]:
    fmin, fmax = frame_range(ent)
    return ent[5], spec >> 5, fmin, fmax - fmin + 1


def guardian_sprite_groups(
    entities: list[tuple[int, int]],
    entities_db: dict[int, bytes],
    gfx: bytes,
) -> tuple[list[tuple[str, list[bytes]]], dict[tuple[int, int, int, int], tuple[int, int]]]:
    """Collect sprite frames and map each gfx key to its index in the text block."""
    groups: list[tuple[str, list[bytes]]] = []
    frame_offsets: dict[tuple[int, int, int, int], tuple[int, int]] = {}
    used: set[tuple[int, int, int, int]] = set()
    next_frame = 0
    for ent_id, spec in entities:
        ent = entities_db.get(ent_id)
        if not ent or entity_type(ent) not in (1, 2):
            continue
        key = guardian_sprite_key(ent, spec)
        if key in used:
            continue
        used.add(key)
        page, sprite, fmin, count = key
        data = sprite_bytes(gfx, page, sprite, fmin, count)
        frames: list[bytes] = []
        for i in range(0, len(data), 32):
            chunk = data[i : i + 32]
            if len(chunk) == 32:
                frames.append(chunk)
        if frames:
            block_fmin = next_frame
            block_fmax = next_frame + len(frames) - 1
            frame_offsets[key] = (block_fmin, block_fmax)
            next_frame += len(frames)
            label = (
                f"entity {ent_id}: page {page} sprite {sprite} "
                f"f={block_fmin}..{block_fmax}"
            )
            groups.append((label, frames))
    return groups, frame_offsets


def build_guardians(
    entities: list[tuple[int, int]],
    entities_db: dict[int, bytes],
    drop: list[int],
    frame_offsets: dict[tuple[int, int, int, int], tuple[int, int]],
) -> list[str]:
    lines: list[str] = []
    for ent_id, spec in entities:
        if ent_id == 0:
            continue
        ent = entities_db.get(ent_id)
        if not ent:
            continue
        t = entity_type(ent)
        if t not in (1, 2):
            continue
        key = guardian_sprite_key(ent, spec)
        if key not in frame_offsets:
            continue
        block_fmin, block_fmax = frame_offsets[key]
        x = spec & 31
        colour = ink_name(ent[1])
        if is_horizontal(ent):
            x = remap_col(x, drop)
            if x < 0 or x >= DST_W:
                continue
            xmin = remap_col(ent[6], drop)
            xmax = remap_col(ent[7], drop)
            if xmax < xmin:
                xmin, xmax = xmax, xmin
            xmax = min(max(xmax, xmin), DST_W - 1)
            lines.append(
                f"y={guardian_y(ent[3])} x={x}({xmin}..{xmax}) v={horiz_velocity(ent)} "
                f"f={block_fmin}..{block_fmax} {colour}"
            )
        elif is_vertical(ent):
            if x in set(drop):
                continue
            x = remap_col(x, drop)
            y = guardian_y(ent[3])
            ymin = guardian_y(ent[6])
            ymax = guardian_y(ent[7])
            vel = vertical_velocity(ent[4])
            lines.append(
                f"x={x} y={y}({ymin}..{ymax}) v={vel} f={block_fmin}..{block_fmax} {colour}"
            )
        if len(lines) >= 6:
            break
    return lines



def fmt_sprite_lines(groups: list[tuple[str, list[bytes]]]) -> list[str]:
    """Emit Skool interleaved L,R pairs — mkroom deinterleaves at build time."""
    lines: list[str] = []
    for label, frames in groups:
        lines.append(f"; {label}")
        for fr in frames:
            lines.append(",".join(str(b) for b in fr))
    return lines


def tile_udg_line(idx: int, raw9: bytes, invert: bool) -> str:
    if idx == 6:
        bs = list(raw9[:8])
    else:
        bs = list(raw9[1:9])
    parts = ",".join(str(b) for b in bs)
    suffix = " ; invert" if invert and idx != 6 else ""
    return f"{idx}: {parts}{suffix}"


def needs_invert(attr: int) -> bool:
    return bool(attr & 0x40)


def format_room_byte(b: int) -> str:
    """Format a byte for room source: decimal 0-15, $XX hex for 16-255."""
    if b <= 15:
        return str(b)
    return f"${b:02X}"


def format_udg_tag(tag: str, bs: list[int], invert: bool) -> str:
    parts = ",".join(format_room_byte(b) for b in bs)
    suffix = " ; invert" if invert else ""
    return f"@{tag} {parts}{suffix}"


def udg_parsed_bytes(bs: list[int], invert: bool) -> bytes:
    raw = bytes(bs)
    return bytes(b ^ 0xFF for b in raw) if invert else raw


def should_emit_udg(idx: int, parsed: bytes, used: set[int]) -> bool:
    if not any(parsed):
        return False
    return idx in used or any(b != 0 for b in parsed)


def belt_value(conv_dir: int, conv_len: int) -> int:
    if not conv_len:
        return 0
    return 1 if conv_dir else -1


def write_room(
    rid: int,
    room: dict,
    tilemap: list[str],
    guardians: list[str],
    sprite_lines: list[str],
    items_by_room: dict[int, list[tuple[int, int, int]]],
    drop: list[int],
) -> None:
    border = INK_NAMES[room["border"] & 7] if room["border"] < 8 else "BLK"
    belt = belt_value(room["conv_dir"], room["conv_len"])
    item_xy = pick_item(items_by_room.get(rid, []), drop)
    has_item = room_has_item(items_by_room.get(rid, []), drop)
    if has_item:
        itemcolor = pick_item_color(rid)
    else:
        itemcolor = ink_name(room["item_udg"][0])

    lines = [
        f"@room {rid}",
        f"@title {room['title'][:18]}",
        f"@conn {room['exits'][2]} {room['exits'][1]} {room['exits'][3]} {room['exits'][0]}",
        "@spawn 44 104",
        f"@border {border}",
        f"@belt {belt}",
        "",
        "@guardiansprites",
    ]
    lines.extend(sprite_lines)
    lines.append("")
    lines.append("@tilemap")
    lines.extend(tilemap)
    lines.append("")
    tc = [ink_name(t[0]) for t in room["tiles"][:6]]
    if tc[0] != "WHT":
        lines.append(f"@emptycolor {tc[0]}")
    color_tags = (
        "floorcolor",
        "wallcolor",
        "nastycolor",
        "rampcolor",
        "beltcolor",
    )
    for i, tag in enumerate(color_tags, start=1):
        lines.append(f"@{tag} {tc[i]}")
    lines.append(f"@itemcolor {itemcolor}")
    lines.append("")
    if guardians:
        lines.append("@guardians")
        lines.extend(guardians)
        lines.append("")
    used = tile_types_in_tilemap(tilemap)
    udg_tags = (
        "emptyudg",
        "floorudg",
        "walludg",
        "nastyudg",
        "rampudg",
        "beltudg",
        "itemudg",
    )
    for i in range(7):
        if i == 6:
            if not has_item:
                continue
            raw = room["item_udg"] + bytes(max(0, 8 - len(room["item_udg"])))
            bs = list(raw[:8])
            invert = False
        else:
            raw = room["tiles"][i]
            bs = list(raw[1:9])
            invert = needs_invert(raw[0])
        parsed = udg_parsed_bytes(bs, invert)
        if not should_emit_udg(i, parsed, used):
            continue
        lines.append(format_udg_tag(udg_tags[i], bs, invert and i != 6))
    lines.append("")

    path = ROOMS_DIR / f"room{rid:02d}.txt"
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {path.name} (dropped cols {drop})")


def import_room(
    rid: int,
    entities_db: dict[int, bytes],
    gfx: bytes,
    items_by_room: dict[int, list[tuple[int, int, int]]],
) -> None:
    data = load_room_blob(rid)
    room = parse_room_block(data)
    grid = decode_layout(room["layout"])

    vcols: set[int] = set()
    for ent_id, spec in room["entities"]:
        ent = entities_db.get(ent_id)
        if ent and is_vertical(ent):
            vcols.add(spec & 31)

    drop = choose_drop_columns(grid, vcols | feature_columns(room))
    item_xy = pick_item(items_by_room.get(rid, []), drop)
    tilemap = grid_to_tilemap(grid, drop, room, item_xy)
    sprite_groups, frame_offsets = guardian_sprite_groups(
        room["entities"], entities_db, gfx
    )
    guardians = build_guardians(room["entities"], entities_db, drop, frame_offsets)
    sprite_lines = fmt_sprite_lines(sprite_groups)
    write_room(rid, room, tilemap, guardians, sprite_lines, items_by_room, drop)


def main() -> None:
    ap = argparse.ArgumentParser(description="Import JSW rooms from SkoolKit")
    ap.add_argument("--room", type=int, action="append", help="room id(s) to import")
    ap.add_argument("--all-missing", action="store_true", help="import rooms not yet present")
    ap.add_argument("--force", action="store_true", help="overwrite existing hand-tuned rooms")
    args = ap.parse_args()

    entities_db = load_entities()
    gfx = load_guardian_gfx()
    items_by_room = load_items_by_room()

    if args.all_missing:
        targets = [r for r in range(61) if r not in EXISTING or args.force]
    elif args.room:
        targets = args.room
    else:
        ap.error("specify --room N or --all-missing")

    ROOMS_DIR.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    for rid in targets:
        if rid in EXISTING and not args.force:
            print(f"skip room {rid} (existing)")
            continue
        try:
            import_room(rid, entities_db, gfx, items_by_room)
        except Exception as e:
            errors.append(f"room {rid}: {e}")
            print(f"error room {rid}: {e}", file=sys.stderr)
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
