# Room source format (`roomNN.txt`)

Human-editable room descriptions for the JSW VIC-20 port. Convert with [`tools/mkroom.py`](../tools/mkroom.py); pack onto disk with [`tools/mkdisk.py`](../tools/mkdisk.py).

## Screen layout

- **24 × 17** cells (408 bytes screen at `$1E00`).
- **Rows 0–15:** gameplay (author in `@tilemap`).
- **Row 16:** HUD row — left-justified `@title`; men and item count drawn at runtime.

## Tile characters (tilemap)

| Char | Type | Notes |
|------|------|--------|
| ` ` or `.` | Empty | Passable |
| `F` | Floor | Walk on / through (platform) |
| `W` | Wall | Solid; blocks entry |
| `*` | Hazard | Kills Willy |
| `/` | Ramp | Up-right slope |
| `\` | Ramp | Up-left slope |
| `<` | Conveyor | Left belt; must match `@belt -1` |
| `>` | Conveyor | Right belt; must match `@belt 1` |
| `+` | Pickup | Optional collectable position (0 or 1 per room); baked as empty, drawn at runtime |

Author ASCII chars in `@tilemap`; `mkroom` stores screen codes **16–21** (tile type + 16). Ramp direction is **inferred** from `/` (up-right) or `\` (up-left) tiles and baked into room meta. The pickup (screen chr **15**) is **not** baked into the screen — `mkroom` extracts its cell from `+` when present and emits draw code in meta. UDG bitmaps: `@itemudg` → chr 15; `@floorudg` … `@beltudg` → chr 16–21 (tile types 1–5); `@emptyudg` → type 0 (usually omitted — all zeros).

Each `@tilemap` row must be exactly **24 characters** wide. Rows that are entirely spaces are valid (do not delete them).

## Color digits

Each cell is VIC color **0–7** (0=black, 1=white, 2=red, 3=cyan, 4=purple, 5=green, 6=blue, 7=yellow). Extended colours **8–15** are valid only for `@background` (see header tags).

## Header tags

One tag per line, `@name value` or `@name` followed by a block.

| Tag | Fields | Description |
|-----|--------|-------------|
| `@room` | id | Room number (1–63) |
| `@title` | text | Room name (HUD row 16, max 18 characters) |
| `@conn` | N E S W | Neighbours: room number or `FF` (hex ok: `$FF`) |
| `@spawn` | px py | Willy start (quarter-char X, single-pixel head Y) |
| `@border` | colour | Border colour (BLK WHT RED CYN PUR GRN BLU YEL). Combined with `@background` into the meta border byte (full VIC `$900F` value). |
| `@background` | colour | Screen background colour; optional, default **BLK**. Standard colours 0–7 as above; extended VIC background-only colours 8–15: **ORN**, **LIGHT ORN**, **LIGHT RED**, **LIGHT CYN**, **LIGHT PUR**, **LIGHT GRN**, **LIGHT BLU**, **LIGHT YEL** (two-word `LIGHT …` tokens). Digits 0–15 also accepted. Omit when black background is correct. |
| `@belt` | speed | Conveyor speed: `-1`, `0`, or `1` |
| `@playable` | — | Tooling only: room is playtest-ready. Ignored by the binary build. `mkroom.py --status` (or `--all`) reports how many rooms are tagged vs still need work. |
| `@arrow` | y x v sound | Optional flying arrow (one per room). **Mutually exclusive with `@rope`.** `y` = entity pixel Y (tile row = `y >> 3`, same as Spectrum `spec // 2`); `x` = start column (0–255); `v` = `1` (LTR) or `-1` (RTL); `sound` = column where launch SFX fires. Baked **`arrow_init`** + **`arrow_update`** @ chr **47+** (`$1D78`); UDG @ chr **46**. Max **4 `@guardians`**. Meta flag at tail +99. |
| `@arrowudg` | bytes | Optional 8-byte chr **46** UDG; default from `v=` if omitted (LTR: `0,0,194,127,194,0,0,0`; RTL: `0,0,67,254,67,0,0,0`). |
| `@guardiansprites` | block | 256 bytes: 8 frames × 32 bytes. Author in Skool interleaved format (left, right byte pairs per scanline). `mkroom` converts to column-major (16-byte left column, 16-byte right column) in the PRG. |
| `@hguard` | index | Horizontal guardian sprite index |
| `@vguard` | index | Vertical guardian sprite index |
| `@tilemap` | block | 16 lines × 24 characters (gameplay rows 0–15) |
| `@playerbmp` | block | Optional 256-byte Willy sprite (defaults if omitted). Room **29** (Nightmare Room) uses repo-root `nightmareroomwilly.txt` at cook time (Skool interleaved format, deinterleaved like `@guardiansprites`). |
| `@colors` | block | 18 lines × 24 digits |
| `@emptycolor` | colour | Empty/sky cells (type 0); optional, default **WHT** |
| `@floorcolor` | colour | Floor/platform `F` (type 1) |
| `@wallcolor` | colour | Wall `W` (type 2) |
| `@nastycolor` | colour | Hazard `*` (type 3) |
| `@rampcolor` | colour | Ramp `/` `\` (type 4) |
| `@beltcolor` | colour | Conveyor `<` `>` (type 5) |
| `@itemcolor` | colour | Item pickup cell colour for baked `FlickerItem` (optional when no `+`; default YEL) |
| `@emptyudg` | bytes | 8 comma-separated bytes for empty tile; optional, default **8×0**. Decimal by default; **`$XX` hex** ok (e.g. `$FF, 0, 16`) |
| `@floorudg` | bytes | Floor UDG (`; invert` suffix optional); decimal or **`$XX` hex** |
| `@walludg` | bytes | Wall UDG; decimal or **`$XX` hex** |
| `@nastyudg` | bytes | Hazard UDG; decimal or **`$XX` hex** |
| `@rampudg` | bytes | Ramp UDG; decimal or **`$XX` hex** |
| `@beltudg` | bytes | Conveyor UDG; decimal or **`$XX` hex** |
| `@itemudg` | bytes | Item UDG (optional when no `+`); decimal or **`$XX` hex** |
| `@guardians` | list | Guardian DSL per line (see below). Horizontal: **4 or 8** sprite frames (`f=0..3` uni, `f=0..7` bi); byte 7 stores bidirectional flag. Vertical: **1, 2, or 4** frames; byte 7 stores wrap mask. |
| `@guardianbmp` | block | Optional; hex bytes, 128 per guardian in order |

Omit `@*udg` tags for tile types not used in the room when the UDG would be all zeros. Any omitted UDG defaults to 8×0 at build time. Non-zero UDGs are kept even if the tile type is unused.

HUD UDGs (chr **13** men icon, chr **14** items icon) are **not** per-room — `mkroom.py` bakes fixed patterns from `DEFAULT_MEN_UDG` / `DEFAULT_HUD_ITEM_UDG` into every room PRG.

Lines starting with `#` or `;` are comments; `#` may also appear mid-line. Blank lines outside `@tilemap` are ignored.

