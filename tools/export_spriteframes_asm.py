#!/usr/bin/env python3
"""Build spriteframes.asm from SkoolKit gfx, custom sprite text files, and willy.txt."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from guardian_sprite_types import (  # noqa: E402
    SKOOLKIT_TYPES,
    SKOOLKIT_URL,
    format_byte_lines,
    load_gfx,
    read_demon_txt,
    read_sprite_txt,
    read_willy_txt,
    skoolkit_frames,
)

ROOT = Path(__file__).resolve().parent.parent

CUSTOM_SPRITES: dict[str, Path] = {
    "maria": ROOT / "maria.txt",
    "foot": ROOT / "foot.txt",
    "toilet": ROOT / "toilet.txt",
    "barrel": ROOT / "barrel.txt",
}


def render_type(name: str, frames: list[bytes], *, comment: str) -> list[str]:
    lines = [f"; {comment}", f"{name}"]
    for fr in frames:
        lines.append(format_byte_lines(fr))
    lines.append("")
    return lines


def build_asm(root: Path) -> str:
    gfx = load_gfx()
    out: list[str] = [
        f"; {SKOOLKIT_URL}",
        "; Sprite frames: column-major 32 B (16-byte left column, 16-byte right).",
        "",
    ]

    for name in sorted(SKOOLKIT_TYPES):
        page, lo, hi = SKOOLKIT_TYPES[name]
        frames = skoolkit_frames(name, gfx)
        out.extend(
            render_type(name, frames, comment=f"{name} ({page}/{lo}-{hi})")
        )

    demons = read_demon_txt(root / "demon.txt")
    for dname in ("demonA", "demonB", "demonC"):
        out.extend(
            render_type(
                dname,
                demons[dname],
                comment=f"{dname} — VIC composite (demon.txt)",
            )
        )

    for label, path in CUSTOM_SPRITES.items():
        frames = read_sprite_txt(path)
        if not frames:
            raise ValueError(f"no frames in {path}")
        out.extend(render_type(label, frames, comment=f"{label} ({path.name})"))

    willy = read_willy_txt(root / "willy.txt")
    out.extend(render_type("willy", willy, comment="willy (willy.txt)"))

    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Export spriteframes.asm")
    ap.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repo root (sprite .txt files and output path parent)",
    )
    ap.add_argument("-o", type=Path, default=None)
    args = ap.parse_args()
    out_path = args.o or args.root / "spriteframes.asm"
    out_path.write_text(build_asm(args.root), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
