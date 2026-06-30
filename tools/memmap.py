#!/usr/bin/env python3
"""Print JSW PRG code memory map from jsw.lbl."""

import re
import sys
from pathlib import Path

MODULES = [
    ("header/boot", ["cold_start", "warm_start", "basic_end"]),
    ("gameloop", ["start_game", "start_map", "main_loop"]),
    ("map", ["ResetGame", "DrawMap", "CheckRoomEdge"]),
    ("loader", ["LoadRoom", "room_name", "ParseRoomMeta"]),
    ("ramp", ["calculate_ramp_y", "do_walking_ramp_check", "do_falling_ramp_check"]),
    ("willy_collide", ["try_touch", "Collide", "hit_above"]),
    ("willy_draw", ["DrawPlayerEntry", "DrawPlayer"]),
    ("util", ["ConvertXYToScreenAddr", "ConvertTileXYToScreenAddr", "UpdateMoveCounters"]),
    ("input", ["GetPlayerInput", "ScanKeyRow"]),
    ("guardians", ["CopyDownGuardianData", "MoveGuardians", "EraseGuardians"]),
    ("tape_runtime", ["FlickerItem", "AnimateConveyors", "DoBelt"]),
    ("warm boot", ["WarmStart", "init24_val"]),
]

DISK_RAM = [
    ("ROPE_SEGMENT_Y", 0x33C, 32, "rope segment Y (cassette buffer)"),
    ("rope_xadd", 0x35C, 54, "copied at WarmStart (cassette buffer)"),
    ("FlickerItem", 0x1A05, 16, "baked per room; jsr FlickerItem"),
    ("AnimateConveyors", 0x1A05 + 16, 19, "baked per room; jsr AnimateConveyors"),
    ("DoBelt", 0x1A05 + 35, 26, "baked per room; jsr DoBelt"),
    ("tile_color_src", 0x1A42, 6, "tile type colours 0-5"),
    ("guardian_sprites_base", 0x1A48, 288, "from room PRG (9 frames)"),
    ("player_bmp", 0x1B68, 256, "from room PRG"),
    ("HUD UDGs chr 13-14", 0x1C68, 16, "men + items icons"),
    ("tile UDGs chr 15-21", 0x1C78, 56, "chr 15=item, 16-21=tiles"),
    ("guardian_udgs chr 22+", 0x1CB0, 288, "runtime UDG workspace"),
    ("player_udg chr 58+", 0x1DD0, 48, "runtime (6 chars)"),
    ("screen_base", 0x1E00, 408, "24x17 tilemap from room PRG"),
    ("tail meta/gdata", 0x1F98, 104, "meta_content_src @ $1F98"),
]

TAPE_RAM = [
    ("screen_base", 0x1000, 408, "24x17 playfield"),
    ("color_base", 0x9400, 408, "active colour (paired with $1000 screen)"),
    ("map_base", 0x9600, 408, "ghost colour RAM collision map"),
    ("udg_base", 0x1800, 512, "character RAM via 36869 OR $0E (64 slots)"),
    ("meta_content_src", 0x13E, 104, "runtime room meta; guardian AoS at +39 ($165)"),
    ("ROPE_SEGMENT_Y", 0x33C, 32, "rope segment Y (cassette buffer)"),
    ("INGAME_TUNE_SEQ", 0x97C0, 64, "tune index table in map colour spare"),
]

DISK_ROOM_BASE = 0x1A05
TAPE_LOAD_BASE = 0x1201
TAPE_UDG_BASE = 0x1800
TAPE_UDG_END = 0x19FF
TAPE_LOW_BANK_END = 0x17FF
TAPE_HIGH_BANK = 0x1A00
TAPE_MEM_TOP = 0x6000

# PRG segments: (name, start_label, end_label). Order must match link layout.
TAPE_PRG_SEGMENTS = [
    ("low bank code", "cold_start", "low_bank_end"),
    ("high bank code", "high_bank", "high_bank_code_end"),
    ("catalogue rooms", "CatalogueImage", "catalogue_rooms_end"),
    ("catalogue tile UDGs", "udg_pool_counts", "catalogue_udgs_end"),
    ("catalogue sprites", "sprite_set_metadata", "catalogue_sprites_end"),
]


