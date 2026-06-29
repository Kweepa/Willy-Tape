; Jet Set Willy — 16K expanded tape port
; PRG loads at $1201; screen RAM at $1000; UDG hole $1800-$1BFF; high bank $1C00+

!source "zp.asm"
!source "defines.asm"
!source "debug.asm"

; --- Low bank $1201-$17FF: boot path + physics (no UDG writes) ---
!source "header.asm"
!source "gameloop.asm"
!source "map.asm"
!source "loader.asm"
!source "ramp.asm"
!source "willy_collide.asm"

low_bank_end = *
!if low_bank_end > $17FF {
!error "low bank overflow past $17FF"
}

; --- UDG charset RAM $1800-$1BFF: no code ---
*= $1C00

; --- High bank $1C00+ ---
!source "ingame_tune.asm"
!source "willy_draw.asm"
!source "util.asm"
!source "input.asm"
!source "guardians.asm"
!source "spriteframes.asm"
!source "endgame.asm"
!source "music.asm"

!set ROPE_TEST = 0
!source "rope_draw.asm"
!source "rope_interact.asm"

prg_end = *

!source "tape_runtime.asm"
!source "warm.asm"
