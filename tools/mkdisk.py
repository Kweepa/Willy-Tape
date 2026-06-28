#!/usr/bin/env python3
"""Build jsw.d64 from jsw.prg and room PRG binaries."""

import argparse
import os
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

SECTOR_SIZE = 256
TRACKS = 35
SECTORS_PER_TRACK = 21

# VICE install (matches make.bat); override with --c1541 or VICE_BIN env
DEFAULT_VICE_BIN = Path(r"c:\app\vice3.10\bin")


def room_dos_name(room_id: int) -> str:
    """KERNAL LOAD filename: R + zero-padded decimal, e.g. room 33 -> r33."""
    return f"r{room_id:02d}"


def find_c1541(explicit: Optional[Path] = None) -> Optional[Path]:
    if explicit is not None:
        p = explicit
        return p if p.is_file() else None
    env = os.environ.get("VICE_BIN")
    if env:
        p = Path(env) / "c1541.exe"
        if p.is_file():
            return p
        p = Path(env) / "c1541"
        if p.is_file():
            return p
    for name in ("c1541.exe", "c1541"):
        p = DEFAULT_VICE_BIN / name
        if p.is_file():
            return p
    w = shutil.which("c1541")
    return Path(w) if w else None


def collect_room_files(room_dir: Path) -> List[Tuple[int, Path]]:
    """Return (room_id, path) for numeric staging files from mkroom.py --all."""
    rooms: List[Tuple[int, Path]] = []
    for p in room_dir.iterdir():
        if p.is_file() and p.name.isdigit():
            rooms.append((int(p.name), p))
    return sorted(rooms)


def collect_extra_prgs(room_dir: Path) -> List[Tuple[str, Path]]:
    """Non-numeric PRG staging files (e.g. rjy joystick patch)."""
    extras: List[Tuple[str, Path]] = []
    rjy = room_dir / "rjy"
    if rjy.is_file():
        extras.append(("rjy", rjy))
    return extras


def resolve_loader(path: Optional[Path]) -> Optional[Path]:
    """1541-side loader binary (repo-root LOADER by default)."""
    if path is None:
        return None
    p = path if path.is_absolute() else Path.cwd() / path
    return p if p.is_file() else None


def build_with_c1541(
    c1541: Path,
    d64: Path,
    prg: Optional[Path],
    rooms: List[Tuple[int, Path]],
    extras: List[Tuple[str, Path]],
    loader: Optional[Path],
) -> None:
    if d64.exists():
        d64.unlink()
    # Batch mode: format, attach once, then write all files in one c1541 invocation
    cmd = [
        str(c1541),
        "-format",
        "jsw,01",
        "d64",
        str(d64),
        "-attach",
        str(d64),
    ]
    if prg and prg.exists():
        cmd.extend(["-write", str(prg), "jsw"])
    for room_id, room in rooms:
        name = room_dos_name(room_id)
        cmd.extend(["-write", str(room), f"{name},p"])
    for dos_name, path in extras:
        cmd.extend(["-write", str(path), f"{dos_name},p"])
    if loader is not None:
        cmd.extend(["-write", str(loader), "loader,p"])
    subprocess.check_call(cmd)
    extra_bits = []
    if extras:
        extra_bits.append(f"{len(extras)} extra PRG")
    if loader is not None:
        extra_bits.append("loader")
    print(
        f"Wrote {d64} via {c1541} ({len(rooms)} room files"
        + (f", {', '.join(extra_bits)}" if extra_bits else "")
        + ")"
    )


# MinimalD64 class below


