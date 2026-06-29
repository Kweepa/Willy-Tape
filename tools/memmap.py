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
    ("util", ["ConvertXYToScreenAddr", "UpdateMoveCounters"]),
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
    ("udg_base", 0x1800, 1024, "character RAM via 36869 OR $0E"),
    ("meta_content_src", 0x5800, 104, "runtime room meta (was per-room PRG tail)"),
    ("guardian_sprites_base", 0x5E00, 896, "per-room resident gfx (Phase 4)"),
    ("guardian_pool", 0x2000, 4096, "deduped frames (Phase 3 load)"),
    ("catalogue_base", 0x3000, 0x1C00, "compressed rooms + globals (Phase 3)"),
    ("ROPE_SEGMENT_Y", 0x33C, 32, "rope segment Y (cassette buffer)"),
    ("INGAME_TUNE_SEQ", 0x97C0, 64, "tune index table in map colour spare"),
]

DISK_ROOM_BASE = 0x1A05
TAPE_LOAD_BASE = 0x1201
TAPE_UDG_BASE = 0x1800
TAPE_UDG_END = 0x1BFF
TAPE_GUARDIAN_POOL = 0x2000


def parse_labels(lbl: Path) -> dict[str, int]:
    labels = {}
    for line in lbl.read_text().splitlines():
        m = re.match(r"al C:([0-9a-f]+) \.(.+)", line, re.I)
        if m:
            labels[m.group(2)] = int(m.group(1), 16)
    return labels


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
    args = [a for a in args if a != "--tape"]

    if args and args[0] == "--slack":
        lbl = Path(args[1] if len(args) > 1 else "jsw.lbl")
        if tape_mode:
            labels = parse_labels(lbl)
            end = prg_bytes_end(lbl, TAPE_LOAD_BASE)
            slack = TAPE_GUARDIAN_POOL - end
            if slack < 0:
                over = -slack
                print(
                    f"PRG extends {over} (0x{over:02X}) bytes past "
                    f"${TAPE_GUARDIAN_POOL:04X} guardian_pool base"
                )
                sys.exit(1)
            print(
                f"PRG code ends ${end:04X}; "
                f"{slack} (0x{slack:02X}) bytes free before guardian_pool"
            )
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
        pool_slack = TAPE_GUARDIAN_POOL - end
        if pool_slack < 0:
            print(f"  *** {-pool_slack} bytes past ${TAPE_GUARDIAN_POOL:04X} guardian_pool ***")
        else:
            print(f"  {pool_slack} bytes free before guardian_pool @ ${TAPE_GUARDIAN_POOL:04X}")
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
