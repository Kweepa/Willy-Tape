#!/usr/bin/env python3
"""Detect code/data and runtime RAM overlaps from sorted ACME labels (jsws.lbl)."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# PRG segments: (name, start_label, end_label). end label is exclusive (*=).
TAPE_PRG_SEGMENTS: list[tuple[str, str, str]] = [
    ("low bank code", "cold_start", "low_bank_end"),
    ("high bank code", "high_bank", "high_bank_code_end"),
    ("catalogue rooms", "CatalogueImage", "catalogue_rooms_end"),
    ("catalogue tile UDGs", "udg_pool_counts", "catalogue_udgs_end"),
    ("catalogue sprites", "sprite_set_metadata", "catalogue_sprites_end"),
]

# Embedded PRG sub-blobs (start, exclusive end).
TAPE_PRG_BLOBS: list[tuple[str, str, str]] = [
    ("ingame_tune_pitch_rom", "ingame_tune_pitch_rom", "ingame_tune_pitch_rom_end"),
    ("ingame_tune_idx_rom", "ingame_tune_idx_rom", "ingame_tune_idx_rom_end"),
    ("sprite_set_metadata", "sprite_set_metadata", "sprite_frames"),
    ("sprite_frames", "sprite_frames", "catalogue_sprites_end"),
]

# Runtime RAM only — not fixed PRG addresses. Code/data above $1A00 flow from
# jsw.asm !source order; catalogue is embedded at CatalogueImage … prg_end.
TAPE_RUNTIME_RAM: list[tuple[str, str | int, str | int, str]] = [
    ("pickup_got", "pickup_got", "pickup_got_last", "room pickup flags (inclusive last)"),
    ("meta_content_src", "meta_content_src", "tail_size", "runtime room meta"),
    ("udg charset RAM", 0x1800, 512, "character RAM @ udg_base (runtime)"),
    ("screen_base", "screen_base", 408, "24x17 playfield"),
    ("color_base", "color_base", 408, "active colour RAM"),
    ("map_base", "map_base", 408, "ghost colour / collision map"),
    ("ROPE_SEGMENT_Y", 0x33C, 32, "rope segment Y (rope rooms)"),
    ("INGAME_TUNE_SEQ", 0x97C0, 64, "optional tune index spare"),
]

TAPE_UDG_HOLE = (0x1800, 0x19FF)

LABEL_RE = re.compile(r"al C:([0-9a-f]+) \.(.+)", re.I)


@dataclass(frozen=True)
class Region:
    name: str
    start: int
    end: int  # inclusive
    kind: str  # prg | ram

    @property
    def size(self) -> int:
        return self.end - self.start + 1

    def overlaps(self, other: Region) -> bool:
        return self.start <= other.end and other.start <= self.end

    def overlap_bytes(self, other: Region) -> int:
        if not self.overlaps(other):
            return 0
        lo = max(self.start, other.start)
        hi = min(self.end, other.end)
        return hi - lo + 1


def parse_labels(path: Path) -> dict[str, int]:
    labels: dict[str, int] = {}
    for line in path.read_text().splitlines():
        m = LABEL_RE.match(line)
        if m:
            labels[m.group(2)] = int(m.group(1), 16)
    return labels


def resolve(labels: dict[str, int], key: str | int) -> int:
    if isinstance(key, int):
        return key
    if key not in labels:
        raise KeyError(key)
    return labels[key]


def region_from_exclusive_end(name: str, start: int, end_exclusive: int, *, kind: str) -> Region | None:
    if end_exclusive <= start:
        return None
    return Region(name, start, end_exclusive - 1, kind)


def build_regions(labels: dict[str, int]) -> tuple[list[Region], list[str]]:
    warnings: list[str] = []
    regions: list[Region] = []

    for seg_name, start_sym, end_sym in TAPE_PRG_SEGMENTS:
        if start_sym not in labels:
            warnings.append(f"missing label .{start_sym} ({seg_name})")
            continue
        if end_sym not in labels:
            warnings.append(f"missing label .{end_sym} ({seg_name})")
            continue
        r = region_from_exclusive_end(
            seg_name, labels[start_sym], labels[end_sym], kind="prg"
        )
        if r:
            regions.append(r)

    for blob_name, start_sym, end_sym in TAPE_PRG_BLOBS:
        if start_sym not in labels or end_sym not in labels:
            warnings.append(f"missing blob labels for {blob_name}")
            continue
        r = region_from_exclusive_end(
            blob_name, labels[start_sym], labels[end_sym], kind="prg"
        )
        if r:
            regions.append(r)

    for ram_name, start_key, size_key, _note in TAPE_RUNTIME_RAM:
        try:
            start = resolve(labels, start_key)
            if isinstance(size_key, str) and size_key.endswith("_last"):
                end = resolve(labels, size_key)
                size = end - start + 1
            else:
                size = resolve(labels, size_key)
        except KeyError as exc:
            warnings.append(f"missing label .{exc.args[0]} ({ram_name})")
            continue
        regions.append(Region(ram_name, start, start + size - 1, "ram"))

    meta = labels.get("meta_content_src")
    tail = labels.get("tail_size", 104)
    gdb = labels.get("guardian_data_base")
    gbytes = labels.get("guardian_data_bytes", 60)
    if meta is not None and gdb is not None:
        meta_end = meta + tail - 1
        gdb_end = gdb + gbytes - 1
        if gdb < meta or gdb_end > meta_end:
            warnings.append(
                f"guardian_data_base ${gdb:04X}-${gdb_end:04X} outside "
                f"meta_content_src ${meta:04X}-${meta_end:04X}"
            )

    return regions, warnings


def check_prg_segment_adjacency(segs: list[Region], labels: dict[str, int]) -> list[str]:
    errors: list[str] = []
    ordered = sorted(segs, key=lambda r: r.start)
    for i in range(len(ordered) - 1):
        a, b = ordered[i], ordered[i + 1]
        if a.end >= b.start:
            nbytes = a.overlap_bytes(b)
            errors.append(
                f"PRG SEGMENT OVERLAP ({nbytes} B @ ${max(a.start, b.start):04X}): "
                f"{a.name} (${a.start:04X}-${a.end:04X}) vs "
                f"{b.name} (${b.start:04X}-${b.end:04X})"
            )
        elif b.start - a.end - 1 > 0 and {a.name, b.name} != {
            "low bank code",
            "high bank code",
        }:
            gap = b.start - a.end - 1
            print(
                f"  gap {gap} B between {a.name} and {b.name} "
                f"(${a.end + 1:04X}-${b.start - 1:04X})"
            )

    from memmap import print_tape_free_memory

    print_tape_free_memory(labels)
    return errors


def check_hole_vs_prg(segs: list[Region]) -> list[str]:
    hole_lo, hole_hi = TAPE_UDG_HOLE
    errors: list[str] = []
    for r in segs:
        if r.name not in {"low bank code", "high bank code"}:
            continue
        lo = max(r.start, hole_lo)
        hi = min(r.end, hole_hi)
        if lo <= hi:
            errors.append(
                f"PRG CODE IN UDG HOLE ({hi - lo + 1} B @ ${lo:04X}): "
                f"{r.name} (${r.start:04X}-${r.end:04X}) vs "
                f"${hole_lo:04X}-${hole_hi:04X}"
            )
    return errors


def check_blob_containment(parent: Region, blob: Region) -> str | None:
    if parent.start <= blob.start and parent.end >= blob.end:
        return None
    if not parent.overlaps(blob):
        return f"{blob.name} outside {parent.name}"
    if blob.start < parent.start or blob.end > parent.end:
        return (
            f"{blob.name} (${blob.start:04X}-${blob.end:04X}) "
            f"extends outside {parent.name} (${parent.start:04X}-${parent.end:04X})"
        )
    return None


def print_map(regions: list[Region]) -> None:
    print("Layout regions (from sorted labels):")
    print(f"{'Region':32} {'Start':>6} {'End':>6} {'Size':>6}  Kind")
    print("-" * 60)
    for r in sorted(regions, key=lambda x: (x.start, x.name)):
        print(f"{r.name:32} ${r.start:04X} ${r.end:04X} {r.size:6}  {r.kind}")


def main() -> int:
    lbl_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "jsws.lbl"
    if not lbl_path.is_file():
        print(f"lbloverlap: missing {lbl_path}", file=sys.stderr)
        return 1

    labels = parse_labels(lbl_path)
    regions, warnings = build_regions(labels)

    print(f"Label overlap check: {lbl_path.name} ({len(labels)} symbols)")
    print_map(regions)

    for w in warnings:
        print(f"  warning: {w}")

    seg_names = {s[0] for s in TAPE_PRG_SEGMENTS}
    blob_names = {b[0] for b in TAPE_PRG_BLOBS}
    prg_segs = [r for r in regions if r.name in seg_names]
    prg_blobs = [r for r in regions if r.name in blob_names]
    ram = [r for r in regions if r.kind == "ram"]

    errors: list[str] = []
    errors.extend(check_prg_segment_adjacency(prg_segs, labels))
    errors.extend(check_hole_vs_prg(prg_segs))

    sprites = next((r for r in prg_segs if r.name == "catalogue sprites"), None)
    for blob in prg_blobs:
        parent = next(
            (s for s in prg_segs if s.start <= blob.start and s.end >= blob.start),
            None,
        )
        if parent is None:
            errors.append(f"{blob.name} (${blob.start:04X}) not inside any PRG segment")
            continue
        msg = check_blob_containment(parent, blob)
        if msg:
            errors.append(msg)

    for blob in prg_blobs:
        for other in prg_blobs:
            if blob.name >= other.name:
                continue
            nbytes = blob.overlap_bytes(other)
            if nbytes > 0:
                errors.append(
                    f"PRG BLOB OVERLAP ({nbytes} B @ ${max(blob.start, other.start):04X}): "
                    f"{blob.name} vs {other.name}"
                )

    for p in prg_segs:
        for m in ram:
            nbytes = p.overlap_bytes(m)
            if nbytes <= 0:
                continue
            # Loaded PRG occupies its own address range; runtime RAM is separate.
            # udg charset RAM ($1800) is a hole in the PRG layout (skipped by *= high_bank).
            if m.name == "udg charset RAM":
                continue
            errors.append(
                f"PRG vs RAM ({nbytes} B @ ${max(p.start, m.start):04X}): "
                f"{p.name} vs {m.name}"
            )

    for i, a in enumerate(ram):
        for b in ram[i + 1 :]:
            nbytes = a.overlap_bytes(b)
            if nbytes > 0:
                errors.append(
                    f"RAM vs RAM ({nbytes} B @ ${max(a.start, b.start):04X}): "
                    f"{a.name} vs {b.name}"
                )

    if errors:
        print()
        print(f"*** {len(errors)} overlap(s) ***")
        for e in errors:
            print(f"  {e}")
        return 1

    print()
    print("Label overlap check: OK — no code/data/RAM overlaps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
