#!/usr/bin/env python3
"""Disassemble CopyGuardianFrame from jsw.prg."""
import re
from pathlib import Path

prg = Path("jsw.prg").read_bytes()
LOAD = 0x1201
labels = {}
for line in Path("jsws.lbl").read_text().splitlines():
    m = re.match(r"al C:([0-9a-f]+) \.(.+)", line, re.I)
    if m:
        labels[m.group(2)] = int(m.group(1), 16)


def at(addr: int, n: int = 256) -> bytes:
    return prg[addr - LOAD + 2 : addr - LOAD + 2 + n]


def disasm6502(data: bytes, base: int) -> None:
    i = 0
    while i < len(data):
        a = base + i
        op = data[i]
        if op == 0x20 and i + 2 < len(data):
            t = data[i + 1] | (data[i + 2] << 8)
            print(f"{a:04X}: JSR ${t:04X}")
            i += 3
        elif op == 0x4C and i + 2 < len(data):
            t = data[i + 1] | (data[i + 2] << 8)
            print(f"{a:04X}: JMP ${t:04X}")
            i += 3
        elif op == 0xAD and i + 2 < len(data):
            t = data[i + 1] | (data[i + 2] << 8)
            print(f"{a:04X}: LDA ${t:04X}")
            i += 3
        elif op == 0x8D and i + 2 < len(data):
            t = data[i + 1] | (data[i + 2] << 8)
            print(f"{a:04X}: STA ${t:04X}")
            i += 3
        elif op == 0xA5 and i + 1 < len(data):
            print(f"{a:04X}: LDA ${data[i+1]:02X}")
            i += 2
        elif op == 0x85 and i + 1 < len(data):
            print(f"{a:04X}: STA ${data[i+1]:02X}")
            i += 2
        elif op == 0x91 and i + 1 < len(data):
            print(f"{a:04X}: STA (${data[i+1]:02X}),Y")
            i += 2
        elif op == 0xA9 and i + 1 < len(data):
            print(f"{a:04X}: LDA #{data[i+1]:02X}")
            i += 2
        elif op == 0x18:
            print(f"{a:04X}: CLC")
            i += 1
        elif op == 0x69 and i + 1 < len(data):
            print(f"{a:04X}: ADC #{data[i+1]:02X}")
            i += 2
        elif op == 0xA2 and i + 1 < len(data):
            print(f"{a:04X}: LDX #{data[i+1]:02X}")
            i += 2
        elif op == 0xA0 and i + 1 < len(data):
            print(f"{a:04X}: LDY #{data[i+1]:02X}")
            i += 2
        elif op == 0xA8:
            print(f"{a:04X}: TAY")
            i += 1
        elif op == 0xAA:
            print(f"{a:04X}: TAX")
            i += 1
        elif op == 0xC8:
            print(f"{a:04X}: INY")
            i += 1
        elif op == 0xCA:
            print(f"{a:04X}: DEX")
            i += 1
        elif op == 0xE6 and i + 1 < len(data):
            print(f"{a:04X}: INC ${data[i+1]:02X}")
            i += 2
        elif op == 0xEE and i + 2 < len(data):
            t = data[i + 1] | (data[i + 2] << 8)
            print(f"{a:04X}: INC ${t:04X}")
            i += 3
        elif op == 0xD0 and i + 1 < len(data):
            print(f"{a:04X}: BNE ${a+2+data[i+1]:04X}")
            i += 2
        elif op == 0xF0 and i + 1 < len(data):
            print(f"{a:04X}: BEQ ${a+2+data[i+1]:04X}")
            i += 2
        elif op == 0x10 and i + 1 < len(data):
            print(f"{a:04X}: BPL ${a+2+data[i+1]:04X}")
            i += 2
        elif op == 0x30 and i + 1 < len(data):
            print(f"{a:04X}: BMI ${a+2+data[i+1]:04X}")
            i += 2
        elif op == 0x24 and i + 1 < len(data):
            print(f"{a:04X}: BIT ${data[i+1]:02X}")
            i += 2
        elif op == 0x29 and i + 1 < len(data):
            print(f"{a:04X}: AND #{data[i+1]:02X}")
            i += 2
        elif op == 0x49 and i + 1 < len(data):
            print(f"{a:04X}: EOR #{data[i+1]:02X}")
            i += 2
        elif op == 0x60:
            print(f"{a:04X}: RTS")
            i += 1
            break
        else:
            print(f"{a:04X}: db ${op:02X}")
            i += 1


start = labels["CopyGuardianFrame"]
end = labels["MoveGuardians"]
print(f"CopyGuardianFrame ${start:04X}-${end:04X}\n")
disasm6502(at(start, end - start), start)

# overlap check
sf = labels["sprite_frames"]
frames = 170 * 32
sf_end = sf + frames
gdb = labels["guardian_data_base"]
print(f"\nsprite_frames ${sf:04X}-${sf_end:04X}")
print(f"guardian_data_base ${gdb:04X}-${gdb+60:04X}")
if gdb < sf_end:
    print(f"OVERLAP: guardian AoS overwrites sprite pool by {sf_end - gdb} bytes")