## Binary layout (output of `mkroom.py`)

PRG loads at **`$1A05`** (1531 bytes image, ends `$1FFF`; 2-byte load address + 1531 = 1535-byte PRG):

| Offset | Address | Size | Content |
|--------|---------|------|---------|
| 0 | `$1A05` | 16 | `FlickerItem` (baked prefix; `jsr` from gameloop) |
| 16 | `$1A15` | 19 | `AnimateConveyors` |
| 35 | `$1A28` | 26 | `DoBelt` |
| 61 | `$1A42` | 6 | Tile colours (types 0–5) |
| 67 | `$1A48` | 288 | Guardian sprites (column-major from `@guardiansprites`) |
| 355 | `$1B68` | 256 | `player_bmp` |
| 611 | `$1C68` | 16 | HUD UDG bytes (chr 13=men, chr 14=items) |
| 627 | `$1C78` | 56 | Tile UDG bytes (chr 15=item, chr 16–21=tiles 0–5) |
| 683 | `$1CB0` | 336 | Runtime UDG pad (zeros; guardian + player UDG workspace) |
| 1019 | `$1E00` | 408 | 24×17 screen (row 16 = HUD + title; item not baked in) |
| 1427 | `$1F98` | 104 | Meta tail (see below) |

**r35 (Master Bedroom) only:** `master_bed_hook` is baked at guardian UDG slots 1–5 (`$1CE0`, up to 240 B in the pad); overflow continues in unused sprite frames 4–7 (`$1AC8`, up to 160 B). `gameloop.asm` calls it when `map == ROOM_MASTER_BED` (after erase, before `MoveGuardians`). The hook zeros `meta_content_guardians` when items are complete; `ending_pending` lives in meta spare byte +100.

