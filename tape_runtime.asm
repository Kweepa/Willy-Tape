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

hud_udg_men
    !byte 60, 60, 126, 52, 62, 60, 24, 60
hud_udg_item
    !byte 4, 4, 174, 174, 162, 66, 66, 238

tile_color_src
    !byte 1, 5, 7, 3, 2, 6       ; WHT GRN YEL CYN RED BLU — types 0-5

item_erase
    lda #0
    tay
    sta (pickup_scr),y
    lda #1
    sta (pickup_col),y
    rts