def parse_labels(lbl: Path) -> dict[str, int]:
    labels = {}
    for line in lbl.read_text().splitlines():
        m = re.match(r"al C:([0-9a-f]+) \.(.+)", line, re.I)
        if m:
            labels[m.group(2)] = int(m.group(1), 16)
    return labels


def print_tape_free_memory(labels: dict[str, int], *, prg_end: int | None = None) -> None:
    """Report slack before udg_base, slack before mem_top, and their sum."""
    udg = labels.get("udg_base", TAPE_UDG_BASE)
    low_end = labels.get("low_bank_end")
    if prg_end is None:
        prg_end = labels.get("prg_end")

    if low_end is not None and low_end < udg:
        gap_low = udg - low_end
        print(
            f"  gap {gap_low} B between low bank code and udg_base "
            f"(${low_end:04X}-${udg - 1:04X})"
        )
    elif low_end is not None:
        print(
            f"  *** low bank code extends past udg_base "
            f"(low_bank_end ${low_end:04X}, udg_base ${udg:04X})"
        )
        gap_low = 0
    else:
        gap_low = 0

    if prg_end is not None and prg_end < TAPE_MEM_TOP:
        gap_high = TAPE_MEM_TOP - prg_end
        print(
            f"  gap {gap_high} B between high bank code and mem_top "
            f"(${prg_end:04X}-${TAPE_MEM_TOP - 1:04X})"
        )
    elif prg_end is not None and prg_end >= TAPE_MEM_TOP:
        print(
            f"  *** PRG end ${prg_end:04X} at or past mem_top ${TAPE_MEM_TOP:04X}"
        )
        gap_high = 0
    else:
        gap_high = 0

    if gap_low or gap_high:
        print(f"  free memory: {gap_low + gap_high} B")


