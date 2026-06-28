#!/usr/bin/env python3
"""Convert roomNN.txt source files to PRG room binaries for JSW VIC-20."""

import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

WIDTH = 24


def normalize_tilemap_row(row: str) -> str:
    """Trim overlong rows; pad short rows with spaces to exactly WIDTH."""
    return row[:WIDTH].ljust(WIDTH)


SCREEN_ROWS = 17              # gameplay 0-15 + HUD row 16
TILEMAP_ROWS = 16             # @tilemap lines (gameplay only)
TILE_BYTES = WIDTH * SCREEN_ROWS
UDG_BYTES = 56
TILE_COLOR_BYTES = 6
ITEM_DRAW_BYTES = 11
ITEM_ERASE_BYTES = 11
ITEM_FLICKER_BYTES = 16
BAKE_DIR = Path(__file__).resolve().parent.parent / "bake"
ACME = Path(r"\app\acme\acme.exe")
JSW_LBL = Path(__file__).resolve().parent.parent / "jsw.lbl"
GUARDIAN_SPRITES_BYTES = 288  # 9 frames x 32 bytes
TITLE_HOLD_FRAMES = 150         # 3 s @ 50 Hz (WaitForRaster)
TITLE_SCROLL_FRAMES = 6         # ~8.3 chars/s @ 50 Hz
TITLE_MESSAGE = (
    "+SPACE or FIRE to Start+"
    "JET-SET WILLY by Matthew Smith 1984"
    "++"
    "VIC-20 port by Steve McCrea 2026"
    "++"
    "Collect all the items around the house so Maria will let you get to bed"
)
META_OFF_ROPE = 16 + ITEM_DRAW_BYTES + ITEM_ERASE_BYTES
TAIL_OFF_GUARDIAN_DATA = META_OFF_ROPE + 1
PLAYER_BMP_BYTES = 256
NIGHTMARE_ROOM_ID = 29
DEFAULT_PLAYER_BMP_PATH = (
    Path(__file__).resolve().parent.parent / "willy.txt"
)
NIGHTMARE_PLAYER_BMP_PATH = (
    Path(__file__).resolve().parent.parent / "nightmareroomwilly.txt"
)
GUARDIAN_DATA_BYTES = 60          # AoS: 10 bytes x 6 guardians
GUARDIAN_RECORD_BYTES = 10
MAX_GUARDIANS = 6
TAIL_BYTES = 104
META_SIZE = 16 + ITEM_DRAW_BYTES + ITEM_ERASE_BYTES
IMAGE_LOAD = 0x1A05
CONVEYOR_PREFIX_BYTES = 19
DO_BELT_SLOT_BYTES = 26
GUARDIAN_PREFIX_BYTES = (
    ITEM_FLICKER_BYTES + CONVEYOR_PREFIX_BYTES + DO_BELT_SLOT_BYTES + TILE_COLOR_BYTES
)
TITLE_SCREEN_OFF = GUARDIAN_PREFIX_BYTES
LOGO_ROOM_ID = 62
ROOM_MASTER_BED = 35
MASTER_BED_PAD_HOOK_OFF = 48       # guardian UDG slots 1-5 within runtime_udg_pad
MASTER_BED_SPRITE_HOOK_OFF = 128   # sprite frames 4-7 within guardian_sprites
MASTER_BED_HOOK_BYTES = 240
MASTER_BED_HOOK_EXT_BYTES = 160
MASTER_BED_HOOK_MAX_BYTES = MASTER_BED_HOOK_BYTES + MASTER_BED_HOOK_EXT_BYTES
MASTER_BED_HOOK_ORG = 0x1CE0
LOGO_ORIGIN_COL = 4
LOGO_ORIGIN_ROW = 4
LOGO_DEFAULT_PATH = BAKE_DIR / "jswlogo.png"
LOGO_UDG_RAM = 0x1C00
LOGO_UDG_OFF = LOGO_UDG_RAM - IMAGE_LOAD
TITLE_SCREEN_SLOT_BYTES = LOGO_UDG_OFF  # r62: TitleScreen @ $1A05-$1BFF
LOGO_UDG_MAX_BYTES = 0x1E00 - LOGO_UDG_RAM
SCREEN_BASE = 0x1E00
MAP_BASE = 0x9400
COLOR_BASE = 0x9600
MAX_ITEMS = 1
DEFAULT_SPAWN = (46, 104)
ROOM_IMAGE_SIZE = 0x5FB           # 1531 bytes ($1A05-$1FFF); FlickerItem +16 at load base
HUD_UDG_BYTES = 16
# Pad pins screen at $1E00: IMAGE_LOAD + flicker + code prefix + sprites + ... + pad == SCREEN_BASE
RUNTIME_UDG_PAD = 0x150           # 336 bytes ($1CB0-$1DFF)
TILE_CHR_BASE = 16
TILE_EMPTY = 0
TILE_PLATFORM = 1
TILE_SOLID = 2
TILE_HAZARD = 3
TILE_RAMP = 4
TILE_CONVEYOR = 5
TILE_ITEM = 6
RAMP_NONE = 0
RAMP_UP_RIGHT = 1
RAMP_UP_LEFT = 0xFF
RAMP_BOUNDS_NONE = 99
TILE_CHAR_MAP = {
    " ": TILE_EMPTY,
    ".": TILE_EMPTY,
    "F": TILE_PLATFORM,
    "W": TILE_SOLID,
    "*": TILE_HAZARD,
    "/": TILE_RAMP,
    "\\": TILE_RAMP,
    "<": TILE_CONVEYOR,
    ">": TILE_CONVEYOR,
}
ITEM_CHR = 15
MEN_CHR = 13
HUD_ITEM_CHR = 14
HUD_TITLE_COLS = 18
DEFAULT_TILE_COLORS = [0, 1, 3, 2, 5, 4]
DEFAULT_EMPTY_COLOR = 1  # WHT
TILE_COLOR_TAGS = {
    "emptycolor": 0,
    "floorcolor": 1,
    "wallcolor": 2,
    "nastycolor": 3,
    "rampcolor": 4,
    "beltcolor": 5,
}
TILE_UDG_TAGS = {
    "emptyudg": 0,
    "floorudg": 1,
    "walludg": 2,
    "nastyudg": 3,
    "rampudg": 4,
    "beltudg": 5,
    "itemudg": 6,
}
DEFAULT_ITEM_UDG = bytes([48, 72, 136, 144, 104, 4, 10, 4])
DEFAULT_MEN_UDG = bytes([60, 60, 126, 52, 62, 60, 24, 60])
DEFAULT_HUD_ITEM_UDG = bytes([4, 4, 174, 174, 162, 66, 66, 238])
DEFAULT_ARROW_UDG_LTR = bytes([0, 0, 194, 127, 194, 0, 0, 0])
DEFAULT_ARROW_UDG_RTL = bytes([0, 0, 67, 254, 67, 0, 0, 0])
GUARDIAN_CHR = 22
ARROW_CHR = 46
ARROW_CODE_BYTES = 88
META_OFF_HAS_ARROW = 99
UDG_BASE = 0x1C00
RUNTIME_UDG_PAD_BASE = 0x1CB0
ARROW_UDG_ADDR = RUNTIME_UDG_PAD_BASE + (ARROW_CHR - GUARDIAN_CHR) * 8
ARROW_CODE_ADDR = ARROW_UDG_ADDR + 8
EMPTY_SCREEN_CHR = TILE_CHR_BASE + TILE_EMPTY
ARROW_ENTITY_LTR = 60
ARROW_ENTITY_RTL = 69
ARROW_TEMPLATE_X = {ARROW_ENTITY_LTR: 208, ARROW_ENTITY_RTL: 28}
ARROW_TEMPLATE_SOUND = {ARROW_ENTITY_LTR: 244, ARROW_ENTITY_RTL: 44}
ARROW_TAG_RE = re.compile(
    r"y\s*=\s*(\d+)\s+"
    r"x\s*=\s*(\d+)\s+"
    r"v\s*=\s*([-+]?\d+)\s+"
    r"sound\s*=\s*(\d+)",
    re.I,
)

VIC_COLOR = {
    "BLK": 0,
    "WHT": 1,
    "RED": 2,
    "CYN": 3,
    "PUR": 4,
    "GRN": 5,
    "BLU": 6,
    "YEL": 7,
}

# VIC-20 screen background only ($900F bits 4-7); not valid for border or color RAM.
VIC_BG_EXTRA = {
    "ORN": 8,
    "LIGHT ORN": 9,
    "LIGHT RED": 10,
    "LIGHT CYN": 11,
    "LIGHT PUR": 12,
    "LIGHT GRN": 13,
    "LIGHT BLU": 14,
    "LIGHT YEL": 15,
}

GUARDIAN_DSL_H = re.compile(
    r"y\s*=\s*(\d+)\s+"
    r"x\s*=\s*(\d+)\((\d+)\.\.(\d+)\)\s+"
    r"v\s*=\s*([+-]?\d+)\s+"
    r"f\s*=\s*(\d+)(?:\.\.(\d+))?\s+"
    r"(\w+)",
    re.I,
)
GUARDIAN_DSL_V = re.compile(
    r"x\s*=\s*(\d+)\s+"
    r"y\s*=\s*(\d+)\((\d+)\.\.(\d+)\)\s+"
    r"v\s*=\s*([+-]?\d+)\s+"
    r"f\s*=\s*(\d+)(?:\.\.(\d+))?\s+"
    r"(\w+)",
    re.I,
)