### Item pickup runtime

- **`@itemcolor`** — baked into `FlickerItem` as the item cell colour address; `FlickerItem` cycles colour every frame (`inx` / `and #7`). Not written by `item_draw`.
- **`FlickerItem`** — 16-byte prefix at `$1A05`; noop (`rts` + pad) when the room has no `+` pickup.
- **`item_draw`** — 11 bytes at meta **+16**: `lda #15` / `sta screen` / `lda #TILE_ITEM` / `sta map` / `rts`. `LoadRoom` calls `jsr item_draw` when `pickup_got` for this room is clear.
- **`item_erase`** — 11 bytes at meta **+27**: `lda #empty_col` / `sta colour` / `lda #TILE_EMPTY` / `sta map` / `rts` (on pickup).

### Meta tail (`$1F98`, 104 bytes)

Fixed meta header (**38** bytes), then rope flag, guardian AoS, spare:

| Meta offset | Size | Content |
|-------------|------|---------|
| +0 | 16 | Guardian count, border/spawn/belt/ramp, `@conn` |
| +16 | 11 | `item_draw` stub |
| +27 | 11 | `item_erase` stub |
| +38 | 1 | Rope flag |
| +39 | 60 | Guardian AoS (6 × 10 bytes) |
| +99 | 1 | Arrow flag (`meta_content_has_arrow`; non-zero = room has `@arrow`) |
| +100 | 4 | Spare (reserved) |

Split outputs (optional): `ROOMnn.TIL`, `ROOMnn.COL`, `ROOMnn.MET`.

### Meta border byte (`$1F99`) and VIC `$900F`

`$900F` sets **screen background** (bits 4–7) and **border** (bits 0–3) only; it does not affect per-cell color RAM.

Packed value: `(background << 4) | 8 | border`. Bit 3 (`| 8`) is always set in the baked byte. Omitting `@background` is equivalent to `@background BLK`.

| `@background` | `@border` | Meta byte | `$900F` |
|---------------|-----------|-----------|---------|
| (omit / BLK) | BLK | 8 | black bg, black border |
| (omit / BLK) | CYN | 11 | black bg, cyan border |
| (omit / BLK) | RED | 10 | black bg, red border |
| RED | CYN | 43 | red bg, cyan border |
| LIGHT CYN | BLK | B8 | light cyan bg, black border |

Runtime (`ParseRoomMeta`) loads this byte and writes it directly to `$900F` — no `and`/`ora` at load time.

---

## Example room 1 — copy from here

Save as [`rooms/room01.txt`](../rooms/room01.txt).

```
# ROOM 1 — The Landing
# South exit to room 2. Tutorial: platforms, hazard, one item.

@room 1
@title The Landing
@playable
@conn FF FF 2 FF
@spawn 44 56
@border BLK
@belt 0
@hguard 0
@vguard 0

@tilemap
WWWWWWWWWWWWWWWWWWWWWWWW
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W          + *        W
W          FFFFF       W
W          FFFFF       W
                        
                        

@floorcolor WHT
@wallcolor WHT
@nastycolor RED
@rampcolor CYN
@beltcolor PUR
@itemcolor YEL

@guardians

@floorudg 0,0,0,0,255,255,255,255
@walludg 255,255,255,255,255,255,255,255
@nastyudg 0,24,60,126,255,126,60,24
@rampudg 0,0,1,3,6,12,24,48
@beltudg 0,170,85,170,85,170,85,170
@itemudg 48,72,136,144,104,4,10,4
```

**Notes:** Row 13 hazard at column 12 (`*`). Floor rows 14–15 (cols 11–15, `F`). Open south on row 15. Pickup at (10, 13) marked with `+` on row 13.

---

## Example room 2 — copy from here

Save as [`rooms/room02.txt`](../rooms/room02.txt).

