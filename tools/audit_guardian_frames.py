#!/usr/bin/env python3
"""Audit unique guardian animation frames in the Spectrum JSW disassembly."""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jswimport import (  # noqa: E402
    entity_type,
    frame_range,
    guardian_sprite_key,
    is_horizontal,
    load_entities,
    load_guardian_gfx,
    load_room_blob,
    parse_room_block,
    sprite_bytes,
)


def flip_h_frame(frame: bytes) -> bytes:
    """Horizontal mirror of 16x16 two-column sprite (16+16 column-major)."""

    def rev_bits(b: int) -> int:
        r = 0
        for i in range(8):
            if b & (1 << i):
                r |= 1 << (7 - i)
        return r

    left, right = frame[:16], frame[16:]
    left_r = bytes(rev_bits(b) for b in reversed(left))
    right_r = bytes(rev_bits(b) for b in reversed(right))
    return right_r + left_r


def extract_frames(gfx: bytes, key: tuple[int, int, int, int]) -> list[bytes]:
    page, sprite, fmin, count = key
    data = sprite_bytes(gfx, page, sprite, fmin, count)
    return [data[i : i + 32] for i in range(0, len(data), 32) if len(data[i : i + 32]) == 32]


def effective_frames(ent: bytes, key: tuple[int, int, int, int], gfx: bytes) -> tuple[list[bytes], str]:
    frames = extract_frames(gfx, key)
    count = key[3]
    if is_horizontal(ent) and count == 8:
        return frames[:4], "h8"
    if is_horizontal(ent):
        return frames, f"h{count}"
    return frames, f"v{count}"


def collect_keys(entities_db: dict[int, bytes]) -> dict[tuple, list[tuple]]:
    keys_used: dict[tuple, list[tuple]] = {}
    for rid in range(61):
        room = parse_room_block(load_room_blob(rid))
        for ent_id, spec in room["entities"]:
            if ent_id == 0:
                continue
            ent = entities_db.get(ent_id)
            if not ent or entity_type(ent) not in (1, 2):
                continue
            key = guardian_sprite_key(ent, spec)
            keys_used.setdefault(key, []).append((rid, ent_id, spec, ent))
    return keys_used


def main() -> None:
    entities_db = load_entities()
    gfx = load_guardian_gfx()
    keys_used = collect_keys(entities_db)

    total_raw = 0
    total_effective = 0
    by_type: dict[str, dict] = defaultdict(lambda: {"keys": 0, "frames": 0, "rooms": set()})
    unique_bytes: set[bytes] = set()
    unique_with_flip: set[bytes] = set()
    per_key: list[dict] = []

    for key, uses in sorted(keys_used.items()):
        rid, ent_id, spec, ent = uses[0]
        raw_frames = extract_frames(gfx, key)
        eff_frames, kind = effective_frames(ent, key, gfx)
        total_raw += len(raw_frames)
        total_effective += len(eff_frames)
        axis = "H" if is_horizontal(ent) else "V"
        by_type[kind]["keys"] += 1
        by_type[kind]["frames"] += len(eff_frames)
        for u in uses:
            by_type[kind]["rooms"].add(u[0])
        for fr in eff_frames:
            unique_bytes.add(fr)
            unique_with_flip.add(fr)
            unique_with_flip.add(flip_h_frame(fr))
        fmin, fmax = frame_range(ent)
        per_key.append(
            {
                "key": key,
                "ent_id": ent_id,
                "axis": axis,
                "kind": kind,
                "raw": len(raw_frames),
                "eff": len(eff_frames),
                "fmin": fmin,
                "fmax": fmax,
                "page": key[0],
                "sprite": key[1],
                "rooms": sorted({u[0] for u in uses}),
                "use_count": len(uses),
            }
        )

    max_room = 0
    max_room_id = -1
    for rid in range(61):
        room = parse_room_block(load_room_blob(rid))
        seen: set[tuple] = set()
        n = 0
        for ent_id, spec in room["entities"]:
            if ent_id == 0:
                continue
            ent = entities_db.get(ent_id)
            if not ent or entity_type(ent) not in (1, 2):
                continue
            key = guardian_sprite_key(ent, spec)
            if key in seen:
                continue
            seen.add(key)
            eff_frames, _ = effective_frames(ent, key, gfx)
            n += len(eff_frames)
        if n > max_room:
            max_room = n
            max_room_id = rid

    print("=== JSW Spectrum guardian animation frame audit ===")
    print(f"Guardian gfx blob: {len(gfx)} bytes (${43776:05X}..${49151:05X})")
    print(f"Unique sprite sets used in rooms: {len(keys_used)}")
    print()
    print("By animation type (h8 counted as 4 unique frames):")
    for kind in sorted(by_type):
        v = by_type[kind]
        print(
            f"  {kind:4s}: {v['keys']:2d} sprite sets, "
            f"{v['frames']:3d} effective frames, {len(v['rooms']):2d} rooms"
        )
    print()
    print(f"Total raw frames if stored verbatim:     {total_raw:3d}  ({total_raw * 32:5d} B)")
    print(f"Total effective frames (h8 -> 4):        {total_effective:3d}  ({total_effective * 32:5d} B)")
    print(f"Globally unique 32-byte frame blobs:     {len(unique_bytes):3d}  ({len(unique_bytes) * 32:5d} B)")
    print(
        f"Unique incl. horizontal flip variants:   {len(unique_with_flip):3d}  "
        f"({len(unique_with_flip) * 32:5d} B)"
    )
    print()
    print(f"Max frames needed in one room: {max_room} (room {max_room_id}, {max_room * 32} B)")
    print()
    print("Sprite sets (entity id, type, page/sprite, frames, rooms):")
    for row in sorted(per_key, key=lambda r: (r["kind"], r["ent_id"])):
        rooms = ",".join(f"{r:02d}" for r in row["rooms"][:8])
        if len(row["rooms"]) > 8:
            rooms += f",+{len(row['rooms']) - 8}"
        print(
            f"  ent {row['ent_id']:3d} {row['axis']} {row['kind']:3s} "
            f"page={row['page']:3d} spr={row['sprite']} "
            f"raw={row['raw']} eff={row['eff']} "
            f"rooms=[{rooms}]"
        )


if __name__ == "__main__":
    main()