G_OFF_X = 0
G_OFF_Y = 1
G_OFF_MIN = 2
G_OFF_MAX = 3
G_OFF_VEL = 4
G_OFF_FRAME = 5
G_OFF_FMIN = 6
G_OFF_FCTL = 7
G_OFF_COLOR = 8
G_OFF_AXIS = 9

GUARDIAN_HORIZONTAL = 0
GUARDIAN_VERTICAL = 1
GUARDIAN_ORBIT_STEP_CAP = 512


def parse_byte(s: str) -> int:
    """Parse a byte: decimal by default; $XX or 0xXX for hex (used in @*udg, @conn, sprite blocks)."""
    s = s.strip().upper()
    if s.startswith("$"):
        try:
            v = int(s[1:].strip(), 16)
        except ValueError as e:
            raise ValueError(f"invalid hex byte {s!r}") from e
    elif s.startswith("0X"):
        try:
            v = int(s[2:], 16)
        except ValueError as e:
            raise ValueError(f"invalid hex byte {s!r}") from e
    else:
        try:
            v = int(s, 10)
        except ValueError as e:
            raise ValueError(
                f"byte value {s!r}: use decimal or $XX hex (e.g. 255 or $FF)"
            ) from e
    if not 0 <= v <= 255:
        raise ValueError(f"byte out of range 0-255: {v}")
    return v


def parse_vic_color(token: str) -> int:
    """Parse a VIC colour token: name (BLK, WHT, …) or digit 0-7."""
    s = token.strip().upper()
    if s in VIC_COLOR:
        return VIC_COLOR[s]
    if len(s) == 1 and s.isdigit():
        v = int(s)
        if v > 7:
            raise ValueError(f"tile color out of range 0-7: {v}")
        return v
    names = ", ".join(VIC_COLOR)
    raise ValueError(f"unknown colour {token!r} (use {names})")


def parse_vic_bg_color(value_tokens: list[str]) -> int:
    """Parse @background colour: standard 0-7, extended 8-15, or digit 0-15."""
    if not value_tokens:
        raise ValueError("missing background colour")
    if value_tokens[0].strip().upper() == "LIGHT":
        if len(value_tokens) < 2:
            raise ValueError("LIGHT background colour needs a second token (ORN, RED, …)")
        key = f"LIGHT {value_tokens[1].strip().upper()}"
        if key in VIC_BG_EXTRA:
            return VIC_BG_EXTRA[key]
        names = ", ".join(VIC_BG_EXTRA)
        raise ValueError(f"unknown background colour {key!r} (use {names})")
    s = value_tokens[0].strip().upper()
    if s in VIC_COLOR:
        return VIC_COLOR[s]
    if s in VIC_BG_EXTRA:
        return VIC_BG_EXTRA[s]
    if s.isdigit():
        v = int(s)
        if v > 15:
            raise ValueError(f"background colour out of range 0-15: {v}")
        return v
    std = ", ".join(VIC_COLOR)
    extra = ", ".join(k for k in VIC_BG_EXTRA if not k.startswith("LIGHT "))
    light = ", ".join(k for k in VIC_BG_EXTRA if k.startswith("LIGHT "))
    raise ValueError(
        f"unknown background colour {value_tokens[0]!r} "
        f"(use {std}, {extra}, or {light})"
    )


def parse_byte_list(text: str) -> list[int]:
    """Comma-separated byte list: decimal by default, $XX hex ok (e.g. 255, $FF, 16)."""
    return [parse_byte(part) for part in text.split(",") if part.strip()]


def parse_velocity(text: str) -> int:
    v = int(text.strip())
    return v & 0xFF


def fmt_loc(source: Path | str | None = None, line_no: int | None = None) -> str:
    if not source:
        return ""
    loc = str(source)
    if line_no is not None:
        loc += f":{line_no}"
    return loc + ": "


def scan_room_title(text: str) -> str:
    """Read @title from header without full parse."""
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line.lower().startswith("@title"):
            continue
        parts = line.split(None, 1)
        return parts[1] if len(parts) > 1 else ""
    return ""


def room_error(room: dict | None, msg: str) -> ValueError:
    if room:
        rid = room.get("id", "?")
        if rid != "?":
            return ValueError(f"room {rid}: {msg}")
    return ValueError(msg)


def format_build_error(
    src: Path,
    exc: BaseException,
    *,
    text: str | None = None,
    room: dict | None = None,
) -> str:
    title = (room or {}).get("title") or (scan_room_title(text) if text else "")
    head = title if title else src.name
    msg = str(exc)
    msg = re.sub(r"^room \d+: ", "", msg)
    return f"error: {head}: {msg}"


def parse_guardian_line(
    line: str, *, source: Path | str | None = None, line_no: int | None = None
) -> dict:
    """Parse guardian DSL line into SoA field dict."""
    loc = fmt_loc(source, line_no)
    m = GUARDIAN_DSL_H.match(line)
    if m:
        hy, x_tile, xmin, xmax, vel, fmin, fmax, colour = m.groups()
        gx = int(x_tile) * 4
        gmin = int(xmin) * 4
        gmax = int(xmax) * 4 - 1
        gy = int(hy)
        axis = 0
    else:
        m = GUARDIAN_DSL_V.match(line)
        if not m:
            raise ValueError(f"{loc}bad @guardians line: {line!r}")
        x_tile, gy, ymin, ymax, vel, fmin, fmax, colour = m.groups()
        gx = int(x_tile) * 4
        gy = int(gy)
        gmin = int(ymin)
        gmax = int(ymax)
        axis = 1

    fmin_i = int(fmin)
    fmax_i = int(fmax) if fmax is not None else fmin_i
    if not 0 <= fmin_i <= 8 or not 0 <= fmax_i <= 8 or fmin_i > fmax_i:
        raise ValueError(f"{loc}frame range out of range 0-8: {fmin}..{fmax}")

    frame_count = fmax_i - fmin_i + 1
    if axis == 1:
        if frame_count not in (1, 2, 4):
            raise ValueError(
                f"{loc}vertical guardian frame count must be 1, 2, or 4: {fmin}..{fmax}"
            )
        fctl_store = frame_count - 1  # wrap mask: 0, 1, or 3
    else:
        if frame_count not in (4, 8):
            raise ValueError(
                f"{loc}horizontal guardian frame count must be 4 or 8: {fmin}..{fmax}"
            )
        fctl_store = 1 if frame_count == 8 else 0  # bidirectional flag

    out = {
        "x": gx & 0xFF,
        "y": gy & 0xFF,
        "min": gmin & 0xFF,
        "max": gmax & 0xFF,
        "vel": parse_velocity(vel),
        "fmin": fmin_i,
        "fmax": fmax_i,
        "fctl": fctl_store,
        "color": parse_vic_color(colour),
        "axis": axis,
    }
    if line_no is not None:
        out["line_no"] = line_no
    out["line"] = line
    return out


def guardian_vel_signed(vel_byte: int) -> int:
    return vel_byte if vel_byte < 128 else vel_byte - 256


def guardian_error_loc(room: dict, g: dict) -> str:
    src = Path(room["_source"]).name if room.get("_source") else "room"
    line_no = g.get("line_no")
    if line_no is not None:
        return f"{src}:{line_no}"
    return src


def guardian_footprint_cells(hx: int, hy: int) -> list[tuple[int, int]]:
    """Screen cells occupied by DrawGuardian (ConvertXYToScreenAddr + cell_off_2x3)."""
    col = hx >> 2
    row = hy >> 3
    if (hy & 7) == 0:
        dr_rows = (0, 0, 1, 1)
    else:
        dr_rows = (0, 0, 1, 1, 2, 2)
    cells: list[tuple[int, int]] = []
    for i, dr in enumerate(dr_rows):
        c, r = col + (i & 1), row + dr
        if 0 <= c < WIDTH and 0 <= r < TILEMAP_ROWS:
            cells.append((c, r))
    return cells


def iter_guardian_orbit(g: dict) -> list[tuple[int, int, int]]:
    """Return (hx, hy, step_index) for each position on the bounce orbit."""
    axis = g["axis"]
    vmin, vmax = g["min"], g["max"]
    vel = guardian_vel_signed(g["vel"])
    if axis == GUARDIAN_HORIZONTAL:
        start, fixed = g["x"], g["y"]
    else:
        start, fixed = g["y"], g["x"]

    out: list[tuple[int, int, int]] = []
    if vel == 0:
        if axis == GUARDIAN_HORIZONTAL:
            out.append((start, fixed, 0))
        else:
            out.append((fixed, start, 0))
        return out

    pos = start
    v = vel
    seen: set[tuple[int, int]] = set()
    step = 0
    while step < GUARDIAN_ORBIT_STEP_CAP:
        pos += v
        key = (pos, v)
        if key in seen:
            break
        seen.add(key)
        if axis == GUARDIAN_HORIZONTAL:
            out.append((pos, fixed, step))
        else:
            out.append((fixed, pos, step))
        step += 1
        if v > 0 and pos == vmax:
            v = -v
        elif v < 0 and pos == vmin:
            v = -v
    else:
        raise ValueError(
            f"guardian orbit exceeded {GUARDIAN_ORBIT_STEP_CAP} steps "
            f"(range [{vmin}..{vmax}] v={vel})"
        )
    return out


