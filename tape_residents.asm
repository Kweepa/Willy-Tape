; Tape residents — high bank PRG only (not copied to page 2).
; Island 1 ($0200) holds load-path paint + stream parsers.

rope_xadd_table
    !byte 1,2,3,2,2,2,3,1
    !byte 2,2,2,2,0,1,2,0
    !byte 1,2,1,1,1,2,1,2
    !byte 1,2,1,2,1,2,1,2
    !byte 1,2,1,2,1,2,1,2
    !byte 1,2,1,2,1,0,1,1
    !byte 1,1,1,0,1,1
rope_xadd_table_end = *

!if rope_xadd_table_end - rope_xadd_table <> ROPE_XADD_BYTES {
!error "rope_xadd_table size mismatch"
}

LoadOneUdgChr
    asl
    asl
    asl
    sta udg_ptr ; udg_base is page aligned
    ; when we do this it's always a udg < 32
    lda #>udg_base
    sta udg_ptr+1
    ldy #7
-
    lda (stream_ptr),y
    sta (udg_ptr),y
    dey
    bpl -

    lda #8
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts

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
    adc #<sprite_frames
    sta arr
    lda arr+1
    adc #>sprite_frames
    sta arr+1
    rts
