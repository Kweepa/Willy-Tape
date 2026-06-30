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

; these are aliases
paint_loop_counter = ht
paint_loop_x = hc
paint_loop_y = hy

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
; BakeRampMeta reads arr2 bit7 (stashed in arr3 before ramp_surface_abs).

; these are aliases
; also used by BakeRampMeta so keep in sync
ramp_lenandy = arr
ramp_dirandx = arr2
ramp_start_x = hx
ramp_start_y = mov
ramp_length = num

ApplyRamp
    ldy #0

    lda (stream_ptr),y ; ramp length and y
    and #$0f
    sta ramp_start_y
    sta paint_loop_y
    lda (stream_ptr),y ; ramp length and y
    lsr
    lsr
    lsr
    lsr
    tax
    inx
    stx ramp_length
    stx paint_loop_counter

    iny
    lda (stream_ptr),y ; ramp dir and x
    sta ramp_dirandx
    and #$1f
    sta ramp_start_x
    sta paint_loop_x

    ; draw
-
    lda #TILE_RAMP
    jsr PaintPlayfieldCell
    inc paint_loop_x
    lda ramp_dirandx
    bmi +
    dec paint_loop_y
    bne ++
+
    inc paint_loop_y
++
    dec paint_loop_counter
    bne -

    ; calculate values for calculate_ramp_y
    jsr BakeRampMeta

    ; advance stream
    lda #2
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts


; these are aliases
conveyor_lengthandy = arr
conveyor_velandx = arr2

; Apply 2-byte conveyor overlay (pack_conveyor2). Advances stream_ptr by 2.
; byte0 = (length-1)<<4 | y; byte1 = (velocity<<6) | x
ApplyConveyor
    ; unpack
    ldy #0
    lda (stream_ptr),y
    and #$0f
    sta paint_loop_y
    lda (stream_ptr),y
    lsr
    lsr
    lsr
    lsr
    tax
    inx
    sta paint_loop_counter

    iny
    lda (stream_ptr),y
    and #$1f
    sta paint_loop_x
    lda (stream_ptr),y
    rol
    rol
    rol
    and #$03
    tax
    dex ; was 0,1,2, want -1,0,1. doing it here gets us free sign extension.
    stx meta_content_belt

    ; draw
-
    lda #TILE_CONVEYOR
    jsr PaintPlayfieldCell
    inc paint_loop_x
    dec paint_loop_counter
    bpl -

    ; advance stream
    lda #2
    clc
    adc stream_ptr
    sta stream_ptr
    bcc +
    inc stream_ptr_hi
+
    rts
