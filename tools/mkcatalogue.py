#!/usr/bin/env python3
"""Build JSW-Tape room catalogue.bin from rooms/room*.txt sources."""

from __future__ import annotations

import argparse
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from audit_room_compress import (  # noqa: E402
    pack_conveyor3,
    pack_ramp3,
    rle_pack,
    strip_overlays,
    tile_grid,
)
from catalogue_asm import RoomSection, write_catalogue_asm  # noqa: E402
from udg_pool import audit_unused_udg_definitions  # noqa: E402
from mkroom import (  # noqa: E402
    GUARDIAN_HORIZONTAL,
    HUD_TITLE_COLS,
    MAX_GUARDIANS,
    TILE_HAZARD,
    build_tile_colors,
    deinterleave_guardian_sprites,
    parse_room,
)

ROOT = Path(__file__).resolve().parent.parent
BAKE_CATALOGUE_ROOMS_ASM = ROOT / "bake" / "catalogue_rooms.asm"
BAKE_CATALOGUE_SPRITES_ASM = ROOT / "bake" / "catalogue_sprites.asm"
# Set table entry: u8 start_frame, u8 frame_count (2 B each; pool < 256 frames)
SET_ENTRY_BYTES = 2

# Catalogue guardian: motion + color + axis + set_idx (no frame/fmin/fctl — in set table)
GUARDIAN_CATALOG_BYTES = 8

HEADER_SIZE = 2  # u16 room_count only
ROOM_INDEX_ENTRY = 4  # u16 offset + u16 length
SCREEN_WIDTH = 24
SCREEN_BASE = 0x1000
PICKUP_NONE = 0xFFFF

# meta8 byte 6 — feature flags (optional overlays + UDG chunks)
FLAG_NASTY = 0x01
FLAG_RAMP = 0x02
FLAG_CONVEYOR = 0x04
FLAG_ROPE = 0x08
FLAG_ARROW = 0x10

UDG_FIXED_BYTES = 24  # floor + wall + item (8 B each)


SAW_LINE = re.compile(r"\bsaw\b", re.IGNORECASE)
ENTITY_LINE = re.compile(
    r";\s*entity\s+(\d+):\s*page\s+(\d+)(?:\s+sprite\s+(\d+))?(?:\s+f=([\d\.]+))?",
    re.IGNORECASE,
)

try:
    from jswimport import (  # noqa: E402
        entity_type,
        frame_range,
        is_horizontal,
        load_entities,
        load_guardian_gfx,
        sprite_bytes,
    )

    _ENTITIES_DB = load_entities()
    _GUARDIAN_GFX = load_guardian_gfx()
except Exception:
    _ENTITIES_DB = None
    _GUARDIAN_GFX = None


@dataclass
class EntityBlock:
    ent_id: int
    page: int
    sprite: int
    block_fmin: int
    block_fmax: int


@dataclass
class GuardianPool:
    """Build-time pool: one entry per distinct guardian sprite name."""

    _flat: list[bytes] = field(default_factory=list)
    _by_name: dict[str, int] = field(default_factory=dict)
    sets: list[tuple[int, int, str]] = field(default_factory=list)  # start, count, name

    def set_index(self, name: str) -> int:
        """Return set index for sprite name; append frames on first use."""
        key = name.lower()
        if not key:
            raise ValueError("guardian missing sprite name")
        if key in self._by_name:
            return self._by_name[key]

        frames = sprite_frames(key)
        for fr in frames:
            if len(fr) != 32:
                raise ValueError(f"{key!r}: frame must be 32 bytes, got {len(fr)}")

        start = len(self._flat)
        self._flat.extend(frames)
        idx = len(self.sets)
        self.sets.append((start, len(frames), key))
        self._by_name[key] = idx
        return idx

    @property
    def frame_count(self) -> int:
        return len(self._flat)

    @property
    def unique_frame_count(self) -> int:
        return len({bytes(f) for f in self._flat})

    @property
    def frames_bytes(self) -> int:
        return len(self._flat) * 32

    @property
    def pool_ram_bytes(self) -> int:
        return self.frames_bytes

    def frames_blob(self) -> bytes:
        return b"".join(self._flat)

    def sets_blob(self) -> bytes:
        out = bytearray()
        for start, count, _name in self.sets:
            if start > 255 or count > 255:
                raise ValueError(f"set out of u8 range: start={start} count={count}")
            out.extend([start & 0xFF, count & 0xFF])
        return bytes(out)


