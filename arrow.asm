; Flying arrow — unified runtime (tape). UDG chr 64/65 @ $1A00; pick at draw time.

!zone arrow

arrow_update
    ldx left_right_ctr
    beq +
    rts
+
    ldy arrow_row_y
    jsr ConvertXYToScreenAddr

    ldy arrow_x_zp
    cpy #24
    bcs +

    lda (map_ptr),y
    and #$0f
    sta (scr_ptr),y
+
    ldy arrow_x_zp
    lda arrow_rtl
    beq arrow_step_right
    dey
    jmp arrow_step_done
arrow_step_right
    iny
arrow_step_done
    tya
    and #127
    tay
    sty arrow_x_zp

    cpy arrow_sound_x
    bne +
    lda #129
    sta $900c
    lda #10
    sta $900e
+
    cpy #24
    bcs ++

    ldx #ARROW_CHR_LTR
    lda arrow_rtl
    beq +
    inx
+
    txa
    sta (scr_ptr),y
++
    rts
