; Master bedroom (r35) — tape PRG hook only (disk build uses bake/master_bedroom.asm).
; Runs in gameloop after erase, before MoveGuardians.

!zone master_bed

; Maria set 30 — pool frames 121..124 (bake/catalogue_sprites.asm)
MARIA_POOL_HT = 121

FCTL_IDLE = 1
FCTL_LOCK = 0

!ifndef ENDGAME_ITEMS_REQUIRED {
!error "ENDGAME_ITEMS_REQUIRED not defined — pass -DENDGAME_ITEMS_REQUIRED=N from make.bat"
}

master_bed_hook
    lda items_collected
    cmp #ENDGAME_ITEMS_REQUIRED
    bcc check_end
    lda #0
    sta meta_content_guardians

check_end
    lda px
    cmp #ENDING_TRIGGER_PX
    bne proximity
    lda #1
    sta willy_hidden
    sta use_room_spawn
    sta ending_pending
    lda #ROOM_BATHROOM
    sta map
    rts

proximity
    lda px
    cmp #$3a
    bcc near
    lda #MARIA_POOL_HT
    sta guardian_data_base + g_off_fmin
    lda #FCTL_IDLE
    sta guardian_data_base + g_off_fctl
    rts

near
    lda px
    cmp #$36
    bcc set_frame3
    lda #MARIA_POOL_HT + 2
    bne store_point

set_frame3
    lda #MARIA_POOL_HT + 3

store_point
    sta guardian_data_base + g_off_fmin
    lda #FCTL_LOCK
    sta guardian_data_base + g_off_fctl
    lda #0
    sta guardian_data_base + g_off_frame
    rts
