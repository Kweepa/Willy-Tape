; Jet Set Willy - unexpanded VIC-20
; PRG from $1000; room image loads to image_base ($1A05)

!source "zp.asm"
!source "defines.asm"
!source "debug.asm"

!source "header.asm"
!source "gameloop.asm"
!source "map.asm"
!source "loader.asm"
!source "ramp.asm"
!source "willy.asm"
!source "util.asm"
!source "input.asm"
!source "guardians.asm"
!source "endgame.asm"
!source "music.asm"

!set ROPE_TEST = 0
!source "rope_draw.asm"
!source "rope_interact.asm"

prg_end = *

!source "ingame_tune.asm"
!source "warm.asm"
!source "runtime_const.asm"
!source "relocated_code.asm"
