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
MEN_CHR = 66                    ; HUD men icon
HUD_ITEM_CHR = 67               ; HUD items icon
PROPFONT_CHR = 9
PROPFONT_COLS = 13
propfont_udg = udg_base + PROPFONT_CHR * 8
GUARDIAN_CHR = 22
PLAY_CHR = 58
ARROW_CHR_LTR = 64
ARROW_CHR_RTL = 65

udg_base = $1800
UDG_CHAR_SLOTS = 64
high_bank = udg_base + UDG_CHAR_SLOTS * 8   ; $1A00 — arrow UDGs chr 64–65, then code
guardian_udgs = udg_base + GUARDIAN_CHR*8
player_udg = udg_base + PLAY_CHR*8
; Arrow glyph addresses — labels in arrow_udgs.asm @ high_bank

; Sync at row 15/16 boundary (below playfield, above HUD). $9001 positions 17-row screen.
RASTERLINE_PAL      = $70
RASTERLINE_NTSC     = $62

GUARDIAN_HORIZONTAL = 0
GUARDIAN_VERTICAL = 1

; player frames 0-7 via player_sprite_set_idx in catalogue sprite pool; GetPlayerFrameAddr

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
; to test rope: room 31 (swimming pool)
; to test arrow: room 36 (a bit of tree)
ROOM_START = 36
ROOM_TITLE = 62

; RJY.prg overlay at GetPlayerInput; keyboard slot padded with $EA to this size (62 B).
GETPLAYERINPUT_PATCH_BYTES = 62
ENDING_TRIGGER_PX = 20

; 1 = emit border colour writes for raster timing bars; 0 = no code/size cost
BORDER_DEBUG = 0

; Rope constants (addresses in header.asm)
ROPE_ANCHOR_COL = 12
ROPE_ANCHOR_PY = 8
ROPE_FIRST_UDG = GUARDIAN_CHR + 12
ROPE_UDG_BYTES = 128
ROPE_XADD_BYTES = 54
ROPE_SEGMENT_Y_BYTES = 32
ROPE_GRAB_COOLDOWN_MAX = 60
ROPE_SEG_MAX = 31
