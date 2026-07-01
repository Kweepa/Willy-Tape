; Jet Set Willy — 16K expanded tape port
; PRG loads at $1201; screen RAM at $1000; warm boot @ $1800; high bank $1A00+

!source "zp.asm"
!source "defines.asm"
!source "debug.asm"

; --- Low bank $1201-$17FF: boot path + physics (no UDG writes) ---
!source "header.asm"
!source "gameloop.asm"
!source "map.asm"
!source "ramp.asm"
!source "willy_collide.asm"
!source "conveyorbelt.asm"

low_bank_end = *
!if low_bank_end > $17FF {
!error "low bank overflow past $17FF"
}

; --- Warm boot @ $1800 (overwritten when UDGs load; charset RAM at runtime) ---
*= udg_base
!source "warm.asm"
warm_boot_end = *
!if warm_boot_end > high_bank {
!error "warm boot overlaps high bank"
}

; --- High bank $1A00+ ---
*= high_bank

; --- High bank $1A00+ ---
!source "decompress.asm"
!source "catalogue_reader.asm"
!source "loader.asm"
!source "font.asm"
!source "ingame_tune.asm"
!source "willy_draw.asm"
!source "util.asm"
!source "input.asm"
!source "guardians.asm"
!source "arrow.asm"
!source "endgame.asm"
!source "master_bedroom_tape.asm"
!source "music.asm"

!set ROPE_TEST = 0
!source "rope_draw.asm"
!source "rope_interact.asm"

!source "tape_runtime.asm"

high_bank_code_end = *
!if high_bank_code_end > $17FF {
!if high_bank_code_end <= $19FF {
!error "high bank code overlaps UDG charset RAM ($1800-$19FF)"
}
}

!source "catalogue_data.asm"

prg_end:
!if prg_end != catalogue_sprites_end {
!error "prg_end must follow catalogue_sprites_end with no gap"
}
