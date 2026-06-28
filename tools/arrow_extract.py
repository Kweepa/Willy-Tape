#!/usr/bin/env python3
"""Emit @arrow tags into roomNN.txt from Spectrum SkoolKit room data."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import jswimport as ji  # noqa: E402
from mkroom import (  # noqa: E402
    ARROW_ENTITY_LTR,
    ARROW_ENTITY_RTL,
    ARROW_TEMPLATE_SOUND,
    ARROW_TEMPLATE_X,
    parse_room,
)

ATTIC_ROOM_ID = 41
ATTIC_RTL_Y_FIX = 41
ARROW_ROOM_IDS = (7, 9, 11, 12, 15, 17, 36, 37, 41, 42, 56)
ARROW_TAG_LINE = re.compile(r"^@arrow\b", re.I)
ROPE_TAG_LINE = re.compile(r"^@rope\b", re.I)


def room_has_rope(text: str) -> bool:
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if ROPE_TAG_LINE.match(line):
            return True
    return False


def first_arrow_entity(entities: list[tuple[int, int]]) -> tuple[int, int] | None:
    for ent_id, spec in entities:
        if ent_id in (ARROW_ENTITY_LTR, ARROW_ENTITY_RTL):
            return ent_id, spec
    return None


def remap_arrow_x(value: int, drop: list[int]) -> int:
    if value >= 32:
        return value & 0xFF
    return ji.remap_col(value, drop) & 0xFF


def decode_arrow(
    rid: int, ent_id: int, spec: int, drop: list[int]
) -> tuple[int, int, int, int]:
    y = spec // 2
    if rid == ATTIC_ROOM_ID and ent_id == ARROW_ENTITY_RTL and spec == 213:
        y = ATTIC_RTL_Y_FIX
    v = 1 if ent_id == ARROW_ENTITY_LTR else -1
    x = ARROW_TEMPLATE_X[ent_id]
    sound = ARROW_TEMPLATE_SOUND[ent_id]
    return y, remap_arrow_x(x, drop), v, remap_arrow_x(sound, drop)


def drop_columns_for_room(rid: int) -> list[int]:
    data = ji.load_room_blob(rid)
    room = ji.parse_room_block(data)
    grid = ji.decode_layout(room["layout"])
    vcols: set[int] = set()
    entities_db = ji.load_entities()
    for ent_id, spec in room["entities"]:
        ent = entities_db.get(ent_id)
        if ent and ji.is_vertical(ent):
            vcols.add(spec & 31)
    return ji.choose_drop_columns(grid, vcols | ji.feature_columns(room))


def format_arrow_line(y: int, x: int, v: int, sound: int) -> str:
    return f"@arrow y={y} x={x} v={v} sound={sound}"


def upsert_arrow_tag(path: Path, arrow_line: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    replaced = False
    for line in lines:
        if ARROW_TAG_LINE.match(line.split("#", 1)[0].strip()):
            if not replaced:
                out.append(arrow_line)
                replaced = True
            continue
        out.append(line)
    if not replaced:
        insert_at = len(out)
        for i, line in enumerate(out):
            if line.strip().startswith("@belt"):
                insert_at = i + 1
                break
        out.insert(insert_at, arrow_line)
        if insert_at < len(out) and out[insert_at].strip():
            out.insert(insert_at + 1, "")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def emit_arrows(rooms_dir: Path, *, dry_run: bool = False) -> None:
    for rid in ARROW_ROOM_IDS:
        path = rooms_dir / f"room{rid:02d}.txt"
        if not path.is_file():
            print(f"skip room {rid}: missing {path.name}", file=sys.stderr)
            continue
        text = path.read_text(encoding="utf-8")
        if room_has_rope(text):
            print(f"skip room {rid}: @rope present")
            continue
        data = ji.load_room_blob(rid)
        block = ji.parse_room_block(data)
        pair = first_arrow_entity(block["entities"])
        if pair is None:
            print(f"skip room {rid}: no arrow entity in Spectrum data", file=sys.stderr)
            continue
        ent_id, spec = pair
        drop = drop_columns_for_room(rid)
        y, x, v, sound = decode_arrow(rid, ent_id, spec, drop)
        arrow_line = format_arrow_line(y, x, v, sound)
        room = parse_room(text, source=path)
        if room.get("arrow"):
            room["arrow"] = {"y": y, "x": x, "v": v, "sound": sound}
        else:
            room["arrow"] = {"y": y, "x": x, "v": v, "sound": sound}
        if dry_run:
            print(f"would write {path.name}: {arrow_line}")
        else:
            upsert_arrow_tag(path, arrow_line)
            print(f"wrote {path.name}: {arrow_line}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Emit @arrow tags from Spectrum room data")
    ap.add_argument(
        "rooms_dir",
        nargs="?",
        default=str(ROOT / "rooms"),
        help="directory containing roomNN.txt files",
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="print tags only, do not modify room files",
    )
    args = ap.parse_args()
    emit_arrows(Path(args.rooms_dir), dry_run=args.dry_run)


if __name__ == "__main__":
    main()