```
# ROOM 2 — The Cellar
# North exit back to room 1. Conveyor across middle.

@room 2
@title The Cellar
@conn 1 FF FF FF
@spawn 44 16
@border BLU
@belt 1
@hguard 0
@vguard 0

@tilemap
WWWWWWWWWWWWWWWWWWWWWWWW
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W                      W
W       >>>>>>>        W
W                      W
W                      W
W                      W
W                      W
W                      W
W          FFFFF       W
W    +     FFFFF       W
                        
                        

@emptycolor BLU
@floorcolor WHT
@wallcolor WHT
@nastycolor RED
@rampcolor CYN
@beltcolor PUR
@itemcolor YEL

@guardians

@floorudg 0,0,0,0,255,255,255,255
@walludg 255,255,255,255,255,255,255,255
@nastyudg 0,24,60,126,255,126,60,24
@rampudg 0,0,1,3,6,12,24,48
@beltudg 170,85,170,85,170,85,170,85
@itemudg 48,72,136,144,104,4,10,4
```

**Notes:** `@conn 1` = north to room 1. Spawn near top (`py=16`) for entry from north. Conveyor row 8 (cols 11–16, `>`). One pickup at (4, 14) marked with `+`.

---

## Guardian runtime performance

Vertical guardians follow the same pattern as horizontal ones and as Manic Miner (`Miner-main/guardians.asm`):

- **`CopyGuardianFrame`** runs when a guardian gets its round-robin tick (`ShouldMove*GuardianThisFrame` passes), even if position does not change (`v=0`). `MoveGuardian` advances the stored frame index (`g_frame`, byte 5) on every such tick; vertical sprite lookup uses `g_frame + ht`, horizontal still uses `hx & 3`.

`CopyDownGuardianData` / `CopyUpGuardianData` copy the full 10-byte record into ZP scratch (`hx`–`guard_axis` at `$20`–`$29`, with `g_frame` at `$25`). `CopyUp` writes back the mutable prefix through byte 5 (position, velocity, frame).
- **`DrawGuardian`** runs every tick — it only plasters existing UDG codes to the screen.

`CopyGuardianFrame` is expensive (column copy, top/bottom clears, self-modifying source pointers). Rooms with many vertical guardians (e.g. room 29) were slow when the copy ran every frame for every guardian; round-robin limits copies to one guardian per axis group per movement phase.

Set `BORDER_DEBUG = 0` in `defines.asm` to disable raster timing border probes (`debug.asm` macros).

### Guardian data layout

Room tail stores **60 bytes** of guardian state as **AoS**: six records of ten bytes each (`x`, `y`, `min`, `max`, `vel`, `frame`, `fmin`, `fctl`, `color`, `axis`) at `guardian_data_base` (tail offset **39**). Byte **`fctl`**: horizontal bidirectional flag (0/1); vertical `g_frame` wrap mask (0/1/3). Tile colours live in the prefix at `tile_color_src` (`$1A42`), not in the tail.

Each frame, `CopyDownGuardianData` / `CopyUpGuardianData` copy one record between room RAM and ZP scratch via tight `(arr),y` loops indexed from `hx`.

---

## Tooling

```bash
# One room → binary
python tools/mkroom.py rooms/room01.txt rooms/out/ROOM01

# All rooms/room*.txt → rooms/out/
python tools/mkroom.py --all rooms rooms/out

# Playable-room progress (@playable tag; no build)
python tools/mkroom.py --status rooms

# D64 (needs built jsw.prg optional)
python tools/mkdisk.py --out jsw.d64 --prg jsw.prg --rooms rooms/out
```

On Windows with VICE installed at `c:\app\vice3.10\bin`, `mkdisk.py` uses that `c1541` automatically (same path as [`make.bat`](../make.bat)). Override with `--c1541` or `VICE_BIN` env. An `OPENCBM` warning on startup is normal when no real IEC drive is attached; image operations still work.

Example sources: [`rooms/room01.txt`](../rooms/room01.txt), [`rooms/room02.txt`](../rooms/room02.txt).

Save the scripts below as [`tools/mkroom.py`](../tools/mkroom.py) and [`tools/mkdisk.py`](../tools/mkdisk.py).

---

## Reference script: `tools/mkroom.py`