def validate_guardian_ranges(room: dict) -> None:
    for g in room["guardians"]:
        loc = guardian_error_loc(room, g)
        axis = g["axis"]
        vmin, vmax = g["min"], g["max"]
        vel = guardian_vel_signed(g["vel"])
        start = g["x"] if axis == GUARDIAN_HORIZONTAL else g["y"]

        if vel == 0:
            if not vmin <= start <= vmax:
                raise room_error(
                    room,
                    f"{loc}: stationary_outside start={start} not in [{vmin}..{vmax}]",
                )
            continue

        first = start + vel
        if not vmin <= first <= vmax:
            raise room_error(
                room,
                f"{loc}: first_step_outside first={first} not in [{vmin}..{vmax}]",
            )

        if axis == GUARDIAN_VERTICAL:
            a = abs(vel)
            if (start - vmin) % a:
                raise room_error(
                    room,
                    f"{loc}: off_grid (start={start}-min={vmin}) % {a} != 0",
                )
            if (vmax - vmin) % a:
                raise room_error(
                    room,
                    f"{loc}: span_indivisible (max-min)={vmax - vmin} % {a} != 0",
                )


def tilemap_passable_for_guardian(ch: str) -> bool:
    """Only space and dot are empty for guardian path checks ('+' blocks, 'S' does not)."""
    return ch in (" ", ".", "S")


def validate_guardian_paths(room: dict) -> None:
    tilemap = room["tilemap"]
    for g in room["guardians"]:
        loc = guardian_error_loc(room, g)
        for hx, hy, step in iter_guardian_orbit(g):
            for col, row in guardian_footprint_cells(hx, hy):
                ch = tilemap[row][col]
                if not tilemap_passable_for_guardian(ch):
                    raise room_error(
                        room,
                        f"{loc}: path_not_empty step {step} cell ({col},{row}) tile {ch!r}",
                    )


def validate_guardians(room: dict) -> None:
    validate_guardian_ranges(room)
    validate_guardian_paths(room)


def tile_to_spawn(col: int, row: int, room: dict | None = None) -> tuple[int, int]:
    """Convert 'S' tile (lower body) to @spawn px/py (head one row above)."""
    if row < 1:
        raise room_error(
            room,
            f"'S' spawn marker at row {row} needs a row above for Willy's head",
        )
    return (col * 4, (row - 1) * 8)


def parse_tile_char(ch: str, room: dict | None = None) -> int:
    """Map ASCII tilemap character to tile type 0-5. '+' and 'S' bake as empty."""
    if ch in ("+", "S"):
        return TILE_EMPTY
    try:
        return TILE_CHAR_MAP[ch]
    except KeyError:
        raise room_error(room, f"unknown tilemap character {ch!r}")


def parse_udg_bytes(content: str) -> bytes:
    """Parse UDG byte list with optional '; invert' suffix. Bytes: decimal or $XX hex."""
    content = content.split("#", 1)[0].strip()
    invert = False
    if ";" in content:
        left, right = content.split(";", 1)
        if "INVERT" in right.upper():
            invert = True
        content = left.strip()
    bs = parse_byte_list(content)
    if len(bs) != 8:
        raise ValueError(f"UDG needs 8 bytes, got {len(bs)}")
    if invert:
        bs = [b ^ 0xFF for b in bs]
    return bytes(bs)


def tile_types_in_tilemap(tilemap: list) -> set[int]:
    """Return tile type indices 0-5 present in gameplay rows; 6 if '+' found."""
    found: set[int] = set()
    for row, line in enumerate(tilemap):
        if row >= TILEMAP_ROWS:
            continue
        for ch in line:
            if ch == "+":
                found.add(6)
            elif ch in TILE_CHAR_MAP:
                found.add(TILE_CHAR_MAP[ch])
    return found


def extract_items_from_tilemap(
    tilemap: list, room: dict | None = None
) -> list[tuple[int, int]]:
    """Return [(col, row), ...] for '+' pickup markers (0 or 1 allowed)."""
    found: list[tuple[int, int]] = []
    for row, line in enumerate(tilemap):
        if row >= TILEMAP_ROWS:
            continue
        for col, ch in enumerate(line):
            if ch == "+":
                found.append((col, row))
    if len(found) > MAX_ITEMS:
        raise room_error(
            room,
            f"tilemap must have at most {MAX_ITEMS} '+' pickup marker(s), found {len(found)}",
        )
    return found


def extract_spawn_from_tilemap(
    tilemap: list, room: dict | None = None
) -> tuple[int, int] | None:
    """Return (col, row) for 'S' spawn marker, or None."""
    found: list[tuple[int, int]] = []
    for row, line in enumerate(tilemap):
        if row >= TILEMAP_ROWS:
            continue
        for col, ch in enumerate(line):
            if ch == "S":
                found.append((col, row))
    if len(found) > 1:
        raise room_error(
            room,
            f"tilemap must have at most one 'S' spawn marker, found {len(found)}",
        )
    return found[0] if found else None


def resolve_spawn(room: dict) -> None:
    """Set room['spawn'] from tilemap S, @spawn tag, or DEFAULT_SPAWN."""
    spawn_tile = extract_spawn_from_tilemap(room["tilemap"], room)
    if spawn_tile is not None:
        room["spawn"] = tile_to_spawn(*spawn_tile, room=room)
    elif room["spawn"] is None:
        room["spawn"] = DEFAULT_SPAWN


def infer_ramp_from_tilemap(
    tilemap: list, room: dict | None = None
) -> int:
    """Derive ramp type from '/' (up-right) or '\\' (up-left) tiles."""
    has_up_right = False
    has_up_left = False
    for row, line in enumerate(tilemap):
        if row >= TILEMAP_ROWS:
            continue
        for ch in line:
            if ch == "/":
                has_up_right = True
            elif ch == "\\":
                has_up_left = True
    if has_up_right and has_up_left:
        raise room_error(room, "tilemap has mixed ramp directions ('/' and '\\')")
    if has_up_right:
        return RAMP_UP_RIGHT
    if has_up_left:
        return RAMP_UP_LEFT
    return RAMP_NONE


def validate_tilemap_belt(
    tilemap: list, belt: int, room: dict | None = None
) -> None:
    """Check conveyor chars match @belt direction."""
    for row, line in enumerate(tilemap):
        if row >= TILEMAP_ROWS:
            continue
        for col, ch in enumerate(line):
            if ch == "<" and belt == 1:
                raise room_error(
                    room,
                    f"conveyor '<' at col {col} row {row} but @belt 1 (expect '>')",
                )
            elif ch == ">" and belt == -1:
                raise room_error(
                    room,
                    f"conveyor '>' at col {col} row {row} but @belt -1 (expect '<')",
                )


