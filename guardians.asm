!zone guardians_implementation

CopyDownGuardianData
    jsr CalcGuardianRecPtr
    ldy #g_off_axis
-
    lda (arr),y
    sta hx,y
    dey
    bpl -
    rts

GetHorizontalGuardianFrame
    lda hx
    and #$03
    ldx g_fctl ; check bidirectional
    beq +
    ldx hd ; if going left, want to use the first four frames
    bmi ++
    eor #4 ; otherwise use the next four
+
    bpl ++

GetVerticalGuardianBmpAddr
    lda g_frame
++
    clc
    adc ht
    jmp GetSpriteFrameAddr   ; tail call — rts resumes at caller after jsr GetVerticalGuardianBmpAddr

MoveGuardian
    ; advance either x or y
    ldx guard_axis
    lda hx,x
    clc
    adc hd
    sta hx,x
    tay

    ; convert hd into a 0 or 1 index in x
    ldx #0
    lda hd
    bmi +
    inx
+
    ; compare left or right extent against new coord stored in y
    tya
    cmp hl,x
    bne +

    lda hd     ; flip direction
    eor #$ff
    clc
    adc #1
    sta hd
+
    inc g_frame
    lda g_frame
    and g_fctl
    sta g_frame
    rts

DrawGuardian
    ldx guard_axis
    inc hguard_count,x

    ldx hx
    ldy hy
    jsr ConvertXYToScreenAddr

    ldx #3
    lda hy
    and #7
    beq draw_guard_loop
    inx
    inx
draw_guard_loop
-
    ldy cell_off_2x3,x
    lda hc
    sta (col_ptr),y
    lda draw_vguard_chrs,x
    clc
    adc guard_udg_index
    sta (scr_ptr),y
    dex
    bpl -
    rts

CopyGuardianFrame
    lda arr2
    clc
    adc #24
    sta arr3
    lda arr2+1
    adc #0
    sta arr3+1
    lda arr
    sta mod_src_col1+1
    clc
    adc #16
    sta mod_src_col2+1
    lda arr+1
    sta mod_src_col1+2
    adc #0
    sta mod_src_col2+2

    ldy #0

    lda hy
    and #7
    beq +
    tax

    lda #0
-
    sta (arr2),y
    sta (arr3),y
    iny
    dex
    bne -
+
    ldx #16
-
mod_src_col1
    lda guardian_sprites_base
    inc mod_src_col1+1
    bne +
    inc mod_src_col1+2
+
    sta (arr2),y
mod_src_col2
    lda guardian_sprites_base
    inc mod_src_col2+1
    bne +
    inc mod_src_col2+2
+
    sta (arr3),y
    iny
    dex
    bne -

    lda hy
    and #7
    eor #7
    tax

    lda #0
-
    sta (arr2),y
    sta (arr3),y
    iny
    dex
    bpl -

    rts

MoveGuardians
    lda meta_content_guardians
    beq move_guardians_done
    lda #0
    sta guardian_index
    sta hguard_count
    sta vguard_count
--
    ; UDG slot from guardian_index (inlined CalcGuardianUDGIndex)
    ; multiply by 6
    lda guardian_index
    asl
    adc guardian_index  ; asl clears C
    asl
    sta guard_udg_off
    adc #GUARDIAN_CHR ; asl clears C
    sta guard_udg_index

    jsr CopyDownGuardianData
    lda guard_axis
    bne +
    jsr ShouldMoveHorizontalGuardianThisFrame
    bne draw_guardian
    beq move_guardian
+
    jsr ShouldMoveVerticalGuardianThisFrame
    bne draw_guardian
move_guardian
    jsr MoveGuardian
    lda guard_axis
    bne +
    jsr GetHorizontalGuardianFrame
    jmp got_sprite_frame
+
    jsr GetVerticalGuardianBmpAddr
got_sprite_frame
    jsr CalcGuardianUDGAddr
    jsr CopyGuardianFrame
draw_guardian
    jsr DrawGuardian
    jmp EndGuardianLoop

EndGuardianLoop

    ; CopyUpGuardianData
    jsr CalcGuardianRecPtr
    ldy #g_off_frame
-
    lda hx,y
    sta (arr),y
    dey
    bpl -

    +BorderDebugGuardianIndex
    inc guardian_index
    lda guardian_index
    cmp meta_content_guardians
    bne --
move_guardians_done
    rts
