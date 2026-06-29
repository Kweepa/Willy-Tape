#!/usr/bin/env python3
"""Audit bidir horizontal guardian classification and pool dedup."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jswimport import entity_type, frame_range, is_horizontal, load_entities  # noqa: E402
from mkcatalogue import (  # noqa: E402
    SAW_LINE,
    GuardianPool,
    _entity_horizontal_eight,
    _frame_used,
    entity_for_frame,
    expand_guardian_frames,
    gameplay_room_paths,
    horizontal_bidir_capable,
    parse_entity_blocks,
)
from mkroom import deinterleave_guardian_sprites, parse_room  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ents = load_entities()


def ent_label(eid: int | None) -> str:
    if eid is None:
        return "no-entity"
    e = ents.get(eid)
    if not e:
        return f"ent{eid}?"
    kind = "H" if is_horizontal(e) else "V"
    fmin, fmax = frame_range(e)
    return f"ent{eid} {kind}{fmax - fmin + 1}"


def bidir_reason(g: dict, sprites: bytes, blocks, source: str) -> str:
    if g["fctl"] == 1:
        return "fctl=1"
    n = g["fmax"] - g["fmin"] + 1
    if SAW_LINE.search(source) and n == 4:
        return "saw-room h4"
    block = entity_for_frame(blocks, g["fmin"])
    if block and _entity_horizontal_eight(block.ent_id):
        return "entity-h8"
    if block:
        span = block.block_fmax - block.block_fmin + 1
        if span >= 8:
            return "block-span>=8"
        if g["fmin"] >= 4 and block.block_fmin <= 3:
            return "fmin>=4 in block"
    if _frame_used(sprites, 4) and _frame_used(sprites, 7):
        return "sprites-4-and-7-used"
    return "?"


def main() -> None:
    pool = GuardianPool()
    set_info: dict[int, dict] = {}
    instances: list[dict] = []

    for p in gameplay_room_paths(ROOT / "rooms"):
        source = p.read_text(encoding="utf-8")
        room = parse_room(source, source=p)
        sprites = deinterleave_guardian_sprites(room.get("guardiansprites") or b"\x00" * 288)
        blocks = parse_entity_blocks(source)
        for g in room["guardians"]:
            if g["axis"] != 0:
                continue
            if not horizontal_bidir_capable(g, sprites, blocks, source):
                continue
            frames, flags = expand_guardian_frames(g, sprites, blocks, source)
            sid = pool.add_set(frames, flags)
            block = entity_for_frame(blocks, g["fmin"])
            reason = bidir_reason(g, sprites, blocks, source)
            rec = {
                "room": room["id"],
                "title": room["title"],
                "ent": ent_label(block.ent_id if block else None),
                "eid": block.ent_id if block else None,
                "page": block.page if block else None,
                "sprite": block.sprite if block else None,
                "fmin": g["fmin"],
                "fmax": g["fmax"],
                "set_idx": sid,
                "reason": reason,
                "gfx_key": (block.page, block.sprite) if block else None,
            }
            instances.append(rec)
            if sid not in set_info:
                set_info[sid] = {**rec, "frame_bytes": len(frames) * 32}

    print(f"Bidir instances: {len(instances)}")
    print(f"Bidir pool sets:  {len(set_info)}")
    print(f"Pool total frames: {pool.frame_count} ({pool.frames_bytes} B)")
    print()
    print("Sets (first room reference):")
    for sid in sorted(set_info):
        s = set_info[sid]
        print(
            f"  {sid:2d}  {s['ent']:18s}  p{s['page']} s{s['sprite']}  "
            f"room {s['room']:2d} {s['title'][:24]:24s}  [{s['reason']}]"
        )

    print()
    print("By gfx (page, sprite) — should collapse to ~5 types:")
    by_gfx: dict[tuple, list] = {}
    for s in set_info.values():
        key = s["gfx_key"]
        by_gfx.setdefault(key, []).append(s)
    for key in sorted(by_gfx, key=lambda k: (k is None, k or (0, 0))):
        group = by_gfx[key]
        set_ids = sorted({g["set_idx"] for g in group})
        print(f"  gfx {key}: {len(group)} sets {set_ids} — {group[0]['ent']} e.g. room {group[0]['room']}")

    print()
    print("Reason counts:")
    from collections import Counter

    print(Counter(i["reason"] for i in instances))


if __name__ == "__main__":
    main()