def parse_room(text: str, source: Path | str | None = None) -> dict:
    lines = text.splitlines()
    loc = lambda line_no=None: fmt_loc(source, line_no)
    room = {
        "id": 0,
        "title": "",
        "conn": [0xFF, 0xFF, 0xFF, 0xFF],
        "spawn": None,
        "border": 0,
        "background": 0,
        "belt": 0,
        "ramp": 0,
        "tilemap": [],
        "tilecolors": [DEFAULT_EMPTY_COLOR] + list(DEFAULT_TILE_COLORS[1:]),
        "itemcolor": 7,
        "items": [],
        "guardians": [],
        "tileudg": [bytes(8) for _ in range(7)],
        "itemudg_defined": False,
        "guardiansprites": b"",
        "playerbmp": b"",
        "rope": False,
        "playable": False,
        "logo": None,
        "hudright": "",
        "arrow": None,
    }
    if source:
        room["_source"] = str(source)
    block = None
    block_lines = []

    def flush_block():
        nonlocal block, block_lines
        if block == "tilemap":
            room["tilemap"] = [normalize_tilemap_row(line) for line in block_lines]
        elif block == "tileudg":
            for line in block_lines:
                m = re.match(r"(\d+)\s*:\s*(.+)", line.strip(), re.I)
                if not m:
                    continue
                idx = int(m.group(1))
                if idx < 7:
                    room["tileudg"][idx] = parse_udg_bytes(m.group(2).strip())
                    if idx == 6:
                        room["itemudg_defined"] = True
        elif block == "guardiansprites":
            bs = []
            for line in block_lines:
                if line.strip().startswith(";"):
                    continue
                bs.extend(parse_byte_list(line))
            room["guardiansprites"] = bytes(bs[:GUARDIAN_SPRITES_BYTES]).ljust(
                GUARDIAN_SPRITES_BYTES, b"\x00"
            )
        elif block == "playerbmp":
            bs = []
            for line in block_lines:
                if line.strip().startswith(";"):
                    continue
                bs.extend(parse_byte_list(line))
            room["playerbmp"] = bytes(bs[:PLAYER_BMP_BYTES]).ljust(
                PLAYER_BMP_BYTES, b"\x00"
            )
        block = None
        block_lines.clear()

    for line_no, raw in enumerate(lines, start=1):
        raw_content = raw.split("#", 1)[0].rstrip("\r\n")
        line = raw_content.strip()
        if line.startswith("@"):
            flush_block()
            parts = line.split()
            tag = parts[0][1:].lower()
            if tag in (
                "tilemap",
                "tileudg",
                "guardiansprites",
                "playerbmp",
                "guardians",
            ):
                block = tag
                continue
            if tag == "room":
                room["id"] = int(parts[1])
            elif tag == "title":
                room["title"] = line.split(None, 1)[1]
            elif tag == "hudright":
                room["hudright"] = line.split(None, 1)[1]
            elif tag == "conn":
                room["conn"] = [parse_byte(x) for x in parts[1:5]]
            elif tag == "spawn":
                room["spawn"] = (int(parts[1]), int(parts[2]))
            elif tag == "border":
                room["border"] = parse_vic_color(parts[1])
            elif tag == "background":
                room["background"] = parse_vic_bg_color(parts[1:])
            elif tag == "belt":
                room["belt"] = int(parts[1])
            elif tag == "rope":
                room["rope"] = True
            elif tag == "playable":
                room["playable"] = True
            elif tag == "tilecolors":
                if len(parts[1:]) != TILE_COLOR_BYTES:
                    raise ValueError(
                        f"{loc(line_no)}@tilecolors needs {TILE_COLOR_BYTES} values (tile types 0-5)"
                    )
                room["tilecolors"] = [parse_vic_color(x) for x in parts[1:7]]
            elif tag in TILE_COLOR_TAGS:
                room["tilecolors"][TILE_COLOR_TAGS[tag]] = parse_vic_color(parts[1])
            elif tag in TILE_UDG_TAGS:
                content = line.split(None, 1)[1] if len(parts) > 1 else ""
                idx = TILE_UDG_TAGS[tag]
                room["tileudg"][idx] = parse_udg_bytes(content)
                if idx == 6:
                    room["itemudg_defined"] = True
            elif tag == "itemcolor":
                room["itemcolor"] = parse_vic_color(parts[1])
            elif tag == "logo":
                room["logo"] = parts[1] if len(parts) > 1 else LOGO_DEFAULT_PATH.name
            elif tag == "arrow":
                if room.get("arrow") is not None:
                    raise room_error(
                        room, f"{loc(line_no)}only one @arrow per room allowed"
                    )
                if len(parts) < 2:
                    raise room_error(room, f"{loc(line_no)}@arrow needs y/x/v/sound fields")
                m = ARROW_TAG_RE.match(line.split(None, 1)[1] if len(parts) > 1 else "")
                if not m:
                    raise room_error(
                        room,
                        f"{loc(line_no)}@arrow y=<py> x=<col> v=[-1|1] sound=<col>",
                    )
                y, x, v, sound = m.groups()
                v_i = int(v)
                if v_i not in (-1, 1):
                    raise room_error(room, f"{loc(line_no)}@arrow v must be -1 or 1")
                room["arrow"] = {
                    "y": int(y),
                    "x": int(x),
                    "v": v_i,
                    "sound": int(sound),
                }
            elif tag == "arrowudg":
                if room.get("arrow") is None:
                    raise room_error(
                        room, f"{loc(line_no)}@arrowudg requires @arrow in the same room"
                    )
                content = line.split(None, 1)[1] if len(parts) > 1 else ""
                room["arrow"]["udg"] = parse_udg_bytes(content)
            continue
        if block == "tilemap":
            if raw_content.lstrip().startswith(";"):
                continue
            if not raw_content and not line:
                continue
            block_lines.append(raw_content)
            continue
        if not line or line.startswith(";"):
            continue
        if block == "guardians":
            if line:
                room["guardians"].append(
                    parse_guardian_line(line, source=source, line_no=line_no)
                )
        elif block in ("tileudg", "guardiansprites", "playerbmp"):
            block_lines.append(line)
    flush_block()
    if room.get("logo"):
        room["tilemap"] = [normalize_tilemap_row("") for _ in range(TILEMAP_ROWS)]
        room["guardians"] = []
        room["items"] = [(0, 0)]
        room["ramp"] = RAMP_NONE
    else:
        room["items"] = extract_items_from_tilemap(room["tilemap"], room)
        room["ramp"] = infer_ramp_from_tilemap(room["tilemap"], room)
        validate_tilemap_belt(room["tilemap"], room["belt"], room)
        validate_guardians(room)
        validate_arrow_room(room)
    resolve_spawn(room)
    return room


def validate_arrow_room(room: dict) -> None:
    if not room.get("arrow"):
        return
    if room.get("rope"):
        raise room_error(room, "@arrow cannot be used with @rope in the same room")
    if len(room["guardians"]) > 4:
        raise room_error(
            room,
            "@arrow rooms allow at most 4 guardians (chr 46–57 reserved)",
        )


def grid_bytes(rows: list, name: str, room: dict | None = None) -> bytes:
    if len(rows) != TILEMAP_ROWS:
        raise room_error(
            room, f"{name}: expected {TILEMAP_ROWS} rows, got {len(rows)}"
        )
    out = bytearray()
    for r, row in enumerate(rows):
        row = normalize_tilemap_row(row)
        for ch in row:
            v = parse_tile_char(ch, room)
            out.append(v + TILE_CHR_BASE)
    out.extend([TILE_CHR_BASE] * WIDTH)  # HUD row 16 — title stamped later
    return bytes(out)


def ascii_to_rom_screen(ch: str) -> int:
    """Map ASCII to screen codes 128-255 (ROM charset with bit 7 set)."""
    code = ord(ch)
    if 65 <= code <= 90:
        return code + 64
    if 48 <= code <= 57:
        return code + 128
    return code + 128


def stamp_hud_title(tiles: bytearray, room: dict) -> None:
    title = room["title"].upper().ljust(HUD_TITLE_COLS)[:HUD_TITLE_COLS]
    base = (SCREEN_ROWS - 1) * WIDTH
    for i, ch in enumerate(title):
        tiles[base + i] = ascii_to_rom_screen(ch)


def stamp_logo_hud_title(tiles: bytearray, room: dict) -> None:
    """Logo room HUD row: @title left, optional @hudright flush to col 23."""
    left = room["title"].upper()
    right = room.get("hudright", "").upper()
    if len(left) + len(right) > WIDTH:
        raise room_error(
            room,
            f"@title + @hudright ({len(left)}+{len(right)}) exceed {WIDTH} HUD columns",
        )
    base = (SCREEN_ROWS - 1) * WIDTH
    for i in range(WIDTH):
        tiles[base + i] = ascii_to_rom_screen(" ")
    for i, ch in enumerate(left):
        tiles[base + i] = ascii_to_rom_screen(ch)
    start = WIDTH - len(right)
    for i, ch in enumerate(right):
        tiles[base + start + i] = ascii_to_rom_screen(ch)


def stamp_hud_men(tiles: bytearray) -> None:
    """HUD row 16 col 18 — Willy head (chr 13); count at col 19 runtime."""
    base = (SCREEN_ROWS - 1) * WIDTH + 18
    tiles[base] = MEN_CHR


def stamp_hud_item(tiles: bytearray) -> None:
    """HUD row 16 col 21 — items icon (chr 14); count drawn at cols 22-23 at runtime."""
    base = (SCREEN_ROWS - 1) * WIDTH + 21
    tiles[base] = HUD_ITEM_CHR


def belt_byte(speed: int) -> int:
    return speed & 0xFF


def load_resident_symbol(name: str) -> int:
    """Resident routine address from jsw.lbl (assemble jsw.prg first)."""
    if not JSW_LBL.is_file():
        raise ValueError(f"missing {JSW_LBL}; assemble jsw.prg before mkroom")
    pat = re.compile(rf"al C:([0-9a-f]+) \.{re.escape(name)}$", re.I)
    for line in JSW_LBL.read_text(encoding="utf-8").splitlines():
        m = pat.match(line)
        if m:
            return int(m.group(1), 16)
    raise ValueError(f"{name} not found in {JSW_LBL}")


def load_scan_key_row() -> int:
    return load_resident_symbol("ScanKeyRow")


