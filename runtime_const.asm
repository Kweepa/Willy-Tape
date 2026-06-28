; Boot source tables — copied once at WarmStart to ZP ($D6+), stack page ($140+), and cassette buffer ($35C+).
; Not read at runtime; game code uses equates in zp.asm / header.asm.

boot_zp_pack
    !byte 24, 25, 48, 49, 72, 73                    ; cell_off_2x3_boot / util.asm, guardians.asm
    !byte 23, 26, 47, 50, 71, 74                    ; lr_touch_a_boot / willy.asm CollideLeftRight
    !byte 0, 3, 1, 4, 2, 5                            ; draw_vguard_chrs_boot / guardians.asm
boot_draw_player_offsets
    !byte 24, 48, 72, 25, 49, 73                    ; willy.asm DrawPlayer
boot_draw_player_chrs
    !byte PLAY_CHR, PLAY_CHR+1, PLAY_CHR+2, PLAY_CHR+3, PLAY_CHR+4, PLAY_CHR+5
boot_zp_pack_end = *

boot_zp_room_size = boot_draw_player_offsets - boot_zp_pack

stack_page_pack
    ; x24rowtab_boot
    !word screen_base - 24
    !word screen_base + 0
    !word screen_base + 24
    !word screen_base + 48
    !word screen_base + 72
    !word screen_base + 96
    !word screen_base + 120
    !word screen_base + 144
    !word screen_base + 168
    !word screen_base + 192
    !word screen_base + 216
    !word screen_base + 240
    !word screen_base + 264
    !word screen_base + 288
    !word screen_base + 312
    !word screen_base + 336
    !word screen_base + 360
    !word screen_base + 384
    ; jumptab_boot / willy.asm Collide
    !byte -2, -1, -2, -1, -2, -1, -1, -1, -2, -1, -1, 0, -1, -1, -1, 0, -1, 0, -1, 0, 0, -1, 0, 0, 0, 0, 0
    !byte 0, 0, 0, 0, 0, 1, 0, 0, 1, 0, 1, 0, 1, 1, 1, 0, 1, 1, 2, 1, 1, 1, 2, 1, 2, 1, 2
    ; jumpnotes / willy.asm Collide
    !byte 150,155,160,165,170,175,180,185,190
    !byte 195,200,205,210,215,210,205,200,195
    !byte 190,185,180,175,170,165,160,155,150
stack_page_pack_end = *

!source "rope_xadd_boot.asm"

boot_zp_size = boot_zp_pack_end - boot_zp_pack
!if boot_zp_size <> 30 {
!error "boot_zp_size must be 30"
}
!if boot_zp_room_size <> 18 {
!error "boot_zp_room_size must be 18"
}

stack_page_size = stack_page_pack_end - stack_page_pack
!if stack_page_size <> 117 {
!error "stack_page_size must be 117"
}

boot_rope_xadd_size = boot_rope_xadd_pack_end - boot_rope_xadd_pack
!if boot_rope_xadd_size <> ROPE_XADD_BYTES {
!error "boot_rope_xadd_size must match ROPE_XADD_BYTES"
}
