; Unified per-room hooks (disk build baked these into each room PRG).

!zone tape_runtime

; Draw pickup chr and cycle cell colour while pickup_got for this room is clear.
; pickup_scr / pickup_col set at load (absolute screen + colour pointers in ZP).

FlickerItem
    ldx map
    lda pickup_got,x
    bne fi_done
    lda pickup_scr+1
    bmi fi_done
    ldy #0
    lda #ITEM_CHR
    sta (pickup_scr),y
    lda (pickup_col),y
    clc
    adc #1
    and #7
    sta (pickup_col),y
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
