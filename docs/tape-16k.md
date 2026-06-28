# JSW-Tape — 16K expanded memory map and data design

This document is the authoritative spec for the tape port. The disk port lives in [`../JSW`](../JSW).

**Baseline import:** JSW git tag `disk-baseline`.

---

## Target hardware

- VIC-20 with **16K RAM expansion** + **~3K base** (~19K usable)
- Load entire game from **cassette once** at cold start
- Tape buffer (`$0200`–`$03FF`) free after load for scratch

---

## Memory map

Screen at **`$1000`** flips the VIC colour pairing vs the disk build (`$1E00` screen):

| Region | Address | Size | Purpose |
|--------|---------|-----:|---------|
| ZP + game state | `$02`+ | ~160 B | See `zp.asm` |
| Tape scratch | `$0200`–`$03FF` | ~512 B | Decompress staging; free after bulk load |
| Rope tables | `$033C`+ | 86 B | Cassette buffer (`warm.asm`) |
| **screen_base** | **$1000** | 408 B | 24×17 display |
| **Engine** | **$1200**+ | ~3.5 KB | Code, decompress, flip, font, music |
| **udg_base** | **$1800** | **1024 B** | 128 character slots |
| **fontchars** | program | 512 B | Proportional glyph defs (Miner-main) |
| **Guardian pool** | **$2000** | 4096 B | Deduped unique frames (127×32 B) |
| **Room catalogue** | **$3000** | ~7 KB | Compressed rooms + indices |
| **Entity table** | **~$4C00** | ~1160 B | Spectrum-style 8 B templates |
| **Palettes / titles / tunes** | **~$5080** | ~2 KB | Shared lookup tables |
| **color_base** | **$9400** | 408 B | Active colour (paired with $1000 screen) |
| **map_base** | **$9600** | 408 B | Ghost colour RAM — collision map |
| **INGAME_TUNE_SEQ** | **$97C0** | 64 B | Optional tail spare in map block |
| **Resident guardian gfx** | **$5E00**+ | ≤896 B | Per-room frames + 128 B h8 flip |

No separate `$5C00` map (Miner-style) — ghost colour RAM reuse saves 512 B.

### UDG layout ($1800, 1024 B)

| Chr | Use |
|-----|-----|
| 13–14 | HUD icons |
| 15–21 | Room tiles |
| 22–45 | Guardian UDGs |
| 46–47 | Arrow |
| 58–63 | Willy |
| 68–90 | Propfont composite row |
| 91–127 | Title art / extra glyphs |

---

## Room catalogue (not per-room PRGs)

~**115 B average** per room record:

- Packed meta (~8 B): conn, palette index, flags, pickup, spawn override, title index
- RLE tilemap (base types 0–3) + optional 3 B ramp + 3 B conveyor overlays
- Guardian refs: **2 B × N** (`entity_id` + `spec`)
- Room UDG bytes (~48 B avg, unique per room)

Global tables (loaded once):

- Entity templates (~848–1160 B)
- Guardian frame pool (4096 B)
- 55 palette × 6 B, 61 title strings, tune data

Tools: `tools/mkcatalogue.py` (TBD), `tools/audit_room_compress.py`, `tools/audit_guardian_frames.py`.

---

## Guardians

- **Entity table** + room **`(id, spec)`** refs (Spectrum model)
- **h8 → 4** unique frames; **128 B flip** contiguous after that sprite set at room load
- **One bidirectional sprite set per room**; multiple instances share frames (colour from entity)
- Runtime uses frame index only — no per-frame flip in game loop

---

## Title and audio

- **Title** in main binary (`title.asm`) — not baked into room 62
- **Font** from Miner-main (`font.asm`, `PrintSpecFontString`)
- **Music** from Miner-main (`music.asm`, dual/triple voice + vibrato)

---

## Implementation phases

| Phase | Status | Content |
|-------|--------|---------|
| 0 | **Done** | Repo split, `rooms/` copy, this doc |
| 1 | Pending | Header equates, `$1000` screen, `make_tape.bat` |
| 2 | Pending | `mkcatalogue.py` |
| 3 | Pending | `decompress.asm`, catalogue loader |
| 4 | Pending | Entity guardians + load-time flip |
| 5 | Pending | Miner font/music + `title.asm` |
| 6 | Pending | `mktape.py`, VICE test |

---

## Size budget (~19 KB)

| Block | ~Size |
|-------|------:|
| Engine + helpers | 3.5 KB |
| Guardian pool | 4 KB |
| Catalogue + globals | 10 KB |
| UDG workspace | 1 KB |
| Screen + map + resident gfx | 1.7 KB |
| ZP + rope + scratch | 0.7 KB |
