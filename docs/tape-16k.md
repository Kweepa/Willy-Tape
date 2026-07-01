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
| **meta_content_src** | **$13E** | **104 B** | Runtime room meta on stack page; guardian AoS at +39 |
| **Reloc island 1** | **$0200**–**$0313** | **276 B** | Load-path routines copied at WarmStart |
| **ROPE_SEGMENT_Y** | **$034C** | **32 B** | Rope rooms only; xadd table in PRG |
| **Warm boot + reloc src** | **$1800**–**$19FF** | **512 B** | One-shot VIC init, copy loops, pseudopc source blobs |
| **screen_base** | **$1000** | 408 B | 24×17 display |
| **Engine + catalogue** | **$1200**+ | ~18 KB | Code then embedded `catalogue_data.asm` (flows by `!source`; read in place) |
| **udg_base** | **$1800** | **512 B** | 64 character slots (chr 0–63) — runtime charset RAM, not PRG |
| **color_base** | **$9400** | 408 B | Active colour (paired with $1000 screen) |
| **map_base** | **$9600** | 408 B | Ghost colour RAM — collision map |
| **INGAME_TUNE_SEQ** | **$97C0** | 64 B | Optional tail spare in map block |

No separate `$5C00` map (Miner-style) — ghost colour RAM reuse saves 512 B.

### UDG layout ($1800, 512 B — chr 0–63)

| Chr | Use |
|-----|-----|
| 0–6 | Room tiles (empty, floor, wall, …) |
| 13–14 | HUD icons |
| 15–21 | Room tile variants (from canonical pool) |
| 22–45 | Guardian UDGs |
| 64–65 | Arrow (resident in PRG) |
| 58–63 | Willy (6 frames) |

---

## Room catalogue (not per-room PRGs)

~**130 B average** per room record:

- Packed meta (8 B), palette index, null-terminated title, RLE tilemap
- Optional pickup / ramp / conveyor overlays
- Room UDG bytes (~48 B avg)
- Guardians: **count byte** + N × **8 B** (x, y, min, max, vel, color, axis, set_idx)

Global tables (loaded once):

- Guardian frame pool (~220 slots / unique blobs, no flip scratch)
- Set descriptor table (start + count per unique animation)
- 55 palette × 6 B, tune data

Tools: `tools/mkcatalogue.py`, `tools/audit_room_compress.py`, `tools/audit_guardian_frames.py`.

### PRG layout (engine binary)

| Region | Range | Contents |
|--------|-------|----------|
| Low bank | `$1201–$17FF` | Boot stub, gameloop, map, ramp, `willy_collide.asm` |
| UDG hole | `$1800–$19FF` | Warm boot, reloc source pack, then charset RAM at runtime |
| High bank | `$1A00+` | Loader orchestration, draw, guardians, music, rope, catalogue |

### catalogue.bin format (version 6)

Built by `tools/mkcatalogue.py`. Little-endian. Phase 3 loader copies sections to the RAM bases below.

**Header (64 B @ file $0000)** — version **6**; sets offset @ 32; byte 46 reserved (0).

**Per-room guardians** — `8×N` bytes each: **x, y, min, max, vel, color, axis, set_idx**. No frame/fmin/fctl in catalogue (loader fills runtime 10 B AoS from set table).

**Set table** — `set_count × 4 B`: u16 **start_frame**, u8 **frame_count**, u8 **flags** (`SET_FLAG_H_BIDIR` = horizontal bidir: 8 frames in pool, 0–3 left / 4–7 right).

**Flat pool** — unique animation sets appended contiguously. Horizontal bidir stores **8 frames** (left 4 + right 4 from room gfx or parent entity). Split saw sprites expand to bidir. Runtime uses `eor #4` on anim index when facing right.

Loader derives runtime AoS bytes 6–7: `fmin=0`; `fctl=1` if `SET_FLAG_H_BIDIR`, else `fctl=frame_count−1` for vertical wrap.

Measured build: ~8.6 KB room records + sets + pool ≈ **17 KB** file; pool RAM **~7 KB**.

---

## Guardians

- **165 instances** across 61 rooms; **8 B** catalogue bytes each (+ set_idx)
- **`set_idx`** → set table (gfx only; not entities)
- Bidir horizontal: **8 frames in pool** (0–3 left, 4–7 right from source gfx); `eor #4` at runtime
- Runtime 10 B AoS built at load from set flags + count

---

## Title and audio

- **Title** in main binary (`title.asm`) — not a catalogue room
- **Font** from Miner-main (`font.asm`, `PrintSpecFontString`)
- **Music** from Miner-main (`music.asm`, dual/triple voice + vibrato)

---

## Implementation phases

| Phase | Status | Content |
|-------|--------|---------|
| 0 | **Done** | Repo split, `rooms/` copy, this doc |
| 1 | **Done** | Header equates, `$1000` screen, `make.bat`, blank-room boot stub |
| 2 | **Done** | PRG UDG-hole split; `mkcatalogue.py` v6 → `catalogue.bin` |
| 3 | Pending | `decompress.asm`, catalogue loader |
| 4 | Pending | Pool-direct gfx (`guardian_pool` + set table) |
| 5 | Pending | Miner font/music + `title.asm` |
| 6 | Pending | `mktape.py`, VICE test |

---

## Size budget (~19 KB)

| Block | ~Size |
|-------|------:|
| Engine + helpers | 3.5 KB |
| Guardian pool | ~7 KB |
| Catalogue + globals | ~17 KB |
| UDG workspace | 1 KB |
| Screen + map + resident gfx | 1.7 KB |
| ZP + rope + scratch | 0.7 KB |
