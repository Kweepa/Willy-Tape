; Relocated leaf routines — bytes assembled in boot zone, run at $01B6/$02xx/$03xx/$1000.
; WarmStart copies each block before jmp start_game.

reloc_a_src
!pseudopc RELOC_A_BASE {
FormatRoomName
    lda map
    ldy #'0'
-
    cmp #10
    bcc +
    sbc #10
    iny
    bne -
+
    adc #'0'
    sta room_name+2
    sty room_name+1
    rts

DrawHud
    lda items_collected
    ldy #$b0
-
    cmp #10
    bcc +
    sbc #10
    iny
    bne -
+
    sty hud_items_scr
    clc
    adc #$b0
    sta hud_items_scr+1

    lda men
    clc
    adc #$b0
    sta hud_men_count_scr
    rts

ShouldMoveHorizontalGuardianThisFrame
    lda hguard_count
    and #3
    cmp left_right_ctr
    rts

ShouldMoveVerticalGuardianThisFrame
    lda vguard_count
    cmp up_down_ctr
    beq +
    sec
    sbc #3
    cmp up_down_ctr
+
    rts

SaveSpawn
    lda px
    sta spawn_px
    lda py
    sta spawn_py
    rts
}
reloc_a_size = * - reloc_a_src
!if RELOC_A_BASE + reloc_a_size > RELOC_A_LIMIT {
!error "reloc block A overflow"
}

reloc_b_src
!pseudopc RELOC_B_BASE {
ConvertXYToScreenAddr
    tya
    lsr
    lsr
    and #$fe
    tay
    lda x24rowtab,y
    sta scr_ptr
    lda x24rowtab + 1,y
    sta scr_ptr + 1
    txa
    lsr
    lsr
    clc
    adc scr_ptr
    sta scr_ptr
    bcc +
    inc scr_ptr + 1
+
    lda scr_ptr
    sta map_ptr
    sta col_ptr
    lda scr_ptr + 1
    clc
    adc #>(map_base - screen_base)
    sta map_ptr + 1
    adc #>(color_base - map_base)
    sta col_ptr + 1
    rts

GetSpriteFrameAddr
    ldx #0
    stx arr+1
    ldx #5
-
    asl
    rol arr+1
    dex
    bne -
    clc
    adc #<guardian_sprites_base
    sta arr
    lda arr+1
    adc #>guardian_sprites_base
    sta arr+1
    rts

CalcGuardianRecPtr
    lda guardian_index
    asl
    asl
    adc guardian_index
    asl
    adc #<guardian_data_base
    sta arr
    lda #>guardian_data_base
    sta arr+1
    rts

CalcGuardianUDGAddr
    lda guard_udg_off
    asl
    asl
    asl
    clc
    adc #<guardian_udgs
    sta arr2
    lda #>guardian_udgs
    adc #0
    sta arr2+1
    rts
}
reloc_b_size = * - reloc_b_src
!if RELOC_B_BASE + reloc_b_size > RELOC_B_LIMIT {
!error "reloc block B overflow"
}

reloc_c_src
!pseudopc RELOC_C_BASE {
GetCollision
    lda (map_ptr),y
    and #$0f
    rts
}
reloc_c_size = * - reloc_c_src
!if RELOC_C_BASE + reloc_c_size > RELOC_C_LIMIT {
!error "reloc block C overflow"
}

reloc_d_src
!pseudopc RELOC_D_BASE {
ResetMap
    lda #0
    sta dead
    sta left_right_ctr
    sta up_down_ctr
    sta belt_active
    rts
}
reloc_d_size = * - reloc_d_src
!if RELOC_D_BASE + reloc_d_size > RELOC_D_LIMIT {
!error "reloc block D overflow"
}

reloc_e_src
!pseudopc RELOC_E_BASE {
rope_release
    lda #0
    sta rope_willy_is_holding
    lda #ROPE_GRAB_COOLDOWN_MAX
    sta rope_grab_cooldown
    rts
}
reloc_e_size = * - reloc_e_src
!if RELOC_E_BASE + reloc_e_size > RELOC_E_LIMIT {
!error "reloc block E overflow"
}
