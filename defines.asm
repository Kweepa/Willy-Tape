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

TILE_CHR_BASE = 16
ITEM_CHR = 15
MEN_CHR = 13                    ; HUD men icon @ $1C68 (hud_udg_base)
HUD_ITEM_CHR = 14               ; HUD items icon @ $1C70
GUARDIAN_CHR = 22
PLAY_CHR = 58
ARROW_CHR = 46

udg_base = $1c00
guardian_udgs = udg_base + GUARDIAN_CHR*8
player_udg = udg_base + PLAY_CHR*8
arrow_udg_addr = udg_base + ARROW_CHR*8
arrow_init = arrow_udg_addr + 8
arrow_update = arrow_init + 5

; Sync at row 15/16 boundary (below playfield, above HUD). Screen shifted down ($9001 = $32).
RASTERLINE_PAL      = $70
RASTERLINE_NTSC     = $62

GUARDIAN_HORIZONTAL = 0
GUARDIAN_VERTICAL = 1

; player frames are indices 9-16 in the guardian_sprites_base + player_bmp block
PLAYER_SPRITE_FRAME = 9

RAMP_NONE = 0
RAMP_UP_RIGHT = 1
RAMP_UP_LEFT = $FF

; Endgame: collect all pickups, enter master bedroom (Maria vanishes),
; walk to ENDING_TRIGGER_PX, then teleport to bathroom for the toilet ending.
; r35 master_bed_hook threshold: count_items at bake time (see mkroom.py).
; Quick endgame test: make_test_endgame.bat (--endgame-items-required 2).
ROOM_MASTER_BED = 35
ROOM_BATHROOM = 33
; to test rope: room 31 (swimming pool)
; to test arrow: room 36 (a bit of tree)
ROOM_START = 33
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
ROPE_GRAB_COOLDOWN_MAX = 60
ROPE_SEG_MAX = 31