class MinimalD64:
    """Minimal D64 writer for development when c1541 is unavailable."""

    def __init__(self):
        self.data = bytearray(SECTOR_SIZE * SECTORS_PER_TRACK * TRACKS)
        self.next_t = 1
        self.next_s = 2
        self._init_bam()
        self._init_dir()

    def _ts_off(self, track: int, sector: int) -> int:
        return (track * SECTORS_PER_TRACK + sector) * SECTOR_SIZE

    def _init_bam(self):
        self.data[0x90] = 0x41
        self.data[0xA0] = 18
        self.data[0xA1] = 1

    def _init_dir(self):
        off = self._ts_off(18, 1)
        self.data[off] = 0x00
        self.data[off + 1] = 0xFF

    def _alloc_sector(self):
        t, s = self.next_t, self.next_s
        self.next_s += 1
        if self.next_s >= SECTORS_PER_TRACK:
            self.next_s = 0
            self.next_t += 1
        return t, s

    def add_file(self, name: str, payload: bytes, file_type: int = 0x82):
        name = name.lower().ljust(16)[:16]
        entry_base = self._ts_off(18, 1) + 2
        for slot in range(8):
            e = entry_base + slot * 32
            if self.data[e] in (0x00, 0xA0):
                break
        else:
            raise RuntimeError("directory full")

        sectors_needed = (len(payload) + SECTOR_SIZE - 1) // SECTOR_SIZE
        first_t, first_s = self._alloc_sector()
        t, s = first_t, first_s

        for i in range(sectors_needed):
            off = self._ts_off(t, s)
            start = i * SECTOR_SIZE
            chunk = payload[start : start + SECTOR_SIZE]
            if i + 1 < sectors_needed:
                nt, ns = self._alloc_sector()
                self.data[off] = nt
                self.data[off + 1] = ns
                t, s = nt, ns
            else:
                self.data[off] = 0
                self.data[off + 1] = 0xFF
            self.data[off + 2 : off + 2 + len(chunk)] = chunk

        self.data[e] = file_type
        self.data[e + 0x1C] = first_t
        self.data[e + 0x1D] = first_s
        self.data[e + 0x1E] = sectors_needed & 0xFF
        self.data[e + 0x1F] = (sectors_needed >> 8) & 0xFF
        for i, c in enumerate(name):
            self.data[e + 0x03 + i] = ord(c)

    def save(self, path: Path):
        path.write_bytes(self.data)


def build_pure_python(
    d64: Path,
    prg: Optional[Path],
    rooms: List[Tuple[int, Path]],
    extras: List[Tuple[str, Path]],
    loader: Optional[Path],
) -> None:
    d = MinimalD64()
    if prg and prg.exists():
        d.add_file("jsw", prg.read_bytes(), file_type=0x82)
    for room_id, room in rooms:
        d.add_file(room_dos_name(room_id), room.read_bytes(), file_type=0x82)
    for dos_name, path in extras:
        d.add_file(dos_name, path.read_bytes(), file_type=0x82)
    if loader is not None:
        d.add_file("loader", loader.read_bytes(), file_type=0x82)
    d.save(d64)
    extra_bits = []
    if extras:
        extra_bits.append(f"{len(extras)} extra PRG")
    if loader is not None:
        extra_bits.append("loader")
    print(
        f"Wrote {d64} (pure Python, {len(rooms)} room files"
        + (f", {', '.join(extra_bits)}" if extra_bits else "")
        + ")"
    )


def main():
    ap = argparse.ArgumentParser(description="Build jsw.d64 from PRG and room binaries")
    ap.add_argument("--out", default="jsw.d64")
    ap.add_argument("--prg", default="jsw.prg")
    ap.add_argument("--rooms", default="rooms/out", help="directory with numeric room PRG files")
    ap.add_argument(
        "--loader",
        default="LOADER",
        help="1541-side loader binary to include (default: LOADER; omit file to skip)",
    )
    ap.add_argument(
        "--c1541",
        type=Path,
        default=None,
        help=f"path to c1541 (default: {DEFAULT_VICE_BIN}\\c1541.exe or PATH)",
    )
    args = ap.parse_args()

    room_dir = Path(args.rooms)
    rooms = collect_room_files(room_dir)
    extras = collect_extra_prgs(room_dir)
    loader = resolve_loader(Path(args.loader) if args.loader else None)
    if not rooms:
        print("No room PRG files found; run mkroom.py --all first", file=sys.stderr)
        sys.exit(1)

    d64 = Path(args.out)
    prg = Path(args.prg)
    c1541 = find_c1541(args.c1541)
    if c1541:
        build_with_c1541(
            c1541, d64, prg if prg.exists() else None, rooms, extras, loader
        )
    else:
        print("c1541 not found; using pure-Python D64 writer", file=sys.stderr)
        build_pure_python(
            d64, prg if prg.exists() else None, rooms, extras, loader
        )


if __name__ == "__main__":
    main()
