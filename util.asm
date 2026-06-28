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

    ; set colors to A
SetColors
    ldx #192
-
    sta $95ff,x
    sta $96bf,x
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

    ; takes A=note
play_sound_at_default_volume
    sta $900c
    lda #2
    sta $900e
    rts