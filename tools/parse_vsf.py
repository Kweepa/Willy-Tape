#!/usr/bin/env python3
"""Parse VICE VIC-20 VSF RAM (VIC20MEM v1.x layout)."""

from __future__ import annotations

import struct
import sys
from pathlib import Path


def read_vic20_ram(path: Path) -> bytearray:
    data = path.read_bytes()
    tag = data.find(b"VIC20MEM")
    if tag < 0:
        raise ValueError("VIC20MEM not found")

    off = tag + 8  # skip name
    major, minor = data[off], data[off + 1]
    off += 2
    mod_size = struct.unpack_from("<I", data, off)[0]
    off += 4
    chunk_end = tag + 8 + mod_size if mod_size else len(data)

    config = data[off]
    off += 1
    # VICE 3.x adds one extra byte after CONFIG (ROM write protect)
    if major >= 1 and minor >= 1:
        off += 1

    ram = bytearray(0x10000)

    def take(n: int) -> bytes:
        nonlocal off
        blob = data[off : off + n]
        off += n
        return blob

    ram[0x0000:0x0400] = take(0x0400)
    ram[0x1000:0x2000] = take(0x1000)
    ram[0x9400:0x9C00] = take(0x0800)
    if config & 1:
        ram[0x0400:0x1000] = take(0x0C00)
    if config & 2:
        ram[0x2000:0x4000] = take(0x2000)
    if config & 4:
        ram[0x4000:0x6000] = take(0x2000)
    if config & 8:
        ram[0x6000:0x8000] = take(0x2000)
    if config & 32:
        ram[0xA000:0xC000] = take(0x2000)

    return ram


def cpu_pc(path: Path) -> int | None:
    data = path.read_bytes()
    tag = data.find(b"C20CPU")
    if tag < 0:
        return None
    off = tag + 8 + 2 + 4  # name + ver + size
    # Registers block: A, X, Y, SP, PC lo, PC hi ...
    if off + 6 > len(data):
        return None
    return data[off + 4] | (data[off + 5] << 8)


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "vice-snapshot-20260701032309.vsf")
    ram = read_vic20_ram(path)
    pc = cpu_pc(path)

    addrs = [0x120D, 0x1800, 0x200, 0x2B6, 0x314, 0x316, 0x34C, 0x36C, 0x396, 0x5B, 0x1000, 0x1808]
    if pc is not None:
        print(f"CPU PC ${pc:04X}: {ram[pc : pc + 8].hex()}")
    for a in addrs:
        print(f"${a:04X}: {ram[a : a + 12].hex()}")


if __name__ == "__main__":
    main()