def check_tape_layout(labels: dict[str, int], *, end: int) -> int:
    """Return error count; print segment map and overlap report."""
    errors = 0
    segments: list[tuple[str, int, int]] = []

    print("PRG layout (from labels):")
    print(f"{'Segment':28} {'Start':>6} {'End':>6} {'Size':>6}")
    print("-" * 52)

    for name, start_sym, end_sym in TAPE_PRG_SEGMENTS:
        if start_sym not in labels:
            print(f"  *** missing label .{start_sym}")
            errors += 1
            continue
        if end_sym not in labels:
            print(f"  *** missing label .{end_sym}")
            errors += 1
            continue
        start = labels[start_sym]
        seg_end = labels[end_sym] - 1
        if seg_end < start:
            print(f"  *** {name}: .{end_sym} (${labels[end_sym]:04X}) before .{start_sym} (${start:04X})")
            errors += 1
            continue
        size = seg_end - start + 1
        segments.append((name, start, seg_end))
        print(f"{name:28} ${start:04X} ${seg_end:04X} {size:6}")

    prg_end = labels.get("prg_end")
    if prg_end is None:
        print("  *** missing label .prg_end")
        errors += 1
    elif prg_end != end + 1:
        print(
            f"  *** prg_end ${prg_end:04X} != PRG byte end ${end + 1:04X}"
        )
        errors += 1
    elif segments and segments[-1][2] + 1 != prg_end:
        print(
            f"  *** catalogue_sprites_end ${segments[-1][2] + 1:04X} != prg_end ${prg_end:04X}"
        )
        errors += 1
    else:
        print(f"{'prg_end':28} ${prg_end:04X} ${prg_end - 1:04X} {1:6}")

    print()
    for i in range(len(segments) - 1):
        _n1, _s1, e1 = segments[i]
        n2, s2, _e2 = segments[i + 1]
        if e1 >= s2:
            overlap = e1 - s2 + 1
            print(
                f"  *** OVERLAP: {segments[i][0]} ends ${e1:04X}, "
                f"{n2} starts ${s2:04X} ({overlap} bytes)"
            )
            errors += 1
        elif s2 - e1 - 1 > 0 and {
            segments[i][0],
            n2,
        } != {"low bank code", "high bank code"}:
            gap = s2 - e1 - 1
            print(f"  gap {gap} B between {segments[i][0]} and {n2} (${e1 + 1:04X}-${s2 - 1:04X})")

    print_tape_free_memory(labels, prg_end=end + 1)

    low_end = labels.get("low_bank_end")
    if low_end is not None and low_end > TAPE_LOW_BANK_END:
        print(
            f"  *** low bank extends to ${low_end:04X} (limit ${TAPE_LOW_BANK_END:04X})"
        )
        errors += 1

    for name, start, seg_end in segments:
        if start <= TAPE_UDG_END and seg_end >= TAPE_UDG_BASE:
            if name != "low bank code":
                print(f"  *** {name} spans UDG charset hole (${TAPE_UDG_BASE:04X}-${TAPE_UDG_END:04X})")
                errors += 1

    if end >= TAPE_UDG_BASE and labels.get("low_bank_end", 0) <= TAPE_LOW_BANK_END:
        over = min(end, TAPE_UDG_END) - max(TAPE_LOAD_BASE, TAPE_UDG_BASE) + 1
        if over > 0 and not any(
            n == "low bank code" and s <= TAPE_UDG_END and e >= TAPE_UDG_BASE
            for n, s, e in segments
        ):
            print(
                f"  note: PRG file spans UDG hole (${TAPE_UDG_BASE:04X}-${TAPE_UDG_END:04X}) "
                f"via low bank — expected until Phase 2 split"
            )

    prg_total = end - TAPE_LOAD_BASE + 1
    cat = labels.get("CatalogueImage")
    print()
    print(f"  PRG image ${TAPE_LOAD_BASE:04X}-${end:04X} ({prg_total} bytes)")
    if cat is not None:
        cat_size = end - cat + 1
        print(
            f"  embedded catalogue ${cat:04X}-${end:04X} ({cat_size} bytes, read in place)"
        )

    if errors:
        print(f"\nLayout check: {errors} error(s)")
    else:
        print("\nLayout check: OK — no segment overlaps")
    return errors


def prg_slack(lbl: Path, room_base: int) -> int:
    labels = parse_labels(lbl)
    prg_end = labels.get("prg_end", max(labels.values()))
    return room_base - prg_end


def prg_bytes_end(lbl: Path, load_base: int) -> int:
    prg = lbl.with_name("jsw.prg")
    if not prg.is_file():
        labels = parse_labels(lbl)
        markers = [
            labels[s]
            for s in (
                "reloc_e_src",
                "ingame_tune_idx_rom_end",
                "WarmStart",
                "prg_end",
            )
            if s in labels
        ]
        if "reloc_e_src" in labels and "reloc_e_size" in labels:
            markers.append(labels["reloc_e_src"] + labels["reloc_e_size"])
        return max(markers) if markers else load_base
    size = len(prg.read_bytes())
    if size < 2:
        return load_base
    return load_base + size - 3


