; Tape residents — high bank PRG only (not copied to page 2).
; Island 1 ($0200) holds load-path paint + stream parsers.
; Island 2 ($036C) holds ConvertXY*, GetSpriteFrameAddr, CalcGuardian*.

!zone tape_residents

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

