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
    beq rle_err
    sta run
    lda run
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
rle_err
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

; Apply 3-byte ramp overlay (pack_ramp3). Advances stream_ptr by 3.
; word = x | (y<<5) | (len<<9) | (dir<<14) | (step<<15); step: 0=0, 1=+1, 3=-1 row/col.
ApplyRamp3
    ldy #0
    lda (stream_ptr),y
    sta arr
    iny
    lda (stream_ptr),y
    sta arr2
    iny
    lda (stream_ptr),y
    sta mov
    lda arr
    and #$1f
    sta hx
    lda arr
    lsr
    lsr
    lsr
    lsr
    lsr
    sta hy
    lda arr2
    and #7
    asl
    asl
    asl
    ora hy
    and #$0f
    sta hy
    lda arr2
    lsr
    and #$1f
    sta num
    lda arr2
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    lsr
    and #1
    sta g_frame
    lda mov
    and #1
    asl
    ora g_frame
    sta g_frame
    lda hy
    sta mov                     ; start row (byte 3 no longer needed)
    lda #0
    sta g_fctl
ramp_cell_loop
    lda g_fctl
    clc
    adc hx
    sta hc
    lda mov                     ; always from start row
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
    lda #3
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts

; Apply 3-byte conveyor overlay (pack_conveyor3). Advances stream_ptr by 3.
ApplyConveyor3
    ldy #0
    lda (stream_ptr),y
    sta arr
    iny
    lda (stream_ptr),y
    sta arr2
    iny
    lda (stream_ptr),y
    sta mov
    lda arr
    and #$1f
    sta hx
    lda arr
    lsr
    lsr
    lsr
    lsr
    lsr
    sta hy
    lda arr2
    and #7
    asl
    asl
    asl
    ora hy
    and #$0f
    sta hy
    lda arr2
    lsr
    and #$1f
    sta num
    lda #0
    sta g_fctl
conv_loop
    lda g_fctl
    clc
    adc hx
    sta hc
    lda #TILE_CONVEYOR
    jsr PaintPlayfieldCell
    inc g_fctl
    lda g_fctl
    cmp num
    bne conv_loop
    lda #3
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts
