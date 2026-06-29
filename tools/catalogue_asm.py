"""Emit catalogue as commented ACME asm (bake/catalogue.asm + bake/rooms/*.asm)."""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

BAKE_DIR = Path(__file__).resolve().parent.parent / "bake"
ROOMS_ASM_DIR = BAKE_DIR / "rooms"
CATALOGUE_ASM = BAKE_DIR / "catalogue.asm"
VIC_COLORS_ASM = BAKE_DIR / "vic_colors.asm"

SET_ENTRY_BYTES = 4
SCREEN_WIDTH = 24
SCREEN_BASE = 0x1000
PICKUP_NONE = 0xFFFF
UDG_FIXED_BYTES = 24

FLAG_NASTY = 0x01
FLAG_RAMP = 0x02
FLAG_CONVEYOR = 0x04
FLAG_ROPE = 0x08
FLAG_ARROW = 0x10

VIC_COLOR_NAMES: dict[int, str] = {
    0: "BLK",
    1: "WHT",
    2: "RED",
    3: "CYN",
    4: "PUR",
    5: "GRN",
    6: "BLU",
    7: "YEL",
    8: "ORN",
    9: "LIGHT ORN",
    10: "LIGHT RED",
    11: "LIGHT CYN",
    12: "LIGHT PUR",
    13: "LIGHT GRN",
    14: "LIGHT BLU",
    15: "LIGHT YEL",
}

TILE_TYPE_NAMES = ("empty", "floor", "wall", "nasty", "ramp", "belt", "pickup")


@dataclass(frozen=True)
class RoomSection:
    name: str
    comment: str
    data: bytes
    extra: Mapping[str, Any] = field(default_factory=dict)


def byte_lines(data: bytes, *, indent: str = "    ", per_line: int = 16) -> list[str]:
    if not data:
        return [f"{indent}; (empty)"]
    lines: list[str] = []
    for i in range(0, len(data), per_line):
        chunk = data[i : i + per_line]
        hexes = ", ".join(f"${b:02x}" for b in chunk)
        lines.append(f"{indent}!byte {hexes}")
    return lines


def vic_name(value: int) -> str:
    return VIC_COLOR_NAMES.get(value & 0xFF, str(value))


def flags_binary(flags: int) -> str:
    return f"%{flags & 0xFF:08b}"


def flags_asm(flags: int) -> str:
    parts = []
    if flags & FLAG_NASTY:
        parts.append("FLAG_NASTY")
    if flags & FLAG_RAMP:
        parts.append("FLAG_RAMP")
    if flags & FLAG_CONVEYOR:
        parts.append("FLAG_CONVEYOR")
    if flags & FLAG_ROPE:
        parts.append("FLAG_ROPE")
    if flags & FLAG_ARROW:
        parts.append("FLAG_ARROW")
    return "|".join(parts) if parts else "0"


def signed_byte(value: int) -> int:
    value &= 0xFF
    return value - 256 if value >= 128 else value


def format_meta8(data: bytes) -> list[str]:
    conn = data[0:4]
    spawn_x, spawn_y = data[4], data[5]
    flags = data[6]
    vic = data[7]
    border = vic & 0x07
    bg = (vic >> 4) & 0x0F
    vic_expr = (bg << 4) | border
    flag_bits = (
        (FLAG_NASTY, "nasty"),
        (FLAG_RAMP, "ramp"),
        (FLAG_CONVEYOR, "conveyor"),
        (FLAG_ROPE, "rope"),
        (FLAG_ARROW, "arrow"),
    )
    flag_names = [name for bit, name in flag_bits if flags & bit]
    flag_note = "|".join(flag_names) if flag_names else "none"
    return [
        "; conn N E S W",
        f"    !byte {conn[0]}, {conn[1]}, {conn[2]}, {conn[3]}",
        f"; spawn px py",
        f"    !byte {spawn_x}, {spawn_y}",
        f"; flags: {flag_note}",
        f"    !byte {flags_asm(flags)}",
        f"; border {vic_name(border)}, background {vic_name(bg)};"
        f" (bg<<4)|border = {vic_expr} (byte ${vic:02x} includes VIC bit 3)",
        f"    !byte {vic}",
    ]


def format_tile_colors(data: bytes) -> list[str]:
    names = [vic_name(b) for b in data]
    return [
        "; types 0-5: empty floor wall nasty ramp belt",
        f"    !byte {', '.join(names)}",
    ]


def format_title(data: bytes) -> list[str]:
    text = data[:-1].decode("ascii", errors="replace")
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return [f'; "{text}"', f'    !pet "{escaped}", 0']


def format_rle(data: bytes) -> list[str]:
    lines = [f"; {len(data)} tokens, 384 cells — each byte (N<<3)|C"]
    tokens: list[str] = []
    for b in data:
        run = (b >> 3) & 0x1F
        cell = b & 7
        tokens.append(f"({run}<<3)|{cell}")
        if len(tokens) >= 8:
            lines.append("    !byte " + ", ".join(tokens))
            tokens = []
    if tokens:
        lines.append("    !byte " + ", ".join(tokens))
    return lines


def format_pickup(data: bytes, *, rid: int, extra: Mapping[str, Any]) -> list[str]:
    offset = struct.unpack("<H", data)[0]
    if offset == PICKUP_NONE:
        return ["; no pickup", "    !word $ffff"]
    return [f"    !word screen_base + {offset}"]


