;
; RLE tilemap unpack — token (run<<3)|value, 384 cells to screen_base ($1000).
;

!zone decompress

; stream_ptr -> RLE bytes; paints screen_base + color_base; advances stream_ptr.
; 384 B playfield — align_tmp=0 page (256 cells) then 1 page (128 cells).
RleUnpack
    ldx #0
    lda #0
    sta align_tmp
rle_loop
    lda align_tmp
    beq rle_loop_cont
    cpx #128
    bcs rle_done
rle_loop_cont
    ldy #0
    lda (stream_ptr),y
    sta run
    lsr
    lsr
    lsr
    sta num
    lda run
    and #7
    sta col
    ldy #0
fill_loop
    lda align_tmp
    beq fill_p0
    cpx #128
    bcs rle_done
    txa
    pha
    lda col
    tax
    lda tile_color_src,x
    sta tmp
    pla
    tax
    lda tmp
    sta color_base+256,x
    lda col
    clc
    adc #TILE_CHR_BASE
    sta screen_base+256,x
    jmp fill_advance
fill_p0
    txa
    pha
    lda col
    tax
    lda tile_color_src,x
    sta tmp
    pla
    tax
    lda tmp
    sta color_base,x
    lda col
    clc
    adc #TILE_CHR_BASE
    sta screen_base,x
fill_advance
    inx
    bne +
    inc align_tmp
+
    iny
    cpy num
    bne fill_loop
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    jmp rle_loop
rle_done
    rts

; A = tile type 0-6 at (hy, hc): screen chr + colour via scr_ptr / col_ptr.
PaintPlayfieldCell
    pha
    ldx hc
    ldy hy
    jsr ConvertTileXYToScreenAddr
    pla
    tax
    lda tile_color_src,x
    sta col
    ldy #0
    sta (col_ptr),y
    txa
    sta (scr_ptr),y
    rts

; Apply 2-byte ramp overlay (pack_ramp2). Advances stream_ptr by 2.
; byte0 = (length-1)<<4 | y; byte1 = (direction<<7) | x
; direction bit7: 0 = / up-right (row-), 1 = \ up-left (row+).
ApplyRamp
    ldy #0
    lda (stream_ptr),y
    sta arr
    iny
    lda (stream_ptr),y
    sta arr2
    lda arr
    and #$0f
    sta mov                     ; start row y
    lda arr
    lsr
    lsr
    lsr
    lsr
    clc
    adc #1
    sta num                     ; length 1-16
    lda arr2
    and #$1f
    sta hx
    lda arr2
    bmi ramp_dir_up_left
    lda #3                      ; / up-right: row decreases with column
    sta g_frame
    jmp ramp_paint
ramp_dir_up_left
    lda #1                      ; \ up-left: row increases with column
    sta g_frame
ramp_paint
    lda #0
    sta g_fctl
ramp_cell_loop
    lda g_fctl
    clc
    adc hx
    sta hc
    lda mov
    ldx g_frame
    beq ramp_row_ok
    cpx #1
    bne +
    clc
    adc g_fctl
    jmp ramp_row_ok
+
    cpx #3
    bne ramp_done
    sec
    sbc g_fctl
ramp_row_ok
    sta hy
    lda #TILE_RAMP
    jsr PaintPlayfieldCell
    inc g_fctl
    lda g_fctl
    cmp num
    bne ramp_cell_loop
ramp_done
    jsr BakeRampMeta
    lda #2
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts

; Apply 2-byte conveyor overlay (pack_conveyor2). Advances stream_ptr by 2.
; byte0 = (length-1)<<4 | y; byte1 = (velocity<<6) | x
ApplyConveyor
    ldy #0
    lda (stream_ptr),y
    sta arr
    iny
    lda (stream_ptr),y
    sta arr2
    lda arr
    and #$0f
    sta mov                     ; row y
    lda arr
    lsr
    lsr
    lsr
    lsr
    clc
    adc #1
    sta num
    lda arr2
    and #$1f
    sta hx
    lda #0
    sta g_fctl
conv_loop
    lda g_fctl
    clc
    adc hx
    sta hc
    lda mov
    sta hy
    lda #TILE_CONVEYOR
    jsr PaintPlayfieldCell
    inc g_fctl
    lda g_fctl
    cmp num
    bne conv_loop
    lda #2
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts
