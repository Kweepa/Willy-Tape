; Unified per-room hooks (disk build baked these into each room PRG).

!zone tape_runtime

; Cycle item cell colour while pickup_got for this room is clear.

; TODO: optimize this. for example eor >(color_base ^ screen_base)
; to make the color address, write to colour, then eor it back
; or in LoadRoom, make this once and write to metadata
; would be much simpler to assign 4 bytes in zp and then we can use (zp),y
; directly

FlickerItem
    ldx map
    lda pickup_got,x
    bne fi_done
    lda meta_content_pickup_scr+1
    cmp #$ff
    beq fi_done
    lda meta_content_pickup_scr
    sta col_ptr
    lda meta_content_pickup_scr+1
    clc
    adc #>(color_base - screen_base)
    sta col_ptr+1
    ldy #0
    lda (col_ptr),y
    clc
    adc #1
    and #7
    sta (col_ptr),y
fi_done
    rts

AnimateConveyors
    rts
    !fill conveyor_prefix_bytes - 1, 0

DoBelt
    sec                         ; willy.asm tail call expects C=1
    rts
    !fill do_belt_prefix_bytes - 2, 0

tile_color_src
    !byte 1, 5, 7, 3, 2, 6       ; WHT GRN YEL CYN RED BLU — types 0-5

item_draw
    rts
    !fill meta_content_item_draw_size - 1, 0

item_erase
    rts
    !fill meta_content_item_erase_size - 1, 0