def main():
    args = sys.argv[1:]
    tape_mode = "--tape" in args
    check_overlap = "--overlap" in args or tape_mode
    args = [a for a in args if a not in ("--tape", "--overlap")]

    if args and args[0] == "--slack":
        lbl = Path(args[1] if len(args) > 1 else "jsw.lbl")
        if tape_mode:
            labels = parse_labels(lbl)
            end = prg_bytes_end(lbl, TAPE_LOAD_BASE)
            total = end - TAPE_LOAD_BASE + 1
            print(f"PRG image ${TAPE_LOAD_BASE:04X}-${end:04X} ({total} bytes)")
            cat = labels.get("CatalogueImage")
            if cat is not None:
                print(f"  catalogue embedded ${cat:04X}-${end:04X} ({end - cat + 1} bytes)")
            return
        slack = prg_slack(lbl, DISK_ROOM_BASE)
        if slack < 0:
            over = -slack
            print(
                f"PRG extends {over} (0x{over:02X}) bytes past "
                f"${DISK_ROOM_BASE:04X} image_base room load base"
            )
            sys.exit(1)
        print(
            f"PRG has {slack} (0x{slack:02X}) bytes free before "
            f"${DISK_ROOM_BASE:04X} image_base room load base"
        )
        return

    lbl = Path(args[0] if args else "jsw.lbl")
    labels = parse_labels(lbl)

    bounds = []
    for name, syms in MODULES:
        for sym in syms:
            if sym in labels:
                bounds.append((labels[sym], name, sym))
                break

    bounds.sort()
    prg_end = labels.get("prg_end", max(labels.values()))

    if tape_mode:
        load_base = TAPE_LOAD_BASE
        end = prg_bytes_end(lbl, load_base)
        total = end - load_base + 1
        udg_overlap = max(0, min(end, TAPE_UDG_END) - max(load_base, TAPE_UDG_BASE) + 1)

        print(f"Tape PRG: ${load_base:04X}-${end:04X}  ({total} bytes)")
        if udg_overlap:
            print(
                f"  *** {udg_overlap} bytes overlap UDG charset RAM "
                f"(${TAPE_UDG_BASE:04X}-${TAPE_UDG_END:04X}) — split code in Phase 2 ***"
            )
        cat = labels.get("CatalogueImage")
        if cat is not None:
            print(
                f"  catalogue embedded ${cat:04X}-${end:04X} ({end - cat + 1} bytes)"
            )
        bounds = [(s, n, sym) for s, n, sym in bounds if s >= load_base]
        bounds.sort()
        print()
        print(f"{'Segment':32} {'Start':>6} {'End':>6} {'Size':>6}  Notes")
        print("-" * 72)

        for i, (start, name, sym) in enumerate(bounds):
            seg_end = bounds[i + 1][0] - 1 if i + 1 < len(bounds) else end
            size = seg_end - start + 1
            notes = f"; {sym}"
            if start <= TAPE_UDG_END and seg_end >= TAPE_UDG_BASE:
                notes += "  [spans UDG RAM]"
            print(f"{name:32} ${start:04X} ${seg_end:04X} {size:5}  {notes}")

        print()
        print("Runtime RAM (tape layout):")
        for name, addr, size, note in TAPE_RAM:
            if isinstance(size, int):
                size_s = f"{size:4} B"
            else:
                size_s = f"~{size}"
            print(f"  ${addr:04X}  {name:28} {size_s:>6}  ({note})")
        if check_overlap:
            print()
            if check_tape_layout(labels, end=end):
                sys.exit(1)
        return

    load_base = 0x1000
    room_base = DISK_ROOM_BASE
    room_size = 0x5FB
    total = prg_end - load_base
    overlap = prg_end - room_base

    print(f"PRG load: ${load_base:04X}-${prg_end - 1:04X}  ({total} bytes)")
    if overlap > 0:
        print(f"  *** {overlap} bytes (${room_base:04X}+) overlap room load area ***")
    print(f"Room LOAD overwrites: ${room_base:04X}-${room_base + room_size - 1:04X}  ({room_size} bytes)")
    print()
    print(f"{'Segment':32} {'Start':>6} {'End':>6} {'Size':>6}  Notes")
    print("-" * 72)

    for i, (start, name, sym) in enumerate(bounds):
        end = bounds[i + 1][0] - 1 if i + 1 < len(bounds) else prg_end - 1
        size = end - start + 1
        notes = f"; {sym}"
        if start >= room_base:
            notes += "  [entirely in room zone]"
        elif end >= room_base:
            notes += f"  [{end - room_base + 1} B past ${room_base:04X}]"
        print(f"{name:32} ${start:04X} ${end:04X} {size:5}  {notes}")

    print()
    print("Runtime RAM (absolute, during play):")
    for name, addr, size, note in DISK_RAM:
        print(f"  ${addr:04X}  {name:28} {size:4} B  ({note})")


if __name__ == "__main__":
    main()
