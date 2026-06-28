!zone endgame_implementation

; Called from main loop after Collide. Room hook sets ending_pending + map.
CheckEndingTeleport
    lda ending_pending
    beq +
    dec ending_pending
    jsr LoadRoom
    lda #6
    sta guardian_data_base + guardian_record_bytes + g_off_fmin
+
    rts
