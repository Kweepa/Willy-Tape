; Shared equates for per-room bake templates (assembled at org $0000).

!source "../defines.asm"

left_right_ctr  = $46          ; keep in sync with zp.asm (moved off $9D)
belt_active     = $4f
xadd            = $0e
lastxmove       = $4c

conveyor_udg_lo = $1ca8
conveyor_udg_hi = $1caa

; Conveyor oppose rows — must match GetPlayerInput left/right (QW/OP)
belt_opp_right_row   = $fd
belt_opp_right_xadd  = $01

belt_opp_left_row   = $bf
belt_opp_left_xadd  = $ff

belt_push_left  = $ff
belt_push_right = $01

leftIsPressed   = $12          ; keep in sync with zp.asm
rightIsPressed  = $2d
jumpIsPressed   = $0f
on_ground       = $18
ts              = $50

; title screen scratch — keep in sync with zp.asm
title_scroll_off    = $33
title_phase         = $34
title_hold_ctr      = $35
title_scroll_ctr    = $d7
title_music_step    = $d8
title_mpack         = $d9

arrow_x_zp      = $d6          ; keep in sync with zp.asm
scr_ptr         = $05          ; keep in sync with zp.asm
map_ptr         = $15          ; keep in sync with zp.asm
col_ptr         = $07          ; keep in sync with zp.asm

tile_color_src  = $1a42        ; keep in sync with header.asm (6 B tile type colours 0-5)

; master_bedroom.asm — keep in sync with zp.asm / header.asm
px                  = $10
items_collected     = $19
g_frame             = $25
map                 = $5b
use_room_spawn      = $5f
willy_hidden        = $66
meta_content_guardians = $1f98 ; meta_content_src
ending_pending      = $1ffc    ; meta_content_spare
guardian_data_base  = $1fbf    ; meta_content_guardian_data
g_off_frame         = 5
g_off_fmin          = 6
g_off_fctl          = 7          ; vertical frame wrap mask (0/1/3)
FCTL_IDLE           = 1          ; f=0..1 bob
FCTL_LOCK           = 0          ; f=N..N — inc then and #0 keeps g_frame at 0

ROOM_BATHROOM       = 33
ENDING_TRIGGER_PX   = 20
MASTER_BED_HOOK_BYTES = 240

WHT = 1