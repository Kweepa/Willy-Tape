"""Guardian sprite type map and helpers (SkoolKit page/slot layout)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

GFX_PAGE_BASE = 171

SKOOLKIT_TYPES: dict[str, tuple[int, int, int]] = {
    "chip": (171, 0, 3),
    "elf": (171, 4, 7),
    "scroll": (172, 0, 3),
    "spiral": (172, 4, 7),
    "shears": (173, 0, 3),
    "razor": (173, 4, 7),
    "wirecutter": (174, 0, 3),
    "domebot": (174, 4, 7),
    "multitool": (175, 0, 3),
    "egg": (175, 4, 7),
    "pacbody": (176, 0, 1),
    "pachead": (176, 2, 3),
    "esmerelda": (176, 4, 5),
    "chandelier": (176, 6, 7),
    "flag": (178, 0, 3),
    "moon": (178, 4, 7),
    "monk": (180, 0, 7),
    "saw": (181, 0, 7),
    "bat": (182, 0, 7),
    "chef": (183, 0, 1),
    "jelly": (183, 2, 3),
    "tambourine": (183, 4, 7),
    "rabbit": (184, 0, 7),
    "globes": (185, 0, 3),
    "ufo": (185, 4, 7),
    "pinhead": (186, 0, 3),
    "cone": (187, 0, 3),
    "flower": (187, 4, 7),
    "bird": (188, 0, 7),
    "penguin": (189, 0, 7),
    "hootbot": (190, 0, 3),
    "bubble": (190, 4, 7),
    "ewok": (191, 0, 3),
    "guard": (191, 4, 5),
    "clive": (191, 6, 7),
}

SKOOLKIT_URL = "https://skoolkit.ca/disassemblies/jet_set_willy/asm/43776.html"

CUSTOM_COUNTS: dict[str, int] = {
    "demona": 1,
    "demonb": 1,
    "demonc": 2,
    "maria": 4,
    "foot": 1,
    "toilet": 4,
    "barrel": 2,
}


@dataclass(frozen=True)
class SpriteMeta:
    name: str
    frame_count: int
    bidir: bool


def frame_count_for(name: str) -> int:
    key = name.lower()
    if key in SKOOLKIT_TYPES:
        _page, lo, hi = SKOOLKIT_TYPES[key]
        return hi - lo + 1
    return CUSTOM_COUNTS.get(key, 4)


def sprite_meta(name: str, *, axis: int) -> SpriteMeta:
    n = frame_count_for(name)
    bidir = axis == 0 and n == 8
    return SpriteMeta(name.lower(), n, bidir)


def interleave_frame(column_major: bytes) -> bytes:
    if len(column_major) != 32:
        raise ValueError(f"frame must be 32 bytes, got {len(column_major)}")
    out = bytearray(32)
    for row in range(16):
        out[row * 2] = column_major[row]
        out[row * 2 + 1] = column_major[row + 16]
    return bytes(out)


def deinterleave_frame(interleaved: bytes) -> bytes:
    if len(interleaved) != 32:
        raise ValueError(f"frame must be 32 bytes, got {len(interleaved)}")
    out = bytearray(32)
    for row in range(16):
        out[row] = interleaved[row * 2]
        out[row + 16] = interleaved[row * 2 + 1]
    return bytes(out)


def parse_byte_list(text: str) -> list[int]:
    return [int(p.strip()) & 0xFF for p in text.split(",") if p.strip()]


def format_byte_lines(data: bytes, *, indent: str = "    ") -> str:
    parts = [f"${b:02x}" for b in data]
    lines: list[str] = []
    for i in range(0, len(parts), 16):
        chunk = ", ".join(parts[i : i + 16])
        lines.append(f"{indent}!byte {chunk}")
    return "\n".join(lines)


def load_gfx() -> bytes:
    from jswimport import load_guardian_gfx  # noqa: WPS433

    return load_guardian_gfx()


def skoolkit_frames(name: str, gfx: bytes) -> list[bytes]:
    key = name.lower()
    if key not in SKOOLKIT_TYPES:
        raise KeyError(name)
    page, lo, hi = SKOOLKIT_TYPES[key]
    frames: list[bytes] = []
    for slot in range(lo, hi + 1):
        off = (page - GFX_PAGE_BASE) * 256 + slot * 32
        raw = gfx[off : off + 32]
        if len(raw) < 32:
            raw = raw.ljust(32, b"\x00")
        frames.append(raw)
    return frames


def read_sprite_txt(path: Path) -> list[bytes]:
    """Load 32-byte frames from a willy.txt-style comma-separated byte file."""
    if not path.is_file():
        raise FileNotFoundError(path)
    pending: list[int] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        pending.extend(parse_byte_list(line))
    frames: list[bytes] = []
    while len(pending) >= 32:
        frames.append(bytes(pending[:32]))
        pending = pending[32:]
    if pending:
        raise ValueError(f"{path}: {len(pending)} trailing bytes (not a multiple of 32)")
    return frames


def read_willy_txt(path: Path) -> list[bytes]:
    """Load willy.txt (Skool interleaved L,R pairs) as column-major frames."""
    return [deinterleave_frame(fr) for fr in read_sprite_txt(path)]


def read_demon_txt(path: Path) -> dict[str, list[bytes]]:
    """Split demon.txt into demonA (1), demonB (1), demonC (2) frames."""
    frames = read_sprite_txt(path)
    if len(frames) < 3:
        raise ValueError(f"{path}: expected >=3 frames, got {len(frames)}")
    return {
        "demonA": [frames[0]],
        "demonB": [frames[1]],
        "demonC": frames[2:4] if len(frames) >= 4 else [frames[2]],
    }


def parse_spriteframes_asm(path: Path) -> dict[str, list[bytes]]:
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    out: dict[str, list[bytes]] = {}
    label: str | None = None
    cur: list[int] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        m = re.search(r"!byte\s+(.+)", line, re.I)
        if m:
            if not label:
                continue
            for tok in m.group(1).split(","):
                tok = tok.strip()
                if tok.startswith("$"):
                    cur.append(int(tok[1:], 16) & 0xFF)
            continue
        if label and cur:
            out[label.lower()] = _flush_frames(cur)
        label = line.rstrip(":").lower()
        cur = []
    if label and cur:
        out[label.lower()] = _flush_frames(cur)
    return out


def _flush_frames(data: list[int]) -> list[bytes]:
    frames: list[bytes] = []
    for i in range(0, len(data), 32):
        chunk = bytes(data[i : i + 32])
        if len(chunk) == 32:
            frames.append(chunk)
    return frames
