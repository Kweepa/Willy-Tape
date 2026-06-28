#!/usr/bin/env python3
"""Segment and routine size breakdown from jsw.lbl."""

import re
import sys
from pathlib import Path

lbl = Path(sys.argv[1] if len(sys.argv) > 1 else "jsw.lbl")
labels = {}
for line in lbl.read_text().splitlines():
    m = re.match(r"al C:([0-9a-f]+) \.(.+)", line, re.I)
    if m:
        labels[m.group(2)] = int(m.group(1), 16)

prg_end = labels.get("prg_end", max(labels.values()))
load_base = 0x1000
room_base = 0x1A05
resident_limit = room_base - load_base

MODULES = [
    ("header/boot", ["cold_start", "warm_start", "basic_end"]),
    ("gameloop", ["start_game", "start_map", "main_loop"]),
    ("map", ["ResetGame", "DrawMap", "CheckRoomEdge"]),
    ("loader", ["LoadRoom", "room_name", "ParseRoomMeta"]),
    ("ramp", ["calculate_ramp_y", "do_walking_ramp_check", "do_falling_ramp_check"]),
    ("willy", ["try_touch", "Collide", "DrawPlayer"]),
    ("util", ["ConvertXYToScreenAddr", "UpdateMoveCounters"]),
    ("input", ["GetPlayerInput", "ScanKeyRow"]),
    ("guardians", ["CopyDownGuardianData", "MoveGuardians", "EraseGuardians"]),
    ("warm boot", ["WarmStart", "init24_val"]),
]

bounds = []
for name, syms in MODULES:
    for sym in syms:
        if sym in labels:
            bounds.append((labels[sym], name, sym))
            break
bounds.sort()


def bytes_past_room(start, end):
    if end < room_base:
        return 0
    if start >= room_base:
        return end - start + 1
    return end - room_base + 1


rows = []
for i, (start, name, sym) in enumerate(bounds):
    end = bounds[i + 1][0] - 1 if i + 1 < len(bounds) else prg_end - 1
    size = end - start + 1
    past = bytes_past_room(start, end)
    if name == "warm boot":
        resident = 0
    else:
        resident = size - past
    rows.append((name, start, end, size, past, resident, sym))

rows.sort(key=lambda r: -r[3])

print(f"PRG: ${load_base:04X}-${prg_end - 1:04X}  ({prg_end - load_base} bytes)")
print(f"Resident budget below ${room_base:04X}: {resident_limit} bytes")
print()
print(f"{'Segment':22} {'Size':>5}  {'Past image_base':>15}  {'Resident':>8}  Entry")
print("-" * 72)
for name, start, end, size, past, resident, sym in rows:
    past_s = f"{past} B" if past else "-"
    res_s = "(boot)" if name == "warm boot" else f"{resident} B"
    print(f"{name:22} {size:5}  {past_s:>10}  {res_s:>8}  {sym}")

resident_total = sum(r[5] for r in rows)
guard_past = next((r[4] for r in rows if r[0] == "guardians"), 0)
over = resident_total - resident_limit
print()
print(f"Resident total: {resident_total} B  (over budget by {over} B)")
if guard_past:
    print(f"Trim target: {guard_past} B of guardian code past ${room_base:04X}")
else:
    print(f"Headroom below ${room_base:04X}: {resident_limit - resident_total} B")
print()

for mod_start, mod_name, _ in bounds:
    if mod_name in ("spritedata", "warm boot", "header/boot"):
        continue
    mod_end = next(
        (bounds[i + 1][0] - 1 for i, (s, n, _) in enumerate(bounds) if n == mod_name and i + 1 < len(bounds)),
        prg_end - 1,
    )
    syms = [
        (addr, sym)
        for sym, addr in labels.items()
        if mod_start <= addr <= mod_end and sym and sym[0].isupper()
    ]
    syms.sort(key=lambda x: x[0])
    if len(syms) < 2:
        continue
    sizes = []
    for i, (addr, sym) in enumerate(syms):
        end = syms[i + 1][0] - 1 if i + 1 < len(syms) else mod_end
        sz = end - addr + 1
        past = bytes_past_room(addr, end)
        sizes.append((sz, sym, addr, past))
    sizes.sort(key=lambda x: -x[0])
    print(f"{mod_name} — routines (largest first):")
    for sz, sym, addr, past in sizes[:10]:
        extra = f"  [{past} B past ${room_base:04X}]" if past else ""
        print(f"  {sz:4} B  ${addr:04X}  {sym}{extra}")
    print()
