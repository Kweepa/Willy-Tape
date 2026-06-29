# Jet Set Willy — 16K expanded tape port (JSW-Tape)

16K RAM expansion + 3K base VIC-20 build. The game loads from cassette into memory once; rooms are served from a compressed in-RAM catalogue (no per-room disk loads).

## Relationship to JSW (disk)

| | **JSW** (`../JSW`) | **JSW-Tape** (this repo) |
|--|-------------------|-------------------------|
| Target | Unexpanded + 1541 disk | 16K expanded + tape |
| Rooms | `rooms/` → per-room PRGs on D64 | `rooms/` → compressed catalogue |
| Loader | KERNAL `LOAD` per room | Decompress from catalogue |
| Baseline | Tag `disk-baseline` on JSW | Initial import from that tag |

**`rooms/` in this repo is an independent copy.** Tape-specific layout or guardian edits belong here only. The disk port keeps its own `../JSW/rooms/`. Copy individual room files manually if a fix should land in both.

## Reference code

- **Miner-main/** — local reference for proportional font, music player, and 16K memory layout (gitignored; copy from sibling JSW checkout if missing).
- **tools/jswcache/** — SkoolKit HTML cache for Spectrum data audits (gitignored; populated by `tools/jswimport.py`).

## Build

```bat
make.bat
```

Produces `jsw.prg` (loads at `$1201`) and `catalogue.bin` (room catalogue for Phase 3 loader). Phase 6 adds `mktape.py` for TAP output. Disk-era `mkroom.py` / `mkdisk.py` remain as reference only.

See [docs/tape-16k.md](docs/tape-16k.md) for the target memory map and catalogue design.

## Docs

- [docs/tape-16k.md](docs/tape-16k.md) — memory map, data formats, implementation phases
- [docs/room-format.md](docs/room-format.md) — room source format (shared with disk port at import time)
