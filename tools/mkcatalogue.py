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
from mkroom import (  # noqa: E402
    GUARDIAN_HORIZONTAL,
    HUD_TITLE_COLS,
    MAX_GUARDIANS,
    build_tile_colors,
    deinterleave_guardian_sprites,
    parse_room,
)

ROOT = Path(__file__).resolve().parent.parent

CATALOGUE_MAGIC = 0x43575354  # "TSWC" little-endian on wire
CATALOGUE_VERSION = 6

# Set table entry: u16 start_frame, u8 frame_count, u8 flags (4 B each)
SET_ENTRY_BYTES = 4

# Catalogue guardian: motion + color + axis + set_idx (no frame/fmin/fctl — in set table)
GUARDIAN_CATALOG_BYTES = 8

SET_FLAG_H_BIDIR = 0x01

# Target RAM bases (documented in catalogue.map; loaded in Phase 3)
RAM_POOL = 0x2000
RAM_PALETTES = 0x5080

HEADER_SIZE = 64
ROOM_INDEX_ENTRY = 4  # u16 offset + u16 length

FLAG_PICKUP = 0x01
FLAG_RAMP = 0x02
FLAG_CONVEYOR = 0x04
FLAG_ROPE = 0x08
FLAG_ARROW = 0x10
FLAG_BELT_NEG = 0x20

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
    """Unique guardian frame sets; set flags hold bidir / wrap metadata for load."""

    _flat: list[bytes] = field(default_factory=list)
    _set_key: dict[tuple[bytes, int], int] = field(default_factory=dict)
    sets: list[tuple[int, int, int]] = field(default_factory=list)  # start, count, flags

    def add_set(self, frames: list[bytes], flags: int) -> int:
        if not frames:
            return 0
        for fr in frames:
            if len(fr) != 32:
                raise ValueError(f"guardian frame must be 32 bytes, got {len(fr)}")

        key = (b"".join(frames), flags & 0xFF)
        if key in self._set_key:
            return self._set_key[key]

        start = len(self._flat)
        self._flat.extend(frames)
        idx = len(self.sets)
        self.sets.append((start, len(frames), flags & 0xFF))
        self._set_key[key] = idx
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
        for start, count, flags in self.sets:
            if count > 255:
                raise ValueError(f"set frame_count out of u8 range: {count}")
            out.extend(struct.pack("<HBB", start, count & 0xFF, flags & 0xFF))
        return bytes(out)


def gameplay_room_paths(rooms_dir: Path) -> list[Path]:
    paths = sorted(rooms_dir.glob("room*.txt"))
    return [p for p in paths if p.name != "room62.txt"]


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


def expand_guardian_frames(
    g: dict,
    sprites: bytes,
    entity_blocks: list[EntityBlock],
    source: str,
) -> tuple[list[bytes], int]:
    """Return expanded frame list and set flags (SET_FLAG_H_BIDIR etc.)."""
    fmin, fmax = g["fmin"], g["fmax"]
    axis = g["axis"]

    if axis == GUARDIAN_HORIZONTAL:
        if horizontal_bidir_capable(g, sprites, entity_blocks, source):
            return horizontal_bidir_eight(g, sprites, entity_blocks), SET_FLAG_H_BIDIR
        frames = slice_frames(sprites, fmin, fmax)
        return frames, 0

    # Vertical — expand partial disk references to full contiguous parent set.
    n = fmax - fmin + 1
    block = entity_for_frame(entity_blocks, fmin)

    if fmin >= 8 or (block and block.block_fmin >= 8):
        ent_frames = fetch_entity_frames(block) if block else []
        if ent_frames:
            return ent_frames, 0
        one = slice_frames(sprites, fmin, fmin)
        if one:
            return one * 4, 0

    if fmin <= 3 or (n == 1 and fmin in (0, 1, 2, 3)) or (n == 2 and fmin in (0, 2)):
        return slice_frames(sprites, 0, 3), 0

    if fmin >= 4 or (n == 2 and fmin == 4):
        raw = slice_frames(sprites, 4, 7)
        if len(raw) < 4 and block:
            ent_frames = fetch_entity_frames(block)
            if len(ent_frames) >= 4:
                raw = ent_frames[:4]
        return raw, 0

    return slice_frames(sprites, fmin, fmax), 0


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


