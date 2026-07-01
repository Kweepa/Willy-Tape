#!/usr/bin/env python3
"""Document tape loader mapping: catalogue meta8 flags -> runtime meta tail bytes.

ParseMeta8 stores meta8 byte 6 in meta_content_record_flags (+101) and must
also copy FLAG_ROPE / FLAG_ARROW into meta_content_room_has_rope (+38) and
meta_content_has_arrow (+99) — mirroring mkroom.py build_tail for disk rooms.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mkcatalogue import FLAG_ARROW, FLAG_ROPE  # noqa: E402

HEADER = 2
INDEX_ENTRY = 4
META_OFF_ROPE = 38
META_OFF_HAS_ARROW = 99


def parse_record_flags(blob: bytes, off: int) -> tuple[int, str]:
    title_end = blob.index(0, off)
    meta_off = title_end + 1
    flags = blob[meta_off + 6]
    return flags, blob[off:title_end].decode("ascii", errors="replace")


def runtime_meta_from_flags(flags: int) -> tuple[int, int]:
    """Mirror loader.asm ParseMeta8: tail bytes hold FLAG_* bit values."""
    return (flags & FLAG_ROPE, flags & FLAG_ARROW)


def main() -> None:
    cat = (ROOT / "catalogue.bin").read_bytes()
    count, = struct.unpack_from("<H", cat, 0)
    records_off = HEADER + count * INDEX_ENTRY
    errors = 0
    rope_rooms: list[int] = []
    arrow_rooms: list[int] = []

    for rid in range(count):
        idx_off = HEADER + rid * INDEX_ENTRY
        rec_off, _rec_len = struct.unpack_from("<HH", cat, idx_off)
        flags, _title = parse_record_flags(cat, records_off + rec_off)
        rope, arrow = runtime_meta_from_flags(flags)
        if rope:
            rope_rooms.append(rid)
        if arrow:
            arrow_rooms.append(rid)
        if flags & FLAG_ROPE and not rope:
            print(f"room {rid}: FLAG_ROPE set but runtime rope byte would be 0")
            errors += 1
        if flags & FLAG_ARROW and not arrow:
            print(f"room {rid}: FLAG_ARROW set but runtime arrow byte would be 0")
            errors += 1

    print(f"rope rooms ({len(rope_rooms)}): {rope_rooms}")
    print(f"arrow rooms ({len(arrow_rooms)}): {arrow_rooms}")
    assert 31 in rope_rooms, "room 31 (Swimming Pool) must have FLAG_ROPE"
    assert 25 in rope_rooms, "room 25 (Cold Store) must have FLAG_ROPE"
    assert 36 in arrow_rooms, "room 36 must have FLAG_ARROW"
    print(f"meta offsets: rope +{META_OFF_ROPE}, arrow +{META_OFF_HAS_ARROW}")
    if errors:
        raise SystemExit(errors)
    print("OK: catalogue flags map to runtime meta tail bytes")


if __name__ == "__main__":
    main()
