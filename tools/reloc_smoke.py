#!/usr/bin/env python3
"""Verify tape relocation bytes in jsw.prg and room 33 catalogue decode."""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOAD = 0x1201
IRQ_VECTOR = 0x0314


def parse_lbl(path: Path) -> dict[str, int]:
    labels: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1].startswith("C:"):
            labels[parts[2].lstrip(".")] = int(parts[1][2:], 16)
    return labels


def sort_lbl_file(src: Path, dst: Path) -> None:
    lines = [line for line in src.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip()]

    def key(line: str) -> int:
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("C:"):
            return int(parts[1][2:], 16)
        return -1

    dst.write_text("\n".join(sorted(lines, key=key)) + "\n", encoding="utf-8")


def load_labels(root: Path) -> dict[str, int]:
    lbl_path = root / "jsws.lbl"
    raw_path = root / "jsw.lbl"
    if raw_path.is_file():
        sort_lbl_file(raw_path, lbl_path)
    if not lbl_path.is_file():
        raise SystemExit(f"missing {lbl_path} — run make.bat first")
    return parse_lbl(lbl_path)


def prg_slice(prg: bytes, addr: int, n: int) -> bytes:
    return prg[addr - LOAD : addr - LOAD + n]


def check_jsr_targets(block: bytes, run_base: int) -> list[str]:
    errors: list[str] = []
    i = 0
    while i < len(block) - 2:
        if block[i] != 0x20:
            i += 1
            continue
        target = block[i + 1] | (block[i + 2] << 8)
        if target < 0x0200 or (target >= 0x0400 and target < 0x1200) or target >= 0x6000:
            errors.append(f"jsr ${target:04X} at run ${run_base + i:04X} outside PRG")
        i += 3
    return errors


def simulate_room33(cat: bytes) -> tuple[int, int]:
    sys.path.insert(0, str(ROOT / "tools"))
    from mkcatalogue import udg_blob_size

    count, = struct.unpack_from("<H", cat, 0)
    records_off = 2 + count * 4
    idx_off = 2 + 33 * 4
    rec_off, _ = struct.unpack_from("<HH", cat, idx_off)
    blob = cat[records_off + rec_off :]
    pos = 0
    while blob[pos] != 0:
        pos += 1
    pos += 1
    flags = blob[pos + 6]
    pos += 8 + 6 + udg_blob_size(flags)
    cells: list[int] = []
    while len(cells) < 384:
        tok = blob[pos]
        pos += 1
        cells.extend([tok & 7] * (tok >> 3))
    return sum(1 for c in cells if c), len(set(cells))


def main() -> None:
    prg_path = ROOT / "jsw.prg"
    cat_path = ROOT / "catalogue.bin"
    if not prg_path.is_file():
        raise SystemExit(f"missing {prg_path}")
    prg = prg_path.read_bytes()[2:]
    labels = load_labels(ROOT)

    errors: list[str] = []
    run = labels["RELOC_LO1_BASE"]
    src = labels["reloc_lo1_src"]
    size = labels["reloc_lo1_size"]
    if run + size > IRQ_VECTOR:
        errors.append(f"reloc lo1 spans IRQ vector (${run:04X}+${size:X})")
    src_bytes = prg_slice(prg, src, size)
    if src_bytes[:3] != bytes([0xA2, 0x00, 0xA0]):
        errors.append(f"reloc lo1 src at ${src:04X} bad prologue")
    errors.extend(check_jsr_targets(src_bytes, run))

    lo1_max = labels["RELOC_LO1_LIMIT"] - labels["RELOC_LO1_BASE"]
    if size > lo1_max:
        errors.append(f"reloc lo1 size {size} > {lo1_max}")

    rope = prg_slice(prg, labels["rope_xadd_table"], 4)
    if rope != bytes([0x01, 0x02, 0x03, 0x02]):
        errors.append("rope_xadd_table missing in PRG")

    gs_run = labels["GetSpriteFrameAddr"]
    if gs_run < 0x1A00:
        errors.append(f"GetSpriteFrameAddr at ${gs_run:04X} should live in high bank")

    warm = prg_slice(prg, labels["WarmStart"], 0x50)
    if warm[0:2] != bytes([0xA9, 0x7F]):
        errors.append("WarmStart missing lda #$7f")
    rtb = labels["RelocateTapeBlocks"]
    if bytes([0x20, rtb & 0xFF, rtb >> 8]) not in warm:
        errors.append("WarmStart missing jsr RelocateTapeBlocks")
    if bytes([0xA9, 0x15, 0x8D, 0x14, 0x03]) not in warm:
        errors.append("WarmStart missing IRQ vector setup after RelocateTapeBlocks")

    dec = prg_slice(prg, labels["DecompressRoom"], 0x30)
    rle = labels["RleUnpack"]
    if bytes([0x20, rle & 0xFF, rle >> 8]) not in dec:
        errors.append("DecompressRoom missing jsr RleUnpack")

    nonzero, uniq = simulate_room33(cat_path.read_bytes())
    if nonzero < 50:
        errors.append(f"room 33 RLE only {nonzero} nonzero cells (expected ~81)")

    if errors:
        for e in errors:
            print(f"FAIL: {e}")
        raise SystemExit(1)

    print(
        f"reloc smoke OK — lo1 {size} B in page 2; residents in PRG; "
        f"room 33 paints {nonzero} cells, types {uniq}"
    )


if __name__ == "__main__":
    main()