def gameplay_room_paths(rooms_dir: Path) -> list[Path]:
    paths = sorted(rooms_dir.glob("room*.txt"))
    return [p for p in paths if p.name not in ("room62.txt", "room47.txt")]


def _entity_block_count(ent_id: int, page: int, sprite: int, fr_hint: str | None) -> int:
    if fr_hint and ".." in fr_hint:
        lo, hi = fr_hint.split("..", 1)
        return int(hi) - int(lo) + 1
    if fr_hint:
        return 1
    if _ENTITIES_DB and ent_id in _ENTITIES_DB:
        ent = _ENTITIES_DB[ent_id]
        if entity_type(ent) in (1, 2):
            fmin, fmax = frame_range(ent)
            count = fmax - fmin + 1
            if is_horizontal(ent) and count == 8:
                return 8
            return count
    return 4


def parse_entity_blocks(source: str) -> list[EntityBlock]:
    """Map room @guardiansprites frame indices to entity ids from file comments."""
    blocks: list[EntityBlock] = []
    base = 0
    for line in source.splitlines():
        m = ENTITY_LINE.match(line.strip())
        if not m:
            continue
        ent_id = int(m.group(1))
        page = int(m.group(2))
        sprite = int(m.group(3) or 0)
        fr_hint = m.group(4)
        count = _entity_block_count(ent_id, page, sprite, fr_hint)
        blocks.append(
            EntityBlock(
                ent_id=ent_id,
                page=page,
                sprite=sprite,
                block_fmin=base,
                block_fmax=base + count - 1,
            )
        )
        base += count
    return blocks


def entity_for_frame(blocks: list[EntityBlock], frame: int) -> EntityBlock | None:
    for block in blocks:
        if block.block_fmin <= frame <= block.block_fmax:
            return block
    return None


def fetch_entity_gfx_frames(
    block: EntityBlock, gfx_fmin: int, gfx_count: int
) -> list[bytes]:
    """Load gfx frames from Spectrum guardian gfx at page/sprite."""
    if not _ENTITIES_DB or not _GUARDIAN_GFX:
        return []
    ent = _ENTITIES_DB.get(block.ent_id)
    if not ent or entity_type(ent) not in (1, 2):
        return []
    data = sprite_bytes(_GUARDIAN_GFX, block.page, block.sprite, gfx_fmin, gfx_count)
    return [
        data[i : i + 32]
        for i in range(0, len(data), 32)
        if len(data[i : i + 32]) == 32
    ]


def fetch_entity_frames(block: EntityBlock) -> list[bytes]:
    """Load parent sprite run from gfx (h8 horizontal: left 4 only)."""
    if not _ENTITIES_DB or not _GUARDIAN_GFX:
        return []
    ent = _ENTITIES_DB.get(block.ent_id)
    if not ent or entity_type(ent) not in (1, 2):
        return []
    fmin, fmax = frame_range(ent)
    count = fmax - fmin + 1
    if is_horizontal(ent) and count == 8:
        count = 4
        fmin = 0
    return fetch_entity_gfx_frames(block, fmin, count)


def _frame_used(sprites: bytes, index: int) -> bool:
    off = index * 32
    if off + 32 > len(sprites):
        return False
    return any(sprites[off : off + 32])


def _entity_horizontal_eight(ent_id: int) -> bool:
    if not _ENTITIES_DB or ent_id not in _ENTITIES_DB:
        return False
    ent = _ENTITIES_DB[ent_id]
    if not is_horizontal(ent):
        return False
    fmin, fmax = frame_range(ent)
    return fmax - fmin + 1 >= 8


def horizontal_bidir_capable(
    g: dict,
    sprites: bytes,
    entity_blocks: list[EntityBlock],
    source: str,
) -> bool:
    """True when this horizontal guardian uses an 8-frame bidir set in the pool."""
    if g["axis"] != GUARDIAN_HORIZONTAL:
        return False
    if g["fctl"] == 1:
        return True

    fmin, fmax = g["fmin"], g["fmax"]
    n = fmax - fmin + 1

    # Split saw sprites (facing left 0..3 / right 4..7) in a saw room.
    if SAW_LINE.search(source) and n == 4:
        return True

    block = entity_for_frame(entity_blocks, fmin)
    if block and _entity_horizontal_eight(block.ent_id):
        return True

    if block:
        span = block.block_fmax - block.block_fmin + 1
        if span >= 8:
            return True
        if fmin >= 4 and block.block_fmin <= 3:
            return True
        if _frame_used(sprites, 4) and _frame_used(sprites, 7):
            return True

    return False


