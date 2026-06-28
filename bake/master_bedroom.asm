; Master bedroom (r35) — Maria proximity, hide on items, ending prep.
; Baked into runtime_udg_pad+48 ($1CE0); overflow at guardian_sprites+128 ($1AC8).
; CLI: -DORG=$1ce0 -DENDGAME_ITEMS_REQUIRED=N -DENDING_TRIGGER_PX=20 -DROOM_BATHROOM=33
;
; Hook runs in gameloop after erase, before MoveGuardians — safe to zero guardian
; count here (never mid-loop). Erase already ran while count was still 1.

!source "equates.asm"

!ifndef ORG {
!error "ORG required"
}

* = ORG
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
    lda #0
    sta guardian_data_base + g_off_fmin
    lda #FCTL_IDLE
    sta guardian_data_base + g_off_fctl
    rts

near
    lda px
    cmp #$36
    bcc set_frame3
    lda #2
    bne store_point

set_frame3
    lda #3

store_point
    sta guardian_data_base + g_off_fmin
    lda #FCTL_LOCK
    sta guardian_data_base + g_off_fctl
    lda #0
    sta guardian_data_base + g_off_frame
    rts

!if * > ORG + MASTER_BED_HOOK_BYTES {
!error "master_bedroom hook primary slot overflow"
}
