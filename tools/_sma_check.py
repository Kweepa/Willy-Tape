#!/usr/bin/env python3
"""Inspect CopyGuardianFrame SMA in built jsw.prg."""
from pathlib import Path

prg = Path("jsw.prg").read_bytes()
LOAD = 0x1201


def at(addr: int, n: int = 32) -> bytes:
    return prg[addr - LOAD + 2 : addr - LOAD + 2 + n]


labels = {
    "CopyGuardianFrame": 0x243F,
    "ResolveGuardianFramePtr": 0x2434,
    "mod_src_col1": 0x2479,
    "mod_src_col2": 0x2486,
    "GetSpriteFrameAddr": 0x22EA,
    "guardian_sprite_frames": 0x616D,
    "guardian_data_base": 0x5827,
}

for k, v in labels.items():
    b = at(v, 16)
    print(f"{k} ${v:04X}: {' '.join(f'{x:02X}' for x in b)}")


def disasm_abs_lda_inc(addr: int) -> None:
    b = at(addr, 24)
    print(f"\n=== mod_src at ${addr:04X} ===")
    i = 0
    while i < len(b):
        op = b[i]
        if op == 0xAD and i + 2 < len(b):
            lo, hi = b[i + 1], b[i + 2]
            print(f"  LDA ${hi:02X}{lo:02X}")
            i += 3
        elif op == 0xEE and i + 2 < len(b):
            lo, hi = b[i + 1], b[i + 2]
            print(f"  INC ${hi:02X}{lo:02X}")
            i += 3
        elif op == 0xD0 and i + 1 < len(b):
            print(f"  BNE +{b[i + 1]}")
            i += 2
        elif op == 0x91 and i + 1 < len(b):
            print(f"  STA (${b[i + 1]:02X}),Y")
            i += 2
        elif op == 0xC8:
            print("  INY")
            i += 1
        elif op == 0xCA:
            print("  DEX")
            i += 1
        elif op == 0x10 and i + 1 < len(b):
            print(f"  BPL +{b[i + 1]}")
            i += 2
        else:
            print(f"  db ${op:02X}")
            i += 1


disasm_abs_lda_inc(0x2479)
disasm_abs_lda_inc(0x2486)

# Patch simulation
arr = 0x6DCC  # frame 99
col1 = arr
col2 = arr + 16
print(f"\nPatch arr=${arr:04X} -> col1=${col1:04X} col2=${col2:04X}")

# What bytes does col1 path read?
pool = 0x616D
idx = (col1 - pool) // 32
off = col1 - LOAD + 2
chunk = prg[off : off + 16]
print(f"col1 reads file offset {off:#x} ({len(chunk)} B):", chunk.hex())

# If wrongly patched to guardian_data_base
bad = 0x5827
off2 = bad - LOAD + 2
print(f"If arr=${bad:04X} col1 reads:", prg[off2 : off2 + 16].hex())

# Check GetSpriteFrameAddr
print("\nGetSpriteFrameAddr:")
b = at(0x22EA, 20)
for i, x in enumerate(b):
    print(f"  {0x22EA+i:04X}: {x:02X}")

# Frame 99 expected
frame99_off = pool - LOAD + 2 + 99 * 32
print(f"\nFrame 99 @ ${pool + 99*32:04X}:", prg[frame99_off : frame99_off + 32].hex())
