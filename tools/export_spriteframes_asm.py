#!/usr/bin/env python3
"""Export bake/sprite_source.asm for mkcatalogue (all sprites including willy)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from guardian_sprite_types import (  # noqa: E402
    SKOOLKIT_TYPES,
    SKOOLKIT_URL,
    format_byte_lines,
    guardian_frame_column_major,
    load_gfx,
    read_demon_txt,
    read_sprite_txt,
    read_willy_txt,
    skoolkit_frames,
)

ROOT = Path(__file__).resolve().parent.parent

# Skool interleaved .txt -> column-major at export (same as mkroom @guardiansprites).
CUSTOM_SPRITES: dict[str, Path] = {
    "maria": ROOT / "maria.txt",
    "toilet": ROOT / "toilet.txt",
    "barrel": ROOT / "barrel.txt",
}

# VIC composite — passthrough (not Skool L,R pairs).
FOOT_SPRITE = ("foot", ROOT / "foot.txt")


def render_type(name: str, frames: list[bytes], *, comment: str) -> list[str]:
    lines = [f"; {comment}", f"{name}"]
    for fr in frames:
        lines.append(format_byte_lines(fr))
    lines.append("")
    return lines


def _header() -> list[str]:
    return [
        f"; {SKOOLKIT_URL}",
        "; Sprite frames: column-major 32 B (16-byte left column, 16-byte right).",
        "",
    ]


def build_sprite_source_asm(root: Path) -> str:
    """All sprite types — consumed by mkcatalogue.py, embedded via catalogue_sprites.asm."""
    gfx = load_gfx()
    out: list[str] = _header() + [
        "; demonA/B/C and foot: VIC composite passthrough (not deinterleaved).",
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
        frames = [guardian_frame_column_major(fr) for fr in read_sprite_txt(path)]
        if not frames:
            raise ValueError(f"no frames in {path}")
        out.extend(render_type(label, frames, comment=f"{label} ({path.name})"))

    foot_label, foot_path = FOOT_SPRITE
    foot_frames = read_sprite_txt(foot_path)
    if not foot_frames:
        raise ValueError(f"no frames in {foot_path}")
    out.extend(
        render_type(
            foot_label,
            foot_frames,
            comment=f"{foot_label} ({foot_path.name}) — VIC composite passthrough",
        )
    )

    willy = read_willy_txt(root / "willy.txt")
    if len(willy) != 8:
        raise ValueError(f"willy.txt: expected 8 frames, got {len(willy)}")
    out.extend(render_type("willy", willy, comment="willy (willy.txt) — player, 8 frames"))

    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description="Export bake/sprite_source.asm")
    ap.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="repo root (sprite .txt files and output path parent)",
    )
    ap.add_argument(
        "-o",
        type=Path,
        default=None,
        help="output asm (default: <root>/bake/sprite_source.asm)",
    )
    args = ap.parse_args()
    out_path = args.o or args.root / "bake" / "sprite_source.asm"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(build_sprite_source_asm(args.root), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