> **Note:** The abbreviated listing below is outdated (numeric tilemaps, `@items`). Use the real [`tools/mkroom.py`](../tools/mkroom.py) — ASCII tilemap chars and `+` pickup markers as documented above.

```python
#!/usr/bin/env python3
"""Convert roomNN.txt source files to binary room blobs for JSW VIC-20."""

import argparse
import re
import struct
import sys
from pathlib import Path

WIDTH, HEIGHT = 24, 18
GRID = WIDTH * HEIGHT


def parse_byte(s: str) -> int:
    s = s.strip().upper()
    if s.startswith("$"):
        return int(s[1:], 16)
    if s.startswith("0X"):
        return int(s[2:], 16)
    return int(s)


def parse_room(text: str) -> dict:
    lines = text.splitlines()
    room = {
        "id": 0,
        "title": "",
        "conn": [0xFF, 0xFF, 0xFF, 0xFF],
        "spawn": (0, 0),
        "border": 0,
        "belt": 0,
        "ramp": 0,
        "hguard": 0,
        "vguard": 0,
        "tilemap": [],
        "colors": [],
        "items": [],
        "guardians": [],
        "tileudg": [bytes(8) for _ in range(6)],
        "guardianbmp": b"",
    }
    block = None
    block_lines = []

    def flush_block():
        nonlocal block, block_lines
        if block == "tilemap":
            room["tilemap"] = block_lines.copy()
        elif block == "colors":
            room["colors"] = block_lines.copy()
        elif block == "tileudg":
            for line in block_lines:
                m = re.match(r"(\d+)\s*:\s*(.+)", line.strip(), re.I)
                if not m:
                    continue
                idx = int(m.group(1))
                bs = [int(x, 16) for x in m.group(2).split()]
                if idx < 6 and len(bs) == 8:
                    room["tileudg"][idx] = bytes(bs)
        elif block == "guardianbmp":
            bs = []
            for line in block_lines:
                bs.extend(int(x, 16) for x in line.split())
            room["guardianbmp"] = bytes(bs)
        block = None
        block_lines.clear()

    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("@"):
            flush_block()
            parts = line.split()
            tag = parts[0][1:].lower()
            if tag in ("tilemap", "colors", "tileudg", "guardianbmp", "guardians", "items"):
                block = tag
                continue
            if tag == "room":
                room["id"] = int(parts[1])
            elif tag == "title":
                room["title"] = line.split(None, 1)[1]
            elif tag == "conn":
                room["conn"] = [parse_byte(x) for x in parts[1:5]]
            elif tag == "spawn":
                room["spawn"] = (int(parts[1]), int(parts[2]))
            elif tag == "border":
                room["border"] = parse_vic_color(parts[1])
            elif tag == "belt":
                room["belt"] = int(parts[1])
            elif tag == "ramp":
                room["ramp"] = int(parts[1])
            elif tag == "hguard":
                room["hguard"] = int(parts[1])
            elif tag == "vguard":
                room["vguard"] = int(parts[1])
            continue
        if block == "guardians":
            if line:
                room["guardians"].append([int(x) for x in line.split()])
        elif block == "items":
            cols = [int(x) for x in line.split()]
            for i in range(0, len(cols) - 1, 2):
                room["items"].append((cols[i], cols[i + 1]))
        elif block in ("tilemap", "colors", "tileudg", "guardianbmp"):
            block_lines.append(line)
    flush_block()
    return room


def grid_bytes(rows: list[str], name: str) -> bytes:
    if len(rows) != HEIGHT:
        raise ValueError(f"{name}: expected {HEIGHT} rows, got {len(rows)}")
    out = bytearray()
    for r, row in enumerate(rows):
        row = row.strip()
        if len(row) != WIDTH:
            raise ValueError(f"{name} row {r}: expected {WIDTH} cols, got {len(row)}")
        for ch in row:
            v = int(ch)
            if v > 7 and name == "colors":
                raise ValueError(f"color out of range 0-7: {v}")
            if v > 5 and name == "tilemap":
                raise ValueError(f"tile out of range 0-5: {v}")
            out.append(v)
    return bytes(out)


def belt_byte(speed: int) -> int:
    return speed & 0xFF  # -1 -> 255


def build_binary(room: dict) -> bytes:
    tilemap = grid_bytes(room["tilemap"], "tilemap")
    colors = grid_bytes(room["colors"], "colors")
    meta = bytearray()
    g = room["guardians"]
    meta.append(len(g))
    for rec in g:
        if len(rec) != 7:
            raise ValueError("guardian record needs 7 fields")
        meta.extend(rec)
    meta.append(room["border"] | 8)
    meta.append(room["spawn"][0] & 0xFF)
    meta.append(room["spawn"][1] & 0xFF)
    meta.append(belt_byte(room["belt"]))
    meta.append(room["ramp"] & 0xFF)
    meta.append(room["hguard"] & 0xFF)
    meta.append(room["vguard"] & 0xFF)
    meta.extend(room["conn"])
    meta.extend(room["title"].encode("ascii") + b"\x00")
    meta.append(len(room["items"]))
    for col, row in room["items"]:
        meta.append(col & 0xFF)
        meta.append(row & 0xFF)
    for i in range(6):
        meta.extend(room["tileudg"][i])
    if room["guardianbmp"]:
        meta.extend(room["guardianbmp"])
    return tilemap + colors + bytes(meta)


def convert_file(src: Path, outstem: Path, split: bool) -> None:
    room = parse_room(src.read_text(encoding="utf-8"))
    data = build_binary(room)
    outstem.parent.mkdir(parents=True, exist_ok=True)
    outstem.write_bytes(data)
    print(f"{src.name} -> {outstem} ({len(data)} bytes, room {room['id']})")
    if split:
        outstem.with_suffix(".TIL").write_bytes(data[0:432])
        outstem.with_suffix(".COL").write_bytes(data[432:864])
        outstem.with_suffix(".MET").write_bytes(data[864:])


def main():
    ap = argparse.ArgumentParser(description="Convert JSW roomNN.txt files to binary")
    ap.add_argument("input", nargs="?", help="roomNN.txt file or directory with --all")
    ap.add_argument("output", nargs="?", help="output file stem e.g. rooms/out/ROOM01")
    ap.add_argument("--all", action="store_true", help="convert all rooms/room*.txt in input dir")
    ap.add_argument("--split", action="store_true", help="also write .TIL .COL .MET")
    args = ap.parse_args()
    if args.all:
        indir = Path(args.input or "rooms")
        outdir = Path(args.output or "rooms/out")
        for src in sorted(indir.glob("room*.txt")):
            n = parse_room(src.read_text(encoding="utf-8"))["id"]
            convert_file(src, outdir / f"ROOM{n:02d}", args.split)
        return
    if not args.input or not args.output:
        ap.error("need input and output, or --all")
    convert_file(Path(args.input), Path(args.output), args.split)


if __name__ == "__main__":
    main()
```

