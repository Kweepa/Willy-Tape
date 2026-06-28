; unexpanded JSW layout

image_base = $1a05                    ; KERNAL LOAD; room image $1A05-$1FFF (1531 B)
item_flicker_prefix_bytes = 16
room_code_base = image_base + item_flicker_prefix_bytes
conveyor_prefix_bytes = 19
do_belt_prefix_bytes = 26
FlickerItem = image_base
AnimateConveyors = room_code_base
DoBelt = room_code_base + conveyor_prefix_bytes
tile_color_bytes = 6
tile_color_src = room_code_base + conveyor_prefix_bytes + do_belt_prefix_bytes
guardian_sprites_base = tile_color_src + tile_color_bytes
guardian_prefix_bytes = guardian_sprites_base - room_code_base
TitleScreen = image_base              ; r62 only: scroll message + wait for space ($1A05)
title_screen_slot_bytes = $1c00 - image_base  ; 507 B; logo UDGs from $1C00
; arrow UDG @ chr 46 ($1D70); arrow_init + arrow_update @ chr 47+ ($1D78) — see defines.asm
player_bmp = guardian_sprites_base + 288
hud_udg_base = player_bmp + 256         ; chr 13-14 @ $1C68-$1C77
runtime_udg_pad = $150                  ; 336 B ($1CB0-$1DFF); pins screen_base after load

; Relocated resident code (copied from boot zone at WarmStart)
RELOC_A_BASE = $0200
RELOC_A_LIMIT = $0259
RELOC_B_BASE = $0392
RELOC_B_LIMIT = $03fc
RELOC_C_BASE = $0334
RELOC_C_LIMIT = $033c
RELOC_D_BASE = $1000
RELOC_D_LIMIT = $100d
RELOC_E_BASE = $01b6
RELOC_E_LIMIT = $01bf
STACK_FLOOR = $01c0

; Rope runtime in cassette buffer ($033C-$03FB); survives KERNAL disk LOAD
ROPE_SEGMENT_Y = $33c            ; 32 B segment Y table ($33C-$35B)
ROPE_XADD = $35c                 ; 54 B horiz shift table ($35C-$391); copied at WarmStart
rope_xadd = ROPE_XADD
room_image_size = $5fb           ; 1531 bytes ($1A05-$1FFF); +16 B FlickerItem prefix
tail_size = $68                  ; 104 bytes at end of room image
meta_content_src = image_base + room_image_size - tail_size

; Meta payload at meta_content_src (see build_meta in mkroom.py)
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
meta_content_item_draw = meta_content_src + 16    ; 11-byte 6502: lda #chr sta scr lda #TILE_ITEM sta map rts
meta_content_item_draw_size = 11
meta_content_item_erase = meta_content_src + 27   ; 11-byte 6502: lda #empty_col sta col lda #TILE_EMPTY sta map rts
meta_content_item_erase_size = 11
meta_size = 38
meta_content_room_has_rope = meta_content_src + 38
meta_content_guardian_data = meta_content_src + 39
meta_content_has_arrow = meta_content_src + 99
meta_content_spare = meta_content_src + 100        ; 4 bytes reserved in tail
ending_pending = meta_content_spare                  ; r35 hook raises; CheckEndingTeleport clears
master_bed_hook = guardian_udgs + 48                 ; r35 only; UDG slots 1-5 ($1CE0)
master_bed_hook_ext = guardian_sprites_base + 128    ; r35 overflow; sprite frames 4-7 ($1AC8)
master_bed_hook_bytes = 240
master_bed_hook_ext_bytes = 160
item_draw = meta_content_item_draw
item_erase = meta_content_item_erase
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
screen_base = $1e00
ROPE_ANCHOR_SCR = screen_base + ROPE_ANCHOR_COL
ROPE_FIRST_UDG_ADDRESS = udg_base + ROPE_FIRST_UDG * 8
tile_bytes = 408                 ; 24 x 17
hud_row_off = 384                ; row 16 * 24
hud_men_scr = screen_base + hud_row_off + 18
hud_men_col = color_base + hud_row_off + 18
hud_men_count_scr = screen_base + hud_row_off + 19
hud_item_scr = screen_base + hud_row_off + 21
hud_item_col = color_base + hud_row_off + 21
hud_items_scr = screen_base + hud_row_off + 22
hud_items_col = color_base + hud_row_off + 22
map_base = $9400
color_base = $9600
INGAME_TUNE_SEQ = $95c0          ; 64 B index seq; map_base tail; mask low nybble on read
guardian_data_bytes = 60
max_guardians = 6

pickup_got = $100
pickup_got_last = pickup_got + $3d

basic_start = $1000

; basic header
*=basic_start-1
	!word basic_start+1
    !word basic_end
	!word 10
	!byte $9e
	!text "4109"
	!byte 0
basic_end
	!word 0

cold_start
warm_start
    jmp WarmStart
