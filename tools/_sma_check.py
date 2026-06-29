#!/usr/bin/env python3
"""Inspect CopyGuardianFrame in current jsw.prg."""
import re
from pathlib import Path

prg = Path("jsw.prg").read_bytes()
LOAD = 0x1201
labels = {}
for line in Path("jsws.lbl").read_text().splitlines():
    m = re.match(r"al C:([0-9a-f]+) \.(.+)", line, re.I)
    if m:
        labels[m.group(2)] = int(m.group(1), 16)


def at(addr: int, n: int = 32) -> bytes:
    return prg[addr - LOAD + 2 : addr - LOAD + 2 + n]


for name in [
    "CopyGuardianFrame",
    "ResolveGuardianFramePtr",
    "GetSpriteFrameAddr",
    "GetHorizontalGuardianFramePtr",
    "GetVerticalGuardianFramePtr",
    "MoveGuardians",
    "sprite_frames",
    "sprite_set_metadata",
]:
    addr = labels[name]
    b = at(addr, 24)
    print(f"{name} ${addr:04X}: {' '.join(f'{x:02X}' for x in b)}")

# Find mod_src_col1 = lda sprite_frames inside CopyGuardianFrame
cgf = labels["CopyGuardianFrame"]
chunk = at(cgf, 120)
for i in range(len(chunk) - 2):
    if chunk[i] == 0xAD:  # LDA abs
        lo, hi = chunk[i + 1], chunk[i + 2]
        print(f"  CopyGuardianFrame+{i}: LDA ${hi:02X}{lo:02X}")

# Simulate globes frame 99
ht = 0x63
g_frame = 0
idx = ht + g_frame
base = labels["sprite_frames"]
addr = base + idx * 32
print(f"\nGlobes frame0: idx={idx} addr=${addr:04X}")
print("bytes:", at(addr, 16).hex())

# guardian 0 runtime record
gdb = labels["guardian_data_base"]
print(f"\nguardian0 record @ ${gdb:04X}:", at(gdb, 10).hex())

# set 25 metadata
meta = labels["sprite_set_metadata"] + 25 * 2
print(f"set25 meta @ ${meta:04X}:", at(meta, 2).hex())