def horizontal_left_four(
    g: dict,
    sprites: bytes,
    entity_blocks: list[EntityBlock],
) -> list[bytes]:
    block = entity_for_frame(entity_blocks, g["fmin"])
    if block:
        left = block.block_fmin
        frames = slice_frames(sprites, left, left + 3)
        if len(frames) == 4:
            return frames
        ent_frames = fetch_entity_frames(block)
        if len(ent_frames) >= 4:
            return ent_frames[:4]
    return slice_frames(sprites, 0, 3)


def horizontal_right_four(
    g: dict,
    sprites: bytes,
    entity_blocks: list[EntityBlock],
) -> list[bytes]:
    block = entity_for_frame(entity_blocks, g["fmin"])

    if _frame_used(sprites, 4) and _frame_used(sprites, 7):
        right = slice_frames(sprites, 4, 7)
        if len(right) == 4:
            return right

    if block:
        span = block.block_fmax - block.block_fmin + 1
        if span >= 8:
            right = slice_frames(sprites, block.block_fmin + 4, block.block_fmin + 7)
            if len(right) == 4:
                return right
        ent_right = fetch_entity_gfx_frames(block, 4, 4)
        if len(ent_right) == 4:
            return ent_right

    raise ValueError(
        f"bidir horizontal guardian missing right frames 4..7 "
        f"(room frame ref fmin={g['fmin']})"
    )


def horizontal_bidir_eight(
    g: dict,
    sprites: bytes,
    entity_blocks: list[EntityBlock],
) -> list[bytes]:
    if g["fctl"] == 1:
        full = slice_frames(sprites, g["fmin"], g["fmax"])
        if len(full) == 8:
            return full

    left = horizontal_left_four(g, sprites, entity_blocks)
    if len(left) != 4:
        raise ValueError(f"bidir horizontal guardian needs 4 left frames, got {len(left)}")
    right = horizontal_right_four(g, sprites, entity_blocks)
    return left + right


def slice_frames(sprites: bytes, fmin: int, fmax: int) -> list[bytes]:
    out: list[bytes] = []
    for i in range(fmin, fmax + 1):
        off = i * 32
        if off + 32 > len(sprites):
            break
        out.append(sprites[off : off + 32])
    return out


ROOT = Path(__file__).resolve().parent.parent
SPRITE_SOURCE_ASM = ROOT / "bake" / "sprite_source.asm"

_sprite_lib_cache: dict[str, list[bytes]] | None = None


def load_sprite_lib() -> dict[str, list[bytes]]:
    global _sprite_lib_cache
    if _sprite_lib_cache is not None:
        return _sprite_lib_cache
    from guardian_sprite_types import parse_spriteframes_asm  # noqa: WPS433

    raw = parse_spriteframes_asm(SPRITE_SOURCE_ASM)
    if not raw:
        raise FileNotFoundError(f"missing or empty {SPRITE_SOURCE_ASM}")
    _sprite_lib_cache = dict(raw)
    return _sprite_lib_cache


def sprite_frames(name: str) -> list[bytes]:
    """Frames for a sprite name from bake/sprite_source.asm."""
    key = name.lower()
    if not key:
        raise ValueError("guardian sprite name required")
    lib = load_sprite_lib()
    if key not in lib:
        raise KeyError(
            f"unknown guardian sprite {key!r} (not in {SPRITE_SOURCE_ASM.name})"
        )
    return lib[key]


def expand_guardian_frames(g: dict) -> list[bytes]:
    """Return frame list for a parsed guardian dict."""
    name = (g.get("sprite") or "").lower()
    if not name:
        raise ValueError(f"guardian missing sprite name: {g.get('line', g)!r}")
    return sprite_frames(name)


def pack_guardian_catalog(g: dict, set_idx: int) -> bytes:
    """8 B motion + set_idx (runtime 10 B AoS filled at room load from set table)."""
    return bytes(
        [
            g["x"] & 0xFF,
            g["y"] & 0xFF,
            g["min"] & 0xFF,
            g["max"] & 0xFF,
            g["vel"] & 0xFF,
            g["color"] & 0xFF,
            g["axis"] & 0xFF,
            set_idx & 0xFF,
        ]
    )


