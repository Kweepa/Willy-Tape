"""Proportional font glyph indices — full Miner set + compact bake subset."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SUBSET_JSON = ROOT / "bake" / "font_subset.json"

# chartofontchar from Miner-main/font.asm — index (ASCII - 32)
CHARTOFONTCHAR = bytes(
    [
        62, 0, 0, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0, 65, 66, 0,
        52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 0, 0, 0, 0, 0, 0,
        0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 0, 0, 0, 0, 0,
        0, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 0, 0, 0, 0, 63,
    ]
)

FULL_GLYPH_COUNT = 67

# Glyph index in full font -> representative character
FULL_GLYPH_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " #'-."
)


def parse_fontchars_asm(path: Path) -> list[list[int]]:
    rows: list[list[int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if "!byte" not in line:
            continue
        parts = [int(x.strip(), 0) for x in line.split("!byte", 1)[1].split(",") if x.strip()]
        if len(parts) == 8:
            rows.append(parts)
    return rows


def ascii_to_full_glyph(ch: str) -> int:
    """Map one ASCII character to full-font glyph index 0-66."""
    code = ord(ch)
    if code < 32 or code > 127:
        return 62
    g = CHARTOFONTCHAR[code - 32]
    if g == 0 and code not in (64, 65):
        return 62
    return g


def titles_glyph_set(rooms_dir: Path) -> set[int]:
    used: set[int] = set()
    for path in sorted(rooms_dir.glob("room*.txt")):
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"@title\s+(.+)", text, re.I)
        if not match:
            continue
        for ch in match.group(1).strip()[:18]:
            used.add(ascii_to_full_glyph(ch))
    return used


def _load_subset() -> dict | None:
    if not SUBSET_JSON.is_file():
        return None
    return json.loads(SUBSET_JSON.read_text(encoding="utf-8"))


def full_to_compact_glyph(full_index: int) -> int:
    subset = _load_subset()
    if subset is None:
        return full_index
    mapped = subset["full_to_compact"].get(str(full_index))
    if mapped is None:
        raise KeyError(f"full glyph {full_index} ({FULL_GLYPH_CHARS[full_index]!r}) not in font subset")
    return int(mapped)


def compact_glyph_label(compact_index: int) -> str:
    subset = _load_subset()
    if subset is None:
        if 0 <= compact_index < len(FULL_GLYPH_CHARS):
            return FULL_GLYPH_CHARS[compact_index]
        return "?"
    labels = subset["compact_labels"]
    if 0 <= compact_index < len(labels):
        return labels[compact_index]
    return "?"


def pack_title_glyphs(text: str) -> bytes:
    """1-based compact glyph bytes, null-terminated (0 = end)."""
    out: list[int] = []
    for ch in text:
        compact = full_to_compact_glyph(ascii_to_full_glyph(ch))
        out.append(compact + 1)
    out.append(0)
    return bytes(out)


def decode_title_glyphs(data: bytes) -> str:
    """Decode 1-based compact title bytes to a display string."""
    out: list[str] = []
    for b in data:
        if b == 0:
            break
        out.append(compact_glyph_label(b - 1))
    return "".join(out)


def digit_compact_index(digit: int) -> int:
    """Compact glyph index 0-57 for ASCII digit 0-9 (for future HUD counts)."""
    subset = _load_subset()
    if subset is None:
        return 52 + digit
    return int(subset["digit_compact"][str(digit)])
