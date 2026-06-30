"""Proportional font glyph indices (Miner chartofontchar / fontchars order)."""

from __future__ import annotations

# chartofontchar from Miner-main/font.asm — index (ASCII - 32)
CHARTOFONTCHAR = bytes(
    [
        62, 0, 0, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0, 65, 66, 0,
        52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 0, 0, 0, 0, 0, 0,
        0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 0, 0, 0, 0, 0,
        0, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 0, 0, 0, 0, 63,
    ]
)

# Glyph index -> representative character (for comments / test decode)
GLYPH_CHARS = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789"
    " #'-."
)


def ascii_to_font_glyph(ch: str) -> int:
    """Map one ASCII character to font glyph index 0-66."""
    code = ord(ch)
    if code < 32 or code > 127:
        return 62
    g = CHARTOFONTCHAR[code - 32]
    if g == 0 and code not in (64, 65):
        return 62
    return g


def pack_title_glyphs(text: str) -> bytes:
    """1-based stored bytes, null-terminated (0 = end)."""
    return bytes(ascii_to_font_glyph(c) + 1 for c in text) + b"\x00"


def decode_title_glyphs(data: bytes) -> str:
    """Decode 1-based glyph title bytes to a display string."""
    out: list[str] = []
    for b in data:
        if b == 0:
            break
        g = b - 1
        if 0 <= g < len(GLYPH_CHARS):
            out.append(GLYPH_CHARS[g])
        else:
            out.append("?")
    return "".join(out)
