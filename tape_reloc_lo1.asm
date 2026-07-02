; Reloc island 1 source — high bank PRG; copied to $0200 at WarmStart.

!zone tape_reloc_lo1

reloc_lo1_src
!pseudopc RELOC_LO1_BASE {

paint_loop_counter = ht
paint_loop_value = mov
paint_loop_x = hc
paint_loop_y = hy
ramp_lenandy = arr
ramp_dirandx = arr2
ramp_start_x = hx
ramp_start_y = mov
ramp_length = num
conveyor_lengthandy = arr
conveyor_velandx = arr2

RleUnpack
    ldx #0
    ldy #0
    jsr ConvertTileXYToScreenAddr
--
    jsr LoadByteFromStream
    pha
    lsr
    lsr
    lsr
    sta paint_loop_counter
    pla
    and #$7
    sta paint_loop_value
-
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

ApplyRamp
    jsr LoadByteFromStream
    pha
    and #$0f
    sta ramp_start_y
    sta paint_loop_y
    pla
    lsr
    lsr
    lsr
    lsr
    tax
    inx
    stx ramp_length
    stx paint_loop_counter
    jsr LoadByteFromStream
    sta ramp_dirandx
    and #$1f
    sta ramp_start_x
    sta paint_loop_x
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
    jsr BakeRampMeta
    rts

ApplyConveyor
    jsr LoadByteFromStream
    pha
    and #$0f
    sta paint_loop_y
    pla
    lsr
    lsr
    lsr
    lsr
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
    dex
    stx meta_content_belt
-
    lda #TILE_CONVEYOR
    jsr PaintPlayfieldCell
    inc paint_loop_x
    dec paint_loop_counter
    bpl -
    rts

LoadByteFromStream
    ldy #0
    lda (stream_ptr),y
    php
    inc stream_ptr
    bne +
    inc stream_ptr_hi
+
    plp
    rts

ParseMeta8
    jsr LoadByteFromStream
    sta meta_content_conn
    jsr LoadByteFromStream
    sta meta_content_conn+1
    jsr LoadByteFromStream
    sta meta_content_conn+2
    jsr LoadByteFromStream
    sta meta_content_conn+3
    jsr LoadByteFromStream
    sta meta_content_spawn_px
    jsr LoadByteFromStream
    sta meta_content_spawn_py
    jsr LoadByteFromStream
    sta meta_content_record_flags
    lda meta_content_record_flags
    and #FLAG_ROPE
    sta meta_content_room_has_rope
    lda meta_content_record_flags
    and #FLAG_ARROW
    sta meta_content_has_arrow
    jsr LoadByteFromStream
    sta $900f ; border/bg color
    rts

}
reloc_lo1_size = * - reloc_lo1_src
!if reloc_lo1_size > RELOC_LO1_MAX {
!error "reloc island 1 overflow"
}