def pack_guardians(room: dict, pool: GuardianPool) -> tuple[bytes, list[str]]:
    guardians = room["guardians"]
    if len(guardians) > MAX_GUARDIANS:
        raise ValueError(f"room {room['id']}: too many guardians ({len(guardians)})")

    out = bytearray([len(guardians) & 0xFF])
    for g in guardians:
        name = (g.get("sprite") or "").lower()
        set_idx = pool.set_index(name)
        out.extend(pack_guardian_catalog(g, set_idx))

    return bytes(out), []


def pack_meta8(room: dict, *, flags: int) -> bytes:
    """8 B fixed meta; byte 7 = VIC border/background nybbles (same as disk meta byte 1)."""
    meta = bytearray(8)
    meta[0:4] = bytes(room["conn"][:4])
    meta[4] = room["spawn"][0] & 0xFF
    meta[5] = room["spawn"][1] & 0xFF
    meta[6] = flags & 0xFF
    meta[7] = ((room["background"] & 0x0F) << 4) | 8 | (room["border"] & 0x0F)
    return bytes(meta)


def pack_room_title(room: dict) -> bytes:
    """Null-terminated HUD title as 1-based proportional-font glyph bytes."""
    from font_glyph import pack_title_glyphs

    text = room["title"].encode("ascii", errors="replace").decode("ascii")[:HUD_TITLE_COLS]
    return pack_title_glyphs(text)


def room_record_flags(room: dict) -> int:
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


def pack_room_udg(room: dict, flags: int) -> bytes:
    """floor + wall + item always; nasty/ramp/belt UDG when flag set."""
    chunks = [
        bytes(room["tileudg"][1][:8]),
        bytes(room["tileudg"][2][:8]),
        bytes(room["tileudg"][6][:8]),
    ]
    if flags & FLAG_NASTY:
        chunks.append(bytes(room["tileudg"][3][:8]))
    if flags & FLAG_RAMP:
        chunks.append(bytes(room["tileudg"][4][:8]))
    if flags & FLAG_CONVEYOR:
        chunks.append(bytes(room["tileudg"][5][:8]))
    return b"".join(chunks)


def udg_blob_size(flags: int) -> int:
    size = UDG_FIXED_BYTES
    if flags & FLAG_NASTY:
        size += 8
    if flags & FLAG_RAMP:
        size += 8
    if flags & FLAG_CONVEYOR:
        size += 8
    return size


def pack_arrow(room: dict) -> bytes:
    a = room["arrow"]
    return bytes(
        [
            a["y"] & 0xFF,
            a["x"] & 0xFF,
            (a["v"] + 2) & 0x03,  # map -1/1 → 1/2
            a["sound"] & 0xFF,
            0,
        ]
    )


def pack_pickup_bytes(pickup: tuple[int, int] | None) -> bytes:
    if pickup:
        col, row = pickup
        offset = row * SCREEN_WIDTH + col
        addr = SCREEN_BASE + offset
        return struct.pack("<H", addr)
    return struct.pack("<H", PICKUP_NONE)


@dataclass
class RoomBuild:
    rid: int
    title: str
    record: bytes
    stats: dict
    flags: int = 0
    sections: list[RoomSection] = field(default_factory=list)


def build_room_record(
    room: dict,
    *,
    source: str,
    pool: GuardianPool,
    pickup: tuple[int, int] | None,
    ramp,
    conv,
) -> RoomBuild:
    grid = tile_grid(room["tilemap"])
    base, ramp, conv, pickup = strip_overlays(grid)

    flags = 0
    if TILE_HAZARD in base:
        flags |= FLAG_NASTY
    if ramp:
        flags |= FLAG_RAMP
    if conv:
        flags |= FLAG_CONVEYOR
    if room.get("rope"):
        flags |= FLAG_ROPE
    if room.get("arrow"):
        flags |= FLAG_ARROW

    meta = pack_meta8(room, flags=flags)
    title = pack_room_title(room)
    tile_colors = build_tile_colors(room)

    base_rle, _, _, _ = strip_overlays(grid)
    rle = bytes(rle_pack(base_rle, "row"))

    udg_blob = pack_room_udg(room, flags)
    guardians_blob, guardian_warnings = pack_guardians(room, pool)
    pickup_bytes = pack_pickup_bytes(pickup)

    parts = [title, meta, tile_colors, udg_blob, rle, pickup_bytes]
    sections: list[RoomSection] = [
        RoomSection("title", "", title),
        RoomSection("meta8", "", meta),
        RoomSection("tile_colors", "", tile_colors),
        RoomSection("tile_udg", "", udg_blob, extra={"flags": flags}),
        RoomSection("rle_tilemap", "", rle),
        RoomSection(
            "pickup",
            "",
            pickup_bytes,
            extra={"pickup": pickup},
        ),
    ]
    if ramp:
        parts.append(pack_ramp3(ramp))
        sections.append(
            RoomSection(
                "ramp",
                f"x={ramp['x']} y={ramp['y']} len={ramp['length']} dir={ramp['direction']}",
                pack_ramp3(ramp),
            )
        )
    if conv:
        parts.append(pack_conveyor3(conv, room.get("belt", 0)))
        sections.append(
            RoomSection(
                "conveyor",
                f"x={conv['x']} y={conv['y']} len={conv['length']} belt={room.get('belt', 0)}",
                pack_conveyor3(conv, room.get("belt", 0)),
            )
        )
    if room.get("arrow"):
        parts.append(pack_arrow(room))
        a = room["arrow"]
        sections.append(
            RoomSection(
                "arrow",
                f"x={a['x']} y={a['y']} v={a['v']} sound={a['sound']}",
                pack_arrow(room),
            )
        )
    parts.append(guardians_blob)
    sections.append(
        RoomSection(
            "guardians",
            "",
            guardians_blob,
            extra={"guardians": room["guardians"]},
        )
    )

    record = b"".join(parts)
    return RoomBuild(
        rid=room["id"],
        title=room["title"],
        record=record,
        flags=flags,
        sections=sections,
        stats={
            "meta": len(meta),
            "title": len(title),
            "rle": len(rle),
            "udg": len(udg_blob),
            "guardians": len(room["guardians"]),
            "guardian_bytes": len(guardians_blob),
            "guardian_warnings": guardian_warnings,
            "total": len(record),
        },
    )


def flags_desc(flags: int) -> str:
    bits = (
        (FLAG_NASTY, "nasty"),
        (FLAG_RAMP, "ramp"),
        (FLAG_CONVEYOR, "conveyor"),
        (FLAG_ROPE, "rope"),
        (FLAG_ARROW, "arrow"),
    )
    names = [name for bit, name in bits if flags & bit]
    return "|".join(names) if names else "none"


def build_catalogue(rooms_dir: Path) -> tuple[bytes, dict]:
    paths = gameplay_room_paths(rooms_dir)
    parsed: list[tuple[dict, str]] = []
    for p in paths:
        source = p.read_text(encoding="utf-8")
        parsed.append((parse_room(source, source=p), source))
    parsed.sort(key=lambda rs: rs[0]["id"])

    rooms = [room for room, _source in parsed]

    pool = GuardianPool()
    all_warnings: list[str] = list(audit_unused_udg_definitions(rooms))

    room_builds: list[RoomBuild] = []
    for room, source in parsed:
        grid = tile_grid(room["tilemap"])
        base, ramp, conv, pickup = strip_overlays(grid)
        rb = build_room_record(
            room,
            source=source,
            pool=pool,
            pickup=pickup,
            ramp=ramp,
            conv=conv,
        )
        all_warnings.extend(rb.stats.get("guardian_warnings", []))
        room_builds.append(rb)

    player_sprite_set_idx = pool.set_index("willy")

    sets_blob = pool.sets_blob()
    pool_blob = pool.frames_blob()
    room_records_blob = b"".join(rb.record for rb in room_builds)
    room_index = bytearray()
    offset = 0
    for rb in room_builds:
        room_index.extend(struct.pack("<HH", offset, len(rb.record)))
        offset += len(rb.record)

    header = struct.pack("<H", len(room_builds))

    parts: list[bytes] = [header, bytes(room_index)]
    section_offsets: dict[str, int] = {}

    section_offsets["room_index"] = len(parts[0])
    section_offsets["room_records"] = section_offsets["room_index"] + len(room_index)
    parts.append(room_records_blob)

    section_offsets["sets"] = sum(len(p) for p in parts)
    parts.append(sets_blob)

    section_offsets["pool"] = sum(len(p) for p in parts)
    parts.append(pool_blob)

    blob = b"".join(parts)

    write_catalogue_asm(
        room_builds=room_builds,
        pool=pool,
        report={
            "rooms": len(room_builds),
            "set_count": len(pool.sets),
            "pool_frames": pool.frame_count,
            "pool_ram_bytes": pool.pool_ram_bytes,
            "player_sprite_set_idx": player_sprite_set_idx,
        },
    )

    guardian_instances = sum(rb.stats["guardians"] for rb in room_builds)
    guardian_bytes = sum(rb.stats["guardian_bytes"] for rb in room_builds)
    title_bytes = sum(rb.stats["title"] for rb in room_builds)
    report = {
        "rooms": len(room_builds),
        "guardian_instances": guardian_instances,
        "guardian_bytes": guardian_bytes,
        "title_bytes": title_bytes,
        "pool_frames": pool.frame_count,
        "pool_unique_frames": pool.unique_frame_count,
        "pool_frame_bytes": pool.frames_bytes,
        "pool_ram_bytes": pool.pool_ram_bytes,
        "set_count": len(pool.sets),
        "set_bytes": len(sets_blob),
        "room_records_bytes": len(room_records_blob),
        "total_bytes": len(blob),
        "room_builds": room_builds,
        "section_offsets": section_offsets,
        "warnings": all_warnings,
    }
    return blob, report