def _udg_block(chunk: bytes, name: str) -> list[str]:
    hexes = ", ".join(f"${b:02x}" for b in chunk)
    return [f"; {name}", f"    !byte {hexes}"]


def format_udg(data: bytes, extra: Mapping[str, Any]) -> list[str]:
    flags = int(extra.get("flags", 0))
    lines = [
        "; types 1 floor, 2 wall, 6 pickup always; 3 nasty / 4 ramp / 5 belt when flagged",
        "; type 0 empty is always zero — not stored",
    ]
    pos = 0
    for name in ("floor", "wall", "pickup"):
        lines.extend(_udg_block(data[pos : pos + 8], name))
        pos += 8
    optional = (
        (FLAG_NASTY, "nasty"),
        (FLAG_RAMP, "ramp"),
        (FLAG_CONVEYOR, "belt"),
    )
    for bit, name in optional:
        if flags & bit:
            lines.extend(_udg_block(data[pos : pos + 8], name))
            pos += 8
    return lines


def format_guardians(data: bytes, extra: Mapping[str, Any]) -> list[str]:
    count = data[0]
    lines = [
        "; count, then 8 B per guardian:",
        ";   x, y, min, max, vel, color, axis (0=horizontal 1=vertical), set_idx",
        f"    !byte {count}",
    ]
    guardians = extra.get("guardians") or []
    pos = 1
    for i in range(count):
        gbytes = data[pos : pos + 8]
        pos += 8
        x, y, gmin, gmax, vel, color, axis, set_idx = gbytes
        vel_s = signed_byte(vel)
        sprite = ""
        if i < len(guardians):
            sprite = guardians[i].get("sprite", "")
        axis_name = "horizontal" if axis == 0 else "vertical"
        note = f"; {sprite}: x={x} y={y} min={gmin} max={gmax} vel={vel_s} " \
               f"{vic_name(color)} {axis_name} set={set_idx}"
        lines.append(note)
        lines.append(
            f"    !byte {x}, {y}, {gmin}, {gmax}, {vel}, "
            f"{vic_name(color)}, {axis}, {set_idx}"
        )
    return lines


def format_section(sec: RoomSection, *, rid: int) -> list[str]:
    if sec.name == "meta8":
        return format_meta8(sec.data)
    if sec.name == "tile_colors":
        return format_tile_colors(sec.data)
    if sec.name == "title":
        return format_title(sec.data)
    if sec.name == "rle_tilemap":
        return format_rle(sec.data)
    if sec.name == "pickup":
        return format_pickup(sec.data, rid=rid, extra=sec.extra)
    if sec.name == "tile_udg":
        return format_udg(sec.data, sec.extra)
    if sec.name == "guardians":
        return format_guardians(sec.data, sec.extra)
    if sec.comment:
        return [f"; {sec.comment}", *byte_lines(sec.data)]
    return byte_lines(sec.data)


def write_room_asm(path: Path, rid: int, title: str, sections: list[RoomSection]) -> None:
    lines = [
        f"; room {rid:02d} — {title}",
        f"; Generated by mkcatalogue.py — do not edit.",
        "",
        '!source "bake/room_record.asm"',
        '!source "bake/vic_colors.asm"',
        "",
        f"room{rid:02d}_data",
    ]
    for sec in sections:
        lines.append(f"; --- {sec.name} ---")
        lines.extend(format_section(sec, rid=rid))
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_catalogue_asm(
    *,
    room_builds: list,
    pool,
    report: dict,
) -> None:
    ROOMS_ASM_DIR.mkdir(parents=True, exist_ok=True)

    for old in ROOMS_ASM_DIR.glob("room*.asm"):
        old.unlink()

    for rb in room_builds:
        write_room_asm(
            ROOMS_ASM_DIR / f"room{rb.rid:02d}.asm",
            rb.rid,
            rb.title,
            rb.sections,
        )

    lines: list[str] = [
        "; JSW-Tape room catalogue — generated by mkcatalogue.py",
        "; CatalogueImage in catalogue_data.asm points here.",
        "",
        "RoomRecordPtrs",
    ]
    for rb in room_builds:
        lines.append(f"    !word room{rb.rid:02d}_data")
    lines.extend(["", "; --- room records ---", ""])
    for rb in room_builds:
        lines.append(f'!source "bake/rooms/room{rb.rid:02d}.asm"')
        lines.append("")

    sets_blob = pool.sets_blob()
    lines.extend(["CatalogueSets", f"; {len(pool.sets)} sets x {SET_ENTRY_BYTES} bytes"])
    for i in range(0, len(sets_blob), SET_ENTRY_BYTES):
        chunk = sets_blob[i : i + SET_ENTRY_BYTES]
        start = chunk[0] | (chunk[1] << 8)
        count = chunk[2]
        flags = chunk[3]
        lines.append(f"; set {i // SET_ENTRY_BYTES}: start={start} count={count} flags=${flags:02x}")
        lines.extend(byte_lines(chunk))
    lines.append("")

    pool_blob = pool.frames_blob()
    lines.extend(
        [
            "CataloguePool",
            f"; {pool.frame_count} frames x 32 bytes ({report['pool_ram_bytes']} B)",
        ]
    )
    for i in range(0, len(pool_blob), 32):
        lines.append(f"; frame {i // 32}")
        lines.extend(byte_lines(pool_blob[i : i + 32]))
    lines.append("")

    CATALOGUE_ASM.write_text("\n".join(lines), encoding="utf-8")