def assemble_room_code(
    asm_name: str,
    defines: dict[str, int],
    slot_bytes: int | None = None,
) -> bytes:
    """Assemble a bake/*.asm template to raw bytes via ACME (-f plain)."""
    if not ACME.is_file():
        raise ValueError(f"ACME not found at {ACME}")
    asm_path = BAKE_DIR / asm_name
    if not asm_path.is_file():
        raise ValueError(f"missing bake source {asm_path}")
    tmp_dir = BAKE_DIR / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    out_path = tmp_dir / f"{asm_path.stem}.bin"
    args = [str(ACME), "-f", "plain", "-o", str(out_path)]
    if slot_bytes is not None:
        defines = {**defines, "SLOT_BYTES": slot_bytes}
    for key, value in defines.items():
        args.append(f"-D{key}=${value:x}")
    args.append(str(asm_path))
    result = subprocess.run(
        args,
        cwd=BAKE_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        msg = result.stderr.strip() or result.stdout.strip() or "ACME failed"
        raise ValueError(f"{asm_name}: {msg}")
    data = out_path.read_bytes()
    if slot_bytes is not None and len(data) != slot_bytes:
        raise ValueError(
            f"{asm_name}: size {len(data)} != slot {slot_bytes}"
        )
    return data


PICKUP_GOT_BASE = 0x100


def build_item_flicker(room: dict) -> bytes:
    """16 bytes at image_base ($1A05) — ACME bake/item_flicker.asm."""
    if room.get("logo") or not room["items"]:
        return noop_stub(ITEM_FLICKER_BYTES)
    col, row = room["items"][0]
    cell_off = row * WIDTH + col
    col_addr = COLOR_BASE + cell_off
    return assemble_room_code(
        "item_flicker.asm",
        {
            "PICKUP_GOT": PICKUP_GOT_BASE + room["id"],
            "COL_ADDR": col_addr,
        },
        ITEM_FLICKER_BYTES,
    )


def build_conveyor_animate(room: dict) -> bytes:
    """19 bytes at room_code_base ($1A15) — ACME bake/animate_conveyors.asm."""
    return assemble_room_code(
        "animate_conveyors.asm",
        {"BELT": belt_byte(room["belt"])},
        CONVEYOR_PREFIX_BYTES,
    )


def build_do_belt(room: dict) -> bytes:
    """DoBelt prefix slot — ACME bake/do_belt.asm."""
    return assemble_room_code(
        "do_belt.asm",
        {"BELT": belt_byte(room["belt"])},
        DO_BELT_SLOT_BYTES,
    )


def build_prefix(room: dict) -> bytes:
    return (
        build_item_flicker(room)
        + build_conveyor_animate(room)
        + build_do_belt(room)
        + build_tile_colors(room)
    )


def title_screen_msg_bytes() -> bytes:
    return bytes(ascii_to_rom_screen(c) for c in TITLE_MESSAGE.upper())


def build_title_screen() -> tuple[bytes, int]:
    """TitleScreen @ $1A05 in r62 (507 B max; logo UDGs load at $1C00)."""
    import sys

    repo = Path(__file__).resolve().parent.parent
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.title_tune_convert import TITLE_BAR_COUNT

    msg = title_screen_msg_bytes()
    tmp_dir = BAKE_DIR / ".tmp"
    tmp_dir.mkdir(exist_ok=True)
    msg_inc = tmp_dir / "title_msg.inc"
    msg_inc.write_text(
        "!byte " + ",".join(f"${b:02x}" for b in msg) + "\n",
        encoding="utf-8",
    )
    hud_row_off = (SCREEN_ROWS - 1) * WIDTH
    title_org = IMAGE_LOAD
    data = assemble_room_code(
        "title_screen.asm",
        {
            "ORG": title_org,
            "SCANKEYROW": load_resident_symbol("ScanKeyRow"),
            "WAITFORRASTER": load_resident_symbol("WaitForRaster"),
            "SETCOLORS": load_resident_symbol("SetColors"),
            "LOADROOMFILE": load_resident_symbol("LoadRoomFile"),
            "room_name": load_resident_symbol("room_name"),
            "TITLE_BAR_COUNT": TITLE_BAR_COUNT,
            "HUD_SCR": SCREEN_BASE + hud_row_off,
            "HUD_COL": COLOR_BASE + hud_row_off,
            "RED": VIC_COLOR["RED"],
            "MSG_LEN": len(msg),
            "HOLD_FRAMES": TITLE_HOLD_FRAMES,
            "SCROLL_FRAMES": TITLE_SCROLL_FRAMES,
        },
        TITLE_SCREEN_SLOT_BYTES,
    )
    end = len(data)
    while end > 0 and data[end - 1] == 0xEA:
        end -= 1
    return data, end


def load_joystick_patch_bytes() -> int:
    """Bytes from GetPlayerInput up to CopyDownGuardianData (no reloc)."""
    start = load_resident_symbol("GetPlayerInput")
    end = load_resident_symbol("CopyDownGuardianData")
    return end - start


def build_joystick_patch() -> bytes:
    """RJY.prg — stick-only GetPlayerInput overlay at resident GetPlayerInput."""
    org = load_resident_symbol("GetPlayerInput")
    patch_bytes = load_joystick_patch_bytes()
    body = assemble_room_code(
        "joystick_input.asm",
        {"PATCH_BYTES": patch_bytes},
    )
    over = len(body) - patch_bytes
    if over > 0:
        raise ValueError(
            f"joystick_input.asm: {len(body)} bytes, need to lose {over} "
            f"(slot is {patch_bytes} bytes at ${org:04X})"
        )
    return struct.pack("<H", org) + body


def write_joystick_patch(out_path: Path) -> None:
    data = build_joystick_patch()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(data)
    print(
        f"rjy -> {out_path.name} (rjy, {len(data)} bytes PRG @ ${data[0] | (data[1] << 8):04X})"
    )


def noop_stub(size: int) -> bytes:
    """Single RTS padded to slot size (unused item draw/erase on logo room)."""
    return bytes([0x60] + [0xEA] * (size - 1))


def logo_png_path(room: dict) -> Path:
    name = room["logo"]
    path = Path(name)
    if path.is_file():
        return path
    baked = BAKE_DIR / name
    if baked.is_file():
        return baked
    raise room_error(room, f"logo image not found: {name}")


def logo_white_index(im: Image.Image) -> int:
    """Palette index of the brightest colour (near-white ink in jswlogo.png)."""
    palette = im.getpalette()
    if not palette:
        raise ValueError("logo image has no palette")
    best_index = 0
    best_score = -1
    for i in range(len(palette) // 3):
        r, g, b = palette[i * 3 : i * 3 + 3]
        score = r + g + b
        if score > best_score:
            best_score = score
            best_index = i
    return best_index


def tile_to_udg_bytes(im: Image.Image, tx: int, ty: int, white_idx: int) -> bytes:
    px = im.load()
    x0, y0 = tx * 8, ty * 8
    out = bytearray(8)
    for y in range(8):
        byte = 0
        for x in range(8):
            if px[x0 + x, y0 + y] == white_idx:
                byte |= 1 << (7 - x)
        out[y] = byte
    return bytes(out)


def build_logo_payload(path: Path) -> tuple[bytes, bytearray]:
    """Return (udg_bytes from $1C00, 408-byte screen)."""
    if Image is None:
        raise ValueError("Pillow required for @logo rooms (pip install pillow)")
    im = Image.open(path)
    if im.mode != "P":
        raise ValueError(f"{path}: logo must be a palette PNG (P mode)")
    white_idx = logo_white_index(im)
    if im.width % 8 or im.height % 8:
        raise ValueError(f"{path}: logo size must be a multiple of 8 pixels")
    cols, rows = im.width // 8, im.height // 8
    if LOGO_ORIGIN_COL + cols > WIDTH or LOGO_ORIGIN_ROW + rows > TILEMAP_ROWS:
        raise ValueError(
            f"{path}: logo {cols}x{rows} at ({LOGO_ORIGIN_COL},{LOGO_ORIGIN_ROW}) "
            f"does not fit {WIDTH}x{TILEMAP_ROWS} playfield"
        )

    unique: list[bytes] = []
    key: dict[bytes, int] = {}
    screen = bytearray(TILE_BYTES)  # chr 0 = blank UDG (not 32 — that is UDG slot 32)

    for ty in range(rows):
        for tx in range(cols):
            tile = tile_to_udg_bytes(im, tx, ty, white_idx)
            sc = LOGO_ORIGIN_COL + tx
            sr = LOGO_ORIGIN_ROW + ty
            off = sr * WIDTH + sc
            if not any(tile):
                continue
            if tile not in key:
                key[tile] = len(unique) + 1
                unique.append(tile)
            screen[off] = key[tile]

    udg_bytes = bytearray(8)
    for tile in unique:
        udg_bytes.extend(tile)
    return bytes(udg_bytes), screen


def build_item_draw(room: dict) -> bytes:
    """11 bytes in meta tail — ACME bake/item_draw.asm."""
    if room.get("logo") or not room["items"]:
        return noop_stub(ITEM_DRAW_BYTES)
    col, row = room["items"][0]
    if not 0 <= col < WIDTH or not 0 <= row < TILEMAP_ROWS:
        raise room_error(room, f"item cell out of range: col={col} row={row}")
    cell_off = row * WIDTH + col
    scr_addr = SCREEN_BASE + cell_off
    map_addr = scr_addr + (MAP_BASE - SCREEN_BASE)
    return assemble_room_code(
        "item_draw.asm",
        {
            "SCR_ADDR": scr_addr,
            "MAP_ADDR": map_addr,
            "ITEM_CHR": ITEM_CHR,
            "TILE_ITEM": TILE_ITEM,
        },
        ITEM_DRAW_BYTES,
    )


def build_item_erase(room: dict) -> bytes:
    """11 bytes in meta tail — ACME bake/item_erase.asm."""
    if room.get("logo") or not room["items"]:
        return noop_stub(ITEM_ERASE_BYTES)
    col, row = room["items"][0]
    cell_off = row * WIDTH + col
    scr_addr = SCREEN_BASE + cell_off
    map_addr = scr_addr + (MAP_BASE - SCREEN_BASE)
    col_addr = COLOR_BASE + cell_off
    return assemble_room_code(
        "item_erase.asm",
        {
            "COL_ADDR": col_addr,
            "MAP_ADDR": map_addr,
            "EMPTY_COLOR": room["tilecolors"][0] & 0xFF,
            "TILE_EMPTY": TILE_EMPTY,
        },
        ITEM_ERASE_BYTES,
    )


def default_arrow_udg(velocity: int) -> bytes:
    if velocity == 1:
        return DEFAULT_ARROW_UDG_LTR
    if velocity == -1:
        return DEFAULT_ARROW_UDG_RTL
    raise room_error(None, f"arrow v must be -1 or 1, got {velocity}")


def arrow_convert_y(entity_y: int) -> int:
    """ConvertXYToScreenAddr row for a 1-row glyph on tile row entity_y >> 3."""
    return (((entity_y >> 3) + 1) << 3) & 0xFF


def arrow_bake_defines(room: dict) -> dict[str, int]:
    arrow = room["arrow"]
    v = arrow["v"]
    entity_y = arrow["y"] & 0xFF
    return {
        "COOKED_X": arrow["x"] & 0xFF,
        "COOKED_Y": arrow_convert_y(entity_y),
        "COOKED_SOUND_X": arrow["sound"] & 0xFF,
        "ARROW_V": 1 if v == 1 else 0xFF,
        "ARROW_TILE": ARROW_CHR,
        "ARROW_CODE_BYTES": ARROW_CODE_BYTES,
    }


def build_arrow(room: dict) -> bytes:
    code = assemble_room_code(
        "arrow.asm",
        arrow_bake_defines(room),
        None,
    )
    if len(code) > ARROW_CODE_BYTES:
        raise room_error(
            room,
            f"arrow.asm size {len(code)} exceeds {ARROW_CODE_BYTES} bytes",
        )
    return code


def build_master_bed_hook(endgame_items_required: int) -> bytes:
    """r35 only — Maria / ending hook @ $1CE0 (overflow $1AC8)."""
    data = assemble_room_code(
        "master_bedroom.asm",
        {
            "ORG": MASTER_BED_HOOK_ORG,
            "ENDGAME_ITEMS_REQUIRED": endgame_items_required,
        },
    )
    if len(data) > MASTER_BED_HOOK_MAX_BYTES:
        raise ValueError(
            f"master_bedroom.asm: size {len(data)} > {MASTER_BED_HOOK_MAX_BYTES}"
        )
    return data


def splice_master_bed_hook(
    sprites: bytearray, pad: bytearray, hook: bytes
) -> None:
    if len(hook) > MASTER_BED_HOOK_BYTES:
        overflow = hook[MASTER_BED_HOOK_BYTES :]
        sprites[MASTER_BED_SPRITE_HOOK_OFF : MASTER_BED_SPRITE_HOOK_OFF + len(overflow)] = (
            overflow
        )
    pad[MASTER_BED_PAD_HOOK_OFF : MASTER_BED_PAD_HOOK_OFF + min(MASTER_BED_HOOK_BYTES, len(hook))] = (
        hook[:MASTER_BED_HOOK_BYTES]
    )


# py is head Y (single pixels); ramp_y runtime is feet Y (head + 16 on surface).
RAMP_FEET_OFFSET = 16
RAMP_BOUNDS_EXTEND = 4
# UP_LEFT only: lowers feet 2px on \ ramps for visual alignment and so the
# right-exit snap is py-aligned (Collide clears xadd at look_below_2).  See
# willy.asm CollideLeftRight — skip lr_touch_c while is_on_ramp (walls under \).
RAMP_UP_LEFT_RY_ADJUST = 2
RAMP_RY_TOE: dict[int, int] = {
    RAMP_UP_RIGHT: 0,
    RAMP_UP_LEFT: 6,
}


def ramp_surface_abs(
    px: int,
    col_start: int,
    col_end: int,
    row_start: int,
    row_step: int,
    ramp_type: int,
) -> int:
    """Absolute Y of ramp walking surface at px."""
    mid_col = (px + 3) >> 2
    feet_row = row_start + (mid_col - col_start) * row_step
    x_offset = ((px + 3) & 3) * 2
    if ramp_type == RAMP_UP_RIGHT:
        y_surface = 6 - x_offset
    else:
        y_surface = x_offset
    return feet_row * 8 + y_surface


def ramp_baked_ry(
    rx1: int,
    col_start: int,
    col_end: int,
    row_start: int,
    row_step: int,
    ramp_type: int,
) -> int:
    """Baked meta ry: feet Y at ramp entry px rx1."""
    toe = RAMP_RY_TOE.get(ramp_type, 0)
    return (
        ramp_surface_abs(rx1, col_start, col_end, row_start, row_step, ramp_type)
        - toe
    )


def ramp_upper_row(
    col_start: int,
    col_end: int,
    row_start: int,
    row_step: int,
    ramp_type: int,
) -> int:
    """Tilemap row of the upper (smallest screen y) end of the ramp."""
    upper_col = col_end if ramp_type == RAMP_UP_RIGHT else col_start
    return row_start + (upper_col - col_start) * row_step


def ramp_baked_ymin(
    col_start: int,
    col_end: int,
    row_start: int,
    row_step: int,
    ramp_type: int,
) -> int:
    """Minimum feet ramp_y at the upper (smallest Y) end of the ramp."""
    toe = RAMP_RY_TOE.get(ramp_type, 0)
    if ramp_type == RAMP_UP_RIGHT:
        upper_px = col_end * 4
    else:
        upper_px = col_start * 4
    return (
        ramp_surface_abs(
            upper_px, col_start, col_end, row_start, row_step, ramp_type
        )
        - toe
    )


def derive_ramp_bounds(
    tilemap: list, ramp_type: int, room: dict | None = None
) -> tuple[int, int, int, int]:
    """Return (col_start, col_end, row_start, row_step) for room meta."""
    cells: list[tuple[int, int]] = []
    for row, line in enumerate(tilemap):
        if row >= TILEMAP_ROWS:
            continue
        for col, ch in enumerate(line):
            if ch in ("/", "\\"):
                cells.append((col, row))

    if ramp_type == RAMP_NONE:
        return (0, 0, 0, 0)

    if not cells:
        raise room_error(room, "ramp type set but no ramp tiles (/ or \\) in tilemap")

    col_start = min(col for col, _ in cells)
    col_end = max(col for col, _ in cells)

    by_col: dict[int, list[int]] = {}
    for col, row in cells:
        by_col.setdefault(col, []).append(row)

    for col in range(col_start, col_end + 1):
        if col not in by_col or len(by_col[col]) != 1:
            raise room_error(room, f"ramp gap or multiple tiles in column {col}")

    row_start = by_col[col_start][0]
    if col_end == col_start:
        row_step = 0
    else:
        row_step = by_col[col_start + 1][0] - row_start
        if row_step not in (-1, 0, 1):
            raise room_error(room, f"invalid ramp row step {row_step}")
        for col in range(col_start, col_end + 1):
            expected = row_start + (col - col_start) * row_step
            if by_col[col][0] != expected:
                raise room_error(
                    room,
                    f"ramp row mismatch at col {col}: expected {expected}, got {by_col[col][0]}",
                )

    return (col_start, col_end, row_start, row_step & 0xFF)


def derive_ramp_params(
    tilemap: list, ramp_type: int, room: dict | None = None
) -> tuple[int, int, int, int, int, int]:
    """Return baked (rx1, rx2, ry, E, A, ymin) px bounds and slope sign."""
    if ramp_type == RAMP_NONE:
        return (RAMP_BOUNDS_NONE, RAMP_BOUNDS_NONE, 0, 0, 0, 0)

    col_start, col_end, row_start, row_step_b = derive_ramp_bounds(
        tilemap, ramp_type, room
    )
    row_step = row_step_b if row_step_b < 128 else row_step_b - 256

    if ramp_type == RAMP_UP_RIGHT:
        rx1 = col_start * 4 - 4
        rx2 = col_end * 4   # exclusive upper bound
        e, a = 0xFF, 1
    else:
        rx1 = col_start * 4
        rx2 = col_end * 4 + 4   # exclusive upper bound
        e, a = 0, 0

    ymin = ramp_baked_ymin(
        col_start, col_end, row_start, row_step, ramp_type
    )

    if ramp_type == RAMP_UP_RIGHT:
        rx2 += RAMP_BOUNDS_EXTEND
    else:
        rx1 -= RAMP_BOUNDS_EXTEND

    ry = ramp_baked_ry(
        rx1, col_start, col_end, row_start, row_step, ramp_type
    )
    if ramp_type == RAMP_UP_LEFT:
        ry += RAMP_UP_LEFT_RY_ADJUST
    return (rx1, rx2, ry, e, a, ymin)


def build_meta(room: dict) -> bytes:
    g = room["guardians"]
    if len(g) > MAX_GUARDIANS:
        raise room_error(room, f"too many guardians ({len(g)}, max {MAX_GUARDIANS})")
    meta = bytearray()
    meta.append(len(g))
    meta.append((room["background"] << 4) | 8 | room["border"])  # full $900F
    meta.append(room["spawn"][0] & 0xFF)
    meta.append(room["spawn"][1] & 0xFF)
    meta.append(belt_byte(room["belt"]))
    meta.append(room["ramp"] & 0xFF)
    rx1, rx2, ry, e, a, ymin = derive_ramp_params(
        room["tilemap"], room["ramp"], room
    )
    meta.append(rx1 & 0xFF)
    meta.append(rx2 & 0xFF)
    meta.append(ry & 0xFF)
    meta.append(e & 0xFF)
    meta.append(a & 0xFF)
    meta.append(ymin & 0xFF)
    meta.extend(room["conn"])
    meta.extend(build_item_draw(room))
    meta.extend(build_item_erase(room))
    if len(meta) != META_SIZE:
        raise room_error(room, f"meta size {len(meta)} != {META_SIZE}")
    return bytes(meta)


def build_guardian_data(room: dict) -> bytes:
    out = bytearray(GUARDIAN_DATA_BYTES)
    for i, g in enumerate(room["guardians"]):
        base = i * GUARDIAN_RECORD_BYTES
        out[base + G_OFF_X] = g["x"]
        out[base + G_OFF_Y] = g["y"]
        out[base + G_OFF_MIN] = g["min"]
        out[base + G_OFF_MAX] = g["max"]
        out[base + G_OFF_VEL] = g["vel"]
        out[base + G_OFF_FRAME] = 0
        out[base + G_OFF_FMIN] = g["fmin"]
        out[base + G_OFF_FCTL] = g["fctl"]
        out[base + G_OFF_COLOR] = g["color"]
        out[base + G_OFF_AXIS] = g["axis"]
    return bytes(out)


def build_hud_udg() -> bytes:
    """Fixed HUD icons: chr 13 men, chr 14 items (see DEFAULT_*_UDG)."""
    return DEFAULT_MEN_UDG + DEFAULT_HUD_ITEM_UDG


def build_udg(room: dict) -> bytes:
    out = bytearray()
    out.extend(room["tileudg"][6])   # item → chr 15
    for i in range(6):
        out.extend(room["tileudg"][i])  # tiles 0–5 → chr 16–21
    return bytes(out)


def build_tile_colors(room: dict) -> bytes:
    colors = room["tilecolors"]
    if len(colors) != TILE_COLOR_BYTES:
        raise room_error(
            room, f"tilecolors length {len(colors)} != {TILE_COLOR_BYTES}"
        )
    return bytes(colors)


def deinterleave_guardian_frame(frame: bytes) -> bytes:
    """Skool L,R pairs -> column-major 16+16 (matches CopyDownGuardianBmp)."""
    out = bytearray(32)
    for row in range(16):
        out[row] = frame[row * 2]
        out[row + 16] = frame[row * 2 + 1]
    return bytes(out)


def deinterleave_guardian_sprites(
    data: bytes, nbytes: int = GUARDIAN_SPRITES_BYTES
) -> bytes:
    data = data[:nbytes].ljust(nbytes, b"\x00")
    return b"".join(
        deinterleave_guardian_frame(data[i : i + 32])
        for i in range(0, nbytes, 32)
    )


def build_tail(room: dict) -> bytes:
    tail = bytearray(TAIL_BYTES)
    meta = build_meta(room)
    gdata = build_guardian_data(room)
    tail[0:META_SIZE] = meta
    tail[META_OFF_ROPE] = 1 if room.get("rope") else 0
    tail[META_OFF_HAS_ARROW] = 1 if room.get("arrow") else 0
    off = TAIL_OFF_GUARDIAN_DATA
    tail[off : off + GUARDIAN_DATA_BYTES] = gdata
    return bytes(tail)


def load_player_bmp_file(path: Path) -> bytes:
    """256-byte Willy sprite from Skool interleaved text file."""
    if not path.is_file():
        raise ValueError(f"missing {path}")
    bs: list[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(";") or not line.strip():
            continue
        bs.extend(parse_byte_list(line))
    if len(bs) != PLAYER_BMP_BYTES:
        raise ValueError(
            f"{path}: expected {PLAYER_BMP_BYTES} bytes, got {len(bs)}"
        )
    return deinterleave_guardian_sprites(bytes(bs), PLAYER_BMP_BYTES)


def load_default_player_bmp() -> bytes:
    return load_player_bmp_file(DEFAULT_PLAYER_BMP_PATH)


def load_nightmare_player_bmp() -> bytes:
    """256-byte Willy sprite for the Nightmare Room (room 29)."""
    return load_player_bmp_file(NIGHTMARE_PLAYER_BMP_PATH)


def player_bmp_for_room(room: dict) -> bytes:
    if room["id"] == NIGHTMARE_ROOM_ID:
        return load_nightmare_player_bmp()
    return room["playerbmp"] or load_default_player_bmp()


def build_logo_room_image(room: dict) -> bytes:
    """Title room: UDGs land at $1C00, screen at $1E00."""
    udg_data, screen = build_logo_payload(logo_png_path(room))
    if len(udg_data) > LOGO_UDG_MAX_BYTES:
        raise room_error(
            room,
            f"logo needs {len(udg_data)} UDG bytes at $1C00; max {LOGO_UDG_MAX_BYTES}",
        )

    stamp_logo_hud_title(screen, room)
    tail = build_tail(room)
    title_screen, title_used = build_title_screen()
    print(
        f"  title screen @ ${IMAGE_LOAD:04X}: "
        f"{title_used}/{TITLE_SCREEN_SLOT_BYTES} bytes used "
        f"({TITLE_SCREEN_SLOT_BYTES - title_used} free)"
    )

    blob = bytearray(ROOM_IMAGE_SIZE)
    blob[0 : len(title_screen)] = title_screen
    blob[LOGO_UDG_OFF : LOGO_UDG_OFF + len(udg_data)] = udg_data
    blob[SCREEN_BASE - IMAGE_LOAD : SCREEN_BASE - IMAGE_LOAD + TILE_BYTES] = screen
    blob[-TAIL_BYTES:] = tail
    return bytes(blob)


def build_room_image(
    room: dict,
    endgame_items_required: int | None = None,
    rooms_dir: Path | None = None,
) -> bytes:
    """RAM image loaded at $1A05 (1531 bytes)."""
    if room.get("logo"):
        return build_logo_room_image(room)
    tiles = bytearray(grid_bytes(room["tilemap"], "tilemap", room))
    stamp_hud_title(tiles, room)
    stamp_hud_men(tiles)
    stamp_hud_item(tiles)

    raw = room["guardiansprites"] or bytes(GUARDIAN_SPRITES_BYTES)
    sprites = bytearray(deinterleave_guardian_sprites(raw))
    player = player_bmp_for_room(room)
    hud_udg = build_hud_udg()
    udg = build_udg(room)
    pad = bytearray(RUNTIME_UDG_PAD)
    if room.get("arrow"):
        off = (ARROW_CHR - GUARDIAN_CHR) * 8
        arrow = room["arrow"]
        udg_bytes = arrow.get("udg") or default_arrow_udg(arrow["v"])
        pad[off : off + 8] = udg_bytes
        code = build_arrow(room)
        pad[off + 8 : off + 8 + len(code)] = code
    if room["id"] == ROOM_MASTER_BED:
        if rooms_dir is None:
            raise room_error(room, "rooms_dir required for master bedroom hook bake")
        threshold = (
            endgame_items_required
            if endgame_items_required is not None
            else count_items(rooms_dir)
        )
        hook = build_master_bed_hook(threshold)
        splice_master_bed_hook(sprites, pad, hook)
    tail = build_tail(room)
    prefix = build_prefix(room)

    blob = (
        prefix
        + bytes(sprites)
        + player
        + hud_udg
        + udg
        + bytes(pad)
        + tiles
        + tail
    )
    if len(blob) != ROOM_IMAGE_SIZE:
        raise room_error(room, f"room image size {len(blob)} != {ROOM_IMAGE_SIZE}")
    return blob


def build_room_prg(
    room: dict,
    endgame_items_required: int | None = None,
    rooms_dir: Path | None = None,
) -> bytes:
    return struct.pack("<H", IMAGE_LOAD) + build_room_image(
        room, endgame_items_required, rooms_dir
    )


def room_dos_name(room_id: int) -> str:
    """KERNAL LOAD filename: R + zero-padded decimal, e.g. room 33 -> r33."""
    return f"r{room_id:02d}"


def scan_playable_header(text: str) -> tuple[int | None, bool]:
    """Read @room id and @playable from header tags only (no full parse)."""
    room_id: int | None = None
    playable = False
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line.startswith("@"):
            continue
        parts = line.split()
        tag = parts[0][1:].lower()
        if tag == "room" and len(parts) > 1:
            room_id = int(parts[1])
        elif tag == "playable":
            playable = True
    return room_id, playable


def playable_status(
    indir: Path,
) -> tuple[list[tuple[int, str, str]], list[tuple[int, str, str]]]:
    """Scan room*.txt; return (playable, need_work) as (id, filename, title) tuples."""
    playable: list[tuple[int, str, str]] = []
    need_work: list[tuple[int, str, str]] = []
    for src in sorted(indir.glob("room*.txt")):
        text = src.read_text(encoding="utf-8")
        room_id, is_playable = scan_playable_header(text)
        if room_id is None:
            room_id = int(src.stem[4:]) if src.stem[4:].isdigit() else -1
        title = scan_room_title(text)
        entry = (room_id, src.name, title)
        if is_playable:
            playable.append(entry)
        else:
            need_work.append(entry)
    return playable, need_work


def count_items(indir: Path) -> int:
    """Total pickup markers ('+') across playable rooms (excludes @logo)."""
    total = 0
    for src in sorted(indir.glob("room*.txt")):
        text = src.read_text(encoding="utf-8")
        room = parse_room(text, source=src)
        if room.get("logo"):
            continue
        total += len(room["items"])
    return total


LINT_SOLID_CHARS = frozenset("FW/\\<>")
LINT_ITEM_MAX_TILE_DIST = 4
LINT_ITEM_MAX_ABOVE = 5


def _tilemap_solid_cells(tilemap: list) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for row, line in enumerate(tilemap):
        if row >= TILEMAP_ROWS:
            continue
        for col, ch in enumerate(normalize_tilemap_row(line)):
            if ch in LINT_SOLID_CHARS:
                cells.append((col, row))
    return cells


def _chebyshev(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def _nearest_solid_tiles(pos: tuple[int, int], solids: list[tuple[int, int]]) -> int:
    if not solids:
        return 999
    return min(_chebyshev(pos, s) for s in solids)


def _solid_reachable(pos: tuple[int, int], solids: list[tuple[int, int]]) -> bool:
    """True if pickup is within Chebyshev distance or directly above solid (<=5 rows)."""
    col, row = pos
    for sc, sr in solids:
        if sc == col and sr > row and sr - row <= LINT_ITEM_MAX_ABOVE:
            return True
        if _chebyshev(pos, (sc, sr)) <= LINT_ITEM_MAX_TILE_DIST:
            return True
    return False


def lint_room(room: dict) -> list[str]:
    """Return pickup placement warnings for one parsed room."""
    if room.get("logo") or not room["items"]:
        return []
    warnings: list[str] = []
    if not room.get("itemudg_defined"):
        warnings.append("missing @itemudg")
    elif not any(room["tileudg"][6]):
        warnings.append("@itemudg is all zeros")
    solids = _tilemap_solid_cells(room["tilemap"])
    for col, row in room["items"]:
        pos = (col, row)
        if room["itemcolor"] == VIC_COLOR["BLK"]:
            warnings.append(f"@itemcolor BLK (pickup at col {col} row {row})")
        dist = _nearest_solid_tiles(pos, solids)
        if not _solid_reachable(pos, solids):
            warnings.append(
                f"pickup >{LINT_ITEM_MAX_TILE_DIST} tiles from nearest "
                f"F/W/ramp/belt (col {col} row {row}, nearest {dist} tiles)"
            )
    return warnings


def print_room_lint(indir: Path) -> int:
    """Print pickup lint warnings; return warning count."""
    count = 0
    for src in sorted(indir.glob("room*.txt")):
        room = parse_room(src.read_text(encoding="utf-8"), source=src)
        for msg in lint_room(room):
            title = room.get("title") or ""
            head = f"{src.name} — {title}" if title else src.name
            print(f"warning: {head}: {msg}", file=sys.stderr)
            count += 1
    if count:
        print(f"{count} pickup lint warning(s)", file=sys.stderr)
    return count


def print_arrow_report(indir: Path) -> None:
    """List arrow rooms."""
    for src in sorted(indir.glob("room*.txt")):
        text = src.read_text(encoding="utf-8")
        room = parse_room(text, source=src)
        if not room.get("arrow"):
            continue
        title = room.get("title") or ""
        head = f"{src.name} — {title}" if title else src.name
        print(f"arrow: {head} v={room['arrow']['v']} y={room['arrow']['y']} "
              f"x={room['arrow']['x']} sound={room['arrow']['sound']}")


def print_playable_summary(indir: Path) -> None:
    playable, need_work = playable_status(indir)
    total = len(playable) + len(need_work)
    print(
        f"playable: {len(playable)}/{total} rooms done, {len(need_work)} need work"
    )
    if need_work:
        for room_id, filename, title in sorted(need_work, key=lambda x: x[0]):
            name = title or "(untitled)"
            print(f"  room {room_id:2d} — {name} ({filename})")


def convert_file(
    src: Path,
    outstem: Path,
    room: dict | None = None,
    endgame_items_required: int | None = None,
    rooms_dir: Path | None = None,
) -> None:
    if room is None:
        room = parse_room(src.read_text(encoding="utf-8"), source=src)
    if rooms_dir is None:
        rooms_dir = src.parent
    hook_override = (
        endgame_items_required if room["id"] == ROOM_MASTER_BED else None
    )
    data = build_room_prg(room, hook_override, rooms_dir)
    outstem.parent.mkdir(parents=True, exist_ok=True)
    outstem.write_bytes(data)
    print(
        f"{src.name} -> {outstem.name} ({room_dos_name(room['id'])}, {len(data)} bytes PRG @ ${IMAGE_LOAD:04X}, room {room['id']})"
    )


def main():
    ap = argparse.ArgumentParser(description="Convert JSW roomNN.txt files to PRG binaries")
    ap.add_argument("input", nargs="?", help="roomNN.txt file or directory with --all")
    ap.add_argument("output", nargs="?", help="output file stem e.g. rooms/out/33")
    ap.add_argument("--all", action="store_true", help="convert all room*.txt in input dir")
    ap.add_argument(
        "--status",
        action="store_true",
        help="report @playable room counts only (no build)",
    )
    ap.add_argument(
        "--count-items",
        action="store_true",
        help="print total '+' pickup count for rooms dir (for -DITEMS_REQUIRED)",
    )
    ap.add_argument(
        "--endgame-items-required",
        type=int,
        metavar="N",
        dest="endgame_items_required",
        help="r35 master_bed_hook threshold only (does not affect pickup_got)",
    )
    ap.add_argument(
        "--lint",
        action="store_true",
        help="warn on BLK @itemcolor, missing/blank @itemudg, or pickups far from F/W/ramp/belt",
    )
    ap.add_argument(
        "--arrow-report",
        action="store_true",
        help="list @arrow rooms",
    )
    ap.add_argument(
        "--emit-arrows",
        action="store_true",
        help="emit @arrow tags from Spectrum data into non-rope roomNN.txt files",
    )
    args = ap.parse_args()
    if args.emit_arrows:
        from arrow_extract import emit_arrows

        indir = Path(args.input or "rooms")
        if not indir.is_dir():
            ap.error(f"not a directory: {indir}")
        emit_arrows(indir)
        return
    if args.arrow_report:
        indir = Path(args.input or "rooms")
        if not indir.is_dir():
            ap.error(f"not a directory: {indir}")
        print_arrow_report(indir)
        return
    if args.count_items:
        indir = Path(args.input or "rooms")
        if not indir.is_dir():
            ap.error(f"not a directory: {indir}")
        print(count_items(indir))
        return
    if args.lint:
        indir = Path(args.input or "rooms")
        if not indir.is_dir():
            ap.error(f"not a directory: {indir}")
        if print_room_lint(indir):
            sys.exit(1)
        return
    if args.status:
        indir = Path(args.input or "rooms")
        if not indir.is_dir():
            ap.error(f"not a directory: {indir}")
        print_playable_summary(indir)
        return
    if args.all:
        indir = Path(args.input or "rooms")
        outdir = Path(args.output or "rooms/out")
        errors: list[tuple[Path, str]] = []
        endgame_override = args.endgame_items_required
        for src in sorted(indir.glob("room*.txt")):
            text = ""
            room = None
            try:
                text = src.read_text(encoding="utf-8")
                room = parse_room(text, source=src)
                convert_file(
                    src,
                    outdir / str(room["id"]),
                    room=room,
                    endgame_items_required=endgame_override,
                    rooms_dir=indir,
                )
            except (ValueError, OSError) as e:
                errors.append((src, str(e)))
                print(
                    format_build_error(src, e, text=text or None, room=room),
                    file=sys.stderr,
                )
        if errors:
            print(f"\n{len(errors)} room(s) failed", file=sys.stderr)
            sys.exit(1)
        write_joystick_patch(outdir / "rjy")
        print_playable_summary(indir)
        print_room_lint(indir)
        return
    if not args.input or not args.output:
        ap.error("need input and output, or --all")
    src = Path(args.input)
    text = ""
    room = None
    try:
        text = src.read_text(encoding="utf-8")
        room = parse_room(text, source=src)
        convert_file(
            src,
            Path(args.output),
            room=room,
            endgame_items_required=args.endgame_items_required,
            rooms_dir=src.parent,
        )
    except (ValueError, OSError) as e:
        print(format_build_error(src, e, text=text or None, room=room), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
