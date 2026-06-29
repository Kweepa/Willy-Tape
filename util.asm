;
; WaitForRasterLine
;

WaitForRaster
    ; wait for raster below sync band (inlined WaitForRasterLineLessThan)
-
    lda $9004
    and #$fe
    cmp #RASTERLINE_PAL
    bcs -

WaitForRasterLine
    lda $9004
    and #$fe
    cmp #RASTERLINE_PAL
    bne WaitForRasterLine
    rts

    ; set colors to A across gameplay colour cells (408 bytes)
SetColors
    ldx #0
-
    sta color_base,x
    inx
    cpx #0
    bne -
    ldx #152
-
    sta color_base+256,x
    dex
    bne -
    rts

try_fall_death
    lda inairtime
    cmp #70
    bcc +
    lda #1
    sta dead
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

GetCollision
    lda (map_ptr),y
    and #$0f
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

play_sound_at_default_volume
    sta $900c
    lda #2
    sta $900e
    rts

cell_off_2x3
    !byte 24, 25, 48, 49, 72, 73                    ; gameloop, guardians

x24rowtab
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