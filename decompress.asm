;
; RLE tilemap unpack — token (run<<3)|value, 384 cells to screen_base ($1000).
;

!zone decompress

; these are aliases
paint_loop_counter = ht
paint_loop_value = mov

; stream_ptr -> RLE bytes; paints screen_base + color_base; advances stream_ptr.
RleUnpack

    ; set up scr_ptr & col_ptr
    ldx #0
    ldy #0
    jsr ConvertTileXYToScreenAddr

--
    ; read a byte
    jsr LoadByteFromStream
    pha

    ; unpack it
    lsr
    lsr
    lsr
    sta paint_loop_counter
    pla
    and #$7
    sta paint_loop_value

-
    ; write it
    lda paint_loop_value
    sta (scr_ptr),y
    tax
    lda tile_color_src,x
    sta (col_ptr),y

    inc scr_ptr
    inc col_ptr
    bne +
    inc scr_ptr+1
    inc col_ptr+1
+
    dec paint_loop_counter
    bne -

    lda scr_ptr
    cmp #$80
    bne --
    lda scr_ptr+1
    cmp #$11
    bne --

    rts


; these are aliases
paint_loop_x = hc
paint_loop_y = hy

; A = tile type 0-6 at (hy, hc): screen chr + colour via scr_ptr / col_ptr.
PaintPlayfieldCell
    pha
    ldx paint_loop_x
    ldy paint_loop_y
    jsr ConvertTileXYToScreenAddr
    pla
    tax
    lda tile_color_src,x
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
    jsr LoadByteFromStream
    pha
    and #$0f
    sta ramp_start_y
    sta paint_loop_y
    pla                     ; ramp length and y
    lsr
    lsr
    lsr
    lsr
    tax
    inx
    stx ramp_length
    stx paint_loop_counter

    jsr LoadByteFromStream
    sta ramp_dirandx        ; ramp dir and x
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
    rts


; these are aliases
conveyor_lengthandy = arr
conveyor_velandx = arr2

; Apply 2-byte conveyor overlay (pack_conveyor2). Advances stream_ptr by 2.
; byte0 = (length-1)<<4 | y; byte1 = (velocity<<6) | x
ApplyConveyor
    ; unpack
    jsr LoadByteFromStream
    pha
    and #$0f
    sta paint_loop_y
    pla
    lsr
    lsr
    lsr
    lsr
    tax
    inx
    sta paint_loop_counter

    jsr LoadByteFromStream
    pha
    and #$1f
    sta paint_loop_x
    pla
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

    rts
