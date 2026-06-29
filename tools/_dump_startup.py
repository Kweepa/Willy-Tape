#!/usr/bin/env python3
"""Disassemble key PRG sites for startup crash debug."""
from pathlib import Path

prg = Path("jsw.prg").read_bytes()
LOAD = 0x1201


def at(addr: int, n: int = 32) -> bytes:
    return prg[addr - LOAD + 2 : addr - LOAD + 2 + n]


for sym, addr in [
    ("FindRoomRecord", 0x1B46),
    ("RoomRecordPtrs", 0x2651),
    ("Collide", None),
]:
    b = at(addr, 20)
    print(f"{sym} ${addr:04X}: {' '.join(f'{x:02X}' for x in b)}")

gpf = at(0x2133, 16)
print("\nGetPlayerFrameAddr:")
if gpf[0] == 0x48 and gpf[1] == 0xA9:
    print(f"  lda #{gpf[2]} (immediate)")

meta_off = 42 * 2
meta = at(0x447F + meta_off, 2)
start_frame = meta[0]
print(f"\nWilly metadata: start={start_frame}, count={meta[1]}")
frame0 = 0x44D5 + start_frame * 32
print(f"Frame0 ${frame0:04X}: {' '.join(f'{x:02X}' for x in at(frame0, 8))}")
