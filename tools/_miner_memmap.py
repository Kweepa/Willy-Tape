#!/usr/bin/env python3
from pathlib import Path

labels = {}
for line in (Path(__file__).resolve().parent.parent / "Miner-main" / "miner.lbl").read_text().splitlines():
    if line.startswith("al C:"):
        addr, sym = line[5:].strip().split(" ", 1)
        labels[sym.strip().lstrip(".")] = int(addr, 16)

keys = [
    "screen_base",
    "basic_start",
    "udg_base",
    "propfont_udg",
    "fontchars",
    "happy_udgs",
    "guardian_bmps",
    "block_bmps",
    "map0",
    "map19",
    "TitleScreen",
    "hguard_bmp",
    "vguard_bmp",
    "map_base",
    "music_notes_a_1",
    "music_notes_1",
    "PrintSpecFontString",
    "GetCharDefAddr",
]
for k in keys:
    if k in labels:
        print(f"{k:22s} ${labels[k]:04X}")

mx = max(labels.values())
print(f"\nmax symbol: ${mx:04X}")

print(f"\ncode ($1200..$2E6E map0): {labels['map0'] - labels['basic_start']} B")
print(f"font glyph data ($1D00..): starts before happy at $1B00")
print(f"  fontchars..PrintSpecFontString: {labels['PrintSpecFontString'] - labels['fontchars']} B code+data mixed")
print(f"  fontchars size: 64 glyphs * 8 = 512 B (approx to next symbol)")

# UDG layout from defines
udg = labels["udg_base"]
print("\n=== Miner UDG map ($1800 char RAM) ===")
print(f"  udg_base           $1800  chr 16-31  (16 chars = 128 B) room tiles")
print(f"  exit_udgs          +128   chr 32-35  (4 chars)")
print(f"  switch_udgs        +160   chr 36-37  (2 chars)")
print(f"  guardian_udgs      +176   chr 38-57  (6 guardians × 6 chars = 36 chars = 288 B)")
print(f"  player_udg         +464   chr 58-65  (8 chars) — PLAY_CHR=58, HEAD=64")
print(f"  propfont_udg       ${labels['propfont_udg']:04X}  chr 68-90  (23 chars = 184 B runtime composite)")

print("\n=== Miner 16K tape RAM banks (header.asm) ===")
print("  $1000  screen_base     512 B  (22×16 + HUD — NOT at $1E00)")
print("  $1200  basic_start     code + data begins")
print("  $1800  udg_base        512 B character RAM (36869=$0E)")
print("  $1A10  propfont_udg    23×8 composite slot (184 B)")
print("  $1D00  fontchars       64×8 glyph definitions (512 B)")
print("  $1B00  happy_udgs      title clouds (96×8 = 768 B in char RAM)")
print("  $4098  guardian_bmps   all guardian sprite sheets (ROM in file)")
print("  $4E78  block_bmps      tile definitions")
print("  $5C00  map_base        decoded collision map (mirrors screen layout)")
print("  $5E80  vguard_bmp      128 B workspace")
print("  $5F00  hguard_bmp      256 B workspace (+ flip in place)")
print("  $9400  color_base      color RAM (standard VIC)")

# guardian + music sizes
if "music_notes_1" in labels and "map0" in labels:
    print(f"\nmusic data approx: ${labels['music_notes_a_1']:04X}..${labels['map0']:04X} = {labels['map0']-labels['music_notes_a_1']} B")
if "guardian_bmps" in labels and "block_bmps" in labels:
    print(f"guardian_bmps..block_bmps: {labels['block_bmps']-labels['guardian_bmps']} B")

# PRG file
prg = Path(__file__).resolve().parent.parent / "Miner-main" / "miner.prg"
if prg.is_file():
    print(f"\nminer.prg file size: {prg.stat().st_size} B (tape image includes $1000..$5FFF data)")
