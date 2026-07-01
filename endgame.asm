!zone endgame_implementation

; Toilet end sequence uses pool frames 2-3 of the 4-frame toilet gfx block
; (set toilet_end in bake/catalogue_sprites.asm — adjacent to set toilet).
TOILET_END_POOL_HT = 140

; Called from main loop after Collide. Room hook sets ending_pending + map.
CheckEndingTeleport
    lda ending_pending
    beq +
    dec ending_pending
    jsr LoadRoom
    lda #TOILET_END_POOL_HT
    sta guardian_data_base + guardian_record_bytes + g_off_fmin
    lda #1
    sta guardian_data_base + guardian_record_bytes + g_off_fctl
+
    rts
