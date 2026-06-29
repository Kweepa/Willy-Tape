; JSW-Tape — 16K expanded cassette layout
; Screen @ $1000 pairs with color @ $9400; ghost colour @ $9600 holds map_base.

screen_base = $1000
color_base  = $9400
map_base    = $9600
tile_bytes  = 408                 ; 24 x 17
hud_row_off = 384                 ; row 16 * 24

; Character RAM @ $1800 — room tiles chr 0-6 (empty=0), HUD 13-14, guardians 22+
udg_base = $1800

; Room catalogue in PRG (catalogue_data.asm): catalogue_rooms.asm (RoomRecordPtrs +
; room records), catalogue_guardians.asm (guardian_set_metadata, guardian_sprite_frames).
; Read in place. Tile colours are 6 B inline in each room record.

; Room record flags (meta8 byte 6 — see bake/room_record.asm)
FLAG_NASTY    = $01
FLAG_RAMP     = $02
FLAG_CONVEYOR = $04
FLAG_ROPE     = $08
FLAG_ARROW    = $10

title_ptr       = $39          ; 2 B pointer into catalogue record title

UDG_FIXED_BYTES = 24              ; floor + wall + item UDG in every room record

meta_content_src = $5800
tail_size       = 104
meta_content_guardians = meta_content_src
meta_content_border = meta_content_src + 1
meta_content_spawn_px = meta_content_src + 2
meta_content_spawn_py = meta_content_src + 3
meta_content_belt = meta_content_src + 4
meta_content_ramp = meta_content_src + 5
meta_content_ramp_rx1 = meta_content_src + 6
meta_content_ramp_rx2 = meta_content_src + 7
meta_content_ramp_ry = meta_content_src + 8
meta_content_ramp_E = meta_content_src + 9
meta_content_ramp_A = meta_content_src + 10
meta_content_ramp_ymin = meta_content_src + 11
meta_content_conn = meta_content_src + 12
meta_content_item_draw = meta_content_src + 16
meta_content_item_draw_size = 11
meta_content_item_erase = meta_content_src + 27
meta_content_item_erase_size = 11
meta_size = 38
meta_content_room_has_rope = meta_content_src + 38
meta_content_guardian_data = meta_content_src + 39
meta_content_has_arrow = meta_content_src + 99
meta_content_spare = meta_content_src + 100
meta_content_record_flags = meta_content_spare + 1
ending_pending = meta_content_spare
guardian_data_base = meta_content_guardian_data
tail_base = meta_content_src
guardian_record_bytes = 10
g_off_x = 0
g_off_y = 1
g_off_min = 2
g_off_max = 3
g_off_vel = 4
g_off_frame = 5
g_off_fmin = 6
g_off_fctl = 7
g_off_color = 8
g_off_axis = 9
guardian_data_bytes = 60
max_guardians = 6

; Per-room resident gfx workspace (Phase 4)
guardian_sprites_base = $5e00
player_bmp = $5f00

; In-game tune index seq — optional tail spare in map colour block (unused; tune in PRG).
INGAME_TUNE_SEQ = $97c0

; Unified runtime stubs (tape_runtime.asm)
item_flicker_prefix_bytes = 16
conveyor_prefix_bytes = 19
do_belt_prefix_bytes = 26
tile_color_bytes = 6

hud_men_scr = screen_base + hud_row_off + 18
hud_men_col = color_base + hud_row_off + 18
hud_men_count_scr = screen_base + hud_row_off + 19
hud_item_scr = screen_base + hud_row_off + 21
hud_item_col = color_base + hud_row_off + 21
hud_items_scr = screen_base + hud_row_off + 22
hud_items_col = color_base + hud_row_off + 22

ROPE_ANCHOR_SCR = screen_base + ROPE_ANCHOR_COL
ROPE_FIRST_UDG_ADDRESS = udg_base + ROPE_FIRST_UDG * 8
master_bed_hook = guardian_udgs + 48
master_bed_hook_ext = guardian_sprites_base + 128
master_bed_hook_bytes = 240
master_bed_hook_ext_bytes = 160

pickup_got = $100
pickup_got_last = pickup_got + $3d

ROPE_SEGMENT_Y = $33c

; Code / BASIC entry (Miner-main layout)
basic_start = $1200

*= basic_start - 1
    !word basic_start + 1       ; PRG load address
    !word basic_end
    !word 10
    !byte $9e
    !text "4621"                ; $1200 + 13 = $120D
    !byte 0
basic_end
    !word 0

cold_start
warm_start
    jmp WarmStart
