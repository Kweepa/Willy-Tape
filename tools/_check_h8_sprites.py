#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mkroom import parse_room

ROOMS = Path(__file__).resolve().parent.parent / "rooms"


def h8_sprite_key(room):
    """One key per distinct h8 sprite block in guardiansprites."""
    gs = room["guardiansprites"] or b""
    keys = []
    for g in room["guardians"]:
        if g["axis"] == 0 and g["fctl"] == 1:
            keys.append((g["fmin"], g["fmax"], g["fctl"]))
    return keys


for p in sorted(ROOMS.glob("room*.txt")):
    room = parse_room(p.read_text(), p)
    h8 = [g for g in room["guardians"] if g["axis"] == 0 and g["fctl"] == 1]
    if len(h8) < 2:
        continue
    frame_sets = {(g["fmin"], g["fmax"]) for g in h8}
    colors = [g["color"] for g in h8]
    print(
        f"room {room['id']:02d} {room['title'][:22]:22s} "
        f"h8={len(h8)} frame_sets={len(frame_sets)} colors={len(set(colors))}"
    )
