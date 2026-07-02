BLACK = 0
WHITE = 1
RED = 2
CYAN = 3
PURPLE = 4
GREEN = 5
BLUE = 6
YELLOW = 7

TILE_EMPTY = 0
TILE_PLATFORM = 1
TILE_SOLID = 2
TILE_HAZARD = 3
TILE_RAMP = 4
TILE_CONVEYOR = 5
TILE_ITEM = 6                   ; map-only marker for pickup cell (not in author tilemap)

ITEM_CHR = 6                    ; pickup (TILE_ITEM)
MEN_CHR = 68                    ; HUD men icon
HUD_ITEM_CHR = 69               ; HUD items icon
FONT_CHR = 70                   ; resident propfont glyphs @ $1A30 (arrow_udgs.asm)
!source "bake/font_equates.inc"
PROPFONT_CHR = 7
PROPFONT_COLS = 17
; propfont_udg label kept for PutFontUDGsOnScreen clear loop (HUD @ PROPFONT_CHR).
propfont_udg = udg_base + PROPFONT_CHR * 8
GUARDIAN_CHR = 24
PLAY_CHR = 60
ARROW_CHR_LTR = 66
ARROW_CHR_RTL = 67
ARROW_X_LTR   = 80
ARROW_X_RTL   = 40
ARROW_SND_LTR = 115
ARROW_SND_RTL = 36

udg_base = $1800
UDG_CHAR_SLOTS = 64
high_bank = udg_base + UDG_CHAR_SLOTS * 8   ; $1A00 — pad, then residents @ $1A10+
RESIDENT_CHR_PAD = 2                          ; chr 64-65 @ $1A00 (player scratch)
resident_base = high_bank + RESIDENT_CHR_PAD * 8   ; $1A10 — arrow/men/item, font @ $1A30
guardian_udgs = udg_base + GUARDIAN_CHR*8
player_udg = udg_base + PLAY_CHR*8
; Arrow glyph addresses — labels in arrow_udgs.asm @ resident_base

; Sync at row 15/16 boundary (below playfield, above HUD). $9001 positions 17-row screen.
RASTERLINE_PAL      = $70
RASTERLINE_NTSC     = $62

GUARDIAN_HORIZONTAL = 0
GUARDIAN_VERTICAL = 1

; player frames 0-3 left / 4-7 right (guardian bidir order); GetPlayerFrameAddr

RAMP_NONE = 0
RAMP_UP_RIGHT = 1
RAMP_UP_LEFT = $FF
RAMP_BOUNDS_NONE = 99

; Endgame: collect all pickups, enter master bedroom (Maria vanishes),
; walk to ENDING_TRIGGER_PX, then teleport to bathroom for the toilet ending.
; r35 master_bed_hook threshold: count_items at bake time (see mkroom.py).
; Quick endgame test: make_test_endgame.bat (--endgame-items-required 2).
ROOM_MASTER_BED = 35
ROOM_BATHROOM = 33
ROOM_NIGHTMARE = 29
; to test rope: room 31 (swimming pool)
; to test arrow: room 36 (a bit of tree)
ROOM_START = 16

ENDING_TRIGGER_PX = 20

; 1 = emit border colour writes for raster timing bars; 0 = no code/size cost
BORDER_DEBUG = 0

; 1 = title screen (title.asm); 0 = skip to game start
SHOW_TITLE = 1

; Rope constants (addresses in header.asm)
ROPE_ANCHOR_COL = 12
ROPE_ANCHOR_PY = 8
ROPE_FIRST_UDG = GUARDIAN_CHR + 12
ROPE_UDG_BYTES = 128
ROPE_XADD_BYTES = 54
ROPE_SEGMENT_Y_BYTES = 32
ROPE_GRAB_COOLDOWN_MAX = 60
ROPE_SEG_MAX = 31
