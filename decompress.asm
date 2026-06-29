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
; arr3 = ramp direction (3=/ 1=\); run = column index — not g_frame/g_fctl
; (guardian animation uses those ZP bytes during gameplay).

; these are aliases
; also used by BakeRampMeta so keep in sync
ramp_lenandy = arr
ramp_dirandx = arr2
ramp_start_x = hx
ramp_start_y = mov
ramp_length = num

ramp_loop_counter = ht
; used by PaintPlayfieldCell
ramp_loop_x = hc
ramp_loop_y = hy

ApplyRamp
    ldy #0
    lda (stream_ptr),y
    sta ramp_lenandy
    iny
    lda (stream_ptr),y
    sta ramp_dirandx
    lda ramp_lenandy
    and #$0f
    sta ramp_start_y
    sta ramp_loop_y
    lda ramp_lenandy
    lsr
    lsr
    lsr
    lsr
    clc
    adc #1
    sta ramp_length
    sta ramp_loop_counter
    lda ramp_dirandx
    and #$1f
    sta ramp_start_x
    sta ramp_loop_x

-
    lda #TILE_RAMP
    jsr PaintPlayfieldCell
    inc ramp_loop_x
    lda ramp_dirandx
    bmi +
    dec ramp_loop_y
    bne ++
+
    inc ramp_loop_y
++
    dec ramp_loop_counter
    bne -

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