def pack_guardians(
    room: dict, pool: GuardianPool, source: str
) -> tuple[bytes, list[str]]:
    guardians = room["guardians"]
    if len(guardians) > MAX_GUARDIANS:
        raise ValueError(f"room {room['id']}: too many guardians ({len(guardians)})")
    sprites = deinterleave_guardian_sprites(room.get("guardiansprites") or b"\x00" * 288)
    entity_blocks = parse_entity_blocks(source)

    out = bytearray([len(guardians) & 0xFF])
    for g in guardians:
        frames, set_flags = expand_guardian_frames(g, sprites, entity_blocks, source)
        set_idx = pool.add_set(frames, set_flags)
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
    """Null-terminated HUD title (max 18 chars, same as stamp_hud_title)."""
    text = room["title"].encode("ascii", errors="replace")[:HUD_TITLE_COLS]
    return text + b"\x00"


def pack_room_udg(room: dict) -> bytes:
    mask = 0
    chunks: list[bytes] = []
    for i in range(6):
        if any(room["tileudg"][i]):
            mask |= 1 << i
            chunks.append(bytes(room["tileudg"][i][:8]))
    if room.get("itemudg_defined") or any(room["tileudg"][6]):
        mask |= 1 << 6
        chunks.append(bytes(room["tileudg"][6][:8]))
    return bytes([mask & 0xFF]) + b"".join(chunks)


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


def pack_pickup(pickup: tuple[int, int]) -> bytes:
    col, row = pickup
    return bytes([col & 0xFF, row & 0xFF])


@dataclass
class RoomBuild:
    rid: int
    title: str
    record: bytes
    stats: dict


def build_room_record(
    room: dict,
    *,
    source: str,
    palette_idx: int,
    pool: GuardianPool,
    pickup: tuple[int, int] | None,
    ramp,
    conv,
) -> RoomBuild:
    flags = 0
    if pickup:
        flags |= FLAG_PICKUP
    if ramp:
        flags |= FLAG_RAMP
    if conv:
        flags |= FLAG_CONVEYOR
    if room.get("rope"):
        flags |= FLAG_ROPE
    if room.get("arrow"):
        flags |= FLAG_ARROW
    if room.get("belt", 0) < 0:
        flags |= FLAG_BELT_NEG

    meta = pack_meta8(room, flags=flags)
    title = pack_room_title(room)

    grid = tile_grid(room["tilemap"])
    base, _, _, _ = strip_overlays(grid)
    rle = bytes(rle_pack(base, "row"))

    parts = [meta, bytes([palette_idx & 0xFF]), title, rle]
    if pickup:
        parts.append(pack_pickup(pickup))
    if ramp:
        parts.append(pack_ramp3(ramp))
    if conv:
        parts.append(pack_conveyor3(conv, room.get("belt", 0)))
    parts.append(pack_room_udg(room))
    if room.get("arrow"):
        parts.append(pack_arrow(room))

    guardians_blob, guardian_warnings = pack_guardians(room, pool, source)
    parts.append(guardians_blob)

    record = b"".join(parts)
    return RoomBuild(
        rid=room["id"],
        title=room["title"],
        record=record,
        stats={
            "meta": len(meta),
            "title": len(title),
            "rle": len(rle),
            "udg": len(pack_room_udg(room)),
            "guardians": len(room["guardians"]),
            "guardian_bytes": len(guardians_blob),
            "guardian_warnings": guardian_warnings,
            "total": len(record),
        },
    )


def dedupe_palettes(rooms: list[dict]) -> tuple[list[bytes], dict[bytes, int]]:
    palettes: list[bytes] = []
    index: dict[bytes, int] = {}
    for room in rooms:
        key = build_tile_colors(room)
        if key not in index:
            index[key] = len(palettes)
            palettes.append(key)
    return palettes, index


def build_catalogue(rooms_dir: Path) -> tuple[bytes, dict]:
    paths = gameplay_room_paths(rooms_dir)
    parsed: list[tuple[dict, str]] = []
    for p in paths:
        source = p.read_text(encoding="utf-8")
        parsed.append((parse_room(source, source=p), source))
    parsed.sort(key=lambda rs: rs[0]["id"])

    palettes, palette_index = dedupe_palettes([r for r, _ in parsed])
    pool = GuardianPool()
    all_warnings: list[str] = []

    room_builds: list[RoomBuild] = []
    for room, source in parsed:
        grid = tile_grid(room["tilemap"])
        base, ramp, conv, pickup = strip_overlays(grid)
        rb = build_room_record(
            room,
            source=source,
            palette_idx=palette_index[build_tile_colors(room)],
            pool=pool,
            pickup=pickup,
            ramp=ramp,
            conv=conv,
        )
        all_warnings.extend(rb.stats.get("guardian_warnings", []))
        room_builds.append(rb)

    palettes_blob = b"".join(palettes)
    sets_blob = pool.sets_blob()
    pool_blob = pool.frames_blob()
    catalogue_ram = (RAM_POOL + pool.pool_ram_bytes + 0xFF) & ~0xFF

    room_records_blob = b"".join(rb.record for rb in room_builds)
    room_index = bytearray()
    offset = 0
    for rb in room_builds:
        room_index.extend(struct.pack("<HH", offset, len(rb.record)))
        offset += len(rb.record)

    header = bytearray(HEADER_SIZE)
    struct.pack_into(
        "<IHH", header, 0, CATALOGUE_MAGIC, CATALOGUE_VERSION, len(room_builds)
    )
    struct.pack_into(
        "<IIII",
        header,
        8,
        catalogue_ram,
        RAM_POOL,
        RAM_PALETTES,
        len(room_records_blob),
    )

    parts: list[bytes] = [bytes(header), bytes(room_index)]
    section_offsets: dict[str, int] = {}

    section_offsets["room_index"] = len(parts[0])
    section_offsets["room_records"] = section_offsets["room_index"] + len(room_index)
    parts.append(room_records_blob)

    section_offsets["palettes"] = sum(len(p) for p in parts)
    parts.append(palettes_blob)

    section_offsets["sets"] = sum(len(p) for p in parts)
    parts.append(sets_blob)

    section_offsets["pool"] = sum(len(p) for p in parts)
    parts.append(pool_blob)

    blob = b"".join(parts)

    struct.pack_into("<I", header, 24, section_offsets["room_records"])
    struct.pack_into("<I", header, 28, section_offsets["palettes"])
    struct.pack_into("<I", header, 32, section_offsets["sets"])
    struct.pack_into("<I", header, 36, section_offsets["pool"])
    struct.pack_into("<I", header, 40, len(blob))
    struct.pack_into("<H", header, 44, len(pool.sets))
    struct.pack_into("<H", header, 46, 0)  # reserved (v5: no flip scratch)

    blob = bytes(header) + blob[HEADER_SIZE:]

    guardian_instances = sum(rb.stats["guardians"] for rb in room_builds)
    guardian_bytes = sum(rb.stats["guardian_bytes"] for rb in room_builds)
    title_bytes = sum(rb.stats["title"] for rb in room_builds)
    report = {
        "rooms": len(room_builds),
        "guardian_instances": guardian_instances,
        "guardian_bytes": guardian_bytes,
        "title_bytes": title_bytes,
        "palettes": len(palettes),
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
        "ram": {
            "catalogue": catalogue_ram,
            "pool": RAM_POOL,
            "palettes": RAM_PALETTES,
        },
    }
    return blob, report


def write_map(path: Path, report: dict) -> None:
    lines = [
        "JSW-Tape catalogue.map",
        f"version {CATALOGUE_VERSION}",
        "",
        "Target RAM bases (Phase 3 loader):",
    ]
    for name, addr in report["ram"].items():
        lines.append(f"  {name:12s} ${addr:04X}")
    lines.append("")
    lines.append("File sections:")
    for name, off in report["section_offsets"].items():
        lines.append(f"  {name:14s} file ${off:04X}")
    lines.append("")
    lines.append(
        f"guardians:  {report['guardian_instances']} instances "
        f"({report['guardian_bytes']} B inline, {GUARDIAN_CATALOG_BYTES} B each)"
    )
    lines.append(
        f"sets:       {report['set_count']} x {SET_ENTRY_BYTES} B "
        f"(u16 start_frame + count + flags)"
    )
    lines.append(
        f"pool:       {report['pool_frames']} flat slots "
        f"({report['pool_unique_frames']} unique 32 B blobs, "
        f"{report['pool_frame_bytes']} B) = {report['pool_ram_bytes']} B RAM"
    )
    lines.append(
        f"titles:     embedded in room records ({report['title_bytes']} B total)"
    )
    lines.append(f"palettes:   {report['palettes']} x 6 B (shared table)")
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
        f"Pool:         {report['pool_frames']} slots ({report['pool_unique_frames']} unique), "
        f"{report['pool_ram_bytes']} B RAM"
    )
    print(f"Palettes:     {report['palettes']} x 6 B")
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


if __name__ == "__main__":
    main()