def write_map(path: Path, report: dict) -> None:
    lines = [
        "JSW-Tape catalogue.map",
        f"rooms {report['rooms']}",
        "",
        "Embedded in PRG (read in place): sprite_set_metadata, sprite_frames",
        "",
        "File sections:",
    ]
    for name, off in report["section_offsets"].items():
        lines.append(f"  {name:14s} file ${off:04X}")
    lines.append("")
    lines.append(
        f"guardians:  {report['guardian_instances']} instances "
        f"({report['guardian_bytes']} B inline, {GUARDIAN_CATALOG_BYTES} B each)"
    )
    lines.append(
        f"sets:       {report['set_count']} x {SET_ENTRY_BYTES} B "
        f"(start_frame + frame_count)"
    )
    lines.append(
        f"pool:       {report['pool_frames']} frames "
        f"({report['set_count']} sprite names, "
        f"{report['pool_frame_bytes']} B) = {report['pool_ram_bytes']} B RAM"
    )
    lines.append(
        f"titles:     embedded in room records ({report['title_bytes']} B total)"
    )
    lines.append("tile colors: 6 B per room record (types 0-5)")
    lines.append("")
    if report.get("warnings"):
        lines.append("Warnings:")
        for w in report["warnings"]:
            lines.append(f"  *** {w}")
        lines.append("")
    lines.append("Per-room records:")
    lines.append(f"{'id':>3}  {'total':>5}  {'rle':>4}  {'g':>2}  title")
    for rb in report["room_builds"]:
        lines.append(
            f"{rb.rid:3d}  {rb.stats['total']:5d}  {rb.stats['rle']:4d}  "
            f"{rb.stats['guardians']:2d}  {rb.title[:40]}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_report(report: dict) -> None:
    sizes = [rb.stats["total"] for rb in report["room_builds"]]
    print("=== mkcatalogue.py ===")
    print(f"Rooms:        {report['rooms']}")
    print(f"Room records: {report['room_records_bytes']} B ({report['room_records_bytes']/1024:.1f} KB)")
    print(f"Titles:       embedded ({report['title_bytes']} B in records)")
    print(f"Guardians:    {report['guardian_instances']} x {GUARDIAN_CATALOG_BYTES} B inline")
    print(f"Sets:         {report['set_count']} descriptors ({report['set_bytes']} B)")
    print(
        f"Pool:         {report['pool_frames']} frames ({report['set_count']} sprite names), "
        f"{report['pool_ram_bytes']} B RAM"
    )
    print("Tile colors:  6 B inline per room record")
    print(f"Total file:   {report['total_bytes']} B ({report['total_bytes']/1024:.1f} KB)")
    print(
        f"Per-room:     min={min(sizes)} avg={sum(sizes)/len(sizes):.1f} "
        f"max={max(sizes)} total={sum(sizes)}"
    )
    if report.get("warnings"):
        print("")
        print("Warnings:")
        for w in report["warnings"]:
            print(f"  *** {w}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build JSW-Tape catalogue.bin")
    ap.add_argument("--rooms", type=Path, default=ROOT / "rooms")
    ap.add_argument("--out", type=Path, default=ROOT / "catalogue.bin")
    ap.add_argument("--map", type=Path, default=ROOT / "catalogue.map")
    args = ap.parse_args()

    blob, report = build_catalogue(args.rooms)
    args.out.write_bytes(blob)
    write_map(args.map, report)
    print_report(report)
    print(f"Wrote {args.out} and {args.map}")
    print(
        f"Wrote {BAKE_CATALOGUE_ROOMS_ASM.name}, "
        f"{BAKE_CATALOGUE_SPRITES_ASM.name}, and bake/rooms/*.asm"
    )


if __name__ == "__main__":
    main()
