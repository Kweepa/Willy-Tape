#!/usr/bin/env python3
"""Disassemble MoveGuardians loop."""
import re
from pathlib import Path

prg = Path("jsw.prg").read_bytes()
LOAD = 0x1201
labels = {}
for line in Path("jsws.lbl").read_text().splitlines():
    m = re.match(r"al C:([0-9a-f]+) \.(.+)", line, re.I)
    if m:
        labels[m.group(2)] = int(m.group(1), 16)

start = labels["MoveGuardians"]
end = labels.get("move_guardians_done", start + 200)
chunk = prg[start - LOAD + 2 : end - LOAD + 2 + 80]

for i, b in enumerate(chunk[:80]):
    print(f"{start+i:04X}: {b:02X}", end="  ")
    if (i + 1) % 8 == 0:
        print()