---

## Reference script: `tools/mkdisk.py`

Uses **`c1541`** from VICE when on `PATH`; otherwise builds a minimal D64 with [`d64` layout](https://www.z64.dk/cbm/d64.html) in pure Python (sufficient for a few PRG files).

```python
#!/usr/bin/env python3
"""Build jsw.d64 from jsw.prg and ROOMnn binaries."""

import argparse
import shutil
import struct
import subprocess
import sys
from pathlib import Path

SECTOR_SIZE = 256
TRACKS = 35
SECTORS_PER_TRACK = 21


def c1541_available() -> bool:
    return shutil.which("c1541") is not None


def build_with_c1541(d64: Path, prg: Path | None, rooms: list[Path]) -> None:
    if d64.exists():
        d64.unlink()
    label = "JSW"
    subprocess.check_call(["c1541", "-format", f"{label},01", "d64", str(d64)])
    if prg and prg.exists():
        subprocess.check_call(["c1541", str(d64), "-write", str(prg), "JSW"])
    for room in rooms:
        name = room.name.upper()[:16]
        subprocess.check_call(["c1541", str(d64), "-write", str(room), name])
    print(f"Wrote {d64} via c1541 ({len(rooms)} rooms)")


def load_address(data: bytes) -> bytes:
    """PRG with 2-byte load address prefix."""
    return struct.pack("<H", 0x1200) + data


class MinimalD64:
    """Minimal D64 writer: one directory block + file chains."""

    def __init__(self):
        self.data = bytearray(SECTOR_SIZE * SECTORS_PER_TRACK * TRACKS)
        self._init_bam()
        self._init_dir()
        self.next_t = 1
        self.next_s = 2  # skip BAM(0,0) and dir(18,1)

    def _ts_off(self, track: int, sector: int) -> int:
        return (track * SECTORS_PER_TRACK + sector) * SECTOR_SIZE

    def _init_bam(self):
        off = 0
        self.data[off + 0x90] = 0x41  # DOS type 'A'
        self.data[off + 0xA0] = 0x28  # dir track 18
        self.data[off + 0xA1] = 0x01  # dir sector
        # mark track 18 sector 0 used in BAM (simplified)
        self.data[off + 0x100] = 0xFF

    def _init_dir(self):
        off = self._ts_off(18, 1)
        self.data[off + 0x00] = 0x00  # no next dir block
        self.data[off + 0x01] = 0xFF

    def _alloc_sector(self) -> tuple[int, int]:
        t, s = self.next_t, self.next_s
        self.next_s += 1
        if self.next_s >= SECTORS_PER_TRACK:
            self.next_s = 0
            self.next_t += 1
        return t, s

    def add_file(self, name: str, payload: bytes, file_type: int = 0x82):
        name = name.upper().ljust(16)[:16]
        entry_off = self._ts_off(18, 1) + 2
        # find free dir slot
        for slot in range(8):
            e = entry_off + slot * 32
            if self.data[e] == 0x00 or self.data[e] == 0xA0:
                break
        else:
            raise RuntimeError("directory full")
        sectors = (len(payload) + SECTOR_SIZE - 1) // SECTOR_SIZE
        first_t, first_s = self._alloc_sector()
        # write chain
        pos = 0
        t, s = first_t, first_s
        for i in range(sectors):
            off = self._ts_off(t, s)
            chunk = payload[pos : pos + SECTOR_SIZE]
            pos += len(chunk)
            if i + 1 < sectors:
                nt, ns = self._alloc_sector()
                self.data[off] = nt
                self.data[off + 1] = ns
            else:
                self.data[off] = 0
                self.data[off + 1] = 0xFF
            self.data[off + 2 : off + 2 + len(chunk)] = chunk
            t, s = nt, ns if i + 1 < sectors else (0, 0)
        # dir entry
        self.data[e] = file_type
        self.data[e + 2 : e + 4] = struct.pack("<H", first_t * 256 + first_s)  # simplified track/sector
        self.data[e + 0x1C] = first_t
        self.data[e + 0x1D] = first_s
        self.data[e + 0x1E] = sectors & 0xFF
        self.data[e + 0x1F] = (sectors >> 8) & 0xFF
        for i, c in enumerate(name):
            self.data[e + 0x03 + i] = ord(c)

    def save(self, path: Path):
        path.write_bytes(self.data)


def build_pure_python(d64: Path, prg: Path | None, rooms: list[Path]) -> None:
    d = MinimalD64()
    if prg and prg.exists():
        d.add_file("JSW", load_address(prg.read_bytes()))
    for room in rooms:
        d.add_file(room.stem, room.read_bytes())
    d.save(d64)
    print(f"Wrote {d64} (pure Python, {len(rooms)} rooms)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="jsw.d64")
    ap.add_argument("--prg", default="jsw.prg")
    ap.add_argument("--rooms", default="rooms/out", help="directory with ROOMnn files")
    args = ap.parse_args()
    room_dir = Path(args.rooms)
    rooms = sorted(room_dir.glob("ROOM*"))
    rooms = [r for r in rooms if r.suffix.upper() not in (".TIL", ".COL", ".MET")]
    if not rooms:
        print("No ROOM* binaries found; run mkroom.py first", file=sys.stderr)
        sys.exit(1)
    d64 = Path(args.out)
    prg = Path(args.prg)
    if c1541_available():
        build_with_c1541(d64, prg if prg.exists() else None, rooms)
    else:
        print("c1541 not found; using pure-Python D64 writer", file=sys.stderr)
        build_pure_python(d64, prg if prg.exists() else None, rooms)


if __name__ == "__main__":
    main()
```

**Note:** The pure-Python D64 writer is minimal — prefer **`c1541`** from VICE for a reliable image. Test with:

```bash
xvic -pal jsw.d64
```
